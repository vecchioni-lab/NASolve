"""Physical pair measurements must not depend on their force provider."""
from copy import deepcopy
import math

import pytest

from nasolve.topostitch_recipe import POLICY, recipe_digest
from nasolve.topostitch_native_recipe import _pair_term_summary
from nasolve.topostitch_pair_coverage import select_pair_providers
from tests.test_topostitch_pair_coverage import inputs, term


def fixture(partial=False):
    requested, _, _, context = inputs()
    rows = []
    for i, declaration in enumerate(requested):
        kind = declaration['kind']; pair = 'core' if i < 4 else 'connection'
        declaration['term_id'] = f'{pair}:{i}'
        parameters = declaration['parameters']
        if kind == 'planarity': parameters['weights'] = [25.] * 3
        measurement = {
            'bond': {'distance_angstrom': parameters.get('ideal', 0) + (.2 if i < 4 else -.4)},
            'angle': {'angle_degrees': parameters.get('ideal', 0) + (2. if i < 4 else -4.)},
            'planarity': {'rms_distance_angstrom': .1 if i < 4 else .3},
            'parallelity': {'native_delta_degrees': 5. if i < 4 else -10.},
        }[kind]
        definition = dict(pair_id=pair, purpose='core' if i < 4 else 'selected', kind=kind,
                          sigma=1 / math.sqrt(parameters.get('weight', 25.)))
        if kind != 'planarity': definition['ideal'] = parameters['ideal']
        rows.append(dict(number=i + 1, definition=definition, measurement=measurement,
                         native_residual=float(i + 1)))
    native = deepcopy(requested[:3] if partial else requested[:4])
    for i, row in enumerate(native): row['term_id'] = f'observed:{i}'
    # Neither origin label establishes chemical ownership of unmatched terms.
    extras = [term('unknown-edited-bond', 'bond'), term('unknown-standard-angle', 'angle')]
    extras[0]['atoms'][1]['atom'] = 'f'; extras[1]['atoms'][2]['atom'] = 'f'
    native += extras
    selection = select_pair_providers(requested, native, frozen=dict(context=context,
        requested_sha256=recipe_digest(requested), native_sha256=recipe_digest(native)),
        current_context=context)
    attribution = dict(schema_version=1, kind='topostitch-native-pair-attribution',
        binding_sha256='a'*64, points_sha256='b'*64, terms=rows,
        **_pair_term_summary(rows), normalization=POLICY['normalization'],
        native_container_sum_verified=True, runtime_authority=False, scientific_acceptance=False)
    compiled = dict(policy_id='topostitch-compiled-pair-declarations-v1',
        compiled_binding_sha256='a'*64, source_model_sha256=context['source_model_sha256'],
        recipe_sha256=context['recipe_sha256'], atom_labels=context['atom_labels'],
        terms=requested, terms_sha256=recipe_digest(requested), runtime_authority=False,
        scientific_acceptance=False)
    observation = dict(policy_id='topostitch-native-pair-observation-v2', context=context,
        policy_owner_sha256='e'*64, terms=native, origin_ids=[4]*(len(native)-1)+[0],
        terms_sha256=recipe_digest(native), points_sha256='c'*64,
        native_state=dict(policy_id='topostitch-dual-native-state-v1',
            state_owner_policy_id='native-refinement-output-state-v1', state_owner_sha256='d'*64,
            atom_count=len(context['atom_labels']), hierarchy_sha256='e'*64,
            scattering_sha256='f'*64, fractional_sites_sha256='a'*64, force_sites_sha256='b'*64),
        runtime_authority=False, scientific_acceptance=False)
    return [attribution, compiled, observation, selection]


def review(values, digest=None):
    from nasolve.topostitch_pair_geometry import review_pair_geometry
    return review_pair_geometry(*values, expected_inputs_sha256=digest or recipe_digest(values))


