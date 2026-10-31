"""A repaired manager needs its own bound derivative audit."""
import json
import sys
from hashlib import sha256
from pathlib import Path
import pytest
from nasolve.cif_recovered_gradient import audit_recovered_gradients, read_recovered_gradients


def recovery_parent(tmp_path, monkeypatch, *, sdk=None):
    from tests.test_cif_mixed_gradient import anchored_initial_parent, fake_sdk_parent
    from nasolve.cif_mixed_source_recovery import _ref
    if sdk is None:
        root, _ = anchored_initial_parent(tmp_path, monkeypatch); seed = None
    else:
        root, _, seed = fake_sdk_parent(tmp_path, monkeypatch, sdk)
    native = json.loads((root/'saved_active.json').read_bytes())
    capture = root/'active_receipt.json'
    capture.write_text(json.dumps({'native_validation': native, 'phenix_version': 'EXPLICIT_FAKE', 'executable_sha256': sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()}))
    report = {'status': 'MIXED_SOURCE_RECOVERY_MECHANICS_PASS', 'qualification': {'mechanics_checks_pass': True},
        'inputs': {'resources': [{'role': 'model', 'artifact': _ref(root/'model.pdb', root)}],
                   'active_policy': _ref(root/'explicit.phil', root)},
        'bundle': {'native_dictionaries': [_ref(root/'projected.cif', root)], 'context_phils': []},
        'native_captures': {'linked': {'active': _ref(capture, root)}},
        'model_preserved': True, 'source_inputs_preserved': True, 'automatic_adoption': False}
    (root/'mixed_source_recovery.json').write_text(json.dumps(report))
    monkeypatch.setattr('nasolve.cif_mixed_source_recovery.read_mixed_source_recovery',
        lambda p: json.loads((Path(p)/'mixed_source_recovery.json').read_bytes()))
    return root, seed


def test_prepared_recovery_gradient_has_no_inherited_derivative_pass_and_relocates(tmp_path, monkeypatch):
    parent, _ = recovery_parent(tmp_path, monkeypatch)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('Preparation launched a native process'))
    out = tmp_path/'gradient'; report = audit_recovered_gradients(parent, None, out)
    assert report['status'] == 'PREPARED_ONLY'
    assert report['new_native_calls'] == 0 and report['qualification'] == {'status': 'NOT_RUN'}
    assert report['model_optimization'] == report['refinement'] == 'NOT_RUN'
    assert report['coordinate_selection'] == 'UNCHANGED_C98_SOURCE_RECOVERY_INPUT'
    moved = tmp_path/'relocated'; moved.mkdir(); parent.rename(moved/'parent'); out.rename(moved/'gradient')
    assert not parent.exists() and not out.exists()
    assert read_recovered_gradients(moved/'gradient', recovery_directory=moved/'parent') == report


@pytest.mark.parametrize('timeout', [True, 0, -1, 601, 1.5])
def test_invalid_deadline_is_rejected_before_parent_access(tmp_path, timeout):
    with pytest.raises(ValueError): audit_recovered_gradients(tmp_path/'absent', None, tmp_path/'out', timeout_seconds=timeout)
    assert not (tmp_path/'out').exists()


def fake_phenix(parent, seed):
    import os
    from types import SimpleNamespace
    return SimpleNamespace(executables={'phenix.python': sys.executable}, version='EXPLICIT_FAKE',
        environment={**os.environ, 'PYTHONPATH': str(seed), 'EXPLICIT_FAKE_NATIVE': str(parent/'saved_active.json')})


