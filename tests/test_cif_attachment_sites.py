"""Explicit site intent must not become implicit permission to change chemistry."""
import json
from unittest.mock import patch

import pytest
from Bio.PDB.mmcifio import MMCIFIO

from nasolve.cli import main
from nasolve.cif_linked_preparation import component_values
from .test_cif_catalogue import workbook, row, source, snapshot
from .test_cif_attachment_profiles import pna


def pdb_atom(serial, atom, element, code, site):
    chain, resid = site.split(':')
    return (f'HETATM{serial:5d} {atom:>4} {code:>3} {" " if chain == "_" else chain}{int(resid):4d}    '
            f'{serial * .1:8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{20.:6.2f}          {element:>2}  \n')


def case(root, code='PDU', *, linked=True):
    path = source(root / 'ccd', code)
    book = workbook(root, [('thymine', row(code))])
    values = component_values(path, code)
    leaving = 'OXT' if code == 'ATL' else 'OP3'
    atoms = dict(zip(values['_chem_comp_atom.atom_id'], values['_chem_comp_atom.type_symbol']))
    model = root / 'model.pdb'
    retained = [(a, e) for a, e in atoms.items() if e not in {'H', 'D'} and (not linked or a != leaving)]
    lines = [pdb_atom(i + 1, a, e, code, 'A:2') for i, (a, e) in enumerate(retained)]
    lines += [pdb_atom(len(lines)+1, "O3'", 'O', 'DA', 'A:1'),
              pdb_atom(len(lines)+2, 'P', 'P', 'DA', 'A:3')]
    model.write_text(''.join(lines) + 'END\n')
    partner = lambda site, atom: {'site': site, 'component': 'DA', 'atom_id': atom}
    ports = {'phosphate': {'state': 'source'}, 'alcohol': {'state': 'source'}}
    if linked:
        ports = {'phosphate': {'state': 'linked', 'leaving_atom': leaving,
                              'partner': partner('A:1', "O3'"), 'symmetry_operation': 'x,y,z'},
                 'alcohol': {'state': 'linked', 'partner': partner('A:3', 'P'), 'symmetry_operation': 'x,y,z'}}
    context = root / 'context.json'
    context.write_text(json.dumps({'schema_version': 1, 'site': 'A:2', 'ports': ports}))
    return path, book, model, context


def inspect(inputs, candidate=None):
    from nasolve.cif_attachment_sites import inspect_attachment_site
    path, book, model, context = inputs
    return inspect_attachment_site(path, 'ATL' if 'ATL' in path.name else 'PDU',
                                   workbook=book, model=model, context=context, candidate=candidate)


def edit_context(inputs, edit):
    path = inputs[3]; data = json.loads(path.read_text()); edit(data)
    path.write_text(json.dumps(data))


def projected(inputs, removed, destination):
    # Independent table filtering: exact reference deletions, no native typing.
    code = 'ATL' if 'ATL' in inputs[0].name else 'PDU'
    values = component_values(inputs[0], code)
    for category in {k.split('.')[0] for k in values if '.' in k}:
        fields = [k for k in values if k.startswith(category + '.')]
        refs = [k for k in fields if k.split('.')[1].startswith('atom_id')]
        if not refs: continue
        keep = [i for i in range(len(values[fields[0]])) if all(values[k][i] not in removed for k in refs)]
        for key in fields:
            if keep: values[key] = [values[key][i] for i in keep]
            else: values.pop(key)
    writer = MMCIFIO(); writer.set_dict(values); writer.save(str(destination))
    return destination


def test_public_site_cli_fails_before_implementation(tmp_path, capsys):
    path, book, model, context = case(tmp_path)
    before = snapshot(tmp_path)
    with patch('nasolve.cli.discover_phenix') as discover, patch('subprocess.Popen') as process:
        assert main(['cif-doctor', 'site-plan', str(path), '--code', 'PDU', '--workbook', str(book),
                     '--model', str(model), '--context', str(context), '--json']) == 2
    result = json.loads(capsys.readouterr().out)
    assert result['plan_status'] == 'PROPOSED'
    assert result['status'] == 'REVIEW' and not result['automatic_adoption']
    assert result['native_qualification'] == 'NOT_ASSESSED'
    assert snapshot(tmp_path) == before
    discover.assert_not_called(); process.assert_not_called()


