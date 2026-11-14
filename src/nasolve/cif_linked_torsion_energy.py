"""Fixed-coordinate attribution after an exact graph-qualified linked omission.

Native capture provenance remains the caller's responsibility. This pure reader
binds raw single-proxy evaluations to exact native indices and coordinates; it
does not authenticate execution, qualify derivatives, optimize or adopt a model.
"""
from collections import Counter
import json
import math

from .cif_candidate_usability import energy_inventory_checks, _close
from .cif_linked_linear_torsion import qualify_linked_linear_torsion_candidate, _exact

POLICY_ID = 'cif-linked-linear-torsion-energy-v1'
_MODULES = {'cctbx.geometry_restraints.'+n for n in ('flags', 'energies', 'manager')}


def _need(value, message):
    if not value:
        raise ValueError(message)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _vector_close(a, b):
    return len(a) == len(b) and math.dist(a, b) <= 1e-8 + 1e-10*max(1., math.hypot(*a), math.hypot(*b))


def _removed(before, after):
    rows = []
    for kind in ('dihedral', 'const_dihedral'):
        remaining = Counter(json.dumps(p, sort_keys=True, allow_nan=False)
                            for p in after['geometry']['proxy_details'][kind])
        for proxy in before['geometry']['proxy_details'][kind]:
            key = json.dumps(proxy, sort_keys=True, allow_nan=False)
            if remaining[key]:
                remaining[key] -= 1
            else:
                rows.append((kind, proxy))
        _need(not any(remaining.values()), 'Candidate added an unexplained torsion')
    return rows


def _snapshots(native):
    energy = native['energy_inventory']
    _need(set(energy) == {'policy_id', 'status', 'normalization', 'evaluation_calls', 'snapshots', 'installed_sources'}
          and type(energy['evaluation_calls']) is int and all(energy_inventory_checks(native).values()),
          'Require complete finite repeated native energy inventories')
    sources = energy['installed_sources']
    _need(len(sources) == 3 and {s['module'] for s in sources} == _MODULES
          and all(set(s) == {'module', 'sha256', 'historical_path'}
                  and isinstance(s['sha256'], str) and len(s['sha256']) == 64
                  and all(c in '0123456789abcdef' for c in s['sha256'])
                  and isinstance(s['historical_path'], str) and s['historical_path'] for s in sources),
          'Require exact native energy source identities')
    for row in energy['snapshots']:
        _need(set(row) == {'target', 'gradient', 'gradient_norm', 'terms', 'proxy_counts'},
              'Unsupported energy snapshot fields')
        _need('dihedral_residual_sum' in row['terms']
              and all(isinstance(k, str) and k.endswith('_residual_sum') and _finite(v) for k, v in row['terms'].items()),
              'Require complete finite residual terms')
        _need('n_dihedral_proxies' in row['proxy_counts']
              and all(isinstance(k, str) and k.startswith('n_') and k.endswith('_proxies')
                      and (v is None or type(v) is int and v >= 0) for k, v in row['proxy_counts'].items()),
              'Require supported native proxy counts')
    return energy['snapshots']


