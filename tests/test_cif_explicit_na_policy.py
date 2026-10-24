"""Explicit mixed recipes bind actual named PDB sites without native guessing.

Canonical/CGY/DX/IGU/IMC sources below are artificial role graphs, not chemical
qualification. Public PDU/5PC and curated component sources retain actual bytes.
Coordinates are deliberate toy layouts; this suite tests compiler contracts.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[1]


def fixture(tmp_path):
    from nasolve.cif_acquisition import REQUESTED_PAIRS
    from nasolve.cif_stereochemistry_audit import _graph, _values
    from nasolve.component_records import resolve_component_record
    from nasolve.postmr import _patch_narestraints_records
    from restraints.builder import pair_residue_from_pdb
    from restraints.residue_library import load_residue_records
    target = [list(pair) for pair in REQUESTED_PAIRS]
    background = [['DC', 'DG'], ['DA', 'DT']] * 6
    codes = set(c for pair in target + background for c in pair)
    records, _ = _patch_narestraints_records(load_residue_records(), codes)
    source_dir = tmp_path / 'sources'; source_dir.mkdir()
    sources = {}; elements = {}
    for code in sorted(codes):
        destination = source_dir / (code + '.cif')
        actual = ROOT / 'src/nasolve/data/ligands' / (code + '.cif')
        public = ROOT / 'tests/fixtures/public_ccd' / (code + '.cif')
        if code in {'1AP', 'DZ', 'DP', '5CM', 'S6G', 'DF'}:
            shutil.copyfile(actual, destination)
        elif public.exists():
            shutil.copyfile(public, destination)
        else:
            record, _ = resolve_component_record(records, code)
            residue = SimpleNamespace(get_resname=lambda c=code: c, has_id=lambda n: True,
                id=('', 1, ''), get_parent=lambda: SimpleNamespace(get_id=lambda: 'A'))
            names = sorted(set(pair_residue_from_pdb([record], residue).atoms.values()))
            # A simple connected graph tests identity/role wiring only.
            destination.write_text(f'data_{code}\n_chem_comp.id {code}\nloop_\n'
                '_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
                + ''.join(f'{code} {name} {name[0]}\n' for name in names)
                + 'loop_\n_chem_comp_bond.comp_id\n_chem_comp_bond.atom_id_1\n'
                '_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
                + ''.join(f'{code} {a} {b} SING\n' for a, b in zip(names, names[1:])))
        sources[code] = destination; elements[code] = _graph(_values(destination, code))[0]
    pairs = []
    for number, pair in enumerate(target + background, 1):
        pairs.append({'sites': [f'A:{number}', f'B:{number}'], 'components': pair,
                      'scope': 'requested' if number <= 8 else 'background'})
    lines = []; serial = 0
    for chain, side in [('A', 0), ('B', 1)]:
        for number, pair in enumerate(target + background, 1):
            code = pair[side]
            for j, (name, element) in enumerate(elements[code].items()):
                serial += 1
                lines.append(f'HETATM{serial:5d} {name:>4} {code:>3} {chain}{number:4d}    '
                    f'{float(number * 3):8.3f}{float(j):8.3f}{float(side * 8):8.3f}'
                    f'{1.:6.2f}{20.:6.2f}          {element:>2}\n')
        lines.append('TER\n')
    model = tmp_path / 'model.pdb'; model.write_text(''.join(lines) + 'END\n')
    stacks = [(f'{chain}:{i}', f'{chain}:{i+1}') for chain in ['A', 'B'] for i in range(1, 20)]
    return model, pairs, stacks, sources, deepcopy(pairs[:8])


def compile_fixture(tmp_path, inputs=None, *, name='policy'):
    from nasolve.cif_explicit_na_policy import compile_explicit_na_policy
    model, pairs, stacks, sources, controls = fixture(tmp_path) if inputs is None else inputs
    return compile_explicit_na_policy(model, pairs, stacks, sources, tmp_path / name,
                                      orientation_controls=controls)


def test_twenty_actual_site_pairs_preserve_background_and_keep_orientation_controls_separate(tmp_path, monkeypatch):
    import restraints.guesser as guesser
    from nasolve.cif_explicit_na_policy import read_explicit_na_policy
    monkeypatch.setattr(guesser, 'guess_pairs', lambda *a, **k: (_ for _ in ()).throw(AssertionError('NO_PAIR_GUESS')))
    inputs = fixture(tmp_path); before = {p: p.read_bytes() for p in [inputs[0], *inputs[3].values()]}
    result = compile_fixture(tmp_path, inputs)
    assert result['status'] == 'EXPLICIT_NA_POLICY_COMPILED'
    assert [result[k] for k in ['pair_count', 'requested_pair_count', 'background_pair_count', 'stack_count',
                               'orientation_control_count', 'source_component_count']] == [20, 8, 12, 38, 16, 16]
    assert result['requested_request_counts'] == {'angle': 38, 'bond': 22, 'parallelity': 8}
    assert result['request_counts']['parallelity'] == 58
    text = (tmp_path / 'policy/explicit_na_policy.phil').read_text()
    assert text.count('parallelity {') == 58 and text.count('enabled = False') == 1
    assert 'base_pair {' not in text and 'stacking_pair {' not in text
    assert all(not c['included_in_active_policy'] and c['swapped_membership_targets_equal'] for c in result['orientation_controls'])
    assert len({c['file']['path'] for c in result['orientation_controls']}) == 16
    assert result['index_basis'] == 'PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES'
    assert result['native_execution'] == result['model_optimization'] == 'NOT_RUN'
    assert result['native_membership'] == 'NOT_ASSESSED' and result['requires_cif_review'] is False
    assert all(path.read_bytes() == data for path, data in before.items())
    assert read_explicit_na_policy(tmp_path / 'policy') == result
    moved = tmp_path / 'moved'; (tmp_path / 'policy').rename(moved)
    inputs[0].unlink(); shutil.rmtree(tmp_path / 'sources')
    assert read_explicit_na_policy(moved) == result


def test_reversed_pair_roles_and_coordinate_moves_preserve_targets(tmp_path):
    inputs = fixture(tmp_path); first = compile_fixture(tmp_path, inputs)
    model, pairs, stacks, sources, controls = inputs
    lines = model.read_text().splitlines(keepends=True)
    model.write_text(''.join(line[:30] + f'{float(line[30:38])+50.:8.3f}' + line[38:]
        if line[:6] == 'HETATM' else line for line in lines))
    moved = compile_fixture(tmp_path, inputs, name='coordinates_moved')
    assert moved['compiled_requests'] == first['compiled_requests']
    assert moved['compiled_phil'] == first['compiled_phil']
    assert moved['inputs']['model']['sha256'] != first['inputs']['model']['sha256']
    reversed_pairs = [{**row, 'sites': row['sites'][::-1], 'components': row['components'][::-1]} for row in pairs]
    reversed_result = compile_fixture(tmp_path, (model, reversed_pairs, stacks, sources, controls), name='reversed')
    assert reversed_result['compiled_requests'] == first['compiled_requests']


@pytest.mark.parametrize('defect', ['unsupported_pair', 'wrong_component', 'missing_role', 'alternate', 'insertion',
    'duplicate_atom', 'wrong_element', 'multiple_models', 'duplicate_pair', 'multiply_paired', 'duplicate_stack', 'reversed_stack',
    'cross_chain_stack', 'missing_source', 'extra_source', 'wrong_source', 'control_background', 'control_duplicate',
    'control_not_declared'])
def test_unsupported_or_ambiguous_intent_is_rejected_before_writing(tmp_path, defect):
    from nasolve.cif_explicit_na_policy import compile_explicit_na_policy
    model, pairs, stacks, sources, controls = fixture(tmp_path)
    text = model.read_text()
    if defect == 'unsupported_pair':
        # DP is P-like; explicit P:C is unsupported, never coerced to GC.
        pairs[2]['sites'][0] = 'A:9'; pairs[2]['components'][0] = 'DC'; pairs.pop(8)
    if defect == 'wrong_component':pairs[0]['components'][0] = 'PDU'
    if defect == 'missing_role':
        text = ''.join(line for line in text.splitlines(keepends=True)
                       if not (line[:6] == 'HETATM' and line[21] == 'A' and line[22:26].strip() == '1' and line[12:16].strip() == 'N1'))
    if defect == 'alternate':text = text[:16] + 'A' + text[17:]
    if defect == 'insertion':text = text[:26] + 'A' + text[27:]
    if defect == 'duplicate_atom':text = text.splitlines(keepends=True)[0] + text
    if defect == 'wrong_element':text = text[:76] + ' O' + text[78:]
    if defect == 'multiple_models':text = 'MODEL        1\n' + text + 'ENDMDL\nMODEL        2\n' + text + 'ENDMDL\n'
    if defect == 'duplicate_pair':pairs.append(deepcopy(pairs[0]))
    if defect == 'multiply_paired':pairs[1]['sites'][0] = pairs[0]['sites'][0]; pairs[1]['components'][0] = pairs[0]['components'][0]
    if defect == 'duplicate_stack':stacks.append(stacks[0])
    if defect == 'reversed_stack':stacks.append(stacks[0][::-1])
    if defect == 'cross_chain_stack':stacks.append(('A:1', 'B:1'))
    if defect == 'missing_source':sources.pop('PDU')
    if defect == 'extra_source':sources['Q17'] = sources['PDU']
    if defect == 'wrong_source':sources['PDU'] = sources['5PC']
    if defect == 'control_background':controls.append(deepcopy(pairs[8]))
    if defect == 'control_duplicate':controls.append(deepcopy(controls[0]))
    if defect == 'control_not_declared':controls[0] = {**controls[0], 'sites': ['A:1', 'B:2'], 'components': ['CGY', 'DT']}
    model.write_text(text)
    match = 'No NARestraints recipe' if defect == 'unsupported_pair' else None
    with pytest.raises(ValueError, match=match):
        compile_explicit_na_policy(model, pairs, stacks, sources, tmp_path / 'policy', orientation_controls=controls)
    assert not (tmp_path / 'policy').exists()


@pytest.mark.parametrize('defect', ['input', 'phil', 'extra', 'symlink', 'operational_path', 'altered_target', 'altered_scope', 'list_report', 'list_inputs', 'list_reference'])
def test_reader_checks_exact_bytes_inventory_and_maintained_reconstruction(tmp_path, defect):
    from nasolve.cif_explicit_na_policy import read_explicit_na_policy
    compile_fixture(tmp_path)
    root = tmp_path / 'policy'; receipt = root / 'explicit_na_policy.json'
    r = json.loads(receipt.read_bytes())
    if defect == 'input':(root / 'inputs/model.pdb').write_bytes(b'CHANGED')
    if defect == 'phil':(root / 'explicit_na_policy.phil').write_bytes(b'CHANGED')
    if defect == 'extra':(root / 'unexpected').write_bytes(b'EXTRA')
    if defect == 'symlink':
        path = root / 'inputs/sources/PDU.cif'; path.unlink(); path.symlink_to(tmp_path / 'sources/PDU.cif')
    if defect == 'operational_path':r['inputs']['model']['path'] = '../model.pdb'
    if defect == 'altered_target':
        path = root / 'explicit_na_policy.phil'; path.write_text(path.read_text().replace('distance_ideal = 2.8', 'distance_ideal = 8.2', 1))
        for ref in r['outputs']:
            if ref['path'] == 'explicit_na_policy.phil':ref['sha256'] = sha256(path.read_bytes()).hexdigest(); ref['size'] = path.stat().st_size
        r['compiled_phil'] = next(ref for ref in r['outputs'] if ref['path'] == 'explicit_na_policy.phil')
    if defect == 'altered_scope':r['pairs'][0]['scope'] = 'background'
    if defect == 'list_inputs':r['inputs'] = []
    if defect == 'list_reference':r['outputs'][0] = []
    if defect == 'list_report':r = []
    receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError):read_explicit_na_policy(root)
