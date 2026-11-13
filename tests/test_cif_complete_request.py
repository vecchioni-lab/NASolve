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
    # This historical ownership fixture retains its original unpacked storage contract.
    args=dict(compact_evidence=False,qualify_no_repair=False,optional_failure_policy=None,source_selection=sources,components=components,model=ordinary['model'],consumer=ordinary['consumer'],expected_links=ordinary['expected_links'],native_context=ordinary['native_context'],total_timeout_seconds=60,component_timeout_seconds=30,max_attempts=3)
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
    def late(attempt, **options):
        result=capture(attempt, **options);tick[0]=61.;return result
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
    def no_headroom(attempt, **options):
        result=capture(attempt, **options)
        if bound=='files':monkeypatch.setattr(frozen_tree,'MAX_FILES',len(result['files']))
        else:monkeypatch.setattr(frozen_tree,'MAX_BYTES',sum(r['size'] for r in result['files'].values()))
        return result
    monkeypatch.setattr(m,'_attempt_files',no_headroom)
    with pytest.raises(ValueError,match='completion exceeds frozen artifact bounds'):
        m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert not (root/'attempts/attempt-0001/finished.json').exists()
    assert (root/'attempts/attempt-0001/result.json').exists() and len(calls)==1



def test_new_complete_requests_enable_independent_no_repair_qualification(case,monkeypatch):
    from nasolve import cif_repair_attempt as repair
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args.pop('qualify_no_repair')
    old=repair.execute_prepared_dictionary_repair
    def execute(*a,**k):
        assert k['qualify_no_repair'] is True
        result=old(*a,**k);result.update(qualify_no_repair=True,status='NO_USABLE_BUNDLE')
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    m.initialize_dictionary_request(output=root,**args)
    assert read_record(root/'request.json')['configuration']['qualify_no_repair'] is True
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert result['result']['status']=='NO_USABLE_BUNDLE'
    assert m.read_dictionary_request_result(root,1)['execution']['qualify_no_repair'] is True
    child=root/'attempts/attempt-0001/repair/request.json'
    assert read_record(child)['configuration']['qualify_no_repair'] is True


@pytest.mark.parametrize('mode',[1,0,None,'yes'])
def test_complete_request_rejects_ambiguous_no_repair_mode(case,mode):
    m,args,root,sdk,store,generations,calls=case;args=dict(args,qualify_no_repair=mode)
    with pytest.raises(ValueError,match='boolean'):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and not calls


def test_legacy_complete_request_does_not_silently_enable_mode(case):
    m,args,root,sdk,store,generations,calls=case;m.initialize_dictionary_request(output=root,**args)
    assert 'qualify_no_repair' not in read_record(root/'request.json')['configuration']
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert 'NOT_ASSESSED' in result['result']['status']
    assert 'qualify_no_repair' not in read_record(root/'attempts/attempt-0001/repair/request.json')['configuration']



def test_complete_request_freezes_new_optional_failure_default(case,monkeypatch):
    from nasolve import cif_repair_attempt as repair
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args.pop('optional_failure_policy')
    old=repair.execute_prepared_dictionary_repair
    def execute(*a,**k):
        assert k['optional_failure_policy']==repair.FALLBACK_POLICY_ID
        result=old(*a,**k);result['optional_failure_policy']=k['optional_failure_policy']
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    m.initialize_dictionary_request(output=root,**args)
    assert read_record(root/'request.json')['configuration']['optional_failure_policy']==repair.FALLBACK_POLICY_ID
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    result=m.read_dictionary_request_result(root,1)
    assert result['execution']['optional_failure_policy']==repair.FALLBACK_POLICY_ID
    assert read_record(root/'attempts/attempt-0001/repair/request.json')['configuration']['optional_failure_policy']==repair.FALLBACK_POLICY_ID


@pytest.mark.parametrize('policy',[True,False,'UNKNOWN',1])
def test_complete_request_refuses_unknown_failure_policy(case,policy):
    m,args,root,sdk,store,generations,calls=case
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**dict(args,optional_failure_policy=policy))
    assert not (root/'request.json').exists() and not calls


