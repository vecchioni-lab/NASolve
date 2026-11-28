"""Initial-only native gradient ferry, pinned inputs and opaque history."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).parents[1]
CONTEXT = 'inputs/review/mixed_context/'
PARENT = 'inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'


def module():
    spec = importlib.util.spec_from_file_location('mixed_gradient_ferry', ROOT/'scripts/mixed_gradient_probe_template.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def capsule(tmp_path, defect='none'):
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-linked-context-v2',
        'status': 'MIXED_CONTEXT_MECHANICS_PASS', 'targets': ['Q17'], 'new_native_calls': 2}
    qdata = b'{"status":"MIXED_CONTEXT_MECHANICS_PASS","mechanics_checks_pass":true}\n'
    rdata = json.dumps(report).encode()
    summary = {'schema_version': 1, 'policy_id': 'cif-saved-mixed-context-v1',
        'context_policy_id': 'cif-mixed-linked-context-v2', 'status': 'MIXED_CONTEXT_MECHANICS_PASS',
        'targets': ['Q17'], 'saved_native_calls': 2, 'new_native_calls': 0,
        'automatic_adoption': False, 'requires_cif_review': False,
        'scientific_qualification': 'NOT_ASSESSED',
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'verified_constructed_model',
            'native_usable': True, 'automatic_adoption': False, 'requires_cif_review': False},
        'original_report': {'anchor': 'parent_review', 'path': 'mixed_context/mixed_context.json',
            'sha256': sha256(rdata).hexdigest(), 'size': len(rdata)},
        'qualification': {'anchor': 'parent_review', 'path': 'mixed_context/qualification.json',
            'sha256': sha256(qdata).hexdigest(), 'size': len(qdata)}}
    if defect == 'policy': summary['policy_id'] = 'OTHER'
    elif defect == 'context_policy': summary['context_policy_id'] = 'OTHER'
    elif defect == 'status': summary['status'] = 'REVIEW'
    elif defect == 'saved_count': summary['saved_native_calls'] = 1
    elif defect == 'new_count': summary['new_native_calls'] = 1
    elif defect == 'new_count_bool': summary['new_native_calls'] = False
    elif defect == 'report_hash': summary['original_report']['sha256'] = '0'*64
    elif defect == 'report_path': summary['original_report']['path'] = '../outside'
    elif defect == 'report_anchor': summary['original_report']['anchor'] = 'unbound_location'
    elif defect == 'qualification_hash': summary['qualification']['sha256'] = '0'*64
    elif defect == 'qualification_size': summary['qualification']['size'] += 1
    elif defect == 'adoption': summary['automatic_adoption'] = True
    sdata = json.dumps(summary).encode()
    reference = {'artifact': {'anchor': 'probe_directory', 'path': 'saved_mixed_context.json',
        'sha256': sha256(sdata).hexdigest(), 'size': len(sdata)},
        'status': 'MIXED_CONTEXT_MECHANICS_PASS', 'saved_native_calls': 2, 'new_native_calls': 0}
    header = {'schema_version': 1, 'kind': 'mixed-context-probe', 'delivery_prefix': '88_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'saved_mixed_context': reference}
    if defect == 'kind': header['kind'] = 'OTHER'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'approval': header['requires_cif_review'] = True
    elif defect == 'summary_hash': reference['artifact']['sha256'] = '0'*64
    elif defect == 'summary_size': reference['artifact']['size'] += 1
    elif defect == 'summary_path': reference['artifact']['path'] = '../outside'
    elif defect == 'summary_anchor': reference['artifact']['anchor'] = 'unbound_location'
    members = {'probe_receipt.json': json.dumps(header).encode(), 'saved_mixed_context.json': sdata,
        CONTEXT+'mixed_context.json': rdata, CONTEXT+'qualification.json': qdata,
        CONTEXT+'native/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        PARENT+'mixed_linked_recovery.json': b'{"opaque_parent":true}\n',
        PARENT+'inputs/model.pdb': b'EXACT SCIENTIFIC MODEL\n',
        PARENT+'native/captured.py': b'raise RuntimeError("PARENT_CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/inputs/review/inputs/review/mixed_linked_recovery/mixed_linked_recovery.json': b'DECOY_PARENT\n',
        'mixed_context/mixed_context.json': b'DECOY_CONTEXT\n',
        'unrelated/model.pdb': b'DECOY_BASENAME\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['inputs/review/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['inputs/review/oversize.json'] = b' '*(33*1024*1024)
    elif defect == 'entries': members.update({f'inputs/review/extra/{i:04d}.txt': b'x' for i in range(1024)})
    manifest = {name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)} for name, data in members.items()}
    if defect == 'hash': manifest['saved_mixed_context.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop('saved_mixed_context.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'context-pass.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members


def test_verified_saved_native_context_is_accepted_without_running_captured_programs(tmp_path):
    ferry = module()
    path, digest, members = capsule(tmp_path)
    ferry.REVIEW_SHA256 = digest
    actual = ferry._read_capsule(path)
    assert {name: actual[name] for name in members} == members


@pytest.mark.parametrize('defect', ['large', 'kind', 'prefix', 'incomplete', 'approval',
    'policy', 'context_policy', 'status', 'saved_count', 'new_count', 'new_count_bool',
    'report_hash', 'report_path', 'report_anchor', 'qualification_hash', 'qualification_size',
    'adoption', 'summary_hash', 'summary_size', 'summary_path', 'summary_anchor',
    'path', 'hash', 'inventory', 'symlink', 'duplicate', 'archive', 'oversize', 'entries'])
def test_gradient_parent_envelope_and_portable_artifact_bindings_are_strict(tmp_path, defect):
    ferry = module()
    path, digest, members = capsule(tmp_path, defect)
    ferry.REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    original = path.read_bytes()
    if defect == 'large':
        actual = ferry._read_capsule(path)
        assert {name: actual[name] for name in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original
    assert not (tmp_path/'outside').exists()


def test_gradient_inputs_use_only_the_two_declared_shallow_views(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'inputs'
    context, parent = ferry._materialize_inputs(members, destination)
    assert (Path(context), Path(parent)) == (destination/'context', destination/'linked_parent')
    for prefix, view in [(CONTEXT, context), (PARENT, parent)]:
        expected = {n[len(prefix):]: d for n, d in members.items() if n.startswith(prefix)}
        actual = {p.relative_to(view).as_posix(): p.read_bytes() for p in Path(view).rglob('*') if p.is_file()}
        assert actual == expected


def test_gradient_input_views_refuse_existing_user_directory(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'existing'
    destination.mkdir()
    sentinel = destination/'keep.txt'
    sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError): ferry._materialize_inputs(members, destination)
    assert sentinel.read_bytes() == b'KEEP USER DATA'
    assert list(destination.iterdir()) == [sentinel]


@pytest.mark.parametrize('missing', [CONTEXT, PARENT])
def test_missing_declared_view_never_uses_a_matching_basename_or_older_prefix(tmp_path, missing):
    ferry = module()
    _, _, members = capsule(tmp_path)
    members = {n: d for n, d in members.items() if not n.startswith(missing)}
    with pytest.raises(ValueError): ferry._materialize_inputs(members, tmp_path/'missing-view')


@pytest.mark.parametrize('timeout', ['0', '601'])
def test_bad_initial_audit_deadline_stops_before_runtime_or_archive(tmp_path, monkeypatch, timeout):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('invalid deadline read runtime'))
    monkeypatch.setattr('sys.argv', ['gradient-probe', '--review-zip', str(tmp_path/'absent.zip'),
        '--timeout-seconds', timeout])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


@pytest.mark.parametrize('inspect_only,seconds', [(True, None), (False, None), (True, 1), (False, 600)])
def test_initial_gradient_main_uses_explicit_views_once_and_preserves_the_exact_parent(tmp_path, monkeypatch, capsys, inspect_only, seconds):
    import nasolve
    import restraints
    from types import SimpleNamespace
    ferry = module()
    path, digest, original_members = capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '89_Cedar'})
    monkeypatch.setattr(ferry, 'REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime_members)

    def isolated_fixture(runtime, session, members):
        for name, data in members.items(): ferry._write(runtime/name, data)
        monkeypatch.setattr(nasolve, '__file__', str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(runtime/'restraints/__init__.py'))

    selected_executable = tmp_path/'selected-sdk/bin/phenix.python'
    selected_executable.parent.mkdir(parents=True)
    selected_executable.write_bytes(b'OWNED FAKE SDK; NEVER EXECUTED\n')
    sdk = SimpleNamespace(version='2.2.1', root=tmp_path/'selected-sdk', source='explicit',
        executables={'phenix.python': selected_executable}, environment={})
    discoveries, events, views = [], [], []
    result = {'schema_version': 1, 'policy_id': 'cif-mixed-initial-native-gradient-v1',
        'status': 'PREPARED_ONLY' if inspect_only else 'REVIEW', 'targets': ['Q17'],
        'new_native_calls': 0 if inspect_only else 1}

    def discovery(config, *, explicit, environ):
        assert not inspect_only
        assert Path(explicit) == sdk.root
        discoveries.append(explicit)
        return sdk

    def audit(context, parent, phenix, output, *, timeout_seconds=600):
        assert not events and timeout_seconds == (600 if seconds is None else seconds)
        assert phenix is (None if inspect_only else sdk)
        context, parent, output = Path(context), Path(parent), Path(output)
        assert (context/'mixed_context.json').read_bytes() == original_members[CONTEXT+'mixed_context.json']
        assert (context/'qualification.json').read_bytes() == original_members[CONTEXT+'qualification.json']
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        assert not context.is_relative_to(output.parent) and not parent.is_relative_to(output.parent)
        assert (context/'native/captured.py').read_bytes().startswith(b'raise RuntimeError')
        views.extend([context, parent])
        events.append('audit')
        output.mkdir()
        (output/'mixed_initial_gradients.json').write_text(json.dumps(result))
        return result

    def read(output, *, context_directory, linked_parent_directory):
        assert events == ['audit']
        assert Path(context_directory) == views[0] and Path(linked_parent_directory) == views[1]
        assert all(p.is_dir() for p in views)
        assert json.loads((Path(output)/'mixed_initial_gradients.json').read_bytes()) == result
        events.append('reader')
        return result

    def forbidden(*args, **kwargs): pytest.fail('initial ferry executed a subprocess or optimizer')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.config.load_config', lambda: {})
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', discovery)
    monkeypatch.setattr('nasolve.cif_mixed_gradient.audit_mixed_initial_gradients', audit)
    monkeypatch.setattr('nasolve.cif_mixed_gradient.read_mixed_initial_gradients', read)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    argv = ['gradient-probe', '--review-zip', str(path), '--phenix-root', str(sdk.root),
        '--output-parent', str(outputs)]
    if inspect_only: argv.append('--inspect-only')
    if seconds is not None: argv.extend(['--timeout-seconds', str(seconds)])
    monkeypatch.setattr('sys.argv', argv)
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and not captured.err
    assert events == ['audit', 'reader']
    assert len(discoveries) == (0 if inspect_only else 1)
    assert all(not p.exists() for p in views)
    archive = next(outputs.glob('*/*_review.zip'))
    with ZipFile(archive) as capsule_zip:
        returned = {n: capsule_zip.read(n) for n in capsule_zip.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert receipt['parent_review']['sha256'] == digest
    assert receipt['mixed_gradient']['new_native_calls'] == result['new_native_calls']
    assert receipt['mixed_gradient']['status'] == result['status']
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['model_optimization_requested'] is False
    assert ('phenix' not in receipt) is inspect_only
    assert all(returned['inputs/review/'+n] == d for n, d in original_members.items())
    assert path.read_bytes() == original_zip
    assert not any(n.startswith('mixed_gradient/inputs/parent/') for n in returned)
    directory = receipt['mixed_gradient']['directory']
    assert directory['anchor'] == 'probe_directory'
    rdata = returned[directory['path']+'/mixed_initial_gradients.json']
    assert receipt['mixed_gradient']['report_sha256'] == sha256(rdata).hexdigest()
    assert receipt['mixed_gradient']['report_size'] == len(rdata)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[n]), 'sha256': sha256(returned[n]).hexdigest()}
               for n, ref in manifest.items())


def test_gradient_ferry_build_relocates_without_sources_and_preserves_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_gradient_probe_template.py']:
        path = source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source)
    _initialize_git(nar)
    spec = importlib.util.spec_from_file_location('gradient_builder', ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    runner = tmp_path/'relocated/89_Cedar_probe_mixed_gradient.py'
    metadata = builder.build(source, nar, runner, template_name='mixed_gradient_probe_template.py')
    assert metadata['kind'] == 'mixed-gradient-shuttle' and metadata['delivery_prefix'] == '89_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any(name.endswith('.zip') for name in metadata['runtime_files'])
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
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout and 'C88' in result.stderr
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


@pytest.mark.parametrize('bound', ['single_member', 'entries', 'total_including_manifest'])
def test_review_output_never_writes_a_capsule_outside_its_unchanged_reader_bounds(tmp_path, monkeypatch, bound):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '89_Cedar'}
    session = tmp_path/'89_Cedar_mixed-gradient-owned'
    session.mkdir()
    if bound == 'single_member':
        files = {'scientific/oversized.bin': b'x'*(33*1024*1024)}
    elif bound == 'entries':
        files = {f'scientific/{i:04d}.bin': b'x' for i in range(1024)}
    else:
        # Aliased immutable payloads exercise the real byte total cheaply.
        # Payloads alone exactly fit; their required manifest must also fit.
        payload = b'x'*(32*1024*1024)
        files = {f'scientific/{i}.bin': payload for i in range(4)}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    with pytest.raises(ValueError, match='archive bounds'): ferry._review_zip(session)
    assert not list(session.glob('*.zip'))


def test_oversized_output_keeps_the_first_error_and_scientific_session_in_a_bounded_failure_capsule(tmp_path, monkeypatch):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '89_Cedar'}
    session = tmp_path/'89_Cedar_mixed-gradient-owned'
    scientific = session/'mixed_gradient/native.json'
    scientific.parent.mkdir(parents=True)
    original = b'COMPLETED SCIENTIFIC CAPTURE MUST REMAIN AVAILABLE\n'
    scientific.write_bytes(original)
    files = {'scientific/oversized.bin': b'x'*(33*1024*1024),
        'mixed_gradient/native.json': original}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    receipt = {'schema_version': 1, 'analysis_completed': True,
        'automatic_adoption': False, 'requires_cif_review': False}
    archive = ferry._report_failure(session, receipt, ValueError('first native evidence failure'))
    assert archive.name.endswith('_failure_review.zip')
    assert scientific.read_bytes() == original
    assert list(session.glob('*.zip')) == [archive]
    with ZipFile(archive) as captured:
        assert set(captured.namelist()) == {'probe_receipt.json', 'manifest.json'}
        data = captured.read('probe_receipt.json')
        result = json.loads(data)
        manifest = json.loads(captured.read('manifest.json'))
    assert result['analysis_completed'] is False
    assert result['error_type'] == 'ValueError' and result['error'] == 'first native evidence failure'
    assert 'archive bounds' in result['archive_collection_error']
    assert result['failure_archive_scope'] == 'RECEIPT_ONLY; OTHER_OUTPUTS_REMAIN_IN_SESSION'
    assert manifest == {'probe_receipt.json': {'bytes': len(data), 'sha256': sha256(data).hexdigest()}}
