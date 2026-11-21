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


@pytest.fixture
def typed_preparation(tmp_path):
    from types import SimpleNamespace
    from nasolve.topostitch_recipe import recipe_digest
    parent=tmp_path/'parent.pdb';parent.write_bytes(b'exact parent')
    restraint=tmp_path/'restraint.phil';restraint.write_bytes(b'restraints')
    control=tmp_path/'control.phil';control.write_bytes(b'controls')
    keys=('pdb_interpretation.sort_atoms','pdb_interpretation.restraints_library.cdl',
          'pdb_interpretation.restraints_library.cdl_nucleotides.enable',
          'pdb_interpretation.use_ncs_to_build_restraints')
    report=dict(policy_id='cif-typed-native-literal-inputs-v1',authority='original capture',
                execution_context=dict(ordinary_handoff_allowed=False))
    value=dict(report=report,model=parent,phils=[restraint],
               compiled_restraint_phils=[restraint],interpretation_control_phils=[control])
    calls=[]
    def read(kind,directory,*,reader_control_policy):
        assert kind=='literal_na_inputs' and directory==tmp_path
        assert reader_control_policy=='cif-captured-reader-control-handoff-v1'
        calls.append('read');return value
    def definitions(data,seen):
        assert data==b'controls' and not seen;seen.update(keys)
        calls.append('controls');return {k:False for k in keys},[]
    def shadows(paths):assert paths==[restraint];calls.append('shadows')
    compiler=SimpleNamespace(_compiler_input=read)
    controls=SimpleNamespace(POLICY_ID='cif-captured-reader-control-handoff-v1',
        CONTROLS=frozenset(keys),control_definitions=definitions,reject_shadow_controls=shadows)
    return SimpleNamespace(root=tmp_path,parent=parent,restraint=restraint,control=control,
        report=report,value=value,compiler=compiler,controls=controls,calls=calls,
        report_pin=recipe_digest(report))


def bind_typed(s,**kw):
    from nasolve.topostitch_native_preparation import bind_native_preparation_inputs
    options=dict(expected_report_sha256=s.report_pin,compiler_owner=s.compiler,controls_owner=s.controls)
    options.update(kw)
    return bind_native_preparation_inputs(s.root,b'exact parent',**options)


def test_typed_preparation_binding_is_detached_without_runtime_authority(typed_preparation):
    from dataclasses import FrozenInstanceError
    import json
    s=typed_preparation;bound=bind_typed(s)
    assert bound.parent_bytes==b'exact parent'
    assert bound.compiled_restraint_phils==(b'restraints',)
    assert bound.interpretation_control_phils==(b'controls',)
    assert dict(bound.reader_controls)=={k:False for k in s.controls.CONTROLS}
    assert bound.report_sha256==s.report_pin
    assert json.loads(bound.source_report_json)==s.report
    assert bound.runtime_authority is False and bound.chemical_admission is False
    assert s.calls==['read','controls','shadows','read']
    s.restraint.write_bytes(b'new');s.report['authority']='changed'
    assert bound.compiled_restraint_phils==(b'restraints',)
    assert json.loads(bound.source_report_json)['authority']=='original capture'
    with pytest.raises(FrozenInstanceError):bound.parent_bytes=b'new'


@pytest.mark.parametrize('fault',['parent','report_pin','report_policy','owner_policy','alias_role',
    'combined_controls','missing_role','missing_control','nonboolean_control','true_control',
    'shadow','file_race','report_race','role_race'])
