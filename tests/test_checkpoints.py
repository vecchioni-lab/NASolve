import json
import shutil
import tempfile
import unittest
from pathlib import Path

from nasolve.checkpoints import (
    CheckpointError,
    add_checkpoint,
    inherited_paths,
    initialize_registry,
    list_checkpoints,
    resolve_checkpoint,
    select_checkpoint,
)
from nasolve.model_assessment import file_sha256

from .helpers import pdb_record


def make_checkpoint_run(root: Path) -> Path:
    dataset = root / "dataset"
    run = dataset / "AutoMR" / "run_001"
    model_dir = run / "PostMR" / "Model"
    restraint_dir = run / "PostMR" / "Restraints"
    readyset_dir = run / "PostMR" / "ReadySet"
    model_dir.mkdir(parents=True)
    restraint_dir.mkdir(parents=True)
    readyset_dir.mkdir(parents=True)
    reflections = dataset / "staraniso.mtz"
    reflections.parent.mkdir(exist_ok=True)
    reflections.write_bytes(b"original observations")
    model = model_dir / "readyset_model.pdb"
    model.write_text(pdb_record("ATOM", 1, "P", "DA", "A", 1) + "END\n")
    phil = restraint_dir / "narestraints.phil"
    phil.write_text("geometry_restraints {}\n")
    input_cif = restraint_dir / "C38.cif"
    input_cif.write_text("data_C38\n")
    generated_cif = readyset_dir / "prepared_model.ligands.cif"
    generated_cif.write_text("data_readyset\n")
    report = {
        "workflow": "automr",
        "stage": "postmr",
        "status": "POSTMR_READY",
        "inputs": {
            "reflections": str(reflections.resolve()),
            "reflections_sha256": file_sha256(reflections),
        },
        "postmr": {
            "status": "POSTMR_READY",
            "created_utc": "2026-08-28T12:00:00+00:00",
            "prepared_model": str(model.resolve()),
            "prepared_sha256": file_sha256(model),
            "restraints": [str(phil.resolve()), str(input_cif.resolve())],
            "readyset": {"generated_ligand_cif": str(generated_cif.resolve())},
            "mutation_actions": [],
            "anomalous": {"candidates": []},
        },
    }
    (run / "report.json").write_text(json.dumps(report))
    return run


