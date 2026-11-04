"""The native readback delivery accepts completed construction evidence only."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def fake_return(monkeypatch):
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar64', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    a = {'policy_id': 'cif-postmr-construction-controls-v1', 'status': 'CONSTRUCTION_CONTROLS_PASS',
        'analysis_completed': True, 'ordinary_construction_api': 'nasolve.postmr.construct_postmr_model',
        'coot': {'execution': 'COMPLETED', 'version': '1.3.3', 'timeout_seconds': 600},
        'audit': {'raw_fallback_sites': []}, 'context_receipt': {'status': 'CONTEXT_PREPARED'},
        'user_cif_review_required': False, 'source_inputs_preserved': True,
        **{k: 'NOT_RUN' for k in ['mr_execution', 'phenix_execution', 'readyset_execution', 'optimization', 'refinement']},
        'mtz_used': False}
    r = {'delivery_prefix': '63_Cedar', 'build': {'explicit_fake': 'TEST_BUILD'},
        'kind': 'cif-source-graph-numerical-recovery-probe', 'status': 'REVIEW',
        'requested_action': 'ORDINARY_POSTMR_CONSTRUCTION_CONTROLS', 'policy_authority': 'NARestraints',
        'native_execution': 'FRESH_COOT_POSTMR_CONSTRUCTION', 'coot_runtime': {'version': '1.3.3'},
        'model_editing': 'SEPARATE_FRESH_CONSTRUCTION_CONTROLS', 'postmr_construction_audit': a,
        'prior_archive': {'sha256': module.CEDAR62_SHA256, 'verified_payloads': 3445},
        'requires_cif_review': False, 'automatic_adoption': False,
        **{k: True for k in ['analysis_completed', 'original_archive_preserved', 'frozen_inputs_preserved', 'prerequisite_mechanics_replayed']},
        **{k: 'NOT_RUN' for k in ['native_proxy_validation', 'linked_site_validation', 'model_optimization', 'dictionary_generation',
            'policy_recompilation', 'refinement', 'readyset_retry', 'installed_phenix_edits', 'scientific_approval']}}
    module.CEDAR63_BUILD_SHA256 = sha256(json.dumps(r['build'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(module, '_read_cedar62_members', lambda members: ('proof', 'prior', 'rotation'))
    monkeypatch.setattr(module, '_replay_postmr_construction', lambda members: {'context_replayed': True})
    return module, r


@pytest.mark.parametrize('defect', ['none', 'build', 'kind', 'action', 'lineage', 'preservation',
    'native', 'coot_version', 'fallback', 'context', 'adoption', 'policy', 'report', 'optimizer', 'student_gate'])
def test_native_readback_requires_exact_completed_context_return(monkeypatch, defect):
    module, r = fake_return(monkeypatch); a = r['postmr_construction_audit']
    if defect == 'build': r['build']['changed'] = True
    if defect == 'kind': r['kind'] = 'OTHER'
    if defect == 'action': r['requested_action'] = 'OTHER'
    if defect == 'lineage': r['prior_archive']['sha256'] = '0'*64
    if defect == 'preservation': r['original_archive_preserved'] = False
    if defect == 'native': r['native_execution'] = 'NOT_RUN'
    if defect == 'coot_version': r['coot_runtime']['version'] = 'OTHER'
    if defect == 'fallback': a['audit']['raw_fallback_sites'] = ['A:6']
    if defect == 'context': a['context_receipt']['status'] = 'RAW_CONTEXT_RETAINED'
    if defect == 'adoption': r['automatic_adoption'] = True
    if defect == 'policy': a['policy_id'] = 'OTHER'
    if defect == 'optimizer': r['model_optimization'] = 'UNBOUNDED'
    if defect == 'student_gate': r['requires_cif_review'] = True
    members = {'probe_receipt.json': json.dumps(r).encode(), 'postmr_construction_audit.json': json.dumps(a).encode(),
        'inputs/review/probe_receipt.json': b'{}'}
    if defect == 'report': members['postmr_construction_audit.json'] = b'{}'
    members.update({'padding/' + str(i): b'EXPLICIT_FAKE_PADDING' for i in range(3489 - len(members))})
    members['manifest.json'] = json.dumps({n: {'sha256': sha256(d).hexdigest(), 'bytes': len(d)} for n, d in members.items()}).encode()
    if defect == 'none': assert module._read_cedar63_members(members) == ('proof', 'prior', 'rotation')
    else:
        with pytest.raises(ValueError): module._read_cedar63_members(members)


@pytest.mark.parametrize('action', ['postmr_construction_native_only', 'postmr_construction_only', 'runtime_bundle_only'])
def test_native_action_is_bound_to_cedar63(monkeypatch, action):
    module, _ = fake_return(monkeypatch)
    args = SimpleNamespace(**{action: True})
    if action == 'postmr_construction_native_only': module._check_constructor_input_mode(args, '63_Cedar')
    else:
        with pytest.raises(ValueError): module._check_constructor_input_mode(args, '63_Cedar')
