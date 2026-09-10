"""Durable local campaign records and portable checksummed artifacts.

Record digests detect accidental corruption, not hostile modification. Stage
receipts are immutable; operational state and heartbeats are atomically replaced.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .campaigns import CampaignError, _canonical, _file_identity, _json_object, _safe_relative


STAGES = ("preflight", "phaser", "postmr", "autosol", "autorefine")
EXECUTION = "NASolveCampaign/execution"
ACCEPTED = {
    "preflight": {"READY", "READY_POST_MR_MUTATION", "READY_WITH_RED_FLAG"},
    "phaser": {"MR_SUCCESS"}, "postmr": {"POSTMR_READY"},
    "autosol": {"AUTOSOL_READY", "SKIPPED"}, "autorefine": {"AUTOREFINE_READY"},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def path_in(root: Path, relative: str) -> Path:
    """Reject path traversal and symlink components, including dangling links."""
    relative = _safe_relative(relative, "execution path")
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise CampaignError(f"Execution path contains a symbolic link: {relative}")
    return path


def run_path(root: Path, dataset: str, relative: str) -> Path:
    if not isinstance(relative, str) or not re.fullmatch(re.escape(dataset) + r"/AutoMR/run_[0-9]{3,}", relative):
        raise CampaignError("Campaign run must be an exact numbered run in its dataset")
    return path_in(root, relative)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_record(path: Path, value: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
    unsigned = {key: item for key, item in value.items() if key != "record_sha256"}
    record = dict(unsigned, record_sha256=hashlib.sha256(_canonical(unsigned)).hexdigest())
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
        _sync_directory(path.parent)
    except (OSError, ValueError, TypeError) as exc:
        raise CampaignError(f"Cannot save campaign record {path.name}: {exc}") from exc
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return record


def read_record(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        unsigned = {key: item for key, item in value.items() if key != "record_sha256"}
        if value.get("record_sha256") != hashlib.sha256(_canonical(unsigned)).hexdigest():
            raise ValueError("record checksum mismatch")
        return value
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise CampaignError(f"Cannot read campaign record {path.name}: {exc}") from exc


def artifact(root: Path, relative: str) -> dict[str, Any]:
    path = path_in(root, relative)
    try:
        digest, size = _file_identity(path)
    except (OSError, ValueError) as exc:
        raise CampaignError(f"Cannot verify stage artifact {relative}: {exc}") from exc
    return {"anchor": "campaign", "relative_path": relative, "sha256": digest, "size": size}


def verify_artifact(root: Path, reference: dict[str, Any]) -> None:
    if (not isinstance(reference, dict) or reference.get("anchor") != "campaign"
            or not isinstance(reference.get("relative_path"), str)
            or type(reference.get("size")) is not int or reference["size"] < 0
            or not isinstance(reference.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]) is None):
        raise CampaignError("Malformed stage artifact reference")
    actual = artifact(root, reference["relative_path"])
    if actual != reference:
        raise CampaignError(f"Stage artifact changed: {reference['relative_path']}")


def job_relative(dataset: str, attempt: int, stage: str) -> str:
    if stage not in STAGES or type(attempt) is not int or attempt < 1:
        raise CampaignError("Invalid campaign job stage or attempt")
    return f"{EXECUTION}/datasets/{dataset}/attempt_{attempt:03d}/{stage}"


def read_job(root: Path, path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    job = read_record(path)
    if (job.get("schema_version") != 1 or type(job.get("schema_version")) is not int
            or job.get("plan_fingerprint") != plan["fingerprint"]
            or not isinstance(job.get("launch_id"), str)):
        raise CampaignError("Campaign job does not match its frozen plan")
    dataset = job.get("dataset")
    if dataset not in {item["id"] for item in plan["datasets"]}:
        raise CampaignError("Campaign job has an unknown dataset")
    expected = path_in(root, job_relative(dataset, job.get("attempt"), job.get("stage"))) / "job.json"
    if expected != path:
        raise CampaignError("Campaign job is outside its declared attempt")
    if job.get("run") is not None:
        run_path(root, dataset, job["run"])
    if job.get("phenix_root") is not None and not isinstance(job["phenix_root"], str):
        raise CampaignError("Malformed Phenix override in campaign job")
    return job


def read_receipt(root: Path, directory: Path, job: dict[str, Any]) -> dict[str, Any]:
    result = read_record(directory / "result.json")
    if (type(result.get("schema_version")) is not int or result["schema_version"] != 1
            or result.get("job_sha256") != job["record_sha256"]
            or any(result.get(key) != job[key] for key in
                   ("launch_id", "dataset", "attempt", "stage", "plan_fingerprint"))
            or not isinstance(result.get("status"), str)
            or not isinstance(result.get("message"), str)
            or not isinstance(result.get("artifacts"), list)):
        raise CampaignError("Stage receipt does not match its immutable job")
    if result.get("run") is not None:
        run_path(root, job["dataset"], result["run"])
        if job.get("run") is not None and result["run"] != job["run"]:
            raise CampaignError("Stage receipt changed its assigned run")
    allowed = (directory.relative_to(root).as_posix() + "/",)
    if result.get("run") is not None:
        allowed += (result["run"] + "/",)
    for reference in result["artifacts"]:
        if not isinstance(reference, dict) or not isinstance(reference.get("relative_path"), str):
            raise CampaignError("Malformed stage artifact inventory")
        if not reference["relative_path"].startswith(allowed):
            raise CampaignError("Stage artifact is outside its dataset run or job")
        verify_artifact(root, reference)
    snapshot = result.get("run_report_snapshot")
    if snapshot is not None:
        if snapshot not in result["artifacts"]:
            raise CampaignError("Stage receipt is missing its run report snapshot checksum")
        verify_artifact(root, snapshot)
    return result


def verify_dependencies(root: Path, job: dict[str, Any], plan: dict[str, Any]) -> None:
    dependencies = job.get("dependencies")
    prior = STAGES[:STAGES.index(job["stage"])]
    if not isinstance(dependencies, list) or len(dependencies) != len(prior):
        raise CampaignError("Stage job has an incomplete dependency history")
    last = None
    for stage, dependency in zip(prior, dependencies):
        directory = path_in(root, job_relative(job["dataset"], job["attempt"], stage))
        previous = read_job(root, directory / "job.json", plan)
        receipt = read_receipt(root, directory, previous)
        if (not isinstance(dependency, dict)
                or dependency.get("job_sha256") != previous["record_sha256"]
                or dependency.get("receipt_sha256") != receipt["record_sha256"]
                or receipt["status"] not in ACCEPTED[stage]
                or receipt.get("run") != job.get("run")):
            raise CampaignError("Stage dependency is unaccepted or belongs to another run")
        last = receipt
    if last is not None:
        snapshot = last.get("run_report_snapshot")
        if snapshot is None:
            raise CampaignError("Completed dependency has no frozen run report")
        actual = artifact(root, job["run"] + "/report.json")
        if any(actual[field] != snapshot[field] for field in ("sha256", "size")):
            raise CampaignError("Run report changed outside the recorded campaign stages")
