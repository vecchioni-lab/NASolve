"""Measure Altona–Sundaralingam pseudorotation from an occupied native furanose ring."""
from collections import Counter, defaultdict
from math import atan2, degrees, hypot, isfinite, pi, sin

from .cif_dihedral_conditioning import dihedral_geometry
from .refinement_plane_departures import _fit_plane_offsets


_RING = ("C4'", "O4'", "C1'", "C2'", "C3'")
_EDGES = tuple(zip(_RING, _RING[1:] + _RING[:1]))
_METHOD = "Altona–Sundaralingam 1972"


def _ring_measurement(positions, bonds, gemmi):
    import numpy as np

    missing = [name for name in _RING if name not in positions]
    if missing:
        return dict(status="UNASSESSED", reason="Missing, incorrectly typed or unoccupied " + ", ".join(missing))
    counts = Counter(tuple(sorted(name.replace("*", "'") for name in row["atoms"])) for row in bonds["rows"] or ()
                     if row["origin"] == "covalent geometry" and row["weight"] > 0)
    incomplete = [pair for pair in _EDGES if counts[tuple(sorted(pair))] != 1]
    if incomplete:
        return dict(status="UNASSESSED", reason="Each ring edge needs one printed positive covalent bond",
                    unverified_bonds=[list(pair) for pair in incomplete])

    ring = [positions[name] for name in _RING]
    cyclic = ring + ring[:3]
    torsions = []
    for i in range(len(ring)):
        points = cyclic[i:i+4]
        if dihedral_geometry(points)["near_collinear_review"]:
            return dict(status="UNASSESSED", reason="A nearly collinear ring path leaves the torsion unreliable")
        value = degrees(gemmi.calculate_dihedral(*(gemmi.Position(*p) for p in points)))
        if not isfinite(value):
            return dict(status="UNASSESSED", reason="The signed ring torsion is undefined")
        torsions.append(value)

    v0, v1, v2, v3, v4 = torsions
    y = (v4 + v1 - v3 - v0) / (2 * (sin(pi / 5) + sin(2 * pi / 5)))
    amplitude = hypot(v2, y)
    result = dict(torsions_deg=torsions, amplitude_deg=amplitude)
    plane, reason = _fit_plane_offsets(np.asarray(ring), np.ones(len(ring)))
    if plane is None:
        return dict(result, status="PHASE_UNRESOLVED", phase_deg=None, reason=reason)
    offset, normal = plane
    # If orthogonal projection fits in each atom's F8.3 rounding box, a flat
    # ring is compatible with these written positions. It has no unique phase.
    max_projection = max(abs(offset(p)) for p in ring) * max(abs(normal))
    if max_projection <= 0.0005 or amplitude == 0:
        return dict(result, status="PHASE_UNRESOLVED", phase_deg=None,
                    reason="The ring is compatible with a plane at PDB coordinate precision"
                    if max_projection <= 0.0005 else "The pseudorotation amplitude is zero")
    phase = degrees(atan2(y, v2)) % 360
    return dict(result, status="MEASURED", phase_deg=0.0 if phase == 360 else phase)


def read_sugar_puckers(raw, labels, residues, *, all_sites):
    """The existing PDB and GEO readers establish the site and the five covalent edges."""
    try:
        import gemmi
    except ImportError as exc:
        raise ValueError("--sugar-pucker requires NASolve[topology]") from exc
    selected = {(r["site"], r["component"]) for r in residues}
    positions, names, ambiguous = defaultdict(dict), defaultdict(dict), set()
    for line in raw.decode("ascii").splitlines():
        if line[:6] not in {"ATOM  ", "HETATM"}:
            continue
        (site, code, atom), xyz = labels[line[12:27]]
        key = (site, code)
        name = atom.replace("*", "'")
        if key not in selected or name not in _RING:
            continue
        if name in names[key]:
            ambiguous.add(key)
        names[key][name] = atom
        try:
            occupied = 0 < float(line[54:60]) <= 1
        except ValueError:
            occupied = False
        if occupied and line[76:78].strip().upper() == name[0]:
            positions[key][name] = xyz

    rows = []
    for residue in residues:
        site, code = residue["site"], residue["component"]
        key = (site, code)
        if key in ambiguous:
            result = dict(status="UNASSESSED", reason="Multiple atom names identify the same ring position")
        elif key in names:
            result = _ring_measurement(positions[key], residue["bonds"], gemmi)
            if any(name != atom for name, atom in names[key].items()):
                result["written_atom_names"] = names[key]
        else:
            result = dict(status="NO_NAMED_RING", reason="No conventionally named furanose ring atoms")
        rows.append(dict(site=site, component=code, **result))
    counts = Counter(row["status"] for row in rows)
    requested = len(rows) - counts["NO_NAMED_RING"] if all_sites else len(rows)
    status = "MEASURED" if requested and counts["MEASURED"] == requested else "REVIEW"
    return dict(method=_METHOD, ring_order=list(_RING), status=status, counts=dict(counts), sites=rows)


def print_sugar_puckers(report, label=""):
    counts = report["counts"]
    prefix = f"{label} " if label else ""
    print(f"{prefix}Sugar ring measurements in degrees ({_METHOD}). "
          + ", ".join(f"{n} {status}" for status, n in counts.items()))
    for row in report["sites"]:
        if row["status"] == "NO_NAMED_RING":
            continue
        if row["status"] == "MEASURED":
            print(f"  {row['site']} {row['component']} phase {row['phase_deg']:.1f}°, "
                  f"amplitude {row['amplitude_deg']:.1f}°.")
        else:
            print(f"  {row['site']} {row['component']} {row['status']}  {row['reason']}.")
