"""Compare the inter-residue bonds printed by Phenix with the checked preparation.

Only an explicit source supplies chemical connectivity and named PHIL distances.
A printed symmetry operation acts on the second atom. Its chemical intent and
image coordinates need a separate crystal contact declaration.
"""
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from math import dist, isfinite, sqrt, ulp
from pathlib import Path
import re

from .cif_explicit_na_policy import _model
from .cif_printed_parallelity import _LABEL, _NUMBER, _SECTION
from .cif_restraint_context import derive_restraint_context
from .cif_topology_gate import _declared, _edge

POLICY_ID = "cif-printed-inter-residue-bonds-v1"


def _require(condition, message):
    if not condition:
        raise ValueError("Refined bonds: " + message)


def _identity(atom):
    literal = atom["identity"]
    return (literal["chain_id"] + ":" + literal["resseq"], literal["resname"], atom["atom_id"])


def _declarations(model, links, phils):
    raw, atoms, _, codes, _, _ = _model(model)
    keys = [_identity(atom) for atom in atoms]
    expected = []
    for left, right in links:
        _require(left in codes and right in codes, "backbone declaration names an absent site")
        expected.append({"endpoints": [
            {"site": left, "component": codes[left], "atom_id": "O3'"},
            {"site": right, "component": codes[right], "atom_id": "P"},
        ]})
    backbone = set(_declared(expected, set(keys))) if expected else set()
    supplied = {}
    frame_hashes = []
    if phils:
        context = derive_restraint_context(model, list(phils))
        _require(context["model_sha256"] == sha256(raw).hexdigest(), "prepared model changed while reading its frame")
        frame_hashes = [row["sha256"] for row in context["inputs"]]
        for request in context["requests"]:
            if request["kind"] != "bond":
                continue
            ends = _edge(keys[i] for i in request["i_seqs"])
            if ends[0][0] != ends[1][0]:
                _require(ends not in backbone and ends not in supplied, "overlapping declarations for a bond")
                supplied[ends] = request
    return backbone, supplied, sha256(raw).hexdigest(), frame_hashes


def _values(header, line):
    columns = header.split()
    has_image = columns[-1:] == ["sym.op."]
    fields = columns[:-1] if has_image else columns
    basic = ["ideal", "model", "delta", "sigma", "weight", "residual"]
    _require(fields in (basic, [*basic[:2], "slack", *basic[2:]]), "unsupported bond value columns")
    items = line.split()
    _require(len(items) == len(columns), "bond values differ from their columns")
    tokens = dict(zip(fields, items[:len(fields)]))
    _require(all(_NUMBER.fullmatch(v) and isfinite(float(v)) for v in tokens.values()), "invalid printed number")
    # The Phenix table prints distances to 0.001 Å and uncertainties and weights
    # to three significant digits. A rounded transcription cannot verify these.
    _require(all(Decimal(tokens[k]).as_tuple().exponent <= -3 for k in ("ideal", "model"))
             and all(len(Decimal(tokens[k]).as_tuple().digits) >= 3 for k in ("sigma", "weight")),
             "insufficient printed precision for native bond values")
    _require(all(float(tokens[k]) > 0 for k in ("ideal", "sigma", "weight"))
             and all(float(tokens.get(k, 0)) >= 0 for k in ("model", "residual", "slack")), "invalid bond parameter")
    image = items[-1] if has_image else None
    if has_image:
        _require(re.fullmatch(r"[xyz0-9/+*-]+(?:,[xyz0-9/+*-]+){2}", image), "unrecognized printed symmetry operator")
    return tokens, image


