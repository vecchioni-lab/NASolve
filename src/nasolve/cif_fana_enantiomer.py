"""Read-only validation of an explicitly proposed whole FANA enantiomer source.

Identity comes from the parent graph and NAR binding, not the target code/name.
This gate verifies a rigid mirror reference, not independently assigned CIP,
optimized coordinates, numerical restraints, NAR registration or model insertion.
"""
from hashlib import sha256
from itertools import combinations
import math
from pathlib import Path

from .cif_fana import inspect_fana
from .cif_linked_preparation import component_values
from .cif_stereochemistry_audit import _values, _graph, _stereo, _number, _volume, VOLUME_EPSILON

POLICY_ID = "cif-explicit-fana-enantiomer-source-v1"
INTENT = "whole-component-enantiomer"
DISTANCE_TOLERANCE = 1e-6  # Angstrom; serialization/isometry, not refinement tolerance.
_ATOM = "_chem_comp_atom."
_COORDINATES = {
    "SOURCE_IDEAL": [_ATOM + "pdbx_model_cartn_" + a + "_ideal" for a in "xyz"],
    "SOURCE_MODEL": [_ATOM + "model_cartn_" + a for a in "xyz"],
    "RESTRAINT_CARTESIAN": [_ATOM + a for a in "xyz"],
}


def _coordinate_families(values):
    families = {}
    for name, keys in _COORDINATES.items():
        if not any(k in values for k in keys):
            continue
        if not all(k in values for k in keys):
            raise ValueError("Incomplete enantiomer coordinate family: " + name)
        names = values[_ATOM + "atom_id"]
        if any(len(values[k]) != len(names) for k in keys):
            raise ValueError("Ragged enantiomer coordinates")
        xyz = {atom: [_number(values[k][i]) for k in keys] for i, atom in enumerate(names)}
        if any(x is None or not math.isfinite(x) for point in xyz.values() for x in point):
            raise ValueError("Require complete finite enantiomer coordinates")
        families[name] = xyz
    if not families:
        raise ValueError("Require an explicit enantiomer coordinate family")
    return families


def _bond_annotations(values):
    prefix = "_chem_comp_bond."
    fields = [k for k in values if k.startswith(prefix) and ("aromatic" in k or "stereo" in k)]
    return {tuple(sorted((a, b))): {k: values[k][i] for k in fields}
            for i, (a, b) in enumerate(zip(values[prefix + "atom_id_1"], values[prefix + "atom_id_2"]))}


