"""Diagnostics explain existing decisions without reclassifying chemistry."""
from copy import deepcopy

import pytest


def diagnose(report):
    from nasolve.cif_source_candidate import candidate_generation_diagnostic
    before = deepcopy(report)
    result = candidate_generation_diagnostic(report)
    assert report == before
    assert result['automatic_adoption'] is False
    assert result['native_usability'] == 'NOT_ASSESSED_BY_DIAGNOSTIC'
    return result


def blocked_handoff():
    return {'status': 'FAILED', 'candidate': None,
            'execution': {'status': 'COMPLETED', 'returncode': 0},
            'result': {'reader': {'execution': 'COMPLETED'},
                       'charge_control': {'status': 'BLOCKED', 'preconditions': {
                           'reader_route': True, 'bond_orders': False, 'coordinates': True}},
                       'builder': {'status': 'EXCEPTION', 'exception_type': 'ValueError',
                                   'message': 'Declared source charge handoff failed'}}}


def test_graph_handoff_is_not_reported_as_charge_or_optimizer_failure():
    result = diagnose(blocked_handoff())
    assert result['blocking_stage'] == 'SOURCE_HANDOFF'
    assert result['failed_handoff_checks'] == ['bond_orders']
    assert result['builder_started'] is False
    assert result['candidate_state'] == 'ABSENT'
    assert 'bond_orders' in result['summary']
    assert 'charge handoff failed' in result['native_exception']['message']


@pytest.mark.parametrize('checks', [
    {'atom_charge_values': False, 'other_native_fields_preserved': True},
    {'atom_charge_values': True, 'other_native_fields_preserved': False},
])
def test_failed_population_checks_are_distinct_from_reader_preconditions(checks):
    report = blocked_handoff()
    report['result']['charge_control'].update(status='REVIEW', preconditions={'bond_orders': True}, checks=checks)
    result = diagnose(report)
    assert result['blocking_stage'] == 'SOURCE_HANDOFF'
    assert result['failed_handoff_checks'] == sorted(k for k, value in checks.items() if value is False)


@pytest.mark.parametrize('field', ['bond_orders', 'hydrogen_attachments', 'atom_elements'])
def test_combined_rejection_names_only_the_actual_changed_identity_field(field):
    report = {'status': 'REJECTED', 'candidate': {'path': 'candidate.cif'},
              'inspection': {'status': 'REJECTED', 'rejection_reasons': [
                  'generated-atom-bond-or-hydrogen-identity-changed'],
                  'chemical_changes': [{'field': field}, {'field': 'atom_stereo_declarations'}],
                  'bond_representation': {'status': 'UNSUPPORTED_DIFFERENCE'}}}
    result = diagnose(report)
    assert result['blocking_stage'] == 'CANDIDATE_ASSESSMENT'
    assert result['identity_change_fields'] == [field]
    assert result['candidate_state'] == 'RETAINED_REJECTED'
    assert field in result['summary']


def test_allowed_aromatic_representation_is_not_an_identity_blocker():
    result = diagnose({'status': 'REJECTED', 'candidate': {'path': 'candidate.cif'},
                       'inspection': {'status': 'REJECTED', 'rejection_reasons': ['generated-restraints-invalid-or-incomplete'],
                                      'chemical_changes': [{'field': 'bond_orders'}],
                                      'bond_representation': {'status': 'SOURCE_DECLARED_EQUIVALENT'}}})
    assert result['identity_change_fields'] == []
    assert result['rejection_reasons'] == ['generated-restraints-invalid-or-incomplete']


@pytest.mark.parametrize('execution', ['COMPLETED', 'FAILED', 'TIMED_OUT'])
def test_retained_review_candidate_survives_execution_or_postoutput_exception(execution):
    result = diagnose({'status': 'CANDIDATE_REVIEW', 'candidate': {'path': 'candidate.cif'},
                       'execution': {'status': execution, 'returncode': 0 if execution == 'COMPLETED' else -15},
                       'result': {'builder': {'status': 'EXCEPTION', 'before': {'atoms': []},
                                             'exception_type': 'RuntimeError', 'message': 'after output'}}})
    assert result['candidate_state'] == 'RETAINED_REVIEW'
    assert result['blocking_stage'] is None
    assert result['native_exception']['message'] == 'after output'
    assert result['builder_started'] is True


