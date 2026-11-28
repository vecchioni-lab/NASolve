"""Independent numerical references do not silently approve or change chemistry."""
from copy import deepcopy
import pytest
from nasolve.ligand_profiles import _emit
from nasolve.cif_linear_bond_reference import linear_bond_query, compare_linear_bond_reference, prepare_linear_bond_candidate
from tests.test_cif_triple_bond_audit import fixture


def reference(query):
    return {'policy_id':'cif-mmff-linear-bond-reference-v1','status':'RECORDED',
            'query':deepcopy(query),'provider':{'name':'RDKit/MMFF94s','version':'synthetic-test-only'},
            'bonds':[{'atoms':pair,'bond_type':0,'atom_types':[4,1],'force_constant':4.7,
                      'equilibrium_angstrom':1.2 if pair==['X','Y'] else 1.459}
                     for pair in query['selected_bonds']],
            'chemical_approval':'NOT_ASSESSED','automatic_adoption':False}


@pytest.mark.parametrize('code',['Q17','PDU','AB'])
@pytest.mark.parametrize('target',['1.607','1.364'])
def test_neighbor_discrepancy_is_reported_without_coordinates_or_residue_rules(tmp_path,code,target):
    source,values=fixture(tmp_path,code)
    # No coordinate family is needed to identify or compare bonds.
    values={k:v for k,v in values.items() if 'cartn' not in k.lower()}
    source.write_text(_emit(values));query=linear_bond_query(source,code)
    values['_chem_comp_bond.value_dist'][-1]=target
    candidate=tmp_path/'dictionary.cif';candidate.write_text(_emit(values));before=(source.read_bytes(),candidate.read_bytes())
    result=compare_linear_bond_reference(source,candidate,code,reference(query))
    row=next(x for x in result['bonds'] if x['atoms']==['R','Y'])
    assert row['target_angstrom']==float(target)
    assert row['reference_equilibrium_angstrom']==1.459
    assert row['target_minus_reference_angstrom']==pytest.approx(float(target)-1.459)
    assert result['status']=='COMPARISON_ONLY' and result['automatic_adoption'] is False
    assert 'PASS' not in result.values() and (source.read_bytes(),candidate.read_bytes())==before


@pytest.mark.parametrize('defect',['source','missing','duplicate','extra','nan','negative','provider','approval'])
def test_unbound_or_malformed_reference_cannot_make_a_candidate(tmp_path,defect):
    source,v=fixture(tmp_path);q=linear_bond_query(source,'Q17');r=reference(q)
    if defect=='source':r['query']['source_sha256']='0'*64
    if defect=='missing':r['bonds'].pop()
    if defect=='duplicate':r['bonds'].append(deepcopy(r['bonds'][0]))
    if defect=='extra':r['bonds'].append(dict(r['bonds'][0],atoms=['L','R']))
    if defect=='nan':r['bonds'][0]['equilibrium_angstrom']=float('nan')
    if defect=='negative':r['bonds'][0]['force_constant']=-1
    if defect=='provider':r['provider']['name']='unidentified'
    if defect=='approval':r['automatic_adoption']=True
    with pytest.raises(ValueError):prepare_linear_bond_candidate(source,source,'Q17',r,tmp_path/'candidate.cif',bonds=[['R','Y']])
    assert not (tmp_path/'candidate.cif').exists()


def test_candidate_changes_only_requested_distance_preserving_esd_and_all_other_fields(tmp_path):
    from nasolve.ligand_profiles import _blocks
    source,v=fixture(tmp_path);q=linear_bond_query(source,'Q17');dictionary=tmp_path/'dictionary.cif'
    v['_chem_comp_bond.value_dist'][-1]='1.607';dictionary.write_text(_emit(v)+'data_other\n_other.value untouched\n')
    before=source.read_bytes(),dictionary.read_bytes();out=tmp_path/'candidate.cif'
    r=prepare_linear_bond_candidate(source,dictionary,'Q17',reference(q),out,bonds=[['Y','R']])
    expected=[deepcopy(b.values) for b in _blocks(dictionary)];expected[0]['_chem_comp_bond.value_dist'][-1]='1.459'
    assert [b.values for b in _blocks(out)]==expected
    assert r['status']=='CANDIDATE_REVIEW' and r['automatic_adoption'] is False
    assert r['scientific_approval']=='NOT_ASSESSED' and r['model_editing']=='NOT_RUN'
    assert (source.read_bytes(),dictionary.read_bytes())==before
    with pytest.raises(FileExistsError):prepare_linear_bond_candidate(source,dictionary,'Q17',reference(q),out,bonds=[['Y','R']])


