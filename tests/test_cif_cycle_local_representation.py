"""A single bridge between independently qualified rings stays single."""
from pathlib import Path
from copy import deepcopy

import pytest

from nasolve.cif_source_representation import generation_representation_contract, native_representation_check
from nasolve.cif_stereochemistry_audit import _values
from nasolve.ligand_profiles import _emit

POLICY = 'cif-source-declared-cycle-local-neutral-cn-aromatic-v1'
OLD = 'cif-source-declared-neutral-five-membered-cn-aromatic-v1'
SOURCE = Path(__file__).parent/'fixtures/public_ccd/PIM.cif'
A, B = '_chem_comp_atom.', '_chem_comp_bond.'


def test_public_pim_preserves_bridge_despite_its_aromatic_flag():
    before = SOURCE.read_bytes()
    with pytest.raises(ValueError, match='outside the explicit'):
        generation_representation_contract(SOURCE, 'PIM', OLD)
    contract = generation_representation_contract(SOURCE, 'PIM', POLICY)
    assert sorted(map(len, contract['allowed_systems'])) == [5, 6]
    assert all(['C5', 'C6'] not in system for system in contract['allowed_systems'])
    assert contract['retained_single_bridges'] == [{'atoms':['C5','C6'], 'source_aromatic_declaration':'Y', 'source_order':'SINGLE', 'native_order_required':1}]
    assert SOURCE.read_bytes() == before


def test_renamed_reordered_source_uses_graph_not_pim_names(tmp_path):
    v = _values(SOURCE, 'PIM'); names = {n:'Q'+str(i) for i,n in enumerate(v[A+'atom_id'])}
    for key in v:
        if key.split('.')[-1].startswith('atom_id'): v[key] = [names.get(n,n) for n in v[key]]
        if key.startswith((A,B)): v[key] = list(reversed(v[key]))
    p=tmp_path/'renamed.cif';p.write_text(_emit(v))
    contract=generation_representation_contract(p,'PIM',POLICY)
    assert sorted(map(len,contract['allowed_systems'])) == [5,6]
    assert set(contract['retained_single_bridges'][0]['atoms']) == {names['C5'],names['C6']}


@pytest.mark.parametrize('defect', ['bridge_double','bridge_stereo','hydrogen_flag','charged_ring','ring_flag','conflicting_flag'])
def test_unproven_flag_contradictions_still_refuse(tmp_path, defect):
    v=_values(SOURCE,'PIM');edges=[set(p) for p in zip(v[B+'atom_id_1'],v[B+'atom_id_2'])]
    bridge=edges.index({'C5','C6'});hydrogen=edges.index({'N1','HN1'})
    if defect=='bridge_double':v[B+'value_order'][bridge]='DOUB'
    elif defect=='bridge_stereo':v[B+'pdbx_stereo_config'][bridge]='E'
    elif defect=='hydrogen_flag':v[B+'pdbx_aromatic_flag'][hydrogen]='Y'
    elif defect=='charged_ring':v[A+'charge'][v[A+'atom_id'].index('N1')]='1'
    elif defect=='ring_flag':v[B+'pdbx_aromatic_flag'][0]='N'
    else:
        v[B+'aromatic']=v[B+'pdbx_aromatic_flag'][:];v[B+'aromatic'][bridge]='N'
    p=tmp_path/'source.cif';p.write_text(_emit(v))
    with pytest.raises(ValueError):generation_representation_contract(p,'PIM',POLICY)


@pytest.mark.parametrize('defect', ['none','bridge','partial','charge','element'])
def test_native_contract_does_not_authorize_bridge_or_chemical_changes(defect):
    from tests.test_cif_source_representation import snapshot
    from nasolve.cif_stereochemistry_audit import _graph, _coordinates
    values=_values(SOURCE,'PIM');elements,bonds,charges,_=_graph(values);_,xyz=_coordinates(values,source=True)
    wanted=dict(component='PIM',elements=elements,charges={n:int(q) for n,q in charges.items()},
                coordinates=xyz,bonds=[dict(atoms=list(edge),order={'SINGLE':1,'DOUBLE':2}[order]) for edge,order in bonds.items()])
    actual=snapshot(wanted)
    contract=generation_representation_contract(SOURCE,'PIM',POLICY)
    allowed={tuple(edge) for system in contract['allowed_systems'] for edge in system}
    for bond in actual['bonds']:
        if tuple(bond['atoms']) in allowed:bond['native_order']=1.5
    if defect=='bridge':next(b for b in actual['bonds'] if set(b['atoms'])=={'C5','C6'})['native_order']=1.5
    elif defect=='partial':next(b for b in actual['bonds'] if tuple(b['atoms']) in allowed)['native_order']=1
    elif defect=='charge':actual['atoms'][0]['native_atom_charge']=1
    elif defect=='element':actual['atoms'][0]['element']='O'
    result=native_representation_check(actual,wanted,contract,coordinates=True,charges=True)
    assert (result['status']=='SOURCE_REPRESENTATION_PASS') is (defect=='none')
    assert result['native_bond_order_editing']=='NOT_RUN'


def test_reader_projection_changes_only_proven_bridge_flags(tmp_path):
    from nasolve.cif_generation_input import source_input_files, CYCLE_LOCAL_INPUT_POLICY
    from nasolve.cif_stereochemistry_audit import _graph, _coordinates
    import json
    original=SOURCE.read_bytes()
    old_binding,old_files=source_input_files(original,'PIM')
    binding,files=source_input_files(original,'PIM',policy=CYCLE_LOCAL_INPUT_POLICY)
    before=tmp_path/'before.cif';after=tmp_path/'after.cif'
    before.write_bytes(old_files['prepared/consumer.cif']);after.write_bytes(files['prepared/consumer.cif'])
    bv,av=_values(before,'PIM'),_values(after,'PIM')
    assert _graph(bv)==_graph(av) and _coordinates(bv,source=True)==_coordinates(av,source=True)
    edge=[set(p) for p in zip(bv[B+'atom_id_1'],bv[B+'atom_id_2'])].index({'C5','C6'})
    expected=deepcopy(bv);expected[B+'pdbx_aromatic_flag'][edge]='N'
    assert av==expected
    from nasolve.cif_linked_preparation import component_values
    assert component_values(before,'PIM').keys()==component_values(after,'PIM').keys()
    assert '_chem_comp_atom.pdbx_model_Cartn_x_ideal' in component_values(after,'PIM')
    report=json.loads(files['prepared/preparation.json'])
    assert report['cycle_local_flags']['changes']==[dict(atoms=['C5','C6'],field=B+'pdbx_aromatic_flag',before='Y',after='N')]
    assert binding['policy_id']==CYCLE_LOCAL_INPUT_POLICY and binding!=old_binding
    assert source_input_files(original,'PIM',policy=CYCLE_LOCAL_INPUT_POLICY)==(binding,files)
    assert SOURCE.read_bytes()==original
    assert generation_representation_contract(after,'PIM',POLICY)['retained_single_bridges']==[]


def test_reader_projection_refuses_an_unqualified_side_flag():
    from nasolve.cif_generation_input import source_input_files, CYCLE_LOCAL_INPUT_POLICY
    v=_values(SOURCE,'PIM');edges=[set(p) for p in zip(v[B+'atom_id_1'],v[B+'atom_id_2'])]
    v[B+'pdbx_aromatic_flag'][edges.index({'N1','HN1'})]='Y'
    with pytest.raises(ValueError):source_input_files(_emit(v).encode(),'PIM',policy=CYCLE_LOCAL_INPUT_POLICY)
