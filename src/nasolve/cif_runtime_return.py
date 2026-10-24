"""Read-only replay of an activated ordinary CIF Doctor runtime bundle.

The caller first validates the parent C60 return. This module checks the new
portable copies, ordinary assessment and fresh native readback without running
captured Python or repeating optimization.
"""
from copy import deepcopy
from hashlib import sha256
import math
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from .cif_candidate_usability import energy_inventory_checks
from .cif_fixed_geometry import _fixed_policy
from .cif_fragment_restoration import _model
from .cif_native_validation import API_SOURCES
from .cif_runtime_bundle import (POLICY_ID as BUNDLE_POLICY_ID, assess_runtime_bundle,
    prepare_runtime_bundle, resolve_runtime_bundle)
from .cif_scaffold_return import _artifact_rows, _equivalent, _json, _need, _safe

POLICY_ID = 'cif-saved-runtime-activation-replay-v1'
C60_SHA256 = '3035ccbf1b89c399d36ed195b5df43c6aad78bbf831f68217103d9fad76e759c'
NATIVE_ENERGY_WORKER_SHA256 = '0d10c459f194564937e1b27d13c2650f077e6c6f6214d5172132f3472848e0a6'
COMPACT_KEYS = ('policy_id', 'status', 'component', 'selected_sites', 'atom_count',
    'decision', 'selected_model', 'starting_model', 'captured_code_execution')


def qualify_runtime_readback(expected, native, model, reference_target, *, energy_sources=None):
    """Match a fresh ordinary-layout manager and its fixed raw objective."""
    checks = {key: native.get(key) == expected.get(key) for key in
        ['atoms', 'atom_count', 'monomer_mappings', 'geometry', 'installed_api_sources', 'restraint_policy']}
    checks.update(energy_inventory_checks(native))
    checks['native_interpreter'] = (native.get('status') == 'REVIEW' and native.get('fatal_problems') is None
        and native.get('unused_definitions') == [] and native.get('unsupported_fields') == [])
    checks['fixed_na_policy'] = _fixed_policy(native)
    snapshots = native.get('energy_inventory', {}).get('snapshots', [])
    checks['repeatable_fixed_energy'] = len(snapshots) == 2 and snapshots[0] == snapshots[1]
    checks['same_serialized_objective'] = (len(snapshots) == 2 and type(reference_target) in (int, float)
        and math.isfinite(reference_target) and all(type(row.get('target')) in (int, float)
        and math.isfinite(row['target']) and math.isclose(row['target'], reference_target, rel_tol=1e-10, abs_tol=1e-8)
        for row in snapshots))
    try:
        _model(native, Path(model), coordinates_match=True)
        checks['exact_selected_model'] = True
    except (KeyError, ValueError, TypeError):
        checks['exact_selected_model'] = False
    if energy_sources is not None:
        proof = native.get('energy_inventory', {}).get('installed_sources', [])
        checks['exact_energy_sources'] = (len(proof) == len(energy_sources) == 3
            and [(row['module'], row['sha256']) for row in proof]
            == [(row['module'], row['sha256']) for row in energy_sources])
    return {'policy_id': 'cif-activated-runtime-native-readback-v1', 'checks': checks,
        'native_usable': all(checks.values()), 'status': 'PASS' if all(checks.values()) else 'REVIEW',
        'model_sha256': sha256(Path(model).read_bytes()).hexdigest(),
        'model_optimization': 'NOT_RUN', 'requires_cif_review': False}