@pytest.mark.parametrize('kind,stage', [
    ('reader', 'SOURCE_READER'), ('builder', 'NATIVE_BUILDER'),
    ('timeout', 'EXECUTION'), ('error', 'ADAPTER'), ('unknown', 'UNDETERMINED'),
])
def test_no_output_distinguishes_known_failure_stages(kind, stage):
    report = {'status': 'FAILED', 'candidate': None}
    if kind == 'reader':
        report['result'] = {'reader': {'execution': 'NOT_RUN'}, 'builder': {'status': 'EXCEPTION', 'message': 'parse failed'}}
    if kind == 'builder':
        report['result'] = {'reader': {'execution': 'COMPLETED'},
                            'charge_control': {'status': 'DECLARED_CHARGE_CONTROL_PASS'},
                            'builder': {'status': 'EXCEPTION', 'before': {'atoms': []}, 'message': 'Bond length too long : 8.92'}}
    if kind == 'timeout':report['execution'] = {'status': 'TIMED_OUT', 'returncode': -15}
    if kind == 'error':report['error'] = 'ValueError: unsupported generator options'
    result = diagnose(report)
    assert result['blocking_stage'] == stage
    assert result['candidate_state'] == 'ABSENT'


def test_failed_integrity_with_retained_output_is_unassessed():
    result = diagnose({'status': 'FAILED', 'candidate': {'path': 'candidate.cif'},
                       'error': 'Source/dispatcher changed', 'source_preserved': False})
    assert result['candidate_state'] == 'RETAINED_UNASSESSED'
    assert result['blocking_stage'] == 'ADAPTER'


def test_additional_charge_and_stereo_rejections_are_not_lost():
    result = diagnose({'status': 'REJECTED', 'candidate': {'path': 'candidate.cif'},
                       'formal_charges_preserved': False,
                       'finished_stereo': {'stereochemistry': 'INVERTED'},
                       'inspection': {'rejection_reasons': [], 'chemical_changes': []}})
    assert result['rejection_reasons'] == ['complete-formal-charges-not-preserved', 'finished-source-relative-stereo-inverted']
    assert result['blocking_stage'] == 'CANDIDATE_ASSESSMENT'


def test_diagnostic_does_not_trust_its_own_previous_summary():
    report = blocked_handoff()
    result = diagnose(report)
    report['diagnostic'] = {'blocking_stage': None, 'automatic_adoption': True}
    assert diagnose(report) == result


@pytest.mark.parametrize('mode', ['legacy', 'tampered'])
def test_candidate_diagnostic_is_optional_but_recomputed_when_present(tmp_path, monkeypatch, mode):
    import json
    from tests.test_cif_mixed_recovery import parent_fixture, fake_builder_installation
    from nasolve.cif_mixed_recovery import audit_mixed_recovery, read_mixed_recovery, _ref
    parent, _, _ = parent_fixture(tmp_path, monkeypatch)
    phenix = fake_builder_installation(tmp_path, parent/'inputs/Q17_bad.cif')
    out = tmp_path/'result'
    report = audit_mixed_recovery(parent, phenix, out, timeout_seconds=10)
    generation = report['components']['Q17']['generation']
    assert generation['diagnostic']['blocking_stage'] == 'CANDIDATE_ASSESSMENT'
    if mode == 'legacy':generation.pop('diagnostic')
    else:generation['diagnostic']['blocking_stage'] = None
    receipt = out/generation['directory']['path']/'source_candidate_receipt.json'
    receipt.write_text(json.dumps({k:v for k,v in generation.items() if k != 'directory'}))
    report['outputs'] = [_ref(receipt,out) if row['path'] == receipt.relative_to(out).as_posix() else row
                         for row in report['outputs']]
    (out/'mixed_recovery.json').write_text(json.dumps(report))
    if mode == 'legacy':assert read_mixed_recovery(out) == report
    else:
        with pytest.raises(ValueError, match='candidate diagnostic differs'):
            read_mixed_recovery(out)


@pytest.mark.parametrize('execution', ['FAILED', 'TIMED_OUT'])
def test_missing_worker_result_keeps_builder_start_unknown(execution):
    result = diagnose({'status': 'FAILED', 'candidate': None,
                       'execution': {'status': execution, 'returncode': -15}})
    assert result['builder_started'] is None
    assert result['blocking_stage'] == 'EXECUTION'
