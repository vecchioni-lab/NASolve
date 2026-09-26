"""Read-only inventory of dataset-local MR model candidates.

This module discovers and assesses candidate PDB files without selecting,
ranking, transforming, or launching molecular replacement. Existing AutoMR
model-resolution behavior remains unchanged until a later reviewed integration.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from .model_assessment import ModelAssessmentError, inspect_pdb


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
                "diagnostic": str(exc),
                "assessment": None,
            })
            continue

        valid_count += 1
        candidates.append({
            "selector": selector,
            "status": "VALID",
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

    return {
        "schema_version": 1,
        "kind": "dataset-pdb-candidate-inventory",
        "dataset": str(root),
        "scope": "top-level-pdb-files-only",
        "candidate_count": len(candidates),
        "valid_candidate_count": valid_count,
        "invalid_candidate_count": invalid_count,
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


__all__ = [
    "ModelCandidateInventoryError",
    "inventory_dataset_pdb_candidates",
]
