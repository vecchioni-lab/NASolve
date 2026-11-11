"""Request ownership controls use synthetic workers, not chemical qualification."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import subprocess
import time

import pytest

from nasolve.campaign_records import read_record, write_record
from nasolve.campaigns import CampaignError
from nasolve.campaign_process import CampaignProcessError, current_process_identity
from nasolve.cif_generation_process import run_generation_command

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Owned generation requires POSIX')


def inventory(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    import nasolve.cif_generation_attempt as module
    sdk = tmp_path/'sdk'; sdk.mkdir()
    for name in ('python', 'elbow', 'api.py'):
        (sdk/name).write_text(name)
    source = tmp_path/'source.cif'; source.write_text('EXACT SYNTHETIC SOURCE\n')
    pin = {'anchor': 'phenix_installation', 'path': 'api.py',
           'sha256': sha256((sdk/'api.py').read_bytes()).hexdigest(), 'size': 6}
    kwargs = dict(environment=dict(os.environ), expected_dialect='CHEMICAL_COMPONENTS_CIF',
                  prior_sources=[pin], phenix_version='SYNTHETIC', single_block_steps=12,
                  timeout_seconds=5, max_attempts=2)
    calls = []
    original_source = source.read_bytes()

    def generator(root, python, elbow, api, frozen, code, output, **options):
        output.mkdir(parents=True)
        assert frozen.read_bytes() == original_source
        calls.append(output)
        run_generation_command([sys.executable, '-c', "from pathlib import Path; Path('partial.cif').write_text('kept')"],
            output, phase='candidate', environment=dict(os.environ), timeout_seconds=4,
            context={'component': code, 'source_sha256': sha256(frozen.read_bytes()).hexdigest(), 'attempt_owner': options['attempt_identity'],
                     **({'multiple_planes':True,'candidate_policy_id':'cif-source-native-multiple-plane-candidate-v1'}
                        if options.get('multiple_planes') else {})})
        result = {'status': 'FAILED', 'automatic_adoption': False}
        (output/'source_candidate_receipt.json').write_text(json.dumps(result))
        return result

    monkeypatch.setattr(module, 'generate_source_candidate', generator)
    args = (sdk, sdk/'python', sdk/'elbow', [pin], source, 'Q17', tmp_path/'request')
    return module, args, kwargs, calls


def test_attempts_preserve_previous_outputs_and_enforce_frozen_allowance(setup):
    module, args, kwargs, calls = setup
    first = module.generate_source_candidate_attempt(*args, **kwargs)
    root = args[-1]; previous = inventory(root/'attempts/attempt-0001')
    assert first['attempt_number'] == 1 and first['generation']['status'] == 'FAILED'
    assert first['generation_directory'] == {'anchor': 'request_directory', 'path': 'attempts/attempt-0001/generation'}
    second = module.generate_source_candidate_attempt(*args, **kwargs)
    assert second['attempt_number'] == 2 and second['attempt_id'] != first['attempt_id']
    assert first['request_id'] == second['request_id']
    assert inventory(root/'attempts/attempt-0001') == previous
    before = inventory(root)
    with pytest.raises(CampaignProcessError, match='exhausted'):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert len(calls) == 2 and inventory(root) == before
    state = module.inspect_source_generation_request(root)
    assert state['availability'] == 'EXHAUSTED' and not state['retry_authorized']


@pytest.mark.parametrize('field', ['source', 'component', 'steps', 'timeout', 'allowance', 'version', 'dispatcher', 'pin'])
def test_changed_request_cannot_reuse_identity_or_relax_budget(setup, field):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    args = list(args); kwargs = dict(kwargs); before = inventory(args[-1])
    if field == 'source': args[4].write_text('DIFFERENT SOURCE')
    elif field == 'component': args[5] = 'Q18'
    elif field == 'steps': kwargs['single_block_steps'] = 13
    elif field == 'timeout': kwargs['timeout_seconds'] = 6
    elif field == 'allowance': kwargs['max_attempts'] = 3
    elif field == 'version': kwargs['phenix_version'] = 'OTHER'
    elif field == 'dispatcher': args[1].write_text('changed dispatcher')
    elif field == 'pin':
        p = args[0]/'api.py'; p.write_text('changed source')
        pin = dict(args[3][0], sha256=sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
        args[3] = [pin]; kwargs['prior_sources'] = [pin]
    with pytest.raises(ValueError, match='request'):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert len(calls) == 1 and inventory(args[-1]) == before


def test_lock_blocks_other_outputs_until_whole_call_returns(setup, monkeypatch):
    module, args, kwargs, calls = setup
    original = module.generate_source_candidate
    def overlap(*a, **k):
        # The native phase may be stopped while this coordinator still owns the call.
        result = original(*a, **k)
        before = inventory(args[-1])
        with pytest.raises(CampaignProcessError, match='lock busy'):
            module.generate_source_candidate_attempt(*args, **kwargs)
        assert inventory(args[-1]) == before
        return result
    monkeypatch.setattr(module, 'generate_source_candidate', overlap)
    module.generate_source_candidate_attempt(*args, **kwargs)
    assert len(calls) == 1


@pytest.mark.parametrize('alive', [True, None, False])
def test_unsealed_attempt_requires_dead_coordinator_even_when_worker_stopped(setup, monkeypatch, alive):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    (args[-1]/'attempts/attempt-0001/finished.json').unlink()  # fault injection only
    monkeypatch.setattr(module, 'coordinator_alive', lambda identity: alive)
    before = inventory(args[-1])
    state = module.inspect_source_generation_request(args[-1])
    assert state['availability'] == ('AVAILABLE' if alive is False else 'BLOCKED')
    assert inventory(args[-1]) == before
    if alive is False:
        module.generate_source_candidate_attempt(*args, **kwargs)
        assert len(calls) == 2 and not (args[-1]/'attempts/attempt-0001/finished.json').exists()
    else:
        with pytest.raises(CampaignProcessError, match='unresolved'):
            module.generate_source_candidate_attempt(*args, **kwargs)
        assert len(calls) == 1 and inventory(args[-1]) == before


@pytest.mark.parametrize('gap', ['attempt', 'job', 'process'])
def test_unpublished_ownership_remains_blocked_after_dead_coordinator(setup, monkeypatch, gap):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    attempt = args[-1]/'attempts/attempt-0001'
    (attempt/'finished.json').unlink()
    phase = attempt/'generation/execution/candidate'
    if gap == 'attempt':
        # Model the mkdir-before-intent gap without impossible later evidence.
        import shutil
        shutil.rmtree(attempt/'generation'); (attempt/'attempt.json').unlink()
    else:
        (phase/'finished.json').unlink(); (phase/'process.json').unlink()
        if gap == 'job': (phase/'job.json').unlink()
    monkeypatch.setattr(module, 'coordinator_alive', lambda identity: False)
    before = inventory(args[-1])
    assert module.inspect_source_generation_request(args[-1])['availability'] == 'BLOCKED'
    with pytest.raises(CampaignProcessError, match='unresolved'):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert len(calls) == 1 and inventory(args[-1]) == before


@pytest.mark.parametrize('alive', [True, None, False])
def test_dead_coordinator_cannot_outrun_unsealed_worker(setup, monkeypatch, alive):
    import nasolve.cif_generation_process as process
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    attempt = args[-1]/'attempts/attempt-0001'
    (attempt/'finished.json').unlink()
    (attempt/'generation/execution/candidate/finished.json').unlink()
    monkeypatch.setattr(module, 'coordinator_alive', lambda identity: False)
    monkeypatch.setattr(process, 'process_alive', lambda identity: alive)
    before = inventory(args[-1])
    state = module.inspect_source_generation_request(args[-1])
    assert state['attempts'][0]['activity'] is alive
    assert state['availability'] == ('AVAILABLE' if alive is False else 'BLOCKED')
    assert inventory(args[-1]) == before


@pytest.mark.parametrize('failure', ['before_output', 'after_worker'])
def test_exception_closes_only_owned_call_and_preserves_partial_files(setup, monkeypatch, failure):
    module, args, kwargs, calls = setup
    original = module.generate_source_candidate
    def interrupted(*a, **k):
        if failure == 'after_worker': original(*a, **k)
        raise KeyboardInterrupt('injected between native phases')
    monkeypatch.setattr(module, 'generate_source_candidate', interrupted)
    with pytest.raises(KeyboardInterrupt): module.generate_source_candidate_attempt(*args, **kwargs)
    state = module.inspect_source_generation_request(args[-1])
    assert state['availability'] == 'AVAILABLE' and state['attempts'][0]['state'] == 'STOPPED'
    assert state['attempts'][0]['finished']['outcome'] == 'RAISED'
    if failure == 'after_worker': assert (args[-1]/'attempts/attempt-0001/generation/partial.cif').read_text() == 'kept'


@pytest.mark.parametrize('damage', ['source', 'receipt', 'phase_binding', 'foreign_phase', 'unknown_phase', 'symlink', 'gap', 'unknown_policy'])
def test_corruption_or_mixed_records_never_authorize_attempt(setup, monkeypatch, damage):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    root = args[-1]; attempt = root/'attempts/attempt-0001'; phase = attempt/'generation/execution/candidate'
    if damage == 'source': (root/'inputs/source.cif').write_text('changed')
    elif damage == 'receipt': (attempt/'generation/source_candidate_receipt.json').write_text('{}')
    elif damage == 'phase_binding':
        p = phase/'finished.json'; value = read_record(p); value['error_type'] = 'changed'
        write_record(p, value, replace=True)
    elif damage == 'foreign_phase':
        p = phase/'job.json'; value = read_record(p); value['context']['source_sha256'] = 'a'*64
        write_record(p, value, replace=True)
    elif damage == 'unknown_phase': (attempt/'generation/execution/unowned').mkdir()
    elif damage == 'symlink':
        p = root/'inputs/source.cif'; p.unlink(); p.symlink_to(args[4])
    elif damage == 'gap': attempt.rename(root/'attempts/attempt-0002')
    else:
        p = root/'request.json'; value = read_record(p); value['policy_id'] = 'unknown'
        write_record(p, value, replace=True)
    before = inventory(root)
    with pytest.raises((ValueError, CampaignError)):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert len(calls) == 1 and inventory(root) == before


def test_inspection_never_creates_a_request_or_lock(setup):
    module, args, kwargs, calls = setup
    root = args[-1]
    assert module.inspect_source_generation_request(root)['state'] == 'NOT_RECORDED'
    assert not root.exists()
    root.mkdir()
    assert module.inspect_source_generation_request(root)['state'] == 'UNKNOWN'
    assert list(root.iterdir()) == []


@pytest.mark.parametrize('multiple_planes',[False,True])
def test_sealed_readback_is_relocatable_and_needs_no_process_probe(setup, monkeypatch, tmp_path,multiple_planes):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs,multiple_planes=multiple_planes)
    relocated = tmp_path/'relocated'; args[-1].rename(relocated)
    def forbidden(*a, **k): raise AssertionError('sealed inspection must not query process state')
    monkeypatch.setattr(module, 'coordinator_alive', forbidden)
    monkeypatch.setattr('nasolve.cif_generation_process.process_alive', forbidden)
    before = inventory(relocated)
    assert module.inspect_source_generation_request(relocated)['attempts'][0]['state'] == 'STOPPED'
    assert inventory(relocated) == before and not args[-1].exists()


def test_relocated_input_path_and_capture_snapshot_names_keep_request_identity(setup):
    module, args, kwargs, calls = setup
    first = module.generate_source_candidate_attempt(*args, **kwargs)
    args = list(args); moved = args[4].with_name('moved.cif'); args[4].rename(moved); args[4] = moved
    args[3] = [dict(row, snapshot='another-capture/api.py.txt') for row in args[3]]
    second = module.generate_source_candidate_attempt(*args, **kwargs)
    assert first['request_id'] == second['request_id']


@pytest.mark.parametrize('condition,expected', [('same',True), ('dead',False), ('reused',False), ('reboot',False), ('foreign',None), ('no_marker',None), ('permission',None)])
def test_coordinator_identity_is_not_worker_group_identity(monkeypatch, condition, expected):
    import nasolve.campaign_process as process
    identity = {'pid': 1234, 'pgid': 77, 'host': 'local', 'boot_id': 'boot', 'start_marker': 'test-start:one'}
    monkeypatch.setattr(process.platform, 'node', lambda: 'local')
    monkeypatch.setattr(process, '_boot_id', lambda: 'new-boot' if condition == 'reboot' else 'boot')
    monkeypatch.setattr(process, '_start_marker', lambda pid: 'test-start:two' if condition == 'reused' else None if condition == 'no_marker' else 'test-start:one')
    if condition == 'foreign': identity['host'] = 'elsewhere'
    def probe(pid, sig):
        assert pid == 1234 and sig == 0
        if condition == 'dead': raise ProcessLookupError()
        if condition == 'permission': raise PermissionError()
    monkeypatch.setattr(process.os, 'kill', probe)
    assert process.coordinator_alive(identity) is expected


@pytest.mark.skipif(sys.platform != 'darwin', reason='Actual Darwin start-identity control')
def test_timezone_change_cannot_make_live_coordinator_look_dead(monkeypatch):
    from nasolve.campaign_process import coordinator_alive
    monkeypatch.setenv('TZ', 'UTC')
    identity = current_process_identity()
    monkeypatch.setenv('TZ', 'Pacific/Honolulu')
    assert coordinator_alive(identity) is True


def test_old_locale_dependent_marker_cannot_prove_coordinator_death(monkeypatch):
    import nasolve.campaign_process as process
    identity = {'pid': 1234, 'host': 'local', 'boot_id': 'boot', 'start_marker': 'ps-lstart:old date'}
    monkeypatch.setattr(process.platform, 'node', lambda: 'local')
    monkeypatch.setattr(process, '_boot_id', lambda: 'boot')
    monkeypatch.setattr(process, '_start_marker', lambda pid: 'ps-lstart-utc:new date')
    monkeypatch.setattr(process.os, 'kill', lambda pid, sig: None)
    assert process.coordinator_alive(identity) is None


@pytest.mark.parametrize('stage', ['after_worker', 'during_worker'])
def test_actual_killed_coordinator_and_surviving_worker_recover_only_when_both_stopped(setup, tmp_path, stage):
    module, args, kwargs, calls = setup
    script = tmp_path/'coordinator.py'
    payload = tmp_path/'parameters.json'
    serial = [str(p) if isinstance(p, Path) else p for p in args]
    payload.write_text(json.dumps({'args': serial, 'kwargs': kwargs, 'stage': stage, 'control': str(tmp_path)}))
    script.write_text(r"""from pathlib import Path
