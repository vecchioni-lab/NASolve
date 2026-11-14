"""Saved linked-native transport uses exact envelopes, never captured programs."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).parents[1]


def module():
    spec = importlib.util.spec_from_file_location(
        'saved_mixed_linked_ferry', ROOT/'scripts/mixed_linked_recovery_probe_template.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def saved_capsule(tmp_path, defect='none'):
    """Artificial return envelope; the scientific reader remains authoritative."""
    qualification = {'status': 'REVIEW', 'mechanics_checks_pass': False,
        'checks': [{'check': 'full-model-narestraints-membership', 'status': 'REVIEW'}],
        'membership': {'checks': {'all_declared_backbone_links_exact': True,
            'active:dna_classification': False}}}
    qualification_bytes = json.dumps(qualification).encode()
    main = {'schema_version': 1, 'status': 'REVIEW', 'targets': ['Q17'],
        'new_native_calls': 2, 'maximum_native_calls': 2,
        'native_baseline': {'receipt': {'anchor': 'mixed_linked_recovery_directory',
            'path': 'native/baseline/native_receipt.json', 'size': 3, 'sha256': 'a'*64}},
        'native_active': {'receipt': {'anchor': 'mixed_linked_recovery_directory',
            'path': 'native/active/native_receipt.json', 'size': 3, 'sha256': 'b'*64}},
        'qualification': {'artifact': {'anchor': 'mixed_linked_recovery_directory',
            'path': 'qualification.json', 'size': len(qualification_bytes),
            'sha256': sha256(qualification_bytes).hexdigest()}},
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES',
            'selected': 'verified_constructed_model', 'native_usable': 'NOT_YET_QUALIFIED',
            'requires_cif_review': False, 'automatic_adoption': False}}
    header = {'kind': 'mixed-linked-recovery-probe', 'delivery_prefix': '84_Cedar',
        'analysis_completed': False, 'error_type': 'ValueError',
        'error': 'Linked native qualification does not reproduce',
        'automatic_adoption': False, 'requires_cif_review': False}
    if defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'kind': header['kind'] = 'unrelated-probe'
    elif defect == 'completed': header['analysis_completed'] = True
    elif defect == 'exception': header['error_type'] = 'OSError'
    elif defect == 'error': header['error'] = 'Different native failure'
    elif defect == 'status': main['status'] = 'PREPARED_ONLY'
    elif defect == 'count': main['new_native_calls'] = 1
    elif defect == 'qualification': main['qualification'] = {'status': 'NOT_RUN'}
    elif defect == 'active': main['native_active'] = {'status': 'NOT_RUN'}
    members = {'probe_receipt.json': json.dumps(header).encode(),
        'mixed_linked_recovery/mixed_linked_recovery.json': json.dumps(main).encode(),
        'mixed_linked_recovery/qualification.json': qualification_bytes,
        'mixed_linked_recovery/native/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/private-parent.json': b'{"opaque_parent":true}\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    manifest = {n: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
                for n, data in members.items()}
    if defect == 'hash': manifest['mixed_linked_recovery/qualification.json']['sha256'] = '0'*64
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'saved.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members


@pytest.mark.parametrize('defect', ['none', 'prefix', 'kind', 'completed', 'exception',
    'error', 'status', 'count', 'qualification', 'active', 'path', 'hash', 'symlink', 'archive'])
def test_saved_capsule_requires_exact_failure_envelope_and_complete_native_scope(tmp_path, defect):
    ferry = module()
    path, digest, members = saved_capsule(tmp_path, defect)
    ferry.SAVED_REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    if defect == 'none':
        actual = ferry._read_capsule(path, saved_native_only=True)
        assert {name: actual[name] for name in members} == members
    else:
        with pytest.raises(ValueError):
            ferry._read_capsule(path, saved_native_only=True)
    assert not (tmp_path/'outside').exists()


def test_saved_replay_reads_only_shallow_scientific_view_and_removes_it(tmp_path, monkeypatch):
    ferry = module()
    _, _, members = saved_capsule(tmp_path)
    main = json.loads(members['mixed_linked_recovery/mixed_linked_recovery.json'])
    observed = []

    def trusted_reader(root):
        root = Path(root)
        observed.append(root)
        assert root.is_dir()
        assert (root/'native/captured.py').read_bytes() == members['mixed_linked_recovery/native/captured.py']
        assert not (root/'inputs/review/private-parent.json').exists()
        assert not (root/'probe_receipt.json').exists()
        return main

    monkeypatch.setattr('nasolve.cif_mixed_linked_recovery.read_mixed_linked_recovery', trusted_reader)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('saved replay started an SDK process'))
    result = ferry._replay_saved_native(members)
    assert observed and all(not root.exists() for root in observed)
    assert result['status'] == 'REVIEW' and result['targets'] == ['Q17']
    assert result['coordinate_decision'] == main['coordinate_decision']
    assert result['saved_native_calls'] == 2 and result['new_native_calls'] == 0
    assert result['policy_id'] == 'cif-saved-mixed-linked-recovery-v1'
    for name in ['report', 'qualification']:
        ref = result[name] if name == 'report' else result[name]['artifact']
        assert ref['anchor'] == 'preserved_review'
        assert ref['path'].startswith('mixed_linked_recovery/')
        assert ref['size'] == len(members[ref['path']])
        assert ref['sha256'] == sha256(members[ref['path']]).hexdigest()
    expected_qualification = json.loads(members['mixed_linked_recovery/qualification.json'])
    assert result['qualification']['checks'] == expected_qualification['checks']
    assert result['qualification']['membership'] == expected_qualification['membership']['checks']
    assert members['mixed_linked_recovery/native/captured.py'].startswith(b'raise RuntimeError')


def test_saved_replay_never_turns_a_rejected_scientific_reader_into_success(tmp_path, monkeypatch):
    ferry = module()
    _, _, members = saved_capsule(tmp_path)
    observed = []

    def rejected(root):
        observed.append(Path(root))
        raise ValueError('bound native evidence differs')

    monkeypatch.setattr('nasolve.cif_mixed_linked_recovery.read_mixed_linked_recovery', rejected)
    with pytest.raises(ValueError, match='bound native evidence differs'):
        ferry._replay_saved_native(members)
    assert observed and all(not root.exists() for root in observed)


def test_saved_replay_and_inspect_modes_are_mutually_exclusive(tmp_path, monkeypatch, capsys):
    ferry = module()
    monkeypatch.setattr('sys.argv', ['saved-probe', '--review-zip', str(tmp_path/'not-read.zip'),
        '--inspect-only', '--saved-native-only'])
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('conflicting modes read runtime'))
    with pytest.raises(SystemExit) as stopped:
        ferry.main()
    assert stopped.value.code == 2
    assert 'not allowed with argument' in capsys.readouterr().err


def test_saved_main_keeps_review_and_parent_without_sdk_discovery(tmp_path, monkeypatch, capsys):
    """Exercise the actual main branch, archive transport and summary publication."""
    import nasolve
    import restraints
    ferry = module()
    path, digest, original_members = saved_capsule(tmp_path)
    original_zip = path.read_bytes()
    main = json.loads(original_members['mixed_linked_recovery/mixed_linked_recovery.json'])
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '85_Cedar'})
    monkeypatch.setattr(ferry, 'SAVED_REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        # Main's import-origin check stays active. A separate source-removed cold
        # test covers actual bundled import isolation; this fixture owns no SDK.
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    def forbidden(*args, **kwargs): pytest.fail('saved main attempted SDK discovery or execution')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_linked_recovery.audit_mixed_linked_recovery', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_linked_recovery.read_mixed_linked_recovery', lambda root: main)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    output = tmp_path/'outputs'
    monkeypatch.setattr('sys.argv', ['saved-probe', '--review-zip', str(path),
        '--saved-native-only', '--phenix-root', str(tmp_path/'NO_SDK'), '--output-parent', str(output)])
    assert ferry.main() == 2  # Retained scientific REVIEW is a completed replay.
    text = capsys.readouterr()
    assert 'new native calls: 0' in text.out and not text.err
    archive = next(output.glob('*/*_mixed_linked_recovery_review.zip'))
    with ZipFile(archive) as captured:
        returned = {name: captured.read(name) for name in captured.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert receipt['saved_linked_recovery']['new_native_calls'] == 0
    assert receipt['saved_linked_recovery']['saved_native_calls'] == 2
    assert receipt['saved_linked_recovery']['status'] == 'REVIEW'
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert 'phenix' not in receipt
    saved = json.loads(returned['saved_linked_recovery.json'])
    assert saved['coordinate_decision'] == main['coordinate_decision']
    assert all(returned['inputs/review/'+name] == data for name, data in original_members.items())
    assert path.read_bytes() == original_zip
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
        for name, ref in manifest.items())
