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


def completed(tmp_path,monkeypatch,*,failure=None,changed=None,bad_preflight=False,chemistry=None):
    run,policy,refine,dump=inputs(tmp_path);original=subprocess.run;commands=[]
    if chemistry is not None:
        from tests.test_cif_triple_bond_audit import fixture
        directory=run/'PostMR/projection';directory.mkdir()
        source,_=fixture(directory)
        scope=[dict(site='A:1',component='Q17',projection=_file_reference(source,run))]
        monkeypatch.setattr('nasolve.refinement_chemistry.prepare_chemistry_scope',lambda *args:scope)
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
            from nasolve.refinement_parallelity import _RUNTIME_POLICIES,LEGACY_POLICY_ID
            request=json.loads((root/'request.json').read_text())
            result=dict(schema_version=1,policy_id=_RUNTIME_POLICIES[request['policy_id']],
                status='FAILED' if failed else 'COMPLETE',arguments=native_args,pid=123,parent_pid=122,
                scientific_approval='NOT_RUN',binding_restored=True,native_profile=profile,
                dry_run=phase=='preflight',macro_cycles=0 if phase=='preflight' else 5,
                atom_labels=['a','b'],parallelity_parameters=[],usage_observations=[],
                parent_kernel_statistics=dict(policy_id='native-parallelity-kernel-adapter-v1',
                    successful_calls=0,gradient_calls=0,energy_only_calls=0,maximum_proxy_count=0))
            if request['policy_id']!=LEGACY_POLICY_ID:
                from tests.test_cif_refinement_runtime import output_row
                result.update(output_binding_restored=True,output_synchronization=[] if phase=='preflight' else [output_row(2)])
            if request['policy_id'] in ('round-local-parallelity-execution-v3','round-local-parallelity-execution-v4'):
                result.update(chemistry_observation=None,chemistry_model=None,chemistry_binding_restored=True)
            if bad_preflight and phase=='preflight':result['status']='RUNNING'
            if failed:result['error']=dict(type='RuntimeError',message='native failed')
            (folder/'result.json').write_text(json.dumps(result))
            if changed==phase:
                (root/'code/_nasolve_refinement/cif_parallelity_kernel.py').write_text('changed helper')
            if failed:return subprocess.CompletedProcess(command,1)
            fake_args=['--dry_run',*native_args[:-1]] if phase=='preflight' else native_args
            native_result=original([str(refine),*fake_args],*args,**kwargs)
            if chemistry is not None:
                from tests.test_cif_refinement_sites import capture,SITES
                from nasolve.cif_refinement_sites import unavailable
                observation,labels=capture()
                result['atom_labels']=labels
                if chemistry=='straight':
                    observation['atoms'][3]['xyz'][1]=.001
                if chemistry=='unavailable':observation=unavailable(SITES,'Synthetic observer interface unavailable')
                result['chemistry_observation']=observation
                if phase=='refine':
                    from tests.test_cif_refinement_runtime import output_row
                    row=output_row(len(labels))
                    if chemistry!='unavailable':
                        row['hierarchy_after_sha256']=observation['model_state_sha256']
                        model=root.parent/'refined_001.pdb'
                        ref=_file_reference(model,run)
                        result['chemistry_model']={key:ref[key] for key in ('sha256','size')}
                    result['output_synchronization']=[row]
                (folder/'result.json').write_text(json.dumps(result))
            if phase=='preflight' and bad_preflight=='missing':(folder/'result.json').unlink()
            if phase=='preflight' and bad_preflight=='malformed':(folder/'result.json').write_text('{broken evidence')
            return native_result
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
    assert len(request['code'])==8 and len(request['inputs'])==6
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
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,bad_preflight=True)
    record=json.loads(receipt.read_text())
    assert commands==['preflight'] and record['schema_version']==2
    assert [phase['returncode'] for phase in record['phases']]==[0,None]
    assert record['admission_refusal']['stage']=='preflight_evidence'
    assert record['admission_refusal']['error']['type']=='ValueError'
    assert child['status']=='FAILED' and child['usable'] is False
    assert registry['current']=='postmr' and result.exit_code==2
    assert 'not launched' in result.message and 'preflight evidence' in result.message
    report=json.loads(result.report_path.read_text())
    assert report['phenix_exit_code'] is None and report['preflight_exit_code']==0
    assert report['preflight_failed'] is False
    assert report['admission_refusal']==record['admission_refusal']
    assert (receipt.parent/'preflight/native_001.geo').read_text()=='preflight geometry preserved'
    assert not (receipt.parent/'refine').exists()


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



