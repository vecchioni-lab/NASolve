"""Crystal incoming ends remain explicit image edges at preparation intake."""
from copy import deepcopy
import json

import pytest
pytest.importorskip('gemmi')

from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb, file_sha256
from nasolve.cif_model_context import derive_prepared_model_context, validate_prepared_model_context
from .test_construct_registration import target
from .test_cif_model_context import model, report


def case(root, *, terminal=False):
    root.mkdir(exist_ok=True)
    source = model(root/'source.pdb', chains=(('A','DC'),('B','DA')))
    raw = ''.join(line for line in source.read_text().splitlines(keepends=True)
                  if not (line[12:16].strip() == 'OP3' and line[22:26].strip() == '1'
                          and not (terminal and line[21]=='A')))
    source.write_text('CRYST1   12.000  100.000  100.000  90.00  90.00  90.00 P 1           1\n'+raw)
    sites = [('L:1','DC'),('L:9','DC'),('K:1','DA'),('K:9','DA')]
    reg = root/'registration.json'
    reg.write_text(json.dumps(build_construct_registration(inspect_pdb(source), target(*sites),
        {'source': {'L:1':'A:1','L:9':'A:9','K:1':'B:1','K:9':'B:9'}}, source='test two strands')))
    discovery = root/'discovery.json'
    discovery.write_text(json.dumps(dict(schema_version=1,kind='topostitch-end-discovery-input',
        model_sha256=file_sha256(source),registration_sha256=file_sha256(reg),copy_id='source',
        strands=[dict(strand_id=s,sites=ss,five_prime_boundary='representation',three_prime_boundary='representation')
                 for s,ss in [('a',['L:1','L:9']),('b',['K:1','K:9'])]],
        duplex_pairs=[],protected_sites=[],do_not_connect_sites=[],pairing_inventory_complete=False)))
    edges = root/'edges.json'
    edges.write_text(json.dumps([dict(continuation_id=i,source_site=a,target_site=b,target_operator_xyz='x+1,y,z')
                                for i,a,b in [(1,'L:9','L:1'),(2,'K:9','K:1')]]))
    return dict(model=source, report=report('A:1') if terminal else report(), components=['DA','DC'], registration_model=source,
                registration=reg,discovery=discovery,continuations=edges)


def derive(args):
    from nasolve.cif_registered_preparation_context import derive_registered_preparation_context
    return derive_registered_preparation_context(**args)


def snapshot(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_two_image_links_are_not_free_ends_or_same_image_bonds(tmp_path):
    args=case(tmp_path); before=snapshot(tmp_path); original=deepcopy(args['report'])
    with pytest.raises(ValueError,match='B:1|A:1'):
        derive_prepared_model_context(args['model'],args['report'],args['components'])
    result=derive(args)
    assert result['local_links']==[['A:1','A:9'],['B:1','B:9']]
    assert [(r['o3_site'],r['phosphate_site'],r['o3_image'],r['target_operator_xyz'])
            for r in result['image_links']]==[('A:9','A:1','x-1,y,z','x+1,y,z'),('B:9','B:1','x-1,y,z','x+1,y,z')]
    for code,chain in [('DC','A'),('DA','B')]:
        first,last=result['site_contexts'][code]
        assert first['incoming']==dict(site=chain+':9',relation='registered_image',operator_xyz='x-1,y,z',continuation_id=1 if chain=='A' else 2)
        assert first['outgoing']==dict(site=chain+':9',relation='local',operator_xyz='x,y,z')
        assert last['outgoing']['operator_xyz']=='x+1,y,z'
        assert first['five_prime_state']==last['three_prime_state']=='linked'
    assert 'expected_links' not in result and 'contexts' not in result
    assert result['native_qualification']=='NOT_RUN' and result['ordinary_admission'] is False
    with pytest.raises(ValueError,match='Unsupported'):
        validate_prepared_model_context(args['model'],result)
    assert snapshot(tmp_path)==before and args['report']==original


def test_missing_registered_partner_does_not_become_a_terminal(tmp_path):
    args=case(tmp_path);p=args['continuations'];p.write_text(json.dumps(json.loads(p.read_text())[:1]))
    with pytest.raises(ValueError,match='lack a registered partner.*B:1'):derive(args)


def test_declared_terminal_conflicts_with_registered_incoming(tmp_path):
    args=case(tmp_path,terminal=True)
    with pytest.raises(ValueError,match='protected terminal'):derive(args)


def test_source_hash_and_explicit_crystal_frame_cannot_be_redirected(tmp_path):
    args=case(tmp_path);args['registration_model'].write_bytes(args['registration_model'].read_bytes()+b'\n')
    with pytest.raises(ValueError):derive(args)


def test_descendant_preserves_named_image_without_claiming_construction(tmp_path):
    args=case(tmp_path);child=tmp_path/'child.pdb'
    text=args['model'].read_text();child.write_text(text.replace('   5.000','   5.010'))
    args['model']=child
    result=derive(args)
    assert result['source_model_sha256']!=result['model_sha256']
    assert all(r['frame_transfer']['child_model_sha256']==result['model_sha256'] for r in result['image_links'])
    assert result['ordinary_admission'] is False
    child.write_text(child.read_text().replace(' 100.000',' 101.000',1))
    with pytest.raises(ValueError,match='same crystal'):derive(args)


def test_input_change_during_registered_read_refuses(tmp_path,monkeypatch):
    from nasolve import cif_registered_preparation_context as owner
    args=case(tmp_path);original=owner.inspect_registered_backbone
    def changed(*a,**kw):
        rows=original(*a,**kw);args['continuations'].write_bytes(args['continuations'].read_bytes()+b'\n');return rows
    monkeypatch.setattr(owner,'inspect_registered_backbone',changed)
    with pytest.raises(ValueError,match='changed'):derive(args)


def test_relocating_all_declared_inputs_keeps_same_context(tmp_path):
    old=tmp_path/'original';args=case(old);expected=derive(args)
    new=old.rename(tmp_path/'moved')
    for key in ('model','registration_model','registration','discovery','continuations'):
        args[key]=new/args[key].relative_to(old)
    assert not old.exists() and derive(args)==expected
    assert str(tmp_path) not in json.dumps(expected)


def test_one_oxygen_cannot_satisfy_two_incoming_ends(tmp_path):
    args=case(tmp_path);p=args['continuations'];edges=json.loads(p.read_text())
    edges[1]['source_site']='L:9';p.write_text(json.dumps(edges))
    with pytest.raises(ValueError):derive(args)