def test_typed_preparation_binding_refuses_mismatched_or_changed_sources(typed_preparation,fault):
    from nasolve.topostitch_recipe import recipe_digest
    s=typed_preparation
    if fault=='parent':s.parent.write_bytes(b'other parent')
    elif fault=='report_pin':s.report_pin='0'*64
    elif fault=='report_policy':
        s.report['policy_id']='old untyped';s.report_pin=recipe_digest(s.report)
    elif fault=='owner_policy':s.controls.POLICY_ID='different'
    elif fault=='alias_role':s.value['interpretation_control_phils']=[s.restraint]
    elif fault=='combined_controls':s.value['phils'].append(s.control)
    elif fault=='missing_role':s.value['interpretation_control_phils']=[]
    elif fault in ('missing_control','nonboolean_control','true_control'):
        original=s.controls.control_definitions
        def changed(*args):
            values,mappings=original(*args);key=sorted(values)[0]
            if fault=='missing_control':values.pop(key)
            else:values[key]=0 if fault=='nonboolean_control'else True
            return values,mappings
        s.controls.control_definitions=changed
    elif fault=='shadow':
        def fail(paths):raise ValueError('conflicting shadow setting')
        s.controls.reject_shadow_controls=fail
    else:
        original=s.compiler._compiler_input
        def changed(*args,**kw):
            result=original(*args,**kw)
            if s.calls.count('read')==2:
                if fault=='file_race':s.restraint.write_bytes(b'changed')
                elif fault=='report_race':s.report['authority']='changed'
                else:result['compiled_restraint_phils']=[s.control]
            return result
        s.compiler._compiler_input=changed
    with pytest.raises(ValueError):bind_typed(s)


@pytest.fixture
def typed_source_observation(typed_preparation):
    from nasolve.topostitch_recipe import recipe_digest
    s=typed_preparation
    s.native=s.root/'native/native_validation.json';s.native.parent.mkdir()
    s.native_bytes=b'{"status":"REVIEW","original":"site definitions"}\n'
    s.native.write_bytes(s.native_bytes)
    s.report['files']=[dict(anchor='literal_na_input_directory',path='native/native_validation.json',
        sha256=sha256(s.native_bytes).hexdigest(),size=len(s.native_bytes))]
    s.report_pin=recipe_digest(s.report)
    return s


def test_original_native_observation_is_opt_in_and_detached(typed_source_observation):
    s=typed_source_observation
    assert bind_typed(s).source_native_json is None
    bound=bind_typed(s,include_source_native=True)
    assert bound.source_native_json==s.native_bytes
    assert bound.report_sha256==s.report_pin
    assert bound.compiled_restraint_phils==(b'restraints',)
    assert bound.interpretation_control_phils==(b'controls',)
    assert bound.runtime_authority is False and bound.chemical_admission is False
    s.native.unlink()
    s.report['files'][0]['sha256']='0'*64
    assert bound.source_native_json==s.native_bytes
    assert json.loads(bound.source_report_json)['files'][0]['sha256']==sha256(s.native_bytes).hexdigest()


@pytest.mark.parametrize('fault',['missing','duplicate','anchor','path','size','digest','bytes',
    'outside','role_alias','byte_race','path_race','report_race'])
def test_source_observation_binding_refuses_ambiguous_or_changed_evidence(typed_source_observation,fault):
    from nasolve.topostitch_recipe import recipe_digest
    s=typed_source_observation;row=s.report['files'][0]
    if fault=='missing':s.report.pop('files')
    elif fault=='duplicate':s.report['files'].append(dict(row))
    elif fault=='anchor':row['anchor']='other'
    elif fault=='path':row['path']='another/native_validation.json'
    elif fault=='size':row['size']+=1
    elif fault=='digest':row['sha256']='0'*64
    elif fault=='bytes':s.native.write_bytes(b'changed')
    elif fault=='outside':
        outside=s.root.parent/(s.root.name+'-external.json');outside.write_bytes(s.native_bytes)
        s.native.unlink();s.native.symlink_to(outside)
    elif fault=='role_alias':
        s.value['compiled_restraint_phils']=[s.native];s.value['phils']=[s.native]
    else:
        original=s.compiler._compiler_input
        def changed(*args,**kw):
            result=original(*args,**kw)
            if s.calls.count('read')==2:
                if fault=='byte_race':s.native.write_bytes(b'changed after binding')
                elif fault=='path_race':
                    new=s.root/'other.json';new.write_bytes(s.native_bytes)
                    s.native.rename(s.root/'preserved.json');s.native.symlink_to(new)
                else:row['sha256']='0'*64
            return result
        s.compiler._compiler_input=changed
    s.report_pin=recipe_digest(s.report)
    with pytest.raises(ValueError):bind_typed(s,include_source_native=True)


@pytest.mark.parametrize('option',[1,None,'yes'])
def test_source_observation_opt_in_requires_boolean(typed_preparation,option):
    with pytest.raises(ValueError):bind_typed(typed_preparation,include_source_native=option)
    assert not typed_preparation.calls


