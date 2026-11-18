"""Explicit counted ownership through one qualified native refinement cycle.

Enter this lifetime before the existing v4 run_compatible_refinement call. The
caller owns processes, the actual preflight seal, immutable outputs and receipts.
This helper never runs a program, writes evidence, chooses providers or installs
the correction kernel. Its statistics are observations, not runtime authority.
"""
import importlib
import inspect
from pathlib import Path

from . import cif_counted_contribution as counted
from . import cif_refinement_runtime as runtime
from . import cif_refinement_output as output

POLICY_ID = 'prepared-counted-refinement-cycle-v1'
LONG_POLICY_ID = 'prepared-counted-refinement-cycle-v2'


def refinement_scope(refined, *, scope_policy=POLICY_ID):
    """Read actual parameters for the initially qualified one-cycle protocol.

    The unchanged v1 scope admits a configured cap of 1–10. Explicit v2 uses a
    configured cap of exactly 100 and seed 1; convergence/error may stop earlier.
    Unit fixed weights, one process, all-site coordinates and no changing targets
    remain deliberate control bounds, not recommended scientific defaults. Read
    both returned preflight and fresh actual driver objects; CLI strings alone
    cannot establish this scope.
    """
    need=counted._need
    need(scope_policy in (POLICY_ID,LONG_POLICY_ID), 'Unknown counted refinement scope')
    longer=scope_policy==LONG_POLICY_ID
    try:
        p=refined.params; m=p.main; w=p.target_weights
        need(type(m.number_of_macro_cycles) is int and m.number_of_macro_cycles==1
             and type(m.max_number_of_iterations) is int
             and (m.max_number_of_iterations==100 if longer else 1<=m.max_number_of_iterations<=10)
             and type(m.nproc) is int and m.nproc==1 and type(m.random_seed) is int
             and (not longer or m.random_seed==1),
             'Unqualified counted cycle/process/iteration controls')
        need(all(type(v) in (int,float) and v==1. for v in (w.fix_wxc,w.wc)),
             'Require qualified fixed unit counted weights')
        need(all(v is False for v in (m.bulk_solvent_and_scale,m.ordered_solvent,
             m.ias,m.simulated_annealing,m.apply_overall_isotropic_scale_to_adp,
             m.find_and_add_hydrogens,w.optimize_xyz_weight,w.optimize_adp_weight,
             w.force_optimize_weights,w.shake_sites,p.pdb_interpretation.sort_atoms,
             p.pdb_interpretation.restraints_library.cdl,
             p.pdb_interpretation.restraints_library.cdl_nucleotides.enable)),
             'Changing targets, identity, weights or parallel phases are outside counted scope')
        # Native preprocess normalizes disabled ion placement to None.
        need(m.place_ions is None,'Require native disabled ion-placement state')
        need(m.update_ss=='off' and m.target=='ml' and m.scattering_table=='n_gaussian'
             and list(p.refine.strategy)==['individual_sites'] and list(p.refine.sites.individual)==['all'],
             'Require qualified all-site coordinate refinement')
        need(refined.model.ncs_constraints_present() is False
             and refined.fmodels.fmodel_neutron() is None and refined.neutron_refinement is False,
             'NCS or neutron refinement is outside counted scope')
        return dict(policy_id=scope_policy,cycles=m.number_of_macro_cycles,
            iterations=m.max_number_of_iterations,nproc=m.nproc,seed=m.random_seed,
            fix_wxc=float(w.fix_wxc),wc=float(w.wc),strategy=['individual_sites'],
            individual=['all'],target=m.target,scattering_table=m.scattering_table,place_ions=None)
    except (AttributeError,TypeError) as exc:
        raise ValueError('Incomplete prepared refinement scope') from exc


def _native_driver(helper_sources):
    counted._need(runtime.POLICY_ID=='explicit-native-parallelity-refinement-v4',
                  'Counted phase requires the existing v4 runtime')
    sources=counted._Sources({'cif_refinement_runtime':runtime},
        {'cif_refinement_runtime':helper_sources.get('cif_refinement_runtime')})
    _,_,_,_,verify=runtime._native_runtime()
    driver=importlib.import_module('phenix.refinement.driver');klass=driver.refine
    compiled=compile(Path(driver.__file__).read_bytes(),str(driver.__file__),'exec',dont_inherit=True)
    attributes=[(klass,name,getattr(klass,name)) for name in
        ('__init__','run','write_before_run_outputs')]
    functions=[counted._function(driver,fn,compiled) for fn in
        (driver.run,klass.write_after_run_outputs,*(v for _,_,v in attributes))]
    def check(expected):
        verify();sources.check()
        counted._need(driver.run is expected and driver.refine is klass
            and all(getattr(obj,name) is value for obj,name,value in attributes)
            and all(fn.__code__ is code and fn.__defaults__==defaults
                and fn.__kwdefaults__==kwdefaults and not fn.__closure__
                for fn,code,defaults,kwdefaults in functions), 'Native driver binding changed')
    check(driver.run)
    return driver,check


def _writer(driver):
    """Recognize v4's existing writer wrapper without installing a second one."""
    writer=driver.refine.write_after_run_outputs
    counted._need(getattr(writer,'__qualname__',None)=='synchronized_outputs.<locals>.write',
                  'Require existing synchronized native final writer')
    counted._function(output,writer,compile(Path(output.__file__).read_bytes(),
        str(output.__file__),'exec',dont_inherit=True))
    closure=dict(zip(writer.__code__.co_freevars,(c.cell_contents for c in writer.__closure__ or ())))
    original=closure.get('original')
    counted._need(getattr(original,'__qualname__',None)=='refine.write_after_run_outputs',
                  'Foreign original native final writer')
    counted._function(driver,original,compile(Path(driver.__file__).read_bytes(),
        str(driver.__file__),'exec',dont_inherit=True))
    return writer


