"""Read-only candidate screening for explicitly supplied canonical DNA ends.

This first primitive accepts caller-identified ends in one Cartesian frame. It
neither detects duplex ends in coordinates nor searches crystallographic images.
It does not establish a connection, alter chemistry, or authorize construction.
Sequences are exposed single-strand overhangs written 5' to 3'; positions are
caller-supplied duplex-end reference points in Angstrom, not atom identities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
import json
import math
import re
from typing import Iterable


@dataclass(frozen=True)
class DuplexEnd:
    """An explicitly classified end, not an inferred PDB chain terminus.

    None sequence means unknown/unsupported chemistry. ``free`` is an explicit
    do-not-connect declaration; ``connected`` preserves an established contact.
    Caller coordinates and classifications must come from the same source model.
    """

    end_id: str
    sequence: str | None
    polarity: str
    position: tuple[float, float, float]
    state: str = "available"

    def __post_init__(self) -> None:
        if not isinstance(self.end_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", self.end_id
        ):
            raise ValueError("end_id must be a nonempty stable identifier")
        if self.sequence is not None and (
            not isinstance(self.sequence, str)
            or re.fullmatch(r"[ACGT]+", self.sequence) is None
        ):
            raise ValueError("sequence must be uppercase canonical DNA or None")
        if self.polarity not in ("5prime", "3prime"):
            raise ValueError("polarity must be 5prime or 3prime")
        if self.state not in ("available", "connected", "free", "unknown"):
            raise ValueError("Unsupported end state")
        if not isinstance(self.position, (tuple, list)) or len(self.position) != 3:
            raise ValueError("position must contain three Cartesian coordinates")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for v in self.position):
            raise ValueError("position coordinates must be finite numbers")
        object.__setattr__(self, "position", tuple(float(v) for v in self.position))


def propose_connections(
    ends: Iterable[DuplexEnd], *, source_model_sha256: str,
    max_distance_angstrom: float, max_pairs: int = 100_000,
) -> dict:
    """Screen all supplied ends for exact full-overhang complement candidates.

    The bound is an explicit search policy, not a chemical target. Partial
    overlap/register shifts, orientation, density and periodicity are untested.
    Every surviving edge remains a review-only hypothesis, even when alone.
    The no-connection alternative is always retained. Competing edges are not
    greedily assigned, and exceeding the pair budget returns no partial report.

    The source hash is caller-supplied provenance, not verification of file bytes.
    No I/O or external tools are used. Returned schema 1 is a descriptive report,
    never a reusable connection scheme or a materialization/approval manifest.
    """
    if not isinstance(source_model_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", source_model_sha256
    ) is None:
        raise ValueError("source_model_sha256 must be a lowercase SHA-256 digest")
    if (type(max_distance_angstrom) not in (int, float)
            or not math.isfinite(max_distance_angstrom) or max_distance_angstrom <= 0):
        raise ValueError("max_distance_angstrom must be positive and finite")
    if type(max_pairs) is not int or max_pairs < 1:
        raise ValueError("max_pairs must be a positive integer")
    rows = list(ends)
    if any(not isinstance(row, DuplexEnd) for row in rows):
        raise ValueError("ends must contain DuplexEnd records")
    if len({row.end_id for row in rows}) != len(rows):
        raise ValueError("Duplicate end_id")
    rows.sort(key=lambda row: row.end_id)
    eligible = [row for row in rows if row.state == "available" and row.sequence is not None]
    pairs = len(eligible) * (len(eligible) - 1) // 2
    if pairs > max_pairs:
        raise ValueError("Pair search budget exceeded; no partial inference returned")

    neighbors: dict[str, list[str]] = {row.end_id: [] for row in rows}
    candidates = []
    complement = str.maketrans("ACGT", "TGCA")
    for left, right in combinations(eligible, 2):
        if left.polarity != right.polarity:
            continue
        if left.sequence != right.sequence.translate(complement)[::-1]:
            continue
        distance = math.dist(left.position, right.position)
        if not math.isfinite(distance):
            raise ValueError("Coordinate separation is not finite")
        if distance > max_distance_angstrom:
            continue
        neighbors[left.end_id].append(right.end_id)
        neighbors[right.end_id].append(left.end_id)
        candidates.append({
            "ends": [left.end_id, right.end_id],
            "edge_type": "base_pairing",
            "register": "full_overhang_antiparallel",
            "residue_pairs": [[i, len(right.sequence) - 1 - i]
                              for i in range(len(left.sequence))],
            "distance_angstrom": distance,
            "geometry_validated": False,
            "evidence": ["exact_reverse_complement", "within_supplied_distance_bound"],
        })

    end_reports = []
    for row in rows:
        partners = neighbors[row.end_id]
        if row.state != "available" or row.sequence is None:
            status = "EXCLUDED"
            reason = row.state if row.state != "available" else "unknown_sequence"
        elif not partners:
            status, reason = "NO_CANDIDATE", "none_in_supplied_scope"
        elif len(partners) > 1 or any(len(neighbors[p]) > 1 for p in partners):
            status, reason = "COMPETING_CANDIDATES", "partner_assignment_unresolved"
        else:
            status, reason = "SINGLE_CANDIDATE_NOT_CONFIRMED", "geometry_and_intent_unchecked"
        end_reports.append({"end_id": row.end_id, "status": status,
                            "reason": reason, "partners": partners})

    # JSON roundtrip normalizes tuples and gives callers a detached input snapshot.
    inputs = json.loads(json.dumps({
        "ends": [asdict(row) for row in rows],
        "source_model_sha256": source_model_sha256,
        "max_distance_angstrom": float(max_distance_angstrom), "max_pairs": max_pairs,
    }, allow_nan=False))
    fingerprint = sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()
    return {
        "schema_version": 1, "kind": "topostitch-end-candidate-report",
        "algorithm": "canonical-full-overhang-screen-v1",
        "source_model_sha256": source_model_sha256, "source_bytes_verified": False,
        "input_sha256": fingerprint, "inputs": inputs,
        "scope": "supplied-ends-single-cartesian-frame",
        "pairs_screened": pairs, "candidates": candidates, "ends": end_reports,
        "selected_candidate": None, "no_connection_alternative": True,
        "runtime_authority": False, "inspection_required": True,
        "limitations": ["No coordinate-derived end detection or symmetry search",
                        "No partial-overlap or noncanonical pairing search",
                        "No oriented-frame, backbone, clash or diffraction validation",
                        "No construction, checkpoint selection or campaign integration"],
    }
