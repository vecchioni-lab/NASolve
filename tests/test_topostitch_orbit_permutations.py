"""A representative must permute labelled crystal copies without losing shifts."""
from fractions import Fraction
import json
import shutil

import pytest
gemmi=pytest.importorskip('gemmi')
from nasolve.topostitch_recut import observe_registered_relabel_orbits
from tests.test_topostitch_scattering import fixture,rebind
from nasolve.topostitch_graph import build_registered_periodic_graph


def compose_exact(left,right):
    # Independent rational calculation; do not use the production compose helper.
    a=[[Fraction(v,left.DEN) for v in row] for row in left.rot];b=[[Fraction(v,right.DEN) for v in row] for row in right.rot]
    t=[Fraction(v,left.DEN) for v in left.tran];u=[Fraction(v,right.DEN) for v in right.tran]
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)],[sum(a[i][k]*u[k] for k in range(3))+t[i] for i in range(3)]


@pytest.mark.parametrize('cell,group,image',[
    ((30,30,40,90,90,90),'P 43','y+2,-x-1,z+1/4'),
    ((30,30,40,90,90,120),'H 3','-x+y+2/3,-x+1/3,z+1/3'),
    ((30,40,50,90,110,90),'P 21','-x,y+1/2,-z'),
    ((30,40,50,90,90,90),'P 21 21 21','-x+1/2,-y,z+1/2'),
    ((30,40,50,80,100,110),'P 1','x+2,y-1,z'),
])
def test_exact_permutations_and_independent_expanded_coordinates(tmp_path,cell,group,image):
    paths,kw=fixture(tmp_path,cell=cell,group=group,image=image);kw.pop('hkls');before={p:p.read_bytes() for p in paths}
    r=observe_registered_relabel_orbits(*paths,**kw);ops=[gemmi.Op(s) for s in r['space_group_operations']]
    assigned=[]
    for table in r['image_assignments']:
        h=gemmi.Op(table['operator_xyz']);assigned+=table['atom_indices'];forward=table['forward'];backward=table['inverse']
        assert sorted(v['mapped_group_index'] for v in forward)==list(range(len(ops)))
        for row in forward:
            g=ops[row['input_group_index']];p=ops[row['mapped_group_index']];rot,shift=compose_exact(g,h)
            assert rot==[[Fraction(v,p.DEN) for v in row] for row in p.rot]
            assert shift==[Fraction(v,p.DEN)+n for v,n in zip(p.tran,row['lattice_translation'])]
            inverse=backward[row['mapped_group_index']]
            assert inverse['mapped_group_index']==row['input_group_index']
            assert inverse['lattice_translation']==[-v for v in row['lattice_translation']]
            # Non-axis test point verifies lattice side/sign and multiplication order.
            x=[.123,.237,.341];left=g.apply_to_xyz(h.apply_to_xyz(x));right=[a+n for a,n in zip(p.apply_to_xyz(x),row['lattice_translation'])]
            assert left==pytest.approx(right,abs=1e-12)
    assert sorted(assigned)==list(range(r['atom_count'])) and len(assigned)==len(set(assigned))
    assert r['labelled_cell_image_count']==r['atom_count']*len(ops)
    assert r['status']=='EXACT_LABELLED_ORBIT_PERMUTATIONS'
    assert r['maximum_coordinate_binding_error_angstrom']<1e-10
    assert not r['physical_identity_validated'] and not r['scattering_invariance_validated'] and not r['coordinates_materialized']
    assert all(p.read_bytes()==b for p,b in before.items())
    assert str(tmp_path) not in json.dumps(r)


def test_noop_is_identity_permutation_and_exactly_retains_all_atoms(tmp_path):
    paths,kw=fixture(tmp_path);kw.pop('hkls');kw['node_images']=[]
    r=observe_registered_relabel_orbits(*paths,**kw);assert len(r['image_assignments'])==1
    row=r['image_assignments'][0];assert row['operator_xyz']=='x,y,z' and row['atom_indices']==list(range(r['atom_count']))
    assert all(x['input_group_index']==x['mapped_group_index'] and x['lattice_translation']==[0,0,0] for x in row['forward'])


