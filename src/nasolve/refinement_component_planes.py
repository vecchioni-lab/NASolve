"""Read Phenix's printed planarity restraints for explicitly supplied components."""
from collections import defaultdict
from hashlib import sha256
from itertools import chain
from math import isfinite
from pathlib import Path

from .cif_printed_parallelity import _LABEL, _NUMBER, _SECTION
from .refinement_link_geometry import _model_labels


def _planarity_sections(text, labels):
    sections = {}
    groups = []
    origin = None
    pending_header = False
    members = None
    count = 0
    for line in chain(text.splitlines(), (None,)):
        section = _SECTION.fullmatch(line) if line is not None else None
        if line is not None and line.lstrip().startswith("Planarity |") and section is None:
            raise ValueError("Malformed printed planarity section heading")
        if section or line is None:
            if origin and (count != sections[origin] or pending_header):
                raise ValueError("Incomplete printed planarity section")
            if line is None:
                break
            origin = None
            if section[1] == "Planarity":
                origin = section[2]
                if section[3] != "restraints" or origin in sections:
                    raise ValueError("Ambiguous printed planarity section")
                sections[origin] = int(section[4])
                count, pending_header, members = 0, False, None
            continue
        if origin is None or not line.strip() or line.strip() == "Sorted by residual:":
            continue
        if line.split() == ["delta", "sigma", "weight", "rms_deltas", "residual"]:
            if pending_header:
                raise ValueError("Printed plane is missing its first member")
            pending_header, members = True, None
            continue
        row = line.strip()
        first = row.startswith("plane ")
        if first != pending_header or (not first and members is None):
            raise ValueError("Unsupported printed plane member or column header")
        if first:
            row = row[6:].lstrip()
            count += 1
            if count > sections[origin]:
                raise ValueError("More printed planes than declared")
            members = {}
            groups.append((origin, count, members))
            pending_header = False
        atom = _LABEL.match(row)
        if atom is None or atom[0][5:-1] not in labels:
            raise ValueError("Printed plane atom is absent from the supplied model")
        values = row[atom.end():].split()
        if len(values) != (5 if first else 3) or not all(_NUMBER.fullmatch(v) and isfinite(float(v)) for v in values):
            raise ValueError("Invalid printed plane coordinates or weights")
        delta, sigma, weight = map(float, values[:3])
        identity = labels[atom[0][5:-1]][0]
        if identity in members or sigma < 0 or weight < 0 or any(float(x) < 0 for x in values[3:]):
            raise ValueError("Repeated plane member or negative printed sigma, weight, RMS or residual")
        members[identity] = dict(atom=identity[2], delta_A=delta, sigma_A=sigma, weight=weight)
    if any(len(group) < 3 for _, _, group in groups):
        raise ValueError("Printed plane contains fewer than three distinct atom records")
    return sections, groups


def _source_plane(name, members, modeled, covalent, sections):
    present = set(members) & modeled
    matches = [index for index, active in covalent if active == present]
    if len(present) < 3:
        status = "TOO_FEW_MODELED_MEMBERS"
    elif "covalent geometry" not in sections:
        status = "COVALENT_SECTION_NOT_RECORDED"
    else:
        status = "EXACT_MODELED_MEMBERS" if matches else "NO_EXACT_MODELED_MATCH"
    covered = set().union(*(active for _, active in covalent))
    uncovered = sorted(present - covered) if "covalent geometry" in sections else None
    return dict(
        plane_id=name, status=status, modeled_atoms=sorted(present),
        unmodeled_atoms=sorted(set(members) - modeled), matching_covalent_planes=matches,
        modeled_atoms_without_positive_covalent_plane=uncovered,
    )


def _tip_plane_comparisons(arm, positions, planes):
    """Measure how much a printed intra-residue plane moves when its tip is omitted."""
    from math import acos, degrees
    import numpy as np
    from .refinement_plane_departures import _fit_plane_offsets

    if planes is None or arm["status"] != "MEASURED":
        return None
    tip = arm["arm_atoms"][-1]
    required = set(arm["ring_atoms"]) | {tip}
    comparisons = []
    for plane in planes:
        active = {m["atom"]: m for m in plane["members"] if m["weight"] > 0}
        if not required <= active.keys():
            continue
        missing = sorted(active.keys() - positions.keys())
        result = dict(origin=plane["origin"], section_index=plane["section_index"],
                      positive_member_count=len(active), unavailable_atoms=missing,
                      printed_tip_distance_A=abs(active[tip]["delta_A"]),
                      tip_to_all_members_plane_A=None, tip_to_other_members_plane_A=None,
                      tilt_on_omitting_tip_deg=None, max_printed_distance_difference_A=None,
                      status="UNASSESSED", reason=None)
        comparisons.append(result)
        if missing:
            result["reason"] = "A positive-weight plane member is missing, unoccupied or has a different element"
            continue
        points = np.asarray([positions[name] for name in active])
        weights = np.asarray([m["weight"] for m in active.values()])
        all_members, reason = _fit_plane_offsets(points, weights)
        if all_members is None:
            result["reason"] = reason
            continue
        offset, normal = all_members
        result["tip_to_all_members_plane_A"] = abs(offset(positions[tip]))
        result["max_printed_distance_difference_A"] = max(
            abs(abs(offset(positions[name])) - abs(m["delta_A"])) for name, m in active.items()
        )
        weights[list(active).index(tip)] = 0.
        other_members, reason = _fit_plane_offsets(points, weights)
        if other_members is None:
            result["reason"] = reason
            continue
        other_offset, other_normal = other_members
        result.update(status="MEASURED", tip_to_other_members_plane_A=abs(other_offset(positions[tip])),
                      tilt_on_omitting_tip_deg=degrees(acos(min(1., abs(float(normal @ other_normal))))))
    return comparisons


