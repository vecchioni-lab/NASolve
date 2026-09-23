"""Pure target assembly for explicitly sequence-defined construct families.

A sequence reference is one optional project resource, not a campaign-wide
requirement or a claim that members can exchange MR models. This module does
not alter coordinates, select dictionaries, add metals, or launch tools.
Existing chirality, chemistry and mutation-execution gates remain separate.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class SequenceReferenceError(ValueError):
    """A sequence reference or an overlay cannot be resolved unambiguously."""


_CHAIN = re.compile(r"[A-Za-z0-9_]")
_RESID = re.compile(r"-?(?:0|[1-9][0-9]*)[A-Za-z]?")
_CODE = re.compile(r"[A-Z0-9]{1,5}")
_SEQUENCE_CODES = {
    "DNA": {"A": "DA", "C": "DC", "G": "DG", "T": "DT"},
    "RNA": {"A": "A", "C": "C", "G": "G", "U": "U"},
}


def _fail(message: str) -> None:
    raise SequenceReferenceError(message)


def _exact_fields(value: object, fields: set[str], context: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != fields:
        _fail(f"{context} must contain exactly: {', '.join(sorted(fields))}")
    return value


def _text(value: object, context: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or any(ord(char) < 32 for char in value)
    ):
        _fail(f"{context} must be non-empty text without padding/control characters")
    return value


def _sequence(value: object, polymer: str, length: int, context: str) -> str:
    if not isinstance(value, str):
        _fail(f"{context} must be a sequence string")
    sequence = "".join(value.split()).upper()
    if len(sequence) != length:
        _fail(f"{context}: expected {length} bases, found {len(sequence)}")
    invalid = sorted(set(sequence) - set(_SEQUENCE_CODES[polymer]))
    if invalid:
        _fail(f"{context}: unsupported {polymer} sequence symbols: {', '.join(invalid)}")
    return sequence


@dataclass(frozen=True)
class ReferenceChain:
    chain: str
    residue_ids: tuple[str, ...]
    polymer: str
    sequence: str


@dataclass(frozen=True)
class SequenceReference:
    identifier: str
    version: str
    chains: tuple[ReferenceChain, ...]
    content_sha256: str

    @property
    def sites(self) -> tuple[str, ...]:
        return tuple(
            f"{item.chain}:{resid}"
            for item in self.chains
            for resid in item.residue_ids
        )


def parse_sequence_reference(value: object) -> SequenceReference:
    """Validate an explicit chain/residue correspondence; never infer row order."""
    value = _exact_fields(
        value, {"schema_version", "kind", "id", "version", "chains"}, "Reference"
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        _fail("Unsupported sequence-reference schema")
    if value["kind"] != "sequence-defined-reference":
        _fail("Expected a sequence-defined-reference, not a generic family record")
    identifier = _text(value["id"], "Reference id")
    version = _text(value["version"], "Reference version")
    raw_chains = value["chains"]
    if not isinstance(raw_chains, list) or not raw_chains:
        _fail("Reference chains must be a non-empty list")
    chains: list[ReferenceChain] = []
    seen: set[str] = set()
    for item in raw_chains:
        item = _exact_fields(
            item, {"chain", "residue_ids", "polymer", "sequence"}, "Reference chain"
        )
        chain = item["chain"]
        if not isinstance(chain, str) or _CHAIN.fullmatch(chain) is None:
            _fail("Reference chain must be one explicit PDB chain identifier")
        if chain in seen:
            _fail(f"Duplicate reference chain: {chain}")
        seen.add(chain)
        ids = item["residue_ids"]
        if (
            not isinstance(ids, list)
            or not ids
            or any(not isinstance(x, str) or _RESID.fullmatch(x) is None for x in ids)
        ):
            _fail(f"Reference chain {chain} requires explicit residue-ID strings")
        if len(set(ids)) != len(ids):
            _fail(f"Duplicate reference residue ID in chain {chain}")
        polymer = item["polymer"]
        if not isinstance(polymer, str) or polymer not in _SEQUENCE_CODES:
            _fail(f"Reference chain {chain}: polymer must explicitly be DNA or RNA")
        sequence = _sequence(item["sequence"], polymer, len(ids), f"Reference {chain}")
        chains.append(ReferenceChain(chain, tuple(ids), polymer, sequence))
    # Canonical validated content identifies semantics, not a file's location.
    normalized = {
        "schema_version": 1,
        "kind": "sequence-defined-reference",
        "id": identifier,
        "version": version,
        "chains": [
            {"chain": c.chain, "residue_ids": list(c.residue_ids),
             "polymer": c.polymer, "sequence": c.sequence}
            for c in chains
        ],
    }
    fingerprint = sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return SequenceReference(identifier, version, tuple(chains), fingerprint)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"Duplicate JSON key in sequence reference: {key}")
        result[key] = value
    return result


def load_sequence_reference(path: Path) -> SequenceReference:
    """Read one explicitly selected reference; no filename-based discovery."""
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
    except (OSError, ValueError) as exc:
        raise SequenceReferenceError(f"Could not read sequence reference {path}: {exc}") from exc
    return parse_sequence_reference(value)


def compile_sequence_family_targets(
    reference: SequenceReference,
    *,
    thread_sequences: Mapping[str, str] | None = None,
    dataset_sequences: Mapping[str, str] | None = None,
    thread_site_codes: Mapping[str, str] | None = None,
    dataset_site_codes: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Resolve one residue target per site, retaining all layer assignments.

    Sequence overlays replace complete declared chains, not their numbering.
    Site-code overlays contain already-resolved component identities, not aliases.
    More specific site chemistry takes precedence over ordinary sequence letters;
    dataset site declarations then override inherited/thread site declarations.
    Code syntax is checked here; dictionary support and actual chemistry are not.
    This primitive is not yet wired into AutoMR/PostMR or campaign input parsing.
    """
    if not isinstance(reference, SequenceReference):
        _fail("An explicitly validated sequence reference is required")
    if (
        not isinstance(reference.chains, tuple)
        or not all(isinstance(chain, ReferenceChain) for chain in reference.chains)
    ):
        _fail("Reference chains must be validated ReferenceChain records")
    # Revalidate even a directly constructed dataclass; type annotations alone
    # do not establish valid reference metadata.
    checked = parse_sequence_reference({
        "schema_version": 1, "kind": "sequence-defined-reference",
        "id": reference.identifier, "version": reference.version,
        "chains": [
            {"chain": c.chain, "residue_ids": list(c.residue_ids),
             "polymer": c.polymer, "sequence": c.sequence}
            for c in reference.chains
        ],
    })
    if reference.content_sha256 != checked.content_sha256:
        _fail("Sequence-reference content fingerprint does not match its fields")
    by_chain = {chain.chain: chain for chain in checked.chains}
    assignments: dict[str, list[dict[str, str]]] = {site: [] for site in checked.sites}

    def assign_sequence(chain: ReferenceChain, sequence: str, source: str) -> None:
        codes = _SEQUENCE_CODES[chain.polymer]
        for resid, base in zip(chain.residue_ids, sequence):
            assignments[f"{chain.chain}:{resid}"].append({
                "source": source, "residue_code": codes[base],
            })

    for chain in checked.chains:
        assign_sequence(chain, chain.sequence, "family_reference")
    for source, overlay in (
        ("thread_sequence", thread_sequences), ("dataset_sequence", dataset_sequences)
    ):
        if overlay is None:
            continue
        if not isinstance(overlay, Mapping):
            _fail(f"{source} must map explicit chain identifiers to sequences")
        for name, raw_sequence in overlay.items():
            if name not in by_chain:
                _fail(f"{source}: unknown reference chain {name!r}")
            chain = by_chain[name]
            sequence = _sequence(
                raw_sequence, chain.polymer, len(chain.residue_ids), f"{source} {name}"
            )
            assign_sequence(chain, sequence, source)
    for source, overlay in (
        ("thread_site_chemistry", thread_site_codes),
        ("dataset_site_chemistry", dataset_site_codes),
    ):
        if overlay is None:
            continue
        if not isinstance(overlay, Mapping):
            _fail(f"{source} must map explicit sites to resolved component codes")
        for site, code in overlay.items():
            if site not in assignments:
                _fail(f"{source}: unknown reference site {site!r}")
            if not isinstance(code, str) or _CODE.fullmatch(code) is None:
                _fail(f"{source} {site}: expected an uppercase resolved component code")
            assignments[site].append({"source": source, "residue_code": code})
    return {
        "schema_version": 1,
        "kind": "sequence-family-target",
        "reference": {
            "id": checked.identifier, "version": checked.version,
            "content_sha256": checked.content_sha256,
        },
        "sites": [
            {"site": site, "residue_code": history[-1]["residue_code"],
             "source": history[-1]["source"], "assignments": history}
            for site, history in assignments.items()
        ],
    }


