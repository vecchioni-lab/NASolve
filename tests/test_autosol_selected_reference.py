"""A chosen preparation supplies HA validation, never the native phasing model."""
import json
import shutil
from copy import deepcopy

import pytest

from nasolve import checkpoints
from nasolve.autosol import execute_autosol
from nasolve.campaign_records import read_record, write_record
from nasolve.cif_postmr_publication import publish_checked_preparation
from nasolve.coot_view import resolve_view_profile
from tests.helpers import pdb_record
from tests.test_autosol import cryst1, make_autosol, make_mtz_dump
from tests.test_cif_postmr_publication import setup, snapshot


@pytest.fixture
def selected_run(tmp_path, monkeypatch):
    run, exact, calls = setup(tmp_path, monkeypatch)
    path = run/'report.json'; report = json.loads(path.read_text())
    summary = run/'summary.html'; summary.write_text('wavelength [A] = 1.377618\n')
    report['inputs']['summary'] = str(summary)
    sequence = run/'sequence.txt'; sequence.write_text('AA\n')
    report['inputs']['frame_sequence'] = str(sequence)
    phaser = run/'Phaser/mr_solution.pdb'; phaser.write_text(cryst1(space_group='P 1')+'END\n')
    report['execution'] = {'phaser':{'solution_pdb':str(phaser)}}
    path.write_text(json.dumps(report))
    model = exact['runtime']['model']
    extra = ''.join(pdb_record('HETATM', 100+i, name, 'DA', 'A', 1,
        element=element, x=x, y=2., z=3.)
        for i,(name,element,x) in enumerate((("C1'",'C',1.),("C2'",'C',2.),('I','I',1.))))
    model.write_text(cryst1(space_group='P 1')+model.read_text().replace('END\n','')+extra+'END\n')
    publish_checked_preparation(run, attempt_number=1)
    manual = run/'edited.pdb'
    text = model.read_text()
    lines = [line[:30]+f'{20.:8.3f}'+line[38:] if line.startswith('HETATM') and line[12:16].strip()=='I' else line for line in text.splitlines()]
    manual.write_text('\n'.join(lines)+'\n')
    child = checkpoints.add_checkpoint(run, name='chosen iodine', model=manual)
    checkpoints.select_checkpoint(run, child.checkpoint_id)
    return run, exact, calls, child.checkpoint_id


def run_autosol(run, root, **kwargs):
    return execute_autosol(run, make_autosol(root,(20.,2.,3.),map_files=('overall_best_denmod_map_coeffs.mtz',)),
        make_mtz_dump(root), environment={'PATH':'/usr/bin:/bin'}, processor_count=8, **kwargs)


def test_chosen_coordinates_are_used_but_original_phaser_model_is_sent(selected_run,tmp_path):
    run, exact, calls, identifier = selected_run
    result = run_autosol(run,tmp_path)
    assert result.status == 'AUTOSOL_READY'
    assert result.matched_distance == 0.
    report = json.loads((run/'report.json').read_text())
    args = json.loads((run/'AutoSol/received_args.json').read_text())
    assert f'autosol.phasing.input_partpdb_file={run}/Phaser/mr_solution.pdb' in args
    ref = read_record(run/'AutoSol/site-reference.json')
    assert ref['checkpoint_id'] == identifier
    assert ref['candidates'][0]['coordinates'] == [20.,2.,3.]
    assert report['postmr']['anomalous']['candidates'][0]['coordinates'] == [1.,2.,3.]
    assert checkpoints.read_registry(run)[1]['schema_version'] == 5
    assert resolve_view_profile(run).checkpoint_id == identifier
    assert report['autosol']['site_reference']['relative_path'] == 'AutoSol/site-reference.json'


def phase_read(run):
    from nasolve.autorefine import _effective_phase
    report = json.loads((run/'report.json').read_text())
    return _effective_phase(report, {}, run)


