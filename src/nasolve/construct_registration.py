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




_RESID_PARTS = re.compile(r"(-?(?:0|[1-9][0-9]*))([A-Za-z]?)$")


def _split_site(site: str) -> tuple[str, str]:
    chain, resid = site.split(":", 1)
    return chain, resid


def _target_chains(
    target: Mapping[str, object],
) -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    ordered_sites, codes = _target_inventory(target)
    order: list[str] = []
    by_chain: dict[str, list[str]] = {}
    for site in ordered_sites:
        chain, resid = _split_site(site)
        if chain not in by_chain:
            order.append(chain)
            by_chain[chain] = []
        by_chain[chain].append(resid)
    return order, by_chain, codes


def _constant_residue_offset(
    logical_ids: Sequence[str],
    coordinate_ids: Sequence[str],
) -> int | None:
    """Return one numeric residue-number offset, or None if the pattern differs."""
    if len(logical_ids) != len(coordinate_ids) or not logical_ids:
        return None
    offsets: set[int] = set()
    for logical, coordinate in zip(logical_ids, coordinate_ids):
        left = _RESID_PARTS.fullmatch(logical)
        right = _RESID_PARTS.fullmatch(coordinate)
        if left is None or right is None or left.group(2) != right.group(2):
            return None
        offsets.add(int(right.group(1)) - int(left.group(1)))
        if len(offsets) > 1:
            return None
    return next(iter(offsets))


def _simple_chain_candidates(
    assessment: ModelAssessment,
    target: Mapping[str, object],
) -> tuple[list[str], dict[str, list[dict[str, object]]]]:
    logical_order, logical_ids, _ = _target_chains(target)
    candidates: dict[str, list[dict[str, object]]] = {}
    for logical_chain in logical_order:
        rows: list[dict[str, object]] = []
        for coordinate_chain, coordinate_ids in (
            assessment.polymer_residue_ids_by_chain.items()
        ):
            offset = _constant_residue_offset(
                logical_ids[logical_chain],
                coordinate_ids,
            )
            if offset is None:
                continue
            rows.append({
                "coordinate_chain": coordinate_chain,
                "residue_number_offset": offset,
            })
        candidates[logical_chain] = rows
    return logical_order, candidates


def describe_simple_chain_evidence(
    assessment: ModelAssessment,
    target: Mapping[str, object],
) -> dict[str, object]:
    """Describe design-identity evidence for every simple chain candidate.

    This report is deliberately non-decisional. A target residue mismatch may
    simply be the intended PostMR mutation or modification, so match counts are
    not a compatibility score and are not used by Scout v1 to choose chains.
    """
    logical_order, logical_ids, target_codes = _target_chains(target)
    coordinate = _coordinate_inventory(assessment)
    _, candidates = _simple_chain_candidates(assessment, target)

    chains: list[dict[str, object]] = []
    for logical_chain in logical_order:
        candidate_rows: list[dict[str, object]] = []
        for option in candidates[logical_chain]:
            coordinate_chain = option["coordinate_chain"]
            coordinate_ids = assessment.polymer_residue_ids_by_chain[
                coordinate_chain
            ]
            mismatches: list[dict[str, str]] = []
            match_count = 0
            for logical_resid, coordinate_resid in zip(
                logical_ids[logical_chain],
                coordinate_ids,
            ):
                logical_site = f"{logical_chain}:{logical_resid}"
                coordinate_site = f"{coordinate_chain}:{coordinate_resid}"
                observed = coordinate[coordinate_site]
                intended = target_codes[logical_site]
                if observed == intended:
                    match_count += 1
                else:
                    mismatches.append({
                        "logical_site": logical_site,
                        "coordinate_site": coordinate_site,
                        "coordinate_residue_code": observed,
                        "target_residue_code": intended,
                    })
            candidate_rows.append({
                "coordinate_chain": coordinate_chain,
                "residue_number_offset": option["residue_number_offset"],
                "compared_site_count": len(coordinate_ids),
                "identity_match_count": match_count,
                "identity_mismatch_count": len(mismatches),
                "mismatches": mismatches,
            })
        chains.append({
            "logical_chain": logical_chain,
            "logical_site_count": len(logical_ids[logical_chain]),
            "candidates": candidate_rows,
        })

    return {
        "schema_version": 1,
        "kind": "construct-registration-chain-evidence",
        "model": {
            "sha256": assessment.sha256,
            "polymer_residue_count": assessment.polymer_residue_count,
        },
        "target": {
            "kind": target["kind"],
            "reference": target.get("reference"),
            "site_count": sum(len(logical_ids[chain]) for chain in logical_order),
        },
        "chains": chains,
        "semantics": {
            "descriptive_only": True,
            "used_for_assignment": False,
            "identity_match_count_is_not_a_score": True,
            "target_differences_may_be_expected_postmr_changes": True,
        },
    }


