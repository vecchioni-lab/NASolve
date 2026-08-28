import json
import stat
import tempfile
import unittest
from pathlib import Path

from nasolve.autorefine import (
    AutoRefineError,
    anomalous_selections,
    build_reflection_plan,
    execute_autorefine,
    parse_refinement_statistics,
)
from nasolve.checkpoints import list_checkpoints

from .helpers import pdb_record


def make_refine_run(root: Path, *, autosol: bool = True) -> Path:
    dataset = root / "dataset"
    run = dataset / "AutoMR" / "run_001"
    model_dir = run / "PostMR" / "Model"
    restraints_dir = run / "PostMR" / "Restraints"
    readyset_dir = run / "PostMR" / "ReadySet"
    model_dir.mkdir(parents=True)
    restraints_dir.mkdir(parents=True)
    readyset_dir.mkdir(parents=True)
    observations = dataset / "staraniso.mtz"
    observations.parent.mkdir(exist_ok=True)
    observations.write_bytes(b"observations")
    model = model_dir / "readyset_model.pdb"
    model.write_text(
        pdb_record("ATOM", 1, "P", "S6G", "A", 12)
        + pdb_record("HETATM", 2, "I", "C38", "B", 4, element="I")
        + "END\n"
    )
    phil = restraints_dir / "narestraints.phil"
    phil.write_text("geometry_restraints {}\n")
    readyset_cif = readyset_dir / "prepared_model.ligands.cif"
    readyset_cif.write_text("data_components\n")
    report = {
        "workflow": "automr",
        "stage": "postmr",
        "status": "POSTMR_READY",
        "inputs": {"reflections": str(observations.resolve())},
        "postmr": {
            "status": "POSTMR_READY",
            "created_utc": "2026-08-28T12:00:00+00:00",
            "prepared_model": str(model.resolve()),
            "restraints": [str(phil.resolve())],
            "readyset": {"generated_ligand_cif": str(readyset_cif.resolve())},
            "mutation_actions": [
                {"site": "A:12", "before": "DC", "after": "S6G"},
                {"site": "B:4", "before": "DG", "after": "C38"},
            ],
            "anomalous": {
                "candidates": [{
                    "site": "B:4",
                    "residue": "C38",
                    "atom_name": "I",
                    "alternate": None,
                    "element": "I",
                    "coordinates": [1.0, 2.0, 3.0],
                }],
            },
        },
    }
    if autosol:
        phase = run / "AutoSol" / "overall_best_refine_data.mtz"
        phase.parent.mkdir(parents=True)
        phase.write_bytes(b"phases")
        report["stage"] = "autosol"
        report["status"] = "AUTOSOL_READY"
        report["autosol"] = {
            "status": "AUTOSOL_READY",
            "use_for_refinement": True,
            "wavelength": 1.377618,
            "outputs": {"refinement_data": str(phase.resolve())},
        }
    (run / "report.json").write_text(json.dumps(report))
    return run


