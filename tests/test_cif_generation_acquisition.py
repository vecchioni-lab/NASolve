"""Cache ordering and owned generation are separate from chemical qualification."""
from copy import deepcopy
from hashlib import sha256
import json
import os
import shutil

import pytest

from tests.test_cif_dictionary_store import inputs
from tests.test_cif_generation_attempt import inventory


@pytest.fixture
def case(tmp_path, monkeypatch):
    from nasolve import cif_generation_acquisition as module
    import nasolve.cif_generation_attempt as attempts
    s, c, m, q, options, request, provenance = inputs(tmp_path)
    sdk=tmp_path/'sdk';sdk.mkdir()
    for name in ('python','elbow','api.py'):(sdk/name).write_text(name)
    pin={'anchor':'phenix_installation','path':'api.py','sha256':sha256(b'api.py').hexdigest(),'size':6}
    generation=dict(installation_root=sdk,python_executable=sdk/'python',elbow_executable=sdk/'elbow',
        api_sources=[pin],prior_sources=[pin],environment=dict(os.environ),expected_dialect='CHEMICAL_COMPONENTS_CIF',
        phenix_version='SYNTHETIC',single_block_steps=12,timeout_seconds=5,max_attempts=2)
    calls=[]
    def generate(root,python,elbow,api,source,code,output,**kwargs):
        calls.append('generate');output.mkdir()
        candidate=output/'candidate.cif';candidate.write_bytes(c.read_bytes())
        report={'schema_version':1,'status':'CANDIDATE_REVIEW','component':code,
            'source_sha256':sha256(source.read_bytes()).hexdigest(),'source_preserved':True,
            'candidate_retained':True,'candidate':{'anchor':'candidate_directory','path':'candidate.cif',
                'sha256':sha256(candidate.read_bytes()).hexdigest(),'size':candidate.stat().st_size},
            'execution':{'status':'TIMED_OUT'},'stopping':{'status':'ITERATION_LIMIT','convergence_claimed':False}}
        (output/'source_candidate_receipt.json').write_text(json.dumps(report))
        return report
    monkeypatch.setattr(attempts,'generate_source_candidate',generate)
    def qualify(source,candidate,consumer,output):
        calls.append('qualify');assert not output.exists()
        assert source.read_bytes()==s.read_bytes() and candidate.read_bytes()==c.read_bytes()
        output.mkdir();(output/'native-evidence.json').write_text('synthetic fixture only')
        return deepcopy(q)
    args=(s,'Q17',tmp_path/'store',tmp_path/'snapshot',tmp_path/'request',tmp_path/'qualification')
    kwargs=dict(source_authority='EXPLICIT',consumer=options['consumer'],generation=generation,qualify=qualify)
    return module,args,kwargs,calls,c,q


def test_miss_generates_once_then_qualified_hit_never_enters_sdk_or_adapters(case):
    module,args,kwargs,calls,c,q=case
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    first=module.resolve_generated_dictionary(*args,**kwargs)
    assert first['status']=='PREPARED_AND_FROZEN' and calls==['generate','qualify']
    saved=resolve_dictionary_snapshot(args[3]);p=saved['provenance']
    assert p['converged'] is False and p['stopping']=='ITERATION_LIMIT'
    assert p['generation_acquisition']['attempt_number']==1
    assert p['generation_acquisition']['consumer']==kwargs['consumer']
    before=inventory(args[4]);shutil.rmtree(kwargs['generation']['installation_root'])
    kwargs['qualify']=lambda *a:pytest.fail('cache hit must not qualify')
    again=module.resolve_generated_dictionary(*args[:3],args[3].with_name('second'),args[4],args[5].with_name('unused'),**kwargs)
    assert again['status']=='REUSED' and again['entry_id']==first['entry_id']
    assert calls==['generate','qualify'] and inventory(args[4])==before
    assert not args[5].with_name('unused').exists()


def test_absent_qualifier_miss_does_not_generate_or_create_any_workspace(case):
    module,args,kwargs,calls,*_=case
    kwargs['qualify']=None
    before=inventory(args[0].parent)
    result=module.resolve_generated_dictionary(*args,**kwargs)
    assert result['status']=='MISS' and calls==[] and inventory(args[0].parent)==before
    assert not args[4].exists() and not args[5].exists()


