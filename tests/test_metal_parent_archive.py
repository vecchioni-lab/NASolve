"""Parent transport must release its scope before ordinary checked readers."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import subprocess
import sys

import pytest


def layout(tmp_path):
    root=tmp_path/'layout';root.mkdir()
    (root/'dataset').mkdir();(root/'empty').mkdir()
    (root/'dataset/model.pdb').write_bytes(b'Pristine parent coordinates\n')
    (root/'dataset/copy.pdb').write_bytes(b'Pristine parent coordinates\n')
    (root/'dataset/observations.mtz').write_bytes(b'Exact observations and Free-R flags\n')
    (root/'captured.py').write_text('raise AssertionError("Never execute captured code")\n')
    return root


def packed(tmp_path,monkeypatch=None):
    from nasolve.metal import parent_archive as m
    if monkeypatch:monkeypatch.setattr(m,'_PART_TARGET_BYTES',30)
    source=layout(tmp_path);out=tmp_path/'parent'
    return m,source,out,m.pack_parent_inputs(source,out)


def rewrite(out,change):
    p=out/'parent.json';value=json.loads(p.read_text());change(value)
    p.write_text(json.dumps(value,sort_keys=True)+'\n')
    return sha256(p.read_bytes()).hexdigest()


def test_parent_transport_outlives_transport_scope_and_preserves_inputs(tmp_path,monkeypatch):
    from nasolve import cif_runtime_evidence as owner
    m,source,out,receipt=packed(tmp_path,monkeypatch)
    expected={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
    assert receipt['parts']>1 and receipt['logical_files']==4 and receipt['unique_files']==3
    assert receipt['retirement_authorized'] is False and receipt['scientific_validation'] is False
    inner=tmp_path/'inner.zip';q=owner.pack_runtime_evidence(source,inner)
    shutil.rmtree(source)
    with patch('subprocess.Popen',side_effect=AssertionError('No execution')):
        with m.materialized_parent_inputs(out,receipt['manifest_sha256']) as (root,report):
            assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==expected
            assert (root/'empty').is_dir()
            assert report['transport_scope_closed'] is True
            assert report['retirement_authorized'] is False
            # Regression: keeping the transport working scope open makes this
            # ordinary checked-reader entry fail with "outer root scope".
            with owner.expanded_working_evidence(inner,q['archive_sha256']) as view:
                assert (view/'evidence/dataset/model.pdb').read_bytes()==expected['dataset/model.pdb']
            assert not view.exists()
            assert not (root/'dataset/model.pdb').stat().st_mode & 0o222
    assert not root.exists()
    assert report['snapshot_removed'] and report['inputs_unchanged']


def test_deterministic_packing_and_unchanged_source(tmp_path):
    m,source,out,receipt=packed(tmp_path)
    before={p:p.read_bytes() for p in source.rglob('*') if p.is_file()}
    other=tmp_path/'again';second=m.pack_parent_inputs(source,other)
    assert second==receipt
    assert {p.name:p.read_bytes() for p in out.iterdir()}=={p.name:p.read_bytes() for p in other.iterdir()}
    assert before=={p:p.read_bytes() for p in before}


@pytest.mark.parametrize('defect',['unknown','extra-key','bool-version','missing-part','duplicate-part','escape','wrong-size','wrong-part-hash','wrong-index','extra-file','case-alias'])
def test_rehashed_manifest_cannot_bypass_transport_invariants(tmp_path,defect):
    m,source,out,receipt=packed(tmp_path)
    def change(v):
        if defect=='unknown':v['kind']='unknown'
        elif defect=='extra-key':v['retirement_authorized']=True
        elif defect=='bool-version':v['schema_version']=True
        elif defect=='missing-part':v['parts']=[]
        elif defect=='duplicate-part':v['parts']*=2
        elif defect=='escape':v['parts'][0]['name']='../outside.zip'
        elif defect=='wrong-size':v['parts'][0]['bytes']+=1
        elif defect=='wrong-part-hash':v['parts'][0]['sha256']='0'*64
        elif defect=='wrong-index':v['index']['files']['dataset/model.pdb']['sha256']='0'*64
        elif defect=='extra-file':v['index']['files']['extra']=v['index']['files']['dataset/model.pdb']
        elif defect=='case-alias':v['index']['files']['DATASET/MODEL.pdb']=v['index']['files']['dataset/model.pdb']
    digest=rewrite(out,change)
    with pytest.raises(ValueError):
        with m.materialized_parent_inputs(out,digest):pytest.fail('Invalid transport accepted')


@pytest.mark.parametrize('defect',['manifest-hash','missing-file','part-corruption','part-symlink','directory-symlink'])
def test_missing_changed_or_symlink_transport_refuses(tmp_path,defect):
    m,source,out,receipt=packed(tmp_path)
    part=out/'part-001.zip';digest=receipt['manifest_sha256']
    if defect=='manifest-hash':digest='0'*64
    elif defect=='missing-file':part.unlink()
    elif defect=='part-corruption':part.write_bytes(b'changed')
    elif defect=='part-symlink':
        other=tmp_path/'other.zip';part.rename(other);part.symlink_to(other)
    else:
        other=tmp_path/'alias';other.symlink_to(out,target_is_directory=True);out=other
    with pytest.raises(ValueError):
        with m.materialized_parent_inputs(out,digest):pytest.fail('Changed transport accepted')


@pytest.mark.parametrize('defect',['changed','extra','empty-dir','symlink','part-changed','manifest-changed'])
def test_exit_detects_changed_snapshot_or_bundle_and_cleans(tmp_path,defect):
    m,source,out,receipt=packed(tmp_path)
    with pytest.raises(ValueError):
        with m.materialized_parent_inputs(out,receipt['manifest_sha256']) as (root,report):
            if defect=='changed':
                p=root/'dataset/model.pdb';p.chmod(0o600);p.write_text('changed')
            elif defect=='extra':root.chmod(0o700);(root/'extra').write_text('extra')
            elif defect=='empty-dir':root.chmod(0o700);(root/'extra-dir').mkdir()
            elif defect=='symlink':
                p=root/'dataset';p.chmod(0o700);(p/'link').symlink_to(source/'dataset/model.pdb')
            elif defect=='part-changed':(out/'part-001.zip').write_bytes(b'changed')
            else:(out/'parent.json').write_text('{}')
    assert not root.exists()
    assert report['snapshot_removed'] is True


def test_caller_exception_cleans_and_nested_parent_scope_refuses(tmp_path):
    m,source,out,receipt=packed(tmp_path)
    with pytest.raises(RuntimeError,match='consumer stopped'):
        with m.materialized_parent_inputs(out,receipt['manifest_sha256']) as (root,report):
            with pytest.raises(ValueError,match='parent scope'):
                with m.materialized_parent_inputs(out,receipt['manifest_sha256']):pytest.fail('Nested parent snapshot')
            raise RuntimeError('consumer stopped')
    assert not root.exists() and report['snapshot_removed']
    with m.materialized_parent_inputs(out,receipt['manifest_sha256']) as (root,_):assert root.is_dir()
    assert not root.exists()


@pytest.mark.parametrize('budget',[1,True,0,-1])
def test_budget_refusal_precedes_temporary_allocation(tmp_path,monkeypatch,budget):
    m,source,out,receipt=packed(tmp_path)
    monkeypatch.setattr(m,'TemporaryDirectory',lambda *a,**kw:pytest.fail('Allocated before budget check'))
    with pytest.raises(ValueError):
        with m.materialized_parent_inputs(out,receipt['manifest_sha256'],max_disk_bytes=budget):pytest.fail('Invalid budget')


def test_low_free_space_refuses_before_allocation(tmp_path,monkeypatch):
    m,source,out,receipt=packed(tmp_path)
    monkeypatch.setattr(m.shutil,'disk_usage',lambda p:shutil._ntuple_diskusage(100,99,1))
    monkeypatch.setattr(m,'TemporaryDirectory',lambda *a,**kw:pytest.fail('Allocated on full disk'))
    with pytest.raises(ValueError,match='space'):
        with m.materialized_parent_inputs(out,receipt['manifest_sha256']):pytest.fail('No space')


@pytest.mark.parametrize('defect',['unsafe-name','symlink','inside','existing','source-changed'])
def test_pack_refuses_unsafe_or_changing_layout_and_preserves_source(tmp_path,monkeypatch,defect):
    from nasolve.metal import parent_archive as m
    source=layout(tmp_path);out=tmp_path/'parent'
    if defect=='unsafe-name':(source/'timestamp:backup.gz').write_bytes(b'opaque')
    elif defect=='symlink':(source/'link').symlink_to(source/'dataset/model.pdb')
    elif defect=='inside':out=source/'parent'
    elif defect=='existing':out.mkdir();(out/'keep').write_text('keep')
    elif defect=='source-changed':
        original=m.owner._archive_bytes
        def changed(*args,**kwargs):
            value=original(*args,**kwargs);(source/'dataset/model.pdb').write_text('changed');return value
        monkeypatch.setattr(m.owner,'_archive_bytes',changed)
    with pytest.raises(ValueError):m.pack_parent_inputs(source,out)
    assert not (out/'parent.json').exists()
    if defect=='existing':assert (out/'keep').read_text()=='keep'


def test_source_and_package_relocation_with_original_absent(tmp_path):
    m,source,out,receipt=packed(tmp_path)
    old=tmp_path/'old';old.mkdir()
    shutil.copytree(Path(m.__file__).resolve().parents[2],old/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    out.rename(old/'parent');shutil.rmtree(source)
    moved=tmp_path/'moved';old.rename(moved);assert not old.exists()
    code='''import sys,subprocess
from pathlib import Path
from nasolve.metal import parent_archive as m
assert Path(m.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*a,**k):raise AssertionError('No native execution')
subprocess.Popen=forbidden
with m.materialized_parent_inputs(Path(sys.argv[2]),sys.argv[3]) as (root,report):
 assert (root/'dataset/model.pdb').read_bytes()==b'Pristine parent coordinates\\n'
assert not root.exists()
print('relocated parent transport exact')
'''
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(moved/'src'))
    r=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'parent'),receipt['manifest_sha256']],cwd=moved,env=env,text=True,capture_output=True,timeout=30)
    assert r.returncode==0,r.stderr
    assert r.stdout.strip()=='relocated parent transport exact'


def test_interrupted_publication_has_no_manifest_and_cannot_be_adopted(tmp_path,monkeypatch):
    from nasolve.metal import parent_archive as m
    source=layout(tmp_path);out=tmp_path/'partial';original=m._write
    def interrupt(path,raw):
        if path.name==m.MANIFEST:raise OSError('simulated interruption')
        original(path,raw)
    monkeypatch.setattr(m,'_write',interrupt)
    with pytest.raises(OSError,match='interruption'):m.pack_parent_inputs(source,out)
    assert (out/'part-001.zip').exists() and not (out/m.MANIFEST).exists()
    with pytest.raises(ValueError):m.pack_parent_inputs(source,out)
    with pytest.raises(ValueError):
        with m.materialized_parent_inputs(out,'0'*64):pytest.fail('Partial archive adopted')
    assert (source/'dataset/model.pdb').read_bytes()==b'Pristine parent coordinates\n'


def test_source_change_during_publication_leaves_unpublished_parts(tmp_path,monkeypatch):
    from nasolve.metal import parent_archive as m
    source=layout(tmp_path);out=tmp_path/'partial';original=m._write
    def change(path,raw):
        original(path,raw)
        (source/'dataset/model.pdb').write_text('source changed during writes')
    monkeypatch.setattr(m,'_write',change)
    with pytest.raises(ValueError,match='before manifest publication'):m.pack_parent_inputs(source,out)
    assert not (out/m.MANIFEST).exists()


def test_shared_archive_cap_is_not_enlarged(tmp_path,monkeypatch):
    from nasolve.metal import parent_archive as m
    source=layout(tmp_path);out=tmp_path/'oversized'
    from nasolve import cif_mixed_runtime_source as shared
    monkeypatch.setattr(shared,'MAX_ARCHIVE_BYTES',1)
    with pytest.raises(ValueError):m.pack_parent_inputs(source,out)
    assert not out.exists()


def test_copy_fallback_and_consumer_mutation_do_not_touch_original(tmp_path,monkeypatch):
    m,source,out,receipt=packed(tmp_path)
    def no_links(*a,**kw):raise OSError('No hard links')
    monkeypatch.setattr(m.owner.os,'link',no_links)
    with m.materialized_parent_inputs(out,receipt['manifest_sha256'],scratch_directory=tmp_path) as (root,report):
        assert (root/'dataset/copy.pdb').read_bytes()==(source/'dataset/model.pdb').read_bytes()
    assert report['inputs_unchanged'] and report['snapshot_removed']
