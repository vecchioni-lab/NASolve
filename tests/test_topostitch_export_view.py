"""A saved-export view must not weaken its producer binding or imply new science."""
import json,re,shutil
from hashlib import sha256
from pathlib import Path
import pytest
from tests.test_topostitch_cif_export import fixture,write


def packet(tmp_path):
    root,original,kw,_,_=fixture(tmp_path);out=tmp_path/'packet';write(root,original,out,kw)
    return out,kw,sha256((out/'export.json').read_bytes()).hexdigest()


def view(packet,out,kw,digest):
    from nasolve.topostitch_view import write_export_view
    return write_export_view(packet,out,expected_receipt_sha256=digest,cedar_source=kw['cedar_source'])


def test_relocated_export_view_preserves_working_coordinates_and_trusted_identity(tmp_path):
    from nasolve.topostitch_view import representative_scene,main
    old=tmp_path/'old';old.mkdir();root,kw,digest=packet(old)
    moved=tmp_path/'moved';moved.mkdir();shutil.move(root,moved/'packet');shutil.copytree(kw['cedar_source'],moved/'cedar');shutil.rmtree(old)
    root=moved/'packet';kw['cedar_source']=moved/'cedar';before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    output=tmp_path/'view.html';scene=view(root,output,kw,digest)
    assert scene['atoms']==representative_scene(root/'preview')['atoms']
    detail=scene['verified_export'];assert detail['receipt_sha256']==digest
    assert detail['display_coordinates']=='saved_working_preview'
    assert detail['output']['sha256']==sha256((root/'representative.cif').read_bytes()).hexdigest()
    assert not scene['runtime_authority'] and not detail['native_restart_qualified']
    text=output.read_text();embedded=re.search(r'<script id="scene" type="application/json">(.*?)</script>',text,re.S)
    assert json.loads(embedded.group(1))==scene and str(tmp_path) not in text
    assert 'Saved CIF verified' in text and 'saved preview coordinates' in text
    assert main([str(root),'--out',str(tmp_path/'cli.html'),'--export-sha256',digest,'--cedar-source',str(kw['cedar_source'])])==0
    assert before=={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_changed_receipt_or_artifact_never_produces_view(tmp_path):
    root,kw,digest=packet(tmp_path);out=tmp_path/'view.html'
    with pytest.raises(ValueError,match='receipt differs'):view(root,out,kw,'0'*64)
    assert not out.exists()
    p=root/'representative.cif';p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='changed whole-asym'):view(root,out,kw,digest)
    assert not out.exists()


def test_export_view_refuses_frozen_or_existing_destinations(tmp_path):
    root,kw,digest=packet(tmp_path)
    with pytest.raises(ValueError,match='outside'):view(root,root/'view.html',kw,digest)
    out=tmp_path/'existing';out.write_text('keep')
    with pytest.raises(FileExistsError):view(root,out,kw,digest)
    assert out.read_text()=='keep'


def test_scene_construction_drift_refuses_view(tmp_path,monkeypatch):
    import nasolve.topostitch_view as module
    root,kw,digest=packet(tmp_path);scene=module.representative_scene
    def drift(*args,**kwargs):
        result=scene(*args,**kwargs);p=root/'coverage.json';p.write_bytes(p.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'representative_scene',drift)
    out=tmp_path/'view.html'
    with pytest.raises(ValueError,match='changed during'):view(root,out,kw,digest)
    assert not out.exists()


def test_export_cli_rejects_mixed_or_missing_bindings(tmp_path):
    from nasolve.topostitch_view import main
    for extra in [[],['--cedar-source',str(tmp_path),'--periodic']]:
        with pytest.raises(SystemExit) as exc:main([str(tmp_path),'--out',str(tmp_path/'x.html'),'--export-sha256','0'*64,*extra])
        assert exc.value.code==2 and not (tmp_path/'x.html').exists()
