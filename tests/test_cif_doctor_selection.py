"""Choose a usable fallback without making students adjudicate dictionaries."""
from dataclasses import replace

import pytest


def candidate(name="native", **changes):
    from nasolve.cif_doctor_selection import ComponentCandidate
    return ComponentCandidate(
        candidate_id=name, component="ZZ9", source_priority=1,
        artifact_sha256="a" * 64, chemistry_sha256="b" * 64,
        integrity_verified=True, native_usable=True, chemistry_preserved=True,
        essential_restraints_present=True, finite_parameters=True,
        stereochemistry="UNASSESSED", **changes,
    )


def test_nonconvergence_is_not_a_student_cif_approval_gate():
    from nasolve.cif_doctor_selection import select_component_candidate
    original = candidate()
    repaired = replace(original, candidate_id="repaired", converged=False,
                       objective_id="fixed-v1", target=12., warnings=("sugar pucker differs",))
    original = replace(original, objective_id="fixed-v1", target=30.)
    q = select_component_candidate([original, repaired])
    assert q["selected_candidate"] == "repaired" and q["continue_solving"]
    assert q["status"] == "CONTINUE_WITH_NOTES" and not q["requires_cif_review"]
    assert "did not converge" in q["report_text"]


@pytest.mark.parametrize("defect", ["integrity_verified", "native_usable", "chemistry_preserved",
                                  "essential_restraints_present", "finite_parameters", "stereochemistry"])
def test_known_broken_repair_falls_back_to_native_without_changing_mechanics(defect):
    from nasolve.cif_doctor_selection import select_component_candidate
    native = candidate()
    repair = replace(native, candidate_id="repair", **{defect: "INVERTED" if defect == "stereochemistry" else False})
    q = select_component_candidate([repair, native])
    assert q["selected_candidate"] == "native" and q["continue_solving"]
    assert q["excluded_candidates"][0]["candidate_id"] == "repair"
    assert not q["requires_cif_review"] and q["mechanics_changed"] is False


def test_unknown_evidence_is_not_a_pass_or_an_inversion():
    from nasolve.cif_doctor_selection import select_component_candidate
    q = select_component_candidate([candidate()])
    assert q["continue_solving"] and q["status"] == "CONTINUE_WITH_NOTES"
    assert q["selected_stereochemistry"] == "UNASSESSED"
    assert "not independently established" in q["report_text"]


def test_no_usable_candidate_stops_for_a_concrete_reason_without_cif_homework():
    from nasolve.cif_doctor_selection import select_component_candidate
    q = select_component_candidate([replace(candidate(), native_usable=False)])
    assert q["selected_candidate"] is None and not q["continue_solving"]
    assert q["status"] == "NO_USABLE_DICTIONARY" and not q["requires_cif_review"]


def test_established_stereo_is_preferred_to_unknown_within_source_authority():
    from nasolve.cif_doctor_selection import select_component_candidate
    known = replace(candidate("preserved"), stereochemistry="PRESERVED")
    assert select_component_candidate([candidate(), known])["selected_candidate"] == "preserved"


def test_authoritative_source_wins_and_incomparable_energies_are_not_ranked():
    from nasolve.cif_doctor_selection import select_component_candidate
    a = replace(candidate("curated"), source_priority=0, target=100., objective_id="A")
    b = replace(a, candidate_id="native", source_priority=1, target=0.)
    c = replace(a, candidate_id="incomparable", target=-1., objective_id="B")
    assert select_component_candidate([b, a])["selected_candidate"] == "curated"
    assert select_component_candidate([a, c])["selected_candidate"] == "curated"


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -float("inf")])
def test_nonfinite_endpoint_is_excluded(value):
    from nasolve.cif_doctor_selection import select_component_candidate
    q = select_component_candidate([replace(candidate(), objective_id="fixed", target=value), candidate("fallback")])
    assert q["selected_candidate"] == "fallback"


def test_different_chemical_states_or_duplicate_ids_are_rejected():
    from nasolve.cif_doctor_selection import select_component_candidate
    with pytest.raises(ValueError):
        select_component_candidate([candidate(), replace(candidate("other"), chemistry_sha256="c" * 64)])
    with pytest.raises(ValueError):
        select_component_candidate([candidate(), candidate()])


def test_report_summary_preserves_offline_findings_without_claiming_native_selection():
    from nasolve.cif_doctor_selection import assessment_report_summary
    assessment = {"status": "REVIEW", "components": [{"component_id": "ZZ9", "status": "REVIEW"}],
                  "summary": {"component_count": 1, "finding_counts": {"REVIEW": 2}}}
    q = assessment_report_summary(assessment)
    assert not q["requires_cif_review"] and q["native_selection"] == "NOT_RUN"
    assert q["assessment_status"] == "REVIEW" and q["component_ids"] == ["ZZ9"]
    assert q["pdf_status"] == "PLANNED" and "reported" in q["text"]
