"""Fixed native torsion evidence remains separate from endpoint acceptance."""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess

import pytest

PARENT_SHA256 = 'c'*64


@pytest.mark.parametrize('seconds', [0, 601, True, 2.5])
def test_torsion_deadline_is_bounded_before_reading_parents_or_staging(tmp_path, seconds):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    output = tmp_path/'audit'
    with pytest.raises(ValueError):
        audit_mixed_torsions(tmp_path/'geometry', tmp_path/'gradient', tmp_path/'context',
            tmp_path/'linked', None, output, parent_archive_sha256=PARENT_SHA256, timeout_seconds=seconds)
    assert not output.exists()


@pytest.mark.parametrize('digest', ['', 'd'*63, 'g'*64, False, None])
def test_torsion_parent_archive_needs_exact_sha256_before_staging(tmp_path, digest):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    output = tmp_path/'audit'
    with pytest.raises(ValueError):
        audit_mixed_torsions(tmp_path/'geometry', tmp_path/'gradient', tmp_path/'context',
            tmp_path/'linked', None, output, parent_archive_sha256=digest)
    assert not output.exists()


def selection_fixture():
    """Disjoint native rows with independently controlled linearity and force."""
    points, rows = [], []
    for index in range(12):
        theta = math.radians(.5+index*.5)
        local = ([[-1., math.tan(theta), 0.], [0., 0., 0.], [1., 0., 0.], [1.6, .8, 1.1]]
            if index < 8 else [[0., 1., .2], [0., 0., 0.], [1.3, 0., 0.], [1.6, .8, 1.1]])
        offset = len(points); points.extend(local)
        rows.append({'i_seqs': list(range(offset, offset+4)), 'angle_ideal': 27.+index,
            'weight': .3, 'periodicity': 3, 'alt_angle_ideals': None, 'origin_id': index})
    expected = {'atom_count': len(points), 'geometry': {'sites_cart_exact': points,
        'proxy_details': {'dihedral': rows, 'const_dihedral': [], 'bond_simple': []}}}
    cases = {name: deepcopy(points) for name in ['initial', 'full_precision', 'pdb_rounded']}
    gradients = {name: [float(1+index//12) for index in range(3*len(points))] for name in cases}
    return expected, cases, gradients


def selected_keys(plan):
    return {(row['kind'], tuple(row['proxy']['i_seqs'])) for row in plan['selected']}


def test_selection_is_bounded_by_geometry_and_native_forces_without_component_exceptions():
    from nasolve.cif_mixed_torsion import select_torsions
    expected, cases, gradients = selection_fixture(); before = deepcopy((expected, cases, gradients))
    plan = select_torsions(expected, cases, gradients)
    assert (expected, cases, gradients) == before
    assert len(plan['eligible']) == 12 and len(plan['selected']) == 8
    assert {row['native_index'] for row in plan['selected']} == {0, 1, 2, 3, 4, 5, 10, 11}
    assert plan['truncated_near_count'] == 2
    assert all(row['kind'] == 'dihedral' for row in plan['selected'])
    assert len({tuple(row['proxy']['i_seqs']) for row in plan['selected']}) == 8
    expected['geometry']['proxy_details']['dihedral'].reverse()
    reordered = select_torsions(expected, cases, gradients)
    assert selected_keys(reordered) == selected_keys(plan)
    for row in reordered['selected']:
        original = expected['geometry']['proxy_details'][row['kind']][row['native_index']]
        assert row['proxy']['i_seqs'] == original['i_seqs']


def test_zero_weight_native_torsions_remain_in_inventory_but_are_never_probed():
    from nasolve.cif_mixed_torsion import select_torsions
    expected, cases, gradients = selection_fixture()
    expected['geometry']['proxy_details']['dihedral'][0]['weight'] = 0.
    plan = select_torsions(expected, cases, gradients)
    assert len(plan['eligible']) == 12 and plan['excluded_count'] == 1
    assert any(row['native_index'] == 0 and row['eligible'] is False for row in plan['eligible'])
    assert all(row['native_index'] != 0 for row in plan['selected'])


def test_constant_and_zero_weight_rows_are_accounted_for_without_becoming_ordinary_torsions():
    from nasolve.cif_mixed_torsion import select_torsions
    expected, cases, gradients = selection_fixture()
    constant = deepcopy(expected['geometry']['proxy_details']['dihedral'][0]); constant['periodicity'] = 0
    expected['geometry']['proxy_details']['const_dihedral'] = [constant, {**constant, 'weight': 0.}]
    plan = select_torsions(expected, cases, gradients)
    assert len(plan['eligible']) == 14 and plan['excluded_count'] == 2 and plan['positive_constant_count'] == 1
    assert all(row['kind'] == 'dihedral' for row in plan['selected'])


def analytic_fixture(*, biased=False, undefined=False):
    """Independent quadratic kernels; this is deliberately not torsion code."""
    points = [[0., 1., .2], [0., 0., 0.], [1.3, 0., 0.], [1.6, .8, 1.1]]
    if undefined: points = [[-1., 0., 0.], [0., 0., 0.], [1., 0., 0.], [2., 0., 0.]]
    cases = {name: deepcopy(points) for name in ['initial', 'full_precision', 'pdb_rounded']}
    proxy = {'i_seqs': [0, 1, 2, 3], 'angle_ideal': 27., 'weight': .3,
        'periodicity': 3, 'alt_angle_ideals': None, 'origin_id': 0}
    def evaluate(local, row, gradients):
        value = row['weight']*math.fsum(v*v for point in local for v in point)
        result = {'single_target': value, 'accumulated_target': value,
            'native_angle_defined': not undefined, 'native_angle_degrees': None if undefined else 42.}
        if gradients:
            force = [2*row['weight']*v for point in local for v in point]
            if biased: force[0] += 1.
            result.update(single_gradient=force, accumulated_gradient=force.copy())
        return result
    def groups(coordinates, group, gradients):
        weight = {'full': 9., 'selected': .3, 'remainder': 8.7, 'family': 9.}[group]
        result = {'target': weight*math.fsum(v*v for point in coordinates for v in point)}
        if gradients: result['gradient'] = [2*weight*v for point in coordinates for v in point]
        return result
    return cases, [proxy], evaluate, groups


@pytest.mark.parametrize('changes', [{'max_pairs': 0}, {'max_pairs': 10001},
    {'max_pairs': True}, {'max_group_calls': 0}, {'max_group_calls': 601}, {'max_group_calls': True}])
def test_torsion_evaluation_budgets_are_checked_before_any_kernel(changes):
    from nasolve.cif_mixed_torsion import audit_torsions
    cases, proxies, _, _ = analytic_fixture()
    def forbidden(*args, **kwargs): pytest.fail('invalid budget reached a native kernel')
    with pytest.raises(ValueError): audit_torsions(forbidden, forbidden, cases, proxies, **changes)


@pytest.mark.parametrize('changes', [{'max_pairs': 1}, {'max_group_calls': 1}])
def test_native_budget_exhaustion_cannot_create_a_complete_audit_or_mutate_inputs(changes):
    from nasolve.cif_mixed_torsion import audit_torsions
    cases, proxies, evaluate, groups = analytic_fixture(); before = deepcopy((cases, proxies))
    with pytest.raises(ValueError): audit_torsions(evaluate, groups, cases, proxies, **changes)
    assert (cases, proxies) == before


@pytest.mark.parametrize('mode', ['correct', 'wrong_gradient', 'undefined', 'native_exception'])
def test_fixed_coordinate_audit_preserves_failing_native_evidence_without_promoting_endpoints(mode):
    from nasolve.cif_mixed_torsion import audit_torsions, replay_torsions, STEPS
    cases, proxies, evaluate, groups = analytic_fixture(biased=mode == 'wrong_gradient', undefined=mode == 'undefined')
    before = deepcopy((cases, proxies))
    if mode == 'native_exception':
        def evaluate(*args): raise RuntimeError('EXPLICIT_NATIVE_KERNEL_FAILURE')
    result = audit_torsions(evaluate, groups, cases, proxies)
    assert result['analysis_completed'] and result['model_optimization'] == 'NOT_RUN'
    assert result['restraint_changes'] == 'NONE' and result['coordinate_model_written'] is False
    assert result['automatic_adoption'] is False and result['endpoint_requalification'] == 'NOT_RUN'
    assert (cases, proxies) == before
    assert result['evaluation_pairs'] <= 10000 and result['group_calls'] <= 600
    assert result['evaluation_pairs']+result['group_calls'] == len(result['observations'])
    assert tuple(STEPS) == (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9)
    for case in result['cases'].values():
        row = case['proxies'][0]
        assert set(row['orders']) == {'forward', 'reversed'}
        assert case['summary']['local_sampled_agreement'] is (mode == 'correct')
        for order in row['orders'].values():
            assert len(order['directions']) == (14 if mode in {'correct', 'wrong_gradient'} else 0)
            for direction in order['directions']:
                assert [sample['step'] for sample in direction['samples']] == list(STEPS)
        if mode == 'correct':
            assert all(case['attribution'].values())
            assert case['summary']['group_sampled_agreement']
    replay = replay_torsions(result, cases, proxies)
    assert replay['status'] == 'MIXED_TORSION_AUDIT_COMPLETE'
    assert replay['endpoint_requalification'] == 'NOT_RUN' and not replay['automatic_adoption']
    assert replay['summary'] == result['summary']


def test_finer_steps_resolve_a_sharp_smooth_potential_without_requalifying_failed_coarse_evidence():
    """An independent nonlinear potential makes coarse/fine behavior observable."""
    from nasolve.cif_mixed_torsion import audit_torsions, replay_torsions
    cases, proxies, _, _ = analytic_fixture()
    points = [[1e-5, 1., .2], [1e-5, 0., 0.], [1e-5, 1.3, 0.], [1e-5, 1.6, 1.1]]
    cases = {name: deepcopy(points) for name in cases}; before = deepcopy(cases)
    sigma = 1e-5
    def potential(coordinates, weight, gradients):
        exponentials = [math.exp(-(point[0]/sigma)**2) for point in coordinates]
        result = {'target': weight*math.fsum(exponentials)}
        if gradients:
            result['gradient'] = [value for point, exponential in zip(coordinates, exponentials)
                for value in [-2*weight*point[0]*exponential/(sigma*sigma), 0., 0.]]
        return result
    def local(coordinates, proxy, gradients):
        value = potential(coordinates, proxy['weight'], gradients)
        result = {'single_target': value['target'], 'accumulated_target': value['target'],
            'native_angle_defined': True, 'native_angle_degrees': 42.}
        if gradients: result.update(single_gradient=value['gradient'], accumulated_gradient=value['gradient'].copy())
        return result
    def groups(coordinates, group, gradients):
        return potential(coordinates, 0. if group == 'remainder' else proxies[0]['weight'], gradients)
    result = audit_torsions(local, groups, cases, proxies)
    assert cases == before and result['endpoint_requalification'] == 'NOT_RUN'
    assert result['automatic_adoption'] is False and result['restraint_changes'] == 'NONE'
    for case in result['cases'].values():
        for order in case['proxies'][0]['orders'].values():
            direction = next(row for row in order['directions'] if row['direction'] == 'atom_0_axis_0')
            assert all(not row['comparisons']['single']['consistent'] for row in direction['samples'][:4])
            assert all(row['comparisons']['single']['consistent'] for row in direction['samples'][4:6])
            assert direction['coarse_adjacent_agreement'] == {'single': False, 'accumulated': False}
            assert direction['fine_adjacent_agreement'] == {'single': True, 'accumulated': True}
        assert case['summary']['local_coarse_review_directions'] > 0
        assert case['summary']['local_fine_only_directions'] > 0
    replay = replay_torsions(result, cases, proxies)
    assert replay['status'] == 'MIXED_TORSION_AUDIT_COMPLETE'
    assert replay['endpoint_requalification'] == 'NOT_RUN' and not replay['automatic_adoption']


@pytest.mark.parametrize('defect', ['target', 'gradient', 'request', 'step', 'bound', 'summary',
    'attribution', 'drop_order', 'drop_observation', 'extra_observation', 'counter', 'adoption', 'endpoint'])
def test_saved_torsion_replay_recomputes_requests_both_orders_and_numerical_arithmetic(defect):
    from nasolve.cif_mixed_torsion import audit_torsions, replay_torsions
    cases, proxies, evaluate, groups = analytic_fixture()
    result = audit_torsions(evaluate, groups, cases, proxies)
    first = result['cases']['initial']['proxies'][0]['orders']['forward']
    if defect == 'target': result['observations'][0]['value']['single_target'] += 1.
    elif defect == 'gradient': result['observations'][0]['value']['single_gradient'][0] += 1.
    elif defect == 'request': result['observations'][0]['request']['points_sha256'] = 'd'*64
    elif defect == 'step': first['directions'][0]['samples'][0]['step'] *= 2.
    elif defect == 'bound': first['directions'][0]['samples'][0]['comparisons']['single']['bound'] *= 100.
    elif defect == 'summary': result['summary']['cases']['initial']['local_sampled_agreement'] = False
    elif defect == 'attribution': result['cases']['initial']['attribution']['selected_plus_remainder'] = False
    elif defect == 'drop_order': del result['cases']['initial']['proxies'][0]['orders']['reversed']
    elif defect == 'drop_observation': result['observations'].pop()
    elif defect == 'extra_observation': result['observations'].append(deepcopy(result['observations'][0]))
    elif defect == 'counter': result['evaluation_pairs'] += 1
    elif defect == 'adoption': result['automatic_adoption'] = True
    else: result['endpoint_requalification'] = 'PASS'
    with pytest.raises(ValueError): replay_torsions(result, cases, proxies)


@pytest.mark.parametrize('defect', ['case', 'count', 'nonfinite', 'indices', 'negative_weight', 'periodicity', 'gradient_count'])
def test_selector_refuses_incomplete_or_unsupported_native_data(defect):
    from nasolve.cif_mixed_torsion import select_torsions
    expected, cases, gradients = selection_fixture()
    row = expected['geometry']['proxy_details']['dihedral'][0]
    if defect == 'case': del cases['initial']
    elif defect == 'count': expected['atom_count'] += 1
    elif defect == 'nonfinite': cases['full_precision'][0][0] = float('nan')
    elif defect == 'indices': row['i_seqs'][3] = row['i_seqs'][0]
    elif defect == 'negative_weight': row['weight'] = -.1
    elif defect == 'periodicity': row['periodicity'] = 1.5
    else: gradients['initial'].pop()
    with pytest.raises(ValueError): select_torsions(expected, cases, gradients)


def qualified_failed_endpoint_parent(tmp_path, monkeypatch):
    """Extend the analytic SDK before its genuine initial audit/source binding.

    The C90 worker then runs unchanged. A deliberately bad finite-difference
    sample produces a valid retained REVIEW, with the complete failed endpoint
    preserved. C91 must inspect it without turning that endpoint into a pass.
    """
    from tests.test_cif_mixed_geometry import qualified_gradient_parent
    from tests.test_cif_dihedral_conditioning import _FAKE_DIHEDRAL_API
    import nasolve.cif_mixed_gradient as gradient_module
    from nasolve.cif_mixed_geometry import trial_mixed_geometry
    original_audit = gradient_module.audit_mixed_initial_gradients
    def add_torsion(context, linked, phenix, output, **kwargs):
        sdk = Path(phenix.environment['PYTHONPATH'])
        api = sdk/'cctbx/geometry_restraints/__init__.py'
        dihedral_api = _FAKE_DIHEDRAL_API.replace('    global TAMPER',
            "    import os,time\n    if os.environ.get('EXPLICIT_C91_TIMEOUT'):time.sleep(30)\n    global TAMPER")
        api.write_text(api.read_text()+dihedral_api)
        for name in ['dihedral.h', 'dihedral_bpl.cpp']:
            (api.parent/name).write_text('EXPLICIT_FAKE_'+name+'\n')
        proxy = {'i_seqs': [0, 1, 2, 3], 'angle_ideal': 27., 'weight': .3,
            'periodicity': 3, 'alt_angle_ideals': None, 'origin_id': 0}
        manager = sdk/'cctbx/geometry_restraints/manager.py'
        data = manager.read_text().replace('if getattr(flags,k))', "if k!='dihedral' and getattr(flags,k))")
        data = data.replace('        return NS(target=',
            '        torsion=gr.dihedral_residual_sum(sites_cart,self.dihedral_proxies,gradient) if flags.dihedral else 0.\n        return NS(target=')
        data = data.replace('+parallel,gradients=', '+parallel+torsion,gradients=')
        data += '\nGeo.dihedral_proxies=gr.shared_dihedral_proxy([gr.dihedral_proxy(**'+repr(proxy)+')])\n'
        manager.write_text(data)
        path = context/'saved_active.json'; native = json.loads(path.read_bytes())
        native['geometry']['proxy_details']['dihedral'] = [{**proxy,
            'atoms': [native['atoms'][i]['label'] for i in proxy['i_seqs']]}]
        native['geometry']['proxy_counts']['dihedral'] = 1
        points = native['geometry']['sites_cart_exact']; total = math.fsum(v*v for p in points for v in p)
        selected = math.fsum(v*v for p in points[:4] for v in p)
        for snapshot in native['energy_inventory']['snapshots']:
            snapshot['target'] += .3*selected-total
            snapshot['gradient'] = [g-2*v+(.6*v if i//3 < 4 else 0.)
                for i, (g, v) in enumerate(zip(snapshot['gradient'], [v for p in points for v in p]))]
            snapshot['gradient_norm'] = math.sqrt(math.fsum(v*v for v in snapshot['gradient']))
        for row in native['energy_inventory']['installed_sources']:
            row['sha256'] = sha256(Path(row['historical_path']).read_bytes()).hexdigest()
        path.write_text(json.dumps(native))
        return original_audit(context, linked, phenix, output, **kwargs)
    monkeypatch.setattr(gradient_module, 'audit_mixed_initial_gradients', add_torsion)
    gradient, context, linked, sdk, phenix = qualified_gradient_parent(tmp_path, monkeypatch)
    monkeypatch.setattr(gradient_module, 'audit_mixed_initial_gradients', original_audit)
    original_popen = subprocess.Popen
    class FailedEndpoint:
        def __init__(self, process, job): self.process, self.job = process, job
        def __getattr__(self, name): return getattr(self.process, name)
        def wait(self, **kwargs):
            code = self.process.wait(**kwargs); assert code == 0
            path = self.job/'geometry_result.json'; value = json.loads(path.read_bytes())
            value['endpoint_gradient_audit']['cases']['full_precision']['families']['dihedral']['directions'][0]['samples'][0]['plus_target'] += 1.
            path.write_text(json.dumps(value)); return code
    def controlled(*args, **kwargs): return FailedEndpoint(original_popen(*args, **kwargs), Path(kwargs['cwd']))
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, 'Popen', controlled)
        geometry = tmp_path/'geometry'
        report = trial_mixed_geometry(gradient, context, linked, phenix, geometry,
            parent_archive_sha256=PARENT_SHA256, max_iterations=5, timeout_seconds=30)
    assert report['status'] == 'REVIEW' and report['qualification']['status'] == 'REVIEW'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    return geometry, gradient, context, linked, sdk, phenix


def parent_files(*directories):
    return {path: path.read_bytes() for directory in directories
        for path in directory.rglob('*') if path.is_file()}


def test_genuine_failed_geometry_endpoint_can_be_inspected_and_relocated_without_sdk(tmp_path, monkeypatch):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions, read_mixed_torsions, _WORKER
    geometry, gradient, context, linked, sdk, _ = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    before = parent_files(geometry, gradient, context, linked)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('inspect launched an SDK'))
    output = tmp_path/'torsions'
    report = audit_mixed_torsions(geometry, gradient, context, linked, None, output, parent_archive_sha256=PARENT_SHA256)
    assert report['status'] == 'PREPARED_ONLY' and report['new_native_calls'] == 0
    assert report['maximum_native_calls'] == 1 and report['maximum_evaluation_pairs'] == 10000
    assert report['original_geometry_qualification']['status'] == 'REVIEW'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['endpoint_requalification'] == report['model_optimization'] == 'NOT_RUN'
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert (output/'job/torsion_worker.py').read_text() == _WORKER
    assert all(path.read_bytes() == data for path, data in before.items())
    moved = tmp_path/'moved'; moved.mkdir()
    for name, path in [('geometry', geometry), ('gradient', gradient), ('context', context), ('linked', linked), ('torsions', output)]: path.rename(moved/name)
    import shutil
    shutil.rmtree(sdk)
    assert read_mixed_torsions(moved/'torsions', geometry_directory=moved/'geometry', gradient_directory=moved/'gradient',
        context_directory=moved/'context', linked_parent_directory=moved/'linked', parent_archive_sha256=PARENT_SHA256) == report


@pytest.mark.parametrize('mode', ['correct', 'manager', 'source', 'timeout', 'missing_result'])
def test_new_owned_worker_checks_genuine_pinned_manager_and_never_optimizes(tmp_path, monkeypatch, mode):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions, read_mixed_torsions, _WORKER
    geometry, gradient, context, linked, sdk, phenix = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    before = parent_files(geometry, gradient, context, linked)
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH'] = '1'
    elif mode == 'source':
        api = sdk/'cctbx/geometry_restraints/__init__.py'; api.write_bytes(api.read_bytes()+b'\n# EXPLICIT_CHANGED_SDK_SOURCE\n')
    elif mode == 'timeout': phenix.environment['EXPLICIT_C91_TIMEOUT'] = '1'
    if mode == 'missing_result':
        original_popen = subprocess.Popen
        class MissingResult:
            def __init__(self, process, work): self.process, self.work = process, work
            def __getattr__(self, name): return getattr(self.process, name)
            def wait(self, **kwargs):
                code = self.process.wait(**kwargs); assert code == 0
                (self.work/'torsion_result.json').unlink(); return code
        monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: MissingResult(original_popen(*a, **kw), Path(kw['cwd'])))
    output = tmp_path/'torsions'
    report = audit_mixed_torsions(geometry, gradient, context, linked, phenix, output,
        parent_archive_sha256=PARENT_SHA256, timeout_seconds=1 if mode == 'timeout' else 30)
    assert report['new_native_calls'] == report['maximum_native_calls'] == 1
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['original_geometry_qualification']['status'] == 'REVIEW'
    assert report['endpoint_requalification'] == report['model_optimization'] == 'NOT_RUN'
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert (output/'job/torsion_worker.py').read_text() == _WORKER
    assert not (output/'job/fake_optimizer_called').exists()
    assert all(path.read_bytes() == data for path, data in before.items())
    if mode == 'correct':
        assert report['status'] == report['qualification']['status'] == 'MIXED_TORSION_AUDIT_COMPLETE', report
        assert all(row['local_sampled_agreement'] and row['group_attribution_consistent']
            and row['group_sampled_agreement'] for row in report['summary']['cases'].values())
        assert all(report['summary']['saved_family_matches'].values())
        moved = tmp_path/'relocated'; moved.mkdir()
        for name, path in [('geometry', geometry), ('gradient', gradient), ('context', context), ('linked', linked), ('torsions', output)]: path.rename(moved/name)
        import shutil
        shutil.rmtree(sdk)
        geometry, gradient, context, linked, output = [moved/name for name in ['geometry', 'gradient', 'context', 'linked', 'torsions']]
    else:
        assert report['status'] == 'REVIEW'
        assert report['execution']['status'] == ('TIMED_OUT' if mode == 'timeout' else 'COMPLETED' if mode == 'missing_result' else 'FAILED')
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('saved reader launched an SDK'))
    assert read_mixed_torsions(output, geometry_directory=geometry, gradient_directory=gradient,
        context_directory=context, linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256) == report


