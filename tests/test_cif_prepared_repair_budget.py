"""One explicit elapsed allowance across prepared repair stages, never a retry grant."""
import pytest
from .test_cif_prepared_repair_execution import case


@pytest.fixture
def timed(case, monkeypatch):
    m,b,sdk,out,state,calls,options=case
    clock=[0.0]
    monkeypatch.setattr(m,'monotonic',lambda:clock[0],raising=False)
    return case,clock


@pytest.mark.parametrize('value',[0,-1,True,1.5,float('nan'),float('inf'),3601,'10'])
def test_invalid_total_budget_refuses_before_outputs(timed,value):
    (m,b,sdk,out,state,calls,o),clock=timed
    with pytest.raises(ValueError,match='total'):
        m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=value,**o)
    assert not out.exists() and calls==[]


def test_workers_share_remaining_budget_instead_of_resetting(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;limits=[]
    native=m.inspect_native_bundle;gradient=m.audit_captured_mixed_gradients;attribution=m.audit_captured_linear_attribution
    def capture(*a,**k):
        limits.append(k['timeout_seconds']);r=native(*a,**{**k,'timeout_seconds':7});clock[0]+=3;return r
    def derivatives(*a,**k):
        limits.append(k['timeout_seconds']);r=gradient(*a,**{**k,'timeout_seconds':11});clock[0]+=5 if a[2].name=='original-gradient' else 1;return r
    def attribute(*a,**k):
        limits.append(k['timeout_seconds']);r=attribution(*a,**{**k,'timeout_seconds':9});clock[0]+=2;return r
    monkeypatch.setattr(m,'inspect_native_bundle',capture);monkeypatch.setattr(m,'audit_captured_mixed_gradients',derivatives);monkeypatch.setattr(m,'audit_captured_linear_attribution',attribute)
    r=m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)
    assert limits==[7,7,11,7,6,4]
    assert r['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME' and r['total_timeout_seconds']==20
    assert r['elapsed_seconds']==17 and r['whole_acquisition_ownership']=='NOT_IMPLEMENTED'
    assert 'COOPERATIVE' in r['total_deadline'] and r['automatic_adoption'] is False


@pytest.mark.parametrize('spent',[1,2])
def test_expired_preflight_does_not_reserve_output(timed,monkeypatch,spent):
    (m,b,sdk,out,state,calls,o),clock=timed
    def consumer(*a):clock[0]=spent;return True
    monkeypatch.setattr(m,'verify_current_consumer',consumer)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=1,**o)
    assert not out.exists() and calls==[]


@pytest.mark.parametrize('adapter',['prepare_linear_torsion_bundle','audit_captured_mixed_gradients','inspect_dictionary_bundle_repair'])
def test_late_stage_result_cannot_start_later_work_or_publish(timed,monkeypatch,adapter):
    (m,b,sdk,out,state,calls,o),clock=timed;original=getattr(m,adapter)
    def slow(*a,**k):
        result=original(*a,**k);clock[0]=20;return result
    monkeypatch.setattr(m,adapter,slow)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)
    assert not (out/'runtime').exists() and not (out/'repair_execution.json').exists()
    assert (out/'plan').exists() and 'BUDGET_EXHAUSTED' in (out/'progress.jsonl').read_text()
    assert 'NO_RECOVERY_AUTHORITY' in (out/'progress.jsonl').read_text()
    if adapter=='audit_captured_mixed_gradients':assert 'native-001' not in calls
    with pytest.raises(FileExistsError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)


def test_less_than_one_second_does_not_round_up_native_allowance(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;original=m.prepare_linear_torsion_bundle
    def plan(*a,**k):r=original(*a,**k);clock[0]=0.1;return r
    monkeypatch.setattr(m,'prepare_linear_torsion_bundle',plan)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=1,**o)
    assert not any(c.startswith('native') for c in calls)


def test_publication_overrun_preserves_partial_bundle_but_returns_no_success(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;original=m.prepare_repaired_component_runtime_bundle
    def publish(*a,**k):r=original(*a,**k);clock[0]=20;return r
    monkeypatch.setattr(m,'prepare_repaired_component_runtime_bundle',publish)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)
    assert (out/'runtime/runtime_bundle.json').exists() and not (out/'repair_execution.json').exists()
    assert 'BUDGET_EXHAUSTED' in (out/'progress.jsonl').read_text()


def test_budget_cannot_turn_corrupt_evidence_into_fallback(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;original=m.audit_captured_mixed_gradients
    def corrupt(*a,**k):r=original(*a,**k);a[0].write_bytes(a[0].read_bytes()+b' ');clock[0]=20;return r
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',corrupt)
    with pytest.raises(ValueError,match='reference changed'):
        m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)
    assert not (out/'runtime').exists()


def test_noop_stays_unqualified_with_budget(timed):
    (m,b,sdk,out,state,calls,o),clock=timed;state['steps']=False
    r=m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=1,**o)
    assert r['status']=='NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED'
    assert r['runtime'] is None and calls==['consumer']


