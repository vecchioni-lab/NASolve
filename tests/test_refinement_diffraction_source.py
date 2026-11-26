"""Shared-reader extraction controls, run directly with phenix.python/unittest."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from nasolve.refinement_diffraction_source import indexed_values, read_source_arrays

try:
    from cctbx import crystal, miller
    from cctbx.array_family import flex
    from iotbx import reflection_file_reader
except ImportError:
    NATIVE=False
else:
    NATIVE=True


class IndexChecks(unittest.TestCase):
    def test_index_order_is_not_identity(self):
        self.assertEqual(indexed_values([[0,0,1],[0,0,2]],[10,20],'source'),
                         indexed_values([[0,0,2],[0,0,1]],[20,10],'source'))

    def test_duplicates_empty_and_noninteger_indices_refuse(self):
        for indices,values in [([],[]),([[0,0,1]],[]),([[0,0,1],[0,0,1]],[1,2]),([[0,0,True]],[1])]:
            with self.subTest(indices=indices),self.assertRaises(ValueError):
                indexed_values(indices,values,'source')


@unittest.skipUnless(NATIVE,'Requires explicit native Phenix array library')
class SourceChecks(unittest.TestCase):
    def setUp(self):
        cs=crystal.symmetry(unit_cell=(20,21,22,90,90,90),space_group_symbol='P1')
        ms=miller.set(crystal_symmetry=cs,indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0)]),anomalous_flag=False)
        self.fo=miller.array(ms,data=flex.double([8.,10.,12.]),sigmas=flex.double([1.,2.,3.])).set_observation_type_xray_amplitude()
        self.flags=miller.array(ms,data=flex.int([1,0,1]))
        self.hl=miller.array(ms,data=flex.hendrickson_lattman([(1,2,3,4),(5,6,7,8),(9,10,11,12)]))
        self.fo.set_info(miller.array_info(labels=['F','SIGF']))
        self.flags.set_info(miller.array_info(labels=['FreeR_flag']))
        self.hl.set_info(miller.array_info(labels=['HLA','HLB','HLC','HLD']))

    def read(self, arrays=None):
        arrays=[self.fo,self.flags,self.hl] if arrays is None else arrays
        with patch.object(reflection_file_reader,'any_reflection_file',return_value=SimpleNamespace(as_miller_arrays=lambda:arrays)):
            return read_source_arrays(data_file='data.mtz',phase_file='hl.mtz',data_labels=['F','SIGF'],
                free_label='FreeR_flag',phase_labels=['HLA','HLB','HLC','HLD'],test_flag_value=0)

    def test_exact_source(self):
        r=self.read();self.assertEqual(len(r.observations),3)
        self.assertEqual(sum(r.flags[1]),1)
        self.assertEqual(r.hl[1],[list(v) for v in self.hl.data()])

    def test_independently_reordered_phases_join_by_index(self):
        expected=self.read();self.hl=self.hl.select(flex.size_t([2,1,0])).set_info(self.hl.info())
        actual=self.read();self.assertEqual(actual.hl,expected.hl);self.assertEqual(actual.observations,expected.observations)

    def test_flags_superset_preserves_existing_semantics(self):
        self.flags=self.flags.customized_copy(indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0),(2,0,0)]),data=flex.int([1,0,1,0])).set_info(self.flags.info())
        self.assertEqual(self.read().flags[1],[False,True,False])

    def test_missing_or_extra_HL_refuses(self):
        old=self.hl
        for indices,data in [(list(old.indices())[:-1],list(old.data())[:-1]),
                             (list(old.indices())+[(2,0,0)],list(old.data())+[(1,1,1,1)])]:
            self.hl=old.customized_copy(indices=flex.miller_index(indices),data=flex.hendrickson_lattman(data)).set_info(old.info())
            with self.assertRaisesRegex(ValueError,'cover'):self.read()

    def test_missing_flags_refuse(self):
        self.flags=self.flags.select(flex.size_t([0,1])).set_info(self.flags.info())
        with self.assertRaisesRegex(ValueError,'cover'):self.read()

    def test_noninteger_flags_refuse(self):
        self.flags=self.flags.customized_copy(data=flex.double([1.,0.,1.])).set_info(self.flags.info())
        with self.assertRaisesRegex(ValueError,'integer'):self.read()

    def test_nonpositive_observations_refuse_without_filtering(self):
        old=self.fo
        for data,sigmas in [([0.,10.,12.],[1.,2.,3.]),([8.,10.,12.],[0.,2.,3.])]:
            self.fo=old.customized_copy(data=flex.double(data),sigmas=flex.double(sigmas)).set_info(old.info())
            with self.assertRaisesRegex(ValueError,'positive'):self.read()

    def test_intensities_not_converted(self):
        self.fo.set_observation_type_xray_intensity()
        with self.assertRaisesRegex(ValueError,'amplitudes'):self.read()

    def test_mismatched_crystal_refuses(self):
        cs=crystal.symmetry(unit_cell=(25,21,22,90,90,90),space_group_symbol='P1')
        self.hl=self.hl.customized_copy(crystal_symmetry=cs).set_info(self.hl.info())
        with self.assertRaisesRegex(ValueError,'crystals'):self.read()

    def test_unknown_and_ambiguous_labels_refuse(self):
        for arrays in [[self.fo,self.flags],[self.fo,self.fo,self.flags,self.hl]]:
            with self.assertRaisesRegex(ValueError,'requested'):self.read(arrays)

    def test_anomalous_amplitudes_are_explicitly_averaged(self):
        indices=flex.miller_index([(0,0,1),(0,0,-1),(0,1,0),(0,-1,0),(1,0,0),(-1,0,0)])
        self.fo=self.fo.customized_copy(indices=indices,data=flex.double([8,8,10,10,12,12]),
            sigmas=flex.double([2]*6),anomalous_flag=True).set_info(self.fo.info())
        result=self.read()
        self.assertEqual(len(result.observations),3)
        self.assertEqual(sorted(row[1] for row in result.observations),[8.,10.,12.])
        self.assertEqual(sum(result.flags[1]),1)

    def test_anomalous_flags_or_HL_refuse(self):
        old_flags,old_hl=self.flags,self.hl
        for name in ('flags','hl'):
            setattr(self,name,getattr(self,name).customized_copy(anomalous_flag=True).set_info(getattr(self,name).info()))
            with self.assertRaisesRegex(ValueError,'non-anomalous'):self.read()
            self.flags,self.hl=old_flags,old_hl

    def test_real_mtz_read(self):
        with tempfile.TemporaryDirectory() as td:
            data=Path(td)/'data.mtz';phase=Path(td)/'phase.mtz'
            dataset=self.fo.as_mtz_dataset(column_root_label='F');dataset.add_miller_array(self.flags,column_root_label='FreeR_flag');dataset.mtz_object().write(str(data))
            self.hl.as_mtz_dataset(column_root_label='HL').mtz_object().write(str(phase))
            r=read_source_arrays(data_file=data,phase_file=phase,data_labels=['F','SIGF'],free_label='FreeR_flag',phase_labels=['HLA','HLB','HLC','HLD'],test_flag_value=0)
            self.assertEqual(r.observations,self.read().observations)
            self.assertEqual(r.hl,self.read().hl)


if __name__=='__main__':unittest.main()
