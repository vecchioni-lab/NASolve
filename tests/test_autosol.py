import json
import math
import stat
import tempfile
import unittest
from pathlib import Path

from nasolve.autosol import (
    AutoSolPreparationError,
    execute_autosol,
    nearest_symmetry_distance,
    read_wavelength,
)

from .helpers import pdb_record


def cryst1(
    a: float = 50.0,
    b: float = 50.0,
    c: float = 60.0,
    alpha: float = 90.0,
    beta: float = 90.0,
    gamma: float = 120.0,
    space_group: str = "R 3",
) -> str:
    return (
        f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}"
        f"{alpha:7.2f}{beta:7.2f}{gamma:7.2f} {space_group:<11s}   9\n"
    )


def hex_cart(x: float, y: float, z: float) -> tuple[float, float, float]:
    return (50.0 * x - 25.0 * y, 50.0 * math.sin(math.radians(120.0)) * y, 60.0 * z)


def make_mtz_dump(root: Path) -> Path:
    executable = root / "phenix.mtz.dump"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' 'I(+) 1 K' 'SIGI(+) 1 M' 'I(-) 1 K' 'SIGI(-) 1 M'\n"
        "case \"$1\" in\n"
        "  *overall_best_refine_data.mtz) "
        "printf '%s\\n' 'HLAM 1 A' 'HLBM 1 A' 'HLCM 1 A' 'HLDM 1 A';;\n"
        "esac\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def make_autosol(
    root: Path,
    site_xyz: tuple[float, float, float],
    return_code: int = 0,
) -> Path:
    executable = root / "phenix.autosol"
    ha_record = pdb_record(
        "HETATM",
        1,
        "I",
        "I",
        "A",
        1,
        occupancy=0.93,
        element="I",
        x=site_xyz[0],
        y=site_xyz[1],
        z=site_xyz[2],
    ).rstrip("\n")
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "root = Path.cwd() / 'AutoSol_run_1_'\n"
        "root.mkdir()\n"
        "(Path.cwd() / 'received_args.json').write_text(__import__('json').dumps(sys.argv[1:]))\n"
        f"return_code = {return_code}\n"
        "if return_code:\n"
        "    print('AutoSol diagnostic failure')\n"
        "    raise SystemExit(return_code)\n"
        "(root / 'autosol.eff').write_text('sites = None\\nbuild = False\\n"
        "phase_improve_and_build = False\\nnproc = 8\\n')\n"
        f"(root / 'overall_best_ha_pdb.pdb').write_text({ha_record!r} + '\\nEND\\n')\n"
        "(root / 'overall_best_refine_data.mtz').write_bytes(b'mtz')\n"
        "print('AutoSol complete')\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def make_run(root: Path, model_xyz: tuple[float, float, float]) -> Path:
    dataset = root / "dataset"
    frame = root / "MR_frames" / "5W6W"
    run = dataset / "AutoMR" / "run_001"
    phaser = run / "Phaser"
    postmr_model_dir = run / "PostMR" / "Model"
    frame.mkdir(parents=True)
    phaser.mkdir(parents=True)
    postmr_model_dir.mkdir(parents=True)
    input_mtz = dataset / "staraniso_alldata-unique.mtz"
    input_mtz.write_bytes(b"mtz")
    summary = dataset / "summary.html"
    summary.write_text(
        "wavelength [A] = 1.377618\nWavelength               1.37762 A\n"
    )
    frame_model = frame / "C_G.pdb"
    frame_model.write_text("END\n")
    (frame / "seq_base.txt").write_text("GAGC\n\nCTGC\n")
    phaser_model = phaser / "mr_solution.pdb"
    phaser_model.write_text(cryst1() + "END\n")
    prepared_model = postmr_model_dir / "readyset_model.pdb"
    prepared_model.write_text(
        cryst1()
        + pdb_record(
            "HETATM", 1, "I", "C38", "B", 4, element="I",
            x=model_xyz[0], y=model_xyz[1], z=model_xyz[2],
        )
        + "END\n"
    )
    report = {
        "workflow": "automr",
        "stage": "postmr",
        "status": "POSTMR_READY",
        "inputs": {
            "reflections": str(input_mtz.resolve()),
            "summary": str(summary.resolve()),
            "model": str(frame_model.resolve()),
        },
        "post_mr_plan": {"sequences": {}},
        "execution": {
            "phaser": {"solution_pdb": str(phaser_model.resolve())},
        },
        "postmr": {
            "prepared_model": str(prepared_model.resolve()),
            "anomalous": {
                "autosol_required": True,
                "trigger_elements": ["BR", "I", "SE"],
                "candidates": [{
                    "site": "B:4",
                    "residue": "C38",
                    "atom_name": "I",
                    "alternate": None,
                    "element": "I",
                    "coordinates": list(model_xyz),
                }],
            },
        },
    }
    (run / "report.json").write_text(json.dumps(report))
    return run


