"""Final geometry must be observed after ownership closes, never from preflight."""
import pytest

from tests.test_cif_counted_refinement import case


def make(case, enabled):
    old=case.make()
    return case.module.PreparedCountedRefinement(expected_scope=old._scope,
        **old._options, capture_pair_geometry=enabled)


def test_final_capture_runs_after_writer_and_counted_close_once(case):
    from nasolve import cif_counted_geometry as capture
    c=case; record={'actual_final_state': 'fixture'}
    def observe(owner, **kwargs):
        assert owner.closed and not owner.active
        assert c.events==['enter','driver','writer','exit']
        c.events.append('observe')
        return record
    c.monkeypatch.setattr(capture,'capture_closed_pair_geometry',observe)
    phase=make(c,True)
    with phase:
        with pytest.raises(ValueError):phase.pair_geometry_capture()
        c.driver.run(c.objects)
        with pytest.raises(ValueError):phase.pair_geometry_capture()
    assert c.events==['enter','driver','writer','exit','observe']
    assert phase.pair_geometry_capture()==record
    phase.pair_geometry_capture()['actual_final_state']='changed'
    assert phase.pair_geometry_capture()==record
    assert phase.statistics()['pair_geometry_capture']==dict(status='CAPTURED',
        record_sha256=c.module.counted._digest(record))
    assert c.driver.run is c.original


def test_disabled_geometry_keeps_existing_lifetime(case):
    from nasolve import cif_counted_geometry as capture
    def forbidden(*args,**kwargs):raise AssertionError('unrequested observation')
    case.monkeypatch.setattr(capture,'capture_closed_pair_geometry',forbidden)
    phase=make(case,False)
    with phase:case.driver.run(case.objects)
    assert 'pair_geometry_capture' not in phase.statistics()
    with pytest.raises(ValueError):phase.pair_geometry_capture()


def test_failed_capture_preserves_closed_owner_and_original_exception(case):
    from nasolve import cif_counted_geometry as capture
    def fail(owner, **kwargs):
        assert owner.closed and not owner.active
        raise ValueError('changed actual native state')
    case.monkeypatch.setattr(capture,'capture_closed_pair_geometry',fail)
    phase=make(case,True)
    with pytest.raises(ValueError,match='changed actual native state'):
        with phase:case.driver.run(case.objects)
    assert phase.statistics()['status']=='FAILED'
    assert phase.statistics()['error']['message']=='changed actual native state'
    assert case.driver.run is case.original
    with pytest.raises(ValueError):phase.pair_geometry_capture()
    with pytest.raises(ValueError,match='reused'):phase.__enter__()


@pytest.mark.parametrize('invalid',[None,1,'true'])
def test_capture_choice_requires_a_boolean(case,invalid):
    with pytest.raises(ValueError):make(case,invalid)


def test_final_geometry_is_explicit_and_retains_written_model_lineage():
    from nasolve import refinement_counted as counted, refinement_parallelity as execution
    assert execution.POLICY_ID==execution.V3_POLICY_ID
    counted._require_policy_continuation({'policy_id':execution.V6_POLICY_ID},execution.V7_POLICY_ID)
    counted._require_policy_continuation({'policy_id':execution.V7_POLICY_ID},execution.V7_POLICY_ID)
    for policy in (execution.V5_POLICY_ID,execution.V6_POLICY_ID):
        with pytest.raises(ValueError):
            counted._require_policy_continuation({'policy_id':execution.V7_POLICY_ID},policy)


def test_final_geometry_without_explicit_counted_control_refuses_before_files(tmp_path):
    from nasolve.autorefine import execute_autorefine,AutoRefineError
    with pytest.raises(AutoRefineError,match='explicit counted control'):
        execute_autorefine(tmp_path/'absent',tmp_path/'refine',tmp_path/'dump',
            phenix_version='2.2.1-6174', counted_pair_geometry=True)
    assert not list(tmp_path.iterdir())


def test_historical_worker_payloads_remain_byte_identical():
    from hashlib import sha256
    from nasolve import refinement_parallelity as execution
    from nasolve.refinement_counted import _digest
    # Recorded from C390 before any runtime integration. Includes entry scripts,
    # native helpers and packaged profile, not merely declared source hashes.
    expected={
        execution.V3_POLICY_ID:'31638ab5d8f20f8279f59bcf4c9b937115b389d22c6622eaf17e47dc0aa406ac',
        execution.V4_POLICY_ID:'672da86fd7d137a5a86b6bb4a699e9e1a60c1f07da6561c92189ba20013638d5',
        execution.V5_POLICY_ID:'41f94489be909338bc5f393ba62379595e16d66df5100ee16489a2f7cf033ccf',
        execution.V6_POLICY_ID:'d136bd407dc655c03b95892918df2bb17a5685470bfacda775868deca8d0b7fe'}
    for policy,digest in expected.items():
        assert _digest({n:sha256(v).hexdigest() for n,v in execution._code(policy).items()})==digest


def test_new_capture_policy_is_explicit_in_saved_request(tmp_path):
    from nasolve import refinement_parallelity as execution
    from tests.test_refinement_counted import request_case
    run,reference,_=request_case(tmp_path,request_changes={'runtime_policy':execution.V7_POLICY_ID})
    record=execution.read_execution_request(run,reference,checkpoint='refine-001')
    assert record['policy_id']==execution.V7_POLICY_ID
    assert 'code/_nasolve_refinement/cif_counted_geometry.py' in record['code']
    assert len(record['code'])==25
    assert execution.POLICY_ID==execution.V3_POLICY_ID
