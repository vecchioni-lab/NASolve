"""Durable explicit component acquisition over the existing cache/generator/qualifier.

The selected source is already declared. No source discovery, multi-component
preparation, ordinary adoption or automatic retry loop is implemented here.
"""
from copy import deepcopy
from hashlib import sha256
import math
import os
from pathlib import Path
from time import monotonic
import uuid

from .failure_reporting import add_failure_note
from .campaign_process import CampaignProcessError, coordinator_alive, current_process_identity, exclusive_lock
from .campaign_records import _sync_directory, now, path_in, read_record, write_record
from .cif_component_runtime import _tree
from .cif_dictionary_store import _bytes, _json, make_dictionary_request, resolve_dictionary_snapshot, recipe_representation_policy
from .cif_dictionary_sites import _consumer, _read, _safe
from .cif_generation_acquisition import generation_dictionary_options, resolve_generated_dictionary
from .cif_generation_attempt import _attempt_identity, generate_source_candidate_attempt, inspect_source_generation_request
from .cif_generation_process import _valid_identity, _valid_attempt_identity
from .cif_outer_context import OuterAllowance, parent_identity
from .cif_candidate_qualification import inspect_candidate_qualification_processes
from .cif_candidate_qualification_execution import execute_candidate_qualification, read_candidate_qualification, _inputs
from .cif_repair_attempt import _root, _members, _inventory
from .cif_repair_process import _uuid

POLICY_ID = 'cif-component-acquisition-request-v1'
ANCHOR = 'request_directory'
_SNAPSHOT_FILES = {'resolution.json','entry/manifest.json','entry/source.cif','entry/dictionary.cif','entry/qualification.json','entry/provenance.json'}


class AcquisitionBudgetExceeded(TimeoutError):
    """The shared component allowance expired; no successful attempt is returned."""


def _need(value, message='Invalid component acquisition evidence'):
    if not value:raise ValueError(message)


def _generation_binding(generation):
    root=Path(os.path.abspath(generation['installation_root']))
    dispatchers={name:Path(os.path.abspath(generation[key])).relative_to(root).as_posix()
                 for name,key in [('python','python_executable'),('elbow','elbow_executable')]}
    _need(all(_safe(path) for path in dispatchers.values()), 'Require anchored generation dispatchers')
    return dict(dispatchers=dispatchers,timeout_seconds=generation.get('timeout_seconds',600),max_attempts=generation.get('max_attempts',2))


def _configuration(source, code, authority, options, consumer, binding, inputs, limits, max_attempts):
    _consumer(consumer)
    _need(set(limits)=={'native_timeout_seconds','total_timeout_seconds'}
          and all(type(v) is int and 1<=v<=(600 if k=='native_timeout_seconds' else 3600) for k,v in limits.items()), 'Require bounded integer acquisition deadlines')
    _need(type(max_attempts) is int and 1<=max_attempts<=5, 'Require one to five acquisition attempts')
    _need(isinstance(binding,dict) and set(binding)=={'dispatchers','timeout_seconds','max_attempts'}
          and set(binding['dispatchers'])=={'python','elbow'} and all(_safe(v) for v in binding['dispatchers'].values())
          and type(binding['timeout_seconds']) in (int,float) and math.isfinite(binding['timeout_seconds']) and 0<binding['timeout_seconds']<=600
          and type(binding['max_attempts']) is int and 1<=binding['max_attempts']<=5, 'Invalid generation execution binding')
    return _json(_bytes(dict(dictionary_request=make_dictionary_request(source,code,source_authority=authority,**options),consumer=consumer,
        generation_binding=binding,input_files=_inventory(inputs),limits=limits,max_attempts=max_attempts)))


