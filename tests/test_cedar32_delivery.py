"""C31 retains two distinct execution failures and excludes serialized objects."""
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar31_delivery import failed_generation_capsule
from tests.test_cif_geometry_review_probe import write_capsule


def two_failed_candidates(tmp_path,monkeypatch):
    m,old=failed_generation_capsule(tmp_path,monkeypatch)
    p=tmp_path/'old.zip';write_capsule(p,old)
    with zipfile.ZipFile(p) as z:entries={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    source,_=m._source_view(old);dp=source[m.ROTATION_PREFIX+'/inputs/004_dictionary.cif']
    public=b'EXPLICIT_FAKE_PUBLIC_PDU_NEVER_EXECUTED';m.PDU_SOURCE_SHA256=sha256(public).hexdigest()
    r={'build':{'fixture':'EXPLICIT_FAKE_BUILD_C31'},'kind':'cif-source-graph-numerical-recovery-probe',
       'delivery_prefix':'31_Cedar','status':'REVIEW','analysis_completed':True,'automatic_adoption':False,
       'policy_authority':'NARestraints','original_archive_preserved':True,'frozen_inputs_preserved':True,
       'prerequisite_mechanics_replayed':True,'dictionary_generation':'REVIEW_REQUIRED',
       'prior_archive':{'sha256':m.CEDAR30_SHA256,'verified_payloads':1185},'candidates':{},'component_controls':{}}
    r.update({k:'NOT_RUN' for k in ['model_editing','model_optimization','native_execution','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry']})
    m.CEDAR31_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for code,(prefix,generatedir,_) in list(m.CEDAR31_CASES.items()):
        gp=prefix+'/generation/'+generatedir;graph=('EXPLICIT_FAKE_GRAPH_C31_'+code).encode()
        m.CEDAR31_CASES[code]=(prefix,generatedir,sha256(graph).hexdigest())
        original=dp if code=='DP' else public;go=[];co=[]
        def add(pre,name,data,outputs):
            entries[pre+'/'+name]=data;outputs.append({'anchor':'candidate_directory','path':name,'size':len(data),'sha256':sha256(data).hexdigest()})
        add(prefix,'original/source.cif',original,co);add(prefix,'graph/source.cif',graph,co)
        add(gp,'source.cif',graph,go);entries['graph_preview/'+code+'/source.cif']=graph
        log=("AttributeError: 'empty' object has no attribute 'alt_atom_id'" if code=='DP' else
             "38 atoms\n39 bonds\n3 chirals : R S R\ngeometry not converged\nUnboundLocalError: cannot access local variable 'smc'").encode()
        add(gp,'elbow.log',log,go)
        if code=='PDU':
            add(gp,'candidate.elbow_opt.xyz',b'',go)
            for name in ['candidate.options.pickle','candidate.pickle']:
                go.append({'anchor':'candidate_directory','path':name,'size':25,'sha256':sha256(b'FAKE_EXCLUDED_NOT_EXECUTED').hexdigest()})
            control={'graph_status':'PASS','policy_status':'PASS','source_sha256':m.PDU_SOURCE_SHA256}
            entries['component_controls/sources/PDU.cif']=public
            entries['component_controls/PDU_control.json']=json.dumps(control).encode();r['component_controls']['PDU']=control
        g={'status':'FAILED','execution':{'status':'FAILED','returncode':1},'source_preserved':True,'frozen_source_preserved':True,'outputs':go}
        entries[gp+'/generation_receipt.json']=json.dumps(g).encode()
        co.append({'anchor':'candidate_directory','path':'generation/'+generatedir+'/generation_receipt.json',
                   'size':len(entries[gp+'/generation_receipt.json']),'sha256':sha256(entries[gp+'/generation_receipt.json']).hexdigest()})
        c={'status':'REJECTED','source_preserved':True,'generation':g,'outputs':co};r['candidates'][code]=c
        entries[prefix+'/numerical_recovery_receipt.json']=json.dumps(c).encode()
    entries['probe_receipt.json']=json.dumps(r).encode()
    for i in range(1209-len(entries)):entries[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    return m,entries


@pytest.mark.parametrize('defect',['none','build','scope','source','graph','control','xyz','parser_evidence','optimizer_evidence','pickle_included','phase','prior'])
def test_two_failure_boundary_rechecks_phase_artifacts_and_preserved_lineage(tmp_path,monkeypatch,defect):
    m,e=two_failed_candidates(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json'])
    code='PDU' if defect in {'control','xyz','optimizer_evidence','pickle_included'} else 'DP'
    prefix,generatedir,_=m.CEDAR31_CASES[code];gp=prefix+'/generation/'+generatedir
    c=r['candidates'][code];g=c['generation']
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='scope':r['candidates'].pop('DP')
    if defect=='source':e[prefix+'/original/source.cif']=b'CHANGED'
    if defect=='graph':e[prefix+'/graph/source.cif']=b'CHANGED'
    if defect=='control':
        r['component_controls']['PDU']['policy_status']='REVIEW';e['component_controls/PDU_control.json']=json.dumps(r['component_controls']['PDU']).encode()
    if defect=='xyz':e[gp+'/candidate.elbow_opt.xyz']=b'NOT_EMPTY'
    if defect in {'parser_evidence','optimizer_evidence'}:e[gp+'/elbow.log']=b'MISSING_RECORDED_FAILURE'
    if defect=='pickle_included':e[gp+'/candidate.pickle']=b'FAKE_EXCLUDED_NOT_EXECUTED';e.pop('padding/000.txt')
    if defect=='phase':g['execution']['returncode']=0
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    for row in g['outputs']:
        name=gp+'/'+row['path']
        if name in e:row.update(size=len(e[name]),sha256=sha256(e[name]).hexdigest())
    e[gp+'/generation_receipt.json']=json.dumps(g).encode()
    for row in c['outputs']:
        name=prefix+'/'+row['path']
        if name in e:row.update(size=len(e[name]),sha256=sha256(e[name]).hexdigest())
    e[prefix+'/numerical_recovery_receipt.json']=json.dumps(c).encode()
    e['probe_receipt.json']=json.dumps(r).encode();path=tmp_path/'review.zip';write_capsule(path,e)
    if defect=='none':
        result=m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
        assert result[3]['delivery_prefix']=='29_Cedar'
        assert m._source_view(result[0])[1]=='inputs/review/inputs/review/'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,sha256(path.read_bytes()).hexdigest())
