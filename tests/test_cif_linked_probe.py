"""Exclusive, hash-bound diagnostic transport; no native scientific claim."""
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

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('linked_template',ROOT/'scripts/cif_linked_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capsule(tmp_path):
    path=tmp_path/'review.zip'
    entries={f'evidence/{i:02d}.txt':str(i).encode() for i in range(57)}
    manifest={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in entries.items()}
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in entries.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(manifest))
    module=template();module.ARCHIVE_SHA256=hashlib.sha256(path.read_bytes()).hexdigest()
    session=tmp_path/'session';session.mkdir()
    return module,path,session


def test_freeze_checks_all_payloads_and_preserves_archive(tmp_path):
    module,path,session=capsule(tmp_path)
    before=path.read_bytes()
    copied,payload=module._freeze_review(path,session)
    assert path.read_bytes()==payload==before
    assert len(list((copied/'evidence').glob('*.txt')))==57


def test_modified_archive_rejected_before_materializing(tmp_path):
    module,path,session=capsule(tmp_path)
    with path.open('ab') as handle:handle.write(b'changed')
    with pytest.raises(ValueError,match='hash-bound'):module._freeze_review(path,session)
    assert not (session/'baseline').exists()


@pytest.mark.parametrize('name',['../escape','/absolute','a//b','a/./b','a/../b','C:/x','a\\b'])
def test_zip_paths_are_explicitly_bounded(name):
    assert template()._safe_name(name) is False


def test_review_zip_omits_embedded_runtime_and_has_integrity_manifest(tmp_path):
    module=template();module.BUNDLE={'delivery_prefix':'06_Cedar'}
    session=tmp_path/'06_Cedar_cif-linked-probe-token';session.mkdir()
    (session/'runtime').mkdir();(session/'runtime/private-code.py').write_text('code')
    (session/'probe_receipt.json').write_text('{}')
    path=module._review_zip(session)
    assert path.name=='06_Cedar_token_cif_linked_review.zip'
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist()==['probe_receipt.json','manifest.json']
        row=json.loads(archive.read('manifest.json'))['probe_receipt.json']
        assert row['sha256']==hashlib.sha256(b'{}').hexdigest()


