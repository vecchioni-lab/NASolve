"""Transport/integrity regressions; native execution is explicitly faked here."""
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

from tests.test_cif_fragment_restoration import fixture
from tests.test_cif_geometry_review_probe import write_capsule

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('fragment_probe_template',ROOT/'scripts/cif_fragment_restoration_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def capsule(directory):
    from nasolve.cif_construction_provenance import declared_coot_references
    directory.mkdir(parents=True,exist_ok=True)
    raw,model,parent,n,_=fixture(directory);m=template();prefix=m.CAPTURE_PREFIX
    script="""import coot
coot.write_pdb_file(imol, '/old/run/PostMR/Coot/parent_Z_9_DC.pdb')
print('NASOLVE_OVERLAP', 'Z:9', overlap_status)
"""
    sources={'PostMR/Model/after_coot_raw.pdb':raw.read_bytes(),'PostMR/Coot/parent_Z_9_DC.pdb':parent.read_bytes(),
             'PostMR/Coot/mutate.py':script.encode()}
    entries={'inputs/run/'+name:data for name,data in sources.items()}
    inputs=[]
    for i,role in enumerate(['model']+['dictionary']*18+['phil']*11):
        name=f'inputs/{i:03d}_{role}.txt';data=model.read_bytes() if role=='model' else f'EXPLICIT_FAKE_{i}'.encode()
        entries[prefix+'/'+name]=data
        inputs.append({'anchor':'native_directory','path':name,'role':role,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    native_data=json.dumps(n).encode();entries[prefix+'/native_validation.json']=native_data
    capture={'native_validation':n,'inputs':inputs,'outputs':[{'anchor':'native_directory','path':'native_validation.json',
        'size':len(native_data),'sha256':hashlib.sha256(native_data).hexdigest()}],
        'execution':{'status':'COMPLETED','returncode':0},'phenix_version':'EXPLICIT_FAKE'}
    entries[prefix+'/native_receipt.json']=json.dumps(capture).encode()
    evidence={'historical_run_provenance':'/old/run','saved_script_declarations':declared_coot_references(script,'/old/run'),
        'source_artifacts':{name:{'anchor':'run','path':name,'status':'RECORDED','size':len(data),
            'sha256':hashlib.sha256(data).hexdigest()} for name,data in sources.items()}}
    entries['construction_evidence.json']=json.dumps(evidence).encode()
    entries['construction_provenance.json']=json.dumps({'analysis_completed':True}).encode()
    entries['probe_receipt.json']=json.dumps({'kind':'cif-construction-provenance-probe','delivery_prefix':'16_Cedar',
        'analysis_completed':True,'status':'REVIEW','original_run_preserved':True,'original_archive_preserved':True,'frozen_inputs_preserved':True}).encode()
    entries['inputs/review/prior_evidence.json']=json.dumps({'prior_qualification':{'status':'REVIEW','checks':[]},'source_assessments':[]}).encode()
    for i in range(74-len(entries)):entries[f'padding/{i:03d}.txt']=b'UNSELECTED_BUT_VERIFIED'
    path=directory/'captured.zip';write_capsule(path,entries);return path


@pytest.mark.parametrize('defect',['archive','unsafe_path','duplicate','symlink','unselected_payload'])
def test_changed_or_unsafe_capsule_is_refused(tmp_path,defect):
    m=template();path=capsule(tmp_path);expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'changed')
    else:
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe_path':entries['../escaped.txt']=entries.pop('padding/000.txt')
        write_capsule(path,entries,duplicate=defect=='duplicate',symlink=defect=='symlink')
        if defect=='unselected_payload':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'changed'
            with zipfile.ZipFile(path,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):m._read_capsule(path,expected)


@pytest.mark.parametrize('native_status',['NOT_RUN','COMPLETED','FAILED'])
def test_cli_keeps_inputs_and_reports_native_success_or_failure_honestly(tmp_path,monkeypatch,native_status):
    m=template();path=capsule(tmp_path/'protected');original=path.read_bytes()
    m.REVIEW_SHA256=hashlib.sha256(original).hexdigest();m.BUNDLE={'delivery_prefix':'17_Cedar'}
    monkeypatch.setattr(m,'_runtime_members',lambda:{})
    monkeypatch.setattr(m,'_fingerprints',lambda *args:[])
    monkeypatch.setattr('nasolve.phenix_runtime.installation_from_candidate',lambda *a,**k:SimpleNamespace(environment={},version='EXPLICIT_FAKE',executables={'phenix.python':Path(sys.executable)}))
    def fake_inspect(model,*args,**kwargs):
        members,evidence,capture,_=m._read_capsule(path);n=deepcopy(capture['native_validation'])
        points=[[float(l[i:i+8]) for i in (30,38,46)] for l in model.read_text().splitlines() if l.startswith('HETATM')]
        for a,p in zip(n['atoms'],points):a['xyz']=p
        n['geometry']['sites_cart_exact']=points
        return {'status':'REVIEW' if native_status=='COMPLETED' else 'FAILED',
            'execution':{'status':native_status,'returncode':0 if native_status=='COMPLETED' else 1},'native_validation':n,'error':'EXPLICIT_FAKE_FAILURE'}
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle',fake_inspect)
    argv=['runner','--review-zip',str(path),'--output-parent',str(tmp_path/'out')]
    if native_status=='NOT_RUN':argv.append('--inspect-only')
    monkeypatch.setattr(sys,'argv',argv)
    assert m.main()==2
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] is (native_status!='FAILED')
    assert receipt['native_execution']==native_status
    assert receipt['original_archive_preserved'] and receipt['frozen_inputs_preserved']
    assert not receipt['automatic_adoption'] and receipt['status']=='REVIEW'
    assert path.read_bytes()==original
    if native_status=='COMPLETED':assert receipt['native_mechanics']['mechanics_checks_pass']


def test_runner_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root,nar=tmp_path/'build',tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    path=capsule(tmp_path/'protected');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    source=(ROOT/'scripts/cif_fragment_restoration_probe_template.py').read_text().replace(template().REVIEW_SHA256,digest)
    (root/'scripts/cif_fragment_restoration_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'17_Cedar_probe_cif_fragment_restoration.py'
    metadata=build(root,nar,runner,template_name='cif_fragment_restoration_probe_template.py')
    assert metadata['kind']=='cif-fragment-restoration-shuttle'
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True)
    (poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout
    assert 'stopped' not in result.stderr and 'poisoned import' not in result.stderr
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved']
