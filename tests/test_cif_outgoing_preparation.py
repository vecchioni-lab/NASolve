"""Captured-source linked oxygen candidates; fixtures are not installed Phenix."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest


def fixture(tmp_path, hydrogen='oddH', element='H'):
    from nasolve.cif_linked_preparation import _prune, _render
    from nasolve.cif_terminal_qualification import _CATEGORIES, _rows
    directory=tmp_path/'inputs';directory.mkdir()
    names=['P','OP1','OP2','OP3',"O5'","C5'","C3'","O3'",'keepH',hydrogen]
    elements=['P','O','O','O','O','C','C','O','H',element]
    values={'data_':'comp_ZZZ','_chem_comp.id':['ZZZ'],'_chem_comp.group':['DNA'],
        '_chem_comp.number_atoms_all':['10'],'_chem_comp.number_atoms_nh':['8']}
    def category(name, rows):
        for key in rows[0]:values[name+'.'+key]=[str(row[key]) for row in rows]
    category('_chem_comp_atom',[{'comp_id':'ZZZ','atom_id':n,'type_symbol':e,
        'type_energy':'OH1' if n=="O3'" else e,'charge':'0'} for n,e in zip(names,elements)])
    bonds=[('P','OP1'),('P','OP2'),('P','OP3'),('P',"O5'"),("O5'","C5'"),
           ("C3'","O3'"),('OP2','keepH'),("O3'",hydrogen)]
    category('_chem_comp_bond',[{'comp_id':'ZZZ','atom_id_1':a,'atom_id_2':b,
        'type':'single','value_dist':1.5,'value_dist_esd':.02} for a,b in bonds])
    category('_chem_comp_angle',[{'comp_id':'ZZZ','atom_id_1':"C3'",'atom_id_2':"O3'",
        'atom_id_3':hydrogen,'value_angle':109.47,'value_angle_esd':3.}])
    source=directory/'source.cif';source.write_text(_render(values,'ZZZ'))
    model=directory/'model.pdb';lines=[];atoms=[];serial=0
    for chain,resid,code in [('A',1,'ZZZ'),('A',2,'ZZZ'),('C',1,'DC'),('C',2,'DC')]:
        inventory=[(n,e) for n,e in zip(names,elements) if e not in {'H','D'}
                   and not (resid==2 and n=='OP3')] if code=='ZZZ' else [('P','P'),("C3'",'C'),("O3'",'O')]
        for name,symbol in inventory:
            serial+=1;lines.append(f'HETATM{serial:5d} {name:>4} {code:>3} {chain}{resid:4d}    {serial:8.3f}{1.:8.3f}{2.:8.3f}  1.00 20.00          {symbol:>2}\n')
            atoms.append({'i_seq':serial-1,'atom_id':name,'identity':{'chain_id':chain,'resseq':str(resid),'icode':''}})
    model.write_text(''.join(lines)+'END\n')
    mappings=[]
    for site,removed in [('A:1',set()),('A:2',{'OP3'})]:
        v=_prune(values,removed,outgoing=False)
        definition={name:[{k:r.get(k) for k in fields} for r in _rows(v,category)]
                    for name,(category,fields) in _CATEGORIES.items()}
        mappings.append({'site':site,'resname':'ZZZ','chem_mod_ids':{'status':'RECORDED','ids':[] if site=='A:1' else ['existing']},
            'metadata':{'group':'DNA','effective_definition':definition}})
    for site in ['C:1','C:2']:
        mappings.append({'site':site,'resname':'DC','chem_mod_ids':{'status':'RECORDED','ids':[]},
            'metadata':{'group':'DNA','effective_definition':{'atoms':[
                {'atom_id':"O3'",'type_symbol':'O','type_energy':'OC2'},
                {'atom_id':"C3'",'type_symbol':'C','type_energy':'CH1'}],
                'bonds':[{'atom_id_1':"O3'",'atom_id_2':"C3'",'type':'single'}]}}})
    links=[('A:1','A:2'),('C:1','C:2')]
    def index(site,name):
        return next(a['i_seq'] for a in atoms if a['identity']['chain_id']+':'+a['identity']['resseq']==site and a['atom_id']==name)
    native={'schema_version':1,'policy_id':'cif-native-bundle-inventory-v1','status':'REVIEW',
        'inventory_detail':'linked','atoms':atoms,'monomer_mappings':{'status':'RECORDED','rows':mappings},
        'geometry':{'simple_bonds':[{'i_seqs':[index(a,"O3'"),index(b,'P')],
            'distance_ideal':1.6,'weight':2500.} for a,b in links]}}
    capture=tmp_path/'capture';(capture/'inputs').mkdir(parents=True)
    frozen_model=capture/'inputs/model.pdb';frozen_model.write_bytes(model.read_bytes())
    receipt={'schema_version':1,'audit_kind':'cif_native_bundle_inspection',
        'policy_id':native['policy_id'],'status':'REVIEW','native_validation':native,
        'execution':{'status':'COMPLETED','returncode':0},'frozen_inputs_preserved':True,'source_preserved':True,
        'phenix_version':'FAKE_TEST_NO_PHENIX','executable_sha256':'b'*64,
        'inputs':[{'anchor':'native_directory','path':'inputs/model.pdb','role':'model',
            'sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'size':model.stat().st_size}]}
    receipt_path=capture/'native_receipt.json';save_capture(receipt_path,receipt)
    contexts=[{'site':'A:1','incoming_site':None,'outgoing_site':'A:2','five_prime_state':'phosphate','three_prime_state':'linked'},
        {'site':'A:2','incoming_site':'A:1','outgoing_site':None,'five_prime_state':'linked','three_prime_state':'free_OH'}]
    return source,model,contexts,receipt_path,links


def save_capture(path,receipt):
    report=path.parent/'native_validation.json';report.write_text(json.dumps(receipt['native_validation']))
    receipt['outputs']=[{'anchor':'native_directory','path':report.name,
        'sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'size':report.stat().st_size}]
    path.write_text(json.dumps(receipt))


@pytest.mark.parametrize('hydrogen,element',[('HO31','H'),("HO3'",'H'),('H2','H'),('H3','H'),('looksC','H'),('oddD','D')])
def test_graph_selected_correction_preserves_true_end_op2_and_numerics(tmp_path,hydrogen,element):
    from nasolve.cif_outgoing_preparation import prepare_outgoing_component
    from nasolve.cif_linked_preparation import atom_rows,component_values,hydrogen_neighbors
    source,model,contexts,capture,links=fixture(tmp_path,hydrogen,element)
    before={p:p.read_bytes() for p in [source,model,capture]}
    result=prepare_outgoing_component(source,model,contexts,capture,tmp_path/'out',
        code='ZZZ',expected_links=links,authority_site='C:1')
    assert result['status']=='PREPARED_REVIEW' and result['automatic_adoption'] is False
    assert result['unchanged_sites']==['A:2']
    assert len(result['sites'])==1 and result['sites'][0]['site']=='A:1'
    assert result['sites'][0]['deleted_atoms']==[hydrogen]
    assert result['sites'][0]['retained_op2_hydrogens']==['keepH']
    assert result['sites'][0]['expected_energy_types']["O3'"]=='OC2'
    projected=component_values(tmp_path/'out/projected_A_1.cif','ZZZ')
    assert hydrogen_neighbors(projected,"O3'")==[] and hydrogen_neighbors(projected,'OP2')==['keepH']
    assert 'OP3' in atom_rows(projected)  # Declared terminal phosphate survives.
    assert all(row['charge']=='0' for row in atom_rows(projected).values())
    assert (tmp_path/'out/site_modifications.phil').read_text().count('residue_selection')==1
    assert 'resid 2' not in (tmp_path/'out/site_modifications.phil').read_text()
    assert result['outgoing_type_authority']['type_energy']=='OC2'
    assert result['outgoing_type_authority']['partial_charge_copied'] is False
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('defect',['changed_report','failed_execution','model_changed','wrong_authority_type',
    'wrong_authority_identity','changed_target','missing_context','wrong_link','coordinate_hydrogen','reused_output'])
def test_unproven_or_unsafe_correction_is_refused(tmp_path,defect):
    from nasolve.cif_outgoing_preparation import prepare_outgoing_component
    source,model,contexts,capture,links=fixture(tmp_path)
    receipt=json.loads(capture.read_text());native=receipt['native_validation'];output=tmp_path/'out'
    if defect=='changed_report':(capture.parent/'native_validation.json').write_text('{}')
    elif defect=='failed_execution':receipt['execution']['returncode']=2;save_capture(capture,receipt)
    elif defect=='model_changed':model.write_text(model.read_text()+'REMARK changed\n')
    elif defect=='wrong_authority_type':
        native['monomer_mappings']['rows'][2]['metadata']['effective_definition']['atoms'][0]['type_energy']='OH1'
        save_capture(capture,receipt)
    elif defect=='wrong_authority_identity':native['monomer_mappings']['rows'][2]['resname']='ZZZ';save_capture(capture,receipt)
    elif defect=='changed_target':
        native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['value_dist']=1.9
        save_capture(capture,receipt)
    elif defect=='missing_context':contexts.pop()
    elif defect=='wrong_link':contexts[0]['outgoing_site']='C:2'
    elif defect=='coordinate_hydrogen':
        line=f'HETATM{99:5d} {"oddH":>4} ZZZ A{1:4d}    {1.:8.3f}{1.:8.3f}{2.:8.3f}  1.00 20.00           H\n'
        model.write_text(model.read_text()+line)
        (capture.parent/'inputs/model.pdb').write_bytes(model.read_bytes())
        receipt['inputs'][0].update(sha256=hashlib.sha256(model.read_bytes()).hexdigest(),size=model.stat().st_size)
        save_capture(capture,receipt)
    else:output.mkdir()
    with pytest.raises((ValueError,FileExistsError)):
        prepare_outgoing_component(source,model,contexts,capture,output,code='ZZZ',expected_links=links,authority_site='C:1')
    if defect!='reused_output':assert not output.exists()


def test_existing_incoming_modification_is_retained_in_new_site_plan(tmp_path):
    from nasolve.cif_outgoing_preparation import prepare_outgoing_component
    source,model,contexts,capture,links=fixture(tmp_path)
    # Reverse the declared strand so A:2 has both an incoming link from C:2
    # and an outgoing link to A:1; the source/native projection already lacks OP3.
    contexts[0].update(incoming_site='A:2',outgoing_site=None,five_prime_state='linked',three_prime_state='free_OH')
    contexts[1].update(incoming_site='C:2',outgoing_site='A:1',three_prime_state='linked')
    receipt=json.loads(capture.read_text());native=receipt['native_validation']
    native['monomer_mappings']['rows'][0]['metadata']['effective_definition']=deepcopy(native['monomer_mappings']['rows'][1]['metadata']['effective_definition'])
    native['monomer_mappings']['rows'][0]['chem_mod_ids']['ids']=['existing']
    model.write_text(''.join(line for line in model.read_text().splitlines(keepends=True) if not (line.startswith('HETATM') and line[21]=='A' and line[22:26].strip()=='1' and line[12:16].strip()=='OP3')))
    native['atoms']=[a for a in native['atoms'] if not (a['identity']['chain_id']=='A' and a['identity']['resseq']=='1' and a['atom_id']=='OP3')]
    (capture.parent/'inputs/model.pdb').write_bytes(model.read_bytes())
    receipt['inputs'][0].update(sha256=hashlib.sha256(model.read_bytes()).hexdigest(),size=model.stat().st_size)
    def idx(site,name):
        return next(a['i_seq'] for a in native['atoms'] if a['identity']['chain_id']+':'+a['identity']['resseq']==site and a['atom_id']==name)
    links=[('C:1','C:2'),('C:2','A:2'),('A:2','A:1')]
    native['geometry']['simple_bonds']=[{'i_seqs':[idx(a,"O3'"),idx(b,'P')],'distance_ideal':1.6,'weight':2500.} for a,b in links]
    save_capture(capture,receipt)
    result=prepare_outgoing_component(source,model,contexts,capture,tmp_path/'out',code='ZZZ',expected_links=links,authority_site='C:1')
    assert result['sites'][0]['site']=='A:2'
    assert result['sites'][0]['prior_modification_ids']==['existing']
    assert result['sites'][0]['deleted_atoms']==['oddH']
    assert 'OP3' not in result['sites'][0]['expected_atoms']


def test_retained_formal_partial_charges_and_targets_are_not_replaced(tmp_path):
    from nasolve.cif_outgoing_preparation import prepare_outgoing_component
    from nasolve.cif_linked_preparation import _render,component_values,atom_rows
    source,model,contexts,capture,links=fixture(tmp_path)
    values=component_values(source,'ZZZ');values['_chem_comp_atom.partial_charge']=['.17']*10
    values['_chem_comp_atom.charge'][0]='-1';source.write_text(_render(values,'ZZZ'))
    receipt=json.loads(capture.read_text())
    for row in receipt['native_validation']['monomer_mappings']['rows'][:2]:
        for atom in row['metadata']['effective_definition']['atoms']:atom['partial_charge']=.17
    receipt['native_validation']['monomer_mappings']['rows'][2]['metadata']['effective_definition']['atoms'][0]['partial_charge']=-.267
    save_capture(capture,receipt)
    result=prepare_outgoing_component(source,model,contexts,capture,tmp_path/'out',code='ZZZ',expected_links=links,authority_site='C:1')
    projected=component_values(tmp_path/'out/projected_A_1.cif','ZZZ');atoms=atom_rows(projected)
    assert atoms["O3'"]['partial_charge']=='.17' and atoms['P']['charge']=='-1'
    assert result['sites'][0]['expected_formal_charges']['P']=='-1'
    assert set(projected['_chem_comp_bond.value_dist'])=={'1.5'}
    assert set(projected['_chem_comp_bond.value_dist_esd'])=={'0.02'}
    from nasolve.ligand_profiles import _blocks
    mod=_blocks(tmp_path/'out/site_modifications.cif')[0].values
    assert set(mod['_chem_mod_atom.new_partial_charge'])=={'.'}


def test_source_change_during_preparation_prevents_publication(tmp_path,monkeypatch):
    from nasolve import cif_outgoing_preparation as module
    source,model,contexts,capture,links=fixture(tmp_path)
    original=module.assess_dictionaries
    def changing(*args,**kwargs):
        result=original(*args,**kwargs);source.write_text(source.read_text()+'\n# changed\n');return result
    monkeypatch.setattr(module,'assess_dictionaries',changing)
    with pytest.raises(ValueError,match='Input changed'):
        module.prepare_outgoing_component(source,model,contexts,capture,tmp_path/'out',code='ZZZ',expected_links=links,authority_site='C:1')
    assert not (tmp_path/'out').exists()