@pytest.mark.parametrize('mode', ['existing_output', 'symlink_output', 'inside_parent'])
def test_fresh_owned_torsion_output_cannot_overwrite_or_enter_parent_data(tmp_path, mode):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    parents = [tmp_path/name for name in ['geometry', 'gradient', 'context', 'linked']]
    for path in parents: path.mkdir()
    protected = tmp_path/'protected'; protected.mkdir(); sentinel = protected/'student.txt'; sentinel.write_bytes(b'KEEP')
    if mode == 'existing_output': output = protected
    elif mode == 'symlink_output':
        alias = tmp_path/'alias'; alias.symlink_to(protected, target_is_directory=True); output = alias/'audit'
    else: output = parents[0]/'audit'
    with pytest.raises(ValueError): audit_mixed_torsions(*parents, None, output, parent_archive_sha256=PARENT_SHA256)
    assert sentinel.read_bytes() == b'KEEP' and list(protected.iterdir()) == [sentinel]
    assert all(not (path/'audit').exists() for path in parents)


def test_optional_torsion_launch_failure_preserves_genuine_prior_fallback(tmp_path, monkeypatch):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions, read_mixed_torsions
    geometry, gradient, context, linked, _, phenix = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    before = parent_files(geometry, gradient, context, linked)
    def fail(*args, **kwargs): raise OSError('EXPLICIT_TORSION_LAUNCH_FAILURE')
    monkeypatch.setattr(subprocess, 'Popen', fail)
    output = tmp_path/'torsions'
    report = audit_mixed_torsions(geometry, gradient, context, linked, phenix, output, parent_archive_sha256=PARENT_SHA256)
    assert report['status'] == 'REVIEW' and report['new_native_calls'] == 0
    assert report['execution']['status'] == 'LAUNCH_FAILED'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['coordinate_decision']['continue_solving'] and not report['requires_cif_review']
    assert report['endpoint_requalification'] == report['model_optimization'] == 'NOT_RUN'
    assert all(path.read_bytes() == data for path, data in before.items())
    assert read_mixed_torsions(output, geometry_directory=geometry, gradient_directory=gradient,
        context_directory=context, linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256) == report


