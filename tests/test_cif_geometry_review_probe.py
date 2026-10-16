"""Hash-bound captured-evidence transport; no installed Phenix is invoked."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from tests.test_cif_captured_geometry import native

ROOT = Path(__file__).resolve().parents[1]


def template():
    spec = importlib.util.spec_from_file_location('geometry_review_template', ROOT / 'scripts/cif_geometry_review_probe_template.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def capsule(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    module = template(); prefix = module.CAPTURE_PREFIX
    report = native(); entries = {}
    inputs = []
    for i, role in enumerate(['model'] + ['dictionary']*18 + ['phil']*11):
        path = 'inputs/{:03d}_{}.txt'.format(i, role); data = ('EXPLICIT_FAKE_' + str(i)).encode()
        entries[prefix + '/' + path] = data
        inputs.append({'anchor': 'native_directory', 'path': path, 'role': role,
                       'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    data = json.dumps(report).encode(); entries[prefix + '/native_validation.json'] = data
    capture = {'audit_kind': 'cif_native_bundle_inspection', 'policy_id': 'cif-native-bundle-inventory-v1',
               'status': 'REVIEW', 'execution': {'status': 'COMPLETED', 'returncode': 0},
               'source_preserved': True, 'frozen_inputs_preserved': True, 'automatic_adoption': False,
               'native_validation': report, 'inputs': inputs,
               'outputs': [{'anchor': 'native_directory', 'path': 'native_validation.json',
                            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}
    entries[prefix + '/native_receipt.json'] = json.dumps(capture).encode()
    qualification = {'checks': [{'check': 'fixture_' + str(i), 'status': 'PASS'} for i in range(138)] +
                                [{'check': 'effective-site-formal-charges:Z:' + str(i), 'status': 'UNSUPPORTED'} for i in range(9)]}
    prior = {'kind': 'cif-outgoing-bundle-native-probe', 'delivery_prefix': '14_Cedar', 'status': 'REVIEW',
             'original_archive_preserved': True, 'frozen_inputs_preserved': True,
             'qualification': qualification, 'native_validation': capture, 'outgoing_preparations': [],
             'build': {'nasolve_source': {'commit': 'EXPLICIT_FAKE'}, 'narestraints_source': {'commit': 'EXPLICIT_FAKE'}}}
    entries['probe_receipt.json'] = json.dumps(prior).encode()
    entries['bundle_qualification.json'] = json.dumps(qualification).encode()
    for i in range(141-len(entries)):
        entries['padding/{:03d}.txt'.format(i)] = b'UNSELECTED_BUT_VERIFIED'
    path = tmp_path / 'captured.zip'
    write_capsule(path, entries)
    return path


def write_capsule(path, entries, *, duplicate=False, symlink=False):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in entries.items():
            if symlink and name == 'padding/000.txt':
                info = zipfile.ZipInfo(name); info.external_attr = 0o120777 << 16
                z.writestr(info, data)
            else:
                z.writestr(name, data)
        manifest = {n: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for n, data in entries.items()}
        z.writestr('manifest.json', json.dumps(manifest))
        if duplicate:
            with pytest.warns(UserWarning): z.writestr('padding/000.txt', b'other')


def test_complete_capture_is_verified_then_only_anchored_members_materialize(tmp_path):
    module = template(); path = capsule(tmp_path); original = path.read_bytes()
    members, prior, _ = module._read_capsule(path, hashlib.sha256(original).hexdigest())
    session = tmp_path / 'session'
    report, state = module._freeze_capture(session, members, prior)
    module._verify_frozen(session, state)
    assert len(members) == 142 and len(state['frozen_members']) == 32
    assert not (session / 'inputs/review/padding').exists()
    assert report['atom_count'] == 4 and path.read_bytes() == original
    first = next(iter(state['frozen_members']))
    (session / 'inputs/review' / first).write_text('changed')
    with pytest.raises(ValueError, match='changed'): module._verify_frozen(session, state)


@pytest.mark.parametrize('defect', ['archive', 'unsafe_path', 'duplicate', 'symlink', 'unselected_payload'])
def test_changed_or_unsafe_capsule_is_refused(tmp_path, defect):
    module = template(); path = capsule(tmp_path)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    if defect == 'archive':
        path.write_bytes(path.read_bytes() + b'changed')
    else:
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist() if n != 'manifest.json'}
        if defect == 'unsafe_path': entries['../escaped.txt'] = entries.pop('padding/000.txt')
        write_capsule(path, entries, duplicate=defect == 'duplicate', symlink=defect == 'symlink')
        if defect == 'unselected_payload':
            # Preserve the recorded digest while changing a member.
            with zipfile.ZipFile(path) as z:
                entries = {n: z.read(n) for n in z.namelist()}
            entries['padding/000.txt'] = b'changed'
            with zipfile.ZipFile(path, 'w') as z:
                for n, data in entries.items(): z.writestr(n, data)
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError): module._read_capsule(path, expected)


def test_cli_preserves_inputs_and_reports_completed_review_without_external_tools(tmp_path, monkeypatch):
    module = template(); path = capsule(tmp_path/'protected'); original = path.read_bytes()
    module.REVIEW_SHA256 = hashlib.sha256(original).hexdigest(); module.BUNDLE = {'delivery_prefix': '15_Cedar'}
    monkeypatch.setattr(module, '_runtime_members', lambda: {})
    monkeypatch.setattr(sys, 'argv', ['runner', '--review-zip', str(path), '--output-parent', str(tmp_path/'out')])
    assert module.main() == 2
    session = next((tmp_path/'out').iterdir())
    receipt = json.loads((session/'probe_receipt.json').read_text())
    assert receipt['analysis_completed'] and receipt['native_execution'] == 'NOT_RUN'
    assert receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['automatic_adoption'] is False and path.read_bytes() == original
    assert len(list(session.glob('15_Cedar_*_cif_geometry_review.zip'))) == 1


def test_runner_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0, str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root, nar = tmp_path/'build', tmp_path/'nar'
    for relative in ['src', 'MR_frames/5W6W', 'docs/recipes']:
        shutil.copytree(ROOT/relative, root/relative, ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    path = capsule(tmp_path/'protected'); digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source = (ROOT/'scripts/cif_geometry_review_probe_template.py').read_text().replace(template().REVIEW_SHA256, digest)
    (root/'scripts/cif_geometry_review_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root, nar):
        subprocess.run(['git', 'init', str(checkout)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(checkout), 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(checkout), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-m', 'fixture'], check=True, capture_output=True)
    runner = tmp_path/'15_Cedar_probe_cif_geometry_review.py'
    metadata = build(root, nar, runner, template_name='cif_geometry_review_probe_template.py')
    assert metadata['kind'] == 'cif-captured-geometry-review-shuttle'
    assert metadata['dependencies'] == ['Python >=3.10']
    shutil.rmtree(root); shutil.rmtree(nar)
    poison = tmp_path/'poison/nasolve'; poison.mkdir(parents=True)
    (poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result = subprocess.run([sys.executable, '-B', str(runner), '--review-zip', str(path),
                             '--output-parent', str(tmp_path/'out')], cwd=tmp_path, capture_output=True,
                            text=True, env={**os.environ, 'PYTHONPATH': str(poison.parent)})
    assert result.returncode == 2 and 'Diagnostic: REVIEW' in result.stdout
    assert 'stopped' not in result.stderr and 'poisoned import' not in result.stderr
    receipt = json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved']
