"""Synthetic API transport/negative controls; actual pinned SDK has separate evidence."""
from types import SimpleNamespace
import json
import pytest


class Map(dict):
    def size(self): return len(self)


class Rational:
    def __init__(self, values, denominator=1): self.values, self.denominator = values, denominator
    def num(self): return self.values
    def den(self): return self.denominator


class Operation:
    def __init__(self, translation=(0, 0, 0), denominator=1):
        self.rotation = Rational((1,0,0,0,1,0,0,0,1))
        self.translation = Rational(translation, denominator)
    def r(self): return self.rotation
    def t(self): return self.translation


class SiteOps:
    def matrices(self): return [Operation()]
    def special_op(self): return Operation()
    def multiplicity(self): return 1


class SiteTable:
    def indices(self): return [0, 0, 0]
    def table(self): return [SiteOps()]


class Crystal:
    def unit_cell(self): return SimpleNamespace(parameters=lambda: (20.,21.,22.,90.,90.,90.))
    def space_group(self): return [Operation()]


class Shell(list): pass
class Parameters: pass
class Function: pass
class Flags: pass
class Manager: pass


@pytest.fixture
def case(monkeypatch):
    from nasolve import cif_live_nonbonded_policy as m
    monkeypatch.setattr(m, '_native_types', lambda: dict(manager=Manager, params=Parameters,
        function=Function, flags=Flags, crystal=(Crystal,), site_table=SiteTable,
        shell=Shell, operation=Operation, site_ops=(SiteOps, SimpleNamespace),
        scalar_map=Map, nested_map=Map, pair_map=Map, indices=list, charges=list, types=list))
    p=Parameters()
    for field in m.PARAMETER_SCALARS: setattr(p, field, 0.)
    p.factor_1_4_interactions=2/3
    for field in m.PARAMETER_TABLES: setattr(p, field, Map({'C':1.7,'UNUSED':2.1}))
    p.distance_table=Map({'C':Map({'N':3.2}), 'EMPTY':Map()})
    f=Function()
    for name,value in zip(m.FUNCTION_FIELDS, (16.,1.,1.,4.)): setattr(f,name,value)
    g=Manager()
    g.nonbonded_params=p;g.nonbonded_function=f
    for field in m.ASSIGNMENT_FIELDS: setattr(g,field,[0,0,0])
    g.nonbonded_types=['C','C','N'];g.nonbonded_charges=[0,0,1]
    g.shell_sym_tables=[Shell([Map({1:[Operation()]}), Map(), Map()]),Shell([Map(),Map(),Map()])]
    g.crystal_symmetry=Crystal();g.site_symmetry_table=SiteTable()
    g.nonbonded_distance_cutoff=5.;g.nonbonded_buffer=1.;g.min_cubicle_edge=5.
    g.plain_pairs_radius=None;g.max_reasonable_bond_distance=None;g.external_energy_function=None
    g.adjusted_nonbonded_distance_cutoff=3.4;g.effective_nonbonded_buffer=2.6
    g.n_updates_pair_proxies=1;g.nonbonded_distance_cutoff_was_determined_automatically=True
    flags=Flags()
    for field in m.FLAG_FIELDS:setattr(flags,field,True)
    options=dict(flags=flags,normalization=False)
    return m,g,options


