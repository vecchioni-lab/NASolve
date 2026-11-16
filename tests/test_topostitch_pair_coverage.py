"""A complete callback must not duplicate ordinary native pair restraints."""
from copy import deepcopy

import pytest

from nasolve.topostitch_recipe import recipe_digest


def atom(label, translation=('0', '0', '0')):
    return dict(atom=label, rotation=[1,0,0,0,1,0,0,0,1], translation=list(translation))


def term(name, kind, offset=''):
    labels=[offset+x for x in ('a','b','c','d','e','f')]
    count={'bond':2,'angle':3,'planarity':3,'parallelity':3}[kind]
    parameters={
        'bond':dict(ideal=2.8,weight=25.,slack=0.,limit=-1.,top_out=False),
        'angle':dict(ideal=116.2,weight=.1,slack=0.),
        'planarity':dict(weights=[10.,20.,30.]),
        'parallelity':dict(ideal=0.,weight=100.,slack=0.,limit=1.,top_out=False),
    }[kind]
    return dict(term_id=name,kind=kind,atoms=[atom(x) for x in labels[:count]],
        other_atoms=[atom(x) for x in labels[3:]] if kind=='parallelity' else [],parameters=parameters)


def inputs():
    kinds=('bond','angle','planarity','parallelity')
    requested=[term('core-'+k,k) for k in kinds]+[term('selected-'+k,k,'s') for k in kinds]
    native=deepcopy(requested[:4]);additive=deepcopy(requested[4:])
    for row in native:row['term_id']='native:'+row['term_id']
    for row in additive:row['term_id']='add:'+row['term_id']
    current=dict(source_model_sha256='a'*64,recipe_sha256='b'*64,atom_labels=list('abcdef')+['s'+x for x in 'abcdef'],crystal_sha256='c'*64,native_exclusion_policy_sha256='d'*64)
    return requested,native,additive,current


def frozen(requested,native,additive,current):
    return dict(context=deepcopy(current),requested_sha256=recipe_digest(requested),
        native_sha256=recipe_digest(native),additive_sha256=recipe_digest(additive),
        native_requested_ids=[r['term_id'] for r in requested if r['term_id'].startswith('core-')])


def review(values, plan=None):
    from nasolve.topostitch_pair_coverage import review_pair_coverage
    r,n,a,c=values
    return review_pair_coverage(r,n,a,frozen=frozen(r,n,a,c) if plan is None else plan,current_context=c)


def test_existing_core_and_explicit_additions_cover_once_without_mutation():
    values=inputs();before=deepcopy(values);result=review(values)
    assert values==before
    assert result['native_requested_term_count']==4 and result['additive_requested_term_count']==4
    assert [r['requested_id'] for r in result['coverage']]==[r['term_id'] for r in values[0]]
    assert [r['provider'] for r in result['coverage']]==['native']*4+['additive']*4
    assert result['declared_coverage_complete'] is True
    assert not result['runtime_authority'] and not result['scientific_acceptance']
    assert result['native_exclusion_policy_sha256']=='d'*64


def test_full_callback_on_ordinary_core_refuses_even_with_current_hashes():
    r,n,a,c=inputs();a+=deepcopy(n)
    with pytest.raises(ValueError,match='Duplicate'):
        review((r,n,a,c))


@pytest.mark.parametrize('source',['native','additive'])
def test_missing_term_is_not_filled_or_reassigned(source):
    r,n,a,c=inputs();(n if source=='native' else a).pop()
    with pytest.raises(ValueError,match='Missing'):
        review((r,n,a,c))


@pytest.mark.parametrize('source',['native','additive'])
def test_repeated_occurrences_are_not_deduplicated(source):
    r,n,a,c=inputs();rows=n if source=='native' else a;duplicate=deepcopy(rows[0]);duplicate['term_id']+='-duplicate';rows.append(duplicate)
    with pytest.raises(ValueError,match='Duplicate'):
        review((r,n,a,c))


def test_unrequested_addition_and_provider_swap_refuse():
    r,n,a,c=inputs();extra=term('extra','bond','s');extra['atoms'][1]=atom('sf');a.append(extra)
    with pytest.raises(ValueError,match='Unrequested'):review((r,n,a,c))
    r,n,a,c=inputs();a.append(n.pop())
    with pytest.raises(ValueError,match='provider'):review((r,n,a,c))


@pytest.mark.parametrize('kind,field,value',[('bond','ideal',2.9),('bond','limit',1.),('bond','top_out',True),('angle','slack',.1),('angle','weight',.2),('parallelity','limit',2.),('parallelity','ideal',1.)])
def test_target_and_mode_differences_are_not_presence_matches(kind,field,value):
    values=inputs();next(t for t in values[1] if t['kind']==kind)['parameters'][field]=value
    with pytest.raises(ValueError,match='parameters'):review(values)


