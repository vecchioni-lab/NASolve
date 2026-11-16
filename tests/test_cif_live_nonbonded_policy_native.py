"""Actual pinned API controls, run with phenix.python; ordinary Python skips.

Synthetic atoms only. No data files, native copies as inputs, refinement or SDK
mutation. The deepcopy negative control operates on a disposable parameter object.
"""
import copy
import json
import os
import pytest

if os.environ.get('NASOLVE_TEST_NATIVE_NONBONDED') != '1':
    pytest.skip('Opt-in pinned Phenix API qualification', allow_module_level=True)
from cctbx import crystal, geometry_restraints as gr, sgtbx, xray
from cctbx.array_family import flex
from cctbx.geometry_restraints.manager import manager
from cctbx.geometry_restraints.flags import flags
from nasolve import cif_live_nonbonded_policy as policy


def make_case(symbol='P 21 21 21', sites=None):
    sites = sites or [(.1,.2,.3),(.2,.2,.3),(.3,.3,.3)]
    cs=crystal.symmetry(unit_cell=(20,21,22,90,90,90),space_group_symbol=symbol)
    xs=xray.structure(crystal_symmetry=cs,scatterers=flex.xray_scatterer([
        xray.scatterer(label='C%d'%i,site=site) for i,site in enumerate(sites)]))
    n=len(sites);p=gr.nonbonded_params(default_distance=3.)
    for key,value in [('C',1.7),('N',1.5),('UNUSED',1.9)]:p.radius_table[key]=value
    p.ionic_radius_table['N']=1.4;p.donor_acceptor_table['N']=2
    p.distance_table.setdefault('C',{})['N']=3.2;p.distance_table.setdefault('EMPTY',{})
    geo=manager(crystal_symmetry=cs,site_symmetry_table=xs.site_symmetry_table(),
        shell_sym_tables=[crystal.pair_sym_table(n) for _ in range(3)],
        bond_params_table=gr.bond_params_table(n),nonbonded_params=p,
        nonbonded_types=flex.std_string(['C']*n),nonbonded_charges=flex.int(n,0),
        model_indices=flex.size_t(n,0),conformer_indices=flex.size_t(n,0),
        sym_excl_indices=flex.size_t(n,0),donor_acceptor_excl_groups=flex.size_t(n,0),
        nonbonded_function=gr.prolsq_repulsion_function(),nonbonded_distance_cutoff=5.)
    return geo,xs.sites_cart(),dict(flags=flags(default=True),normalization=False,compute_gradients=True)


def test_native_read_only_snapshot_and_rebuilds():
    g,sites,options=make_case()
    initial_vars=dict(vars(g))
    baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    assert set(vars(g))==set(initial_vars)
    assert all(vars(g)[k] is v for k,v in initial_vars.items())
    assert g._pair_proxies is None and g.n_updates_pair_proxies==0
    assert baseline['policy']['parameters']['distance_table']['EMPTY']=={}
    first=g.energies_sites(sites_cart=sites,**options)
    built=policy.require_live_nonbonded_policy(g,json.loads(json.dumps(baseline)),**options)
    assert built['policy_sha256']==baseline['policy_sha256']
    assert built['cache_observations']!=baseline['cache_observations']
    g.reset_internals()
    assert g._pair_proxies is None
    policy.require_live_nonbonded_policy(g,baseline,**options)
    assert g._pair_proxies is None  # the guard did not warm it
    second=g.energies_sites(sites_cart=sites,**options)
    assert first.residual_sum==second.residual_sum
    assert list(first.gradients)==list(second.gradients)
    moved=sites.deep_copy();moved[2]=tuple(v+s for v,s in zip(moved[2],(7.,0.,0.)))
    before=g.n_updates_pair_proxies
    third=g.energies_sites(sites_cart=moved,**options)
    policy.require_live_nonbonded_policy(g,baseline,**options)
    assert g.n_updates_pair_proxies>before
    pair_count=lambda e:len(e.nonbonded_proxies.simple)+len(e.nonbonded_proxies.asu)
    assert pair_count(third)!=pair_count(second)


def test_native_automatic_cutoff_must_be_resolved_and_marker_can_reset():
    g,sites,options=make_case();g.nonbonded_distance_cutoff=None;g.reset_internals()
    with pytest.raises(ValueError,match='resolved'):policy.snapshot_live_nonbonded_policy(g,**options)
    assert g._pair_proxies is None and g.nonbonded_distance_cutoff is None
    g.energies_sites(sites_cart=sites,**options)
    baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    assert g.nonbonded_distance_cutoff_was_determined_automatically
    g.reset_internals()
    assert not g.nonbonded_distance_cutoff_was_determined_automatically
    policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('field',policy.PARAMETER_TABLES+('distance_table',))
