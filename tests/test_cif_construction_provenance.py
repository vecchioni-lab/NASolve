"""Synthetic stage evidence: no Coot or Phenix execution."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from tests.test_cif_captured_geometry import native as scalar_fixture


def fixture_native():
    n = scalar_fixture()
    for atom, name in zip(n['atoms'], ['C0', 'C1', 'C2', 'N3']):
        atom.update(atom_id=name, element='C')
    n['geometry']['sites_cart_exact'][1][0] = 5.
    n['geometry']['proxy_details']['bond_simple'][0].update(distance_ideal=1., weight=100.)
    return n


def pdb(path, distance=1., code='ZZZ', *, duplicate=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    coords = [(0., 0., 0.), (distance, 0., 0.), (0., 1., 0.), (0., 0., 1.)]
    lines = [f'HETATM{i:5d} {name:>4} {code:>3} Z{9:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n'
             for i, (name, (x, y, z)) in enumerate(zip(['C0', 'C1', 'C2', 'N3'], coords), 1)]
    path.write_text(''.join(lines + ([lines[0]] if duplicate else [])) + 'END\n')
    return path


def test_generic_stage_comparison_locates_a_new_distortion_without_claiming_a_cause(tmp_path):
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.cif_construction_provenance import audit_construction_stages
    n = fixture_native(); g = review_captured_geometry(n)
    stages = {'mr_input': pdb(tmp_path/'mr.pdb', code='DG'),
              'coot_raw': pdb(tmp_path/'raw.pdb'),
              'restored': pdb(tmp_path/'restored.pdb', distance=5.),
              'prepared': pdb(tmp_path/'prepared.pdb', distance=5.)}
    before = {p: p.read_bytes() for p in stages.values()}
    parent = pdb(tmp_path/'parent.pdb', distance=5., code='DG')
    r = audit_construction_stages(n, g, stages, {'Z:9': parent})
    finding = next(x for x in r['findings'] if x['kind'] == 'bond_simple')
    assert finding['first_observed_outlier_stage'] == 'restored'
    assert finding['stages'][0]['status'] == 'COMPONENT_NOT_YET_PRESENT'
    assert finding['stages'][1]['nominal_deviation'] == 0.
    assert finding['stages'][2]['nominal_deviation'] == 40.
    assert finding['threshold_crossings'] == [{'before': 'coot_raw', 'after': 'restored'}]
    copied = next(x for x in r['parent_coordinate_comparisons']['Z:9'] if x['atom_id'] == 'C1')
    assert copied['raw_to_parent'] == 4. and copied['restored_to_parent'] == 0.
    assert copied['observed_parent_coordinate_copy'] is True
    assert r['root_cause'] == 'NOT_ESTABLISHED' and r['status'] == 'REVIEW'
    assert all(p.read_bytes() == data for p, data in before.items())


def test_missing_intermediate_stage_never_becomes_a_proven_transition(tmp_path):
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.cif_construction_provenance import audit_construction_stages
    n = fixture_native(); g = review_captured_geometry(n)
    r = audit_construction_stages(n, g, {'coot_raw': pdb(tmp_path/'raw.pdb'),
        'restored': None, 'prepared': pdb(tmp_path/'prepared.pdb', distance=5.)})
    f = next(x for x in r['findings'] if x['kind'] == 'bond_simple')
    assert f['threshold_crossings'] == [] and f['stages'][1]['status'] == 'NOT_PRESENT'
    assert f['first_observed_outlier_stage'] == 'prepared'


@pytest.mark.parametrize('defect', ['duplicate', 'multiple_models', 'wrong_element'])
def test_ambiguous_or_incompatible_atom_correspondence_is_not_silently_used(tmp_path, defect):
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.cif_construction_provenance import audit_construction_stages
    n = fixture_native(); g = review_captured_geometry(n)
    p = pdb(tmp_path/'stage.pdb', duplicate=defect == 'duplicate')
    if defect == 'multiple_models':
        s=p.read_text();p.write_text('MODEL        1\n'+s+'ENDMDL\nMODEL        2\n'+s+'ENDMDL\n')
    elif defect == 'wrong_element': p.write_text(p.read_text().replace('           C\n', '           N\n'))
    if defect == 'wrong_element':
        r = audit_construction_stages(n, g, {'prepared': p})
        assert all(f['stages'][0]['status'] == 'ELEMENT_MISMATCH' for f in r['findings'])
    else:
        with pytest.raises(ValueError): audit_construction_stages(n, g, {'prepared': p})


def test_script_references_are_parsed_without_execution_and_rebase_only_from_the_declared_run(tmp_path):
    from nasolve.cif_construction_provenance import declared_coot_references
    text = """import coot
