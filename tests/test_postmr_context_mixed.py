"""Curated mutations share serial authority without joining OP3 graph eligibility."""
from pathlib import Path

import pytest

from nasolve.postmr import MutationAction
from nasolve.postmr_context import prepare_construction_context
from tests.helpers import pdb_record
from tests.test_postmr_context import fixture, SCAFFOLD, atom_rows


def mixed_context(tmp_path, *, problem=None):
    raw, parent, source, graph = fixture(tmp_path)
    original = []; changed = []
    for i, (name, point) in enumerate({**SCAFFOLD, 'C2': (10, 0, 0), 'O2': (11, 0, 0)}.items(), 200):
        element = 'P' if name == 'P' else 'O' if name.startswith('O') else 'C'
        original.append(pdb_record('HETATM', i, name, 'DT', 'R', 4, element=element,
            x=point[0]+100, y=point[1], z=point[2]))
        target = 'S1' if name == 'O2' else name
        changed.append(pdb_record('HETATM', i-199, target, 'DF', 'R', 4,
            element='S' if target == 'S1' else element, x=point[0]+105, y=point[1]+10, z=point[2]))
    parent.write_text(parent.read_text().replace('END\n', '')+''.join(original)+'END\n')
    raw.write_text(raw.read_text().replace('END\n', '')+''.join(changed)+'END\n')
    if problem == 'unselected_coordinate':
        raw.write_text(raw.read_text().replace('  -0.530  -0.760  -1.308', '  -0.630  -0.760  -1.308'))
    if problem == 'selected_conect':
        for path in [raw, parent]:
            path.write_text(path.read_text().replace('CONECT    1    2', 'CONECT  200  201'))
    curated = tmp_path/'DF.cif'
    # The context transaction deliberately does not parse a curated placement
    # as a graph recipe; its bytes remain immutable for the existing placer.
    curated.write_text('data_DF\n# EXPLICIT CONTEXT-ONLY TOY SOURCE\n')
    actions = (graph, MutationAction('R:4', 'DT', 'DF', 'coot-parent-overlap', parent_code='DT'))
    snapshots = {p: p.read_bytes() for p in [raw, parent, source, curated]}
    result = prepare_construction_context(raw, parent, actions, {'ZZZ': source, 'DF': curated},
        {a.site: parent for a in actions}, tmp_path/'context.pdb',
        passthrough_sites=('R:4',) if problem == 'passthrough' else ())
    assert all(p.read_bytes() == data for p, data in snapshots.items())
    return result, raw


def test_mixed_curated_and_graph_context_preserves_all_coordinates(tmp_path):
    result, raw = mixed_context(tmp_path)
    report = result['receipt']
    assert report['status'] == 'CONTEXT_PREPARED'
    assert {(r['site'], r['atom']) for r in report['removed_atoms']} == {('Z:9', 'OP3')}
    assert report['eligible_sites'] == ['Z:9']
    assert {r['site'] for r in report['serial_repairs']} == {'Z:9', 'R:4'}
    before, after = atom_rows(raw), atom_rows(result['model'])
    assert set(before)-set(after) == {('Z', '9', ' ', 'OP3')}
    for key, line in after.items():
        assert line[11:] == before[key][11:]
        if key[0] != 'R' and key[1] != '9':
            assert line == before[key]
    assert len({line[6:11] for line in after.values()}) == len(after)
    assert [r for r in report['skipped_sites'] if r['site'] == 'R:4']
    assert report['serial_scope_extension']['sites'] == ['R:4']
    assert report['serial_scope_extension']['chemical_context'] == 'UNCHANGED; CURATED_SITES_ARE_NOT_OP3_CANDIDATES'


@pytest.mark.parametrize('problem', ['unselected_coordinate', 'selected_conect', 'passthrough'])
def test_mixed_scope_keeps_existing_authority_and_passthrough_guards(tmp_path, problem):
    result, raw = mixed_context(tmp_path, problem=problem)
    assert result['receipt']['status'] == 'RAW_CONTEXT_RETAINED'
    assert result['receipt']['serial_repairs'] == result['receipt']['removed_atoms'] == []
    assert result['model'].read_bytes() == raw.read_bytes()
