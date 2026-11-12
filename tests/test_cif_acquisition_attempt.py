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
        if kwargs.get('multiple_planes') is True:
            from nasolve.cif_source_candidate import MULTIPLE_PLANE_POLICY_ID
            context.update(multiple_planes=True,candidate_policy_id=MULTIPLE_PLANE_POLICY_ID)
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


def test_outer_parent_and_allowance_preserve_one_component_request(setup):
    from nasolve.campaign_records import read_record
    m,args,options,calls,generated=setup
    parent=dict(request_sha256='a'*64,attempt_sha256='b'*64,attempt_id='11111111-1111-1111-1111-111111111111')
    first=m.acquire_dictionary_attempt(*args,**options,_parent_attempt_identity=parent,_remaining_seconds=lambda:20)
    initial=inventory(args[-1]/'attempts/attempt-0001')
    next_parent=dict(parent,attempt_sha256='c'*64,attempt_id='22222222-2222-2222-2222-222222222222')
    second=m.acquire_dictionary_attempt(*args,**options,_parent_attempt_identity=next_parent,_remaining_seconds=lambda:10)
    state=m.inspect_acquisition_request(args[-1])
    assert [row['intent']['parent_attempt'] for row in state['attempts']]==[parent,next_parent]
    assert first['request_id']==second['request_id'] and second['attempt_number']==2 and len(generated)==1
    assert state['request']['configuration']['limits']['total_timeout_seconds']==30
    assert inventory(args[-1]/'attempts/attempt-0001')==initial
    assert m.read_acquisition_result(args[-1],2)['report']['status']=='REUSED'


@pytest.mark.parametrize('parent',[False,{},{'request_sha256':'a'*64,'attempt_sha256':'b'*64,'attempt_id':'bad'},{'request_sha256':'x'*64,'attempt_sha256':'b'*64,'attempt_id':'11111111-1111-1111-1111-111111111111'}])
def test_invalid_enclosing_identity_never_reserves(setup,parent):
    m,args,options,calls,generated=setup
    with pytest.raises(ValueError):m.acquire_dictionary_attempt(*args,**options,_parent_attempt_identity=parent)
    assert not args[-1].exists() and not calls


@pytest.mark.parametrize('value',[True,None,'10',float('nan'),float('inf'),0,-1])
def test_invalid_or_expired_enclosing_allowance_never_reserves(setup,value):
    m,args,options,calls,generated=setup
    with pytest.raises((ValueError,TimeoutError)):m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=lambda:value)
    assert not args[-1].exists() and not calls


def test_noncallable_enclosing_allowance_refuses(setup):
    m,args,options,calls,generated=setup
    with pytest.raises(ValueError):m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=10)
    assert not args[-1].exists() and not calls


def test_parent_claim_is_detached_before_callback(setup):
    m,args,options,calls,generated=setup
    parent=dict(request_sha256='a'*64,attempt_sha256='b'*64,attempt_id='11111111-1111-1111-1111-111111111111');expected=dict(parent)
    def allowance():parent['attempt_id']='changed by caller';return 20
    m.acquire_dictionary_attempt(*args,**options,_parent_attempt_identity=parent,_remaining_seconds=allowance)
    assert m.inspect_acquisition_request(args[-1])['attempts'][0]['intent']['parent_attempt']==expected


@pytest.mark.parametrize('value',[None,False,{},{'request_sha256':'a'*64,'attempt_sha256':'b'*64,'attempt_id':'bad'}])
def test_readback_rejects_malformed_parent_claim(setup,value):
    from nasolve.campaign_records import read_record,write_record
    m,args,options,calls,generated=setup;m.acquire_dictionary_attempt(*args,**options)
    p=args[-1]/'attempts/attempt-0001/attempt.json';r=read_record(p);r['parent_attempt']=value;write_record(p,r,replace=True)
    before=inventory(args[-1])
    with pytest.raises(ValueError):m.inspect_acquisition_request(args[-1])
    assert inventory(args[-1])==before


def test_parent_deadline_includes_preflight_and_cannot_refresh(setup,monkeypatch):
    m,args,options,calls,generated=setup;clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0]);configure=m._configuration
    def slow(*a,**k):r=configure(*a,**k);clock[0]=21.;return r
    monkeypatch.setattr(m,'_configuration',slow)
    with pytest.raises(TimeoutError):m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=lambda:20)
    assert not args[-1].exists() and not generated and not calls