def test_single_complete_request_keeps_owned_children_and_replays_cold(case,tmp_path):
    from unittest.mock import patch
    from tests.test_cif_dictionary_bundle import select_single_component
    m,args,root,sdk,store,generations,calls=case;args=select_single_component(args,tmp_path)
    m.initialize_dictionary_request(output=root,**args)
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation={'ZZZ':generations['ZZZ']})
    state=m.inspect_dictionary_request(root);row=state['attempts'][0]
    assert set(row['children'])=={'ZZZ','repair'} and all(c['state']=='STOPPED' for c in row['children'].values())
    exact=m.read_dictionary_request_result(root,1)
    assert exact['preparation']['bundle']['report']['site_owners']=={'A:1':'ZZZ','A:2':'ZZZ'}
    assert result['result']['selected_attempts']=={'ZZZ':1} and result['result']['automatic_adoption'] is False
    before=inventory(root);root=root.rename(tmp_path/'relocated');shutil.rmtree(args['source_selection']);args['model'].unlink();shutil.rmtree(store)
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(root,1)['result']==result['result']
    assert inventory(root)==before


@pytest.mark.parametrize('with_continuation', [False, True])
def test_new_request_inventories_independently_bounded_runtime(case, tmp_path, monkeypatch, with_continuation):
    from nasolve import cif_component_runtime as frozen
    m, args, root, sdk, store, generations, calls = case
    m.initialize_dictionary_request(output=root, **args)
    config = read_record(root / 'request.json')['configuration']
    sample = tmp_path / 'composed'; sample.mkdir()
    names = ['evidence', 'repair/attempts/attempt-0001/execution/runtime']
    if with_continuation: names.append('continuation')
    for name in names:
        folder = sample / name; folder.mkdir(parents=True)
        for i in range(6): (folder / str(i)).write_bytes(b'x' * 10)
    monkeypatch.setattr(frozen, 'MAX_FILES', 10)
    monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    options = dict(with_continuation=with_continuation)
    if 'artifact_policy' in config: options['artifact_policy'] = config['artifact_policy']
    result = m._attempt_files(sample, **options)
    assert len(result['files']) == 6 * len(names)
    assert config['artifact_policy'] == m.ARTIFACT_POLICY
    with pytest.raises(ValueError): m._attempt_files(sample, with_continuation=with_continuation)
    assert not calls


@pytest.mark.parametrize('partition', ['', 'repair/attempts/attempt-0001/execution/runtime', 'continuation'])
@pytest.mark.parametrize('excess', ['files', 'bytes', 'member'])
def test_partitioned_request_keeps_each_existing_bound(tmp_path, monkeypatch, partition, excess):
    from nasolve import cif_complete_request as m
    from nasolve import cif_component_runtime as frozen
    monkeypatch.setattr(frozen, 'MAX_FILES', 10)
    monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    monkeypatch.setattr(frozen, 'MAX_FILE_BYTES', 30)
    folder = tmp_path / partition; folder.mkdir(parents=True, exist_ok=True)
    count = 11 if excess == 'files' else 6 if excess == 'bytes' else 1
    data = b'x' * (20 if excess == 'bytes' else 31 if excess == 'member' else 1)
    for i in range(count): (folder / str(i)).write_bytes(data)
    with pytest.raises(ValueError, match='bounds'):
        m._attempt_files(tmp_path, with_continuation=True, artifact_policy=m.ARTIFACT_POLICY)


@pytest.mark.parametrize('alias', ['runtime-extra', 'runtime/../elsewhere', 'runtime-link'])
def test_partitioned_request_cannot_alias_the_runtime_partition(tmp_path, monkeypatch, alias):
    from nasolve import cif_complete_request as m
    from nasolve import cif_component_runtime as frozen
    monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    base = tmp_path / 'repair/attempts/attempt-0001/execution'; base.mkdir(parents=True)
    (base / 'runtime').mkdir(); (base / 'runtime/published').write_bytes(b'x' * 60)
    (tmp_path / 'working').write_bytes(b'x' * 60)
    if alias == 'runtime-link': (base / alias).symlink_to(base / 'runtime', target_is_directory=True)
    else:
        target = base / alias; target.mkdir(parents=True); (target / 'unrelated').write_bytes(b'x' * 60)
    with pytest.raises(ValueError): m._attempt_files(tmp_path, artifact_policy=m.ARTIFACT_POLICY)


