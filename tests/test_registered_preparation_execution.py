"""Opt-in registered execution keeps the existing child/process owners.

Synthetic child transport below returns no usable model. Native qualified-result
acceptance is checked separately on fresh FT evidence; no fixture is chemistry.
"""
from copy import deepcopy
from unittest.mock import patch
import shutil

import pytest
pytest.importorskip('gemmi')
from .test_cif_complete_request import case
from .test_cif_postmr_request import entry_case
from .test_registered_preparation_request import registered_case
from .test_cif_repair_attempt import inventory


def test_new_policy_uses_existing_owned_attempt_without_claiming_usable_model(entry_case,tmp_path):
    from nasolve.cif_registered_execution import POLICY_ID
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generation,calls=registered_case(entry_case)
    request=initialize_postmr_dictionary_request(**args,registered_execution_policy=POLICY_ID)
    root=args['output'];state=m.inspect_dictionary_request(root)
    assert state['availability']=='AVAILABLE' and not state['attempts']
    assert request['configuration']['registered_execution_policy']==POLICY_ID
    result=m.execute_dictionary_request_attempt(root,sdk,store,generation=generation)
    exact=m.read_dictionary_request_result(root,1)
    assert result['result']['status']=='NO_USABLE_BUNDLE' and exact['runtime'] is None
    assert result['result']['registered_execution_policy']==POLICY_ID
    assert exact['registered_runtime_review'] is None and len(calls)==1
    state=m.inspect_dictionary_request(root)
    assert state['attempts'][0]['finished']['stopped_verified'] is True
    assert state['attempts'][0]['finished']['outcome']=='RETURNED'
    frozen=inventory(root);moved=tmp_path/'moved-request';root.rename(moved)
    shutil.rmtree(args['source_output']);args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read')):
        assert m.read_dictionary_request_result(moved,1)['result']==exact['result']
    assert inventory(moved)==frozen


@pytest.mark.parametrize('defect',['unknown','no_registration','readyset'])
def test_bad_execution_scope_refuses_without_children(entry_case,defect):
    from nasolve.cif_registered_execution import POLICY_ID
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generation,calls=registered_case(entry_case);policy=POLICY_ID
    if defect=='unknown':policy='registered-all-results'
    if defect=='no_registration':args.pop('registered_preparation')
    if defect=='readyset':args['continuation_options']={'readyset_timeout_seconds':60}
    with pytest.raises(ValueError):initialize_postmr_dictionary_request(**args,registered_execution_policy=policy)
    assert not calls and not (args['output']/'attempts').exists()
    assert not (args['output']/'request.json').exists()


def test_changed_registration_cannot_start_opted_in_attempt(entry_case):
    from nasolve.cif_registered_execution import POLICY_ID
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generation,calls=registered_case(entry_case)
    initialize_postmr_dictionary_request(**args,registered_execution_policy=POLICY_ID)
    p=args['output']/'inputs/registered_backbone/continuations.json';p.write_bytes(p.read_bytes()+b'\n')
    before=inventory(args['output'])
    with pytest.raises(ValueError):m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generation)
    assert inventory(args['output'])==before and not calls


def test_old_registered_request_remains_held_after_new_policy_exists(entry_case):
    from nasolve.cif_registered_execution import POLICY_ID
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generation,calls=registered_case(entry_case)
    initialize_postmr_dictionary_request(**args);before=inventory(args['output'])
    assert m.inspect_dictionary_request(args['output'])['availability']=='BLOCKED'
    with pytest.raises(ValueError,match='intake only'):
        m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generation)
    assert inventory(args['output'])==before and not calls


@pytest.mark.parametrize('bad',['qualification','continuation','missing_context','policy'])
def test_execution_fields_require_explicit_original_only_scope(bad):
    from nasolve.cif_registered_execution import POLICY_ID, execution_fields
    args=dict(policy=POLICY_ID,registered_backbone={'role':'registered'},qualify_no_repair=True,continuation_options=None)
    if bad=='qualification':args['qualify_no_repair']=False
    if bad=='continuation':args['continuation_options']={}
    if bad=='missing_context':args['registered_backbone']=None
    if bad=='policy':args['policy']=True
    with pytest.raises(ValueError):execution_fields(**args)


def test_usable_result_must_pass_registered_native_reader(tmp_path,monkeypatch):
    from nasolve.cif_registered_execution import review_execution_runtime
    from nasolve import cif_registered_preparation_native
    selected={'manifest_path':tmp_path/'runtime/runtime_bundle.json'};seen=[]
    config={'components':{'ZZZ':{},'YYY':{}},'registered_backbone':{'reference':'frozen'}}
    def review(inputs,codes,ref,value):
        seen.append((inputs,codes,ref,value));return {'ordinary_admission':False,'native_image_forces':'NOT_ASSESSED'}
    monkeypatch.setattr(cif_registered_preparation_native,'_review_original_selection',review)
    result=review_execution_runtime(tmp_path,config,selected)
    assert seen==[(tmp_path/'inputs',['YYY','ZZZ'],config['registered_backbone'],selected)]
    assert result['native_image_forces']=='NOT_ASSESSED' and result['ordinary_admission'] is False
    def refuse(*a):raise ValueError('Registered native result mismatch')
    monkeypatch.setattr(cif_registered_preparation_native,'_review_original_selection',refuse)
    with pytest.raises(ValueError,match='mismatch'):review_execution_runtime(tmp_path,config,selected)


def test_unusable_result_never_acquires_native_qualification(tmp_path,monkeypatch):
    from nasolve.cif_registered_execution import review_execution_runtime
    def forbidden(*args):raise AssertionError('No usable result to review')
    monkeypatch.setattr('nasolve.cif_registered_preparation_native._review_original_selection',forbidden)
    assert review_execution_runtime(tmp_path,{},None) is None
