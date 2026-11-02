"""Explicit cache-first acquisition through owned source-generation attempts.

Generation and native usability remain distinct. The qualification adapter owns
its native execution; this API is not a whole-acquisition scheduler or deadline.
Failed evidence and partial outputs are retained. No implicit retries, fallback
usability, ordinary PostMR adoption or model edits are authorized here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from .campaign_records import path_in
from .cif_dictionary_store import (_identity, _regular, _snapshot_destination,
    make_dictionary_request, resolve_qualified_dictionary)
from .cif_generation_attempt import _pins, _root, generate_source_candidate_attempt, inspect_source_generation_request

POLICY_ID = 'cif-source-generation-acquisition-v1'
RECIPE_POLICY_ID = 'cif-source-preserving-generation-recipe-v1'


def _need(value, message):
    if not value:
        raise ValueError(message)


def _json(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def generation_dictionary_options(generation):
    """Map declared generation controls to a reusable source/recipe/producer key.

    No installed files are read: a qualified hit remains usable without its old
    builder. Versions/pins are producer provenance; the store separately checks
    the current consumer. Execution time/attempt limits are not chemical identity.
    """
    required = {'installation_root', 'python_executable', 'elbow_executable', 'api_sources',
                'environment', 'expected_dialect', 'prior_sources', 'phenix_version'}
    optional = {'single_block_steps', 'timeout_seconds', 'max_attempts', 'bond_representation_policy'}
    _need(isinstance(generation, dict) and required <= generation.keys()
          and generation.keys() <= required | optional, 'Require explicit supported generation configuration')
    steps = generation.get('single_block_steps', 180)
    timeout = generation.get('timeout_seconds', 600)
    attempts = generation.get('max_attempts', 2)
    _need(type(steps) is int and 1 <= steps <= 600
          and type(timeout) in (float, int) and math.isfinite(timeout) and 0 < timeout <= 600
          and type(attempts) is int and 1 <= attempts <= 5, 'Invalid bounded generation controls')
    dialect = generation['expected_dialect']
    _need(isinstance(dialect, str) and bool(dialect), 'Require source reader dialect')
    recipe = {'policy_id': RECIPE_POLICY_ID, 'expected_dialect': dialect, 'single_block_steps': steps}
    policy = generation.get('bond_representation_policy')
    from .cif_purine_representation import validate_policy
    validate_policy(policy)
    if policy is not None:
        recipe['bond_representation_policy'] = policy
    generator = {'name': 'phenix.elbow.source-preserving', 'version': generation['phenix_version'],
                 'api_sources': _pins(generation['api_sources']), 'prior_sources': _pins(generation['prior_sources'])}
    _identity(generator)
    return _json({'recipe': recipe, 'generator': generator})


def resolve_generated_dictionary(source, code, store_root, output, request_directory, qualification_directory,
        *, source_authority, consumer, generation, qualify=None):
    """Reuse first; otherwise perform at most one owned generation and qualification.

    ``qualify(source_copy, candidate_copy, consumer_copy, fresh_native_output)``
    supplies complete current isolated usability evidence. Copies and any failed
    native output remain in the fresh qualification directory. Without this
    adapter, misses/stale evidence return without generation. A stale candidate
    is requalified first and failure never falls through to regeneration.

    Repeated explicit misses must share request_directory to share the frozen
    generation allowance, and use fresh output/qualification directories. The
    generation scope binds its source/recipe/producer, independently of consumer
    qualification. No whole-acquisition ownership or automatic retry is claimed.
    """
    generation = deepcopy(generation)
    options = generation_dictionary_options(generation)
    _need(qualify is None or callable(qualify), 'Qualification adapter must be callable')
    consumer = _json(_identity(consumer))
    output = _snapshot_destination(output).resolve()
    qualification_directory = _snapshot_destination(qualification_directory).resolve()
    request_directory = _root(request_directory)
    store = Path(store_root).expanduser().resolve()
    roots = (output, qualification_directory, request_directory, store)
    _need(all(not a.is_relative_to(b) and not b.is_relative_to(a)
              for i, a in enumerate(roots) for b in roots[i+1:]),
          'Dictionary snapshot, qualification, generation request and store must be separate')
    installation = Path(generation['installation_root']).resolve()
    _need(not any(p.is_relative_to(installation) or installation.is_relative_to(p) for p in roots),
          'Acquisition outputs and store must be separate from the selected installation')
    source = Path(source)
    original = _regular(source)
    request = make_dictionary_request(source, code, source_authority=source_authority, **options)
    _need(original == _regular(source), 'Selected source changed before acquisition')
    _need(not any(source.resolve().is_relative_to(p) for p in roots),
          'Selected source must be separate from acquisition outputs and store')

    def checked_qualify(a, b, current_consumer):
        _need(qualify is not None, 'Current native qualification adapter is unavailable')
        _need(_regular(source) == original, 'Selected source changed before qualification')
        directory = _snapshot_destination(qualification_directory)
        left, right = _regular(a), _regular(b)
        _need(left == original, 'Qualification source differs from selected source')
        directory.mkdir(parents=True)
        inputs = directory/'inputs'; inputs.mkdir()
        x, y = inputs/'source.cif', inputs/'dictionary.cif'
        x.write_bytes(left); y.write_bytes(right)
        current = _json(current_consumer)
        result = qualify(x, y, current, directory/'native')
        _need(_regular(x) == left and _regular(y) == right and current == current_consumer
              and _regular(source) == original, 'Native adapter changed a qualification input or consumer')
        # The reusable store validates all chemistry/native evidence independently.
        return result

    def acquire():
        _need(_regular(source) == original, 'Selected source changed before generation')
        result = generate_source_candidate_attempt(source=source, code=code,
            request_directory=request_directory, **generation)
        state = inspect_source_generation_request(request_directory)
        attempt = state['attempts'][result['attempt_number']-1]
        _need(attempt['state'] == 'STOPPED' and attempt['intent']['attempt_id'] == result['attempt_id']
              and state['request']['request_id'] == result['request_id'], 'Generation attempt is not sealed and bound')
        name = f"attempts/attempt-{result['attempt_number']:04d}/generation"
        _need(result['generation_directory'] == {'anchor': 'request_directory', 'path': name},
              'Generation output reference differs')
        work = path_in(request_directory, name)
        receipt_path = path_in(work, 'source_candidate_receipt.json')
        receipt = json.loads(_regular(receipt_path))
        _need(receipt == result['generation'] and receipt.get('component') == code
              and receipt.get('source_sha256') == request['source_sha256']
              and receipt.get('source_preserved') is True and _regular(source) == original,
              'Generation receipt source/identity differs')
        _need(receipt.get('candidate_retained') is True and receipt.get('candidate') is not None,
              'Generation has no retained candidate; retained attempt requires separate recovery')
        candidate = path_in(work, 'candidate.cif'); data = _regular(candidate)
        _need(receipt.get('candidate') == {'anchor': 'candidate_directory', 'path': 'candidate.cif',
              'sha256': sha256(data).hexdigest(), 'size': len(data)}, 'Generated candidate binding differs')
        from .cif_candidate_usability import reassess_complete_candidate
        assessment = reassess_complete_candidate(source, candidate, code,
            bond_representation_policy=generation.get('bond_representation_policy'))
        _need(assessment['candidate_status'] == 'CANDIDATE_REVIEW',
              'Generated candidate does not preserve the selected source chemistry')
        qualification = checked_qualify(source, candidate, consumer)
        _need(_regular(candidate) == data, 'Generated candidate changed during qualification')
        after = inspect_source_generation_request(request_directory)
        _need(after['request'] == state['request']
              and after['attempts'][result['attempt_number']-1] == attempt,
              'Generation evidence changed during qualification')
        # Seal identities are provenance, not a substitute for the native verdict.
        stopping = receipt.get('stopping', {}).get('status', 'NOT_REPORTED')
        provenance = {'converged': False if stopping in {'NOT_CONVERGED_REPORTED', 'ITERATION_LIMIT'} else None,
            'stopping': stopping,
            'notes': ['Source generation does not establish convergence or linked/model usability.',
                      'Generation execution: ' + str(receipt.get('execution', {}).get('status', 'NOT_REPORTED'))],
            'generation_acquisition': {'policy_id': POLICY_ID, 'request': request, 'consumer': consumer,
                'request_id': result['request_id'], 'attempt_id': result['attempt_id'],
                'attempt_number': result['attempt_number'], 'request_sha256': state['request']['record_sha256'],
                'attempt_sha256': attempt['intent']['record_sha256'],
                'completion_sha256': attempt['finished']['record_sha256'],
                'generation_status': receipt.get('status'),
                'stopping_evidence': receipt.get('stopping'), 'execution': receipt.get('execution'),
                'diagnostic': receipt.get('diagnostic'), 'error': receipt.get('error'),
                'generation_receipt_sha256': sha256(_regular(receipt_path)).hexdigest()}}
        if receipt.get('error'):
            provenance['notes'].append('Generation diagnostic: ' + str(receipt['error']))
        return {'candidate': candidate, 'qualification': qualification, 'provenance': provenance}

    return resolve_qualified_dictionary(source, code, store_root, output, source_authority=source_authority,
        consumer=consumer, **options, acquire=acquire if qualify is not None else None,
        requalify=checked_qualify if qualify is not None else None)