def test_selection_after_launch_does_not_rewrite_the_validation_reference(selected_run,tmp_path,monkeypatch):
    import nasolve.autosol as autosol
    run, _, _, identifier = selected_run
    original = autosol.subprocess.run
    def native(*args, **kwargs):
        if 'cwd' in kwargs:
            checkpoints.select_checkpoint(run,'postmr')
        return original(*args, **kwargs)
    monkeypatch.setattr(autosol.subprocess,'run',native)
    assert run_autosol(run,tmp_path).status == 'AUTOSOL_READY'
    assert checkpoints.read_registry(run)[1]['current'] == 'postmr'
    assert read_record(run/'AutoSol/site-reference.json')['checkpoint_id'] == identifier
    assert phase_read(run) is not None


def test_competing_preflight_selection_prevents_native_launch(selected_run,tmp_path,monkeypatch):
    import nasolve.autosol as autosol
    run, _, _, _ = selected_run
    original = autosol._run_mtz_dump
    def changed(*args, **kwargs):
        checkpoints.select_checkpoint(run,'postmr')
        return original(*args, **kwargs)
    monkeypatch.setattr(autosol,'_run_mtz_dump',changed)
    with pytest.raises(checkpoints.CheckpointError,match='changed since'):
        run_autosol(run,tmp_path)
    assert checkpoints.read_registry(run)[1]['current'] == 'postmr'
    assert not (run/'AutoSol/received_args.json').exists()
    assert (run/'AutoSol/site-reference.json').is_file()  # interrupted evidence preserved


@pytest.mark.parametrize('defect',['candidates','cell','model','missing','downgrade','phase_binding','site_result','accepted','heavy_atom'])
def test_consumers_refuse_changed_reference_or_result(selected_run,tmp_path,defect):
    from nasolve.autorefine import AutoRefineError
    from nasolve.coot_view import CootViewError
    run, _, _, _ = selected_run
    run_autosol(run,tmp_path)
    rp=run/'report.json'; report=json.loads(rp.read_text())
    cp=checkpoints.registry_path(run); registry=read_record(cp)
    refpath=run/'AutoSol/site-reference.json'; ref=read_record(refpath)
    if defect in {'candidates','cell','model'}:
        if defect=='candidates':ref['candidates'][0]['coordinates'][0]=1.
        if defect=='cell':ref['unit_cell'][0]=100.
        if defect=='model':ref['model']=registry['checkpoints'][0]['model']
        write_record(refpath,ref,replace=True)
        registry['autosol_site_reference']=checkpoints._file_reference(refpath,run)
        write_record(cp,registry,replace=True)
        report['autosol']['site_reference']=registry['autosol_site_reference']
    elif defect=='missing':refpath.unlink()
    elif defect=='downgrade':
        registry['schema_version']=3;write_record(cp,registry,replace=True)
    elif defect=='phase_binding':report['autosol'].pop('site_reference')
    elif defect=='site_result':report['autosol']['site_validation']['attempts'][0]['candidate']['coordinates'][0]=1.
    elif defect=='accepted':report['autosol']['site_validation']['best_distance']=19.
    else:
        heavy=run/'AutoSol/AutoSol_run_1_/overall_best_ha_pdb.pdb';heavy.write_text('END\n')
    # Rehashing both copies does not make a scientifically contradictory result valid.
    report['autosol']=write_record(run/'AutoSol/report.json',report['autosol'],replace=True)
    rp.write_text(json.dumps(report))
    before=snapshot(run)
    with pytest.raises(AutoRefineError):phase_read(run)
    with pytest.raises(CootViewError):resolve_view_profile(run)
    assert snapshot(run)==before


