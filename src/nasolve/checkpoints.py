"""Immutable, user-visible refinement checkpoints.

The checkpoint registry is deliberately independent of Phenix.  It records the
model lineage and the frozen crystallographic inputs needed to reproduce or
branch a refinement, including work performed manually outside NASolve.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


class CheckpointError(RuntimeError):
    """Raised when checkpoint provenance cannot be established safely."""


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    parent: str | None
    status: str
    model: Path | None
    usable: bool
    recipe: str
    label: str | None
    metrics: dict[str, float | None]


SCHEMA_VERSION = 1
AUTOMATIC_STATUSES = {"READY", "SUCCESS", "USER_APPROVED"}
REUSABLE_STATUSES = AUTOMATIC_STATUSES | {"REVIEW"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _required_file(value: object, description: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CheckpointError(f"Run report has no {description}")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise CheckpointError(f"Required {description} is missing: {path}")
    return path


def _run_and_report(run_directory: Path) -> tuple[Path, dict[str, object]]:
    selected = run_directory.expanduser().resolve()
    report_path = selected if selected.name == "report.json" else selected / "report.json"
    run = report_path.parent
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"Could not read NASolve report {report_path}: {exc}") from exc
    if report.get("workflow") != "automr":
        raise CheckpointError("Checkpoints require a NASolve AutoMR run")
    postmr = report.get("postmr")
    if not isinstance(postmr, Mapping) or postmr.get("status") != "POSTMR_READY":
        raise CheckpointError("Checkpoints require a completed POSTMR_READY model")
    return run, report


def registry_path(run_directory: Path) -> Path:
    run = run_directory.expanduser().resolve()
    if run.name == "report.json":
        run = run.parent
    return run / "AutoRefine" / "checkpoints.json"


def _file_reference(path: Path) -> dict[str, object]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise CheckpointError(f"Checkpoint input is missing: {resolved}")
    return {
        "path": str(resolved),
        "sha256": _sha256(resolved),
        "size": resolved.stat().st_size,
    }


def _ref_path(value: object, description: str, *, required: bool = True) -> Path | None:
    path_value = value.get("path") if isinstance(value, Mapping) else None
    if not isinstance(path_value, str):
        if required:
            raise CheckpointError(f"Checkpoint has no {description}")
        return None
    path = Path(path_value).expanduser().resolve()
    if required and not path.is_file():
        raise CheckpointError(f"Checkpoint {description} is missing: {path}")
    if not path.is_file():
        return None
    expected = value.get("sha256") if isinstance(value, Mapping) else None
    if isinstance(expected, str) and _sha256(path) != expected:
        raise CheckpointError(
            f"Checkpoint {description} changed after it was frozen: {path}"
        )
    return path


def _initial_restraints(postmr: Mapping[str, object]) -> list[Path]:
    values = postmr.get("restraints")
    paths = [
        Path(value).expanduser().resolve()
        for value in values
        if isinstance(values, list) and isinstance(value, str)
    ] if isinstance(values, list) else []
    readyset = postmr.get("readyset")
    generated = readyset.get("generated_ligand_cif") if isinstance(readyset, Mapping) else None
    generated_path = (
        Path(generated).expanduser().resolve()
        if isinstance(generated, str) and Path(generated).expanduser().is_file()
        else None
    )
    # ReadySet's combined ligand dictionary supersedes the individual input CIFs.
    retained = [path for path in paths if path.suffix.lower() != ".cif"]
    if generated_path is not None:
        retained.append(generated_path)
    else:
        retained.extend(path for path in paths if path.suffix.lower() == ".cif")
    missing = [path for path in retained if not path.is_file()]
    if missing:
        raise CheckpointError(f"PostMR restraint input is missing: {missing[0]}")
    return list(dict.fromkeys(retained))


def _phase_reference(report: Mapping[str, object]) -> dict[str, object] | None:
    autosol = report.get("autosol")
    if not isinstance(autosol, Mapping) or autosol.get("use_for_refinement") is not True:
        return None
    outputs = autosol.get("outputs")
    if not isinstance(outputs, Mapping):
        return None
    path = _required_file(outputs.get("refinement_data"), "AutoSol refinement data")
    labels = outputs.get("refinement_data_phase_labels")
    return {
        **_file_reference(path),
        "labels": list(labels) if isinstance(labels, list) else [],
        "source": "validated-autosol",
    }


def _root_payload(report: Mapping[str, object]) -> dict[str, object]:
    postmr = report["postmr"]
    assert isinstance(postmr, Mapping)
    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise CheckpointError("Run report has no frozen AutoMR inputs")
    model = _required_file(postmr.get("prepared_model"), "PostMR prepared model")
    reflections = _required_file(inputs.get("reflections"), "authoritative reflections")
    restraint_refs = [_file_reference(path) for path in _initial_restraints(postmr)]
    return {
        "id": "postmr",
        "parent": None,
        "kind": "postmr",
        "status": "READY",
        "usable": True,
        "created_utc": str(postmr.get("created_utc") or _now()),
        "recipe": "PostMR/ReadySet",
        "label": "ReadySet model",
        "model": _file_reference(model),
        "observations": _file_reference(reflections),
        "phases": _phase_reference(report),
        "restraints": restraint_refs,
        "metrics": {},
        "compatibility": {"validated": True, "source": "POSTMR_READY"},
    }


def initialize_registry(run_directory: Path) -> tuple[Path, dict[str, object]]:
    """Create the root PostMR checkpoint, or validate an existing registry."""
    run, report = _run_and_report(run_directory)
    path = registry_path(run)
    if path.is_file():
        try:
            registry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointError(f"Could not read checkpoint registry {path}: {exc}") from exc
        if registry.get("schema_version") != SCHEMA_VERSION:
            raise CheckpointError(f"Unsupported checkpoint schema in {path}")
        checkpoints = registry.get("checkpoints")
        if not isinstance(checkpoints, list) or not any(
            isinstance(item, Mapping) and item.get("id") == "postmr" for item in checkpoints
        ):
            raise CheckpointError("Checkpoint registry has no PostMR root")
        return run, registry
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = {
        "schema_version": SCHEMA_VERSION,
        "run_directory": str(run),
        "created_utc": _now(),
        "updated_utc": _now(),
        "current": "postmr",
        "bookmarks": {},
        "checkpoints": [_root_payload(report)],
    }
    _write_json(path, registry)
    return run, registry


def save_registry(run: Path, registry: dict[str, object]) -> Path:
    registry["updated_utc"] = _now()
    path = registry_path(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, registry)
    return path


def _items(registry: Mapping[str, object]) -> list[dict[str, object]]:
    values = registry.get("checkpoints")
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise CheckpointError("Malformed checkpoint registry")
    return values  # type: ignore[return-value]


def resolve_checkpoint(
    registry: Mapping[str, object], checkpoint: str | None = None
) -> dict[str, object]:
    requested = checkpoint or registry.get("current")
    if not isinstance(requested, str) or not requested:
        raise CheckpointError("No current checkpoint is selected")
    bookmarks = registry.get("bookmarks")
    if isinstance(bookmarks, Mapping) and isinstance(bookmarks.get(requested), str):
        requested = bookmarks[requested]
    for item in _items(registry):
        if item.get("id") == requested:
            return item
    raise CheckpointError(f"Unknown checkpoint or bookmark: {requested}")


def checkpoint_record(item: Mapping[str, object]) -> CheckpointRecord:
    metrics = item.get("metrics")
    normalized_metrics = {
        str(key): float(value) if isinstance(value, (int, float)) else None
        for key, value in metrics.items()
    } if isinstance(metrics, Mapping) else {}
    return CheckpointRecord(
        checkpoint_id=str(item.get("id")),
        parent=str(item["parent"]) if isinstance(item.get("parent"), str) else None,
        status=str(item.get("status", "UNKNOWN")),
        model=_ref_path(item.get("model"), "model", required=False),
        usable=item.get("usable") is True,
        recipe=str(item.get("recipe", "unknown")),
        label=str(item["label"]) if isinstance(item.get("label"), str) else None,
        metrics=normalized_metrics,
    )


def list_checkpoints(run_directory: Path) -> tuple[list[CheckpointRecord], str, dict[str, str]]:
    _, registry = initialize_registry(run_directory)
    current = str(registry.get("current", "postmr"))
    bookmarks = registry.get("bookmarks")
    aliases = {
        str(name): str(target)
        for name, target in bookmarks.items()
        if isinstance(bookmarks, Mapping) and isinstance(name, str) and isinstance(target, str)
    } if isinstance(bookmarks, Mapping) else {}
    return [checkpoint_record(item) for item in _items(registry)], current, aliases


def next_checkpoint_id(registry: Mapping[str, object], prefix: str) -> str:
    expression = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    numbers = [
        int(match.group(1))
        for item in _items(registry)
        if isinstance(item.get("id"), str)
        and (match := expression.match(str(item["id"]))) is not None
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def append_checkpoint(
    run: Path,
    registry: dict[str, object],
    payload: dict[str, object],
    *,
    select: bool = False,
) -> Path:
    checkpoint_id = payload.get("id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise CheckpointError("New checkpoint has no ID")
    if any(item.get("id") == checkpoint_id for item in _items(registry)):
        raise CheckpointError(f"Checkpoint already exists: {checkpoint_id}")
    payload.setdefault("created_utc", _now())
    _items(registry).append(payload)
    if select:
        registry["current"] = checkpoint_id
    return save_registry(run, registry)


def select_checkpoint(run_directory: Path, checkpoint: str) -> CheckpointRecord:
    run, registry = initialize_registry(run_directory)
    item = resolve_checkpoint(registry, checkpoint)
    if item.get("usable") is not True or item.get("status") not in REUSABLE_STATUSES:
        raise CheckpointError(f"Checkpoint {item.get('id')} is not reusable")
    _ref_path(item.get("model"), "model")
    registry["current"] = item["id"]
    save_registry(run, registry)
    return checkpoint_record(item)


def _valid_bookmark(name: str) -> str:
    normalized = name.strip()
    if not normalized or len(normalized) > 80:
        raise CheckpointError("Checkpoint name must contain 1-80 characters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]*", normalized):
        raise CheckpointError(
            "Checkpoint name may contain letters, numbers, spaces, '.', '_' and '-'"
        )
    return normalized


def add_checkpoint(
    run_directory: Path,
    *,
    name: str,
    model: Path | None = None,
    reflections: Path | None = None,
    parent: str | None = None,
) -> CheckpointRecord:
    """Bookmark the current node, or import a manual model as a new child."""
    run, registry = initialize_registry(run_directory)
    label = _valid_bookmark(name)
    bookmarks = registry.setdefault("bookmarks", {})
    if not isinstance(bookmarks, dict):
        raise CheckpointError("Malformed checkpoint bookmarks")
    if label in bookmarks:
        raise CheckpointError(f"Checkpoint name already exists: {label}")
    base = resolve_checkpoint(registry, parent)
    if model is None:
        if reflections is not None:
            raise CheckpointError("--mtz may be used only when importing --model")
        bookmarks[label] = base["id"]
        save_registry(run, registry)
        return checkpoint_record(base)

    source_model = model.expanduser().resolve()
    if not source_model.is_file():
        raise CheckpointError(f"Manual checkpoint model does not exist: {source_model}")
    source_reflections: Path | None = None
    if reflections is not None:
        source_reflections = reflections.expanduser().resolve()
        if not source_reflections.is_file():
            raise CheckpointError(
                f"Manual checkpoint reflections do not exist: {source_reflections}"
            )
    checkpoint_id = next_checkpoint_id(registry, "manual")
    destination_dir = run / "AutoRefine" / "Checkpoints" / checkpoint_id
    destination_dir.mkdir(parents=True)
    destination_model = destination_dir / source_model.name
    shutil.copyfile(source_model, destination_model)
    observations = base.get("observations")
    if source_reflections is not None:
        destination_reflections = destination_dir / source_reflections.name
        shutil.copyfile(source_reflections, destination_reflections)
        observations = _file_reference(destination_reflections)
    payload = {
        "id": checkpoint_id,
        "parent": base["id"],
        "kind": "manual",
        "status": "REVIEW",
        "usable": True,
        "recipe": "manual-import",
        "label": label,
        "model": _file_reference(destination_model),
        "observations": observations,
        "phases": base.get("phases"),
        "restraints": base.get("restraints", []),
        "metrics": {},
        "compatibility": {
            "validated": False,
            "source": str(source_model),
            "review_required": True,
        },
    }
    append_checkpoint(run, registry, payload, select=False)
    bookmarks = registry.setdefault("bookmarks", {})
    assert isinstance(bookmarks, dict)
    bookmarks[label] = checkpoint_id
    save_registry(run, registry)
    return checkpoint_record(payload)


def inherited_paths(item: Mapping[str, object]) -> dict[str, object]:
    """Resolve and verify the frozen files inherited by a refinement child."""
    model = _ref_path(item.get("model"), "model")
    observations = _ref_path(item.get("observations"), "observations")
    phase = _ref_path(item.get("phases"), "phase data", required=False)
    restraint_values = item.get("restraints")
    restraints = [
        _ref_path(value, "restraint")
        for value in restraint_values
        if isinstance(restraint_values, Sequence) and isinstance(value, Mapping)
    ] if isinstance(restraint_values, list) else []
    return {
        "model": model,
        "observations": observations,
        "phases": phase,
        "phase_metadata": item.get("phases"),
        "restraints": [path for path in restraints if path is not None],
    }


__all__ = [
    "AUTOMATIC_STATUSES",
    "CheckpointError",
    "CheckpointRecord",
    "add_checkpoint",
    "append_checkpoint",
    "checkpoint_record",
    "inherited_paths",
    "initialize_registry",
    "list_checkpoints",
    "next_checkpoint_id",
    "registry_path",
    "resolve_checkpoint",
    "save_registry",
    "select_checkpoint",
]
