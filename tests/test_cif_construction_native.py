"""Exact constructed coordinates must retain complete native linkage mechanics."""
from copy import deepcopy
import pytest

from tests.test_cif_linked_control_qualification import case


@pytest.mark.parametrize('defect', ['none', 'qualification', 'source_binding', 'candidate_binding', 'context',
    'duplicate_site', 'missing_context', 'existing', 'symlink', 'nested_output', 'unselected_coordinate', 'component_path'])
def test_constructed_preparation_uses_bound_sources_and_exact_models(tmp_path, defect):
    from pathlib import Path
    from hashlib import sha256
    from tests.test_cif_linked_usability_bridge import prepared_inputs
    from nasolve.cif_construction_native import prepare_constructed_native
    source, numerical, model, contexts, q = prepared_inputs(tmp_path)
    # Keep an explicit independent unselected atom for coordinate preservation.
    text = model.read_text().replace('END\n', '')
    model.write_text(text + 'HETATM  999    P  DG Y   1       0.000   0.000   0.000  1.00 20.00           P\nEND\n')
    reference = tmp_path / 'inputs/reference.pdb'; reference.write_bytes(model.read_bytes())
    resource = {'source': source, 'numerical': numerical, 'contexts': contexts, 'qualification': q}
    output = tmp_path / 'prepared'; resources = {'ZZZ': resource}
    if defect == 'qualification': q['native_usable'] = False
    if defect == 'source_binding': q['source_assessment']['finished_stereo']['source_sha256'] = '0'*64
    if defect == 'candidate_binding': q['candidate_sha256'] = '0'*64
    if defect == 'context': contexts[0]['site'] = 'Y:99'
    if defect == 'duplicate_site': contexts.append(deepcopy(contexts[0]))
    if defect == 'missing_context': contexts.pop()
    if defect == 'existing': output.mkdir(); (output / 'sentinel').write_text('KEEP')
    if defect == 'symlink': output.symlink_to(tmp_path / 'inputs', target_is_directory=True)
    if defect == 'nested_output': output = source.parent / 'nested'
    if defect == 'unselected_coordinate': reference.write_text(reference.read_text().replace('  DG Y   1       0.000', '  DG Y   1       0.100'))
    if defect == 'component_path': resources = {'../ZZZ': resource}
    snapshots = {p: p.read_bytes() for p in [source, numerical, model, reference]}
    if defect != 'none':
        with pytest.raises((ValueError, FileExistsError)): prepare_constructed_native(reference, model, resources, output)
    else:
        report = prepare_constructed_native(reference, model, resources, output)
        refs = report['outputs']
        assert (output / refs['model']['path']).read_bytes() == model.read_bytes()
        assert (output / refs['reference']['path']).read_bytes() == reference.read_bytes()
        assert not report['requires_cif_review'] and not report['automatic_adoption']
        assert report['native_execution'] == report['policy_recompilation'] == 'NOT_RUN'
        assert len(refs['dictionaries']) == 2 and len(refs['phils']) == 2
        for r in [refs['model'], refs['reference'], *refs['dictionaries'], *refs['phils'], *refs['projections'].values()]:
            data = (output / r['path']).read_bytes()
            assert r['anchor'] == 'construction_native_directory' and len(data) == r['size'] and sha256(data).hexdigest() == r['sha256']
    assert all(p.read_bytes() == data for p, data in snapshots.items())
    if defect == 'existing': assert (output / 'sentinel').read_text() == 'KEEP'


@pytest.mark.parametrize('defect', ['none', 'lost_link', 'changed_link_target', 'changed_link_weight',
    'missing_heavy', 'native_coordinate', 'roundtrip', 'definition', 'proxy', 'modifier', 'lost_p_angle',
    'zero_weight', 'nonfinite_target', 'ss', 'extra_policy', 'energy', 'unrelated_definition', 'counts',
    'duplicate_mapping', 'missing_baseline_evidence', 'formal_charge_unavailable', 'formal_charge_conflict'])
