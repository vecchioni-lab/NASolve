"""Offline, matched-endpoint comparisons; no native jobs or solution ranking."""
import gzip
from pathlib import Path
import re

from .binding import AtomKey
from .context import _reference, parse_pdb
from .fdp import verify_fdp
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest

PROTOCOL = 'metal-fdp-comparison-v1'
BUDGET_AXES = ('cycles', 'minimizer_cycles', 'max_iterations')
SETTING_AXES = ('start_fdp', *BUDGET_AXES)
MAX_TRIALS = 128


def _load_trial(run, directory):
    doc = verify_fdp(run, directory)
    directory = run / Path(doc['files']['result.json']['relative_path']).parent
    ref = _reference(directory / 'manifest.json', run)
    if canonical(_json(_source(ref, run))) != canonical(doc):
        raise RecipeError('Trial changed during comparison readback')
    plan = _json(_source(doc['files']['plan.json'], run))
    result = _json(_source(doc['files']['result.json'], run))
    native = _json(gzip.decompress(_source(doc['files']['native-result.json.gz'], run)))
    geometry = _json(_source(doc['parent']['manifest'], run))
    hypothesis = _json(_source(geometry['parent']['manifest'], run))
    parsed = parse_pdb(_source(doc['files']['input.pdb'], run))
    state = parsed.to_dict()['atomic_state']
    indices = {a.key: i for i, a in enumerate(parsed.snapshot.atoms)}
    q = {site['node_id']: state[indices[AtomKey(**site['key'])]]['occupancy']
         for site in hypothesis['sites']}
    groups = []
    for original in plan['groups']:
        group = dict(original)
        if group['refine_fdp']:
            group.pop('f_double_prime_start')
        groups.append(group)
    # Only declared starts, budgets and placed-metal q may differ. Version,
    # background, actual reflection selection and all inherited inputs must match.
    basis = dict(parent=doc['parent'], input_sources=doc['input_sources'],
                 metadata=plan['metadata'], references=plan['references'], groups=groups,
                 policy={k: v for k, v in plan['policy'].items() if k not in BUDGET_AXES},
                 tolerances=plan['tolerances'], background_policy=plan['background_policy'],
                 nuisance_policy=plan['nuisance_policy'], phase_policy=plan['phase_policy'],
                 worker_sha256=doc['worker_sha256'], native_protocol=doc['protocol'],
                 native_version=native['native_version'], native_source_hashes=native['native_source_hashes'],
                 normal_scattering_types=native['normal_scattering_before'],
                 reflection_input_hash=native['reflection_before']['hash'])
    return dict(ref=ref, trial_id=doc['trial_id'], basis=basis, result=result,
                occupancy_vector=dict(sorted(q.items())),
                settings={axis: plan['options'][axis] for axis in SETTING_AXES})


def _load_trials(run, directories):
    if not isinstance(directories, (list, tuple)) or not 2 <= len(directories) <= MAX_TRIALS:
        raise RecipeError(f'Compare 2 to {MAX_TRIALS} explicit audited fdp trials')
    loaded = [_load_trial(run, directory) for directory in directories]
    if len({t['trial_id'] for t in loaded}) != len(loaded):
        raise RecipeError('Duplicate trial in comparison')
    baseline = canonical(loaded[0]['basis'])
    if any(canonical(t['basis']) != baseline for t in loaded[1:]):
        raise RecipeError('Trials do not share the same geometry, data, groups, references and native protocol')
    return loaded


def _sensitivity(rows, axis):
    """Compare one variable at a time, retaining every independent endpoint."""
    grouped = {}
    for row in rows:
        q = dict(row['occupancy_vector'])
        settings = dict(row['settings'])
        value = q.pop(row['node_id']) if axis == 'occupancy' else settings.pop(axis)
        fixed = dict(node_id=row['node_id'], key=row['key'], element=row['element'],
                     reference_f_double_prime=row['reference_f_double_prime'],
                     fixed_occupancies=q, fixed_settings=settings)
        key = canonical(fixed)
        group = grouped.setdefault(key, dict(fixed=fixed, points={}))
        group['points'].setdefault(value, []).append(row)
    output = []
    for key in sorted(grouped):
        group = grouped[key]
        points = []
        for value, samples in sorted(group['points'].items()):
            values = [r['f_double_prime'] for r in samples]
            points.append(dict(value=value, row_ids=[r['row_id'] for r in samples],
                               trial_ids=[r['trial_id'] for r in samples],
                               f_double_prime_min_e=min(values), f_double_prime_max_e=max(values)))
        tested = len(points) >= 2
        spread = (max(p['f_double_prime_max_e'] for p in points)
                  - min(p['f_double_prime_min_e'] for p in points)) if tested else None
        output.append(dict(axis=axis, **group['fixed'], status='COMPARED' if tested else 'NOT_TESTED',
                           distinct_values=len(points), endpoints=points, f_double_prime_range_e=spread))
    return output


