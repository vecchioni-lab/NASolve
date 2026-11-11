"""Owned continuation: real worker lifecycle, explicitly synthetic native physics."""
from hashlib import sha256
from unittest.mock import patch
import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.test_cif_runtime_readyset import parent_case, inventory


@pytest.fixture
def continuation(tmp_path, monkeypatch, request):
    from nasolve import cif_runtime_continuation as m
    from nasolve import cif_runtime_readyset as adapter
    from nasolve.cif_native_monomers import POLICY_ID
    parent, sdk = parent_case(tmp_path, monkeypatch, single=True, repaired=getattr(request,'param',True))
    consumer = m._selected_consumer(m._parent(parent))
    state = dict(reject_raw=False, fail=None, elapsed=None, calls=[])
    monkeypatch.setattr(m,'verify_current_consumer',lambda *a:True)
    def capture(model,dictionaries,output,executable,**k):
        phase=output.name;work=output/'capture';work.mkdir(parents=True);state['calls'].append(phase)
        rows=[]
        for i,(role,p) in enumerate([('model',model),*[('dictionary',p) for p in dictionaries],*[('phil',p) for p in k['phil_files']]]):
            data=p.read_bytes();name=f'input-{i:03d}';(work/name).write_bytes(data)
            rows.append(dict(role=role,path=name,sha256=sha256(data).hexdigest(),size=len(data)))
        spec=dict(policy_id=m.NATIVE_POLICY_ID,model=rows[0]['path'],
            dictionaries=[r['path'] for r in rows if r['role']=='dictionary'],phil_files=[r['path'] for r in rows if r['role']=='phil'],
            **{key:k[key] for key in ('phil_namespace_policy','inventory_detail','policy_inventory','energy_inventory','nonbonded_inventory','full_monomer_inventory')})
        if k.get('nonbonded_policy') is not None: spec['nonbonded_policy']=k['nonbonded_policy']
        (work/'native_spec.json').write_text(json.dumps(spec))
        (work/'native_worker.py').write_text('import sys\nprint("synthetic native transport")\nsys.exit('+('1' if state['fail']==phase else '0')+')\n')
        command=[str(executable),'native_worker.py','native_spec.json']
        rc=k['_process_runner'](command,cwd=work,log_path=work/'native.log',environment=sdk.environment,timeout_seconds=k['timeout_seconds'])
        execution=dict(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc,timeout_seconds=k['timeout_seconds'])
        record=dict(inputs=rows,execution=execution,command=command,status='REVIEW' if rc==0 else 'FAILED',
            phenix_version=consumer['version'],executable_sha256=consumer['executable_sha256'],
            phase=phase,full_monomer_inventory_policy=POLICY_ID)
        (work/'native_receipt.json').write_text(json.dumps(record))
        if state['elapsed'] is not None:state['elapsed'][0]=100
        return dict(native_directory=str(work),execution=execution)
    def read_capture(path,model):
        data=path.read_bytes();r=json.loads(data)
        assert r['inputs'][0]['sha256']==sha256(model).hexdigest()
        native=dict(phase=r['phase']) if r['execution']['status']=='COMPLETED' else None
        return r,native,{path:data}
    monkeypatch.setattr(m,'inspect_native_bundle',capture)
    monkeypatch.setattr(m,'_capture',read_capture)
    monkeypatch.setattr('nasolve.cif_attachment_native._capture',read_capture)
    monkeypatch.setattr('nasolve.cif_native_monomers.review_full_monomers',lambda *a:None)
    def bind(r,c,model,ds,ps):
        # Only native physics/source fingerprints are synthetic. Keep the real
        # completion and exact ordered-input contract in this wiring fixture.
        if r['execution']['status']!='COMPLETED' or r['execution']['returncode']!=0:
            raise ValueError('Synthetic native worker did not complete')
        return m._bind_capture_inputs(r,model,ds,ps)
    monkeypatch.setattr(adapter,'_bind_capture',bind)
    def compare(a,b,*_):
        accepted=not state['reject_raw'] or b['phase']=='ordered'
        return dict(mechanics_checks_pass=accepted,checks={'synthetic_native_physics':accepted})
    monkeypatch.setattr('nasolve.cif_postmr_cached_model.qualify_cached_model_roundtrip',compare)
    return m,parent,sdk,tmp_path/'continuation',state


