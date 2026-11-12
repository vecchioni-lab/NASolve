"""Compact storage preserves scientific evidence; it does not qualify it."""
from hashlib import sha256
import io,json,shutil,stat,zipfile
from pathlib import Path
from unittest.mock import patch
import pytest


def source(tmp_path):
    root=tmp_path/'source';root.mkdir()
    data=b'An exact repeated native inventory.\n'*10000
    for name in ('a/report.json','b/report.json','b/worker.py'):
        p=root/name;p.parent.mkdir(exist_ok=True);p.write_bytes(data if name.endswith('json') else b'raise AssertionError("never execute evidence")\n')
    (root/'empty').mkdir()
    return root


def rewrite(path,change):
    from nasolve.cif_mixed_runtime_source import archive_members
    members=archive_members(path.read_bytes(),sha256(path.read_bytes()).hexdigest())
    index=json.loads(members['index.json']);change(index,members)
    members['index.json']=(json.dumps(index,sort_keys=True)+'\n').encode()
    members['manifest.json']=(json.dumps({k:dict(sha256=sha256(v).hexdigest(),bytes=len(v)) for k,v in members.items() if k!='manifest.json'},sort_keys=True)+'\n').encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,value in sorted(members.items()):z.writestr(name,value)


def test_exact_deduplicated_bytes_replay_without_original_tree_or_execution(tmp_path):
    from nasolve import cif_runtime_evidence as m
    original=source(tmp_path);files={p.relative_to(original).as_posix():p.read_bytes() for p in original.rglob('*') if p.is_file()}
    out=tmp_path/'evidence.zip';q=m.pack_runtime_evidence(original,out)
    assert q['logical_files']==3 and q['unique_files']==2
    assert out.stat().st_size < sum(map(len,files.values()))/100
    second=tmp_path/'again.zip';m.pack_runtime_evidence(original,second)
    assert second.read_bytes()==out.read_bytes()
    shutil.rmtree(original)
    with patch('subprocess.Popen',side_effect=AssertionError('No execution')):
        with m.expanded_runtime_evidence(out,sha256(out.read_bytes()).hexdigest()) as view:
            temporary=view;root=view/'evidence'
            assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==files
            assert (root/'empty').is_dir()
            assert (root/'a/report.json').stat().st_ino==(root/'b/report.json').stat().st_ino
    assert not temporary.exists()


