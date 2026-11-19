"""Contact measurements are observations, never pairing approval."""
import hashlib
import json

import pytest

from nasolve.topostitch_contacts import inspect_end_contacts
from .helpers import pdb_record
from .test_topostitch_coordinates import two_end_fixture
from .test_topostitch_periodic import cryst1


def contact_fixture(transform=lambda p: p):
    text, assignments = two_end_fixture()
    # Extra exocyclic atoms: synthetic coordinates for arithmetic, not an ideal DNA model.
    extras = [('A', 1, 'DG', 'N2', (0, 0, 0)),
              ('A', 1, 'DG', 'O6', (0, 3, 0)),
              ('C', 2, 'DC', 'O2', (2.8, 0, 0)),
              ('C', 2, 'DC', 'N4', (2.8, 3, 0)),
              ('A', 2, 'DA', 'N6', (0, 0, 3)),
              ('C', 1, 'DT', 'O4', (2.8, 0, 3))]
    additions = {(chain, resid): [] for chain, resid, *_ in extras}
    for i, (chain, resid, code, atom, xyz) in enumerate(extras):
        additions[chain, resid].append(pdb_record('ATOM', 200+i, atom, code, chain, resid,
            element=atom[0], x=xyz[0], y=xyz[1], z=xyz[2]).rstrip('\n'))
    expanded = []
    for line in text.splitlines():
        if line.startswith('ATOM'):
            expanded.extend(additions.pop((line[21], int(line[22:26])), []))
        expanded.append(line)
    lines = []
    for line in expanded:
        if line.startswith('ATOM'):
            xyz = transform(tuple(float(line[a:b]) for a, b in ((30,38),(38,46),(46,54))))
            line = line[:30] + ''.join(f'{x:8.3f}' for x in xyz) + line[54:]
        lines.append(line)
    return '\n'.join(lines)+'\nEND\n', assignments


def inspect(tmp_path, text=None, periodic=False):
    source, assignments = contact_fixture()
    model = tmp_path/'model.pdb'
    model.write_text(source if text is None else text)
    data = model.read_bytes()
    report = inspect_end_contacts(model, assignments, expected_sha256=hashlib.sha256(data).hexdigest(),
                                  max_distance_angstrom=15, periodic=periodic)
    assert model.read_bytes() == data
    assert str(tmp_path) not in json.dumps(report)
    return report


def test_contacts_use_library_roles_and_measured_geometry_without_acceptance(tmp_path):
    report = inspect(tmp_path)
    audit = report['contact_assessment']
    edge, = audit['candidates']
    gc, at = edge['residue_pairs']
    assert gc['recipe'] == 'GC' and at['recipe'] == 'AT'
    assert [len(p['bonds']) for p in (gc, at)] == [3, 2]
    assert gc['bonds'][0]['observed'] == pytest.approx(2.8)
    assert gc['bonds'][0]['deviation'] == pytest.approx(0)
    assert gc['bonds'][0]['atoms'][0]['atom_name'] == 'N2'
    assert gc['bonds'][0]['atoms'][1]['atom_name'] == 'O2'
    assert at['bonds'][1]['atoms'][0]['end_id'] == 'end2'  # T role is target
    assert len(gc['angles']) == 6 and len(at['angles']) == 2
    assert gc['plane_observation']['normal_angle_degrees'] == pytest.approx(0)
    assert audit['acceptance_evaluated'] is False and report['geometry_validated'] is False
    assert audit['library']['name'] == 'NARestraints'
    assert len(audit['library']['effective_catalog_sha256']) == 64
    assert report['changes'] == []
    assert json.loads(json.dumps(report, allow_nan=False)) == report


def test_missing_exocyclic_atom_is_incomplete_not_zero_distance(tmp_path):
    text, _ = contact_fixture()
    text = '\n'.join(l for l in text.splitlines() if not (l[12:16].strip() == 'N2' and l[21:26] == 'A   1'))
    audit = inspect(tmp_path, text)['contact_assessment']
    pair = audit['candidates'][0]['residue_pairs'][0]
    assert pair['bonds'][0]['observed'] is None
    assert pair['bonds'][0]['issues'][0]['code'] == 'MISSING_ATOM'
    assert pair['assessment'] == 'INCOMPLETE_MEASUREMENTS'
    assert pair['bonds'][1]['observed'] is not None


def test_zero_occupancy_contact_atom_is_not_measured(tmp_path):
    text, _ = contact_fixture()
    text = '\n'.join(l[:54]+'  0.00'+l[60:] if l[12:16].strip() == 'N2' else l
                     for l in text.splitlines())
    pair = inspect(tmp_path, text)['contact_assessment']['candidates'][0]['residue_pairs'][0]
    assert pair['bonds'][0]['observed'] is None
    assert pair['bonds'][0]['issues'][0]['code'] == 'UNUSABLE_OCCUPANCY'


def test_rigid_transform_preserves_contact_measurements(tmp_path):
    first = inspect(tmp_path)['contact_assessment']['candidates'][0]
    text, _ = contact_fixture(lambda p: (-p[1]+17, p[0]-4, p[2]+12))
    second = inspect(tmp_path, text)['contact_assessment']['candidates'][0]
    for left, right in zip(first['residue_pairs'], second['residue_pairs']):
        for kind in ('bonds', 'angles'):
            assert [v['observed'] for v in left[kind]] == pytest.approx([v['observed'] for v in right[kind]])