@pytest.mark.parametrize('code,leaving', [('PDU', 'OP3'), ('ATL', 'OXT')])
def test_exact_link_deletions_preserve_other_phosphate_hydrogen(tmp_path, code, leaving):
    inputs = case(tmp_path, code); result = inspect(inputs)
    delta = result['permitted_source_projection']
    assert result['plan_status'] == 'PROPOSED'
    values = component_values(inputs[0], code)
    bonds = list(zip(values['_chem_comp_bond.atom_id_1'], values['_chem_comp_bond.atom_id_2']))
    hydrogen = lambda parent: {b if a == parent else a for a, b in bonds if parent in {a, b}} & set(
        a for a, e in zip(values['_chem_comp_atom.atom_id'], values['_chem_comp_atom.type_symbol']) if e in {'H', 'D'})
    assert set(delta['deleted_atoms']) == {leaving} | hydrogen(leaving) | hydrogen("O3'")
    assert hydrogen('OP2') <= set(delta['retained_atoms'])
    assert 'OP2' in delta['retained_atoms']
    assert delta['formal_charge_changes'] == []
    assert delta['added_atoms'] == []
    assert len(delta['declared_external_bonds']) == 2
    assert result['partner_chemistry'] == 'NOT_ASSESSED'
    candidate = projected(inputs, set(delta['deleted_atoms']), tmp_path / 'projection.cif')
    assert inspect(inputs, candidate)['projection_check']['status'] == 'MATCH'


def test_terminal_phosphate_is_protected_and_never_inferred_from_nearby_partner(tmp_path):
    inputs = case(tmp_path, linked=False)
    result = inspect(inputs)
    assert result['plan_status'] == 'PROPOSED'
    assert result['permitted_source_projection']['deleted_atoms'] == []
    assert result['permitted_source_projection']['declared_external_bonds'] == []
    assert inspect(inputs, inputs[0])['projection_check']['status'] == 'MATCH'
    candidate = projected(inputs, {'OP3'}, tmp_path / 'stripped.cif')
    assert inspect(inputs, candidate)['projection_check']['status'] == 'MISMATCH'


@pytest.mark.parametrize('mode', ['no_choice', 'double_oxygen', 'retained_oxygen', 'port', 'absent', 'extra_field',
                                  'missing_port', 'symmetry', 'missing_symmetry', 'bad_partner', 'wrong_element', 'self'])
def test_bad_or_ambiguous_context_never_selects_a_projection(tmp_path, mode):
    inputs = case(tmp_path)
    def change(c):
        p = c['ports']['phosphate']
        if mode == 'no_choice': p.pop('leaving_atom')
        if mode in {'double_oxygen', 'retained_oxygen', 'port', 'absent'}:
            p['leaving_atom'] = {'double_oxygen': 'OP1', 'retained_oxygen': 'OP2', 'port': "O5'", 'absent': 'XX'}[mode]
        if mode == 'extra_field': p['neutralize'] = True
        if mode == 'missing_port': c['ports'].pop('alcohol')
        if mode == 'symmetry': p['symmetry_operation'] = '-x,y,z'
        if mode == 'missing_symmetry': p.pop('symmetry_operation')
        if mode == 'bad_partner': p['partner']['component'] = 'DG'
        if mode == 'wrong_element': p['partner'] = {'site': 'A:3', 'component': 'DA', 'atom_id': 'P'}
        if mode == 'self': p['partner'] = {'site': 'A:2', 'component': 'PDU', 'atom_id': "O3'"}
    edit_context(inputs, change)
    with pytest.raises(ValueError): inspect(inputs)


