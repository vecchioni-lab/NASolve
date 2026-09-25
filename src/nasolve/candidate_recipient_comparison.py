"""Descriptive checkpoint-candidate versus recipient-run comparison.

This is a pure/read-only bridge toward Campaign Doctor.  It compares verified
Fern donor provenance with the recipient's own frozen AutoMR intent.  It never
selects a donor, ranks candidates, launches MR, or authorizes reuse.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .checkpoint_candidate import (
    CheckpointCandidateError,
    describe_checkpoint_candidate,
)
from .model_compatibility import (
    ModelCompatibilityFactsError,
    load_model_compatibility_facts,
)
from .run_context import dataset_directory
from .sequence_family import load_frozen_sequence_family
from .sequence_reference import SequenceReferenceError


class CandidateRecipientComparisonError(RuntimeError):
    """Verified donor/recipient provenance cannot be compared safely."""


def _relation(left: object, right: object) -> str:
    if left is None or right is None:
        return "UNKNOWN"
    return "SAME" if left == right else "DIFFERENT"


def _run_report(run: Path) -> dict[str, object]:
    path = run / "report.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateRecipientComparisonError(
            f"Could not read recipient run report {path}: {exc}"
        ) from exc
    if not isinstance(value, dict) or value.get("workflow") != "automr":
        raise CandidateRecipientComparisonError(
            "Recipient comparison requires a NASolve AutoMR run"
        )
    return value


def _inventory(candidate: Mapping[str, object]) -> dict[str, str]:
    model = candidate.get("model")
    assessment = model.get("assessment") if isinstance(model, Mapping) else None
    identities = (
        assessment.get("residue_identities")
        if isinstance(assessment, Mapping)
        else None
    )
    if not isinstance(identities, list):
        raise CandidateRecipientComparisonError(
            "Fern donor descriptor has no literal residue inventory"
        )
    result: dict[str, str] = {}
    for row in identities:
        if (
            not isinstance(row, Mapping)
            or set(row) != {"site", "residue_code"}
            or not isinstance(row.get("site"), str)
            or not row["site"]
            or not isinstance(row.get("residue_code"), str)
            or not row["residue_code"]
            or row["site"] in result
        ):
            raise CandidateRecipientComparisonError(
                "Fern donor descriptor has malformed residue identities"
            )
        result[row["site"]] = row["residue_code"]
    return result


def _target_inventory(family) -> dict[str, str]:
    rows = family.target.get("sites")
    if not isinstance(rows, list):
        raise CandidateRecipientComparisonError(
            "Recipient frozen target has no explicit sites"
        )
    result: dict[str, str] = {}
    for row in rows:
        if (
            not isinstance(row, Mapping)
            or not isinstance(row.get("site"), str)
            or not isinstance(row.get("residue_code"), str)
            or row["site"] in result
        ):
            raise CandidateRecipientComparisonError(
                "Recipient frozen target has malformed site identities"
            )
        result[row["site"]] = row["residue_code"]
    return result


def compare_checkpoint_to_recipient(
    donor_run_directory: Path,
    recipient_run_directory: Path,
    *,
    donor_checkpoint: str | None = None,
) -> dict[str, object]:
    """Compare verified donor checkpoint facts to frozen recipient intent only."""
    try:
        donor = describe_checkpoint_candidate(
            donor_run_directory,
            donor_checkpoint,
        )
    except CheckpointCandidateError as exc:
        raise CandidateRecipientComparisonError(
            f"Donor checkpoint provenance failed validation: {exc}"
        ) from exc

    donor_source = donor.get("source")
    donor_context = donor.get("run_context")
    donor_semantics = donor.get("semantics")
    if (
        donor.get("schema_version") != 1
        or donor.get("kind") != "checkpoint-model-candidate"
        or not isinstance(donor_source, Mapping)
        or not isinstance(donor_context, Mapping)
        or not isinstance(donor_semantics, Mapping)
        or donor_semantics.get("descriptive_only") is not True
        or donor_semantics.get("donor_eligibility") is not None
        or donor_semantics.get("automatic_reuse_authorized") is not False
    ):
        raise CandidateRecipientComparisonError(
            "Fern donor descriptor violates the non-decision contract"
        )

    recipient_run = recipient_run_directory.expanduser().resolve()
    recipient_report = _run_report(recipient_run)
    try:
        recipient_facts = load_model_compatibility_facts(
            recipient_report,
            recipient_run,
        )
        recipient_family = load_frozen_sequence_family(
            recipient_report,
            recipient_run,
        )
    except (ModelCompatibilityFactsError, SequenceReferenceError) as exc:
        raise CandidateRecipientComparisonError(
            f"Recipient frozen provenance failed validation: {exc}"
        ) from exc

    donor_inventory = _inventory(donor)
    if recipient_family is None:
        site_dimension = {
            "relation": "UNKNOWN",
            "basis": "recipient-has-no-complete-explicit-residue-target",
            "missing_sites": [],
            "unexpected_sites": [],
        }
        identity_dimension = {
            "relation": "UNKNOWN",
            "basis": "recipient-has-no-complete-explicit-residue-target",
            "compared_site_count": 0,
            "mismatch_count": 0,
            "mismatches": [],
        }
        recipient_reference = None
    else:
        target = _target_inventory(recipient_family)
        donor_sites = set(donor_inventory)
        target_sites = set(target)
        missing = sorted(target_sites - donor_sites)
        unexpected = sorted(donor_sites - target_sites)
        common = sorted(donor_sites & target_sites)
        mismatches = [
            {
                "site": site,
                "donor": donor_inventory[site],
                "recipient": target[site],
            }
            for site in common
            if donor_inventory[site] != target[site]
        ]
        exact_sites = not missing and not unexpected
        site_dimension = {
            "relation": "SAME" if exact_sites else "DIFFERENT",
            "basis": "verified-donor-literal-inventory-vs-frozen-recipient-target",
            "missing_sites": missing,
            "unexpected_sites": unexpected,
        }
        identity_dimension = {
            "relation": (
                "SAME"
                if exact_sites and not mismatches
                else "DIFFERENT"
                if exact_sites
                else "PARTIAL"
                if common
                else "UNKNOWN"
            ),
            "basis": "verified-donor-literal-inventory-vs-frozen-recipient-target",
            "compared_site_count": len(common),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }
        recipient_reference = {
            "id": recipient_family.reference.identifier,
            "version": recipient_family.reference.version,
            "content_sha256": recipient_family.reference.content_sha256,
        }

    donor_family = donor_context.get("sequence_family")
    donor_reference = (
        donor_family.get("reference")
        if isinstance(donor_family, Mapping)
        and isinstance(donor_family.get("reference"), Mapping)
        else None
    )

    recipient_frame = None
    recipient_mode = None
    recipient_symmetry = None
    recipient_copies = None
    if isinstance(recipient_facts, Mapping):
        recipient = recipient_facts.get("recipient")
        if isinstance(recipient, Mapping):
            recipient_frame = recipient.get("frame")
            recipient_mode = recipient.get("mode")
            recipient_symmetry = recipient.get("symmetry_class")
            recipient_copies = recipient.get("mr_copies")
    if recipient_mode is None:
        raw_mode = recipient_report.get("mode")
        recipient_mode = raw_mode if isinstance(raw_mode, str) else None
    if recipient_frame is None:
        frame = recipient_report.get("frame")
        if isinstance(frame, Mapping):
            recipient_frame = frame.get("name")

    if recipient_symmetry is None or recipient_copies is None:
        symmetry_report = recipient_report.get("symmetry")
        if isinstance(symmetry_report, Mapping):
            evidence = symmetry_report.get("evidence")
            if recipient_symmetry is None and isinstance(evidence, Mapping):
                recipient_symmetry = evidence.get("normalized_class")
            copies = symmetry_report.get("mr_copies")
            if recipient_copies is None and type(copies) is int:
                recipient_copies = copies

    donor_frame = donor_context.get("frame")
    donor_mode = donor_context.get("mode")
    donor_mirror = donor_context.get("mirror_transform_applied")
    recipient_inputs = recipient_report.get("inputs")
    recipient_mirror = (
        recipient_inputs.get("mirror")
        if isinstance(recipient_inputs, Mapping)
        else None
    )

    donor_reference_identity = (
        {
            "id": donor_reference.get("id"),
            "version": donor_reference.get("version"),
            "content_sha256": donor_reference.get("content_sha256"),
        }
        if isinstance(donor_reference, Mapping)
        else None
    )
    recipient_reference_identity = (
        dict(recipient_reference)
        if isinstance(recipient_reference, Mapping)
        else None
    )

    donor_model = donor.get("model")
    donor_artifact = (
        donor_model.get("artifact")
        if isinstance(donor_model, Mapping)
        else None
    )
    if not isinstance(donor_artifact, Mapping):
        raise CandidateRecipientComparisonError(
            "Fern donor descriptor has no verified model artifact"
        )

    return {
        "schema_version": 1,
        "kind": "checkpoint-recipient-comparison",
        "donor": {
            "dataset_name": donor_source.get("dataset_name"),
            "dataset_locator": str(
                dataset_directory(
                    donor_run_directory.expanduser().resolve()
                ).resolve()
            ),
            "run_id": donor_source.get("run_id"),
            "run_locator": str(
                donor_run_directory.expanduser().resolve()
            ),
            "checkpoint_id": donor_source.get("checkpoint_id"),
            "status": donor_source.get("status"),
            "usable": donor_source.get("usable"),
            "locally_reusable": donor_source.get("locally_reusable"),
            "model_artifact": dict(donor_artifact),
        },
        "recipient": {
            "dataset_name": dataset_directory(recipient_run).name,
            "dataset_locator": str(
                dataset_directory(recipient_run).resolve()
            ),
            "run_id": recipient_run.name,
            "run_locator": str(recipient_run),
            "mode": recipient_mode,
            "frame": recipient_frame,
            "symmetry_class": recipient_symmetry,
            "mr_copies": recipient_copies,
            "target_reference": recipient_reference,
        },
        "dimensions": {
            "mode_context": {
                "donor_source_mode": donor_mode,
                "recipient_mode": recipient_mode,
                "relation": _relation(donor_mode, recipient_mode),
            },
            "frame_context": {
                "donor_source_frame": donor_frame,
                "recipient_frame": recipient_frame,
                "relation": _relation(donor_frame, recipient_frame),
            },
            "target_reference_context": {
                "donor_source_reference": (
                    dict(donor_reference)
                    if isinstance(donor_reference, Mapping)
                    else None
                ),
                "recipient_reference": recipient_reference,
                "relation": _relation(
                    donor_reference_identity,
                    recipient_reference_identity,
                ),
                "basis": (
                    "source-run-target-reference-context-only; "
                    "not a donor-family-membership claim"
                ),
            },
            "site_set": site_dimension,
            "residue_identity": identity_dimension,
            "mirror_transform_context": {
                "donor_source_mirror_transform": donor_mirror,
                "recipient_mirror_transform": recipient_mirror,
                "relation": _relation(donor_mirror, recipient_mirror),
                "basis": (
                    "relative transform flags only; absolute chirality remains unknown"
                ),
            },
            "symmetry_and_copy_number": {
                "recipient_symmetry_class": recipient_symmetry,
                "recipient_mr_copies": recipient_copies,
                "donor_coordinate_claim": None,
                "relation": "UNKNOWN",
            },
        },
        "semantics": {
            "descriptive_only": True,
            "score": None,
            "ranking": None,
            "donor_eligibility": None,
            "recipient_compatibility": None,
            "automatic_reuse_authorized": False,
            "rescue_authorized": False,
        },
    }


__all__ = [
    "CandidateRecipientComparisonError",
    "compare_checkpoint_to_recipient",
]
