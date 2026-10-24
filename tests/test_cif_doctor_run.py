import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.checkpoints import (
    CheckpointError, inherited_paths, initialize_registry, read_registry,
)
from nasolve.cif_doctor_run import assess_run
from nasolve.model_assessment import file_sha256
from nasolve.run_context import artifact_reference

from .test_checkpoints import make_checkpoint_run


def _descriptor(path, **extra):
    return {"name": path.name, "sha256": file_sha256(path), "size": path.stat().st_size, **extra}


def _assessor(paths, *, stage, model):
    return {
        "stage": stage,
        "status": "UNASSESSED",
        "inputs": [_descriptor(path, input_index=index) for index, path in enumerate(paths)],
        "model": _descriptor(model),
    }


def _snapshot(root):
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*") if path.is_file()
    }


def _reference(path, run):
    return {**artifact_reference(path, run), "sha256": file_sha256(path), "size": path.stat().st_size}


def _child(run):
    _, registry = initialize_registry(run)
    root = registry["checkpoints"][0]
    directory = run / "AutoRefine" / "refine_001"
    directory.mkdir()
    model = directory / "refined.pdb"
    model.write_text("REMARK selected child\n" + (run / "PostMR/Model/readyset_model.pdb").read_text())
    cif = directory / "effective.cif"
    cif.write_text("data_effective\n")
    eff = directory / "effective.eff"
    eff.write_text("refinement {}\n")
    phil = run / "PostMR/Restraints/narestraints.phil"
    child = {
        **root, "id": "refine-001", "parent": "postmr", "recipe": "test-child",
        "model": _reference(model, run),
        "restraints": [_reference(path, run) for path in (phil, cif, eff)],
    }
    registry["checkpoints"].append(child)
    registry["current"] = "refine-001"
    registry["bookmarks"] = {"first-refinement": "refine-001"}
    (run / "AutoRefine/checkpoints.json").write_text(json.dumps(registry))
    return child


