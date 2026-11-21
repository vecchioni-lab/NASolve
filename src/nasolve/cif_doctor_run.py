"""Read-only CIF Doctor assessment of an existing immutable checkpoint.

This adapter resolves the selected checkpoint's complete effective input bundle;
it never searches for a dictionary by component name or initializes a registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .checkpoints import (
    CheckpointError,
    checkpoint_record,
    inherited_paths,
    read_registry,
    registry_path,
    resolve_checkpoint,
)
from .cif_doctor import assess_dictionaries
from .model_assessment import file_sha256
from .run_context import artifact_reference


def _reference(path: Path, run: Path) -> dict[str, object]:
    """Describe a resolved file without inventing a portable anchor."""
    reference: dict[str, object] = {
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }
    anchored = artifact_reference(path, run)
    if anchored["anchor"] == "absolute":
        reference.update({
            "portable": False,
            "provenance_path": anchored["absolute_path"],
        })
    else:
        reference.update(anchored)
    return reference


def _require_unchanged(path: Path, reference: Mapping[str, object]) -> None:
    if not path.is_file() or file_sha256(path) != reference["sha256"]:
        raise CheckpointError(
            f"CIF Doctor input changed during read-only assessment: {path}"
        )


def _require_registry_unchanged(
    path: Path, reference: Mapping[str, object] | None
) -> None:
    if reference is not None:
        _require_unchanged(path, reference)
    elif path.exists():
        raise CheckpointError("Checkpoint registry appeared during CIF assessment")


def assess_run(run: Path, *, checkpoint: str | None = None) -> dict[str, object]:
    """Assess a selected run/checkpoint without creating or modifying artifacts.

    The current checkpoint is used unless an explicit ID or bookmark is given.
    The established checkpoint resolver verifies every available frozen checksum,
    including observations and phase data, before the assessor sees any inputs.
    An uninitialized run uses the existing validated, in-memory PostMR root.
    """
    requested_run = run.expanduser().resolve()
    if requested_run.name == "report.json":
        requested_run = requested_run.parent
    report_path = requested_run / "report.json"
    existing_registry = registry_path(requested_run)
    try:
        report_ref = _reference(report_path, requested_run)
        registry_ref = (
            _reference(existing_registry, requested_run)
            if existing_registry.is_file() else None
        )
    except OSError as exc:
        raise CheckpointError(f"Could not snapshot CIF assessment run provenance: {exc}") from exc
    run, registry = read_registry(requested_run)
    _require_unchanged(report_path, report_ref)
    _require_registry_unchanged(existing_registry, registry_ref)
    selected = resolve_checkpoint(registry, checkpoint)
    record = checkpoint_record(selected, run)
    if record.model is None:
        raise CheckpointError("Selected checkpoint has no usable model for CIF assessment")
    restraint_values = selected.get("restraints")
    if not isinstance(restraint_values, list) or not all(
        isinstance(value, Mapping) for value in restraint_values
    ):
        raise CheckpointError("Malformed frozen checkpoint restraint list")
    inherited = inherited_paths(selected, run)
    model = inherited["model"]
    observations = inherited["observations"]
    restraints = inherited["restraints"]
    assert isinstance(model, Path)
    assert isinstance(observations, Path)
    assert isinstance(restraints, list)

    model_ref = _reference(model, run)
    observations_ref = _reference(observations, run)
    restraint_refs = [_reference(path, run) for path in restraints]
    phase = inherited["phases"]
    phase_ref = _reference(phase, run) if isinstance(phase, Path) else None

    receipt = assess_dictionaries(restraints, stage="effective", model=model)
    inputs = receipt.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != len(restraints):
        raise ValueError("CIF assessor returned an incomplete input inventory")
    for descriptor, reference in zip(inputs, restraint_refs):
        if not isinstance(descriptor, dict) or descriptor.get("sha256") != reference["sha256"]:
            raise CheckpointError("CIF assessor input inventory does not match the frozen bundle")
        descriptor["frozen_reference"] = dict(reference)
    model_descriptor = receipt.get("model")
    if not isinstance(model_descriptor, dict) or model_descriptor.get("sha256") != model_ref["sha256"]:
        raise CheckpointError("CIF assessor model inventory does not match the selected checkpoint")
    model_descriptor["frozen_reference"] = dict(model_ref)

    tracked = [
        (report_path, report_ref),
        (model, model_ref),
        (observations, observations_ref),
        *zip(restraints, restraint_refs),
    ]
    if registry_ref is not None:
        tracked.append((existing_registry, registry_ref))
    _require_registry_unchanged(existing_registry, registry_ref)
    if isinstance(phase, Path) and phase_ref is not None:
        tracked.append((phase, phase_ref))
    for path, reference in tracked:
        _require_unchanged(path, reference)
    # Recheck the declared frozen hashes, rather than only the fresh snapshots:
    # a file could have changed between the first resolver and snapshot capture.
    inherited_paths(selected, run)

    receipt["run_context"] = {
        "run": {"anchor": "run", "relative_path": "."},
        "report": report_ref,
        "registry": registry_ref,
        "registry_source": (
            "frozen_registry" if registry_ref is not None else "derived_postmr_root"
        ),
        "checkpoint": {
            "id": record.checkpoint_id,
            "parent": record.parent,
            "status": record.status,
            "usable": record.usable,
            "recipe": record.recipe,
            "current": registry.get("current"),
            "requested": checkpoint,
            "compatibility": selected.get("compatibility"),
        },
        "model": model_ref,
        "observations": observations_ref,
        "phases": phase_ref,
        "effective_restraints": restraint_refs,
        "read_only": True,
    }
    return receipt


__all__ = ["assess_run"]
