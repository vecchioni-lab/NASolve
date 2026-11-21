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


def _fresh_scattering(prepared, plan, native):
    metadata=inspect_observations(prepared/'observations.mtz',
        executable=native.executables['phenix.mtz.dump'],environment=native.environment)
    _same(metadata,plan['metadata'],'Fresh observation metadata')
    symbols={a.element for a in parse_pdb((prepared/'input.pdb').read_bytes()).snapshot.atoms}
    references=reference_scattering(symbols,metadata['wavelength_A'],
        executable=native.executables['phenix.python'],version=native.version,environment=native.environment)
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
                      max_output_bytes=child_outputs.DEFAULT_MAX_BYTES):
    """Derive, freshly inspect, execute and audit one conditional frozen fit.

    FDP_REVIEW means the declared frozen calculation passed its audits; it does
    not accept geometry, metal identity/count, convergence or scientific fitness.
    Failed sessions remain distinct and retained. No implicit retry is performed.
    """
    request=child_process._request(request,request_id)
    child_process._need(request['schema_version']==2,'Audited child requires a helper-pinned request')
    child_process._need(type(timeout_seconds) in (int,float) and math.isfinite(timeout_seconds)
        and 0<timeout_seconds<=600,'Require a bounded positive child deadline')
    child_process._need(type(max_output_bytes) is int and 0<max_output_bytes<=child_outputs.MAX_BYTES,
        'Invalid output byte budget')
    prepared=child_process._root(prepared_directory);parent=child_process._root(parent_directory)
    payload=child_process._inputs(prepared,request['files']);child_process._declared_plan(payload)
    child_process._worker_payload(Path(child_process.__file__).parent,request['worker_files'])
    session=Path(session_directory).expanduser().absolute()
    child_process._need(not session.exists() and not session.is_symlink() and session.parent.is_dir()
        and not any(p.is_symlink() for p in session.parents)
        and not session.resolve().is_relative_to(prepared) and not session.resolve().is_relative_to(parent),
        'Require a new session outside prepared inputs and parent archive')
    options=dict(request_id=request_id,run_relative=run_relative,endpoint_relative=endpoint_relative,
        reader_control_policy=reader_control_policy,max_parent_disk_bytes=max_parent_disk_bytes)
    before=child_inputs.verify_child_inputs(prepared,parent,request,**options)
    plan=_json(payload['plan.json']);model=payload['input.pdb']
    session.mkdir()
    stage='FRESH_INPUT_INSPECTION'
    proofs={}
    def record(name,value):
        proofs[name]=records.write_record(session/name,value)
    try:
        record('request.json',dict(request=request,run_relative=run_relative,
            endpoint_relative=endpoint_relative,timeout_seconds=timeout_seconds,max_output_bytes=max_output_bytes))
        record('parent-before.json',before)
        fresh=_fresh_scattering(prepared,plan,native)
        record('fresh-inputs.json',fresh)
        audit=audit_free_r_flags(prepared/'observations.mtz',plan['metadata']['free_r_label'],
            plan['policy']['free_r_test_value'],native.executables['phenix.python'],session,
            environment=native.environment)
        record('free-r.json',dict(status=audit.status,usable=audit.valid,
            details=audit.details,warnings=list(audit.warnings)))
        if not audit.valid:raise RecipeError('Original Free-R audit failed; see retained free-r.json')
        child_process._inputs(prepared,request['files'])
        stage='OWNED_NATIVE_CHILD'
        process=child_process.run_child(prepared,parent,request,request_id=request_id,
            attempt_directory=session/'attempt',native=native,timeout_seconds=timeout_seconds,
            max_parent_disk_bytes=max_parent_disk_bytes)
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
        for name,recorded in proofs.items():
            _same(records.read_record(session/name),recorded,'Session proof '+name)
        proof_names=sorted(proofs)
        files={name:dict(anchor='session',relative_path=name,size=(session/name).stat().st_size,
            sha256=sha256((session/name).read_bytes()).hexdigest()) for name in proof_names}
        return records.write_record(session/'review.json',dict(kind=KIND,schema_version=1,status='FDP_REVIEW',
            request_id=request_id,parent_manifest_sha256=request['parent_manifest_sha256'],
            parent_derivation_before=before['derivation_id'],parent_derivation_after=after['derivation_id'],
            attempt=dict(anchor='session',relative_path='attempt'),output_evidence_id=output['record_sha256'],
            files=files,result=result,fresh_metadata=True,fresh_scattering=True,fresh_free_r_audit=True,
            serialized_model_unchanged=True,scientific_acceptance='NOT_ASSESSED',
            automatic_checkpoint_selection=False,reuse_authorized=False,retirement_authorized=False))
    except BaseException as exc:
        records.write_record(session/'failure.json',dict(kind='metal-fdp-audited-child-failure',schema_version=1,
            request_id=request_id,stage=stage,error=type(exc).__name__,message=str(exc),
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False))
        if isinstance(exc,(RecipeError,KeyboardInterrupt,SystemExit)):raise
        raise RecipeError('Audited child failed at '+stage+': '+str(exc)) from exc


