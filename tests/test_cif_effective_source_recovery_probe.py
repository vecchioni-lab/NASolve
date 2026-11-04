"""Cedar 18 integrity and phase ordering; native paths use explicit fakes."""
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

from tests.test_cif_fragment_restoration_probe import capsule as fragment_capsule
from tests.test_cif_geometry_review_probe import write_capsule
from tests.test_cif_effective_source_recovery import case

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('effective_source_template',ROOT/'scripts/cif_effective_source_recovery_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(directory):
    old=fragment_capsule(directory/'old')
    from tests.test_cif_fragment_restoration_probe import template as old_template
    old_module=old_template()
    members,evidence,capture,_=old_module._read_capsule(old,hashlib.sha256(old.read_bytes()).hexdigest())
    prefix=template().CAPTURE_PREFIX
    entries={'inputs/review/'+n:data for n,data in members.items()}
    old_prefix=old_module.CAPTURE_PREFIX
    for name,data in members.items():
        if name.startswith(old_prefix+'/'):entries[prefix+name[len(old_prefix):]]=data
    checks={'mechanics_checks_pass':True,'checks':[{'status':'PASS','check':'EXPLICIT_FAKE'}]}
    entries['native_mechanics.json']=json.dumps(checks).encode()
    entries['probe_receipt.json']=json.dumps({'kind':'cif-fragment-restoration-native-probe','delivery_prefix':'17_Cedar',
        'analysis_completed':True,'status':'REVIEW','original_archive_preserved':True,'frozen_inputs_preserved':True,
        'native_validation':capture,'native_mechanics':checks,'prior_qualification':{'status':'REVIEW'},'source_assessments':[]}).encode()
    # Retain all anchored native files but trim padding to this delivery's exact inventory.
    for name in list(entries):
        if name.startswith('inputs/review/padding/'):del entries[name]
    for i in range(129-len(entries)):entries[f'padding/{i:03d}.txt']=b'UNSELECTED_BUT_VERIFIED'
    assert len(entries)==129
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


@pytest.mark.parametrize('verdict',['PASS','FORMAL_UNAVAILABLE','TARGET_REVIEW','OTHER_UNSUPPORTED','GENERATION_REJECTED'])
def test_generation_and_native_definition_gates_precede_any_fragment_edit(tmp_path,monkeypatch,verdict):
    m=template();n,model,source,audit=case(tmp_path)
    from tests.test_cif_fragment_restoration import fixture
    # Fresh generic raw/parent witnesses, isolated from the case's source resource.
    witness=tmp_path/'witness';witness.mkdir();raw,_,parent,_,_=fixture(witness)
    run=tmp_path/'session/inputs/review/inputs/review/inputs/run/PostMR/Model';run.mkdir(parents=True)
    shutil.copyfile(raw,run/'after_coot_raw.pdb')
    session=tmp_path/'session';installation=tmp_path/'phenix';installation.mkdir();elbow=installation/'phenix.elbow';elbow.write_text('EXPLICIT_FAKE')
    phenix=SimpleNamespace(root=installation,version='EXPLICIT_FAKE',environment={},executables={'phenix.elbow':elbow,'phenix.python':Path(sys.executable)})
    state={'plan':{'blocked':[],'recovery_codes':['ZZZ'],'selected':[{'component':'ZZZ','sites':['Z:9']}]},
        'sources':{'ZZZ':source},'model':model,'cifs':[source],'phils':[],'parents':{'Z:9':parent}}
    calls=[]
    def generate(*args,**kwargs):
        directory=tmp_path/'generated';directory.mkdir();shutil.copyfile(source,directory/'candidate.cif')
        return {'status':'REJECTED' if verdict=='GENERATION_REJECTED' else 'CANDIDATE_REVIEW','candidate_directory':str(directory)}
    def prepare(*args,**kwargs):
        directory=Path(args[4]);directory.mkdir(parents=True)
        for name in ['base_dictionary.cif','site_modifications.cif','site_modifications.phil']:(directory/name).write_text('EXPLICIT_FAKE')
        return {'sites':[{'site':'Z:9','modification_id':'FAKE_MOD'}],
            'outputs':{key:{'path':name} for key,name in [('dictionary','base_dictionary.cif'),('modifications','site_modifications.cif'),('parameters','site_modifications.phil')]}}
    def inspect(path,*args,**kwargs):
        calls.append(Path(path));after=deepcopy(n)
        after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][7]['type']='single'
        after['monomer_mappings']['rows'][0]['chem_mod_ids']['ids']=['FAKE_MOD']
        points=[[float(l[i:i+8]) for i in (30,38,46)] for l in Path(path).read_text().splitlines() if l.startswith('HETATM')]
        for atom,point in zip(after['atoms'],points):atom['xyz']=point
        after['geometry']['sites_cart_exact']=points
        return {'status':'REVIEW','execution':{'status':'COMPLETED'},'native_validation':after}
    checks=[{'check':'source-targets','status':'REVIEW' if verdict=='TARGET_REVIEW' else 'PASS'}]
    if verdict in {'FORMAL_UNAVAILABLE','OTHER_UNSUPPORTED'}:
        checks.append({'check':'effective-site-formal-charges:Z:9' if verdict=='FORMAL_UNAVAILABLE' else 'unknown','status':'UNSUPPORTED','contradictions':[]})
    monkeypatch.setattr('nasolve.cif_generation.generate_elbow_candidate',generate)
    monkeypatch.setattr('nasolve.cif_linked_preparation.prepare_linked_component',prepare)
    monkeypatch.setattr('nasolve.cif_linked_qualification.declared_linear_links',lambda chains:[('Z:8','Z:9'),('Z:9','Z:10')])
    monkeypatch.setattr('nasolve.cif_terminal_qualification.qualify_terminal_bundle',lambda *a,**k:{'checks':deepcopy(checks)})
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle',inspect)
    receipt={}
    if verdict in {'PASS','FORMAL_UNAVAILABLE'}:
        m._run_recovery(session,state,{'native_validation':n},phenix,30,receipt)
        assert len(calls)==2 and calls[0]==model and calls[1]!=model
        assert receipt['fragment_preparation']['changed_atom_count']==1
        assert receipt['fragment_mechanics']['mechanics_checks_pass']
    else:
        with pytest.raises(ValueError):m._run_recovery(session,state,{'native_validation':n},phenix,30,receipt)
        assert len(calls)==(0 if verdict=='GENERATION_REJECTED' else 1)
        assert not (session/'candidate').exists()