@pytest.mark.parametrize('defect',['changed_order','changed_charge','missing_esd','zero_esd','extra_selection','duplicate_selection','empty_selection'])
def test_changed_chemistry_or_ambiguous_numeric_edit_refuses(tmp_path,defect):
    source,v=fixture(tmp_path);q=linear_bond_query(source,'Q17');bonds=[['R','Y']]
    if defect=='changed_order':v['_chem_comp_bond.value_order'][0]='DOUB'
    if defect=='changed_charge':v['_chem_comp_atom.charge'][0]='1'
    if defect=='missing_esd':v.pop('_chem_comp_bond.value_dist_esd')
    if defect=='zero_esd':v['_chem_comp_bond.value_dist_esd'][-1]='0'
    if defect=='extra_selection':bonds=[['L','R']]
    if defect=='duplicate_selection':bonds=[['Y','R'],['R','Y']]
    if defect=='empty_selection':bonds=[]
    dictionary=tmp_path/'dictionary.cif';dictionary.write_text(_emit(v))
    with pytest.raises(ValueError):prepare_linear_bond_candidate(source,dictionary,'Q17',reference(q),tmp_path/'candidate.cif',bonds=bonds)
    assert not (tmp_path/'candidate.cif').exists()


def test_historical_triple_pass_does_not_cover_adjacent_single_bond(tmp_path):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds, POLICY_ID
    source,v=fixture(tmp_path);q=linear_bond_query(source,'Q17')
    v['_chem_comp_bond.value_dist'][-1]='1.607'
    candidate=tmp_path/'dictionary.cif';candidate.write_text(_emit(v))
    old=audit_triple_bonds(source,'Q17',dictionary=candidate)
    assert old['policy_id']==POLICY_ID=='cif-declared-triple-bond-screen-v1'
    assert old['status']=='TRIPLE_SCREEN_PASS'
    new=compare_linear_bond_reference(source,candidate,'Q17',reference(q))
    row=next(r for r in new['bonds'] if r['atoms']==['R','Y'])
    assert row['difference_over_dictionary_esd']==pytest.approx(7.4)
    assert new['acceptance_threshold']=='NOT_ASSIGNED'


@pytest.mark.parametrize('defect',['missing_charge','fractional_charge','ambiguous_order','nonfinite_esd','overflow','provider_shape'])
def test_undefined_chemistry_and_nonfinite_comparison_refuse(tmp_path,defect):
    source,v=fixture(tmp_path)
    if defect=='missing_charge':v.pop('_chem_comp_atom.charge')
    if defect=='fractional_charge':v['_chem_comp_atom.charge'][0]='0.5'
    if defect=='ambiguous_order':v['_chem_comp_bond.value_order'][0]='DELOC'
    if defect in {'missing_charge','fractional_charge','ambiguous_order'}:
        source.write_text(_emit(v))
        with pytest.raises(ValueError):linear_bond_query(source,'Q17')
        return
    r=reference(linear_bond_query(source,'Q17'))
    if defect=='nonfinite_esd':v['_chem_comp_bond.value_dist_esd'][0]='nan'
    if defect=='overflow':v['_chem_comp_bond.value_dist_esd'][0]='1e-323'
    if defect=='provider_shape':r['provider']=[]
    candidate=tmp_path/'candidate.cif';candidate.write_text(_emit(v))
    with pytest.raises(ValueError):compare_linear_bond_reference(source,candidate,'Q17',r)


