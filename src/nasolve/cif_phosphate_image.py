"""Measure a caller-named O3' crystal image at a phosphorus in a written model."""
from hashlib import sha256
from math import dist, isfinite
from pathlib import Path

from .refinement_contact_geometry import _contacts
from .refinement_link_geometry import _model_labels, _printed_rows
from .topostitch_contacts import _angle
from .topostitch_graph import _inverse, _operator
from .topostitch_images import _cartesian, _fractional
from .topostitch_periodic import _op_key, crystal_from_pdb_bytes


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


def inspect_phosphate_image(model, *, phosphate, o3, o3_image, geometry=None):
    """Compare coordinates and optional printed terms without assigning a partner.

    Apply the full image (including its cell translation) to O3' and its C3'.
    Missing or unoccupied angle atoms leave that measurement unavailable.
    Coordinate angles alone say nothing about the angles restrained by Phenix.
    """
    model = Path(model)
    raw, labels = _model_labels(model)
    gemmi, cell, group = crystal_from_pdb_bytes(raw)
    members = {_op_key(op) for op in gemmi.find_spacegroup_by_name(group).operations()}
    op = _operator(o3_image, gemmi, members)
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
                raise ValueError(f"Require an occupied {element} atom named {name} at {site}")
            return None
        if apply_image:
            return _cartesian(op.apply_to_xyz(_fractional(atom[1], cell, gemmi)), cell, gemmi)
        return atom[1]

    p = point(phosphate, "P", "P", required=True)
    oxygen = point(o3, "O3'", "O", apply_image=True, required=True)
    c3 = point(o3, "C3'", "C", apply_image=True)
    angles = {"C3'-O3'-P": _angle([c3, oxygen, p]) if c3 is not None else None}
    for name in ("OP1", "OP2", "O5'"):
        neighbour = point(phosphate, name, "O")
        angles["O3'-P-" + name] = _angle([oxygen, p, neighbour]) if neighbour is not None else None
    phosphate_atoms = {}
    for name in ("P", "OP1", "OP2", "OP3", "O5'"):
        atom = atoms.get((phosphate, name))
        phosphate_atoms[name] = dict(element=atom[2], occupancy=atom[3]) if atom else None
    ends = atoms[phosphate, "P"][0], atoms[o3, "O3'"][0]
    distance = dist(p, oxygen)
    printed = None
    if geometry is not None:
        geometry = Path(geometry)
        data = geometry.read_bytes()
        text = data.decode("utf-8")
        images = (op, _inverse(op, gemmi.Op("x,y,z")))
        printed = {kind: _printed_evidence(kind, text, labels, ends, images, gemmi, members, distance)
                   for kind in ("bonds", "nonbonded")}
        printed["geometry_sha256"] = sha256(data).hexdigest()
        if geometry.read_bytes() != data:
            raise ValueError("Printed geometry changed during inspection")
    if model.read_bytes() != raw:
        raise ValueError("Model changed during phosphate inspection")
    return dict(policy_id="phosphate-image-observation-v1", model_sha256=sha256(raw).hexdigest(),
                phosphate=list(ends[0]), o3=list(ends[1]), o3_image=op.triplet(),
                cell=list(cell.parameters), space_group=group, phosphate_atoms=phosphate_atoms,
                distance_A=distance, coordinate_angles_degrees=angles, printed_geometry=printed,
                scientific_approval="NOT_ASSESSED")
