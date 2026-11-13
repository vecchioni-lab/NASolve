from copy import deepcopy
import math
import pytest
from nasolve.topostitch_packing import compare_native_packing, NATIVE_POLICY

I=[1,0,0,0,1,0,0,0,1]
R=[0,-1,0,1,-1,0,0,0,1]


def capture(rows, *, image=1, translation=(1/3,0,0), first=None):
    # Test the comparison layer; this fixture is not a native authentication test.
    mappings=[];pairs=[];measurements=[]
    for index,(i,j,distance,weight) in enumerate(rows):
        pairs.append(['asu',i,j,image,3.])
        measurements.append(dict(proxy_index=index,kind='asu',i_seqs=[i,j],image_j=image,
            atoms=['A','B'][i:i+1]+['A','B'][j:j+1],vdw_distance=3.,distance=distance,
            overlap=3.-distance,residual=max(0.,3.-distance)**4*weight,residual_weight=weight))
        for key,rotation,t in [((i,0),I,(0,0,0)),((j,image),R,translation)]:
            if not any(r[:2]==list(key) for r in mappings):mappings.append([*key,rotation,list(t),I])
    if first is not None:
        for row in mappings:
            if row[1]==0:row[2],row[3]=first
    review=dict(policy_id=NATIVE_POLICY,analysis_completed=True,pair_sum_and_gradient_replay=True,
        fixed_manager_repeats=True,geometry_accepted=False,measurements=measurements,pair_count=len(rows),
        total_residual=sum(r['residual'] for r in measurements))
    return dict(atoms=[dict(label='A'),dict(label='B')],installed_api_sources={},restraint_policy={},
        parameter_consumers={},phil_adaptations=[],geometry=dict(proxy_details={}),
        nonbonded_inventory=dict(policy_id=NATIVE_POLICY,pairs=pairs,mappings=mappings,
            unit_cell=[40,40,70,90,90,120],function_parameters={'c_rep':1}),_test_review=review)


def compare(a,b):return compare_native_packing(a,b,reviewer=lambda n:deepcopy(n['_test_review']))


def test_renumbered_native_image_matches_by_operation():
    a=capture([(0,1,3.1,.5)],image=1);b=capture([(0,1,2.8,.5)],image=7)
    saved=deepcopy((a,b));result=compare(a,b)
    assert (a,b)==saved
    assert result['summary']['common_identity_count']==1
    assert result['summary']['newly_overlapping_existing_count']==1
    assert result['summary']['newly_listed_overlapping_count']==0
    assert result['geometry_accepted'] is result['runtime_authority'] is False
    assert result['common_pairs'][0]['positive_overlap_change']==pytest.approx(.2)


def test_lattice_translation_is_not_wrapped():
    a=capture([(0,1,2.9,.5)],translation=(1/3,0,0));b=capture([(0,1,2.8,.5)],translation=(4/3,0,0))
    r=compare(a,b)
    assert r['summary']['common_identity_count']==0
    assert len(r['added_pairs'])==len(r['removed_pairs'])==1
    assert r['summary']['newly_listed_overlapping_count']==1


def test_relative_mapping_uses_both_endpoint_images():
    # Simultaneously translate both mappings; relative physical contact is unchanged.
    a=capture([(0,1,2.9,.5)],translation=(1/3,0,0))
    b=capture([(0,1,2.8,.5)],translation=(4/3,0,0),first=(I,[1,0,0]))
    assert compare(a,b)['summary']['common_identity_count']==1


def test_directed_multiplicity_and_weights_are_not_deduplicated():
    a=capture([(0,1,2.9,.5)]);b=capture([(0,1,2.8,.5),(0,1,2.8,.5)])
    r=compare(a,b);row=r['common_pairs'][0]
    assert row['after']['multiplicity']==2
    assert row['after']['residual']==pytest.approx(.2**4)
    assert r['summary']['multiplicity_changes']==1
    assert len(row['after']['directed_rows'])==2


