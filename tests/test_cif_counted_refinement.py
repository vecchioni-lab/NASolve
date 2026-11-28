"""A prepared contribution owns the complete native driver lifetime once."""
from types import SimpleNamespace as NS
import pytest


def prepared_objects():
    main=NS(number_of_macro_cycles=1,max_number_of_iterations=10,nproc=1,
        random_seed=2679941,bulk_solvent_and_scale=False,ordered_solvent=False,
        ias=False,place_ions=None,simulated_annealing=False,
        apply_overall_isotropic_scale_to_adp=False,find_and_add_hydrogens=False,
        update_ss='off',target='ml',scattering_table='n_gaussian')
    weights=NS(fix_wxc=1.,wc=1.,optimize_xyz_weight=False,optimize_adp_weight=False,
        force_optimize_weights=False,shake_sites=False)
    params=NS(main=main,target_weights=weights,
        refine=NS(strategy=['individual_sites'],sites=NS(individual=['all'])),
        pdb_interpretation=NS(sort_atoms=False,restraints_library=NS(cdl=False,
            cdl_nucleotides=NS(enable=False))))
    return NS(params=params,model=NS(ncs_constraints_present=lambda:False),
        fmodels=NS(fmodel_neutron=lambda:None),neutron_refinement=False)


@pytest.fixture
def case(monkeypatch):
    from nasolve import cif_counted_refinement as phase
    objects=prepared_objects();events=[];owners=[]
    def run(refinement_objects, dry_run=False, call_back_handler=None):
        events.append('driver')
        assert owners[-1].active
        events.append('writer')
        return NS(model=refinement_objects.model,params=refinement_objects.params,
            fmodels=refinement_objects.fmodels,neutron_refinement=False,macro_cycle=1)
    driver=NS(run=run)
    def qualify(helper_sources):
        original=driver.run
        def verify(expected):
            if driver.run is not expected:raise ValueError('Native driver binding changed')
        return driver,verify
    monkeypatch.setattr(phase,'_native_driver',qualify)
    monkeypatch.setattr(phase,'_writer',lambda driver:None)
    class Owner:
        def __init__(self):self.active=False;self.closed=False;self.failed=False
        def __enter__(self):self.active=True;events.append('enter');return self
        def __exit__(self,kind,error,tb):
            self.active=False;self.closed=True;self.failed=kind is not None;events.append('exit')
        def statistics(self):return dict(closed=self.closed,poisoned=self.failed)
    def consume(model,**options):
        assert model is objects.model
        owner=Owner();owners.append(owner);return owner
    monkeypatch.setattr(phase.counted,'owner_from_prepared_pair_contribution',consume)
    def make():
        return phase.PreparedCountedRefinement(expected_scope=phase.refinement_scope(objects),
            factory_module=object(),factory_sources={},helper_sources={},packet={},
            model_bytes=b'bound source',expected_recipe_sha256='recipe',
            prepared={},expected_prepared_sha256='prepared')
    return NS(module=phase,objects=objects,driver=driver,original=run,make=make,
        events=events,owners=owners,monkeypatch=monkeypatch)


def test_owner_covers_constructor_through_writer_once(case):
    c=case;phase=c.make()
    with phase:
        result=c.driver.run(c.objects)
        assert result.model is c.objects.model
        assert c.events==['enter','driver','writer','exit']
    assert c.driver.run is c.original
    assert phase.statistics()['status']=='COMPLETE'
    assert phase.statistics()['owner']=={'closed':True,'poisoned':False}
    detached=phase.statistics();detached['status']='modified'
    assert phase.statistics()['status']=='COMPLETE'
    with pytest.raises(ValueError,match='reused'):phase.__enter__()


@pytest.mark.parametrize('defect',['no_entry','second_entry','dry_run','callback','model','scope'])
def test_refuses_wrong_or_repeated_phase_and_restores(case,defect):
    c=case;phase=c.make()
    if defect=='model':
        def replacement(refinement_objects,dry_run=False,call_back_handler=None):
            return NS(model=object(),params=refinement_objects.params)
        c.driver.run=replacement
    original=c.driver.run
    with pytest.raises(ValueError):
        with phase:
            if defect=='no_entry':pass
            elif defect=='scope':
                c.objects.params.main.random_seed+=1;c.driver.run(c.objects)
            elif defect=='second_entry':
                c.driver.run(c.objects);c.driver.run(c.objects)
            else:c.driver.run(c.objects,dry_run=defect=='dry_run',
                call_back_handler=(lambda:None) if defect=='callback' else None)
    assert c.driver.run is original and phase.statistics()['status']=='FAILED'
    assert all(o.closed for o in c.owners)