def test_periodic_contacts_use_recorded_target_image(tmp_path):
    pytest.importorskip('gemmi')
    text, _ = contact_fixture()
    # Shift only second end by one unit cell; its chosen image must undo this.
    lines = []
    for l in text.splitlines():
        if l.startswith('ATOM') and l[21] in 'CD':
            l = l[:30]+f'{float(l[30:38])+40:8.3f}'+l[38:]
        lines.append(l)
    original = inspect(tmp_path)['contact_assessment']['candidates'][0]['residue_pairs']
    result = inspect(tmp_path, cryst1((40,40,40,90,90,90))+'\n'.join(lines)+'\n', periodic=True)
    edge, = result['contact_assessment']['candidates']
    assert edge['target_image']['operator_xyz'] == 'x-1,y,z'
    for a, b in zip(original, edge['residue_pairs']):
        assert [v['observed'] for v in a['bonds']] == pytest.approx([v['observed'] for v in b['bonds']])


def test_source_drift_is_rejected_before_contact_measurement(tmp_path):
    text, assignments = contact_fixture()
    path = tmp_path/'model.pdb'
    path.write_text(text)
    with pytest.raises(ValueError, match='checksum'):
        inspect_end_contacts(path, assignments, expected_sha256='a'*64, max_distance_angstrom=15)


def test_screw_rotation_is_applied_to_every_contact_atom(tmp_path):
    gemmi = pytest.importorskip('gemmi')
    text, assignments = contact_fixture()
    cell = gemmi.UnitCell(40, 40, 40, 90, 90, 90)
    wanted = gemmi.Op('y,-x,z+1/4')
    inverse = wanted.inverse()
    lines = []
    for line in text.splitlines():
        if line.startswith('ATOM') and line[21] in 'CD':
            xyz = [float(line[a:b]) for a,b in ((30,38),(38,46),(46,54))]
            fractional = cell.fractionalize(gemmi.Position(*xyz))
            xyz = cell.orthogonalize(gemmi.Fractional(*inverse.apply_to_xyz(list(fractional))))
            line = line[:30]+''.join(f'{v:8.3f}' for v in xyz)+line[54:]
        lines.append(line)
    expected = inspect(tmp_path)['contact_assessment']['candidates'][0]['residue_pairs']
    actual = inspect(tmp_path, cryst1((40,40,40,90,90,90),'P 43')+'\n'.join(lines)+'\n', True)
    selected = [e for e in actual['contact_assessment']['candidates']
                if e['target_image']['operator_xyz'] == wanted.triplet()]
    edge, = selected
    for a,b in zip(expected, edge['residue_pairs']):
        for kind in ('bonds', 'angles'):
            assert [x['observed'] for x in a[kind]] == pytest.approx([x['observed'] for x in b[kind]])


def test_mapping_comes_from_library_and_effective_hash_changes(tmp_path, monkeypatch):
    from restraints import residue_library
    original = residue_library.load_residue_records
    before = inspect(tmp_path)['contact_assessment']['library']['effective_catalog_sha256']
    def renamed():
        records = original()
        for record in records:
            if record['Ligand code'] == 'DG': record['N2'] = 'Q2'
        return records
    monkeypatch.setattr(residue_library, 'load_residue_records', renamed)
    text, _ = contact_fixture()
    report = inspect(tmp_path, text.replace('  N2 ', '  Q2 '))['contact_assessment']
    bond = report['candidates'][0]['residue_pairs'][0]['bonds'][0]
    assert bond['atoms'][0]['atom_name'] == 'Q2'
    assert bond['observed'] == pytest.approx(2.8)
    assert report['library']['effective_catalog_sha256'] != before


def test_degenerate_angle_is_null_and_not_a_fabricated_zero(tmp_path):
    text, _ = contact_fixture()
    # A.C6 and A.N6 coincide; the angle at N6 is undefined.
    c6 = next(l[30:54] for l in text.splitlines() if l[12:16].strip() == 'C6' and l[21:26] == 'A   2')
    text = '\n'.join(l[:30]+c6+l[54:] if l[12:16].strip() == 'N6' and l[21:26] == 'A   2' else l
                     for l in text.splitlines())
    pair = inspect(tmp_path, text)['contact_assessment']['candidates'][0]['residue_pairs'][1]
    assert pair['angles'][1]['observed'] is None
    assert pair['angles'][1]['issues'] == [{'code': 'DEGENERATE_ANGLE'}]


def test_cli_contacts_flag_is_optional_and_report_remains_read_only(tmp_path, capsys):
    from dataclasses import asdict
    from nasolve.topostitch_inspect import main
    text, assignments = contact_fixture()
    model = tmp_path/'model.pdb'; model.write_text(text)
    manifest = tmp_path/'ends.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'kind': 'topostitch-end-assignments',
        'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'ends': [asdict(a) for a in assignments]}))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert main([str(model), str(manifest), '--radius', '15', '--contacts']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['contact_assessment']['candidates']
    assert report['workflow']['execution_state'] == 'NOT_ATTEMPTED'
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert main([str(model), str(manifest), '--radius', '15']) == 0
    assert 'contact_assessment' not in json.loads(capsys.readouterr().out)


def test_relocated_contact_input_preserves_report(tmp_path):
    from shutil import move
    text, assignments = contact_fixture()
    original = tmp_path/'original'; original.mkdir()
    model = original/'model.pdb'; model.write_text(text)
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    before = inspect_end_contacts(model, assignments, expected_sha256=digest, max_distance_angstrom=15)
    moved = tmp_path/'renamed.pdb'
    move(model, moved); original.rmdir()
    assert not original.exists()
    after = inspect_end_contacts(moved, assignments, expected_sha256=digest, max_distance_angstrom=15)
    assert before == after
