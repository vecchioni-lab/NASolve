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


def test_plane_display_notes_do_not_rewrite_published_messages(tmp_path,monkeypatch):
    from nasolve import cif_ordinary_postmr as ordinary,cif_postmr_publication as publication
    run,exact,_=setup(tmp_path,monkeypatch)
    exact['result']['plane_generation']=dict(components={'PDU':dict(status='KNOWN_GENERATION_FAILURE',
        missing_centres=['C5'],proof=dict(failure_kind='TIMED_OUT'))})
    current=ordinary._plane_support_limitations
    monkeypatch.setattr(ordinary,'_plane_support_limitations',lambda report:('Historical display wording',))
    old=publication.publish_checked_preparation(run,attempt_number=1);before=snapshot(run)
    monkeypatch.setattr(ordinary,'_plane_support_limitations',current)
    with patch('subprocess.Popen',side_effect=AssertionError('No new execution')):
        assert publication.publish_checked_preparation(run,attempt_number=1)==old
        publication.validate_published_preparation(run,json.loads((run/'report.json').read_text()))
    assert snapshot(run)==before


@pytest.mark.parametrize('selected', ['verified_parent_runtime', 'readyset_checked_model'])
def test_publication_returns_current_notes_without_second_proof_or_receipt_rewrite(tmp_path, monkeypatch, selected):
    from nasolve import cif_postmr_publication as publication
    run, exact, reads = setup(tmp_path, monkeypatch, selected)
    exact['result']['plane_generation'] = dict(components={
        'PDU': dict(status='OWNED_SUPPORT_READY', missing_centres=['C5']),
        'OTHER': dict(status='KNOWN_GENERATION_FAILURE', missing_centres=['C2'], proof=dict(failure_kind='TIMED_OUT'))})
    record, notes = publication.publish_checked_preparation_with_notes(run, attempt_number=1)
    assert reads == [1]
    assert 'PDU: generated source-checked support' in '\n'.join(notes)
    assert 'OTHER: optional plane generation timed out' in '\n'.join(notes)
    assert 'does not establish final plane adoption' in '\n'.join(notes)
    assert 'checkpoint adoption is a separate' not in '\n'.join(notes)
    assert 'generated' not in record['message'] and 'limitations' not in record
    before = snapshot(run)
    with patch('subprocess.Popen', side_effect=AssertionError('No new execution')):
        again, current = publication.publish_checked_preparation_with_notes(run, attempt_number=1)
    assert reads == [1, 1] and again == record and current == notes
    assert snapshot(run) == before
    assert publication.publish_checked_preparation(run, attempt_number=1) == record


def test_publication_cli_shows_generation_limits_without_sdk_or_duplicate_read(tmp_path, monkeypatch, capsys):
    from nasolve.cli import main
    run, exact, reads = setup(tmp_path, monkeypatch)
    exact['result']['plane_generation'] = dict(components={'PDU': dict(
        status='KNOWN_GENERATION_FAILURE', missing_centres=['C5'], proof=dict(failure_kind='TIMED_OUT'))})
    with patch('nasolve.cli.load_config', side_effect=AssertionError('No tool discovery')):
        assert main(['cif-doctor', 'publish-preparation', str(run), '--attempt', '1']) == 0
    text = capsys.readouterr().out
    assert 'optional plane generation timed out' in text
    assert 'does not establish final plane adoption' in text and 'REVIEW' in text
    assert reads == [1]



@pytest.mark.parametrize('change', ['bookmark', 'selection', 'child'])
def test_checked_registry_stale_save_preserves_newer_work(tmp_path, monkeypatch, change):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run, _, _ = setup(tmp_path, monkeypatch)
    publish_checked_preparation(run, attempt_number=1)
    _, stale = checkpoints.read_registry(run)
    if change == 'bookmark':
        checkpoints.add_checkpoint(run, name='newer bookmark')
    else:
        manual = run/'manual.pdb'
        manual.write_bytes((run/'PostMR/Model/readyset_model.pdb').read_bytes())
        child = checkpoints.add_checkpoint(run, name='newer model', model=manual)
        if change == 'selection':
            checkpoints.select_checkpoint(run, child.checkpoint_id)
    before = snapshot(run)
    stale['bookmarks']['older pending edit'] = 'postmr'
    with pytest.raises(checkpoints.CheckpointError, match='changed since'):
        checkpoints.save_registry(run, stale)
    assert snapshot(run) == before


