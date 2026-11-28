"""Measure the four neighbours of a sulfur-bearing phosphate in a deposited model."""
from hashlib import sha256
from itertools import combinations
from math import dist, isfinite
from pathlib import Path
import re

from .cif_captured_geometry import _observed
from .cif_catalogue import MAX_SOURCE_BYTES
from .cif_deposition_links import (_cif_block, _coordinates, _covalent_o3_connections,
                                   _endpoint, _rows, resolve_deposition_image)
from .cif_doctor import assess_dictionaries
from .cif_linked_preparation import component_values
from .cif_stereochemistry_audit import _graph
from .cif_sulfur_phosphate import source_sulfur_phosphates
from .topostitch_contacts import _angle
from .topostitch_graph import _compose, _inverse


def _centre(dictionary, code):
    assessment = assess_dictionaries([dictionary], stage="source")
    components = assessment["components"]
    if (len(components) != 1 or components[0]["component_id"] != code
            or components[0]["verdicts"]["graph"] != "PASS"):
        raise ValueError("Supply one graph-valid source dictionary for the specified component")
    values = component_values(dictionary, code)
    elements, _, _, neighbours = _graph(values)
    centres = [p for p, e in elements.items() if e == "P" and
               any(elements[other] == "S" for other in neighbours[p])]
    rows = source_sulfur_phosphates(values, sorted(centres))
    if len(rows) == 1 and rows[0]["status"] == "SOURCE_ROLES_IDENTIFIED":
        return {"phosphorus": rows[0]["phosphorus"], **rows[0]["roles"]}, None
    return None, [r["status"] for r in rows] or ["NO_PHOSPHORUS_SULFUR_BOND"]


def _donor_image(row, donor_side, phosphorus_side, coords, gemmi):
    donor, acceptor = (row.get(f"ptnr{s}_symmetry") for s in (donor_side, phosphorus_side))
    identity = gemmi.Op("x,y,z")
    # The same declared operation, including its translation, cancels in g^-1 g.
    # Different unlisted images cannot be related from the space-group name alone.
    if (not coords.ops and isinstance(donor, str) and donor == acceptor
            and re.fullmatch(r"[1-9][0-9]*_[0-9]{3}", donor)):
        return identity
    d, p = (resolve_deposition_image(x, coords.ops) for x in (donor, acceptor))
    return _compose(_inverse(p, identity), d) if p is not None and d is not None else None


def _site_measurement(coords, site, code, roles, declarations, maximum, gemmi):
    model, chain, number = site
    row = dict(model=model, label_asym_id=chain, label_seq_id=number,
               author_ids=sorted(coords.authors.get(site, ())))
    if len(declarations) != 1:
        return dict(row, status="AMBIGUOUS_INCOMING_LINK" if declarations else "NO_DECLARED_INCOMING_LINK")
    connection, donor_side, p_side = declarations[0]
    donor_chain, donor_number, donor_code, donor_alt = _endpoint(connection, donor_side)
    _, _, _, p_alt = _endpoint(connection, p_side)
    row["connection_id"] = connection.get("id") or None
    if not donor_chain or not donor_number or not donor_code:
        return dict(row, status="INCOMPLETE_DONOR_IDENTITY")
    donor = (model, donor_chain, int(donor_number))
    row["donor"] = dict(label_asym_id=donor_chain, label_seq_id=donor[2], component=donor_code,
                        author_ids=sorted(coords.authors.get(donor, ())))
    if any(c[:4] in {(*site, code), (*donor, donor_code)} for c in coords.sequence_conflicts):
        return dict(row, status="CONFLICTING_SEQUENCE")
    op = _donor_image(connection, donor_side, p_side, coords, gemmi)
    if op is None or (op != gemmi.Op("x,y,z") and coords.cell is None):
        return dict(row, status="UNRESOLVED_CRYSTAL_IMAGE")
    row["donor_image_in_phosphate_frame"] = op.triplet()
    if site == donor and op == gemmi.Op("x,y,z"):
        return dict(row, status="SAME_RESIDUE_LINK")
    if any(comp == code and atom == roles["leaving_oxygen"] and (not p_alt or alt in ("", p_alt))
           for comp, atom, alt in coords.sites[site]):
        return dict(row, status="LEAVING_OXYGEN_PRESENT")

    def point(address, component, name, alt, element, *, in_donor_image=False):
        hit = coords.locate(address, name, component, alt)
        if hit is None:
            return None
        key, xyz = hit
        if (key[2] and key[2] != alt) or coords.atom_elements[address, key] != element:
            return None
        if in_donor_image and op != gemmi.Op("x,y,z"):
            return tuple(coords.cell.op_as_transform(op).apply(gemmi.Position(*xyz)))
        return xyz

    p = point(site, code, roles["phosphorus"], p_alt, "P")
    previous = point(donor, donor_code, "O3'", donor_alt, "O", in_donor_image=True)
    neighbours = {
        "carbon_linked_oxygen": point(site, code, roles["carbon_linked_oxygen"], p_alt, "O"),
        "preceding_O3": previous,
        "retained_oxygen": point(site, code, roles["retained_oxygen"], p_alt, "O"),
        "sulfur": point(site, code, roles["sulfur"], p_alt, "S"),
    }
    if p is None or None in neighbours.values():
        return dict(row, status="INCOMPLETE_OR_AMBIGUOUS_ATOMS")
    lengths = {name: dist(p, xyz) for name, xyz in neighbours.items()}
    if lengths["preceding_O3"] > maximum:
        return dict(row, status="LONG_DECLARED_LINK", lengths_A=lengths)
    angles = {f"{a}--{b}": _angle([x, p, y]) for (a, x), (b, y) in combinations(neighbours.items(), 2)}
    # Order is fixed by chemical role. This scalar is six times a tetrahedron's volume.
    shell = [neighbours["sulfur"], neighbours["carbon_linked_oxygen"], previous, neighbours["retained_oxygen"]]
    v = _observed("chirality", shell)
    if any(x is None or not isfinite(x) for x in (*angles.values(), *lengths.values(), v)) or v == 0:
        return dict(row, status="DEGENERATE_COORDINATES")
    # An outside/face-centred P does not give one consistent tetrahedral hand.
    subvolumes = [_observed("chirality", [*shell[:i], p, *shell[i+1:]]) for i in range(4)]
    if any(not isfinite(x) or x == 0 or (x > 0) != (v > 0) for x in subvolumes):
        return dict(row, status="PHOSPHORUS_OUTSIDE_TETRAHEDRON", lengths_A=lengths, angles_deg=angles)
    c3 = point(donor, donor_code, "C3'", donor_alt, "C", in_donor_image=True)
    native_order = [p, previous, neighbours["retained_oxygen"], neighbours["sulfur"]]
    return dict(row, status="MEASURED", lengths_A=lengths, angles_deg=angles, ordered_volume_A3=v,
                native_order_volume_A3=_observed("chirality", native_order),
                donor_C3_O3_P_deg=_angle([c3, previous, p]) if c3 is not None else None)


