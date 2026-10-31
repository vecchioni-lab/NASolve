"""Synthetic policy shuttle guardrails and deleted-build transport."""
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
from tests.test_cif_na_policy import fixture
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('na_policy_template',ROOT/'scripts/cif_na_policy_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(root):
    root.mkdir(parents=True);model,ph,native=fixture(root)
    m=template();entries={};inputs=[]
    data=[('model',model.read_bytes())]+[('dictionary',b'EXPLICIT_SYNTHETIC_CIF')]*19+ [('phil',ph.read_bytes())]+[('phil',b'# retained empty fixture\n')]*11
    for i,(role,payload) in enumerate(data):
        name=f'inputs/{i:03d}_{role}'+{'model':'.pdb','dictionary':'.cif','phil':'.phil'}[role]
        entries[m.CAPTURE_PREFIX+'/'+name]=payload
        inputs.append({'role':role,'anchor':'native_directory','path':name,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
    native.update(status='REVIEW',atom_count=len(native['atoms']))
    payload=json.dumps(native).encode();entries[m.CAPTURE_PREFIX+'/native_validation.json']=payload
    capture={'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,'execution':{'returncode':0},
        'inputs':inputs,'outputs':[{'anchor':'native_directory','path':'native_validation.json','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}],
        'native_validation':native}
    entries[m.CAPTURE_PREFIX+'/native_receipt.json']=json.dumps(capture).encode()
    entries[m.INITIAL_MODEL]=model.read_bytes().replace(b'   0.000',b'   0.100',1)
    entries['candidate/geometry_trial_model.pdb']=model.read_bytes()
    prior={'kind':'cif-fixed-native-geometry-probe','delivery_prefix':'20_Cedar','status':'REVIEW','analysis_completed':False,
        'original_archive_preserved':True,'native_execution':'COMPLETED','model_optimization':'REUSED_COMPLETED_TRIAL','automatic_adoption':False,
        'error':'Geometry candidate changed native identities, definitions or proxies','native_roundtrip':capture,
        'native_mechanics':{'checks':[{'status':'PASS'}]*11+[{'status':'REVIEW'}]*3}}
    entries['probe_receipt.json']=json.dumps(prior).encode()
    for i in range(367-len(entries)):entries[f'padding/{i:03d}.txt']=b'PRESERVED_SYNTHETIC'
    path=root/'review.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['archive','unsafe','duplicate','symlink','payload','verdict'])
def test_review_capsule_rejects_changes_before_execution(tmp_path,defect):
    m=template();path=capsule(tmp_path/'case');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'CHANGED')
    else:
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escaped']=entries.pop('padding/000.txt')
        if defect=='verdict':
            r=json.loads(entries['probe_receipt.json']);r['native_mechanics']['checks']=[];entries['probe_receipt.json']=json.dumps(r).encode()
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'CHANGED'
            with zipfile.ZipFile(path,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):m._read_capsule(path,expected)


def test_source_bundled_policy_compiles_after_both_builds_are_deleted(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    path=capsule(tmp_path/'protected');expected=hashlib.sha256(path.read_bytes()).hexdigest()
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    source=(ROOT/'scripts/cif_na_policy_probe_template.py').read_text().replace(template().REVIEW_SHA256,expected)
    (root/'scripts/cif_na_policy_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'21_Cedar_probe_cif_na_policy.py'
    metadata=build(root,nar,runner,template_name='cif_na_policy_probe_template.py')
    assert metadata['delivery_prefix']=='21_Cedar' and metadata['kind']=='cif-na-policy-probe-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'outputs'),'--inspect-only'],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    receipt=json.loads(next((tmp_path/'outputs').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['frozen_inputs_preserved'] and receipt['original_archive_preserved']
    assert receipt['compiled_policy']['pair_count']==1 and receipt['compiled_policy']['stack_count']==1
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_optimization']=='NOT_RUN'
    assert receipt['automatic_adoption'] is False
    assert path.read_bytes() and 'stopped' not in result.stderr
