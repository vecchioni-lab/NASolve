"""C76 consumes the verified C75 return, without reopening isolated controls."""
from types import SimpleNamespace
from tests.test_cedar65_delivery import template
import pytest

@pytest.mark.parametrize('action,delivery,valid',[
    ('postmr_cached_model_only','75_Cedar',True),('postmr_readyset_consumption_only','75_Cedar',False),
    ('postmr_cached_model_only','74_Cedar',False),('postmr_cached_model_only','77_Cedar',False)])
def test_cached_whole_model_has_explicit_input_scope(action,delivery,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)

@pytest.mark.parametrize('defect',['none','build','action','readyset_calls','native_calls','parent','cases','policy','adoption','student_gate','status','native_label','preservation','dictionary','model_edit','report'])
def test_c75_return_header_preserves_completed_scope(monkeypatch,defect):
    from hashlib import sha256
    import json
    m=template()
    a={'policy_id':'cif-postmr-readyset-consumption-controls-v2','status':'POSTMR_READYSET_CONSUMPTION_PASS',
        'new_readyset_calls':3,'new_native_calls':3,'requires_cif_review':False,'automatic_adoption':False,
        'production_checkpoint':'NOT_CREATED','cases':{c:{} for c in ['DP','PDU','5PC']}}
    r={'delivery_prefix':'75_Cedar','kind':'cif-source-graph-numerical-recovery-probe','requested_action':'ORDINARY_POSTMR_READYSET_CONSUMPTION',
        'status':'REVIEW','build':{'fixture':True},'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['model_editing','policy_recompilation','refinement','installed_phenix_edits','scientific_approval','linked_site_validation','native_proxy_validation']},
        'native_execution':'ISOLATED_READYSET_CONSUMPTION_AND_EFFECTIVE_NATIVE_READBACK',
        'dictionary_generation':'NOT_OBSERVED_BY_SELECTED_BUILDER_TRACE','model_optimization':'NOT_REQUESTED; NATIVE_INTERNALS_NOT_EXHAUSTIVELY_INSTRUMENTED',
        'readyset_retry':'ISOLATED_ORDINARY_ARGUMENTS_OBSERVED_ENTRYPOINT','prior_archive':{'sha256':m.CEDAR74_SHA256,'verified_payloads':5304},
        'postmr_readyset_consumption_audit':a}
    m.CEDAR75_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_verify_manifest',lambda members,count:None)
    monkeypatch.setattr(m,'_read_cedar74_members',lambda members:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar75_return',lambda members:True)
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='readyset_calls':a['new_readyset_calls']=0
    if defect=='native_calls':a['new_native_calls']=0
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='cases':a['cases'].pop('DP')
    if defect=='policy':a['policy_id']='OTHER'
    if defect=='adoption':r['automatic_adoption']=True
    if defect=='student_gate':r['requires_cif_review']=True
    if defect=='status':a['status']='REVIEW'
    if defect=='native_label':r['native_execution']='NOT_RUN'
    if defect=='preservation':r['frozen_inputs_preserved']=False
    if defect=='dictionary':r['dictionary_generation']='REGENERATED'
    if defect=='model_edit':r['model_editing']='OPTIMIZED'
    members={'probe_receipt.json':json.dumps(r).encode(),'postmr_readyset_consumption_audit.json':json.dumps(a).encode()}
    if defect=='report':members['postmr_readyset_consumption_audit.json']=b'{}'
    if defect=='none':assert m._read_cedar75_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar75_members(members)


@pytest.mark.parametrize('delivery',['75_Cedar','76_Cedar'])
def test_c75_direct_native_qualification_reaches_the_whole_model_adapter(tmp_path,monkeypatch,delivery):
    """C75 returns its native qualification directly, unlike the C57 wrapper."""
    from hashlib import sha256
    import json
    from nasolve.cif_review_transport import stage_review_members
    import nasolve.cif_postmr_cached_model as cached
    m=template();session=tmp_path/'session';session.mkdir();inputs=tmp_path/'source_inputs';inputs.mkdir()
    resources={}
    for code in ['DP','PDU','5PC']:
        s=inputs/(code+'_source.cif');c=inputs/(code+'_numerics.cif');s.write_bytes(b'SOURCE');c.write_bytes(b'NUMERICS')
        resources[code]={'source':s,'candidate':c,'qualification':{'native_usable':True,'candidate_sha256':sha256(c.read_bytes()).hexdigest()},'consumer':{'fixture':'SAME_CONSUMER'}}
    monkeypatch.setattr(m,'_replay_cedar75_return' if delivery=='75_Cedar' else '_replay_cedar76_return',lambda *a:resources)
    data=b'EXACT CONSTRUCTED MODEL\n';ref={'anchor':'construction_directory','path':'model.pdb','size':len(data),'sha256':sha256(data).hexdigest()}
    members={'probe_receipt.json':json.dumps({'delivery_prefix':delivery}).encode(),
        'inputs/review/probe_receipt.json':json.dumps({'delivery_prefix':'64_Cedar','construction_native_audit':{'canonical_reference':{'fixture':'VERIFIED'}}}).encode(),
        'inputs/review/inputs/review/probe_receipt.json':json.dumps({'delivery_prefix':'63_Cedar','postmr_construction_audit':{'input_model':ref,'outputs':{'model':ref}}}).encode(),
        'inputs/review/inputs/review/postmr_construction/model.pdb':data}
    frozen=session/'inputs/review';stage_review_members(members,frozen)
    report={'status':'PREPARED_ONLY','readyset':{'status':'PREPARED_ONLY'},'decision':{'status':'NOT_ASSESSED','selected':None},'new_native_calls':0,'new_readyset_calls':0}
    def inspect(reference,model,canonical,linked,phenix,consumer,output,**kwargs):
        assert reference.read_bytes()==model.read_bytes()==data
        assert canonical=={'fixture':'VERIFIED'} and phenix is None
        for code,row in linked.items():
            assert row['qualification'] is resources[code]['qualification']
            assert row['source']==resources[code]['source'] and row['numerical']==resources[code]['candidate']
            assert len(row['contexts'])==1
        return report
    monkeypatch.setattr(cached,'audit_cached_model',inspect);monkeypatch.setattr(cached,'read_cached_model',lambda path:report)
    monkeypatch.setattr(m,'_review_zip',lambda path:'EXPLICIT TEST ZIP; NOT GENERATED')
    review=tmp_path/'review.zip';review.write_bytes(b'PRESERVED')
    receipt={};args=SimpleNamespace(inspect_only=True,timeout_seconds=120)
    assert m._run_postmr_cached_model_action(args,receipt,session,review,b'PRESERVED',members,frozen)==2
    assert receipt['postmr_cached_model_audit']['status']=='PREPARED_ONLY'
    assert receipt['native_execution']=='NOT_RUN' and not receipt['requires_cif_review']
