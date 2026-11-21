"""Saved native readback is data, bound to exact workers, inputs and results."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest


def captured_native():
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_validation import _NATIVE_WORKER
    directory = 'native/reference'; model = b'EXPLICIT_FAKE_MODEL'; phil = b'EXPLICIT_FAKE_PHIL'
    spec = {'policy_id': 'cif-native-bundle-inventory-v1', 'model': 'inputs/000_model.pdb',
        'dictionaries': [], 'phil_files': ['inputs/001_phil.phil'], 'inventory_detail': 'linked',
        'policy_inventory': True, 'energy_inventory': True, 'installed_library_only': True,
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1'}
    result = {'explicit_fake': 'NO_NATIVE_EXECUTION', 'installed_api_sources': [],
        'energy_inventory': {'installed_sources': []}}
    files = {'inputs/000_model.pdb': model, 'inputs/001_phil.phil': phil,
        'native_worker.py': native_energy_worker(_NATIVE_WORKER).encode(),
        'native_spec.json': json.dumps(spec).encode(), 'native_validation.json': json.dumps(result).encode()}
    def ref(name): return {'anchor': 'native_directory', 'path': name, 'size': len(files[name]), 'sha256': sha256(files[name]).hexdigest()}
    record = {'status': 'REVIEW', 'policy_id': 'cif-native-bundle-inventory-v1', 'phenix_version': '2.2.1',
        'execution': {'status': 'COMPLETED', 'returncode': 0, 'timeout_seconds': 60},
        'source_preserved': True, 'frozen_inputs_preserved': True, 'symlink_outputs': [],
        'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN', 'readyset_retry': 'NOT_RUN',
        'automatic_adoption': False, 'scientific_approval': 'NOT_RUN',
        'dictionary_source_policy': 'INSTALLED_LIBRARY_ONLY',
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1',
        'inputs': [dict(ref('inputs/000_model.pdb'), input_index=0, role='model'),
            dict(ref('inputs/001_phil.phil'), input_index=1, role='phil')],
        'input_integrity': [{'input_index': i, 'source_preserved': True, 'snapshot_preserved': True} for i in range(2)],
        'outputs': [ref(n) for n in sorted(files)], 'native_validation': result}
    files['native_receipt.json'] = json.dumps(record).encode()
    members = {directory + '/' + n: d for n, d in files.items()}
    record = dict(record, directory={'anchor': 'probe_directory', 'path': directory})
    return members, record, [('model', model), ('phil', phil)]


def rewrite_receipt(members, record):
    members[record['directory']['path'] + '/native_receipt.json'] = json.dumps(
        {k: v for k, v in record.items() if k != 'directory'}).encode()


@pytest.mark.parametrize('defect', ['none', 'execution', 'returncode', 'timeout', 'source_preservation',
    'frozen_preservation', 'symlink', 'optimizer', 'readyset', 'adoption', 'namespace', 'library_policy',
    'input_order', 'input_index', 'input_role', 'input_bytes', 'input_label_integrity', 'output_bytes',
    'unsafe_path', 'anchor', 'receipt', 'inventory', 'worker', 'spec'])
def test_saved_native_capture_requires_all_exact_bindings(defect):
    from nasolve.cif_construction_native import _saved_native_capture
    members, record, expected = captured_native(); directory = record['directory']['path']
    if defect == 'execution': record['execution']['status'] = 'FAILED'
    if defect == 'returncode': record['execution']['returncode'] = 2
    if defect == 'timeout': record['execution']['timeout_seconds'] = 600
    if defect == 'source_preservation': record['source_preserved'] = False
    if defect == 'frozen_preservation': record['frozen_inputs_preserved'] = False
    if defect == 'symlink': record['symlink_outputs'] = ['escape']
    if defect == 'optimizer': record['optimization'] = 'RAN'
    if defect == 'readyset': record['readyset_retry'] = 'RAN'
    if defect == 'adoption': record['automatic_adoption'] = True
    if defect == 'namespace': record['phil_namespace_policy'] = 'direct'
    if defect == 'library_policy': record['dictionary_source_policy'] = 'EXPLICIT_DICTIONARIES'
    if defect == 'input_order': record['inputs'].reverse()
    if defect == 'input_index': record['inputs'][0]['input_index'] = 1
    if defect == 'input_role': record['inputs'][0]['role'] = 'dictionary'
    if defect == 'input_bytes': expected[0] = ('model', b'CHANGED_MODEL')
    if defect == 'input_label_integrity': record['input_integrity'][0]['source_preserved'] = False
    if defect == 'output_bytes': members[directory + '/native_worker.py'] += b'\n# CHANGE'
    if defect == 'unsafe_path': record['outputs'][0]['path'] = '../outside'
    if defect == 'anchor': record['directory']['anchor'] = 'host'
    if defect == 'inventory': record['native_validation']['explicit_fake'] = 'CHANGED'
    if defect in {'worker', 'spec'}:
        name = 'native_worker.py' if defect == 'worker' else 'native_spec.json'
        members[directory + '/' + name] = b'raise AssertionError("SAVED CODE MUST NOT EXECUTE")' if defect == 'worker' else b'{}'
        for ref in record['outputs']:
            if ref['path'] == name:
                data = members[directory + '/' + name]; ref.update(size=len(data), sha256=sha256(data).hexdigest())
    if defect != 'receipt': rewrite_receipt(members, record)
    else: members[directory + '/native_receipt.json'] = b'{}'
    snapshot = deepcopy(members)
    if defect == 'none': assert _saved_native_capture(members, record, expected, installed_only=True) == record['native_validation']
    else:
        with pytest.raises((ValueError, KeyError, TypeError)):
            _saved_native_capture(members, record, expected, installed_only=True)
    assert members == snapshot


@pytest.mark.parametrize('defect,passes', [('none', True), ('eigen_roundoff', True), ('det_roundoff', True),
    ('eigen_change', False), ('det_change', False), ('rule', False), ('severity', False),
    ('target', False), ('weight', False), ('unknown_measurement', False), ('type', False)])
def test_only_derived_eigen_measurements_allow_machine_roundoff(defect, passes):
    from nasolve.cif_construction_native import _preparation_replays
    old = {'findings': [{'rule': 'declared-angle-plane', 'severity': 'review',
        'measurements': {'determinant': -4.16e-16, 'eigenvalues': [0., 1.47, 1.53], 'target': 180.}}],
        'target': 1.2, 'weight': 2500.}
    new = deepcopy(old)
    if defect == 'eigen_roundoff': new['findings'][0]['measurements']['eigenvalues'][0] = -2.22e-16
    if defect == 'det_roundoff': new['findings'][0]['measurements']['determinant'] = -1.38e-16
    if defect == 'eigen_change': new['findings'][0]['measurements']['eigenvalues'][1] += .001
    if defect == 'det_change': new['findings'][0]['measurements']['determinant'] = .001
    if defect == 'rule': new['findings'][0]['rule'] = 'OTHER'
    if defect == 'severity': new['findings'][0]['severity'] = 'pass'
    if defect == 'target': new['target'] += 1e-13
    if defect == 'weight': new['weight'] += 1e-10
    if defect == 'unknown_measurement': new['findings'][0]['measurements']['target'] += 1e-13
    if defect == 'type': new['findings'][0]['measurements']['eigenvalues'][0] = '0'
    assert _preparation_replays(old, new) is passes
