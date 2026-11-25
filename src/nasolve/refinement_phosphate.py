"""Carry declared crystal phosphodiesters through an ordinary numbered refinement."""
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from math import floor, log10
from pathlib import Path
import re

from .campaign_records import path_in, read_record
from .checkpoint_candidate import _lineage
from .checkpoints import _file_reference, _ref_path, resolve_checkpoint
from .cif_geometry_report_replay import _exact
from .cif_dictionary_sites import _bind_capture_inputs, _bind_capture_input_pins
from .cif_phosphate_continuation import RegisteredContinuation, inspect_inherited_continuation
from .cif_phosphate_restraints import phosphate_bond_phil
from .cif_phosphate_runtime import RegisteredPhosphateRuntime
from .refinement_inputs import _bound_path

_SOURCE_NAMES = ("registration", "discovery", "continuations")


@dataclass(frozen=True)
class PhosphateRequest:
    native_receipt: Path
    registered: RegisteredContinuation | None = None
    registration_checkpoint: str | None = None
    additional_ids: tuple[int, ...] = ()
    prepared_backbone_source: Path | None = None


def _ordered_ids(values):
    if any(type(v) is not int or v < 1 for v in values) or len(set(values)) != len(values):
        raise ValueError("Registered continuation IDs must be distinct positive integers")
    return tuple(sorted(values))


def request_from_args(args):
    paths = (args.registration, args.discovery_input, args.backbone_continuations)
    ids = ()
    if getattr(args, "registered_continuations", None) is not None:
        ids = _ordered_ids(args.registered_continuations)
        if len(ids) < 2:
            raise ValueError("Use --registered-continuation for one phosphate or give at least two distinct IDs")
    elif args.registered_continuation is not None:
        ids = _ordered_ids([args.registered_continuation])
    source = getattr(args, "prepared_backbone_source", None)
    if source is not None and (not ids or not args.from_checkpoint or (not args.registration_checkpoint and args.from_checkpoint != "postmr")
                               or args.native_receipt is None or any(p is None for p in paths)):
        raise ValueError("A prepared backbone trial needs a named parent, all crystal topology and a native receipt. "
                         "Give --registration-checkpoint for an imported source, or --from postmr for the same run's construction.")
    if not ids:
        if args.registration_checkpoint is not None or any(p is not None for p in paths):
            raise ValueError("Registering crystal phosphates requires continuation IDs with all three topology files")
        return PhosphateRequest(args.native_receipt) if args.native_receipt is not None else None
    if any(p is None for p in paths) or args.native_receipt is None:
        raise ValueError("A positive continuation ID, registration, discovery input, backbone continuations and native receipt are required")
    return PhosphateRequest(args.native_receipt, RegisteredContinuation(ids[0], *paths),
                            args.registration_checkpoint, ids[1:], source)


def _prior_intent(run, registry, parent):
    from .refinement_parallelity import PHOSPHATE_POLICIES
    by_id = {row["id"]: row for row in registry["checkpoints"]}
    for key in reversed(_lineage(registry, parent)):
        ref = (by_id[key].get("outputs") or {}).get("parallelity_execution")
        if ref is not None:
            sealed = read_record(_bound_path(ref, "ancestor execution", run))
            if sealed["policy_id"] in PHOSPHATE_POLICIES:
                request = read_record(_bound_path(sealed["request"], "ancestor request", run))
                return request["phosphate"]
    return None


def _identity(ancestor, edge):
    return (ancestor, edge["continuation_id"], edge["sources"], edge["registered_graph_sha256"],
            edge["source"], edge["target"], edge["oxygen_operator_xyz"])


def _inspections(intent):
    return intent["inspections"] if "inspections" in intent else [intent["inspection"]]


def _frozen_registration(run, intent, inspection=None):
    if inspection is None:
        inspection, = _inspections(intent)
    identifier = inspection["registered_continuation"].get("continuation_id")
    if type(identifier) is not int or identifier < 1:
        raise ValueError("The saved phosphate has no valid continuation ID")
    paths = (_bound_path(intent["sources"][name], "frozen phosphate " + name, run) for name in _SOURCE_NAMES)
    return RegisteredContinuation(identifier, *paths)


