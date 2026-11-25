"""Indexed diffraction handoff checks; native cases run explicitly in Phenix."""
import copy
import hashlib
import json
from types import SimpleNamespace
import unittest

from nasolve.refinement_diffraction_observation import (
    DiffractionReference, make_reference, observe_diffraction, observe_target,
)
from nasolve.refinement_parameter_scope import scope_digest


def signature(rows, observations=False):
    result=dict(rows=rows,count=len(rows),hash=scope_digest(rows))
    if observations:result.update(anomalous=False,free_count=sum(r[3] for r in rows))
    return result


def sources():
    obs=signature([[[0,0,1],8.,1.,False],[[0,1,0],10.,2.,True],[[1,0,0],12.,3.,False]],True)
    hl=signature([[[0,0,1],[1.,2.,3.,4.]],[[0,1,0],[5.,6.,7.,8.]],[[1,0,0],[9.,10.,11.,12.]]])
    return obs,hl


def packet():
    obs,hl=sources()
    return make_reference(observations=obs,phases=hl,data_sha256='a'*64,phases_sha256='b'*64)


def reference():
    p=packet();return DiffractionReference(p,expected_sha256=scope_digest(p))


class PureChecks(unittest.TestCase):
    def test_exact_state(self):
        obs,hl=sources();r=reference().state(obs,hl,target='mlhl')
        self.assertEqual((r['observations'],r['free_count'],r['phases']),(3,1,3))
        self.assertTrue(r['exact_source_values'])

    def test_detached_input_and_return(self):
        p=packet();ref=DiffractionReference(p,expected_sha256=scope_digest(p))
        p['observations']['rows'][0][1]=100
        returned=ref.record();returned['phases']['rows'][0][1][0]=100
        ref.state(*sources(),target='mlhl')

    def test_bad_digest(self):
        with self.assertRaises(ValueError):DiffractionReference(packet(),expected_sha256='0'*64)

    def test_extra_fields_and_version(self):
        for name,value in [('unexpected',1),('schema_version',True),('policy_id','old')]:
            p=packet();p[name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):DiffractionReference(p,expected_sha256=scope_digest(p))

    def test_bad_source_checksum(self):
        for h in ['a'*63,'A'*64,None]:
            with self.subTest(h=h),self.assertRaises(ValueError):make_reference(observations=sources()[0],phases=sources()[1],data_sha256=h,phases_sha256='b'*64)

    def test_no_common_scale_permission(self):
        obs,hl=sources()
        for row in obs['rows']:row[1]*=2;row[2]*=2
        obs['hash']=scope_digest(obs['rows'])
        with self.assertRaisesRegex(ValueError,'exact'):reference().state(obs,hl,target='mlhl')

    def test_changed_amplitudes_sigmas_and_flags(self):
        for field,value in [(1,9.),(2,1.1),(3,True)]:
            obs,hl=sources();obs['rows'][0][field]=value
            obs=signature(obs['rows'],True)
            with self.subTest(field=field),self.assertRaises(ValueError):reference().state(obs,hl,target='mlhl')

    def test_changed_phases(self):
        obs,hl=sources();hl['rows'][0][1][0]+=0.000001;hl=signature(hl['rows'])
        with self.assertRaises(ValueError):reference().state(obs,hl,target='mlhl')

    def test_bad_phase_coverage(self):
        obs,hl=sources();hl=signature(hl['rows'][:-1])
        with self.assertRaises(ValueError):make_reference(observations=obs,phases=hl,data_sha256='a'*64,phases_sha256='b'*64)

    def test_bad_target(self):
        for target in ['ml',None,'MLHL']:
            with self.subTest(target=target),self.assertRaises(ValueError):reference().state(*sources(),target=target)

    def test_rejects_anomalous_state(self):
        obs,hl=sources();obs['anomalous']=True
        with self.assertRaises(ValueError):reference().state(obs,hl,target='mlhl')

    def test_nonpositive_observations(self):
        for field,value in [(1,0.),(1,-1.),(2,0.),(2,-1.)]:
            obs,hl=sources();obs['rows'][0][field]=value;obs=signature(obs['rows'],True)
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):make_reference(observations=obs,phases=hl,data_sha256='a'*64,phases_sha256='b'*64)

    def test_duplicates_and_order(self):
        for rows in [sources()[0]['rows'][::-1],[sources()[0]['rows'][0]]*3]:
            obs=signature(rows,True)
            with self.subTest(rows=rows),self.assertRaises(ValueError):make_reference(observations=obs,phases=sources()[1],data_sha256='a'*64,phases_sha256='b'*64)

    def test_corrupt_signature(self):
        obs,hl=sources();obs['hash']='f'*64
        with self.assertRaises(ValueError):reference().state(obs,hl,target='mlhl')


