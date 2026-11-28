"""Declared imide proton loss preserves remote chemistry; names select no rule."""
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.cif_linked_preparation import component_values
from nasolve.cif_stereochemistry_audit import _graph
from nasolve.ligand_profiles import _emit

A, B = '_chem_comp_atom.', '_chem_comp_bond.'
POLICY = 'cif-declared-imide-proton-loss-v1'


def source(tmp_path, code='DT'):
    root = Path(__file__).parent
    original = root/'fixtures/chemical_reference_DT.cif' if code == 'DT' else files('nasolve').joinpath('data/ligands/DF.cif')
    path = tmp_path/'parent.cif'
    path.write_bytes(original.read_bytes())
    return path


def derive(path, code='DT', **changes):
    from nasolve.cif_declared_proton_loss import derive_imide_anion_source
    arguments = dict(component='Q71', donor='N3', hydrogen='H3', operation=POLICY)
    arguments.update(changes)
    return derive_imide_anion_source(path, code, **arguments)


@pytest.mark.parametrize('code', ['DT', 'DF'])
def test_explicit_proton_loss_keeps_every_other_atom_and_bond(tmp_path, code):
    path = source(tmp_path, code); before = path.read_bytes()
    original = component_values(path, code)
    with patch('subprocess.Popen', side_effect=AssertionError('No native execution')):
        payload, report = derive(path, code)
    output = tmp_path/'derived.cif'; output.write_bytes(payload)
    values = component_values(output, 'Q71')
    elements, bonds, charges, neighbors = _graph(values)
    oe, ob, oq, _ = _graph(original)
    assert elements == {k: v for k, v in oe.items() if k != 'H3'}
    assert bonds == {k: v for k, v in ob.items() if 'H3' not in k}
    assert charges == {k: (-1 if k == 'N3' else v) for k, v in oq.items() if k != 'H3'}
    assert neighbors['N3'] == {'C2', 'C4'} and len(elements) == 35
    # Independent row comparison includes coordinates, handedness, sugar and P/O/H flags.
    old_ids, new_ids = original[A+'atom_id'], values[A+'atom_id']
    for key, column in original.items():
        if key.startswith(A) and key not in {A+'comp_id', A+'charge'}:
            assert dict(zip(new_ids, values[key])) == {n: x for n, x in zip(old_ids, column) if n != 'H3'}
    assert values['_chem_comp.pdbx_formal_charge'] == ['-1']
    assert values['_chem_comp.formula'] == ['C10 H14 N2 O8 P' if code == 'DT' else 'C10 H14 N2 O7 P S']
    assert not any(k.startswith('_pdbx_chem_comp_descriptor.') for k in values)
    assert '_chem_comp.formula_weight' not in values
    assert report['status'] == 'DECLARED_SOURCE_REQUIRES_QUALIFICATION'
    assert report['source']['sha256'] == sha256(before).hexdigest()
    assert report['output_sha256'] == sha256(payload).hexdigest()
    assert report['formal_charge_delta'] == -1 and report['released_species']['formal_charge'] == 1
    assert report['native_qualification'] == 'NOT_RUN' and not report['automatic_adoption']
    assert path.read_bytes() == before
    assert derive(path, code) == (payload, report)


@pytest.mark.parametrize('variant', ['renamed', 'deuterium', 'reordered', 'remote_charge', 'charge_alias'])
def test_operation_is_graph_selected_and_preserves_other_declared_states(tmp_path, variant):
    path = source(tmp_path); v = component_values(path, 'DT'); kwargs = {}
    if variant == 'renamed':
        mapping = {n: 'X'+str(i) for i, n in enumerate(v[A+'atom_id'])}
        for key in v:
            if key.startswith((A, B)) and key.split('.')[-1].startswith('atom_id'):
                v[key] = [mapping.get(x, x) for x in v[key]]
        kwargs = dict(donor=mapping['N3'], hydrogen=mapping['H3'])
    if variant == 'deuterium': v[A+'type_symbol'][v[A+'atom_id'].index('H3')] = 'D'
    if variant == 'reordered':
        for key in v:
            if key.startswith((A, B)): v[key] = list(reversed(v[key]))
    if variant == 'remote_charge':
        from nasolve.cif_linked_preparation import _prune
        v = _prune(v, {'HOP2'}, outgoing=False)
        v[A+'charge'][v[A+'atom_id'].index('OP2')] = '-1'
        v['_chem_comp.pdbx_formal_charge'] = ['-1']
    if variant == 'charge_alias': v[A+'pdbx_formal_charge'] = list(v[A+'charge'])
    path.write_text(_emit(v)); payload, report = derive(path, **kwargs)
    output = tmp_path/'derived.cif'; output.write_bytes(payload); d = component_values(output, 'Q71')
    assert report['released_species']['element'] == ('D' if variant == 'deuterium' else 'H')
    assert report['output_total_formal_charge'] == (-2 if variant == 'remote_charge' else -1)
    if variant == 'remote_charge': assert d[A+'charge'][d[A+'atom_id'].index('OP2')] == '-1'
    if variant == 'charge_alias': assert d[A+'charge'] == d[A+'pdbx_formal_charge']


