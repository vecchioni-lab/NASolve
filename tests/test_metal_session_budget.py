"""A complete audited session, not just its native child, owns this allowance."""
from unittest.mock import patch
import pytest
from nasolve import campaign_records as records
from nasolve.metal import storage_budget as b,parent_archive as p,child_session as m
from nasolve.metal.recipe import RecipeError
from tests.test_metal_owned_preflight import owned_setup
from tests.test_metal_child_process import inventory

ALLOWANCE=40*1024*1024


def setup(tmp_path,monkeypatch,defect=None,quota=1024**3):
    values,native=owned_setup(tmp_path,monkeypatch,defect)
    config=b.create_budget(tmp_path,quota_bytes=quota,free_space_reserve_bytes=0,
                           include_retained_parents=True,include_audited_sessions=True)
    pin=config['record_sha256'];parent_options=dict(directory=tmp_path,budget_id=pin,scope='shared-parent',allowance_bytes=p.DEFAULT_DISK_BYTES+1024*1024)
    options=dict(directory=tmp_path,budget_id=pin,allowance_bytes=ALLOWANCE)
    return values,native,parent_options,options


def run(tmp_path,values,native,parent,options,name='session',**kwargs):
    return m.run_audited_child(values[2],values[1],values[3],request_id=values[3]['request_id'],
        run_relative='dataset/AutoMR/run_001',endpoint_relative='Metal/xyz_001',session_directory=tmp_path/name,
        native=native,timeout_seconds=5,retained_parent=parent,owned_preflight=True,
        max_output_bytes=1_000_000,storage_budget=options,**kwargs)


def inspect(options):return b.inspect_budget(options['directory'],budget_id=options['budget_id'])


def settle(tmp_path,options,name,review):
    admission=records.read_record(tmp_path/name/'storage-admission.json')
    return b.settle_audited_session(tmp_path,budget_id=options['budget_id'],reservation_id=admission['reservation_id'],review_id=review['record_sha256'])