@pytest.mark.parametrize('version',[1,2,3])
def test_frozen_reader_survives_current_helper_upgrade_and_relocation(tmp_path,monkeypatch,version):
    from nasolve import refinement_parallelity as module
    from hashlib import sha256
    package=Path(module.__file__).parent
    fixture=Path(__file__).parent/f'fixtures/refinement_runtime_v{version}'
    code={'entry.py':module._ENTRY if version==3 else module._V2_ENTRY,'code/_nasolve_refinement/__init__.py':b''}
    policy={1:module.LEGACY_POLICY_ID,2:module.V2_POLICY_ID,3:module.V3_POLICY_ID}[version]
    for name,digest in module._SOURCES[policy].items():
        path=fixture/name if (fixture/name).exists() else package/name
        data=module._code(module.V3_POLICY_ID)['code/_nasolve_refinement/'+name] if version==3 else path.read_bytes()
        assert sha256(data).hexdigest()==digest
        code['code/_nasolve_refinement/'+name]=data
    with monkeypatch.context() as legacy:
        legacy.setattr(module,'POLICY_ID',policy)
        legacy.setattr(module,'_code',lambda:code)
        run,result,registry,child,receipt,commands=completed(tmp_path,legacy)
    old=run.parents[1];moved=tmp_path/'relocated';old.rename(moved)
    assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('historical read must stay cold')):
        _,saved=read_registry(moved/'AutoMR/run_001')
    assert resolve_checkpoint(saved,child['id'])['usable']
    assert module.POLICY_ID!='round-local-parallelity-execution-v1'


