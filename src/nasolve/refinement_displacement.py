"""Compare the B factors and occupancies written for an explicitly named PDB residue."""
from hashlib import sha256
from math import isfinite

from .cif_base_displacement import _site_lines
from .postmr_scaffold_displacement import _indexed
from .refinement_contact_geometry import validate_contact_sites


def _index_model(data):
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return None
    markers = [(i, line[:6].strip()) for i, line in enumerate(lines)
               if line[:6].strip() in {"MODEL", "ENDMDL"}]
    if markers:
        if [kind for _, kind in markers] != ["MODEL", "ENDMDL"]:
            return None
        first, last = (i for i, _ in markers)
        if _indexed(lines[:first]) or _indexed(lines[last + 1:]):
            return None
        lines = lines[first + 1:last]
    return _indexed(lines)


def _fields(index, site):
    if index is None:
        raise ValueError("A single fixed-column PDB model is required")
    group = index.get(tuple(site.split(":")), [])
    records = _site_lines([line for line in group if line[:6] in {"ATOM  ", "HETATM"}], site)
    if not records:
        raise ValueError("Requested residue is absent from the model")
    labels = {line[6:27] for _, line in records.values()}
    anisou = [line[6:27] for line in group if line[:6] == "ANISOU"]
    if len(anisou) != len(set(anisou)) or set(anisou) - labels:
        raise ValueError("An anisotropic record lacks a unique matching coordinate atom")
    components = {line[17:20].strip() for _, line in records.values()}
    if len(components) != 1 or not all(components):
        raise ValueError("Residue component identity is ambiguous")
    atoms = {}
    for name, (_, line) in records.items():
        try:
            occupancy, b = float(line[54:60]), float(line[60:66])
        except ValueError as exc:
            raise ValueError(f"Missing or invalid PDB occupancy or B factor at {name}") from exc
        element = line[76:78].strip().upper()
        if not name or not element or not isfinite(occupancy) or not isfinite(b):
            raise ValueError(f"Incomplete PDB atom identity, occupancy or B factor at {name}")
        atoms[name] = (element, dict(occupancy=occupancy, b_A2=b, has_anisou=line[6:27] in anisou))
    return components.pop(), atoms


def compare_pdb_displacements(input_model, selected_model, sites):
    """Describe named atoms. A parentless selection has one reading and no changes."""
    validate_contact_sites(sites)
    selected = _index_model(selected_model)
    initial = _index_model(input_model) if input_model is not None else None
    result = {}
    for site in sites:
        try:
            component, current = _fields(selected, site)
            previous = {}
            if input_model is not None:
                previous_component, previous = _fields(initial, site)
                if previous_component != component:
                    raise ValueError(f"Residue component changed from {previous_component} to {component}")
            rows = {}
            for name in sorted(current.keys() | previous.keys()):
                old_element, before = previous.get(name, (None, None))
                element, fields = current.get(name, (None, None))
                row = dict(element=element or old_element, input=before, selected=fields, b_change_A2=None)
                if before is not None and fields is not None:
                    if element == old_element:
                        # PDB fields have six columns. Keep differences at their written precision.
                        delta = round(fields["b_A2"] - before["b_A2"], 6)
                        if not isfinite(delta):
                            raise ValueError(f"Invalid PDB B difference at {name}")
                        row["b_change_A2"] = delta
                    else:
                        row["input_element"] = old_element
                rows[name] = row
            matched = [row for row in rows.values() if row["b_change_A2"] is not None]
            changes = [row["b_change_A2"] for row in matched]
            status = "SELECTED_ONLY"
            if previous:
                status = "COMPARED" if len(matched) == len(rows) else "PARTIAL"
            result[site] = dict(status=status, component=component, matched_atoms=len(matched),
                atoms=rows, b_change_range_A2=[min(changes), max(changes)] if changes else None,
                changed_occupancies=sum(row["input"]["occupancy"] != row["selected"]["occupancy"]
                                        for row in matched) if changes else None)
        except ValueError as exc:
            result[site] = dict(status="UNASSESSED", reason=str(exc))
    return dict(policy_id="checkpoint-pdb-displacement-v1", sites=result,
                input_model_sha256=sha256(input_model).hexdigest() if input_model is not None else None,
                selected_model_sha256=sha256(selected_model).hexdigest())
