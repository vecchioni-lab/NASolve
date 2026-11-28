"""Discovery intent crosses existing requests; native chemistry has separate tests."""
from copy import deepcopy
from unittest.mock import patch
import json
import shutil
import pytest
from nasolve.campaign_records import read_record, write_record
from nasolve.cif_prepared_bond_discovery import POLICY_ID
from tests.test_cif_complete_continuation import joined
from tests.test_cif_complete_request import case
from tests.test_cif_postmr_request import entry_case, frozen_entry
from tests.test_cif_repair_attempt import inventory
from tests.test_postmr_runtime import setup as postmr_setup, checked_case


@pytest.fixture
def automatic(joined,monkeypatch):
    from nasolve import cif_prepared_bond_discovery as binding
    m,args,root,sdk,store,generations,state=joined
    # Transport/recovery only: source/reference decisions use real chemistry in
    # test_cif_prepared_bond_discovery. Here the synthetic worker has no candidates.
    monkeypatch.setattr(binding,'prepared_bond_queries',lambda bundle:{'YYY':{'selected_bonds':[]}})
    old=m.repair.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        assert kw['automatic_bond_targets'] is True and 'bond_targets' not in kw
        result=old(*a,**kw);result['bond_discovery_policy']=POLICY_ID
        (a[2]/'repair_execution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(m.repair,'execute_prepared_dictionary_repair',execute)
    args.update(automatic_bond_targets=True,artifact_policy=m.CAPTURE_ARTIFACT_POLICY)
    return joined


def test_saved_automatic_intent_survives_attempts_readyset_archive_and_move(automatic,monkeypatch):
    from nasolve.cif_attempt_retention import retire_attempt_working_files
    m,args,root,sdk,store,generations,state=automatic
    request=m.initialize_dictionary_request(output=root,**args)
    assert request['configuration']['bond_discovery_policy']==POLICY_ID and not state['calls']
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert m.read_dictionary_request_result(root,1)['execution']['bond_discovery_policy']==POLICY_ID
    retire_attempt_working_files(root,1);first=inventory(root/'attempts/attempt-0001')
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root/'attempts/attempt-0001')==first
    moved=root.rename(root.with_name('moved'))
    shutil.rmtree(store);shutil.rmtree(sdk.root);shutil.rmtree(args['source_selection'])
    args['model'].unlink()
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read cannot execute')):
        for n in (1,2):
            r=m.read_dictionary_request_result(moved,n)
            assert r['execution']['bond_discovery_policy']==POLICY_ID and r['continuation'] is not None
    assert inventory(moved)==before


@pytest.mark.parametrize('where',['outer','child','execution'])
@pytest.mark.parametrize('defect',['drop','unknown'])
def test_saved_automatic_intent_cannot_be_lost_or_replaced(automatic,where,defect):
    m,args,root,sdk,store,generations,state=automatic
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    p=root/{'outer':'request.json','child':'attempts/attempt-0001/repair/request.json',
            'execution':'attempts/attempt-0001/repair/attempts/attempt-0001/execution/repair_execution.json'}[where]
    if where=='execution':r=json.loads(p.read_text());target=r
    else:r=read_record(p);target=r['configuration']
    if defect=='drop':target.pop('bond_discovery_policy')
    else:target['bond_discovery_policy']='unknown'
    if where=='execution':p.write_text(json.dumps(r))
    else:write_record(p,r,replace=True)
    before=inventory(root)
    with pytest.raises(ValueError):m.inspect_dictionary_request(root)
    assert inventory(root)==before


@pytest.mark.parametrize('bad',[None,1,[],{},'true'])
def test_bad_complete_intent_refuses_before_request(automatic,bad):
    m,args,root,sdk,store,generations,state=automatic;args['automatic_bond_targets']=bad
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**args)
    assert not root.exists() and not state['calls']


def test_automatic_intent_needs_capture_policy_and_excludes_manual_pairs(automatic):
    m,args,root,*_=automatic
    args['artifact_policy']=m.ARTIFACT_POLICY
    with pytest.raises(ValueError,match='v4'):m.initialize_dictionary_request(output=root,**args)
    args['artifact_policy']=m.CAPTURE_ARTIFACT_POLICY;args['bond_targets']={'YYY':[['R','Y']]}
    with pytest.raises(ValueError,match='combined'):m.initialize_dictionary_request(output=root,**args)
    assert not root.exists()


@pytest.mark.parametrize('enabled',[False,True])
def test_fresh_and_frozen_ordinary_intake_freeze_same_mode_without_native_work(frozen_entry,case,enabled):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    from nasolve.cif_complete_request import ARTIFACT_POLICY,CAPTURE_ARTIFACT_POLICY
    m,args,sdk,store,generations,calls=frozen_entry
    fresh=deepcopy(args);fresh.pop('frozen_sources')
    fresh.update(source_output=case[2].parent/'fresh-sources',output=case[2].parent/'fresh-request',
        data_root=case[2].parent/'data',ready_set_executable=sdk.executables['phenix.ready_set'])
    with patch('subprocess.Popen',side_effect=AssertionError('No native intake')):
        a=initialize_postmr_dictionary_request(**args,automatic_bond_targets=enabled)
        b=initialize_postmr_dictionary_request(**fresh,automatic_bond_targets=enabled)
    assert a['configuration']==b['configuration']
    assert a['configuration'].get('bond_discovery_policy')==(POLICY_ID if enabled else None)
    assert a['configuration']['artifact_policy']==(CAPTURE_ARTIFACT_POLICY if enabled else ARTIFACT_POLICY)
    assert not calls


@pytest.mark.parametrize('enabled',[False,True])
def test_public_checked_entry_forwards_only_requested_discovery(tmp_path,monkeypatch,enabled):
    from nasolve.postmr import prepare_postmr
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    result=prepare_postmr(run,ready,phenix_installation=sdk,checked_preparation=True,automatic_bond_targets=enabled)
    assert calls[0][1].get('automatic_bond_targets',False)==enabled
    assert ('automatic_bond_targets' in calls[0][1])==enabled
    assert reads==[1] and result.model_path==exact['runtime']['model']


@pytest.mark.parametrize('kwargs',[{'automatic_bond_targets':1},{'automatic_bond_targets':None},
    {'automatic_bond_targets':True,'bond_targets':{'DA':[['R','Y']]}}])
def test_bad_ordinary_intent_refuses_before_tool_setup(tmp_path,kwargs):
    from nasolve.cif_ordinary_postmr import initialize_ordinary_postmr_request
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',side_effect=AssertionError('No tools')):
        with pytest.raises(ValueError):initialize_ordinary_postmr_request(tmp_path/'run',None,expected_dialect='CHEMICAL_COMPONENTS_CIF',**kwargs)
    assert not (tmp_path/'run').exists()


def test_public_automatic_intent_requires_checked_preparation(tmp_path):
    from nasolve.postmr import prepare_postmr,PostMRPreparationError
    run,ready,sdk,data=postmr_setup(tmp_path)
    before=inventory(run)
    with patch('nasolve.postmr._selected_postmr_environment',side_effect=AssertionError('No tools')):
        with pytest.raises(PostMRPreparationError,match='requires checked'):
            prepare_postmr(run,ready,phenix_installation=sdk,automatic_bond_targets=True)
    assert inventory(run)==before
