"""Qualified component reuse is independent of a later crystal's coordinates."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from tests.test_cif_candidate_usability import native_case


def inputs(tmp_path):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_dictionary_store import make_dictionary_request
    s, c, m, native = native_case(tmp_path)
    q = qualify_candidate_native(s, c, m, 'Q17', native)
    assert q['native_usable']
    options = dict(source_authority='EXPLICIT', recipe={'policy_id':'TEST_REPAIR', 'sha256':'1'*64},
        generator={'name':'EXPLICIT_FAKE_BUILDER', 'version':'TEST', 'sha256':'2'*64},
        consumer={'name':'EXPLICIT_FAKE_CONSUMER', 'version':'TEST', 'sha256':'3'*64})
    request = make_dictionary_request(s, 'Q17', **{k:v for k,v in options.items() if k != 'consumer'})
    provenance = {'stopping':'NOT_CONVERGED_REPORTED', 'converged':False,
        'notes':['TEST: finite usable candidate, iteration budget reached.'], 'evidence_sha256':'4'*64}
    return s, c, m, q, options, request, provenance


def publish(tmp_path):
    from nasolve.cif_dictionary_store import publish_dictionary
    s,c,m,q,o,request,p = inputs(tmp_path)
    entry = publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    return s,c,m,q,o,request,p,entry


def test_repeated_consumer_reuses_without_acquisition_or_optimization(tmp_path):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary, resolve_dictionary_snapshot
    s,c,m,q,o,request,p = inputs(tmp_path); calls=[]
    def acquire():
        calls.append('verified acquisition'); return dict(candidate=c, qualification=q, provenance=p)
    a = resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'run1', acquire=acquire, **o)
    m.write_text(m.read_text().replace('   0.000','   8.000'))
    def forbidden(): raise AssertionError('A cache hit must not call a builder')
    b = resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'run2', acquire=forbidden, **o)
    assert calls == ['verified acquisition'] and a['status']=='PREPARED_AND_FROZEN' and b['status']=='REUSED'
    assert a['entry_id']==b['entry_id'] and b['requires_cif_review'] is False
    assert b['converged'] is False and 'iteration budget' in ' '.join(b['notes'])
    assert b['linked_context']=='REQUALIFY_FOR_CURRENT_SITE' and b['model_geometry']=='ASSESS_FOR_NEW_MODEL'
    shutil.rmtree(tmp_path/'store'); s.unlink(); c.unlink()
    shutil.move(tmp_path/'run2', tmp_path/'relocated')
    result = resolve_dictionary_snapshot(tmp_path/'relocated')
    assert sha256(result['dictionary'].read_bytes()).hexdigest() == q['candidate_sha256']
    assert result['provenance']==p


@pytest.mark.parametrize('change',['source_bytes','charge','order','atom_name','stereo','authority','recipe','generator'])
def test_incompatible_sources_states_and_authorities_do_not_hit(tmp_path, change):
    from nasolve.cif_dictionary_store import make_dictionary_request, lookup_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path)
    if change=='source_bytes':s.write_text(s.read_text()+'# distinct authoritative source\n')
    if change in {'charge','order','atom_name','stereo'}:
        from nasolve.cif_linked_preparation import component_values,_render
        v=component_values(s,'Q17')
        if change=='charge':v['_chem_comp_atom.charge'][1]='-1'
        if change=='order':
            v['_chem_comp_bond.type'][0]='double';v['_chem_comp_bond.value_order'][0]='DOUB'
        if change=='atom_name':
            v={k:[('ALT' if x=='CTR' else x) for x in values] for k,values in v.items()}
        if change=='stereo':v['_chem_comp_atom.pdbx_stereo_config'][0]='S'
        s.write_text(_render(v,'Q17'))
    if change=='authority':o['source_authority']='CURATED'
    if change=='recipe':o['recipe']['sha256']='5'*64
    if change=='generator':o['generator']['name']='DIFFERENT_NUMERICAL_BACKEND'
    other=make_dictionary_request(s,'Q17',**{k:v for k,v in o.items() if k!='consumer'})
    assert other != request
    assert lookup_dictionary(tmp_path/'store',other,o['consumer'])['status']=='MISS'


def test_changed_consumer_requires_saved_dictionary_requalification_before_generation(tmp_path):
    from nasolve.cif_dictionary_store import lookup_dictionary, resolve_qualified_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path);o['consumer']['version']='NEW_TEST_VERSION'
    assert lookup_dictionary(tmp_path/'store',request,o['consumer'])['status']=='REQUALIFICATION_REQUIRED'
    def forbidden():raise AssertionError('Consumer changes must requalify saved numerics first')
    r=resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',acquire=forbidden,**o)
    assert r['status']=='REQUALIFICATION_REQUIRED' and not (tmp_path/'run').exists()
    calls=[]
    def requalify(source,candidate,consumer):
        assert candidate.read_bytes()==c.read_bytes() and source.read_bytes()==s.read_bytes()
        calls.append(consumer['version']);return deepcopy(q)
    r=resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',acquire=forbidden,requalify=requalify,**o)
    assert calls==['NEW_TEST_VERSION'] and r['status']=='REQUALIFIED_AND_FROZEN'


def test_new_native_qualification_policy_keeps_saved_numerics_available_for_requalification(tmp_path,monkeypatch):
    import nasolve.cif_candidate_usability as usability
    from nasolve.cif_dictionary_store import make_dictionary_request,lookup_dictionary,resolve_qualified_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path)
    monkeypatch.setattr(usability,'POLICY_ID','cif-isolated-candidate-native-usability-v3')
    newer=make_dictionary_request(s,'Q17',**{k:v for k,v in o.items() if k!='consumer'})
    assert newer == request
    result=lookup_dictionary(tmp_path/'store',newer,o['consumer'])
    assert result['status']=='REQUALIFICATION_REQUIRED' and result['entry_id']==e['entry_id']
    def forbidden():raise AssertionError('A native qualification policy update must not regenerate base numerics')
    result=resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',acquire=forbidden,**o)
    assert result['status']=='REQUALIFICATION_REQUIRED'


def test_combined_phenix_upgrade_requalifies_saved_bytes_before_using_the_new_builder(tmp_path):
    from nasolve.cif_dictionary_store import make_dictionary_request,lookup_dictionary,resolve_qualified_dictionary,resolve_dictionary_snapshot
    s,c,m,q,o,request,p,e=publish(tmp_path)
    o['generator']['version']='NEW_TEST_VERSION';o['generator']['sha256']='7'*64
    o['consumer']['version']='NEW_TEST_VERSION';o['consumer']['sha256']='8'*64
    newer=make_dictionary_request(s,'Q17',**{k:v for k,v in o.items() if k!='consumer'})
    result=lookup_dictionary(tmp_path/'store',newer,o['consumer'])
    assert result['status']=='REQUALIFICATION_REQUIRED' and result['entry_id']==e['entry_id']
    def forbidden():raise AssertionError('A combined tool upgrade must not regenerate before saved-numerics requalification')
    assert resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',acquire=forbidden,**o)['status']=='REQUALIFICATION_REQUIRED'
    r=resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',acquire=forbidden,
        requalify=lambda *args:deepcopy(q),**o)
    saved=resolve_dictionary_snapshot(tmp_path/'run')
    assert saved['manifest']['request']['generator']['version']=='TEST'
    assert saved['manifest']['consumer']['version']=='NEW_TEST_VERSION'


@pytest.mark.parametrize('defect',['candidate','source','component','policy','scope','status','unusable','empty_checks','missing_check','failed_check','inverted','nonfinite'])
def test_unusable_or_unbound_evidence_never_enters_reusable_store(tmp_path,defect):
    from nasolve.cif_dictionary_store import publish_dictionary
    s,c,m,q,o,request,p=inputs(tmp_path)
    if defect=='candidate':q['candidate_sha256']='0'*64
    if defect=='source':q['source_assessment']['finished_stereo']['source_sha256']='0'*64
    if defect=='component':q['component']='BAD'
    if defect=='policy':q['policy_id']='UNSUPPORTED'
    if defect=='scope':q['scope']='FULL_SCAFFOLD'
    if defect=='status':q['status']='REVIEW'
    if defect=='unusable':q['native_usable']=False
    if defect=='empty_checks':q['checks']={}
    if defect=='missing_check':q['checks'].pop('exact_active_bonds')
    if defect=='failed_check':q['checks']['exact_active_bonds']=False
    if defect=='inverted':q['source_assessment']['finished_stereo']['stereochemistry']='INVERTED'
    if defect=='nonfinite':p['energy']=float('nan')
    with pytest.raises(ValueError):publish_dictionary(tmp_path/'store',request,s,c,q,consumer=o['consumer'],provenance=p)
    assert not list((tmp_path/'store').glob('entries/*/*/manifest.json'))


@pytest.mark.parametrize('artifact',['source.cif','dictionary.cif','qualification.json','provenance.json','manifest.json'])
def test_corrupt_entries_are_not_hits_and_are_never_overwritten(tmp_path,artifact):
    from nasolve.cif_dictionary_store import publish_dictionary,lookup_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path)
    original=e['directory']/artifact; original.write_bytes(original.read_bytes()+b'CORRUPTED')
    before=original.read_bytes()
    assert lookup_dictionary(tmp_path/'store',request,o['consumer'])['status']=='MISS'
    with pytest.raises(ValueError):publish_dictionary(tmp_path/'store',request,s,c,q,consumer=o['consumer'],provenance=p)
    assert original.read_bytes()==before


def test_duplicate_publication_is_immutable_and_partial_staging_is_not_visible(tmp_path):
    from nasolve.cif_dictionary_store import publish_dictionary,lookup_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path)
    before={x.name:x.read_bytes() for x in e['directory'].iterdir()}
    again=publish_dictionary(tmp_path/'store',request,s,c,q,consumer=o['consumer'],provenance=p)
    assert e['entry_id']==again['entry_id'] and before=={x.name:x.read_bytes() for x in e['directory'].iterdir()}
    partial=tmp_path/'store'/'pending'/'interrupted';partial.mkdir(parents=True);(partial/'dictionary.cif').write_bytes(b'NO')
    assert lookup_dictionary(tmp_path/'store',request,o['consumer'])['entry_id']==e['entry_id']


@pytest.mark.parametrize('kind',['entry','dictionary','key'])
def test_cache_symlinks_never_substitute_scientific_bytes(tmp_path,kind):
    from nasolve.cif_dictionary_store import lookup_dictionary
    s,c,m,q,o,request,p,e=publish(tmp_path)
    target=e['directory'] if kind=='entry' else e['directory']/'dictionary.cif' if kind=='dictionary' else e['directory'].parent
    moved=tmp_path/'moved';target.rename(moved);target.symlink_to(moved,target_is_directory=kind!='dictionary')
    assert lookup_dictionary(tmp_path/'store',request,o['consumer'])['status']=='MISS'


def test_read_only_store_failure_retains_fresh_usable_run_snapshot(tmp_path,monkeypatch):
    import nasolve.cif_dictionary_store as cache
    s,c,m,q,o,request,p=inputs(tmp_path)
    monkeypatch.setattr(cache,'publish_dictionary',lambda *a,**k:(_ for _ in ()).throw(PermissionError('TEST read-only store')))
    r=cache.resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',
        acquire=lambda:dict(candidate=c,qualification=q,provenance=p),**o)
    assert r['status']=='PREPARED_AND_FROZEN' and r['persistent_store']=='UNAVAILABLE'
    assert cache.resolve_dictionary_snapshot(tmp_path/'run')['dictionary'].read_bytes()==c.read_bytes()


@pytest.mark.parametrize('platform,env,ending',[('darwin',{},'Library/Application Support/NASolve/cif-dictionaries/v1'),
    ('linux',{},'.local/share/nasolve/cif-dictionaries/v1'),('linux',{'XDG_DATA_HOME':'/explicit/data'},'nasolve/cif-dictionaries/v1'),
    ('win32',{'LOCALAPPDATA':'/explicit/local'},'NASolve/cif-dictionaries/v1')])
def test_platform_default_is_user_local_app_data(tmp_path,platform,env,ending):
    from nasolve.cif_dictionary_store import default_dictionary_store
    p=default_dictionary_store(environ=env,home=tmp_path,platform=platform)
    assert p.as_posix().endswith(ending)
    assert default_dictionary_store(environ={'NASOLVE_CIF_STORE':str(tmp_path/'explicit')},home=tmp_path,platform=platform)==tmp_path/'explicit'


@pytest.mark.parametrize('overlap',['same','inside_store','contains_store'])
def test_run_snapshot_cannot_depend_on_the_cache_directory(tmp_path,overlap):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary
    s,c,m,q,o,request,p=inputs(tmp_path);store=tmp_path/'store'
    output=store if overlap=='same' else store/'run' if overlap=='inside_store' else tmp_path/'enclosing'
    if overlap=='contains_store':store=output/'store'
    with pytest.raises(ValueError,match='separate'):
        resolve_qualified_dictionary(s,'Q17',store,output,acquire=lambda:pytest.fail('must validate before acquisition'),**o)


@pytest.mark.parametrize('field,value',[('model_geometry','PASS'),('linked_context','PASS'),
    ('requires_cif_review',True),('production_adoption','COMPLETED'),('stopping','CONVERGED'),('notes',[])])
def test_snapshot_cannot_upgrade_evidence_or_erase_original_notes(tmp_path,field,value):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary,resolve_dictionary_snapshot
    s,c,m,q,o,request,p=inputs(tmp_path)
    resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'run',
        acquire=lambda:dict(candidate=c,qualification=q,provenance=p),**o)
    path=tmp_path/'run/resolution.json';report=json.loads(path.read_bytes());report[field]=value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):resolve_dictionary_snapshot(tmp_path/'run')
