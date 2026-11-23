"""Measure images of a named O3' atom at a named phosphorus in a written model."""
from hashlib import sha256
from math import dist, isfinite, sqrt
from pathlib import Path

from .cif_phosphate_angles import printed_phosphate_angles
from .refinement_contact_geometry import _contacts
from .refinement_link_geometry import _model_labels, _printed_rows
from .topostitch_contacts import _angle
from .topostitch_graph import _inverse, _operator
from .topostitch_images import _cartesian, _fractional, closest_atom_images
from .topostitch_periodic import _op_key, crystal_from_pdb_bytes


# Two distances between PDB positions rounded to 0.001 Å can differ by this amount.
PDB_IMAGE_SEPARATION_A = 2 * sqrt(3) * .001


def _printed_evidence(kind, text, labels, endpoints, images, gemmi, members, distance):
    """Phenix applies its operator to the second label, in printed order."""
    sections = {}
    try:
        if kind == "bonds":
            sections, bonds = _printed_rows(text, labels)
            rows = ((ends, image, origin, float(values["model"]),
                     {"ideal_A": float(values["ideal"]), "sigma_A": float(values["sigma"]),
                      "slack_A": float(values.get("slack", 0))})
                    for ends, origin, values, image in bonds)
        else:
            rows = ((ends, image, origin, float(actual), {"vdw_A": float(vdw)})
                    for ends, actual, vdw, image, origin in _contacts(text, labels, sections))
        matches = []
        for ends, image, origin, actual, details in rows:
            if ends == endpoints:
                expected = images[0]
            elif ends == endpoints[::-1]:
                expected = images[1]
            else:
                continue
            if _op_key(_operator(image or "x,y,z", gemmi, members)) == _op_key(expected):
                matches.append(dict(endpoints=[list(e) for e in ends], image_of_second_atom=image,
                                    origin=origin, model_A=actual, printed_minus_coordinate_A=actual-distance,
                                    **details))
    except ValueError as exc:
        return dict(status="UNASSESSED", reason=str(exc), sections=None, matches=None)
    return dict(status="OBSERVED" if sections else "NOT_RECORDED", sections=sections,
                matches=matches if sections else None)


class PhosphateEndpointUnavailable(ValueError):
    """The coordinate identities or an endpoint prevent a phosphate measurement."""


def inspect_phosphate_image(model, *, phosphate=None, o3=None, o3_image=None, nearest_image=False, geometry=None,
                            native_receipt=None, registered=None, duplex_partners=None, partner_images=None):
    """Inspect a manual pair or resolve an explicit registered continuation on this model."""
    if registered is not None:
        from .cif_phosphate_continuation import inspect_registered_continuation
        if any(value is not None for value in (phosphate, o3, o3_image)) or nearest_image:
            raise ValueError("A registered continuation supplies both endpoints and the image")
        result = inspect_registered_continuation(model, registered, geometry=geometry, native_receipt=native_receipt)
    else:
        if not phosphate or not o3:
            raise ValueError("Manual phosphate inspection requires both --phosphate and --o3")
        result = _inspect_coordinates(model, phosphate=phosphate, o3=o3, o3_image=o3_image, nearest_image=nearest_image,
                                      geometry=geometry, native_receipt=native_receipt)
    return with_duplex_direction(model, result, duplex_partners, partner_images)


def with_duplex_direction(model, inspection, partners, images):
    if partners is None:
        if images is not None:
            raise ValueError("--partner-images requires --duplex-partners")
        return inspection
    from .cif_phosphate_duplex import inspect_duplex_direction
    return dict(inspection, duplex_direction=inspect_duplex_direction(model, inspection, partners, images))


