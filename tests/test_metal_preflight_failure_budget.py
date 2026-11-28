"""Known-stopped partial input checks release headroom, never scientific or file claims."""
from unittest.mock import patch
import shutil
import pytest
from nasolve import campaign_records as records
from nasolve.metal import child_session as m,storage_budget as b,parent_archive as p,preflight_process as pre
from nasolve.metal.recipe import RecipeError
from tests.test_metal_session_budget import setup,run,inspect,ALLOWANCE
from tests.test_metal_failed_session_budget import settle
from tests.test_metal_child_process import inventory


def failed_preflight(tmp_path,values,native,parent,options,name='session'):
    with patch.object(m.child_process,'run_child',side_effect=AssertionError('No main child')):
        with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options,name)
    assert not (tmp_path/name/'attempt').exists()
    return records.read_record(tmp_path/name/'failure.json')


@pytest.mark.parametrize('defect',['metadata','timeout','before-launch','scattering','free-r','lost-inspection'])
def test_stopped_partial_preflight_releases_only_explicit_session_headroom(tmp_path,tmp_path_factory,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,defect)
    if defect=='before-launch':monkeypatch.setattr(m,'_fresh_scattering',lambda *a,**k:(_ for _ in ()).throw(RecipeError('Before launch')))
    if defect=='scattering':monkeypatch.setattr(m,'_check_scattering_record',lambda *a:(_ for _ in ()).throw(RecipeError('Scattering comparison failed')))
    if defect=='free-r':
        audit=m.audit_free_r_flags
        def rejected_flags(*a,**k):
            from types import SimpleNamespace
            value=audit(*a,**k)
            return SimpleNamespace(valid=False,status=value.status,details=value.details,warnings=value.warnings)
        monkeypatch.setattr(m,'audit_free_r_flags',rejected_flags)
    if defect=='lost-inspection':
        write=records.write_record
        def lost(path,value,**kwargs):
            if path.name=='inspection.json':raise OSError('Lost input inspection publication')
            return write(path,value,**kwargs)
        monkeypatch.setattr(records,'write_record',lost)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
        before=inventory(tmp_path/'session')
        proof=settle(tmp_path,options,failure)
        assert failure['schema_version']==3 and failure['stage']=='FRESH_INPUT_INSPECTION'
        assert proof['native_not_started_verified'] and proof['preflight_stopped_verified']
        assert proof['postflight_review_complete'] is False and not proof['retirement_authorized']
        assert 'native_stopped_verified' not in proof and 'native_outcome_sha256' not in proof
        assert inventory(tmp_path/'session')==before
        assert inspect(options)['outstanding_bytes']==parent_options['allowance_bytes']
    assert inspect(options)['outstanding_bytes']==0
    moved=tmp_path_factory.mktemp('preflight-relocation')/'moved';tmp_path.rename(moved);assert not tmp_path.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('No native calls')):
        with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No historical PID queries')):
            read=m.inspect_failed_audited_child(moved/'session',failure_id=failure['record_sha256'])
            assert read['native_not_started_verified'] and read['stage']=='FRESH_INPUT_INSPECTION'
            with patch.object(m,'inspect_failed_audited_child',side_effect=AssertionError('Already settled')):
                assert settle(moved,options,failure)==proof
                assert b.inspect_budget(moved,budget_id=options['budget_id'])['outstanding_bytes']==0


@pytest.mark.parametrize('defect',['missing-outer','missing-phase','changed-log','changed-input','old-version','attempt-present','review-present','copied-session'])
def test_partial_preflight_release_requires_exact_sealed_scope(tmp_path,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
        if defect=='copied-session':other=failed_preflight(tmp_path,values,native,parent,options,'other')
    root=tmp_path/'session'
    if defect=='missing-outer':(root/'preflight/ownership/finished.json').unlink()
    elif defect=='missing-phase':(root/'preflight/ownership/phases/native-observations/finished.json').unlink()
    elif defect=='changed-log':(root/'preflight/native/observations/job/native.log').write_text('changed')
    elif defect=='changed-input':(root/'preflight/inputs/input.pdb').write_text('changed')
    elif defect=='attempt-present':(root/'attempt').mkdir()
    elif defect=='review-present':records.write_record(root/'review.json',dict(ambiguous=True))
    elif defect=='old-version':
        failure=dict(failure,schema_version=2);failure=records.write_record(root/'failure.json',failure,replace=True)
    else:
        admission=(root/'storage-admission.json').read_bytes();shutil.copytree(tmp_path/'other',root,dirs_exist_ok=True);(root/'storage-admission.json').write_bytes(admission);failure=other
    with patch('nasolve.cif_repair_process.coordinator_alive',side_effect=AssertionError('No historical coordinator query')):
        with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No historical process query')):
            with pytest.raises((RecipeError,OSError)):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_by_scope']['audited_session']>=ALLOWANCE


def test_unknown_preflight_process_stop_keeps_allowance_and_original_error(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    assert failure['process_stop_evidence'] is None and 'stop uncertain' in failure['message']
    with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_by_scope']['audited_session']==ALLOWANCE


def test_preflight_release_rechecks_no_child_before_ledger_write(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    reader=m.inspect_failed_audited_child;calls=[]
    def changed(*a,**k):
        calls.append(1)
        if len(calls)==2:(tmp_path/'session/attempt').mkdir()
        return reader(*a,**k)
    with patch.object(m,'inspect_failed_audited_child',side_effect=changed):
        with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert len(calls)==2 and inspect(options)['outstanding_by_scope']['audited_session']==ALLOWANCE


def test_preflight_settlement_acknowledgement_loss_is_idempotent(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    save=b._save
    def lost(*a):save(*a);raise OSError('Acknowledgement lost')
    with patch.object(b,'_save',side_effect=lost):
        with pytest.raises(OSError,match='Acknowledgement'):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==0
    with patch.object(m,'inspect_failed_audited_child',side_effect=AssertionError('Already settled')):
        assert settle(tmp_path,options,failure)['failure_sha256']==failure['record_sha256']


@pytest.mark.parametrize('defect',['malformed-phase','missing-phase'])
def test_failed_closure_capture_does_not_replace_original_input_error(tmp_path,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    original=pre.run_preflight
    def damaged(*a,**k):
        try:return original(*a,**k)
        finally:
            path=tmp_path/'session/preflight/ownership/phases/native-observations/finished.json'
            if defect=='missing-phase':path.unlink()
            else:
                value=records.read_record(path);value['elapsed_seconds']='bad';records.write_record(path,value,replace=True)
    monkeypatch.setattr(pre,'run_preflight',damaged)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=failed_preflight(tmp_path,values,native,parent,options)
    assert failure['process_stop_evidence'] is None and 'Fresh observation metadata' in failure['message']
    with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE
