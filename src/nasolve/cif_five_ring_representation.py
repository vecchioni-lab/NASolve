"""Explicit neutral five-membered C/N aromatic representation, not perception.

Exactly two localized double bonds and one pyrrolic nitrogen supply the declared
six-electron ring. All hydrogen attachments, charges and boundary single bonds
remain source-owned. This rule supplies neither coordinates nor restraints.
"""
from copy import deepcopy

from .cif_doctor import _bridges, _comparison_inventory
from .cif_purine_representation import FIVE_RING_POLICY_ID, _charges, _orders


def five_ring_bond_representation(source, generated, legacy):
    result = deepcopy(legacy)
    result.update(policy_id=FIVE_RING_POLICY_ID, equivalent_fused_systems=[])
    if result["status"] in {"EXACT", "SOURCE_DECLARED_EQUIVALENT"} or not result["connectivity_unchanged"]:
        return result
    a, b = source["inventory"], generated["inventory"]
    left = {tuple(sorted(r["atoms"])): r for r in a["bond_orders"]}
    right = {tuple(sorted(r["atoms"])): r for r in b["bond_orders"]}
    elements = {r["atom_id"]: r["element"] for r in a["atoms"]}
    other = {r["atom_id"]: r["element"] for r in b["atoms"]}
    charges, other_charges = _charges(a["atoms"]), _charges(b["atoms"])
    if (elements != other or len(elements) != len(a["atoms"]) or len(other) != len(b["atoms"])
            or charges is None or charges != other_charges
            or _comparison_inventory(source)["hydrogen_attachments"] != _comparison_inventory(generated)["hydrogen_attachments"]):
        return result
    changed = {tuple(edge) for edge in result["unresolved_bonds"]}
    eligible = {edge for edge in changed
                if _orders(left[edge]) in ({"SINGLE"}, {"DOUBLE"})
                and _orders(right[edge]) == {"AROMATIC"}
                and set(left[edge]["aromatic_declarations"].values()) == {"Y"}
                and set(right[edge]["aromatic_declarations"].values()) <= {"Y"}
                and all(set(row["stereo_declarations"].values()) <= {"N"} for row in (left[edge], right[edge]))}
    adjacency, eligible_by_atom = {}, {}
    for x, y in left:
        adjacency.setdefault(x, set()).add(y)
        adjacency.setdefault(y, set()).add(x)
    for edge in eligible:
        for atom in edge:
            eligible_by_atom.setdefault(atom, set()).add(edge)
    bridges = _bridges(adjacency)
    stereo = {n: set() for n in elements}
    for atom in a["atoms"] + b["atoms"]:
        stereo[atom["atom_id"]].update(v.upper() for v in atom["stereo_declarations"].values() if v not in {"", ".", "?"})
    remaining, covered = set(eligible), set()
    while remaining:
        pending, atoms, edges = set(min(remaining)), set(), set()
        while pending:
            atom = pending.pop()
            if atom in atoms:
                continue
            atoms.add(atom)
            for edge in eligible_by_atom[atom]:
                edges.add(edge)
                pending.update(set(edge) - atoms)
        remaining -= edges
        if (len(atoms) != 5 or len(edges) != 5
                or any(sum(n in edge for edge in edges) != 2 for n in atoms)
                or any(elements[n] not in {"C", "N"} or charges[n] != 0 or not stereo[n] <= {"N"} for n in atoms)):
            continue
        side_edges = {edge for edge in left if set(edge) & atoms} - edges
        if any(frozenset(edge) not in bridges or _orders(left[edge]) != {"SINGLE"}
               or _orders(right[edge]) != {"SINGLE"} for edge in side_edges):
            continue
        doubles = {edge for edge in edges if _orders(left[edge]) == {"DOUBLE"}}
        donors, valid = [], len(doubles) == 2
        for atom in atoms:
            degree = len(adjacency[atom])
            double_count = sum(atom in edge for edge in doubles)
            if elements[atom] == "C":
                valid &= degree == 3 and double_count == 1
            elif double_count == 0:
                donors.append(atom)
                valid &= degree == 3
            else:
                valid &= degree == 2 and double_count == 1
        if not valid or len(donors) != 1:
            continue
        covered |= edges
        result["equivalent_rings"].append({"family": "neutral-five-membered-cn-single-bridge-substituents",
            "atoms": sorted(atoms), "source_pyrrolic_nitrogen": donors[0], "bonds": [
                {"atoms": list(edge), "source_order": next(iter(_orders(left[edge]))),
                 "generated_order": "AROMATIC", "source_aromatic_declaration": "Y"} for edge in sorted(edges)]})
    result["unresolved_bonds"] = [list(edge) for edge in sorted(changed - covered)]
    if not result["unresolved_bonds"]:
        result["status"] = "SOURCE_DECLARED_EQUIVALENT"
    return result
