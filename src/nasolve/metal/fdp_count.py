"""Offline, explicit-scope anomalous atom-equivalent accounting.

Sums of Q*f-double-prime are coefficient bookkeeping, not structure factors:
positions, phases, B attenuation, mixed identities and correlations still matter.
No integer count, new site placement or scientific acceptance is inferred.
"""
import math
from pathlib import Path

from .context import _reference
from .fdp import verify_fdp
from .fdp_scan import _allocate, _directory
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest, number

PROTOCOL = 'metal-fdp-count-v1'


def _sum(values):
    return number(math.fsum(values), 'finite count-evidence sum')


def _ratio(a, b):
    return number(a/b, 'finite count-evidence ratio') if b > 0 else None


def summarize_count(result, groups):
    """Pure accounting over explicitly named fitted nodes; no implicit neighbors."""
    if result.get('freeze_audit') != 'PASS':
        raise RecipeError('Count evidence requires a passed frozen-state audit')
    wavelength = number(result['wavelength_A'], 'wavelength')
    if wavelength <= 0: raise RecipeError('Count evidence requires positive wavelength')
    if not isinstance(groups, dict) or not 1 <= len(groups) <= 128:
        raise RecipeError('Require 1 to 128 explicitly named count groups')
    sites = {s['node_id']: s for s in result['sites']}
    if len(sites) != len(result['sites']): raise RecipeError('Duplicate fitted site')
    rows = []; included = set()
    for name, request in sorted(groups.items()):
        if not isinstance(name,str) or not name.strip() or len(name)>128:
            raise RecipeError('Require a short nonempty group name')
        if not isinstance(request,dict) or set(request) != {'nodes','representation'}:
            raise RecipeError('Count group requires nodes and representation')
        nodes = request['nodes']; representation = request['representation']
        if (not isinstance(nodes,list) or not nodes or any(not isinstance(n,str) for n in nodes)
                or len(set(nodes)) != len(nodes) or set(nodes)-sites.keys()):
            raise RecipeError('Count group must name distinct fitted nodes; no missing or background sites')
        if representation not in {'explicit-sites','unresolved-proxy'}:
            raise RecipeError('Unknown count representation')
        if representation == 'unresolved-proxy' and len(nodes) != 1:
            raise RecipeError('An unresolved proxy requires one explicitly fitted site')
        selected = [sites[n] for n in sorted(nodes)]; by_element = {}; warnings = set()
        for site in selected:
            q = number(site['occupancy'], 'Q'); b = number(site['b_iso'], 'B')
            f = number(site['f_double_prime'], 'fitted fdp')
            ref = number(site['reference_f_double_prime'], 'reference fdp')
            if not 0 < q <= 1 or b < 0 or ref < 0: raise RecipeError('Invalid fitted site state')
            if f < 0: warnings.add('NEGATIVE_FDP')
            if ref == 0: warnings.add('ZERO_REFERENCE_FDP')
            symbol = site['element']
            if not isinstance(symbol,str) or not symbol: raise RecipeError('Missing element identity')
            by_element.setdefault(symbol,[]).append(site)
        elements = []
        for symbol, members in sorted(by_element.items()):
            refs = {s['reference_f_double_prime'] for s in members}
            if len(refs) != 1: raise RecipeError('Same-element sites must share the wavelength reference')
            ref = next(iter(refs))
            qsum = _sum(s['occupancy'] for s in members)
            fitted = _sum(s['occupancy']*s['f_double_prime'] for s in members)
            expected = _sum(s['occupancy']*ref for s in members)
            elements.append(dict(element=symbol,node_ids=[s['node_id'] for s in members],
                modeled_site_count=len(members),occupancy_sum=qsum,reference_f_double_prime=ref,
                q_weighted_fdp_e=fitted,q_weighted_reference_e=expected,
                response_ratio=_ratio(fitted,expected),effective_atom_equivalents=_ratio(fitted,ref)))
        fitted = _sum(e['q_weighted_fdp_e'] for e in elements)
        expected = _sum(e['q_weighted_reference_e'] for e in elements)
        rows.append(dict(group_id=name,representation=representation,node_ids=sorted(nodes),
            modeled_site_count=len(nodes),sites=selected,elements=elements,
            q_weighted_fdp_e=fitted,q_weighted_reference_e=expected,response_ratio=_ratio(fitted,expected),
            integer_count_estimate=None,warnings=sorted(warnings)))
        included.update(nodes)
    return dict(kind='metal-fdp-count-report',schema_version=1,protocol=PROTOCOL,
        wavelength_A=wavelength,groups=rows,excluded_fitted_nodes=sorted(sites.keys()-included),
        overlap_policy='groups_may_overlap_never_sum_groups',
        background_policy='only_explicit_fitted_nodes_included_background_scatterers_excluded',
        interpretation='Q-weighted coefficient and per-element atom-equivalent diagnostics; not an observed structure-factor sum or integer atom count',
        convergence=result.get('convergence','NOT_ASSESSED'),
        scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False)


