"""Generic source conflicts produce isolated graph-seeded numerical candidates."""
from copy import deepcopy
import hashlib,json,math,os
from pathlib import Path
import pytest
from nasolve.ligand_profiles import _emit,_blocks
from tests.test_cif_generation import component,write,program

ROOT=Path(__file__).resolve().parents[1]

def source_values(code='ZZZ'):
    v=component(code,numerical=True)
    names=['NQ',"C'",'C2','C3']
    for key in list(v):
        if key.startswith(('_chem_comp_angle.','_chem_comp_bond.')):v.pop(key)
    v.update({'_chem_comp_atom.atom_id':names,'_chem_comp_atom.type_symbol':['N','C','C','C'],
        '_chem_comp_atom.type_energy':['NT','C','C','C'],
        '_chem_comp_bond.comp_id':[code]*3,'_chem_comp_bond.atom_id_1':['NQ']*3,
        '_chem_comp_bond.atom_id_2':names[1:],'_chem_comp_bond.type':['SINGLE']*3,
        '_chem_comp_bond.aromatic':['N']*3,'_chem_comp_bond.value_dist':['1.4']*3,
        '_chem_comp_bond.value_dist_esd':['.02']*3,
        '_chem_comp_angle.comp_id':[code]*3,'_chem_comp_angle.atom_id_1':[names[1],names[1],names[2]],
        '_chem_comp_angle.atom_id_2':['NQ']*3,'_chem_comp_angle.atom_id_3':[names[2],names[3],names[3]],
        '_chem_comp_angle.value_angle':['109.471','120.772','109.471'],
        '_chem_comp_angle.value_angle_esd':['3','1.58','3'],
        '_chem_comp_plane_atom.comp_id':[code]*4,'_chem_comp_plane_atom.plane_id':['base']*4,
        '_chem_comp_plane_atom.atom_id':names,'_chem_comp_plane_atom.dist_esd':['.02']*4})
    return v

