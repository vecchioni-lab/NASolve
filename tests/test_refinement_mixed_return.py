"""Post-exit transfer controls; native arrays, controlled dispatcher, no fits."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_refinement_mixed_parent as fixtures


@unittest.skipUnless(fixtures.NATIVE, 'Explicit native Phenix library required')
class ReturnChecks(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.NativeParent()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.bound=self.fixture.bind()
        self.driver,self.hooks,self.target=self.fixture.scene()
        self.callbacks=patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(self.hooks,{'control':'synthetic dispatcher'},lambda:None))
        self.callbacks.start();self.addCleanup(self.callbacks.stop)

    def complete(self):
        with self.bound.guard() as guard:
            self.driver.initialize();guard.finish(self.driver,dry_run=True)
        return guard

    def test_exact_return_after_exit_is_read_only_and_detached(self):
        guard=self.complete();before=self.fixture.snapshot();summary=guard.summary()
        result=self.bound.observe_return(self.driver,guard=guard)
        self.assertEqual(result['status'],'OBSERVED_NOT_ADOPTED')
        self.assertEqual(result['diffraction']['observations'],3)
        self.assertEqual(result['diffraction']['free_count'],1)
        self.assertFalse(result['checkpoint_adoption']);self.assertEqual(result['scientific_approval'],'NOT_RUN')
        self.assertEqual(result['written_output'],'SEPARATE_OWNER_REQUIRED')
        self.assertEqual(before,self.fixture.snapshot());self.assertEqual(summary,guard.summary())
        result['sources']['model']['sha256']='0'*64
        self.assertNotEqual(result,self.bound.observe_return(self.driver,guard=guard))

    def test_unfinished_or_still_active_guard_refuses(self):
        guard=self.bound.guard()
        with self.assertRaisesRegex(ValueError,'completed guard exit'):
            self.bound.observe_return(self.driver,guard=guard)
        with guard:
            self.driver.initialize();guard.finish(self.driver,dry_run=True)
            with self.assertRaisesRegex(ValueError,'completed guard exit'):
                self.bound.observe_return(self.driver,guard=guard)
        self.bound.observe_return(self.driver,guard=guard)

    def test_different_driver_or_parent_refuses(self):
        guard=self.complete()
        with self.assertRaisesRegex(ValueError,'exact observed driver'):
            self.bound.observe_return(SimpleNamespace(),guard=guard)
        other=self.fixture.bind()
        with self.assertRaisesRegex(ValueError,'exact parent-bound guard'):
            other.observe_return(self.driver,guard=guard)

    def test_allowed_during_fit_motion_is_not_allowed_after_completed_return(self):
        import math
        guard=self.complete();atom=self.fixture.xs.scatterers()[0];original_site=tuple(atom.site);original_u=atom.u_iso
        for name in ('XYZ','B'):
            with self.subTest(name=name):
                if name=='XYZ':atom.site=tuple(v+.001 for v in original_site)
                else:atom.u_iso=original_u+1/(8*math.pi**2)
                with self.assertRaisesRegex(ValueError,'completed guard state'):
                    self.bound.observe_return(self.driver,guard=guard)
                atom.site=original_site;atom.u_iso=original_u
        self.bound.observe_return(self.driver,guard=guard)

    def test_changed_native_phase_or_flags_after_exit_refuse(self):
        guard=self.complete();flags=self.driver.fmodels.fmodel_xray().r_free_flags()
        before=tuple(self.fixture.hl.data()[0]);self.fixture.hl.data()[0]=(1.1,2,3,4)
        with self.assertRaises(ValueError):self.bound.observe_return(self.driver,guard=guard)
        self.fixture.hl.data()[0]=before
        flags.data()[0]=True
        with self.assertRaises(ValueError):self.bound.observe_return(self.driver,guard=guard)
        flags.data()[0]=False
        self.bound.observe_return(self.driver,guard=guard)

    def test_parent_phase_and_restraint_files_stay_bound_after_exit(self):
        guard=self.complete()
        for path in (self.fixture.phase,self.fixture.data,self.fixture.model,*self.fixture.restraints,self.fixture.run/'report.json'):
            raw=path.read_bytes();path.write_bytes(raw+b'changed')
            with self.subTest(path=path.name),self.assertRaises((ValueError,fixtures.CheckpointError)):
                self.bound.observe_return(self.driver,guard=guard)
            path.write_bytes(raw)
        self.bound.observe_return(self.driver,guard=guard)

    def test_changed_callback_after_exit_refuses_without_overwriting_it(self):
        guard=self.complete();cls,name=self.hooks['xyz'];original=getattr(cls,name);foreign=lambda *args:None
        setattr(cls,name,foreign)
        try:
            with self.assertRaisesRegex(ValueError,'callback changed'):
                self.bound.observe_return(self.driver,guard=guard)
            self.assertIs(getattr(cls,name),foreign)
        finally:setattr(cls,name,original)

    def test_failure_inside_guard_cannot_be_received_as_completed(self):
        with self.assertRaises(RuntimeError):
            with self.bound.guard() as guard:
                self.driver.initialize();raise RuntimeError('controlled failure')
        with self.assertRaisesRegex(ValueError,'completed guard exit'):
            self.bound.observe_return(self.driver,guard=guard)
        self.assertTrue(guard.summary()['bindings_restored'])


    def test_post_exit_reuses_explicit_normalization_witness(self):
        # Controlled normalization callback, not a Phenix fit or new event claim.
        from cctbx.array_family import flex
        self.fixture.request['runtime']=dict(cell_roundoff_ulps=4,witness_native_normalization=True)
        self.fixture.save();self.bound=self.fixture.bind()
        fixture,target=self.fixture,self.target
        class Normalizer(SimpleNamespace):
            def normalize(self):
                fixture.fo=fixture.fo.customized_copy(data=fixture.fo.data()/2,sigmas=fixture.fo.sigmas()/2)
                target.core.f_obs=fixture.fo
        fm=Normalizer(**vars(self.driver.fmodels.fmodel_xray()))
        fm.twin_law=None
        fc=fixture.fo.customized_copy(data=flex.complex_double([4,5,6]),sigmas=None)
        fm.f_model=lambda:fc;fm.r_work=lambda:.3;fm.r_free=lambda:.34
        target.manager=fm;self.driver.fmodels.fmodel_xray=lambda:fm
        self.hooks['normalization']=(Normalizer,'normalize')
        with self.bound.guard() as guard:
            self.driver.initialize();fm.normalize();guard.finish(self.driver,dry_run=True)
        result=self.bound.observe_return(self.driver,guard=guard)
        self.assertFalse(result['diffraction']['exact_source_values'])
        self.assertEqual(result['diffraction']['normalization_events'],1)
        fixture.fo.data()[0]+=1e-8
        with self.assertRaises(ValueError):self.bound.observe_return(self.driver,guard=guard)


if __name__=='__main__':unittest.main()
