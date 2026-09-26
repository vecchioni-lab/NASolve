"""Pure logical-construct to coordinate registration semantics.

This module does not infer crystallographic topology, edit coordinates, launch
external tools, or authorize MR rescue. It provides the strict data contract
that later Registration Scout / ASU Registration layers can populate.

Logical sites describe construct intent (for example A:12). Coordinate sites
describe one concrete PDB realization (for example M:104). Keeping those
namespaces separate allows chain renaming, arbitrary residue numbering, chain
splits, multiple complete copies, and partial copies without changing logical
mutation or chemistry intent.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path

from .model_assessment import (
    ModelAssessment,
    ModelAssessmentError,
    literal_polymer_identity_inventory,
)
from .run_context import artifact_reference, resolve_artifact_path


class ConstructRegistrationError(RuntimeError):
    """Raised when a construct registration is malformed or ambiguous."""


_SITE = re.compile(r"[^:\s]+:[^:\s]+")
_COPY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_CODE = re.compile(r"[A-Z0-9]{1,5}")


def _target_inventory(target: Mapping[str, object]) -> tuple[list[str], dict[str, str]]:
    if (
        not isinstance(target, Mapping)
        or type(target.get("schema_version")) is not int
        or target.get("schema_version") != 1
        or target.get("kind") != "sequence-family-target"
        or not isinstance(target.get("sites"), list)
    ):
        raise ConstructRegistrationError("Unsupported logical construct target")

    ordered: list[str] = []
    codes: dict[str, str] = {}
    for row in target["sites"]:
        if not isinstance(row, Mapping):
            raise ConstructRegistrationError("Malformed logical construct target row")
        site = row.get("site")
        code = row.get("residue_code")
        if (
            not isinstance(site, str)
            or _SITE.fullmatch(site) is None
            or not isinstance(code, str)
            or _CODE.fullmatch(code) is None
            or site in codes
        ):
            raise ConstructRegistrationError("Malformed logical construct target row")
        ordered.append(site)
        codes[site] = code
    if not ordered:
        raise ConstructRegistrationError("Logical construct target has no sites")
    return ordered, codes


def _coordinate_inventory(assessment: ModelAssessment) -> dict[str, str]:
    if not isinstance(assessment, ModelAssessment):
        raise ConstructRegistrationError("A validated ModelAssessment is required")
    if assessment.duplicate_atom_identities:
        raise ConstructRegistrationError(
            "Duplicate coordinate atom identities make registration ambiguous"
        )
    try:
        inventory = literal_polymer_identity_inventory(assessment)
    except ModelAssessmentError as exc:
        raise ConstructRegistrationError(str(exc)) from exc
    for site, code in inventory.items():
        if _SITE.fullmatch(site) is None or _CODE.fullmatch(code) is None:
            raise ConstructRegistrationError("Malformed assessed coordinate inventory")
    return inventory


def _copy_status(mapped_sites: set[str], expected_sites: set[str]) -> str:
    return "COMPLETE" if mapped_sites == expected_sites else "PARTIAL"


def build_construct_registration(
    assessment: ModelAssessment,
    target: Mapping[str, object],
    copies: Mapping[str, Mapping[str, str]],
    *,
    source: str,
) -> dict[str, object]:
    """Build one strict registration record from an explicit logical mapping.

    copies maps a copy identifier to logical_site -> coordinate_site.
    It may describe complete or partial copies. A coordinate site may appear
    only once globally; a partial copy is recorded but never treated as a
    complete mutation target.

    This function validates correspondence only. It does not infer missing
    mappings, symmetry operations, cut recipes, topology, or edit coordinates.
    """
    if not isinstance(source, str) or not source.strip() or source != source.strip():
        raise ConstructRegistrationError("Registration source must be non-empty text")
    if not isinstance(copies, Mapping) or not copies:
        raise ConstructRegistrationError("Registration requires at least one copy mapping")

    ordered_sites, target_codes = _target_inventory(target)
    expected = set(ordered_sites)
    coordinate = _coordinate_inventory(assessment)

    used_coordinates: set[str] = set()
    records: list[dict[str, object]] = []
    complete_ids: list[str] = []
    partial_ids: list[str] = []
    mismatch_rows: list[dict[str, str]] = []

    for copy_id, mapping in copies.items():
        if not isinstance(copy_id, str) or _COPY_ID.fullmatch(copy_id) is None:
            raise ConstructRegistrationError(f"Invalid registration copy id: {copy_id!r}")
        if not isinstance(mapping, Mapping) or not mapping:
            raise ConstructRegistrationError(
                f"Registration copy {copy_id!r} requires at least one mapped site"
            )
        mapped = set(mapping)
        unknown_logical = sorted(mapped - expected)
        if unknown_logical:
            raise ConstructRegistrationError(
                f"Registration copy {copy_id!r} contains unknown logical sites: "
                + ", ".join(unknown_logical)
            )

        rows: list[dict[str, str]] = []
        for logical_site in ordered_sites:
            if logical_site not in mapping:
                continue
            coordinate_site = mapping[logical_site]
            if (
                not isinstance(coordinate_site, str)
                or _SITE.fullmatch(coordinate_site) is None
            ):
                raise ConstructRegistrationError(
                    f"Registration copy {copy_id!r} has invalid coordinate site "
                    f"for {logical_site}"
                )
            if coordinate_site not in coordinate:
                raise ConstructRegistrationError(
                    f"Registration copy {copy_id!r} references absent coordinate "
                    f"site {coordinate_site}"
                )
            if coordinate_site in used_coordinates:
                raise ConstructRegistrationError(
                    f"Coordinate site {coordinate_site} is assigned more than once"
                )
            used_coordinates.add(coordinate_site)
            observed_code = coordinate[coordinate_site]
            target_code = target_codes[logical_site]
            relation = "SAME" if observed_code == target_code else "DIFFERENT"
            row = {
                "logical_site": logical_site,
                "coordinate_site": coordinate_site,
                "coordinate_residue_code": observed_code,
                "target_residue_code": target_code,
                "identity_relation": relation,
            }
            rows.append(row)
            if relation == "DIFFERENT":
                mismatch_rows.append({
                    "copy_id": copy_id,
                    "logical_site": logical_site,
                    "coordinate_site": coordinate_site,
                    "coordinate_residue_code": observed_code,
                    "target_residue_code": target_code,
                })

        status = _copy_status(mapped, expected)
        if status == "COMPLETE":
            complete_ids.append(copy_id)
        else:
            partial_ids.append(copy_id)
        missing = [site for site in ordered_sites if site not in mapped]
        records.append({
            "copy_id": copy_id,
            "status": status,
            "mapped_site_count": len(rows),
            "target_site_count": len(ordered_sites),
            "missing_logical_sites": missing,
            "mappings": rows,
        })

    if partial_ids:
        registration_status = "PARTIAL_COPY_PRESENT"
    elif len(complete_ids) > 1:
        registration_status = "REGISTERED_COMPLETE_MULTICOPY"
    else:
        registration_status = "REGISTERED_COMPLETE"

    unmapped_coordinates = sorted(set(coordinate) - used_coordinates)
    record: dict[str, object] = {
        "schema_version": 1,
        "kind": "construct-registration",
        "status": registration_status,
        "source": source,
        "model": {
            "sha256": assessment.sha256,
            "polymer_residue_count": assessment.polymer_residue_count,
        },
        "target": {
            "kind": target["kind"],
            "reference": target.get("reference"),
            "site_count": len(ordered_sites),
            "sites": list(ordered_sites),
        },
        "copies": records,
        "summary": {
            "complete_copy_count": len(complete_ids),
            "partial_copy_count": len(partial_ids),
            "complete_copy_ids": complete_ids,
            "partial_copy_ids": partial_ids,
            "mapped_coordinate_site_count": len(used_coordinates),
            "unmapped_coordinate_sites": unmapped_coordinates,
        },
        "identity": {
            "compared_site_count": sum(len(copy["mappings"]) for copy in records),
            "mismatch_count": len(mismatch_rows),
            "mismatches": mismatch_rows,
        },
        "semantics": {
            "logical_sites_are_authoritative": True,
            "coordinate_labels_are_representation_only": True,
            "partial_copies_receive_complete_copy_mutations": False,
            "coordinate_edit_performed": False,
            "symmetry_or_topology_inferred": False,
            "mr_rescue_authorized": False,
        },
    }
    return validate_construct_registration(record)


def build_identity_registration(
    assessment: ModelAssessment,
    target: Mapping[str, object],
    *,
    copy_id: str = "copy_1",
) -> dict[str, object]:
    """Build the fast-path registration when logical and coordinate IDs coincide."""
    ordered_sites, _ = _target_inventory(target)
    coordinate = _coordinate_inventory(assessment)
    expected = set(ordered_sites)
    observed = set(coordinate)
    if observed != expected:
        raise ConstructRegistrationError(
            "Identity registration requires the exact logical/coordinate site set; "
            f"missing={sorted(expected - observed)!r}; "
            f"unexpected={sorted(observed - expected)!r}"
        )
    return build_construct_registration(
        assessment,
        target,
        {copy_id: {site: site for site in ordered_sites}},
        source="identity-site-map",
    )


def expand_logical_sites(
    registration: Mapping[str, object],
    logical_sites: Sequence[str],
) -> dict[str, object]:
    """Expand logical actions to coordinate sites on complete registered copies.

    Partial copies are reported and skipped. This is a planning operation only;
    no coordinate edit or mutation is performed.
    """
    checked = validate_construct_registration(registration)
    if (
        isinstance(logical_sites, (str, bytes))
        or not isinstance(logical_sites, Sequence)
        or not logical_sites
    ):
        raise ConstructRegistrationError("Logical-site expansion requires a non-empty sequence")
    target_sites = checked["target"]["sites"]
    requested: list[str] = []
    seen: set[str] = set()
    for site in logical_sites:
        if (
            not isinstance(site, str)
            or site not in target_sites
            or site in seen
        ):
            raise ConstructRegistrationError(
                f"Unknown or duplicate logical site requested for expansion: {site!r}"
            )
        seen.add(site)
        requested.append(site)

    targets: list[dict[str, str]] = []
    skipped_partial: list[str] = []
    for copy in checked["copies"]:
        if copy["status"] != "COMPLETE":
            skipped_partial.append(copy["copy_id"])
            continue
        by_logical = {
            row["logical_site"]: row["coordinate_site"]
            for row in copy["mappings"]
        }
        for site in requested:
            coordinate_site = by_logical.get(site)
            if coordinate_site is None:
                raise ConstructRegistrationError(
                    f"Complete registration copy {copy['copy_id']} omitted {site}"
                )
            targets.append({
                "copy_id": copy["copy_id"],
                "logical_site": site,
                "coordinate_site": coordinate_site,
            })

    if not targets:
        raise ConstructRegistrationError(
            "No complete registered copy is available for logical-site expansion"
        )
    return {
        "schema_version": 1,
        "kind": "registration-site-expansion",
        "logical_sites": requested,
        "targets": targets,
        "skipped_partial_copy_ids": skipped_partial,
        "semantics": {
            "complete_copies_only": True,
            "coordinate_edit_performed": False,
        },
    }


def validate_construct_registration(value: Mapping[str, object]) -> dict[str, object]:
    """Strictly validate one schema-1 construct-registration record."""
    if not isinstance(value, Mapping):
        raise ConstructRegistrationError("Construct registration is not an object")
    required = {
        "schema_version",
        "kind",
        "status",
        "source",
        "model",
        "target",
        "copies",
        "summary",
        "identity",
        "semantics",
    }
    if set(value) != required:
        raise ConstructRegistrationError("Malformed construct-registration record")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "construct-registration"
        or value["status"] not in {
            "REGISTERED_COMPLETE",
            "REGISTERED_COMPLETE_MULTICOPY",
            "PARTIAL_COPY_PRESENT",
        }
        or not isinstance(value["source"], str)
        or not value["source"]
    ):
        raise ConstructRegistrationError("Malformed construct-registration identity")

    model = value["model"]
    target = value["target"]
    copies = value["copies"]
    summary = value["summary"]
    identity = value["identity"]
    semantics = value["semantics"]
    if (
        not isinstance(model, Mapping)
        or set(model) != {"sha256", "polymer_residue_count"}
        or not isinstance(model["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", model["sha256"]) is None
        or type(model["polymer_residue_count"]) is not int
        or model["polymer_residue_count"] < 0
    ):
        raise ConstructRegistrationError("Malformed registration model identity")
    if (
        not isinstance(target, Mapping)
        or set(target) != {"kind", "reference", "site_count", "sites"}
        or target["kind"] != "sequence-family-target"
        or type(target["site_count"]) is not int
        or target["site_count"] <= 0
        or not isinstance(target["sites"], list)
        or len(target["sites"]) != target["site_count"]
        or len(set(target["sites"])) != len(target["sites"])
        or not all(
            isinstance(site, str) and _SITE.fullmatch(site)
            for site in target["sites"]
        )
    ):
        raise ConstructRegistrationError("Malformed registration target identity")
    if not isinstance(copies, list) or not copies:
        raise ConstructRegistrationError("Registration copies must be a non-empty list")

    copy_ids: set[str] = set()
    coordinate_sites: set[str] = set()
    complete_ids: list[str] = []
    partial_ids: list[str] = []
    mismatch_rows: list[dict[str, str]] = []
    mapped_count = 0
    expected_sites = set(target["sites"])

    for copy in copies:
        if (
            not isinstance(copy, Mapping)
            or set(copy) != {
                "copy_id",
                "status",
                "mapped_site_count",
                "target_site_count",
                "missing_logical_sites",
                "mappings",
            }
        ):
            raise ConstructRegistrationError("Malformed registration copy record")
        copy_id = copy["copy_id"]
        if (
            not isinstance(copy_id, str)
            or _COPY_ID.fullmatch(copy_id) is None
            or copy_id in copy_ids
        ):
            raise ConstructRegistrationError("Malformed or duplicate registration copy id")
        copy_ids.add(copy_id)
        if copy["status"] not in {"COMPLETE", "PARTIAL"}:
            raise ConstructRegistrationError("Malformed registration copy status")
        if (
            type(copy["mapped_site_count"]) is not int
            or type(copy["target_site_count"]) is not int
            or copy["target_site_count"] != target["site_count"]
            or not isinstance(copy["missing_logical_sites"], list)
            or not isinstance(copy["mappings"], list)
            or len(copy["mappings"]) != copy["mapped_site_count"]
        ):
            raise ConstructRegistrationError("Malformed registration copy counts")

        mapped_logical: set[str] = set()
        for row in copy["mappings"]:
            if (
                not isinstance(row, Mapping)
                or set(row) != {
                    "logical_site",
                    "coordinate_site",
                    "coordinate_residue_code",
                    "target_residue_code",
                    "identity_relation",
                }
                or row["logical_site"] not in expected_sites
                or row["logical_site"] in mapped_logical
                or not isinstance(row["coordinate_site"], str)
                or _SITE.fullmatch(row["coordinate_site"]) is None
                or row["coordinate_site"] in coordinate_sites
                or not isinstance(row["coordinate_residue_code"], str)
                or _CODE.fullmatch(row["coordinate_residue_code"]) is None
                or not isinstance(row["target_residue_code"], str)
                or _CODE.fullmatch(row["target_residue_code"]) is None
                or row["identity_relation"] not in {"SAME", "DIFFERENT"}
            ):
                raise ConstructRegistrationError("Malformed registration mapping row")
            expected_relation = (
                "SAME"
                if row["coordinate_residue_code"] == row["target_residue_code"]
                else "DIFFERENT"
            )
            if row["identity_relation"] != expected_relation:
                raise ConstructRegistrationError(
                    "Registration identity relation disagrees with residue codes"
                )
            mapped_logical.add(row["logical_site"])
            coordinate_sites.add(row["coordinate_site"])
            if row["identity_relation"] == "DIFFERENT":
                mismatch_rows.append({
                    "copy_id": copy_id,
                    "logical_site": row["logical_site"],
                    "coordinate_site": row["coordinate_site"],
                    "coordinate_residue_code": row["coordinate_residue_code"],
                    "target_residue_code": row["target_residue_code"],
                })

        missing = [site for site in target["sites"] if site not in mapped_logical]
        if copy["missing_logical_sites"] != missing:
            raise ConstructRegistrationError("Registration missing-site summary is inconsistent")
        expected_status = "COMPLETE" if not missing else "PARTIAL"
        if copy["status"] != expected_status:
            raise ConstructRegistrationError("Registration copy completeness is inconsistent")
        if copy["status"] == "COMPLETE":
            complete_ids.append(copy_id)
        else:
            partial_ids.append(copy_id)
        mapped_count += len(copy["mappings"])

    expected_status = (
        "PARTIAL_COPY_PRESENT"
        if partial_ids
        else "REGISTERED_COMPLETE_MULTICOPY"
        if len(complete_ids) > 1
        else "REGISTERED_COMPLETE"
    )
    if value["status"] != expected_status:
        raise ConstructRegistrationError("Registration overall status is inconsistent")

    required_summary = {
        "complete_copy_count",
        "partial_copy_count",
        "complete_copy_ids",
        "partial_copy_ids",
        "mapped_coordinate_site_count",
        "unmapped_coordinate_sites",
    }
    if (
        not isinstance(summary, Mapping)
        or set(summary) != required_summary
        or summary["complete_copy_count"] != len(complete_ids)
        or summary["partial_copy_count"] != len(partial_ids)
        or summary["complete_copy_ids"] != complete_ids
        or summary["partial_copy_ids"] != partial_ids
        or summary["mapped_coordinate_site_count"] != mapped_count
        or not isinstance(summary["unmapped_coordinate_sites"], list)
        or len(set(summary["unmapped_coordinate_sites"]))
        != len(summary["unmapped_coordinate_sites"])
        or not all(
            isinstance(site, str) and _SITE.fullmatch(site)
            for site in summary["unmapped_coordinate_sites"]
        )
        or coordinate_sites.intersection(summary["unmapped_coordinate_sites"])
        or mapped_count + len(summary["unmapped_coordinate_sites"])
        != model["polymer_residue_count"]
    ):
        raise ConstructRegistrationError("Malformed registration summary")

    if (
        not isinstance(identity, Mapping)
        or set(identity) != {"compared_site_count", "mismatch_count", "mismatches"}
        or identity["compared_site_count"] != mapped_count
        or identity["mismatch_count"] != len(mismatch_rows)
        or identity["mismatches"] != mismatch_rows
    ):
        raise ConstructRegistrationError("Malformed registration identity summary")

    expected_semantics = {
        "logical_sites_are_authoritative": True,
        "coordinate_labels_are_representation_only": True,
        "partial_copies_receive_complete_copy_mutations": False,
        "coordinate_edit_performed": False,
        "symmetry_or_topology_inferred": False,
        "mr_rescue_authorized": False,
    }
    if semantics != expected_semantics:
        raise ConstructRegistrationError("Malformed registration semantics")

    return dict(value)


def logical_inventory_by_copy(
    registration: Mapping[str, object],
    *,
    complete_only: bool = False,
) -> dict[str, dict[str, str]]:
    """Return observed residue identities in logical-site coordinates.

    The values come from the registered coordinate model, not the target.
    This is a read-only adapter for later comparison/provenance layers.
    """
    checked = validate_construct_registration(registration)
    result: dict[str, dict[str, str]] = {}
    for copy in checked["copies"]:
        if complete_only and copy["status"] != "COMPLETE":
            continue
        result[copy["copy_id"]] = {
            row["logical_site"]: row["coordinate_residue_code"]
            for row in copy["mappings"]
        }
    return result


def freeze_construct_registration(
    registration: Mapping[str, object],
    run: Path,
) -> dict[str, object]:
    """Freeze one registration artifact beneath an already allocated run."""
    checked = validate_construct_registration(registration)
    data = (
        json.dumps(checked, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    path = run / "Model" / "construct_registration.json"
    try:
        with path.open("xb") as handle:
            handle.write(data)
    except OSError as exc:
        raise ConstructRegistrationError(
            f"Could not freeze construct registration: {exc}"
        ) from exc
    return {
        "schema_version": 1,
        "kind": "frozen-construct-registration",
        "artifact": {
            **artifact_reference(path, run),
            "sha256": sha256(data).hexdigest(),
            "size": len(data),
        },
    }


def load_construct_registration(
    report: Mapping[str, object],
    run: Path,
) -> dict[str, object] | None:
    """Load only a checksum-verified run-local registration artifact."""
    frozen = report.get("construct_registration")
    if frozen is None:
        return None
    if (
        not isinstance(frozen, Mapping)
        or set(frozen) != {"schema_version", "kind", "artifact"}
        or type(frozen.get("schema_version")) is not int
        or frozen["schema_version"] != 1
        or frozen.get("kind") != "frozen-construct-registration"
        or not isinstance(frozen.get("artifact"), Mapping)
    ):
        raise ConstructRegistrationError("Malformed frozen construct registration")

    artifact = frozen["artifact"]
    if (
        artifact.get("anchor") != "run"
        or not isinstance(artifact.get("relative_path"), str)
        or not isinstance(artifact.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None
        or type(artifact.get("size")) is not int
        or artifact["size"] <= 0
    ):
        raise ConstructRegistrationError(
            "Malformed construct-registration artifact reference"
        )
    try:
        path = resolve_artifact_path(artifact, run)
        if path is None:
            raise ConstructRegistrationError(
                "Frozen construct registration is missing or failed checksum validation"
            )
        path.resolve().relative_to(run.resolve())
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ConstructRegistrationError(
            f"Could not read frozen construct registration: {exc}"
        ) from exc
    if len(data) != artifact["size"] or sha256(data).hexdigest() != artifact["sha256"]:
        raise ConstructRegistrationError(
            "Frozen construct registration changed while being read"
        )
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ConstructRegistrationError(
            f"Could not decode frozen construct registration: {exc}"
        ) from exc
    return validate_construct_registration(value)


__all__ = [
    "ConstructRegistrationError",
    "build_construct_registration",
    "build_identity_registration",
    "expand_logical_sites",
    "freeze_construct_registration",
    "load_construct_registration",
    "logical_inventory_by_copy",
    "validate_construct_registration",
]
