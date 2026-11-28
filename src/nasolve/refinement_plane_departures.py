"""Cartesian departures from recorded intra-residue planes in a sealed refinement.

Only positive-weight plane members determine the plane. A recorded, active
180-degree angle can place a third atom on a line through two known atoms. Measure those
additional atoms separately so they cannot tilt the reference being tested.
"""
from collections import defaultdict, deque
from math import asin, degrees, sqrt

from .cif_captured_geometry import _number, _observed, _point, _site


def _straight_angles(angles):
    """Index each recorded positive, exactly linear target by its three atoms."""
    by_atom = defaultdict(list)
    for index, row in enumerate(angles):
        if row["angle_ideal"] != 180 or row["weight"] is None:
            continue
        weight = _number(row["weight"])
        if weight < 0:
            raise ValueError("Negative captured linear angle weight")
        if weight == 0:
            continue
        ids = tuple(row["i_seqs"])
        if len(ids) != 3 or len(set(ids)) != 3:
            raise ValueError("Invalid captured linear angle endpoints")
        for atom in ids:
            by_atom[atom].append((index, ids, weight))
    return by_atom


def _linear_extensions(members, by_atom, atoms, coords, distance, site):
    """Retain one grounded linear-angle witness per extra atom, in capture order."""
    known = {member["i_seq"] for member in members if member["weight"] > 0}
    pending = deque(sorted(known))
    extensions = {}
    while pending:
        for index, indices, weight in by_atom[pending.popleft()]:
            unknown = [i for i in indices if i not in known]
            if len(unknown) != 1:
                continue
            tip, = unknown
            first, second = (i for i in indices if i != tip)
            if any(_site(atoms[i]) != site for i in indices):
                raise ValueError("Captured linear angle crosses the selected residue")
            if coords[first] == coords[second]:
                continue
            known.add(tip)
            pending.append(tip)
            extensions[tip] = dict(
                i_seq=tip, atom=atoms[tip]["atom_id"], angle_proxy_index=index,
                angle_i_seqs=list(indices), supporting_i_seqs=[first, second],
                angle_target_degrees=180., angle_weight=weight,
                distance_angstrom=distance(coords[tip]),
                observed_angle_degrees=_observed("angle", [coords[i] for i in indices]),
            )
    return [extensions[i] for i in sorted(extensions)]


def _fit_plane_offsets(points, weights):
    """Return a signed offset function and its unit normal, or a fit failure."""
    import numpy as np

    used = weights > 0
    if used.sum() < 3:
        return None, "Fewer than three positive-weight members"
    # Work relative to a member. Translation and common weight scale cancel.
    origin = points[used][0]
    relative = points[used] - origin
    scaled = weights[used] / weights[used].max()
    centre = np.average(relative, axis=0, weights=scaled)
    weighted = (relative - centre) * np.sqrt(scaled[:, None])
    _, singular, axes = np.linalg.svd(weighted, full_matrices=False)
    tolerance = np.finfo(float).eps * max(weighted.shape) * singular[0]
    if singular[1] - singular[2] <= tolerance:
        return None, "Positive-weight positions do not define a unique plane"

    normal = axes[-1]

    def offset(point):
        return float((np.asarray(point) - origin - centre) @ normal)

    return (offset, normal), None


def _fit_plane(points, weights):
    frame, reason = _fit_plane_offsets(points, weights)
    if frame is None:
        return None, reason
    offset, _ = frame
    return lambda point: abs(offset(point)), None


def _arm_bond_directions(arm, ring, coords, offset, normal):
    """Orient the fitted plane by the two source ring bonds at the attachment."""
    import numpy as np

    anchor, left, right = ring[0], ring[1], ring[-1]
    first, second = coords[left] - coords[anchor], coords[right] - coords[anchor]
    alignment = float(normal @ np.cross(first, second))
    scale = np.linalg.norm(first) * np.linalg.norm(second)
    result = dict(anchor=anchor, ring_flanks=[left, right], status="UNASSESSED")
    if abs(alignment) <= 16 * np.finfo(float).eps * scale:
        return dict(result, reason="The ring bonds at the anchor do not determine a side of the fitted plane")
    sign = 1 if alignment > 0 else -1
    segments = []
    for a, b in zip(arm, arm[1:]):
        vector = coords[b] - coords[a]
        length = float(np.linalg.norm(vector))
        if not length:
            return dict(result, reason=f"Coincident atoms leave the direction of {a}–{b} undefined")
        rise = sign * float(vector @ normal)
        elevation = degrees(asin(max(-1., min(1., rise / length))))
        segments.append(dict(atoms=[a, b], length_A=length, normal_rise_A=rise, elevation_deg=elevation))
    return dict(result, status="MEASURED", segments=segments,
                anchor_offset_A=sign * offset(coords[anchor]), tip_offset_A=sign * offset(coords[arm[-1]]))


