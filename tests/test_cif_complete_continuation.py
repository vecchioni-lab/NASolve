"""Real outer/child ownership with explicitly synthetic scientific transports.

C183 tests and separate actual Phenix controls qualify the continuation physics.
These tests exercise composition, recovery, frozen intent and shared allowances.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import sys
import uuid

import pytest

from nasolve.campaign_records import read_record, write_record
from nasolve.campaign_process import CampaignProcessError
from tests.test_cif_complete_request import case
from tests.test_cif_postmr_request import entry_case
from tests.test_cif_repair_attempt import inventory

OPTIONS = dict(readyset_timeout_seconds=12.5,restore_serialization=True)


@pytest.fixture
def joined(case,monkeypatch):
    from nasolve import cif_runtime_continuation as continuation
    from nasolve import cif_repair_process as process
    from nasolve.cif_runtime_continuation_process import RuntimeContinuationProcesses,inspect_runtime_continuation_processes
    m,args,root,sdk,store,generations,calls=case
    state=dict(repair_status='QUALIFIED_DIAGNOSTIC_RUNTIME',selected='readyset_checked_model',fault=None,calls=[],reads=0)
    original=m.repair.execute_prepared_dictionary_repair
    def repair(*a,**k):
        result=original(*a,**k);result['status']=state['repair_status']
        if result['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME':
            runtime=a[2]/'runtime';runtime.mkdir()
            (runtime/'runtime_bundle.json').write_text(json.dumps(dict(selected='repaired_prepared_bundle')))
            (runtime/'model.pdb').write_bytes(Path(args['model']).read_bytes())
            (runtime/'dictionary.cif').write_text('synthetic selected numerical dictionary\n')
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    def resolve(path):
        path=Path(path);directory=path.parent if path.is_file() else path
        selected=json.loads((directory/'runtime_bundle.json').read_bytes())['selected']
        return dict(manifest_path=directory/'runtime_bundle.json',model=directory/'model.pdb',
            dictionaries=[directory/'dictionary.cif'],phils=[],manifest=dict(decision=dict(selected=selected)))
    def execute(parent,phenix,out,**k):
        assert 0<k['_remaining_seconds']()<=args['total_timeout_seconds']
        state['calls'].append(dict(output=out,identity=deepcopy(k['_attempt_identity']),settings={n:v for n,v in k.items() if not n.startswith('_')}))
        out.mkdir();shutil.copytree(parent,out/'inputs/runtime')
        config=continuation._configuration(dict(native=k['native_timeout_seconds'],readyset=k['readyset_timeout_seconds'],total=k['total_timeout_seconds']),k['restore_serialization'],artifact_policy=k.get('artifact_policy'),nonbonded_policy=k.get('nonbonded_policy'))
        (out/'inputs/configuration.json').write_text(json.dumps(config))
        if state['fault']=='pre-header':raise KeyboardInterrupt('partial continuation header publication')
        owner=RuntimeContinuationProcesses(out,attempt_identity=k['_attempt_identity'])
        if state['fault']=='after-header':raise KeyboardInterrupt('coordinator disappeared before work')
        if state['fault']=='worker-unknown':
            work=out/'readyset/readyset';work.mkdir(parents=True)
            with patch.object(process,'run_owned_command',side_effect=RuntimeError('unknown worker publication')):
                owner.runner('readyset')([sys.executable,'-c','print("test")'],cwd=work,log_path=work/'observer.log',environment=dict(os.environ),timeout_seconds=1)
        if state['fault']=='interrupted':owner.finish('RAISED');raise KeyboardInterrupt('known stopped continuation')
        shutil.copytree(parent,out/'runtime')
        (out/'runtime/runtime_bundle.json').write_text(json.dumps(dict(selected=state['selected'])))
        report=write_record(out/'continuation_execution.json',dict(synthetic_scientific_transport=True,selected=state['selected']))
        assert owner.finish('RETURNED')
        return report
    def read(out):
        state['reads']+=1;owned=inspect_runtime_continuation_processes(out)
        assert owned['state']=='STOPPED' and owned['finished']['outcome']=='RETURNED'
        return dict(report=read_record(out/'continuation_execution.json'),runtime=resolve(out/'runtime'),process_evidence=owned)
    monkeypatch.setattr(m.repair,'execute_prepared_dictionary_repair',repair)
    monkeypatch.setattr(m,'resolve_runtime_bundle',resolve)
    monkeypatch.setattr(continuation,'execute_runtime_continuation',execute)
    monkeypatch.setattr(continuation,'read_runtime_continuation',read)
    return m,dict(args,continuation_options=deepcopy(OPTIONS)),root,sdk,store,generations,state


def test_freezes_continuation_without_execution_and_preserves_legacy_omission(case):
    m,args,root,sdk,store,generations,calls=case
    with patch('subprocess.Popen',side_effect=AssertionError('Initializer must not run')):
        r=m.initialize_dictionary_request(output=root,**dict(args,continuation_options=OPTIONS))
    c=r['configuration']['continuation']
    assert c['readyset_timeout_seconds']==12.5 and c['restore_serialization'] is True
    assert c['execution_policy']=='cif-selected-runtime-continuation-execution-v1'
    assert c['process_policy']=='cif-runtime-continuation-process-v1'
    before=inventory(root);assert m.inspect_dictionary_request(root)['attempts']==[] and inventory(root)==before
    legacy=m.initialize_dictionary_request(output=root.with_name('legacy'),**args)
    assert 'continuation' not in legacy['configuration'] and not calls


@pytest.mark.parametrize('options',[True,{},dict(OPTIONS,unknown=True),dict(OPTIONS,readyset_timeout_seconds=True),
    dict(OPTIONS,readyset_timeout_seconds=0),dict(OPTIONS,readyset_timeout_seconds=181),
    dict(OPTIONS,readyset_timeout_seconds=float('nan')),dict(OPTIONS,restore_serialization=1),
    dict(OPTIONS,execution_policy='wrong',process_policy='cif-runtime-continuation-process-v1')])
def test_invalid_continuation_settings_never_publish_request(case,options):
    m,args,root,sdk,store,generations,calls=case
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**dict(args,continuation_options=options))
    assert not (root/'request.json').exists() and not (root/'attempts').exists() and not calls


@pytest.mark.parametrize('selected',['readyset_checked_model','verified_parent_runtime'])
def test_final_selection_is_owned_by_same_request_and_cold_reader(joined,selected):
    m,args,root,sdk,store,generations,state=joined;state['selected']=selected
    request=m.initialize_dictionary_request(output=root,**args)
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    exact=m.read_dictionary_request_result(root,1);owner=m.inspect_dictionary_request(root)['attempts'][0]
    assert owner['children']['continuation']['state']=='STOPPED'
    assert exact['runtime']['manifest']['decision']['selected']==selected and exact['continuation']['report']['selected']==selected
    assert result['result']['continuation']==dict(anchor='attempt_directory',path='continuation')
    assert not result['result']['automatic_adoption'] and state['reads']>0
    assert state['calls'][0]['identity']==m._attempt_identity(owner['intent'])
    assert state['calls'][0]['settings']==dict(native_timeout_seconds=90,readyset_timeout_seconds=12.5,total_timeout_seconds=60,restore_serialization=True,artifact_policy=m.continuation.ARTIFACT_POLICY,nonbonded_policy=m.continuation.NATIVE_NONBONDED_POLICY)
    before=inventory(root);moved=root.rename(root.with_name('relocated'))
    shutil.rmtree(store);shutil.rmtree(sdk.root);shutil.rmtree(args['source_selection']);Path(args['model']).unlink()
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    with patch('subprocess.Popen',side_effect=AssertionError('Replay must not execute')):
        assert m.read_dictionary_request_result(moved,1)['result']==result['result']
    assert inventory(moved)==before and not root.exists()


@pytest.mark.parametrize('status',['NO_USABLE_BUNDLE','SOURCE_PREPARATION_UNQUALIFIED','NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED'])
def test_unusable_repair_truthfully_skips_continuation(joined,status):
    m,args,root,sdk,store,generations,state=joined;state['repair_status']=status
    m.initialize_dictionary_request(output=root,**args)
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    exact=m.read_dictionary_request_result(root,1)
    assert result['result']['status']==status and result['result']['continuation'] is None
    assert exact['runtime'] is None and exact['continuation'] is None and state['calls']==[]
    assert m.inspect_dictionary_request(root)['attempts'][0]['children']['continuation']['state']=='NOT_CREATED'


@pytest.mark.parametrize('fault',['pre-header','worker-unknown'])
def test_unknown_continuation_blocks_fresh_recovery_even_after_caller_exit(joined,monkeypatch,fault):
    from nasolve import cif_repair_process as process
    m,args,root,sdk,store,generations,state=joined;state['fault']=fault
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises((KeyboardInterrupt,RuntimeError)):
        m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    monkeypatch.setattr(m,'coordinator_alive',lambda _:False);monkeypatch.setattr(process,'coordinator_alive',lambda _:False)
    before=inventory(root);observed=m.inspect_dictionary_request(root)
    assert observed['availability']=='BLOCKED' and observed['attempts'][0]['children']['continuation']['state']=='UNKNOWN'
    with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and len(state['calls'])==1


@pytest.mark.parametrize('fault',['after-header','interrupted'])
def test_known_stopped_recovery_creates_fresh_child_preserving_history(joined,monkeypatch,fault):
    from nasolve import cif_repair_process as process
    m,args,root,sdk,store,generations,state=joined;state['fault']=fault
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    first=root/'attempts/attempt-0001';before=inventory(first)
    if fault=='after-header':
        assert m.inspect_dictionary_request(root)['availability']=='BLOCKED'
        monkeypatch.setattr(m,'coordinator_alive',lambda _:False);monkeypatch.setattr(process,'coordinator_alive',lambda _:False)
    assert m.inspect_dictionary_request(root)['availability']=='AVAILABLE'
    state['fault']=None
    second=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert second['attempt_number']==2 and inventory(first)==before
    assert state['calls'][0]['output']!=state['calls'][1]['output']
    assert state['calls'][0]['identity']!=state['calls'][1]['identity']
    assert second['result']['selected_attempts']=={code:2 for code in generations}
    if fault=='after-header':assert not (first/'finished.json').exists()


@pytest.mark.parametrize('defect',['missing-parent','foreign-parent','coordinator','runtime','settings'])
def test_rehashed_continuation_cannot_change_parent_or_frozen_intent(joined,defect):
    from nasolve.cif_runtime_continuation_process import _SCOPE
    from nasolve.cif_repair_process import _bundle
    m,args,root,sdk,store,generations,state=joined;m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    outer=root/'attempts/attempt-0001';work=outer/'continuation'
    (outer/'finished.json').unlink();(work/'ownership/finished.json').unlink()
    path=work/'ownership/continuation.json';header=read_record(path)
    if defect=='missing-parent':header.pop('attempt_owner')
    elif defect=='foreign-parent':header['attempt_owner']['attempt_id']=str(uuid.uuid4())
    elif defect=='coordinator':header['coordinator']['pid']+=1
    elif defect=='runtime':(work/'inputs/runtime/dictionary.cif').write_text('changed selected dictionary\n')
    else:
        settings=work/'inputs/configuration.json';v=json.loads(settings.read_bytes());v['limits']['readyset']=13;settings.write_text(json.dumps(v))
    header['input_files']=_bundle(work,_SCOPE);write_record(path,header,replace=True)
    with pytest.raises(ValueError):m.inspect_dictionary_request(root)


@pytest.mark.parametrize('boundary',['execution','final-replay'])
def test_outer_allowance_includes_continuation_and_final_readback(joined,monkeypatch,boundary):
    m,args,root,sdk,store,generations,state=joined;m.initialize_dictionary_request(output=root,**args)
    clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    name='execute_runtime_continuation' if boundary=='execution' else 'read_runtime_continuation';original=getattr(m.continuation,name)
    def expire(*a,**k):
        result=original(*a,**k);clock[0]=61.;return result
    monkeypatch.setattr(m.continuation,name,expire)
    with pytest.raises(TimeoutError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    owner=m.inspect_dictionary_request(root)['attempts'][0]
    assert owner['finished']['outcome']=='RAISED'
    assert owner['children']['continuation']['finished']['outcome']=='RETURNED'
    assert (root/'attempts/attempt-0001/continuation/runtime/runtime_bundle.json').exists()


def test_continuation_uses_same_exhaustible_request_and_preserves_old_result(joined):
    m,args,root,sdk,store,generations,state=joined;args['max_attempts']=1
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root)
    with pytest.raises(CampaignProcessError):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root)==before and len(state['calls'])==1


def test_postmr_entry_forwards_frozen_continuation_without_running_it(entry_case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generations,calls=entry_case
    r=initialize_postmr_dictionary_request(**args,continuation_options=OPTIONS)
    assert r['configuration']['continuation']['readyset_timeout_seconds']==12.5 and not calls
    result=m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generations)
    assert result['result']['continuation'] is None and result['result']['status']=='NO_USABLE_BUNDLE'


def test_postmr_rejects_invalid_continuation_before_freezing_sources(entry_case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generations,calls=entry_case;before=inventory(args['output'].parent)
    with pytest.raises(ValueError):initialize_postmr_dictionary_request(**args,continuation_options=dict(OPTIONS,restore_serialization=1))
    assert inventory(args['output'].parent)==before and not calls


def test_continuation_mode_cannot_reset_shared_generation_history(case,monkeypatch):
    from tests.test_cif_complete_request import test_generation_limit_is_shared_across_failed_outer_attempts
    m,args,root,sdk,store,generations,calls=case;args=dict(args,continuation_options=OPTIONS)
    test_generation_limit_is_shared_across_failed_outer_attempts((m,args,root,sdk,store,generations,calls),monkeypatch)


@pytest.mark.parametrize('partition',['both-valid','outer-files','child-files','outer-bytes','child-bytes'])
def test_composed_inventory_keeps_both_original_partition_bounds(tmp_path,monkeypatch,partition):
    from nasolve import cif_complete_request as m
    from nasolve import cif_component_runtime as frozen
    monkeypatch.setattr(frozen,'MAX_FILES',10);monkeypatch.setattr(frozen,'MAX_BYTES',100)
    outer=11 if partition=='outer-files' else 6;child=11 if partition=='child-files' else 6
    for label,count in [('',outer),('continuation',child)]:
        folder=tmp_path/label;folder.mkdir(exist_ok=True)
        for i in range(count):
            data=b'x'*20 if partition==('child-bytes' if label else 'outer-bytes') else b'x'
            (folder/str(i)).write_bytes(data)
    if partition=='both-valid':
        result=m._attempt_files(tmp_path,with_continuation=True);assert len(result['files'])==12
        with pytest.raises(ValueError):m._attempt_files(tmp_path)
    else:
        with pytest.raises(ValueError,match='partition exceeds'):m._attempt_files(tmp_path,with_continuation=True)


@pytest.mark.parametrize('excess', [None, 'working', 'repair', 'continuation', 'published'])
def test_v2_nested_continuation_partitions_keep_independent_bounds(tmp_path, monkeypatch, excess):
    from nasolve import cif_complete_request as m
    from nasolve import cif_component_runtime as frozen
    monkeypatch.setattr(frozen, 'MAX_FILES', 10); monkeypatch.setattr(frozen, 'MAX_BYTES', 100)
    folders = dict(working='preparation', repair='repair/attempts/attempt-0001/execution/runtime',
                   continuation='continuation/inputs', published='continuation/runtime')
    for label, name in folders.items():
        folder = tmp_path / name; folder.mkdir(parents=True)
        for i in range(11 if label == excess else 6): (folder / str(i)).write_bytes(b'x' * 10)
    if excess is None:
        result = m._attempt_files(tmp_path, with_continuation=True, artifact_policy=m.ARTIFACT_POLICY)
        assert len(result['files']) == 24
        with pytest.raises(ValueError):
            m._attempt_files(tmp_path, with_continuation=True, artifact_policy=m.LEGACY_ARTIFACT_POLICY)
    else:
        with pytest.raises(ValueError):
            m._attempt_files(tmp_path, with_continuation=True, artifact_policy=m.ARTIFACT_POLICY)


def test_old_continuation_settings_retain_flat_child_policy(case):
    m, args, root, sdk, store, generations, calls = case
    old = dict(OPTIONS, execution_policy=m.continuation.POLICY_ID,
               process_policy=m.CONTINUATION_PROCESS_POLICY,
               artifact_policy='cif-complete-continuation-artifacts-v1')
    request = m.initialize_dictionary_request(output=root, **dict(args, continuation_options=old,
        artifact_policy=m.LEGACY_ARTIFACT_POLICY))
    settings = request['configuration']['continuation']
    assert settings == old and m._continuation_parameters(request['configuration'])['artifact_policy'] is None
    assert m.inspect_dictionary_request(root)['request'] == request and not calls


@pytest.mark.parametrize('value', [None, 'unknown', True, {}])
def test_invalid_frozen_child_artifact_policy_refuses(case, value):
    m, args, root, sdk, store, generations, calls = case
    options = dict(OPTIONS, execution_policy=m.continuation.POLICY_ID,
                   process_policy=m.CONTINUATION_PROCESS_POLICY,
                   artifact_policy='cif-complete-continuation-artifacts-v1',
                   child_artifact_policy=value)
    with pytest.raises(ValueError, match='artifact policy'):
        m.initialize_dictionary_request(output=root, **dict(args, continuation_options=options))
    assert not (root / 'request.json').exists() and not calls


def test_new_minimal_continuation_options_freeze_native_asu_policy(case):
    m,args,root,sdk,store,generations,calls=case
    request=m.initialize_dictionary_request(output=root,**dict(args,continuation_options=OPTIONS))
    settings=request['configuration']['continuation']
    assert settings['native_nonbonded_policy']=='cif-native-nonbonded-asu-attribution-v1'
    assert m._continuation_parameters(request['configuration'])['nonbonded_policy']==settings['native_nonbonded_policy']
    assert m.inspect_dictionary_request(root)['request']==request


def test_c200_frozen_continuation_settings_keep_legacy_native_mode(case):
    m,args,root,sdk,store,generations,calls=case
    old=dict(OPTIONS,execution_policy=m.continuation.POLICY_ID,process_policy=m.CONTINUATION_PROCESS_POLICY,
        artifact_policy='cif-complete-continuation-artifacts-v1',child_artifact_policy=m.continuation.ARTIFACT_POLICY)
    request=m.initialize_dictionary_request(output=root,**dict(args,continuation_options=old))
    assert request['configuration']['continuation']==old
    assert m._continuation_parameters(request['configuration'])['nonbonded_policy'] is None
    assert m.inspect_dictionary_request(root)['request']==request and not calls


@pytest.mark.parametrize('policy',[None,'unknown',True,{},''])
def test_invalid_frozen_native_policy_refuses_before_request(case,policy):
    m,args,root,sdk,store,generations,calls=case
    options=dict(OPTIONS,execution_policy=m.continuation.POLICY_ID,process_policy=m.CONTINUATION_PROCESS_POLICY,
        artifact_policy='cif-complete-continuation-artifacts-v1',child_artifact_policy=m.continuation.ARTIFACT_POLICY,
        native_nonbonded_policy=policy)
    with pytest.raises(ValueError,match='nonbonded'):
        m.initialize_dictionary_request(output=root,**dict(args,continuation_options=options))
    assert not (root/'request.json').exists() and not calls


@pytest.mark.parametrize('kind', ['complete-legacy', 'complete-partitioned', 'continuation-legacy', 'continuation-partitioned'])
def test_owner_inventory_does_not_retain_the_whole_payload(tmp_path, kind):
    from hashlib import sha256
    import tracemalloc
    from nasolve import cif_complete_request as complete
    from nasolve import cif_runtime_continuation as continuation
    payload = b'x' * (2 * 1024 * 1024)
    expected = {}
    for i in range(8):
        name = f'{i}.dat'
        (tmp_path / name).write_bytes(payload)
        expected[name] = dict(sha256=sha256(payload).hexdigest(), size=len(payload))
    tracemalloc.start()
    try:
        if kind.startswith('complete'):
            result = complete._attempt_files(tmp_path, with_continuation=True,
                artifact_policy=complete.ARTIFACT_POLICY if kind.endswith('partitioned') else None)['files']
        else:
            config = dict(artifact_policy=continuation.ARTIFACT_POLICY) if kind.endswith('partitioned') else {}
            result = continuation._continuation_files(tmp_path, config)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    # An inventory needs hashes/sizes, not all sixteen MiB of source payload.
    assert peak < 8 * 1024 * 1024
    assert result == expected