try:
    from cctbx import crystal,miller
    from cctbx.array_family import flex
except ImportError:
    NATIVE=False
else:
    NATIVE=True


@unittest.skipUnless(NATIVE,'Explicit native Phenix qualification required')
class NativeChecks(unittest.TestCase):
    def setUp(self):
        cs=crystal.symmetry(unit_cell=(20,21,22,90,90,90),space_group_symbol='P1')
        ms=miller.set(crystal_symmetry=cs,indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0)]),anomalous_flag=False)
        self.fo=miller.array(ms,data=flex.double([8,10,12]),sigmas=flex.double([1,2,3])).set_observation_type_xray_amplitude()
        self.flags=miller.array(ms,data=flex.bool([False,True,False]))
        self.hl=miller.array(ms,data=flex.hendrickson_lattman([(1,2,3,4),(5,6,7,8),(9,10,11,12)]))
        self.fm=SimpleNamespace(target_name='mlhl',f_obs=lambda:self.fo,r_free_flags=lambda:self.flags,hl_coeffs=lambda:self.hl)
        self.core=SimpleNamespace(spacialization='hl',f_obs=self.fo,r_free_flags=self.flags,experimental_phases=self.hl)
        self.functor=SimpleNamespace(manager=self.fm,core=self.core)

    def test_native_arrays(self):
        self.assertEqual(observe_diffraction(reference(),self.fm)['observations'],3)

    def test_target_arrays(self):
        self.assertTrue(observe_target(reference(),self.fm,self.functor)['exact_source_values'])

    def test_integer_flags_are_not_coerced(self):
        self.flags=self.flags.customized_copy(data=flex.int([0,1,0]))
        with self.assertRaisesRegex(ValueError,'boolean'):observe_diffraction(reference(),self.fm)

    def test_array_crystal_mismatch(self):
        cs=crystal.symmetry(unit_cell=(20,21,23,90,90,90),space_group_symbol='P1')
        self.hl=self.hl.customized_copy(crystal_symmetry=cs)
        with self.assertRaisesRegex(ValueError,'crystal'):observe_diffraction(reference(),self.fm)

    def test_exact_core_cannot_hide_changed_manager(self):
        self.fo=self.fo.customized_copy(data=self.fo.data()*2,sigmas=self.fo.sigmas()*2)
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)

    def test_target_manager_mismatch(self):
        self.functor.manager=object()
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)

    def test_target_without_hl_specialization(self):
        self.core.spacialization='ml'
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)

    def test_target_changed_flags(self):
        self.core.r_free_flags=self.flags.customized_copy(data=flex.bool([True,False,False]))
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)

    def test_native_alignment_is_not_sorted_away(self):
        self.flags=self.flags.select(flex.size_t([2,1,0]))
        with self.assertRaisesRegex(ValueError,'align'):observe_diffraction(reference(),self.fm)

    def test_target_missing_phases(self):
        self.core.experimental_phases=None
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)

    def test_target_scaled_amplitudes(self):
        self.core.f_obs=self.fo.customized_copy(data=self.fo.data()*2,sigmas=self.fo.sigmas()*2)
        with self.assertRaises(ValueError):observe_target(reference(),self.fm,self.functor)


if __name__=='__main__':unittest.main()
