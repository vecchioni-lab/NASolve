"""Recompute a saved fixed-scaffold trial without running captured code.

The caller verifies the parent capsule and supplies its genuine plane proof.
This adapter validates the new worker/source/input boundary, derivative data,
serialization and native readback before exposing a selected artifact.
"""
from collections import Counter
from hashlib import sha256
import ast
import json
import math
from pathlib import Path, PurePosixPath
import tempfile

from .cif_corrected_geometry import (FAMILIES, _close, _norm, _sampled_cases,
    replacement_manager_view, validate_gradient_qualification,
    validate_replacement_manager_bridge)
from .cif_gradient_audit import review_distance_groups
from .cif_fixed_geometry import (API_SOURCES as GEOMETRY_API_SOURCES, classify_stopping, qualify_fixed_policy_geometry,
    review_fixed_coordinates, write_geometry_candidate)
from .cif_captured_geometry import review_captured_geometry
from .cif_scaffold_candidate import select_scaffold_geometry

POLICY_ID = 'cif-saved-scaffold-geometry-replay-v1'
C59_SHA256 = '7a67af5579d5ea2cc260bff2e64dff35c45e21aa128ee53cde5f8e0107e8d777'
C60_SOURCE_SHA256 = {
    'src/nasolve/cif_replacement_geometry.py': '15f0c3f779a328332216bb04e7f8cad76297a931b9f92c65a9ee9fdb68da4642',
    'src/nasolve/cif_fixed_geometry.py': '6b87732f1ab9165531d297e633edc13f755c70a5cc350ff8ff51f75e4053db14',
    'src/nasolve/cif_native_validation.py': 'a80014965b04e224f0ac9b62ed5065c090fb2814893ef823855ef982f4ee34ce',
    'src/nasolve/cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f',
    'src/nasolve/cif_gradient_audit.py': 'a4d6571512313ae7ce8522668bd152ea806c5478803b74e296822bc313f275cc',
    'src/nasolve/cif_corrected_geometry.py': '319722394340b70c2c8a2d421e5f24f1a015c1b1c016324c2d492be9adc0c5c2',
}
C60_WORKER_SHA256 = {
    'replacement_gradient_worker.py': '05bd5ffb497982d0cd9d4258d3987ed2187ec5628dac75d90391667b29db1717',
    'geometry_worker.py': '348a28b7a85883eb1bdf6767a75cb4d6db6c500d82539ca734d8d7ea6ad9f47f',
    'native_worker.py': '9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78',
}
HELPER_SOURCES = {
    'correction_core.py': 'src/nasolve/cif_parallelity_correction.py',
    'gradient_core.py': 'src/nasolve/cif_gradient_audit.py',
    'corrected_geometry_core.py': 'src/nasolve/cif_corrected_geometry.py',
}


def _need(value, message):
    if not value:
        raise ValueError(message)


def _safe(name):
    return (isinstance(name, str) and not name.startswith('/') and '\\' not in name
        and ':' not in name and all(v not in {'', '.', '..'} for v in name.split('/')))


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'Duplicate saved JSON field')
        result[key] = value
    return result


def _json(members, name):
    _need(_safe(name), 'Unsafe saved JSON reference')
    return json.loads(members[name], object_pairs_hook=_unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite saved JSON constant')))


def _equivalent(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, float):
        return math.isfinite(left) and math.isfinite(right) and _close(left, right)
    if isinstance(left, dict):
        return set(left) == set(right) and all(_equivalent(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_equivalent(a, b) for a, b in zip(left, right))
    return left == right


def _runtime_sources(runtime_sources):
    """Optionally verify complete original sources; never import these bytes."""
    if runtime_sources is None:
        return {}
    _need(isinstance(runtime_sources, dict), 'Runtime sources must be an explicit byte mapping')
    result = {}
    for name, digest in C60_SOURCE_SHA256.items():
        data = runtime_sources.get(name)
        _need(type(data) is bytes and sha256(data).hexdigest() == digest,
            'Saved C60 runtime source differs: ' + name)
        result[name] = data
    for source, variable, worker in [
            ('cif_replacement_geometry.py', '_REPLACEMENT_WORKER', 'replacement_gradient_worker.py'),
            ('cif_fixed_geometry.py', '_GEOMETRY_WORKER', 'geometry_worker.py'),
            ('cif_native_validation.py', '_NATIVE_WORKER', 'native_worker.py')]:
        tree = ast.parse(result['src/nasolve/' + source])
        values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets)]
        _need(len(values) == 1 and isinstance(values[0], str)
            and sha256(values[0].encode()).hexdigest() == C60_WORKER_SHA256[worker],
            'Saved C60 worker/source binding differs')
    return result