class CifDoctorRunTests(unittest.TestCase):
    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_uninitialized_run_assessment_does_not_write_or_initialize(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            before = _snapshot(root)
            result = assess_run(run)
            self.assertEqual(before, _snapshot(root))
            self.assertFalse((run / "AutoRefine").exists())
            self.assertEqual(result["run_context"]["registry_source"], "derived_postmr_root")
            self.assertIsNone(result["run_context"]["registry"])
            self.assertEqual(result["run_context"]["checkpoint"]["id"], "postmr")
            self.assertEqual(result["run_context"]["observations"]["anchor"], "dataset")
            paths = assessor.call_args.args[0]
            self.assertEqual([path.name for path in paths], ["narestraints.phil", "prepared_model.ligands.cif"])

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_current_checkpoint_full_effective_bundle_and_model_are_used(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            _child(run)
            before = _snapshot(root)
            result = assess_run(run)
            self.assertEqual(before, _snapshot(root))
            self.assertEqual(result["run_context"]["checkpoint"]["id"], "refine-001")
            self.assertEqual(result["run_context"]["registry_source"], "frozen_registry")
            self.assertEqual([path.name for path in assessor.call_args.args[0]], ["narestraints.phil", "effective.cif", "effective.eff"])
            self.assertEqual(assessor.call_args.kwargs["model"], run / "AutoRefine/refine_001/refined.pdb")
            self.assertEqual(result["model"]["frozen_reference"]["relative_path"], "AutoRefine/refine_001/refined.pdb")
            for descriptor in result["inputs"]:
                self.assertEqual(descriptor["frozen_reference"]["anchor"], "run")
                self.assertEqual(descriptor["sha256"], descriptor["frozen_reference"]["sha256"])

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_explicit_checkpoint_and_bookmark_never_change_selection(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            _child(run)
            before = _snapshot(root)
            result = assess_run(run, checkpoint="postmr")
            self.assertEqual(result["run_context"]["checkpoint"]["id"], "postmr")
            self.assertEqual(result["run_context"]["checkpoint"]["current"], "refine-001")
            result = assess_run(run, checkpoint="first-refinement")
            self.assertEqual(result["run_context"]["checkpoint"]["id"], "refine-001")
            self.assertEqual(before, _snapshot(root))

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_frozen_input_checksum_changes_block_without_assessment(self, assessor):
        for relative in ("AutoRefine/refine_001/refined.pdb", "AutoRefine/refine_001/effective.cif", "../staraniso.mtz"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                run = make_checkpoint_run(root)
                _child(run)
                path = run.parent.parent / "staraniso.mtz" if relative == "../staraniso.mtz" else run / relative
                path.write_bytes(b"changed frozen input")
                before = _snapshot(root)
                with self.assertRaisesRegex(CheckpointError, "changed after it was frozen"):
                    assess_run(run)
                self.assertEqual(before, _snapshot(root))
                assessor.assert_not_called()

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_missing_declared_dictionary_does_not_search_by_basename(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            _child(run)
            cif = run / "AutoRefine/refine_001/effective.cif"
            alternate = run / "PostMR/Restraints/effective.cif"
            alternate.write_bytes(cif.read_bytes())
            cif.unlink()
            before = _snapshot(root)
            with self.assertRaisesRegex(CheckpointError, "restraint is missing"):
                assess_run(run)
            self.assertEqual(before, _snapshot(root))
            assessor.assert_not_called()

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_malformed_bundle_is_not_silently_partially_assessed(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            child = _child(run)
            path = run / "AutoRefine/checkpoints.json"
            registry = json.loads(path.read_text())
            registry["checkpoints"][-1]["restraints"] = [child["restraints"][0], "undeclared.cif"]
            path.write_text(json.dumps(registry))
            with self.assertRaisesRegex(CheckpointError, "Malformed frozen checkpoint restraint list"):
                assess_run(run)
            assessor.assert_not_called()

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_relocated_checkpoint_assesses_after_original_path_is_gone(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_checkpoint_run(root / "original")
            _child(source)
            destination = root / "relocated/dataset"
            shutil.copytree(source.parent.parent, destination)
            shutil.rmtree(root / "original")
            run = destination / "AutoMR/run_001"
            before = _snapshot(destination)
            result = assess_run(run)
            self.assertEqual(before, _snapshot(destination))
            self.assertEqual(result["run_context"]["checkpoint"]["id"], "refine-001")
            self.assertTrue(all(path.is_relative_to(run) for path in assessor.call_args.args[0]))
            self.assertNotIn(str(root / "original"), json.dumps(result))
            self.assertEqual(result["run_context"]["observations"]["relative_path"], "staraniso.mtz")

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_legacy_external_input_is_visible_as_nonportable_provenance(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            _child(run)
            external = root / "external.cif"
            external.write_text("data_external\n")
            path = run / "AutoRefine/checkpoints.json"
            registry = json.loads(path.read_text())
            registry["checkpoints"][-1]["restraints"] = [_reference(external, run)]
            path.write_text(json.dumps(registry))
            before = _snapshot(root)
            result = assess_run(run)
            self.assertEqual(before, _snapshot(root))
            reference = result["inputs"][0]["frozen_reference"]
            self.assertFalse(reference["portable"])
            self.assertEqual(reference["provenance_path"], str(external))
            self.assertEqual(reference["sha256"], file_sha256(external))
            self.assertNotIn("absolute_path", reference)
            self.assertNotIn("anchor", reference)

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_changed_registry_or_report_during_selection_is_rejected(self, assessor):
        for relative in ("AutoRefine/checkpoints.json", "report.json"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as directory:
                run = make_checkpoint_run(Path(directory))
                _child(run)

                def read_then_change(selected_run):
                    result = read_registry(selected_run)
                    path = selected_run / relative
                    changed = json.loads(path.read_text())
                    if relative.endswith("checkpoints.json"):
                        changed["current"] = "postmr"
                    else:
                        changed["annotation"] = "changed after selection"
                    path.write_text(json.dumps(changed))
                    return result

                with patch("nasolve.cif_doctor_run.read_registry", side_effect=read_then_change):
                    with self.assertRaisesRegex(CheckpointError, "changed during read-only assessment"):
                        assess_run(run)
                assessor.assert_not_called()

    @patch("nasolve.cif_doctor_run.assess_dictionaries")
    def test_input_change_during_assessment_is_not_receipted_as_frozen(self, assessor):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _child(run)

            def change_input(paths, *, stage, model):
                result = _assessor(paths, stage=stage, model=model)
                paths[1].write_text("changed during interpretation\n")
                return result

            assessor.side_effect = change_input
            with self.assertRaisesRegex(CheckpointError, "changed during read-only assessment"):
                assess_run(run)

    @patch("nasolve.cif_doctor_run.assess_dictionaries", side_effect=_assessor)
    def test_change_after_resolver_before_snapshot_still_fails_frozen_hash(self, assessor):
        for key in ("model", "restraints"):
            with self.subTest(input=key), tempfile.TemporaryDirectory() as directory:
                run = make_checkpoint_run(Path(directory))
                _child(run)
                calls = 0

                def resolve_then_change(selected, selected_run):
                    nonlocal calls
                    result = inherited_paths(selected, selected_run)
                    calls += 1
                    if calls == 1:
                        path = result["model"] if key == "model" else result["restraints"][1]
                        path.write_text("changed after frozen hash verification\n")
                    return result

                with patch("nasolve.cif_doctor_run.inherited_paths", side_effect=resolve_then_change):
                    with self.assertRaisesRegex(CheckpointError, "changed after it was frozen"):
                        assess_run(run)
                self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