def test_stale_consumer_requalifies_original_numerics_before_any_generation(case):
    module,args,kwargs,calls,*_=case
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    module.resolve_generated_dictionary(*args,**kwargs)
    old=resolve_dictionary_snapshot(args[3]);before=inventory(args[4])
    kwargs['consumer']['version']='NEW_CONSUMER'
    kwargs['generation']['phenix_version']='NEW_PRODUCER'
    shutil.rmtree(kwargs['generation']['installation_root'])
    result=module.resolve_generated_dictionary(*args[:3],args[3].with_name('second'),args[4],args[5].with_name('qual2'),**kwargs)
    new=resolve_dictionary_snapshot(args[3].with_name('second'))
    assert result['status']=='REQUALIFIED_AND_FROZEN' and calls==['generate','qualify','qualify']
    assert new['manifest']['request']['generator']==old['manifest']['request']['generator']
    assert new['manifest']['consumer']['version']=='NEW_CONSUMER' and inventory(args[4])==before


@pytest.mark.parametrize('defect',['unusable','wrong_source','wrong_candidate','inverted','mutate_source','mutate_candidate','mutate_consumer','raise'])
def test_failed_qualification_never_publishes_or_damages_originals(case,defect):
    module,args,kwargs,calls,c,q=case
    original_source=args[0].read_bytes();original_candidate=c.read_bytes()
    def qualify(source,candidate,consumer,output):
        result=deepcopy(q)
        if defect=='unusable':result['native_usable']=False
        elif defect=='wrong_source':result['source_assessment']['finished_stereo']['source_sha256']='0'*64
        elif defect=='wrong_candidate':result['candidate_sha256']='0'*64
        elif defect=='inverted':result['source_assessment']['finished_stereo']['stereochemistry']='INVERTED'
        elif defect=='mutate_source':source.write_text('CORRUPT')
        elif defect=='mutate_candidate':candidate.write_text('CORRUPT')
        elif defect=='mutate_consumer':consumer['version']='WRONG'
        else:raise RuntimeError('synthetic native failure')
        return result
    kwargs['qualify']=qualify
    with pytest.raises((ValueError,RuntimeError)):module.resolve_generated_dictionary(*args,**kwargs)
    assert args[0].read_bytes()==original_source and c.read_bytes()==original_candidate
    assert not args[3].exists() and not args[2].exists()
    assert (args[4]/'attempts/attempt-0001/finished.json').is_file()
    assert (args[5]/'inputs/dictionary.cif').exists()


@pytest.mark.parametrize('obstacle',['snapshot_symlink','qualification_symlink','request_symlink','snapshot_file','qual_existing','overlap'])
def test_invalid_destinations_refuse_before_generation(case,obstacle):
    module,args,kwargs,calls,*_=case;args=list(args)
    if obstacle.endswith('symlink'):
        target=args[0].parent/'external';target.mkdir();(target/'sentinel').write_text('keep')
        index={'snapshot_symlink':3,'qualification_symlink':5,'request_symlink':4}[obstacle]
        args[index].symlink_to(target,target_is_directory=True)
    elif obstacle=='snapshot_file':args[3].parent.joinpath('file').write_text('keep');args[3]=args[3].parent/'file'/'snapshot'
    elif obstacle=='qual_existing':args[5].mkdir()
    else:args[5]=args[4]/'nested'
    before=inventory(args[0].parent)
    with pytest.raises((ValueError,FileExistsError)):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and inventory(args[0].parent)==before


