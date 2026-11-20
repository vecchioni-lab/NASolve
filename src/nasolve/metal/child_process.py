"""Fresh frozen-child process ownership, separate from scientific trial acceptance.

Prepared inputs and a protected-parent archive are explicit caller mounts. Saved
commands are provenance only. This seam never prunes or accepts a scientific fit.
"""
from hashlib import sha256
from pathlib import Path
import math
import json
import subprocess

from .. import campaign_records as records
from ..cif_repair_process import _ProcessScope, _OwnedProcesses, _inspect_owned_processes
from . import parent_archive
from .compact import read_projection
from .materialize import _json
from .fdp import NATIVE_VERSION
from .recipe import RecipeError, checksum, digest

KIND = 'metal-fdp-child-process-request'
POLICY = 'metal-fdp-child-process-v1'
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_REQUEST_BYTES = 1024 * 1024
_SCOPE = _ProcessScope(POLICY, 'child_directory', 'inputs', 'child.json',
    'inputs', 'input_files', 'child_sha256', r'native-fdp',
    'FRESH_FROZEN_CHILD_PROCESS_ONLY; NO_SCIENTIFIC_ACCEPTANCE_OR_RETIREMENT')


class ChildProcesses(_OwnedProcesses):
    _scope = _SCOPE


def _need(value, message):
    if not value:
        raise RecipeError(message)


def _root(path):
    path = Path(path).expanduser().absolute()
    _need(path.is_dir() and not any(p.is_symlink() for p in (path, *path.parents)),
          'Require an existing directory without symlink ancestors')
    return path


def _file(root, name):
    _need(isinstance(name, str) and name and Path(name).name == name
          and name not in {'.', '..'} and chr(92) not in name, 'Require simple declared input names')
    path = root/name
    _need(path.is_file() and not path.is_symlink(), 'Missing or nonregular prepared input: '+name)
    return path


def _inputs(root, files):
    _need(isinstance(files, dict) and 3 <= len(files) <= 128,
          'Require a bounded explicit prepared-input inventory')
    _need({'input.pdb','native-plan.json','plan.json'} <= files.keys(), 'Incomplete prepared inputs')
    total = 0; payload = {}
    for name, ref in files.items():
        _need(isinstance(ref, dict) and set(ref) == {'sha256','size'}, 'Invalid prepared input reference')
        checksum(ref['sha256'], 'prepared input checksum')
        _need(type(ref['size']) is int and ref['size'] >= 0, 'Invalid prepared input size')
        total += ref['size']; _need(total <= MAX_INPUT_BYTES, 'Prepared inputs exceed byte budget')
        path = _file(root, name)
        _need(path.stat().st_size == ref['size'], 'Prepared input size changed')
        with path.open('rb') as handle: raw = handle.read(ref['size']+1)
        _need(len(raw) == ref['size'] and sha256(raw).hexdigest() == ref['sha256'], 'Prepared input changed')
        payload[name] = raw
    return payload


def _request(value, request_id):
    checksum(request_id, 'independent child request identity')
    try:
        body = dict(value); actual = body.pop('request_id')
        _need(set(body) == {'kind','schema_version','parent_manifest_sha256','files','worker_sha256',
                           'native_version','scientific_validation','retirement_authorized'}, 'Unsupported child request fields')
        _need(actual == request_id == digest(body) and body['kind'] == KIND
              and type(body['schema_version']) is int and body['schema_version'] == 1
              and body['native_version'] == NATIVE_VERSION
              and body['scientific_validation'] is False and body['retirement_authorized'] is False,
              'Changed or unsupported child request')
        checksum(body['parent_manifest_sha256'], 'protected parent identity')
        checksum(body['worker_sha256'], 'maintained worker identity')
        return value
    except (KeyError, TypeError, ValueError) as exc:
        raise RecipeError('Invalid child request: '+str(exc)) from exc


def _declared_plan(payload):
    plan = _json(payload['plan.json']); native_plan = _json(payload['native-plan.json'])
    _need(isinstance(plan,dict) and isinstance(native_plan,dict)
          and native_plan.get('plan')==plan and isinstance(plan.get('policy'),dict)
          and plan['policy'].get('strategy')==['group_anomalous']
          and isinstance(native_plan.get('args'),list) and native_plan['args']
          and all(isinstance(n,str) and n in payload for n in native_plan['args'])
          and len(native_plan['args'])==len(set(native_plan['args'])),
          'Prepared bytes do not declare a matched frozen-only request')


