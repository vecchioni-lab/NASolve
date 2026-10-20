"""Graph-selected linear-bond checks distinguish declarations and active terms."""
from copy import deepcopy
import pytest
from nasolve.ligand_profiles import _emit


def fixture(tmp_path,code='Q17'):
    a,b='_chem_comp_atom.','_chem_comp_bond.';names=['L','X','Y','R']
    v={'data_':code,'_chem_comp.id':[code],a+'comp_id':[code]*4,a+'atom_id':names,
       a+'type_symbol':['C']*4,a+'charge':['0']*4,
       a+'pdbx_model_Cartn_x_ideal':['-1.4','0','1.2','2.6'],
       a+'pdbx_model_Cartn_y_ideal':['.001','0','0','.001'],a+'pdbx_model_Cartn_z_ideal':['0']*4,
       b+'comp_id':[code]*3,b+'atom_id_1':names[:-1],b+'atom_id_2':names[1:],
       b+'value_order':['SING','TRIP','SING'],b+'value_dist':['1.4','1.2','1.4'],b+'value_dist_esd':['.02']*3,
       '_chem_comp_angle.comp_id':[code]*2,'_chem_comp_angle.atom_id_1':['L','X'],
       '_chem_comp_angle.atom_id_2':['X','Y'],'_chem_comp_angle.atom_id_3':['Y','R'],
       '_chem_comp_angle.value_angle':['180']*2,'_chem_comp_angle.value_angle_esd':['3']*2}
    src=tmp_path/'source.cif';src.write_text(_emit(v));return src,v


@pytest.mark.parametrize('code',['Q17','PDU','Z99'])
@pytest.mark.parametrize('defect',['none','order','long','weak_bond','missing_angle','bent_target','weak_angle','bent_coordinates','linear_torsion','duplicate'])
def test_explicit_triple_geometry_is_checked_independently_of_component_name(tmp_path,code,defect):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    src,v=fixture(tmp_path,code);candidate=tmp_path/'candidate.cif';c=deepcopy(v)
    if defect=='order':c['_chem_comp_bond.value_order'][1]='SING'
    if defect=='long':c['_chem_comp_bond.value_dist'][1]='1.54'
    if defect=='weak_bond':c['_chem_comp_bond.value_dist_esd'][1]='.2'
    if defect=='missing_angle':c={k:x for k,x in c.items() if not k.startswith('_chem_comp_angle.')}
    if defect=='bent_target':c['_chem_comp_angle.value_angle'][0]='109.5'
    if defect=='weak_angle':c['_chem_comp_angle.value_angle_esd'][0]='30'
    if defect=='bent_coordinates':c['_chem_comp_atom.pdbx_model_Cartn_y_ideal'][-1]='.3'
    if defect=='linear_torsion':
        c.update({'_chem_comp_tor.comp_id':[code],'_chem_comp_tor.id':['t1'],
          **{'_chem_comp_tor.atom_id_'+str(i+1):[name] for i,name in enumerate(['L','X','Y','R'])},
          '_chem_comp_tor.value_angle':['20'],'_chem_comp_tor.value_angle_esd':['30'],'_chem_comp_tor.period':['3']})
    if defect=='duplicate':
        for k,x in list(c.items()):
            if k.startswith('_chem_comp_angle.'):c[k]=x+[x[0]]
    candidate.write_text(_emit(c));before=src.read_bytes(),candidate.read_bytes()
    r=audit_triple_bonds(src,code,dictionary=candidate)
    assert r['status']==('TRIPLE_SCREEN_PASS' if defect=='none' else 'REVIEW')
    assert r['triple_bonds'][0]['atoms']==['X','Y'] and r['automatic_adoption'] is False
    assert (src.read_bytes(),candidate.read_bytes())==before
    if defect=='linear_torsion':assert len(r['linear_axis_torsions'])==1


@pytest.mark.parametrize('defect',['none','missing_bond','missing_angle','duplicate','long','weak','bent','unknown_order','extra_site',
    'nonfinite_weight','negative_weight','nonfinite_target','nonfinite_coordinate','missing_atom','wrong_element','asu'])
