"""Explicit declared neutral purine representation, without aromaticity perception.

This is a graph/valence whitelist, not a tautomer, protonation or resonance
generator. Source declarations remain authority and numerical checks are separate.
"""
from copy import deepcopy
from math import isfinite

from .cif_doctor import _bridges, _comparison_inventory, _number, _ORDERS

POLICY_ID = "cif-source-declared-neutral-purine-aromatic-v1"

OXO_POLICY_ID = "cif-source-declared-neutral-6-oxo-purine-aromatic-v1"


def validate_policy(policy):
    if policy not in (None, POLICY_ID, OXO_POLICY_ID):
        raise ValueError("Unsupported bond representation policy: " + repr(policy))


def _charges(atoms):
    result = {}
    for atom in atoms:
        fields = atom["declared_charge_fields"]
        tokens = [fields[k] for k in ("charge", "pdbx_formal_charge") if k in fields]
        try:
            values = [_number(token) for token in tokens]
        except (TypeError, ValueError, OverflowError):
            return None
        if not values or any(v is None or not isfinite(v) or not float(v).is_integer() for v in values):
            return None
        if len(set(values)) != 1 or atom["atom_id"] in result:
            return None
        result[atom["atom_id"]] = values[0]
    return result


def _orders(row):
    return {_ORDERS.get(v.upper(), v.upper()) for v in row["declarations"].values()}


def _cycles(edges):
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    if len(adjacency) != 9 or len(edges) != 10:
        return None
    junctions = sorted(n for n, ns in adjacency.items() if len(ns) == 3)
    if len(junctions) != 2 or any(len(ns) != (3 if n in junctions else 2) for n, ns in adjacency.items()):
        return None
    start, end = junctions
    if end not in adjacency[start]:
        return None
    paths = []
    for first in sorted(adjacency[start] - {end}):
        path = [start, first]
        while path[-1] != end:
            options = adjacency[path[-1]] - {path[-2]}
            if len(options) != 1:
                return None
            nxt = next(iter(options))
            if nxt in path or len(path) >= 9:
                return None
            path.append(nxt)
        paths.append(path)
    paths.sort(key=len)
    if [len(p) for p in paths] != [5, 6] or set(paths[0]) & set(paths[1]) != set(junctions):
        return None
    return paths


def purine_bond_representation(source, generated, legacy):
    """Extend the legacy isolated-six-ring result only for the bounded 5/6 graph."""
    result = deepcopy(legacy)
    result.update(policy_id=POLICY_ID, equivalent_fused_systems=[])
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
    stereo = {r["atom_id"]: set() for r in a["atoms"]}
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
        cycles = _cycles(edges)
        if cycles is None:
            continue
        five, six = cycles
        if ([elements.get(n) for n in (five[0], five[-1])] != ["C", "C"]
                or [elements.get(n) for n in five[1:-1]] != ["N", "C", "N"]
                or [elements.get(n) for n in six[1:-1]] not in (["N", "C", "N", "C"], ["C", "N", "C", "N"])
                or any(charges[n] != 0 or not stereo[n] <= {"N"} for n in atoms)):
            continue
        side_edges = {edge for edge in left if set(edge) & atoms} - edges
        if any(frozenset(edge) not in bridges or _orders(left[edge]) != {"SINGLE"}
               or _orders(right[edge]) != {"SINGLE"} for edge in side_edges):
            continue
        doubles = {edge for edge in edges if _orders(left[edge]) == {"DOUBLE"}}
        donors, valid = [], len(doubles) == 4
        for atom in atoms:
            degree = len(adjacency[atom])
            double_count = sum(atom in edge for edge in doubles)
            valence = degree + double_count  # All boundary edges are single.
            if elements[atom] == "C":
                valid &= valence == 4 and double_count == 1
            elif double_count == 0:
                donors.append(atom)
                valid &= degree == 3 and atom in five[1:-1]
            else:
                valid &= valence == 3 and degree == 2 and double_count == 1
        if not valid or len(donors) != 1:
            continue
        covered |= edges
        result["equivalent_fused_systems"].append({"family": "neutral-purine-single-bridge-substituents",
            "atoms": sorted(atoms), "cycle_sizes": [5, 6], "cycles": cycles,
            "source_pyrrolic_nitrogen": donors[0], "bonds": [
                {"atoms": list(edge), "source_order": next(iter(_orders(left[edge]))),
                 "generated_order": "AROMATIC", "source_aromatic_declaration": "Y"} for edge in sorted(edges)]})
    result["unresolved_bonds"] = [list(edge) for edge in sorted(changed - covered)]
    if not result["unresolved_bonds"]:
        result["status"] = "SOURCE_DECLARED_EQUIVALENT"
    return result


def assess_bond_representation(source, generated, legacy, policy):
    """Dispatch explicit policies without widening any historical policy."""
    validate_policy(policy)
    if policy == OXO_POLICY_ID:
        from .cif_oxo_purine_representation import oxo_purine_bond_representation
        return oxo_purine_bond_representation(source, generated, legacy)
    if policy == POLICY_ID:
        return purine_bond_representation(source, generated, legacy)
    return legacy
