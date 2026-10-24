"""Explicit, bounded dictionary derivatives; no general chemistry inference.

Preparation never edits the source or adopts a dictionary into an existing run.
The content-based alternate adapter is already supported by NASolve. The 5CM
reference recipe is confined to the exact reviewed historical source and output;
its prior native diagnostic is not general scientific qualification.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .dictionary_compatibility import TORSION_POLICY, normalize_torsion_block
from .ligand_profiles import _blocks, _emit, normalize_ccp4_torsion_alternates


RECIPE_IDS = ("torsion-alternates-v1", "5cm-reviewed-torsion-v1")
REVIEWED_5CM_SOURCE_SHA256 = (
    "38378c7df4eef73a0bd2be40059b2c3dd2b98618a4eeb7e91f6ec3427f7e7858")
REVIEWED_5CM_CANDIDATE_SHA256 = (
    "61bf14a1f52e5294bb38a1a27144d464010e01e95ac60da0e1b2ce13070ea562")
_TOR = "_chem_comp_tor."


class CIFPreparationError(ValueError):
    """A recipe, preservation guard or bounded-change check failed."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact(path: Path, data: bytes) -> dict:
    # Names are descriptive provenance, never input-resolution authority. The
    # caller can add declared anchor/relative_path references for a saved report.
    return {"name": path.name, "sha256": _sha(data), "size": len(data)}


def _source_guard(source: Path, expected_sha: str) -> None:
    if _sha(source.read_bytes()) != expected_sha:
        raise CIFPreparationError("Source changed during dictionary preparation")


def _reviewed_reference(values: list[dict]) -> dict:
    matches = []
    for block in values:
        columns = {key[len(_TOR):]: value for key, value in block.items()
                   if key.startswith(_TOR)}
        required = ("comp_id", "id", "atom_id_1", "atom_id_2", "atom_id_3",
                    "atom_id_4", "value_angle", "value_angle_esd", "period")
        if not all(key in columns for key in required):
            continue
        count = len(columns["id"])
        if any(not isinstance(column, list) or len(column) != count
               for column in columns.values()):
            raise CIFPreparationError("Reviewed 5CM torsion layout changed")
        for index in range(count):
            quartet = [columns[f"atom_id_{i}"][index] for i in range(1, 5)]
            if (columns["comp_id"][index] == "5CM"
                    and columns["id"][index] == "C2e-nyu0"
                    and quartet == ["C4'", "O4'", "C1'", "C2"]
                    and float(columns["value_angle"][index]) == 340.7
                    and float(columns["value_angle_esd"][index]) == 6.3
                    and float(columns["period"][index]) == 1):
                matches.append((block, index))
    if len(matches) != 1:
        raise CIFPreparationError("Reviewed 5CM reference requires exactly one matching torsion")
    block, index = matches[0]
    block[_TOR + "atom_id_4"][index] = "C2'"
    return {"block": block["data_"], "component": "5CM", "term_id": "C2e-nyu0",
            "status": "ADAPTED", "action": "reviewed-atom-reference",
            "field": _TOR + "atom_id_4", "before": "C2", "after": "C2'",
            "source_hash_scope": REVIEWED_5CM_SOURCE_SHA256}


def _verify_allowlist(original: list[dict], expected: list[dict], actual: list[dict]) -> list[dict]:
    """Compare every parsed field; only the declared torsion transform may vary."""
    if len(original) != len(actual) or len(expected) != len(actual):
        raise CIFPreparationError("Preparation allowlist rejected a changed block inventory")
    changes = []
    for before, permitted, after in zip(original, expected, actual):
        if {key: val for key, val in before.items() if not key.startswith(_TOR)} != {
                key: val for key, val in after.items() if not key.startswith(_TOR)}:
            raise CIFPreparationError("Preparation allowlist rejected a non-torsion change")
        if after != permitted:
            raise CIFPreparationError("Preparation allowlist rejected an undeclared torsion change")
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                changes.append({"block": before["data_"], "field": key,
                                "before": before.get(key), "after": after.get(key)})
    return changes


