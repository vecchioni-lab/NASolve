"""Compare source and effective CIF assessments, including optional stereochemical checks."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Sequence

from . import cif_doctor as assessor
from .cif_doctor import POLICY_ID, _MISSING, _ORDERS, _finding, _number, _status


def _comparison_inventory(component: dict) -> dict:
    inventory = component["inventory"]
    atom_elements = {atom["atom_id"]: atom["element"] for atom in inventory["atoms"]}
    charges = {atom["atom_id"]: {key: None if value in _MISSING else value
                for key, value in atom["declared_charge_fields"].items()} for atom in inventory["atoms"]}
    stereo = {atom["atom_id"]: {key: None if value in _MISSING else value
               for key, value in atom["stereo_declarations"].items()} for atom in inventory["atoms"]}
    bonds = {}
    aromatic = {}
    bond_stereo = {}
    for row in inventory["bond_orders"]:
        pair = tuple(sorted(row["atoms"]))
        bonds[pair] = sorted({_ORDERS.get(value.upper(), value.upper()) for value in row["declarations"].values()})
        aromatic[pair] = sorted(set(row["aromatic_declarations"].values()))
        bond_stereo[pair] = row["stereo_declarations"]
    chirality = []
    for row in inventory["chirality"]:
        if len(row["atoms"]) != 4:
            continue
        centre, *neighbors = row["atoms"]
        sign = row["volume_sign"]
        if sign in {"positive", "positiv", "negative", "negativ"}:
            inversions = sum(neighbors[i] > neighbors[j] for i in range(3) for j in range(i + 1, 3))
            parity = (1 if sign.startswith("pos") else -1) * (-1 if inversions % 2 else 1)
            sign = "positive" if parity > 0 else "negative"
        chirality.append((centre, tuple(sorted(neighbors)), sign))
    return {"atom_elements": atom_elements, "declared_charge_fields": charges,
            "energy_types": {atom["atom_id"]: atom.get("type_energy") for atom in inventory["atoms"]},
            "atom_stereo_declarations": stereo, "bond_orders": bonds,
            "bond_aromatic_declarations": aromatic, "bond_stereo_declarations": bond_stereo,
            "hydrogen_attachments": {row["atom_id"]: row["neighbors"] for row in inventory["hydrogen_attachments"]},
            "signed_chirality": sorted(chirality),
            "numerical_restraints": inventory["numerical_restraints"]}


def _comparison_value(value):
    if isinstance(value, dict):
        return {"|".join(key) if isinstance(key, tuple) else key: _comparison_value(item)
                for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_comparison_value(item) for item in value]
    return value


def _positive_esd(value):
    try:
        sigma = _number(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return sigma if sigma is not None and sigma > 0 else None


def source_stereocentre_conflicts(source_components: Sequence[dict], effective_components: Sequence[dict], *,
                                 planes: bool, bonds: bool) -> list[dict]:
    """Compare local restraints at a source-declared, four-single-bond carbon."""
    if not source_components or not effective_components:
        return []
    sides = []
    for components in (source_components, effective_components):
        definitions = defaultdict(dict)
        for component in components:
            definitions[component["component_id"]][component["definition_sha256"]] = component
        sides.append({code: next(iter(rows.values())) for code, rows in definitions.items()
                      if len(rows) == 1})
    source, effective = sides
    findings = []
    for code in sorted(source.keys() & effective.keys()):
        left, right = source[code], effective[code]
        if left["verdicts"]["graph"] != "PASS" or right["verdicts"]["graph"] != "PASS":
            continue
        findings.extend(_component_stereo_conflicts(code, left, right, planes=planes, bonds=bonds))
    return findings


def _matching_tetrahedral_carbons(original, returned):
    graphs = []
    for part in (original, returned):
        neighbors = defaultdict(set)
        for a, b in part["bond_orders"]:
            neighbors[a].add(b)
            neighbors[b].add(a)
        graphs.append(neighbors)
    source_graph, returned_graph = graphs
    for centre, bonded in sorted(source_graph.items()):
        if original["atom_elements"][centre].upper() != "C" or len(bonded) != 4:
            continue
        hands = {v.upper() for v in original["atom_stereo_declarations"][centre].values() if v}
        if hands not in ({"R"}, {"S"}):
            continue
        edges = {tuple(sorted((centre, atom))) for atom in bonded}
        if any(original["bond_orders"][e] != ["SINGLE"]
               or set(original["bond_aromatic_declarations"][e]) - {"N", "NO"} for e in edges):
            continue
        heavy = {a: original["atom_elements"][a].upper() for a in bonded
                 if original["atom_elements"][a].upper() not in {"H", "D"}}
        returned_heavy = {a: returned["atom_elements"][a].upper() for a in returned_graph[centre]
                          if returned["atom_elements"][a].upper() not in {"H", "D"}}
        if (returned["atom_elements"].get(centre, "").upper() != "C" or
                len(heavy) < 3 or heavy != returned_heavy):
            continue
        yield centre, next(iter(hands)), heavy.keys()


def _component_stereo_conflicts(code, source, effective, *, planes, bonds):
    inventory = effective["inventory"]["numerical_restraints"]
    members_by_plane = defaultdict(dict)
    if planes:
        for row in inventory["plane_atom"]:
            sigma = _positive_esd(row.get("dist_esd"))
            if sigma is not None:
                members_by_plane[row["plane_id"]][row["atom_id"]] = sigma
    if not members_by_plane and not bonds:
        return []
    widths = {tuple(sorted((row["atom_id_1"], row["atom_id_2"]))):
              _positive_esd(row.get("value_dist_esd")) for row in inventory["bond"]}
    original, returned = _comparison_inventory(source), _comparison_inventory(effective)
    aromatic_edges = defaultdict(dict)
    findings = []
    pins = dict(source_definition_sha256=source["definition_sha256"],
                effective_definition_sha256=effective["definition_sha256"])
    for centre, hand, heavy in _matching_tetrahedral_carbons(original, returned):
        if bonds:
            for neighbor in heavy:
                edge = tuple(sorted((centre, neighbor)))
                orders = set(returned["bond_orders"][edge])
                flags = set(returned["bond_aromatic_declarations"][edge])
                if (orders == {"AROMATIC"} and flags <= {"Y", "YES"}) or (
                        flags and flags <= {"Y", "YES"} and len(orders) <= 1
                        and orders <= {"SINGLE", "DOUBLE", "DELOCALIZED"}):
                    aromatic_edges[edge][centre] = hand
        for plane, members in sorted(members_by_plane.items()):
            neighbors = sorted(heavy & members.keys())
            if centre not in members or len(neighbors) < 3:
                continue
            bond_esds = {a: widths.get(tuple(sorted((a, centre)))) for a in neighbors}
            # Only quarantine an explicit quartet whose plane widths are at least
            # as tight as all three local bond widths. Looser terms are report-only.
            tight = any(all(bond_esds[a] is not None for a in trio)
                        and max(members[a] for a in (centre, *trio))
                        <= min(bond_esds[a] for a in trio) for trio in combinations(neighbors, 3))
            findings.append({"component_id": code, **_finding("PLANE-02", "REVIEW",
                "plane-through-source-stereocentre",
                f"Plane {plane} restrains source tetrahedral {centre} and three or more bonded heavy neighbors.",
                plane=plane, centre=centre, source_hand=hand, bonded_heavy_neighbors=neighbors,
                plane_esds_angstrom={a: members[a] for a in (centre, *neighbors)},
                bond_esds_angstrom=bond_esds, plane_as_tight_as_local_bonds=tight,
                **pins)})
    for edge, centres in sorted(aromatic_edges.items()):
        findings.append({"component_id": code, **_finding("CHEM-02", "REVIEW",
            "aromatic-bond-at-source-stereocentre",
            f"The generated aromatic bond {'–'.join(edge)} meets a source tetrahedral carbon.",
            atoms=list(edge), source_stereocentres=centres, source_order="SINGLE",
            effective_orders=returned["bond_orders"][edge],
            effective_aromatic_flags=returned["bond_aromatic_declarations"][edge], **pins)})
    return findings


def compare_dictionaries(source_paths: Sequence[Path], effective_paths: Sequence[Path], *,
                         compare_stereo_planes: bool = False, compare_stereo_bonds: bool = False) -> dict:
    """Compare explicit same-ID declarations without deciding which is correct.

    Labels are never treated as aliases. Site deletions/link modifications and
    tautomer/protonation transformations need separate declared policies.
    """
    source = assessor.assess_dictionaries(source_paths, stage="source")
    effective = assessor.assess_dictionaries(effective_paths, stage="effective")
    grouped = []
    for receipt in (source, effective):
        by_code: dict[str, list[dict]] = defaultdict(list)
        for component in receipt["components"]:
            by_code[component["component_id"]].append(component)
        grouped.append(by_code)
    left, right = grouped
    differences = []
    findings = []
    compared = []
    for code in sorted(left.keys() | right.keys()):
        if code not in left or code not in right:
            findings.append({"component_id": code, **_finding("CHEM-01", "UNSUPPORTED", "component-unpaired",
                             "Component identity is absent on one side; no alias or chemical mapping is inferred.",
                             present_in_source=code in left, present_in_effective=code in right)})
            continue
        if any(len({row["definition_sha256"] for row in side[code]}) > 1 for side in (left, right)):
            findings.append({"component_id": code, **_finding("PROV-01", "REVIEW", "ambiguous-comparison-definition",
                             "One side contains differing definitions of the component; precedence must be declared.")})
            continue
        source_inventory = _comparison_inventory(left[code][0])
        effective_inventory = _comparison_inventory(right[code][0])
        changed = []
        for field in sorted(source_inventory):
            if source_inventory[field] != effective_inventory[field]:
                changed.append(field)
                differences.append({"component_id": code, "field": field,
                                    "source": _comparison_value(source_inventory[field]),
                                    "effective": _comparison_value(effective_inventory[field])})
        compared.append(code)
        findings.append({"component_id": code, **_finding("CHEM-01", "REVIEW" if changed else "PASS",
                         "component-declarations-differ" if changed else "component-declarations-match",
                         "Same-ID declarations differ; neither source is assumed correct."
                         if changed else "Same-ID graph and declared chemical fields match within the assessed inventory.",
                         changed_fields=changed, limitations=["Partial charge and declared charge fields stay separate.",
                                                             "Missing charge stays unknown; no protonation or pH is assigned.",
                                                             "Signed volume declarations are not absolute CIP labels."])})
    if compare_stereo_planes or compare_stereo_bonds:
        findings.extend(source_stereocentre_conflicts(source["components"], effective["components"],
                        planes=compare_stereo_planes, bonds=compare_stereo_bonds))
    invalid = source["status"] == "INVALID" or effective["status"] == "INVALID"
    integrity = "UNCHANGED"
    for receipt, paths in ((source, source_paths), (effective, effective_paths)):
        for descriptor, path in zip(receipt["inputs"], paths):
            if descriptor.get("sha256") is None:
                continue
            try:
                unchanged = assessor._descriptor(Path(path), descriptor["role"])["sha256"] == descriptor["sha256"]
            except OSError:
                unchanged = False
            if not unchanged:
                invalid = True
                integrity = "CHANGED_DURING_ASSESSMENT"
                findings.append(_finding("PROV-01", "ERROR", "comparison-input-changed",
                                         "Comparison input changed between or after its component assessments.",
                                         role="source" if receipt is source else "effective", input_index=descriptor["input_index"]))
    status = "INVALID" if invalid else _status(findings, assessed=bool(compared))
    if status == "PASS" and (source["status"] == "REVIEW" or effective["status"] == "REVIEW"):
        status = "REVIEW"
    if status == "PASS" and findings and any(finding["code"] == "component-unpaired" for finding in findings):
        status = "REVIEW"
    return {"schema_version": 1, "audit_kind": "cif_restraint_comparison", "policy_id": POLICY_ID,
            **({"source_bond_comparison_policy": "explicit-four-single-bond-carbon-v1"} if compare_stereo_bonds else {}),
            **({"source_plane_comparison_policy": "explicit-four-single-bond-carbon-v1"} if compare_stereo_planes else {}),
            "status": status, "source_assessment": source, "effective_assessment": effective,
            "differences": differences, "findings": findings, "compared_components": compared,
            "comparison_scope_complete": not any(f["code"] in {"component-unpaired", "ambiguous-comparison-definition"} for f in findings),
            "input_integrity": "UNCHANGED" if integrity == source["input_integrity"] == effective["input_integrity"] == "UNCHANGED"
            else "CHANGED_DURING_ASSESSMENT",
            "limitations": ["No alias, atom remapping, source authority or site-linked modification is inferred.",
                            "Graph agreement does not validate numerical restraints, native proxies or geometry."]}
