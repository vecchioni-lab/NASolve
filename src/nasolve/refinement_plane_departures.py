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
                distance_angstrom=distance(tip),
                observed_angle_degrees=_observed("angle", [coords[i] for i in indices]),
            )
    return [extensions[i] for i in sorted(extensions)]


def _measure_plane(index, proxy, atoms, coords, angles):
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
    used = weights > 0
    if used.sum() < 3:
        row["reason"] = "Fewer than three positive-weight members"
        return row

    # Work relative to a member, with normalized weights. Translation and
    # multiplying all weights by a common positive factor leave the fit intact.
    points = np.array([coords[i] for i in ids])
    origin = points[used][0]
    relative = points[used] - origin
    scaled = weights[used] / weights[used].max()
    centre = np.average(relative, axis=0, weights=scaled)
    weighted = (relative - centre) * np.sqrt(scaled[:, None])
    _, singular, axes = np.linalg.svd(weighted, full_matrices=False)
    tolerance = np.finfo(float).eps * max(weighted.shape) * singular[0]
    if singular[1] - singular[2] <= tolerance:
        row["reason"] = "Positive-weight positions do not define a unique plane"
        return row

    def distance(i):
        return float(abs((np.asarray(coords[i]) - origin - centre) @ axes[-1]))

    for member in members:
        member["distance_angstrom"] = distance(member["i_seq"])
    rms = sqrt(sum(m["distance_angstrom"]**2 for m in members if m["weight"] > 0) / int(used.sum()))
    row.update(status="MEASURED", positive_member_rms_angstrom=rms,
               linear_extensions=_linear_extensions(members, angles, atoms, coords, distance, site))
    return row


def describe_planes(observation):
    """Describe literal Cartesian geometry from an already authenticated snapshot."""
    result = dict(schema_version=1, policy_id="refinement-declared-site-plane-departures-v1",
                  status="UNASSESSED", reason=observation.get("reason"), planes=[],
                  coordinate_scope="LITERAL_SAME_SITE_CARTESIAN", symmetry_context="UNASSESSED",
                  sites_without_captured_plane=None,
                  coordinate_precision=observation.get("coordinate_precision"),
                  model_state_sha256=observation.get("model_state_sha256"),
                  native_residuals="UNASSESSED", scientific_approval="NOT_RUN", automatic_adoption=False)
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
    planes = [_measure_plane(i, p, atoms, coords, angles) for i, p in enumerate(proxies["planarity"])]
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