def test_nitrile_and_atom_renaming_use_connectivity_not_methyl_names(tmp_path):
    source,v=fixture(tmp_path,'ABC')
    rename={'L':'O9','X':'C10','Y':'N11','R':'H12'}
    for key,values in v.items():
        if key.endswith('atom_id') or '.atom_id_' in key:
            v[key]=[rename.get(x,x) for x in values]
    v['_chem_comp_atom.type_symbol']=['O','C','N','H']
    source.write_text(_emit(v));q=linear_bond_query(source,'ABC')
    assert q['selected_bonds']==[['C10','N11'],['C10','O9']]


def test_candidate_keeps_full_reference_precision_and_unselected_bonds(tmp_path):
    from nasolve.cif_linked_preparation import component_values
    source,v=fixture(tmp_path);r=reference(linear_bond_query(source,'Q17'))
    target=1.459123456789123
    next(x for x in r['bonds'] if x['atoms']==['R','Y'])['equilibrium_angstrom']=target
    out=tmp_path/'candidate.cif'
    prepare_linear_bond_candidate(source,source,'Q17',r,out,bonds=[['R','Y']])
    values=component_values(out,'Q17')
    assert float(values['_chem_comp_bond.value_dist'][-1])==target
    assert values['_chem_comp_bond.value_dist'][:-1]==v['_chem_comp_bond.value_dist'][:-1]