@pytest.mark.parametrize('policy', ['unknown', '', True, {}, ['cif-complete-request-partitioned-artifacts-v1']])
def test_unknown_outer_artifact_policy_refuses_before_freezing(case, policy):
    m, args, root, sdk, store, generations, calls = case
    with pytest.raises(ValueError, match='artifact policy'):
        m.initialize_dictionary_request(output=root, artifact_policy=policy, **args)
    assert not root.exists() and not calls


def test_legacy_artifact_policy_stays_absent_through_execution(case):
    m, args, root, sdk, store, generations, calls = case
    m.initialize_dictionary_request(output=root, artifact_policy=None, **args)
    assert 'artifact_policy' not in read_record(root / 'request.json')['configuration']
    result = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert m.read_dictionary_request_result(root, 1)['result'] == result['result']


def test_changed_artifact_policy_refuses_read_and_execution(case):
    m, args, root, sdk, store, generations, calls = case
    m.initialize_dictionary_request(output=root, **args)
    request = read_record(root / 'request.json'); request.pop('record_sha256')
    request['configuration']['artifact_policy'] = 'unknown'
    (root / 'request.json').unlink(); write_record(root / 'request.json', request)
    before = inventory(root)
    with pytest.raises(ValueError, match='artifact policy'): m.inspect_dictionary_request(root)
    with pytest.raises(ValueError, match='artifact policy'):
        m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert inventory(root) == before and not calls


def test_exact_result_replays_each_completed_attempt_once_without_persistent_cache(case, monkeypatch):
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args)
    first=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    replay=m._result; seen=[]
    def observe(*a,**k):
        seen.append(a[2]['number']);return replay(*a,**k)
    monkeypatch.setattr(m,'_result',observe)
    before=inventory(root)
    value=m.read_dictionary_request_result(root,1)
    assert value['result']==first['result'] and seen==[1,2]
    seen.clear();again=m.read_dictionary_request_result(root,1)
    assert again==value and again is not value and seen==[1,2]
    assert inventory(root)==before


@pytest.mark.parametrize('changed',['result','seal','request','model','child','extra'])
def test_exact_result_refuses_changes_after_scientific_replay(case,monkeypatch,changed):
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    replay=m._result; altered=[]
    def mutate(*a,**k):
        value=replay(*a,**k)
        if not altered:
            attempt=a[1]
            path={'result':attempt/'result.json','seal':attempt/'finished.json','request':root/'request.json',
                  'model':root/'inputs/model.pdb','child':attempt/'repair/attempts/attempt-0001/finished.json',
                  'extra':attempt/'unexpected.txt'}[changed]
            path.write_bytes((path.read_bytes() if path.exists() else b'')+b'\n')
            altered.append(inventory(root))
        return value
    monkeypatch.setattr(m,'_result',mutate)
    with pytest.raises((ValueError,OSError)):m.read_dictionary_request_result(root,1)
    assert len(altered)==1 and inventory(root)==altered[0]


def test_exact_result_still_validates_unselected_history(case,monkeypatch):
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    path=root/'attempts/attempt-0002/result.json';path.write_bytes(path.read_bytes()+b'\n')
    before=inventory(root)
    with pytest.raises(ValueError):m.read_dictionary_request_result(root,1)
    assert inventory(root)==before


def test_explicit_resume_checks_previous_attempt_inside_existing_owner(case):
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args)
    first=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations,after_attempt=0)
    before=inventory(root)
    with pytest.raises(ValueError,match='attempt'):
        m.execute_dictionary_request_attempt(root,sdk,store,generation=generations,after_attempt=0)
    assert inventory(root)==before and len(calls)==1
    second=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations,after_attempt=1)
    assert first['attempt_number']==1 and second['attempt_number']==2