def measure_ring_arm(arm, rings, positions):
    """Measure an explicitly assigned arm against its ring alone, with equal atom weights."""
    import numpy as np

    row = dict(status="UNASSESSED", arm_atoms=list(arm), candidate_ring_count=len(rings), ring_atoms=None,
               ring_rms_angstrom=None, arm_distances_angstrom=None, bond_directions=None, missing_atoms=[])
    if len(rings) != 1:
        return dict(row, reason="Multiple chordless six-membered source rings through the attachment")
    ring, = rings
    row["ring_atoms"] = list(ring)
    required = set(ring) | set(arm)
    row["missing_atoms"] = sorted(required - positions.keys())
    if row["missing_atoms"]:
        return dict(row, reason="Source ring or arm atoms missing from the selected capture")
    coords = {n: np.asarray(_point(positions[n])) for n in required}
    frame, reason = _fit_plane_offsets(np.array([coords[n] for n in ring]), np.ones(len(ring)))
    if frame is None:
        return dict(row, reason=reason)
    offset, normal = frame
    return dict(row, status="MEASURED", reason=None,
                ring_rms_angstrom=sqrt(sum(offset(coords[n])**2 for n in ring) / len(ring)),
                arm_distances_angstrom={n: abs(offset(coords[n])) for n in arm[1:]},
                bond_directions=_arm_bond_directions(arm, ring, coords, offset, normal))


def measure_source_ring_arms(sources, observation, planes):
    """Bind native plane membership and captured positions to the selected source arms."""
    from .cif_plane_coverage import source_ring_alkyne_arms

    positions = defaultdict(dict)
    for atom in observation["atoms"]:
        positions[_site(atom)][atom["atom_id"]] = atom.get("xyz")
    by_site = defaultdict(list)
    for plane in planes:
        active = {m["atom"] for m in plane["members"] if m["weight"] > 0}
        by_site[plane["site"]].append((plane["proxy_index"], active))
    rows = []
    for declared in observation["sites"]:
        site = declared["site"]
        for arm, rings in source_ring_alkyne_arms(*sources[site]):
            reading = measure_ring_arm(arm, rings, positions[site])
            coverage = None
            if reading["ring_atoms"] is not None:
                coverage = [dict(proxy_index=i, positive_arm_members=[n for n in arm[1:] if n in active])
                            for i, active in by_site[site] if set(reading["ring_atoms"]) <= active]
            rows.append(dict(declared, **reading, captured_ring_planes=coverage))
    return rows


def _arm_endpoints(sources, phase):
    arms = measure_source_ring_arms(sources, phase, [])
    if not arms:
        return {}
    atoms = {(_site(atom), atom["atom_id"]): atom for atom in phase["atoms"]}
    targets = defaultdict(list)
    for bond in phase["geometry"]["proxy_details"]["bond_simple"]:
        weight = bond["weight"]
        targets[frozenset(bond["i_seqs"])].append(dict(
            ideal_A=bond["distance_ideal"], weight=weight,
            sigma_A=1 / sqrt(weight) if weight is not None and weight > 0 else None,
            origin_id=bond["origin_id"], symmetry_operation=bond.get("symmetry_operation"),
        ))
    rows = {}
    for arm in arms:
        site, path = arm["site"], tuple(arm["arm_atoms"])
        measured = arm["arm_distances_angstrom"]
        row = dict(status=arm["status"], reason=arm["reason"], ring_atoms=arm["ring_atoms"],
                   tip_height_A=measured[path[-1]] if measured is not None else None,
                   bond_directions=arm["bond_directions"], terminal_bond_A=None, terminal_targets=None)
        outside, tip = (atoms.get((site, name)) for name in path[-2:])
        if outside is not None and tip is not None:
            row["terminal_bond_A"] = _observed("bond_simple", [outside["xyz"], tip["xyz"]])
            recorded = targets[frozenset((outside["i_seq"], tip["i_seq"]))]
            row["terminal_targets"] = [t for t in recorded if t["symmetry_operation"] in (None, "x,y,z")]
            images = [t for t in recorded if t["symmetry_operation"] not in (None, "x,y,z")]
            if images:
                row["terminal_image_targets"] = images
        rows[(site, arm["component"], path)] = row
    return rows


def compare_source_ring_arms(sources, preflight, refined):
    """Compare the same chemical arm at two native stages using each stage's atom indices."""
    phases = {"preflight": preflight, "refined": refined}
    unavailable = {stage: phase["reason"] for stage, phase in phases.items() if phase["status"] == "UNASSESSED"}
    result = dict(policy_id="refinement-source-ring-arm-change-v1", status="UNASSESSED",
                  unavailable=unavailable, arms=[], scientific_approval="NOT_RUN")
    if unavailable:
        return result
    before, after = (_arm_endpoints(sources, phase) for phase in (preflight, refined))
    if before.keys() != after.keys():
        raise ValueError("The observed stages have different source-defined arms")
    if not before:
        return dict(result, status="NO_ELIGIBLE_ARMS")
    result["status"] = "MEASURED"
    for key, old in before.items():
        new = after[key]
        if old["ring_atoms"] != new["ring_atoms"]:
            raise ValueError("The observed stages have different source ring atoms")
        if old["status"] != "MEASURED" or new["status"] != "MEASURED":
            result["status"] = "PARTIAL"
        row = dict(site=key[0], component=key[1], arm_atoms=list(key[2]), preflight=old, refined=new)
        for field, change in (("tip_height_A", "tip_height_change_A"), ("terminal_bond_A", "terminal_bond_change_A")):
            row[change] = None if old[field] is None or new[field] is None else new[field] - old[field]
        result["arms"].append(row)
    return result