def test_parent_expiry_after_generation_stops_qualification(setup,monkeypatch):
    m,args,options,calls,generated=setup;cap=[20];run=m.generate_source_candidate_attempt
    def expired(*a,**k):result=run(*a,**k);cap[0]=0;return result
    monkeypatch.setattr(m,'generate_source_candidate_attempt',expired)
    with pytest.raises(TimeoutError):m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=lambda:cap[0])
    state=m.inspect_acquisition_request(args[-1]);row=state['attempts'][0]
    assert row['state']=='STOPPED' and row['finished']['outcome']=='RAISED' and len(generated)==1 and not calls
    assert row['children']['qualification']['state']=='NOT_CREATED'
    assert (args[-1]/'generation/attempts/attempt-0001/generation/candidate.cif').exists()


def test_late_cache_result_is_retained_but_not_returned_as_success(setup,monkeypatch):
    m,args,options,calls,generated=setup;cap=[20];resolve=m.resolve_generated_dictionary
    def late(*a,**k):r=resolve(*a,**k);cap[0]=0;return r
    monkeypatch.setattr(m,'resolve_generated_dictionary',late)
    with pytest.raises(TimeoutError):m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=lambda:cap[0])
    row=m.inspect_acquisition_request(args[-1])['attempts'][0]
    assert row['state']=='STOPPED' and row['finished']['outcome']=='RAISED'
    assert (args[-1]/'attempts/attempt-0001/snapshot/resolution.json').exists()
    with pytest.raises(ValueError):m.read_acquisition_result(args[-1],1)
    old=inventory(args[-1]/'attempts/attempt-0001');monkeypatch.setattr(m,'resolve_generated_dictionary',resolve);cap[0]=10
    r=m.acquire_dictionary_attempt(*args,**options,_remaining_seconds=lambda:cap[0])
    assert r['attempt_number']==2 and r['acquisition']['status']=='REUSED' and len(generated)==1
    assert inventory(args[-1]/'attempts/attempt-0001')==old



def test_multiple_plane_generation_keeps_its_frozen_recipe_through_acquisition_and_cold_read(setup,tmp_path,monkeypatch):
    import shutil
    m,args,options,calls,generated=setup
    options['generation']['multiple_planes']=True
    first=m.acquire_dictionary_attempt(*args,**options)
    before=inventory(args[-1]/'attempts/attempt-0001')
    second=m.acquire_dictionary_attempt(*args,**options)
    assert len(generated)==1 and second['acquisition']['status']=='REUSED'
    assert inventory(args[-1]/'attempts/attempt-0001')==before
    state=m.inspect_acquisition_request(args[-1]);assert all(row['state']=='STOPPED' for row in state['attempts'])
    assert state['request']['configuration']['dictionary_request']['recipe']['multiple_planes'] is True
    moved=args[-1].rename(tmp_path/'relocated-request');shutil.rmtree(options['phenix'].root)
    args[0].unlink();shutil.rmtree(args[2])
    def forbidden(*a,**k):raise AssertionError('Cold acquisition read must not execute or write')
    monkeypatch.setattr('subprocess.Popen',forbidden);monkeypatch.setattr(m,'write_record',forbidden)
    before=inventory(moved)
    assert m.read_acquisition_result(moved,2)['report']['entry_id']==first['acquisition']['entry_id']
    assert inventory(moved)==before


@pytest.mark.parametrize('requested',[False,True])
def test_generation_child_cannot_add_or_drop_multiple_plane_choice(setup,monkeypatch,requested):
    m,args,options,calls,generated=setup
    if requested:options['generation']['multiple_planes']=True
    m.acquire_dictionary_attempt(*args,**options)
    original=m.inspect_source_generation_request
    def changed(path):
        state=original(path)
        if state['state']=='RECORDED':
            recipe=state['request']['configuration']['recipe']
            if requested:recipe.pop('multiple_planes')
            else:recipe['multiple_planes']=True
        return state
    monkeypatch.setattr(m,'inspect_source_generation_request',changed)
    before=inventory(args[-1])
    with pytest.raises(ValueError,match='Shared generation request identity differs'):
        m.inspect_acquisition_request(args[-1])
    assert inventory(args[-1])==before