@pytest.fixture
def plane_reuse(case,tmp_path,monkeypatch):
    """Synthetic support transport; real owned-support checks have their own suite."""
    from hashlib import sha256
    from nasolve import cif_prepared_repair_execution as executor
    from nasolve import cif_repair_attempt as repair
    from nasolve.cif_acquisition_sources import read_acquisition_sources
    m,args,root,sdk,store,generations,calls=case
    sources=read_acquisition_sources(args['source_selection'])['sources'];code=sorted(sources)[0]
    support=tmp_path/'owned-support';support.mkdir();(support/'empty').mkdir()
    (support/'source.sha').write_text(sha256(sources[code]['source'].read_bytes()).hexdigest())
    def snapshot(selected,declarations):
        if declarations is None:return None,{}
        assert set(declarations)=={code} and code in selected
        row=declarations[code];assert type(row['attempt_number']) is int and row['attempt_number']==1
        directory=Path(row['request_directory']);raw=(directory/'source.sha').read_bytes()
        assert raw.decode()==sha256(Path(selected[code]).read_bytes()).hexdigest()
        files={code+'/source.sha':raw}
        return dict(policy_id=executor.PLANE_SUPPORT_POLICY,choices={code:1},
            files={n:dict(size=len(b),sha256=sha256(b).hexdigest()) for n,b in files.items()},directories=[code,code+'/empty']),files
    monkeypatch.setattr(executor,'_source_plane_support_snapshot',snapshot,raising=False)
    monkeypatch.setattr(m,'_source_plane_support_snapshot',snapshot,raising=False)
    original=repair.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        report=original(*a,**kw)
        cfg,_=executor._plane_support_snapshot(a[0],kw['plane_support'])
        report['plane_support']=cfg;(a[2]/'repair_execution.json').write_text(json.dumps(report))
        return report
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    args['plane_support']={code:dict(request_directory=support,attempt_number=1)}
    return case,support,code


def test_complete_request_reuses_frozen_plane_support_across_attempts_and_relocation(plane_reuse,tmp_path,monkeypatch):
    (m,args,root,sdk,store,generations,calls),support,code=plane_reuse
    initial=m.initialize_dictionary_request(output=root,**args)
    assert initial['configuration']['plane_support']['choices']=={code:1}
    shutil.rmtree(support)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    old=inventory(root/'attempts/attempt-0001')
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root/'attempts/attempt-0001')==old
    for n in (1,2):
        child=read_record(root/f'attempts/attempt-{n:04d}/repair/request.json')
        assert child['configuration']['plane_support']==initial['configuration']['plane_support']
    moved=root.rename(tmp_path/'relocated')
    def forbidden(*a,**k):raise AssertionError('Cold read must not execute/write')
    monkeypatch.setattr('subprocess.Popen',forbidden);monkeypatch.setattr(m,'write_record',forbidden)
    before=inventory(moved)
    value=m.read_dictionary_request_result(moved,1)
    assert value['execution']['plane_support']==initial['configuration']['plane_support']
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['source','attempt','overlap','mutation-during-freeze'])
def test_complete_plane_intake_refuses_wrong_or_changing_support(plane_reuse,monkeypatch,defect):
    (m,args,root,sdk,store,generations,calls),support,code=plane_reuse
    if defect=='source':(support/'source.sha').write_text('different source')
    elif defect=='attempt':args['plane_support'][code]['attempt_number']=True
    elif defect=='overlap':root=support/'nested'
    else:
        original=m._freeze
        def freeze(*a,**k):
            result=original(*a,**k);(support/'source.sha').write_text('changed');return result
        monkeypatch.setattr(m,'_freeze',freeze)
    with pytest.raises((AssertionError,ValueError)):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and not calls


