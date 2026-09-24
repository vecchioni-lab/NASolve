"""Opt-in, run-local sequence-family provenance for standalone AutoMR/PostMR.

This adapter freezes an already explicit reference and overlays; it neither
chooses an experimental family nor supplies a new coordinate-mutation engine.
Legacy reports without the additive contract retain their existing behavior.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .frame_postmr import frame_postmr_spec
from .model_assessment import ModelAssessment, ModelAssessmentError, inspect_pdb
from .residue_aliases import LigandCodeError, known_ligand_codes
from .run_context import artifact_reference, resolve_artifact_path
from .sequence_reference import (
    SequenceReference, SequenceReferenceError, compile_sequence_family_targets,
    parse_sequence_reference,
)


@dataclass(frozen=True)
class SequenceFamilySeed:
    """Validated immutable bytes prepared before a run directory is allocated."""

    reference_bytes: bytes
    target_bytes: bytes
    intent_sha256: str
    overlays_bytes: bytes
    differences: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class FrozenSequenceFamily:
    reference: SequenceReference
    target: dict[str, object]
    record: dict[str, object]

    @property
    def codes(self) -> dict[str, str]:
        return {row["site"]: row["residue_code"] for row in self.target["sites"]}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SequenceReferenceError(f"Duplicate JSON key in sequence-family artifact: {key}")
        result[key] = value
    return result


def _decode(data: bytes, label: str) -> object:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique)
    except (UnicodeError, ValueError) as exc:
        raise SequenceReferenceError(f"Could not read {label}: {exc}") from exc


def _intent_fingerprint(plan: Mapping[str, object], frame: object, mirror: object) -> str:
    if type(mirror) is not bool:
        raise SequenceReferenceError("Sequence-family mirror intent must be a boolean")
    intent = {
        "frame": frame, "mirror": mirror,
        "sequences": plan.get("sequences"),
        "standard_pair": plan.get("standard_pair"),
        "mutations": plan.get("mutations"),
    }
    try:
        return sha256(_json_bytes(intent)).hexdigest()
    except (TypeError, ValueError) as exc:
        raise SequenceReferenceError("Malformed sequence-family input intent") from exc


def _site_codes(plan: Mapping[str, object], frame: str | None) -> dict[str, str]:
    """Read already-resolved NEW-run codes; never reinterpret historical aliases."""
    codes: dict[str, str] = {}
    pair = plan.get("standard_pair")
    if pair is not None:
        if not isinstance(pair, Mapping) or not isinstance(frame, str):
            raise SequenceReferenceError("Malformed sequence-family standard pair")
        pair_codes = pair.get("ligand_codes")
        if not isinstance(pair_codes, list) or len(pair_codes) != 2:
            raise SequenceReferenceError("Sequence-family standard pair requires two resolved codes")
        try:
            spec = frame_postmr_spec(frame)
        except KeyError as exc:
            raise SequenceReferenceError(str(exc)) from exc
        codes.update((site.text, code) for site, code in zip(spec.sites, pair_codes))
    mutations = plan.get("mutations", {})
    if not isinstance(mutations, Mapping):
        raise SequenceReferenceError("Malformed sequence-family mutation declarations")
    for site, request in mutations.items():
        if not isinstance(request, Mapping):
            raise SequenceReferenceError(f"Malformed sequence-family mutation at {site}")
        codes[site] = request.get("ligand_code")
    # The pure compiler validates all site/code values, including None or aliases.
    return codes


def _model_inventory(
    model: Path, assessment: ModelAssessment, reference: SequenceReference,
) -> dict[str, str]:
    if assessment.duplicate_atom_identities:
        raise SequenceReferenceError("Duplicate coordinate atom identities make sequence-family correspondence ambiguous")
    expected = set(reference.sites)
    observed = {
        f"{chain}:{resid}"
        for chain, ids in assessment.polymer_residue_ids_by_chain.items()
        for resid in ids
    }
    if observed != expected:
        raise SequenceReferenceError(
            "Model/reference site correspondence differs; missing="
            + repr(sorted(expected - observed)) + "; unexpected="
            + repr(sorted(observed - expected))
        )
    try:
        data = model.read_bytes()
    except OSError as exc:
        raise SequenceReferenceError(f"Could not read sequence-family model {model}: {exc}") from exc
    if sha256(data).hexdigest() != assessment.sha256:
        raise SequenceReferenceError("Model changed after its sequence-family inventory was assessed")
    names: dict[str, set[str]] = {site: set() for site in reference.sites}
    model_records = 0
    try:
        lines = data.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as exc:
        raise SequenceReferenceError("Sequence-family model is not UTF-8 text") from exc
    for line in lines:
        if line.startswith("MODEL "):
            model_records += 1
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 27:
            continue
        site = f"{line[21:22].strip() or '_'}:{line[22:26].strip()}{line[26:27].strip()}"
        if site in names:
            names[site].add(line[17:20].strip())
    if model_records > 1:
        raise SequenceReferenceError("Sequence-family correspondence requires one coordinate model")
    ambiguous = [site for site, values in names.items() if len(values) != 1]
    if ambiguous:
        raise SequenceReferenceError("Missing or ambiguous sequence-family identities: " + ", ".join(ambiguous))
    return {site: next(iter(values)) for site, values in names.items()}


def prepare_sequence_family(
    reference_path: Path, model: Path, assessment: ModelAssessment,
    plan: Mapping[str, object], *, frame: str | None, mirror: bool,
) -> SequenceFamilySeed:
    """Validate and compile once, retaining the exact reference bytes consumed."""
    try:
        raw = reference_path.read_bytes()
    except OSError as exc:
        raise SequenceReferenceError(f"Could not read selected sequence reference: {exc}") from exc
    reference = parse_sequence_reference(_decode(raw, "selected sequence reference"))
    sequences = plan.get("sequences", {})
    if not isinstance(sequences, Mapping):
        raise SequenceReferenceError("Malformed sequence-family dataset sequences")
    overlays = {"dataset_sequences": dict(sequences), "dataset_site_codes": _site_codes(plan, frame)}
    target = compile_sequence_family_targets(reference, **overlays)
    inventory = _model_inventory(model, assessment, reference)
    differences = tuple(
        (row["site"], inventory[row["site"]], row["residue_code"])
        for row in target["sites"] if inventory[row["site"]] != row["residue_code"]
    )
    return SequenceFamilySeed(
        raw, _json_bytes(target), _intent_fingerprint(plan, frame, mirror),
        _json_bytes(overlays), differences,
    )


def freeze_sequence_family(seed: SequenceFamilySeed, run: Path) -> dict[str, object]:
    """Write new run-local artifacts; never replace an earlier snapshot."""
    def write(name: str, data: bytes) -> dict[str, object]:
        path = run / "Model" / name
        with path.open("xb") as handle:
            handle.write(data)
        return {**artifact_reference(path, run), "sha256": sha256(data).hexdigest(), "size": len(data)}

    reference = write("sequence_reference.json", seed.reference_bytes)
    target = write("sequence_family_target.json", seed.target_bytes)
    return {
        "schema_version": 1, "kind": "frozen-sequence-family",
        "reference": reference, "target": target,
        "intent_sha256": seed.intent_sha256,
        "overlays": _decode(seed.overlays_bytes, "sequence-family overlays"),
    }


def _frozen_bytes(value: object, run: Path, label: str) -> bytes:
    if (
        not isinstance(value, Mapping) or value.get("anchor") != "run"
        or not isinstance(value.get("relative_path"), str)
        or not isinstance(value.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
        or type(value.get("size")) is not int or value["size"] <= 0
    ):
        raise SequenceReferenceError(f"Malformed run-local {label} reference")
    try:
        path = resolve_artifact_path(value, run)
        if path is None:
            raise SequenceReferenceError(f"Frozen {label} is missing or failed checksum validation")
        path.resolve().relative_to(run.resolve())
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise SequenceReferenceError(f"Could not read run-local {label}: {exc}") from exc
    if len(data) != value["size"] or sha256(data).hexdigest() != value["sha256"]:
        raise SequenceReferenceError(f"Frozen {label} changed while being read")
    return data


def load_frozen_sequence_family(
    report: Mapping[str, object], run: Path | None,
) -> FrozenSequenceFamily | None:
    """Use only this run's verified artifacts, never the current installed recipe."""
    plan = report.get("post_mr_plan")
    inputs = report.get("inputs")
    input_reference = inputs.get("sequence_reference") if isinstance(inputs, Mapping) else None
    if not isinstance(plan, Mapping) or "sequence_family" not in plan:
        if input_reference is not None:
            raise SequenceReferenceError("Selected sequence reference has no frozen target contract")
        return None
    if run is None:
        raise SequenceReferenceError("An explicit run_directory is required for frozen sequence-family targets")
    value = plan["sequence_family"]
    fields = {"schema_version", "kind", "reference", "target", "intent_sha256", "overlays"}
    if (
        not isinstance(value, Mapping) or set(value) != fields
        or type(value.get("schema_version")) is not int or value["schema_version"] != 1
        or value.get("kind") != "frozen-sequence-family"
    ):
        raise SequenceReferenceError("Malformed frozen sequence-family contract")
    if input_reference != value["reference"]:
        raise SequenceReferenceError("Input sequence-reference provenance disagrees with the frozen contract")
    frame = report.get("frame")
    frame_name = frame.get("name") if isinstance(frame, Mapping) else None
    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise SequenceReferenceError("Frozen sequence-family report has no input record")
    expected_intent = _intent_fingerprint(plan, frame_name, inputs.get("mirror", False))
    if value["intent_sha256"] != expected_intent:
        raise SequenceReferenceError("Frozen sequence-family input intent has changed")
    reference = parse_sequence_reference(_decode(
        _frozen_bytes(value["reference"], run, "sequence reference"), "frozen sequence reference",
    ))
    overlays = value["overlays"]
    if not isinstance(overlays, Mapping) or set(overlays) != {"dataset_sequences", "dataset_site_codes"}:
        raise SequenceReferenceError("Malformed frozen sequence-family overlays")
    if overlays["dataset_sequences"] != plan.get("sequences", {}):
        raise SequenceReferenceError("Frozen sequence-family sequence overlays disagree with the plan")
    if overlays["dataset_site_codes"] != _site_codes(plan, frame_name):
        raise SequenceReferenceError("Frozen sequence-family site overlays disagree with the plan")
    target = _decode(_frozen_bytes(value["target"], run, "sequence target"), "frozen sequence target")
    expected_target = compile_sequence_family_targets(reference, **dict(overlays))
    if target != expected_target:
        raise SequenceReferenceError("Frozen sequence-family target differs from its reference/overlays")
    return FrozenSequenceFamily(reference, expected_target, dict(value))


