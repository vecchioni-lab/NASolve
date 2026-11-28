"""Observe one complete objective without switching native restraint families.

The caller owns native inputs, process identity and restoration of native state.
This module owns only bounded directional arithmetic and its read-only replay;
metadata is retained verbatim, never used to rescale scores or repair forces.
"""
from copy import deepcopy
import json
import math

from .cif_gradient_audit import STEPS, FD_ABSOLUTE, FD_RELATIVE, _close, _norm, _unit

POLICY_ID = 'cif-whole-objective-probe-v1'
MAX_METADATA_BYTES = 16384
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, model_optimization='NOT_RUN',
              scientific_approval='NOT_RUN', automatic_adoption=False)


def _need(value, message='Invalid whole-objective probe evidence'):
    if not value:
        raise ValueError(message)


def _number(value):
    _need(type(value) in (int, float) and math.isfinite(value))
    return float(value)


def _request(points, selected, budget):
    _need(isinstance(points, list) and bool(points))
    for point in points:
        _need(isinstance(point, list) and len(point) == 3)
        for value in point:
            _number(value)
    _need(isinstance(selected, (list, tuple)) and 1 <= len(selected) <= 6)
    _need(all(type(i) is int and 0 <= i < len(points) for i in selected)
          and len(set(selected)) == len(selected))
    _need(type(budget) is int and 1 <= budget <= 512, 'Invalid objective probe budget')


def _metadata(value):
    _need(isinstance(value, dict))
    try:
        encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))
        _need(len(encoded.encode()) <= MAX_METADATA_BYTES)
        _need(json.loads(encoded) == value)
    except (TypeError, OverflowError) as exc:
        raise ValueError('Invalid objective metadata') from exc
    return deepcopy(value)


def _observation(value, count, *, gradient):
    _need(isinstance(value, dict))
    keys = {'target', 'metadata'} | ({'gradient'} if gradient else set())
    _need(set(value) == keys)
    result = dict(target=_number(value['target']), metadata=_metadata(value['metadata']))
    if gradient:
        _need(isinstance(value['gradient'], list) and len(value['gradient']) == 3*count)
        result['gradient'] = [_number(v) for v in value['gradient']]
        _need(math.isfinite(_norm(result['gradient'])))
    return result


def _directions(gradient, selected):
    rows = []
    if (direction := _unit(gradient)) is not None:
        rows.append(('full_gradient', direction))
    rows.append(('alternating_global', _unit([1. if i % 2 else -1. for i in range(len(gradient))])))
    for index in selected:
        for axis in range(3):
            direction = [0.]*len(gradient)
            direction[3*index+axis] = 1.
            rows.append((f'atom_{index}_axis_{axis}', direction))
    return rows


def probe_objective(evaluate, points, selected_indices, *, max_calls=256):
    """Sample a single ``evaluate(points)`` callback at four fixed step sizes.

    No flags, normalization or restraint parameters are passed or changed here.
    A final baseline evaluation restores the requested coordinate argument on
    success; restoring external native state after failure remains the caller's
    responsibility. Numerical agreement is neither source nor chemistry approval.
    """
    _request(points, selected_indices, max_calls)
    points = deepcopy(points)
    calls = 0
    def call(p):
        nonlocal calls
        _need(calls < max_calls, 'Objective probe budget exhausted')
        calls += 1
        raw = evaluate(deepcopy(p))
        _need(isinstance(raw, dict) and set(raw) <= {'target', 'gradient', 'metadata'})
        return _observation(dict(raw, metadata=raw.get('metadata', {})), len(points), gradient=True)
    baseline = call(points)
    directions = _directions(baseline['gradient'], selected_indices)
    _need(2+8*len(directions) <= max_calls, 'Objective probe budget exhausted')
    rows = []
    for name, direction in directions:
        samples = []
        for step in STEPS:
            sample = {'step': step}
            for label, sign in [('plus', 1), ('minus', -1)]:
                shifted = [[x+sign*step*direction[3*i+j] for j, x in enumerate(p)] for i, p in enumerate(points)]
                value = call(shifted)
                sample[label] = {k: value[k] for k in ('target', 'metadata')}
            samples.append(sample)
        rows.append(dict(name=name, samples=samples))
    repeat = call(points)
    result = dict(_FIXED, points=points, selected_indices=list(selected_indices),
                  max_calls=max_calls, evaluation_calls=calls, baseline=baseline,
                  directions=rows, repeat=repeat)
    review_objective_probe(result)
    return result


