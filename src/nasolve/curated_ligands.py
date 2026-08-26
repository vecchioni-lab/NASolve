"""Curated overrides for residues Phenix cannot interpret reliably.

These entries are deliberately small and explicit.  NASolve does not run
eLBOW for every residue: a reviewed dictionary is bundled once and copied
into each run that needs it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CuratedLigand:
    code: str
    dictionary_filename: str
    accepted_model_labels: tuple[str, ...]
    narestraints_label: str
    description: str


CURATED_LIGANDS: dict[str, CuratedLigand] = {
    "8RO": CuratedLigand(
        code="8RO",
        dictionary_filename="8RO.cif",
        accepted_model_labels=("8RO", "DE"),
        narestraints_label="DE",
        description="4-thiothymidine; curated local geometry replaces problematic CCD interpretation",
    ),
}

CURATED_LIGAND_CODES = frozenset(CURATED_LIGANDS)


def ligand_data_directory(data_root: Path | None = None) -> Path:
    if data_root is not None:
        return Path(data_root) / "ligands"
    return Path(__file__).resolve().parent / "data" / "ligands"


def curated_dictionary(code: str, data_root: Path | None = None) -> Path:
    try:
        ligand = CURATED_LIGANDS[code]
    except KeyError as exc:
        raise KeyError(f"No curated NASolve ligand is registered for {code}") from exc
    path = ligand_data_directory(data_root) / ligand.dictionary_filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Curated dictionary for {code} is missing: {path}"
        )
    return path


__all__ = [
    "CURATED_LIGAND_CODES",
    "CURATED_LIGANDS",
    "CuratedLigand",
    "curated_dictionary",
    "ligand_data_directory",
]
