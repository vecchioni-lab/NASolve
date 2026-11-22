"""Compare written Phenix intramonomer bond targets with explicitly supplied CIFs."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

from .cif_doctor import _number
from .refinement_link_geometry import _model_labels, _printed_rows, _within

_DIFFERENCES = {"TARGET_DIFFERS", "SIGMA_DIFFERS", "TARGET_AND_SIGMA_DIFFER"}


def _definitions(components):
    """Use Doctor's parsed numerical tables and preserve ambiguous input precedence."""
    grouped = defaultdict(list)
    for item in components:
        grouped[item["component_id"]].append(item)
    result = {}
    for component, entries in grouped.items():
        indices = [item["input_index"] for item in entries]
        digests = {item["definition_sha256"] for item in entries}
        bonds = None
        if len(digests) == 1:
            bonds = defaultdict(list)
            for row in entries[0]["inventory"]["numerical_restraints"]["bond"]:
                a, b = row.get("atom_id_1"), row.get("atom_id_2")
                if a and b:
                    bonds[tuple(sorted((a, b)))].append(row)
        result[component] = indices, bonds
    return result


def _compare_row(declarations, numbers):
    if declarations is None:
        return "AMBIGUOUS_DEFINITION", None, None
    if not declarations:
        return "NO_DECLARED_BOND", None, None
    if len(declarations) != 1:
        return "AMBIGUOUS_BOND", None, None
    row = declarations[0]
    try:
        ideal, sigma = (_number(row.get(k)) for k in ("value_dist", "value_dist_esd"))
        # A dictionary with an alternative nuclear target needs the native
        # radiation/typing context before the effective target can be attributed.
        nuclear = _number(row.get("value_dist_nucleus"))
    except (TypeError, ValueError):
        return "INVALID_DECLARATION", None, None
    if nuclear is not None:
        return "SEPARATE_NUCLEAR_TARGET", ideal, sigma
    if ideal is None or sigma is None or ideal <= 0 or sigma <= 0:
        return "NO_NUMERICAL_TARGET", ideal, sigma
    target_matches = _within(ideal, numbers["ideal"])
    sigma_matches = _within(sigma, numbers["sigma"])
    states = {(True, True): "AGREES", (False, True): "TARGET_DIFFERS",
              (True, False): "SIGMA_DIFFERS", (False, False): "TARGET_AND_SIGMA_DIFFER"}
    return states[target_matches, sigma_matches], ideal, sigma


def read_component_bond_targets(model, geometry, components):
    """Observe every printed same-residue bond belonging to an inventoried component.

    Include individual rows for differences, unresolved readings and user-supplied
    bonds. An effective linked monomer can legitimately differ from its input CIF.
    """
    model, geometry = Path(model), Path(geometry)
    raw, labels = _model_labels(model)
    data = geometry.read_bytes()
    definitions = _definitions(components)
    counts, observations = Counter(), []
    try:
        sections, printed = _printed_rows(data.decode("utf-8"), labels, intra_components=definitions)
    except ValueError as exc:
        sections, printed, reason = None, [], str(exc)
    else:
        reason = None
    for (left, right), origin, numbers, image in printed:
        site, component, first = left
        if right[:2] != left[:2] or component not in definitions:
            continue
        atoms = tuple(sorted((first, right[2])))
        indices, bonds = definitions[component]
        if image not in (None, "x,y,z"):
            status, ideal, sigma = "CRYSTAL_IMAGE", None, None
        else:
            declarations = bonds.get(atoms, []) if bonds is not None else None
            status, ideal, sigma = _compare_row(declarations, numbers)
        counts[status] += 1
        if status != "AGREES" or origin == "User supplied":
            observations.append(dict(site=site, component=component, atoms=list(atoms), origin=origin,
                                     comparison=status, input_indices=indices, image_of_second_atom=image,
                                     dictionary_ideal_A=ideal, dictionary_sigma_A=sigma,
                                     printed_ideal_A=float(numbers["ideal"]), printed_sigma_A=float(numbers["sigma"]),
                                     printed_slack_A=float(numbers.get("slack", 0)), model_A=float(numbers["model"])))
    if model.read_bytes() != raw or geometry.read_bytes() != data:
        raise ValueError("Model or printed geometry changed during the bond target comparison")
    status = "UNASSESSED" if reason else ("OBSERVED" if sections else "NOT_RECORDED")
    return dict(policy_id="printed-component-bond-targets-v1", model_sha256=sha256(raw).hexdigest(),
                geometry_sha256=sha256(data).hexdigest(), status=status, reason=reason, sections=sections,
                counts=dict(sorted(counts.items())) if sections else None, observations=observations if sections else None,
                scope="Printed same-residue bonds for explicit input components, at GEO precision.",
                scientific_approval="NOT_ASSESSED")


def apply_bond_target_review(receipt):
    """Keep the dictionary verdict and flag differences only when this inspection was requested."""
    receipt.setdefault("dictionary_status", receipt["status"])
    final = receipt["refined_bond_targets"]
    stages = [r for r in (receipt.get("preflight_bond_targets"), final) if r is not None]
    findings = {kind for r in stages for kind in (r["counts"] or {})}
    if findings & _DIFFERENCES:
        verdict = "REVIEW"
    elif (final is None or not final["counts"] or findings - {"AGREES"}
          or any(r["status"] != "OBSERVED" for r in stages)):
        verdict = "UNASSESSED"
    else:
        verdict = "AGREES_AT_PRINTED_PRECISION"
    receipt["bond_target_status"] = verdict
    if verdict == "REVIEW" and receipt["status"] != "INVALID":
        receipt["status"] = "REVIEW"
    elif verdict == "UNASSESSED" and receipt["status"] == "PASS":
        receipt["status"] = "UNASSESSED"
