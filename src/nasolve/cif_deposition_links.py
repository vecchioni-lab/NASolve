"""Inspect directly labelled nucleic-acid steps and separately read declared crystal links."""
from collections import defaultdict
from dataclasses import dataclass
import gzip
from hashlib import sha256
from math import dist, isfinite
from pathlib import Path
import re

from .topostitch_contacts import _angle
from .topostitch_graph import _compose, _inverse


_NA_TYPES = {"polydeoxyribonucleotide", "polyribonucleotide", "polydeoxyribonucleotide/polyribonucleotide hybrid"}
_ELEMENTS = {"P": "P", "OP1": "O", "OP2": "O", "O5'": "O", "O3'": "O", "C3'": "C"}
_CELL = ("length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma")


def _rows(block, category):
    columns = block.get_mmcif_category(category)
    return (dict(zip(columns, row)) for row in zip(*columns.values()))


@dataclass
class _Coordinates:
    sites: dict
    authors: dict
    models: list
    cell: object
    ops: dict
    unlabelled: int
    sequence_tables: list
    sequence_conflicts: set

    def locate(self, site, atom, component=None, alt=None):
        candidates = [(key, xyz) for key, xyz in self.sites.get(site, {}).items()
                      if key[1] == atom and (not component or key[0] == component)
                      and (not alt or not key[2] or key[2] == alt)]
        return candidates[0] if len(candidates) == 1 else None

    def point(self, site, atom, component=None, alt=None):
        match = self.locate(site, atom, component, alt)
        return match[1] if match is not None else None


def _number(value, gemmi):
    n = gemmi.cif.as_number(str(value))
    if not isfinite(n):
        raise ValueError(f"Invalid numeric value in coordinate mmCIF: {value}")
    return n


def _coordinates(block, gemmi):
    polymers = {r.get("entity_id") for r in _rows(block, "_entity_poly.") if r.get("entity_id")
                if str(r.get("type")).lower() in _NA_TYPES}
    chains = {r.get("id"): r.get("entity_id") for r in _rows(block, "_struct_asym.") if r.get("id")}
    sequences = {}
    for cat, owner, number in (("_entity_poly_seq.", "entity_id", "num"), ("_pdbx_poly_seq_scheme.", "asym_id", "seq_id")):
        declared = defaultdict(set)
        for r in _rows(block, cat):
            if r.get(owner) and r.get(number) and r.get("mon_id"):
                declared[r[owner], int(r[number])].add(r["mon_id"])
        if declared:
            sequences[cat] = declared
    conflicts = set()
    sites, authors, models, unlabelled = {}, defaultdict(set), set(), 0
    for row in _rows(block, "_atom_site."):
        ch, n, comp = (row.get(k) for k in ("label_asym_id", "label_seq_id", "label_comp_id"))
        entity = row.get("label_entity_id") or chains.get(ch)
        if entity not in polymers and chains.get(ch) not in polymers:
            continue
        if not ch or not n or not comp:
            unlabelled += 1
            continue
        number = int(n)
        if number < 1:
            raise ValueError("Polymer label_seq_id must be positive")
        model = row.get("pdbx_PDB_model_num") or "1"
        models.add(model)
        site = (model, ch, number)
        if ch in chains and entity != chains[ch]:
            conflicts.add((*site, comp, "_struct_asym."))
        for cat, seq in sequences.items():
            owner = entity if cat == "_entity_poly_seq." else ch
            if comp not in seq.get((owner, number), ()):
                conflicts.add((*site, comp, cat))
        atoms = sites.setdefault(site, {})
        if row.get("auth_asym_id") and row.get("auth_seq_id"):
            authors[site].add((row["auth_asym_id"], row["auth_seq_id"], row.get("pdbx_PDB_ins_code") or ""))
        name = str(row.get("label_atom_id")).replace("*", "'")
        if name not in _ELEMENTS:
            continue
        occ = _number(row.get("occupancy"), gemmi)
        if not 0 <= occ <= 1:
            raise ValueError("Backbone atom occupancy is outside [0,1]")
        if not occ or str(row.get("type_symbol")).upper() != _ELEMENTS[name]:
            continue
        key = comp, name, row.get("label_alt_id") or ""
        if key in atoms:
            raise ValueError(f"Ambiguous atom {key} at {model}/{ch}/{n}")
        atoms[key] = tuple(_number(row.get("Cartn_" + a), gemmi) for a in "xyz")

    cell_row = next(_rows(block, "_cell."), {})
    cell = None
    if all(cell_row.get(k) for k in _CELL):
        values = [_number(cell_row[k], gemmi) for k in _CELL]
        cell = gemmi.UnitCell(*values)
        if min(values[:3]) <= 0 or any(not 0 < v < 180 for v in values[3:]) or not isfinite(cell.volume) or cell.volume <= 0:
            raise ValueError("Invalid crystallographic cell")
    ops = {}
    for category, field in (("_space_group_symop.", "operation_xyz"), ("_symmetry_equiv.", "pos_as_xyz")):
        for row in _rows(block, category):
            key, xyz = row.get("id"), row.get(field)
            if not key or not xyz:
                continue
            op = gemmi.Op(xyz)
            if key in ops and op != ops[key]:
                raise ValueError(f"Conflicting crystal operations for ID {key}")
            ops[key] = op
        if ops:
            break
    return _Coordinates(sites, authors, sorted(models), cell, ops, unlabelled, list(sequences), conflicts)


