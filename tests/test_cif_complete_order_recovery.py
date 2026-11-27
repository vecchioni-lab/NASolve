"""Replay a narrowly permitted second source-order attempt without losing the first."""
from copy import deepcopy

import pytest

from nasolve import cif_complete_order_recovery as order
from nasolve.cif_acquisition_recovery import CONNECTED_INPUT_POLICY, EVIDENCE, SOURCE_INPUT_POLICY
from nasolve.cif_dictionary_store import _bytes
from nasolve.cif_repair_attempt import _inventory


def config():
    primary = dict(dictionary_request=dict(component="Q17", recipe=dict(source_input_policy=SOURCE_INPUT_POLICY,
                     bond_representation_policy="cif-source-exact-bond-orders-v1")), input_files=_inventory({"source.cif": b"source"}),
                   max_attempts=3, limits=dict(total_timeout_seconds=60), consumer={"version": "test"})
    return dict(**order.permission(True), components={"Q17":primary}, controls={"sites":{"Q17":{"retained":None}}})


@pytest.mark.parametrize("state", ("eligible", "ordinary_success", "unrelated_failure", "another_parent", "live", "expired", "interrupted"))
def test_recovery_uses_only_own_stopped_eligible_attempt_and_original_budget(tmp_path, monkeypatch, state):
    primary = tmp_path / "acquisitions/Q17"
    owner = {"attempt_id":"outer-2"}
    calls = []
    row = dict(state="STOPPED",number=2,finished={"outcome":"RAISED"},intent={"parent_attempt":owner})
    if state=="another_parent":
        row["intent"] = {"parent_attempt":{"attempt_id":"unrelated"}}
    stage = {"returned": False}
    def allowance():
        return 0 if state=="expired" and stage["returned"] else 30
    def attempt(source, code, store, directory, **opts):
        calls.append((directory, opts))
        if directory==primary:
            assert 0 < opts["_remaining_seconds"]() <= 30
            stage["returned"] = True
            if state=="ordinary_success":
                return {"attempt_number":2}
            if state=="interrupted":
                raise KeyboardInterrupt
            raise ValueError("first attempt failed")
        assert opts["connected_order_failure"] == (primary,2) and opts["max_attempts"] == 1
        assert opts["_parent_attempt_identity"] == owner and 0 < opts["_remaining_seconds"]() <= 30
        return {"attempt_number":1}
    monkeypatch.setattr(order.acquisition,"acquire_dictionary_attempt",attempt)
    monkeypatch.setattr(order.acquisition,"inspect_acquisition_request",lambda p: dict(state="RECORDED",availability="BLOCKED" if state=="live" else "AVAILABLE",attempts=[row]))
    monkeypatch.setattr(order.recovery,"read_connected_order_failure",lambda p,n: None if state=="unrelated_failure" else {"attempt":n})
    opts = dict(_parent_attempt_identity=owner,_remaining_seconds=allowance,max_attempts=3,total_timeout_seconds=60)
    if state in ("eligible","ordinary_success"):
        folder, child, proof = order.acquire(None,"Q17",tmp_path/"store",primary,2,opts)
        assert folder == (primary.parent/"Q17-order-0002" if state=="eligible" else primary)
        assert proof == ({"original":2,"reordered":1} if state=="eligible" else None)
        assert child["attempt_number"] == (1 if state=="eligible" else 2)
    elif state=="expired":
        with pytest.raises(order.acquisition.AcquisitionBudgetExceeded):
            order.acquire(None,"Q17",tmp_path/"store",primary,2,opts)
    elif state=="interrupted":
        with pytest.raises(KeyboardInterrupt):
            order.acquire(None,"Q17",tmp_path/"store",primary,2,opts)
    else:
        with pytest.raises(ValueError,match="first attempt failed"):
            order.acquire(None,"Q17",tmp_path/"store",primary,2,opts)
    assert len(calls)==(2 if state=="eligible" else 1)


@pytest.mark.parametrize("defect", ("none", "changed_prior", "different_source", "different_limit", "different_limit_type", "duplicate", "primary_succeeded", "lost_proof", "unknown", "orphan_process"))
def test_recovered_acquisition_rebinds_its_original_before_an_outer_result(tmp_path, monkeypatch, defect):
    original = {"state":"STOPPED","number":1,"finished":{"outcome":"RAISED"}}
    expected = config()["components"]["Q17"]
    proof = {"pinned_failure":"earlier source proof"}
    normal = expected["dictionary_request"]
    request = dict(expected, dictionary_request=dict(normal,recipe=dict(normal["recipe"],source_input_policy=CONNECTED_INPUT_POLICY)),
                   input_files=dict(expected["input_files"],**_inventory({EVIDENCE:_bytes(proof)})),max_attempts=1)
    child = {"state":"STOPPED","number":1,"finished":{"outcome":"RETURNED"}}
    state = {"state":"RECORDED","availability":"EXHAUSTED","request":{"configuration":request},"attempts":[child]}
    if defect=="changed_prior": proof["pinned_failure"]="other historical source"
    if defect=="different_source": request["dictionary_request"]["component"]="X"
    if defect=="different_limit": request["limits"]={"total_timeout_seconds":600}
    if defect=="different_limit_type": request["max_attempts"]=True
    if defect=="duplicate": state["attempts"].append(deepcopy(child))
    if defect=="primary_succeeded": original["finished"]["outcome"]="RETURNED"
    if defect=="lost_proof": proof=None
    if defect=="unknown": state["state"]="UNKNOWN"
    if defect=="orphan_process": state["availability"]="BLOCKED"
    (tmp_path/"acquisitions/Q17-order-0002").mkdir(parents=True)
    monkeypatch.setattr(order.acquisition,"inspect_acquisition_request",lambda p:state)
    monkeypatch.setattr(order.recovery,"read_connected_order_failure",lambda p,n:proof)
    if defect=="none":
        assert order.inspect(tmp_path,"Q17",2,expected,original)==(state["request"],child)
    elif defect=="unknown":
        assert order.inspect(tmp_path,"Q17",2,expected,original)==(None,{"state":"UNKNOWN","activity":None})
    elif defect=="orphan_process":
        assert order.inspect(tmp_path,"Q17",2,expected,original)==(state["request"],{"state":"UNKNOWN","activity":None})
    else:
        with pytest.raises(ValueError):
            order.inspect(tmp_path,"Q17",2,expected,original)


def test_only_the_graph_proven_failure_may_precede_a_successful_component():
    cfg=config()
    assert order.eligible(cfg,"Q17")
    assert not order.eligible(dict(cfg,connected_order_policy="other"),"Q17")
    cfg["controls"]["sites"]["Q17"]["retained"]="retained/Q17"
    assert not order.eligible(cfg,"Q17")
    failed={"state":"STOPPED","finished":{"outcome":"RAISED"}}
    good={"state":"STOPPED","finished":{"outcome":"RETURNED"}}
    rows={"Q17":failed,"order/Q17":good,"OTHER":good,"repair":good}
    bindings={k:{"number":(2 if k=="Q17" else 1)} for k in rows}
    selected, prior=order.selection(["Q17","OTHER"],rows,bindings)
    assert selected=={"Q17":bindings["order/Q17"],"OTHER":bindings["OTHER"]}
    assert prior=={"Q17":{"original":2,"reordered":1}}
    with pytest.raises(ValueError):
        order.selection(["Q17","OTHER"],dict(rows,OTHER=failed),bindings)
    with pytest.raises(ValueError):
        order.selection(["Q17","OTHER"],{k:v for k,v in rows.items() if k!="order/Q17"},bindings)