def make_request(prepared_directory, *, parent_manifest_sha256):
    """Pin an explicitly prepared frozen request; this does not admit its science."""
    checksum(parent_manifest_sha256, 'protected parent identity')
    root = _root(prepared_directory)
    native = read_projection(_file(root,'native-plan.json'),max_projection_bytes=MAX_REQUEST_BYTES)
    plan = read_projection(_file(root,'plan.json'),max_projection_bytes=MAX_REQUEST_BYTES)
    _need(isinstance(native,dict) and isinstance(plan,dict) and native.get('plan') == plan
          and isinstance(plan.get('policy'),dict) and plan['policy'].get('strategy') == ['group_anomalous'],
          'Require a matched declared frozen anomalous-only plan')
    args = native.get('args')
    _need(isinstance(args,list) and args and all(isinstance(n,str) for n in args)
          and len(args) == len(set(args)), 'Require explicit unique native input names')
    names = set(args) | {'input.pdb','plan.json','native-plan.json'}
    _need(not names.intersection({'request.json','execution.json','_fdp_native.py'}), 'Reserved child input name')
    files = {}
    for name in sorted(names):
        path = _file(root,name); size = path.stat().st_size
        _need(size <= MAX_INPUT_BYTES and sum(x['size'] for x in files.values())+size <= MAX_INPUT_BYTES,
              'Prepared inputs exceed byte budget')
        raw = path.read_bytes(); _need(len(raw)==size,'Prepared input changed during inventory')
        files[name] = dict(sha256=sha256(raw).hexdigest(),size=size)
    _declared_plan(_inputs(root,files))
    body = dict(kind=KIND,schema_version=1,parent_manifest_sha256=parent_manifest_sha256,
        files=files,worker_sha256=sha256(Path(__file__).with_name('_fdp_native.py').read_bytes()).hexdigest(),
        native_version=NATIVE_VERSION,scientific_validation=False,retirement_authorized=False)
    return dict(body,request_id=digest(body))


def inspect_child(directory, *, request_id):
    """Read durable outcome/current process evidence; never signal or rerun a PID."""
    root = _root(directory)
    request = _request(read_projection(root/'inputs/request.json',max_projection_bytes=MAX_REQUEST_BYTES),request_id)
    error = None
    try:
        _inputs(root/'inputs',request['files'])
        _need(sha256((root/'inputs/_fdp_native.py').read_bytes()).hexdigest()==request['worker_sha256'],'Worker snapshot changed')
        process = _inspect_owned_processes(root,_SCOPE)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        process = dict(state='UNKNOWN',phases={}); error = str(exc)
    outcome = records.read_record(root/'outcome.json') if (root/'outcome.json').exists() else None
    if outcome is not None:
        _need(outcome.get('request_id')==request_id and outcome.get('parent_manifest_sha256')==request['parent_manifest_sha256']
              and outcome.get('policy_id')==POLICY,'Outcome belongs to a different child request')
    if outcome is not None:
        _need(outcome.get('kind')=='metal-fdp-child-process-outcome'
              and type(outcome.get('schema_version')) is int and outcome['schema_version']==1
              and outcome.get('scientific_acceptance')=='NOT_ASSESSED'
              and outcome.get('retirement_authorized') is False,'Unsupported process outcome')
        header = process.get('header')
        if header is not None:
            _need(outcome.get('ownership_sha256')==header['record_sha256'],'Outcome ownership changed')
            execution = records.read_record(root/'inputs/execution.json')
            _need(execution.get('request_id')==request_id
                  and execution.get('native_executable_sha256')==outcome.get('native_executable_sha256')
                  and execution.get('retry_of')==outcome.get('retry_of'),'Outcome execution binding changed')
        phase = process.get('phases',{}).get('native-fdp',{}).get('finished')
        if outcome['status'] in {'COMPLETED','FAILED','TIMED_OUT','INTERRUPTED'}:
            _need(phase is not None and phase['status']==outcome['status']
                  and phase['returncode']==outcome.get('returncode'),'Outcome contradicts native phase')
    stopped = process['state']=='STOPPED' and error is None
    ready = bool(stopped and outcome and outcome.get('stopped_verified') is True
                 and outcome.get('parent_transport_verified') is True
                 and outcome.get('status') in {'FAILED','TIMED_OUT','INTERRUPTED'})
    return dict(status=outcome['status'] if outcome and error is None else 'REVIEW_REQUIRED',
        request_id=request_id,parent_manifest_sha256=request['parent_manifest_sha256'],
        process=process,outcome=outcome,stopped_verified=stopped,
        fresh_retry_eligible=ready,error=error,scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)