@pytest.mark.parametrize('defect',['missing','unfinished','count','hash','false','policy','receipt_policy'])
def test_rehashed_v2_output_proof_cannot_be_weakened(tmp_path,monkeypatch,defect):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    record=json.loads(receipt.read_text());request_path=run/record['request']['relative_path']
    output_path=request_path.parent/'refine/result.json';output=json.loads(output_path.read_text())
    if defect=='missing':del output['output_synchronization']
    elif defect=='unfinished':output['output_synchronization'][0]['write_completed']=False
    elif defect=='count':output['output_synchronization'][0]['atom_count']=3
    elif defect=='hash':output['output_synchronization'][0]['fcalc_sha256']='broken'
    elif defect=='false':output['output_synchronization'][0]['scattering_unchanged']=False
    elif defect=='policy':output['policy_id']='explicit-native-parallelity-refinement-v1'
    elif defect=='receipt_policy':record['policy_id']='round-local-parallelity-execution-v1'
    output_path.write_text(json.dumps(output))
    for ref in record['phases'][1]['files']:
        if ref['relative_path']==str(output_path.relative_to(run)):
            ref.update(_file_reference(output_path,run))
    write_record(receipt,record,replace=True);child['outputs']['parallelity_execution']=_file_reference(receipt,run)
    (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    with patch('subprocess.Popen',side_effect=AssertionError('cold refusal')):
        with pytest.raises(CheckpointError):read_registry(run)


@pytest.mark.parametrize('location',['request','receipt'])
@pytest.mark.parametrize('policy',[[],{}])
def test_malformed_policy_is_a_controlled_checkpoint_refusal(tmp_path,monkeypatch,location,policy):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch)
    record=json.loads(receipt.read_text())
    if location=='request':
        path=run/record['request']['relative_path'];request=json.loads(path.read_text())
        request['policy_id']=policy;write_record(path,request,replace=True)
        record['request']=_file_reference(path,run)
    else:record['policy_id']=policy
    write_record(receipt,record,replace=True)
    child['outputs']['parallelity_execution']=_file_reference(receipt,run)
    (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    before={p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('cold refusal')):
        with pytest.raises(CheckpointError,match='Invalid explicit parallelity execution evidence'):
            read_registry(run)
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('chemistry',['bent','straight','unavailable'])
def test_native_chemistry_report_preserves_usable_model_but_real_review_prevents_selection(tmp_path,monkeypatch,chemistry):
    # Synthetic native records exercise the ordinary AutoRefine/checkpoint owner;
    # this is not an executed Phenix scientific qualification.
    run,result,registry,child,receipt,_=completed(tmp_path,monkeypatch,chemistry=chemistry)
    report=result.statistics['chemical_geometry']
    assert result.exit_code==0 and child['usable']
    assert report['status']=={'bent':'REVIEW','straight':'SCOPED_TRIPLE_SCREEN_PASS','unavailable':'UNASSESSED'}[chemistry]
    assert report['scientific_approval']=='NOT_RUN' and not report['automatic_adoption']
    assert result.status==('AUTOREFINE_REVIEW' if chemistry=='bent' else 'AUTOREFINE_READY')
    if chemistry=='bent':assert not result.selected_as_current and registry['current']=='postmr'
    assert child['metrics']['chemical_geometry']==report
    saved=json.loads(result.report_path.read_text())
    assert saved['statistics']['chemical_geometry']==report
    assert saved['acceptance']['chemical_geometry_review'] is (chemistry=='bent')
    from nasolve.refinement_parallelity import read_execution_chemistry
    before={p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        actual=read_execution_chemistry(run,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=result.model_path)
    assert actual==report and all(p.read_bytes()==data for p,data in before.items())


def test_actual_manager_observation_relocates_without_original_paths(tmp_path,monkeypatch):
    from nasolve.refinement_parallelity import read_execution_chemistry
    run,result,registry,child,receipt,_=completed(tmp_path,monkeypatch,chemistry='bent')
    old=run.parents[1];moved=tmp_path/'moved';old.rename(moved);new=moved/run.relative_to(old)
    assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('no native job for readback')):
        _,registry=read_registry(new)
        report=read_execution_chemistry(new,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=new/child['model']['relative_path'])
    assert report==result.statistics['chemical_geometry']


@pytest.mark.parametrize('defect',['state','model_hash','missing','scope','proxy','definition','unrestored','projection','relabelled_projection'])
def test_rehashed_compact_observation_cannot_claim_other_model_state_or_source(tmp_path,monkeypatch,defect):
    run,result,registry,child,receipt,_=completed(tmp_path,monkeypatch,chemistry='bent')
    record=json.loads(receipt.read_text());request_path=run/record['request']['relative_path'];request=json.loads(request_path.read_text())
    path=request_path.parent/'refine/result.json';value=json.loads(path.read_text())
    if defect=='state':value['chemistry_observation']['model_state_sha256']='f'*64
    elif defect=='model_hash':value['chemistry_model']['sha256']='f'*64
    elif defect=='missing':value.pop('chemistry_observation')
    elif defect=='scope':value['chemistry_observation']['sites'][0]['site']='B:4'
    elif defect=='proxy':value['chemistry_observation']['geometry']['proxy_details']['angle'][0]['atoms'][0]='wrong'
    elif defect=='definition':value['chemistry_observation']['monomer_mappings']['rows']=[]
    elif defect=='unrestored':value['chemistry_binding_restored']=False
    else:
        p=run/request['chemistry_projections'][0]['projection']['relative_path']
        p.write_text(p.read_text().replace('TRIP','SING'))
        if defect=='relabelled_projection':
            request['chemistry_projections'][0]['projection']=_file_reference(p,run)
            write_record(request_path,request,replace=True);record['request']=_file_reference(request_path,run)
    path.write_text(json.dumps(value))
    for ref in record['phases'][1]['files']:
        if ref['relative_path']==str(path.relative_to(run)):ref.update(_file_reference(path,run))
    write_record(receipt,record,replace=True);child['outputs']['parallelity_execution']=_file_reference(receipt,run)
    (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    with patch('subprocess.Popen',side_effect=AssertionError('cold refusal')):
        with pytest.raises(CheckpointError):read_registry(run)


@pytest.mark.parametrize('chemistry',[None,'bent','unavailable'])
def test_explicit_v4_keeps_chemistry_checks_and_cold_relocation(tmp_path,monkeypatch,chemistry):
    from nasolve import refinement_parallelity as module
    original=module.prepare_execution
    monkeypatch.setattr(module,'prepare_execution',lambda *a,**k:original(*a,**k,runtime_policy=module.V4_POLICY_ID))
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,chemistry=chemistry)
    record=json.loads(receipt.read_text());assert record['policy_id']==module.V4_POLICY_ID
    assert child['usable'] and commands==['preflight','refine']
    if chemistry=='bent':assert result.status=='AUTOREFINE_REVIEW' and not result.selected_as_current
    old=run.parents[1];moved=tmp_path/'relocated';old.rename(moved)
    assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('relocated read stays cold')):
        _,saved=read_registry(moved/'AutoMR/run_001')
    assert resolve_checkpoint(saved,child['id'])['usable']
    assert module.POLICY_ID==module.V3_POLICY_ID


