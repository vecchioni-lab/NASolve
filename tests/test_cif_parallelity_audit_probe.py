"""Cedar 23 provenance and relocated source-bundle checks for Cedar 24."""
import hashlib,importlib.util,json,os
from pathlib import Path
import shutil,subprocess,sys,zipfile
import pytest
from tests.test_cif_gradient_audit_probe import capsule as geometry_capsule
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('parallelity_template',ROOT/'scripts/cif_parallelity_audit_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(directory):
    m=template();old=geometry_capsule(directory/'geometry')
    with zipfile.ZipFile(old) as z:prior={name:z.read(name) for name in z.namelist()}
    geometry=json.loads(prior['probe_receipt.json']);trial=geometry['geometry_trial']
    expected=json.loads(prior[m.GEOMETRY_PREFIX+'/expected_inventory.json']);points=trial['result']['final_sites_cart']
    cases={'full_precision':points,'pdb_rounded':[[float('%.3f'%v) for v in p] for p in points]}
    baseline={'target':1.,'gradient':[0.]*(3*expected['atom_count'])}
    result={'policy_id':'cif-fixed-native-gradient-audit-v1','status':'REVIEW','analysis_completed':True,'captured_inventory_matches':True,
            'model_optimization':'NOT_RUN','automatic_adoption':False,'evaluation_calls':2734,
            'constraint_signature_before':'1'*64,'constraint_signature_after':'1'*64,
            'installed_numeric_sources':[],
            'cases':{label:{'families':{'parallelity':{'baseline':baseline}},'baseline_repeats_consistent':True,'captured_snapshot_match':{'consistent':True}} for label in cases}}
    entries={'inputs/review/'+name:payload for name,payload in prior.items()};inputs=[];outputs=[]
    for row in trial['inputs']:
        payload=prior[m.GEOMETRY_PREFIX+'/'+row['path']];entries[m.CAPTURE_PREFIX+'/'+row['path']]=payload;inputs.append(row)
    for name,value in [('expected_inventory.json',expected),('native_validation.json',expected),('gradient_result.json',result),
                       ('gradient_spec.json',{'coordinate_cases':cases,'expected_numeric_sources':[]})]:
        payload=json.dumps(value).encode();entries[m.CAPTURE_PREFIX+'/'+name]=payload
        outputs.append({'anchor':'native_directory','path':name,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
    audit={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
           'inputs':inputs,'outputs':outputs,'result':result}
    entries[m.CAPTURE_PREFIX+'/gradient_receipt.json']=json.dumps(audit).encode()
    receipt={'kind':'cif-native-gradient-audit-probe','delivery_prefix':'23_Cedar','analysis_completed':True,'status':'REVIEW',
             'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_optimization':'NOT_RUN',
             'automatic_adoption':False,'prior_convergence':'NOT_CONVERGED_ERROR','prerequisite_mechanics_replayed':True,
             'policy_authority':'NARestraints','native_gradient_audit':audit}
    entries['probe_receipt.json']=json.dumps(receipt).encode()
    for i in range(670-len(entries)):entries[f'padding/{i:03d}.txt']=b'SYNTHETIC'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','verdict','prior','native_input','saved_coordinate','manager'])
def test_parallelity_capsule_preserves_all_prior_evidence(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            r=json.loads(entries['probe_receipt.json']);r['model_optimization']='EXPLICIT_BOUNDED_TRIAL';entries['probe_receipt.json']=json.dumps(r).encode()
        if defect=='prior':entries['inputs/review/padding/000.txt']=b'CHANGED'
        if defect=='native_input':entries[m.CAPTURE_PREFIX+'/inputs/000_model.pdb']=b'CHANGED'
        if defect=='saved_coordinate':
            name=m.CAPTURE_PREFIX+'/gradient_spec.json';r=json.loads(entries[name]);r['coordinate_cases']['full_precision'][0][0]+=1.;entries[name]=json.dumps(r).encode()
        if defect=='manager':
            name=m.CAPTURE_PREFIX+'/expected_inventory.json';r=json.loads(entries[name]);r['atom_count']+=1;entries[name]=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,payload in entries.items():z.writestr(name,payload)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert len(m._read_capsule(path,expected)[0])==671
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_parallelity_shuttle_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();(root/'scripts/cif_parallelity_audit_probe_template.py').write_text((ROOT/'scripts/cif_parallelity_audit_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'24_Cedar_probe_cif_parallelity_audit.py'
    metadata=build(root,nar,runner,template_name='cif_parallelity_audit_probe_template.py')
    assert metadata['delivery_prefix']=='24_Cedar' and metadata['kind']=='cif-native-parallelity-audit-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['prerequisite_mechanics_replayed'] and receipt['frozen_inputs_preserved'] and receipt['original_archive_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN' and receipt['automatic_adoption'] is False
    assert receipt['toy_plane_sizes']==[[4,4],[4,6],[6,4]] and receipt['prior_convergence']=='NOT_CONVERGED_ERROR'
