"""A generation failure stays visible while the next pinned control is bundled."""
from copy import deepcopy
from hashlib import sha256
import json,sys,zipfile,subprocess
from pathlib import Path
import pytest
from tests.test_cif_numerical_recovery_probe import setup_capsule
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def failed_generation_capsule(tmp_path,monkeypatch):
    m,old=setup_capsule(tmp_path,monkeypatch)
    original=b'EXPLICIT_FAKE_ORIGINAL_DP';graph=b'EXPLICIT_FAKE_GRAPH_DP'
    old[m.ROTATION_PREFIX+'/inputs/004_dictionary.cif']=original;old.pop('padding/000.txt')
    prior=tmp_path/'old.zip';write_capsule(prior,old)
    with zipfile.ZipFile(prior) as z:entries={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    p=m.CEDAR30_RECOVERY_PREFIX;gp=m.CEDAR30_GENERATION_PREFIX;go=[];co=[]
    def artifact(prefix,name,data,outputs):
        entries[prefix+'/'+name]=data;outputs.append({'anchor':'candidate_directory','path':name,'sha256':sha256(data).hexdigest(),'size':len(data)})
    artifact(p,'original/source.cif',original,co);artifact(p,'graph/source.cif',graph,co)
    artifact(gp,'source.cif',graph,go)
    artifact(gp,'elbow.log',b"AttributeError: 'empty' object has no attribute 'pdbx_model_Cartn_x_ideal'",go)
    g={'status':'FAILED','execution':{'status':'FAILED','returncode':1},'source_preserved':True,'frozen_source_preserved':True,'outputs':go}
    artifact(gp,'generation_receipt.json',json.dumps(g).encode(),co)
    # The recovery receipt's descriptors are relative to its own directory.
    co[-1]['path']='generation/'+gp.rsplit('/',1)[-1]+'/generation_receipt.json'
    c={'status':'REJECTED','source_preserved':True,'generation':g,'outputs':co}
    entries[p+'/numerical_recovery_receipt.json']=json.dumps(c).encode()
    build={'fixture':'C30_BUILD_NOT_EXECUTABLE'};m.CEDAR30_BUILD_SHA256=sha256(json.dumps(build,sort_keys=True,separators=(',',':')).encode()).hexdigest();m.CEDAR30_GRAPH_SHA256=sha256(graph).hexdigest()
    r={'build':build,'kind':'cif-source-graph-numerical-recovery-probe','delivery_prefix':'30_Cedar','status':'REVIEW','analysis_completed':True,
       'automatic_adoption':False,'policy_authority':'NARestraints','original_archive_preserved':True,'frozen_inputs_preserved':True,'prerequisite_mechanics_replayed':True,
       'dictionary_generation':'REVIEW_REQUIRED','prior_archive':{'sha256':m.REVIEW_SHA256,'verified_payloads':1173},'candidates':{'DP':c}}
    r.update({k:'NOT_RUN' for k in ['model_editing','model_optimization','native_execution','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry']})
    entries['probe_receipt.json']=json.dumps(r).encode()
    for i in range(1185-len(entries)):entries[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    return m,entries


@pytest.mark.parametrize('defect',['none','source','graph','build','output','phase','candidate','evidence','prior'])
def test_prior_generation_failure_requires_exact_preserved_lineage_and_artifacts(tmp_path,monkeypatch,defect):
    m,e=failed_generation_capsule(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json']);p=m.CEDAR30_RECOVERY_PREFIX;gp=m.CEDAR30_GENERATION_PREFIX
    if defect=='source':e[p+'/original/source.cif']=b'CHANGED'
    if defect=='graph':e[p+'/graph/source.cif']=b'CHANGED'
    if defect=='build':r['build']['fixture']='CHANGED';e['probe_receipt.json']=json.dumps(r).encode()
    if defect=='output':
        r['candidates']['DP']['outputs'][0]['sha256']='0'*64;e[p+'/numerical_recovery_receipt.json']=json.dumps(r['candidates']['DP']).encode();e['probe_receipt.json']=json.dumps(r).encode()
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    if defect in {'phase','candidate','evidence'}:
        c=r['candidates']['DP'];g=c['generation']
        if defect=='phase':g['execution']['returncode']=0
        if defect=='candidate':e['generation/UNEXPECTED/candidate.cif']=b'UNEXPECTED';e.pop('padding/000.txt')
        if defect=='evidence':
            data=b'NO_RECORDED_PARSER_EVIDENCE';e[gp+'/elbow.log']=data
            row=next(x for x in g['outputs'] if x['path']=='elbow.log');row.update(size=len(data),sha256=sha256(data).hexdigest())
        data=json.dumps(g).encode();e[gp+'/generation_receipt.json']=data
        row=next(x for x in c['outputs'] if x['path'].endswith('generation_receipt.json'));row.update(size=len(data),sha256=sha256(data).hexdigest())
        e[p+'/numerical_recovery_receipt.json']=json.dumps(c).encode();e['probe_receipt.json']=json.dumps(r).encode()
    path=tmp_path/'review.zip';write_capsule(path,e)
    if defect=='none':
        result=m._read_capsule(path,sha256(path.read_bytes()).hexdigest());assert result[3]['delivery_prefix']=='29_Cedar'
        assert m._source_view(result[0])[1]=='inputs/review/'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,sha256(path.read_bytes()).hexdigest())


@pytest.mark.parametrize('defect',['none','bytes','missing_fixture','duplicate','wrong_template'])
def test_only_explicit_hash_pinned_public_control_can_enter_source_bundle(tmp_path,defect):
    import shutil,restraints
    sys.path.insert(0,str(ROOT/'scripts'));from build_synthetic_dna_shuttle import build
    root=tmp_path/'source';nar=tmp_path/'nar'
    for rel in ['src','MR_frames/5W6W','docs/recipes','tests/fixtures/public_ccd']:
        shutil.copytree(ROOT/rel,root/rel,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/cif_numerical_recovery_probe_template.py',root/'scripts/cif_numerical_recovery_probe_template.py')
    shutil.copyfile(ROOT/'docs/cif-doctor-ccd-controls.json',root/'docs/cif-doctor-ccd-controls.json')
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],check=True,capture_output=True)
    if defect=='bytes':(root/'tests/fixtures/public_ccd/PDU.cif').write_text('CHANGED')
    if defect=='missing_fixture':
        p=root/'docs/cif-doctor-ccd-controls.json';d=json.loads(p.read_text());next(c for c in d['components'] if c['code']=='PDU').pop('test_fixture');p.write_text(json.dumps(d))
    target=tmp_path/'31_Cedar.py';template='cif_numerical_recovery_probe_template.py' if defect!='wrong_template' else 'cif_base_rotation_probe_template.py'
    codes=('PDU','PDU') if defect=='duplicate' else ('PDU',)
    if defect=='none':
        r=build(root,nar,target,template_name=template,delivery_prefix='31_Cedar',component_controls=codes)
        assert r['delivery_prefix']=='31_Cedar' and r['component_controls'][0]['component']=='PDU'
        assert r['component_controls'][0]['sha256']=='cd192f18964a28c628544ae1c0b4b1f2aed124e1b90a21b9c6ca0aa4458c0292'
        assert 'controls/PDU.cif' in r['runtime_files'] and not any('/data/ligands/PDU.cif' in n for n in r['runtime_files'])
    else:
        with pytest.raises(ValueError):build(root,nar,target,template_name=template,delivery_prefix='31_Cedar',component_controls=codes)
        assert not target.exists()