def _check_inherited_scope(prior, ancestor, observations, *, construction_sha256=None):
    if prior is None:
        return
    old = [_identity(prior["ancestor"], row["registered_continuation"]) for row in _inspections(prior)]
    new = [_identity(ancestor, row["registered_continuation"]) for row in observations]
    if new != old or prior.get("postmr_construction_sha256") != construction_sha256:
        raise ValueError("Changing an inherited phosphate registration requires a different starting branch")


def _original(run, registry, parent, checkpoint):
    ancestor = resolve_checkpoint(registry, checkpoint)
    if ancestor["id"] not in _lineage(registry, parent):
        raise ValueError("Phosphate registration belongs to a different checkpoint branch")
    if ancestor["model"].get("anchor") not in ("run", "dataset", "repository"):
        raise ValueError("The original phosphate registration needs a portable checkpoint model")
    return ancestor, _bound_path(ancestor["model"], "original phosphate registration model", run)


def direct_preparation(run, parent_id, choice):
    """Only an explicit preparation from this run's ReadySet root may use its Coot construction."""
    if choice.prepared_backbone_source is None or choice.registration_checkpoint is not None:
        return False
    if parent_id != "postmr" or Path(choice.prepared_backbone_source).expanduser().resolve() != Path(run).resolve():
        raise ValueError("Using the recorded Coot construction requires --from postmr in the same run")
    return True


def construction_registration(run, ancestor_id, *, expected=None):
    """Resolve the recorded pre-ReadySet coordinates and the exact immutable construction that produced them."""
    from .postmr_lineage import read_postmr_construction

    if ancestor_id != "postmr":
        raise ValueError("A Coot construction belongs to the postmr root")
    proof = read_postmr_construction(run)
    digest = proof["report"]["record_sha256"]
    model_hash = proof["report"]["outputs"]["prepared"]["sha256"]
    model = proof["model"]
    if (not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest)
            or (expected is not None and digest != expected) or model_hash != sha256(model.read_bytes()).hexdigest()):
        raise ValueError("The PostMR construction differs from the recorded source")
    return model, model_hash, digest


def _same_native_capture(receipt, version, python_executable):
    # phenix.version can report the release alone. The capture and this round
    # must also use identical dispatcher bytes; the worker checks native code.
    pattern = r"(\d+\.\d+\.\d+)(?:-(\d+))?"
    versions = [re.fullmatch(pattern, value) for value in (receipt["phenix_version"], version)]
    if not all(versions) or versions[0][1] != versions[1][1]:
        return False
    left, right = (match[2] for match in versions)
    return ((not left or not right or left == right)
            and receipt["executable_sha256"] == sha256(Path(python_executable).read_bytes()).hexdigest())