def test_owned_readyset_process_scope_preserves_inputs_and_reads_without_execution(tmp_path):
    from nasolve.cif_runtime_continuation_process import RuntimeContinuationProcesses,inspect_runtime_continuation_processes
    (tmp_path/'inputs').mkdir();(tmp_path/'inputs/runtime').write_text('selected input')
    owner=RuntimeContinuationProcesses(tmp_path);work=tmp_path/'readyset/readyset';work.mkdir(parents=True)
    owner.runner('readyset')([sys.executable,'-c','print("observed")'],cwd=work,log_path=work/'observer.log',environment=dict(os.environ),timeout_seconds=3)
    assert owner.finish('RETURNED');before=inventory(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('Reader must not execute')):
        state=inspect_runtime_continuation_processes(tmp_path)
    assert state['state']=='STOPPED' and not state['retry_authorized'] and inventory(tmp_path)==before


@pytest.mark.parametrize('continuation',[False,True],indirect=True)
def test_continuation_joins_real_worker_ownership_and_exact_selected_parent(continuation):
    m,parent,sdk,out,state=continuation;before=inventory(parent)
    r=m.execute_runtime_continuation(parent,sdk,out)
    assert r['selected']=='readyset_checked_model' and r['serialization']=={'status':'NOT_NEEDED'}
    assert r['phases']=={'native-baseline':'COMPLETED','native-endpoint':'COMPLETED','readyset':'COMPLETED'}
    loaded=m.read_runtime_continuation(out)
    assert loaded['report']==r and not r['automatic_adoption'] and not r['retry_authorized']
    assert inventory(parent)==before and state['calls']==['baseline','endpoint']
    frozen=inventory(out)
    with pytest.raises(FileExistsError):m.execute_runtime_continuation(parent,sdk,out)
    assert inventory(out)==frozen


@pytest.mark.parametrize('failure',['baseline','endpoint','readyset','readyset-timeout'])
def test_known_stopped_optional_failure_preserves_complete_repaired_parent(continuation,failure):
    m,parent,sdk,out,state=continuation;options={}
    if failure.startswith('readyset'):
        p=sdk.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
        body="raise ValueError('fake failure')" if failure=='readyset' else 'import time; time.sleep(3)'
        p.write_text(p.read_text().replace("print('No unknown residues')",body))
        if failure=='readyset-timeout':options['readyset_timeout_seconds']=.05
    else:state['fail']=failure
    r=m.execute_runtime_continuation(parent,sdk,out,**options);loaded=m.read_runtime_continuation(out)
    assert r['selected']=='verified_parent_runtime'
    selected=m._parent(parent)
    for name in ('dictionaries','phils'):
        assert [p.read_bytes() for p in loaded['runtime'][name]]==[p.read_bytes() for p in selected[name]]
    assert loaded['runtime']['model'].read_bytes()==selected['model'].read_bytes()
    assert loaded['process_evidence']['state']=='STOPPED'
    if failure=='baseline':assert set(r['phases'])=={'native-baseline'}
    if failure=='readyset-timeout':assert r['phases']['readyset']=='TIMED_OUT'


def padding_change(sdk):
    p=sdk.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    body="lines=Path(args[0]).read_text().splitlines(); lines=[l[:6]+str(int(l[6:11])+100).rjust(5)+l[11:] if l.startswith(('ATOM  ','HETATM')) else l for l in lines]; Path(Path(args[0]).stem+'.updated.pdb').write_text('\\n'.join(lines)+'\\n'); print('No unknown residues')"
    p.write_text(p.read_text().replace("print('No unknown residues')",body))


