"""A measured inspection snapshot is neither a producer receipt nor an approval."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve import model_inspection as inspection
from nasolve.coot_view import CootViewError, resolve_view_profile
from nasolve.run_context import resolve_artifact_path
from tests.test_coot_view import make_view_run, add_manual_checkpoint, add_review_checkpoint


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_snapshot_pins_selected_bytes_without_launch_or_checkpoint_selection(tmp_path):
    run = make_view_run(tmp_path)
    add_review_checkpoint(run)
    before = tree_bytes(tmp_path)
    with patch('subprocess.Popen', side_effect=AssertionError('Inspection must not launch tools')):
        result = inspection.inspect_model_map(run, checkpoint='refine-002')
    assert json.loads(json.dumps(result)) == result
    assert result['selection'] == {'stage': 'autorefine', 'checkpoint_id': 'refine-002'}
    assert result['map_origin'] == {'stage': 'autorefine', 'checkpoint_id': 'refine-002', 'inherited_through': []}
    assert result['artifact_hash_basis'] == 'measured_at_inspection'
    assert result['generation_evidence'] == result['frame_evidence'] == 'not_assessed'
    for role in ('model', 'map'):
        ref = result['artifacts'][role]
        path = resolve_artifact_path(ref, run)
        assert path is not None
        assert hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256']
        assert path.stat().st_size == ref['size']
    assert result['reference_scope'] == 'anchored'
    assert tree_bytes(tmp_path) == before


def test_inherited_snapshot_relocates_without_the_associated_ancestor_model(tmp_path):
    original = tmp_path/'original'
    run = make_view_run(original)
    add_manual_checkpoint(run)
    registry = json.loads((run/'AutoRefine/checkpoints.json').read_text())
    Path(registry['checkpoints'][0]['model']['path']).unlink()
    first = inspection.inspect_model_map(run)
    assert first['selection']['checkpoint_id'] == 'manual-001'
    assert first['map_origin']['checkpoint_id'] == 'refine-001'
    assert first['map_origin']['inherited_through'] == ['manual-001']
    moved = tmp_path/'moved'; original.rename(moved)
    run = moved/'dataset/AutoMR/run_001'
    before = tree_bytes(moved)
    assert inspection.inspect_model_map(run) == first
    assert resolve_artifact_path(first['artifacts']['map'], run).is_relative_to(moved.resolve())
    assert tree_bytes(moved) == before and not original.exists()


def test_external_explicit_map_remains_usable_without_an_anchored_claim(tmp_path):
    run = make_view_run(tmp_path/'project')
    outside = tmp_path/'external.mtz'; outside.write_bytes(b'explicit external map')
    p = run/'AutoRefine/checkpoints.json'; registry = json.loads(p.read_text())
    registry['checkpoints'][0]['outputs']['map_coefficients'] = str(outside)
    p.write_text(json.dumps(registry))
    result = inspection.inspect_model_map(run)
    assert result['reference_scope'] == 'contains_external_paths'
    assert result['artifacts']['map']['anchor'] == 'absolute'
    assert resolve_artifact_path(result['artifacts']['map'], run) == outside.resolve()


def test_current_choice_changed_during_snapshot_is_not_silently_mixed(tmp_path, monkeypatch):
    run = make_view_run(tmp_path); add_review_checkpoint(run)
    calls = []
    def changing(root, **selection):
        calls.append(1)
        if len(calls) == 2:
            p = run/'AutoRefine/checkpoints.json'; r = json.loads(p.read_text())
            r['current'] = 'refine-002'; p.write_text(json.dumps(r))
        return resolve_view_profile(root, **selection)
    monkeypatch.setattr(inspection, 'resolve_view_profile', changing)
    with pytest.raises(inspection.InspectionError, match='selection changed'):
        inspection.inspect_model_map(run)


def test_legacy_model_changed_after_measurement_does_not_get_a_fresh_binding(tmp_path, monkeypatch):
    run = make_view_run(tmp_path)
    original = inspection._file_reference
    changed = []
    def changing(path, context):
        result = original(path, context)
        if not changed:
            changed.append(path); path.write_bytes(path.read_bytes()+b'REMARK changed during inspection\n')
        return result
    monkeypatch.setattr(inspection, '_file_reference', changing)
    with pytest.raises(inspection.InspectionError, match='changed during inspection'):
        inspection.inspect_model_map(run)


def test_existing_declared_map_refusal_is_preserved(tmp_path):
    run = make_view_run(tmp_path)
    p = run/'AutoRefine/checkpoints.json'; registry = json.loads(p.read_text())
    map_path = Path(registry['checkpoints'][0]['outputs']['map_coefficients'])
    registry['checkpoints'][0]['outputs']['map_coefficients'] = {
        'anchor': 'run', 'relative_path': str(map_path.relative_to(run)),
        'sha256': hashlib.sha256(map_path.read_bytes()).hexdigest(),
    }
    p.write_text(json.dumps(registry)); map_path.write_bytes(b'changed declared coefficients')
    with pytest.raises(CootViewError, match='checksum'):
        inspection.inspect_model_map(run)
