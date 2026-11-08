"""Explicit component requests preserve process and chemical evidence separately."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import pytest
from tests.test_cif_candidate_qualification_execution import case
from tests.test_cif_repair_process import inventory


@pytest.fixture
def setup(case,tmp_path,monkeypatch):
    from nasolve import cif_acquisition_attempt as m
    from nasolve import cif_generation_attempt as generation_module
    from nasolve.cif_generation_process import run_generation_command
    qualification,args,calls,native=case
    s,c,code,consumer,sdk,unused=args
    for name in ('python','elbow','api.py'):(sdk.root/name).write_text(name)
    sdk.executables['phenix.python']=sdk.root/'python';consumer['executable_sha256']=sha256(b'python').hexdigest()
    pin=dict(anchor='phenix_installation',path='api.py',sha256=sha256(b'api.py').hexdigest(),size=6)
    generation=dict(installation_root=sdk.root,python_executable=sdk.root/'python',elbow_executable=sdk.root/'elbow',api_sources=[pin],prior_sources=[pin],environment=dict(os.environ),expected_dialect='CHEMICAL_COMPONENTS_CIF',phenix_version='SYNTHETIC',single_block_steps=12,timeout_seconds=5,max_attempts=2)
    generated=[]
    def generate(root,python,elbow,api,source,code,output,**kwargs):
        output.mkdir();generated.append(output)
        context=dict(component=code,source_sha256=sha256(source.read_bytes()).hexdigest(),attempt_owner=kwargs['attempt_identity'])
        run_generation_command([sys.executable,'-c','print("synthetic generation")'],output,phase='candidate',environment=dict(os.environ),timeout_seconds=kwargs['timeout_seconds'],context=context)
        target=output/'candidate.cif';target.write_bytes(c.read_bytes())
        report=dict(schema_version=1,status='CANDIDATE_REVIEW',component=code,source_sha256=sha256(source.read_bytes()).hexdigest(),source_preserved=True,candidate_retained=True,candidate=dict(anchor='candidate_directory',path='candidate.cif',sha256=sha256(c.read_bytes()).hexdigest(),size=c.stat().st_size),execution={'status':'COMPLETED'},stopping={'status':'NOT_REPORTED'})
        (output/'source_candidate_receipt.json').write_text(json.dumps(report));return report
    monkeypatch.setattr(generation_module,'generate_source_candidate',generate)
    return m,(s,code,tmp_path/'store',tmp_path/'request'),dict(source_authority='EXPLICIT',consumer=consumer,generation=generation,phenix=sdk,total_timeout_seconds=30,max_attempts=3),calls,generated


def test_miss_then_cache_hit_share_request_and_preserve_attempts(setup):
    m,args,options,calls,generated=setup
    first=m.acquire_dictionary_attempt(*args,**options);before=inventory(args[-1]/'attempts/attempt-0001')
    second=m.acquire_dictionary_attempt(*args,**options)
    assert first['request_id']==second['request_id'] and first['attempt_id']!=second['attempt_id']
    assert second['attempt_number']==2 and second['acquisition']['status']=='REUSED'
    assert len(generated)==1 and len(calls)==2 and inventory(args[-1]/'attempts/attempt-0001')==before
    state=m.inspect_acquisition_request(args[-1]);assert state['availability']=='AVAILABLE' and not state['retry_authorized']
    assert m.read_acquisition_result(args[-1],2)['report']['entry_id']==first['acquisition']['entry_id']


def test_absent_inspection_does_not_create_request(setup):
    m,args,options,calls,generated=setup
    assert m.inspect_acquisition_request(args[-1])['state']=='NOT_RECORDED' and not args[-1].exists()


@pytest.mark.parametrize('field',['source','consumer','total','native','allowance'])
def test_changed_request_refuses_new_reservation(setup,field):
    m,args,options,calls,generated=setup;m.acquire_dictionary_attempt(*args,**options);before=inventory(args[-1]);options=deepcopy(options)
    if field=='source':args[0].write_bytes(args[0].read_bytes()+b'\n# other exact bytes\n')
    elif field=='consumer':options['consumer']['version']='OTHER'
    elif field=='total':options['total_timeout_seconds']=31
    elif field=='native':options['native_timeout_seconds']=91
    else:options['max_attempts']=2
    with pytest.raises(ValueError):m.acquire_dictionary_attempt(*args,**options)
    assert inventory(args[-1])==before



def test_generation_pre_reservation_failure_never_claims_later_child(setup,monkeypatch):
    m,args,options,calls,generated=setup;run=m.generate_source_candidate_attempt
    def fail(**kwargs):raise KeyboardInterrupt('before nested reservation')
    monkeypatch.setattr(m,'generate_source_candidate_attempt',fail)
    with pytest.raises(KeyboardInterrupt):m.acquire_dictionary_attempt(*args,**options)
    previous=inventory(args[-1]/'attempts/attempt-0001');monkeypatch.setattr(m,'generate_source_candidate_attempt',run)
    result=m.acquire_dictionary_attempt(*args,**options);state=m.inspect_acquisition_request(args[-1])
    assert result['attempt_number']==2 and state['attempts'][0]['children']['generation']['state']=='NOT_CREATED'
    assert len(generated)==1 and inventory(args[-1]/'attempts/attempt-0001')==previous


def test_cache_hit_needs_no_live_sdk_and_readback_relocates(setup,monkeypatch):
    import shutil
    m,args,options,calls,generated=setup;m.acquire_dictionary_attempt(*args,**options)
    shutil.rmtree(options['phenix'].root);options=dict(options,phenix=None)
    result=m.acquire_dictionary_attempt(*args,**options);assert result['acquisition']['status']=='REUSED' and len(generated)==1
    root=args[-1];moved=root.with_name('relocated');root.rename(moved);args[0].unlink();shutil.rmtree(args[2])
    import subprocess
    def forbidden(*a,**k):raise AssertionError('Readback wrote or executed')
    monkeypatch.setattr(subprocess,'Popen',forbidden);monkeypatch.setattr(m,'write_record',forbidden)
    before=inventory(moved);assert m.read_acquisition_result(moved,2)['report']['status']=='REUSED';assert inventory(moved)==before


@pytest.mark.parametrize('option,value',[('total_timeout_seconds',0),('total_timeout_seconds',None),('total_timeout_seconds',True),('native_timeout_seconds',601),('max_attempts',6)])
def test_bad_limits_do_not_create_request(setup,option,value):
    m,args,options,calls,generated=setup;options=dict(options);options[option]=value
    with pytest.raises(ValueError):m.acquire_dictionary_attempt(*args,**options)
    assert not args[-1].exists() and not generated


def test_overlapping_call_refuses_and_lock_inode_survives(setup):
    from nasolve.campaign_process import exclusive_lock,CampaignProcessError
    m,args,options,calls,generated=setup;root=args[-1];root.mkdir()
    with exclusive_lock(root/'request.lock'):
        inode=(root/'request.lock').stat().st_ino
        with pytest.raises(CampaignProcessError):m.acquire_dictionary_attempt(*args,**options)
        assert not (root/'attempts').exists()
    m.acquire_dictionary_attempt(*args,**options);assert (root/'request.lock').stat().st_ino==inode


def test_outer_exhaustion_preserves_all_prior_work(setup):
    from nasolve.campaign_process import CampaignProcessError
    m,args,options,calls,generated=setup;options=dict(options,max_attempts=1)
    m.acquire_dictionary_attempt(*args,**options);before=inventory(args[-1])
    with pytest.raises(CampaignProcessError,match='exhausted'):m.acquire_dictionary_attempt(*args,**options)
    assert inventory(args[-1])==before and len(generated)==1


@pytest.mark.parametrize('boundary',['preflight','after_generation','after_qualification','after_snapshot'])
def test_shared_budget_withholds_late_result(setup,monkeypatch,boundary):
    m,args,options,calls,generated=setup;clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    if boundary=='preflight':
        original=m._configuration
        def late(*a,**k):r=original(*a,**k);clock[0]=31.;return r
        monkeypatch.setattr(m,'_configuration',late)
    else:
        name={'after_generation':'generate_source_candidate_attempt','after_qualification':'execute_candidate_qualification','after_snapshot':'resolve_generated_dictionary'}[boundary];original=getattr(m,name)
        def late(*a,**k):r=original(*a,**k);clock[0]=31.;return r
        monkeypatch.setattr(m,name,late)
    with pytest.raises(m.AcquisitionBudgetExceeded):m.acquire_dictionary_attempt(*args,**options)
    if boundary=='preflight':assert not args[-1].exists()
    else:
        state=m.inspect_acquisition_request(args[-1]);assert state['attempts'][0]['state']=='STOPPED'
        with pytest.raises(ValueError):m.read_acquisition_result(args[-1],1)
        if boundary=='after_snapshot':assert (args[-1]/'attempts/attempt-0001/snapshot/resolution.json').is_file()


def test_generation_failure_does_not_reset_shared_allowance(setup,monkeypatch):
    m,args,options,calls,generated=setup
    def refuse(*a,**k):raise ValueError('no native permission')
    monkeypatch.setattr(m,'execute_candidate_qualification',refuse)
    for _ in range(2):
        with pytest.raises(ValueError):m.acquire_dictionary_attempt(*args,**options)
    with pytest.raises(ValueError,match='blocked or exhausted'):m.acquire_dictionary_attempt(*args,**options)
    from nasolve.cif_generation_attempt import inspect_source_generation_request
    g=inspect_source_generation_request(args[-1]/'generation')
    assert g['availability']=='EXHAUSTED' and len(g['attempts'])==2 and len(generated)==2
    assert m.inspect_acquisition_request(args[-1])['availability']=='EXHAUSTED'


@pytest.mark.parametrize('activity',[True,None,False])
def test_unsealed_attempt_recovers_only_after_known_caller_death(setup,monkeypatch,activity):
    from nasolve.campaign_process import CampaignProcessError
    m,args,options,calls,generated=setup;m.acquire_dictionary_attempt(*args,**options)
    (args[-1]/'attempts/attempt-0001/finished.json').unlink();before=inventory(args[-1]/'attempts/attempt-0001')
    monkeypatch.setattr(m,'coordinator_alive',lambda identity:activity)
    state=m.inspect_acquisition_request(args[-1]);assert state['availability']==('AVAILABLE' if activity is False else 'BLOCKED')
    if activity is False:assert m.acquire_dictionary_attempt(*args,**options)['attempt_number']==2
    else:
        with pytest.raises(CampaignProcessError):m.acquire_dictionary_attempt(*args,**options)
    assert inventory(args[-1]/'attempts/attempt-0001')==before


@pytest.mark.parametrize('damage',['missing_parent','wrong_parent','missing_process','changed_result','extra_input','missing_intent'])
def test_corrupt_or_unknown_evidence_cannot_authorize_retry(setup,monkeypatch,damage):
    from nasolve.campaign_records import read_record,write_record
    m,args,options,calls,generated=setup;m.acquire_dictionary_attempt(*args,**options);root=args[-1];attempt=root/'attempts/attempt-0001'
    if damage in {'missing_parent','wrong_parent'}:
        p=root/'generation/attempts/attempt-0001/attempt.json';v=read_record(p)
        if damage=='missing_parent':v.pop('parent_attempt')
        else:v['parent_attempt']['attempt_id']='0'*8+'-'+'0'*4+'-'+'0'*4+'-'+'0'*4+'-'+'0'*12
        write_record(p,v,replace=True)
    elif damage=='changed_result':(attempt/'snapshot/entry/dictionary.cif').write_text('changed')
    elif damage=='extra_input':(root/'inputs/extra').write_text('unknown')
    elif damage=='missing_intent':(attempt/'attempt.json').unlink()
    else:
        (attempt/'finished.json').unlink();native=attempt/'qualification/native';(native/'ownership/finished.json').unlink()
        for name in ('process.json','finished.json'):(native/'ownership/phases/native-000'/name).unlink()
        monkeypatch.setattr(m,'coordinator_alive',lambda identity:False)
    before=inventory(root)
    if damage=='missing_process':assert m.inspect_acquisition_request(root)['availability']=='BLOCKED'
    else:
        with pytest.raises((ValueError,RuntimeError,KeyError)):m.inspect_acquisition_request(root)
    assert inventory(root)==before