@pytest.mark.parametrize('interrupted',[False,True])
def test_foreign_driver_is_preserved_even_on_failure(case,interrupted):
    c=case;foreign=lambda *a,**k:None
    def replace(refinement_objects,dry_run=False,call_back_handler=None):
        c.driver.run=foreign
        if interrupted:raise RuntimeError('native failure')
        return NS(model=refinement_objects.model,params=refinement_objects.params,
            fmodels=refinement_objects.fmodels,neutron_refinement=False,macro_cycle=1)
    c.driver.run=replace;phase=c.make()
    with pytest.raises(RuntimeError if interrupted else ValueError):
        with phase:c.driver.run(c.objects)
    assert c.driver.run is foreign
    assert phase.statistics()['binding_restored'] is False
    assert phase.statistics()['status']=='FAILED'
    assert phase.statistics()['owner']['closed'] is True


def test_native_failure_retains_original_exception_and_owner_statistics(case):
    c=case
    def fail(refinement_objects,dry_run=False,call_back_handler=None):raise RuntimeError('native failure')
    c.driver.run=fail;phase=c.make()
    with pytest.raises(RuntimeError,match='native failure'):
        with phase:c.driver.run(c.objects)
    assert c.driver.run is fail
    assert phase.statistics()['owner']=={'closed':True,'poisoned':True}


def test_swallowed_native_failure_cannot_mark_phase_complete(case):
    c=case
    def fail(refinement_objects,dry_run=False,call_back_handler=None):raise RuntimeError('native failure')
    c.driver.run=fail;phase=c.make()
    with pytest.raises(ValueError,match='complete'):
        with phase:
            try:c.driver.run(c.objects)
            except RuntimeError:pass
    assert phase.statistics()['status']=='FAILED'
    assert phase.statistics()['error']=={'type':'RuntimeError','message':'native failure'}


@pytest.mark.parametrize('path,value',[
    ('main.nproc',2),('main.nproc',True),('main.number_of_macro_cycles',2),
    ('main.max_number_of_iterations',11),('main.random_seed',None),
    ('main.bulk_solvent_and_scale',True),('main.ordered_solvent',True),
    ('main.ias',True),('main.place_ions',True),('main.place_ions',False),('main.place_ions','Mg'),('main.simulated_annealing',True),
    ('main.find_and_add_hydrogens',True),('main.apply_overall_isotropic_scale_to_adp',True),
    ('main.update_ss','every_macro_cycle'),('main.target','ls'),
    ('target_weights.fix_wxc',None),('target_weights.fix_wxc',True),
    ('target_weights.wc',float('nan')),('target_weights.optimize_xyz_weight',True),
    ('target_weights.optimize_adp_weight',True),('target_weights.force_optimize_weights',True),
    ('target_weights.shake_sites',True),('refine.strategy',['individual_sites','individual_adp']),
    ('refine.sites.individual','chain A'),('refine.sites.individual',['chain A']),('refine.sites.individual','all'),('pdb_interpretation.sort_atoms',True),
    ('pdb_interpretation.restraints_library.cdl',True),
    ('pdb_interpretation.restraints_library.cdl_nucleotides.enable',True),
])
def test_actual_parameter_scope_refuses_unqualified_mechanics(path,value):
    from nasolve.cif_counted_refinement import refinement_scope
    objects=prepared_objects();node=objects.params;parts=path.split('.')
    for name in parts[:-1]:node=getattr(node,name)
    setattr(node,parts[-1],value)
    with pytest.raises(ValueError):refinement_scope(objects)


@pytest.mark.parametrize('defect',['missing','ncs','neutron'])
def test_incomplete_or_joint_prepared_model_is_not_admitted(defect):
    from nasolve.cif_counted_refinement import refinement_scope
    objects=prepared_objects()
    if defect=='missing':del objects.params.main.nproc
    elif defect=='ncs':objects.model.ncs_constraints_present=lambda:True
    else:objects.fmodels.fmodel_neutron=lambda:object()
    with pytest.raises(ValueError):refinement_scope(objects)


def test_native_preprocessed_disabled_ion_placement_is_none():
    from nasolve.cif_counted_refinement import refinement_scope
    objects=prepared_objects();objects.params.main.place_ions=None
    assert refinement_scope(objects)["place_ions"] is None


def test_native_all_sites_selection_is_a_sequence():
    from nasolve.cif_counted_refinement import refinement_scope
    objects=prepared_objects();objects.params.refine.sites.individual=["all"]
    assert refinement_scope(objects)["individual"] == ["all"]