def _request(root):
    request=read_record(path_in(root,'request.json'));config=request.get('configuration')
    _need(type(request.get('schema_version')) is int and request['schema_version']==1 and request.get('policy_id')==POLICY_ID
          and _uuid(request.get('request_id')) and request.get('inputs')==dict(anchor=ANCHOR,path='inputs') and isinstance(config,dict))
    inputs=_tree(root/'inputs');_need(set(inputs)=={'source.cif'} or set(inputs)=={'source.cif'}|{'retained/'+n for n in _SNAPSHOT_FILES}, 'Unexpected acquisition inputs')
    req=config['dictionary_request'];options={k:req[k] for k in ('recipe','generator')}
    expected=_configuration(root/'inputs/source.cif',req['component'],req['source_authority'],options,config['consumer'],config['generation_binding'],inputs,config['limits'],config['max_attempts'])
    _need(config==expected, 'Frozen acquisition source or configuration changed')
    if 'retained/resolution.json' in inputs:
        saved=resolve_dictionary_snapshot(root/'inputs/retained');prior=saved['manifest']['request']
        _need(make_dictionary_request(root/'inputs/source.cif',req['component'],source_authority=req['source_authority'],**{k:prior[k] for k in ('recipe','generator')})==prior
              and recipe_representation_policy(prior['recipe'])==recipe_representation_policy(req['recipe']), 'Retained source/authority/permission differs')
    return request


def _generation_child(root, attempt, intent, config, *, closed_no_child=False):
    linkpath=path_in(attempt,'generation.json')
    if not linkpath.exists():return dict(state='NOT_CREATED',activity=False),None
    link=read_record(linkpath);number=link.get('number')
    _need(link.get('attempt_sha256')==intent['record_sha256'] and type(number) is int and 1<=number<=5
          and link.get('request_directory')==dict(anchor=ANCHOR,path='generation'), 'Generation reservation belongs to another attempt')
    state=inspect_source_generation_request(root/'generation');proof=dict(link=link['record_sha256'],request=None,attempt=None,finished=None,files=None)
    if state['state']=='NOT_RECORDED':return dict(state='NOT_CREATED',activity=False),proof
    if state['state']!='RECORDED':return dict(state='NOT_CREATED' if closed_no_child else 'UNKNOWN',activity=False if closed_no_child else None),proof
    request=state['request'];g=request['configuration'];r=config['dictionary_request'];b=config['generation_binding']
    _need(link.get('request_sha256') in (None,request['record_sha256']) and g['source']=={'sha256':r['source_sha256'],'size':r['source_size']}
          and g['component']==r['component'] and g['max_attempts']==b['max_attempts']
          and g['recipe']==dict(expected_dialect=r['recipe']['expected_dialect'],single_block_steps=r['recipe']['single_block_steps'],timeout_seconds=b['timeout_seconds'],bond_representation_policy=r['recipe'].get('bond_representation_policy'),
              **({'multiple_planes':True} if r['recipe'].get('multiple_planes') is True else {}),
              **({'source_input_policy':r['recipe']['source_input_policy']} if 'source_input_policy' in r['recipe'] else {}))
          and all(g['generator'][k]==r['generator'][k] for k in ('api_sources','prior_sources'))
          and g['generator']['phenix_version']==r['generator']['version'], 'Shared generation request identity differs')
    # A next-slot observation is not a reservation. A failed preflight may leave
    # that slot for a later outer attempt. Only the durable parent digest/UUID
    # binds a child; never adopt it merely because its number became available.
    matching=[row for row in state['attempts'] if row.get('intent',{}).get('parent_attempt')==_attempt_identity(intent)]
    _need(len(matching)<=1, 'Multiple generation children belong to one acquisition attempt')
    if not matching:
        unknown=any('intent' not in row for row in state['attempts']) and not closed_no_child
        return dict(state='UNKNOWN' if unknown else 'NOT_CREATED',activity=None if unknown else False),proof
    child=matching[0];owner=child['intent']
    _need(child['number']==number and all(owner['coordinator'].get(k)==intent['coordinator'].get(k)
          for k in ('pid','pgid','host','boot_id','start_marker')), 'Generation belongs to another acquisition coordinator')
    proof['request']=request['record_sha256']
    proof.update(attempt=owner['record_sha256'],finished=child.get('finished',{}).get('record_sha256'))
    if child['state'] in {'STOPPED','STOPPED_UNFINISHED'}:
        proof['files']=_inventory(_tree(root/'generation/attempts'/f'attempt-{number:04d}'))
    return child,proof