@pytest.mark.parametrize('mode', ['MODEL', 'altloc', 'insertion', 'duplicate', 'missing_element', 'nonfinite', 'extra_atom', 'missing_heavy'])
def test_model_identity_and_inventory_are_not_guessed(tmp_path, mode):
    inputs = case(tmp_path); model = inputs[2]; lines = model.read_text().splitlines(keepends=True)
    if mode == 'MODEL': lines.insert(0, 'MODEL        1\n')
    if mode == 'altloc': lines[0] = lines[0][:16] + 'B' + lines[0][17:]
    if mode == 'insertion': lines[0] = lines[0][:26] + 'A' + lines[0][27:]
    if mode == 'duplicate': lines.insert(0, lines[0])
    if mode == 'missing_element': lines[0] = lines[0][:76] + '    \n'
    if mode == 'nonfinite': lines[0] = lines[0][:30] + '     nan' + lines[0][38:]
    if mode == 'extra_atom': lines.insert(0, pdb_atom(999, 'OP3', 'O', 'PDU', 'A:2'))
    if mode == 'missing_heavy': lines.pop(0)
    model.write_text(''.join(lines))
    with pytest.raises(ValueError): inspect(inputs)


@pytest.mark.parametrize('mode', ['charge', 'stereo', 'bond', 'hydrogen', 'metadata', 'extra_column'])
def test_projection_comparison_rejects_unplanned_changes(tmp_path, mode):
    inputs = case(tmp_path); result = inspect(inputs)
    candidate = projected(inputs, set(result['permitted_source_projection']['deleted_atoms']), tmp_path / 'candidate.cif')
    values = component_values(candidate, 'PDU'); a = '_chem_comp_atom.'; b = '_chem_comp_bond.'
    if mode == 'charge': values[a+'charge'][0] = '1'
    if mode == 'stereo':
        i = values[a+'atom_id'].index("C1'"); values[a+'pdbx_stereo_config'][i] = 'S' if values[a+'pdbx_stereo_config'][i] == 'R' else 'R'
    if mode == 'bond': values[b+'value_order'][0] = 'DOUB'
    if mode == 'hydrogen':
        i = next(i for i, (x, y) in enumerate(zip(values[b+'atom_id_1'], values[b+'atom_id_2'])) if x == 'OP2' and y.startswith('H'))
        values[b+'atom_id_1'][i] = 'OP1'
    if mode == 'metadata': values['_chem_comp.type'] = ['NON-POLYMER']
    if mode == 'extra_column': values[a+'type_energy'] = ['X'] * len(values[a+'atom_id'])
    writer = MMCIFIO(); writer.set_dict(values); writer.save(str(candidate))
    assert inspect(inputs, candidate)['projection_check']['status'] == 'MISMATCH'


def test_candidate_row_order_is_not_chemical_change(tmp_path):
    inputs = case(tmp_path, linked=False)
    values = component_values(inputs[0], 'PDU')
    for key in values:
        if key.startswith(('_chem_comp_atom.', '_chem_comp_bond.')): values[key].reverse()
    candidate = tmp_path / 'reordered.cif'; writer = MMCIFIO(); writer.set_dict(values); writer.save(str(candidate))
    assert inspect(inputs, candidate)['projection_check']['status'] == 'MATCH'


def test_unknown_phosphate_reconstruction_stays_unresolved(tmp_path):
    inputs = case(tmp_path, linked=False)
    edit_context(inputs, lambda c: c['ports'].update(phosphate={'state': 'free_OH'}))
    result = inspect(inputs)
    assert result['plan_status'] == 'UNRESOLVED' and result['permitted_source_projection'] is None
    assert 'FREE_OH_RECONSTRUCTION_NEEDS_HYDROGEN_AUTHORITY' in result['review_reasons']


@pytest.mark.parametrize('charge', [0, 1])
def test_pna_link_requires_explicit_protonation_policy(tmp_path, charge):
    from nasolve.cif_attachment_sites import inspect_attachment_site
    path = tmp_path / 'pna.cif'; pna(path, charge=charge)
    book = workbook(tmp_path, [('adenine', row('Z99', N1='BN', C5='BC'))])
    v = component_values(path, 'Z99'); model = tmp_path / 'pna.pdb'
    atoms = [(a, e) for a, e in zip(v['_chem_comp_atom.atom_id'], v['_chem_comp_atom.type_symbol']) if e != 'H']
    model.write_text(''.join(pdb_atom(i+1, a, e, 'Z99', 'A:2') for i, (a, e) in enumerate(atoms)) + pdb_atom(99, 'C', 'C', 'GLY', 'A:1'))
    context = tmp_path / 'context.json'; context.write_text(json.dumps({'schema_version': 1, 'site': 'A:2', 'ports': {
        'amine': {'state': 'linked', 'partner': {'site': 'A:1', 'component': 'GLY', 'atom_id': 'C'}, 'symmetry_operation': 'x,y,z'},
        'carboxyl': {'state': 'source'}}}))
    result = inspect_attachment_site(path, 'Z99', workbook=book, model=model, context=context)
    assert result['plan_status'] == 'UNRESOLVED' and result['permitted_source_projection'] is None
    assert result['source_profile']['ports']['amine']['formal_charge'] == charge
    assert 'PNA_LINK_STATE_AUTHORITY_REQUIRED' in result['review_reasons']


