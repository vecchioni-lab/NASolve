"""Matched, signed cluster response profiles from existing frozen fdp evidence.

Q*f-double-prime sums describe coefficients, not observed structure factors.
No new native execution, integer atom count or scientific acceptance is inferred.
"""
from pathlib import Path

from .context import _reference
from .fdp_compare import MAX_TRIALS, SETTING_AXES, _load_trials
from .fdp_count import _sum, summarize_count
from .fdp_scan import _allocate, _directory
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest

PROTOCOL = 'metal-fdp-count-comparison-v1'
MAX_GROUPS = 32
PREFIX = 'fdp_count_comparison'


def response_diagnostics(group):
    """Retain signed contributions and the B range for a validated count group."""
    sites = group['sites']
    contributions = [s['occupancy'] * s['f_double_prime'] for s in sites]
    positive = _sum(max(v, 0.) for v in contributions)
    negative = _sum(min(v, 0.) for v in contributions)
    absolute = _sum(abs(v) for v in contributions)
    b = [s['b_iso'] for s in sites]
    warnings = set(group['warnings'])
    if positive > 0 and negative < 0:
        warnings.add('MIXED_SIGN_FDP')
    if min(b) != max(b):
        warnings.add('DIFFERENT_SITE_B')
    return dict(unweighted_fdp_e=_sum(s['f_double_prime'] for s in sites),
                positive_q_weighted_fdp_e=positive, negative_q_weighted_fdp_e=negative,
                absolute_q_weighted_fdp_e=absolute,
                cancellation_fraction=1-abs(_sum(contributions))/absolute if absolute else None,
                occupancy_sum=_sum(s['occupancy'] for s in sites),
                b_min_A2=min(b), b_max_A2=max(b), b_range_A2=max(b)-min(b),
                warnings=sorted(warnings))


def _profiles(snapshots):
    # Include every placed-metal occupancy in the matching key, even if excluded
    # from the declared sum. Varying a neighbor can change this group's response.
    axes = [dict(kind='occupancy', node_id=n) for n in snapshots[0]['occupancy_vector']]
    axes += [dict(kind='setting', name=n) for n in SETTING_AXES]
    output = []
    for axis in axes:
        matched = {}
        for snapshot in snapshots:
            q = dict(snapshot['occupancy_vector'])
            settings = dict(snapshot['settings'])
            value = q.pop(axis['node_id']) if axis['kind']=='occupancy' else settings.pop(axis['name'])
            for group in snapshot['groups']:
                fixed = dict(group_id=group['group_id'], fixed_occupancies=q, fixed_settings=settings)
                bucket = matched.setdefault(canonical(fixed), dict(fixed=fixed, values={}))
                bucket['values'].setdefault(value, []).append((snapshot['trial_id'], group))
        for key in sorted(matched):
            bucket = matched[key]
            points = []
            for value, samples in sorted(bucket['values'].items()):
                point = dict(value=value, trial_ids=[t for t, g in samples])
                for field in ('q_weighted_fdp_e', 'q_weighted_reference_e', 'response_ratio',
                              'cancellation_fraction'):
                    values = [g[field] for t, g in samples if g[field] is not None]
                    point[field+'_min'] = min(values) if values else None
                    point[field+'_max'] = max(values) if values else None
                points.append(point)
            tested = len(points) >= 2
            output.append(dict(axis=axis, **bucket['fixed'], points=points,
                               status='COMPARED' if tested else 'NOT_TESTED',
                               distinct_values=len(points)))
    return output