def review_objective_probe(record):
    """Recompute saved arithmetic without native execution or file writes.

    This does not authenticate a producer or frozen input bundle. Native ownership,
    input hashes, fixed restraint identities and installed versions stay with the
    calling evidence owner. A changing metadata record is reported separately from
    derivative agreement; unchanged metadata is only what the caller observed.
    """
    _need(isinstance(record, dict) and set(record) == set(_FIXED) | {
        'points', 'selected_indices', 'max_calls', 'evaluation_calls', 'baseline', 'directions', 'repeat'})
    _need(all(type(record[k]) is type(v) and record[k] == v for k, v in _FIXED.items()))
    points, selected = record['points'], record['selected_indices']
    _request(points, selected, record['max_calls'])
    baseline = _observation(record['baseline'], len(points), gradient=True)
    repeat = _observation(record['repeat'], len(points), gradient=True)
    directions = _directions(baseline['gradient'], selected)
    _need(type(record['evaluation_calls']) is int and record['evaluation_calls'] == 2+8*len(directions)
          and record['evaluation_calls'] <= record['max_calls'])
    _need(isinstance(record['directions'], list) and len(record['directions']) == len(directions))
    metadata = [baseline['metadata'], repeat['metadata']]
    rows = []
    for saved, (name, direction) in zip(record['directions'], directions):
        _need(isinstance(saved, dict) and set(saved) == {'name', 'samples'} and saved['name'] == name)
        _need(isinstance(saved['samples'], list) and len(saved['samples']) == len(STEPS))
        analytical = math.fsum(g*d for g, d in zip(baseline['gradient'], direction))
        samples = []
        for saved_sample, step in zip(saved['samples'], STEPS):
            _need(isinstance(saved_sample, dict) and set(saved_sample) == {'step', 'plus', 'minus'})
            _need(type(saved_sample['step']) is float and saved_sample['step'] == step)
            plus = _observation(saved_sample['plus'], len(points), gradient=False)
            minus = _observation(saved_sample['minus'], len(points), gradient=False)
            metadata.extend([plus['metadata'], minus['metadata']])
            numerical = (plus['target']-minus['target'])/(2*step)
            error = abs(numerical-analytical)
            bound = FD_ABSOLUTE+FD_RELATIVE*max(abs(numerical), abs(analytical))
            _need(all(math.isfinite(v) for v in (analytical, numerical, error, bound)))
            samples.append(dict(step=step, numerical=numerical, absolute_error=error,
                                bound=bound, consistent=error <= bound))
        consistent = any(samples[i]['consistent'] and samples[i+1]['consistent'] for i in range(len(STEPS)-1))
        rows.append(dict(name=name, analytical=analytical, samples=samples, consistent=consistent))
    repeated = _close(baseline['target'], repeat['target']) and all(
        _close(a, b) for a, b in zip(baseline['gradient'], repeat['gradient']))
    context = ('NOT_RECORDED' if not any(metadata) else
               'UNCHANGED' if all(m == metadata[0] for m in metadata) else 'CHANGED')
    return dict(policy_id=POLICY_ID, directions=rows, baseline_repeat_consistent=repeated,
                sampled_gradients_consistent=repeated and all(row['consistent'] for row in rows),
                context_observation=context, evaluation_calls=record['evaluation_calls'],
                scientific_approval='NOT_RUN', automatic_adoption=False)
