import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from nasolve.coot_view import (
    find_last_run,
    launch_coot_view,
    resolve_run,
    resolve_view_profile,
)


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


if __name__ == "__main__":
    unittest.main()
