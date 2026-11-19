"""Exact native-array choice without map generation or policy inference."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from nasolve.map_coefficients import describe_complex_array, select_complex_array


def array(labels, complex_array=True):
    result = Mock()
    result.info.return_value = SimpleNamespace(labels=list(labels))
    result.is_complex_array.return_value = complex_array
    result.fft_map.side_effect = AssertionError('Selection must not calculate density')
    return result


def test_exact_ordered_labels_select_the_original_array_without_reading_values():
    wanted = array(['FWT', 'PHWT'])
    unrelated = array(['DELFWT', 'PHDELWT'])
    real = array(['FWT', 'PHWT'], False)
    assert select_complex_array([unrelated, real, wanted], ['FWT', 'PHWT']) is wanted
    wanted.fft_map.assert_not_called()
    wanted.data.assert_not_called()
    assert wanted.info().labels == ['FWT', 'PHWT']


@pytest.mark.parametrize('labels', [['PHWT', 'FWT'], ['FWT'], ['FWT', 'PHWT', 'W'], ['fwt', 'PHWT']])
def test_partial_reordered_or_case_changed_labels_do_not_silently_select(labels):
    with pytest.raises(ValueError, match='Exact complex map labels not found'):
        select_complex_array([array(['FWT', 'PHWT'])], labels)


@pytest.mark.parametrize('arrays', [[], [array(['FWT', 'PHWT'], False)], [array(['FWT', 'PHWT']), array(['FWT', 'PHWT'])]])
def test_absent_real_only_or_ambiguous_matches_preserve_the_existing_refusal(arrays):
    with pytest.raises(ValueError, match='Exact complex map labels not found'):
        select_complex_array(arrays, ['FWT', 'PHWT'])


def test_real_array_is_not_described_as_complex_map_coefficients():
    with pytest.raises(ValueError, match='requires a complex array'):
        describe_complex_array(array(['F', 'SIGF'], False))
