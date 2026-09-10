import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.autorefine import AutoRefineError
from nasolve.cli import _workspace_run, build_parser, main
from nasolve.config import AppConfig, ConfigError, WorkspaceSettings
from nasolve.coot_runtime import CootInstallation
from nasolve.coot_view import launch_coot_view
from nasolve.model_assessment import file_sha256
from nasolve.refine_doctor import RefineDoctorError

from .helpers import pdb_record, symlinked_temporary_directory
from .test_coot_view import add_manual_checkpoint, add_review_checkpoint, make_view_run


class CLITests(unittest.TestCase):
    def test_show_active_run_and_explicit_overrides_report_exact_sources(self):
        with symlinked_temporary_directory() as directory:
            root = Path(directory)
            active = make_view_run(root, 1)
            newest = make_view_run(root, 2)
            add_review_checkpoint(active)
            config = AppConfig(workspace=WorkspaceSettings(
                dataset=str(active.parent.parent), run=str(active),
            ))
            coot = root / "coot"
            coot.write_text("")
            launch = partial(
                launch_coot_view,
                launcher=lambda *args, **kwargs: SimpleNamespace(pid=1234),
            )
            cases = (
                (["show"], active, "refine-001", "current refinement checkpoint refine-001"),
                (["show", str(active), "--checkpoint", "refine-002"], active,
                 "refine-002", "requested refinement checkpoint refine-002 (REVIEW)"),
                (["show", str(newest), "--stage", "autosol"], newest,
                 None, "PostMR ReadySet prepared model with separate AutoSol HA sites"),
                (["show", "last"], newest, "refine-001", "current refinement checkpoint refine-001"),
            )
            with (
                patch("nasolve.cli.load_config", return_value=config),
                patch("nasolve.cli.save_config"),
                patch("nasolve.cli.discover_coot", return_value=CootInstallation(coot, "test", "fixture")),
                patch("nasolve.cli.launch_coot_view", side_effect=launch),
            ):
                for arguments, run, checkpoint, source in cases:
                    output = io.StringIO()
                    with self.subTest(arguments=arguments), redirect_stdout(output):
                        self.assertEqual(main(arguments), 0)
                    text = output.getvalue()
                    self.assertIn(f"in run: {run.resolve()}", text)
                    self.assertIn(source, text)
                    self.assertIn("Map source:", text)
                    pen = run / "CootGUI" / ("autorefine" if checkpoint else "autosol")
                    if checkpoint:
                        pen /= checkpoint
                    record = json.loads((pen / "launch.json").read_text())
                    self.assertEqual(record["run_directory"], str(run.resolve()))
                    self.assertEqual(record["checkpoint_id"], checkpoint)
                    self.assertIn(record["map_source"], text)
                    self.assertIn(record["model_path"], text)
                    self.assertIn(record["map_path"], text)
                    self.assertEqual(config.workspace.run, str(active))

    def test_bare_show_opens_current_imported_model_in_active_workspace(self):
        with symlinked_temporary_directory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            model = add_manual_checkpoint(run)
            config = AppConfig(workspace=WorkspaceSettings(run=str(run)))
            coot = root / "coot"
            coot.write_text("")
            output = io.StringIO()
            with (
                patch("nasolve.cli.load_config", return_value=config),
                patch("nasolve.cli.save_config"),
                patch("nasolve.cli.discover_coot", return_value=CootInstallation(coot, "test", "fixture")),
                patch("nasolve.cli.launch_coot_view", side_effect=partial(
                    launch_coot_view, launcher=lambda *args, **kwargs: SimpleNamespace(pid=1234),
                )),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["show"]), 0)
            self.assertIn(f"Model: {model.resolve()}", output.getvalue())
            self.assertIn("current manual checkpoint manual-001", output.getvalue())
            self.assertIn("inherited refinement checkpoint refine-001", output.getvalue())

    def test_autorefine_forwards_discovered_phenix_version(self):
        installation = SimpleNamespace(
            version="1.20.1-4487",
            executables={
                "phenix.refine": Path("/phenix/phenix.refine"),
                "phenix.mtz.dump": Path("/phenix/phenix.mtz.dump"),
            },
            environment={"PATH": "/phenix"},
        )
        with (
            patch("nasolve.cli.load_config", return_value=AppConfig()),
            patch("nasolve.cli._workspace_run", return_value=Path("/dataset/AutoMR/run_001")),
            patch("nasolve.cli.discover_phenix", return_value=installation),
            patch("nasolve.cli.remember_phenix"),
            patch("nasolve.cli.save_config"),
            patch(
                "nasolve.cli.execute_autorefine",
                side_effect=AutoRefineError("sentinel"),
            ) as execute,
        ):
            self.assertEqual(main(["autorefine", "run_001"]), 2)

        self.assertEqual(execute.call_args.kwargs["phenix_version"], installation.version)

    def test_refine_doctor_forwards_discovered_phenix_version(self):
        installation = SimpleNamespace(
            version="2.1-6048",
            executables={
                "phenix.refine": Path("/phenix/phenix.refine"),
                "phenix.mtz.dump": Path("/phenix/phenix.mtz.dump"),
            },
            environment={"PATH": "/phenix"},
        )
        with (
            patch("nasolve.cli.load_config", return_value=AppConfig()),
            patch("nasolve.cli._workspace_run", return_value=Path("/dataset/AutoMR/run_001")),
            patch("nasolve.cli.discover_phenix", return_value=installation),
            patch("nasolve.cli.remember_phenix"),
            patch("nasolve.cli.save_config"),
            patch(
                "nasolve.cli.execute_refine_doctor",
                side_effect=RefineDoctorError("sentinel"),
            ) as execute,
        ):
            self.assertEqual(main(["refine-doctor", "run_001"]), 2)

        self.assertEqual(execute.call_args.kwargs["phenix_version"], installation.version)

    def test_refine_doctor_unknown_version_is_a_guarded_cli_error(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "dataset" / "AutoMR" / "run_001"
            installation = SimpleNamespace(
                version="unknown",
                executables={
                    "phenix.refine": Path("/phenix/phenix.refine"),
                    "phenix.mtz.dump": Path("/phenix/phenix.mtz.dump"),
                },
                environment={"PATH": "/phenix"},
            )
            with (
                patch("nasolve.cli.load_config", return_value=AppConfig()),
                patch("nasolve.cli._workspace_run", return_value=run),
                patch("nasolve.cli.discover_phenix", return_value=installation),
                patch("nasolve.cli.remember_phenix"),
                patch("nasolve.cli.save_config"),
            ):
                self.assertEqual(main(["refine-doctor", "run_001"]), 2)

            self.assertFalse((run / "RefineDoctor").exists())

    def test_workspace_drives_checkpoint_commands_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            run = dataset / "AutoMR" / "run_004"
            model = run / "PostMR" / "Model" / "readyset_model.pdb"
            model.parent.mkdir(parents=True)
            model.write_text(pdb_record("ATOM", 1, "P", "DA", "A", 1) + "END\n")
            observations = dataset / "staraniso.mtz"
            observations.write_bytes(b"observations")
            report = {
                "workflow": "automr",
                "inputs": {
                    "reflections": str(observations),
                    "reflections_sha256": file_sha256(observations),
                },
                "postmr": {
                    "status": "POSTMR_READY",
                    "prepared_model": str(model),
                    "prepared_sha256": file_sha256(model),
                    "restraints": [],
                },
            }
            (run / "report.json").write_text(json.dumps(report))
            config_path = root / "config.json"

            with patch.dict(
                "os.environ", {"NASOLVE_CONFIG_FILE": str(config_path)}, clear=False
            ):
                self.assertEqual(main(["workspace", "use", str(run)]), 0)
                self.assertEqual(main(["checkpoints", "list"]), 0)
                self.assertEqual(main(["checkpoints", "use", "postmr"]), 0)
                self.assertEqual(main(["workspace", "clear"]), 0)

    def test_workspace_run_rejects_non_object_report(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "dataset" / "AutoMR" / "run_001"
            run.mkdir(parents=True)
            (run / "report.json").write_text(json.dumps([]))
            config = AppConfig(workspace=WorkspaceSettings(run=str(run)))

            with self.assertRaisesRegex(ConfigError, "not a JSON object"):
                _workspace_run(None, config)

    def test_workspace_and_optional_active_targets(self):
        parser = build_parser()
        workspace = parser.parse_args(["workspace", "use", "dataset/AutoMR/run_004"])
        self.assertEqual(workspace.workspace_action, "use")
        self.assertEqual(str(workspace.target), "dataset/AutoMR/run_004")
        self.assertIsNone(parser.parse_args(["autorefine"]).run)
        self.assertIsNone(parser.parse_args(["checkpoints", "list"]).run)
        self.assertIsNone(parser.parse_args(["show"]).target)

    def test_standard_frame_shortcuts(self):
        parser = build_parser()
        w = parser.parse_args(["automr", "dataset", "-W", "--pair", "D:T"])
        self.assertEqual((w.command, w.frame, w.pair), ("automr", "W", "D:T"))
        three_gbi = parser.parse_args(["automr", "dataset", "-3GBI", "--pair", "D:T"])
        self.assertEqual(three_gbi.frame, "3GBI")
        shunted = parser.parse_args([
            "automr", "dataset", "-W", "--pair", "D:T", "--allow-p1-standard",
            "--execute",
        ])
        self.assertTrue(shunted.allow_p1_standard)
        self.assertTrue(shunted.execute)
        mirrored = parser.parse_args([
            "automr", "dataset", "-W", "--pair", "D:T", "--mirror",
        ])
        self.assertTrue(mirrored.mirror)

    def test_postmr_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "postmr", "run_004", "--allow-mr-review", "--modified-pairs-only",
        ])
        self.assertEqual(args.command, "postmr")
        self.assertTrue(args.allow_mr_review)
        self.assertTrue(args.modified_pairs_only)

    def test_autosol_command(self):
        parser = build_parser()
        args = parser.parse_args(["autosol", "run_001"])
        self.assertEqual(args.command, "autosol")
        self.assertEqual(str(args.run), "run_001")

    def test_autorefine_and_checkpoint_commands(self):
        parser = build_parser()
        refine = parser.parse_args([
            "autorefine", "run_001", "--from", "clean", "--cycles", "5",
        ])
        self.assertEqual(refine.command, "autorefine")
        self.assertEqual(refine.from_checkpoint, "clean")
        self.assertEqual(refine.cycles, 5)
        doctor = parser.parse_args([
            "refine-doctor", "run_001", "--from", "refine-003", "--cycles", "3",
        ])
        self.assertEqual(doctor.command, "refine-doctor")
        self.assertEqual(doctor.from_checkpoint, "refine-003")
        self.assertEqual(doctor.cycles, 3)
        listing = parser.parse_args(["checkpoints", "list", "run_001"])
        self.assertEqual(listing.checkpoint_action, "list")
        add = parser.parse_args([
            "checkpoints", "add", "run_001", "--name", "after coot",
            "--model", "fixed.pdb",
        ])
        self.assertEqual(add.name, "after coot")
        self.assertEqual(str(add.model), "fixed.pdb")
        use = parser.parse_args(["checkpoints", "use", "run_001", "refine-001"])
        self.assertEqual(use.checkpoint, "refine-001")
        active_use = parser.parse_args(["checkpoints", "use", "refine-001"])
        self.assertEqual(active_use.run_or_checkpoint, "refine-001")
        self.assertIsNone(active_use.checkpoint)
        show = parser.parse_args(["show", "last", "dataset", "--stage", "autosol"])
        self.assertEqual(show.target, "last")
        self.assertEqual(str(show.dataset), "dataset")
        self.assertEqual(show.stage, "autosol")
        inspect = parser.parse_args([
            "show", "run_001", "--checkpoint", "refine-005",
        ])
        self.assertEqual(inspect.checkpoint, "refine-005")


if __name__ == "__main__":
    unittest.main()
