"""Ordinary parent -> native-array -> existing guard controls; no refinement.

Synthetic ordinary records and tiny real MTZs establish software binding, not
FT chemistry, scientific acceptance or a full numbered execution.
"""
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch

from nasolve.refinement_mixed_parent import bind_mixed_parent, POLICY_ID
from nasolve.checkpoints import initialize_registry, _file_reference, registry_path, CheckpointError
from nasolve.refinement_parameter_scope import make_scope

try:
    from cctbx import crystal, miller
    from cctbx.array_family import flex
    from iotbx import pdb
    from phenix.programs.phenix_refine import Program
except ImportError:
    NATIVE = False
else:
    NATIVE = True


def atom(i, name, symbol):
    return (f'HETATM{i:5d} {name:>4s} UNK A{i:4d}    '
            f'{float(i):8.3f}{2.:8.3f}{3.:8.3f}{1.:6.2f}{200.:6.2f}          {symbol:>2s}  \n')


@unittest.skipUnless(NATIVE, 'Explicit native Phenix library required')
class NativeParent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root/'original/dataset/AutoMR/run_001'
        self.run.mkdir(parents=True)
        self.model = self.run/'prepared.pdb'
        source = ('CRYST1   20.000   21.000   22.000  90.00  90.00  90.00 P 1           1\n'
                  + atom(1,'N3','N') + atom(2,'O4','O') + atom(3,'HG','HG') + 'END\n').encode()
        self.model.write_bytes(source)
        self.source = source
        inp=pdb.input(source_info='synthetic parent',lines=source.decode().splitlines())
        self.hierarchy=inp.construct_hierarchy(); self.xs=inp.xray_structure_simple()
        self.xs.scatterers()[2].fp=-8.100181579589844
        from nasolve.refinement_parameter_native import capture_atoms
        scope=make_scope(source_model_sha256=sha256(source).hexdigest(),initial_atoms=capture_atoms(self.xs),
                         xyz_indices=[0,1,2],adp_groups=[[0],[1]],real_space=False)
        ms=miller.set(crystal_symmetry=self.xs.crystal_symmetry(),indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0)]),anomalous_flag=False)
        self.fo=miller.array(ms,data=flex.double([8.,10.,12.]),sigmas=flex.double([1.,2.,3.])).set_observation_type_xray_amplitude()
        self.flags=miller.array(ms,data=flex.int([1,0,1]))
        self.hl=miller.array(ms,data=flex.hendrickson_lattman([(1,2,3,4),(5,6,7,8),(9,10,11,12)]))
        data=self.run.parent.parent/'observations.mtz';phase=self.run/'AutoSol/overall_best_refine_data.mtz';phase.parent.mkdir()
        mtz=self.fo.as_mtz_dataset(column_root_label='F');mtz.add_miller_array(self.flags,column_root_label='FreeR_flag');mtz.mtz_object().write(str(data))
        self.hl.as_mtz_dataset(column_root_label='HL').mtz_object().write(str(phase))
        self.data,self.phase=data,phase
        self.restraints=[self.run/'pair.phil',self.run/'ligand.cif']
        for i,path in enumerate(self.restraints):path.write_text('synthetic opaque restraint '+str(i))
        report=dict(workflow='automr',inputs=dict(reflections=str(data),reflections_sha256=sha256(data.read_bytes()).hexdigest()),
            postmr=dict(status='POSTMR_READY',prepared_model=str(self.model),prepared_sha256=sha256(source).hexdigest()),
            autosol=dict(use_for_refinement=True,outputs=dict(refinement_data=str(phase),refinement_data_sha256=sha256(phase.read_bytes()).hexdigest(),
                         refinement_data_phase_labels=['HLA','HLB','HLC','HLD'])))
        (self.run/'report.json').write_text(json.dumps(report))
        initialize_registry(self.run)
        rp=registry_path(self.run);reg=json.loads(rp.read_text());reg['checkpoints'][0]['restraints']=[self.ref(p) for p in self.restraints];rp.write_text(json.dumps(reg))
        self.policy=self.run/'new-mixed-policy.params'
        self.policy.write_text('''data_manager {
 miller_array {
  file = "original-data"
  labels { name = "F,SIGF" }
  labels { name = "FreeR_flag" }
 }
 miller_array {
  file = "original-AutoSol"
  labels { name = "HLA,HLB,HLC,HLD" }
 }
 fmodel.xray_data {
  r_free_flags.test_flag_value = 0
  force_anomalous_flag_to_be_equal_to = False
  outliers_rejection = False
 }
}
refinement {
 main {
  target = mlhl
  use_experimental_phases = True
  nproc = 1
 }
 group_anomalous.find_automatically = False
 refine.anomalous_scatterers {
  group {
   selection = "not element Hg"
   f_prime = 0
   f_double_prime = 0
   refine = None
  }
  group {
   selection = "element Hg"
   f_prime = -8.100181579589844
   f_double_prime = 0
   refine = None
  }
 }
}
''')
        self.request=dict(schema_version=1,policy_id=POLICY_ID,checkpoint_id='postmr',
            parent=dict(model=self.ref(self.model),observations=self.ref(data),phases=self.ref(phase),restraints=[self.ref(p) for p in self.restraints],
                        report=self.ref(self.run/'report.json'),registry=self.ref(rp)),
            selectors=dict(data_labels=['F','SIGF'],free_label='FreeR_flag',test_flag_value=0,phase_labels=['HLA','HLB','HLC','HLD']),
            scope=scope,policy=dict(source=self.ref(self.policy),bindings=[dict(historical_file=old,source_reference=self.ref(path))
                for old,path in [('original-data',data),('original-AutoSol',phase)]]),
            runtime=dict(cell_roundoff_ulps=0,witness_native_normalization=False))
        self.request_path=self.run/'mixed-request.json'
        self.save()

    def ref(self,path):return _file_reference(path,self.run)
    def save(self):
        self.request_path.write_text(json.dumps(self.request,allow_nan=False))
        self.request_ref=self.ref(self.request_path)
    def bind(self):return bind_mixed_parent(self.run,request_reference=self.request_ref)

    def test_source_guard_refuses_wrong_model_before_installing_hooks(self):
        from nasolve.refinement_mixed_source_guard import SourceMixedGuard
        bound = self.bind()
        with patch('nasolve.refinement_mixed_runtime._native_bindings', side_effect=AssertionError('No hooks')):
            with self.assertRaisesRegex(ValueError, 'declared model'):
                SourceMixedGuard(bound._scope, bound._diffraction, source=bound._source+b'\n',
                    crystal=bound._crystal, recheck=bound._recheck, **bound._runtime)
            with self.assertRaisesRegex(ValueError, 'input recheck'):
                SourceMixedGuard(bound._scope, bound._diffraction, source=bound._source,
                    crystal=bound._crystal, recheck=None, **bound._runtime)

    def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def policy_change(self,old,new):
        text=self.policy.read_text();self.assertIn(old,text);self.policy.write_text(text.replace(old,new))
        self.request['policy']['source']=self.ref(self.policy);self.save()

    def scene(self):
        flags=self.flags.customized_copy(data=flex.bool([False,True,False]))
        fm=NS(xray_structure=self.xs,target_name='mlhl',f_obs=lambda:self.fo,r_free_flags=lambda:flags,hl_coeffs=lambda:self.hl)
        target=NS(manager=fm,core=NS(spacialization='hl',f_obs=self.fo,r_free_flags=flags,experimental_phases=self.hl))
        fm.alpha_beta=lambda:None;fm.target_functor=lambda **kw:target
        modes={name:name in ('individual_sites','group_adp') for name in ('individual_sites','torsion_angles','rigid_body','individual_adp','group_adp','tls','occupancies','group_anomalous')}
        modes.update(sites_individual=flex.bool([True]*3),adp_group=[flex.size_t([0]),flex.size_t([1])])
        model=NS(refinement_flags=NS(**modes),get_xray_structure=lambda:self.xs,get_anomalous_scatterer_groups=lambda:[],get_hierarchy=lambda:self.hierarchy)
        params=NS(refine=NS(strategy=['individual_sites','group_adp']),main=NS(nproc=1,number_of_macro_cycles=0,apply_overall_isotropic_scale_to_adp=False),bulk_solvent_and_scale=NS(apply_back_trace=False))
        class Driver:
            def initialize(self):pass
        class Stages:
            def call(self,*args):pass
        class XYZ:
            def evaluate(self):pass
        class B:
            def evaluate(self):pass
        driver=Driver();driver.model=model;driver.params=params;driver.fmodels=NS(fmodel_xray=lambda:fm,fmodel_neutron=lambda:None);driver.iparams=NS(refinement=NS(dry_run=True));driver.macro_cycle=0
        hooks={'initialize':(Driver,'initialize'),'stage':(Stages,'call'),'xyz':(XYZ,'evaluate'),'group_B':(B,'evaluate')}
        return driver,hooks,target

    def test_valid_parent_reaches_existing_guard_without_fit_or_writes(self):
        before=self.snapshot();bound=self.bind();driver,hooks,_=self.scene()
        originals={k:getattr(c,n) for k,(c,n) in hooks.items()}
        with patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(hooks,{'control':'synthetic dispatcher; native arrays'},lambda:None)):
            with bound.guard() as guard:
                driver.initialize();guard.finish(driver,dry_run=True)
        receipt=guard.summary();self.assertEqual(receipt['status'],'OBSERVED');self.assertTrue(receipt['bindings_restored'])
        self.assertEqual(receipt['parent_binding']['observations'],3);self.assertEqual(receipt['parent_binding']['free_count'],1)
        self.assertEqual(receipt['scientific_approval'],'NOT_RUN');self.assertEqual(before,self.snapshot())
        self.assertTrue(all(getattr(c,n) is originals[k] for k,(c,n) in hooks.items()))
        self.assertEqual(receipt['counts'].get('xyz',0),0)

    def test_relocation_resolves_declared_inputs_after_original_is_gone(self):
        original=self.root/'original';moved=self.root/'relocated';original.rename(moved)
        self.run=moved/'dataset/AutoMR/run_001'
        self.assertFalse(original.exists());bound=self.bind()
        self.assertIn(str(self.run.parent.parent/'observations.mtz').encode(),bound.policy)
        self.assertEqual(bound.receipt()['sources']['model']['sha256'],sha256(self.source).hexdigest())

    def test_incomplete_parent_refuses_before_source_read_or_hooks(self):
        (self.run/'report.json').unlink()
        with patch('nasolve.refinement_mixed_parent.read_source_arrays',side_effect=AssertionError('Too late')):
            with self.assertRaisesRegex(CheckpointError,'report|Report'):self.bind()

    def test_unapproved_phase_cannot_be_promoted_by_request(self):
        p=self.run/'report.json';report=json.loads(p.read_text());report['autosol']['use_for_refinement']=False;p.write_text(json.dumps(report))
        self.request['parent']['report']=self.ref(p);self.save()
        with self.assertRaisesRegex(ValueError,'approved'):self.bind()

    def test_wrong_declared_phase_order_refuses(self):
        self.request['selectors']['phase_labels']=['HLB','HLA','HLC','HLD'];self.save()
        with self.assertRaisesRegex(ValueError,'phase labels'):self.bind()

    def test_same_bytes_at_other_model_path_are_not_the_parent(self):
        other=self.run/'other.pdb';other.write_bytes(self.source);self.request['parent']['model']=self.ref(other);self.save()
        with self.assertRaisesRegex(ValueError,'parent model'):self.bind()

    def test_restraint_order_is_preserved(self):
        self.request['parent']['restraints'].reverse();self.save()
        with self.assertRaisesRegex(ValueError,'order'):self.bind()

    def test_forged_source_identity_or_scattering_is_not_admitted(self):
        from copy import deepcopy
        original=deepcopy(self.request['scope'])
        for key,value in [('label','not the source atom'),('scattering_type','Au'),('f_prime',2),('B',25),('Q',.5),('xyz',[9,9,9])]:
            with self.subTest(key=key):
                self.request['scope']=deepcopy(original);self.request['scope']['initial_atoms'][0][key]=value;self.save()
                with self.assertRaises(ValueError):self.bind()

    def test_wrong_child_science_refuses(self):
        original=self.policy.read_text()
        for old,new in [('target = mlhl','target = ml'),('use_experimental_phases = True','use_experimental_phases = False'),
                        ('nproc = 1','nproc = 2'),('test_flag_value = 0','test_flag_value = 1'),
                        ('outliers_rejection = False','outliers_rejection = True'),('f_double_prime = 0','f_double_prime = 2'),
                        ('refine = None','refine = *f_prime *f_double_prime')]:
            with self.subTest(new=new):
                self.policy.write_text(original);self.policy_change(old,new)
                with self.assertRaises(ValueError):self.bind()

    def test_saflags_refuse_before_native_read(self):
        self.request['selectors']['free_label']='SAflags';self.save()
        with patch('nasolve.refinement_mixed_parent.read_source_arrays',side_effect=AssertionError('No native read')):
            with self.assertRaisesRegex(ValueError,'SAflags'):self.bind()

    def test_changes_after_binding_refuse_before_hook_installation(self):
        bound=self.bind()
        for path in (self.policy,self.model,self.phase,self.data,self.run/'report.json',registry_path(self.run),self.request_path,*self.restraints):
            raw=path.read_bytes();path.write_bytes(raw+b'\n')
            with self.subTest(path=path.name),patch('nasolve.refinement_mixed_runtime._native_bindings',side_effect=AssertionError('No hooks')):
                with self.assertRaises((ValueError, CheckpointError)):bound.guard()
            path.write_bytes(raw)

    def test_active_crystal_is_bound_to_source_even_if_arrays_agree(self):
        bound=self.bind();driver,hooks,target=self.scene()
        changed=crystal.symmetry(unit_cell=(25,21,22,90,90,90),space_group_symbol='P1')
        self.fo=self.fo.customized_copy(crystal_symmetry=changed);self.hl=self.hl.customized_copy(crystal_symmetry=changed)
        flags=driver.fmodels.fmodel_xray().r_free_flags().customized_copy(crystal_symmetry=changed)
        driver.fmodels.fmodel_xray().r_free_flags=lambda:flags
        target.core.f_obs=self.fo;target.core.r_free_flags=flags;target.core.experimental_phases=self.hl
        # Source check occurs before the ordinary array-consistency check.
        with patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(hooks,{},lambda:None)):
            with self.assertRaisesRegex(ValueError,'admitted source'):
                with bound.guard() as guard:driver.initialize()
        self.assertTrue(guard.summary()['bindings_restored'])

    def test_changed_phase_values_at_runtime_refuse(self):
        bound=self.bind();driver,hooks,target=self.scene()
        with patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(hooks,{},lambda:None)):
            with self.assertRaises(ValueError):
                with bound.guard() as guard:
                    driver.initialize()
                    self.hl.data()[0]=(1.1,2,3,4)
                    guard.finish(driver,dry_run=True)
        self.assertTrue(guard.summary()['bindings_restored'])


    def test_derived_postmr_without_registry_remains_read_only(self):
        registry_path(self.run).unlink()
        self.request['parent']['registry']=None
        self.request['parent']['restraints']=[]
        self.save();before=self.snapshot()
        bound=self.bind()
        self.assertIsNone(bound.receipt()['sources']['registry'])
        self.assertEqual(self.snapshot(),before)
        self.assertFalse(registry_path(self.run).exists())

    def test_source_change_during_numerical_read_refuses(self):
        from nasolve.refinement_diffraction_source import read_source_arrays
        def changed(**kw):
            result=read_source_arrays(**kw)
            self.data.write_bytes(self.data.read_bytes()+b'changed')
            return result
        with patch('nasolve.refinement_mixed_parent.read_source_arrays',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed'):self.bind()

    def test_aliased_checkpoint_and_unusable_parent_refuse(self):
        p=registry_path(self.run);record=json.loads(p.read_text());record['bookmarks']['review-parent']='postmr';p.write_text(json.dumps(record))
        self.request['parent']['registry']=self.ref(p)
        self.request['checkpoint_id']='review-parent';self.save()
        with self.assertRaisesRegex(ValueError,'exact checkpoint'):self.bind()
        self.request['checkpoint_id']='postmr'
        p=registry_path(self.run);record=json.loads(p.read_text());record['checkpoints'][0]['usable']=False;p.write_text(json.dumps(record))
        self.request['parent']['registry']=self.ref(p);self.save()
        with self.assertRaisesRegex(ValueError,'not usable'):self.bind()

    def test_report_and_registry_source_disagreement_refuses_even_if_both_repinned(self):
        alternate=self.data.with_name('declared-other-data.mtz');alternate.write_bytes(self.data.read_bytes())
        p=self.run/'report.json';record=json.loads(p.read_text());record['inputs']['reflections']=str(alternate);p.write_text(json.dumps(record))
        self.request['parent']['report']=self.ref(p);self.save()
        with self.assertRaisesRegex(ValueError,'original run source'):self.bind()

    def test_hidden_child_input_refuses(self):
        self.policy.write_text(self.policy.read_text()+'\nrefinement.reference_model.file = "/undeclared/model.pdb"\n')
        self.request['policy']['source']=self.ref(self.policy);self.save()
        with self.assertRaisesRegex(ValueError,'dependency'):self.bind()

    def test_guard_entry_rechecks_after_guard_creation(self):
        bound=self.bind();guard=bound.guard();self.model.write_bytes(self.source+b'REMARK changed\n')
        with patch('nasolve.refinement_mixed_runtime._native_bindings',side_effect=AssertionError('No hooks')):
            with self.assertRaisesRegex(ValueError,'changed'):
                with guard:pass

    def test_finish_detects_parent_changes_and_restores_hooks(self):
        bound=self.bind();driver,hooks,_=self.scene()
        with patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(hooks,{},lambda:None)):
            with self.assertRaisesRegex(ValueError,'changed'):
                with bound.guard() as guard:
                    driver.initialize()
                    self.restraints[0].write_bytes(b'changed restraint')
                    guard.finish(driver,dry_run=True)
        self.assertTrue(guard.summary()['bindings_restored'])
        self.assertEqual(guard.summary()['status'],'FAILED')


if __name__=='__main__':unittest.main()