def test_snapshot_is_detached_and_json_roundtrips(case):
    m,g,options=case
    before=m.snapshot_live_nonbonded_policy(g,**options)
    frozen=json.dumps(before,sort_keys=True)
    assert m.require_live_nonbonded_policy(g,json.loads(frozen),**options)['policy_sha256']==before['policy_sha256']
    g.nonbonded_params.radius_table['UNUSED']=99.
    assert json.dumps(before,sort_keys=True)==frozen
    with pytest.raises(ValueError,match='parameters'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field',['distance_table', 'radius_table','ionic_radius_table','donor_acceptor_table'])
def test_unused_table_values_and_empty_rows_remain_guarded(case,field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    if field=='distance_table':g.nonbonded_params.distance_table['EMPTY']['NOT_PRESENT']=3.
    else:getattr(g.nonbonded_params,field)['UNUSED']+=.1
    with pytest.raises(ValueError,match='parameters'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field',['factor_1_4_interactions','const_shrink_1_4_interactions','default_distance','minimum_distance','const_shrink_donor_acceptor'])
def test_every_parameter_scalar_is_guarded(case,field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    setattr(g.nonbonded_params,field,getattr(g.nonbonded_params,field)+.1)
    with pytest.raises(ValueError,match='parameters'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field',['model_indices','conformer_indices','sym_excl_indices','donor_acceptor_excl_groups','nonbonded_types','nonbonded_charges'])
def test_assignments_are_ordered_and_complete(case,field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    getattr(g,field)[2]='C' if field=='nonbonded_types' else 2
    with pytest.raises(ValueError,match='assignments'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field',['nonbonded_distance_cutoff','nonbonded_buffer','min_cubicle_edge','plain_pairs_radius','max_reasonable_bond_distance'])
def test_fixed_search_controls_are_guarded(case,field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    setattr(g,field,9.)
    with pytest.raises(ValueError,match='search'):m.require_live_nonbonded_policy(g,before,**options)


def test_derived_cache_changes_do_not_change_fixed_policy(case):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    g.adjusted_nonbonded_distance_cutoff=2.;g.effective_nonbonded_buffer=1.
    g.n_updates_pair_proxies=5;g.nonbonded_distance_cutoff_was_determined_automatically=False
    after=m.require_live_nonbonded_policy(g,before,**options)
    assert after['policy_sha256']==before['policy_sha256'] and after['cache_observations']!=before['cache_observations']


def test_unsettled_cutoff_refuses_without_mutating_it(case):
    m,g,options=case;g.nonbonded_distance_cutoff=None
    with pytest.raises(ValueError,match='resolved'):m.snapshot_live_nonbonded_policy(g,**options)
    assert g.nonbonded_distance_cutoff is None and g.n_updates_pair_proxies==1


def test_shell_direction_multiplicity_and_rational_images_are_guarded(case):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    g.shell_sym_tables[1][2][0]=[Operation((1,0,0),2),Operation((1,0,0),2)]
    with pytest.raises(ValueError,match='shells'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('kind',['cell','site_index','site_operation','function','flags','normalization'])
def test_symmetry_function_and_actual_invocation_are_guarded(case,kind):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    if kind=='cell':g.crystal_symmetry.unit_cell=lambda:SimpleNamespace(parameters=lambda:(21.,21.,22.,90.,90.,90.))
    elif kind=='site_index':g.site_symmetry_table.indices=lambda:[0,0,1];g.site_symmetry_table.table=lambda:[SiteOps(),SiteOps()]
    elif kind=='site_operation':g.site_symmetry_table.table=lambda:[SimpleNamespace(matrices=lambda:[Operation()],special_op=lambda:Operation((1,0,0),2),multiplicity=lambda:1)]
    elif kind=='function':g.nonbonded_function.c_rep=32.
    elif kind=='flags':options['flags'].nonbonded=False
    else:options['normalization']=True
    with pytest.raises(ValueError):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('kind',['custom','external','manager_external','extensions','nan','short_assignment','missing_table','unknown_schema','tampered_digest','oversized'])
def test_unsupported_or_malformed_policy_refuses(case,kind):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    if kind=='custom':options['custom_nonbonded_function']=g.nonbonded_function
    elif kind=='external':options['external_energy_function']=lambda:0.
    elif kind=='manager_external':g.external_energy_function=lambda:0.
    elif kind=='extensions':options['extension_objects']=[object()]
    elif kind=='nan':g.nonbonded_params.radius_table['C']=float('nan')
    elif kind=='short_assignment':g.nonbonded_charges=[0]
    elif kind=='missing_table':del g.nonbonded_params.ionic_radius_table
    elif kind=='unknown_schema':before['schema_version']=2
    elif kind=='tampered_digest':before['policy_sha256']='0'*64
    else:g.nonbonded_types=['C']*(m.MAX_ATOMS+1)
    with pytest.raises(ValueError):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field', ['bond','nonbonded','angle','dihedral','reference_coordinate',
    'reference_dihedral','ncs_dihedral','den_restraints','chirality','planarity',
    'parallelity','bond_similarity','ramachandran_restraints'])
def test_every_resolved_flag_is_guarded(case, field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    setattr(options['flags'],field,False)
    with pytest.raises(ValueError,match='invocation'):m.require_live_nonbonded_policy(g,before,**options)


@pytest.mark.parametrize('field', ['compute_gradients','disable_asu_cache'])
def test_actual_native_call_settings_are_guarded(case,field):
    m,g,options=case;before=m.snapshot_live_nonbonded_policy(g,**options)
    with pytest.raises(ValueError,match='invocation'):
        m.require_live_nonbonded_policy(g,before,**dict(options,**{field:True}))


def test_optional_assignment_absence_is_not_empty(case):
    m,g,options=case;g.model_indices=None
    before=m.snapshot_live_nonbonded_policy(g,**options)
    g.model_indices=[]
    with pytest.raises(ValueError,match='assignments'):m.require_live_nonbonded_policy(g,before,**options)


def test_snapshot_does_not_call_native_evaluation(case,monkeypatch):
    m,g,options=case
    def forbidden(*args,**kwargs):raise AssertionError('Read path called native evaluation')
    monkeypatch.setattr(Manager,'energies_sites',forbidden,raising=False)
    monkeypatch.setattr(Manager,'pair_proxies',forbidden,raising=False)
    before=dict(vars(g));baseline=m.snapshot_live_nonbonded_policy(g,**options)
    m.require_live_nonbonded_policy(g,baseline,**options)
    assert set(vars(g))==set(before) and all(vars(g)[key] is value for key,value in before.items())


@pytest.mark.parametrize('kind',['unknown_type','noncrystal','bad_index','zero_denominator',
    'bad_boolean','gradient_buffer','unknown_envelope','invalid_cache','nonfinite_baseline',
    'deep_baseline','cyclic_baseline','item_bound','byte_bound','long_key','overridden_manager'])
def test_additional_malformed_or_unsupported_cases_refuse(case,monkeypatch,kind):
    m,g,options=case;baseline=m.snapshot_live_nonbonded_policy(g,**options)
    if kind=='unknown_type':g.nonbonded_function=SimpleNamespace(c_rep=16.,k_rep=1.,irexp=1.,rexp=4.)
    elif kind=='noncrystal':g.crystal_symmetry=None;g.site_symmetry_table=None
    elif kind=='bad_index':g.shell_sym_tables[0][0][3]=[Operation()]
    elif kind=='zero_denominator':g.shell_sym_tables[0][0][1][0].translation.denominator=0
    elif kind=='bad_boolean':options['normalization']=1
    elif kind=='gradient_buffer':options['gradients']=[]
    elif kind=='unknown_envelope':baseline['extra']='unexpected'
    elif kind=='invalid_cache':baseline['cache_observations']['n_updates_pair_proxies']=True
    elif kind=='nonfinite_baseline':baseline['policy']['parameters']['default_distance']=float('inf')
    elif kind=='deep_baseline':
        value=[]
        for _ in range(34):value=[value]
        baseline['policy']['deep']=value
    elif kind=='cyclic_baseline':baseline['policy']['cycle']=baseline
    elif kind=='item_bound':monkeypatch.setattr(m,'MAX_ITEMS',2)
    elif kind=='byte_bound':monkeypatch.setattr(m,'MAX_BYTES',10)
    elif kind=='long_key':g.nonbonded_params.radius_table['x'*257]=1.
    elif kind=='overridden_manager':g.energies_sites=lambda:None
    with pytest.raises(ValueError):m.require_live_nonbonded_policy(g,baseline,**options)


def test_profile_rejects_changed_sources_and_platform(tmp_path,monkeypatch):
    from nasolve import cif_live_nonbonded_policy as m
    import hashlib
    path=tmp_path/'native.py';path.write_bytes(b'first native API')
    monkeypatch.setattr(m.importlib,'import_module',lambda name:SimpleNamespace(__file__=str(path)))
    profile=dict(profile_id=m.PROFILE_ID,system=m.platform.system(),machine=m.platform.machine(),
        modules={'fake':dict(size=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())})
    assert 'fake' in m._qualify_modules(profile)
    path.write_bytes(b'other native API')
    with pytest.raises(ValueError,match='source'):m._qualify_modules(profile)
    profile['system']='Unsupported'
    with pytest.raises(ValueError,match='platform'):m._qualify_modules(profile)


def test_module_import_does_not_require_a_native_installation():
    from nasolve import cif_live_nonbonded_policy as m
    assert m.POLICY_ID=='cif-live-nonbonded-policy-v1'
    # Type qualification is deferred, rather than importing cctbx for every user.
    assert hasattr(m._native_types,'cache_info')


@pytest.mark.parametrize('field', ['nonbonded_buffer','min_cubicle_edge'])
def test_required_search_settings_cannot_be_unresolved(case,field):
    m,g,options=case;setattr(g,field,None)
    with pytest.raises(ValueError):m.snapshot_live_nonbonded_policy(g,**options)
