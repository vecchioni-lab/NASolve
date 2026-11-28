"""A numbered restart may carry only its registered, chemically qualified crystal bond."""
from pathlib import Path

import pytest


@pytest.mark.parametrize("version", (10, 11, 12))
def test_registered_phosphate_worker_keeps_its_original_base_restraint_reader(version):
    from hashlib import sha256
    from nasolve import refinement_parallelity as runtime

    policy = getattr(runtime, f"V{version}_POLICY_ID")
    worker = runtime._code(policy)
    name = "code/_nasolve_refinement/cif_explicit_na_policy.py"
    assert sha256(worker[name]).hexdigest() == "b01612596352d24886eb4d3bd257b7246004623f3d794253ed029129b736f6c5"
    assert {n:sha256(data).hexdigest() for n,data in worker.items()} == runtime._expected_code(policy)


def test_registered_phosphate_replay_uses_physical_precision_only_for_coordinate_angles():
    from copy import deepcopy
    from math import inf, nan
    from nasolve.refinement_phosphate import _same_observation

    name = "O3'-P-OP2"
    saved = {"coordinate_angles_degrees": {"C3'-O3'-P": None, "O3'-P-OP1": 110.0,
                                          name: 108.74217535393782, "O3'-P-O5'": 109.0},
             "o3_image": "-x+y,-x,z", "o3": ["B:7", "DA", "O3'"], "model_sha256": "a" * 64,
             "distance_A": 1.6123456789, "registered_continuation": {"continuation_id": 1}}
    rebuilt = deepcopy(saved)
    # The same numbered PDU file gave these two values in Python 3.11 and 3.12.
    rebuilt["coordinate_angles_degrees"][name] = 108.74217535393781
    assert _same_observation(rebuilt, saved)
    # Straddle a decimal rounding boundary. Half a unit in the seventh figure
    # at this angle is 0.00005 degrees, independently of the rounding grid.
    rebuilt["coordinate_angles_degrees"][name] = 108.74214
    assert _same_observation(rebuilt, saved)
    for value in (108.74211, 108.75, None, True, "108.7422", nan, inf, -1.0, 181.0):
        bad = deepcopy(rebuilt)
        bad["coordinate_angles_degrees"][name] = value
        assert not _same_observation(bad, saved)
    for key, value in (("o3_image", "x,y,z"), ("o3", ["B:6", "DA", "O3'"]),
                       ("model_sha256", "b" * 64), ("distance_A", 1.6123456789000001),
                       ("registered_continuation", {"continuation_id": True})):
        assert not _same_observation(dict(rebuilt, **{key: value}), saved)
    angles = rebuilt["coordinate_angles_degrees"]
    for altered in (dict(angles, **{"C3'-O3'-P": 0.0}), dict(angles, unrelated=1.0),
                    {key: val for key, val in angles.items() if key != "O3'-P-OP1"}):
        assert not _same_observation(dict(rebuilt, coordinate_angles_degrees=altered), saved)
    assert _same_observation({"coordinate_angles_degrees": None}, {"coordinate_angles_degrees": None})
    assert not _same_observation({}, {"coordinate_angles_degrees": None})


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


@pytest.mark.parametrize("command", [("autorefine", "run_002"), ("cif-doctor", "phosphate-image", "model.pdb")])
def test_one_phosphate_request_cannot_silently_drop_another_registered_edge(command, capsys):
    from nasolve.cli import build_parser
    parser = build_parser()
    first = [*command, "--registered-continuation", "1"]
    assert parser.parse_args([*first, "--registered-continuation=1"]).registered_continuation == 1
    with pytest.raises(SystemExit) as exc:
        parser.parse_args([*first, "--registered-continuation=2"])
    assert exc.value.code == 2
    assert "continuation IDs 1 and 2" in capsys.readouterr().err


def test_plain_round_and_an_inherited_registration_are_distinct_choices():
    from nasolve.cli import build_parser
    from nasolve.refinement_phosphate import request_from_args
    parser = build_parser()
    assert request_from_args(parser.parse_args(["autorefine"])) is None
    continuation = request_from_args(parser.parse_args(["autorefine", "--native-receipt", "new.json"]))
    assert continuation.native_receipt == Path("new.json")
    assert continuation.registered is None and continuation.registration_checkpoint is None


