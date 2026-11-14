"""Request/recovery mechanics use synthetic workers, not chemical qualification."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
from nasolve.campaign_records import read_record, write_record
from nasolve.campaign_process import CampaignProcessError
from nasolve.campaigns import CampaignError

pytestmark=pytest.mark.skipif(os.name!='posix',reason='Owned repair requires POSIX')


def inventory(root):
    return {str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def setup(tmp_path,monkeypatch):
    from nasolve import cif_repair_attempt as m
    from nasolve.cif_repair_process import PreparedRepairProcesses
    source=tmp_path/'source';source.mkdir();(source/'source.cif').write_text('EXACT SOURCE')
    (source/'bundle_receipt.json').write_text('{"consumer":{"test":"consumer"}}')
    sdk=tmp_path/'sdk';sdk.mkdir()
    phenix=SimpleNamespace(root=sdk,version='TEST',executables={'phenix.ready_set':sdk/'ready'},environment={})
    calls=[]
    def prepared(p):return {'report':json.loads((Path(p)/'bundle_receipt.json').read_bytes())}
    def execute(bundle,phenix,output,**kwargs):
        output.mkdir();shutil.copytree(bundle,output/'bundle');calls.append(output)
        o=PreparedRepairProcesses(output,attempt_identity=kwargs['_attempt_identity'])
        work=output/'original-gradient/job';work.mkdir(parents=True)
        o.runner('original-gradient')([sys.executable,'-c',"from pathlib import Path;Path('partial').write_text('retained')"],
            cwd=work,log_path=work/'gradient.log',environment=dict(os.environ),timeout_seconds=3)
        o.finish('RETURNED');r={'status':'SYNTHETIC_NOT_CHEMICAL_QUALIFICATION'}
        (output/'repair_execution.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'verify_current_consumer',lambda *a:True)
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    return m,(source,phenix,tmp_path/'request'),{'total_timeout_seconds':10,'max_attempts':2},calls


def test_fresh_attempts_preserve_prior_output_and_frozen_allowance(setup):
    m,args,options,calls=setup
    first=m.execute_prepared_dictionary_repair_attempt(*args,**options)
    root=args[-1];before=inventory(root/'attempts/attempt-0001')
    second=m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert first['request_id']==second['request_id'] and first['attempt_id']!=second['attempt_id']
    assert second['attempt_number']==2 and inventory(root/'attempts/attempt-0001')==before
    assert second['execution_directory']=={'anchor':'request_directory','path':'attempts/attempt-0002/execution'}
    assert m.inspect_prepared_repair_request(root)['availability']=='EXHAUSTED'
    before=inventory(root)
    with pytest.raises(CampaignProcessError,match='exhausted'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert len(calls)==2 and inventory(root)==before


def test_inspection_is_non_mutating_and_never_authorizes_retry(setup):
    m,args,options,calls=setup;root=args[-1]
    state=m.inspect_prepared_repair_request(root)
    assert state['state']=='NOT_RECORDED' and not root.exists() and not state['retry_authorized']
    m.execute_prepared_dictionary_repair_attempt(*args,**options);before=inventory(root)
    state=m.inspect_prepared_repair_request(root)
    assert state['availability']=='AVAILABLE' and state['attempts'][0]['state']=='STOPPED'
    assert not state['retry_authorized'] and inventory(root)==before


@pytest.mark.parametrize('field',['source','total','phase','allowance'])
def test_changed_request_refuses_before_new_attempt(setup,field):
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    before=inventory(args[-1]);options=dict(options)
    if field=='source':(args[0]/'source.cif').write_text('CHANGED')
    elif field=='total':options['total_timeout_seconds']=11
    elif field=='phase':options['native_timeout_seconds']=5
    else:options['max_attempts']=3
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert len(calls)==1 and inventory(args[-1])==before


@pytest.mark.parametrize('option,value',[('max_attempts',0),('max_attempts',6),('max_attempts',True),
 ('total_timeout_seconds',None),('total_timeout_seconds',0),('total_timeout_seconds',3601),
 ('total_timeout_seconds',True),('native_timeout_seconds',601),('attribution_timeout_seconds',301),
 ('derivative_timeout_seconds',float('nan'))])
def test_invalid_limits_leave_no_request(setup,option,value):
    m,args,options,calls=setup;options=dict(options);options[option]=value
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert not args[-1].exists() and not calls


@pytest.mark.parametrize('member',['unrelated','inputs','request.lock','request.json'])
def test_invalid_existing_destination_is_preserved(setup,member):
    m,args,options,calls=setup;root=args[-1];root.mkdir()
    if member in {'request.lock','request.json'}:(root/member).mkdir()
    elif member=='inputs':(root/member).write_text('unrelated')
    else:(root/member).write_text('user file')
    before=inventory(root);names=sorted(p.name for p in root.iterdir())
    with pytest.raises((ValueError,CampaignError)):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert inventory(root)==before and sorted(p.name for p in root.iterdir())==names and not calls


@pytest.mark.parametrize('kind',['source-child','source-parent','sdk','sdk-dot','symlink'])
def test_containment_and_symlinks_refuse_before_reservation(setup,tmp_path,kind):
    m,args,options,calls=setup;source,sdk,root=args
    if kind=='source-child':root=source/'request'
    elif kind=='source-parent':root=source.parent
    elif kind=='sdk':root=sdk.root/'request'
    elif kind=='sdk-dot':root=sdk.root/'missing/../request'
    else:root=tmp_path/'link';root.symlink_to(tmp_path/'absent',target_is_directory=True)
    before=inventory(tmp_path)
    with pytest.raises((ValueError,CampaignError)):m.execute_prepared_dictionary_repair_attempt(source,sdk,root,**options)
    assert inventory(tmp_path)==before and not calls


@pytest.mark.parametrize('failure',['before-output','after-worker','partial-preparation'])
def test_exception_preserves_partial_and_seals_only_known_execution(setup,monkeypatch,failure):
    m,args,options,calls=setup;execute=m.execute_prepared_dictionary_repair
    def interrupted(*a,**kw):
        if failure=='after-worker':execute(*a,**kw)
        elif failure=='partial-preparation':a[2].mkdir();(a[2]/'partial').write_text('keep')
        raise KeyboardInterrupt('interrupted')
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',interrupted)
    with pytest.raises(KeyboardInterrupt):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    state=m.inspect_prepared_repair_request(args[-1])
    if failure=='partial-preparation':
        assert state['availability']=='BLOCKED' and not (args[-1]/'attempts/attempt-0001/finished.json').exists()
        monkeypatch.setattr(m,'coordinator_alive',lambda identity:False)
        assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'
    else:
        assert state['availability']=='AVAILABLE' and state['attempts'][0]['finished']['outcome']=='RAISED'
    if failure=='after-worker':assert (args[-1]/'attempts/attempt-0001/execution/original-gradient/job/partial').read_text()=='retained'


@pytest.mark.parametrize('target',['request','attempt','completion'])
def test_publication_gaps_preserved_without_repair_in_place(setup,monkeypatch,target):
    m,args,options,calls=setup;write=m.write_record
    def broken(path,value,**kw):
        if path.name=={'request':'request.json','attempt':'attempt.json','completion':'finished.json'}[target]:
            raise OSError('publication failed')
        return write(path,value,**kw)
    monkeypatch.setattr(m,'write_record',broken)
    with pytest.raises(OSError,match='publication failed'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    before=inventory(args[-1]);state=m.inspect_prepared_repair_request(args[-1])
    assert state['availability']=='BLOCKED'
    with pytest.raises(CampaignProcessError):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert inventory(args[-1])==before


@pytest.mark.parametrize('damage',['source','receipt','binding','copied-execution','missing-owner','coordinator','gap','unknown-policy','symlink','extra'])
def test_inconsistent_or_copied_evidence_cannot_authorize_retry(setup,monkeypatch,damage):
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    root=args[-1];attempt=root/'attempts/attempt-0001';execution=attempt/'execution'
    if damage=='source':(root/'inputs/bundle/source.cif').write_text('different')
    elif damage=='receipt':(execution/'repair_execution.json').write_text('{}')
    elif damage=='gap':attempt.rename(root/'attempts/attempt-0002')
    elif damage=='symlink':
        p=root/'inputs/bundle/source.cif';p.unlink();p.symlink_to(args[0]/'source.cif')
    elif damage=='extra':(attempt/'untracked').write_text('unknown')
    elif damage=='copied-execution':
        m.execute_prepared_dictionary_repair_attempt(*args,**options)
        second=root/'attempts/attempt-0002';(second/'finished.json').unlink()
        shutil.rmtree(second/'execution');shutil.copytree(execution,second/'execution')
    else:
        path=root/'request.json' if damage=='unknown-policy' else execution/'ownership/repair.json' if damage in {'missing-owner','coordinator'} else attempt/'finished.json'
        record=read_record(path)
        if damage=='unknown-policy':record['policy_id']='unrecognized'
        elif damage=='missing-owner':record.pop('attempt_owner')
        elif damage=='coordinator':record['coordinator']['pid']+=1
        else:record['process_records']['header']='b'*64
        write_record(path,record,replace=True)
    before=inventory(root);count=len(calls)
    with pytest.raises((ValueError,CampaignError)):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert len(calls)==count and inventory(root)==before


def test_live_outer_caller_blocks_even_when_inner_execution_is_sealed(setup,monkeypatch):
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    first=args[-1]/'attempts/attempt-0001';(first/'finished.json').unlink()
    assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'
    before=inventory(first)
    with pytest.raises(CampaignProcessError,match='unresolved'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    monkeypatch.setattr(m,'coordinator_alive',lambda identity:False)
    assert m.inspect_prepared_repair_request(args[-1])['availability']=='AVAILABLE'
    result=m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert result['attempt_number']==2 and inventory(first)==before
    assert not (first/'finished.json').exists()


def test_dead_coordinator_precedes_execution_snapshot(setup,monkeypatch):
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    attempt=args[-1]/'attempts/attempt-0001';(attempt/'finished.json').unlink()
    shutil.rmtree(attempt/'execution')
    def exit_before_snapshot(identity):
        (attempt/'execution').mkdir(exist_ok=True)
        return False
    monkeypatch.setattr(m,'coordinator_alive',exit_before_snapshot)
    assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'


def test_relocation_preserves_request_identity_and_inspection_is_cold(setup,tmp_path,monkeypatch):
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    relocated=args[-1].rename(tmp_path/'relocated');moved=args[0].rename(tmp_path/'moved-source')
    assert not args[-1].exists() and not args[0].exists()
    with monkeypatch.context() as patch:
        patch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Reader executed a command'))
        before=inventory(relocated);state=m.inspect_prepared_repair_request(relocated)
        assert state['availability']=='AVAILABLE' and inventory(relocated)==before
    result=m.execute_prepared_dictionary_repair_attempt(moved,args[1],relocated,**options)
    assert result['request_id']==state['request']['request_id'] and result['attempt_number']==2


@pytest.mark.parametrize('damage',['caller-source','frozen-source','consumer'])
def test_changed_inputs_during_execution_preserve_error_and_output(setup,monkeypatch,damage):
    m,args,options,calls=setup;execute=m.execute_prepared_dictionary_repair
    def mutate(*a,**kw):
        result=execute(*a,**kw)
        if damage=='caller-source':(args[0]/'source.cif').write_text('changed')
        elif damage=='frozen-source':(a[0]/'source.cif').write_text('changed')
        else:monkeypatch.setattr(m,'verify_current_consumer',lambda *a:False)
        return result
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',mutate)
    with pytest.raises(ValueError,match='changed'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert (args[-1]/'attempts/attempt-0001/execution/original-gradient/job/partial').exists()


@pytest.mark.parametrize('identity',[{}, {'attempt_id':'bad'}, {'request_sha256':'a'*64,'attempt_sha256':'b'*64,'attempt_id':'invalid'}])
def test_bad_attempt_binding_refuses_before_prepared_output(tmp_path,identity):
    from nasolve.cif_prepared_repair_execution import execute_prepared_dictionary_repair
    with pytest.raises(ValueError,match='attempt identity'):
        execute_prepared_dictionary_repair(tmp_path/'missing',None,tmp_path/'output',_attempt_identity=identity)
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('stage',['during-worker','after-worker','identity-gap'])
def test_actual_overlap_hard_kill_and_fresh_recovery(setup,tmp_path,stage):
    m,args,options,calls=setup
    controller = r"""import json,os,sys,time,shutil
