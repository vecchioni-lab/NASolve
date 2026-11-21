"""Ordinary entry transports explicit choices; graph/native science has separate controls."""
from copy import deepcopy
from unittest.mock import patch
import shutil

import pytest

from tests.test_cif_complete_request import case
from tests.test_cif_postmr_request import entry_case, frozen_entry
from tests.test_cif_repair_attempt import inventory
from tests.test_postmr_runtime import setup, checked_case


@pytest.mark.parametrize('selected', [None, {'YYY': [['Y', 'R']]}])
def test_fresh_and_frozen_entry_share_choices_policy_and_cold_read(frozen_entry, case, monkeypatch, selected):
    from nasolve import cif_postmr_request as entry
    from nasolve import cif_prepared_repair_execution as repair
    from nasolve.cif_complete_request import ARTIFACT_POLICY, CAPTURE_ARTIFACT_POLICY
    m, args, sdk, store, generations, calls = frozen_entry
    # Transport fixture only: actual source-graph eligibility remains C326's test.
    monkeypatch.setattr(repair, 'linear_bond_query', lambda *a: {'selected_bonds': [['R', 'Y']]})
    fresh = deepcopy(args)
    fresh.pop('frozen_sources')
    fresh.update(source_output=case[2].parent/'fresh-sources', output=case[2].parent/'fresh-request',
        data_root=case[2].parent/'data', ready_set_executable=sdk.executables['phenix.ready_set'])
    with patch('subprocess.Popen', side_effect=AssertionError('No native intake')):
        frozen_record = entry.initialize_postmr_dictionary_request(**args, bond_targets=selected)
        fresh_record = entry.initialize_postmr_dictionary_request(**fresh, bond_targets=selected)
    config = frozen_record['configuration']
    assert fresh_record['configuration'] == config
    assert config['artifact_policy'] == (ARTIFACT_POLICY if selected is None else CAPTURE_ARTIFACT_POLICY)
    if selected is None:
        assert 'bond_targets' not in config
    else:
        assert config['bond_targets']['choices'] == {'YYY': [['R', 'Y']]}
        selected['YYY'][0][:] = ['X', 'Y']
        assert config['bond_targets']['choices'] == {'YYY': [['R', 'Y']]}
    before = inventory(args['output'])
    moved = args['output'].rename(args['output'].with_name('moved'))
    shutil.rmtree(args['frozen_sources'])
    shutil.rmtree(fresh['source_output'])
    shutil.rmtree(fresh['data_root'])
    with patch('subprocess.Popen', side_effect=AssertionError('No cold execution')):
        assert m.inspect_dictionary_request(moved)['attempts'] == []
    assert inventory(moved) == before and not calls and not store.exists()


BAD = [{}, [], True, {'YYY': []}, {'YYY': [['R', 'Y'], ['Y', 'R']]},
       {'YYY': [['R', 'R']]}, {'YYY': [['R']]}, {'../YYY': [['R', 'Y']]}]


@pytest.mark.parametrize('bad', BAD + [{'absent': [['R', 'Y']]}])
def test_bad_entry_choices_refuse_before_source_freezing(entry_case, bad):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = entry_case
    with patch('nasolve.cif_postmr_request.freeze_acquisition_sources', side_effect=AssertionError('No source writes')):
        with pytest.raises(ValueError):
            initialize_postmr_dictionary_request(**args, bond_targets=bad)
    assert not args['source_output'].exists() and not args['output'].exists() and not calls


def test_entry_still_requires_source_graph_eligibility(entry_case, monkeypatch):
    from nasolve import cif_prepared_repair_execution as repair
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, *_ = entry_case
    monkeypatch.setattr(repair, 'linear_bond_query', lambda *a: {'selected_bonds': []})
    with pytest.raises(ValueError, match='source linear neighborhood'):
        initialize_postmr_dictionary_request(**args, bond_targets={'YYY': [['R', 'Y']]})
    assert (args['source_output']/'source_selection.json').is_file()
    assert not (args['output']/'request.json').exists()


@pytest.mark.parametrize('bad', BAD)
def test_bad_ordinary_choices_refuse_before_tool_setup(tmp_path, bad):
    from nasolve.cif_ordinary_postmr import initialize_ordinary_postmr_request
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine', side_effect=AssertionError('No tool setup')):
        with pytest.raises(ValueError):
            initialize_ordinary_postmr_request(tmp_path/'run', None,
                expected_dialect='CHEMICAL_COMPONENTS_CIF', bond_targets=bad)
    assert not (tmp_path/'run').exists()


@pytest.mark.parametrize('selected', [None, {'DA': [['Y', 'R']]}])
def test_public_checked_entry_forwards_choices_once(tmp_path, monkeypatch, selected):
    from nasolve.postmr import prepare_postmr
    run, ready, sdk, exact, calls, reads = checked_case(tmp_path, monkeypatch)
    result = prepare_postmr(run, ready, phenix_installation=sdk,
        checked_preparation=True, bond_targets=selected)
    options = calls[0][1]
    if selected is None:
        assert 'bond_targets' not in options
    else:
        assert options['bond_targets'] == {'DA': [['R', 'Y']]}
        selected['DA'][0][:] = ['X', 'Y']
        assert options['bond_targets'] == {'DA': [['R', 'Y']]}
    assert [name for name, _ in calls] == ['construct', 'execute']
    assert reads == [1] and result.model_path == exact['runtime']['model']


@pytest.mark.parametrize('bad,checked', [(v, True) for v in BAD] + [({'DA': [['R', 'Y']]}, False)])
def test_public_bad_choices_refuse_before_preparation(tmp_path, bad, checked):
    from nasolve.postmr import prepare_postmr, PostMRPreparationError
    run, ready, sdk, data = setup(tmp_path)
    before = inventory(run)
    with patch('nasolve.postmr._selected_postmr_environment', side_effect=AssertionError('No tool setup')):
        with pytest.raises(PostMRPreparationError):
            prepare_postmr(run, ready, phenix_installation=sdk,
                checked_preparation=checked, bond_targets=bad)
    assert inventory(run) == before