def test_native_unused_parameter_mutation_is_detected(field):
    g,_,options=make_case();baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    table=getattr(g.nonbonded_params,field)
    if field=='distance_table':table['EMPTY']['UNUSED']=4.
    else:table['UNUSED']=4.
    with pytest.raises(ValueError,match='parameters'):policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('field',policy.PARAMETER_SCALARS)
def test_native_parameter_scalar_mutation_is_detected(field):
    g,_,options=make_case();baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    setattr(g.nonbonded_params,field,getattr(g.nonbonded_params,field)+.1)
    with pytest.raises(ValueError,match='parameters'):policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('field',policy.ASSIGNMENT_FIELDS)
def test_native_ordered_assignment_mutation_is_detected(field):
    g,_,options=make_case();baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    getattr(g,field)[1]='N' if field=='nonbonded_types' else 1
    with pytest.raises(ValueError,match='assignments'):policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('shell_index',[0,1,2,3])
def test_native_shells_include_exact_rational_images_and_duplicates(shell_index):
    g,_,options=make_case()
    if shell_index==3:g.shell_sym_tables.append(crystal.pair_sym_table(3))
    op=sgtbx.rt_mx('-x,y+1/2,-z')
    g.shell_sym_tables[shell_index][0].setdefault(2,[]).extend([op,op])
    before=policy.snapshot_live_nonbonded_policy(g,**options)
    rows=before['policy']['shells'][shell_index]
    assert rows[2]==[] and len(rows[0][0][1])==2
    assert rows[0][0][1][0]['translation']==[[0,6,0],12]
    # Same image and indices, different multiplicity must not disappear in a set.
    g.shell_sym_tables[shell_index][0][2].append(op)
    with pytest.raises(ValueError,match='shells'):policy.require_live_nonbonded_policy(g,before,**options)


def test_native_special_position_projection_and_nonidentity_pairs():
    g,sites,options=make_case('P 1 2 1',[(0.,.2,0.),(.05,.2,.1)])
    before=policy.snapshot_live_nonbonded_policy(g,**options)
    table=before['policy']['symmetry']['site_table']
    assert max(len(row['matrices']) for row in table)>1
    assert any(row['special_op']['rotation'][0]==[0,0,0,0,1,0,0,0,0] for row in table)
    energy=g.energies_sites(sites_cart=sites,**options)
    assert len(energy.nonbonded_proxies.asu)>0
    policy.require_live_nonbonded_policy(g,before,**options)


def test_native_copy_loss_detected_despite_retained_scalar_values():
    g,_,options=make_case();baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    g.nonbonded_params=copy.deepcopy(g.nonbonded_params)
    for name in policy.PARAMETER_SCALARS:
        assert getattr(g.nonbonded_params,name)==baseline['policy']['parameters'][name]
    with pytest.raises(ValueError,match='parameters'):policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('field',policy.FUNCTION_FIELDS)
def test_native_function_parameters_are_guarded(field):
    g,_,options=make_case();baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    values={name:getattr(g.nonbonded_function,name) for name in policy.FUNCTION_FIELDS}
    values[field]+=1;g.nonbonded_function=gr.prolsq_repulsion_function(**values)
    with pytest.raises(ValueError,match='function'):policy.require_live_nonbonded_policy(g,baseline,**options)


@pytest.mark.parametrize('compute_gradients',[False,True])
@pytest.mark.parametrize('disable_asu_cache',[False,True])
def test_native_invocation_settings(compute_gradients,disable_asu_cache):
    g,sites,options=make_case()
    options.update(compute_gradients=compute_gradients,disable_asu_cache=disable_asu_cache)
    baseline=policy.snapshot_live_nonbonded_policy(g,**options)
    g.energies_sites(sites_cart=sites,**options)
    policy.require_live_nonbonded_policy(g,baseline,**options)
    with pytest.raises(ValueError,match='invocation'):
        policy.require_live_nonbonded_policy(g,baseline,**dict(options,compute_gradients=not compute_gradients))


def test_native_special_position_settings_wrapper_preserves_policy():
    g,sites,options=make_case()
    before=policy.snapshot_live_nonbonded_policy(g,**options)
    g.crystal_symmetry=crystal.special_position_settings(crystal_symmetry=g.crystal_symmetry)
    policy.require_live_nonbonded_policy(g,before,**options)
    g.energies_sites(sites_cart=sites,**options)
    policy.require_live_nonbonded_policy(g,before,**options)
