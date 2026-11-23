"""Bind one declared crystal phosphodiester to an ordinary numbered refinement round."""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from .campaign_records import path_in, read_record
from .checkpoint_candidate import _lineage
from .checkpoints import _file_reference, _ref_path, resolve_checkpoint
from .cif_dictionary_sites import _bind_capture_inputs, _bind_capture_input_pins
from .cif_phosphate_continuation import RegisteredContinuation, inspect_inherited_continuation
from .cif_phosphate_restraints import phosphate_bond_phil
from .refinement_inputs import _bound_path

_SOURCE_NAMES = ("registration", "discovery", "continuations")


@dataclass(frozen=True)
class PhosphateRequest:
    native_receipt: Path
    registered: RegisteredContinuation | None = None
    registration_checkpoint: str | None = None


def request_from_args(args):
    paths = (args.registration, args.discovery_input, args.backbone_continuations)
    if args.registered_continuation is None:
        if args.registration_checkpoint is not None or any(p is not None for p in paths):
            raise ValueError("Registering a phosphate requires --registered-continuation with all three topology files")
        return PhosphateRequest(args.native_receipt) if args.native_receipt is not None else None
    if args.registered_continuation < 1 or any(p is None for p in paths) or args.native_receipt is None:
        raise ValueError("A positive continuation ID, registration, discovery input, backbone continuations and native receipt are required")
    return PhosphateRequest(args.native_receipt, RegisteredContinuation(args.registered_continuation, *paths),
                            args.registration_checkpoint)


def _prior_intent(run, registry, parent):
    from .refinement_parallelity import V10_POLICY_ID
    by_id = {row["id"]: row for row in registry["checkpoints"]}
    for key in reversed(_lineage(registry, parent)):
        ref = (by_id[key].get("outputs") or {}).get("parallelity_execution")
        if ref is not None:
            sealed = read_record(_bound_path(ref, "ancestor execution", run))
            if sealed["policy_id"] == V10_POLICY_ID:
                request = read_record(_bound_path(sealed["request"], "ancestor request", run))
                return request["phosphate"]
    return None


def _identity(ancestor, edge):
    return (ancestor, edge["continuation_id"], edge["sources"], edge["registered_graph_sha256"],
            edge["source"], edge["target"], edge["oxygen_operator_xyz"])


def _frozen_registration(run, intent):
    identifier = intent["inspection"]["registered_continuation"].get("continuation_id")
    if type(identifier) is not int or identifier < 1:
        raise ValueError("The saved phosphate has no valid continuation ID")
    paths = (_bound_path(intent["sources"][name], "frozen phosphate " + name, run) for name in _SOURCE_NAMES)
    return RegisteredContinuation(identifier, *paths)


def _original(run, registry, parent, checkpoint):
    ancestor = resolve_checkpoint(registry, checkpoint)
    if ancestor["id"] not in _lineage(registry, parent):
        raise ValueError("Phosphate registration belongs to a different checkpoint branch")
    if ancestor["model"].get("anchor") not in ("run", "dataset", "repository"):
        raise ValueError("The original phosphate registration needs a portable checkpoint model")
    return ancestor, _bound_path(ancestor["model"], "original phosphate registration model", run)


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
        if prior is None:
            raise ValueError("This branch has no registered phosphate to continue")
        checkpoint = prior["ancestor"]
        registered = _frozen_registration(run, prior)
    else:
        checkpoint = choice.registration_checkpoint or parent["id"]
    ancestor, source = _original(run, registry, parent, checkpoint)
    model = _bound_path(parent["model"], "phosphate starting model", run)
    inspection = inspect_inherited_continuation(source, model, registered, native_receipt=choice.native_receipt)
    edge = inspection["registered_continuation"]
    if edge["frame_transfer"]["source_model_sha256"] != ancestor["model"]["sha256"]:
        raise ValueError("Phosphate registration differs from its original checkpoint")
    if prior is not None and _identity(ancestor["id"], edge) != _identity(
            prior["ancestor"], prior["inspection"]["registered_continuation"]):
        raise ValueError("Changing an inherited phosphate registration requires a different starting branch")
    proof = inspection["native_reference_links"]
    receipt_raw = Path(choice.native_receipt).read_bytes()
    receipt = json.loads(receipt_raw)
    if sha256(receipt_raw).hexdigest() != proof["native_receipt_sha256"] or not _same_native_capture(
            receipt, phenix_version, python_executable):
        raise ValueError("The phosphate capture or its Phenix version differs from this refinement")
    capture_inputs = [{k: row[k] for k in ("role", "sha256", "size")} for row in receipt["inputs"]]
    bond = phosphate_bond_phil(inspection).encode()
    sources = {name: Path(getattr(registered, name)).read_bytes() for name in _SOURCE_NAMES}
    if not all(sha256(raw).hexdigest() == edge["sources"][name+"_sha256"] for name, raw in sources.items()):
        raise ValueError("A phosphate topology input changed after inspection")
    return dict(ancestor=ancestor["id"], inspection=inspection, sources=sources, bond=bond,
                capture_inputs=capture_inputs)