def _artifact_rows(members, prefix, rows):
    _need(isinstance(rows, list) and len({row['path'] for row in rows}) == len(rows),
        'Duplicate or unavailable saved artifact inventory')
    for row in rows:
        name = row['path']
        _need(row.get('anchor') == 'native_directory' and _safe(name)
            and PurePosixPath(name).suffix not in {'.pkl', '.pickle'}, 'Unsafe saved artifact reference')
        data = members[prefix + '/' + name]
        _need(type(data) is bytes and len(data) == row['size']
            and sha256(data).hexdigest() == row['sha256'], 'Saved native artifact integrity differs')


def _worker_capture(members, native, capture, expected_inputs, *, receipt_name, worker_name, timeout):
    directory = native['directory']; prefix = directory['path']; execution = native['execution']
    _need(directory.get('anchor') == 'probe_directory' and _safe(prefix), 'Unsafe saved native directory')
    _need(native.get('status') == 'REVIEW' and execution.get('status') == 'COMPLETED'
        and execution.get('returncode') == 0 and execution.get('timeout_seconds') == timeout
        and native.get('source_preserved') is True and native.get('frozen_inputs_preserved') is True
        and native.get('phenix_version') == '2.2.1' and native.get('automatic_adoption') is False
        and native.get('scientific_approval') == 'NOT_RUN'
        and native['executable_sha256'] == capture['executable_sha256']
        and native['executable_provenance'] == capture['executable_provenance'],
        'Incomplete or changed saved native execution')
    _need(_json(members, prefix + '/' + receipt_name) == {k: v for k, v in native.items() if k != 'directory'},
        'Saved native receipt differs from its report')
    _artifact_rows(members, prefix, native['inputs']); _artifact_rows(members, prefix, native['outputs'])
    for name in {worker_name, 'native_worker.py'}:
        _need(sha256(members[prefix + '/' + name]).hexdigest() == C60_WORKER_SHA256[name],
            'Saved native worker source differs')
    inputs = native['inputs']
    _need([v.get('input_index') for v in inputs] == list(range(len(inputs)))
        and [(v['role'], members[prefix + '/' + v['path']]) for v in inputs] == expected_inputs,
        'Saved native scientific inputs differ from the qualified bundle')
    spec = {'policy_id': 'cif-native-bundle-inventory-v1', 'model': inputs[0]['path'],
        'dictionaries': [v['path'] for v in inputs if v['role'] == 'dictionary'],
        'phil_files': [v['path'] for v in inputs if v['role'] == 'phil'],
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1',
        'inventory_detail': 'linked', 'policy_inventory': True}
    _need(_json(members, prefix + '/native_spec.json') == spec, 'Saved native specification differs')
    return prefix


def _helpers(members, prefix, sources):
    for name, source in HELPER_SOURCES.items():
        data = members[prefix + '/' + name]
        _need(sha256(data).hexdigest() == C60_SOURCE_SHA256[source]
            and (not sources or data == sources[source]), 'Saved numerical helper source differs')


