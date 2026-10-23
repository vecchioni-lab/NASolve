"""Curated placement keeps its rule while eligible DNA context is proved."""
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
    # This incomplete toy source cannot authorize graph context. Its explicit
    # placement still has the older, independent serial-field authority.
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


def curated_phosphate_context(tmp_path, *, mixed=True, problem=None):
    """Public canonical frame with a synthetic bad raw DF phosphate position."""
    from nasolve.synthetic_dna import prepare_free_five_prime_model

    raw, parent, source, graph = fixture(tmp_path)
    root = Path(__file__).parents[1]
    data, _ = prepare_free_five_prime_model((root/'MR_frames/5W6W/C_G.pdb').read_bytes())
    canonical = [line for line in data.decode().splitlines(keepends=True)
                 if line.startswith(('ATOM  ', 'HETATM')) and line[21] == 'A'
                 and line[22:26].strip() in {'18', '19', '20'}]
    incoming = next(line for line in canonical if line[22:26].strip() == '18'
                    and line[12:16].strip() == "O3'")
    incoming_xyz = tuple(float(incoming[i:i+8]) for i in (30, 38, 46))
    changed = []; phosphorus = None
    for line in canonical:
        if line[22:26].strip() == '19':
            line = line[:17]+' DF'+line[20:]
            name = line[12:16].strip()
            if name == 'O2':
                line = line[:12]+' S1 '+line[16:76]+' S'+line[78:]
            if name == 'P':
                phosphorus = line
                point = (incoming_xyz[0]+.2, *incoming_xyz[1:])
                line = line[:30]+''.join(f'{v:8.3f}' for v in point)+line[54:]
            line = line[:6]+f'{len(changed)+1:5d}'+line[11:]
        changed.append(line)
    assert phosphorus is not None
    point = tuple(float(phosphorus[i:i+8]) for i in (30, 38, 46))
    changed.append(pdb_record('HETATM', 30, 'OP3', 'DF', 'A', 19, element='O',
                             x=point[0], y=point[1], z=point[2]+1.5))
    if mixed:
        parent.write_text(parent.read_text().replace('END\n', '')+''.join(canonical)+'END\n')
        raw.write_text(raw.read_text().replace('END\n', '')+''.join(changed)+'END\n')
    else:
        parent.write_text(''.join(canonical)+'END\n')
        raw.write_text(''.join(changed)+'END\n')
    curated = tmp_path/'DF.cif'
    curated.write_bytes((root/'src/nasolve/data/ligands/DF.cif').read_bytes())
    if problem == 'invalid_source':
        curated.write_text(curated.read_text().replace('DNA', 'RNA'))
    elif problem == 'missing_parent':
        parent.write_text(''.join(line for line in parent.read_text().splitlines(keepends=True)
            if not (line.startswith(('ATOM  ', 'HETATM')) and line[21] == 'A'
                    and line[22:26].strip() == '19' and line[12:16].strip() == "C3'")))
    elif problem == 'unselected_coordinate':
        raw.write_text(raw.read_text().replace(incoming, incoming[:30]+
            f'{incoming_xyz[0]+.1:8.3f}'+incoming[38:]))
    elif problem == 'selected_conect':
        serial = int(next(line for line in canonical if line[22:26].strip() == '19'
                          and line[12:16].strip() == 'P')[6:11])
        for path in (raw, parent):
            path.write_text(path.read_text().replace('END\n', f'CONECT{serial:5d}{serial+1:5d}\nEND\n'))
    action = MutationAction('A:19', 'DT', 'DF', 'coot-parent-overlap', parent_code='DT')
    actions = (graph, action) if mixed else (action,)
    sources = {'ZZZ': source, 'DF': curated} if mixed else {'DF': curated}
    snapshots = {path: path.read_bytes() for path in (raw, parent, source, curated)}
    result = prepare_construction_context(raw, parent, actions, sources,
        {item.site: parent for item in actions}, tmp_path/'context.pdb',
        passthrough_sites=('A:19',) if problem == 'passthrough' else (),
        allow_op3_sites=('A:19',) if problem == 'explicit_terminal' else ())
    assert all(path.read_bytes() == data for path, data in snapshots.items())
    return result, raw, parent


@pytest.mark.parametrize('mixed', [False, True])
def test_source_graph_curated_context_uses_discarded_parent_shadow_only(tmp_path, mixed):
    result, raw, parent = curated_phosphate_context(tmp_path, mixed=mixed)
    report = result['receipt']
    assert report['status'] == 'CONTEXT_PREPARED', report
    expected = {('A:19', 'OP3')} | ({('Z:9', 'OP3')} if mixed else set())
    assert {(row['site'], row['atom']) for row in report['removed_atoms']} == expected
    assert report['curated_context']['sites'] == report['curated_context']['candidate_sites'] == ['A:19']
    assert report['curated_context']['scope'] == 'SOURCE_GRAPH_AND_DISCARDED_PARENT_SCAFFOLD_SHADOW_ONLY; FINAL_CURATED_PLACEMENT_UNCHANGED'
    assert report['curated_context']['source_graphs']['A:19']['component'] == 'DF'
    assert 'serial_scope_extension' not in report
    before, after, shadow = map(atom_rows, (raw, result['model'], result['shadow']))
    assert set(before)-set(after) == {('A', '19', ' ', 'OP3')} | ({('Z', '9', ' ', 'OP3')} if mixed else set())
    for key, line in after.items():
        assert line[11:] == before[key][11:], 'Only proved deletions and selected serial fields may transfer'
    p = ('A', '19', ' ', 'P')
    assert after[p][30:54] == before[p][30:54]
    assert shadow[p][30:54] == atom_rows(parent)[p][30:54]
    assert shadow[p][30:54] != before[p][30:54]


@pytest.mark.parametrize('problem', ['invalid_source', 'missing_parent', 'unselected_coordinate',
                                     'selected_conect', 'passthrough', 'explicit_terminal'])
def test_curated_context_cannot_override_existing_authority_or_chemical_guards(tmp_path, problem):
    result, raw, _ = curated_phosphate_context(tmp_path, problem=problem)
    assert result['receipt']['status'] == 'RAW_CONTEXT_RETAINED'
    assert result['receipt']['serial_repairs'] == result['receipt']['removed_atoms'] == []
    assert result['model'].read_bytes() == raw.read_bytes()
    if problem in {'invalid_source', 'missing_parent', 'passthrough'}:
        assert 'curated_context' not in result['receipt']
