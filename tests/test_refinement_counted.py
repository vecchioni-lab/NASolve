"""Saved counted requests/admission reuse the existing immutable execution owner."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from nasolve import refinement_parallelity as execution
from nasolve import refinement_counted as saved
from nasolve.campaign_records import write_record
from nasolve.checkpoints import _file_reference


def request_case(tmp_path, *, request_changes=None):
    from tests.test_topostitch_recipe import prepare
    source=tmp_path/'source';source.mkdir()
    packet=prepare(source)
    recipe=source/'recipe.json';recipe.write_text(json.dumps(packet))
    run=tmp_path/'run';folder=run/'AutoRefine/round_001';folder.mkdir(parents=True)
    inputs=run/'inputs';inputs.mkdir()
    parent=inputs/'model.pdb';parent.write_bytes((source/'model.pdb').read_bytes())
    observations=inputs/'observations.mtz';observations.write_bytes(b'fixture observations')
    parameters=inputs/'refinement.phil';parameters.write_text('explicit one-cycle fixture')
    options=dict(checkpoint='refine-001',parent='postmr',inputs=[observations,parent,parameters],
        command=['phenix.refine',str(observations),str(parent),str(parameters),'output.prefix=refined'],
        python_executable=sys.executable,macro_cycles=1,runtime_policy=execution.V5_POLICY_ID,
        counted_pair_request=dict(recipe=recipe,source_model=source/'model.pdb'))
    options.update(request_changes or {})
    reference,preflight,refine=execution.prepare_execution(run,**options)
    assert refine is None
    return run,reference,preflight


def observed_case(tmp_path):
    run,reference,command=request_case(tmp_path)
    request=execution.read_execution_request(run,reference,checkpoint='refine-001')
    root=run/execution._root('refine-001');phase=root/'preflight';phase.mkdir();(phase/'calls').mkdir()
    profile=json.loads((root/'code/_nasolve_refinement/data/parallelity-native-profile.json').read_text())
    result=dict(schema_version=1,policy_id='explicit-native-parallelity-refinement-v4',
        status='COMPLETE',arguments=command[5:],pid=123,parent_pid=122,
        scientific_approval='NOT_RUN',binding_restored=True,native_profile=profile,
        dry_run=True,macro_cycles=0,atom_labels=[],parallelity_parameters=[],usage_observations=[],
        parent_kernel_statistics=dict(policy_id='native-parallelity-kernel-adapter-v1',
            successful_calls=0,gradient_calls=0,energy_only_calls=0,maximum_proxy_count=0),
        output_binding_restored=True,output_synchronization=[],chemistry_observation=None,
        chemistry_model=None,chemistry_binding_restored=True)
    (phase/'result.json').write_text(json.dumps(result))
    # This unit fixture stands in for the source-qualified native observer. It is
    # not scientific evidence and cannot qualify a real model for C375 ownership.
    context=dict(recipe_sha256=request['counted_intent']['current_recipe_sha256'],source_model_sha256=request['inputs'][1]['sha256'])
    prepared=dict(frozen_policy={},compiled_binding=dict(kind='topostitch-native-pair-binding',**context),
        native_observation=dict(context=context,terms=[],terms_sha256=saved._digest([])),
        provider_selection=dict(additive=[],frozen=dict(context=context,native_sha256=saved._digest([]),additive_sha256=saved._digest([]))),
        counted_baseline=dict(policy_id='prepared-counted-native-baseline-v1',outer_normalization=True,bonded={}))
    work=phase/'preparation-work';work.mkdir();(work/'prepared.json').write_text(json.dumps(prepared))
    observation=dict(policy_id=saved.OBSERVATION_POLICY,status='PREPARED',
        scope=dict(policy_id='prepared-counted-refinement-cycle-v1',cycles=1,iterations=10,nproc=1,
            seed=1,fix_wxc=1.,wc=1.,strategy=['individual_sites'],individual=['all'],target='ml',
            scattering_table='n_gaussian',place_ions=None),
        prepared_sha256=saved._digest(prepared),recipe_sha256=request['counted_intent']['current_recipe_sha256'])
    (phase/'counted.json').write_text(json.dumps(observation))
    return run,reference,root,prepared


def test_saved_recipe_keeps_original_bytes_and_has_no_refine_command(tmp_path):
    run,reference,command=request_case(tmp_path)
    record=execution.read_execution_request(run,reference,checkpoint='refine-001')
    root=run/execution._root('refine-001')
    assert record['schema_version']==2 and execution.POLICY_ID==execution.V3_POLICY_ID
    assert (root/'intent/original-model.pdb').read_bytes()==(tmp_path/'source/model.pdb').read_bytes()
    assert (root/'intent/original-recipe.json').read_bytes()==(tmp_path/'source/recipe.json').read_bytes()
    assert len(record['code'])==24
    assert command[3:5]==['preflight',reference['sha256']]
    assert not (root/'admission.json').exists()


@pytest.mark.parametrize('changes',[{'macro_cycles':5},{'chemistry_projections':[]},
    {'counted_pair_request':None},{'runtime_policy':execution.V4_POLICY_ID}])
def test_unsupported_counted_choice_refuses_before_runtime_allocation(tmp_path,changes):
    with pytest.raises(ValueError):request_case(tmp_path,request_changes=changes)
    assert not (tmp_path/'run/AutoRefine/round_001/parallelity_runtime').exists()


def test_changed_original_source_is_refused_before_allocation(tmp_path,monkeypatch):
    original=saved.prepare_intent
    def changed(recipe,source,parent):
        Path(source).write_bytes(Path(source).read_bytes()+b'REMARK changed\n')
        return original(recipe,source,parent)
    monkeypatch.setattr(saved,'prepare_intent',changed)
    with pytest.raises(ValueError,match='checksum'):request_case(tmp_path)
    assert not (tmp_path/'run/AutoRefine/round_001/parallelity_runtime').exists()


def test_sealed_preparation_is_compact_immutable_and_cold_after_relocation(tmp_path):
    run,reference,root,prepared=observed_case(tmp_path)
    raw=(root/'preflight/preparation-work/prepared.json').read_bytes()
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert not (root/'preflight/preparation-work').exists()
    assert (root/'preflight/prepared.zip').exists()
    assert not any('preparation-work' in row['relative_path'] for row in
        saved.read_admission(run,reference,admission,checkpoint='refine-001')['preflight_files'])
    before={p.relative_to(run):(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    moved=tmp_path/'moved';run.rename(moved);assert not run.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('cold read')), \
         patch.object(saved,'write_record',side_effect=AssertionError('read must not seal')):
        value=saved.read_admission(moved,reference,admission,checkpoint='refine-001')
    assert value['prepared_sha256']==saved._digest(prepared)
    assert {p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}==before
    with pytest.raises(ValueError,match='immutable'):
        saved.seal_admission(moved,reference,checkpoint='refine-001',preflight_returncode=0)


def test_command_requires_positive_admission_and_owns_only_temporary_view(tmp_path):
    run,reference,root,prepared=observed_case(tmp_path)
    with pytest.raises(ValueError,match='Admission'):
        with saved.refinement_command(run,reference,None,checkpoint='refine-001',python_executable=sys.executable):pass
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    before=sorted(str(p.relative_to(root)) for p in root.rglob('*'))
    with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable) as command:
        view=Path(command[6]);assert json.loads(view.read_text())==prepared
        assert command[3:6]==['refine',reference['sha256'],admission['sha256']]
        assert not view.is_relative_to(root)
        saved.read_admission(run,reference,admission,checkpoint='refine-001')
    assert not view.exists() and sorted(str(p.relative_to(root)) for p in root.rglob('*'))==before
    (root/'refine').mkdir()
    with pytest.raises(ValueError,match='fresh unlaunched'):
        with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable):pass


@pytest.mark.parametrize('defect',['archive','observation','extra','intent','code','admission','rehashed_scope'])
def test_changed_admission_inputs_cannot_launch(tmp_path,defect):
    run,reference,root,prepared=observed_case(tmp_path)
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    if defect=='archive':(root/'preflight/prepared.zip').write_bytes(b'changed')
    elif defect=='observation':(root/'preflight/counted.json').write_text('{}')
    elif defect=='extra':(root/'preflight/extra').write_text('extra')
    elif defect=='intent':(root/'intent/current-recipe.json').write_text('{}')
    elif defect=='code':(root/'code/_nasolve_refinement/cif_counted_phase.py').write_text('changed')
    elif defect=='admission':(root/'admission.json').write_text('{}')
    elif defect=='rehashed_scope':
        value=json.loads((root/'admission.json').read_text());value['scope']['cycles']=2
        write_record(root/'admission.json',value,replace=True);admission=_file_reference(root/'admission.json',run)
    with patch('subprocess.Popen',side_effect=AssertionError('no launch')):
        with pytest.raises((ValueError,RuntimeError)):
            with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable):pass


def test_native_zero_and_preparation_refusal_keep_existing_failure_contract(tmp_path):
    run,reference,root,prepared=observed_case(tmp_path)
    (root/'preflight/counted.json').write_text(json.dumps(dict(policy_id=saved.OBSERVATION_POLICY,
        status='REFUSED',error=dict(type='ValueError',message='unsupported actual scope'))))
    with pytest.raises(ValueError,match='unsupported actual scope') as error:
        saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert not (root/'admission.json').exists() and (root/'preflight/preparation-work/prepared.json').exists()
    refused=dict(stage='preflight_evidence',error=dict(type=type(error.value).__name__,message=str(error.value)))
    receipt=execution.finish_execution(run,reference,checkpoint='refine-001',preflight_returncode=0,
        refinement_returncode=None,admission_refusal=refused)
    record=execution.validate_execution(run,receipt,checkpoint='refine-001')
    assert record['schema_version']==2 and record['refinement_status']=='NOT_LAUNCHED'
    assert [row['returncode'] for row in record['phases']]==[0,None]
    with pytest.raises(ValueError):execution.validate_execution(run,receipt,checkpoint='refine-001',usable=True)


@pytest.mark.parametrize('field',['compiled_binding','native_observation','provider_selection'])
def test_rehashed_preparation_cannot_switch_recipe_or_parent(tmp_path,field):
    run,reference,root,prepared=observed_case(tmp_path)
    if field=='compiled_binding':prepared[field]['source_model_sha256']='0'*64
    elif field=='native_observation':prepared[field]['context']=dict(prepared[field]['context'],recipe_sha256='0'*64)
    else:prepared[field]['frozen']['native_sha256']='0'*64
    raw=root/'preflight/preparation-work/prepared.json';raw.write_text(json.dumps(prepared))
    p=root/'preflight/counted.json';observation=json.loads(p.read_text());observation['prepared_sha256']=saved._digest(prepared);p.write_text(json.dumps(observation))
    with pytest.raises(ValueError,match='binding|context|inventory'):
        saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert raw.exists() and not (root/'admission.json').exists()


def test_archive_failure_preserves_raw_preparation_and_cannot_admit(tmp_path,monkeypatch):
    run,reference,root,prepared=observed_case(tmp_path)
    def fail(*args,**kwargs):raise OSError('disk unavailable')
    monkeypatch.setattr('nasolve.cif_runtime_evidence.pack_runtime_evidence',fail)
    raw=root/'preflight/preparation-work/prepared.json';before=raw.read_bytes()
    with pytest.raises(OSError,match='disk unavailable'):
        saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert raw.read_bytes()==before and not (root/'admission.json').exists()


def test_finished_failure_without_refine_directory_cannot_be_retried(tmp_path):
    run,reference,root,prepared=observed_case(tmp_path)
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    execution.finish_execution(run,reference,checkpoint='refine-001',preflight_returncode=0,
        refinement_returncode=1,counted_admission=admission)
    assert not (root/'refine').exists()
    with pytest.raises(ValueError,match='finished|fresh unlaunched'):
        with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable):
            pytest.fail('Finished failed attempt was launchable again')


def test_atomic_launch_claim_blocks_retry_after_failure_before_phase_folder(tmp_path):
    run,reference,root,prepared=observed_case(tmp_path)
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    # Plain Python has no Phenix SDK. The authenticated worker claims this
    # attempt, then fails before creating the native refinement evidence folder.
    with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable) as command:
        first=subprocess.run(command,capture_output=True,text=True,check=False)
        assert first.returncode!=0 and (root/'refinement-launch.json').is_file()
        before=(root/'refinement-launch.json').read_bytes()
        second=subprocess.run(command,capture_output=True,text=True,check=False)
        assert second.returncode!=0 and 'FileExistsError' in second.stderr
        assert (root/'refinement-launch.json').read_bytes()==before
    assert not (root/'refine').exists()
    with pytest.raises(ValueError,match='fresh unlaunched'):
        with saved.refinement_command(run,reference,admission,checkpoint='refine-001',python_executable=sys.executable):pass
    receipt=execution.finish_execution(run,reference,checkpoint='refine-001',preflight_returncode=0,
        refinement_returncode=first.returncode,counted_admission=admission)
    record=execution.validate_execution(run,receipt,checkpoint='refine-001')
    assert record['counted_launch']['sha256']==hashlib.sha256(before).hexdigest()


def test_counted_write_failure_preserves_primary_native_exception(tmp_path,monkeypatch):
    from nasolve import cif_counted_phase as phase
    run,reference,root,prepared=observed_case(tmp_path)
    admission_ref=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    admission=saved.read_admission(run,reference,admission_ref,checkpoint='refine-001')
    request=execution.read_execution_request(run,reference,checkpoint='refine-001')
    primary=RuntimeError('original native failure')
    class Owner:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def statistics(self):return {'status':'FAILED'}
    def fail(*args,**kwargs):
        (root/'refine').mkdir()
        raise primary
    def disk(*args,**kwargs):raise OSError('disk unavailable')
    monkeypatch.setattr(phase.lifetime,'PreparedCountedRefinement',Owner)
    monkeypatch.setattr(phase.runtime,'run_compatible_refinement',fail)
    monkeypatch.setattr(phase,'_write',disk)
    with saved.refinement_command(run,reference,admission_ref,checkpoint='refine-001',python_executable=sys.executable) as command:
        with pytest.raises(RuntimeError,match='original native failure') as error:
            phase.run_phase(root,request,'refine',request['command'][1:],admission=admission,prepared_path=command[6])
    assert error.value is primary
    if hasattr(primary,'__notes__'):assert any('disk unavailable' in n for n in primary.__notes__)


def test_malformed_current_input_is_a_controlled_request_refusal(tmp_path):
    run,reference,command=request_case(tmp_path)
    path=run/reference['relative_path'];record=json.loads(path.read_text());record['inputs'][0]='not a reference'
    write_record(path,record,replace=True);reference=_file_reference(path,run)
    with pytest.raises((ValueError,RuntimeError)):
        execution.read_execution_request(run,reference,checkpoint='refine-001')


@pytest.mark.parametrize('manual',[False,True])
def test_ordinary_continuation_cannot_drop_counted_intent(tmp_path,manual):
    # Only a refusal decision is made here. Ordinary callers have already
    # validated their complete registry; this policy read grants no authority.
    run,reference,root,prepared=observed_case(tmp_path)
    policy=root/'policy-fixture.json';write_record(policy,dict(policy_id=execution.V5_POLICY_ID))
    items=[dict(id='postmr',parent=None),dict(id='refine-001',parent='postmr',
        outputs=dict(parallelity_execution=_file_reference(policy,run)))]
    if manual:items.append(dict(id='manual-child',parent='refine-001'))
    before={p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('refuse before launch')):
        with pytest.raises(ValueError,match='counted pair restraints'):
            execution.require_runtime_continuation(dict(checkpoints=items),items[-1],True,run=run)
    assert {p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}==before


def test_archive_directory_sync_failure_preserves_raw_bytes(tmp_path,monkeypatch):
    run,reference,root,prepared=observed_case(tmp_path)
    raw=root/'preflight/preparation-work/prepared.json';before=raw.read_bytes()
    def fail(path):raise OSError('archive directory sync failed')
    monkeypatch.setattr(saved,'_sync_directory',fail)
    with pytest.raises(OSError,match='archive directory sync'):
        saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert raw.read_bytes()==before and (root/'preflight/prepared.zip').is_file()
    assert not (root/'admission.json').exists()


def registered_counted_case(tmp_path):
    """Synthetic lifecycle evidence; no native or scientific qualification."""
    from nasolve.checkpoints import initialize_registry,append_checkpoint
    from tests.test_cif_refinement_runtime import output_row
    run,reference,root,prepared=observed_case(tmp_path)
    # The existing checkpoint owner requires its round-local parameter spelling.
    params=run/'AutoRefine/round_001/autorefine.params'
    params.write_bytes((run/'inputs/refinement.phil').read_bytes())
    path=root/'request.json';request=json.loads(path.read_text())
    request['inputs'][-1]=_file_reference(params,run)
    request['command'][3]=str(params)
    write_record(path,request,replace=True);reference=_file_reference(path,run)
    result_path=root/'preflight/result.json';result=json.loads(result_path.read_text())
    result['arguments']=execution._preflight_arguments(request);result_path.write_text(json.dumps(result))
    admission=saved.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    admitted=saved.read_admission(run,reference,admission,checkpoint='refine-001')
    phase=root/'refine';phase.mkdir();(phase/'calls').mkdir()
    result.update(arguments=request['command'][1:],dry_run=False,macro_cycles=1,
        atom_labels=['fixture-a','fixture-b'],output_synchronization=[output_row(2)])
    (phase/'result.json').write_text(json.dumps(result))
    (root/'refinement-launch.json').write_text(json.dumps(dict(schema_version=1,checkpoint='refine-001',
        request_sha256=reference['sha256'],admission_sha256=admission['sha256'],pid=123,parent_pid=122,created_ns=1)))
    outcome=dict(policy_id=saved.OBSERVATION_POLICY,admission_record_sha256=admitted['record_sha256'],
        prepared_sha256=admitted['prepared_sha256'],compiled_binding_sha256=admitted['compiled_binding_sha256'],
        provider_selection_sha256=admitted['provider_selection_sha256'],scope_sha256=saved._digest(admitted['scope']),
        recipe_sha256=request['counted_intent']['current_recipe_sha256'],
        lifetime=dict(policy_id='prepared-counted-refinement-cycle-v1',status='COMPLETE',binding_restored=True,
                      driver_entries=1,owner=dict(closed=True,poisoned=False,successful_calls=1)))
    (phase/'counted.json').write_text(json.dumps(outcome))
    receipt=execution.finish_execution(run,reference,checkpoint='refine-001',preflight_returncode=0,
        refinement_returncode=0,counted_admission=admission)
    model=run/'inputs/model.pdb';observations=run/'inputs/observations.mtz'
    report=dict(workflow='automr',inputs=dict(reflections='inputs/observations.mtz',reflections_sha256=_file_reference(observations,run)['sha256']),
        postmr=dict(status='POSTMR_READY',prepared_model='inputs/model.pdb',prepared_sha256=_file_reference(model,run)['sha256'],restraints=[]))
    (run/'report.json').write_text(json.dumps(report));_,registry=initialize_registry(run)
    child=root.parent/'refined_001.pdb';child.write_bytes(model.read_bytes().replace(b'   4.000',b'   4.010',1))
    item=dict(id='refine-001',parent='postmr',status='REVIEW',usable=True,kind='autorefine',recipe='explicit-test',
        model=_file_reference(child,run),observations=_file_reference(observations,run),restraints=[],phases=None,
        outputs=dict(parallelity_execution=receipt))
    append_checkpoint(run,registry,item,select=False)
    return run,reference,registry,item


def continuation_options(run,parent='refine-001'):
    from nasolve.checkpoints import read_registry,resolve_checkpoint,inherited_paths
    _,registry=read_registry(run);paths=inherited_paths(resolve_checkpoint(registry,parent),run)
    folder=run/'AutoRefine/round_002';folder.mkdir()
    params=folder/'autorefine.params';params.write_text('one cycle fixture')
    inputs=[paths['observations'],paths['model'],*paths['restraints'],params]
    return dict(checkpoint='refine-002',parent=parent,inputs=inputs,
        command=['phenix.refine',*map(str,inputs),'output.prefix=refined'],python_executable=sys.executable,macro_cycles=1)


@pytest.mark.parametrize('manual',[False,True])
def test_explicit_descendant_preserves_original_intent_and_rebinds_selected_model(tmp_path,manual):
    from nasolve.checkpoints import add_checkpoint,read_registry
    run,original,registry,parent=registered_counted_case(tmp_path)
    selected='refine-001'
    if manual:
        child=run/parent['model']['relative_path']
        selected=add_checkpoint(run,name='compatible manual child',model=child,parent=selected).checkpoint_id
    options=continuation_options(run,selected)
    before={p.relative_to(run):(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    reference,command,refine=saved.prepare_continuation(run,**options)
    assert refine is None and command[3]=='preflight'
    request=execution.read_execution_request(run,reference,checkpoint='refine-002')
    old=execution.read_execution_request(run,original,checkpoint='refine-001')
    assert request['parent']==selected
    for name in ('original_recipe','original_model'):
        assert request['counted_intent'][name]['sha256']==old['counted_intent'][name]['sha256']
    assert request['counted_intent']['current_recipe_sha256']!=old['counted_intent']['current_recipe_sha256']
    assert request['inputs'][1]==_file_reference(options['inputs'][1],run)
    assert read_registry(run)[1]['current']=='postmr'
    assert all((run/p).read_bytes()==data and (run/p).stat().st_mtime_ns==mtime for p,(data,mtime) in before.items())


@pytest.mark.parametrize('defect',['wrong_model','wrong_observations','not_counted','failed_parent','missing_atom','changed_frame','broken_lineage'])
def test_descendant_refuses_incompatible_or_unproven_parent_before_runtime_allocation(tmp_path,defect):
    from nasolve.checkpoints import save_registry,add_checkpoint
    run,reference,registry,parent=registered_counted_case(tmp_path)
    options=continuation_options(run)
    if defect=='wrong_model':options['inputs'][1]=run/'inputs/model.pdb'
    elif defect=='wrong_observations':options['inputs'][0]=run/'inputs/model.pdb'
    elif defect=='not_counted':options['parent']='postmr'
    elif defect=='failed_parent':parent['usable']=False;parent['status']='FAILED';save_registry(run,registry)
    elif defect=='broken_lineage':parent['parent']='missing';save_registry(run,registry)
    else:
        model=run/parent['model']['relative_path'];text=model.read_text()
        if defect=='missing_atom':text=''.join(line for line in text.splitlines(keepends=True) if line[12:16].strip()!='N7')
        else:text=text.replace('  40.000','  41.000',1)
        source=run/'manual.pdb';source.write_text(text)
        selected=add_checkpoint(run,name='incompatible manual',model=source,parent='refine-001').checkpoint_id
        options['parent']=selected
        options['inputs'][1]=run/'AutoRefine/Checkpoints'/selected/'manual.pdb'
    options['command']=['phenix.refine',*map(str,options['inputs']),'output.prefix=refined']
    before={p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with pytest.raises((ValueError,RuntimeError)):
        saved.prepare_continuation(run,**options)
    assert not (run/'AutoRefine/round_002/parallelity_runtime').exists()
    assert {p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('field',['original_recipe_sha256','original_model'])
def test_rehashed_child_intent_cannot_replace_its_counted_ancestry(tmp_path,field):
    run,reference,registry,parent=registered_counted_case(tmp_path)
    request=execution.read_execution_request(run,reference,checkpoint='refine-001')
    child=dict(parent,id='refine-002',parent='refine-001');registry['checkpoints'].append(child)
    changed=json.loads(json.dumps(request));intent=changed['counted_intent']
    if field=='original_model':intent[field]['sha256']='0'*64
    else:intent[field]='0'*64
    with pytest.raises(ValueError,match='changed its original pair intent'):
        saved.validate_intent_lineage(run,registry,child,changed)


def test_registered_counted_ancestry_reads_cold_and_continues_after_relocation(tmp_path):
    from nasolve.checkpoints import read_registry
    run,reference,registry,parent=registered_counted_case(tmp_path)
    moved=tmp_path/'relocated-run';run.rename(moved);assert not run.exists()
    before={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        assert read_registry(moved)[1]['current']=='postmr'
    assert all((moved/p).read_bytes()==data and (moved/p).stat().st_mtime_ns==mtime for p,(data,mtime) in before.items())
    options=continuation_options(moved)
    child,command,refine=saved.prepare_continuation(moved,**options)
    assert refine is None
    value=execution.read_execution_request(moved,child,checkpoint='refine-002')
    assert value['parent']=='refine-001' and str(run) not in ' '.join(value['command'])


def test_counted_lineage_cannot_cross_a_refinement_that_dropped_its_intent(tmp_path):
    run,reference,registry,parent=registered_counted_case(tmp_path)
    policy=run/'ordinary-policy-fixture.json'
    write_record(policy,dict(policy_id=execution.V3_POLICY_ID))
    ordinary=dict(id='refine-002',parent='refine-001',outputs=dict(parallelity_execution=_file_reference(policy,run)))
    selected=dict(id='manual-001',parent='refine-002',outputs={})
    registry['checkpoints'].extend([ordinary,selected])
    with pytest.raises(ValueError,match='lost its counted pair intent'):
        saved._inherited_request(run,registry,selected,include_selected=True)