def _printed_rows(text, labels, *, intra_components=()):
    """Read every bond section. Keep intramonomer rows for requested components."""
    sections = {}
    links = []
    origin = None
    expected = count = 0
    lines = iter(text.splitlines())
    for line in lines:
        section = _SECTION.fullmatch(line) if "|" in line else None
        if section:
            _require(origin is None or count == expected, "printed bond count differs from the header")
            kind, name, unit, total = section.groups()
            origin = name if kind == "Bond" else None
            if origin is not None:
                _require(unit == "restraints" and origin not in sections, "duplicate or unsupported bond section")
                expected, count = int(total), 0
                sections[origin] = expected
            continue
        stripped = line.strip()
        _require(not stripped.startswith("Bond "), "unsupported bond section heading")
        if origin is None:
            _require(not stripped.startswith("bond "), "bond has no enclosing section")
            continue
        if not stripped or stripped == "Sorted by residual:":
            continue
        first = re.fullmatch(r'bond\s+(pdb="[^"]+")', stripped)
        _require(first, "unsupported bond label or incomplete header")
        try:
            second, header, values = next(lines).strip(), next(lines), next(lines)
        except StopIteration as exc:
            raise ValueError("Refined bonds: incomplete printed bond") from exc
        _require(_LABEL.fullmatch(second), "require a second PDB atom label")
        names = [first[1][5:-1], second[5:-1]]
        _require(all(name in labels for name in names), "printed atom label is absent from the written model")
        (left, xyz_left), (right, xyz_right) = (labels[name] for name in names)
        numbers, image = _values(header, values)
        count += 1
        _require(count <= expected, "more bonds than declared in the header")
        if image is None and left[0] == right[0] and left[1] not in intra_components:
            continue
        if image is None:
            model_distance = dist(xyz_left, xyz_right)
            # Each written PDB component can differ by 0.0005 Å per atom.
            _require(_within(model_distance, numbers["model"], extra=sqrt(3)*0.001),
                     "printed bond length differs from the written coordinates")
        links.append(((left, right), origin, numbers, image))
    _require(origin is None or count == expected, "incomplete printed bond section")
    return sections, links


def _within(value, printed, extra=0):
    number = Decimal(printed)
    half_unit = Decimal(1).scaleb(number.as_tuple().exponent) / 2
    return abs(Decimal(str(value)) - number) <= half_unit + Decimal(str(extra + 2*ulp(value)))


def _endpoint_rows(edges):
    return [[list(atom) for atom in edge] for edge in sorted(edges)]


def _model_labels(model):
    """Bind the fixed-column labels printed by Phenix to validated PDB identities."""
    raw, atoms, _, _, _, _ = _model(model)
    records = (line for line in raw.decode("ascii").splitlines() if line[:6] in {"ATOM  ", "HETATM"})
    labels = {
        line[12:27]: (_identity(atom), tuple(float(line[i:i+8]) for i in (30, 38, 46)))
        for line, atom in zip(records, atoms, strict=True)
    }
    _require(len(labels) == len(atoms), "ambiguous PDB atom labels")
    return raw, labels


def _supplied_distance_fit(rows):
    """Give both extremes among uniquely matched same-image inter-residue edits."""
    occurrences = Counter(_edge(row["endpoints"]) for row in rows if row["image_of_second_atom"] is None)
    ranked = []
    ambiguous = 0
    for row in rows:
        if row["classification"] != "DECLARED_SUPPLIED_DISTANCE":
            continue
        ends = _edge(row["endpoints"])
        if occurrences[ends] != 1:
            ambiguous += 1
            continue
        measured, target, sigma = (Decimal(str(row[k])) for k in ("model_A", "target_A", "sigma_A"))
        widths = float((measured - target) / sigma)
        ranked.append(dict(endpoints=[list(atom) for atom in ends], target_A=row["target_A"],
                           model_A=row["model_A"], sigma_A=row["sigma_A"], signed_widths=widths))
    short = min((r for r in ranked if r["signed_widths"] < 0),
                key=lambda r: (r["signed_widths"], r["endpoints"]), default=None)
    long = min((r for r in ranked if r["signed_widths"] > 0),
               key=lambda r: (-r["signed_widths"], r["endpoints"]), default=None)
    return dict(count=len(ranked), ambiguous=ambiguous, most_compressed=short, most_extended=long)