@pytest.mark.parametrize('code',['ZZZ','R17','DP'])
def test_conflict_selection_uses_declared_restraints_not_code_or_model_residual(tmp_path,code):
    from nasolve.cif_numerical_recovery import plan_numerical_recovery
    p=write(tmp_path/'source.cif',source_values(code));native={'monomer_mappings':{'rows':[{'site':'Q:7','resname':code,'chem_mod_ids':{'status':'RECORDED','ids':['KEEP']}}]}}
    r=plan_numerical_recovery(native,[p]);assert r['recovery_codes']==[code] and r['selected'][0]['sites']==['Q:7']
    assert r['selected'][0]['source_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
    assert r['selected'][0]['site_modifiers']['Q:7']['ids']==['KEEP']
    assert r['selected'][0]['findings'][0]['measurements']['centre']=='NQ'
    assert r['automatic_adoption'] is False and r['linked_site_validation']=='NOT_RUN'
    good=source_values(code);good['_chem_comp_angle.value_angle']=['120']*3;p.write_text(_emit(good))
    assert plan_numerical_recovery(native,[p])['selected']==[]

@pytest.mark.parametrize('coordinates',['ideal','declared'])
def test_graph_seed_drops_all_old_targets_types_but_preserves_chemical_declarations(tmp_path,coordinates):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    from nasolve.cif_generation import _ideal_seed
    from nasolve.cif_doctor import compare_dictionaries
    v=source_values();v['_chem_comp_atom.pdbx_stereo_config']=['N']*4
    v['_chem_comp_atom.partial_charge']=['.1']*4
    if coordinates=='declared':
        for axis in 'xyz':v['_chem_comp_atom.'+axis]=v.pop('_chem_comp_atom.pdbx_model_Cartn_'+axis+'_ideal')
    source=write(tmp_path/'source.cif',v);before=source.read_bytes();output=tmp_path/'seed/source.cif'
    r=prepare_graph_generation_source(source,'ZZZ',output);values={k.lower():v for k,v in _blocks(output)[0].values.items()}
    assert not any(k.startswith(('_chem_comp_angle.','_chem_comp_tor.','_chem_comp_plane_atom.')) for k in values)
    assert '_chem_comp_atom.type_energy' not in values and '_chem_comp_bond.value_dist' not in values
    assert values['_chem_comp_bond.type']==['SINGLE']*3 and values['_chem_comp_atom.partial_charge']==['.1']*4
    assert source.read_bytes()==before and r['source_preserved'] and r['chemical_comparison']['status']=='EXACT_DECLARATIONS'
    seed,receipt=_ideal_seed(output,'ZZZ');assert "C'" in seed and receipt['experimental_model_used'] is False
    assert r['coordinate_origin']==('SOURCE_IDEAL_COORDINATES' if coordinates=='ideal' else 'SOURCE_DECLARED_COORDINATES_NOT_INDEPENDENT_IDEAL')
    assert r['numerical_parameters']=='REMOVED_FOR_INDEPENDENT_GENERATION'
    assert not [x for x in compare_dictionaries([source],[output])['differences'] if x['field'] in r['chemical_comparison']['fields']]

@pytest.mark.parametrize('defect',['partial_ideal','missing_coords','nonfinite','missing_charge','bad_charge','disagreeing_charge','duplicate_atom','multi_component','existing','symlink','inside_source'])
def test_ambiguous_or_lossy_seed_refuses_before_generation(tmp_path,defect):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    v=source_values();out=tmp_path/'seed/graph.cif'
    if defect=='partial_ideal':v.pop('_chem_comp_atom.pdbx_model_Cartn_z_ideal');v['_chem_comp_atom.z']=['0']*4
    if defect=='missing_coords':
        for axis in 'xyz':v.pop('_chem_comp_atom.pdbx_model_Cartn_'+axis+'_ideal')
    if defect=='nonfinite':v['_chem_comp_atom.pdbx_model_Cartn_x_ideal'][0]='nan'
    if defect=='missing_charge':v.pop('_chem_comp_atom.pdbx_formal_charge')
    if defect=='bad_charge':v['_chem_comp_atom.pdbx_formal_charge'][0]='.5'
    if defect=='disagreeing_charge':v['_chem_comp_atom.charge']=['1']*4
    if defect=='duplicate_atom':v['_chem_comp_atom.atom_id'][1]='NQ'
    source=write(tmp_path/'input/source.cif',v)
    if defect=='multi_component':source.write_text(source.read_text()+_emit(component('MIX')))
    if defect in {'existing','symlink'}:
        out.parent.mkdir();out.write_text('PRESERVE') if defect=='existing' else out.symlink_to(source)
    if defect=='inside_source':out=source
    before=source.read_bytes()
    with pytest.raises((ValueError,FileExistsError)):prepare_graph_generation_source(source,'ZZZ',out)
    assert source.read_bytes()==before

@pytest.mark.parametrize('change',['none','bond_order','charge','missing_charge','hydrogen'])
def test_generation_compares_candidate_to_original_source_not_only_intermediate_seed(tmp_path,change):
    from nasolve.cif_numerical_recovery import generate_numerical_recovery
    source=write(tmp_path/'input/source.cif',component('ZZZ',numerical=True));values=component('ZZZ',numerical=True)
    if change=='bond_order':values['_chem_comp_bond.value_order'][0]='DOUB'
    if change=='charge':values['_chem_comp_atom.pdbx_formal_charge'][0]='1'
    if change=='missing_charge':values.pop('_chem_comp_atom.pdbx_formal_charge')
    if change=='hydrogen':values['_chem_comp_atom.type_symbol'][0]='H'
    fixture=write(tmp_path/'fixture.cif',values);exe=program(tmp_path);before=source.read_bytes()
    r=generate_numerical_recovery(source,'ZZZ',tmp_path/'out',exe,environment={**os.environ,'CANDIDATE_FIXTURE':str(fixture)},phenix_version='test-only')
    assert r['status']==('CANDIDATE_REVIEW' if change=='none' else 'REJECTED')
    assert r['source_preserved'] and source.read_bytes()==before and r['automatic_adoption'] is False
    assert r['model_optimization']=='NOT_RUN' and r['native_proxy_validation']=='NOT_RUN'
    assert r['original_source_inspection']['source_assessment']['inputs'][0]['sha256']==hashlib.sha256(before).hexdigest()

@pytest.mark.parametrize('defect',['none','fd','flag','snapshot','missing_step','plan','budget','signature'])
def test_saved_rotation_evidence_is_recomputed_before_recovery(tmp_path,defect):
    from nasolve.cif_base_rotation_audit import audit_base_rotations
    from nasolve.cif_numerical_recovery import validate_rotation_evidence
    from tests.test_cif_base_rotation_audit import problem,polynomial
    p,plan=problem();cases={'full_precision':p,'pdb_rounded':deepcopy(p)}
    q=audit_base_rotations(polynomial,cases,plan)
    q.update(rotation_derivative_qualification='SAMPLED_ROTATION_DERIVATIVES_PASS',constraint_signature_before='signature',constraint_signature_after='signature',preflight_evaluations=17,audit_evaluation_calls=q['evaluation_calls'])
    q['evaluation_calls']+=17;q['max_evaluation_calls']=3000
    saved={'endpoint_gradient_audit':{'cases':{label:{'families':{f:{'baseline':deepcopy(v)} for f,v in c['baseline'].items()}} for label,c in q['cases'].items()}}}
    q0=q['cases']['full_precision']['groups'][0]['profile'][0]['derivative']
    if defect=='fd':q0['samples'][0]['plus_target']+=100
    if defect=='flag':q0['consistent']=False
    if defect=='snapshot':q['cases']['full_precision']['baseline']['all']['gradient'][0]+=1
    if defect=='missing_step':q0['samples'].pop()
    if defect=='plan':plan['groups'][0]['site']='other'
    if defect=='budget':q['evaluation_calls']=3001
    if defect=='signature':q['constraint_signature_after']='changed'
    if defect=='none':assert validate_rotation_evidence(q,plan,saved,'signature')['directions_passed']==32
    else:
        with pytest.raises(ValueError):validate_rotation_evidence(q,plan,saved,'signature')