@pytest.mark.parametrize('defect',['missing','bad_hash','wrong_component','wrong_source'])
def test_generation_receipt_cannot_substitute_unbound_candidate(case,monkeypatch,defect):
    module,args,kwargs,calls,*_=case
    import nasolve.cif_generation_attempt as attempts
    original=attempts.generate_source_candidate
    def generate(*a,**k):
        r=original(*a,**k)
        if defect=='missing':r['candidate']=None;r['candidate_retained']=False
        elif defect=='bad_hash':r['candidate']['sha256']='0'*64
        elif defect=='wrong_component':r['component']='BAD'
        elif defect=='wrong_source':r['source_sha256']='0'*64
        (a[6]/'source_candidate_receipt.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(attempts,'generate_source_candidate',generate)
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==['generate'] and not args[3].exists() and not args[5].exists()


def test_retained_candidate_after_failed_reporting_uses_complete_auditor(case,monkeypatch):
    module,args,kwargs,calls,c,q=case
    import nasolve.cif_generation_attempt as attempts
    from nasolve.cif_candidate_usability import qualify_candidate_native, reassess_complete_candidate
    from nasolve.cif_generation import inspect_component_generation
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_candidate_usability import native_case
    from tests.test_cif_stereochemistry_audit import write
    fixture=args[0].parent/'both-volume';fixture.mkdir()
    s2,c2,m2,n2=native_case(fixture)
    left,right=_values(s2,'Q17'),_values(c2,'Q17')
    left['_chem_comp_chir.volume_sign']=['both']
    left['_chem_comp_atom.pdbx_stereo_config'][0]=right['_chem_comp_atom.pdbx_stereo_config'][0]='N'
    right={k:v for k,v in right.items() if not k.startswith('_chem_comp_chir.')}
    n2['monomer_mappings']['rows'][0]['metadata']['effective_definition']['chirality']=[]
    n2['geometry']['proxy_details']['chirality']=[];n2['geometry']['proxy_counts']['chirality']=0
    write(s2,left);write(c2,right)
    q2=qualify_candidate_native(s2,c2,m2,'Q17',n2)
    assert q2['native_usable'] and q2['checks']['omitted_unoriented_volume_coverage']
    assert inspect_component_generation(s2,c2,'Q17')['status']=='CANDIDATE_REVIEW'
    assert reassess_complete_candidate(s2,c2,'Q17')['candidate_status']=='CANDIDATE_REVIEW'
    args[0].write_bytes(s2.read_bytes());c.write_bytes(c2.read_bytes())
    def qualify(*a):calls.append('qualify');return deepcopy(q2)
    kwargs['qualify']=qualify
    original=attempts.generate_source_candidate
    def generate(*a,**k):
        r=original(*a,**k);r['status']='FAILED'
        r['error']='Synthetic post-write reporting failure; complete candidate retained'
        (a[6]/'source_candidate_receipt.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(attempts,'generate_source_candidate',generate)
    result=module.resolve_generated_dictionary(*args,**kwargs)
    assert result['status']=='PREPARED_AND_FROZEN' and calls==['generate','qualify']


def test_explicit_retries_share_attempt_allowance_and_preserve_failed_outputs(case):
    module,args,kwargs,calls,*_=case
    from nasolve.campaign_process import CampaignProcessError
    kwargs['qualify']=lambda *a:(_ for _ in ()).throw(ValueError('unqualified'))
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args,**kwargs)
    before=inventory(args[4]/'attempts/attempt-0001')
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args[:5],args[5].with_name('qual2'),**kwargs)
    assert before==inventory(args[4]/'attempts/attempt-0001')
    with pytest.raises(CampaignProcessError,match='exhausted'):
        module.resolve_generated_dictionary(*args[:5],args[5].with_name('qual3'),**kwargs)
    assert calls==['generate','generate'] and not args[5].with_name('qual3').exists()


def test_changed_recipe_cannot_reuse_generation_request_scope(case):
    module,args,kwargs,calls,*_=case
    kwargs['qualify']=lambda *a:(_ for _ in ()).throw(ValueError('unqualified'))
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args,**kwargs)
    before=inventory(args[4]);kwargs['generation']['single_block_steps']+=1
    with pytest.raises(ValueError,match='identity differs'):
        module.resolve_generated_dictionary(*args[:5],args[5].with_name('qual2'),**kwargs)
    assert before==inventory(args[4]) and calls==['generate']


def test_stale_failure_does_not_fall_through_to_regeneration(case):
    module,args,kwargs,calls,*_=case
    module.resolve_generated_dictionary(*args,**kwargs);before=inventory(args[2])
    kwargs['consumer']['version']='NEW'
    kwargs['qualify']=lambda *a:(_ for _ in ()).throw(ValueError('unqualified current consumer'))
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args[:3],args[3].with_name('second'),args[4],args[5].with_name('qual2'),**kwargs)
    assert calls==['generate','qualify'] and inventory(args[2])==before


def test_relocated_snapshot_survives_original_source_store_sdk_and_request_removal(case,tmp_path):
    module,args,kwargs,*_=case
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    module.resolve_generated_dictionary(*args,**kwargs)
    destination=tmp_path/'relocated';shutil.copytree(args[3],destination)
    expected=inventory(destination)
    for p in (args[2],args[3],args[4],args[5],kwargs['generation']['installation_root']):shutil.rmtree(p)
    args[0].unlink()
    saved=resolve_dictionary_snapshot(destination)
    assert saved['qualification']['native_usable'] is True and inventory(destination)==expected


@pytest.mark.parametrize('field,value', [('single_block_steps',0),('single_block_steps',True),
    ('timeout_seconds',0),('timeout_seconds',float('inf')),('max_attempts',0),('max_attempts',6),
    ('bond_representation_policy','UNSUPPORTED'),('expected_dialect',''),('phenix_version',''),('unknown_option',1)])
def test_invalid_generation_configuration_refuses_before_writes(case,field,value):
    module,args,kwargs,calls,*_=case
    kwargs['generation'][field]=value;before=inventory(args[0].parent)
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and inventory(args[0].parent)==before


@pytest.mark.parametrize('index',[2,3,4,5])
def test_no_acquisition_path_can_write_inside_selected_installation(case,index):
    module,args,kwargs,calls,*_=case;args=list(args)
    args[index]=kwargs['generation']['installation_root']/f'forbidden-{index}'
    before=inventory(kwargs['generation']['installation_root'])
    with pytest.raises(ValueError,match='installation'):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and before==inventory(kwargs['generation']['installation_root'])


