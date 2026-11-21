"""Read-only CIF Doctor assessment of an existing immutable checkpoint.

This adapter resolves the selected checkpoint's complete effective input bundle;
it never searches for a dictionary by component name or initializes a registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .checkpoints import (
    CheckpointError,
    _read_registry_with_preparations,
    _ref_path,
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


def assess_run(
    run: Path, *, checkpoint: str | None = None, refined_planes: bool = False,
    refined_links: bool = False, contact_sites: list[str] | tuple[str, ...] | None = None,
    b_factor_sites: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Assess a selected run/checkpoint without creating or modifying artifacts.

    The current checkpoint is used unless an explicit ID or bookmark is given.
    The established checkpoint resolver verifies every available frozen checksum,
    including observations and phase data, before the assessor sees any inputs.
    An uninitialized run uses the existing validated, in-memory PostMR root.
    Optional readings cover selected-site planes, inter-residue bonds and
    per-atom nonbonded contacts at native preflight and after refinement.
    """
    if type(refined_planes) is not bool:
        raise ValueError("The refined plane option must be boolean")
    if type(refined_links) is not bool:
        raise ValueError("The refined link option must be boolean")
    if contact_sites is not None:
        from .refinement_contact_geometry import read_refined_contacts, validate_contact_sites
        validate_contact_sites(contact_sites)
    if b_factor_sites is not None:
        from .refinement_contact_geometry import validate_contact_sites
        validate_contact_sites(b_factor_sites)
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
    verified = None
    if refined_links:
        from .cif_numerical_replay import numerical_replay_scope
        with numerical_replay_scope():
            run, registry, verified = _read_registry_with_preparations(requested_run)
    else:
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

    outputs = selected.get("outputs", {})
    if (refined_planes or refined_links or contact_sites) and not isinstance(outputs, Mapping):
        raise CheckpointError("Malformed checkpoint output references")
    if refined_planes:
        receipt["refined_planes"] = None
        if "parallelity_execution" in outputs:
            from .refinement_parallelity import read_execution_plane_geometry
            receipt["refined_planes"] = read_execution_plane_geometry(
                run, outputs["parallelity_execution"], checkpoint=record.checkpoint_id,
                parent=record.parent, model=model, omit_each_member=True, compare_preflight=True,
            )

    tracked = [
        (report_path, report_ref),
        (model, model_ref),
        (observations, observations_ref),
        *zip(restraints, restraint_refs),
    ]
    if b_factor_sites:
        from .refinement_displacement import compare_pdb_displacements
        input_model = None
        parent_id = record.parent if selected.get("kind") == "refinement" else None
        if parent_id is not None:
            parent = resolve_checkpoint(registry, parent_id)
            parent_ref = parent["model"]
            if isinstance(parent_ref, Mapping) and isinstance(parent_ref.get("sha256"), str):
                parent_path = _ref_path(parent_ref, "refinement parent model", run)
                input_model = parent_path.read_bytes()
                tracked.append((parent_path, {"sha256": parent_ref["sha256"].casefold()}))
        values = compare_pdb_displacements(input_model, model.read_bytes(), b_factor_sites)
        if (values["selected_model_sha256"] != model_ref["sha256"] or
                (input_model is not None and values["input_model_sha256"] != parent_ref["sha256"].casefold())):
            raise CheckpointError("B factor readings differ from the recorded models")
        receipt["b_factors"] = dict(values, input_checkpoint=parent_id if input_model is not None else None,
                                    selected_checkpoint=record.checkpoint_id)
    if refined_links:
        from .campaigns import _canonical
        from .refinement_chemistry import _preparation_context
        from .refinement_link_geometry import read_prepared_link_geometry, summarize_round_links
        context = _preparation_context(run, registry, verified, selected)
        metrics = selected.get("metrics", {})
        recorded = isinstance(metrics, Mapping) and "inter_residue_bonds" in metrics
    if refined_links or contact_sites:
        from .refinement_link_geometry import preflight_link_inputs
        initial_files = preflight_link_inputs(run, selected)
        final_files = None
        final_ref = outputs.get("final_geometry")
        if final_ref is not None:
            if not isinstance(final_ref, Mapping) or not isinstance(final_ref.get("sha256"), str):
                raise CheckpointError("Final geometry needs its recorded checksum")
            if selected.get("kind") != "refinement":
                raise CheckpointError("Final geometry must belong to a refinement checkpoint")
            geo = _ref_path(final_ref, "final geometry", run)
            final_files = ((model, model_ref), (geo, final_ref))
        for stage, files in (("preflight", initial_files), ("refined", final_files)):
            if refined_links:
                receipt[stage + "_links"] = None
            if contact_sites:
                receipt[stage + "_contacts"] = None
            if files is None:
                continue
            (coords, coords_ref), (geo, geo_ref) = files
            observations_at_stage = {}
            if refined_links:
                observations_at_stage["links"] = read_prepared_link_geometry(context, coords, geo, allow_unassessed=recorded)
            if contact_sites:
                observations_at_stage["contacts"] = read_refined_contacts(coords, geo, contact_sites)
            for kind, observed in observations_at_stage.items():
                if (observed["model_sha256"] != coords_ref["sha256"].casefold()
                        or observed["geometry_sha256"] != geo_ref["sha256"].casefold()):
                    raise CheckpointError(f"{stage.capitalize()} {kind} differ from the frozen model or geometry")
                receipt[stage + "_" + kind] = observed
            tracked.append((geo, {"sha256": geo_ref["sha256"].casefold()}))
            if stage == "preflight":
                tracked.append((coords, {"sha256": coords_ref["sha256"].casefold()}))
    if refined_links:
        bond_review = False
        if recorded:
            if context is None:
                raise CheckpointError("Recorded bond summary has no checked preparation")
            current = summarize_round_links(context[1], receipt["preflight_links"], receipt["refined_links"])
            if _canonical(current) != _canonical(metrics["inter_residue_bonds"]):
                raise CheckpointError("Recorded bond summary differs from the native geometry evidence")
            bond_review = current["requires_review"]
        receipt["dictionary_status"] = receipt["status"]
        link_status = (receipt["refined_links"] or {}).get("status")
        initial_status = (receipt["preflight_links"] or {}).get("status")
        if receipt["status"] != "INVALID" and (bond_review or "REVIEW" in (link_status, initial_status)):
            receipt["status"] = "REVIEW"
        elif receipt["status"] == "PASS" and (link_status != "MATCH" or initial_status not in (None, "MATCH")):
            receipt["status"] = "UNASSESSED"
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