@pytest.mark.parametrize('defect',['escape','absolute','case_alias','directory_alias','file_parent','wrong_size','bool_size','wrong_hash','unused_object','missing_object','unknown_policy','oversized_logical','wrong_digest'])
def test_rehashed_archive_cannot_bypass_paths_objects_or_expansion_bounds(tmp_path,defect):
    from nasolve import cif_runtime_evidence as m
    out=tmp_path/'evidence.zip';m.pack_runtime_evidence(source(tmp_path),out)
    def change(index,members):
        files=index['files'];key='a/report.json';ref=files[key]
        if defect=='escape':files['../escaped']=files.pop(key)
        if defect=='absolute':files['/escaped']=files.pop(key)
        if defect=='case_alias':files['A/REPORT.json']=dict(ref)
        if defect=='directory_alias':index['directories'].append('A')
        if defect=='file_parent':files['a']=dict(ref)
        if defect=='wrong_size':ref['size']+=1
        if defect=='bool_size':ref['size']=True
        if defect=='wrong_hash':ref['sha256']='0'*64
        if defect=='unused_object':members['objects/'+sha256(b'extra').hexdigest()]=b'extra'
        if defect=='missing_object':members.pop('objects/'+ref['sha256'])
        if defect=='unknown_policy':index['policy_id']='unknown'
        if defect=='oversized_logical':
            for i in range(500):files[f'copy-{i:03d}']=dict(ref)
    rewrite(out,change)
    digest='0'*64 if defect=='wrong_digest' else sha256(out.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        with m.expanded_runtime_evidence(out,digest):pytest.fail('Invalid evidence was expanded')


def test_nested_expansion_shares_one_temporary_allowance(tmp_path,monkeypatch):
    from nasolve import cif_runtime_evidence as m
    original=source(tmp_path);out=tmp_path/'evidence.zip';q=m.pack_runtime_evidence(original,out)
    (original/'a/report.json').write_bytes(b'different inventory '*20000)
    second=tmp_path/'different.zip';m.pack_runtime_evidence(original,second)
    monkeypatch.setattr(m,'MAX_ACTIVE_BYTES',q['unique_bytes'])
    digest=sha256(out.read_bytes()).hexdigest()
    with m.expanded_runtime_evidence(out,digest) as first:
        # Exact contents consume no second physical copy while both views live.
        with m.expanded_runtime_evidence(out,digest) as same:
            assert (first/'evidence/a/report.json').stat().st_ino==(same/'evidence/a/report.json').stat().st_ino
        with pytest.raises(ValueError,match='temporary'):
            with m.expanded_runtime_evidence(second,sha256(second.read_bytes()).hexdigest()):pytest.fail('New data exceeded allowance')
        assert first.exists()
    with m.expanded_runtime_evidence(out,digest) as after:assert after.exists()


def test_temporary_copy_fallback_and_exception_cleanup(tmp_path,monkeypatch):
    from nasolve import cif_runtime_evidence as m
    out=tmp_path/'evidence.zip';m.pack_runtime_evidence(source(tmp_path),out)
    monkeypatch.setattr(m.os,'link',lambda *a,**k:(_ for _ in ()).throw(OSError('hard links unavailable')))
    with pytest.raises(RuntimeError,match='caller'):
        with m.expanded_runtime_evidence(out,sha256(out.read_bytes()).hexdigest()) as root:
            temporary=root;assert (root/'evidence/a/report.json').read_bytes()==(root/'evidence/b/report.json').read_bytes()
            raise RuntimeError('caller')
    assert not temporary.exists()


@pytest.mark.parametrize('composed,fallback',[(False,False),(True,False),(True,True)])
def test_compact_publication_replays_same_selection_and_direct_resources(tmp_path,monkeypatch,composed,fallback):
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    if composed:
        from tests.test_cif_repair_chain import fixture,compose
        chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
        args.update(attribution_directory=compose(chain,root,plane),repair_chain=True)
    else:
        from tests.test_cif_dictionary_bundle_repair import fixture
        selector,root,args,state=fixture(tmp_path,monkeypatch)
    if fallback:(root/'repaired/captured_mixed_gradients.json').write_text(json.dumps(dict(status='REVIEW')))
    out=tmp_path/'compact'
    q=runtime.prepare_repaired_component_runtime_bundle(**args,output=out,compact_evidence=True)
    assert q['schema_version']==2 and q['evidence_storage']['policy_id']=='cif-content-addressed-runtime-evidence-v1'
    assert (out/'evidence.zip').is_file() and not (out/'evidence').exists()
    expected=resolve_runtime_bundle(out)
    selected={k:[p.read_bytes() for p in expected[k]] for k in ('dictionaries','phils')}
    shutil.rmtree(root);out=out.rename(tmp_path/'relocated')
    before={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No execution during replay')):
        r=resolve_runtime_bundle(out)
        assert {k:[p.read_bytes() for p in r[k]] for k in selected}==selected
        assert all(p.is_relative_to(out) for k in selected for p in r[k])
    assert before=={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    assert r['manifest']['decision']['selected']==('verified_prepared_bundle' if fallback else 'repaired_prepared_bundle')


@pytest.mark.parametrize('defect',['archive','unpacked_twin','schema','storage_policy','claim','resource','rehashed_bad_proof'])
def test_compact_runtime_does_not_weaken_scientific_or_resource_replay(tmp_path,monkeypatch,defect):
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle,_reference
    from tests.test_cif_dictionary_bundle_repair import fixture
    selector,root,args,state=fixture(tmp_path,monkeypatch);out=tmp_path/'compact'
    q=runtime.prepare_repaired_component_runtime_bundle(**args,output=out,compact_evidence=True)
    if defect=='archive':(out/'evidence.zip').write_bytes(b'corrupted')
    if defect=='unpacked_twin':(out/'evidence').mkdir()
    if defect=='schema':q['schema_version']=1
    if defect=='storage_policy':q['evidence_storage']['policy_id']='unknown'
    if defect=='claim':q['automatic_adoption']=True
    if defect=='resource':(out/q['resources']['dictionaries'][0]['relative_path']).write_text('changed')
    if defect=='rehashed_bad_proof':
        def change(index,members):
            key='repaired-gradient/captured_mixed_gradients.json';old=index['files'][key]['sha256']
            payload=b'{"status":"REVIEW"}';new=sha256(payload).hexdigest()
            index['files'][key]=dict(sha256=new,size=len(payload));members['objects/'+new]=payload
            if not any(r['sha256']==old for r in index['files'].values()):members.pop('objects/'+old)
        rewrite(out/'evidence.zip',change)
        ref=_reference(out/'evidence.zip',out);q['evidence_storage']['archive']=ref
        q['files']=[ref if r['relative_path']=='evidence.zip' else r for r in q['files']]
    (out/'runtime_bundle.json').write_text(json.dumps(q))
    with pytest.raises(ValueError):resolve_runtime_bundle(out)


def test_readyset_reads_source_from_temporary_view_but_keeps_public_selected_paths(tmp_path,monkeypatch):
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_runtime_readyset import _selected_view,_parent
    from nasolve.cif_runtime_continuation import _selected_consumer
    from tests.test_cif_runtime_readyset import parent_case
    publish=runtime.prepare_repaired_component_runtime_bundle
    monkeypatch.setattr(runtime,'prepare_repaired_component_runtime_bundle',lambda *a,**k:publish(*a,**k,compact_evidence=True))
    parent,sdk=parent_case(tmp_path,monkeypatch,single=True)
    assert not (parent/'evidence').exists()
    with _selected_view(parent) as (selected,view):
        source_path=view['source'];assert source_path.is_file()
        assert all(p.is_relative_to(parent) for p in view['after_dictionaries'])
        assert view['model']==selected['model']
        consumer=view['report']['consumer']
    assert not source_path.exists()
    assert _selected_consumer(_parent(parent))==consumer


@pytest.mark.parametrize('fallback',[False,True])
def test_owned_continuation_keeps_compact_parent_and_output_through_cold_replay(tmp_path,monkeypatch,request,fallback):
    from nasolve import cif_component_runtime as runtime
    from tests.test_cif_runtime_continuation import continuation
    publish=runtime.prepare_repaired_component_runtime_bundle
    monkeypatch.setattr(runtime,'prepare_repaired_component_runtime_bundle',lambda *a,**k:publish(*a,**k,compact_evidence=True))
    m,parent,sdk,out,state=continuation.__wrapped__(tmp_path,monkeypatch,request)
    if fallback:state['fail']='endpoint'
    result=m.execute_runtime_continuation(parent,sdk,out,compact_evidence=True)
    assert result['configuration']['compact_evidence'] is True
    assert not (out/'runtime/evidence').exists() and not (out/'inputs/runtime/evidence').exists()
    expected='verified_parent_runtime' if fallback else 'readyset_checked_model'
    assert result['selected']==expected
    shutil.rmtree(parent);shutil.rmtree(sdk.root);moved=out.rename(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('Cold continuation must not execute')):
        replay=m.read_runtime_continuation(moved)
    assert replay['report']==result and replay['runtime']['manifest']['schema_version']==2
    assert replay['process_evidence']['state']=='STOPPED'


@pytest.mark.parametrize('value',[1,'yes',None])
def test_nonboolean_compact_choice_cannot_create_output(tmp_path,monkeypatch,value):
    from nasolve import cif_component_runtime as runtime
    from tests.test_cif_dictionary_bundle_repair import fixture
    _,_,args,_=fixture(tmp_path,monkeypatch);out=tmp_path/'bad'
    with pytest.raises(ValueError):runtime.prepare_repaired_component_runtime_bundle(**args,output=out,compact_evidence=value)
    assert not out.exists()


def test_platform_copy_fallback_still_obeys_the_physical_limit(tmp_path,monkeypatch):
    from nasolve import cif_runtime_evidence as m
    out=tmp_path/'evidence.zip';q=m.pack_runtime_evidence(source(tmp_path),out)
    monkeypatch.setattr(m,'MAX_ACTIVE_BYTES',q['unique_bytes'])
    monkeypatch.setattr(m.os,'link',lambda *a,**k:(_ for _ in ()).throw(OSError('hard links unavailable')))
    with pytest.raises(ValueError,match='temporary'):
        with m.expanded_runtime_evidence(out,sha256(out.read_bytes()).hexdigest()):pytest.fail('Copies exceeded bound')
    assert m._ACTIVE_BYTES.get()==0 and m._ACTIVE_OBJECTS.get() is None


def test_two_layer_storage_does_not_allow_unbounded_nested_views(tmp_path):
    from nasolve import cif_runtime_evidence as m
    out=tmp_path/'evidence.zip';m.pack_runtime_evidence(source(tmp_path),out)
    digest=sha256(out.read_bytes()).hexdigest()
    with m.expanded_runtime_evidence(out,digest):
        with m.expanded_runtime_evidence(out,digest):
            with pytest.raises(ValueError,match='depth'):
                with m.expanded_runtime_evidence(out,digest):pytest.fail('Unbounded nested archive')
    assert m._ACTIVE_DEPTH.get()==0