def test_plane_weights_follow_atoms_when_reordered():
    values=inputs();plane=next(t for t in values[1] if t['kind']=='planarity')
    plane['atoms'].reverse();plane['parameters']['weights'].reverse();assert review(values)['declared_coverage_complete']
    plane['parameters']['weights'].reverse()
    with pytest.raises(ValueError,match='parameters'):review(values)


def test_common_rotation_translation_and_family_permutations_match():
    values=inputs()
    for row in values[1]+values[2]:
        for site in row['atoms']+row['other_atoms']:
            site.update(rotation=[0,-1,0,1,0,0,0,0,1],translation=['1','2','3'])
        if row['kind'] in ('bond','angle'):row['atoms'].reverse()
        elif row['kind']=='parallelity':row['atoms'],row['other_atoms']=row['other_atoms'],row['atoms']
    assert review(values)['declared_coverage_complete']


def test_lattice_translation_is_not_wrapped_or_inferred():
    values=inputs();values[2][0]['atoms'][1]['translation'][0]='1'
    with pytest.raises(ValueError,match='Unrequested|Missing'):review(values)


@pytest.mark.parametrize('change',['context','native_bytes','additive_bytes','request_bytes','provider_list'])
def test_stale_frozen_binding_refuses(change):
    values=inputs();r,n,a,c=values;plan=frozen(*values)
    if change=='context':c['native_exclusion_policy_sha256']='e'*64
    elif change=='native_bytes':n[0]['parameters']['weight']=26.
    elif change=='additive_bytes':a[0]['parameters']['weight']=26.
    elif change=='request_bytes':r[0]['parameters']['weight']=26.
    else:plan['native_requested_ids'].append('not-requested')
    with pytest.raises(ValueError):review(values,plan)


@pytest.mark.parametrize('change',['bool','nonfinite','unknown_field','bad_label','bad_rotation','bad_fraction','duplicate_atom','duplicate_id','unknown_kind','zero_digest'])
def test_malformed_term_or_binding_refuses(change):
    r,n,a,c=inputs()
    if change=='bool':a[0]['parameters']['weight']=True
    elif change=='nonfinite':a[0]['parameters']['weight']=float('nan')
    elif change=='unknown_field':a[0]['parameters']['hidden_policy']=1
    elif change=='bad_label':a[0]['atoms'][0]['atom']='unknown'
    elif change=='bad_rotation':a[0]['atoms'][0]['rotation'][0]=-1
    elif change=='bad_fraction':a[0]['atoms'][0]['translation'][0]='2/6'
    elif change=='duplicate_atom':a[0]['atoms'][1]=deepcopy(a[0]['atoms'][0])
    elif change=='duplicate_id':a[1]['term_id']=a[0]['term_id']
    elif change=='unknown_kind':a[0]['kind']='torsion'
    else:c['recipe_sha256']=''
    with pytest.raises(ValueError):review((r,n,a,c))


def test_tiny_weights_are_not_equal_by_absolute_tolerance():
    values=inputs();values[0][0]['parameters']['weight']=1e-20;values[1][0]['parameters']['weight']=1e-16
    with pytest.raises(ValueError,match='parameters'):review(values)


def test_floating_reciprocal_weight_roundoff_is_supported():
    values=inputs();values[1][0]['parameters']['weight']=1/.2**2
    assert review(values)['declared_coverage_complete']


def test_noncommuting_periodic_images_match_under_common_motion_and_reversal():
    values=inputs();requested=values[0][4];addition=values[2][0]
    quarter=[0,-1,0,1,0,0,0,0,1];half=[-1,0,0,0,-1,0,0,0,1]
    requested['atoms'][1].update(rotation=quarter,translation=['0','0','1/4'])
    addition['atoms'][0].update(rotation=quarter,translation=['1','2','3'])
    addition['atoms'][1].update(rotation=half,translation=['1','2','13/4'])
    addition['atoms'].reverse()
    assert review(values)['declared_coverage_complete']


