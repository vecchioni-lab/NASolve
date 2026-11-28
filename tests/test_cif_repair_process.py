"""Process evidence is not chemistry qualification or retry authorization."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from nasolve.campaign_records import read_record, write_record


def owner(tmp_path):
    from nasolve.cif_repair_process import PreparedRepairProcesses
    (tmp_path/'bundle').mkdir()
    (tmp_path/'bundle/source.cif').write_text('synthetic source')
    return PreparedRepairProcesses(tmp_path)


def inventory(root):
    return {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def run(o, script='print("evidence")', timeout=5):
    work=o.root/'original-gradient/job';work.mkdir(parents=True,exist_ok=True)
    return o.runner('original-gradient')([sys.executable,'-c',script], cwd=work,
        log_path=work/'gradient.log',environment=dict(os.environ),timeout_seconds=timeout)


@pytest.mark.parametrize('code',[0,7])
def test_owned_exit_and_read_only_completion(tmp_path,code):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    o=owner(tmp_path);assert run(o,f'raise SystemExit({code})')==code
    state=inspect_prepared_repair_processes(tmp_path)
    assert state['state']=='LIVE'  # caller still owns the unsealed execution
    assert o.finish('RETURNED') is True
    before=inventory(tmp_path);state=inspect_prepared_repair_processes(tmp_path)
    assert state['state']=='STOPPED' and state['activity'] is False
    assert state['phases']['original-gradient']['finished']['returncode']==code
    assert not state['retry_authorized'] and inventory(tmp_path)==before
    with pytest.raises((ValueError,RuntimeError,FileExistsError)):run(o)
    assert inventory(tmp_path)==before


def test_timeout_preserves_partial_and_proves_descendants_stopped(tmp_path):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    o=owner(tmp_path)
    script="import subprocess,sys,time;from pathlib import Path;subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path('partial').write_text('keep');time.sleep(30)"
    with pytest.raises(subprocess.TimeoutExpired) as caught:run(o,script,.5)
    assert caught.value.stopped_verified is True and o.finish('RAISED') is True
    s=inspect_prepared_repair_processes(tmp_path)
    assert s['state']=='STOPPED' and s['phases']['original-gradient']['finished']['status']=='TIMED_OUT'
    assert (tmp_path/'original-gradient/job/partial').read_text()=='keep'


def test_missing_is_unknown_and_non_mutating(tmp_path):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    before=inventory(tmp_path);s=inspect_prepared_repair_processes(tmp_path)
    assert s['state']=='NOT_RECORDED' and s['activity'] is None and not s['retry_authorized']
    assert inventory(tmp_path)==before


@pytest.mark.parametrize('failure',['sigterm','record-error','spawn-interrupt'])
def test_interruption_and_identity_publication_failure_cleanup(tmp_path,monkeypatch,failure):
    import signal
    import nasolve.cif_repair_process as m
    import nasolve.campaign_process as process
    o=owner(tmp_path);write=m.write_record;spawn=process.subprocess.Popen
    previous=signal.getsignal(signal.SIGTERM)
    def record(path,value,**kwargs):
        if path.name=='process.json' and failure=='record-error':raise OSError('publication failed')
        result=write(path,value,**kwargs)
        if path.name=='process.json' and failure=='sigterm':os.kill(os.getpid(),signal.SIGTERM)
        return result
    def popen(*a,**kw):
        child=spawn(*a,**kw)
        if kw.get('start_new_session') and failure=='spawn-interrupt':os.kill(os.getpid(),signal.SIGINT)
        return child
    monkeypatch.setattr(m,'write_record',record);monkeypatch.setattr(process.subprocess,'Popen',popen)
    with pytest.raises(process.CampaignProcessError if failure=='record-error' else KeyboardInterrupt):
        run(o,'import time;time.sleep(30)')
    assert signal.getsignal(signal.SIGTERM)==previous and o.finish('RAISED')
    assert m.inspect_prepared_repair_processes(tmp_path)['state']=='STOPPED'


def test_unknown_cleanup_does_not_seal_parent(tmp_path,monkeypatch):
    from nasolve import cif_repair_process as m
    from nasolve.campaign_process import CampaignProcessError
    o=owner(tmp_path)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    with pytest.raises(CampaignProcessError):run(o)
    assert not o.finish('RAISED')
    assert not (tmp_path/'ownership/finished.json').exists()
    assert m.inspect_prepared_repair_processes(tmp_path)['phases']['original-gradient']['state']=='UNKNOWN'


@pytest.mark.parametrize('target',['job.json','finished.json'])
def test_publication_gap_remains_unsealed(tmp_path,monkeypatch,target):
    from nasolve import cif_repair_process as m
    o=owner(tmp_path);write=m.write_record
    def record(path,value,**kwargs):
        if path.name==target:raise OSError('disk error')
        return write(path,value,**kwargs)
    monkeypatch.setattr(m,'write_record',record)
    with pytest.raises(OSError):run(o)
    assert not o.finish('RAISED')
    monkeypatch.setattr(m,'coordinator_alive',lambda identity:False)
    state=m.inspect_prepared_repair_processes(tmp_path)
    assert state['state']==('UNKNOWN' if target=='job.json' else 'STOPPED_UNFINISHED')
    assert not state['retry_authorized']


@pytest.mark.parametrize('target',['job','process','phase-finish','parent-finish','cwd','bundle','symlink'])
def test_corruption_and_rehashed_wrong_bindings_refuse(tmp_path,target):
    from nasolve import cif_repair_process as m
    o=owner(tmp_path);run(o);o.finish('RETURNED')
    phase=tmp_path/'ownership/phases/original-gradient'
    path={'job':phase/'job.json','process':phase/'process.json','phase-finish':phase/'finished.json',
          'parent-finish':tmp_path/'ownership/finished.json','cwd':phase/'job.json'}.get(target)
    if target=='bundle':(tmp_path/'bundle/source.cif').write_text('changed')
    elif target=='symlink':
        path=phase/'process.json';saved=tmp_path/'saved.json';path.rename(saved);path.symlink_to(saved)
    else:
        r=read_record(path)
        if target=='job':r['repair_sha256']='b'*64
        elif target in {'process','phase-finish'}:r['job_sha256']='b'*64
        elif target=='parent-finish':r['phases']={}
        else:r['cwd']['path']='../escaped'
        write_record(path,r,replace=True)
    before=inventory(tmp_path)
    with pytest.raises((ValueError,RuntimeError)):m.inspect_prepared_repair_processes(tmp_path)
    assert inventory(tmp_path)==before


@pytest.mark.parametrize('caller,worker,expected',[(True,False,'LIVE'),(False,True,'LIVE'),(False,False,'STOPPED_UNFINISHED'),(False,None,'UNKNOWN'),(None,False,'UNKNOWN')])
def test_unsealed_requires_both_coordinator_and_children_dead(tmp_path,monkeypatch,caller,worker,expected):
    from nasolve import cif_repair_process as m
    o=owner(tmp_path);run(o)
    (tmp_path/'ownership/phases/original-gradient/finished.json').unlink()
    monkeypatch.setattr(m,'coordinator_alive',lambda identity:caller)
    monkeypatch.setattr(m,'process_alive',lambda identity:worker)
    before=inventory(tmp_path);s=m.inspect_prepared_repair_processes(tmp_path)
    assert s['state']==expected and not s['retry_authorized'] and inventory(tmp_path)==before


def test_missing_or_foreign_child_identity_never_proves_dead(tmp_path,monkeypatch):
    from nasolve import cif_repair_process as m
    o=owner(tmp_path);run(o);folder=tmp_path/'ownership/phases/original-gradient'
    (folder/'finished.json').unlink();path=folder/'process.json';record=read_record(path)
    record['identity']['host']='foreign-host';write_record(path,record,replace=True)
    monkeypatch.setattr(m,'coordinator_alive',lambda identity:False)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:pytest.fail('Foreign group probed'))
    assert m.inspect_prepared_repair_processes(tmp_path)['state']=='UNKNOWN'
    path.unlink();assert m.inspect_prepared_repair_processes(tmp_path)['state']=='UNKNOWN'


def test_sealed_readback_after_relocation_never_executes(tmp_path,monkeypatch):
    from nasolve import cif_repair_process as m
    original=tmp_path/'original';original.mkdir();o=owner(original);run(o);o.finish('RETURNED')
    moved=original.rename(tmp_path/'moved');assert not original.exists()
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Readback executed a command'))
    before=inventory(moved);assert m.inspect_prepared_repair_processes(moved)['state']=='STOPPED'
    assert inventory(moved)==before


@pytest.mark.parametrize('exc',[ValueError('bad record'),OSError('disk'),subprocess.TimeoutExpired(['worker'],1)])
def test_ownership_error_cannot_be_hidden_as_scientific_review(tmp_path,exc):
    from nasolve.cif_native_validation import _run_native_command
    from nasolve.campaign_process import CampaignProcessError
    def runner(*a,**k):raise exc
    with pytest.raises(CampaignProcessError):
        _run_native_command(['worker'],cwd=tmp_path,log_path=tmp_path/'log',environment={},timeout_seconds=1,process_runner=runner)


@pytest.mark.parametrize('gap',[False,True])
def test_coordinator_hard_kill_preserves_worker_or_publication_gap(tmp_path,gap):
    import time
    from nasolve import cif_repair_process as m
    controller = """import os,sys,time
