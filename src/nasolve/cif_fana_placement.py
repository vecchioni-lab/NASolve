"""Separate rigid whole-FANA controls, with explicit internal phosphodiester intent.

Placement preserves a complete candidate's internal geometry; it does not optimize
the junctions, infer terminal chemistry or authorize ordinary model adoption.
"""
from hashlib import sha256
from itertools import combinations
import math
from pathlib import Path
import shutil

from .cif_attachment_sites import _model, _projection_values
from .cif_candidate_usability import reassess_complete_candidate
from .cif_catalogue import _workbook_records
from .component_records import resolve_component_record
from .cif_construction_provenance import _pdb_inventory
from .cif_fana_component import read_fana_enantiomer_component, _digest, _load, _save
from .cif_fragment_restoration import _SCAFFOLD, _FRAME, _frame, _dot, _sub, _cross
from .cif_stereochemistry_audit import _values, _graph, _coordinates, _volume, VOLUME_EPSILON

POLICY_ID = "cif-rigid-whole-fana-linked-control-v1"
_INPUTS = {"frame.pdb", "numerical.cif", "context.json"}
_OUTPUTS = {"model.pdb", "placement.json"}
_CONTEXT = {"site": "A:2", "incoming_site": "A:1", "outgoing_site": "A:3",
            "five_prime_state": "linked", "three_prime_state": "linked",
            "symmetry_operation": "x,y,z"}
_DNA = {"DA", "DC", "DG", "DT", "0DA", "0DC", "0DG", "0DT"}
_ROLES = {"anomeric": "C1'", "ring_o": "O4'", "ring_c2": "C2'",
          "ring_c3": "C3'", "ring_c4": "C4'", "five_c": "C5'",
          "five_o": "O5'", "three_o": "O3'", "phosphate": "P"}


def _hand(a, b):
    return (a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
            and min(abs(a), abs(b)) > VOLUME_EPSILON and (a > 0) == (b > 0))


