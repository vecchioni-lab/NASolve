"""Construct the 2′ hydroxyl of an explicitly requested canonical RNA parent."""
from hashlib import sha256
from math import copysign, dist, isfinite, sqrt

from .cif_stereochemistry_audit import _coordinates, _graph, _stereo, _values, _volume
from .postmr_restoration import _dot, _frame, _model_records, _sub, source_graph_fragment

RNA_PARENTS = frozenset({"A", "C", "G", "U"})
POLICY_ID = "postmr-source-deoxy-to-ribose-parent-v1"
_C2_FRAME = ("C2'", "C1'", "C3'")
_C2_NEIGHBORS = ("C1'", "C3'", "O2'")
_C3_NEIGHBORS = ("C2'", "C4'", "O3'")


def _bonded_hydrogens(graph, atom):
    elements, _, _, neighbors = graph
    return {n for n in neighbors[atom] if elements[n] == "H"}


def _remainder(graph, markers, omitted):
    elements, bonds, charges, _ = graph
    atoms = {n: (e, charges[n], markers[n] if n != "C2'" else None)
             for n, e in elements.items() if n not in omitted}
    edges = {key: order for key, order in bonds.items() if not omitted.intersection(key)}
    return atoms, edges


def _reference(source, before, template, parent):
    dna = _values(source, before)
    rna = _values(template, parent)
    source_graph, target_graph = _graph(dna), _graph(rna)
    dna_stereo, rna_stereo = _stereo(dna), _stereo(rna)
    types = {v.strip().upper() for k in ("_chem_comp.type", "_chem_comp.group")
             for v in rna.get(k, ()) if v.strip() not in {"", ".", "?"}}
    if not types or not types <= {"RNA LINKING", "RNA"}:
        raise ValueError("Canonical target must declare an RNA component")
    hydrogens = _bonded_hydrogens(source_graph, "C2'")
    if (len(hydrogens) != 2 or source_graph[3]["C2'"] - hydrogens != {"C1'", "C3'"}
            or dna_stereo["C2'"] != "N"):
        raise ValueError("Source must have an explicit deoxy methylene at C2′")
    elements, bonds, charges, neighbors = target_graph
    if elements.get("O2'") != "O" or "C2'" not in neighbors:
        raise ValueError("Canonical RNA target lacks its 2′ oxygen or C2′")
    retained_h = _bonded_hydrogens(target_graph, "C2'")
    hydroxyl_h = _bonded_hydrogens(target_graph, "O2'")
    if (len(retained_h) != 1 or len(hydroxyl_h) != 1 or charges["O2'"] != 0
            or neighbors["C2'"] - retained_h != set(_C2_NEIGHBORS)
            or neighbors["O2'"] - hydroxyl_h != {"C2'"}):
        raise ValueError("Canonical parent requires an unbridged neutral 2′ hydroxyl")
    for atom, attached in (("C2'", neighbors["C2'"]), ("O2'", hydroxyl_h)):
        if any(bonds[tuple(sorted((atom, n)))] != "SINGLE" for n in attached):
            raise ValueError("Ribose 2′ hydroxyl requires single bonds")
    for graph, hydrogens_by_atom in ((source_graph, {"C2'": hydrogens}),
                                     (target_graph, {"C2'": retained_h, "O2'": hydroxyl_h})):
        for donor, attached in hydrogens_by_atom.items():
            if any(graph[3][h] != {donor} or graph[2][h] != 0
                   or graph[1][tuple(sorted((donor, h)))] != "SINGLE" for h in attached):
                raise ValueError("Each replaced hydrogen must be neutral and singly bonded to its donor")
    # In the four canonical RNA parents C2′ is R. An arabinose epimer needs its own source.
    if rna_stereo["C2'"] != "R":
        raise ValueError("Canonical RNA parent requires the declared ribose C2′ stereochemistry")
    if any(rna_stereo[n] not in {"R", "S"} for n in ("C1'", "C2'", "C3'", "C4'")):
        raise ValueError("Canonical RNA reference lacks a declared sugar stereocentre")
    added = retained_h | hydroxyl_h | {"O2'"}
    if _remainder(source_graph, dna_stereo, hydrogens) != _remainder(target_graph, rna_stereo, added):
        raise ValueError("Source and canonical parent differ outside the 2′ hydroxyl substitution")
    family, ideal = _coordinates(rna, source=True)
    if family != "SOURCE_IDEAL" or any(n not in ideal for n in elements if elements[n] != "H"):
        raise ValueError("Require complete ideal heavy-atom coordinates for the canonical RNA reference")
    source_family, source_ideal = _coordinates(dna, source=True)
    if source_family != "SOURCE_IDEAL":
        raise ValueError("Require ideal source coordinates to compare the unchanged sugar centres")
    return source_ideal, ideal


