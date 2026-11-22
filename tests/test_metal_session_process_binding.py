"""Identical scientific inputs must not make process owners interchangeable."""
import shutil
from uuid import UUID
from unittest.mock import patch
import pytest
from nasolve import campaign_records as records
from nasolve.metal import child_session as m, parent_archive as p
from nasolve.metal.recipe import RecipeError
from tests.test_metal_session_budget import setup, run, inspect, ALLOWANCE


def header(root, component):
    name = 'preflight.json' if component == 'preflight' else 'child.json'
    return records.read_record(root/component/'ownership'/name)


def test_budgeted_processes_bind_declaration_and_reservation_before_launch(tmp_path, monkeypatch):
    values, native, parent_options, options = setup(tmp_path, monkeypatch)
    fresh = m._fresh_scattering
    def checked(*args, **kwargs):
        declaration = records.read_record(tmp_path/'session/request.json')
        admission = records.read_record(tmp_path/'session/storage-admission.json')
        expected = dict(request_sha256=declaration['record_sha256'],
                        attempt_sha256=admission['reservation_id'],
                        attempt_id=str(UUID(hex=admission['grant']['nonce'])))
        assert declaration['process_attempt_id'] == expected['attempt_id']
        assert header(tmp_path/'session', 'preflight')['attempt_owner'] == expected
        return fresh(*args, **kwargs)
    monkeypatch.setattr(m, '_fresh_scattering', checked)
    with p.retained_parent_inputs(values[1], values[3]['parent_manifest_sha256'], storage_budget=parent_options) as parent:
        review = run(tmp_path, values, native, parent, options)
    first = header(tmp_path/'session', 'preflight')['attempt_owner']
    assert header(tmp_path/'session', 'attempt')['attempt_owner'] == first
    assert m.inspect_audited_child(tmp_path/'session', review_id=review['record_sha256'])['new_native_calls'] == 0
    assert inspect(options)['outstanding_bytes'] == ALLOWANCE


@pytest.mark.parametrize('component', ['preflight', 'attempt'])
def test_identical_science_from_other_reservation_cannot_supply_inner_stop(tmp_path, monkeypatch, component):
    values, native, parent_options, options = setup(tmp_path, monkeypatch, 'metadata' if component == 'preflight' else None)
    with p.retained_parent_inputs(values[1], values[3]['parent_manifest_sha256'], storage_budget=parent_options) as parent:
        for name in ('first', 'second'):
            with patch.object(m, '_audit_job', side_effect=RecipeError('Synthetic postflight failure')):
                with pytest.raises(RecipeError):
                    run(tmp_path, values, native, parent, options, name)
    declarations = [records.read_record(tmp_path/name/'request.json') for name in ('first', 'second')]
    assert declarations[0]['request'] == declarations[1]['request']
    root = tmp_path/'first'
    read = m._failed_preflight_stop_evidence if component == 'preflight' else m._failed_stop_evidence
    read(root, declarations[0])
    (root/component).rename(root/(component+'-original-retained'))
    shutil.copytree(tmp_path/'second'/component, root/component)
    with pytest.raises(RecipeError, match='process owner'):
        read(root, declarations[0])
    failure = records.read_record(root/'failure.json')
    with pytest.raises(RecipeError):
        m.inspect_failed_audited_child(root, failure_id=failure['record_sha256'])
    assert inspect(options)['outstanding_bytes'] == 2*ALLOWANCE


@pytest.mark.parametrize('change', ['missing', 'null', 'bad-uuid', 'other-reservation', 'other-declaration'])
def test_bound_process_cannot_be_downgraded_or_rebound(tmp_path, monkeypatch, change):
    values, native, parent_options, options = setup(tmp_path, monkeypatch, 'metadata')
    with p.retained_parent_inputs(values[1], values[3]['parent_manifest_sha256'], storage_budget=parent_options) as parent:
        with pytest.raises(RecipeError):
            run(tmp_path, values, native, parent, options)
    root = tmp_path/'session'
    declaration = records.read_record(root/'request.json')
    if change == 'missing': declaration.pop('process_attempt_id')
    elif change == 'null': declaration['process_attempt_id'] = None
    elif change == 'bad-uuid': declaration['process_attempt_id'] = 'not-an-attempt'
    elif change == 'other-reservation': declaration['storage_reservation']['reservation_id'] = '0'*64
    else: declaration['record_sha256'] = '0'*64
    with pytest.raises(RecipeError, match='[Pp]rocess|attempt identity'):
        m._failed_preflight_stop_evidence(root, declaration)
    assert inspect(options)['outstanding_bytes'] == ALLOWANCE


def test_launch_binding_does_not_replace_missing_terminal_receipt(tmp_path, monkeypatch):
    from nasolve.metal import storage_budget as b
    from nasolve.metal.session_diagnostics import diagnose_session_reservation
    values, native, parent_options, options = setup(tmp_path, monkeypatch, 'metadata')
    write = records.write_record
    def interrupted(path, value, **kwargs):
        if path.name == 'failure.json': raise OSError('Terminal publication interrupted')
        return write(path, value, **kwargs)
    with p.retained_parent_inputs(values[1], values[3]['parent_manifest_sha256'], storage_budget=parent_options) as parent:
        with patch.object(records, 'write_record', side_effect=interrupted):
            with pytest.raises(OSError, match='Terminal publication'):
                run(tmp_path, values, native, parent, options)
    root = tmp_path/'session'
    declaration = records.read_record(root/'request.json')
    proof = m._failed_preflight_stop_evidence(root, declaration)
    assert proof['native_not_started_verified']
    assert header(root, 'preflight')['attempt_owner']['request_sha256'] == declaration['record_sha256']
    admission = records.read_record(root/'storage-admission.json')
    args = dict(budget_id=options['budget_id'], reservation_id=admission['reservation_id'])
    before = (tmp_path/'.metal-budget/ledger.json').read_bytes()
    with patch('nasolve.cif_repair_process.coordinator_alive', side_effect=AssertionError('No PID recovery')):
        report = diagnose_session_reservation(tmp_path, **args)
        assert report['status'] == 'HELD_BLOCKED'
        with pytest.raises((RecipeError, OSError)):
            b.settle_failed_audited_session(tmp_path, failure_id='0'*64, **args)
    assert (tmp_path/'.metal-budget/ledger.json').read_bytes() == before
    assert inspect(options)['outstanding_bytes'] == ALLOWANCE
