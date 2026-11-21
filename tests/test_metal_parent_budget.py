"""The ordinary parent lifetime, recorded closure and budget settlement are distinct."""
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch
import importlib
import os
import pytest
from nasolve import campaign_records as records
from nasolve.campaign_process import CampaignProcessError
from nasolve.metal import parent_archive as p,storage_budget as b
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_process import setup,invoke,inventory


def owner():return importlib.import_module('nasolve.metal.parent_budget')


def configured(tmp_path):
    values=setup(tmp_path)
    config=b.create_budget(tmp_path,quota_bytes=1024**3,free_space_reserve_bytes=0,include_retained_parents=True)
    options=dict(directory=tmp_path,budget_id=config['record_sha256'],scope='parent-one',allowance_bytes=p.DEFAULT_DISK_BYTES+1024*1024)
    return values,options


def retain(values,options):
    return p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256'],storage_budget=options)


def budget(options):return b.inspect_budget(options['directory'],budget_id=options['budget_id'])


def inspect(options,info):
    return owner().inspect_parent_closure(options['directory'],budget_id=options['budget_id'],
        reservation_id=info['reservation_id'],closure_id=info['closure_id'])


def test_normal_owner_closes_and_reopens_without_reusing_old_scope(tmp_path):
    values,options=configured(tmp_path);original=inventory(values[1])
    with retain(values,options) as retained:
        info=retained.storage_budget
        assert info['state']=='ACTIVE' and budget(options)['outstanding_bytes']==options['allowance_bytes']
        with pytest.raises(TypeError):info['state']='SETTLED'
        for _ in range(2):
            with p.read_parent_inputs(values[1],values[2]['parent_manifest_sha256'],retained_parent=retained) as (root,read):
                assert (root/'model.pdb').read_bytes()==b'Protected test parent\n'
            assert read['read_scope_closed'] and not read['snapshot_removed']
        assert budget(options)['held_by_scope']['retained_parent']==1
    assert info['state']=='SETTLED' and budget(options)['outstanding_bytes']==0
    assert not retained.active and not retained.root.exists()
    report=inspect(options,info);closure=report['closure'];measure=closure['measurement']
    assert report['settled'] and report['scratch_absent_now']
    assert closure['managed_reads_closed'] and closure['handle_expired'] and closure['snapshot_removed']
    assert measure['logical_bytes']==22 and measure['file_count']==1
    assert measure['free_space_delta_bytes']==measure['free_bytes_after']-measure['free_bytes_before']
    assert measure['physical_reclaim_verified'] is False
    first=inventory(tmp_path/'parent-one')
    again=dict(options,scope='parent-two')
    with retain(values,again) as second:
        assert second.scope_id!=retained.scope_id
        assert second.storage_budget['reservation_id']!=info['reservation_id']
    assert budget(options)['outstanding_bytes']==0 and inventory(tmp_path/'parent-one')==first
    assert inventory(values[1])==original
    with pytest.raises(ValueError):p.retained_parent_binding(retained,values[1],values[2]['parent_manifest_sha256'])


def test_read_interruption_can_clean_space_without_accepting_science(tmp_path):
    values,options=configured(tmp_path)
    with pytest.raises(RuntimeError,match='consumer interruption'):
        with retain(values,options) as retained:
            info=retained.storage_budget
            with p.read_parent_inputs(values[1],values[2]['parent_manifest_sha256'],retained_parent=retained):
                raise RuntimeError('consumer interruption')
    assert retained.invalidated and info['state']=='SETTLED'
    report=inspect(options,info)
    assert report['closure']['consumer_outcome']=='RAISED'
    assert report['closure']['scientific_acceptance']=='NOT_ASSESSED'
    assert budget(options)['outstanding_bytes']==0
    with retain(values,dict(options,scope='retry')) as retry:assert not retry.invalidated


def test_active_read_out_of_order_close_never_releases(tmp_path):
    values,options=configured(tmp_path);outer=retain(values,options);retained=outer.__enter__();info=retained.storage_budget
    reader=p.read_parent_inputs(values[1],values[2]['parent_manifest_sha256'],retained_parent=retained)
    root,_=reader.__enter__();opened=(root/'model.pdb').open('rb')
    try:
        with pytest.raises(ValueError,match='active read'):outer.__exit__(None,None,None)
        assert not root.exists() and opened.read()==b'Protected test parent\n'
        assert info['state']=='UNRESOLVED' and budget(options)['outstanding_bytes']==options['allowance_bytes']
        assert not (tmp_path/'parent-one/closure.json').exists()
    finally:
        opened.close()
        with pytest.raises(ValueError):reader.__exit__(None,None,None)
    assert budget(options)['held_count']==1


