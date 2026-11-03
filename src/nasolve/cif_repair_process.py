"""Durable process evidence for one explicit prepared-repair execution.

Campaign cleanup owns live handles. Saved identities are observations only;
these records never authorize retry, replay commands or qualify chemistry.
"""
from hashlib import sha256
from pathlib import Path
import math
import re
import subprocess
import time
import uuid

from .campaign_process import current_process_identity, coordinator_alive, process_alive, run_owned_command
from .campaign_records import now, path_in, read_record, write_record
from .cif_component_runtime import _tree
from .cif_generation_process import _valid_identity, _valid_command, FINISHED

POLICY_ID = 'cif-prepared-repair-process-v1'
ANCHOR = 'repair_directory'


def _need(condition, message='Invalid prepared-repair ownership evidence'):
    if not condition:
        raise ValueError(message)


def _root(root):
    root = Path(root).absolute()
    _need(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)))
    return root


def _uuid(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value) is not None


def _phase(phase):
    return isinstance(phase, str) and (phase in {'original-gradient', 'repaired-gradient', 'attribution'}
        or re.fullmatch(r'native-(baseline|[0-9]{3,})', phase) is not None)


def _bundle(root):
    return {name: {'sha256': sha256(data).hexdigest(), 'size': len(data)}
            for name, data in _tree(root/'bundle').items()}


def _members(directory, allowed, *, directories=False):
    for p in directory.iterdir():
        _need(not p.is_symlink())
        if p.name in allowed:
            _need(p.is_dir() if directories else p.is_file())
        else:
            _need(not directories and p.name.startswith('.record-') and p.is_file())


def _paths(root, phase, cwd, log):
    _need(_phase(phase))
    _need(isinstance(cwd, dict) and set(cwd) == {'anchor','path'} and cwd['anchor'] == ANCHOR)
    _need(isinstance(log, dict) and set(log) == {'anchor','path'} and log['anchor'] == ANCHOR)
    work = path_in(root, cwd['path']); logfile = path_in(root, log['path'])
    _need(work.is_dir())
    if phase.startswith('native-'):
        _need(work.parent == root/'native'/phase[7:] and logfile == work/'native.log')
    else:
        _need(work == root/phase/'job' and logfile == work/('execution.log' if phase == 'attribution' else 'gradient.log'))
    return work, logfile


def _header(root):
    path = path_in(root, 'ownership/repair.json')
    value = read_record(path)
    _need(type(value.get('schema_version')) is int and value['schema_version'] == 1
          and value.get('policy_id') == POLICY_ID and _uuid(value.get('execution_id'))
          and _valid_identity(value.get('coordinator'))
          and value.get('bundle') == {'anchor': ANCHOR, 'path': 'bundle'}
          and value.get('bundle_files') == _bundle(root))
    return value


def _inspect_phase(root, phase, header):
    directory = path_in(root, 'ownership/phases/'+phase)
    _need(_phase(phase) and directory.is_dir())
    _members(directory, {'job.json','process.json','finished.json'})
    result = dict(state='UNKNOWN', activity=None, retry_authorized=False)
    if not (directory/'job.json').exists():
        _need(not any((directory/n).exists() for n in ('process.json','finished.json')))
        return result
    job = read_record(directory/'job.json')
    _need(job.get('repair_sha256') == header['record_sha256'] and job.get('phase') == phase
          and _uuid(job.get('invocation_id')) and _valid_command(job.get('argv_provenance'))
          and job.get('argv_role') == 'PROVENANCE_ONLY; NEVER_REPLAY'
          and job.get('coordinator') == header['coordinator']
          and type(job.get('timeout_seconds')) in (int,float)
          and math.isfinite(job['timeout_seconds']) and 0 < job['timeout_seconds'] <= 600)
    _paths(root, phase, job.get('cwd'), job.get('log'))
    result['job'] = job
    # Completion is published last: read it first to avoid a publication race.
    finished = read_record(directory/'finished.json') if (directory/'finished.json').exists() else None
    owner = read_record(directory/'process.json') if (directory/'process.json').exists() else None
    if owner is not None:
        _need(owner.get('job_sha256') == job['record_sha256'] and _valid_identity(owner.get('identity'), child=True))
        result['identity'] = owner['identity']
    if finished is not None:
        code = finished.get('returncode')
        _need(finished.get('job_sha256') == job['record_sha256']
              and finished.get('process_sha256') == (owner['record_sha256'] if owner else None)
              and finished.get('status') in FINISHED and finished.get('stopped_verified') is True
              and type(finished.get('elapsed_seconds')) in (int,float)
              and math.isfinite(finished['elapsed_seconds']) and finished['elapsed_seconds'] >= 0
              and (code is None or type(code) is int))
        if finished['status'] in {'COMPLETED','FAILED'}:
            _need(owner is not None and code is not None and (code == 0) == (finished['status'] == 'COMPLETED'))
        return dict(result, state='STOPPED', activity=False, finished=finished)
    if owner is not None:
        live = process_alive(owner['identity'])
        result.update(activity=live, state='LIVE' if live is True else 'STOPPED_UNFINISHED' if live is False else 'UNKNOWN')
    return result


