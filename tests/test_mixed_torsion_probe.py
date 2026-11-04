"""Fixed-coordinate torsion ferry with exact nested opaque review ancestry."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from tests.test_mixed_geometry_probe import capsule as gradient_capsule

ROOT = Path(__file__).parents[1]
GEOMETRY = 'mixed_geometry/'
GRADIENT = 'mixed_gradient/'
CONTEXT = 'inputs/review/inputs/review/mixed_context/'
PARENT = 'inputs/review/inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'


def module():
    spec = importlib.util.spec_from_file_location('mixed_torsion_ferry', ROOT/'scripts/mixed_torsion_probe_template.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def capsule(tmp_path, defect='none'):
    inner_defect = defect.removeprefix('inner_') if defect.startswith('inner_') else 'none'
    inner, inner_digest, inner_members = gradient_capsule(tmp_path, inner_defect)
    inner_bytes = inner.read_bytes()
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-qualified-geometry-trial-v1',
        'status': 'REVIEW', 'new_native_calls': 1, 'maximum_native_calls': 2,
        'parent_archive_sha256': inner_digest, 'automatic_adoption': False,
        'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED',
        'model_optimization': 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL',
        'execution': {'status': 'COMPLETED', 'returncode': 0},
        'qualification': {'status': 'REVIEW', 'sampled_derivatives_pass': False},
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES',
            'selected': 'verified_constructed_model', 'native_usable': True,
            'endpoint_usable': False, 'continue_solving': True,
            'automatic_adoption': False, 'requires_cif_review': False}}
    mutations = {'policy': ('policy_id', 'OTHER'), 'status': ('status', 'PREPARED_ONLY'),
        'new_count': ('new_native_calls', 0), 'new_count_bool': ('new_native_calls', True),
        'adoption': ('automatic_adoption', True), 'approval': ('requires_cif_review', True),
        'science': ('scientific_qualification', 'APPROVED'), 'optimization': ('model_optimization', 'NOT_RUN'),
        'parent_hash': ('parent_archive_sha256', '0'*64)}
    if defect in mutations: report[mutations[defect][0]] = mutations[defect][1]
    elif defect == 'execution': report['execution']['returncode'] = 2
    elif defect == 'execution_bool': report['execution']['returncode'] = False
    elif defect == 'unusable_original': report['coordinate_decision']['native_usable'] = False
    elif defect == 'decision_adoption': report['coordinate_decision']['automatic_adoption'] = True
    rdata = json.dumps(report).encode()
    reference = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_geometry'},
        'report_sha256': sha256(rdata).hexdigest(), 'report_size': len(rdata),
        'status': 'REVIEW', 'new_native_calls': 1}
    parent_ref = {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
        'sha256': inner_digest, 'size': len(inner_bytes)}
    header = {'schema_version': 1, 'kind': 'mixed-geometry-probe', 'delivery_prefix': '90_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'mixed_geometry': reference, 'parent_review': {'artifact': parent_ref,
            'payload_count': len(inner_members), 'preserved': True}, 'parent_review_preserved': True}
    if defect == 'kind': header['kind'] = 'OTHER'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'header_approval': header['requires_cif_review'] = True
    elif defect == 'report_hash': reference['report_sha256'] = '0'*64
    elif defect == 'report_size': reference['report_size'] += 1
    elif defect == 'report_path': reference['directory']['path'] = '../outside'
    elif defect == 'report_anchor': reference['directory']['anchor'] = 'unbound_location'
    elif defect == 'envelope_count_bool': reference['new_native_calls'] = True
    elif defect == 'parent_anchor': parent_ref['anchor'] = 'unbound_location'
    elif defect == 'parent_path': parent_ref['path'] = '../outside'
    elif defect == 'parent_size': parent_ref['size'] += 1
    elif defect == 'parent_count': header['parent_review']['payload_count'] += 1
    elif defect == 'parent_preserved': header['parent_review']['preserved'] = False
    elif defect == 'parent_envelope_preserved': header['parent_review_preserved'] = False
    members = {'probe_receipt.json': json.dumps(header).encode(),
        GEOMETRY+'mixed_geometry_trial.json': rdata,
        GEOMETRY+'job/geometry_result.json': b'{"saved_endpoint":"FAILED_DERIVATIVES_RETAINED"}\n',
        GEOMETRY+'job/captured.py': b'raise RuntimeError("CAPTURED_GEOMETRY_CODE_MUST_NOT_RUN")\n',
        'inputs/parent_review.zip': inner_bytes,
        'unrelated/mixed_geometry_trial.json': b'DECOY_GEOMETRY\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['saved/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['saved/oversize.json'] = b' '*(33*1024*1024)
    elif defect == 'entries': members.update({f'saved/extra/{i:04d}.txt': b'x' for i in range(1024)})
    manifest = {name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)} for name, data in members.items()}
    if defect == 'hash': manifest[GEOMETRY+'mixed_geometry_trial.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop(GEOMETRY+'mixed_geometry_trial.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'geometry-review.zip'
    path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members, inner_digest, inner_members


def configure(ferry, digest, inner_digest):
    ferry.REVIEW_SHA256 = digest
    ferry.GEOMETRY_PARENT_SHA256 = inner_digest


def test_completed_geometry_review_with_failed_endpoint_is_accepted_as_data(tmp_path):
    ferry = module()
    path, digest, members, inner_digest, _ = capsule(tmp_path)
    configure(ferry, digest, inner_digest)
    actual = ferry._read_capsule(path)
    assert {name: actual[name] for name in members} == members


def test_torsion_inputs_use_only_four_declared_shallow_views(tmp_path):
    ferry = module()
    _, digest, members, inner_digest, inner_members = capsule(tmp_path)
    configure(ferry, digest, inner_digest)
    destination = tmp_path/'inputs'
    views = ferry._materialize_inputs(members, destination)
    assert tuple(map(Path, views)) == tuple(destination/n for n in ['geometry', 'gradient', 'context', 'linked_parent'])
    for prefix, view, source in [(GEOMETRY, views[0], members),
        (GRADIENT, views[1], inner_members), (CONTEXT, views[2], inner_members), (PARENT, views[3], inner_members)]:
        expected = {n[len(prefix):]: d for n, d in source.items() if n.startswith(prefix)}
        actual = {p.relative_to(view).as_posix(): p.read_bytes() for p in Path(view).rglob('*') if p.is_file()}
        assert actual == expected


@pytest.mark.parametrize('timeout', ['0', '601'])
def test_bad_torsion_deadline_stops_before_runtime_or_archive(tmp_path, monkeypatch, timeout):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('invalid deadline read runtime'))
    monkeypatch.setattr('sys.argv', ['torsion-probe', '--review-zip', str(tmp_path/'absent.zip'), '--timeout-seconds', timeout])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


@pytest.mark.parametrize('defect', ['large', 'kind', 'prefix', 'incomplete', 'header_approval',
    'policy', 'status', 'new_count', 'new_count_bool', 'adoption', 'approval', 'science',
    'optimization', 'execution', 'execution_bool', 'unusable_original', 'decision_adoption',
    'envelope_count_bool', 'report_hash', 'report_size', 'report_path', 'report_anchor',
    'parent_hash', 'parent_anchor', 'parent_path', 'parent_size', 'parent_count',
    'parent_preserved', 'parent_envelope_preserved', 'path', 'hash', 'inventory', 'symlink',
    'duplicate', 'archive', 'oversize', 'entries'])
def test_torsion_parent_bindings_and_outer_capsule_bounds_are_strict(tmp_path, defect):
    ferry = module()
    path, digest, members, inner_digest, _ = capsule(tmp_path, defect)
    configure(ferry, '0'*64 if defect == 'archive' else digest, inner_digest)
    original = path.read_bytes()
    if defect == 'large':
        actual = ferry._read_capsule(path)
        assert {n: actual[n] for n in members} == members
    else:
        with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original
    assert not (tmp_path/'outside').exists()


@pytest.mark.parametrize('defect', ['hash', 'inventory', 'symlink', 'duplicate', 'path', 'oversize', 'entries'])
def test_nested_gradient_capsule_is_validated_before_scientific_staging(tmp_path, defect):
    ferry = module()
    path, digest, _, inner_digest, _ = capsule(tmp_path, 'inner_'+defect)
    configure(ferry, digest, inner_digest)
    original = path.read_bytes()
    with pytest.raises(ValueError): ferry._read_capsule(path)
    assert path.read_bytes() == original and not (tmp_path/'outside').exists()


def test_exact_nested_gradient_archive_checksum_is_required(tmp_path):
    ferry = module()
    path, digest, _, inner_digest, _ = capsule(tmp_path)
    configure(ferry, digest, '0'*64)
    with pytest.raises(ValueError): ferry._read_capsule(path)


def test_opaque_geometry_parent_must_fit_the_unchanged_outer_member_limit(tmp_path):
    ferry = module()
    _, _, members, inner_digest, _ = capsule(tmp_path)
    payload = b'x'*(17*1024*1024)
    members.update({'bounded_one.bin': payload, 'bounded_two.bin': payload})
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items(): archive.writestr(name, data)
        manifest = {n: {'sha256': sha256(d).hexdigest(), 'bytes': len(d)} for n, d in members.items()}
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'too-large-opaque-parent.zip'
    path.write_bytes(raw.getvalue())
    configure(ferry, sha256(raw.getvalue()).hexdigest(), inner_digest)
    assert path.stat().st_size > 32*1024*1024
    with pytest.raises(ValueError): ferry._read_capsule(path)


def test_torsion_input_views_refuse_existing_user_directory(tmp_path):
    ferry = module()
    _, digest, members, inner_digest, _ = capsule(tmp_path)
    configure(ferry, digest, inner_digest)
    destination = tmp_path/'existing'
    destination.mkdir()
    sentinel = destination/'keep.txt'
    sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError): ferry._materialize_inputs(members, destination)
    assert sentinel.read_bytes() == b'KEEP USER DATA' and list(destination.iterdir()) == [sentinel]


def _pack(members):
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items(): archive.writestr(name, data)
        manifest = {n: {'sha256': sha256(d).hexdigest(), 'bytes': len(d)} for n, d in members.items()}
        archive.writestr('manifest.json', json.dumps(manifest))
    return raw.getvalue()


@pytest.mark.parametrize('missing', [GEOMETRY, GRADIENT, CONTEXT, PARENT])
def test_missing_explicit_geometry_or_ancestor_view_has_no_basename_fallback(tmp_path, missing):
    ferry = module()
    _, digest, members, inner_digest, inner_members = capsule(tmp_path)
    if missing == GEOMETRY:
        members = {n: d for n, d in members.items() if not n.startswith(missing)}
    else:
        inner = _pack({n: d for n, d in inner_members.items() if not n.startswith(missing)})
        members['inputs/parent_review.zip'] = inner
        inner_digest = sha256(inner).hexdigest()
    configure(ferry, digest, inner_digest)
    with pytest.raises((ValueError, KeyError)): ferry._materialize_inputs(members, tmp_path/'missing-view')


@pytest.mark.parametrize('inspect_only,seconds', [(True, None), (False, None), (True, 1), (False, 600)])
def test_torsion_main_uses_four_views_and_preserves_one_exact_opaque_parent(tmp_path, monkeypatch, capsys, inspect_only, seconds):
    import nasolve
    import restraints
    from types import SimpleNamespace
    ferry = module()
    path, digest, original_members, inner_digest, inner_members = capsule(tmp_path)
    original_zip = path.read_bytes()
    runtime_members = {'src/nasolve/__init__.py': b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py': b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry, 'BUNDLE', {'delivery_prefix': '91_Cedar'})
    monkeypatch.setattr(ferry, 'REVIEW_SHA256', digest)
    monkeypatch.setattr(ferry, 'GEOMETRY_PARENT_SHA256', inner_digest)
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
    result = {'schema_version': 1, 'policy_id': 'cif-mixed-fixed-torsion-audit-v1',
        'status': 'PREPARED_ONLY' if inspect_only else 'REVIEW',
        'new_native_calls': 0 if inspect_only else 1, 'coordinate_decision': decision}

    def discovery(config, *, explicit, environ):
        assert not inspect_only and Path(explicit) == sdk.root
        discoveries.append(explicit)
        return sdk

    def audit(geometry, gradient, context, parent, phenix, output, *, parent_archive_sha256, timeout_seconds=120):
        assert not events and parent_archive_sha256 == digest
        assert timeout_seconds == (120 if seconds is None else seconds)
        assert phenix is (None if inspect_only else sdk)
        geometry, gradient, context, parent, output = map(Path, (geometry, gradient, context, parent, output))
        assert (geometry/'mixed_geometry_trial.json').read_bytes() == original_members[GEOMETRY+'mixed_geometry_trial.json']
        assert (geometry/'job/geometry_result.json').read_bytes() == original_members[GEOMETRY+'job/geometry_result.json']
        assert (gradient/'mixed_initial_gradients.json').read_bytes() == inner_members[GRADIENT+'mixed_initial_gradients.json']
        assert (context/'mixed_context.json').read_bytes() == inner_members[CONTEXT+'mixed_context.json']
        assert (parent/'inputs/model.pdb').read_bytes() == b'EXACT SCIENTIFIC MODEL\n'
        assert (geometry/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')
        assert all(not p.is_relative_to(output.parent) for p in [geometry, gradient, context, parent])
        assert (output.parent/'inputs/parent_review.zip').read_bytes() == original_zip
        views.extend([geometry, gradient, context, parent])
        events.append('audit')
        output.mkdir()
        (output/'mixed_torsion_audit.json').write_text(json.dumps(result))
        return result

    def read(output, *, geometry_directory, gradient_directory, context_directory, linked_parent_directory, parent_archive_sha256):
        assert events == ['audit'] and parent_archive_sha256 == digest
        assert tuple(map(Path, (geometry_directory, gradient_directory, context_directory, linked_parent_directory))) == tuple(views)
        assert all(p.is_dir() for p in views)
        assert json.loads((Path(output)/'mixed_torsion_audit.json').read_bytes()) == result
        events.append('reader')
        return result

    def forbidden(*args, **kwargs): pytest.fail('torsion ferry executed an unrequested subprocess')

    monkeypatch.setattr(ferry, '_isolate', isolated_fixture)
    monkeypatch.setattr('nasolve.config.load_config', lambda: {})
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix', discovery)
    import sys
    from types import ModuleType
    owned_module = ModuleType('nasolve.cif_mixed_torsion')
    owned_module.audit_mixed_torsions = audit
    owned_module.read_mixed_torsions = read
    monkeypatch.setitem(sys.modules, 'nasolve.cif_mixed_torsion', owned_module)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    outputs = tmp_path/'outputs'
    argv = ['torsion-probe', '--review-zip', str(path), '--phenix-root', str(sdk.root),
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
    assert receipt['kind'] == 'mixed-torsion-probe' and receipt['delivery_prefix'] == '91_Cedar'
    assert not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['model_optimization_requested'] is False
    assert receipt['parent_review']['artifact'] == {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
        'sha256': digest, 'size': len(original_zip)}
    assert receipt['parent_review']['payload_count'] == len(original_members)
    assert receipt['parent_review']['preserved'] is True
    assert ('phenix' not in receipt) is inspect_only
    assert returned['inputs/parent_review.zip'] == original_zip and path.read_bytes() == original_zip
    assert list(n for n, d in returned.items() if d == original_zip) == ['inputs/parent_review.zip']
    assert not any(n.startswith('inputs/review/') for n in returned)
    assert not any(n.startswith(('geometry/', 'gradient/', 'context/', 'linked_parent/')) for n in returned)
    reference = receipt['mixed_torsion']
    assert reference['status'] == result['status'] and reference['new_native_calls'] == result['new_native_calls']
    assert reference['directory'] == {'anchor': 'probe_directory', 'path': 'mixed_torsion'}
    data = returned['mixed_torsion/mixed_torsion_audit.json']
    assert reference['report_sha256'] == sha256(data).hexdigest() and reference['report_size'] == len(data)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[n]), 'sha256': sha256(returned[n]).hexdigest()}
               for n, ref in manifest.items())


def test_torsion_cli_excludes_optimizer_controls(tmp_path, monkeypatch):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('optimizer argument read runtime'))
    monkeypatch.setattr('sys.argv', ['torsion-probe', '--review-zip', str(tmp_path/'absent.zip'), '--max-iterations', '1000'])
    with pytest.raises(SystemExit) as stopped: ferry.main()
    assert stopped.value.code == 2


def test_torsion_ferry_build_relocates_without_sources_and_preserves_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_torsion_probe_template.py']:
        path = source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source)
    _initialize_git(nar)
    spec = importlib.util.spec_from_file_location('torsion_builder', ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    runner = tmp_path/'relocated/91_Cedar_probe_mixed_torsions.py'
    metadata = builder.build(source, nar, runner, template_name='mixed_torsion_probe_template.py')
    assert metadata['kind'] == 'mixed-torsion-shuttle' and metadata['delivery_prefix'] == '91_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any(name.endswith('.zip') for name in metadata['runtime_files'])
    shutil.rmtree(source)
    shutil.rmtree(nar)
    result = subprocess.run([sys.executable, '-B', str(runner), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert all(name in result.stdout for name in ['--review-zip', '--inspect-only', '--timeout-seconds', '--phenix-root'])
    assert '--max-iterations' not in result.stdout
    wrapper_help = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/build_mixed_torsion_probe.py'), '--help'], capture_output=True, text=True)
    assert wrapper_help.returncode == 0 and '--local-artifact-checkout' in wrapper_help.stdout
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
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout and 'verified parent ZIP' in result.stderr
    assert 'AMBIENT_IMPORT' not in result.stderr and 'NO_SDK' not in result.stderr
    assert configuration.read_bytes() == original
    archive = next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as captured:
        returned = {name: captured.read(name) for name in captured.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert not receipt['analysis_completed'] and not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['captured_code_execution'] == 'NOT_RUN' and receipt['production_checkpoint'] == 'NOT_CREATED'
    assert receipt['model_optimization_requested'] is False
    assert not any(name.startswith('runtime/') for name in returned)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())


@pytest.mark.parametrize('bound', ['single_member', 'entries', 'total_including_manifest'])
def test_torsion_review_output_never_exceeds_unchanged_archive_bounds(tmp_path, monkeypatch, bound):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '91_Cedar'}
    session = tmp_path/'91_Cedar_mixed-torsion-owned'
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


def test_torsion_oversized_output_keeps_parent_and_scientific_session_in_failure_capsule(tmp_path, monkeypatch):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '91_Cedar'}
    session = tmp_path/'91_Cedar_mixed-torsion-owned'
    scientific = session/'mixed_torsion/native.json'
    scientific.parent.mkdir(parents=True)
    original = b'COMPLETED SCIENTIFIC CAPTURE MUST REMAIN AVAILABLE\n'
    scientific.write_bytes(original)
    parent = session/'inputs/parent_review.zip'
    parent.parent.mkdir()
    parent_bytes = b'EXACT OPAQUE HISTORICAL PARENT\n'
    parent.write_bytes(parent_bytes)
    files = {'scientific/oversized.bin': b'x'*(33*1024*1024),
        'mixed_torsion/native.json': original, 'inputs/parent_review.zip': parent_bytes}
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
