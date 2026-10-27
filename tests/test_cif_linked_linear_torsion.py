"""Complete linked omissions preserve same-named bystanders and all other fields."""
from copy import deepcopy
import pytest
from tests.test_cif_linear_torsion_candidate import dictionary, inventory
from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate


def fixture(tmp_path):
    source, values = dictionary(tmp_path)
    candidate = tmp_path/'candidate.cif'
    prepare_linear_torsion_candidate(source, 'Q17', candidate)
    before = inventory()
    before['inventory_detail'] = 'linked'
    def identity(code, chain):
        return dict(model_id='', chain_id=chain, resseq='1', icode='', altloc='', resname=code)
    first = before['monomer_mappings']['rows'][0]
    first['literal_identity'] = identity('Q17', 'A')
    from nasolve.cif_triple_bond_audit import _rows, _numeric
    definition = first['metadata']['effective_definition']
    for category, count, field in [('bond',2,'bonds'),('angle',3,'angles')]:
        definition[field] = []
        for row in _rows(values, category, count):
            native = {'atom_id_'+str(i+1): name for i,name in enumerate(row['atoms'])}
            native.update({k: _numeric(v) if k in ('value_dist','value_dist_esd','value_angle','value_angle_esd') else v for k,v in row.items() if k != 'atoms'})
            if category == 'bond': native['type'] = native.pop('value_order')
            definition[field].append(native)
    before['dictionary_loading'] = [{'input':'inputs/001_dictionary.cif',
        'component_metadata':[dict(id='Q17', effective_definition=deepcopy(first['metadata']['effective_definition']))]}]
    for a in before['atoms']:
        a['identity'] = identity('Q17', 'A')
    other = deepcopy(first); other['literal_identity'] = identity('5PC', 'B')
    before['monomer_mappings']['rows'].append(other)
    for a in deepcopy(before['atoms']):
        a['i_seq'] += 4; a['identity'] = identity('5PC', 'B'); before['atoms'].append(a)
    proxy = deepcopy(before['geometry']['proxy_details']['dihedral'][0]); proxy['i_seqs'] = [4,5,6,7]
    before['geometry']['proxy_details']['dihedral'].append(proxy)
    before['geometry']['proxy_counts']['dihedral'] = 2
    before['atom_count'] = 8
    after = deepcopy(before)
    after['dictionary_loading'][0]['component_metadata'][0]['effective_definition']['torsions'] = []
    after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions'] = []
    after['geometry']['proxy_details']['dihedral'].pop(0)
    after['geometry']['proxy_counts']['dihedral'] = 1
    return before, after, source, candidate


def qualify(args):
    from nasolve.cif_linked_linear_torsion import qualify_linked_linear_torsion_candidate
    before, after, source, candidate = args
    return qualify_linked_linear_torsion_candidate(before, after, source, 'Q17', candidate)


def test_complete_plan_preserves_same_named_bystander_and_inputs(tmp_path):
    args = fixture(tmp_path); saved = deepcopy(args[:2]); data = [p.read_bytes() for p in args[2:]]
    r = qualify(args)
    assert r['inventory_checks_pass'] and r['removed_native_proxy_counts'] == {'dihedral':1,'const_dihedral':0}
    assert r['modeled_occurrences'] == 1 and r['energy_delta_qualification'] == 'NOT_RUN'
    assert r['automatic_adoption'] is False and args[:2] == saved
    assert [p.read_bytes() for p in args[2:]] == data