@pytest.mark.parametrize('defect',['frozen','intent','child'])
def test_complete_plane_choice_cannot_be_dropped_or_changed(plane_reuse,defect):
    (m,args,root,sdk,store,generations,calls),support,code=plane_reuse
    m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    if defect=='frozen':(root/'inputs/plane-support'/code/'source.sha').write_text('changed')
    else:
        path=root/('request.json' if defect=='intent' else 'attempts/attempt-0001/repair/request.json')
        r=read_record(path);r['configuration'].pop('plane_support');write_record(path,r,replace=True)
    before=inventory(root)
    with pytest.raises((AssertionError,ValueError)):m.inspect_dictionary_request(root)
    assert inventory(root)==before and len(calls)==1



def test_automatic_plane_choice_freezes_without_generating(case):
    m,args,root,sdk,store,generations,calls=case
    header=m.initialize_dictionary_request(output=root,automatic_plane_support=True,**args)
    assert header['configuration']['plane_generation_policy']==m.PLANE_GENERATION_POLICY
    assert not (root/'attempts').exists() and not calls
    before=inventory(root);m.inspect_dictionary_request(root);assert inventory(root)==before


@pytest.mark.parametrize('value',[None,1,'yes',{}])
def test_automatic_plane_choice_requires_boolean(case,value):
    m,args,root,*_=case
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,automatic_plane_support=value,**args)
    assert not root.exists()


def test_supplied_and_automatic_support_are_exclusive(plane_reuse):
    (m,args,root,*_),_,_=plane_reuse
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,automatic_plane_support=True,**args)
    assert not root.exists()


