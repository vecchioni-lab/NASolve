"""Ordinary refinement may fill only the missing end of a verified geometry input list."""
from hashlib import sha256
from pathlib import Path

import pytest

from nasolve.cli import build_parser
from nasolve.refinement_phosphate import request_from_args


def captured(tmp_path, restraints):
    result = []
    for index, (role, suffix, raw) in enumerate(restraints):
        relative = f"{index:03d}{suffix}"
        (tmp_path / relative).write_bytes(raw)
        result.append(dict(role=role, path=relative, anchor="native_directory",
                           sha256=sha256(raw).hexdigest(), size=len(raw)))
    return result


def test_append_only_the_ordered_restraint_suffix(tmp_path):
    from nasolve.refinement_prepared_backbone import supplemental_inputs
    from nasolve.cif_native_monomers import FULL_MODEL_PHIL
    from nasolve.refinement_inputs import refinement_input_bytes

    capture = tmp_path / "capture"
    capture.mkdir()
    parent_phil = tmp_path / "root.phil"
    parent_phil.write_text(FULL_MODEL_PHIL)
    rows = captured(capture, [("model", ".pdb", b"model"), ("dictionary", ".cif", b"chemistry"),
                              ("phil", ".phil", refinement_input_bytes(parent_phil.read_bytes())),
                              ("phil", ".phil", b"angle\n"), ("phil", ".phil", b"another restraint\n")])
    model, dictionary = [capture / r["path"] for r in rows[:2]]
    inherited = [parent_phil, dictionary]
    assert supplemental_inputs(capture, rows, model, inherited) == (b"angle\n", b"another restraint\n")
    assert supplemental_inputs(capture, rows, model, [*inherited, capture/rows[-2]["path"], capture/rows[-1]["path"]]) == ()
    for paths in ([parent_phil], [*inherited, dictionary], [*inherited, capture/rows[-1]["path"]]):
        with pytest.raises(ValueError, match="inherited"):
            supplemental_inputs(capture, rows, model, paths)
    (capture / rows[-1]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        supplemental_inputs(capture, rows, model, inherited)


@pytest.mark.parametrize("value", [b"include file ../geometry.phil\n", b"include scope sample.master\n",
                                  b"refinement.geometry_restraints.edits {\n  include file other\n}\n"])
def test_cannot_import_an_uncaptured_include(tmp_path, value):
    from nasolve.refinement_prepared_backbone import supplemental_inputs
    rows = captured(tmp_path, [("model", ".pdb", b"model"), ("phil", ".phil", value)])
    with pytest.raises(ValueError, match="self-contained"):
        supplemental_inputs(tmp_path, rows, tmp_path / rows[0]["path"], [])


def test_terminal_seed_has_one_exact_owner_in_the_supplements():
    from nasolve.refinement_prepared_backbone import terminal_input_index
    assert terminal_input_index((b"A", b"D1", b"B"), "D1") == 1
    for raws in ((b"A",), (b"D1", b"D1")):
        with pytest.raises(ValueError, match="one"):
            terminal_input_index(raws, "D1")


def test_source_review_requires_explicit_parent_ancestor_and_all_topology():
    def args(*more):
        return build_parser().parse_args(["autorefine", "run", "--prepared-backbone-source", "old", *more])
    named = ["--from", "manual-002", "--registration-checkpoint", "manual-001", "--registered-continuations", "7", "4",
             "--registration", "r", "--discovery-input", "d", "--backbone-continuations", "e", "--native-receipt", "n"]
    assert request_from_args(args(*named)).prepared_backbone_source == Path("old")
    for missing in ([*named[2:]], [*named[:2], *named[4:]], ["--from", "manual-002", "--native-receipt", "n"]):
        with pytest.raises(ValueError, match="prepared backbone"):
            request_from_args(args(*missing))


@pytest.mark.parametrize("mismatch", [None, "original data", "recorded observations", "terminal", "source model", "missing junction", "capture"])
def test_cannot_transfer_scientific_intent_from_a_different_source(tmp_path, monkeypatch, mismatch):
    import json
    from copy import deepcopy
    from nasolve.cif_phosphate_continuation import RegisteredContinuation
    from nasolve.refinement_phosphate import PhosphateRequest
    from nasolve.refinement_prepared_backbone import prepare_trial
    from .test_cif_model_context import report

    source = tmp_path / "run"; source.mkdir()
    original = source / "input.mtz"; original.write_bytes(b"work and free")
    observations = tmp_path / "child.mtz"; observations.write_bytes(original.read_bytes())
    obs_pin = sha256(observations.read_bytes()).hexdigest()
    saved = dict(workflow="automr", inputs=dict(reflections=str(original), reflections_sha256=obs_pin), **report("D:1"))
    receiving = deepcopy(saved)
    capture = tmp_path / "capture"; capture.mkdir()
    rows = captured(capture, [("model", ".pdb", b"selected candidate"), ("phil", ".phil", b"edited bond")])
    model = capture / rows[0]["path"]
    digest = lambda tag: sha256(tag.encode()).hexdigest()
    coot, native, registration, graph = map(digest, ("coot", "native", "registration", "graph"))
    candidate = dict(candidate_model_sha256=rows[0]["sha256"], native_receipt_sha256=native, native_inputs=rows,
                     registered_continuations=[dict(id=4), dict(id=7)])
    review = dict(native_candidate=candidate, prepared_model=dict(sha256=coot), construction_sha256=digest("construction"),
                  protected_terminal_phosphates=["D:1"], registration=dict(registration_sha256=registration, graph_sha256=graph))
    monkeypatch.setattr("nasolve.refinement_prepared_backbone.review_prepared_backbone", lambda *a, **kw: review)
    ins = [dict(model_sha256=rows[0]["sha256"], native_reference_links=dict(native_receipt_sha256=native),
                registered_continuation=dict(continuation_id=i, registered_graph_sha256=graph,
                    sources=dict(registration_sha256=registration), frame_transfer=dict(source_model_sha256=coot))) for i in (4, 7)]
    pins = [{k: r[k] for k in ("role", "size", "sha256")} for r in rows]
    intent = dict(ancestor="manual-001", inspections=ins, capture_inputs=pins)
    choice = PhosphateRequest(capture/"receipt.json", RegisteredContinuation(4, source/"r", source/"d", source/"e"),
                              "manual-001", (7,), source)
    parent = dict(observations=dict(sha256=obs_pin))
    if mismatch == "original data": original.write_bytes(b"flipped flags")
    if mismatch == "recorded observations": parent["observations"]["sha256"] = digest("foreign")
    if mismatch == "terminal": receiving.update(report("A:1"))
    if mismatch == "source model": review["prepared_model"]["sha256"] = digest("other Coot")
    if mismatch == "missing junction": intent["inspections"] = ins[:1]
    if mismatch == "capture": pins[-1]["size"] += 1
    (source / "report.json").write_text(json.dumps(saved))
    def plan():
        return prepare_trial(source, receiving, parent, dict(model=model, observations=observations, restraints=[]), choice, intent)
    if mismatch:
        with pytest.raises(ValueError): plan()
    else:
        trial = plan()
        assert trial.evidence["continuation_ids"] == [4, 7] and trial.supplements == (b"edited bond",)
    assert not (source / "AutoRefine").exists()


def test_numbered_receipt_reopens_after_moving_and_rejects_a_different_ancestor(tmp_path):
    from nasolve.campaign_records import read_record, write_record
    from nasolve.checkpoints import _file_reference
    from nasolve.refinement_prepared_backbone import PreparedBackbone, POLICY_ID, validate_trial, write_trial

    root = tmp_path / "run"; (root / "AutoRefine/round_001").mkdir(parents=True)
    digest = lambda value: sha256(value.encode()).hexdigest()
    coot, model, receipt, registration, graph, data = map(digest, ("coot", "model", "capture", "registration", "graph", "data"))
    intent = dict(ancestor="manual-001", inspection=dict(model_sha256=model,
        native_reference_links=dict(native_receipt_sha256=receipt), registered_continuation=dict(continuation_id=7,
            frame_transfer=dict(source_model_sha256=coot), sources=dict(registration_sha256=registration), registered_graph_sha256=graph)))
    evidence = dict(schema_version=1, policy_id=POLICY_ID, candidate_model_sha256=model, native_receipt_sha256=receipt,
        coot_model_sha256=coot, registration_sha256=registration, graph_sha256=graph, observations_sha256=data,
        continuation_ids=[7], ancestor="manual-001", protected_terminal_sites=[], construction_sha256=digest("construction"))
    parent = dict(id="manual-002", observations=dict(sha256=data), model=dict(sha256=model), restraints=[])
    paths, ref = write_trial(root, "refine-001", parent["id"], PreparedBackbone(evidence, (b"captured restraint",)))
    item = dict(id="refine-001", parent=parent["id"], observations=parent["observations"],
                restraints=[_file_reference(p, root) for p in paths])
    moved = root.rename(tmp_path / "relocated")
    proof = validate_trial(moved, ref, item, parent, intent)
    assert proof["supplemental_phils"] == item["restraints"]
    path = moved / ref["relative_path"]
    write_record(path, dict(read_record(path), ancestor="other"), replace=True)
    with pytest.raises(ValueError, match="numbered inputs"):
        validate_trial(moved, _file_reference(path, moved), item, parent, intent)
    from nasolve.refinement_parallelity import validate_checkpoint_execution
    with pytest.raises(ValueError, match="preparation record"):
        validate_checkpoint_execution(moved, dict(item, kind="refinement", outputs={}), {})
