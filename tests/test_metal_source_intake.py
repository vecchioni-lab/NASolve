"""New metal imports bind checkpoint inputs to the run's original sources.

Synthetic legacy reports exercise file/metadata ownership, not native HL values.
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve import checkpoints
from nasolve.metal.context import load_run_context
from nasolve.metal.recipe import RecipeError
from tests.test_metal_integration import write_run

RECORDS = [{'Ligand code': 'DF', 'O2': 'S2'}, {'Ligand code': 'DT', 'N3': 'N3'}]


def saved_run(root, phases=False):
    run = write_run(root)
    if phases:
        phase = run/'AutoSol/original-HL.mtz'
        phase.parent.mkdir()
        phase.write_bytes(b'synthetic HL source; not numerical diffraction evidence')
        path = run/'report.json'
        report = json.loads(path.read_text())
        report['autosol'] = dict(use_for_refinement=True, outputs=dict(
            refinement_data=str(phase),
            refinement_data_sha256=hashlib.sha256(phase.read_bytes()).hexdigest(),
            refinement_data_phase_labels=['HLA', 'HLB', 'HLC', 'HLD']))
        path.write_text(json.dumps(report))
    checkpoints.initialize_registry(run)
    return run


def edit(path, fn):
    record = json.loads(path.read_text())
    fn(record)
    path.write_text(json.dumps(record))


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def imported(run):
    with patch('subprocess.Popen', side_effect=AssertionError('Import cannot execute native tools')):
        return load_run_context(run, records=RECORDS).to_dict()


@pytest.mark.parametrize('change', ['report_file', 'checkpoint_file', 'same_bytes_other_path',
                                    'report_checksum', 'missing_original'])
def test_conflicting_original_observations_refuse(tmp_path, change):
    run = saved_run(tmp_path)
    original = run.parent.parent/'observations.mtz'
    alternate = original.with_name('explicit-alternative.mtz')
    alternate.write_bytes(original.read_bytes() if change == 'same_bytes_other_path' else b'other observations')
    if change in ('report_file', 'same_bytes_other_path'):
        edit(run/'report.json', lambda r: r['inputs'].update(
            reflections=str(alternate), reflections_sha256=hashlib.sha256(alternate.read_bytes()).hexdigest()))
    elif change == 'checkpoint_file':
        edit(checkpoints.registry_path(run), lambda r: r['checkpoints'][0].update(
            observations=checkpoints._file_reference(alternate, run)))
    elif change == 'report_checksum':
        edit(run/'report.json', lambda r: r['inputs'].update(reflections_sha256='0'*64))
    else:
        # The selected file remains intact while its declared original disappears.
        edit(checkpoints.registry_path(run), lambda r: r['checkpoints'][0].update(
            observations=checkpoints._file_reference(alternate, run)))
        original.unlink()
    before = snapshot(tmp_path)
    with pytest.raises(RecipeError, match='(observations|reflections)'):
        imported(run)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('change', ['labels', 'drop', 'path', 'unapproved'])
def test_conflicting_approved_phase_source_refuses(tmp_path, change):
    run = saved_run(tmp_path, phases=True)
    def change_registry(r):
        item = r['checkpoints'][0]
        if change == 'labels':
            item['phases']['labels'] = ['HLB', 'HLA', 'HLC', 'HLD']
        elif change == 'drop':
            item['phases'] = None
        elif change == 'path':
            other = run/'AutoSol/explicit-other-HL.mtz'
            other.write_bytes((run/'AutoSol/original-HL.mtz').read_bytes())
            item['phases'].update(checkpoints._file_reference(other, run))
    edit(checkpoints.registry_path(run), change_registry)
    if change == 'unapproved':
        edit(run/'report.json', lambda r: r['autosol'].update(use_for_refinement=False))
    before = snapshot(tmp_path)
    with pytest.raises(RecipeError, match='phase'):
        imported(run)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('name', ['report.json', 'AutoRefine/checkpoints.json'])
def test_metadata_change_during_import_refuses(tmp_path, monkeypatch, name):
    import nasolve.metal.context as context
    run = saved_run(tmp_path)
    real = context.read_registry
    def changing(path):
        result = real(path)
        target = run/name
        target.write_bytes(target.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(context, 'read_registry', changing)
    with pytest.raises(RecipeError, match='changed during'):
        imported(run)


@pytest.mark.parametrize('phases', [False, True])
def test_consistent_import_retains_saved_state_and_relocates(tmp_path, phases):
    old = tmp_path/'original'
    run = saved_run(old, phases)
    before = snapshot(old)
    first = imported(run/'report.json')
    assert first['native_ready'] is False
    assert (first['sources']['phases'] is not None) == phases
    assert snapshot(old) == before
    moved = tmp_path/'relocated'
    old.rename(moved)
    assert not old.exists()
    assert imported(moved/'dataset/AutoMR/run_001') == first
    assert snapshot(moved) == before


@pytest.mark.parametrize('name', ['model', 'observations', 'restraint'])
def test_inputs_changed_after_initial_read_refuse(tmp_path, monkeypatch, name):
    import nasolve.metal.context as context
    run = saved_run(tmp_path)
    restraint = run/'pair.phil'
    restraint.write_text('synthetic restraint input\n')
    edit(checkpoints.registry_path(run), lambda r: r['checkpoints'][0].update(
        restraints=[checkpoints._file_reference(restraint, run)]))
    target = {'model': run/'prepared.pdb', 'observations': run.parent.parent/'observations.mtz',
              'restraint': restraint}[name]
    real = context._patch_narestraints_records
    def changing(*args):
        result = real(*args)
        target.write_bytes(target.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(context, '_patch_narestraints_records', changing)
    with pytest.raises(RecipeError, match='changed during'):
        imported(run)


def test_existing_publication_supplies_review_parent_for_metal_intake(tmp_path, monkeypatch):
    """Publication/intake control, with the existing synthetic chemistry-result stub."""
    from tests.test_cif_postmr_publication import setup
    from tests.test_cif_model_context import model
    from nasolve.cif_model_context import derive_prepared_model_context
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from nasolve.campaign_records import write_record, read_record
    run, exact, calls = setup(tmp_path, monkeypatch)
    target = exact['runtime']['model']
    model(target, chains=(('A', 'DF'), ('B', 'DT')), free=True)
    lines = []
    for line in target.read_text().splitlines(keepends=True):
        if line.startswith(('ATOM  ', 'HETATM')) and int(line[22:26]) == 9:
            line = line[:22] + f'{12 if line[21] == "A" else 4:4d}' + line[26:]
        lines.append(line)
    target.write_text(''.join(lines))
    report_path = run/'report.json'
    edit(report_path, lambda r: r.update(frame={'name': 'W'}))
    report = json.loads(report_path.read_text())
    request = run/'PostMR/DictionaryEngine/request'
    record = read_record(request/'request.json')
    record['configuration']['model_context'] = derive_prepared_model_context(target, report, ['DF', 'DT'])
    write_record(request/'request.json', record, replace=True)
    original = request/'inputs/construction/PostMR/Model/mr_solution.pdb'
    original.write_bytes(target.read_bytes())
    with patch('subprocess.Popen', side_effect=AssertionError('No native run')):
        publish_checked_preparation(run, attempt_number=1)
        before = snapshot(tmp_path)
        doc = imported(run)
        _, registry = checkpoints.read_registry(run)
    assert snapshot(tmp_path) == before
    assert doc['checkpoint_id'] == 'postmr' and doc['native_ready'] is False
    assert registry['checkpoints'][0]['status'] == 'REVIEW'
    assert registry['current'] == 'postmr'
    assert doc['sources']['model']['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert len(doc['sources']['restraints']) == 3  # original PHIL + repeated dictionaries, in order
    assert doc['sources']['phases'] is None


def test_legacy_missing_checksum_and_unused_autosol_keep_their_meaning(tmp_path):
    run = saved_run(tmp_path)
    def legacy(r):
        r['inputs'].pop('reflections_sha256')
        r['autosol'] = {'use_for_refinement': False, 'outputs': {'refinement_data': 'absent-unused.mtz'}}
    edit(run/'report.json', legacy)
    assert imported(run)['sources']['phases'] is None


def test_saved_hypothesis_replay_is_not_reinterpreted_as_a_new_import(tmp_path):
    from tests.test_metal_materialize import control
    from nasolve.metal.materialize import build_hypothesis, verify_hypothesis
    context, recipe, placement = control(tmp_path)
    result = build_hypothesis(context, recipe, placement)
    directory = (context.run/result['files']['model']['relative_path']).parent
    checkpoints.initialize_registry(context.run)
    edit(context.run/'report.json', lambda r: r['inputs'].update(reflections_sha256='0'*64))
    before = snapshot(tmp_path)
    with pytest.raises(RecipeError, match='observations'):
        imported(context.run)
    assert verify_hypothesis(context.run, directory) == result
    assert snapshot(tmp_path) == before


def test_normal_cli_refuses_missing_parent_before_native_discovery(tmp_path, monkeypatch, capsys):
    from nasolve.cli import main
    import nasolve.metal.cli as cli
    def unexpected(*args, **kwargs):
        raise AssertionError('No discovery for an unreadable parent')
    monkeypatch.setattr(cli, 'discover_phenix', unexpected)
    root = tmp_path/'private-fit'
    root.mkdir()
    assert main(['metal', 'inspect', str(root), '--json']) == 2
    assert 'Could not read NASolve report' in capsys.readouterr().err
    assert list(root.iterdir()) == []
