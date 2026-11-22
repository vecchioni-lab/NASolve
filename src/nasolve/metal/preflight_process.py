"""Owned native input inspections using the existing process and science owners.

An explicit session can record all three preflight processes without changing
scientific scripts/parsers or existing caller defaults. No storage settlement,
checkpoint acceptance, retry scheduler or second process implementation lives here.
"""
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import time

from .. import campaign_records as records
from ..cif_generation_process import _valid_attempt_identity
from ..cif_repair_process import _ProcessScope,_OwnedProcesses,_inspect_owned_processes
from ..refine_doctor import _AUDIT_SCRIPT
from . import child_process as child
from .recipe import checksum,RecipeError

POLICY='metal-fdp-input-process-v1'
KIND='metal-fdp-owned-input-inspection'
PHASES={'native-observations','native-scattering','native-free-r'}
SCOPE=_ProcessScope(POLICY,'preflight_directory','inputs','preflight.json',
    'inputs','input_files','preflight_sha256',r'native-(observations|scattering|free-r)',
    'OWNED_INPUT_INSPECTION_ONLY; NO_SCIENTIFIC_ACCEPTANCE_OR_STORAGE_RELEASE')
MAX_RECORD_BYTES=1024*1024
MAX_CAPTURE_BYTES=4*1024*1024


class PreflightProcesses(_OwnedProcesses):
    _scope=SCOPE


def _read(path,limit):
    child._need(path.is_file() and not path.is_symlink() and path.stat().st_size<=limit,'Missing or oversized input-inspection evidence')
    with path.open('rb') as f:raw=f.read(limit+1)
    child._need(len(raw)<=limit,'Input-inspection evidence exceeds byte bound')
    return raw


def _files(root):
    # Fixed phases; preserve exact native logs and any audit script/log generated
    # by the existing scientific API. The shared owner validates process records.
    refs={};total=0
    for phase in sorted(PHASES):
        work=root/'native'/phase[7:]/'job'
        if not work.exists():continue
        for path in work.iterdir():
            raw=_read(path,MAX_CAPTURE_BYTES);total+=len(raw)
            child._need(total<=3*MAX_CAPTURE_BYTES,'Input-inspection capture exceeds bound')
            name=path.relative_to(root).as_posix();refs[name]=dict(anchor='preflight',relative_path=name,size=len(raw),sha256=sha256(raw).hexdigest())
    return refs


def run_preflight(prepared,request,*,request_id,directory,native,timeout_seconds,fresh_scattering,audit_flags,_attempt_identity=None):
    """Run the existing three inspections under one bounded shared-process scope."""
    child._need(_attempt_identity is None or _valid_attempt_identity(_attempt_identity),'Invalid parent attempt identity')
    request=child._request(request,request_id);payload=child._inputs(prepared,request['files'])
    root=Path(directory).absolute();child._need(not root.exists() and root.parent.is_dir(),'Require a fresh input-inspection directory')
    child._need(native.version in {child.NATIVE_VERSION,child.NATIVE_VERSION.rsplit('-',1)[0]},'Unsupported input-inspection native version')
    executable={phase:Path(native.executables['phenix.mtz.dump' if phase=='native-observations' else 'phenix.python']).resolve() for phase in PHASES}
    hashes={phase:sha256(path.read_bytes()).hexdigest() for phase,path in executable.items()}
    root.mkdir();inputs=root/'inputs';inputs.mkdir()
    for name,raw in payload.items():(inputs/name).write_bytes(raw)
    (inputs/'request.json').write_text(json.dumps(request,sort_keys=True)+'\n')
    (inputs/'audit_free_r.py').write_text(_AUDIT_SCRIPT.lstrip())
    records.write_record(inputs/'dispatchers.json',dict(native_version=native.version,
        executable_hashes=hashes,paths_provenance_only={k:str(v) for k,v in executable.items()}))
    process=PreflightProcesses(root,attempt_identity=_attempt_identity);deadline=time.monotonic()+timeout_seconds;returned=False
    def runner(phase):
        work=root/'native'/phase[7:]/'job';work.mkdir(parents=True)
        log=work/'native.log'
        owned=process.runner(phase)
        def invoke(command,**kwargs):
            child._need(Path(command[0]).resolve()==executable[phase],'Input-inspection executable changed')
            child._need(sha256(executable[phase].read_bytes()).hexdigest()==hashes[phase],'Input-inspection executable bytes changed')
            script=work/'audit_free_r.py' if phase=='native-free-r' else None
            if script is not None:
                child._need(len(command)>1 and Path(command[1]).resolve()==script.resolve()
                    and _read(script,MAX_RECORD_BYTES)==_read(inputs/'audit_free_r.py',MAX_RECORD_BYTES),
                    'Free-R script differs from the frozen scientific helper')
            timeout=min(kwargs['timeout'],deadline-time.monotonic())
            if timeout<=0:raise subprocess.TimeoutExpired(command,timeout_seconds)
            code=owned([str(x) for x in command],cwd=work,log_path=log,environment=kwargs.get('env'),timeout_seconds=timeout)
            child._need(sha256(executable[phase].read_bytes()).hexdigest()==hashes[phase],'Input-inspection executable changed during execution')
            if script is not None:
                child._need(_read(script,MAX_RECORD_BYTES)==_read(inputs/'audit_free_r.py',MAX_RECORD_BYTES),
                            'Free-R script changed during input inspection')
            raw=_read(log,MAX_CAPTURE_BYTES).decode('utf-8',errors='replace')
            return subprocess.CompletedProcess(command,code,stdout=raw,stderr=raw)
        return invoke
    try:
        plan=json.loads(payload['plan.json'])
        fresh=fresh_scattering(inputs,plan,native,command_runners={
            'observations':runner('native-observations'),'scattering':runner('native-scattering')})
        free_runner=runner('native-free-r');work=root/'native/free-r/job'
        audit=audit_flags(inputs/'observations.mtz',plan['metadata']['free_r_label'],plan['policy']['free_r_test_value'],
            native.executables['phenix.python'],work,environment=native.environment,command_runner=free_runner)
        child._need(audit.valid,'Original Free-R audit failed in owned preflight')
        free_r=dict(status=audit.status,usable=audit.valid,details=audit.details,warnings=list(audit.warnings))
        child._inputs(inputs,request['files']);child._inputs(prepared,request['files'])
        returned=True
    finally:
        stopped=process.finish('RETURNED' if returned else 'RAISED')
        if not stopped:raise RecipeError('Input-inspection process stop uncertain; retain the attempt')
    state=_inspect_owned_processes(root,SCOPE)
    child._need(set(state['phases'])==PHASES and all(v['finished']['status']=='COMPLETED' and v['finished']['returncode']==0 for v in state['phases'].values()),
                'Input inspections did not complete all owned phases')
    return records.write_record(root/'inspection.json',dict(kind=KIND,schema_version=1,policy_id=POLICY,request_id=request_id,
        ownership_sha256=process.header['record_sha256'],finished_sha256=state['finished']['record_sha256'],
        fresh_inputs=fresh,free_r=free_r,files=_files(root),stopped_verified=True,
        scientific_acceptance='NOT_ASSESSED',retirement_authorized=False))


