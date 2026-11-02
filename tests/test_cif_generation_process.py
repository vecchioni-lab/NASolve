"""Actual local process groups; synthetic workers do not qualify Phenix chemistry."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from nasolve.campaign_process import CampaignProcessError
from nasolve.campaign_records import read_record, write_record
from nasolve.cif_generation_process import inspect_generation_process, run_generation_command

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Owned native generation requires POSIX')
CONTEXT = {'component': 'Q17', 'source_sha256': 'a' * 64}


def run(work, script, *, timeout=5, phase='candidate'):
    return run_generation_command([sys.executable, '-c', script], work, phase=phase,
                                  environment=dict(os.environ), timeout_seconds=timeout, context=CONTEXT)


def inventory(work):
    return {p.relative_to(work).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in work.rglob('*') if p.is_file()}


@pytest.mark.parametrize('code', [0, 7])
def test_prelaunch_identity_and_complete_exit_evidence(tmp_path, code):
    script = ("import json; from pathlib import Path; "
              "j=json.loads(Path('execution/candidate/job.json').read_text()); "
              "assert j['context']['component']=='Q17'; "
              "print('preserved evidence', flush=True); " + f"raise SystemExit({code})")
    assert run(tmp_path, script) == code
    before = inventory(tmp_path)
    state = inspect_generation_process(tmp_path, 'candidate')
    assert state['state'] == 'STOPPED' and state['activity'] is False
    assert state['finished']['returncode'] == code
    assert state['finished']['status'] == ('COMPLETED' if code == 0 else 'FAILED')
    assert state['job']['context'] == CONTEXT and not state['retry_authorized']
    assert state['identity']['pid'] == state['identity']['pgid']
    assert (tmp_path/'candidate_worker.log').read_text() == 'preserved evidence\n'
    assert inventory(tmp_path) == before
    with pytest.raises(FileExistsError):
        run(tmp_path, "raise SystemExit('MUST NOT RETRY')")
    assert inventory(tmp_path) == before


def test_timeout_preserves_partial_output_and_stops_owned_descendants(tmp_path):
    child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    script = ("import subprocess,sys,time; from pathlib import Path; "
              f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
              "Path('partial.cif').write_text('partial evidence'); time.sleep(30)")
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        run(tmp_path, script, timeout=.35)
    assert caught.value.stopped_verified is True
    state = inspect_generation_process(tmp_path, 'candidate')
    assert state['state'] == 'STOPPED' and state['finished']['status'] == 'TIMED_OUT'
    assert (tmp_path/'partial.cif').read_text() == 'partial evidence'
    from nasolve.campaign_process import process_alive
    assert process_alive(state['identity']) is False


@pytest.mark.parametrize('failure', ['sigterm', 'record-error'])
def test_identity_publication_interruption_cleans_owned_worker(tmp_path, monkeypatch, failure):
    import nasolve.cif_generation_process as module
    original = module.write_record
    previous = signal.getsignal(signal.SIGTERM)
    def publish(path, value, **kwargs):
        if path.name == 'process.json' and failure == 'record-error':
            raise OSError('simulated identity storage failure')
        saved = original(path, value, **kwargs)
        if path.name == 'process.json':
            os.kill(os.getpid(), signal.SIGTERM)
        return saved
    monkeypatch.setattr(module, 'write_record', publish)
    with pytest.raises(KeyboardInterrupt if failure == 'sigterm' else CampaignProcessError):
        run(tmp_path, 'import time; time.sleep(30)')
    assert signal.getsignal(signal.SIGTERM) == previous
    state = inspect_generation_process(tmp_path, 'candidate')
    assert state['state'] == 'STOPPED'
    assert state['finished']['status'] == ('INTERRUPTED' if failure == 'sigterm' else 'ERROR')


def test_spawn_interrupt_before_identity_is_proven_stopped(tmp_path, monkeypatch):
    import nasolve.campaign_process as module
    original = module.subprocess.Popen
    children = []
    def spawn(command, *args, **kwargs):
        child = original(command, *args, **kwargs)
        if kwargs.get('start_new_session'):
            children.append(child)
            os.kill(os.getpid(), signal.SIGINT)
        return child
    monkeypatch.setattr(module.subprocess, 'Popen', spawn)
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, 'import time; time.sleep(30)')
    state = inspect_generation_process(tmp_path, 'candidate')
    assert state['state'] == 'STOPPED' and 'identity' not in state
    assert children[0].returncode is not None


def test_unverifiable_descendants_never_publish_stopped(tmp_path, monkeypatch):
    monkeypatch.setattr('nasolve.campaign_process._group_alive', lambda pgid: None)
    with pytest.raises(CampaignProcessError, match='unidentifiable descendants'):
        run(tmp_path, 'raise SystemExit(0)')
    assert not (tmp_path/'execution/candidate/finished.json').exists()
    assert inspect_generation_process(tmp_path, 'candidate')['state'] == 'UNKNOWN'


def test_launch_failure_has_sealed_no_child_evidence(tmp_path):
    with pytest.raises(CampaignProcessError, match='Cannot launch'):
        run_generation_command(['/definitely/absent/c156-program'], tmp_path, phase='candidate',
                               environment={}, timeout_seconds=2, context=CONTEXT)
    state = inspect_generation_process(tmp_path, 'candidate')
    assert state['state'] == 'STOPPED' and state['finished']['status'] == 'ERROR'
    assert 'identity' not in state


@pytest.mark.parametrize('defect', ['job', 'owner', 'finish', 'code', 'symlink'])
def test_rehashed_inconsistent_or_symlinked_evidence_refuses(tmp_path, defect):
    run(tmp_path, 'raise SystemExit(0)')
    folder = tmp_path/'execution/candidate'
    name = {'job':'job.json','owner':'process.json'}.get(defect, 'finished.json')
    path = folder/name
    if defect == 'symlink':
        target = tmp_path/'preserved.json'; path.rename(target); path.symlink_to(target)
    else:
        record = read_record(path)
        if defect == 'job': record['phase'] = 'capabilities'
        elif defect in {'owner','finish'}: record['job_sha256'] = 'b'*64
        else: record['returncode'] = 7
        write_record(path, record, replace=True)
    before = inventory(tmp_path)
    with pytest.raises(ValueError): inspect_generation_process(tmp_path, 'candidate')
    assert inventory(tmp_path) == before


def test_missing_identity_and_foreign_process_remain_unknown(tmp_path, monkeypatch):
    assert inspect_generation_process(tmp_path, 'candidate')['state'] == 'NOT_RECORDED'
    assert not list(tmp_path.iterdir())
    run(tmp_path, 'raise SystemExit(0)')
    folder = tmp_path/'execution/candidate'; (folder/'finished.json').unlink()
    path=folder/'process.json'; owner=read_record(path)
    owner['identity']['host']='different-host'; write_record(path,owner,replace=True)
    def no_probe(*args): raise AssertionError('Foreign identity must not be probed')
    monkeypatch.setattr('nasolve.campaign_process._group_alive',no_probe)
    assert inspect_generation_process(tmp_path,'candidate')['state']=='UNKNOWN'
    path.unlink()
    before=inventory(tmp_path)
    assert inspect_generation_process(tmp_path,'candidate')['state']=='UNKNOWN'
    assert inventory(tmp_path)==before


def test_completed_evidence_replays_after_original_path_disappears(tmp_path, monkeypatch):
    original=tmp_path/'original';original.mkdir();run(original,'raise SystemExit(0)')
    moved=tmp_path/'relocated';original.rename(moved)
    def no_launch(*args,**kwargs):raise AssertionError('Read-only inspection must not execute a process')
    monkeypatch.setattr(subprocess,'Popen',no_launch)
    before=inventory(moved)
    assert inspect_generation_process(moved,'candidate')['state']=='STOPPED'
    assert inventory(moved)==before and not original.exists()


@pytest.mark.parametrize('gap', [False, True])
def test_hard_kill_preserves_unknown_or_live_and_prevents_same_phase_retry(tmp_path,gap):
    # The bounded child exits on its own. This test never signals a saved PID.
    controller='''import os,sys,time
from pathlib import Path
import nasolve.cif_generation_process as m
work=Path(sys.argv[1]);gap=sys.argv[2]=='True'
original=m.write_record
def write(path,value,**kwargs):
 if gap and path.name=='process.json':
  (work/'publication-gap').write_text('ready')
  time.sleep(10)
 return original(path,value,**kwargs)
m.write_record=write
m.run_generation_command([sys.executable,'-c',"import time; from pathlib import Path; Path('partial.cif').write_text('preserved'); time.sleep(2)"],work,phase='candidate',environment=dict(os.environ),timeout_seconds=5,context={'component':'Q17','source_sha256':'a'*64})
'''
    process=subprocess.Popen([sys.executable,'-c',controller,str(tmp_path),str(gap)])
    try:
        ready=tmp_path/('publication-gap' if gap else 'execution/candidate/process.json')
        deadline=time.monotonic()+5
        while not (ready.exists() and (tmp_path/'partial.cif').exists()):
            assert process.poll() is None and time.monotonic()<deadline
            time.sleep(.01)
        with pytest.raises(FileExistsError):run(tmp_path,'raise SystemExit(0)')
        process.kill();process.wait(timeout=3)
        before=inventory(tmp_path)
        state=inspect_generation_process(tmp_path,'candidate')
        assert state['state']==('UNKNOWN' if gap else 'LIVE')
        assert not state['retry_authorized']
        time.sleep(2.1)
        state=inspect_generation_process(tmp_path,'candidate')
        assert state['state']==('UNKNOWN' if gap else 'STOPPED_UNFINISHED')
        assert inventory(tmp_path)==before
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)


@pytest.mark.parametrize('timeout',[0,-1,float('nan'),float('inf'),601,True])
def test_invalid_deadline_leaves_no_reservation(tmp_path,timeout):
    with pytest.raises(ValueError):run(tmp_path,'raise SystemExit(0)',timeout=timeout)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('record', ['job.json', 'finished.json'])
def test_record_publication_failure_preserves_unknown_without_fabricating_completion(tmp_path,monkeypatch,record):
    import nasolve.cif_generation_process as module
    original=module.write_record
    def write(path,value,**kwargs):
        if path.name==record:raise OSError('simulated durable publication failure')
        return original(path,value,**kwargs)
    monkeypatch.setattr(module,'write_record',write)
    with pytest.raises(OSError):run(tmp_path,'raise SystemExit(0)')
    state=inspect_generation_process(tmp_path,'candidate')
    assert state['state']==('UNKNOWN' if record=='job.json' else 'STOPPED_UNFINISHED')
    assert not state['retry_authorized']
    assert not (tmp_path/'execution/candidate/finished.json').exists()
    if record=='job.json':assert not (tmp_path/'candidate_worker.log').exists()
    with pytest.raises(FileExistsError):run(tmp_path,'raise SystemExit(0)')


@pytest.mark.parametrize('field', ['context', 'argv_provenance', 'coordinator', 'invocation_id'])
def test_incomplete_job_contract_refuses_before_liveness_probe(tmp_path,monkeypatch,field):
    run(tmp_path,'raise SystemExit(0)')
    directory=tmp_path/'execution/candidate'
    (directory/'finished.json').unlink();(directory/'process.json').unlink()
    path=directory/'job.json';record=read_record(path);record.pop(field)
    write_record(path,record,replace=True)
    with pytest.raises(ValueError,match='Invalid generation process job'):
        inspect_generation_process(tmp_path,'candidate')


def test_malformed_execution_ancestor_is_not_legacy_absence(tmp_path):
    (tmp_path/'execution').write_text('unrelated evidence')
    before=inventory(tmp_path)
    with pytest.raises(ValueError,match='not a directory'):
        inspect_generation_process(tmp_path,'candidate')
    with pytest.raises(ValueError,match='not a directory'):
        run(tmp_path,'raise SystemExit(0)')
    assert inventory(tmp_path)==before


@pytest.mark.parametrize('pid',[True,1,'123'])
def test_malformed_owned_identity_cannot_support_a_sealed_completion(tmp_path,pid):
    run(tmp_path,'raise SystemExit(0)')
    folder=tmp_path/'execution/candidate';path=folder/'process.json'
    record=read_record(path);record['identity']['pid']=pid
    owner=write_record(path,record,replace=True)
    path=folder/'finished.json';done=read_record(path);done['process_sha256']=owner['record_sha256']
    write_record(path,done,replace=True)
    with pytest.raises(ValueError,match='identity'):
        inspect_generation_process(tmp_path,'candidate')


def test_deadline_includes_slow_identity_publication_even_if_child_has_exited(tmp_path,monkeypatch):
    import nasolve.cif_generation_process as module
    original=module.write_record
    def publish(path,value,**kwargs):
        saved=original(path,value,**kwargs)
        if path.name=='process.json':time.sleep(.65)
        return saved
    monkeypatch.setattr(module,'write_record',publish)
    with pytest.raises(subprocess.TimeoutExpired):
        run(tmp_path,'raise SystemExit(0)',timeout=.5)
    state=inspect_generation_process(tmp_path,'candidate')
    assert state['state']=='STOPPED' and state['finished']['status']=='TIMED_OUT'


def test_deadline_exhausted_during_prelaunch_publication_never_starts_a_child(tmp_path,monkeypatch):
    import nasolve.cif_generation_process as module
    original=module.current_process_identity
    def slow_identity():
        identity=original();time.sleep(.1);return identity
    def no_launch(*args,**kwargs):raise AssertionError('Expired prelaunch budget must not launch')
    monkeypatch.setattr(module,'current_process_identity',slow_identity)
    monkeypatch.setattr(module,'run_owned_command',no_launch)
    with pytest.raises(subprocess.TimeoutExpired):run(tmp_path,'raise SystemExit(0)',timeout=.05)
    state=inspect_generation_process(tmp_path,'candidate')
    assert state['state']=='STOPPED' and 'identity' not in state
    assert state['finished']['status']=='TIMED_OUT'
    assert not (tmp_path/'candidate_worker.log').exists()
