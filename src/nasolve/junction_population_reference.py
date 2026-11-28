"""Compare a named standard phosphodiester and its sugars with published outer limits."""
from hashlib import sha256
from importlib.resources import files
import json
from math import dist, isfinite
from pathlib import Path

from .cif_stereochemistry_audit import VOLUME_EPSILON, _volume
from .refinement_link_geometry import _model_labels
from .topostitch_contacts import _angle
from .topostitch_images import _cartesian, _fractional
from .topostitch_periodic import crystal_from_pdb_bytes


_FAMILY = {**dict.fromkeys(("DA", "DC", "DG", "DT"), "DNA"),
           **dict.fromkeys(("A", "C", "G", "U"), "RNA")}
_BASE_ATOMS = {
    "A": "N9 C8 N7 C5 C6 N6 N1 C2 N3 C4",
    "G": "N9 C8 N7 C5 C6 O6 N1 C2 N2 N3 C4",
    "C": "N1 C2 O2 N3 C4 N4 C5 C6",
    "T": "N1 C2 O2 N3 C4 O4 C5 C7 C6",
    "U": "N1 C2 O2 N3 C4 O4 C5 C6",
}
_BACKBONE = {"C1'", "C2'", "C3'", "C4'", "C5'", "O3'", "O4'", "O5'", "P", "OP1", "OP2"}


def _coordinates(raw, labels, sites):
    coordinates = {site: {} for site in sites}
    for line in raw.decode("ascii").splitlines():
        if line[:6] not in {"ATOM  ", "HETATM"}:
            continue
        (site, component, name), xyz = labels[line[12:27]]
        if site not in sites:
            continue
        occ = float(line[54:60])
        if not isfinite(occ) or not 0 <= occ <= 1:
            raise ValueError(f"Invalid occupancy at {site} {name}")
        if not occ or line[76:78].strip() in {"H", "D"}:
            continue
        if component != sites[site] or name in coordinates[site]:
            raise ValueError(f"Ambiguous residue at {site}")
        coordinates[site][name] = (xyz, line[76:78].strip().upper())
    return coordinates


def _standard_sugar(code, atoms, *, acceptor):
    base = code[-1]
    allowed = _BACKBONE.union(_BASE_ATOMS[base].split())
    if not acceptor:
        allowed.update(("OP3", "O3P"))  # The donor's own upstream phosphate is outside this junction.
    if _FAMILY[code] == "RNA":
        allowed.add("O2'")
    xyz = {}
    for name, (point, element) in atoms.items():
        if name not in allowed or element != name[0]:
            return None, f"{name} ({element}) differs from the standard {code} heavy-atom inventory"
        xyz[name] = point
    required = ("P", "OP1", "OP2", "O5'") if acceptor else ("O3'",)
    for name in required:
        if name not in xyz:
            return None, f"An occupied {name} is required for this phosphodiester"
    # Positive ordered triple products from the standard D nucleoside monomer dictionaries.
    centers = {"C1'": ("N9" if base in {"A", "G"} else "N1", "O4'", "C2'"),
               "C3'": ("C2'", "O3'", "C4'"), "C4'": ("C3'", "O4'", "C5'")}
    if _FAMILY[code] == "RNA":
        centers["C2'"] = ("C1'", "O2'", "C3'")
    for center, neighbors in centers.items():
        volume = _volume(xyz, center, neighbors)
        if volume is None or volume <= VOLUME_EPSILON:
            return None, f"The standard {code} sugar hand cannot be confirmed at {center}"
    return xyz, None


def _terms(reference, family, codes, donor, acceptor):
    groups = (("donor", codes[0], donor), ("acceptor", codes[1], acceptor))
    for role, code, local in groups:
        for feature, limits in (reference[family] | reference[code]).items():
            tokens = feature.split("-")
            cross = any(token.endswith("r2") for token in tokens)
            if role == "donor" and (cross or any(t in {"P", "OP1", "OP2", "O5p"} for t in tokens)):
                continue
            if role == "acceptor" and "O3p" in tokens:
                continue
            points = []
            for token in tokens:
                previous = token.endswith("r2")
                name = token.removesuffix("r2").replace("p", "'")
                points.append((donor if previous else local).get(name))
            value = None
            if None not in points:
                value = dist(*points) if len(points) == 2 else _angle(points)
            yield dict(group="link" if cross else role, feature=feature, interval=limits, observed=value,
                       unit="Å" if len(points) == 2 else "°",
                       outside=None if value is None else not limits[0] <= value <= limits[1])


def inspect_junction_reference(model, inspection):
    """The r2 atoms belong to the O3′ donor in the declared crystal image."""
    model = Path(model)
    raw, labels = _model_labels(model)
    model_hash = sha256(raw).hexdigest()
    if model_hash != inspection["model_sha256"]:
        raise ValueError("Junction coordinates differ from the inspected phosphate model")
    data = files("nasolve").joinpath("data", "chemical_references", "na_val_2026_junctions.json").read_bytes()
    reference = json.loads(data)
    result = dict(method="na-val-2026-junction-outer-limits-v1", status="UNASSESSED", terms=[],
                  model_sha256=model_hash, source=reference["source"], reference_sha256=sha256(data).hexdigest(),
                  source_archive_sha256=reference["archive_sha256"],
                  assignment="registered continuation" if "registered_continuation" in inspection else "caller-specified endpoints and image")
    if "image_ranking" in inspection or not all(inspection.get(k) for k in ("o3", "phosphate", "o3_image")):
        return dict(result, reason="Choose a declared phosphodiester and its explicit O3′ image")
    donor, acceptor = inspection["o3"], inspection["phosphate"]
    codes = donor[1], acceptor[1]
    family = _FAMILY.get(codes[0])
    if family is None or _FAMILY.get(codes[1]) != family:
        return dict(result, reason="Published limits require two standard residues of the same DNA or RNA family")
    gemmi, cell, _ = crystal_from_pdb_bytes(raw)
    op = gemmi.Op(inspection["o3_image"])
    if op.det_rot() < 0:
        return dict(result, reason="The selected symmetry operation reverses the standard donor sugar hand")
    if donor[0] == acceptor[0] and op == gemmi.Op("x,y,z"):
        return dict(result, reason="The named image places both endpoints in the same residue copy")
    sites = {donor[0]: codes[0], acceptor[0]: codes[1]}
    atoms = _coordinates(raw, labels, sites)
    donor_xyz, reason = _standard_sugar(codes[0], atoms[donor[0]], acceptor=False)
    if reason:
        return dict(result, reason=f"{donor[0]} {reason}")
    acceptor_xyz, reason = _standard_sugar(codes[1], atoms[acceptor[0]], acceptor=True)
    if reason:
        return dict(result, reason=f"{acceptor[0]} {reason}")
    moved = {name: _cartesian(op.apply_to_xyz(_fractional(xyz, cell, gemmi)), cell, gemmi)
             for name, xyz in donor_xyz.items()}
    terms = list(_terms(reference["features"], family, codes, moved, acceptor_xyz))
    missing = sum(t["observed"] is None for t in terms)
    if model.read_bytes() != raw:
        raise ValueError("Model changed during the junction population comparison")
    return dict(result, status="PARTIAL" if missing else "MEASURED", family=family, terms=terms,
                missing_count=missing, measured_count=len(terms)-missing,
                outside_count=sum(t["outside"] is True for t in terms))
