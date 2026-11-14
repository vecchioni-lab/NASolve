"""Deep archive names never become long physical paths on a consumer host."""
from hashlib import sha256
from pathlib import Path
import errno,json,shutil
import pytest
import nasolve.cif_review_transport as transport


def limit_paths(monkeypatch,budget=1024):
    original=Path.stat
    seen=[]
    def limited(path,*args,**kwargs):
        size=len(str(path.absolute()).encode());seen.append(size)
        if size>=budget:raise OSError(63,'File name too long',str(path))
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'stat',limited)
    return seen


def test_deep_names_roundtrip_under_mac_path_limit(tmp_path,monkeypatch):
    logical='inputs/review/'*90+'native/inputs/000_model.pdb'
    members={'manifest.json':b'ORIGINAL MANIFEST',logical:b'EXACT SCIENTIFIC BYTES'}
    seen=limit_paths(monkeypatch);session=tmp_path/'session';target=session/'inputs/review'
    mapping=transport.stage_review_members(members,target,indexed=True)
    assert max(seen)<1024 and all(len(v)<120 for v in mapping.values())
    assert transport.read_staged_review_member(target,logical)==members[logical]
    assert transport.staged_review_members_match(members,target)
    assert transport.review_archive_files(session,session/'out.zip')=={'inputs/review/'+n:d for n,d in members.items()}
    moved=tmp_path/'relocated/session';shutil.copytree(session,moved);shutil.rmtree(session)
    assert transport.staged_review_members_match(members,moved/'inputs/review')
    for _ in range(3):
        members={'inputs/review/'+n:d for n,d in members.items()}
        current=tmp_path/('copy'+str(_));transport.stage_review_members(members,current/'inputs/review',indexed=True)
        assert transport.review_archive_files(current,current/'out.zip')=={'inputs/review/'+n:d for n,d in members.items()}


@pytest.mark.parametrize('logical',['x'*300+'.cif','inputs/review/'*100+'a.json','native/'+'\u00e9'*150+'.pdb'])
def test_indexed_transport_bounds_component_and_full_path_bytes(tmp_path,logical):
    data=b'OPAQUE TRANSPORT; NEVER EXECUTED';members={logical:data}
    mapping=transport.stage_review_members(members,tmp_path/'staged',indexed=True)
    assert all(len(part.encode())<255 for part in Path(mapping[logical]).parts)
    assert transport.read_staged_review_member(tmp_path/'staged',logical)==data


@pytest.mark.parametrize('defect',['hash','size','physical','policy','missing','extra','symlink','shadow','logical'])
def test_indexed_bindings_cannot_hide_mutations(tmp_path,defect):
    target=tmp_path/'session/inputs/review';members={'inputs/review/'*90+'a.cif':b'SOURCE'}
    mapping=transport.stage_review_members(members,target,indexed=True);name=next(iter(members))
    index=target/'.review-transport/index.json';value=json.loads(index.read_bytes());row=value['members'][name]
    if defect=='hash':row['sha256']='0'*64
    if defect=='size':row['size']+=1
    if defect=='physical':row['physical']='../outside'
    if defect=='policy':value['policy_id']='OTHER'
    if defect=='missing':(target/mapping[name]).unlink()
    if defect=='extra':(target/'.review-transport/objects/extra.bin').write_bytes(b'extra')
    if defect=='symlink':
        p=target/mapping[name];p.unlink();p.symlink_to(tmp_path/'outside')
    if defect=='shadow':(target/'shadow.cif').write_bytes(b'extra')
    if defect=='logical':value['members']['../escape.cif']=value['members'].pop(name)
    index.write_text(json.dumps(value))
    assert not transport.staged_review_members_match(members,target)
    with pytest.raises((ValueError,OSError)):transport.review_archive_files(tmp_path/'session',tmp_path/'session/out.zip')


def test_preservation_check_reports_partial_stage_instead_of_repeating_path_error(tmp_path,monkeypatch):
    logical='inputs/review/'*90+'a.cif';members={logical:b'FROZEN'};target=tmp_path/'partial';target.mkdir()
    limit_paths(monkeypatch)
    assert transport.staged_review_members_match(members,target) is False


def test_indexed_full_check_reads_each_payload_once(tmp_path,monkeypatch):
    members={f'inputs/review/{i}/a.cif':str(i).encode() for i in range(40)}
    target=tmp_path/'staged';transport.stage_review_members(members,target,indexed=True)
    original=transport._read;seen=[]
    def read(root,relative,**kwargs):seen.append(relative);return original(root,relative,**kwargs)
    monkeypatch.setattr(transport,'_read',read)
    assert transport.staged_review_members_match(members,target)
    assert len([p for p in seen if '/objects/' in p])==len(members)
