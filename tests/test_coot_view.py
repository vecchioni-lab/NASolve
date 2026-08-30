import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from nasolve.coot_view import (
    CootViewError,
    find_last_run,
    launch_coot_view,
    resolve_run,
    resolve_view_profile,
)
from nasolve.model_assessment import file_sha256
from nasolve.run_context import artifact_reference


def make_view_run(root: Path, number: int = 1) -> Path:
    run = root / "dataset" / "AutoMR" / f"run_{number:03d}"
    phaser = run / "Phaser"
    postmr_model = run / "PostMR" / "Model"
    readyset = run / "PostMR" / "ReadySet"
    autosol = run / "AutoSol" / "AutoSol_run_1_"
    round_dir = run / "AutoRefine" / "round_001"
    for path in (phaser, postmr_model, readyset, autosol, round_dir):
        path.mkdir(parents=True)
    phaser_model = phaser / "mr_solution.pdb"
    phaser_map = phaser / "mr_solution.mtz"
    postmr = postmr_model / "readyset_model.pdb"
    dictionary = readyset / "prepared_model.ligands.cif"
    ha = autosol / "overall_best_ha_pdb.pdb"
    denmod = autosol / "overall_best_denmod_map_coeffs.mtz"
    refined = round_dir / "refined_001.pdb"
    refine_map = round_dir / "refined_001_map_coeffs.mtz"
    for path in (phaser_model, postmr, ha, refined):
        path.write_text("END\n")
    for path in (phaser_map, denmod, refine_map):
        path.write_bytes(b"mtz")
    dictionary.write_text("data_ligands\n")
    report = {
        "workflow": "automr",
        "execution": {
            "phaser": {
                "solution_pdb": str(phaser_model.resolve()),
                "solution_mtz": str(phaser_map.resolve()),
            },
        },
        "postmr": {
            "status": "POSTMR_READY",
            "prepared_model": str(postmr.resolve()),
            "restraints": [],
            "readyset": {"generated_ligand_cif": str(dictionary.resolve())},
        },
        "autosol": {
            "outputs": {"heavy_atom_model": str(ha.resolve())},
        },
    }
    (run / "report.json").write_text(json.dumps(report))
    registry = {
        "schema_version": 1,
        "current": "refine-001",
        "checkpoints": [{
            "id": "refine-001",
            "kind": "refinement",
            "model": {"path": str(refined.resolve())},
            "restraints": [{"path": str(dictionary.resolve())}],
            "outputs": {"map_coefficients": str(refine_map.resolve())},
        }],
    }
    (run / "AutoRefine" / "checkpoints.json").write_text(json.dumps(registry))
    return run


def add_review_checkpoint(run: Path) -> tuple[Path, Path]:
    round_dir = run / "AutoRefine" / "round_002"
    round_dir.mkdir()
    model = round_dir / "refined_001.pdb"
    map_path = round_dir / "refined_001.mtz"
    model.write_text("REVIEW\nEND\n")
    map_path.write_bytes(b"review maps")
    registry_path = run / "AutoRefine" / "checkpoints.json"
    registry = json.loads(registry_path.read_text())
    registry["checkpoints"].append({
        "id": "refine-002",
        "kind": "refinement",
        "model": {"path": str(model.resolve())},
        "restraints": [],
        "outputs": {"map_coefficients": str(map_path.resolve())},
    })
    registry_path.write_text(json.dumps(registry))
    return model, map_path


