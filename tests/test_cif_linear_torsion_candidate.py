"""Omit only graph-undefined torsions in a separate, review-only candidate."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from nasolve.ligand_profiles import _emit, _blocks
from tests.test_cif_triple_bond_audit import fixture


def dictionary(tmp_path, code='Q17'):
    source, v = fixture(tmp_path, code)
    # One invalid torsion and a valid torsion away from the triple bond.
    a, b, t = '_chem_comp_atom.', '_chem_comp_bond.', '_chem_comp_tor.'
    for k in list(v):
        if k.startswith(a):
            v[k] += ['C' if k.endswith('type_symbol') else code if k.endswith('comp_id') else
                     'S' if k.endswith('atom_id') else '0']
    for k in list(v):
        if k.startswith(b):
            v[k] += [code if k.endswith('comp_id') else 'R' if k.endswith('atom_id_1') else
                     'S' if k.endswith('atom_id_2') else 'SING' if k.endswith('value_order') else '.02' if k.endswith('esd') else '1.4']
    v.update({t+'comp_id':[code]*2,t+'id':['bad','good'],
              t+'atom_id_1':['L','L'],t+'atom_id_2':['X','X'],
              t+'atom_id_3':['Y','R'],t+'atom_id_4':['R','S'],
              t+'value_angle':['20','30'],t+'value_angle_esd':['30']*2,t+'period':['3']*2,
              t+'details':['preserve omitted row evidence','retain unknown field']})
    # The retained row need not be bonded: only selected removals require a
    # consecutive graph path; unrelated dictionary defects are not repaired.
    v['_custom.note']=['Unknown categories survive']
    source.write_text(_emit(v)+'data_unrelated\n_custom.value kept\n')
    return source, v


@pytest.mark.parametrize('code',['Q17','PDU','Z99'])
@pytest.mark.parametrize('reverse',[False,True])
def test_graph_and_declared_target_select_without_coordinates_or_names(tmp_path,code,reverse):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    source,v=dictionary(tmp_path,code)
    if reverse:
        for i in (1,2):
            left,right='_chem_comp_tor.atom_id_'+str(i),'_chem_comp_tor.atom_id_'+str(5-i)
            v[left][0],v[right][0]=v[right][0],v[left][0]
        # Very bent seed coordinates must not change the graph rule.
        v['_chem_comp_atom.pdbx_model_Cartn_y_ideal'][0]='500'
        source.write_text(_emit(v)+'data_unrelated\n_custom.value kept\n')
    original=source.read_bytes();out=tmp_path/'candidate/out.cif'
    r=prepare_linear_torsion_candidate(source,code,out)
    after=_blocks(out)
    assert r['status']=='CANDIDATE_REVIEW' and r['removed_torsion_count']==1
    assert r['parsed_allowlist_pass'] and r['automatic_adoption'] is False
    assert after[0].values['_chem_comp_tor.id']==['good']
    assert after[0].values['_chem_comp_tor.details']==['retain unknown field']
    assert after[0].values['_custom.note']==v['_custom.note']
    assert after[1].text==_blocks(source)[1].text and source.read_bytes()==original


@pytest.mark.parametrize('defect',['single','bent_target','missing_angle','duplicate_angle','weak_angle','branch','bad_path','missing_tor_column'])
def test_ambiguous_or_unsupported_declarations_never_write_candidate(tmp_path,defect):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    source,v=dictionary(tmp_path)
    if defect=='single':v['_chem_comp_bond.value_order'][1]='SING'
    if defect=='bent_target':v['_chem_comp_angle.value_angle'][0]='179.9'
    if defect=='missing_angle':v={k:x for k,x in v.items() if not k.startswith('_chem_comp_angle.')}
    if defect=='duplicate_angle':
        for k in list(v):
            if k.startswith('_chem_comp_angle.'):v[k].append(v[k][0])
    if defect=='weak_angle':v['_chem_comp_angle.value_angle_esd'][0]='0'
    if defect=='branch':v['_chem_comp_bond.atom_id_1'][-1]='X'
    if defect=='bad_path':v['_chem_comp_tor.atom_id_4'][0]='S'
    if defect=='missing_tor_column':del v['_chem_comp_tor.period']
    source.write_text(_emit(v));out=tmp_path/'candidate/out.cif'
    with pytest.raises(ValueError):prepare_linear_torsion_candidate(source,'Q17',out)
    assert not out.exists()


def inventory():
    tors=[{'id':'bad','atom_id_1':'L','atom_id_2':'X','atom_id_3':'Y','atom_id_4':'R',
           'value_angle':20.,'value_angle_esd':30.,'period':3}]
    proxy={'i_seqs':[0,1,2,3],'angle_ideal':20.,'weight':1/900,'periodicity':3,'alt_angle_ideals':None,'origin_id':0}
    r={'atoms':[{'i_seq':i,'atom_id':n,'identity':{'resname':'Q17','chain_id':'A','resseq':'1'}} for i,n in enumerate(['L','X','Y','R'])],
       'atom_count':4,'status':'REVIEW','fatal_problems':None,'unused_definitions':[],'unsupported_fields':[],
       'installed_api_sources':[{'sha256':'same'}],'restraint_policy':{'secondary_structure_enabled':False},
       'monomer_mappings':{'rows':[{'metadata':{'effective_definition':{'torsions':tors,'bonds':['unchanged']}}}]},
       'geometry':{'proxy_counts':{'dihedral':1,'const_dihedral':0,'angle':1},
                   'proxy_details':{'dihedral':[proxy],'const_dihedral':[],'angle':[{'angle_ideal':180.}]},'sites_cart_exact':[[0,0,0]]*4}}
    return r


@pytest.mark.parametrize('defect',['none','bond','angle','unrelated_proxy','charge','atom','api','policy','count','replacement_torsion','stereo'])
def test_native_delta_is_exact_and_keeps_every_unrelated_field(tmp_path,defect):
    from nasolve.cif_linear_torsion_candidate import qualify_linear_torsion_candidate
    source,v=dictionary(tmp_path);before=inventory();after=deepcopy(before)
    after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions']=[]
    after['geometry']['proxy_counts']['dihedral']=0;after['geometry']['proxy_details']['dihedral']=[]
    if defect=='bond':after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds']=[]
    if defect=='angle':after['geometry']['proxy_details']['angle'][0]['angle_ideal']=179.
    if defect=='unrelated_proxy':after['geometry']['proxy_details']['parallelity']=[{'weight':1.}]
    if defect=='charge':after['monomer_mappings']['rows'][0]['metadata']['formal_charge_readback']=-2
    if defect=='atom':after['atoms'][0]['atom_id']='OTHER'
    if defect=='api':after['installed_api_sources'][0]['sha256']='changed'
    if defect=='policy':after['restraint_policy']['secondary_structure_enabled']=True
    if defect=='count':after['geometry']['proxy_counts']['dihedral']=1
    if defect=='replacement_torsion':after['geometry']['proxy_details']['dihedral']=[{'i_seqs':[3,2,1,0]}]
    if defect=='stereo':after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['chirality']=[]
    removed=[{k:v[0] for k,v in v.items() if k.startswith('_chem_comp_tor.')}]
    r=qualify_linear_torsion_candidate(before,after,{'component':'Q17','removed_torsions':removed})
    assert r['mechanics_checks_pass'] is (defect=='none')
    assert r['status']=='REVIEW' and not r['automatic_adoption']
    if defect=='none':assert r['removed_native_proxy_counts']=={'dihedral':1,'const_dihedral':0}


def test_output_is_fresh_separate_and_never_overwrites(tmp_path):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    source,_=dictionary(tmp_path)
    for out in (source,tmp_path/'alias.cif'):
        if out!=source:out.symlink_to(source)
        with pytest.raises(ValueError):prepare_linear_torsion_candidate(source,'Q17',out)


def test_removing_last_torsion_deletes_only_that_loop(tmp_path):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    source,v=dictionary(tmp_path)
    for k in list(v):
        if k.startswith('_chem_comp_tor.'):v[k]=v[k][:1]
    source.write_text(_emit(v));out=tmp_path/'candidate.cif'
    prepare_linear_torsion_candidate(source,'Q17',out)
    actual=_blocks(out)[0].values
    assert actual=={k:x for k,x in v.items() if not k.startswith('_chem_comp_tor.')}


@pytest.mark.parametrize('defect',['duplicate_torsion','nonfinite_target','nonfinite_esd','fractional_period'])
def test_selected_rows_need_unambiguous_finite_function_parameters(tmp_path,defect):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    source,v=dictionary(tmp_path)
    if defect=='duplicate_torsion':
        for k in list(v):
            if k.startswith('_chem_comp_tor.'):v[k].append(v[k][0])
    if defect=='nonfinite_target':v['_chem_comp_tor.value_angle'][0]='nan'
    if defect=='nonfinite_esd':v['_chem_comp_tor.value_angle_esd'][0]='inf'
    if defect=='fractional_period':v['_chem_comp_tor.period'][0]='1.5'
    source.write_text(_emit(v));out=tmp_path/'candidate.cif'
    with pytest.raises(ValueError):prepare_linear_torsion_candidate(source,'Q17',out)
    assert not out.exists()
