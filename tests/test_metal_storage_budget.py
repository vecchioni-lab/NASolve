"""Cooperative capacity reservations do not retire files or accept science."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
import importlib
import shutil
import time
import pytest
from nasolve.campaign_process import CampaignProcessError
from nasolve.campaigns import CampaignError
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_process import setup, invoke, inventory


def owner():
    return importlib.import_module('nasolve.metal.storage_budget')


def budget(tmp_path, limit=2_000_000):
    m=owner(); root=tmp_path/'store'; root.mkdir()
    config=m.create_budget(root, quota_bytes=limit, free_space_reserve_bytes=0)
    return m,root,config['record_sha256']


def claim(m,root,pin,child='attempt',allowance=1_000_000,request='1'*64):
    return m.reserve_child(root,budget_id=pin,child=child,request_id=request,allowance_bytes=allowance)


def test_two_concurrent_claims_cannot_oversubscribe(tmp_path):
    m,root,pin=budget(tmp_path,1_500_000); start=Barrier(2)
    def attempt(name):
        start.wait()
        for _ in range(100):
            try:return claim(m,root,pin,name)
            except CampaignProcessError as exc:
                assert 'lock busy' in str(exc); time.sleep(.005)
            except RecipeError as exc:
                assert 'budget' in str(exc); return None
        raise AssertionError('lock did not become available')
    with ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(attempt,['one','two']))
    assert sum(v is not None for v in values)==1
    report=m.inspect_budget(root,budget_id=pin)
    assert report['outstanding_bytes']==1_000_000 and report['held_count']==1
    assert not (root/'one').exists() and not (root/'two').exists()
    assert not report['retirement_authorized'] and not report['os_enforced']


def test_partial_and_never_started_children_keep_allowance(tmp_path):
    m,root,pin=budget(tmp_path); grant=claim(m,root,pin)
    with pytest.raises((RecipeError,OSError,ValueError)):
        m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    (root/'attempt').mkdir(); (root/'attempt/partial').write_bytes(b'x'*200)
    with pytest.raises((RecipeError,OSError,ValueError)):
        m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    report=m.inspect_budget(root,budget_id=pin)
    assert report['outstanding_bytes']==1_000_000 and report['held_count']==1
    assert (root/'attempt/partial').read_bytes()==b'x'*200


@pytest.mark.parametrize('mode',['success','fail','timeout'])
def test_known_stopped_child_releases_only_allowance(tmp_path,mode):
    m,root,pin=budget(tmp_path,5_000_000)
    values=setup(root); values[3].environment['SIM_MODE']=mode
    grant=claim(m,root,pin,request=values[2]['request_id'])
    result=invoke(root,values,timeout_seconds=.5 if mode=='timeout' else 5)
    assert result['stopped_verified']
    before=inventory(root/'attempt')
    settlement=m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    assert settlement['outcome_sha256']==result['outcome']['record_sha256']
    report=m.inspect_budget(root,budget_id=pin)
    assert report['outstanding_bytes']==0 and report['settled_count']==1
    assert report['observed_bytes']>=sum(map(len,before.values()))
    assert inventory(root/'attempt')==before
    with pytest.raises(RecipeError):m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])


def test_stopped_without_outcome_does_not_release(tmp_path,monkeypatch):
    m,root,pin=budget(tmp_path,5_000_000); values=setup(root)
    grant=claim(m,root,pin,request=values[2]['request_id'])
    from nasolve.metal import child_process
    write=child_process.records.write_record
    def interrupted(path,value,**options):
        if path.name=='outcome.json':raise OSError('Interrupted outcome')
        return write(path,value,**options)
    monkeypatch.setattr(child_process.records,'write_record',interrupted)
    with pytest.raises(OSError,match='Interrupted'):invoke(root,values)
    monkeypatch.setattr(child_process.records,'write_record',write)
    with pytest.raises(RecipeError,match='stopped outcome'):
        m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    assert m.inspect_budget(root,budget_id=pin)['outstanding_bytes']==1_000_000


@pytest.mark.parametrize('state',['live','uncertain','wrong-request','late-change'])
def test_unverified_stop_never_releases(tmp_path,monkeypatch,state):
    m,root,pin=budget(tmp_path,5_000_000); values=setup(root)
    grant=claim(m,root,pin,request=values[2]['request_id']); invoke(root,values)
    inspect=m.inspect_child; calls=[]
    def changed(*a,**k):
        value=inspect(*a,**k); calls.append(1)
        if state=='wrong-request':value['request_id']='0'*64
        elif state!='late-change' or len(calls)>1:
            value['stopped_verified']=False
            value['status']='STOP_UNCERTAIN' if state=='uncertain' else 'RUNNING'
        return value
    monkeypatch.setattr(m,'inspect_child',changed)
    with pytest.raises(RecipeError):m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    assert m.inspect_budget(root,budget_id=pin)['held_count']==1


@pytest.mark.parametrize('child',['../escape','.metal-budget/child','existing','nested/child'])
def test_invalid_or_existing_child_never_grants(tmp_path,child):
    m,root,pin=budget(tmp_path); (root/'existing').mkdir()
    with pytest.raises((RecipeError,ValueError,CampaignError)):
        claim(m,root,pin,child)
    assert m.inspect_budget(root,budget_id=pin)['held_count']==0


def test_same_child_and_nested_claims_refuse(tmp_path):
    m,root,pin=budget(tmp_path,5_000_000); claim(m,root,pin)
    with pytest.raises(RecipeError):claim(m,root,pin)
    (root/'attempt').mkdir()
    with pytest.raises(RecipeError):claim(m,root,pin,'attempt/nested')


def test_low_disk_and_existing_bytes_are_charged(tmp_path,monkeypatch):
    m,root,pin=budget(tmp_path); (root/'protected').write_bytes(b'x'*1_100_000)
    with pytest.raises(RecipeError,match='budget'):claim(m,root,pin)
    assert m.inspect_budget(root,budget_id=pin)['held_count']==0
    monkeypatch.setattr(m.shutil,'disk_usage',lambda p:SimpleNamespace(free=10))
    with pytest.raises(RecipeError,match='free space'):claim(m,root,pin,allowance=100)
    assert (root/'protected').stat().st_size==1_100_000


@pytest.mark.parametrize('change',['pin','symlink','fifo','ledger','orphan','missing-ledger'])
def test_unsafe_store_or_broken_ledger_refuses(tmp_path,change):
    m,root,pin=budget(tmp_path)
    if change=='pin':pin='0'*64
    elif change=='symlink':(root/'link').symlink_to(tmp_path)
    elif change=='fifo':
        import os
        os.mkfifo(root/'pipe')
    elif change=='ledger':(root/'.metal-budget/ledger.json').write_text('{}')
    elif change=='orphan':(root/'.metal-budget/.record-interrupted').write_text('partial')
    else:(root/'.metal-budget/ledger.json').unlink()
    with pytest.raises((RecipeError,ValueError,CampaignError)):
        claim(m,root,pin)


def test_relocated_ledger_without_old_paths(tmp_path):
    m,root,pin=budget(tmp_path); grant=claim(m,root,pin)
    moved=tmp_path/'moved'; root.rename(moved)
    assert not root.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('Budget read never launches')):
        report=m.inspect_budget(moved,budget_id=pin)
    assert report['outstanding_bytes']==grant['allowance_bytes']
    assert str(root) not in (moved/'.metal-budget/ledger.json').read_text()


def test_allowance_validation_and_budget_are_immutable(tmp_path):
    m,root,pin=budget(tmp_path)
    for invalid in [True,0,-1,1.5]:
        with pytest.raises(RecipeError):claim(m,root,pin,allowance=invalid)
    with pytest.raises(RecipeError):m.create_budget(root,quota_bytes=10,free_space_reserve_bytes=0)
    assert m.inspect_budget(root,budget_id=pin)['held_count']==0


def test_equal_limits_do_not_make_stores_interchangeable(tmp_path):
    m,root,pin=budget(tmp_path)
    other=tmp_path/'other';other.mkdir()
    second=m.create_budget(other,quota_bytes=2_000_000,free_space_reserve_bytes=0)
    assert second['record_sha256']!=pin
    with pytest.raises(RecipeError,match='identity'):claim(m,other,pin)


@pytest.mark.parametrize('point',['before-publish','after-publish'])
def test_interrupted_grant_has_no_partial_release(tmp_path,monkeypatch,point):
    m,root,pin=budget(tmp_path);write=m.records.write_record
    def interrupted(path,value,**options):
        if point=='after-publish':write(path,value,**options)
        raise OSError('Interrupted ledger publication')
    monkeypatch.setattr(m.records,'write_record',interrupted)
    with pytest.raises(OSError,match='Interrupted'):claim(m,root,pin)
    monkeypatch.setattr(m.records,'write_record',write)
    report=m.inspect_budget(root,budget_id=pin)
    assert report['held_count']==(point=='after-publish')
    assert report['outstanding_bytes']==(1_000_000 if point=='after-publish' else 0)


def test_interrupted_settlement_keeps_claim_and_all_payloads(tmp_path,monkeypatch):
    m,root,pin=budget(tmp_path,5_000_000);values=setup(root)
    grant=claim(m,root,pin,request=values[2]['request_id']);invoke(root,values)
    before=inventory(root/'attempt')
    with patch.object(m.records,'write_record',side_effect=OSError('Interrupted ledger publication')):
        with pytest.raises(OSError):m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    assert m.inspect_budget(root,budget_id=pin)['outstanding_bytes']==1_000_000
    assert inventory(root/'attempt')==before


def test_active_overrun_is_reported_without_deleting_or_releasing(tmp_path):
    m,root,pin=budget(tmp_path,1_500_000);grant=claim(m,root,pin)
    (root/'attempt').mkdir();(root/'attempt/large').write_bytes(b'x'*1_000_000)
    report=m.inspect_budget(root,budget_id=pin)
    assert not report['within_declared_budget'] and report['held_count']==1
    with pytest.raises(RecipeError,match='budget'):claim(m,root,pin,'second',allowance=1)
    assert (root/'attempt/large').stat().st_size==1_000_000


def test_declared_entry_and_reservation_bounds(tmp_path,monkeypatch):
    m,root,pin=budget(tmp_path,5_000_000)
    with monkeypatch.context() as scoped:
        scoped.setattr(m,'MAX_ENTRIES',1)
        with pytest.raises(RecipeError,match='entry limit'):claim(m,root,pin)
    with monkeypatch.context() as scoped:
        scoped.setattr(m,'MAX_RESERVATIONS',1)
        claim(m,root,pin)
        with pytest.raises(RecipeError,match='reservation limit'):claim(m,root,pin,'second')
    assert m.inspect_budget(root,budget_id=pin)['held_count']==1


def test_unfinished_budget_directory_publication_is_not_adopted(tmp_path,monkeypatch):
    m=owner();root=tmp_path/'store';root.mkdir();sync=m.records._sync_directory
    def interrupted(directory):
        if directory==root:raise OSError('Interrupted budget directory sync')
        return sync(directory)
    monkeypatch.setattr(m.records,'_sync_directory',interrupted)
    with pytest.raises(OSError,match='directory sync'):
        m.create_budget(root,quota_bytes=2_000_000,free_space_reserve_bytes=0)
    assert (root/'.metal-budget').is_dir() and not (root/'.metal-budget/ledger.json').exists()
    monkeypatch.setattr(m.records,'_sync_directory',sync)
    with pytest.raises(RecipeError,match='incomplete'):
        m.create_budget(root,quota_bytes=2_000_000,free_space_reserve_bytes=0)
