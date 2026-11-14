"""Complete candidate captures retain raw statuses and never execute saved code."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest
from tests.test_cif_candidate_usability import component
from tests.test_cif_source_candidate import REFERENCE
from tests.test_cif_stereochemistry_audit import write


def returned(tmp_path):
    from nasolve.cif_source_candidate import native_object_reference,complete_candidate_stereo,POLICY_ID
    from nasolve.cif_constructor_setup import native_setup_reference
    from nasolve.cif_generation import inspect_component_generation
    from nasolve.cif_stereochemistry_audit import audit_optimizer_log
    spec=importlib.util.spec_from_file_location('replay55',Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.CEDAR54_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_COMPLETE_WORKER').hexdigest()
    a={'policy_id':POLICY_ID,'cases':{},'native_execution':'SOURCE_NATIVE_COMPLETE_CANDIDATES','dictionary_generation':'BOUNDED_NATIVE_BUILDER',
       'single_block_steps':180,'automatic_adoption':False,'requires_cif_review':False,'selection':'PENDING_NATIVE_USABILITY'}
    members={};r={'source_candidate_audit':a}
    for code in ['DP','PDU','5PC']:
        p='source_candidates/'+code;v=component(code);s=write(tmp_path/code/'source.cif',v);f=write(tmp_path/code/'candidate.cif',v)
        source=s.read_bytes();candidate=f.read_bytes();args=['--id='+code,'--opt','--opt_steps=180'];result={'builder':{'status':'COMPLETED'},'charge_control':{'status':'DECLARED_CHARGE_CONTROL_PASS'}}
        g={'directory':{'anchor':'probe_directory','path':p},'policy_id':POLICY_ID,'component':code,'source_preserved':True,'candidate_retained':True,
           'execution':{'status':'COMPLETED','returncode':0,'timeout_seconds':600},'single_block_steps':180,'automatic_adoption':False,'requires_cif_review':False,
           'native_proxy_validation':'NOT_RUN','model_editing':'NOT_RUN','installed_phenix_edits':'NOT_RUN','sources':[],
           'arguments':args,'result':result,'source_sha256':sha256(source).hexdigest(),'status':'CANDIDATE_REVIEW','formal_charges_preserved':True,
           'candidate':{'anchor':'candidate_directory','path':'candidate.cif','sha256':sha256(candidate).hexdigest(),'size':len(candidate)},
           'native_object_reference':native_object_reference(REFERENCE),'native_setup_reference':native_setup_reference(REFERENCE),
           'inspection':inspect_component_generation(s,f,code),'finished_stereo':complete_candidate_stereo(s,f,code),
           'stopping':{'status':'NOT_REPORTED','convergence_claimed':False,'trajectory':audit_optimizer_log('')},'excluded_serialized_outputs':[]}
        a['cases'][code]={'generation':g,'consumer':{'anchor':'probe_directory','path':p+'/source.cif','sha256':sha256(source).hexdigest(),'size':len(source)}}
        members.update({p+'/source.cif':source,p+'/candidate.cif':candidate,p+'/candidate_spec.json':json.dumps({'component':code,'arguments':args}).encode(),
            p+'/candidate_worker.py':b'EXPLICIT_FAKE_COMPLETE_WORKER',p+'/candidate_worker.log':b''})
        for name in ['elbow/chemistry/any_chemical_format_reader.py','elbow/chemistry/MoleculeClass.py','elbow/chemistry/SimpleMoleculeClass.py','elbow/command_line/builder.py']:
            data=REFERENCE.encode() if name.endswith('/builder.py') else b'# EXPLICIT_FAKE_CAPTURED_API\n';path='api_sources/'+name+'.txt'
            g['sources'].append({'anchor':'phenix_installation','path':'site/'+name,'snapshot':{'anchor':'candidate_directory','path':path},'sha256':sha256(data).hexdigest(),'size':len(data)})
            members[p+'/'+path]=data
    save(members,r);return m,members,r


def save(members,r):
    for c in r['source_candidate_audit']['cases'].values():
        g=c['generation'];p=g['directory']['path'];members[p+'/candidate_result.json']=json.dumps(g['result']).encode()
        g['outputs']=[{'anchor':'candidate_directory','path':name[len(p)+1:],'sha256':sha256(data).hexdigest(),'size':len(data)} for name,data in members.items() if name.startswith(p+'/') and name!=p+'/source_candidate_receipt.json']
        members[p+'/source_candidate_receipt.json']=json.dumps({k:v for k,v in g.items() if k!='directory'}).encode()
    members['source_candidate_audit.json']=json.dumps(r['source_candidate_audit']).encode();members['probe_receipt.json']=json.dumps(r).encode()


@pytest.mark.parametrize('defect',['none','worker','candidate','source','source_pin','hidden_rejection','hidden_hand','hidden_stopping','builder_exception','charges','api_bytes','api_reference','spec','excluded_pickle'])
def test_saved_generation_replay_recomputes_legacy_findings_and_keeps_all_sources_pinned(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_candidate_audit']['cases']['DP'];g=c['generation'];p=g['directory']['path']
    if defect=='worker':members[p+'/candidate_worker.py']=b'CHANGED'
    if defect=='candidate':members[p+'/candidate.cif']+=b'CHANGED'
    if defect=='source':members[p+'/source.cif']+=b'CHANGED'
    if defect=='source_pin':g['source_sha256']='a'*64
    if defect=='hidden_rejection':g['status']='REJECTED'
    if defect=='hidden_hand':g['finished_stereo']['stereochemistry']='INVERTED'
    if defect=='hidden_stopping':g['stopping']['status']='CONVERGED'
    if defect=='builder_exception':g['result']['builder']['status']='EXCEPTION'
    if defect=='charges':g['formal_charges_preserved']=False
    if defect=='api_bytes':members[p+'/'+g['sources'][0]['snapshot']['path']]+=b'CHANGED'
    if defect=='api_reference':g['native_object_reference']['object_line']+=1
    if defect=='spec':members[p+'/candidate_spec.json']=json.dumps({'component':'BAD','arguments':g['arguments']}).encode()
    if defect=='excluded_pickle':
        data=b'EXCLUDED_SERIALIZED_FILE_MUST_NOT_BE_LOADED';members[p+'/candidate.pickle']=data
        g['excluded_serialized_outputs']=[{'anchor':'candidate_directory','path':'candidate.pickle','sha256':sha256(data).hexdigest(),'size':len(data)}]
    save(members,r)
    if defect=='none':assert set(m._check_source_candidate_return(members,r))=={'DP','PDU','5PC'}
    else:
        with pytest.raises((ValueError,KeyError)):m._check_source_candidate_return(members,r)


@pytest.mark.parametrize('delivery,option',[('54_Cedar','candidate_native_usability_only'),('53_Cedar','source_candidate_generation_only'),('52_Cedar','source_constructor_setup_audit_only')])
def test_usability_routing_does_not_repeat_generation_or_constructor(tmp_path,delivery,option):
    from types import SimpleNamespace
    m,_,_=returned(tmp_path);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.candidate_native_usability_only=not getattr(args,'candidate_native_usability_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
