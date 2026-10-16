"""Independent scalar geometry review; these fixtures are not native Phenix."""
from copy import deepcopy
import math

import pytest


def native():
    coords = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    atoms = [{'i_seq': i, 'label': 'synthetic_' + str(i), 'atom_id': name,
              'xyz': xyz, 'identity': {'chain_id': 'Z', 'resseq': '9', 'icode': '',
                                     'resname': 'ZZZ', 'altloc': '', 'model_id': ''}}
             for i, (xyz, name) in enumerate(zip(coords, ['centre', 'one', 'two', 'three']))]
    def row(indices, **fields):
        return {'i_seqs': indices, 'atoms': [atoms[i]['label'] for i in indices],
                'origin_id': 0, **fields}
    details = {
        'bond_simple': [row([0, 1], distance_ideal=.8, weight=100., symmetry_operation=None)],
        'angle': [row([1, 0, 2], angle_ideal=80., weight=.04)],
        'chirality': [row([0, 1, 2, 3], volume_ideal=.5, weight=4., both_signs=False)],
        'bond_asu': [], 'dihedral': [], 'const_dihedral': [], 'planarity': [], 'parallelity': []}
    return {'schema_version': 1, 'policy_id': 'cif-native-bundle-inventory-v1',
            'inventory_detail': 'linked', 'status': 'REVIEW', 'atom_count': 4, 'atoms': atoms,
            'geometry': {'status': 'RECORDED', 'sites_cart_exact': coords,
                         'proxy_details': details,
                         'proxy_counts': {k: len(v) for k, v in details.items()}}}


def test_scalar_measurements_use_captured_cartesian_coordinates_and_native_targets():
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native(); original = deepcopy(n)
    r = review_captured_geometry(n)
    bond, angle, chirality = [r['measurements'][kind][0] for kind in ('bond_simple', 'angle', 'chirality')]
    assert bond['observed'] == 1. and bond['nominal_deviation'] == pytest.approx(2.)
    assert angle['observed'] == 90. and angle['nominal_deviation'] == pytest.approx(2.)
    assert chirality['observed'] == 1. and chirality['nominal_deviation'] == pytest.approx(1.)
    assert chirality['sign_agreement'] is True
    assert r['status'] == 'REVIEW' and r['analysis_completed'] is True
    assert r['native_residuals'] == 'UNASSESSED' and r['scientific_approval'] == 'NOT_RUN'
    assert r['automatic_adoption'] is False and n == original


def test_geometry_is_invariant_to_rigid_motion_and_chirality_tracks_reflection():
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native(); transformed = deepcopy(n)
    for i, xyz in enumerate(n['geometry']['sites_cart_exact']):
        p = [-xyz[1]+12, xyz[0]-7, xyz[2]+3]
        transformed['geometry']['sites_cart_exact'][i] = p; transformed['atoms'][i]['xyz'] = p
    a = review_captured_geometry(n); b = review_captured_geometry(transformed)
    for kind in ('bond_simple', 'angle', 'chirality'):
        assert a['measurements'][kind][0]['observed'] == b['measurements'][kind][0]['observed']
    reflected = deepcopy(n)
    reflected['geometry']['sites_cart_exact'][1][0] = -1.
    reflected['atoms'][1]['xyz'][0] = -1.
    r = review_captured_geometry(reflected)
    assert r['measurements']['chirality'][0]['sign_agreement'] is False
    assert r['summary']['chirality']['sign_conflicts'] == 1
    reflected['geometry']['proxy_details']['chirality'][0]['both_signs'] = True
    r = review_captured_geometry(reflected)
    assert r['measurements']['chirality'][0]['sign_agreement'] is None
    assert r['measurements']['chirality'][0]['nominal_deviation'] == 1.


@pytest.mark.parametrize('weight,status', [(0., 'UNWEIGHTED'), (None, 'UNSUPPORTED'), (-1., 'INVALID_PROXY')])
def test_unavailable_or_nonpositive_weights_never_become_a_zero_deviation_pass(weight, status):
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native(); n['geometry']['proxy_details']['bond_simple'][0]['weight'] = weight
    row = review_captured_geometry(n)['measurements']['bond_simple'][0]
    assert row['status'] == status and row['nominal_deviation'] is None
    assert row['observed'] == 1.


@pytest.mark.parametrize('defect', ['index', 'label', 'count', 'coordinate', 'nonfinite', 'duplicate_index'])
def test_inconsistent_capture_is_refused(defect):
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native()
    if defect == 'index': n['geometry']['proxy_details']['angle'][0]['i_seqs'][0] = 99
    elif defect == 'label': n['geometry']['proxy_details']['angle'][0]['atoms'][0] = 'wrong'
    elif defect == 'count': n['geometry']['proxy_counts']['angle'] += 1
    elif defect == 'coordinate': n['atoms'][0]['xyz'] = [7., 8., 9.]
    elif defect == 'nonfinite': n['geometry']['sites_cart_exact'][0][0] = math.nan
    else: n['atoms'][1]['i_seq'] = 0
    with pytest.raises(ValueError): review_captured_geometry(n)


def test_degenerate_and_symmetry_proxies_remain_explicit_and_deferred_kinds_are_counted():
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native(); n['geometry']['proxy_details']['bond_simple'][0]['symmetry_operation'] = '-x,y,z'
    n['geometry']['proxy_details']['angle'][0]['i_seqs'] = [0, 0, 2]
    n['geometry']['proxy_details']['angle'][0]['atoms'] = ['synthetic_0', 'synthetic_0', 'synthetic_2']
    n['geometry']['proxy_details']['dihedral'] = [{'unassessed': 'periodic alternative convention'}]
    n['geometry']['proxy_counts']['dihedral'] = 1
    r = review_captured_geometry(n)
    assert r['measurements']['bond_simple'][0]['status'] == 'UNSUPPORTED'
    assert r['measurements']['bond_simple'][0]['observed'] is None
    assert r['measurements']['angle'][0]['status'] == 'DEGENERATE'
    assert r['deferred_proxy_kinds']['dihedral']['count'] == 1
    assert r['deferred_proxy_kinds']['dihedral']['status'] == 'UNASSESSED'


def test_ranking_reports_nominal_deviations_without_a_scientific_threshold_gate():
    from nasolve.cif_captured_geometry import review_captured_geometry
    n = native(); n['geometry']['proxy_details']['bond_simple'][0]['distance_ideal'] = .1
    r = review_captured_geometry(n)
    assert r['summary']['bond_simple']['nominal_abs_ge_5'] == 1
    assert r['summary']['bond_simple']['worst'][0]['nominal_deviation'] == 9.
    assert r['status'] == 'REVIEW' and r['complete_geometry_qualification'] == 'NOT_RUN'