def read_refined_links(model, geometry, *, preparation_model=None, backbone_links=None, restraint_phils=(),
                       allow_unassessed=False):
    """Account for every printed cross-site bond or crystal-image bond in a final GEO.

    With no preparation, report observed endpoints and origins only. The caller
    binds the checkpoint files and preparation to their recorded lineage. Values
    from the GEO have printed precision. A match concerns these bonds alone.
    """
    _require((preparation_model is None) == (backbone_links is None), "require both a preparation model and its backbone")
    _require(preparation_model is not None or not restraint_phils, "supplied distances need a preparation model")
    model, geometry = Path(model), Path(geometry)
    raw, labels = _model_labels(model)
    data = geometry.read_bytes()
    declared = preparation_model is not None
    backbone, supplied, source, frame_hashes = (
        _declarations(preparation_model, backbone_links, restraint_phils) if declared else (set(), {}, None, None)
    )
    reason = None
    try:
        sections, printed = _printed_rows(data.decode("utf-8"), labels)
    except ValueError as exc:
        if not allow_unassessed:
            raise
        # An unreadable native table can coexist with a usable model.
        # Discard partial counts. Source validation and file identity still apply.
        reason = str(exc)
        sections, printed = {}, []
    remaining_backbone, remaining_supplied = backbone.copy(), supplied.copy()
    rows = []
    needs_review = False
    for ends, origin, numbers, image in printed:
        key = _edge(ends)
        if image is not None:
            classification = "SYMMETRY_REVIEW"
        elif not declared:
            classification = "OBSERVED"
        elif origin == "covalent geometry" and key in remaining_backbone and float(numbers.get("slack", 0)) == 0:
            classification = "DECLARED_BACKBONE"
            remaining_backbone.remove(key)
        elif origin == "User supplied" and key in remaining_supplied:
            request = remaining_supplied[key]
            weight = request["weight"]
            same = (_within(request["distance_ideal"], numbers["ideal"]) and _within(weight, numbers["weight"])
                    and _within(1/sqrt(weight), numbers["sigma"]) and float(numbers.get("slack", 0)) == 0)
            if same:
                classification = "DECLARED_SUPPLIED_DISTANCE"
                del remaining_supplied[key]
            else:
                classification = "OUTSIDE_DECLARATION"
        else:
            classification = "OUTSIDE_DECLARATION"
        if classification in {"SYMMETRY_REVIEW", "OUTSIDE_DECLARATION"}:
            needs_review = True
        rows.append(dict(endpoints=[list(e) for e in ends], origin=origin, classification=classification,
                         target_A=float(numbers["ideal"]), model_A=float(numbers["model"]), sigma_A=float(numbers["sigma"]),
                         weight=float(numbers["weight"]), slack_A=float(numbers.get("slack", 0)), image_of_second_atom=image))
    if reason is not None:
        status = "UNASSESSED"
    elif not sections:
        status = "NOT_RECORDED"
    elif not declared:
        status = "OBSERVED"
    else:
        status = "REVIEW" if needs_review or remaining_backbone or remaining_supplied else "MATCH"
    compared = bool(sections) and declared
    _require(geometry.read_bytes() == data and model.read_bytes() == raw, "checkpoint files changed during read")
    return dict(schema_version=1, policy_id=POLICY_ID, status=status, sections=sections, links=rows,
                **({"reason": reason} if reason is not None else {}),
                model_sha256=sha256(raw).hexdigest(), geometry_sha256=sha256(data).hexdigest(),
                preparation_model_sha256=source, restraint_input_sha256=frame_hashes,
                supplied_distance_fit=_supplied_distance_fit(rows) if compared else None,
                matched_backbone=len(backbone)-len(remaining_backbone) if compared else None,
                matched_supplied=len(supplied)-len(remaining_supplied) if compared else None,
                missing_backbone=_endpoint_rows(remaining_backbone) if compared else None,
                missing_supplied=_endpoint_rows(remaining_supplied) if compared else None,
                geometry_scope="Printed inter-residue and crystal-image bonds; distances at printed precision.",
                scientific_approval="NOT_ASSESSED", automatic_adoption=False)


def preflight_link_inputs(run, checkpoint):
    """Find the original model and its zero-cycle GEO in an already validated round."""
    from .campaign_records import read_record
    from .refinement_inputs import _bound_path
    from .refinement_parallelity import _root, read_execution_request

    execution = checkpoint.get("outputs", {}).get("parallelity_execution")
    if execution is None:
        return None
    identity = checkpoint["id"]
    root = _root(identity)
    _require(execution.get("anchor") == "run" and execution.get("relative_path") == root + "/execution.json",
             "execution belongs to a different round")
    record = read_record(_bound_path(execution, "refinement execution", run))
    _require(record["checkpoint"] == identity, "execution checkpoint differs")
    request = read_execution_request(run, record["request"], checkpoint=identity)
    _require(request["parent"] == checkpoint["parent"], "preflight parent differs")
    phase = record["phases"][0]
    _require(phase["name"] == "preflight", "first native phase is not preflight")
    if request.get("preflight_mode") != "native-model-zero-cycle-isolated-v1" or phase["returncode"] != 0:
        return None
    name = root + "/preflight/native_001.geo"
    refs = [ref for ref in phase["files"] if ref["relative_path"] == name]
    if not refs:
        return None
    _require(len(refs) == 1 and refs[0]["anchor"] == "run" and len(request["inputs"]) >= 2,
             "ambiguous zero-cycle geometry or entrance model")
    model = request["inputs"][1]
    geo = refs[0]
    return ((_bound_path(model, "preflight entrance model", run), model),
            (_bound_path(geo, "preflight geometry", run), geo))


