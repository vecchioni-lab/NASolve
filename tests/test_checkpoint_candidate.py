import json
import tempfile
import unittest
from pathlib import Path

from nasolve.checkpoint_candidate import (
    CheckpointCandidateError,
    describe_checkpoint_candidate,
)
from nasolve.checkpoints import append_checkpoint, initialize_registry, resolve_checkpoint
from nasolve.model_assessment import file_sha256

from .test_checkpoints import make_checkpoint_run


class CheckpointCandidateTests(unittest.TestCase):
    def test_postmr_descriptor_is_read_only_and_not_a_donor_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            before = {
                path.relative_to(run): path.read_bytes()
                for path in run.rglob("*")
                if path.is_file()
            }

            descriptor = describe_checkpoint_candidate(run)

            after = {
                path.relative_to(run): path.read_bytes()
                for path in run.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)
            self.assertFalse((run / "AutoRefine").exists())

            source = descriptor["source"]
            self.assertEqual(source["checkpoint_id"], "postmr")
            self.assertEqual(source["lineage"], ["postmr"])
            self.assertEqual(source["status"], "READY")
            self.assertTrue(source["usable"])
            self.assertTrue(source["locally_reusable"])
            self.assertTrue(source["selected_current"])

            model = descriptor["model"]
            prepared = Path(
                json.loads((run / "report.json").read_text())["postmr"]["prepared_model"]
            )
            self.assertEqual(model["artifact"]["sha256"], file_sha256(prepared))
            self.assertEqual(model["assessment"]["polymer_residue_count"], 1)
            self.assertEqual(model["assessment"]["residue_identities"], [
                {"site": "A:1", "residue_code": "DA"},
            ])

            self.assertEqual(
                descriptor["source_observations"]["semantics"],
                "source-provenance-only; not recipient evidence",
            )
            self.assertIsNone(
                descriptor["run_context"]["checkpoint_model_target_comparison"]
            )
            self.assertEqual(descriptor["semantics"], {
                "descriptive_only": True,
                "checkpoint_local_reusable": True,
                "donor_eligibility": None,
                "recipient_compatibility": None,
                "automatic_reuse_authorized": False,
            })

    def test_success_child_reports_exact_lineage_without_promoting_donor_eligibility(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            run, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            payload = {
                "id": "refine-001",
                "parent": "postmr",
                "kind": "refinement",
                "status": "SUCCESS",
                "usable": True,
                "recipe": "test/refinement",
                "label": None,
                "model": dict(root["model"]),
                "observations": dict(root["observations"]),
                "phases": root.get("phases"),
                "restraints": list(root.get("restraints", [])),
                "metrics": {"r_work": 0.15, "r_free": 0.17},
                "compatibility": {"validated": True},
            }
            append_checkpoint(run, registry, payload, select=True)

            descriptor = describe_checkpoint_candidate(run)
            self.assertEqual(
                descriptor["source"]["lineage"],
                ["postmr", "refine-001"],
            )
            self.assertEqual(descriptor["source"]["checkpoint_id"], "refine-001")
            self.assertEqual(descriptor["source"]["status"], "SUCCESS")
            self.assertTrue(descriptor["source"]["locally_reusable"])
            self.assertTrue(descriptor["source"]["selected_current"])
            self.assertEqual(
                descriptor["metrics"],
                {"r_work": 0.15, "r_free": 0.17},
            )
            self.assertIsNone(descriptor["semantics"]["donor_eligibility"])
            self.assertFalse(
                descriptor["semantics"]["automatic_reuse_authorized"]
            )

    def test_descriptor_accepts_bookmark_but_preserves_underlying_checkpoint_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            run, registry = initialize_registry(run)
            registry["bookmarks"] = {"clean model": "postmr"}
            from nasolve.checkpoints import save_registry
            save_registry(run, registry)

            descriptor = describe_checkpoint_candidate(run, "clean model")
            self.assertEqual(descriptor["source"]["checkpoint_id"], "postmr")
            self.assertEqual(descriptor["source"]["lineage"], ["postmr"])

    def test_changed_checkpoint_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_checkpoint_run(Path(directory))
            run, registry = initialize_registry(run)
            root = resolve_checkpoint(registry, "postmr")
            model_path = run / root["model"]["relative_path"]
            model_path.write_text(model_path.read_text() + "REMARK changed\n")

            with self.assertRaisesRegex(
                CheckpointCandidateError,
                "model.*missing|model.*checksum|changed",
            ):
                describe_checkpoint_candidate(run)

    def test_cycle_or_unknown_parent_in_lineage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root_dir = Path(directory)
            for parent in ("refine-001", "missing-parent"):
                with self.subTest(parent=parent):
                    run = make_checkpoint_run(root_dir / parent)
                    run, registry = initialize_registry(run)
                    root = resolve_checkpoint(registry, "postmr")
                    payload = {
                        "id": "refine-001",
                        "parent": "postmr",
                        "kind": "refinement",
                        "status": "SUCCESS",
                        "usable": True,
                        "recipe": "test/refinement",
                        "label": None,
                        "model": dict(root["model"]),
                        "observations": dict(root["observations"]),
                        "phases": root.get("phases"),
                        "restraints": list(root.get("restraints", [])),
                        "metrics": {},
                        "compatibility": {"validated": True},
                    }
                    append_checkpoint(run, registry, payload, select=True)
                    path = run / "AutoRefine" / "checkpoints.json"
                    data = json.loads(path.read_text())
                    for item in data["checkpoints"]:
                        if item["id"] == "refine-001":
                            item["parent"] = parent
                    path.write_text(json.dumps(data))

                    with self.assertRaisesRegex(
                        CheckpointCandidateError,
                        "cycle|unknown parent",
                    ):
                        describe_checkpoint_candidate(run)


if __name__ == "__main__":
    unittest.main()