def _hydroxyl_position(ideal, host):
    """Intersect the two source bond-angle cones on the side specified by the template."""
    ref = _frame([ideal[n] for n in _C2_FRAME])
    axes = _frame([host[n] for n in _C2_FRAME])
    bond = _sub(ideal["O2'"], ideal["C2'"])
    length = dist(ideal["O2'"], ideal["C2'"])
    if length < .5:
        raise ValueError("Degenerate 2′ hydroxyl reference")
    along = _dot(bond, ref[0]) / length
    ref_c3 = _sub(ideal["C3'"], ideal["C2'"])
    to_c3 = _dot(bond, ref_c3) / (length * dist(ideal["C3'"], ideal["C2'"]))
    host_c3 = _sub(host["C3'"], host["C2'"])
    shared = _dot(host_c3, axes[0]) / dist(host["C3'"], host["C2'"])
    across = (to_c3 - along * shared) / sqrt(1 - shared * shared)
    height_sq = 1 - along * along - across * across
    source_hand = _volume(ideal, "C2'", _C2_NEIGHBORS)
    if height_sq <= 0 or abs(source_hand) < .01 or source_hand * _volume(ideal, "C3'", _C3_NEIGHBORS) <= 0:
        raise ValueError("The source ribose hand and two bond angles must fit the retained sugar")
    above = copysign(sqrt(height_sq), source_hand)
    return tuple(host["C2'"][i] + length * sum(v * axis[i] for v, axis in zip((along, across, above), axes))
                 for i in range(3))


def ribose_parent_seed(data, site, source, before, template, parent):
    graph = source_graph_fragment(source, before)
    source_ideal, ideal = _reference(source, before, template, parent)
    lines, indices, atoms, serial = _model_records(data, site, before)
    phosphate = set(graph["phosphate_atoms"])
    present = atoms.keys() & phosphate
    expected = {n for n, e in graph["elements"].items() if e not in {"H", "D"}} - phosphate
    if (atoms.keys() - present != expected
            or present not in (set(), {"P", "OP1", "OP2"}, {"P", "OP1", "OP2", "OP3"})
            or any(row["element"] != graph["elements"][n] for n, row in atoms.items())):
        raise ValueError("Require a complete source base/sugar and a supported unchanged phosphate")
    host = {n: row["xyz"] for n, row in atoms.items()}
    for center, arms in (("C1'", ("O4'", "C2'", graph["attachment_atom"])),
                         ("C3'", _C3_NEIGHBORS), ("C4'", ("C3'", "O4'", "C5'"))):
        volumes = [_volume(xyz, center, arms) for xyz in (source_ideal, ideal, host)]
        if any(v is None or abs(v) < .01 for v in volumes) or not all(v * volumes[0] > 0 for v in volumes):
            raise ValueError(f"Incompatible or degenerate model/template sugar hand at {center}")
    point = _hydroxyl_position(ideal, host)
    fields = [f"{value:8.3f}" for value in point]
    c2 = atoms["C2'"]["line"]
    occupancy, b_iso = float(c2[54:60]), float(c2[60:66])
    if (serial >= 99999 or any(len(field) != 8 for field in fields)
            or not 0 < occupancy <= 1 or not isfinite(b_iso) or b_iso < 0):
        raise ValueError("Cannot write a 2′ oxygen with the host C2′ occupancy and displacement")
    ending = "\r\n" if c2.endswith("\r\n") else "\n"
    oxygen = (c2[:6] + f"{serial + 1:5d}  O2' " + f"{parent:>3}" + c2[20:30]
              + "".join(fields) + c2[54:76].ljust(22) + " O  " + ending)
    for i in indices:
        original = lines[i]
        lines[i] = original[:17] + f"{parent:>3}" + original[20:]
        if original == c2:
            if not original.endswith(("\n", "\r")):
                lines[i] += ending
            lines[i] += oxygen
    result = "".join(lines).encode("ascii")
    _, _, actual, _ = _model_records(result, site, parent)
    if actual.keys() != atoms.keys() | {"O2'"} or any(actual[n]["xyz"] != host[n] for n in atoms):
        raise ValueError("The serialized RNA parent changed its original atoms")
    new_volume = _volume({n: row["xyz"] for n, row in actual.items()}, "C2'", _C2_NEIGHBORS)
    ref_volume = _volume(ideal, "C2'", _C2_NEIGHBORS)
    if abs(new_volume) < .01 or new_volume * ref_volume <= 0:
        raise ValueError("The serialized 2′ oxygen lost the reference stereochemistry")
    return result, dict(schema_version=1, policy_id=POLICY_ID, status="CANONICAL_RIBOSE_SEED",
        site=site, source_component=before, canonical_component=parent,
        source_sha256=graph["source_sha256"], canonical_dictionary_sha256=sha256(template.read_bytes()).hexdigest(),
        input_model_sha256=sha256(data).hexdigest(), output_model_sha256=sha256(result).hexdigest(),
        added_atom="O2'", retained_atom_count=len(atoms), retained_phosphate=sorted(present),
        coordinate_source="SOURCE_IDEAL", c2_ordered_neighbors=list(_C2_NEIGHBORS),
        reference_c2_volume_A3=ref_volume, written_c2_volume_A3=new_volume,
        occupancy_and_b_from="C2'", native_qualification="NOT_RUN", automatic_adoption=False)
