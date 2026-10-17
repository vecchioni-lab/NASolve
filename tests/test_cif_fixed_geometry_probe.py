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


def test_runner_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root,nar=tmp_path/'build',tmp_path/'nar';path=capsule(tmp_path/'protected');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    (root/'scripts/cif_fixed_geometry_probe_template.py').write_text(
        (ROOT/'scripts/cif_fixed_geometry_probe_template.py').read_text().replace(template().REVIEW_SHA256,digest))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'19_Cedar_probe_cif_geometry_trial.py'
    metadata=build(root,nar,runner,template_name='cif_fixed_geometry_probe_template.py')
    assert metadata['delivery_prefix']=='19_Cedar' and metadata['kind']=='cif-fixed-native-geometry-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    assert 'stopped' not in result.stderr
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN' and not receipt['automatic_adoption']