def test_cleanup_failure_holds_and_fresh_retry_preserves_failed_scope(tmp_path,monkeypatch):
    values,options=configured(tmp_path)
    class LeftBehind:
        def __init__(self,*args,**kwargs):self.name=mkdtemp(prefix='metal-parent-',dir=kwargs['dir'])
        def __enter__(self):return self.name
        def __exit__(self,*args):raise OSError('cleanup incomplete')
    with monkeypatch.context() as scoped:
        scoped.setattr(p,'TemporaryDirectory',LeftBehind)
        with pytest.raises(OSError,match='cleanup incomplete'):
            with retain(values,options) as retained:info=retained.storage_budget
    assert info['state']=='UNRESOLVED' and retained.root.exists()
    before=inventory(tmp_path/'parent-one')
    with retain(values,dict(options,scope='parent-two')) as second:pass
    assert second.storage_budget['state']=='SETTLED'
    assert budget(options)['outstanding_bytes']==options['allowance_bytes']
    assert inventory(tmp_path/'parent-one')==before
    with pytest.raises(ValueError):
        with retain(values,options):pytest.fail('An old scope was reused')


@pytest.mark.parametrize('mode',['success','uncertain','missing-outcome'])
def test_parent_cleanup_does_not_release_unresolved_child(tmp_path,monkeypatch,mode):
    values,options=configured(tmp_path)
    with retain(values,options) as retained:
        info=retained.storage_budget
        child=b.reserve_child(tmp_path,budget_id=options['budget_id'],child='attempt',request_id=values[2]['request_id'],
            allowance_bytes=1_000_000,parent_reservation_id=info['reservation_id'])
        if mode=='uncertain':
            with patch('nasolve.campaign_process._group_alive',return_value=None):result=invoke(tmp_path,values,retained_parent=retained)
            assert result['status']=='STOP_UNCERTAIN'
        elif mode=='missing-outcome':
            write=records.write_record
            def interrupted(path,value,**kwargs):
                if path.name=='outcome.json':raise OSError('missing outcome')
                return write(path,value,**kwargs)
            with patch.object(records,'write_record',side_effect=interrupted):
                with pytest.raises(OSError,match='missing outcome'):invoke(tmp_path,values,retained_parent=retained)
        else:
            result=invoke(tmp_path,values,retained_parent=retained)
            assert result['outcome']['parent_scope']['scope_id']==retained.scope_id
            b.settle_child(tmp_path,budget_id=options['budget_id'],reservation_id=child['reservation_id'])
        assert budget(options)['outstanding_by_scope']['retained_parent']==options['allowance_bytes']
    assert info['state']=='SETTLED'
    assert budget(options)['outstanding_by_scope']=={'retained_parent':0,'child':0 if mode=='success' else 1_000_000}
    if mode!='success':
        with pytest.raises(ValueError):b.settle_child(tmp_path,budget_id=options['budget_id'],reservation_id=child['reservation_id'])
    with pytest.raises(RecipeError,match='parent'):
        b.reserve_child(tmp_path,budget_id=options['budget_id'],child='later',request_id=values[2]['request_id'],
            allowance_bytes=100,parent_reservation_id=info['reservation_id'])


def test_busy_settlement_retries_from_closure_without_expansion(tmp_path):
    values,options=configured(tmp_path);m=owner()
    with patch.object(m,'settle_parent',side_effect=CampaignProcessError('lock busy')):
        with retain(values,options) as retained:info=retained.storage_budget
    assert info['state']=='CLOSED_HELD' and info['closure_id']
    assert not inspect(options,info)['settled']
    before=inventory(tmp_path/'parent-one')
    with patch.object(p,'materialized_parent_inputs',side_effect=AssertionError('No rematerialization')):
        first=m.settle_parent(tmp_path,budget_id=options['budget_id'],reservation_id=info['reservation_id'],closure_id=info['closure_id'])
        second=m.settle_parent(tmp_path,budget_id=options['budget_id'],reservation_id=info['reservation_id'],closure_id=info['closure_id'])
    assert first==second and inspect(options,info)['settled']
    assert inventory(tmp_path/'parent-one')==before


@pytest.mark.parametrize('stage',['opened.json','closure.json'])
def test_missing_proof_keeps_charge_even_after_cleanup(tmp_path,monkeypatch,stage):
    values,options=configured(tmp_path);write=records.write_record
    def interrupted(path,value,**kwargs):
        if path.name==stage:raise OSError('proof publication interrupted')
        return write(path,value,**kwargs)
    monkeypatch.setattr(records,'write_record',interrupted)
    with pytest.raises(OSError,match='proof publication'):
        with retain(values,options):pass
    assert budget(options)['outstanding_bytes']==options['allowance_bytes']
    assert not (tmp_path/'parent-one/closure.json').exists()