def inspect_sulfur_links(model, dictionary, code, *, maximum=2.2):
    """Use one exact CCD and explicit covalent connections to read occupied polymer sites."""
    try:
        import gemmi
    except ImportError as exc:
        raise ValueError("Sulfur-link inspection requires NASolve[topology]") from exc
    if not isfinite(maximum) or maximum <= 0:
        raise ValueError("Supply a positive, finite maximum incoming O3′–P distance")
    model, dictionary = Path(model), Path(dictionary)
    if dictionary.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Oversized source component dictionary")
    source_digest = sha256(dictionary.read_bytes()).hexdigest()
    digest, block = _cif_block(model, "_atom_site.id", "coordinate", gemmi)
    roles, reasons = _centre(dictionary, code)
    report = dict(schema_version=1, component=code, model_sha256=digest, source_sha256=source_digest,
                  maximum_incoming_distance_A=maximum, roles=roles, status="REVIEW", sites=[],
                  volume_definition="det(own carbon-linked O - S, preceding O3′ - S, retained O - S), in the P frame.",
                  native_order_definition="det(preceding O3′ - P, retained O - P, S - P), at the written coordinates.",
                  scope="Coordinates and declared covalent links only. Charge, absolute CIP assignment, native restraints and diffraction are separate evidence.")
    if reasons is not None:
        report["review_reasons"] = reasons
    else:
        coords = _coordinates(block, gemmi, requested_atoms={"O3'", "C3'", *roles.values()})
        sites = set()
        outside = 0
        for atom in _rows(block, "_atom_site."):
            if atom.get("label_comp_id") != code:
                continue
            seq = atom.get("label_seq_id")
            site = (atom.get("pdbx_PDB_model_num") or "1", atom.get("label_asym_id"), int(seq) if seq else None)
            if site in coords.sites:
                sites.add(site)
            else:
                outside += 1
        by_site = {}
        for connection, donor_side, p_side in _covalent_o3_connections(block, roles["phosphorus"]):
            ch, seq, comp, _ = _endpoint(connection, p_side)
            if comp != code or not seq:
                continue
            key = (ch, int(seq))
            by_site.setdefault(key, []).append((connection, donor_side, p_side))
        report["unbound_matching_atom_rows"] = outside
        if not sites:
            report["review_reasons"] = ["NO_MATCHING_NUCLEIC_ACID_POLYMER_SITE"]
        elif outside:
            report["review_reasons"] = ["MATCHING_ATOMS_OUTSIDE_LABELLED_POLYMER_SITES"]
        for site in sorted(sites):
            links = by_site.get(site[1:], ())
            report["sites"].append(_site_measurement(coords, site, code, roles, links, maximum, gemmi))
        if sites and not outside and all(row["status"] == "MEASURED" for row in report["sites"]):
            report["status"] = "MEASURED"
    if sha256(dictionary.read_bytes()).hexdigest() != source_digest or sha256(model.read_bytes()).hexdigest() != digest:
        raise ValueError("A sulfur-link input changed during inspection")
    return report