def test_multiple_registered_phosphates_are_an_explicit_complete_set():
    from nasolve.cli import build_parser
    from nasolve.refinement_phosphate import request_from_args

    parser = build_parser()
    base = ["autorefine", "--registration", "r", "--discovery-input", "d",
            "--backbone-continuations", "edges", "--native-receipt", "capture"]
    choice = request_from_args(parser.parse_args([*base, "--registered-continuations", "4", "2"]))
    assert choice.registered.identifier == 2 and choice.additional_ids == (4,)
    for values in (["4"], ["4", "2", "4"], ["1", "0"], ["-1", "2"]):
        with pytest.raises(ValueError):
            request_from_args(parser.parse_args([*base, "--registered-continuations", *values]))
    with pytest.raises(SystemExit):
        parser.parse_args([*base, "--registered-continuation", "1", "--registered-continuations", "2", "3"])


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


def frozen_round(tmp_path, policy=None, *, group=False):
    from hashlib import sha256
    import sys
    from nasolve.cif_phosphate_restraints import phosphate_bond_phil
    from nasolve.refinement_parallelity import prepare_execution, V11_POLICY_ID
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
    if group:
        from copy import deepcopy
        edge = observed["registered_continuation"]
        edge.update(copy_id="as-built", registered_graph_sha256="d"*64)
        edge["frame_transfer"]["source_model_sha256"] = model_digest
        second = deepcopy(observed)
        edge = second["registered_continuation"]
        edge["continuation_id"] = 4
        second["o3"][0] = edge["source"]["coordinate_site"] = "M:3"
        second["phosphate"][0] = edge["target"]["coordinate_site"] = "N:2"
        second["o3_image"] = edge["oxygen_operator_xyz"] = "-y,x-y,z"
        prepared["inspections"] = [prepared.pop("inspection"), second]
        prepared["bond"] += phosphate_bond_phil(second).encode()
    command = ["phenix.refine", *map(str, paths), "--overwrite", "output.prefix=refined"]
    reference, dry, fit = prepare_execution(run, checkpoint="refine-001", parent="postmr", inputs=paths,
        command=command, python_executable=Path(sys.executable), macro_cycles=5, runtime_policy=policy or V11_POLICY_ID,
        phosphate=prepared)
    return original, run, stage, paths, reference, dry, fit


def test_numbered_set_preserves_each_image_and_rejects_truncated_or_reordered_evidence(tmp_path):
    from copy import deepcopy
    from nasolve.refinement_parallelity import V12_POLICY_ID, read_execution_request
    from nasolve.refinement_phosphate import read_intent

    original, run, stage, _, ref, dry, fit = frozen_round(tmp_path, V12_POLICY_ID, group=True)
    folder = stage / "parallelity_runtime"
    bond = folder / "phosphate/image-bond.phil"
    assert fit.count(str(bond)) == dry.count(str(bond)) == 1
    assert bond.read_text().count("symmetry_operation = ") == 2
    copied = original.rename(tmp_path / "relocated")
    run, root = copied / run.relative_to(original), folder.relative_to(run).as_posix()
    checked = read_execution_request(run, ref, checkpoint="refine-001")
    assert [i["o3_image"] for i in checked["phosphate"]["inspections"]] == ["-x+y,-x,z+1", "-y,x-y,z"]
    for change in ("drop", "reverse", "repeat", "operator", "capture", "legacy-policy"):
        bad = deepcopy(checked)
        rows = bad["phosphate"]["inspections"]
        if change == "drop":
            rows.pop()
        elif change == "reverse":
            rows.reverse()
        elif change == "repeat":
            rows[1] = rows[0]
        elif change == "operator":
            rows[1]["o3_image"] = rows[0]["o3_image"]
        elif change == "capture":
            rows[1]["native_reference_links"]["native_receipt_sha256"] = "a"*64
        else:
            from nasolve.refinement_parallelity import V11_POLICY_ID
            bad["policy_id"] = V11_POLICY_ID
        with pytest.raises(ValueError):
            read_intent(run, root, bad)


