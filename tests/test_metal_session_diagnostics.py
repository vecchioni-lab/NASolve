"""Held-session explanations preserve output and cannot substitute for settlement."""
import importlib
import json
from unittest.mock import patch
import pytest
from nasolve import campaign_records as records
from nasolve.metal import parent_archive as p,storage_budget as b,child_session as m
from nasolve.metal.recipe import RecipeError
from tests.test_metal_session_budget import setup,run,inspect,ALLOWANCE
from tests.test_metal_preflight_failure_budget import failed_preflight
from tests.test_metal_failed_session_budget import settle
from tests.test_metal_child_process import inventory


def diagnose(root,options,failure=None):
    module=importlib.import_module('nasolve.metal.session_diagnostics')
    ledger=records.read_record(root/'.metal-budget/ledger.json')
    reservation_id=next(k for k,v in ledger['reservations'].items() if v['grant'].get('session')=='session')
    return module.diagnose_session_reservation(root,budget_id=options['budget_id'],
        reservation_id=reservation_id,failure_id=None if failure is None else failure['record_sha256'])


def stopped(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    return options,failure


def test_stopped_diagnosis_does_not_settle_and_relocates(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch);before=inventory(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('No process calls')):
        with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No PID query')):
            value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_READY_FOR_EXPLICIT_SETTLEMENT' and value['blockers']==[]
    assert value['outstanding_allowance_bytes']==ALLOWANCE and value['release_authorized'] is False
    assert value['observed_failure_id']==failure['record_sha256'] and value['failure_pin_matched']
    assert inventory(tmp_path)==before and inspect(options)['outstanding_bytes']==ALLOWANCE
    moved=tmp_path.with_name(tmp_path.name+'-moved');tmp_path.rename(moved)
    assert not tmp_path.exists() and diagnose(moved,options,failure)==value
    assert str(tmp_path) not in json.dumps(value)
    proof=settle(moved,options,failure);assert proof['native_not_started_verified']
    assert diagnose(moved,options,failure)['status']=='ALREADY_SETTLED'


@pytest.mark.parametrize('defect,code,relative',[
 ('outer','MISSING_RECEIPT','session/preflight/ownership/finished.json'),
 ('phase','MISSING_RECEIPT','session/preflight/ownership/phases/native-observations/finished.json'),
 ('malformed-phase','INVALID_RECEIPT','session/preflight/ownership/phases/native-observations/finished.json'),
 ('failure','MISSING_RECEIPT','session/failure.json'),
 ('request','MISSING_RECEIPT','session/request.json'),
 ('copied-admission','BINDING_NOT_VERIFIED','session/storage-admission.json'),
 ('changed-input','RELEASE_PROOF_NOT_VERIFIED','session/failure.json'),
 ('late-child','UNEXPECTED_MAIN_CHILD','session/attempt'),
 ('review','REVIEW_PRESENT','session/review.json'),
 ('no-captured-proof','FAILURE_STOP_PROOF_ABSENT','session/failure.json'),
])
def test_specific_receipt_blockers_preserve_every_file(tmp_path,monkeypatch,defect,code,relative):
    options,failure=stopped(tmp_path,monkeypatch);s=tmp_path/'session'
    if defect=='outer':(s/'preflight/ownership/finished.json').unlink()
    elif defect=='phase':(s/'preflight/ownership/phases/native-observations/finished.json').unlink()
    elif defect=='malformed-phase':(s/'preflight/ownership/phases/native-observations/finished.json').write_text('{}')
    elif defect=='failure':(s/'failure.json').unlink()
    elif defect=='request':(s/'request.json').unlink()
    elif defect=='copied-admission':
        v=records.read_record(s/'storage-admission.json');v['reservation_id']='f'*64;records.write_record(s/'storage-admission.json',v,replace=True)
    elif defect=='changed-input':(s/'preflight/inputs/input.pdb').write_text('changed')
    elif defect=='late-child':(s/'attempt').mkdir()
    elif defect=='review':records.write_record(s/'review.json',dict(ambiguous=True))
    else:
        failure=records.write_record(s/'failure.json',dict(failure,process_stop_evidence=None),replace=True)
    before=inventory(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('No process calls')):
        with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No historical PID query')):
            with patch('nasolve.cif_repair_process.coordinator_alive',side_effect=AssertionError('No historical coordinator query')):
                value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_BLOCKED' and not value['release_authorized']
    assert any(x['code']==code and x['reference']==dict(anchor='store',relative_path=relative) for x in value['blockers'])
    assert inventory(tmp_path)==before and inspect(options)['outstanding_bytes']==ALLOWANCE


def test_unpinned_or_wrong_failure_cannot_be_ready(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch)
    assert any(x['code']=='FAILURE_PIN_REQUIRED' for x in diagnose(tmp_path,options)['blockers'])
    assert any(x['code']=='FAILURE_PIN_MISMATCH' for x in diagnose(tmp_path,options,dict(record_sha256='f'*64))['blockers'])
    assert inspect(options)['outstanding_bytes']==ALLOWANCE


def test_unknown_stop_lists_the_missing_phase_without_querying_pid(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    before=inventory(tmp_path)
    with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No PID query')):
        value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_BLOCKED'
    assert any(x.get('phase')=='native-observations' for x in value['blockers'])
    assert inventory(tmp_path)==before and inspect(options)['outstanding_bytes']==ALLOWANCE


def test_prior_native_failure_uses_existing_reader(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(m,'_audit_job',side_effect=RecipeError('Scientific rejection')):
            with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_READY_FOR_EXPLICIT_SETTLEMENT' and value['failure_stage']=='SCIENTIFIC_AUDIT'
    (tmp_path/'session/attempt/ownership/phases/native-fdp/finished.json').unlink()
    value=diagnose(tmp_path,options,failure)
    assert any(x.get('phase')=='native-fdp' and x['code']=='MISSING_RECEIPT' for x in value['blockers'])
    assert inspect(options)['outstanding_bytes']==ALLOWANCE


def test_cli_is_read_only_and_reports_a_pinned_ready_case(tmp_path,monkeypatch,capsys):
    options,failure=stopped(tmp_path,monkeypatch);before=inventory(tmp_path)
    from nasolve.metal.session_diagnostics import main
    admission=records.read_record(tmp_path/'session/storage-admission.json')
    assert main([str(tmp_path),'--budget-id',options['budget_id'],'--reservation-id',admission['reservation_id'],
                 '--failure-id',failure['record_sha256']])==0
    value=json.loads(capsys.readouterr().out)
    assert value['status']=='HELD_READY_FOR_EXPLICIT_SETTLEMENT' and not value['release_authorized']
    assert inventory(tmp_path)==before


def test_malformed_stage_is_a_receipt_blocker(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch)
    failure=records.write_record(tmp_path/'session/failure.json',dict(failure,stage={}),replace=True)
    value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_BLOCKED'
    assert any(x['code']=='INVALID_RECEIPT' and x['reference']['relative_path']=='session/failure.json' for x in value['blockers'])


def test_extra_phase_is_named_without_opening_or_querying_it(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch)
    (tmp_path/'session/preflight/ownership/phases/unexpected').mkdir()
    with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No process query')):
        value=diagnose(tmp_path,options,failure)
    assert any(x['code']=='UNEXPECTED_PHASES' for x in value['blockers'])
    assert inspect(options)['outstanding_bytes']==ALLOWANCE


def test_read_only_diagnosis_does_not_recreate_missing_lock(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch);lock=tmp_path/'.metal-budget.lock';lock.unlink()
    before=inventory(tmp_path)
    with pytest.raises(RecipeError,match='Existing budget lock'):diagnose(tmp_path,options,failure)
    assert inventory(tmp_path)==before and not lock.exists()


def test_receipt_symlink_is_refused_without_touching_target(tmp_path,monkeypatch):
    options,failure=stopped(tmp_path,monkeypatch)
    phase=tmp_path/'session/preflight/ownership/phases/native-observations/finished.json';saved=phase.read_bytes();phase.unlink();target=tmp_path/'external';target.write_bytes(saved);phase.symlink_to(target)
    value=diagnose(tmp_path,options,failure)
    assert value['status']=='HELD_BLOCKED' and any(x['code']=='INVALID_RECEIPT' for x in value['blockers'])
    assert target.read_bytes()==saved and phase.is_symlink()
