"""Registered publication and descendant identity, with simulated owner results.

The complete-request reader is stubbed only to isolate the publication boundary.
Real FT request/runtime evidence is qualified separately; fixtures are not chemistry.
"""
from copy import deepcopy
import json
import shutil
from unittest.mock import patch

import pytest
pytest.importorskip('gemmi')
from nasolve.campaign_records import read_record, write_record
from nasolve import checkpoints
from .test_cif_complete_request import case
from .test_cif_postmr_request import entry_case
from .test_registered_preparation_request import registered_case
from .test_cif_postmr_publication import setup, snapshot


def prepared(tmp_path, monkeypatch, entry):
    from nasolve.cif_registered_execution import POLICY_ID
    from nasolve.cif_registered_preparation_input import capture_registered_backbone
    run, exact, calls = setup(tmp_path, monkeypatch, 'verified_prepared_bundle')
    _, args, *_ = registered_case(entry)
    path = run/'report.json'; report = json.loads(path.read_text())
    report['post_mr_plan'] = args['report']['post_mr_plan']; path.write_text(json.dumps(report))
    model = exact['runtime']['model']; model.write_bytes(args['model'].read_bytes())
    request = run/'PostMR/DictionaryEngine/request'
    (request/'request.lock').touch()
    captured = capture_registered_backbone(model, ['YYY','ZZZ'],
        dict(args['registered_preparation'], report=report))
    for name, raw in dict(captured['files'], **{'model.pdb':model.read_bytes()}).items():
        p=request/'inputs'/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
    config = dict(components={'YYY':{},'ZZZ':{}}, registered_backbone=captured['reference'],
                  registered_execution_policy=POLICY_ID)
    write_record(request/'request.json', dict(configuration=config), replace=True)
    exact['result']['registered_execution_policy'] = POLICY_ID
    context = captured['context']
    exact['registered_runtime_review'] = dict(policy_id='registered-original-runtime-review-v1',
        status='REGISTERED_ORIGINAL_RUNTIME_FOR_REVIEW', native_input_review={
            k:deepcopy(context[k]) for k in ('model_sha256','components','local_links','image_links','protected_terminal_phosphates')})
    return run, exact, calls


def publish(run):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    with patch('subprocess.Popen', side_effect=AssertionError('Publication must not execute')):
        return publish_checked_preparation(run, attempt_number=1)


def test_registered_publication_preserves_both_images_and_original_choice(tmp_path,monkeypatch,entry_case):
    run, exact, calls=prepared(tmp_path,monkeypatch,entry_case)
    before=snapshot(run); record=publish(run)
    assert calls==[1]
    topology=record['checked_model_topology']
    assert topology['policy_id']=='registered-prepared-model-topology-v1'
    assert [(r['o3_site'],r['phosphate_site'],r['o3_image']) for r in topology['image_links']]==[
        ('A:9','A:1','x-1,y,z'),('B:9','B:1','x-1,y,z')]
    assert len(topology['local_links'])==4
    assert all(r['anchor']=='run' for r in topology['sources'].values())
    _,registry=checkpoints.read_registry(run)
    assert registry['current']=='postmr' and registry['checkpoints'][0]['status']=='REVIEW'
    assert registry['checkpoints'][0]['usable'] is True
    after=snapshot(run)
    assert all(after[name]==value for name,value in before.items() if name!='report.json')
    frozen=snapshot(run); publish(run); assert snapshot(run)==frozen


@pytest.mark.parametrize('defect',['held','readyset','missing_review','different_review'])
def test_unqualified_registered_selection_cannot_publish(tmp_path,monkeypatch,entry_case,defect):
    run,exact,_=prepared(tmp_path,monkeypatch,entry_case)
    if defect=='held':
        p=run/'PostMR/DictionaryEngine/request/request.json'; r=read_record(p)
        r['configuration'].pop('registered_execution_policy');write_record(p,{k:v for k,v in r.items() if k!='record_sha256'},replace=True)
    if defect=='readyset':exact['runtime']['manifest']['decision']['selected']='readyset_checked_model'
    if defect=='missing_review':exact.pop('registered_runtime_review')
    if defect=='different_review':exact['registered_runtime_review']['native_input_review']['image_links'].pop()
    before=snapshot(run)
    with pytest.raises(ValueError,match='[Rr]egistered|original'):publish(run)
    assert snapshot(run)==before


def test_registered_descendant_keeps_declared_partners_without_freezing_xyz(tmp_path,monkeypatch,entry_case):
    from nasolve.autorefine import validate_refined_model
    from nasolve.ligand_profiles import validate_model_phosphate_policy
    run,exact,_=prepared(tmp_path,monkeypatch,entry_case);publish(run)
    child=tmp_path/'child.pdb';child.write_text(exact['runtime']['model'].read_text().replace('   5.000','   5.010'))
    report=json.loads((run/'report.json').read_text())
    result=validate_refined_model(child,report,run_directory=run)
    assert result['validated'] is True
    assert len(result['phosphate_policy']['registered_image_links'])==2
    imported=checkpoints.add_checkpoint(run,name='moved-slightly',model=child)
    _,registry=checkpoints.read_registry(run)
    assert registry['current']=='postmr'
    checkpoints.select_checkpoint(run,imported.checkpoint_id)
    publish(run)
    _,registry=checkpoints.read_registry(run)
    assert registry['current']==imported.checkpoint_id
    with pytest.raises(ValueError,match='run|anchor'):
        validate_model_phosphate_policy(child,report)


@pytest.mark.parametrize('defect',['cell','identity','occupied','image','missing','digest','intent'])
def test_registered_topology_refuses_changed_sources_or_descendants(tmp_path,monkeypatch,entry_case,defect):
    from nasolve.ligand_profiles import validate_model_phosphate_policy
    run,exact,_=prepared(tmp_path,monkeypatch,entry_case);record=publish(run)
    child=tmp_path/'child.pdb';child.write_bytes(exact['runtime']['model'].read_bytes())
    report=json.loads((run/'report.json').read_text())
    if defect=='cell':child.write_text(child.read_text().replace(' 100.000',' 101.000',1))
    if defect=='identity':child.write_text(child.read_text().replace(' DA B   9',' DC B   9'))
    if defect=='occupied':child.write_text(child.read_text().replace('  1.00','  0.00',1))
    if defect=='image':report['postmr']['checked_model_topology']['image_links'][0]['o3_image']='x+1,y,z'
    if defect in {'missing','digest'}:
        ref=record['checked_model_topology']['sources']['continuations'];p=run/ref['relative_path']
        if defect=='missing':p.unlink()
        else:p.write_bytes(p.read_bytes()+b'\n')
    if defect=='intent':report['post_mr_plan']['allow_op3_sites']=['A:1']
    before=snapshot(run)
    with pytest.raises(ValueError):validate_model_phosphate_policy(child,report,run_directory=run)
    assert snapshot(run)==before


def test_registered_publication_relocates_with_original_paths_absent(tmp_path,monkeypatch,entry_case):
    from nasolve.ligand_profiles import validate_model_phosphate_policy
    run,exact,_=prepared(tmp_path,monkeypatch,entry_case);record=publish(run)
    old=run.parent.parent; moved=tmp_path/'relocated';shutil.move(old,moved)
    target=moved/'AutoMR'/run.name
    assert not old.exists()
    report=json.loads((target/'report.json').read_text())
    model=target/record['prepared_model']
    with patch('subprocess.Popen',side_effect=AssertionError('Read only')):
        result=validate_model_phosphate_policy(model,report,run_directory=target)
    assert len(result['registered_image_links'])==2
