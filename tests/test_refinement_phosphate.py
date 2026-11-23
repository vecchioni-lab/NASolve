"""A numbered restart may carry only its registered, chemically qualified crystal bond."""
from pathlib import Path

import pytest


def test_autorefine_accepts_the_same_registered_edge_inputs_as_inspection():
    from nasolve.cli import build_parser
    from nasolve.refinement_phosphate import request_from_args
    args = build_parser().parse_args([
        "autorefine", "run_002", "--from", "manual-001",
        "--registered-continuation", "3", "--registration-checkpoint", "refine-005",
        "--registration", "registration.json", "--discovery-input", "discovery.json",
        "--backbone-continuations", "continuations.json", "--native-receipt", "native.json",
    ])
    choice = request_from_args(args)
    assert choice.registered.identifier == 3
    assert choice.registered.registration == Path("registration.json")
    assert choice.registration_checkpoint == "refine-005"
    assert choice.native_receipt == Path("native.json")


@pytest.mark.parametrize("switches", [
    ["--registered-continuation", "1"], ["--discovery-input", "d.json"],
    ["--registration-checkpoint", "refine-005"], ["--registered-continuation", "0",
     "--registration", "r", "--discovery-input", "d", "--backbone-continuations", "e",
     "--native-receipt", "n"],
])
def test_incomplete_phosphate_choice_is_refused_before_phaser_or_run_allocation(switches):
    from nasolve.cli import build_parser
    from nasolve.refinement_phosphate import request_from_args
    with pytest.raises(ValueError):
        request_from_args(build_parser().parse_args(["autorefine", *switches]))


def test_plain_round_and_an_inherited_registration_are_distinct_choices():
    from nasolve.cli import build_parser
    from nasolve.refinement_phosphate import request_from_args
    parser = build_parser()
    assert request_from_args(parser.parse_args(["autorefine"])) is None
    continuation = request_from_args(parser.parse_args(["autorefine", "--native-receipt", "new.json"]))
    assert continuation.native_receipt == Path("new.json")
    assert continuation.registered is None and continuation.registration_checkpoint is None


def test_free_set_follows_miller_indices_and_allows_a_reported_native_rejection():
    from nasolve.cif_phosphate_phase import reflection_change
    first = {(0, 1, 2): (5., 1., True), (4, 5, 6): (3., .1, False),
             (2, 3, 9): (4., .5, False)}
    final = {(2, 3, 9): (4.2, .6, False), (0, 1, 2): (5.1, 1., True)}
    result = reflection_change(first, final)
    assert (result["start"]["work"], result["finish"]["work"], result["removed_free"]) == (2, 1, 0)
    assert result == reflection_change(dict(reversed(list(first.items()))), final)
    for changed in (final | {(0, 1, 2): (5., 1., False)}, final | {(8, 8, 8): (1., 1., False)}):
        with pytest.raises(ValueError, match="work/free"):
            reflection_change(first, changed)


def test_release_only_version_requires_identical_dispatcher_and_agreeing_build(tmp_path):
    from hashlib import sha256
    from nasolve.refinement_phosphate import _same_native_capture
    exe = tmp_path/"phenix.python"
    exe.write_bytes(b"dispatcher")
    record = dict(phenix_version="2.2.1-6174", executable_sha256=sha256(exe.read_bytes()).hexdigest())
    assert _same_native_capture(record, "2.2.1", exe)
    assert _same_native_capture(record, "2.2.1-6174", exe)
    assert not _same_native_capture(record, "2.2.1-1234", exe)
    assert not _same_native_capture(record, "2.2.10", exe)
    exe.write_bytes(b"changed")
    assert not _same_native_capture(record, "2.2.1", exe)


def test_exact_restraint_capture_preserves_order_within_native_input_roles(tmp_path):
    from hashlib import sha256
    from nasolve.refinement_phosphate import bind_execution_inputs
    files = [tmp_path/name for name in ["model.pdb", "a.eff", "one.cif", "b.phil", "two.cif"]]
    for p in files:
        p.write_text(p.name)
    pins = [dict(role=role, sha256=sha256(files[i].read_bytes()).hexdigest(), size=files[i].stat().st_size)
            for role, i in [("model",0), ("dictionary",2), ("dictionary",4), ("phil",1), ("phil",3)]]
    bind_execution_inputs({"capture_inputs":pins}, files[0], files[1:])
    for order in ([1,4,3,2], [3,2,1,4], [1,2,3], [1,2,3,4,2]):
        with pytest.raises(ValueError,match="ordered"):
            bind_execution_inputs({"capture_inputs":pins}, files[0], [files[i] for i in order])