def _report(loaded, groups):
    if not isinstance(groups, dict) or not 1 <= len(groups) <= MAX_GROUPS:
        raise RecipeError(f'Require 1 to {MAX_GROUPS} explicit count-comparison groups')
    snapshots = []
    for trial in loaded:
        counted = summarize_count(trial['result'], groups)
        aggregates = []
        for group in counted['groups']:
            compact = {k: v for k, v in group.items() if k != 'sites'}
            compact.update(response_diagnostics(group))
            aggregates.append(compact)
        # Per-site B calibration belongs to the shared comparison basis. Avoid
        # duplicating its atom provenance in every aggregate and snapshot.
        sites = [{k: v for k, v in s.items() if k != 'b_calibration'} for s in trial['result']['sites']]
        snapshots.append(dict(trial_id=trial['trial_id'], manifest=trial['ref'],
            occupancy_vector=trial['occupancy_vector'], settings=trial['settings'],
            sites=sites, groups=aggregates, excluded_fitted_nodes=counted['excluded_fitted_nodes'],
            r_work=trial['result']['r_work'], r_free=trial['result']['r_free'],
            source_convergence=counted['convergence']))
    return dict(kind='metal-fdp-count-comparison-report', schema_version=1, protocol=PROTOCOL,
        status='COMPARISON_REVIEW', comparison_basis=loaded[0]['basis'],
        wavelength_A=loaded[0]['result']['wavelength_A'], snapshots=snapshots,
        profiles=_profiles(snapshots), overlap_policy='groups_may_overlap_never_sum_groups',
        background_policy='only_explicit_fitted_nodes_included_background_scatterers_excluded',
        interpretation='Signed Q-weighted coefficients and per-element atom equivalents, not observed '
            'structure-factor sums or integer atom counts; positions, B attenuation, phases and correlations '
            'still matter. Cancellation and different site B values require review. Endpoint ranges are '
            'descriptive, not uncertainties. Different geometries require separate comparisons.',
        convergence='NOT_ESTABLISHED_BY_ENDPOINT_COMPARISON', scientific_acceptance='NOT_ASSESSED',
        automatic_checkpoint_selection=False)


def _manifest(run, directory, loaded, groups):
    doc = dict(kind='metal-fdp-count-comparison', schema_version=1, protocol=PROTOCOL,
        status='COMPARISON_REVIEW', inputs=[t['ref'] for t in loaded], groups=groups,
        files={'report': _reference(directory/'report.json', run)},
        automatic_checkpoint_selection=False, scientific_acceptance='NOT_ASSESSED')
    doc['comparison_id'] = digest(doc)
    return doc


def build_count_comparison(run, trials, groups):
    """Save a new immutable comparison; validate before allocating any output."""
    run = Path(run).expanduser().resolve()
    groups = _json(_json_bytes(groups))
    loaded = _load_trials(run, trials)
    report = _report(loaded, groups)
    directory = _allocate(run, PREFIX)
    try:
        (directory/'report.json').write_bytes(_json_bytes(report))
        repeated = _load_trials(run, [Path(t['ref']['relative_path']).parent for t in loaded])
        if canonical(repeated) != canonical(loaded):
            raise RecipeError('Trial changed while publishing count comparison')
        doc = _manifest(run, directory, loaded, groups)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED', exception=type(exc).__name__, error=str(exc))))
        raise


def verify_count_comparison(run, directory):
    """Replay the complete source audit and comparison arithmetic offline."""
    run = Path(run).expanduser().resolve()
    directory = _directory(run, directory, PREFIX)
    try:
        if ({p.name for p in directory.iterdir()} != {'manifest.json', 'report.json'}
                or any(p.is_symlink() or not p.is_file() for p in directory.iterdir())):
            raise RecipeError('Failed or unexpected count-comparison inventory')
        doc = _json((directory/'manifest.json').read_bytes())
        if (doc.get('kind') != 'metal-fdp-count-comparison' or type(doc.get('schema_version')) is not int
                or doc['schema_version'] != 1 or doc.get('protocol') != PROTOCOL):
            raise RecipeError('Unsupported count-comparison manifest')
        refs = doc['inputs']
        if not isinstance(refs, list) or not 2 <= len(refs) <= MAX_TRIALS:
            raise RecipeError('Invalid count-comparison input count')
        for ref in refs:
            if ref.get('anchor') != 'run' or Path(ref['relative_path']).name != 'manifest.json':
                raise RecipeError('Require run-anchored trial manifests')
            _source(ref, run)
        loaded = _load_trials(run, [Path(ref['relative_path']).parent for ref in refs])
        if canonical([t['ref'] for t in loaded]) != canonical(refs):
            raise RecipeError('Count-comparison trial references changed')
        if (directory/'report.json').read_bytes() != _json_bytes(_report(loaded, doc['groups'])):
            raise RecipeError('Count-comparison report differs from source replay')
        if canonical(doc) != canonical(_manifest(run, directory, loaded, doc['groups'])):
            raise RecipeError('Count-comparison manifest or review state changed')
        return doc
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot verify fdp count comparison: '+str(exc)) from exc
