"""One opt-in audited frozen child; no checkpoint acceptance, search or pruning.

Compose the existing parent, reflection, process and scientific audit owners.
Each invocation retains a distinct session and one bounded child attempt.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import math

from .. import campaign_records as records
from ..refine_doctor import audit_free_r_flags
from . import child_inputs, child_process, child_outputs, parent_archive
from .context import parse_pdb
from .fdp import audit_result
from .materialize import _json
from .recipe import RecipeError, canonical
from .scattering import inspect_observations, reference_scattering

KIND = 'metal-fdp-audited-child-review'


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
    # Discovery's display label is provenance, not the independently read native
    # build tag. All actual table/element/energy/value fields must match exactly.
    normalize=lambda rows:[{k:v for k,v in row.items() if k!='phenix_version'} for row in rows]
    _same(normalize(references),normalize(plan['references']),'Fresh scattering references')
    return dict(observations=metadata,references=references,discovered_version=native.version)


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
        evidence=_json(gzip.decompress((job/'native-result.json.gz').read_bytes()))
        result=audit_result(plan,model,evidence)
        initial=parse_pdb(model);final=parse_pdb((job/'final.pdb').read_bytes())
        if initial.snapshot.atoms!=final.snapshot.atoms or canonical(initial.to_dict()['atomic_state'])!=canonical(final.to_dict()['atomic_state']):
            raise RecipeError('Serialized final PDB changed frozen atomic state')
        if 'anomalous_map' in evidence:
            from .anomalous_maps import verify_file
            verify_file(evidence['anomalous_map'],job)
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
