"""Compare each dictionary's explicit heavy-atom coordinates with its own bond targets."""
from collections import defaultdict
from math import dist, isfinite
from pathlib import Path

from .cif_doctor import _number, _rows
from .ligand_profiles import _blocks
from .model_assessment import file_sha256


_COORDINATES = (
    ("RESTRAINT_CARTESIAN", ("x", "y", "z")),
    ("SOURCE_IDEAL", tuple(f"pdbx_model_cartn_{axis}_ideal" for axis in "xyz")),
    ("SOURCE_MODEL", tuple(f"model_cartn_{axis}" for axis in "xyz")),
)


def _finite(value):
    try:
        return _number(value)
    except (ValueError, TypeError, OverflowError):
        return None


def _measure(row, coords):
    atoms = [row["atom_id_1"], row["atom_id_2"]]
    target = _finite(row.get("value_dist"))
    esd = _finite(row.get("value_dist_esd"))
    result = {"atoms": atoms, "target_A": target, "esd_A": esd}
    if target is None or target <= 0:
        return {**result, "reason": "no-positive-value_dist"}
    if any(atom not in coords for atom in atoms):
        return {**result, "reason": "coordinates-unavailable"}
    distance = dist(coords[atoms[0]], coords[atoms[1]])
    if not isfinite(distance):
        return {**result, "reason": "distance-out-of-range"}
    delta = distance - target
    scaled = delta / esd if esd is not None and esd > 0 else None
    return {**result, "distance_A": distance, "minus_target_A": delta,
            "difference_in_esds": scaled if scaled is not None and isfinite(scaled) else None}


def _component(item, atom_rows):
    code = item["component_id"]
    result = {"component": code, "input_index": item["input_index"],
              "block": item["block"], "coordinate_sets": []}
    inventory = item["inventory"]
    if item["verdicts"]["graph"] != "PASS":
        return {**result, "reason": "ambiguous-graph"}
    if inventory["graph_only"]:
        return {**result, "reason": "graph-only"}
    if inventory["atom_count"] > 10000 or inventory["bond_count"] > 50000:
        return {**result, "reason": "assessment-size-bound"}
    heavy = {a["atom_id"] for a in inventory["atoms"] if a["element"].upper() not in {"H", "D"}}
    rows = {r["atom_id"]: r for r in atom_rows if r.get("comp_id", code) == code and r["atom_id"] in heavy}
    if set(rows) != heavy:
        raise ValueError("Dictionary coordinate atoms differ from the assessed inventory")
    bonds = [b for b in inventory["numerical_restraints"]["bond"]
             if b.get("atom_id_1") in heavy and b.get("atom_id_2") in heavy]
    if not bonds:
        return {**result, "reason": "no-heavy-atom-bonds"}
    columns = {key for row in rows.values() for key in row}
    for family, axes in _COORDINATES:
        if not columns.intersection(axes):
            continue
        coords = {atom: tuple(_finite(row.get(axis)) for axis in axes) for atom, row in rows.items()}
        complete = {atom: xyz for atom, xyz in coords.items() if None not in xyz}
        observed = [_measure(bond, complete) for bond in bonds]
        result["coordinate_sets"].append({"family": family, "bonds": observed,
                                          "measured": sum("distance_A" in bond for bond in observed)})
    if not result["coordinate_sets"]:
        result["reason"] = "no-coordinate-set"
    return result


def read_template_bonds(paths, assessment):
    """Use the exact inputs of an ordinary assessment. Keep each definition and coordinate family separate."""
    grouped = defaultdict(list)
    for item in assessment["components"]:
        grouped[item["input_index"]].append(item)
    components = []
    for index, (path, descriptor) in enumerate(zip(paths, assessment["inputs"], strict=True)):
        if index not in grouped:
            continue
        path = Path(path)
        if file_sha256(path) != descriptor["sha256"]:
            raise ValueError("Dictionary changed before template bond inspection")
        blocks = {}
        for block in _blocks(path):
            values = {key.lower(): value for key, value in block.values.items()}
            blocks[values["data_"]] = _rows(values, "_chem_comp_atom", [])
        for item in grouped[index]:
            components.append(_component(item, blocks[item["block"]]))
        if file_sha256(path) != descriptor["sha256"]:
            raise ValueError("Dictionary changed during template bond inspection")
    return {"policy_id": "dictionary-template-bonds-v1", "target_field": "_chem_comp_bond.value_dist",
            "components": components, "assessment": "DESCRIPTIVE", "coordinate_changes": False}
