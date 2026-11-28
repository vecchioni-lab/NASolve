"""Immutable process evidence for explicit source-generation invocations.

This is execution evidence, not chemistry qualification or a retry scheduler.
Missing/foreign live evidence never proves inactivity. Readers never signal a
saved PID, execute a saved command, create a lock, or repair a partial record.
"""

from __future__ import annotations

import math
from pathlib import Path
import re
import subprocess
import time
import uuid

from .campaign_process import current_process_identity, process_alive, run_owned_command
from .campaign_records import now, read_record, write_record

POLICY_ID = 'cif-source-generation-process-v1'
PHASES = {'capabilities': 'elbow_help.log', 'candidate': 'candidate_worker.log'}
FINISHED = {'COMPLETED', 'FAILED', 'TIMED_OUT', 'INTERRUPTED', 'ERROR'}


def _directory(work, phase):
    if phase not in PHASES:
        raise ValueError('Unknown source-generation process phase')
    work = Path(work).absolute()
    directory = work / 'execution' / phase
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('Generation process evidence cannot traverse a symlink')
    if not work.is_dir():
        raise ValueError('Generation working directory must already exist')
    if (work / 'execution').exists() and not (work / 'execution').is_dir():
        raise ValueError('Generation execution evidence is not a directory')
    return work, directory


