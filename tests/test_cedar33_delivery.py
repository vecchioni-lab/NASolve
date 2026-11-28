"""The installed reader/source contract is rechecked before a bounded retry."""
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar32_delivery import two_failed_candidates
from tests.test_cif_geometry_review_probe import write_capsule


def installed_contract_capsule(tmp_path,monkeypatch):
    m,old=two_failed_candidates(tmp_path,monkeypatch);path=tmp_path/'old.zip';write_capsule(path,old)
    with zipfile.ZipFile(path) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    r={'build':{'fixture':'EXPLICIT_FAKE_C32_BUILD'},'delivery_prefix':'32_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'status':'REVIEW','analysis_completed':True,'requested_action':'NATIVE_READ_ONLY_CONTRACT','native_execution':'READ_ONLY_INPUT_CHECKS',
       'automatic_adoption':False,'policy_authority':'NARestraints','original_archive_preserved':True,'frozen_inputs_preserved':True,
       'prerequisite_mechanics_replayed':True,'prior_archive':{'sha256':m.CEDAR31_SHA256,'verified_payloads':1209},'native_input_checks':{}}
    r.update({k:'NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry']})
    m.CEDAR32_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    c={'status':'CAPTURED_NOT_QUALIFIED','captured_code_execution':'NOT_RUN','installed_phenix_edits':'NOT_RUN','pickle_loading':'NOT_RUN','sources':[]}
    pre='native_contract/installed_sources'
    for name in m.ELBOW_SOURCE_SHA256:
        data=b'raise RuntimeError("CAPTURED PYTHON MUST NOT EXECUTE")\n'+('# '+name).encode()
        e[pre+'/'+name]=data;digest=sha256(data).hexdigest();m.ELBOW_SOURCE_SHA256[name]=digest
        c['sources'].append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/'+name,
            'snapshot':{'anchor':'contract_directory','path':name},'sha256':digest,'size':len(data)})
    e[pre+'/source_capture.json']=json.dumps(c).encode()
    r['installed_elbow_contract']={**c,'source_directory':{'anchor':'probe_directory','path':pre}}
    for code in ['DP','PDU']:
        directory='native_contract/inputs/FIXTURE_'+code
        log=b"has no attribute 'pdbx_aromatic_flag'" if code=='DP' else b'Input format is CHEMICAL COMPONENTS'
        data=('EXPLICIT_FAKE_GRAPH32_'+code).encode();e[directory+'/source.cif']=data;e['graph_preview/'+code+'/source.cif']=data;e[directory+'/elbow_read_only.log']=log
        check={'status':'REVIEW' if code=='DP' else 'PARSER_READ_ONLY_PASS','execution':{'returncode':1 if code=='DP' else 0},
            'source_preserved':True,'frozen_source_preserved':True,'executable_preserved':True,'dictionary_generation':'NOT_RUN','model_optimization':'NOT_RUN','automatic_adoption':False,
            'outputs':[{'anchor':'contract_directory','path':name,'size':len(payload),'sha256':sha256(payload).hexdigest()}
                for name,payload in [('source.cif',data),('elbow_read_only.log',log)]]}
        e[directory+'/input_receipt.json']=json.dumps(check).encode()
        r['native_input_checks'][code]={**check,'directory':{'anchor':'probe_directory','path':directory}}
    e['probe_receipt.json']=json.dumps(r).encode()
    for i in range(1229-len(e)):e[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    return m,e


@pytest.mark.parametrize('defect',['none','build','source','source_escape','input_outcome','log','snapshot','prior','generated_scope','directory','captured_exec'])
def test_installed_contract_gate_rejects_changed_sources_outcomes_and_unsupported_actions(tmp_path,monkeypatch,defect):
    m,e=installed_contract_capsule(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json'])
    c=r['installed_elbow_contract'];pre=c['source_directory']['path'];first=c['sources'][0]
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='source':
        name=pre+'/'+first['snapshot']['path'];e[name]=b'CHANGED';first.update(size=len(e[name]),sha256=sha256(e[name]).hexdigest())
    if defect=='source_escape':first['path']='../outside.py'
    if defect=='captured_exec':c['captured_code_execution']='COMPLETED'
    if defect=='input_outcome':r['native_input_checks']['DP']['status']='PARSER_READ_ONLY_PASS'
    if defect=='directory':r['native_input_checks']['DP']['directory']['anchor']='UNSUPPORTED'
    check=r['native_input_checks']['DP'];directory=check['directory']['path']
    if defect=='log':
        data=b'NO_CAPTURED_ERROR';e[directory+'/elbow_read_only.log']=data
        row=next(x for x in check['outputs'] if x['path']=='elbow_read_only.log');row.update(size=len(data),sha256=sha256(data).hexdigest())
    if defect=='snapshot':
        data=b'CHANGED';e[directory+'/source.cif']=data
        row=next(x for x in check['outputs'] if x['path']=='source.cif');row.update(size=len(data),sha256=sha256(data).hexdigest())
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    if defect=='generated_scope':r['dictionary_generation']='COMPLETED'
    e[pre+'/source_capture.json']=json.dumps({k:v for k,v in c.items() if k!='source_directory'}).encode()
    e[directory+'/input_receipt.json']=json.dumps({k:v for k,v in check.items() if k!='directory'}).encode()
    e['probe_receipt.json']=json.dumps(r).encode();path=tmp_path/'review.zip';write_capsule(path,e)
    if defect=='none':
        result=m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
        assert m._source_view(result[0])[1]=='inputs/review/'*3
    else:
        with pytest.raises(ValueError):m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
