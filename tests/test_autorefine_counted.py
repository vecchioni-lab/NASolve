"""The ordinary owner must preserve explicitly requested counted refinement."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from nasolve.autorefine import AutoRefineError, execute_autorefine
from nasolve import refinement_counted as counted
from nasolve import refinement_parallelity as execution
from nasolve.checkpoints import read_registry
from tests.test_refinement_counted import registered_counted_case
from tests.test_autorefine import make_refine, make_mtz_dump

PROTOCOL = 'counted-xyz-fixed-unit-v1'


def case(tmp_path, *, policy=execution.V6_POLICY_ID):
    run, reference, _, _ = registered_counted_case(tmp_path, full_model=True, policy=policy)
    request = execution.read_execution_request(run, reference, checkpoint='refine-001')
    intent = request['counted_intent']
    tools = tmp_path / 'tools'; tools.mkdir()
    options = dict(phenix_version='2.2.1-6174', from_checkpoint='refine-001',
        macro_cycles=1, processor_count=1, real_space_sites=False, adp_mode='none',
        refine_occupancies=False, anomalous_mode='off',
        correct_native_parallelity=True, phenix_python_executable=Path(sys.executable),
        counted_protocol=PROTOCOL, counted_pair_request={
            'recipe': run / intent['original_recipe']['relative_path'],
            'source_model': run / intent['original_model']['relative_path']})
    return run, make_refine(tools), make_mtz_dump(tools, anomalous=False), options


@pytest.mark.parametrize('change', [
    {'macro_cycles': 5}, {'processor_count': None}, {'processor_count': 2},
    {'real_space_sites': True}, {'adp_mode': 'group'}, {'refine_occupancies': True},
    {'anomalous_mode': 'refine'}, {'refine_coordinates': False},
    {'correct_native_parallelity': False}, {'counted_protocol': 'unknown'},
    {'counted_protocol': None}, {'counted_pair_request': None},
])
def test_unqualified_counted_control_refuses_before_new_round_or_process(tmp_path, change):
    run, refine, dump, options = case(tmp_path)
    options.update(change)
    before = (run / 'AutoRefine/checkpoints.json').read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('must refuse before native work')):
        with pytest.raises(AutoRefineError, match='[Cc]ounted'):
            execute_autorefine(run, refine, dump, **options)
    assert not (run / 'AutoRefine/round_002').exists()
    assert (run / 'AutoRefine/checkpoints.json').read_bytes() == before


def test_changed_original_pair_intent_refuses_before_new_round(tmp_path):
    run, refine, dump, options = case(tmp_path)
    original = options['counted_pair_request']['recipe']
    packet = json.loads(original.read_text())
    replacement = run / 'changed-recipe.json'; replacement.write_text(json.dumps(packet, indent=2))
    options['counted_pair_request']['recipe'] = replacement
    with patch('subprocess.Popen', side_effect=AssertionError('must refuse before native work')):
        with pytest.raises(AutoRefineError):
            execute_autorefine(run, refine, dump, **options)
    assert not (run / 'AutoRefine/round_002').exists()
    assert read_registry(run)[1]['current'] == 'postmr'


def completed_control(tmp_path, monkeypatch, *, failure=None, initial=False, ancestor_policy=execution.V6_POLICY_ID, chemistry=None, extra=False, longer=False):
    """Synthetic native envelopes exercise owners, not chemical qualification."""
    import hashlib
    import subprocess
    from tests.test_refinement_counted import observed_case
    from tests.test_cif_refinement_runtime import output_row
    from nasolve.checkpoints import _file_reference
    run, refine, dump, options = case(tmp_path, policy=ancestor_policy)
    selected_policy = execution.V8_POLICY_ID if longer else execution.V6_POLICY_ID
    if longer:
        options.update(counted_protocol=counted.LONG_CONTROL_PROTOCOL,counted_pair_geometry=True)
    if initial:
        options['from_checkpoint'] = 'postmr'
    if extra:
        from nasolve.cif_native_monomers import FULL_MODEL_PHIL
        extra_path = run / 'new-restraints.phil'
        extra_path.write_text(FULL_MODEL_PHIL)
        options['extra_restraints'] = [extra_path, extra_path]
    if chemistry is not None:
        from tests.test_cif_triple_bond_audit import fixture
        directory = run / 'projection'; directory.mkdir()
        source, _ = fixture(directory)
        scope = [dict(site='A:1', component='Q17', projection=_file_reference(source, run))]
        monkeypatch.setattr('nasolve.refinement_chemistry.prepare_chemistry_scope', lambda *args: scope)
    def add_chemistry(result, model=None):
        if chemistry is None:
            return
        from tests.test_cif_refinement_sites import capture, SITES
        from nasolve.cif_refinement_sites import unavailable
        observation, labels = capture()
        if chemistry == 'unavailable':
            observation = unavailable(SITES, 'Synthetic observer unavailable')
        result.update(atom_labels=labels, chemistry_observation=observation,
                      chemistry_model=None, chemistry_binding_restored=True)
        if model is not None:
            row = output_row(len(labels))
            if chemistry != 'unavailable':
                row['hierarchy_after_sha256'] = observation['model_state_sha256']
                result['chemistry_model'] = {key: _file_reference(model, run)[key] for key in ('sha256', 'size')}
            result['output_synchronization'] = [row]
    original = subprocess.run
    commands = []
    temporary_views = []

    def consume(command, *args, **kwargs):
        if len(command) < 4 or not str(command[2]).endswith('/parallelity_runtime/entry.py'):
            return original(command, *args, **kwargs)
        assert not kwargs.get('start_new_session') and 'preexec_fn' not in kwargs
        root = Path(command[2]).parent
        request = json.loads((root / 'request.json').read_text())
        assert request['policy_id'] == selected_policy
        reference = _file_reference(root / 'request.json', run)
        checkpoint = request['checkpoint']
        phase = command[3]; commands.append(phase)
        if phase == 'preflight':
            assert not (root / 'admission.json').exists()
            observed_case(tmp_path, policy=selected_policy,
                          execution_case=(run, reference, command), checkpoint=checkpoint)
            if chemistry is not None:
                path = root / 'preflight/result.json'
                value = json.loads(path.read_text()); add_chemistry(value)
                path.write_text(json.dumps(value))
            if failure == 'refused':
                (root / 'preflight/counted.json').write_text(json.dumps({
                    'policy_id': counted.OBSERVATION_POLICY, 'status': 'REFUSED',
                    'error': {'type': 'ValueError', 'message': 'unqualified actual native scope'}}))
            if failure == 'preflight':
                return subprocess.CompletedProcess(command, 4)
            return subprocess.CompletedProcess(command, 0)
        assert phase == 'refine' and commands == ['preflight', 'refine']
        assert failure != 'refused'
        view = Path(command[6]); assert view.is_file(); temporary_views.append(view)
        admission = json.loads((root / 'admission.json').read_text())
        assert not (root / 'preflight/preparation-work').exists()
        (root / 'refinement-launch.json').write_text(json.dumps(dict(schema_version=1,
            checkpoint=checkpoint, request_sha256=reference['sha256'],
            admission_sha256=_file_reference(root / 'admission.json', run)['sha256'],
            pid=123, parent_pid=122, created_ns=1)))
        folder = root / 'refine'; folder.mkdir(); (folder / 'calls').mkdir()
        result = json.loads((root / 'preflight/result.json').read_text())
        result.update(arguments=request['command'][1:], dry_run=False, macro_cycles=1,
            atom_labels=['fixture-a', 'fixture-b'], output_synchronization=[output_row(2)])
        actual = original([str(refine), *request['command'][1:]], *args, **kwargs)
        assert actual.returncode == 0
        model = root.parent / 'refined_001.pdb'
        add_chemistry(result, model)
        result['written_model'] = dict(policy_id='native-written-model-v1',
            sha256=hashlib.sha256(model.read_bytes()).hexdigest(), size=model.stat().st_size,
            model_state_sha256=result['output_synchronization'][0]['hierarchy_after_sha256'])
        if failure == 'wrong_model':
            model.write_bytes(model.read_bytes() + b'REMARK substituted after native writer\n')
        if failure == 'refine':
            result.update(status='FAILED', error={'type': 'RuntimeError', 'message': 'native failure'})
        (folder / 'result.json').write_text(json.dumps(result))
        outcome = dict(policy_id=counted.OBSERVATION_POLICY,
            admission_record_sha256=admission['record_sha256'],
            prepared_sha256=admission['prepared_sha256'],
            compiled_binding_sha256=admission['compiled_binding_sha256'],
            provider_selection_sha256=admission['provider_selection_sha256'],
            scope_sha256=counted._digest(admission['scope']),
            recipe_sha256=request['counted_intent']['current_recipe_sha256'],
            lifetime=dict(policy_id=admission['scope']['policy_id'],
                status='FAILED' if failure == 'refine' else 'COMPLETE', binding_restored=True,
                driver_entries=1, owner=dict(closed=True, poisoned=failure == 'refine', successful_calls=1)))
        (folder / 'counted.json').write_text(json.dumps(outcome))
        return subprocess.CompletedProcess(command, 5 if failure == 'refine' else 0)

    monkeypatch.setattr('subprocess.run', consume)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns)
              for p in (run / 'AutoRefine/round_001').rglob('*') if p.is_file()}
    result = execute_autorefine(run, refine, dump, **options)
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == value for p, value in before.items())
    assert all(not p.exists() for p in temporary_views)
    _, registry = read_registry(run)
    child = next(p for p in registry['checkpoints'] if p['id'] == result.checkpoint_id)
    return run, result, registry, child, commands


@pytest.mark.parametrize('initial,ancestor_policy', [(True, execution.V6_POLICY_ID),
    (False, execution.V6_POLICY_ID), (False, execution.V5_POLICY_ID)])
def test_explicit_ordinary_control_uses_sealed_v6_and_stays_unselected_review(tmp_path, monkeypatch, initial, ancestor_policy):
    run, result, registry, child, commands = completed_control(tmp_path, monkeypatch,
        initial=initial, ancestor_policy=ancestor_policy)
    assert commands == ['preflight', 'refine']
    assert child['status'] == 'REVIEW' and child['usable'] is True
    assert result.status == 'AUTOREFINE_REVIEW' and registry['current'] == 'postmr'
    receipt = execution.validate_execution(run, child['outputs']['parallelity_execution'],
        checkpoint=child['id'], parent=child['parent'], usable=True)
    assert receipt['policy_id'] == execution.V6_POLICY_ID and receipt['counted_admission']
    report = json.loads(result.report_path.read_text())
    assert report['command'][3] == 'refine' and report['refinement']['target'] == 'ml'
    assert report['refinement']['weights']['optimize_xyz'] is False
    assert report['refinement']['weights']['fix_wxc'] == 1.0
    assert report['refinement']['counted_protocol'] == PROTOCOL
    assert report['selected_as_current'] is False
    params = (result.round_directory / 'autorefine.params').read_text()
    assert 'optimize_xyz_weight = False' in params and 'max_number_of_iterations = 10' in params
    request = execution.read_execution_request(run, receipt['request'], checkpoint=child['id'])
    assert 'main.target="ml"' in request['command'] and 'main.target="auto"' not in request['command']
    assert child['outputs']['refinement_inputs']
    assert 'xray_data.r_free_flags.generate=False' in request['command']


@pytest.mark.parametrize('failure', ['preflight', 'refused', 'refine'])
def test_counted_failures_preserve_existing_failed_checkpoint_and_original_evidence(tmp_path, monkeypatch, failure):
    run, result, registry, child, commands = completed_control(tmp_path, monkeypatch, failure=failure)
    assert child['status'] == 'FAILED' and child['usable'] is False
    assert registry['current'] == 'postmr'
    assert commands == (['preflight', 'refine'] if failure == 'refine' else ['preflight'])
    record = execution.validate_execution(run, child['outputs']['parallelity_execution'], checkpoint=child['id'])
    assert [p['returncode'] for p in record['phases']] == {
        'preflight': [4, None], 'refused': [0, None], 'refine': [0, 5]}[failure]
    if failure == 'refused':
        assert record['refinement_status'] == 'NOT_LAUNCHED'
        assert 'unqualified actual native scope' in record['admission_refusal']['error']['message']
        assert (result.round_directory / 'parallelity_runtime/preflight/preparation-work/prepared.json').exists()


def test_substituted_ordinary_output_cannot_be_published(tmp_path, monkeypatch):
    with pytest.raises(AutoRefineError, match='written'):
        completed_control(tmp_path, monkeypatch, failure='wrong_model')
    run = tmp_path / 'run'
    assert len(read_registry(run)[1]['checkpoints']) == 2
    assert (run / 'AutoRefine/round_002/refined_001.pdb').exists()


@pytest.mark.parametrize('scope', ['chemistry', 'extra', 'new_terminal'])
def test_unsupported_scientific_scope_is_not_dropped(tmp_path, monkeypatch, scope):
    run, refine, dump, options = case(tmp_path)
    if scope == 'chemistry':
        monkeypatch.setattr('nasolve.refinement_chemistry.prepare_chemistry_scope',
                            lambda *args: [{'site': 'A:1', 'component': 'Q17'}])
    elif scope == 'extra':
        from nasolve.autorefine import _file_reference
        # Declare a fixture-local repository even when pytest runs inside a checkout.
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "fixture"\n')
        (tmp_path / 'MR_frames').mkdir()
        p = tmp_path.parent / (tmp_path.name + '-external.phil')
        p.write_text('geometry_restraints {}\n')
        assert _file_reference(p, run)['anchor'] == 'absolute'
        options['extra_restraints'] = [p]
    else:
        monkeypatch.setattr('nasolve.autorefine.requested_op3_sites', lambda report: ('A:1',))
    with patch('subprocess.Popen', side_effect=AssertionError('no native work')):
        with pytest.raises(AutoRefineError, match='Counted'):
            execute_autorefine(run, refine, dump, **options)
    assert not (run / 'AutoRefine/round_002').exists()


@pytest.mark.parametrize('choice', [None, 'recipe'])
def test_working_frame_choice_is_explicit_and_recorded(tmp_path, monkeypatch, choice):
    from nasolve import autorefine
    original = autorefine.execute_autorefine
    def configured(*args, **kwargs):
        return original(*args, **kwargs, counted_frame=choice)
    monkeypatch.setitem(completed_control.__globals__, 'execute_autorefine', configured)
    run, result, _, _, _ = completed_control(tmp_path, monkeypatch)
    params = (result.round_directory / 'autorefine.params').read_text()
    report = json.loads(result.report_path.read_text())
    if choice == 'recipe':
        assert 'unit_cell = 40,40,60,90,90,90' in params
        assert 'space_group = "P 43"' in params
        assert report['refinement']['working_frame']['crystal']['cell_parameters'] == [40, 40, 60, 90, 90, 90]
    else:
        assert 'crystal_symmetry' not in params
        assert report['refinement']['working_frame'] == {'choice': 'native', 'crystal': None}


def test_unknown_frame_choice_refuses_before_allocation(tmp_path):
    run, refine, dump, options = case(tmp_path)
    with patch('subprocess.Popen', side_effect=AssertionError('no launch')):
        with pytest.raises(AutoRefineError, match='working frame'):
            execute_autorefine(run, refine, dump, **options, counted_frame='guess-model')
    assert not (run / 'AutoRefine/round_002').exists()


def test_command_context_refusal_does_not_claim_an_existing_launch_never_started(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from nasolve.checkpoints import _file_reference
    marker_bytes = b'{"external-process-provenance":"preserve"}\n'
    @contextmanager
    def refused(run, request, admission, *, checkpoint, python_executable):
        root = run / execution._root(checkpoint)
        marker = root / 'refinement-launch.json'
        marker.write_bytes(marker_bytes)
        raise ValueError('attempt already started')
        yield  # pragma: no cover
    monkeypatch.setattr(counted, 'refinement_command', refused)
    with pytest.raises(AutoRefineError, match='preserve the attempt'):
        completed_control(tmp_path, monkeypatch)
    run = tmp_path / 'run'; root = run / execution._root('refine-002')
    assert (root / 'refinement-launch.json').read_bytes() == marker_bytes
    assert (root / 'admission.json').is_file() and not (root / 'execution.json').exists()
    assert len(read_registry(run)[1]['checkpoints']) == 2


def test_current_experimental_phase_is_not_silently_omitted(tmp_path, monkeypatch):
    from types import SimpleNamespace
    run, refine, dump, options = case(tmp_path)
    phase = run / 'known-phases.mtz'; phase.write_bytes(b'phase fixture')
    monkeypatch.setattr('nasolve.autorefine._effective_phase', lambda *args: SimpleNamespace(path=phase))
    with patch('subprocess.Popen', side_effect=AssertionError('no native work')):
        with pytest.raises(AutoRefineError, match='experimental phases'):
            execute_autorefine(run, refine, dump, **options)
    assert not (run / 'AutoRefine/round_002').exists()


@pytest.mark.parametrize('chemistry', ['bent', 'unavailable'])
def test_counted_control_keeps_existing_actual_chemistry_report(tmp_path, monkeypatch, chemistry):
    run, result, registry, child, commands = completed_control(tmp_path, monkeypatch, chemistry=chemistry)
    assert commands == ['preflight', 'refine']
    assert result.status == 'AUTOREFINE_REVIEW' and registry['current'] == 'postmr'
    report = result.statistics['chemical_geometry']
    assert report['status'] == ('REVIEW' if chemistry == 'bent' else 'UNASSESSED')
    assert report['automatic_adoption'] is False
    record = execution.validate_execution(run, child['outputs']['parallelity_execution'],
        checkpoint=child['id'], parent=child['parent'], usable=True)
    request = execution.read_execution_request(run, record['request'], checkpoint=child['id'])
    assert request['chemistry_projections'][0]['site'] == 'A:1'
    assert request['policy_id'] == execution.V6_POLICY_ID
    before = {p.relative_to(run): (p.read_bytes(), p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    moved = run.with_name('relocated'); run.rename(moved)
    with patch('subprocess.Popen', side_effect=AssertionError('cold read')):
        assert read_registry(moved)[1]['current'] == 'postmr'
        cold = execution.read_execution_chemistry(moved, child['outputs']['parallelity_execution'],
            checkpoint=child['id'], parent=child['parent'], model=moved / child['model']['relative_path'])
    assert cold == report
    assert all((moved/p).read_bytes() == data and (moved/p).stat().st_mtime_ns == mtime
               for p, (data, mtime) in before.items())


@pytest.mark.parametrize('defect', [None, 'drop', 'replace'])
def test_counted_descendant_preserves_original_chemistry_scope(tmp_path, monkeypatch, defect):
    from copy import deepcopy
    from nasolve.checkpoints import inherited_paths, CheckpointError
    run, result, registry, child, _ = completed_control(tmp_path, monkeypatch, chemistry='bent')
    paths = inherited_paths(child, run)
    folder = run / 'AutoRefine/round_003'; folder.mkdir()
    params = folder / 'autorefine.params'; params.write_text('synthetic one-cycle protocol')
    inputs = [paths['observations'], paths['model'], *paths['restraints'], params]
    reference, _, _ = counted.prepare_continuation(run, checkpoint='refine-003', parent=child['id'],
        inputs=inputs, command=['phenix.refine', *map(str, inputs), 'output.prefix=refined'],
        python_executable=sys.executable, macro_cycles=1)
    request = execution.read_execution_request(run, reference, checkpoint='refine-003')
    assert request['chemistry_projections'][0]['site'] == 'A:1'
    proposed = dict(child, id='refine-003', parent=child['id'], outputs={})
    lineage = dict(registry, checkpoints=[*registry['checkpoints'], proposed])
    altered = deepcopy(request)
    if defect == 'drop':
        altered.pop('chemistry_projections')
    elif defect == 'replace':
        source = run / request['chemistry_projections'][0]['projection']['relative_path']
        replacement = run / 'different-source.cif'; replacement.write_bytes(source.read_bytes() + b'\n# same graph, different source\n')
        from nasolve.checkpoints import _file_reference
        altered['chemistry_projections'][0]['projection'] = _file_reference(replacement, run)
    if defect is None:
        counted.validate_intent_lineage(run, lineage, proposed, altered)
    else:
        with pytest.raises(ValueError, match='inherited chemistry'):
            counted.validate_intent_lineage(run, lineage, proposed, altered)
        # The ordinary pre-allocation guard rejects the same loss independently
        # of a future publication; original recipe/model remain valid.
        packet = request['counted_intent']
        original = {key: run / packet[name]['relative_path'] for key, name in
                    [('recipe', 'original_recipe'), ('source_model', 'original_model')]}
        with pytest.raises(ValueError, match='inherited chemistry'):
            counted.validate_autorefine_intent(run, registry, child, original, paths['model'],
                chemistry_projections=altered.get('chemistry_projections'))


def test_new_counted_restraints_keep_source_execution_and_inheritance(tmp_path, monkeypatch):
    from nasolve.checkpoints import inherited_paths, CheckpointError
    from nasolve.refinement_inputs import validate_checkpoint_refinement_inputs
    run, result, registry, child, commands = completed_control(tmp_path, monkeypatch, extra=True)
    assert commands == ['preflight', 'refine']
    source = run / 'new-restraints.phil'
    assert inherited_paths(child, run)['restraints'].count(source) == 1
    assert registry['current'] == 'postmr' and child['status'] == 'REVIEW'
    reference = child['restraints'][-1]
    assert reference['anchor'] == 'run' and reference['relative_path'] == 'new-restraints.phil'
    adaptations = validate_checkpoint_refinement_inputs(run, child)['adaptations']
    assert adaptations[-1]['source'] == reference
    receipt = execution.validate_execution(run, child['outputs']['parallelity_execution'],
        checkpoint=child['id'], parent=child['parent'], usable=True)
    request = execution.read_execution_request(run, receipt['request'], checkpoint=child['id'])
    assert adaptations[-1]['execution'] in request['inputs']
    before = {p.relative_to(run): (p.read_bytes(), p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    moved = run.with_name('relocated'); run.rename(moved)
    with patch('subprocess.Popen', side_effect=AssertionError('cold read')):
        assert read_registry(moved)[1]['current'] == 'postmr'
        assert inherited_paths(child, moved)['restraints'][-1] == moved / reference['relative_path']
    assert all((moved/p).read_bytes() == data and (moved/p).stat().st_mtime_ns == mtime
               for p, (data, mtime) in before.items())
    (moved / reference['relative_path']).write_text('changed after refinement')
    with pytest.raises(CheckpointError, match='checksum|changed|match'):
        read_registry(moved)


def test_new_counted_restraint_cannot_change_after_preallocation_check(tmp_path, monkeypatch):
    from nasolve import autorefine
    run, refine, dump, options = case(tmp_path)
    source = run / 'new-restraints.phil'; source.write_text('geometry_restraints {}\n')
    options['extra_restraints'] = [source]
    original = autorefine.write_recipe_parameters
    def change_source(*args, **kwargs):
        value = original(*args, **kwargs)
        source.write_text('geometry_restraints { edits {} }\n')
        return value
    monkeypatch.setattr(autorefine, 'write_recipe_parameters', change_source)
    before = (run / 'AutoRefine/checkpoints.json').read_bytes()
    import subprocess
    original_run = subprocess.run
    def only_dump(command, *args, **kwargs):
        assert Path(command[0]) == dump, 'Changed input must refuse before refinement'
        return original_run(command, *args, **kwargs)
    with patch('subprocess.run', side_effect=only_dump), \
            pytest.raises(AutoRefineError, match='input preparation failed'):
        execute_autorefine(run, refine, dump, **options)
    assert (run / 'AutoRefine/round_002/autorefine.params').is_file()
    assert (run / 'AutoRefine/checkpoints.json').read_bytes() == before
