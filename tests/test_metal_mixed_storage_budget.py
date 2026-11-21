"""Opt-in mixed grants share one budget; parent release is deliberately absent."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
import shutil
import time
import pytest
from nasolve import campaign_records as records
from nasolve.campaign_process import CampaignProcessError
from nasolve.metal import storage_budget as m
from nasolve.metal.recipe import RecipeError,digest
from tests.test_metal_child_process import setup,invoke,inventory


def mixed(tmp_path,limit=3_000_000):
    root=tmp_path/'store';root.mkdir()
    config=m.create_budget(root,quota_bytes=limit,free_space_reserve_bytes=0,include_retained_parents=True)
    return root,config['record_sha256']


def parent(root,pin,name='snapshot',allowance=1_000_000):
    return m.reserve_retained_parent(root,budget_id=pin,scope=name,parent_manifest_sha256='2'*64,allowance_bytes=allowance)


def child(root,pin,name='attempt',parent_id=None,request='1'*64):
    return m.reserve_child(root,budget_id=pin,child=name,request_id=request,allowance_bytes=1_000_000,parent_reservation_id=parent_id)


def test_parent_and_child_share_charge_without_materializing(tmp_path):
    root,pin=mixed(tmp_path);a=parent(root,pin);b=child(root,pin,parent_id=a['reservation_id'])
    report=m.inspect_budget(root,budget_id=pin)
    assert report['schema_version']==2 and report['outstanding_bytes']==2_000_000
    assert report['outstanding_by_scope']=={'child':1_000_000,'retained_parent':1_000_000}
    assert report['held_by_scope']=={'child':1,'retained_parent':1}
    assert b['parent_reservation_id']==a['reservation_id'] and a['scope_type']=='retained_parent'
    assert not (root/'snapshot').exists() and not (root/'attempt').exists()


def test_mixed_concurrent_grants_cannot_oversubscribe(tmp_path):
    root,pin=mixed(tmp_path,1_500_000);barrier=Barrier(2)
    def reserve(kind):
        barrier.wait()
        for _ in range(100):
            try:return parent(root,pin) if kind=='parent' else child(root,pin)
            except CampaignProcessError as exc:
                assert 'lock busy' in str(exc);time.sleep(.005)
            except RecipeError as exc:
                assert 'budget' in str(exc);return None
        raise AssertionError('Lock stayed busy')
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,['parent','child']))
    assert sum(x is not None for x in results)==1
    report=m.inspect_budget(root,budget_id=pin)
    assert report['outstanding_bytes']==1_000_000 and report['held_count']==1


def test_parent_cannot_be_settled_as_child(tmp_path):
    root,pin=mixed(tmp_path);a=parent(root,pin)
    with patch.object(m,'inspect_child',side_effect=AssertionError('Parent is not a native child')):
        with pytest.raises(RecipeError,match='parent'):m.settle_child(root,budget_id=pin,reservation_id=a['reservation_id'])
    assert m.inspect_budget(root,budget_id=pin)['outstanding_bytes']==1_000_000


def test_stopped_child_settlement_leaves_parent_held(tmp_path):
    root,pin=mixed(tmp_path,5_000_000);values=setup(root);a=parent(root,pin)
    grant=child(root,pin,parent_id=a['reservation_id'],request=values[2]['request_id'])
    result=invoke(root,values);assert result['stopped_verified']
    before=inventory(root/'attempt')
    m.settle_child(root,budget_id=pin,reservation_id=grant['reservation_id'])
    report=m.inspect_budget(root,budget_id=pin)
    assert report['held_by_scope']=={'child':0,'retained_parent':1}
    assert report['outstanding_bytes']==1_000_000 and report['settled_count']==1
    assert inventory(root/'attempt')==before


@pytest.mark.parametrize('reference',['missing','child','foreign'])
def test_invalid_parent_reference_never_grants(tmp_path,reference):
    root,pin=mixed(tmp_path,5_000_000)
    if reference=='missing':ref='0'*64
    elif reference=='child':ref=child(root,pin,'other')['reservation_id']
    else:
        other=tmp_path/'foreign';other.mkdir();cfg=m.create_budget(other,quota_bytes=5_000_000,free_space_reserve_bytes=0,include_retained_parents=True)
        ref=parent(other,cfg['record_sha256'])['reservation_id']
    before=m.inspect_budget(root,budget_id=pin)
    with pytest.raises(RecipeError,match='parent'):child(root,pin,parent_id=ref)
    assert m.inspect_budget(root,budget_id=pin)['outstanding_bytes']==before['outstanding_bytes']


def test_grant_namespaces_cannot_overlap(tmp_path):
    root,pin=mixed(tmp_path,5_000_000);parent(root,pin)
    with pytest.raises(RecipeError):child(root,pin,'snapshot')
    (root/'snapshot').mkdir()
    with pytest.raises(RecipeError):child(root,pin,'snapshot/attempt')
    assert m.inspect_budget(root,budget_id=pin)['held_count']==1


def test_relocated_mixed_ledger_preserves_both_holds(tmp_path):
    root,pin=mixed(tmp_path);a=parent(root,pin);child(root,pin,parent_id=a['reservation_id'])
    moved=tmp_path/'relocated';root.rename(moved);assert not root.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('Ledger read cannot execute')):
        report=m.inspect_budget(moved,budget_id=pin)
    assert report['outstanding_bytes']==2_000_000
    assert str(root) not in (moved/'.metal-budget/ledger.json').read_text()


def test_v1_stays_child_only_without_conversion(tmp_path):
    root=tmp_path/'store';root.mkdir();cfg=m.create_budget(root,quota_bytes=3_000_000,free_space_reserve_bytes=0)
    pin=cfg['record_sha256'];assert cfg['schema_version']==1 and 'reservation_types' not in cfg
    child(root,pin)
    before=inventory(root/'.metal-budget')
    with pytest.raises(RecipeError,match='version'):parent(root,pin)
    with pytest.raises(RecipeError,match='version'):child(root,pin,'second',parent_id='0'*64)
    assert inventory(root/'.metal-budget')==before
    report=m.inspect_budget(root,budget_id=pin)
    assert report['schema_version']==1 and 'held_by_scope' not in report


def test_v2_is_not_activated_in_ordinary_launcher(tmp_path):
    root,pin=mixed(tmp_path,600*1024*1024);values=setup(root)
    options=dict(directory=root,budget_id=pin,allowance_bytes=300*1024*1024)
    with patch('nasolve.metal.parent_archive.read_parent_inputs',side_effect=AssertionError('No expansion')):
        with pytest.raises(RecipeError,match='mixed'):invoke(root,values,storage_budget=options)
    assert m.inspect_budget(root,budget_id=pin)['held_count']==0 and not (root/'attempt').exists()


@pytest.mark.parametrize('defect',['version','relabel-v1','parent-settlement','unknown-scope','scope-list','missing-parent','scope-reuse'])
def test_resealed_unsupported_or_inconsistent_ledger_refuses(tmp_path,defect):
    root,pin=mixed(tmp_path,5_000_000);a=parent(root,pin);child(root,pin,parent_id=a['reservation_id'])
    path=root/'.metal-budget/ledger.json';ledger=records.read_record(path)
    if defect=='version':ledger['schema_version']=99
    elif defect=='relabel-v1':ledger['schema_version']=1
    elif defect=='parent-settlement':ledger['reservations'][a['reservation_id']]['settlement']={'status':'CLOSED','snapshot_removed':True}
    elif defect=='missing-parent':del ledger['reservations'][a['reservation_id']]
    else:
        old=a['reservation_id'];entry=ledger['reservations'].pop(old);grant=entry['grant']
        if defect in {'unknown-scope','scope-list'}:grant['scope_type']='guessed' if defect=='unknown-scope' else []
        else:
            ledger['reservations'][old]={'grant':dict(grant),'settlement':None};grant['scope']='second';grant['nonce']='f'*32
        changed=digest(grant);ledger['reservations'][changed]=entry
        for item in ledger['reservations'].values():
            if item['grant'].get('scope_type')=='child':
                child_entry=item;break
        previous=digest(child_entry['grant']);ledger['reservations'].pop(previous)
        child_entry['grant']['parent_reservation_id']=changed
        ledger['reservations'][digest(child_entry['grant'])]=child_entry
    records.write_record(path,ledger,replace=True)
    with pytest.raises(RecipeError):m.inspect_budget(root,budget_id=pin)


def test_interrupted_parent_grant_stays_held_if_published(tmp_path,monkeypatch):
    root,pin=mixed(tmp_path);write=records.write_record
    def interrupted(path,value,**kwargs):
        result=write(path,value,**kwargs)
        if path.name=='ledger.json':raise OSError('Interrupted after grant publication')
        return result
    monkeypatch.setattr(records,'write_record',interrupted)
    with pytest.raises(OSError,match='Interrupted'):parent(root,pin)
    assert m.inspect_budget(root,budget_id=pin)['outstanding_by_scope']=={'child':0,'retained_parent':1_000_000}
