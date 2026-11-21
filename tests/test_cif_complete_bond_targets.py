"""Bond choices cross complete ownership/continuation/retention, not chemistry.

Existing real source/snapshot/request readers are used. Only the source query and
native/continuation result producers are synthetic; C326 covers real graph/native
qualification separately.
"""
import json
import shutil
from pathlib import Path
import pytest
from nasolve.campaign_records import read_record, write_record
from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
from tests.test_cif_repair_attempt import inventory


@pytest.fixture
def bonds(joined, monkeypatch):
    from nasolve import cif_prepared_repair_execution as executor
    m,args,root,sdk,store,generations,state=joined
    code=sorted(generations)[0]
    monkeypatch.setattr(executor,'linear_bond_query',lambda source,code:dict(selected_bonds=[['R','Y'],['X','Y']]))
    original=m.repair.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        assert kw['bond_targets']=={code:[['R','Y']]}
        r=original(*a,**kw);r['bond_targets']=executor._bond_target_choices(a[0],kw['bond_targets'])
        (a[2]/'repair_execution.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(m.repair,'execute_prepared_dictionary_repair',execute)
    args['bond_targets']={code:[['Y','R']]}
    return joined,code


def test_complete_target_choice_survives_continuation_archive_and_move(bonds,monkeypatch):
    from nasolve.cif_attempt_retention import retire_attempt_working_files
    (m,args,root,sdk,store,generations,state),code=bonds
    request=m.initialize_dictionary_request(output=root,**args)
    config=request['configuration']['bond_targets']
    assert config==dict(policy_id='cif-prepared-source-bond-targets-v1',choices={code:[['R','Y']]})
    assert not state['calls'] and not (root/'attempts').exists()
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    first=m.read_dictionary_request_result(root,1)
    assert first['execution']['bond_targets']==config and first['continuation'] is not None
    assert read_record(root/'attempts/attempt-0001/repair/request.json')['configuration']['bond_targets']==config
    retire_attempt_working_files(root,1)
    prior=inventory(root/'attempts/attempt-0001')
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    assert inventory(root/'attempts/attempt-0001')==prior
    moved=root.rename(root.with_name('moved'))
    shutil.rmtree(store);shutil.rmtree(sdk.root);shutil.rmtree(args['source_selection']);Path(args['model']).unlink()
    for item in args['components']:shutil.rmtree(item['retained_snapshot'])
    def forbidden(*a,**kw):raise AssertionError('Cold read cannot execute or write')
    monkeypatch.setattr('subprocess.Popen',forbidden);monkeypatch.setattr(m,'write_record',forbidden)
    before=inventory(moved)
    for n in (1,2):
        read=m.read_dictionary_request_result(moved,n)
        assert read['execution']['bond_targets']==config and read['continuation'] is not None
    assert inventory(moved)==before


@pytest.mark.parametrize('bad',[{},[],True,{'absent':[['R','Y']]},{'YYY':[]},{'YYY':[['R','Y'],['Y','R']]},{'YYY':[['unknown','Y']]}])
def test_invalid_complete_target_selection_never_starts_children(bonds,bad):
    (m,args,root,sdk,store,generations,state),code=bonds
    args['bond_targets']=bad
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and not state['calls']


@pytest.mark.parametrize('bad',[None,{},True,{'policy_id':'wrong','choices':{'YYY':[['R','Y']]}},
    {'policy_id':'cif-prepared-source-bond-targets-v1','choices':None}])
def test_bad_saved_outer_target_choice_refuses_read_only(bonds,bad):
    (m,args,root,sdk,store,generations,state),code=bonds
    m.initialize_dictionary_request(output=root,**args)
    p=root/'request.json';r=read_record(p);r['configuration']['bond_targets']=bad;write_record(p,r,replace=True)
    before=inventory(root)
    with pytest.raises(ValueError):m.inspect_dictionary_request(root)
    assert inventory(root)==before and not state['calls']


@pytest.mark.parametrize('where',['outer','child','execution'])
def test_target_choice_cannot_be_silently_dropped_or_changed(bonds,where):
    (m,args,root,sdk,store,generations,state),code=bonds
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    p=root/({'outer':'request.json','child':'attempts/attempt-0001/repair/request.json',
             'execution':'attempts/attempt-0001/repair/attempts/attempt-0001/execution/repair_execution.json'}[where])
    if where=='execution':
        r=json.loads(p.read_text());r.pop('bond_targets');p.write_text(json.dumps(r))
    else:
        r=read_record(p);r['configuration']['bond_targets']['choices'][code]=[['X','Y']];write_record(p,r,replace=True)
    before=inventory(root)
    with pytest.raises(ValueError):m.inspect_dictionary_request(root)
    assert inventory(root)==before


def test_caller_cannot_change_selection_while_inputs_are_frozen(bonds,monkeypatch):
    (m,args,root,sdk,store,generations,state),code=bonds
    original=m._freeze
    def freeze(*a,**kw):
        r=original(*a,**kw);args['bond_targets'][code]=[['X','Y']];return r
    monkeypatch.setattr(m,'_freeze',freeze)
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,**args)
    assert not (root/'request.json').exists() and not state['calls']