def make_mtz_dump(root: Path, *, anomalous: bool = True) -> Path:
    executable = root / "phenix.mtz.dump"
    anomalous_lines = (
        "printf '%s\\n' 'F(+) 1 G' 'SIGF(+) 1 L' 'F(-) 1 G' 'SIGF(-) 1 L'\n"
        if anomalous else ""
    )
    executable.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *overall_best*) printf '%s\\n' 'HLAM 1 A' 'HLBM 1 A' 'HLCM 1 A' 'HLDM 1 A';;\n"
        "  *) printf '%s\\n' 'IMEAN 1 J' 'SIGIMEAN 1 Q' 'FreeR_flag 1 I';\n"
        f"     {anomalous_lines}"
        "     printf '%s\\n' 'Resolution range: 20.0 5.27';\n"
        "     ;;\n"
        "esac\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def make_refine(
    root: Path,
    *,
    final_work: float = 0.274,
    final_free: float = 0.301,
    return_code: int = 0,
    preflight_return_code: int = 0,
) -> Path:
    executable = root / "phenix.refine"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import json, shutil, sys\n"
        "if '--dry_run' in sys.argv:\n"
        f"    preflight_return_code = {preflight_return_code}\n"
        "    print('Dry-run parameters accepted' if not preflight_return_code else 'ERROR bad parameter')\n"
        "    raise SystemExit(preflight_return_code)\n"
        "Path('received_args.json').write_text(json.dumps(sys.argv[1:]))\n"
        f"return_code = {return_code}\n"
        "if return_code:\n"
        "    print('Sorry: deliberate refinement failure')\n"
        "    raise SystemExit(return_code)\n"
        "model = next(Path(arg) for arg in sys.argv[1:] if arg.endswith('.pdb'))\n"
        "shutil.copyfile(model, 'refined_001.pdb')\n"
        "Path('refined_001.cif').write_text('data_model\\n')\n"
        "Path('refined_001.reflections.cif').write_text('data_reflections\\n')\n"
        "Path('refined_001_map_coeffs.mtz').write_bytes(b'maps')\n"
        "Path('refined_001_data.mtz').write_bytes(b'refine evidence')\n"
        "print('Start: r_work = 0.412 r_free = 0.438 bonds = 0.012 angles = 1.82')\n"
        "print('Macrocycle 1: r_work = 0.331 r_free = 0.359')\n"
        f"print('Final: r_work = {final_work} r_free = {final_free} bonds = 0.009 angles = 1.21')\n"
        "print('clashscore = 4.8')\n"
        "print('Anomalous scatterer group:')\n"
        "print('  Selection: \\\"chain B and resid 4 and name I\\\"')\n"
        "print('  Number of selected scatterers: 1')\n"
        "print('  f_prime: -1.8')\n"
        "print('  f_double_prime: 7.91907')\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    phenix_python = root / "phenix.python"
    phenix_python.write_text(
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *audit_free_r.py*) printf '%s\\n' 'NASOLVE_FREE_R_AUDIT_JSON:{\"array_anomalous\": true, \"stored_observations\": 2017, \"independent_friedel_groups\": 1010, \"paired_friedel_groups\": 1007, \"free_independent_groups\": 45, \"free_fraction\": 0.044554, \"inconsistent_friedel_flag_groups\": 0, \"test_flag_value\": 0, \"resolution_shells\": [{\"groups\": 101, \"free_groups\": 4}, {\"groups\": 101, \"free_groups\": 5}]}';;\n"
        "  *) printf '%s\\n' '5.750252723693848';;\n"
        "esac\n"
    )
    phenix_python.chmod(phenix_python.stat().st_mode | stat.S_IXUSR)
    return executable


