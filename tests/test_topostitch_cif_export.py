"""An immutable diagnostic export must remain source-bound after relocation."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
from tests.test_topostitch_cif_coverage import fixture as coverage_fixture, bind_steps
from tests.test_topostitch_cif_output import policy
from tests.test_topostitch_cif_source import edit


def fixture(tmp_path):
    root,original,_,kw,owner,payload,_=coverage_fixture(tmp_path)
    kw.update(reviewed_categories=policy(original),tls_policy='preserve_raw_no_restart',
        center_policy='unit_occupancy_present_polymer_mass',max_rotation_component_error=1e-8,
        max_translation_component_error_angstrom=1e-6,max_assembly_position_error_angstrom=1e-5)
    return root,original,kw,owner,payload


def write(root,original,output,kw):
    from nasolve.topostitch_cif_output import write_whole_asym_cif
    return write_whole_asym_cif(root,original,output_directory=output,**kw)


def load(output,kw):
    from nasolve.topostitch_cif_output import load_whole_asym_cif
    return load_whole_asym_cif(output,expected_receipt_sha256=sha256((output/'export.json').read_bytes()).hexdigest(),
        cedar_source=kw['cedar_source'])


def test_export_and_replay_survive_removal_of_original_input_paths(tmp_path):
    old=tmp_path/'old';old.mkdir();root,original,kw,owner,_=fixture(old)
    before={p:p.read_bytes()for p in [original,owner,*root.iterdir()]}
    output=old/'export';r=write(root,original,output,kw)
    assert r['complete_declared_backbone_coverage'] and r['status']=='EXPORTED_REVIEW_REQUIRED'
    assert not r['native_restart_qualified'] and not r['selection_applied']
    assert len(r['artifacts'])==9 and all(ref['anchor']=='run'for ref in r['artifacts'].values())
    assert str(old)not in json.dumps(r)
    assert all(p.read_bytes()==v for p,v in before.items())
    with pytest.raises(FileExistsError):write(root,original,output,kw)
    moved=tmp_path/'moved';moved.mkdir()
    shutil.copytree(kw['cedar_source'],moved/'reader');kw['cedar_source']=moved/'reader'
    shutil.move(output,moved/'packet');shutil.rmtree(old)
    assert not old.exists() and load(moved/'packet',kw)==r


def test_missing_coverage_never_creates_a_published_directory(tmp_path):
    root,original,kw,owner,payload=fixture(tmp_path)
    payload['model']['ordinary']['steps'].pop(0);bind_steps(owner,kw,payload)
    output=tmp_path/'missing'
    with pytest.raises(ValueError,match='complete declared backbone'):write(root,original,output,kw)
    assert not output.exists()


def test_live_source_drift_refuses_publication(tmp_path,monkeypatch):
    import nasolve.topostitch_cif_output as module
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'drift'
    prepare=module.prepare_whole_asym_cif
    def changed(*args,**kwargs):
        result=prepare(*args,**kwargs)
        original.write_bytes(original.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(module,'prepare_whole_asym_cif',changed)
    with pytest.raises(ValueError,match='Original inputs changed'):write(root,original,output,kw)
    assert not output.exists()


def test_rehashing_a_corrupt_derived_model_cannot_make_it_replay(tmp_path):
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'packet';write(root,original,output,kw)
    model=output/'representative.cif'
    def change(doc):
        t=doc[0].get_mmcif_category('_atom_site.');t['Cartn_x'][0]='999';doc[0].set_mmcif_category('_atom_site.',t)
    edit(model,change)
    with pytest.raises(ValueError,match='changed whole-asym'):load(output,kw)
    receipt=output/'export.json';r=json.loads(receipt.read_text())
    r['artifacts']['representative.cif'].update(sha256=sha256(model.read_bytes()).hexdigest(),size_bytes=model.stat().st_size)
    receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='does not reproduce'):load(output,kw)


def test_interrupted_output_has_no_completion_receipt_and_is_not_reused(tmp_path,monkeypatch):
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'partial';original_open=Path.open
    def interrupted(path,*args,**kwargs):
        if path==output/'draft.json' and args and args[0]=='xb':raise OSError('simulated interrupted write')
        return original_open(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',interrupted)
    with pytest.raises(OSError,match='interrupted'):write(root,original,output,kw)
    assert output.exists() and not(output/'export.json').exists()
    with pytest.raises(FileExistsError):write(root,original,output,kw)


def test_receipt_binding_and_external_artifact_paths_are_refused(tmp_path):
    from nasolve.topostitch_cif_output import load_whole_asym_cif
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'packet';write(root,original,output,kw)
    with pytest.raises(ValueError,match='receipt differs'):
        load_whole_asym_cif(output,expected_receipt_sha256='0'*64,cedar_source=kw['cedar_source'])
    p=output/'export.json';r=json.loads(p.read_text());r['artifacts']['original.cif']['relative_path']='../original.cif';p.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='exact local anchored'):load(output,kw)


def test_completion_receipt_is_invisible_until_complete_bytes_are_synced(tmp_path,monkeypatch):
    import os
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'atomic'
    sync=os.fsync;observed=[]
    def inspect(fd):
        pending=list(output.glob('.export-*'))
        if pending:
            data=pending[0].read_bytes()
            if data:
                assert json.loads(data)['kind']=='topostitch-whole-asym-cif-export'
                assert not(output/'export.json').exists()
                observed.append(data)
        return sync(fd)
    monkeypatch.setattr(os,'fsync',inspect)
    result=write(root,original,output,kw)
    assert observed and (output/'export.json').read_bytes()==observed[0]
    assert json.loads(observed[0])==result and not list(output.glob('.export-*'))
    assert load(output,kw)==result


def test_receipt_sync_failure_leaves_no_completion_marker(tmp_path,monkeypatch):
    import os
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'sync-failed'
    def fail(fd):raise OSError('simulated receipt sync failure')
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises(OSError,match='receipt sync failure'):write(root,original,output,kw)
    assert output.exists() and not(output/'export.json').exists()
    assert not list(output.glob('.export-*'))
    with pytest.raises(FileExistsError):write(root,original,output,kw)


def test_competing_completion_receipt_is_never_overwritten(tmp_path,monkeypatch):
    import os
    root,original,kw,_,_=fixture(tmp_path);output=tmp_path/'raced';link=os.link
    def race(source,destination,*args,**kwargs):
        if Path(destination)==output/'export.json':Path(destination).write_bytes(b'competing writer')
        return link(source,destination,*args,**kwargs)
    monkeypatch.setattr(os,'link',race)
    with pytest.raises(FileExistsError):write(root,original,output,kw)
    assert (output/'export.json').read_bytes()==b'competing writer'
    assert not list(output.glob('.export-*'))