def compiled_fixture(monkeypatch):
    from types import SimpleNamespace as NS
    from nasolve.topostitch_native_recipe import NativePairRecipe
    from nasolve import topostitch_pair_coverage as coverage
    identities=[dict(atom_name=x) for x in 'abcdef']
    packet=dict(source_model_sha256='a'*64,atom_count=6,atom_identities=identities,
        crystal=dict(cell_parameters=[10.,10.,10.,90.,90.,90.],space_group='P 1'),
        pairs=[dict(pair_id='p',purpose='core',target_operator_xyz='x,y,z',
                    role_indices=dict(L=[0,1,2],R=[3,4,5]),
                    expected_counts=dict(bond=1,angle=1,planarity=1,parallelity=1))])
    definitions=[dict(kind=k,pair_id='p',purpose='core',sigma=.2,i_seqs=ids,**extra)
        for k,ids,extra in [('bond',[0,3],dict(ideal=2.8)),
            ('angle',[0,1,3],dict(ideal=116.2)),('planarity',list(range(6)),{}),
            ('parallelity',[0,1,2],dict(ideal=0.,j_seqs=[3,4,5]))]]
    refs=[dict(asu_index=i,rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],translation=[0.,0.,0.]) for i in range(6)]
    recipe=NativePairRecipe.__new__(NativePairRecipe)
    recipe._identities=identities;recipe._count=6;recipe._terms=definitions
    recipe._refs=tuple((v['asu_index'],NS(rotation=v['rotation'],translation=v['translation'])) for v in refs)
    recipe._report=dict(schema_version=1,kind='topostitch-native-pair-binding',source_model_sha256='a'*64,
        recipe_sha256=recipe_digest(packet),atom_count=6,terms=definitions,references=refs)
    recipe._bonds=[NS(i_seqs=[0,3],distance_ideal=2.8,weight=1/.2**2,slack=0.,limit=-1.,top_out=False,rt_mx_ji=None)]
    recipe._angles=[NS(i_seqs=[0,1,3],angle_ideal=116.2,weight=1/.2**2,slack=0.,sym_ops=None)]
    recipe._planes=[NS(i_seqs=list(range(6)),weights=[1/.2**2]*6,sym_ops=None)]
    recipe._parallel=[NS(i_seqs=[0,1,2],j_seqs=[3,4,5],target_angle_deg=0.,weight=1/.2**2,slack=0.,limit=1.,top_out=False,sym_ops=None)]
    def image(text, cell):
        assert text=='x,y,z'
        return dict(rotation=[1,0,0,0,1,0,0,0,1],translation=['0','0','0']),refs[0]['rotation'],refs[0]['translation']
    monkeypatch.setattr(coverage,'_compiled_fractional_image',image,raising=False)
    return recipe,packet


def export(recipe,packet):
    from nasolve.topostitch_pair_coverage import describe_compiled_pair_terms
    return describe_compiled_pair_terms(recipe,packet,expected_binding_sha256=recipe_digest(recipe.binding_report()))


def test_compiled_export_preserves_old_binding_and_returns_detached_terms(monkeypatch):
    recipe,packet=compiled_fixture(monkeypatch);before=deepcopy([recipe.binding_report(),packet]);result=export(recipe,packet)
    assert result['recipe_sha256']==recipe_digest(packet)
    assert result['compiled_binding_sha256']==recipe_digest(before[0])
    assert [r['term_id'] for r in result['terms']]==['p:0','p:1','p:2','p:3']
    assert [r['kind'] for r in result['terms']]==['bond','angle','planarity','parallelity']
    assert result['terms'][0]['parameters']['limit']==-1.
    assert result['terms'][3]['parameters']['limit']==1.
    assert [recipe.binding_report(),packet]==before
    result['terms'][0]['parameters']['weight']=999.
    assert export(recipe,packet)['terms'][0]['parameters']['weight']!=999.
    assert not result['runtime_authority']


@pytest.mark.parametrize('change',['missing_proxy','extra_proxy','proxy_indices','proxy_weight','proxy_mode','proxy_image','virtual_reference','packet','purpose','identity'])
def test_compiled_export_refuses_drift_in_live_proxy_or_bound_packet(monkeypatch,change):
    recipe,packet=compiled_fixture(monkeypatch)
    if change=='missing_proxy':recipe._angles=[]
    elif change=='extra_proxy':recipe._bonds.append(recipe._bonds[0])
    elif change=='proxy_indices':recipe._bonds[0].i_seqs=[1,3]
    elif change=='proxy_weight':recipe._bonds[0].weight=26.
    elif change=='proxy_mode':recipe._parallel[0].limit=2.
    elif change=='proxy_image':recipe._angles[0].sym_ops=['x+1,y,z']
    elif change=='virtual_reference':recipe._refs[0][1].translation=[1.,0.,0.]
    elif change=='packet':packet['pairs'][0]['purpose']='selected'
    elif change=='purpose':recipe._terms[0]['purpose']='selected'
    else:recipe._identities=[dict(atom_name='wrong')]+recipe._identities[1:]
    with pytest.raises(ValueError):export(recipe,packet)


def test_compiled_export_requires_original_binding_digest(monkeypatch):
    from nasolve.topostitch_pair_coverage import describe_compiled_pair_terms
    recipe,packet=compiled_fixture(monkeypatch)
    with pytest.raises(ValueError,match='binding'):
        describe_compiled_pair_terms(recipe,packet,expected_binding_sha256='0'*64)