def _ordinary_step(c, step, left, right, maximum):
    model, chain = step["model"], step["label_asym_id"]
    first, last = step["from_label_seq_id"], step["to_label_seq_id"]

    def label(number, match):
        return (chain, str(number), match[0][0], match[0][2]) if match else None

    oxygen, phosphorus = label(first, left), label(last, right)

    def phosphate_atom(name):
        return c.point((model, chain, last), name, phosphorus[2], phosphorus[3])

    geometry = _phosphate_geometry(left[1] if left else None, right[1] if right else None, phosphate_atom)
    distance = geometry["distance_A"]
    if distance is None:
        status = "UNMEASURED"
    elif oxygen[3] and phosphorus[3] and oxygen[3] != phosphorus[3]:
        status = "ALTERNATE_LABEL_REVIEW"
    elif distance > maximum:
        status = "LONG"
    elif any(v is None for v in geometry.values()):
        status = "PARTIAL_ANGLES"
    else:
        status = "MEASURED"
    return dict(step, status=status, O3_label=oxygen, P_label=phosphorus, operator_on_P="x,y,z", **geometry)


def _ordinary(c, maximum, include_steps=False):
    chains = defaultdict(list)
    for model, ch, n in c.sites:
        chains[model, ch].append(n)
    measured, long_steps, unmeasured, gaps, details = [], [], [], [], []
    for (model, ch), numbers in sorted(chains.items()):
        ordered = sorted(numbers)
        for a, b in zip(ordered, ordered[1:]):
            step = {"model": model, "label_asym_id": ch, "from_label_seq_id": a, "to_label_seq_id": b}
            for side, n in (("from", a), ("to", b)):
                author = c.authors.get((model, ch, n), ())
                if len(author) == 1:
                    step[side + "_author"] = next(iter(author))
            if b != a + 1:
                gaps.append(step)
                if include_steps:
                    details.append(dict(step, status="SEQUENCE_GAP", O3_label=None, P_label=None,
                                        operator_on_P=None, **_phosphate_geometry(None, None, None)))
                continue
            left = c.locate((model, ch, a), "O3'")
            right = c.locate((model, ch, b), "P")
            distance = None if left is None or right is None else dist(left[1], right[1])
            if distance is None:
                unmeasured.append(step)
            else:
                measured.append(distance)
                if distance > maximum:
                    long_steps.append(dict(step, distance_A=distance))
            if include_steps:
                details.append(_ordinary_step(c, step, left, right, maximum))

    result = {"measured": len(measured), "minimum_A": min(measured, default=None),
              "maximum_A": max(measured, default=None), "long_steps": long_steps,
              "unmeasured": unmeasured, "sequence_gaps": gaps}
    if include_steps:
        result["steps"] = details
    return result