def test_frozen_v3_default_and_explicit_v4_sources_are_independently_pinned(tmp_path,monkeypatch):
    from nasolve import refinement_parallelity as module
    from hashlib import sha256
    package=Path(module.__file__).parent
    default=module._code();assert default==module._code(module.V3_POLICY_ID)
    assert {n:sha256(v).hexdigest() for n,v in default.items()}==module._expected_code(module.V3_POLICY_ID)
    assert {n:sha256(v).hexdigest() for n,v in module._code(module.V4_POLICY_ID).items()}==module._expected_code(module.V4_POLICY_ID)
    # A damaged legacy payload cannot be hidden behind unchanged current sources.
    copied=tmp_path/'package';copied.mkdir()
    for name in {*module._V4_SOURCE_DIGESTS,'data/refinement-runtime-v3-sources.json'}:
        target=copied/name;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes((package/name).read_bytes())
    monkeypatch.setattr(module,'__file__',str(copied/'refinement_parallelity.py'))
    archive=copied/'data/refinement-runtime-v3-sources.json';saved=archive.read_bytes();value=json.loads(saved)
    value['cif_refinement_runtime.py']+='\n# changed\n';archive.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='qualified runtime'):module._code()
    assert module._code(module.V4_POLICY_ID)
    archive.write_bytes(saved);(copied/'cif_refinement_runtime.py').write_text('# changed current runtime')
    assert module._code()==default
    with pytest.raises(ValueError,match='qualified runtime'):module._code(module.V4_POLICY_ID)


@pytest.mark.parametrize('policy',[[],{},'round-local-parallelity-execution-v2','unknown'])
def test_unknown_new_runtime_policy_refuses_before_allocating(tmp_path,policy):
    from nasolve.refinement_parallelity import prepare_execution
    with pytest.raises(ValueError,match='execution policy'):
        prepare_execution(tmp_path,checkpoint='refine-001',parent='postmr',inputs=[],
            command=['phenix.refine','model.pdb'],python_executable=sys.executable,
            macro_cycles=1,runtime_policy=policy)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('defect',['running','missing','malformed'])
