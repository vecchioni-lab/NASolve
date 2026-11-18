"""Read-only byte accounting for explicitly selected, complete frozen fdp trials.

This is a storage-integrity check, not verify_fdp's scientific replay. No parent
payload is traversed, no native code runs, and no file is eligible for retirement.
"""
import hashlib
from pathlib import Path
import re
import stat

from .fdp import PROTOCOL
from .materialize import _json
from .recipe import RecipeError, checksum, digest

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_FILES_PER_TRIAL = 256
MAX_TRIALS = 256
DEFAULT_MAX_BYTES = 1024 ** 3
_REQUIRED = {'input.pdb', 'observations.mtz', 'parameters.phil', 'plan.json',
             'native-plan.json', 'free-r.json', 'native-result.json.gz',
             'final.pdb', 'native.log', 'result.json'}


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise RecipeError(f'{name} must be an integer >= {minimum}')
    return value


def _state(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode):
        raise RecipeError('Storage inventory requires regular files: ' + path.name)
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _snapshot(path):
    states = {}
    for member in path.iterdir():
        if len(states) >= MAX_FILES_PER_TRIAL:
            raise RecipeError('Trial file-count limit exceeded')
        states[member.name] = _state(member)
    return states


def _hash(path, expected_state):
    if _state(path) != expected_state:
        raise RecipeError('Storage inventory changed during inspection')
    h = hashlib.sha256()
    remaining = expected_state[2]
    with path.open('rb') as handle:
        while remaining:
            block = handle.read(min(1024 * 1024, remaining))
            if not block:
                raise RecipeError('Storage inventory changed during inspection')
            h.update(block)
            remaining -= len(block)
        if handle.read(1):
            raise RecipeError('Storage inventory grew during inspection')
    if _state(path) != expected_state:
        raise RecipeError('Storage inventory changed during inspection')
    return h.hexdigest()


def _role(name):
    # Roles follow the producer's named contract, never an extension purge rule.
    if name == 'map-anomalous.mtz':
        return 'anomalous_map'
    if name in {'input.pdb', 'observations.mtz', 'parameters.phil'} or name.startswith('resource_'):
        return 'trial_input'
    if name in {'manifest.json', 'plan.json', 'native-plan.json', 'free-r.json', 'result.json'}:
        return 'receipt_or_plan'
    if name in {'final.pdb', 'native-result.json.gz', 'native.log'}:
        return 'native_evidence'
    return 'other_declared_payload'


