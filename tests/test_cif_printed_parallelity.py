"""Printed restraint observations must retain every group and each plane's atoms."""
from hashlib import sha256
import pytest
from nasolve.cif_printed_parallelity import parse_printed_parallelity, read_printed_parallelity

HEADER = '    plane 1                plane 2                residual  delta(deg) sigma'


def label(atom, chain='A'):
    return f'pdb=" {atom:<4} XAA {chain}   1 "'


def block(first, second, values='1.23e+01  4.5678  0.0270'):
    lines = [HEADER]
    for index in range(max(len(first), len(second))):
        left = label(first[index]) if index < len(first) else ''
        right = label(second[index], 'B') if index < len(second) else ''
        lines.append(f'    {left:<25} {right:<25}' + ('  ' + values if index == 0 else ''))
    return '\n'.join(lines)


def section(blocks, count=None, origin='User supplied'):
    count = len(blocks) if count is None else count
    return f'Parallelity | {origin} | restraints: {count}\nSorted by residual:\n' + '\n\n'.join(blocks) + '\n'


def test_all_blocks_survive_blank_lines_and_unequal_planes_in_both_orders():
    text = section([block(['N1', 'C2', 'N3'], ['X1', 'X2', 'X3', 'X4']),
                    block(['Y1', 'Y2', 'Y3', 'Y4'], ['Z1', 'Z2', 'Z3'])])
    result = parse_printed_parallelity(text)
    assert result['status'] == 'OBSERVED'
    assert result['observed_restraints'] == 2
    rows = result['sections'][0]['restraints']
    assert rows[0]['plane_1'] == [label(n) for n in ['N1', 'C2', 'N3']]
    assert rows[0]['plane_2'] == [label(n, 'B') for n in ['X1', 'X2', 'X3', 'X4']]
    assert rows[1]['plane_1'][-1] == label('Y4')
    assert rows[1]['plane_2'] == [label(n, 'B') for n in ['Z1', 'Z2', 'Z3']]
    assert rows[0]['printed_values'] == {'residual': '1.23e+01', 'delta_degrees': '4.5678', 'sigma': '0.0270'}
    assert 'weight' not in rows[0]
    assert result['source_sha256'] == sha256(text.encode()).hexdigest()
    assert result['scientific_approval'] == 'NOT_ASSESSED'


def test_multiple_origins_and_other_restraint_sections_do_not_merge_groups():
    one = block(['A1', 'A2', 'A3'], ['B1', 'B2', 'B3'])
    text = 'Bond | covalent geometry | restraints: 1\nother printed bond text\n'
    text += section([one], origin='First origin') + '\n' + section([one], origin='Second origin')
    text += '\nNonbonded | unspecified | interactions: 0\n'
    result = parse_printed_parallelity(text)
    assert [s['origin'] for s in result['sections']] == ['First origin', 'Second origin']
    assert result['observed_restraints'] == 2  # identical observations are not deduplicated


def test_no_printed_section_is_not_evidence_for_zero_native_restraints():
    result = parse_printed_parallelity('Bond | covalent geometry | restraints: 0\n')
    assert result['status'] == 'NOT_RECORDED' and result['observed_restraints'] is None
    empty = parse_printed_parallelity(section([]))
    assert empty['status'] == 'OBSERVED' and empty['observed_restraints'] == 0


@pytest.mark.parametrize('transform', [
    lambda s: s.replace('restraints: 1', 'restraints: 2'),
    lambda s: s.replace('restraints: 1', 'restraints: 0'),
    lambda s: s.replace('restraints: 1', 'restraints: broken'),
    lambda s: s.replace('restraints: 1', 'interactions: 1'),
    lambda s: s.replace('Sorted by residual:', 'Sorted by unknown:'),
    lambda s: s.replace('delta(deg)', 'different-units'),
    lambda s: s.replace('1.23e+01', 'nan'),
    lambda s: s.replace('1.23e+01', 'inf'),
    lambda s: s.replace('1.23e+01  4.5678', '1.23e+01  extra  4.5678'),
    lambda s: s.replace(label('A3'), label('A2')),
    lambda s: s.replace(label('A3'), ' ' * len(label('A3'))),
    lambda s: s.replace(label('A3'), ' ' + label('A3')),
    lambda s: s + 'unrecognized trailing content\n',
])
def test_malformed_or_incomplete_evidence_refuses_instead_of_returning_partial_rows(transform):
    text = section([block(['A1', 'A2', 'A3'], ['B1', 'B2', 'B3'])])
    with pytest.raises(ValueError):
        parse_printed_parallelity(transform(text))


def test_unbound_table_header_refuses_even_without_a_section():
    with pytest.raises(ValueError):
        parse_printed_parallelity(block(['A1', 'A2', 'A3'], ['B1', 'B2', 'B3']))


def test_read_only_relocation_and_printed_zero_sigma(tmp_path):
    original = tmp_path / 'original'; original.mkdir()
    path = original / 'final.geo'
    path.write_text(section([block(['A1', 'A2', 'A3'], ['B1', 'B2', 'B3'], values='0  -0.0001  0.0000')]))
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    result = read_printed_parallelity(path)
    moved = tmp_path / 'moved'; original.rename(moved)
    assert not original.exists()
    assert read_printed_parallelity(moved / 'final.geo') == result
    assert ((moved / 'final.geo').read_bytes(), (moved / 'final.geo').stat().st_mtime_ns) == before
    assert result['sections'][0]['restraints'][0]['values']['sigma'] == 0.0


def test_file_change_during_observation_is_not_accepted(tmp_path, monkeypatch):
    import nasolve.cif_printed_parallelity as module
    path = tmp_path / 'final.geo'
    path.write_text(section([block(['A1', 'A2', 'A3'], ['B1', 'B2', 'B3'])]))
    original = module.parse_printed_parallelity
    def changing(text):
        result = original(text)
        path.write_text('changed')
        return result
    monkeypatch.setattr(module, 'parse_printed_parallelity', changing)
    with pytest.raises(ValueError, match='changed'):
        module.read_printed_parallelity(path)