def inspect_fana_enantiomer(source, source_code, target, target_code, *, workbook, intent):
    """Check complete graph identity, inverted declarations and every coordinate family.

    The target needs a distinct explicit local code. Its parent NAR record binds
    the unchanged named base atoms; this does not register the new code in NAR.
    Only sources declaring exactly the four sugar centres and N elsewhere qualify.
    All pair distances and all four neighbour triples per sugar centre are checked.
    Numerical dictionaries and target descriptor/identifier tables need separate
    adapters; they cannot be carried through as unexplained stereo authority.
    """
    if intent != INTENT or not isinstance(intent, str):
        raise ValueError("Require explicit whole-component-enantiomer intent")
    if not source_code or not target_code or source_code == target_code:
        raise ValueError("Require distinct explicit parent and target component codes")
    source, target, workbook = (Path(p).expanduser().resolve(strict=True) for p in (source, target, workbook))
    before = {p: p.read_bytes() for p in (source, target, workbook)}
    profile = inspect_fana(source, source_code, workbook=workbook)
    def ref(path, anchor):
        return {"anchor": anchor, "path": path.name, "sha256": sha256(before[path]).hexdigest(), "size": len(before[path])}
    report = {"schema_version": 1, "policy_id": POLICY_ID, "status": "REVIEW", "intent": intent,
        "source_code": source_code, "target_code": target_code, "parent_fana": profile,
        "source": ref(source, "source_directory"), "target": ref(target, "target_source_directory"),
        "target_family": None, "checks": {}, "coordinate_families": [], "review_reasons": [],
        "distance_tolerance_angstrom": DISTANCE_TOLERANCE, "volume_epsilon_angstrom_cubed": VOLUME_EPSILON,
        "absolute_cip_assignment": "NOT_RUN", "target_nar_registration": "NOT_RUN",
        "native_qualification": "NOT_RUN", "model_editing": "NOT_RUN", "automatic_adoption": False,
        "input_integrity": "UNCHANGED", "scope": "EXPLICIT_RIGID_ENANTIOMER_SOURCE_ONLY"}
    checks, reasons = report["checks"], report["review_reasons"]
    checks["parent_fana_source"] = profile["status"] == "SOURCE_MATCH"
    if checks["parent_fana_source"]:
        for path, code in ((source, source_code), (target, target_code)):
            raw = component_values(path, code)
            if len({k.lower() for k in raw}) != len(raw):
                raise ValueError("Ambiguous case-variant enantiomer fields")
        a, b = _values(source, source_code), _values(target, target_code)
        ga, gb = _graph(a), _graph(b)
        checks["bounded_atom_count"] = 1 <= len(ga[0]) <= 512
        checks["whole_graph_elements_orders_charges"] = ga[:3] == gb[:3]
        checks["complete_integer_formal_charges"] = all(q is not None and math.isfinite(q) and float(q).is_integer() for graph in (ga, gb) for q in graph[2].values())
        checks["bond_annotations_preserved"] = _bond_annotations(a) == _bond_annotations(b)
        centers = {row["atom_id"] for row in profile["core_stereo"].values()}
        ma, mb = _stereo(a), _stereo(b)
        checks["only_four_declared_sugar_centers"] = (len(centers) == 4 and
            {n for n, mark in ma.items() if mark in {"R", "S"}} == centers and
            all(mark in {"R", "S", "N"} for mark in ma.values()))
        checks["exact_inverted_stereo_declarations"] = mb == {n: {"R": "S", "S": "R"}.get(mark, mark) for n, mark in ma.items()}
        forbidden = ("_chem_comp_angle.", "_chem_comp_tor.", "_chem_comp_chir.", "_chem_comp_plane", "_chem_comp_tree.")
        checks["source_graph_only"] = not any(k.startswith(forbidden) or k.startswith("_chem_comp_bond.value_dist") or k == _ATOM + "type_energy" for values in (a, b) for k in values)
        checks["target_descriptors_not_inherited"] = not any(k.startswith(("_pdbx_chem_comp_descriptor.", "_pdbx_chem_comp_identifier.")) for k in b)
        if all(checks.values()):
            ca, cb = _coordinate_families(a), _coordinate_families(b)
            checks["same_coordinate_families"] = ca.keys() == cb.keys()
            for family in sorted(ca.keys() & cb.keys()):
                left, right = ca[family], cb[family]
                errors = [abs(math.dist(left[x], left[y]) - math.dist(right[x], right[y])) for x, y in combinations(sorted(left), 2)]
                error = max(errors) if all(math.isfinite(e) for e in errors) else None
                hands = []
                for center in sorted(centers):
                    for triple in combinations(sorted(ga[3][center]), 3):
                        va, vb = _volume(left, center, triple), _volume(right, center, triple)
                        finite = math.isfinite(va) and math.isfinite(vb)
                        hands.append({"center": center, "ordered_neighbors": list(triple), "source_volume": va if math.isfinite(va) else None,
                                      "target_volume": vb if math.isfinite(vb) else None, "inverted": finite and min(abs(va), abs(vb)) > VOLUME_EPSILON and (va > 0) != (vb > 0)})
                report["coordinate_families"].append({"family": family, "max_pair_distance_difference": error,
                    "all_distances_preserved": error is not None and error <= DISTANCE_TOLERANCE,
                    "all_sugar_hands_inverted": len(hands) == 16 and all(row["inverted"] for row in hands), "sugar_hands": hands})
            checks["complete_rigid_mirror"] = bool(report["coordinate_families"]) and checks["same_coordinate_families"] and all(
                row["all_distances_preserved"] and row["all_sugar_hands_inverted"] for row in report["coordinate_families"])
    reasons.extend(name for name, passed in checks.items() if not passed)
    if checks and all(checks.values()):
        report.update(status="ENANTIOMER_SOURCE_PASS", target_family={"beta-D-FANA": "beta-L-FANA", "beta-L-FANA": "beta-D-FANA"}[profile["source_family"]])
    if any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError("Enantiomer input changed during inspection")
    return report
