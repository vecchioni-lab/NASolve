"""Compare printed phosphate angles with the two coordinate frames in a saved PDB."""
from decimal import Decimal
from math import asin, degrees, dist, isfinite, sqrt
import re

from .cif_printed_parallelity import _LABEL, _NUMBER, _SECTION
from .refinement_link_geometry import _within
from .topostitch_contacts import _angle
from .topostitch_graph import _compose, _inverse, _operator
from .topostitch_periodic import _op_key


def _require(condition, message):
    if not condition:
        raise ValueError("Printed angles: " + message)


def _label(line, labels):
    match = _LABEL.match(line)
    _require(match and match[0][5:-1] in labels, "require a single atom label from the written model")
    tail = line[match.end():]
    _require(not tail or tail[0].isspace(), "unrecognized angle label suffix")
    image = tail.strip() or None
    if image is not None:
        _require(re.fullmatch(r"[xyz0-9/+*-]+(?:,[xyz0-9/+*-]+){2}", image), "unrecognized angle image")
    return labels[match[0][5:-1]][0], image


def _reads_as(points, printed):
    if any(point is None for point in points):
        return None, None
    value = _angle(points)
    # Each endpoint can move half a PDB coordinate unit per Cartesian axis.
    # An isometry preserves that bound, also for the atom from the other cell.
    arm_error = sqrt(3) * 0.001
    arms = (dist(points[0], points[1]), dist(points[2], points[1]))
    if value is None or min(arms) <= arm_error:
        return value, None
    tolerance = sum(degrees(asin(arm_error / arm)) for arm in arms)
    return value, _within(value, printed, extra=tolerance)


def _relative_images(ops, identity):
    # A common change of crystal frame cancels at the vertex.
    inverse_vertex = _inverse(ops[1], identity)
    return [_op_key(_compose(inverse_vertex, op)) for op in ops]


def _compare(atoms, image_ops, sample, reversed_order, origin, values, mate, identity, gemmi, members):
    relation = "NOT_PRINTED"
    if any(image_ops):
        printed = [_operator(op, gemmi, members) if op else identity for op in image_ops]
        expected = [mate if use_mate else identity for use_mate in sample["image_atoms"]]
        if reversed_order:
            expected.reverse()
        relation = "REQUESTED_IMAGE" if _relative_images(printed, identity) == _relative_images(expected, identity) else "OTHER_IMAGE"
    asu, asu_match = _reads_as(sample["asu"], values[1])
    crystal, crystal_match = _reads_as(sample["mate"], values[1])
    agreement = {(True, True): "BOTH", (False, True): "CRYSTAL_MATE",
                 (True, False): "ASYMMETRIC_UNIT", (False, False): "NEITHER"}.get((asu_match, crystal_match), "UNAVAILABLE")
    return dict(angle=sample["name"], origin=origin, endpoints=[list(atom) for atom in atoms],
                printed_operators=list(image_ops), image_relation=relation, coordinate_agreement=agreement,
                ideal_degrees=float(values[0]), model_degrees=float(values[1]), sigma_degrees=float(values[3]),
                asymmetric_unit_degrees=asu, crystal_mate_degrees=crystal)


def visit_printed_angles(text, labels, visit):
    """Visit the rows of complete native bond-angle sections and return their counts.

    A caller must discard collected rows if a later row or section is incomplete.
    """
    sections = {}
    origin = None
    count = 0
    lines = iter(text.splitlines())
    try:
        for line in lines:
            header = _SECTION.fullmatch(line) if "|" in line else None
            if header:
                _require(origin is None or count == sections[origin], "incomplete angle section")
                kind, name, count_kind, total = header.groups()
                origin = name if kind == "Bond angle" else None
                if origin is not None:
                    _require(count_kind == "restraints" and origin not in sections, "duplicate or unsupported angle section")
                    sections[origin], count = int(total), 0
                continue
            stripped = line.strip()
            _require(not stripped.startswith("Bond angle"), "unsupported bond-angle section heading")
            if origin is None:
                _require(not stripped.startswith("angle "), "angle has no enclosing section")
                continue
            if not stripped or stripped == "Sorted by residual:":
                continue
            first = stripped.split(maxsplit=1)
            _require(len(first) == 2 and first[0] == "angle", "unsupported angle row")
            rows = (first[1], next(lines).strip(), next(lines).strip())
            atoms, ops = zip(*(_label(row, labels) for row in rows))
            _require(next(lines).split() == ["ideal", "model", "delta", "sigma", "weight", "residual"],
                     "unsupported angle value columns")
            values = next(lines).split()
            _require(len(values) == 6 and all(_NUMBER.fullmatch(n) and isfinite(float(n)) for n in values),
                     "invalid angle values")
            _require(0 <= float(values[1]) <= 180 and Decimal(values[1]).as_tuple().exponent <= -2
                     and float(values[3]) > 0 and float(values[4]) >= 0 and float(values[5]) >= 0,
                     "unsupported printed angle or precision")
            count += 1
            _require(count <= sections[origin], "more angles than declared")
            visit(atoms, ops, origin, values)
        _require(origin is None or count == sections[origin], "incomplete angle section")
    except StopIteration as exc:
        raise ValueError("Incomplete printed angle row") from exc
    return sections


def printed_phosphate_angles(text, labels, samples, mate, gemmi, members):
    """Read complete native bond-angle sections. Values describe the written PDB and cell."""
    matches = []
    identity = gemmi.Op("x,y,z")

    def collect(atoms, ops, origin, values):
        reverse = atoms not in samples
        sample = samples.get(atoms[::-1] if reverse else atoms)
        if sample is not None:
            matches.append(_compare(atoms, ops, sample, reverse, origin, values, mate, identity, gemmi, members))

    try:
        sections = visit_printed_angles(text, labels, collect)
    except ValueError as exc:
        return dict(status="UNASSESSED", reason=str(exc), sections=None, matches=None)
    return dict(status="OBSERVED" if sections else "NOT_RECORDED", sections=sections,
                matches=matches if sections else None)
