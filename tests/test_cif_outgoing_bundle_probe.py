"""Bounded Cedar 12 transport and native orchestration with explicit fake APIs."""
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

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('outgoing_bundle_template',ROOT/'scripts/cif_outgoing_bundle_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capsule(tmp_path):
    entries={'probe_receipt.json':json.dumps({'kind':'cif-terminal-bundle-probe','delivery_prefix':'12_Cedar',
        'status':'REVIEW','original_archives_preserved':{'09_Cedar':True,'11_Cedar':True}}).encode()}
    entries.update({f'evidence/{i:03d}.txt':b'bounded' for i in range(115)})
    path=tmp_path/'review.zip'
    with zipfile.ZipFile(path,'w') as z:
        for name,data in entries.items():z.writestr(name,data)
        z.writestr('manifest.json',json.dumps({n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in entries.items()}))
    return path


def test_every_frozen_payload_is_verified_before_materializing_selected_members(tmp_path):
    module=template();path=capsule(tmp_path);original=path.read_bytes()
    members,prior,data=module._read_capsule(path,hashlib.sha256(original).hexdigest())
    assert len(members)==117 and prior['delivery_prefix']=='12_Cedar' and path.read_bytes()==data==original
    destination=tmp_path/'selected';module._materialize(members,['evidence/002.txt'],destination)
    assert [p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()]==['evidence/002.txt']


@pytest.mark.parametrize('defect',['archive','unselected_payload','unsafe_path','duplicate','symlink'])
def test_changed_or_unsafe_capsule_is_refused(tmp_path,defect):
    module=template();path=capsule(tmp_path);expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'changed')
    else:
        with zipfile.ZipFile(path) as z:members={n:z.read(n) for n in z.namelist()}
        if defect=='unselected_payload':members['evidence/114.txt']=b'changed'
        elif defect=='unsafe_path':
            members['../unsafe.txt']=members.pop('evidence/114.txt')
            manifest=json.loads(members['manifest.json']);manifest['../unsafe.txt']=manifest.pop('evidence/114.txt')
            members['manifest.json']=json.dumps(manifest).encode()
        path.unlink()
        with zipfile.ZipFile(path,'w') as z:
            for n,data in members.items():
                if defect=='symlink' and n=='evidence/114.txt':
                    info=zipfile.ZipInfo(n);info.external_attr=0o120777<<16;z.writestr(info,data)
                else:z.writestr(n,data)
            if defect=='duplicate':
                with pytest.warns(UserWarning):z.writestr('evidence/114.txt',b'bounded')
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):module._read_capsule(path,expected)


def test_installation_sources_rebase_only_through_the_declared_anchor(tmp_path):
    module=template();root=tmp_path/'relocated';(root/'bin').mkdir(parents=True);(root/'lib').mkdir()
    dispatcher=root/'bin/phenix.python';dispatcher.write_bytes(b'FAKE_DISPATCHER')
    api=root/'lib/api.py';api.write_bytes(b'FAKE_API')
    digest=hashlib.sha256(api.read_bytes()).hexdigest()
    capture={'phenix_version':'FAKE','executable_sha256':hashlib.sha256(dispatcher.read_bytes()).hexdigest(),
        'executable_provenance':'/retired/phenix/bin/phenix.python',
        'native_validation':{'installed_api_sources':[{'historical_path':'/retired/phenix/lib/api.py','sha256':digest}]}}
    state={'installed_terminal_authorities':[{'anchor':'phenix_installation','path':'lib/api.py','sha256':digest}]}
    phenix=SimpleNamespace(root=root,version='FAKE',executables={'phenix.python':dispatcher})
    assert module._installation_fingerprints(phenix,state,capture)[0]['path']=='lib/api.py'
    api.write_bytes(b'CHANGED')
    with pytest.raises(ValueError):module._installation_fingerprints(phenix,state,capture)


