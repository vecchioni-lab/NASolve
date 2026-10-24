from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template
from nasolve.cif_acquisition import REQUESTED_PAIRS


@pytest.mark.parametrize('defect',['none','build','action','parent','source','pair','stacks','report','native',
    'adoption','student','preserved','dispatcher','cache_selected','cache_hit','replay'])
def test_source_reuse_requires_exact_completed_c67(monkeypatch,defect):
    m=template();codes={c for p in REQUESTED_PAIRS for c in p}
    a={'policy_id':'cif-ordinary-source-acquisition-controls-v1','status':'ORDINARY_ACQUISITION_CONTROLS_PASS',
        'directory':{'anchor':'probe_directory','path':'ordinary_acquisition'},'dispatcher':{'execution':'NOT_RUN'},
        'policy_authority':'NARestraints','requires_cif_review':False,
        **{k:'NOT_RUN' for k in ['native_execution','dictionary_generation','model_editing','model_optimization','readyset_execution','production_adoption']},
        'sources':{c:{'status':'SOURCE_ACQUISITION_PASS'} for c in codes},
        'declared_pairs':[{'components':list(p),'status':'DECLARED_PAIR_AND_STACK_COMPILER_PASS',
            'stack_phils':[{},{}]} for p in REQUESTED_PAIRS]}
    for code in ['DP','PDU','5PC']:
        a['sources'][code]['saved_repair']={'lookup_status':'MISS','candidate_selected':False,'source_and_authority_exact':False}
    r={'build':{'EXPLICIT_FAKE':'C67'},'delivery_prefix':'67_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
        'status':'REVIEW','requested_action':'ORDINARY_SOURCE_ACQUISITION_PREFLIGHT',
        'prior_archive':{'sha256':'bd0369f2901ccb71fed7272e491e8afd611ec6e3689bad939f457fdedee496fc','verified_payloads':3659},
        'ordinary_acquisition_audit':a,'policy_authority':'NARestraints','automatic_adoption':False,'requires_cif_review':False,
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['native_execution','native_proxy_validation','linked_site_validation','model_editing','model_optimization',
            'dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval']}}
    m.CEDAR67_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar66_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar67_return',lambda x:defect!='replay',raising=False)
    if defect=='build':r['build']['OTHER']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='source':a['sources']['DP']['status']='REVIEW'
    if defect=='pair':a['declared_pairs'][2]['components']=['DP','DG']
    if defect=='stacks':a['declared_pairs'][2]['stack_phils']=[]
    if defect=='native':r['native_execution']='RAN'
    if defect=='adoption':a['production_adoption']='RAN'
    if defect=='student':r['requires_cif_review']=True
    if defect=='preserved':r['frozen_inputs_preserved']=False
    if defect=='dispatcher':a['dispatcher']['execution']='RAN'
    if defect=='cache_selected':a['sources']['DP']['saved_repair']['candidate_selected']=True
    if defect=='cache_hit':a['sources']['DP']['saved_repair']['lookup_status']='HIT'
    members={'probe_receipt.json':json.dumps(r).encode(),'ordinary_acquisition_audit.json':json.dumps(a).encode(),
        'ordinary_acquisition/acquisition.json':json.dumps({k:v for k,v in a.items() if k not in {'directory','dispatcher'}}).encode(),
        'inputs/review/probe_receipt.json':b'{}'}
    if defect=='report':members['ordinary_acquisition_audit.json']=b'{}'
    members.update({'padding/'+str(i):b'EXPLICIT_FAKE' for i in range(3713-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar67_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar67_members(members)


@pytest.mark.parametrize('action,delivery,valid',[('source_reuse_qualification_only','67_Cedar',True),
    ('ordinary_acquisition_only','67_Cedar',False),('source_reuse_qualification_only','66_Cedar',False)])
def test_source_reuse_action_is_explicit_and_isolated(action,delivery,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


@pytest.mark.parametrize('native_status,real_preflight',[('REVIEW',False),('FAILED',False),('FAILED',True),('NOT_RUN',False)])
def test_current_native_evidence_has_a_relocatable_directory(monkeypatch,tmp_path,native_status,real_preflight):
    """Exercise the actual action callback, including a failed native receipt."""
    from pathlib import Path
    import nasolve.cif_source_reuse as reuse
    import nasolve.cif_dictionary_store as store
    import nasolve.phenix_runtime as runtime
    import nasolve.cif_elbow_chirality as chirality
    import nasolve.cif_candidate_usability as usability
    import nasolve.cif_native_validation as native_api
    import nasolve.cif_triple_bond_audit as triple
    import nasolve.cif_review_transport as transport
    inspect_bundle=native_api.inspect_native_bundle
    m=template();session=tmp_path/'session';session.mkdir()
    root=tmp_path/'phenix';exe=root/'bin/phenix.ready_set';exe.parent.mkdir(parents=True);exe.write_text('EXPLICIT_FAKE')
    site=Path('lib/python3.11/site-packages')
    energy=[]
    for name in ['flags.py','energies.py','manager.py']:
        p=root/site/'cctbx/geometry_restraints'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('EXPLICIT_FAKE')
        energy.append({'historical_path':str(p),'sha256':sha256(p.read_bytes()).hexdigest()})
    phenix=SimpleNamespace(root=root,version='EXPLICIT_FAKE',executables={'phenix.python':exe},environment={})
    monkeypatch.setattr(runtime,'installation_from_candidate',lambda *a,**k:phenix)
    monkeypatch.setattr(m,'_fingerprints',lambda *a:[])
    monkeypatch.setattr(chirality,'_library_anchor',lambda *a:site)
    monkeypatch.setattr(store,'resolve_dictionary_snapshot',lambda p:{'manifest':{'request':{
        'recipe':{'policy_id':'EXPLICIT_FAKE'},'generator':{'name':'EXPLICIT_FAKE','version':'TEST'}},'consumer':{}}})
    def write_model(source,code,path):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text('EXPLICIT_FAKE_MODEL')
    monkeypatch.setattr(triple,'write_component_control_model',write_model)
    def triple_report(*a,dictionary=None,native=None):
        if (dictionary is None)==(native is None):raise ValueError('Require exactly one dictionary or native inventory')
        return {'scope':'EXPLICIT_FAKE'}
    monkeypatch.setattr(triple,'audit_triple_bonds',triple_report)
    monkeypatch.setattr(usability,'qualify_candidate_native',lambda *a:{
        'status':'EXPLICIT_FAKE_PASS','checks':{'EXPLICIT_FAKE':True}})
    launches=[]
    class FailedWorker:
        def __init__(self,command,**kwargs):
            launches.append(kwargs['cwd']);self.returncode=1
        def wait(self,timeout):return self.returncode
    if real_preflight:monkeypatch.setattr(native_api.subprocess,'Popen',FailedWorker)
    def inspect(model,cifs,output,*a,**k):
        if native_status=='NOT_RUN':raise ValueError('EXPLICIT_FAILED_PREFLIGHT')
        if real_preflight:return inspect_bundle(model,cifs,output,*a,**k)
        folder=output/'native-test';folder.mkdir(parents=True)
        return {'status':native_status,'source_preserved':True,'frozen_inputs_preserved':True,
            'native_directory':str(folder),'native_validation':{'energy_inventory':{'installed_sources':energy}},
            'execution':{'status':'COMPLETED' if native_status=='REVIEW' else 'FAILED','returncode':0 if native_status=='REVIEW' else 1}}
    monkeypatch.setattr(native_api,'inspect_native_bundle',inspect)
    inputs=tmp_path/'qualification_inputs';inputs.mkdir()
    for name in ['source.cif','candidate.cif']:(inputs/name).write_text('EXPLICIT_FAKE_INPUT')
    def resolve(code,dispatcher,cache,output,**kwargs):
        try:kwargs['qualify'](inputs/'source.cif',inputs/'candidate.cif',kwargs['consumer'])
        except ValueError:pass  # The ordinary resolver retains the source on native failure.
        return {'selected':'ordinary_source','status':'ORDINARY_SOURCE_FALLBACK',
            'source':{'authority':'CURATED','artifact':{'sha256':'1'*64}}}
    monkeypatch.setattr(reuse,'resolve_ordinary_dictionary',resolve)
    cases={c:{'first_snapshot':{'path':c+'/resolution.json'}} for c in ['DP','PDU','5PC']}
    members={'probe_receipt.json':json.dumps({'delivery_prefix':'67_Cedar'}).encode(),
        'inputs/review/dictionary_reuse_audit.json':json.dumps({'cases':cases}).encode(),
        'ordinary_acquisition_audit.json':json.dumps({'sources':{
            c:{'authority':'CURATED','source':{'sha256':'1'*64}} for c in cases}}).encode()}
    monkeypatch.setattr(transport,'read_staged_review_member',lambda folder,n:members[n])
    monkeypatch.setattr(m,'_review_zip',lambda p:p/'EXPLICIT_FAKE.zip')
    review=tmp_path/'review.zip';review.write_bytes(b'EXPLICIT_FAKE')
    args=SimpleNamespace(phenix_root=root,dictionary_store=tmp_path/'cache',inspect_only=False,timeout_seconds=60)
    receipt={}
    assert m._run_source_reuse_qualification_action(args,receipt,session,review,b'EXPLICIT_FAKE',members,tmp_path/'frozen',{}, {})==2
    report=receipt['source_reuse_audit'];assert report['native_attempts']==3
    if native_status=='NOT_RUN':
        assert report['new_native_calls']==0 and report['native_execution']=='NOT_RUN'
        assert receipt['native_proxy_validation']=='NOT_RUN'
        assert all(r['native']=={'status':'NOT_RUN'} for r in report['cases'].values())
        return
    assert report['new_native_calls']==3
    for code,row in report['cases'].items():
        ref=row['native']['directory']
        if native_status=='REVIEW':assert set(row['triple_screens'])=={'dictionary','native'}
        if not real_preflight:assert ref=={'anchor':'probe_directory','path':'source_reuse_native/'+code+'/readback/native-test'}
        assert (session/ref['path']).is_dir() and row['native']['native_directory']==str(session/ref['path'])
    if real_preflight:
        assert len(launches)==3
        assert report['native_attempts']==3 and report['new_native_calls']==3
        for row in report['cases'].values():
            n=row['native'];work=session/n['directory']['path']
            assert n['execution']['returncode']==1 and n['frozen_inputs_preserved']
            for ref in n['inputs']:
                original=__import__('pathlib').Path(ref['source_provenance'])
                assert not work.is_relative_to(original.parent)