def prepare_intent(run, registry, parent, choice, *, phenix_version, python_executable):
    """Read exact author inputs once; later native checks use the numbered snapshot."""
    prior = _prior_intent(run, registry, parent)
    registered = choice.registered
    if registered is None:
        if choice.additional_ids or choice.registration_checkpoint is not None:
            raise ValueError("Additional IDs or a registration checkpoint need an explicit phosphate registration")
        if prior is None:
            raise ValueError("This branch has no registered phosphate to continue")
        checkpoint = prior["ancestor"]
        registrations = [_frozen_registration(run, prior, row) for row in _inspections(prior)]
    else:
        checkpoint = choice.registration_checkpoint or parent["id"]
        ids = _ordered_ids((registered.identifier, *choice.additional_ids))
        registrations = [replace(registered, identifier=i) for i in ids]
    ancestor, source = _original(run, registry, parent, checkpoint)
    source_hash = ancestor["model"]["sha256"]
    origin = {}
    inherited_hash = (prior or {}).get("postmr_construction_sha256") if registered is None else None
    if direct_preparation(run, parent["id"], choice) or inherited_hash is not None:
        source, source_hash, construction_hash = construction_registration(
            run, ancestor["id"], expected=inherited_hash)
        origin["postmr_construction_sha256"] = construction_hash
    model = _bound_path(parent["model"], "phosphate starting model", run)
    observations = [inspect_inherited_continuation(source, model, reg, native_receipt=choice.native_receipt)
                    for reg in registrations]
    for observation in observations:
        reference = observation["native_reference_links"]
        if reference["status"] in ("COMPETING_ENDPOINT_BOND", "UNRESOLVED_ENDPOINT_IMAGE"):
            raise ValueError(reference["reason"])
    if len(observations) > 1:
        RegisteredPhosphateRuntime.check_group(observations)
    edges = [row["registered_continuation"] for row in observations]
    if any(edge["frame_transfer"]["source_model_sha256"] != source_hash for edge in edges):
        raise ValueError("Phosphate registration differs from its original checkpoint")
    _check_inherited_scope(prior, ancestor["id"], observations, construction_sha256=origin.get("postmr_construction_sha256"))
    receipt_raw = Path(choice.native_receipt).read_bytes()
    receipt = json.loads(receipt_raw)
    digest = sha256(receipt_raw).hexdigest()
    if any(row["native_reference_links"]["native_receipt_sha256"] != digest for row in observations) or not _same_native_capture(
            receipt, phenix_version, python_executable):
        raise ValueError("The phosphate capture or its Phenix version differs from this refinement")
    capture_inputs = [{k: row[k] for k in ("role", "sha256", "size")} for row in receipt["inputs"]]
    bond = "".join(map(phosphate_bond_phil, observations)).encode()
    sources = {name: Path(getattr(registrations[0], name)).read_bytes() for name in _SOURCE_NAMES}
    if not all(sha256(raw).hexdigest() == edges[0]["sources"][name+"_sha256"] for name, raw in sources.items()):
        raise ValueError("A phosphate topology input changed after inspection")
    scope = {"inspection": observations[0]} if len(observations) == 1 else {"inspections": observations}
    return dict(ancestor=ancestor["id"], **origin, **scope, sources=sources, bond=bond, capture_inputs=capture_inputs)


def bind_execution_inputs(prepared, model, restraints):
    _bind_capture_inputs({"inputs": prepared["capture_inputs"]}, model,
                         [p for p in restraints if p.suffix.casefold() == ".cif"],
                         [p for p in restraints if p.suffix.casefold() != ".cif"])


def bind_planned_inputs(prepared, model, restraints, *, terminal_protection=None, supplemental_phils=()):
    """Reject a mismatched capture before allocating an immutable round."""
    from .refinement_inputs import refinement_input_bytes
    def pin(role, raw):
        return role, sha256(raw).hexdigest(), len(raw)
    pins = [pin("model", model.read_bytes())]
    dictionaries, phils = [], []
    for path in restraints:
        role = "dictionary" if path.suffix.casefold() == ".cif" else "phil"
        (dictionaries if role == "dictionary" else phils).append(pin(role, refinement_input_bytes(path.read_bytes())))
    phils.extend(pin("phil", refinement_input_bytes(raw)) for raw in supplemental_phils)
    if terminal_protection is not None:
        phils.append(pin("phil", refinement_input_bytes(terminal_protection.encode())))
    _bind_capture_input_pins({"inputs": prepared["capture_inputs"]}, [*pins, *dictionaries, *phils])


def write_intent(run, root, prepared):
    """Freeze the three small topology inputs. The large native capture is already verified."""
    folder = root / "phosphate"
    folder.mkdir()
    refs = {}
    for name, raw in prepared["sources"].items():
        target = folder / (name + ".json")
        with target.open("xb") as handle:
            handle.write(raw)
        refs[name] = _file_reference(target, run)
    bond = folder / "image-bond.phil"
    with bond.open("xb") as handle:
        handle.write(prepared["bond"])
    return {**prepared, "sources": refs, "bond": _file_reference(bond, run)}


def read_intent(run, root, request):
    """Verify the frozen declaration and every bond in the execution-only PHIL."""
    try:
        return _read_intent(run, root, request)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("Malformed registered phosphate request") from exc


