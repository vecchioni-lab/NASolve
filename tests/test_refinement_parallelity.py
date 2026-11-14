"""Ordinary AutoRefine must bind explicit compatibility to its exact round."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from tests.test_refinement_inputs import inputs
from nasolve.autorefine import execute_autorefine,AutoRefineError
from nasolve.checkpoints import read_registry,resolve_checkpoint,CheckpointError,_file_reference
from nasolve.campaign_records import write_record


def completed(tmp_path,monkeypatch,*,failure=None,changed=None,bad_preflight=False):
    run,policy,refine,dump=inputs(tmp_path);original=subprocess.run;commands=[]
    def consume(command,*args,**kwargs):
        if len(command)>2 and str(command[2]).endswith('/parallelity_runtime/entry.py'):
            phase=command[3];commands.append(phase)
            if bad_preflight and phase=='refine':pytest.fail('refinement launched without complete preflight evidence')
            root=Path(command[2]).parent;folder=root/phase;folder.mkdir();(folder/'calls').mkdir()
            native_args=command[4:]
            if phase=='preflight':
                assert '--dry_run' not in native_args and native_args[-1]=='refinement.dry_run=True'
                assert 'output.prefix=parallelity_runtime/preflight/native' in native_args
                assert 'output.prefix=refined' not in native_args
            if phase=='preflight':(folder/'native_001.geo').write_text('preflight geometry preserved')
            profile=json.loads((root/'code/_nasolve_refinement/data/parallelity-native-profile.json').read_text())
            failed=phase==failure
            result=dict(schema_version=1,policy_id='explicit-native-parallelity-refinement-v1',
                status='FAILED' if failed else 'COMPLETE',arguments=native_args,pid=123,parent_pid=122,
                scientific_approval='NOT_RUN',binding_restored=True,native_profile=profile,
                dry_run=phase=='preflight',macro_cycles=0 if phase=='preflight' else 5,
                atom_labels=['a','b'],parallelity_parameters=[],usage_observations=[],
                parent_kernel_statistics=dict(policy_id='native-parallelity-kernel-adapter-v1',
                    successful_calls=0,gradient_calls=0,energy_only_calls=0,maximum_proxy_count=0))
            if bad_preflight and phase=='preflight':result['status']='RUNNING'
            if failed:result['error']=dict(type='RuntimeError',message='native failed')
            (folder/'result.json').write_text(json.dumps(result))
            if changed==phase:
                (root/'code/_nasolve_refinement/cif_parallelity_kernel.py').write_text('changed helper')
            if failed:return subprocess.CompletedProcess(command,1)
            fake_args=['--dry_run',*native_args[:-1]] if phase=='preflight' else native_args
            return original([str(refine),*fake_args],*args,**kwargs)
        return original(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'run',consume)
    result=execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174',
        correct_native_parallelity=True,phenix_python_executable=Path(sys.executable))
    _,registry=read_registry(run);child=resolve_checkpoint(registry,result.checkpoint_id)
    receipt=run/child['outputs']['parallelity_execution']['relative_path']
    return run,result,registry,child,receipt,commands


def test_explicit_route_uses_original_executor_and_saves_exact_round_evidence(tmp_path,monkeypatch):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    assert commands==['preflight','refine'] and child['usable']
    record=json.loads(receipt.read_text());assert [p['returncode'] for p in record['phases']]==[0,0]
    request=json.loads((run/record['request']['relative_path']).read_text())
    assert request['parent']==child['parent'] and request['checkpoint']==child['id']
    assert child['outputs']['parallelity_execution']['anchor']=='run'
    assert len(request['code'])==6 and len(request['inputs'])==6
    assert (result.round_directory/'received_args.json').exists()


@pytest.mark.parametrize('phase',['preflight','refine'])
def test_native_failure_retains_readable_failed_checkpoint_without_retry(tmp_path,monkeypatch,phase):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,failure=phase)
    assert not child['usable'] and child['status']=='FAILED'
    assert commands==(['preflight'] if phase=='preflight' else ['preflight','refine'])
    record=json.loads(receipt.read_text());assert record['phases'][0 if phase=='preflight' else 1]['returncode']==1
    assert registry['current']=='postmr'


@pytest.mark.parametrize('phase',['preflight','refine'])
def test_changed_frozen_helper_preserves_outputs_but_cannot_publish(tmp_path,monkeypatch,phase):
    with pytest.raises(AutoRefineError,match='changed|differs'):
        completed(tmp_path,monkeypatch,changed=phase)
    run=tmp_path/'dataset/AutoMR/run_001'
    assert (run/'AutoRefine/round_001/parallelity_runtime').exists()
    assert len(json.loads((run/'AutoRefine/checkpoints.json').read_text())['checkpoints'])==1


def test_cold_checkpoint_read_after_dataset_move_never_calls_native(tmp_path,monkeypatch):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    old=run.parents[1];moved=tmp_path/'relocated';old.rename(moved);assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        _,saved=read_registry(moved/'AutoMR/run_001')
    assert resolve_checkpoint(saved,child['id'])['usable']


@pytest.mark.parametrize('defect',['code','rehash_code','result','missing','extra','usage','parent','input','usable_failure','cycle_count','symlink_code','symlink_request','statistics'])
def test_reader_refuses_changed_or_relabelled_runtime_evidence(tmp_path,monkeypatch,defect):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    record=json.loads(receipt.read_text());request_path=run/record['request']['relative_path'];request=json.loads(request_path.read_text())
    root=request_path.parent
    if defect in ('code','rehash_code'):
        p=root/'code/_nasolve_refinement/cif_parallelity_kernel.py';p.write_text('changed')
        if defect=='rehash_code':
            request['code']['code/_nasolve_refinement/cif_parallelity_kernel.py']=_file_reference(p,run)
    elif defect in ('symlink_code','symlink_request'):
        p=root/'code/_nasolve_refinement/cif_parallelity_kernel.py' if defect=='symlink_code' else request_path
        other=root/(p.name+'.saved');p.rename(other);p.symlink_to(other)
    elif defect=='missing':(root/'refine/result.json').unlink()
    elif defect=='extra':(root/'refine/unrecorded.json').write_text('{}')
    elif defect=='parent':request['parent']='refine-999'
    elif defect=='input':request['inputs'][1]=request['inputs'][0]
    elif defect=='usable_failure':record['phases'][1]['returncode']=1
    else:
        p=root/'refine/result.json';value=json.loads(p.read_text())
        if defect in ('result','cycle_count'):value['macro_cycles']=0 if defect=='result' else 1
        elif defect=='statistics':value['parent_kernel_statistics']['successful_calls']=1
        else:value['usage_observations']=['not-recorded.json']
        p.write_text(json.dumps(value));record['phases'][1]['files']=[_file_reference(p,run)]
    if defect in ('rehash_code','parent','input'):
        write_record(request_path,request,replace=True);record['request']=_file_reference(request_path,run)
    if defect in ('rehash_code','parent','input','result','usage','usable_failure','cycle_count','statistics'):
        write_record(receipt,record,replace=True);child['outputs']['parallelity_execution']=_file_reference(receipt,run)
        (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        with pytest.raises(CheckpointError):read_registry(run)


def test_opt_in_requires_python_before_creating_registry_or_round(tmp_path):
    run,policy,refine,dump=inputs(tmp_path)
    with pytest.raises(AutoRefineError,match='phenix.python'):
        execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174',correct_native_parallelity=True)
    assert not (run/'AutoRefine').exists()


def test_zero_exit_without_complete_model_preflight_cannot_start_refinement(tmp_path,monkeypatch):
    with pytest.raises(AutoRefineError,match='preflight evidence'):
        completed(tmp_path,monkeypatch,bad_preflight=True)


def test_preflight_native_outputs_are_retained_in_the_phase_receipt(tmp_path,monkeypatch):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    record=json.loads(receipt.read_text())
    files=record['phases'][0]['files']
    native=[r for r in files if r['relative_path'].endswith('/preflight/native_001.geo')]
    assert len(native)==1
    assert (run/native[0]['relative_path']).read_text()=='preflight geometry preserved'
    assert (result.round_directory/'refined_001.pdb').is_file()


@pytest.mark.parametrize('manual',[False,True])
def test_checked_ancestry_cannot_silently_drop_the_correction(tmp_path,monkeypatch,manual):
    from nasolve.checkpoints import add_checkpoint
    from tests.test_cif_postmr_publication import snapshot
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    parent=child['id']
    if manual:
        imported=add_checkpoint(run,name='manual-child',model=run/child['model']['relative_path'],parent=parent)
        parent=imported.checkpoint_id
    before=snapshot(run)
    with patch('subprocess.Popen',side_effect=AssertionError('refusal must precede native execution')):
        with pytest.raises(AutoRefineError,match='checked-plane-forces'):
            execute_autorefine(run,tmp_path/'tools/phenix.refine',tmp_path/'tools/phenix.mtz.dump',
                phenix_version='2.2.1-6174',from_checkpoint=parent)
    assert snapshot(run)==before
    assert not (run/'AutoRefine/round_002').exists()


@pytest.mark.parametrize('checked,parent',[(True,'refine-001'),(False,'postmr')])
def test_explicit_continuation_and_uncorrected_sibling_use_existing_checkpoint_owner(tmp_path,monkeypatch,checked,parent):
    from tests.test_cif_postmr_publication import snapshot
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    before=snapshot(result.round_directory)
    next_result=execute_autorefine(run,tmp_path/'tools/phenix.refine',tmp_path/'tools/phenix.mtz.dump',
        phenix_version='2.2.1-6174',from_checkpoint=parent,correct_native_parallelity=checked,
        phenix_python_executable=Path(sys.executable) if checked else None)
    _,saved=read_registry(run);next_child=resolve_checkpoint(saved,next_result.checkpoint_id)
    assert next_child['id']=='refine-002' and next_child['parent']==parent and next_child['usable']
    assert ('parallelity_execution' in next_child['outputs']) is checked
    assert snapshot(result.round_directory)==before


def test_checked_ancestry_reuses_strict_lineage_validation():
    from nasolve.refinement_parallelity import requires_checked_plane_forces
    parent=dict(id='refine-001',parent='missing',outputs={'parallelity_execution':{}})
    with pytest.raises(ValueError,match='unknown parent'):
        requires_checked_plane_forces({'checkpoints':[parent]},parent)
