"""Hidden native proxy policy and individual regressions must stay visible."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from nasolve.topostitch_native_terms import checked_proxy_rows, compare_native_term_observations


def inventory():
    atoms=[dict(i_seq=i,label=str(i),identity=dict(atom_name=str(i))) for i in range(4)]
    torsion=dict(i_seqs=[0,1,2,3],atoms=['0','1','2','3'],angle_ideal=60.,weight=.0025,
                 periodicity=3,alt_angle_ideals=None,origin_id=0)
    plane=dict(i_seqs=[0,1,2],atoms=['0','1','2'],weights=[100.,100.,100.],origin_id=0)
    native=dict(atom_count=4,atoms=atoms,geometry=dict(proxy_details=dict(dihedral=[torsion],planarity=[plane]),
                                                    proxy_counts=dict(dihedral=1,planarity=1)))
    t=SimpleNamespace(**{k:v for k,v in torsion.items() if k!='atoms'},sym_ops=None,limit=-1.,top_out=False,slack=0.)
    p=SimpleNamespace(**{k:v for k,v in plane.items() if k!='atoms'},sym_ops=None)
    return native,SimpleNamespace(dihedral_proxies=[t],planarity_proxies=[p])


def test_live_proxy_policy_is_required_even_when_capture_has_no_such_fields():
    native,geo=inventory();result=checked_proxy_rows(geo,native)
    assert result['dihedral'][0]['live_policy']==dict(symmetry_operations=None,limit=-1.,top_out=False,slack=0.)
    del geo.dihedral_proxies[0].slack
    with pytest.raises(ValueError,match='omits required'):checked_proxy_rows(geo,native)


@pytest.mark.parametrize('field,value', [('slack',.001),('top_out',True),('limit',1.),('weight',.1),
                                         ('alt_angle_ideals',[120.]),('i_seqs',[3,2,1,0])])
def test_hidden_torsion_policy_or_live_definition_change_refuses(field,value):
    native,geo=inventory();setattr(geo.dihedral_proxies[0],field,value)
    with pytest.raises(ValueError):checked_proxy_rows(geo,native)


@pytest.mark.parametrize('kind', ['dihedral','planarity'])
def test_nonidentity_images_are_not_discarded_by_local_kernel_adapter(kind):
    native,geo=inventory();proxy=getattr(geo,kind+'_proxies')[0]
    proxy.sym_ops=[SimpleNamespace(as_xyz=lambda:'x,y,z') for _ in proxy.i_seqs]
    checked_proxy_rows(geo,native)
    proxy.sym_ops[-1]=SimpleNamespace(as_xyz=lambda:'x+1,y,z')
    with pytest.raises(ValueError,match='identity-only'):checked_proxy_rows(geo,native)


def observation():
    native,geo=inventory();bound=checked_proxy_rows(geo,native);families={}
    for kind in ('dihedral','planarity'):
        rows=[dict(proxy_index=0,**bound[kind][0],scope='boundary',native_residual=10.,measurement=dict(value=1.))]
        families[kind]=dict(rows=rows,proxy_count=1,native_residual=10.,container_target=10.,
                            complete_family_sum_verified=True,full_family_gradient_verified=True)
    return dict(schema_version=1,kind='topostitch-native-term-observation',binding_sha256='a'*64,points_sha256='b'*64,
        families=families,deferred_proxy_kinds=dict(const_dihedral=3),normalization=False,
        derivative_qualification='NOT_RUN',chemical_qualification='NOT_ESTABLISHED',runtime_authority=False,scientific_acceptance=False)


def test_lower_total_keeps_worsening_plane_visible_beside_improving_torsion():
    before=observation();after=deepcopy(before);after['points_sha256']='c'*64
    for kind,value in [('dihedral',1.),('planarity',12.)]:
        f=after['families'][kind];f['rows'][0]['native_residual']=value;f['native_residual']=f['container_target']=value
    report=compare_native_term_observations(before,after)
    assert sum(f['target_change'] for f in report['families'].values())==-7.
    assert report['families']['planarity']['scopes']['boundary']['increased_proxy_indices']==[0]
    assert report['deferred_proxy_kinds']==dict(const_dihedral=3)
    assert not report['scientific_acceptance'] and report['chemical_qualification']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('edit', [
    lambda r:r.update(binding_sha256='c'*64),
    lambda r:r.update(points_sha256='not-a-digest'),
    lambda r:r.update(scientific_acceptance=True),
    lambda r:r['deferred_proxy_kinds'].update(const_dihedral=2),
    lambda r:r['families']['dihedral'].update(native_residual=9.),
    lambda r:r['families']['dihedral']['rows'][0]['definition'].update(weight=.5),
    lambda r:r['families']['dihedral']['rows'][0]['live_policy'].update(slack=.1),
    lambda r:r['families']['dihedral']['rows'][0].update(scope='fixed_only'),
    lambda r:r['families']['dihedral']['rows'][0].update(native_residual=float('nan')),
])
def test_comparison_rejects_changed_binding_policy_or_arithmetic(edit):
    before=observation();after=deepcopy(before);edit(after)
    with pytest.raises(ValueError):compare_native_term_observations(before,after)


# W71: the durable record carries fields omitted by native proxy pickle.
def angle_inventory():
    atoms = [dict(i_seq=i, label=f'atom-{i}', identity=dict(atom_name=str(i))) for i in range(4)]
    rows = [dict(i_seqs=[0, 1, 2], atoms=['atom-0', 'atom-1', 'atom-2'],
                 angle_ideal=109.5, weight=2., origin_id=0),
            dict(i_seqs=[1, 2, 3], atoms=['atom-1', 'atom-2', 'atom-3'],
                 angle_ideal=120., weight=0., origin_id=3)]
    native = dict(atom_count=4, atoms=atoms, geometry=dict(
        proxy_details=dict(angle=rows), proxy_counts=dict(angle=2)))
    proxies = [SimpleNamespace(**{k:v for k,v in row.items() if k!='atoms'},
                              sym_ops=None, slack=.25) for row in rows]
    proxies[0].sym_ops = [SimpleNamespace(as_xyz=lambda value=value:value)
                         for value in ('x,y,z', 'x,y,z', 'x+1,y,z')]
    return native, SimpleNamespace(angle_proxies=proxies)


def freeze_angles():
    from nasolve.topostitch_native_terms import freeze_native_angles
    native, geo = angle_inventory()
    return freeze_native_angles(geo, native, cell_parameters=[40, 40, 70, 90, 90, 120], space_group='P 1')


def test_angle_snapshot_retains_live_images_slack_zero_weight_and_origin():
    import json
    from nasolve.topostitch_native_terms import validate_angle_snapshot
    from nasolve.topostitch_recipe import recipe_digest
    packet = freeze_angles()
    restored = json.loads(json.dumps(packet))
    assert validate_angle_snapshot(restored, expected_sha256=recipe_digest(packet)) == packet
    assert packet['terms'][0]['sym_ops'] == ['x,y,z', 'x,y,z', 'x+1,y,z']
    assert packet['terms'][1]['sym_ops'] is None
    assert packet['terms'][1]['slack'] == .25
    assert packet['terms'][1]['weight'] == 0.
    assert packet['terms'][1]['origin_id'] == 3
    assert packet['runtime_authority'] is False
    restored['terms'][0]['sym_ops'][2] = 'x,y,z'
    with pytest.raises(ValueError, match='checksum'):
        validate_angle_snapshot(restored, expected_sha256=recipe_digest(packet))


@pytest.mark.parametrize('edit', [
    lambda n,g: setattr(g.angle_proxies[0], 'slack', float('nan')),
    lambda n,g: delattr(g.angle_proxies[0], 'sym_ops'),
    lambda n,g: setattr(g.angle_proxies[0], 'weight', 3.),
    lambda n,g: g.angle_proxies.pop(),
    lambda n,g: n['atoms'][1].update(i_seq=0),
    lambda n,g: n['geometry']['proxy_details']['angle'][0]['atoms'].reverse(),
    lambda n,g: setattr(g.angle_proxies[0], 'sym_ops', []),
])
def test_angle_snapshot_does_not_infer_missing_live_metadata(edit):
    from nasolve.topostitch_native_terms import freeze_native_angles
    native, geo = angle_inventory(); edit(native, geo)
    with pytest.raises(ValueError):
        freeze_native_angles(geo, native, cell_parameters=[40, 40, 70, 90, 90, 120], space_group='P 1')


@pytest.mark.parametrize('edit', [
    lambda p:p.update(schema_version=True),
    lambda p:p.update(runtime_authority=True),
    lambda p:p.update(normalization=True),
    lambda p:p.update(extra='ignored'),
    lambda p:p.update(source_native_sha256='unbound'),
    lambda p:p['crystal'].update(cell_parameters=[40,40,70,90,90,180]),
    lambda p:p['crystal'].update(space_group=''),
    lambda p:p['terms'][0].update(i_seqs=[0,1,4]),
    lambda p:p['terms'][0].update(i_seqs=[0,1,True]),
    lambda p:p['terms'][0].update(i_seqs=[0,1,0]),
    lambda p:p['terms'][0].update(origin_id=256),
    lambda p:p['terms'][0].update(weight=-1),
    lambda p:p['terms'][0].update(slack=-.1),
    lambda p:p['terms'][0].update(angle_ideal=181),
    lambda p:p['terms'][0].update(sym_ops=['x,y,z']),
    lambda p:p['terms'][0].update(sym_ops=[None]*3),
    lambda p:p['terms'][0].update(proxy_index=1),
    lambda p:p['atom_labels'].append('unexpected'),
])
def test_angle_snapshot_rejects_bad_schema_even_with_recomputed_digest(edit):
    from nasolve.topostitch_native_terms import validate_angle_snapshot
    from nasolve.topostitch_recipe import recipe_digest
    packet = freeze_angles(); edit(packet)
    with pytest.raises(ValueError):
        validate_angle_snapshot(packet, expected_sha256=recipe_digest(packet))


def test_angle_snapshot_detaches_inputs_and_preserves_empty_family():
    from nasolve.topostitch_native_terms import freeze_native_angles, validate_angle_snapshot
    from nasolve.topostitch_recipe import recipe_digest
    native, geo = angle_inventory()
    packet = freeze_native_angles(geo, native, cell_parameters=[40,40,70,90,90,120], space_group='P 1')
    geo.angle_proxies[0].weight = 7.
    native['atoms'][0]['label'] = 'changed'
    assert packet['terms'][0]['weight'] == 2. and packet['atom_labels'][0] == 'atom-0'
    detached = validate_angle_snapshot(packet, expected_sha256=recipe_digest(packet))
    detached['terms'][0]['sym_ops'][0] = 'x+1,y,z'
    assert packet['terms'][0]['sym_ops'][0] == 'x,y,z'
    native, geo = angle_inventory(); native['geometry']['proxy_details']['angle'] = []
    native['geometry']['proxy_counts']['angle'] = 0; geo.angle_proxies = None
    packet = freeze_native_angles(geo, native, cell_parameters=[40,40,70,90,90,120], space_group='P 1')
    assert packet['terms'] == [] and packet['runtime_authority'] is False
