"""Recovered fixed-coordinate diagnostics cannot promote a failed endpoint."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import pytest
from nasolve.cif_recovered_torsion import audit_recovered_torsions, read_recovered_torsions, REPORT


def failed_parent(tmp_path, monkeypatch):
    from tests.test_cif_mixed_torsion import qualified_failed_endpoint_parent
    from tests.test_cif_recovered_geometry import qualified_parent
    from nasolve.cif_recovered_geometry import trial_recovered_geometry
    _, old_gradient, context, linked, sdk, phenix = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    with monkeypatch.context() as patch:
        patch.setattr('tests.test_cif_mixed_geometry.qualified_gradient_parent',
            lambda *a, **kw: (old_gradient, context, linked, sdk, phenix))
        gradient, parent, sdk, phenix = qualified_parent(tmp_path, monkeypatch)
    original = subprocess.Popen
    class FailedEndpoint:
        def __init__(self, process, job): self.process, self.job = process, job
        def __getattr__(self, name): return getattr(self.process, name)
        def wait(self, **kwargs):
            code = self.process.wait(**kwargs); assert code == 0
            path = self.job/'geometry_result.json'; value = json.loads(path.read_bytes())
            value['endpoint_derivative_qualification'] = 'DERIVATIVE_REVIEW'
            path.write_text(json.dumps(value)); return code
    geometry = tmp_path/'c100'
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, 'Popen', lambda *a, **kw: FailedEndpoint(original(*a, **kw), Path(kw['cwd'])))
        report = trial_recovered_geometry(gradient, parent, phenix, geometry, max_iterations=5, timeout_seconds=30)
    assert report['status'] == 'REVIEW'
    assert report['coordinate_decision']['selected'] == 'verified_recovered_model'
    return geometry, gradient, parent, sdk, phenix


@pytest.mark.parametrize('seconds', [0, 601, True, 1.5])
def test_bounds_precede_parent_reads_and_output_creation(tmp_path, seconds):
    with pytest.raises(ValueError):
        audit_recovered_torsions(tmp_path/'geometry', tmp_path/'gradient', tmp_path/'recovery', None, tmp_path/'out', timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode', ['prepare', 'complete', 'manager', 'source', 'timeout', 'missing_result', 'launch'])
def test_diagnostic_preserves_failed_endpoint_and_replays_without_sdk(tmp_path, monkeypatch, mode):
    from nasolve.cif_mixed_torsion import _WORKER
    from tests.test_cif_mixed_torsion import parent_files
    geometry, gradient, parent, sdk, phenix = failed_parent(tmp_path, monkeypatch)
    before = parent_files(geometry, gradient, parent)
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH'] = '1'
    if mode == 'source':
        path = sdk/'cctbx/geometry_restraints/__init__.py'; path.write_bytes(path.read_bytes()+b'\n# CHANGED\n')
    if mode == 'timeout': phenix.environment['EXPLICIT_C91_TIMEOUT'] = '1'
    if mode == 'launch':
        def fail(*a, **kw): raise OSError('EXPLICIT_LAUNCH_FAILURE')
        monkeypatch.setattr(subprocess, 'Popen', fail)
    if mode == 'missing_result':
        original = subprocess.Popen
        class MissingResult:
            def __init__(self, process, job): self.process, self.job = process, job
            def __getattr__(self, name): return getattr(self.process, name)
            def wait(self, **kwargs):
                code = self.process.wait(**kwargs); assert code == 0
                (self.job/'torsion_result.json').unlink(); return code
        monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: MissingResult(original(*a, **kw), Path(kw['cwd'])))
    out = tmp_path/'torsions'
    report = audit_recovered_torsions(geometry, gradient, parent, None if mode == 'prepare' else phenix, out,
        timeout_seconds=1 if mode == 'timeout' else 30)
    assert report['new_native_calls'] == (0 if mode in {'prepare','launch'} else 1)
    assert report['coordinate_decision']['selected'] == 'verified_recovered_model'
    assert report['original_geometry_qualification']['status'] == 'REVIEW'
    assert report['model_optimization'] == report['endpoint_requalification'] == 'NOT_RUN'
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert (out/'job/torsion_worker.py').read_text() == _WORKER
    assert not (out/'job/fake_optimizer_called').exists()
    assert all(p.read_bytes() == data for p, data in before.items())
    if mode == 'complete':
        assert report['status'] == 'RECOVERED_MIXED_TORSION_AUDIT_COMPLETE', report
        assert all(report['summary']['saved_family_matches'].values())
        assert all(row['local_sampled_agreement'] and row['group_attribution_consistent'] and row['group_sampled_agreement']
            for row in report['summary']['cases'].values())
    else:
        assert report['status'] == ('PREPARED_ONLY' if mode == 'prepare' else 'REVIEW')
        assert report['execution']['status'] == {'prepare':'NOT_RUN','manager':'FAILED','source':'FAILED','timeout':'TIMED_OUT',
            'missing_result':'COMPLETED','launch':'LAUNCH_FAILED'}[mode]
    moved = tmp_path/'relocated'; moved.mkdir()
    for name, path in [('geometry',geometry),('gradient',gradient),('recovery',parent),('torsions',out)]: path.rename(moved/name)
    import shutil
    shutil.rmtree(sdk)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('Reader launched native code'))
    assert read_recovered_torsions(moved/'torsions', geometry_directory=moved/'geometry',
        gradient_directory=moved/'gradient', recovery_directory=moved/'recovery') == report


@pytest.mark.parametrize('defect', ['version','executable','parent_result','prepared_parent'])
def test_wrong_consumer_or_incomplete_parent_cannot_start(tmp_path, monkeypatch, defect):
    geometry, gradient, parent, _, phenix = failed_parent(tmp_path, monkeypatch)
    if defect == 'version': phenix.version = 'CHANGED'
    elif defect == 'executable': phenix.executables['phenix.python'] = str(parent/'projected.cif')
    elif defect == 'parent_result':
        p = geometry/'job/geometry_result.json'; p.write_bytes(p.read_bytes()+b'CHANGED')
    else:
        from nasolve.cif_recovered_geometry import trial_recovered_geometry
        geometry = tmp_path/'prepared'
        trial_recovered_geometry(gradient, parent, None, geometry)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('Bad precondition launched'))
    with pytest.raises(ValueError): audit_recovered_torsions(geometry, gradient, parent, phenix, tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode', ['existing','symlink','inside_parent'])
def test_output_cannot_overwrite_or_enter_prior_attempts(tmp_path, mode):
    parents = [tmp_path/name for name in ['geometry','gradient','recovery']]
    for path in parents: path.mkdir()
    protected = tmp_path/'protected'; protected.mkdir(); (protected/'keep').write_text('KEEP')
    if mode == 'existing': out = protected
    elif mode == 'symlink':
        alias = tmp_path/'alias'; alias.symlink_to(protected, target_is_directory=True); out = alias/'out'
    else: out = parents[0]/'out'
    with pytest.raises(ValueError): audit_recovered_torsions(*parents, None, out)
    assert (protected/'keep').read_text() == 'KEEP'
    assert all(not (p/'out').exists() for p in parents)


@pytest.mark.parametrize('defect', ['worker','core','selection','spec','model','dictionary','decision','qualification',
    'endpoint','adoption','schema_bool','native_limit_bool','archive','scope','extra','parent_binding'])
def test_reader_rejects_rebound_recipe_scope_and_lineage(tmp_path, monkeypatch, defect):
    from nasolve.cif_mixed_torsion import _ref
    from tests.test_cif_mixed_torsion import rebind_artifact
    geometry, gradient, parent, _, _ = failed_parent(tmp_path, monkeypatch)
    out = tmp_path/'out'; report = audit_recovered_torsions(geometry, gradient, parent, None, out)
    paths = {'worker':'job/torsion_worker.py','core':'job/mixed_torsion_core.py',
        'selection':'torsion_selection.json','spec':'job/torsion_spec.json',
        'model':report['preparation']['inputs'][0]['artifact']['path'],
        'dictionary':report['preparation']['inputs'][1]['artifact']['path']}
    if defect in paths:
        p = out/paths[defect]; p.write_bytes(p.read_bytes()+b' ')
        rebind_artifact(report, paths[defect], p.read_bytes())
    elif defect == 'decision': report['coordinate_decision']['selected'] = 'qualified_geometry_endpoint'
    elif defect == 'qualification': report['original_geometry_qualification']['status'] = 'PASS'
    elif defect == 'endpoint': report['endpoint_requalification'] = 'PASS'
    elif defect == 'adoption': report['automatic_adoption'] = True
    elif defect == 'schema_bool': report['schema_version'] = True
    elif defect == 'native_limit_bool': report['maximum_native_calls'] = True
    elif defect == 'archive': report['parent_archive_sha256'] = '0'*64
    elif defect == 'scope': report['source_chemical_findings'] = 'CLEARED'
    elif defect == 'extra': (out/'unbound.json').write_text('{}')
    else: report['inputs']['geometry_result']['anchor'] = 'recovered_gradient_directory'
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('Reader launched'))
    with pytest.raises(ValueError): read_recovered_torsions(out, geometry_directory=geometry, gradient_directory=gradient, recovery_directory=parent)


@pytest.mark.parametrize('defect', ['consumer','counter','observation','saved_match','claim'])
def test_completed_receipt_cannot_forge_consumer_numerics_or_endpoint_pass(tmp_path, monkeypatch, defect):
    from tests.test_cif_mixed_torsion import rebind_artifact
    geometry, gradient, parent, _, phenix = failed_parent(tmp_path, monkeypatch)
    out = tmp_path/'out'; report = audit_recovered_torsions(geometry, gradient, parent, phenix, out, timeout_seconds=30)
    assert report['status'] == 'RECOVERED_MIXED_TORSION_AUDIT_COMPLETE'
    if defect == 'consumer': report['executable_sha256'] = '0'*64
    elif defect == 'counter': report['new_native_calls'] = 0
    elif defect == 'claim': report['endpoint_requalification'] = 'PASS'
    else:
        p = out/'job/torsion_result.json'; value = json.loads(p.read_bytes())
        if defect == 'observation': value['audit']['observations'][0]['value']['single_target'] += 1
        else: value['audit']['cases']['full_precision']['saved_family_match'] = False
        p.write_text(json.dumps(value)); rebind_artifact(report,'job/torsion_result.json',p.read_bytes())
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('Reader launched'))
    with pytest.raises(ValueError): read_recovered_torsions(out, geometry_directory=geometry, gradient_directory=gradient, recovery_directory=parent)
