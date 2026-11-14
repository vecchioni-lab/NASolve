"""New capsule boundaries and the ignored branch-runner delivery destination."""
from copy import deepcopy
import hashlib,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
import pytest
from tests.test_cif_fragment_restoration import fixture
from tests.test_cif_base_rotation_audit import polynomial
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def setup_capsule(tmp_path,monkeypatch):
    from nasolve.cif_base_rotation_audit import audit_base_rotations,plan_base_rotations
    import nasolve.cif_corrected_geometry as qualified_module
    spec=importlib.util.spec_from_file_location('recovery_template',ROOT/'scripts/cif_numerical_recovery_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    (tmp_path/'fixture').mkdir()
    _,_,_,native,_=fixture(tmp_path/'fixture');p=native['geometry']['sites_cart_exact']
    native['geometry']['proxy_details']['bond_simple']=[{'i_seqs':[11,12],'distance_ideal':1.,'weight':100.,'origin_id':0,'atoms':[native['atoms'][i]['label'] for i in [11,12]]}]
    native['geometry']['proxy_counts']['bond_simple']=1;plan=plan_base_rotations(native,p)
    q=audit_base_rotations(polynomial,{'full_precision':p,'pdb_rounded':p},plan)
    q.update(status='REVIEW',rotation_derivative_qualification='SAMPLED_ROTATION_DERIVATIVES_PASS',constraint_signature_before='1'*64,constraint_signature_after='1'*64,
        installed_numeric_sources=[],installed_adapter_sources=[],installed_parallelity_sources=[],preflight_evaluations=17,audit_evaluation_calls=q['evaluation_calls'])
    q['evaluation_calls']+=17;q['max_evaluation_calls']=3000
    saved={'final_sites_cart':p,'endpoint_gradient_audit':{'cases':{label:{'families':{f:{'baseline':deepcopy(v)} for f,v in c['baseline'].items()}} for label,c in q['cases'].items()}}}
    proof={k:q[k] for k in ['constraint_signature_before','installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources']}
    # Earlier C24--C28 gates have their own complete fixtures/regressions. This
    # fixture isolates the new C29 boundary and raw rotation verifier.
    monkeypatch.setattr(qualified_module,'validate_continuation',lambda *args:True)
    previous={'geometry_trial':{'result':saved,'inputs':[]}}
    qualified={'native_correction_audit':{'result':proof}}
    monkeypatch.setattr(m,'_read_cedar28',lambda nested:(nested,qualified,previous))
    entries={'inputs/review/'+m.CURRENT_TRIAL_PREFIX+'/expected_inventory.json':json.dumps(native).encode()}
    inputs=[]
    for i,role in enumerate(['model']+['dictionary']*19+['phil']*13):
        name=f'inputs/{i:03d}_{role}.txt';data=('EXPLICIT_FAKE_'+role+str(i)).encode();entries[m.ROTATION_PREFIX+'/'+name]=data
        inputs.append({'anchor':'native_directory','path':name,'role':role,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
    previous['geometry_trial']['inputs']=inputs
    outputs=[]
    def artifact(name,data):
        entries[m.ROTATION_PREFIX+'/'+name]=data
        outputs.append({'anchor':'native_directory','path':name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
    for name in m.ROTATION_SOURCE_SHA256:
        target={'rotation_worker_py':'rotation_worker.py','native_worker_py':'native_worker.py'}.get(name,name)
        data=b'raise RuntimeError("CAPTURED CODE MUST NEVER EXECUTE")\n'+target.encode()
        m.ROTATION_SOURCE_SHA256[name]=hashlib.sha256(data).hexdigest();artifact(target,data)
    for name,value in [('expected_inventory.json',native),('native_validation.json',native),('gradient_validation.json',proof),('endpoint_validation.json',saved),
        ('rotation_spec.json',{'plan':plan,'correction_core_sha256':m.ROTATION_SOURCE_SHA256['correction_core.py']}),('rotation_result.json',q)]:artifact(name,json.dumps(value).encode())
    audit={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'inputs':inputs,'outputs':outputs,'result':q}
    entries[m.ROTATION_PREFIX+'/rotation_receipt.json']=json.dumps(audit).encode()
    r={'kind':'cif-fixed-na-base-rotation-probe','delivery_prefix':'29_Cedar','status':'REVIEW','analysis_completed':True,
        'native_execution':'COMPLETED','automatic_adoption':False,'policy_authority':'NARestraints','rotation_derivative_qualification':'SAMPLED_ROTATION_DERIVATIVES_PASS',
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'prerequisite_mechanics_replayed':True,
        'prior_archive':{'sha256':'1f553b4e57e75afbd8e29824600d470825a2b428c231a6bd0365c4319b05fb6c','verified_payloads':1104},
        'native_rotation_audit':audit,'rotation_plan':plan}
    r.update({k:'NOT_RUN' for k in ['model_editing','model_optimization','dictionary_generation','policy_recompilation','readyset_retry','refinement','installed_phenix_edits']})
    entries['probe_receipt.json']=json.dumps(r).encode();entries['base_rotation_plan.json']=json.dumps(plan).encode()
    for i in range(1173-len(entries)):entries[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    return m,entries


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','worker','snapshot','derivative','summary','signature','policy'])
def test_new_capsule_gate_rechecks_sources_arrays_and_raw_evidence(tmp_path,monkeypatch,defect):
    m,entries=setup_capsule(tmp_path,monkeypatch);path=tmp_path/'review.zip'
    if defect=='unsafe':entries['../escape']=entries.pop('padding/000.txt')
    elif defect=='worker':
        name=m.ROTATION_PREFIX+'/rotation_worker.py';entries[name]=b'COHERENT_CHANGED_WORKER'
        r=json.loads(entries['probe_receipt.json']);row=next(v for v in r['native_rotation_audit']['outputs'] if v['path']=='rotation_worker.py');row.update(size=len(entries[name]),sha256=hashlib.sha256(entries[name]).hexdigest())
        entries[m.ROTATION_PREFIX+'/rotation_receipt.json']=json.dumps(r['native_rotation_audit']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
    elif defect in {'snapshot','derivative','summary','signature','policy'}:
        r=json.loads(entries['probe_receipt.json']);a=r['native_rotation_audit'];q=a['result']
        if defect=='snapshot':q['cases']['full_precision']['baseline']['all']['gradient'][0]+=1.
        if defect=='derivative':q['cases']['full_precision']['groups'][0]['profile'][0]['derivative']['samples'][0]['plus_target']+=100.
        if defect=='summary':q['cases']['full_precision']['groups'][0]['lowest_sampled_target']['target']=-3.
        if defect=='signature':q['constraint_signature_after']='2'*64
        if defect=='policy':r['policy_recompilation']='ATTEMPTED'
        data=json.dumps(q).encode();entries[m.ROTATION_PREFIX+'/rotation_result.json']=data
        row=next(v for v in a['outputs'] if v['path']=='rotation_result.json');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
        entries[m.ROTATION_PREFIX+'/rotation_receipt.json']=json.dumps(a).encode();entries['probe_receipt.json']=json.dumps(r).encode()
    write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    if defect=='payload':
        with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
        data['padding/000.txt']=b'CHANGED'
        with zipfile.ZipFile(path,'w') as z:
            for n,v in data.items():z.writestr(n,v)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert m._read_capsule(path,expected)[3]['delivery_prefix']=='29_Cedar'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


@pytest.mark.parametrize('mode',['older_checkout','tracked_rule','existing','outside','symlink','not_root'])
def test_branch_artifact_destination_is_ignored_without_touching_tracked_checkout(tmp_path,mode):
    sys.path.insert(0,str(ROOT/'scripts'));from build_synthetic_dna_shuttle import prepare_branch_runner_destination
    checkout=tmp_path/'checkout';checkout.mkdir();subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
    (checkout/'README').write_text('PRESERVE');(checkout/'.gitignore').write_text('/branch-artifacts/\n' if mode=='tracked_rule' else '# OLD CHECKOUT\n')
    subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    exclude=checkout/'.git/info/exclude';previous=exclude.read_bytes()+b'# private rule without newline';exclude.write_bytes(previous)
    before=(checkout/'.gitignore').read_bytes();output=checkout/'branch-artifacts/cedar/runners/30_Cedar_probe.py';selected=checkout
    if mode=='existing':output.parent.mkdir(parents=True);output.write_text('PRESERVE')
    if mode=='outside':output=tmp_path/'outside/branch-artifacts/cedar/runners/x.py'
    if mode=='symlink':(checkout/'branch-artifacts').symlink_to(tmp_path,target_is_directory=True)
    if mode=='not_root':selected=checkout/'subdir';selected.mkdir();output=selected/'branch-artifacts/cedar/runners/x.py'
    if mode in {'older_checkout','tracked_rule'}:
        prepare_branch_runner_destination(selected,output)
        assert subprocess.run(['git','-C',str(checkout),'check-ignore','-q',str(output)]).returncode==0
        after=exclude.read_bytes();prepare_branch_runner_destination(selected,output);assert exclude.read_bytes()==after
        assert after==(previous+b'\n/branch-artifacts/\n' if mode=='older_checkout' else previous)
    else:
        with pytest.raises((ValueError,FileExistsError)):prepare_branch_runner_destination(selected,output)
        assert exclude.read_bytes()==previous
    assert (checkout/'.gitignore').read_bytes()==before and (checkout/'README').read_text()=='PRESERVE'
    assert not subprocess.run(['git','-C',str(checkout),'status','--short','--untracked-files=no'],capture_output=True,text=True).stdout
