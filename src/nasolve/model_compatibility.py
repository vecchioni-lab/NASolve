"""Descriptive model-compatibility facts for future campaign reasoning.

This module joins already-authoritative NASolve provenance into explicit,
machine-readable dimensions. It never computes an overall compatibility score,
authorizes donor reuse, or selects between candidate models.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

from .model_assessment import ModelAssessment
from .run_context import artifact_reference, resolve_artifact_path
from .search_model_comparison import (
    SearchModelComparisonError,
    load_search_model_comparison,
)


class ModelCompatibilityFactsError(RuntimeError):
    """Raised when compatibility facts cannot be built or verified."""


_RELATIONS = {"SAME", "DIFFERENT", "PARTIAL", "UNKNOWN"}


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _provider_summary(value: object) -> dict[str, object]:
    provider = value if isinstance(value, Mapping) else {}
    return {
        "kind": _text_or_none(provider.get("kind")),
        "selection": _text_or_none(provider.get("selection")),
        "location": _text_or_none(provider.get("location")),
        "selector": _text_or_none(provider.get("selector")),
        "declared_frame": _text_or_none(provider.get("frame")),
    }


def _frame_relation(candidate: str | None, recipient: str | None) -> str:
    if candidate is None or recipient is None:
        return "UNKNOWN"
    return "SAME" if candidate == recipient else "DIFFERENT"


def _comparison_dimensions(
    comparison: Mapping[str, object] | None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if comparison is None:
        unknown_site = {
            "relation": "UNKNOWN",
            "basis": "no-complete-explicit-residue-target",
            "missing_sites": [],
            "unexpected_sites": [],
        }
        unknown_identity = {
            "relation": "UNKNOWN",
            "basis": "no-complete-explicit-residue-target",
            "compared_site_count": 0,
            "mismatch_count": 0,
        }
        family = {
            "candidate_declared_family": None,
            "recipient_reference": None,
            "relation": "UNKNOWN",
            "basis": "candidate family membership is not declared",
        }
        return unknown_site, unknown_identity, family

    if (
        comparison.get("kind") != "search-model-target-comparison"
        or comparison.get("scope") != "complete-residue-target"
        or not isinstance(comparison.get("correspondence"), Mapping)
        or not isinstance(comparison.get("identity"), Mapping)
        or not isinstance(comparison.get("target"), Mapping)
    ):
        raise ModelCompatibilityFactsError(
            "Malformed search-model comparison supplied to compatibility facts"
        )
    correspondence = comparison["correspondence"]
    identity = comparison["identity"]
    target = comparison["target"]
    missing = correspondence.get("missing_sites")
    unexpected = correspondence.get("unexpected_sites")
    exact = correspondence.get("exact_site_set")
    mismatch_count = identity.get("mismatch_count")
    compared = identity.get("compared_site_count")
    if (
        type(exact) is not bool
        or not isinstance(missing, list)
        or not isinstance(unexpected, list)
        or not all(isinstance(site, str) for site in missing + unexpected)
        or type(mismatch_count) is not int
        or mismatch_count < 0
        or type(compared) is not int
        or compared < 0
    ):
        raise ModelCompatibilityFactsError(
            "Malformed search-model comparison summary"
        )
    site_relation = "SAME" if exact else "DIFFERENT"
    if exact:
        identity_relation = "SAME" if mismatch_count == 0 else "DIFFERENT"
    else:
        identity_relation = "PARTIAL" if compared else "UNKNOWN"
    reference = target.get("reference")
    if reference is not None and not isinstance(reference, Mapping):
        raise ModelCompatibilityFactsError(
            "Malformed search-model target reference"
        )
    recipient_reference = None
    if isinstance(reference, Mapping):
        recipient_reference = {
            "id": _text_or_none(reference.get("id")),
            "version": _text_or_none(reference.get("version")),
            "content_sha256": _text_or_none(reference.get("content_sha256")),
        }
    return (
        {
            "relation": site_relation,
            "basis": "complete-explicit-residue-target",
            "missing_sites": list(missing),
            "unexpected_sites": list(unexpected),
        },
        {
            "relation": identity_relation,
            "basis": "source-search-model-before-any-mirror-transform",
            "compared_site_count": compared,
            "mismatch_count": mismatch_count,
        },
        {
            "candidate_declared_family": None,
            "recipient_reference": recipient_reference,
            "relation": "UNKNOWN",
            "basis": (
                "the recipient target reference is known, but current model "
                "providers do not declare construct-family membership"
            ),
        },
    )


def build_model_compatibility_facts(
    *,
    source_assessment: ModelAssessment,
    effective_assessment: ModelAssessment,
    model_provider: Mapping[str, object] | None,
    mode: str,
    recipient_frame: str | None,
    mirror_transform_applied: bool,
    comparison: Mapping[str, object] | None,
    comparison_artifact: Mapping[str, object] | None,
    terminal_phosphate_sites: tuple[str, ...],
    phosphate_intent: Mapping[str, object] | None,
    backbone_policy: Mapping[str, object],
    symmetry: Mapping[str, object] | None,
) -> dict[str, object]:
    """Join explicit facts without deriving a compatibility verdict."""
    if mode not in {"standard", "nonstandard"}:
        raise ModelCompatibilityFactsError("Unsupported AutoMR mode in compatibility facts")
    if type(mirror_transform_applied) is not bool:
        raise ModelCompatibilityFactsError("Mirror-transform fact must be boolean")
    if any(not isinstance(site, str) for site in terminal_phosphate_sites):
        raise ModelCompatibilityFactsError("Terminal-phosphate sites must be explicit strings")
    if not isinstance(backbone_policy, Mapping):
        raise ModelCompatibilityFactsError("Backbone policy must be a mapping")

    provider = _provider_summary(model_provider)
    candidate_frame = _text_or_none(provider["declared_frame"])
    site_set, residue_identity, family = _comparison_dimensions(comparison)

    phosphate_source = "legacy"
    if isinstance(phosphate_intent, Mapping):
        phosphate_source = _text_or_none(phosphate_intent.get("source")) or "unknown"
    elif not terminal_phosphate_sites:
        phosphate_source = "none"

    sites = backbone_policy.get("sites", {})
    passthrough = backbone_policy.get("experimental_passthrough_sites", [])
    default = backbone_policy.get("default")
    if (
        not isinstance(sites, Mapping)
        or not all(isinstance(site, str) and isinstance(value, str) for site, value in sites.items())
        or not isinstance(passthrough, list)
        or not all(isinstance(site, str) for site in passthrough)
        or not isinstance(default, str)
    ):
        raise ModelCompatibilityFactsError("Malformed backbone policy in compatibility facts")

    symmetry_class = None
    mr_copies = None
    if isinstance(symmetry, Mapping):
        evidence = symmetry.get("evidence")
        if isinstance(evidence, Mapping):
            symmetry_class = _text_or_none(evidence.get("normalized_class"))
        copies = symmetry.get("mr_copies")
        if type(copies) is int and copies > 0:
            mr_copies = copies

    return {
        "schema_version": 1,
        "kind": "model-compatibility-facts",
        "roles": {
            "candidate": "effective-search-model-submitted-to-or-prepared-for-Phaser",
            "recipient": "frozen-AutoMR-intent-for-this-dataset",
        },
        "candidate": {
            "source_model_sha256": source_assessment.sha256,
            "effective_model_sha256": effective_assessment.sha256,
            "provider": provider,
            "mode": mode,
            "polymer_residue_count": effective_assessment.polymer_residue_count,
            "chains": [
                {
                    "chain": chain,
                    "residue_count": len(residue_ids),
                    "residue_ids": list(residue_ids),
                }
                for chain, residue_ids in effective_assessment.polymer_residue_ids_by_chain.items()
            ],
        },
        "recipient": {
            "mode": mode,
            "frame": recipient_frame,
            "symmetry_class": symmetry_class,
            "mr_copies": mr_copies,
        },
        "dimensions": {
            "frame_identity": {
                "candidate_declared_frame": candidate_frame,
                "recipient_frame": recipient_frame,
                "relation": _frame_relation(candidate_frame, recipient_frame),
                "basis": (
                    "provider declaration versus frozen recipient frame; "
                    "no coordinate inference"
                ),
            },
            "construct_family": family,
            "site_set": site_set,
            "residue_identity": residue_identity,
            "chirality": {
                "candidate_absolute_chirality": None,
                "recipient_absolute_chirality": None,
                "mirror_transform_applied": mirror_transform_applied,
                "relation": "UNKNOWN",
                "basis": (
                    "current schema records only a relative mirror transform; "
                    "absolute D/L chirality is not declared"
                ),
            },
            "terminal_phosphate_chemistry": {
                "recipient_sites": list(terminal_phosphate_sites),
                "recipient_intent_source": phosphate_source,
                "candidate_coordinate_evidence": "NOT_ASSESSED",
                "relation": "UNKNOWN",
            },
            "backbone_chemistry": {
                "recipient_default": default,
                "recipient_site_overrides": dict(sites),
                "experimental_passthrough_sites": list(passthrough),
                "recipient_allow_unreviewed": bool(backbone_policy.get("allow_unreviewed", False)),
                "candidate_coordinate_evidence": "NOT_ASSESSED",
                "relation": "UNKNOWN",
            },
            "symmetry_and_copy_number": {
                "recipient_symmetry_class": symmetry_class,
                "recipient_mr_copies": mr_copies,
                "candidate_coordinate_claim": None,
                "relation": "UNKNOWN",
                "basis": (
                    "diffraction symmetry/copy-number intent belongs to the "
                    "recipient dataset, not the coordinate model"
                ),
            },
        },
        "evidence": {
            "search_model_comparison": (
                dict(comparison_artifact)
                if isinstance(comparison_artifact, Mapping)
                else None
            ),
        },
        "semantics": {
            "descriptive_only": True,
            "score": None,
            "overall_compatibility": None,
            "donor_eligibility": None,
            "automatic_reuse_authorized": False,
        },
    }


def _validate_relation(value: object, label: str) -> None:
    if value not in _RELATIONS:
        raise ModelCompatibilityFactsError(f"Malformed {label} relation")


def _validated_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ModelCompatibilityFactsError("Frozen compatibility facts are not an object")
    required = {
        "schema_version", "kind", "roles", "candidate", "recipient",
        "dimensions", "evidence", "semantics",
    }
    if set(value) != required:
        raise ModelCompatibilityFactsError("Malformed frozen compatibility-facts record")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "model-compatibility-facts"
    ):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts identity")

    roles = value["roles"]
    candidate = value["candidate"]
    recipient = value["recipient"]
    dimensions = value["dimensions"]
    evidence = value["evidence"]
    semantics = value["semantics"]
    if not all(isinstance(item, dict) for item in (roles, candidate, recipient, dimensions, evidence, semantics)):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts sections")

    if (
        set(roles) != {"candidate", "recipient"}
        or roles["candidate"] != "effective-search-model-submitted-to-or-prepared-for-Phaser"
        or roles["recipient"] != "frozen-AutoMR-intent-for-this-dataset"
    ):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts roles")
    if set(candidate) != {
        "source_model_sha256", "effective_model_sha256", "provider", "mode",
        "polymer_residue_count", "chains",
    }:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts candidate")
    for key in ("source_model_sha256", "effective_model_sha256"):
        if (
            not isinstance(candidate[key], str)
            or re.fullmatch(r"[0-9a-f]{64}", candidate[key]) is None
        ):
            raise ModelCompatibilityFactsError("Malformed compatibility-facts model hash")
    if candidate["mode"] not in {"standard", "nonstandard"}:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts candidate mode")
    if (
        type(candidate["polymer_residue_count"]) is not int
        or candidate["polymer_residue_count"] < 0
        or not isinstance(candidate["chains"], list)
    ):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts candidate inventory")
    counted = 0
    seen_chains: set[str] = set()
    for chain in candidate["chains"]:
        if (
            not isinstance(chain, dict)
            or set(chain) != {"chain", "residue_count", "residue_ids"}
            or not isinstance(chain["chain"], str)
            or not chain["chain"]
            or chain["chain"] in seen_chains
            or type(chain["residue_count"]) is not int
            or chain["residue_count"] < 0
            or not isinstance(chain["residue_ids"], list)
            or len(chain["residue_ids"]) != chain["residue_count"]
            or not all(isinstance(resid, str) and resid for resid in chain["residue_ids"])
        ):
            raise ModelCompatibilityFactsError("Malformed compatibility-facts chain inventory")
        seen_chains.add(chain["chain"])
        counted += chain["residue_count"]
    if counted != candidate["polymer_residue_count"]:
        raise ModelCompatibilityFactsError("Inconsistent compatibility-facts residue count")
    provider = candidate["provider"]
    if (
        not isinstance(provider, dict)
        or set(provider) != {
            "kind", "selection", "location", "selector", "declared_frame",
        }
        or any(
            provider[key] is not None and not isinstance(provider[key], str)
            for key in provider
        )
    ):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts provider")

    if set(recipient) != {"mode", "frame", "symmetry_class", "mr_copies"}:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts recipient")
    if recipient["mode"] not in {"standard", "nonstandard"}:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts recipient mode")
    if recipient["mode"] != candidate["mode"]:
        raise ModelCompatibilityFactsError("Candidate and recipient modes disagree")
    if recipient["frame"] is not None and not isinstance(recipient["frame"], str):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts recipient frame")
    if recipient["symmetry_class"] is not None and not isinstance(recipient["symmetry_class"], str):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts symmetry class")
    if recipient["mr_copies"] is not None and (
        type(recipient["mr_copies"]) is not int or recipient["mr_copies"] <= 0
    ):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts MR copy count")

    expected_dimensions = {
        "frame_identity", "construct_family", "site_set", "residue_identity",
        "chirality", "terminal_phosphate_chemistry", "backbone_chemistry",
        "symmetry_and_copy_number",
    }
    if set(dimensions) != expected_dimensions:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts dimensions")
    for name in expected_dimensions:
        if not isinstance(dimensions[name], dict):
            raise ModelCompatibilityFactsError(f"Malformed compatibility-facts {name}")
        _validate_relation(dimensions[name].get("relation"), f"compatibility-facts {name}")

    frame = dimensions["frame_identity"]
    if set(frame) != {
        "candidate_declared_frame", "recipient_frame", "relation", "basis",
    }:
        raise ModelCompatibilityFactsError("Malformed frame-identity facts")
    if (
        frame["candidate_declared_frame"] != provider["declared_frame"]
        or frame["recipient_frame"] != recipient["frame"]
        or not isinstance(frame["basis"], str)
        or not frame["basis"]
    ):
        raise ModelCompatibilityFactsError("Inconsistent frame-identity facts")
    expected_frame_relation = _frame_relation(
        frame["candidate_declared_frame"], frame["recipient_frame"]
    )
    if frame["relation"] != expected_frame_relation:
        raise ModelCompatibilityFactsError("Inconsistent frame-identity relation")

    site_set = dimensions["site_set"]
    if set(site_set) != {
        "relation", "basis", "missing_sites", "unexpected_sites",
    }:
        raise ModelCompatibilityFactsError("Malformed site-set facts")
    if not all(
        isinstance(values, list) and all(isinstance(site, str) for site in values)
        for values in (site_set["missing_sites"], site_set["unexpected_sites"])
    ) or not isinstance(site_set["basis"], str) or not site_set["basis"]:
        raise ModelCompatibilityFactsError("Malformed site-set inventory")
    if site_set["basis"] == "no-complete-explicit-residue-target":
        if (
            site_set["relation"] != "UNKNOWN"
            or site_set["missing_sites"]
            or site_set["unexpected_sites"]
        ):
            raise ModelCompatibilityFactsError("Inconsistent unknown site-set facts")
    elif site_set["basis"] == "complete-explicit-residue-target":
        expected_site_relation = (
            "SAME"
            if not site_set["missing_sites"] and not site_set["unexpected_sites"]
            else "DIFFERENT"
        )
        if site_set["relation"] != expected_site_relation:
            raise ModelCompatibilityFactsError("Inconsistent site-set relation")
    else:
        raise ModelCompatibilityFactsError("Unsupported site-set fact basis")

    residue = dimensions["residue_identity"]
    if set(residue) != {
        "relation", "basis", "compared_site_count", "mismatch_count",
    } or any(
        type(residue[key]) is not int or residue[key] < 0
        for key in ("compared_site_count", "mismatch_count")
    ) or residue["mismatch_count"] > residue["compared_site_count"] or not isinstance(
        residue["basis"], str
    ) or not residue["basis"]:
        raise ModelCompatibilityFactsError("Malformed residue-identity facts")
    if residue["basis"] == "no-complete-explicit-residue-target":
        if (
            residue["relation"] != "UNKNOWN"
            or residue["compared_site_count"] != 0
            or residue["mismatch_count"] != 0
        ):
            raise ModelCompatibilityFactsError("Inconsistent unknown residue-identity facts")
    elif residue["basis"] == "source-search-model-before-any-mirror-transform":
        if site_set["relation"] == "SAME":
            expected_identity_relation = (
                "SAME" if residue["mismatch_count"] == 0 else "DIFFERENT"
            )
        else:
            expected_identity_relation = (
                "PARTIAL" if residue["compared_site_count"] else "UNKNOWN"
            )
        if residue["relation"] != expected_identity_relation:
            raise ModelCompatibilityFactsError("Inconsistent residue-identity relation")
    else:
        raise ModelCompatibilityFactsError("Unsupported residue-identity fact basis")

    chirality = dimensions["chirality"]
    if set(chirality) != {
        "candidate_absolute_chirality", "recipient_absolute_chirality",
        "mirror_transform_applied", "relation", "basis",
    } or type(chirality["mirror_transform_applied"]) is not bool:
        raise ModelCompatibilityFactsError("Malformed chirality facts")
    if (
        chirality["candidate_absolute_chirality"] is not None
        or chirality["recipient_absolute_chirality"] is not None
        or chirality["relation"] != "UNKNOWN"
        or not isinstance(chirality["basis"], str)
        or not chirality["basis"]
    ):
        raise ModelCompatibilityFactsError("Current schema cannot claim absolute chirality")

    terminal = dimensions["terminal_phosphate_chemistry"]
    if set(terminal) != {
        "recipient_sites", "recipient_intent_source",
        "candidate_coordinate_evidence", "relation",
    } or not isinstance(terminal["recipient_sites"], list) or not all(
        isinstance(site, str) for site in terminal["recipient_sites"]
    ) or not isinstance(terminal["recipient_intent_source"], str) or not terminal[
        "recipient_intent_source"
    ] or terminal["candidate_coordinate_evidence"] != "NOT_ASSESSED" or terminal["relation"] != "UNKNOWN":
        raise ModelCompatibilityFactsError("Malformed terminal-phosphate facts")

    backbone = dimensions["backbone_chemistry"]
    if set(backbone) != {
        "recipient_default", "recipient_site_overrides",
        "experimental_passthrough_sites", "recipient_allow_unreviewed",
        "candidate_coordinate_evidence", "relation",
    } or not isinstance(backbone["recipient_default"], str) or not isinstance(
        backbone["recipient_site_overrides"], dict
    ) or not all(
        isinstance(site, str) and isinstance(mode, str)
        for site, mode in backbone["recipient_site_overrides"].items()
    ) or not isinstance(backbone["experimental_passthrough_sites"], list) or not all(
        isinstance(site, str) for site in backbone["experimental_passthrough_sites"]
    ) or type(backbone["recipient_allow_unreviewed"]) is not bool or backbone[
        "candidate_coordinate_evidence"
    ] != "NOT_ASSESSED" or backbone["relation"] != "UNKNOWN":
        raise ModelCompatibilityFactsError("Malformed backbone-chemistry facts")
    expected_passthrough = sorted(
        site
        for site, mode in backbone["recipient_site_overrides"].items()
        if mode == "experimental_passthrough"
    )
    if backbone["experimental_passthrough_sites"] != expected_passthrough:
        raise ModelCompatibilityFactsError("Inconsistent backbone passthrough facts")

    symmetry = dimensions["symmetry_and_copy_number"]
    if set(symmetry) != {
        "recipient_symmetry_class", "recipient_mr_copies",
        "candidate_coordinate_claim", "relation", "basis",
    } or symmetry["candidate_coordinate_claim"] is not None or symmetry["relation"] != "UNKNOWN" or not isinstance(
        symmetry["basis"], str
    ) or not symmetry["basis"]:
        raise ModelCompatibilityFactsError("Malformed symmetry/copy-number facts")
    if (
        symmetry["recipient_symmetry_class"] != recipient["symmetry_class"]
        or symmetry["recipient_mr_copies"] != recipient["mr_copies"]
    ):
        raise ModelCompatibilityFactsError("Inconsistent symmetry/copy-number facts")

    family = dimensions["construct_family"]
    if set(family) != {
        "candidate_declared_family", "recipient_reference", "relation", "basis",
    } or family["candidate_declared_family"] is not None or family["relation"] != "UNKNOWN" or not isinstance(
        family["basis"], str
    ) or not family["basis"]:
        raise ModelCompatibilityFactsError("Current providers do not declare construct family")
    reference = family["recipient_reference"]
    if reference is not None:
        if (
            not isinstance(reference, dict)
            or set(reference) != {"id", "version", "content_sha256"}
            or not isinstance(reference["id"], str)
            or not reference["id"]
            or not isinstance(reference["version"], str)
            or not reference["version"]
            or not isinstance(reference["content_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", reference["content_sha256"]) is None
        ):
            raise ModelCompatibilityFactsError("Malformed construct-family recipient reference")

    if set(evidence) != {"search_model_comparison"}:
        raise ModelCompatibilityFactsError("Malformed compatibility-facts evidence")
    comparison = evidence["search_model_comparison"]
    if comparison is not None and not isinstance(comparison, dict):
        raise ModelCompatibilityFactsError("Malformed compatibility-facts comparison evidence")

    if set(semantics) != {
        "descriptive_only", "score", "overall_compatibility",
        "donor_eligibility", "automatic_reuse_authorized",
    } or semantics["descriptive_only"] is not True or any(
        semantics[key] is not None
        for key in ("score", "overall_compatibility", "donor_eligibility")
    ) or semantics["automatic_reuse_authorized"] is not False:
        raise ModelCompatibilityFactsError("Compatibility facts must not contain a verdict or score")
    return value


def freeze_model_compatibility_facts(
    facts: Mapping[str, object],
    run: Path,
) -> dict[str, object]:
    validated = _validated_record(dict(facts))
    data = (
        json.dumps(validated, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    path = run / "Model" / "model_compatibility_facts.json"
    with path.open("xb") as handle:
        handle.write(data)
    return {
        "schema_version": 1,
        "kind": "frozen-model-compatibility-facts",
        "artifact": {
            **artifact_reference(path, run),
            "sha256": sha256(data).hexdigest(),
            "size": len(data),
        },
    }


def load_model_compatibility_facts(
    report: Mapping[str, object],
    run: Path,
) -> dict[str, object] | None:
    frozen = report.get("model_compatibility_facts")
    if frozen is None:
        return None
    if (
        not isinstance(frozen, Mapping)
        or set(frozen) != {"schema_version", "kind", "artifact"}
        or type(frozen.get("schema_version")) is not int
        or frozen["schema_version"] != 1
        or frozen.get("kind") != "frozen-model-compatibility-facts"
        or not isinstance(frozen.get("artifact"), Mapping)
    ):
        raise ModelCompatibilityFactsError(
            "Malformed frozen model-compatibility facts"
        )
    artifact = frozen["artifact"]
    if (
        artifact.get("anchor") != "run"
        or not isinstance(artifact.get("relative_path"), str)
        or not isinstance(artifact.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None
        or type(artifact.get("size")) is not int
        or artifact["size"] <= 0
    ):
        raise ModelCompatibilityFactsError(
            "Malformed model-compatibility facts artifact"
        )
    try:
        path = resolve_artifact_path(artifact, run)
        if path is None:
            raise ModelCompatibilityFactsError(
                "Frozen model-compatibility facts are missing or failed checksum validation"
            )
        path.resolve().relative_to(run.resolve())
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ModelCompatibilityFactsError(
            f"Could not read frozen model-compatibility facts: {exc}"
        ) from exc
    if (
        len(data) != artifact["size"]
        or sha256(data).hexdigest() != artifact["sha256"]
    ):
        raise ModelCompatibilityFactsError(
            "Frozen model-compatibility facts changed while being read"
        )
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ModelCompatibilityFactsError(
            f"Could not decode frozen model-compatibility facts: {exc}"
        ) from exc
    facts = _validated_record(value)

    inputs = report.get("inputs")
    assessment = report.get("model_assessment")
    if not isinstance(inputs, Mapping) or not isinstance(assessment, Mapping):
        raise ModelCompatibilityFactsError(
            "Run report lacks model provenance required by compatibility facts"
        )
    if facts["candidate"]["source_model_sha256"] != inputs.get("model_sha256"):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with the source-model checksum"
        )
    if facts["candidate"]["effective_model_sha256"] != assessment.get("sha256"):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with the effective-model checksum"
        )
    if facts["candidate"]["mode"] != report.get("mode"):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with the run mode"
        )
    expected_provider = _provider_summary(inputs.get("model_provider"))
    if facts["candidate"]["provider"] != expected_provider:
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with model-provider provenance"
        )
    expected_ids = assessment.get("polymer_residue_ids_by_chain")
    if not isinstance(expected_ids, Mapping):
        raise ModelCompatibilityFactsError(
            "Run model assessment lacks polymer residue inventory"
        )
    expected_chains = [
        {
            "chain": chain,
            "residue_count": len(residue_ids),
            "residue_ids": list(residue_ids),
        }
        for chain, residue_ids in expected_ids.items()
        if isinstance(chain, str) and isinstance(residue_ids, list)
    ]
    if (
        facts["candidate"]["chains"] != expected_chains
        or facts["candidate"]["polymer_residue_count"]
        != assessment.get("polymer_residue_count")
    ):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with candidate chain inventory"
        )
    frame = report.get("frame")
    frame_name = frame.get("name") if isinstance(frame, Mapping) else None
    if facts["recipient"]["frame"] != frame_name:
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with the recipient frame"
        )
    if facts["dimensions"]["chirality"]["mirror_transform_applied"] != inputs.get("mirror"):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with the mirror-transform intent"
        )
    symmetry_report = report.get("symmetry")
    expected_symmetry_class = None
    expected_mr_copies = None
    if isinstance(symmetry_report, Mapping):
        evidence_report = symmetry_report.get("evidence")
        if isinstance(evidence_report, Mapping):
            expected_symmetry_class = evidence_report.get("normalized_class")
        copies = symmetry_report.get("mr_copies")
        if type(copies) is int:
            expected_mr_copies = copies
    if (
        facts["recipient"]["symmetry_class"] != expected_symmetry_class
        or facts["recipient"]["mr_copies"] != expected_mr_copies
    ):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with recipient symmetry/copy-number evidence"
        )
    plan = report.get("post_mr_plan")
    if not isinstance(plan, Mapping):
        raise ModelCompatibilityFactsError(
            "Run report lacks PostMR intent required by compatibility facts"
        )
    if facts["dimensions"]["terminal_phosphate_chemistry"]["recipient_sites"] != plan.get(
        "allow_op3_sites", []
    ):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with terminal-phosphate intent"
        )
    plan_phosphate = plan.get("phosphate_intent")
    expected_phosphate_source = (
        plan_phosphate.get("source")
        if isinstance(plan_phosphate, Mapping)
        else ("legacy" if plan.get("allow_op3_sites") else "none")
    )
    if facts["dimensions"]["terminal_phosphate_chemistry"]["recipient_intent_source"] != expected_phosphate_source:
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with terminal-phosphate provenance"
        )
    plan_backbone = plan.get("backbone_policy")
    if not isinstance(plan_backbone, Mapping):
        raise ModelCompatibilityFactsError(
            "Run report lacks backbone policy required by compatibility facts"
        )
    backbone_facts = facts["dimensions"]["backbone_chemistry"]
    if (
        backbone_facts["recipient_default"] != plan_backbone.get("default")
        or backbone_facts["recipient_site_overrides"] != plan_backbone.get("sites")
        or backbone_facts["experimental_passthrough_sites"]
        != plan_backbone.get("experimental_passthrough_sites")
        or backbone_facts["recipient_allow_unreviewed"]
        != plan_backbone.get("allow_unreviewed")
    ):
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with backbone chemistry intent"
        )

    comparison_ref = facts["evidence"]["search_model_comparison"]
    report_comparison = report.get("search_model_comparison")
    if comparison_ref != report_comparison:
        raise ModelCompatibilityFactsError(
            "Compatibility facts disagree with search-model comparison provenance"
        )
    if comparison_ref is not None:
        try:
            load_search_model_comparison(
                {"search_model_comparison": comparison_ref},
                run,
            )
        except SearchModelComparisonError as exc:
            raise ModelCompatibilityFactsError(
                f"Compatibility-facts comparison evidence failed verification: {exc}"
            ) from exc
    return facts


__all__ = [
    "ModelCompatibilityFactsError",
    "build_model_compatibility_facts",
    "freeze_model_compatibility_facts",
    "load_model_compatibility_facts",
]
