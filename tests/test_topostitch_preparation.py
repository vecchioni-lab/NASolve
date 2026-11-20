"""Preparation reporting composes a trusted owner; it never admits motion."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import shutil

import pytest
from nasolve import checkpoints


@pytest.fixture
def prepared(tmp_path):
    run=tmp_path/'dataset/AutoMR/run_001';run.mkdir(parents=True)
    def write(name,value):
        p=run/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(value if isinstance(value,bytes) else json.dumps(value).encode());return p
    model=write('PostMR/model.pdb',b'unchanged model bytes\n');obs=write('data.mtz',b'observations')
    phil=write('PostMR/parameters.phil',b'original restraint')
    config=dict(model_context={'model_sha256':'1'*64,'policy_id':'test-source'},restraint_context={'policy_id':'test-restraints'},literal_na_inputs={'anchor':'dictionary_request_directory','path':'inputs/literal_na','policy_id':'test-literal'})
    request=write('PostMR/request/request.json',{'configuration':config})
    result=write('PostMR/request/attempts/attempt-0001/result.json',{'status':'TEST_ONLY'})
    meta=dict(attempt_number=1,request=checkpoints._file_reference(request,run),result=checkpoints._file_reference(result,run))
    published=write('PostMR/report.json',{'checked_preparation':meta})
    parent=dict(id='postmr',kind='postmr',parent=None,usable=True,model=checkpoints._file_reference(model,run),observations=checkpoints._file_reference(obs,run),phases=None,restraints=[checkpoints._file_reference(phil,run)],checked_preparation=checkpoints._file_reference(published,run))
    write('report.json',{'postmr':json.loads(published.read_text())})
    write('AutoRefine/checkpoints.json',dict(schema_version=3,current='postmr',bookmarks={},checkpoints=[parent]))
    checked=SimpleNamespace(run_directory=run,request_directory=request.parent,attempt_number=1,model_path=model,report_path=result,restraint_paths=(phil,),dictionary_paths=())
    exact={'result':json.loads(result.read_text()),'literal_na_inputs':{'report':{'policy_id':'test-literal','index_basis':'PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES'}}}
    state=dict(run=run,checked=checked,exact=exact,config=config)
    def reader(path):
        assert path==state['run']
        return path,json.loads(checkpoints.registry_path(path).read_text()),{1:(state['checked'],state['exact'])}
    state['reader']=reader
    return state


def load(s,**overrides):
    from nasolve.topostitch_preparation import inspect_checkpoint_preparation
    args=dict(expected_checkpoint_id='postmr',expected_model_sha256=sha256(s['checked'].model_path.read_bytes()).hexdigest(),preparation_reader=s['reader'])
    return inspect_checkpoint_preparation(s['run'],**dict(args,**overrides))


def test_available_fields_are_exact_but_not_chemical_or_motion_authority(prepared):
    before={p:p.read_bytes() for p in prepared['run'].rglob('*') if p.is_file()}
    value=load(prepared)
    assert value['availability']['model_context']['status']=='AVAILABLE'
    assert value['availability']['model_context']['matches_selected_model'] is False
    assert value['availability']['literal_na_inputs']['index_basis'].startswith('PDB_RECORD_ORDER')
    assert value['availability']['explicit_na_policy']['status']=='UNAVAILABLE'
    assert not value['chemical_admission'] and not value['motion_admission'] and not value['locking']
    assert value==load(prepared,expected_context_sha256=value['context_sha256'])
    assert str(prepared['run']) not in json.dumps(value)
    assert all(p.read_bytes()==b for p,b in before.items())


def test_same_bytes_different_checkpoint_and_wrong_hash_refused(prepared):
    with pytest.raises(ValueError,match='identity'):load(prepared,expected_checkpoint_id='prepare-002')
    with pytest.raises(ValueError,match='model'):load(prepared,expected_model_sha256='0'*64)


def test_refined_descendants_are_not_preparation_inputs(prepared):
    p=checkpoints.registry_path(prepared['run']);r=json.loads(p.read_text());r['checkpoints'][0].update(id='refine-001',kind='refine');r['current']='refine-001';p.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='descendant'):load(prepared,expected_checkpoint_id='refine-001')


def test_explicit_preparation_alternative_uses_its_own_publication(prepared):
    run=prepared['run'];p=run/'PostMR/alternative.json';p.write_text(json.dumps({'preparation':json.loads((run/'PostMR/report.json').read_text())}))
    rp=checkpoints.registry_path(run);r=json.loads(rp.read_text());r['schema_version']=4;r['checkpoints'][0].update(id='prepare-001',kind='preparation',checked_preparation=checkpoints._file_reference(p,run));r['current']='prepare-001';rp.write_text(json.dumps(r))
    assert load(prepared,expected_checkpoint_id='prepare-001')['context']['checkpoint_id']=='prepare-001'


@pytest.mark.parametrize('field',['model_context','restraint_context','literal_na_inputs'])
def test_missing_authority_is_reported_not_invented(prepared,field):
    p=prepared['checked'].request_directory/'request.json';d=json.loads(p.read_text());d['configuration'].pop(field);p.write_text(json.dumps(d))
    pub=prepared['run']/'PostMR/report.json';v=json.loads(pub.read_text());v['checked_preparation']['request']=checkpoints._file_reference(p,prepared['run']);pub.write_text(json.dumps(v))
    cp=checkpoints.registry_path(prepared['run']);r=json.loads(cp.read_text());r['checkpoints'][0]['checked_preparation']=checkpoints._file_reference(pub,prepared['run']);cp.write_text(json.dumps(r))
    prepared['exact'].pop(field,None)
    assert load(prepared)['availability'][field]['status']=='UNAVAILABLE'


@pytest.mark.parametrize('target',['model','publication','request','result','registry','report'])
def test_owner_side_input_change_is_refused(prepared,target):
    original=prepared['reader'];run=prepared['run']
    paths=dict(model=prepared['checked'].model_path,publication=run/'PostMR/report.json',request=prepared['checked'].request_directory/'request.json',result=prepared['checked'].report_path,registry=checkpoints.registry_path(run),report=run/'report.json')
    def changed(path):
        value=original(path);p=paths[target];p.write_bytes(p.read_bytes()+b'\n');return value
    with pytest.raises(ValueError,match='changed'):load(prepared,preparation_reader=changed)


@pytest.mark.parametrize('change',['wrong_result','wrong_model','compiler_disagreement'])
def test_unrelated_owner_result_cannot_supply_fields(prepared,change):
    if change=='wrong_result':prepared['exact']['result']={'status':'OTHER'}
    elif change=='wrong_model':prepared['checked'].model_path=prepared['run']/'data.mtz'
    else:prepared['exact'].pop('literal_na_inputs')
    with pytest.raises(ValueError):load(prepared)


def test_missing_owner_fails_clearly(prepared):
    if hasattr(checkpoints,'_read_registry_with_preparations'):pytest.skip('Cedar reader installed')
    with pytest.raises(RuntimeError,match='Cedar'):load(prepared,preparation_reader=None)


def test_old_path_gone_relocation_preserves_summary(prepared,tmp_path):
    before=load(prepared);old=prepared['run'];new=tmp_path/'relocated/AutoMR/run_001';new.parent.mkdir(parents=True);shutil.move(str(old),new)
    c=prepared['checked']
    for field in ('run_directory','request_directory','model_path','report_path'):
        setattr(c,field,new/getattr(c,field).relative_to(old))
    c.restraint_paths=tuple(new/p.relative_to(old) for p in c.restraint_paths);prepared['run']=new
    assert not old.exists() and load(prepared)==before


def test_legacy_missing_preparation_is_explicit_unavailable(prepared):
    p=checkpoints.registry_path(prepared['run']);r=json.loads(p.read_text());r['schema_version']=2;r['checkpoints'][0].pop('checked_preparation');p.write_text(json.dumps(r))
    def reader(path):return path,json.loads(p.read_text()),None
    result=load(prepared,preparation_reader=reader)
    assert result['status']=='NO_CHECKED_PREPARATION'
    assert all(v['status']=='UNAVAILABLE' for v in result['availability'].values())
    assert not result['motion_admission']


def test_context_pin_refuses_new_report_even_with_identical_model(prepared):
    pin=load(prepared)['context_sha256'];p=prepared['run']/'report.json';p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='context changed'):load(prepared,expected_context_sha256=pin)