def test_constructed_native_qualification_keeps_exact_mechanics(tmp_path, defect):
    from nasolve.cif_construction_native import qualify_constructed_native
    before, after, model, preparation, projected = case(tmp_path)
    entry = {'component': 'ZZZ', 'context': {'site': 'A:2', 'incoming_site': 'A:1', 'outgoing_site': 'A:3',
        'five_prime_state': 'linked', 'three_prime_state': 'linked'},
        'preparation': preparation, 'projected': projected}
    site = after['monomer_mappings']['rows'][1]
    if defect == 'lost_link': after['geometry']['simple_bonds'].pop()
    if defect == 'changed_link_target': after['geometry']['simple_bonds'][-1]['distance_ideal'] += .1
    if defect == 'changed_link_weight': after['geometry']['simple_bonds'][-1]['weight'] /= 2
    if defect == 'missing_heavy': site['missing_non_hydrogen_atoms']['atom_ids'] = ['OP1']
    if defect == 'native_coordinate': after['atoms'][0]['xyz'][0] += .1
    if defect == 'roundtrip': after['geometry']['sites_cart_exact'][0][0] += .1
    if defect == 'definition': site['metadata']['effective_definition']['atoms'][0]['type_energy'] = 'BROKEN'
    if defect == 'proxy': after['geometry']['proxy_details']['angle'][0]['angle_ideal'] += 5
    if defect == 'modifier': site['chem_mod_ids']['ids'] = []
    if defect == 'lost_p_angle': after['geometry']['proxy_details']['angle'].pop()
    if defect == 'zero_weight': after['geometry']['proxy_details']['bond_simple'][0]['weight'] = 0.
    if defect == 'nonfinite_target': after['geometry']['proxy_details']['angle'][-1]['angle_ideal'] = float('nan')
    if defect == 'ss': after['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'extra_policy': after['geometry']['custom_proxy_requests'] = [{'kind': 'bond'}]
    if defect == 'energy': after['energy_inventory']['snapshots'][1]['target'] += 1
    if defect == 'unrelated_definition': after['monomer_mappings']['rows'][0]['metadata']['effective_definition'] = {'changed': True}
    if defect == 'counts': after['geometry']['proxy_counts']['angle'] += 1
    if defect == 'duplicate_mapping': after['monomer_mappings']['rows'].append(deepcopy(site))
    if defect == 'missing_baseline_evidence': before['unused_definitions'] = ['bad']
    if defect == 'formal_charge_unavailable':
        for atom in site['metadata']['effective_definition']['atoms']: atom['charge'] = None
    if defect == 'formal_charge_conflict': site['metadata']['effective_definition']['atoms'][0]['charge'] = '-1'
    result = qualify_constructed_native(before, after, model, model, [entry])
    assert result['mechanics_checks_pass'] is (defect in {'none', 'formal_charge_unavailable'}), result['checks']
    assert result['status'] == ('CONSTRUCTED_NATIVE_MECHANICS_PASS' if result['mechanics_checks_pass'] else 'REVIEW')
    assert result['scientific_geometry_qualification'] == 'NOT_ASSESSED'
    assert not result['requires_cif_review'] and not result['automatic_adoption']


def test_missing_constructed_native_data_does_not_become_a_pass(tmp_path):
    from nasolve.cif_construction_native import qualify_constructed_native
    r = qualify_constructed_native({}, {}, tmp_path / 'absent', tmp_path / 'absent', [])
    assert r['status'] == 'REVIEW' and not r['mechanics_checks_pass']


@pytest.mark.parametrize('code', ['PDU', '5PC', 'Q17'])
@pytest.mark.parametrize('defect', ['none', 'missing_bond', 'missing_angle', 'long_bond', 'bent_target', 'weak_weight', 'order'])
def test_native_triples_are_scoped_to_the_exact_site_in_a_larger_model(tmp_path, code, defect):
    from tests.test_cif_triple_bond_audit import fixture
    from nasolve.cif_construction_native import _triple_readback
    source, values = fixture(tmp_path, code)
    atoms = [{'i_seq': i+10, 'atom_id': n, 'element': 'C', 'xyz': [float(values['_chem_comp_atom.pdbx_model_Cartn_'+x+'_ideal'][i]) for x in 'xyz'],
        'identity': {'model_id': '', 'chain_id': 'A', 'resseq': '9', 'icode': '', 'altloc': '', 'resname': f'{code:>3}'}}
        for i, n in enumerate(values['_chem_comp_atom.atom_id'])]
    # Another site with the same code must not affect this explicit projection.
    others = deepcopy(atoms)
    for a in others: a['i_seq'] += 30; a['identity']['resseq'] = '17'
    native = {'atoms': atoms + others, 'monomer_mappings': {'rows': [
        {'site': 'A:9', 'metadata': {'effective_definition': {'bonds': [{'atom_id_1': 'X', 'atom_id_2': 'Y', 'type': 'triple'}]}}},
        {'site': 'A:17', 'metadata': {'effective_definition': {'bonds': []}}}]},
        'geometry': {'proxy_details': {'bond_simple': [{'i_seqs': [11, 12], 'distance_ideal': 1.2, 'weight': 2500.}],
            'bond_asu': [], 'angle': [{'i_seqs': [10, 11, 12], 'angle_ideal': 180., 'weight': 1/9},
                {'i_seqs': [11, 12, 13], 'angle_ideal': 180., 'weight': 1/9}], 'dihedral': [], 'const_dihedral': []}}}
    g = native['geometry']['proxy_details']
    if defect == 'missing_bond': g['bond_simple'] = []
    if defect == 'missing_angle': g['angle'].pop()
    if defect == 'long_bond': g['bond_simple'][0]['distance_ideal'] = 1.54
    if defect == 'bent_target': g['angle'][0]['angle_ideal'] = 109.5
    if defect == 'weak_weight': g['angle'][0]['weight'] = .001
    if defect == 'order': native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type'] = 'single'
    report = _triple_readback(source, code, native, 'A:9')
    # Declared order is a separate graph check; target-screen alone addresses
    # membership/length/linearity. The full qualifier also checks exact bonds.
    assert report['target_screen'] == ('PASS' if defect in {'none', 'order'} else 'REVIEW')
    assert any(r['rule'] == 'triple-order-not-preserved' for r in report['findings']) is (defect == 'order')
    assert not any(r['rule'].startswith('ambiguous') for r in report['findings'])
    assert report['site'] == 'A:9'
