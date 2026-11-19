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


def representative_capture():
    """Synthetic directed native rows; Cedar authentication remains a caller duty."""
    gemmi=pytest.importorskip('gemmi');cell=gemmi.UnitCell(30,30,40,90,90,90)
    points=[[1.,2.,3.],[4.,5.,6.]];labels=['A','B'];mappings=[];pairs=[];measurements=[]
    rows=[('simple',0,1,'x,y,z',1.),('simple',0,1,'x,y,z',1.),
          ('asu',0,1,'-y,x,z+1/4',.5),('asu',1,0,'y,-x,z-1/4',.5),
          ('asu',0,0,'-y,x,z+1/4',.5)]
    for number,(kind,i,j,xyz,weight) in enumerate(rows):
        image=0 if kind=='simple' else number+1;op=gemmi.Op(xyz)
        if kind=='asu':
            for atom,image_id,operation in ((i,0,gemmi.Op('x,y,z')),(j,image,op)):
                if not any(row[:2]==[atom,image_id] for row in mappings):
                    mappings.append([atom,image_id,[x/operation.DEN for row in operation.rot for x in row],
                                     [x/operation.DEN for x in operation.tran],I])
        q=cell.op_as_transform(op).apply(gemmi.Position(*points[j]))
        distance=math.dist(points[i],list(q));vdw=20.
        pairs.append([kind,i,j,image,vdw])
        measurements.append(dict(proxy_index=number,kind=kind,i_seqs=[i,j],image_j=image,
            atoms=[labels[i],labels[j]],vdw_distance=vdw,distance=distance,overlap=vdw-distance,
            residual=max(0.,vdw-distance)**4*weight,residual_weight=weight))
    return dict(atom_count=2,atoms=[dict(i_seq=i,label=s,xyz=points[i]) for i,s in enumerate(labels)],
        geometry=dict(sites_cart_exact=points),nonbonded_inventory=dict(policy_id=NATIVE_POLICY,
            unit_cell=[30,30,40,90,90,90],pairs=pairs,mappings=mappings),
        _test_review=dict(policy_id=NATIVE_POLICY,analysis_completed=True,pair_sum_and_gradient_replay=True,
            fixed_manager_repeats=True,geometry_accepted=False,measurements=measurements,pair_count=len(pairs),
            total_residual=sum(v['residual'] for v in measurements)))


def reframe(n,**kw):
    from nasolve.topostitch_packing import reframe_native_packing,_digest
    args=dict(atom_labels=['A','B'],atom_images=['x+2,y,z','-y,x,z+1/4'],space_group='P 41',
              expected_native_sha256=_digest(n),reviewer=lambda native:deepcopy(native['_test_review']))
    args.update(kw)
    return reframe_native_packing(n,**args)


def test_representative_contacts_preserve_distances_rows_and_native_multiplicity():
    n=representative_capture();original=deepcopy(n);r=reframe(n)
    assert n==original and r['source_directed_row_count']==5 and r['source_group_count']==4
    assert sum(x['source']['multiplicity'] for x in r['contacts'])==5
    assert r['contacts'][0]['source']['kind'] in ('simple','asu')
    assert r['maximum_distance_error_angstrom']<1e-10
    assert r['source_total_residual']==pytest.approx(n['_test_review']['total_residual'])
    for row in r['contacts']:
        assert row['representative_distance_angstrom']==pytest.approx(row['source']['distance'],abs=1e-10)
        assert len(row['source']['directed_rows'])==row['source']['multiplicity']
    assert any(abs(x['direct_representative_distance_angstrom']-x['source']['distance'])>10 for x in r['contacts'])
    assert not any(r[k] for k in ('runtime_authority','geometry_accepted','native_pair_tables_rebuilt','chemical_connectivity_changed'))


def test_representative_reciprocal_and_self_image_contacts_remain_distinct():
    gemmi=pytest.importorskip('gemmi');r=reframe(representative_capture())
    forward=next(x for x in r['contacts'] if x['source']['kind']=='asu' and x['source']['atoms']==['A','B'])
    reverse=next(x for x in r['contacts'] if x['source']['atoms']==['B','A'])
    assert gemmi.Op(forward['representative_target_operator_xyz']).inverse().triplet()==reverse['representative_target_operator_xyz']
    self_row=next(x for x in r['contacts'] if x['source']['atoms']==['A','A'])
    assert self_row['direct_representative_distance_angstrom']==0
    assert self_row['representative_distance_angstrom']>0


