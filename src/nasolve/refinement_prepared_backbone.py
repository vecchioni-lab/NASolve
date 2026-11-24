"""Carry a verified Coot/ReadySet preparation into an unselected numbered refinement."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from .campaign_records import path_in, read_record, write_record
from .checkpoints import _file_reference, _required_observations, _sha256
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _json
from .cif_model_context import _intent
from .cif_prepared_backbone import review_prepared_backbone
from .refinement_inputs import _bound_path, _directory, refinement_input_bytes
from .refinement_phosphate import _inspections

POLICY_ID = "numbered-prepared-backbone-v1"


@dataclass(frozen=True)
class PreparedBackbone:
    evidence: dict
    supplements: tuple[bytes, ...]


def supplemental_inputs(directory, rows, model, inherited):
    """Existing model, dictionaries and ordered PHIL prefix must all match the capture."""
    def pin(role, data):
        return role, sha256(data).hexdigest(), len(data)

    dictionaries, phils = [], []
    for path in inherited:
        role = "dictionary" if path.suffix.casefold() == ".cif" else "phil"
        ordered = dictionaries if role == "dictionary" else phils
        ordered.append(pin(role, refinement_input_bytes(_read(path))))
    expected = [pin("model", _read(model)), *dictionaries, *phils]
    actual = [(r["role"], r["sha256"], r["size"]) for r in rows]
    remaining = rows[len(expected):]
    _need(expected == actual[:len(expected)] and all(r["role"] == "phil" for r in remaining),
          "The inherited model, dictionaries or ordered restraints differ from the native capture")
    supplements = []
    for row in remaining:
        _need(row["anchor"] == "native_directory", "Supplemental restraint needs a native capture anchor")
        data = _read(path_in(directory, row["path"]))
        _need(pin("phil", data) == ("phil", row["sha256"], row["size"]), "Captured supplemental restraint changed")
        # A relative include or a variable could be resolved differently inside the new numbered round.
        _need(not re.search(rb"(?:^|[;{}\n])\s*include\s", data) and b"$" not in data,
              "Supplemental restraint must be self-contained")
        supplements.append(data)
    return tuple(supplements)


def terminal_input_index(supplements, generated_text):
    matches = [i for i, raw in enumerate(supplements) if raw == generated_text.encode()]
    _need(len(matches) == 1, "Require one captured copy of the independently generated terminal-phosphate protection")
    return matches[0]


def _request_identity(intent):
    rows = _inspections(intent)
    first = rows[0]
    reg = first["registered_continuation"]
    return dict(ancestor=intent["ancestor"], coot_model_sha256=reg["frame_transfer"]["source_model_sha256"],
                candidate_model_sha256=first["model_sha256"], native_receipt_sha256=first["native_reference_links"]["native_receipt_sha256"],
                registration_sha256=reg["sources"]["registration_sha256"], graph_sha256=reg["registered_graph_sha256"],
                continuation_ids=[r["registered_continuation"]["continuation_id"] for r in rows])


def prepare_trial(source_run, receiving_report, parent, inherited, choice, intent):
    """Compare both actual run contexts before allocating an immutable round."""
    source_run = Path(source_run).expanduser().resolve()
    original = _read(source_run / "report.json")
    source = _json(original)
    _need(receiving_report.get("workflow") == "automr" and _intent(source) == _intent(receiving_report),
          "Receiving run has different frozen backbone or terminal intent")
    observed = _sha256(inherited["observations"])
    _need(observed == parent["observations"]["sha256"] == receiving_report["inputs"].get("reflections_sha256")
          == source["inputs"].get("reflections_sha256") == _sha256(_required_observations(source, source_run)),
          "Prepared and receiving runs must have the same original observations and Free-R flags")
    registered = choice.registered
    proof = review_prepared_backbone(source_run, registration=registered.registration, discovery=registered.discovery,
        continuations=registered.continuations, candidate_model=inherited["model"], native_receipt=choice.native_receipt)
    candidate = proof["native_candidate"]
    identity = _request_identity(intent)
    if "postmr_construction_sha256" in intent:
        _need(intent["postmr_construction_sha256"] == proof["construction_sha256"],
              "The numbered trial belongs to a different PostMR construction")
    _need(proof["prepared_model"]["sha256"] == identity["coot_model_sha256"]
          and candidate["candidate_model_sha256"] == identity["candidate_model_sha256"]
          and candidate["native_receipt_sha256"] == identity["native_receipt_sha256"]
          and proof["registration"]["registration_sha256"] == identity["registration_sha256"]
          and proof["registration"]["graph_sha256"] == identity["graph_sha256"]
          and sorted(r["id"] for r in candidate["registered_continuations"]) == identity["continuation_ids"],
          "The numbered trial requires the same Coot construction, candidate and complete crystal registration")
    rows = candidate["native_inputs"]
    _need([{k: r[k] for k in ("role", "size", "sha256")} for r in rows] == intent["capture_inputs"],
          "Native inputs changed between preparation and refinement review")
    supplements = supplemental_inputs(Path(choice.native_receipt).parent, rows, inherited["model"], inherited["restraints"])
    _need(_read(source_run / "report.json") == original, "Source preparation changed during review")
    evidence = dict(schema_version=1, policy_id=POLICY_ID, construction_sha256=proof["construction_sha256"],
                    observations_sha256=observed, protected_terminal_sites=proof["protected_terminal_phosphates"], **identity)
    return PreparedBackbone(evidence, supplements)


def write_trial(run, checkpoint, parent, trial):
    directory = path_in(run, _directory(checkpoint) + "/prepared_backbone")
    directory.mkdir()
    paths = []
    for index, raw in enumerate(trial.supplements):
        path = directory / f"{index:03d}.phil"
        with path.open("xb") as handle:
            handle.write(raw)
        paths.append(path)
    proof = directory / "source.json"
    write_record(proof, dict(trial.evidence, checkpoint=checkpoint, parent=parent,
                             supplemental_phils=[_file_reference(p, run) for p in paths]))
    return paths, _file_reference(proof, run)


def validate_trial(run, reference, item, parent, intent):
    """Cold read needs only the numbered run and its normal declared anchors."""
    directory = _directory(item["id"]) + "/prepared_backbone/"
    _need(isinstance(reference, dict) and reference.get("anchor") == "run" and reference.get("relative_path") == directory + "source.json",
          "Prepared backbone record belongs to a different numbered round")
    proof = read_record(_bound_path(reference, "prepared backbone source", run))
    identity = _request_identity(intent)
    if "postmr_construction_sha256" in intent:
        _need(intent["postmr_construction_sha256"] == proof.get("construction_sha256"),
              "The numbered preparation differs from its recorded PostMR construction")
    _need(proof.get("schema_version") == 1 and proof.get("policy_id") == POLICY_ID
          and proof.get("checkpoint") == item["id"] and proof.get("parent") == parent["id"]
          and proof.get("observations_sha256") == item["observations"]["sha256"]
          and proof.get("candidate_model_sha256") == parent["model"]["sha256"]
          and all(proof.get(k) == value for k, value in identity.items())
          and isinstance(proof.get("construction_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", proof["construction_sha256"]),
          "Prepared backbone evidence differs from the numbered inputs")
    terminal = item.get("terminal_geometry_protection") or {}
    _need(proof.get("protected_terminal_sites") == sorted(terminal.get("sites", ())),
          "Prepared backbone protected terminal sites differ from the checkpoint")
    supplements = proof.get("supplemental_phils")
    _need(isinstance(supplements, list) and item["restraints"] == [*parent["restraints"], *supplements],
          "Prepared backbone supplements differ from the checkpoint restraints")
    for index, ref in enumerate(supplements):
        _need(isinstance(ref, dict) and ref.get("anchor") == "run" and ref.get("relative_path") == directory + f"{index:03d}.phil",
              "Prepared backbone supplemental restraint belongs to a different numbered round")
        _bound_path(ref, "prepared backbone supplemental restraint", run)
    return proof