def qualify_linked_torsion_energy(before, after, source, component, candidate, references):
    """Attribute the entire native delta to the complete planned omission.

    Each ordered reference contains proxy_kind, the exact proxy, its four sites_cart,
    and two evaluations with single/accumulated target and 12 local gradients.
    Native source pins, full terms/counts, repetitions and scattered gradients are
    checked independently. A passing result is fixed-point attribution only.
    """
    inventory = qualify_linked_linear_torsion_candidate(before, after, source, component, candidate)
    _need(inventory['inventory_checks_pass'], 'Linked inventory must qualify before numerical attribution')
    try:
        left, right = _snapshots(before), _snapshots(after)
        _need(_exact(before['energy_inventory']['installed_sources'], after['energy_inventory']['installed_sources']),
              'Original and candidate native energy sources differ')
        points = before['geometry']['sites_cart_exact']
        count = before['atom_count']
        _need(type(count) is int and count > 0 and len(points) == count
              and all(len(p) == 3 and all(_finite(x) for x in p) for p in points), 'Invalid native coordinate inventory')
        removed = _removed(before, after)
        _need(len(references) == len(removed) and bool(removed), 'Require exactly the complete removed proxy references')
        gradient_terms = [[] for _ in range(3*count)]
        targets, reference_checks = [], []
        for ref, (kind, proxy) in zip(references, removed):
            ids = proxy['i_seqs']
            _need(len(ids) == 4 and len(set(ids)) == 4 and all(type(i) is int and 0 <= i < count for i in ids),
                  'Invalid removed native indices')
            _need(set(ref) == {'proxy_kind', 'proxy', 'sites_cart', 'evaluations'}
                  and ref['proxy_kind'] == kind and _exact(ref['proxy'], proxy)
                  and _exact(ref['sites_cart'], [points[i] for i in ids]), 'Removed reference identity or coordinates differ')
            evaluations = ref['evaluations']
            _need(len(evaluations) == 2, 'Require two removed-proxy evaluations')
            for row in evaluations:
                _need(set(row) == {'single_target', 'single_gradient', 'accumulated_target', 'accumulated_gradient'}
                      and all(_finite(row[k]) and row[k] >= 0 for k in ('single_target', 'accumulated_target'))
                      and all(len(row[k]) == 12 and all(_finite(x) for x in row[k])
                              for k in ('single_gradient', 'accumulated_gradient')), 'Invalid removed numerical reference')
                reference_checks.append(_close(row['single_target'], row['accumulated_target'])
                                        and _vector_close(row['single_gradient'], row['accumulated_gradient']))
            a, b = evaluations
            reference_checks.append(_close(a['single_target'], b['single_target'])
                                    and _vector_close(a['single_gradient'], b['single_gradient']))
            targets.append(a['single_target'])
            for local, index in enumerate(ids):
                for axis in range(3):
                    gradient_terms[3*index+axis].append(a['single_gradient'][3*local+axis])
        removed_target = math.fsum(targets)
        removed_gradient = [math.fsum(v) for v in gradient_terms]
        checks = {'removed_reference_repeats_and_container': all(reference_checks)}
        for label, snapshots in [('original', left), ('candidate', right)]:
            a, b = snapshots
            checks[label+'_term_repeats'] = a['terms'].keys() == b['terms'].keys() and all(_close(v, b['terms'][k]) for k, v in a['terms'].items())
            checks[label+'_count_repeats'] = _exact(a['proxy_counts'], b['proxy_counts'])
            checks[label+'_term_sum'] = all(_close(s['target'], math.fsum(s['terms'].values())) for s in snapshots)
        a, b = left[0], right[0]
        checks['unaffected_terms'] = a['terms'].keys() == b['terms'].keys() and all(
            _close(v, b['terms'][k]) for k, v in a['terms'].items() if k != 'dihedral_residual_sum')
        expected_counts = dict(a['proxy_counts'])
        _need(type(expected_counts['n_dihedral_proxies']) is int, 'Missing native dihedral count')
        expected_counts['n_dihedral_proxies'] -= len(removed)
        checks['only_planned_proxy_count_change'] = _exact(expected_counts, b['proxy_counts'])
        checks['dihedral_delta_matches_removed'] = _close(a['terms']['dihedral_residual_sum']-b['terms']['dihedral_residual_sum'], removed_target)
        checks['total_delta_matches_removed'] = _close(a['target']-b['target'], removed_target)
        delta = [x-y for x, y in zip(a['gradient'], b['gradient'])]
        checks['full_gradient_delta_matches_removed'] = _vector_close(delta, removed_gradient)
        return dict(schema_version=1, policy_id=POLICY_ID, status='REVIEW', component=component,
                    inventory_checks_pass=True, checks=checks, numerical_checks_pass=all(checks.values()),
                    removed_proxy_count=len(removed), removed_target=removed_target, target_delta=a['target']-b['target'],
                    gradient_delta_error_norm=math.dist(delta, removed_gradient),
                    tolerance={'absolute':1e-8, 'relative':1e-10},
                    derivative_qualification='NOT_RUN', scientific_approval='NOT_RUN',
                    model_editing='NOT_RUN', optimization='NOT_RUN', automatic_adoption=False,
                    scope='FIXED_COORDINATE_ATTRIBUTION_ONLY; CALLER_AUTHENTICATES_NATIVE_CAPTURE')
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Incomplete or unsupported linked energy evidence') from exc