def test_separate_nuclear_target_and_symlink_output_cannot_be_silently_edited(tmp_path):
    source,v=fixture(tmp_path);r=reference(linear_bond_query(source,'Q17'))
    v['_chem_comp_bond.value_dist_nucleus']=['1.4','1.2','1.4']
    dictionary=tmp_path/'dictionary.cif';dictionary.write_text(_emit(v))
    with pytest.raises(ValueError,match='nuclear'):
        prepare_linear_bond_candidate(source,dictionary,'Q17',r,tmp_path/'candidate.cif',bonds=[['R','Y']])
    assert not (tmp_path/'candidate.cif').exists()
    folder=tmp_path/'folder';folder.mkdir();alias=tmp_path/'alias';alias.symlink_to(folder,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        prepare_linear_bond_candidate(source,source,'Q17',r,alias/'candidate.cif',bonds=[['R','Y']])
    assert not (folder/'candidate.cif').exists()


def energy_inputs(tmp_path,code='Q17'):
    source,v=fixture(tmp_path,code)
    a,b='_chem_comp_atom.','_chem_comp_bond.'
    # L is a source-declared methyl carbon; X has an explicit triple bond to Y.
    for key in list(v):
        if key.startswith(a):
            if key==a+'atom_id':v[key]+= ['H1','H2','H3']
            elif key==a+'comp_id':v[key]+=[code]*3
            elif key==a+'type_symbol':v[key]+=['H']*3
            else:v[key]+=['0']*3
    v[a+'type_energy']=['CH3','CSP','CSP','C','HCH3','HCH3','HCH3']
    for key in list(v):
        if key.startswith(b):
            if key==b+'atom_id_1':v[key]+=['L']*3
            elif key==b+'atom_id_2':v[key]+=['H1','H2','H3']
            elif key==b+'comp_id':v[key]+=[code]*3
            elif key==b+'value_order':v[key]+=['SING']*3
            elif key==b+'value_dist':v[key]+=['1.09']*3
            else:v[key]+=['.02']*3
    v[b+'value_dist'][0]='1.607';source.write_text(_emit(v))
    lib=tmp_path/'energy.cif'
    library={'data_':'energy','_lib_atom.type':['CSP','CH3'],'_lib_atom.element':['C','C'],
      '_lib_atom.valency':['4','4'],'_lib_atom.sp':['1','3'],
      '_lib_bond.atom_type_1':['CH3'],'_lib_bond.atom_type_2':['CSP'],'_lib_bond.type':['single'],
      '_lib_bond.const':['405'],'_lib_bond.length':['1.470'],'_lib_bond.value_esd':['.020']}
    lib.write_text(_emit(library));return source,v,lib,library


@pytest.mark.parametrize('code',['Q17','XYZ'])
def test_exact_energy_library_reference_is_graph_typed_and_keeps_unsupported_neighbors(tmp_path,code):
    from nasolve.cif_linear_bond_reference import energy_library_linear_reference
    source,v,lib,lv=energy_inputs(tmp_path,code)
    before=source.read_bytes(),lib.read_bytes()
    r=energy_library_linear_reference(source,source,code,lib)
    supported=[x for x in r['bonds'] if x['status']=='SUPPORTED']
    assert len(r['bonds'])==3 and len(supported)==1
    row=supported[0];assert row['atoms']==['L','X'] and row['equilibrium_angstrom']==1.47
    assert row['reference_esd_angstrom']==.02 and row['atom_types']==['CH3','CSP']
    comparison=compare_linear_bond_reference(source,source,code,r)
    assert len([b for b in comparison['bonds'] if b['reference_status']=='UNSUPPORTED'])==2
    out=tmp_path/'candidate.cif'
    plan=prepare_linear_bond_candidate(source,source,code,r,out,bonds=[['L','X']])
    assert plan['changes'][0]['reference_equilibrium_angstrom']==1.47
    assert (source.read_bytes(),lib.read_bytes())==before
    with pytest.raises(ValueError):prepare_linear_bond_candidate(source,source,code,r,tmp_path/'bad.cif',bonds=[['X','Y']])


@pytest.mark.parametrize('defect',['wildcard','duplicate','wrong_order','missing_sigma','wrong_element','wrong_hybrid','wrong_type','charged'])
def test_energy_reference_refuses_unmatched_types_or_unqualified_rows(tmp_path,defect):
    from nasolve.cif_linear_bond_reference import energy_library_linear_reference
    source,v,lib,lv=energy_inputs(tmp_path)
    if defect=='wildcard':lv['_lib_bond.atom_type_2']=['.']
    if defect=='duplicate':
        for k,x in list(lv.items()):
            if k.startswith('_lib_bond.'):lv[k]=x+x
    if defect=='wrong_order':lv['_lib_bond.type']=['double']
    if defect=='missing_sigma':lv['_lib_bond.value_esd']=['.']
    if defect=='wrong_element':lv['_lib_atom.element'][0]='N'
    if defect=='wrong_hybrid':lv['_lib_atom.sp'][0]='2'
    if defect=='wrong_type':v['_chem_comp_atom.type_energy'][0]='CR6'
    if defect=='charged':v['_chem_comp_atom.charge'][0]='1'
    lib.write_text(_emit(lv));source.write_text(_emit(v))
    r=energy_library_linear_reference(source,source,'Q17',lib)
    assert not [x for x in r['bonds'] if x['status']=='SUPPORTED']
    with pytest.raises(ValueError):prepare_linear_bond_candidate(source,source,'Q17',r,tmp_path/'candidate.cif',bonds=[['L','X']])
    assert not (tmp_path/'candidate.cif').exists()


def test_supplied_library_receipt_cannot_reclassify_a_triple_as_a_single_bond(tmp_path):
    from nasolve.cif_linear_bond_reference import energy_library_linear_reference
    source,v,lib,lv=energy_inputs(tmp_path)
    r=energy_library_linear_reference(source,source,'Q17',lib)
    bad=next(b for b in r['bonds'] if b['atoms']==['X','Y'])
    bad.clear();bad.update(atoms=['X','Y'],status='SUPPORTED',atom_types=['CSP','CSP'],bond_type='SINGLE',
       force_constant=200.,equilibrium_angstrom=1.377,reference_esd_angstrom=.012,
       library_bond_row=dict(atom_type_1='CSP',atom_type_2='CSP',type='single',const='200',length='1.377',value_esd='.012'))
    with pytest.raises(ValueError,match='neighborhood'):
        prepare_linear_bond_candidate(source,source,'Q17',r,tmp_path/'candidate.cif',bonds=[['X','Y']])
    assert not (tmp_path/'candidate.cif').exists()