raise RuntimeError('NEVER EXECUTE')
coot.handle_read_draw_molecule('/old/run/PostMR/Model/mr_solution.pdb')
coot.read_cif_dictionary('/external/library/private.cif')
coot.write_pdb_file(imol, '/old/run/PostMR/Coot/parent_Z_9_DG.pdb')
print('NASOLVE_OVERLAP', 'Z:9', overlap_status)
"""
    r = declared_coot_references(text, '/old/run')
    assert r['parents'] == {'Z:9': 'PostMR/Coot/parent_Z_9_DG.pdb'}
    assert r['inputs'] == ['PostMR/Model/mr_solution.pdb']
    assert r['uncollected_external_paths'] == ['/external/library/private.cif']
    with pytest.raises(ValueError): declared_coot_references(text.replace('parent_Z_9_DG.pdb', '../outside.pdb'), '/old/run')


def test_hash_bound_run_snapshot_refuses_replacement_and_preserves_missing_evidence(tmp_path):
    from nasolve.cif_construction_provenance import snapshot_construction_run
    run = tmp_path/'run'; prepared = pdb(run/'PostMR/Model/prepared_model.pdb')
    binding = {'path': 'PostMR/Model/prepared_model.pdb', 'sha256': hashlib.sha256(prepared.read_bytes()).hexdigest(), 'size': prepared.stat().st_size}
    before = prepared.read_bytes()
    result = snapshot_construction_run(run, tmp_path/'snapshot', binding, '/old/run')
    assert result['stages']['prepared'] is not None and result['stages']['coot_raw'] is None
    assert prepared.read_bytes() == before
    prepared.write_bytes(before+b'changed')
    with pytest.raises(ValueError, match='binding'): snapshot_construction_run(run, tmp_path/'other', binding, '/old/run')


def test_snapshot_rejects_source_symlinks_and_output_inside_the_run(tmp_path):
    from nasolve.cif_construction_provenance import snapshot_construction_run
    run = tmp_path/'run'; prepared = pdb(run/'PostMR/Model/prepared_model.pdb')
    binding={'path':'PostMR/Model/prepared_model.pdb','sha256':hashlib.sha256(prepared.read_bytes()).hexdigest(),'size':prepared.stat().st_size}
    with pytest.raises(ValueError): snapshot_construction_run(run,run/'output',binding,'/old/run')
    (run/'PostMR/Coot').mkdir();(run/'PostMR/Coot/coot.log').symlink_to(prepared)
    with pytest.raises(ValueError): snapshot_construction_run(run,tmp_path/'out',binding,'/old/run')


def test_model_binding_is_rechecked_if_the_source_changes_between_reads(tmp_path, monkeypatch):
    from nasolve.cif_construction_provenance import snapshot_construction_run
    run=tmp_path/'run';prepared=pdb(run/'PostMR/Model/prepared_model.pdb')
    binding={'path':'PostMR/Model/prepared_model.pdb','sha256':hashlib.sha256(prepared.read_bytes()).hexdigest(),'size':prepared.stat().st_size}
    read=Path.read_bytes;changed=False
    def changing(path):
        nonlocal changed
        data=read(path)
        if path==prepared and not changed:
            changed=True;path.write_bytes(data+b'changed')
        return data
    monkeypatch.setattr(Path,'read_bytes',changing)
    with pytest.raises(ValueError,match='binding'):snapshot_construction_run(run,tmp_path/'out',binding,'/old/run')
