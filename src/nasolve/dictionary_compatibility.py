"""Small, content-based CIF compatibility transformations (no chemistry inference).

CCP4 C2e/C3e rows describe alternative sugar conformations. CCTBX represents
alternative targets in one row's ``alt_value_angle`` and retains the primary
row's uncertainty. We follow that policy explicitly, recording unequal source
uncertainties rather than claiming a lossless conversion of their weights.
Unknown conflicts are retained and reported; Phenix remains the interpreter.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
import re
from typing import Mapping

TORSION_POLICY = "ccp4-alternates-primary-sigma-v2"
_TOR = "_chem_comp_tor."
_REQUIRED = ("comp_id", "id", "atom_id_1", "atom_id_2", "atom_id_3",
             "atom_id_4", "value_angle", "value_angle_esd", "period")
_KNOWN = frozenset((*_REQUIRED, "alt_value_angle"))


def _number(value: object) -> float:
    number = float(str(value))
    if not isfinite(number):
        raise ValueError("non-finite torsion parameter")
    return number


def _angle_key(value: str) -> float:
    # Full reversal of a dihedral has the same signed angle. Arbitrary atom
    # permutations do not. Deduplication here is only modulo a complete turn.
    return round(_number(value) % 360.0, 8) % 360.0


def _targets(row: Mapping[str, str]) -> list[str]:
    targets = [row["value_angle"]]
    alternatives = row.get("alt_value_angle", ".").strip()
    if alternatives not in {"", ".", "?"}:
        targets.extend(part.strip() for part in alternatives.split(","))
    if any(not part for part in targets):
        raise ValueError("empty alternative torsion target")
    for value in targets:
        _number(value)
    return targets


def normalize_torsion_block(values: Mapping[str, object]) -> tuple[dict, list[dict]]:
    """Return a copied CIF block and an auditable list of conversions/warnings.

    Convert only identified CCP4 C2e/C3e alternatives, exact equivalent rows,
    including already populated alternative fields on those identified rows. Never collapse different
    periods, different central-bond orderings, or unclassified competing targets.
    This function does not alter atom definitions, bonds, planes or chirality.
    """
    result = deepcopy(dict(values))
    columns = {key[len(_TOR):]: val for key, val in values.items()
               if key.startswith(_TOR)}
    if not columns:
        return result, []
    angles = columns.get("value_angle", [])
    count = len(angles) if isinstance(angles, list) else 0
    if (not count or any(not isinstance(val, list) or len(val) != count
                         for val in columns.values())
            or any(key not in columns for key in _REQUIRED)):
        return result, [{"status": "WARNING", "reason": "unsupported-torsion-layout",
                         "action": "retained-for-native-interpretation"}]

    rows = [{key: str(val[index]) for key, val in columns.items()}
            for index in range(count)]
    groups: dict[tuple[str, tuple[str, ...]], list[int]] = {}
    for index, row in enumerate(rows):
        atoms = tuple(row[f"atom_id_{i}"] for i in range(1, 5))
        if len(set(atoms)) != 4 or any(atom in {"", ".", "?"} for atom in atoms):
            # Leave malformed native input available for Phenix diagnostics.
            continue
        key = (row["comp_id"], min(atoms, atoms[::-1]))
        groups.setdefault(key, []).append(index)

    remove: set[int] = set()
    alternate_values: dict[int, str] = {}
    events: list[dict] = []
    for (code, atoms), indices in groups.items():
        if len(indices) < 2:
            continue
        source_rows = [rows[index] for index in indices]
        event = {"component": code, "atoms": list(atoms),
                 "source_rows": source_rows, "policy": TORSION_POLICY}
        reason = None
        try:
            periods = [_number(row["period"]) for row in source_rows]
            sigmas = [_number(row["value_angle_esd"]) for row in source_rows]
            targets = [_targets(row) for row in source_rows]
            if any(period <= 0 or not period.is_integer() for period in periods):
                reason = "unsupported-period"
            elif len(set(periods)) != 1:
                reason = "different-periods"
            elif any(sigma <= 0 for sigma in sigmas):
                reason = "unusable-uncertainty"
        except (TypeError, ValueError, OverflowError):
            reason = "unusable-torsion-parameters"
        if reason is None:
            matches = [re.fullmatch(r"C([23])e-(.+)", row["id"])
                       for row in source_rows]
            ccp4_alternates = (
                all(match is not None for match in matches)
                and len({match.group(2) for match in matches if match}) == 1
                and {match.group(1) for match in matches if match} == {"2", "3"}
            )
            exact_equivalents = (
                len({tuple(_angle_key(value) for value in group) for group in targets}) == 1
                and len(set(sigmas)) == 1
            )
            if not (ccp4_alternates or exact_equivalents):
                reason = "unclassified-competing-targets"
            elif any(len({row[key] for row in source_rows}) != 1
                     for key in columns if key not in _KNOWN):
                reason = "different-extra-torsion-fields"
        if reason is not None:
            events.append({**event, "status": "WARNING", "reason": reason,
                           "action": "retained-for-native-interpretation"})
            continue

        first = indices[0]
        seen = {_angle_key(rows[first]["value_angle"])}
        alternatives = []
        for group in targets:
            for value in group:
                key = _angle_key(value)
                if key not in seen:
                    alternatives.append(value)
                    seen.add(key)
        alternate_values[first] = ",".join(alternatives) if alternatives else "."
        remove.update(indices[1:])
        events.append({
            **event, "status": "ADAPTED", "primary_id": rows[first]["id"],
            "primary_angle": rows[first]["value_angle"],
            "alternate_angles": alternatives,
            "period": rows[first]["period"],
            "effective_sigma": rows[first]["value_angle_esd"],
            "source_uncertainties_differ": len(set(sigmas)) > 1,
            "uncertainty_policy": "retain-primary-row-as-in-cctbx-conversion",
        })

    if remove:
        keep = [index for index in range(count) if index not in remove]
        for key, column in columns.items():
            result[_TOR + key] = [column[index] for index in keep]
        old_alts = columns.get("alt_value_angle", ["."] * count)
        result[_TOR + "alt_value_angle"] = [
            alternate_values.get(index, old_alts[index]) for index in keep
        ]
    return result, events
