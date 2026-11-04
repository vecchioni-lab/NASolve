from pathlib import Path
import json
import pytest


def atom(serial,name,x=1.,residue=1):
    return f'ATOM  {serial:5d} {name:^4s} 0DG A{residue:4d}    {x:8.3f}{2.:8.3f}{3.:8.3f}{1.:6.2f}{20.:6.2f}          {name[0]:>2s}  \n'


def inputs(tmp_path):
    ref=tmp_path/'reference.pdb';raw=tmp_path/'raw.pdb'
    ref.write_text(atom(3,'C1')+atom(9,'O1')+'TER\nEND\n')
    raw.write_text(atom(1,'O1')+atom(2,'C1')+'TER\nEND\n')
    return ref,raw


def prepare(ref,raw,out):
    from nasolve.cif_readyset_atom_order import prepare_readyset_atom_order
    return prepare_readyset_atom_order(ref,raw,out)


def test_reorders_only_serialization_and_replays_without_originals(tmp_path):
    from nasolve.cif_readyset_atom_order import read_readyset_atom_order
    ref,raw=inputs(tmp_path);expected=ref.read_bytes();original=raw.read_bytes()
    r=prepare(ref,raw,tmp_path/'order');assert r['changed'] and not r['automatic_adoption']
    assert (tmp_path/'order/model.pdb').read_bytes()==expected and raw.read_bytes()==original
    ref.unlink();raw.unlink();(tmp_path/'order').rename(tmp_path/'moved')
    result=read_readyset_atom_order(tmp_path/'moved')
    assert result['model'].read_bytes()==expected and result['report']==r


@pytest.mark.parametrize('defect',['coordinate','occupancy','bfactor','element','charge','missing','extra','duplicate','hydrogen','nan','anisou','conect','model','ter','residue_order','metadata','serial','altloc'])
def test_unsupported_or_scientific_changes_refuse(tmp_path,defect):
    ref,raw=inputs(tmp_path);s=raw.read_text();line=s.splitlines(keepends=True)[0]
    offsets={'coordinate':(30,38,'   1.001'),'occupancy':(54,60,'  0.50'),'bfactor':(60,66,' 21.00'),
        'element':(76,78,' N'),'charge':(78,80,'1+'),'nan':(30,38,'     nan'),'altloc':(16,17,'B')}
    if defect in offsets:
        a,b,v=offsets[defect];s=line[:a]+v+line[b:]+s[len(line):]
    elif defect=='missing':s=s[len(line):]
    elif defect=='extra':s=atom(10,'N1')+s
    elif defect=='duplicate':s=atom(10,'O1')+s
    elif defect=='hydrogen':s=atom(10,'H1')+s;ref.write_text(atom(10,'H1')+ref.read_text())
    elif defect in ['anisou','conect','model']:s=defect.upper().ljust(6)+'\n'+s
    elif defect=='ter':s=s.replace('TER\n','')
    elif defect=='residue_order':s=atom(1,'O1',residue=2)+atom(2,'C1')+'TER\nEND\n';ref.write_text(atom(3,'C1')+atom(9,'O1',residue=2)+'TER\nEND\n')
    elif defect=='metadata':s='CRYST1 changed\n'+s
    elif defect=='serial':s=s.replace('ATOM      2','ATOM      1')
    raw.write_text(s)
    with pytest.raises(ValueError):prepare(ref,raw,tmp_path/'order')
    assert not (tmp_path/'order').exists()


