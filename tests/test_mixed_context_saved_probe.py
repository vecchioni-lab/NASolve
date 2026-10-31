"""Saved native context replay preserves completed work and its failed ferry."""
from hashlib import sha256
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from tests.test_mixed_context_probe import module


PREFIX = 'inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'


def saved_capsule(tmp_path, defect='none'):
    qualification = {'schema_version': 1, 'policy_id': 'cif-mixed-linked-context-v2',
        'status': 'MIXED_CONTEXT_MECHANICS_PASS', 'mechanics_checks_pass': True,
        'checks': [{'check': 'named native equality', 'status': 'PASS'}]}
    qdata = json.dumps(qualification).encode()
    qref = {'anchor': 'mixed_context_directory', 'path': 'qualification.json',
        'sha256': sha256(qdata).hexdigest(), 'size': len(qdata)}
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-linked-context-v2',
        'status': 'MIXED_CONTEXT_MECHANICS_PASS', 'targets': ['Q17'],
        'new_native_calls': 2, 'saved_native_calls': 2, 'maximum_native_calls': 2,
        'automatic_adoption': False, 'requires_cif_review': False,
        'qualification': {'artifact': qref},
        'native_baseline': {'receipt': {'anchor': 'mixed_context_directory', 'path': 'native/baseline.json'}},
        'native_active': {'receipt': {'anchor': 'mixed_context_directory', 'path': 'native/active.json'}},
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'verified_constructed_model',
            'native_usable': True, 'automatic_adoption': False, 'requires_cif_review': False}}
    header = {'schema_version': 1, 'kind': 'mixed-context-probe', 'delivery_prefix': '87_Cedar',
        'analysis_completed': False, 'error_type': 'ValueError',
        'error': 'Context qualification does not reproduce',
        'automatic_adoption': False, 'requires_cif_review': False,
        'policy_authority': 'NARestraints', 'captured_code_execution': 'NOT_RUN',
        'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'generation_execution': 'NOT_RUN', 'model_optimization_requested': False,
        'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    if defect == 'kind': header['kind'] = 'OTHER'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'completed': header['analysis_completed'] = True
    elif defect == 'error_type': header['error_type'] = 'RuntimeError'
    elif defect == 'error': header['error'] = 'Different failure'
    elif defect == 'approval': header['requires_cif_review'] = True
    elif defect == 'policy': report['policy_id'] = 'UNTRUSTED'
    elif defect == 'status': report['status'] = 'REVIEW'
    elif defect == 'calls': report['new_native_calls'] = 1
    elif defect == 'calls_bool': report['new_native_calls'] = True
    elif defect == 'adoption': report['automatic_adoption'] = True
    elif defect == 'qualification_anchor': qref['anchor'] = 'unbound_location'
    elif defect == 'qualification_path': qref['path'] = '../outside'
    elif defect == 'qualification_hash': qref['sha256'] = '0'*64
    elif defect == 'qualification_size': qref['size'] += 1
    members = {'probe_receipt.json': json.dumps(header).encode(),
        'mixed_context/mixed_context.json': json.dumps(report).encode(),
        'mixed_context/qualification.json': qdata,
        'mixed_context/native/baseline.json': b'{"status":"COMPLETE_NATIVE_BASELINE"}\n',
        'mixed_context/native/active.json': b'{"status":"COMPLETE_NATIVE_ACTIVE"}\n',
        'mixed_context/native/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        PREFIX+'mixed_linked_recovery.json': b'{"opaque_scientific_parent":true}\n',
        PREFIX+'inputs/model.pdb': b'EXACT SCIENTIFIC MODEL\n',
        PREFIX+'native/captured.py': b'raise RuntimeError("PARENT_CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/inputs/review/mixed_linked_recovery/mixed_linked_recovery.json': b'DECOY_OLD_PREFIX\n',
        'unrelated/model.pdb': b'DECOY_BASENAME\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['inputs/review/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['inputs/review/oversize.json'] = b' '*(33*1024*1024)
    manifest = {name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)} for name, data in members.items()}
    if defect == 'hash': manifest['mixed_context/mixed_context.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop('mixed_context/qualification.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'completed-context.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members, report


def test_exact_completed_native_return_with_failed_ferry_is_accepted(tmp_path):
    ferry = module()
    path, digest, members, _ = saved_capsule(tmp_path)
    ferry.SAVED_REVIEW_SHA256 = digest
    actual = ferry._read_capsule(path)
    assert {name: actual[name] for name in members} == members


@pytest.mark.parametrize('defect', ['large', 'kind', 'prefix', 'completed', 'error_type',
    'error', 'approval', 'policy', 'status', 'calls', 'calls_bool', 'adoption',
    'qualification_anchor', 'qualification_path', 'qualification_hash', 'qualification_size',
    'path', 'hash', 'inventory', 'symlink', 'duplicate', 'archive', 'oversize'])
def test_saved_envelope_accepts_only_exact_completed_work_and_failed_ferry(tmp_path, defect):
    ferry = module()
    path, digest, members, _ = saved_capsule(tmp_path, defect)
    ferry.SAVED_REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    original = path.read_bytes()
    if defect == 'large':
        actual = ferry._read_capsule(path)
        assert {name: actual[name] for name in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original
    assert not (tmp_path/'outside').exists()


def test_saved_parent_is_the_explicit_c87_lineage_without_older_prefix_fallback(tmp_path):
    ferry = module()
    _, _, members, _ = saved_capsule(tmp_path)
    destination = tmp_path/'parent'
    ferry._materialize_parent(members, destination)
    expected = {n[len(PREFIX):]: d for n, d in members.items() if n.startswith(PREFIX)}
    actual = {p.relative_to(destination).as_posix(): p.read_bytes()
              for p in destination.rglob('*') if p.is_file()}
    assert actual == expected


def test_saved_replay_calls_maintained_reader_and_returns_original_report(tmp_path, monkeypatch):
    ferry = module()
    _, _, members, report = saved_capsule(tmp_path)
    parent = tmp_path/'parent'
    parent.mkdir()
    destination = tmp_path/'saved-context'
    observed = []

    def read(directory, *, linked_parent_directory):
        directory = Path(directory)
        observed.append((directory, Path(linked_parent_directory)))
        assert (directory/'mixed_context.json').read_bytes() == members['mixed_context/mixed_context.json']
        assert (directory/'qualification.json').read_bytes() == members['mixed_context/qualification.json']
        assert (directory/'native/captured.py').read_bytes().startswith(b'raise RuntimeError')
        return report

    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', read)
    assert ferry._replay_saved_context(members, parent, destination) == report
    assert observed == [(destination, parent)]
    assert not (destination/'inputs').exists()
    assert not (destination/'probe_receipt.json').exists()


def test_saved_replay_propagates_maintained_reader_rejection_without_using_written_pass(tmp_path, monkeypatch):
    ferry = module()
    _, _, members, _ = saved_capsule(tmp_path)

    def reject(*args, **kwargs): raise ValueError('native membership differs')

    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', reject)
    with pytest.raises(ValueError, match='native membership differs'):
        ferry._replay_saved_context(members, tmp_path/'parent', tmp_path/'saved')


def test_saved_replay_does_not_overwrite_existing_user_destination(tmp_path):
    ferry = module()
    _, _, members, _ = saved_capsule(tmp_path)
    existing = tmp_path/'existing'
    existing.mkdir()
    sentinel = existing/'keep.txt'
    sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError): ferry._replay_saved_context(members, tmp_path/'parent', existing)
    assert list(existing.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'KEEP USER DATA'


def test_saved_parent_never_uses_an_old_prefix_when_exact_lineage_is_missing(tmp_path):
    ferry = module()
    _, _, members, _ = saved_capsule(tmp_path)
    members = {name: data for name, data in members.items() if not name.startswith(PREFIX)}
    with pytest.raises(ValueError): ferry._materialize_parent(members, tmp_path/'missing-parent')


def test_saved_and_inspect_flags_are_mutually_exclusive_before_runtime_or_archive(tmp_path, monkeypatch):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('conflicting modes read runtime'))
    monkeypatch.setattr('sys.argv', ['saved-context', '--review-zip', str(tmp_path/'absent.zip'),
        '--saved-native-only', '--inspect-only'])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


def test_saved_mode_preserves_original_failure_and_completed_artifacts_without_sdk(tmp_path, monkeypatch, capsys):
    import nasolve
    import restraints
    ferry = module()
    path, digest, original_members, report = saved_capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '88_Cedar'})
    monkeypatch.setattr(ferry, 'SAVED_REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    views = []

    def read(output, *, linked_parent_directory):
        output, parent = Path(output), Path(linked_parent_directory)
        views.extend([output, parent])
        assert not parent.is_relative_to(tmp_path/'outputs')
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        assert (output/'mixed_context.json').read_bytes() == original_members['mixed_context/mixed_context.json']
        assert (output/'qualification.json').read_bytes() == original_members['mixed_context/qualification.json']
        return report

    def forbidden(*args, **kwargs): pytest.fail('saved mode attempted SDK discovery, audit or process execution')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_context.audit_mixed_context', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', read)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    monkeypatch.setattr('sys.argv', ['saved-context', '--review-zip', str(path), '--saved-native-only',
        '--phenix-root', str(tmp_path/'NO_SDK'), '--output-parent', str(outputs)])
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and not captured.err
    assert views and all(not p.exists() for p in views)
    archive = next(outputs.glob('*/*_review.zip'))
    with ZipFile(archive) as returned_zip:
        returned = {name: returned_zip.read(name) for name in returned_zip.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert receipt['parent_review']['sha256'] == digest
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert 'phenix' not in receipt
    assert all(returned['inputs/review/'+name] == data for name, data in original_members.items())
    assert path.read_bytes() == original_zip
    assert not any(name.startswith('mixed_context/') for name in returned)
    summary = json.loads(returned['saved_mixed_context.json'])
    assert summary['status'] == 'MIXED_CONTEXT_MECHANICS_PASS'
    assert summary['new_native_calls'] == 0 and summary['saved_native_calls'] == 2
    assert summary['requires_cif_review'] is False and summary['automatic_adoption'] is False
    references = []

    def collect(value):
        if isinstance(value, dict):
            if value.get('anchor') == 'parent_review': references.append(value)
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)

    collect(summary)
    for logical in ['mixed_context/mixed_context.json', 'mixed_context/qualification.json']:
        expected = {'anchor': 'parent_review', 'path': logical,
            'sha256': sha256(original_members[logical]).hexdigest(), 'size': len(original_members[logical])}
        assert expected in references
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())


