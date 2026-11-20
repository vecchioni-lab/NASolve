"""Synthetic scope accounting, not native or scientific geometry qualification."""
from copy import deepcopy

import pytest

from nasolve.metal.motion_scope import inspect_movement_scope
from nasolve.metal.recipe import RecipeError


def fixture():
    declarations = [('X', '8', 'DG', "O3'", 'O'), ('X', '17', 'Q17', 'P', 'P'),
                    ('X', '17', 'Q17', "O3'", 'O'), ('X', '17', 'Q17', 'N3', 'N'),
                    ('X', '92', 'DC', 'P', 'P'), ('Y', '-2', 'DG', "O3'", 'O'),
                    ('Y', '6', 'PDU', 'P', 'P'), ('Y', '6', 'PDU', "O3'", 'O'),
                    ('Y', '6', 'PDU', 'N3', 'N'), ('Y', '108', 'DC', 'P', 'P'),
                    ('Z', '5', 'HG', 'HG', 'HG'), ('Y', '0', 'I', 'I', 'I')]
    atoms = [dict(i_seq=i, label='synthetic_' + str(i), atom_id=name, element=element,
                  xyz=[float(i), float(i % 3), float(i % 2)], occupancy=.6 if element == 'HG' else 1.,
                  identity=dict(model_id='', chain_id=chain, resseq=resid, resname=code, altloc='', icode=''))
             for i, (chain, resid, code, name, element) in enumerate(declarations)]
    def row(indices, **values):
        return dict(i_seqs=indices, atoms=[atoms[i]['label'] for i in indices], origin_id=0, **values)
    bonds = [row(ids, distance_ideal=1.607, weight=100., symmetry_operation=None)
             for ids in ([0, 1], [2, 4], [5, 6], [7, 9], [3, 10], [8, 10], [4, 11])]
    angles = [row(ids, angle_ideal=110., weight=.25) for ids in ([0, 1, 3], [3, 2, 4], [5, 6, 8], [8, 7, 9])]
    parallel = row([1, 2, 3], j_seqs=[9, 10, 11], j_atoms=[atoms[i]['label'] for i in [9, 10, 11]], weight=1., target_angle_deg=0.)
    details = dict(bond_simple=bonds, bond_asu=[], angle=angles, chirality=[],
                   planarity=[row([1, 2, 3], weights=[1., 1., 1.])], parallelity=[parallel],
                   dihedral=[row([0, 1, 2, 3], angle_ideal=180., weight=1., periodicity=1)], const_dihedral=[])
    native = dict(schema_version=1, policy_id='cif-native-bundle-inventory-v1', inventory_detail='linked',
                  status='REVIEW', fatal_problems=None, unused_definitions=[], unsupported_fields=[], atom_count=len(atoms), atoms=atoms,
                  geometry=dict(status='RECORDED', sites_cart_exact=[a['xyz'][:] for a in atoms],
                                proxy_details=details, proxy_counts={k:len(v) for k, v in details.items()},
                                simple_bonds=deepcopy(bonds), asu_bonds=[]))
    contexts = [dict(site='X:17', component='Q17', incoming_site='X:8', outgoing_site='X:92'),
                dict(site='Y:6', component='PDU', incoming_site='Y:-2', outgoing_site='Y:108')]
    return native, contexts, ['synthetic_10']


def inspect(native, contexts, labels):
    return inspect_movement_scope(native, site_contexts=contexts, metal_labels=labels)


def test_explicit_nonsequential_sites_include_four_junctions_and_all_term_families():
    n, contexts, labels = fixture()
    before = deepcopy((n, contexts, labels))
    r = inspect(n, contexts, labels)
    assert r['moving_indices'] == [1, 2, 3, 6, 7, 8, 10]
    assert r['fixed_atom_count'] == 5
    assert r['fixed_flank_sites'] == ['X:8', 'X:92', 'Y:-2', 'Y:108']
    assert len(r['polymer_junctions']) == 4
    assert all(len(j['angles']) == 1 for j in r['polymer_junctions'])
    assert r['term_counts']['bond_simple'] == dict(internal=2, boundary=4, outside=1)
    assert r['term_counts']['parallelity'] == dict(internal=0, boundary=1, outside=0)
    assert r['term_counts']['planarity'] == dict(internal=1, boundary=0, outside=0)
    assert r['term_counts']['dihedral'] == dict(internal=0, boundary=1, outside=0)
    assert r['fixed_boundary_indices'] == [0, 4, 5, 9, 11]
    assert r['scientific_acceptance'] is False and r['movement_admitted'] is False
    assert r['coordinates_changed'] is False and r['native_execution'] == 'NOT_RUN'
    assert (n, contexts, labels) == before
    r['boundary_terms']['bond_simple'][0]['proxy']['i_seqs'][0] = 99
    assert (n, contexts, labels) == before


def test_context_and_metal_order_do_not_change_scope_identity():
    n, contexts, labels = fixture()
    assert inspect(n, contexts, labels) == inspect(n, contexts[::-1], labels)


