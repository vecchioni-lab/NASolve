"""The construction delivery consumes completed Coot fallback evidence only."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def fake_return(monkeypatch):
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar63', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    audit = {'policy_id': 'cif-postmr-construction-controls-v1',
             'status': 'CONSTRUCTION_CONTROLS_PASS_WITH_NOTES', 'analysis_completed': True,
             'ordinary_construction_api': 'nasolve.postmr.construct_postmr_model',
             'coot': {'execution': 'COMPLETED', 'version': '1.3.3', 'timeout_seconds': 600},
             'audit': {'raw_fallback_sites': ['A:6', 'A:9', 'A:7']},
             'user_cif_review_required': False, 'source_inputs_preserved': True,
             'mr_execution': 'NOT_RUN', 'phenix_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
             'optimization': 'NOT_RUN', 'refinement': 'NOT_RUN', 'mtz_used': False}
    receipt = {'build': {'explicit_fake': 'TEST_BUILD'}, 'delivery_prefix': '62_Cedar',
               'kind': 'cif-source-graph-numerical-recovery-probe', 'status': 'REVIEW',
               'requested_action': 'ORDINARY_POSTMR_CONSTRUCTION_CONTROLS',
               'coot_runtime': {'version': '1.3.3'}, 'policy_authority': 'NARestraints',
               'requires_cif_review': False, 'automatic_adoption': False,
               'postmr_construction_audit': audit,
               'model_optimization': 'NOT_RUN', 'native_execution': 'FRESH_COOT_POSTMR_CONSTRUCTION',
               'model_editing': 'SEPARATE_FRESH_CONSTRUCTION_CONTROLS',
               'prior_archive': {'sha256': module.CEDAR61_SHA256, 'verified_payloads': 3406}}
    receipt.update({key: 'NOT_RUN' for key in ['native_proxy_validation', 'linked_site_validation']})
    receipt.update({key: True for key in ['analysis_completed','original_archive_preserved',
                                        'frozen_inputs_preserved','prerequisite_mechanics_replayed']})
    receipt.update({key: 'NOT_RUN' for key in ['dictionary_generation','policy_recompilation',
                    'refinement','readyset_retry','installed_phenix_edits','scientific_approval']})
    module.CEDAR62_BUILD_SHA256 = sha256(json.dumps(receipt['build'], sort_keys=True,
                                                   separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(module, '_read_cedar61_members', lambda members: ('proof', 'prior', 'rotation'))
    monkeypatch.setattr(module, '_replay_postmr_construction', lambda members: {'explicit_fake': 'tested separately'}, raising=False)
    return module, receipt


def members_for(receipt):
    members = {'probe_receipt.json': json.dumps(receipt).encode(),
               'postmr_construction_audit.json': json.dumps(receipt['postmr_construction_audit']).encode(),
               'inputs/review/probe_receipt.json': b'{"explicit_fake":"parent tested separately"}'}
    members.update({'padding/' + str(i): b'EXPLICIT_FAKE_PADDING' for i in range(3445 - len(members))})
    members['manifest.json'] = json.dumps({name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
                                          for name, data in members.items()}).encode()
    return members


@pytest.mark.parametrize('defect', ['none', 'build', 'kind', 'action', 'lineage', 'preservation',
    'native', 'version', 'site', 'adoption', 'policy', 'different_report', 'optimization', 'student_gate'])
def test_exact_completed_construction_return_boundary(monkeypatch, defect):
    module, receipt = fake_return(monkeypatch)
    audit = receipt['postmr_construction_audit']
    if defect == 'build': receipt['build']['changed'] = True
    if defect == 'kind': receipt['kind'] = 'UNRELATED'
    if defect == 'action': receipt['requested_action'] = 'UNQUALIFIED_OPTIMIZER'
    if defect == 'lineage': receipt['prior_archive']['sha256'] = '0' * 64
    if defect == 'preservation': receipt['original_archive_preserved'] = False
    if defect == 'native': receipt['native_execution'] = 'NOT_RUN'
    if defect == 'version': receipt['coot_runtime']['version'] = 'DIFFERENT'
    if defect == 'site': audit['audit']['raw_fallback_sites'] = ['A:6']
    if defect == 'adoption': receipt['automatic_adoption'] = True
    if defect == 'policy': audit['policy_id'] = 'UNVERIFIED'
    if defect == 'optimization': receipt['model_optimization'] = 'UNBOUNDED'
    if defect == 'student_gate': receipt['requires_cif_review'] = True
    members = members_for(receipt)
    if defect == 'different_report':
        members['postmr_construction_audit.json'] = b'{}'
        members['manifest.json'] = json.dumps({name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
            for name, data in members.items() if name != 'manifest.json'}).encode()
    if defect == 'none':
        assert module._read_cedar62_members(members) == ('proof', 'prior', 'rotation')
    else:
        with pytest.raises(ValueError):
            module._read_cedar62_members(members)


@pytest.mark.parametrize('delivery, option', [('62_Cedar', 'postmr_construction_only'), ('61_Cedar', 'postmr_construction_only'),
    ('60_Cedar', 'runtime_bundle_only'), ('59_Cedar', 'scaffold_geometry_only')])
def test_construction_requires_the_matching_explicit_input_action(monkeypatch, delivery, option):
    module, _ = fake_return(monkeypatch)
    args = SimpleNamespace(**{option: True})
    module._check_constructor_input_mode(args, delivery)
    args.postmr_construction_only = not getattr(args, 'postmr_construction_only', False)
    with pytest.raises(ValueError):
        module._check_constructor_input_mode(args, delivery)
