"""Completed batch publication issues independently retained selection identities."""
import json
import shutil
from unittest.mock import patch
import pytest
from tests.test_metal_compact import trials
from nasolve.metal.recipe import RecipeError


def test_completed_two_trial_producer_to_pinned_reader_without_extra_parent_replay(tmp_path, monkeypatch):
    from nasolve.metal import publication as module, fdp, context
    from nasolve.metal.input_archive import pack_fdp_inputs
    run, selected = trials(tmp_path, monkeypatch, (.6, .7))
    expected = [json.loads((run / p / 'result.json').read_text()) for p in selected]
    before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    original = fdp._input_bundle
    with patch.object(context, 'read_registry', side_effect=AssertionError('No whole registry walk')), \
         patch.object(fdp, '_input_bundle', wraps=original) as replay:
        pack_fdp_inputs(run, selected, tmp_path / 'baseline.zip')
        baseline_calls = replay.call_count; replay.reset_mock()
        receipt = module.publish_fdp_inputs(run, selected, tmp_path / 'review.zip', tmp_path / 'publication.json')
        assert replay.call_count == baseline_calls
    assert {p: p.read_bytes() for p in run.rglob('*') if p.is_file()} == before
    assert len(receipt['attempts']) == 2 and len(receipt['parents']) == 1
    assert json.loads((tmp_path / 'publication.json').read_text()) == receipt
    assert str(tmp_path) not in json.dumps(receipt)
    shutil.rmtree(run)
    with patch.object(fdp, '_input_bundle', side_effect=AssertionError('No source lookup')):
        for attempt, result in zip(receipt['attempts'], expected):
            actual = module.inspect_published_fdp(tmp_path / 'review.zip', receipt,
                publication_id=receipt['record_sha256'], trial_id=attempt['trial_id'])
            assert actual['record']['result'] == result
            assert not actual['native_evidence_replayed'] and not actual['retirement_authorized']
        with pytest.raises(RecipeError):
            module.inspect_published_fdp(tmp_path / 'review.zip', receipt,
                publication_id='0'*64, trial_id=receipt['attempts'][0]['trial_id'])


@pytest.mark.parametrize('stage', ['failed-trial', 'archive', 'receipt'])
def test_interrupted_publication_issues_no_selectable_receipt(tmp_path, monkeypatch, stage):
    from nasolve.metal import publication as module
    run, selected = trials(tmp_path, monkeypatch, (.6, .7))
    archive = tmp_path / 'review.zip'; receipt = tmp_path / 'publication.json'
    if stage == 'failed-trial':
        (run / selected[-1] / 'failure.json').write_text('{"status":"FAILED"}')
    elif stage == 'archive':
        def interrupted(*args, **kwargs):
            archive.write_bytes(b'interrupted archive')
            raise OSError('Interrupted packing')
        monkeypatch.setattr(module, 'pack_fdp_inputs', interrupted)
    else:
        def interrupted(*args, **kwargs):
            raise OSError('Interrupted before final receipt publication')
        monkeypatch.setattr(module.records.os, 'link', interrupted)
    before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with pytest.raises((ValueError, OSError)):
        module.publish_fdp_inputs(run, selected, archive, receipt)
    assert {p: p.read_bytes() for p in run.rglob('*') if p.is_file()} == before
    assert not receipt.exists()
    if stage == 'receipt':
        assert archive.is_file()
        assert not list(tmp_path.glob('.record-*'))
    if stage == 'archive': assert archive.read_bytes() == b'interrupted archive'


def test_existing_or_in_run_outputs_refuse_before_packing(tmp_path, monkeypatch):
    from nasolve.metal import publication as module
    run = tmp_path / 'run'; run.mkdir()
    archive = tmp_path / 'review.zip'; receipt = tmp_path / 'publication.json'
    monkeypatch.setattr(module, 'pack_fdp_inputs', lambda *a, **k: pytest.fail('Preflight must precede packing'))
    receipt.write_text('retain')
    with pytest.raises(ValueError):module.publish_fdp_inputs(run, [], archive, receipt)
    assert receipt.read_text() == 'retain' and not archive.exists()
    with pytest.raises(ValueError):module.publish_fdp_inputs(run, [], archive, run / 'receipt.json')
    with pytest.raises(ValueError):module.publish_fdp_inputs(run, [], archive, archive)


def test_normal_cli_publishes_and_reads_independently_pinned_receipt(tmp_path, monkeypatch, capsys):
    from nasolve.cli import main
    run, selected = trials(tmp_path, monkeypatch, (.6, .7))
    archive = tmp_path / 'review.zip'; receipt = tmp_path / 'publication.json'
    command = ['metal', 'publish-fdp-inputs', str(run), '--archive', str(archive), '--output', str(receipt), '--json']
    for p in selected: command += ['--trial', str(p)]
    assert main(command) == 0
    publication = json.loads(capsys.readouterr().out)
    shutil.rmtree(run)
    read = ['metal', 'inspect-recorded-fdp', '--archive', str(archive), '--publication', str(receipt),
            '--publication-id', publication['record_sha256'], '--trial-id', publication['attempts'][0]['trial_id'], '--json']
    assert main(read) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['record']['record_id'] == publication['attempts'][0]['record_id']
    assert main(read + ['--archive-sha256', '0'*64]) == 2
    assert not capsys.readouterr().out
