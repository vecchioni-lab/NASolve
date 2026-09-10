import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.campaign_execution import execute_campaign, execution_status, request_pause, retry_dataset
from nasolve.campaign_records import EXECUTION, STAGES, job_relative, read_record, write_record
from nasolve.campaign_worker import execute_job
from nasolve.campaign_process import CampaignProcessError, run_job as real_run_job
from nasolve.campaigns import CampaignError, plan_campaign

from .helpers import make_dataset, model_text


class CampaignExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "campaign"
        self.root.mkdir()
        frames = self.base / "frames" / "5W6W"
        frames.mkdir(parents=True)
        (frames / "C_G.pdb").write_text(model_text())
        for name in ("A", "B"):
            dataset = make_dataset(self.root / name)
            (dataset / "nasolve.txt").write_text("[automr]\nmode=standard\nframe=W\npair=C:G\n")
        self.plan = plan_campaign(self.root, frames_directory=frames.parent)
        self.calls = []
        self.outcomes = {}
        self.after_stage = None
        self.identity = {"pid": 99999999, "pgid": 99999999, "host": "fixture"}
        self.addCleanup(patch.stopall)
        patch("nasolve.campaign_worker.execute_stage", side_effect=self.stage).start()
        patch("nasolve.campaign_worker.current_process_identity", return_value=self.identity).start()
        patch("nasolve.campaign_execution.run_job", side_effect=self.run_job).start()

    def stage(self, root, dataset, policy, stage, attempt, run, **kwargs):
        self.calls.append((dataset["id"], stage))
        if stage == "preflight":
            automr = root / dataset["id"] / "AutoMR"
            automr.mkdir(exist_ok=True)
            number = 1
            while (automr / f"run_{number:03d}").exists():
                number += 1
            run = automr / f"run_{number:03d}"
            run.mkdir()
            kwargs["on_run_allocated"](run)
        stagefile = run / f"{stage}.dat"
        stagefile.write_text(stage + dataset["id"])
        status = self.outcomes.get((dataset["id"], stage), {
            "preflight": "READY", "phaser": "MR_SUCCESS", "postmr": "POSTMR_READY",
            "autosol": "SKIPPED", "autorefine": "AUTOREFINE_READY",
        }[stage])
        report = run / "report.json"
        report.write_text(json.dumps({"stage": stage, "status": status}))
        snapshot = attempt / "run-report.json"
        snapshot.write_bytes(report.read_bytes())
        result = {"status": status, "message": status, "run": run.relative_to(root).as_posix(),
                  "artifacts": [p.relative_to(root).as_posix() for p in (stagefile, snapshot)],
                  "run_report_snapshot": snapshot.relative_to(root).as_posix()}
        if stage == "autorefine":
            result.update(checkpoint="refine-001", selected_as_current=status == "AUTOREFINE_READY")
        if self.after_stage is not None:
            self.after_stage(dataset["id"], stage)
        return result

    def run_job(self, job, *, on_process, on_heartbeat):
        on_process(self.identity)
        return execute_job(job)

    def items(self, result):
        return {item["id"]: item for item in result["execution"]["datasets"]}

    def directory(self, dataset, stage, attempt=1):
        return self.root / job_relative(dataset, attempt, stage)

    def test_read_only_status_does_not_create_execution(self):
        self.assertIsNone(execution_status(self.root)["execution"])
        self.assertFalse((self.root / EXECUTION).exists())

    def test_sequential_execution_freezes_receipts_and_preserves_plan_workspace_and_existing_run(self):
        old = self.root / "A" / "AutoMR" / "run_007"
        old.mkdir(parents=True)
        (old / "keep").write_bytes(b"previous standalone result")
        planbytes = (self.root / "NASolveCampaign" / "plan.json").read_bytes()
        result = execute_campaign(self.root)
        self.assertEqual(result["execution"]["state"], "COMPLETE")
        self.assertEqual(self.calls, [(name, stage) for name in ("A", "B") for stage in STAGES])
        for item in self.items(result).values():
            self.assertEqual(item["status"], "SOLVED")
            self.assertTrue(item["inspection_required"])
            self.assertTrue(item["numerical_success"])
            self.assertEqual(item["checkpoint"], "refine-001")
        self.assertEqual((old / "keep").read_bytes(), b"previous standalone result")
        self.assertEqual((self.root / "NASolveCampaign" / "plan.json").read_bytes(), planbytes)
        receipt = read_record(self.directory("A", "postmr") / "result.json")
        self.assertEqual(receipt["plan_fingerprint"], self.plan["fingerprint"])
        self.assertTrue(all(ref["sha256"] for ref in receipt["artifacts"]))
        self.calls.clear()
        execute_campaign(self.root)
        self.assertEqual(self.calls, [])

    def test_boundary_stop_resumes_after_relocation_without_original(self):
        result = execute_campaign(self.root, datasets=("A",), through="postmr")
        self.assertEqual(self.items(result)["A"]["next_stage"], "autosol")
        self.assertEqual(self.items(result)["B"]["status"], "DISCOVERED")
        self.calls.clear()
        relocated = self.base / "relocated"
        shutil.copytree(self.root, relocated)
        shutil.rmtree(self.root)
        self.root = relocated
        shutil.rmtree(self.base / "frames")
        result = execute_campaign(self.root, datasets=("A",))
        self.assertEqual(self.calls, [("A", "autosol"), ("A", "autorefine")])
        self.assertEqual(self.items(result)["A"]["status"], "SOLVED")

    def test_recovered_receipt_is_portable_after_original_host_disappears(self):
        execute_campaign(self.root, datasets=("A",), through="postmr")
        finished = self.directory("A", "postmr") / "process-finished.json"
        finished.unlink()
        with patch("nasolve.campaign_execution.process_alive", return_value=False):
            execute_campaign(self.root, datasets=("A",))
        self.assertIn("recovered_from_receipt", read_record(finished))
        with patch("nasolve.campaign_execution.process_alive", return_value=None):
            result = execution_status(self.root)
        self.assertEqual(self.items(result)["A"]["status"], "SOLVED")

    def test_each_scientific_review_stops_only_its_dataset(self):
        for stage, outcome in (("phaser", "MR_REVIEW"), ("autosol", "AUTOSOL_REVIEW"),
                               ("autosol", "AUTOSOL_WARNING"), ("autorefine", "AUTOREFINE_REVIEW")):
            with self.subTest(stage=stage, outcome=outcome):
                self.outcomes[("A", stage)] = outcome
                result = execute_campaign(self.root)
                self.assertEqual(self.items(result)["A"]["status"], "AWAITING_INSPECTION")
                self.assertEqual(self.items(result)["B"]["status"], "SOLVED")
                count = len(self.calls)
                execute_campaign(self.root)
                self.assertEqual(len(self.calls), count)
                self.outcomes.clear()
                retry_dataset(self.root, "A")

    def test_mr_failed_does_not_reach_postmr(self):
        self.outcomes[("A", "phaser")] = "MR_FAILED"
        result = execute_campaign(self.root)
        self.assertEqual(self.items(result)["A"]["status"], "NO_SOLUTION")
        self.assertNotIn(("A", "postmr"), self.calls)
        self.assertEqual(self.items(result)["B"]["status"], "SOLVED")

    def test_changed_completed_output_blocks_resume_but_other_dataset_runs(self):
        result = execute_campaign(self.root, datasets=("A",), through="postmr")
        run = self.root / self.items(result)["A"]["run"]
        (run / "preflight.dat").write_text("changed model")
        self.calls.clear()
        result = execute_campaign(self.root)
        self.assertEqual(self.items(result)["A"]["status"], "BLOCKED")
        self.assertTrue(all(name == "B" for name, stage in self.calls))

    def test_changed_live_report_is_not_overwritten_or_adopted(self):
        result = execute_campaign(self.root, datasets=("A",), through="preflight")
        report = self.root / self.items(result)["A"]["run"] / "report.json"
        report.write_text('{"stage":"phaser","status":"MR_SUCCESS"}')
        result = execute_campaign(self.root, datasets=("A",))
        self.assertIn("Run report changed", self.items(result)["A"]["diagnostic"])
        self.assertEqual(self.calls, [("A", "preflight")])

    def test_input_drift_before_and_during_stage_cannot_be_accepted(self):
        (self.root / "A" / "staraniso-alldata.mtz").write_bytes(b"changed input")
        def mutate(name, stage):
            if name == "B" and stage == "phaser":
                (self.root / "B" / "staraniso-alldata.mtz").write_bytes(b"changed midstage")
        self.after_stage = mutate
        result = execute_campaign(self.root)
        self.assertEqual({item["status"] for item in self.items(result).values()}, {"BLOCKED"})
        self.assertNotIn(("A", "preflight"), self.calls)
        self.assertNotIn(("B", "postmr"), self.calls)
        with self.assertRaisesRegex(CampaignError, "integrity"):
            retry_dataset(self.root, "B")

    def test_pause_finishes_current_stage_and_next_run_resumes(self):
        self.after_stage = lambda name, stage: request_pause(self.root) if (name, stage) == ("A", "phaser") else None
        result = execute_campaign(self.root)
        self.assertEqual(result["execution"]["state"], "PAUSED")
        self.assertEqual(self.calls, [("A", "preflight"), ("A", "phaser")])
        self.after_stage = None
        execute_campaign(self.root)
        self.assertEqual(self.calls.count(("A", "phaser")), 1)

    def test_competing_controller_cannot_launch_another_dataset(self):
        def compete(name, stage):
            with self.assertRaisesRegex(CampaignError, "lock busy"):
                execute_campaign(self.root, datasets=("B",))
        self.after_stage = compete
        result = execute_campaign(self.root, datasets=("A",), through="preflight")
        self.assertEqual(self.calls, [("A", "preflight")])
        self.assertEqual(self.items(result)["B"]["status"], "DISCOVERED")

    def test_interrupted_stage_is_never_automatically_repeated(self):
        def interrupted(job, **callbacks):
            callbacks["on_process"](self.identity)
            raise KeyboardInterrupt
        with patch("nasolve.campaign_execution.run_job", side_effect=interrupted), \
                patch("nasolve.campaign_execution.process_alive", return_value=False):
            result = execute_campaign(self.root)
        self.assertEqual(result["execution"]["state"], "PAUSED")
        with patch("nasolve.campaign_execution.process_alive", return_value=False):
            result = execute_campaign(self.root)
            self.assertEqual(self.items(result)["A"]["status"], "AWAITING_INSPECTION")
            self.assertEqual(self.items(result)["B"]["status"], "SOLVED")
            retry_dataset(self.root, "A")
            result = execute_campaign(self.root)
        self.assertEqual(self.items(result)["A"]["status"], "SOLVED")
        self.assertEqual(len(self.items(result)["A"]["attempts"]), 2)

    def test_parent_crash_after_receipt_recovers_completed_stage_without_reexecution(self):
        result = execute_campaign(self.root, datasets=("A",), through="postmr")
        (self.directory("A", "postmr") / "process-finished.json").unlink()
        self.calls.clear()
        with patch("nasolve.campaign_execution.process_alive", return_value=False):
            result = execute_campaign(self.root, datasets=("A",))
        self.assertEqual(self.calls, [("A", "autosol"), ("A", "autorefine")])
        self.assertEqual(self.items(result)["A"]["status"], "SOLVED")

    def test_verified_spawn_interrupt_and_launch_failure_are_retryable_without_pid(self):
        for failure in (KeyboardInterrupt(), CampaignProcessError("Could not spawn", stopped_verified=True)):
            failure.stopped_verified = True
            with self.subTest(failure=type(failure).__name__):
                with patch("nasolve.campaign_execution.run_job", side_effect=failure):
                    result = execute_campaign(self.root, datasets=("A",))
                self.assertEqual(self.items(result)["A"]["status"], "AWAITING_INSPECTION")
                result = retry_dataset(self.root, "A")
                self.assertEqual(self.items(result)["A"]["status"], "DISCOVERED")

    def test_live_or_unknown_worker_prevents_retry_and_duplicate_start(self):
        execute_campaign(self.root, datasets=("A",), through="preflight")
        (self.directory("A", "preflight") / "process-finished.json").unlink()
        self.calls.clear()
        for activity in (True, None):
            with self.subTest(activity=activity), patch("nasolve.campaign_execution.process_alive", return_value=activity):
                with self.assertRaisesRegex(CampaignError, "worker"):
                    retry_dataset(self.root, "A")
                if activity is True:
                    with self.assertRaisesRegex(CampaignError, "worker"):
                        execute_campaign(self.root)
                else:
                    result = execute_campaign(self.root, datasets=("A",))
                    self.assertEqual(self.items(result)["A"]["status"], "AWAITING_INSPECTION")
        self.assertEqual(self.calls, [])

    def test_retry_schedules_without_running_and_keeps_old_receipt(self):
        execute_campaign(self.root, datasets=("A",))
        receipt = self.directory("A", "autorefine") / "result.json"
        before = receipt.read_bytes()
        count = len(self.calls)
        result = retry_dataset(self.root, "A")
        self.assertEqual(len(self.calls), count)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(self.items(result)["A"]["status"], "DISCOVERED")
        execute_campaign(self.root, datasets=("A",))
        self.assertEqual(receipt.read_bytes(), before)

    def test_nonzero_worker_exit_cannot_accept_a_success_receipt(self):
        def wrong_exit(job, **callbacks):
            self.run_job(job, **callbacks)
            return 1
        with patch("nasolve.campaign_execution.run_job", side_effect=wrong_exit):
            result = execute_campaign(self.root, datasets=("A",))
        self.assertEqual(self.items(result)["A"]["status"], "BLOCKED")
        self.assertIn("exited unsuccessfully", self.items(result)["A"]["diagnostic"])
        self.assertEqual(self.calls, [("A", "preflight")])

    def test_real_subprocess_worker_records_runtime_failure_without_allocating_run(self):
        with patch("nasolve.campaign_execution.run_job", side_effect=real_run_job):
            result = execute_campaign(self.root, datasets=("A",), through="preflight",
                                      phenix_root=str(self.base / "no-such-phenix"))
        item = self.items(result)["A"]
        self.assertEqual(item["status"], "BLOCKED", item["diagnostic"])
        self.assertIsNone(item["run"])
        directory = self.directory("A", "preflight")
        receipt = read_record(directory / "result.json")
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertTrue((directory / "worker.log").is_file())
        self.assertTrue((directory / "worker-process.json").is_file())
        self.assertFalse((self.root / "A/AutoMR").exists())

    def test_corrupt_receipt_lineage_and_state_are_rejected(self):
        execute_campaign(self.root, datasets=("A",), through="phaser")
        receiptpath = self.directory("A", "phaser") / "result.json"
        receipt = read_record(receiptpath)
        receipt["run"] = "B/AutoMR/run_001"
        write_record(receiptpath, receipt, replace=True)
        self.assertEqual(self.items(execution_status(self.root))["A"]["status"], "BLOCKED")
        statepath = self.root / EXECUTION / "state.json"
        statepath.write_text("{}")
        with self.assertRaisesRegex(CampaignError, "checksum"):
            execution_status(self.root)

    def test_symlink_execution_path_is_rejected_before_writing(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.root / EXECUTION).symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(CampaignError, "symbolic link"):
            execute_campaign(self.root)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
