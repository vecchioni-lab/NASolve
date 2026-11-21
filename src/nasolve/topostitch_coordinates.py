"""Read-only PDB adapter for explicitly assigned canonical duplex ends.

Assignments supply topology; coordinates supply identity and a descriptive end
frame. Neither component proves that the declared pairs actually pair or that
an overhang is terminal. There is no symmetry search or construction authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Iterable

from .topostitch import DuplexEnd, propose_connections

_CANONICAL = {"DA": "A", "DC": "C", "DG": "G", "DT": "T"}
_RING = ("N1", "C2", "N3", "C4", "C5", "C6")


@dataclass(frozen=True)
class ResidueSite:
    """Exact PDB coordinate site; blank chain is the empty string."""

    chain: str
    residue_number: int
    insertion_code: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.chain, str) or re.fullmatch(r"[!-~]?", self.chain) is None:
            raise ValueError("chain must be a single printable PDB character or empty")
        if type(self.residue_number) is not int or not -999 <= self.residue_number <= 9999:
            raise ValueError("residue_number must be a PDB decimal integer")
        if not isinstance(self.insertion_code, str) or re.fullmatch(r"[A-Za-z0-9]?", self.insertion_code) is None:
            raise ValueError("insertion_code must be empty or one alphanumeric character")


@dataclass(frozen=True)
class EndAssignment:
    """Caller-declared topology for one duplex end, all in the identity image.

    Overhang sites are in chemical 5'->3' order, never sorted by numbering.
    terminal_pair and inner_pair each list strand-1 then strand-2 sites. The
    inner pair must be the next paired step toward the duplex interior. These
    assertions are not inferred or chemically validated by this adapter.
    """

    end_id: str
    overhang_sites: tuple[ResidueSite, ...]
    terminal_pair: tuple[ResidueSite, ResidueSite]
    inner_pair: tuple[ResidueSite, ResidueSite]
    polarity: str
    state: str = "available"

    def __post_init__(self) -> None:
        DuplexEnd(self.end_id, None, self.polarity, (0, 0, 0), self.state)
        for name in ("overhang_sites", "terminal_pair", "inner_pair"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or not values:
                raise ValueError(f"{name} requires explicit coordinate sites")
            if any(not isinstance(site, ResidueSite) for site in values):
                raise ValueError(f"{name} requires ResidueSite records")
            if name != "overhang_sites" and len(values) != 2:
                raise ValueError(f"{name} requires two sites")
            object.__setattr__(self, name, tuple(values))
        all_sites = self.overhang_sites + self.terminal_pair + self.inner_pair
        if len(set(all_sites)) != len(all_sites):
            raise ValueError("Assignment contains overlapping or duplicate sites")


class _Unassessed(ValueError):
    def __init__(self, code: str, site: ResidueSite | None = None):
        self.code, self.site = code, site
        super().__init__(code)


def _read_atoms(data: bytes) -> dict:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("PDB adapter requires ASCII fixed-column records") from exc
    models = sum(line[:6].strip() == "MODEL" for line in lines)
    if models > 1:
        raise ValueError("Multiple PDB models are unsupported; select one explicitly upstream")
    inside = not models
    segment, atoms = 0, {}
    seen_endmdl = False
    for line in lines:
        record = line[:6].strip()
        if record == "MODEL":
            inside = True
        elif record == "ENDMDL":
            if not models or not inside:
                raise ValueError("Malformed PDB model boundaries")
            inside, seen_endmdl = False, True
        elif record == "TER":
            segment += 1
        elif record in ("ATOM", "HETATM"):
            if not inside:
                raise ValueError("Atoms outside the selected PDB model")
            try:
                site = ResidueSite(line[21:22].strip(), int(line[22:26]), line[26:27].strip())
                xyz = tuple(float(line[a:b]) for a,b in ((30,38),(38,46),(46,54)))
                if len(line) < 54 or not all(math.isfinite(x) for x in xyz):
                    raise ValueError("Invalid coordinates")
                name = line[12:16].strip().replace("*", "'")
                residue = line[17:20].strip()
                if not name or not residue:
                    raise ValueError("Missing atom/residue name")
            except (ValueError, TypeError) as exc:
                raise ValueError("Malformed PDB atom record") from exc
            try:
                occupancy = float(line[54:60])
            except ValueError:
                occupancy = None
            groups = atoms.setdefault(site, {})
            groups.setdefault(segment, []).append((name, residue, line[16:17].strip(), xyz, occupancy))
    if models and not seen_endmdl:
        raise ValueError("PDB model has no ENDMDL")
    if not atoms:
        raise ValueError("PDB contains no atom records")
    return atoms


def _residue(atoms: dict, site: ResidueSite) -> tuple[str, dict]:
    groups = atoms.get(site)
    if not groups:
        raise _Unassessed("MISSING_RESIDUE", site)
    if len(groups) != 1:
        raise _Unassessed("AMBIGUOUS_RESIDUE", site)
    rows = next(iter(groups.values()))
    if len({row[1] for row in rows}) != 1:
        raise _Unassessed("AMBIGUOUS_RESIDUE", site)
    code = rows[0][1]
    if code not in _CANONICAL:
        raise _Unassessed("UNSUPPORTED_RESIDUE", site)
    if any(row[2] for row in rows):
        raise _Unassessed("ALTERNATE_CONFORMER", site)
    names = [row[0] for row in rows]
    if len(set(names)) != len(names):
        raise _Unassessed("AMBIGUOUS_ATOM", site)
    required = set(_RING) | {"C1'"}
    if not required <= set(names):
        raise _Unassessed("MISSING_ATOM", site)
    if any(row[4] is None or not math.isfinite(row[4]) or not 0 < row[4] <= 1
           for row in rows if row[0] in required):
        raise _Unassessed("UNUSABLE_OCCUPANCY", site)
    return _CANONICAL[code], {row[0]: row[3] for row in rows}


def _sub(a, b):
    return tuple(x-y for x,y in zip(a,b))


def _dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(a):
    length = math.hypot(*a)
    if not math.isfinite(length) or length < 1e-10:
        raise _Unassessed("DEGENERATE_FRAME")
    return tuple(v/length for v in a)


def _mean(points):
    return tuple(sum(p[i] for p in points)/len(points) for i in range(3))


def _plane(coords):
    points = [coords[name] for name in _RING]
    origin = _mean(points)
    centered = [_sub(p, origin) for p in points]
    crosses = [_cross(p, centered[(i+1)%len(centered)]) for i,p in enumerate(centered)]
    normal = _unit(tuple(sum(c[i] for c in crosses) for i in range(3)))
    rms = math.sqrt(sum(_dot(p, normal)**2 for p in centered)/len(centered))
    return origin, normal, rms


def _frame(terminal, inner):
    # Descriptive polygon-area normals, not standardized 3DNA base-pair frames.
    center_a, normal_a, rms_a = _plane(terminal[0])
    center_b, normal_b, rms_b = _plane(terminal[1])
    origin = _mean((center_a, center_b))
    alignment = _dot(normal_a, normal_b)
    if alignment < 0:
        normal_b = tuple(-v for v in normal_b)
    z = _unit(tuple(a+b for a,b in zip(normal_a,normal_b)))
    inside = _mean((_plane(inner[0])[0], _plane(inner[1])[0]))
    outward = _sub(origin, inside)
    if abs(_dot(z, _unit(outward))) < 1e-8:
        raise _Unassessed("AMBIGUOUS_OUTWARD_DIRECTION")
    if _dot(z, outward) < 0:
        z = tuple(-v for v in z)
    across = _sub(terminal[1]["C1'"], terminal[0]["C1'"])
    x = _unit(tuple(a-_dot(across,z)*n for a,n in zip(across,z)))
    y = _unit(_cross(z,x))
    return {
        "origin": list(origin), "x": list(x), "y": list(y), "z": list(z),
        "units": "angstrom", "convention": "terminal-six-ring-area-normal-v1",
        "terminal_base_plane_angle_degrees": math.degrees(math.acos(min(1.,abs(alignment)))),
        "terminal_ring_plane_rms_angstrom": [rms_a,rms_b],
        "inward_pair_center": list(inside),
    }


def inspect_end_assignments(
    model_path: Path, assignments: Iterable[EndAssignment], *,
    expected_sha256: str, max_distance_angstrom: float, max_pairs: int = 100_000,
) -> dict:
    """Verify exact PDB bytes and describe caller-declared end assignments.

    Malformed inputs or source checksum mismatch fail the request. Missing or
    ambiguous selected residues produce per-end UNASSESSED outcomes, never
    inferred termini. No filesystem paths are emitted; relocating unchanged
    inputs does not change the result. All topology remains caller-declared.
    """
    # Reuse primitive validation for shared hash, budget and radius semantics.
    propose_connections([], source_model_sha256=expected_sha256,
                        max_distance_angstrom=max_distance_angstrom, max_pairs=max_pairs)
    rows = list(assignments)
    if any(not isinstance(row, EndAssignment) for row in rows):
        raise ValueError("assignments must contain EndAssignment records")
    if len({row.end_id for row in rows}) != len(rows):
        raise ValueError("Duplicate end_id in assignments")
    rows.sort(key=lambda row: row.end_id)
    overhangs = [site for row in rows for site in row.overhang_sites]
    if len(set(overhangs)) != len(overhangs):
        raise ValueError("A coordinate overhang site cannot belong to multiple ends")
    data = Path(model_path).read_bytes()
    digest = sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Source model checksum mismatch")
    atoms = _read_atoms(data)
    end_reports, screening_ends = [], []
    for row in rows:
        entry = {"end_id": row.end_id, "state": row.state, "polarity": row.polarity,
                 "assessment": "UNASSESSED", "sequence": None, "frame": None, "issues": []}
        try:
            resolved = {site: _residue(atoms, site) for site in
                        row.overhang_sites + row.terminal_pair + row.inner_pair}
            for pair in (row.terminal_pair, row.inner_pair):
                if resolved[pair[0]][0] + resolved[pair[1]][0] not in ("AT","TA","GC","CG"):
                    raise _Unassessed("UNSUPPORTED_PAIR")
            frame = _frame([resolved[s][1] for s in row.terminal_pair],
                           [resolved[s][1] for s in row.inner_pair])
            sequence = "".join(resolved[s][0] for s in row.overhang_sites)
            entry.update(assessment="FRAME_AVAILABLE", sequence=sequence, frame=frame)
            screening_ends.append(DuplexEnd(row.end_id, sequence, row.polarity,
                                           tuple(frame["origin"]), row.state))
        except _Unassessed as exc:
            entry["issues"].append({"code": exc.code,
                                    "site": asdict(exc.site) if exc.site else None})
        end_reports.append(entry)
    screening = propose_connections(screening_ends, source_model_sha256=digest,
                                    max_distance_angstrom=max_distance_angstrom, max_pairs=max_pairs)
    manifest = json.loads(json.dumps([asdict(row) for row in rows], allow_nan=False))
    manifest_hash = sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    incomplete = any(e["assessment"] == "UNASSESSED" for e in end_reports)
    state = "INCOMPLETE_ASSESSMENT" if incomplete else (
        "CANDIDATES_FOR_REVIEW" if screening["candidates"] else "NO_CANDIDATES")
    return {
        "schema_version": 1, "kind": "topostitch-coordinate-end-report",
        "source_model_sha256": digest, "source_bytes_verified": True,
        "source_model_size_bytes": len(data), "format": "pdb", "model_scope": "single_model",
        "assignments": manifest, "assignments_sha256": manifest_hash,
        "assignment_authority": "caller_declared_not_inferred",
        "ends": end_reports, "screening": screening,
        "workflow": {"proposal_state": state, "execution_state": "NOT_ATTEMPTED",
                     "review_state": "UNREVIEWED"},
        "changes": [], "runtime_authority": False, "geometry_validated": False,
        "inspection_required": True,
        "limitations": ["Declared terminal pairing, strand order and polarity are not validated",
                        "Frames describe coordinates; they do not establish valid stacking or helicity",
                        "No periodic images, alternate conformer choice or mmCIF adapter",
                        "No model edits, refinement or checkpoint selection"],
    }