def test_checked_registry_serial_saves_refresh_same_live_identity(tmp_path, monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run, _, _ = setup(tmp_path, monkeypatch)
    publish_checked_preparation(run, attempt_number=1)
    _, registry = checkpoints.read_registry(run)
    old = registry['record_sha256']
    registry['bookmarks']['one'] = 'postmr'
    checkpoints.save_registry(run, registry)
    assert registry['record_sha256'] != old
    assert registry['record_sha256'] == read_record(checkpoints.registry_path(run))['record_sha256']
    registry['bookmarks']['two'] = 'postmr'
    checkpoints.save_registry(run, registry)
    assert read_record(checkpoints.registry_path(run))['bookmarks'] == {'one':'postmr', 'two':'postmr'}


def test_checked_registry_conflict_is_checked_inside_existing_kernel_lock(tmp_path, monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from nasolve.campaign_process import exclusive_lock
    run, _, _ = setup(tmp_path, monkeypatch)
    publish_checked_preparation(run, attempt_number=1)
    _, registry = checkpoints.read_registry(run)
    with exclusive_lock(run/'AutoRefine/checkpoints.lock'):
        before = snapshot(run)
        registry['bookmarks']['busy'] = 'postmr'
        with pytest.raises(checkpoints.CheckpointError, match='lock busy'):
            checkpoints.save_registry(run, registry)
        assert snapshot(run) == before


@pytest.mark.parametrize('defect', ['missing_digest', 'registry_symlink'])
def test_checked_registry_writer_requires_bound_regular_registry(tmp_path, monkeypatch, defect):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run, _, _ = setup(tmp_path, monkeypatch)
    publish_checked_preparation(run, attempt_number=1)
    _, registry = checkpoints.read_registry(run)
    path = checkpoints.registry_path(run)
    if defect == 'missing_digest':
        registry.pop('record_sha256')
    else:
        target = path.with_name('preserved.json'); path.rename(target); path.symlink_to(target)
    # The lock inode may be created; evidence and registry bytes must not change.
    before = snapshot(run)
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints.save_registry(run, registry)
    after = snapshot(run)
    assert all(after[name] == value for name, value in before.items())
    assert set(after)-set(before) <= {'AutoRefine/checkpoints.lock'}



@pytest.fixture
def alternative_preparation(tmp_path, monkeypatch):
    from nasolve import cif_postmr_publication as publication
    run, first, calls = setup(tmp_path, monkeypatch)
    publication.publish_checked_preparation(run, attempt_number=1)
    request = run/'PostMR/DictionaryEngine/request'
    second = deepcopy(first)
    attempt = request/'attempts/attempt-0002'; attempt.mkdir()
    write_record(attempt/'result.json', dict(status='QUALIFIED_DIAGNOSTIC_RUNTIME'))
    model = attempt/'selected.pdb'; model.write_text(first['runtime']['model'].read_text()+'REMARK preparation alternative\n')
    cif = attempt/'selected.cif'; cif.write_text('data_new_selected\n')
    phil = attempt/'selected.phil'; phil.write_text('geometry_restraints {}\n')
    second['runtime'].update(model=model, dictionaries=[cif], phils=[phil])
    values = {1:first, 2:second}; reads=[]
    def batch(root, numbers):
        assert root == request
        reads.append(tuple(numbers))
        return {number:values[number] for number in numbers}
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_results',batch,raising=False)
    return publication, run, values, reads


def test_later_preparation_is_unselected_alternative_from_frozen_construction(alternative_preparation):
    p, run, values, reads = alternative_preparation
    root_report=(run/'report.json').read_bytes(); root_receipt=(run/'PostMR/report.json').read_bytes()
    before=read_record(checkpoints.registry_path(run)); root=deepcopy(before['checkpoints'][0])
    result, notes=p.publish_preparation_alternative(run,attempt_number=2)
    assert reads == [(1,2)]  # One complete history read, not one per publication.
    saved=read_record(checkpoints.registry_path(run))
    assert saved['schema_version']==4 and saved['current']=='postmr'
    assert saved['checkpoints'][0]==root and saved['bookmarks']==before['bookmarks']
    item=saved['checkpoints'][1]
    assert item['id']=='prepare-002' and item['parent']=='postmr'
    assert item['kind']=='preparation' and item['preparation_relation']=='SAME_FROZEN_CONSTRUCTION'
    assert item['status']=='REVIEW' and item['compatibility']['refinement_validation']=='NOT_RUN'
    assert result['checkpoint_id']==item['id'] and notes
    assert (run/'report.json').read_bytes()==root_report and (run/'PostMR/report.json').read_bytes()==root_receipt
    paths=checkpoints.inherited_paths(item,run)
    assert paths['model']==values[2]['runtime']['model']
    assert paths['restraints']==values[2]['runtime']['phils']+values[2]['runtime']['dictionaries']
    profile=resolve_view_profile(run,checkpoint='prepare-002')
    assert profile.checkpoint_id=='prepare-002' and 'not recalculated for prepared alternative' in profile.map_source
    before=snapshot(run);p.publish_preparation_alternative(run,attempt_number=2)
    assert snapshot(run)==before


def test_alternative_selection_and_manual_descendant_keep_exact_new_restraints(alternative_preparation):
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    checkpoints.select_checkpoint(run,'prepare-002')
    added=checkpoints.add_checkpoint(run,name='edited alternative',model=values[2]['runtime']['model'])
    _,registry=checkpoints.read_registry(run)
    assert registry['schema_version']==4 and registry['current']=='prepare-002'
    item=checkpoints.resolve_checkpoint(registry,added.checkpoint_id)
    assert item['parent']=='prepare-002'
    assert checkpoints.inherited_paths(item,run)['restraints']==values[2]['runtime']['phils']+values[2]['runtime']['dictionaries']
    checkpoints.select_checkpoint(run,added.checkpoint_id)
    before=snapshot(run);p.publish_preparation_alternative(run,attempt_number=2)
    assert snapshot(run)==before
    assert resolve_view_profile(run).checkpoint_id==added.checkpoint_id
    _,registry=checkpoints.read_registry(run);item=checkpoints.resolve_checkpoint(registry,added.checkpoint_id)
    item['restraints']=item['restraints'][1:]
    write_record(checkpoints.registry_path(run),registry,replace=True)
    with pytest.raises(checkpoints.CheckpointError,match='inherited'):
        checkpoints.resolve_checkpoint(registry,added.checkpoint_id)


@pytest.mark.parametrize('boundary',['receipt','registry'])
def test_interrupted_alternative_publication_reuses_receipt_and_preserves_newer_selection(alternative_preparation,monkeypatch,boundary):
    p,run,values,reads=alternative_preparation
    original=p.write_record
    def interrupted(path,value,**kw):
        result=original(path,value,**kw)
        if boundary=='receipt' and path.name=='attempt-0002.json':
            raise OSError('interrupted after save')
        return result
    with monkeypatch.context() as patcher:
        patcher.setattr(p,'write_record',interrupted)
        if boundary=='registry':
            save=checkpoints.save_registry
            def interrupted_registry(*args,**kwargs):
                save(*args,**kwargs);raise OSError('interrupted after save')
            patcher.setattr(checkpoints,'save_registry',interrupted_registry)
        with pytest.raises(OSError,match='interrupted'):
            p.publish_preparation_alternative(run,attempt_number=2)
    receipt=run/'PostMR/Preparations/attempt-0002.json'
    sealed=receipt.read_bytes(),receipt.stat().st_mtime_ns
    checkpoints.add_checkpoint(run,name='intervening bookmark')
    before=read_record(checkpoints.registry_path(run))
    p.publish_preparation_alternative(run,attempt_number=2)
    after=read_record(checkpoints.registry_path(run))
    assert after['current']==before['current'] and after['bookmarks']==before['bookmarks']
    assert (receipt.read_bytes(),receipt.stat().st_mtime_ns)==sealed
    assert len([x for x in after['checkpoints'] if x['id']=='prepare-002'])==1


@pytest.mark.parametrize('defect',['model','restraints','parent','relation','receipt','schema'])
def test_alternative_consumers_refuse_rehashed_broken_binding(alternative_preparation,defect):
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    registry=read_record(checkpoints.registry_path(run));item=registry['checkpoints'][1]
    if defect=='model':item['model']=registry['checkpoints'][0]['model']
    elif defect=='restraints':item['restraints']=registry['checkpoints'][0]['restraints']
    elif defect=='parent':item['parent']='manual-001'
    elif defect=='relation':item['preparation_relation']='REFINED_FROM_PARENT'
    elif defect=='receipt':item.pop('checked_preparation')
    else:registry['schema_version']=3
    write_record(checkpoints.registry_path(run),registry,replace=True)
    before=snapshot(run)
    with pytest.raises(checkpoints.CheckpointError):checkpoints.read_registry(run)
    with pytest.raises(CootViewError):resolve_view_profile(run,checkpoint='prepare-002')
    assert snapshot(run)==before


def test_alternative_publication_cannot_adopt_unqualified_or_initial_attempt(alternative_preparation):
    p,run,values,reads=alternative_preparation
    before=snapshot(run)
    with pytest.raises(ValueError):p.publish_preparation_alternative(run,attempt_number=1)
    values[2]['runtime']=None
    with pytest.raises(ValueError,match='independently checked'):
        p.publish_preparation_alternative(run,attempt_number=2)
    after=snapshot(run)
    assert all(after[name]==value for name,value in before.items())
    assert set(after)-set(before)<= {'AutoRefine/checkpoints.lock'}


def test_autosol_does_not_silently_use_root_when_alternative_is_selected(alternative_preparation):
    from nasolve.autosol import _read_run_report,AutoSolPreparationError
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    _read_run_report(run)  # Unselected alternative leaves initial phasing semantics intact.
    checkpoints.select_checkpoint(run,'prepare-002')
    before=snapshot(run)
    with pytest.raises(AutoSolPreparationError,match='initial.*preparation'):
        _read_run_report(run)
    assert snapshot(run)==before



def test_alternative_refinement_receives_selected_model_and_matching_restraints(alternative_preparation,tmp_path):
    from nasolve.autorefine import execute_autorefine
    from tests.test_autorefine import make_refine,make_mtz_dump
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    result=execute_autorefine(run,make_refine(tmp_path),make_mtz_dump(tmp_path,anomalous=False),
        from_checkpoint='prepare-002',macro_cycles=1,phenix_version='2.2.1-6174',environment={'PATH':'/usr/bin:/bin'})
    received=json.loads(next((run/'AutoRefine').rglob('received_args.json')).read_text())
    expected=[values[2]['runtime']['model'],*values[2]['runtime']['phils'],*values[2]['runtime']['dictionaries']]
    assert all(str(path) in received for path in expected)
    assert all(str(path) not in received for path in values[1]['runtime']['dictionaries'])
    _,registry=checkpoints.read_registry(run)
    assert registry['schema_version']==4
    item=checkpoints.resolve_checkpoint(registry,result.checkpoint_id)
    assert item['parent']=='prepare-002'
    assert checkpoints.inherited_paths(item,run)['restraints']==expected[1:]


def test_alternative_cli_is_explicit_and_does_not_discover_tools(alternative_preparation,monkeypatch,capsys):
    from nasolve.cli import main
    p,run,values,reads=alternative_preparation
    monkeypatch.setattr('nasolve.cli.load_config',lambda:pytest.fail('No SDK discovery'))
    assert main(['cif-doctor','publish-preparation',str(run),'--attempt','2','--as-alternative'])==0
    output=capsys.readouterr().out
    assert 'same frozen construction' in output and 'selection is unchanged' in output
    assert '--checkpoint prepare-002' in output and 'REVIEW' in output
    assert reads==[(1,2)]


def test_alternative_publication_and_reads_survive_relocation(alternative_preparation,monkeypatch,tmp_path):
    import shutil
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    dataset=run.parents[1];moved=tmp_path/'moved-dataset';shutil.move(str(dataset),moved)
    newrun=moved/run.relative_to(dataset)
    for exact in values.values():
        runtime=exact['runtime'];runtime['model']=newrun/runtime['model'].relative_to(run)
        for key in ('dictionaries','phils'):runtime[key]=[newrun/path.relative_to(run) for path in runtime[key]]
    def batch(root,numbers):
        assert root==newrun/'PostMR/DictionaryEngine/request'
        return {n:values[n] for n in numbers}
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_results',batch)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('Cold read must not run'))
    before=snapshot(moved)
    p.publish_preparation_alternative(newrun,attempt_number=2)
    assert checkpoints.read_registry(newrun)[1]['schema_version']==4
    assert resolve_view_profile(newrun,checkpoint='prepare-002').model_path==values[2]['runtime']['model']
    assert snapshot(moved)==before and not dataset.exists()


def test_alternative_conflicting_save_retains_receipt_for_fresh_reconciliation(alternative_preparation,monkeypatch):
    p,run,values,reads=alternative_preparation
    original=p._alternative_node;intervened=[]
    def competing(*args):
        node=original(*args)
        if not intervened:
            intervened.append(True)
            checkpoints.add_checkpoint(run,name='newer while saving')
        return node
    with monkeypatch.context() as patcher:
        patcher.setattr(p,'_alternative_node',competing)
        with pytest.raises(checkpoints.CheckpointError,match='changed since'):
            p.publish_preparation_alternative(run,attempt_number=2)
    receipt=run/'PostMR/Preparations/attempt-0002.json';before=receipt.read_bytes(),receipt.stat().st_mtime_ns
    registry=read_record(checkpoints.registry_path(run))
    assert registry['bookmarks']=={'newer while saving':'postmr'} and len(registry['checkpoints'])==1
    p.publish_preparation_alternative(run,attempt_number=2)
    assert (receipt.read_bytes(),receipt.stat().st_mtime_ns)==before
    assert read_record(checkpoints.registry_path(run))['bookmarks']==registry['bookmarks']


def test_alternative_cannot_write_through_symlinked_publication_directory(alternative_preparation,tmp_path):
    p,run,values,reads=alternative_preparation
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir()
    (run/'PostMR/Preparations').symlink_to(elsewhere,target_is_directory=True)
    from nasolve.campaigns import CampaignError
    with pytest.raises(CampaignError,match='symbolic link'):
        p.publish_preparation_alternative(run,attempt_number=2)
    assert not list(elsewhere.iterdir())



def test_initial_checked_observations_follow_declared_anchor_after_dataset_rename(tmp_path,monkeypatch):
    import shutil
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    dataset=run.parents[1];moved=tmp_path/'renamed-dataset';shutil.move(str(dataset),moved)
    newrun=moved/run.relative_to(dataset)
    runtime=exact['runtime'];runtime['model']=newrun/runtime['model'].relative_to(run)
    for key in ('dictionaries','phils'):runtime[key]=[newrun/path.relative_to(run) for path in runtime[key]]
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    before=snapshot(moved)
    registry=checkpoints.read_registry(newrun)[1]
    assert checkpoints.inherited_paths(registry['checkpoints'][0],newrun)['observations']==moved/'staraniso.mtz'
    publish_checked_preparation(newrun,attempt_number=1)
    assert snapshot(moved)==before and not dataset.exists()


@pytest.mark.parametrize('defect',['missing','checksum','absolute'])
def test_checked_observation_anchor_never_falls_back_to_historical_path(tmp_path,monkeypatch,defect):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,_=setup(tmp_path,monkeypatch);publish_checked_preparation(run,attempt_number=1)
    report=json.loads((run/'report.json').read_text())
    ref=report['postmr']['checked_preparation']['observations']
    if defect=='missing':ref['relative_path']='missing.mtz'
    elif defect=='checksum':ref['sha256']='0'*64
    else:ref.update(anchor='absolute',absolute_path=report['inputs']['reflections'])
    with pytest.raises(checkpoints.CheckpointError):checkpoints._required_observations(report,run)



@pytest.mark.parametrize('defect',['attempt_type','initial_receipt','unqualified_second'])
def test_alternative_saved_proof_must_remain_bound_to_its_exact_result(alternative_preparation,defect):
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    receipt=run/'PostMR/Preparations/attempt-0002.json'
    record=read_record(receipt)
    if defect=='unqualified_second':
        values[2]['runtime']=None
    else:
        if defect=='attempt_type':record['preparation']['checked_preparation']['attempt_number']=2.0
        else:record['initial_preparation']['sha256']='0'*64
        write_record(receipt,record,replace=True)
        registry=read_record(checkpoints.registry_path(run))
        registry['checkpoints'][1]['checked_preparation']=checkpoints._file_reference(receipt,run)
        write_record(checkpoints.registry_path(run),registry,replace=True)
    before=snapshot(run)
    with pytest.raises(checkpoints.CheckpointError):checkpoints.read_registry(run)
    assert snapshot(run)==before


def test_alternative_schema_is_preserved_and_old_readers_refuse(alternative_preparation,monkeypatch):
    p,run,values,reads=alternative_preparation
    p.publish_preparation_alternative(run,attempt_number=2)
    _,registry=checkpoints.read_registry(run)
    before=snapshot(run);registry['schema_version']=3
    with pytest.raises(checkpoints.CheckpointError,match='downgrade'):
        checkpoints.save_registry(run,registry)
    assert snapshot(run)==before
    monkeypatch.setattr(checkpoints,'READABLE_SCHEMA_VERSIONS',{1,2,3})
    with pytest.raises(checkpoints.CheckpointError,match='Unsupported checkpoint schema'):
        checkpoints.read_registry(run)
    assert snapshot(run)==before
