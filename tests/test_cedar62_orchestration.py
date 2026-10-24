"""Fresh ordinary construction consumes exact qualified source artifacts only."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def template():
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar62action', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_members():
    prefix = 'inputs/review/' * 4
    members = {('inputs/review/' * i) + 'probe_receipt.json': json.dumps(
        {'delivery_prefix': f'{61-i}_Cedar'}).encode() for i in range(4)}
    cases = {}
    for code in ['DP', 'PDU', '5PC']:
        data = ('EXPLICIT_FAKE_' + code).encode()
        directory = 'source_classification/' + code
        cases[code] = {'preparation': {'directory': {'anchor': 'probe_directory', 'path': directory},
            'candidate': {'anchor': 'candidate_directory', 'path': 'candidate.cif',
                'sha256': sha256(data).hexdigest(), 'size': len(data)}},
            'decision': {'status': 'CONTINUE_WITH_NOTES', 'selected_candidate': 'source_declared_dna'}}
        members[prefix + directory + '/candidate.cif'] = data
    members[prefix + 'probe_receipt.json'] = json.dumps({'delivery_prefix': '57_Cedar',
        'source_classification_audit': {'cases': cases}}).encode()
    return members


def materialize(members, folder):
    for name, data in members.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


@pytest.mark.parametrize('defect', ['none', 'lineage', 'hash', 'size', 'unsafe', 'decision', 'frozen_copy'])
def test_control_sources_follow_exact_declared_candidate_references(tmp_path, defect):
    module = template(); members = source_members()
    key = 'inputs/review/' * 4 + 'probe_receipt.json'
    current = json.loads(members[key]); row = current['source_classification_audit']['cases']['DP']
    if defect == 'lineage': members['probe_receipt.json'] = b'{"delivery_prefix":"60_Cedar"}'
    if defect == 'hash': row['preparation']['candidate']['sha256'] = '0' * 64
    if defect == 'size': row['preparation']['candidate']['size'] += 1
    if defect == 'unsafe': row['preparation']['directory']['path'] = '../elsewhere'
    if defect == 'decision': row['decision']['selected_candidate'] = 'UNQUALIFIED'
    members[key] = json.dumps(current).encode()
    materialize(members, tmp_path)
    if defect == 'frozen_copy':
        (tmp_path / ('inputs/review/' * 4) / 'source_classification/DP/candidate.cif').write_bytes(b'CHANGED')
    if defect != 'none':
        with pytest.raises(ValueError): module._postmr_control_dictionaries(members, tmp_path)
    else:
        paths, references = module._postmr_control_dictionaries(members, tmp_path)
        assert list(paths) == ['DP', 'PDU', '5PC']
        assert all(paths[code].read_bytes() == members[references[code]['path']] for code in paths)


@pytest.mark.parametrize('mode', ['live', 'inspect_only', 'construction_review', 'source_drift', 'executable_drift'])
def test_fresh_action_uses_ordinary_discovery_and_preserves_qualified_evidence(tmp_path, monkeypatch, mode):
    from nasolve import cif_postmr_construction, config, coot_runtime
    module = template(); session = tmp_path / 'session'; frozen = session / 'inputs/review'
    members = source_members(); materialize(members, frozen)
    canonical = 'MR_frames/5W6W/5W6W_noPO4.pdb'
    runtime = {canonical: b'EXPLICIT_FAKE_CANONICAL'}
    materialize(runtime, session / 'runtime')
    archive = tmp_path / 'review.zip'; archive.write_bytes(b'EXPLICIT_FAKE_ARCHIVE')
    executable = tmp_path / 'coot'; executable.write_bytes(b'EXPLICIT_FAKE_COOT')
    calls = []
    def discover(conf, **kwargs):
        calls.append('discover')
        assert conf == 'EXPLICIT_FAKE_CONFIG' and kwargs['explicit'] == executable
        return SimpleNamespace(executable=executable, version='EXPLICIT_FAKE_VERSION', source='override')
    monkeypatch.setattr(config, 'load_config', lambda: 'EXPLICIT_FAKE_CONFIG')
    monkeypatch.setattr(coot_runtime, 'discover_coot', discover)
    def construct(model, dictionaries, output, **kwargs):
        calls.append('construct')
        assert model.read_bytes() == runtime[canonical]
        assert list(dictionaries) == ['DP', 'PDU', '5PC']
        assert kwargs['timeout_seconds'] == 600
        assert kwargs['inspect_only'] is (mode == 'inspect_only')
        assert kwargs['coot_executable'] == (None if mode == 'inspect_only' else executable)
        if mode == 'source_drift': dictionaries['DP'].write_bytes(b'CHANGED')
        if mode == 'executable_drift': executable.write_bytes(b'CHANGED')
        return {'policy_id': 'cif-postmr-construction-controls-v1',
            'status': 'REVIEW' if mode == 'construction_review' else 'PASS', 'requires_cif_review': False}
    monkeypatch.setattr(cif_postmr_construction, 'run_postmr_construction_controls', construct)
    monkeypatch.setattr(module, '_review_zip', lambda *a: 'EXPLICIT_FAKE_OUTPUT_ZIP')
    args = SimpleNamespace(inspect_only=mode == 'inspect_only', coot=executable, timeout_seconds=1000)
    receipt = {}
    if mode.endswith('_drift'):
        with pytest.raises(ValueError):
            module._run_postmr_construction_action(args, receipt, session, archive, archive.read_bytes(), members, frozen, runtime)
        return
    assert module._run_postmr_construction_action(args, receipt, session, archive, archive.read_bytes(), members, frozen, runtime) == 2
    assert calls == (['construct'] if mode == 'inspect_only' else ['discover', 'construct'])
    report = receipt['postmr_construction_audit']
    assert report['qualified_runtime_input']['native_checks'] == 15
    assert receipt['requires_cif_review'] is False
    assert receipt['native_execution'] == ('NOT_RUN' if mode == 'inspect_only' else 'FRESH_COOT_POSTMR_CONSTRUCTION')
    assert all((frozen / name).read_bytes() == data for name, data in members.items())
