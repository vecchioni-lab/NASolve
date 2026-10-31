"""A source-only shuttle rechecks the saved continuation without captured code."""
from copy import deepcopy
import hashlib,importlib.util,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
import pytest
from tests.test_cif_geometry_continuation_probe import capsule as previous_capsule,FAKE_SOURCES as OLD_SOURCES
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]
FAKE_SOURCES={n:b"raise RuntimeError('captured continuation source must not execute')\n" for n in ['geometry_worker.py','corrected_geometry_core.py']}


def template():
    spec=importlib.util.spec_from_file_location('rotation_template',ROOT/'scripts/cif_base_rotation_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.CAPTURED_TRIAL_SOURCE_SHA256={n:hashlib.sha256(v).hexdigest() for n,v in OLD_SOURCES.items()}
    m.CURRENT_SOURCE_SHA256={n:hashlib.sha256(v).hexdigest() for n,v in FAKE_SOURCES.items()}
    return m


def capsule(directory):
    from nasolve.cif_fixed_geometry import write_geometry_candidate,qualify_fixed_policy_geometry
    m=template();old=previous_capsule(directory/'prior')
    with zipfile.ZipFile(old) as z:previous={n:z.read(n) for n in z.namelist()}
    before=json.loads(previous[m.PREVIOUS_TRIAL_PREFIX+'/expected_inventory.json'])
    oldreceipt=json.loads(previous['probe_receipt.json']);oldq=oldreceipt['geometry_trial']['result']
    proof=json.loads(previous[m.PREVIOUS_TRIAL_PREFIX+'/gradient_validation.json']);q=deepcopy(oldq)
    q.update(policy_id='cif-fixed-na-corrected-geometry-continuation-v1',starting_coordinates='SAVED_FULL_PRECISION_ENDPOINT',
        qualified_continuation_snapshot_matches=True,initial=deepcopy(oldq['final']),captured_initial=deepcopy(oldq.get('initial',{})))
    q['continuation']={'archive_sha256':m.CEDAR27_SHA256,'optimizer_history':'FRESH_LBFGS_FROM_SAVED_COORDINATES',
        'prior_stopping':oldq['stopping'],'prior_total_iterations':oldq['stopping']['iterations'],'prior_total_calls':oldq['stopping']['calls'],
        'total_iterations':2*oldq['stopping']['iterations'],'total_calls':2*oldq['stopping']['calls']}
    entries={'inputs/review/'+n:d for n,d in previous.items()};inputs=oldreceipt['geometry_trial']['inputs']
    model=directory/'source.pdb';model.write_bytes(previous[m.PREVIOUS_TRIAL_PREFIX+'/'+inputs[0]['path']])
    candidate=directory/'candidate.pdb';serialization=write_geometry_candidate(model,candidate,before,q['final_sites_cart'])
    mechanics=qualify_fixed_policy_geometry(before,before,candidate,serialization)
    def artifact(name,data,prefix,outputs):
        entries[prefix+'/'+name]=data;outputs.append({'anchor':'native_directory','path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for row in inputs:entries[m.CURRENT_TRIAL_PREFIX+'/'+row['path']]=previous[m.PREVIOUS_TRIAL_PREFIX+'/'+row['path']]
    outputs=[]
    values=[('expected_inventory.json',json.dumps(before).encode()),('native_validation.json',json.dumps(before).encode()),
        ('geometry_result.json',json.dumps(q).encode()),('gradient_validation.json',json.dumps(proof).encode()),
        ('continuation_validation.json',json.dumps(oldq).encode()),('native_worker.py',b'EXPLICIT_FAKE_NATIVE_WORKER'),
        ('correction_core.py',previous[m.PREVIOUS_TRIAL_PREFIX+'/correction_core.py']),*FAKE_SOURCES.items()]
    for row in q['installed_parallelity_sources']:values.append(('installed_source/'+row['path'],previous[m.PREVIOUS_TRIAL_PREFIX+'/installed_source/'+row['path']]))
    for name,data in values:artifact(name,data,m.CURRENT_TRIAL_PREFIX,outputs)
    trial={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':inputs,'outputs':outputs,'result':q}
    entries[m.CURRENT_TRIAL_PREFIX+'/geometry_receipt.json']=json.dumps(trial).encode()
    ri=deepcopy(inputs);ri[0].update(sha256=serialization['candidate_sha256'],size=candidate.stat().st_size)
    for row in ri:entries[m.CURRENT_READBACK_PREFIX+'/'+row['path']]=candidate.read_bytes() if row['role']=='model' else previous[m.PREVIOUS_TRIAL_PREFIX+'/'+row['path']]
    ro=[]
    for name,data in [('native_worker.py',b'EXPLICIT_FAKE_NATIVE_WORKER'),('native_validation.json',json.dumps(before).encode())]:artifact(name,data,m.CURRENT_READBACK_PREFIX,ro)
    readback={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':ri,'outputs':ro,'native_validation':before}
    entries[m.CURRENT_READBACK_PREFIX+'/native_receipt.json']=json.dumps(readback).encode()
    receipt={**deepcopy(oldreceipt),'kind':'cif-corrected-na-geometry-continuation-probe','delivery_prefix':'28_Cedar',
        'prior_convergence':'NOT_CONVERGED_LIMIT','starting_coordinates':'SAVED_FULL_PRECISION_ENDPOINT',
        'geometry_trial':trial,'native_roundtrip':readback,'serialization':serialization,'native_mechanics':mechanics,
        'continuation':q['continuation'],'prior_archive':{'sha256':m.CEDAR27_SHA256,'verified_payloads':980}}
    entries['probe_receipt.json']=json.dumps(receipt).encode();entries['native_mechanics.json']=json.dumps(mechanics).encode()
    entries['candidate/continued_geometry_model.pdb']=candidate.read_bytes()
    for i in range(1104-len(entries)):entries[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','prior','source','qualification','mechanics','candidate','lineage','signature'])
def test_rotation_capsule_rechecks_qualified_continuation_and_sources(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        elif defect=='prior':entries['inputs/review/padding/000.txt']=b'CHANGED'
        elif defect=='candidate':entries['candidate/continued_geometry_model.pdb']=b'CHANGED'
        elif defect=='mechanics':
            r=json.loads(entries['probe_receipt.json']);r['native_mechanics']['checks'][0]['status']='REVIEW'
            entries['native_mechanics.json']=json.dumps(r['native_mechanics']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        elif defect in {'source','qualification','signature','lineage'}:
            r=json.loads(entries['probe_receipt.json']);q=r['geometry_trial']['result']
            if defect=='qualification':q['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
            if defect=='signature':q['constraint_signature_before']=q['constraint_signature_after']='2'*64
            if defect=='lineage':q['continuation']['total_iterations']+=1;r['continuation']=q['continuation']
            if defect=='source':
                data=b'COHERENT_CHANGED_WORKER';entries[m.CURRENT_TRIAL_PREFIX+'/geometry_worker.py']=data
                row=next(x for x in r['geometry_trial']['outputs'] if x['path']=='geometry_worker.py');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            data=json.dumps(q).encode();entries[m.CURRENT_TRIAL_PREFIX+'/geometry_result.json']=data
            row=next(x for x in r['geometry_trial']['outputs'] if x['path']=='geometry_result.json');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            entries[m.CURRENT_TRIAL_PREFIX+'/geometry_receipt.json']=json.dumps(r['geometry_trial']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink');expected=hashlib.sha256(path.read_bytes()).hexdigest()
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for n,data in entries.items():z.writestr(n,data)
            expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert m._read_capsule(path,expected)[2]['delivery_prefix']=='28_Cedar'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_rotation_shuttle_survives_deleted_builds_with_poisoned_ambient_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'));from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest();m=template()
    root=tmp_path/'source';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    text=(ROOT/'scripts/cif_base_rotation_probe_template.py').read_text().replace(m.REVIEW_SHA256,expected)
    for mapping,values in [('CAPTURED_TRIAL_SOURCE_SHA256',OLD_SOURCES),('CURRENT_SOURCE_SHA256',FAKE_SOURCES)]:
        original=importlib.util.spec_from_file_location('raw_template',ROOT/'scripts/cif_base_rotation_probe_template.py');module=importlib.util.module_from_spec(original);original.loader.exec_module(module)
        for name,digest in getattr(module,mapping).items():text=text.replace(digest,hashlib.sha256(values[name]).hexdigest())
    (root/'scripts').mkdir();(root/'scripts/cif_base_rotation_probe_template.py').write_text(text)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'29_Cedar_probe_cif_base_rotation.py';metadata=build(root,nar,runner,template_name='cif_base_rotation_probe_template.py')
    assert metadata['delivery_prefix']=='29_Cedar' and metadata['kind']=='cif-fixed-na-base-rotation-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("ambient import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['prerequisite_mechanics_replayed'] and receipt['native_execution']=='NOT_RUN'
    assert receipt['automatic_adoption'] is False and receipt['model_optimization']=='NOT_RUN' and receipt['model_editing']=='NOT_RUN'
