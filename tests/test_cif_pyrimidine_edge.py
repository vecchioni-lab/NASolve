"""The chemical names of the two uracil carbonyls do not determine the pairing edge."""
import json
from unittest.mock import patch

import openpyxl
import pytest

from nasolve.cli import main
from nasolve.cif_attachment_profiles import inspect_attachment_profile
from nasolve.cif_stereochemistry_audit import _graph, _values
from .test_cif_catalogue import row, snapshot, source, workbook


def pair_book(directory, code, attachment, *, swap=False):
    path = workbook(directory, [('thymine', row(code))])
    with path.open('rb') as stream:
        wb = openpyxl.load_workbook(stream)
    sheet = wb['thymine']
    extra = {'O2': 'O4' if swap else 'O2', 'O4': 'O2' if swap else 'O4',
             'N3': 'N3', 'C2': 'C2', 'C6': 'C6', 'C4': 'C4',
             'Glycosidic atom': attachment, 'Backbone attachment atom': "C1'"}
    for index, (role, value) in enumerate(extra.items(), sheet.max_column + 1):
        sheet.cell(1, index, role)
        sheet.cell(2, index, value)
    wb.save(path)
    wb.close()
    return path


@pytest.mark.parametrize('code,attachment,distal', [('PDU', 'N1', 'O4'), ('UY1', 'C5', 'O2')])
@pytest.mark.parametrize('swap', [False, True])
def test_public_ring_matches_the_actual_emitted_contacts(tmp_path, code, attachment, distal, swap):
    path = source(tmp_path / 'ccd', code)
    book = pair_book(tmp_path, code, attachment, swap=swap)
    before = snapshot(tmp_path)
    original = inspect_attachment_profile(path, code, workbook=book)
    with patch('subprocess.Popen', side_effect=AssertionError('This inspection is offline')):
        result = inspect_attachment_profile(path, code, workbook=book, check_at_pair=True)
    check = result.pop('at_pair_check')
    assert result == original
    assert check['source_atoms_by_adenine_contact'] == {'N1':'N3', 'N6':distal}
    emitted = 'O2' if swap else 'O4'
    assert check['narestraints_atoms_by_adenine_contact'] == {'N1':'N3', 'N6':emitted}
    assert check['status'] == ('AGREES' if emitted == distal else 'CONFLICT')
    assert before == snapshot(tmp_path)


def test_renamed_ring_gives_the_same_atoms_and_ambiguous_chemistry_stays_open(tmp_path):
    from nasolve.cif_pyrimidine_edge import source_uracil_edge

    elements, bonds, charges, neighbors = _graph(_values(source(tmp_path / 'ccd', 'UY1'), 'UY1'))
    names = {a:f'X{i:03d}' for i,a in enumerate(reversed(sorted(elements)))}
    rename = lambda values: {names[a]:v for a,v in values.items()}
    graph = (rename(elements), {tuple(sorted((names[a],names[b]))):v for (a,b),v in bonds.items()},
             rename(charges), {names[a]:{names[n] for n in ns} for a,ns in neighbors.items()})
    result = source_uracil_edge(graph, names['C5'])
    assert result['adenine_N6_acceptor'] == names['O2'] and result['adenine_N1_donor'] == names['N3']
    assert result['proximal_carbonyl_oxygen'] == names['O4']
    # A deprotonated donor, missing H, thione or altered bond is outside this evidence.
    for change in ('charge', 'hydrogen', 'thione', 'carbonyl'):
        e,b,q,n = dict(elements),dict(bonds),dict(charges),{a:set(v) for a,v in neighbors.items()}
        if change == 'charge':
            q['N3'] = -1.
        elif change == 'hydrogen':
            n['N3'].remove('HN3')
            n['HN3'].remove('N3')
        elif change == 'thione':
            e['O4'] = 'S'
        else:
            b[tuple(sorted(('C2','O2')))] = 'SINGLE'
        assert source_uracil_edge((e,b,q,n), 'C5') is None


def test_public_cli_relocates_without_choosing_a_partner(tmp_path, capsys):
    origin = tmp_path/'original'
    origin.mkdir()
    path = source(origin/'ccd', 'UY1')
    book = pair_book(origin, 'UY1', 'C5')
    def run(root):
        args = ['cif-doctor','profile',str(root/path.relative_to(origin)), '--code','UY1',
                '--workbook',str(root/book.name),'--check-at-pair','--json']
        assert main(args) == 2
        return json.loads(capsys.readouterr().out)
    first = run(origin)
    moved = tmp_path/'moved'
    origin.rename(moved)
    before = snapshot(moved)
    assert run(moved) == first
    assert snapshot(moved) == before and not origin.exists()
    assert first['at_pair_check']['status'] == 'CONFLICT' and first['automatic_adoption'] is False
    assert str(tmp_path) not in json.dumps(first)