def _measure_plane(index, proxy, atoms, coords, angles, omit_each_member):
    import numpy as np

    ids = proxy["i_seqs"]
    if not ids or len(set(ids)) != len(ids) or len(proxy["weights"]) != len(ids):
        raise ValueError("Invalid captured plane membership or weight count")
    site = _site(atoms[ids[0]])
    if any(_site(atoms[i]) != site for i in ids):
        raise ValueError("Captured plane crosses the selected residue")
    weights = np.array([_number(w) for w in proxy["weights"]])
    if np.any(weights < 0):
        raise ValueError("Negative captured plane weight")
    members = [dict(i_seq=i, atom=atoms[i]["atom_id"], weight=float(w), distance_angstrom=None)
               for i, w in zip(ids, weights)]
    row = dict(proxy_index=index, origin_id=proxy["origin_id"], site=site,
               component=atoms[ids[0]]["identity"]["resname"].strip(), members=members,
               status="UNASSESSED", reason=None, positive_member_rms_angstrom=None, linear_extensions=[])
    points = np.array([coords[i] for i in ids])
    distance, reason = _fit_plane(points, weights)
    for pos, member in enumerate(members):
        if distance is not None:
            member["distance_angstrom"] = distance(points[pos])
        if omit_each_member:
            other_distance, other_reason = distance, reason
            if weights[pos] > 0:
                other_weights = weights.copy()
                other_weights[pos] = 0.
                other_distance, other_reason = _fit_plane(points, other_weights)
            member["other_members"] = {
                "distance_angstrom": other_distance(points[pos]) if other_distance is not None else None,
                "reason": other_reason,
            }
    if distance is None:
        row["reason"] = reason
        return row
    rms = sqrt(sum(m["distance_angstrom"]**2 for m in members if m["weight"] > 0) / int((weights > 0).sum()))
    row.update(status="MEASURED", positive_member_rms_angstrom=rms,
               linear_extensions=_linear_extensions(members, angles, atoms, coords, distance, site))
    return row


def describe_planes(observation, *, omit_each_member=False):
    """Describe literal Cartesian geometry from an already authenticated snapshot."""
    if type(omit_each_member) is not bool:
        raise ValueError("Plane member omission choice must be boolean")
    result = dict(schema_version=1, policy_id="refinement-declared-site-plane-departures-v1",
                  status="UNASSESSED", reason=observation.get("reason"), planes=[],
                  coordinate_scope="LITERAL_SAME_SITE_CARTESIAN", symmetry_context="UNASSESSED",
                  sites_without_captured_plane=None,
                  coordinate_precision=observation.get("coordinate_precision"),
                  model_state_sha256=observation.get("model_state_sha256"),
                  native_residuals="UNASSESSED", scientific_approval="NOT_RUN", automatic_adoption=False)
    if omit_each_member:
        result.update(schema_version=2, policy_id="refinement-declared-site-plane-departures-v2")
    if observation["status"] == "UNASSESSED":
        return result
    if observation["status"] != "OBSERVED":
        raise ValueError("Require a captured native observation")
    proxies = observation["geometry"]["proxy_details"]
    declared_sites = {row["site"] for row in observation["sites"]}
    if not proxies["planarity"]:
        result["sites_without_captured_plane"] = sorted(declared_sites)
        result["reason"] = "No intra-residue plane was captured"
        return result
    atoms = {a["i_seq"]: a for a in observation["atoms"]}
    coords = {i: _point(a["xyz"]) for i, a in atoms.items()}
    angles = _straight_angles(proxies["angle"])
    planes = [_measure_plane(i, p, atoms, coords, angles, omit_each_member) for i, p in enumerate(proxies["planarity"])]
    measured = sum(p["status"] == "MEASURED" for p in planes)
    result["planes"] = planes
    uncovered = sorted(declared_sites - {plane["site"] for plane in planes})
    result["sites_without_captured_plane"] = uncovered
    if measured == len(planes) and not uncovered:
        result.update(status="MEASURED", reason=None)
    elif measured:
        result.update(status="PARTIAL", reason="A declared site lacks a captured plane or a captured plane lacks a unique fit")
    else:
        result["reason"] = "No captured plane had a unique measurable fit"
    return result