@pytest.mark.parametrize('defect', ['no_intent', 'same_code', 'wrong_h', 'missing_charge', 'charge_conflict',
    'total_charge', 'charged_donor', 'charged_h', 'not_n', 'not_carbonyl', 'aromatic', 'stereo',
    'numerical', 'partial_charge', 'extra_component', 'unknown_chemistry', 'double_nh'])
def test_unsupported_state_refuses_without_writing_or_altering_source(tmp_path, defect):
    path = source(tmp_path); v = component_values(path, 'DT'); kwargs = {}
    ids = v[A+'atom_id']
    if defect == 'no_intent': kwargs['operation'] = 'automatic'
    if defect == 'same_code': kwargs['component'] = 'DT'
    if defect == 'wrong_h': kwargs['hydrogen'] = 'H6'
    if defect == 'missing_charge': v[A+'charge'][0] = '?'
    if defect == 'charge_conflict': v[A+'pdbx_formal_charge'] = ['1'] * len(ids)
    if defect == 'total_charge': v['_chem_comp.pdbx_formal_charge'] = ['1']
    if defect == 'charged_donor': v[A+'charge'][ids.index('N3')] = '-1'; v['_chem_comp.pdbx_formal_charge'] = ['-1']
    if defect == 'charged_h': v[A+'charge'][ids.index('H3')] = '1'; v['_chem_comp.pdbx_formal_charge'] = ['1']
    if defect == 'not_n': v[A+'type_symbol'][ids.index('N3')] = 'C'
    if defect == 'not_carbonyl': v[A+'type_symbol'][ids.index('O2')] = 'C'
    if defect == 'aromatic': v[A+'pdbx_aromatic_flag'][ids.index('N3')] = 'Y'
    if defect == 'stereo': v[A+'pdbx_stereo_config'][ids.index('N3')] = 'R'
    if defect == 'numerical': v[B+'value_dist'] = ['1.4'] * len(v[B+'atom_id_1'])
    if defect == 'partial_charge': v[A+'partial_charge'] = ['0'] * len(ids)
    if defect == 'unknown_chemistry': v['_chem_link.id'] = ['UNSUPPORTED']
    if defect == 'double_nh':
        pairs = list(zip(v[B+'atom_id_1'], v[B+'atom_id_2']))
        i = next(i for i, p in enumerate(pairs) if set(p) == {'N3', 'H3'})
        v[B+'value_order'][i] = 'DOUB'
    path.write_text(_emit(v))
    if defect == 'extra_component': path.write_text(path.read_text()+'\ndata_extra\n_chem_comp.id ZZ\n')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError): derive(path, **kwargs)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_source_change_during_planning_is_rejected(tmp_path, monkeypatch):
    import nasolve.cif_declared_proton_loss as module
    path = source(tmp_path); original = module._graph
    def change(v):
        result = original(v); path.write_bytes(path.read_bytes()+b'\n# changed\n'); return result
    monkeypatch.setattr(module, '_graph', change)
    with pytest.raises(ValueError, match='changed'): derive(path)


@pytest.mark.parametrize('code', ['DF', 'DT'])
def test_derived_source_enters_existing_generation_input_without_state_loss(tmp_path, code):
    from nasolve.cif_generation_input import source_input_files
    path = source(tmp_path, code); payload, _ = derive(path, code)
    original = tmp_path/'declared.cif'; original.write_bytes(payload)
    binding, files = source_input_files(payload, 'Q71')
    consumer = tmp_path/'consumer.cif'; consumer.write_bytes(files['prepared/consumer.cif'])
    assert _graph(component_values(original, 'Q71')) == _graph(component_values(consumer, 'Q71'))
    assert binding['reader_dialect'] == 'CHEMICAL_COMPONENTS_CIF'
    assert original.read_bytes() == payload
