"""Saved counted intent/admission for the existing round-local execution owner.

No subprocess, native object, alternate executor or provider planner lives here.
Readers remain data-only. An explicit stopped-preflight publication owns compact
storage; a temporary read view is held only around the caller's refinement phase.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

from .campaign_records import path_in, read_record, write_record, _json_object, _sync_directory
from .refinement_inputs import _bound_path

INTENT_POLICY = 'saved-counted-pair-intent-v1'
ADMISSION_POLICY = 'prepared-counted-admission-v1'
OBSERVATION_POLICY = 'counted-phase-observation-v1'


def _need(value,message):
    if not value:raise ValueError(message)


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(),object_pairs_hook=_json_object)


def prepare_intent(recipe, source_model, current_model):
    """Validate all proposed bytes before the existing owner allocates a folder."""
    from .topostitch_recipe import rebind_pair_recipe
    original=Path(recipe).read_bytes();source=Path(source_model).read_bytes()
    packet=json.loads(original,object_pairs_hook=_json_object)
    current=Path(current_model).read_bytes()
    rebound=rebind_pair_recipe(packet,source,current,expected_recipe_sha256=_digest(packet),
        expected_model_sha256=hashlib.sha256(current).hexdigest())
    return {'original-recipe.json':original,'original-model.pdb':source,
            'current-recipe.json':json.dumps(rebound,sort_keys=True,allow_nan=False).encode()+b'\n'}


def write_intent(run, root, payload):
    from .checkpoints import _file_reference
    folder=root/'intent';folder.mkdir()
    refs={}
    for name,data in payload.items():
        target=folder/name
        with target.open('xb') as handle:handle.write(data)
        refs[name]=_file_reference(target,run)
    return dict(policy_id=INTENT_POLICY,original_recipe=refs['original-recipe.json'],
        original_model=refs['original-model.pdb'],current_recipe=refs['current-recipe.json'],
        original_recipe_sha256=_digest(json.loads(payload['original-recipe.json'])),
        current_recipe_sha256=_digest(json.loads(payload['current-recipe.json'])))


def read_intent(run, root, request):
    """Authenticate saved unchanged intent; native interpretation stays native."""
    value=request.get('counted_intent')
    _need(isinstance(value,dict) and set(value)=={'policy_id','original_recipe','original_model',
        'current_recipe','original_recipe_sha256','current_recipe_sha256'} and value['policy_id']==INTENT_POLICY,
        'Unsupported saved counted intent')
    paths={}
    for key,name in [('original_recipe','original-recipe.json'),('original_model','original-model.pdb'),
                     ('current_recipe','current-recipe.json')]:
        ref=value[key];expected=root+'/intent/'+name
        _need(isinstance(ref,dict) and ref.get('anchor')=='run' and ref.get('relative_path')==expected,
              'Counted intent must belong to its exact round')
        path_in(run,expected);paths[key]=_bound_path(ref,'counted intent',run)
    _need(len(request['inputs'])>=2,'Counted request requires the current parent model')
    for ref in request['inputs']:
        _need(isinstance(ref,dict) and ref.get('anchor') in ('run','dataset','repository'),
              'Counted inputs require declared portable anchors')
    parent=_bound_path(request['inputs'][1],'counted current parent',run)
    original=_json(paths['original_recipe']);current=_json(paths['current_recipe'])
    _need(isinstance(original,dict) and isinstance(current,dict)
          and _digest(original)==value['original_recipe_sha256']
          and _digest(current)==value['current_recipe_sha256'], 'Counted recipe digest differs')
    _need(original.get('source_model_sha256')==hashlib.sha256(paths['original_model'].read_bytes()).hexdigest()
          and current==dict(original,source_model_sha256=hashlib.sha256(parent.read_bytes()).hexdigest()),
          'Current recipe must preserve exact original pair intent')
    return value



def _original_identity(request):
    intent=request['counted_intent']
    return (intent['original_recipe_sha256'],
            tuple(intent[name][key] for name in ('original_recipe','original_model') for key in ('sha256','size')))


def _inherited_request(run, registry, selected, *, include_selected):
    """Read pinned intent from validated ancestry without recursively reading a registry."""
    from .checkpoint_candidate import _lineage, CheckpointCandidateError
    from . import refinement_parallelity as execution
    try:lineage=_lineage(registry,selected)
    except CheckpointCandidateError as exc:raise ValueError(str(exc)) from exc
    if not include_selected:lineage=lineage[:-1]
    by_id={item['id']:item for item in registry['checkpoints']}
    inherited=None
    for identifier in lineage:
        item=by_id[identifier];outputs=item.get('outputs')
        reference=outputs.get('parallelity_execution') if isinstance(outputs,dict) else None
        if reference is None:continue
        record=read_record(_bound_path(reference,'ancestor execution',run))
        if record['policy_id']!=execution.V5_POLICY_ID:
            _need(inherited is None,'A later refinement lost its counted pair intent')
            continue
        _need([row['returncode'] for row in record['phases']]==[0,0],
              'Counted continuation requires a completed ancestor')
        request=execution.read_execution_request(run,record['request'],checkpoint=identifier)
        if inherited is not None:
            _need(_original_identity(inherited)==_original_identity(request),
                  'Counted ancestry changed its original pair intent')
        inherited=request
    return inherited


def validate_intent_lineage(run, registry, selected, request):
    """Join original intent during existing checkpoint validation; no rebind or writes."""
    inherited=_inherited_request(run,registry,selected,include_selected=False)
    if inherited is not None:
        _need(_original_identity(inherited)==_original_identity(request),
              'Counted descendant changed its original pair intent')


def prepare_continuation(run_directory, *, checkpoint, parent, inputs, command,
                         python_executable, macro_cycles):
    """Prepare a fresh explicit request from a registered compatible descendant.

    The existing caller owns its numbered round, parameters, process and result
    publication. This joins validated lineage to the existing freezer and W118
    rebind; it neither runs Phenix nor changes selection or ordinary defaults.
    """
    from . import refinement_parallelity as execution
    from .checkpoints import read_registry,resolve_checkpoint,inherited_paths,REUSABLE_STATUSES
    run,registry=read_registry(run_directory)
    selected=resolve_checkpoint(registry,parent)
    _need(selected['id']==parent,'Counted continuation requires an exact checkpoint ID')
    _need(selected.get('usable') is True and selected.get('status') in REUSABLE_STATUSES,
          'Counted continuation requires a reusable selected parent')
    _need(checkpoint not in {item['id'] for item in registry['checkpoints']},
          'Counted continuation requires a fresh checkpoint')
    request=_inherited_request(run,registry,selected,include_selected=True)
    _need(request is not None,'Selected checkpoint has no completed counted ancestor')
    paths=inherited_paths(selected,run)
    expected=[paths['observations'],paths['model'],*paths['restraints']]
    if paths['phases'] is not None:expected.append(paths['phases'])
    expected.append(path_in(run,execution._root(checkpoint)).parent/'autorefine.params')
    inputs=[Path(p).expanduser().resolve() for p in inputs]
    _need(inputs==expected,
          'Counted continuation inputs differ from selected ancestry and round parameters')
    intent=request['counted_intent']
    return execution.prepare_execution(run,checkpoint=checkpoint,parent=parent,inputs=inputs,
        command=command,python_executable=python_executable,macro_cycles=macro_cycles,
        runtime_policy=execution.V5_POLICY_ID,counted_pair_request=dict(
            recipe=_bound_path(intent['original_recipe'],'original pair recipe',run),
            source_model=_bound_path(intent['original_model'],'original pair source',run)))


def _prepared(value, expected, request):
    _need(isinstance(value,dict) and set(value)=={'frozen_policy','compiled_binding',
        'native_observation','provider_selection','counted_baseline'} and _digest(value)==expected,
        'Require exact strong prepared record')
    baseline=value['counted_baseline']
    _need(isinstance(baseline,dict) and set(baseline)=={'policy_id','outer_normalization','bonded'}
          and baseline['policy_id']=='prepared-counted-native-baseline-v1'
          and type(baseline['outer_normalization']) is bool,'Unsupported counted baseline')
    binding=value['compiled_binding'];observation=value['native_observation'];selection=value['provider_selection']
    recipe=request['counted_intent']['current_recipe_sha256'];model=request['inputs'][1]['sha256']
    _need(isinstance(binding,dict) and binding.get('kind')=='topostitch-native-pair-binding'
          and binding.get('recipe_sha256')==recipe and binding.get('source_model_sha256')==model,
          'Prepared binding belongs to another recipe or parent')
    context=observation.get('context') if isinstance(observation,dict) else None
    frozen=selection.get('frozen') if isinstance(selection,dict) else None
    _need(isinstance(context,dict) and context.get('recipe_sha256')==recipe
          and context.get('source_model_sha256')==model and isinstance(frozen,dict)
          and frozen.get('context')==context,'Prepared provider context differs from the request')
    _need(observation.get('terms_sha256')==_digest(observation.get('terms'))
          and frozen.get('native_sha256')==observation['terms_sha256']
          and frozen.get('additive_sha256')==_digest(selection.get('additive')),
          'Prepared provider inventory digest differs')


def _scope(value):
    # Saved representation of C377's qualified scope, not a new native protocol.
    _need(isinstance(value,dict) and set(value)=={'policy_id','cycles','iterations','nproc','seed',
          'fix_wxc','wc','strategy','individual','target','scattering_table','place_ions'}
          and value['policy_id']=='prepared-counted-refinement-cycle-v1'
          and type(value['cycles']) is int and value['cycles']==1
          and type(value['nproc']) is int and value['nproc']==1
          and type(value['iterations']) is int and 1<=value['iterations']<=10
          and type(value['seed']) is int
          and all(type(value[k]) in (int,float) and value[k]==1. for k in ('fix_wxc','wc'))
          and value['strategy']==['individual_sites'] and value['individual']==['all']
          and value['target']=='ml' and value['scattering_table']=='n_gaussian'
          and value['place_ions'] is None,'Unsupported saved counted scope')


def _observation(run, root, request):
    value=_json(path_in(run,root+'/preflight/counted.json'))
    _need(isinstance(value,dict) and value.get('policy_id')==OBSERVATION_POLICY,
          'Missing counted preflight observation')
    if value.get('status')=='REFUSED':
        error=value.get('error')
        _need(isinstance(error,dict) and set(error)=={'type','message'}
              and all(isinstance(v,str) for v in error.values()),'Invalid counted preparation refusal')
        raise ValueError('Counted preparation refused: '+error['type']+': '+error['message'])
    _need(set(value)=={'policy_id','status','scope','prepared_sha256','recipe_sha256'}
          and value['status']=='PREPARED' and isinstance(value['scope'],dict)
          and value['scope'].get('policy_id')=='prepared-counted-refinement-cycle-v1'
          and value['recipe_sha256']==request['counted_intent']['current_recipe_sha256'],
          'Invalid counted prepared observation')
    _scope(value['scope'])
    return value


def seal_admission(run, reference, *, checkpoint, preflight_returncode):
    """Publish once after the caller's native preflight process has stopped.

    Compact only the completed worker's transient preparation copy. The same
    exact bytes survive in the existing bounded archive. Every failure before
    verified storage retains the raw copy; a stopped partial attempt is never
    repaired/retried here. This function grants no scientific acceptance.
    """
    from . import refinement_parallelity as execution
    from .checkpoints import _file_reference
    from .cif_runtime_evidence import pack_runtime_evidence, expanded_runtime_evidence
    _need(type(preflight_returncode) is int and preflight_returncode==0,'Admission requires native preflight zero')
    request=execution.read_execution_request(run,reference,checkpoint=checkpoint)
    _need(request['policy_id']==execution.V5_POLICY_ID,'Counted admission requires explicit v5')
    root=execution._root(checkpoint);target=path_in(run,root+'/admission.json')
    _need(not target.exists(),'Counted admission is immutable')
    _need(not path_in(run,root+'/execution.json').exists()
          and not path_in(run,root+'/refinement-launch.json').exists(),'Counted attempt already launched or finished')
    _need(not path_in(run,root+'/refine').exists(),'Refinement already allocated')
    execution.validate_preflight(run,reference,checkpoint=checkpoint)
    observed=_observation(run,root,request)
    work=path_in(run,root+'/preflight/preparation-work');raw=work/'prepared.json'
    _need(list(work.iterdir())==[raw] and not raw.is_symlink(),'Unexpected transient preparation membership')
    original=raw.read_bytes();prepared=_json(raw);_prepared(prepared,observed['prepared_sha256'],request)
    archive=path_in(run,root+'/preflight/prepared.zip')
    stored=pack_runtime_evidence(work,archive)
    with expanded_runtime_evidence(archive,stored['archive_sha256']) as view:
        _need((view/'evidence/prepared.json').read_bytes()==original,'Archived preparation changed')
    with archive.open('rb') as handle:os.fsync(handle.fileno())
    _sync_directory(archive.parent)  # Make the archive name durable before retiring raw bytes.
    _need(raw.read_bytes()==original,'Preparation changed during publication')
    raw.unlink();work.rmdir()  # Only the verified transient copy, never an earlier result.
    _sync_directory(archive.parent)
    write_record(target,dict(schema_version=1,policy_id=ADMISSION_POLICY,checkpoint=checkpoint,
        request=reference,preflight_returncode=0,
        preflight_files=[_file_reference(p,run) for p in execution._phase_paths(run,root,'preflight')],
        prepared_archive=_file_reference(archive,run),prepared_sha256=observed['prepared_sha256'],
        scope=observed['scope'],compiled_binding_sha256=_digest(prepared['compiled_binding']),
        provider_selection_sha256=_digest(prepared['provider_selection'])))
    result=_file_reference(target,run)
    read_admission(run,reference,result,checkpoint=checkpoint)
    return result


def read_admission(run, request_reference, admission_reference, *, checkpoint):
    from . import refinement_parallelity as execution
    from .cif_runtime_evidence import expanded_runtime_evidence
    request=execution.read_execution_request(run,request_reference,checkpoint=checkpoint)
    _need(request['policy_id']==execution.V5_POLICY_ID,'Counted admission requires explicit v5')
    root=execution._root(checkpoint);ref=admission_reference
    _need(isinstance(ref,dict) and ref.get('anchor')=='run' and ref.get('relative_path')==root+'/admission.json',
          'Admission must belong to its exact round')
    path_in(run,ref['relative_path']);value=read_record(_bound_path(ref,'counted admission',run))
    _need(set(value)=={'schema_version','policy_id','checkpoint','request','preflight_returncode',
        'preflight_files','prepared_archive','prepared_sha256','scope','compiled_binding_sha256',
        'provider_selection_sha256','record_sha256'}
        and type(value['schema_version']) is int and value['schema_version']==1
        and value['policy_id']==ADMISSION_POLICY and value['checkpoint']==checkpoint
        and value['request']==request_reference and type(value['preflight_returncode']) is int
        and value['preflight_returncode']==0 and isinstance(value['preflight_files'],list),
        'Invalid counted admission envelope')
    names=[]
    for item in value['preflight_files']:
        _need(isinstance(item,dict) and item.get('anchor')=='run'
              and isinstance(item.get('relative_path'),str) and item['relative_path'].startswith(root+'/preflight/'),
              'Counted preflight reference escaped its phase')
        path_in(run,item['relative_path']);_bound_path(item,'counted preflight evidence',run);names.append(item['relative_path'])
    _need(names==sorted(set(names))==[p.relative_to(run).as_posix() for p in execution._phase_paths(run,root,'preflight')],
          'Counted preflight membership changed')
    execution.validate_preflight(run,request_reference,checkpoint=checkpoint)
    observed=_observation(run,root,request)
    _need(value['scope']==observed['scope'] and value['prepared_sha256']==observed['prepared_sha256'],
          'Admission differs from actual preflight observation')
    archive=value['prepared_archive']
    _need(isinstance(archive,dict) and archive.get('anchor')=='run'
          and archive.get('relative_path')==root+'/preflight/prepared.zip' and archive in value['preflight_files'],
          'Admission archive differs from preflight membership')
    path=_bound_path(archive,'prepared archive',run)
    with expanded_runtime_evidence(path,archive['sha256']) as view:
        _need(list((view/'evidence').iterdir())==[view/'evidence/prepared.json'],
              'Unexpected prepared archive membership')
        prepared=_json(view/'evidence/prepared.json');_prepared(prepared,value['prepared_sha256'],request)
        _need(value['compiled_binding_sha256']==_digest(prepared['compiled_binding'])
              and value['provider_selection_sha256']==_digest(prepared['provider_selection']),
              'Admission prepared identities differ')
    return value


@contextmanager
def refinement_command(run, request_reference, admission_reference, *, checkpoint, python_executable):
    """Keep the temporary prepared view alive around the existing caller's process."""
    from . import refinement_parallelity as execution
    from .cif_runtime_evidence import expanded_runtime_evidence
    request=execution.read_execution_request(run,request_reference,checkpoint=checkpoint)
    value=read_admission(run,request_reference,admission_reference,checkpoint=checkpoint)
    root=execution._root(checkpoint)
    _need(not path_in(run,root+'/refine').exists()
          and not path_in(run,root+'/execution.json').exists()
          and not path_in(run,root+'/refinement-launch.json').exists(),
          'Require a fresh unlaunched refinement phase; attempt already started or finished')
    # A relocated completed attempt is readable, not a command-replay permission.
    current=[str(_bound_path(ref,'native input',run)) for ref in request['inputs']]
    _need(request['command'][1:1+len(current)]==current,
          'Pending native command moved; prepare a fresh anchored attempt')
    archive=value['prepared_archive'];path=_bound_path(archive,'prepared archive',run)
    with expanded_runtime_evidence(path,archive['sha256']) as view:
        yield [str(python_executable),'-B',str(path_in(run,root+'/entry.py')),'refine',
            request_reference['sha256'],admission_reference['sha256'],str(view/'evidence/prepared.json'),
            *request['command'][1:]]


