"""One isolated scientific stage. Internal entry point used by campaign run."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from .campaign_process import current_process_identity, exclusive_lock
from .campaign_records import (
    artifact, now, path_in, read_job, run_path, verify_dependencies, write_record,
)
from .campaign_stages import execute_stage
from .campaigns import CampaignError, campaign_status


def execute_job(job_path: Path) -> int:
    job_path = job_path.expanduser().absolute()
    if len(job_path.parents) < 7:
        raise CampaignError("Invalid internal campaign job path")
    root = job_path.parents[6].resolve()
    plan = campaign_status(root)
    job = read_job(root, job_path, plan)
    directory = job_path.parent
    dataset = next(item for item in plan["datasets"] if item["id"] == job["dataset"])
    run = run_path(root, dataset["id"], job["run"]) if job["run"] else None
    with exclusive_lock(path_in(root, dataset["id"] + "/.nasolve-campaign.lock")):
        write_record(directory / "worker-process.json", current_process_identity())

        def allocated(path: Path) -> None:
            nonlocal run
            relative = path.relative_to(root).as_posix()
            run = run_path(root, dataset["id"], relative)
            write_record(directory / "allocation.json", {
                "job_sha256": job["record_sha256"], "run": relative,
            })

        result = {key: job[key] for key in
                  ("launch_id", "dataset", "attempt", "stage", "plan_fingerprint")}
        result.update(schema_version=1, job_sha256=job["record_sha256"], artifacts=[])
        try:
            if plan["integrity_issues"] or dataset["integrity"] != "OK":
                raise CampaignError("Frozen campaign inputs changed; execution is blocked")
            verify_dependencies(root, job, plan)
            outcome = execute_stage(
                root, dataset, plan["preset"]["policy"], job["stage"], directory, run,
                phenix_root=job.get("phenix_root"), on_run_allocated=allocated,
            )
            # Freeze receipts only after all scientific writes have completed.
            checked = campaign_status(root)
            current = next(item for item in checked["datasets"] if item["id"] == dataset["id"])
            if checked["fingerprint"] != plan["fingerprint"] or checked["integrity_issues"] or current["integrity"] != "OK":
                raise CampaignError("Frozen inputs changed while the scientific stage was running")
            references = [artifact(root, relative) for relative in outcome.pop("artifacts")]
            snapshot_path = outcome.pop("run_report_snapshot", None)
            result.update(outcome, artifacts=references)
            if snapshot_path is not None:
                result["run_report_snapshot"] = next(
                    reference for reference in references if reference["relative_path"] == snapshot_path
                )
        except Exception as exc:
            traceback.print_exc()
            result.update(status="BLOCKED", message=f"{type(exc).__name__}: {exc}",
                          run=run.relative_to(root).as_posix() if run is not None else None,
                          artifacts=[], error_type=type(exc).__name__)
        result["completed_utc"] = now()
        write_record(directory / "result.json", result)
    return 0 if result["status"] != "BLOCKED" else 2


def main() -> int:
    try:
        if len(sys.argv) != 2:
            raise CampaignError("Internal campaign worker requires one job record")
        return execute_job(Path(sys.argv[1]))
    except Exception as exc:
        print(f"Campaign worker error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