from pathlib import Path
from types import SimpleNamespace
import nasolve.cif_repair_attempt as m
import nasolve.cif_repair_process as processes
source,request,control=map(Path,sys.argv[1:4]);stage=sys.argv[4]
sdk=SimpleNamespace(root=control/'sdk',executables={'phenix.ready_set':control/'sdk/ready'})
m.read_dictionary_bundle=lambda p:{'report':json.loads((Path(p)/'bundle_receipt.json').read_bytes())}
m.verify_current_consumer=lambda *a:True
write=processes.write_record
def publish(path,value,**kw):
 if stage=='identity-gap' and path.name=='process.json':
  (control/'identity-gap').touch();time.sleep(10)
 return write(path,value,**kw)
processes.write_record=publish
def execute(bundle,phenix,output,**kw):
 output.mkdir();shutil.copytree(bundle,output/'bundle')
 owner=processes.PreparedRepairProcesses(output,attempt_identity=kw['_attempt_identity'])
 work=output/'original-gradient/job';work.mkdir(parents=True)
 worker="from pathlib import Path;import time;Path('partial').write_text('preserved');end=time.monotonic()+8\nwhile not Path("+repr(str(control/'release'))+").exists() and time.monotonic()<end:time.sleep(.02)\n"
 if stage=='after-worker':worker="from pathlib import Path;Path('partial').write_text('preserved')"
 owner.runner('original-gradient')([sys.executable,'-c',worker],cwd=work,log_path=work/'gradient.log',environment=dict(os.environ),timeout_seconds=10)
 owner.finish('RETURNED');(control/'after-worker').touch();time.sleep(10)