def _written_ring_arms(raw, labels, by_code, native):
    from .cif_plane_coverage import dictionary_ring_arm_paths
    from .refinement_plane_departures import measure_ring_arm

    if labels is None:
        return None
    graphs = {code: {d["definition_sha256"]: dictionary_ring_arm_paths(d) for d in definitions}
              for code, definitions in by_code.items()}
    relevant = {code for code, candidates in graphs.items()
                if any(candidate["arms"] or candidate["status"] == "UNASSESSED" for candidate in candidates.values())}
    if not relevant:
        return []
    elements = {code: {r["atom_id"]: r["element"].upper() for r in by_code[code][0]["inventory"]["atoms"]
                       if isinstance(r["element"], str)} for code in relevant}
    positions = defaultdict(dict)
    for line in raw.decode("ascii").splitlines():
        if line[:6] not in {"ATOM  ", "HETATM"}:
            continue
        (site, code, atom), xyz = labels[line[12:27]]
        if code not in relevant:
            continue
        coords = positions[site, code]
        try:
            occupied = 0 < float(line[54:60]) <= 1
        except ValueError:
            occupied = False
        if occupied and all(isfinite(v) for v in xyz) and line[76:78].strip().upper() == elements[code].get(atom):
            coords[atom] = list(xyz)
    result = []
    for (site, code), coords in sorted(positions.items()):
        definitions = by_code[code]
        hashes = sorted({d["definition_sha256"] for d in definitions})
        identity = dict(site=site, component=code, definition_sha256s=hashes)
        planes = native.get((site, code), []) if native is not None else None
        if len(hashes) != 1:
            result.append(dict(identity, status="UNASSESSED", reason="Conflicting supplied component definitions", tip_plane_comparisons=None))
            continue
        definition = graphs[code][hashes[0]]
        if definition["status"] == "UNASSESSED":
            result.append(dict(identity, status="UNASSESSED", reason=definition["reason"], tip_plane_comparisons=None))
            continue
        for path in definition["arms"]:
            observation = measure_ring_arm(path["arm"], path["rings"], coords)
            if observation["missing_atoms"]:
                observation["reason"] = "A required coordinate is missing, unoccupied or has a different element"
            observation["tip_plane_comparisons"] = _tip_plane_comparisons(observation, coords, planes)
            result.append(dict(identity, **observation))
    return result


def read_component_planes(model, geometry, components):
    """Compare positive intramonomer covalent plane members with modeled CIF atoms.

    Keep user-supplied planes separate. A cross-site restraint cannot prove
    membership in a residue's own ring plane. The report describes saved tables
    and leaves source assignment, target strength and scientific acceptance open.
    """
    model, geometry = Path(model), Path(geometry)
    raw, data = model.read_bytes(), geometry.read_bytes()
    parsed = labels = native = None
    by_code = defaultdict(list)
    for component in components:
        by_code[component["component_id"]].append(component)
    status, reason, sites = "NOT_RECORDED", None, None
    try:
        parsed, labels = _model_labels(model)
        sections, groups = _planarity_sections(data.decode("utf-8"), labels)
    except ValueError as exc:
        status, reason, sections = "UNASSESSED", str(exc), None
    if sections:
        status, sites = "OBSERVED", []
        modeled = defaultdict(set)
        for (site, code, name), _ in labels.values():
            if code in by_code:
                modeled[site, code].add(name)
        native = defaultdict(list)
        for origin, index, group in groups:
            locations = {key[:2] for key in group}
            if len(locations) == 1:
                location, = locations
                if location in modeled:
                    native[location].append(dict(origin=origin, section_index=index, members=list(group.values())))
        for (site, code), atoms in sorted(modeled.items()):
            definitions = by_code[code]
            printed = native[site, code]
            covalent = [
                (row["section_index"], {member["atom"] for member in row["members"] if member["weight"] > 0})
                for row in printed if row["origin"] == "covalent geometry"
            ]
            declared = None
            if len({d["definition_sha256"] for d in definitions}) == 1:
                planes = definitions[0]["inventory"]["planes"]
                declared = [_source_plane(name, members, atoms, covalent, sections) for name, members in planes.items()]
            sites.append(dict(site=site, component=code, input_indices=[d["input_index"] for d in definitions],
                              printed_planes=printed, dictionary_planes=declared))
    if (parsed is not None and parsed != raw) or model.read_bytes() != raw or geometry.read_bytes() != data:
        raise ValueError("Model or GEO changed during printed-plane inspection")
    return dict(
        policy_id="printed-component-plane-members-v1", model_sha256=sha256(raw).hexdigest(),
        geometry_sha256=sha256(data).hexdigest(), status=status, reason=reason, sections=sections, sites=sites,
        written_ring_arms=_written_ring_arms(raw, labels, by_code, native),
        scope="Printed intramonomer planes at modeled sites of supplied components. Exact membership compares positive covalent members only.",
        scientific_approval="NOT_ASSESSED",
    )