def bind_execution_inputs(prepared, model, restraints):
    _bind_capture_inputs({"inputs": prepared["capture_inputs"]}, model,
                         [p for p in restraints if p.suffix.casefold() == ".cif"],
                         [p for p in restraints if p.suffix.casefold() != ".cif"])


def bind_planned_inputs(prepared, model, restraints, *, terminal_protection=None):
    """Reject a mismatched capture before allocating an immutable round."""
    from .refinement_inputs import refinement_input_bytes
    def pin(role, raw):
        return role, sha256(raw).hexdigest(), len(raw)
    pins = [pin("model", model.read_bytes())]
    dictionaries, phils = [], []
    for path in restraints:
        role = "dictionary" if path.suffix.casefold() == ".cif" else "phil"
        (dictionaries if role == "dictionary" else phils).append(pin(role, refinement_input_bytes(path.read_bytes())))
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
    return dict(ancestor=prepared["ancestor"], inspection=prepared["inspection"], sources=refs,
                capture_inputs=prepared["capture_inputs"], bond=_file_reference(bond, run))


def read_intent(run, root, request):
    """Verify the small frozen declaration and the one execution-only bond."""
    try:
        return _read_intent(run, root, request)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("Malformed registered phosphate request") from exc


def _read_intent(run, root, request):
    intent = request.get("phosphate")
    if not isinstance(intent, dict) or set(intent) != {"ancestor", "inspection", "sources", "bond", "capture_inputs"}:
        raise ValueError("Missing registered phosphate intent")
    observation = intent["inspection"]
    edge = observation["registered_continuation"]
    if (not isinstance(intent["ancestor"], str) or not intent["ancestor"] or set(intent["sources"]) != set(_SOURCE_NAMES)
            or len(request["inputs"]) < 4 or observation["model_sha256"] != request["inputs"][1]["sha256"]
            or any(row.get("anchor") not in ("run", "dataset", "repository") for row in request["inputs"])
            or edge["frame_transfer"]["child_model_sha256"] != observation["model_sha256"]):
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
            or path_in(run, relative).read_bytes() != phosphate_bond_phil(observation).encode()):
        raise ValueError("A single crystal bond with its exact operator is required")
    capture = intent["capture_inputs"]
    if not isinstance(capture, list) or not capture or len(inputs) - len(capture) not in (3, 4):
        raise ValueError("Phosphate capture does not cover the ordered model and restraints")
    model, *restraints = inputs[1:1+len(capture)]
    rows = [("dictionary" if Path(p["relative_path"]).suffix.casefold() == ".cif" else "phil", p)
            for p in restraints]
    ordered = [("model", model), *sorted(rows, key=lambda row: row[0] != "dictionary")]
    _bind_capture_input_pins({"inputs":capture}, [(role, p["sha256"], p["size"]) for role, p in ordered])
    return intent


