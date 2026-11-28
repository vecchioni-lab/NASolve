"""The longer control is explicit; old requests retain their qualified bounds."""
import hashlib
import json
from unittest.mock import patch
import pytest

from nasolve import cif_counted_refinement as lifetime
from nasolve import refinement_counted as counted
from tests.test_cif_counted_refinement import prepared_objects
from tests.test_cif_counted_refinement import case
from nasolve import refinement_parallelity as execution

LONG_SCOPE = 'prepared-counted-refinement-cycle-v2'
LONG_PROTOCOL = 'counted-xyz-fixed-unit-100-v1'
LONG_RUNTIME = 'round-local-counted-execution-v8'


def test_long_scope_requires_explicit_policy_at_actual_native_parameters():
    objects = prepared_objects()
    objects.params.main.max_number_of_iterations = 100
    objects.params.main.random_seed = 1
    with pytest.raises(ValueError):
        lifetime.refinement_scope(objects)
    scope = lifetime.refinement_scope(objects, scope_policy=LONG_SCOPE)
    assert scope['iterations'] == 100 and scope['policy_id'] == LONG_SCOPE
    counted._scope(scope, runtime_policy=LONG_RUNTIME)
    with pytest.raises(ValueError):
        counted._scope(scope)


def test_long_control_admission_is_explicit_and_does_not_override_settings():
    options = dict(enabled=True, macro_cycles=1, processor_count=1,
        real_space_sites=False, adp_mode='none', refine_occupancies=False,
        anomalous_mode='off', refine_coordinates=True)
    counted.validate_autorefine_control(LONG_PROTOCOL,
        {'recipe': 'recipe.json', 'source_model': 'model.pdb'}, **options)
    with pytest.raises(ValueError):
        counted.validate_autorefine_control(LONG_PROTOCOL,
            {'recipe': 'recipe.json', 'source_model': 'model.pdb'},
            **dict(options, macro_cycles=2))


@pytest.mark.parametrize('cap', [1, 10, 11, 99])
def test_long_scope_refuses_a_different_configured_cap(cap):
    objects = prepared_objects()
    objects.params.main.max_number_of_iterations = cap
    objects.params.main.random_seed = 1
    with pytest.raises(ValueError):
        lifetime.refinement_scope(objects, scope_policy=LONG_SCOPE)


@pytest.mark.parametrize('key,value', [
    ('max_number_of_iterations', 0), ('max_number_of_iterations', 101),
    ('max_number_of_iterations', True), ('max_number_of_iterations', 100.0),
    ('random_seed', 2), ('random_seed', True), ('nproc', 2),
    ('number_of_macro_cycles', 2), ('bulk_solvent_and_scale', True),
])
def test_long_scope_retains_numerical_and_type_boundaries(key, value):
    objects = prepared_objects()
    objects.params.main.max_number_of_iterations = 100
    objects.params.main.random_seed = 1
    setattr(objects.params.main, key, value)
    with pytest.raises(ValueError):
        lifetime.refinement_scope(objects, scope_policy=LONG_SCOPE)


def test_old_scope_keeps_seed_semantics_and_cannot_be_relabelled_as_long():
    scope = lifetime.refinement_scope(prepared_objects())
    assert scope['seed'] == 2679941
    counted._scope(scope)
    with pytest.raises(ValueError):
        counted._scope(scope, runtime_policy=LONG_RUNTIME)
    scope.update(policy_id=LONG_SCOPE, iterations=100, seed=1)
    with pytest.raises(ValueError):
        counted._scope(scope, runtime_policy=execution.V7_POLICY_ID)


def test_v7_payload_is_exactly_the_pre_patch_worker():
    # Independent digest recorded from clean Cedar 653587b9 before edits.
    expected = 'be26e75096c8a15f37dbad03e64cdfec31a61c50c23c4c76c039d2514a4e2346'
    assert counted._digest({n:hashlib.sha256(v).hexdigest()
        for n,v in execution._code(execution.V7_POLICY_ID).items()}) == expected
    assert execution._code(execution.V8_POLICY_ID) != execution._code(execution.V7_POLICY_ID)


def test_long_preflight_admission_is_bound_to_request_and_survives_relocation(tmp_path):
    from tests.test_refinement_counted import observed_case
    run, reference, root, _ = observed_case(tmp_path, policy=execution.V8_POLICY_ID)
    path = root/'preflight/counted.json'
    original = path.read_bytes()
    wrong = json.loads(original)
    wrong['scope'].update(policy_id='prepared-counted-refinement-cycle-v1', iterations=10)
    path.write_text(json.dumps(wrong))
    with pytest.raises(ValueError, match='scope'):
        counted.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    assert not (root/'admission.json').exists()
    path.write_bytes(original)
    admission = counted.seal_admission(run,reference,checkpoint='refine-001',preflight_returncode=0)
    snapshot = {p.relative_to(run):(p.read_bytes(),p.stat().st_mtime_ns)
        for p in run.rglob('*') if p.is_file()}
    moved = run.with_name('relocated'); run.rename(moved)
    assert not run.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('cold read')):
        result = counted.read_admission(moved,reference,admission,checkpoint='refine-001')
    assert result['scope']['iterations'] == 100
    assert snapshot == {p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns)
        for p in moved.rglob('*') if p.is_file()}