class AutoSolTests(unittest.TestCase):
    def test_wavelength_prefers_precise_assignment(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.html"
            summary.write_text(
                "wavelength [A] = 1.377618\nWavelength 1.37762 A\n"
            )
            value, source = read_wavelength(summary)
            self.assertEqual(value, 1.377618)
            self.assertIn("high-precision", source)

    def test_conflicting_wavelengths_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.html"
            summary.write_text("wavelength [A] = 1.377618\nWavelength 0.91990 A\n")
            with self.assertRaisesRegex(AutoSolPreparationError, "Conflicting"):
                read_wavelength(summary)

    def test_r3_symmetry_match_finds_third_operator(self):
        model = hex_cart(0.2, 0.1, 0.3)
        transformed = hex_cart(-0.1, -0.2, 0.3)
        site = (transformed[0] + 1.0, transformed[1], transformed[2])
        result = nearest_symmetry_distance(
            model, site, (50.0, 50.0, 60.0, 90.0, 90.0, 120.0), "R 3"
        )
        self.assertAlmostEqual(result["distance"], 1.0, places=6)
        self.assertEqual(result["operator"], "-x+y,-x,z")

    def test_execute_is_mr_guided_never_builds_and_validates_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = hex_cart(0.2, 0.1, 0.3)
            transformed = hex_cart(-0.1, -0.2, 0.3)
            site = (transformed[0] + 1.0, transformed[1], transformed[2])
            run = make_run(root, model)
            result = execute_autosol(
                run,
                make_autosol(root, site),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
            )
            self.assertEqual(result.status, "AUTOSOL_READY")
            self.assertEqual(result.matched_distance, 1.0)
            args = json.loads((result.autosol_directory / "received_args.json").read_text())
            self.assertIn("build=False", args)
            self.assertIn("phase_improve_and_build=False", args)
            self.assertIn("nproc=8", args)
            self.assertFalse(any(argument.startswith("sites=") for argument in args))
            model_argument = next(arg for arg in args if arg.startswith("input_partpdb_file="))
            self.assertTrue(model_argument.endswith("/Phaser/mr_solution.pdb"))
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["stage"], "autosol")
            self.assertFalse(report["autosol"]["effective_parameters"]["build"])
            self.assertEqual(
                report["autosol"]["site_validation"]["accepted"][0]
                ["nearest_site"]["operator"],
                "-x+y,-x,z",
            )

    def test_distant_ha_sites_stop_before_report_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = hex_cart(0.2, 0.1, 0.3)
            run = make_run(root, model)
            result = execute_autosol(
                run,
                make_autosol(root, (13.0, 14.0, 15.0)),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
            )
            self.assertEqual(result.status, "AUTOSOL_WARNING")
            report = json.loads((run / "report.json").read_text())
            self.assertFalse(report["autosol"]["use_for_refinement"])
            self.assertIn("continue without AutoSol phases", report["autosol"]["continuation"])

    def test_intermediate_distance_requests_review_but_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = hex_cart(0.2, 0.1, 0.3)
            transformed = hex_cart(-0.1, -0.2, 0.3)
            site = (transformed[0] + 6.0, transformed[1], transformed[2])
            run = make_run(root, model)
            result = execute_autosol(
                run,
                make_autosol(root, site),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
            )
            self.assertEqual(result.status, "AUTOSOL_REVIEW")
            self.assertAlmostEqual(result.matched_distance, 6.0)
            report = json.loads((run / "report.json").read_text())
            self.assertFalse(report["autosol"]["use_for_refinement"])
            self.assertEqual(
                len(report["autosol"]["site_validation"]["review_candidates"]), 1
            )

    def test_autosol_program_failure_warns_and_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = hex_cart(0.2, 0.1, 0.3)
            run = make_run(root, model)
            result = execute_autosol(
                run,
                make_autosol(root, (0.0, 0.0, 0.0), return_code=5),
                make_mtz_dump(root),
                environment={"PATH": "/usr/bin:/bin"},
                processor_count=8,
            )
            self.assertEqual(result.status, "AUTOSOL_WARNING")
            self.assertIsNone(result.refinement_data)
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["autosol"]["status"], "AUTOSOL_WARNING")
            self.assertIn("status 5", report["autosol"]["failure_reason"])


if __name__ == "__main__":
    unittest.main()
