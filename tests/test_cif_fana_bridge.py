"""Synthetic kinematics and package tests; no scientific refinement claim."""
from copy import deepcopy
import json
from unittest.mock import patch
import numpy as np
import pytest
from tests.test_cif_fana_placement import setup,run,CONTEXT
from tests.test_cif_catalogue import snapshot


def control(tmp_path):
    paths=setup(tmp_path,phosphate_alias=True)
    run(paths,{**CONTEXT,'leaving_atom':'O3P'})
    return paths[-1]


def test_seed_preserves_source_geometry_and_replays_without_execution(tmp_path):
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed,read_fana_bridge_seed
    placement=control(tmp_path);out=tmp_path/'seed';before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        report=prepare_fana_bridge_seed(placement,out)
        assert read_fana_bridge_seed(out)==report
    assert report['status']=='FANA_BRIDGE_SEED_REVIEW' and report['automatic_adoption'] is False
    assert report['virtual_leaving_atom']=='O3P' and not report['virtual_atom_written']
    assert report['search']['starts']==27 and report['search']['evaluations']<=27*(1+5*8*6)+1
    assert report['preservation']['four_sugar_hands'] and report['preservation']['max_bond_length_error']<1e-9
    assert report['preservation']['max_angle_error_degrees']<1e-8
    assert report['preservation']['rounded_max_bond_length_error']<.002
    assert 'O3P' not in [l[12:16].strip() for l in (out/'model.pdb').read_text().splitlines() if l[:6] in {'ATOM  ','HETATM'}]
    assert all(snapshot(tmp_path)[p]==v for p,v in before.items())


def test_graph_cut_does_not_rotate_a_ring_or_multiple_bond():
    from nasolve.cif_fana_bridge import _moving_group
    graph={'a':{'b','x'},'b':{'a','y'},'x':{'a'},'y':{'b'}};bonds={('a','b'):'SINGLE'}
    assert _moving_group(graph,bonds,'a','b')=={'b','y'}
    with pytest.raises(ValueError):_moving_group(graph,{('a','b'):'DOUBLE'},'a','b')
    graph['x'].add('y');graph['y'].add('x')
    with pytest.raises(ValueError):_moving_group(graph,bonds,'a','b')


def test_fit_is_proper_and_rotations_preserve_internal_geometry():
    from nasolve.cif_fana_bridge import _fit
    xyz=np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[1.,1.,1.],[0.,0.,1.]])
    target=xyz@np.array([[0.,1.,0.],[-1.,0.,0.],[0.,0.,1.]])+[3,4,5]
    loss,points,det=_fit(xyz,[(0,1,[1,2,3])],[0.],list(range(5)),target,np.ones(5))
    assert loss<1e-25 and det==pytest.approx(1)
    assert points==pytest.approx(target)
    _,rotated,_=_fit(xyz,[(0,1,[1,2,3])],[90.],list(range(5)),target,np.ones(5))
    assert np.linalg.norm(rotated[2]-rotated[3])==pytest.approx(1)
    with pytest.raises(ValueError):_fit(xyz*0,[(0,1,[1])],[0.],list(range(5)),target,np.ones(5))


@pytest.mark.parametrize('weight',[True,0,-1,float('nan'),float('inf'),1001])
def test_invalid_search_weight_refused_before_output(tmp_path,weight):
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed
    placement=control(tmp_path);out=tmp_path/'seed'
    with pytest.raises(ValueError):prepare_fana_bridge_seed(placement,out,endpoint_weight=weight)
    assert not out.exists()


@pytest.mark.parametrize('defect',['model','report','extra','symlink','incomplete','receipt','config'])
def test_cold_reader_never_trusts_rehashed_outputs(tmp_path,defect):
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed,read_fana_bridge_seed
    from nasolve.cif_fana_component import _digest
    placement=control(tmp_path);out=tmp_path/'seed';prepare_fana_bridge_seed(placement,out)
    r=json.loads((out/'receipt.json').read_text());name=None
    if defect=='model':name='model.pdb';(out/name).write_text((out/name).read_text().replace('20.00','99.00'))
    if defect=='report':
        name='seed.json';q=json.loads((out/name).read_text());q['automatic_adoption']=True;(out/name).write_text(json.dumps(q))
    if defect=='extra':(out/'unknown.txt').write_text('unknown')
    if defect=='symlink':(out/'model.pdb').unlink();(out/'model.pdb').symlink_to(placement/'model.pdb')
    if defect=='config':name='config.json';(out/name).write_text(json.dumps({'endpoint_weight':1.}))
    if name:r['files'][name]=_digest(out/name)
    if defect=='receipt':r['schema_version']=True
    (out/'receipt.json').write_text(json.dumps(r))
    if defect=='incomplete':(out/'receipt.json').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_fana_bridge_seed(out)