def test_long_descendants_retain_writer_capture_and_scope():
    for parent in (execution.V6_POLICY_ID, execution.V7_POLICY_ID, execution.V8_POLICY_ID):
        counted._require_policy_continuation({'policy_id':parent},execution.V8_POLICY_ID)
    for policy in (execution.V5_POLICY_ID, execution.V6_POLICY_ID, execution.V7_POLICY_ID):
        with pytest.raises(ValueError):
            counted._require_policy_continuation({'policy_id':execution.V8_POLICY_ID},policy)


def test_long_control_requires_capture_before_files_or_processes(tmp_path):
    from nasolve.autorefine import execute_autorefine, AutoRefineError
    with patch('subprocess.Popen',side_effect=AssertionError('no process')):
        with pytest.raises(AutoRefineError,match='requires final pair'):
            execute_autorefine(tmp_path/'absent',tmp_path/'refine',tmp_path/'dump',
                phenix_version='2.2.1-6174',counted_protocol=LONG_PROTOCOL)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('defect', [None, 'before_driver', 'after_driver', 'missing_capture'])
def test_actual_long_driver_requires_the_admitted_scope_and_final_capture(case, defect):
    from nasolve import cif_counted_geometry
    c = case
    old = c.make()
    c.objects.params.main.max_number_of_iterations = 100
    c.objects.params.main.random_seed = 1
    scope = lifetime.refinement_scope(c.objects, scope_policy=LONG_SCOPE)
    captured = []
    def capture(owner, **kwargs):
        assert owner.closed and c.events[-1] == 'exit'
        captured.append(True)
        return {'fixture':'final'}
    c.monkeypatch.setattr(cif_counted_geometry,'capture_closed_pair_geometry',capture)
    if defect == 'after_driver':
        def changed(refinement_objects, dry_run=False, call_back_handler=None):
            result = c.original(refinement_objects,dry_run=dry_run,call_back_handler=call_back_handler)
            result.params.main.max_number_of_iterations = 99
            return result
        c.driver.run = changed
    if defect == 'missing_capture':
        with pytest.raises(ValueError,match='requires final pair'):
            lifetime.PreparedCountedRefinement(expected_scope=scope,**old._options,
                scope_policy=LONG_SCOPE)
        return
    owner = lifetime.PreparedCountedRefinement(expected_scope=scope,**old._options,
        capture_pair_geometry=True,scope_policy=LONG_SCOPE)
    original_driver = c.driver.run
    if defect == 'before_driver':
        c.objects.params.main.max_number_of_iterations = 99
    if defect:
        with pytest.raises(ValueError):
            with owner: c.driver.run(c.objects)
        assert not captured and owner.statistics()['status']=='FAILED'
    else:
        with owner: c.driver.run(c.objects)
        assert owner.statistics()['policy_id']==LONG_SCOPE and captured==[True]
        assert owner.pair_geometry_capture()=={'fixture':'final'}
    assert c.driver.run is original_driver


def test_ordinary_long_control_emits_and_records_the_same_cap(tmp_path,monkeypatch):
    from tests.test_autorefine_counted import completed_control
    calls = []
    # Synthetic native envelope: the actual capture reader is independently
    # exercised by test_refinement_pair_geometry; here require its dispatch.
    monkeypatch.setattr('nasolve.refinement_pair_geometry.seal_pair_geometry',
        lambda *args: calls.append('seal') or {'fixture':True})
    monkeypatch.setattr('nasolve.refinement_pair_geometry.read_pair_geometry',
        lambda *args: calls.append('read') or {'fixture':True})
    monkeypatch.setattr('nasolve.refinement_pair_geometry.summary',
        lambda value: {'status':'FIXTURE_ONLY'})
    run,result,registry,child,phases = completed_control(tmp_path,monkeypatch,longer=True)
    assert phases == ['preflight','refine'] and calls.count('seal') == 1 and 'read' in calls
    assert registry['current'] == 'postmr' and child['status'] == 'REVIEW'
    report = json.loads(result.report_path.read_text())
    assert report['refinement']['max_iterations'] == 100
    assert report['refinement']['counted_protocol'] == LONG_PROTOCOL
    params = (result.round_directory/'autorefine.params').read_text()
    assert 'max_number_of_iterations = 100' in params
    record = execution.validate_execution(run,child['outputs']['parallelity_execution'],
        checkpoint=child['id'],parent=child['parent'],usable=True)
    assert record['policy_id'] == LONG_RUNTIME
