"""Locate literal PHIL bond edits for comparison with a printed Phenix target."""
from collections import defaultdict
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re

from .cif_na_policy import _parse, _path, _site_selection
from .refinement_link_geometry import _within


def _endpoint(expression, atoms):
    match = re.fullmatch(r"(.+?)\s+and\s+name\s+(.+)", expression)
    if match is None:
        raise ValueError("Require a literal atom selection")
    chain, residue = _site_selection(match[1])
    name = match[2]
    if len(name) >= 2 and name[0] == name[-1] and name[0] in {"'", '"'}:
        name = name[1:-1]
    if not re.fullmatch(r"[A-Za-z0-9_]+(?:'{1,2})?", name):
        raise ValueError("Require one literal atom name")
    return atoms[chain + ":" + residue, name]


def explicit_bond_edits(bound_inputs, labels):
    """Read each ordered, fingerprinted input. Keep duplicates and incomplete readings."""
    atoms = {(site, name): (site, code, name) for (site, code, name), _ in labels.values()}
    edits, inputs = defaultdict(list), []
    required = {"action", "atom_selection_1", "atom_selection_2", "distance_ideal", "sigma"}
    for index, (supplied, reference) in enumerate(bound_inputs):
        path = Path(supplied)
        if path.suffix.casefold() in {".cif", ".mmcif"}:
            continue
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        if index != reference.get("input_index") or digest != reference.get("sha256"):
            raise ValueError("Bond edit input differs from the assessed restraint")
        summary = dict(input_index=index, name=path.name, sha256=digest, status="READ_LITERAL_BLOCKS",
                       read_bond_blocks=0, unread_bond_blocks=0)
        inputs.append(summary)
        try:
            nodes, _ = _parse(raw.decode("utf-8"))
        except ValueError as exc:
            summary.update(status="UNASSESSED", reason=str(exc))
            nodes = []
        for node in nodes:
            if _path(node) != "geometry_restraints.edits.bond":
                continue
            f = node["fields"]
            try:
                if (node["children"] or not required.issubset(f) or f.keys() - required - {"slack"}
                        or f["action"] not in {"add", "change"}):
                    raise ValueError("Unsupported bond edit")
                endpoints = tuple(sorted(_endpoint(f[k], atoms) for k in ("atom_selection_1", "atom_selection_2")))
                ideal, sigma, slack = float(f["distance_ideal"]), float(f["sigma"]), float(f.get("slack", 0))
                if not all(isfinite(v) for v in (ideal, sigma, slack)) or min(ideal, sigma) <= 0 or slack < 0:
                    raise ValueError("Invalid bond edit parameters")
            except (KeyError, ValueError):
                summary["unread_bond_blocks"] += 1
                summary["status"] = "PARTIAL"
                continue
            summary["read_bond_blocks"] += 1
            if endpoints[0][:2] == endpoints[1][:2] and endpoints[0] != endpoints[1]:
                edits[endpoints].append(dict(input_index=index, line=node["start"] + 1, action=f["action"],
                                             ideal_A=ideal, sigma_A=sigma, slack_A=slack))
        if path.read_bytes() != raw:
            raise ValueError("Restraint input changed during bond edit inspection")
    return edits, inputs


def compare_explicit_edits(edits, left, right, numbers, image):
    if image not in (None, "x,y,z"):
        return []
    results = []
    for edit in edits.get(tuple(sorted((left, right))), []):
        slack_matches = (_within(edit["slack_A"], numbers["slack"])
                         if "slack" in numbers else edit["slack_A"] == 0)
        matches = slack_matches and _within(edit["ideal_A"], numbers["ideal"]) and _within(edit["sigma_A"], numbers["sigma"])
        results.append(dict(edit, matches_printed_parameters=matches))
    return results
