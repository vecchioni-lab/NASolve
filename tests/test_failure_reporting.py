"""Secondary diagnostic failures must not replace the original engine failure.

Scientific transports below are synthetic; process/request readers remain real.
Missing note support models the Python 3.10 boundary without claiming that host.
"""
from pathlib import Path

import pytest

from tests.test_cif_candidate_qualification_execution import case
from tests.test_cif_acquisition_attempt import setup as acquisition_setup
from tests.test_cif_repair_attempt import setup as repair_setup, inventory
from tests.test_cif_prepared_repair_execution import case as prepared_case
from tests.test_cif_complete_request import case as complete_case
from tests.test_cif_runtime_continuation import continuation


MODES = ('missing', 'disabled', 'broken', 'normal')


def primary_failure(mode, base=RuntimeError):
    class Primary(base):
        def __getattribute__(self, name):
            if name == 'add_note' and mode == 'missing':
                raise AttributeError('Python 3.10 has no exception notes')
            return super().__getattribute__(name)

        def add_note(self, note):
            if mode == 'broken':
                raise OSError('secondary note hook failed')
            self.recorded_notes.append(note)

    if mode == 'disabled':
        Primary.add_note = None
    error = Primary('ORIGINAL_ENGINE_FAILURE')
    error.recorded_notes = []
    return error


def raising(error):
    def fail(*args, **kwargs):
        raise error
    return fail


def assert_original(caught, original, mode, count=1):
    assert caught.value is original
    assert str(caught.value) == 'ORIGINAL_ENGINE_FAILURE'
    assert len(original.recorded_notes) == (count if mode == 'normal' else 0)