def validate_lineage(run, registry, parent, intent):
    """Cold replay binds the original topology and current coordinate frame without Phenix."""
    ancestor, source = _original(run, registry, parent, intent["ancestor"])
    recorded = intent["inspection"]
    edge = recorded["registered_continuation"]
    registered = _frozen_registration(run, intent)
    actual = inspect_inherited_continuation(source, _ref_path(parent["model"], "phosphate model", run), registered)
    if actual != {key: value for key, value in recorded.items() if key != "native_reference_links"}:
        raise ValueError("The registered phosphate observation differs from the original or selected parent")
    prior = _prior_intent(run, registry, parent)
    if prior is not None and _identity(ancestor["id"], edge) != _identity(
            prior["ancestor"], prior["inspection"]["registered_continuation"]):
        raise ValueError("Numbered child changed its inherited phosphate")


def saved_refinement(run, checkpoint):
    """Read the restraint evidence from this completed checkpoint's own fit."""
    from .refinement_parallelity import V10_POLICY_ID, read_execution_request, validate_execution

    reference = (checkpoint.get("outputs") or {}).get("parallelity_execution")
    missing = "The named checkpoint has no completed registered phosphate refinement"
    if checkpoint.get("kind") != "refinement" or checkpoint.get("usable") is not True or reference is None:
        raise ValueError(missing)
    record = validate_execution(run, reference, checkpoint=checkpoint["id"], parent=checkpoint["parent"], usable=True)
    if record["policy_id"] != V10_POLICY_ID:
        raise ValueError(missing)
    request = read_execution_request(run, record["request"], checkpoint=checkpoint["id"])
    intent = request["phosphate"]
    root = Path(record["request"]["relative_path"]).parent.as_posix()
    phase = read_phase(run, root, "refine", request)
    capture = intent["inspection"]["native_reference_links"].get("native_receipt_sha256")
    if not isinstance(capture, str) or not re.fullmatch("[0-9a-f]{64}", capture):
        raise ValueError("The starting-model native chemistry receipt has no valid fingerprint")
    evidence = {
        "parent": request["parent"],
        "starting_model_sha256": phase["parent_model_sha256"],
        "starting_native_receipt_sha256": capture,
        "request_sha256": record["request"]["sha256"],
        "native_forces": phase["families"],
        "native_neighbours": phase["bond"],
        "full_gradient_calls": phase["full_gradient_calls"],
        "reflections": phase["reflections"],
    }
    return intent["ancestor"], _frozen_registration(run, intent), evidence


def read_phase(run, root, phase, request):
    """Read checked phosphate and free-set observations without invoking native code."""
    directory = path_in(run, root)
    row = json.loads(path_in(directory, phase+"/phosphate.json").read_bytes())
    inspection = request["phosphate"]["inspection"]
    expected = dict(schema_version=1, phase=phase, request_sha256=sha256((directory/"request.json").read_bytes()).hexdigest(),
                    parent_model_sha256=inspection["model_sha256"], oxygen_operator_xyz=inspection["o3_image"],
                    families={"bond_simple": 1, "angle": 4, "dihedral": 3},
                    bond={"bonds": 1, "second_shell_pairs": 4, "remaining_nonbonded": 0}, bindings_restored=True)
    def digest(value):
        return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (not isinstance(row, dict) or set(row) != set(expected) | {"live_sources_sha256", "full_gradient_calls", "reflections"}
            or any(type(row[k]) is not type(v) or row[k] != v for k, v in expected.items())
            or type(row["full_gradient_calls"]) is not int or row["full_gradient_calls"] < 1
            or not digest(row["live_sources_sha256"])):
        raise ValueError("Incomplete native phosphate geometry or restored binding")
    if any(type(n) is not int for key in ("families", "bond") for n in row[key].values()):
        raise ValueError("Native phosphate proxy counts must be integers")
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
        if before["live_sources_sha256"] != row["live_sources_sha256"] or before["reflections"]["start"] != flags["start"]:
            raise ValueError("Phosphate preflight and refinement started with different chemistry or diffraction inputs")
    return row
