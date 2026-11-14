"""Repair publication wiring; upstream native verifiers are explicitly synthetic."""
from copy import deepcopy
from pathlib import Path
import json, shutil
from unittest.mock import patch
import pytest
from tests.test_cif_dictionary_bundle_repair import fixture


def prepare(tmp_path, monkeypatch, fallback=False):
    _, root, args, state = fixture(tmp_path, monkeypatch)
    from nasolve import cif_component_runtime as runtime
    if fallback:
        (root/'repaired/captured_mixed_gradients.json').write_text(json.dumps(dict(status='REVIEW')))
    out = tmp_path/'runtime'
    value = runtime.prepare_repaired_component_runtime_bundle(output=out, **args)
    return runtime, root, args, state, out, value


@pytest.mark.parametrize('fallback', [False, True])
def test_source_and_repair_proofs_are_frozen_and_publicly_resolved(tmp_path, monkeypatch, fallback):
    runtime, root, args, state, out, value = prepare(tmp_path, monkeypatch, fallback)
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    selected = 'verified_prepared_bundle' if fallback else 'repaired_prepared_bundle'
    assert value['policy_id'] == runtime.REPAIRED_POLICY_ID
    assert value['decision']['selected'] == selected
    expected = args['bundle']/'0.cif' if fallback else args['attribution_directory']/'bundle/repaired.cif'
    payload = expected.read_bytes()
    shutil.rmtree(root)
    moved = out.rename(tmp_path/'relocated')
    before = {p.relative_to(moved):p.read_bytes() for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen', side_effect=AssertionError('No native process during replay')):
        result = resolve_runtime_bundle(moved)
        assert result['dictionaries'][0].read_bytes() == payload
        summary = runtime.component_runtime_summary(result['manifest'])
    assert summary['qualification_scope'] == 'SEPARATE_DIAGNOSTIC_PHASE_ONLY'
    assert 'repaired' in summary['text'] if not fallback else 'starting' in summary['text']
    assert not value['automatic_adoption'] and value['refinement'] == 'NOT_RUN'
    assert before == {p.relative_to(moved):p.read_bytes() for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect', ['resource', 'source', 'selection', 'rehashed_resource', 'derivatives', 'policy', 'scope', 'extra', 'path_escape', 'missing_attribution', 'symlink', 'evidence_root'])
def test_changed_frozen_proof_or_selected_resources_refuse(tmp_path, monkeypatch, defect):
    runtime, root, args, state, out, value = prepare(tmp_path, monkeypatch)
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle, _reference
    if defect in ('resource', 'rehashed_resource'):
        ref = value['resources']['dictionaries'][0]; p = out/ref['relative_path']; p.write_text('changed')
        if defect == 'rehashed_resource':
            updated = _reference(p, out)
            value['resources']['dictionaries'][0] = updated
            value['files'] = [updated if r['relative_path']==ref['relative_path'] else r for r in value['files']]
    elif defect == 'source': (out/'evidence/bundle/0.cif').write_text('changed')
    elif defect == 'selection': value['decision']['selected'] = 'verified_prepared_bundle'
    elif defect == 'derivatives':
        p=out/'evidence/repaired-gradient/captured_mixed_gradients.json'; p.write_text(json.dumps(dict(status='REVIEW')))
        value['files']=[_reference(out/r['relative_path'],out) for r in value['files']]
    elif defect == 'policy': value['policy_id'] = runtime.POLICY_ID
    elif defect == 'scope': value['scope'] = 'ORDINARY_REFINEMENT'
    elif defect == 'extra': (out/'extra').write_text('extra')
    elif defect == 'path_escape': value['source_selection']['baseline_receipt'] = '../outside'
    elif defect == 'missing_attribution': value['source_selection'].pop('attribution_directory')
    elif defect == 'symlink':
        p=out/'evidence/bundle/0.cif'; p.unlink(); p.symlink_to(args['bundle']/'0.cif')
    elif defect == 'evidence_root': (out/'evidence/unrequested').mkdir()
    (out/'runtime_bundle.json').write_text(json.dumps(value))
    with pytest.raises(ValueError): resolve_runtime_bundle(out)


@pytest.mark.parametrize('mode', ['no_usable', 'source_unqualified', 'existing_output', 'nested_output', 'file_bound', 'byte_bound'])
def test_publication_never_promotes_absence_or_overwrites_evidence(tmp_path, monkeypatch, mode):
    _, root, args, state = fixture(tmp_path, monkeypatch)
    from nasolve import cif_component_runtime as runtime
    out = tmp_path/'runtime'
    if mode == 'no_usable': args.update(repaired_gradient_directory=None, original_gradient_directory=None)
    elif mode == 'source_unqualified': state['source_usable'] = False
    elif mode == 'existing_output': out.mkdir(); (out/'owned').write_text('keep')
    elif mode == 'nested_output': out = args['bundle']/'nested'
    elif mode == 'file_bound': monkeypatch.setattr(runtime, 'MAX_FILES', 1)
    elif mode == 'byte_bound': monkeypatch.setattr(runtime, 'MAX_BYTES', 1)
    with pytest.raises((ValueError, FileExistsError)):
        runtime.prepare_repaired_component_runtime_bundle(output=out, **args)
    if mode == 'existing_output': assert (out/'owned').read_text() == 'keep'
    else: assert not out.exists()


def test_original_proof_is_optional_when_repaired_bundle_is_qualified(tmp_path, monkeypatch):
    _, root, args, state = fixture(tmp_path, monkeypatch)
    from nasolve import cif_component_runtime as runtime
    args['original_gradient_directory'] = None
    result = runtime.prepare_repaired_component_runtime_bundle(output=tmp_path/'runtime', **args)
    assert result['decision']['selected'] == 'repaired_prepared_bundle'
    assert result['source_selection']['original_gradient_directory'] is None


def test_changed_source_during_publication_leaves_no_final_bundle(tmp_path, monkeypatch):
    _, root, args, state = fixture(tmp_path, monkeypatch)
    from nasolve import cif_component_runtime as runtime
    original = runtime.resolve_component_runtime_bundle
    def changed(*a, **k):
        result = original(*a, **k)
        (args['bundle']/'0.cif').write_text('concurrent change')
        return result
    monkeypatch.setattr(runtime, 'resolve_component_runtime_bundle', changed)
    with pytest.raises(ValueError, match='Source evidence changed'):
        runtime.prepare_repaired_component_runtime_bundle(output=tmp_path/'runtime', **args)
    assert not (tmp_path/'runtime').exists()