def test_existing_overlap_can_worsen_while_total_energy_falls():
    a=capture([(0,1,2.,.5),(1,0,3.1,.5)])
    b=capture([(0,1,2.5,.5),(1,0,2.8,.5)])
    r=compare(a,b)['summary']
    assert r['native_residual_after']<r['native_residual_before']
    assert r['worsened_existing_overlap_count']==r['newly_overlapping_existing_count']==1


@pytest.mark.parametrize('change', ['context','labels','definitions','cell','function','vdw','invalid_review','nan','irrational','improper','duplicate_mapping'])
def test_incompatible_or_corrupt_evidence_rejected(change):
    a=capture([(0,1,2.9,.5)]);b=deepcopy(a)
    if change=='context':b['restraint_policy']={'different':True}
    elif change=='labels':b['atoms'][1]['label']='A'
    elif change=='definitions':b['geometry']['proxy_details']={'changed':[]}
    elif change=='cell':b['nonbonded_inventory']['unit_cell'][0]=41
    elif change=='function':b['nonbonded_inventory']['function_parameters']['c_rep']=2
    elif change=='vdw':b['nonbonded_inventory']['pairs'][0][-1]=4
    elif change=='invalid_review':b['_test_review']['pair_sum_and_gradient_replay']=False
    elif change=='nan':b['_test_review']['measurements'][0]['distance']=math.nan
    elif change=='irrational':b['nonbonded_inventory']['mappings'][1][3][0]=math.sqrt(2)
    elif change=='improper':b['nonbonded_inventory']['mappings'][1][2]=[-1,0,0,0,1,0,0,0,1]
    else:b['nonbonded_inventory']['mappings'].append(deepcopy(b['nonbonded_inventory']['mappings'][0]))
    with pytest.raises(ValueError):compare(a,b)


def test_relative_rotation_uses_inverse_of_first_mapping():
    a=capture([(0,1,2.9,.5)])
    b=capture([(0,1,2.8,.5)],translation=(1,1/3,0),first=(R,[1,0,0]))
    b['nonbonded_inventory']['mappings'][1][2]=[-1,1,0,-1,0,0,0,0,1]
    assert compare(a,b)['summary']['common_identity_count']==1


def test_self_image_and_reciprocal_rows_are_retained():
    a=capture([(0,0,2.9,.5),(0,1,2.9,.5),(1,0,2.9,.5)])
    r=compare(a,deepcopy(a))
    assert r['summary']['common_identity_count']==3
    assert r['summary']['directed_rows_before']==3
    assert r['summary']['worsened_existing_overlap_count']==0


def test_removed_neighbor_is_not_claimed_as_resolved_overlap():
    a=capture([(0,1,2.9,.5)]);b=capture([])
    r=compare(a,b)
    assert len(r['removed_pairs'])==1 and not r['common_pairs']
    assert r['summary']['worsened_existing_overlap_count']==0


def test_identity_simple_pair_is_compared_separately_from_asu_pair():
    a=capture([(0,1,2.9,1.)]);b=deepcopy(a)
    for n in (a,b):
        n['nonbonded_inventory']['pairs'][0][0]='simple'
        n['nonbonded_inventory']['pairs'][0][3]=0
        n['nonbonded_inventory']['mappings']=[]
        n['_test_review']['measurements'][0].update(kind='simple',image_j=0)
    r=compare(a,b)
    assert r['common_pairs'][0]['after']['fractional_operation']==dict(rotation=I,translation=['0','0','0'])



def test_reader_retains_first_snapshot_when_paths_repeat(tmp_path):
    from pathlib import Path
    import runpy
    reader=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/compare_topostitch_native_packing.py'))
    remember=reader['_remember'];path=tmp_path/'model.pdb';snapshots={}
    remember(snapshots,{path:b'original'})
    remember(snapshots,{path:b'original'})
    with pytest.raises(ValueError,match='changed between reads'):
        remember(snapshots,{path:b'changed'})
    assert snapshots[path]==b'original'
