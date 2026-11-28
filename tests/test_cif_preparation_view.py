"""Inspect a named checked preparation, including an independently safe fallback."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nasolve.campaigns import CampaignError
from nasolve.coot_view import CootViewError, launch_coot_view, resolve_view_profile
from nasolve.model_assessment import file_sha256
from nasolve.run_context import artifact_reference
from tests.test_cif_ordinary_outcome import selected_result
from tests.test_coot_view import make_view_run


def preparation(tmp_path, monkeypatch, choice='verified_parent_runtime'):
    run = make_view_run(tmp_path)
    # Keep a newer refinement selected, but inspect the exact preparation below.
    exact = selected_result(tmp_path / 'evidence', choice)
    target = run / 'PostMR/DictionaryEngine/request/attempts/attempt-0001'
    target.mkdir(parents=True)
    runtime = exact['runtime']
    for name in ('model', 'manifest_path'):
        runtime[name] = target / runtime[name].name
    for name in ('dictionaries', 'phils'):
        runtime[name] = [target / path.name for path in runtime[name]]
    runtime['dictionaries'].append(runtime['dictionaries'][0])
    for path in [runtime['model'], *runtime['dictionaries'], *runtime['phils']]:
        path.write_text('data_component\n' if path.suffix == '.cif' else 'test input\n')
    calls = []
    def read(root, attempt):
        calls.append((root, attempt))
        return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result', read)
    return run, exact, calls


def snapshot(run):
    return {p.relative_to(run).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in run.rglob('*') if p.is_file()}


@pytest.mark.parametrize('choice', ['readyset_checked_model', 'readyset_ordered_checked_model',
                                   'verified_parent_runtime', 'verified_prepared_bundle', 'repaired_prepared_bundle'])
def test_exact_preparation_view_uses_checked_inputs_and_never_selects_latest(tmp_path, monkeypatch, choice):
    run, exact, calls = preparation(tmp_path, monkeypatch, choice)
    before = snapshot(run)
    with patch('subprocess.Popen', side_effect=AssertionError('Read must not launch tools')):
        view = resolve_view_profile(run, preparation_attempt=1)
    assert calls == [(run / 'PostMR/DictionaryEngine/request', 1)]
    assert view.model_path == exact['runtime']['model']
    assert view.dictionary_paths == tuple(exact['runtime']['dictionaries'])
    assert view.preparation_attempt == 1 and view.checkpoint_id is None
    assert view.stage == 'preparation' and 'attempt 1' in view.source
    assert 'not recalculated' in view.map_source and 'Phaser' in view.map_source
    assert view.map_path == run / 'Phaser/mr_solution.mtz'
    if choice == 'verified_parent_runtime':
        assert 'retained' in view.source and 'FAILED' in view.source
    assert snapshot(run) == before


@pytest.mark.parametrize('attempt', [0, -1, True, '1', 1.5])
def test_attempt_must_be_exact_positive_integer_before_read(tmp_path, attempt):
    with patch('nasolve.cif_ordinary_postmr.read_ordinary_postmr_result', side_effect=AssertionError('no read')):
        with pytest.raises(CootViewError, match='positive'):
            resolve_view_profile(tmp_path, preparation_attempt=attempt)


@pytest.mark.parametrize('other', [{'checkpoint': 'postmr'}, {'stage': 'postmr'}, {'stage': 'autorefine'}])
def test_preparation_cannot_be_combined_with_other_selections(tmp_path, other):
    with pytest.raises(CootViewError, match='cannot be combined'):
        resolve_view_profile(tmp_path, preparation_attempt=1, **other)


@pytest.mark.parametrize("error", [ValueError, OSError, CampaignError])
def test_failed_evidence_cannot_fall_through_to_current_checkpoint(tmp_path, monkeypatch, error):
    run, _, _ = preparation(tmp_path, monkeypatch)
    before = snapshot(run)
    with patch('nasolve.cif_complete_request.read_dictionary_request_result', side_effect=error('changed pair restraints')):
        with pytest.raises(CootViewError, match='changed pair restraints'):
            launch_coot_view(run, Path('/unused/coot'), preparation_attempt=1,
                             launcher=lambda *a, **k: pytest.fail('no launch'))
    assert snapshot(run) == before


def test_unqualified_attempt_keeps_report_available_without_launch(tmp_path, monkeypatch):
    run, exact, _ = preparation(tmp_path, monkeypatch)
    exact['runtime'] = None
    exact['result']['status'] = 'NO_USABLE_BUNDLE'
    before = snapshot(run)
    with pytest.raises(CootViewError, match='prepared-result'):
        launch_coot_view(run, Path('/unused/coot'), preparation_attempt=1,
                         launcher=lambda *a, **k: pytest.fail('no launch'))
    assert snapshot(run) == before


def test_launch_isolates_preparation_attempt_and_preserves_order(tmp_path, monkeypatch):
    run, exact, _ = preparation(tmp_path, monkeypatch)
    before = snapshot(run)
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=12345)
    result = launch_coot_view(run, Path('/unused/coot'), preparation_attempt=1, launcher=launch)
    assert result.working_directory == run / 'CootGUI/preparation/attempt-0001'
    assert result.preparation_attempt == 1
    command = calls[0][0]
    dictionaries = [command[n + 1] for n, value in enumerate(command) if value == '--dictionary']
    assert dictionaries == [str(p) for p in exact['runtime']['dictionaries']]
    receipt = json.loads((result.working_directory / 'launch.json').read_text())
    assert receipt['preparation_attempt'] == 1 and receipt['checkpoint_id'] is None
    assert 'retained' in receipt['source'] and 'FAILED' in receipt['source']
    after = snapshot(run)
    assert {name: after[name] for name in before} == before
    assert all(name.startswith('CootGUI/') for name in set(after) - set(before))


def test_changed_declared_map_is_not_replaced_by_another_map(tmp_path, monkeypatch):
    run, _, _ = preparation(tmp_path, monkeypatch)
    path = run / 'report.json'; report = json.loads(path.read_text())
    mtz = run / 'Phaser/mr_solution.mtz'
    report['execution']['phaser']['solution_mtz'] = dict(artifact_reference(mtz, run), sha256=file_sha256(mtz))
    path.write_text(json.dumps(report)); mtz.write_bytes(b'changed map')
    with pytest.raises(CootViewError, match='Phaser'):
        resolve_view_profile(run, preparation_attempt=1)


def test_cli_names_exact_attempt_and_successful_fallback(tmp_path, monkeypatch, capsys):
    from functools import partial
    from nasolve.cli import main
    from nasolve.config import AppConfig
    run, _, _ = preparation(tmp_path, monkeypatch)
    with patch('nasolve.cli.load_config', return_value=AppConfig()), patch('nasolve.cli.save_config'), \
         patch('nasolve.cli.discover_coot', return_value=SimpleNamespace(executable=Path('/unused/coot'))), \
         patch('nasolve.cli.remember_coot'), \
         patch('nasolve.cli.launch_coot_view', side_effect=partial(launch_coot_view, launcher=lambda *a, **k: SimpleNamespace(pid=12345))):
        assert main(['show', str(run), '--preparation-attempt', '1']) == 0
    text = capsys.readouterr().out
    assert 'attempt 1' in text and 'retained' in text and 'FAILED' in text
    assert 'not recalculated' in text


def test_modification_only_dictionary_is_checked_but_not_sent_to_coot(tmp_path, monkeypatch):
    from nasolve.ligand_profiles import MOD_CIF
    run, exact, calls = preparation(tmp_path, monkeypatch)
    modification = exact['runtime']['model'].parent / 'linked-phosphate.cif'
    modification.write_text(MOD_CIF)
    expected = tuple(exact['runtime']['dictionaries'])
    exact['runtime']['dictionaries'].insert(1, modification)
    view = resolve_view_profile(run, preparation_attempt=1)
    assert view.dictionary_paths == expected and len(calls) == 1


def test_missing_mr_map_does_not_erase_preparation_or_use_latest_refinement(tmp_path, monkeypatch):
    run, _, _ = preparation(tmp_path, monkeypatch)
    (run / 'Phaser/mr_solution.mtz').unlink()
    before = snapshot(run)
    with pytest.raises(CootViewError, match='Phaser'):
        resolve_view_profile(run, preparation_attempt=1)
    assert snapshot(run) == before