def test_runner_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root,nar=tmp_path/'build',tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();path=capsule(tmp_path/'protected');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    source=(ROOT/'scripts/cif_effective_source_recovery_probe_template.py').read_text().replace(template().REVIEW_SHA256,digest)
    (root/'scripts/cif_effective_source_recovery_probe_template.py').write_text(source)
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    # Supply an explicit miniature source audit and inventory for planning only.
    helper=tmp_path/'planning';helper.mkdir();n,model,resource,audit=case(helper)
    with zipfile.ZipFile(path) as z:entries={k:z.read(k) for k in z.namelist() if k!='manifest.json'}
    prefix=template().CAPTURE_PREFIX
    capture=json.loads(entries[prefix+'/native_receipt.json']);capture['native_validation']=n
    encoded=json.dumps(n).encode();entries[prefix+'/native_validation.json']=encoded
    for row in capture['inputs']:
        if row['role']=='model':
            entries[prefix+'/'+row['path']]=model.read_bytes();row.update(size=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest())
    for row in capture['outputs']:
        if row['path']=='native_validation.json':row.update(size=len(encoded),sha256=hashlib.sha256(encoded).hexdigest())
    entries[prefix+'/native_receipt.json']=json.dumps(capture).encode()
    receipt=json.loads(entries['probe_receipt.json']);receipt['native_validation']=capture;entries['probe_receipt.json']=json.dumps(receipt).encode()
    entries['inputs/review/inputs/run/PostMR/Restraints/cif_doctor_source.json']=json.dumps(audit).encode()
    # One unselected padding member yields the source-audit slot without changing payload count.
    del entries['padding/000.txt'];write_capsule(path,entries)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (root/'scripts/cif_effective_source_recovery_probe_template.py').write_text(
        (ROOT/'scripts/cif_effective_source_recovery_probe_template.py').read_text().replace(template().REVIEW_SHA256,digest))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'18_Cedar_probe_cif_source_recovery.py';build(root,nar,runner,template_name='cif_effective_source_recovery_probe_template.py')
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(path),'--output-parent',str(tmp_path/'out'),'--source','ZZZ='+str(resource),'--inspect-only'],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout,(result.stdout,result.stderr)
    assert 'stopped' not in result.stderr and 'poisoned import' not in result.stderr
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_archive_preserved'] and receipt['native_execution']=='NOT_RUN'