@pytest.mark.parametrize('restore',[False,True])
def test_lossless_serialization_gets_one_separate_owned_capture(continuation,restore):
    m,parent,sdk,out,state=continuation;padding_change(sdk);state['reject_raw']=True
    r=m.execute_runtime_continuation(parent,sdk,out,restore_serialization=restore)
    assert r['selected']==('readyset_ordered_checked_model' if restore else 'verified_parent_runtime')
    assert r['serialization']['status']==('APPLIED' if restore else 'DISABLED')
    assert state['calls']==(['baseline','endpoint','ordered'] if restore else ['baseline','endpoint'])
    assert m.read_runtime_continuation(out)['report']==r


def test_rejected_raw_comparison_does_not_retry_an_identical_serialization(continuation):
    m,parent,sdk,out,state=continuation;state['reject_raw']=True
    r=m.execute_runtime_continuation(parent,sdk,out)
    assert r['selected']=='verified_parent_runtime' and r['serialization']['status']=='UNCHANGED'
    assert state['calls']==['baseline','endpoint']


@pytest.mark.parametrize('kind',['unknown','interrupt'])
def test_unknown_cleanup_or_interruption_never_becomes_a_published_fallback(continuation,monkeypatch,kind):
    from nasolve import cif_repair_process as shared
    from nasolve.campaign_process import CampaignProcessError
    m,parent,sdk,out,state=continuation
    def broken(*a,**k):
        if kind=='unknown':raise CampaignProcessError('unknown spawn or cleanup')
        error=KeyboardInterrupt();error.stopped_verified=True;raise error
    monkeypatch.setattr(shared,'run_owned_command',broken)
    with pytest.raises((CampaignProcessError,KeyboardInterrupt)):m.execute_runtime_continuation(parent,sdk,out)
    assert not (out/'continuation_execution.json').exists() and not (out/'runtime').exists()
    if kind=='unknown':
        assert m.inspect_runtime_continuation_processes(out)['state']=='LIVE'
        monkeypatch.setattr(shared,'coordinator_alive',lambda identity:False)
    s=m.inspect_runtime_continuation_processes(out)
    assert s['state']==('UNKNOWN' if kind=='unknown' else 'STOPPED')
    if kind=='interrupt':assert s['finished']['outcome']=='RAISED'


def test_shared_allowance_expiry_keeps_completed_phase_and_withholds_result(continuation,monkeypatch):
    m,parent,sdk,out,state=continuation;clock=[0];state['elapsed']=clock
    monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    with pytest.raises(m.RuntimeContinuationBudgetExceeded):m.execute_runtime_continuation(parent,sdk,out,total_timeout_seconds=60)
    assert state['calls']==['baseline'] and not (out/'continuation_execution.json').exists()
    assert m.inspect_runtime_continuation_processes(out)['finished']['outcome']=='RAISED'


@pytest.mark.parametrize('defect',['parent','public-input','public-resource','job-timeout','result-selection','config','missing-seal','missing-phase'])
def test_execution_reader_rejects_changed_ownership_inputs_or_selection(continuation,defect):
    from nasolve.campaign_records import write_record,read_record
    m,parent,sdk,out,state=continuation;m.execute_runtime_continuation(parent,sdk,out)
    if defect=='parent':p=out/'inputs/runtime/model/model.pdb';p.write_bytes(p.read_bytes()+b'CHANGED')
    elif defect=='public-input':p=out/'runtime/evidence/runtime/model/model.pdb';p.write_bytes(p.read_bytes()+b'CHANGED')
    elif defect=='public-resource':p=out/'runtime/model/model.pdb';p.write_bytes(p.read_bytes()+b'CHANGED')
    elif defect=='config':p=out/'inputs/configuration.json';v=json.loads(p.read_bytes());v['restore_serialization']=False;p.write_text(json.dumps(v))
    elif defect=='missing-seal':(out/'ownership/finished.json').unlink()
    elif defect=='missing-phase':shutil.rmtree(out/'ownership/phases/native-endpoint')
    else:
        p=out/('continuation_execution.json' if defect=='result-selection' else 'ownership/phases/readyset/job.json')
        v=read_record(p);v.pop('record_sha256');v['selected' if defect=='result-selection' else 'timeout_seconds']='invented' if defect=='result-selection' else 181
        p.unlink();write_record(p,v)
    before=inventory(out)
    with pytest.raises((ValueError,OSError,KeyError)):m.read_runtime_continuation(out)
    assert inventory(out)==before