def validate_endpoint_derivatives(result, initial_proof, atom_count):
    """Recompute endpoint samples and additivity without imposing convergence."""
    validate_gradient_qualification(initial_proof, atom_count)
    _need(result.get('policy_id') == 'cif-fixed-na-corrected-geometry-trial-v1'
        and result.get('status') == 'REVIEW' and result.get('captured_inventory_matches') is True
        and result.get('qualified_initial_snapshot_matches') is True
        and result.get('policy_inventory') is True and result.get('normalization') is False
        and result.get('automatic_adoption') is False and result.get('starting_coordinates') == 'CAPTURED_INITIAL'
        and result.get('constraint_signature_before') == result.get('constraint_signature_after') == initial_proof['constraint_signature_before']
        and result.get('correction_policy_id') == initial_proof['correction_policy_id']
        and result.get('derivative_precondition') == 'SAMPLED_NATIVE_DERIVATIVES_PASS'
        and result.get('special_position_count') == 0, 'Saved trial lost its fixed initial qualification')
    for new, old in [('installed_optimizer_sources', 'installed_numeric_sources'),
            ('installed_adapter_sources', 'installed_adapter_sources'), ('installed_parallelity_sources', 'installed_parallelity_sources')]:
        _need(result[new] == initial_proof[old], 'Saved trial native numerical implementation differs')
    for key in ['target', 'gradient_norm']:
        _need(_close(result['initial'][key], initial_proof['cases']['initial']['families']['all']['baseline'][key]),
            'Saved trial initial corrected snapshot differs')
    audit = result['endpoint_gradient_audit']
    _need(audit.get('policy_id') == 'cif-fixed-native-gradient-audit-v1'
        and audit.get('analysis_completed') is True and audit.get('model_optimization') == 'NOT_RUN'
        and audit.get('automatic_adoption') is False and audit['selected_indices'] == initial_proof['selected_indices']
        and type(audit['evaluation_calls']) is int and type(audit['max_evaluation_calls']) is int
        and 0 < audit['evaluation_calls'] <= audit['max_evaluation_calls'] <= 4000
        and result.get('endpoint_derivative_qualification') == 'SAMPLED_NATIVE_DERIVATIVES_PASS',
        'Incomplete saved endpoint derivative evidence')
    _sampled_cases(audit, atom_count, {'full_precision', 'pdb_rounded'})
    for label, field in [('full_precision', 'final'), ('pdb_rounded', 'serialized')]:
        case = audit['cases'][label]; families = case['families']; baseline = families['all']['baseline']
        _need(all(_close(result[field][key], baseline[key]) for key in ['target', 'gradient_norm']),
            'Saved endpoint snapshot differs from its derivative audit')
        for family in families.values():
            b = family['baseline']
            values = [b['target'], family['repeat_target'], family['repeat_gradient_norm']]
            _need(all(type(x) in (int, float) and math.isfinite(x) for x in values)
                and _close(b['target'], family['repeat_target']) and _close(b['gradient_norm'], family['repeat_gradient_norm']),
                'Saved endpoint baseline repeats differ')
        total = math.fsum(families[name]['baseline']['target'] for name in FAMILIES[1:])
        _need(_close(total, baseline['target']) and _close(case['target_additivity']['all'], baseline['target'])
            and _close(case['target_additivity']['sum_controls'], total), 'Saved endpoint target additivity differs')
        summed = [math.fsum(families[name]['baseline']['gradient'][i] for name in FAMILIES[1:]) for i in range(3 * atom_count)]
        mismatch = _norm([a-b for a, b in zip(summed, baseline['gradient'])])
        _need(_close(mismatch, case['gradient_additivity']['difference_norm'])
            and mismatch <= 1e-8 + 1e-10 * max(1., baseline['gradient_norm']), 'Saved endpoint gradient additivity differs')
        comparisons = case['captured_snapshot_match']['comparisons']
        _need(set(comparisons) == {'target', 'gradient_norm'} and all(v['consistent'] is True
            and _close(v['captured'], result[field][key]) and _close(v['rebuilt'], baseline[key])
            for key, v in comparisons.items()), 'Saved endpoint reference comparisons differ')
    return True


