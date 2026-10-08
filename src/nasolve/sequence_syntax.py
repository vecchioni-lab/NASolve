"""One-residue-per-token annotated DNA/RNA sequence syntax.

Ordinary A/C/G/T/U letters stay backwards compatible. A parenthesized literal
NARestraints/curated ligand code occupies one site: A(5CM)G(DZ). A recognized
code is target intent, not proof that its structure can be emitted as PDB or
that a dictionary/construction route is usable. Do not interpret parentheses
as aliases, or silently truncate long CCD identifiers.
"""
from __future__ import annotations

import re
from typing import Collection


class SequenceSyntaxError(ValueError):
    """Malformed sequence or unregistered explicit ligand code."""


CANONICAL_CODES = {
    "DNA": {"A": "DA", "C": "DC", "G": "DG", "T": "DT"},
    "RNA": {"A": "A", "C": "C", "G": "G", "U": "U"},
}
_LETTERS = frozenset("ACGTU")
_LIGAND_CODE = re.compile(r"[A-Z0-9]{1,5}\Z")


def parse_sequence_tokens(
    value: object,
    *,
    polymer: str | None = None,
    context: str = "Sequence",
    valid_ligand_codes: Collection[str] | None = None,
) -> tuple[str, ...]:
    """Return normalized tokens; ``(CCD)`` is exactly one residue.

    Library validation happens only for explicit parenthetical tokens; ordinary
    sequences remain usable without loading the ligand registry. A supplied
    ``valid_ligand_codes`` is used in tests/standalone resolvers alongside the
    curated NASolve codes; it does not authorize unregistered chemistry in a
    normal user run. All model/geometry/dictionary decisions stay downstream.
    """
    if not isinstance(value, str):
        raise SequenceSyntaxError(f"{context} must be sequence text")
    if polymer is not None and polymer not in CANONICAL_CODES:
        raise SequenceSyntaxError(f"{context}: unsupported polymer {polymer!r}")
    text = "".join(value.split()).upper()
    if not text:
        raise SequenceSyntaxError(f"{context} cannot be empty")
    tokens: list[str] = []
    allowed: frozenset[str] | None = None
    i = 0
    while i < len(text):
        char = text[i]
        if char == "(":
            close = text.find(")", i + 1)
            if close == -1:
                raise SequenceSyntaxError(f"{context}: unclosed ligand token at column {i + 1}")
            code = text[i + 1:close]
            if _LIGAND_CODE.fullmatch(code) is None:
                raise SequenceSyntaxError(
                    f"{context}: invalid literal ligand code {code!r} at column {i + 1}; "
                    "use (CODE) with 1-5 letters/digits"
                )
            if allowed is None:
                if valid_ligand_codes is None:
                    try:
                        from .residue_aliases import known_ligand_codes
                        allowed = known_ligand_codes()
                    except ValueError as exc:
                        raise SequenceSyntaxError(f"{context}: {exc}") from exc
                else:
                    from .curated_ligands import CURATED_LIGAND_CODES, PDB_DEPOSITION_ALIASES
                    allowed = (frozenset(valid_ligand_codes) | CURATED_LIGAND_CODES
                               | frozenset(PDB_DEPOSITION_ALIASES))
            if code not in allowed:
                raise SequenceSyntaxError(
                    f"{context}: unknown literal ligand code ({code}); use a code "
                    "from the NARestraints/curated ligand library, not a bare alias"
                )
            tokens.append(f"({code})")
            i = close + 1
        elif char in _LETTERS:
            if polymer is not None and char not in CANONICAL_CODES[polymer]:
                raise SequenceSyntaxError(
                    f"{context}: unsupported {polymer} sequence symbol {char!r} "
                    f"at column {i + 1}"
                )
            tokens.append(char)
            i += 1
        else:
            raise SequenceSyntaxError(
                f"{context}: unsupported sequence character {char!r} "
                f"at column {i + 1}; use A/C/G/T/U or (LIGAND_CODE)"
            )
    return tuple(tokens)


def canonical_sequence(value: object, **kwargs: object) -> str:
    """Canonical human-readable sequence, without losing CCD token boundaries."""
    return "".join(parse_sequence_tokens(value, **kwargs))


def sequence_length(value: object, **kwargs: object) -> int:
    """Biological residue count rather than source-character count."""
    return len(parse_sequence_tokens(value, **kwargs))


def sequence_residue_codes(
    value: object,
    polymer: str,
    *,
    context: str = "Sequence",
    valid_ligand_codes: Collection[str] | None = None,
) -> tuple[str, ...]:
    """Resolve each position to the actual requested component code.

    Literal parenthetical tokens bypass nucleotide aliases: ``(A)`` requests
    component A, whereas bare A is DNA DA or RNA A. Site-specific mutation and
    P2 preparation policies may subsequently override/normalize these targets.
    """
    tokens = parse_sequence_tokens(
        value, polymer=polymer, context=context,
        valid_ligand_codes=valid_ligand_codes,
    )
    return tuple(
        token[1:-1] if token.startswith("(") else CANONICAL_CODES[polymer][token]
        for token in tokens
    )