def inspect_storage(run, trials, *, max_bytes=DEFAULT_MAX_BYTES, forecast=None):
    """Inventory an explicit sample; hash every payload within a total byte cap.

    Forecast describes the CURRENT uncompressed layout, using the largest sampled
    trial. All other allowances must be explicit. It is a scenario, not a quota
    reservation or a guaranteed bound on different datasets/future native jobs.
    """
    _integer(max_bytes, 'max_bytes', 1)
    run = Path(run).expanduser().resolve()
    trials = list(trials)
    if not 1 <= len(trials) <= MAX_TRIALS:
        raise RecipeError(f'Require 1..{MAX_TRIALS} explicit trials')
    directories, snapshots, envelopes = [], {}, []
    for value in trials:
        path = Path(value).expanduser()
        if '..' in path.parts:
            raise RecipeError('Trial path traversal is unsupported')
        if not path.is_absolute():
            path = run / path
        if path.is_symlink() or path.parent.is_symlink():
            raise RecipeError('Trial directory must not be a symlink')
        path = path.resolve()
        if path.parent != run / 'Metal' or not re.fullmatch(r'fdp_\d{3,}', path.name):
            raise RecipeError('Require an explicit numbered fdp trial within this run')
        if path in directories:
            raise RecipeError('Duplicate requested trial')
        directories.append(path)
        states = _snapshot(path)
        if 'manifest.json' not in states or states['manifest.json'][2] > MAX_MANIFEST_BYTES:
            raise RecipeError('Missing or oversized trial manifest')
        with (path / 'manifest.json').open('rb') as handle:
            raw = handle.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) != states['manifest.json'][2]:
            raise RecipeError('Trial manifest changed during inspection')
        doc = _json(raw)
        if not isinstance(doc, dict):
            raise RecipeError('Invalid trial manifest')
        check = dict(doc)
        trial_id = check.pop('trial_id', None)
        if (digest(check) != trial_id or doc.get('kind') != 'metal-fdp-trial'
                or type(doc.get('schema_version')) is not int or doc['schema_version'] != 1
                or doc.get('protocol') != PROTOCOL or doc.get('status') != 'FDP_REVIEW'
                or doc.get('automatic_checkpoint_selection') is not False
                or doc.get('scientific_acceptance') != 'NOT_ASSESSED'
                or not isinstance(doc.get('execution'), dict)
                or doc['execution'].get('mode') != 'complete'):
            raise RecipeError('Unsupported, incomplete or changed fdp manifest')
        files = doc.get('files')
        if (not isinstance(files, dict) or not _REQUIRED <= files.keys()
                or set(states) != {'manifest.json', *files}):
            raise RecipeError('Incomplete or unexpected trial inventory')
        parent = doc.get('parent')
        if not isinstance(parent, dict):
            raise RecipeError('Missing parent declaration')
        pref = parent.get('manifest', {})
        if (not isinstance(pref, dict) or pref.get('anchor') != 'run'
                or not isinstance(pref.get('relative_path'), str)
                or not pref['relative_path']
                or Path(pref['relative_path']).as_posix() != pref['relative_path']
                or Path(pref['relative_path']).is_absolute()
                or '..' in Path(pref['relative_path']).parts):
            raise RecipeError('Parent must have a declared run-relative reference')
        checksum(pref.get('sha256'), 'parent manifest checksum declaration')
        _integer(pref.get('size'), 'parent manifest size declaration')
        snapshots[path] = states
        envelopes.append((path, doc, hashlib.sha256(raw).hexdigest()))
    total = sum(s[2] for states in snapshots.values() for s in states.values())
    if total > max_bytes:
        raise RecipeError(f'Storage inventory exceeds byte budget ({total} > {max_bytes})')
    rows, samples, content, roles = [], [], {}, {}
    for path, doc, manifest_hash in envelopes:
        trial_rows = []
        for name, before in sorted(snapshots[path].items()):
            sha = _hash(path / name, before)
            ref = dict(anchor='run', relative_path=(path / name).relative_to(run).as_posix(),
                       sha256=sha, size=before[2])
            if name == 'manifest.json':
                if sha != manifest_hash:
                    raise RecipeError('Trial manifest changed during inspection')
            elif (not isinstance(doc['files'][name], dict)
                  or type(doc['files'][name].get('size')) is not int
                  or doc['files'][name] != ref):
                raise RecipeError('Trial payload checksum, size or anchor mismatch: ' + name)
            role = _role(name)
            row = dict(trial_id=doc['trial_id'], role=role, file=ref)
            rows.append(row)
            trial_rows.append(row)
            content.setdefault((sha, before[2]), []).append(ref['relative_path'])
            roles[role] = roles.get(role, 0) + before[2]
        samples.append(dict(trial_id=doc['trial_id'], directory=path.relative_to(run).as_posix(),
                            logical_bytes=sum(r['file']['size'] for r in trial_rows),
                            file_count=len(trial_rows), parent=doc['parent'],
                            parent_payload_counted=False))
    # Catch additions/removals and later changes before publishing the observation.
    for path, states in snapshots.items():
        if _snapshot(path) != states:
            raise RecipeError('Storage inventory changed during inspection')
    unique = sum(size for sha, size in content)
    report = dict(kind='metal-fdp-storage-inventory', schema_version=1,
                  evidence_level='manifest_and_payload_integrity_only',
                  scientific_replay=False, retirement_authorized=False,
                  upstream_payloads_counted=False, physical_disk_usage_measured=False,
                  scope='explicit complete frozen-fdp trial directories only',
                  logical_bytes=total, unique_content_bytes=unique,
                  repeated_content_bytes=total-unique, bytes_by_role=roles,
                  samples=samples, files=rows,
                  repeated_contents=[dict(sha256=sha, size=size, paths=paths)
                                     for (sha, size), paths in sorted(content.items()) if len(paths)>1],
                  limits=dict(max_bytes=max_bytes, max_trials=MAX_TRIALS,
                              max_files_per_trial=MAX_FILES_PER_TRIAL),
                  forecast=None)
    if forecast is not None:
        report['forecast'] = forecast_storage(max(s['logical_bytes'] for s in samples), forecast)
    report['inventory_id'] = digest(report)
    return report


def forecast_storage(sample_trial_bytes, request):
    keys = {'datasets', 'trials_per_dataset', 'protected_bytes_per_dataset',
            'concurrent_jobs', 'scratch_bytes_per_job', 'compaction_overlap_bytes',
            'reserve_bytes'}
    if not isinstance(request, dict) or set(request) != keys:
        raise RecipeError('Forecast requires exactly: ' + ', '.join(sorted(keys)))
    for name, value in request.items():
        _integer(value, name, 1 if name in {'datasets', 'trials_per_dataset', 'concurrent_jobs'} else 0)
    _integer(sample_trial_bytes, 'sample_trial_bytes', 1)
    points = request['datasets'] * request['trials_per_dataset']
    if request['concurrent_jobs'] > points:
        raise RecipeError('Concurrent jobs exceed forecast trial count')
    completed = points * sample_trial_bytes
    protected = request['datasets'] * request['protected_bytes_per_dataset']
    scratch = request['concurrent_jobs'] * request['scratch_bytes_per_job']
    return dict(basis='largest_sampled_trial_in_current_layout', assumptions=request.copy(),
                sample_trial_bytes=sample_trial_bytes, trial_count=points,
                completed_trial_bytes=completed, protected_bytes=protected,
                concurrent_scratch_bytes=scratch,
                scenario_peak_bytes=completed+protected+scratch+request['compaction_overlap_bytes']+request['reserve_bytes'],
                compact_layout_estimated=False, guaranteed_upper_bound=False,
                reserved_bytes=0)