def replay_scaffold_geometry(members, parent_proof, parent_inventory, *, runtime_sources=None):
    """Validate a completed C60 return and derive its automatic artifact choice.

    The parent C59 capsule must already be validated by the caller. Returned
    Python and serialized molecule objects are never imported or executed.
    """
    try:
        sources = _runtime_sources(runtime_sources)
        report = _json(members, 'probe_receipt.json'); audit = report['scaffold_geometry_audit']
        _need(audit == _json(members, 'scaffold_geometry_audit.json')
            and audit.get('policy_id') == 'cif-qualified-scaffold-geometry-trial-v1'
            and audit.get('scope') == 'SEPARATE_FULL_SCAFFOLD_GEOMETRY_TRIAL'
            and audit.get('native_execution') == 'SOURCE_NATIVE_SCAFFOLD_GEOMETRY_TRIAL'
            and audit.get('dictionary_generation') == 'NOT_RUN'
            and audit.get('model_optimization') == 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL'
            and audit.get('automatic_adoption') is False and audit.get('requires_cif_review') is False
            and audit.get('production_pipeline') == 'UNCHANGED' and audit.get('parent_qualification_replayed') is True,
            'Require complete separate saved scaffold geometry evidence')
        previous = _json(members, 'inputs/review/probe_receipt.json')['scaffold_candidate_audit']
        capture = previous['candidate']; before = capture['native_validation']; count = before['atom_count']
        _need(previous['decision']['selected_candidate'] == 'qualified_candidate'
            and audit['component'] == previous['component'] and audit['selected_sites'] == previous['selected_sites'],
            'Saved trial does not match the qualified component selection')
        parent_prefix = capture['directory']['path']
        _need(capture['directory'].get('anchor') == 'probe_directory' and _safe(parent_prefix), 'Unsafe qualified parent native directory')
        _artifact_rows(members, 'inputs/review/' + parent_prefix, capture['inputs'])
        original = [(v['role'], members['inputs/review/' + parent_prefix + '/' + v['path']]) for v in capture['inputs']]
        _need(original and original[0][0] == 'model' and Counter(role for role, _ in original)['model'] == 1
            and any(role == 'dictionary' for role, _ in original) and any(role == 'phil' for role, _ in original),
            'Qualified parent native resource scope differs')
        bridge = {'previous': replacement_manager_view(parent_inventory), 'replacement': replacement_manager_view(before)}
        validate_replacement_manager_bridge(bridge, parent_proof, count)
        plane_parent = audit['plane_parent']
        _need(plane_parent.get('anchor') == 'input_capsule' and _safe(plane_parent['path'])
            and sha256(members['inputs/review/' + plane_parent['path']]).hexdigest() == plane_parent['sha256']
            and _json(members, 'inputs/review/' + plane_parent['path']) == parent_proof,
            'Saved genuine plane-parent reference differs')
        plan = review_distance_groups(before, before['geometry']['sites_cart_exact'])
        _need(_equivalent(plan, audit['initial_probe_plan']) and plan == _json(members, 'initial_probe_plan.json'),
            'Saved derivative probe plan does not replay')
        significant = ['atoms', 'atom_count', 'monomer_mappings', 'geometry', 'installed_api_sources', 'restraint_policy']
        initial = audit['initial_audit']
        ip = _worker_capture(members, initial, capture, original, receipt_name='replacement_gradient_receipt.json',
            worker_name='replacement_gradient_worker.py', timeout=600)
        _helpers(members, ip, sources)
        proof = initial['result']
        _need(proof == _json(members, ip + '/replacement_gradient_result.json')
            and proof['parent_qualification'] == parent_proof and proof['manager_bridge'] == bridge
            and _json(members, ip + '/parent_gradient_qualification.json') == parent_proof
            and _json(members, ip + '/expected_inventory.json') == before,
            'Saved fresh initial derivative proof/input differs')
        validate_gradient_qualification(proof, count)
        _need(set(proof['cases']) == {'initial'} and initial['correction_core_sha256'] == C60_SOURCE_SHA256[HELPER_SOURCES['correction_core.py']],
            'Saved replacement initial proof scope or correction differs')
        expected_spec = {'policy_id': 'cif-replacement-manager-gradient-qualification-v1', 'manager_bridge': bridge,
            'selected_indices': plan['selected_indices'], 'max_calls': 2000}
        _need(_json(members, ip + '/replacement_gradient_spec.json') == expected_spec
            and proof['selected_indices'] == plan['selected_indices'] and proof['max_evaluation_calls'] == 2000
            and proof.get('preflight_native_evaluations') == 1, 'Saved initial derivative request differs')
        _need(all(_json(members, ip + '/native_validation.json').get(k) == before.get(k) for k in significant)
            and proof['raw_snapshot']['captured'] == {k: before['energy_inventory']['snapshots'][0][k] for k in ['target', 'gradient']},
            'Saved initial raw manager or snapshot differs')
        trial = audit['geometry_trial']
        tp = _worker_capture(members, trial, capture, original, receipt_name='geometry_receipt.json',
            worker_name='geometry_worker.py', timeout=600)
        _helpers(members, tp, sources)
        result = trial['result']
        _need(result == _json(members, tp + '/geometry_result.json')
            and _json(members, tp + '/expected_inventory.json') == before
            and _json(members, tp + '/gradient_validation.json') == proof
            and all(_json(members, tp + '/native_validation.json').get(k) == before.get(k) for k in significant),
            'Saved trial bootstrap or qualified input proof differs')
        validate_endpoint_derivatives(result, proof, count)
        geometry_spec = {'expected_inventory': 'expected_inventory.json', 'gradient_epsilon': 1e-5,
            'max_calls': 20000, 'max_iterations': 1000, 'native_spec': 'native_spec.json',
            'policy_id': 'cif-fixed-na-corrected-geometry-trial-v1', 'policy_inventory': True,
            'validated_correction': {'archive_sha256': C59_SHA256, 'correction_core_sha256': initial['correction_core_sha256']}}
        _need(_json(members, tp + '/geometry_spec.json') == geometry_spec
            and result['derivative_validation_archive'] == C59_SHA256
            and result['termination_parameters'] == {'max_calls': 20000, 'max_iterations': 1000,
                'traditional_convergence_test': True, 'traditional_convergence_test_eps': 1e-5},
            'Saved fixed trial policy, limits or lineage differs')
        _need(trial['convergence'] == audit['convergence'] == classify_stopping(result['stopping']),
            'Saved native stopping classification differs')
        for prefix in [ip, tp]:
            for row in parent_proof['installed_parallelity_sources']:
                data = members[prefix + '/installed_source/' + row['path']]
                _need(len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256'], 'Saved installed plane source differs')
        with tempfile.TemporaryDirectory(prefix='nasolve-scaffold-return-') as temporary:
            folder = Path(temporary).resolve(); model = folder / 'inputs/000_model.pdb'
            model.parent.mkdir(); model.write_bytes(original[0][1])
            candidate = folder / 'candidate/scaffold_geometry_model.pdb'
            serialization = write_geometry_candidate(model, candidate, before, result['final_sites_cart'])
            candidate_ref = 'geometry_candidate/scaffold_geometry_model.pdb'
            _need(candidate.read_bytes() == members[candidate_ref] and _equivalent(serialization, audit['serialization'])
                and audit['serialization'] == _json(members, 'geometry_serialization.json'), 'Saved coordinate serialization does not replay')
            full = review_fixed_coordinates(before, result['final_sites_cart'])
            _need(_equivalent(full, _json(members, 'full_precision_geometry_review.json'))
                and _equivalent(full['summary'], audit['full_precision_geometry_summary']), 'Saved full-precision geometry review differs')
            after = audit['native_roundtrip']
            ap = _worker_capture(members, after, capture, [('model', candidate.read_bytes()), *original[1:]],
                receipt_name='native_receipt.json', worker_name='native_worker.py', timeout=60)
            _need(after['native_validation'] == _json(members, ap + '/native_validation.json')
                and after.get('dictionary_source_policy') == 'EXPLICIT_DICTIONARIES'
                and after.get('phil_namespace_policy') == 'refinement-root-to-interpreter-v1'
                and after.get('symlink_outputs') == []
                and after.get('input_integrity') == [{'input_index': i, 'snapshot_preserved': True, 'source_preserved': True} for i in range(len(original))],
                'Saved serialized native inventory or consumer scope differs')
            mechanics = qualify_fixed_policy_geometry(before, after['native_validation'], candidate, serialization)
            _need(mechanics == audit['native_mechanics'] == _json(members, 'geometry_native_mechanics.json')
                and mechanics['mechanics_checks_pass'] is True and len(mechanics['checks']) == 17
                and all(v['status'] == 'PASS' for v in mechanics['checks']), 'Saved native endpoint mechanics do not replay')
            rounded = review_captured_geometry(after['native_validation'])
            _need(_equivalent(rounded, _json(members, 'rounded_native_geometry_review.json'))
                and _equivalent(rounded['summary'], audit['rounded_native_geometry_summary']), 'Saved rounded native geometry review differs')
            decision = select_scaffold_geometry(previous['qualification'], trial, mechanics, full, serialization,
                atom_count=count, rounded_geometry_review=rounded)
            _need(decision == audit['decision'] and decision['selected_candidate'] == 'qualified_geometry_endpoint'
                and decision['endpoint_usable'] is True, 'Saved automatic coordinate selection does not replay')
        for label, native in [('initial', _json(members, ip + '/native_validation.json')),
                ('trial', _json(members, tp + '/native_validation.json')), ('readback', after['native_validation'])]:
            _need(native['installed_api_sources'] == before['installed_api_sources'], 'Saved native API fingerprints differ: ' + label)
        native_root = Path(capture['executable_provenance']).parent.parent
        fingerprints = [{'anchor': 'phenix_installation', 'path': Path(v['historical_path']).relative_to(native_root).as_posix(),
            'sha256': v['sha256']} for v in before['installed_api_sources']]
        _need(report['installed_api_sources'] == fingerprints, 'Saved installed API source inventory differs')
        _need(after['api_sources'] == capture['api_sources'] and trial['api_sources'] == GEOMETRY_API_SOURCES,
            'Saved declared native API versions differ')
        return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'SAVED_SCAFFOLD_GEOMETRY_REPLAY_PASS',
            'component': audit['component'], 'selected_sites': audit['selected_sites'], 'atom_count': count,
            'initial_proof': proof, 'trial_result': result, 'native_roundtrip': after['native_validation'],
            'native_mechanics': mechanics, 'serialization': serialization, 'full_geometry_review': full,
            'rounded_geometry_review': rounded, 'decision': decision,
            'selected_model': {'anchor': 'input_capsule', 'path': candidate_ref,
                'sha256': serialization['candidate_sha256'], 'size': len(members[candidate_ref])},
            'starting_model': {'anchor': 'input_capsule', 'path': 'inputs/review/' + parent_prefix + '/' + capture['inputs'][0]['path'],
                'sha256': serialization['source_sha256'], 'size': len(original[0][1])},
            'captured_code_execution': 'NOT_RUN', 'new_native_execution': 'NOT_RUN',
            'model_optimization': 'NOT_RUN', 'automatic_adoption': False, 'requires_cif_review': False}
    except (KeyError, TypeError, IndexError, OSError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError('Incomplete saved scaffold geometry evidence: ' + str(exc)) from exc