def _qualification_child(attempt,intent,config):
    work=path_in(attempt,'qualification/native')
    if not work.exists():return dict(state='NOT_CREATED',activity=False),None
    state=inspect_candidate_qualification_processes(work);header=state.get('header')
    if header is not None:
        _need(header.get('attempt_owner')==_attempt_identity(intent)
              and all(header['coordinator'].get(k)==intent['coordinator'].get(k) for k in ('pid','pgid','host','boot_id','start_marker')), 'Qualification belongs to another acquisition owner')
        protocol,paths,_,_=_inputs(work);r=config['dictionary_request'];limits=config['limits']
        _need(protocol['component']==r['component'] and protocol['consumer']==config['consumer']
              and protocol['bond_representation_policy']==r['recipe'].get('bond_representation_policy')
              and protocol['native_timeout_seconds']==limits['native_timeout_seconds']
              and protocol['total_timeout_seconds']<=limits['total_timeout_seconds']
              and sha256(_read(paths[0])).hexdigest()==r['source_sha256'], 'Qualification source/consumer/allowance differs')
    return state,dict(header=header['record_sha256'] if header else None,finished=state.get('finished',{}).get('record_sha256'))


def _children(root,attempt,intent,config, *, closed_no_child=False):
    g,gb=_generation_child(root,attempt,intent,config,closed_no_child=closed_no_child);q,qb=_qualification_child(attempt,intent,config)
    return {'generation':g,'qualification':q},{'generation':gb,'qualification':qb}


def _attempt_files(attempt):
    return {n:v for n,v in _inventory(_tree(attempt)).items() if n!='finished.json'}


def _result(root,attempt,config):
    report=read_record(path_in(attempt,'result.json'));elapsed=report.get('elapsed_seconds')
    _need(set(report)=={'schema_version','policy_id','snapshot','acquisition','elapsed_seconds','record_sha256'}
          and type(report.get('schema_version')) is int and report['schema_version']==1 and report.get('policy_id')==POLICY_ID
          and report.get('snapshot')==dict(anchor='attempt_directory',path='snapshot')
          and type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<=elapsed<config['limits']['total_timeout_seconds'], 'Invalid acquisition result/allowance')
    saved=resolve_dictionary_snapshot(attempt/'snapshot');req=saved['manifest']['request'];allowed=[config['dictionary_request']]
    if (root/'inputs/retained').exists():allowed.append(resolve_dictionary_snapshot(root/'inputs/retained')['manifest']['request'])
    _need(saved['report']==report['acquisition'] and req in allowed and saved['manifest']['consumer']==config['consumer']
          and _read(saved['source'])==_read(root/'inputs/source.cif'), 'Acquisition snapshot identity differs')
    if (attempt/'qualification/native').exists():
        qualification=read_candidate_qualification(attempt/'qualification/native')
        _need(saved['qualification']==qualification['qualification'], 'Acquisition differs from its scientific qualification')
    if (attempt/'generation.json').exists():
        link=read_record(attempt/'generation.json');child=root/'generation/attempts'/f"attempt-{link['number']:04d}"
        _need(_read(saved['dictionary'])==_read(child/'generation/candidate.cif')
              and saved['provenance']['generation_acquisition']['attempt_id']==read_record(child/'attempt.json')['attempt_id'], 'Acquisition differs from its generated candidate')
    return saved