def _placement(package, numerical, frame, context):
    if (not isinstance(context, dict) or set(context) != set(_CONTEXT) | {"leaving_atom"}
            or any(context[k] != v for k, v in _CONTEXT.items())
            or not isinstance(context["leaving_atom"], str)):
        raise ValueError("Require exact explicit A:1 -> A:2 -> A:3 identity-symmetry context and leaving atom")
    binding = read_fana_enantiomer_component(package)
    code = binding["target_code"]
    source = package / "inputs/target.cif"
    parent = binding["enantiomer"]["parent_fana"]
    roles = parent["source_profile"]["bindings"]
    if any(roles[k] != v for k, v in _ROLES.items()):
        raise ValueError("This bounded control requires conventional phosphodiester atom names")
    _projection_values(numerical, code)
    assessment = reassess_complete_candidate(source, numerical, code)
    centers = {roles[r] for r in ("anomeric", "ring_c2", "ring_c3", "ring_c4")}
    terms = [r for r in assessment["finished_stereo"]["terms"] if r["center"] in centers]
    if (assessment["candidate_status"] != "CANDIDATE_REVIEW" or len(terms) != 4
            or {r["center"] for r in terms} != centers
            or any(r["handedness"] != "PRESERVED" for r in terms)):
        raise ValueError("Require a complete source-preserving candidate with all four sugar hands")
    elements, bonds, charges, neighbors = _graph(_values(source, code))
    leaving = context["leaving_atom"]
    if (elements.get(leaving) != "O" or neighbors[leaving] - {n for n in elements if elements[n] in {"H", "D"}} != {"P"}
            or bonds.get(tuple(sorted(("P", leaving)))) != "SINGLE"):
        raise ValueError("Explicit leaving oxygen does not match the source graph")
    removed = {leaving}
    for atom in (leaving, "O3'"):
        hydrogens = {n for n in neighbors[atom] if elements[n] in {"H", "D"}}
        if (charges[atom] != 0 or len(hydrogens) != 1 or any(charges[h] != 0
                or neighbors[h] != {atom} or bonds[tuple(sorted((h, atom)))] != "SINGLE" for h in hydrogens)):
            raise ValueError("Require explicit neutral source protonation for both linked ports")
        removed.update(hydrogens)

    payload = frame.read_bytes()
    sites = _model(payload)
    if set(sites) != {"A:1", "A:2", "A:3"} or any(r["component"] not in _DNA for r in sites.values()):
        raise ValueError("Require exactly three conventional DNA control sites A:1-3")
    if any(e in {"H", "D"} for r in sites.values() for e in r["atoms"].values()):
        raise ValueError("Control frame must be heavy-atom only")
    if code in {r["component"] for r in sites.values()}:
        raise ValueError("Target identity already occurs in the control")
    if set(sites["A:1"]["atoms"]) & {"P", "OP1", "OP2", "OP3", "O3P"}:
        raise ValueError("First control site must have a free 5-prime end")
    for site in ("A:2", "A:3"):
        if any(sites[site]["atoms"].get(n) != e for n, e in _SCAFFOLD.items()) or set(sites[site]["atoms"]) & {"OP3", "O3P"}:
            raise ValueError("Require complete internal DNA scaffold inventories")
    if sites["A:1"]["atoms"].get("O3'") != "O":
        raise ValueError("Incoming control oxygen is absent")
    lines = payload.decode("utf-8").splitlines(keepends=True)
    if any(line[:6].strip() not in {"ATOM", "HETATM", "REMARK", "CRYST1", "TER", "END", ""} for line in lines):
        raise ValueError("Unsupported frame records require explicit reconciliation")
    inventory = _pdb_inventory(frame)
    center = {k[-1]: r["xyz"] for k, r in inventory.items() if k[:2] == ("A", "2")}
    records, _ = _workbook_records(package/"inputs/Ligands.xlsx")
    host_record, _ = resolve_component_record(records, sites["A:2"]["component"])
    host_base = host_record.get("Glycosidic atom")
    if sites["A:2"]["atoms"].get(host_base) != "N":
        raise ValueError("Host glycosidic nitrogen is absent")
    family, xyz = _coordinates(_values(numerical, code), source=False)
    if set(xyz) != set(elements):
        raise ValueError("Require complete finite numerical coordinates")
    host_checks = []
    for atom, ns, host_ns in [("C1'", ["O4'", "C2'", roles["base"]], ["O4'", "C2'", host_base]),
                              ("C3'", ["C2'", "C4'", "O3'"], ["C2'", "C4'", "O3'"]),
                              ("C4'", ["O4'", "C3'", "C5'"], ["O4'", "C3'", "C5'"])]:
        left, right = _volume(xyz, atom, ns), _volume(center, atom, host_ns)
        if not _hand(left, right):
            raise ValueError("Host and target sugar hand differ or are degenerate at " + atom)
        host_checks.append({"center": atom, "target_volume": left, "host_volume": right})
    a, b = [xyz[n] for n in _FRAME], [center[n] for n in _FRAME]
    u, v = _frame(a), _frame(b)
    determinant = _dot(u[0], _cross(u[1], u[2])) * _dot(v[0], _cross(v[1], v[2]))
    if not math.isfinite(determinant) or abs(determinant - 1) > 1e-10:
        raise ValueError("Require a proper finite rigid transform")
    moved = {n: [b[0][i] + sum(_dot(_sub(p, a[0]), u[j])*v[j][i] for j in range(3)) for i in range(3)]
             for n, p in xyz.items()}
    heavy = sorted(n for n in elements if elements[n] not in {"H", "D"} and n not in removed)
    rounded = {n: [float(f"{x:.3f}") for x in moved[n]] for n in heavy}
    error = max(abs(math.dist(xyz[x], xyz[y]) - math.dist(rounded[x], rounded[y])) for x, y in combinations(heavy, 2))
    if not math.isfinite(error) or error > .002:
        raise ValueError("PDB rounding changed the rigid component geometry")
    hands = []
    for atom in sorted(centers):
        ns = sorted(n for n in neighbors[atom] if elements[n] not in {"H", "D"})
        if len(ns) != 3 or not _hand(_volume(xyz, atom, ns), _volume(rounded, atom, ns)):
            raise ValueError("Output does not preserve all four heavy sugar hands")
        hands.append({"center": atom, "ordered_neighbors": ns, "source_volume": _volume(xyz, atom, ns),
                      "placed_volume": _volume(rounded, atom, ns)})
    serials = [int(line[6:11]) for line in lines if line[:6] in {"ATOM  ", "HETATM"}]
    if len(serials) != len(set(serials)):
        raise ValueError("Duplicate frame atom serial")
    serial = max(serials)
    replacement = []
    for n in heavy:
        serial += 1
        fields = [f"{x:8.3f}" for x in rounded[n]]
        if len(n) > 4 or serial > 99999 or any(len(f) != 8 for f in fields):
            raise ValueError("Placed atom exceeds supported PDB fields")
        replacement.append(f"HETATM{serial:5d} {n:>4} {code:>3} A   2    {''.join(fields)}  1.00 20.00          {elements[n]:>2}\n")
    result, inserted = [], False
    for line in lines:
        if line[:6] in {"ATOM  ", "HETATM"} and line[21:26] == "A   2":
            if not inserted:
                result.extend(replacement)
                inserted = True
        else:
            result.append(line)
    model = "".join(result)
    if not inserted or _model(model.encode())["A:2"]["atoms"] != {n: elements[n] for n in heavy}:
        raise ValueError("Output inventory does not match the explicit heavy projection")
    junctions = []
    for site, atom, target in [("1", "O3'", "P"), ("3", "P", "O3'")]:
        partner = inventory[("A", site, "", "", atom)]["xyz"]
        junctions.append({"partner": "A:"+site+":"+atom, "target_atom": target,
                          "before_angstrom": math.dist(partner, center[target]),
                          "after_angstrom": math.dist(partner, rounded[target])})
    report = {"schema_version": 1, "policy_id": POLICY_ID, "status": "PLACED_FOR_LINK_REVIEW",
              "component": code, "family": binding["enantiomer"]["target_family"], "context": context,
              "coordinate_family": family, "rigid_frame_atoms": list(_FRAME), "rotation_determinant": determinant,
              "max_internal_distance_error_angstrom": error, "four_sugar_hands": hands,
              "host_hand_checks": host_checks, "host_glycosidic_atom": host_base, "deleted_source_atoms_for_declared_links": sorted(removed),
              "model_heavy_atoms": heavy, "source_hydrogens_retained_in_dictionary": True,
              "flanking_records_preserved": True, "junction_distances": junctions,
              "candidate_sha256": sha256(numerical.read_bytes()).hexdigest(),
              "source_sha256": sha256(source.read_bytes()).hexdigest(),
              "frame_sha256": sha256(payload).hexdigest(),
              "model_optimization": "NOT_RUN", "native_linkage": "NOT_ASSESSED", "clash_assessment": "NOT_RUN",
              "absolute_cip_assignment": "NOT_RUN", "automatic_adoption": False,
              "scope": "SEPARATE_THREE_RESIDUE_CONTROL; NO_JUNCTION_GEOMETRY_ACCEPTANCE"}
    return report, model


