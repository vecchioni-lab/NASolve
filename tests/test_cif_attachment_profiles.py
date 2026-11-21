"""Topology transfer without implicit chemical-state or linkage decisions."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.cli import main
from .test_cif_catalogue import workbook, row, source, snapshot


def inspect(path, code, book):
    from nasolve.cif_attachment_profiles import inspect_attachment_profile
    return inspect_attachment_profile(path, code, workbook=book)


def pna(path, *, charge=1, copies=1, cap=False, rename=False):
    # Independent, deliberately differently named aminoethylglycine structure.
    # A minimal base ring is sufficient: these are graph tests, not CCD chemistry.
    atoms = {'BN': 'N', 'BC': 'C', 'BX': 'C'}
    edges = [('BN', 'BC', 'SING'), ('BC', 'BX', 'DOUB'), ('BX', 'BN', 'SING')]
    core = {'L': 'C', 'K': 'C', 'Q': 'O', 'T': 'N', 'G': 'C', 'A': 'C',
            'O': 'O', 'OH': 'O', 'E': 'C', 'F': 'C', 'N': 'N'}
    links = [('BN', 'L', 'SING'), ('L', 'K', 'SING'), ('K', 'Q', 'DOUB'),
             ('K', 'T', 'SING'), ('T', 'G', 'SING'), ('G', 'A', 'SING'),
             ('A', 'O', 'DOUB'), ('A', 'OH', 'SING'), ('T', 'E', 'SING'),
             ('E', 'F', 'SING'), ('F', 'N', 'SING')]
    for i in range(copies):
        prefix = str(i)
        atoms.update({prefix + a: e for a, e in core.items()})
        edges.extend((a if a == 'BN' else prefix + a, prefix + b, order) for a, b, order in links)
        for h in range(3 if charge else 2):
            atoms[f'{i}H{h}'] = 'H'
            edges.append((prefix + 'N', f'{i}H{h}', 'SING'))
        if cap:
            atoms[prefix + 'CAP'] = 'C'; edges.append((prefix + 'N', prefix + 'CAP', 'SING'))
    mapping = {a: f'X{i:03}' if rename else a for i, a in enumerate(atoms)}
    lines = ['data_Z99', '_chem_comp.id Z99', '_chem_comp.type "DNA LINKING"', 'loop_',
             '_chem_comp_atom.comp_id', '_chem_comp_atom.atom_id', '_chem_comp_atom.type_symbol',
             '_chem_comp_atom.charge', '_chem_comp_atom.pdbx_stereo_config']
    for a, element in atoms.items():
        lines.append(f'Z99 {mapping[a]} {element} {charge if a.endswith("N") and a != "BN" else 0} {"R" if a.endswith("F") else "N"}')
    lines += ['loop_', '_chem_comp_bond.comp_id', '_chem_comp_bond.atom_id_1',
              '_chem_comp_bond.atom_id_2', '_chem_comp_bond.value_order']
    lines += [f'Z99 {mapping[a]} {mapping[b]} {order}' for a, b, order in edges]
    path.write_text('\n'.join(lines) + '\n')
    return mapping


def test_profile_public_cli_regression(tmp_path, capsys):
    book = workbook(tmp_path, [('thymine', row())]); path = source(tmp_path / 'ccd')
    before = snapshot(tmp_path)
    with patch('nasolve.cli.discover_phenix') as discover, patch('subprocess.Popen') as process:
        assert main(['cif-doctor', 'profile', str(path), '--code', 'PDU',
                     '--workbook', str(book), '--json']) == 2
    report = json.loads(capsys.readouterr().out)
    assert report['topology_status'] == 'MATCH'
    assert report['matched_profile'] == 'unbridged-furanose-phosphate-v1'
    assert snapshot(tmp_path) == before
    discover.assert_not_called(); process.assert_not_called()


@pytest.mark.parametrize('code,bridged,terminal', [('PDU', False, 'OP3'), ('ATL', True, 'OXT')])
def test_public_furanoses_preserve_phosphate_and_stereo(tmp_path, code, bridged, terminal):
    book = workbook(tmp_path, [('thymine', row(code))]); path = source(tmp_path / 'ccd', code)
    before = snapshot(tmp_path); report = inspect(path, code, book)
    assert report['topology_status'] == 'MATCH'
    assert ('two-o-four-c' in report['matched_profile']) == bridged
    assert report['bindings']['base'] == 'N1'
    assert report['ports']['phosphate']['atom_id'] == 'P'
    neighbors = {n['atom_id']: n for n in report['ports']['phosphate']['neighbors']}
    assert terminal in neighbors
    # The P atom has no H, but its terminal O atoms do. Preserve that distinction.
    assert report['ports']['phosphate']['source_hydrogens'] == []
    assert len(neighbors[terminal]['source_hydrogens']) == 1
    assert len(neighbors['OP2']['source_hydrogens']) == 1
    assert report['ports']['phosphate']['leaving_atoms'] == 'NOT_ASSIGNED'
    assert report['ports']['alcohol']['atom_id'] == "O3'"
    assert report['source_stereo_markers']["C1'"] in {'R', 'S'}
    assert report['status'] == 'REVIEW' and report['site_context'] == 'NOT_ASSESSED'
    assert report['permitted_delta'] == 'NOT_ASSIGNED' and not report['automatic_adoption']
    assert report['transformations'] == [] and snapshot(tmp_path) == before


@pytest.mark.parametrize('charge', [0, 1])
@pytest.mark.parametrize('renamed', [False, True])
def test_pna_state_and_names_are_evidence_not_phosphate_logic(tmp_path, charge, renamed):
    path = tmp_path / 'source.cif'; names = pna(path, charge=charge, rename=renamed)
    book = workbook(tmp_path, [('adenine', row('Z99', N1=names['BN'], C5=names['BC'], **{'Sugar Type': 'made up'}))])
    report = inspect(path, 'Z99', book)
    assert report['topology_status'] == 'MATCH'
    assert report['matched_profile'] == 'uncapped-aminoethylglycine-pna-core-v1'
    assert report['source_type_declaration'] == 'DNA LINKING'
    assert report['ports']['amine']['atom_id'] == names['0N']
    assert report['ports']['amine']['formal_charge'] == charge
    assert len(report['ports']['amine']['source_hydrogens']) == (3 if charge else 2)
    assert set(report['ports']) == {'amine', 'carboxyl'}
    assert report['ports']['carboxyl']['atom_id'] == names['0A']
    assert report['source_stereo_markers'][names['0F']] == 'R'
    assert report['ports']['amine']['terminal_state_selection'] == 'NOT_ASSIGNED'
    assert not report['transformations']


@pytest.mark.parametrize('mode', ['capped', 'wrong_order', 'ambiguous', 'search_limit', 'size_limit'])
def test_incomplete_or_multiple_topologies_never_select_a_profile(tmp_path, mode):
    path = tmp_path / 'source.cif'; pna(path, copies=2 if mode == 'ambiguous' else 1, cap=mode == 'capped')
    book = workbook(tmp_path, [('adenine', row('Z99', N1='BN', C5='BC'))])
    if mode == 'wrong_order':
        path.write_text(path.read_text().replace('Z99 0K 0Q DOUB', 'Z99 0K 0Q SING'))
    settings = {'MAX_SEARCH_STEPS': 1} if mode == 'search_limit' else {'MAX_HEAVY_ATOMS': 1} if mode == 'size_limit' else {}
    import nasolve.cif_attachment_profiles as profiles
    with patch.multiple(profiles, **settings) if settings else patch.object(profiles, 'MAX_HEAVY_ATOMS', 128):
        report = inspect(path, 'Z99', book)
    assert report['topology_status'] == {'ambiguous': 'AMBIGUOUS', 'search_limit': 'SEARCH_LIMIT',
                                       'size_limit': 'NOT_ASSESSED'}.get(mode, 'NO_MATCH')
    assert report['matched_profile'] is None and not report['ports']
    assert report['review_reasons']


@pytest.mark.parametrize('mode', ['missing', 'conflicting', 'empty', 'absent', 'wrong_identity', 'parse_error'])
def test_no_weaker_path_around_source_and_nar_checks(tmp_path, mode):
    path = source(tmp_path / 'ccd')
    entries = [('thymine', row(N1='missing' if mode == 'missing' else None if mode == 'empty' else 'N1',
                               C5=None if mode == 'empty' else 'C5'))]
    if mode == 'conflicting': entries.append(('thymine', row(N1='N9')))
    if mode == 'absent': entries = [('thymine', row('ZZZ'))]
    if mode == 'wrong_identity': path.write_text(path.read_text().replace('PDU', 'ZZZ'))
    if mode == 'parse_error': path.write_text(path.read_text() + '\ndata_bad\n_chem_comp.id X\n_chem_comp.id X\n')
    report = inspect(path, 'PDU', workbook(tmp_path, entries))
    assert report['matched_profile'] is None and report['review_reasons']


def test_loader_glycosidic_disagreement_is_visible(tmp_path):
    path = source(tmp_path / 'ccd')
    book = workbook(tmp_path, [('thymine', row(N1='C5', C5='N1'))])
    report = inspect(path, 'PDU', book)
    assert report['topology_status'] == 'MATCH'
    assert report['base_attachment'] == {'source_atom': 'N1', 'loader_atom': 'C5', 'matches_loader': False}
    assert 'NAR_LOADER_ATTACHMENT_DISAGREES_WITH_TOPOLOGY' in report['review_reasons']


@pytest.mark.parametrize('target', ['source', 'workbook'])
def test_changed_inputs_cannot_receive_a_receipt(tmp_path, target):
    import nasolve.cif_attachment_profiles as profiles
    path = source(tmp_path / 'ccd'); book = workbook(tmp_path, [('thymine', row())])
    original = profiles._embeddings
    def mutate(*args):
        result = original(*args)
        changed = path if target == 'source' else book
        changed.write_bytes(changed.read_bytes() + b'\n')
        return result
    with patch.object(profiles, '_embeddings', mutate), pytest.raises(ValueError, match='changed'):
        inspect(path, 'PDU', book)


def test_relocated_original_gone_is_exact_read_only(tmp_path):
    original = tmp_path / 'original'; original.mkdir()
    path = source(original / 'ccd', 'ATL'); book = workbook(original, [('thymine', row('ATL'))])
    report = inspect(path, 'ATL', book)
    moved = tmp_path / 'moved'; original.rename(moved)
    before = snapshot(moved)
    with patch('subprocess.Popen', side_effect=AssertionError('no native process')):
        assert inspect(moved / path.relative_to(original), 'ATL', moved / book.name) == report
    assert not original.exists() and snapshot(moved) == before
    assert str(tmp_path) not in json.dumps(report)


def test_text_summary_and_missing_input(tmp_path, capsys):
    path = source(tmp_path / 'ccd'); book = workbook(tmp_path, [('thymine', row())])
    args = ['cif-doctor', 'profile', str(path), '--code', 'PDU', '--workbook', str(book)]
    assert main(args) == 2
    output = capsys.readouterr().out
    assert 'MATCH' in output and 'phosphate: P' in output and 'No linkage' in output
    assert main([*args[:2], str(tmp_path / 'absent.cif'), *args[3:]]) == 1
    assert 'CIF Doctor:' in capsys.readouterr().err


@pytest.mark.parametrize('code', ['PDU', 'ATL'])
def test_entire_furanose_rename_and_false_labels_do_not_choose_profile(tmp_path, code):
    from Bio.PDB.mmcifio import MMCIFIO
    from nasolve.cif_linked_preparation import component_values
    path = source(tmp_path / 'ccd', code)
    book = workbook(tmp_path, [('thymine', row(code))])
    expected = inspect(path, code, book)
    values = component_values(path, code)
    names = {atom: f'R{i:03}' for i, atom in enumerate(values['_chem_comp_atom.atom_id'])}
    for key, column in values.items():
        if key == 'data_': continue
        field = key.split('.')[-1]
        if field.startswith('atom_id'):
            values[key] = [names.get(value, value) for value in column]
        elif field in {'comp_id', 'id'}:
            values[key] = ['Z99' if value == code else value for value in column]
    values['_chem_comp.type'] = ['NON-POLYMER']
    values['data_'] = 'Z99'
    writer = MMCIFIO(); writer.set_dict(values); writer.save(str(path))
    book = workbook(tmp_path, [('thymine', row('Z99', N1=names['N1'], C5=names['C5'], **{'Sugar Type': 'PNA'}))])
    report = inspect(path, 'Z99', book)
    assert report['matched_profile'] == expected['matched_profile']
    assert report['bindings'] == {role: names[atom] for role, atom in expected['bindings'].items()}
    assert report['source_type_declaration'] == 'NON-POLYMER'


def test_truncated_unique_search_never_claims_unique_match(tmp_path):
    import nasolve.cif_attachment_profiles as profiles
    path = source(tmp_path / 'ccd'); book = workbook(tmp_path, [('thymine', row())])
    with patch.object(profiles, 'MAX_EMBEDDINGS', 1):
        report = inspect(path, 'PDU', book)
    assert report['topology_status'] == 'SEARCH_LIMIT'
    assert report['matched_profile'] is None
    assert any(r['matches'] for r in report['profile_searches'])


def test_pna_deuterium_and_absent_role_marker_are_retained(tmp_path):
    path = tmp_path / 'source.cif'; pna(path)
    path.write_text(path.read_text().replace('0H0 H 0', '0H0 D 0'))
    book = workbook(tmp_path, [('adenine', row('Z99', N1='BN', C5='/'))])
    report = inspect(path, 'Z99', book)
    assert report['topology_status'] == 'MATCH'
    assert report['ports']['amine']['source_hydrogens'] == ['0H0', '0H1', '0H2']
    assert report['operational_signature']['atom_roles']['C5'] == '/'


@pytest.mark.parametrize('element', ['Cn', 'Cl', 'Ca'])
def test_element_symbols_are_exact_not_substrings(tmp_path, element):
    path = tmp_path / 'source.cif'; pna(path)
    path.write_text(path.read_text().replace('Z99 BN N 0', f'Z99 BN {element} 0'))
    book = workbook(tmp_path, [('adenine', row('Z99', N1='BN', C5='BC'))])
    report = inspect(path, 'Z99', book)
    assert report['topology_status'] == 'NO_MATCH'
    assert report['matched_profile'] is None and not report['ports']