def run_child(prepared_directory, parent_directory, request, *, request_id,
              attempt_directory, native, timeout_seconds=240, retry_from=None,
              max_parent_disk_bytes=parent_archive.DEFAULT_DISK_BYTES):
    """Invoke the maintained worker once in a fresh owned attempt.

    Parent transport is verified, not scientific admission. A normal pipeline
    must still qualify the parent, replay input derivation and audit the result.
    Retry never overwrites a prior attempt or executes its stored argv.
    """
    request = _request(request,request_id)
    _need(type(timeout_seconds) in (int,float) and math.isfinite(timeout_seconds)
          and 0 < timeout_seconds <= 600,'Require a bounded positive child deadline')
    prepared = _root(prepared_directory); parent = _root(parent_directory)
    payload = _inputs(prepared,request['files'])
    _declared_plan(payload)
    worker = Path(__file__).with_name('_fdp_native.py').read_bytes()
    _need(sha256(worker).hexdigest()==request['worker_sha256'],'Request requires a different maintained worker')
    _need(native.version==NATIVE_VERSION,'Unsupported native version')
    executable = Path(native.executables['phenix.python']).resolve()
    _need(executable.is_file(),'Native executable missing')
    executable_sha = sha256(executable.read_bytes()).hexdigest()
    attempt = Path(attempt_directory).expanduser().absolute()
    _need(not attempt.exists() and not attempt.is_symlink() and attempt.parent.is_dir()
          and not any(p.is_symlink() for p in attempt.parents)
          and not attempt.resolve().is_relative_to(prepared)
          and not attempt.resolve().is_relative_to(parent),'Require a fresh attempt outside prepared inputs/parent archive')
    previous = None
    if retry_from is not None:
        prior = inspect_child(retry_from,request_id=request_id)
        _need(prior['fresh_retry_eligible'],'Prior child is not qualified for a fresh retry')
        _need(prior['outcome'].get('native_executable_sha256')==executable_sha,'Retry native executable changed')
        previous = prior['outcome']['record_sha256']
    owner = None; transport = None; status = 'REVIEW_REQUIRED'; code = None; error = None; sealed = False
    try:
        with parent_archive.materialized_parent_inputs(parent,request['parent_manifest_sha256'],
                max_disk_bytes=max_parent_disk_bytes) as (_,transport):
            attempt.mkdir(); inputs = attempt/'inputs'; inputs.mkdir()
            for name,raw in payload.items():(inputs/name).write_bytes(raw)
            (inputs/'_fdp_native.py').write_bytes(worker)
            (inputs/'request.json').write_text(json.dumps(request,sort_keys=True)+'\n')
            execution = dict(native_version=native.version,native_executable_sha256=executable_sha,
                request_id=request_id,parent_manifest_sha256=request['parent_manifest_sha256'],retry_of=previous)
            records.write_record(inputs/'execution.json',execution)
            owner = ChildProcesses(attempt)
            work = attempt/'native/fdp/job';work.mkdir(parents=True)
            for name,raw in payload.items():(work/name).write_bytes(raw)
            try:
                code = owner.runner('native-fdp')([str(executable),'-B',str(inputs/'_fdp_native.py'),'native-plan.json'],
                    cwd=work,log_path=work/'native.log',environment=native.environment,timeout_seconds=timeout_seconds)
                _need(all((work/n).read_bytes()==raw for n,raw in payload.items()),'Native worker changed a frozen input')
                _need(sha256(executable.read_bytes()).hexdigest()==executable_sha,'Native executable changed during execution')
                status = 'COMPLETED' if code==0 else 'FAILED'
            except BaseException as exc:
                code = getattr(exc,'returncode',None)
                error = dict(type=type(exc).__name__,message=str(exc))
                status = 'TIMED_OUT' if isinstance(exc,subprocess.TimeoutExpired) else 'INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'REVIEW_REQUIRED'
            finally:
                sealed = owner.finish('RETURNED' if error is None else 'RAISED')
                if not sealed: status = 'STOP_UNCERTAIN'
    except BaseException as exc:
        if owner is None: raise
        status = 'STOP_UNCERTAIN' if not sealed else 'REVIEW_REQUIRED';error = dict(type=type(exc).__name__,message=str(exc))
    parent_verified = bool(transport and transport['inputs_unchanged'] and transport['snapshot_removed'])
    if not parent_verified:status='REVIEW_REQUIRED'
    records.write_record(attempt/'outcome.json',dict(kind='metal-fdp-child-process-outcome',schema_version=1,
        policy_id=POLICY,request_id=request_id,parent_manifest_sha256=request['parent_manifest_sha256'],
        parent_transport_verified=parent_verified,native_executable_sha256=executable_sha,
        ownership_sha256=owner.header['record_sha256'],status=status,returncode=code,
        stopped_verified=sealed,error=error,retry_of=previous,
        scientific_acceptance='NOT_ASSESSED',retirement_authorized=False))
    return inspect_child(attempt,request_id=request_id)