@pytest.fixture
def auto_planes(case,monkeypatch):
    """Synthetic transport only; existing generation/chemistry tests and native control own science."""
    from hashlib import sha256
    import uuid
    from nasolve import cif_prepared_repair_execution as executor,cif_repair_attempt as repair
    m,args,root,sdk,store,generations,calls=case;code=sorted(generations)[0]
    options=dict(outcome='support',needed=True,generated=[])
    def plan(attempt):
        return {c:dict(source_sha256='s',dictionary_sha256='d',coverage_policy='synthetic',
            coverage_status='REVIEW' if c==code and options['needed'] else 'SCOPED_EXPLICIT_COVERAGE_PASS',
            missing_centres=['C'] if c==code and options['needed'] else []) for c in generations}
    monkeypatch.setattr(m,'_plane_plan',plan)
    def generate(*,source,code,request_directory,_parent_attempt_identity,_remaining_seconds,**g):
        assert g['multiple_planes'] is True and g['max_attempts']==1 and 0<_remaining_seconds()<=args['total_timeout_seconds']
        options['generated'].append(request_directory)
        if options['outcome']=='partial':request_directory.mkdir(parents=True);raise KeyboardInterrupt('partial generation reservation')
        request_directory.mkdir(parents=True);(request_directory/'inputs').mkdir()
        (request_directory/'inputs/source.cif').write_bytes(source.read_bytes())
        parent=read_record(request_directory.parent.parent/'attempt.json')
        config=read_record(root/'request.json')['configuration']['components'][code];r=config['dictionary_request'];b=config['generation_binding']
        header=write_record(request_directory/'request.json',dict(configuration=dict(component=code,
            source=dict(sha256=r['source_sha256'],size=r['source_size']),max_attempts=1,
            recipe=dict(expected_dialect=r['recipe']['expected_dialect'],single_block_steps=r['recipe']['single_block_steps'],
                timeout_seconds=b['timeout_seconds'],bond_representation_policy=r['recipe'].get('bond_representation_policy'),multiple_planes=True),
            generator=dict(phenix_version=r['generator']['version'],api_sources=r['generator']['api_sources'],prior_sources=r['generator']['prior_sources'],
                dispatchers={k:dict(path=v,size=1,sha256='1'*64) for k,v in b['dispatchers'].items()}))))
        attempt=request_directory/'attempts/attempt-0001';attempt.mkdir(parents=True)
        intent=write_record(attempt/'attempt.json',dict(number=1,attempt_id=str(uuid.uuid4()),request_sha256=header['record_sha256'],
            coordinator=parent['coordinator'],parent_attempt=_parent_attempt_identity))
        work=attempt/'generation';work.mkdir()
        (work/'source_candidate_receipt.json').write_text(json.dumps(dict(status='CANDIDATE_REVIEW' if options['outcome']=='support' else 'REJECTED',execution=dict(status='COMPLETED'))))
        write_record(attempt/'finished.json',dict(outcome='RETURNED',stopped_verified=True,attempt_sha256=intent['record_sha256']))
        if options['outcome']=='interrupt':raise KeyboardInterrupt('after stopped child')
        return dict(attempt_number=1)
    def inspect(path):
        if not path.exists():return dict(state='NOT_RECORDED')
        if not (path/'request.json').exists():return dict(state='UNKNOWN')
        attempt=path/'attempts/attempt-0001'
        return dict(state='RECORDED',request=read_record(path/'request.json'),attempts=[dict(number=1,state='STOPPED',activity=False,
            intent=read_record(attempt/'attempt.json'),finished=read_record(attempt/'finished.json'))])
    def proof(source,c,path,n):
        assert c==code and n==1 and source.read_bytes()==(path/'inputs/source.cif').read_bytes()
        return dict(policy_id='synthetic-transport',source_sha256=sha256(source.read_bytes()).hexdigest())
    def negative(*a):
        if options['outcome']=='corrupt':raise ValueError('unclassified evidence')
        return dict(proof(*a),failure_kind='REJECTED_CANDIDATE',fallback_authorized=False)
    def snapshot(sources,declarations):
        if declarations is None:return None,{}
        files={};dirs=[]
        for c,row in declarations.items():
            directory=Path(row['request_directory']);proof(sources[c],c,directory,row['attempt_number'])
            files.update({c+'/'+p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()})
            dirs.extend([c,*[c+'/'+p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_dir()]])
        return dict(policy_id=executor.PLANE_SUPPORT_POLICY,choices={c:row['attempt_number'] for c,row in declarations.items()},
            files={n:dict(size=len(b),sha256=sha256(b).hexdigest()) for n,b in files.items()},directories=sorted(dirs)),files
    monkeypatch.setattr(m,'generate_source_candidate_attempt',generate);monkeypatch.setattr(m,'inspect_source_generation_request',inspect)
    monkeypatch.setattr(m,'read_owned_plane_support',proof);monkeypatch.setattr(m,'inspect_owned_plane_generation_failure',negative)
    monkeypatch.setattr(m,'_source_plane_support_snapshot',snapshot);monkeypatch.setattr(executor,'_source_plane_support_snapshot',snapshot)
    original=repair.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        report=original(*a,**kw)
        if 'plane_support' in kw:report['plane_support']=executor._plane_support_snapshot(a[0],kw['plane_support'])[0]
        (a[2]/'repair_execution.json').write_text(json.dumps(report));return report
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    args['automatic_plane_support']=True
    return case,options,code


def test_automatic_support_joins_fresh_children_and_preserves_old_attempt(auto_planes,tmp_path,monkeypatch):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes
    m.initialize_dictionary_request(output=root,**args);inputs=inventory(root/'inputs')
    first=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    old=inventory(root/'attempts/attempt-0001')
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root/'inputs')==inputs and inventory(root/'attempts/attempt-0001')==old
    assert len(options['generated'])==2 and options['generated'][0]!=options['generated'][1]
    assert first['result']['plane_generation']['components'][code]['status']=='OWNED_SUPPORT_READY'
    moved=root.rename(tmp_path/'relocated-auto');before=inventory(moved)
    def forbidden(*a,**k):raise AssertionError('Cold result must not execute')
    monkeypatch.setattr(m,'generate_source_candidate_attempt',forbidden);monkeypatch.setattr('subprocess.Popen',forbidden)
    assert m.read_dictionary_request_result(moved,1)['result']==first['result']
    assert inventory(moved)==before


