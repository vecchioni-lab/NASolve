"""Prepared bytes must derive from the selected protected parent, not just hash."""
from pathlib import Path
import json
import shutil
from unittest.mock import patch
import pytest
from nasolve.cli import main
from nasolve.metal import child_inputs as m
from nasolve.metal import child_process, parent_archive, fdp
from nasolve.metal.context import parse_pdb
from nasolve.metal.recipe import RecipeError
from tests.test_metal_fdp_endpoint import endpoint


def prepared_case(tmp_path,monkeypatch):
    c,h,x,native=endpoint(tmp_path/'layout',monkeypatch,metals=('Hg',))
    archive=tmp_path/'parent';receipt=parent_archive.pack_parent_inputs(tmp_path/'layout',archive)
    doc=fdp.run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1'],occupancies={'m1':.6},metal_b_policy='donor-mean')
    trial=c.run/Path(doc['files']['plan.json']['relative_path']).parent
    prepared=tmp_path/'prepared';prepared.mkdir()
    plan=json.loads((trial/'native-plan.json').read_text())
    for name in set(plan['args'])|{'plan.json','native-plan.json'}:shutil.copyfile(trial/name,prepared/name)
    request=child_process.make_request(prepared,parent_manifest_sha256=receipt['manifest_sha256'])
    return c,archive,prepared,request


def verify(values,**kwargs):
    c,archive,prepared,request=values
    return m.verify_child_inputs(prepared,archive,request,request_id=request['request_id'],
        run_relative='dataset/AutoMR/run_001',endpoint_relative='Metal/xyz_001',**kwargs)


def test_normal_cli_replays_refined_b_q_and_parent_under_one_registry_read(tmp_path,monkeypatch,capsys):
    values=prepared_case(tmp_path,monkeypatch);c,archive,prepared,request=values
    request_path=tmp_path/'request.json';request_path.write_text(json.dumps(request))
    files={p:p.read_bytes() for root in [archive,prepared] for p in root.rglob('*') if p.is_file()}
    with patch.object(m,'read_registry',wraps=m.read_registry) as registry, patch('subprocess.Popen',side_effect=AssertionError('No native work')):
        assert main(['metal','verify-fdp-child-inputs',str(prepared),'--parent-archive',str(archive),
          '--request',str(request_path),'--request-id',request['request_id'],'--run-relative','dataset/AutoMR/run_001',
          '--endpoint-relative','Metal/xyz_001','--json'])==0
        assert registry.call_count==1
    result=json.loads(capsys.readouterr().out)
    assert result['derivation_verified'] and result['ordinary_checkpoint_verified']
    assert result['source_kind']=='native_xyz_endpoint'
    assert result['root_checkpoint_id']=='postmr'
    assert result['parent_transport']['snapshot_removed'] and result['parent_transport']['inputs_unchanged']
    assert result['scientific_acceptance']=='NOT_ASSESSED' and not result['execution_authorized']
    state=parse_pdb((prepared/'input.pdb').read_bytes()).to_dict()['atomic_state'][-1]
    assert state['b_iso']==260. and state['occupancy']==.6
    assert all(p.read_bytes()==raw for p,raw in files.items())


@pytest.mark.parametrize('file',['input.pdb','observations.mtz','parameters.phil'])
def test_rehashed_prepared_bytes_still_fail_parent_derivation(tmp_path,monkeypatch,file):
    values=prepared_case(tmp_path,monkeypatch);c,archive,prepared,request=values
    (prepared/file).write_bytes((prepared/file).read_bytes()+b'changed')
    request=child_process.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    with pytest.raises(RecipeError,match='derivation'):
        verify((c,archive,prepared,request))


def test_original_sources_removed_relocated_parent_replays(tmp_path,monkeypatch):
    values=prepared_case(tmp_path,monkeypatch);c,archive,prepared,request=values
    shutil.rmtree(tmp_path/'layout')
    new=tmp_path/'relocated';new.mkdir();archive.rename(new/'parent');prepared.rename(new/'prepared')
    with patch('subprocess.Popen',side_effect=AssertionError('No native work')):
        result=verify((c,new/'parent',new/'prepared',request))
    assert result['derivation_verified'] and result['parent_transport']['snapshot_removed']
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize('defect',['unusable-root','different-root-model','missing-original-reflections'])
def test_ordinary_parent_is_required_even_with_saved_hypothesis(tmp_path,monkeypatch,defect):
    values=prepared_case(tmp_path,monkeypatch);c,archive,prepared,request=values
    report_path=c.run/'report.json';report=json.loads(report_path.read_text())
    if defect=='unusable-root':report['postmr']['status']='FAILED'
    elif defect=='different-root-model':
        alternate=c.run/'alternate.pdb';shutil.copyfile(c.run/'model.pdb',alternate)
        report['postmr']['prepared_model']=str(alternate)
    else:(tmp_path/'layout/dataset/observations.mtz').unlink()
    report_path.write_text(json.dumps(report))
    # Deliberately remove the diagnostic child: the archive represents the parent only.
    shutil.rmtree(c.run/'Metal/fdp_001')
    other=tmp_path/'changed-parent';receipt=parent_archive.pack_parent_inputs(tmp_path/'layout',other)
    request=child_process.make_request(prepared,parent_manifest_sha256=receipt['manifest_sha256'])
    with pytest.raises(ValueError):verify((c,other,prepared,request))


