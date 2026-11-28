"""Observe the nonbridging oxygens in two explicitly assigned, stacked base pairs."""
from hashlib import sha256
from math import acos, degrees, isfinite

from .refinement_link_geometry import _model_labels
from .refinement_plane_departures import _fit_plane_offsets
from .topostitch_coordinates import _RING
from .topostitch_graph import _compose, _operator
from .topostitch_images import _cartesian, _fractional
from .topostitch_periodic import _op_key, crystal_from_pdb_bytes


class _Unavailable(ValueError):
    """The specified copies or atoms do not define this local measurement."""


def _unit(vector):
    import numpy as np

    length = np.linalg.norm(vector)
    if not isfinite(length) or length <= 1e-9:
        raise _Unavailable("Coincident positions leave the duplex direction undefined")
    return vector / length


def _mean_normal(first, second):
    dot = float(first @ second)
    if abs(dot) <= 1e-9:
        raise _Unavailable("Perpendicular planes do not define a unique mean normal")
    return _unit(first + (second if dot > 0 else -second))


def inspect_duplex_direction(model, phosphate, partners, partner_images=None):
    """Return local projections in Å. Partner images are relative to each paired anchor.

    The phosphate reading supplies the exact model and O3′ image. The caller
    declares two consecutive pairs on one duplex arm. Pairing, covalency and
    diffraction support require separate evidence.
    """
    import numpy as np

    if not isinstance(partners, (tuple, list)) or len(partners) != 2 or not all(isinstance(p, str) and p for p in partners):
        raise ValueError("Declare the partner of the O3' residue and the partner of the phosphate residue")
    if partner_images is None:
        partner_images = ("x,y,z", "x,y,z")
    if not isinstance(partner_images, (tuple, list)) or len(partner_images) != 2:
        raise ValueError("Require one relative crystal image for each paired residue")
    raw, labels = _model_labels(model)
    if sha256(raw).hexdigest() != phosphate["model_sha256"]:
        raise ValueError("Duplex step coordinates differ from the inspected phosphate model")
    gemmi, cell, group = crystal_from_pdb_bytes(raw)
    members = {_op_key(op) for op in gemmi.find_spacegroup_by_name(group).operations()}
    relative = [_operator(x, gemmi, members) for x in partner_images]
    result = dict(method="declared-duplex-phosphate-projection-v1", status="UNASSESSED",
                  partner_sites=list(partners), partner_relative_images=[op.triplet() for op in relative])
    if phosphate["o3_image"] is None or not phosphate["o3"] or not phosphate["phosphate"]:
        return dict(result, reason="The phosphate and its donor need resolved coordinate images")
    donor, acceptor = phosphate["o3"][0], phosphate["phosphate"][0]
    donor_op = _operator(phosphate["o3_image"], gemmi, members)
    identity = gemmi.Op("x,y,z")
    steps = [(donor, donor_op, partners[0], _compose(donor_op, relative[0])),
             (acceptor, identity, partners[1], relative[1])]
    copies = [(site, _op_key(op)) for a, ao, b, bo in steps for site, op in ((a, ao), (b, bo))]
    if len(set(copies)) != 4:
        raise ValueError("A duplex step requires four distinct residue copies")
    atoms = {site: {} for site, _ in copies}
    for line in raw.decode("ascii").splitlines():
        if line[:6] in {"ATOM  ", "HETATM"}:
            (site, component, name), xyz = labels[line[12:27]]
            if site in atoms:
                atoms[site][name] = (component, line[76:78].strip().upper(), float(line[54:60]), xyz)

    def point(site, name, op):
        record = atoms[site].get(name)
        if record is None or record[1] != name[0] or not 0 < record[2] <= 1:
            raise _Unavailable(f"Require one occupied {name[0]} atom named {name} at {site}")
        frac = _fractional(record[3], cell, gemmi)
        return np.asarray(_cartesian(op.apply_to_xyz(frac), cell, gemmi))

    def base(site, op):
        purine = ("N7", "C8", "N9")
        names = _RING + (purine if any(name in atoms[site] for name in purine) else ())
        ring = np.array([point(site, name, op) for name in names])
        centre = ring.mean(axis=0)
        frame, reason = _fit_plane_offsets(ring, np.ones(len(ring)))
        if reason:
            raise _Unavailable(f"{site} ring plane unavailable: {reason}")
        _, normal = frame
        detail = dict(site=site, component=atoms[site][names[0]][0], image=op.triplet(), ring_atoms=list(names))
        return centre, normal, point(site, "C1'", op), detail

    try:
        for name in ("OP3", "O3P"):
            terminal = atoms[acceptor].get(name)
            if terminal is not None and terminal[2] > 0:
                raise _Unavailable(f"The phosphate bears an occupied {name}")
        point(acceptor, "O5'", identity)
        phosphorus, op1, op2 = (point(acceptor, name, identity) for name in ("P", "OP1", "OP2"))
        centres, normals, sugars, pairs = [], [], [], []
        for a, ao, b, bo in steps:
            ac, an, ag, anchor = base(a, ao)
            bc, bn, bg, partner = base(b, bo)
            centres.append((ac + bc) / 2)
            sugars.append((ag + bg) / 2)
            normals.append(_mean_normal(an, bn))
            span = float(np.linalg.norm(ag - bg))
            if span <= 1e-9:
                raise _Unavailable("Pair partners have coincident C1' atoms")
            pairs.append(dict(anchor=anchor, partner=partner, c1_span_A=span))
        normal = _mean_normal(*normals)
        step_distance = float(np.linalg.norm(centres[1] - centres[0]))
        if step_distance <= 1e-9:
            raise _Unavailable("The two declared pair centres coincide")

        def project(origins):
            radius = phosphorus - np.mean(origins, axis=0)
            outward = _unit(radius - (radius @ normal) * normal)
            first, second = (float((o - phosphorus) @ outward) for o in (op1, op2))
            return dict(midpoint_A=(first + second) / 2, OP1_A=first, OP2_A=second)

        return dict(result, status="MEASURED", pairs=pairs, pair_centre_distance_A=step_distance,
                    pair_tilt_degrees=degrees(acos(min(1., abs(float(normals[0] @ normals[1]))))),
                    ring_centres=project(centres), c1_midpoints=project(sugars))
    except _Unavailable as exc:
        return dict(result, reason=str(exc))