@pytest.mark.parametrize('defect',['output','reference','candidate','receipt','extra','symlink'])
def test_frozen_receipt_is_rederived_not_trusted(tmp_path,defect):
    from nasolve.cif_readyset_atom_order import read_readyset_atom_order
    ref,raw=inputs(tmp_path);prepare(ref,raw,tmp_path/'order');root=tmp_path/'order'
    if defect in ['output','reference','candidate']:
        p=root/{'output':'model.pdb','reference':'reference.pdb','candidate':'readyset.pdb'}[defect];p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='receipt':
        p=root/'atom_order.json';r=json.loads(p.read_text());r['changed']=False;p.write_text(json.dumps(r))
    elif defect=='extra':(root/'undeclared').write_text('extra')
    elif defect=='symlink':(root/'model.pdb').unlink();(root/'model.pdb').symlink_to(ref)
    with pytest.raises(ValueError):read_readyset_atom_order(root)


def test_fresh_destination_and_source_paths_are_preserved(tmp_path):
    ref,raw=inputs(tmp_path);prepare(ref,raw,tmp_path/'order')
    with pytest.raises(ValueError):prepare(ref,raw,tmp_path/'order')
    link=tmp_path/'link';link.symlink_to(raw)
    with pytest.raises(ValueError):prepare(ref,link,tmp_path/'other')


def test_existing_strict_inspector_binds_optional_order_receipt(tmp_path,monkeypatch):
    from tests.test_cif_dictionary_bundle_readyset import control
    from nasolve.cif_dictionary_bundle_readyset import readyset_endpoint_inputs
    b,_=control(tmp_path,monkeypatch)
    initial=readyset_endpoint_inputs(tmp_path/'bundle',tmp_path/'readyset')
    prepare(b['model'],initial['model'],tmp_path/'order')
    result=readyset_endpoint_inputs(tmp_path/'bundle',tmp_path/'readyset',atom_order_directory=tmp_path/'order')
    assert result['model']==tmp_path/'order/model.pdb'
    assert result['dictionaries']==initial['dictionaries'] and result['phils']==initial['phils']
    other=tmp_path/'other';other.mkdir();ref,raw=inputs(other);prepare(ref,raw,other/'order')
    with pytest.raises(ValueError):readyset_endpoint_inputs(tmp_path/'bundle',tmp_path/'readyset',atom_order_directory=other/'order')


def test_unchecked_serialization_cannot_bypass_missing_native_capture(tmp_path,monkeypatch):
    from tests.test_cif_dictionary_bundle_readyset import control,initial
    from nasolve.cif_dictionary_bundle_readyset import readyset_endpoint_inputs,inspect_dictionary_bundle_readyset,ATOM_ORDER_POLICY_ID
    b,_=control(tmp_path,monkeypatch)
    endpoint=readyset_endpoint_inputs(tmp_path/'bundle',tmp_path/'readyset')
    prepare(b['model'],endpoint['model'],tmp_path/'order')
    monkeypatch.setattr('nasolve.cif_dictionary_bundle_readyset.inspect_dictionary_bundle_native',lambda *a:initial(True))
    review=inspect_dictionary_bundle_readyset(tmp_path/'bundle',tmp_path/'before',tmp_path/'after',tmp_path/'readyset',atom_order_directory=tmp_path/'order')
    assert review['policy_id']==ATOM_ORDER_POLICY_ID
    assert review['decision']['selected']=='verified_prepared_model' and 'missing' in review['endpoint_error']


@pytest.mark.parametrize('defect',['source_charge','source_occupancy','boundary'])
def test_rehashing_false_derivation_does_not_establish_equivalence(tmp_path,defect):
    from hashlib import sha256
    from nasolve.cif_readyset_atom_order import read_readyset_atom_order
    ref,raw=inputs(tmp_path);prepare(ref,raw,tmp_path/'order');root=tmp_path/'order'
    p=root/'readyset.pdb';s=p.read_text()
    if defect=='source_charge':s=s[:78]+'1+'+s[80:]
    elif defect=='source_occupancy':s=s[:54]+'  0.50'+s[60:]
    else:s=s.replace('TER\n','')
    p.write_text(s);r=json.loads((root/'atom_order.json').read_text())
    r['artifacts']['readyset.pdb'].update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
    (root/'atom_order.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):read_readyset_atom_order(root)
