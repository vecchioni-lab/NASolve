"""Source-relative handedness is distinct from absolute CIP and convergence."""
from copy import deepcopy
import pytest
from nasolve.ligand_profiles import _emit


def tetrahedron(code='Q17'):
    a,b='_chem_comp_atom.','_chem_comp_bond.'
    v={'data_':'comp_'+code,'_chem_comp.id':[code],a+'comp_id':[code]*5,
       a+'atom_id':['CTR','O','N','C','H'],a+'type_symbol':['C','O','N','C','H'],
       a+'charge':['0']*5,a+'pdbx_stereo_config':['R','N','N','N','N'],
       a+'pdbx_model_Cartn_x_ideal':['0','1','0','0','-1'],
       a+'pdbx_model_Cartn_y_ideal':['0','0','1','0','-1'],
       a+'pdbx_model_Cartn_z_ideal':['0','0','0','1','-1'],
       b+'comp_id':[code]*4,b+'atom_id_1':['CTR']*4,b+'atom_id_2':['O','N','C','H'],
       b+'value_order':['SING']*4}
    g=deepcopy(v)
    for axis in 'xyz':g[a+axis]=g[a+'pdbx_model_Cartn_'+axis+'_ideal']
    p='_chem_comp_chir.'
    g.update({p+'comp_id':[code],p+'id':['s1'],p+'atom_id_centre':['CTR'],
              p+'atom_id_1':['O'],p+'atom_id_2':['N'],p+'atom_id_3':['C'],p+'volume_sign':['positiv']})
    return v,g


def write(path,values):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(_emit(values));return path


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('defect',['none','omitted','inverted','wrong_target','both','missing_term','wrong_label','unknown_coords','flat','not_neighbor'])
def test_handedness_audit_keeps_metadata_geometry_and_absolute_assignment_separate(tmp_path,code,defect):
    from nasolve.cif_stereochemistry_audit import audit_candidate_stereochemistry
    v,g=tetrahedron(code);a,p='_chem_comp_atom.','_chem_comp_chir.'
    if defect=='omitted':del g[a+'pdbx_stereo_config']
    if defect=='inverted':g[a+'z']=[str(-float(x)) for x in g[a+'z']]
    if defect=='wrong_target':g[p+'volume_sign']=['negativ']
    if defect=='both':g[p+'volume_sign']=['both']
    if defect=='missing_term':g={k:x for k,x in g.items() if not k.startswith(p)}
    if defect=='wrong_label':g[a+'pdbx_stereo_config'][0]='S'
    if defect=='unknown_coords':v[a+'pdbx_model_Cartn_z_ideal'][1]='?'
    if defect=='flat':g[a+'z']=['0']*5
    if defect=='not_neighbor':g[p+'atom_id_3']=['CTR']
    src,out=write(tmp_path/'src.cif',v),write(tmp_path/'out.cif',g);before=src.read_bytes(),out.read_bytes()
    if defect=='not_neighbor':
        with pytest.raises(ValueError):audit_candidate_stereochemistry(src,out,code)
        return
    r=audit_candidate_stereochemistry(src,out,code)
    assert (src.read_bytes(),out.read_bytes())==before
    assert r['absolute_cip_assignment']=='NOT_RUN' and r['automatic_adoption'] is False
    assert r['convergence']=='NOT_ASSESSED' and len(r['centres'])==1
    if defect=='none':assert r['status']=='SOURCE_RELATIVE_STEREO_PASS'
    elif defect in {'omitted','both','missing_term','unknown_coords'}:assert r['status']=='REVIEW'
    else:assert r['status']=='REJECTED'
    if defect=='omitted':
        assert r['centres'][0]['atom_label']=='OMITTED'
        assert r['centres'][0]['terms'][0]['coordinate_handedness']=='PRESERVED'


def test_unknown_reader_markers_are_not_converted_to_nonchiral(tmp_path):
    from nasolve.cif_stereochemistry_audit import reader_stereo_inventory
    v,_=tetrahedron();v['_chem_comp_atom.pdbx_stereo_config']=['?']*5
    src=write(tmp_path/'src.cif',v);r=reader_stereo_inventory(src,'Q17')
    assert len(r['unknown_markers'])==5
    assert r['unknown_markers_without_four_declared_neighbors']==['C','H','N','O']
    assert r['atoms']['CTR']['declared_neighbors']==['C','H','N','O']
    assert src.read_text().count('?')==5 and r['stereochemistry_inferred'] is False


@pytest.mark.parametrize('defect',['changed_charge','changed_element','changed_order','conflicting_alias'])
def test_handedness_never_overrides_chemical_mismatch(tmp_path,defect):
    from nasolve.cif_stereochemistry_audit import audit_candidate_stereochemistry
    v,g=tetrahedron()
    if defect=='changed_charge':g['_chem_comp_atom.charge'][1]='-1'
    if defect=='changed_element':g['_chem_comp_atom.type_symbol'][1]='S'
    if defect=='changed_order':g['_chem_comp_bond.value_order'][0]='DOUB'
    if defect=='conflicting_alias':g['_chem_comp_atom.stereo_config']=['S','N','N','N','N']
    src,out=write(tmp_path/'src.cif',v),write(tmp_path/'out.cif',g)
    if defect=='conflicting_alias':
        with pytest.raises(ValueError):audit_candidate_stereochemistry(src,out,'Q17')
    else:assert audit_candidate_stereochemistry(src,out,'Q17')['status']=='REJECTED'


def test_trajectory_records_energy_rises_and_does_not_infer_convergence():
    from nasolve.cif_stereochemistry_audit import audit_optimizer_log
    log='''Time      Energy        delta E    RMS         Max      Step size
 0:00  1.    -20.0000
 0:01  2.    -22.0000   -2.0000     0.0200*    0.1000     0.0005  0:00
 0:02  3.    -12.0000   10.0000     0.0200*    0.1000     0.0005  0:00
DONE Steps:3   deltaE:10.0000   RMS:(0.02,0.10)   Error Norm:0.000
geometry not converged
'''
    r=audit_optimizer_log(log)
    assert r['rows']==3 and r['lowest_printed_energy']['iteration']==2
    assert r['largest_adjacent_increase']['energy_change']==10
    assert r['stopping']=='NOT_CONVERGED_REPORTED' and r['convergence_claimed'] is False
    assert audit_optimizer_log('DONE')['stopping']=='NOT_REPORTED'


def test_multiple_optimizer_tables_are_not_concatenated_into_one_trial():
    from nasolve.cif_stereochemistry_audit import audit_optimizer_log
    r=audit_optimizer_log('Time Energy delta E\n 0:00 1. -20.0\nTime Energy delta E\n 0:00 1. -10.0\n')
    assert r['status']=='REVIEW' and r['table_count']==2
    assert r['largest_adjacent_increase'] is None