class CheckpointTests(unittest.TestCase):
    def test_non_object_report_and_registry_are_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_run = make_checkpoint_run(root / "report")
            (report_run / "report.json").write_text(json.dumps([]))
            with self.assertRaisesRegex(CheckpointError, "not a JSON object"):
                initialize_registry(report_run)

            registry_run = make_checkpoint_run(root / "registry")
            registry_path = registry_run / "AutoRefine" / "checkpoints.json"
            registry_path.parent.mkdir(parents=True)
            registry_path.write_text(json.dumps([]))
            with self.assertRaisesRegex(CheckpointError, "not a JSON object"):
                initialize_registry(registry_run)

    def test_non_integer_checkpoint_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            registry_path = run / "AutoRefine" / "checkpoints.json"

            for version in (True, 1.0, 2.0):
                registry["schema_version"] = version
                registry_path.write_text(json.dumps(registry))
                with self.subTest(version=version):
                    with self.assertRaisesRegex(CheckpointError, "Unsupported"):
                        initialize_registry(run)

    def test_collaborator_report_rebases_and_writes_portable_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_run = make_checkpoint_run(root / "collaborator")
            source_dataset = source_run.parent.parent
            checkout_dataset = root / "checkout" / source_dataset.name
            shutil.copytree(source_dataset, checkout_dataset)
            shutil.rmtree(root / "collaborator")
            run = (checkout_dataset / "AutoMR" / source_run.name).resolve()
            checkout_dataset = checkout_dataset.resolve()

            _, registry = initialize_registry(run)
            checkpoint = resolve_checkpoint(registry, "postmr")
            paths = inherited_paths(checkpoint, run)

            self.assertTrue(str(paths["model"]).startswith(str(run)))
            self.assertTrue(str(paths["observations"]).startswith(str(checkout_dataset)))
            self.assertEqual(checkpoint["model"]["anchor"], "run")
            self.assertEqual(checkpoint["observations"]["anchor"], "dataset")
            self.assertEqual(
                checkpoint["model"]["relative_path"],
                "PostMR/Model/readyset_model.pdb",
            )
            self.assertEqual(registry["schema_version"], 2)
            registry_text = (run / "AutoRefine" / "checkpoints.json").read_text()
            self.assertNotIn(str(root / "collaborator"), registry_text)

    def test_initial_checkpoint_uses_readyset_dictionary_and_authoritative_data(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            paths = inherited_paths(root, run)
            self.assertEqual(registry["current"], "postmr")
            self.assertEqual(paths["observations"].read_bytes(), b"original observations")
            restraint_names = [path.name for path in paths["restraints"]]
            self.assertEqual(
                restraint_names,
                ["narestraints.phil", "prepared_model.ligands.cif"],
            )
            self.assertEqual(
                root["compatibility"]["observations_checksum"], "verified"
            )

    def test_superseded_input_cif_need_not_be_committed(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            report = json.loads((run / "report.json").read_text())
            input_cif = Path(report["postmr"]["restraints"][1])
            input_cif.unlink()

            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            names = [path.name for path in inherited_paths(root, run)["restraints"]]

            self.assertEqual(
                names, ["narestraints.phil", "prepared_model.ligands.cif"]
            )

    def test_legacy_report_without_reflection_hash_is_marked_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            report_path = run / "report.json"
            report = json.loads(report_path.read_text())
            del report["inputs"]["reflections_sha256"]
            report_path.write_text(json.dumps(report))

            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")

            self.assertEqual(
                root["compatibility"]["observations_checksum"],
                "legacy-unverified",
            )

    def test_changed_report_reflections_are_rejected_before_freezing(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            report = json.loads((run / "report.json").read_text())
            Path(report["inputs"]["reflections"]).write_bytes(b"replacement")

            with self.assertRaisesRegex(CheckpointError, "frozen checksum"):
                initialize_registry(run)

    def test_schema_one_registry_migrates_to_schema_two_on_write(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            paths = inherited_paths(root, run)
            registry["schema_version"] = 1
            root["model"] = {
                "path": str(paths["model"]),
                "sha256": root["model"]["sha256"],
            }
            root["observations"] = {
                "path": str(paths["observations"]),
                "sha256": root["observations"]["sha256"],
            }
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry_path.write_text(json.dumps(registry))

            add_checkpoint(run, name="migration trigger")

            migrated = json.loads(registry_path.read_text())
            migrated_root = resolve_checkpoint(migrated, "postmr")
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated_root["model"]["anchor"], "run")
            self.assertIn("relative_path", migrated_root["model"])

    def test_missing_schema_one_artifacts_migrate_to_provenance_only(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            missing_model = (
                Path("/collaborator/dataset/AutoMR")
                / run.name
                / "Missing"
                / "model.pdb"
            )
            missing_log = (
                Path("/collaborator/dataset/AutoMR")
                / run.name
                / "AutoRefine"
                / "missing.log"
            )
            root["model"] = {
                "path": str(missing_model),
                "sha256": "0" * 64,
            }
            root["outputs"] = {"full_log": str(missing_log)}
            registry["schema_version"] = 1
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry_path.write_text(json.dumps(registry))

            add_checkpoint(run, name="migration trigger")

            migrated = json.loads(registry_path.read_text())
            migrated_root = resolve_checkpoint(migrated, "postmr")
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(
                migrated_root["model"]["provenance_path"], str(missing_model)
            )
            self.assertFalse(migrated_root["model"]["available"])
            self.assertNotIn("path", migrated_root["model"])
            self.assertEqual(
                migrated_root["outputs"]["full_log"]["provenance_path"],
                str(missing_log),
            )
            self.assertFalse(migrated_root["outputs"]["full_log"]["available"])

    def test_bookmark_does_not_duplicate_immutable_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            record = add_checkpoint(run, name="clean postmr")
            records, current, bookmarks = list_checkpoints(run)
            self.assertEqual(record.checkpoint_id, "postmr")
            self.assertEqual(len(records), 1)
            self.assertEqual(current, "postmr")
            self.assertEqual(bookmarks["clean postmr"], "postmr")

    def test_manual_import_is_a_review_child_and_can_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            manual = root / "manual.pdb"
            manual.write_text(pdb_record("ATOM", 1, "P", "DA", "A", 1) + "END\n")
            record = add_checkpoint(run, name="after coot", model=manual)
            self.assertEqual(record.status, "REVIEW")
            self.assertEqual(record.parent, "postmr")
            _, current_before, _ = list_checkpoints(run)
            self.assertEqual(current_before, "postmr")
            selected = select_checkpoint(run, "after coot")
            self.assertEqual(selected.checkpoint_id, record.checkpoint_id)
            _, current_after, _ = list_checkpoints(run)
            self.assertEqual(current_after, record.checkpoint_id)

    def test_duplicate_bookmark_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            add_checkpoint(run, name="clean")
            with self.assertRaisesRegex(CheckpointError, "already exists"):
                add_checkpoint(run, name="clean")

    def test_replacement_mtz_requires_imported_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_checkpoint_run(root)
            mtz = root / "replacement.mtz"
            mtz.write_bytes(b"mtz")
            with self.assertRaisesRegex(CheckpointError, "only when importing"):
                add_checkpoint(run, name="bad import", reflections=mtz)

    def test_frozen_observation_checksum_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            observations = inherited_paths(root, run)["observations"]
            assert isinstance(observations, Path)
            observations.write_bytes(b"changed observations")
            with self.assertRaisesRegex(CheckpointError, "changed after it was frozen"):
                inherited_paths(root, run)

    def test_schema_two_critical_reference_requires_valid_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            original = dict(root["model"])

            for invalid in (None, "", 123):
                root["model"] = dict(original)
                if invalid is None:
                    root["model"].pop("sha256")
                else:
                    root["model"]["sha256"] = invalid
                with self.subTest(invalid=invalid):
                    with self.assertRaisesRegex(CheckpointError, "malformed checksum"):
                        inherited_paths(root, run)


if __name__ == "__main__":
    unittest.main()
