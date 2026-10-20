"""Returned constructor evidence remains distinct from optimizer qualification."""
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar34_delivery import completed_single_block
from tests.test_cif_geometry_review_probe import write_capsule


def stereo_return(tmp_path,monkeypatch):
    m,old=completed_single_block(tmp_path,monkeypatch);p=tmp_path/'old.zip';write_capsule(p,old)
    with zipfile.ZipFile(p) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    r={'build':{'fixture':'FAKE_C34_BUILD'},'delivery_prefix':'34_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'status':'REVIEW','analysis_completed':True,'requested_action':'READ_ONLY_STEREOCHEMISTRY_AUDIT',
       'native_execution':'INSTALLED_READER_CHIRALITY_CONTROLS','automatic_adoption':False,'policy_authority':'NARestraints',
       'original_archive_preserved':True,'frozen_inputs_preserved':True,'prerequisite_mechanics_replayed':True,
       'prior_archive':{'sha256':m.CEDAR33_SHA256,'verified_payloads':1288},'installed_chirality_controls':{},
       'source_stereo_inventories':{},'saved_optimizer_trajectories':{},'saved_candidate_stereochemistry':{'PDU':{'fixture':'FAKE_STEREO'}}}
    r.update({k:'NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry']})
    m.CEDAR34_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for code in ['DP','PDU']:
        pre='native_stereochemistry/'+code;names=[code+str(i) for i in range(35 if code=='DP' else 38)]
        markers={n:'?' if code=='DP' else ['R','S','R'][i] if i<3 else '' for i,n in enumerate(names)}
        inventory={'source_sha256':sha256(old['consumer_preview/'+code+'/source.cif']).hexdigest(),
                   'atoms':{n:{'declared_stereo':v if v else 'N'} for n,v in markers.items()}}
        result={'reader_atoms':[{'atom':n,'native_chiral_marker':v} for n,v in markers.items()],
            'constructor_probe':{'status':'EXCEPTION','exception_type':'AssertionError','traceback':'assert len(atoms) in [4,5]'} if code=='DP' else {'status':'COMPLETED','atom_count':38}}
        control={'status':'REVIEW' if code=='DP' else 'READER_MARKERS_PASS','constructor_scope':'READER_CHIRALS_TRUE_NOT_FULL_BUILDER_REPLAY',
            'source_preserved':True,'installed_sources_preserved':True,'dictionary_generation':'NOT_RUN','installed_phenix_edits':'NOT_RUN',
            'captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN','automatic_adoption':False,'declared_marker_conflicts':[],
            'unknown_inputs_marked_chiral':names if code=='DP' else [],'source_inventory':inventory,'result':result,'sources':[]}
        for name in m.CEDAR34_CHIRAL_SOURCES:
            data=(old['native_contract/installed_sources/'+name] if name in m.ELBOW_SOURCE_SHA256 else
                  ('# FAKE INSTALLED SOURCE '+name+'\n').encode())
            m.CEDAR34_CHIRAL_SOURCES[name]=sha256(data).hexdigest();e[pre+'/'+name+'.txt']=data
            control['sources'].append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/'+name,
                'snapshot':{'anchor':'chirality_directory','path':name+'.txt'},'sha256':sha256(data).hexdigest(),'size':len(data)})
        data=b'raise RuntimeError("CAPTURED WORKER MUST NOT EXECUTE")\n';m.CEDAR34_WORKER_SHA256=sha256(data).hexdigest()
        e[pre+'/chirality_worker.py']=data;e[pre+'/source.cif']=old['consumer_preview/'+code+'/source.cif']
        e['consumer_preview/'+code+'/source.cif']=e[pre+'/source.cif']
        e[pre+'/chirality_result.json']=json.dumps(result).encode();e[pre+'/chirality_receipt.json']=json.dumps(control).encode()
        r['installed_chirality_controls'][code]={**control,'directory':{'anchor':'probe_directory','path':pre}}
        r['source_stereo_inventories'][code]=inventory
        trajectory={'fixture':'FAKE_TRAJECTORY_'+code};r['saved_optimizer_trajectories'][code]=trajectory
        e['stereochemistry/'+code+'_trajectory.json']=json.dumps(trajectory).encode()
    e['stereochemistry/PDU_candidate.json']=json.dumps(r['saved_candidate_stereochemistry']['PDU']).encode()
    e['probe_receipt.json']=json.dumps(r).encode()
    for i in range(1320-len(e)):e[f'padding/{i:03d}.txt']=b'FAKE_C34_PADDING'
    return m,e


@pytest.mark.parametrize('defect',['none','build','phase','adoption','prior','dp_marker','pdu_marker','source','source_escape','worker','scope','constructor','input','summary'])
def test_stereo_return_gate_checks_markers_native_sources_and_preserved_lineage(tmp_path,monkeypatch,defect):
    m,e=stereo_return(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json'])
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='phase':r['native_execution']='GENERATION'
    if defect=='adoption':r['automatic_adoption']=True
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    dp=r['installed_chirality_controls']['DP'];pd=r['installed_chirality_controls']['PDU']
    if defect=='dp_marker':dp['result']['reader_atoms'][0]['native_chiral_marker']='N'
    if defect=='pdu_marker':pd['result']['reader_atoms'][0]['native_chiral_marker']='S'
    if defect=='source':
        row=dp['sources'][1];name=dp['directory']['path']+'/'+row['snapshot']['path'];e[name]=b'# CHANGED';row.update(sha256=sha256(e[name]).hexdigest(),size=len(e[name]))
    if defect=='source_escape':dp['sources'][0]['path']='../outside.py'
    if defect=='worker':e[dp['directory']['path']+'/chirality_worker.py']=b'CHANGED'
    if defect=='scope':dp['captured_code_execution']='COMPLETED'
    if defect=='constructor':pd['result']['constructor_probe']['status']='EXCEPTION'
    if defect=='input':e[dp['directory']['path']+'/source.cif']=b'CHANGED'
    if defect=='summary':r['saved_candidate_stereochemistry']['PDU']['fixture']='CHANGED'
    for c in [dp,pd]:
        pre=c['directory']['path'];e[pre+'/chirality_result.json']=json.dumps(c['result']).encode()
        e[pre+'/chirality_receipt.json']=json.dumps({k:v for k,v in c.items() if k!='directory'}).encode()
    e['probe_receipt.json']=json.dumps(r).encode();p=tmp_path/'review.zip';write_capsule(p,e)
    if defect=='none':
        x=m._read_capsule(p,sha256(p.read_bytes()).hexdigest());assert m._source_view(x[0])[1]=='inputs/review/'*5
    else:
        with pytest.raises((ValueError,KeyError)):m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
