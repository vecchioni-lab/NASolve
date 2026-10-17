"""Full source rows and unaffected native proxies cannot hide behind counts."""
from copy import deepcopy
from pathlib import Path
import runpy

import pytest


def case(tmp_path):
    helper=runpy.run_path(str(Path(__file__).with_name('test_cif_linked_qualification.py')))['native_case']
    before,after,prepared,links,ends=helper()
    for native in [before,after]:
        definition=native['monomer_mappings']['rows'][1]['metadata']['effective_definition']
        definition['bonds'][0].update(type='single',value_dist=1.5,value_dist_esd=.02,value_dist_neutron=1.51)
        native['monomer_mappings']['rows'][0]['metadata']['effective_definition']={
            'atoms':[{'atom_id':"O3'",'type_symbol':'O'},{'atom_id':"C3'",'type_symbol':'C'}],
            'bonds':[{'atom_id_1':"O3'",'atom_id_2':"C3'"}]}
    text='''data_comp_list
loop_
_chem_comp.id
_chem_comp.group
IGU DNA
data_comp_IGU
loop_
_chem_comp_atom.comp_id
_chem_comp_atom.atom_id
_chem_comp_atom.type_symbol
_chem_comp_atom.type_energy
_chem_comp_atom.charge
IGU P O X 0
IGU "O3'" O OC2 0
IGU OP2 O X 0
IGU keepH H X 0
loop_
_chem_comp_bond.comp_id
_chem_comp_bond.atom_id_1
_chem_comp_bond.atom_id_2
_chem_comp_bond.type
_chem_comp_bond.value_dist
_chem_comp_bond.value_dist_esd
_chem_comp_bond.value_dist_neutron
IGU OP2 keepH single 1.5 0.02 1.51
'''
    path=tmp_path/'projection.cif';path.write_text(text)
    return before,after,prepared,links,ends,{'A:2':(path,'IGU')}


def test_complete_projection_and_existing_gates_are_both_required(tmp_path):
    from nasolve.cif_terminal_qualification import qualify_terminal_bundle
    result=qualify_terminal_bundle(*case(tmp_path))
    assert result['status']=='TERMINAL_BUNDLE_MECHANICS_PASS'
    assert result['automatic_adoption'] is False and result['achieved_model_geometry']=='NOT_RUN'


@pytest.mark.parametrize('defect',['hydrogen_target','neutron_target','atom_type','extra_plane',
    'unselected_definition','unaffected_proxy','formal_unavailable'])
def test_matching_counts_cannot_hide_a_terminal_bundle_defect(tmp_path,defect):
    from nasolve.cif_terminal_qualification import qualify_terminal_bundle
    values=case(tmp_path);before,after,_,_,_,_=values
    definition=after['monomer_mappings']['rows'][1]['metadata']['effective_definition']
    if defect=='hydrogen_target':definition['bonds'][0]['value_dist']=1.6
    elif defect=='neutron_target':definition['bonds'][0]['value_dist_neutron']=1.52
    elif defect=='atom_type':definition['atoms'][0]['type_energy']='wrong'
    elif defect=='extra_plane':definition['plane_atoms'].append({'plane_id':'extra','atom_id':'P','dist_esd':.1})
    elif defect=='unselected_definition':after['monomer_mappings']['rows'][0]['metadata']['effective_definition']={'changed':True}
    elif defect=='unaffected_proxy':
        row={'i_seqs':[0,3],'atoms':['0','3'],'distance_ideal':2.,'weight':100.}
        before['geometry']['proxy_details']['bond_simple'].append(row)
        after['geometry']['proxy_details']['bond_simple'].append(dict(row,weight=101.))
    elif defect=='formal_unavailable':definition['atoms'][0]['charge']=None
    result=qualify_terminal_bundle(*values)
    assert result['status']=='REVIEW'
    if defect=='formal_unavailable':
        assert next(r for r in result['checks'] if r['check']=='effective-site-formal-charges:A:2')['status']=='UNSUPPORTED'


@pytest.mark.parametrize('defect',['target','sigma','alternate','quartet'])
def test_reviewed_torsion_requires_exact_native_proxy_and_alternate(tmp_path,defect):
    from nasolve.cif_terminal_qualification import reviewed_torsion_proxy_check
    before,after,_,_,_,projections=case(tmp_path)
    path=projections['A:2'][0]
    with path.open('a') as handle:handle.write('''loop_
_chem_comp_tor.comp_id
_chem_comp_tor.id
_chem_comp_tor.atom_id_1
_chem_comp_tor.atom_id_2
_chem_comp_tor.atom_id_3
_chem_comp_tor.atom_id_4
_chem_comp_tor.value_angle
_chem_comp_tor.alt_value_angle
_chem_comp_tor.value_angle_esd
_chem_comp_tor.period
IGU reviewed P "O3'" OP2 keepH 340.7 2.8 6.3 1
''')
    native={'atoms':[{'i_seq':i,'atom_id':name,'identity':{'chain_id':'A','resseq':'2','icode':''}}
                     for i,name in enumerate(['P',"O3'",'OP2','keepH'])],
        'geometry':{'proxy_details':{'dihedral':[{'i_seqs':[0,1,2,3],
            'angle_ideal':340.7,'weight':1/6.3**2,'periodicity':1,'alt_angle_ideals':[2.8]}]}}}
    assert reviewed_torsion_proxy_check(native,path,'IGU','A:2','reviewed')['status']=='PASS'
    row=native['geometry']['proxy_details']['dihedral'][0]
    if defect=='target':row['angle_ideal']=341.
    elif defect=='sigma':row['weight']=1/6.1**2
    elif defect=='alternate':row['alt_angle_ideals']=[]
    else:row['i_seqs']=[0,1,2,2]
    assert reviewed_torsion_proxy_check(native,path,'IGU','A:2','reviewed')['status']=='REVIEW'


def test_outgoing_link_audit_uses_element_and_adjacency_not_hydrogen_spelling():
    from nasolve.cif_terminal_qualification import declared_outgoing_hydrogen_checks
    definition={'atoms':[{'atom_id':"O3'",'type_symbol':'O','type_energy':'OH1'},
        {'atom_id':'misleading_C','type_symbol':'H'}],
        'bonds':[{'atom_id_1':"O3'",'atom_id_2':'misleading_C'}]}
    native={'monomer_mappings':{'rows':[{'site':'A:7','metadata':{'effective_definition':definition}}]}}
    result=declared_outgoing_hydrogen_checks(native,[('A:7','A:8')])
    assert result[0]['status']=='REVIEW' and result[0]['observed_hydrogens']==['misleading_C']
    assert declared_outgoing_hydrogen_checks(native,[])==[]
