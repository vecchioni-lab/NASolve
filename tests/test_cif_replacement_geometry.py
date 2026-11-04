"""A changed covalent objective needs its own initial derivative evidence."""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import pytest


def replacement_proof():
    from tests.test_cif_corrected_geometry import qualified_result
    from nasolve.cif_gradient_audit import audit_gradients, FAMILIES
    parent, count = qualified_result()
    points = [[float(i + 1), .25, -.5] for i in range(count)]
    weights = {f: i + 1 for i, f in enumerate(FAMILIES[1:])}
    def evaluate(x, family):
        w = sum(weights.values()) if family == 'all' else weights[family]
        return {'target': w * sum(v*v for p in x for v in p), 'gradient': [2*w*v for p in x for v in p]}
    raw = evaluate(points, 'all')
    audit = audit_gradients(evaluate, {'initial': points}, [0], references={'initial': {'target': raw['target']}}, max_calls=2000)
    numeric = ['scitbx.lbfgs', 'cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.manager', 'cctbx.geometry_restraints.energies', 'scitbx_lbfgs_ext', 'cctbx_geometry_restraints_ext']
    adapters = ['cctbx.geometry_restraints', 'cctbx.array_family.flex']
    rows = lambda names: [{'module': name, 'sha256': sha256(name.encode()).hexdigest()} for name in names]
    cpp = [{'path': name, 'status': 'RECORDED', 'bytes': 1, 'sha256': sha256(name.encode()).hexdigest()} for name in ['parallelity.h', 'parallelity_bpl.cpp']]
    for record in [parent, audit]:
        record.update(installed_numeric_sources=rows(numeric), installed_adapter_sources=rows(adapters), installed_parallelity_sources=deepcopy(cpp))
    proxies = [deepcopy(row['proxy']) for row in parent['plane_order_audit']['cases']['initial']['proxies']]
    parent['native_parallelity_proxies'] = deepcopy(proxies)
    atoms = [{'i_seq': i, 'atom_id': f'X{i}', 'label': f'atom_{i}', 'element': 'C',
              'identity': {'chain_id': 'A', 'resseq': '1', 'resname': 'ZZZ', 'icode': '', 'altloc': '', 'model_id': ''}} for i in range(count)]
    plane_rows = []
    for row in proxies:
        value = {k: v for k, v in row.items() if k != 'limit'}
        value['atoms'] = [atoms[i]['label'] for i in row['i_seqs']]
        value['j_atoms'] = [atoms[i]['label'] for i in row['j_seqs']]
        plane_rows.append(value)
    view = {'atom_count': count, 'atoms': atoms, 'planarity': [], 'parallelity': plane_rows,
        'restraint_policy': {'secondary_structure_enabled': False, 'origin_ids': {'hydrogen bonds': 1, 'edits': 2, 'basepair stacking': 3, 'basepair parallelity': 4, 'basepair planarity': 5}},
        'installed_api_sources': [{'module': 'native_api', 'sha256': 'a' * 64}]}
    audit.update(policy_id='cif-replacement-manager-gradient-qualification-v1', parent_qualification=parent,
        manager_bridge={'previous': deepcopy(view), 'replacement': deepcopy(view)},
        raw_snapshot={'captured': deepcopy(raw), 'rebuilt': deepcopy(raw)},
        native_parallelity_proxies=proxies, correction_policy_id='native-parallelity-both-first-planes-v1',
        correction_core_sha256='701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f',
        correction_qualification='SAMPLED_NATIVE_DERIVATIVES_PASS', plane_order_safe=True,
        normalization=False, captured_inventory_matches=True, constraint_signature_before='2' * 64,
        constraint_signature_after='2' * 64, correction_statistics={'max_energy_change': 0.})
    return audit, count


@pytest.mark.parametrize('defect', ['none', 'parent', 'recursive_parent', 'missing_initial', 'extra_case', 'gradient', 'sample',
    'raw_target', 'raw_gradient', 'raw_snapshot_target', 'planes', 'plane_weight', 'names', 'named_index', 'ss', 'api',
    'numeric_source', 'adapter_source', 'cpp_source', 'empty_sources', 'signature', 'correction', 'core', 'energy_change', 'evaluation_budget',
    'target_additivity', 'gradient_additivity', 'repeat', 'missing_target_comparison'])
