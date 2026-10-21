"""Automatic component decisions from verified evidence, without editing mechanics.

This pure policy consumes trusted adapter results, not user assertions or CIF
scores. It performs no generation, optimization, file adoption or checkpoint
selection. Production candidate acquisition/native qualification remain separate
adapters; PostMR currently uses only the plain-language assessment summary.
"""
from dataclasses import dataclass
import math
import re
from typing import Sequence

POLICY_ID = "cif-automatic-usable-fallback-v1"


@dataclass(frozen=True)
class ComponentCandidate:
    candidate_id: str
    component: str
    source_priority: int
    artifact_sha256: str
    chemistry_sha256: str
    integrity_verified: bool
    native_usable: bool
    chemistry_preserved: bool
    essential_restraints_present: bool
    finite_parameters: bool
    stereochemistry: str  # PRESERVED / UNASSESSED / INVERTED
    converged: bool | None = None
    objective_id: str | None = None
    target: float | None = None
    warnings: tuple[str, ...] = ()


def select_component_candidate(candidates: Sequence[ComponentCandidate]) -> dict:
    """Retain the first authoritative usable candidate or its best fixed endpoint.

    Lower source_priority means stronger declared source authority. Within that
    tier, prefer demonstrated preservation of stereo, then minimize only when
    *all* remaining usable records share one explicit fixed
    objective and finite targets. Otherwise preserve caller's declared order.
    Convergence, pucker and unknown stereo are notes; demonstrated inversion or
    unusable chemistry excludes that candidate and triggers automatic fallback.
    Bounded optimization belongs upstream and must retain its best valid state.
    """
    rows = list(candidates)
    if len(rows) > 64 or len({r.candidate_id for r in rows}) != len(rows):
        raise ValueError("Require at most 64 uniquely named component candidates")
    if len({(r.component, r.chemistry_sha256) for r in rows}) > 1:
        raise ValueError("Candidate selection requires one declared component/chemical state")
    required = ("integrity_verified", "native_usable", "chemistry_preserved",
                "essential_restraints_present", "finite_parameters")
    usable, excluded = [], []
    for r in rows:
        if (not r.candidate_id or not r.component or type(r.source_priority) is not int
                or r.source_priority < 0 or r.stereochemistry not in {"PRESERVED", "UNASSESSED", "INVERTED"}
                or any(type(getattr(r, key)) is not bool for key in required)
                or (r.converged is not None and type(r.converged) is not bool)
                or any(not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                       for digest in [r.artifact_sha256, r.chemistry_sha256])
                or any(not isinstance(w, str) for w in r.warnings)
                or (r.objective_id is not None and (not isinstance(r.objective_id, str) or not r.objective_id))):
            raise ValueError("Malformed verified candidate evidence")
        reasons = [key for key in required if not getattr(r, key)]
        if r.stereochemistry == "INVERTED":
            reasons.append("demonstrated_stereochemical_inversion")
        if r.target is not None and (type(r.target) not in (int, float) or not math.isfinite(r.target)):
            reasons.append("nonfinite_endpoint_target")
        if reasons:
            excluded.append({"candidate_id": r.candidate_id, "artifact_sha256": r.artifact_sha256,
                             "reasons": reasons})
        else:
            usable.append(r)
    decision = {"schema_version": 1, "policy_id": POLICY_ID,
                "requires_cif_review": False, "mechanics_changed": False,
                "excluded_candidates": excluded, "automatic_adoption": False}
    if not usable:
        return {**decision, "status": "NO_USABLE_DICTIONARY", "continue_solving": False,
                "selected_candidate": None,
                "report_text": "No usable component dictionary is available; automatic recovery could not supply the required restraints."}
    priority = min(r.source_priority for r in usable)
    tier = [r for r in usable if r.source_priority == priority]
    established = [r for r in tier if r.stereochemistry == "PRESERVED"]
    if established:
        tier = established
    comparable = (all(r.objective_id and r.target is not None for r in tier)
                  and len({r.objective_id for r in tier}) == 1)
    chosen = min(tier, key=lambda r: r.target) if comparable else tier[0]
    notes = list(chosen.warnings)
    if chosen.converged is False:
        notes.append("The bounded component optimization did not converge; a usable saved candidate was retained.")
    if chosen.stereochemistry == "UNASSESSED":
        notes.append("Absolute stereochemistry was not independently established.")
    if excluded:
        notes.append("Unusable alternatives were excluded automatically.")
    text = f"{chosen.component}: NASolve selected {chosen.candidate_id}."
    if notes:
        text += " " + " ".join(notes)
    return {**decision, "status": "CONTINUE_WITH_NOTES" if notes else "CONTINUE",
            "continue_solving": True, "selected_candidate": chosen.candidate_id,
            "selected_sha256": chosen.artifact_sha256, "chemistry_sha256": chosen.chemistry_sha256,
            "selected_stereochemistry": chosen.stereochemistry, "converged": chosen.converged,
            "ranking": "FIXED_OBJECTIVE" if comparable else "DECLARED_SOURCE_ORDER",
            "notes": notes, "report_text": text}


def assessment_report_summary(assessment: dict) -> dict:
    """Render existing report-only evidence without inventing a native decision."""
    status = assessment["status"]
    components = sorted({r["component_id"] for r in assessment.get("components", [])})
    return {"schema_version": 1, "policy_id": POLICY_ID,
            "assessment_status": status, "component_ids": components,
            "requires_cif_review": False, "native_selection": "NOT_RUN",
            "pdf_status": "PLANNED",
            "text": ("Dictionary checks are reported with the solution. "
                     "CIF inspection is not required to continue. "
                     "Existing model and usable-restraint checks still apply."),
            "finding_counts": dict(assessment.get("summary", {}).get("finding_counts", {}))}
