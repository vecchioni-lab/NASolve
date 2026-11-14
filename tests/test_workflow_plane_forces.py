"""Frozen campaign and Doctor choices must reach the same refinement owner."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from nasolve.checkpoints import read_registry,resolve_checkpoint
from nasolve.cli import build_parser
from nasolve.refine_doctor import execute_refine_doctor,RefineDoctorError,RefineDoctorTrial
from nasolve.presets import load_preset,PresetError
from nasolve.campaign_stages import CampaignStageError
from nasolve.campaigns import campaign_status,CampaignError
from tests import test_campaigns,test_campaign_stages
from tests.test_refinement_parallelity import completed
from tests.test_refinement_inputs import inputs
from tests.test_cif_postmr_publication import snapshot


@pytest.mark.parametrize('value,schema,valid', [('true',2,True),('false',2,True),('true',1,False),('1',2,False),('"true"',2,False)])
def test_frozen_refinement_choice_is_versioned_and_typed(tmp_path,value,schema,valid):
    path=tmp_path/'preset.toml'
    path.write_text(f'schema_version = {schema}\nid = "test"\nversion = "1"\n[autorefine]\nchecked_plane_forces = {value}\n')
    if valid:
        assert load_preset(path).to_dict()['autorefine']==dict(recipe='AutoRefine/default',cycles=5,checked_plane_forces=value=='true')
    else:
        with pytest.raises(PresetError):load_preset(path)


def test_campaign_choice_survives_relocation_and_reader_rejects_resigned_bad_type():
    case=test_campaigns.CampaignTests();case.setUp()
    try:
        case.dataset('sample');case.write_preset(extra='[autorefine]\nchecked_plane_forces = true\n')
        case.preset.write_text(case.preset.read_text().replace('schema_version = 1','schema_version = 2'))
        plan=case.plan();assert plan['preset']['policy']['autorefine']['checked_plane_forces'] is True
        frozen=case.state_path().read_bytes();old=case.root;case.root=case.base/'relocated';old.rename(case.root);case.preset.unlink()
        with patch('subprocess.Popen',side_effect=AssertionError('cold read')):
            assert campaign_status(case.root)['integrity']=='OK'
        assert not old.exists() and case.state_path().read_bytes()==frozen
        def corrupt(state):
            import hashlib
            policy=state['preset']['policy'];policy['autorefine']['checked_plane_forces']=1
            state['preset']['config_sha256']=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        case.rewrite_state(corrupt,resign=True)
        with pytest.raises(CampaignError):campaign_status(case.root)
    finally:case.doCleanups()


@pytest.mark.parametrize('stage',['autorefine','refine-doctor'])
def test_campaign_forwards_exact_native_python_to_both_existing_owners(stage):
    case=test_campaign_stages.CampaignStageTests();case.setUp()
    try:
        run=test_campaign_stages.make_refine_run(case.root);case.set_run(run)
        refine=test_campaign_stages.make_refine(case.tools,final_work=.24,final_free=.22)
        dump=test_campaign_stages.refine_dump(case.tools)
        case.phenix.executables.update({'phenix.refine':refine,'phenix.mtz.dump':dump,'phenix.python':case.tools/'phenix.python'})
        if stage=='refine-doctor':case.stage('autorefine',run)
        case.policy['schema_version']=2;case.policy['autorefine']['checked_plane_forces']=True
        target='nasolve.campaign_stages.execute_'+stage.replace('-','_')
        with patch(target,side_effect=RuntimeError('stop at owner')) as owner:
            with pytest.raises(RuntimeError,match='stop at owner'):case.stage(stage,run)
        assert owner.call_args.kwargs['correct_native_parallelity'] is True
        assert owner.call_args.kwargs['phenix_python_executable']==case.tools/'phenix.python'
    finally:case.doCleanups()


@pytest.mark.parametrize('stage',['autorefine','refine-doctor'])
def test_bad_campaign_choice_refuses_before_discovery_or_execution(stage):
    case=test_campaign_stages.CampaignStageTests();case.setUp()
    try:
        run=test_campaign_stages.make_refine_run(case.root);case.set_run(run)
        case.policy['schema_version']=2;case.policy['autorefine']['checked_plane_forces']='true'
        with patch('nasolve.campaign_stages.discover_phenix',side_effect=AssertionError('must validate first')):
            with pytest.raises(CampaignStageError):case.stage(stage,run)
        assert not (run/'AutoRefine').exists() and not (run/'RefineDoctor').exists()
    finally:case.doCleanups()


def test_doctor_keeps_checked_forces_in_actual_sibling_checkpoint(tmp_path,monkeypatch):
    run,previous,registry,parent,receipt,commands=completed(tmp_path,monkeypatch)
    before=snapshot(previous.round_directory);current=registry['current']
    result=execute_refine_doctor(run,tmp_path/'tools/phenix.refine',tmp_path/'tools/phenix.mtz.dump',
        phenix_version='2.2.1-6174',from_checkpoint=parent['id'],macro_cycles=5,max_trials=1,
        trial_recipes=[RefineDoctorTrial('RefineDoctor/ML-geometry-conservative',False)],
        correct_native_parallelity=True,phenix_python_executable=tmp_path/'tools/phenix.python')
    assert len(result.trials)==1 and result.current_checkpoint_preserved
    _,saved=read_registry(run);child=resolve_checkpoint(saved,result.trials[0].checkpoint_id)
    assert child['parent']==parent['id'] and child['usable'] and 'parallelity_execution' in child['outputs']
    assert saved['current']==current and snapshot(previous.round_directory)==before
    assert json.loads(result.report_path.read_text())['checked_plane_forces'] is True


def test_doctor_without_explicit_correction_refuses_before_audit_or_directory(tmp_path,monkeypatch):
    run,previous,registry,parent,receipt,commands=completed(tmp_path,monkeypatch);before=snapshot(run)
    with patch('subprocess.Popen',side_effect=AssertionError('must refuse before audit')):
        with pytest.raises(RefineDoctorError,match='checked-plane-forces'):
            execute_refine_doctor(run,tmp_path/'tools/phenix.refine',tmp_path/'tools/phenix.mtz.dump',phenix_version='2.2.1-6174',from_checkpoint=parent['id'])
    assert snapshot(run)==before and not (run/'RefineDoctor').exists()


@pytest.mark.parametrize('enabled,python',[(1,None),(True,None)])
def test_doctor_invalid_runtime_choice_refuses_before_registry(tmp_path,enabled,python):
    run,policy,refine,dump=inputs(tmp_path)
    with pytest.raises(RefineDoctorError):
        execute_refine_doctor(run,refine,dump,phenix_version='2.2.1-6174',correct_native_parallelity=enabled,phenix_python_executable=python)
    assert not (run/'AutoRefine').exists() and not (run/'RefineDoctor').exists()


def test_doctor_cli_has_the_same_explicit_flag():
    args=build_parser().parse_args(['refine-doctor','/run','--checked-plane-forces'])
    assert args.checked_plane_forces is True and args.run==Path('/run')
