"""Explicit all-declared-site observation preserves old policies and lineage."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
import sys
import pytest
from nasolve import refinement_parallelity as runtime
from nasolve.refinement_chemistry import _projection_scope
from nasolve.checkpoints import _file_reference, CheckpointError


def test_nontriple_capture_reaches_ordinary_owner_and_reads_cold_after_move(tmp_path,monkeypatch):
    from tests.test_refinement_parallelity import completed
    run,result,registry,child,receipt,_=completed(tmp_path,monkeypatch,chemistry='bent',declared_sites=True)
    record=json.loads(receipt.read_text());assert record['policy_id']==runtime.V9_POLICY_ID
    request=runtime.read_execution_request(run,record['request'],checkpoint=child['id'])
    with pytest.raises(ValueError,match='no explicit source triple'):
        _projection_scope(run,request['chemistry_projections'])
    original=run.parents[1];moved=tmp_path/'relocated';original.rename(moved);run=moved/run.relative_to(original)
    model=run/child['model']['relative_path'];before={p:(p.read_bytes(),p.stat().st_mtime_ns)for p in run.rglob('*')if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native launch for inspection')):
        report=runtime.read_execution_chemistry_sites(run,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=model)
    assert not original.exists()
    assert report['observation']['status']=='OBSERVED'
    assert len(report['observation']['atoms'])==4
    assert report['observation']['geometry']['proxy_details']['angle']
    assert report['declared_sites']['A:1']['component']=='Q17'
    assert report['model_sha256']==sha256(model.read_bytes()).hexdigest()
    assert report['scientific_approval']=='NOT_RUN'and not report['automatic_adoption']
    assert result.statistics['chemical_geometry']['status']=='UNASSESSED'
    assert 'No explicit triple bonds' in result.statistics['chemical_geometry']['reason']
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())
    with pytest.raises(ValueError,match='declared-site chemistry'):
        runtime.require_runtime_continuation(registry,child,True,run=run)
    runtime.require_runtime_continuation(registry,child,True,run=run,observe_declared_sites=True)
    from nasolve.autorefine import execute_autorefine,AutoRefineError
    with pytest.raises(AutoRefineError,match='declared-site chemistry'):
        execute_autorefine(run,tmp_path/'refine',tmp_path/'dump',phenix_version='2.2.1-6174',from_checkpoint=child['id'],correct_native_parallelity=True,phenix_python_executable=Path(sys.executable))
    assert not (run/'AutoRefine/round_002').exists()
    model.write_bytes(model.read_bytes()+b'REMARK changed\n')
    with pytest.raises(ValueError):
        runtime.read_execution_chemistry_sites(run,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=model)


@pytest.mark.parametrize('code',['Q17','DF','XYZ'])
def test_nontriple_scope_is_explicit_graph_bound_and_not_residue_named(tmp_path,code):
    from tests.test_cif_triple_bond_audit import fixture
    source,_=fixture(tmp_path,code);source.write_text(source.read_text().replace('TRIP','DOUB'))
    refs=[dict(site='B:4',component=code,projection=_file_reference(source,tmp_path))]
    before=source.read_bytes(),source.stat().st_mtime_ns
    with pytest.raises(ValueError,match='no explicit source triple'):_projection_scope(tmp_path,refs)
    sites,paths=_projection_scope(tmp_path,refs,require_triple=False)
    assert sites==[dict(site='B:4',component=code)]and paths['B:4']==(source,code)
    assert (source.read_bytes(),source.stat().st_mtime_ns)==before
    wrong=deepcopy(refs);wrong[0]['component']='BAD'
    with pytest.raises(ValueError):_projection_scope(tmp_path,wrong,require_triple=False)
    source.write_text(source.read_text()+'# changed\n')
    with pytest.raises(CheckpointError):_projection_scope(tmp_path,refs,require_triple=False)


def test_scope_uses_all_and_only_bound_preparation_projections(tmp_path,monkeypatch):
    import nasolve.refinement_chemistry as chemistry
    from tests.test_cif_triple_bond_audit import fixture
    triple,_=fixture(tmp_path);other=tmp_path/'other';other.mkdir();single,_=fixture(other,'NEW')
    single.write_text(single.read_text().replace('TRIP','SING'))
    bundle=dict(projections={'B:4':(single,'NEW'),'A:1':(triple,'Q17')},report=dict(files=[dict(path=p.relative_to(tmp_path).as_posix(),sha256=sha256(p.read_bytes()).hexdigest())for p in (triple,single)]))
    monkeypatch.setattr(chemistry,'_preparation_context',lambda *a:(dict(bundle=bundle,bundle_directory=tmp_path),'postmr',{}))
    assert [r['site']for r in chemistry.prepare_chemistry_scope(tmp_path,{},None,{})]==['A:1']
    assert [r['site']for r in chemistry.prepare_chemistry_scope(tmp_path,{},None,{},include_nontriple=True)]==['A:1','B:4']
    single.write_text(single.read_text()+'# drift\n')
    with pytest.raises(ValueError,match='projection changed'):
        chemistry.prepare_chemistry_scope(tmp_path,{},None,{},include_nontriple=True)


def test_new_scope_reuses_exact_v3_worker_and_old_default():
    assert runtime.POLICY_ID==runtime.V3_POLICY_ID
    assert runtime._code(runtime.V9_POLICY_ID)==runtime._code(runtime.V3_POLICY_ID)==runtime._code()
    for policy in (runtime.V3_POLICY_ID,runtime.V4_POLICY_ID,runtime.V5_POLICY_ID,runtime.V6_POLICY_ID,runtime.V7_POLICY_ID,runtime.V8_POLICY_ID):
        assert {n:sha256(b).hexdigest()for n,b in runtime._code(policy).items()}==runtime._expected_code(policy)


@pytest.mark.parametrize('value,enabled,counted',[(1,True,None),(True,False,None),(True,True,'unsupported')])
def test_new_option_refuses_unsupported_combinations_before_allocation(tmp_path,value,enabled,counted):
    from nasolve.autorefine import execute_autorefine,AutoRefineError
    with pytest.raises(AutoRefineError,match='Declared-site observation'):
        execute_autorefine(tmp_path/'absent',tmp_path/'refine',tmp_path/'dump',phenix_version='2.2.1-6174',observe_declared_sites=value,correct_native_parallelity=enabled,counted_protocol=counted)
    assert list(tmp_path.iterdir())==[]


def test_manual_descendant_cannot_drop_declared_site_observation(tmp_path,monkeypatch):
    from tests.test_refinement_parallelity import completed
    from nasolve.checkpoints import add_checkpoint,read_registry,resolve_checkpoint
    run,_,_,child,_,_=completed(tmp_path,monkeypatch,chemistry='bent',declared_sites=True)
    added=add_checkpoint(run,name='manual',model=run/child['model']['relative_path'],parent=child['id'])
    _,registry=read_registry(run);selected=resolve_checkpoint(registry,added.checkpoint_id)
    with pytest.raises(ValueError,match='declared-site chemistry'):
        runtime.require_runtime_continuation(registry,selected,True,run=run)
    runtime.require_runtime_continuation(registry,selected,True,run=run,observe_declared_sites=True)


def test_unavailable_nontriple_observation_never_invents_native_terms(tmp_path,monkeypatch):
    from tests.test_refinement_parallelity import completed
    run,result,_,child,_,_=completed(tmp_path,monkeypatch,chemistry='unavailable',declared_sites=True)
    report=runtime.read_execution_chemistry_sites(run,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=result.model_path)
    assert report['observation']['status']=='UNASSESSED'
    assert 'atoms'not in report['observation']and 'geometry'not in report['observation']
    assert report['scientific_approval']=='NOT_RUN'


def test_doctor_forwards_declared_site_observation_from_the_exact_source(tmp_path, monkeypatch):
    from nasolve import refine_doctor as doctor
    from nasolve.checkpoints import read_registry, resolve_checkpoint, select_checkpoint
    from tests.test_autorefine import make_refine
    from tests.test_refinement_parallelity import completed

    run, _, _, parent, _, calls = completed(tmp_path, monkeypatch, chemistry="bent", declared_sites=True)
    select_checkpoint(run, "postmr")
    tools = tmp_path / "tools"
    refine = make_refine(tools, final_work=.40, final_free=.48)
    audit = doctor.FreeRAudit("VALID", True, {}, (), tmp_path / "audit.log")
    monkeypatch.setattr(doctor, "audit_free_r_flags", lambda *args: audit)
    trials = [doctor.RefineDoctorTrial("RefineDoctor/ML-group", False),
              doctor.RefineDoctorTrial("RefineDoctor/ML-coordinates-only", False, adp_mode="none")]
    result = doctor.execute_refine_doctor(
        run, refine, tools / "phenix.mtz.dump", phenix_version="2.2.1-6174",
        from_checkpoint=parent["id"], macro_cycles=5, trial_recipes=trials, max_trials=2,
        correct_native_parallelity=True, phenix_python_executable=Path(sys.executable),
        observe_declared_sites=True,
    )
    assert result.current_checkpoint_preserved
    assert json.loads(result.report_path.read_text())["observe_declared_sites_requested"] is True
    assert calls == ["preflight", "refine"] * 3
    _, updated = read_registry(run)
    assert updated["current"] == "postmr" and len(result.trials) == 2
    parent_request = runtime.read_execution_request(
        run, json.loads((run/parent["outputs"]["parallelity_execution"]["relative_path"]).read_bytes())["request"],
        checkpoint=parent["id"],
    )
    for published in result.trials:
        child = resolve_checkpoint(updated, published.checkpoint_id)
        assert child["parent"] == parent["id"]
        sealed = child["outputs"]["parallelity_execution"]
        record = runtime.validate_execution(run, sealed, checkpoint=child["id"], parent=parent["id"], usable=True)
        request = runtime.read_execution_request(run, record["request"], checkpoint=child["id"])
        assert request["policy_id"] == runtime.V9_POLICY_ID
        assert request["inputs"][1]["sha256"] == parent["model"]["sha256"]
        assert request["chemistry_projections"] == parent_request["chemistry_projections"]
        report = runtime.read_execution_plane_geometry(run, sealed, checkpoint=child["id"], parent=parent["id"],
                                                      model=published.model_path)
        assert report["declared_sites"]["A:1"]["component"] == "Q17"


@pytest.mark.parametrize("value,enabled", [(True,False),(1,True)])
def test_doctor_refuses_invalid_observation_choice_before_allocating_work(tmp_path, value, enabled):
    from nasolve.refine_doctor import execute_refine_doctor, RefineDoctorError
    with pytest.raises(RefineDoctorError, match="Declared-site observation"):
        execute_refine_doctor(tmp_path/"absent", tmp_path/"refine", tmp_path/"dump",
            phenix_version="2.2.1-6174", observe_declared_sites=value,
            correct_native_parallelity=enabled, phenix_python_executable=Path(sys.executable))
    assert not list(tmp_path.iterdir())


def test_doctor_observation_does_not_override_counted_ancestry(tmp_path, monkeypatch):
    from tests.test_autorefine_counted import case
    from nasolve.refine_doctor import execute_refine_doctor, RefineDoctorError
    run, refine, dump, options = case(tmp_path)
    with patch("subprocess.Popen", side_effect=AssertionError("Unadmitted Doctor trial started")):
        with pytest.raises(RefineDoctorError, match="inherits counted pair restraints"):
            execute_refine_doctor(run, refine, dump, from_checkpoint=options["from_checkpoint"],
                phenix_version="2.2.1-6174", correct_native_parallelity=True,
                phenix_python_executable=Path(sys.executable), observe_declared_sites=True)
    assert not (run/"RefineDoctor").exists() and not (run/"AutoRefine/round_002").exists()


def test_doctor_cannot_silently_drop_observation_and_invalid_free_r_cannot_start_a_trial(tmp_path, monkeypatch):
    from nasolve import refine_doctor as doctor
    from tests.test_refinement_parallelity import completed
    run, _, _, parent, _, calls = completed(tmp_path, monkeypatch, chemistry="bent", declared_sites=True)
    options = dict(phenix_version="2.2.1-6174", correct_native_parallelity=True,
                   from_checkpoint=parent["id"], phenix_python_executable=Path(sys.executable))
    flags = doctor.FreeRAudit("INVALID", False, {}, (), tmp_path/"audit.log")
    monkeypatch.setattr(doctor,"audit_free_r_flags",lambda *a: flags)
    with pytest.raises(doctor.RefineDoctorError, match="declared-site chemistry"):
        doctor.execute_refine_doctor(run, tmp_path/"tools/phenix.refine", tmp_path/"tools/phenix.mtz.dump", **options)
    assert not (run/"RefineDoctor").exists()
    result = doctor.execute_refine_doctor(run,tmp_path/"tools/phenix.refine",tmp_path/"tools/phenix.mtz.dump",
        observe_declared_sites=True, **options)
    payload = json.loads(result.report_path.read_text())
    assert result.trials == () and result.status == "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED"
    assert payload["observe_declared_sites_requested"] and payload["automatic_selection"] is False
    assert calls == ["preflight","refine"]
