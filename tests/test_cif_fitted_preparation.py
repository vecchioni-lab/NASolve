"""A fitted sugar may keep the parent's restraints only when a new native read verifies them."""
from copy import deepcopy

import pytest

from tests.test_cif_native_parent_chemistry import original
from tests.test_cif_postmr_publication import alternative_preparation


def test_geometry_check_accepts_motion_and_checks_force_identity_and_all_families(original):
    from nasolve.cif_fitted_preparation import compare_fit_mechanics

    child = deepcopy(original)
    child['atoms'][1]['xyz'][0] += 0.5
    assert compare_fit_mechanics(original, child)['bond_simple'] == 1
    for defect in ('weight', 'new bond', 'missing family', 'unused input', 'component', 'origin', 'request'):
        other = deepcopy(child)
        geometry = other['geometry']
        if defect == 'weight':
            geometry['proxy_details']['bond_simple'][0]['weight'] -= 1
        elif defect == 'new bond':
            geometry['proxy_details']['bond_simple'].append(deepcopy(geometry['proxy_details']['bond_simple'][0]))
            geometry['proxy_counts']['bond_simple'] += 1
        elif defect == 'missing family':
            del geometry['proxy_details']['bond_asu']
        elif defect == 'unused input':
            other['unused_definitions'].append('geometry_restraints.edits.bond.sigma')
        elif defect == 'component':
            other['monomer_mappings']['rows'][0]['chem_mod_ids']['ids'].append('other')
        elif defect == 'origin':
            other['restraint_policy']['origin_ids']['edits'] = 99
        else:
            geometry['custom_proxy_requests'].append({'kind':'bond'})
        with pytest.raises(ValueError):
            compare_fit_mechanics(original, other)


def test_publication_cli_forwards_an_exact_sugar_fit_and_receipt(tmp_path, monkeypatch, capsys):
    from nasolve import cli, cif_postmr_publication

    def publish(run, *, attempt_number, sugar_fit, native_receipt):
        assert (run, attempt_number, sugar_fit, native_receipt) == (tmp_path, 2, 3, tmp_path/'native_receipt.json')
        return {'message':'Fitted sugar for review.', 'readyset':{'status':'COMPLETED'}}, ()
    monkeypatch.setattr(cif_postmr_publication, 'publish_checked_preparation_with_notes', publish)
    assert cli.main(['cif-doctor','publish-preparation',str(tmp_path),'--attempt','2',
                     '--sugar-fit','3','--native-receipt',str(tmp_path/'native_receipt.json')]) == 0
    assert 'Checkpoint: postmr' in capsys.readouterr().out


def test_checkpoint_keeps_the_fitted_choice_and_rechecks_it(tmp_path, monkeypatch):
    from dataclasses import replace
    from hashlib import sha256
    from nasolve import checkpoints, cif_fitted_preparation as fitted
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from tests.test_cif_postmr_publication import setup, snapshot

    run, exact, _ = setup(tmp_path, monkeypatch)
    original_model = exact['runtime']['model']
    exact['construction_inputs']['furanose_substitution'] = {
        'unfitted_pairing_edge_seed':True, 'context':{'site':'A:1'}, 'code':'DA'}
    model = run/'PostMR/fitted.pdb'
    model.write_bytes(original_model.read_bytes()+b'REMARK fit fixture\n')
    receipt = tmp_path/'native_receipt.json'
    receipt.write_bytes(b'proof fixture')
    pin = sha256(receipt.read_bytes()).hexdigest()
    checked_calls = []

    def bind(root, checked, data, number, *, native_receipt=None, may_freeze=False):
        assert root == run and checked.model_path == original_model and checked.local_fit_site == 'A:1'
        assert data == exact and number == 2
        checked_calls.append(may_freeze)
        if may_freeze:
            assert native_receipt == receipt
        return replace(checked, model_path=model, local_fit_site=None), {
            'fit_number':2, 'native_receipt_sha256':pin, 'site':'A:1'}

    monkeypatch.setattr(fitted, 'bind_fitted_preparation', bind)
    with pytest.raises(ValueError, match='requires an exact sugar fit'):
        publish_checked_preparation(run, attempt_number=1, native_receipt=receipt)
    with pytest.raises(ValueError, match='construction seed'):
        publish_checked_preparation(run, attempt_number=1)
    def planned_actions(report, source, *, run_directory, furanose_target):
        assert run_directory == run and furanose_target == ('A:1', 'DA')
        return []  # This registry fixture has an empty mutation card.
    monkeypatch.setattr('nasolve.postmr.build_mutation_plan', planned_actions)
    actual = publish_checked_preparation(run, attempt_number=1, sugar_fit=2, native_receipt=receipt)
    assert actual['prepared_sha256'] == sha256(model.read_bytes()).hexdigest()
    assert actual['checked_preparation']['fitted_sugar']['fit_number'] == 2
    receipt.unlink()
    before = snapshot(run)
    _, registry, results = checkpoints._read_registry_with_preparations(run)
    assert results[1][0].model_path == model
    assert checkpoints.inherited_paths(registry['checkpoints'][0], run)['model'] == model
    assert publish_checked_preparation(run, attempt_number=1, sugar_fit=2) == actual
    with pytest.raises(ValueError, match='different fitted preparation'):
        publish_checked_preparation(run, attempt_number=1, sugar_fit=1)
    with pytest.raises(ValueError, match='different fitted preparation'):
        publish_checked_preparation(run, attempt_number=1)
    assert checked_calls == [True, False, False] and snapshot(run) == before