@pytest.mark.parametrize('mode', MODES)
def test_acquisition_seal_failure_preserves_primary(acquisition_setup, monkeypatch, mode):
    m, args, options, calls, generated = acquisition_setup
    original = primary_failure(mode, KeyboardInterrupt)
    before = args[0].read_bytes()
    monkeypatch.setattr(m, 'generate_source_candidate_attempt', raising(original))
    monkeypatch.setattr(m, '_seal', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.acquire_dictionary_attempt(*args, **options)
    assert_original(caught, original, mode)
    root = args[-1]
    saved = inventory(root)
    state = m.inspect_acquisition_request(root)
    assert state['availability'] == 'BLOCKED' and not state['retry_authorized']
    assert inventory(root) == saved and args[0].read_bytes() == before
    assert not (root/'attempts/attempt-0001/finished.json').exists()
    assert not generated and not calls


@pytest.mark.parametrize('mode', MODES)
def test_repair_attempt_seal_failure_preserves_primary(repair_setup, monkeypatch, mode):
    m, args, options, calls = repair_setup
    original = primary_failure(mode, KeyboardInterrupt)
    before = inventory(args[0])
    monkeypatch.setattr(m, 'execute_prepared_dictionary_repair', raising(original))
    monkeypatch.setattr(m, '_seal', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.execute_prepared_dictionary_repair_attempt(*args, **options)
    assert_original(caught, original, mode)
    root = args[-1]
    saved = inventory(root)
    state = m.inspect_prepared_repair_request(root)
    assert state['availability'] == 'BLOCKED' and not state['retry_authorized']
    assert inventory(root) == saved and inventory(args[0]) == before
    assert not (root/'attempts/attempt-0001/finished.json').exists() and not calls


@pytest.mark.parametrize('mode', MODES)
def test_qualification_seal_failure_preserves_primary(case, monkeypatch, mode):
    m, args, calls, native = case
    original = primary_failure(mode, KeyboardInterrupt)
    monkeypatch.setattr(m, 'inspect_native_bundle', raising(original))
    monkeypatch.setattr(m.CandidateQualificationProcesses, 'finish', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.execute_candidate_qualification(*args)
    assert_original(caught, original, mode)
    assert (args[-1]/'inputs/protocol.json').exists()
    assert not (args[-1]/m.REPORT).exists()
    assert not (args[-1]/'ownership/finished.json').exists() and not calls


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('budget', (False, True))
def test_prepared_seal_failure_preserves_primary_and_budget(prepared_case, monkeypatch, mode, budget):
    m, bundle, sdk, out, state, calls, options = prepared_case
    original = primary_failure(mode, m.PreparedRepairBudgetExceeded if budget else KeyboardInterrupt)
    before = inventory(bundle)
    monkeypatch.setattr(m, 'inspect_native_bundle', raising(original))
    monkeypatch.setattr(m.PreparedRepairProcesses, 'finish', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.execute_prepared_dictionary_repair(bundle, sdk, out, **options)
    assert_original(caught, original, mode)
    assert inventory(bundle) == before and inventory(out/'bundle')
    assert not (out/'runtime').exists() and not (out/'ownership/finished.json').exists()
    label = 'BUDGET_EXHAUSTED' if budget else 'EXCEPTION'
    assert label in (out/'progress.jsonl').read_text()


@pytest.mark.parametrize('mode', ('missing', 'normal'))
@pytest.mark.parametrize('budget', (False, True))
@pytest.mark.parametrize('seal_fails', (False, True))
def test_progress_write_failure_preserves_primary(prepared_case, monkeypatch, mode, budget, seal_fails):
    m, bundle, sdk, out, state, calls, options = prepared_case
    original = primary_failure(mode, m.PreparedRepairBudgetExceeded if budget else KeyboardInterrupt)
    encode = m._bytes
    def failed_event(value):
        if value.get('state', '').startswith(('BUDGET_EXHAUSTED', 'EXCEPTION')):
            raise OSError('failure progress could not be written')
        return encode(value)
    monkeypatch.setattr(m, '_bytes', failed_event)
    monkeypatch.setattr(m, 'inspect_native_bundle', raising(original))
    if seal_fails:
        monkeypatch.setattr(m.PreparedRepairProcesses, 'finish', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.execute_prepared_dictionary_repair(bundle, sdk, out, **options)
    assert_original(caught, original, mode, 2 if seal_fails else 1)
    assert (out/'ownership/finished.json').exists() is not seal_fails
    assert not (out/'runtime').exists() and not (out/'repair_execution.json').exists()
    assert (out/'progress.jsonl').read_bytes() and inventory(out/'bundle')


@pytest.mark.parametrize('mode', MODES)
def test_complete_request_preserves_primary_with_unresolved_child(complete_case, monkeypatch, mode):
    m, args, root, sdk, store, generations, calls = complete_case
    m.initialize_dictionary_request(output=root, **args)
    original = primary_failure(mode, KeyboardInterrupt)
    def partial(*args, **kwargs):
        args[3].mkdir(parents=True)
        raise original
    monkeypatch.setattr(m.acquisition, 'acquire_dictionary_attempt', partial)
    with pytest.raises(type(original)) as caught:
        m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert_original(caught, original, mode)
    saved = inventory(root)
    state = m.inspect_dictionary_request(root)
    assert state['availability'] == 'BLOCKED' and not state['retry_authorized']
    assert inventory(root) == saved and not calls
    assert not (root/'attempts/attempt-0001/result.json').exists()


@pytest.mark.parametrize('mode', MODES)
def test_continuation_seal_failure_preserves_primary(continuation, monkeypatch, mode):
    m, parent, sdk, out, state = continuation
    original = primary_failure(mode, KeyboardInterrupt)
    before = inventory(parent)
    monkeypatch.setattr(m, 'inspect_native_bundle', raising(original))
    monkeypatch.setattr(m.RuntimeContinuationProcesses, 'finish', raising(OSError('seal failed')))
    with pytest.raises(type(original)) as caught:
        m.execute_runtime_continuation(parent, sdk, out)
    assert_original(caught, original, mode)
    assert inventory(parent) == before and inventory(out/'inputs/runtime')
    assert not (out/'runtime').exists() and not (out/'continuation_execution.json').exists()
    assert not (out/'ownership/finished.json').exists() and not state['calls']


@pytest.mark.parametrize('mode', MODES)
def test_fixture_report_failure_preserves_primary(tmp_path, monkeypatch, mode):
    from nasolve import cif_mixed_pair_fixture as m
    from tests.test_cif_mixed_pair_fixture import artificial_sources, ASSETS
    artificial_sources(tmp_path, monkeypatch)
    original = primary_failure(mode)
    monkeypatch.setattr('nasolve.postmr._run_coot', raising(original))
    write = m._write_json
    def fail_report(path, value):
        if Path(path).name == 'mixed_pair_fixture.json':
            raise OSError('fixture report failed')
        return write(path, value)
    monkeypatch.setattr(m, '_write_json', fail_report)
    out = tmp_path/'fixture'
    with pytest.raises(type(original)) as caught:
        m.run_mixed_pair_fixture(*ASSETS, Path('/synthetic/phenix.ready_set'), out,
                                coot_executable=Path('/synthetic/coot'))
    assert_original(caught, original, mode)
    assert original.fixture_reporting_error == {'error_type':'OSError', 'error':'fixture report failed'}
    assert (out/'inputs/template.pdb').read_bytes() == ASSETS[0].read_bytes()
    assert not (out/'mixed_pair_fixture.json').exists()


def test_note_lookup_and_secondary_formatting_are_best_effort():
    from nasolve.failure_reporting import add_failure_note
    class BadLookup(RuntimeError):
        def __getattribute__(self, name):
            if name == 'add_note':
                raise OSError('note lookup failed')
            return super().__getattribute__(name)
    class BadMessage(RuntimeError):
        def __str__(self):
            raise ValueError('message formatting failed')
    add_failure_note(BadLookup('primary'), 'secondary', RuntimeError('detail'))
    primary = primary_failure('normal')
    add_failure_note(primary, 'secondary', BadMessage())
    assert not primary.recorded_notes


def test_note_helper_does_not_swallow_a_new_interrupt():
    from nasolve.failure_reporting import add_failure_note
    new_interrupt = KeyboardInterrupt('new interruption while recording a note')
    class Interrupted(RuntimeError):
        add_note = staticmethod(raising(new_interrupt))
    with pytest.raises(KeyboardInterrupt) as caught:
        add_failure_note(Interrupted('primary'), 'secondary', RuntimeError('detail'))
    assert caught.value is new_interrupt


def test_builtin_exception_note_is_retained_when_available():
    from nasolve.failure_reporting import add_failure_note
    original = ValueError('primary')
    add_failure_note(original, 'Cleanup failed', OSError('disk unavailable'))
    if callable(getattr(original, 'add_note', None)):
        assert original.__notes__ == ['Cleanup failed: disk unavailable']
