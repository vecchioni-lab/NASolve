"""Correction delivery requires preserved, qualified individual gradients."""
import hashlib,importlib.util,json,os
from pathlib import Path
import shutil,subprocess,sys,zipfile
import pytest
from tests.test_cif_parallelity_audit_probe import capsule as gradient_capsule
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('correction_template',ROOT/'scripts/cif_corrected_gradient_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(directory):
    m=template();old=gradient_capsule(directory/'gradient')
    with zipfile.ZipFile(old) as z:prior={name:z.read(name) for name in z.namelist()}
    before=json.loads(prior['probe_receipt.json']);previous=before['native_gradient_audit']
    previous_prefix='native_gradients/cif-gradient-audit-ilzjo7_w'
    expected=json.loads(prior[previous_prefix+'/expected_inventory.json'])
    coordinates=json.loads(prior[previous_prefix+'/gradient_spec.json'])['coordinate_cases'];count=expected['atom_count']
    result={'policy_id':'cif-native-parallelity-accumulation-audit-v1','status':'REVIEW','analysis_completed':True,
        'captured_inventory_matches':True,'model_optimization':'NOT_RUN','automatic_adoption':False,'evaluation_pairs':6188,
        'constraint_signature_before':'synthetic_fixed','constraint_signature_after':'synthetic_fixed','installed_numeric_sources':[],
        'installed_adapter_sources':[],'installed_parallelity_sources':[],
        'cases':{label:{'summary':{'single_derivatives_consistent':True,'baseline_repeats_consistent':True}} for label in coordinates},
        'toy_summary':{'single_derivatives_consistent':True,'baseline_repeats_consistent':True},
        'full_batch_comparisons':{label:{'manager_matches_batch':True,'captured_snapshot_match':True,'energy_agreement':True,
            'accumulated_residual':1.,'accumulated_gradient':[0.]*(3*count),'manual_gradient':[0.]*(3*count)} for label in coordinates}}
    entries={'inputs/review/'+name:payload for name,payload in prior.items()};outputs=[]
    for row in previous['inputs']:entries[m.CAPTURE_PREFIX+'/'+row['path']]=prior[previous_prefix+'/'+row['path']]
    for name in ['parallelity.h','parallelity_bpl.cpp']:
        data=('EXPLICIT_FAKE_'+name+'\n').encode();relative='installed_source/'+name;entries[m.CAPTURE_PREFIX+'/'+relative]=data
        result['installed_parallelity_sources'].append({'anchor':'native_geometry_module','path':name,'status':'RECORDED','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        outputs.append({'anchor':'native_directory','path':relative,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for name,value in [('expected_inventory.json',expected),('native_validation.json',expected),('parallelity_result.json',result),('parallelity_spec.json',{'coordinate_cases':coordinates})]:
        data=json.dumps(value).encode();entries[m.CAPTURE_PREFIX+'/'+name]=data
        outputs.append({'anchor':'native_directory','path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    audit={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':previous['inputs'],'outputs':outputs,'result':result}
    entries[m.CAPTURE_PREFIX+'/parallelity_receipt.json']=json.dumps(audit).encode()
    receipt={'kind':'cif-native-parallelity-audit-probe','delivery_prefix':'24_Cedar','status':'REVIEW','analysis_completed':True,
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_optimization':'NOT_RUN',
        'automatic_adoption':False,'policy_authority':'NARestraints','prerequisite_mechanics_replayed':True,
        'prior_convergence':'NOT_CONVERGED_ERROR','native_parallelity_audit':audit}
    entries['probe_receipt.json']=json.dumps(receipt).encode()
    for i in range(732-len(entries)):entries[f'padding/{i:03d}.txt']=b'SYNTHETIC'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','verdict','prior','native_input','single','cpp','source'])
def test_correction_capsule_requires_intact_qualified_prerequisites(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={name:z.read(name) for name in z.namelist() if name!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            r=json.loads(entries['probe_receipt.json']);r['model_optimization']='EXPLICIT_BOUNDED_TRIAL';entries['probe_receipt.json']=json.dumps(r).encode()
        if defect=='prior':entries['inputs/review/padding/000.txt']=b'CHANGED'
        if defect=='native_input':entries[m.CAPTURE_PREFIX+'/inputs/000_model.pdb']=b'CHANGED'
        if defect in {'single','cpp','source'}:
            r=json.loads(entries['probe_receipt.json']);a=r['native_parallelity_audit'];q=a['result']
            if defect=='single':q['cases']['full_precision']['summary']['single_derivatives_consistent']=False
            if defect=='cpp':q['installed_parallelity_sources'][0]['sha256']='0'*64
            if defect=='source':q['installed_numeric_sources']=[{'module':'CHANGED','sha256':'0'*64}]
            data=json.dumps(q).encode();entries[m.CAPTURE_PREFIX+'/parallelity_result.json']=data
            row=next(row for row in a['outputs'] if row['path']=='parallelity_result.json');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            entries[m.CAPTURE_PREFIX+'/parallelity_receipt.json']=json.dumps(a).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={name:z.read(name) for name in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert set(m._read_capsule(path,expected)[3])=={'initial','full_precision','pdb_rounded'}
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_correction_shuttle_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest();root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();(root/'scripts/cif_corrected_gradient_probe_template.py').write_text((ROOT/'scripts/cif_corrected_gradient_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True);subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'25_Cedar_probe_cif_corrected_gradient.py';metadata=build(root,nar,runner,template_name='cif_corrected_gradient_probe_template.py')
    assert metadata['delivery_prefix']=='25_Cedar' and metadata['kind']=='cif-native-corrected-gradient-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['prerequisite_mechanics_replayed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['installed_phenix_edits']=='NOT_RUN' and receipt['automatic_adoption'] is False
    assert receipt['correction_policy_id']=='native-parallelity-complete-accumulation-v1'
    assert receipt['coordinate_cases']==['initial','full_precision','pdb_rounded'] and receipt['model_optimization']=='NOT_RUN'
