"""A completed batch is inspected in one bounded archive lifetime."""
from copy import deepcopy
from contextlib import contextmanager
from hashlib import sha256
import json
import shutil
from unittest.mock import patch
import pytest
from tests.test_metal_compact import trials
from nasolve.metal import publication
from nasolve.metal.recipe import RecipeError


def batch(tmp_path, monkeypatch):
    run, selected = trials(tmp_path, monkeypatch, (.6, .7, .6))
    archive = tmp_path / 'batch.zip'
    receipt_file = tmp_path / 'publication.json'
    receipt = publication.publish_fdp_inputs(run, selected, archive, receipt_file)
    expected = [publication.inspect_published_fdp(archive, receipt,
        publication_id=receipt['record_sha256'], trial_id=a['trial_id']) for a in receipt['attempts']]
    shutil.rmtree(run)
    return archive, receipt_file, receipt, expected


def test_complete_batch_uses_one_expansion_and_keeps_distinct_attempts(tmp_path, monkeypatch):
    archive, receipt_file, receipt, expected = batch(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    original = publication.expanded_fdp_inputs
    roots = []
    @contextmanager
    def tracked(*args, **kwargs):
        with original(*args, **kwargs) as view:
            roots.append(view[0])
            yield view
    with patch.object(publication, 'expanded_fdp_inputs', tracked), \
         patch('subprocess.Popen', side_effect=AssertionError('No native process')):
        actual = publication.inspect_published_fdp_batch(archive, receipt,
            publication_id=receipt['record_sha256'])
    assert actual == expected
    assert len(roots) == 1 and not roots[0].exists()
    assert len({x['record']['trial_id'] for x in actual}) == 3
    assert actual[0]['record']['input_id'] == actual[2]['record']['input_id']
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('mode', ['json', 'text'])
def test_normal_cli_all_published_trials(tmp_path, monkeypatch, capsys, mode):
    from nasolve.cli import main
    archive, receipt_file, receipt, expected = batch(tmp_path, monkeypatch)
    args = ['metal','inspect-recorded-fdp','--archive',str(archive),
            '--publication',str(receipt_file),'--publication-id',receipt['record_sha256'],'--all-trials']
    assert main(args + (['--json'] if mode == 'json' else [])) == 0
    out = capsys.readouterr()
    assert not out.err
    if mode == 'json':assert json.loads(out.out) == expected
    else:
        assert '3 historical attempts' in out.out and 'Q (occ)' in out.out
        for report in expected: assert report['record']['trial_id'] in out.out


@pytest.mark.parametrize('change', ['wrong-pin','late-result','budget','no-receipt','duplicate-attempt'])
def test_all_batch_refuses_without_partial_output(tmp_path, monkeypatch, capsys, change):
    from nasolve.cli import main
    archive, receipt_file, receipt, _ = batch(tmp_path, monkeypatch)
    value = deepcopy(receipt)
    if change == 'late-result':value['attempts'][-1]['record_id'] = '0'*64
    if change == 'duplicate-attempt':value['attempts'].append(value['attempts'][0])
    if change in {'late-result','duplicate-attempt'}:
        value.pop('record_sha256')
        value['record_sha256'] = sha256(publication.records._canonical(value)).hexdigest()
        receipt_file.write_text(json.dumps(value))
    args = ['metal','inspect-recorded-fdp','--archive',str(archive),'--all-trials']
    if change != 'no-receipt':
        args += ['--publication',str(receipt_file),'--publication-id',
                 '0'*64 if change == 'wrong-pin' else value['record_sha256']]
    if change == 'budget': args += ['--max-input-bytes','1']
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert main(args) == 2
    out = capsys.readouterr()
    assert not out.out and 'Metal integration error' in out.err
    assert {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before