def _session_record(root,name):
    path=child_process._file(root,name)
    child_process._need(path.stat().st_size<=child_outputs.MAX_RECORD_BYTES,'Session record exceeds byte budget')
    return records.read_record(path)


def _saved_proofs(root,review):
    names={'request.json','parent-before.json','parent-after.json','fresh-inputs.json','free-r.json'}
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
        child_process._need(set(review)==fields and review['kind']==KIND
            and type(review['schema_version']) is int and review['schema_version']==1
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
        payload=child_process._inputs(attempt/'inputs',request['files']);child_process._declared_plan(payload)
        plan=_json(payload['plan.json']);model=payload['input.pdb']
        before=proofs['parent-before.json'];after=proofs['parent-after.json'];_same(before,after,'Recorded parent derivations')
        unsigned={k:v for k,v in before.items() if k not in {'record_sha256','derivation_id'}}
        child_process._need(before['kind']==child_inputs.KIND and before['schema_version']==1
            and before['derivation_verified'] is True and before['ordinary_checkpoint_verified'] is True
            and before['request_id']==request['request_id'] and before['parent_manifest_sha256']==request['parent_manifest_sha256']
            and before['derivation_id']==digest(unsigned)==review['parent_derivation_before']==review['parent_derivation_after'],
            'Recorded parent derivation differs')
        _same(before['run'],dict(anchor='parent',relative_path=declaration['run_relative']),'Recorded run selection')
        _same(before['endpoint'],dict(anchor='run',relative_path=declaration['endpoint_relative']),'Recorded endpoint selection')
        _same(before['input_model_sha256'],sha256(model).hexdigest(),'Recorded parent-derived model')
        _same(before['plan_sha256'],sha256(payload['plan.json']).hexdigest(),'Recorded parent-derived plan')
        _check_scattering_record(proofs['fresh-inputs.json'],plan)
        free_r=proofs['free-r.json']
        child_process._need(free_r['usable'] is True,'Recorded original Free-R audit is not usable')
        _same(before['free_r_label'],plan['metadata']['free_r_label'],'Recorded Free-R label')
        _same(before['free_r_test_value'],plan['policy']['free_r_test_value'],'Recorded Free-R test value')
        result=_audit_job(attempt/'native/fdp/job',plan,model)
        _same(result,review['result'],'Saved scientific result')
        _same(_saved_proofs(root,review),proofs,'Session proof during read')
        _same(child_outputs.inspect_child_outputs(attempt,request_id=review['request_id'],output_id=review['output_evidence_id']),seal,'Child output during read')
        _same(_session_record(root,'review.json'),review,'Session review during read')
        return dict(kind='metal-fdp-audited-child-inspection',schema_version=1,review_id=review_id,
            request_id=review['request_id'],output_evidence_id=review['output_evidence_id'],result=result,
            parent_context={k:before[k] for k in ('run','endpoint','parent','source_kind','root_checkpoint_id','root_context_id','metal_b_policy')},
            recorded_free_r=dict(label=before['free_r_label'],test_value=before['free_r_test_value'],status=free_r['status'],
                usable=free_r['usable'],details=free_r['details'],warnings=free_r['warnings']),
            verification_scope='SAVED_SESSION_EVIDENCE_AND_FROZEN_STATE',fresh_parent_verification=False,
            fresh_free_r_audit=False,fresh_scattering=False,new_native_calls=0,
            scientific_acceptance='NOT_ASSESSED',reuse_authorized=False,retirement_authorized=False)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,CampaignError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot inspect audited child: '+str(exc)) from exc
