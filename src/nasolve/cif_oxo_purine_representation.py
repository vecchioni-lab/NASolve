"""Source-declared five-ring aromatic representation beside a fixed 6-oxo ring.

This structural whitelist does not infer aromaticity, tautomers or protonation.
The old whole-purine policy remains separate and unchanged.
"""
from copy import deepcopy

from .cif_doctor import _bridges, _comparison_inventory
from .cif_purine_representation import OXO_POLICY_ID, _charges, _cycles, _orders


def oxo_purine_bond_representation(source, generated, legacy):
    result = deepcopy(legacy)
    result.update(policy_id=OXO_POLICY_ID, equivalent_fused_systems=[])
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
    adjacency = {}
    for x, y in left:
        adjacency.setdefault(x, set()).add(y)
        adjacency.setdefault(y, set()).add(x)
    bridges = _bridges(adjacency)
    cyclic = {edge for edge in left if frozenset(edge) not in bridges}
    stereo = {r["atom_id"]: set() for r in a["atoms"]}
    for atom in a["atoms"] + b["atoms"]:
        stereo[atom["atom_id"]].update(v.upper() for v in atom["stereo_declarations"].values() if v not in {"", ".", "?"})
    remaining, covered = set(eligible), set()
    while remaining:
        # Expand through non-bridge edges, keeping attached sugar rings separate.
        pending, atoms = set(min(remaining)), set()
        while pending:
            atom = pending.pop()
            if atom in atoms:
                continue
            atoms.add(atom)
            pending.update(n for n in adjacency[atom] if frozenset((atom, n)) not in bridges and n not in atoms)
        edges = {edge for edge in cyclic if set(edge) <= atoms}
        remaining -= {edge for edge in remaining if set(edge) & atoms}
        cycles = _cycles(edges)
        if cycles is None:
            continue
        five, six = cycles
        pattern = [elements[n] for n in six[1:-1]]
        if ([elements[n] for n in (five[0], five[-1])] != ["C", "C"]
                or [elements[n] for n in five[1:-1]] != ["N", "C", "N"]
                or pattern not in (["N", "C", "N", "C"], ["C", "N", "C", "N"])
                or any(charges[n] != 0 or not stereo[n] <= {"N"} for n in atoms)):
            continue
        shared = tuple(sorted((five[0], five[-1])))
        five_edges = {tuple(sorted(e)) for e in zip(five, five[1:])} | {shared}
        if not five_edges <= eligible or _orders(left[shared]) != {"DOUBLE"}:
            continue
        carbon, lactam = (six[-2], six[-3]) if pattern[0] == "N" else (six[1], six[2])
        side_edges = {edge for edge in left if set(edge) & atoms} - edges
        carbonyls = {edge for edge in side_edges if carbon in edge and _orders(left[edge]) == {"DOUBLE"}
                     and all(elements[n] == "O" and charges[n] == 0 and len(adjacency[n]) == 1 for n in set(edge) - {carbon})}
        if len(carbonyls) != 1:
            continue
        carbonyl = next(iter(carbonyls))
        fixed = (edges - five_edges) | side_edges
        if any(_orders(left[edge]) != _orders(right[edge])
               or not set(left[edge]["aromatic_declarations"].values()) <= {"N"}
               or not set(right[edge]["aromatic_declarations"].values()) <= {"N"}
               or any(not set(row["stereo_declarations"].values()) <= {"N"} for row in (left[edge], right[edge])) for edge in fixed):
            continue
        if any(frozenset(edge) not in bridges or _orders(left[edge]) != ({"DOUBLE"} if edge == carbonyl else {"SINGLE"}) for edge in side_edges):
            continue
        all_incident = edges | side_edges
        if any(_orders(left[edge]) not in ({"SINGLE"}, {"DOUBLE"}) for edge in all_incident):
            continue
        doubles = {edge for edge in all_incident if _orders(left[edge]) == {"DOUBLE"}}
        donors, valid = [], len(doubles & five_edges) == 2
        for atom in atoms:
            degree = len(adjacency[atom])
            double_count = sum(atom in edge for edge in doubles)
            if elements[atom] == "C":
                valid &= degree + double_count == 4
            elif atom == lactam:
                valid &= degree == 3 and double_count == 0
            elif double_count == 0:
                donors.append(atom)
                valid &= degree == 3 and atom in five[1:-1]
            else:
                valid &= degree == 2 and double_count == 1
        if not valid or len(donors) != 1:
            continue
        covered |= five_edges
        result["equivalent_fused_systems"].append({"family": "neutral-6-oxo-purine-five-ring",
            "atoms": sorted(atoms), "cycle_sizes": [5, 6], "cycles": cycles,
            "source_pyrrolic_nitrogen": donors[0], "source_lactam_nitrogen": lactam,
            "unchanged_carbonyl": list(carbonyl), "bonds": [
                {"atoms": list(edge), "source_order": next(iter(_orders(left[edge]))),
                 "generated_order": "AROMATIC", "source_aromatic_declaration": "Y"} for edge in sorted(five_edges)]})
    result["unresolved_bonds"] = [list(edge) for edge in sorted(changed - covered)]
    if not result["unresolved_bonds"]:
        result["status"] = "SOURCE_DECLARED_EQUIVALENT"
    return result
