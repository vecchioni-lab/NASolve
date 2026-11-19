"""Existing scalar mathematics applied to authenticated selected final sites."""
from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch
import pytest


def test_exact_owner_reads_nontriple_scalar_geometry_after_relocation(tmp_path, monkeypatch):
    from tests.test_refinement_parallelity import completed
    from nasolve.refinement_parallelity import read_execution_scalar_geometry, read_execution_chemistry
    run, result, _, child, _, _ = completed(tmp_path, monkeypatch, chemistry='bent', declared_sites=True)
    old = run.parents[1]; moved = tmp_path / 'relocated'; old.rename(moved)
    run = moved / run.relative_to(old); model = run / child['model']['relative_path']
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    args = dict(checkpoint=child['id'], parent=child['parent'], model=model)
    with patch('subprocess.Popen', side_effect=AssertionError('Cold read only')):
        report = read_execution_scalar_geometry(run, child['outputs']['parallelity_execution'], **args)
        assert read_execution_chemistry(run, child['outputs']['parallelity_execution'], **args) == result.statistics['chemical_geometry']
    assert not old.exists() and report['model_sha256'] == sha256(model.read_bytes()).hexdigest()
    assert report['status'] == 'REVIEW' and report['scientific_approval'] == 'NOT_RUN'
    assert report['coordinate_precision'] == 'FULL_NATIVE' and not report['automatic_adoption']
    assert report['measurements']['angle'] and report['declared_sites']['A:1']['component'] == 'Q17'
    assert report['native_residuals'] == 'UNASSESSED'
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == value for p, value in before.items())
    model.write_bytes(model.read_bytes() + b'REMARK changed\n')
    with pytest.raises(ValueError, match='differs from the checkpoint model'):
        read_execution_scalar_geometry(run, child['outputs']['parallelity_execution'], **args)


def selected(tmp_path, *, code='Q17'):
    from tests.test_cif_captured_geometry import native
    from tests.test_cif_triple_bond_audit import fixture
    from nasolve.cif_refinement_sites import validate_snapshot
    source, _ = fixture(tmp_path, code)
    whole = native(); names = ['L', 'X', 'Y', 'R']; global_indices = [11, 18, 29, 42]
    atoms = deepcopy(whole['atoms']); labels = ['outside_' + str(i) for i in range(61)]
    for i, atom in enumerate(atoms):
        atom.update(i_seq=global_indices[i], atom_id=names[i], element='C', occupancy=1.)
        atom['identity'].update(chain_id='A', resseq='1', resname=code)
        labels[global_indices[i]] = atom['label']
    details = deepcopy(whole['geometry']['proxy_details'])
    for rows in details.values():
        for row in rows: row['i_seqs'] = [global_indices[i] for i in row['i_seqs']]
    observation = dict(policy_id='native-refinement-selected-sites-v1', status='OBSERVED',
        sites=[dict(site='A:1', component=code)], scope='ACTUAL_NATIVE_MANAGER_INTRA_SITE_HEAVY_ATOMS',
        coordinate_precision='FULL_NATIVE', model_state_sha256='a'*64, full_atom_count=len(labels),
        atoms=atoms, monomer_mappings=dict(rows=[dict(site='A:1', metadata=dict(effective_definition=dict(bonds=[])))]),
        geometry=dict(proxy_details=details, full_proxy_counts={k:len(v)+7 for k,v in details.items()}),
        definition_binding='EXACT_OBSERVED_SUMMARY_OBJECT', scientific_approval='NOT_RUN')
    validate_snapshot(observation, observation['sites'], labels)
    return {'A:1': (source, code)}, observation


@pytest.mark.parametrize('code', ['Q17', 'XYZ'])
def test_sparse_global_indices_and_partial_counts_keep_known_scalar_geometry(tmp_path, code):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    projections, observation = selected(tmp_path, code=code); original = deepcopy(observation)
    report = _observed_scalar_geometry(projections, observation)
    bond, angle, hand = [report['measurements'][k][0] for k in ('bond_simple','angle','chirality')]
    assert (bond['observed'], angle['observed'], hand['observed']) == (1., 90., 1.)
    assert (bond['nominal_deviation'], angle['nominal_deviation'], hand['nominal_deviation']) == pytest.approx((2.,2.,1.))
    assert bond['i_seqs'] == [11,18] and angle['i_seqs'] == [18,11,29]
    assert report['atom_count'] == 4 and report['full_atom_count'] == 61
    assert report['captured_proxy_counts']['bond_simple'] == 1 and report['full_proxy_counts']['bond_simple'] == 8
    assert report['deferred_proxy_kinds']['dihedral']['count'] == 0
    assert report['full_proxy_counts']['dihedral'] == 7
    assert hand['sign_agreement'] is True and report['status'] == 'REVIEW'
    assert observation == original


