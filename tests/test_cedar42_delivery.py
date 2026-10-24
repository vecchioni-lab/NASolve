"""Failed ReadySet calls and preparatory source copies remain failed evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest


def returned():
    p=Path(__file__).resolve().parents[1]/'scripts/cif_numerical_recovery_probe_template.py'
    spec=importlib.util.spec_from_file_location('cedar42_template',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    worker=b'raise RuntimeError("CAPTURED WORKER MUST NEVER EXECUTE")\n';m.CEDAR41_WORKER_SHA256=sha256(worker).hexdigest()
    audit={'policy_id':'cif-isolated-readyset-call-and-triple-restraint-audit-v1','status':'REVIEW','automatic_adoption':False,
        'native_execution':'ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS',
        **{k:'NOT_RUN' for k in ['experimental_model_changes','refinement','scientific_approval']},'cases':{}}
    members={}
    for code in ['PDU','5PC']:
        source=('FAKE SOURCE '+code).encode();members['component_controls/sources/'+code+'.cif']=source
        pre='readyset_controls/generation/'+code;sourcepath='api_sources/ready_set.py.txt';members[pre+'/'+sourcepath]=b'FAKE STATIC SOURCE'
        g={'policy_id':audit['policy_id'],'actions':dict(__import__('nasolve.cif_readyset_generation_audit',fromlist=['ACTIONS']).ACTIONS),
            'execution':{'status':'COMPLETED','returncode':0},'result':{'execution':'EXCEPTION','exception_type':'SystemExit','message':'2',
                'traceback':'optparse.BadOptionError: no such option: --ready_set.input.output_file_name'},
            'trace':{'argument_overrides':'NONE','truncated':False,'events':[{'api':'ELBOW_BUILDER','args':[],
                'kwargs':{'file':code+'.cif','id':code,'output':code,'silent':True},'status':'EXCEPTION','exception_type':'SystemExit','message':'2',
                'caller':{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/elbow/scripts/elbow_on_pdb_file.py','line':779}}]},
            'sources':[{'anchor':'phenix_installation','path':'lib/ready_set.py','sha256':sha256(b'FAKE STATIC SOURCE').hexdigest(),'size':18,
                'snapshot':{'anchor':'readyset_directory','path':sourcepath}}],
            'outputs':[],'excluded_serialized_outputs':[],
            'candidate':{'status':'RECORDED','anchor':'readyset_directory','path':code+'.cif','sha256':sha256(source).hexdigest(),'size':len(source)}}
        members[pre+'/'+code+'.cif']=source;members[pre+'/readyset_worker.py']=worker
        case={'source_sha256':sha256(source).hexdigest(),'generation':{'directory':{'anchor':'readyset_control_directory','path':'generation/'+code},**g},
            'native_triple_screen':{'status':'NOT_RUN'}}
        audit['cases'][code]=case
    return m,members,{'readyset_generation_audit':audit}


def materialize(members,r):
    audit=r['readyset_generation_audit']
    for code,case in audit['cases'].items():
        pre='readyset_controls/generation/'+code;g=deepcopy(case['generation']);g.pop('directory')
        for name,data in [('readyset_generation_receipt.json',g),('readyset_result.json',g['result']),('call_trace.json',g['trace'])]:
            members[pre+'/'+name]=json.dumps(data).encode()
    members['readyset_controls/readyset_control_receipt.json']=json.dumps(audit).encode()


@pytest.mark.parametrize('defect',['none','worker','snapshot','adoption','native_pass','native_interpretation','native_completed',
    'returncode','caught_fallback','different_file','wrong_file_ref','actions','trace_override','claimed_generation'])
def test_failed_generation_gate_cannot_promote_surviving_source_copies(defect):
    m,members,r=returned();a=r['readyset_generation_audit'];c=a['cases']['PDU'];g=c['generation'];pre='readyset_controls/generation/PDU'
    if defect=='worker':members[pre+'/readyset_worker.py']=b'CHANGED'
    if defect=='snapshot':members[pre+'/api_sources/ready_set.py.txt']=b'CHANGED'
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='native_pass':c['native_triple_screen']={'status':'PASS'}
    if defect=='native_interpretation':c['native_interpretation']={'status':'PASS'}
    if defect=='native_completed':g['result']['execution']='COMPLETED'
    if defect=='returncode':g['execution']['returncode']=2
    if defect=='caught_fallback':g['trace']['events'].append({'api':'CCD_TEMPLATE','status':'RETURNED'})
    if defect=='different_file':members[pre+'/PDU.cif']=b'CHANGED'
    if defect=='wrong_file_ref':g['candidate']['path']='../PDU.cif'
    if defect=='actions':g['actions']['hydrogens']=True
    if defect=='trace_override':g['trace']['argument_overrides']='USED'
    if defect=='claimed_generation':g['candidate']['classification']='COMPLETED_READYSET_OUTPUT'
    materialize(members,r)
    if defect=='none':m._check_readyset_generation_return(members,r)
    else:
        with pytest.raises(ValueError):m._check_readyset_generation_return(members,r)
