"""Cartesian departures from recorded intra-residue planes in a sealed refinement.

Only positive-weight plane members determine the plane. A recorded, active
180-degree angle can place a third atom on a line through two known atoms. Measure those
additional atoms separately so they cannot tilt the reference being tested.
"""
from collections import defaultdict, deque
from math import sqrt

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


def _fit_plane(points, weights):
    """Return a Cartesian distance function, or the reason the normal is undefined."""
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

    def distance(point):
        return float(abs((np.asarray(point) - origin - centre) @ axes[-1]))

    return distance, None


def measure_source_ring_arms(sources, observation, planes):
    """Measure a pendant carbon alkyne against its source ring alone, with equal atom weights."""
    import numpy as np
    from .cif_plane_coverage import source_ring_alkyne_arms

    atoms = defaultdict(dict)
    for atom in observation["atoms"]:
        atoms[_site(atom)][atom["atom_id"]] = atom
    by_site = defaultdict(list)
    for plane in planes:
        active = {m["atom"] for m in plane["members"] if m["weight"] > 0}
        by_site[plane["site"]].append((plane["proxy_index"], active))
    rows = []
    for declared in observation["sites"]:
        site = declared["site"]
        for arm, rings in source_ring_alkyne_arms(*sources[site]):
            row = dict(**declared, status="UNASSESSED", arm_atoms=list(arm),
                       candidate_ring_count=len(rings), ring_atoms=None, ring_rms_angstrom=None,
                       arm_distances_angstrom=None, captured_ring_planes=None, missing_atoms=[])
            rows.append(row)
            if len(rings) != 1:
                row["reason"] = "Multiple chordless six-membered source rings through the attachment"
                continue
            ring, = rings
            row["ring_atoms"] = list(ring)
            row["captured_ring_planes"] = [
                dict(proxy_index=index, positive_arm_members=[n for n in arm[1:] if n in active])
                for index, active in by_site[site] if set(ring) <= active
            ]
            required = set(ring) | set(arm)
            row["missing_atoms"] = sorted(required - atoms[site].keys())
            if row["missing_atoms"]:
                row["reason"] = "Source ring or arm atoms missing from the selected capture"
                continue
            coords = {n: _point(atoms[site][n]["xyz"]) for n in required}
            distance, reason = _fit_plane(np.array([coords[n] for n in ring]), np.ones(len(ring)))
            row["reason"] = reason
            if distance is not None:
                row.update(status="MEASURED",
                           ring_rms_angstrom=sqrt(sum(distance(coords[n])**2 for n in ring) / len(ring)),
                           arm_distances_angstrom={n: distance(coords[n]) for n in arm[1:]})
    return rows


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
