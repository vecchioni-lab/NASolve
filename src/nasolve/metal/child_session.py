"""One opt-in audited frozen child; no checkpoint acceptance, search or pruning.

Compose the existing parent, reflection, process and scientific audit owners.
Each invocation retains a distinct session and one bounded child attempt.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import math
import zlib

from .. import campaign_records as records
from ..campaigns import CampaignError
from ..refine_doctor import audit_free_r_flags
from . import child_inputs, child_process, child_outputs, parent_archive
from .context import parse_pdb
from .fdp import audit_result
from .materialize import _json
from .recipe import RecipeError, canonical, checksum, digest
from .scattering import inspect_observations, reference_scattering

KIND = 'metal-fdp-audited-child-review'
MAX_NATIVE_JSON_BYTES = 64 * 1024 * 1024


def _same(actual, expected, label):
    if canonical(actual) != canonical(expected):
        raise RecipeError(label+' differs from the frozen request')


def _fresh_scattering(prepared, plan, native, *, command_runners=None):
    options={} if command_runners is None else dict(command_runner=command_runners['observations'])
    metadata=inspect_observations(prepared/'observations.mtz',
        executable=native.executables['phenix.mtz.dump'],environment=native.environment,**options)
    _same(metadata,plan['metadata'],'Fresh observation metadata')
    symbols={a.element for a in parse_pdb((prepared/'input.pdb').read_bytes()).snapshot.atoms}
    options={} if command_runners is None else dict(command_runner=command_runners['scattering'])
    references=reference_scattering(symbols,metadata['wavelength_A'],
        executable=native.executables['phenix.python'],version=native.version,environment=native.environment,**options)
    fresh=dict(observations=metadata,references=references,discovered_version=native.version)
    _check_scattering_record(fresh,plan)
    return fresh


def _check_scattering_record(fresh,plan):
    _same(fresh['observations'],plan['metadata'],'Fresh observation metadata')
    # Discovery labels are provenance; actual native build/table/value fields match.
    normalize=lambda rows:[{k:v for k,v in row.items() if k!='phenix_version'} for row in rows]
    _same(normalize(fresh['references']),normalize(plan['references']),'Fresh scattering references')


def _audit_job(job,plan,model):
    try:
        with gzip.open(job/'native-result.json.gz','rb') as handle:
            raw=handle.read(MAX_NATIVE_JSON_BYTES+1)
    except (OSError,EOFError,zlib.error) as exc:
        raise RecipeError('Cannot read native audit evidence: '+str(exc)) from exc
    child_process._need(len(raw)<=MAX_NATIVE_JSON_BYTES,'Native audit JSON exceeds byte budget')
    evidence=_json(raw);result=audit_result(plan,model,evidence)
    initial=parse_pdb(model);final=parse_pdb((job/'final.pdb').read_bytes())
    if initial.snapshot.atoms!=final.snapshot.atoms or canonical(initial.to_dict()['atomic_state'])!=canonical(final.to_dict()['atomic_state']):
        raise RecipeError('Serialized final PDB changed frozen atomic state')
    if 'anomalous_map' in evidence:
        from .anomalous_maps import verify_file
        verify_file(evidence['anomalous_map'],job)
    return result


def run_audited_child(prepared_directory,parent_directory,request,*,request_id,
                      run_relative,endpoint_relative,session_directory,native,
                      timeout_seconds=240,reader_control_policy=None,
                      max_parent_disk_bytes=parent_archive.DEFAULT_DISK_BYTES,
                      max_output_bytes=child_outputs.DEFAULT_MAX_BYTES,retained_parent=None,owned_preflight=False,storage_budget=None):
    """Derive, freshly inspect, execute and audit one conditional frozen fit.

    FDP_REVIEW means the declared frozen calculation passed its audits; it does
    not accept geometry, metal identity/count, convergence or scientific fitness.
    Failed sessions remain distinct and retained. No implicit retry is performed.
    """
    child_process._need(type(owned_preflight) is bool,'Owned input inspection must be explicitly boolean')
    child_process._need(storage_budget is None or (owned_preflight and retained_parent is not None),
                       'Session budget requires owned preflight and a live budgeted retained parent')
    request=child_process._request(request,request_id)
    child_process._need(request['schema_version']==2,'Audited child requires a helper-pinned request')
    child_process._need(type(timeout_seconds) in (int,float) and math.isfinite(timeout_seconds)
        and 0<timeout_seconds<=600,'Require a bounded positive child deadline')
    child_process._need(type(max_output_bytes) is int and 0<max_output_bytes<=child_outputs.MAX_BYTES,
        'Invalid output byte budget')
    prepared=child_process._root(prepared_directory);parent=child_process._root(parent_directory)
    scope=parent_archive.retained_parent_binding(retained_parent,parent,request['parent_manifest_sha256']) if retained_parent is not None else None
    lifetime=dict(parent_scope=scope) if scope is not None else {}
    inspection_mode=dict(owned_preflight=True) if owned_preflight else {}
    payload=child_process._inputs(prepared,request['files']);child_process._declared_plan(payload)
    child_process._worker_payload(Path(child_process.__file__).parent,request['worker_files'])
    session=Path(session_directory).expanduser().absolute()
    child_process._need(not session.exists() and not session.is_symlink() and session.parent.is_dir()
        and not any(p.is_symlink() for p in session.parents)
        and not session.resolve().is_relative_to(prepared) and not session.resolve().is_relative_to(parent),
        'Require a new session outside prepared inputs and parent archive')
    options=dict(request_id=request_id,run_relative=run_relative,endpoint_relative=endpoint_relative,
        reader_control_policy=reader_control_policy,max_parent_disk_bytes=max_parent_disk_bytes,retained_parent=retained_parent)
    before=child_inputs.verify_child_inputs(prepared,parent,request,**options)
    plan=_json(payload['plan.json']);model=payload['input.pdb']
    admission=None
    if storage_budget is not None:
        from . import storage_budget as budget_owner
        known=sum(map(len,payload.values()))+sum(ref['size'] for ref in request['worker_files'].values())
        _,grant,minimum=budget_owner._reserve_audited_execution(storage_budget,session=session,request_id=request_id,
            known_input_bytes=known,max_output_bytes=max_output_bytes,retained_parent=retained_parent)
        admission=dict(kind=budget_owner.SESSION_ADMISSION,schema_version=1,reservation_id=grant['reservation_id'],
            grant={k:v for k,v in grant.items() if k!='reservation_id'},minimum_allowance_bytes=minimum,
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
    session.mkdir()
    if admission is not None:records.write_record(session/'storage-admission.json',admission)
    stage='FRESH_INPUT_INSPECTION'
    proofs={}
    def record(name,value):
        proofs[name]=records.write_record(session/name,value)
    try:
        storage_binding={} if admission is None else dict(storage_reservation=dict(
            budget_id=grant['budget_id'],reservation_id=grant['reservation_id']))
        record('request.json',dict(request=request,run_relative=run_relative,
            endpoint_relative=endpoint_relative,timeout_seconds=timeout_seconds,max_output_bytes=max_output_bytes,
            **lifetime,**inspection_mode,**storage_binding))
        record('parent-before.json',before)
        if owned_preflight:
            from . import preflight_process
            checked=preflight_process.run_preflight(prepared,request,request_id=request_id,directory=session/'preflight',
                native=native,timeout_seconds=timeout_seconds,fresh_scattering=_fresh_scattering,audit_flags=audit_free_r_flags)
            verified=preflight_process.inspect_preflight(session/'preflight',inspection_id=checked['record_sha256'])
            fresh=verified['fresh_inputs'];free_r=verified['free_r']
            record('fresh-inputs.json',fresh)
            record('owned-preflight.json',dict(directory=dict(anchor='session',relative_path='preflight'),inspection_id=checked['record_sha256']))
        else:
            fresh=_fresh_scattering(prepared,plan,native)
            record('fresh-inputs.json',fresh)
            audit=audit_free_r_flags(prepared/'observations.mtz',plan['metadata']['free_r_label'],
                plan['policy']['free_r_test_value'],native.executables['phenix.python'],session,
                environment=native.environment)
            free_r=dict(status=audit.status,usable=audit.valid,details=audit.details,warnings=list(audit.warnings))
        record('free-r.json',free_r)
        if not free_r['usable']:raise RecipeError('Original Free-R audit failed; see retained free-r.json')
        child_process._inputs(prepared,request['files'])
        stage='OWNED_NATIVE_CHILD'
        process=child_process.run_child(prepared,parent,request,request_id=request_id,
            attempt_directory=session/'attempt',native=native,timeout_seconds=timeout_seconds,
            max_parent_disk_bytes=max_parent_disk_bytes,retained_parent=retained_parent)
        if process['status']!='COMPLETED' or not process['stopped_verified']:
            raise RecipeError('Native child did not complete with a verified stop: '+process['status'])
        stage='SCIENTIFIC_AUDIT'
        output=child_outputs.freeze_child_outputs(session/'attempt',request_id=request_id,max_bytes=max_output_bytes)
        job=session/'attempt/native/fdp/job'
        result=_audit_job(job,plan,model)
        after=child_inputs.verify_child_inputs(prepared,parent,request,**options)
        _same(after,before,'Post-run parent derivation')
        child_outputs.inspect_child_outputs(session/'attempt',request_id=request_id,output_id=output['record_sha256'])
        record('parent-after.json',after)
        stage='REVIEW_PUBLICATION'
        if scope is not None:
            _same(parent_archive.retained_parent_binding(retained_parent,parent,request['parent_manifest_sha256']),scope,'Retained parent lifetime')
            _same(process['outcome']['parent_scope'],scope,'Native child parent lifetime')
        for name,recorded in proofs.items():
            _same(records.read_record(session/name),recorded,'Session proof '+name)
        proof_names=sorted(proofs)
        files={name:dict(anchor='session',relative_path=name,size=(session/name).stat().st_size,
            sha256=sha256((session/name).read_bytes()).hexdigest()) for name in proof_names}
        return records.write_record(session/'review.json',dict(kind=KIND,schema_version=3 if owned_preflight else 2 if scope is not None else 1,status='FDP_REVIEW',
            request_id=request_id,parent_manifest_sha256=request['parent_manifest_sha256'],
            parent_derivation_before=before['derivation_id'],parent_derivation_after=after['derivation_id'],
            attempt=dict(anchor='session',relative_path='attempt'),output_evidence_id=output['record_sha256'],
            files=files,result=result,fresh_metadata=True,fresh_scattering=True,fresh_free_r_audit=True,
            serialized_model_unchanged=True,scientific_acceptance='NOT_ASSESSED',
            automatic_checkpoint_selection=False,reuse_authorized=False,retirement_authorized=False,
            **(dict(owned_preflight=True,parent_scope=scope) if owned_preflight else lifetime)))
    except BaseException as exc:
        failure=dict(kind='metal-fdp-audited-child-failure',schema_version=1,
            request_id=request_id,stage=stage,error=type(exc).__name__,message=str(exc),
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
        if admission is not None:
            declaration=proofs.get('request.json')
            stop=None
            if declaration is not None and stage in FAILED_STOP_STAGES:
                try:stop=_failed_stop_evidence(session,declaration)
                except (OSError,ValueError,KeyError,TypeError,CampaignError):pass
            if declaration is not None and stage=='FRESH_INPUT_INSPECTION':
                try:stop=_failed_preflight_stop_evidence(session,declaration)
                except (OSError,ValueError,KeyError,TypeError,CampaignError):pass
            failure.update(schema_version=3 if stage=='FRESH_INPUT_INSPECTION' else 2,
                           session_declaration_sha256=(declaration or {}).get('record_sha256'),
                           process_stop_evidence=stop)
        records.write_record(session/'failure.json',failure)
        if isinstance(exc,(RecipeError,KeyboardInterrupt,SystemExit)):raise
        raise RecipeError('Audited child failed at '+stage+': '+str(exc)) from exc


def _session_record(root,name):
    path=child_process._file(root,name)
    child_process._need(path.stat().st_size<=child_outputs.MAX_RECORD_BYTES,'Session record exceeds byte budget')
    return records.read_record(path)


def _saved_proofs(root,review):
    names={'request.json','parent-before.json','parent-after.json','fresh-inputs.json','free-r.json'}
    if review.get('schema_version')==3:names.add('owned-preflight.json')
    refs=review.get('files')
    child_process._need(isinstance(refs,dict) and set(refs)==names,'Incomplete or unexpected session proof inventory')
    result={}
    for name,ref in refs.items():
        child_process._need(isinstance(ref,dict) and set(ref)=={'anchor','relative_path','size','sha256'}
            and ref['anchor']=='session' and ref['relative_path']==name
            and type(ref['size']) is int and 0<ref['size']<=child_outputs.MAX_RECORD_BYTES,'Invalid session proof reference')
        checksum(ref['sha256'],'session proof')
        path=child_process._file(root,name)
        child_process._need(path.stat().st_size==ref['size'],'Session proof size changed')
        with path.open('rb') as handle:raw=handle.read(ref['size']+1)
        child_process._need(len(raw)==ref['size'] and sha256(raw).hexdigest()==ref['sha256'],'Session proof bytes changed')
        result[name]=_session_record(root,name)
    return result


def inspect_audited_child(session_directory,*,review_id):
    """Read and re-audit saved evidence without originals or native execution.

    Parent derivation and Free-R/scattering acquisition are recorded checks, not
    newly executed checks. This read grants no reuse, acceptance or retirement.
    """
    checksum(review_id,'independent audited child review')
    root=child_process._root(session_directory)
    try:
        review=_session_record(root,'review.json')
        child_process._need(review['record_sha256']==review_id,'Audited child review identity changed')
        fields={'kind','schema_version','status','request_id','parent_manifest_sha256','parent_derivation_before',
            'parent_derivation_after','attempt','output_evidence_id','files','result','fresh_metadata','fresh_scattering',
            'fresh_free_r_audit','serialized_model_unchanged','scientific_acceptance','automatic_checkpoint_selection',
            'reuse_authorized','retirement_authorized','record_sha256'}
        version=review.get('schema_version')
        if version in (2,3):fields.add('parent_scope')
        if version==3:fields.add('owned_preflight')
        child_process._need(set(review)==fields and review['kind']==KIND
            and type(version) is int and version in (1,2,3)
            and (version!=3 or review['owned_preflight'] is True)
            and review['status']=='FDP_REVIEW' and review['scientific_acceptance']=='NOT_ASSESSED'
            and all(review[k] is True for k in ('fresh_metadata','fresh_scattering','fresh_free_r_audit','serialized_model_unchanged'))
            and all(review[k] is False for k in ('automatic_checkpoint_selection','reuse_authorized','retirement_authorized')),
            'Unsupported audited child review')
        _same(review['attempt'],dict(anchor='session',relative_path='attempt'),'Session attempt')
        proofs=_saved_proofs(root,review);declaration=proofs['request.json']
        request=child_process._request(declaration['request'],review['request_id'])
        child_process._need(request['schema_version']==2,'Session requires a helper-pinned child')
        _same(request['parent_manifest_sha256'],review['parent_manifest_sha256'],'Session protected parent')
        attempt=root/'attempt'
        _same(_json((attempt/'inputs/request.json').read_bytes()),request,'Copied child request')
        seal=child_outputs.inspect_child_outputs(attempt,request_id=review['request_id'],output_id=review['output_evidence_id'])
        outcome=records.read_record(attempt/'outcome.json')
        lifetime_version=2 if version==2 or (version==3 and review['parent_scope'] is not None) else 1
        child_process._need(outcome['schema_version']==lifetime_version,'Scientific review and process lifetime versions differ')
        if lifetime_version==2:
            parent_archive.validate_parent_binding(review['parent_scope'],request['parent_manifest_sha256'])
            _same(declaration.get('parent_scope'),review['parent_scope'],'Declared parent lifetime')
            _same(outcome['parent_scope'],review['parent_scope'],'Executed parent lifetime')
        payload=child_process._inputs(attempt/'inputs',request['files']);child_process._declared_plan(payload)
        plan=_json(payload['plan.json']);model=payload['input.pdb']
        before=proofs['parent-before.json'];after=proofs['parent-after.json'];_same(before,after,'Recorded parent derivations')
        unsigned={k:v for k,v in before.items() if k not in {'record_sha256','derivation_id'}}
        child_process._need(before['kind']==child_inputs.KIND and type(before['schema_version']) is int and before['schema_version']==lifetime_version
            and before['derivation_verified'] is True and before['ordinary_checkpoint_verified'] is True
            and before['request_id']==request['request_id'] and before['parent_manifest_sha256']==request['parent_manifest_sha256']
            and before['derivation_id']==digest(unsigned)==review['parent_derivation_before']==review['parent_derivation_after'],
            'Recorded parent derivation differs')
        if lifetime_version==2:
            parent_archive.validate_parent_read(before['parent_transport'],request['parent_manifest_sha256'],completed=True)
        _same(before['run'],dict(anchor='parent',relative_path=declaration['run_relative']),'Recorded run selection')
        _same(before['endpoint'],dict(anchor='run',relative_path=declaration['endpoint_relative']),'Recorded endpoint selection')
        _same(before['input_model_sha256'],sha256(model).hexdigest(),'Recorded parent-derived model')
        _same(before['plan_sha256'],sha256(payload['plan.json']).hexdigest(),'Recorded parent-derived plan')
        _check_scattering_record(proofs['fresh-inputs.json'],plan)
        free_r=proofs['free-r.json']
        child_process._need(free_r['usable'] is True,'Recorded original Free-R audit is not usable')
        if version==3:
            from . import preflight_process
            child_process._need(declaration.get('owned_preflight') is True,'Owned input inspection declaration changed')
            link=proofs['owned-preflight.json']
            _same(link.get('directory'),dict(anchor='session',relative_path='preflight'),'Owned input inspection directory')
            inspected=preflight_process.inspect_preflight(root/'preflight',inspection_id=link['inspection_id'])
            _same(inspected['request_id'],review['request_id'],'Owned input inspection request')
            _same(inspected['fresh_inputs'],{k:v for k,v in proofs['fresh-inputs.json'].items() if k!='record_sha256'},'Owned input inspection values')
            # Session proofs have their own durable record digest; compare the
            # scientific payload, not that outer envelope.
            _same(inspected['free_r'],{k:v for k,v in free_r.items() if k!='record_sha256'},'Owned Free-R inspection')
        _same(before['free_r_label'],plan['metadata']['free_r_label'],'Recorded Free-R label')
        _same(before['free_r_test_value'],plan['policy']['free_r_test_value'],'Recorded Free-R test value')
        result=_audit_job(attempt/'native/fdp/job',plan,model)
        _same(result,review['result'],'Saved scientific result')
        _same(_saved_proofs(root,review),proofs,'Session proof during read')
        _same(child_outputs.inspect_child_outputs(attempt,request_id=review['request_id'],output_id=review['output_evidence_id']),seal,'Child output during read')
        _same(_session_record(root,'review.json'),review,'Session review during read')
        lifetime=dict(recorded_parent_scope=review['parent_scope'],parent_snapshot_cleanup_verified=False) if lifetime_version==2 else {}
        if version==3:lifetime['preflight_stopped_verified']=True
        return dict(kind='metal-fdp-audited-child-inspection',schema_version=version,review_id=review_id,
            request_id=review['request_id'],output_evidence_id=review['output_evidence_id'],result=result,
            parent_context={k:before[k] for k in ('run','endpoint','parent','source_kind','root_checkpoint_id','root_context_id','metal_b_policy')},
            recorded_free_r=dict(label=before['free_r_label'],test_value=before['free_r_test_value'],status=free_r['status'],
                usable=free_r['usable'],details=free_r['details'],warnings=free_r['warnings']),
            verification_scope='SAVED_SESSION_EVIDENCE_AND_FROZEN_STATE',fresh_parent_verification=False,
            fresh_free_r_audit=False,fresh_scattering=False,new_native_calls=0,
            scientific_acceptance='NOT_ASSESSED',reuse_authorized=False,retirement_authorized=False,**lifetime)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,CampaignError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot inspect audited child: '+str(exc)) from exc


FAILED_STOP_STAGES=frozenset({'OWNED_NATIVE_CHILD','SCIENTIFIC_AUDIT','REVIEW_PUBLICATION'})


def _failed_session_request(root,declaration):
    """Bind any failed-session closure to its original request and reservation."""
    child_process._need(not (root/'review.json').exists() and not (root/'review.json').is_symlink(),
                        'A published or ambiguous review cannot settle as a failed session')
    request=child_process._request(declaration['request'],declaration['request']['request_id'])
    child_process._need(declaration.get('owned_preflight') is True,'Failed-session release requires owned preflight')
    parent_archive.validate_parent_binding(declaration.get('parent_scope'),request['parent_manifest_sha256'])
    binding=declaration.get('storage_reservation')
    child_process._need(isinstance(binding,dict) and set(binding)=={'budget_id','reservation_id'},
                        'Failed session has no exact reservation binding')
    for name,value in binding.items():checksum(value,name)
    return request


def _failed_preflight_stop_evidence(root,declaration):
    from . import preflight_process
    request=_failed_session_request(root,declaration)
    child_process._need(not (root/'attempt').exists() and not (root/'attempt').is_symlink(),
                        'Input-inspection failure cannot contain a native child attempt')
    proof=preflight_process.inspect_stopped_preflight(root/'preflight',request_id=request['request_id'])
    return dict(**proof,native_not_started_verified=True)


def _failed_stop_evidence(root,declaration):
    """Read sealed process owners only; a scientific review is not required."""
    from . import preflight_process
    request=_failed_session_request(root,declaration)
    proof=_session_record(root,'owned-preflight.json')
    _same(proof.get('directory'),dict(anchor='session',relative_path='preflight'),'Failed session preflight location')
    preflight=preflight_process.inspect_preflight(root/'preflight',inspection_id=proof['inspection_id'])
    child_process._need(preflight['request_id']==request['request_id'],'Failed session preflight request changed')
    attempt=child_process._root(root/'attempt')
    # Require saved seals before the shared reader; never query historical PIDs
    # as a substitute for missing process completion evidence.
    _session_record(attempt/'ownership','finished.json')
    _session_record(attempt/'ownership/phases/native-fdp','finished.json')
    outcome=_session_record(attempt,'outcome.json')
    report=child_process.inspect_child(attempt,request_id=request['request_id'])
    child_process._need(report['status'] in {'COMPLETED','FAILED','TIMED_OUT','INTERRUPTED'}
        and report['stopped_verified'] is True and outcome.get('stopped_verified') is True
        and report['outcome']==outcome and outcome.get('schema_version')==2,
        'Failed session requires a verified stopped native outcome')
    _same(outcome['parent_scope'],declaration['parent_scope'],'Failed session native parent lifetime')
    return dict(preflight_inspection_id=proof['inspection_id'],native_outcome_sha256=outcome['record_sha256'],
                native_status=report['status'],preflight_stopped_verified=True,native_stopped_verified=True)


def inspect_failed_audited_child(session_directory,*,failure_id):
    """Verify a pinned new failure and stopped owners; never retry or accept science.

    New sealed preflight failures prove no main child began; older unbound
    failures remain unsupported.
    Missing stop seals refuse before the shared process reader can inspect PIDs.
    """
    checksum(failure_id,'independent failed session identity');root=child_process._root(session_directory)
    try:
        failure=_session_record(root,'failure.json')
        fields={'kind','schema_version','request_id','stage','error','message','scientific_acceptance',
                'retirement_authorized','session_declaration_sha256','process_stop_evidence','record_sha256'}
        child_process._need(set(failure)==fields and failure['record_sha256']==failure_id
            and failure['kind']=='metal-fdp-audited-child-failure' and type(failure['schema_version']) is int
            and ((failure['schema_version']==2 and failure['stage'] in FAILED_STOP_STAGES)
                 or (failure['schema_version']==3 and failure['stage']=='FRESH_INPUT_INSPECTION'))
            and isinstance(failure['error'],str) and isinstance(failure['message'],str)
            and failure['scientific_acceptance']=='NOT_ASSESSED' and failure['retirement_authorized'] is False
            and isinstance(failure['process_stop_evidence'],dict),'Unsupported or incomplete failed-session closure')
        declaration=_session_record(root,'request.json')
        _same(declaration['record_sha256'],failure['session_declaration_sha256'],'Failed session declaration')
        _same(declaration['request']['request_id'],failure['request_id'],'Failed session request')
        partial=failure['schema_version']==3
        stop=(_failed_preflight_stop_evidence if partial else _failed_stop_evidence)(root,declaration)
        _same(stop,failure['process_stop_evidence'],'Failed session stopped evidence')
        return dict(kind='metal-fdp-failed-child-read',schema_version=2 if partial else 1,failure_id=failure_id,
            request_id=failure['request_id'],stage=failure['stage'],recorded_parent_scope=declaration['parent_scope'],
            storage_reservation=declaration['storage_reservation'],postflight_review_complete=False,
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False,
            **{k:v for k,v in stop.items() if k!='request_id'})
    except (OSError,ValueError,KeyError,TypeError,CampaignError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot inspect failed session: '+str(exc)) from exc
