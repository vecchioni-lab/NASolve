"""Campaign orchestration integration through the actual scientific engines.

External crystallographic programs use fixture executables. The worker is
called in-process to exercise its real locks, records, and integrity checks
without replacing Python process discovery with a fixture executable.
"""

import json
import shutil
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch

from nasolve.campaign_execution import execute_campaign, execution_status
from nasolve.campaign_records import read_record
from nasolve.campaign_worker import execute_job
from nasolve.campaigns import plan_campaign
from nasolve.config import AppConfig
from nasolve.coot_runtime import CootDiscoveryError
from nasolve.phenix_runtime import PhenixInstallation
from nasolve.postmr import prepare_postmr

from .helpers import make_dataset, make_mtz_dump, make_ready_set, pdb_record
from .test_autorefine import make_refine
from .test_autosol import cryst1, make_autosol
from .test_postmr import postmr_model_text


class CampaignPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "original"
        self.root.mkdir()
        self.tools = self.base / "tools"
        self.tools.mkdir()
        frames = self.base / "frames" / "5W6W"
        frames.mkdir(parents=True)
        (frames / "C_G.pdb").write_text(postmr_model_text("DC", "DG"))
        (frames / "seq_base.txt").write_text("C\n\nG\n")
        dataset = make_dataset(self.root / "dataset", include_model=False)
        (dataset / "nasolve.txt").write_text("[automr]\nframe = W\npair = C:G\n")
        self.plan = plan_campaign(self.root, frames_directory=frames.parent)
        self.plan_bytes = (self.root / "NASolveCampaign/plan.json").read_bytes()
        shutil.rmtree(frames.parent)

        dump = make_mtz_dump(self.tools)
        with dump.open("a") as handle:
            handle.write("printf '%s\\n' 'IMEAN 1 J' 'SIGIMEAN 1 Q' 'FreeR_flag 1 I' "
                         "'Resolution range: 20.0 5.27'\n")
        phaser = self.tools / "phenix.phaser"
        phaser.write_text("#!/bin/sh\ncp ../Model/input_model.pdb PHASER.1.pdb\n"
                          "printf mtz > PHASER.1.mtz\n"
                          "echo 'SOLU SET RFZ=9.1 TFZ=14.3 LLG=121'\n")
        phaser.chmod(0o755)
        installation = PhenixInstallation(
            self.tools, None, "2.2.1", {
                "phenix.phaser": phaser,
                "phenix.mtz.dump": dump,
                "phenix.ready_set": make_ready_set(self.tools),
                "phenix.refine": make_refine(self.tools),
            }, {"PATH": "/usr/bin:/bin"}, "fixture",
        )
        self.installation = installation

        def restraints_builder(model, pairs, output):
            output.write_text("geometry_restraints.edits {}\n")

        self.jobs = []

        def run_worker(job_path, **kwargs):
            self.jobs.append(read_record(job_path)["stage"])
            return execute_job(job_path)

        self.addCleanup(patch.stopall)
        patch("nasolve.campaign_execution.run_job", side_effect=run_worker).start()
        patch("nasolve.campaign_stages.load_config", return_value=AppConfig()).start()
        patch("nasolve.campaign_stages.discover_phenix", return_value=installation).start()
        patch("nasolve.campaign_stages.discover_coot", side_effect=CootDiscoveryError("not needed")).start()
        patch("nasolve.campaign_stages.prepare_postmr", side_effect=partial(
            prepare_postmr, narestraints_builder=restraints_builder,
        )).start()

    def test_completed_postmr_resumes_after_relocation_through_actual_worker_and_engines(self):
        result = execute_campaign(self.root, through="postmr")
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "PAUSED", item["diagnostic"])
        self.assertEqual(item["next_stage"], "autosol")
        self.assertEqual(self.jobs, ["preflight", "phaser", "postmr"])
        run_relative = item["run"]
        self.assertEqual(run_relative, "dataset/AutoMR/run_001")
        preserved = {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in (self.root / run_relative / "PostMR").rglob("*") if path.is_file()
        }

        original = self.root
        self.root = self.base / "relocated"
        shutil.copytree(original, self.root)
        shutil.rmtree(original)
        result = execute_campaign(self.root)
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "SOLVED", item["diagnostic"])
        self.assertEqual(item["run"], run_relative)
        self.assertEqual(item["checkpoint"], "refine-001")
        self.assertTrue(item["numerical_success"])
        self.assertTrue(item["inspection_required"])
        self.assertEqual(self.jobs, ["preflight", "phaser", "postmr", "autosol", "autorefine"])
        self.assertEqual((self.root / "NASolveCampaign/plan.json").read_bytes(), self.plan_bytes)
        for relative, content in preserved.items():
            self.assertEqual((self.root / relative).read_bytes(), content, relative)
        self.assertFalse((self.root / run_relative / "AutoSol").exists())
        self.assertFalse((self.root / "dataset/AutoMR/run_002").exists())
        refine_report = json.loads((self.root / run_relative / "AutoRefine/round_001/report.json").read_text())
        self.assertEqual(refine_report["parent_checkpoint"], "postmr")
        self.assertEqual(refine_report["inputs"]["observation_labels"], ["IMEAN", "SIGIMEAN"])
        self.assertTrue(refine_report["acceptance"]["visual_inspection_required"])
        self.assertEqual(execution_status(self.root)["execution"]["datasets"][0]["status"], "SOLVED")
        execute_campaign(self.root)
        self.assertEqual(len(self.jobs), 5, "Completed stages must not execute twice")

    def test_changed_readyset_dictionary_blocks_resume_before_refinement(self):
        result = execute_campaign(self.root, through="postmr")
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "PAUSED", item["diagnostic"])
        run = self.root / item["run"]
        (run / "PostMR/ReadySet/prepared_model.ligands.cif").write_text("data_changed\n")
        result = execute_campaign(self.root)
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "BLOCKED")
        self.assertIn("artifact changed", item["diagnostic"].lower())
        self.assertEqual(self.jobs, ["preflight", "phaser", "postmr"])
        self.assertFalse((run / "AutoRefine").exists())

    def test_anomalous_pipeline_preserves_original_observations_and_accepted_phases(self):
        self.root = self.base / "phased-original"
        self.root.mkdir()
        frames = self.base / "phased-frames" / "5W6W"
        frames.mkdir(parents=True)
        model = cryst1() + "".join([
            pdb_record("HETATM", 1, "P", "S6G", "A", 12),
            pdb_record("HETATM", 2, "C1'", "S6G", "A", 12, element="C"),
            pdb_record("HETATM", 3, "C3'", "S6G", "A", 12, element="C"),
            pdb_record("HETATM", 4, "S6", "S6G", "A", 12, element="S"),
            pdb_record("HETATM", 5, "P", "C38", "B", 4),
            pdb_record("HETATM", 6, "C1'", "C38", "B", 4, element="C"),
            pdb_record("HETATM", 7, "C3'", "C38", "B", 4, element="C"),
            pdb_record("HETATM", 8, "I", "C38", "B", 4, element="I", x=1, y=2, z=3),
            "END\n",
        ])
        (frames / "Q_iC.pdb").write_text(model)
        (frames / "seq_base.txt").write_text("G\n\nC\n")
        dataset = make_dataset(self.root / "dataset", include_model=False)
        (dataset / "nasolve.txt").write_text("[automr]\nframe = W\npair = Q:iC\n")
        with (dataset / "summary.html").open("a") as handle:
            handle.write("wavelength [A] = 1.377618\n")
        plan = plan_campaign(self.root, frames_directory=frames.parent)
        self.assertEqual(plan["datasets"][0]["status"], "DISCOVERED")
        self.assertTrue(plan["datasets"][0]["effective_config"]["exact_pair_model"])
        shutil.rmtree(frames.parent)
        observations = (dataset / "staraniso-alldata.mtz").read_bytes()
        self.installation.executables["phenix.autosol"] = make_autosol(self.tools, (1, 2, 3))
        dump = make_mtz_dump(self.tools)
        with dump.open("a") as handle:
            handle.write("printf '%s\\n' 'F(+) 1 G' 'SIGF(+) 1 L' 'F(-) 1 G' 'SIGF(-) 1 L' "
                         "'IMEAN 1 J' 'SIGIMEAN 1 Q' 'FreeR_flag 1 I' 'Resolution range: 20.0 5.27'\n"
                         "case \"$1\" in\n"
                         "  *overall_best*) printf '%s\\n' 'HLAM 1 A' 'HLBM 1 A' 'HLCM 1 A' 'HLDM 1 A';;\n"
                         "esac\n")
        with patch("nasolve.autosol.os.cpu_count", return_value=8):
            result = execute_campaign(self.root, through="autosol")
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "PAUSED", item["diagnostic"])
        self.assertEqual(item["next_stage"], "autorefine")
        run_relative = item["run"]
        run = self.root / run_relative
        phase_relative = Path(run_relative) / "AutoSol/AutoSol_run_1_/overall_best_refine_data.mtz"
        phase_bytes = (self.root / phase_relative).read_bytes()
        autosol_report = json.loads((run / "AutoSol/report.json").read_text())
        self.assertEqual(autosol_report["status"], "AUTOSOL_READY")
        self.assertTrue(autosol_report["use_for_refinement"])
        self.assertEqual(Path(autosol_report["input_model"]), run / "Phaser/mr_solution.pdb")

        original = self.root
        self.root = self.base / "phased-relocated"
        shutil.copytree(original, self.root)
        shutil.rmtree(original)
        result = execute_campaign(self.root)
        item = result["execution"]["datasets"][0]
        self.assertEqual(item["status"], "SOLVED", item["diagnostic"])
        self.assertTrue(item["inspection_required"])
        self.assertEqual(self.jobs, ["preflight", "phaser", "postmr", "autosol", "autorefine"])
        run = self.root / run_relative
        refined = json.loads((run / "AutoRefine/round_001/report.json").read_text())
        self.assertEqual(refined["parent_checkpoint"], "postmr")
        self.assertEqual(refined["inputs"]["observation_labels"], ["F(+)", "SIGF(+)", "F(-)", "SIGF(-)"])
        self.assertEqual(refined["inputs"]["free_r_label"], "FreeR_flag")
        self.assertEqual(refined["inputs"]["phase_labels"], ["HLAM", "HLBM", "HLCM", "HLDM"])
        self.assertEqual(Path(refined["inputs"]["phase_file"]), self.root / phase_relative)
        self.assertTrue(refined["refinement"]["anomalous"])
        self.assertTrue(refined["refinement"]["use_experimental_phases"])
        self.assertEqual((self.root / phase_relative).read_bytes(), phase_bytes)
        self.assertEqual((self.root / "dataset/staraniso-alldata.mtz").read_bytes(), observations)
        arguments = json.loads((run / "AutoRefine/round_001/received_args.json").read_text())
        self.assertIn("xray_data.r_free_flags.generate=False", arguments)
        self.assertEqual(execution_status(self.root)["execution"]["datasets"][0]["status"], "SOLVED")