def sequence_family_inventory(
    family: FrozenSequenceFamily, model: Path, *, extra_codes: tuple[str, ...] = (),
) -> tuple[dict[str, str], ModelAssessment]:
    """Check complete correspondence using the existing polymer classifier."""
    try:
        codes = set(known_ligand_codes()) | set(family.codes.values()) | set(extra_codes)
        assessment = inspect_pdb(model, polymer_ligand_codes=codes)
    except (ModelAssessmentError, LigandCodeError) as exc:
        raise SequenceReferenceError(f"Sequence-family model assessment failed: {exc}") from exc
    return _model_inventory(model, assessment, family.reference), assessment


def audit_sequence_family_model(
    family: FrozenSequenceFamily, model: Path, expected_codes: Mapping[str, str], run: Path,
) -> dict[str, object]:
    """Verify complete prepared residue identities, not coordinates or chemistry."""
    if set(expected_codes) != set(family.reference.sites):
        raise SequenceReferenceError("Executable sequence-family plan has incomplete target coverage")
    inventory, assessment = sequence_family_inventory(
        family, model, extra_codes=tuple(expected_codes.values()),
    )
    mismatches = [
        f"{site} {inventory[site]} != {code}"
        for site, code in expected_codes.items() if inventory[site] != code
    ]
    if mismatches:
        raise SequenceReferenceError("Prepared model differs from frozen sequence-family target: " + "; ".join(mismatches))
    return {
        "status": "PASS", "target_count": len(expected_codes), "mismatches": [],
        "reference_id": family.reference.identifier,
        "reference_version": family.reference.version,
        "reference": family.record["reference"], "target": family.record["target"],
        "model": {**artifact_reference(model, run), "sha256": assessment.sha256, "size": assessment.byte_size},
        "scope": "residue-identities-only; chemistry and geometry gates remain separate",
    }