def test_replacement_qualification_recomputes_parent_bridge_and_fresh_derivatives(defect):
    from nasolve.cif_corrected_geometry import validate_gradient_qualification
    q, count = replacement_proof()
    if defect == 'parent': q['parent_qualification']['correction_qualification'] = 'REVIEW'
    if defect == 'recursive_parent': q['parent_qualification']['policy_id'] = q['policy_id']
    if defect == 'missing_initial': q['cases'] = {}
    if defect == 'extra_case': q['cases']['pdb_rounded'] = deepcopy(q['cases']['initial'])
    if defect == 'gradient': q['cases']['initial']['families']['angle']['baseline']['gradient'][0] += 1
    if defect == 'sample': q['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target'] += 1
    if defect == 'raw_target': q['raw_snapshot']['rebuilt']['target'] += 1
    if defect == 'raw_gradient': q['raw_snapshot']['rebuilt']['gradient'][0] += 1
    if defect == 'raw_snapshot_target':
        q['raw_snapshot']['captured']['target'] += 1; q['raw_snapshot']['rebuilt']['target'] += 1
    if defect == 'planes': q['manager_bridge']['replacement']['parallelity'].pop()
    if defect == 'plane_weight': q['native_parallelity_proxies'][0]['weight'] *= 2
    if defect == 'names': q['manager_bridge']['replacement']['atoms'][0]['atom_id'] = 'Y'
    if defect == 'named_index':
        for v in q['manager_bridge'].values(): v['atoms'][0]['i_seq'] = 99
    if defect == 'ss': q['manager_bridge']['replacement']['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'api': q['manager_bridge']['replacement']['installed_api_sources'][0]['sha256'] = 'b' * 64
    if defect == 'numeric_source': q['installed_numeric_sources'][0]['sha256'] = '0' * 64
    if defect == 'adapter_source': q['installed_adapter_sources'][0]['sha256'] = '0' * 64
    if defect == 'cpp_source': q['installed_parallelity_sources'][0]['sha256'] = '0' * 64
    if defect == 'empty_sources': q['installed_numeric_sources'] = []
    if defect == 'signature': q['constraint_signature_after'] = '3' * 64
    if defect == 'correction': q['correction_policy_id'] = 'UNKNOWN'
    if defect == 'core': q['correction_core_sha256'] = '0' * 64
    if defect == 'energy_change': q['correction_statistics']['max_energy_change'] = .01
    if defect == 'evaluation_budget': q['max_evaluation_calls'] = 2001
    if defect == 'target_additivity': q['cases']['initial']['families']['angle']['baseline']['target'] += 1
    if defect == 'gradient_additivity': q['cases']['initial']['gradient_additivity']['difference_norm'] += 1
    if defect == 'repeat': q['cases']['initial']['families']['all']['repeat_target'] += 1
    if defect == 'missing_target_comparison': q['cases']['initial']['captured_snapshot_match']['comparisons'] = {}
    if defect == 'none': assert validate_gradient_qualification(q, count)
    else:
        with pytest.raises(ValueError): validate_gradient_qualification(q, count)


def fixture(tmp_path, monkeypatch, mode='converged'):
    from tests.test_cif_corrected_geometry import native_fixture
    from tests.test_cif_parallelity_audit import evaluate
    from nasolve.cif_candidate_usability import ENERGY_POLICY_ID
    model, dictionary, native, seed, config = native_fixture(tmp_path, monkeypatch, 'converged')
    native['installed_api_sources'] = [{'module': 'explicit_fake', 'sha256': 'a' * 64}]
    points = native['geometry']['sites_cart_exact']; proxy = native['geometry']['proxy_details']['parallelity'][0]
    proxy['atoms'] = [native['atoms'][i]['label'] for i in proxy['i_seqs']]
    proxy['j_atoms'] = [native['atoms'][i]['label'] for i in proxy['j_seqs']]
    plane = evaluate(points, proxy, broken=True)
    gradient = [12*v + g for p, gs in zip(points, [plane['accumulated_gradient'][i:i+3] for i in range(0, len(plane['accumulated_gradient']), 3)]) for v, g in zip(p, gs)]
    snapshot = {'target': 6 * sum(v*v for p in points for v in p) + plane['accumulated_target'], 'gradient': gradient, 'gradient_norm': math.sqrt(sum(g*g for g in gradient))}
    native['energy_inventory'] = {'policy_id': ENERGY_POLICY_ID, 'status': 'RECORDED', 'normalization': False, 'evaluation_calls': 2, 'snapshots': [snapshot, deepcopy(snapshot)]}
    if mode == 'raw':
        for row in native['energy_inventory']['snapshots']:
            row['gradient'][0] += 1; row['gradient_norm'] = math.sqrt(sum(g*g for g in row['gradient']))
    return model, dictionary, native, seed, config


@pytest.mark.parametrize('mode', ['pass', 'raw', 'source', 'planes', 'manager', 'derivative', 'budget', 'timeout'])
def test_fresh_native_replacement_audit_gates_existing_unchanged_trial(tmp_path, monkeypatch, mode):
    from nasolve.cif_replacement_geometry import run_initial_replacement_audit
    from nasolve.cif_fixed_geometry import run_fixed_geometry
    from nasolve.cif_corrected_geometry import validate_gradient_qualification
    import nasolve.cif_native_validation as native_module
    import nasolve.cif_replacement_geometry as replacement
    model, dictionary, native, seed, config = fixture(tmp_path, monkeypatch, mode)
    parent = deepcopy(native)
    if mode == 'source': config['result']['installed_numeric_sources'][0]['sha256'] = '0' * 64
    if mode == 'planes': parent['geometry']['proxy_details']['parallelity'][0]['weight'] *= 2
    if mode == 'manager': monkeypatch.setattr(native_module, '_NATIVE_WORKER', native_module._NATIVE_WORKER.replace("report=json.loads", "report=json.loads").replace("sites=flex.vec3_double", "report['atom_count']+=1\nsites=flex.vec3_double"))
    if mode == 'derivative':
        # This changes only the derivative, so a raw target check cannot detect it.
        monkeypatch.setattr(native_module, '_NATIVE_WORKER', native_module._NATIVE_WORKER.replace('2*coefficient*v', '3*coefficient*v'))
        # Match the altered raw snapshot; the fresh finite-difference check must fail.
        for row in native['energy_inventory']['snapshots']:
            row['gradient'] = [g + 6*v for g, v in zip(row['gradient'], [x for p in native['geometry']['sites_cart_exact'] for x in p])]
            row['gradient_norm'] = math.sqrt(sum(g*g for g in row['gradient']))
    if mode == 'timeout': monkeypatch.setattr(replacement, '_REPLACEMENT_WORKER', 'import time\ntime.sleep(30)\n')
    kwargs = dict(environment={**os.environ, 'PYTHONPATH': str(seed)}, phenix_version='EXPLICIT_FAKE', timeout_seconds=1 if mode == 'timeout' else 30, max_calls=10 if mode == 'budget' else 2000)
    if mode == 'planes':
        with pytest.raises(ValueError): run_initial_replacement_audit(model, [dictionary], [], native, config['result'], parent, [0], tmp_path/'audit', sys.executable, **kwargs)
        return
    r = run_initial_replacement_audit(model, [dictionary], [], native, config['result'], parent, [0], tmp_path/'audit', sys.executable, **kwargs)
    assert r['source_preserved'] and r['frozen_inputs_preserved']
    assert r['status'] == ('REVIEW' if mode == 'pass' else 'FAILED'), r
    if mode == 'timeout': assert r['execution']['status'] == 'TIMED_OUT'
    if mode != 'pass': return
    q = r['result']; assert set(q['cases']) == {'initial'} and validate_gradient_qualification(q, native['atom_count'])
    assert q['correction_statistics']['max_energy_change'] == 0 and q['evaluation_calls'] <= 2000
    trial = run_fixed_geometry(model, [dictionary], [], native, tmp_path/'trial', sys.executable,
        environment=kwargs['environment'], phenix_version='EXPLICIT_FAKE', max_iterations=5, timeout_seconds=30,
        policy_inventory=True, validated_correction={'result': q, 'archive_sha256': 'a' * 64, 'correction_core_sha256': r['correction_core_sha256']})
    assert trial['status'] == 'REVIEW', trial
    assert trial['result']['qualified_initial_snapshot_matches'] and trial['result']['endpoint_derivative_qualification'] == 'SAMPLED_NATIVE_DERIVATIVES_PASS'