def test_saved_fit_requires_the_named_member_and_simultaneous_gradients(tmp_path, monkeypatch):
    import json
    from copy import deepcopy
    from nasolve import refinement_parallelity as runtime
    from nasolve.cif_phosphate_phase import reflection_change
    from nasolve.refinement_phosphate import read_phase, saved_refinement

    _, run, stage, _, ref, _, _ = frozen_round(tmp_path, runtime.V12_POLICY_ID, group=True)
    req = runtime.read_execution_request(run, ref, checkpoint="refine-001")
    folder = stage / "parallelity_runtime"
    root = folder.relative_to(run).as_posix()
    observations = req["phosphate"]["inspections"]
    edges = [dict(continuation_id=row["registered_continuation"]["continuation_id"],
                  oxygen_operator_xyz=row["o3_image"], live_sources_sha256=token*64,
                  families={"bond_simple": 1, "angle": 4, "dihedral": 3},
                  bond={"bonds": 1, "second_shell_pairs": 4, "remaining_nonbonded": 0})
             for row, token in zip(observations, "ab")]
    flags = {(1, 0, 0): (4., 1., True), (0, 1, 0): (5., 1., False)}
    record = dict(schema_version=2, request_sha256=ref["sha256"], parent_model_sha256=observations[0]["model_sha256"],
                  full_gradient_calls=3, reflections=reflection_change(flags, flags), bindings_restored=True, edges=edges)
    for phase in ("preflight", "refine"):
        (folder/phase).mkdir()
        (folder/phase/"phosphate.json").write_text(json.dumps(dict(record, phase=phase)))
    selected = dict(id="refine-001", kind="refinement", usable=True, parent="postmr",
                    outputs={"parallelity_execution": ref})
    monkeypatch.setattr(runtime, "validate_execution", lambda *a, **k: dict(request=ref, policy_id=runtime.V12_POLICY_ID))
    with pytest.raises(ValueError, match="1, 4"):
        saved_refinement(run, selected)
    for invalid in (2, True):
        with pytest.raises(ValueError, match="not fitted"):
            saved_refinement(run, selected, identifier=invalid)
    for identifier in (1, 4):
        ancestor, registered, evidence = saved_refinement(run, selected, identifier=identifier)
        assert (ancestor, registered.identifier, evidence["registered_continuation_ids"]) == ("postmr", identifier, [1, 4])
        assert evidence["full_gradient_calls"] == 3
    altered = deepcopy(edges)
    altered[1]["live_sources_sha256"] = "c"*64
    for change in ({"edges": edges[:1]}, {"edges": list(reversed(edges))}, {"edges": altered}, {"full_gradient_calls": 0}):
        (folder/"refine/phosphate.json").write_text(json.dumps(dict(record, phase="refine") | change))
        with pytest.raises(ValueError):
            read_phase(run, root, "refine", req)


def test_descendant_cannot_add_or_drop_a_registered_phosphate(tmp_path):
    from nasolve import refinement_parallelity as runtime
    from nasolve.refinement_phosphate import _check_inherited_scope

    _, run, _, _, ref, _, _ = frozen_round(tmp_path, runtime.V12_POLICY_ID, group=True)
    intent = runtime.read_execution_request(run, ref, checkpoint="refine-001")["phosphate"]
    rows = intent["inspections"]
    ancestor = intent["ancestor"]
    _check_inherited_scope(intent, ancestor, rows)
    with pytest.raises(ValueError, match="different starting branch"):
        _check_inherited_scope(intent, ancestor, rows[:1])
    with pytest.raises(ValueError, match="different starting branch"):
        _check_inherited_scope(dict(ancestor=ancestor, inspection=rows[0]), ancestor, rows)


@pytest.mark.parametrize("policy,ancestor,origin,accepted", [
    (12, "postmr", "7" * 64, True), (11, "postmr", "7" * 64, True),
    (12, "manual-001", "7" * 64, False), (11, "postmr", None, False),
    (10, "postmr", "7" * 64, False),
])
def test_construction_origin_is_specific_to_the_numbered_postmr_protocol(tmp_path, policy, ancestor, origin, accepted):
    from nasolve import refinement_parallelity as runtime
    from nasolve.refinement_phosphate import read_intent

    policy_id = getattr(runtime, f"V{policy}_POLICY_ID")
    _, run, stage, _, ref, _, _ = frozen_round(tmp_path, policy_id, group=policy == 12)
    record = runtime.read_execution_request(run, ref, checkpoint="refine-001")
    record["phosphate"].update(ancestor=ancestor, postmr_construction_sha256=origin)
    root = (stage / "parallelity_runtime").relative_to(run).as_posix()
    if accepted:
        assert read_intent(run, root, record)["postmr_construction_sha256"] == origin
    else:
        with pytest.raises(ValueError, match="construction"):
            read_intent(run, root, record)


@pytest.mark.parametrize("policy_version", [10, 11])
def test_registered_round_retains_order_translated_operator_and_relocatable_sources(tmp_path, policy_version):
    from nasolve.refinement_parallelity import read_execution_request, V10_POLICY_ID, V11_POLICY_ID
    policy = V10_POLICY_ID if policy_version == 10 else V11_POLICY_ID
    original, run, stage, paths, ref, dry, fit = frozen_round(tmp_path, policy)
    helper = stage / "parallelity_runtime/code/_nasolve_refinement/cif_phosphate_restraints.py"
    assert ("_same_atomic_species" in helper.read_text()) == (policy_version == 11)
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
    execution = dict(request=ref, policy_id=refinement_parallelity.V11_POLICY_ID)
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
