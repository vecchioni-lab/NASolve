"""Graph-bound furanose seed kinematics; synthetic poses are not refinement proof."""
from pathlib import Path
import json
from unittest.mock import patch
import pytest
from tests.test_cif_base_anchored_furanose import inputs,run
from tests.test_cif_catalogue import snapshot


def control(tmp_path, *, bridged=False, rename=False, hand='D'):
    from nasolve.cif_stereochemistry_audit import _values,_coordinates
    paths,c=inputs(tmp_path,bridged=bridged,rename=rename,hand=hand)
    _,xyz=_coordinates(_values(paths[1],'Z99'),source=False)
    virtual=xyz[c['ports']['phosphate']['leaving_atom']]
    lines=paths[4].read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[:6]!='ATOM  ':continue
        if line[21:26]=='A  11':line=line[:46]+f'{-float(line[46:54]):8.3f}'+line[54:]
        if line[21:26]=='A  10' and line[12:16].strip()==c['ports']['phosphate']['partner']['atom_id']:
            point=[-virtual[1]+55,virtual[0]+10,virtual[2]+2]
            line=line[:30]+''.join(f'{x:8.3f}' for x in point)+line[54:]
        lines[i]=line
    paths[4].write_text(''.join(lines));run(paths,c)
    return paths[-1]


def seed(placement,out,**kw):
    from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
    return prepare_furanose_bridge_seed(placement,out,endpoint_weight=1000.,max_base_displacement=2.,**kw)


@pytest.mark.parametrize('bridged,rename,hand',[(False,False,'D'),(False,True,'L'),(True,False,'D'),(True,True,'D')])
def test_general_seed_preserves_all_source_hands_and_bystanders(tmp_path,bridged,rename,hand):
    from nasolve.cif_furanose_bridge import read_furanose_bridge_seed
    placement=control(tmp_path,bridged=bridged,rename=rename,hand=hand);before=snapshot(tmp_path);out=tmp_path/'seed'
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        q=seed(placement,out);assert read_furanose_bridge_seed(out)==q
    assert q['status']=='FURANOSE_BRIDGE_SEED_REVIEW' and not q['automatic_adoption']
    assert q['native_linkage']=='NOT_ASSESSED' and not q['virtual_atom_written']
    assert q['search']['evaluations']<=27*(1+5*8*6)+1
    assert q['preservation']['max_bond_length_error']<1e-9
    assert q['preservation']['max_angle_error_degrees']<1e-8
    assert q['max_base_displacement_angstrom']<.01
    assert q['virtual_partner_error']<.002
    assert all(abs(j['pdb_rounded']-j['before'])<.002 for j in q['junctions'])
    assert not q['search']['global_minimum_claimed']
    assert len({r['center'] for r in q['source_hands']})==4
    assert len(q['source_hands'])==(7 if bridged else 4)
    unchanged=lambda p:[l for l in p.read_text().splitlines() if not(l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  11')]
    assert unchanged(placement/'model.pdb')==unchanged(out/'model.pdb')
    assert all(snapshot(tmp_path)[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(q)


@pytest.mark.parametrize('key,value',[('endpoint_weight',True),('endpoint_weight',0),('endpoint_weight',1001),('endpoint_weight',float('nan')),('max_base_displacement',True),('max_base_displacement',0),('max_base_displacement',6),('max_base_displacement',float('inf'))])
def test_invalid_bound_refuses_without_output(tmp_path,key,value):
    from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
    placement=control(tmp_path);out=tmp_path/'seed';config={'endpoint_weight':1000.,'max_base_displacement':2.};config[key]=value
    with pytest.raises(ValueError):prepare_furanose_bridge_seed(placement,out,**config)
    assert not out.exists()


def test_excessive_motion_never_becomes_a_seed(tmp_path):
    import nasolve.cif_furanose_bridge as module
    placement=control(tmp_path)
    original=module._search
    def shifted(*args):
        points,report=original(*args);return points+10,report
    with patch.object(module,'_search',shifted),pytest.raises(ValueError,match='base displacement'):
        seed(placement,tmp_path/'seed')
    assert not (tmp_path/'seed').exists()


@pytest.mark.parametrize('defect',['model','report','config','extra','empty_directory','receipt','incomplete'])
def test_rehashed_forgery_refuses(tmp_path,defect):
    from nasolve.cif_furanose_bridge import read_furanose_bridge_seed
    from nasolve.cif_fana_component import _digest
    placement=control(tmp_path);out=tmp_path/'seed';seed(placement,out);r=json.loads((out/'receipt.json').read_text());name=None
    if defect=='model':name='model.pdb';(out/name).write_text((out/name).read_text().replace('20.00','99.00'))
    if defect=='report':name='seed.json';q=json.loads((out/name).read_text());q['native_linkage']='PASS';(out/name).write_text(json.dumps(q))
    if defect=='config':name='config.json';q=json.loads((out/name).read_text());q['extra']=True;(out/name).write_text(json.dumps(q))
    if defect=='extra':(out/'extra').write_text('unbound')
    if defect=='empty_directory':(out/'extra').mkdir()
    if defect=='receipt':r['schema_version']=True
    if name:r['files'][name]=_digest(out/name)
    (out/'receipt.json').write_text(json.dumps(r))
    if defect=='incomplete':(out/'receipt.json').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_furanose_bridge_seed(out)


def test_relocation_and_interruption_preserve_history(tmp_path):
    import nasolve.cif_furanose_bridge as module
    old=tmp_path/'old';old.mkdir();placement=control(old,bridged=True);out=old/'seed';q=seed(placement,out);before=snapshot(old)
    with pytest.raises(FileExistsError):seed(placement,out)
    assert snapshot(old)==before
    moved=old.rename(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert module.read_furanose_bridge_seed(moved/'seed')==q
    assert not old.exists() and snapshot(moved)==before
    original=module._seed;calls=0
    def interrupt(*a):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('interrupted')
        return original(*a)
    with patch.object(module,'_seed',interrupt),pytest.raises(RuntimeError):seed(moved/'control',tmp_path/'partial')
    assert (tmp_path/'partial/placement/receipt.json').exists() and not (tmp_path/'partial/receipt.json').exists()
    with pytest.raises(FileExistsError):seed(moved/'control',tmp_path/'partial')


@pytest.mark.parametrize('defect',['reflection','bond_distortion'])
def test_corrupt_search_result_cannot_bypass_chemistry(tmp_path,defect):
    import nasolve.cif_furanose_bridge as module
    placement=control(tmp_path,bridged=True);original=module._search
    def invalid(*args):
        points,report=original(*args)
        if defect=='reflection':points[:,2]=2*points[:,2].mean()-points[:,2]
        else:points[0,0]+=.01
        return points,report
    with patch.object(module,'_search',invalid),pytest.raises(ValueError):
        module.prepare_furanose_bridge_seed(placement,tmp_path/'seed',endpoint_weight=1000.,max_base_displacement=5.)
    assert not (tmp_path/'seed').exists()
