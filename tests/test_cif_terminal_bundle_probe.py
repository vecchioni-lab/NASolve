"""Bounded review transport and native orchestration, with explicit fake APIs."""
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
    spec=importlib.util.spec_from_file_location('terminal_bundle_template',ROOT/'scripts/cif_terminal_bundle_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capsule(tmp_path):
    entries={'probe_receipt.json':json.dumps({'kind':'cif-linked-native-probe','delivery_prefix':'09_Cedar',
        'original_archive_preserved':True}).encode()}
    entries.update({f'evidence/{i:03d}.txt':b'bounded' for i in range(206)})
    path=tmp_path/'review.zip'
    with zipfile.ZipFile(path,'w') as z:
        for n,data in entries.items():z.writestr(n,data)
        z.writestr('manifest.json',json.dumps({n:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for n,data in entries.items()}))
    return path


def test_every_capsule_payload_is_verified_before_selection(tmp_path):
    module=template();path=capsule(tmp_path);original=path.read_bytes()
    members,receipt,data=module._read_capsule(path,hashlib.sha256(original).hexdigest(),207,'cif-linked-native-probe','09_Cedar')
    assert len(members)==208 and receipt['original_archive_preserved']
    assert path.read_bytes()==data==original
    chosen=tmp_path/'selected';module._materialize(members,['evidence/002.txt'],chosen)
    assert [p.relative_to(chosen).as_posix() for p in chosen.rglob('*') if p.is_file()]==['evidence/002.txt']


@pytest.mark.parametrize('defect',['archive','payload'])
def test_changed_capsule_or_payload_is_refused(tmp_path,defect):
    module=template();path=capsule(tmp_path);expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='archive':path.write_bytes(path.read_bytes()+b'changed')
    else:
        with zipfile.ZipFile(path) as z:members={n:z.read(n) for n in z.namelist()}
        members['evidence/002.txt']=b'changed'
        path.unlink()
        with zipfile.ZipFile(path,'w') as z:
            for n,data in members.items():z.writestr(n,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):module._read_capsule(path,expected,207,'cif-linked-native-probe','09_Cedar')


def test_installed_authority_rebases_only_through_the_declared_installation(tmp_path):
    module=template();root=tmp_path/'relocated-phenix';(root/'bin').mkdir(parents=True);(root/'lib').mkdir()
    executable=root/'bin/phenix.python';executable.write_bytes(b'fake dispatcher')
    api=root/'lib/api.py';api.write_bytes(b'fake API');source=root/'lib/source.cif';source.write_bytes(b'fake source')
    receipt={'phenix_version':'fake','executable_provenance':'/retired/phenix/bin/phenix.python',
        'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'native_resources':{'api_sources':[{'historical_path':'/retired/phenix/lib/api.py','sha256':hashlib.sha256(api.read_bytes()).hexdigest()}],
            'source_files':[{'historical_path':'/retired/phenix/lib/source.cif','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}}
    file=tmp_path/'resource_receipt.json';file.write_text(json.dumps(receipt))
    installation=SimpleNamespace(root=root,version='fake',executables={'phenix.python':executable})
    result=module._installation_fingerprints(installation,file)
    assert {r['path'] for r in result}=={'lib/api.py','lib/source.cif'}
    assert all(r['anchor']=='phenix_installation' for r in result)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='authority changed'):module._installation_fingerprints(installation,file)


@pytest.mark.parametrize('mode',['inspect','native_failed','charge_review'])
def test_orchestration_preserves_both_archives_and_qualification_review(tmp_path,monkeypatch,mode):
    from nasolve import phenix_runtime,cif_native_validation,cif_terminal_qualification
    module=template();module.BUNDLE={'delivery_prefix':'12_Cedar'}
    protected=tmp_path/'protected';protected.mkdir();linked=protected/'09.zip';terminal=protected/'11.zip'
    linked.write_bytes(b'original linked');terminal.write_bytes(b'original terminal')
    originals={name:(p,p.read_bytes()) for name,p in [('09_Cedar',linked),('11_Cedar',terminal)]}
    monkeypatch.setattr(module,'_runtime_members',lambda:{})
    monkeypatch.setattr(module,'_freeze_inputs',lambda *a:({'verified_archives':{}},originals))
    def prepare(session,state):
        model=session/'model.pdb';model.write_text('END\n')
        before=session/'before.cif';before.write_text('before')
        after=session/'after.cif';after.write_text('after')
        return {'model':model,'old_cifs':[before],'old_phils':[],'cifs':[after],'phils':[],
            'preparations':[{'sites':[{'site':'E:1','terminal_hydroxyl':{'hydrogen':"HO5'"}}]}],
            'projections':{},'five_cm_preparation':{'status':'PREPARED'},'resource_receipt':session/'not-needed.json'}
    monkeypatch.setattr(module,'_prepare_candidate',prepare)
    monkeypatch.setattr(module,'_installation_fingerprints',lambda *a:[])
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *a,**k:SimpleNamespace(
        environment={},version='fake',executables={'phenix.python':Path(sys.executable)}))
    calls=[]
    def native(model,cifs,*a,**kwargs):
        calls.append((model,cifs,kwargs))
        status='FAILED' if mode=='native_failed' else 'REVIEW'
        return {'status':status,'native_validation':{'status':status},'error':'fake native failure' if status=='FAILED' else None}
    monkeypatch.setattr(cif_native_validation,'inspect_native_bundle',native)
    monkeypatch.setattr(cif_terminal_qualification,'qualify_terminal_bundle',lambda *a,**k:{
        'status':'REVIEW','checks':[{'check':'formal-charge-readback','status':'UNSUPPORTED'}]})
    argv=['runner','--linked-review-zip',str(linked),'--terminal-review-zip',str(terminal),'--output-parent',str(tmp_path/'out')]
    if mode=='inspect':argv.append('--inspect-only')
    monkeypatch.setattr(sys,'argv',argv)
    assert module.main()==(0 if mode=='inspect' else 2)
    assert len(calls)==(0 if mode=='inspect' else 2)
    if calls:
        assert calls[0][1][0].name=='before.cif' and calls[1][1][0].name=='after.cif'
        assert all(c[2]['inventory_detail']=='linked' for c in calls)
    session=next((tmp_path/'out').glob('12_Cedar_cif-terminal-bundle-*'))
    receipt=json.loads((session/'probe_receipt.json').read_text())
    assert receipt['original_archives_preserved']=={'09_Cedar':True,'11_Cedar':True}
    assert receipt['automatic_adoption'] is False and receipt['refinement']=='NOT_RUN'
    assert receipt['status']=={'inspect':'PREPARED_REVIEW_NATIVE_NOT_RUN','native_failed':'NATIVE_REVIEW','charge_review':'REVIEW'}[mode]
    assert list(session.glob('12_Cedar_*_cif_terminal_bundle_review.zip'))
    assert all(path.read_bytes()==data for path,data in originals.values())


def test_bundled_delivery_runs_after_original_builds_are_gone(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/cif_terminal_bundle_probe_template.py',root/'scripts/cif_terminal_bundle_probe_template.py')
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    script=tmp_path/'12_Cedar_probe_cif_terminal_bundle.py'
    metadata=build(root,nar,script,template_name='cif_terminal_bundle_probe_template.py')
    assert metadata['delivery_prefix']=='12_Cedar' and metadata['prior_native_results_included'] is False
    shutil.rmtree(root);shutil.rmtree(nar)
    assert subprocess.run([sys.executable,'-B',str(script),'--help'],capture_output=True).returncode==0
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True)
    (poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    bad=tmp_path/'protected/review.zip';bad.parent.mkdir();bad.write_bytes(b'bad')
    result=subprocess.run([sys.executable,'-B',str(script),'--linked-review-zip',str(bad),'--terminal-review-zip',str(bad),
        '--output-parent',str(tmp_path/'out'),'--inspect-only'],capture_output=True,text=True,
        env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'hash-bound 09_Cedar' in result.stderr
    assert 'poisoned import' not in result.stderr
