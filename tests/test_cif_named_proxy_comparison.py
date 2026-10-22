"""Display padding and manager numbering cannot hide real restraint changes."""
from copy import deepcopy

import pytest

from nasolve.cif_terminal_qualification import _proxy_subset


KINDS = ['bond_simple', 'bond_asu', 'angle', 'dihedral', 'const_dihedral',
    'chirality', 'planarity', 'parallelity']


def native_pair(kind):
    atoms = [{'i_seq': i, 'atom_id': name, 'element': 'C', 'label': f'old:{i}',
        'identity': {'model_id': '', 'chain_id': 'X', 'resseq': '  17', 'icode': ' ',
            'altloc': '', 'resname': 'DG '}} for i, name in enumerate(['C1', 'C2', 'C3', 'C4', 'C5', 'C6'])]
    ids = list(range(3 if kind in {'angle', 'planarity', 'parallelity'} else 2 if kind.startswith('bond') else 4))
    row = {'i_seqs': ids, 'atoms': [atoms[i]['label'] for i in ids], 'origin_id': 0}
    if kind.startswith('bond'): row.update(distance_ideal=1.418, weight=1600., symmetry_operation=None)
    elif kind in {'angle', 'dihedral', 'const_dihedral'}:
        row.update(angle_ideal=125.1, weight=2.5)
        if kind != 'angle': row.update(periodicity=0 if kind == 'const_dihedral' else 3, alt_angle_ideals=[-60., 60.])
    elif kind == 'chirality': row.update(volume_ideal=-2.73, weight=25., both_signs=False)
    elif kind == 'planarity': row['weights'] = [2500., 1600., 900.]
    else: row.update(j_seqs=[3, 4, 5], j_atoms=[atoms[i]['label'] for i in [3, 4, 5]], weight=100., target_angle_deg=0.)
    before = {'atoms': atoms, 'geometry': {'proxy_details': {kind: [row]}}}
    after = deepcopy(before)
    for atom in after['atoms']:
        atom['i_seq'] += 20
        atom['label'] = f'new:{atom["i_seq"]}'
        atom['identity'].update(resname=' DG', resseq='17', icode='')
    current = after['geometry']['proxy_details'][kind][0]
    for key, labels in [('i_seqs', 'atoms'), ('j_seqs', 'j_atoms')]:
        if key in current:
            current[key] = [i + 20 for i in current[key]]
            current[labels] = [f'new:{i}' for i in current[key]]
    after['atoms'].reverse()  # Manager order is not atom identity.
    return before, after


@pytest.mark.parametrize('kind', KINDS)
def test_padding_and_reindexing_preserve_every_named_proxy(kind):
    before, after = native_pair(kind)
    snapshots = deepcopy((before, after))
    assert _proxy_subset(before, set(), kind) == _proxy_subset(after, set(), kind)
    assert (before, after) == snapshots


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('defect', ['target', 'weight', 'origin', 'multiplicity', 'endpoints', 'extra_parameter'])
def test_same_counts_or_labels_do_not_conceal_changed_mechanics(kind, defect):
    before, after = native_pair(kind); row = after['geometry']['proxy_details'][kind][0]
    if defect == 'target':
        key = 'distance_ideal' if kind.startswith('bond') else 'volume_ideal' if kind == 'chirality' else 'target_angle_deg' if kind == 'parallelity' else 'angle_ideal'
        if kind == 'planarity': row['weights'][0] += 1.
        else: row[key] += 1.
    if defect == 'weight':
        if kind == 'planarity': row['weights'][-1] *= 2
        else: row['weight'] *= 2
    if defect == 'origin': row['origin_id'] = 9
    if defect == 'multiplicity': after['geometry']['proxy_details'][kind].append(deepcopy(row))
    if defect == 'endpoints': row['i_seqs'][0] = 25; row['atoms'][0] = 'new:25'
    if defect == 'extra_parameter': row['new_native_parameter'] = 123
    assert _proxy_subset(before, set(), kind) != _proxy_subset(after, set(), kind)


@pytest.mark.parametrize('field,value', [('model_id', '2'), ('chain_id', 'Y'), ('resseq', '18'),
    ('icode', 'A'), ('altloc', 'B'), ('resname', 'DA'), ('atom_id', 'N1'), ('element', 'N')])
