"""Preserve exact numerical verdicts while avoiding repeated work per inspection."""
from copy import deepcopy
import pytest
from nasolve.cif_numerical_replay import numerical_replay_scope, validate_mixed_result
from nasolve.cif_mixed_gradient import _validate_result
from tests.test_cif_mixed_gradient import mixed_initial_result


def test_identical_numerical_proof_runs_once_per_scope_without_sharing_mutable_result():
    result,expected=mixed_initial_result();before=deepcopy((result,expected));calls=[]
    def counted(*args):
        calls.append(1);return _validate_result(*args)
    with numerical_replay_scope():
        first=validate_mixed_result(counted,result,expected,[0])
        original=deepcopy(first);first['checks']['unchanged_native_energy']=False
        with numerical_replay_scope():
            second=validate_mixed_result(counted,deepcopy(result),deepcopy(expected),[0])
        assert second==original and len(calls)==1
    with numerical_replay_scope():
        assert validate_mixed_result(counted,result,expected,[0])==original
    assert len(calls)==2 and (result,expected)==before


@pytest.mark.parametrize('changed',['result','expected','selected'])
def test_changed_evidence_recalculates_and_refuses_within_the_same_scope(changed):
    result,expected=mixed_initial_result();calls=[]
    def counted(*args):
        calls.append(1);return _validate_result(*args)
    with numerical_replay_scope():
        validate_mixed_result(counted,result,expected,[0])
        selected=[0]
        if changed=='result':result['gradient_audit']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
        elif changed=='expected':expected['energy_inventory']['snapshots'][0]['target']+=1.
        else:selected=[1]
        for _ in range(2):
            with pytest.raises(ValueError):validate_mixed_result(counted,result,expected,selected)
    assert len(calls)==3


def test_scope_exit_after_error_discards_prior_verdicts_and_unscoped_calls_repeat():
    calls=[]
    def checked(*args):calls.append(1);return {'status':'REVIEW'}
    with pytest.raises(RuntimeError), numerical_replay_scope():
        validate_mixed_result(checked,{}, {}, []);raise RuntimeError('inspection failed')
    with numerical_replay_scope():validate_mixed_result(checked,{}, {}, [])
    validate_mixed_result(checked,{}, {}, [])
    validate_mixed_result(checked,{}, {}, [])
    assert len(calls)==4


def test_different_validators_never_share_verdicts_and_review_stays_review():
    with numerical_replay_scope():
        assert validate_mixed_result(lambda *a:{'status':'REVIEW'}, {}, {}, [])=={'status':'REVIEW'}
        assert validate_mixed_result(lambda *a:{'status':'PASS'}, {}, {}, [])=={'status':'PASS'}


@pytest.mark.parametrize('unusual',[{1:'a'},(1,),float('nan')])
def test_non_json_or_lossy_inputs_use_original_validation_each_time(unusual):
    calls=[]
    def check(*args):calls.append(1);return {'status':'REVIEW'}
    with numerical_replay_scope():
        for _ in range(2):validate_mixed_result(check,unusual,{},[])
    assert len(calls)==2


def test_bounded_capacity_does_not_change_validation_or_retain_large_verdicts(monkeypatch):
    import nasolve.cif_numerical_replay as m
    monkeypatch.setattr(m,'MAX_ENTRIES',1);calls=[]
    def check(result,*args):calls.append(1);return {'status':result}
    with numerical_replay_scope():
        for value in ['one','two','one','two']:validate_mixed_result(check,value,{},[])
    assert len(calls)==3
    calls.clear();monkeypatch.setattr(m,'MAX_RESULT_BYTES',1)
    with numerical_replay_scope():
        for _ in range(2):validate_mixed_result(check,'large',{},[])
    assert len(calls)==2



def test_input_dictionary_order_is_not_normalized_or_treated_as_equivalent():
    calls=[]
    def check(result,*args):calls.append(1);return {'order':list(result)}
    with numerical_replay_scope():
        assert validate_mixed_result(check,{'a':1,'b':2},{},[])=={'order':['a','b']}
        assert validate_mixed_result(check,{'b':2,'a':1},{},[])=={'order':['b','a']}
    assert len(calls)==2