@pytest.mark.parametrize('mode', ['correct', 'manager', 'timeout'])
def test_recovered_job_binds_fresh_manager_and_retains_failure_evidence(tmp_path, monkeypatch, mode):
    parent, seed = recovery_parent(tmp_path, monkeypatch, sdk=mode)
    output = tmp_path/'gradient'
    report = audit_recovered_gradients(parent, fake_phenix(parent, seed), output,
                                      timeout_seconds=1 if mode == 'timeout' else 30)
    assert report['new_native_calls'] == 1
    assert report['execution']['status'] == {'correct': 'COMPLETED', 'manager': 'FAILED', 'timeout': 'TIMED_OUT'}[mode]
    assert report['status'] == ('RECOVERED_MIXED_DERIVATIVES_PASS' if mode == 'correct' else 'REVIEW')
    assert report['model_optimization'] == 'NOT_RUN' and report['automatic_adoption'] is False
    assert not list(tmp_path.rglob('fake_optimizer_called'))
    assert read_recovered_gradients(output, recovery_directory=parent) == report
    if mode == 'correct':
        import shutil
        moved = tmp_path/'moved'; moved.mkdir(); parent.rename(moved/'parent'); output.rename(moved/'gradient')
        shutil.rmtree(seed)
        monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('Reader launched a process'))
        assert read_recovered_gradients(moved/'gradient', recovery_directory=moved/'parent') == report
    else:
        assert report['qualification'] == {'status': 'NOT_RUN'}
        assert (output/'job/gradient.log').is_file()
        with pytest.raises(ValueError): audit_recovered_gradients(parent, None, output)


@pytest.mark.parametrize('field', ['status', 'qualification', 'model_preserved', 'source_inputs_preserved', 'automatic_adoption'])
def test_unqualified_recovery_never_creates_an_attempt(tmp_path, monkeypatch, field):
    parent, _ = recovery_parent(tmp_path, monkeypatch)
    path = parent/'mixed_source_recovery.json'; value = json.loads(path.read_bytes())
    value[field] = {'status': 'REVIEW', 'qualification': {'mechanics_checks_pass': False},
                    'model_preserved': False, 'source_inputs_preserved': False, 'automatic_adoption': True}[field]
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError): audit_recovered_gradients(parent, None, tmp_path/'gradient')
    assert not (tmp_path/'gradient').exists()


@pytest.mark.parametrize('defect', ['worker', 'core', 'input', 'spec', 'parent', 'selection', 'adoption',
                                   'science', 'status', 'calls', 'max_calls', 'source_claim', 'extra'])
def test_rebound_preparation_or_scope_cannot_inherit_a_pass(tmp_path, monkeypatch, defect):
    from nasolve.cif_recovered_gradient import REPORT
    from nasolve.cif_mixed_gradient import _ref
    parent, _ = recovery_parent(tmp_path, monkeypatch); out = tmp_path/'gradient'
    report = audit_recovered_gradients(parent, None, out)
    paths = {'worker': 'job/gradient_worker.py', 'core': 'job/gradient_core.py',
             'input': report['preparation']['inputs'][0]['artifact']['path'], 'spec': 'job/gradient_spec.json'}
    if defect in paths:
        path = out/paths[defect]; path.write_bytes(path.read_bytes()+b' ')
    elif defect == 'parent':
        path = parent/'mixed_source_recovery.json'; value = json.loads(path.read_bytes())
        value['source_inputs_preserved'] = False; path.write_text(json.dumps(value))
    elif defect == 'selection': report['coordinate_selection'] = 'OLD_C95_ENDPOINT'
    elif defect == 'adoption': report['automatic_adoption'] = True
    elif defect == 'science': report['scientific_qualification'] = 'PASS'
    elif defect == 'status': report['status'] = 'RECOVERED_MIXED_DERIVATIVES_PASS'
    elif defect == 'calls': report['new_native_calls'] = True
    elif defect == 'max_calls': report['maximum_native_calls'] = True
    elif defect == 'source_claim': report['source_chemical_findings'] = 'ALL_CLEAR'
    elif defect == 'extra': (out/'unbound.json').write_text('{}')
    # Rebinding the outer inventory must not defeat recipe/parent validation.
    if defect != 'extra':
        report['outputs'] = [_ref(out/r['path'], out) for r in report['outputs']]
    (out/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError): read_recovered_gradients(out, recovery_directory=parent)


@pytest.mark.parametrize('defect', ['native_energy', 'manager', 'numeric_pin', 'numeric_repeat', 'cpp_bytes',
                                   'qualification', 'missing_qualification', 'sample', 'coordinates', 'executable', 'version'])
