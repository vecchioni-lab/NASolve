"""The independent ferry preserves failures and avoids ambient imports."""
from hashlib import sha256
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZipInfo

import pytest
import restraints

ROOT = Path(__file__).parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize('defect', ['none', 'member', 'archive', 'inventory', 'traversal', 'symlink', 'duplicate'])
def test_runtime_integrity_precedes_extraction(defect):
    m = module(ROOT/'scripts/mixed_pair_probe_template.py', 'mixed_runtime_'+defect)
    name = '../outside' if defect == 'traversal' else 'src/nasolve/fixture.py'
    data = b'# source fixture only\n'
    archive = io.BytesIO()
    with ZipFile(archive, 'w') as z:
        entry = ZipInfo(name)
        entry.external_attr = (0o120777 if defect == 'symlink' else 0o100644) << 16
        z.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning):
                z.writestr(entry, data)
    raw = archive.getvalue()
    m.BUNDLE = {'runtime_archive_sha256': sha256(raw).hexdigest(),
                'runtime_files': {name: {'sha256': sha256(data).hexdigest(), 'size': len(data)}}}
    m.RUNTIME_BASE64 = base64.b64encode(raw).decode()
    if defect == 'archive':
        m.BUNDLE['runtime_archive_sha256'] = '0'*64
    if defect == 'member':
        m.BUNDLE['runtime_files'][name]['sha256'] = '0'*64
    if defect == 'inventory':
        m.BUNDLE['runtime_files']['missing'] = m.BUNDLE['runtime_files'][name]
    if defect == 'none':
        assert m._runtime_members() == {name: data}
    else:
        with pytest.raises(ValueError):
            m._runtime_members()


@pytest.mark.parametrize('collection_fails', [False, True])
def test_failure_keeps_original_error_and_checked_capsule(tmp_path, monkeypatch, collection_fails):
    m = module(ROOT/'scripts/mixed_pair_probe_template.py', 'mixed_failure')
    m.BUNDLE = {'delivery_prefix': '80_Cedar'}
    session = tmp_path/'80_Cedar_mixed-pair-token'; session.mkdir()
    (session/'saved_model.pdb').write_bytes(b'UNCHANGED INPUT FIXTURE\n')
    receipt = {'native_membership': 'NOT_ASSESSED', 'requires_cif_review': False}
    if collection_fails:
        import nasolve.cif_review_transport as transport
        monkeypatch.setattr(transport, 'review_archive_files', lambda *a: (_ for _ in ()).throw(OSError('COLLECTION FAILURE')))
    archive = m._report_failure(session, receipt, ValueError('FIRST CONSTRUCTION FAILURE'))
    with ZipFile(archive) as z:
        r = json.loads(z.read('probe_receipt.json'))
        assert r['error'] == 'FIRST CONSTRUCTION FAILURE' and r['analysis_completed'] is False
        assert r['native_membership'] == 'NOT_ASSESSED' and not r['requires_cif_review']
        manifest = json.loads(z.read('manifest.json'))
        assert len(manifest)+1 == len(z.namelist())
        for name, ref in manifest.items():
            data = z.read(name)
            assert len(data) == ref['bytes'] and sha256(data).hexdigest() == ref['sha256']
        if collection_fails:
            assert 'failure_archive_scope' in r and 'COLLECTION FAILURE' in r['archive_collection_error']
            assert z.namelist() == ['probe_receipt.json', 'manifest.json']
        else:
            assert z.read('saved_model.pdb') == b'UNCHANGED INPUT FIXTURE\n'


def test_zip_writer_failure_retains_receipt_and_original_error(tmp_path, monkeypatch):
    m = module(ROOT/'scripts/mixed_pair_probe_template.py', 'mixed_no_zip')
    m.BUNDLE = {'delivery_prefix': '80_Cedar'}
    receipt = {'requires_cif_review': False}
    monkeypatch.setattr(m.zipfile, 'ZipFile', lambda *a, **k: (_ for _ in ()).throw(OSError('NO SPACE')))
    with pytest.raises(OSError, match='NO SPACE'):
        m._report_failure(tmp_path, receipt, RuntimeError('FIRST ERROR'))
    assert json.loads((tmp_path/'probe_receipt.json').read_bytes())['error'] == 'FIRST ERROR'


@pytest.fixture
def delivered(tmp_path):
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source = tmp_path/'source'; nar = tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'docs/cif-doctor-ccd-controls.json',
                     'tests/fixtures/public_ccd/ATL.cif', 'scripts/mixed_pair_probe_template.py']:
        p = source/relative; p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/relative, p)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source); _initialize_git(nar)
    runner = tmp_path/'relocated/80_Cedar_probe_mixed_pairs.py'
    builder = module(ROOT/'scripts/build_synthetic_dna_shuttle.py', 'mixed_builder')
    metadata = builder.build(source, nar, runner, template_name='mixed_pair_probe_template.py', component_controls=('ATL',))
    shutil.rmtree(source); shutil.rmtree(nar)
    return runner, metadata


def test_builder_and_help_need_no_source_checkout(delivered, tmp_path):
    runner, metadata = delivered
    assert metadata['delivery_prefix'] == '80_Cedar'
    assert metadata['kind'] == 'mixed-eight-pair-construction-shuttle'
    assert metadata['default_model'] == 'MR_frames/5W6W/C_G.pdb'
    assert [v['component'] for v in metadata['component_controls']] == ['ATL']
    assert not metadata['private_diffraction_included'] and metadata['automatic_adoption'] is False
    assert not any('review.zip' in name for name in metadata['runtime_files'])
    result = subprocess.run([sys.executable, '-B', str(runner), '--help'], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0 and '--inspect-only' in result.stdout
    assert '--review-zip' not in result.stdout


def test_source_discovery_failure_still_returns_capsule(delivered, tmp_path):
    runner, metadata = delivered
    config = tmp_path/'user-config.json'
    original = b'{"workspace":{"run":"keep-active-run"},"coot":{}}\n'; config.write_bytes(original)
    poison = tmp_path/'poison'
    for name in ['nasolve', 'restraints']:
        p = poison/name; p.mkdir(parents=True); (p/'__init__.py').write_text('raise RuntimeError("AMBIENT_IMPORT")\n')
    guard = tmp_path/'guard.py'
    guard.write_text('import runpy,subprocess,sys\ndef forbidden(*a,**k):raise AssertionError("NO_NATIVE_PROCESS_ALLOWED")\nsubprocess.Popen=forbidden\np=sys.argv.pop(1)\nrunpy.run_path(p,run_name="__main__")\n')
    result = subprocess.run([sys.executable, '-B', str(guard), str(runner), '--inspect-only',
        '--phenix-root', str(tmp_path/'missing-phenix'), '--output-parent', str(tmp_path/'outputs')],
        cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(poison), 'NASOLVE_CONFIG_FILE': str(config)})
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout
    assert 'Mixed-pair test stopped:' in result.stderr and 'AMBIENT_IMPORT' not in result.stderr
    assert config.read_bytes() == original
    archive = next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as z:
        receipt = json.loads(z.read('probe_receipt.json'))
        assert receipt['analysis_completed'] is False and not receipt['requires_cif_review']
        assert receipt['native_membership'] == 'NOT_ASSESSED' and receipt['production_checkpoint'] == 'NOT_CREATED'
        assert receipt['phenix_execution'] == receipt['readyset_execution'] == 'NOT_RUN'
        assert all(not name.startswith('runtime/') for name in z.namelist())
        assert receipt['build'] == metadata