def test_absent_total_budget_preserves_original_phase_limits(timed):
    (m,b,sdk,out,state,calls,o),clock=timed
    r=m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert r['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME' and r['total_timeout_seconds'] is None
    assert r['total_deadline']=='NOT_CONFIGURED'


def test_final_report_cannot_record_elapsed_time_past_its_allowance(timed, monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed; original=m.resolve_runtime_bundle
    def resolve(*a,**k):
        result=original(*a,**k)
        moments=iter([19.9,20.1])
        monkeypatch.setattr(m,'monotonic',lambda:next(moments,20.1))
        return result
    monkeypatch.setattr(m,'resolve_runtime_bundle',resolve)
    with pytest.raises(TimeoutError):
        m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=20,**o)
    assert (out/'runtime/runtime_bundle.json').exists()
    assert not (out/'repair_execution.json').exists()


def test_outer_shrink_caps_each_native_job_without_changing_local_limit(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;cap=[20.];limits=[];native=m.inspect_native_bundle;gradient=m.audit_captured_mixed_gradients;attribution=m.audit_captured_linear_attribution
    def capture(*a,**k):
        limits.append(k['timeout_seconds']);r=native(*a,**{**k,'timeout_seconds':7});clock[0]+=1;cap[0]=5.;return r
    def derivative(*a,**k):
        limits.append(k['timeout_seconds']);return gradient(*a,**{**k,'timeout_seconds':11})
    def attribute(*a,**k):
        limits.append(k['timeout_seconds']);return attribution(*a,**{**k,'timeout_seconds':9})
    monkeypatch.setattr(m,'inspect_native_bundle',capture);monkeypatch.setattr(m,'audit_captured_mixed_gradients',derivative);monkeypatch.setattr(m,'audit_captured_linear_attribution',attribute)
    r=m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=30,_remaining_seconds=lambda:cap[0],**o)
    assert limits==[7,5,4,4,3,3] and r['total_timeout_seconds']==30 and r['elapsed_seconds']==3


@pytest.mark.parametrize('adapter',['prepare_linear_torsion_bundle','audit_captured_mixed_gradients','prepare_repaired_component_runtime_bundle'])
def test_outer_expiry_withholds_later_work_and_success(timed,monkeypatch,adapter):
    (m,b,sdk,out,state,calls,o),clock=timed;cap=[20.];original=getattr(m,adapter)
    def late(*a,**k):r=original(*a,**k);cap[0]=0.;return r
    monkeypatch.setattr(m,adapter,late)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,total_timeout_seconds=100,_remaining_seconds=lambda:cap[0],**o)
    assert not (out/'repair_execution.json').exists() and (out/'bundle').exists()
    if adapter=='prepare_repaired_component_runtime_bundle':assert (out/'runtime/runtime_bundle.json').exists()
    elif adapter=='prepare_linear_torsion_bundle':assert not any(c.startswith('native') for c in calls)
    else:assert 'native-001' not in calls


@pytest.mark.parametrize('boundary',['derivative','selection','publication'])
def test_no_repair_qualification_obeys_outer_deadline_and_retains_partials(timed,monkeypatch,boundary):
    import json
    (m,b,sdk,out,state,calls,o),clock=timed;state['steps']=False;cap=[20.]
    original=m.audit_captured_mixed_gradients
    def derivative(*a,**k):
        result=original(*a,**k)
        if boundary=='derivative':cap[0]=0.
        return result
    def selection(**kwargs):
        if boundary=='selection':cap[0]=0.
        return {'decision':{'selected':'verified_prepared_bundle'}}
    def publish(output,**kwargs):
        output.mkdir();(output/'runtime_bundle.json').write_text(json.dumps(selection(**kwargs)))
        if boundary=='publication':cap[0]=0.
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',derivative)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',selection)
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',publish)
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,
        qualify_no_repair=True,total_timeout_seconds=100,_remaining_seconds=lambda:cap[0],**o)
    assert not (out/'repair_execution.json').exists() and (out/'original-gradient').exists()
    assert (out/'runtime').exists()==(boundary=='publication')
    assert not (out/'attribution').exists()



def test_optional_failure_cannot_reset_expired_outer_allowance(timed,monkeypatch):
    (m,b,sdk,out,state,calls,o),clock=timed;cap=[20.];native=m.inspect_native_bundle
    def failed(*a,**k):
        value=native(*a,**k)
        if a[2].name=='001':value['execution']={'status':'TIMED_OUT','returncode':-15}
        return value
    def classify(*a):cap[0]=0.;return {'phase':'native-001','status':'KNOWN_STOPPED_NATIVE_FAILURE'}
    monkeypatch.setattr(m,'inspect_native_bundle',failed);monkeypatch.setattr(m,'inspect_prepared_native_failure',classify)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',lambda **k:{'decision':{'selected':'verified_prepared_bundle'}})
    with pytest.raises(TimeoutError):m.execute_prepared_dictionary_repair(b,sdk,out,optional_failure_policy=m.FALLBACK_POLICY_ID,
        total_timeout_seconds=100,_remaining_seconds=lambda:cap[0],**o)
    assert not (out/'runtime').exists() and not (out/'repair_execution.json').exists()
    assert (out/'native/001/unique-capture/native_receipt.json').exists()
