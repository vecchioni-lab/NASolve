"""Bounded mixed geometry ferry with a complete opaque parent archive."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).parents[1]
GRADIENT = 'mixed_gradient/'
CONTEXT = 'inputs/review/inputs/review/mixed_context/'
PARENT = 'inputs/review/inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'


def module():
    spec = importlib.util.spec_from_file_location('mixed_geometry_ferry', ROOT/'scripts/mixed_geometry_probe_template.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def capsule(tmp_path, defect='none'):
    qualification = {'policy_id': 'cif-mixed-initial-native-gradient-v1',
        'status': 'MIXED_INITIAL_DERIVATIVES_PASS', 'sampled_derivatives_pass': True,
        'automatic_adoption': False, 'scientific_qualification': 'NOT_ASSESSED',
        'checks': {name: True for name in ['captured_raw_snapshot',
            'complete_both_order_plane_derivatives_and_controls', 'complete_initial_sampled_derivatives',
            'unchanged_native_energy', 'unchanged_static_constraint_signature']}}
    if defect == 'qualification_status': qualification['status'] = 'REVIEW'
    elif defect == 'qualification_verdict': qualification['sampled_derivatives_pass'] = False
    elif defect == 'qualification_check_type': qualification['checks']['captured_raw_snapshot'] = 1
    qdata = json.dumps(qualification).encode()
    qref = {'anchor': 'mixed_initial_gradient_directory', 'path': 'qualification.json',
        'sha256': sha256(qdata).hexdigest(), 'size': len(qdata)}
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-initial-native-gradient-v1',
        'status': 'MIXED_INITIAL_DERIVATIVES_PASS', 'new_native_calls': 1, 'maximum_native_calls': 1,
        'initial_coordinates_only': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'scientific_qualification': 'NOT_ASSESSED', 'policy_authority': 'NARestraints',
        'model_optimization': 'NOT_RUN', 'execution': {'status': 'COMPLETED', 'returncode': 0},
        'qualification': {'artifact': qref},
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'verified_constructed_model',
            'native_usable': True, 'optional_derivative_phase': True,
            'requires_cif_review': False, 'automatic_adoption': False}}
    if defect == 'policy': report['policy_id'] = 'OTHER'
    elif defect == 'status': report['status'] = 'REVIEW'
    elif defect == 'new_count': report['new_native_calls'] = 0
    elif defect == 'new_count_bool': report['new_native_calls'] = True
    elif defect == 'adoption': report['automatic_adoption'] = True
    elif defect == 'optimization': report['model_optimization'] = 'RUN'
    elif defect == 'execution': report['execution']['returncode'] = 2
    elif defect == 'qualification_anchor': qref['anchor'] = 'unbound_location'
    elif defect == 'qualification_path': qref['path'] = '../outside'
    elif defect == 'qualification_hash': qref['sha256'] = '0'*64
    elif defect == 'qualification_size': qref['size'] += 1
    rdata = json.dumps(report).encode()
    reference = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_gradient'},
        'report_sha256': sha256(rdata).hexdigest(), 'report_size': len(rdata),
        'status': 'MIXED_INITIAL_DERIVATIVES_PASS', 'new_native_calls': 1}
    header = {'schema_version': 1, 'kind': 'mixed-gradient-probe', 'delivery_prefix': '89_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'mixed_gradient': reference}
    if defect == 'kind': header['kind'] = 'OTHER'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'approval': header['requires_cif_review'] = True
    elif defect == 'report_hash': reference['report_sha256'] = '0'*64
    elif defect == 'report_size': reference['report_size'] += 1
    elif defect == 'report_path': reference['directory']['path'] = '../outside'
    elif defect == 'report_anchor': reference['directory']['anchor'] = 'unbound_location'
    elif defect == 'envelope_count_bool': reference['new_native_calls'] = True
    members = {'probe_receipt.json': json.dumps(header).encode(),
        GRADIENT+'mixed_initial_gradients.json': rdata, GRADIENT+'qualification.json': qdata,
        GRADIENT+'job/captured.py': b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        CONTEXT+'mixed_context.json': b'{"opaque_context":true}\n',
        CONTEXT+'native/captured.py': b'raise RuntimeError("CONTEXT_CODE_MUST_NOT_RUN")\n',
        PARENT+'mixed_linked_recovery.json': b'{"opaque_parent":true}\n',
        PARENT+'inputs/model.pdb': b'EXACT SCIENTIFIC MODEL\n',
        PARENT+'native/captured.py': b'raise RuntimeError("PARENT_CODE_MUST_NOT_RUN")\n',
        'inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/mixed_linked_recovery.json': b'DECOY_PARENT\n',
        'inputs/review/mixed_context/mixed_context.json': b'DECOY_CONTEXT\n',
        'unrelated/mixed_initial_gradients.json': b'DECOY_GRADIENT\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['inputs/review/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['inputs/review/oversize.json'] = b' '*(33*1024*1024)
    elif defect == 'entries': members.update({f'inputs/review/extra/{i:04d}.txt': b'x' for i in range(1024)})
    manifest = {name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)} for name, data in members.items()}
    if defect == 'hash': manifest[GRADIENT+'qualification.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop(GRADIENT+'qualification.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'gradient-pass.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members


def test_verified_initial_gradient_parent_is_accepted_as_data(tmp_path):
    ferry = module()
    path, digest, members = capsule(tmp_path)
    ferry.REVIEW_SHA256 = digest
    actual = ferry._read_capsule(path)
    assert {name: actual[name] for name in members} == members


def test_geometry_inputs_use_only_three_declared_shallow_views(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'inputs'
    gradient, context, parent = ferry._materialize_inputs(members, destination)
    assert tuple(map(Path, (gradient, context, parent))) == tuple(destination/n for n in ['gradient', 'context', 'linked_parent'])
    for prefix, view in [(GRADIENT, gradient), (CONTEXT, context), (PARENT, parent)]:
        expected = {n[len(prefix):]: d for n, d in members.items() if n.startswith(prefix)}
        actual = {p.relative_to(view).as_posix(): p.read_bytes() for p in Path(view).rglob('*') if p.is_file()}
        assert actual == expected


@pytest.mark.parametrize('timeout', ['0', '601'])
def test_bad_geometry_deadline_stops_before_runtime_or_archive(tmp_path, monkeypatch, timeout):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('invalid deadline read runtime'))
    monkeypatch.setattr('sys.argv', ['geometry-probe', '--review-zip', str(tmp_path/'absent.zip'),
        '--timeout-seconds', timeout])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


@pytest.mark.parametrize('defect', ['large', 'kind', 'prefix', 'incomplete', 'approval',
    'policy', 'status', 'new_count', 'new_count_bool', 'adoption', 'optimization', 'execution',
    'qualification_status', 'qualification_verdict', 'qualification_check_type', 'envelope_count_bool',
    'qualification_anchor', 'qualification_path',
    'qualification_hash', 'qualification_size', 'report_hash', 'report_size', 'report_path', 'report_anchor',
    'path', 'hash', 'inventory', 'symlink', 'duplicate', 'archive', 'oversize', 'entries'])
def test_geometry_parent_bindings_and_capsule_bounds_are_strict(tmp_path, defect):
    ferry = module()
    path, digest, members = capsule(tmp_path, defect)
    ferry.REVIEW_SHA256 = '0'*64 if defect == 'archive' else digest
    original = path.read_bytes()
    if defect == 'large':
        actual = ferry._read_capsule(path)
        assert {n: actual[n] for n in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original
    assert not (tmp_path/'outside').exists()


def test_opaque_parent_must_itself_fit_the_unchanged_outer_member_limit(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    payload = b'x'*(17*1024*1024)
    members.update({'bounded_one.bin': payload, 'bounded_two.bin': payload})
    manifest = {n: {'sha256': sha256(d).hexdigest(), 'bytes': len(d)} for n, d in members.items()}
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items(): archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'too-large-opaque-parent.zip'
    path.write_bytes(raw.getvalue())
    ferry.REVIEW_SHA256 = sha256(raw.getvalue()).hexdigest()
    assert path.stat().st_size > 32*1024*1024
    with pytest.raises(ValueError): ferry._read_capsule(path)


def test_geometry_input_views_refuse_existing_user_directory(tmp_path):
    ferry = module()
    _, _, members = capsule(tmp_path)
    destination = tmp_path/'existing'
    destination.mkdir()
    sentinel = destination/'keep.txt'
    sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError): ferry._materialize_inputs(members, destination)
    assert sentinel.read_bytes() == b'KEEP USER DATA'
    assert list(destination.iterdir()) == [sentinel]


@pytest.mark.parametrize('missing', [GRADIENT, CONTEXT, PARENT])
def test_missing_explicit_gradient_context_or_parent_view_has_no_basename_fallback(tmp_path, missing):
    ferry = module()
    _, _, members = capsule(tmp_path)
    members = {n: d for n, d in members.items() if not n.startswith(missing)}
    with pytest.raises(ValueError): ferry._materialize_inputs(members, tmp_path/'missing-view')


@pytest.mark.parametrize('iterations', ['0', '1001'])
def test_bad_geometry_iteration_budget_stops_before_runtime_or_archive(tmp_path, monkeypatch, iterations):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('invalid iterations read runtime'))
    monkeypatch.setattr('sys.argv', ['geometry-probe', '--review-zip', str(tmp_path/'absent.zip'),
        '--max-iterations', iterations])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


@pytest.mark.parametrize('inspect_only,seconds,iterations',
    [(True, None, None), (False, None, None), (True, 1, 1), (False, 600, 1000)])
def test_geometry_main_uses_three_views_and_preserves_one_exact_opaque_parent(tmp_path, monkeypatch, capsys, inspect_only, seconds, iterations):
    import nasolve
    import restraints
    from types import SimpleNamespace
    ferry = module()
    path, digest, original_members = capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '90_Cedar'})
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
    decision = {'status': 'CONTINUE_WITH_NOTES', 'selected': 'verified_constructed_model',
        'native_usable': True, 'automatic_adoption': False, 'requires_cif_review': False}
    result = {'schema_version': 1, 'policy_id': 'cif-mixed-qualified-geometry-trial-v1',
        'status': 'PREPARED_ONLY' if inspect_only else 'REVIEW',
        'new_native_calls': 0 if inspect_only else 2, 'coordinate_decision': decision}

    def discovery(config, *, explicit, environ):
        assert not inspect_only and Path(explicit) == sdk.root
        discoveries.append(explicit)
        return sdk

    def trial(gradient, context, parent, phenix, output, *, parent_archive_sha256, max_iterations=1000, timeout_seconds=600):
        assert not events and parent_archive_sha256 == digest
        assert timeout_seconds == (600 if seconds is None else seconds)
        assert max_iterations == (1000 if iterations is None else iterations)
        assert phenix is (None if inspect_only else sdk)
        gradient, context, parent, output = map(Path, (gradient, context, parent, output))
        assert (gradient/'mixed_initial_gradients.json').read_bytes() == original_members[GRADIENT+'mixed_initial_gradients.json']
        assert (gradient/'qualification.json').read_bytes() == original_members[GRADIENT+'qualification.json']
        assert (context/'mixed_context.json').read_bytes() == original_members[CONTEXT+'mixed_context.json']
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        assert (gradient/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')
        assert all(not p.is_relative_to(output.parent) for p in [gradient, context, parent])
        assert (output.parent/'inputs/parent_review.zip').read_bytes() == original_zip
        views.extend([gradient, context, parent])
        events.append('trial')
        output.mkdir()
        (output/'mixed_geometry_trial.json').write_text(json.dumps(result))
        return result

    def read(output, *, gradient_directory, context_directory, linked_parent_directory, parent_archive_sha256):
        assert events == ['trial'] and parent_archive_sha256 == digest
        assert tuple(map(Path, (gradient_directory, context_directory, linked_parent_directory))) == tuple(views)
        assert all(p.is_dir() for p in views)
        assert json.loads((Path(output)/'mixed_geometry_trial.json').read_bytes()) == result
        events.append('reader')
        return result

    def forbidden(*args, **kwargs): pytest.fail('geometry ferry executed an unrequested subprocess')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.config.load_config', lambda: {})
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', discovery)
    monkeypatch.setattr('nasolve.cif_mixed_geometry.trial_mixed_geometry', trial)
    monkeypatch.setattr('nasolve.cif_mixed_geometry.read_mixed_geometry_trial', read)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    argv = ['geometry-probe', '--review-zip', str(path), '--phenix-root', str(sdk.root),
        '--output-parent', str(outputs)]
    if inspect_only: argv.append('--inspect-only')
    if seconds is not None: argv.extend(['--timeout-seconds', str(seconds)])
    if iterations is not None: argv.extend(['--max-iterations', str(iterations)])
    monkeypatch.setattr('sys.argv', argv)
    assert ferry.main() == 2
    captured = capsys.readouterr()
    assert 'REVIEW ZIP:' in captured.out and not captured.err
    assert events == ['trial', 'reader']
    assert len(discoveries) == (0 if inspect_only else 1)
    assert all(not p.exists() for p in views)
    archive = next(outputs.glob('*/*_review.zip'))
    with ZipFile(archive) as capsule_zip:
        returned = {n: capsule_zip.read(n) for n in capsule_zip.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert receipt['analysis_completed'] and receipt['parent_review_preserved']
    assert receipt['kind'] == 'mixed-geometry-probe' and receipt['delivery_prefix'] == '90_Cedar'
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['parent_review']['artifact'] == {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
        'sha256': digest, 'size': len(original_zip)}
    assert receipt['parent_review']['payload_count'] == len(original_members)
    assert receipt['parent_review']['preserved'] is True
    assert ('phenix' not in receipt) is inspect_only
    assert returned['inputs/parent_review.zip'] == original_zip and path.read_bytes() == original_zip
    assert list(n for n, d in returned.items() if d == original_zip) == ['inputs/parent_review.zip']
    assert not any(n.startswith('inputs/review/') for n in returned)
    assert not any(n.startswith(('gradient/', 'context/', 'linked_parent/')) for n in returned)
    reference = receipt['mixed_geometry']
    assert reference['status'] == result['status'] and reference['new_native_calls'] == result['new_native_calls']
    assert reference['directory'] == {'anchor': 'probe_directory', 'path': 'mixed_geometry'}
    data = returned['mixed_geometry/mixed_geometry_trial.json']
    assert reference['report_sha256'] == sha256(data).hexdigest() and reference['report_size'] == len(data)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[n]), 'sha256': sha256(returned[n]).hexdigest()}
               for n, ref in manifest.items())


def test_geometry_ferry_build_relocates_without_sources_and_preserves_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_geometry_probe_template.py']:
        path = source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source)
    _initialize_git(nar)
    spec = importlib.util.spec_from_file_location('geometry_builder', ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    runner = tmp_path/'relocated/90_Cedar_probe_mixed_geometry.py'
    metadata = builder.build(source, nar, runner, template_name='mixed_geometry_probe_template.py')
    assert metadata['kind'] == 'mixed-geometry-shuttle' and metadata['delivery_prefix'] == '90_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any(name.endswith('.zip') for name in metadata['runtime_files'])
    shutil.rmtree(source)
    shutil.rmtree(nar)
    result = subprocess.run([sys.executable, '-B', str(runner), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert all(name in result.stdout for name in ['--review-zip', '--inspect-only', '--max-iterations', '--timeout-seconds', '--phenix-root'])
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
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout and 'C89' in result.stderr
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
def test_geometry_review_output_never_exceeds_unchanged_archive_bounds(tmp_path, monkeypatch, bound):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '90_Cedar'}
    session = tmp_path/'90_Cedar_mixed-geometry-owned'
    session.mkdir()
    if bound == 'single_member':
        files = {'inputs/parent_review.zip': b'x'*(33*1024*1024)}
    elif bound == 'entries':
        files = {f'scientific/{i:04d}.bin': b'x' for i in range(1024)}
    else:
        payload = b'x'*(32*1024*1024)
        files = {f'scientific/{i}.bin': payload for i in range(4)}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    with pytest.raises(ValueError, match='archive bounds'): ferry._review_zip(session)
    assert not list(session.glob('*.zip'))


def test_geometry_oversized_output_keeps_parent_and_scientific_session_in_failure_capsule(tmp_path, monkeypatch):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '90_Cedar'}
    session = tmp_path/'90_Cedar_mixed-geometry-owned'
    scientific = session/'mixed_geometry/native.json'
    scientific.parent.mkdir(parents=True)
    original = b'COMPLETED SCIENTIFIC CAPTURE MUST REMAIN AVAILABLE\n'
    scientific.write_bytes(original)
    parent = session/'inputs/parent_review.zip'
    parent.parent.mkdir()
    parent_bytes = b'EXACT OPAQUE HISTORICAL PARENT\n'
    parent.write_bytes(parent_bytes)
    files = {'scientific/oversized.bin': b'x'*(33*1024*1024),
        'mixed_geometry/native.json': original, 'inputs/parent_review.zip': parent_bytes}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    receipt = {'schema_version': 1, 'analysis_completed': True,
        'automatic_adoption': False, 'requires_cif_review': False}
    archive = ferry._report_failure(session, receipt, ValueError('first native evidence failure'))
    assert archive.name.endswith('_failure_review.zip')
    assert scientific.read_bytes() == original and parent.read_bytes() == parent_bytes
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