class PreparedCountedRefinement:
    """Fresh one-shot lifetime around unchanged v4 native execution.

    Supply the authenticated stronger preparation and the scope read from actual
    preflight. The enclosing execution owner must bind those to request/parent
    lineage; matching data/digests alone is not that authority. A new process gets
    a new instance. No successful inspection or exception allows in-place retry.
    """
    def __init__(self, *, expected_scope, factory_module, factory_sources, helper_sources,
                 packet, model_bytes, expected_recipe_sha256, prepared, expected_prepared_sha256, capture_pair_geometry=False,
                 scope_policy=POLICY_ID):
        counted._need(type(capture_pair_geometry) is bool, 'Require explicit geometry capture choice')
        counted._need(scope_policy in (POLICY_ID,LONG_POLICY_ID), 'Unknown counted refinement scope')
        counted._need(scope_policy!=LONG_POLICY_ID or capture_pair_geometry,
                      'Longer counted scope requires final pair geometry capture')
        self._scope_policy=scope_policy
        self._capture_pair_geometry=capture_pair_geometry;self._pair_geometry=None
        self._scope=counted._detached(expected_scope)
        self._options=dict(factory_module=factory_module,
            **counted._detached(dict(factory_sources=factory_sources,helper_sources=helper_sources,
                packet=packet,expected_recipe_sha256=expected_recipe_sha256,
                prepared=prepared,expected_prepared_sha256=expected_prepared_sha256)),
            model_bytes=bytes(model_bytes))
        self._record=dict(policy_id=scope_policy,status='NEW',driver_entries=0,
            binding_restored=True,owner=None,runtime_authority=False,scientific_acceptance=False)
        self._driver=None;self._original=None;self._owner=None;self._adapter=self._run
        self._completed=False;self._closed=False

    def __enter__(self):
        counted._need(self._record['status']=='NEW' and not self._closed,
                      'Counted refinement lifetime cannot be reused')
        self._record['status']='RUNNING'
        try:
            self._driver,self._verify=_native_driver(self._options['helper_sources'])
            self._original=self._driver.run
            self._signature=inspect.signature(self._original)
            self._driver.run=self._adapter;self._record['binding_restored']=False
            return self
        except BaseException as exc:
            self._closed=True;self._failed(exc);raise

    def _failed(self,exc):
        self._record['status']='FAILED'
        # A later close refusal must retain the original native failure cause.
        self._record.setdefault('error',dict(type=type(exc).__name__,message=str(exc)))

    def _run(self,*args,**kwargs):
        try:
            self._verify(self._adapter)
            self._record['driver_entries']+=1
            counted._need(not self._closed and self._record['driver_entries']==1,
                          'Require exactly one fresh native driver entry')
            bound=self._signature.bind(*args,**kwargs);bound.apply_defaults()
            counted._need(bound.arguments['dry_run'] is False
                and bound.arguments.get('call_back_handler') is None,
                'Require actual refinement without caller callbacks')
            objects=bound.arguments['refinement_objects'];model=objects.model
            scope=refinement_scope(objects,scope_policy=self._scope_policy)
            counted._need(counted._digest(scope)==counted._digest(self._scope),
                          'Actual refinement scope differs from prepared scope')
            writer=_writer(self._driver)
            self._owner=counted.owner_from_prepared_pair_contribution(model,**self._options)
            with self._owner:
                refined=self._original(*args,**kwargs)
                counted._need(refined.model is model and objects.model is model,
                              'Native refinement replaced the prepared model')
                counted._need(refinement_scope(refined,scope_policy=self._scope_policy)==scope and refined.macro_cycle==scope['cycles'],
                              'Native refinement did not complete the prepared scope')
                self._verify(self._adapter)
                counted._need(_writer(self._driver) is writer,'Native final writer binding changed')
            if self._capture_pair_geometry:
                from .cif_counted_geometry import capture_closed_pair_geometry
                self._pair_geometry=capture_closed_pair_geometry(self._owner,
                    prepared=self._options['prepared'],
                    expected_prepared_sha256=self._options['expected_prepared_sha256'])
                self._record['pair_geometry_capture']=dict(status='CAPTURED',
                    record_sha256=counted._digest(self._pair_geometry))
            self._completed=True
            return refined
        except BaseException as exc:
            self._failed(exc);raise
        finally:
            if self._owner is not None:self._record['owner']=self._owner.statistics()

    def __exit__(self,kind,error,tb):
        try:
            if kind is not None:self._failed(error)
            else:
                counted._need(self._completed and self._record['status']=='RUNNING',
                              'Counted refinement lifetime did not complete')
                self._verify(self._adapter)
                self._record['status']='COMPLETE'
        except BaseException as exc:
            self._failed(exc);raise
        finally:
            if self._driver.run is self._adapter:self._driver.run=self._original
            self._record['binding_restored']=self._driver.run is self._original
            self._closed=True
        return False

    def statistics(self):
        return counted._detached(self._record)

    def pair_geometry_capture(self):
        counted._need(self._capture_pair_geometry and self._closed
                      and self._record['status']=='COMPLETE' and self._pair_geometry is not None,
                      'No completed requested pair geometry capture')
        return counted._detached(self._pair_geometry)
