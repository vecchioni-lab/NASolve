"""Connectivity-selected derivatives, including misleading hydrogen names."""
from pathlib import Path

import pytest


def fixture(tmp_path):
    input_dir=tmp_path/'inputs'; input_dir.mkdir()
    names = ['P', 'OP1', 'OP2', 'OP3', "O5'", "C5'", "C3'", "O3'",
             'keepH', 'leaveH', 'oddH']
    elements = ['P', 'O', 'O', 'O', 'O', 'C', 'C', 'O', 'H', 'H', 'H']
    bonds = [('P','OP1'), ('P','OP2'), ('P','OP3'), ('P',"O5'"),
             ("O5'","C5'"), ("C3'","O3'"), ('OP2','keepH'),
             ('OP3','leaveH'), ("O3'",'oddH')]
    def quote(value): return '"'+value+'"'
    text = ('data_comp_list\nloop_\n_chem_comp.id\n_chem_comp.type\n_chem_comp.group\n'
            'ZZZ "DNA LINKING" non-polymer\n\ndata_comp_ZZZ\nloop_\n'
            '_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n'
            '_chem_comp_atom.type_symbol\n_chem_comp_atom.type_energy\n_chem_comp_atom.charge\n')
    text += ''.join('ZZZ '+quote(n)+' '+e+' '+('OH1' if e=='O' else e)+' 0\n'
                    for n,e in zip(names,elements))
    text += ('loop_\n_chem_comp_bond.comp_id\n_chem_comp_bond.atom_id_1\n'
             '_chem_comp_bond.atom_id_2\n_chem_comp_bond.type\n'
             '_chem_comp_bond.value_dist\n_chem_comp_bond.value_dist_esd\n')
    text += ''.join('ZZZ '+quote(a)+' '+quote(b)+' single 1.5 0.02\n' for a,b in bonds)
    from itertools import combinations
    text += ('loop_\n_chem_comp_angle.comp_id\n_chem_comp_angle.atom_id_1\n'
             '_chem_comp_angle.atom_id_2\n_chem_comp_angle.atom_id_3\n'
             '_chem_comp_angle.value_angle\n_chem_comp_angle.value_angle_esd\n')
    for center in names:
        neighbors=[b if a==center else a for a,b in bonds if center in (a,b)]
        for a,b in combinations(neighbors,2):
            text += 'ZZZ '+quote(a)+' '+quote(center)+' '+quote(b)+' 109.47 3.0\n'
    source=input_dir/'source.cif'; source.write_text(text)
    numerical=input_dir/'numerical.cif'; numerical.write_text(text)
    lines=[]; serial=0
    for chain,resseq,state in [('A',1,'phosphate'),('A',2,'internal'),('B',1,'free_OH')]:
        for name,element in zip(names,elements):
            if element=='H' or (state=='internal' and name=='OP3') or (state=='free_OH' and name in {'P','OP1','OP2','OP3'}): continue
            serial+=1
            lines.append(f'HETATM{serial:5d} {name:>4} ZZZ {chain}{resseq:4d}    {serial:8.3f}{1.:8.3f}{2.:8.3f}  1.00 20.00          {element:>2}\n')
    model=input_dir/'model.pdb'; model.write_text(''.join(lines)+'END\n')
    contexts=[{'site':'A:2','incoming_site':'A:1','outgoing_site':None,
               'five_prime_state':'linked','three_prime_state':'free_OH'},
              {'site':'B:1','incoming_site':None,'outgoing_site':None,
               'five_prime_state':'free_OH','three_prime_state':'free_OH'},
              {'site':'A:1','incoming_site':None,'outgoing_site':'A:2',
               'five_prime_state':'phosphate','three_prime_state':'linked'}]
    return source,numerical,model,contexts