def _inspect_coordinates(model, *, phosphate, o3, o3_image=None, nearest_image=False, geometry=None, native_receipt=None):
    """Compare coordinates and optional printed terms without assigning a partner.

    Apply the full image (including its cell translation) to O3' and its C3'.
    Missing or unoccupied angle atoms leave that measurement unavailable.
    Coordinate angles alone say nothing about the angles restrained by Phenix.
    """
    if (o3_image is not None) == nearest_image:
        raise ValueError("Choose either one explicit O3' image or the nearest-image comparison")
    model = Path(model)
    try:
        raw, labels = _model_labels(model)
    except ValueError as exc:
        raise PhosphateEndpointUnavailable(str(exc)) from exc
    gemmi, cell, group = crystal_from_pdb_bytes(raw)
    spacegroup = gemmi.find_spacegroup_by_name(group)
    members = {_op_key(op) for op in spacegroup.operations()}
    op = None if nearest_image else _operator(o3_image, gemmi, members)
    fields = {phosphate: {"P", "OP1", "OP2", "OP3", "O5'"}}
    fields.setdefault(o3, set()).update(("O3'", "C3'"))
    atoms = {}
    for line in raw.decode("ascii").splitlines():
        if line[:6] not in {"ATOM  ", "HETATM"}:
            continue
        identity, xyz = labels[line[12:27]]
        site, _, name = identity
        if name not in fields.get(site, ()):
            continue
        occupancy = float(line[54:60])
        if not isfinite(occupancy) or not 0 <= occupancy <= 1:
            raise ValueError(f"Invalid occupancy for {site} {name}")
        atoms[site, name] = (identity, xyz, line[76:78].strip().upper(), occupancy)

    def point(site, name, element, *, apply_image=False, required=False):
        atom = atoms.get((site, name))
        if atom is None or atom[2] != element or atom[3] == 0:
            if required:
                raise PhosphateEndpointUnavailable(f"Require an occupied {element} atom named {name} at {site}")
            return None
        if apply_image:
            if op is None:
                return None
            return _cartesian(op.apply_to_xyz(_fractional(atom[1], cell, gemmi)), cell, gemmi)
        return atom[1]

    p = point(phosphate, "P", "P", required=True)
    observations = {}
    if nearest_image:
        moving = point(o3, "O3'", "O", required=True)
        closest = closest_atom_images(p, moving, cell, spacegroup, gemmi)
        gap = closest[1]["distance_A"] - closest[0]["distance_A"]
        allowance = PDB_IMAGE_SEPARATION_A
        if gap > allowance:
            op = _operator(closest[0]["image"]["operator_xyz"], gemmi, members)
        observations["image_ranking"] = dict(status="SEPARATED" if op is not None else "AMBIGUOUS_AT_PDB_PRECISION",
            closest_two=closest, separation_A=gap, pdb_rounding_allowance_A=allowance)
    oxygen = point(o3, "O3'", "O", apply_image=True, required=True)
    p_atom, o_atom = (phosphate, "P", "P", False), (o3, "O3'", "O", True)
    triplets = {"C3'-O3'-P": ((o3, "C3'", "C", True), o_atom, p_atom)}
    for name in ("OP1", "OP2", "O5'"):
        triplets["O3'-P-" + name] = (o_atom, p_atom, (phosphate, name, "O", False))
    angles = {}
    samples = {}
    for name, triplet in triplets.items():
        positions = [point(site, atom, element, apply_image=use_mate) for site, atom, element, use_mate in triplet]
        angles[name] = _angle(positions) if all(x is not None for x in positions) else None
        if geometry is not None and all((site, atom) in atoms for site, atom, _, _ in triplet):
            keys = tuple(atoms[site, atom][0] for site, atom, _, _ in triplet)
            samples[keys] = dict(name=name, mate=positions, image_atoms=[row[3] for row in triplet],
                                 asu=[point(site, atom, element) for site, atom, element, _ in triplet])
    phosphate_atoms = {}
    for name in ("P", "OP1", "OP2", "OP3", "O5'"):
        atom = atoms.get((phosphate, name))
        phosphate_atoms[name] = dict(element=atom[2], occupancy=atom[3]) if atom else None
    ends = atoms[phosphate, "P"][0], atoms[o3, "O3'"][0]
    distance = dist(p, oxygen) if oxygen is not None else None
    printed = None
    if geometry is not None:
        geometry = Path(geometry)
        data = geometry.read_bytes()
        if op is None:
            printed = dict(status="UNASSESSED", reason="Comparing printed terms requires one resolved O3' image")
        else:
            text = data.decode("utf-8")
            images = (op, _inverse(op, gemmi.Op("x,y,z")))
            printed = {kind: _printed_evidence(kind, text, labels, ends, images, gemmi, members, distance)
                       for kind in ("bonds", "nonbonded")}
            printed["angles"] = printed_phosphate_angles(text, labels, samples, op, gemmi, members)
        printed["geometry_sha256"] = sha256(data).hexdigest()
        if geometry.read_bytes() != data:
            raise ValueError("Printed geometry changed during inspection")
    if native_receipt is not None:
        from .cif_phosphate_reference import read_phosphate_references
        observations["native_reference_links"] = read_phosphate_references(native_receipt, raw, phosphate=phosphate, o3=o3)
    if model.read_bytes() != raw:
        raise ValueError("Model changed during phosphate inspection")
    return dict(policy_id="phosphate-image-observation-v1", model_sha256=sha256(raw).hexdigest(),
                phosphate=list(ends[0]), o3=list(ends[1]), o3_image=op.triplet() if op is not None else None,
                cell=list(cell.parameters), space_group=group, phosphate_atoms=phosphate_atoms,
                distance_A=distance, coordinate_angles_degrees=angles, printed_geometry=printed,
                scientific_approval="NOT_ASSESSED", **observations)