m.execute_prepared_dictionary_repair=execute
m.execute_prepared_dictionary_repair_attempt(source,sdk,request,total_timeout_seconds=10,max_attempts=2)
"""
    with (tmp_path/'controller.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-c',controller,str(args[0]),str(args[-1]),str(tmp_path),stage],stdout=log,stderr=log)
        try:
            execution=args[-1]/'attempts/attempt-0001/execution'
            ready=tmp_path/stage if stage!='during-worker' else execution/'ownership/phases/original-gradient/process.json'
            end=time.monotonic()+5
            while not (ready.exists() and (execution/'original-gradient/job/partial').exists()):
                assert process.poll() is None and time.monotonic()<end,(tmp_path/'controller.log').read_text();time.sleep(.02)
            assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'
            inode=(args[-1]/'request.lock').stat().st_ino
            with pytest.raises(CampaignProcessError,match='lock busy'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
            process.kill();process.wait(timeout=3)
            if stage!='after-worker':assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'
            (tmp_path/'release').touch()
            if stage=='identity-gap':
                time.sleep(.15)
                assert m.inspect_prepared_repair_request(args[-1])['availability']=='BLOCKED'
                with pytest.raises(CampaignProcessError,match='unresolved'):m.execute_prepared_dictionary_repair_attempt(*args,**options)
            else:
                end=time.monotonic()+5
                while m.inspect_prepared_repair_request(args[-1])['availability']!='AVAILABLE' and time.monotonic()<end:time.sleep(.02)
                first=args[-1]/'attempts/attempt-0001';before=inventory(first)
                result=m.execute_prepared_dictionary_repair_attempt(*args,**options)
                assert result['attempt_number']==2 and inventory(first)==before and not (first/'finished.json').exists()
            assert (args[-1]/'request.lock').stat().st_ino==inode
        finally:
            (tmp_path/'release').touch()
            if process.poll() is None:process.kill()
            process.wait(timeout=3)


def test_outer_parent_and_allowance_preserve_one_prepared_request(setup):
    m,args,options,calls=setup
    parent=dict(request_sha256='a'*64,attempt_sha256='b'*64,attempt_id='11111111-1111-1111-1111-111111111111')
    first=m.execute_prepared_dictionary_repair_attempt(*args,**options,_parent_attempt_identity=parent,_remaining_seconds=lambda:8)
    initial=inventory(args[-1]/'attempts/attempt-0001')
    next_parent=dict(parent,attempt_sha256='c'*64,attempt_id='22222222-2222-2222-2222-222222222222')
    second=m.execute_prepared_dictionary_repair_attempt(*args,**options,_parent_attempt_identity=next_parent,_remaining_seconds=lambda:6)
    state=m.inspect_prepared_repair_request(args[-1])
    assert [row['intent']['parent_attempt'] for row in state['attempts']]==[parent,next_parent]
    assert first['request_id']==second['request_id'] and second['attempt_number']==2
    assert state['request']['configuration']['limits']['total_timeout_seconds']==10
    assert inventory(args[-1]/'attempts/attempt-0001')==initial


@pytest.mark.parametrize('parent',[False,{},{'request_sha256':'a'*64,'attempt_sha256':'b'*64,'attempt_id':'bad'},{'request_sha256':'x'*64,'attempt_sha256':'b'*64,'attempt_id':'11111111-1111-1111-1111-111111111111'}])
def test_invalid_enclosing_identity_never_reserves(setup,parent):
    m,args,options,calls=setup
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,**options,_parent_attempt_identity=parent)
    assert not args[-1].exists() and not calls


@pytest.mark.parametrize('value',[True,None,'10',float('nan'),float('inf'),0,-1])
def test_invalid_or_expired_enclosing_allowance_never_reserves(setup,value):
    m,args,options,calls=setup
    with pytest.raises((ValueError,TimeoutError)):m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=lambda:value)
    assert not args[-1].exists() and not calls


def test_noncallable_enclosing_allowance_refuses(setup):
    m,args,options,calls=setup
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=10)
    assert not args[-1].exists() and not calls


def test_parent_claim_is_detached_before_callback(setup):
    m,args,options,calls=setup
    parent=dict(request_sha256='a'*64,attempt_sha256='b'*64,attempt_id='11111111-1111-1111-1111-111111111111');expected=dict(parent)
    def allowance():parent['attempt_id']='changed by caller';return 20
    m.execute_prepared_dictionary_repair_attempt(*args,**options,_parent_attempt_identity=parent,_remaining_seconds=allowance)
    assert m.inspect_prepared_repair_request(args[-1])['attempts'][0]['intent']['parent_attempt']==expected


@pytest.mark.parametrize('value',[None,False,{},{'request_sha256':'a'*64,'attempt_sha256':'b'*64,'attempt_id':'bad'}])
def test_readback_rejects_malformed_parent_claim(setup,value):
    from nasolve.campaign_records import read_record,write_record
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    p=args[-1]/'attempts/attempt-0001/attempt.json';r=read_record(p);r['parent_attempt']=value;write_record(p,r,replace=True)
    before=inventory(args[-1])
    with pytest.raises(ValueError):m.inspect_prepared_repair_request(args[-1])
    assert inventory(args[-1])==before


def test_parent_expiry_during_preflight_keeps_destination_absent(setup,monkeypatch):
    m,args,options,calls=setup;cap=[8]
    def verify(*a):cap[0]=0;return True
    monkeypatch.setattr(m,'verify_current_consumer',verify)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=lambda:cap[0])
    assert not args[-1].exists() and not calls


def test_parent_expiry_after_native_return_seals_failure_and_preserves_outputs(setup,monkeypatch):
    m,args,options,calls=setup;cap=[8];execute=m.execute_prepared_dictionary_repair
    def late(*a,**k):r=execute(*a,**k);cap[0]=0;return r
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',late)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=lambda:cap[0])
    state=m.inspect_prepared_repair_request(args[-1]);row=state['attempts'][0]
    assert row['state']=='STOPPED' and row['finished']['outcome']=='RAISED'
    assert (args[-1]/'attempts/attempt-0001/execution/repair_execution.json').exists()
    old=inventory(args[-1]/'attempts/attempt-0001');monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute);cap[0]=6
    assert m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=lambda:cap[0])['attempt_number']==2
    assert inventory(args[-1]/'attempts/attempt-0001')==old


def test_execution_receives_live_parent_clock_without_changing_frozen_limits(setup,monkeypatch):
    m,args,options,calls=setup;clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0]);execute=m.execute_prepared_dictionary_repair;seen=[]
    def observe(*a,**k):
        assert k['total_timeout_seconds']==10
        seen.append(k['_remaining_seconds']());clock[0]=2;seen.append(k['_remaining_seconds']())
        return execute(*a,**k)
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',observe)
    m.execute_prepared_dictionary_repair_attempt(*args,**options,_remaining_seconds=lambda:8)
    assert seen==[8,6]


@pytest.mark.parametrize('enabled',[False,True])
def test_no_repair_mode_is_frozen_and_bound_to_execution(setup,monkeypatch,enabled):
    m,args,options,calls=setup;old=m.execute_prepared_dictionary_repair
    def execute(*a,**k):
        assert k.get('qualify_no_repair',False) is enabled
        result=old(*a,**k)
        if enabled:result['qualify_no_repair']=True
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    m.execute_prepared_dictionary_repair_attempt(*args,qualify_no_repair=enabled,**options)
    root=args[-1];config=read_record(root/'request.json')['configuration']
    assert config.get('qualify_no_repair',False) is enabled
    if not enabled:assert 'qualify_no_repair' not in config
    before=inventory(root)
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,qualify_no_repair=not enabled,**options)
    assert inventory(root)==before and len(calls)==1


@pytest.mark.parametrize('reported',[False,None,1])
def test_execution_cannot_discard_or_weaken_frozen_no_repair_mode(setup,monkeypatch,reported):
    m,args,options,calls=setup;old=m.execute_prepared_dictionary_repair
    def execute(*a,**k):
        result=old(*a,**k)
        if reported is not None:result['qualify_no_repair']=reported
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    with pytest.raises(ValueError,match='mode'):m.execute_prepared_dictionary_repair_attempt(*args,qualify_no_repair=True,**options)
    assert not (args[-1]/'attempts/attempt-0001/finished.json').exists()
    assert (args[-1]/'attempts/attempt-0001/execution/repair_execution.json').exists()


@pytest.mark.parametrize('enabled',[False,True])
def test_optional_failure_policy_is_frozen_and_bound_to_execution(setup,monkeypatch,enabled):
    m,args,options,calls=setup;old=m.execute_prepared_dictionary_repair;policy=m.FALLBACK_POLICY_ID if enabled else None
    def execute(*a,**k):
        assert k.get('optional_failure_policy')==policy
        result=old(*a,**k)
        if enabled:result['optional_failure_policy']=policy
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    m.execute_prepared_dictionary_repair_attempt(*args,optional_failure_policy=policy,**options)
    root=args[-1];assert read_record(root/'request.json')['configuration'].get('optional_failure_policy')==policy
    before=inventory(root)
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair_attempt(*args,optional_failure_policy=None if enabled else m.FALLBACK_POLICY_ID,**options)
    assert inventory(root)==before and len(calls)==1


def test_execution_cannot_drop_frozen_optional_failure_policy(setup):
    m,args,options,calls=setup
    with pytest.raises(ValueError,match='policy'):m.execute_prepared_dictionary_repair_attempt(*args,optional_failure_policy=m.FALLBACK_POLICY_ID,**options)
    assert not (args[-1]/'attempts/attempt-0001/finished.json').exists()
