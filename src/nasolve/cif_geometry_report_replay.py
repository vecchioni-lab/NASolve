"""Compare derived Cartesian reports while keeping captured chemistry exact.

This is a saved-report compatibility rule, never a restraint, derivative,
optimization or scientific-geometry acceptance tolerance.
"""
from __future__ import annotations

import math

POLICY_ID = 'cif-derived-cartesian-report-replay-v1'
ROUNDING_ULPS = 64
DERIVED_FIELDS = ('observed', 'difference', 'nominal_deviation')
KINDS = ('bond_simple', 'angle', 'chirality')


def _exact(a, b):
    """Preserve JSON types, finite raw numbers and signed zero."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_exact(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(_exact(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return math.isfinite(a) and math.isfinite(b) and a.hex() == b.hex()
    return a == b


def _derived_close(a, b, bound):
    return abs(a-b) <= bound


def compare_geometry_reports(saved, rebuilt):
    """Allow bounded roundoff only in three named calculated scalar fields.

    The observed-value allowance is 64 ULPs at its rebuilt magnitude (minimum
    scale one in that row's unit). Subtraction and square-root weighting carry
    this allowance into difference and nominal deviation. Identity, targets,
    weights, signs, states, ranks, counts and report scope remain exact.
    """
    issues = []
    changed = 0
    maximum_error = 0.
    maximum_bound = 0.

    def need(value, path, reason):
        if not value:
            issues.append({'path': path, 'reason': reason})
        return value

    def metadata(a, b, exclude, path):
        return need(isinstance(a, dict) and isinstance(b, dict)
                    and _exact({k: v for k, v in a.items() if k not in exclude},
                               {k: v for k, v in b.items() if k not in exclude}),
                    path, 'EXACT_METADATA_DIFFERS')

    try:
        if not need(isinstance(rebuilt, dict) and rebuilt.get('schema_version') == 1
                    and rebuilt.get('policy_id') == 'cif-captured-cartesian-geometry-v1'
                    and set(rebuilt['measurements']) == set(rebuilt['summary']) == set(KINDS),
                    '/', 'UNSUPPORTED_REBUILT_REPORT'):
            raise ValueError('Unsupported rebuilt Cartesian report')
        metadata(saved, rebuilt, {'measurements', 'summary'}, '/')
        need(set(saved['measurements']) == set(saved['summary']) == set(KINDS), '/', 'MEASUREMENT_SCOPE_DIFFERS')
        for kind in KINDS:
            arows, brows = saved['measurements'][kind], rebuilt['measurements'][kind]
            path = '/measurements/' + kind
            if not need(type(arows) is list and type(brows) is list and len(arows) == len(brows), path, 'ROW_COUNT_DIFFERS'):
                continue
            for index, (a, b) in enumerate(zip(arows, brows)):
                rowpath = path + '/' + str(index)
                if not metadata(a, b, set(DERIVED_FIELDS), rowpath):
                    continue
                observed = b['observed']
                if observed is None:
                    need(_exact(a, b), rowpath, 'UNAVAILABLE_MEASUREMENT_DIFFERS')
                    continue
                if not need(type(observed) is float and math.isfinite(observed), rowpath, 'INVALID_REBUILT_SCALAR'):
                    continue
                observed_bound = ROUNDING_ULPS * math.ulp(max(1., abs(observed)))
                target = b['target']
                scale = max(1., abs(observed), abs(target) if type(target) in (int, float) and math.isfinite(target) else 0.)
                difference_bound = observed_bound + ROUNDING_ULPS * math.ulp(scale)
                bounds = {'observed': observed_bound, 'difference': difference_bound}
                if b['nominal_deviation'] is not None:
                    weight = b['weight']
                    if not need(type(weight) in (int, float) and not isinstance(weight, bool)
                                and math.isfinite(weight) and weight > 0, rowpath, 'INVALID_REBUILT_WEIGHT'):
                        continue
                    bounds['nominal_deviation'] = (difference_bound * math.sqrt(weight)
                        + ROUNDING_ULPS * math.ulp(max(1., abs(b['nominal_deviation']))))
                for field in DERIVED_FIELDS:
                    x, y = a[field], b[field]
                    if y is None:
                        need(_exact(x, y), rowpath + '/' + field, 'UNAVAILABLE_MEASUREMENT_DIFFERS')
                        continue
                    bound = bounds[field]
                    if not need(type(x) is type(y) is float and math.isfinite(x) and math.isfinite(y)
                                and math.isfinite(bound) and _derived_close(x, y, bound),
                                rowpath + '/' + field, 'DERIVED_SCALAR_OUTSIDE_ROUNDOFF_BOUND'):
                        continue
                    if field == 'observed' and kind == 'chirality':
                        need((x == 0.) == (y == 0.) and math.copysign(1., x) == math.copysign(1., y),
                             rowpath + '/' + field, 'ORDERED_VOLUME_SIGN_OR_DEGENERACY_DIFFERS')
                    if field == 'nominal_deviation':
                        need(all((abs(x) >= threshold) == (abs(y) >= threshold) for threshold in (3., 5.)),
                             rowpath + '/' + field, 'DESCRIPTIVE_THRESHOLD_CLASS_DIFFERS')
                    changed += not _exact(x, y)
                    maximum_error = max(maximum_error, abs(x-y))
                    maximum_bound = max(maximum_bound, bound)
            a, b = saved['summary'][kind], rebuilt['summary'][kind]
            metadata(a, b, {'worst'}, '/summary/' + kind)
            # Ranked rows must point to the same identities and be exact copies
            # of their own report's measurements, including calculated fields.
            aworst, bworst = a['worst'], b['worst']
            if need(type(aworst) is list and len(aworst) == len(bworst), '/summary/' + kind, 'RANKED_SCOPE_DIFFERS'):
                for index, (x, y) in enumerate(zip(aworst, bworst)):
                    rowpath = '/summary/' + kind + '/worst/' + str(index)
                    i = y['proxy_index']
                    need(type(x['proxy_index']) is type(i) is int and x['proxy_index'] == i
                         and 0 <= i < len(brows) and _exact(x, arows[i]) and _exact(y, brows[i]),
                         rowpath, 'RANKED_IDENTITY_OR_DUPLICATE_ROW_DIFFERS')
    except (KeyError, TypeError, IndexError, ValueError, OverflowError) as exc:
        issues.append({'path': '/', 'reason': 'INCOMPLETE_OR_INVALID_REPORT', 'error_type': type(exc).__name__})
    return {'schema_version': 1, 'policy_id': POLICY_ID,
            'status': 'DERIVED_REPORT_REPLAY_PASS' if not issues else 'REVIEW',
            'consistent': not issues, 'rounding_ulps': ROUNDING_ULPS,
            'derived_fields': list(DERIVED_FIELDS), 'changed_derived_values': changed,
            'maximum_absolute_difference': maximum_error, 'maximum_allowed_difference': maximum_bound,
            'issue_count': len(issues), 'issues': issues[:25],
            'scientific_qualification': 'NOT_ASSESSED', 'mechanics_changes': 'NONE'}