def test_connected_selected_residue_is_internal_not_a_fixed_flank():
    n, contexts, labels = fixture()
    contexts.append(dict(site='X:8', component='DG', incoming_site=None, outgoing_site='X:17'))
    r = inspect(n, contexts, labels)
    assert 0 in r['moving_indices'] and 'X:8' not in r['fixed_flank_sites']
    assert r['term_counts']['bond_simple'] == dict(internal=3, boundary=3, outside=1)
    link = next(j for j in r['polymer_junctions'] if j['sites'] == ['X:8', 'X:17'])
    assert link['scope'] == 'internal'


@pytest.mark.parametrize('fault', ['missing_link', 'extra_link', 'stale_comp', 'missing_partner', 'duplicate_context',
                                  'context_extra', 'self_link', 'missing_metal', 'duplicate_metal', 'overlap_metal',
                                  'alternate', 'insertion', 'hydrogen', 'crossing_symmetry', 'count', 'parallel_label',
                                  'deferred_indices', 'partial_capture', 'coordinates', 'duplicate_native_identity', 'model_ids', 'flank_alternate', 'ambiguous_flank'])
def test_incomplete_or_ambiguous_scope_is_refused(fault):
    n, contexts, labels = fixture()
    if fault == 'missing_link': n['geometry']['simple_bonds'].pop(0)
    elif fault == 'extra_link': contexts[0]['outgoing_site'] = None
    elif fault == 'stale_comp': contexts[0]['component'] = 'BAD'
    elif fault == 'missing_partner': contexts[0]['incoming_site'] = 'X:7'
    elif fault == 'duplicate_context': contexts.append(deepcopy(contexts[0]))
    elif fault == 'context_extra': contexts[0]['guess_by_distance'] = True
    elif fault == 'self_link': contexts[0]['incoming_site'] = 'X:17'
    elif fault == 'missing_metal': labels[0] = 'absent'
    elif fault == 'duplicate_metal': labels *= 2
    elif fault == 'overlap_metal': labels[0] = 'synthetic_3'
    elif fault == 'alternate': n['atoms'][1]['identity']['altloc'] = 'A'
    elif fault == 'insertion': n['atoms'][1]['identity']['icode'] = 'A'
    elif fault == 'hydrogen': n['atoms'][1]['element'] = 'H'
    elif fault == 'crossing_symmetry': n['geometry']['proxy_details']['bond_simple'][0]['symmetry_operation'] = '-x,y,z'
    elif fault == 'count': n['geometry']['proxy_counts']['dihedral'] += 1
    elif fault == 'parallel_label': n['geometry']['proxy_details']['parallelity'][0]['j_atoms'][0] = 'incorrect'
    elif fault == 'deferred_indices': n['geometry']['proxy_details']['dihedral'][0]['i_seqs'][0] = 999
    elif fault == 'partial_capture': n['inventory_detail'] = 'selected'
    elif fault == 'coordinates': n['atoms'][0]['xyz'] = [100., 0., 0.]
    elif fault == 'duplicate_native_identity': n['atoms'][2]['atom_id'] = n['atoms'][1]['atom_id']
    elif fault == 'model_ids': n['atoms'][0]['identity']['model_id'] = 'other'
    elif fault == 'flank_alternate': n['atoms'][0]['identity']['altloc'] = 'A'
    elif fault == 'ambiguous_flank':
        extra = deepcopy(n['atoms'][0])
        extra.update(i_seq=len(n['atoms']), label='extra_flank_alternate')
        extra['identity']['altloc'] = 'A'
        n['atoms'].append(extra)
        n['atom_count'] += 1
        n['geometry']['sites_cart_exact'].append(extra['xyz'][:])
    with pytest.raises(RecipeError):
        inspect(n, contexts, labels)


def test_missing_and_changed_targets_remain_distinct_from_geometry_acceptance():
    n, contexts, labels = fixture()
    for table in ('simple_bonds',):
        n['geometry'][table][0]['distance_ideal'] = 2.
    n['geometry']['proxy_details']['bond_simple'][0]['distance_ideal'] = 2.
    r = inspect(n, contexts, labels)
    assert next(j for j in r['polymer_junctions'] if j['sites'] == ['X:8', 'X:17'])['bond']['target'] == 2.
    assert r['status'] == 'MOVEMENT_SCOPE_REVIEW' and r['scientific_acceptance'] is False
    n['geometry']['proxy_details']['bond_simple'][0]['weight'] = None
    with pytest.raises(RecipeError): inspect(n, contexts, labels)


def test_intra_site_capture_cannot_stand_for_junction_coverage():
    n, contexts, labels = fixture()
    n.update(policy_id='native-refinement-selected-sites-v1', scope='ACTUAL_NATIVE_MANAGER_INTRA_SITE_HEAVY_ATOMS')
    with pytest.raises(RecipeError): inspect(n, contexts, labels)
