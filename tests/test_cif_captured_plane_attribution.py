"""Maintained whole-plane evidence; synthetic executions test contracts only."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.test_cif_attachment_native import save, rebind


def fixture(tmp_path):
    from tests.test_cif_plane_captures import setup
    from tests.test_cif_plane_energy import case
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_validation import _NATIVE_WORKER
    root=tmp_path/'original';root.mkdir()
    args, options=setup(root)
    numeric=tmp_path/'numeric';numeric.mkdir();values, references=case(numeric)
    for label, receipt, value in zip(('before','after'),args[-2:],values[:2]):
        record=json.loads(receipt.read_text())
        record['native_validation']['energy_inventory']=value['energy_inventory']
        record['executable_sha256']=sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()
        (receipt.parent/'native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER))
        (receipt.parent/'native_effective.phil').write_text('# synthetic effective policy\n')
        (receipt.parent/'canonical_000.phil').write_text('# synthetic canonical policy\n')
        spec=json.loads((receipt.parent/'native_spec.json').read_text());spec['energy_inventory']=True
        save(receipt.parent/'native_spec.json',spec)
        # Synthetic numbers establish accounting/provenance behavior only.
        references[0][label]['sites_cart']=[[0.,0.,0.]]*len(references[0][label]['proxy']['i_seqs'])
        save(receipt,record);rebind(receipt)
    source,component,request,attempt,candidate,model,before,after=args
    call=(source,component,request,attempt,before,after,options['dictionary_index'])
    sdk=SimpleNamespace(executables={'phenix.python':sys.executable},version='SYNTHETIC',environment=os.environ)
    return call,sdk,references


def fake_runner(refs, mode='pass'):
    def run(command, *, cwd, log_path, environment, timeout_seconds):
        from nasolve import cif_captured_plane_attribution as m
        log_path.write_text('EXPLICIT SYNTHETIC EXECUTION\n')
        if mode=='interrupt': raise KeyboardInterrupt
        if mode=='unknown_timeout': raise subprocess.TimeoutExpired(command,timeout_seconds)
        if mode=='timeout':
            exc=subprocess.TimeoutExpired(command,timeout_seconds);exc.returncode=-15;exc.stopped_verified=True;raise exc
        if mode=='failed':return 3
        for name,data in m._native_auxiliary(cwd.parent).items():
            (cwd.parent/name).write_bytes(data)
        spec=json.loads((cwd/'spec.json').read_text())
        pins=spec['installed_sources']+[dict(module=n,sha256='b'*64,historical_path='/missing/'+n) for n in m.MODULES[3:]]
        sides={}
        for label in ('before','after'):
            save(cwd/label/'native_validation.json',spec[label]['inventory'])
            sides[label]=dict(exact_native_inventory=True,special_position_indices=[],references=[deepcopy(r[label]) for r in refs])
        result=dict(spec_sha256=sha256((cwd/'spec.json').read_bytes()).hexdigest(),
            evaluator_sha256=sha256((cwd/'evaluator.py').read_bytes()).hexdigest(),
            installed_sources=pins,installed_sources_after=deepcopy(pins),sides=sides)
        if mode=='numeric':
            for e in result['sides']['after']['references'][0]['evaluations']:e['single_target']+=1;e['accumulated_target']+=1
        save(cwd/'result.json',result)
        return 0
    return run


def test_prepared_plane_job_replays_after_original_inputs_are_gone_without_execution(tmp_path):
    from nasolve import cif_captured_plane_attribution as m
    args,sdk,refs=fixture(tmp_path);output=tmp_path/'out'
    with patch('subprocess.Popen',side_effect=AssertionError('Preparation/readback must not execute')):
        report=m.audit_captured_plane_attribution(*args,None,output)
        assert report['status']=='PREPARED_ONLY' and report['new_native_calls']==0
        moved=output.rename(tmp_path/'moved');shutil.rmtree(tmp_path/'original')
        assert m.read_captured_plane_attribution(moved)==report
    assert report['qualification']=={'status':'NOT_RUN'} and not report['automatic_adoption']


@pytest.mark.parametrize('mode',['pass','numeric','failed','timeout'])
def test_owned_runner_outcome_keeps_complete_plane_accounting_and_replays_cold(tmp_path,mode):
    from nasolve import cif_captured_plane_attribution as m
    args,sdk,refs=fixture(tmp_path);output=tmp_path/'out'
    report=m.audit_captured_plane_attribution(*args,sdk,output,_process_runner=fake_runner(refs,mode))
    assert report['status']==('CAPTURED_PLANE_ATTRIBUTION_PASS' if mode=='pass' else 'REVIEW')
    assert report['new_native_calls']==1 and report['derivative_qualification']=='NOT_RUN'
    if mode=='pass':
        assert report['qualification']['changed_plane_count']==1
        assert report['qualification']['whole_plane_target_delta']==3.
    with pytest.raises(ValueError):m.audit_captured_plane_attribution(*args,sdk,output)
    moved=output.rename(tmp_path/'moved');shutil.rmtree(tmp_path/'original')
    with patch('subprocess.Popen',side_effect=AssertionError('No replayed execution')):
        assert m.read_captured_plane_attribution(moved)==report


@pytest.mark.parametrize('mode',['interrupt','unknown_timeout'])
def test_interruption_and_uncertain_cleanup_never_become_a_finished_plane_result(tmp_path,mode):
    from nasolve import cif_captured_plane_attribution as m
    from nasolve.campaign_process import CampaignProcessError
    args,sdk,refs=fixture(tmp_path);output=tmp_path/'out'
    with pytest.raises(KeyboardInterrupt if mode=='interrupt' else CampaignProcessError):
        m.audit_captured_plane_attribution(*args,sdk,output,_process_runner=fake_runner(refs,mode))
    assert (output/'job/spec.json').is_file() and not (output/m.REPORT).exists()


@pytest.mark.parametrize('defect',['worker','evaluator','spec','model','capture','support','numerics','symmetry',
    'special_position','pins','rebuilt_native','effective_phil','missing_log','claim','suppressed_pass','calls','extra','bound_extra'])
def test_rehashed_changes_cannot_invent_a_plane_pass(tmp_path,defect):
    from nasolve import cif_captured_plane_attribution as m
    args,sdk,refs=fixture(tmp_path);output=tmp_path/'out'
    report=m.audit_captured_plane_attribution(*args,sdk,output,_process_runner=fake_runner(refs))
    if defect in {'worker','evaluator','spec'}:
        name={'worker':'worker.py','evaluator':'evaluator.py','spec':'spec.json'}[defect]
        p=output/'job'/name;p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='model':
        spec=json.loads((output/'inputs/before/native_spec.json').read_text());p=output/'inputs/before'/spec['model'];p.write_bytes(p.read_bytes()+b'REMARK changed\n')
    elif defect=='capture':
        p=output/'inputs/after/native_receipt.json';r=json.loads(p.read_text());r['phenix_version']='other';save(p,r)
    elif defect=='support':
        p=output/'inputs/generation/request.json';r=json.loads(p.read_text());r['configuration']['recipe']['multiple_planes']=False
        from nasolve.campaign_records import write_record
        write_record(p,r,replace=True)
    elif defect in {'numerics','symmetry','special_position','pins'}:
        p=output/'job/result.json';r=json.loads(p.read_text())
        if defect=='numerics':r['sides']['after']['references'][0]['evaluations'][0]['single_target']+=1
        if defect=='symmetry':r['sides']['after']['references'][0]['symmetry_operations']=['x+1,y,z']*4
        if defect=='special_position':r['sides']['after']['special_position_indices']=[0]
        if defect=='pins':r['installed_sources_after'][0]['sha256']='0'*64
        save(p,r)
    elif defect=='rebuilt_native':
        p=output/'job/after/native_validation.json';r=json.loads(p.read_text());r['geometry']['proxy_details']['parallelity']=[];save(p,r)
    elif defect=='effective_phil':(output/'job/after/native_effective.phil').write_text('different policy')
    elif defect=='missing_log':
        (output/'job/execution.log').unlink();report['outputs']=[r for r in report['outputs'] if r['path']!='job/execution.log']
    elif defect=='claim':report['automatic_adoption']=True
    elif defect=='suppressed_pass':report.update(status='REVIEW',qualification={'status':'NOT_RUN'},kernel_execution_authentication='NOT_RUN')
    elif defect=='calls':report['new_native_calls']=True
    else:(output/'job/unrequested').write_text('not a declared output')
    report['outputs']=[m._ref(output/r['path'],output,m.ANCHOR) for r in report['outputs']]
    if defect=='bound_extra':report['outputs'],report['directories']=m._inventory(output)
    save(output/m.REPORT,report)
    with pytest.raises(ValueError):m.read_captured_plane_attribution(output)


@pytest.mark.parametrize('defect',['version','index','attempt','timeout','unrelated_capture_file'])
def test_invalid_inputs_refuse_before_output_reservation(tmp_path,defect):
    from nasolve import cif_captured_plane_attribution as m
    args,sdk,refs=fixture(tmp_path);args=list(args);seconds=120
    if defect=='version':sdk.version='other'
    if defect=='index':args[-1]=True
    if defect=='attempt':args[3]=2
    if defect=='timeout':seconds=True
    if defect=='unrelated_capture_file':(args[-3].parent/'unrelated.txt').write_text('leave alone')
    with pytest.raises(ValueError):
        m.audit_captured_plane_attribution(*args,sdk,tmp_path/'out',timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()
