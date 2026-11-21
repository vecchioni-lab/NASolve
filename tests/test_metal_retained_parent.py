"""One retained transport snapshot, fresh scientific replay on every read."""
from contextvars import Context
from pathlib import Path
from unittest.mock import patch
import shutil
import pytest
from nasolve.metal import parent_archive as m
from tests.test_metal_parent_archive import packed
from tests.test_metal_child_inputs import prepared_case, verify


def files(root):
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_repeated_reads_share_snapshot_with_closed_archive_owner(tmp_path):
    from nasolve import cif_runtime_evidence as owner
    _,source,archive,record=packed(tmp_path)
    original=files(source);saved=files(archive)
    nested=tmp_path/'nested.zip';inner=owner.pack_runtime_evidence(source,nested)
    with patch.object(m.shutil,'copytree',wraps=m.shutil.copytree) as copy:
        with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
            roots=[];reports=[]
            for _ in range(3):
                with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained) as (root,report):
                    roots.append(root);reports.append(report)
                    assert files(root)==original
                    assert not (root/'dataset/model.pdb').stat().st_mode & 0o222
                    with owner.expanded_working_evidence(nested,inner['archive_sha256']) as view:
                        assert (view/'evidence/dataset/model.pdb').read_bytes()==original['dataset/model.pdb']
                    assert not view.exists()
                assert report['read_scope_closed'] and report['inputs_unchanged'] and report['consumer_completed']
                assert report['snapshot_removed'] is False
                assert not report['scientific_validation'] and not report['reuse_authorized']
            assert len(set(roots))==1 and reports[0]==reports[1]==reports[2]
            # copytree recurses internally: count only the outer transport call.
            assert sum(Path(c.args[0]).name=='evidence' for c in copy.call_args_list)==1
        assert not root.exists()
    assert files(source)==original and files(archive)==saved
    with pytest.raises(ValueError,match='active retained'):
        with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):pytest.fail('Expired handle reused')


@pytest.mark.parametrize('defect',['snapshot','archive','manifest'])
def test_change_between_reads_poisoned_even_after_restore(tmp_path,defect):
    _,source,archive,record=packed(tmp_path)
    saved=files(source)
    with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
        with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained) as (root,_):pass
        target={'snapshot':root/'dataset/model.pdb','archive':archive/'part-001.zip','manifest':archive/'parent.json'}[defect]
        raw=target.read_bytes();mode=target.stat().st_mode;target.chmod(0o600);target.write_bytes(b'changed')
        try:
            with pytest.raises(ValueError):
                with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):pytest.fail('Changed parent accepted')
        finally:target.write_bytes(raw);target.chmod(mode)
        with pytest.raises(ValueError,match='invalidated'):
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):pytest.fail('Poisoned handle accepted')
    assert files(source)==saved


@pytest.mark.parametrize('defect',['other-directory','other-pin','budget','forged','overlap'])
def test_substituted_or_overlapping_read_refuses(tmp_path,defect):
    _,source,archive,record=packed(tmp_path)
    other=tmp_path/'other';shutil.copytree(archive,other)
    with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
        options=dict(retained_parent=retained);directory=archive;digest=record['manifest_sha256']
        if defect=='other-directory':directory=other
        elif defect=='other-pin':digest='0'*64
        elif defect=='budget':options['max_disk_bytes']=1
        elif defect=='forged':options['retained_parent']=object()
        if defect=='overlap':
            with m.read_parent_inputs(archive,digest,retained_parent=retained):
                with pytest.raises(ValueError):
                    with m.read_parent_inputs(directory,digest,**options):pytest.fail('Overlapping lease accepted')
        else:
            with pytest.raises(ValueError):
                with m.read_parent_inputs(directory,digest,**options):pytest.fail('Substitution accepted')


@pytest.mark.parametrize('interrupt',[KeyboardInterrupt,RuntimeError])
def test_interruption_releases_owned_snapshot_preserves_original(tmp_path,interrupt):
    _,source,archive,record=packed(tmp_path)
    saved=files(source);transport=files(archive)
    with pytest.raises(interrupt):
        with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained) as (root,report):
                raise interrupt('consumer stopped')
    assert not root.exists() and report['read_scope_closed'] and report['inputs_unchanged']
    assert report['consumer_completed'] is False
    assert files(source)==saved and files(archive)==transport
    with m.retained_parent_inputs(archive,record['manifest_sha256']):pass


def test_late_change_refuses_return_and_removes_owned_snapshot(tmp_path):
    _,source,archive,record=packed(tmp_path);saved=files(source);transport=files(archive)
    with pytest.raises(ValueError,match='snapshot changed'):
        with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained) as (root,report):
                p=root/'dataset/model.pdb';p.chmod(0o600);p.write_bytes(b'changed')
    assert not root.exists() and not report['inputs_unchanged']
    assert files(source)==saved and files(archive)==transport


def test_derivation_uses_same_snapshot_but_replays_science_for_each_request(tmp_path,monkeypatch):
    from nasolve.metal import child_inputs
    values=prepared_case(tmp_path,monkeypatch);_,archive,prepared,request=values
    saved=files(archive);raw=files(prepared)
    with patch.object(child_inputs,'read_registry',wraps=child_inputs.read_registry) as registry:
        with m.retained_parent_inputs(archive,request['parent_manifest_sha256']) as retained:
            first=verify(values,retained_parent=retained)
            second=verify(values,retained_parent=retained)
            assert registry.call_count==2
            assert first==second and first['schema_version']==2
            assert first['parent_transport']['kind']=='metal-parent-input-read'
            assert first['derivation_verified'] and not first['reuse_authorized']
            (prepared/'parameters.phil').write_bytes(raw['parameters.phil']+b'changed')
            from nasolve.metal.child_process import make_request
            substituted=make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
            with pytest.raises(ValueError,match='derivation'):
                verify((values[0],archive,prepared,substituted),retained_parent=retained)
            assert registry.call_count==3
    assert files(archive)==saved


def test_handle_is_context_local_and_interrupted_reader_cannot_resume(tmp_path):
    _,source,archive,record=packed(tmp_path)
    with m.retained_parent_inputs(archive,record['manifest_sha256']) as retained:
        def foreign_read():
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):
                pytest.fail('Read escaped its owning context')
        with pytest.raises(ValueError,match='active retained'):Context().run(foreign_read)
        with pytest.raises(RuntimeError,match='interrupted'):
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):
                raise RuntimeError('interrupted')
        with pytest.raises(ValueError,match='invalidated'):
            with m.read_parent_inputs(archive,record['manifest_sha256'],retained_parent=retained):
                pytest.fail('Interrupted handle continued')
