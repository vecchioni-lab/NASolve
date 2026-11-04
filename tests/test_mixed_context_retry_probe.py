"""Preserve the failed context return while retrying the native CIF grammar."""
from hashlib import sha256
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from tests.test_mixed_context_probe import module


PREFIX = 'inputs/review/inputs/review/mixed_linked_recovery/'


def retry_capsule(tmp_path, defect='none'):
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-linked-context-v1',
        'status': 'REVIEW', 'targets': ['Q17'], 'new_native_calls': 1,
        'saved_native_calls': 2, 'maximum_native_calls': 2,
        'automatic_adoption': False, 'requires_cif_review': False,
        'native_active': {'status': 'NOT_RUN'},
        'qualification': {'status': 'NOT_RUN'}}
    if defect == 'policy': report['policy_id'] = 'UNTRUSTED_POLICY'
    elif defect == 'status': report['status'] = 'MIXED_CONTEXT_MECHANICS_PASS'
    elif defect == 'calls': report['new_native_calls'] = 2
    elif defect == 'calls_bool': report['new_native_calls'] = True
    elif defect == 'schema': report['schema_version'] = 2
    elif defect == 'adoption': report['automatic_adoption'] = True
    data = json.dumps(report).encode()
    context = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_context'},
        'report_sha256': sha256(data).hexdigest(), 'report_size': len(data),
        'status': report['status'], 'targets': ['Q17'], 'new_native_calls': report['new_native_calls']}
    header = {'schema_version': 1, 'kind': 'mixed-context-probe',
        'delivery_prefix': '86_Cedar', 'analysis_completed': True,
        'automatic_adoption': False, 'requires_cif_review': False,
        'mixed_context': context}
    if defect == 'kind': header['kind'] = 'UNTRUSTED_KIND'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'approval': header['requires_cif_review'] = True
    elif defect == 'artifact_hash': context['report_sha256'] = '0'*64
    elif defect == 'artifact_size': context['report_size'] += 1
    elif defect == 'artifact_anchor': context['directory']['anchor'] = 'unbound_location'
    elif defect == 'artifact_path': context['directory']['path'] = '../outside'
    elif defect == 'receipt_calls': context['new_native_calls'] = 0
    elif defect == 'receipt_targets': context['targets'] = ['OTHER']
    members = {'probe_receipt.json': json.dumps(header).encode(),
        'mixed_context/mixed_context.json': data,
        'mixed_context/native/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        'mixed_context/native/failed.json': b'{"status":"FAILED","error":"native scalar modifier"}\n',
        PREFIX+'mixed_linked_recovery.json': b'{"opaque_scientific_parent":true}\n',
        PREFIX+'inputs/model.pdb': b'EXACT SCIENTIFIC MODEL\n',
        PREFIX+'native/captured.py': b'raise RuntimeError("PARENT_CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/mixed_linked_recovery/mixed_linked_recovery.json': b'DECOY_OLD_PREFIX\n',
        'unrelated/model.pdb': b'DECOY_BASENAME\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['inputs/review/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['inputs/review/oversize.json'] = b' '*(33*1024*1024)
    manifest = {name: {'sha256': sha256(value).hexdigest(), 'bytes': len(value)}
                for name, value in members.items()}
    if defect == 'hash': manifest['mixed_context/mixed_context.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop('mixed_context/mixed_context.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, value in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, value)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'context-return.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members, report


def test_exact_failed_context_return_is_accepted_without_executing_its_programs(tmp_path):
    ferry = module()
    path, digest, members, _ = retry_capsule(tmp_path)
    ferry.RETRY_REVIEW_SHA256 = digest
    with ZipFile(path) as archive:
        expected = {**members, 'manifest.json': archive.read('manifest.json')}
    assert ferry._read_capsule(path) == expected


@pytest.mark.parametrize('defect', ['large', 'kind', 'prefix', 'incomplete', 'approval',
    'policy', 'status', 'calls', 'calls_bool', 'schema', 'adoption', 'artifact_hash',
    'artifact_size', 'artifact_anchor', 'artifact_path', 'receipt_calls', 'receipt_targets',
    'path', 'hash', 'inventory', 'symlink', 'duplicate', 'archive', 'oversize'])
def test_retry_envelope_and_archive_checks_keep_the_failed_result_exact(tmp_path, defect):
    ferry = module()
    path, digest, members, _ = retry_capsule(tmp_path, defect)
    ferry.RETRY_REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    original = path.read_bytes()
    if defect == 'large':
        actual = ferry._read_capsule(path)
        assert {name: actual[name] for name in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original
    assert not (tmp_path/'outside').exists()


def test_retry_parent_uses_declared_c86_prefix_instead_of_old_prefix_or_basename(tmp_path):
    ferry = module()
    _, _, members, _ = retry_capsule(tmp_path)
    destination = tmp_path/'parent'
    ferry._materialize_parent(members, destination)
    expected = {name[len(PREFIX):]: data for name, data in members.items() if name.startswith(PREFIX)}
    actual = {p.relative_to(destination).as_posix(): p.read_bytes()
              for p in destination.rglob('*') if p.is_file()}
    assert actual == expected


def test_saved_context_uses_maintained_reader_and_explicit_parent_outside_new_result(tmp_path, monkeypatch):
    ferry = module()
    _, _, members, report = retry_capsule(tmp_path)
    parent = tmp_path/'parent'
    parent.mkdir()
    destination = tmp_path/'saved-context'
    observed = []

    def read(directory, *, linked_parent_directory):
        observed.append((Path(directory), Path(linked_parent_directory)))
        assert Path(linked_parent_directory) == parent
        assert json.loads((Path(directory)/'mixed_context.json').read_bytes()) == report
        assert (Path(directory)/'native/failed.json').read_bytes() == members['mixed_context/native/failed.json']
        assert (Path(directory)/'native/captured.py').read_bytes().startswith(b'raise RuntimeError')
        return report

    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', read)
    result = ferry._verify_previous_context(members, parent, destination)
    assert observed == [(destination, parent)]
    assert result is not None
    assert not (destination/'inputs').exists()
    assert not (destination/'probe_receipt.json').exists()


def test_saved_context_never_overwrites_an_existing_destination(tmp_path):
    ferry = module()
    _, _, members, _ = retry_capsule(tmp_path)
    destination = tmp_path/'existing'
    destination.mkdir()
    sentinel = destination/'keep.txt'
    sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError):
        ferry._verify_previous_context(members, tmp_path/'parent', destination)
    assert sentinel.read_bytes() == b'KEEP USER DATA'
    assert list(destination.iterdir()) == [sentinel]


def test_retry_parent_never_falls_back_to_a_matching_basename_or_older_prefix(tmp_path):
    ferry = module()
    _, _, members, _ = retry_capsule(tmp_path)
    members = {name: data for name, data in members.items() if not name.startswith(PREFIX)}
    with pytest.raises(ValueError): ferry._materialize_parent(members, tmp_path/'missing-parent')


def test_saved_context_reader_rejection_is_not_replaced_by_report_status(tmp_path, monkeypatch):
    ferry = module()
    _, _, members, _ = retry_capsule(tmp_path)

    def reject(*args, **kwargs): raise ValueError('bound native evidence differs')

    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', reject)
    with pytest.raises(ValueError, match='bound native evidence differs'):
        ferry._verify_previous_context(members, tmp_path/'parent', tmp_path/'saved')


def test_inspect_retry_replays_failed_context_before_audit_and_preserves_every_parent_byte(tmp_path, monkeypatch, capsys):
    import nasolve
    import restraints
    ferry = module()
    path, digest, original_members, previous = retry_capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '87_Cedar'})
    monkeypatch.setattr(ferry, 'RETRY_REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    events = []
    views = []
    result = {'schema_version': 1, 'policy_id': 'cif-mixed-linked-context-v2',
        'status': 'PREPARED_ONLY', 'targets': ['Q17'], 'new_native_calls': 0}

    def read(output, *, linked_parent_directory):
        output, parent = Path(output), Path(linked_parent_directory)
        value = json.loads((output/'mixed_context.json').read_bytes())
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        views.extend([output, parent])
        if value == previous:
            assert not events
            assert (output/'native/failed.json').read_bytes() == original_members['mixed_context/native/failed.json']
            events.append('previous-reader')
            return previous
        assert value == result and events == ['previous-reader', 'audit']
        events.append('new-reader')
        return result

    def audit(parent, phenix, output, *, timeout_seconds=60):
        assert events == ['previous-reader']
        assert phenix is None and timeout_seconds == 60
        parent, output = Path(parent), Path(output)
        assert not parent.is_relative_to(output.parent)
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        events.append('audit')
        output.mkdir()
        (output/'mixed_context.json').write_text(json.dumps(result))
        return result

    def forbidden(*args, **kwargs): pytest.fail('inspect retry attempted SDK discovery or execution')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_context.audit_mixed_context', audit)
    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', read)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    monkeypatch.setattr('sys.argv', ['context-retry', '--review-zip', str(path), '--inspect-only',
        '--phenix-root', str(tmp_path/'NO_SDK'), '--output-parent', str(outputs)])
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and not captured.err
    assert events == ['previous-reader', 'audit', 'new-reader']
    assert all(not p.exists() for p in views if not p.is_relative_to(outputs))
    archive = next(outputs.glob('*/*_review.zip'))
    with ZipFile(archive) as returned_zip:
        returned = {name: returned_zip.read(name) for name in returned_zip.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert receipt['parent_review']['sha256'] == digest
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['mixed_context']['new_native_calls'] == 0
    assert all(returned['inputs/review/'+name] == data for name, data in original_members.items())
    assert path.read_bytes() == original_zip
    assert not any(name.startswith('mixed_context/inputs/parent/') for name in returned)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())