def test_native_failure_retains_reference_and_allows_mr_continuation(selected_run,tmp_path):
    from nasolve.autosol_reference import validate_result_reference
    run, _, _, identifier=selected_run
    result=execute_autosol(run,make_autosol(tmp_path,(20.,2.,3.),return_code=2),make_mtz_dump(tmp_path),
        environment={'PATH':'/usr/bin:/bin'},processor_count=8)
    assert result.status=='AUTOSOL_WARNING'
    assert checkpoints.read_registry(run)[1]['current']==identifier
    assert phase_read(run) is None
    assert resolve_view_profile(run).checkpoint_id==identifier
    report=json.loads((run/'report.json').read_text());validate_result_reference(run,report)
    assert report['autosol']['site_reference']['relative_path']=='AutoSol/site-reference.json'


def test_relocated_reference_and_consumers_do_not_need_original_paths(selected_run,tmp_path,monkeypatch):
    from nasolve.autosol_reference import validate_result_reference
    run, exact, calls, identifier=selected_run
    run_autosol(run,tmp_path)
    original=tmp_path/'dataset'; moved=tmp_path/'renamed dataset'
    shutil.move(original,moved);newrun=moved/run.relative_to(original)
    runtime=exact['runtime']
    runtime['model']=newrun/runtime['model'].relative_to(run)
    for key in ('dictionaries','phils'):
        runtime[key]=[newrun/p.relative_to(run) for p in runtime[key]]
    def read(root,number):
        assert root==newrun/'PostMR/DictionaryEngine/request' and number==1
        calls.append(number);return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',read)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('Readback must not execute tools'))
    before=snapshot(newrun)
    assert not original.exists()
    assert checkpoints.read_registry(newrun)[1]['current']==identifier
    assert phase_read(newrun) is not None
    assert resolve_view_profile(newrun).checkpoint_id==identifier
    validate_result_reference(newrun,json.loads((newrun/'report.json').read_text()))
    assert snapshot(newrun)==before


def test_old_reader_refuses_new_authority_and_save_cannot_downgrade(selected_run,tmp_path,monkeypatch):
    run, _, _, _=selected_run
    run_autosol(run,tmp_path)
    before=snapshot(run)
    with monkeypatch.context() as old:
        old.setattr(checkpoints,'READABLE_SCHEMA_VERSIONS',{1,2,3,4})
        with pytest.raises(checkpoints.CheckpointError,match='Unsupported checkpoint schema'):
            checkpoints.read_registry(run)
    assert snapshot(run)==before
    registry=checkpoints.read_registry(run)[1];registry['schema_version']=4
    with pytest.raises(checkpoints.CheckpointError,match='downgrade'):
        checkpoints.save_registry(run,registry)
    assert snapshot(run)==before


def test_autosol_inspection_uses_saved_model_after_current_choice_changes(selected_run,tmp_path):
    run, _, _, identifier=selected_run
    run_autosol(run,tmp_path)
    chosen=checkpoints.resolve_checkpoint(checkpoints.read_registry(run)[1],identifier)
    checkpoints.select_checkpoint(run,'postmr')
    before=snapshot(run)
    view=resolve_view_profile(run,stage='autosol')
    assert view.model_path==checkpoints._ref_path(chosen['model'],'model',run)
    assert identifier in view.source
    assert resolve_view_profile(run).checkpoint_id=='postmr'
    assert snapshot(run)==before