def run_probe_case(tmp_path,monkeypatch,mode,phenix_selection='mocked'):
    from nasolve import cif_native_validation,cif_outgoing_qualification,phenix_runtime
    module=template();monkeypatch.setattr(module,'BUNDLE',{'delivery_prefix':'13_Cedar'})
    review=tmp_path/'protected/review.zip';review.parent.mkdir();review.write_bytes(b'original')
    monkeypatch.setattr(module,'_runtime_members',lambda:{})
    monkeypatch.setattr(module,'_freeze_inputs',lambda *args:({'prior_archive':{},'links':[]},b'original'))
    def prepare(session,state):
        model=session/'model.pdb';model.write_text('END\n')
        old=session/'old.cif';old.write_text('before');new=session/'new_mod.cif';new.write_text('after')
        return {'model':model,'old_cifs':[old],'old_phils':[],'cifs':[old,new],'phils':[],
            'new_preparations':[],'preparations':[],'projections':{},'capture':{},'captured_baseline':{}}
    monkeypatch.setattr(module,'_prepare_candidate',prepare)
    selected_roots=[]
    if phenix_selection=='mocked':
        monkeypatch.setattr(module,'_installation_fingerprints',lambda *args:[])
        monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *args,**kwargs:SimpleNamespace(
            version='FAKE',environment={},executables={'phenix.python':Path(sys.executable)}))
    else:
        # Exercise the real loader and real executable/version discovery.
        # Only the external programs themselves are explicit shell fixtures.
        test_home=tmp_path/'test-home'
        monkeypatch.setattr(Path,'home',classmethod(lambda cls:test_home))
        root=(test_home/'Applications/phenix-2.2.1-6174') if phenix_selection=='default' else tmp_path/'explicit relocated phenix'
        (root/'bin').mkdir(parents=True)
        for name in [*phenix_runtime.REQUIRED_PROGRAMS,'phenix.python','phenix.version']:
            executable=root/'bin'/name
            executable.write_text('#!/bin/sh\nprintf "Phenix 2.2.1\\n"\n');executable.chmod(0o755)
        def fingerprints(phenix,*args):
            assert phenix.root==root.resolve() and phenix.version=='2.2.1'
            assert phenix.executables['phenix.python']==root/'bin/phenix.python'
            selected_roots.append(phenix.root)
            return []
        monkeypatch.setattr(module,'_installation_fingerprints',fingerprints)
    def verify(*args):
        if mode=='frozen_input_changed':raise ValueError('Frozen bundle input changed')
    monkeypatch.setattr(module,'_verify_frozen_inputs',verify)
    calls=[]
    def native(model,cifs,*args,**kwargs):
        calls.append((model,cifs,kwargs));status='FAILED' if mode=='native_failed' else 'REVIEW'
        return {'status':status,'native_validation':{'status':status}}
    monkeypatch.setattr(cif_native_validation,'inspect_native_bundle',native)
    monkeypatch.setattr(cif_outgoing_qualification,'qualify_outgoing_bundle',lambda *args,**kwargs:{
        'status':'OUTGOING_BUNDLE_MECHANICS_PASS' if mode=='frozen_input_changed' else 'REVIEW',
        'checks':[{'check':'formal-charge-readback','status':'UNSUPPORTED'}]})
    argv=['runner','--review-zip',str(review),'--output-parent',str(tmp_path/'out')]
    if phenix_selection=='explicit':argv.extend(['--phenix-root',str(root)])
    if mode=='inspect':argv.append('--inspect-only')
    monkeypatch.setattr(sys,'argv',argv)
    assert module.main()==(0 if mode=='inspect' else 2)
    assert len(calls)==(0 if mode=='inspect' else 2)
    if calls:
        assert calls[0][0]==calls[1][0] and len(calls[0][1])==1 and len(calls[1][1])==2
        assert all(c[2]['inventory_detail']=='linked' for c in calls)
    session=next((tmp_path/'out').glob('13_Cedar_cif-outgoing-bundle-*'))
    receipt=json.loads((session/'probe_receipt.json').read_text())
    assert receipt['status']=={'inspect':'PREPARED_REVIEW_NATIVE_NOT_RUN','charge_review':'REVIEW',
        'native_failed':'NATIVE_REVIEW','frozen_input_changed':'REVIEW'}[mode]
    assert receipt['original_archive_preserved'] is True and review.read_bytes()==b'original'
    assert receipt['automatic_adoption'] is False and receipt['refinement']=='NOT_RUN'
    assert list(session.glob('13_Cedar_*_cif_outgoing_bundle_review.zip'))
    if phenix_selection!='mocked':assert selected_roots==[root.resolve(),root.resolve()]


@pytest.mark.parametrize('mode',['inspect','charge_review','native_failed','frozen_input_changed'])
def test_probe_keeps_preparation_native_execution_and_adoption_separate(tmp_path,monkeypatch,mode):
    run_probe_case(tmp_path,monkeypatch,mode)


@pytest.mark.parametrize('selection',['default','explicit'])
def test_native_cli_resolves_a_real_candidate_before_interpretation(tmp_path,monkeypatch,selection):
    run_probe_case(tmp_path,monkeypatch,'charge_review',phenix_selection=selection)


def test_bundled_probe_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/cif_outgoing_bundle_probe_template.py',root/'scripts/cif_outgoing_bundle_probe_template.py')
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'13_Cedar_probe_cif_outgoing_bundle.py';metadata=build(root,nar,runner,template_name='cif_outgoing_bundle_probe_template.py')
    assert metadata['delivery_prefix']=='13_Cedar' and metadata['kind']=='cif-outgoing-bundle-probe-shuttle'
    assert metadata['prior_native_results_included'] is False
    shutil.rmtree(root);shutil.rmtree(nar)
    assert subprocess.run([sys.executable,'-B',str(runner),'--help'],capture_output=True).returncode==0
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    bad=tmp_path/'protected/review.zip';bad.parent.mkdir();bad.write_bytes(b'bad')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(bad),
        '--output-parent',str(tmp_path/'out'),'--inspect-only'],capture_output=True,text=True,
        cwd=tmp_path,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'hash-bound 12_Cedar' in result.stderr
    assert 'poisoned import' not in result.stderr
