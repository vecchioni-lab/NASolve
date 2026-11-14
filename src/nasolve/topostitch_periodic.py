"""Read-only periodic candidate search, with optional Gemmi crystallography.

The supplied end inventory is not inferred or approved here. All results are
hypotheses; exact relative image operators are retained for later inspection.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from itertools import combinations_with_replacement, product
import json
import math
from pathlib import Path

from .topostitch import DuplexEnd, propose_connections
from .topostitch_coordinates import inspect_end_assignments

_CART_TOL = 1e-7
_FRAC_TOL = 1e-9


def _gemmi():
    try:
        import gemmi
    except ImportError as exc:
        raise RuntimeError("Periodic TopoStitch requires the optional NASolve[topology] installation") from exc
    return gemmi


def _crystal(parameters, name):
    gemmi = _gemmi()
    if not isinstance(parameters, (tuple, list)) or len(parameters) != 6:
        raise ValueError("cell_parameters must contain a,b,c,alpha,beta,gamma")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in parameters):
        raise ValueError("Cell parameters must be finite numbers")
    a,b,c,alpha,beta,gamma = parameters
    if min(a,b,c) <= 0 or any(not 0 < v < 180 for v in (alpha,beta,gamma)):
        raise ValueError("Invalid unit cell lengths or angles")
    ca,cb,cg = (math.cos(math.radians(v)) for v in (alpha,beta,gamma))
    if 1-ca*ca-cb*cb-cg*cg+2*ca*cb*cg <= 1e-12:
        raise ValueError("Degenerate or impossible cell metric")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Explicit space_group is required")
    group = gemmi.find_spacegroup_by_name(name)
    if group is None:
        raise ValueError("Unrecognized space_group")
    # Improper operations would require a separate chirality policy for DNA.
    if not group.is_sohncke():
        raise ValueError("Initial DNA periodic search supports Sohncke space groups only")
    cell = gemmi.UnitCell(*parameters)
    if not math.isfinite(cell.volume) or cell.volume <= 0:
        raise ValueError("Invalid unit cell volume")
    if not cell.is_compatible_with_spacegroup(group):
        raise ValueError("Cell metric is incompatible with the supplied space group setting")
    return gemmi, cell, group


def _op_key(op):
    return tuple(v for row in op.rot for v in row) + tuple(op.tran)


def _image_record(op, gemmi):
    wrapped = gemmi.Op(op.triplet()).wrap()
    shift = [(a-b)//op.DEN for a,b in zip(op.tran,wrapped.tran)]
    return {"symmetry_operation": wrapped.triplet(), "lattice_translation": shift,
            "operator_xyz": op.triplet(), "rotation_numerators": op.rot,
            "translation_numerators": op.tran, "denominator": op.DEN}


def propose_periodic_connections(
    ends, *, cell_parameters, space_group: str, source_model_sha256: str,
    max_distance_angstrom: float, max_pairs: int = 100_000,
    max_image_tests: int = 100_000,
) -> dict:
    """Enumerate compatible endpoint images inside a bounded Cartesian sphere.

    This is complete only for supplied available canonical ends, exact full
    overhang complementarity and the declared radius. No oriented-frame,
    atom-orbit distinctness, packing, closure or diffraction test is performed.
    A special-position or coincident-center image remains explicitly unvalidated.
    """
    rows = list(ends)
    # Validate all initial API invariants before doing crystallographic work.
    base = propose_connections(rows, source_model_sha256=source_model_sha256,
                               max_distance_angstrom=max_distance_angstrom, max_pairs=max_pairs)
    if type(max_image_tests) is not int or max_image_tests < 1:
        raise ValueError("max_image_tests must be a positive integer")
    gemmi, cell, group = _crystal(cell_parameters, space_group)
    rows.sort(key=lambda e: e.end_id)
    active = [e for e in rows if e.state == "available" and e.sequence is not None]
    if len(active)*(len(active)+1)//2 > max_pairs:
        raise ValueError("Periodic pair search budget exceeded (including self images)")
    fractions = {}
    for e in active:
        f = cell.fractionalize(gemmi.Position(*e.position))
        xyz = (f.x,f.y,f.z)
        if any(not math.isfinite(v) or abs(v) > 1e6 for v in xyz):
            raise ValueError("Fractional coordinates exceed the supported numerical range")
        fractions[e.end_id] = xyz
    # Each row of F maps a Cartesian displacement to one fractional component.
    # Cauchy-Schwarz bounds that component over the Cartesian search sphere.
    bounds = [(max_distance_angstrom+_CART_TOL)*math.hypot(*r)+_FRAC_TOL
              for r in cell.frac.mat.tolist()]
    if any(not math.isfinite(b) for b in bounds):
        raise ValueError("Search radius exceeds the supported numerical range")
    ops = sorted(group.operations(), key=_op_key)
    complement = str.maketrans("ACGT", "TGCA")
    candidates, seen, tested = [], set(), 0
    for left,right in combinations_with_replacement(active,2):
        if left.polarity != right.polarity or left.sequence != right.sequence.translate(complement)[::-1]:
            continue
        lf, rf = fractions[left.end_id], fractions[right.end_id]
        for op in ops:
            transformed = op.apply_to_xyz(rf)
            center = [a-b for a,b in zip(lf,transformed)]
            intervals = [(math.ceil(c-b), math.floor(c+b)) for c,b in zip(center,bounds)]
            count = math.prod(max(0,hi-lo+1) for lo,hi in intervals)
            if tested + count > max_image_tests:
                raise ValueError("Periodic image search budget exceeded; no partial report returned")
            tested += count
            if count == 0:
                continue
            ranges = [range(lo,hi+1) for lo,hi in intervals]
            for shift in product(*ranges):
                full = op.translated([op.DEN*n for n in shift])
                key = _op_key(full)
                inverse_key = _op_key(full.inverse())
                if left.end_id == right.end_id:
                    if full.triplet() == "x,y,z" or key > inverse_key:
                        continue
                edge_key = (left.end_id,right.end_id,key)
                if edge_key in seen:
                    continue
                target_frac = [v+n for v,n in zip(transformed,shift)]
                point = cell.orthogonalize(gemmi.Fractional(*target_frac))
                target = (point.x,point.y,point.z)
                distance = math.dist(left.position,target)
                if distance > max_distance_angstrom+_CART_TOL:
                    continue
                seen.add(edge_key)
                candidates.append({
                    "ends": [left.end_id,right.end_id], "edge_type": "base_pairing",
                    "target_image": _image_record(full,gemmi),
                    "reciprocal_image": _image_record(full.inverse(),gemmi),
                    "target_position_angstrom": list(target), "distance_angstrom": distance,
                    "residue_pairs": [[i,len(right.sequence)-1-i] for i in range(len(left.sequence))],
                    "geometry_validated": False, "image_distinctness_validated": False,
                    "coincident_reference_points": distance <= _CART_TOL,
                    "requires_global_assignment_review": True,
                    "self_image_inverse_is_same_operator": (
                        key == inverse_key if left.end_id == right.end_id else None),
                    "self_image_capacity_warning": (
                        "Distinct forward and reciprocal images may require two partners at one end"
                        if left.end_id == right.end_id and key != inverse_key else None),
                })
    candidates.sort(key=lambda c: (c["ends"],c["target_image"]["rotation_numerators"],
                                    c["target_image"]["translation_numerators"]))
    incident = {e.end_id: [] for e in rows}
    for i,candidate in enumerate(candidates):
        candidate["candidate_index"] = i
        for name in set(candidate["ends"]):
            incident[name].append(i)
    end_reports = []
    for e in rows:
        indices = incident[e.end_id]
        if e.state != "available" or e.sequence is None:
            status = "EXCLUDED"
        elif not indices:
            status = "NO_CANDIDATE"
        elif len(indices)>1 or any(len(incident[n])>1 for i in indices for n in candidates[i]["ends"]):
            status = "COMPETING_CANDIDATES"
        else:
            status = "SINGLE_CANDIDATE_NOT_CONFIRMED"
        end_reports.append({"end_id": e.end_id,"state": e.state,"status": status,
                            "candidate_indices": indices})
    inputs = json.loads(json.dumps({"ends": [asdict(e) for e in rows],
        "source_model_sha256": source_model_sha256,"cell_parameters": list(map(float,cell_parameters)),
        "space_group": group.xhm(),"hall_symbol": group.hall,
        "max_distance_angstrom": float(max_distance_angstrom),"max_pairs": max_pairs,
        "max_image_tests": max_image_tests}, allow_nan=False))
    digest = sha256(json.dumps(inputs,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"schema_version": 1,"kind": "topostitch-periodic-candidate-report",
        "algorithm": "metric-bounded-periodic-overhang-screen-v1", "gemmi_version": gemmi.__version__,
        "source_model_sha256": source_model_sha256,"source_bytes_verified": False,
        "inputs": inputs,"input_sha256": digest,"image_tests": tested,
        "cartesian_tolerance_angstrom": _CART_TOL,"fractional_bound_padding": _FRAC_TOL,
        "search_complete_within_declared_scope": True,
        "reciprocal_self_edges_deduplicated": True,"special_position_orbits_reduced": False,
        "candidates": candidates,"ends": end_reports,"selected_candidate": None,
        "no_connection_alternative": True,"geometry_validated": False,
        "runtime_authority": False,"inspection_required": True,"changes": [],
        "workflow": {"proposal_state": "CANDIDATES_FOR_REVIEW" if candidates else "NO_CANDIDATES",
                     "execution_state": "NOT_ATTEMPTED","review_state": "UNREVIEWED"},
        "limitations": base["limitations"][1:]+[
            "No orientation or atom-orbit distinctness test; coincident centers may be the same physical site",
            "Special-position stabilizer equivalences are retained, not independent evidence",
            "Completeness applies only to supplied ends, exact full complements and the declared radius"]}


def _frame_observations(coordinate, periodic, cell, gemmi):
    """Transform observed axes for display; never use them as acceptance gates."""
    frames = {e["end_id"]: e["frame"] for e in coordinate["ends"] if e["frame"] is not None}
    observations = []
    def angle(a, b):
        norms = math.hypot(*a)*math.hypot(*b)
        if norms < 1e-12:
            return None
        return math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(a,b))/norms))))
    for edge in periodic["candidates"]:
        left,right = (frames[name] for name in edge["ends"])
        op = gemmi.Op(edge["target_image"]["operator_xyz"])
        axes = {}
        for axis in ("x","y","z"):
            v = cell.fractionalize(gemmi.Position(*right[axis]))
            f = (v.x,v.y,v.z)
            rotated = [sum(row[i]*f[i] for i in range(3))/op.DEN for row in op.rot]
            cart = cell.orthogonalize(gemmi.Fractional(*rotated))
            axes[axis] = [cart.x,cart.y,cart.z]
        delta = [a-b for a,b in zip(edge["target_position_angstrom"],left["origin"])]
        coincident = edge["coincident_reference_points"]
        observations.append({
            "candidate_index": edge["candidate_index"],
            "source_frame": {key: left[key] for key in ("origin","x","y","z")},
            "target_image_frame": {"origin": edge["target_position_angstrom"],**axes},
            "outward_axis_angle_degrees": angle(left["z"],axes["z"]),
            "source_facing_angle_degrees": None if coincident else angle(left["z"],delta),
            "target_facing_angle_degrees": None if coincident else angle(axes["z"],[-v for v in delta]),
            "acceptance_evaluated": False,
            "note": "Observed end-frame directions only; no helical-phase or closure test",
        })
    return observations


def crystal_from_pdb_bytes(data):
    """Read the explicit conventional crystal frame; never infer a default."""
    lines = data.decode("ascii").splitlines()
    headers = [line for line in lines if line[:6] == "CRYST1"]
    if len(headers) != 1:
        raise ValueError("Exactly one CRYST1 record is required; no default symmetry is inferred")
    header = headers[0]
    try:
        params = tuple(float(header[a:b]) for a,b in ((6,15),(15,24),(24,33),(33,40),(40,47),(47,54)))
    except ValueError as exc:
        raise ValueError("Malformed CRYST1 cell parameters") from exc
    group_name = header[55:66].strip()
    gemmi, cell, _ = _crystal(params,group_name)
    scales = [line for line in lines if line[:5] == "SCALE"]
    if scales:
        try:
            if len(scales) != 3 or {line[:6] for line in scales} != {"SCALE1","SCALE2","SCALE3"}:
                raise ValueError("Incomplete SCALE")
            for line in scales:
                row = int(line[5])-1
                numbers = [float(line[a:b]) for a,b in ((10,20),(20,30),(30,40),(45,55))]
                expected = cell.frac.mat.tolist()[row]+[0.]
                if any(not math.isfinite(v) or abs(v-e)>1.1e-6 for v,e in zip(numbers,expected)):
                    raise ValueError("Nonstandard SCALE")
        except (ValueError, IndexError) as exc:
            raise ValueError("SCALE must match the conventional cell fractionalization with zero offset") from exc
    return gemmi, cell, group_name


def inspect_periodic_end_assignments(
    model_path: Path, assignments, *, expected_sha256: str,
    max_distance_angstrom: float, max_pairs: int = 100_000,
    max_image_tests: int = 100_000,
) -> dict:
    """Combine the coordinate adapter with crystal context from exact PDB bytes.

    CRYST1 is required. Nonstandard/incomplete SCALE transforms are rejected,
    not silently interpreted in Gemmi's conventional orthogonal frame.
    """
    coordinate = inspect_end_assignments(model_path,assignments,expected_sha256=expected_sha256,
        max_distance_angstrom=max_distance_angstrom,max_pairs=max_pairs)
    data = Path(model_path).read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError("Source model checksum changed during periodic assessment")
    gemmi, cell, group_name = crystal_from_pdb_bytes(data)
    params = cell.parameters
    ends = [DuplexEnd(e["end_id"],e["sequence"],e["polarity"],tuple(e["frame"]["origin"]),e["state"])
            for e in coordinate["ends"] if e["assessment"] == "FRAME_AVAILABLE"]
    periodic = propose_periodic_connections(ends,cell_parameters=params,space_group=group_name,
        source_model_sha256=expected_sha256,max_distance_angstrom=max_distance_angstrom,
        max_pairs=max_pairs,max_image_tests=max_image_tests)
    workflow = dict(periodic["workflow"])
    if coordinate["workflow"]["proposal_state"] == "INCOMPLETE_ASSESSMENT":
        workflow["proposal_state"] = "INCOMPLETE_ASSESSMENT"
    return {"schema_version": 1,"kind": "topostitch-periodic-coordinate-report",
        "source_model_sha256": expected_sha256,"source_bytes_verified": True,
        "crystal_source": "verified_pdb_cryst1","coordinate_assessment": coordinate,
        "periodic_screening": periodic,
        "candidate_frame_observations": _frame_observations(coordinate,periodic,cell,gemmi),
        "workflow": workflow,"changes": [],
        "geometry_validated": False,"runtime_authority": False,"inspection_required": True}