from pathlib import Path
import nasolve.cif_repair_process as m
root=Path(sys.argv[1]);(root/'bundle').mkdir();(root/'bundle/source.cif').write_text('synthetic')
o=m.PreparedRepairProcesses(root);original=m.write_record
def write(path,value,**kwargs):
 if sys.argv[2]=='True' and path.name=='process.json':
  (root/'gap').write_text('ready');time.sleep(10)
 return original(path,value,**kwargs)
m.write_record=write
work=root/'original-gradient/job';work.mkdir(parents=True)
o.runner('original-gradient')([sys.executable,'-c',"import time;from pathlib import Path;Path('partial').write_text('keep');time.sleep(2)"],cwd=work,log_path=work/'gradient.log',environment=dict(os.environ),timeout_seconds=5)
"""
    process=subprocess.Popen([sys.executable,'-c',controller,str(tmp_path),str(gap)])
    try:
        ready=tmp_path/('gap' if gap else 'ownership/phases/original-gradient/process.json')
        deadline=time.monotonic()+5
        while not (ready.exists() and (tmp_path/'original-gradient/job/partial').exists()):
            assert process.poll() is None and time.monotonic()<deadline;time.sleep(.01)
        process.kill();process.wait(timeout=3);before=inventory(tmp_path)
        assert m.inspect_prepared_repair_processes(tmp_path)['state']==('UNKNOWN' if gap else 'LIVE')
        time.sleep(2.1)
        assert m.inspect_prepared_repair_processes(tmp_path)['state']==('UNKNOWN' if gap else 'STOPPED_UNFINISHED')
        assert inventory(tmp_path)==before
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)


from tests.test_cif_prepared_repair_execution import case


def test_prepared_noop_seals_without_granting_chemistry_or_retry(case):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    m,b,sdk,out,state,calls,options=case;state['steps']=False
    r=m.execute_prepared_dictionary_repair(b,sdk,out,**options)
    s=inspect_prepared_repair_processes(out)
    assert s['state']=='STOPPED' and s['phases']=={} and not s['retry_authorized']
    assert r['status']=='NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED'


def test_prepared_all_native_adapters_receive_distinct_ownership(case,monkeypatch):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    m,b,sdk,out,state,calls,options=case
    def wrap(name):
        original=getattr(m,name)
        def adapter(*a,**kw):
            runner=kw['_process_runner']
            if name=='inspect_native_bundle':
                result=original(*a,**kw);cwd=Path(result['native_directory']);log=cwd/'native.log'
            else:
                result=original(*a,**kw);cwd=Path(a[-1])/'job';cwd.mkdir()
                log=cwd/('execution.log' if name=='audit_captured_linear_attribution' else 'gradient.log')
            runner([sys.executable,'-c','print("native fixture")'],cwd=cwd,log_path=log,environment=dict(os.environ),timeout_seconds=2)
            return result
        monkeypatch.setattr(m,name,adapter)
    for n in ('inspect_native_bundle','audit_captured_mixed_gradients','audit_captured_linear_attribution'):wrap(n)
    m.execute_prepared_dictionary_repair(b,sdk,out,**options)
    s=inspect_prepared_repair_processes(out)
    assert s['state']=='STOPPED' and set(s['phases'])=={'native-baseline','native-000','native-001','original-gradient','repaired-gradient','attribution'}


def test_dead_coordinator_is_observed_before_enumerating_worker_publications(tmp_path,monkeypatch):
    from nasolve import cif_repair_process as m
    o=owner(tmp_path)
    def coordinator_exits(identity):
        # A worker reservation becomes visible immediately before caller exit.
        (tmp_path/'ownership/phases/original-gradient').mkdir(parents=True,exist_ok=True)
        return False
    monkeypatch.setattr(m,'coordinator_alive',coordinator_exits)
    assert m.inspect_prepared_repair_processes(tmp_path)['state']=='UNKNOWN'


@pytest.mark.parametrize('seconds',[0,-1,True,float('inf'),float('nan'),601])
def test_bad_timeout_refuses_before_phase_reservation(tmp_path,seconds):
    o=owner(tmp_path)
    with pytest.raises(ValueError):run(o,timeout=seconds)
    assert not (tmp_path/'ownership/phases').exists()


def test_elapsed_prelaunch_allowance_is_not_a_native_timeout_receipt(tmp_path,monkeypatch):
    from nasolve import cif_repair_process as m
    from nasolve.cif_native_validation import _run_native_command
    from nasolve.campaign_process import CampaignProcessError
    o=owner(tmp_path);work=tmp_path/'original-gradient/job';work.mkdir(parents=True)
    ticks=iter([0,3,4]);monkeypatch.setattr(m.time,'monotonic',lambda:next(ticks))
    with pytest.raises(CampaignProcessError,match='before process launch'):
        _run_native_command([sys.executable,'-c','print(1)'],cwd=work,log_path=work/'gradient.log',
            environment={},timeout_seconds=2,process_runner=o.runner('original-gradient'))
    assert not (work/'gradient.log').exists()
    assert o.finish('RAISED')


@pytest.mark.parametrize('phase',['plane-attribution-000','plane-attribution-015'])
def test_plane_attribution_uses_the_existing_owned_process_protocol(tmp_path,phase):
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    o=owner(tmp_path);work=tmp_path/phase/'job';work.mkdir(parents=True)
    assert o.runner(phase)([sys.executable,'-c','print("synthetic plane worker")'],cwd=work,
        log_path=work/'execution.log',environment=dict(os.environ),timeout_seconds=3)==0
    assert o.finish('RETURNED')
    state=inspect_prepared_repair_processes(tmp_path)
    assert state['state']=='STOPPED' and state['phases'][phase]['finished']['status']=='COMPLETED'
    before=inventory(tmp_path)
    with pytest.raises(ValueError):o.runner(phase)([sys.executable,'-c','pass'],cwd=work,
        log_path=work/'execution.log',environment=dict(os.environ),timeout_seconds=3)
    assert inventory(tmp_path)==before