def _compact_scaffold_replay(members, parent):
    """Bind the compact record to the already verified parent selection."""
    previous = _json(members, 'inputs/review/inputs/review/scaffold_candidate_audit.json')
    old = previous['candidate']; old_directory = old['directory']['path']
    _need(old['directory'].get('anchor') == 'probe_directory' and _safe(old_directory), 'Unsafe initial scaffold reference')
    models = [row for row in old['inputs'] if row['role'] == 'model']
    _need(len(models) == 1 and _safe(models[0]['path']), 'Require the exact parent initial model reference')
    selected_name = 'geometry_candidate/scaffold_geometry_model.pdb'
    selected = members['inputs/review/' + selected_name]
    initial_name = 'inputs/review/' + old_directory + '/' + models[0]['path']
    initial = members['inputs/review/' + initial_name]
    serialization = parent['serialization']
    _need(sha256(selected).hexdigest() == serialization['candidate_sha256']
        and sha256(initial).hexdigest() == serialization['source_sha256']
        and parent['decision']['selected_candidate'] == 'qualified_geometry_endpoint'
        and parent['decision']['endpoint_usable'] is True, 'Parent artifact selection is not bound to its saved coordinates')
    return {'policy_id': 'cif-saved-scaffold-geometry-replay-v1', 'status': 'SAVED_SCAFFOLD_GEOMETRY_REPLAY_PASS',
        'component': parent['component'], 'selected_sites': parent['selected_sites'],
        'atom_count': parent['native_roundtrip']['native_validation']['atom_count'], 'decision': parent['decision'],
        'selected_model': {'anchor': 'input_capsule', 'path': selected_name,
            'sha256': serialization['candidate_sha256'], 'size': len(selected)},
        'starting_model': {'anchor': 'input_capsule', 'path': initial_name,
            'sha256': serialization['source_sha256'], 'size': len(initial)}, 'captured_code_execution': 'NOT_RUN'}


def _assessment_compatibility(recorded, manifest):
    """Translate only C61's inherited dictionary-only selection summary flag."""
    value = deepcopy(recorded); summary = value.get('solution_report', {})
    if summary.get('native_selection') == 'NOT_RUN' and 'native_selection_executed' not in summary:
        context = value.get('bundle_context', {})
        _need(context.get('policy_id') == BUNDLE_POLICY_ID and context.get('native_evidence') == 'VERIFIED_SOURCE_CAPTURE'
            and summary.get('native_evidence') == 'VERIFIED_SOURCE_CAPTURE'
            and summary.get('selected_candidate') == manifest['decision']['selected_candidate'],
            'Legacy native-selection flag lacks its qualified runtime scope')
        summary['native_selection'] = 'VERIFIED_SOURCE_CAPTURE'
        summary['native_selection_executed'] = False
    return value