def test_final_native_precision_and_relative_hand_are_not_rounded_or_reclassified(tmp_path):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    projections, observation = selected(tmp_path)
    observation['atoms'][1]['xyz'][0] = -1.000123456789
    report = _observed_scalar_geometry(projections, observation)
    assert report['measurements']['bond_simple'][0]['observed'] == 1.000123456789
    assert report['measurements']['chirality'][0]['sign_agreement'] is False
    assert report['absolute_stereochemistry'] == 'UNASSESSED'
    observation['geometry']['proxy_details']['chirality'][0]['both_signs'] = True
    row = _observed_scalar_geometry(projections, observation)['measurements']['chirality'][0]
    assert row['sign_agreement'] is None and row['difference'] == pytest.approx(.500123456789)


def test_missing_conventions_zero_weight_and_symmetry_are_not_successes(tmp_path):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    projections, observation = selected(tmp_path); details=observation['geometry']['proxy_details']
    details['angle'][0]['weight'] = 0.
    details['chirality'][0]['both_signs'] = None
    details['bond_simple'][0]['symmetry_operation'] = '-x,y,z'
    report = _observed_scalar_geometry(projections, observation)
    assert report['measurements']['angle'][0]['status'] == 'UNWEIGHTED'
    assert report['measurements']['chirality'][0]['status'] == 'UNSUPPORTED'
    assert report['measurements']['bond_simple'][0]['status'] == 'UNSUPPORTED'
    assert all(r['nominal_deviation'] is None for rows in report['measurements'].values() for r in rows)
    assert not report['automatic_adoption'] and report['native_residuals'] == 'UNASSESSED'


@pytest.mark.parametrize('defect', ['element', 'component', 'duplicate_index', 'proxy_label'])
def test_source_identity_or_endpoint_conflict_refuses_scalar_report(tmp_path, defect):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    projections, observation = selected(tmp_path)
    if defect == 'element': observation['atoms'][0]['element'] = 'N'
    elif defect == 'component': observation['atoms'][0]['identity']['resname'] = 'BAD'
    elif defect == 'duplicate_index': observation['atoms'][1]['i_seq'] = 11
    else: observation['geometry']['proxy_details']['angle'][0]['atoms'][0] = 'different'
    with pytest.raises(ValueError): _observed_scalar_geometry(projections, observation)


def test_empty_scalar_capture_and_unavailable_capture_stay_unassessed(tmp_path):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    from nasolve.cif_refinement_sites import unavailable
    projections, observation = selected(tmp_path)
    report = _observed_scalar_geometry(projections, unavailable(observation['sites'], 'No native observation'))
    assert report['status'] == 'UNASSESSED' and report['atom_count'] is None
    assert report['full_proxy_counts'] is None and not report['analysis_completed']
    for kind in ('bond_simple','angle','chirality'): observation['geometry']['proxy_details'][kind] = []
    report = _observed_scalar_geometry(projections, observation)
    assert report['status'] == 'UNASSESSED' and report['analysis_completed']
    assert 'No captured' in report['reason']


def test_source_change_during_calculation_refuses_result(tmp_path, monkeypatch):
    from nasolve.refinement_chemistry import _observed_scalar_geometry
    import nasolve.cif_captured_geometry as geometry
    projections, observation = selected(tmp_path); original = geometry._geometry_measurements
    def changed(*args):
        result = original(*args); source=projections['A:1'][0]
        source.write_text(source.read_text()+'# changed during read\n'); return result
    monkeypatch.setattr(geometry, '_geometry_measurements', changed)
    with pytest.raises(ValueError, match='source projection changed'):
        _observed_scalar_geometry(projections, observation)


@pytest.mark.parametrize('chemistry', [None, 'unavailable'])
def test_owner_does_not_invent_missing_capture(tmp_path, monkeypatch, chemistry):
    from tests.test_refinement_parallelity import completed
    from nasolve.refinement_parallelity import read_execution_scalar_geometry
    run, result, _, child, _, _ = completed(tmp_path, monkeypatch, chemistry=chemistry, declared_sites=True)
    report=read_execution_scalar_geometry(run, child['outputs']['parallelity_execution'],
        checkpoint=child['id'], parent=child['parent'], model=result.model_path)
    if chemistry is None: assert report is None
    else: assert report['status']=='UNASSESSED' and report['atom_count'] is None


@pytest.mark.parametrize('reader', ['read_execution_scalar_geometry', 'read_execution_trigonal_geometry',
                                    'read_execution_chemistry', 'read_execution_chemistry_sites',
                                    'read_execution_plane_geometry'])
def test_projection_change_between_owner_validation_and_report_is_refused(tmp_path, monkeypatch, reader):
    from tests.test_refinement_parallelity import completed
    from nasolve import refinement_parallelity as owner
    from nasolve.checkpoints import CheckpointError
    run, result, _, child, _, _ = completed(tmp_path, monkeypatch, chemistry='bent', declared_sites=True)
    original = owner._selected_chemistry_observation
    def change_after_validation(*args, **kwargs):
        selected = original(*args, **kwargs)
        source = next(iter(selected[1].values()))[0]
        source.write_text(source.read_text() + '# changed after owner validation\n')
        return selected
    monkeypatch.setattr(owner, '_selected_chemistry_observation', change_after_validation)
    with pytest.raises((CheckpointError, ValueError)):
        getattr(owner, reader)(run, child['outputs']['parallelity_execution'],
            checkpoint=child['id'], parent=child['parent'], model=result.model_path)
