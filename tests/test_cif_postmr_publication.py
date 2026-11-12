"""Checked preparation must stay one exact, recoverable choice in normal use."""
import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from nasolve import checkpoints
from nasolve.campaign_records import write_record, read_record
from nasolve.coot_view import resolve_view_profile, CootViewError
from tests.test_checkpoints import make_checkpoint_run


def setup(tmp_path, monkeypatch, selected='verified_parent_runtime'):
    run=make_checkpoint_run(tmp_path)
    p=run/'report.json';report=json.loads(p.read_text());report.pop('postmr')
    report.update(stage='phaser',status='MR_SUCCESS',post_mr_plan={})
    p.write_text(json.dumps(report))
    request=run/'PostMR/DictionaryEngine/request';attempt=request/'attempts/attempt-0001';attempt.mkdir(parents=True)
    write_record(attempt/'result.json',dict(status='QUALIFIED_DIAGNOSTIC_RUNTIME'))
    model=run/'PostMR/Model/readyset_model.pdb';cif=run/'PostMR/ReadySet/prepared_model.ligands.cif'
    phil=run/'PostMR/Restraints/narestraints.phil'
    from tests.test_cif_model_context import model as connected_model
    from nasolve.cif_model_context import derive_prepared_model_context
    connected_model(model,chains=(('A','DA'),),free=True)
    context=derive_prepared_model_context(model,report,['DA'])
    write_record(request/'request.json',dict(configuration=dict(model_context=context)))
    original=request/'inputs/construction/PostMR/Model/mr_solution.pdb';original.parent.mkdir(parents=True);original.write_bytes(model.read_bytes())
    runtime=dict(model=model,dictionaries=[cif,cif],phils=[phil],manifest=dict(decision=dict(selected=selected)))
    exact=dict(result=dict(status='QUALIFIED_DIAGNOSTIC_RUNTIME'),runtime=runtime,
        construction_inputs=dict(report=dict(inputs=dict(reference_model=dict(path='PostMR/Model/mr_solution.pdb')), controls=dict(actions=[]))),
        continuation=dict(report=dict(phases={'readyset':'FAILED' if selected=='verified_parent_runtime' else 'COMPLETED'})))
    phaser=run/'Phaser';phaser.mkdir();(phaser/'mr_solution.mtz').write_bytes(b'map fixture')
    calls=[]
    def read(root,number):
        assert root==request and number==1
        calls.append(number);return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',read)
    return run,exact,calls


