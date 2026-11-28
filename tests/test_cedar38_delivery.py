"""Exact C37 return gate preserves raw readbacks and explicit charge scope."""
from copy import deepcopy
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar37_delivery import completed_source_reader_return
from tests.test_cif_geometry_review_probe import write_capsule


def declared_charge_return(tmp_path,monkeypatch):
    m,old=completed_source_reader_return(tmp_path,monkeypatch);p=tmp_path/'old36.zip';write_capsule(p,old)
    with zipfile.ZipFile(p) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    e.update({n:d for n,d in old.items() if not n.startswith(('inputs/review/','native_source_reader/')) and n!='manifest.json'})
    r=deepcopy(json.loads(old['probe_receipt.json']));r.update(delivery_prefix='37_Cedar',build={'fixture':'EXPLICIT_FAKE_C37_BUILD'},
        requested_action='SOURCE_DIALECT_DECLARED_CHARGE_CONTROL',native_execution='SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS',
        prior_archive={'sha256':m.CEDAR36_SHA256,'verified_payloads':1355},declared_charge_control_requested=True)
    m.CEDAR37_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    worker=b'raise RuntimeError("CAPTURED_CHARGE_WORKER_MUST_NOT_EXECUTE")\n';m.CEDAR37_WORKER_SHA256=sha256(worker).hexdigest()
    historical,_=m._source_reader_evidence(old)
    for code,row in r['source_reader_audits'].items():
        pre=row['directory']['path'];consumer=e['consumer_preview/'+code+'/source.cif'];m.CEDAR37_CONSUMER_SHA256[code]=sha256(consumer).hexdigest()
        e[pre+'/source.cif']=consumer
        for name in m.CEDAR36_READER_SOURCES:
            e[pre+'/'+name+'.txt']=old[pre+'/'+name+'.txt']
        for name in ['elbow/utilities/Utilities.py','elbow/chemistry/MoleculeClass.py']:
            data=historical['native_stereochemistry/DP/'+name+'.txt'];e[pre+'/'+name+'.txt']=data
            row['sources'].append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/'+name,
                'sha256':sha256(data).hexdigest(),'size':len(data),'snapshot':{'anchor':'reader_directory','path':name+'.txt'}})
        if code=='DP':row['checks']['declared_bond_orders']=True
        raw=row['result'];before={'atoms':raw['atoms'],'bonds':raw['bonds'],'molecule_charge':0}
        control={'policy_id':'cif-explicit-source-formal-charge-control-v1','status':'DECLARED_CHARGE_CONTROL_PASS',
            'action':'POPULATED_FROM_EXPLICIT_SOURCE' if code=='DP' else 'ALREADY_PRESERVED',
            'source_total_charge':-2 if code=='DP' else 0,'changed_atoms':['OP2','OP3'] if code=='DP' else [],
            'before':before,'after':{**before,'molecule_charge':-2 if code=='DP' else 0},
            'automatic_adoption':False,'dictionary_generation':'NOT_RUN','independent_absolute_cip_validation':'NOT_RUN','optimization':'NOT_REQUESTED'}
        raw['declared_charge_control']=control;row['declared_charge_control']=control;row['declared_charge_control_requested']=True
        row['declared_charge_qualification']={'status':'DECLARED_CHARGE_CONTROL_PASS','checks':{
            **{k:True for k in row['checks']},'molecule_total_charge':True,'other_native_fields_preserved':True},
            'raw_reader_checks_retained':True,'scientific_approval':'NOT_RUN'}
        for name,data in [('reader_worker.py',worker),('reader_spec.json',b'{}'),('reader_worker.log',b'FAKE'),
                          ('reader_result.json',json.dumps(raw).encode()),
                          ('reader_receipt.json',json.dumps({k:v for k,v in row.items() if k!='directory'}).encode())]:e[pre+'/'+name]=data
    e['probe_receipt.json']=json.dumps(r).encode();assert len(e)==1387
    return m,e


@pytest.mark.parametrize('defect',['none','build','prior','worker','consumer','source','raw_charge','raw_order','action','changed_atoms','total','scope','preserved','qualification'])
def test_returned_declared_charge_gate_rejects_changed_or_overclaimed_evidence(tmp_path,monkeypatch,defect):
    m,e=declared_charge_return(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json']);row=r['source_reader_audits']['DP'];pre=row['directory']['path']
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='prior':e['inputs/review/inputs/review/inputs/review/padding/001.txt']=b'CHANGED'
    if defect=='worker':e[pre+'/reader_worker.py']=b'CHANGED'
    if defect=='consumer':e['consumer_preview/DP/source.cif']=b'CHANGED'
    if defect=='source':e[pre+'/'+row['sources'][-1]['snapshot']['path']]=b'CHANGED'
    if defect=='raw_charge':row['checks']['atom_charge_values']=True
    if defect=='raw_order':row['checks']['declared_bond_orders']=False
    control=row['declared_charge_control']
    if defect=='action':control['action']='INFERRED'
    if defect=='changed_atoms':control['changed_atoms']=[]
    if defect=='total':control['after']['molecule_charge']=0
    if defect=='scope':control['optimization']='COMPLETED'
    if defect=='preserved':control['after']['bonds']=[{'atoms':['OP2','OP3'],'native_order':1}]
    if defect=='qualification':row['declared_charge_qualification']['checks']['atom_charge_values']=False
    row['result']['declared_charge_control']=control
    e[pre+'/reader_result.json']=json.dumps(row['result']).encode()
    e[pre+'/reader_receipt.json']=json.dumps({k:v for k,v in row.items() if k!='directory'}).encode()
    e['probe_receipt.json']=json.dumps(r).encode();p=tmp_path/'review37.zip';write_capsule(p,e)
    if defect=='none':
        result=m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
        assert m._source_view(result[0])[1]=='inputs/review/'*8
        assert m._source_reader_evidence(result[0])[1]=='inputs/review/'*3
    else:
        with pytest.raises((ValueError,KeyError)):m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
