"""Cedar 26 must preserve and replay the exact prior correction capsule."""
import hashlib,importlib.util,json,os
from pathlib import Path
import shutil,subprocess,sys,zipfile
import pytest
from tests.test_cif_corrected_gradient_probe import capsule as prior_capsule
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('order_template',ROOT/'scripts/cif_plane_order_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(directory):
    m=template();old=prior_capsule(directory/'prior')
    with zipfile.ZipFile(old) as z:prior={n:z.read(n) for n in z.namelist()}
    previous=json.loads(prior['probe_receipt.json'])['native_parallelity_audit'];old_result=previous['result']
    expected=json.loads(prior[m.CAPTURE_PREFIX+'/expected_inventory.json']);count=expected['atom_count']
    coordinates={'initial':expected['geometry']['sites_cart_exact'],**json.loads(prior[m.CAPTURE_PREFIX+'/parallelity_spec.json'])['coordinate_cases']}
    result={'status':'REVIEW','policy_id':'cif-fixed-native-corrected-gradient-audit-v1',
        'correction_policy_id':'native-parallelity-complete-accumulation-v1','correction_qualification':'DERIVATIVE_REVIEW',
        'analysis_completed':True,'captured_inventory_matches':True,'model_optimization':'NOT_RUN','automatic_adoption':False,
        'evaluation_calls':4101,'correction_statistics':{'max_energy_change':0.},'constraint_signature_before':'1'*64,
        'constraint_signature_after':'1'*64,'cases':{},'raw_baseline_checks':{},
        **{k:old_result[k] for k in ['installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources']}}
    for label in coordinates:
        result['raw_baseline_checks'][label]={'target':1.,'native_gradient_norm':2.,'captured_raw_baseline_match':True}
        families={name:{'baseline':{'target':1.}} for name in ['all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded']}
        families['parallelity']['baseline']['parallelity_correction']={'plane_gradient':[0.]*(3*count),'native_plane_gradient':[0.]*(3*count)}
        result['cases'][label]={'families':families}
    entries={'inputs/review/'+n:data for n,data in prior.items()};outputs=[]
    for row in previous['inputs']:entries[m.CORRECTION_PREFIX+'/'+row['path']]=prior[m.CAPTURE_PREFIX+'/'+row['path']]
    for name in ['parallelity.h','parallelity_bpl.cpp']:
        relative='installed_source/'+name;data=prior[m.CAPTURE_PREFIX+'/'+relative];entries[m.CORRECTION_PREFIX+'/'+relative]=data
        outputs.append({'anchor':'native_directory','path':relative,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    spec={'coordinate_cases':coordinates,'raw_references':{label:{'target':1.,'gradient_norm':2.} for label in coordinates}}
    for name,value in [('expected_inventory.json',expected),('native_validation.json',expected),('correction_spec.json',spec),('correction_result.json',result)]:
        data=json.dumps(value).encode();entries[m.CORRECTION_PREFIX+'/'+name]=data
        outputs.append({'anchor':'native_directory','path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    audit={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':previous['inputs'],'outputs':outputs,'result':result}
    entries[m.CORRECTION_PREFIX+'/correction_receipt.json']=json.dumps(audit).encode()
    receipt={'kind':'cif-native-corrected-gradient-probe','delivery_prefix':'25_Cedar','status':'REVIEW','analysis_completed':True,
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_optimization':'NOT_RUN',
        'installed_phenix_edits':'NOT_RUN','automatic_adoption':False,'policy_authority':'NARestraints','prerequisite_mechanics_replayed':True,
        'prior_convergence':'NOT_CONVERGED_ERROR','correction_qualification':'DERIVATIVE_REVIEW','native_correction_audit':audit}
    entries['probe_receipt.json']=json.dumps(receipt).encode()
    for i in range(794-len(entries)):entries[f'padding/{i:03d}.txt']=b'SYNTHETIC'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','verdict','prior','native_input','case','raw','source','signature'])
def test_order_capsule_requires_intact_preserved_correction_evidence(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            r=json.loads(entries['probe_receipt.json']);r['installed_phenix_edits']='CHANGED';entries['probe_receipt.json']=json.dumps(r).encode()
        if defect=='prior':entries['inputs/review/padding/000.txt']=b'CHANGED'
        if defect=='native_input':entries[m.CORRECTION_PREFIX+'/inputs/000_model.pdb']=b'CHANGED'
        if defect in {'case','raw','source','signature'}:
            r=json.loads(entries['probe_receipt.json']);a=r['native_correction_audit'];q=a['result']
            if defect=='case':q['cases']['initial']['families'].pop('angle')
            if defect=='raw':q['raw_baseline_checks']['initial']['target']+=1.
            if defect=='source':q['installed_numeric_sources']=[{'module':'CHANGED','sha256':'0'*64}]
            if defect=='signature':q['constraint_signature_before']=q['constraint_signature_after']='CHANGED'
            data=json.dumps(q).encode();entries[m.CORRECTION_PREFIX+'/correction_result.json']=data
            row=next(row for row in a['outputs'] if row['path']=='correction_result.json');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            entries[m.CORRECTION_PREFIX+'/correction_receipt.json']=json.dumps(a).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for n,data in entries.items():z.writestr(n,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert set(m._read_capsule(path,expected)[3])=={'initial','full_precision','pdb_rounded'}
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_order_shuttle_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest();root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();(root/'scripts/cif_plane_order_probe_template.py').write_text((ROOT/'scripts/cif_plane_order_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True);subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'26_Cedar_probe_cif_plane_order.py';metadata=build(root,nar,runner,template_name='cif_plane_order_probe_template.py')
    assert metadata['delivery_prefix']=='26_Cedar' and metadata['kind']=='cif-native-plane-order-gradient-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['prerequisite_mechanics_replayed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['installed_phenix_edits']=='NOT_RUN' and receipt['automatic_adoption'] is False
    assert receipt['correction_policy_id']=='native-parallelity-both-first-planes-v1' and receipt['prior_correction_qualification']=='DERIVATIVE_REVIEW'
    assert receipt['coordinate_cases']==['initial','full_precision','pdb_rounded'] and receipt['model_optimization']=='NOT_RUN'