def resolve_deposition_image(code, operations):
    """Apply a connection's lattice shift to its file-declared Gemmi operation.

    A bare operation ID has zero additional shift. Absent or unknown codes
    return None so the caller can preserve an unresolved crystal image.
    """
    match = re.fullmatch(r"(\d+)(?:_(\d{3}))?", str(code))
    if not match or match[1] not in operations:
        return None
    base = operations[match[1]]
    return base.translated([(int(v) - 5) * base.DEN for v in (match[2] or "555")])


def _image(code, ops):
    """Compatibility entry point for earlier laboratory readers."""
    return resolve_deposition_image(code, ops)


def _endpoint(row, side):
    group = f"ptnr{side}_"
    number = row.get(group + "label_seq_id")
    return (row.get(group + "label_asym_id") or "", str(int(number)) if number else "",
            row.get(group + "label_comp_id") or "", row.get(f"pdbx_ptnr{side}_label_alt_id") or "")


def _phosphate_geometry(o3, phosphorus, image):
    distance = dist(o3, phosphorus) if o3 is not None and phosphorus is not None else None
    result = {"distance_A": distance}
    for atom, field in (("OP1", "O3_P_OP1_deg"), ("OP2", "O3_P_OP2_deg"), ("O5'", "O3_P_O5prime_deg")):
        third = image(atom) if distance is not None else None
        result[field] = _angle([o3, phosphorus, third]) if third is not None else None
    return result


def _observe(c, model, oxygen, phosphorus, relative, gemmi):
    oc, on, om, oa = oxygen
    pc, pn, pm, pa = phosphorus
    o3 = c.point((model, oc, int(on)), "O3'", om, oa)
    transform = c.cell.op_as_transform(relative)

    def image(name):
        point = c.point((model, pc, int(pn)), name, pm, pa)
        return tuple(transform.apply(gemmi.Position(*point))) if point is not None else None

    p = image("P")
    if o3 is None or p is None:
        return {"model": model, "distance_A": None}
    return {"model": model, **_phosphate_geometry(o3, p, image)}


def _declared(block, c, gemmi):
    found, keys = [], set()
    identity = gemmi.Op("x,y,z")
    for row in _rows(block, "_struct_conn."):
        if not str(row.get("conn_type_id")).lower().startswith("covale"):
            continue
        atoms = [str(row.get(f"ptnr{i}_label_atom_id")).replace("*", "'") for i in (1, 2)]
        if set(atoms) != {"P", "O3'"}:
            continue
        i = atoms.index("O3'") + 1
        j = 3 - i
        o, p = _endpoint(row, i), _endpoint(row, j)
        a, b = (resolve_deposition_image(row.get(f"ptnr{s}_symmetry"), c.ops) for s in (i, j))
        relative = _compose(_inverse(a, identity), b) if a is not None and b is not None else None
        op = relative.triplet() if relative is not None else None
        observed = []
        if op is not None and all(o[:3]) and all(p[:3]) and c.cell is not None:
            observed = [_observe(c, model, o, p, relative, gemmi) for model in c.models]
            keys.add((o, p, op))
        found.append({"id": row.get("id"), "O3_label": o, "P_label": p,
                      "O3_author": [row.get(f"ptnr{i}_auth_asym_id"), row.get(f"ptnr{i}_auth_seq_id")],
                      "P_author": [row.get(f"ptnr{j}_auth_asym_id"), row.get(f"ptnr{j}_auth_seq_id")],
                      "operator_on_P": op, "observations": observed})
    return found, keys


