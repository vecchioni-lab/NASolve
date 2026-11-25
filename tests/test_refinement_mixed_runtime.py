"""Guard lifecycle/actual-object controls; fake dispatcher, existing real checkers."""
import math
from types import SimpleNamespace as NS

import pytest

from nasolve.refinement_mixed_runtime import MixedRuntimeGuard
from nasolve.refinement_parameter_scope import ParameterScope, scope_digest
from tests.test_refinement_parameter_scope import packet, fake_xs
from tests.test_refinement_diffraction_observation import reference, sources


class Array:
    def __init__(self, data, sigmas=None, hl=False):
        self.values=data;self.errors=sigmas;self.hl=hl
    def indices(self):return [(0,0,1),(0,1,0),(1,0,0)]
    def data(self):return self.values
    def sigmas(self):return self.errors
    def anomalous_flag(self):return False
    def is_hendrickson_lattman_array(self):return self.hl
    def is_xray_amplitude_array(self):return self.errors is not None
    def unit_cell(self):return NS(parameters=lambda:(20,21,22,90,90,90))
    def space_group(self):return 'P1'


@pytest.fixture
def scene(monkeypatch):
    xs=fake_xs();xs.unit_cell=lambda:NS(orthogonalize=lambda v:v,parameters=lambda:(20,21,22,90,90,90));xs.space_group=lambda:'P1'
    fo=Array([8.,10.,12.],[1.,2.,3.]);flags=Array([False,True,False]);hl=Array([r[1] for r in sources()[1]['rows']],hl=True)
    fm=NS(xray_structure=xs,target_name='mlhl',f_obs=lambda:fo,r_free_flags=lambda:flags,hl_coeffs=lambda:hl)
    functor=NS(manager=fm,core=NS(spacialization='hl',f_obs=fo,r_free_flags=flags,experimental_phases=hl))
    fm.alpha_beta=lambda:None;fm.target_functor=lambda **kw:functor
    fmodels=NS(fmodel_xray=lambda:fm,fmodel_neutron=lambda:None,target_functor_xray=functor)
    modes={name:name in ('individual_sites','group_adp') for name in ('individual_sites','torsion_angles','rigid_body','individual_adp','group_adp','tls','occupancies','group_anomalous')}
    modes.update(sites_individual=NS(iselection=lambda:[0,1,2]),adp_group=[[0],[1]])
    model=NS(refinement_flags=NS(**modes),get_xray_structure=lambda:xs,get_anomalous_scatterer_groups=lambda:[],get_hierarchy=lambda:NS(atoms=lambda:[NS(id_str=lambda a=a:a.label) for a in xs.scatterers()]))
    params=NS(refine=NS(strategy=['individual_sites','group_adp']),main=NS(nproc=1,number_of_macro_cycles=1,apply_overall_isotropic_scale_to_adp=False),bulk_solvent_and_scale=NS(apply_back_trace=False))
    class Driver:
        def write_before_run_outputs(self):return 'initialized'
    class Macro:
        def call(self,func,prefix):
            if self.tt.status(func):return func(prefix=prefix)
    class XYZ:
        def compute_target(self):
            if self.action:self.action()
            return 17
    class ADP:
        def get_tg(self):
            if self.action:self.action()
            return 19
    driver=Driver();driver.model=model;driver.params=params;driver.fmodels=fmodels;driver.macro_cycle=1;driver.iparams=NS(refinement=NS(dry_run=False))
    macro=Macro();macro.model=model;macro.params=params;macro.fmodels=fmodels;macro.tt=NS(status=lambda f:True)
    xyz=XYZ();xyz.refine_xyz=True;xyz.refine_adp=False;xyz.xray_structure=xs;xyz.fmodels=fmodels;xyz.action=None
    group=ADP();group.refine_adp=True;group.refine_occ=False;group.selections=[[0],[1]];group.x=[0.,0.];group.fmodel=fm;group.target_functor=functor;group.action=None
    hooks={'initialize':(Driver,'write_before_run_outputs'),'stage':(Macro,'call'),'xyz':(XYZ,'compute_target'),'group_B':(ADP,'get_tg')}
    monkeypatch.setattr('nasolve.refinement_mixed_runtime._native_bindings',lambda:(hooks,{'profile_id':'synthetic-dispatch-only'},lambda:None))
    p=packet();scope=ParameterScope(p,expected_sha256=scope_digest(p))
    return NS(xs=xs,fo=fo,flags=flags,hl=hl,fm=fm,functor=functor,driver=driver,macro=macro,xyz=xyz,group=group,scope=scope,hooks=hooks,guard=lambda:MixedRuntimeGuard(scope,reference()))


def step(s):
    s.macro.call(lambda prefix:s.xyz.compute_target(),'xyz')
    s.macro.call(lambda prefix:s.group.get_tg(),'group')


def test_declared_mixed_parameters_and_source_values_survive_dispatch(scene):
    s=scene;g=s.guard();before={k:getattr(c,n) for k,(c,n) in s.hooks.items()}
    with g:
        s.driver.write_before_run_outputs()
        s.xyz.action=lambda:setattr(s.xs.scatterers()[2],'site',[2.2,2.,3.])
        s.group.action=lambda:setattr(s.xs.scatterers()[0],'u_iso',250/(8*math.pi**2))
        step(s);g.finish(s.driver,dry_run=False)
    r=g.summary();assert r['status']=='OBSERVED' and r['bindings_restored']
    assert r['counts']['xyz']==r['counts']['group_B']==1
    assert r['final']['state']['max_B_change_A2']==pytest.approx(80)
    assert all(getattr(c,n) is before[k] for k,(c,n) in s.hooks.items())