def test_unsupported_control_policy_refuses_before_parent_materialization(tmp_path,monkeypatch):
    values=prepared_case(tmp_path,monkeypatch)
    monkeypatch.setattr(m.parent_archive,'materialized_parent_inputs',lambda *a,**k:pytest.fail('Opened parent'))
    with pytest.raises(RecipeError,match='reader-control'):
        verify(values,reader_control_policy='cif-captured-reader-control-handoff-v1')


@pytest.mark.parametrize('run,endpoint',[('../outside','Metal/xyz_001'),('dataset/AutoMR/run_001','../xyz_001'),('dataset/AutoMR/run_001','Metal/fdp_001')])
def test_nonexplicit_or_wrong_kind_parent_paths_refuse(tmp_path,monkeypatch,run,endpoint):
    c,archive,prepared,request=prepared_case(tmp_path,monkeypatch)
    with pytest.raises(RecipeError):m.verify_child_inputs(prepared,archive,request,request_id=request['request_id'],run_relative=run,endpoint_relative=endpoint)


def test_mutable_root_report_status_text_does_not_change_frozen_science(tmp_path,monkeypatch):
    c,archive,prepared,request=prepared_case(tmp_path,monkeypatch)
    path=c.run/'report.json';report=json.loads(path.read_text());report['later_note']='Updated stage display only'
    path.write_text(json.dumps(report));shutil.rmtree(c.run/'Metal/fdp_001')
    other=tmp_path/'updated-parent';receipt=parent_archive.pack_parent_inputs(tmp_path/'layout',other)
    request=child_process.make_request(prepared,parent_manifest_sha256=receipt['manifest_sha256'])
    assert verify((c,other,prepared,request))['derivation_verified']


def test_native_endpoint_requires_environment_policy_even_with_valid_request_digest(tmp_path,monkeypatch):
    c,archive,prepared,request=prepared_case(tmp_path,monkeypatch)
    plan=json.loads((prepared/'plan.json').read_text());plan['options'].pop('metal_b_policy')
    native_plan=json.loads((prepared/'native-plan.json').read_text());native_plan['plan']=plan
    (prepared/'plan.json').write_text(json.dumps(plan));(prepared/'native-plan.json').write_text(json.dumps(native_plan))
    request=child_process.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    with pytest.raises(RecipeError,match='B policy'):verify((c,archive,prepared,request))


def test_native_argument_omission_cannot_drop_an_inherited_restraint(tmp_path,monkeypatch):
    c,archive,prepared,request=prepared_case(tmp_path,monkeypatch)
    path=prepared/'native-plan.json';native_plan=json.loads(path.read_text())
    resource=next(n for n in native_plan['args'] if n.startswith('resource_'))
    native_plan['args'].remove(resource);path.write_text(json.dumps(native_plan))
    request=child_process.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    with pytest.raises(RecipeError,match='derivation'):verify((c,archive,prepared,request))


def test_parent_part_changed_during_replay_prevents_a_verdict(tmp_path,monkeypatch):
    values=prepared_case(tmp_path,monkeypatch);archive=values[1];original=m.make_plan
    def changed(*a,**kw):
        result=original(*a,**kw)
        part=archive/'part-001.zip';part.write_bytes(part.read_bytes()+b'changed')
        return result
    monkeypatch.setattr(m,'make_plan',changed)
    with pytest.raises(ValueError):verify(values)


@pytest.mark.parametrize('role',[{}, {'policy_id':'cif-captured-reader-control-handoff-v1','phils':[]}])
def test_role_presence_refuses_even_when_no_control_phils_are_listed(tmp_path,monkeypatch,role):
    c,archive,prepared,request=prepared_case(tmp_path,monkeypatch)
    path=c.run/'report.json';report=json.loads(path.read_text())
    report['configuration']={'controls':{'interpretation_controls':role}}
    path.write_text(json.dumps(report));shutil.rmtree(c.run/'Metal/fdp_001')
    other=tmp_path/'typed-parent';receipt=parent_archive.pack_parent_inputs(tmp_path/'layout',other)
    request=child_process.make_request(prepared,parent_manifest_sha256=receipt['manifest_sha256'])
    with pytest.raises(RecipeError,match='reader-control role'):verify((c,other,prepared,request))


@pytest.mark.parametrize('controls',[{}, {'interpretation_controls':{}}])
def test_guard_follows_declared_checked_preparation_to_request(tmp_path,controls):
    from nasolve.metal.context import _reference
    root=tmp_path/'layout';run=root/'dataset/AutoMR/run_001';run.mkdir(parents=True)
    request=run/'request.json';request.write_text(json.dumps({'configuration':{'controls':controls}}))
    publication=run/'preparation.json';publication.write_text(json.dumps({'checked_preparation':{'request':_reference(request,run)}}))
    selected={'checked_preparation':_reference(publication,run)}
    if controls:
        with pytest.raises(RecipeError,match='reader-control role'):m._refuse_reader_controls(selected,run,root)
    else:m._refuse_reader_controls(selected,run,root)
