"""The ordinary bundle reader must accept a qualified mixed endpoint."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

import pytest


def _dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True))


def fixture(tmp_path, monkeypatch):
    from nasolve import cif_mixed_runtime_bundle as mixed
    from tests.test_cif_runtime_bundle import case
    model, cifs, phils, decision, native, _ = case(tmp_path/'inputs')
    second = tmp_path/'inputs/second.cif'; second.write_bytes(cifs[0].read_bytes()+b'\n# independent ordered resource\n')
    cifs.append(second)
    decision['selected'] = decision.pop('selected_candidate')
    decision.update(scientific_qualification='NOT_ASSESSED', requires_cif_review=False)
    source = tmp_path/'source.zip'; source.write_bytes(b'BOUND_SOURCE_CAPSULE')
    replay = {'status': 'SAVED_ENDPOINT_REPLAY_PASS', 'coordinate_decision': decision,
              'new_native_calls': 0, 'saved_native_calls': 2, 'scientific_qualification': 'NOT_ASSESSED'}
    rows = [(role, path.read_bytes()) for role, paths in [('model', [model]), ('dictionary', cifs), ('phil', phils)] for path in paths]
    calls = []
    @contextmanager
    def verified(path, digest):
        calls.append((Path(path), digest))
        assert sha256(Path(path).read_bytes()).hexdigest() == digest
        yield {'replay': deepcopy(replay), 'resources': [(role, f'{i:03d}_{role}', data) for i, (role, data) in enumerate(rows)],
               'atom_count': native['atom_count'], 'source_chemical_findings': 'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_ENDPOINT_QUALIFICATION'}
    monkeypatch.setattr(mixed, 'verified_endpoint_source', verified)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Bundle handoff launched process'))
    return mixed, source, replay, rows, calls


def activate(tmp_path, monkeypatch):
    mixed, source, replay, rows, calls = fixture(tmp_path, monkeypatch)
    output = tmp_path/'bundle'
    manifest = mixed.prepare_mixed_runtime_bundle(source, output, source_sha256=sha256(source.read_bytes()).hexdigest())
    return mixed, output, manifest, source, replay, rows, calls


def test_ordinary_reader_hands_off_mixed_selection_with_exact_inputs_and_notes(tmp_path, monkeypatch):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle, assess_runtime_bundle
    mixed, output, manifest, source, replay, rows, calls = activate(tmp_path, monkeypatch)
    before = {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    resolved = resolve_runtime_bundle(output)
    assert [resolved['model'].read_bytes(), *[p.read_bytes() for p in resolved['dictionaries']], *[p.read_bytes() for p in resolved['phils']]] == [d for _, d in rows]
    result = assess_runtime_bundle(output)
    assert result['bundle_context']['policy_id'] == mixed.POLICY_ID
    assert result['solution_report']['selected_candidate'] == 'qualified_geometry_endpoint'
    assert result['solution_report']['stopping'] == replay['coordinate_decision']['stopping']
    assert result['solution_report']['native_selection_executed'] is False
    assert result['solution_report']['scientific_qualification'] == 'NOT_ASSESSED'
    assert result['requires_cif_review'] is False and result['solution_report']['pdf_status'] == 'PLANNED'
    assert len(calls) == 3  # Prepare, resolve, assess; the post-assess integrity check only hashes.
    assert before == {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    assert (output/manifest['source_capsule']['relative_path']).read_bytes() == source.read_bytes()


def test_relocation_keeps_one_opaque_parent_and_needs_no_original_source_or_paths(tmp_path, monkeypatch):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    _, output, manifest, source, _, _, _ = activate(tmp_path, monkeypatch)
    moved = tmp_path/'moved'; output.rename(moved); source.unlink(); shutil.rmtree(tmp_path/'inputs')
    result = resolve_runtime_bundle(moved/'runtime_bundle.json')
    assert result['manifest'] == manifest and result['model'].parent.parent == moved
    assert len(list(moved.rglob('*.zip'))) == 1


@pytest.mark.parametrize('defect', ['model', 'dictionary', 'phil', 'capsule', 'missing', 'alias', 'traversal', 'absolute',
    'anchor', 'bool_size', 'symlink', 'unknown_policy', 'schema_bool', 'decision', 'adoption', 'optimization', 'refinement',
    'science', 'checkpoint', 'source_hash', 'resource_reorder', 'forged_resource_hash'])
def test_changed_or_forged_bundle_cannot_be_promoted(tmp_path, monkeypatch, defect):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    _, output, manifest, _, _, _, _ = activate(tmp_path, monkeypatch)
    resources = manifest['resources']; row = resources['model']
    if defect in {'model', 'dictionary', 'phil', 'capsule'}:
        row = resources['dictionaries'][0] if defect == 'dictionary' else resources['phils'][0] if defect == 'phil' else manifest['source_capsule'] if defect == 'capsule' else row
        (output/row['relative_path']).write_bytes(b'CHANGED')
    elif defect == 'missing': (output/row['relative_path']).unlink()
    elif defect == 'alias': resources['phils'][0] = deepcopy(resources['dictionaries'][0])
    elif defect == 'traversal': row['relative_path'] = '../source.zip'
    elif defect == 'absolute': row['relative_path'] = '/outside/model.pdb'
    elif defect == 'anchor': row['anchor'] = 'historical_path'
    elif defect == 'bool_size': row['size'] = True
    elif defect == 'symlink':
        p = output/row['relative_path']; saved = tmp_path/'outside.pdb'; p.rename(saved); p.symlink_to(saved)
    elif defect == 'unknown_policy': manifest['policy_id'] = 'unknown'
    elif defect == 'schema_bool': manifest['schema_version'] = True
    elif defect == 'decision': manifest['decision']['endpoint_usable'] = False
    elif defect == 'adoption': manifest['automatic_adoption'] = True
    elif defect == 'optimization': manifest['model_optimization'] = 'COMPLETED'
    elif defect == 'refinement': manifest['refinement'] = 'COMPLETED'
    elif defect == 'science': manifest['scientific_approval'] = 'APPROVED'
    elif defect == 'checkpoint': manifest['checkpoint_adoption'] = 'COMPLETED'
    elif defect == 'source_hash': manifest['source_archive']['sha256'] = '0'*64
    elif defect == 'resource_reorder': resources['dictionaries'].reverse()
    elif defect == 'forged_resource_hash':
        p = output/row['relative_path']; p.write_bytes(b'CHANGED'); row.update(size=p.stat().st_size, sha256=sha256(p.read_bytes()).hexdigest())
    _dump(output/'runtime_bundle.json', manifest)
    with pytest.raises(ValueError): resolve_runtime_bundle(output)


def test_destination_and_source_are_preserved_on_refusal(tmp_path, monkeypatch):
    mixed, source, _, _, _ = fixture(tmp_path, monkeypatch)
    original = source.read_bytes(); output = tmp_path/'existing'; output.mkdir(); (output/'keep').write_text('mine')
    with pytest.raises(FileExistsError): mixed.prepare_mixed_runtime_bundle(source, output, source_sha256=sha256(original).hexdigest())
    assert source.read_bytes() == original and (output/'keep').read_text() == 'mine'
    alias = tmp_path/'alias'; alias.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError): mixed.prepare_mixed_runtime_bundle(source, alias/'child', source_sha256=sha256(original).hexdigest())
    assert not (output/'child').exists()
