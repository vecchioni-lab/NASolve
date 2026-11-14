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