def _report(loaded):
    rows = []
    trials = []
    for trial in loaded:
        trials.append(dict(trial_id=trial['trial_id'], manifest=trial['ref']))
        for site in trial['result']['sites']:
            reference = site['reference_f_double_prime']
            relative = (site['f_double_prime'] - reference) / reference if reference > 0 else None
            rows.append(dict(site, row_id=digest(dict(trial_id=trial['trial_id'], node_id=site['node_id'])),
                             trial_id=trial['trial_id'], trial_manifest=trial['ref'],
                             occupancy_vector=trial['occupancy_vector'], settings=trial['settings'],
                             wavelength_A=trial['result']['wavelength_A'],
                             reference_deviation_fraction=relative,
                             normalization_status='DEFINED' if relative is not None else 'ZERO_REFERENCE',
                             r_work=trial['result']['r_work'], r_free=trial['result']['r_free']))
    return dict(kind='metal-fdp-comparison-report', schema_version=1, protocol=PROTOCOL,
                status='COMPARISON_REVIEW', comparison_basis=loaded[0]['basis'], trials=trials, rows=rows,
                sensitivity={axis: _sensitivity(rows, axis) for axis in (*SETTING_AXES, 'occupancy')},
                convergence='NOT_ESTABLISHED_BY_ENDPOINT_COMPARISON', scientific_acceptance='NOT_ASSESSED',
                automatic_checkpoint_selection=False,
                note='Descriptive endpoint ranges, not uncertainty estimates, convergence proof or a solution ranking; '
                     'occupancy response holds every other placed-metal occupancy and all fit settings fixed')


def _allocate(run):
    root = run / 'Metal'
    if root.is_symlink():
        raise RecipeError('Metal root must not be a symlink')
    numbers = [int(m.group(1)) for p in root.iterdir()
               if (m := re.fullmatch(r'fdp_comparison_(\d{3,})', p.name))]
    index = max(numbers, default=0) + 1
    while True:
        directory = root / f'fdp_comparison_{index:03d}'
        try:
            directory.mkdir()
            return directory
        except FileExistsError:
            index += 1


def _manifest(run, directory, loaded):
    doc = dict(kind='metal-fdp-comparison', schema_version=1, protocol=PROTOCOL,
               status='COMPARISON_REVIEW', inputs=[t['ref'] for t in loaded],
               files={'report': _reference(directory / 'report.json', run)},
               automatic_checkpoint_selection=False, scientific_acceptance='NOT_ASSESSED')
    doc['comparison_id'] = digest(doc)
    return doc


def build_comparison(run, trials):
    """Publish one immutable comparison of existing trials; never run Phenix."""
    run = Path(run).expanduser().resolve()
    loaded = _load_trials(run, trials)
    report = _report(loaded)
    directory = _allocate(run)
    try:
        (directory / 'report.json').write_bytes(_json_bytes(report))
        # Revalidate inputs before publication; no moving parent may be absorbed.
        repeated = _load_trials(run, [Path(t['ref']['relative_path']).parent for t in loaded])
        if canonical(repeated) != canonical(loaded):
            raise RecipeError('Trial changed while publishing comparison')
        doc = _manifest(run, directory, loaded)
        (directory / 'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory / 'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED', exception=type(exc).__name__, error=str(exc))))
        raise


def verify_comparison(run, directory):
    """Rebuild a saved comparison from verified trial evidence after relocation."""
    run = Path(run).expanduser().resolve()
    directory = Path(directory).expanduser()
    if not directory.is_absolute():
        directory = run / directory
    if directory.is_symlink() or directory.parent.is_symlink():
        raise RecipeError('Comparison must not be a symlink')
    directory = directory.resolve()
    if directory.parent != run / 'Metal' or not re.fullmatch(r'fdp_comparison_\d{3,}', directory.name):
        raise RecipeError('Require an explicit numbered fdp comparison within this run')
    try:
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Comparison payload must contain regular files only')
        if {p.name for p in directory.iterdir()} != {'manifest.json', 'report.json'}:
            raise RecipeError('Failed or unexpected comparison inventory')
        doc = _json((directory / 'manifest.json').read_bytes())
        if (doc.get('kind') != 'metal-fdp-comparison' or type(doc.get('schema_version')) is not int
                or doc['schema_version'] != 1 or doc.get('protocol') != PROTOCOL):
            raise RecipeError('Unsupported comparison manifest')
        refs = doc['inputs']
        if not isinstance(refs, list) or not 2 <= len(refs) <= MAX_TRIALS:
            raise RecipeError('Invalid comparison input count')
        for ref in refs:
            if ref.get('anchor') != 'run' or Path(ref['relative_path']).name != 'manifest.json':
                raise RecipeError('Comparison requires run-anchored trial manifests')
            _source(ref, run)
        loaded = _load_trials(run, [Path(ref['relative_path']).parent for ref in refs])
        if canonical([t['ref'] for t in loaded]) != canonical(refs):
            raise RecipeError('Comparison trial references changed')
        if (directory / 'report.json').read_bytes() != _json_bytes(_report(loaded)):
            raise RecipeError('Comparison report differs from endpoint replay')
        if canonical(doc) != canonical(_manifest(run, directory, loaded)):
            raise RecipeError('Comparison manifest or review state changed')
        return doc
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot verify fdp comparison: ' + str(exc)) from exc