def test_representative_translation_is_not_wrapped_or_reclassified():
    r=reframe(representative_capture(),atom_images=['x+2,y,z','x,y-1,z'])
    row=next(x for x in r['contacts'] if x['source']['kind']=='simple')
    assert row['source']['multiplicity']==2
    assert row['representative_target_operator_xyz']=='x+2,y+1,z'
    assert row['source_target_operator_xyz']=='x,y,z'


def test_identity_representatives_leave_every_source_operation_exact():
    r=reframe(representative_capture(),atom_images=['x,y,z','x,y,z'])
    assert all(row['representative_target_operator_xyz']==row['source_target_operator_xyz'] for row in r['contacts'])


@pytest.mark.parametrize('defect',['hash','labels','missing_image','extra_image','wrong_group','improper',
    'non_group_translation','huge_translation','nonfinite','wrong_count','wrong_order','wrong_distance','bad_review','source_operation'])
def test_representative_contact_context_and_geometry_fail_closed(defect):
    n=representative_capture();kw={}
    if defect=='hash':kw['expected_native_sha256']='0'*64
    elif defect=='labels':kw['atom_labels']=['B','A']
    elif defect=='missing_image':kw['atom_images']=['x,y,z']
    elif defect=='extra_image':kw['atom_images']=['x,y,z']*3
    elif defect=='wrong_group':kw['space_group']='P 1'
    elif defect=='improper':kw['atom_images']=['-x,y,z','x,y,z']
    elif defect=='non_group_translation':kw['atom_images']=['x+1/3,y,z','x,y,z']
    elif defect=='huge_translation':kw['atom_images']=['x+99999999,y,z','x,y,z']
    elif defect=='nonfinite':n['geometry']['sites_cart_exact'][0][0]=math.inf
    elif defect=='wrong_count':n['atom_count']=3
    elif defect=='wrong_order':n['atoms'][0]['i_seq']=1
    elif defect=='wrong_distance':n['_test_review']['measurements'][2]['distance']+=.1;n['_test_review']['measurements'][2]['overlap']-=.1
    elif defect=='bad_review':n['_test_review']['pair_sum_and_gradient_replay']=False
    elif defect=='source_operation':
        n['nonbonded_inventory']['mappings'][1][3][0]+=1/3
    with pytest.raises((ValueError,OverflowError)):reframe(n,**kw)


def test_representative_contact_result_detaches_source_and_reviewer_drift_refuses():
    n=representative_capture();r=reframe(n);r['contacts'][0]['source']['directed_rows'].clear()
    assert len(n['_test_review']['measurements'])==5
    def drifting(native):
        native['atoms'][0]['label']='changed'
        return deepcopy(native['_test_review'])
    with pytest.raises(ValueError):reframe(n,reviewer=drifting)


def test_representative_empty_native_membership_remains_explicit():
    n=representative_capture();n['nonbonded_inventory']['pairs']=[];n['nonbonded_inventory']['mappings']=[]
    n['_test_review'].update(measurements=[],pair_count=0,total_residual=0.)
    r=reframe(n)
    assert r['contacts']==[] and r['source_directed_row_count']==0
    assert r['source_total_residual']==0 and r['maximum_distance_error_angstrom']==0
    assert not r['native_pair_tables_rebuilt']


def test_representative_cell_metric_must_fit_the_requested_rotations():
    n=representative_capture();n['nonbonded_inventory']['unit_cell'][1]=37
    with pytest.raises(ValueError):reframe(n)


def test_representative_direct_distance_overflow_refuses_non_json_numbers():
    n=representative_capture();n['geometry']['sites_cart_exact']=[[1e308,0.,0.],[1e308,0.,0.]]
    n['nonbonded_inventory']['pairs']=n['nonbonded_inventory']['pairs'][:1]
    n['nonbonded_inventory']['mappings']=[]
    row=n['_test_review']['measurements'][0];row.update(distance=0.,overlap=20.,residual=20.**4)
    n['_test_review'].update(measurements=[row],pair_count=1,total_residual=20.**4)
    with pytest.raises(ValueError):reframe(n,atom_images=['x,y,z','-x,-y,z+1/2'])