def test_hardlinked_snapshot_is_not_claimed_fully_released(tmp_path):
    values,options=configured(tmp_path)
    with pytest.raises(RecipeError,match='reference'):
        with retain(values,options) as retained:
            info=retained.storage_budget
            os.link(retained.root/'model.pdb',tmp_path/'external-link')
    assert (tmp_path/'external-link').read_bytes()==b'Protected test parent\n'
    assert info['state']=='UNRESOLVED' and budget(options)['held_count']==1


def test_closure_relocates_and_missing_evidence_blocks_accounting(tmp_path):
    values,options=configured(tmp_path)
    with retain(values,options) as retained:info=retained.storage_budget
    moved=tmp_path.with_name(tmp_path.name+'-'+info['reservation_id'][:10]);tmp_path.rename(moved)
    assert not tmp_path.exists();options=dict(options,directory=moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No native process on read')):
        assert inspect(options,info)['settled']
    (moved/'parent-one/opened.json').unlink()
    with pytest.raises((ValueError,OSError)):budget(options)


@pytest.mark.parametrize('defect',['active-reader','wrong-scope','false-reclaimed','free-delta','scratch-returned'])
def test_resealed_false_closure_cannot_settle(tmp_path,defect):
    values,options=configured(tmp_path);m=owner()
    with patch.object(m,'settle_parent',side_effect=CampaignProcessError('lock busy')):
        with retain(values,options) as retained:info=retained.storage_budget
    path=tmp_path/'parent-one/closure.json';value=records.read_record(path)
    if defect=='active-reader':value['managed_reads_closed']=False
    elif defect=='wrong-scope':value['scope_id']='0'*64
    elif defect=='false-reclaimed':value['measurement']['physical_reclaim_verified']=True
    elif defect=='free-delta':value['measurement']['free_space_delta_bytes']+=1
    else:(tmp_path/'parent-one/scratch/recreated').mkdir()
    fresh=records.write_record(path,value,replace=True)
    with pytest.raises((RecipeError,ValueError)):
        m.settle_parent(tmp_path,budget_id=options['budget_id'],reservation_id=info['reservation_id'],closure_id=fresh['record_sha256'])
    assert budget(options)['held_count']==1


@pytest.mark.parametrize('stage',['closure-published','settlement-published'])
def test_durable_publication_acknowledgement_gap_can_reopen(tmp_path,monkeypatch,stage):
    values,options=configured(tmp_path);write=records.write_record
    def interrupted(path,value,**kwargs):
        result=write(path,value,**kwargs)
        closing=(path.name=='closure.json' if stage=='closure-published' else
                 path.name=='ledger.json' and any(v['settlement'] is not None for v in value['reservations'].values()))
        if closing:raise OSError('publication acknowledgement lost')
        return result
    with monkeypatch.context() as scoped:
        scoped.setattr(records,'write_record',interrupted)
        with pytest.raises(OSError,match='acknowledgement'):
            with retain(values,options) as retained:info=retained.storage_budget
    assert info['state']=='CLOSED_HELD' and not retained.root.exists()
    assert inspect(options,info)['settled'] is (stage=='settlement-published')
    before=inventory(tmp_path/'parent-one')
    with patch.object(p,'materialized_parent_inputs',side_effect=AssertionError('No expansion')):
        owner().settle_parent(tmp_path,budget_id=options['budget_id'],reservation_id=info['reservation_id'],closure_id=info['closure_id'])
    assert budget(options)['outstanding_bytes']==0 and inventory(tmp_path/'parent-one')==before


@pytest.mark.parametrize('defect',['wrong-pin','too-small','scratch-override','wrong-device','no-capacity'])
def test_parent_admission_denial_precedes_expansion(tmp_path,monkeypatch,defect):
    values,options=configured(tmp_path);original=dict(options);kwargs={}
    if defect=='wrong-pin':options['budget_id']='0'*64
    elif defect=='too-small':options['allowance_bytes']=p.DEFAULT_DISK_BYTES
    elif defect=='scratch-override':kwargs['scratch_directory']=tmp_path
    elif defect=='wrong-device':
        if Path('/dev').stat().st_dev==tmp_path.stat().st_dev:pytest.skip('No separate device')
        monkeypatch.setattr(p,'gettempdir',lambda:'/dev')
    else:options['allowance_bytes']=2*1024**3
    with patch.object(p,'materialized_parent_inputs',side_effect=AssertionError('No expansion')):
        with pytest.raises((ValueError,RecipeError)):
            with p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256'],storage_budget=options,**kwargs):
                pytest.fail('Denied parent opened')
    assert budget(original)['held_count']==0 and not (tmp_path/'parent-one').exists()
