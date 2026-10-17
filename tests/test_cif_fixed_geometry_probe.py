"""Capsule isolation and portable Cedar 19 transport with synthetic evidence."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest
from tests.test_cif_fragment_restoration import fixture
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('fixed_geometry_template',ROOT/'scripts/cif_fixed_geometry_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(directory):
    directory.mkdir(parents=True);_,model,_,n,_=fixture(directory);n['installed_api_sources']=[]
    prefix=template().CAPTURE_PREFIX;entries={};inputs=[]
    data=[('model',model.read_bytes())]+[('dictionary',b'EXPLICIT_FAKE_CIF')]*19+[('phil',b'EXPLICIT_FAKE_PHIL')]*12
    for i,(role,payload) in enumerate(data):
        path=f'inputs/{i:03d}_{role}'+{'model':'.pdb','dictionary':'.cif','phil':'.phil'}[role]
        entries[prefix+'/'+path]=payload;inputs.append({'input_index':i,'role':role,'anchor':'native_directory','path':path,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
    native=json.dumps(n).encode();entries[prefix+'/native_validation.json']=native
    capture={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,
        'inputs':inputs,'outputs':[{'anchor':'native_directory','path':'native_validation.json','size':len(native),'sha256':hashlib.sha256(native).hexdigest()}],
        'native_validation':n,'phenix_version':'EXPLICIT_FAKE'}
    entries[prefix+'/native_receipt.json']=json.dumps(capture).encode()
    checks={'checks':[{'check':'EXPLICIT_FAKE','status':'PASS'}]};mech={**deepcopy(checks),'mechanics_checks_pass':True}
    entries['dictionary_qualification.json']=json.dumps(checks).encode();entries['fragment_mechanics.json']=json.dumps(mech).encode()
    r={'kind':'cif-effective-source-recovery-probe','delivery_prefix':'18_Cedar','status':'REVIEW','analysis_completed':True,
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_optimization':'NOT_RUN',
        'automatic_adoption':False,'dictionary_qualification':checks,'fragment_mechanics':mech,'native_fragment':capture,
        'prior_qualification':{'status':'REVIEW'},'prior_source_assessments':[]}
    entries['probe_receipt.json']=json.dumps(r).encode()
    for i in range(252-len(entries)):entries[f'padding/{i:03d}.txt']=b'VERIFIED_UNSELECTED'
    path=directory/'capsule.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['archive','unsafe','duplicate','symlink','padding','failed_mechanics','charge_contradiction'])
def test_changed_capsule_and_unresolved_prerequisites_stop_before_execution(tmp_path,defect):
    m=template();path=capsule(tmp_path/'input');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    else:
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect in {'failed_mechanics','charge_contradiction'}:
            r=json.loads(entries['probe_receipt.json']);key='fragment_mechanics' if defect=='failed_mechanics' else 'dictionary_qualification'
            r[key]['checks']=[{'check':'effective-site-formal-charges:Z:9','status':'UNSUPPORTED','contradictions':[{'atom_id':'NX'}]}]
            entries[key+'.json']=json.dumps(r[key]).encode();entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='padding':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):m._read_capsule(path,expected)


@pytest.mark.parametrize('resume',[False,True])
def test_runner_survives_deleted_builds_and_poisoned_imports(tmp_path,resume):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root,nar=tmp_path/'build',tmp_path/'nar'
    if resume:
        saved,_,_,_=completed_capsule(tmp_path/'protected');path=tmp_path/'protected/prior/capsule.zip'
    else:path=capsule(tmp_path/'protected')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    source=(ROOT/'scripts/cif_fixed_geometry_probe_template.py').read_text().replace(template().REVIEW_SHA256,digest)
    if resume:source=source.replace(template().COMPLETED_TRIAL_SHA256,hashlib.sha256(saved.read_bytes()).hexdigest())
    (root/'scripts/cif_fixed_geometry_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'19_Cedar_probe_cif_geometry_trial.py'
    prefix='20_Cedar' if resume else '19_Cedar'
    metadata=build(root,nar,runner,template_name='cif_fixed_geometry_probe_template.py',delivery_prefix=prefix)
    assert metadata['delivery_prefix']==prefix and metadata['kind']=='cif-fixed-native-geometry-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    extra=['--completed-trial-zip',str(saved)] if resume else []
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only']+extra,
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    assert 'stopped' not in result.stderr
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN' and not receipt['automatic_adoption']
    if resume:assert receipt['completed_trial_archive_preserved'] and receipt['completed_trial_archive']['verified_payloads']==310


def completed_capsule(directory):
    m=template();old=capsule(directory/'prior')
    prior_members,_,capture,_=m._read_capsule(old,hashlib.sha256(old.read_bytes()).hexdigest())
    prefix=m.COMPLETED_TRIAL_PREFIX;entries={'inputs/review/'+n:data for n,data in prior_members.items()}
    for row in capture['inputs']:entries[prefix+'/'+row['path']]=prior_members[m.CAPTURE_PREFIX+'/'+row['path']]
    native=capture['native_validation']
    result={'status':'REVIEW','captured_inventory_matches':True,'constraint_signature_before':'fixed','constraint_signature_after':'fixed',
        'automatic_adoption':False,'scientific_approval':'NOT_RUN','final_sites_cart':deepcopy(native['geometry']['sites_cart_exact']),
        'stopping':{'reason':'max_iterations','error':None,'iterations':5,'max_iterations':5,'native_criterion_met':False},
        'initial':{'target':2.},'final':{'target':1.}}
    result['final_sites_cart'][0][0]+=.123456789
    outputs=[]
    for name,value in [('expected_inventory.json',native),('native_validation.json',native),('geometry_result.json',result)]:
        data=json.dumps(value).encode();entries[prefix+'/'+name]=data;outputs.append({'anchor':'native_directory','path':name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
    trial={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'result':result,'inputs':capture['inputs'],'outputs':outputs,
        'source_preserved':True,'frozen_inputs_preserved':True,'phenix_version':capture['phenix_version'],'executable_sha256':capture.get('executable_sha256'),
        'convergence':'NOT_CONVERGED_LIMIT'}
    entries[prefix+'/geometry_receipt.json']=json.dumps(trial).encode()
    entries['probe_receipt.json']=json.dumps({'kind':'cif-fixed-native-geometry-probe','delivery_prefix':'19_Cedar','error':'PDB/native atom ordering differs',
        'analysis_completed':False,'original_archive_preserved':True,'automatic_adoption':False,'geometry_trial':trial}).encode()
    for i in range(310-len(entries)):entries[f'padding/{i:03d}.txt']=b'VERIFIED'
    assert len(entries)==310
    path=directory/'completed.zip';write_capsule(path,entries)
    return path,prior_members,capture,trial


@pytest.mark.parametrize('defect',['none','changed_payload','changed_definition','different_bundle','constraint_change','unsafe','duplicate','symlink'])
def test_completed_trial_reuse_requires_exact_preserved_bundle(tmp_path,defect):
    m=template();path,prior,capture,trial=completed_capsule(tmp_path/'saved')
    with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
    prefix=m.COMPLETED_TRIAL_PREFIX
    if defect=='changed_definition':
        native=json.loads(entries[prefix+'/native_validation.json']);native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type']='CHANGED'
        data=json.dumps(native).encode();entries[prefix+'/native_validation.json']=data
        row=next(x for x in trial['outputs'] if x['path']=='native_validation.json');row.update(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
    if defect=='different_bundle':capture=deepcopy(capture);capture['inputs'][1]['sha256']='CHANGED'
    if defect=='constraint_change':trial['result']['constraint_signature_after']='changed'
    if defect in {'changed_definition','constraint_change'}:
        entries[prefix+'/geometry_receipt.json']=json.dumps(trial).encode()
        root=json.loads(entries['probe_receipt.json']);root['geometry_trial']=trial;entries['probe_receipt.json']=json.dumps(root).encode()
    if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
    write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
    if defect=='changed_payload':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
        entries['padding/000.txt']=b'CHANGED'
        with zipfile.ZipFile(path,'w') as z:
            for n,data in entries.items():z.writestr(n,data)
    expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':
        members,loaded,_=m._read_completed_trial(path,prior,capture,expected);assert loaded==trial and len(members)==311
    else:
        with pytest.raises(ValueError):m._read_completed_trial(path,prior,capture,expected)


@pytest.mark.parametrize('native_definitions',['unchanged','changed'])
def test_resume_serializes_saved_endpoints_without_another_optimization(tmp_path,monkeypatch,native_definitions):
    from types import SimpleNamespace
    m=template();path,prior,capture,trial=completed_capsule(tmp_path/'saved')
    session=tmp_path/'session';m._materialize(prior,session/'inputs/review')
    def forbidden(*args,**kwargs):raise AssertionError('Completed trial must not rerun minimization')
    monkeypatch.setattr('nasolve.cif_fixed_geometry.run_fixed_geometry',forbidden)
    def inspect(model,*args,**kwargs):
        native=deepcopy(capture['native_validation']);rows={line[12:16].strip():[float(line[i:i+8]) for i in (30,38,46)] for line in model.read_text().splitlines() if line.startswith('HETATM')}
        for atom in native['atoms']:atom['xyz']=rows[atom['atom_id']]
        native['geometry']['sites_cart_exact']=[a['xyz'] for a in native['atoms']]
        if native_definitions=='changed':native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type']='CHANGED'
        return {'status':'REVIEW','native_validation':native,'execution':{'status':'COMPLETED'}}
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle',inspect)
    receipt={};phenix=SimpleNamespace(executables={'phenix.python':Path(sys.executable)},environment={},version='EXPLICIT_FAKE')
    if native_definitions=='changed':
        with pytest.raises(ValueError,match='changed native'):
            m._run_trial(session,capture,phenix,500,30,receipt,completed=trial)
        assert not receipt['native_mechanics']['mechanics_checks_pass']
    else:
        m._run_trial(session,capture,phenix,500,30,receipt,completed=trial)
        assert receipt['geometry_trial_reused'] and receipt['native_mechanics']['mechanics_checks_pass']
        assert receipt['geometry_trial']==trial and receipt['convergence']=='NOT_CONVERGED_LIMIT'
