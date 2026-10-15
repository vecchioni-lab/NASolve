"""Cedar terminal review transport, preservation and explicit preparation scope."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('terminal_template',ROOT/'scripts/cif_terminal_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capsule(tmp_path,source=b'source'):
    module=template();root=tmp_path/'protected';root.mkdir()
    entries={module.SOURCE_MEMBER:source,'probe_receipt.json':json.dumps({
        'kind':'cif-linked-native-probe','delivery_prefix':'09_Cedar','original_archive_preserved':True,
        'status':'REVIEW','build':{'nasolve_source':{},'narestraints_source':{}}}).encode()}
    entries.update({f'evidence/{i:03d}.txt':b'bounded evidence' for i in range(205)})
    path=root/'review.zip'
    with zipfile.ZipFile(path,'w') as z:
        for name,data in entries.items():z.writestr(name,data)
        z.writestr('manifest.json',json.dumps({n:{'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d)} for n,d in entries.items()}))
    module.ARCHIVE_SHA256=hashlib.sha256(path.read_bytes()).hexdigest()
    module.BUNDLE={'delivery_prefix':'10_Cedar'}
    return module,path


def test_all_payloads_verified_but_only_declared_source_materialized(tmp_path):
    module,path=capsule(tmp_path);session=tmp_path/'session';session.mkdir()
    before=path.read_bytes();source,original,record=module._review_source(path,session)
    assert source.read_bytes()==b'source'
    assert path.read_bytes()==original==before
    assert record['verified_payloads']==207 and record['source_member']==module.SOURCE_MEMBER
    assert [p.relative_to(session).as_posix() for p in session.rglob('*') if p.is_file()]==['inputs/5CM_source.cif']


def test_changed_archive_rejected_before_source_copy(tmp_path):
    module,path=capsule(tmp_path);path.write_bytes(path.read_bytes()+b'changed')
    session=tmp_path/'session';session.mkdir()
    with pytest.raises(ValueError,match='hash-bound Cedar 09'):module._review_source(path,session)
    assert not (session/'inputs').exists()


def test_bad_payload_digest_is_not_hidden_by_matching_archive_hash(tmp_path):
    module,path=capsule(tmp_path)
    with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
    entries['evidence/002.txt']=b'changed'
    replacement=tmp_path/'bad.zip'
    with zipfile.ZipFile(replacement,'w') as z:
        for name,data in entries.items():z.writestr(name,data)
    module.ARCHIVE_SHA256=hashlib.sha256(replacement.read_bytes()).hexdigest()
    session=tmp_path/'session';session.mkdir()
    with pytest.raises(ValueError,match='payload integrity'):module._review_source(replacement,session)
    assert not (session/'inputs').exists()


@pytest.mark.parametrize('native_status',['INSPECT_ONLY','REVIEW','UNSUPPORTED'])
def test_explicit_5cm_preparation_never_adopts_or_edits_a_model(tmp_path,monkeypatch,capsys,native_status):
    from nasolve import cif_doctor_repair,phenix_runtime,cif_terminal_resources
    helper=runpy.run_path(str(ROOT/'tests/test_cif_doctor_repair.py'))['synthetic_five_cm']
    fixture=tmp_path/'fixture';fixture.mkdir();source,expected=helper(fixture,monkeypatch)
    module,path=capsule(tmp_path,source.read_bytes());before=path.read_bytes()
    monkeypatch.setattr(module,'_runtime_members',lambda:{})
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *a,**k:SimpleNamespace(
        executables={'phenix.python':sys.executable},environment={},version='fake-native'))
    calls=[]
    def inventory(*args,**kwargs):
        calls.append(args)
        return {'status':native_status,'native_resources':{'error':'fake missing resource'} if native_status=='UNSUPPORTED' else {}}
    monkeypatch.setattr(cif_terminal_resources,'inspect_terminal_resources',inventory)
    argv=['probe','--review-zip',str(path),'--output-parent',str(tmp_path/'out')]
    if native_status=='INSPECT_ONLY':argv.append('--inspect-only')
    monkeypatch.setattr(sys,'argv',argv)
    assert module.main()==(2 if native_status=='UNSUPPORTED' else 0)
    session=next((tmp_path/'out').glob('10_Cedar_cif-terminal-probe-*'))
    receipt=json.loads((session/'probe_receipt.json').read_text())
    assert (session/'5cm_preparation/5CM_candidate.cif').read_bytes()==expected.read_bytes()
    assert receipt['five_cm_preparation']['automatic_adoption'] is False
    assert receipt['terminal_recipe_implementation']=='NOT_RUN'
    assert receipt['model_editing']==receipt['refinement']=='NOT_RUN'
    assert receipt['original_archive_preserved'] and path.read_bytes()==before
    assert bool(calls)==(native_status!='INSPECT_ONLY')
    assert list(session.glob('10_Cedar_*_cif_terminal_review.zip'))
    if native_status=='UNSUPPORTED':assert 'fake missing resource' in capsys.readouterr().out


def test_output_manifest_omits_runtime_and_preserves_prefix(tmp_path):
    module=template();module.BUNDLE={'delivery_prefix':'10_Cedar'}
    session=tmp_path/'10_Cedar_cif-terminal-probe-token';session.mkdir()
    (session/'runtime').mkdir();(session/'runtime/code.py').write_text('code')
    (session/'probe_receipt.json').write_text('{}')
    path=module._review_zip(session)
    assert path.name=='10_Cedar_token_cif_terminal_review.zip'
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist())=={'probe_receipt.json','manifest.json'}
        assert json.loads(z.read('manifest.json'))['probe_receipt.json']['bytes']==2


def test_bundled_runner_survives_deleted_build_paths_and_poisoned_import(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/cif_terminal_probe_template.py',root/'scripts/cif_terminal_probe_template.py')
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in [root,nar]:
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    script=tmp_path/'10_Cedar_probe_cif_terminal_review.py'
    metadata=build(root,nar,script,template_name='cif_terminal_probe_template.py')
    assert metadata['delivery_prefix']=='10_Cedar' and not metadata['prior_native_results_included']
    shutil.rmtree(root);shutil.rmtree(nar)
    result=subprocess.run([sys.executable,'-B',str(script),'--help'],text=True,capture_output=True)
    assert result.returncode==0 and '--inspect-only' in result.stdout
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True)
    (poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    bad=tmp_path/'protected/review.zip';bad.parent.mkdir();bad.write_bytes(b'bad')
    result=subprocess.run([sys.executable,'-B',str(script),'--review-zip',str(bad),'--output-parent',str(tmp_path/'out'),'--inspect-only'],
        env={**os.environ,'PYTHONPATH':str(poison.parent)},text=True,capture_output=True)
    assert result.returncode==2 and 'hash-bound Cedar 09' in result.stderr
    assert 'poisoned import' not in result.stderr