def test_admission_refusal_relocates_and_readers_do_not_repair_evidence(tmp_path,monkeypatch,defect):
    from nasolve import refinement_parallelity as module
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,bad_preflight=defect)
    record=json.loads(receipt.read_text())
    assert record['refinement_status']=='NOT_LAUNCHED'
    assert record['outcome_policy_id']==module.ADMISSION_REFUSAL_POLICY_ID
    old=run.parents[1];moved=tmp_path/'relocated';old.rename(moved)
    new_run=moved/'AutoMR/run_001';assert not old.exists()
    before={p.relative_to(new_run): (p.read_bytes(),p.stat().st_mtime_ns)
            for p in new_run.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('read only')), \
         patch('nasolve.refinement_parallelity.write_record',side_effect=AssertionError('reader must not write')):
        _,saved=read_registry(new_run)
        assert resolve_checkpoint(saved,child['id'])['usable'] is False
        with pytest.raises(ValueError):
            module.validate_preflight(new_run,record['request'],checkpoint=child['id'])
    assert {p.relative_to(new_run): (p.read_bytes(),p.stat().st_mtime_ns)
            for p in new_run.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('defect',['old_schema','unknown_schema','unknown_policy','launched',
    'preflight_failed','refine_code','refine_folder','raw_changed','extra_raw','usable','refusal_stage'])
def test_refused_receipt_cannot_claim_success_or_relabel_evidence(tmp_path,monkeypatch,defect):
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,bad_preflight=True)
    record=json.loads(receipt.read_text())
    if defect=='old_schema':
        record['schema_version']=1
        for key in ('outcome_policy_id','refinement_status','admission_refusal'):del record[key]
    elif defect=='unknown_schema':record['schema_version']=3
    elif defect=='unknown_policy':record['outcome_policy_id']='unknown'
    elif defect=='launched':record['refinement_status']='COMPLETE'
    elif defect=='preflight_failed':record['phases'][0]['returncode']=1
    elif defect=='refine_code':record['phases'][1]['returncode']=0
    elif defect=='refine_folder':(receipt.parent/'refine').mkdir()
    elif defect=='raw_changed':(receipt.parent/'preflight/native_001.geo').write_text('changed')
    elif defect=='extra_raw':(receipt.parent/'preflight/extra.json').write_text('{}')
    elif defect=='usable':child['usable']=True
    elif defect=='refusal_stage':record['admission_refusal']['stage']='refinement'
    write_record(receipt,record,replace=True)
    child['outputs']['parallelity_execution']=_file_reference(receipt,run)
    (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        with pytest.raises(CheckpointError):read_registry(run)


def test_refused_receipt_is_immutable_and_cannot_hide_a_launched_phase(tmp_path,monkeypatch):
    from nasolve.refinement_parallelity import finish_execution
    run,result,registry,child,receipt,commands=completed(tmp_path,monkeypatch,bad_preflight=True)
    record=json.loads(receipt.read_text());before=receipt.read_bytes()
    arguments=dict(checkpoint=child['id'],preflight_returncode=0,refinement_returncode=None,
                   admission_refusal=record['admission_refusal'])
    with pytest.raises(RuntimeError,match='Cannot save'):
        finish_execution(run,record['request'],**arguments)
    assert receipt.read_bytes()==before
    (receipt.parent/'refine').mkdir()
    with pytest.raises(ValueError,match='Unrequested'):
        finish_execution(run,record['request'],**arguments)
    assert receipt.read_bytes()==before


def test_refusal_preservation_failure_reports_original_cause(tmp_path,monkeypatch):
    def cannot_save(*args,**kwargs):raise OSError('disk unavailable')
    monkeypatch.setattr('nasolve.refinement_parallelity.finish_execution',cannot_save)
    with pytest.raises(AutoRefineError,match='disk unavailable; original preflight admission refusal: ValueError:'):
        completed(tmp_path,monkeypatch,bad_preflight=True)
    root=tmp_path/'dataset/AutoMR/run_001/AutoRefine/round_001'
    assert 'NASolve refused preflight evidence' in (root/'phenix.refine.log').read_text()
    assert (root/'parallelity_runtime/preflight/native_001.geo').exists()
    assert not (root/'parallelity_runtime/refine').exists()


def test_unqualified_installed_helper_refuses_before_round_allocation(tmp_path,monkeypatch):
    def damaged(*args,**kwargs):raise ValueError('Helper differs from the qualified runtime policy')
    monkeypatch.setattr('nasolve.refinement_parallelity._code',damaged)
    run,policy,refine,dump=inputs(tmp_path)
    with pytest.raises(AutoRefineError,match='qualified runtime'):
        execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174',
            correct_native_parallelity=True,phenix_python_executable=Path(sys.executable))
    assert not (run/'AutoRefine').exists()


def test_direct_freezer_checks_source_before_creating_runtime_directory(tmp_path,monkeypatch):
    from nasolve.refinement_parallelity import prepare_execution
    def damaged(*args,**kwargs):raise OSError('required helper missing')
    monkeypatch.setattr('nasolve.refinement_parallelity._code',damaged)
    directory=tmp_path/'AutoRefine/round_001';directory.mkdir(parents=True)
    model=tmp_path/'model.pdb';model.write_text('input')
    with pytest.raises(OSError,match='required helper missing'):
        prepare_execution(tmp_path,checkpoint='refine-001',parent='postmr',inputs=[model],
            command=['phenix.refine',str(model),'output.prefix=refined'],
            python_executable=sys.executable,macro_cycles=1)
    assert not (directory/'parallelity_runtime').exists()