def test_each_structured_identity_field_is_preserved(field, value):
    before, after = native_pair('chirality')
    atom = next(a for a in after['atoms'] if a['i_seq'] == 20)
    (atom if field in {'atom_id', 'element'} else atom['identity'])[field] = value
    assert _proxy_subset(before, set(), 'chirality') != _proxy_subset(after, set(), 'chirality')


@pytest.mark.parametrize('defect', ['index', 'bool_index', 'duplicate_index', 'duplicate_name', 'missing_identity',
    'null_identity', 'blank_name', 'row_label', 'row_label_count', 'missing_rows', 'second_plane_label', 'orphan_second_plane'])
def test_ambiguous_or_unbound_native_identity_is_rejected(defect):
    _, after = native_pair('parallelity'); row = after['geometry']['proxy_details']['parallelity'][0]
    if defect == 'index': row['i_seqs'][0] = 999
    if defect == 'bool_index': after['atoms'][0]['i_seq'] = True
    if defect == 'duplicate_index': after['atoms'].append(deepcopy(after['atoms'][0]))
    if defect == 'duplicate_name':
        atom = deepcopy(after['atoms'][0]); atom['i_seq'] = 999; atom['label'] = 'different-display'; after['atoms'].append(atom)
    if defect == 'missing_identity': del after['atoms'][0]['identity']['altloc']
    if defect == 'null_identity': after['atoms'][0]['identity']['model_id'] = None
    if defect == 'blank_name': after['atoms'][0]['atom_id'] = ' '
    if defect == 'row_label': row['atoms'][0] = 'wrong'
    if defect == 'row_label_count': row['atoms'].pop()
    if defect == 'missing_rows': after['geometry']['proxy_details']['parallelity'] = None
    if defect == 'second_plane_label': row['j_atoms'][0] = 'wrong'
    if defect == 'orphan_second_plane': del row['j_seqs']
    with pytest.raises((KeyError, ValueError, TypeError)):
        _proxy_subset(after, set(), 'parallelity')


def test_selected_site_filter_includes_the_second_plane():
    before, after = native_pair('parallelity')
    for native in [before, after]:
        next(a for a in native['atoms'] if a['atom_id'] == 'C6')['identity']['resseq'] = '18'
    after['geometry']['proxy_details']['parallelity'][0]['weight'] = 2.
    assert _proxy_subset(before, {'X:18'}, 'parallelity') == _proxy_subset(after, {'X:18'}, 'parallelity')
    assert _proxy_subset(before, set(), 'parallelity') != _proxy_subset(after, set(), 'parallelity')


@pytest.mark.parametrize('defect', ['none', 'target', 'forged_label'])
def test_constructed_model_uses_the_shared_named_comparison(tmp_path, defect):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_construction_native import qualify_constructed_native
    before, after, model, preparation, projected = case(tmp_path)
    for native in [before, after]:
        native['geometry']['proxy_details']['bond_simple'].append({'i_seqs': [0, 7],
            'atoms': [native['atoms'][i]['label'] for i in [0, 7]], 'origin_id': 0, 'distance_ideal': 4., 'weight': 25.})
        native['geometry']['proxy_counts']['bond_simple'] += 1
    for atom in after['atoms']:
        atom['label'] = 'padded:' + atom['label']; atom['identity']['resname'] = atom['identity']['resname'].rjust(3)
    for rows in after['geometry']['proxy_details'].values():
        for row in rows: row['atoms'] = [after['atoms'][i]['label'] for i in row['i_seqs']]
    row = after['geometry']['proxy_details']['bond_simple'][-1]
    if defect == 'target': row['distance_ideal'] += .1
    if defect == 'forged_label': row['atoms'][0] = 'forged'
    entry = {'component': 'ZZZ', 'context': {'site': 'A:2', 'incoming_site': 'A:1', 'outgoing_site': 'A:3'},
        'preparation': preparation, 'projected': projected}
    result = qualify_constructed_native(before, after, model, model, [entry])
    assert result['mechanics_checks_pass'] is (defect == 'none'), result['checks']