def _read_intent(run, root, request):
    from .refinement_parallelity import V11_POLICY_ID, V12_POLICY_ID
    intent = request.get("phosphate")
    grouped = request.get("policy_id") == V12_POLICY_ID
    scope = "inspections" if grouped else "inspection"
    fields = {"ancestor", scope, "sources", "bond", "capture_inputs"}
    if not isinstance(intent, dict) or set(intent) not in (fields, fields | {"postmr_construction_sha256"}):
        raise ValueError("Missing registered phosphate intent")
    if "postmr_construction_sha256" in intent and (intent["ancestor"] != "postmr" or request.get("policy_id") not in (V11_POLICY_ID, V12_POLICY_ID)
            or not isinstance(intent["postmr_construction_sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", intent["postmr_construction_sha256"])):
        raise ValueError("Invalid registered phosphate construction")
    observations = _inspections(intent)
    if grouped:
        if not isinstance(observations, list) or len(observations) < 2:
            raise ValueError("This round requires its complete registered phosphate set")
        ids = RegisteredPhosphateRuntime.check_group(observations)
        captures = {row["native_reference_links"]["native_receipt_sha256"] for row in observations}
        originals = {row["registered_continuation"]["frame_transfer"]["source_model_sha256"] for row in observations}
        if (ids != _ordered_ids(ids) or len(captures) != 1 or len(originals) != 1
                or not all(re.fullmatch("[0-9a-f]{64}", h) for h in (*captures, *originals))):
            raise ValueError("Crystal phosphates must share one original model and native capture in registration order")
    edge = observations[0]["registered_continuation"]
    if (not isinstance(intent["ancestor"], str) or not intent["ancestor"] or set(intent["sources"]) != set(_SOURCE_NAMES)
            or len(request["inputs"]) < 4 or any(row["model_sha256"] != request["inputs"][1]["sha256"] for row in observations)
            or any(row.get("anchor") not in ("run", "dataset", "repository") for row in request["inputs"])
            or any(row["registered_continuation"]["frame_transfer"]["child_model_sha256"] != row["model_sha256"]
                   for row in observations)):
        raise ValueError("The phosphate observation differs from its numbered parent")
    for name in _SOURCE_NAMES:
        ref = intent["sources"][name]
        expected = root + "/phosphate/" + name + ".json"
        if (ref.get("anchor") != "run" or ref.get("relative_path") != expected
                or ref.get("sha256") != edge["sources"][name+"_sha256"]
                or _bound_path(ref, "phosphate " + name, run) != path_in(run, expected)):
            raise ValueError("Phosphate topology differs from its recorded round")
    ref = intent["bond"]
    relative = root + "/phosphate/image-bond.phil"
    inputs = request["inputs"]
    if (ref.get("anchor") != "run" or ref.get("relative_path") != relative or inputs.count(ref) != 1 or inputs[-2] != ref
            or _bound_path(ref, "registered phosphate bond", run) != path_in(run, relative)
            or path_in(run, relative).read_bytes() != "".join(map(phosphate_bond_phil, observations)).encode()):
        raise ValueError("Each registered crystal bond with its exact operator is required")
    capture = intent["capture_inputs"]
    if not isinstance(capture, list) or not capture or len(inputs) - len(capture) not in (3, 4):
        raise ValueError("Phosphate capture does not cover the ordered model and restraints")
    model, *restraints = inputs[1:1+len(capture)]
    rows = [("dictionary" if Path(p["relative_path"]).suffix.casefold() == ".cif" else "phil", p)
            for p in restraints]
    ordered = [("model", model), *sorted(rows, key=lambda row: row[0] != "dictionary")]
    _bind_capture_input_pins({"inputs":capture}, [(role, p["sha256"], p["size"]) for role, p in ordered])
    return intent


def _same_observation(rebuilt, recorded):
    """Compare a saved phosphate reading; only its four coordinate angles can round."""
    angle_key = "coordinate_angles_degrees"
    if rebuilt.keys() != recorded.keys() or any(
        not _exact(value, recorded[key]) for key, value in rebuilt.items() if key != angle_key
    ):
        return False
    angles, saved = rebuilt.get(angle_key), recorded.get(angle_key)
    if _exact(angles, saved):
        return True
    if not isinstance(angles, dict) or not isinstance(saved, dict) or angles.keys() != saved.keys():
        return False
    for name, angle in angles.items():
        old = saved[name]
        if _exact(angle, old):
            continue
        if (name not in ("C3'-O3'-P", "O3'-P-OP1", "O3'-P-OP2", "O3'-P-O5'")
                or type(angle) is not float or type(old) is not float
                or not (0 < angle <= 180 and 0 < old <= 180)):
            return False
        # Half a unit in the seventh significant figure; avoid decimal bin boundaries.
        half_unit = 0.5 * 10.0 ** (floor(log10(max(angle, old))) - 6)
        if abs(angle - old) > half_unit:
            return False
    return True


def validate_lineage(run, registry, parent, intent):
    """Cold replay binds the original topology and current coordinate frame without Phenix."""
    ancestor, source = _original(run, registry, parent, intent["ancestor"])
    prior = _prior_intent(run, registry, parent)
    construction_hash = intent.get("postmr_construction_sha256")
    if construction_hash is not None:
        if parent["id"] != "postmr" and prior is None:
            raise ValueError("A Coot construction must first be fitted from the postmr root")
        source, _, _ = construction_registration(run, ancestor["id"], expected=construction_hash)
    observations = _inspections(intent)
    model = _ref_path(parent["model"], "phosphate model", run)
    for recorded in observations:
        registered = _frozen_registration(run, intent, recorded)
        actual = inspect_inherited_continuation(source, model, registered)
        if not _same_observation(actual, {k: v for k, v in recorded.items() if k != "native_reference_links"}):
            raise ValueError("The registered phosphate observation differs from the original or selected parent")
    _check_inherited_scope(prior, ancestor["id"], observations, construction_sha256=construction_hash)


def saved_refinement(run, checkpoint, *, identifier=None, restraint_deviations=False, torsion_response=False,
                     flanking_geometry=False):
    """Read the restraint evidence from this completed checkpoint's own fit."""
    from .refinement_parallelity import PHOSPHATE_POLICIES, read_execution_request, validate_execution

    reference = (checkpoint.get("outputs") or {}).get("parallelity_execution")
    missing = "The named checkpoint has no completed registered phosphate refinement"
    if checkpoint.get("kind") != "refinement" or checkpoint.get("usable") is not True or reference is None:
        raise ValueError(missing)
    record = validate_execution(run, reference, checkpoint=checkpoint["id"], parent=checkpoint["parent"], usable=True)
    if record["policy_id"] not in PHOSPHATE_POLICIES:
        raise ValueError(missing)
    request = read_execution_request(run, record["request"], checkpoint=checkpoint["id"])
    intent = request["phosphate"]
    root = Path(record["request"]["relative_path"]).parent.as_posix()
    phase = read_phase(run, root, "refine", request)
    observations = _inspections(intent)
    identifiers = [row["registered_continuation"]["continuation_id"] for row in observations]
    if identifier is None and len(observations) > 1:
        raise ValueError("This checkpoint fitted several phosphates. Use --saved-continuation-id with one of "
                         + ", ".join(map(str, identifiers)))
    if identifier is not None and (type(identifier) is not int or identifier not in identifiers):
        raise ValueError("The selected continuation ID was not fitted in this checkpoint")
    index = identifiers.index(identifier) if identifier is not None else 0
    observation = observations[index]
    fitted = phase["edges"][index] if "edges" in phase else phase
    capture = observation["native_reference_links"].get("native_receipt_sha256")
    if not isinstance(capture, str) or not re.fullmatch("[0-9a-f]{64}", capture):
        raise ValueError("The starting-model native chemistry receipt has no valid fingerprint")
    evidence = {
        "parent": request["parent"],
        "starting_model_sha256": phase["parent_model_sha256"],
        "starting_native_receipt_sha256": capture,
        "request_sha256": record["request"]["sha256"],
        "native_forces": fitted["families"],
        "native_neighbours": fitted["bond"],
        "full_gradient_calls": phase["full_gradient_calls"],
        "reflections": phase["reflections"],
    }
    if len(identifiers) > 1:
        evidence["registered_continuation_ids"] = identifiers
    if "postmr_construction_sha256" in intent:
        evidence["postmr_construction_sha256"] = intent["postmr_construction_sha256"]
    if restraint_deviations or torsion_response or flanking_geometry:
        from .cif_phosphate_reference import measure_written_phosphate
        model = checkpoint.get("model")
        path = _ref_path(model, "written phosphate model", run)
        evidence["written_restraint_geometry"] = measure_written_phosphate(
            path, observation, model_sha256=model.get("sha256"), torsion_response=torsion_response)
        if flanking_geometry:
            from .cif_doctor_run import _final_geometry
            from .refinement_residue_geometry import flanking_residue_geometry

            geo, reference = _final_geometry(run, checkpoint) or (None, {})
            evidence["flanking_residue_geometry"] = flanking_residue_geometry(
                path, geo, observation, model_sha256=model["sha256"].lower(),
                geometry_sha256=reference["sha256"].lower() if geo is not None else None)
    return intent["ancestor"], _frozen_registration(run, intent, observation), evidence


def read_phase(run, root, phase, request):
    """Read checked phosphate and free-set observations without invoking native code."""
    directory = path_in(run, root)
    row = json.loads(path_in(directory, phase+"/phosphate.json").read_bytes())
    inspections = _inspections(request["phosphate"])
    grouped = "inspections" in request["phosphate"]
    expected = dict(schema_version=2 if grouped else 1, phase=phase,
                    request_sha256=sha256((directory/"request.json").read_bytes()).hexdigest(),
                    parent_model_sha256=inspections[0]["model_sha256"], bindings_restored=True)
    edge_fields = {"oxygen_operator_xyz", "families", "bond", "live_sources_sha256"}
    fields = set(expected) | {"full_gradient_calls", "reflections"} | ({"edges"} if grouped else edge_fields)
    def digest(value):
        return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (not isinstance(row, dict) or set(row) != fields
            or any(type(row[k]) is not type(v) or row[k] != v for k, v in expected.items())
            or type(row["full_gradient_calls"]) is not int or row["full_gradient_calls"] < 1):
        raise ValueError("Incomplete native phosphate geometry or restored binding")
    measured = row["edges"] if grouped else [row]
    if not isinstance(measured, list) or len(measured) != len(inspections):
        raise ValueError("The native fit did not record every registered phosphate")
    for item, obs in zip(measured, inspections):
        if grouped and (not isinstance(item, dict) or set(item) != edge_fields | {"continuation_id"}
                or type(item["continuation_id"]) is not int
                or item["continuation_id"] != obs["registered_continuation"]["continuation_id"]):
            raise ValueError("Phosphate fit differs from its registered continuation IDs")
        if (item["oxygen_operator_xyz"] != obs["o3_image"] or not digest(item["live_sources_sha256"])
                or item["families"] != {"bond_simple": 1, "angle": 4, "dihedral": 3}
                or item["bond"] != {"bonds": 1, "second_shell_pairs": 4, "remaining_nonbonded": 0}
                or any(type(n) is not int for key in ("families", "bond") for n in item[key].values())):
            raise ValueError("Incomplete native phosphate geometry or crystal image")
    flags = row["reflections"]
    if not isinstance(flags, dict) or set(flags) != {"start", "finish", "removed_free", "removed_work"}:
        raise ValueError("Incomplete native phosphate reflection inventory")
    for state in (flags["start"], flags["finish"]):
        if (not isinstance(state, dict) or set(state) != {"work", "free", "flags_sha256", "observations_sha256"}
                or any(type(state[k]) is not int or state[k] < 0 for k in ("work", "free"))
                or state["work"] + state["free"] == 0
                or any(not digest(state[k]) for k in ("flags_sha256", "observations_sha256"))):
            raise ValueError("Malformed phosphate refinement work/free observation")
    for name in ("work", "free"):
        removed = flags["removed_"+name]
        if type(removed) is not int or removed < 0 or flags["start"][name]-flags["finish"][name] != removed:
            raise ValueError("Phosphate refinement changed the observed work/free accounting")
    if phase == "refine":
        before = read_phase(run, root, "preflight", request)
        chemistry = "edges" if grouped else "live_sources_sha256"
        if before[chemistry] != row[chemistry] or before["reflections"]["start"] != flags["start"]:
            raise ValueError("Phosphate preflight and refinement started with different chemistry or diffraction inputs")
    return row
