"""A backend retry must preserve and independently replay the C47 failures."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar40_delivery import template
from tests.test_cif_source_constructor import evidence
from tests.test_cif_stereochemistry_audit import tetrahedron,write


def returned(tmp_path):
    from nasolve.cif_source_constructor import SOURCE_PATHS,POLICY_ID,qualify_constructor_evidence
    m=template();members={};m.CEDAR47_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_LEGACY_WORKER').hexdigest();m.CEDAR47_SOURCE_SHA256={}
    a={'policy_id':POLICY_ID,'status':'REVIEW','native_execution':'SOURCE_NATIVE_CONSTRUCTOR_HANDOFF','automatic_adoption':False,
        'whole_molecule_optimization':'NOT_REQUESTED','constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED',
        **{k:'NOT_RUN' for k in ['dictionary_generation','model_editing','absolute_cip_assignment']},'cases':{}}
    for code in ['DP','PDU','5PC']:
        v,_=tetrahedron(code);source=write(tmp_path/(code+'.cif'),v);data=source.read_bytes();dialect='MONOMER_LIBRARY_CIF' if code=='DP' else 'CHEMICAL_COMPONENTS_CIF'
        x=evidence(v);x['constructor'].update(status='EXCEPTION',exception_type='ExplicitFakeException',message='PRESERVE THIS FAILURE')
        if code=='DP':
            x['reader'].update(format='CIF',dispatch_is_chemical_components=False);x['constructor']['promoted_format']='CIF'
        x['constructor'].pop('after_format')
        q=qualify_constructor_evidence(source,code,x,dialect);m.CEDAR47_SOURCE_SHA256[code]=sha256(data).hexdigest();p='source_constructor/'+code
        consumer={'anchor':'probe_directory','path':'consumer_preview/'+code+'/source.cif','sha256':sha256(data).hexdigest(),'size':len(data)}
        members[consumer['path']]=members[p+'/source.cif']=data
        n={'component':code,'policy_id':POLICY_ID,'status':'REVIEW','expected_dialect':dialect,'source_preserved':True,
            'source_sha256':sha256(data).hexdigest(),'automatic_adoption':False,'execution':{'status':'COMPLETED','returncode':0,'timeout_seconds':60},
            'whole_molecule_optimization':'NOT_REQUESTED','constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED',
            **{k:'NOT_RUN' for k in ['dictionary_generation','model_editing','whole_builder_replay','absolute_cip_assignment',
                'installed_phenix_edits','captured_code_execution','pickle_loading']},'result':x,'qualification':q,'sources':[],'outputs':[]}
        for name in SOURCE_PATHS:
            payload=('# EXPLICIT_FAKE_SOURCE '+name).encode();members[p+'/'+name+'.txt']=payload
            n['sources'].append({'anchor':'phenix_installation','path':'site/'+name,'size':len(payload),'sha256':sha256(payload).hexdigest(),
                'snapshot':{'anchor':'constructor_directory','path':name+'.txt'}})
        members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_LEGACY_WORKER';members[p+'/constructor_spec.json']=json.dumps({'component':code}).encode()
        a['cases'][code]={'consumer':consumer,'reader_dialect':dialect,'native':{'directory':{'anchor':'probe_directory','path':p},**n}}
    r={'source_constructor_audit':a};save(members,r);return m,members,r


def save(members,r):
    for code,c in r['source_constructor_audit']['cases'].items():
        n=c['native'];p='source_constructor/'+code;members[p+'/constructor_result.json']=json.dumps(n['result']).encode()
        n['outputs']=[{'anchor':'constructor_directory','path':path.removeprefix(p+'/'),'sha256':sha256(data).hexdigest(),'size':len(data)}
            for path,data in members.items() if path.startswith(p+'/') and not path.endswith('/constructor_receipt.json')]
        members[p+'/constructor_receipt.json']=json.dumps({k:v for k,v in n.items() if k!='directory'}).encode()
    members['source_constructor_receipt.json']=json.dumps(r['source_constructor_audit']).encode()


@pytest.mark.parametrize('defect',['none','worker','source','api','outputs','qualification','hide_exception','charge','route','adoption','execution','budget','backend','dialect'])
def test_failed_constructor_return_is_replayed_without_hiding_or_resuming_it(tmp_path,defect):
    m,members,r=returned(tmp_path);a=r['source_constructor_audit'];n=a['cases']['DP']['native'];p='source_constructor/DP'
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='source':members[p+'/source.cif']=b'CHANGED'
    if defect=='api':members[p+'/elbow/chemistry/ChiralClass.py.txt']=b'CHANGED'
    if defect=='qualification':n['qualification']['checks']['constructor_completed']=True
    if defect=='hide_exception':n['result']['constructor']['status']='COMPLETED'
    if defect=='charge':n['result']['constructor']['after']['atoms'][0]['native_atom_charge']=-1
    if defect=='route':n['result']['constructor']['after_format']='SMILES'
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='execution':n['execution']['returncode']=1
    if defect=='budget':n['execution']['timeout_seconds']=61
    if defect=='backend':members[p+'/constructor_spec.json']=json.dumps({'component':'DP','native_cctbx':True}).encode()
    if defect=='dialect':n['expected_dialect']='CHEMICAL_COMPONENTS_CIF'
    save(members,r)
    if defect=='outputs':n['outputs'][0]['sha256']='CHANGED';members['source_constructor_receipt.json']=json.dumps(a).encode();members[p+'/constructor_receipt.json']=json.dumps({k:v for k,v in n.items() if k!='directory'}).encode()
    if defect=='none':
        q=m._check_constructor_return(members,r)
        assert set(q)=={'DP','PDU','5PC'} and all(v['qualification']['constructor_status']=='EXCEPTION' for v in q.values())
        assert all(v['message']=='PRESERVE THIS FAILURE' and 'native_reader_route_preserved' in v['failed_checks'] for v in q.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_return(members,r)
