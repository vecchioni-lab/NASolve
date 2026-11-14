"""Saved ordinary activation replays resources and native evidence as data."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest


def readback_case(tmp_path):
    from tests.test_cif_runtime_bundle import case
    model, cifs, phils, decision, native, provenance = case(tmp_path)
    snapshot = deepcopy(provenance['trial']['result']['serialized'])
    native['energy_inventory']['snapshots'] = [deepcopy(snapshot), deepcopy(snapshot)]
    pins = [{'module': name, 'sha256': sha256(name.encode()).hexdigest(), 'historical_path': '/explicit_fake/phenix/lib/' + name + '.py'}
        for name in ['cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.energies', 'cctbx.geometry_restraints.manager']]
    native['energy_inventory']['installed_sources'] = deepcopy(pins)
    return model, cifs, phils, decision, native, provenance, pins


@pytest.mark.parametrize('defect', ['none', 'coordinate', 'definition', 'target', 'api', 'ss', 'repeat', 'nonfinite', 'reference', 'model'])
def test_ordinary_readback_rechecks_fixed_native_inventory_and_raw_objective(tmp_path, defect):
    from nasolve.cif_runtime_return import qualify_runtime_readback
    model, _, _, _, expected, provenance, _ = readback_case(tmp_path)
    native = deepcopy(expected); target = provenance['trial']['result']['serialized']['target']
    if defect == 'coordinate': native['atoms'][0]['xyz'][0] += .1
    if defect == 'definition': native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['changed'] = []
    if defect == 'target': native['geometry']['proxy_details']['bond_simple'][0]['distance_ideal'] += .1
    if defect == 'api': native['installed_api_sources'][0]['sha256'] = 'f' * 64
    if defect == 'ss': native['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'repeat': native['energy_inventory']['snapshots'][1]['target'] += 1
    if defect == 'nonfinite': native['energy_inventory']['snapshots'][0]['gradient'][0] = float('nan')
    if defect == 'reference': target += 1
    if defect == 'model':
        lines = model.read_bytes().splitlines(keepends=True); lines[0] = lines[0][:30] + b'  99.000' + lines[0][38:]
        model.write_bytes(b''.join(lines))
    report = qualify_runtime_readback(expected, native, model, target)
    assert len(report['checks']) == 14
    assert report['native_usable'] is (defect == 'none'), report
    assert report['model_optimization'] == 'NOT_RUN' and not report['requires_cif_review']


@pytest.mark.parametrize('defect', ['none', 'wrong_hash', 'missing', 'reordered'])
def test_ordinary_readback_requires_explicit_matching_energy_sources(tmp_path, defect):
    from nasolve.cif_runtime_return import qualify_runtime_readback
    model, _, _, _, expected, provenance, pins = readback_case(tmp_path)
    native = deepcopy(expected)
    if defect == 'wrong_hash': native['energy_inventory']['installed_sources'][0]['sha256'] = '0' * 64
    if defect == 'missing': native['energy_inventory']['installed_sources'].pop()
    if defect == 'reordered': native['energy_inventory']['installed_sources'].reverse()
    report = qualify_runtime_readback(expected, native, model, provenance['trial']['result']['serialized']['target'], energy_sources=pins)
    assert len(report['checks']) == 15
    assert report['native_usable'] is (defect == 'none')


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def runtime_case(tmp_path):
    """Build the ordinary bundle and assessment from public synthetic evidence."""
    from nasolve.cif_runtime_return import C60_SHA256, qualify_runtime_readback
    from nasolve.cif_runtime_bundle import prepare_runtime_bundle, assess_runtime_bundle
    from nasolve.cif_native_validation import _NATIVE_WORKER, API_SOURCES
    from nasolve.cif_candidate_usability import native_energy_worker
    selected, cifs, phils, decision, expected, provenance, pins = readback_case(tmp_path / 'original')
    api = [{'module': 'explicit_fake_native', 'historical_path': '/explicit_fake/phenix/lib/native.py', 'sha256': 'a' * 64}]
    for n in [expected, provenance['initial_native_validation']]:
        n['installed_api_sources'] = deepcopy(api)
        n['energy_inventory']['installed_sources'] = deepcopy(pins)
    extra = tmp_path / 'original/extra.phil'; extra.write_text('# EXPLICIT SECOND ORDERED PARAMETER RESOURCE\n'); phils.append(extra)
    members = {}; executable = '/explicit_fake/phenix/bin/phenix.python'; executable_sha = 'e' * 64
    def inputs(prefix, supplied):
        rows, paths = [], []
        for i, (role, source) in enumerate(supplied):
            suffix = '.pdb' if role == 'model' else '.cif' if role == 'dictionary' else '.phil'
            name = f'inputs/{i:03d}_{role}' + suffix; data = source.read_bytes()
            members[prefix + '/' + name] = data
            path = tmp_path / prefix / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); paths.append(path)
            rows.append({'anchor': 'native_directory', 'path': name, 'role': role, 'input_index': i,
                'sha256': sha256(data).hexdigest(), 'size': len(data), 'source_provenance': '/explicit_fake/' + name})
        return rows, paths
    cp = 'native_endpoint/fixture'; op = 'native_initial/fixture'
    capture_inputs, selected_paths = inputs('inputs/review/' + cp, [('model', selected), *[('dictionary', p) for p in cifs], *[('phil', p) for p in phils]])
    initial_inputs, initial_paths = inputs('inputs/review/inputs/review/' + op, [('model', provenance['initial_model'])])
    capture = {'directory': {'anchor': 'probe_directory', 'path': cp}, 'native_validation': expected,
        'inputs': capture_inputs, 'api_sources': deepcopy(API_SOURCES), 'executable_provenance': executable,
        'executable_sha256': executable_sha, 'phenix_version': '2.2.1'}
    old_capture = {'directory': {'anchor': 'probe_directory', 'path': op}, 'native_validation': provenance['initial_native_validation'], 'inputs': initial_inputs}
    old = {'component': 'ZZZ', 'selected_sites': ['A:2'], 'candidate': old_capture, 'qualification': provenance['initial_qualification']}
    parent = {'component': 'ZZZ', 'selected_sites': ['A:2'], 'native_roundtrip': capture, 'geometry_trial': provenance['trial'],
        'serialization': provenance['serialization'], 'decision': decision}
    members['inputs/review/inputs/review/scaffold_candidate_audit.json'] = _json(old)
    members['inputs/review/scaffold_geometry_audit.json'] = _json(parent)
    members['inputs/review/geometry_candidate/scaffold_geometry_model.pdb'] = selected.read_bytes()
    native_model, native_cifs, native_phils = selected_paths[0], selected_paths[1:2], selected_paths[2:]
    provenance.update(initial_model=initial_paths[0], source_archive={'sha256': C60_SHA256, 'delivery_prefix': '60_Cedar'},
        source_inputs=[{key: row[key] for key in ['role', 'sha256', 'size']} for row in capture_inputs])
    bundle = tmp_path / 'activated_bundle'
    activation = prepare_runtime_bundle(native_model, native_cifs, native_phils, bundle, decision=decision, native_validation=expected, provenance=provenance)
    assessment = assess_runtime_bundle(bundle)
    for path in bundle.rglob('*'):
        if path.is_file(): members['activated_bundle/' + path.relative_to(bundle).as_posix()] = path.read_bytes()
    selected_ref = {'anchor': 'input_capsule', 'path': 'geometry_candidate/scaffold_geometry_model.pdb', 'sha256': sha256(selected.read_bytes()).hexdigest(), 'size': selected.stat().st_size}
    starting_ref = {'anchor': 'input_capsule', 'path': 'inputs/review/' + op + '/' + initial_inputs[0]['path'],
        'sha256': sha256(initial_paths[0].read_bytes()).hexdigest(), 'size': initial_paths[0].stat().st_size}
    replay = {'policy_id': 'cif-saved-scaffold-geometry-replay-v1', 'status': 'SAVED_SCAFFOLD_GEOMETRY_REPLAY_PASS',
        'component': 'ZZZ', 'selected_sites': ['A:2'], 'atom_count': expected['atom_count'], 'decision': decision,
        'selected_model': selected_ref, 'starting_model': starting_ref, 'captured_code_execution': 'NOT_RUN'}
    np = 'native_activated/fixture'
    after_inputs, _ = inputs(np, [('model', bundle / activation['resources']['model']['relative_path']),
        *[('dictionary', bundle / row['relative_path']) for row in activation['resources']['dictionaries']],
        *[('phil', bundle / row['relative_path']) for row in activation['resources']['phils']]])
    spec = {'policy_id': 'cif-native-bundle-inventory-v1', 'model': after_inputs[0]['path'],
        'dictionaries': [row['path'] for row in after_inputs if row['role'] == 'dictionary'],
        'phil_files': [row['path'] for row in after_inputs if row['role'] == 'phil'],
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'inventory_detail': 'linked', 'policy_inventory': True, 'energy_inventory': True}
    members[np + '/native_spec.json'] = _json(spec); members[np + '/native_worker.py'] = native_energy_worker(_NATIVE_WORKER).encode()
    members[np + '/native_validation.json'] = _json(expected)
    native = {'schema_version': 1, 'policy_id': 'cif-native-bundle-inventory-v1', 'audit_kind': 'cif_native_bundle_inspection',
        'directory': {'anchor': 'probe_directory', 'path': np}, 'native_directory': '/explicit_fake/' + np,
        'native_validation': expected, 'inputs': after_inputs, 'api_sources': deepcopy(API_SOURCES),
        'source_preserved': True, 'frozen_inputs_preserved': True, 'automatic_adoption': False, 'scientific_approval': 'NOT_RUN',
        'status': 'REVIEW', 'phenix_version': '2.2.1', 'executable_provenance': executable, 'executable_sha256': executable_sha,
        'execution': {'status': 'COMPLETED', 'returncode': 0, 'timeout_seconds': 60},
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'dictionary_source_policy': 'EXPLICIT_DICTIONARIES',
        'symlink_outputs': [], 'optimization': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'readyset_retry': 'NOT_RUN',
        'input_integrity': [{'input_index': i, 'snapshot_preserved': True, 'source_preserved': True} for i in range(len(after_inputs))]}
    native['outputs'] = [{'anchor': 'native_directory', 'path': name.removeprefix(np + '/'), 'sha256': sha256(data).hexdigest(), 'size': len(data)}
        for name, data in sorted(members.items()) if name.startswith(np + '/')]
    members[np + '/native_receipt.json'] = _json({key: value for key, value in native.items() if key != 'directory'})
    qualification = qualify_runtime_readback(expected, expected, bundle / activation['resources']['model']['relative_path'],
        parent['geometry_trial']['result']['serialized']['target'], energy_sources=pins)
    assert qualification['native_usable']
    manifest_path = 'activated_bundle/' + activation['manifest_file']
    audit = {'schema_version': 1, 'policy_id': 'cif-runtime-bundle-activation-trial-v1', 'scope': 'SEPARATE_PORTABLE_RUNTIME_BUNDLE',
        'component': 'ZZZ', 'selected_sites': ['A:2'], 'source_return_replayed': replay,
        'manifest': {'anchor': 'probe_directory', 'path': manifest_path, 'sha256': sha256(members[manifest_path]).hexdigest()},
        'activation': activation, 'ordinary_assessment': {'anchor': 'probe_directory', 'path': 'ordinary_bundle_assessment.json'},
        'ordinary_reader': 'resolve_runtime_bundle', 'ordinary_cli': 'nasolve cif-doctor assess --bundle PATH',
        'native_readback': native, 'native_qualification': qualification, 'native_execution': 'QUALIFIED_RUNTIME_BUNDLE_READBACK',
        'dictionary_generation': 'NOT_RUN', 'model_optimization': 'NOT_RUN', 'production_checkpoint': 'NOT_CREATED',
        'diffraction_data': 'NOT_READ', 'refinement': 'NOT_RUN', 'requires_cif_review': False, 'automatic_adoption': False,
        'activation_scope': 'OWNED_NEW_RUNTIME_BUNDLE_ONLY', 'existing_runs': 'UNCHANGED'}
    members['runtime_bundle_audit.json'] = _json(audit); members['ordinary_bundle_assessment.json'] = _json(assessment)
    members['probe_receipt.json'] = _json({'runtime_bundle_audit': audit,
        'installed_api_sources': [{'anchor': 'phenix_installation', 'path': 'lib/native.py', 'sha256': 'a' * 64}]})
    return members, audit, replay


def test_saved_activation_replays_ordinary_reader_and_fresh_native_data_without_execution(tmp_path, monkeypatch):
    from nasolve.cif_runtime_return import replay_runtime_activation
    members, _, scaffold = runtime_case(tmp_path)
    before = dict(members)
    def forbidden(*args, **kwargs): raise AssertionError('Saved activation replay started a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    report = replay_runtime_activation(members, scaffold_replay=scaffold)
    assert report['status'] == 'SAVED_RUNTIME_ACTIVATION_REPLAY_PASS'
    assert report['decision']['selected_candidate'] == 'qualified_geometry_endpoint'
    assert report['native_qualification']['native_usable'] and len(report['native_qualification']['checks']) == 15
    assert report['dictionary_count'] == 1 and report['parameter_count'] == 2
    assert report['captured_code_execution'] == report['new_native_execution'] == 'NOT_RUN'
    assert report['checkpoint_adoption'] == 'NOT_RUN' and not report['requires_cif_review']
    assert members == before


def reseal(members, audit):
    """Recompute ordinary native receipt hashes to reach semantic checks."""
    native = audit['native_readback']; prefix = native['directory']['path']
    members[prefix + '/native_validation.json'] = _json(native['native_validation'])
    native['outputs'] = [{'anchor': 'native_directory', 'path': name.removeprefix(prefix + '/'),
        'sha256': sha256(data).hexdigest(), 'size': len(data)} for name, data in sorted(members.items())
        if name.startswith(prefix + '/') and name != prefix + '/native_receipt.json']
    members[prefix + '/native_receipt.json'] = _json({key: value for key, value in native.items() if key != 'directory'})
    header = json.loads(members['probe_receipt.json']); header['runtime_bundle_audit'] = audit
    members['probe_receipt.json'] = _json(header); members['runtime_bundle_audit.json'] = _json(audit)


@pytest.mark.parametrize('defect', ['worker', 'native_spec', 'ordered_parameters', 'declared_api', 'energy_repeat', 'energy_source',
    'native_definition', 'native_model', 'native_qualification', 'bundle_model', 'manifest_order', 'manifest_decision',
    'assessment_finding', 'legacy_execution_false', 'legacy_execution_true', 'legacy_wrong_choice', 'legacy_wrong_context',
    'unsafe_manifest', 'pickle', 'reader'])
def test_saved_activation_rejects_changed_evidence_after_native_receipts_are_resealed(tmp_path, defect):
    from nasolve.cif_runtime_return import replay_runtime_activation
    members, audit, scaffold = runtime_case(tmp_path)
    native = audit['native_readback']; prefix = native['directory']['path']
    if defect == 'worker': members[prefix + '/native_worker.py'] += b'\n# altered worker\n'
    if defect == 'native_spec':
        spec = json.loads(members[prefix + '/native_spec.json']); spec['energy_inventory'] = False
        members[prefix + '/native_spec.json'] = _json(spec)
    if defect == 'ordered_parameters':
        native['inputs'][-2:] = native['inputs'][-2:][::-1]
        for i, row in enumerate(native['inputs']): row['input_index'] = i
        spec = json.loads(members[prefix + '/native_spec.json']); spec['phil_files'].reverse()
        members[prefix + '/native_spec.json'] = _json(spec)
    if defect == 'declared_api': native['api_sources'][0]['git_blob'] = '0' * 40
    if defect == 'energy_repeat': native['native_validation']['energy_inventory']['snapshots'][1]['target'] += 1
    if defect == 'energy_source': native['native_validation']['energy_inventory']['installed_sources'][0]['sha256'] = '0' * 64
    if defect == 'native_definition': native['native_validation']['monomer_mappings']['rows'][0]['metadata']['effective_definition']['changed'] = []
    if defect == 'native_model': native['native_validation']['atoms'][0]['xyz'][0] += 1
    if defect == 'native_qualification': audit['native_qualification']['checks']['atoms'] = False
    if defect == 'bundle_model': members['activated_bundle/' + audit['activation']['resources']['model']['relative_path']] += b'\n# changed model\n'
    if defect in {'manifest_order', 'manifest_decision'}:
        if defect == 'manifest_order': audit['activation']['resources']['phils'].reverse()
        else: audit['activation']['decision']['selected_candidate'] = 'verified_initial_scaffold'
        members[audit['manifest']['path']] = _json(audit['activation'])
        audit['manifest']['sha256'] = sha256(members[audit['manifest']['path']]).hexdigest()
    if defect in {'assessment_finding', 'legacy_execution_false', 'legacy_execution_true', 'legacy_wrong_choice', 'legacy_wrong_context'}:
        assessment = json.loads(members['ordinary_bundle_assessment.json']); summary = assessment['solution_report']
        if defect == 'assessment_finding': assessment['summary']['finding_counts']['PASS'] += 1
        else:
            summary['native_selection'] = 'NOT_RUN'; summary.pop('native_selection_executed', None)
            if defect == 'legacy_execution_false': summary['native_selection_executed'] = False
            if defect == 'legacy_execution_true': summary['native_selection_executed'] = True
            if defect == 'legacy_wrong_choice': summary['selected_candidate'] = 'verified_initial_scaffold'
            if defect == 'legacy_wrong_context': assessment['bundle_context']['native_evidence'] = 'NOT_RUN'
        members['ordinary_bundle_assessment.json'] = _json(assessment)
    if defect == 'unsafe_manifest': audit['manifest']['path'] = '../runtime_bundle.json'
    if defect == 'pickle': members[prefix + '/forbidden.pkl'] = b'EXPLICIT OBJECT MUST NOT LOAD'
    if defect == 'reader': audit['ordinary_reader'] = 'unverified_other_reader'
    reseal(members, audit)
    with pytest.raises(ValueError): replay_runtime_activation(members, scaffold_replay=scaffold)


def test_exact_legacy_c61_summary_is_normalized_without_rerunning_native_selection(tmp_path):
    from nasolve.cif_runtime_return import replay_runtime_activation
    members, _, scaffold = runtime_case(tmp_path)
    assessment = json.loads(members['ordinary_bundle_assessment.json'])
    assessment['solution_report']['native_selection'] = 'NOT_RUN'
    assessment['solution_report'].pop('native_selection_executed')
    members['ordinary_bundle_assessment.json'] = _json(assessment)
    report = replay_runtime_activation(members, scaffold_replay=scaffold)
    summary = report['ordinary_assessment']['solution_report']
    assert summary['native_selection'] == 'VERIFIED_SOURCE_CAPTURE'
    assert summary['native_selection_executed'] is False
    assert report['native_readback']['energy_evaluations'] == 2


def test_supplied_scaffold_replay_must_match_the_bound_parent_artifact(tmp_path):
    from nasolve.cif_runtime_return import replay_runtime_activation
    members, _, scaffold = runtime_case(tmp_path)
    scaffold['selected_model']['sha256'] = '0' * 64
    with pytest.raises(ValueError): replay_runtime_activation(members, scaffold_replay=scaffold)


def test_saved_activation_rejects_duplicate_json_before_ordinary_resolution(tmp_path):
    from nasolve.cif_runtime_return import replay_runtime_activation
    members, _, _ = runtime_case(tmp_path)
    members['probe_receipt.json'] = b'{"runtime_bundle_audit":{},"runtime_bundle_audit":{}}'
    with pytest.raises(ValueError, match='Duplicate'): replay_runtime_activation(members)