def test_exact_cold_relocation_and_input_mutation_guard(tmp_path):
    original = tmp_path / 'original'; original.mkdir(); inputs = case(original, 'ATL')
    result = inspect(inputs); moved = tmp_path / 'moved'; original.rename(moved)
    inputs = tuple(moved / p.relative_to(original) for p in inputs); before = snapshot(moved)
    with patch('subprocess.Popen', side_effect=AssertionError('no subprocess')):
        assert inspect(inputs) == result
    assert snapshot(moved) == before and not original.exists()
    assert str(tmp_path) not in json.dumps(result)
    import nasolve.cif_attachment_sites as module
    saved = module.inspect_attachment_profile
    def mutate(*args, **kwargs):
        report = saved(*args, **kwargs); inputs[2].write_text(inputs[2].read_text() + 'REMARK changed\n'); return report
    with patch.object(module, 'inspect_attachment_profile', mutate), pytest.raises(ValueError, match='changed'):
        inspect(inputs)


def test_duplicate_json_fields_and_stale_nar_mapping_are_rejected(tmp_path):
    inputs = case(tmp_path)
    inputs[3].write_text(inputs[3].read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
    with pytest.raises(ValueError, match='Duplicate'): inspect(inputs)
    inputs = case(tmp_path)
    workbook(tmp_path, [('thymine', row(N1='C5', C5='N1'))])
    result = inspect(inputs)
    assert result['plan_status'] == 'UNRESOLVED' and result['permitted_source_projection'] is None


@pytest.mark.parametrize('mode', ['extra_component', 'unbound_block', 'metadata_block_extra'])
def test_projection_cannot_hide_changes_in_unselected_blocks(tmp_path, mode):
    inputs = case(tmp_path, linked=False); candidate = tmp_path / 'extra.cif'
    extra = {'extra_component': '\ndata_other\n_chem_comp.id ZZZ\n_chem_comp_atom.comp_id ZZZ\n_chem_comp_atom.atom_id C\n_chem_comp_atom.type_symbol C\n',
             'unbound_block': '\ndata_extra\n_custom.assertion changed\n',
             'metadata_block_extra': '\ndata_list\n_chem_comp.id PDU\n_custom.assertion changed\n'}[mode]
    if mode == 'metadata_block_extra':
        # Put metadata in its own valid list block; an unrelated field in it must not vanish.
        from nasolve.cif_linked_preparation import _render
        candidate.write_text(_render(component_values(inputs[0], 'PDU'), 'PDU').replace('data_comp_list', 'data_comp_list\n_custom.assertion changed'))
    else:
        candidate.write_text(inputs[0].read_text() + extra)
    assert inspect(inputs, candidate)['projection_check']['status'] == 'MISMATCH'


@pytest.mark.parametrize('mode', ['charged', 'missing_h', 'unknown_charge', 'deuterium'])
def test_reactive_atom_state_is_explicit_and_never_neutralized(tmp_path, mode):
    inputs = case(tmp_path); path = inputs[0]; values = component_values(path, 'PDU')
    atoms = values['_chem_comp_atom.atom_id']; index = atoms.index("O3'")
    if mode == 'charged': values['_chem_comp_atom.charge'][index] = '-1'
    if mode == 'unknown_charge': values['_chem_comp_atom.charge'][index] = '?'
    if mode == 'missing_h':
        # Remove its single declared H independently; no implicit-H completion.
        bonds = list(zip(values['_chem_comp_bond.atom_id_1'], values['_chem_comp_bond.atom_id_2']))
        hydrogen = next(y for x, y in bonds if x == "O3'" and y.startswith('H'))
        projected(inputs, {hydrogen}, tmp_path / 'missing.cif'); path.write_bytes((tmp_path / 'missing.cif').read_bytes())
    else:
        if mode == 'deuterium':
            values['_chem_comp_atom.type_symbol'] = ['D' if e == 'H' else e for e in values['_chem_comp_atom.type_symbol']]
        writer = MMCIFIO(); writer.set_dict(values); writer.save(str(path))
    result = inspect(inputs)
    assert result['plan_status'] == ('PROPOSED' if mode == 'deuterium' else 'UNRESOLVED')
    if mode != 'deuterium': assert result['permitted_source_projection'] is None


def test_text_error_and_unselected_site_scope(tmp_path, capsys):
    inputs = case(tmp_path, linked=False); path, book, model, context = inputs
    lines = model.read_text().splitlines(keepends=True)
    copy = [line[:22] + '   7' + line[26:] for line in lines if line[17:20] == 'PDU']
    model.write_text(''.join(lines[:-1] + copy + lines[-1:]))
    result = inspect(inputs)
    assert result['other_component_sites'] == ['A:7']
    args = ['cif-doctor', 'site-plan', str(path), '--code', 'PDU', '--workbook', str(book), '--model', str(model), '--context', str(context)]
    assert main(args) == 2
    assert 'Read-only proposal' in capsys.readouterr().out
    model.write_text(model.read_text().replace(' PDU A', ' PDU _'))
    assert main(args) == 1
    assert 'CIF Doctor:' in capsys.readouterr().err


@pytest.mark.parametrize('mode', ['after_end', 'after_ter', 'noncontiguous'])
def test_pdb_record_boundaries_do_not_merge_distinct_sites(tmp_path, mode):
    inputs = case(tmp_path); model = inputs[2]; lines = model.read_text().splitlines(keepends=True)
    if mode == 'after_end': lines.insert(1, 'END\n')
    if mode == 'after_ter': lines.insert(1, 'TER\n')
    if mode == 'noncontiguous': lines.insert(1, lines.pop(-3))
    model.write_text(''.join(lines))
    with pytest.raises(ValueError): inspect(inputs)


def test_explicit_equivalent_oxygen_choice_is_not_hardcoded_op3(tmp_path):
    inputs = case(tmp_path)
    edit_context(inputs, lambda c: c['ports']['phosphate'].update(leaving_atom='OP2'))
    inputs[2].write_text(inputs[2].read_text().replace(' OP2 ', ' OP3 '))
    result = inspect(inputs)
    assert 'OP2' in result['permitted_source_projection']['deleted_atoms']
    assert 'OP3' in result['permitted_source_projection']['retained_atoms']


def test_renamed_atl_ports_use_source_binding_not_spelling(tmp_path):
    inputs = case(tmp_path, 'ATL'); values = component_values(inputs[0], 'ATL')
    names = {atom: f'R{i:03}' for i, atom in enumerate(values['_chem_comp_atom.atom_id'])}
    for key, column in values.items():
        if '.' in key and key.split('.')[1].startswith('atom_id'):
            values[key] = [names.get(v, v) for v in column]
    writer = MMCIFIO(); writer.set_dict(values); writer.save(str(inputs[0]))
    workbook(tmp_path, [('thymine', row('ATL', N1=names['N1'], C5=names['C5']))])
    lines = inputs[2].read_text().splitlines(keepends=True)
    inputs[2].write_text(''.join(line[:12]+f"{names[line[12:16].strip()]:>4}"+line[16:]
                               if line[17:20] == 'ATL' else line for line in lines))
    edit_context(inputs, lambda c: c['ports']['phosphate'].update(leaving_atom=names['OXT']))
    result = inspect(inputs)
    assert result['plan_status'] == 'PROPOSED'
    assert names['OXT'] in result['permitted_source_projection']['deleted_atoms']
    assert names['OP2'] in result['permitted_source_projection']['retained_atoms']
