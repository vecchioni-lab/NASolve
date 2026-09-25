import json
import shutil
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch

from nasolve.automr_input import AutoMRInputError
from nasolve.campaign_stages import CampaignStageError, execute_stage
from nasolve.campaigns import CampaignError, campaign_status, plan_campaign
from nasolve.config import AppConfig
from nasolve.phenix_runtime import PhenixInstallation
from nasolve.phaser import PhaserExecutionError
from nasolve.postmr import prepare_postmr
from nasolve.coot_runtime import CootDiscoveryError
from nasolve.presets import load_preset

from .helpers import make_dataset, make_mtz_dump, make_phaser, w_model_text as model_text, make_postmr_report, make_ready_set
from .test_autorefine import make_refine, make_refine_run, make_mtz_dump as refine_dump
from .test_autosol import make_autosol, make_run as make_autosol_run, make_mtz_dump as autosol_dump
from .test_postmr import make_data_root, postmr_model_text
from .test_sequence_family_integration import model_text as sequence_family_model_text


REFERENCE = Path(__file__).parents[1] / "src/nasolve/data/sequence_references/w-metal-scaffold.json"


class CampaignStageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "campaign"
        self.root.mkdir()
        self.tools = self.base / "tools"
        self.tools.mkdir()
        self.frames = self.base / "frames" / "5W6W"
        self.frames.mkdir(parents=True)
        (self.frames / "C_G.pdb").write_text(model_text())
        (self.frames / "seq_base.txt").write_text("AC\n")
        self.phenix = PhenixInstallation(
            self.tools, None, "2.2.1", {"phenix.mtz.dump": make_mtz_dump(self.tools)},
            {"PATH": "/usr/bin:/bin"}, "fixture",
        )
        self.addCleanup(patch.stopall)
        patch("nasolve.campaign_stages.load_config", return_value=AppConfig()).start()
        patch("nasolve.campaign_stages.discover_phenix", return_value=self.phenix).start()
        patch("nasolve.autosol.os.cpu_count", return_value=8).start()
        # Stage workers may read configuration but never replace active workspace.
        patch("nasolve.config.save_config", side_effect=AssertionError("No config writes")).start()

    def plan(self, pair="D:T", *, config=True):
        dataset = make_dataset(self.root / "dataset", include_model=False)
        if config:
            (dataset / "nasolve.txt").write_text(f"[automr]\npair = {pair}\n")
            plan = plan_campaign(self.root, frames_directory=self.frames.parent)
        else:
            preset = self.base / "preset.toml"
            preset.write_text('schema_version = 1\nid = "test"\nversion = "1"\n'
                              f'[automr]\npair = "{pair}"\n')
            plan = plan_campaign(self.root, preset=preset, frames_directory=self.frames.parent)
        self.dataset = plan["datasets"][0]
        self.policy = plan["preset"]["policy"]
        return plan

    def attempt(self, name):
        attempt = self.root / "NASolveCampaign" / "jobs" / name
        attempt.mkdir(parents=True)
        return attempt

    def stage(self, stage, run=None, **kwargs):
        return execute_stage(self.root, self.dataset, self.policy, stage,
                             self.attempt(stage), run, **kwargs)

    def set_run(self, run, *, anomalous=True):
        self.dataset = {"id": "dataset", "relative_path": "dataset"}
        self.policy = {"postmr": {"modified_pairs_only": False},
                       "autosol": {"policy": "when-anomalous", "on_unaccepted": "inspect"},
                       "autorefine": {"recipe": "AutoRefine/default", "cycles": 5}}
        report = json.loads((run / "report.json").read_text())
        report["postmr"]["status"] = "POSTMR_READY"
        report["postmr"]["anomalous"]["autosol_required"] = anomalous
        if not anomalous:
            report["postmr"]["anomalous"]["candidates"] = []
        (run / "report.json").write_text(json.dumps(report))

    def test_op3_explicit_dataset_request_survives_campaign_freezing(self):
        dataset = make_dataset(self.root / "dataset", include_model=False)
        (dataset / "nasolve.txt").write_text("[automr]\npair = C:G\nallow_op3_sites = A:1\n")
        plan = plan_campaign(self.root, frames_directory=self.frames.parent)
        self.dataset = plan["datasets"][0]
        self.policy = plan["preset"]["policy"]
        self.assertEqual(self.dataset["effective_config"]["allow_op3_sites"], ["A:1"])
        result = self.stage("preflight")
        report = json.loads((self.root / result["run"] / "report.json").read_text())
        self.assertEqual(report["post_mr_plan"]["allow_op3_sites"], ["A:1"])
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_sequence_reference_preflight_uses_frozen_campaign_copy(self):
        dataset = make_dataset(self.root / "dataset", include_model=False)
        # This test exercises the sequence-family correspondence gate, so its
        # search scaffold must contain the complete reviewed 42-site W inventory.
        (self.frames / "C_G.pdb").write_text(sequence_family_model_text())
        custom = dataset / "family.json"
        shutil.copyfile(REFERENCE, custom)
        (dataset / "nasolve.txt").write_text(
            "[automr]\npair = C:G\nsequence_reference = family.json\n"
        )
        plan = plan_campaign(self.root, frames_directory=self.frames.parent)
        self.dataset = plan["datasets"][0]
        self.policy = plan["preset"]["policy"]
        frozen = self.dataset["inputs"]["sequence_reference"]
        self.assertEqual(
            (self.root / frozen["relative_path"]).read_bytes(),
            REFERENCE.read_bytes(),
        )

        # The campaign resource is authoritative after planning; execution must
        # not reopen the dataset-relative source or the installed reference.
        custom.unlink()
        result = self.stage("preflight")
        run = self.root / result["run"]
        report = json.loads((run / "report.json").read_text())

        self.assertEqual(result["status"], "READY_POST_MR_MUTATION")
        self.assertEqual(report["sequence_family_preflight"]["target_count"], 42)
        self.assertEqual(
            (run / "Model/sequence_reference.json").read_bytes(),
            REFERENCE.read_bytes(),
        )
        self.assertIn(
            "sequence_reference = family.json",
            (run / "nasolve.input.txt").read_text(),
        )
        self.assertTrue(
            any(path.endswith("/frozen/sequence_reference.json") for path in result["artifacts"])
        )
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_sequence_thread_overlays_reach_frozen_family_target(self):
        dataset = make_dataset(self.root / "dataset", include_model=False)
        (self.frames / "C_G.pdb").write_text(sequence_family_model_text())
        (dataset / "nasolve.txt").write_text("[automr]\npair = C:G\n")
        (self.root / "nasolve-campaign.toml").write_text(
            'schema_version = 1\n\n'
            '[sequence_threads.w-family]\n'
            'datasets = ["dataset"]\n'
            'sequence_reference = "w-metal-scaffold"\n\n'
            '[sequence_threads.w-family.sequences]\n'
            'B = "CCCCCCC"\n\n'
            '[sequence_threads.w-family.site_codes]\n'
            '"A:13" = "1AP"\n'
        )
        plan = plan_campaign(self.root, frames_directory=self.frames.parent)
        self.dataset = plan["datasets"][0]
        self.policy = plan["preset"]["policy"]
        self.assertEqual(
            self.dataset["effective_config"]["sequence_reference_source"], "thread"
        )

        result = self.stage("preflight")
        run = self.root / result["run"]
        report = json.loads((run / "report.json").read_text())
        target = json.loads((run / "Model/sequence_family_target.json").read_text())
        rows = {row["site"]: row for row in target["sites"]}

        self.assertEqual(report["post_mr_plan"]["sequence_thread"], {
            "id": "w-family",
            "sequences": {"B": "CCCCCCC"},
            "site_codes": {"A:13": "1AP"},
        })
        self.assertEqual(rows["B:3"]["residue_code"], "DC")
        self.assertEqual(rows["B:3"]["source"], "thread_sequence")
        self.assertEqual(rows["A:13"]["residue_code"], "1AP")
        self.assertEqual(rows["A:13"]["source"], "thread_site_chemistry")
        self.assertEqual(rows["B:4"]["residue_code"], "DG")
        self.assertEqual(rows["B:4"]["source"], "dataset_site_chemistry")
        overlays = report["post_mr_plan"]["sequence_family"]["overlays"]
        self.assertEqual(overlays["thread_sequences"], {"B": "CCCCCCC"})
        self.assertEqual(overlays["thread_site_codes"], {"A:13": "1AP"})
        self.assertEqual(report["sequence_family_preflight"]["target_count"], 42)

    def test_preflight_uses_frozen_catalogue_and_does_not_generate_dataset_config(self):
        self.plan(config=False)
        shutil.rmtree(self.frames.parent)
        allocated = []

        def record_allocation(run):
            self.assertTrue(run.is_dir())
            self.assertFalse((run / "Model").exists())
            allocated.append(run)

        with patch("nasolve.automr.resolve_automr_input", side_effect=AssertionError("No rediscovery")):
            result = self.stage("preflight", on_run_allocated=record_allocation)
        self.assertEqual(result["status"], "READY_POST_MR_MUTATION")
        run = self.root / result["run"]
        self.assertEqual(allocated, [run])
        self.assertFalse((self.root / "dataset" / "nasolve.txt").exists())
        report = json.loads((run / "report.json").read_text())
        self.assertFalse(report["configuration"]["generated"])
        self.assertEqual(report["post_mr_plan"]["standard_pair"]["ligand_codes"], ["1AP", "DT"])
        self.assertFalse(report["post_mr_plan"]["standard_pair"]["exact_model_match"])
        self.assertEqual((run / "Model" / "seq_base.txt").read_text(), "AC\n")
        self.assertEqual((run / "Model" / "input_model.pdb").read_text(), model_text())
        self.assertEqual(result["tool_versions"], {"phenix": "2.2.1"})
        self.assertIn(result["run_report_snapshot"], result["artifacts"])
        self.assertNotIn(str(run / "report.json"), result["artifacts"])
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_exact_pair_selection_and_original_model_name_survive_relocation(self):
        (self.frames / "D_T.pdb").write_text(model_text() + "REMARK frozen exact\n")
        self.plan()
        old = self.root
        self.root = self.base / "relocated"
        shutil.copytree(old, self.root)
        shutil.rmtree(old)
        shutil.rmtree(self.frames.parent)
        result = self.stage("preflight")
        report = json.loads((self.root / result["run"] / "report.json").read_text())
        self.assertEqual(result["status"], "READY")
        self.assertTrue(report["post_mr_plan"]["standard_pair"]["exact_model_match"])
        self.assertTrue(report["inputs"]["model"].endswith("D_T.pdb"))
        self.assertIn("REMARK frozen exact", (self.root / result["run"] / "Model/input_model.pdb").read_text())
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_damaged_frozen_model_stops_before_run_allocation(self):
        self.plan()
        (self.root / self.dataset["inputs"]["model"]["relative_path"]).write_bytes(b"wrong")
        with self.assertRaisesRegex(CampaignStageError, "checksum"):
            self.stage("preflight")
        self.assertFalse((self.root / "dataset" / "AutoMR").exists())

    def test_preflight_rejects_linked_run_parent_before_allocating_outside_campaign(self):
        self.plan()
        outside = self.base / "unrelated-runs"
        outside.mkdir()
        (self.root / "dataset" / "AutoMR").symlink_to(outside, target_is_directory=True)
        allocated = []
        with self.assertRaisesRegex(CampaignError, "symbolic link"):
            self.stage("preflight", on_run_allocated=allocated.append)
        self.assertEqual(allocated, [])
        self.assertEqual(list(outside.iterdir()), [])

    def test_symmetry_gate_still_runs_and_stops_before_allocation(self):
        self.plan()
        self.phenix.executables["phenix.mtz.dump"] = make_mtz_dump(self.tools, "P 21 21 21")
        with self.assertRaisesRegex(AutoMRInputError, "space|symmetry|disagree"):
            self.stage("preflight")
        self.assertFalse((self.root / "dataset" / "AutoMR").exists())

    def test_allocation_callback_failure_leaves_identified_run_and_no_outputs(self):
        self.plan()
        allocated = []

        def interrupted(run):
            allocated.append(run)
            raise RuntimeError("journal interruption")

        with self.assertRaisesRegex(RuntimeError, "journal interruption"):
            self.stage("preflight", on_run_allocated=interrupted)
        self.assertEqual(len(allocated), 1)
        self.assertEqual(list(allocated[0].iterdir()), [])

    def test_phaser_receipts_immutable_snapshot_and_preserves_scientific_review(self):
        self.plan()
        preflight = self.stage("preflight")
        old_snapshot = (self.root / preflight["run_report_snapshot"]).read_bytes()
        self.phenix.executables["phenix.phaser"] = make_phaser(self.tools, tfz=7.5)
        run = self.root / preflight["run"]
        result = self.stage("phaser", run)
        self.assertEqual(result["status"], "MR_REVIEW")
        self.assertEqual(result["tfz"], 7.5)
        self.assertIn("dataset/AutoMR/run_001/Phaser/mr_solution.mtz", result["artifacts"])
        self.assertEqual((self.root / preflight["run_report_snapshot"]).read_bytes(), old_snapshot)
        with patch("nasolve.campaign_stages.prepare_postmr") as postmr:
            with self.assertRaisesRegex(CampaignStageError, "MR_SUCCESS"):
                self.stage("postmr", run)
            postmr.assert_not_called()

    def test_phaser_refuses_to_overwrite_an_existing_stage(self):
        self.plan()
        preflight = self.stage("preflight")
        self.phenix.executables["phenix.phaser"] = make_phaser(self.tools)
        run = self.root / preflight["run"]
        self.stage("phaser", run)
        with self.assertRaises(PhaserExecutionError):
            execute_stage(self.root, self.dataset, self.policy, "phaser",
                          self.attempt("phaser-again"), run)

    def test_autosol_skip_needs_explicit_consistent_eligibility_and_no_runtime(self):
        run = make_autosol_run(self.root, (1, 2, 3))
        self.set_run(run, anomalous=False)
        with patch("nasolve.campaign_stages.discover_phenix", side_effect=AssertionError("No Phenix needed")):
            result = self.stage("autosol", run)
        self.assertEqual(result["status"], "SKIPPED")
        self.assertIn(result["run_report_snapshot"], result["artifacts"])
        self.assertEqual((self.root / result["run_report_snapshot"]).read_bytes(),
                         (run / "report.json").read_bytes())
        self.assertFalse((run / "AutoSol").exists())
        report = json.loads((run / "report.json").read_text())
        report["postmr"]["anomalous"]["autosol_required"] = True
        (run / "report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(CampaignStageError, "eligibility"):
            execute_stage(self.root, self.dataset, self.policy, "autosol",
                          self.attempt("bad-eligibility"), run)

    def test_postmr_keeps_existing_curated_dictionary_and_readyset_outputs_in_receipt(self):
        source = self.base / "source.pdb"
        source.write_text(postmr_model_text())
        run = self.root / "dataset" / "AutoMR" / "run_001"
        make_postmr_report(run, source)
        self.dataset = {"id": "dataset", "relative_path": "dataset"}
        self.policy = load_preset().to_dict()
        self.phenix.executables["phenix.ready_set"] = make_ready_set(self.tools)

        def builder(model, pairs, output):
            output.write_text("geometry_restraints.edits {}\n")

        stage_engine = partial(prepare_postmr, data_root=make_data_root(self.base),
                               narestraints_builder=builder)
        with patch("nasolve.campaign_stages.prepare_postmr", side_effect=stage_engine), \
                patch("nasolve.campaign_stages.discover_coot", side_effect=CootDiscoveryError("unused")):
            result = self.stage("postmr", run)
        self.assertEqual(result["status"], "POSTMR_READY")
        for suffix in ("Model/readyset_model.pdb", "Restraints/DE.cif",
                       "Restraints/curated_ligands.cif", "ReadySet/prepared_model.ligands.cif"):
            self.assertTrue(any(path.endswith(suffix) for path in result["artifacts"]), suffix)

    def test_autosol_review_cannot_silently_drop_phases_and_refine(self):
        run = make_autosol_run(self.root, (1, 2, 3))
        self.set_run(run)
        self.phenix.executables.update({"phenix.autosol": make_autosol(self.tools, (6, 2, 3)),
                                      "phenix.mtz.dump": autosol_dump(self.tools)})
        result = self.stage("autosol", run)
        self.assertEqual(result["status"], "AUTOSOL_REVIEW", result["message"])
        self.assertIsNotNone(result["matched_distance"])
        with patch("nasolve.campaign_stages.execute_autorefine") as refine:
            with self.assertRaisesRegex(CampaignStageError, "AUTOSOL_READY"):
                self.stage("autorefine", run)
            refine.assert_not_called()

    def test_accepted_autosol_receipts_phase_and_heavy_atom_files(self):
        run = make_autosol_run(self.root, (1, 2, 3))
        self.set_run(run)
        self.phenix.executables.update({"phenix.autosol": make_autosol(self.tools, (1, 2, 3)),
                                      "phenix.mtz.dump": autosol_dump(self.tools)})
        result = self.stage("autosol", run)
        self.assertEqual(result["status"], "AUTOSOL_READY", result["message"])
        for name in ("overall_best_ha_pdb.pdb", "overall_best_refine_data.mtz"):
            self.assertTrue(any(path.endswith(name) for path in result["artifacts"]))

    def test_autosol_preflight_warning_without_console_log_retains_inspection_reason(self):
        from nasolve.autosol import AutoSolPreparationError
        run = make_autosol_run(self.root, (1, 2, 3))
        self.set_run(run)
        self.phenix.executables.update({"phenix.autosol": make_autosol(self.tools, (1, 2, 3)),
                                      "phenix.mtz.dump": autosol_dump(self.tools)})
        with patch("nasolve.autosol.read_wavelength", side_effect=AutoSolPreparationError("Missing wavelength")):
            result = self.stage("autosol", run)
        self.assertEqual(result["status"], "AUTOSOL_WARNING")
        self.assertIn("Missing wavelength", result["message"])
        self.assertIn("inspection", result["message"])
        self.assertFalse((run / "AutoSol/autosol.console.log").exists())
        self.assertTrue(result["run_report_snapshot"])

    def test_refinement_uses_postmr_parent_and_preserves_review_checkpoint(self):
        run = make_refine_run(self.root)
        self.set_run(run)
        self.phenix.executables.update({"phenix.refine": make_refine(self.tools, final_work=0.24, final_free=0.22),
                                      "phenix.mtz.dump": refine_dump(self.tools)})
        result = self.stage("autorefine", run)
        self.assertEqual(result["status"], "AUTOREFINE_REVIEW")
        self.assertEqual(result["checkpoint"], "refine-001")
        self.assertFalse(result["selected_as_current"])
        registry = json.loads((run / "AutoRefine/checkpoints.json").read_text())
        self.assertEqual(registry["current"], "postmr")
        self.assertTrue(any(path.endswith("checkpoints.json") for path in result["artifacts"]))

    def test_mean_refinement_returns_numerical_success_without_visual_approval(self):
        run = make_refine_run(self.root, autosol=False)
        self.set_run(run, anomalous=False)
        self.phenix.executables.update({"phenix.refine": make_refine(self.tools),
                                      "phenix.mtz.dump": refine_dump(self.tools, anomalous=False)})
        result = self.stage("autorefine", run)
        self.assertEqual(result["status"], "AUTOREFINE_READY")
        self.assertTrue(result["selected_as_current"])
        report = json.loads((run / "AutoRefine/round_001/report.json").read_text())
        self.assertEqual(report["parent_checkpoint"], "postmr")
        self.assertTrue(report["acceptance"]["visual_inspection_required"])

    def test_foreign_refinement_and_run_paths_are_not_adopted(self):
        run = make_refine_run(self.root, autosol=False)
        self.set_run(run, anomalous=False)
        (run / "AutoRefine").mkdir()
        with self.assertRaisesRegex(CampaignStageError, "existing AutoRefine"):
            self.stage("autorefine", run)
        with self.assertRaises(CampaignError):
            execute_stage(self.root, self.dataset, self.policy, "postmr",
                          self.attempt("foreign"), self.base / "foreign" / "run_001")

    def test_ready_autosol_without_explicit_phase_acceptance_is_an_inspection_stop(self):
        run = make_refine_run(self.root)
        self.set_run(run)
        report = json.loads((run / "report.json").read_text())
        report["autosol"]["use_for_refinement"] = False
        (run / "report.json").write_text(json.dumps(report))
        with patch("nasolve.campaign_stages.execute_autorefine") as refine:
            with self.assertRaisesRegex(CampaignStageError, "AUTOSOL_READY"):
                self.stage("autorefine", run)
            refine.assert_not_called()