def test_source_bundled_delivery_survives_deleted_build_checkout(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/cif_linked_probe_template.py',root/'scripts/cif_linked_probe_template.py')
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    script=tmp_path/'06_Cedar_probe_cif_linked.py'
    metadata=build(root,nar,script,template_name='cif_linked_probe_template.py')
    assert metadata['delivery_prefix']=='06_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['prior_native_results_included']
    shutil.rmtree(root);shutil.rmtree(nar)
    result=subprocess.run([sys.executable,'-B',str(script),'--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--review-zip' in result.stdout
    module_spec=importlib.util.spec_from_file_location('delivered_linked',script)
    module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    assert 'src/nasolve/cif_linked_preparation.py' in module._runtime_members()
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True)
    (poison/'__init__.py').write_text('raise RuntimeError("poisoned checkout import")\n')
    bad=tmp_path/'protected/review.zip';bad.parent.mkdir();bad.write_bytes(b'invalid archive')
    result=subprocess.run([sys.executable,'-B',str(script),'--inspect-only','--review-zip',str(bad),
                           '--output-parent',str(tmp_path/'diagnostics')],capture_output=True,text=True,
                          env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'hash-bound Cedar 05' in result.stderr
    assert 'CIF linked-state diagnostic: 06_Cedar' in result.stdout
    assert 'poisoned checkout import' not in result.stderr


@pytest.mark.parametrize('failure_layer',['native','source-recovery'])
def test_orchestration_keeps_native_failures_and_original_capsule(tmp_path,monkeypatch,capsys,failure_layer):
    from types import SimpleNamespace
    import runpy
    fixture=runpy.run_path(str(ROOT/'tests/test_cif_linked_preparation.py'))['fixture']
    native_case=runpy.run_path(str(ROOT/'tests/test_cif_linked_qualification.py'))['native_case']
    from nasolve import phenix_runtime,cif_native_validation,cif_generation
    inputs=tmp_path/'fixture';inputs.mkdir()
    source,numerical,model,_=fixture(inputs)
    model_text=model.read_text().replace('ZZZ','IGU')
    copies=[line[:22]+f'{3:4d}'+line[26:] for line in model_text.splitlines(keepends=True)
            if line.startswith(('ATOM  ','HETATM')) and line[21]=='A' and line[22:26].strip()=='2']
    model_text=model_text.replace('END\n','')+''.join(copies)+'END\n'
    model_text=''.join(line[:17]+' DG'+line[20:] if line.startswith(('ATOM  ','HETATM'))
                       and not (line[21]=='A' and line[22:26].strip()=='2') else line
                       for line in model_text.splitlines(keepends=True))
    entries={
        'inputs/prepared_model.pdb':model_text.encode(),
        'inputs/sources/7_IGU.cif':source.read_bytes().replace(b'ZZZ',b'IGU'),
        'native/cif-native-90b84f1c/inputs/000_model.pdb':model_text.encode(),
        'native/cif-native-90b84f1c/inputs/001_dictionary.cif':numerical.read_bytes().replace(b'ZZZ',b'IGU'),
        'native/cif-native-90b84f1c/native_validation.json':json.dumps(native_case()[0]).encode(),
        'native/cif-native-90b84f1c/native_spec.json':json.dumps({'dictionaries':['inputs/001_dictionary.cif'],'phil_files':[]}).encode(),
    }
    for i in range(57-len(entries)):entries[f'other/{i}.txt']=b'fixture'
    protected=tmp_path/'protected';protected.mkdir()
    archive_path=protected/'review.zip'
    with zipfile.ZipFile(archive_path,'w') as archive:
        for name,data in entries.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in entries.items()}))
    before=archive_path.read_bytes()
    module=template();module.BUNDLE={'delivery_prefix':'06_Cedar'}
    module.ARCHIVE_SHA256=hashlib.sha256(before).hexdigest()
    module.TARGETS={'IGU':('A:2','A:1','A:3',7)}
    module.CHAINS={'A':['1','2','3']}
    monkeypatch.setattr(module,'_runtime_members',lambda:{})
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *args,**kwargs:SimpleNamespace(
        executables={'phenix.python':Path(sys.executable),'phenix.elbow':Path(sys.executable)},environment={},version='fake-offline'))
    calls=[]
    def fake_native(model,dictionaries,*args,**kwargs):
        calls.append((model,dictionaries,kwargs))
        return {'status':'FAILED','native_validation':{'status':'FAILED'},'execution':{'returncode':2}}
    monkeypatch.setattr(cif_native_validation,'inspect_native_bundle',fake_native)
    if failure_layer=='source-recovery':
        monkeypatch.setattr(cif_generation,'inspect_component_generation',lambda *args,**kwargs:
                            {'status':'REJECTED','rejection_reasons':['fixture-source-state-changed']})
        monkeypatch.setattr(cif_generation,'generate_elbow_candidate',lambda *args,**kwargs:
                            {'status':'REJECTED','inspection':{'rejection_reasons':['fixture-source-state-changed']}})
    monkeypatch.setattr(sys,'argv',['runner','--review-zip',str(archive_path),'--output-parent',str(tmp_path/'output')])
    assert module.main()==2
    if failure_layer=='native':
        assert len(calls)==2 and calls[1][2]['inventory_detail']=='linked'
    else:
        assert calls==[]
    outputs=list((tmp_path/'output').glob('06_Cedar_cif-linked-probe-*'))
    receipt=json.loads((outputs[0]/'probe_receipt.json').read_text())
    assert receipt['status']==('NATIVE_REVIEW' if failure_layer=='native' else 'SOURCE_RECOVERY_REVIEW')
    assert receipt['original_archive_preserved']
    assert receipt['automatic_adoption'] is False and receipt['refinement']=='NOT_RUN'
    assert archive_path.read_bytes()==before
    stdout=capsys.readouterr().out
    assert 'REVIEW ZIP:' in stdout
    if failure_layer=='source-recovery':
        assert 'Source recovery requires review: IGU | REJECTED | fixture-source-state-changed' in stdout
    else:
        assert 'Native linked interpretation requires review: FAILED' in stdout
