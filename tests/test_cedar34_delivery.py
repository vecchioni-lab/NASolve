"""The stereo action preserves the failed DP and nonconverged PDU evidence."""
from copy import deepcopy
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar33_delivery import installed_contract_capsule
from tests.test_cif_geometry_review_probe import write_capsule


def completed_single_block(tmp_path,monkeypatch):
    m,old=installed_contract_capsule(tmp_path,monkeypatch);path=tmp_path/'old.zip';write_capsule(path,old)
    with zipfile.ZipFile(path) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    parent=json.loads(old['probe_receipt.json']);r=deepcopy(parent)
    r.update(build={'fixture':'EXPLICIT_FAKE_C33_BUILD'},delivery_prefix='33_Cedar',
        requested_action='SINGLE_BLOCK_NUMERICAL_GENERATION',native_execution='READ_ONLY_INPUT_CHECKS_AND_NUMERICAL_GENERATION',
        dictionary_generation='REVIEW_REQUIRED',prior_archive={'sha256':m.CEDAR32_SHA256,'verified_payloads':1229},
        candidates={},native_input_checks={},single_block_options={},single_block_control={'steps':180,'source_contract_archive':m.CEDAR32_SHA256,'tolerance':'UNCHANGED'})
    m.CEDAR33_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    pre=parent['installed_elbow_contract']['source_directory']['path']
    for name in [*m.ELBOW_SOURCE_SHA256,'source_capture.json']:e[pre+'/'+name]=old[pre+'/'+name]
    original_view,_=m._source_view(old)
    for code,(pre,gd,_) in list(m.CEDAR33_CASES.items()):
        consumer=('FAKE_CONSUMER33_'+code).encode();digest=sha256(consumer).hexdigest();m.CEDAR33_CASES[code]=(pre,gd,digest)
        cp='read_only/'+code
        def add(prefix,name,data,outputs,anchor='candidate_directory'):
            e[prefix+'/'+name]=data;outputs.append({'anchor':anchor,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)})
        ro=[];add(cp,'source.cif',consumer,ro,'contract_directory')
        check={'status':'PARSER_READ_ONLY_PASS','execution':{'returncode':0},'source_preserved':True,'frozen_source_preserved':True,
            'executable_preserved':True,'dictionary_generation':'NOT_RUN','model_optimization':'NOT_RUN','automatic_adoption':False,'outputs':ro}
        e[cp+'/input_receipt.json']=json.dumps(check).encode();r['native_input_checks'][code]={**check,'directory':{'anchor':'probe_directory','path':cp}}
        od='options/'+code;data=b'# FAKE_INSTALLED_OPTIONS_NOT_EXECUTED\n';m.CEDAR33_OPTIONS_SHA256=sha256(data).hexdigest()
        e[od+'/options_parser.py.txt']=data
        options={'status':'SINGLE_BLOCK_OPTIONS_PASS','steps':180,'effective_blocks':1,'macro_override':False,'tolerance':False,
            'optimization_execution':'NOT_RUN','captured_code_execution':'NOT_RUN','convergence_claimed':False,
            'source':{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/elbow/utilities/options_parser.py','sha256':m.CEDAR33_OPTIONS_SHA256,'size':len(data)}}
        e[od+'/options_receipt.json']=json.dumps(options).encode()
        e[od+'/options_result.json']=json.dumps({'steps':180,'macro_override':False,'tolerance':False,'module_sha256':m.CEDAR33_OPTIONS_SHA256}).encode()
        r['single_block_options'][code]={**options,'directory':{'anchor':'probe_directory','path':od}}
        gp=pre+'/generation/'+gd;co=[];go=[]
        original=original_view[m.ROTATION_PREFIX+'/inputs/004_dictionary.cif'] if code=='DP' else old['inputs/review/component_controls/sources/PDU.cif']
        add(pre,'original/source.cif',original,co);add(pre,'graph/source.cif',b'FAKE_GRAPH33_'+code.encode(),co)
        add(pre,'consumer/source.cif',consumer,co)
        e['graph_preview/'+code+'/source.cif']=e[pre+'/graph/source.cif'];e['consumer_preview/'+code+'/source.cif']=consumer
        add(gp,'source.cif',consumer,go)
        log=b'Chiralise ChiralClass.py assert len(atoms) in [4,5] AssertionError' if code=='DP' else b'geometry not converged'
        add(gp,'elbow.log',log,go)
        if code=='PDU':
            candidate=b'FAKE_CANDIDATE33_NEVER_EXECUTED';add(gp,'candidate.cif',candidate,go)
            m.CEDAR33_PDU_CANDIDATE_SHA256=sha256(candidate).hexdigest()
            go.append({'anchor':'candidate_directory','path':'candidate.pickle','size':4,'sha256':sha256(b'FAKE').hexdigest()})
            e['component_controls/sources/PDU.cif']=original
        g={'execution':{'status':'FAILED' if code=='DP' else 'COMPLETED','returncode':1 if code=='DP' else 0},
           'source_preserved':True,'frozen_source_preserved':True,'outputs':go,
           'optimization_control':{'single_block_steps':180},'optimization_stopping':{'status':'NOT_REPORTED' if code=='DP' else 'NOT_CONVERGED_REPORTED'}}
        e[gp+'/generation_receipt.json']=json.dumps(g).encode()
        co.extend({**row,'path':'generation/'+gd+'/'+row['path']} for row in go)
        co.append({'anchor':'candidate_directory','path':'generation/'+gd+'/generation_receipt.json','sha256':sha256(e[gp+'/generation_receipt.json']).hexdigest(),'size':len(e[gp+'/generation_receipt.json'])})
        c={'status':'REJECTED' if code=='DP' else 'CANDIDATE_REVIEW','source_preserved':True,'automatic_adoption':False,
           'source_sha256':sha256(original).hexdigest(),'source_size':len(original),'generation':g,'outputs':co}
        e[pre+'/numerical_recovery_receipt.json']=json.dumps(c).encode();r['candidates'][code]=c
    e['probe_receipt.json']=json.dumps(r).encode()
    for i in range(1288-len(e)):e[f'padding/{i:03d}.txt']=b'FAKE_C33_PADDING'
    return m,e


@pytest.mark.parametrize('defect',['none','build','adoption','policy','prior','consumer','installed_capture','option_steps','option_tolerance','parsed_options','read_only_outcome','dp_phase','pdu_stopping','pdu_candidate','pickle','unsafe_output'])
def test_returned_trial_gate_preserves_both_failure_phases_and_rechecks_sources(tmp_path,monkeypatch,defect):
    m,e=completed_single_block(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json'])
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='adoption':r['automatic_adoption']=True
    if defect=='policy':r['policy_authority']='GUESSED'
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    if defect=='consumer':e['consumer_preview/DP/source.cif']=b'CHANGED'
    if defect=='installed_capture':e['native_contract/installed_sources/'+next(iter(m.ELBOW_SOURCE_SHA256))]=b'CHANGED'
    o=r['single_block_options']['PDU'];od=o['directory']['path']
    if defect=='option_steps':o['steps']=360
    if defect=='option_tolerance':o['tolerance']=100
    if defect=='parsed_options':
        parsed=json.loads(e[od+'/options_result.json']);parsed['macro_override']=3;e[od+'/options_result.json']=json.dumps(parsed).encode()
    e[od+'/options_receipt.json']=json.dumps({k:v for k,v in o.items() if k!='directory'}).encode()
    if defect=='read_only_outcome':r['native_input_checks']['DP']['status']='REVIEW'
    if defect=='dp_phase':r['candidates']['DP']['generation']['execution']['status']='COMPLETED'
    if defect=='pdu_stopping':r['candidates']['PDU']['generation']['optimization_stopping']['status']='CONVERGED'
    if defect=='unsafe_output':r['candidates']['PDU']['outputs'][0]['path']='../outside'
    pre,gd,_=m.CEDAR33_CASES['PDU'];gp=pre+'/generation/'+gd
    if defect=='pdu_candidate':e[gp+'/candidate.cif']=b'CHANGED'
    if defect=='pickle':e[gp+'/candidate.pickle']=b'FAKE'
    e['probe_receipt.json']=json.dumps(r).encode();path=tmp_path/'trial.zip';write_capsule(path,e)
    if defect=='none':
        result=m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
        assert m._source_view(result[0])[1]=='inputs/review/'*4
    else:
        with pytest.raises((ValueError,KeyError)):m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
