"""Scientist-facing preparation commands must not imply refinement success."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from nasolve.cli import main


def outcome(tmp_path,usable=True):
    return SimpleNamespace(message='The checked starting model was retained.',
        model_path=tmp_path/'model.pdb' if usable else None, dictionary_paths=(tmp_path/'component.cif',) if usable else (),
        restraint_paths=(tmp_path/'pairs.phil',) if usable else (), readyset_status='FAILED',
        report_path=tmp_path/'attempt-0002/result.json',attempt_number=2,run_directory=tmp_path,
        limitations=('Diffraction refinement has not been performed.',))


@pytest.mark.parametrize('usable',[True,False])
def test_read_result_is_exact_read_only_and_does_not_claim_readyset_success(tmp_path,capsys,usable):
    with patch('nasolve.cif_ordinary_postmr.read_ordinary_postmr_result',return_value=outcome(tmp_path,usable)) as read, \
         patch('nasolve.cli.load_config',side_effect=AssertionError('Read needs no configuration')), \
         patch('nasolve.cli.discover_phenix',side_effect=AssertionError('Read needs no Phenix')):
        assert main(['cif-doctor','prepared-result',str(tmp_path),'--attempt','2'])==(0 if usable else 2)
    read.assert_called_once_with(tmp_path,attempt_number=2)
    text=capsys.readouterr().out
    assert 'ReadySet: FAILED' in text and 'refinement has not' in text
    assert 'ReadySet log:' not in text and 'attempt-0002/result.json' in text
    assert ('--preparation-attempt 2' in text) is usable


def test_continue_has_no_coot_or_constructor_and_binds_previous_attempt(tmp_path,capsys):
    with patch('nasolve.cli.load_config',return_value=object()),patch('nasolve.cli.discover_phenix',return_value='selected') as sdk, \
         patch('nasolve.cli.discover_coot',side_effect=AssertionError('No repeated construction')), \
         patch('nasolve.cif_ordinary_postmr.continue_checked_postmr',return_value=outcome(tmp_path)) as resume:
        assert main(['cif-doctor','continue-preparation',str(tmp_path),'--after-attempt','1','--store',str(tmp_path/'store')])==0
    resume.assert_called_once_with(tmp_path,'selected',after_attempt=1,store_root=tmp_path/'store')
    sdk.assert_called_once()


def test_fresh_preparation_carries_scientific_permissions_and_selected_tools(tmp_path,capsys):
    with patch('nasolve.cli.load_config',return_value=object()),patch('nasolve.cli.discover_phenix',return_value='selected'), \
         patch('nasolve.cli.discover_coot',return_value=SimpleNamespace(executable=Path('/selected/coot'))), \
         patch('nasolve.cif_ordinary_postmr.prepare_checked_postmr',return_value=outcome(tmp_path)) as prepare:
        assert main(['cif-doctor','prepare-run',str(tmp_path),'--allow-mr-review','--restraint-scope','all'])==0
    prepare.assert_called_once_with(tmp_path,'selected',store_root=None,coot_executable=Path('/selected/coot'),
        allow_mr_review=True,restraint_scope='all',modified_pairs_only=False,allow_unreviewed_backbone=False)


def test_failed_evidence_is_error_without_fallback_output(tmp_path,capsys):
    with patch('nasolve.cif_ordinary_postmr.read_ordinary_postmr_result',side_effect=ValueError('changed saved evidence')):
        assert main(['cif-doctor','prepared-result',str(tmp_path),'--attempt','1'])==2
    text=capsys.readouterr();assert 'changed saved evidence' in text.err and 'Checked model:' not in text.out


def test_preparation_status_reads_owner_without_sdk_or_selecting_latest(tmp_path,capsys):
    state=dict(state='RECORDED',availability='BLOCKED',attempts=[dict(number=1,state='UNKNOWN')])
    with patch('nasolve.cif_complete_request.inspect_dictionary_request',return_value=state) as read, \
         patch('nasolve.cli.load_config',side_effect=AssertionError('Read needs no configuration')):
        assert main(['cif-doctor','preparation-status',str(tmp_path)])==0
    read.assert_called_once_with(tmp_path/'PostMR/DictionaryEngine/request')
    text=capsys.readouterr().out;assert 'BLOCKED' in text and 'UNKNOWN' in text and 'Checked model:' not in text


def test_inspection_hint_quotes_run_path_without_replaying_science(tmp_path, capsys):
    import shlex
    result = outcome(tmp_path / "run with 'quote'")
    with patch('nasolve.cif_ordinary_postmr.read_ordinary_postmr_result', return_value=result) as read, \
         patch('nasolve.cli.resolve_view_profile', side_effect=AssertionError('No second full evidence replay')):
        assert main(['cif-doctor', 'prepared-result', str(result.run_directory), '--attempt', '2']) == 0
    read.assert_called_once()
    text = capsys.readouterr().out
    line = next(line for line in text.splitlines() if line.startswith('Inspect this preparation'))
    assert shlex.split(line.split(': ', 1)[1]) == ['nasolve', 'show', str(result.run_directory), '--preparation-attempt', '2']