@pytest.mark.parametrize('field,value',[('native_timeout_seconds',True),('native_timeout_seconds',0),('readyset_timeout_seconds',181),
    ('readyset_timeout_seconds',float('nan')),('total_timeout_seconds',0),('total_timeout_seconds',3601),('restore_serialization',1)])
def test_invalid_limits_refuse_before_writing(continuation,field,value):
    m,parent,sdk,out,state=continuation
    with pytest.raises(ValueError):m.execute_runtime_continuation(parent,sdk,out,**{field:value})
    assert not out.exists() and not state['calls']


@pytest.mark.parametrize('where',['parent-child','parent-dot-segments','sdk','existing'])
def test_fresh_execution_cannot_overlap_or_repair_old_evidence(continuation,where):
    m,parent,sdk,out,state=continuation
    if where=='parent-child':out=parent/'new-execution'
    elif where=='parent-dot-segments':out=parent.parent/'sibling/../parent/new-execution'
    elif where=='sdk':out=sdk.root/'execution'
    else:out.mkdir();(out/'keep').write_text('untouched')
    before=inventory(parent.parent)
    with pytest.raises((ValueError,FileExistsError)):m.execute_runtime_continuation(parent,sdk,out)
    assert inventory(parent.parent)==before and not state['calls']


def test_owned_continuation_replays_after_parent_and_sdk_are_gone(continuation):
    m,parent,sdk,out,state=continuation;r=m.execute_runtime_continuation(parent,sdk,out)
    moved=out.rename(out.with_name('relocated'));shutil.rmtree(parent);shutil.rmtree(sdk.root)
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay must not execute')):
        result=m.read_runtime_continuation(moved)
    assert result['report']==r and inventory(moved)==before


@pytest.mark.parametrize('kind',['unknown-timeout','not-launched'])
def test_owned_readyset_runner_never_hides_uncertain_or_prelaunch_timeout(continuation,monkeypatch,kind):
    from nasolve import cif_repair_process as shared
    from nasolve.campaign_process import CampaignProcessError
    m,parent,sdk,out,state=continuation;original=shared.run_owned_command
    def run(command,**kwargs):
        if kwargs['log_path'].name!='observer.log':return original(command,**kwargs)
        error=subprocess.TimeoutExpired(command,kwargs['timeout_seconds'])
        if kind=='not-launched':error.stopped_verified=True;error.native_not_launched=True
        raise error
    monkeypatch.setattr(shared,'run_owned_command',run)
    with pytest.raises(CampaignProcessError):m.execute_runtime_continuation(parent,sdk,out)
    assert state['calls']==['baseline'] and not (out/'continuation_execution.json').exists()
    assert not (out/'runtime').exists()
    if kind=='not-launched':assert m.inspect_runtime_continuation_processes(out)['finished']['outcome']=='RAISED'
    else:
        monkeypatch.setattr(shared,'coordinator_alive',lambda identity:False)
        assert m.inspect_runtime_continuation_processes(out)['state']=='UNKNOWN'


@pytest.mark.parametrize('defect',['phase','work','log','second-call'])
def test_readyset_owned_paths_and_phase_identity_cannot_drift(tmp_path,defect):
    from nasolve.cif_runtime_continuation_process import RuntimeContinuationProcesses
    (tmp_path/'inputs').mkdir();(tmp_path/'inputs/source').write_text('source')
    owner=RuntimeContinuationProcesses(tmp_path);work=tmp_path/'readyset/readyset';work.mkdir(parents=True)
    log=work/'observer.log';phase='readyset'
    if defect=='phase':phase='native-000'
    elif defect=='work':work=tmp_path/'elsewhere';work.mkdir()
    elif defect=='log':log=work/'different.log'
    else:owner.runner(phase)([sys.executable,'-c','pass'],cwd=work,log_path=log,environment=dict(os.environ),timeout_seconds=3)
    before=inventory(tmp_path)
    with pytest.raises(ValueError):owner.runner(phase)([sys.executable,'-c','pass'],cwd=work,log_path=log,environment=dict(os.environ),timeout_seconds=3)
    assert inventory(tmp_path)==before