def _derive(run, trial, groups):
    doc = verify_fdp(run,trial)
    directory = run/Path(doc['files']['result.json']['relative_path']).parent
    ref = _reference(directory/'manifest.json',run)
    if canonical(_json(_source(ref,run))) != canonical(doc): raise RecipeError('Source trial changed')
    report = summarize_count(_json(_source(doc['files']['result.json'],run)),groups)
    plan = _json(_source(doc['files']['plan.json'],run))
    report.update(source_trial_id=doc['trial_id'],source_parent=doc['parent'],
                  phase_policy=plan['phase_policy'],b_calibration=plan.get('b_calibration'),
                  references=plan['references'])
    return ref,report


def _manifest(run, directory, ref, groups):
    doc = dict(kind='metal-fdp-count',schema_version=1,protocol=PROTOCOL,
        source=ref,groups=groups,files={'report':_reference(directory/'report.json',run)},
        scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False)
    doc['report_id'] = digest(doc)
    return doc


def capture_count(run, trial, groups):
    """Save a new immutable report without another fit or checkpoint mutation."""
    run=Path(run).expanduser().resolve()
    groups=_json(_json_bytes(groups))
    ref,report=_derive(run,trial,groups)
    directory=_allocate(run,'fdp_count')
    try:
        (directory/'report.json').write_bytes(_json_bytes(report))
        _source(ref,run)
        doc=_manifest(run,directory,ref,groups)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        (directory/'failure.json').write_bytes(_json_bytes(dict(status='FAILED',error=str(exc))))
        raise


def verify_count(run, directory):
    """Replay the original fit, endpoint lineage and count arithmetic offline."""
    run=Path(run).expanduser().resolve();directory=_directory(run,directory,'fdp_count')
    try:
        if ({p.name for p in directory.iterdir()} != {'manifest.json','report.json'}
                or any(p.is_symlink() or not p.is_file() for p in directory.iterdir())):
            raise RecipeError('Unexpected count-report inventory')
        doc=_json((directory/'manifest.json').read_bytes());source=doc['source'];_source(source,run)
        if source['anchor']!='run' or Path(source['relative_path']).name!='manifest.json':
            raise RecipeError('Require a run-anchored trial manifest')
        ref,report=_derive(run,Path(source['relative_path']).parent,doc['groups'])
        # Early schema-1 reports retain convergence through their source only.
        saved=_json(_source(doc['files']['report'],run))
        if 'convergence' not in saved: report.pop('convergence')
        if ((directory/'report.json').read_bytes()!=_json_bytes(report)
                or canonical(doc)!=canonical(_manifest(run,directory,ref,doc['groups']))):
            raise RecipeError('Count report differs from verified source replay')
        return doc
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot verify count report: '+str(exc)) from exc