def test_source_recipe_and_consumer_are_distinct_from_execution_allowance(case):
    module,args,kwargs,*_=case
    from nasolve.cif_dictionary_store import make_dictionary_request,_request_key
    def identity(g,authority='EXPLICIT'):
        return make_dictionary_request(args[0],'Q17',source_authority=authority,**module.generation_dictionary_options(g))
    initial=identity(kwargs['generation']);new=deepcopy(kwargs['generation'])
    new['timeout_seconds']=4;new['max_attempts']=1
    new['api_sources'][0]['snapshot']={'anchor':'old_capture','path':'ignored'}
    assert identity(new)==initial
    new['phenix_version']='UPGRADE'
    assert identity(new)!=initial and _request_key(identity(new))==_request_key(initial)
    new['single_block_steps']+=1
    assert _request_key(identity(new))!=_request_key(initial)
    assert _request_key(identity(kwargs['generation'],'CURATED'))!=_request_key(initial)


@pytest.mark.parametrize('policy', ['cif-source-declared-neutral-purine-aromatic-v1',
                                 'cif-source-declared-neutral-6-oxo-purine-aromatic-v1'])
def test_supported_representation_policies_reach_independent_native_qualification(case,tmp_path,policy):
    module,args,kwargs,calls,c,q=case
    from tests.test_cif_dictionary_policy import inputs as policy_inputs
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    folder=tmp_path/'policy-fixture';folder.mkdir()
    s2,c2,m2,n2,q2,*_=policy_inputs(folder,policy)
    args[0].write_bytes(s2.read_bytes());c.write_bytes(c2.read_bytes())
    kwargs['generation']['bond_representation_policy']=policy
    kwargs['qualify']=lambda source,candidate,consumer,out:deepcopy(q2)
    result=module.resolve_generated_dictionary(*args,**kwargs)
    assert result['status']=='PREPARED_AND_FROZEN'
    saved=resolve_dictionary_snapshot(args[3])
    assert saved['manifest']['request']['recipe']['bond_representation_policy']==policy
    assert saved['qualification']['policy_id']=='cif-isolated-candidate-native-usability-v3'


def test_generation_receipt_mutation_during_qualification_cannot_publish(case):
    module,args,kwargs,calls,*_=case;original=kwargs['qualify']
    def qualify(*a):
        q=original(*a)
        receipt=args[4]/'attempts/attempt-0001/generation/source_candidate_receipt.json'
        receipt.write_bytes(receipt.read_bytes()+b' ')
        return q
    kwargs['qualify']=qualify
    with pytest.raises(ValueError,match='completion'):module.resolve_generated_dictionary(*args,**kwargs)
    assert not args[2].exists() and not args[3].exists()


def test_candidate_chemical_damage_refuses_before_native_adapter(case):
    module,args,kwargs,calls,c,*_=case
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_stereochemistry_audit import write
    values=_values(c,'Q17');values['_chem_comp_atom.charge'][0]='1';write(c,values)
    with pytest.raises(ValueError,match='source chemistry'):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==['generate'] and not args[5].exists()


@pytest.mark.parametrize('stopping,expected',[('NOT_REPORTED',None),('NOT_CONVERGED_REPORTED',False),('ITERATION_LIMIT',False)])
def test_unknown_convergence_is_not_reported_as_nonconvergence_and_diagnostics_survive(case,monkeypatch,stopping,expected):
    module,args,kwargs,calls,*_=case
    import nasolve.cif_generation_attempt as attempts
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    original=attempts.generate_source_candidate
    def generate(*a,**k):
        r=original(*a,**k);r['stopping']={'status':stopping,'convergence_claimed':False,'trajectory':{'status':'SYNTHETIC'}}
        r['error']='Retained post-write diagnostic';r['diagnostic']={'stage':'ADAPTER','summary':r['error']}
        (a[6]/'source_candidate_receipt.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(attempts,'generate_source_candidate',generate)
    result=module.resolve_generated_dictionary(*args,**kwargs)
    saved=resolve_dictionary_snapshot(args[3]);evidence=saved['provenance']['generation_acquisition']
    assert result['converged'] is expected
    assert evidence['stopping_evidence']['status']==stopping
    assert evidence['stopping_evidence']['convergence_claimed'] is False
    assert evidence['diagnostic']=={'stage':'ADAPTER','summary':'Retained post-write diagnostic'}
    assert evidence['error']=='Retained post-write diagnostic'
    assert any('Retained post-write diagnostic' in n for n in result['notes'])