def test_site_specific_deletions_preserve_op2_h_and_true_end(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    before=[p.read_bytes() for p in (source,numerical,model)]
    result=prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    assert result['status']=='PREPARED_REVIEW'
    internal,end,_=result['sites']
    assert internal['deleted_atoms']==['OP3','leaveH']
    assert internal['retained_op2_hydrogens']==['keepH']
    assert 'oddH' in internal['expected_atoms']
    assert end['deleted_atoms']==['OP1','OP2','OP3','P','keepH','leaveH']
    assert 'oddH' in end['expected_atoms']
    assert internal['modification_id']!=end['modification_id']
    assert [p.read_bytes() for p in (source,numerical,model)]==before


def test_single_component_metadata_remains_a_native_list_loop(tmp_path):
    """Native convert_list_block reads comp_list metadata through iterrows."""
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.ligand_profiles import _blocks
    source,numerical,model,contexts=fixture(tmp_path)
    prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    for path in [tmp_path/'out/base_dictionary.cif', *sorted((tmp_path/'out').glob('projected_*.cif'))]:
        metadata=_blocks(path)[0]
        assert metadata.values['data_']=='comp_list'
        assert '\nloop_\n_chem_comp.' in metadata.text
        assert metadata.values['_chem_comp.id']==['ZZZ']
        assert metadata.values['_chem_comp.group']==['DNA']


@pytest.mark.parametrize('name',["Source O3' with a \"quoted\" label",'First line\nSecond line'])
def test_native_list_loop_preserves_quoted_and_multiline_metadata(tmp_path,name):
    from nasolve.cif_linked_preparation import _render,component_values
    source,_,_,_=fixture(tmp_path)
    values=component_values(source,'ZZZ')
    values['_chem_comp.name']=[name]
    output=tmp_path/'rendered.cif';output.write_text(_render(values,'ZZZ'))
    assert component_values(output,'ZZZ')==values


def test_outgoing_link_removes_graph_selected_hydrogen_and_changes_type(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    contexts[0]=dict(contexts[0],outgoing_site='A:1',three_prime_state='linked')
    result=prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    item=result['sites'][0]
    assert item['deleted_atoms']==['OP3','leaveH','oddH']
    assert item['expected_energy_types']["O3'"]=='OC2'
    assert item['retained_op2_hydrogens']==['keepH']
    assert "chain 'A' and resid 2 and resname ZZZ" in (tmp_path/'out/site_modifications.phil').read_text()


def test_explicit_terminal_phosphate_retains_op3(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    result=prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    assert result['sites'][2]['deleted_atoms']==['oddH']
    assert 'OP3' in result['sites'][2]['expected_atoms']


@pytest.mark.parametrize('alteration',['unknown_end','unsupported_symmetry','duplicate_site','wrong_identity','undeclared_same_code_site'])
def test_ambiguous_contexts_rejected_before_output(tmp_path,alteration):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    if alteration=='unknown_end': contexts[1]['five_prime_state']='unknown'
    if alteration=='unsupported_symmetry': contexts[0]['symmetry_operation']='x+1,y,z'
    if alteration=='duplicate_site': contexts.append(contexts[0])
    if alteration=='wrong_identity': contexts[0]['site']='C:1'
    if alteration=='undeclared_same_code_site': contexts.pop()
    with pytest.raises(ValueError):
        prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    assert not (tmp_path/'out').exists()


def test_changed_source_state_requires_generation_instead_of_hydrogen_invention(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    numerical.write_text(numerical.read_text().replace('ZZZ "keepH" H H 0\n','').replace('ZZZ "OP2" "keepH" single 1.5 0.02\n',''))
    with pytest.raises(ValueError,match='source-preserving'):
        prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    assert not (tmp_path/'out').exists()


def test_existing_output_directory_refused(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts=fixture(tmp_path)
    out=tmp_path/'out';out.mkdir()
    with pytest.raises(FileExistsError): prepare_linked_component(source,numerical,model,contexts,out,code='ZZZ')


def test_native_registration_matches_each_requested_site_modifier(tmp_path):
    """The monomer reader derives registry keys from mod_ block names."""
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.ligand_profiles import _blocks
    source,numerical,model,contexts=fixture(tmp_path)
    result=prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')
    expected={site['modification_id'] for site in result['sites'] if site['modification_id']}
    blocks=_blocks(tmp_path/'out/site_modifications.cif')
    registered={block.values['data_'][len('mod_'):] for block in blocks
                if block.values['data_'].startswith('mod_')}
    assert registered==expected
    assert len(blocks)==len(expected)==3
    for block in blocks:
        assert set(block.values['_chem_mod_atom.mod_id'])=={block.values['data_'][len('mod_'):]}
    parameters=(tmp_path/'out/site_modifications.phil').read_text()
    assert all('data_mod = '+identifier in parameters for identifier in registered)


def test_different_component_files_do_not_overwrite_native_modifier_ids(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.ligand_profiles import _blocks
    registered={}
    expected=set()
    for code in ['ZZZ','Q99']:
        case=tmp_path/code;case.mkdir()
        source,numerical,model,contexts=fixture(case)
        for path in (source,numerical,model):
            path.write_text(path.read_text().replace('ZZZ',code))
        result=prepare_linked_component(source,numerical,model,contexts,case/'out',code=code)
        expected.update(site['modification_id'] for site in result['sites'] if site['modification_id'])
        for block in _blocks(case/'out/site_modifications.cif'):
            identifier=block.values['data_'][len('mod_'):]
            assert identifier not in registered
            registered[identifier]=block.values
    assert set(registered)==expected and len(registered)==6
