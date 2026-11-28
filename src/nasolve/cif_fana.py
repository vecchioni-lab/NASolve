"""Read-only FANA source/candidate gates, independent of catalogue family labels.

This bounded N-glycoside rule identifies the source-declared beta-D/L arabino
configuration. It does not calculate CIP, choose a phosphate state, generate a
model, or qualify native numerical restraints.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .cif_attachment_profiles import inspect_attachment_profile
from .cif_candidate_usability import reassess_complete_candidate
from .cif_linked_preparation import component_values
from .cif_purine_representation import validate_policy
from .cif_stereochemistry_audit import _graph, _stereo

POLICY_ID = "cif-source-declared-fana-v1"
_CENTERS = ("anomeric", "ring_c2", "ring_c3", "ring_c4")
_DECLARED_HANDS = {("R", "S", "R", "R"): "beta-D-FANA",
                   ("S", "R", "S", "S"): "beta-L-FANA"}
_H_COUNTS = {"anomeric": 1, "ring_c2": 1, "ring_c3": 1, "ring_c4": 1,
             "five_c": 2, "ring_o": 0, "five_o": 0, "three_o": 1}


def _reference(path, data, anchor):
    return {"anchor": anchor, "path": path.name,
            "sha256": sha256(data).hexdigest(), "size": len(data)}


def inspect_fana(source, code, *, workbook, candidate=None, bond_representation_policy=None):
    """Inspect explicit sources and optionally a complete generated dictionary.

    A candidate must retain all source chemistry under the selected existing
    representation policy and preserve all four sugar centres in source-relative
    coordinates. Unassessed handedness cannot satisfy this FANA-specific gate.
    No native process or write occurs; all operational references are anchored.
    """
    validate_policy(bond_representation_policy)
    source, workbook = (Path(p).expanduser().resolve(strict=True) for p in (source, workbook))
    candidate = Path(candidate).expanduser().resolve(strict=True) if candidate is not None else None
    paths = [source, workbook] + ([candidate] if candidate is not None else [])
    before = {p: p.read_bytes() for p in paths}
    profile = inspect_attachment_profile(source, code, workbook=workbook)
    report = {
        "schema_version": 1, "policy_id": POLICY_ID, "component": code,
        "status": "REVIEW", "source_family": None, "fluorine_atom": None,
        "source_profile": profile, "core_stereo": {}, "candidate_core_stereo": [],
        "bond_representation_policy": bond_representation_policy,
        "candidate": _reference(candidate, before[candidate], "candidate_directory") if candidate else None,
        "candidate_assessment": None, "review_reasons": [],
        "native_execution": "NOT_RUN", "native_qualification": "NOT_ASSESSED",
        "absolute_cip_assignment": "NOT_RUN", "automatic_adoption": False,
        "transformations": [], "input_integrity": "UNCHANGED",
        "scope": "SOURCE_DECLARED_FAMILY_AND_CANDIDATE_PRESERVATION_ONLY",
        "limitations": [
            "Source R/S declarations identify the family; no independent absolute CIP assignment.",
            "Only neutral, explicitly hydrogenated 2-fluoro N-glycoside sugar cores are covered.",
            "Base chemistry and charge are retained, not normalized or approved by family membership.",
            "No phosphate deletion, linkage, model mutation, native usability or automatic adoption.",
        ],
    }
    reasons = report["review_reasons"]
    if profile["matched_profile"] != "unbridged-furanose-phosphate-v1" or profile["review_reasons"]:
        reasons.append("SOURCE_ATTACHMENT_PROFILE_UNRESOLVED")
    else:
        values = {k.lower(): v for k, v in component_values(source, code).items()}
        elements, bonds, charges, neighbors = _graph(values)
        marks = _stereo(values)
        binding = profile["bindings"]
        c2 = binding["ring_c2"]
        outside = neighbors[c2] - {binding["anomeric"], binding["ring_c3"]}
        fluorines = sorted(a for a in outside if elements[a] == "F")
        if (len(fluorines) != 1 or neighbors[fluorines[0]] != {c2}
                or bonds[tuple(sorted((c2, fluorines[0])))] != "SINGLE"
                or charges[fluorines[0]] != 0):
            reasons.append("SOURCE_TWO_PRIME_FLUORINE_UNRESOLVED")
        else:
            report["fluorine_atom"] = fluorines[0]
        # Bound the CIP-pattern rule to the declared local chemistry it describes.
        # Isotopic hydrogen is retained; carbon-linked bases need a separate rule.
        if elements[binding["base"]] != "N":
            reasons.append("SOURCE_N_GLYCOSIDE_REQUIRED")
        for role, count in _H_COUNTS.items():
            atom = binding[role]
            hydrogens = sorted(a for a in neighbors[atom] if elements[a] in {"H", "D"})
            if (len(hydrogens) != count or charges[atom] != 0
                    or any(neighbors[h] != {atom} or charges[h] != 0
                           or bonds[tuple(sorted((h, atom)))] != "SINGLE" for h in hydrogens)):
                reasons.append("SOURCE_SUGAR_STATE_UNRESOLVED:" + role)
        for role in _CENTERS:
            atom = binding[role]
            report["core_stereo"][role] = {"atom_id": atom, "declared": marks[atom],
                                          "neighbors": sorted(neighbors[atom])}
            if len(neighbors[atom]) != 4:
                reasons.append("SOURCE_TETRAHEDRON_UNRESOLVED:" + role)
        family = _DECLARED_HANDS.get(tuple(marks[binding[r]] for r in _CENTERS))
        if family is None:
            reasons.append("SOURCE_STEREO_NOT_BETA_FANA")
        if not reasons:
            report.update(source_family=family, status="SOURCE_MATCH")
    if candidate is not None and not reasons:
        try:
            assessment = reassess_complete_candidate(
                source, candidate, code, bond_representation_policy=bond_representation_policy,
            )
        except ValueError as exc:
            reasons.append("CANDIDATE_ASSESSMENT_UNRESOLVED: " + str(exc))
        else:
            report["candidate_assessment"] = assessment
            if assessment["candidate_status"] != "CANDIDATE_REVIEW":
                reasons.extend("CANDIDATE:" + r for r in assessment["rejection_reasons"])
            centers = {row["atom_id"] for row in report["core_stereo"].values()}
            terms = [r for r in assessment["finished_stereo"]["terms"] if r["center"] in centers]
            report["candidate_core_stereo"] = terms
            if (len(terms) != 4 or {r["center"] for r in terms} != centers
                    or any(r["handedness"] != "PRESERVED" for r in terms)):
                reasons.append("CANDIDATE_FOUR_SUGAR_CENTERS_NOT_PRESERVED")
            if not reasons:
                report["status"] = "CANDIDATE_PRESERVED"
    if reasons:
        report["status"] = "REVIEW"
    if any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError("FANA inspection input changed during assessment")
    return report
