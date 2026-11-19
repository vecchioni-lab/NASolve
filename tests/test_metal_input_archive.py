"""Exact input transport must remain distinct from standalone scientific replay."""
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import os
import subprocess
import sys

import pytest

from tests.test_metal_compact import trials


def test_inputs_and_all_attempts_survive_without_original_data(tmp_path, monkeypatch):
    from nasolve.metal.input_archive import pack_fdp_inputs, expanded_fdp_inputs
    old=tmp_path/'original';old.mkdir()
    run, selected=trials(old,monkeypatch)
    before={p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    expected={}
    for path in selected:
        native=json.loads((run/path/'native-plan.json').read_text())
        expected[str(path)]={name:(run/path/name).read_bytes()
                            for name in set(native['args'])|{'plan.json','native-plan.json'}}
    archive=tmp_path/'inputs.zip'
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        receipt=pack_fdp_inputs(run,selected,archive)
    assert {p:p.read_bytes() for p in run.rglob('*') if p.is_file()}==before
    assert receipt['attempts']==3 and receipt['requests']==2
    assert receipt['retirement_authorized'] is False
    shutil.rmtree(old);assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        with expanded_fdp_inputs(archive,receipt['archive_sha256'],projection_id=receipt['projection_id']) as (root,projection):
            assert len(projection['records'])==3
            for record,path in zip(projection['records'],selected):
                folder=root/'requests'/record['input_id']
                assert {p.name:p.read_bytes() for p in folder.iterdir()}==expected[str(path)]
            assert projection['standalone_evidence'] is False
            assert projection['retirement_authorized'] is False
    assert not root.exists()


def test_cold_transport_requires_both_declared_identities(tmp_path,monkeypatch):
    from nasolve.metal.input_archive import pack_fdp_inputs,expanded_fdp_inputs
    run,selected=trials(tmp_path,monkeypatch,(.6,))
    archive=tmp_path/'inputs.zip';receipt=pack_fdp_inputs(run,selected,archive)
    for sha,projection in [('0'*64,receipt['projection_id']),(receipt['archive_sha256'],'0'*64)]:
        with pytest.raises(ValueError):
            with expanded_fdp_inputs(archive,sha,projection_id=projection):pytest.fail('Wrong identity accepted')


@pytest.mark.parametrize('change',['input','extra','authority'])
def test_repacked_alterations_do_not_override_recorded_inputs(tmp_path,monkeypatch,change):
    from nasolve.metal.input_archive import pack_fdp_inputs,expanded_fdp_inputs
    from nasolve import cif_runtime_evidence as owner
    from nasolve.metal.compact import encode
    from nasolve.metal.recipe import digest
    run,selected=trials(tmp_path,monkeypatch,(.6,))
    original=tmp_path/'original.zip';receipt=pack_fdp_inputs(run,selected,original)
    with owner.expanded_runtime_evidence(original,receipt['archive_sha256']) as view:
        altered=tmp_path/'altered';shutil.copytree(view/'evidence',altered)
    for p in altered.rglob('*'):
        if p.is_file():p.chmod(0o600)
    if change=='input':
        p=next((altered/'requests').glob('*/input.pdb'));p.write_bytes(p.read_bytes()+b'REMARK changed\n')
    elif change=='extra':(altered/'unused.txt').write_text('unrecorded')
    else:
        p=altered/'projection.json';value=json.loads(p.read_text());value['retirement_authorized']=True
        value.pop('projection_id');value['projection_id']=digest(value)
        p.write_bytes(encode(value));receipt['projection_id']=value['projection_id']
    rewritten=tmp_path/'rewritten.zip';packed=owner.pack_runtime_evidence(altered,rewritten)
    with pytest.raises(ValueError):
        with expanded_fdp_inputs(rewritten,packed['archive_sha256'],projection_id=receipt['projection_id']):
            pytest.fail('Repacked input alteration accepted')


def test_budget_refusal_precedes_temporary_expansion(tmp_path,monkeypatch):
    from nasolve.metal.input_archive import pack_fdp_inputs,expanded_fdp_inputs
    from nasolve import cif_runtime_evidence as owner
    run,selected=trials(tmp_path,monkeypatch,(.6,))
    target=tmp_path/'inputs.zip';receipt=pack_fdp_inputs(run,selected,target)
    monkeypatch.setattr(owner,'TemporaryDirectory',lambda *a,**kw:pytest.fail('Over-budget expansion allocated'))
    with pytest.raises(ValueError,match='budget'):
        with expanded_fdp_inputs(target,receipt['archive_sha256'],projection_id=receipt['projection_id'],max_input_bytes=1):
            pytest.fail('Over-budget input archive accepted')


def test_output_and_source_changes_refuse_before_publication(tmp_path,monkeypatch):
    from nasolve.metal import input_archive as module
    run,selected=trials(tmp_path,monkeypatch,(.6,))
    for output,options in [(run/'extra.zip',{}),(tmp_path/'small.zip',{'max_input_bytes':1}),
                           (tmp_path/'bad.zip',{'max_input_bytes':True})]:
        with pytest.raises(ValueError):module.pack_fdp_inputs(run,selected,output,**options)
        assert not output.exists()
    existing=tmp_path/'existing.zip';existing.write_bytes(b'keep')
    with pytest.raises(ValueError):module.pack_fdp_inputs(run,selected,existing)
    assert existing.read_bytes()==b'keep'
    original=module.compact.verify_projection
    def change_source(*args,**kwargs):
        p=run/selected[0]/'input.pdb';p.write_bytes(p.read_bytes()+b'REMARK changed\n')
        return original(*args,**kwargs)
    monkeypatch.setattr(module.compact,'verify_projection',change_source)
    output=tmp_path/'refused.zip'
    with pytest.raises(ValueError):module.pack_fdp_inputs(run,selected,output)
    assert not output.exists()


@pytest.mark.parametrize('missing',['parent','native-result.json.gz'])
def test_original_scientific_evidence_is_required_when_packing(tmp_path,monkeypatch,missing):
    from nasolve.metal.input_archive import pack_fdp_inputs
    run,selected=trials(tmp_path,monkeypatch,(.6,))
    if missing=='parent':shutil.rmtree(run/'Metal/geometry_001')
    else:(run/selected[0]/missing).unlink()
    output=tmp_path/'refused.zip'
    with pytest.raises(ValueError):pack_fdp_inputs(run,selected,output)
    assert not output.exists()


def test_relocated_source_and_archive_without_originals(tmp_path,monkeypatch):
    from nasolve.metal.input_archive import pack_fdp_inputs
    old=tmp_path/'old';old.mkdir()
    run,selected=trials(old,monkeypatch,(.6,))
    archive=old/'inputs.zip';receipt=pack_fdp_inputs(run,selected,archive)
    source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,old/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.rmtree(old/'dataset')
    moved=tmp_path/'moved';old.rename(moved);assert not old.exists()
    code="""import subprocess,sys
from pathlib import Path
import nasolve.metal.input_archive as module
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*args,**kwargs):raise AssertionError('No process during expansion')
subprocess.Popen=forbidden
with module.expanded_fdp_inputs(Path(sys.argv[2]),sys.argv[3],projection_id=sys.argv[4]) as (root,projection):
 assert len(projection['records'])==1
 assert (root/'requests'/projection['records'][0]['input_id']/'input.pdb').is_file()
assert not root.exists()
print('relocated input transport exact')
"""
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(moved/'src'),os.environ.get('PYTHONPATH','')]))
    completed=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'inputs.zip'),
        receipt['archive_sha256'],receipt['projection_id']],cwd=moved,env=env,capture_output=True,text=True,timeout=30)
    assert completed.returncode==0,completed.stderr
    assert completed.stdout.strip()=='relocated input transport exact'
