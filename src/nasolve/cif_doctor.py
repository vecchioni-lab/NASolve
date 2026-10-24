"""Deterministic, read-only component graph and restraint assessment.

This inventory is neither chemical approval nor native Phenix interpretation.
It preserves exact atom identifiers, separates missing data from numeric zero,
and reports candidate conflicts without inventing replacement chemistry.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from itertools import combinations
import json
from math import acos, cos, isfinite, pi, sqrt
from pathlib import Path
import re
import sys
from typing import Mapping, Sequence

from Bio import __version__ as BIOPYTHON_VERSION

from .dictionary_compatibility import normalize_torsion_block
from .ligand_profiles import _blocks

POLICY_ID = "cif-doctor-graph-numerics-v2"
_MISSING = {"", ".", "?"}
_NUMBER = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:\(\d+\))?$")
_ORDERS = {"SINGLE": "SINGLE", "SING": "SINGLE", "DOUBLE": "DOUBLE",
           "DOUB": "DOUBLE", "TRIPLE": "TRIPLE", "TRIP": "TRIPLE",
           "AROMATIC": "AROMATIC", "AROM": "AROMATIC", "DELOC": "DELOCALIZED",
           "DELOCALIZED": "DELOCALIZED"}


def json_canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _number(value: str | None) -> float | None:
    if value is None or value in _MISSING:
        return None
    match = _NUMBER.fullmatch(value)
    result = float(match.group(1)) if match else float(value)
    if not isfinite(result):
        raise ValueError("non-finite number")
    return result


def _descriptor(path: Path, role: str, index: int | None = None) -> dict:
    payload = path.read_bytes()
    result = {"name": path.name, "sha256": sha256(payload).hexdigest(),
              "size": len(payload), "role": role}
    if index is not None:
        result["input_index"] = index
    return result


def _cif_tokens(text: str):
    """CIF1 lexical preflight with quoted/text values kept distinct from tags."""
    lines = iter(text.splitlines())
    for line in lines:
        if line.startswith(";"):
            content = [line[1:]]
            for continuation in lines:
                if continuation.startswith(";"):
                    line = continuation[1:]
                    break
                content.append(continuation)
            else:
                raise ValueError("unterminated semicolon text")
            yield "\n".join(content), True
        cursor = 0
        while cursor < len(line):
            if line[cursor].isspace():
                cursor += 1
                continue
            if line[cursor] == "#":
                break
            if line[cursor] in {"'", '"'}:
                quote = line[cursor]
                start = cursor + 1
                cursor = start
                while cursor < len(line):
                    if line[cursor] == quote and (cursor + 1 == len(line) or line[cursor + 1].isspace()):
                        break
                    cursor += 1
                if cursor == len(line):
                    raise ValueError("unterminated quoted token")
                yield line[start:cursor], True
                cursor += 1
            else:
                start = cursor
                while cursor < len(line) and not line[cursor].isspace():
                    cursor += 1
                yield line[start:cursor], False


def _duplicate_tags(text: str) -> list[str]:
    seen = set()
    duplicates = set()
    for token, quoted in _cif_tokens(text):
        if not quoted and (token.lower().startswith("save_") or token.lower() == "global_"):
            raise ValueError("unsupported save/global CIF layout")
        if not quoted and token.startswith("_"):
            name = token.lower()
            if name in seen:
                duplicates.add(name)
            seen.add(name)
    return sorted(duplicates)


def _finding(rule: str, status: str, code: str, message: str, **measurements) -> dict:
    return {"rule_id": rule, "status": status, "code": code,
            "message": message, "measurements": measurements}


def _status(findings: Sequence[dict], *, assessed: bool = True) -> str:
    states = {finding["status"] for finding in findings}
    if states & {"FAIL", "ERROR"}:
        return "INVALID"
    if "REVIEW" in states:
        return "REVIEW"
    return "PASS" if assessed else "UNASSESSED"


def _rows(values: Mapping, category: str, findings: list[dict]) -> list[dict[str, str]]:
    prefix = category + "."
    columns = {key[len(prefix):]: value for key, value in values.items()
               if key.startswith(prefix)}
    if not columns:
        return []
    if any(not isinstance(column, list) for column in columns.values()):
        findings.append(_finding("GRAPH-01", "ERROR", "unsupported-category-layout",
                                 "Category columns are not lists.", category=category))
        return []
    lengths = {len(column) for column in columns.values()}
    if len(lengths) != 1:
        findings.append(_finding("GRAPH-01", "ERROR", "inconsistent-category-lengths",
                                 "Category columns have different row counts.",
                                 category=category, lengths=sorted(lengths)))
        return []
    return [{key: str(column[index]) for key, column in columns.items()}
            for index in range(next(iter(lengths)))]


def _bridges(adjacency: Mapping[str, set[str]]) -> set[frozenset[str]]:
    """Iterative linear-time bridge inventory; no cycle enumeration."""
    entered: dict[str, int] = {}
    low: dict[str, int] = {}
    result: set[frozenset[str]] = set()
    for root in sorted(adjacency):
        if root in entered:
            continue
        entered[root] = low[root] = len(entered)
        stack = [(root, None, iter(sorted(adjacency[root])))]
        while stack:
            node, parent, neighbors = stack[-1]
            child = next(neighbors, None)
            if child is None:
                stack.pop()
                if parent is not None:
                    low[parent] = min(low[parent], low[node])
                    if low[node] > entered[parent]:
                        result.add(frozenset((node, parent)))
            elif child != parent:
                if child in entered:
                    low[node] = min(low[node], entered[child])
                else:
                    entered[child] = low[child] = len(entered)
                    stack.append((child, node, iter(sorted(adjacency[child]))))
    return result


def _numeric(row: Mapping[str, str], field: str, findings: list[dict], *,
             category: str, row_index: int, positive: bool = False,
             bounds: tuple[float, float] | None = None,
             integer: bool = False) -> float | None:
    raw = row.get(field)
    references = {"atoms": [row.get("atom_id_1", "?"), row.get("atom_id_2", "?")]} if category == "bond" else {}
    try:
        number = _number(raw)
    except (ValueError, TypeError, OverflowError):
        findings.append(_finding("NUM-01", "FAIL", "invalid-numeric-value",
                                 "An explicitly supplied numerical parameter is unusable.",
                                 category=category, row=row_index, field=field, value=raw, **references))
        return None
    if number is None:
        return None
    if ((positive and number <= 0) or (integer and not number.is_integer())
            or (bounds is not None and not bounds[0] <= number <= bounds[1])):
        findings.append(_finding("NUM-01", "FAIL", "numeric-domain-violation",
                                 "A numerical parameter violates its mathematical domain.",
                                 category=category, row=row_index, field=field, value=raw, **references))
        return None
    return number


def _dictionary_geometry(atom_rows: Sequence[dict[str, str]],
                         bond_rows: Sequence[dict[str, str]], *, graph_only: bool,
                         findings: list[dict]) -> dict:
    """Check exact heavy-atom bond degeneracy in explicit numerical candidates.

    This is a bounded linear scan of dictionary coordinates, never a model
    geometry/chemical identity assessment. Graph-only supplier coordinates may
    be placeholders and therefore cannot fail this numerical-candidate check.
    No distance threshold, inferred axes, or replacement target is introduced.
    """
    families = {"atom_xyz": ("x", "y", "z"),
                "supplier_ideal": tuple("pdbx_model_cartn_" + axis + "_ideal" for axis in "xyz")}
    limitations = ["Only exact equality on declared heavy-atom bonds is tested.",
                   "This does not validate other bond lengths, chemical identity or achieved model geometry."]
    inventory = {"status": "UNASSESSED", "coordinate_sets": [],
                 "checked_heavy_bonds": 0, "comparison": "exact-coordinate-equality",
                 "limitations": limitations}
    if graph_only:
        inventory["reason"] = "graph-only-source-coordinates"
        return inventory
    if not any(row.get(field, "?") not in _MISSING for row in bond_rows
               for field in ("value_dist", "value_dist_nucleus")):
        inventory["reason"] = "no-explicit-bond-distance-targets"
        return inventory
    if len(atom_rows) > 10000 or len(bond_rows) > 50000:
        inventory["reason"] = "assessment-size-bound"
        findings.append(_finding("NUM-01", "UNSUPPORTED", "dictionary-coordinate-assessment-bounded",
                                 "Dictionary coordinate assessment exceeds its explicit size bound.",
                                 atom_count=len(atom_rows), bond_count=len(bond_rows),
                                 maximum_atoms=10000, maximum_bonds=50000))
        return inventory
    names = [row.get("atom_id", "?") for row in atom_rows]
    if len(set(names)) != len(names) or any(name in _MISSING for name in names):
        inventory["reason"] = "ambiguous-atom-identifiers"
        return inventory
    heavy = {row["atom_id"]: row for row in atom_rows
             if row.get("type_symbol", "?").upper() not in {"H", "D", "?", ".", ""}}
    if not heavy or any(row.get("type_symbol", "?") in _MISSING for row in atom_rows):
        inventory["reason"] = "unassessed-heavy-atom-inventory"
        return inventory
    supplied = {key for row in atom_rows for key in row}
    supported = [(name, fields) for name, fields in families.items() if supplied.intersection(fields)]
    if not supported:
        coordinate_fields = sorted(key for key in supplied if "cartn" in key or "coordinate" in key)
        inventory["reason"] = "unsupported-coordinate-fields" if coordinate_fields else "no-coordinate-fields"
        findings.append(_finding("NUM-01", "UNSUPPORTED" if coordinate_fields else "NOT_RUN",
                                 "dictionary-coordinates-unassessed",
                                 "No supported, explicitly supplied dictionary coordinate triplet is available.",
                                 supplied_coordinate_fields=coordinate_fields,
                                 supported_coordinate_fields=[list(fields) for fields in families.values()]))
        return inventory
    local_findings = []
    assessed = 0
    for name, fields in supported:
        coordinates: dict[str, tuple[Decimal, ...]] = {}
        missing, invalid = [], []
        for atom, row in heavy.items():
            triplet = []
            for field in fields:
                raw = row.get(field)
                if raw is None or raw in _MISSING:
                    missing.append({"atom_id": atom, "field": field})
                    continue
                try:
                    _number(raw)  # finite, usable numeric representation
                    match = _NUMBER.fullmatch(raw)
                    triplet.append(Decimal(match.group(1) if match else raw))
                except (ValueError, TypeError, OverflowError, InvalidOperation):
                    invalid.append({"atom_id": atom, "field": field, "value": raw})
            if len(triplet) == 3:
                coordinates[atom] = tuple(triplet)
        record = {"coordinate_set": name, "fields": list(fields),
                  "status": "UNASSESSED", "checked_heavy_bonds": 0}
        inventory["coordinate_sets"].append(record)
        if missing or invalid:
            record.update({"missing": missing, "invalid": invalid})
            local_findings.append(_finding("NUM-01", "UNSUPPORTED", "dictionary-coordinates-unassessed",
                                           "The supplied coordinate set lacks complete finite heavy-atom coordinates.",
                                           coordinate_set=name, fields=list(fields), missing=missing, invalid=invalid))
            continue
        assessed += 1
        collisions = 0
        for row_index, row in enumerate(bond_rows):
            refs = (row.get("atom_id_1"), row.get("atom_id_2"))
            if refs[0] == refs[1] or any(atom not in coordinates for atom in refs):
                continue
            record["checked_heavy_bonds"] += 1
            inventory["checked_heavy_bonds"] += 1
            if coordinates[refs[0]] == coordinates[refs[1]]:
                collisions += 1
                local_findings.append(_finding("NUM-01", "FAIL", "coincident-bonded-heavy-atoms",
                                               "Bonded heavy atoms have exactly identical dictionary coordinates; the numerical candidate is degenerate.",
                                               category="bond", row=row_index, atoms=list(refs),
                                               coordinate_set=name, fields=list(fields),
                                               coordinates=[float(value) for value in coordinates[refs[0]]],
                                               distance=0.0, comparison="exact-coordinate-equality",
                                               limitations=limitations))
        record["status"] = "INVALID" if collisions else "PASS"
    findings.extend(local_findings)
    if assessed:
        inventory["status"] = _status(local_findings)
    return inventory


def _references(row: Mapping[str, str], fields: Sequence[str], atoms: set[str],
                findings: list[dict], category: str, index: int) -> tuple[str, ...] | None:
    refs = tuple(row.get(field, "?") for field in fields)
    missing = [atom for atom in refs if atom not in atoms]
    if missing:
        findings.append(_finding("GRAPH-01", "FAIL", "dangling-atom-reference",
                                 "A restraint references an absent exact atom identifier.",
                                 category=category, row=index, atoms=list(refs), missing=missing))
        return None
    if len(set(refs)) != len(refs):
        findings.append(_finding("GRAPH-01", "FAIL", "repeated-restraint-atom",
                                 "A restraint repeats an atom within its defining references.",
                                 category=category, row=index, atoms=list(refs)))
        return None
    return refs


def _rounding_halfwidth(token: str) -> float:
    match = _NUMBER.fullmatch(token)
    if not match:
        return 0.0
    mantissa, _, exponent = match.group(1).lower().partition("e")
    digits = len(mantissa.partition(".")[2]) if "." in mantissa else 0
    power = int(exponent or "0") - digits
    return 0.5 * 10 ** max(-300, min(300, power))


def _gram(angles: Sequence[float]) -> dict:
    x, y, z = (cos(angle * pi / 180) for angle in angles)
    determinant = 1 + 2 * x * y * z - x * x - y * y - z * z
    scale = sqrt((x * x + y * y + z * z) / 3)
    if scale < 1e-16:
        eigenvalues = [1.0, 1.0, 1.0]
    else:
        phase = acos(max(-1.0, min(1.0, x * y * z / scale ** 3))) / 3
        eigenvalues = sorted([1 + 2 * scale * cos(phase + 2 * k * pi / 3)
                              for k in range(3)])
    tolerance = 1e-10
    return {"determinant": determinant, "eigenvalues": eigenvalues,
            "positive_semidefinite": min(eigenvalues) >= -tolerance,
            "rank": sum(abs(value) > tolerance for value in eigenvalues),
            "algebra_tolerance": tolerance}


def _plane_checks(planes: Mapping[str, set[str]], adjacency: Mapping[str, set[str]],
                  angles: Sequence[dict[str, str]], findings: list[dict]) -> int:
    by_centre: dict[str, dict[frozenset[str], list[tuple[float, float, str]]]] = defaultdict(
        lambda: defaultdict(list))
    for row in angles:
        try:
            target = _number(row.get("value_angle"))
            sigma = _number(row.get("value_angle_esd"))
        except (ValueError, TypeError, OverflowError):
            continue
        if target is not None and sigma is not None and 0 <= target <= 180 and sigma > 0:
            by_centre[row.get("atom_id_2", "?")][frozenset(
                (row.get("atom_id_1", "?"), row.get("atom_id_3", "?")))].append(
                    (target, sigma, row["value_angle"]))
    checked = 0
    seen = set()
    for plane, members in sorted(planes.items()):
        for centre in sorted(members):
            neighbors = sorted(adjacency.get(centre, set()) & members)
            # Covalent degrees are small. Bound unusual coordination explicitly.
            if len(neighbors) > 12:
                findings.append(_finding("PLANE-01", "UNSUPPORTED", "high-degree-plane-centre",
                                         "Plane compatibility combinations exceed the supported degree.",
                                         plane=plane, centre=centre, degree=len(neighbors)))
                continue
            for trio in combinations(neighbors, 3):
                key = (centre, trio)
                if key in seen:
                    continue
                seen.add(key)
                terms = [by_centre[centre].get(frozenset(pair), [])
                         for pair in combinations(trio, 2)]
                if any(len(term) != 1 for term in terms):
                    continue
                data = [term[0] for term in terms]
                targets = [term[0] for term in data]
                gram = _gram(targets)
                total = sum(targets)
                interior = abs(total - 360)
                exterior = abs(2 * max(targets) - total)
                rounding = sum(_rounding_halfwidth(term[2]) for term in data)
                rounded_compatible = min(interior, exterior) <= rounding + 1e-9
                status = "PASS" if rounded_compatible else "REVIEW"
                checked += 1
                findings.append(_finding("PLANE-01", status, "plane-angle-compatibility",
                                         "Central angle targets are compatible within displayed rounding."
                                         if rounded_compatible else
                                         "Exact central angle targets and the shared plane conflict; material strain is uncalibrated.",
                                         plane=plane, centre=centre, neighbors=list(trio),
                                         angles_degrees=targets, angle_esds=[term[1] for term in data],
                                         interior_branch_delta_degrees=interior,
                                         exterior_branch_delta_degrees=exterior,
                                         displayed_rounding_bound_degrees=rounding,
                                         rounded_planar_compatible=rounded_compatible,
                                         sigma_adjustment_lower_bound=min(interior, exterior) /
                                         sqrt(sum(term[1] ** 2 for term in data)),
                                         **gram, limitations=["Finite plane weights and correlations are excluded.",
                                                             "No calibrated source-defect threshold or replacement angles."]))
    return checked


def _component(code: str, index: int, block: str, tables: Mapping[str, list[dict]],
               initial: Sequence[dict], stage: str) -> dict:
    findings = list(initial)
    atom_rows = tables.get("atom", [])
    names = [row.get("atom_id", "?") for row in atom_rows]
    atoms = set(names) - _MISSING
    duplicate_atoms = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicate_atoms or len(atoms) != len(set(names)):
        findings.append(_finding("GRAPH-01", "FAIL", "invalid-atom-identifiers",
                                 "Atom identifiers must be present and unique, preserving primes.",
                                 duplicates=duplicate_atoms, missing=sum(name in _MISSING for name in names)))
    elements = {row.get("atom_id"): row.get("type_symbol", "?") for row in atom_rows}
    missing_elements = sorted(name for name, symbol in elements.items() if symbol in _MISSING)
    if missing_elements:
        findings.append(_finding("GRAPH-01", "REVIEW", "missing-atom-elements",
                                 "Some atom elements are unspecified.", atoms=missing_elements))
    adjacency: dict[str, set[str]] = {atom: set() for atom in atoms}
    bond_rows = tables.get("bond", [])
    seen_bonds: dict[frozenset[str], dict] = {}
    bond_orders = []
    aromatic_bonds = []
    missing_orders = []
    missing_bond_targets = []
    for row_index, row in enumerate(bond_rows):
        refs = _references(row, ("atom_id_1", "atom_id_2"), atoms,
                           findings, "bond", row_index)
        if refs:
            pair = frozenset(refs)
            if pair in seen_bonds:
                findings.append(_finding("GRAPH-01", "FAIL", "duplicate-bond",
                                         "More than one component bond row defines the same atom pair.",
                                         row=row_index, atoms=list(refs)))
            seen_bonds[pair] = row
            adjacency[refs[0]].add(refs[1])
            adjacency[refs[1]].add(refs[0])
        declarations = {field: row[field] for field in ("type", "value_order")
                        if row.get(field, "?") not in _MISSING}
        normalized = {_ORDERS.get(value.upper(), value.upper()) for value in declarations.values()}
        if len(normalized) > 1:
            findings.append(_finding("CHEM-01", "REVIEW", "conflicting-bond-orders",
                                     "Explicit bond order fields disagree.", row=row_index, declarations=declarations))
        if not declarations:
            missing_orders.append(row_index)
        elif any(value not in set(_ORDERS.values()) for value in normalized):
            findings.append(_finding("CHEM-01", "UNSUPPORTED", "unsupported-bond-order",
                                     "Bond order representation is retained without interpretation.",
                                     row=row_index, declarations=declarations))
        aromatic = {field: row[field].upper() for field in ("aromatic", "pdbx_aromatic_flag")
                    if row.get(field, "?") not in _MISSING}
        bond_orders.append({"atoms": list(refs or ()), "declarations": declarations,
                            "aromatic_declarations": aromatic,
                            "stereo_declarations": {field: row[field] for field in
                            ("pdbx_stereo_config", "stereo_config") if field in row}})
        if len(set(aromatic.values())) > 1:
            findings.append(_finding("CHEM-01", "REVIEW", "conflicting-aromatic-flags",
                                     "Explicit aromatic flag fields disagree.", row=row_index, declarations=aromatic))
        if "Y" in aromatic.values() and refs:
            aromatic_bonds.append(refs)
        if "AROMATIC" in normalized and "N" in aromatic.values():
            findings.append(_finding("CHEM-01", "REVIEW", "aromatic-order-flag-conflict",
                                     "An aromatic order is accompanied by an explicit nonaromatic flag.", row=row_index))
        for field in ("value_dist", "value_dist_esd", "value_dist_nucleus", "value_dist_nucleus_esd"):
            if field in row or field in {"value_dist", "value_dist_esd"}:
                value = _numeric(row, field, findings, category="bond", row_index=row_index, positive=True)
                if value is None and field in {"value_dist", "value_dist_esd"}:
                    missing_bond_targets.append({"row": row_index, "field": field})
    if missing_orders:
        findings.append(_finding("CHEM-01", "REVIEW", "missing-bond-orders",
                                 "Bond orders are unspecified; they are not inferred from coordinates.", rows=missing_orders))
    bridges = _bridges(adjacency)
    for refs in aromatic_bonds:
        if frozenset(refs) in bridges:
            findings.append(_finding("CHEM-01", "REVIEW", "aromatic-bridge-bond",
                                     "An explicitly aromatic bond is outside every graph cycle.", atoms=list(refs),
                                     limitations=["No aromaticity model or replacement order is assigned."]))
    angles = tables.get("angle", [])
    missing_angle_targets = []
    for row_index, row in enumerate(angles):
        refs = _references(row, ("atom_id_1", "atom_id_2", "atom_id_3"), atoms,
                           findings, "angle", row_index)
        if refs and any(frozenset(pair) not in seen_bonds for pair in zip(refs, refs[1:])):
            findings.append(_finding("NUM-01", "FAIL", "unbonded-angle-path",
                                     "A component bond-angle row does not follow two declared bonds.",
                                     row=row_index, atoms=list(refs)))
        for field in ("value_angle", "value_angle_esd"):
            value = _numeric(row, field, findings, category="angle", row_index=row_index,
                             positive=field.endswith("esd"), bounds=(0, 180) if field == "value_angle" else None)
            if value is None:
                missing_angle_targets.append({"row": row_index, "field": field})
    torsions = tables.get("tor", [])
    torsion_inventory = []
    missing_torsion_targets = []
    for row_index, row in enumerate(torsions):
        refs = _references(row, tuple(f"atom_id_{i}" for i in range(1, 5)), atoms,
                           findings, "tor", row_index)
        kind = row.get("type", row.get("kind", "?")).lower()
        path = bool(refs and all(frozenset(pair) in seen_bonds for pair in zip(refs, refs[1:])))
        family = bool(re.fullmatch(r"C[23]e-.+", row.get("id", "")))
        explicit_proper = kind in {"proper", "proper_dihedral", "torsion"}
        improper = kind in {"improper", "improper_dihedral"}
        if refs and not path and not improper:
            findings.append(_finding("TOR-01", "FAIL" if explicit_proper else "REVIEW",
                                     "torsion-unbonded-path", "A declared proper torsion does not follow its bonded quartet."
                                     if explicit_proper else
                                     "The quartet is not a bonded path; torsion kind needs review.",
                                     row=row_index, id=row.get("id"), atoms=list(refs),
                                     declared_kind=kind, supported_pucker_family=family))
        weight = None
        if row.get("weight", "?") not in _MISSING:
            weight = _numeric(row, "weight", findings, category="tor", row_index=row_index, bounds=(0, float("inf")))
        try:
            zero_sigma = _number(row.get("value_angle_esd")) == 0
        except (ValueError, TypeError, OverflowError):
            zero_sigma = False
        constant = weight == 0 or (weight is None and zero_sigma)
        if zero_sigma and weight is not None and weight > 0:
            findings.append(_finding("TOR-01", "REVIEW", "torsion-weight-sigma-conflict",
                                     "Positive explicit weight and the native zero-sigma convention disagree.", row=row_index))
        for field in ("value_angle", "value_angle_esd", "period"):
            value = _numeric(row, field, findings, category="tor", row_index=row_index,
                             positive=field == "value_angle_esd" and not constant,
                             bounds=(0, float("inf")) if constant and field == "value_angle_esd" else None,
                             integer=field == "period")
            if value is None and not constant:
                missing_torsion_targets.append({"row": row_index, "field": field})
        alternate = row.get("alt_value_angle", ".")
        if alternate not in _MISSING:
            for token in alternate.split(","):
                try:
                    value = _number(token.strip())
                    if value is None:
                        raise ValueError("missing alternate")
                except (ValueError, TypeError, OverflowError):
                    findings.append(_finding("TOR-01", "FAIL", "invalid-torsion-alternate",
                                             "A supplied alternative torsion target is not finite.", row=row_index, value=alternate))
                    break
        torsion_inventory.append({"id": row.get("id"), "atoms": list(refs or ()),
                                  "kind": "improper" if improper else "proper" if explicit_proper else
                                  "bonded-quartet" if path else "unassessed",
                                  "declared_weight": weight, "activity": "constant" if weight == 0 else
                                  "native-inactive-convention" if constant else
                                  "weighted" if weight is not None else "native-unassessed",
                                  "period": row.get("period"), "sigma": row.get("value_angle_esd"),
                                  "target": row.get("value_angle"), "alternates": alternate})
    if torsions:
        values = {"data_": block, **{"_chem_comp_tor." + field:
                  [row.get(field, "?") for row in torsions]
                  for field in sorted({key for row in torsions for key in row})}}
        _, events = normalize_torsion_block(values)
        for event in events:
            findings.append(_finding("TOR-01", "PASS" if event["status"] == "ADAPTED" else "REVIEW",
                                     "supported-torsion-alternates" if event["status"] == "ADAPTED" else
                                     "competing-torsion-terms", "Torsion row relationship inventoried without modification.",
                                     compatibility_event=event))
    chirality = []
    for row_index, row in enumerate(tables.get("chir", [])):
        refs = _references(row, ("atom_id_centre", "atom_id_1", "atom_id_2", "atom_id_3"), atoms,
                           findings, "chir", row_index)
        if refs and any(neighbor not in adjacency[refs[0]] for neighbor in refs[1:]):
            findings.append(_finding("STEREO-01", "FAIL", "unbonded-chiral-neighbor",
                                     "A chirality neighbor is not bonded to its declared centre.",
                                     row=row_index, atoms=list(refs)))
        sign = row.get("volume_sign", "?").lower()
        if sign not in {"positiv", "positive", "negativ", "negative", "both"}:
            findings.append(_finding("STEREO-01", "UNSUPPORTED", "unassessed-chirality-sign",
                                     "Chirality sign is missing or unsupported.", row=row_index, value=sign))
        chirality.append({"id": row.get("id"), "atoms": list(refs or ()),
                          "volume_sign": sign, "absolute_stereochemistry": "UNASSESSED"})
    planes: dict[str, set[str]] = defaultdict(set)
    missing_plane_targets = []
    for row_index, row in enumerate(tables.get("plane_atom", [])):
        refs = _references(row, ("atom_id",), atoms, findings, "plane_atom", row_index)
        plane = row.get("plane_id", "?")
        if plane in _MISSING:
            findings.append(_finding("GRAPH-01", "FAIL", "missing-plane-id", "A plane row lacks its plane identity.", row=row_index))
        if refs:
            if refs[0] in planes[plane]:
                findings.append(_finding("GRAPH-01", "FAIL", "duplicate-plane-atom",
                                         "A plane repeats an atom.", plane=plane, atom=refs[0]))
            planes[plane].add(refs[0])
        if _numeric(row, "dist_esd", findings, category="plane_atom", row_index=row_index, positive=True) is None:
            missing_plane_targets.append(row_index)
    plane_checks = _plane_checks(planes, adjacency, angles, findings)
    missing_types = sorted(row.get("atom_id", "?") for row in atom_rows
                           if row.get("type_energy", "?") in _MISSING)
    missing_numeric = {"bond": missing_bond_targets, "angle": missing_angle_targets,
                       "tor": missing_torsion_targets, "plane_atom": missing_plane_targets,
                       "type_energy": missing_types}
    numeric_fields = {"value_dist", "value_dist_esd", "value_dist_nucleus", "value_dist_nucleus_esd",
                      "value_angle", "value_angle_esd", "dist_esd", "type_energy", "weight"}
    supplied_numeric = any(numeric_fields.intersection(row) for rows in tables.values() for row in rows)
    graph_only = not supplied_numeric
    dictionary_geometry = _dictionary_geometry(atom_rows, bond_rows, graph_only=graph_only,
                                                findings=findings)
    if not graph_only and not angles and any(len(neighbors) > 1 for neighbors in adjacency.values()):
        findings.append(_finding("NUM-01", "REVIEW", "missing-angle-category",
                                 "A multibond numerical component has no bond-angle category; numerical coverage is unassessed.",
                                 centers_with_multiple_neighbors=sum(len(neighbors) > 1 for neighbors in adjacency.values()),
                                 limitations=["No universal requirement for every possible angle row is imposed."]))
    if (missing_bond_targets or missing_types or missing_angle_targets
            or missing_torsion_targets or missing_plane_targets):
        source_graph = graph_only and "effective" not in stage.lower()
        findings.append(_finding("NUM-01", "NOT_RUN" if source_graph else "REVIEW",
                                 "graph-only-source" if source_graph else "incomplete-numerical-parameterization",
                                 "Graph source has no numerical parameterization; this layer is unassessed."
                                 if source_graph else "Required fields within declared restraint rows are incomplete.",
                                 missing=missing_numeric))
    findings.append(_finding("GRAPH-01", "PASS", "graph-inventory", "Exact graph identity inventoried.",
                             atom_count=len(atom_rows), bond_count=len(bond_rows),
                             limitations=["Independent/installed consumer parsing was not run."]))
    graph_findings = [f for f in findings if f["rule_id"] == "GRAPH-01"]
    numerical_findings = [f for f in findings if f["rule_id"] in {"NUM-01", "TOR-01", "PLANE-01"}]
    inventory = {"atom_count": len(atom_rows), "heavy_atom_count": sum(
                 symbol.upper() not in {"H", "D", "?", ".", ""} for symbol in elements.values()),
                 "atoms": [{"atom_id": row.get("atom_id"), "element": row.get("type_symbol"),
                            "type_energy": row.get("type_energy"),
                            "declared_charge_fields": {key: row[key] for key in
                            ("charge", "partial_charge", "pdbx_formal_charge") if key in row},
                            "stereo_declarations": {key: row[key] for key in
                            ("pdbx_stereo_config", "stereo_config") if key in row}}
                           for row in atom_rows],
                 "bond_count": len(bond_rows), "bond_orders": bond_orders,
                 "angle_count": len(angles), "torsions": torsion_inventory,
                 "chirality": chirality, "planes": {plane: sorted(members) for plane, members in sorted(planes.items())},
                 "plane_angle_checks": plane_checks, "graph_only": graph_only,
                 "dictionary_geometry": dictionary_geometry,
                 "numerical_restraints": {category: [{key: value for key, value in row.items()
                     if key.startswith("atom_id") or key.startswith("value_") and key != "value_order"
                     or key in {"period", "weight", "alt_value_angle", "dist_esd", "plane_id", "type", "kind"}}
                     for row in tables.get(category, [])] for category in ("bond", "angle", "tor", "plane_atom")},
                 "hydrogen_attachments": [{"atom_id": name, "neighbors": sorted(adjacency[name])}
                    for name in sorted(atoms) if elements.get(name, "?").upper() in {"H", "D"}]}
    return {"component_id": code, "input_index": index, "block": block,
            "status": _status(findings), "inventory": inventory, "findings": findings,
            "verdicts": {"graph": _status(graph_findings),
                         "numerical": "UNASSESSED" if graph_only and "effective" not in stage.lower()
                         else _status(numerical_findings),
                         "chemical_identity": "UNASSESSED", "linked": "NOT_RUN", "native": "NOT_RUN",
                         "dictionary_geometry": dictionary_geometry["status"],
                         "geometry": "NOT_RUN", "experimental": "NOT_RUN"}}


def _model_audit(model: Path, components: Sequence[dict]) -> tuple[dict, list[dict]]:
    descriptor = _descriptor(model, "model")
    findings = []
    if model.suffix.lower() not in {".pdb", ".ent"}:
        findings.append(_finding("GRAPH-01", "UNSUPPORTED", "unsupported-model-format",
                                 "Model correspondence currently supports PDB atom records."))
        return descriptor, findings
    known: dict[str, set[str]] = defaultdict(set)
    for component in components:
        known[component["component_id"]].update(atom["atom_id"] for atom in component["inventory"]["atoms"])
    residues: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    model_id = "1"
    for line in model.read_text(encoding="utf-8").splitlines():
        if line.startswith("MODEL "):
            model_id = line[10:14].strip() or model_id
        if line.startswith(("ATOM  ", "HETATM")):
            if len(line) < 27:
                findings.append(_finding("GRAPH-01", "ERROR", "short-model-atom-record", "PDB atom record is truncated."))
                continue
            code = line[17:20].strip()
            if code in known:
                residues[(model_id, line[21:22], line[22:26].strip(), line[26:27], code)].append(
                    (line[12:16].strip(), line[16:17]))
    records = []
    for (number, chain, residue, insertion, code), identities in sorted(residues.items()):
        unknown = sorted({atom for atom, _ in identities} - known[code])
        duplicates = sorted([list(key) for key, count in Counter(identities).items() if count > 1])
        record = {"model_id": number, "chain_id": chain, "residue_id": residue,
                  "insertion_code": insertion, "component_id": code,
                  "atoms": [{"atom_id": atom, "alternate_id": alt} for atom, alt in identities],
                  "dictionary_atoms_absent_from_model": sorted(known[code] - {atom for atom, _ in identities})}
        records.append(record)
        if unknown or duplicates:
            findings.append(_finding("GRAPH-01", "REVIEW", "model-dictionary-identity-mismatch",
                                     "Model atom identities differ from the supplied component inventory.",
                                     site={key: record[key] for key in ("model_id", "chain_id", "residue_id", "insertion_code", "component_id")},
                                     unknown_atoms=unknown, duplicate_atom_alternates=duplicates))
    descriptor["component_sites"] = records
    descriptor["limitations"] = ["Absent dictionary atoms may be removed by site modifications or omit hydrogens.",
                                  "No site-link, element, coordinate, chirality or geometry comparison was run."]
    return descriptor, findings


def assess_dictionaries(paths: Sequence[Path], *, stage: str = "standalone",
                        model: Path | None = None) -> dict:
    """Assess explicit inputs without writing files or resolving by basename.

    Descriptors bind supplied order and content hashes. Callers freezing a run
    receipt add their anchored operational references using these exact paths.
    Source graph-only CIFs are allowed; selected effective rows must expose
    numerical omissions. Unsupported ancillary/link/mod definitions are visible.
    """
    inputs = []
    components = []
    findings = []
    auxiliary = []
    for index, supplied in enumerate(paths):
        path = Path(supplied)
        role = "dictionary" if path.suffix.lower() in {".cif", ".mmcif"} else "ancillary"
        try:
            descriptor = _descriptor(path, role, index)
        except OSError as exc:
            inputs.append({"input_index": index, "name": path.name, "role": role,
                           "sha256": None, "size": None})
            findings.append({"input_index": index, **_finding("PROV-01", "ERROR", "input-unreadable",
                             "Explicit input cannot be read.", error_type=type(exc).__name__)})
            continue
        inputs.append(descriptor)
        if role == "ancillary":
            findings.append({"input_index": index, **_finding("COVER-01", "UNSUPPORTED", "ancillary-not-interpreted",
                             "Ancillary restraint input is hashed and retained; its terms were not interpreted.")})
            continue
        try:
            if any(not quoted and (token.lower().startswith("save_") or token.lower() == "global_")
                   for token, quoted in _cif_tokens(path.read_text(encoding="utf-8"))):
                findings.append({"input_index": index, **_finding("GRAPH-01", "ERROR", "unsupported-cif-layout",
                                 "Global/save CIF layouts are outside the supported dictionary parser.")})
                continue
            blocks = _blocks(path)
        except (OSError, ValueError, UnicodeError, KeyError) as exc:
            findings.append({"input_index": index, **_finding("GRAPH-01", "ERROR", "cif-parse-error",
                             "Dictionary cannot be parsed in the supported CIF1 reader.", error_type=type(exc).__name__)})
            continue
        for parsed in blocks:
            values = {key.lower(): value for key, value in parsed.values.items()}
            block_name = str(values.get("data_", "?"))
            try:
                duplicates = _duplicate_tags(parsed.text)
            except ValueError:
                findings.append({"input_index": index, "block": block_name,
                                 **_finding("GRAPH-01", "ERROR", "unsupported-cif-layout",
                                 "The lexical preflight cannot assess this CIF1 layout.")})
                continue
            if duplicates:
                findings.append({"input_index": index, "block": block_name,
                                 **_finding("GRAPH-01", "ERROR", "duplicate-cif-tags",
                                 "Duplicate CIF tags would overwrite content in the supported reader.", tags=duplicates)})
                continue
            local_findings = []
            tables = {category: _rows(values, "_chem_comp_" + category, local_findings)
                      for category in ("atom", "bond", "angle", "tor", "chir", "plane_atom")}
            codes = {row.get("comp_id", "?") for row in tables["atom"]} - _MISSING
            if not codes and tables["atom"]:
                fallback_ids = set(values.get("_chem_comp.id", [])) - _MISSING
                if len(fallback_ids) == 1:
                    codes = fallback_ids
                elif len(fallback_ids) > 1:
                    local_findings.append(_finding("GRAPH-01", "FAIL", "ambiguous-unscoped-component-atoms",
                                                   "Unscoped atom rows cannot be assigned to multiple component declarations.",
                                                   metadata_components=sorted(fallback_ids)))
            declared_ids = set(values.get("_chem_comp.id", [])) - _MISSING
            if tables["atom"] and declared_ids and declared_ids != codes:
                local_findings.append(_finding("GRAPH-01", "FAIL", "component-identity-conflict",
                                               "Component metadata and atom-row component identities disagree.",
                                               metadata_components=sorted(declared_ids), atom_components=sorted(codes)))
            if tables["atom"] and not codes:
                local_findings.append(_finding("GRAPH-01", "FAIL", "missing-component-identity",
                                               "Atom definitions lack a declared component identity."))
            if not tables["atom"]:
                if any(tables[category] for category in ("bond", "angle", "tor", "chir", "plane_atom")):
                    local_findings.append(_finding("GRAPH-01", "FAIL", "restraints-without-atom-definition",
                                                   "Component restraint rows have no component atom definition."))
                categories = sorted({key.split(".")[0] for key in values if key.startswith("_")})
                kind = "component-list" if categories and all(category == "_chem_comp" for category in categories) else "noncomponent"
                auxiliary.append({"input_index": index, "block": block_name, "kind": kind, "categories": categories})
                if kind == "noncomponent":
                    findings.append({"input_index": index, "block": block_name,
                                     **_finding("LINK-01", "UNSUPPORTED", "noncomponent-block-not-interpreted",
                                     "Noncomponent link/mod/other blocks are retained without interpreting their effects.", categories=categories)})
                findings.extend({"input_index": index, "block": block_name, **finding} for finding in local_findings)
                continue
            for code in sorted(codes or {"?"}):
                selected = {}
                for category, rows in tables.items():
                    selected[category] = [row for row in rows if row.get("comp_id", code) == code]
                    bad = [row for row in rows if row.get("comp_id", code) not in codes]
                    if bad:
                        local_findings.append(_finding("GRAPH-01", "FAIL", "restraint-component-identity-mismatch",
                                                       "Restraint rows name a component absent from the atom inventory.",
                                                       category=category, components=sorted({row.get("comp_id", "?") for row in bad})))
                component = _component(code, index, block_name, selected, local_findings, stage)
                semantic_payload = json_canonical({key: value for key, value in values.items() if key != "data_"})
                component["definition_sha256"] = sha256(semantic_payload.encode()).hexdigest()
                components.append(component)
                findings.extend({"input_index": index, "block": block_name, "component_id": code, **finding}
                                for finding in component["findings"])
    by_code: dict[str, list[dict]] = defaultdict(list)
    for component in components:
        by_code[component["component_id"]].append(component)
    for code, definitions in sorted(by_code.items()):
        if len(definitions) > 1:
            signatures = {repr((sorted((atom["atom_id"], atom["element"]) for atom in record["inventory"]["atoms"]),
                               sorted((tuple(sorted(bond["atoms"])), sorted(bond["declarations"].items()))
                                      for bond in record["inventory"]["bond_orders"]))) for record in definitions}
            identical_definitions = len({definition["definition_sha256"] for definition in definitions}) == 1
            findings.append({"component_id": code, **_finding("PROV-01", "PASS" if identical_definitions else "REVIEW",
                             "multiple-component-definitions", "Multiple definitions inventoried; authority/precedence is not inferred.",
                             definition_inputs=[record["input_index"] for record in definitions], identical_graphs=len(signatures) == 1,
                             identical_definitions=identical_definitions)})
    model_descriptor = None
    if model is not None:
        try:
            model_descriptor, model_findings = _model_audit(Path(model), components)
            findings.extend(model_findings)
        except (OSError, UnicodeError) as exc:
            findings.append(_finding("PROV-01", "ERROR", "model-unreadable", "Explicit model cannot be read.", error_type=type(exc).__name__))
    integrity = "UNCHANGED"
    for index, path in enumerate(paths):
        if inputs[index]["sha256"] is not None:
            try:
                current = _descriptor(Path(path), inputs[index]["role"], index)
                unchanged = current["sha256"] == inputs[index]["sha256"]
            except OSError:
                unchanged = False
            if not unchanged:
                integrity = "CHANGED_DURING_ASSESSMENT"
                findings.append({"input_index": index, **_finding("PROV-01", "ERROR", "input-changed-during-assessment",
                                 "Input content changed while the read-only assessment was running.")})
    if model_descriptor is not None:
        try:
            unchanged_model = _descriptor(Path(model), "model")["sha256"] == model_descriptor["sha256"]
        except OSError:
            unchanged_model = False
        if not unchanged_model:
            integrity = "CHANGED_DURING_ASSESSMENT"
            findings.append(_finding("PROV-01", "ERROR", "model-changed-during-assessment",
                                     "Model content changed while the read-only assessment was running."))
    status = _status(findings, assessed=bool(components))
    return {"schema_version": 1, "audit_kind": "cif_restraint_assessment", "policy_id": POLICY_ID,
            "stage": stage, "status": status, "inputs": inputs, "model": model_descriptor,
            "provenance": {"assessor_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                           "tools": [{"name": "Python", "version": sys.version.split()[0]},
                                     {"name": "Biopython MMCIF2Dict", "version": BIOPYTHON_VERSION}],
                           "installed_consumer_validation": "NOT_RUN"},
            "components": components, "auxiliary_blocks": auxiliary, "findings": findings,
            "input_integrity": integrity, "transformations": [],
            "summary": {"component_count": len(components),
                        "finding_counts": dict(sorted(Counter(f["status"] for f in findings).items())),
                        "status_counts": dict(sorted(Counter(c["status"] for c in components).items()))},
            "limitations": ["PASS covers checked invariants, not chemical or scientific approval.",
                            "Independent and installed consumer parsing were not run.",
                            "Native proxies, site-linked chemistry, achieved geometry and diffraction were not assessed."]}


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


def compare_dictionaries(source_paths: Sequence[Path], effective_paths: Sequence[Path]) -> dict:
    """Compare explicit same-ID declarations without deciding which is correct.

    Labels are never treated as aliases. Site deletions/link modifications and
    tautomer/protonation transformations need separate declared policies.
    """
    source = assess_dictionaries(source_paths, stage="source")
    effective = assess_dictionaries(effective_paths, stage="effective")
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
    invalid = source["status"] == "INVALID" or effective["status"] == "INVALID"
    integrity = "UNCHANGED"
    for receipt, paths in ((source, source_paths), (effective, effective_paths)):
        for descriptor, path in zip(receipt["inputs"], paths):
            if descriptor.get("sha256") is None:
                continue
            try:
                unchanged = _descriptor(Path(path), descriptor["role"])["sha256"] == descriptor["sha256"]
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
            "status": status, "source_assessment": source, "effective_assessment": effective,
            "differences": differences, "findings": findings, "compared_components": compared,
            "comparison_scope_complete": not any(f["code"] in {"component-unpaired", "ambiguous-comparison-definition"} for f in findings),
            "input_integrity": "UNCHANGED" if integrity == source["input_integrity"] == effective["input_integrity"] == "UNCHANGED"
            else "CHANGED_DURING_ASSESSMENT",
            "limitations": ["No alias, atom remapping, source authority or site-linked modification is inferred.",
                            "Graph agreement does not validate numerical restraints, native proxies or geometry."]}