def test_completed_recovery_replays_numeric_evidence_after_rebinding(tmp_path, monkeypatch, defect):
    from nasolve.cif_recovered_gradient import REPORT
    from nasolve.cif_mixed_gradient import _ref
    parent, seed = recovery_parent(tmp_path, monkeypatch, sdk='correct'); out = tmp_path/'gradient'
    report = audit_recovered_gradients(parent, fake_phenix(parent, seed), out, timeout_seconds=30)
    assert report['status'] == 'RECOVERED_MIXED_DERIVATIVES_PASS'
    path = None
    if defect in {'native_energy', 'manager'}:
        path = out/'job/native_validation.json'; value = json.loads(path.read_bytes())
        if defect == 'native_energy': value['energy_inventory']['snapshots'][0]['target'] += 1.
        else: value['atoms'][0]['atom_id'] = 'CHANGED'
        path.write_text(json.dumps(value))
    elif defect == 'cpp_bytes':
        path = out/'job/installed_source/parallelity.h'; path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect == 'qualification':
        path = out/'qualification.json'; value = json.loads(path.read_bytes()); value['checks']['captured_raw_snapshot'] = False
        path.write_text(json.dumps(value)); report['qualification']['artifact'] = _ref(path, out)
    elif defect == 'missing_qualification':
        report['qualification'] = {'status': 'NOT_RUN'}; report['status'] = 'REVIEW'
    elif defect == 'executable': report['executable_sha256'] = '0'*64
    elif defect == 'version': report['phenix_version'] = 'DIFFERENT'
    else:
        path = out/'job/gradient_result.json'; value = json.loads(path.read_bytes())
        if defect == 'numeric_pin':
            for field in ['installed_numeric_sources', 'installed_numeric_sources_after']:
                next(r for r in value[field] if r['module'] == 'cctbx.geometry_restraints.flags')['sha256'] = '0'*64
        elif defect == 'numeric_repeat': value['installed_numeric_sources_after'][0]['sha256'] = '0'*64
        elif defect == 'coordinates': value['coordinates_unchanged'] = False
        elif defect == 'sample': value['gradient_audit']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target'] += 1.
        path.write_text(json.dumps(value))
    report['outputs'] = [_ref(out/r['path'], out) for r in report['outputs']]
    (out/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError): read_recovered_gradients(out, recovery_directory=parent)


@pytest.mark.parametrize('defect', ['version', 'executable'])
def test_different_consumer_rejected_before_output_or_launch(tmp_path, monkeypatch, defect):
    parent, _ = recovery_parent(tmp_path, monkeypatch); phenix = fake_phenix(parent, tmp_path)
    if defect == 'version': phenix.version = 'DIFFERENT'
    else:
        path = parent/'active_receipt.json'; value = json.loads(path.read_bytes()); value['executable_sha256'] = '0'*64
        path.write_text(json.dumps(value))
        from nasolve.cif_mixed_source_recovery import _ref
        source = parent/'mixed_source_recovery.json'; value = json.loads(source.read_bytes())
        value['native_captures']['linked']['active'] = _ref(path, parent); source.write_text(json.dumps(value))
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('Changed consumer launched'))
    with pytest.raises(ValueError): audit_recovered_gradients(parent, phenix, tmp_path/'gradient')
    assert not (tmp_path/'gradient').exists()


def test_launch_failure_has_no_native_call_and_retains_inspectable_preparation(tmp_path, monkeypatch):
    parent, _ = recovery_parent(tmp_path, monkeypatch)
    def fail(*args, **kwargs): raise OSError('EXPLICIT_FAKE launch failure')
    monkeypatch.setattr('subprocess.Popen', fail)
    report = audit_recovered_gradients(parent, fake_phenix(parent, tmp_path), tmp_path/'gradient')
    assert report['status'] == 'REVIEW' and report['new_native_calls'] == 0
    assert report['execution']['status'] == 'LAUNCH_FAILED'
    assert read_recovered_gradients(tmp_path/'gradient', recovery_directory=parent) == report