@pytest.mark.parametrize('boundary',['inventory','result-write'])
def test_expiry_during_finalization_never_seals_success(continuation,monkeypatch,boundary):
    m,parent,sdk,out,state=continuation;clock=[0]
    monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    if boundary=='inventory':
        original=m._report
        def report(*a,**k):
            result=original(*a,**k);clock[0]=100;return result
        monkeypatch.setattr(m,'_report',report)
    else:
        original=m.write_record
        def write(path,*a,**k):
            result=original(path,*a,**k)
            if path.name=='continuation_execution.json':clock[0]=100
            return result
        monkeypatch.setattr(m,'write_record',write)
    with pytest.raises(m.RuntimeContinuationBudgetExceeded):m.execute_runtime_continuation(parent,sdk,out,total_timeout_seconds=60)
    assert m.inspect_runtime_continuation_processes(out)['finished']['outcome']=='RAISED'
    with pytest.raises((ValueError,OSError)):m.read_runtime_continuation(out)


def test_separate_bounded_continuation_working_and_published_evidence(tmp_path, monkeypatch):
    from nasolve import cif_runtime_continuation as m
    from nasolve import cif_component_runtime as frozen
    for label in ['inputs', 'runtime']:
        folder = tmp_path / label; folder.mkdir()
        for i in range(6): (folder / str(i)).write_bytes(b'x' * 10)
    monkeypatch.setattr(frozen, 'MAX_FILES', 10); monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    config = dict(artifact_policy='cif-continuation-partitioned-artifacts-v1')
    reader = getattr(m, '_continuation_files', lambda root, config: m._tree(root))
    assert len(reader(tmp_path, config)) == 12
    with pytest.raises(ValueError): reader(tmp_path, {})


@pytest.mark.parametrize('partition', ['inputs', 'runtime'])
@pytest.mark.parametrize('excess', ['files', 'bytes', 'member'])
def test_continuation_partition_keeps_original_bounds(tmp_path, monkeypatch, partition, excess):
    from nasolve import cif_runtime_continuation as m
    from nasolve import cif_component_runtime as frozen
    monkeypatch.setattr(frozen, 'MAX_FILES', 10); monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    monkeypatch.setattr(frozen, 'MAX_FILE_BYTES', 30)
    folder = tmp_path / partition; folder.mkdir()
    for i in range(11 if excess == 'files' else 6 if excess == 'bytes' else 1):
        (folder / str(i)).write_bytes(b'x' * (20 if excess == 'bytes' else 31 if excess == 'member' else 1))
    with pytest.raises(ValueError, match='bounds'):
        m._continuation_files(tmp_path, dict(artifact_policy=m.ARTIFACT_POLICY))


@pytest.mark.parametrize('policy', ['unknown', True, '', {}, []])
def test_unknown_continuation_artifact_policy_refuses_before_execution(continuation, policy):
    m, parent, sdk, out, state = continuation
    with pytest.raises(ValueError, match='artifact policy'):
        m.execute_runtime_continuation(parent, sdk, out, artifact_policy=policy)
    assert not out.exists() and not state['calls']


def test_legacy_continuation_artifact_policy_is_not_upgraded(continuation):
    m, parent, sdk, out, state = continuation
    result = m.execute_runtime_continuation(parent, sdk, out, artifact_policy=None)
    assert 'artifact_policy' not in result['configuration']
    assert m.read_runtime_continuation(out)['report'] == result


