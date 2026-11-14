"""C95 uses the public bundle assessor with no native or optimizer switches."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).parents[1]


def module():
    spec = importlib.util.spec_from_file_location('mixed_runtime_ferry', ROOT/'scripts/mixed_runtime_probe_template.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


@pytest.mark.parametrize('reject', [False, True])
def test_ferry_preserves_one_parent_and_keeps_diagnostics_on_assessor_refusal(tmp_path, monkeypatch, capsys, reject):
    import nasolve, restraints
    from nasolve import cif_runtime_bundle as ordinary, cif_mixed_runtime_bundle as mixed
    ferry = module(); ferry.BUNDLE = {'delivery_prefix': '95_Cedar'}
    source = tmp_path/'c94.zip'; source.write_bytes(b'BOUND_SOURCE'); ferry.REVIEW_SHA256 = sha256(source.read_bytes()).hexdigest()
    runtime = {'src/nasolve/__init__.py': b'', 'restraints/__init__.py': b''}
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime)
    def isolate(root, session, members):
        for n, d in members.items(): ferry._write(root/n, d)
        monkeypatch.setattr(nasolve, '__file__', str(root/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(root/'restraints/__init__.py'))
    monkeypatch.setattr(ferry, '_isolate', isolate)
    expected = {'model': {'sha256': 'a'*64}, 'dictionaries': [{'sha256': 'b'*64}], 'phils': [{'sha256': 'c'*64}]}
    manifest = {'resources': expected, 'decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'qualified_geometry_endpoint'},
                'qualification': {'atom_count': 42}}
    def prepare(path, output, **kwargs):
        assert kwargs == {'source_sha256': ferry.REVIEW_SHA256}
        ferry._write(output/'runtime_bundle.json', manifest)
        ferry._write(output/'evidence/source_review.zip', source.read_bytes())
        return manifest
    monkeypatch.setattr(mixed, 'prepare_mixed_runtime_bundle', prepare)
    calls = []
    def assess(path):
        calls.append(path)
        assert path.name == 'activated_bundle' and not (path.parent/'runtime_bundle').exists()
        if reject: raise ValueError('ORDINARY_READER_REFUSAL')
        return {'status': 'REVIEW', 'model': expected['model'], 'inputs': expected['dictionaries']+expected['phils'],
            'requires_cif_review': False, 'solution_report': {'selected_candidate': 'qualified_geometry_endpoint'}}
    monkeypatch.setattr(ordinary, 'assess_runtime_bundle', assess)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Ferry launched native process'))
    monkeypatch.setattr('sys.argv', ['test', '--review-zip', str(source), '--output-parent', str(tmp_path/'output')])
    assert ferry.main() == 2 and len(calls) == 1
    archives = list((tmp_path/'output').glob('*/*_review.zip')); assert len(archives) == 1
    with ZipFile(archives[0]) as z:
        receipt = json.loads(z.read('probe_receipt.json'))
        assert receipt['analysis_completed'] is not reject and receipt['new_native_calls'] == 0
        assert z.read('activated_bundle/evidence/source_review.zip') == source.read_bytes()
        assert len([n for n in z.namelist() if n.endswith('.zip')]) == 1
        assert not any(n.startswith('runtime/') or 'inputs/review/' in n for n in z.namelist())
        if reject: assert receipt['error'] == 'ORDINARY_READER_REFUSAL'
        else: assert receipt['mixed_runtime']['status'] == 'MIXED_RUNTIME_HANDOFF_PASS'
    assert 'REVIEW ZIP:' in capsys.readouterr().out


@pytest.mark.parametrize('flag', ['--phenix-root', '--max-iterations', '--timeout-seconds', '--inspect-only'])
def test_no_native_optimizer_or_partial_inspection_mode(tmp_path, monkeypatch, flag):
    ferry = module(); monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('Invalid flag unpacked runtime'))
    monkeypatch.setattr('sys.argv', ['test', '--review-zip', str(tmp_path/'missing'), flag, '1'])
    with pytest.raises(SystemExit) as stop: ferry.main()
    assert stop.value.code == 2


def test_builder_bundles_current_runtime_without_old_ferry_dependencies(tmp_path):
    from tests.test_synthetic_dna_shuttle import _initialize_git
    import restraints, shutil
    # The shared builder is exercised by real-source cold validation as well.
    import sys
    sys.path.insert(0, str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    root, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, root/relative)
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_runtime_probe_template.py']:
        path = root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT/relative).read_bytes())
    shutil.copytree(Path(restraints.__file__).resolve().parent, nar/'restraints')
    _initialize_git(root); _initialize_git(nar)
    output = tmp_path/'runner.py'
    metadata = build(root, nar, output, template_name='mixed_runtime_probe_template.py')
    assert metadata['delivery_prefix'] == '95_Cedar'
    assert metadata['native_validation'] == 'NOT_RUN_ORDINARY_BUNDLE_SAVED_EVIDENCE'
    assert 'support/c93_endpoint_ferry.py' not in metadata['runtime_files']
