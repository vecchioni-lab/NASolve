"""Bounded, explicit source-generation attempts under one durable request.

This owns generation only, not source discovery, cache selection, qualification,
or adoption. A call performs one fresh attempt; there is no automatic retry loop.
Readers never create locks or signal saved processes. All callers coordinating
one logical request must use the same request directory.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import uuid

from .campaign_process import CampaignProcessError, coordinator_alive, current_process_identity, exclusive_lock
from .campaign_records import _sync_directory, now, path_in, read_record, write_record
from .cif_generation_process import PHASES, _valid_identity, _valid_attempt_identity, inspect_generation_process
from .cif_source_candidate import generate_source_candidate
from .cif_generation_input import validate_source_input_policy, source_input_files, generation_source
from .cif_elbow_contract import _inside, _safe

POLICY_ID = 'cif-source-generation-request-v1'
ANCHOR = 'request_directory'
_UUID = r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}'


def _root(path):
    path = Path(path).absolute()
    if any(p.is_symlink() or (p.exists() and not p.is_dir()) for p in (path, *path.parents)):
        raise ValueError('Generation request must have regular directory ancestors')
    # Normalize dot segments only after rejecting symlink ancestors.
    return path.resolve()


def _members(path, allowed):
    for member in path.iterdir():
        if member.is_symlink() or (member.name not in allowed and not
                (member.name.startswith('.record-') and member.is_file())):
            raise ValueError('Unexpected generation request evidence member: ' + member.name)


def _digest(data):
    return {'sha256': sha256(data).hexdigest(), 'size': len(data)}


def _valid_digest(value):
    return (isinstance(value, dict) and isinstance(value.get('sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None
            and type(value.get('size')) is int and value['size'] >= 0)


def _pins(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Generation request requires native source pins')
    result = []
    for row in rows:
        if not _valid_digest(row) or row.get('anchor') != 'phenix_installation':
            raise ValueError('Invalid generation request native source pin')
        name = row.get('path')
        if not _safe(name):
            raise ValueError('Invalid generation request native source path')
        result.append({k: row[k] for k in ('anchor', 'path', 'sha256', 'size')})
    if len({r['path'] for r in result}) != len(result):
        raise ValueError('Duplicate generation request native source pin')
    return sorted(result, key=lambda r: r['path'])


def _validate_configuration(config):
    if (not isinstance(config, dict) or not _valid_digest(config.get('source'))
            or not isinstance(config.get('component'), str)
            or re.fullmatch('[A-Z0-9]{1,3}', config['component']) is None
            or type(config.get('max_attempts')) is not int or not 1 <= config['max_attempts'] <= 5):
        raise ValueError('Invalid generation request configuration')
    recipe, generator = config.get('recipe'), config.get('generator')
    if (not isinstance(recipe, dict) or not isinstance(generator, dict)
            or not isinstance(recipe.get('expected_dialect'), str) or not recipe['expected_dialect']
            or type(recipe.get('single_block_steps')) is not int or not 1 <= recipe['single_block_steps'] <= 600
            or type(recipe.get('timeout_seconds')) not in (int, float)
            or not math.isfinite(recipe['timeout_seconds']) or not 0 < recipe['timeout_seconds'] <= 600
            or not isinstance(generator.get('phenix_version'), str) or not generator['phenix_version']):
        raise ValueError('Invalid generation request recipe')
    if 'multiple_planes' in recipe and recipe['multiple_planes'] is not True:
        raise ValueError('Noncanonical generation multiple-plane choice')
    from .cif_purine_representation import validate_policy
    validate_policy(recipe.get('bond_representation_policy'))
    validate_source_input_policy(recipe.get('source_input_policy'))
    if 'source_input_policy' in recipe and recipe['source_input_policy'] is None:
        raise ValueError('Noncanonical source input policy')
    if ('source_preparation' in config) != ('source_input_policy' in recipe):
        raise ValueError('Generation source preparation binding differs')
    for field in ('api_sources', 'prior_sources'):
        if _pins(generator.get(field)) != generator[field]:
            raise ValueError('Noncanonical generation request native pins')
    dispatchers = generator.get('dispatchers')
    if not isinstance(dispatchers, dict) or set(dispatchers) != {'python', 'elbow'}:
        raise ValueError('Invalid generation request dispatchers')
    for row in dispatchers.values():
        _pins([row])


def _attempt_identity(intent):
    return {'request_sha256': intent['request_sha256'], 'attempt_sha256': intent['record_sha256'],
            'attempt_id': intent['attempt_id']}


def _phase_evidence(attempt, intent, config):
    work = path_in(attempt, 'generation')
    if not work.exists():
        return {}, {}
    if not work.is_dir():
        raise ValueError('Generation output is not a directory')
    execution = path_in(work, 'execution')
    if execution.exists():
        if not execution.is_dir():
            raise ValueError('Generation execution evidence is not a directory')
        _members(execution, set(PHASES))
    states, bindings = {}, {}
    for phase in PHASES:
        state = inspect_generation_process(work, phase)
        states[phase] = state['state']
        job = state.get('job')
        if job is not None:
            context = job['context']
            owner = intent['coordinator']
            if (context['component'] != config['component'] or context['source_sha256'] != generation_source(config)[1]['sha256']
                    or context.get('attempt_owner') != _attempt_identity(intent)
                    or any(job['coordinator'].get(k) != owner.get(k)
                           for k in ('pid', 'pgid', 'host', 'boot_id', 'start_marker'))):
                raise ValueError('Generation phase belongs to another request/coordinator')
            if config['recipe'].get('multiple_planes') is True:
                from .cif_source_candidate import MULTIPLE_PLANE_POLICY_ID
                if (context.get('multiple_planes') is not True
                        or context.get('candidate_policy_id') != MULTIPLE_PLANE_POLICY_ID):
                    raise ValueError('Generation phase lacks frozen multiple-plane authority')
        bindings[phase] = {}
        for name in ('job', 'process', 'finished'):
            path = path_in(work, f'execution/{phase}/{name}.json')
            bindings[phase][name] = read_record(path)['record_sha256'] if path.exists() else None
    return states, bindings


def _receipt(attempt):
    path = path_in(attempt, 'generation/source_candidate_receipt.json')
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError('Generation receipt is not a regular file')
    return {'anchor': 'attempt_directory', 'path': 'generation/source_candidate_receipt.json', **_digest(path.read_bytes())}


def _attempt_state(directory, number, request):
    _members(directory, {'attempt.json', 'finished.json', 'generation'})
    result = {'number': number, 'state': 'UNKNOWN', 'activity': None}
    intent_path = path_in(directory, 'attempt.json')
    if not intent_path.exists():
        if (directory/'finished.json').exists() or (directory/'generation').exists():
            raise ValueError('Generation attempt has output without intent')
        return result
    intent = read_record(intent_path)
    if (intent.get('request_sha256') != request['record_sha256']
            or type(intent.get('number')) is not int or intent['number'] != number
            or not isinstance(intent.get('attempt_id'), str) or re.fullmatch(_UUID, intent['attempt_id']) is None
            or not _valid_identity(intent.get('coordinator'))
            or intent.get('generation') != {'anchor': 'attempt_directory', 'path': 'generation'}
            or ('parent_attempt' in intent and not _valid_attempt_identity(intent['parent_attempt']))):
        raise ValueError('Invalid generation attempt intent')
    # Observe the final immutable record before its dependencies: a completion
    # published mid-read must not be paired with an earlier phase observation.
    finished_path = path_in(directory, 'finished.json')
    finished = read_record(finished_path) if finished_path.exists() else None
    states, bindings = _phase_evidence(directory, intent, request['configuration'])
    result.update(intent=intent, phases=states)
    if finished is not None:
        if (finished.get('attempt_sha256') != intent['record_sha256']
                or finished.get('stopped_verified') is not True
                or finished.get('outcome') not in {'RETURNED', 'RAISED'}
                or finished.get('phase_records') != bindings
                or finished.get('candidate_receipt') != _receipt(directory)
                or any(s not in {'STOPPED', 'NOT_RECORDED'} for s in states.values())):
            raise ValueError('Invalid generation attempt completion')
        return dict(result, state='STOPPED', activity=False, finished=finished)
    active = coordinator_alive(intent['coordinator'])
    safe = active is False and all(s in {'NOT_RECORDED', 'STOPPED', 'STOPPED_UNFINISHED'} for s in states.values())
    activity = False if safe else True if active is True or 'LIVE' in states.values() else None
    return dict(result, coordinator_activity=active, activity=activity,
                state='STOPPED_UNFINISHED' if safe else 'LIVE' if activity is True else 'UNKNOWN')


def inspect_source_generation_request(directory):
    """Read request evidence without reservation, mutation, or retry authority.

    AVAILABLE is an advisory observation. The modifying API rechecks it while
    holding the persistent lock. A sealed completion closes this function call,
    even if its caller remains alive; unsealed calls require coordinator death.
    """
    root = _root(directory)
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'state': 'NOT_RECORDED',
              'availability': 'BLOCKED', 'retry_authorized': False, 'attempts': [],
              'scope': 'SOURCE_GENERATION_ONLY; NOT_QUALIFICATION_OR_ADOPTION'}
    if not root.exists():
        return result
    _members(root, {'request.json', 'request.lock', 'inputs', 'attempts'})
    request_path = path_in(root, 'request.json')
    if not request_path.exists():
        return dict(result, state='UNKNOWN')
    request = read_record(request_path)
    if (type(request.get('schema_version')) is not int or request['schema_version'] != 1
            or request.get('policy_id') != POLICY_ID
            or not isinstance(request.get('request_id'), str) or re.fullmatch(_UUID, request['request_id']) is None
            or request.get('source') != {'anchor': ANCHOR, 'path': 'inputs/source.cif'}):
        raise ValueError('Invalid generation request record')
    config = request.get('configuration'); _validate_configuration(config)
    source = path_in(root, 'inputs/source.cif')
    if not source.is_file() or _digest(source.read_bytes()) != config['source']:
        raise ValueError('Generation request source snapshot changed')
    _validate_inputs(root,config)
    attempts = path_in(root, 'attempts')
    rows = []
    if attempts.exists():
        if not attempts.is_dir():
            raise ValueError('Generation attempts is not a directory')
        folders = sorted(attempts.iterdir())
        for number, folder in enumerate(folders, 1):
            if folder.is_symlink() or not folder.is_dir() or folder.name != f'attempt-{number:04d}':
                raise ValueError('Generation attempts must be consecutive immutable directories')
            rows.append(_attempt_state(folder, number, request))
    if len(rows) > config['max_attempts']:
        raise ValueError('Generation request exceeded frozen attempt allowance')
    safe = all(row['state'] in {'STOPPED', 'STOPPED_UNFINISHED'} for row in rows)
    availability = 'BLOCKED' if not safe else 'EXHAUSTED' if len(rows) == config['max_attempts'] else 'AVAILABLE'
    return dict(result, state='RECORDED', request=request, attempts=rows, availability=availability)


def _configuration(root, python, elbow, api, source_bytes, code, options, max_attempts):
    def dispatcher(path):
        if not path.is_relative_to(root):
            raise ValueError('Generation request dispatcher is outside selected installation')
        return {'anchor': 'phenix_installation', 'path': path.relative_to(root).as_posix(), **_digest(path.read_bytes())}
    config = {'source': _digest(source_bytes), 'component': code, 'max_attempts': max_attempts,
              'recipe': {key: options[key] for key in ('expected_dialect', 'single_block_steps', 'timeout_seconds', 'bond_representation_policy')},
              'generator': {'phenix_version': options['phenix_version'], 'api_sources': _pins(api),
                            'prior_sources': _pins(options['prior_sources']),
                            'dispatchers': {'python': dispatcher(python), 'elbow': dispatcher(elbow)}}}
    if options.get('multiple_planes') is True:
        config['recipe']['multiple_planes']=True
    if options.get('source_input_policy') is not None:
        config['recipe']['source_input_policy']=options['source_input_policy']
        config['source_preparation']=source_input_files(source_bytes,code)[0]
    _validate_configuration(config)
    for row in config['generator']['api_sources'] + config['generator']['prior_sources']:
        path = _inside(root, row['path'])
        if _digest(path.read_bytes()) != {k: row[k] for k in ('sha256', 'size')}:
            raise ValueError('Generation request native source changed')
    # Detach caller-owned lists/dicts before reserving immutable intent.
    return json.loads(json.dumps(config, allow_nan=False))


def _validate_inputs(root, config):
    original=path_in(root,'inputs/source.cif').read_bytes()
    if _digest(original)!=config['source']:
        raise ValueError('Generation original source changed')
    folder=root/'inputs'
    if 'source_preparation' not in config:
        _members(folder,{'source.cif'})
        return
    expected,files=source_input_files(original,config['component'])
    if expected!=config['source_preparation']:
        raise ValueError('Generation source projection differs from original')
    _members(folder,{'source.cif','prepared'})
    _members(path_in(folder,'prepared'),{Path(n).name for n in files})
    for name,data in files.items():
        if path_in(folder,name).read_bytes()!=data:
            raise ValueError('Prepared generation input changed: '+name)


def _seal(attempt, intent, request, outcome, error=None):
    states, bindings = _phase_evidence(attempt, intent, request['configuration'])
    if any(s not in {'STOPPED', 'NOT_RECORDED'} for s in states.values()):
        raise CampaignProcessError('Generation attempt has unresolved worker ownership')
    write_record(attempt/'finished.json', {'attempt_sha256': intent['record_sha256'],
        'outcome': outcome, 'error_type': error, 'stopped_verified': True, 'finished_utc': now(),
        'phase_records': bindings, 'candidate_receipt': _receipt(attempt)})


def generate_source_candidate_attempt(installation_root, python_executable, elbow_executable,
        api_sources, source, code, request_directory, *, environment, expected_dialect,
        prior_sources, phenix_version, single_block_steps=180, timeout_seconds=600,
        bond_representation_policy=None, max_attempts=2, _parent_attempt_identity=None, _remaining_seconds=None,
        multiple_planes=False, source_input_policy=None):
    """Run one fresh generation attempt under a frozen request (at most five).

    Repeated calls are explicit retries, not cache hits. Each gets a fresh UUID
    and numbered directory; even failed/empty attempts consume their allowance.
    The unchanged low-level generator remains available for legacy one-shot
    callers. A different request directory is a different coordination scope.
    Explicit source_input_policy preserves original chemical authority and freezes
    separately derived reader inputs. Native phases bind that derived input; final
    acquisition qualification still uses the original. Legacy recipes are unchanged.
    """
    validate_source_input_policy(source_input_policy)
    if type(multiple_planes) is not bool:
        raise ValueError('multiple_planes must be a boolean')
    if _parent_attempt_identity is not None and not _valid_attempt_identity(_parent_attempt_identity):
        raise ValueError('Invalid acquisition parent attempt identity')
    if _remaining_seconds is not None and not callable(_remaining_seconds):
        raise ValueError('Invalid outer generation allowance')
    root = _root(request_directory)
    if root.exists():
        _members(root, {'request.json', 'request.lock', 'inputs', 'attempts'})
        lock = root/'request.lock'
        if lock.exists() and not lock.is_file():
            raise ValueError('Generation request lock is not a regular file')
        if not (root/'request.json').exists() and any(p.name != 'request.lock' for p in root.iterdir()):
            raise CampaignProcessError('Generation request has unresolved initial publication')
    installation = Path(installation_root).resolve(strict=True)
    python, elbow = (Path(p).resolve(strict=True) for p in (python_executable, elbow_executable))
    source = Path(source).resolve(strict=True)
    if root.is_relative_to(installation) or source.is_relative_to(root):
        raise ValueError('Generation request must be separate from installation and caller source')
    original = source.read_bytes()
    options = dict(expected_dialect=expected_dialect, prior_sources=prior_sources, phenix_version=phenix_version,
                   single_block_steps=single_block_steps, timeout_seconds=timeout_seconds,
                   bond_representation_policy=bond_representation_policy)
    if multiple_planes:
        options['multiple_planes']=True
    if source_input_policy is not None:
        options['source_input_policy']=source_input_policy
    config = _configuration(installation, python, elbow, api_sources, original, code, options, max_attempts)
    coordinator = current_process_identity()
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(root/'request.lock'):
        if not (root/'request.json').exists():
            if {p.name for p in root.iterdir()} != {'request.lock'}:
                raise CampaignProcessError('Generation request has unresolved initial publication')
            inputs = root/'inputs'; inputs.mkdir()
            files={'source.cif':original}
            if source_input_policy is not None:
                projection,prepared=source_input_files(original,code)
                if projection!=config['source_preparation']:
                    raise ValueError('Generation source projection changed before publication')
                files.update(prepared)
            for name,data in files.items():
                path=inputs/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as handle:
                    handle.write(data); handle.flush(); os.fsync(handle.fileno())
            for folder in sorted({inputs,*[p for p in inputs.rglob('*') if p.is_dir()]},key=lambda p:len(p.parts),reverse=True):
                _sync_directory(folder)
            write_record(root/'request.json', {'schema_version': 1, 'policy_id': POLICY_ID,
                'request_id': str(uuid.uuid4()), 'created_utc': now(), 'configuration': config,
                'source': {'anchor': ANCHOR, 'path': 'inputs/source.cif'}})
        state = inspect_source_generation_request(root)
        request = state['request']
        if request['configuration'] != config:
            raise ValueError('Generation request identity differs from frozen request')
        if state['availability'] != 'AVAILABLE':
            reason = 'exhausted attempt allowance' if state['availability'] == 'EXHAUSTED' else 'unresolved previous attempt'
            raise CampaignProcessError('Generation request has ' + reason)
        number = len(state['attempts']) + 1
        attempt = root/'attempts'/f'attempt-{number:04d}'; attempt.mkdir(parents=True, exist_ok=False)
        intent = write_record(attempt/'attempt.json', {'request_sha256': request['record_sha256'],
            'number': number, 'attempt_id': str(uuid.uuid4()), 'coordinator': coordinator, 'created_utc': now(),
            'generation': {'anchor': 'attempt_directory', 'path': 'generation'},
            **({'parent_attempt':dict(_parent_attempt_identity)} if _parent_attempt_identity is not None else {})})
        try:
            effective = dict(options)
            effective.pop('source_input_policy',None)
            input_name,_,effective['expected_dialect']=generation_source(config)
            if _remaining_seconds is not None:
                remaining = _remaining_seconds()
                if type(remaining) not in (int,float) or not math.isfinite(remaining) or remaining <= 0:
                    raise ValueError('Outer generation allowance is exhausted or invalid')
                effective['timeout_seconds'] = min(timeout_seconds, remaining)
            result = generate_source_candidate(installation, python, elbow, config['generator']['api_sources'],
                path_in(root/'inputs',input_name), code, attempt/'generation', environment=environment,
                attempt_identity=_attempt_identity(intent),
                **{**effective, 'prior_sources': config['generator']['prior_sources']})
            if _digest((root/'inputs/source.cif').read_bytes()) != config['source']:
                raise ValueError('Generation request source snapshot changed during execution')
            _validate_inputs(root,config)
            # Mutable installed files cannot silently change a frozen request.
            if _configuration(installation, python, elbow, api_sources, original, code, options, max_attempts) != config:
                raise ValueError('Generation request native inputs changed during execution')
        except BaseException as exc:
            _seal(attempt, intent, request, 'RAISED', type(exc).__name__)
            raise
        _seal(attempt, intent, request, 'RETURNED')
        return {'schema_version': 1, 'policy_id': POLICY_ID, 'request_id': request['request_id'],
                'attempt_id': intent['attempt_id'], 'attempt_number': number,
                'generation_directory': {'anchor': ANCHOR, 'path': f'attempts/attempt-{number:04d}/generation'},
                'generation': result}
