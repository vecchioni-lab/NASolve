"""Strict parser for explicit campaign sequence-thread declarations.

Threads provide inherited sequence/identity intent only. They never select MR
models, imply model compatibility, or authorize cross-dataset model reuse.
"""
from __future__ import annotations

import re
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class SequenceThreadError(ValueError):
    """A campaign sequence-thread declaration is malformed or unsupported."""


_THREAD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_SITE = re.compile(r"[A-Za-z0-9_]:[^:\s]+\Z")
_CODE = re.compile(r"[A-Z0-9]{1,5}\Z")
_TOP = {"schema_version", "sequence_threads"}
_FIELDS = {"datasets", "sequence_reference", "sequences", "site_codes"}


def _fail(message: str) -> None:
    raise SequenceThreadError(message)


def parse_sequence_threads(data: bytes) -> dict[str, dict[str, object]]:
    """Parse one root campaign TOML into normalized immutable-intent values."""
    try:
        payload = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        _fail(f"Invalid nasolve-campaign.toml: {exc}")
    if not isinstance(payload, dict) or set(payload) - _TOP:
        _fail("nasolve-campaign.toml contains unsupported top-level fields")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        _fail("nasolve-campaign.toml requires integer schema_version = 1")
    raw_threads = payload.get("sequence_threads", {})
    if not isinstance(raw_threads, dict):
        _fail("sequence_threads must be a TOML table")

    result: dict[str, dict[str, object]] = {}
    membership: dict[str, str] = {}
    for thread_id, raw in raw_threads.items():
        if not isinstance(thread_id, str) or _THREAD_ID.fullmatch(thread_id) is None:
            _fail(f"Invalid sequence thread id: {thread_id!r}")
        if not isinstance(raw, dict) or set(raw) - _FIELDS:
            _fail(f"Sequence thread {thread_id!r} contains unsupported fields")
        datasets = raw.get("datasets")
        if (
            not isinstance(datasets, list) or not datasets
            or not all(isinstance(item, str) and item for item in datasets)
            or len(set(datasets)) != len(datasets)
        ):
            _fail(f"Sequence thread {thread_id!r} requires unique dataset names")
        for dataset in datasets:
            previous = membership.get(dataset)
            if previous is not None:
                _fail(
                    f"Dataset {dataset!r} belongs to multiple sequence threads: "
                    f"{previous!r} and {thread_id!r}"
                )
            membership[dataset] = thread_id

        reference = raw.get("sequence_reference")
        if reference != "w-metal-scaffold":
            _fail(
                f"Sequence thread {thread_id!r} currently requires "
                "sequence_reference = \"w-metal-scaffold\""
            )

        sequences = raw.get("sequences", {})
        if not isinstance(sequences, dict):
            _fail(f"Sequence thread {thread_id!r}.sequences must be a table")
        normalized_sequences: dict[str, str] = {}
        for chain, sequence in sequences.items():
            if (
                not isinstance(chain, str) or len(chain) != 1
                or not isinstance(sequence, str) or not sequence.strip()
            ):
                _fail(f"Sequence thread {thread_id!r} has an invalid chain sequence")
            normalized_sequences[chain] = "".join(sequence.split()).upper()

        site_codes = raw.get("site_codes", {})
        if not isinstance(site_codes, dict):
            _fail(f"Sequence thread {thread_id!r}.site_codes must be a table")
        normalized_codes: dict[str, str] = {}
        for site, code in site_codes.items():
            if (
                not isinstance(site, str) or _SITE.fullmatch(site) is None
                or not isinstance(code, str) or _CODE.fullmatch(code) is None
            ):
                _fail(f"Sequence thread {thread_id!r} has invalid site chemistry")
            normalized_codes[site] = code

        result[thread_id] = {
            "id": thread_id,
            "datasets": sorted(datasets),
            "sequence_reference": reference,
            "sequences": dict(sorted(normalized_sequences.items())),
            "site_codes": dict(sorted(normalized_codes.items())),
        }
    return dict(sorted(result.items()))


def membership_by_dataset(
    threads: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Return exact explicit membership; never infer family relationships."""
    result: dict[str, dict[str, object]] = {}
    for thread in threads.values():
        for dataset in thread["datasets"]:
            result[dataset] = thread
    return result


__all__ = [
    "SequenceThreadError", "parse_sequence_threads", "membership_by_dataset",
]
