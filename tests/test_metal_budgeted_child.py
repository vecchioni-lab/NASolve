"""Explicit child admission occurs before expansion; ambiguous work stays held."""
from pathlib import Path
from unittest.mock import patch
import pytest
from nasolve import campaign_records as records
from nasolve.metal import storage_budget as b, child_process as c, parent_archive
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_process import setup,invoke,inventory


def configured(tmp_path):
    values=setup(tmp_path)
    config=b.create_budget(tmp_path,quota_bytes=600*1024*1024,free_space_reserve_bytes=0)
    options=dict(directory=tmp_path,budget_id=config['record_sha256'],allowance_bytes=parent_archive.DEFAULT_DISK_BYTES+1024*1024)
    return values,options


def state(options):return b.inspect_budget(options['directory'],budget_id=options['budget_id'])


@pytest.mark.parametrize('mode',['success','fail','timeout'])
def test_budgeted_known_stopped_child_settles_without_removing_files(tmp_path,mode):
    values,options=configured(tmp_path);values[3].environment['SIM_MODE']=mode
    result=invoke(tmp_path,values,storage_budget=options,timeout_seconds=.5 if mode=='timeout' else 5)
    assert result['stopped_verified'] and result['storage_budget']['state']=='SETTLED'
    assert state(options)['outstanding_bytes']==0 and state(options)['settled_count']==1
    admission=records.read_record(tmp_path/'attempt/storage-admission.json')
    assert admission['kind']=='metal-fdp-child-storage-admission'
    assert admission['grant']['request_id']==values[2]['request_id']
    assert admission['grant']['child']=='attempt'
    assert admission['reservation_id']==result['storage_budget']['reservation_id']
    assert admission['max_parent_disk_bytes']==parent_archive.DEFAULT_DISK_BYTES
    assert not admission['retirement_authorized']
    assert (tmp_path/'attempt/native/fdp/job/input.pdb').is_file()
    assert (tmp_path/'attempt/outcome.json').is_file()
    before=inventory(tmp_path/'attempt');moved=tmp_path.with_name(tmp_path.name+'-'+admission['reservation_id'][:12]+'-moved');tmp_path.rename(moved)
    assert not tmp_path.exists()
    assert b.inspect_budget(moved,budget_id=options['budget_id'])['settled_count']==1
    assert c.inspect_child(moved/'attempt',request_id=values[2]['request_id'])['stopped_verified']
    assert inventory(moved/'attempt')==before


def test_denied_budget_never_expands_parent_or_launches(tmp_path):
    values=setup(tmp_path);config=b.create_budget(tmp_path,quota_bytes=100_000,free_space_reserve_bytes=0)
    options=dict(directory=tmp_path,budget_id=config['record_sha256'],allowance_bytes=parent_archive.DEFAULT_DISK_BYTES+1_000_000)
    with patch.object(parent_archive,'read_parent_inputs',side_effect=AssertionError('No expansion')),patch('subprocess.Popen',side_effect=AssertionError('No native launch')):
        with pytest.raises(RecipeError,match='budget'):invoke(tmp_path,values,storage_budget=options)
    assert not (tmp_path/'attempt').exists() and state(options)['held_count']==0


@pytest.mark.parametrize('defect',['empty','extra','missing','small','wrong-pin','outside','other-device'])
def test_explicit_budget_validation_precedes_reservation(tmp_path,monkeypatch,defect):
    values,options=configured(tmp_path);original=dict(options)
    if defect=='empty':options={}
    elif defect=='extra':options['guess']=True
    elif defect=='missing':options.pop('budget_id')
    elif defect=='small':options['allowance_bytes']=parent_archive.DEFAULT_DISK_BYTES
    elif defect=='wrong-pin':options['budget_id']='0'*64
    elif defect=='outside':
        elsewhere=tmp_path/'other';elsewhere.mkdir()
        cfg=b.create_budget(elsewhere,quota_bytes=600*1024*1024,free_space_reserve_bytes=0)
        options.update(directory=elsewhere,budget_id=cfg['record_sha256'])
    else:
        if Path('/dev').stat().st_dev==tmp_path.stat().st_dev:pytest.skip('No separate /dev device')
        monkeypatch.setattr(parent_archive,'gettempdir',lambda:'/dev')
    with patch.object(parent_archive,'read_parent_inputs',side_effect=AssertionError('No expansion')):
        with pytest.raises((RecipeError,ValueError)):invoke(tmp_path,values,storage_budget=options)
    assert not (tmp_path/'attempt').exists() and state(original)['held_count']==0


def test_uncertain_stop_keeps_full_reservation(tmp_path,monkeypatch):
    values,options=configured(tmp_path)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    result=invoke(tmp_path,values,storage_budget=options,timeout_seconds=5)
    assert result['status']=='STOP_UNCERTAIN' and result['storage_budget']['state']=='HELD'
    assert state(options)['outstanding_bytes']==options['allowance_bytes']
    assert (tmp_path/'attempt/outcome.json').is_file()


def test_changed_frozen_input_stays_held_even_when_stopped(tmp_path):
    values,options=configured(tmp_path);values[3].environment['SIM_MODE']='mutate'
    result=invoke(tmp_path,values,storage_budget=options)
    assert result['status']=='REVIEW_REQUIRED' and result['storage_budget']['state']=='HELD'
    assert state(options)['held_count']==1


