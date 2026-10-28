"""AutoSol phase references must carry an actual, complete HL quartet."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.autosol import AutoSolPreparationError, _discover_refinement_data
from nasolve.checkpoints import _phase_reference
from nasolve.model_assessment import file_sha256


OBSERVATIONS = 'I(+) 1 K\nSIGI(+) 1 M\nI(-) 1 K\nSIGI(-) 1 M\n'


def discover(tmp_path, phase_labels, observations=OBSERVATIONS):
    path = tmp_path / 'overall_best_refine_data.mtz'
    path.write_bytes(b'phase fixture')
    dump = observations + ''.join(f'{label} 1 A\n' for label in phase_labels)
    with patch('nasolve.autosol._run_mtz_dump', return_value=dump):
        return _discover_refinement_data(tmp_path, Path('unused-native-dump'), None)


@pytest.mark.parametrize('labels', [
    ['HLAM', 'HLBM', 'HLCM', 'HLDM'],
    ['HLA', 'HLB', 'HLC', 'HLD'],
    ['HL_A', 'HL_B', 'HL_C', 'HL_D'],
])
def test_phase_reference_contains_exact_hl_labels_not_observations(tmp_path, labels):
    path, found = discover(tmp_path, labels)
    assert found == labels
    reference = _phase_reference({'autosol': {
        'use_for_refinement': True,
        'outputs': {
            'refinement_data': str(path),
            'refinement_data_sha256': file_sha256(path),
            'refinement_data_phase_labels': found,
        },
    }}, tmp_path)
    assert reference['labels'] == labels


def test_phase_preference_agrees_with_existing_autorefine_policy(tmp_path):
    combined = ['HLAM', 'HLBM', 'HLCM', 'HLDM']
    _, found = discover(tmp_path, ['HLA', 'HLB', 'HLC', 'HLD'] + combined +
                        ['HLanomA', 'HLanomB', 'HLanomC', 'HLanomD'])
    assert found == combined


@pytest.mark.parametrize('labels', [
    ['HLA', 'HLBM', 'HLC', 'HLDM'],
    ['HL_A', 'HLB', 'HL_C', 'HLD'],
    ['HLAM', 'HLBM', 'HLCM'],
    ['XHLAM', 'XHLBM', 'XHLCM', 'XHLDM'],
    ['HLanomA', 'HLanomB', 'HLanomC', 'HLanomD'],
])
def test_incomplete_mixed_or_unqualified_phase_families_are_not_invented(tmp_path, labels):
    with pytest.raises(AutoSolPreparationError, match='both Hendrickson-Lattman'):
        discover(tmp_path, labels)


def test_phase_data_still_requires_anomalous_observations(tmp_path):
    with pytest.raises(AutoSolPreparationError, match='both Hendrickson-Lattman'):
        discover(tmp_path, ['HLAM', 'HLBM', 'HLCM', 'HLDM'], observations='F 1 F\nSIGF 1 Q\n')