def inspect_preflight(directory,*,inspection_id):
    """Verify recorded input checks and stopped processes; never launch or release."""
    checksum(inspection_id,'independent input-inspection identity');root=child._root(directory)
    try:
        _read(root/'inspection.json',MAX_RECORD_BYTES);value=records.read_record(root/'inspection.json')
        child._need(set(value)=={'kind','schema_version','policy_id','request_id','ownership_sha256','finished_sha256',
            'fresh_inputs','free_r','files','stopped_verified','scientific_acceptance','retirement_authorized','record_sha256'}
            and value['record_sha256']==inspection_id and value['kind']==KIND
            and type(value['schema_version']) is int and value['schema_version']==1 and value['policy_id']==POLICY
            and value['stopped_verified'] is True and value['scientific_acceptance']=='NOT_ASSESSED'
            and value['retirement_authorized'] is False,'Unsupported input-inspection record')
        request=child._request(json.loads(_read(root/'inputs/request.json',child.MAX_REQUEST_BYTES)),value['request_id'])
        child._inputs(root/'inputs',request['files'])
        # Cold inspection requires complete saved stop evidence. Do not fall
        # back to probing historical process identities when a seal is missing.
        _read(root/'ownership/finished.json',MAX_RECORD_BYTES)
        for phase in PHASES:_read(root/'ownership/phases'/phase/'finished.json',MAX_RECORD_BYTES)
        state=_inspect_owned_processes(root,SCOPE)
        child._need(state['state']=='STOPPED' and state['header']['record_sha256']==value['ownership_sha256']
            and state['finished']['record_sha256']==value['finished_sha256'] and state['finished']['outcome']=='RETURNED'
            and set(state['phases'])==PHASES and all(v['finished']['status']=='COMPLETED' and v['finished']['returncode']==0 for v in state['phases'].values()),
            'Input-inspection processes are not completely and verifiably stopped')
        child._need(value['files']==_files(root),'Input-inspection capture changed')
        return dict(kind='metal-fdp-owned-input-inspection-read',schema_version=1,inspection_id=inspection_id,
            request_id=value['request_id'],stopped_verified=True,phases=sorted(state['phases']),
            fresh_inputs=value['fresh_inputs'],free_r=value['free_r'],new_native_calls=0,
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot inspect owned input checks: '+str(exc)) from exc


def inspect_stopped_preflight(directory,*,request_id):
    """Read a sealed partial inspection; no scientific pass, PID query or retry.

    A raised input check can have zero, some or all native phases. Only the
    ordinary owner's saved outer seal and every recorded phase seal establish
    closure. Missing/uncertain completion stays unsupported.
    """
    checksum(request_id,'input-inspection request');root=child._root(directory)
    try:
        request=child._request(json.loads(_read(root/'inputs/request.json',child.MAX_REQUEST_BYTES)),request_id)
        child._inputs(root/'inputs',request['files'])
        _read(root/'ownership/finished.json',MAX_RECORD_BYTES)
        seal=records.read_record(root/'ownership/finished.json')
        child._need(isinstance(seal,dict) and isinstance(seal.get('phases'),dict)
            and set(seal['phases'])<=PHASES,'Unsupported partial input-inspection seal')
        phases=root/'ownership/phases'
        names={p.name for p in phases.iterdir()} if phases.exists() else set()
        child._need(names==set(seal['phases']),'Partial input-inspection phases changed')
        for phase in names:_read(phases/phase/'finished.json',MAX_RECORD_BYTES)
        state=_inspect_owned_processes(root,SCOPE)
        child._need(state['state']=='STOPPED' and state['finished']==seal
            and set(state['phases'])==names,'Input inspection is not verifiably stopped')
        return dict(preflight_ownership_sha256=state['header']['record_sha256'],
            preflight_finished_sha256=seal['record_sha256'],request_id=request_id,
            phases={name:dict(finished_sha256=row['finished']['record_sha256'],status=row['finished']['status'])
                    for name,row in state['phases'].items()},files=_files(root),
            preflight_stopped_verified=True,input_inspection_complete=False)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot inspect stopped partial input checks: '+str(exc)) from exc
