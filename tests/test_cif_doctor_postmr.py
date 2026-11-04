"""Read-only CIF Doctor receipts at the PostMR preparation boundaries."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from nasolve.cif_doctor import assess_dictionaries
from nasolve.model_assessment import file_sha256
from nasolve.postmr import (
    MutationAction, PostMRPreparationError, _cif_doctor_assessment, prepare_postmr,
)
from nasolve.run_context import resolve_artifact_path

from .helpers import make_postmr_report
from .test_phosphate import phosphate, without_extra
from .test_postmr import make_data_root, postmr_model_text


def _no_pairs(prepared, compatibility, pair_file, output):
    pair_file.write_text("")
    return {"retained_pair_count": 0, "retained_pairs": [], "modified_sites": []}


def _references(value):
    if isinstance(value, dict):
        if "anchor" in value and "sha256" in value:
            yield value
        for nested in value.values():
            yield from _references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _references(nested)


def _run_fixture(tmp_path, monkeypatch, *, mutate=False):
    original = tmp_path / "original.pdb"
    original.write_text(postmr_model_text("DG" if mutate else "DE", "DC"))
    run = tmp_path / "dataset/AutoMR/run_001"
    report_path = make_postmr_report(run, original)
    report = json.loads(report_path.read_text())
    report["frame"] = None
    report["post_mr_plan"] = {"sequences": {}, "standard_pair": None, "mutations": {}}
    report_path.write_text(json.dumps(report))
    data_root = make_data_root(tmp_path)

    if mutate:
        monkeypatch.setattr(
            "nasolve.postmr.build_mutation_plan",
            lambda *args, **kwargs: (
                MutationAction("A:12", "DG", "DE", "coot-parent-overlap", "DT"),
            ),
        )

        def coot(source, output, actions, executable, coot_dir, *args):
            receipt = coot_dir.parent / "Restraints/cif_doctor_mutation.json"
            assert receipt.is_file(), "mutation dictionaries must be assessed before Coot"
            payload = json.loads(receipt.read_text())
            assert payload["stage"] == "postmr-mutation-source"
            assert payload["inputs"][0]["anchor"] == "run"
            assert payload.get("model") is None, "parent coordinates are not target geometry"
            output.write_text(source.read_text().replace(" DG ", " DE "))
            log = coot_dir / "coot.log"
            log.write_text("mocked Coot")
            return coot_dir / "mutate.py", log

        monkeypatch.setattr("nasolve.postmr._run_coot", coot)

        def restore(source, output, *args):
            shutil.copyfile(source, output)
            return {}

        monkeypatch.setattr("nasolve.postmr._restore_shared_parent_coordinates", restore)

    def readyset(command, cwd, **kwargs):
        receipt = cwd.parent / "Restraints/cif_doctor_source.json"
        assert receipt.is_file(), "frozen source/runtime inputs must be assessed before ReadySet"
        payload = json.loads(receipt.read_text())
        assert payload["stage"] == "postmr-source"
        assert payload["runtime_assessment"]["stage"] == "postmr-runtime-source"
        assert all(item["anchor"] == "run" for item in payload["inputs"])
        prepared = Path(command[1])
        (cwd / "prepared_model.updated.pdb").write_bytes(prepared.read_bytes())
        (cwd / "prepared_model.ligands.cif").write_text("data_ligands\n")
        return SimpleNamespace(returncode=0, stdout="mocked ReadySet")

    monkeypatch.setattr("nasolve.postmr.subprocess.run", readyset)
    result = prepare_postmr(
        run, tmp_path / "ready_set", coot_executable=tmp_path / "coot" if mutate else None,
        data_root=data_root, modified_pairs_only=True, modified_pair_builder=_no_pairs,
    )
    return run, result, original, data_root


def test_postmr_records_findings_without_changing_readiness_or_sources(tmp_path, monkeypatch):
    run, result, original, data_root = _run_fixture(tmp_path, monkeypatch)
    assert result.status == "POSTMR_READY"
    report = json.loads(result.report_path.read_text())
    doctor = report["cif_doctor"]
    assert doctor["mode"] == "report-only"
    assert doctor["coordinate_changes"] is False
    assert doctor["native_interpretation"] == "UNASSESSED"
    digest = doctor["effective"]["solution_report"]
    assert digest["requires_cif_review"] is False
    assert digest["native_selection"] == "NOT_RUN" and digest["pdf_status"] == "PLANNED"
    source = resolve_artifact_path(doctor["source"]["report"], run)
    effective = resolve_artifact_path(doctor["effective"]["report"], run)
    source_receipt = json.loads(source.read_text())
    effective_receipt = json.loads(effective.read_text())
    # This established input fixture deliberately has only bond rows. The
    # assessor must expose incomplete chemistry without becoming a new gate.
    assert source_receipt["status"] in {"REVIEW", "INVALID", "UNASSESSED"}
    assert effective_receipt["stage"] == "postmr-effective"
    assert [item["relative_path"] for item in effective_receipt["inputs"]] == [
        item["relative_path"] for item in report["refinement_restraints"]
    ]
    assert effective_receipt["model"]["relative_path"] == "PostMR/Model/readyset_model.pdb"
    assert (run / "PostMR/Restraints/source_dictionaries/DE.cif").read_bytes() == (
        data_root / "ligands/DE.cif"
    ).read_bytes()
    assert original.read_text() == postmr_model_text("DE", "DC")
    assert json.loads((run / "report.json").read_text())["postmr"]["cif_doctor"] == doctor


def test_mutation_receipt_precedes_coot_and_all_receipt_refs_relocate(tmp_path, monkeypatch):
    run, result, original, data_root = _run_fixture(tmp_path, monkeypatch, mutate=True)
    report = json.loads(result.report_path.read_text())
    assert report["cif_doctor"]["mutation"]["report"]["relative_path"] == (
        "PostMR/Restraints/cif_doctor_mutation.json"
    )
    moved_dataset = tmp_path / "relocated"
    shutil.copytree(run.parents[1], moved_dataset)
    shutil.rmtree(run.parents[1])
    shutil.rmtree(data_root)
    original.unlink()
    moved_run = moved_dataset / "AutoMR/run_001"
    for key in ("mutation", "source", "effective"):
        reference = report["cif_doctor"][key]["report"]
        receipt_path = resolve_artifact_path(reference, moved_run)
        assert receipt_path is not None and file_sha256(receipt_path) == reference["sha256"]
        receipt = json.loads(receipt_path.read_text())
        for item in _references(receipt):
            assert item["anchor"] == "run"
            path = resolve_artifact_path(item, moved_run)
            assert path is not None and path.is_relative_to(moved_run)
            assert file_sha256(path) == item["sha256"]


def test_effective_receipt_uses_selected_definition_not_competing_readyset_output(tmp_path, monkeypatch):
    original = tmp_path / "original.pdb"
    original.write_text("".join(without_extra(phosphate())).replace("1AP", " DZ"))
    run = tmp_path / "dataset/AutoMR/run_001"
    report_path = make_postmr_report(run, original)
    report = json.loads(report_path.read_text())
    report["frame"] = None
    report["post_mr_plan"] = {"sequences": {}, "standard_pair": None, "mutations": {}}
    report_path.write_text(json.dumps(report))
    dictionary = Path(__file__).parents[1] / "src/nasolve/data/ligands/DZ.cif"

    def readyset(command, cwd, **kwargs):
        (cwd / "prepared_model.updated.pdb").write_bytes(Path(command[1]).read_bytes())
        (cwd / "prepared_model.ligands.cif").write_bytes(dictionary.read_bytes())
        return SimpleNamespace(returncode=0, stdout="mocked ReadySet")

    monkeypatch.setattr("nasolve.postmr.subprocess.run", readyset)
    result = prepare_postmr(
        run, tmp_path / "ready_set", modified_pairs_only=True,
        modified_pair_builder=_no_pairs,
    )
    report = json.loads(result.report_path.read_text())
    receipt_path = resolve_artifact_path(report["cif_doctor"]["effective"]["report"], run)
    receipt = json.loads(receipt_path.read_text())
    paths = [item["relative_path"] for item in receipt["inputs"]]
    assert "PostMR/Restraints/DZ.cif" in paths
    assert "PostMR/ReadySet/prepared_model.ligands.cif" not in paths
    assert paths == [item["relative_path"] for item in report["refinement_restraints"]]
    assert receipt["dictionary_precedence"]["policy"] == "parameterized-inputs-over-readyset-v2"
    assert receipt["dictionary_precedence"]["raw_readyset_dictionary"]["relative_path"] == (
        "PostMR/ReadySet/prepared_model.ligands.cif"
    )
    assert (run / "PostMR/ReadySet/prepared_model.ligands.cif").read_bytes() == dictionary.read_bytes()


@pytest.mark.parametrize("change_model", [False, True])
def test_postmr_receipt_cannot_rebind_old_findings_to_changed_content(tmp_path, monkeypatch, change_model):
    dictionary = tmp_path / "source.cif"
    dictionary.write_text("data_test\n")
    model = tmp_path / "model.pdb"
    model.write_text(postmr_model_text("DE", "DC"))

    def changed_after_assessment(paths, **kwargs):
        result = assess_dictionaries(paths, **kwargs)
        changed = model if change_model else dictionary
        changed.write_text(changed.read_text() + "\n# changed\n")
        return result

    monkeypatch.setattr("nasolve.postmr.assess_dictionaries", changed_after_assessment)
    with pytest.raises(PostMRPreparationError, match="changed while binding CIF Doctor assessment"):
        _cif_doctor_assessment([dictionary], tmp_path, stage="postmr-effective", model=model)