def test_provider_transfer_preserves_physical_summary_and_keeps_unknown_edits():
    full, partial = fixture(), fixture(True)
    before = deepcopy(full)
    a, b = review(full), review(partial)
    assert full == before
    assert a['pair_geometry'] == b['pair_geometry']
    assert a['pair_geometry']['bond']['rms_deviation_angstrom'] == pytest.approx(math.sqrt(.1))
    assert a['pair_geometry']['angle']['rms_deviation_degrees'] == pytest.approx(math.sqrt(10))
    assert a['pair_geometry']['planarity']['rms_of_plane_rms_angstrom'] == pytest.approx(math.sqrt(.05))
    assert a['pair_geometry']['parallelity']['rms_native_delta_degrees'] == pytest.approx(math.sqrt(62.5))
    assert a['pairs'] == b['pairs']
    assert a['coverage']['native_requested_term_count'] == 4
    assert b['coverage']['native_requested_term_count'] == 3
    assert a['unclassified_native_terms'] == b['unclassified_native_terms'] == [
        dict(observed_id='unknown-edited-bond', kind='bond', origin_id=4),
        dict(observed_id='unknown-standard-angle', kind='angle', origin_id=0)]
    assert a['force_sites_sha256'] == full[2]['native_state']['force_sites_sha256']
    assert a['pair_energy'] == full[0]['target']
    assert a['covalent_geometry'] == 'UNASSESSED'
    assert not a['runtime_authority'] and not a['scientific_acceptance']


@pytest.mark.parametrize('defect', ['digest', 'old_observer', 'force_points', 'binding',
    'recipe', 'source', 'labels', 'origins', 'terms_digest', 'coverage', 'target',
    'measurement', 'summary', 'definition_order'])
def test_changed_or_inconsistent_measurement_context_refuses(defect):
    v = fixture(); expected = None
    if defect == 'digest':
        expected = recipe_digest(v); v[0]['terms'][0]['measurement']['distance_angstrom'] += 1
    elif defect == 'old_observer': v[2]['policy_id'] = 'topostitch-native-pair-observation-v1'
    elif defect == 'force_points': v[2]['native_state']['force_sites_sha256'] = 'e'*64
    elif defect == 'binding': v[1]['compiled_binding_sha256'] = 'e'*64
    elif defect == 'recipe': v[1]['recipe_sha256'] = 'e'*64
    elif defect == 'source': v[1]['source_model_sha256'] = 'e'*64
    elif defect == 'labels': v[1]['atom_labels'] = list(reversed(v[1]['atom_labels']))
    elif defect == 'origins': v[2]['origin_ids'].pop()
    elif defect == 'terms_digest': v[2]['terms_sha256'] = 'e'*64
    elif defect == 'coverage': v[3]['review']['coverage'][0]['provider'] = 'additive'
    elif defect == 'target': v[0]['terms'][0]['definition']['ideal'] += 1
    elif defect == 'measurement': v[0]['terms'][2]['measurement']['rms_distance_angstrom'] = -.1
    elif defect == 'summary': v[0]['target'] += 1
    else: v[0]['terms'][0]['definition']['pair_id'] = 'connection'
    with pytest.raises(ValueError): review(v, expected)


def test_same_origin_number_does_not_reclassify_the_remainder():
    values = fixture(); values[2]['origin_ids'] = [4] * len(values[2]['terms'])
    result = review(values)
    assert len(result['unclassified_native_terms']) == 2
    assert result['covalent_geometry'] == 'UNASSESSED'


def test_weight_changes_cannot_be_interpreted_as_physical_displacement():
    values = fixture(); baseline = review(values)
    # Change only measured residuals in a separately sealed report.
    for row in values[0]['terms']: row['native_residual'] *= 100
    values[0].update(_pair_term_summary(values[0]['terms']))
    result = review(values)
    assert result['pair_geometry'] == baseline['pair_geometry']
    assert result['pair_energy'] == baseline['pair_energy'] * 100