def test_special_position_retains_labelled_multiplicity_without_physical_claim(tmp_path):
    paths,kw=fixture(tmp_path,cell=(30,30,40,90,90,120),group='H 3',image='-x+y,-x,z');kw.pop('hkls')
    rows=paths[0].read_text().splitlines(keepends=True);i=next(i for i,r in enumerate(rows) if r.startswith('ATOM'))
    rows[i]=rows[i][:30]+f'{0.:8.3f}{0.:8.3f}'+rows[i][46:];rebind(paths,''.join(rows));kw['expected_registered_graph_sha256']=build_registered_periodic_graph(*paths)['report_sha256']
    r=observe_registered_relabel_orbits(*paths,**kw)
    assert r['labelled_cell_image_count']==9*r['atom_count'] and not r['special_position_weights_qualified']
    assert not r['physical_identity_validated']


@pytest.mark.parametrize('budget',[True,0,2_000_001,1])
def test_invalid_or_insufficient_table_budget_refuses(tmp_path,budget):
    paths,kw=fixture(tmp_path);kw.pop('hkls')
    with pytest.raises(ValueError,match='budget'):observe_registered_relabel_orbits(*paths,**kw,max_permutation_rows=budget)


@pytest.mark.parametrize('damage',['points','duplicate_owner','missing_owner'])
def test_changed_preview_cannot_receive_a_coordinate_or_inventory_certificate(tmp_path,monkeypatch,damage):
    paths,kw=fixture(tmp_path);kw.pop('hkls')
    import nasolve.topostitch_recut as module
    original=module.preview_registered_relabel
    def changed(*a,**k):
        r=original(*a,**k)
        if damage=='points':r['proposed_points_angstrom'][r['requested_image_atom_indices'][0]][0]+=.5
        elif damage=='duplicate_owner':r['fixed_atom_indices'].append(r['requested_image_atom_indices'][0])
        else:r['fixed_atom_indices'].pop()
        # Even a rehashed internal result must bind actual source coordinates/ownership.
        r['preview_sha256']=module._fingerprint({k:v for k,v in r.items() if k!='preview_sha256'})
        return r
    monkeypatch.setattr(module,'preview_registered_relabel',changed)
    with pytest.raises(ValueError):observe_registered_relabel_orbits(*paths,**kw)


def test_source_drift_refuses_and_relocation_replays_without_original(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();paths,kw=fixture(source);kw.pop('hkls')
    report=observe_registered_relabel_orbits(*paths,**kw);moved=tmp_path/'relocated';shutil.move(source,moved);paths=tuple(moved/p.name for p in paths)
    assert not source.exists() and observe_registered_relabel_orbits(*paths,**kw)==report
    import nasolve.topostitch_recut as module
    original=module._orbit_permutation
    def drift(*a,**k):
        r=original(*a,**k);paths[1].write_bytes(paths[1].read_bytes()+b'\n');return r
    monkeypatch.setattr(module,'_orbit_permutation',drift)
    with pytest.raises(ValueError,match='changed during'):observe_registered_relabel_orbits(*paths,**kw)


def test_all_65_sohncke_reference_groups_have_exact_inverse_lattice_correspondence():
    from nasolve.topostitch_recut import _orbit_permutation
    from nasolve.topostitch_periodic import _op_key
    checked=0
    for number in range(1,231):
        group=gemmi.SpaceGroup(number)
        if not group.is_sohncke():continue
        ops=sorted(group.operations(),key=_op_key)
        image=gemmi.Op(ops[-1].triplet());image.tran=[v+n*image.DEN for v,n in zip(image.tran,(2,-3,1))]
        forward,inverse=_orbit_permutation(image,ops,gemmi)
        for row in forward:
            rot,t=compose_exact(ops[row['input_group_index']],image);mapped=ops[row['mapped_group_index']]
            assert rot==[[Fraction(v,mapped.DEN) for v in r] for r in mapped.rot]
            assert t==[Fraction(v,mapped.DEN)+n for v,n in zip(mapped.tran,row['lattice_translation'])]
            back=inverse[row['mapped_group_index']]
            assert back['mapped_group_index']==row['input_group_index'] and back['lattice_translation']==[-n for n in row['lattice_translation']]
        checked+=1
    assert checked==65
