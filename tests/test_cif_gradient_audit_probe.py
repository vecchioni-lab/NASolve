"""Safe capsule binding and source-bundled inspection without native Phenix."""
from copy import deepcopy
import hashlib,importlib.util,json,os
from pathlib import Path
import shutil,subprocess,sys,zipfile
import pytest
from tests.test_cif_fragment_restoration import fixture
from tests.test_cif_fixed_geometry import policy_inventory
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('gradient_template',ROOT/'scripts/cif_gradient_audit_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def capsule(directory):
    from nasolve.cif_fixed_geometry import write_geometry_candidate,qualify_fixed_policy_geometry
    directory.mkdir(parents=True);m=template();_,model,_,native,_=fixture(directory);policy_inventory(native)
    native['geometry']['custom_proxy_requests']=[]
    output=directory/'candidate.pdb';serialization=write_geometry_candidate(model,output,native,native['geometry']['sites_cart_exact'])
    mechanics=qualify_fixed_policy_geometry(native,native,output,serialization);assert mechanics['mechanics_checks_pass']
    entries={f'inputs/review/padding/{i:03d}':b'SYNTHETIC_PRIOR' for i in range(491)}
    entries['inputs/review/manifest.json']=json.dumps({n.removeprefix('inputs/review/'):{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in entries.items()}).encode()
    result={'status':'REVIEW','captured_inventory_matches':True,'policy_inventory':True,'constraint_signature_before':'synthetic_fixed',
        'constraint_signature_after':'synthetic_fixed','final_sites_cart':native['geometry']['sites_cart_exact'],
        'initial':{'target':1.,'gradient_norm':2.},'final':{'target':1.,'gradient_norm':2.},'serialized':{'target':1.,'gradient_norm':2.},'installed_optimizer_sources':[],
        'stopping':{'reason':'unreported','error':'EXPLICIT_FAKE_LINE_SEARCH','native_criterion_met':False,'iterations':905,'max_iterations':1000}}
    receipts=[]
    for prefix in [m.CAPTURE_PREFIX,m.NATIVE_PREFIX]:
        inputs=[];outputs=[]
        data=[('model',model.read_bytes())]+[('dictionary',b'data_comp_ZZZ\n_chem_comp.id ZZZ\n')]*19+[('phil',b'# frozen fixture\n')]*13
        for i,(role,payload) in enumerate(data):
            name=f'inputs/{i:03d}_{role}'+{'model':'.pdb','dictionary':'.cif','phil':'.phil'}[role]
            entries[prefix+'/'+name]=payload;inputs.append({'role':role,'anchor':'native_directory','path':name,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
        values=[('native_validation.json',native)]
        if prefix==m.CAPTURE_PREFIX:values += [('expected_inventory.json',native),('geometry_result.json',result)]
        for name,value in values:
            payload=json.dumps(value).encode();entries[prefix+'/'+name]=payload
            outputs.append({'anchor':'native_directory','path':name,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
        receipt={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'inputs':inputs,'outputs':outputs,'native_validation':native}
        if prefix==m.CAPTURE_PREFIX:receipt['result']=result
        entries[prefix+('/geometry_receipt.json' if prefix==m.CAPTURE_PREFIX else '/native_receipt.json')]=json.dumps(receipt).encode();receipts.append(receipt)
    entries['candidate/na_policy_geometry_model.pdb']=output.read_bytes()
    entries['native_mechanics.json']=json.dumps(mechanics).encode()
    prior={'kind':'cif-na-policy-geometry-probe','delivery_prefix':'22_Cedar','analysis_completed':True,'status':'REVIEW',
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_optimization':'EXPLICIT_BOUNDED_TRIAL',
        'automatic_adoption':False,'convergence':'NOT_CONVERGED_ERROR','geometry_trial':receipts[0],'native_roundtrip':receipts[1],
        'native_mechanics':mechanics,'serialization':serialization}
    entries['probe_receipt.json']=json.dumps(prior).encode()
    for i in range(609-len(entries)):entries[f'padding/{i:03d}.txt']=b'SYNTHETIC'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','verdict','prior','native_input'])
def test_gradient_capsule_refuses_changed_evidence(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            r=json.loads(entries['probe_receipt.json']);r['convergence']='NATIVE_CRITERION_MET';entries['probe_receipt.json']=json.dumps(r).encode()
        if defect=='prior':entries['inputs/review/padding/000']=b'CHANGED'
        if defect=='native_input':entries[m.CAPTURE_PREFIX+'/inputs/000_model.pdb']=b'CHANGED'
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,value in entries.items():z.writestr(name,value)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert m._read_capsule(path,expected)[1]['convergence']=='NOT_CONVERGED_ERROR'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_gradient_shuttle_inspects_after_both_builds_are_deleted(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest();root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();(root/'scripts/cif_gradient_audit_probe_template.py').write_text((ROOT/'scripts/cif_gradient_audit_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True);subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'23_Cedar_probe_cif_gradient_audit.py';metadata=build(root,nar,runner,template_name='cif_gradient_audit_probe_template.py')
    assert metadata['delivery_prefix']=='23_Cedar' and metadata['kind']=='cif-native-gradient-audit-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['prerequisite_mechanics_replayed'] and receipt['frozen_inputs_preserved'] and receipt['original_archive_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN' and receipt['automatic_adoption'] is False
    assert receipt['prior_convergence']=='NOT_CONVERGED_ERROR'
