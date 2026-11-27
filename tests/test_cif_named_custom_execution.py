"""Explicit comparison choice follows current ownership, publication and replay."""
from copy import deepcopy
import json,shutil
from unittest.mock import patch
import pytest
from tests.test_cif_runtime_continuation import continuation
from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
from nasolve.cif_terminal_qualification import CUSTOM_REQUEST_POLICY


@pytest.mark.parametrize('enabled',[False,True])
def test_continuation_binds_choice_through_publication_and_relocation(continuation,monkeypatch,enabled):
    m,parent,sdk,out,state=continuation;seen=[]
    def compare(*args,**kwargs):
        seen.append(dict(kwargs));selected=kwargs.get('explicit_request_policy')==CUSTOM_REQUEST_POLICY
        return dict(mechanics_checks_pass=selected,policy_id='synthetic-v3' if selected else 'synthetic-v2')
    monkeypatch.setattr('nasolve.cif_postmr_cached_model.qualify_cached_model_roundtrip',compare)
    options=dict(explicit_request_policy=CUSTOM_REQUEST_POLICY) if enabled else {}
    report=m.execute_runtime_continuation(parent,sdk,out,**options)
    assert report['selected']==('readyset_checked_model' if enabled else 'verified_parent_runtime')
    manifest=json.loads((out/'runtime/runtime_bundle.json').read_bytes())
    assert manifest['source_selection'].get('explicit_request_policy')==options.get('explicit_request_policy')
    assert manifest['source_review']['policy_id']==('cif-selected-runtime-readyset-roundtrip-v2' if enabled else 'cif-selected-runtime-readyset-roundtrip-v1')
    moved=out.rename(out.with_name('relocated'));shutil.rmtree(parent);shutil.rmtree(sdk.root)
    with patch('subprocess.Popen',side_effect=AssertionError('Replay must not execute')):
        assert m.read_runtime_continuation(moved)['report']==report
    assert seen and all(v==options for v in seen)
    if enabled:
        # Even a rewritten manifest cannot drop the selection policy while
        # retaining the recorded v3 comparison/decision.
        del manifest['source_selection']['explicit_request_policy']
        (moved/'runtime/runtime_bundle.json').write_text(json.dumps(manifest))
        with pytest.raises(ValueError):m.resolve_runtime_bundle(moved/'runtime')


def test_complete_request_freezes_and_forwards_opt_in(case):
    m,args,root,sdk,store,generations,calls=case
    options=dict(readyset_timeout_seconds=12.5,restore_serialization=True,explicit_request_policy=CUSTOM_REQUEST_POLICY)
    report=m.initialize_dictionary_request(output=root,**dict(args,continuation_options=options))
    c=report['configuration'];assert c['continuation']['explicit_request_policy']==CUSTOM_REQUEST_POLICY
    forwarded=m._continuation_parameters(c);assert forwarded['explicit_request_policy']==CUSTOM_REQUEST_POLICY
    assert m.inspect_dictionary_request(root)['request']['configuration']==c
    legacy=m.initialize_dictionary_request(output=root.with_name('legacy'),**dict(args,continuation_options={k:v for k,v in options.items() if k!='explicit_request_policy'}))
    assert 'explicit_request_policy' not in legacy['configuration']['continuation']
    assert 'explicit_request_policy' not in m._continuation_parameters(legacy['configuration'])


@pytest.mark.parametrize('value',['unknown',False,None])
def test_unknown_or_missing_explicit_choice_refuses_before_request(case,value):
    m,args,root,sdk,store,generations,calls=case
    with pytest.raises(ValueError):
        m.initialize_dictionary_request(output=root,**dict(args,continuation_options=dict(readyset_timeout_seconds=12.5,restore_serialization=True,explicit_request_policy=value)))
    assert not(root/'request.json').exists() and not calls


def test_complete_attempt_preserves_comparison_choice_through_child_and_replay(joined):
    m,args,root,sdk,store,generations,state=joined
    args['continuation_options']['explicit_request_policy']=CUSTOM_REQUEST_POLICY
    m.initialize_dictionary_request(output=root,**args)
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert state['calls'][0]['settings']['explicit_request_policy']==CUSTOM_REQUEST_POLICY
    assert m.read_dictionary_request_result(root,1)['result']==result['result']
    child=root/'attempts/attempt-0001/continuation/inputs/configuration.json'
    assert json.loads(child.read_bytes())['explicit_request_policy']==CUSTOM_REQUEST_POLICY
    moved=root.rename(root.with_name('relocated'))
    shutil.rmtree(store);shutil.rmtree(sdk.root);shutil.rmtree(args['source_selection'])
    from pathlib import Path
    Path(args['model']).unlink()
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    with patch('subprocess.Popen',side_effect=AssertionError('Replay must not execute')):
        assert m.read_dictionary_request_result(moved,1)['result']==result['result']
