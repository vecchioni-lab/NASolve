"""Bounded mixed-model geometry, truthful gradient proof and automatic fallback."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

PARENT_SHA256 = 'c'*64


@pytest.mark.parametrize('changes', [
    {'max_iterations': 0}, {'max_iterations': 1001},
    {'timeout_seconds': 0}, {'timeout_seconds': 601},
])
def test_mixed_geometry_rejects_bad_bounds_before_reading_sources_or_creating_output(tmp_path, changes):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    output = tmp_path/'result'
    with pytest.raises(ValueError):
        trial_mixed_geometry(tmp_path/'gradient', tmp_path/'context', tmp_path/'parent',
            None, output, parent_archive_sha256=PARENT_SHA256, **changes)
    assert not output.exists()


def qualified_gradient_parent(tmp_path, monkeypatch, *, optimizer='limit'):
    """A genuine C89 analytic audit, followed by the same owned fake SDK.

    Only the explicit SDK and native inventory bootstrap are artificial. The
    maintained C89 worker, derivative evaluator and saved-evidence reader run.
    The C90 worker and optimizer call sequence remain the production sources.
    """
    from tests.test_cif_mixed_gradient import fake_sdk_parent
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients
    import nasolve.cif_native_validation as native_module
    context, linked, sdk = fake_sdk_parent(tmp_path, monkeypatch, 'correct')
    manager = sdk/'cctbx/geometry_restraints/manager.py'
    manager.write_text(manager.read_text()+'''\nGeo.crystal_symmetry=NS(unit_cell=lambda:NS(parameters=lambda:(50.,51.,52.,90.,90.,90.)),space_group_info=lambda:'P 1')\n''')
    lbfgs = sdk/'scitbx/lbfgs.py'
    if optimizer == 'timeout':
        lbfgs.write_text(lbfgs.read_text().replace('e=target_evaluator;e.compute_functional_and_gradients()',
            'import time;time.sleep(30)\n    e=target_evaluator;e.compute_functional_and_gradients()'))
    native = json.loads((context/'saved_active.json').read_bytes())
    native.update(automatic_adoption=False, scientific_approval='NOT_RUN', model_editing='NOT_RUN',
        optimization='NOT_RUN', dictionary_loading=[{'status': 'RECORDED'}])
    native['geometry']['sites_cart_exact'] = [[float(value) for value in point]
        for point in native['geometry']['sites_cart_exact']]
    for atom, point in zip(native['atoms'], native['geometry']['sites_cart_exact']):
        atom['xyz'] = list(point)
    for row in native['energy_inventory']['installed_sources']:
        row['sha256'] = sha256(Path(row['historical_path']).read_bytes()).hexdigest()
    (context/'saved_active.json').write_text(json.dumps(native))
    bootstrap = '''import json,os,math
from pathlib import Path
from cctbx.array_family import flex
from cctbx.geometry_restraints.flags import flags
from cctbx.geometry_restraints.manager import Geo
report=json.loads(Path(os.environ['EXPLICIT_FAKE_NATIVE']).read_text())
spec=json.loads(Path('native_spec.json').read_text())
lines=Path(spec['model']).read_bytes().splitlines()
points=[[float(line[i:i+8]) for i in (30,38,46)] for line in lines if line.startswith((b'ATOM  ',b'HETATM'))]
report['geometry']['sites_cart_exact']=points
for atom,point in zip(report['atoms'],points):atom['xyz']=point
if os.environ.get('EXPLICIT_C90_MISMATCH'):report['atoms'][0]['atom_id']='CHANGED'
sites=flex.vec3_double(points);geo=Geo()
e=geo.energies_sites(sites_cart=sites,flags=flags(default=True),compute_gradients=True,normalization=False)
gradient=[float(v) for v in e.gradients.as_double()]
snapshot={'target':float(e.target),'gradient':gradient,'gradient_norm':math.sqrt(math.fsum(v*v for v in gradient)),
    'terms':{'parallelity_residual_sum':float(e.parallelity_residual_sum)},'proxy_counts':{'n_parallelity_proxies':1}}
report['energy_inventory']['snapshots']=[snapshot,snapshot.copy()]
Path('native_validation.json').write_text(json.dumps(report))
'''
    monkeypatch.setattr(native_module, '_NATIVE_WORKER', bootstrap)
    phenix = NS(executables={'phenix.python': sys.executable}, version='EXPLICIT_FAKE_C90_SDK',
        environment={**os.environ, 'PYTHONPATH': str(sdk), 'EXPLICIT_FAKE_NATIVE': str(context/'saved_active.json')})
    gradient = tmp_path/'gradient'
    report = audit_mixed_initial_gradients(context, linked, phenix, gradient, timeout_seconds=30)
    assert report['status'] == 'MIXED_INITIAL_DERIVATIVES_PASS', report.get('error')
    return gradient, context, linked, sdk, phenix


def preserved_files(*directories):
    return {path: path.read_bytes() for directory in directories
        for path in directory.rglob('*') if path.is_file()}


def test_inspect_preserves_genuine_qualified_parent_and_relocates_without_an_sdk(tmp_path, monkeypatch):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry, read_mixed_geometry_trial
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    gradient, context, linked, sdk, _ = qualified_gradient_parent(tmp_path, monkeypatch)
    before = preserved_files(gradient, context, linked)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('inspect launched an SDK process'))
    output = tmp_path/'geometry'
    report = trial_mixed_geometry(gradient, context, linked, None, output, parent_archive_sha256=PARENT_SHA256)
    assert report['status'] == 'PREPARED_ONLY' and report['new_native_calls'] == 0
    assert report['maximum_native_calls'] == 2
    assert not report['requires_cif_review'] and not report['automatic_adoption']
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert all(path.read_bytes() == data for path, data in before.items())
    assert (output/'job/geometry_worker.py').read_text() == _GEOMETRY_WORKER
    moved = tmp_path/'relocated'; moved.mkdir()
    for name, path in [('gradient', gradient), ('context', context), ('linked', linked), ('geometry', output)]:
        path.rename(moved/name)
    import shutil
    shutil.rmtree(sdk)
    assert read_mixed_geometry_trial(moved/'geometry', gradient_directory=moved/'gradient',
        context_directory=moved/'context', linked_parent_directory=moved/'linked', parent_archive_sha256=PARENT_SHA256) == report


@pytest.mark.parametrize('changes', [
    {'max_iterations': True}, {'max_iterations': 2.5},
    {'timeout_seconds': True}, {'timeout_seconds': 2.5},
])
def test_mixed_geometry_bounds_require_integers_not_boolean_or_fractional(tmp_path, changes):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    output = tmp_path/'result'
    with pytest.raises(ValueError):
        trial_mixed_geometry(tmp_path/'gradient', tmp_path/'context', tmp_path/'parent',
            None, output, parent_archive_sha256=PARENT_SHA256, **changes)
    assert not output.exists()


def test_existing_geometry_output_is_never_overwritten(tmp_path, monkeypatch):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    existing = tmp_path/'keep'; existing.mkdir()
    for name in ['gradient', 'context', 'parent']: (tmp_path/name).mkdir()
    sentinel = existing/'user.txt'; sentinel.write_bytes(b'PRESERVE USER DATA')
    with pytest.raises((FileExistsError, ValueError)):
        trial_mixed_geometry(tmp_path/'gradient', tmp_path/'context', tmp_path/'parent', None, existing, parent_archive_sha256=PARENT_SHA256)
    assert sentinel.read_bytes() == b'PRESERVE USER DATA'
    assert list(existing.iterdir()) == [sentinel]


def test_geometry_output_cannot_traverse_a_symlink(tmp_path):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    protected = tmp_path/'protected'; protected.mkdir()
    for name in ['gradient', 'context', 'parent']: (tmp_path/name).mkdir()
    sentinel = protected/'user.txt'; sentinel.write_bytes(b'KEEP')
    alias = tmp_path/'alias'; alias.symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError):
        trial_mixed_geometry(tmp_path/'gradient', tmp_path/'context', tmp_path/'parent', None, alias/'geometry', parent_archive_sha256=PARENT_SHA256)
    assert sentinel.read_bytes() == b'KEEP'
    assert not (protected/'geometry').exists()


def test_geometry_launch_failure_keeps_usable_initial_model_without_student_approval(tmp_path, monkeypatch):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry, read_mixed_geometry_trial
    gradient, context, linked, _, phenix = qualified_gradient_parent(tmp_path, monkeypatch)
    before = preserved_files(gradient, context, linked)
    def failed(*args, **kwargs):
        raise OSError('EXPLICIT_FAKE_GEOMETRY_LAUNCH_FAILURE')
    monkeypatch.setattr('subprocess.Popen', failed)
    output = tmp_path/'geometry'
    result = trial_mixed_geometry(gradient, context, linked, phenix, output, parent_archive_sha256=PARENT_SHA256)
    assert result['status'] == 'REVIEW' and result['new_native_calls'] == 0
    assert result['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert result['coordinate_decision']['native_usable'] is True
    assert not result['automatic_adoption'] and not result['requires_cif_review']
    assert all(path.read_bytes() == data for path, data in before.items())
    assert read_mixed_geometry_trial(output, gradient_directory=gradient,
        context_directory=context, linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256) == result


@pytest.mark.parametrize('digest', ['', 'd'*63, 'g'*64, 42, False, None])
def test_parent_archive_binding_requires_an_explicit_sha256_before_any_staging(tmp_path, digest):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    output = tmp_path/'result'
    with pytest.raises(ValueError):
        trial_mixed_geometry(tmp_path/'gradient', tmp_path/'context', tmp_path/'parent',
            None, output, parent_archive_sha256=digest)
    assert not output.exists()


def endpoint_evidence():
    """Real finite-difference records for two independent endpoint encodings."""
    from nasolve.cif_gradient_audit import audit_gradients, FAMILIES
    from nasolve.cif_corrected_geometry import NUMERIC_MODULES, ADAPTER_MODULES
    from nasolve.cif_mixed_geometry import POLICY_ID
    from tests.test_cif_mixed_gradient import mixed_initial_result
    proof, expected = mixed_initial_result()
    points = [[value*.99 for value in point] for point in expected['geometry']['sites_cart_exact']]
    rounded = [[float(f'{value:.3f}') for value in point] for point in points]
    weights = {family: i+1 for i, family in enumerate(FAMILIES[1:])}
    def evaluate(coordinates, family):
        weight = sum(weights.values()) if family == 'all' else weights[family]
        return {'target': weight*sum(value*value for point in coordinates for value in point),
            'gradient': [2*weight*value for point in coordinates for value in point], 'proxy_counts': {}}
    def snapshot(coordinates):
        value = evaluate(coordinates, 'all')
        return {'target': value['target'], 'gradient_norm': sum(v*v for v in value['gradient'])**.5}
    final, serialized = snapshot(points), snapshot(rounded)
    references = {'full_precision': final, 'pdb_rounded': serialized}
    audit = audit_gradients(evaluate, {'full_precision': points, 'pdb_rounded': rounded},
        proof['selected_indices'], references=references, max_calls=4000)
    assert all(case['sampled_gradients_consistent'] for case in audit['cases'].values())
    def pins(names):
        return [{'module': name, 'historical_path': '/EXPLICIT_FAKE/'+name,
            'sha256': sha256(name.encode()).hexdigest()} for name in names]
    proof['installed_numeric_sources'] = pins(NUMERIC_MODULES)
    proof['installed_adapter_sources'] = pins(ADAPTER_MODULES)
    proof['installed_parallelity_sources'] = [{'path': name, 'bytes': 1, 'sha256': sha256(name.encode()).hexdigest(),
        'status': 'RECORDED'} for name in ['parallelity.h', 'parallelity_bpl.cpp']]
    baseline = proof['gradient_audit']['cases']['initial']['families']['all']['baseline']
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW',
        'captured_inventory_matches': True, 'qualified_initial_snapshot_matches': True,
        'policy_inventory': True, 'normalization': False, 'automatic_adoption': False,
        'scientific_approval': 'NOT_RUN', 'starting_coordinates': 'CAPTURED_INITIAL', 'special_position_count': 0,
        'constraint_signature_before': proof['constraint_signature_before'],
        'constraint_signature_after': proof['constraint_signature_after'],
        'correction_policy_id': proof['correction_policy_id'], 'derivative_precondition': 'SAMPLED_NATIVE_DERIVATIVES_PASS',
        'derivative_validation_archive': PARENT_SHA256,
        'installed_optimizer_sources': deepcopy(proof['installed_numeric_sources']),
        'installed_adapter_sources': deepcopy(proof['installed_adapter_sources']),
        'installed_parallelity_sources': deepcopy(proof['installed_parallelity_sources']),
        'initial': {k: baseline[k] for k in ['target', 'gradient_norm']},
        'final': final, 'serialized': serialized, 'final_sites_cart': points,
        'endpoint_gradient_audit': audit, 'endpoint_derivative_qualification': 'SAMPLED_NATIVE_DERIVATIVES_PASS',
        'termination_parameters': {'max_iterations': 5, 'max_calls': 100,
            'traditional_convergence_test': True, 'traditional_convergence_test_eps': 1e-5},
        'stopping': {'reason': 'max_iterations', 'error': None, 'iterations': 5,
            'calls': 3, 'max_iterations': 5, 'native_criterion_met': False}}
    return result, proof, len(points)


def test_endpoint_validator_accepts_finite_difference_proof_and_keeps_iteration_limit_separate():
    from nasolve.cif_mixed_geometry import _validate_endpoint
    result, proof, count = endpoint_evidence()
    before = deepcopy(result), deepcopy(proof)
    qualification = _validate_endpoint(result, proof, count, 5, PARENT_SHA256)
    assert qualification['status'] == 'ENDPOINT_DERIVATIVES_PASS'
    assert qualification['sampled_derivatives_pass'] is True
    assert qualification['stopping_classification'] == 'NOT_CONVERGED_LIMIT'
    assert qualification['scientific_qualification'] == 'NOT_ASSESSED'
    assert (result, proof) == before


@pytest.mark.parametrize('defect', ['policy', 'source_pin', 'signature', 'initial_snapshot', 'sample',
    'bound', 'additivity', 'gradient_additivity', 'snapshot_origin', 'endpoint_summary',
    'coordinates', 'budget', 'evaluation_count', 'step', 'atom_selection', 'history_case',
    'archive', 'iterations', 'termination', 'adoption', 'status'])
def test_endpoint_validator_rejects_written_pass_when_raw_numerical_evidence_changes(defect):
    from nasolve.cif_mixed_geometry import _validate_endpoint
    result, proof, count = endpoint_evidence()
    case = result['endpoint_gradient_audit']['cases']['full_precision']
    family = case['families']['all']
    if defect == 'policy': result['policy_id'] = 'UNRELATED_MODEL'
    elif defect == 'source_pin': result['installed_optimizer_sources'][0]['sha256'] = '0'*64
    elif defect == 'signature': result['constraint_signature_after'] = 'b'*64
    elif defect == 'initial_snapshot': result['initial']['target'] += 1.
    elif defect == 'sample': family['directions'][0]['samples'][0]['plus_target'] += 1.
    elif defect == 'bound': family['directions'][0]['samples'][0]['bound'] *= 100.
    elif defect == 'additivity': case['target_additivity']['sum_controls'] += 1.
    elif defect == 'gradient_additivity': case['gradient_additivity']['difference_norm'] += 1.
    elif defect == 'snapshot_origin': case['captured_snapshot_match']['comparisons']['target']['captured'] += 1.
    elif defect == 'endpoint_summary': result['serialized']['gradient_norm'] += 1.
    elif defect == 'coordinates': result['final_sites_cart'].pop()
    elif defect == 'budget': result['endpoint_gradient_audit']['max_evaluation_calls'] = 4001
    elif defect == 'evaluation_count': result['endpoint_gradient_audit']['evaluation_calls'] += 1
    elif defect == 'step': family['directions'][0]['samples'][0]['step'] *= 2.
    elif defect == 'atom_selection': result['endpoint_gradient_audit']['selected_indices'] = [1]
    elif defect == 'history_case': result['endpoint_gradient_audit']['cases']['initial'] = deepcopy(case)
    elif defect == 'archive': result['derivative_validation_archive'] = 'd'*64
    elif defect == 'iterations': result['stopping']['max_iterations'] += 1
    elif defect == 'termination': result['termination_parameters']['gradient_epsilon'] = .1
    elif defect == 'adoption': result['automatic_adoption'] = True
    else: result['status'] = 'APPROVED'
    with pytest.raises(ValueError): _validate_endpoint(result, proof, count, 5, PARENT_SHA256)


@pytest.mark.parametrize('stopping', ['NOT_CONVERGED_LIMIT', 'NOT_CONVERGED_ERROR', 'NOT_ASSESSED', 'NATIVE_CRITERION_MET'])
def test_usable_endpoint_selection_does_not_require_convergence_or_student_cif_review(stopping):
    from nasolve.cif_mixed_geometry import _decision
    checks = {'finite_coordinates': True, 'native_mechanics': True, 'endpoint_derivatives': True, 'fixed_objective_nonworse': True}
    decision = _decision(checks, stopping)
    assert decision['selected'] == 'qualified_geometry_endpoint'
    assert decision['continue_solving'] and decision['native_usable'] and decision['endpoint_usable']
    assert not decision['requires_cif_review'] and not decision['automatic_adoption']
    assert 'chirality' not in decision['checks'] and 'pucker' not in decision['checks']


@pytest.mark.parametrize('failed', ['finite_coordinates', 'native_mechanics', 'endpoint_derivatives', 'fixed_objective_nonworse'])
def test_unusable_optional_endpoint_automatically_retains_the_prequalified_start(failed):
    from nasolve.cif_mixed_geometry import _decision
    checks = {'finite_coordinates': True, 'native_mechanics': True, 'endpoint_derivatives': True, 'fixed_objective_nonworse': True}
    checks[failed] = False
    decision = _decision(checks, 'NOT_CONVERGED_LIMIT')
    assert decision['selected'] == 'verified_constructed_model' and decision['native_usable'] is True
    assert decision['endpoint_usable'] is False and decision['continue_solving'] is True
    assert not decision['requires_cif_review'] and not decision['automatic_adoption']


@pytest.mark.parametrize('mode', ['limit', 'manager', 'timeout'])
def test_owned_fake_sdk_runs_unchanged_worker_and_preserves_bounded_fallbacks(tmp_path, monkeypatch, mode):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry, read_mixed_geometry_trial
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    gradient, context, linked, sdk, phenix = qualified_gradient_parent(tmp_path, monkeypatch,
        optimizer='timeout' if mode == 'timeout' else 'limit')
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH'] = '1'
    before = preserved_files(gradient, context, linked)
    output = tmp_path/'geometry'
    report = trial_mixed_geometry(gradient, context, linked, phenix, output,
        parent_archive_sha256=PARENT_SHA256, max_iterations=5,
        timeout_seconds=1 if mode == 'timeout' else 30)
    assert (output/'job/geometry_worker.py').read_text() == _GEOMETRY_WORKER
    assert report['new_native_calls'] == (2 if mode == 'limit' else 1)
    assert report['status'] == ('MIXED_GEOMETRY_ENDPOINT_PASS' if mode == 'limit' else 'REVIEW'), report.get('optional_trial_finding')
    assert report['coordinate_decision']['selected'] == ('qualified_geometry_endpoint' if mode == 'limit' else 'verified_constructed_model')
    assert not report['requires_cif_review'] and not report['automatic_adoption']
    assert report['execution']['status'] == {'limit': 'COMPLETED', 'manager': 'FAILED', 'timeout': 'TIMED_OUT'}[mode]
    assert all(path.read_bytes() == data for path, data in before.items())
    assert read_mixed_geometry_trial(output, gradient_directory=gradient, context_directory=context,
        linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256) == report
    if mode == 'limit':
        assert report['geometry_summary']['stopping_classification'] == 'NOT_CONVERGED_LIMIT'
        assert report['geometry_summary']['final_target'] < report['geometry_summary']['initial_target']
        assert (output/'candidate/mixed_geometry_model.pdb').is_file()
        assert (output/'job/fake_optimizer_called').read_text() == 'EXPLICIT_FAKE'
        moved = tmp_path/'relocated'; moved.mkdir()
        for name, path in [('gradient', gradient), ('context', context), ('linked', linked), ('geometry', output)]: path.rename(moved/name)
        import shutil
        shutil.rmtree(sdk)
        monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('saved geometry reader launched an SDK'))
        assert read_mixed_geometry_trial(moved/'geometry', gradient_directory=moved/'gradient',
            context_directory=moved/'context', linked_parent_directory=moved/'linked', parent_archive_sha256=PARENT_SHA256) == report
    else:
        assert not (output/'candidate/mixed_geometry_model.pdb').exists()
        assert (output/'job/fake_optimizer_called').exists() is (mode == 'timeout')


@pytest.mark.parametrize('defect', ['missing_result', 'malformed_result', 'missing_native',
    'malformed_native', 'changed_manager'])
def test_exit_zero_with_unusable_worker_evidence_retains_start_without_second_sdk(tmp_path, monkeypatch, defect):
    """Even a successful process must supply complete, matching native evidence."""
    from nasolve.cif_mixed_geometry import trial_mixed_geometry, read_mixed_geometry_trial
    import subprocess
    gradient, context, linked, _, phenix = qualified_gradient_parent(tmp_path, monkeypatch)
    before = preserved_files(gradient, context, linked)
    original_popen = subprocess.Popen
    calls = []
    class CompletedWorker:
        def __init__(self, process, job): self.process, self.job = process, job
        def __getattr__(self, name): return getattr(self.process, name)
        def wait(self, **kwargs):
            code = self.process.wait(**kwargs)
            assert code == 0
            result = self.job/('geometry_result.json' if defect.endswith('result') else 'native_validation.json')
            if defect.startswith('missing'): result.unlink()
            elif defect.startswith('malformed'): result.write_text('{EXPLICIT_INVALID_JSON')
            else:
                data = json.loads(result.read_bytes()); data['atoms'][0]['atom_id'] = 'CHANGED'
                result.write_text(json.dumps(data))
            return code
    def controlled(*args, **kwargs):
        calls.append(args[0]); assert len(calls) == 1, 'unqualified result launched a second SDK'
        return CompletedWorker(original_popen(*args, **kwargs), Path(kwargs['cwd']))
    monkeypatch.setattr(subprocess, 'Popen', controlled)
    output = tmp_path/'geometry'
    report = trial_mixed_geometry(gradient, context, linked, phenix, output,
        parent_archive_sha256=PARENT_SHA256, max_iterations=5, timeout_seconds=30)
    assert report['execution']['status'] == 'COMPLETED' and report['execution']['returncode'] == 0
    assert report['status'] == 'REVIEW' and report['new_native_calls'] == 1 and len(calls) == 1
    assert report['qualification']['status'] == 'REVIEW'
    assert report['qualification']['sampled_derivatives_pass'] is False
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['coordinate_decision']['continue_solving'] is True
    assert report['native_readback'] == {'status': 'NOT_RUN'}
    assert not (output/'candidate/mixed_geometry_model.pdb').exists()
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert all(path.read_bytes() == data for path, data in before.items())
    assert read_mixed_geometry_trial(output, gradient_directory=gradient, context_directory=context,
        linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256) == report


def rebind_report_artifact(report, path, data):
    """Rebind altered bytes so tests reach recipe/proof checks, not hash mismatch."""
    if isinstance(report, dict):
        if report.get('path') == path and report.get('anchor') == 'mixed_geometry_directory':
            report.update(size=len(data), sha256=sha256(data).hexdigest())
        for value in report.values(): rebind_report_artifact(value, path, data)
    elif isinstance(report, list):
        for value in report: rebind_report_artifact(value, path, data)


@pytest.mark.parametrize('defect', ['worker', 'shim', 'raw_proof', 'expected_inventory',
    'model', 'wrapper', 'decision', 'archive'])
def test_saved_reader_reconstructs_owned_recipe_and_rejects_rebound_tampering(tmp_path, monkeypatch, defect):
    from nasolve.cif_mixed_geometry import trial_mixed_geometry, read_mixed_geometry_trial, REPORT
    gradient, context, linked, _, _ = qualified_gradient_parent(tmp_path, monkeypatch)
    output = tmp_path/'geometry'
    report = trial_mixed_geometry(gradient, context, linked, None, output, parent_archive_sha256=PARENT_SHA256)
    before = preserved_files(gradient, context, linked)
    paths = {'worker': 'job/geometry_worker.py', 'shim': 'job/corrected_geometry_core.py',
        'raw_proof': 'job/mixed_initial_result.json', 'expected_inventory': 'job/expected_inventory.json',
        'model': report['preparation']['inputs'][0]['artifact']['path'], 'wrapper': 'job/gradient_validation.json'}
    if defect in paths:
        path = paths[defect]; artifact = output/path
        if defect in {'raw_proof', 'expected_inventory', 'wrapper'}:
            data = json.loads(artifact.read_bytes())
            if defect == 'raw_proof': data['gradient_audit']['cases']['initial']['families']['all']['baseline']['target'] += 1
            elif defect == 'expected_inventory': data['atoms'][0]['atom_id'] = 'CHANGED'
            else: data['policy_id'] = 'cif-native-order-safe-plane-gradients-v1'
            artifact.write_text(json.dumps(data))
        else: artifact.write_bytes(artifact.read_bytes()+b'\nEXPLICIT_CHANGED_BYTES\n')
        rebind_report_artifact(report, path, artifact.read_bytes())
    elif defect == 'decision': report['coordinate_decision']['selected'] = 'qualified_geometry_endpoint'
    else: report['parent_archive_sha256'] = 'd'*64
    (output/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('saved reader launched an SDK'))
    with pytest.raises(ValueError):
        read_mixed_geometry_trial(output, gradient_directory=gradient, context_directory=context,
            linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256)
    assert all(path.read_bytes() == data for path, data in before.items())
