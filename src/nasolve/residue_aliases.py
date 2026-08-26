"""User-facing residue aliases for AutoMR input files.

Aliases are intentionally explicit and case-sensitive.  In particular, ``A``
and ``rA`` describe different residues.  Tokens not present in the alias table
are treated as literal ligand codes and checked against NARestraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Collection


RESIDUE_ALIASES: dict[str, str] = {
    "D": "1AP",
    "T": "DT",
    "C": "DC",
    "G": "DG",
    "A": "DA",
    "rA": "A",
    "rC": "C",
    "rU": "U",
    "rG": "G",
    "U": "DU",
    "F": "DF",
    "E": "DE",
    "Q": "S6G",
    "B": "IGU",
    "rB": "IG",
    "P": "DP",
    "rP": "50L",
    "Z": "DZ",
    "rZ": "50N",
    "I": "DI",
    "rI": "I",
    "X": "DX",
    "K": "CGY",
}

# Reserved for aliases that acquire more than one scientifically valid default.
AMBIGUOUS_ALIASES: dict[str, tuple[str, ...]] = {}


class LigandCodeError(ValueError):
    """Raised when a residue token cannot be resolved safely."""


@dataclass(frozen=True)
class ResolvedLigand:
    token: str
    ligand_code: str
    used_alias: bool


@lru_cache(maxsize=1)
def known_ligand_codes() -> frozenset[str]:
    """Load the authoritative ligand codes bundled with NARestraints."""
    try:
        from restraints.residue_library import load_residue_records
    except ImportError as exc:  # pragma: no cover - installation error path
        raise LigandCodeError(
            "NARestraints is not installed; ligand codes cannot be validated"
        ) from exc
    try:
        records = load_residue_records()
    except Exception as exc:  # pragma: no cover - surfaced with useful context
        raise LigandCodeError(f"Could not load the NARestraints residue library: {exc}") from exc
    return frozenset(str(record["Ligand code"]) for record in records)


def resolve_ligand(
    token: str,
    valid_codes: Collection[str] | None = None,
) -> ResolvedLigand:
    """Resolve one alias or literal code and validate the resulting ligand."""
    cleaned = token.strip()
    if not cleaned:
        raise LigandCodeError("Residue token cannot be empty")
    if cleaned in AMBIGUOUS_ALIASES:
        choices = " or ".join(AMBIGUOUS_ALIASES[cleaned])
        raise LigandCodeError(
            f"Alias {cleaned!r} is ambiguous; specify the ligand code {choices} explicitly"
        )
    used_alias = cleaned in RESIDUE_ALIASES
    code = RESIDUE_ALIASES.get(cleaned, cleaned)
    authoritative = known_ligand_codes() if valid_codes is None else frozenset(valid_codes)
    if code not in authoritative:
        if used_alias:
            raise LigandCodeError(
                f"Alias registry error: {cleaned!r} resolves to unknown ligand code {code!r}"
            )
        raise LigandCodeError(
            f"Unknown ligand code {cleaned!r}; use a configured alias or a code in NARestraints"
        )
    return ResolvedLigand(cleaned, code, used_alias)


def resolve_pair(
    value: str,
    valid_codes: Collection[str] | None = None,
) -> tuple[ResolvedLigand, ResolvedLigand]:
    """Resolve an ordered ``first:second`` standard-frame pair."""
    parts = value.split(":")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise LigandCodeError("Pair must contain exactly two residue tokens: FIRST:SECOND")
    return (
        resolve_ligand(parts[0], valid_codes),
        resolve_ligand(parts[1], valid_codes),
    )