def _attempt_state(root,attempt,number,request):
    # Atomic store publication may leave a private temporary directory on a hard kill.
    temporary={p.name for p in attempt.iterdir() if p.name.startswith('dictionary-snapshot-') and p.is_dir()}
    _members(attempt,{'attempt.json','finished.json','generation.json','result.json'},{'qualification','snapshot'}|temporary)
    result=dict(number=number,state='UNKNOWN',activity=None)
    if not (attempt/'attempt.json').exists():
        _need(not any(p.name!='attempt.json' for p in attempt.iterdir()), 'Acquisition output has no intent')
        return result
    intent=read_record(attempt/'attempt.json');_need(intent.get('request_sha256')==request['record_sha256']
        and type(intent.get('number')) is int and intent['number']==number and _uuid(intent.get('attempt_id')) and _valid_identity(intent.get('coordinator'))
        and ('parent_attempt' not in intent or _valid_attempt_identity(intent['parent_attempt'])))
    finished=read_record(attempt/'finished.json') if (attempt/'finished.json').exists() else None
    caller=coordinator_alive(intent['coordinator']) if finished is None else None
    children,binding=_children(root,attempt,intent,request['configuration'],closed_no_child=finished is not None and finished.get('children',{}).get('generation') is not None and finished['children']['generation'].get('attempt') is None);result.update(intent=intent,children=children)
    if finished is not None:
        _need(finished.get('attempt_sha256')==intent['record_sha256'] and finished.get('outcome') in {'RETURNED','RAISED'}
              and finished.get('stopped_verified') is True and finished.get('children')==binding
              and finished.get('files')==_attempt_files(attempt)
              and all(v['state'] in {'STOPPED','NOT_CREATED'} for v in children.values()), 'Acquisition completion does not bind stopped children/files')
        if finished['outcome']=='RETURNED':_result(root,attempt,request['configuration'])
        return dict(result,state='STOPPED',activity=False,finished=finished)
    safe=caller is False and all(v['state'] in {'STOPPED','STOPPED_UNFINISHED','NOT_CREATED'} for v in children.values())
    live=caller is True or any(v.get('activity') is True for v in children.values())
    return dict(result,coordinator_activity=caller,state='STOPPED_UNFINISHED' if safe else 'LIVE' if live else 'UNKNOWN',activity=False if safe else True if live else None)


def inspect_acquisition_request(directory):
    """Observe advisory availability without writes, locks, signals or retry authority."""
    root=_root(directory);result=dict(schema_version=1,policy_id=POLICY_ID,state='NOT_RECORDED',availability='BLOCKED',retry_authorized=False,attempts=[],scope='DECLARED_COMPONENT_ACQUISITION_ONLY')
    if not root.exists():return result
    _members(root,{'request.json','request.lock'},{'inputs','attempts','generation'})
    if not (root/'request.json').exists():return dict(result,state='UNKNOWN')
    request=_request(root);rows=[];folder=path_in(root,'attempts')
    if folder.exists():
        _need(folder.is_dir())
        for number,p in enumerate(sorted(folder.iterdir()),1):
            _need(not p.is_symlink() and p.is_dir() and p.name==f'attempt-{number:04d}', 'Acquisition attempts must be consecutive immutable directories')
            rows.append(_attempt_state(root,p,number,request))
    generation=inspect_source_generation_request(root/'generation')
    foreign_or_unknown=generation['state'] not in {'NOT_RECORDED','RECORDED'}
    if generation['state']=='RECORDED':
        parents=[_attempt_identity(row['intent']) for row in rows if 'intent' in row]
        for child in generation['attempts']:
            if 'intent' not in child:foreign_or_unknown=True
            else:_need(child['intent'].get('parent_attempt') in parents, 'Shared generation has an unowned acquisition child')
    limit=request['configuration']['max_attempts'];_need(len(rows)<=limit,'Acquisition attempt allowance exceeded')
    safe=not foreign_or_unknown and all(r['state'] in {'STOPPED','STOPPED_UNFINISHED'} for r in rows)
    return dict(result,state='RECORDED',request=request,attempts=rows,availability='BLOCKED' if not safe else 'EXHAUSTED' if len(rows)==limit else 'AVAILABLE')


def _seal(root,attempt,intent,request,outcome,error=None):
    children,binding=_children(root,attempt,intent,request['configuration'])
    if any(v['state'] not in {'STOPPED','NOT_CREATED'} for v in children.values()):raise CampaignProcessError('Acquisition has unresolved native ownership')
    if outcome=='RETURNED':_result(root,attempt,request['configuration'])
    write_record(attempt/'finished.json',dict(attempt_sha256=intent['record_sha256'],outcome=outcome,error_type=error,
        stopped_verified=True,finished_utc=now(),children=binding,files=_attempt_files(attempt)))


