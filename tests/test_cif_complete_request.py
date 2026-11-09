"""Complete request ownership uses real frozen fixtures and synthetic repair transport."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json,shutil
import pytest
from nasolve.campaign_records import read_record,write_record
from tests.test_cif_repair_attempt import inventory


@pytest.fixture
def case(tmp_path,monkeypatch):
    from nasolve import cif_complete_request as m
    from nasolve import curated_ligands as ligands
    from nasolve import cif_repair_attempt as repair
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    from nasolve.cif_repair_process import PreparedRepairProcesses
    from tests.test_cif_dictionary_bundle import fixture
    ordinary=fixture(tmp_path);data=tmp_path/'data';(data/'ligands').mkdir(parents=True)
    sdkroot=tmp_path/'sdk';sdkroot.mkdir();sdk=SimpleNamespace(root=sdkroot,executables={'phenix.ready_set':sdkroot/'ready'},environment={},version='TEST')
    pin=dict(anchor='phenix_installation',path='api.py',sha256='1'*64,size=6)
    generations={};components=[]
    monkeypatch.setattr(ligands,'_registered_record',lambda code:{'Ligand code':code})
    for item in ordinary['components']:
        saved=resolve_dictionary_snapshot(item['snapshot']);code=saved['manifest']['request']['component']
        (data/'ligands'/f'{code}.cif').write_bytes(saved['source'].read_bytes())
        generation=dict(installation_root=sdkroot,python_executable=sdkroot/'python',elbow_executable=sdkroot/'elbow',api_sources=[pin],prior_sources=[pin],expected_dialect='CHEMICAL_COMPONENTS_CIF',phenix_version='TEST',environment={},bond_representation_policy=saved['manifest']['request']['recipe']['bond_representation_policy'])
        generations[code]=generation;components.append(dict(code=code,generation=generation,contexts=item['contexts'],retained_snapshot=item['snapshot']))
    sources=tmp_path/'sources';freeze_acquisition_sources(list(generations),sources,data_root=data)
    monkeypatch.setattr(m,'verify_current_consumer',lambda *a:True);monkeypatch.setattr(repair,'verify_current_consumer',lambda *a:True)
    calls=[]
    def execute(bundle,phenix,out,**kwargs):
        out.mkdir();shutil.copytree(bundle,out/'bundle');calls.append(out)
        owner=PreparedRepairProcesses(out,attempt_identity=kwargs['_attempt_identity']);owner.finish('RETURNED')
        result=dict(status='NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED')
        (out/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    args=dict(source_selection=sources,components=components,model=ordinary['model'],consumer=ordinary['consumer'],expected_links=ordinary['expected_links'],native_context=ordinary['native_context'],total_timeout_seconds=60,component_timeout_seconds=30,max_attempts=3)
    return m,args,tmp_path/'request',sdk,tmp_path/'store',generations,calls


def test_initialization_freezes_complete_intent_before_any_children(case):
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args)
    state=m.inspect_dictionary_request(root)
    assert state['availability']=='AVAILABLE' and state['attempts']==[] and state['retry_authorized'] is False
    assert not (root/'acquisitions').exists() and not store.exists() and not calls
    before=inventory(root);assert m.inspect_dictionary_request(root)==state and inventory(root)==before


def test_complete_attempts_reuse_persistent_children_and_preserve_parent_join(case):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    first=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    old=inventory(root/'attempts/attempt-0001')
    second=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    state=m.inspect_dictionary_request(root)
    assert first['attempt_number']==1 and second['attempt_number']==2 and first['attempt_id']!=second['attempt_id']
    assert all(row['state']=='STOPPED' for row in state['attempts']) and inventory(root/'attempts/attempt-0001')==old
    assert first['result']['automatic_adoption'] is False and 'NOT_ASSESSED' in first['result']['status']
    for code in generations:
        assert len(list((root/'acquisitions'/code/'attempts').iterdir()))==2
        assert not (root/'acquisitions'/code/'generation').exists()
    assert m.read_dictionary_request_result(root,1)['result']==first['result']


def test_changed_generation_identity_refuses_before_outer_reservation(case):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    changed=deepcopy(generations);changed[next(iter(changed))]['phenix_version']='OTHER';before=inventory(root)
    with pytest.raises(ValueError):m.execute_dictionary_request_attempt(root,sdk,store,generation=changed)
    assert inventory(root)==before and not (root/'attempts').exists() and not calls


@pytest.mark.parametrize('field,value',[('max_attempts',True),('max_attempts',0),('max_attempts',6),
 ('total_timeout_seconds',True),('total_timeout_seconds',0),('total_timeout_seconds',3601),
 ('component_timeout_seconds',3601),('native_timeout_seconds',601),('attribution_timeout_seconds',301),
 ('derivative_timeout_seconds',float('nan'))])
def test_bad_limits_never_publish_intent_or_start_children(case,field,value):
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args[field]=value
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and not (root/'acquisitions').exists() and not calls
    if root.exists():assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'


@pytest.mark.parametrize('change',['duplicate','missing','wrong-site','extra-source','model-bytes'])
def test_incomplete_or_changed_frozen_inputs_refuse_without_native_work(case,change):
    m,args,root,sdk,store,generations,calls=case;args=deepcopy(args)
    if change=='duplicate':args['components'][1]=deepcopy(args['components'][0])
    elif change=='missing':args['components'].pop()
    elif change=='wrong-site':args['components'][0]['contexts'][0]['site']='Z:999'
    if change in {'duplicate','missing','wrong-site'}:
        with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**args)
    else:
        m.initialize_dictionary_request(output=root,**args)
        if change=='extra-source':(root/'inputs/unknown.cif').write_text('unrequested')
        else:
            p=root/'inputs/model.pdb';p.write_text(p.read_text()+'REMARK altered\n')
        before=inventory(root)
        with pytest.raises(ValueError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
        assert inventory(root)==before
    assert not (root/'attempts').exists() and not calls


@pytest.mark.parametrize('where',['source','retained','model','existing','symlink'])
def test_initializer_refuses_overlaps_and_preserves_originals(case,tmp_path,where):
    m,args,root,sdk,store,generations,calls=case
    if where=='source':root=args['source_selection']/'request'
    elif where=='retained':root=args['components'][0]['retained_snapshot']/'request'
    elif where=='model':root=Path(args['model']).parent
    elif where=='existing':root.mkdir();(root/'keep').write_text('keep')
    else:root.symlink_to(tmp_path/'absent',target_is_directory=True)
    before=inventory(tmp_path)
    with pytest.raises((ValueError,FileExistsError)):m.initialize_dictionary_request(output=root,**args)
    assert inventory(tmp_path)==before and not calls


@pytest.mark.parametrize('binding',['cache-child','cache-parent','sdk','generator','consumer'])
def test_wrong_runtime_bindings_do_not_reserve_attempts(case,monkeypatch,binding):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    if binding=='cache-child':store=root/'store'
    elif binding=='cache-parent':store=root.parent
    elif binding=='sdk':sdk=SimpleNamespace(root=root,executables=sdk.executables)
    elif binding=='generator':
        generations=deepcopy(generations);g=generations[next(iter(generations))];g.update(installation_root=root,python_executable=root/'python',elbow_executable=root/'elbow')
    else:monkeypatch.setattr(m,'verify_current_consumer',lambda *a:False)
    before=inventory(root)
    with pytest.raises(ValueError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and not calls


def test_shared_allowance_expiry_preserves_completed_child_then_fresh_recovery(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    tick=[0.];acquire=m.acquisition.acquire_dictionary_attempt
    monkeypatch.setattr(m,'monotonic',lambda:tick[0])
    def expire(*a,**kw):
        assert 0<kw['_remaining_seconds']()<=60
        result=acquire(*a,**kw);tick[0]=61.;return result
    with monkeypatch.context() as patch:
        patch.setattr(m.acquisition,'acquire_dictionary_attempt',expire)
        with pytest.raises(TimeoutError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    state=m.inspect_dictionary_request(root);assert state['availability']=='AVAILABLE'
    assert state['attempts'][0]['finished']['outcome']=='RAISED' and not calls
    old=inventory(root/'attempts/attempt-0001');code=next(iter(state['request']['configuration']['components']))
    child=inventory(root/'acquisitions'/code/'attempts/attempt-0001')
    tick[0]=100.;result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert result['attempt_number']==2 and result['result']['selected_attempts'][code]==2
    assert inventory(root/'attempts/attempt-0001')==old and inventory(root/'acquisitions'/code/'attempts/attempt-0001')==child


@pytest.mark.parametrize('phase',['request','attempt','completion'])
def test_publication_interruptions_never_repair_history_in_place(case,monkeypatch,phase):
    m,args,root,sdk,store,generations,calls=case;write=m.write_record
    def broken(path,value,**kw):
        if path.name=={'request':'request.json','attempt':'attempt.json','completion':'finished.json'}[phase]:raise OSError('publication interrupted')
        return write(path,value,**kw)
    if phase=='request':
        with monkeypatch.context() as patch:
            patch.setattr(m,'write_record',broken)
            with pytest.raises(OSError):m.initialize_dictionary_request(output=root,**args)
        before=inventory(root)
        with pytest.raises(FileExistsError):m.initialize_dictionary_request(output=root,**args)
        assert inventory(root)==before and m.inspect_dictionary_request(root)['availability']=='BLOCKED';return
    m.initialize_dictionary_request(output=root,**args)
    with monkeypatch.context() as patch:
        patch.setattr(m,'write_record',broken)
        with pytest.raises(OSError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    old=inventory(root/'attempts/attempt-0001');monkeypatch.setattr(m,'coordinator_alive',lambda _:False)
    if phase=='attempt':
        assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'
        from nasolve.campaign_process import CampaignProcessError
        with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    else:
        assert m.inspect_dictionary_request(root)['attempts'][0]['state']=='STOPPED_UNFINISHED'
        assert m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)['attempt_number']==2
        assert not (root/'attempts/attempt-0001/finished.json').exists()
    assert inventory(root/'attempts/attempt-0001')==old


@pytest.mark.parametrize('activity',[True,None,False])
def test_unsealed_owner_must_be_known_dead_before_fresh_attempt(case,monkeypatch,activity):
    from nasolve.campaign_process import current_process_identity,CampaignProcessError
    import uuid
    m,args,root,sdk,store,generations,calls=case;request=m.initialize_dictionary_request(output=root,**args)
    attempt=root/'attempts/attempt-0001';attempt.mkdir(parents=True)
    write_record(attempt/'attempt.json',dict(request_sha256=request['record_sha256'],number=1,attempt_id=str(uuid.uuid4()),coordinator=current_process_identity(),created_utc='test'))
    monkeypatch.setattr(m,'coordinator_alive',lambda _:activity);before=inventory(attempt)
    if activity is False:
        assert m.inspect_dictionary_request(root)['availability']=='AVAILABLE'
        assert m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)['attempt_number']==2
    else:
        assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'
        with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
        assert not calls
    assert inventory(attempt)==before and not (attempt/'finished.json').exists()


def test_unknown_component_publication_stays_blocked_even_after_coordinator_exit(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    def partial(*a,**kw):a[3].mkdir(parents=True);(a[3]/'inputs').mkdir();raise KeyboardInterrupt('partial child request')
    monkeypatch.setattr(m.acquisition,'acquire_dictionary_attempt',partial)
    with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    monkeypatch.setattr(m,'coordinator_alive',lambda _:False)
    assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'
    assert not (root/'attempts/attempt-0001/finished.json').exists() and not calls


def test_missing_or_foreign_child_owner_cannot_hide_behind_valid_child_digest(case,monkeypatch):
    import uuid
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    acquire=m.acquisition.acquire_dictionary_attempt
    def interrupt(*a,**kw):acquire(*a,**kw);raise KeyboardInterrupt('between components')
    monkeypatch.setattr(m.acquisition,'acquire_dictionary_attempt',interrupt)
    with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    outer=root/'attempts/attempt-0001';(outer/'finished.json').unlink()
    child=next((root/'acquisitions').iterdir())/'attempts/attempt-0001';(child/'finished.json').unlink()
    original=read_record(child/'attempt.json')
    for kind in ('missing','foreign','coordinator'):
        altered=deepcopy(original)
        if kind=='missing':altered.pop('parent_attempt')
        elif kind=='foreign':altered['parent_attempt']['attempt_id']=str(uuid.uuid4())
        else:altered['coordinator']['pid']+=1
        write_record(child/'attempt.json',altered,replace=True)
        with pytest.raises(ValueError):m.inspect_dictionary_request(root)


def test_exhausted_outer_request_preserves_every_attempt(case):
    from nasolve.campaign_process import CampaignProcessError
    m,args,root,sdk,store,generations,calls=case;args=dict(args,max_attempts=1)
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert m.inspect_dictionary_request(root)['availability']=='EXHAUSTED';before=inventory(root)
    with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and len(calls)==1


def test_success_readback_rejects_modified_output_and_invented_result_claim(case):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root);assert m.read_dictionary_request_result(root,1)['runtime'] is None and inventory(root)==before
    result=root/'attempts/attempt-0001/result.json';r=read_record(result);r['automatic_adoption']=True;write_record(result,r,replace=True)
    with pytest.raises(ValueError):m.read_dictionary_request_result(root,1)


def test_frozen_request_runs_after_original_sources_are_absent(case):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    shutil.rmtree(args['source_selection']);Path(args['model']).unlink()
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert m.read_dictionary_request_result(root,result['attempt_number'])['result']==result['result']



def test_generation_limit_is_shared_across_failed_outer_attempts(case,monkeypatch):
    import os,sys
    from hashlib import sha256
    from nasolve import cif_generation_attempt as generator
    from nasolve.cif_generation_process import run_generation_command
    m,args,root,sdk,store,generations,calls=case;code=sorted(generations)[0]
    for name in ('python','elbow','api.py'):(sdk.root/name).write_text(name)
    pin=dict(anchor='phenix_installation',path='api.py',sha256=sha256(b'api.py').hexdigest(),size=6)
    for g in generations.values():g.update(api_sources=[pin],prior_sources=[pin],max_attempts=2,timeout_seconds=5)
    for item in args['components']:
        if item['code']==code:item.pop('retained_snapshot')
    generated=[]
    def generate(sdkroot,python,elbow,api,source,component,output,**kwargs):
        output.mkdir();generated.append(output)
        context=dict(component=component,source_sha256=sha256(source.read_bytes()).hexdigest(),attempt_owner=kwargs['attempt_identity'])
        run_generation_command([sys.executable,'-c','print("synthetic generation ownership")'],output,phase='candidate',environment=dict(os.environ),timeout_seconds=kwargs['timeout_seconds'],context=context)
        target=output/'candidate.cif';target.write_bytes(source.read_bytes())
        report=dict(schema_version=1,status='CANDIDATE_REVIEW',component=component,source_sha256=sha256(source.read_bytes()).hexdigest(),source_preserved=True,candidate_retained=True,candidate=dict(anchor='candidate_directory',path='candidate.cif',sha256=sha256(target.read_bytes()).hexdigest(),size=target.stat().st_size),execution={'status':'COMPLETED'},stopping={'status':'NOT_REPORTED'})
        (output/'source_candidate_receipt.json').write_text(json.dumps(report));return report
    def refuse(*a,**kw):raise ValueError('synthetic consumer refusal')
    monkeypatch.setattr(generator,'generate_source_candidate',generate)
    monkeypatch.setattr(m.acquisition,'execute_candidate_qualification',refuse)
    m.initialize_dictionary_request(output=root,**args)
    for i in (1,2):
        with pytest.raises(ValueError,match='synthetic consumer refusal'):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
        assert m.inspect_dictionary_request(root)['attempts'][i-1]['finished']['outcome']=='RAISED'
    preserved=inventory(root/'acquisitions'/code/'generation')
    with pytest.raises(ValueError,match='blocked or exhausted'):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert len(generated)==2 and inventory(root/'acquisitions'/code/'generation')==preserved and not calls
    assert m.inspect_dictionary_request(root)['availability']=='EXHAUSTED'


def test_changing_original_while_freezing_cannot_publish_complete_request(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case;freeze=m._freeze
    def changing(*a,**kw):
        freeze(*a,**kw);p=Path(args['model']);p.write_text(p.read_text()+'REMARK changed during freezing\n')
    monkeypatch.setattr(m,'_freeze',changing)
    with pytest.raises(ValueError,match='source changed while freezing'):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and m.inspect_dictionary_request(root)['availability']=='BLOCKED' and not calls



def test_expiry_during_final_seal_withholds_outer_success(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    tick=[0.];capture=m._attempt_files
    monkeypatch.setattr(m,'monotonic',lambda:tick[0])
    def late(attempt):
        result=capture(attempt);tick[0]=61.;return result
    monkeypatch.setattr(m,'_attempt_files',late)
    with pytest.raises(TimeoutError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    state=m.inspect_dictionary_request(root)
    assert state['attempts'][0]['finished']['outcome']=='RAISED' and state['availability']=='AVAILABLE'
    assert (root/'attempts/attempt-0001/result.json').exists() and len(calls)==1


def test_overlapping_outer_writer_refuses_without_another_attempt(case):
    from nasolve.campaign_process import CampaignProcessError,exclusive_lock
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    with exclusive_lock(root/'request.lock'):
        before=inventory(root)
        with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
        assert inventory(root)==before and not calls


def test_expiry_in_preflight_never_reserves_an_outer_attempt(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    tick=[0.];monkeypatch.setattr(m,'monotonic',lambda:tick[0])
    def slow(*a):tick[0]=61.;return True
    monkeypatch.setattr(m,'verify_current_consumer',slow);before=inventory(root)
    with pytest.raises(TimeoutError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and not calls



def test_unresolved_cleanup_preserves_exception_without_note_support(case,monkeypatch):
    class LegacyInterrupt(BaseException):
        add_note=None
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    def partial(*a,**kw):a[3].mkdir(parents=True);raise LegacyInterrupt('retain original failure')
    monkeypatch.setattr(m.acquisition,'acquire_dictionary_attempt',partial)
    with pytest.raises(LegacyInterrupt,match='retain original failure'):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert m.inspect_dictionary_request(root)['availability']=='BLOCKED' and not calls



def test_unknown_shared_generation_blocks_outer_reservation(case,monkeypatch):
    from nasolve.campaign_process import CampaignProcessError
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    acquire=m.acquisition.acquire_dictionary_attempt
    def stop(*a,**kw):acquire(*a,**kw);raise KeyboardInterrupt('between components')
    with monkeypatch.context() as patch:
        patch.setattr(m.acquisition,'acquire_dictionary_attempt',stop)
        with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    component=next((root/'acquisitions').iterdir());(component/'generation').mkdir()
    assert m.acquisition.inspect_acquisition_request(component)['availability']=='BLOCKED'
    before=inventory(root)
    assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'
    with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and not (root/'attempts/attempt-0002').exists() and not calls



@pytest.mark.parametrize('bound',['files','bytes'])
def test_completion_must_fit_frozen_artifact_bounds_before_success(case,monkeypatch,bound):
    from nasolve import cif_component_runtime as frozen_tree
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    capture=m._attempt_files
    def no_headroom(attempt):
        result=capture(attempt)
        if bound=='files':monkeypatch.setattr(frozen_tree,'MAX_FILES',len(result['files']))
        else:monkeypatch.setattr(frozen_tree,'MAX_BYTES',sum(r['size'] for r in result['files'].values()))
        return result
    monkeypatch.setattr(m,'_attempt_files',no_headroom)
    with pytest.raises(ValueError,match='completion exceeds frozen artifact bounds'):
        m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert not (root/'attempts/attempt-0001/finished.json').exists()
    assert (root/'attempts/attempt-0001/result.json').exists() and len(calls)==1