def rebind_artifact(report, relative, data):
    if isinstance(report, dict):
        if report.get('anchor') == 'mixed_torsion_directory' and report.get('path') == relative:
            report.update(size=len(data), sha256=sha256(data).hexdigest())
        for value in report.values(): rebind_artifact(value, relative, data)
    elif isinstance(report, list):
        for value in report: rebind_artifact(value, relative, data)


@pytest.mark.parametrize('defect', ['worker', 'core', 'selection', 'spec', 'model',
    'prior_decision', 'prior_qualification', 'endpoint', 'captured_code', 'schema_bool', 'native_limit_bool'])
def test_saved_torsion_reader_rejects_rebound_recipe_and_scope_tampering(tmp_path, monkeypatch, defect):
    from nasolve.cif_mixed_torsion import audit_mixed_torsions, read_mixed_torsions, REPORT
    geometry, gradient, context, linked, _, _ = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    output = tmp_path/'torsions'
    report = audit_mixed_torsions(geometry, gradient, context, linked, None, output, parent_archive_sha256=PARENT_SHA256)
    before = parent_files(geometry, gradient, context, linked)
    paths = {'worker': 'job/torsion_worker.py', 'core': 'job/mixed_torsion_core.py',
        'selection': 'torsion_selection.json', 'spec': 'job/torsion_spec.json',
        'model': report['preparation']['inputs'][0]['artifact']['path']}
    if defect in paths:
        relative = paths[defect]; path = output/relative
        if defect in {'selection', 'spec'}:
            data = json.loads(path.read_bytes())
            if defect == 'selection': data['selected'][0]['native_index'] += 1
            else: data['max_evaluation_pairs'] += 1
            path.write_text(json.dumps(data))
        else: path.write_bytes(path.read_bytes()+b'\nEXPLICIT_TAMPERED_BYTES\n')
        rebind_artifact(report, relative, path.read_bytes())
    elif defect == 'prior_decision': report['coordinate_decision']['selected'] = 'qualified_geometry_endpoint'
    elif defect == 'prior_qualification': report['original_geometry_qualification']['status'] = 'PASS'
    elif defect == 'endpoint': report['endpoint_requalification'] = 'PASS'
    elif defect == 'captured_code': report['captured_code_execution'] = 'RAN'
    elif defect == 'schema_bool': report['schema_version'] = True
    else: report['maximum_native_calls'] = True
    (output/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('saved reader ran an SDK'))
    with pytest.raises(ValueError):
        read_mixed_torsions(output, geometry_directory=geometry, gradient_directory=gradient,
            context_directory=context, linked_parent_directory=linked, parent_archive_sha256=PARENT_SHA256)
    assert all(path.read_bytes() == data for path, data in before.items())
