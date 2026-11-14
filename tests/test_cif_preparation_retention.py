"""Storage follows new publication; storage trouble cannot invent a second result."""
import json
import pytest
from nasolve.campaign_process import CampaignProcessError
from nasolve.campaign_records import read_record
from nasolve.postmr import prepare_postmr, PostMRPreparationError
from tests.test_postmr_runtime import checked_case


def ready_case(tmp_path, monkeypatch):
    run, ready, sdk, exact, calls, reads = checked_case(tmp_path, monkeypatch, 'readyset_checked_model')
    return run, ready, sdk, exact, calls, reads


def test_new_checked_result_is_published_before_retirement_and_keeps_exact_choice(tmp_path, monkeypatch):
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    invoked = []
    def retire(root, number):
        assert root == run/'PostMR/DictionaryEngine/request' and number == 1
        assert read_record(run/'PostMR/report.json')['checked_preparation']['attempt_number'] == number
        assert json.loads((run/'AutoRefine/checkpoints.json').read_text())['current'] == 'postmr'
        invoked.append(number)
        return 'Successful preparation working copies were archived; public models and restraints remain in place.'
    monkeypatch.setattr('nasolve.cif_ordinary_postmr._retire_new_preparation', retire, raising=False)
    result = prepare_postmr(run, ready, phenix_installation=sdk, checked_preparation=True)
    assert invoked == [1]
    assert result.model_path == exact['runtime']['model']
    assert list(result.restraint_paths) == exact['runtime']['phils'] + exact['runtime']['dictionaries']
    assert any('working copies were archived' in note for note in result.preparation_notes)
    assert len(calls) == 2 and reads == [1]


@pytest.mark.parametrize('failure', [OSError('disk unavailable'), ValueError('failed native work'), CampaignProcessError('request busy')])
def test_optional_storage_error_keeps_published_preparation_without_native_retry(tmp_path, monkeypatch, failure):
    from nasolve import cif_attempt_retention as storage
    from nasolve.campaign_records import write_record
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    request = run/'PostMR/DictionaryEngine/request/request.json'
    value = read_record(request); value['configuration']['artifact_policy'] = storage.ARTIFACT_POLICY
    write_record(request, value, replace=True)
    def retire(*args): raise failure
    monkeypatch.setattr(storage, 'retire_attempt_working_files', retire)
    result = prepare_postmr(run, ready, phenix_installation=sdk, checked_preparation=True)
    assert result.status == 'POSTMR_READY' and result.model_path == exact['runtime']['model']
    assert any('Optional working-file cleanup did not complete' in n and str(failure) in n for n in result.preparation_notes)
    assert len(calls) == 2 and reads == [1, 1]
    assert (run/'PostMR/report.json').is_file()


def test_failed_publication_never_starts_storage(tmp_path, monkeypatch):
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    def fail(*a, **k): raise ValueError('publication not qualified')
    monkeypatch.setattr('nasolve.cif_postmr_publication.publish_checked_preparation_with_notes', fail)
    monkeypatch.setattr('nasolve.cif_ordinary_postmr._retire_new_preparation', lambda *a: pytest.fail('No storage before publication'), raising=False)
    with pytest.raises(PostMRPreparationError, match='publication not qualified'):
        prepare_postmr(run, ready, phenix_installation=sdk, checked_preparation=True)
    assert not (run/'PostMR/report.json').exists()


