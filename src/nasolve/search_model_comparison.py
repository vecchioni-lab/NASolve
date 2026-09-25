"""Descriptive search-model versus intended-target provenance.

This module records literal coordinate/target differences. It does not rank
models, establish reuse eligibility, or authorize any PostMR transformation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

from .model_assessment import (
    ModelAssessment,
    ModelAssessmentError,
    literal_polymer_identity_inventory,
)
from .run_context import artifact_reference, resolve_artifact_path


class SearchModelComparisonError(RuntimeError):
    """Raised when comparison provenance cannot be built or verified."""


def _target_rows(target: Mapping[str, object]) -> list[Mapping[str, object]]:
    if (
        type(target.get("schema_version")) is not int
        or target.get("schema_version") != 1
        or target.get("kind") != "sequence-family-target"
        or not isinstance(target.get("sites"), list)
    ):
        raise SearchModelComparisonError("Unsupported complete residue target")
    rows = target["sites"]
    seen: set[str] = set()
    checked: list[Mapping[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise SearchModelComparisonError("Malformed complete residue target row")
        site = row.get("site")
        code = row.get("residue_code")
        source = row.get("source")
        if (
            not isinstance(site, str)
            or site.count(":") != 1
            or not isinstance(code, str)
            or re.fullmatch(r"[A-Z0-9]{1,5}", code) is None
            or not isinstance(source, str)
            or not source
            or site in seen
        ):
            raise SearchModelComparisonError("Malformed complete residue target row")
        seen.add(site)
        checked.append(row)
    return checked


def compare_search_model_to_target(
    assessment: ModelAssessment,
    target: Mapping[str, object],
) -> dict[str, object]:
    """Compare literal assessed identities with one complete explicit target."""
    try:
        inventory = literal_polymer_identity_inventory(assessment)
    except ModelAssessmentError as exc:
        raise SearchModelComparisonError(str(exc)) from exc
    rows = _target_rows(target)
    target_by_site = {row["site"]: row for row in rows}
    observed = set(inventory)
    expected = set(target_by_site)
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    common = [row["site"] for row in rows if row["site"] in observed]

    mismatches = []
    for site in common:
        row = target_by_site[site]
        before = inventory[site]
        after = row["residue_code"]
        if before != after:
            mismatches.append({
                "site": site,
                "model_residue_code": before,
                "target_residue_code": after,
                "target_source": row["source"],
                "expected_postmr_correction": True,
                "route_validated": False,
            })

    status = (
        "SITE_CORRESPONDENCE_DIFFERENCE"
        if missing or unexpected
        else "IDENTITY_DIFFERENCES"
        if mismatches
        else "EXACT"
    )
    chains = [
        {
            "chain": chain,
            "residue_count": len(residue_ids),
            "residue_ids": list(residue_ids),
        }
        for chain, residue_ids in assessment.polymer_residue_ids_by_chain.items()
    ]
    return {
        "schema_version": 1,
        "kind": "search-model-target-comparison",
        "scope": "complete-residue-target",
        "status": status,
        "model": {
            "sha256": assessment.sha256,
            "polymer_residue_count": assessment.polymer_residue_count,
            "chain_count": len(chains),
            "chains": chains,
        },
        "target": {
            "kind": target["kind"],
            "reference": target.get("reference"),
            "site_count": len(rows),
        },
        "correspondence": {
            "exact_site_set": not missing and not unexpected,
            "missing_sites": missing,
            "unexpected_sites": unexpected,
        },
        "identity": {
            "compared_site_count": len(common),
            "match_count": len(common) - len(mismatches),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
        "semantics": {
            "descriptive_only": True,
            "expected_postmr_correction": (
                "target identity differs from the search model; mutation-route "
                "availability is not asserted by this record"
            ),
        },
    }


def _validated_comparison_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SearchModelComparisonError(
            "Frozen search-model comparison is not an object"
        )
    required = {
        "schema_version", "kind", "scope", "status", "model", "target",
        "correspondence", "identity", "semantics",
    }
    if set(value) != required:
        raise SearchModelComparisonError(
            "Malformed frozen search-model comparison record"
        )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "search-model-target-comparison"
        or value["scope"] != "complete-residue-target"
        or value["status"] not in {
            "EXACT", "IDENTITY_DIFFERENCES", "SITE_CORRESPONDENCE_DIFFERENCE",
        }
    ):
        raise SearchModelComparisonError(
            "Malformed frozen search-model comparison identity"
        )
    model = value["model"]
    target = value["target"]
    correspondence = value["correspondence"]
    identity = value["identity"]
    semantics = value["semantics"]
    if (
        not isinstance(model, dict)
        or set(model) != {
            "sha256", "polymer_residue_count", "chain_count", "chains",
        }
        or not isinstance(model["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", model["sha256"]) is None
        or type(model["polymer_residue_count"]) is not int
        or model["polymer_residue_count"] < 0
        or type(model["chain_count"]) is not int
        or model["chain_count"] < 0
        or not isinstance(model["chains"], list)
        or len(model["chains"]) != model["chain_count"]
    ):
        raise SearchModelComparisonError(
            "Malformed search-model comparison model inventory"
        )
    for chain in model["chains"]:
        if (
            not isinstance(chain, dict)
            or set(chain) != {"chain", "residue_count", "residue_ids"}
            or not isinstance(chain["chain"], str)
            or not chain["chain"]
            or type(chain["residue_count"]) is not int
            or chain["residue_count"] < 0
            or not isinstance(chain["residue_ids"], list)
            or len(chain["residue_ids"]) != chain["residue_count"]
            or not all(isinstance(item, str) and item for item in chain["residue_ids"])
        ):
            raise SearchModelComparisonError(
                "Malformed search-model comparison chain inventory"
            )
    if (
        not isinstance(target, dict)
        or set(target) != {"kind", "reference", "site_count"}
        or target["kind"] != "sequence-family-target"
        or type(target["site_count"]) is not int
        or target["site_count"] < 0
    ):
        raise SearchModelComparisonError(
            "Malformed search-model comparison target inventory"
        )
    if (
        not isinstance(correspondence, dict)
        or set(correspondence) != {
            "exact_site_set", "missing_sites", "unexpected_sites",
        }
        or type(correspondence["exact_site_set"]) is not bool
        or not isinstance(correspondence["missing_sites"], list)
        or not isinstance(correspondence["unexpected_sites"], list)
        or not all(
            isinstance(site, str)
            for site in (
                correspondence["missing_sites"]
                + correspondence["unexpected_sites"]
            )
        )
    ):
        raise SearchModelComparisonError(
            "Malformed search-model comparison correspondence"
        )
    if (
        not isinstance(identity, dict)
        or set(identity) != {
            "compared_site_count", "match_count", "mismatch_count", "mismatches",
        }
        or any(
            type(identity[field]) is not int or identity[field] < 0
            for field in ("compared_site_count", "match_count", "mismatch_count")
        )
        or not isinstance(identity["mismatches"], list)
        or len(identity["mismatches"]) != identity["mismatch_count"]
        or identity["match_count"] + identity["mismatch_count"]
        != identity["compared_site_count"]
    ):
        raise SearchModelComparisonError(
            "Malformed search-model comparison identity counts"
        )
    for mismatch in identity["mismatches"]:
        if (
            not isinstance(mismatch, dict)
            or set(mismatch) != {
                "site", "model_residue_code", "target_residue_code",
                "target_source", "expected_postmr_correction",
                "route_validated",
            }
            or not all(
                isinstance(mismatch[field], str) and mismatch[field]
                for field in (
                    "site", "model_residue_code", "target_residue_code",
                    "target_source",
                )
            )
            or mismatch["expected_postmr_correction"] is not True
            or mismatch["route_validated"] is not False
        ):
            raise SearchModelComparisonError(
                "Malformed search-model comparison mismatch"
            )
    if (
        not isinstance(semantics, dict)
        or set(semantics) != {
            "descriptive_only", "expected_postmr_correction",
        }
        or semantics["descriptive_only"] is not True
        or not isinstance(semantics["expected_postmr_correction"], str)
    ):
        raise SearchModelComparisonError(
            "Malformed search-model comparison semantics"
        )
    if correspondence["exact_site_set"] != (
        not correspondence["missing_sites"]
        and not correspondence["unexpected_sites"]
    ):
        raise SearchModelComparisonError(
            "Inconsistent search-model correspondence summary"
        )
    expected_status = (
        "SITE_CORRESPONDENCE_DIFFERENCE"
        if not correspondence["exact_site_set"]
        else "IDENTITY_DIFFERENCES"
        if identity["mismatch_count"]
        else "EXACT"
    )
    if value["status"] != expected_status:
        raise SearchModelComparisonError(
            "Inconsistent search-model comparison status"
        )
    if target["site_count"] != (
        identity["compared_site_count"] + len(correspondence["missing_sites"])
    ):
        raise SearchModelComparisonError(
            "Inconsistent search-model comparison target counts"
        )
    return value


def freeze_search_model_comparison(
    comparison: Mapping[str, object],
    run: Path,
) -> dict[str, object]:
    """Freeze one comparison artifact beneath an already allocated run."""
    data = (
        json.dumps(comparison, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    path = run / "Model" / "search_model_comparison.json"
    with path.open("xb") as handle:
        handle.write(data)
    return {
        "schema_version": 1,
        "kind": "frozen-search-model-comparison",
        "artifact": {
            **artifact_reference(path, run),
            "sha256": sha256(data).hexdigest(),
            "size": len(data),
        },
    }


def load_search_model_comparison(
    report: Mapping[str, object],
    run: Path,
) -> dict[str, object] | None:
    """Load only a checksum-verified run-local comparison artifact."""
    frozen = report.get("search_model_comparison")
    if frozen is None:
        return None
    if (
        not isinstance(frozen, Mapping)
        or set(frozen) != {"schema_version", "kind", "artifact"}
        or type(frozen.get("schema_version")) is not int
        or frozen["schema_version"] != 1
        or frozen.get("kind") != "frozen-search-model-comparison"
        or not isinstance(frozen.get("artifact"), Mapping)
    ):
        raise SearchModelComparisonError("Malformed frozen search-model comparison")
    artifact = frozen["artifact"]
    if (
        artifact.get("anchor") != "run"
        or not isinstance(artifact.get("relative_path"), str)
        or not isinstance(artifact.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None
        or type(artifact.get("size")) is not int
        or artifact["size"] <= 0
    ):
        raise SearchModelComparisonError("Malformed search-model comparison artifact")
    try:
        path = resolve_artifact_path(artifact, run)
        if path is None:
            raise SearchModelComparisonError(
                "Frozen search-model comparison is missing or failed checksum validation"
            )
        path.resolve().relative_to(run.resolve())
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise SearchModelComparisonError(
            f"Could not read frozen search-model comparison: {exc}"
        ) from exc
    if (
        len(data) != artifact["size"]
        or sha256(data).hexdigest() != artifact["sha256"]
    ):
        raise SearchModelComparisonError(
            "Frozen search-model comparison changed while being read"
        )
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise SearchModelComparisonError(
            f"Could not decode frozen search-model comparison: {exc}"
        ) from exc
    return _validated_comparison_record(value)


__all__ = [
    "SearchModelComparisonError",
    "compare_search_model_to_target",
    "freeze_search_model_comparison",
    "load_search_model_comparison",
]