def _validate_chain_evidence(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ConstructRegistrationError("Registration chain evidence is not an object")
    if set(value) != {
        "schema_version", "kind", "model", "target", "chains", "semantics",
    }:
        raise ConstructRegistrationError("Malformed registration chain evidence")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "construct-registration-chain-evidence"
    ):
        raise ConstructRegistrationError("Malformed registration chain-evidence identity")
    model = value["model"]
    target = value["target"]
    chains = value["chains"]
    semantics = value["semantics"]
    if (
        not isinstance(model, Mapping)
        or set(model) != {"sha256", "polymer_residue_count"}
        or not isinstance(model["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", model["sha256"]) is None
        or type(model["polymer_residue_count"]) is not int
        or model["polymer_residue_count"] < 0
    ):
        raise ConstructRegistrationError("Malformed chain-evidence model")
    if (
        not isinstance(target, Mapping)
        or set(target) != {"kind", "reference", "site_count"}
        or target["kind"] != "sequence-family-target"
        or type(target["site_count"]) is not int
        or target["site_count"] <= 0
    ):
        raise ConstructRegistrationError("Malformed chain-evidence target")
    if not isinstance(chains, list) or not chains:
        raise ConstructRegistrationError("Registration chain evidence has no chains")
    logical_seen: set[str] = set()
    total_sites = 0
    for chain in chains:
        if (
            not isinstance(chain, Mapping)
            or set(chain) != {"logical_chain", "logical_site_count", "candidates"}
            or not isinstance(chain["logical_chain"], str)
            or not chain["logical_chain"]
            or chain["logical_chain"] in logical_seen
            or type(chain["logical_site_count"]) is not int
            or chain["logical_site_count"] <= 0
            or not isinstance(chain["candidates"], list)
        ):
            raise ConstructRegistrationError("Malformed chain-evidence chain record")
        logical_seen.add(chain["logical_chain"])
        total_sites += chain["logical_site_count"]
        coordinate_seen: set[str] = set()
        for candidate in chain["candidates"]:
            if (
                not isinstance(candidate, Mapping)
                or set(candidate) != {
                    "coordinate_chain",
                    "residue_number_offset",
                    "compared_site_count",
                    "identity_match_count",
                    "identity_mismatch_count",
                    "mismatches",
                }
                or not isinstance(candidate["coordinate_chain"], str)
                or not candidate["coordinate_chain"]
                or candidate["coordinate_chain"] in coordinate_seen
                or type(candidate["residue_number_offset"]) is not int
                or type(candidate["compared_site_count"]) is not int
                or candidate["compared_site_count"] != chain["logical_site_count"]
                or type(candidate["identity_match_count"]) is not int
                or type(candidate["identity_mismatch_count"]) is not int
                or not isinstance(candidate["mismatches"], list)
                or candidate["identity_mismatch_count"] != len(candidate["mismatches"])
                or candidate["identity_match_count"] + candidate["identity_mismatch_count"]
                != candidate["compared_site_count"]
            ):
                raise ConstructRegistrationError("Malformed chain-evidence candidate")
            coordinate_seen.add(candidate["coordinate_chain"])
            for mismatch in candidate["mismatches"]:
                if (
                    not isinstance(mismatch, Mapping)
                    or set(mismatch) != {
                        "logical_site",
                        "coordinate_site",
                        "coordinate_residue_code",
                        "target_residue_code",
                    }
                    or not all(
                        isinstance(mismatch[field], str) and mismatch[field]
                        for field in (
                            "logical_site",
                            "coordinate_site",
                            "coordinate_residue_code",
                            "target_residue_code",
                        )
                    )
                    or mismatch["coordinate_residue_code"]
                    == mismatch["target_residue_code"]
                ):
                    raise ConstructRegistrationError(
                        "Malformed chain-evidence mismatch"
                    )
    if total_sites != target["site_count"]:
        raise ConstructRegistrationError("Chain-evidence target count is inconsistent")
    if semantics != {
        "descriptive_only": True,
        "used_for_assignment": False,
        "identity_match_count_is_not_a_score": True,
        "target_differences_may_be_expected_postmr_changes": True,
    }:
        raise ConstructRegistrationError("Malformed chain-evidence semantics")
    return dict(value)


def _unique_chain_assignment(
    logical_order: Sequence[str],
    candidates: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[dict[str, Mapping[str, object]] | None, bool]:
    """Return the unique bijection, or signal ambiguity without ranking guesses."""
    solutions: list[dict[str, Mapping[str, object]]] = []

    def visit(
        index: int,
        used: set[str],
        chosen: dict[str, Mapping[str, object]],
    ) -> None:
        if len(solutions) >= 2:
            return
        if index == len(logical_order):
            solutions.append(dict(chosen))
            return
        logical_chain = logical_order[index]
        for option in candidates.get(logical_chain, ()):
            coordinate_chain = option.get("coordinate_chain")
            if not isinstance(coordinate_chain, str) or coordinate_chain in used:
                continue
            used.add(coordinate_chain)
            chosen[logical_chain] = option
            visit(index + 1, used, chosen)
            chosen.pop(logical_chain, None)
            used.remove(coordinate_chain)

    visit(0, set(), {})
    if len(solutions) == 1:
        return solutions[0], False
    return None, len(solutions) > 1


def scout_simple_registration(
    assessment: ModelAssessment,
    target: Mapping[str, object],
) -> dict[str, object]:
    """Conservatively infer only identity/rename/constant-offset registrations.

    The scout intentionally ignores residue-identity similarity when assigning
    chains. Expected mutations must not become a hidden registration score.
    Symmetry expansion, split-chain inference, copy-number inference, topology,
    recutting, and coordinate edits are all deferred.

    A unique simple mapping returns REGISTERED plus a full construct-registration
    record. Multiple equally valid chain assignments return AMBIGUOUS. Missing
    simple correspondence returns UNRESOLVED. No case silently guesses.
    """
    _target_inventory(target)
    coordinate = _coordinate_inventory(assessment)
    logical_order, logical_ids, _ = _target_chains(target)

    if set(coordinate) == {
        f"{chain}:{resid}"
        for chain in logical_order
        for resid in logical_ids[chain]
    }:
        registration = build_identity_registration(assessment, target)
        return {
            "schema_version": 1,
            "kind": "construct-registration-scout",
            "status": "REGISTERED",
            "method": "identity-site-map",
            "reason": "logical and coordinate site identifiers are identical",
            "chain_candidates": {},
            "registration": registration,
            "semantics": {
                "descriptive_only": True,
                "sequence_similarity_used_for_assignment": False,
                "symmetry_or_topology_inferred": False,
                "coordinate_edit_performed": False,
                "guided_review_required": False,
            },
        }

    coordinate_chains = list(assessment.polymer_residue_ids_by_chain)

    # Preserve the ordinary labelled-chain path before considering renames.
    # This matters for constructs such as W where several chains may share the
    # same length/numbering pattern and would otherwise form interchangeable
    # rename candidates despite their labels already agreeing.
    if set(logical_order) == set(coordinate_chains):
        same_name_offsets: dict[str, int] = {}
        same_name_ok = True
        for logical_chain in logical_order:
            offset = _constant_residue_offset(
                logical_ids[logical_chain],
                assessment.polymer_residue_ids_by_chain[logical_chain],
            )
            if offset is None:
                same_name_ok = False
                break
            same_name_offsets[logical_chain] = offset
        if same_name_ok:
            mapping = {}
            for logical_chain in logical_order:
                coordinate_ids = assessment.polymer_residue_ids_by_chain[
                    logical_chain
                ]
                for logical_resid, coordinate_resid in zip(
                    logical_ids[logical_chain],
                    coordinate_ids,
                ):
                    mapping[f"{logical_chain}:{logical_resid}"] = (
                        f"{logical_chain}:{coordinate_resid}"
                    )
            registration = build_construct_registration(
                assessment,
                target,
                {"copy_1": mapping},
                source="registration-scout:residue-number-offset",
            )
            return {
                "schema_version": 1,
                "kind": "construct-registration-scout",
                "status": "REGISTERED",
                "method": "residue-number-offset",
                "reason": (
                    "same-named logical/coordinate chains have constant "
                    "residue-number offsets"
                ),
                "chain_candidates": {
                    chain: [{
                        "coordinate_chain": chain,
                        "residue_number_offset": same_name_offsets[chain],
                    }]
                    for chain in logical_order
                },
                "registration": registration,
                "semantics": {
                    "descriptive_only": True,
                    "sequence_similarity_used_for_assignment": False,
                    "symmetry_or_topology_inferred": False,
                    "coordinate_edit_performed": False,
                    "guided_review_required": False,
                },
            }

    logical_order, candidates = _simple_chain_candidates(assessment, target)
    candidate_view = {
        logical_chain: [
            {
                "coordinate_chain": row["coordinate_chain"],
                "residue_number_offset": row["residue_number_offset"],
            }
            for row in rows
        ]
        for logical_chain, rows in candidates.items()
    }

    common_semantics = {
        "descriptive_only": True,
        "sequence_similarity_used_for_assignment": False,
        "symmetry_or_topology_inferred": False,
        "coordinate_edit_performed": False,
    }

    if len(logical_order) != len(coordinate_chains):
        return {
            "schema_version": 1,
            "kind": "construct-registration-scout",
            "status": "UNRESOLVED",
            "method": None,
            "reason": (
                "logical and coordinate chain counts differ; multiplicity or "
                "split-chain inference is outside simple scout"
            ),
            "chain_candidates": candidate_view,
            "registration": None,
            "semantics": {
                **common_semantics,
                "guided_review_required": True,
            },
        }

    if any(not rows for rows in candidates.values()):
        return {
            "schema_version": 1,
            "kind": "construct-registration-scout",
            "status": "UNRESOLVED",
            "method": None,
            "reason": (
                "at least one logical chain has no coordinate chain with the "
                "same length and constant residue-number offset"
            ),
            "chain_candidates": candidate_view,
            "registration": None,
            "semantics": {
                **common_semantics,
                "guided_review_required": True,
            },
        }

    assignment, ambiguous = _unique_chain_assignment(logical_order, candidates)
    if ambiguous:
        return {
            "schema_version": 1,
            "kind": "construct-registration-scout",
            "status": "AMBIGUOUS",
            "method": None,
            "reason": (
                "more than one chain bijection satisfies simple length/offset "
                "registration; scout refuses to rank by sequence similarity"
            ),
            "chain_candidates": candidate_view,
            "registration": None,
            "semantics": {
                **common_semantics,
                "guided_review_required": True,
            },
        }
    if assignment is None:
        return {
            "schema_version": 1,
            "kind": "construct-registration-scout",
            "status": "UNRESOLVED",
            "method": None,
            "reason": "no complete one-to-one simple chain assignment exists",
            "chain_candidates": candidate_view,
            "registration": None,
            "semantics": {
                **common_semantics,
                "guided_review_required": True,
            },
        }

    mapping: dict[str, str] = {}
    renamed = False
    shifted = False
    for logical_chain in logical_order:
        option = assignment[logical_chain]
        coordinate_chain = option["coordinate_chain"]
        offset = option["residue_number_offset"]
        renamed = renamed or coordinate_chain != logical_chain
        shifted = shifted or offset != 0
        coordinate_ids = assessment.polymer_residue_ids_by_chain[coordinate_chain]
        for logical_resid, coordinate_resid in zip(
            logical_ids[logical_chain],
            coordinate_ids,
        ):
            mapping[f"{logical_chain}:{logical_resid}"] = (
                f"{coordinate_chain}:{coordinate_resid}"
            )

    if renamed and shifted:
        method = "whole-chain-rename-and-residue-offset"
    elif renamed:
        method = "whole-chain-rename"
    else:
        method = "residue-number-offset"

    registration = build_construct_registration(
        assessment,
        target,
        {"copy_1": mapping},
        source=f"registration-scout:{method}",
    )
    return {
        "schema_version": 1,
        "kind": "construct-registration-scout",
        "status": "REGISTERED",
        "method": method,
        "reason": "unique simple chain bijection",
        "chain_candidates": candidate_view,
        "registration": registration,
        "semantics": {
            **common_semantics,
            "guided_review_required": False,
        },
    }


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
    "scout_simple_registration",
    "validate_construct_registration",
]