@pytest.mark.parametrize('defect', ['bystander','phosphate','nar','charge','coordinates','policy','api','unknown','typed'])
def test_unplanned_inventory_changes_fail(tmp_path, defect):
    args = fixture(tmp_path); after = args[1]
    if defect == 'bystander': after['geometry']['proxy_details']['dihedral'] = []
    if defect == 'phosphate': after['monomer_mappings']['rows'][0]['chem_mod_ids'] = []
    if defect == 'nar': after['geometry']['proxy_details']['parallelity'] = []
    if defect == 'charge': after['monomer_mappings']['rows'][1]['metadata']['formal_charge_readback'] = 0
    if defect == 'coordinates': after['geometry']['sites_cart_exact'][0][0] = 1
    if defect == 'policy': after['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'api': after['installed_api_sources'] = []
    if defect == 'unknown': after['new_category'] = {}
    if defect == 'typed': after['geometry']['proxy_counts']['dihedral'] = True
    assert not qualify(args)['inventory_checks_pass']


@pytest.mark.parametrize('defect', ['incomplete_candidate','duplicate_mapping','duplicate_atom','missing_proxy','proxy_weight','alternate','origin','definition','provider','unsupported','linear_target','triple_order','candidate_format'])
def test_ambiguous_or_unbound_omissions_raise(tmp_path, defect):
    args = fixture(tmp_path); before, after, source, candidate = args
    if defect == 'linear_target': before['monomer_mappings']['rows'][0]['metadata']['effective_definition']['angles'][0]['value_angle'] = 179
    if defect == 'triple_order': before['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][1]['type'] = 'SING'
    if defect == 'candidate_format': candidate.write_bytes(candidate.read_bytes()+b'\n')
    if defect == 'incomplete_candidate': candidate.write_bytes(source.read_bytes())
    if defect == 'duplicate_mapping': before['monomer_mappings']['rows'].append(deepcopy(before['monomer_mappings']['rows'][0]))
    if defect == 'duplicate_atom': before['atoms'].append(deepcopy(before['atoms'][0]))
    if defect == 'missing_proxy': before['geometry']['proxy_details']['dihedral'].pop(0)
    if defect == 'proxy_weight': before['geometry']['proxy_details']['dihedral'][0]['weight'] = 2
    if defect == 'alternate': before['geometry']['proxy_details']['dihedral'][0]['alt_angle_ideals'] = [10]
    if defect == 'origin': before['geometry']['proxy_details']['dihedral'][0]['origin_id'] = 4
    if defect == 'definition': before['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions'][0]['period'] = 2
    if defect == 'provider': before['dictionary_loading'] *= 2
    if defect == 'unsupported': after['unsupported_fields'] = ['unread']
    with pytest.raises(ValueError): qualify(args)


def test_relocated_inputs_work_after_original_directory_is_gone(tmp_path):
    import shutil
    old = tmp_path/'original'; old.mkdir(); args = fixture(old)
    new = tmp_path/'relocated'; shutil.move(old, new)
    result = qualify((*args[:2], new/args[2].name, new/args[3].name))
    assert not old.exists() and result['inventory_checks_pass']


def test_all_occurrences_and_reversed_proxy_order_are_qualified(tmp_path):
    args = fixture(tmp_path); before, after, _, _ = args
    for native in (before, after):
        row = native['monomer_mappings']['rows'][1]
        row['literal_identity']['resname'] = 'Q17'
        for atom in native['atoms'][4:]: atom['identity']['resname'] = 'Q17'
    after['monomer_mappings']['rows'][1]['metadata']['effective_definition']['torsions'] = []
    after['geometry']['proxy_details']['dihedral'] = []
    after['geometry']['proxy_counts']['dihedral'] = 0
    before['geometry']['proxy_details']['dihedral'][1]['i_seqs'].reverse()
    r = qualify(args)
    assert r['inventory_checks_pass'] and r['modeled_occurrences'] == 2
    assert r['removed_effective_torsions'] == 2
    assert r['removed_native_proxy_counts']['dihedral'] == 2


def test_energy_is_explicitly_unqualified_not_inherited(tmp_path):
    args = fixture(tmp_path)
    args[0]['energy_inventory'] = {'target':10}
    args[1]['energy_inventory'] = {'target':9}
    r = qualify(args)
    assert r['inventory_checks_pass'] and r['energy_delta_qualification'] == 'NOT_RUN'
    assert r['derivative_qualification'] == 'NOT_RUN' and r['scientific_approval'] == 'NOT_RUN'
