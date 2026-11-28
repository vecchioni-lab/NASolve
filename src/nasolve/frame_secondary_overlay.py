"""Run-local W-frame Saenger replacement for reviewed modified-base pairs.

The packaged W secondary-structure template gives canonical Saenger classes to
fixed sites. A sequence-family mutation can make such a class invalid for
Phenix. Replace only affected template blocks with explicit NARestraints atom-
resolved pair geometry in the *run-local* Std_padd input. Preserve all
unaffected blocks, the source template, the frozen plan and old runs.

Pair identity follows the actual prepared PDB and NARestraints workbook. No
automatic use of force=, blanket removal of secondary structure or guessed
chemistry is permitted.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Mapping

from .model_assessment import file_sha256


class FrameSecondaryOverlayError(ValueError):
    """A legacy frame Saenger block could not be replaced safely."""


_CANONICAL = frozenset({
    "DA", "DC", "DG", "DT", "DU", "A", "C", "G", "U",
    "0DA", "0DC", "0DG", "0DT", "0A", "0C", "0G", "0U",
})
_PAIR_BLOCK = re.compile(r"(?m)^[ \t]*base_pair\s*\{([^{}]*)\}")
_PAIR_START = re.compile(r"\bbase_pair\s*\{")
_SAENGER = re.compile(r"\bsaenger_class\s*=\s*(\d+)\b")


def _site(block: str, key: str) -> str:
    match = re.search(
        rf"\b{key}\s*=\s*chain\s+['\"]?([^\s'\"]+)['\"]?"
        rf"\s+and\s+resid\s+([\w]+)\b",
        block,
    )
    if match is None:
        raise FrameSecondaryOverlayError(
            f"Frame secondary-structure block has no reviewable {key} site"
        )
    chain, resid = match.groups()
    if not re.fullmatch(r"[A-Za-z0-9]", chain) or not re.fullmatch(
        r"[1-9]\d*[A-Za-z]?", resid
    ):
        raise FrameSecondaryOverlayError(
            f"Frame secondary-structure site is not a supported PDB site: {chain}:{resid}"
        )
    return f"{chain}:{resid}"


def _codes_from_pdb(path: Path) -> dict[str, str]:
    codes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 27:
            continue
        site = f"{line[21:22].strip()}:{line[22:26].strip()}{line[26:27].strip()}"
        code = line[17:20].strip()
        previous = codes.setdefault(site, code)
        if not code or previous != code:
            raise FrameSecondaryOverlayError(
                f"Prepared model has ambiguous residue identity at {site}"
            )
    return codes


def _mapped_residue(model: object, site: str) -> object:
    chain, residue_number = site.split(":", 1)
    try:
        chain_obj = model[chain]  # type: ignore[index]
    except (KeyError, IndexError) as exc:
        raise FrameSecondaryOverlayError(f"NARestraints model lacks chain {chain}") from exc
    matches = [
        residue for residue in chain_obj
        if f"{residue.id[1]}{residue.id[2].strip()}" == residue_number
    ]
    if len(matches) != 1:
        raise FrameSecondaryOverlayError(
            f"NARestraints model has {len(matches)} matches for pair site {site}"
        )
    return matches[0]


def prepare_frame_modified_secondary_overlay(
    prepared_model: Path,
    compatibility_model: Path,
    source_secondary: Path,
    run_secondary: Path,
    run_pair_file: Path,
    *,
    patch_records: Callable[[list[dict[str, object]], set[str]], tuple[list[dict[str, object]], list[dict[str, str]]]],
) -> dict[str, object]:
    """Translate modified-site Saenger blocks to reviewed explicit pair geometry.

    Caller copies the three-pair frame input to run_pair_file first; it is
    augmented *only* if needed. The standard NARestraints builder subsequently
    emits one combined PHIL from that file, avoiding duplicate .phil scopes or
    implicit stacking overcount. This function validates everything before
    writing either run-local file, and returns audit data for PostMR/report.json.
    """
    from restraints.base_pairs import read_base_pair_file

    text = source_secondary.read_text(encoding="utf-8")
    blocks = list(_PAIR_BLOCK.finditer(text))
    if not blocks or len(blocks) != len(_PAIR_START.findall(text)):
        raise FrameSecondaryOverlayError(
            "Frame secondary-structure template contains an unparsed base_pair block"
        )

    prepared_codes = _codes_from_pdb(prepared_model)
    modified_sites = {
        site for site, code in prepared_codes.items() if code not in _CANONICAL
    }
    existing_stretches = read_base_pair_file(run_pair_file)
    existing_keys = {
        frozenset((
            f"{pair.base1.chain}:{pair.base1.resid}",
            f"{pair.base2.chain}:{pair.base2.resid}",
        ))
        for stretch in existing_stretches
        for pair in stretch.pairs()
    }

    affected: list[tuple[object, str, str, int]] = []
    seen: set[frozenset[str]] = set()
    for match in blocks:
        body = match.group(1)
        a = _site(body, "base1")
        b = _site(body, "base2")
        key = frozenset((a, b))
        if len(key) != 2 or key in seen:
            raise FrameSecondaryOverlayError(
                f"Duplicate or self-paired W secondary pair {a}/{b}"
            )
        seen.add(key)
        cls = _SAENGER.findall(body)
        if len(cls) != 1:
            raise FrameSecondaryOverlayError(
                f"Frame secondary pair {a}/{b} lacks exactly one Saenger class"
            )
        if a in modified_sites or b in modified_sites:
            affected.append((match, a, b, int(cls[0])))

    if not affected:
        run_secondary.write_text(text, encoding="utf-8")
        return {
            "schema_version": 1,
            "mode": "no-modified-frame-overlap",
            "source_sha256": file_sha256(source_secondary),
            "run_secondary_sha256": file_sha256(run_secondary),
            "base_pair_count": len(blocks),
            "retained_saenger_count": len(blocks),
            "replaced_saenger_count": 0,
            "explicit_new_pair_count": 0,
            "replacements": [],
        }

    # Construct the atom-role evidence *before* removing a single Saenger block.
    # Fail closed if an analogue or partner has no supported chemical recipe.
    from Bio.PDB import PDBParser
    from restraints import builder
    from restraints.phenix import generate_pair_restraints
    from restraints.recipe_library import recipe_for
    from restraints.residue_library import load_residue_records

    required_codes = set(_codes_from_pdb(compatibility_model).values())
    records, corrections = patch_records(load_residue_records(), required_codes)
    model = next(
        PDBParser(QUIET=True).get_structure(
            "frame-secondary-overlays", str(compatibility_model)
        ).get_models()
    )

    replacements: list[dict[str, object]] = []
    additions: list[tuple[str, str]] = []
    for _, a, b, old_class in affected:
        try:
            first = builder.pair_residue_from_pdb(
                records, _mapped_residue(model, a)
            )
            second = builder.pair_residue_from_pdb(
                records, _mapped_residue(model, b)
            )
            recipe = recipe_for(first.base_class, second.base_class)
            if recipe is None:
                raise ValueError(
                    f"No reviewed NARestraints recipe for {first.base_class}:{second.base_class}"
                )
            geometry = generate_pair_restraints(first, second)
            reverse = generate_pair_restraints(second, first)
        except (ValueError, KeyError, IndexError) as exc:
            raise FrameSecondaryOverlayError(
                f"Cannot replace Saenger {old_class} for {a}/{b}: {exc}"
            ) from exc
        if not geometry or geometry != reverse:
            raise FrameSecondaryOverlayError(
                f"NARestraints returned missing/order-dependent geometry for {a}/{b}"
            )
        bond_count = geometry.count("    bond {")
        if (
            bond_count < 1
            or "parallelity {" not in geometry
            or "planarity {" not in geometry
        ):
            raise FrameSecondaryOverlayError(
                f"NARestraints produced incomplete reviewed geometry for {a}/{b}"
            )

        key = frozenset((a, b))
        inherited = key in existing_keys
        replacements.append({
            "sites": [a, b],
            "prepared_codes": [prepared_codes[a], prepared_codes[b]],
            "base_classes": [first.base_class, second.base_class],
            "old_saenger_class": old_class,
            "narestraints_recipe": recipe.name,
            "explicit_bond_count": bond_count,
            "source": (
                "existing-frame-pair" if inherited
                else "appended-frame-pair"
            ),
        })
        if not inherited:
            additions.append((a, b))

    # Render the output entirely from immutable source text, without touching
    # the packaged frame template or preserving invalid Saenger classifications.
    pieces: list[str] = []
    offset = 0
    removed_spans = {(match.start(), match.end()) for match, _, _, _ in affected}
    for match in blocks:
        pieces.append(text[offset:match.start()])
        if (match.start(), match.end()) not in removed_spans:
            pieces.append(text[match.start():match.end()])
        offset = match.end()
    pieces.append(text[offset:])
    secondary_text = "".join(pieces)
    retained = len(_PAIR_BLOCK.findall(secondary_text))
    if retained != len(blocks) - len(affected):
        raise FrameSecondaryOverlayError("Saenger overlay did not retain the expected template pairs")

    old_pair_text = run_pair_file.read_text(encoding="utf-8")
    appended = "\n\n".join(
        f"{a.split(':', 1)[0]} {a.split(':', 1)[1]}\n"
        f"{b.split(':', 1)[0]} {b.split(':', 1)[1]}"
        for a, b in additions
    )
    new_pair_text = (
        old_pair_text.rstrip("\n") + "\n\n" + appended + "\n"
        if appended else old_pair_text
    )
    # The pair parser is authoritative: never silently change a range or
    # introduce duplicate contacts in the local NARestraints input.
    if appended:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="nasolve-frame-pairs-") as tmp:
            candidate = Path(tmp) / "pairs.txt"
            candidate.write_text(new_pair_text, encoding="utf-8")
            parsed = read_base_pair_file(candidate)
            n_pairs = sum(len(stretch.pairs()) for stretch in parsed)
            expected = sum(len(stretch.pairs()) for stretch in existing_stretches) + len(additions)
            if n_pairs != expected:
                raise FrameSecondaryOverlayError("Modified scaffold pairs have an invalid stretch count")

    run_secondary.write_text(secondary_text, encoding="utf-8")
    if additions:
        run_pair_file.write_text(new_pair_text, encoding="utf-8")
    return {
        "schema_version": 1,
        "mode": "modified-frame-pairs-to-narestraints",
        "source_sha256": file_sha256(source_secondary),
        "run_secondary_sha256": file_sha256(run_secondary),
        "run_pair_file_sha256": file_sha256(run_pair_file),
        "base_pair_count": len(blocks),
        "retained_saenger_count": retained,
        "replaced_saenger_count": len(replacements),
        "explicit_new_pair_count": len(additions),
        "replacements": replacements,
        "workbook_compatibility_corrections": corrections,
    }


__all__ = [
    "FrameSecondaryOverlayError",
    "prepare_frame_modified_secondary_overlay",
]