class AutoRefineTests(unittest.TestCase):
    def test_plan_uses_friedel_amplitudes_phases_and_exact_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            report = json.loads((run / "report.json").read_text())
            observations = Path(report["inputs"]["reflections"])
            phase = Path(report["autosol"]["outputs"]["refinement_data"])
            plan = build_reflection_plan(
                report, observations, make_mtz_dump(root), phase_file=phase
            )
            self.assertEqual(plan.observation_labels, ("F(+)", "SIGF(+)", "F(-)", "SIGF(-)"))
            self.assertEqual(plan.phase_labels, ("HLAM", "HLBM", "HLCM", "HLDM"))
            self.assertTrue(plan.anomalous)
            self.assertEqual(
                anomalous_selections(report),
                ("chain B and resid 4 and name I",),
            )

    def test_success_is_quiet_checkpointed_and_reused_by_next_round(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            refine = make_refine(root)
            mtz_dump = make_mtz_dump(root)
            progress: list[tuple[str, Path]] = []
            first = execute_autorefine(
                run,
                refine,
                mtz_dump,
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
                progress=lambda checkpoint, log: progress.append((checkpoint, log)),
            )
            self.assertEqual(first.status, "AUTOREFINE_READY")
            self.assertEqual(progress[0][0], "refine-001")
            self.assertEqual(first.statistics["r_work"], 0.274)
            self.assertEqual(first.statistics["clashscore"], 4.8)
            anomalous = first.statistics["anomalous_scatterers"][0]
            self.assertAlmostEqual(anomalous["refined_f_double_prime"], 7.91907)
            self.assertAlmostEqual(anomalous["calculated_f_double_prime"], 5.750252723693848)
            self.assertAlmostEqual(anomalous["model_occupancy"], 1.0)
            self.assertAlmostEqual(anomalous["apparent_anomalous_occupancy"], 1.377168, places=5)
            self.assertAlmostEqual(anomalous["resolution_limit"], 5.27)
            self.assertTrue(first.log_path.is_file())
            self.assertEqual(first.model_cif.name, "refined_001.cif")
            self.assertEqual(first.reflection_cif.name, "refined_001.reflections.cif")
            self.assertTrue((first.round_directory / "metrics.tsv").is_file())
            args = json.loads((first.round_directory / "received_args.json").read_text())
            self.assertIn('main.target="auto"', args)
            self.assertIn("xray_data.labels=F(+),SIGF(+),F(-),SIGF(-)", args)
            run_report = json.loads((run / "report.json").read_text())
            self.assertIn(
                "xray_data.file_name=" + run_report["inputs"]["reflections"],
                args,
            )
            params = (first.round_directory / "autorefine.params").read_text()
            self.assertIn('target = "auto"', params)
            self.assertIn("strategy = *individual_sites *individual_sites_real_space", params)
            self.assertIn("individual = all", params)
            self.assertIn("group_adp_refinement_mode = one_adp_group_per_residue", params)
            self.assertIn("group = all", params)
            self.assertIn('selection = "chain B and resid 4 and name I"', params)
            self.assertIn("group_anomalous", params)

            second = execute_autorefine(
                run,
                refine,
                mtz_dump,
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
            )
            self.assertEqual(second.checkpoint_id, "refine-002")
            self.assertEqual(second.parent_checkpoint, "refine-001")
            second_report = json.loads(second.report_path.read_text())
            self.assertEqual(second_report["inputs"]["model"], str(first.model_path))
            self.assertTrue(second_report["inputs"]["authoritative_observations"].endswith("staraniso.mtz"))

    def test_review_checkpoint_does_not_replace_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            result = execute_autorefine(
                run,
                make_refine(root, final_work=0.31, final_free=0.34),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.status, "AUTOREFINE_REVIEW")
            records, current, _ = list_checkpoints(run)
            self.assertEqual(current, "postmr")
            self.assertEqual(records[-1].status, "REVIEW")
            self.assertTrue(records[-1].usable)

    def test_controlled_trial_can_disable_phases_real_space_occupancy_and_anomalous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            result = execute_autorefine(
                run,
                make_refine(root),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
                use_experimental_phases=False,
                real_space_sites=False,
                adp_mode="group",
                refine_occupancies=False,
                anomalous_mode="off",
                auto_select_success=False,
            )
            payload = json.loads(result.report_path.read_text())
            params = (result.round_directory / "autorefine.params").read_text()
            self.assertEqual(payload["inputs"]["phase_labels"], [])
            self.assertNotIn("individual_sites_real_space", params)
            self.assertNotIn("occupancies", params)
            self.assertNotIn("group_anomalous", params)
            self.assertFalse(result.selected_as_current)

    def test_missing_friedel_amplitudes_after_autosol_is_final_error_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            result = execute_autorefine(
                run,
                make_refine(root),
                make_mtz_dump(root, anomalous=False),
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.status, "AUTOREFINE_ANOMALOUS_FALLBACK")
            self.assertEqual(result.exit_code, 2)
            payload = json.loads(result.report_path.read_text())
            self.assertFalse(payload["refinement"]["anomalous"])
            self.assertEqual(payload["inputs"]["observation_labels"], ["IMEAN", "SIGIMEAN"])
            self.assertNotIn("group_anomalous", payload["refinement"]["strategies"])

    def test_failed_phenix_round_is_visible_and_not_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            result = execute_autorefine(
                run,
                make_refine(root, return_code=7),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.status, "AUTOREFINE_FAILED")
            records, current, _ = list_checkpoints(run)
            self.assertEqual(current, "postmr")
            self.assertFalse(records[-1].usable)
            self.assertEqual(records[-1].status, "FAILED")

    def test_failed_preflight_never_starts_real_refinement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            result = execute_autorefine(
                run,
                make_refine(root, preflight_return_code=9),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.status, "AUTOREFINE_FAILED")
            self.assertFalse((result.round_directory / "received_args.json").exists())
            self.assertIn("preflight failed", result.log_path.read_text().lower())

    def test_statistics_parser_keeps_cycle_history(self):
        stats = parse_refinement_statistics(
            "Start: r_work=0.40 r_free=0.44 bonds=0.01 angles=1.5\n"
            "cycle: r_work=0.35 r_free=0.39\n"
            "Final: r_work=0.28 r_free=0.31 bonds=0.009 angles=1.2\n"
            "clashscore: 5.1\n"
            "WARNING geometry needs inspection\n"
        )
        self.assertEqual(len(stats["cycle_series"]), 3)
        self.assertEqual(stats["r_free_minus_r_work"], 0.03)
        self.assertEqual(stats["bond_rmsd"], 0.009)
        self.assertEqual(stats["diagnostics"], ["WARNING geometry needs inspection"])

    def test_missing_free_r_is_rejected_without_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            dump = root / "phenix.mtz.dump"
            dump.write_text("#!/bin/sh\necho 'IMEAN 1 J'\necho 'SIGIMEAN 1 Q'\n")
            dump.chmod(dump.stat().st_mode | stat.S_IXUSR)
            with self.assertRaisesRegex(AutoRefineError, "Free-R"):
                execute_autorefine(
                    run,
                    make_refine(root),
                    dump,
                    environment={"PATH": "/usr/bin:/bin"},
                )


if __name__ == "__main__":
    unittest.main()
