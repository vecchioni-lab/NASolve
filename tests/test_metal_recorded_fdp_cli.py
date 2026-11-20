"""The normal CLI exposes pinned historical results without opening a run."""
import json
import shutil
from unittest.mock import patch
import pytest
from nasolve.cli import main, build_parser
from tests.test_metal_recorded_fdp import packed


def selection(tmp_path, monkeypatch):
    archive, receipt, args, projection, run = packed(tmp_path, monkeypatch)
    parent = tmp_path / 'expected-parent.json'
    parent.write_text(json.dumps(args['expected_parent']))
    command = ['metal', 'inspect-recorded-fdp', '--archive', str(archive),
               '--archive-sha256', receipt['archive_sha256'],
               '--projection-id', args['projection_id'], '--trial-id', args['trial_id'],
               '--expected-parent', str(parent)]
    return command, parent, projection, run


@pytest.mark.parametrize('mode', ['json', 'text'])
def test_normal_cli_reads_after_original_run_is_removed(tmp_path, monkeypatch, capsys, mode):
    command, parent, projection, run = selection(tmp_path, monkeypatch)
    shutil.rmtree(run)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with patch('nasolve.metal.cli.discover_phenix', side_effect=AssertionError('No native discovery')), \
         patch('nasolve.metal.cli.load_run_context', side_effect=AssertionError('No source run')), \
         patch('subprocess.Popen', side_effect=AssertionError('No process')):
        assert main(command + (['--json'] if mode == 'json' else [])) == 0
    output = capsys.readouterr()
    assert not output.err
    if mode == 'json':
        result = json.loads(output.out)
        assert result['record'] == projection['records'][0]
        assert result['native_evidence_replayed'] is False
        assert result['retirement_authorized'] is False
    else:
        assert 'Q (occ)' in output.out and 'Expected f″' in output.out
        assert 'Historical result' in output.out and 'No new scientific audit' in output.out
        assert projection['records'][0]['trial_id'] in output.out
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('change', ['archive', 'projection', 'trial', 'parent', 'budget', 'duplicate-parent', 'oversized-parent'])
def test_cli_refuses_wrong_pins_and_parent_json_without_writes(tmp_path, monkeypatch, capsys, change):
    command, parent, projection, run = selection(tmp_path, monkeypatch)
    if change in {'archive', 'projection', 'trial'}:
        flag = {'archive': '--archive-sha256', 'projection': '--projection-id', 'trial': '--trial-id'}[change]
        command[command.index(flag) + 1] = '0' * 64
    elif change == 'parent':
        value = json.loads(parent.read_text()); value['geometry_id'] = '0' * 64
        parent.write_text(json.dumps(value))
    elif change == 'budget':
        command += ['--max-input-bytes', '1']
    elif change == 'duplicate-parent':
        parent.write_text('{"geometry_id":"first","geometry_id":"second"}')
    else:
        parent.write_text(' ' * (16 * 1024 + 1))
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert main(command + ['--json']) == 2
    output = capsys.readouterr()
    assert not output.out and 'Metal integration error' in output.err
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before


def test_cli_requires_independent_selection_and_has_no_output_or_run_argument():
    parser = build_parser()
    with pytest.raises(SystemExit) as stop:
        parser.parse_args(['metal', 'inspect-recorded-fdp'])
    assert stop.value.code == 2
    base = ['metal', 'inspect-recorded-fdp', '--archive', 'inputs.zip',
            '--archive-sha256', '1'*64, '--projection-id', '2'*64,
            '--trial-id', '3'*64, '--expected-parent', 'parent.json']
    for extra in (['--output', 'result.json'], ['some-run']):
        with pytest.raises(SystemExit) as stop:
            parser.parse_args(base + extra)
        assert stop.value.code == 2
