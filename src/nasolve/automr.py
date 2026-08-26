"""AutoMR preflight orchestration.

This module intentionally does not run Phaser yet.  It freezes and validates
the inputs that the Phaser execution layer will consume next.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Collection, Mapping

from .automr_input import (
    AutoMRInputError,
    ResolvedAutoMRInput,
    format_intent,
    read_intent,
    resolve_automr_input,
)
from .model_assessment import ModelAssessment, ModelAssessmentError, copy_preserving_model, inspect_pdb
from .symmetry import StandardSymmetryAssessment, SymmetryError, assess_standard_symmetry


@dataclass(frozen=True)
class AutoMRPreflightResult:
    status: str
    message: str
    run_directory: Path
    generated_config: bool
    report_path: Path


def _next_run_directory(dataset: Path) -> Path:
    parent = dataset / "AutoMR"
    parent.mkdir(exist_ok=True)
    for number in range(1, 10000):
        candidate = parent / f"run_{number:03d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise AutoMRInputError(f"Could not allocate another run directory beneath {parent}")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _post_mr_plan(resolved: ResolvedAutoMRInput) -> dict[str, object]:
    pair = None
    if resolved.pair:
        model_pair = None
        if resolved.model_pair:
            model_pair = {
                "tokens": [resolved.model_pair[0].token, resolved.model_pair[1].token],
                "ligand_codes": [
                    resolved.model_pair[0].ligand_code,
                    resolved.model_pair[1].ligand_code,
                ],
            }
        pair = {
            "requested": resolved.pair_text,
            "ligand_codes": [resolved.pair[0].ligand_code, resolved.pair[1].ligand_code],
            "model_pair": model_pair,
            "exact_model_match": resolved.exact_pair_model,
            "mutation_required": not bool(resolved.exact_pair_model),
            "ordered_roles": ["first standard site", "second standard site"],
            "site_assignment": "pending standard-frame site manifest",
        }
    return {
        "application_order": ["sequences", "standard_pair", "explicit_mutations"],
        "sequences": dict(resolved.sequences),
        "standard_pair": pair,
        "mutations": {
            site: {"requested": ligand.token, "ligand_code": ligand.ligand_code}
            for site, ligand in resolved.mutations.items()
        },
        "execution": "not performed by AutoMR preflight",
    }


def _validate_edit_targets(
    resolved: ResolvedAutoMRInput,
    assessment: ModelAssessment,
) -> None:
    """Require sequence lengths and explicit mutation sites to match the model."""
    for chain, sequence in resolved.sequences.items():
        model_length = assessment.polymer_residues_by_chain.get(chain)
        if model_length is None:
            available = ", ".join(assessment.chains)
            raise AutoMRInputError(
                f"Sequence chain {chain!r} is absent from the MR model; available chains: {available}"
            )
        if len(sequence) != model_length:
            raise AutoMRInputError(
                f"Sequence for chain {chain} has length {len(sequence)}, "
                f"but the MR model contains {model_length} polymer residues"
            )
    for site in resolved.mutations:
        chain, residue = (part.strip() for part in site.split(":", 1))
        if residue not in assessment.polymer_residue_ids_by_chain.get(chain, []):
            raise AutoMRInputError(f"Mutation target {site} does not exist in the MR model")


def _log_text(
    resolved: ResolvedAutoMRInput,
    assessment: ModelAssessment,
    symmetry: StandardSymmetryAssessment | None,
    status: str,
    config_path: Path,
    generated: bool,
) -> str:
    pair_line = "none"
    if resolved.pair:
        pair_line = (
            f"{resolved.pair_text} -> "
            f"{resolved.pair[0].ligand_code}:{resolved.pair[1].ligand_code}"
        )
    model_pair_line = "none"
    if resolved.model_pair:
        model_pair_line = (
            f"{resolved.model_pair[0].token}:{resolved.model_pair[1].token} -> "
            f"{resolved.model_pair[0].ligand_code}:{resolved.model_pair[1].ligand_code}"
        )
    mutation_lines = [
        f"  {site}: {ligand.token} -> {ligand.ligand_code}"
        for site, ligand in resolved.mutations.items()
    ] or ["  none"]
    warning_lines = [f"  {warning}" for warning in assessment.warnings] or ["  none"]
    catalogue_warning_lines = [
        f"  {warning}" for warning in resolved.catalogue_warnings
    ] or ["  none"]
    space_group = symmetry.evidence.mtz_symbol if symmetry else "not gated (nonstandard mode)"
    copies = str(symmetry.mr_copies) if symmetry else "not set by standard-frame rule"
    symmetry_warning = symmetry.red_flag if symmetry and symmetry.red_flag else "none"
    return "\n".join([
        "NASolve AutoMR preflight",
        f"Status: {status}",
        "Phaser executed: no",
        f"Dataset: {resolved.dataset.root}",
        f"Input configuration: {config_path} ({'generated' if generated else 'existing'})",
        f"Mode: {resolved.mode}",
        f"Frame: {resolved.frame.name if resolved.frame else 'none'}",
        f"Authoritative space group: {space_group}",
        f"Planned MR copies: {copies}",
        f"Symmetry red flag: {symmetry_warning}",
        f"Pair: {pair_line}",
        f"Model pair: {model_pair_line}",
        f"Exact pair model: {resolved.exact_pair_model}",
        f"MR model: {resolved.model}",
        f"Model source: {resolved.model_source}",
        "Catalogue warnings:",
        *catalogue_warning_lines,
        f"Model SHA-256: {assessment.sha256}",
        "Polymer residues (including modified HETATM nucleotides): "
        f"{assessment.polymer_residue_count}",
        f"Modified polymer residues from HETATM: {assessment.modified_polymer_residue_count}",
        f"HETATM atom records preserved: {assessment.heteroatom_count}",
        "Explicit mutations:",
        *mutation_lines,
        "Assessment warnings:",
        *warning_lines,
        "",
        "Next layer: use this frozen run input to prepare and execute Phenix Phaser.",
        "",
    ])


def prepare_automr(
    dataset: Path,
    config_path: Path | None = None,
    frame_override: str | None = None,
    pair_override: str | None = None,
    frames_dir: Path | None = None,
    allow_p1_standard: bool = False,
    mtz_dump_executable: Path | None = None,
    phenix_environment: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
    valid_ligand_codes: Collection[str] | None = None,
) -> AutoMRPreflightResult:
    """Validate and freeze one AutoMR request without executing Phaser."""
    root = dataset.expanduser().resolve()
    selected_config = config_path.expanduser().resolve() if config_path else root / "nasolve.txt"
    existing_config = selected_config if selected_config.is_file() else None
    intent = read_intent(existing_config)
    resolved = resolve_automr_input(
        root,
        intent,
        frame_override=frame_override,
        pair_override=pair_override,
        frames_dir=frames_dir,
        allow_p1_standard=allow_p1_standard,
        environ=environ,
        valid_ligand_codes=valid_ligand_codes,
    )
    symmetry: StandardSymmetryAssessment | None = None
    if resolved.mode == "standard":
        if mtz_dump_executable is None:
            raise AutoMRInputError(
                "Standard mode requires phenix.mtz.dump for the authoritative MTZ symmetry check"
            )
        try:
            symmetry = assess_standard_symmetry(
                resolved.dataset.reflections,
                resolved.dataset.metadata,
                resolved.dataset.summary,
                mtz_dump_executable,
                environment=phenix_environment,
                allow_p1_standard=resolved.allow_p1_standard,
            )
        except SymmetryError as exc:
            raise AutoMRInputError(str(exc)) from exc
    assessment = inspect_pdb(
        resolved.model, polymer_ligand_codes=valid_ligand_codes
    )
    _validate_edit_targets(resolved, assessment)
    effective_text = format_intent(resolved)

    generated = existing_config is None
    if generated:
        if config_path is not None and selected_config.parent != root:
            raise AutoMRInputError(
                "A missing --config path is not created outside the dataset; omit --config to generate nasolve.txt"
            )
        selected_config.write_text(effective_text, encoding="utf-8")

    run_dir = _next_run_directory(root)
    model_dir = run_dir / "Model"
    model_dir.mkdir()
    copied_model = model_dir / "input_model.pdb"
    copy_preserving_model(resolved.model, copied_model, assessment)
    _write_json(model_dir / "assessment.json", assessment.to_dict())
    (run_dir / "nasolve.input.txt").write_text(effective_text, encoding="utf-8")

    pair_needs_edit = bool(resolved.pair and not resolved.exact_pair_model)
    needs_edit = bool(pair_needs_edit or resolved.sequences or resolved.mutations)
    if symmetry and symmetry.red_flag:
        status = "READY_WITH_RED_FLAG"
        message = symmetry.red_flag
    elif needs_edit:
        status = "READY_POST_MR_MUTATION"
        message = "AutoMR inputs are frozen; a post-MR sequence/mutation plan is recorded"
    else:
        status = "READY"
        message = "AutoMR inputs are frozen and ready for the Phaser execution layer"
    report = {
        "schema_version": 1,
        "workflow": "automr",
        "stage": "preflight",
        "status": status,
        "message": message,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(root),
        "configuration": {
            "source": str(selected_config),
            "generated": generated,
            "effective_snapshot": str(run_dir / "nasolve.input.txt"),
        },
        "inputs": {
            "reflections": str(resolved.dataset.reflections),
            "metadata": str(resolved.dataset.metadata),
            "summary": str(resolved.dataset.summary),
            "model": str(resolved.model),
            "model_source": resolved.model_source,
            "catalogue_warnings": list(resolved.catalogue_warnings),
        },
        "mode": resolved.mode,
        "frame": asdict(resolved.frame) if resolved.frame else None,
        "symmetry": symmetry.to_dict() if symmetry else {
            "gate": "not applied in nonstandard mode"
        },
        "model_assessment": assessment.to_dict(),
        "post_mr_plan": _post_mr_plan(resolved),
        "execution": {"phaser_ran": False},
    }
    report_path = run_dir / "report.json"
    _write_json(report_path, report)
    (run_dir / "automr.log").write_text(
        _log_text(resolved, assessment, symmetry, status, selected_config, generated),
        encoding="utf-8",
    )
    return AutoMRPreflightResult(status, message, run_dir, generated, report_path)


__all__ = [
    "AutoMRInputError",
    "ModelAssessmentError",
    "AutoMRPreflightResult",
    "prepare_automr",
]