def test_automatic_support_skips_components_with_no_missing_plane(auto_planes):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes;options['needed']=False
    m.initialize_dictionary_request(output=root,**args);result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert not options['generated'] and not (root/'attempts/attempt-0001/plane-generations').exists()
    assert all(v['status']=='NO_GENERATION_NEEDED' for v in result['result']['plane_generation']['components'].values())


@pytest.mark.parametrize('outcome',['rejected','corrupt','partial'])
def test_automatic_support_failure_never_grants_unchecked_fallback(auto_planes,monkeypatch,outcome):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes;options['outcome']=outcome
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises((ValueError,KeyboardInterrupt)):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert not calls and (root/'attempts/attempt-0001/plane-generations'/code).exists()
    monkeypatch.setattr(m,'coordinator_alive',lambda _:False)
    state=m.inspect_dictionary_request(root)
    assert (state['availability']=='BLOCKED') is (outcome=='partial')
    assert not (root/'attempts/attempt-0002').exists()


@pytest.mark.parametrize('defect',['parent','recipe','foreign','intent','result'])
def test_automatic_plane_child_cannot_escape_outer_identity(auto_planes,defect):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    attempt=root/'attempts/attempt-0001';child=attempt/'plane-generations'/code
    if defect=='foreign':(attempt/'plane-generations/EXTRA').mkdir()
    else:
        path={'parent':child/'attempts/attempt-0001/attempt.json','recipe':child/'request.json','intent':root/'request.json','result':attempt/'result.json'}[defect]
        row=read_record(path)
        if defect=='parent':row['parent_attempt']['attempt_id']='foreign'
        elif defect=='recipe':row['configuration']['recipe']['single_block_steps']+=1
        elif defect=='intent':row['configuration'].pop('plane_generation_policy')
        else:row['plane_generation']['components'][code]['status']='NO_GENERATION_NEEDED'
        write_record(path,row,replace=True)
    before=inventory(root)
    with pytest.raises(ValueError):m.inspect_dictionary_request(root)
    assert inventory(root)==before and len(calls)==1



def test_automatic_plane_interruption_uses_new_outer_and_generation_attempt(auto_planes):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes;options['outcome']='interrupt'
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root/'attempts/attempt-0001');options['outcome']='support'
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations,after_attempt=1)
    assert result['attempt_number']==2 and len(options['generated'])==2 and len(calls)==1
    assert inventory(root/'attempts/attempt-0001')==before


def test_generated_plane_owner_is_checked_before_repair(auto_planes,monkeypatch):
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes
    original=m.generate_source_candidate_attempt
    def foreign(**kw):
        value=original(**kw);p=kw['request_directory']/'attempts/attempt-0001/attempt.json';r=read_record(p)
        r['parent_attempt']['attempt_id']='foreign';write_record(p,r,replace=True);return value
    monkeypatch.setattr(m,'generate_source_candidate_attempt',foreign)
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises(ValueError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert not calls and not (root/'attempts/attempt-0001/repair').exists()


def test_classified_plane_failure_still_runs_independent_qualification(auto_planes,monkeypatch):
    from nasolve import cif_repair_attempt as repair
    (m,args,root,sdk,store,generations,calls),options,code=auto_planes
    options['outcome']='rejected';args.update(qualify_no_repair=True,optional_failure_policy=repair.FALLBACK_POLICY_ID)
    original=repair.execute_prepared_dictionary_repair
    def checked(*a,**kw):
        assert kw['qualify_no_repair'] is True and 'plane_support' not in kw
        value=original(*a,**kw);value.update(qualify_no_repair=True,optional_failure_policy=repair.FALLBACK_POLICY_ID,status='NO_USABLE_BUNDLE')
        (a[2]/'repair_execution.json').write_text(json.dumps(value));return value
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',checked)
    m.initialize_dictionary_request(output=root,**args);result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert len(calls)==1 and result['result']['plane_generation']['components'][code]['status']=='KNOWN_GENERATION_FAILURE'
    assert m.read_dictionary_request_result(root,1)['runtime'] is None  # A failed qualification stays unusable.