@pytest.mark.parametrize('kind', ['B','Q','f_prime','f_double_prime','XYZ','flags','phases','group_membership','xyz_flags'])
def test_illegal_changes_at_target_are_refused_and_latched(scene,kind):
    s=scene;g=s.guard()
    def illegal():
        atom=s.xs.scatterers()[3]
        if kind=='B':atom.u_iso+=1
        elif kind=='Q':atom.occupancy-=.1
        elif kind=='f_prime':atom.fp+=1
        elif kind=='f_double_prime':atom.fdp+=1
        elif kind=='XYZ':atom.site=[5.,2.,3.]
        elif kind=='flags':s.flags.values[0]=True
        elif kind=='phases':s.hl.values[0][0]+=1
        elif kind=='group_membership':s.group.selections=[[0,1]]
        elif kind=='xyz_flags':atom.flags.grad_site=lambda:True
    with pytest.raises(ValueError):
        with g:
            s.driver.write_before_run_outputs()
            s.xyz.action=illegal
            try:step(s)
            except ValueError:pass
            g.finish(s.driver,dry_run=False)
    assert g.summary()['status']=='FAILED' and g.summary()['bindings_restored']


def test_body_exception_restores_hooks_without_success(scene):
    s=scene;g=s.guard()
    with pytest.raises(KeyboardInterrupt):
        with g:
            s.driver.write_before_run_outputs();raise KeyboardInterrupt('interrupt')
    assert g.summary()['status']=='FAILED' and g.summary()['bindings_restored']


def test_no_initialization_no_finish_and_no_required_target_calls_refuse(scene):
    for mode in ('no_initialize','no_finish','no_targets'):
        g=scene.guard()
        with pytest.raises(ValueError):
            with g:
                if mode!='no_initialize':scene.driver.write_before_run_outputs()
                if mode!='no_finish':g.finish(scene.driver,dry_run=False)
        assert g.summary()['status']=='FAILED' and g.summary()['bindings_restored']


def test_dry_scope_requires_no_optimizer_evaluations(scene):
    s=scene;s.driver.iparams.refinement.dry_run=True;s.driver.macro_cycle=0;g=s.guard()
    with g:s.driver.write_before_run_outputs();g.finish(s.driver,dry_run=True)
    assert g.summary()['dry_run'] and g.summary()['counts'].get('xyz',0)==0
    bad=s.guard()
    with pytest.raises(ValueError):
        with bad:s.driver.write_before_run_outputs();step(s);bad.finish(s.driver,dry_run=True)


def test_nested_guards_and_reuse_refuse(scene):
    s=scene;g=s.guard()
    with g:
        s.driver.write_before_run_outputs();step(s)
        with pytest.raises(ValueError):
            with s.guard():pass
        g.finish(s.driver,dry_run=False)
    with pytest.raises(ValueError):
        with g:pass


def test_changed_binding_is_reported_without_overwriting_foreign_code(scene):
    s=scene;g=s.guard();cls,name=s.hooks['xyz'];original=getattr(cls,name);foreign=lambda self:0
    try:
        with pytest.raises(ValueError):
            with g:
                s.driver.write_before_run_outputs();setattr(cls,name,foreign);g.finish(s.driver,dry_run=False)
        assert getattr(cls,name) is foreign and not g.summary()['bindings_restored']
    finally:setattr(cls,name,original)


def test_real_space_and_multi_process_are_explicitly_outside_v1(scene):
    p=packet();p['real_space']=True
    with pytest.raises(ValueError,match='real-space'):
        MixedRuntimeGuard(ParameterScope(p,expected_sha256=scope_digest(p)),reference())
    g=scene.guard();scene.driver.params.main.nproc=2
    with pytest.raises(ValueError,match='single-process'):
        with g:scene.driver.write_before_run_outputs()
    assert g.summary()['bindings_restored']


def test_summary_is_compact_and_detached(scene):
    s=scene;g=s.guard()
    with g:
        s.driver.write_before_run_outputs()
        for _ in range(100):step(s)
        g.finish(s.driver,dry_run=False)
    import json
    r=g.summary();assert r['counts']['xyz']==100 and len(json.dumps(r))<5000
    r['counts']['xyz']=0;assert g.summary()['counts']['xyz']==100


def test_roundoff_policy_is_explicit_and_separately_versioned(scene):
    strict=scene.guard();assert strict.summary()['policy_id'].endswith('-v1')
    tolerant=MixedRuntimeGuard(scene.scope,reference(),cell_roundoff_ulps=4)
    assert tolerant.summary()['policy_id'].endswith('-v2')
    assert tolerant.summary()['unit_cell_roundoff_ulps']==4
    for value in [True,1,8,4.0]:
        with pytest.raises(ValueError):MixedRuntimeGuard(scene.scope,reference(),cell_roundoff_ulps=value)


def test_roundoff_rule_is_applied_at_native_target_boundaries(scene):
    s=scene
    cell=(20.,21.,22.,90.,90.,math.nextafter(math.nextafter(90.,math.inf),math.inf))
    s.flags.unit_cell=lambda:NS(parameters=lambda:cell)
    g=MixedRuntimeGuard(s.scope,reference(),cell_roundoff_ulps=4)
    with g:
        s.driver.write_before_run_outputs();step(s);g.finish(s.driver,dry_run=False)
    assert g.summary()['status']=='OBSERVED'
    g=MixedRuntimeGuard(s.scope,reference(),cell_roundoff_ulps=4)
    with pytest.raises(ValueError):
        with g:
            s.driver.write_before_run_outputs()
            s.group.action=lambda:s.fo.values.__setitem__(0,8.00000001)
            step(s)
    assert g.summary()['status']=='FAILED' and g.summary()['bindings_restored']
