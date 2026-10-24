"""Exact saved-parent transport and source-removed mixed-context ferry controls."""
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
        'mixed_context_ferry', ROOT/'scripts/mixed_context_probe_template.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def capsule(tmp_path, defect='none'):
    """Artificial envelope; bound scientific inputs are checked by maintained APIs."""
    summary = {'schema_version': 1, 'policy_id': 'cif-saved-mixed-linked-recovery-v1',
        'status': 'REVIEW', 'targets': ['Q17'], 'saved_native_calls': 2, 'new_native_calls': 0,
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES',
            'selected': 'verified_constructed_model', 'native_usable': 'NOT_YET_QUALIFIED'},
        'automatic_adoption': False, 'requires_cif_review': False}
    if defect == 'policy': summary['policy_id'] = 'UNTRUSTED_POLICY'
    elif defect == 'saved_count': summary['saved_native_calls'] = 1
    elif defect == 'new_count': summary['new_native_calls'] = 1
    elif defect == 'status': summary['status'] = 'PREPARED_ONLY'
    data = json.dumps(summary).encode()
    reference = {'anchor': 'probe_directory', 'path': 'saved_linked_recovery.json',
        'sha256': sha256(data).hexdigest(), 'size': len(data)}
    header = {'kind': 'mixed-linked-recovery-probe', 'delivery_prefix': '85_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'saved_linked_recovery': {'artifact': reference, 'status': 'REVIEW',
            'saved_native_calls': 2, 'new_native_calls': 0}}
    if defect == 'kind': header['kind'] = 'UNTRUSTED_KIND'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'artifact_hash': reference['sha256'] = '0'*64
    elif defect == 'artifact_size': reference['size'] += 1
    elif defect == 'artifact_anchor': reference['anchor'] = 'unbound_absolute_location'
    elif defect == 'artifact_path': reference['path'] = '../outside'
    members = {'probe_receipt.json': json.dumps(header).encode(),
        'saved_linked_recovery.json': data,
        'inputs/review/mixed_linked_recovery/mixed_linked_recovery.json': b'{"opaque_scientific_parent":true}\n',
        'inputs/review/mixed_linked_recovery/inputs/model.pdb': b'EXACT SCIENTIFIC DATA\n',
        'inputs/review/mixed_linked_recovery/native/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/inputs/review/private-parent.json': b'{"opaque_nested_parent":true}\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['inputs/review/large_report.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['inputs/review/oversize.json'] = b' '*(33*1024*1024)
    elif defect == 'entries': members.update({f'inputs/review/extra/{i:04d}.txt': b'x' for i in range(1024)})
    manifest = {name: {'sha256': sha256(value).hexdigest(), 'bytes': len(value)}
                for name, value in members.items()}
    if defect == 'hash': manifest['saved_linked_recovery.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop('saved_linked_recovery.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, value in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, value)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'saved.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members


@pytest.mark.parametrize('defect', ['none', 'large', 'kind', 'prefix', 'incomplete',
    'policy', 'saved_count', 'new_count', 'status', 'artifact_hash', 'artifact_size',
    'artifact_anchor', 'artifact_path', 'path', 'hash', 'inventory', 'symlink',
    'duplicate', 'archive', 'oversize', 'entries'])
def test_exact_completed_replay_envelope_and_archive_bounds(tmp_path, defect):
    ferry = module()
    path, digest, members = capsule(tmp_path, defect)
    ferry.REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    if defect in {'none', 'large'}:
        actual = ferry._read_capsule(path)
        assert {name: actual[name] for name in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert not (tmp_path/'outside').exists()


def test_only_declared_shallow_scientific_subtree_is_materialized(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'owned-parent'
    ferry._materialize_parent(members, destination)
    prefix = 'inputs/review/mixed_linked_recovery/'
    expected = {name[len(prefix):]: value for name, value in members.items() if name.startswith(prefix)}
    actual = {path.relative_to(destination).as_posix(): path.read_bytes()
              for path in destination.rglob('*') if path.is_file()}
    assert actual == expected
    assert actual['native/captured.py'].startswith(b'raise RuntimeError')
    assert not (destination/'probe_receipt.json').exists()
    assert not (destination/'inputs/review/private-parent.json').exists()


def test_parent_view_refuses_existing_destination(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'existing'
    destination.mkdir()
    sentinel = destination/'preserved.txt'
    sentinel.write_bytes(b'KEEP EXISTING USER DATA')
    with pytest.raises(FileExistsError): ferry._materialize_parent(members, destination)
    assert sentinel.read_bytes() == b'KEEP EXISTING USER DATA'
    assert list(destination.iterdir()) == [sentinel]


@pytest.mark.parametrize('timeout', ['0', '61'])
def test_invalid_native_deadline_stops_before_runtime_or_inputs(tmp_path, monkeypatch, capsys, timeout):
    ferry = module()
    monkeypatch.setattr('sys.argv', ['context-probe', '--review-zip', str(tmp_path/'not-read.zip'),
        '--timeout-seconds', timeout])
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('invalid deadline read runtime'))
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2
    assert '60' in capsys.readouterr().err


def test_inspect_main_uses_temporary_parent_and_preserves_capsule_without_sdk(tmp_path, monkeypatch, capsys):
    """Artificial runtime API fixture; real transport/publication/main stay active."""
    import nasolve
    import restraints
    ferry = module()
    path, digest, original_members = capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '86_Cedar'})
    monkeypatch.setattr(ferry, 'REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    observed = []
    result = {'schema_version': 1, 'status': 'PREPARED_ONLY', 'targets': ['Q17'],
        'new_native_calls': 0}

    def audit(parent, phenix, output, *, timeout_seconds=60):
        parent, output = Path(parent), Path(output)
        observed.append(parent)
        assert phenix is None and timeout_seconds == 60
        assert not parent.is_relative_to(output.parent)
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC DATA\n'
        assert (parent/'native/captured.py').read_bytes().startswith(b'raise RuntimeError')
        output.mkdir()
        (output/'mixed_context.json').write_text(json.dumps(result))
        return result

    def read(output, *, linked_parent_directory):
        parent = Path(linked_parent_directory)
        assert parent in observed and parent.is_dir()
        assert json.loads((Path(output)/'mixed_context.json').read_bytes()) == result
        return result

    def forbidden(*args, **kwargs): pytest.fail('inspect main attempted SDK discovery or execution')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', forbidden)
    monkeypatch.setattr('nasolve.cif_mixed_context.audit_mixed_context', audit)
    monkeypatch.setattr('nasolve.cif_mixed_context.read_mixed_context', read)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    output = tmp_path/'outputs'
    monkeypatch.setattr('sys.argv', ['context-probe', '--review-zip', str(path), '--inspect-only',
        '--phenix-root', str(tmp_path/'NO_SDK'), '--output-parent', str(output)])
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and not captured.err
    assert observed and all(not parent.exists() for parent in observed)
    archive = next(output.glob('*/*_review.zip'))
    with ZipFile(archive) as capsule_zip:
        returned = {name: capsule_zip.read(name) for name in capsule_zip.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert 'phenix' not in receipt
    assert receipt['mixed_context']['new_native_calls'] == 0
    assert receipt['mixed_context']['targets'] == ['Q17']
    assert receipt['mixed_context']['status'] == 'PREPARED_ONLY'
    assert all(returned['inputs/review/'+name] == data for name, data in original_members.items())
    assert path.read_bytes() == original_zip
    assert not any(name.startswith('mixed_context/inputs/parent/') for name in returned)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())


def test_built_context_ferry_relocates_without_sources_and_keeps_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_context_probe_template.py']:
        path = source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source)
    _initialize_git(nar)
    spec = importlib.util.spec_from_file_location('context_builder', ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    runner = tmp_path/'relocated/86_Cedar_probe_mixed_context.py'
    metadata = builder.build(source, nar, runner, template_name='mixed_context_probe_template.py')
    assert metadata['kind'] == 'mixed-context-shuttle' and metadata['delivery_prefix'] == '86_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any('review.zip' in name for name in metadata['runtime_files'])
    shutil.rmtree(source)
    shutil.rmtree(nar)
    result = subprocess.run([sys.executable, '-B', str(runner), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert all(name in result.stdout for name in ['--review-zip', '--inspect-only', '--timeout-seconds', '--phenix-root'])
    configuration = tmp_path/'config.json'
    original = b'{"workspace":{"run":"PRESERVE"}}\n'
    configuration.write_bytes(original)
    poison = tmp_path/'poison'
    for package in ['nasolve', 'restraints']:
        path = poison/package
        path.mkdir(parents=True)
        (path/'__init__.py').write_text('raise RuntimeError("AMBIENT_IMPORT")\n')
    guard = tmp_path/'guard.py'
    guard.write_text('import runpy,subprocess,sys\ndef forbidden(*a,**k):raise AssertionError("NO_SDK")\nsubprocess.Popen=forbidden\np=sys.argv.pop(1)\nrunpy.run_path(p,run_name="__main__")\n')
    bad = tmp_path/'bad.zip'
    bad.write_bytes(b'NOT A VERIFIED RETURN')
    result = subprocess.run([sys.executable, '-B', str(guard), str(runner), '--inspect-only',
        '--review-zip', str(bad), '--output-parent', str(tmp_path/'outputs')],
        capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(poison),
            'PYTHONDONTWRITEBYTECODE': '1', 'NASOLVE_CONFIG_FILE': str(configuration)})
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout and 'exact verified C85' in result.stderr
    assert 'AMBIENT_IMPORT' not in result.stderr and 'NO_SDK' not in result.stderr
    assert configuration.read_bytes() == original
    archive = next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as captured:
        returned = {name: captured.read(name) for name in captured.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert not receipt['analysis_completed'] and not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['captured_code_execution'] == 'NOT_RUN' and receipt['production_checkpoint'] == 'NOT_CREATED'
    assert not any(name.startswith('runtime/') for name in returned)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())