@pytest.fixture
def parent_builder():
    """Owner doubles exercise orchestration, not native chemistry qualification."""
    from nasolve.topostitch_native_preparation import NativePreparationInputs, SourceBoundParentBuilder
    state=SimpleNamespace(model=SimpleNamespace(restraints_manager=None),diffraction={'F':[1,2]},
        protected={'model_noncoordinate':{'atoms':['A'], 'scattering':['C'], 'crystal':[1]},'fixed_geometry_inputs':None},
        view={'topology':{'link_status':'MATCH','links':[]},'native_view':{'geometry':{'proxy_details':{'bond':[1]},'custom_proxy_requests':[2]}}},calls=[])
    bound=NativePreparationInputs(b'parent',b'{}',(b'geometry',),(b'controls',),(), 'test',b'original native')
    def interpret(model,inputs,**kw):
        state.calls.append('interpret')
        assert model is state.model and kw['source_native_json']==b'original native'
        if getattr(state,'failure',False):raise RuntimeError('original service error')
        model.restraints_manager=SimpleNamespace(geometry=object());state.protected['fixed_geometry_inputs']={'exclusions':[1]}
        receipt=dict(policy_id='cif-native-parent-interpretation-v1',source_report_sha256=sha256(b'{}').hexdigest(),parent_sha256=sha256(b'parent').hexdigest(),native_interpretations=1,source_chemistry=dict(status='MATCH',source_native_sha256=sha256(b'original native').hexdigest(),scientific_acceptance=False),chemical_admission=False,ordinary_handoff_allowed=False)
        if getattr(state,'bad_chemistry',False):receipt['source_chemistry']['status']='DIFFERENT'
        return SimpleNamespace(processed=object(),native_result='native-return',receipt=receipt)
    def geometry(model,processed,payload):
        state.calls.append(payload.decode());assert model is state.model and processed is not None
        return state.view
    def writer(model,points):state.calls.append('write');state.points=points
    args=dict(model=state.model,bound_inputs=bound,expected_report_sha256=sha256(b'{}').hexdigest(),candidate_bytes=b'candidate',service=SimpleNamespace(interpret=interpret),process_options={'make_restraints':True},
        atom_reader=lambda model:{'atoms':[]},geometry_reader=geometry,protected_reader=lambda model:state.protected,diffraction_reader=lambda:state.diffraction,coordinate_writer=writer)
    state.args=args;state.builder=SourceBoundParentBuilder(**args);return state


def prepare_builder(s):
    s.builder.interpret_parent(s.model,b'parent');s.builder.verify_parent(s.model,None)


def finish_builder(s):
    s.builder.set_candidate_sites(s.model,((1,2,3),));s.builder.verify_candidate(s.model,None,None)


def test_source_bound_builder_requires_source_match_and_retains_evidence(parent_builder):
    s=parent_builder
    with pytest.raises(RuntimeError):s.builder.result()
    prepare_builder(s);finish_builder(s)
    assert s.builder.result().native_result=='native-return'
    r=s.builder.evidence();assert r['status']=='COMPLETE'and not r['runtime_authority']
    assert s.calls==['interpret','parent','write','candidate']
    s.view['topology']['links'].append('later mutation');s.diffraction['F'].append(3)
    assert s.builder.evidence()==r


