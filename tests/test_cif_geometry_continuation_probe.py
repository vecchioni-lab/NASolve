"""A source-bundled continuation consumes preserved endpoint evidence, not code."""
from copy import deepcopy
import hashlib,importlib.util,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
import pytest
from tests.test_cif_corrected_geometry_probe import capsule as qualified_capsule
from tests.test_cif_geometry_review_probe import write_capsule
from tests.test_cif_geometry_continuation import saved_result

ROOT=Path(__file__).resolve().parents[1]
FAKE_SOURCES={name:b"raise RuntimeError('captured source must not execute')\n" for name in ['geometry_worker.py','corrected_geometry_core.py']}


def template():
    spec=importlib.util.spec_from_file_location('continuation_template',ROOT/'scripts/cif_geometry_continuation_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def capsule(directory):
    from nasolve.cif_fixed_geometry import write_geometry_candidate,qualify_fixed_policy_geometry
    m=template();old=qualified_capsule(directory/'prior')
    with zipfile.ZipFile(old) as z:prior={n:z.read(n) for n in z.namelist()}
    qualified=json.loads(prior['probe_receipt.json'])['native_correction_audit'];proof=qualified['result']
    before=json.loads(prior[m.ORDER_PREFIX+'/expected_inventory.json']);entries={'inputs/review/'+n:d for n,d in prior.items()}
    q=saved_result(proof,before['atom_count']);q['final_sites_cart']=before['geometry']['sites_cart_exact']
    q['derivative_validation_archive']=hashlib.sha256(old.read_bytes()).hexdigest()
    model_data=prior[m.ORDER_PREFIX+'/'+qualified['inputs'][0]['path']]
    model=directory/'source.pdb';model.write_bytes(model_data);candidate=directory/'candidate.pdb'
    serialization=write_geometry_candidate(model,candidate,before,q['final_sites_cart']);after=deepcopy(before)
    mechanics=qualify_fixed_policy_geometry(before,after,candidate,serialization);assert mechanics['mechanics_checks_pass']
    def artifact(name,data,prefix,outputs):
        entries[prefix+'/'+name]=data;outputs.append({'anchor':'native_directory','path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    inputs=qualified['inputs'];outputs=[]
    for row in inputs:entries[m.PREVIOUS_TRIAL_PREFIX+'/'+row['path']]=prior[m.ORDER_PREFIX+'/'+row['path']]
    values=[('expected_inventory.json',json.dumps(before).encode()),('native_validation.json',json.dumps(before).encode()),
        ('geometry_result.json',json.dumps(q).encode()),('gradient_validation.json',json.dumps(proof).encode()),
        ('correction_core.py',prior[m.ORDER_PREFIX+'/correction_core.py']),('native_worker.py',b'EXPLICIT_FAKE_NATIVE_WORKER'),*FAKE_SOURCES.items()]
    for row in q['installed_parallelity_sources']:values.append(('installed_source/'+row['path'],prior[m.ORDER_PREFIX+'/installed_source/'+row['path']]))
    for name,data in values:artifact(name,data,m.PREVIOUS_TRIAL_PREFIX,outputs)
    trial={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':inputs,'outputs':outputs,'result':q}
    entries[m.PREVIOUS_TRIAL_PREFIX+'/geometry_receipt.json']=json.dumps(trial).encode()
    rt_inputs=deepcopy(inputs);rt_inputs[0].update(sha256=serialization['candidate_sha256'],size=candidate.stat().st_size)
    for row in rt_inputs:entries[m.PREVIOUS_READBACK_PREFIX+'/'+row['path']]=candidate.read_bytes() if row['role']=='model' else prior[m.ORDER_PREFIX+'/'+row['path']]
    rt_outputs=[]
    for name,data in [('native_worker.py',b'EXPLICIT_FAKE_NATIVE_WORKER'),('native_validation.json',json.dumps(after).encode())]:artifact(name,data,m.PREVIOUS_READBACK_PREFIX,rt_outputs)
    readback={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':rt_inputs,'outputs':rt_outputs,'native_validation':after}
    entries[m.PREVIOUS_READBACK_PREFIX+'/native_receipt.json']=json.dumps(readback).encode()
    receipt={'kind':'cif-corrected-na-geometry-probe','delivery_prefix':'27_Cedar','status':'REVIEW','analysis_completed':True,
        'native_execution':'COMPLETED','model_optimization':'EXPLICIT_BOUNDED_TRIAL','original_archive_preserved':True,
        'frozen_inputs_preserved':True,'prerequisite_mechanics_replayed':True,'automatic_adoption':False,'policy_authority':'NARestraints',
        'installed_phenix_edits':'NOT_RUN','policy_recompilation':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'convergence':'NOT_CONVERGED_LIMIT','prior_convergence':'NOT_CONVERGED_ERROR','starting_coordinates':'CAPTURED_INITIAL',
        'endpoint_derivative_qualification':'SAMPLED_NATIVE_DERIVATIVES_PASS','geometry_trial':trial,'native_roundtrip':readback,
        'serialization':serialization,'native_mechanics':mechanics,'prior_archive':{'sha256':q['derivative_validation_archive'],'verified_payloads':857}}
    entries['probe_receipt.json']=json.dumps(receipt).encode();entries['native_mechanics.json']=json.dumps(mechanics).encode()
    entries['candidate/corrected_geometry_model.pdb']=candidate.read_bytes()
    for i in range(980-len(entries)):entries[f'padding/{i:03d}.txt']=b'EXPLICIT_FAKE_PADDING'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','unsafe','duplicate','symlink','payload','prior','source','qualification','mechanics','candidate','policy','signature'])
def test_continuation_capsule_requires_saved_qualified_fixed_policy_evidence(tmp_path,defect):
    m=template();m.CAPTURED_TRIAL_SOURCE_SHA256={n:hashlib.sha256(d).hexdigest() for n,d in FAKE_SOURCES.items()}
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        elif defect=='prior':entries['inputs/review/padding/000.txt']=b'CHANGED'
        elif defect=='source':
            data=b'COHERENTLY_CHANGED_CAPTURED_WORKER';entries[m.PREVIOUS_TRIAL_PREFIX+'/geometry_worker.py']=data
            r=json.loads(entries['probe_receipt.json']);row=next(x for x in r['geometry_trial']['outputs'] if x['path']=='geometry_worker.py')
            row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            entries[m.PREVIOUS_TRIAL_PREFIX+'/geometry_receipt.json']=json.dumps(r['geometry_trial']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        elif defect=='candidate':entries['candidate/corrected_geometry_model.pdb']=b'CHANGED'
        elif defect=='mechanics':
            r=json.loads(entries['probe_receipt.json']);r['native_mechanics']['checks'][0]['status']='REVIEW'
            entries['native_mechanics.json']=json.dumps(r['native_mechanics']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        elif defect in {'qualification','policy','signature'}:
            r=json.loads(entries['probe_receipt.json']);q=r['geometry_trial']['result']
            if defect=='qualification':q['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
            if defect=='policy':q['policy_inventory']=False
            if defect=='signature':q['constraint_signature_before']=q['constraint_signature_after']='2'*64
            data=json.dumps(q).encode();entries[m.PREVIOUS_TRIAL_PREFIX+'/geometry_result.json']=data
            row=next(row for row in r['geometry_trial']['outputs'] if row['path']=='geometry_result.json');row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            entries[m.PREVIOUS_TRIAL_PREFIX+'/geometry_receipt.json']=json.dumps(r['geometry_trial']).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink');expected=hashlib.sha256(path.read_bytes()).hexdigest()
        if defect=='payload':
            with zipfile.ZipFile(path) as z:all_entries={n:z.read(n) for n in z.namelist()}
            all_entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for n,d in all_entries.items():z.writestr(n,d)
            expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':assert m._read_capsule(path,expected)[2]['convergence']=='NOT_CONVERGED_LIMIT'
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_continuation_shuttle_survives_deleted_builds_and_ignores_captured_code(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'));from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest();root=tmp_path/'build';nar=tmp_path/'nar';m=template()
    for relative in ['src','MR_frames/5W6W','docs/recipes']:shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    text=(ROOT/'scripts/cif_geometry_continuation_probe_template.py').read_text().replace(m.REVIEW_SHA256,expected)
    for name,digest in m.CAPTURED_TRIAL_SOURCE_SHA256.items():text=text.replace(digest,hashlib.sha256(FAKE_SOURCES[name]).hexdigest())
    (root/'scripts').mkdir();(root/'scripts/cif_geometry_continuation_probe_template.py').write_text(text)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'28_Cedar_probe_cif_geometry_continuation.py';metadata=build(root,nar,runner,template_name='cif_geometry_continuation_probe_template.py')
    assert metadata['delivery_prefix']=='28_Cedar' and metadata['kind']=='cif-corrected-na-geometry-continuation-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("ambient import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['prerequisite_mechanics_replayed'] and receipt['starting_coordinates']=='SAVED_FULL_PRECISION_ENDPOINT'
    assert receipt['prior_convergence']=='NOT_CONVERGED_LIMIT' and receipt['native_execution']=='NOT_RUN'
    assert receipt['automatic_adoption'] is False and receipt['model_optimization']=='NOT_RUN'