import json, os, sys, time
from hashlib import sha256
import nasolve.cif_generation_attempt as module
from nasolve.cif_generation_process import run_generation_command
p = json.loads(Path(sys.argv[1]).read_text()); control = Path(p['control'])
def generator(root, python, elbow, api, source, code, output, **kwargs):
    output.mkdir(parents=True)
    worker = 'from pathlib import Path; import time; Path("partial.cif").write_text("retained"); '
    if p['stage'] == 'during_worker':
        worker += '\nend=time.monotonic()+8\nwhile not Path(' + repr(str(control/'release')) + ').exists() and time.monotonic()<end: time.sleep(.02)\n'
    run_generation_command([sys.executable, '-c', worker], output, phase='candidate',
        environment=dict(os.environ), timeout_seconds=10,
        context={'component': code, 'source_sha256': sha256(source.read_bytes()).hexdigest(), 'attempt_owner': kwargs['attempt_identity']})
    (control/'after-worker').write_text('coordinator still active')
    time.sleep(10)
module.generate_source_candidate = generator
module.generate_source_candidate_attempt(*p['args'], **p['kwargs'])
""")
    output = args[-1]/'attempts/attempt-0001/generation'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(Path(module.__file__).parents[1]))
    with (tmp_path/'coordinator.log').open('w') as log:
        owner = subprocess.Popen([sys.executable, str(script), str(payload)], env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            ready = tmp_path/'after-worker' if stage == 'after_worker' else output/'execution/candidate/process.json'
            end = time.monotonic()+5
            while not ready.exists() and owner.poll() is None and time.monotonic()<end:
                time.sleep(.02)
            assert ready.exists(), (tmp_path/'coordinator.log').read_text()
            assert module.inspect_source_generation_request(args[-1])['availability'] == 'BLOCKED'
            with pytest.raises(CampaignProcessError, match='lock busy'):
                module.generate_source_candidate_attempt(*args, **kwargs)
            # Only the test's live Popen handle is killed; saved identities never signal.
            owner.kill(); owner.wait(timeout=3)
            if stage == 'during_worker':
                assert module.inspect_source_generation_request(args[-1])['availability'] == 'BLOCKED'
            (tmp_path/'release').touch()  # Synthetic worker exits cooperatively, with a finite fallback deadline.
            end = time.monotonic()+5
            while module.inspect_source_generation_request(args[-1])['availability'] != 'AVAILABLE' and time.monotonic()<end:
                time.sleep(.02)
            assert module.inspect_source_generation_request(args[-1])['availability'] == 'AVAILABLE'
            before = inventory(args[-1]/'attempts/attempt-0001')
            result = module.generate_source_candidate_attempt(*args, **kwargs)
            assert result['attempt_number'] == 2 and len(calls) == 1
            assert inventory(args[-1]/'attempts/attempt-0001') == before
            assert not (args[-1]/'attempts/attempt-0001/finished.json').exists()
        finally:
            (tmp_path/'release').touch()
            if owner.poll() is None: owner.kill()
            owner.wait(timeout=3)


def test_completion_publication_failure_blocks_retry_until_coordinator_dead(setup, monkeypatch):
    module, args, kwargs, calls = setup
    original = module.write_record
    def publish(path, value, **options):
        if path.name == 'finished.json': raise OSError('injected completion write failure')
        return original(path, value, **options)
    monkeypatch.setattr(module, 'write_record', publish)
    with pytest.raises(OSError, match='injected'): module.generate_source_candidate_attempt(*args, **kwargs)
    assert module.inspect_source_generation_request(args[-1])['availability'] == 'BLOCKED'
    before = inventory(args[-1])
    with pytest.raises(CampaignProcessError, match='unresolved'):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert inventory(args[-1]) == before and len(calls) == 1


@pytest.mark.parametrize('option,value', [('max_attempts', 0), ('max_attempts', 6), ('max_attempts', True),
    ('timeout_seconds', float('nan')), ('timeout_seconds', 601), ('single_block_steps', 0)])
def test_invalid_budget_fails_before_reservation(setup, option, value):
    module, args, kwargs, calls = setup
    kwargs = dict(kwargs); kwargs[option] = value
    with pytest.raises(ValueError): module.generate_source_candidate_attempt(*args, **kwargs)
    assert not args[-1].exists() and not calls


@pytest.mark.parametrize('member', ['unrelated.txt', 'inputs', 'request.lock'])
def test_invalid_existing_request_refuses_without_creating_a_lock(setup, member):
    module, args, kwargs, calls = setup
    root = args[-1]; root.mkdir()
    if member == 'unrelated.txt': (root/member).write_text('belongs to user')
    else: (root/member).mkdir()
    before = inventory(root); names = sorted(p.name for p in root.iterdir())
    with pytest.raises((ValueError, CampaignError)):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert inventory(root) == before and sorted(p.name for p in root.iterdir()) == names
    assert not calls



def test_phase_records_copied_from_prior_attempt_cannot_prove_current_worker_stopped(setup, monkeypatch):
    import shutil
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    module.generate_source_candidate_attempt(*args, **kwargs)
    first = args[-1]/'attempts/attempt-0001/generation/execution/candidate'
    second = args[-1]/'attempts/attempt-0002'
    (second/'finished.json').unlink()
    for name in ('job.json', 'process.json', 'finished.json'):
        shutil.copyfile(first/name, second/'generation/execution/candidate'/name)
    monkeypatch.setattr(module, 'coordinator_alive', lambda identity: False)
    with pytest.raises((ValueError, CampaignError)):
        module.inspect_source_generation_request(args[-1])



@pytest.mark.parametrize('identity', [{}, {'attempt_id': 'not-an-id'},
    {'request_sha256': 'a'*64, 'attempt_sha256': 'b'*64, 'attempt_id': '00000000-0000-0000-0000-000000000000', 'extra': True}])
def test_malformed_attempt_identity_refuses_before_generator_preflight(tmp_path, identity):
    from nasolve.cif_source_candidate import generate_source_candidate
    with pytest.raises(ValueError, match='attempt identity'):
        generate_source_candidate(None, None, None, None, None, None, tmp_path/'out',
            environment={}, expected_dialect='unused', prior_sources=[], phenix_version='unused', attempt_identity=identity)
    assert not (tmp_path/'out').exists()



@pytest.mark.parametrize('outside', [False, True])
def test_native_pins_reuse_existing_installation_containment_rules(setup, outside):
    module, args, kwargs, calls = setup
    pin = args[0]/'api.py'
    target = args[0].parent/'external-api.py' if outside else args[0]/'internal-api.py'
    pin.rename(target); pin.symlink_to(target)
    if outside:
        with pytest.raises(ValueError, match='escapes'):
            module.generate_source_candidate_attempt(*args, **kwargs)
        assert not calls and not args[-1].exists()
    else:
        assert module.generate_source_candidate_attempt(*args, **kwargs)['attempt_number'] == 1
        assert len(calls) == 1



def test_completion_published_during_inspection_is_not_misreported_as_corruption(setup, monkeypatch):
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    finished = args[-1]/'attempts/attempt-0001/finished.json'
    saved = read_record(finished); finished.unlink()
    original = module._phase_evidence
    def crossing(*a, **k):
        states, bindings = original(*a, **k)
        # Read began before the last native phase/attempt was sealed.
        states['candidate'] = 'LIVE'
        write_record(finished, saved)
        return states, bindings
    monkeypatch.setattr(module, '_phase_evidence', crossing)
    first = module.inspect_source_generation_request(args[-1])
    assert first['availability'] == 'BLOCKED'
    monkeypatch.setattr(module, '_phase_evidence', original)
    assert module.inspect_source_generation_request(args[-1])['availability'] == 'AVAILABLE'



def test_phase_completion_published_during_inspection_is_conservative(setup, monkeypatch):
    from nasolve.cif_generation_process import inspect_generation_process
    module, args, kwargs, calls = setup
    module.generate_source_candidate_attempt(*args, **kwargs)
    work = args[-1]/'attempts/attempt-0001/generation'
    process = work/'execution/candidate/process.json'; finished = process.with_name('finished.json')
    owner, completion = read_record(process), read_record(finished)
    process.unlink(); finished.unlink()
    original = Path.exists; crossed = False
    def crossing(path):
        nonlocal crossed
        if path == process and not crossed:
            crossed = True
            write_record(process, owner); write_record(finished, completion)
            return False  # The identity observation preceded both publications.
        return original(path)
    monkeypatch.setattr(Path, 'exists', crossing)
    assert inspect_generation_process(work, 'candidate')['state'] == 'UNKNOWN'
    assert inspect_generation_process(work, 'candidate')['state'] == 'STOPPED'



def test_dot_segment_request_cannot_write_into_selected_installation(setup):
    module, args, kwargs, calls = setup
    args = list(args)
    sibling = args[0].parent/'sibling'; sibling.mkdir()
    args[-1] = sibling/'..'/args[0].name/'request'
    before = inventory(args[0])
    with pytest.raises(ValueError, match='separate'):
        module.generate_source_candidate_attempt(*args, **kwargs)
    assert inventory(args[0]) == before and not calls
    assert not (args[0]/'request').exists()


def test_multiple_plane_choice_binds_the_existing_immutable_request(setup):
    module,args,kwargs,calls=setup
    result=module.generate_source_candidate_attempt(*args,**kwargs,multiple_planes=True)
    state=module.inspect_source_generation_request(args[-1])
    assert state['request']['configuration']['recipe']['multiple_planes'] is True
    assert result['attempt_number']==1
    old=inventory(args[-1])
    with pytest.raises(ValueError,match='identity differs'):
        module.generate_source_candidate_attempt(*args,**kwargs)
    assert inventory(args[-1])==old and len(calls)==1


@pytest.mark.parametrize('value',[None,0,1,'true'])
def test_invalid_multiple_plane_choice_refuses_before_request_reservation(setup,value):
    module,args,kwargs,calls=setup
    with pytest.raises(ValueError):module.generate_source_candidate_attempt(*args,**kwargs,multiple_planes=value)
    assert not args[-1].exists() and not calls


def test_multiple_plane_attempt_cannot_seal_a_phase_that_drops_its_choice(setup,monkeypatch):
    module,args,kwargs,calls=setup
    original=module.generate_source_candidate
    def dropped(*args,**options):
        options.pop('multiple_planes')
        return original(*args,**options)
    monkeypatch.setattr(module,'generate_source_candidate',dropped)
    with pytest.raises(ValueError,match='multiple-plane authority'):
        module.generate_source_candidate_attempt(*args,**kwargs,multiple_planes=True)
    attempt=args[-1]/'attempts/attempt-0001'
    assert not (attempt/'finished.json').exists()
    from nasolve.cif_generation_process import inspect_generation_process
    assert inspect_generation_process(attempt/'generation','candidate')['state']=='STOPPED'
    with pytest.raises(ValueError,match='multiple-plane authority'):
        module.inspect_source_generation_request(args[-1])
