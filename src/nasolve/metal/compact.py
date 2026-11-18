"""Read-only compact views of fully replayed frozen anomalous trials.

This is not a replacement retention manifest. Verification always needs the
original complete trials and their parents; no cache, execution or deletion
authority follows from the projection's self-digest.
"""
from pathlib import Path

from .fdp_compare import _load_trial, MAX_TRIALS
from .materialize import _json, _source
from .recipe import RecipeError, canonical, checksum, digest
from .storage import inspect_storage, DEFAULT_MAX_BYTES, _integer, _state

KIND = 'metal-fdp-compact-projection'
MAX_PROJECTION_BYTES = 16 * 1024 * 1024


def encode(value):
    """The exact compact on-disk encoding; never round scientific values."""
    return (canonical(value) + '\n').encode('utf-8')


def read_projection(path, *, max_projection_bytes=MAX_PROJECTION_BYTES):
    _integer(max_projection_bytes, 'max_projection_bytes', 1)
    path = Path(path).expanduser()
    try:
        before = _state(path)
        if before[2] > max_projection_bytes:
            raise RecipeError('Projection exceeds byte budget')
        with path.open('rb') as handle:
            raw = handle.read(max_projection_bytes + 1)
        if len(raw) != before[2] or _state(path) != before:
            raise RecipeError('Projection changed during read')
        result = _json(raw)
        encode(result)  # Reject nonfinite/non-JSON values before replay.
        return result
    except (OSError, RecursionError, OverflowError) as exc:
        raise RecipeError('Cannot read compact projection: ' + str(exc)) from exc


def _portable_references(value):
    """Refuse absolute operational references; provenance strings are not paths."""
    if isinstance(value, dict):
        if 'anchor' in value:
            path = value.get('relative_path')
            if (value['anchor'] not in {'run','dataset','repository'}
                    or not isinstance(path, str) or not path or '\\' in path
                    or Path(path).is_absolute() or '..' in Path(path).parts
                    or Path(path).as_posix() != path or 'absolute_path' in value):
                raise RecipeError('Projection requires portable declared references')
            checksum(value.get('sha256'), 'projected artifact checksum')
            _integer(value.get('size'), 'projected artifact size')
        for item in value.values():
            _portable_references(item)
    elif isinstance(value, list):
        for item in value:
            _portable_references(item)


def _project_one(run, directory, expected_manifest):
    # Use the existing scientific readback owner, not a new partial freeze audit.
    loaded = _load_trial(run, directory)
    if loaded['ref'] != expected_manifest:
        raise RecipeError('Trial changed after storage preflight')
    doc = _json(_source(loaded['ref'], run))
    native_plan = _json(_source(doc['files']['native-plan.json'], run))
    names = native_plan['args']
    if (not isinstance(names, list) or not names
            or any(not isinstance(name, str) or Path(name).name != name or name not in doc['files'] for name in names)
            or len(names) != len(set(names))):
        raise RecipeError('Native request requires explicit declared input files')
    # Include complete executable inputs plus the complete plan, not a lossy
    # metal-only tuple. Input bytes bind all background atoms, Q/ADPs, flags,
    # references, phases/policies, restraint resources and capture options.
    inputs = {name: {k: doc['files'][name][k] for k in ('sha256','size')}
              for name in sorted(set(names) | {'plan.json','native-plan.json'})}
    basis = loaded['basis']
    basis_id = digest(basis)
    request = dict(basis_id=basis_id, input_files=inputs,
                   settings=loaded['settings'], occupancy_vector=loaded['occupancy_vector'])
    input_id = digest(request)
    record = dict(trial_id=loaded['trial_id'], source_manifest=loaded['ref'],
                  source_result=doc['files']['result.json'], basis_id=basis_id,
                  input_id=input_id, occupancy_vector=loaded['occupancy_vector'],
                  result=loaded['result'])
    record['record_id'] = digest(record)
    _portable_references(basis)
    _portable_references(record)
    return basis_id, basis, input_id, request, record


