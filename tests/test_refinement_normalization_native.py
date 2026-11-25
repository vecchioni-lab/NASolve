"""Actual pinned native normalization hook; synthetic small diffraction control."""
import unittest
from types import SimpleNamespace as NS

try:
    from cctbx import xray,crystal,miller
    from cctbx.array_family import flex
    import mmtbx.f_model
except ImportError:
    NATIVE=False
else:
    NATIVE=True

from nasolve.refinement_diffraction_observation import make_reference,DiffractionReference,observe_diffraction
from nasolve.refinement_parameter_scope import ParameterScope,scope_digest
from nasolve.refinement_mixed_runtime import MixedRuntimeGuard,_native_bindings
from tests.test_refinement_parameter_scope import packet


@unittest.skipUnless(NATIVE,'Explicit native qualification required')
class NativeChecks(unittest.TestCase):
    def setUp(self):
        from nasolve.refinement_diffraction_observation import _capture
        cs=crystal.symmetry(unit_cell=(20,21,22,90,90,90),space_group_symbol='P1')
        xs=xray.structure(crystal_symmetry=cs,scatterers=flex.xray_scatterer([
            xray.scatterer(label='C1',scattering_type='C',site=(.1,.2,.3),u=.1)]))
        ms=miller.set(crystal_symmetry=cs,indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0)]),anomalous_flag=False)
        fo=miller.array(ms,data=flex.double([8,10,12]),sigmas=flex.double([1,2,3])).set_observation_type_xray_amplitude()
        flags=miller.array(ms,data=flex.bool([False,True,False]))
        hl=miller.array(ms,data=flex.hendrickson_lattman([(1,2,3,4),(5,6,7,8),(9,10,11,12)]))
        self.fm=mmtbx.f_model.manager(xray_structure=xs,f_obs=fo,r_free_flags=flags,abcd=hl,target_name='mlhl')
        obs,phases=_capture(self.fm.f_obs(),self.fm.r_free_flags(),self.fm.hl_coeffs())
        p=make_reference(observations=obs,phases=phases,data_sha256='a'*64,phases_sha256='b'*64)
        self.ref=DiffractionReference(p,expected_sha256=scope_digest(p))
        p=packet();self.scope=ParameterScope(p,expected_sha256=scope_digest(p))

    def guard(self):
        g=MixedRuntimeGuard(self.scope,self.ref,cell_roundoff_ulps=4,witness_native_normalization=True)
        # Synthetic driver identity only; this is not a native refinement test.
        g._driver=NS(fmodels=NS(fmodel_xray=lambda:self.fm))
        g.diffraction.check_order(self.fm.f_obs().indices(),initial=True)
        return g

    def test_actual_native_scale_is_witnessed_and_hooks_restore(self):
        g=self.guard();hooks,profile,verify=_native_bindings(normalization=True)
        originals={k:getattr(c,n) for k,(c,n) in hooks.items()}
        with self.assertRaisesRegex(RuntimeError,'synthetic stop'):
            with g:
                self.fm.apply_scale_k1_to_f_obs()
                observed=observe_diffraction(g.diffraction,self.fm,cell_roundoff_ulps=4)
                self.assertFalse(observed['exact_source_values'])
                with self.assertRaises(ValueError):observe_diffraction(self.ref,self.fm,cell_roundoff_ulps=4)
                raise RuntimeError('synthetic stop after actual native normalization')
        self.assertEqual(g.summary()['counts']['normalization'],1)
        self.assertEqual(len(g.summary()['native_normalization']['events']),1)
        self.assertTrue(g.summary()['bindings_restored'])
        self.assertTrue(all(getattr(c,n) is originals[k] for k,(c,n) in hooks.items()))
        verify()

    def test_native_hook_cannot_admit_another_manager(self):
        g=self.guard();g._driver.fmodels.fmodel_xray=lambda:object()
        with self.assertRaisesRegex(ValueError,'manager'):
            with g:self.fm.apply_scale_k1_to_f_obs()
        self.assertTrue(g.summary()['bindings_restored'])
        self.assertEqual(g.summary()['native_normalization']['events'],[])


if __name__=='__main__':unittest.main()