def test_native_active_proxies_require_exact_membership_targets_and_positive_weights(tmp_path,defect):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    src,v=fixture(tmp_path);atoms=[{'i_seq':i,'atom_id':name,'element':'C','xyz':[float(v['_chem_comp_atom.pdbx_model_Cartn_'+x+'_ideal'][i]) for x in 'xyz'],
          'identity':{'chain_id':'A','resseq':'1','icode':'','altloc':'','resname':'Q17'}} for i,name in enumerate(v['_chem_comp_atom.atom_id'])]
    native={'status':'REVIEW','atoms':atoms,'geometry':{'status':'RECORDED','proxy_details':{
       'bond_simple':[{'i_seqs':[1,2],'distance_ideal':1.2,'weight':2500.}],
       'bond_asu':[],'angle':[{'i_seqs':[0,1,2],'angle_ideal':180.,'weight':1/9},
                              {'i_seqs':[1,2,3],'angle_ideal':180.,'weight':1/9}],
       'dihedral':[],'const_dihedral':[]}},'monomer_mappings':{'rows':[{'metadata':{'effective_definition':{
          'bonds':[{'atom_id_1':'X','atom_id_2':'Y','type':'triple'}]}}}]}}
    geo=native['geometry']['proxy_details']
    if defect=='missing_bond':geo['bond_simple']=[]
    if defect=='missing_angle':geo['angle'].pop()
    if defect=='duplicate':geo['angle'].append(deepcopy(geo['angle'][0]))
    if defect=='long':geo['bond_simple'][0]['distance_ideal']=1.54
    if defect=='weak':geo['angle'][0]['weight']=.001
    if defect=='bent':atoms[3]['xyz'][1]=.3
    if defect=='unknown_order':native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type']='single'
    if defect=='extra_site':atoms[3]['identity']['resseq']='2'
    if defect=='nonfinite_weight':geo['bond_simple'][0]['weight']=float('nan')
    if defect=='negative_weight':geo['bond_simple'][0]['weight']=-1
    if defect=='nonfinite_target':geo['bond_simple'][0]['distance_ideal']=float('inf')
    if defect=='nonfinite_coordinate':atoms[3]['xyz'][1]=float('nan')
    if defect=='missing_atom':atoms.pop()
    if defect=='wrong_element':atoms[2]['element']='N'
    if defect=='asu':geo['bond_asu']=[{'i_seqs':[1,2]}]
    r=audit_triple_bonds(src,'Q17',native=native)
    assert r['status']==('TRIPLE_SCREEN_PASS' if defect=='none' else 'REVIEW')


def test_no_triple_bond_is_unassessed(tmp_path):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    src,v=fixture(tmp_path);v['_chem_comp_bond.value_order'][1]='SING';src.write_text(_emit(v))
    assert audit_triple_bonds(src,'Q17',dictionary=src)['status']=='UNASSESSED'


def test_nitrile_uses_distinct_length_bounds_and_only_its_graph_neighbors(tmp_path):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    src,v=fixture(tmp_path)
    for k,x in list(v.items()):
        if k.startswith('_chem_comp_atom.'):v[k]=x[:-1]
        if k.startswith('_chem_comp_bond.') or k.startswith('_chem_comp_angle.'):v[k]=x[:-1]
    v['_chem_comp_atom.type_symbol'][-1]='N';v['_chem_comp_bond.value_dist'][-1]='1.16'
    v['_chem_comp_atom.pdbx_model_Cartn_x_ideal'][-1]='1.16';src.write_text(_emit(v))
    r=audit_triple_bonds(src,'Q17',dictionary=src)
    assert r['status']=='TRIPLE_SCREEN_PASS' and len(r['triple_bonds'][0]['angles'])==1


def test_separate_control_pdb_preserves_seed_identity_without_editing_source(tmp_path):
    from nasolve.cif_triple_bond_audit import write_component_control_model
    from Bio.PDB import PDBParser
    folder=tmp_path/'inputs';folder.mkdir();src,v=fixture(folder)
    output=tmp_path/'control/Q17.pdb';before=src.read_bytes()
    r=write_component_control_model(src,'Q17',output)
    atoms=list(PDBParser(QUIET=True).get_structure('control',output).get_atoms())
    assert [a.name for a in atoms]==v['_chem_comp_atom.atom_id']
    assert [tuple(float(x) for x in a.coord) for a in atoms][1]==(0.,0.,0.)
    assert r['experimental_model_used'] is False and src.read_bytes()==before
    with pytest.raises(ValueError):write_component_control_model(src,'Q17',src)
    with pytest.raises(ValueError):write_component_control_model(src,'Q17',output)