def test_alternative_and_later_publication_preserve_new_reference_schema(selected_run,tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_preparation_alternative
    run, first, _, identifier=selected_run
    request=run/'PostMR/DictionaryEngine/request'; values={1:first}
    manual=checkpoints.resolve_checkpoint(checkpoints.read_registry(run)[1],identifier)
    selected=checkpoints._ref_path(manual['model'],'model',run)
    for number in (2,3):
        attempt=request/f'attempts/attempt-{number:04d}';attempt.mkdir()
        write_record(attempt/'result.json',dict(status='QUALIFIED_DIAGNOSTIC_RUNTIME'))
        model=attempt/'selected.pdb';model.write_bytes(selected.read_bytes())
        values[number]=deepcopy(first);values[number]['runtime']['model']=model
    def batch(root,numbers):
        assert root==request
        return {number:values[number] for number in numbers}
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_results',batch)
    publish_preparation_alternative(run,attempt_number=2)
    checkpoints.select_checkpoint(run,'prepare-002')
    assert run_autosol(run,tmp_path).status=='AUTOSOL_READY'
    reference=(run/'AutoSol/site-reference.json').read_bytes()
    publish_preparation_alternative(run,attempt_number=3)
    registry=checkpoints.read_registry(run)[1]
    assert registry['schema_version']==5 and registry['current']=='prepare-002'
    assert 'prepare-003' in {item['id'] for item in registry['checkpoints']}
    assert (run/'AutoSol/site-reference.json').read_bytes()==reference
    assert phase_read(run) is not None
    assert resolve_view_profile(run,stage='autosol').model_path==values[2]['runtime']['model']


@pytest.mark.parametrize('changed',['chosen_model','phaser_model','run_report'])
def test_changed_inputs_during_execution_preserve_outputs_without_adopting_them(selected_run,tmp_path,monkeypatch,changed):
    import nasolve.autosol as autosol
    run, _, _, identifier=selected_run
    registry=checkpoints.read_registry(run)[1]
    chosen=checkpoints._ref_path(checkpoints.resolve_checkpoint(registry,identifier)['model'],'model',run)
    original=autosol.subprocess.run
    def native(*args,**kwargs):
        result=original(*args,**kwargs)
        if 'cwd' in kwargs:
            if changed=='run_report':
                p=run/'report.json';r=json.loads(p.read_text());r['message']='other work';p.write_text(json.dumps(r))
            else:
                p=chosen if changed=='chosen_model' else run/'Phaser/mr_solution.pdb'
                p.write_text(p.read_text()+'REMARK changed\n')
        return result
    monkeypatch.setattr(autosol.subprocess,'run',native)
    with pytest.raises((checkpoints.CheckpointError,ValueError),match='changed|frozen'):
        run_autosol(run,tmp_path)
    assert (run/'AutoSol/AutoSol_run_1_/overall_best_ha_pdb.pdb').exists()
    report=json.loads((run/'report.json').read_text())
    assert 'autosol' not in report
    if changed=='run_report':
        assert report['message']=='other work'
        assert (run/'AutoSol/report.json').exists()


def test_selected_model_without_heavy_atoms_does_not_reuse_initial_candidates(selected_run,tmp_path):
    from nasolve.autosol import AutoSolPreparationError
    run, exact, _, _=selected_run
    manual=run/'no-iodine.pdb'
    manual.write_text('\n'.join(line for line in exact['runtime']['model'].read_text().splitlines()
                                if not (line.startswith('HETATM') and line[12:16].strip()=='I'))+'\n')
    child=checkpoints.add_checkpoint(run,name='no iodine',model=manual)
    checkpoints.select_checkpoint(run,child.checkpoint_id)
    before=snapshot(run)
    with pytest.raises(AutoSolPreparationError,match='no nucleotide heavy atom'):
        run_autosol(run,tmp_path)
    assert snapshot(run)==before


@pytest.mark.parametrize('site,expected',[(25.,'AUTOSOL_REVIEW'),(30.,'AUTOSOL_WARNING')])
def test_selected_reference_keeps_existing_review_and_warning_distances(selected_run,tmp_path,site,expected):
    run, _, _, _=selected_run
    result=execute_autosol(run,make_autosol(tmp_path,(site,2.,3.),map_files=('overall_best_denmod_map_coeffs.mtz',)),
        make_mtz_dump(tmp_path),environment={'PATH':'/usr/bin:/bin'},processor_count=8)
    assert result.status==expected
    assert phase_read(run) is None
    assert 'unaccepted; inspection only' in resolve_view_profile(run,stage='autosol').map_source