def project_trials(run, trials, *, max_bytes=DEFAULT_MAX_BYTES,
                   max_projection_bytes=MAX_PROJECTION_BYTES):
    """Project explicit completed trials; original evidence stays indispensable.

    Budgets cover trial payload preflight and serialized output, respectively.
    Existing full replay also traverses parent evidence and expands native JSON;
    these limits are NOT a bound on that upstream I/O, memory or physical disk.
    """
    _integer(max_projection_bytes, 'max_projection_bytes', 1)
    if not isinstance(trials, (list,tuple)) or not 1 <= len(trials) <= MAX_TRIALS:
        raise RecipeError(f'Project 1..{MAX_TRIALS} explicit frozen trials')
    run = Path(run).expanduser().resolve()
    inventory = inspect_storage(run, trials, max_bytes=max_bytes)
    manifests = {row['trial_id']:row['file'] for row in inventory['files']
                 if Path(row['file']['relative_path']).name == 'manifest.json'}
    bases, requests, records, loaded = {}, {}, [], []
    for sample in inventory['samples']:
        item = _project_one(run, sample['directory'], manifests[sample['trial_id']])
        basis_id, basis, input_id, request, record = item
        bases[basis_id] = basis
        requests[input_id] = request
        records.append(record)
        loaded.append(item)
        if len(encode(dict(bases=bases,requests=requests,records=records))) > max_projection_bytes:
            raise RecipeError('Projection exceeds byte budget')
    # The projection neither locks nor publishes a new run. Repeat the existing
    # complete replay to reject changes observed while assembling its view.
    for sample, original in zip(inventory['samples'], loaded):
        if canonical(_project_one(run, sample['directory'], manifests[sample['trial_id']])) != canonical(original):
            raise RecipeError('Source trial changed during compact projection')
    if inspect_storage(run, trials, max_bytes=max_bytes) != inventory:
        raise RecipeError('Trial inventory changed during compact projection')
    sections = dict(bases=bases, requests=requests, records=records)
    report = dict(kind=KIND, schema_version=1, status='PROJECTION_REVIEW',
                  source_replay='FULL_FDP_REPLAY_AT_PROJECTION',
                  standalone_evidence=False, reuse_authorized=False,
                  retirement_authorized=False, materialization_supported=False,
                  scientific_acceptance='NOT_ASSESSED', automatic_checkpoint_selection=False,
                  serialization='canonical_json_utf8_lf', **sections,
                  section_bytes={name:len(canonical(value).encode('utf-8')) for name,value in sections.items()},
                  source_trial_bytes=inventory['logical_bytes'],
                  limits=dict(max_trial_bytes=max_bytes, max_projection_bytes=max_projection_bytes,
                              max_trials=MAX_TRIALS, upstream_replay_budgeted=False),
                  note='Input fingerprints describe recorded inputs and native identity, not complete environment or cache eligibility. '
                       'All attempts and complete result summaries are retained. Shared metadata is not a recoverable input store; '
                       'original parent/native evidence is required for verification. No saving or safe-retirement claim includes omitted inputs.')
    report['projection_id'] = digest(report)
    raw = encode(report)
    if len(raw) > max_projection_bytes:
        raise RecipeError('Projection exceeds byte budget')
    return _json(raw)


def verify_projection(run, projection, *, max_bytes=DEFAULT_MAX_BYTES,
                      max_projection_bytes=MAX_PROJECTION_BYTES):
    """Reconstruct against original evidence; a self-consistent digest is insufficient."""
    _integer(max_projection_bytes, 'max_projection_bytes', 1)
    try:
        if len(encode(projection)) > max_projection_bytes:
            raise RecipeError('Projection exceeds byte budget')
        if (not isinstance(projection, dict) or projection.get('kind') != KIND
                or type(projection.get('schema_version')) is not int or projection['schema_version'] != 1):
            raise RecipeError('Unsupported compact projection')
        check = dict(projection)
        if check.pop('projection_id', None) != digest(check):
            raise RecipeError('Compact projection digest changed')
        rows = projection['records']
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_TRIALS:
            raise RecipeError('Invalid projected trial count')
        run = Path(run).expanduser().resolve()
        trials = []
        for row in rows:
            ref = row['source_manifest']
            _portable_references(ref)
            if ref['anchor'] != 'run' or Path(ref['relative_path']).name != 'manifest.json':
                raise RecipeError('Require explicit run-anchored trial manifests')
            # project_trials applies numbered-path, manifest-size and payload
            # preflight before the existing source reader touches any trial.
            trials.append(Path(ref['relative_path']).parent)
        limits = projection['limits']
        _integer(limits['max_trial_bytes'], 'saved max_trial_bytes', 1)
        _integer(limits['max_projection_bytes'], 'saved max_projection_bytes', 1)
        # A supplied resource cap can restrict verification, never be enlarged
        # by the saved report. Rebuild with recorded limits only after preflight.
        if projection['source_trial_bytes'] > max_bytes:
            raise RecipeError('Saved sample exceeds verification byte budget')
        replay = project_trials(run, trials, max_bytes=min(max_bytes,limits['max_trial_bytes']),
                                max_projection_bytes=min(max_projection_bytes,limits['max_projection_bytes']))
        # Limits affect resource use, not scientific contents. Compare at the
        # original declared limits after enforcing the caller's stricter caps.
        replay['limits']['max_trial_bytes'] = limits['max_trial_bytes']
        replay['limits']['max_projection_bytes'] = limits['max_projection_bytes']
        replay.pop('projection_id')
        replay['projection_id'] = digest(replay)
        if canonical(replay) != canonical(projection):
            raise RecipeError('Compact projection differs from complete source replay')
        return replay
    except (OSError, KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot verify compact projection: ' + str(exc)) from exc