def test_fitted_alternative_reopens_without_selecting_it(alternative_preparation, monkeypatch):
    from dataclasses import replace
    from nasolve import checkpoints, cif_fitted_preparation

    publication, run, results, _ = alternative_preparation
    second = results[2]
    second['construction_inputs']['furanose_substitution'] = {
        'unfitted_pairing_edge_seed':True, 'context':{'site':'A:1'}, 'code':'DA'}
    model = run/'PostMR/alternative-fit.pdb'
    model.write_bytes(second['runtime']['model'].read_bytes() + b'REMARK local fit\n')
    def bind(root, checked, exact, number, **options):
        assert root == run and exact == second and checked.model_path == second['runtime']['model'] and number == 1
        return replace(checked, model_path=model, local_fit_site=None), {'fit_number':1}
    monkeypatch.setattr(cif_fitted_preparation, 'bind_fitted_preparation', bind)
    monkeypatch.setattr('nasolve.postmr.build_mutation_plan', lambda *args, **kwargs: [])
    publication.publish_preparation_alternative(run, attempt_number=2, sugar_fit=1)
    _, registry, verified = checkpoints._read_registry_with_preparations(run)
    root, alternative = registry['checkpoints']
    assert registry['current'] == root['id'] == 'postmr'
    assert alternative['id'] == 'prepare-002' and alternative['parent'] == 'postmr'
    assert checkpoints.inherited_paths(root, run)['model'] == results[1]['runtime']['model']
    assert checkpoints.inherited_paths(alternative, run)['model'] == verified[2][0].model_path == model
    with pytest.raises(ValueError, match='different fitted preparation'):
        publication.publish_preparation_alternative(run, attempt_number=2, sugar_fit=2)


def test_only_receipt_files_are_archived_and_no_existing_archive_is_replaced(tmp_path):
    from hashlib import sha256
    from nasolve.cif_fitted_preparation import _freeze_native
    from nasolve.cif_runtime_evidence import expanded_runtime_evidence

    inputs = tmp_path/'inputs'
    inputs.mkdir()
    receipt = inputs/'native_receipt.json'
    receipt.write_bytes(b'receipt')
    unrelated = inputs/'unrelated.log'
    unrelated.write_bytes(b'private note')
    selected = inputs/'relative'/'selected.phil'
    files = {receipt:b'receipt', selected:b'geometry_restraints test'}
    archive = tmp_path/'published'/'checked.zip'
    _freeze_native(receipt, files, archive)
    digest = sha256(archive.read_bytes()).hexdigest()
    with expanded_runtime_evidence(archive, digest) as view:
        root = view/'evidence'
        assert (root/'relative/selected.phil').read_bytes() == files[selected]
        assert (root/'native_receipt.json').read_bytes() == files[receipt]
        assert not (root/'unrelated.log').exists()
    with pytest.raises(FileExistsError):
        _freeze_native(receipt, {receipt:b'different'}, archive)
    assert sha256(archive.read_bytes()).hexdigest() == digest
