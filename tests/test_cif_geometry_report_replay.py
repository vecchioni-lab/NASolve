"""Roundoff compatibility cannot change captured chemistry or classifications."""
from copy import deepcopy
import json
import math

import pytest

from nasolve.cif_captured_geometry import review_captured_geometry
from nasolve.cif_geometry_report_replay import compare_geometry_reports
from tests.test_cif_captured_geometry import native


def report_pair():
    rebuilt = review_captured_geometry(native())
    return json.loads(json.dumps(rebuilt)), rebuilt


def rerank(report, kind):
    report['summary'][kind]['worst'] = sorted(
        (deepcopy(r) for r in report['measurements'][kind] if r['nominal_deviation'] is not None),
        key=lambda r: (-abs(r['nominal_deviation']), r['proxy_index']))[:10]


@pytest.mark.parametrize('kind', ['bond_simple', 'angle', 'chirality'])
@pytest.mark.parametrize('field', ['observed', 'difference', 'nominal_deviation'])
def test_platform_roundoff_in_derived_scalars_replays_without_altering_inputs(kind, field):
    saved, rebuilt = report_pair()
    row = saved['measurements'][kind][0]
    row[field] = math.nextafter(row[field], math.inf)
    rerank(saved, kind)
    before = deepcopy((saved, rebuilt))
    assert saved != rebuilt
    result = compare_geometry_reports(saved, rebuilt)
    assert result['consistent'] is True, result
    assert result['changed_derived_values'] == 1
    assert (saved, rebuilt) == before


@pytest.mark.parametrize('defect', ['target', 'weight', 'indices', 'origin', 'both_signs', 'sign',
    'status', 'unit', 'count', 'rank', 'duplicate', 'approval', 'bool', 'integer', 'nonfinite', 'large'])
def test_roundoff_policy_never_loosens_exact_metadata_or_material_geometry(defect):
    saved, rebuilt = report_pair()
    row = saved['measurements']['chirality'][0]
    if defect in {'target', 'weight'}:row[defect] = math.nextafter(row[defect], math.inf)
    elif defect == 'indices':row['i_seqs'] = row['i_seqs'][::-1]
    elif defect == 'origin':row['origin_id'] = 1
    elif defect == 'both_signs':row['both_signs'] = True
    elif defect == 'sign':row['sign_agreement'] = False
    elif defect == 'status':row['status'] = 'DEGENERATE'
    elif defect == 'unit':row['unit'] = 'degree'
    elif defect == 'count':saved['summary']['chirality']['nominal_abs_ge_5'] += 1
    elif defect == 'rank':saved['summary']['chirality']['worst'] = []
    elif defect == 'duplicate':saved['summary']['chirality']['worst'][0]['observed'] += 1e-14
    elif defect == 'approval':saved['scientific_approval'] = 'PASS'
    elif defect == 'bool':row['observed'] = True
    elif defect == 'integer':row['observed'] = 1
    elif defect == 'nonfinite':row['observed'] = math.nan
    else:row['observed'] += 1e-8
    if defect not in {'rank', 'duplicate'}:rerank(saved, 'chirality')
    assert compare_geometry_reports(saved, rebuilt)['consistent'] is False


def test_identical_reports_and_unavailable_measurements_stay_explicit():
    n = native();n['geometry']['proxy_details']['bond_simple'][0]['weight'] = 0.
    report = review_captured_geometry(n)
    result = compare_geometry_reports(report, deepcopy(report))
    assert result['consistent'] and result['changed_derived_values'] == 0
    assert report['measurements']['bond_simple'][0]['nominal_deviation'] is None


def test_propagated_bound_handles_small_deviation_from_large_observed_angle():
    n = native();n['geometry']['proxy_details']['angle'][0]['angle_ideal'] = 90.-1e-12
    rebuilt = review_captured_geometry(n);saved = deepcopy(rebuilt)
    row = saved['measurements']['angle'][0]
    row['observed'] = math.nextafter(row['observed'], math.inf)
    row['difference'] = row['observed'] - row['target']
    row['nominal_deviation'] = row['difference'] * math.sqrt(row['weight'])
    rerank(saved, 'angle')
    assert compare_geometry_reports(saved, rebuilt)['consistent']


@pytest.mark.parametrize('defect', ['missing', 'extra', 'bad_schema', 'unknown_kind'])
def test_incomplete_or_unknown_scope_is_not_treated_as_roundoff(defect):
    saved, rebuilt = report_pair()
    if defect == 'missing':del saved['measurements']['angle'][0]['observed']
    elif defect == 'extra':saved['measurements']['angle'][0]['new_float'] = 0.
    elif defect == 'bad_schema':saved['schema_version'] = True
    else:saved['measurements']['unknown'] = []
    assert not compare_geometry_reports(saved, rebuilt)['consistent']


def test_near_zero_ordered_volume_sign_cannot_change_inside_a_roundoff_bound():
    n = native();n['geometry']['sites_cart_exact'][3][2] = 1e-15
    n['atoms'][3]['xyz'][2] = 1e-15
    rebuilt = review_captured_geometry(n);saved = deepcopy(rebuilt)
    saved['measurements']['chirality'][0]['observed'] *= -1
    rerank(saved, 'chirality')
    assert not compare_geometry_reports(saved, rebuilt)['consistent']


def test_threshold_class_cannot_change_even_if_saved_counts_are_left_unchanged():
    n = native();n['geometry']['proxy_details']['chirality'][0].update(volume_ideal=0., weight=9.)
    rebuilt = review_captured_geometry(n);saved = deepcopy(rebuilt)
    saved['measurements']['chirality'][0]['nominal_deviation'] = math.nextafter(3., 0.)
    rerank(saved, 'chirality')
    assert not compare_geometry_reports(saved, rebuilt)['consistent']