def prepare_fana_linked_control(package, numerical, frame, output, *, context):
    """Freeze inputs and write a fresh, separate whole-residue placement control."""
    package, numerical, frame = [Path(p).expanduser().resolve(strict=True) for p in (package, numerical, frame)]
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or any(out.resolve().is_relative_to(p) or p.is_relative_to(out.resolve()) for p in (package, numerical, frame)):
        raise ValueError("Control output must be separate and cannot traverse symlinks")
    read_fana_enantiomer_component(package)
    original = [p for p in package.rglob("*") if p.is_file()] + [numerical, frame]
    before = {p: p.read_bytes() for p in original}
    expected, model = _placement(package, numerical, frame, context)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(package, out/"component")
    for name, path in [("numerical.cif", numerical), ("frame.pdb", frame)]:
        with (out/name).open("xb") as stream:
            stream.write(before[path])
    _save(out/"context.json", context)
    actual, frozen_model = _placement(out/"component", out/"numerical.cif", out/"frame.pdb", _load(out/"context.json"))
    if actual != expected or model != frozen_model or any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError("Placement authority changed while freezing inputs")
    with (out/"model.pdb").open("x") as stream:
        stream.write(model)
    _save(out/"placement.json", actual)
    files = {p.relative_to(out).as_posix(): _digest(p) for p in out.rglob("*") if p.is_file()}
    _save(out/"receipt.json", {"schema_version": 1, "policy_id": POLICY_ID, "files": files})
    return read_fana_linked_control(out)


def read_fana_linked_control(control):
    """Replay frozen chemistry and placement offline; saved success is not authority."""
    root = Path(control).expanduser().resolve(strict=True)
    paths = list(root.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Placement control cannot traverse symlinks")
    read_fana_enantiomer_component(root/"component")
    expected = _INPUTS | _OUTPUTS | {"receipt.json"} | {"component/"+p.relative_to(root/"component").as_posix() for p in (root/"component").rglob("*") if p.is_file()}
    if any(p.is_symlink() for p in paths) or {p.relative_to(root).as_posix() for p in paths if p.is_file()} != expected:
        raise ValueError("Require an exact nonsymlinked placement control")
    before = {p: p.read_bytes() for p in paths if p.is_file()}
    r = _load(root/"receipt.json")
    if (set(r) != {"schema_version", "policy_id", "files"} or type(r["schema_version"]) is not int
            or r["schema_version"] != 1 or r["policy_id"] != POLICY_ID or set(r["files"]) != expected - {"receipt.json"}
            or any(_digest(root/name) != value for name, value in r["files"].items())):
        raise ValueError("Invalid placement completion receipt or checksum")
    report, model = _placement(root/"component", root/"numerical.cif", root/"frame.pdb", _load(root/"context.json"))
    if report != _load(root/"placement.json") or model.encode() != (root/"model.pdb").read_bytes() or any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError("Stored placement differs from fresh derivation")
    return report