def test_complete_sessions_hold_until_reviewed_settlement_without_releasing_parent(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        for name in ('first','second'):
            report=run(tmp_path,values,native,parent,options,name)
            state=inspect(options)
            assert state['schema_version']==3 and state['held_by_scope']=={'child':0,'retained_parent':1,'audited_session':1}
            assert state['outstanding_by_scope']['audited_session']==ALLOWANCE
            before=inventory(tmp_path/name)
            proof=settle(tmp_path,options,name,report)
            assert proof['postflight_review_complete'] and proof['preflight_stopped_verified'] and not proof['retirement_authorized']
            assert settle(tmp_path,options,name,report)==proof
            assert inventory(tmp_path/name)==before and inspect(options)['outstanding_bytes']==parent_options['allowance_bytes']
    assert inspect(options)['outstanding_bytes']==0 and inspect(options)['settled_count']==3
    moved=tmp_path.with_name(tmp_path.name+'-moved');tmp_path.rename(moved);assert not tmp_path.exists()
    assert b.inspect_budget(moved,budget_id=options['budget_id'])['settled_count']==3


@pytest.mark.parametrize('defect',['metadata','uncertain','postflight','publication'])
def test_failed_or_unrecorded_session_stays_charged_after_parent_cleanup(tmp_path,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,defect)
    if defect=='uncertain':monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    elif defect=='postflight':monkeypatch.setattr(m,'_audit_job',lambda *a:(_ for _ in ()).throw(RecipeError('Postflight failed')))
    elif defect=='publication':
        write=records.write_record
        def interrupted(path,value,**kwargs):
            if path.name=='review.json':raise OSError('Review publication lost')
            return write(path,value,**kwargs)
        monkeypatch.setattr(records,'write_record',interrupted)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
        admission=records.read_record(tmp_path/'session/storage-admission.json')
        with pytest.raises((RecipeError,OSError)):
            b.settle_audited_session(tmp_path,budget_id=options['budget_id'],reservation_id=admission['reservation_id'],review_id='0'*64)
        with pytest.raises(RecipeError,match='child'):
            b.settle_child(tmp_path,budget_id=options['budget_id'],reservation_id=admission['reservation_id'])
    assert inspect(options)['outstanding_by_scope']=={'child':0,'retained_parent':0,'audited_session':ALLOWANCE}


def test_low_allowance_denies_before_native_inspection(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch);options['allowance_bytes']=1
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(m,'_fresh_scattering',side_effect=AssertionError('No native inspection')):
            with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
        assert not (tmp_path/'session').exists() and inspect(options)['held_by_scope']['audited_session']==0


def test_admission_already_exists_when_first_native_inspection_begins(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch);fresh=m._fresh_scattering
    def checked(*args,**kwargs):
        assert records.read_record(tmp_path/'session/storage-admission.json')['grant']['session']=='session'
        assert inspect(options)['outstanding_by_scope']['audited_session']==ALLOWANCE
        return fresh(*args,**kwargs)
    monkeypatch.setattr(m,'_fresh_scattering',checked)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
    assert inspect(options)['held_count']==1
    settle(tmp_path,options,'session',result)
    assert inspect(options)['held_count']==0


def test_compact_settlement_reopen_does_not_reaudit_native_arrays(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
    settled=settle(tmp_path,options,'session',result)
    with patch.object(m,'inspect_audited_child',side_effect=AssertionError('Ledger inspection is not scientific readback')):
        assert inspect(options)['outstanding_bytes']==0
        assert settle(tmp_path,options,'session',result)==settled


@pytest.mark.parametrize('defect',['wrong-review','admission','missing-preflight','same-request-other-session'])
def test_wrong_or_missing_scope_evidence_cannot_release(tmp_path,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
        if defect=='same-request-other-session':other=run(tmp_path,values,native,parent,options,'other')
    if defect=='wrong-review':result=dict(result,record_sha256='0'*64)
    elif defect=='admission':
        path=tmp_path/'session/storage-admission.json';value=records.read_record(path);value['grant']['request_id']='0'*64;records.write_record(path,value,replace=True)
    elif defect=='missing-preflight':(tmp_path/'session/preflight/inspection.json').unlink()
    else:result=other
    with pytest.raises((RecipeError,OSError)):settle(tmp_path,options,'session',result)
    assert inspect(options)['outstanding_by_scope']['audited_session']>=ALLOWANCE


def test_v3_requires_explicit_parent_profile_and_default_stays_v1(tmp_path):
    with pytest.raises(RecipeError):b.create_budget(tmp_path,quota_bytes=10**9,include_audited_sessions=True)
    assert not (tmp_path/'.metal-budget').exists()
    config=b.create_budget(tmp_path,quota_bytes=10**9)
    assert config['schema_version']==1


def test_busy_session_settlement_keeps_credit_until_explicit_retry(tmp_path,monkeypatch):
    from nasolve.campaign_process import exclusive_lock,CampaignProcessError
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
    before=inventory(tmp_path/'session')
    with exclusive_lock(tmp_path/b.LOCK):
        with pytest.raises(CampaignProcessError):settle(tmp_path,options,'session',result)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE
    settle(tmp_path,options,'session',result)
    assert inspect(options)['outstanding_bytes']==0 and inventory(tmp_path/'session')==before


def test_session_settlement_acknowledgement_gap_is_idempotent(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
    saved=b._save
    def interrupted(*args,**kwargs):
        value=saved(*args,**kwargs)
        raise OSError('Acknowledgement lost after publication')
    with patch.object(b,'_save',side_effect=interrupted):
        with pytest.raises(OSError,match='Acknowledgement'):settle(tmp_path,options,'session',result)
    assert inspect(options)['outstanding_bytes']==0
    with patch.object(m,'inspect_audited_child',side_effect=AssertionError('Already recorded settlement')):
        value=settle(tmp_path,options,'session',result)
    assert value['review_sha256']==result['record_sha256']


def test_completed_but_unsettled_session_still_competes_for_space(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,quota=310*1024*1024)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        result=run(tmp_path,values,native,parent,options)
        with patch.object(m,'_fresh_scattering',side_effect=AssertionError('No inspection before admission')):
            with pytest.raises(RecipeError,match='budget'):run(tmp_path,values,native,parent,options,'denied')
        assert not (tmp_path/'denied').exists()
        settle(tmp_path,options,'session',result)
        second=run(tmp_path,values,native,parent,options,'second')
        settle(tmp_path,options,'second',second)
    assert inspect(options)['outstanding_bytes']==0


def test_another_completed_session_cannot_supply_release_for_failed_scope(tmp_path,monkeypatch):
    import shutil
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(m,'_audit_job',side_effect=RecipeError('Unresolved first postflight')):
            with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options,'first')
        first_admission=(tmp_path/'first/storage-admission.json').read_bytes()
        other=run(tmp_path,values,native,parent,options,'other')
    # Deliberate copied evidence attack in a disposable fixture: valid same-request
    # science cannot establish that a different grant reached its own completion.
    shutil.copytree(tmp_path/'other',tmp_path/'first',dirs_exist_ok=True)
    (tmp_path/'first/storage-admission.json').write_bytes(first_admission)
    with pytest.raises(RecipeError,match='reservation'):
        settle(tmp_path,options,'first',other)
    assert inspect(options)['outstanding_by_scope']['audited_session']==2*ALLOWANCE
