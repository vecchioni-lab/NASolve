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


def _checked_registry(run, *, preparations=False):
    """Snapshot the report and registry around the existing validated read."""
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
    if preparations:
        from .cif_numerical_replay import numerical_replay_scope
        with numerical_replay_scope():
            run, registry, verified = _read_registry_with_preparations(requested_run)
    else:
        run, registry = read_registry(requested_run)
    _require_unchanged(report_path, report_ref)
    _require_registry_unchanged(existing_registry, registry_ref)
    return run, registry, verified, report_ref, registry_ref


def _final_geometry(run, selected):
    outputs = selected.get("outputs", {})
    if not isinstance(outputs, Mapping):
        raise CheckpointError("Malformed checkpoint output references")
    reference = outputs.get("final_geometry")
    if reference is None:
        return None
    if not isinstance(reference, Mapping) or not isinstance(reference.get("sha256"), str):
        raise CheckpointError("Final geometry needs its recorded checksum")
    if selected.get("kind") != "refinement":
        raise CheckpointError("Final geometry must belong to a refinement checkpoint")
    return _ref_path(reference, "final geometry", run), reference


def read_checkpoint_phosphate_image(run: Path, *, checkpoint: str, phosphate: str | None = None, o3: str | None = None,
                                   o3_image: str | None = None, nearest_image: bool = False,
                                   native_receipt: Path | None = None, registered=None, registration_checkpoint: str | None = None):
    """Inspect only the named checkpoint's model and its own optional final GEO."""
    from .cif_numerical_replay import numerical_replay_scope
    from .cif_phosphate_image import inspect_phosphate_image

    if not isinstance(checkpoint, str) or not checkpoint.strip():
        raise CheckpointError("Phosphate inspection needs an explicit checkpoint ID or bookmark")
    with numerical_replay_scope():
        run, registry, _, report_ref, registry_ref = _checked_registry(run)
        selected = resolve_checkpoint(registry, checkpoint)
    frozen_model = selected.get("model")
    if not isinstance(frozen_model, Mapping):
        raise CheckpointError("Selected checkpoint has no model reference")
    expected_model = frozen_model.get("sha256")
    if expected_model is not None and not isinstance(expected_model, str):
        raise CheckpointError("Invalid recorded checkpoint model checksum")
    model = _ref_path(frozen_model, "model", run)
    final_geometry = _final_geometry(run, selected)
    geo, geo_ref = final_geometry if final_geometry is not None else (None, None)
    if registration_checkpoint is None:
        result = inspect_phosphate_image(model, phosphate=phosphate, o3=o3, o3_image=o3_image, nearest_image=nearest_image,
                                         geometry=geo, native_receipt=native_receipt, registered=registered)
    else:
        from .checkpoint_candidate import _lineage
        from .cif_phosphate_continuation import inspect_inherited_continuation
        if registered is None or any(x is not None for x in (phosphate, o3, o3_image)) or nearest_image:
            raise CheckpointError("A registration checkpoint requires one declared continuation")
        ancestor = resolve_checkpoint(registry, registration_checkpoint)
        if ancestor["id"] not in _lineage(registry, selected):
            raise CheckpointError("Registration checkpoint must be the named model or one of its ancestors")
        source = _ref_path(ancestor["model"], "registration model", run)
        result = inspect_inherited_continuation(source, model, registered, geometry=geo, native_receipt=native_receipt)
        transfer = result["registered_continuation"]["frame_transfer"]
        recorded = ancestor["model"].get("sha256")
        if not isinstance(recorded, str) or transfer["source_model_sha256"] != recorded.lower():
            raise CheckpointError("Registration model differs from its frozen ancestor")
        transfer["source_checkpoint"] = ancestor["id"]
    model_ref = _reference(model, run)
    geometry_ref = _reference(geo, run) if geo is not None else None
    if result["model_sha256"] != model_ref["sha256"] or (expected_model is not None and model_ref["sha256"] != expected_model.casefold()):
        raise CheckpointError("Phosphate image reading differs from the frozen model")
    if geometry_ref is not None:
        observed = result["printed_geometry"]["geometry_sha256"]
        if observed != geometry_ref["sha256"] or observed != geo_ref["sha256"].casefold():
            raise CheckpointError("Phosphate image reading differs from the frozen geometry")
    _require_unchanged(run / "report.json", report_ref)
    _require_registry_unchanged(registry_path(run), registry_ref)
    result["checkpoint"] = dict(id=selected["id"], parent=selected.get("parent"), model=model_ref, geometry=geometry_ref)
    return result


def assess_run(
    run: Path, *, checkpoint: str | None = None, refined_planes: bool = False,
    refined_links: bool = False, contact_sites: list[str] | tuple[str, ...] | None = None,
    b_factor_sites: list[str] | tuple[str, ...] | None = None, bond_targets: bool = False,
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
    if type(bond_targets) is not bool:
        raise ValueError("The bond target option must be boolean")
    if contact_sites is not None:
        from .refinement_contact_geometry import read_refined_contacts, validate_contact_sites
        validate_contact_sites(contact_sites)
    if b_factor_sites is not None:
        from .refinement_contact_geometry import validate_contact_sites
        validate_contact_sites(b_factor_sites)
    run, registry, verified, report_ref, registry_ref = _checked_registry(run, preparations=refined_links)
    report_path = run / "report.json"
    existing_registry = registry_path(run)
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
    if (refined_planes or refined_links or contact_sites or bond_targets) and not isinstance(outputs, Mapping):
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
    if refined_links or contact_sites or bond_targets or refined_planes:
        from .refinement_link_geometry import preflight_link_inputs
        initial_files = preflight_link_inputs(run, selected)
        geometry = _final_geometry(run, selected)
        final_files = ((model, model_ref), geometry) if geometry is not None else None
        for stage, files in (("preflight", initial_files), ("refined", final_files)):
            if refined_links:
                receipt[stage + "_links"] = None
            if contact_sites:
                receipt[stage + "_contacts"] = None
            if bond_targets:
                receipt[stage + "_bond_targets"] = None
            if refined_planes:
                receipt[stage + "_printed_planes"] = None
            if files is None:
                continue
            (coords, coords_ref), (geo, geo_ref) = files
            observations_at_stage = {}
            if refined_links:
                observations_at_stage["links"] = read_prepared_link_geometry(context, coords, geo, allow_unassessed=recorded)
            if contact_sites:
                observations_at_stage["contacts"] = read_refined_contacts(coords, geo, contact_sites)
            if bond_targets:
                from .refinement_component_bonds import read_component_bond_targets
                observations_at_stage["bond_targets"] = read_component_bond_targets(coords, geo, receipt["components"])
            if refined_planes:
                from .refinement_component_planes import read_component_planes
                observations_at_stage["printed_planes"] = read_component_planes(coords, geo, receipt["components"])
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
    if bond_targets:
        from .refinement_component_bonds import apply_bond_target_review
        apply_bond_target_review(receipt)
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