def read_acquisition_result(directory,attempt_number):
    """Read one exact successfully sealed attempt; never infer latest or selected."""
    state=inspect_acquisition_request(directory)
    _need(type(attempt_number) is int and 1<=attempt_number<=len(state['attempts']), 'Require an exact recorded attempt number')
    row=state['attempts'][attempt_number-1]
    _need(row['state']=='STOPPED' and row['finished']['outcome']=='RETURNED', 'Acquisition attempt did not complete successfully')
    root=_root(directory)
    return _result(root,root/'attempts'/f'attempt-{attempt_number:04d}',state['request']['configuration'])


def acquire_dictionary_attempt(source,code,store_root,request_directory,*,source_authority,consumer,generation,phenix=None,
        retained_snapshot=None,native_timeout_seconds=90,total_timeout_seconds=600,max_attempts=2,
        _parent_attempt_identity=None,_remaining_seconds=None):
    """Perform one explicit cache-first attempt; preserve every prior output.

    All callers share the request directory. Source/declared recipe/consumer and
    limits are frozen; cache location is an explicit per-call binding, not saved
    operational provenance. The one shared generation request retains its own
    immutable producer and finite allowance across outer attempts. No SDK is
    discovered on a qualified cache hit. The total clock starts before preflight;
    local work, final sealing and cleanup remain cooperative. Optional enclosing
    identity is recorded per attempt, not in the persistent request configuration.
    A remaining-allowance callback can shorten, never reset, nested work limits.
    """
    started=monotonic();parent=parent_identity(_parent_attempt_identity)
    outer=OuterAllowance(_remaining_seconds,monotonic,AcquisitionBudgetExceeded)
    generation=deepcopy(generation);consumer=_json(_bytes(consumer))
    def remaining(minimum=0):
        cap=outer.remaining()
        value=total_timeout_seconds-(monotonic()-started)
        if cap is not None:value=min(value,cap)
        if value<=0 or value<minimum:raise AcquisitionBudgetExceeded('Component acquisition allowance exhausted; partial output grants no successful result')
        return value
    root=_root(request_directory);store=_root(store_root);source=Path(source).absolute();original=_read(source)
    installation=Path(generation['installation_root']).resolve()
    _need(not store.is_relative_to(root) and not root.is_relative_to(store) and not root.is_relative_to(installation)
          and not installation.is_relative_to(root) and not source.resolve().is_relative_to(root), 'Acquisition request overlaps source, cache or installation')
    if phenix is not None:
        sdk=Path(phenix.root).resolve();_need(not root.is_relative_to(sdk) and not sdk.is_relative_to(root),'Acquisition request overlaps qualification installation')
    if root.exists():
        _members(root,{'request.json','request.lock'},{'inputs','attempts','generation'})
        if not (root/'request.json').exists() and any(p.name!='request.lock' for p in root.iterdir()):raise CampaignProcessError('Acquisition initial publication is unresolved')
    inputs={'source.cif':original};retained=None;retained_before=None
    if retained_snapshot is not None:
        retained=_root(retained_snapshot);_need(not retained.is_relative_to(root) and not root.is_relative_to(retained),'Retained snapshot overlaps acquisition request')
        resolve_dictionary_snapshot(retained);retained_before=_tree(retained);_need(set(retained_before)==_SNAPSHOT_FILES,'Unexpected retained snapshot members')
        inputs.update({'retained/'+n:b for n,b in retained_before.items()})
    options=generation_dictionary_options(generation);limits=dict(native_timeout_seconds=native_timeout_seconds,total_timeout_seconds=total_timeout_seconds)
    config=_configuration(source,code,source_authority,options,consumer,_generation_binding(generation),inputs,limits,max_attempts)
    # Validate retained authority before creating a request, using the same source recipe rules.
    if retained is not None:
        prior=resolve_dictionary_snapshot(retained)['manifest']['request']
        _need(make_dictionary_request(source,code,source_authority=source_authority,**{k:prior[k] for k in ('recipe','generator')})==prior
              and recipe_representation_policy(prior['recipe'])==recipe_representation_policy(options['recipe']), 'Retained source/authority/permission differs')
    remaining();coordinator=current_process_identity();root.mkdir(parents=True,exist_ok=True)
    with exclusive_lock(root/'request.lock'):
        if not (root/'request.json').exists():
            if {p.name for p in root.iterdir()}!={'request.lock'}:raise CampaignProcessError('Acquisition initial publication is unresolved')
            for name,data in inputs.items():
                path=root/'inputs'/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            for folder in sorted({root/'inputs',*[p for p in (root/'inputs').rglob('*') if p.is_dir()]},key=lambda p:len(p.parts),reverse=True):_sync_directory(folder)
            write_record(root/'request.json',dict(schema_version=1,policy_id=POLICY_ID,request_id=str(uuid.uuid4()),created_utc=now(),inputs=dict(anchor=ANCHOR,path='inputs'),configuration=config))
        state=inspect_acquisition_request(root);request=state['request'];_need(request['configuration']==config,'Acquisition identity differs from frozen request')
        if state['availability']!='AVAILABLE':raise CampaignProcessError('Acquisition request has '+('exhausted attempt allowance' if state['availability']=='EXHAUSTED' else 'unresolved previous attempt'))
        remaining();_need(_read(source)==original and (retained is None or _tree(retained)==retained_before),'Selected acquisition inputs changed')
        number=len(state['attempts'])+1;attempt=root/'attempts'/f'attempt-{number:04d}';attempt.mkdir(parents=True,exist_ok=False)
        intent=write_record(attempt/'attempt.json',dict(request_sha256=request['record_sha256'],number=number,attempt_id=str(uuid.uuid4()),coordinator=coordinator,created_utc=now(),
            **({'parent_attempt':parent} if parent is not None else {})))
        def generate(**kwargs):
            remaining();child=inspect_source_generation_request(root/'generation')
            _need(child['state']=='NOT_RECORDED' or child['availability']=='AVAILABLE','Shared generation request is blocked or exhausted')
            child_number=len(child['attempts'])+1
            write_record(attempt/'generation.json',dict(attempt_sha256=intent['record_sha256'],number=child_number,
                request_directory=dict(anchor=ANCHOR,path='generation'),request_sha256=child.get('request',{}).get('record_sha256')))
            return generate_source_candidate_attempt(**kwargs,_parent_attempt_identity=_attempt_identity(intent),_remaining_seconds=remaining)
        def qualify(a,b,current,out):
            allowance=int(remaining(1))
            return execute_candidate_qualification(a,b,code,current,phenix,out,native_timeout_seconds=native_timeout_seconds,
                total_timeout_seconds=allowance,bond_representation_policy=options['recipe'].get('bond_representation_policy'),
                _attempt_identity=_attempt_identity(intent),_remaining_seconds=remaining)['qualification']
        try:
            result=resolve_generated_dictionary(root/'inputs/source.cif',code,store,attempt/'snapshot',root/'generation',attempt/'qualification',
                source_authority=source_authority,consumer=consumer,generation=generation,qualify=qualify,
                retained_snapshot=root/'inputs/retained' if retained is not None else None,_generate=generate)
            _need(_read(source)==original and _tree(root/'inputs')==inputs and (retained is None or _tree(retained)==retained_before),'Acquisition inputs changed during execution')
            remaining();elapsed=monotonic()-started
            write_record(attempt/'result.json',dict(schema_version=1,policy_id=POLICY_ID,snapshot=dict(anchor='attempt_directory',path='snapshot'),acquisition=result,elapsed_seconds=elapsed))
            _result(root,attempt,config);remaining();_seal(root,attempt,intent,request,'RETURNED')
        except BaseException as exc:
            try:_seal(root,attempt,intent,request,'RAISED',type(exc).__name__)
            except Exception as seal_error:add_failure_note(exc, 'Acquisition completion could not be sealed', seal_error)
            raise
        return dict(schema_version=1,policy_id=POLICY_ID,request_id=request['request_id'],attempt_id=intent['attempt_id'],attempt_number=number,
            dictionary_directory=dict(anchor=ANCHOR,path=f'attempts/attempt-{number:04d}/snapshot'),acquisition=result)
