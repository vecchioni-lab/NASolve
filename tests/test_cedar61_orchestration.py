"""Activation uses the ordinary loader and one fixed native readback only."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('mode', ['pass', 'inspect_only', 'native_failed', 'native_drift', 'energy_source_drift'])
def test_runtime_activation_preserves_sources_and_uses_the_standard_bundle(tmp_path, monkeypatch, mode):
    from nasolve import cif_native_validation, phenix_runtime
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar61action', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    session = tmp_path / 'session'
    frozen = session / 'inputs/review'
    frozen.mkdir(parents=True)
    pins = [{'module': f'fake{i}', 'sha256': str(i) * 64} for i in range(3)]
    expected = {'atom_count': 2, 'energy_inventory': {'installed_sources': pins}}
    rows = [{'role': role, 'path': name, 'sha256': 'a' * 64, 'size': 1}
            for role, name in [('model', 'model.pdb'), ('dictionary', 'dictionary.cif'), ('phil', 'policy.phil')]]
    capture = {'directory': {'path': 'native_endpoint'}, 'inputs': rows, 'native_validation': expected}
    decision = {'selected_candidate': 'qualified_geometry_endpoint'}
    audit = {'native_roundtrip': capture, 'decision': decision, 'geometry_trial': {'result': {'serialized': {'target': 5.}}},
             'serialization': {'explicit_fake': 'serialization'}}
    old = {'directory': {'path': 'native_initial'}, 'inputs': rows, 'native_validation': expected}
    previous = {'candidate': old, 'qualification': {'explicit_fake': 'passed initial'}}
    members = {'scaffold_geometry_audit.json': json.dumps(audit).encode(),
               'inputs/review/scaffold_candidate_audit.json': json.dumps(previous).encode()}
    for prefix in ['native_endpoint', 'inputs/review/native_initial']:
        members.update({prefix + '/' + row['path']: b'EXPLICIT_FAKE_' + row['role'].encode() for row in rows})
    for name, data in members.items():
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive = tmp_path / 'review.zip'
    archive.write_bytes(b'EXPLICIT_FAKE_ARCHIVE')
    calls = []
    monkeypatch.setattr(module, '_replay_scaffold_geometry', lambda data: {
        'policy_id': 'EXPLICIT_FAKE_REPLAY', 'status': 'EXPLICIT_FAKE_REPLAYED', 'component': 'DP',
        'selected_sites': ['B:4'], 'atom_count': 2, 'decision': decision,
        'selected_model': {}, 'starting_model': {}, 'captured_code_execution': 'NOT_RUN'})
    package = {}
    def prepare(model, dictionaries, phils, output, **kwargs):
        calls.append('prepare')
        assert model.read_bytes() == b'EXPLICIT_FAKE_model'
        assert len(dictionaries) == len(phils) == 1
        assert kwargs['decision'] == decision and kwargs['native_validation'] == expected
        assert kwargs['provenance']['source_inputs'] == [{k: row[k] for k in ['role', 'sha256', 'size']} for row in rows]
        assert kwargs['provenance']['initial_model'].read_bytes() == b'EXPLICIT_FAKE_model'
        output.mkdir()
        manifest = {'manifest_file': 'runtime_bundle.json', 'explicit_fake': 'activated'}
        (output / 'runtime_bundle.json').write_text(json.dumps(manifest))
        package.update(model=model, dictionaries=dictionaries, phils=phils, manifest=manifest)
        return manifest
    def resolve(path):
        calls.append('resolve')
        assert path.is_file()
        return package
    def assess(path):
        calls.append('assess')
        return {'status': 'REVIEW', 'explicit_fake': 'report-only findings'}
    monkeypatch.setitem(sys.modules, 'nasolve.cif_runtime_bundle', SimpleNamespace(
        prepare_runtime_bundle=prepare, resolve_runtime_bundle=resolve, assess_runtime_bundle=assess))
    monkeypatch.setattr(phenix_runtime, 'installation_from_candidate', lambda *a, **kw: SimpleNamespace(
        version='EXPLICIT_FAKE_VERSION', environment={}, executables={'phenix.python': tmp_path / 'python'}))
    monkeypatch.setattr(module, '_fingerprints', lambda *a: [])
    def native(model, dictionaries, output, executable, **kwargs):
        calls.append('native')
        assert kwargs['timeout_seconds'] == 60 and kwargs['policy_inventory'] is True
        assert kwargs['energy_inventory'] is True and kwargs['inventory_detail'] == 'linked'
        assert kwargs['phil_namespace_policy'] == 'refinement-root-to-interpreter-v1'
        assert kwargs['phil_files'] == package['phils']
        output.mkdir()
        result = deepcopy(expected)
        if mode == 'energy_source_drift': result['energy_inventory']['installed_sources'][0]['sha256'] = 'f' * 64
        return {'native_directory': str(output), 'status': 'FAILED' if mode == 'native_failed' else 'REVIEW',
                'execution': {'status': 'FAILED' if mode == 'native_failed' else 'COMPLETED', 'returncode': 1 if mode == 'native_failed' else 0},
                'source_preserved': True, 'frozen_inputs_preserved': True, 'native_validation': result}
    monkeypatch.setattr(cif_native_validation, 'inspect_native_bundle', native)
    monkeypatch.setattr(module, '_runtime_readback_checks', lambda *a: {
        'checks': {'exact_bundle': mode != 'native_drift'}, 'native_usable': mode != 'native_drift'})
    monkeypatch.setattr(module, '_review_zip', lambda *a: 'EXPLICIT_FAKE_OUTPUT_ZIP')
    args = SimpleNamespace(inspect_only=mode == 'inspect_only', timeout_seconds=600, phenix_root=tmp_path)
    receipt = {}
    assert module._run_runtime_bundle_action(args, receipt, session, archive, archive.read_bytes(), members, frozen) == 2
    report = receipt['runtime_bundle_audit']
    assert calls == ['prepare', 'resolve', 'assess', *([] if mode == 'inspect_only' else ['native']), 'resolve']
    assert report['model_optimization'] == report['dictionary_generation'] == report['refinement'] == 'NOT_RUN'
    assert report['production_checkpoint'] == 'NOT_CREATED' and report['existing_runs'] == 'UNCHANGED'
    if mode in {'pass', 'native_drift', 'energy_source_drift'}:
        assert report['native_qualification']['native_usable'] is (mode == 'pass')
    assert receipt['analysis_completed'] and not receipt['requires_cif_review']
    assert archive.read_bytes() == b'EXPLICIT_FAKE_ARCHIVE'
    assert all((frozen / name).read_bytes() == data for name, data in members.items())
