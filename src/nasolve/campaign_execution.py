"""Foreground sequential execution over an immutable schema-1 campaign plan."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Callable, Any

from .campaign_process import exclusive_lock, process_alive, run_job
from .campaign_records import (
    ACCEPTED, EXECUTION, STAGES, artifact, job_relative, now, path_in, read_job,
    read_receipt, read_record, run_path, write_record,
)
from .campaigns import CampaignError, campaign_status


def _new_state(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1, "plan_fingerprint": plan["fingerprint"],
        "state": "PLANNED", "created_utc": now(), "updated_utc": now(),
        "datasets": [{
            "id": entry["id"], "status": entry["status"], "diagnostic": entry["diagnostic"],
            "attempts": [], "run": None, "next_stage": "preflight",
            "checkpoint": None, "numerical_success": False, "inspection_required": False,
        } for entry in plan["datasets"]],
    }


def _load_state(root: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    path = path_in(root, EXECUTION + "/state.json")
    if not path.exists():
        if path_in(root, EXECUTION + "/datasets").exists():
            raise CampaignError("Execution history exists without its state record; inspect before recovery")
        return None
    state = read_record(path)
    if (type(state.get("schema_version")) is not int or state["schema_version"] != 1
            or state.get("plan_fingerprint") != plan["fingerprint"]
            or not isinstance(state.get("datasets"), list)
            or not all(isinstance(item, dict) for item in state["datasets"])
            or [item.get("id") for item in state["datasets"]]
            != [item["id"] for item in plan["datasets"]]):
        raise CampaignError("Execution state does not match the frozen campaign plan")
    for item in state["datasets"]:
        attempts = item.get("attempts")
        if not isinstance(attempts, list):
            raise CampaignError("Malformed execution attempt history")
        for number, attempt in enumerate(attempts, 1):
            if (not isinstance(attempt, dict) or type(attempt.get("number")) is not int
                    or attempt["number"] != number):
                raise CampaignError("Malformed execution attempt numbering")
    # Displayed status is derived from live receipts and may differ from this
    # saved summary; do not attach the saved record's digest to derived fields.
    state.pop("record_sha256", None)
    return state


def _save(root: Path, state: dict[str, Any]) -> None:
    state["updated_utc"] = now()
    write_record(path_in(root, EXECUTION + "/state.json"), state, replace=True)


def _job_activity(directory: Path, job: dict[str, Any]) -> bool | None:
    completed = directory / "process-finished.json"
    if completed.exists():
        record = read_record(completed)
        if record.get("job_sha256") != job["record_sha256"]:
            raise CampaignError("Process completion belongs to another job")
        return False
    for name in ("process.json", "worker-process.json"):
        if (directory / name).exists():
            return process_alive(read_record(directory / name))
    # The coordinator may have died between spawn and identity publication.
    # Lack of a PID is not evidence that the scientific process has stopped.
    return None


def _report_unchanged(root: Path, last: dict[str, Any]) -> None:
    snapshot = last.get("run_report_snapshot")
    if snapshot is None or last.get("run") is None:
        raise CampaignError("Completed stage has no checksummed run report")
    actual = artifact(root, last["run"] + "/report.json")
    if any(actual[key] != snapshot[key] for key in ("sha256", "size")):
        raise CampaignError("Run report changed outside the recorded campaign stages")


def _recover_completions(root: Path, plan: dict[str, Any], state: dict[str, Any]) -> None:
    """Persist verified recovery under the controller lock for future relocation."""
    for item in state["datasets"]:
        for attempt in item["attempts"]:
            for stage in STAGES:
                directory = path_in(root, job_relative(item["id"], attempt["number"], stage))
                finished = directory / "process-finished.json"
                if finished.exists() or not (directory / "result.json").exists():
                    continue
                try:
                    job = read_job(root, directory / "job.json", plan)
                    if _job_activity(directory, job) is not False:
                        continue
                    receipt = read_receipt(root, directory, job)
                    with exclusive_lock(path_in(root, item["id"] + "/.nasolve-campaign.lock")):
                        write_record(finished, {
                            "job_sha256": job["record_sha256"], "return_code": None,
                            "finished_utc": now(), "recovered_from_receipt": receipt["record_sha256"],
                        })
                except (CampaignError, OSError, ValueError, KeyError, TypeError):
                    # The normal read-only reconciliation reports the blocker.
                    continue


def _inspect_attempt(root: Path, plan: dict[str, Any], item: dict[str, Any]) -> list[dict[str, str]]:
    item.update(run=None, checkpoint=None, next_stage="preflight", numerical_success=False,
                inspection_required=False, live_process=False)
    if not item["attempts"]:
        item.update(status="DISCOVERED", diagnostic="Ready for scientific preflight")
        return []
    attempt = item["attempts"][-1]["number"]
    dependencies = []
    last = None
    for stage in STAGES:
        directory = path_in(root, job_relative(item["id"], attempt, stage))
        if not (directory / "job.json").exists():
            if directory.exists() and any(directory.iterdir()):
                raise CampaignError(f"Incomplete {stage} job publication; inspect the retained attempt")
            if last is not None:
                _report_unchanged(root, last)
            item.update(status="PAUSED" if last else "DISCOVERED", next_stage=stage,
                        diagnostic=f"Ready to continue at {stage}" if last else "Ready for scientific preflight")
            return dependencies
        job = read_job(root, directory / "job.json", plan)
        if job.get("dependencies") != dependencies or job.get("run") != item["run"]:
            raise CampaignError("Campaign job has an inconsistent run or dependency lineage")
        activity = _job_activity(directory, job)
        if activity is not False:
            item.update(status="RUNNING" if activity is True else "AWAITING_INSPECTION",
                        live_process=activity is True, next_stage=stage, inspection_required=True,
                        diagnostic=(f"{stage} worker or its descendants are still running" if activity is True
                                    else f"Cannot establish that the {stage} worker stopped; inspect its process record"))
            allocation = directory / "allocation.json"
            if allocation.exists():
                record = read_record(allocation)
                if record.get("job_sha256") != job["record_sha256"]:
                    raise CampaignError("Run allocation belongs to another job")
                run_path(root, item["id"], record["run"])
                item["run"] = record["run"]
            return dependencies
        if not (directory / "result.json").exists():
            finished = directory / "process-finished.json"
            reason = read_record(finished).get("runner_error") if finished.exists() else None
            item.update(status="AWAITING_INSPECTION", next_stage=stage, inspection_required=True,
                        diagnostic=f"{stage}: {reason or 'interrupted without a complete receipt'}; retry explicitly in a new run")
            allocation = directory / "allocation.json"
            if allocation.exists():
                record = read_record(allocation)
                if record.get("job_sha256") != job["record_sha256"]:
                    raise CampaignError("Run allocation belongs to another job")
                run_path(root, item["id"], record["run"])
                item["run"] = record["run"]
            return dependencies
        receipt = read_receipt(root, directory, job)
        finished = directory / "process-finished.json"
        if finished.exists() and receipt["status"] in ACCEPTED[stage]:
            completion = read_record(finished)
            return_code = completion.get("return_code")
            recovered = completion.get("recovered_from_receipt") == receipt["record_sha256"]
            if not recovered and (type(return_code) is not int or return_code != 0):
                raise CampaignError("Worker exited unsuccessfully despite an accepted stage receipt")
        item.update(run=receipt.get("run"), checkpoint=receipt.get("checkpoint"), diagnostic=receipt["message"])
        item["attempts"][-1]["run"] = item["run"]
        if receipt["status"] not in ACCEPTED[stage]:
            status = "NO_SOLUTION" if receipt["status"] == "MR_FAILED" else (
                "AWAITING_INSPECTION" if receipt["status"] in {"MR_REVIEW", "AUTOSOL_REVIEW", "AUTOSOL_WARNING", "AUTOREFINE_REVIEW"}
                else "BLOCKED")
            item.update(status=status, next_stage=None, inspection_required=True)
            return dependencies
        if receipt.get("run") is None:
            raise CampaignError("Accepted stage has no allocated run")
        if stage == "autorefine" and (receipt.get("selected_as_current") is not True
                                      or not isinstance(receipt.get("checkpoint"), str)):
            raise CampaignError("Accepted refinement has no selected checkpoint")
        dependencies.append({"job_sha256": job["record_sha256"], "receipt_sha256": receipt["record_sha256"]})
        last = receipt
    assert last is not None
    _report_unchanged(root, last)
    item.update(status="SOLVED", next_stage=None, numerical_success=True, inspection_required=True,
                diagnostic="Numerical refinement criteria passed; inspect the model and maps before approval")
    return dependencies


def _reconcile(root: Path, plan: dict[str, Any], state: dict[str, Any]) -> None:
    for entry, item in zip(plan["datasets"], state["datasets"]):
        try:
            _inspect_attempt(root, plan, item)
            if entry["status"] == "BLOCKED":
                item.update(status="BLOCKED", diagnostic=entry["diagnostic"], next_stage=None)
            elif plan["integrity_issues"] or entry["integrity"] != "OK":
                item.update(status="BLOCKED", diagnostic="Frozen input integrity failed: " + "; ".join(
                    plan["integrity_issues"] + entry["integrity_issues"]), next_stage=None)
        except (CampaignError, OSError, ValueError, KeyError, TypeError) as exc:
            item.update(status="BLOCKED", next_stage=None, diagnostic=str(exc), inspection_required=True)
    statuses = {item["status"] for item in state["datasets"]}
    state["state"] = (
        "RUNNING" if "RUNNING" in statuses else
        "PAUSED" if statuses & {"DISCOVERED", "PAUSED"} else
        "COMPLETE_WITH_FLAGS" if statuses - {"SOLVED"} else "COMPLETE"
    )


def execution_status(root: Path) -> dict[str, Any]:
    """Read-only integrity and progress, including detached or interrupted jobs."""
    root = root.expanduser().resolve()
    plan = campaign_status(root)
    state = _load_state(root, plan)
    if state is not None:
        _reconcile(root, plan, state)
        request = path_in(root, EXECUTION + "/pause.json")
        if request.exists():
            pause = read_record(request)
            if pause.get("plan_fingerprint") != plan["fingerprint"]:
                raise CampaignError("Pause request belongs to another campaign plan")
            state["pause_requested"] = True
    return dict(plan, execution=state)


def request_pause(root: Path) -> dict[str, Any]:
    """Request a stop at the next stage boundary; never signal saved PIDs."""
    root = root.expanduser().resolve()
    plan = campaign_status(root)
    write_record(path_in(root, EXECUTION + "/pause.json"), {
        "schema_version": 1, "plan_fingerprint": plan["fingerprint"], "requested_utc": now(),
    }, replace=True)
    result = execution_status(root)
    if result["execution"] is None:
        result["execution"] = _new_state(plan)
    result["execution"].update(state="PAUSE_REQUESTED", pause_requested=True)
    return result


def _start_attempt(item: dict[str, Any], reason: str) -> None:
    item["attempts"].append({"number": len(item["attempts"]) + 1, "created_utc": now(),
                             "reason": reason, "run": None})
    item.update(status="DISCOVERED", next_stage="preflight", run=None, checkpoint=None,
                diagnostic="Ready for a new immutable run", inspection_required=False,
                numerical_success=False)


def retry_dataset(root: Path, dataset: str) -> dict[str, Any]:
    """Schedule a new run; preserve all earlier attempts and scientific outputs."""
    root = root.expanduser().resolve()
    plan = campaign_status(root)
    if dataset not in {entry["id"] for entry in plan["datasets"]}:
        raise CampaignError(f"Dataset {dataset!r} is not in the frozen plan")
    path_in(root, EXECUTION).mkdir(parents=True, exist_ok=True)
    with exclusive_lock(path_in(root, EXECUTION + "/campaign.lock")):
        state = _load_state(root, plan)
        if state is None:
            raise CampaignError("No campaign execution exists to retry")
        item = next(item for item in state["datasets"] if item["id"] == dataset)
        if not item["attempts"]:
            raise CampaignError("Dataset has no attempt to retry; use campaign run")
        entry = next(entry for entry in plan["datasets"] if entry["id"] == dataset)
        if plan["integrity_issues"] or entry["integrity"] != "OK" or entry["status"] == "BLOCKED":
            raise CampaignError("Restore frozen input integrity before retrying; a retry cannot change the plan")
        with exclusive_lock(path_in(root, dataset + "/.nasolve-campaign.lock")):
            # Check every previous attempt: none may still have a live writer.
            for attempt in item["attempts"]:
                for stage in STAGES:
                    directory = path_in(root, job_relative(dataset, attempt["number"], stage))
                    if (directory / "job.json").exists():
                        job = read_job(root, directory / "job.json", plan)
                        if _job_activity(directory, job) is not False:
                            raise CampaignError("Cannot retry while a previous worker may still be running")
            _start_attempt(item, "explicit retry")
            state["state"] = "PAUSED"
            _save(root, state)
    return execution_status(root)


def execute_campaign(
    root: Path, *, datasets: tuple[str, ...] | None = None, through: str = "autorefine",
    phenix_root: str | None = None, progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute eligible datasets sequentially, continuing only from verified receipts."""
    if os.name != "posix":
        raise CampaignError("Campaign execution currently requires macOS or Linux (POSIX process groups)")
    if through not in STAGES:
        raise CampaignError(f"Unknown campaign stop stage: {through}")
    root = root.expanduser().resolve()
    plan = campaign_status(root)
    known = {entry["id"] for entry in plan["datasets"]}
    selected = known if datasets is None else set(datasets)
    if not selected or not selected <= known:
        raise CampaignError("Select at least one exact dataset name from the frozen plan")
    if plan["integrity_issues"]:
        raise CampaignError("Frozen preset integrity failed: " + "; ".join(plan["integrity_issues"]))
    tell = progress or (lambda message: None)
    path_in(root, EXECUTION).mkdir(parents=True, exist_ok=True)
    with exclusive_lock(path_in(root, EXECUTION + "/campaign.lock")):
        state = _load_state(root, plan) or _new_state(plan)
        _recover_completions(root, plan, state)
        _reconcile(root, plan, state)
        if any(item.get("live_process") for item in state["datasets"]):
            raise CampaignError("A previous campaign worker is still running; inspect campaign status")
        pause_path = path_in(root, EXECUTION + "/pause.json")
        # A new foreground invocation explicitly resumes a previously paused campaign.
        if pause_path.exists():
            pause_path.unlink()
        _save(root, state)
        stopped = False
        for item in state["datasets"]:
            if item["id"] not in selected or item["status"] not in {"DISCOVERED", "PAUSED"}:
                continue
            if not item["attempts"]:
                _start_attempt(item, "initial execution")
                _save(root, state)
            while item["next_stage"] is not None and STAGES.index(item["next_stage"]) <= STAGES.index(through):
                if pause_path.exists():
                    stopped = True
                    break
                # Recheck frozen inputs and every completed stage at each boundary.
                plan = campaign_status(root)
                _reconcile(root, plan, state)
                if item["status"] not in {"DISCOVERED", "PAUSED"}:
                    break
                stage = item["next_stage"]
                dependencies = _inspect_attempt(root, plan, item)
                attempt = item["attempts"][-1]["number"]
                relative = job_relative(item["id"], attempt, stage)
                directory = path_in(root, relative)
                job = write_record(directory / "job.json", {
                    "schema_version": 1, "plan_fingerprint": plan["fingerprint"],
                    "launch_id": str(uuid.uuid4()), "dataset": item["id"], "attempt": attempt,
                    "stage": stage, "run": item["run"], "phenix_root": phenix_root,
                    "dependencies": dependencies, "created_utc": now(),
                })
                item.update(status="RUNNING", diagnostic=f"Running {stage}")
                state["state"] = "RUNNING"
                _save(root, state)
                tell(f"{item['id']}: {stage} started; log: {directory / 'worker.log'}")

                def record_process(identity: dict[str, Any]) -> None:
                    write_record(directory / "process.json", dict(identity, job_sha256=job["record_sha256"]), replace=True)

                try:
                    return_code = run_job(directory / "job.json", on_process=record_process, on_heartbeat=record_process)
                    write_record(directory / "process-finished.json", {
                        "job_sha256": job["record_sha256"], "return_code": return_code, "finished_utc": now(),
                    })
                except KeyboardInterrupt as exc:
                    if getattr(exc, "stopped_verified", False):
                        write_record(directory / "process-finished.json", {
                            "job_sha256": job["record_sha256"], "return_code": 130,
                            "finished_utc": now(), "interrupted": True,
                        })
                    stopped = True
                    tell(f"{item['id']}: interrupted {stage}; partial work retained for inspection")
                    break
                except CampaignError as exc:
                    if getattr(exc, "stopped_verified", False):
                        write_record(directory / "process-finished.json", {
                            "job_sha256": job["record_sha256"], "return_code": 127,
                            "finished_utc": now(), "runner_error": str(exc),
                        })
                    item.update(status="AWAITING_INSPECTION", next_stage=None,
                                diagnostic=str(exc), inspection_required=True)
                    tell(f"{item['id']}: {exc}")
                    break
                _reconcile(root, plan, state)
                _save(root, state)
                tell(f"{item['id']}: {item['status']}; {item['diagnostic']}")
                if item["status"] not in {"DISCOVERED", "PAUSED"}:
                    break
            _save(root, state)
            if stopped:
                break
        plan = campaign_status(root)
        _reconcile(root, plan, state)
        if stopped:
            state["state"] = "PAUSED"
        _save(root, state)
    return dict(plan, execution=state)


__all__ = ["execute_campaign", "execution_status", "request_pause", "retry_dataset"]
