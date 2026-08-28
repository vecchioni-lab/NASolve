import json
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
        "inputs": {"reflections": str(reflections.resolve())},
        "postmr": {
            "status": "POSTMR_READY",
            "created_utc": "2026-08-28T12:00:00+00:00",
            "prepared_model": str(model.resolve()),
            "restraints": [str(phil.resolve()), str(input_cif.resolve())],
            "readyset": {"generated_ligand_cif": str(generated_cif.resolve())},
            "mutation_actions": [],
            "anomalous": {"candidates": []},
        },
    }
    (run / "report.json").write_text(json.dumps(report))
    return run


class CheckpointTests(unittest.TestCase):
    def test_initial_checkpoint_uses_readyset_dictionary_and_authoritative_data(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            _, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            paths = inherited_paths(root)
            self.assertEqual(registry["current"], "postmr")
            self.assertEqual(paths["observations"].read_bytes(), b"original observations")
            restraint_names = [path.name for path in paths["restraints"]]
            self.assertEqual(
                restraint_names,
                ["narestraints.phil", "prepared_model.ligands.cif"],
            )

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
            observations = Path(root["observations"]["path"])
            observations.write_bytes(b"changed observations")
            with self.assertRaisesRegex(CheckpointError, "changed after it was frozen"):
                inherited_paths(root)


if __name__ == "__main__":
    unittest.main()
