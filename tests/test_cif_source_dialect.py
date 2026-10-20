"""Source dialect routing preserves declarations, including unknown stereo."""
from copy import deepcopy
from pathlib import Path
import pytest
from nasolve.cif_linked_preparation import _render,component_values
from nasolve.cif_numerical_recovery import prepare_graph_generation_source
from tests.test_cif_numerical_recovery import source_values
from tests.test_cif_generation import write


def legacy_values(code):
    v=source_values(code);a='_chem_comp_atom.';p='_chem_comp_chir.'
    for axis in 'xyz':v[a+axis]=v.pop(a+'pdbx_model_Cartn_'+axis+'_ideal')
    v[a+'charge']=list(v[a+'pdbx_formal_charge'])
    v.update({'_chem_comp.group':['DNA'],p+'comp_id':[code],p+'id':['c1'],p+'atom_id_centre':['NQ'],
              p+'atom_id_1':["C'"],p+'atom_id_2':['C2'],p+'atom_id_3':['C3'],p+'volume_sign':['positive']})
    return v


@pytest.mark.parametrize('code',['Q17','DP','Z99'])
def test_source_monomer_dispatch_survives_target_free_export(tmp_path,code):
    from nasolve.cif_elbow_input import prepare_elbow_source_dialect_input
    v=legacy_values(code);src=tmp_path/'original.cif';src.write_text(_render(v,code))
    graph=tmp_path/'graph/source.cif';prepare_graph_generation_source(src,code,graph)
    before=src.read_bytes(),graph.read_bytes();out=tmp_path/'consumer/source.cif'
    r=prepare_elbow_source_dialect_input(src,graph,code,out);parsed=component_values(out,code)
    assert r['source_reader_dialect']==r['consumer_reader_dialect']=='MONOMER_LIBRARY_CIF'
    assert 'data_comp_list\n#\nloop_' in out.read_text()
    assert '_chem_comp_atom.pdbx_stereo_config' not in parsed
    assert '_chem_comp_atom.type_energy' not in parsed
    assert parsed['_chem_comp_bond.type']==v['_chem_comp_bond.type']
    assert parsed['_chem_comp_chir.volume_sign']==v['_chem_comp_chir.volume_sign']
    assert parsed['_chem_comp_atom.x']==v['_chem_comp_atom.x']
    assert (src.read_bytes(),graph.read_bytes())==before
    assert r['chemical_declarations']=='PRESERVED' and r['stereochemistry_inferred'] is False


def test_public_ccd_control_keeps_its_existing_reader_and_consumer_bytes(tmp_path):
    from nasolve.cif_elbow_input import prepare_elbow_source_dialect_input
    source=Path(__file__).parent/'fixtures/public_ccd/PDU.cif';graph=tmp_path/'graph/source.cif'
    prepare_graph_generation_source(source,'PDU',graph);out=tmp_path/'out/source.cif'
    r=prepare_elbow_source_dialect_input(source,graph,'PDU',out)
    assert out.read_bytes()==graph.read_bytes() and r['consumer_reader_dialect']=='CHEMICAL_COMPONENTS_CIF'


@pytest.mark.parametrize('defect',['changed_charge','changed_order','changed_chirality','changed_stereo','coordinate_conflict','numerical_target','old_energy_type','overwrite','escape'])
def test_source_dialect_adapter_refuses_chemical_change_or_unsafe_output(tmp_path,defect):
    from nasolve.cif_elbow_input import prepare_elbow_source_dialect_input
    v=legacy_values('Q17');src=tmp_path/'original.cif';src.write_text(_render(v,'Q17'))
    graph=tmp_path/'graph/source.cif';prepare_graph_generation_source(src,'Q17',graph)
    from nasolve.ligand_profiles import _emit
    g=component_values(graph,'Q17')
    if defect=='changed_charge':g['_chem_comp_atom.charge'][0]='1'
    if defect=='changed_order':g['_chem_comp_bond.type'][0]='DOUBLE'
    if defect=='changed_chirality':g['_chem_comp_chir.volume_sign'][0]='negative'
    if defect=='changed_stereo':g['_chem_comp_atom.pdbx_stereo_config']=['R']*4
    if defect=='coordinate_conflict':g['_chem_comp_atom.x']=['0']*4
    if defect=='numerical_target':g['_chem_comp_bond.value_dist']=['1.4']*3
    if defect=='old_energy_type':g['_chem_comp_atom.type_energy']=v['_chem_comp_atom.type_energy']
    graph.write_text(_emit(g));out=tmp_path/'out/source.cif'
    if defect=='overwrite':out.parent.mkdir();out.write_text('PRESERVE')
    if defect=='escape':
        target=tmp_path/'target';target.mkdir();(tmp_path/'out').symlink_to(target)
    with pytest.raises((ValueError,FileExistsError)):prepare_elbow_source_dialect_input(src,graph,'Q17',out)
    if defect=='overwrite':assert out.read_text()=='PRESERVE'