def test_repeat_publication_and_inspection_do_not_trigger_retirement(tmp_path, monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from nasolve.cif_ordinary_postmr import read_ordinary_postmr_result
    from tests.test_cif_postmr_publication import snapshot
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    publish_checked_preparation(run, attempt_number=1); before = snapshot(run)
    monkeypatch.setattr('nasolve.cif_ordinary_postmr._retire_new_preparation', lambda *a: pytest.fail('No storage on read or historical publication'), raising=False)
    publish_checked_preparation(run, attempt_number=1)
    read_ordinary_postmr_result(run, attempt_number=1)
    assert snapshot(run) == before


def test_interrupt_is_not_swallowed_after_publication(tmp_path, monkeypatch):
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    def stop(*args): raise KeyboardInterrupt()
    monkeypatch.setattr('nasolve.cif_ordinary_postmr._retire_new_preparation', stop, raising=False)
    with pytest.raises(KeyboardInterrupt):
        prepare_postmr(run, ready, phenix_installation=sdk, checked_preparation=True)
    assert (run/'PostMR/report.json').is_file() and exact['runtime']['model'].is_file()
    assert len(calls) == 2


def test_cleanup_error_cannot_hide_a_broken_exact_result(tmp_path, monkeypatch):
    from nasolve import cif_attempt_retention as storage
    from nasolve.campaign_records import write_record
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    request = run/'PostMR/DictionaryEngine/request/request.json'
    value = read_record(request); value['configuration']['artifact_policy'] = storage.ARTIFACT_POLICY
    write_record(request, value, replace=True)
    changed = []
    def read(*args):
        if changed: raise ValueError('changed scientific evidence')
        return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result', read)
    def retire(*args):
        changed.append(True)
        raise OSError('cleanup failed')
    monkeypatch.setattr(storage, 'retire_attempt_working_files', retire)
    with pytest.raises(PostMRPreparationError, match='changed scientific evidence'):
        prepare_postmr(run, ready, phenix_installation=sdk, checked_preparation=True)
    assert (run/'PostMR/report.json').is_file() and len(calls) == 2


from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
from tests.test_cif_attempt_retention import completed
from tests.test_cif_repair_attempt import inventory


@pytest.mark.parametrize('interrupted', [False, True])
def test_real_owner_cleanup_or_partial_cleanup_stays_readable_and_relocates(joined, monkeypatch, tmp_path, interrupted):
    from nasolve import cif_attempt_retention as storage
    from nasolve.cif_ordinary_postmr import _retire_new_preparation
    from nasolve.campaign_records import artifact, verify_artifact
    complete, root, attempt = completed(joined)
    before = complete.read_dictionary_request_result(root, 1)
    if interrupted:
        remove = storage._remove_duplicate; removed = []
        def stop(path, ref):
            if len(removed) == 3: raise OSError('simulated storage interruption')
            remove(path, ref); removed.append(path)
        monkeypatch.setattr(storage, '_remove_duplicate', stop)
    note = _retire_new_preparation(root, 1)
    assert ('did not complete' if interrupted else 'were archived') in note
    assert complete.read_dictionary_request_result(root, 1) == before
    assert (root/'retention/attempt-0001/retired.json').exists() is (not interrupted)
    # Campaigns freeze the remaining files after the ordinary caller returns.
    duplicates = storage.archived_working_paths(root, 1)
    assert attempt/'attempt.json' not in duplicates and before['runtime']['model'] not in duplicates
    refs = [artifact(root, p.relative_to(root).as_posix()) for p in sorted(root.rglob('*')) if p.is_file() and p not in duplicates]
    moved = tmp_path/'moved-request'; root.rename(moved)
    if interrupted:
        monkeypatch.setattr(storage, '_remove_duplicate', remove)
        storage.retire_attempt_working_files(moved, 1)
    frozen = inventory(moved)
    for ref in refs: verify_artifact(moved, ref)
    result = complete.read_dictionary_request_result(moved, 1)
    assert result['runtime']['model'].is_relative_to(moved) and result['runtime']['model'].is_file()
    assert inventory(moved) == frozen and not root.exists()


def test_campaign_records_archive_not_disposable_working_paths(tmp_path, monkeypatch):
    from nasolve.campaign_stages import execute_stage
    from nasolve.config import AppConfig
    from nasolve.coot_runtime import CootDiscoveryError
    from nasolve.presets import load_preset
    from unittest.mock import patch
    run, ready, sdk, exact, calls, reads = ready_case(tmp_path, monkeypatch)
    request = run/'PostMR/DictionaryEngine/request'
    duplicate = request/'attempts/attempt-0001/scratch.log'; duplicate.write_text('disposable')
    archive = request/'retention/attempt-0001/evidence.zip'; archive.parent.mkdir(parents=True)
    archive.write_bytes(b'transport fixture; separately qualified in owner tests')
    monkeypatch.setattr('nasolve.cif_ordinary_postmr._retire_new_preparation', lambda *a: 'storage note')
    def paths(root, number):
        assert root == request and number == 1 and (run/'PostMR/report.json').is_file()
        return frozenset({duplicate})
    monkeypatch.setattr('nasolve.cif_attempt_retention.archived_working_paths', paths)
    policy = load_preset().to_dict(); policy['schema_version'] = 2
    policy['postmr']['checked_preparation'] = True
    attempt = tmp_path/'NASolveCampaign/jobs/postmr'; attempt.mkdir(parents=True)
    with patch('nasolve.campaign_stages.load_config', return_value=AppConfig()), \
            patch('nasolve.campaign_stages.discover_phenix', return_value=sdk), \
            patch('nasolve.campaign_stages.discover_coot', side_effect=CootDiscoveryError('unused')):
        result = execute_stage(tmp_path, {'id':'dataset','relative_path':'dataset'}, policy, 'postmr', attempt, run)
    assert duplicate.relative_to(tmp_path).as_posix() not in result['artifacts']
    assert archive.relative_to(tmp_path).as_posix() in result['artifacts']
    assert exact['runtime']['model'].relative_to(tmp_path).as_posix() in result['artifacts']
    assert 'storage note' in result['preparation_notes'] and reads == [1]
