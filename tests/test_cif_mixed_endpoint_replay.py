"""The portable reader keeps the original C93 recipe and all hard gates."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess

import pytest

from nasolve import cif_mixed_endpoint_window as original
from nasolve.cif_mixed_endpoint_replay import replay_saved_endpoint_window
from tests.test_cif_mixed_endpoint import (
    coherent_torsion_parent, _endpoint_parent_bytes, _rebind_endpoint_artifact, C92_PARENT_SHA256,
)


def replay(output, parents):
    return replay_saved_endpoint_window(output, torsion_directory=parents[0], geometry_directory=parents[1],
        gradient_directory=parents[2], context_directory=parents[3], linked_parent_directory=parents[4],
        parent_archive_sha256=C92_PARENT_SHA256)


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True))


def rebind(output, report, relative, value):
    path = output/relative
    write_json(path, value)
    _rebind_endpoint_artifact(report, relative, path.read_bytes(), original.ANCHOR)
    write_json(output/original.REPORT, report)


def shifted_geometry(value):
    value = deepcopy(value)
    for kind, rows in value['measurements'].items():
        for row in rows:
            if type(row['observed']) is float and row['observed'] > 0:
                row['observed'] = math.nextafter(row['observed'], math.inf)
                value['summary'][kind]['worst'] = [deepcopy(rows[r['proxy_index']]) for r in value['summary'][kind]['worst']]
                return value
    raise AssertionError('Fixture lacks measured geometry')


def measured_reports(monkeypatch):
    """Add a report-only synthetic bond to the plane/dihedral fake SDK.

    That existing SDK deliberately has no distance/angle/volume proxies. This
    scalar-report fixture computes a real distance from its actual sites; it
    does not change its native manager, evaluator or any acceptance decision.
    The unmodified real C93 report is separately exercised in cold validation.
    """
    from nasolve import cif_captured_geometry as captured, cif_fixed_geometry as fixed
    original_review = captured.review_captured_geometry
    def review(native):
        projected = deepcopy(native)
        row = {'i_seqs': [0, 1], 'atoms': [native['atoms'][i]['label'] for i in [0, 1]],
            'origin_id': 0, 'distance_ideal': 1., 'weight': 1., 'symmetry_operation': None}
        projected['geometry']['proxy_details']['bond_simple'] = [row]
        projected['geometry']['proxy_counts']['bond_simple'] = 1
        return original_review(projected)
    monkeypatch.setattr(captured, 'review_captured_geometry', review)
    monkeypatch.setattr(fixed, 'review_captured_geometry', review)


@pytest.mark.parametrize('coordinate_case', ['full_precision', 'pdb_rounded', 'both'])
def test_saved_roundoff_failure_is_replayed_without_changing_any_source_or_native_data(tmp_path, monkeypatch, coordinate_case):
    measured_reports(monkeypatch)
    *parents, _, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    output = tmp_path/'window'
    report = original.qualify_saved_mixed_endpoint(*parents, phenix, output,
        parent_archive_sha256=C92_PARENT_SHA256, timeout_seconds=30)
    assert report['status'] == 'MIXED_ENDPOINT_QUALIFIED'
    files = {'full_precision': 'full_precision_geometry.json', 'pdb_rounded': 'rounded_geometry.json'}
    for label, relative in files.items():
        if coordinate_case in {label, 'both'}:
            rebind(output, report, relative, shifted_geometry(json.loads((output/relative).read_bytes())))
    before = _endpoint_parent_bytes(*parents, output)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Saved replay launched a native process'))
    with pytest.raises(ValueError):
        original.read_saved_mixed_endpoint(output, torsion_directory=parents[0], geometry_directory=parents[1],
            gradient_directory=parents[2], context_directory=parents[3], linked_parent_directory=parents[4],
            parent_archive_sha256=C92_PARENT_SHA256)
    result = replay(output, parents)
    assert result['status'] == 'SAVED_ENDPOINT_REPLAY_PASS'
    assert result['coordinate_decision'] == report['coordinate_decision']
    assert result['coordinate_decision']['selected'] == 'qualified_geometry_endpoint'
    assert all(result['coordinate_decision']['checks'].values())
    assert result['new_native_calls'] == 0 and result['saved_native_calls'] == 2
    assert all(r['consistent'] for r in result['descriptive_geometry_replay'].values())
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize('defect', ['target', 'native_proxy', 'derivative', 'worker', 'approval'])
def test_rebinding_hashes_cannot_promote_corrupt_chemistry_derivatives_or_recipe(tmp_path, monkeypatch, defect):
    measured_reports(monkeypatch)
    *parents, _, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    output = tmp_path/'window'
    report = original.qualify_saved_mixed_endpoint(*parents, phenix, output,
        parent_archive_sha256=C92_PARENT_SHA256, timeout_seconds=30)
    if defect == 'target':
        relative = 'full_precision_geometry.json';value = json.loads((output/relative).read_bytes())
        row = next(r for rows in value['measurements'].values() for r in rows if type(r['target']) is float)
        row['target'] = math.nextafter(row['target'], math.inf)
        rebind(output, report, relative, value)
    elif defect == 'native_proxy':
        relative = 'native_mechanics.json';value = json.loads((output/relative).read_bytes())
        value['checks'][0]['status'] = 'REVIEW';rebind(output, report, relative, value)
    elif defect == 'derivative':
        relative = 'job/endpoint_result.json';value = json.loads((output/relative).read_bytes())
        value['audit']['observations'][0]['value']['target'] += 1.
        rebind(output, report, relative, value)
    elif defect == 'worker':
        path = output/'job/endpoint_core.py';path.write_bytes(path.read_bytes()+b'\n# CHANGED_RECIPE\n')
        _rebind_endpoint_artifact(report, 'job/endpoint_core.py', path.read_bytes(), original.ANCHOR)
        write_json(output/original.REPORT, report)
    else:
        report['requires_cif_review'] = True;write_json(output/original.REPORT, report)
    before = _endpoint_parent_bytes(*parents, output)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Corrupt saved evidence launched native process'))
    with pytest.raises(ValueError):
        replay(output, parents)
    assert all(path.read_bytes() == data for path, data in before.items())


def test_prepared_only_is_not_promoted_to_an_endpoint_or_a_new_native_job(tmp_path, monkeypatch):
    *parents, _, _ = coherent_torsion_parent(tmp_path, monkeypatch)
    output = tmp_path/'prepared'
    report = original.qualify_saved_mixed_endpoint(*parents, None, output, parent_archive_sha256=C92_PARENT_SHA256)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Prepared-only replay launched process'))
    result = replay(output, parents)
    assert result['original_status'] == 'PREPARED_ONLY'
    assert result['coordinate_decision'] == report['coordinate_decision']
    assert result['new_native_calls'] == result['saved_native_calls'] == 0
    assert result['descriptive_geometry_replay'] == {}
    assert result['scientific_qualification'] == 'NOT_ASSESSED'