def prepare_dictionary(source: Path, output: Path, *, recipe: str) -> dict:
    """Prepare one exclusive derivative and return a review receipt.

    ``torsion-alternates-v1`` wraps the existing content-based adapter; unknown
    conflicts remain visible. ``5cm-reviewed-torsion-v1`` requires the exact
    historical SHA-256, changes one demonstrated C2/C2' reference and uses that
    adapter. Neither recipe changes bonds, protonation, phosphates or chirality.

    The output is a candidate, never automatic adoption. Assessment is read-only;
    native interpretation and achieved model geometry are explicitly not run.
    Existing outputs, including symlinks, are refused. Source bytes are checked
    before and after preparation and publication.
    """
    from .cif_doctor import assess_dictionaries

    source, output = Path(source), Path(output)
    if recipe not in RECIPE_IDS:
        raise CIFPreparationError(f"Unknown dictionary preparation recipe: {recipe}")
    if source.resolve() == output.resolve():
        raise CIFPreparationError("Preparation output must differ from its source")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Preparation output already exists: {output}")
    source_bytes = source.read_bytes()
    source_sha = _sha(source_bytes)
    if recipe == "5cm-reviewed-torsion-v1" and source_sha != REVIEWED_5CM_SOURCE_SHA256:
        raise CIFPreparationError(
            "Reviewed 5CM recipe requires source SHA-256 " + REVIEWED_5CM_SOURCE_SHA256)

    with TemporaryDirectory(prefix="nasolve-cif-prepare-") as temporary:
        work = Path(temporary)
        snapshot = work / "source" / source.name
        snapshot.parent.mkdir()
        snapshot.write_bytes(source_bytes)
        original_blocks = _blocks(snapshot)
        original = [deepcopy(block.values) for block in original_blocks]
        reviewed = deepcopy(original)
        events = []
        before = assess_dictionaries([snapshot], stage="source")
        adapter_input = snapshot
        if recipe == "5cm-reviewed-torsion-v1":
            events.append(_reviewed_reference(reviewed))
            adapter_input = work / "reviewed.cif"
            adapter_input.write_text("\n".join(
                _emit(values) if values != block.values else block.text
                for block, values in zip(original_blocks, reviewed)), encoding="utf-8")

        expected = []
        for values in reviewed:
            normalized, _ = normalize_torsion_block(values)
            expected.append(normalized)
        candidate = work / "candidate" / output.name
        candidate.parent.mkdir()
        adapter_audits = []
        adapter_changed = normalize_ccp4_torsion_alternates(
            adapter_input, candidate, audit=adapter_audits)
        if not adapter_changed and recipe == "torsion-alternates-v1":
            # The existing text adapter uses universal newlines. A semantic
            # no-op here is an exact byte copy, including supplier line endings.
            candidate.write_bytes(source_bytes)
        events.extend(event for audit in adapter_audits for event in audit["events"])
        actual = [block.values for block in _blocks(candidate)]
        changes = _verify_allowlist(original, expected, actual)
        candidate_bytes = candidate.read_bytes()
        if (recipe == "5cm-reviewed-torsion-v1"
                and _sha(candidate_bytes) != REVIEWED_5CM_CANDIDATE_SHA256):
            raise CIFPreparationError("Reviewed 5CM candidate SHA-256 changed; recipe needs review")
        after = assess_dictionaries([candidate], stage="effective")
        _source_guard(source, source_sha)

        # Exclusive publication prevents collisions with an existing candidate.
        # Remove only our own untouched inode if a late preservation check fails.
        published_identity = None
        try:
            with output.open("xb") as handle:
                published_identity = os.fstat(handle.fileno())
                handle.write(candidate_bytes)
                handle.flush()
                _source_guard(source, source_sha)
            if output.read_bytes() != candidate_bytes:
                raise CIFPreparationError("Preparation output changed during publication")
            _source_guard(source, source_sha)
        except Exception:
            if published_identity is not None:
                try:
                    current = output.stat()
                    if ((current.st_dev, current.st_ino)
                            == (published_identity.st_dev, published_identity.st_ino)
                            and output.read_bytes() == candidate_bytes):
                        output.unlink()
                except OSError:
                    pass
            raise

    return {
        "schema_version": 1,
        "audit_kind": "cif_restraint_preparation",
        "status": "PREPARED",
        "recipe_id": recipe,
        "adapter_policy": TORSION_POLICY,
        "source": _artifact(source, source_bytes),
        "output": _artifact(output, candidate_bytes),
        "source_preserved": True,
        "changed": source_bytes != candidate_bytes,
        "changes": changes,
        "events": events,
        "before_assessment": before,
        "after_assessment": after,
        "adoption_status": "BLOCKED" if after["status"] == "INVALID" else "REVIEW_REQUIRED",
        "automatic_adoption": False,
        "native_validation": {"status": "NOT_RUN", "reason": "No Phenix invocation in preparation"},
        "model_geometry_validation": {"status": "NOT_RUN", "reason": "No coordinate model supplied"},
    }