def replay_runtime_activation(members, *, scaffold_replay=None):
    """Reproduce C61 activation/assessment and derive all fresh native checks.

    The exact parent C60 capsule must already be validated by the caller. The
    optional parent replay record is checked only through its bound compact
    fields; no earlier numerical audit or optimizer is invoked again.
    """
    try:
        receipt = _json(members, 'probe_receipt.json'); report = receipt['runtime_bundle_audit']
        _need(report == _json(members, 'runtime_bundle_audit.json')
            and report.get('policy_id') == 'cif-runtime-bundle-activation-trial-v1'
            and report.get('scope') == 'SEPARATE_PORTABLE_RUNTIME_BUNDLE'
            and report.get('native_execution') == 'QUALIFIED_RUNTIME_BUNDLE_READBACK'
            and report.get('activation_scope') == 'OWNED_NEW_RUNTIME_BUNDLE_ONLY'
            and report.get('existing_runs') == 'UNCHANGED' and report.get('production_checkpoint') == 'NOT_CREATED'
            and report.get('requires_cif_review') is False and report.get('automatic_adoption') is False
            and all(report.get(key) == 'NOT_RUN' for key in ['dictionary_generation', 'model_optimization', 'refinement'])
            and report.get('diffraction_data') == 'NOT_READ'
            and report.get('ordinary_reader') == 'resolve_runtime_bundle'
            and report.get('ordinary_cli') == 'nasolve cif-doctor assess --bundle PATH',
            'Require completed separate ordinary runtime activation evidence')
        parent = _json(members, 'inputs/review/scaffold_geometry_audit.json')
        previous = _json(members, 'inputs/review/inputs/review/scaffold_candidate_audit.json')
        compact = _compact_scaffold_replay(members, parent)
        _need(report['component'] == parent['component'] and report['selected_sites'] == parent['selected_sites']
            and report['source_return_replayed'] == compact, 'Recorded parent selection replay differs from its bound source')
        if scaffold_replay is not None:
            _need({key: scaffold_replay[key] for key in COMPACT_KEYS} == compact, 'Supplied parent replay differs from the activation source')
        capture = parent['native_roundtrip']; expected = capture['native_validation']
        directory = capture['directory']['path']
        _need(capture['directory'].get('anchor') == 'probe_directory' and _safe(directory), 'Unsafe selected parent native directory')
        _artifact_rows(members, 'inputs/review/' + directory, capture['inputs'])
        manifest_ref = report['manifest']; assessment_ref = report['ordinary_assessment']
        _need(manifest_ref.get('anchor') == assessment_ref.get('anchor') == 'probe_directory'
            and _safe(manifest_ref['path']) and _safe(assessment_ref['path']), 'Unsafe ordinary activation output reference')
        manifest_prefix = PurePosixPath(manifest_ref['path']).parent.as_posix()
        with TemporaryDirectory(prefix='nasolve-runtime-return-') as temporary:
            folder = Path(temporary).resolve(); inputs = folder / 'inputs'; inputs.mkdir()
            resources = []
            for row in capture['inputs']:
                path = inputs / PurePosixPath(row['path']).name
                _need(not path.exists(), 'Parent resource basenames cannot alias')
                path.write_bytes(members['inputs/review/' + directory + '/' + row['path']])
                resources.append((row['role'], path))
            models = [path for role, path in resources if role == 'model']
            _need(len(models) == 1, 'Require one exact selected runtime model')
            model = models[0]; cifs = [path for role, path in resources if role == 'dictionary']
            phils = [path for role, path in resources if role == 'phil']
            old = previous['candidate']; old_directory = old['directory']['path']
            old_models = [row for row in old['inputs'] if row['role'] == 'model']
            _need(len(old_models) == 1 and _safe(old_models[0]['path']), 'Require one exact initial runtime fallback model')
            initial = folder / 'initial/initial_model.pdb'; initial.parent.mkdir()
            initial.write_bytes(members['inputs/review/inputs/review/' + old_directory + '/' + old_models[0]['path']])
            provenance = {'initial_model': initial, 'initial_native_validation': old['native_validation'],
                'initial_qualification': previous['qualification'], 'trial': parent['geometry_trial'],
                'serialization': parent['serialization'], 'source_archive': {'sha256': C60_SHA256, 'delivery_prefix': '60_Cedar'},
                'source_inputs': [{key: row[key] for key in ['role', 'sha256', 'size']} for row in capture['inputs']]}
            output = folder / 'bundle'
            manifest = prepare_runtime_bundle(model, cifs, phils, output, decision=parent['decision'],
                native_validation=expected, provenance=provenance)
            _need(manifest == report['activation'] == _json(members, manifest_ref['path'])
                and sha256(members[manifest_ref['path']]).hexdigest() == manifest_ref['sha256'],
                'Ordinary activation manifest does not reproduce the qualified selection')
            for path in output.rglob('*'):
                if path.is_file():
                    name = manifest_prefix + '/' + path.relative_to(output).as_posix()
                    _need(path.read_bytes() == members[name], 'Activated runtime resource/evidence bytes do not replay')
            bundle = resolve_runtime_bundle(output / manifest['manifest_file'])
            assessment = assess_runtime_bundle(output / manifest['manifest_file'])
            recorded_assessment = _assessment_compatibility(_json(members, assessment_ref['path']), manifest)
            _need(_equivalent(assessment, recorded_assessment), 'Ordinary bundle assessment findings or summary do not replay')
            native = report['native_readback']; prefix = native['directory']['path']; execution = native['execution']
            _need(native['directory'].get('anchor') == 'probe_directory' and _safe(prefix)
                and native.get('status') == 'REVIEW' and execution.get('status') == 'COMPLETED'
                and execution.get('returncode') == 0 and execution.get('timeout_seconds') == 60
                and native.get('source_preserved') is True and native.get('frozen_inputs_preserved') is True
                and native.get('phenix_version') == '2.2.1' and native.get('automatic_adoption') is False
                and native.get('dictionary_source_policy') == 'EXPLICIT_DICTIONARIES'
                and native.get('phil_namespace_policy') == 'refinement-root-to-interpreter-v1'
                and native.get('symlink_outputs') == []
                and all(native.get(key) == 'NOT_RUN' for key in ['optimization', 'model_editing', 'scientific_approval', 'readyset_retry'])
                and native['executable_sha256'] == capture['executable_sha256']
                and native['executable_provenance'] == capture['executable_provenance'], 'Fresh ordinary-layout native execution differs')
            _need(_json(members, prefix + '/native_receipt.json') == {k: v for k, v in native.items() if k != 'directory'},
                'Fresh ordinary-layout native receipt differs')
            _artifact_rows(members, prefix, native['inputs']); _artifact_rows(members, prefix, native['outputs'])
            _need(sha256(members[prefix + '/native_worker.py']).hexdigest() == NATIVE_ENERGY_WORKER_SHA256,
                'Fresh ordinary native energy worker source differs')
            ordinary = [('model', bundle['model'].read_bytes()),
                *[('dictionary', path.read_bytes()) for path in bundle['dictionaries']], *[('phil', path.read_bytes()) for path in bundle['phils']]]
            supplied = native['inputs']
            _need([(row['role'], members[prefix + '/' + row['path']]) for row in supplied] == ordinary
                and [row.get('input_index') for row in supplied] == list(range(len(supplied)))
                and native.get('input_integrity') == [{'input_index': i, 'snapshot_preserved': True, 'source_preserved': True} for i in range(len(supplied))],
                'Fresh ordinary native scientific inputs or integrity differ')
            specification = {'policy_id': 'cif-native-bundle-inventory-v1', 'model': supplied[0]['path'],
                'dictionaries': [row['path'] for row in supplied if row['role'] == 'dictionary'],
                'phil_files': [row['path'] for row in supplied if row['role'] == 'phil'],
                'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'inventory_detail': 'linked',
                'policy_inventory': True, 'energy_inventory': True}
            _need(_json(members, prefix + '/native_spec.json') == specification
                and native['native_validation'] == _json(members, prefix + '/native_validation.json'),
                'Fresh ordinary native specification or inventory differs')
            pins = previous['candidate']['native_validation']['energy_inventory']['installed_sources']
            qualification = qualify_runtime_readback(expected, native['native_validation'], bundle['model'],
                parent['geometry_trial']['result']['serialized']['target'], energy_sources=pins)
            _need(qualification == report['native_qualification'] and qualification['native_usable'] is True
                and qualification['status'] == 'PASS' and len(qualification['checks']) == 15,
                'Fresh ordinary native mechanics/objective qualification does not replay')
            _need(native['api_sources'] == capture['api_sources'] == API_SOURCES, 'Fresh declared native APIs differ')
            installation = Path(native['executable_provenance']).parent.parent
            fingerprints = [{'anchor': 'phenix_installation',
                'path': Path(row['historical_path']).relative_to(installation).as_posix(), 'sha256': row['sha256']}
                for row in native['native_validation']['installed_api_sources']]
            _need(receipt['installed_api_sources'] == fingerprints, 'Fresh installed native API source hashes differ')
        model_ref = manifest['resources']['model']
        return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'SAVED_RUNTIME_ACTIVATION_REPLAY_PASS',
            'component': report['component'], 'selected_sites': report['selected_sites'],
            'decision': manifest['decision'], 'native_qualification': qualification,
            'selected_model': {'anchor': 'input_capsule', 'path': manifest_prefix + '/' + model_ref['relative_path'],
                'sha256': model_ref['sha256'], 'size': model_ref['size']},
            'manifest': {'anchor': 'input_capsule', 'path': manifest_ref['path'], 'sha256': manifest_ref['sha256']},
            'ordinary_assessment': {'status': assessment['status'], 'summary': assessment['summary'],
                'solution_report': assessment['solution_report'], 'requires_cif_review': False},
            'native_readback': {'anchor': 'input_capsule', 'path': prefix + '/native_validation.json',
                'sha256': sha256(members[prefix + '/native_validation.json']).hexdigest(),
                'energy_evaluations': native['native_validation']['energy_inventory']['evaluation_calls']},
            'dictionary_count': len(manifest['resources']['dictionaries']), 'parameter_count': len(manifest['resources']['phils']),
            'source_archive': manifest['source_archive'], 'captured_code_execution': 'NOT_RUN', 'new_native_execution': 'NOT_RUN',
            'model_optimization': 'NOT_RUN', 'checkpoint_adoption': 'NOT_RUN', 'automatic_adoption': False, 'requires_cif_review': False}
    except (KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete saved runtime activation evidence: ' + str(exc)) from exc