def read_outcome_binding(run, root, request, admission, launch_reference, *, complete):
    """Join completed native observations to the admission actually consumed.

    A partial launch marker is preserved as raw evidence on failure. It is never
    a liveness check, retry grant or substitute for the caller's process handle.
    """
    if launch_reference is not None:
        _need(isinstance(launch_reference,dict) and launch_reference.get('anchor')=='run'
              and launch_reference.get('relative_path')==root+'/refinement-launch.json',
              'Counted launch marker must belong to its exact round')
        path_in(run,launch_reference['relative_path'])
        path=_bound_path(launch_reference,'counted launch marker',run)
    else:
        _need(not path_in(run,root+'/refinement-launch.json').exists(),'Unrecorded counted launch marker')
        _need(not complete,'Completed counted refinement lacks launch provenance')
        return
    if not complete:return
    marker=_json(path);native=_json(path_in(run,root+'/refine/result.json'))
    _need(isinstance(marker,dict) and set(marker)=={'schema_version','checkpoint','request_sha256',
          'admission_sha256','pid','parent_pid','created_ns'} and type(marker['schema_version']) is int
          and marker['schema_version']==1 and marker['checkpoint']==request['checkpoint']
          and marker['request_sha256']==admission['request']['sha256']
          and marker['admission_sha256']==hashlib.sha256(path_in(run,root+'/admission.json').read_bytes()).hexdigest()
          and all(type(marker[k]) is int and marker[k]>0 for k in ('pid','created_ns'))
          and type(marker['parent_pid']) is int and marker['parent_pid']>=0
          and marker['pid']==native['pid'] and marker['parent_pid']==native['parent_pid'],
          'Counted launch provenance differs from native execution')
    outcome=_json(path_in(run,root+'/refine/counted.json'))
    expected=dict(admission_record_sha256=admission['record_sha256'],prepared_sha256=admission['prepared_sha256'],
        compiled_binding_sha256=admission['compiled_binding_sha256'],
        provider_selection_sha256=admission['provider_selection_sha256'],scope_sha256=_digest(admission['scope']),
        recipe_sha256=request['counted_intent']['current_recipe_sha256'])
    _need(all(outcome.get(k)==v for k,v in expected.items()),
          'Completed counted phase consumed a different admission or preparation')