def test_outcome_publication_gap_keeps_reservation(tmp_path,monkeypatch):
    values,options=configured(tmp_path);write=records.write_record
    def interrupted(path,value,**kwargs):
        if path.name=='outcome.json':raise OSError('Interrupted outcome')
        return write(path,value,**kwargs)
    monkeypatch.setattr(records,'write_record',interrupted)
    with pytest.raises(OSError,match='Interrupted'):invoke(tmp_path,values,storage_budget=options)
    assert state(options)['held_count']==1
    assert (tmp_path/'attempt/storage-admission.json').is_file()


def test_prelaunch_parent_failure_keeps_admission(tmp_path):
    values,options=configured(tmp_path)
    with patch.object(parent_archive,'read_parent_inputs',side_effect=RecipeError('Parent unavailable')):
        with pytest.raises(RecipeError,match='Parent unavailable'):invoke(tmp_path,values,storage_budget=options)
    assert state(options)['held_count']==1 and not (tmp_path/'attempt').exists()


def test_budgeted_retained_lifetime_refuses_before_claim(tmp_path):
    values,options=configured(tmp_path)
    with parent_archive.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) as retained:
        with pytest.raises(RecipeError,match='retained'):
            invoke(tmp_path,values,storage_budget=options,retained_parent=retained)
        assert state(options)['held_count']==0
        # Existing nonbudgeted retained route remains available.
        result=invoke(tmp_path,values,retained_parent=retained)
        assert result['status']=='COMPLETED' and 'storage_budget' not in result


def test_no_budget_preserves_default_and_invalid_native_does_not_claim(tmp_path):
    values,options=configured(tmp_path);values[3].version='unsupported'
    with pytest.raises(RecipeError,match='version'):invoke(tmp_path,values,storage_budget=options)
    assert state(options)['held_count']==0
    values[3].version=c.NATIVE_VERSION
    result=invoke(tmp_path,values)
    assert result['status']=='COMPLETED' and 'storage_budget' not in result
    assert not (tmp_path/'attempt/storage-admission.json').exists()
    assert state(options)['held_count']==0


def test_interrupted_owner_creation_preserves_grant_and_inputs(tmp_path,monkeypatch):
    values,options=configured(tmp_path)
    def interrupted(*args,**kwargs):raise OSError('Interrupted before child ownership')
    monkeypatch.setattr(c,'ChildProcesses',interrupted)
    with pytest.raises(OSError,match='child ownership'):invoke(tmp_path,values,storage_budget=options)
    assert state(options)['outstanding_bytes']==options['allowance_bytes']
    assert (tmp_path/'attempt/storage-admission.json').is_file()
    assert (tmp_path/'attempt/inputs/request.json').is_file()
    assert not (tmp_path/'attempt/outcome.json').exists()


def test_known_input_copies_need_room_beyond_parent_allowance(tmp_path):
    values,options=configured(tmp_path)
    options['allowance_bytes']=parent_archive.DEFAULT_DISK_BYTES+1
    with pytest.raises(RecipeError,match='headroom'):invoke(tmp_path,values,storage_budget=options)
    assert state(options)['held_count']==0 and not (tmp_path/'attempt').exists()


def test_busy_settlement_preserves_completed_result_and_held_allowance(tmp_path):
    from nasolve.campaign_process import CampaignProcessError
    values,options=configured(tmp_path)
    with patch.object(b,'settle_child',side_effect=CampaignProcessError('lock busy')):
        result=invoke(tmp_path,values,storage_budget=options)
    assert result['status']=='COMPLETED' and result['storage_budget']['state']=='HELD'
    assert 'lock busy' in result['storage_budget']['settlement_error']
    assert state(options)['held_count']==1
    before=inventory(tmp_path/'attempt')
    b.settle_child(tmp_path,budget_id=options['budget_id'],reservation_id=result['storage_budget']['reservation_id'])
    assert state(options)['held_count']==0 and inventory(tmp_path/'attempt')==before


def test_second_launcher_refuses_while_first_child_owns_space(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import time
    values=setup(tmp_path);values[3].environment['SIM_MODE']='timeout'
    config=b.create_budget(tmp_path,quota_bytes=300*1024*1024,free_space_reserve_bytes=0)
    options=dict(directory=tmp_path,budget_id=config['record_sha256'],allowance_bytes=parent_archive.DEFAULT_DISK_BYTES+1024*1024)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(invoke,tmp_path,values,storage_budget=options,timeout_seconds=1)
        marker=tmp_path/'attempt/native/fdp/job/child.pid';deadline=time.monotonic()+3
        while not marker.exists() and not task.done() and time.monotonic()<deadline:time.sleep(.01)
        assert marker.exists() and not task.done()
        with pytest.raises(RecipeError,match='budget'):
            invoke(tmp_path,values,'second',storage_budget=options)
        assert not (tmp_path/'second').exists() and state(options)['held_count']==1
        result=task.result(timeout=5)
    assert result['status']=='TIMED_OUT' and result['storage_budget']['state']=='SETTLED'
    assert state(options)['held_count']==0 and state(options)['settled_count']==1