def _inspect(path, maximum, gemmi, include_ordinary_steps):
    raw = Path(path).read_bytes()
    try:
        data = gzip.decompress(raw) if raw.startswith(b"\x1f\x8b") else raw
    except EOFError as exc:
        raise ValueError("Truncated gzip coordinate file") from exc
    doc = gemmi.cif.read_string(data)
    blocks = [b for b in doc if len(b.find_values("_atom_site.id"))]
    if len(blocks) != 1:
        raise ValueError("Supply a coordinate mmCIF with one atom_site data block")
    block = blocks[0]
    c = _coordinates(block, gemmi)
    ordinary = _ordinary(c, maximum, include_ordinary_steps)
    declared, keys = _declared(block, c, gemmi)
    unresolved = [r["id"] for r in declared if not r["observations"]
                  or any(v["distance_A"] is None for v in r["observations"])]
    extended = [r["id"] for r in declared if any(v["distance_A"] is not None and v["distance_A"] > maximum
                                                    for v in r["observations"])]
    missing_oxygen_angles = [r["id"] for r in declared if any(
        obs.get("O3_P_OP1_deg") is None or obs.get("O3_P_OP2_deg") is None for obs in r["observations"])]
    review = bool(c.unlabelled or not ordinary["measured"] or ordinary["long_steps"] or ordinary["sequence_gaps"]
                  or any(s["status"] != "MEASURED" for s in ordinary.get("steps", ()))
                  or ordinary["unmeasured"] or unresolved or extended or missing_oxygen_angles or c.sequence_conflicts)
    return {"sha256": sha256(raw).hexdigest(), "status": "REVIEW" if review else "CHECKED",
            "ordinary": ordinary, "declared": declared, "unmeasured_declarations": unresolved,
            "long_declarations": extended, "missing_declared_OP_angles": missing_oxygen_angles,
            "unlabelled_polymer_atom_rows": c.unlabelled, "sequence_tables_checked": c.sequence_tables,
            "sequence_conflicts": sorted(c.sequence_conflicts)}, c, keys


def _same_backbone(a, b):
    if a.sites.keys() != b.sites.keys() or bool(a.cell) != bool(b.cell):
        return False
    if a.cell and any(abs(x - y) > .0001 for x, y in zip(a.cell.parameters, b.cell.parameters)):
        return False
    if a.ops and b.ops and {op.triplet() for op in a.ops.values()} != {op.triplet() for op in b.ops.values()}:
        return False
    for site, aa in a.sites.items():
        bb = b.sites[site]
        if aa.keys() != bb.keys() or any(dist(pos, bb[key]) > .002 for key, pos in aa.items()):
            return False
    return bool(a.sites)


def inspect_deposition_links(model, *, processed=None, maximum=2.2, include_ordinary_steps=False):
    """Read sequence steps and declared O3'–P images. Opt in for labels and geometry at each ordinary step."""
    try:
        import gemmi
    except ImportError as exc:
        raise ValueError("Deposition linkage inspection requires NASolve[topology]") from exc
    if not isfinite(maximum) or maximum <= 0:
        raise ValueError("The maximum step distance must be a positive finite number")
    source, a, expected = _inspect(model, maximum, gemmi, include_ordinary_steps)
    report = {"schema_version": 1, "maximum_step_A": maximum, "status": source["status"], "model": source}
    if processed is not None:
        returned, b, actual = _inspect(processed, maximum, gemmi, include_ordinary_steps)
        comparable = (_same_backbone(a, b) and not source["unmeasured_declarations"]
                      and not returned["unmeasured_declarations"])
        missing = sorted(expected - actual) if comparable else None
        report.update(processed=returned, comparison={"comparable": comparable, "missing": missing,
                      "basis": "Matching occupied backbone atom labels and coordinates within 0.002 angstrom, cell and explicit relative crystal operations."})
        if not comparable or missing or returned["status"] == "REVIEW":
            report["status"] = "REVIEW"
    return report
