"""Read-only descriptors for checkpoint models that may later be considered by Campaign Doctor.

A descriptor is provenance, not a donor decision.  It records one checkpoint's
lineage, verified model bytes, literal coordinate inventory, frozen run intent
and source observations without selecting, exporting or reusing the model.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .backbone import BackboneError, requested_backbone_policy
from .checkpoints import (
    CheckpointError,
    REUSABLE_STATUSES,
    checkpoint_record,
    read_registry,
    resolve_checkpoint,
)
from .model_assessment import (
    ModelAssessmentError,
    file_sha256,
    inspect_pdb,
    literal_polymer_identity_inventory,
)
from .phosphate import PhosphateError, requested_op3_sites
from .residue_aliases import LigandCodeError, known_ligand_codes
from .run_context import artifact_reference, dataset_directory, resolve_artifact_path
from .search_model_comparison import (
    SearchModelComparisonError,
    compare_search_model_to_target,
)
from .sequence_family import load_frozen_sequence_family
from .sequence_reference import SequenceReferenceError


class CheckpointCandidateError(RuntimeError):
    """A checkpoint candidate cannot be described without guessing."""


def _run_report(run: Path) -> dict[str, object]:
    path = run / "report.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointCandidateError(
            f"Could not read NASolve run report {path}: {exc}"
        ) from exc
    if not isinstance(value, dict) or value.get("workflow") != "automr":
        raise CheckpointCandidateError(
            "Checkpoint candidate requires a NASolve AutoMR run report"
        )
    return value


def _lineage(
    registry: Mapping[str, object],
    selected: Mapping[str, object],
) -> list[str]:
    values = registry.get("checkpoints")
    if not isinstance(values, list) or not all(isinstance(item, Mapping) for item in values):
        raise CheckpointCandidateError("Malformed checkpoint registry")
    by_id: dict[str, Mapping[str, object]] = {}
    for item in values:
        checkpoint_id = item.get("id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            raise CheckpointCandidateError("Checkpoint registry contains an invalid ID")
        if checkpoint_id in by_id:
            raise CheckpointCandidateError(
                f"Checkpoint registry contains duplicate ID {checkpoint_id}"
            )
        by_id[checkpoint_id] = item

    checkpoint_id = selected.get("id")
    if not isinstance(checkpoint_id, str) or checkpoint_id not in by_id:
        raise CheckpointCandidateError("Selected checkpoint has no registry identity")

    lineage: list[str] = []
    seen: set[str] = set()
    current = checkpoint_id
    while True:
        if current in seen:
            raise CheckpointCandidateError("Checkpoint lineage contains a cycle")
        seen.add(current)
        lineage.append(current)
        item = by_id[current]
        parent = item.get("parent")
        if parent is None:
            break
        if not isinstance(parent, str) or parent not in by_id:
            raise CheckpointCandidateError(
                f"Checkpoint {current} has an unknown parent"
            )
        current = parent
    lineage.reverse()
    if not lineage or lineage[0] != "postmr":
        raise CheckpointCandidateError(
            "Checkpoint lineage is not rooted at the PostMR checkpoint"
        )
    return lineage


def _verified_artifact(
    value: object,
    run: Path,
    description: str,
) -> tuple[Path, dict[str, object]]:
    path = resolve_artifact_path(value, run)
    if path is None:
        raise CheckpointCandidateError(
            f"Checkpoint {description} is missing or failed checksum validation"
        )
    digest = file_sha256(path)
    return path, {
        **artifact_reference(path, run),
        "sha256": digest,
        "size": path.stat().st_size,
    }


def _target_context(
    report: Mapping[str, object],
    run: Path,
    assessment,
) -> dict[str, object]:
    try:
        family = load_frozen_sequence_family(report, run)
    except SequenceReferenceError as exc:
        raise CheckpointCandidateError(
            f"Frozen checkpoint target provenance failed validation: {exc}"
        ) from exc

    if family is None:
        return {
            "sequence_family": None,
            "checkpoint_model_target_comparison": None,
        }

    try:
        comparison = compare_search_model_to_target(assessment, family.target)
    except SearchModelComparisonError as exc:
        raise CheckpointCandidateError(
            f"Checkpoint model/target comparison failed: {exc}"
        ) from exc

    return {
        "sequence_family": {
            "reference": {
                "id": family.reference.identifier,
                "version": family.reference.version,
                "content_sha256": family.reference.content_sha256,
            },
            "reference_artifact": dict(family.record["reference"]),
            "target_artifact": dict(family.record["target"]),
        },
        "checkpoint_model_target_comparison": comparison,
    }


def describe_checkpoint_candidate(
    run_directory: Path,
    checkpoint: str | None = None,
) -> dict[str, object]:
    """Describe one checkpoint without changing the run or selecting the model."""
    try:
        run, registry = read_registry(run_directory)
        item = resolve_checkpoint(registry, checkpoint)
        record = checkpoint_record(item, run)
    except CheckpointError as exc:
        raise CheckpointCandidateError(str(exc)) from exc

    if record.model is None:
        raise CheckpointCandidateError(
            f"Checkpoint {record.checkpoint_id} has no verified model"
        )
    model = record.model

    model_value = item.get("model")
    verified_model, model_artifact = _verified_artifact(
        model_value, run, "model"
    )
    if verified_model != model:
        raise CheckpointCandidateError(
            "Checkpoint model resolution changed while being described"
        )

    report = _run_report(run)
    try:
        family = load_frozen_sequence_family(report, run)
        ligand_codes = set(known_ligand_codes())
        if family is not None:
            ligand_codes.update(family.codes.values())
        assessment = inspect_pdb(model, polymer_ligand_codes=ligand_codes)
        if assessment.duplicate_atom_identities:
            raise CheckpointCandidateError(
                "Checkpoint model contains duplicate coordinate atom identities"
            )
        identities = literal_polymer_identity_inventory(assessment)
    except (ModelAssessmentError, LigandCodeError) as exc:
        raise CheckpointCandidateError(
            f"Checkpoint model assessment failed: {exc}"
        ) from exc
    except SequenceReferenceError as exc:
        raise CheckpointCandidateError(
            f"Frozen checkpoint target provenance failed validation: {exc}"
        ) from exc

    if assessment.sha256 != model_artifact["sha256"]:
        raise CheckpointCandidateError(
            "Checkpoint model changed while being assessed"
        )

    observations, observation_artifact = _verified_artifact(
        item.get("observations"), run, "observations"
    )
    if file_sha256(observations) != observation_artifact["sha256"]:
        raise CheckpointCandidateError(
            "Checkpoint observations changed while being described"
        )

    try:
        phosphate_sites = list(requested_op3_sites(report))
        backbone_policy = requested_backbone_policy(report)
    except (PhosphateError, BackboneError) as exc:
        raise CheckpointCandidateError(
            f"Frozen checkpoint chemistry provenance failed validation: {exc}"
        ) from exc

    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise CheckpointCandidateError("Run report has no frozen AutoMR inputs")
    frame = report.get("frame")
    frame_name = frame.get("name") if isinstance(frame, Mapping) else None
    mode = report.get("mode")
    if not isinstance(mode, str):
        raise CheckpointCandidateError("Run report has no AutoMR mode")

    provider = inputs.get("model_provider")
    if provider is not None and not isinstance(provider, Mapping):
        raise CheckpointCandidateError("Run model-provider provenance is malformed")

    lineage = _lineage(registry, item)
    current = registry.get("current")
    if not isinstance(current, str):
        raise CheckpointCandidateError("Checkpoint registry has no current selection")

    created_utc = item.get("created_utc")
    if created_utc is not None and not isinstance(created_utc, str):
        raise CheckpointCandidateError("Checkpoint creation time is malformed")
    kind = item.get("kind")
    status = item.get("status")
    recipe = item.get("recipe")
    label = item.get("label")
    usable = item.get("usable")
    if (
        not isinstance(kind, str)
        or not isinstance(status, str)
        or not isinstance(recipe, str)
        or (label is not None and not isinstance(label, str))
        or type(usable) is not bool
    ):
        raise CheckpointCandidateError(
            "Checkpoint state is malformed for candidate description"
        )

    target_context = _target_context(report, run, assessment)
    local_reusable = usable and status in REUSABLE_STATUSES

    return {
        "schema_version": 1,
        "kind": "checkpoint-model-candidate",
        "source": {
            "dataset_name": dataset_directory(run).name,
            "run_id": run.name,
            "checkpoint_registry_schema": registry.get("schema_version"),
            "checkpoint_id": record.checkpoint_id,
            "parent_checkpoint": record.parent,
            "lineage": lineage,
            "checkpoint_kind": kind,
            "status": status,
            "usable": usable,
            "locally_reusable": local_reusable,
            "selected_current": current == record.checkpoint_id,
            "recipe": recipe,
            "label": label,
            "created_utc": created_utc,
        },
        "model": {
            "artifact": model_artifact,
            "assessment": {
                "atom_count": assessment.atom_count,
                "polymer_residue_count": assessment.polymer_residue_count,
                "heteroatom_count": assessment.heteroatom_count,
                "modified_polymer_residue_count": (
                    assessment.modified_polymer_residue_count
                ),
                "nonpolymer_hetero_residue_count": (
                    assessment.nonpolymer_hetero_residue_count
                ),
                "duplicate_atom_identities": assessment.duplicate_atom_identities,
                "chains": [
                    {
                        "chain": chain,
                        "residue_count": len(residue_ids),
                        "residue_ids": list(residue_ids),
                    }
                    for chain, residue_ids in (
                        assessment.polymer_residue_ids_by_chain.items()
                    )
                ],
                "residue_identities": [
                    {"site": site, "residue_code": code}
                    for site, code in identities.items()
                ],
            },
        },
        "source_observations": {
            "artifact": observation_artifact,
            "semantics": "source-provenance-only; not recipient evidence",
        },
        "run_context": {
            "mode": mode,
            "frame": frame_name,
            "mirror_transform_applied": inputs.get("mirror"),
            "source_model_provider": (
                dict(provider) if isinstance(provider, Mapping) else None
            ),
            "terminal_phosphate_sites": phosphate_sites,
            "backbone_policy": backbone_policy,
            **target_context,
        },
        "metrics": dict(record.metrics),
        "semantics": {
            "descriptive_only": True,
            "checkpoint_local_reusable": local_reusable,
            "donor_eligibility": None,
            "recipient_compatibility": None,
            "automatic_reuse_authorized": False,
        },
    }


__all__ = [
    "CheckpointCandidateError",
    "describe_checkpoint_candidate",
]