def frozen_round(tmp_path):
    from hashlib import sha256
    import sys
    from nasolve.cif_phosphate_restraints import phosphate_bond_phil
    from nasolve.refinement_parallelity import prepare_execution, V10_POLICY_ID
    from tests.test_phosphate_restraints import inspection
    original = tmp_path/"original"
    run = original/"dataset/AutoMR/run_001"
    stage = run/"AutoRefine/round_001"
    stage.mkdir(parents=True)
    names = ["data.mtz", "parent.pdb", "one.cif", "another.phil", "phase.mtz"]
    paths = [run/name for name in names] + [stage/"autorefine.params"]
    for path in paths:
        path.write_text(path.name)
    model_digest = sha256(paths[1].read_bytes()).hexdigest()
    observed = inspection()
    observed["native_reference_links"]["native_receipt_sha256"] = "b" * 64
    sources = {name:name.encode() for name in ("registration","discovery","continuations")}
    observed["model_sha256"] = model_digest
    observed["registered_continuation"].update(continuation_id=1, frame_transfer=dict(child_model_sha256=model_digest),
        sources={k+"_sha256":sha256(v).hexdigest() for k,v in sources.items()})
    capture = [dict(role=role,sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
               for role,p in zip(("model","dictionary","phil"),paths[1:4])]
    prepared = dict(ancestor="postmr", sources=sources, inspection=observed, bond=phosphate_bond_phil(observed).encode(),
                    capture_inputs=capture)
    command = ["phenix.refine", *map(str, paths), "--overwrite", "output.prefix=refined"]
    reference, dry, fit = prepare_execution(run, checkpoint="refine-001", parent="postmr", inputs=paths,
        command=command, python_executable=Path(sys.executable), macro_cycles=5, runtime_policy=V10_POLICY_ID,
        phosphate=prepared)
    return original, run, stage, paths, reference, dry, fit


def test_registered_round_retains_order_translated_operator_and_relocatable_sources(tmp_path):
    from nasolve.refinement_parallelity import read_execution_request
    original, run, stage, paths, ref, dry, fit = frozen_round(tmp_path)
    bond = stage/"parallelity_runtime/phosphate/image-bond.phil"
    assert "symmetry_operation = -x+y,-x,z+1" in bond.read_text()
    expected = [*map(str, paths[:-1]), str(bond), str(paths[-1])]
    assert fit[3:5] == ["refine", ref["sha256"]] and fit[5:5+len(expected)] == expected
    assert dry[3:5] == ["preflight", ref["sha256"]] and dry[-1] == "refinement.dry_run=True"
    moved = original.rename(tmp_path/"elsewhere")
    assert not original.exists()
    relocated = moved/run.relative_to(original)
    rec = read_execution_request(relocated, ref, checkpoint="refine-001")
    assert rec["phosphate"]["inspection"]["o3_image"] == "-x+y,-x,z+1"
    assert all(v["anchor"] == "run" for v in rec["phosphate"]["sources"].values())
    (moved/bond.relative_to(original)).write_text("changed\n")
    with pytest.raises((ValueError,RuntimeError), match="checksum|changed"):
        read_execution_request(relocated, ref, checkpoint="refine-001")


def test_checked_ancestor_rejects_a_plain_or_counted_restart_through_a_manual_edit(tmp_path):
    from nasolve.checkpoints import _file_reference
    from nasolve.campaign_records import write_record
    from nasolve.refinement_parallelity import V10_POLICY_ID, require_runtime_continuation
    root = tmp_path/"AutoRefine/round_001/parallelity_runtime"
    entry = root/"execution.json"
    write_record(entry,{"policy_id":V10_POLICY_ID})
    records = [{"id":"postmr","parent":None},
               {"id":"refine-001","parent":"postmr","outputs":{"parallelity_execution":_file_reference(entry,tmp_path)}},
               {"id":"manual-001","parent":"refine-001"}, {"id":"manual-002","parent":"postmr"}]
    tree = {"checkpoints":records}
    for checked in (False, True):
        with pytest.raises(ValueError, match="registered crystal phosphate"):
            require_runtime_continuation(tree,records[2],checked,run=tmp_path,allow_counted=True)
    require_runtime_continuation(tree,records[2],True,run=tmp_path,registered_phosphate=True)
    require_runtime_continuation(tree,records[3],False,run=tmp_path)


def test_planned_namespace_and_terminal_restraint_must_match_before_a_round_opens(tmp_path):
    from hashlib import sha256
    from nasolve.refinement_inputs import _SOURCE, _EXECUTION
    from nasolve.refinement_phosphate import bind_planned_inputs
    model, dictionary, policy = (tmp_path/name for name in ("model.pdb","ligand.cif","native.phil"))
    model.write_bytes(b"model")
    dictionary.write_bytes(b"ligand")
    policy.write_bytes(_SOURCE)
    protection = "refinement.geometry_restraints.edits {}\n"
    def pin(role, raw):
        return dict(role=role, sha256=sha256(raw).hexdigest(),size=len(raw))
    rows = [pin("model", b"model"),pin("dictionary", b"ligand"),pin("phil", _EXECUTION),
            pin("phil", protection.encode())]
    bind_planned_inputs({"capture_inputs":rows},model,[policy,dictionary],terminal_protection=protection)
    rows[2] = pin("phil", _SOURCE)
    with pytest.raises(ValueError,match="ordered"):
        bind_planned_inputs({"capture_inputs":rows},model,[policy,dictionary],terminal_protection=protection)
    assert policy.read_bytes() == _SOURCE


def test_cold_reader_rejects_missing_proxy_force_or_changed_comparison(tmp_path, monkeypatch):
    import json
    from nasolve.cif_phosphate_phase import reflection_change
    from nasolve.refinement_parallelity import read_execution_request
    from nasolve.refinement_phosphate import read_phase
    _, run, stage, _, ref, _, _ = frozen_round(tmp_path)
    folder = stage/"parallelity_runtime"
    req = read_execution_request(run, ref, checkpoint="refine-001")
    observation = req["phosphate"]["inspection"]
    a = {(0,1,2):(4.,1.,True), (3,2,1):(6.,1.,False)}
    data = dict(schema_version=1,request_sha256=ref["sha256"],parent_model_sha256=observation["model_sha256"],
        oxygen_operator_xyz=observation["o3_image"], families={"bond_simple":1,"angle":4,"dihedral":3},
        bond={"bonds":1,"second_shell_pairs":4,"remaining_nonbonded":0},live_sources_sha256="a"*64,
        full_gradient_calls=2, reflections=reflection_change(a,a), bindings_restored=True)
    for phase in ("preflight","refine"):
        (folder/phase).mkdir()
        (folder/phase/"phosphate.json").write_text(json.dumps(dict(data,phase=phase)))
    relative = folder.relative_to(run).as_posix()
    assert read_phase(run,relative,"refine",req)["reflections"]["start"]["free"] == 1
    from nasolve import refinement_parallelity, refinement_phosphate
    execution = dict(request=ref, policy_id=refinement_parallelity.V10_POLICY_ID)
    def prior_execution(root, reference, *, checkpoint, parent, usable):
        assert (root, checkpoint, parent, usable) == (run, "refine-001", "postmr", True)
        assert reference == {"source": "this round"}
        return execution
    monkeypatch.setattr(refinement_parallelity, "validate_execution", prior_execution)
    selected = dict(kind="refinement", usable=True, id="refine-001", parent="postmr",
                    outputs={"parallelity_execution": {"source": "this round"}})
    ancestor, registration, fit = refinement_phosphate.saved_refinement(run, selected)
    assert ancestor == req["phosphate"]["ancestor"]
    assert registration.registration == folder / "phosphate/registration.json"
    assert fit["starting_native_receipt_sha256"] == "b" * 64
    assert fit["request_sha256"] == ref["sha256"] and fit["full_gradient_calls"] == 2
    assert fit["native_neighbours"] == data["bond"] and fit["reflections"] == data["reflections"]
    for invalid in (None, True, 0):
        edge = req["phosphate"]["inspection"]["registered_continuation"]
        with monkeypatch.context() as patch:
            patch.setitem(edge, "continuation_id", invalid)
            with pytest.raises(ValueError, match="continuation ID"):
                refinement_phosphate._frozen_registration(run, req["phosphate"])
    execution["policy_id"] = "ordinary"
    with pytest.raises(ValueError, match="no completed registered"):
        refinement_phosphate.saved_refinement(run, selected)
    for changed in ({"families":dict(data["families"],dihedral=2)},
                    {"bond":dict(data["bond"],remaining_nonbonded=1)},
                    {"full_gradient_calls":0}, {"oxygen_operator_xyz":"-x+y,-x,z"},
                    {"live_sources_sha256":"b"*64}, {"bindings_restored":False},
                    {"bond":dict(data["bond"],bonds=True)},
                    {"reflections":dict(data["reflections"], removed_free=1)}):
        (folder/"refine/phosphate.json").write_text(json.dumps(dict(data,phase="refine") | changed))
        with pytest.raises(ValueError):
            read_phase(run,relative,"refine",req)


def test_same_bytes_on_a_sibling_are_not_an_ancestor(tmp_path):
    from nasolve.checkpoints import _file_reference
    from nasolve.refinement_phosphate import _original
    p = tmp_path/"model.pdb"
    p.write_text("MODEL")
    ref = _file_reference(p,tmp_path)
    rows = [dict(id="postmr",parent=None,model=ref),
            dict(id="manual-001",parent="postmr",model=ref),
            dict(id="manual-002",parent="postmr",model=ref)]
    registry = dict(checkpoints=rows, current="manual-002",bookmarks={})
    assert _original(tmp_path,registry,rows[1],"postmr") == (rows[0],p)
    with pytest.raises(ValueError, match="different checkpoint branch"):
        _original(tmp_path,registry,rows[1],"manual-002")