def read_checkpoint_link_geometry(run, registry, verified, checkpoint, model, geometry):
    """Use the closest checked preparation already verified by the registry reader."""
    from .refinement_chemistry import _preparation_context

    context = _preparation_context(run, registry, verified, checkpoint)
    return read_prepared_link_geometry(context, model, geometry)


def read_prepared_link_geometry(context, model, geometry, *, allow_unassessed=False):
    """Compare to one already verified preparation and bind its source bytes."""
    if context is None:
        return dict(read_refined_links(model, geometry), preparation_checkpoint=None)
    acquired, preparation_id, _ = context
    bundle = acquired["bundle"]
    directory = acquired["bundle_directory"]
    names = bundle["report"]["supplementary_phils"]
    pins = {row["path"]: row["sha256"] for row in bundle["report"]["files"]}
    source_name = bundle["model"].relative_to(directory).as_posix()
    report = read_refined_links(
        model, geometry, preparation_model=bundle["model"], backbone_links=bundle["report"]["expected_links"],
        restraint_phils=[directory / name for name in names], allow_unassessed=allow_unassessed,
    )
    _require(report["preparation_model_sha256"] == pins[source_name]
             and report["restraint_input_sha256"] == [pins[name] for name in names],
             "declarations differ from the checked preparation")
    return dict(report, preparation_checkpoint=preparation_id)


def _stage_summary(report):
    """Keep counts and the first actionable finding in the ordinary round report."""
    if report is None:
        return None
    result = {key: report[key] for key in ("status", "model_sha256", "geometry_sha256")}
    if report["status"] == "UNASSESSED":
        return dict(result, reason=report["reason"])
    if report["status"] == "NOT_RECORDED":
        return dict(result, reason="No bond table was printed.")
    issues = [r for r in report["links"] if r["classification"] in {"OUTSIDE_DECLARATION", "SYMMETRY_REVIEW"}]
    first = issues[0] if issues else None
    for kind in ("missing_backbone", "missing_supplied"):
        if first is None and report[kind]:
            first = dict(classification=kind.upper(), endpoints=report[kind][0])
    return dict(result, matched_backbone=report["matched_backbone"], matched_supplied=report["matched_supplied"],
                outside_declaration=sum(row["classification"] == "OUTSIDE_DECLARATION" for row in issues),
                crystal_images=sum(row["classification"] == "SYMMETRY_REVIEW" for row in issues),
                missing_backbone=len(report["missing_backbone"] or ()), missing_supplied=len(report["missing_supplied"] or ()),
                first_issue=first)


def summarize_round_links(preparation_id, initial, refined):
    """Use the same rule when publishing a round and independently reopening it."""
    return dict(policy_id=POLICY_ID, preparation_checkpoint=preparation_id,
                preflight=_stage_summary(initial), refined=_stage_summary(refined),
                requires_review=any(stage is None or stage["status"] != "MATCH" for stage in (initial, refined)))


def review_round_links(run, registry, verified, parent, checkpoint, execution, model, geometry):
    """Summarize an opt-in ordinary round from its established preparation and native evidence."""
    from .refinement_chemistry import _preparation_context

    context = _preparation_context(run, registry, verified, parent)
    if context is None:
        return None
    item = dict(id=checkpoint, parent=parent["id"], outputs={"parallelity_execution": execution})
    early = preflight_link_inputs(run, item)
    initial = refined = None
    if early is not None:
        (entrance, entrance_ref), (geo, geo_ref) = early
        initial = read_prepared_link_geometry(context, entrance, geo, allow_unassessed=True)
        _require(initial["model_sha256"] == entrance_ref["sha256"] and initial["geometry_sha256"] == geo_ref["sha256"],
                 "preflight bonds differ from their recorded model or geometry")
    if model is not None and geometry is not None:
        refined = read_prepared_link_geometry(context, model, geometry, allow_unassessed=True)
    return summarize_round_links(context[1], initial, refined)