@pytest.mark.parametrize('fault',['no_native','wrong_report','wrong_parent','wrong_chemistry','service_error','diffraction_parent','noncoordinate_parent','topology','geometry_missing','empty_protected','nan_snapshot'])
def test_source_bound_builder_refuses_before_transfer(parent_builder,fault):
    from dataclasses import replace
    from nasolve.topostitch_native_preparation import SourceBoundParentBuilder
    s=parent_builder
    if fault in ('no_native','wrong_report','wrong_parent'):
        args=dict(s.args)
        if fault=='no_native':args['bound_inputs']=replace(args['bound_inputs'],source_native_json=None)
        elif fault=='wrong_report':args['expected_report_sha256']='0'*64
        else:args['bound_inputs']=replace(args['bound_inputs'],parent_bytes=b'wrong')
        if fault=='wrong_parent':
            # Wrong parent is rejected when the service receipt names the original.
            s.builder=SourceBoundParentBuilder(**args)
            with pytest.raises((ValueError,AssertionError)):s.builder.interpret_parent(s.model,b'wrong')
        else:
            with pytest.raises(ValueError):SourceBoundParentBuilder(**args)
    else:
        if fault=='wrong_chemistry':s.bad_chemistry=True
        if fault=='service_error':s.failure=True
        if fault=='nan_snapshot':s.diffraction['F']=[float('nan')]
        if fault in ('wrong_chemistry','service_error','nan_snapshot'):
            with pytest.raises((ValueError,RuntimeError)):s.builder.interpret_parent(s.model,b'parent')
        else:
            s.builder.interpret_parent(s.model,b'parent')
            if fault=='diffraction_parent':s.diffraction['F'].append(99)
            elif fault=='noncoordinate_parent':s.protected['model_noncoordinate']['atoms']=['changed']
            elif fault=='topology':s.view['topology']['link_status']='DIFFERENT'
            elif fault=='geometry_missing':s.view['native_view']['geometry'].pop('proxy_details')
            elif fault=='empty_protected':s.protected['fixed_geometry_inputs']=None
            with pytest.raises((ValueError,KeyError)):s.builder.verify_parent(s.model,None)
    assert 'write'not in s.calls
    with pytest.raises(RuntimeError):s.builder.result()


@pytest.mark.parametrize('fault',['diffraction','noncoordinate','fixed_geometry','proxy','custom','topology','geometry_object','foreign_model'])
def test_source_bound_builder_refuses_changed_transfer_state(parent_builder,fault):
    s=parent_builder;prepare_builder(s);s.builder.set_candidate_sites(s.model,((1,2,3),))
    if fault=='diffraction':s.diffraction['F'].append(99)
    elif fault=='noncoordinate':s.protected['model_noncoordinate']['atoms']=['changed']
    elif fault=='fixed_geometry':s.protected['fixed_geometry_inputs']['exclusions']=[2]
    elif fault=='proxy':s.view['native_view']['geometry']['proxy_details']['bond'].append(3)
    elif fault=='custom':s.view['native_view']['geometry']['custom_proxy_requests'].append(3)
    elif fault=='topology':s.view['topology']['links'].append('unexpected')
    elif fault=='geometry_object':s.model.restraints_manager.geometry=object()
    model=object()if fault=='foreign_model'else s.model
    with pytest.raises(ValueError):s.builder.verify_candidate(model,None,None)
    with pytest.raises(RuntimeError):s.builder.result()


@pytest.mark.parametrize('method',['verify_parent','set_candidate_sites','verify_candidate'])
def test_source_bound_builder_rejects_out_of_order_and_invalidates(parent_builder,method):
    s=parent_builder;args=(s.model,None,None)if method=='verify_candidate'else(s.model,None)
    with pytest.raises(RuntimeError):getattr(s.builder,method)(*args)
    with pytest.raises(RuntimeError,match='failed'):s.builder.interpret_parent(s.model,b'parent')


def test_source_bound_builder_reuse_invalidates_result(parent_builder):
    s=parent_builder;prepare_builder(s);finish_builder(s)
    with pytest.raises(RuntimeError):s.builder.interpret_parent(s.model,b'parent')
    with pytest.raises(RuntimeError):s.builder.result()


@pytest.mark.parametrize('stage',['parent','candidate'])
def test_source_bound_builder_catches_reader_side_effects(parent_builder,stage):
    s=parent_builder;original=s.builder._review
    def changed(*args):
        result=original(*args);s.protected['model_noncoordinate']['scattering'].append('changed ADP')
        return result
    if stage=='parent':
        s.builder.interpret_parent(s.model,b'parent');s.builder._review=changed
        with pytest.raises(ValueError,match='observer'):s.builder.verify_parent(s.model,None)
        assert 'write'not in s.calls
    else:
        prepare_builder(s);s.builder.set_candidate_sites(s.model,((1,2,3),));s.builder._review=changed
        with pytest.raises(ValueError,match='observer'):s.builder.verify_candidate(s.model,None,None)
    with pytest.raises(RuntimeError):s.builder.result()