def compare_sequence_family_inventory(
    reference: SequenceReference,
    inventory: Mapping[str, str],
    **overlays: Mapping[str, str] | None,
) -> dict[str, object]:
    """Compare all reference sites to literal model identities without mutation.

    Missing/extra sites are mapping failures, not invitations to renumber, insert,
    delete, align, or rebuild a polymer. Differences are identity differences,
    not an assertion that a mutation method or a ligand dictionary is supported.
    """
    target = compile_sequence_family_targets(reference, **overlays)
    if not isinstance(inventory, Mapping):
        _fail("Model inventory must be a mapping of explicit sites to residue codes")
    expected = set(reference.sites)
    if any(not isinstance(site, str) for site in inventory):
        _fail("Model inventory site keys must be strings")
    missing, unexpected = expected - set(inventory), set(inventory) - expected
    if missing or unexpected:
        _fail(
            "Model/reference site correspondence differs; missing="
            + repr(sorted(missing)) + "; unexpected=" + repr(sorted(unexpected))
        )
    if any(not isinstance(code, str) or _CODE.fullmatch(code) is None for code in inventory.values()):
        _fail("Model inventory must contain literal uppercase residue codes")
    differences = [
        {"site": row["site"], "before": inventory[row["site"]],
         "after": row["residue_code"], "source": row["source"]}
        for row in target["sites"]
        if inventory[row["site"]] != row["residue_code"]
    ]
    return {"target": target, "target_count": len(target["sites"]),
            "differences": differences, "matches": not differences}


__all__ = [
    "SequenceReferenceError", "ReferenceChain", "SequenceReference",
    "parse_sequence_reference", "load_sequence_reference",
    "compile_sequence_family_targets", "compare_sequence_family_inventory",
]
