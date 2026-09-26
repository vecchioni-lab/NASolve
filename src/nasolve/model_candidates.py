"""Read-only inventory of dataset-local MR model candidates.

This module discovers and assesses candidate PDB files without selecting,
ranking, transforming, or launching molecular replacement. Existing AutoMR
model-resolution behavior remains unchanged until a later reviewed integration.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from hashlib import sha256
from pathlib import Path

from .construct_registration import (
    ConstructRegistrationError,
    scout_simple_registration,
)
from .model_assessment import ModelAssessmentError, file_sha256, inspect_pdb


class ModelCandidateInventoryError(RuntimeError):
    """Raised when a dataset candidate inventory cannot be constructed safely."""


def inventory_dataset_pdb_candidates(
    dataset: Path,
    *,
    polymer_ligand_codes: Collection[str] | None = None,
) -> dict[str, object]:
    """Describe every top-level PDB candidate in one dataset directory.

    Invalid PDBs remain visible as rejected candidates with diagnostics so a
    multi-model workflow can explain why they were not eligible. Nested PDBs
    are intentionally ignored in this first slice to match current dataset
    discovery semantics and avoid silently broadening search scope.
    """
    root = Path(dataset).expanduser().resolve()
    if not root.is_dir():
        raise ModelCandidateInventoryError(
            f"Dataset directory does not exist: {root}"
        )

    paths = sorted(
        path.resolve()
        for path in root.glob("*.pdb")
        if path.is_file()
    )
    candidates: list[dict[str, object]] = []
    valid_count = 0
    invalid_count = 0

    for path in paths:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ModelCandidateInventoryError(
                "Discovered PDB escaped the dataset directory"
            ) from exc

        selector = path.relative_to(root).as_posix()
        file_identity = {
            "sha256": file_sha256(path),
            "byte_size": path.stat().st_size,
        }
        try:
            assessment = inspect_pdb(
                path,
                polymer_ligand_codes=polymer_ligand_codes,
            )
        except ModelAssessmentError as exc:
            invalid_count += 1
            candidates.append({
                "selector": selector,
                "status": "INVALID",
                "file": file_identity,
                "diagnostic": str(exc),
                "assessment": None,
            })
            continue

        valid_count += 1
        candidates.append({
            "selector": selector,
            "status": "VALID",
            "file": file_identity,
            "diagnostic": None,
            "assessment": {
                "sha256": assessment.sha256,
                "byte_size": assessment.byte_size,
                "polymer_residue_count": assessment.polymer_residue_count,
                "heteroatom_count": assessment.heteroatom_count,
                "chains": [
                    {
                        "chain": chain,
                        "residue_count": len(residue_ids),
                        "residue_ids": list(residue_ids),
                    }
                    for chain, residue_ids
                    in assessment.polymer_residue_ids_by_chain.items()
                ],
                "duplicate_atom_identities": assessment.duplicate_atom_identities,
                "warnings": list(assessment.warnings),
            },
        })

    fingerprint_payload = [
        {
            "selector": row["selector"],
            "status": row["status"],
            "sha256": row["file"]["sha256"],
            "byte_size": row["file"]["byte_size"],
        }
        for row in candidates
    ]
    candidate_set_sha256 = sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": 1,
        "kind": "dataset-pdb-candidate-inventory",
        "dataset": str(root),
        "scope": "top-level-pdb-files-only",
        "candidate_count": len(candidates),
        "valid_candidate_count": valid_count,
        "invalid_candidate_count": invalid_count,
        "candidate_set_sha256": candidate_set_sha256,
        "candidates": candidates,
        "selection": None,
        "semantics": {
            "descriptive_only": True,
            "filename_establishes_construct_identity": False,
            "automatic_selection_authorized": False,
            "mr_attempt_authorized": False,
            "nested_pdbs_discovered": False,
        },
    }


def scout_dataset_pdb_candidates(
    dataset: Path,
    target: dict[str, object],
    *,
    polymer_ligand_codes: Collection[str] | None = None,
) -> dict[str, object]:
    """Run conservative Registration Scout on every valid top-level PDB.

    This remains descriptive only. It does not select a candidate, authorize an
    MR attempt, transform coordinates, or change current AutoMR ambiguity rules.
    """
    inventory = inventory_dataset_pdb_candidates(
        dataset,
        polymer_ligand_codes=polymer_ligand_codes,
    )
    root = Path(dataset).expanduser().resolve()
    results: list[dict[str, object]] = []
    registered = ambiguous = unresolved = invalid = 0

    for candidate in inventory["candidates"]:
        selector = candidate["selector"]
        if candidate["status"] != "VALID":
            invalid += 1
            results.append({
                "selector": selector,
                "status": "INVALID",
                "diagnostic": candidate["diagnostic"],
                "registration_scout": None,
            })
            continue

        model_path = (root / selector).resolve()
        try:
            model_path.relative_to(root)
        except ValueError as exc:
            raise ModelCandidateInventoryError(
                "Candidate selector escaped the dataset directory"
            ) from exc
        try:
            assessment = inspect_pdb(
                model_path,
                polymer_ligand_codes=polymer_ligand_codes,
            )
            scout = scout_simple_registration(assessment, target)
        except (ModelAssessmentError, ConstructRegistrationError) as exc:
            raise ModelCandidateInventoryError(
                f"Could not registration-scout candidate {selector}: {exc}"
            ) from exc

        status = scout["status"]
        if status == "REGISTERED":
            registered += 1
        elif status == "AMBIGUOUS":
            ambiguous += 1
        elif status == "UNRESOLVED":
            unresolved += 1
        else:
            raise ModelCandidateInventoryError(
                f"Unexpected registration-scout status for {selector}: {status}"
            )
        results.append({
            "selector": selector,
            "status": "VALID",
            "diagnostic": None,
            "registration_scout": scout,
        })

    return {
        "schema_version": 1,
        "kind": "dataset-pdb-registration-scout",
        "dataset": inventory["dataset"],
        "scope": inventory["scope"],
        "candidate_count": inventory["candidate_count"],
        "valid_candidate_count": inventory["valid_candidate_count"],
        "invalid_candidate_count": inventory["invalid_candidate_count"],
        "registered_candidate_count": registered,
        "ambiguous_candidate_count": ambiguous,
        "unresolved_candidate_count": unresolved,
        "candidates": results,
        "selection": None,
        "semantics": {
            "descriptive_only": True,
            "registration_status_is_not_mr_quality": True,
            "design_evidence_is_not_a_selection_score": True,
            "automatic_selection_authorized": False,
            "mr_attempt_authorized": False,
        },
    }


__all__ = [
    "ModelCandidateInventoryError",
    "inventory_dataset_pdb_candidates",
    "scout_dataset_pdb_candidates",
]
