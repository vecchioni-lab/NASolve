"""Describe the nonbonded contacts Phenix printed for named checkpoint residues."""
from decimal import Decimal
from hashlib import sha256
from math import dist, isfinite, sqrt
from pathlib import Path
import re

from .cif_explicit_na_policy import _SITE
from .cif_printed_parallelity import _LABEL, _NUMBER, _SECTION
from .refinement_link_geometry import _model_labels, _within


def _contact_values(header, line):
    columns = header.split()
    values = line.split()
    if columns not in (["model", "vdw"], ["model", "vdw", "sym.op."]) or len(values) != len(columns):
        raise ValueError("Unsupported Phenix nonbonded value columns")
    for value in values[:2]:
        if (not _NUMBER.fullmatch(value) or not isfinite(float(value)) or float(value) < 0
                or Decimal(value).as_tuple().exponent > -3):
            raise ValueError("Invalid or insufficiently precise printed nonbonded distance")
    image = values[2] if len(values) == 3 else None
    if image is not None and not re.fullmatch(r"[xyz0-9/+*-]+(?:,[xyz0-9/+*-]+){2}", image):
        raise ValueError("Invalid printed crystal-image operator")
    return values[0], values[1], image


def _contacts(text, labels, sections):
    origin = None
    count = expected = 0
    lines = iter(text.splitlines())
    for line in lines:
        section = _SECTION.fullmatch(line) if "|" in line else None
        if section:
            if origin is not None and count != expected:
                raise ValueError("Incomplete printed nonbonded section")
            kind, name, unit, total = section.groups()
            origin = name if kind == "Nonbonded" else None
            if origin is not None:
                if unit != "interactions" or origin in sections:
                    raise ValueError("Duplicate or unsupported nonbonded section")
                sections[origin] = expected = int(total)
                count = 0
            continue
        stripped = line.strip()
        if stripped.startswith("Nonbonded") or (origin is None and stripped.startswith("nonbonded ")):
            raise ValueError("Nonbonded row has no supported section heading")
        if origin is None or not stripped or stripped == "Sorted by model distance:":
            continue
        first = re.fullmatch(r'nonbonded\s+(pdb="[^"]+")', stripped)
        second = next(lines, "").strip()
        if not first or not _LABEL.fullmatch(second):
            raise ValueError("Incomplete nonbonded atom labels")
        fields = [first[1][5:-1], second[5:-1]]
        if any(label not in labels for label in fields):
            raise ValueError("Nonbonded atom label is absent from the model")
        actual, vdw, image = _contact_values(next(lines, ""), next(lines, ""))
        (left, xyz), (right, other) = (labels[label] for label in fields)
        if image is None and not _within(dist(xyz, other), actual, extra=sqrt(3)*0.001):
            raise ValueError("Nonbonded distance differs from the supplied model")
        count += 1
        yield (left, right), actual, vdw, image, origin
    if origin is not None and count != expected:
        raise ValueError("Incomplete printed nonbonded section")


def validate_contact_sites(sites):
    if (not isinstance(sites, (list, tuple)) or not sites or
            any(not isinstance(site, str) or not _SITE.fullmatch(site) for site in sites) or len(set(sites)) != len(sites)):
        raise ValueError("Choose distinct residue sites in CHAIN:NUMBER form")


def _retain_largest(summary, value_field, rows_field, overlap, row):
    highest = summary[value_field]
    if highest is None or overlap > highest:
        summary[value_field] = overlap
        summary[rows_field] = [row]
    elif overlap == highest:
        summary[rows_field].append(row)


def read_refined_contacts(model, geometry, sites):
    """Measure printed vdW minus distance, retaining each atom's most crowded contacts.

    A negative maximum is a gap. Crystal images use the distance and ordered
    operator in Phenix's table. These measurements do not assign contact chemistry.
    """
    validate_contact_sites(sites)
    model, geometry = Path(model), Path(geometry)
    raw, labels = _model_labels(model)
    sites_by_name = {site: {} for site in sites}
    selected = {}
    for key, _ in labels.values():
        site, component, name = key
        if site in sites_by_name:
            summary = dict(printed_contacts=0, shorter_than_vdw=0, image_contacts=0,
                           largest_overlap_A=None, largest_contacts=[], largest_image_overlap_A=None,
                           largest_image_contacts=[])
            selected[key] = summary
            sites_by_name[site].setdefault("atoms", {})[name] = summary
            sites_by_name[site]["component"] = component
    missing = [site for site, group in sites_by_name.items() if not group]
    if missing:
        raise ValueError("Requested site absent from the model: " + ", ".join(missing))
    data = geometry.read_bytes()
    sections = {}
    reason = None
    try:
        for ends, actual, vdw, image, origin in _contacts(data.decode("utf-8"), labels, sections):
            for key in dict.fromkeys(ends):
                if key not in selected:
                    continue
                summary = selected[key]
                overlap = float(Decimal(vdw) - Decimal(actual))
                summary["printed_contacts"] += 1
                summary["shorter_than_vdw"] += int(overlap > 0)
                summary["image_contacts"] += int(image is not None)
                row = dict(endpoints=[list(e) for e in ends], origin=origin,
                           model_A=float(actual), vdw_A=float(vdw), image_of_second_atom=image)
                _retain_largest(summary, "largest_overlap_A", "largest_contacts", overlap, row)
                if image is not None:
                    _retain_largest(summary, "largest_image_overlap_A", "largest_image_contacts", overlap, row)
    except ValueError as exc:
        reason = str(exc)
    if model.read_bytes() != raw or geometry.read_bytes() != data:
        raise ValueError("Checkpoint files changed during the nonbonded contact reading")
    status = "UNASSESSED" if reason else "OBSERVED" if sections else "NOT_RECORDED"
    return dict(policy_id="phenix-printed-local-contacts-v1", status=status, reason=reason,
                sections=sections if reason is None else None, requested_sites=list(sites),
                sites=sites_by_name if status == "OBSERVED" else None, model_sha256=sha256(raw).hexdigest(),
                geometry_sha256=sha256(data).hexdigest(), scientific_approval="NOT_ASSESSED")