@pytest.mark.parametrize('bound', ['files', 'bytes'])
def test_continuation_reserves_process_seal_before_reporting_success(continuation, monkeypatch, bound):
    from nasolve import cif_component_runtime as frozen
    m, parent, sdk, out, state = continuation
    original = m.write_record
    def write(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == 'continuation_execution.json':
            rows = m._continuation_files(out, result['configuration'])
            working = {n: data for n, data in rows.items() if not n.startswith('runtime/')}
            if bound == 'files': monkeypatch.setattr(frozen, 'MAX_FILES', len(working))
            else: monkeypatch.setattr(frozen, 'MAX_BYTES', sum(map(len, working.values())))
        return result
    monkeypatch.setattr(m, 'write_record', write)
    with pytest.raises(ValueError): m.execute_runtime_continuation(parent, sdk, out)
    assert m.inspect_runtime_continuation_processes(out)['finished']['outcome'] == 'RAISED'
    with pytest.raises(ValueError): m.read_runtime_continuation(out)


def test_owned_completion_reservation_can_prevent_atomic_success(tmp_path):
    from nasolve.cif_runtime_continuation_process import RuntimeContinuationProcesses
    (tmp_path / 'inputs').mkdir(); (tmp_path / 'inputs/source').write_text('frozen')
    owner = RuntimeContinuationProcesses(tmp_path)
    before = inventory(tmp_path); seen = []
    def reserve(record):
        seen.append(record)
        raise ValueError('No publication headroom')
    with pytest.raises(ValueError, match='headroom'): owner.finish('RETURNED', before_publish=reserve)
    assert len(seen) == 1 and seen[0]['outcome'] == 'RETURNED' and inventory(tmp_path) == before
    assert owner.finish('RAISED')


@pytest.mark.parametrize('value', [{}, {'name': 'phosphate λ', 'values': [1, 1.25, True, None]}, {'record_sha256': 'ignored', 'result': 'RETURNED'}])
def test_completion_size_matches_atomic_record_bytes(tmp_path, value):
    from nasolve.campaign_records import serialized_record_size, write_record
    path = tmp_path / 'record.json'
    expected = serialized_record_size(value)
    write_record(path, value)
    assert expected == len(path.read_bytes())


def test_fresh_continuation_freezes_asu_policy_for_every_native_phase(continuation):
    m,parent,sdk,out,state=continuation;padding_change(sdk);state['reject_raw']=True
    result=m.execute_runtime_continuation(parent,sdk,out)
    assert result['configuration']['nonbonded_policy']=='cif-native-nonbonded-asu-attribution-v1'
    assert state['calls']==['baseline','endpoint','ordered']
    for phase in state['calls']:
        spec=json.loads((out/'native'/phase/'capture/native_spec.json').read_bytes())
        assert spec['nonbonded_policy']==result['configuration']['nonbonded_policy']
    assert m.read_runtime_continuation(out)['report']==result


def test_explicit_legacy_native_mode_is_not_upgraded(continuation):
    m,parent,sdk,out,state=continuation
    result=m.execute_runtime_continuation(parent,sdk,out,nonbonded_policy=None)
    assert 'nonbonded_policy' not in result['configuration']
    for phase in state['calls']:
        assert 'nonbonded_policy' not in json.loads((out/'native'/phase/'capture/native_spec.json').read_bytes())
    assert m.read_runtime_continuation(out)['report']==result


@pytest.mark.parametrize('policy',['unknown',True,{},'',[]])
def test_unknown_continuation_native_policy_refuses_before_output(continuation,policy):
    m,parent,sdk,out,state=continuation
    with pytest.raises(ValueError,match='nonbonded'):
        m.execute_runtime_continuation(parent,sdk,out,nonbonded_policy=policy)
    assert not out.exists() and not state['calls']


def test_native_phase_cannot_downgrade_the_frozen_asu_mode(continuation):
    m,parent,sdk,out,state=continuation
    m.execute_runtime_continuation(parent,sdk,out)
    spec=out/'native/baseline/capture/native_spec.json';value=json.loads(spec.read_bytes());value.pop('nonbonded_policy');spec.write_text(json.dumps(value))
    phases=m.inspect_runtime_continuation_processes(out)['phases'];selected=m._parent(out/'inputs/runtime')
    with pytest.raises(ValueError,match='maintained context'):
        m._native(out,phases['native-baseline'],selected,m._selected_consumer(selected),nonbonded_policy=m.NATIVE_NONBONDED_POLICY)