class CootViewTests(unittest.TestCase):
    def test_profiles_rebase_after_checkout_moves(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_run = make_view_run(root / "collaborator")
            source_dataset = source_run.parent.parent
            checkout_dataset = root / "checkout" / source_dataset.name
            shutil.copytree(source_dataset, checkout_dataset)
            shutil.rmtree(root / "collaborator")
            run = checkout_dataset / "AutoMR" / source_run.name

            postmr = resolve_view_profile(run, stage="postmr")
            refined = resolve_view_profile(run, stage="autorefine")

            self.assertTrue(postmr.model_path.is_relative_to(run.resolve()))
            self.assertTrue(refined.model_path.is_relative_to(run.resolve()))

    def test_show_last_uses_highest_run_number_not_mtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = make_view_run(root, 1)
            tenth = make_view_run(root, 10)
            self.assertEqual(find_last_run(root / "dataset"), tenth.resolve())
            self.assertEqual(resolve_run("last", root / "dataset"), tenth.resolve())
            self.assertNotEqual(first, tenth)

    def test_profiles_choose_stage_specific_models_and_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            automatic = resolve_view_profile(run)
            self.assertEqual(automatic.stage, "autorefine")
            self.assertEqual(automatic.model_path.name, "refined_001.pdb")
            self.assertEqual(automatic.map_path.name, "refined_001_map_coeffs.mtz")
            autosol = resolve_view_profile(run, stage="autosol")
            self.assertEqual(autosol.model_path.name, "mr_solution.pdb")
            self.assertEqual(autosol.extra_model_paths[0].name, "overall_best_ha_pdb.pdb")
            self.assertEqual(autosol.map_path.name, "overall_best_denmod_map_coeffs.mtz")
            postmr = resolve_view_profile(run, stage="postmr")
            self.assertEqual(postmr.model_path.name, "readyset_model.pdb")
            self.assertEqual(postmr.dictionary_paths[0].name, "prepared_model.ligands.cif")

    def test_postmr_view_fails_when_reported_dictionary_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            report = json.loads((run / "report.json").read_text())
            dictionary = Path(
                report["postmr"]["readyset"]["generated_ligand_cif"]
            )
            dictionary.unlink()

            with self.assertRaisesRegex(CootViewError, "dictionary is missing"):
                resolve_view_profile(run, stage="postmr")

    def test_autosol_view_rejects_changed_heavy_atom_model(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            report_path = run / "report.json"
            report = json.loads(report_path.read_text())
            heavy_atom = Path(report["autosol"]["outputs"]["heavy_atom_model"])
            report["autosol"]["outputs"]["heavy_atom_model_sha256"] = (
                file_sha256(heavy_atom)
            )
            report_path.write_text(json.dumps(report))
            heavy_atom.write_text("changed\n")

            with self.assertRaisesRegex(CootViewError, "failed checksum"):
                resolve_view_profile(run, stage="autosol")

    def test_autosol_warning_without_outputs_falls_back_to_postmr(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            shutil.rmtree(run / "AutoRefine")
            report_path = run / "report.json"
            report = json.loads(report_path.read_text())
            report["autosol"] = {
                "status": "AUTOSOL_WARNING",
                "outputs": {
                    "heavy_atom_model": None,
                    "refinement_data": None,
                    "console_log": str(run / "AutoSol" / "autosol.console.log"),
                },
            }
            report_path.write_text(json.dumps(report))

            profile = resolve_view_profile(run)

            self.assertEqual(profile.stage, "postmr")

    def test_autorefine_profile_reads_schema_two_artifact_references(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())
            checkpoint = registry["checkpoints"][0]
            model = Path(checkpoint["model"]["path"])
            dictionary = Path(checkpoint["restraints"][0]["path"])
            map_path = Path(checkpoint["outputs"]["map_coefficients"])
            checkpoint["model"] = artifact_reference(model, run)
            checkpoint["model"]["sha256"] = file_sha256(model)
            checkpoint["restraints"] = [artifact_reference(dictionary, run)]
            checkpoint["restraints"][0]["sha256"] = file_sha256(dictionary)
            checkpoint["outputs"]["map_coefficients"] = artifact_reference(
                map_path, run
            )
            checkpoint["outputs"]["map_coefficients"]["sha256"] = file_sha256(
                map_path
            )
            registry["schema_version"] = 2
            registry_path.write_text(json.dumps(registry))

            profile = resolve_view_profile(run, stage="autorefine")

            self.assertEqual(profile.model_path, model.resolve())
            self.assertEqual(profile.map_path, map_path.resolve())
            self.assertEqual(profile.dictionary_paths, (dictionary.resolve(),))

    def test_schema_two_view_rejects_changed_map_and_dictionary(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())
            checkpoint = registry["checkpoints"][0]
            model = Path(checkpoint["model"]["path"])
            map_path = Path(checkpoint["outputs"]["map_coefficients"])
            dictionary = Path(checkpoint["restraints"][0]["path"])
            model_ref = artifact_reference(model, run)
            model_ref["sha256"] = file_sha256(model)
            map_ref = artifact_reference(map_path, run)
            map_ref["sha256"] = file_sha256(map_path)
            dictionary_ref = artifact_reference(dictionary, run)
            dictionary_ref["sha256"] = file_sha256(dictionary)
            checkpoint["model"] = model_ref
            checkpoint["outputs"]["map_coefficients"] = map_ref
            checkpoint["restraints"] = [dictionary_ref]
            registry["schema_version"] = 2
            registry_path.write_text(json.dumps(registry))

            map_path.write_bytes(b"changed map")
            with self.assertRaisesRegex(CootViewError, "map coefficients"):
                resolve_view_profile(run, stage="autorefine")
            with self.assertRaisesRegex(CootViewError, "map coefficients"):
                resolve_view_profile(run)

            map_path.write_bytes(b"mtz")
            map_ref["sha256"] = file_sha256(map_path)
            registry_path.write_text(json.dumps(registry))
            dictionary.write_text("changed dictionary\n")
            with self.assertRaisesRegex(CootViewError, "ligand dictionary"):
                resolve_view_profile(run, stage="autorefine")

    def test_unknown_or_non_integer_checkpoint_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())

            for version in (True, 1.0, 2.0, 999):
                registry["schema_version"] = version
                registry_path.write_text(json.dumps(registry))
                with self.subTest(version=version):
                    with self.assertRaisesRegex(
                        CootViewError, "Unsupported checkpoint schema"
                    ):
                        resolve_view_profile(run)

    def test_unknown_current_checkpoint_pointer_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())
            registry["current"] = "missing-checkpoint"
            registry_path.write_text(json.dumps(registry))

            with self.assertRaisesRegex(CootViewError, "current pointer is unknown"):
                resolve_view_profile(run)

    def test_autorefine_profile_recovers_legacy_primary_mtz(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())
            reported = Path(registry["checkpoints"][0]["outputs"]["map_coefficients"])
            reported.unlink()
            registry["checkpoints"][0]["outputs"]["map_coefficients"] = None
            registry_path.write_text(json.dumps(registry))
            legacy = run / "AutoRefine" / "round_001" / "refined_001.mtz"
            legacy.write_bytes(b"legacy maps")
            profile = resolve_view_profile(run, stage="autorefine")
            self.assertEqual(profile.map_path, legacy.resolve())

    def test_schema_two_primary_mtz_requires_valid_output_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            registry_path = run / "AutoRefine" / "checkpoints.json"
            registry = json.loads(registry_path.read_text())
            checkpoint = registry["checkpoints"][0]
            model = Path(checkpoint["model"]["path"])
            dictionary = Path(checkpoint["restraints"][0]["path"])
            reported_map = Path(checkpoint["outputs"]["map_coefficients"])
            reported_map.unlink()
            primary = model.with_suffix(".mtz")
            primary.write_bytes(b"primary maps")
            model_ref = artifact_reference(model, run)
            model_ref["sha256"] = file_sha256(model)
            dictionary_ref = artifact_reference(dictionary, run)
            dictionary_ref["sha256"] = file_sha256(dictionary)
            primary_ref = artifact_reference(primary, run)
            primary_ref["sha256"] = file_sha256(primary)
            checkpoint["model"] = model_ref
            checkpoint["restraints"] = [dictionary_ref]
            checkpoint["outputs"]["map_coefficients"] = None
            checkpoint["outputs"]["refinement_reflections"] = primary_ref
            registry["schema_version"] = 2
            registry_path.write_text(json.dumps(registry))

            profile = resolve_view_profile(run, stage="autorefine")
            self.assertEqual(profile.map_path, primary.resolve())

            primary.write_bytes(b"changed maps")
            with self.assertRaisesRegex(CootViewError, "refinement reflections"):
                resolve_view_profile(run, stage="autorefine")

            primary.write_bytes(b"primary maps")
            checkpoint["outputs"]["refinement_reflections"] = None
            registry_path.write_text(json.dumps(registry))
            with self.assertRaisesRegex(CootViewError, "refinement reflections"):
                resolve_view_profile(run, stage="autorefine")

    def test_specific_checkpoint_can_be_inspected_without_selecting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            run = make_view_run(Path(directory))
            model, map_path = add_review_checkpoint(run)
            profile = resolve_view_profile(run, checkpoint="refine-002")
            self.assertEqual(profile.model_path, model.resolve())
            self.assertEqual(profile.map_path, map_path.resolve())
            registry = json.loads(
                (run / "AutoRefine" / "checkpoints.json").read_text()
            )
            self.assertEqual(registry["current"], "refine-001")

    def test_launcher_uses_stage_local_pen_and_all_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            coot = root / "coot"
            coot.write_text("")
            calls: list[tuple[list[str], dict[str, object]]] = []

            def launcher(command: list[str], **kwargs: object):
                calls.append((command, kwargs))
                return SimpleNamespace(pid=4321)

            result = launch_coot_view(
                run,
                coot,
                stage="autosol",
                environment={"PATH": "/usr/bin:/bin"},
                launcher=launcher,
            )
            self.assertEqual(result.pid, 4321)
            self.assertEqual(
                result.working_directory,
                (run / "CootGUI" / "autosol").resolve(),
            )
            command, kwargs = calls[0]
            self.assertEqual(command.count("--pdb"), 2)
            self.assertIn("--auto", command)
            self.assertEqual(kwargs["cwd"], result.working_directory)
            self.assertTrue(str(kwargs["env"]["COOT_BACKUP_DIR"]).endswith("backups"))

    def test_specific_checkpoint_gets_its_own_coot_pen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            add_review_checkpoint(run)
            coot = root / "coot"
            coot.write_text("")

            def launcher(command: list[str], **kwargs: object):
                return SimpleNamespace(pid=1234)

            result = launch_coot_view(
                run,
                coot,
                checkpoint="refine-002",
                environment={"PATH": "/usr/bin:/bin"},
                launcher=launcher,
            )
            self.assertEqual(
                result.working_directory,
                (run / "CootGUI" / "autorefine" / "refine-002").resolve(),
            )

    def test_launcher_rejects_checkpoint_path_components(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            coot = root / "coot"
            coot.write_text("")

            for checkpoint in ("../../escape", str(root / "escape")):
                with self.subTest(checkpoint=checkpoint):
                    with self.assertRaisesRegex(CootViewError, "single safe"):
                        launch_coot_view(
                            run,
                            coot,
                            checkpoint=checkpoint,
                            launcher=lambda *args, **kwargs: SimpleNamespace(pid=1),
                        )
            self.assertFalse((root / "escape").exists())

    def test_launcher_rejects_symlinked_scratch_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            coot = root / "coot"
            coot.write_text("")
            outside = root / "outside"
            outside.mkdir()
            (run / "CootGUI").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(CootViewError, "symbolic link"):
                launch_coot_view(
                    run,
                    coot,
                    stage="automr",
                    launcher=lambda *args, **kwargs: SimpleNamespace(pid=1),
                )
            self.assertEqual(list(outside.iterdir()), [])

    def test_launcher_rejects_symlinked_backup_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_view_run(root)
            coot = root / "coot"
            coot.write_text("")
            outside = root / "outside"
            outside.mkdir()
            working = run / "CootGUI" / "automr"
            working.mkdir(parents=True)
            (working / "backups").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(CootViewError, "symbolic link"):
                launch_coot_view(
                    run,
                    coot,
                    stage="automr",
                    launcher=lambda *args, **kwargs: SimpleNamespace(pid=1),
                )
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