def inspect_prepared_repair_processes(root):
    """Read local process evidence without locks, signalling, repair or retry."""
    root = _root(root)
    directory = path_in(root, 'ownership')
    result = dict(schema_version=1, policy_id=POLICY_ID, state='NOT_RECORDED', activity=None,
        retry_authorized=False, scope='PREPARED_EXECUTION_ONLY; NOT_ACQUISITION_OR_CHEMISTRY', phases={})
    if not directory.exists():
        return result
    _need(directory.is_dir())
    for p in directory.iterdir():
        _need(not p.is_symlink() and ((p.name == 'phases' and p.is_dir()) or
              (p.is_file() and (p.name in {'repair.json','finished.json'} or p.name.startswith('.record-')))))
    if not (directory/'repair.json').exists():
        _need(not (directory/'finished.json').exists())
        return dict(result, state='UNKNOWN')
    header = _header(root)
    # Observe the outer seal before its phase dependencies for concurrent readers.
    seal = read_record(directory/'finished.json') if (directory/'finished.json').exists() else None
    # Prove the caller gone before taking the worker snapshot. Otherwise a last
    # reservation can appear between enumeration and the caller's exit.
    caller = coordinator_alive(header['coordinator']) if seal is None else None
    phases = directory/'phases'
    states = {}
    if phases.exists():
        names = [p.name for p in phases.iterdir()]
        _need(all(_phase(n) for n in names))
        _members(phases, set(names), directories=True)
        states = {name:_inspect_phase(root,name,header) for name in sorted(names)}
    result.update(header=header, phases=states, state='UNKNOWN')
    if seal is not None:
        _need(seal.get('repair_sha256') == header['record_sha256']
              and seal.get('outcome') in {'RETURNED','RAISED'} and seal.get('stopped_verified') is True
              and all(v['state'] == 'STOPPED' for v in states.values())
              and seal.get('phases') == {n:v['finished']['record_sha256'] for n,v in states.items()})
        return dict(result, state='STOPPED', activity=False, finished=seal)
    result['coordinator_activity'] = caller
    if caller is True or any(v['activity'] is True for v in states.values()):
        result.update(state='LIVE',activity=True)
    elif caller is False and all(v['activity'] is False for v in states.values()):
        result.update(state='STOPPED_UNFINISHED',activity=False)
    return result


class PreparedRepairProcesses:
    """Own native invocations for one fresh prepared execution, never an attempt retry."""

    def __init__(self, root):
        self.root = _root(root)
        coordinator = current_process_identity()
        bundle = _bundle(self.root)
        directory = path_in(self.root, 'ownership')
        directory.mkdir(exist_ok=False)
        self.header = write_record(directory/'repair.json', dict(schema_version=1, policy_id=POLICY_ID,
            execution_id=str(uuid.uuid4()), coordinator=coordinator, created_utc=now(),
            bundle={'anchor':ANCHOR,'path':'bundle'}, bundle_files=bundle))

    def runner(self, phase):
        _need(_phase(phase))
        def run(command, *, cwd, log_path, environment, timeout_seconds):
            root = self.root
            _need(not path_in(root,'ownership/finished.json').exists(), 'Prepared execution is already sealed')
            _need(_header(root) == self.header, 'Prepared execution inputs changed')
            _need(_valid_command(command) and type(timeout_seconds) in (int,float)
                  and math.isfinite(timeout_seconds) and 0 < timeout_seconds <= 600)
            cwd = {'anchor':ANCHOR,'path':Path(cwd).absolute().relative_to(root).as_posix()}
            log = {'anchor':ANCHOR,'path':Path(log_path).absolute().relative_to(root).as_posix()}
            work, logfile = _paths(root,phase,cwd,log)
            _need(not logfile.exists(), 'Native log already exists')
            directory = path_in(root,'ownership/phases/'+phase)
            directory.mkdir(parents=True,exist_ok=False)
            started = time.monotonic()
            job = write_record(directory/'job.json', dict(repair_sha256=self.header['record_sha256'],
                phase=phase, invocation_id=str(uuid.uuid4()), coordinator=self.header['coordinator'],
                created_utc=now(), timeout_seconds=timeout_seconds, cwd=cwd, log=log,
                argv_provenance=command, argv_role='PROVENANCE_ONLY; NEVER_REPLAY'))
            def publish(identity):
                write_record(directory/'process.json',dict(job_sha256=job['record_sha256'],identity=identity))
            def finish(status, code, error=None):
                path = path_in(root,'ownership/phases/'+phase+'/process.json')
                identity = read_record(path) if path.exists() else None
                write_record(directory/'finished.json',dict(job_sha256=job['record_sha256'],
                    process_sha256=identity['record_sha256'] if identity else None, status=status,
                    returncode=code, stopped_verified=True, elapsed_seconds=time.monotonic()-started,
                    finished_utc=now(), error_type=error))
            try:
                remaining = timeout_seconds - (time.monotonic()-started)
                if remaining <= 0:
                    expired = subprocess.TimeoutExpired(command,timeout_seconds)
                    expired.stopped_verified = True  # reserved but never launched
                    expired.native_not_launched = True
                    raise expired
                code = run_owned_command(command,cwd=work,log_path=logfile,environment=environment,
                    timeout_seconds=remaining,on_process=publish)
            except BaseException as exc:
                if getattr(exc,'stopped_verified',False) is True:
                    status = 'TIMED_OUT' if isinstance(exc,subprocess.TimeoutExpired) else 'INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
                    finish(status,getattr(exc,'returncode',None),type(exc).__name__)
                raise
            finish('COMPLETED' if code == 0 else 'FAILED',code)
            return code
        return run

    def finish(self, outcome):
        _need(outcome in {'RETURNED','RAISED'})
        state = inspect_prepared_repair_processes(self.root)
        _need(state.get('header') == self.header and 'finished' not in state)
        if not all(v['state'] == 'STOPPED' for v in state['phases'].values()):
            return False
        write_record(self.root/'ownership/finished.json',dict(repair_sha256=self.header['record_sha256'],
            outcome=outcome, stopped_verified=True, finished_utc=now(),
            phases={n:v['finished']['record_sha256'] for n,v in state['phases'].items()}))
        return True
