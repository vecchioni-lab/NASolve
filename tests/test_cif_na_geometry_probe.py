"""Verified-policy geometry transport and orchestration, without installed Phenix."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile
import pytest

from tests.test_cif_na_policy import fixture
from tests.test_cif_captured_geometry import native as scalar_native
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('na_geometry_template',ROOT/'scripts/cif_na_geometry_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def capsule(directory):
    from nasolve.cif_na_policy import compile_na_policy,qualify_na_policy
    directory.mkdir(parents=True);model,phil,base=fixture(directory);m=template()
    geometry=scalar_native()['geometry']
    geometry['sites_cart_exact']=[a['xyz'] for a in base['atoms']]
    geometry['proxy_details']={k:[] for k in geometry['proxy_details']}
    geometry['proxy_counts']={k:0 for k in geometry['proxy_counts']}
    geometry['custom_proxy_requests']=[];base.update(geometry=geometry,atom_count=len(base['atoms']),status='REVIEW',
        schema_version=1,policy_id='cif-native-bundle-inventory-v1',inventory_detail='linked')
    for atom in base['atoms']:atom['element']=atom['atom_id'][0]
    policy=compile_na_policy(model,[phil],base,directory/'policy')
    # The captured experiment has 12 retained PHIL inputs, one compiled policy.
    for i in range(1,12):
        name=f'retained_{i:03d}.phil';(directory/'policy'/name).write_text('# frozen empty fixture\n');policy['retained_phils'].append(name)
    after=deepcopy(base)
    after['restraint_policy']={'secondary_structure_enabled':False,'origin_ids':{
        'hydrogen bonds':37,'edits':41,'basepair stacking':43,'basepair parallelity':47,'basepair planarity':49}}
    after['installed_api_sources']=[]
    after['geometry']['custom_proxy_requests']=deepcopy(policy['compiled_requests'])
    for request in policy['compiled_requests']:
        row={k:v for k,v in request.items() if k not in {'kind','action','selections'}};row['origin_id']=41
        kind='bond_simple' if request['kind']=='bond' else request['kind']
        after['geometry']['proxy_details'][kind].append(row)
    after['geometry']['proxy_counts']={k:len(v) for k,v in after['geometry']['proxy_details'].items()}
    mechanics=qualify_na_policy(base,after,policy);assert mechanics['mechanics_checks_pass']
    entries={m.ORIGINAL_PREFIX+'/native_validation.json':json.dumps(base).encode()}
    # All earlier evidence remains byte-identical under its declared anchor.
    for i in range(367-len(entries)):entries[f'inputs/review/padding/{i:03d}']=b'SYNTHETIC_PRIOR'
    frozen={n.removeprefix('inputs/review/'):v for n,v in entries.items()}
    entries['inputs/review/manifest.json']=json.dumps({n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in frozen.items()}).encode()
    entries['policy_report.json']=json.dumps(policy).encode()
    for name in policy['retained_phils']+[policy['compiled_phil']]:entries['policy/'+name]=(directory/'policy'/name).read_bytes()
    cases={}
    for name,prefix in [('initial',m.INITIAL_PREFIX),('saved_endpoint',m.CAPTURE_PREFIX)]:
        inputs=[];payloads=[('model',model.read_bytes())]+[('dictionary',b'EXPLICIT_FAKE_CIF')]*19
        payloads += [('phil',entries['policy/'+p]) for p in policy['retained_phils']+[policy['compiled_phil']]]
        for i,(role,payload) in enumerate(payloads):
            relative=f'inputs/{i:03d}_{role}'+{'model':'.pdb','dictionary':'.cif','phil':'.phil'}[role]
            inputs.append({'role':role,'anchor':'native_directory','path':relative,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
            entries[prefix+'/'+relative]=payload
        payload=json.dumps(after).encode();entries[prefix+'/native_validation.json']=payload
        capture={'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,'phenix_version':'EXPLICIT_FAKE',
            'execution':{'status':'COMPLETED','returncode':0},'inputs':inputs,'native_validation':after,
            'outputs':[{'anchor':'native_directory','path':'native_validation.json','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]}
        entries[prefix+'/native_receipt.json']=json.dumps(capture).encode()
        entries[name+'_mechanics.json']=json.dumps(mechanics).encode()
        cases[name]={'native':capture,'mechanics':mechanics}
    prior={'kind':'cif-na-policy-native-probe','delivery_prefix':'21_Cedar','status':'REVIEW','analysis_completed':True,
        'original_archive_preserved':True,'frozen_inputs_preserved':True,'native_execution':'COMPLETED','model_editing':'NOT_RUN',
        'model_optimization':'NOT_RUN','automatic_adoption':False,'membership_invariant':True,'policy_authority':'NARestraints',
        'compiled_policy':policy,'native_cases':cases,'objective':policy['objective'],'prior_convergence':'NOT_CONVERGED_LIMIT'}
    entries['probe_receipt.json']=json.dumps(prior).encode()
    for i in range(491-len(entries)):entries[f'padding/{i:03d}.txt']=b'SYNTHETIC'
    path=directory/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['none','archive','payload','unsafe','duplicate','symlink','verdict','policy','prior','model'])
def test_policy_geometry_capsule_requires_preserved_membership_evidence(tmp_path,defect):
    m=template();path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    elif defect!='none':
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            root=json.loads(entries['probe_receipt.json']);root['membership_invariant']=False;entries['probe_receipt.json']=json.dumps(root).encode()
        if defect=='policy':entries['policy/'+json.loads(entries['policy_report.json'])['compiled_phil']]+=b'CHANGED'
        if defect=='prior':entries['inputs/review/padding/000']=b'CHANGED'
        if defect=='model':entries[m.CAPTURE_PREFIX+'/inputs/000_model.pdb']=b'CHANGED'
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,value in entries.items():z.writestr(name,value)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='none':
        _,prior,capture,_=m._read_capsule(path,expected)
        assert capture==prior['native_cases']['saved_endpoint']['native']
    else:
        with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_shuttle_replays_policy_after_both_builds_are_deleted(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    source=(ROOT/'scripts/cif_na_geometry_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected)
    (root/'scripts/cif_na_geometry_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'22_Cedar_probe_cif_na_geometry.py'
    metadata=build(root,nar,runner,template_name='cif_na_geometry_probe_template.py')
    assert metadata['delivery_prefix']=='22_Cedar' and metadata['kind']=='cif-na-policy-geometry-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'outputs'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'outputs').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['frozen_inputs_preserved'] and receipt['original_archive_preserved']
    assert receipt['prerequisite_membership_replayed'] and receipt['selected_case']=='saved_endpoint'
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN'
    assert receipt['prior_convergence']=='NOT_CONVERGED_LIMIT' and receipt['automatic_adoption'] is False


@pytest.mark.parametrize('changed',['none','native_policy','worker_failure'])
def test_orchestrator_uses_fixed_endpoint_inputs_and_checks_native_readback(tmp_path,monkeypatch,changed):
    import nasolve.cif_fixed_geometry as geometry
    import nasolve.cif_native_validation as validation
    m=template();path=capsule(tmp_path/'protected')
    members,prior,capture,_=m._read_capsule(path,hashlib.sha256(path.read_bytes()).hexdigest())
    session=tmp_path/'session';m._materialize(members,session/'inputs/review')
    before=capture['native_validation'];seen=[]
    def run(model,cifs,phils,expected,output,executable,**options):
        assert model.read_bytes()==members[m.CAPTURE_PREFIX+'/inputs/000_model.pdb']
        assert len(cifs)==19 and len(phils)==13 and expected==before and options['policy_inventory'] is True
        assert options['max_iterations']==1000;seen.append('trial')
        return {'status':'FAILED' if changed=='worker_failure' else 'REVIEW','execution':{'status':'COMPLETED'},
            'convergence':'NOT_CONVERGED_LIMIT','result':{'final_sites_cart':deepcopy(before['geometry']['sites_cart_exact']),
            'initial':{'target':2.,'gradient_norm':10.},'final':{'target':1.,'gradient_norm':5.},'stopping':{'reason':'max_iterations'}}}
    def inspect(model,cifs,output,executable,**options):
        assert options['policy_inventory'] is True and len(options['phil_files'])==13;seen.append('readback')
        after=deepcopy(before)
        if changed=='native_policy':after['restraint_policy']['secondary_structure_enabled']=True
        return {'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'native_validation':after}
    monkeypatch.setattr(geometry,'run_fixed_geometry',run);monkeypatch.setattr(validation,'inspect_native_bundle',inspect)
    phenix=SimpleNamespace(executables={'phenix.python':Path('/EXPLICIT_FAKE')},environment={},version='EXPLICIT_FAKE')
    receipt={}
    if changed=='none':
        m._run_trial(session,capture,phenix,1000,1200,receipt)
        assert receipt['native_mechanics']['mechanics_checks_pass'] and receipt['convergence']=='NOT_CONVERGED_LIMIT'
        assert seen==['trial','readback']
    else:
        with pytest.raises(ValueError):m._run_trial(session,capture,phenix,1000,1200,receipt)
        assert seen==(['trial'] if changed=='worker_failure' else ['trial','readback'])
