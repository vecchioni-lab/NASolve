"""The activation delivery consumes completed, bound replacement evidence only."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def fake_return(monkeypatch):
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar61', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    audit = {'policy_id': 'cif-qualified-scaffold-geometry-trial-v1',
             'scope': 'SEPARATE_FULL_SCAFFOLD_GEOMETRY_TRIAL', 'component': 'DP',
             'selected_sites': ['B:4'], 'native_execution': 'SOURCE_NATIVE_SCAFFOLD_GEOMETRY_TRIAL',
             'model_optimization': 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL',
             'dictionary_generation': 'NOT_RUN', 'automatic_adoption': False,
             'requires_cif_review': False, 'production_pipeline': 'UNCHANGED'}
    receipt = {'build': {'explicit_fake': 'TEST_BUILD'}, 'delivery_prefix': '60_Cedar',
               'kind': 'cif-source-graph-numerical-recovery-probe', 'status': 'REVIEW',
               'requested_action': 'SOURCE_NATIVE_SCAFFOLD_GEOMETRY_TRIAL',
               'phenix_version': '2.2.1', 'policy_authority': 'NARestraints',
               'requires_cif_review': False, 'automatic_adoption': False,
               'scaffold_geometry_audit': audit,
               'model_optimization': 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL',
               'model_editing': 'SEPARATE_COORDINATE_CANDIDATE',
               'prior_archive': {'sha256': module.CEDAR59_SHA256, 'verified_payloads': 3097}}
    receipt.update({key: 'SOURCE_NATIVE_SCAFFOLD_GEOMETRY_TRIAL'
                    for key in ['native_execution', 'native_proxy_validation', 'linked_site_validation']})
    receipt.update({key: True for key in ['analysis_completed', 'original_archive_preserved',
                                        'frozen_inputs_preserved', 'prerequisite_mechanics_replayed']})
    receipt.update({key: 'NOT_RUN' for key in ['dictionary_generation', 'policy_recompilation',
                    'refinement', 'readyset_retry', 'installed_phenix_edits', 'scientific_approval']})
    module.CEDAR60_BUILD_SHA256 = sha256(json.dumps(receipt['build'], sort_keys=True,
                                                   separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(module, '_read_cedar59_members', lambda members: ('proof', 'prior', 'rotation'))
    monkeypatch.setattr(module, '_replay_scaffold_geometry', lambda members: {'explicit_fake': 'tested separately'}, raising=False)
    return module, receipt


def members_for(receipt):
    members = {'probe_receipt.json': json.dumps(receipt).encode(),
               'scaffold_geometry_audit.json': json.dumps(receipt['scaffold_geometry_audit']).encode(),
               'inputs/review/probe_receipt.json': b'{"explicit_fake":"parent tested separately"}'}
    members.update({'padding/' + str(i): b'EXPLICIT_FAKE_PADDING' for i in range(3300 - len(members))})
    members['manifest.json'] = json.dumps({name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
                                          for name, data in members.items()}).encode()
    return members


@pytest.mark.parametrize('defect', ['none', 'build', 'kind', 'action', 'lineage', 'preservation',
    'native', 'version', 'site', 'adoption', 'policy', 'different_report', 'optimization', 'student_gate'])
def test_exact_completed_geometry_return_boundary(monkeypatch, defect):
    module, receipt = fake_return(monkeypatch)
    audit = receipt['scaffold_geometry_audit']
    if defect == 'build': receipt['build']['changed'] = True
    if defect == 'kind': receipt['kind'] = 'UNRELATED'
    if defect == 'action': receipt['requested_action'] = 'UNQUALIFIED_OPTIMIZER'
    if defect == 'lineage': receipt['prior_archive']['sha256'] = '0' * 64
    if defect == 'preservation': receipt['original_archive_preserved'] = False
    if defect == 'native': receipt['native_execution'] = 'NOT_RUN'
    if defect == 'version': receipt['phenix_version'] = 'DIFFERENT'
    if defect == 'site': audit['selected_sites'] = ['B:5']
    if defect == 'adoption': audit['automatic_adoption'] = True
    if defect == 'policy': audit['policy_id'] = 'UNVERIFIED'
    if defect == 'optimization': receipt['model_optimization'] = 'UNBOUNDED'
    if defect == 'student_gate': receipt['requires_cif_review'] = True
    members = members_for(receipt)
    if defect == 'different_report':
        members['scaffold_geometry_audit.json'] = b'{}'
        members['manifest.json'] = json.dumps({name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
            for name, data in members.items() if name != 'manifest.json'}).encode()
    if defect == 'none':
        assert module._read_cedar60_members(members) == ('proof', 'prior', 'rotation')
    else:
        with pytest.raises(ValueError):
            module._read_cedar60_members(members)


@pytest.mark.parametrize('delivery, option', [('60_Cedar', 'runtime_bundle_only'),
    ('59_Cedar', 'scaffold_geometry_only'), ('58_Cedar', 'scaffold_candidate_only')])
def test_activation_requires_the_matching_explicit_input_action(monkeypatch, delivery, option):
    module, _ = fake_return(monkeypatch)
    args = SimpleNamespace(**{option: True})
    module._check_constructor_input_mode(args, delivery)
    args.runtime_bundle_only = not getattr(args, 'runtime_bundle_only', False)
    with pytest.raises(ValueError):
        module._check_constructor_input_mode(args, delivery)