@pytest.mark.parametrize('lineage', ['C85', 'C86'])
def test_saved_mode_rejects_earlier_capsules_before_any_sdk_or_audit(tmp_path, monkeypatch, capsys, lineage):
    import nasolve
    import restraints
    from tests.test_mixed_context_probe import capsule
    from tests.test_mixed_context_retry_probe import retry_capsule
    ferry = module()
    if lineage == 'C85':
        path, digest, _ = capsule(tmp_path)
        constant = 'REVIEW_SHA256'
    else:
        path, digest, _, _ = retry_capsule(tmp_path)
        constant = 'RETRY_REVIEW_SHA256'
    monkeypatch.setattr(ferry, constant, digest)
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '88_Cedar'})
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    def forbidden(*args, **kwargs): pytest.fail('old capsule saved mode attempted SDK or audit')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_context.audit_mixed_context', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    monkeypatch.setattr('sys.argv', ['saved-context', '--review-zip', str(path), '--saved-native-only',
        '--phenix-root', str(tmp_path/'NO_SDK'), '--output-parent', str(outputs)])
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and 'C87' in captured.err
    archive = next(outputs.glob('*/*_review.zip'))
    with ZipFile(archive) as returned:
        receipt = json.loads(returned.read('probe_receipt.json'))
        assert 'saved_mixed_context.json' not in returned.namelist()
    assert receipt['analysis_completed'] is False
    assert 'phenix' not in receipt