def _valid_attempt_identity(identity):
    return (isinstance(identity, dict) and set(identity) == {'request_sha256', 'attempt_sha256', 'attempt_id'}
            and all(isinstance(identity[k], str) and re.fullmatch('[0-9a-f]{64}', identity[k]) is not None
                    for k in ('request_sha256', 'attempt_sha256'))
            and isinstance(identity['attempt_id'], str)
            and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', identity['attempt_id']) is not None)


def _valid_context(context):
    return (isinstance(context, dict)
            and isinstance(context.get('source_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', context['source_sha256']) is not None
            and isinstance(context.get('component'), str)
            and re.fullmatch('[A-Z0-9]{1,3}', context['component']) is not None
            and ('attempt_owner' not in context or _valid_attempt_identity(context['attempt_owner'])))


def _valid_identity(identity, *, child=False):
    return (isinstance(identity, dict)
            and type(identity.get('pid')) is int and identity['pid'] > 1
            and type(identity.get('pgid')) is int and identity['pgid'] > 0
            and (not child or identity['pid'] == identity['pgid'])
            and isinstance(identity.get('host'), str)
            and all(identity.get(key) is None or isinstance(identity[key], str)
                    for key in ('boot_id', 'start_marker'))
            and all(isinstance(identity.get(key), str) for key in ('started_utc', 'heartbeat_utc')))


def _valid_command(command):
    return (isinstance(command, list) and bool(command)
            and all(isinstance(s, str) and s and '\0' not in s for s in command))


def run_generation_command(command, work, *, phase, environment, timeout_seconds, context):
    """Reserve one never-reused phase and persist intent before starting a child.

    A hard kill in the spawn/publication gap deliberately leaves UNKNOWN. A
    terminal record is written only after the live owner proves its group gone.
    No environment variables are persisted. Absolute argv strings are historical
    provenance only; inspection uses relative records and never replays them.
    """
    work, directory = _directory(work, phase)
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 600):
        raise ValueError('Generation deadline must be finite and in (0, 600]')
    if not _valid_command(command):
        raise ValueError('Require an explicit generation command')
    if not _valid_context(context):
        raise ValueError('Require an exact source/component process context')
    log = work / PHASES[phase]
    if log.exists() or log.is_symlink():
        raise FileExistsError(log)
    started = time.monotonic()
    coordinator = current_process_identity()  # Refuse unsupported platforms before reservation.
    directory.mkdir(parents=True, exist_ok=False)
    job = write_record(directory / 'job.json', {
        'schema_version': 1, 'policy_id': POLICY_ID, 'invocation_id': str(uuid.uuid4()),
        'phase': phase, 'context': context, 'coordinator': coordinator,
        'created_utc': now(), 'timeout_seconds': timeout_seconds,
        'argv_provenance': command, 'argv_role': 'PROVENANCE_ONLY; NEVER_REPLAY',
        'log': {'anchor': 'candidate_directory', 'path': PHASES[phase]},
    })

    def publish(identity):
        write_record(directory / 'process.json', {
            'job_sha256': job['record_sha256'], 'identity': identity,
        })

    def finish(status, returncode, error=None):
        identity_path = directory / 'process.json'
        if identity_path.is_symlink():
            raise ValueError('Generation process identity cannot be a symlink')
        identity = read_record(identity_path) if identity_path.exists() else None
        write_record(directory / 'finished.json', {
            'job_sha256': job['record_sha256'], 'status': status,
            'process_sha256': None if identity is None else identity['record_sha256'],
            'returncode': returncode, 'stopped_verified': True,
            'elapsed_seconds': time.monotonic() - started,
            'finished_utc': now(), 'error_type': error,
        })

    try:
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            expired = subprocess.TimeoutExpired(command, timeout_seconds)
            expired.stopped_verified = True  # No child was launched for this reserved invocation.
            raise expired
        code = run_owned_command(command, log_path=log, cwd=work, environment=environment,
                                 timeout_seconds=remaining, on_process=publish)
    except BaseException as exc:
        if getattr(exc, 'stopped_verified', False) is True:
            status = ('TIMED_OUT' if isinstance(exc, subprocess.TimeoutExpired)
                      else 'INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR')
            finish(status, getattr(exc, 'returncode', None), type(exc).__name__)
        raise
    finish('COMPLETED' if code == 0 else 'FAILED', code)
    return code


def inspect_generation_process(work, phase):
    """Read execution state conservatively, including historical and partial jobs.

    Activity applies only to this phase's worker group. Even a sealed stopped
    invocation does not prove the caller has stopped or authorize another attempt.
    Chemistry and candidate usability require their independent existing gates.
    """
    work, directory = _directory(work, phase)
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'phase': phase,
              'state': 'NOT_RECORDED', 'activity': None, 'retry_authorized': False,
              'scope': 'INVOCATION_PROCESS_ONLY; NOT_CHEMISTRY_OR_ATTEMPT_RECOVERY'}
    if not directory.exists():
        return result
    if not directory.is_dir():
        raise ValueError('Generation process evidence is not a directory')
    allowed = {'job.json', 'process.json', 'finished.json'}
    for path in directory.iterdir():
        # An interrupted atomic publication can retain a temporary record. It
        # is evidence, never a replacement for the published named record.
        if path.is_symlink() or not path.is_file() or (path.name not in allowed and not path.name.startswith('.record-')):
            raise ValueError('Unexpected generation process evidence member')
    job_path = directory / 'job.json'
    if not job_path.exists():
        if any((directory / name).exists() for name in ('process.json', 'finished.json')):
            raise ValueError('Generation process evidence has no job')
        return dict(result, state='UNKNOWN')
    job = read_record(job_path)
    if (type(job.get('schema_version')) is not int or job['schema_version'] != 1
            or job.get('policy_id') != POLICY_ID or job.get('phase') != phase
            or not _valid_context(job.get('context'))
            or not _valid_command(job.get('argv_provenance'))
            or not _valid_identity(job.get('coordinator'))
            or not isinstance(job.get('invocation_id'), str)
            or re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', job['invocation_id']) is None
            or job.get('log') != {'anchor': 'candidate_directory', 'path': PHASES[phase]}
            or job.get('argv_role') != 'PROVENANCE_ONLY; NEVER_REPLAY'
            or type(job.get('timeout_seconds')) not in (int, float)
            or not math.isfinite(job['timeout_seconds']) or not 0 < job['timeout_seconds'] <= 600):
        raise ValueError('Invalid generation process job')
    result.update(job=job, state='UNKNOWN')
    # Completion is published after identity. Observe it first, so a concurrent
    # publication cannot pair a new completion with an earlier missing identity.
    finished_path = directory / 'finished.json'
    finished = read_record(finished_path) if finished_path.exists() else None
    identity_path = directory / 'process.json'
    owner = read_record(identity_path) if identity_path.exists() else None
    if owner is not None:
        if owner.get('job_sha256') != job['record_sha256'] or not _valid_identity(owner.get('identity'), child=True):
            raise ValueError('Generation process identity belongs to another job')
        result['identity'] = owner['identity']
    if finished is not None:
        code = finished.get('returncode')
        if (finished.get('job_sha256') != job['record_sha256']
                or finished.get('process_sha256') != (None if owner is None else owner['record_sha256'])
                or finished.get('status') not in FINISHED or finished.get('stopped_verified') is not True
                or type(finished.get('elapsed_seconds')) not in (int, float)
                or not math.isfinite(finished['elapsed_seconds']) or finished['elapsed_seconds'] < 0
                or (code is not None and type(code) is not int)
                or (finished['status'] in {'COMPLETED', 'FAILED'} and
                    (owner is None or code is None or (code == 0) != (finished['status'] == 'COMPLETED')))):
            raise ValueError('Invalid generation process completion')
        return dict(result, state='STOPPED', activity=False, finished=finished)
    if owner is not None:
        activity = process_alive(owner['identity'])
        result.update(activity=activity, state=('LIVE' if activity is True else
                      'STOPPED_UNFINISHED' if activity is False else 'UNKNOWN'))
    return result