def test_relocation_and_existing_output(tmp_path):
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed,read_fana_bridge_seed
    old=tmp_path/'old';old.mkdir();placement=control(old);out=old/'seed';q=prepare_fana_bridge_seed(placement,out)
    before=snapshot(old)
    with pytest.raises(FileExistsError):prepare_fana_bridge_seed(placement,out)
    assert snapshot(old)==before
    moved=old.rename(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert read_fana_bridge_seed(moved/'seed')==q
    assert not old.exists() and snapshot(moved)==before


def seeded_native(tmp_path):
    from tests.test_cif_fana_junction import fixture,save
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed
    from nasolve.cif_construction_provenance import _pdb_inventory
    paths,n=fixture(tmp_path);seed=tmp_path/'seed';prepare_fana_bridge_seed(paths[0],seed)
    inv=_pdb_inventory(seed/'model.pdb')
    for a in n['atoms']:
        i=a['identity'];a['xyz']=inv[(i['chain_id'],i['resseq'],i['icode'],i['altloc'],a['atom_id'])]['xyz']
    n['geometry']['sites_cart_exact']=[a['xyz'] for a in n['atoms']]
    by={(a['identity']['resseq'],a['atom_id']):a['i_seq'] for a in n['atoms']};d=n['geometry']['proxy_details']
    def add(kind,keys,**values):
        ids=[by[k] for k in keys];d[kind].append({'i_seqs':ids,'atoms':[n['atoms'][i]['label'] for i in ids],'origin_id':0,**values})
    for o in [('2',"O3'"),('3',"O5'"),('3','OP1'),('3','OP2')]:
        add('bond_simple',[o,('3','P')],distance_ideal=1.607,weight=1/.012**2,symmetry_operation=None)
    for o,target,sigma in [("O5'",104.,1.9),('OP1',108.,3.),('OP2',108.,3.)]:
        add('angle',[('2',"O3'"),('3','P'),('3',o)],angle_ideal=target,weight=1/sigma**2)
    add('angle',[('2',"C3'"),('2',"O3'"),('3','P')],angle_ideal=119.7,weight=1/1.2**2)
    for a,b in [("O5'",'OP1'),("O5'",'OP2'),('OP1','OP2')]:
        add('angle',[('3',a),('3','P'),('3',b)],angle_ideal=110.,weight=.1)
    n['geometry']['simple_bonds']=deepcopy(d['bond_simple']);n['geometry']['proxy_counts']={k:len(v) for k,v in d.items()}
    capture=tmp_path/'seed-native.json';save(capture,n)
    return paths,seed,capture,n


def test_seed_native_coverage_uses_the_same_junction_validation(tmp_path):
    from nasolve.cif_fana_junction import prepare_fana_junction_angles,read_fana_junction_angles,qualify_fana_junction_angles
    from tests.test_cif_fana_junction import completed
    paths,seed,capture,n=seeded_native(tmp_path);out=tmp_path/'seed-junction'
    q=prepare_fana_junction_angles(paths[0],seed/'model.pdb',capture,paths[3],out,bridge_seed=seed)
    assert read_fana_junction_angles(out)==q and q['outgoing_phosphate_angles']==6
    assert q['policy_id']=='cif-source-bound-fana-seed-junction-angles-v1'
    assert qualify_fana_junction_angles(out,completed(n,q))['status']=='JUNCTION_ANGLE_MECHANICS_PASS'


@pytest.mark.parametrize('defect',['unbound_model','unbound_placement','missing_outgoing','outgoing_angle'])
def test_seed_binding_and_outgoing_checks_cannot_be_bypassed(tmp_path,defect):
    from nasolve.cif_fana_junction import prepare_fana_junction_angles
    from tests.test_cif_fana_junction import save
    paths,seed,capture,n=seeded_native(tmp_path);model=seed/'model.pdb';placement=paths[0]
    if defect=='unbound_model':model=placement/'model.pdb'
    if defect=='unbound_placement':
        other=tmp_path/'other';other.mkdir();placement=control(other)
        p=placement/'frame.pdb';p.write_text(p.read_text()+'REMARK unbound\n')
    if defect=='missing_outgoing':
        d=n['geometry']['proxy_details'];d['bond_simple'].pop();n['geometry']['simple_bonds']=deepcopy(d['bond_simple']);n['geometry']['proxy_counts']['bond_simple']-=1
    if defect=='outgoing_angle':n['geometry']['proxy_details']['angle'][-4]['weight']*=2
    save(capture,n)
    with pytest.raises(ValueError):prepare_fana_junction_angles(placement,model,capture,paths[3],tmp_path/'bad-junction',bridge_seed=seed)


def test_virtual_leaving_point_recovers_a_known_source_pose(tmp_path):
    from nasolve.cif_fana_bridge import prepare_fana_bridge_seed
    from nasolve.cif_stereochemistry_audit import _values,_coordinates
    from tests.test_cif_stereochemistry_audit import write
    paths=setup(tmp_path,phosphate_alias=True);values=_values(paths[1],'LF1')
    # Make this known pose exactly representable in the frozen PDB frame.
    for axis in 'xyz':
        key='_chem_comp_atom.'+axis;values[key]=[f'{float(x):.3f}' for x in values[key]]
    write(paths[1],values);xyz=_coordinates(values,source=False)[1]
    pose=lambda p:[-p[1]+30,p[0]+10,p[2]+2]
    virtual=pose(xyz['O3P']);lines=paths[2].read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[:6] in {'ATOM  ','HETATM'} and line[21:26]=='A   1' and line[12:16].strip()=="O3'":
            lines[i]=line[:30]+''.join(f'{x:8.3f}' for x in virtual)+line[54:]
    paths[2].write_text(''.join(lines));run(paths,{**CONTEXT,'leaving_atom':'O3P'})
    report=prepare_fana_bridge_seed(paths[-1],tmp_path/'seed')
    assert report['virtual_partner_error']<1e-10
    assert report['search']['trials'][report['search']['selected_trial']]['weighted_mean_square']<1e-20
    for name,point in report['full_precision_heavy_coordinates'].items():
        assert point==pytest.approx(pose(xyz[name]),abs=1e-10)