def snapshot(root):
    return {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('value',['bad',{},[None],[{}]])
@pytest.mark.parametrize('reader',[checkpoints.inherited_paths,checkpoints._inherited_paths_for_autorefine])
def test_refinement_never_silently_drops_a_malformed_restraint(tmp_path,value,reader):
    run=make_checkpoint_run(tmp_path);_,registry=checkpoints.initialize_registry(run)
    item=deepcopy(registry['checkpoints'][0]);item['restraints']=value
    with pytest.raises(checkpoints.CheckpointError,match='restraint'):reader(item,run)


@pytest.mark.parametrize('selected',['verified_parent_runtime','readyset_checked_model','repaired_prepared_bundle'])
def test_publish_exact_preparation_preserves_order_and_review_status(tmp_path,monkeypatch,selected):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,calls=setup(tmp_path,monkeypatch,selected)
    if selected=='readyset_checked_model':
        p=run/'report.json';r=json.loads(p.read_text())
        r['inputs']['reflections_sha256']=r['inputs']['reflections_sha256'].upper()
        p.write_text(json.dumps(r))
    before=snapshot(run)
    with patch('subprocess.Popen',side_effect=AssertionError('Publication must not run tools')):
        result=publish_checked_preparation(run,attempt_number=1)
    assert calls==[1]
    assert result['checked_preparation']['selected']==selected
    assert result['readyset']['status']==('FAILED' if selected=='verified_parent_runtime' else 'COMPLETED')
    saved=json.loads((run/'report.json').read_text());assert saved['postmr']==read_record(run/'PostMR/report.json')
    _,registry=checkpoints.read_registry(run);assert registry['schema_version']==3
    root=checkpoints.resolve_checkpoint(registry,'postmr')
    assert root['status']=='REVIEW' and root['usable'] is True and registry['current']=='postmr'
    inherited=checkpoints.inherited_paths(root,run)
    assert inherited['model']==exact['runtime']['model']
    assert inherited['restraints']==exact['runtime']['phils']+exact['runtime']['dictionaries']
    view=resolve_view_profile(run);assert view.model_path==exact['runtime']['model']
    assert view.dictionary_paths==tuple(exact['runtime']['dictionaries'])
    assert 'retained' in view.source.lower() if selected=='verified_parent_runtime' else True
    after=snapshot(run)
    assert all(after[name]==value for name,value in before.items() if name!='report.json')
    again=snapshot(run);publish_checked_preparation(run,attempt_number=1);assert snapshot(run)==again


@pytest.mark.parametrize('boundary',['registry','run_report'])
def test_interrupted_publication_recovers_exact_choice_without_rerunning_tools(tmp_path,monkeypatch,boundary):
    import nasolve.cif_postmr_publication as m
    run,exact,calls=setup(tmp_path,monkeypatch)
    original=snapshot(run)
    if boundary=='run_report':
        with patch.object(m,'_publish_run_report',side_effect=OSError('interrupted')):
            with pytest.raises(OSError):m.publish_checked_preparation(run,attempt_number=1)
    else:
        write=m.write_record
        def interrupted(path,value,**kw):
            if path.name=='checkpoints.json':raise OSError('interrupted')
            return write(path,value,**kw)
        with patch.object(m,'write_record',side_effect=interrupted):
            with pytest.raises(OSError):m.publish_checked_preparation(run,attempt_number=1)
    partial=snapshot(run)
    assert partial['report.json']==original['report.json']
    assert 'PostMR/report.json' in partial
    sealed=partial['PostMR/report.json']
    with patch('subprocess.Popen',side_effect=AssertionError('no native rerun')):
        m.publish_checked_preparation(run,attempt_number=1)
    assert snapshot(run)['PostMR/report.json']==sealed
    assert checkpoints.read_registry(run)[1]['schema_version']==3


def test_recovery_never_overwrites_a_changed_run_report(tmp_path,monkeypatch):
    import nasolve.cif_postmr_publication as m
    run,_,_=setup(tmp_path,monkeypatch)
    with patch.object(m,'_publish_run_report',side_effect=OSError('interrupted')):
        with pytest.raises(OSError):m.publish_checked_preparation(run,attempt_number=1)
    p=run/'report.json';r=json.loads(p.read_text());r['message']='other work';p.write_text(json.dumps(r))
    before=snapshot(run)
    with pytest.raises(ValueError,match='changed since'):m.publish_checked_preparation(run,attempt_number=1)
    assert snapshot(run)==before


def test_publication_cannot_replace_an_earlier_choice_or_reselect_after_refinement(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,_,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    manual=run/'manual.pdb';manual.write_bytes((run/'PostMR/Model/readyset_model.pdb').read_bytes())
    added=checkpoints.add_checkpoint(run,name='later manual model',model=manual)
    checkpoints.select_checkpoint(run,added.checkpoint_id)
    before=snapshot(run)
    publish_checked_preparation(run,attempt_number=1)
    assert snapshot(run)==before
    with pytest.raises(ValueError,match='different preparation'):publish_checked_preparation(run,attempt_number=2)
    assert snapshot(run)==before
    assert checkpoints.read_registry(run)[1]['current']==added.checkpoint_id


@pytest.mark.parametrize('which',['model','restraints','binding','intent','registry_digest','proof','review_claim','phases'])
def test_normal_consumers_reject_changed_published_binding(tmp_path,monkeypatch,which):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,_,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    rp=run/'report.json';r=json.loads(rp.read_text());cp=run/'AutoRefine/checkpoints.json';c=read_record(cp)
    if which=='proof':
        def fail(*a):raise ValueError('changed native/producer/compiler proof')
        monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',fail)
    elif which=='intent':
        r['post_mr_plan']['allow_op3_sites']=['A:1'];rp.write_text(json.dumps(r))
    elif which=='registry_digest':
        c['current']='bad';cp.write_text(json.dumps(c))
    else:
        root=c['checkpoints'][0]
        if which=='model':root['model']=root['restraints'][0]
        if which=='restraints':root['restraints']=root['restraints'][:-1]
        if which=='binding':root.pop('checked_preparation')
        if which=='review_claim':root['compatibility']['refinement_validation']='PASSED'
        if which=='phases':root['phases']=root['observations']
        write_record(cp,c,replace=True)
    before=snapshot(run)
    with pytest.raises(checkpoints.CheckpointError):checkpoints.read_registry(run)
    with pytest.raises(CootViewError):resolve_view_profile(run)
    from nasolve.autosol import _read_run_report, AutoSolPreparationError
    with pytest.raises(AutoSolPreparationError):_read_run_report(run)
    assert snapshot(run)==before


def test_new_child_model_is_allowed_but_dropped_parent_restraints_are_not(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,_,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    manual=run/'manual.pdb';manual.write_text((run/'PostMR/Model/readyset_model.pdb').read_text()+'REMARK changed model\n')
    child=checkpoints.add_checkpoint(run,name='child',model=manual)
    _,registry=checkpoints.read_registry(run);item=checkpoints.resolve_checkpoint(registry,child.checkpoint_id)
    assert checkpoints.inherited_paths(item,run)['model'].read_bytes()==manual.read_bytes()
    assert resolve_view_profile(run,checkpoint=child.checkpoint_id).checkpoint_id==child.checkpoint_id
    item['restraints']=item['restraints'][1:]
    write_record(run/'AutoRefine/checkpoints.json',registry,replace=True)
    _,registry=checkpoints.read_registry(run)
    with pytest.raises(checkpoints.CheckpointError,match='restraints'):checkpoints.resolve_checkpoint(registry,child.checkpoint_id)
    with pytest.raises(CootViewError,match='restraints'):resolve_view_profile(run,checkpoint=child.checkpoint_id)
    assert resolve_view_profile(run,checkpoint='postmr').checkpoint_id=='postmr'


def test_publication_and_reads_follow_relocation_without_old_paths(tmp_path,monkeypatch):
    import shutil
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,_=setup(tmp_path/'original',monkeypatch);publish_checked_preparation(run,attempt_number=1)
    moved=tmp_path/'moved';shutil.move(str(tmp_path/'original'),moved)
    newrun=moved/run.relative_to(tmp_path/'original')
    runtime=exact['runtime']
    for name in ('model',):runtime[name]=newrun/runtime[name].relative_to(run)
    for name in ('dictionaries','phils'):runtime[name]=[newrun/p.relative_to(run) for p in runtime[name]]
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    before=snapshot(moved)
    assert checkpoints.read_registry(newrun)[1]['schema_version']==3
    assert resolve_view_profile(newrun).model_path==runtime['model']
    publish_checked_preparation(newrun,attempt_number=1)
    assert snapshot(moved)==before and not (tmp_path/'original').exists()


def test_cli_publishes_fallback_without_discovering_sdk(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    run,_,_=setup(tmp_path,monkeypatch)
    with patch('nasolve.cli.load_config',side_effect=AssertionError('No SDK configuration')):
        assert main(['cif-doctor','publish-preparation',str(run),'--attempt','1'])==0
    output=capsys.readouterr().out
    assert 'FAILED' in output and 'retained' in output and 'REVIEW' in output
    assert '--checkpoint postmr' in output


def test_later_unused_autosol_phase_is_not_required_to_read_preparation(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,_,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    p=run/'report.json';r=json.loads(p.read_text())
    r['autosol']=dict(status='AUTOSOL_READY',use_for_refinement=True,outputs=dict(refinement_data='AutoSol/absent.mtz'))
    p.write_text(json.dumps(r))
    _,registry=checkpoints.read_registry(run)
    assert checkpoints.inherited_paths(registry['checkpoints'][0],run)['phases'] is None


def test_initial_publication_rejects_changed_requested_mutations(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,_,_=setup(tmp_path,monkeypatch)
    p=run/'report.json';r=json.loads(p.read_text());r['post_mr_plan']['mutations']={'A:1':'DC'};p.write_text(json.dumps(r))
    with pytest.raises((ValueError,RuntimeError)):
        publish_checked_preparation(run,attempt_number=1)
    assert not (run/'PostMR/report.json').exists()


def test_ordinary_refinement_receives_the_exact_checked_bundle(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from nasolve.autorefine import execute_autorefine
    from tests.test_autorefine import make_refine,make_mtz_dump
    run,exact,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    before=(run/'PostMR/report.json').read_bytes()
    result=execute_autorefine(run,make_refine(tmp_path),make_mtz_dump(tmp_path,anomalous=False),macro_cycles=1,phenix_version="2.2.1-6174",environment={"PATH":"/usr/bin:/bin"})
    assert result.checkpoint_id
    _,registry=checkpoints.read_registry(run)
    child=checkpoints.resolve_checkpoint(registry,result.checkpoint_id)
    assert child['parent']=='postmr'
    paths=checkpoints.inherited_paths(child,run)
    assert paths['restraints']==exact['runtime']['phils']+exact['runtime']['dictionaries']
    assert (run/'PostMR/report.json').read_bytes()==before
    received=json.loads(next((run/'AutoRefine').rglob('received_args.json')).read_text())
    for path in paths['restraints']:assert str(path) in received


def test_unqualified_preparation_cannot_create_a_checkpoint(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,_=setup(tmp_path,monkeypatch);exact['runtime']=None
    before=snapshot(run)
    with pytest.raises(ValueError,match='no independently checked'):
        publish_checked_preparation(run,attempt_number=1)
    after=snapshot(run)
    assert all(after[name]==value for name,value in before.items())
    assert set(after)-set(before)=={'PostMR/DictionaryEngine/request/request.lock'}


def test_checked_backbone_links_survive_later_model_edits(tmp_path):
    from tests.test_cif_model_context import model
    from nasolve.cif_model_context import derive_prepared_model_context
    from nasolve.autorefine import validate_refined_model, AutoRefineError
    original=model(tmp_path/'original.pdb',chains=(('A','DA'),),free=True)
    report=dict(post_mr_plan={})
    context=derive_prepared_model_context(original,report,['DA'])
    fields=('schema_version','policy_id','components','intent','contexts','expected_links')
    report['postmr']={'checked_model_topology':{k:context[k] for k in fields}}
    # Rigid translation changes coordinates, not chemistry or the recorded link.
    translated=tmp_path/'translated.pdb';broken=tmp_path/'broken.pdb'
    def shift(line,amount):
        return line[:30]+f'{float(line[30:38])+amount:8.3f}'+line[38:] if line.startswith(('ATOM  ','HETATM')) else line
    translated.write_text(''.join(shift(line,0.2) for line in original.read_text().splitlines(keepends=True)))
    assert validate_refined_model(translated,report)['validated'] is True
    # Pull the second residue away: names and old restraint files still agree,
    # but its phosphate no longer connects to the original neighbour.
    broken.write_text(''.join(shift(line,30) if line.startswith(('ATOM  ','HETATM')) and line[22:26].strip()=='9' else line
                              for line in original.read_text().splitlines(keepends=True)))
    with pytest.raises(AutoRefineError,match='phosphate'):
        validate_refined_model(broken,report)
