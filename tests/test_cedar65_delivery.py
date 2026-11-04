"""Saved construction replay accepts the exact completed C64 evidence only."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def template():
    spec = importlib.util.spec_from_file_location('cedar65', Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def fake_return(monkeypatch):
    m = template()
    checks = [{'check': 'unaffected-native-proxies:' + k, 'status': 'REVIEW'} for k in
        ['angle', 'bond_simple', 'chirality', 'const_dihedral', 'dihedral', 'planarity']]
    checks += [{'check': 'effective-site-formal-charges:' + s, 'status': 'UNSUPPORTED'} for s in ['A:6', 'A:7', 'A:9']]
    checks += [{'check': 'explicit_fake_pass_' + str(i), 'status': 'PASS'} for i in range(87)]
    a = {'policy_id': 'cif-ordinary-construction-native-readback-v1', 'scope': 'SEPARATE_CONSTRUCTED_MODEL_NATIVE_READBACK',
        'status': 'REVIEW', 'native_execution': 'ORDINARY_CONSTRUCTION_NATIVE_READBACK',
        'qualification': {'status': 'REVIEW', 'mechanics_checks_pass': False, 'checks': checks},
        'construction_input': {'delivery_prefix': '63_Cedar', 'sha256': m.CEDAR63_SHA256, 'status': 'CONSTRUCTION_CONTROLS_PASS'},
        'automatic_adoption': False, 'requires_cif_review': False, 'mtz_used': False,
        **{k: 'NOT_RUN' for k in ['coot_execution', 'readyset_execution', 'dictionary_generation', 'model_optimization', 'policy_recompilation', 'refinement']}}
    r = {'delivery_prefix': '64_Cedar', 'build': {'explicit_fake': 'TEST_BUILD'}, 'kind': 'cif-source-graph-numerical-recovery-probe',
        'status': 'REVIEW', 'requested_action': 'ORDINARY_POSTMR_CONSTRUCTION_NATIVE_READBACK', 'phenix_version': '2.2.1',
        'policy_authority': 'NARestraints', 'requires_cif_review': False, 'automatic_adoption': False,
        'native_execution': 'ORDINARY_CONSTRUCTION_NATIVE_READBACK', 'native_proxy_validation': 'ORDINARY_CONSTRUCTION_NATIVE_READBACK',
        'linked_site_validation': 'ORDINARY_CONSTRUCTION_NATIVE_READBACK', 'model_editing': 'EXACT_CONSTRUCTED_MODEL_COPY',
        'construction_native_audit': a, 'prior_archive': {'sha256': m.CEDAR63_SHA256, 'verified_payloads': 3489},
        **{k: True for k in ['analysis_completed', 'original_archive_preserved', 'frozen_inputs_preserved', 'prerequisite_mechanics_replayed']},
        **{k: 'NOT_RUN' for k in ['model_optimization', 'dictionary_generation', 'policy_recompilation', 'refinement',
            'readyset_retry', 'installed_phenix_edits', 'scientific_approval']}}
    m.CEDAR64_BUILD_SHA256 = sha256(json.dumps(r['build'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(m, '_read_cedar63_members', lambda members: ('proof', 'prior', 'rotation'))
    return m, r


@pytest.mark.parametrize('defect', ['none', 'build', 'kind', 'action', 'lineage', 'payload_count', 'preservation',
    'native', 'version', 'model_edit', 'report', 'scope', 'optimizer', 'adoption', 'student_gate', 'review_families',
    'missing_check', 'duplicate_check', 'unrecognized_status'])
def test_saved_constructed_native_requires_exact_return(monkeypatch, defect):
    m, r = fake_return(monkeypatch); a = r['construction_native_audit']
    if defect == 'build': r['build']['changed'] = True
    if defect == 'kind': r['kind'] = 'OTHER'
    if defect == 'action': r['requested_action'] = 'OTHER'
    if defect == 'lineage': r['prior_archive']['sha256'] = '0'*64
    if defect == 'payload_count': r['prior_archive']['verified_payloads'] = 0
    if defect == 'preservation': r['original_archive_preserved'] = False
    if defect == 'native': r['native_execution'] = 'NOT_RUN'
    if defect == 'version': r['phenix_version'] = 'OTHER'
    if defect == 'model_edit': r['model_editing'] = 'CHANGED'
    if defect == 'scope': a['scope'] = 'OTHER'
    if defect == 'optimizer': a['model_optimization'] = 'RAN'
    if defect == 'adoption': a['automatic_adoption'] = True
    if defect == 'student_gate': r['requires_cif_review'] = True
    if defect == 'review_families': a['qualification']['checks'][0]['check'] = 'different_failure'
    if defect == 'missing_check': a['qualification']['checks'].pop()
    if defect == 'duplicate_check': a['qualification']['checks'][-1] = deepcopy(a['qualification']['checks'][-2])
    if defect == 'unrecognized_status': a['qualification']['checks'][-1]['status'] = 'UNKNOWN'
    members = {'probe_receipt.json': json.dumps(r).encode(), 'construction_native_audit.json': json.dumps(a).encode(),
        'inputs/review/probe_receipt.json': b'{}'}
    if defect == 'report': members['construction_native_audit.json'] = b'{}'
    members.update({'padding/' + str(i): b'EXPLICIT_FAKE' for i in range(3552 - len(members))})
    members['manifest.json'] = json.dumps({n: {'sha256': sha256(d).hexdigest(), 'bytes': len(d)} for n, d in members.items()}).encode()
    if defect == 'none': assert m._read_cedar64_members(members) == ('proof', 'prior', 'rotation')
    else:
        with pytest.raises(ValueError): m._read_cedar64_members(members)


@pytest.mark.parametrize('action,delivery,valid', [('saved_postmr_construction_native_only', '64_Cedar', True),
    ('postmr_construction_native_only', '64_Cedar', False), ('saved_native_usability_only', '64_Cedar', False),
    ('saved_postmr_construction_native_only', '63_Cedar', False)])
def test_saved_construction_action_has_one_input_scope(action, delivery, valid):
    m = template(); args = SimpleNamespace(**{action: True})
    if valid: m._check_constructor_input_mode(args, delivery)
    else:
        with pytest.raises(ValueError): m._check_constructor_input_mode(args, delivery)
