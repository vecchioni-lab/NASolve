"""Preserve raw C36 reader failures and prove the exact installed parser scope."""
from copy import deepcopy
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar36_delivery import failed_source_dialect_return
from tests.test_cif_geometry_review_probe import write_capsule


def completed_source_reader_return(tmp_path,monkeypatch):
    m,old=failed_source_dialect_return(tmp_path,monkeypatch);p=tmp_path/'old.zip';write_capsule(p,old)
    with zipfile.ZipFile(p) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    historical,_=m._source_reader_evidence(old);parent=json.loads(historical['probe_receipt.json'])
    r=deepcopy(json.loads(old['probe_receipt.json']))
    r.update(build={'fixture':'EXPLICIT_FAKE_C36_BUILD'},delivery_prefix='36_Cedar',analysis_completed=True,
        native_execution='SOURCE_READER_DIALECT_CONTROLS',prior_archive={'sha256':m.CEDAR35_SHA256,'verified_payloads':1327},
        source_reader_audits={},saved_candidate_stereochemistry=parent['saved_candidate_stereochemistry'],
        saved_optimizer_trajectories=parent['saved_optimizer_trajectories'])
    r.pop('error');m.CEDAR36_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for name in ['component_controls/PDU_control.json','component_controls/sources/PDU.cif','graph_preview/DP/source.cif',
                 'graph_preview/PDU/source.cif','numerical_recovery_plan.json']:e[name]=old[name]
    for name in ['stereochemistry/DP_trajectory.json','stereochemistry/PDU_trajectory.json','stereochemistry/PDU_candidate.json']:e[name]=historical[name]
    for code in ['DP','PDU']:
        pre='native_source_reader/'+code;consumer=historical['consumer_preview/'+code+'/source.cif'];digest=sha256(consumer).hexdigest()
        m.CEDAR36_CONSUMER_SHA256[code]=digest;e['consumer_preview/'+code+'/source.cif']=consumer;e[pre+'/source.cif']=consumer
        result={'execution':'COMPLETED','atoms':[],'bonds':[],'fixture':'EXPLICIT_FAKE_INVENTORY_'+code}
        checks={k:True for k in ['reader_route','atom_identities','atom_elements','atom_charge_values','source_coordinates','declared_bond_orders']}
        if code=='DP':checks.update(atom_charge_values=False,declared_bond_orders=False)
        row={'policy_id':'cif-installed-source-reader-inventory-v1','source_sha256':digest,'source_preserved':True,
            'installed_sources_preserved':True,'automatic_adoption':False,'chiral_constructor':'NOT_REQUESTED',
            'whole_molecule_optimization':'NOT_REQUESTED','parser_internal_operations':'NOT_INSTRUMENTED',
            'sources':[],'result':result,'checks':checks,'status':'REVIEW' if code=='DP' else 'READER_ROUTE_AND_INVENTORY_PASS'}
        row.update({k:'NOT_RUN' for k in ['dictionary_generation','independent_absolute_cip_validation',
            'signed_stereo_native_qualification','installed_phenix_edits','captured_code_execution','pickle_loading']})
        for name in m.CEDAR36_READER_SOURCES:
            data=historical['native_stereochemistry/DP/'+name+'.txt'] if name in m.CEDAR34_CHIRAL_SOURCES else ('# FAKE_READER_SNAPSHOT '+name+'\n').encode()
            e[pre+'/'+name+'.txt']=data;m.CEDAR36_READER_SOURCES[name]=sha256(data).hexdigest()
            row['sources'].append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/'+name,
                'sha256':sha256(data).hexdigest(),'size':len(data),'snapshot':{'anchor':'reader_directory','path':name+'.txt'}})
        worker=b'raise RuntimeError("CAPTURED_READER_WORKER_MUST_NOT_EXECUTE")\n';e[pre+'/reader_worker.py']=worker
        m.CEDAR36_WORKER_SHA256=sha256(worker).hexdigest()
        e[pre+'/reader_spec.json']=b'{}';e[pre+'/reader_worker.log']=b'EXPLICIT_FAKE_LOG'
        e[pre+'/reader_result.json']=json.dumps(result).encode();e[pre+'/reader_receipt.json']=json.dumps(row).encode()
        r['source_reader_audits'][code]={**row,'directory':{'anchor':'probe_directory','path':pre}}
    e['probe_receipt.json']=json.dumps(r).encode()
    assert len(e)==1355
    return m,e


@pytest.mark.parametrize('defect',['none','build','phase','prior','source','source_escape','worker','input','receipt',
                                  'raw_charge','raw_order','scope','charge_control','saved_stereo'])
def test_completed_reader_return_gate_keeps_raw_differences_and_rejects_changed_evidence(tmp_path,monkeypatch,defect):
    m,e=completed_source_reader_return(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json']);dp=r['source_reader_audits']['DP'];pre=dp['directory']['path']
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='phase':r['native_execution']='GENERATION'
    if defect=='prior':e['inputs/review/inputs/review/padding/001.txt']=b'CHANGED'
    if defect=='source':e[pre+'/'+dp['sources'][0]['snapshot']['path']]=b'# CHANGED'
    if defect=='source_escape':dp['sources'][0]['path']='../outside.py'
    if defect=='worker':e[pre+'/reader_worker.py']=b'CHANGED'
    if defect=='input':e[pre+'/source.cif']=b'CHANGED'
    if defect=='raw_charge':dp['checks']['atom_charge_values']=True
    if defect=='raw_order':dp['checks']['declared_bond_orders']=True
    if defect=='scope':dp['chiral_constructor']='COMPLETED'
    if defect=='charge_control':dp['declared_charge_control_requested']=True
    if defect=='saved_stereo':r['saved_candidate_stereochemistry']['PDU']['fixture']='CHANGED'
    e[pre+'/reader_receipt.json']=json.dumps({k:v for k,v in dp.items() if k!='directory'}).encode()
    if defect=='receipt':e[pre+'/reader_receipt.json']=b'{}'
    e['probe_receipt.json']=json.dumps(r).encode();p=tmp_path/'review.zip';write_capsule(p,e)
    if defect=='none':
        result=m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
        assert m._source_view(result[0])[1]=='inputs/review/'*7
        assert m._source_reader_evidence(result[0])[1]=='inputs/review/'*2
    else:
        with pytest.raises((ValueError,KeyError)):m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
