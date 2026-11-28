"""PDU is a pinned public chemistry control, separate from the frozen scaffold."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from nasolve.ligand_profiles import _blocks
from tests.test_cif_numerical_recovery import source_values
from tests.test_cif_generation import write

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'tests/fixtures/public_ccd/PDU.cif'
PDU_SHA='cd192f18964a28c628544ae1c0b4b1f2aed124e1b90a21b9c6ca0aa4458c0292'


def test_5pc_equivalent_cytosine_records_compile_without_workbook_changes():
    from nasolve.cif_component_controls import assess_component_control
    p=ROOT/'tests/fixtures/public_ccd/5PC.cif'
    assert len(p.read_bytes())==9080 and sha256(p.read_bytes()).hexdigest()=='cea88a7236f4775310e0d997a063c00c4dfc5982d89f1dc27c59593fb4c71650'
    r=assess_component_control(p,'5PC')
    assert r['graph_status']=='PASS' and r['matching_policy_records']==2
    assert r['policy_status']=='PASS' and r['mapped_base_class']=='C'
    assert r['policy_record_resolution']=='EQUIVALENT_ROLE_RECORDS' and r['missing_mapped_atoms']==[]
    assert r['policy_controls']['pair_recipe']=='GC'
    assert set(r['policy_controls']['component_stack_plane_atoms'])=={'N1','C2','O2','N3','C4','N4','C5','C6'}

@pytest.mark.parametrize('coordinates',['ideal','declared'])
def test_graph_export_matches_installed_elbow_object_attribute_case(tmp_path,coordinates):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    values=source_values('R17')
    if coordinates=='declared':
        for axis in 'xyz':values['_chem_comp_atom.'+axis]=values.pop('_chem_comp_atom.pdbx_model_Cartn_'+axis+'_ideal')
    source=write(tmp_path/'source.cif',values);output=tmp_path/'graph/source.cif'
    prepare_graph_generation_source(source,'R17',output)
    fields=_blocks(output)[0].values
    # The returned installed reader accesses these exact attributes even though
    # mmCIF tags are case insensitive. This independent consumer contract must
    # survive the NASolve parser's normalized internal representation.
    atom=SimpleNamespace(**{k.split('.',1)[1]:v[0] for k,v in fields.items() if k.startswith('_chem_comp_atom.')})
    assert atom.pdbx_model_Cartn_x_ideal=='9.111'
    assert atom.pdbx_model_Cartn_y_ideal=='1.2'
    assert atom.pdbx_model_Cartn_z_ideal=='-1'


def test_pdu_public_control_is_hash_pinned_with_complete_propynyl_graph(tmp_path):
    from nasolve.cif_component_controls import assess_component_control
    assert len(PUBLIC.read_bytes())==9033 and sha256(PUBLIC.read_bytes()).hexdigest()==PDU_SHA
    report=assess_component_control(PUBLIC,'PDU')
    assert report['source_sha256']==PDU_SHA and report['graph_status']=='PASS'
    assert report['atom_count']==38 and report['heavy_atom_count']==23 and report['bond_count']==39
    assert report['declared_type'].upper()=='DNA LINKING' and report['declared_formal_charge']=='0'
    assert report['policy_authority']=='NARestraints' and report['mapped_base_class']=='T'
    assert report['glycosidic_attachment']=={'sugar_atom':"C1'",'base_atom':'N1','order':'SINGLE'}
    assert report['triple_bonds']==[['C5A','C5B']]
    assert report['named_mappings']['C7']=='C5A' and report['outgoing_oxygen_hydrogens']==['H2']
    assert report['atom_stereo']=={"C1'":'R',"C3'":'S',"C4'":'R'}
    policy=report['policy_controls'];assert policy['pair_recipe']=='AT'
    assert len(policy['pair_requests']['bond'])==2 and len(policy['pair_requests']['angle'])==2
    assert len(policy['stack_requests'])==2
    assert policy['pair_contact_atoms']==[['N3','N1'],['O4','N6']]
    assert 'C5A' in policy['component_stack_plane_atoms']
    assert not {'C5B','C5M'} & set(policy['component_stack_plane_atoms'])
    assert report['native_proxy_validation']=='NOT_RUN' and report['model_editing']=='NOT_RUN' and report['automatic_adoption'] is False


@pytest.mark.parametrize('defect',['none','renamed_code','bond_order','missing_role','ambiguous_record'])
def test_control_reports_actual_graph_and_refuses_ambiguous_policy(tmp_path,defect):
    from nasolve.cif_component_controls import assess_component_control
    from nasolve.cif_linked_preparation import component_values
    from nasolve.ligand_profiles import _emit
    from restraints.residue_library import load_residue_records
    values=component_values(PUBLIC,'PDU');records=load_residue_records();row=next(r for r in records if r['Ligand code']=='PDU');code='PDU'
    if defect=='renamed_code':
        code='Q17';row['Ligand code']=code
        for key,items in values.items():
            if key.endswith('.comp_id') or key=='_chem_comp.id':values[key]=[code if x=='PDU' else x for x in items]
    if defect=='bond_order':
        i=values['_chem_comp_bond.value_order'].index('TRIP');values['_chem_comp_bond.value_order'][i]='SING'
    if defect=='missing_role':row['O4']='MISSING'
    selected=[row]
    if defect=='ambiguous_record':
        other=deepcopy(row);other['O4']='CONFLICTING_ROLE';selected.append(other)
    source=tmp_path/'control.cif';source.write_text(_emit(values));before=source.read_bytes()
    if defect=='ambiguous_record':
        with pytest.raises(ValueError):assess_component_control(source,code,records=selected)
    else:
        r=assess_component_control(source,code,records=selected)
        assert r['mapped_base_class']=='T' and source.read_bytes()==before
        if defect=='missing_role':assert r['policy_status']=='REVIEW' and r['missing_mapped_atoms']==['MISSING']
        else:assert r['policy_status']=='PASS'
        assert r['triple_bonds']==([] if defect=='bond_order' else [['C5A','C5B']])


def test_pdu_graph_seed_retains_every_source_chemical_declaration(tmp_path):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    from nasolve.cif_generation import _ideal_seed
    from nasolve.cif_doctor import compare_dictionaries
    output=tmp_path/'graph/PDU.cif';report=prepare_graph_generation_source(PUBLIC,'PDU',output)
    assert report['coordinate_origin']=='SOURCE_IDEAL_COORDINATES'
    assert report['chemical_comparison']['status']=='EXACT_DECLARATIONS'
    assert len(_ideal_seed(output,'PDU')[1]['atom_ids'])==38
    assert not [r for r in compare_dictionaries([PUBLIC],[output])['differences'] if r['field'] in report['chemical_comparison']['fields']]


@pytest.mark.parametrize('change',['descriptive_only','atom_role','base_class','sugar_type','missing_atom'])
def test_duplicate_roles_are_equivalent_only_when_all_operational_fields_agree(tmp_path,change):
    from nasolve.cif_component_controls import assess_component_control
    from nasolve.cif_linked_preparation import component_values
    from nasolve.ligand_profiles import _emit
    from restraints.residue_library import load_residue_records
    values=component_values(PUBLIC,'PDU');code='Q17'
    for k,v in values.items():
        if k.endswith('.comp_id') or k=='_chem_comp.id':values[k]=[code if x=='PDU' else x for x in v]
    source=tmp_path/'Q17.cif';source.write_text(_emit(values))
    first=deepcopy(next(r for r in load_residue_records() if r['Ligand code']=='PDU'));first['Ligand code']=code
    second=deepcopy(first);second.update(Name='A descriptive alias',Entries=42,**{'C5-mod':'description, never an atom'})
    first['C5-mod']='another descriptive alias'
    if change=='atom_role':second['O4']='N3'
    if change=='base_class':second['Base Analog']='C'
    if change=='sugar_type':second['Sugar Type']='RNA'
    if change=='missing_atom':first['O4']=second['O4']='MISSING'
    if change in {'atom_role','base_class','sugar_type'}:
        with pytest.raises(ValueError,match='unambiguous'):assess_component_control(source,code,records=[first,second])
        r=assess_component_control(source,code,records=[first,second],graph_only_if_ambiguous=True)
        assert r['policy_status']=='REVIEW' and r['mapped_base_class'] is None
    else:
        r=assess_component_control(source,code,records=[first,second])
        assert r['policy_record_resolution']=='EQUIVALENT_ROLE_RECORDS' and r['matching_policy_records']==2
        assert r['policy_status']==('REVIEW' if change=='missing_atom' else 'PASS')
        assert r['missing_mapped_atoms']==(['MISSING'] if change=='missing_atom' else [])
