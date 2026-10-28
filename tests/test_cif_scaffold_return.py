"""Saved fixed-scaffold evidence is checked without executing captured workers."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest


def pinned_runtime():
    """Read exact C60 sources, including the historical native-capture fixture."""
    from nasolve.cif_scaffold_return import C60_SOURCE_SHA256
    repository = Path(__file__).parents[1]
    historical = repository / 'tests/fixtures/c60_runtime/cif_native_validation.py.txt'
    return {name: (historical if name == 'src/nasolve/cif_native_validation.py'
                   else repository / name).read_bytes() for name in C60_SOURCE_SHA256}


def test_saved_return_requires_exact_public_runtime_sources():
    from nasolve.cif_scaffold_return import _runtime_sources
    sources = pinned_runtime()
    assert _runtime_sources(sources)


def test_saved_c60_rejects_current_native_capture_api_as_historical_source():
    from nasolve.cif_scaffold_return import _runtime_sources
    sources = pinned_runtime()
    name = 'src/nasolve/cif_native_validation.py'
    sources[name] = (Path(__file__).parents[1] / name).read_bytes()
    with pytest.raises(ValueError, match='Saved C60 runtime source differs'):
        _runtime_sources(sources)


@pytest.mark.parametrize('defect', ['missing_source', 'changed_source', 'wrong_type'])
def test_saved_return_does_not_trust_worker_source_labels(defect):
    from nasolve.cif_scaffold_return import _runtime_sources
    sources = dict(pinned_runtime()); name = next(iter(sources))
    if defect == 'missing_source': sources.pop(name)
    if defect == 'changed_source': sources[name] += b'\n# altered implementation\n'
    if defect == 'wrong_type': sources[name] = sources[name].decode()
    with pytest.raises((ValueError, TypeError)):
        _runtime_sources(sources)


def test_saved_replay_requires_data_and_never_starts_a_native_worker(monkeypatch):
    from nasolve.cif_scaffold_return import replay_scaffold_geometry
    sources = pinned_runtime()
    def forbidden(*args, **kwargs):
        raise AssertionError('Read-only saved evidence replay started a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    with pytest.raises((ValueError, KeyError, TypeError)):
        replay_scaffold_geometry({}, {}, {}, runtime_sources=sources)


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def _literal(source, name):
    import ast
    tree = ast.parse(source)
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def saved_case(tmp_path, monkeypatch):
    """An explicit synthetic native capture; its quadratic FD proof is real.

    No generated worker is executed. The model and mechanics use eight named
    carbon atoms, and only the graph-selected probe plan is supplied by a fake.
    This fixture tests saved transport, proof wiring and exact manager readback.
    """
    from math import sqrt
    from nasolve import cif_scaffold_return as module
    from nasolve.cif_gradient_audit import audit_gradients, FAMILIES
    from nasolve.cif_fixed_geometry import write_geometry_candidate, review_fixed_coordinates, qualify_fixed_policy_geometry
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.cif_scaffold_candidate import select_scaffold_geometry
    from nasolve.cif_native_validation import API_SOURCES
    from tests.test_cif_replacement_geometry import replacement_proof
    sources = pinned_runtime(); q, count = replacement_proof(); parent = q['parent_qualification']
    points = [[float(i + 1), .25, -.5] for i in range(count)]
    end = [[round(v * .9, 3) for v in p] for p in points]
    view = q['manager_bridge']['previous']
    for atom in view['atoms']:
        atom['identity'].update(chain_id='B', resseq='4', resname='DP')
    api = [{'module': 'explicit_fake_native', 'historical_path': '/explicit_fake/phenix/lib/native.py', 'sha256': 'a' * 64}]
    view['installed_api_sources'] = api
    q['manager_bridge']['replacement'] = deepcopy(view)
    for record in [parent, q]:
        for row in record['installed_parallelity_sources']:
            row['bytes'] = len(row['path'].encode())
    q['preflight_native_evaluations'] = 1
    details = {name: [] for name in ['bond_simple', 'bond_asu', 'angle', 'dihedral', 'const_dihedral', 'chirality', 'planarity', 'parallelity']}
    details['parallelity'] = deepcopy(view['parallelity'])
    atoms = [{**deepcopy(atom), 'xyz': p} for atom, p in zip(view['atoms'], points)]
    raw = deepcopy(q['raw_snapshot']['captured']); raw['gradient_norm'] = sqrt(sum(g*g for g in raw['gradient']))
    before = {'schema_version': 1, 'policy_id': 'cif-native-bundle-inventory-v1', 'status': 'REVIEW',
        'inventory_detail': 'linked', 'fatal_problems': None, 'unused_definitions': [], 'unsupported_fields': [],
        'atoms': atoms, 'atom_count': count, 'installed_api_sources': api, 'restraint_policy': deepcopy(view['restraint_policy']),
        'monomer_mappings': {'rows': [{'site': 'B:4', 'resname': 'DP', 'metadata': {'group': 'DNA'}}]},
        'geometry': {'status': 'RECORDED', 'sites_cart_exact': points, 'simple_bonds': [], 'asu_bonds': [],
            'custom_proxy_requests': [], 'proxy_details': details, 'proxy_counts': {k: len(v) for k, v in details.items()}},
        'energy_inventory': {'policy_id': 'cif-fixed-native-usability-energy-v1', 'status': 'RECORDED',
            'normalization': False, 'evaluation_calls': 2, 'snapshots': [deepcopy(raw), deepcopy(raw)]}}
    # The signature is the real fixed-geometry worker's static proxy encoding.
    data = {'simple': [], 'asu': [], 'angle': [], 'dihedral': [], 'const_dihedral': [], 'chirality': [], 'planarity': [],
        'parallelity': [[p['i_seqs'], p.get('origin_id'), p['j_seqs'], p['weight'], p['target_angle_deg'], p['slack'], p['top_out']] for p in details['parallelity']]}
    signature = sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    q['constraint_signature_before'] = q['constraint_signature_after'] = signature
    # Frozen source declarations and the written PDB stay independent of workers.
    model = tmp_path / 'inputs/000_model.pdb'; model.parent.mkdir()
    model.write_text(''.join(f'HETATM{i+1:5d} {a["atom_id"]:>4}  DP B   4    {p[0]:8.3f}{p[1]:8.3f}{p[2]:8.3f}  1.00 20.00           C\n' for i, (a, p) in enumerate(zip(atoms, points))) + 'TER\nEND\n')
    candidate = tmp_path / 'written/scaffold_geometry_model.pdb'
    serialization = write_geometry_candidate(model, candidate, before, end)
    after = deepcopy(before)
    after['geometry']['sites_cart_exact'] = deepcopy(end)
    for atom, point in zip(after['atoms'], end): atom['xyz'] = list(point)
    full = review_fixed_coordinates(before, end); rounded = review_captured_geometry(after)
    mechanics = qualify_fixed_policy_geometry(before, after, candidate, serialization)
    assert mechanics['mechanics_checks_pass']
    weights = {family: i + 1 for i, family in enumerate(FAMILIES[1:])}
    def evaluate(values, family):
        weight = sum(weights.values()) if family == 'all' else weights[family]
        return {'target': weight * sum(v*v for p in values for v in p), 'gradient': [2*weight*v for p in values for v in p]}
    raw_endpoint = evaluate(end, 'all')
    endpoint_reference = {'target': raw_endpoint['target'], 'gradient_norm': sqrt(sum(g*g for g in raw_endpoint['gradient']))}
    audit = audit_gradients(evaluate, {'full_precision': end, 'pdb_rounded': end}, [0],
        references={key: endpoint_reference for key in ['full_precision', 'pdb_rounded']}, max_calls=4000)
    endpoint = audit['cases']['full_precision']['families']['all']['baseline']
    initial = q['cases']['initial']['families']['all']['baseline']
    stopping = {'calls': 1033, 'iterations': 1000, 'max_iterations': 1000, 'native_criterion_met': False, 'reason': 'max_iterations', 'error': None}
    result = {'schema_version': 1, 'status': 'REVIEW', 'policy_id': 'cif-fixed-na-corrected-geometry-trial-v1',
        'automatic_adoption': False, 'scientific_approval': 'NOT_RUN', 'normalization': False,
        'captured_inventory_matches': True, 'qualified_initial_snapshot_matches': True, 'policy_inventory': True,
        'starting_coordinates': 'CAPTURED_INITIAL', 'special_position_count': 0,
        'constraint_signature_before': signature, 'constraint_signature_after': signature,
        'correction_policy_id': 'native-parallelity-both-first-planes-v1',
        'derivative_validation_archive': '7a67af5579d5ea2cc260bff2e64dff35c45e21aa128ee53cde5f8e0107e8d777',
        'derivative_precondition': 'SAMPLED_NATIVE_DERIVATIVES_PASS', 'endpoint_derivative_qualification': 'SAMPLED_NATIVE_DERIVATIVES_PASS',
        'endpoint_gradient_audit': audit, 'initial': initial, 'final': endpoint, 'serialized': endpoint, 'final_sites_cart': end,
        'installed_optimizer_sources': deepcopy(q['installed_numeric_sources']), 'installed_adapter_sources': deepcopy(q['installed_adapter_sources']),
        'installed_parallelity_sources': deepcopy(q['installed_parallelity_sources']), 'stopping': stopping,
        'termination_parameters': {'max_calls': 20000, 'max_iterations': 1000, 'traditional_convergence_test': True, 'traditional_convergence_test_eps': 1e-5}}
    members = {}; expected_inputs = [('model', model.read_bytes())] + [('dictionary', f'data_fake_{i}\n'.encode()) for i in range(19)] + [('phil', f'# EXPLICIT_FAKE_NA_POLICY_{i}\n'.encode()) for i in range(14)]
    executable = '/explicit_fake/phenix/bin/phenix.python'; executable_sha = 'e' * 64
    def native_rows(prefix, values):
        rows = []
        for i, (role, contents) in enumerate(values):
            suffix = '.pdb' if role == 'model' else '.cif' if role == 'dictionary' else '.phil'
            path = f'inputs/{i:03d}_{role}' + suffix; members[prefix + '/' + path] = contents
            rows.append({'anchor': 'native_directory', 'input_index': i, 'role': role, 'path': path,
                'sha256': sha256(contents).hexdigest(), 'size': len(contents), 'source_provenance': '/explicit_fake/' + path})
        return rows
    capture_prefix = 'parent_native/fixture'; capture_inputs = native_rows('inputs/review/' + capture_prefix, expected_inputs)
    capture = {'directory': {'anchor': 'probe_directory', 'path': capture_prefix}, 'native_validation': before,
        'inputs': capture_inputs, 'executable_provenance': executable, 'executable_sha256': executable_sha,
        'phenix_version': '2.2.1', 'api_sources': API_SOURCES}
    initial_qualification = {'policy_id': 'cif-qualified-scaffold-candidate-v1', 'component': 'DP',
        'model_sha256': sha256(model.read_bytes()).hexdigest(), 'status': 'SCAFFOLD_CANDIDATE_MECHANICS_PASS',
        'native_usable': True, 'checks': [{'check': 'explicit_fake_passed_context', 'status': 'PASS'}]}
    prior = {'component': 'DP', 'selected_sites': ['B:4'], 'candidate': capture, 'qualification': initial_qualification,
        'decision': {'selected_candidate': 'qualified_candidate'}}
    members['inputs/review/probe_receipt.json'] = _json({'scaffold_candidate_audit': prior})
    native_text = _literal(sources['src/nasolve/cif_native_validation.py'], '_NATIVE_WORKER')
    geometry_text = _literal(sources['src/nasolve/cif_fixed_geometry.py'], '_GEOMETRY_WORKER')
    replacement_text = _literal(sources['src/nasolve/cif_replacement_geometry.py'], '_REPLACEMENT_WORKER')
    plans = {'selected_indices': [0], 'groups': [], 'scope': 'EXPLICIT_FAKE_TEST_PLAN'}
    monkeypatch.setattr(module, 'review_distance_groups', lambda *args: deepcopy(plans))
    def record(prefix, label, values, inventory, worker_name, worker, policy, audit_kind, outcome=None):
        inputs = native_rows(prefix, values)
        spec = {'policy_id': 'cif-native-bundle-inventory-v1', 'model': inputs[0]['path'],
            'dictionaries': [v['path'] for v in inputs if v['role'] == 'dictionary'], 'phil_files': [v['path'] for v in inputs if v['role'] == 'phil'],
            'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'inventory_detail': 'linked', 'policy_inventory': True}
        members[prefix + '/native_spec.json'] = _json(spec); members[prefix + '/native_worker.py'] = native_text.encode()
        members[prefix + '/native_validation.json'] = _json(inventory); members[prefix + '/' + worker_name] = worker.encode()
        receipt = {'schema_version': 1, 'policy_id': policy, 'audit_kind': audit_kind, 'status': 'REVIEW',
            'directory': {'anchor': 'probe_directory', 'path': prefix}, 'native_directory': '/explicit_fake/' + prefix,
            'source_preserved': True, 'frozen_inputs_preserved': True, 'automatic_adoption': False,
            'scientific_approval': 'NOT_RUN', 'phenix_version': '2.2.1', 'inputs': inputs,
            'executable_provenance': executable, 'executable_sha256': executable_sha,
            'execution': {'status': 'COMPLETED', 'returncode': 0, 'timeout_seconds': 60 if label == 'native_roundtrip' else 600},
            'api_sources': API_SOURCES, 'phil_namespace_policy': 'refinement-root-to-interpreter-v1',
            'dictionary_source_policy': 'EXPLICIT_DICTIONARIES', 'optimization': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'readyset_retry': 'NOT_RUN',
            'symlink_outputs': [], 'input_integrity': [{'input_index': i, 'source_preserved': True, 'snapshot_preserved': True} for i in range(len(inputs))]}
        if label == 'native_roundtrip': receipt['native_validation'] = inventory
        else:
            receipt['result'] = outcome
            members[prefix + '/expected_inventory.json'] = _json(before)
            for file, source_name in [('correction_core.py', 'cif_parallelity_correction.py'), ('gradient_core.py', 'cif_gradient_audit.py'), ('corrected_geometry_core.py', 'cif_corrected_geometry.py')]: members[prefix + '/' + file] = sources['src/nasolve/' + source_name]
            for row in q['installed_parallelity_sources']: members[prefix + '/installed_source/' + row['path']] = row['path'].encode()
        return receipt
    ip = 'initial_gradient/fixture'; tp = 'geometry_trial/fixture'; ap = 'readback/fixture'
    initial_record = record(ip, 'initial_audit', expected_inputs, before, 'replacement_gradient_worker.py', replacement_text,
        'cif-replacement-manager-gradient-qualification-v1', 'cif_replacement_initial_gradient_qualification', q)
    initial_record['correction_core_sha256'] = q['correction_core_sha256']; initial_record['model_optimization'] = 'NOT_RUN'
    members[ip + '/parent_gradient_qualification.json'] = _json(parent)
    members[ip + '/replacement_gradient_spec.json'] = _json({'policy_id': q['policy_id'], 'manager_bridge': q['manager_bridge'], 'selected_indices': [0], 'max_calls': 2000})
    members[ip + '/replacement_gradient_result.json'] = _json(q)
    trial = record(tp, 'geometry_trial', expected_inputs, before, 'geometry_worker.py', geometry_text,
        'cif-fixed-na-corrected-geometry-trial-v1', 'cif_fixed_native_corrected_geometry_trial', result)
    from nasolve.cif_fixed_geometry import API_SOURCES as GEOMETRY_API_SOURCES
    trial['policy_inventory'] = True; trial['convergence'] = 'NOT_CONVERGED_LIMIT'; trial['api_sources'] = GEOMETRY_API_SOURCES
    members[tp + '/gradient_validation.json'] = _json(q); members[tp + '/geometry_result.json'] = _json(result)
    members[tp + '/geometry_spec.json'] = _json({'policy_id': result['policy_id'], 'native_spec': 'native_spec.json', 'expected_inventory': 'expected_inventory.json',
        'max_calls': 20000, 'max_iterations': 1000, 'gradient_epsilon': 1e-5, 'policy_inventory': True,
        'validated_correction': {'archive_sha256': result['derivative_validation_archive'], 'correction_core_sha256': q['correction_core_sha256']}})
    readback = record(ap, 'native_roundtrip', [('model', candidate.read_bytes()), *expected_inputs[1:]], after, 'native_worker.py', native_text,
        'cif-native-bundle-inventory-v1', 'cif_native_bundle_inspection')
    def seal(receipt, prefix, receipt_name):
        receipt['outputs'] = [{'anchor': 'native_directory', 'path': n.removeprefix(prefix + '/'), 'sha256': sha256(contents).hexdigest(), 'size': len(contents)}
            for n, contents in sorted(members.items()) if n.startswith(prefix + '/') and n != prefix + '/' + receipt_name]
        members[prefix + '/' + receipt_name] = _json({k: v for k, v in receipt.items() if k != 'directory'})
    seal(initial_record, ip, 'replacement_gradient_receipt.json'); seal(trial, tp, 'geometry_receipt.json'); seal(readback, ap, 'native_receipt.json')
    decision = select_scaffold_geometry(initial_qualification, trial, mechanics, full, serialization, atom_count=count, rounded_geometry_review=rounded)
    assert decision['selected_candidate'] == 'qualified_geometry_endpoint'
    report = {'schema_version': 1, 'policy_id': 'cif-qualified-scaffold-geometry-trial-v1', 'scope': 'SEPARATE_FULL_SCAFFOLD_GEOMETRY_TRIAL',
        'component': 'DP', 'selected_sites': ['B:4'], 'initial_audit': initial_record, 'geometry_trial': trial, 'native_roundtrip': readback,
        'initial_probe_plan': plans, 'native_mechanics': mechanics, 'serialization': serialization, 'full_precision_geometry_summary': full['summary'],
        'rounded_native_geometry_summary': rounded['summary'], 'decision': decision, 'native_execution': 'SOURCE_NATIVE_SCAFFOLD_GEOMETRY_TRIAL',
        'model_optimization': 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL', 'dictionary_generation': 'NOT_RUN', 'automatic_adoption': False,
        'requires_cif_review': False, 'production_pipeline': 'UNCHANGED', 'parent_qualification_replayed': True,
        'plane_bridge': 'EXACT_NAMED_ATOMS_PLANES_PARALLELITIES_NA_POLICY_AND_APIS', 'plane_parent': {'anchor': 'input_capsule', 'path': 'explicit_fake_parent.json', 'sha256': sha256(_json(parent)).hexdigest()},
        'starting_coordinates': 'EXACT_C59_PDB_ROUNDED_ENDPOINT', 'objective': 'FIXED_C59_REPLACEMENT_DEFINITIONS; FRESH_TRIAL_NOT_OLD_OBJECTIVE_CONTINUATION',
        'convergence': 'NOT_CONVERGED_LIMIT', 'endpoint_derivative_qualification': 'SAMPLED_NATIVE_DERIVATIVES_PASS'}
    members.update({'initial_probe_plan.json': _json(plans), 'geometry_candidate/scaffold_geometry_model.pdb': candidate.read_bytes(),
        'geometry_serialization.json': _json(serialization), 'full_precision_geometry_review.json': _json(full), 'rounded_native_geometry_review.json': _json(rounded),
        'geometry_native_mechanics.json': _json(mechanics), 'scaffold_geometry_audit.json': _json(report), 'inputs/review/explicit_fake_parent.json': _json(parent),
        'probe_receipt.json': _json({'scaffold_geometry_audit': report,
            'installed_api_sources': [{'anchor': 'phenix_installation', 'path': 'lib/native.py', 'sha256': 'a' * 64}]})})
    return members, parent, deepcopy(before), report


def test_replays_owned_saved_capsule_without_running_captured_code(tmp_path, monkeypatch):
    from nasolve.cif_scaffold_return import replay_scaffold_geometry
    members, parent, inventory, _ = saved_case(tmp_path, monkeypatch)
    before = dict(members)
    def forbidden(*args, **kwargs): raise AssertionError('Saved replay executed a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    report = replay_scaffold_geometry(members, parent, inventory, runtime_sources=pinned_runtime())
    assert report['status'] == 'SAVED_SCAFFOLD_GEOMETRY_REPLAY_PASS'
    assert report['decision']['selected_candidate'] == 'qualified_geometry_endpoint'
    assert report['captured_code_execution'] == report['new_native_execution'] == 'NOT_RUN'
    assert members == before


def reseal(members, report):
    """Keep receipt integrity valid so mutations reach their semantic gates."""
    for label, receipt_name, result_name in [('initial_audit', 'replacement_gradient_receipt.json', 'replacement_gradient_result.json'),
            ('geometry_trial', 'geometry_receipt.json', 'geometry_result.json'), ('native_roundtrip', 'native_receipt.json', 'native_validation.json')]:
        native = report[label]; prefix = native['directory']['path']
        members[prefix + '/' + result_name] = _json(native['native_validation'] if label == 'native_roundtrip' else native['result'])
        native['outputs'] = [{'anchor': 'native_directory', 'path': n.removeprefix(prefix + '/'),
            'sha256': sha256(data).hexdigest(), 'size': len(data)} for n, data in sorted(members.items())
            if n.startswith(prefix + '/') and n != prefix + '/' + receipt_name]
        members[prefix + '/' + receipt_name] = _json({k: v for k, v in native.items() if k != 'directory'})
    header = json.loads(members['probe_receipt.json']); header['scaffold_geometry_audit'] = report
    members['probe_receipt.json'] = _json(header); members['scaffold_geometry_audit.json'] = _json(report)


@pytest.mark.parametrize('defect', ['worker', 'helper', 'namespace', 'pickle', 'role', 'initial_sample', 'extra_initial_case',
    'endpoint_sample', 'endpoint_target_sum', 'endpoint_gradient_sum', 'endpoint_repeat', 'endpoint_sources',
    'endpoint_case', 'endpoint_snapshot', 'endpoint_indices', 'signature', 'model_bytes', 'readback_definition',
    'readback_api', 'stopping_label', 'decision', 'unsafe_reference'])
def test_saved_return_rejects_semantically_changed_evidence_after_valid_receipt_hashes(tmp_path, monkeypatch, defect):
    from nasolve.cif_scaffold_return import replay_scaffold_geometry
    members, parent, inventory, report = saved_case(tmp_path, monkeypatch)
    initial = report['initial_audit']; trial = report['geometry_trial']; after = report['native_roundtrip']
    ip, tp = initial['directory']['path'], trial['directory']['path']; result = trial['result']
    if defect == 'worker': members[ip + '/replacement_gradient_worker.py'] += b'\n# altered worker\n'
    if defect == 'helper': members[ip + '/gradient_core.py'] += b'\n# altered helper\n'
    if defect == 'namespace':
        spec = json.loads(members[ip + '/native_spec.json']); spec['phil_namespace_policy'] = 'wrong'
        members[ip + '/native_spec.json'] = _json(spec)
    if defect == 'pickle': members[ip + '/forbidden.pkl'] = b'EXPLICIT SERIALIZED OBJECT NEVER LOADED'
    if defect == 'role': initial['inputs'][1]['role'] = 'phil'
    if defect == 'initial_sample': initial['result']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target'] += 1
    if defect == 'extra_initial_case': initial['result']['cases']['full_precision'] = deepcopy(initial['result']['cases']['initial'])
    if defect == 'endpoint_sample': result['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target'] += 1
    if defect == 'endpoint_target_sum': result['endpoint_gradient_audit']['cases']['full_precision']['target_additivity']['sum_controls'] += 1
    if defect == 'endpoint_gradient_sum': result['endpoint_gradient_audit']['cases']['full_precision']['gradient_additivity']['difference_norm'] += 1
    if defect == 'endpoint_repeat': result['endpoint_gradient_audit']['cases']['full_precision']['families']['angle']['repeat_target'] += 1
    if defect == 'endpoint_sources': result['installed_optimizer_sources'][0]['sha256'] = 'f' * 64
    if defect == 'endpoint_case': result['endpoint_gradient_audit']['cases'].pop('pdb_rounded')
    if defect == 'endpoint_snapshot': result['final']['target'] += 1
    if defect == 'endpoint_indices': result['endpoint_gradient_audit']['selected_indices'] = [1]
    if defect == 'signature': result['constraint_signature_after'] = 'f' * 64
    if defect == 'model_bytes': members['geometry_candidate/scaffold_geometry_model.pdb'] += b'\n# altered model\n'
    if defect == 'readback_definition': after['native_validation']['monomer_mappings']['rows'][0]['metadata']['group'] = 'other'
    if defect == 'readback_api': after['native_validation']['installed_api_sources'][0]['sha256'] = 'f' * 64
    if defect == 'stopping_label': trial['convergence'] = report['convergence'] = 'CONVERGED'
    if defect == 'decision': report['decision']['selected_candidate'] = 'verified_initial_scaffold'
    if defect == 'unsafe_reference': initial['inputs'][0]['path'] = '../escape.pdb'
    reseal(members, report)
    with pytest.raises(ValueError):
        replay_scaffold_geometry(members, parent, inventory, runtime_sources=pinned_runtime())


def test_saved_return_allows_native_nonconvergence_without_restarting_or_discarding_a_usable_endpoint(tmp_path, monkeypatch):
    from nasolve.cif_scaffold_return import replay_scaffold_geometry
    members, parent, inventory, report = saved_case(tmp_path, monkeypatch)
    report['geometry_trial']['result']['stopping'].update(reason='unreported', error='rounding errors prevent progress')
    report['convergence'] = report['geometry_trial']['convergence'] = 'NOT_CONVERGED_ERROR'
    reseal(members, report)
    replayed = replay_scaffold_geometry(members, parent, inventory)
    assert replayed['decision']['selected_candidate'] == 'qualified_geometry_endpoint'
    assert replayed['trial_result']['stopping']['error'] == 'rounding errors prevent progress'


def test_saved_return_rejects_duplicate_json_fields_before_using_data(tmp_path, monkeypatch):
    from nasolve.cif_scaffold_return import replay_scaffold_geometry
    members, parent, inventory, _ = saved_case(tmp_path, monkeypatch)
    members['probe_receipt.json'] = b'{"scaffold_geometry_audit":{},"scaffold_geometry_audit":{}}'
    with pytest.raises(ValueError, match='Duplicate'):
        replay_scaffold_geometry(members, parent, inventory)
