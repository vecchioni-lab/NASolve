"""Native PHIL controls also run directly under phenix.python using unittest."""
from hashlib import sha256
import unittest

from nasolve.refinement_parameter_scope import ParameterScope,make_scope,scope_digest
from nasolve.refinement_parameter_composition import compose_parameters

try:
    import iotbx.phil
    from phenix.programs.phenix_refine import Program
    NATIVE = True
except ImportError:
    NATIVE = False


def inputs():
    source=(''.join(f'HETATM{i:5d} {name:>4s} UNK {chain:1s}{i:4d}    '
        f'{float(i):8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{200.:6.2f}          {symbol:>2s}  \n'
        for i,(name,chain,symbol) in enumerate([('N3','A','N'),('O4','B','O'),('HG','M','HG')],1))+'END\n').encode()
    atoms=[dict(label='native-label-'+str(i),scattering_type=el,xyz=[float(i+1),0.,0.],
        B=200.,Q=1.,f_prime=0.,f_double_prime=0.) for i,el in enumerate(['N','O','Hg'])]
    record=make_scope(source_model_sha256=sha256(source).hexdigest(),initial_atoms=atoms,
                      xyz_indices=[0,2],adp_groups=[[0,1]],real_space=False)
    return source,ParameterScope(record,expected_sha256=scope_digest(record))


POLICY=b'''# Literal policy example; compiler control only.
refinement {
 main { target = mlhl
  use_experimental_phases = True
 }
 refine {
  sites { individual = all }
  adp { group = all }
  anomalous_scatterers {
   group {
    selection = "chain M"
    f_prime = -8.100181579589844
    f_double_prime = 3.123456789012345
    refine = None
   }
   group {
    selection = "chain A"
    f_prime = 0.005101799964904785
    f_double_prime = 0
    refine = None
   }
  }
 }
}
refinement.refine.sites.individual = "chain B"
refinement.refine.adp.group = "chain A"
'''


def compose(policy=POLICY,**changes):
    source,scope=inputs();kw=dict(expected_policy_sha256=sha256(policy).hexdigest(),
                                scope=scope,source=source);kw.update(changes)
    return compose_parameters(policy,**kw)


class InputChecks(unittest.TestCase):
    def test_wrong_policy_hash_is_rejected_before_native_import(self):
        with self.assertRaisesRegex(ValueError,'checksum'):
            compose(expected_policy_sha256='0'*64)

    def test_policy_bytes_are_required(self):
        source,scope=inputs()
        with self.assertRaisesRegex(ValueError,'bytes'):
            compose_parameters('text',expected_policy_sha256='a'*64,scope=scope,source=source)

    def test_external_includes_are_refused(self):
        with self.assertRaisesRegex(ValueError,'self-contained'):
            compose(b'include file secret.params\n')

    def test_variable_expansion_is_refused(self):
        with self.assertRaisesRegex(ValueError,'self-contained'):
            compose(b'refinement.input.pdb.file_name = $MODEL\n')

    def test_parameter_attributes_are_refused(self):
        with self.assertRaisesRegex(ValueError,'attributes'):
            compose(b'refinement.main.nproc = 1\n.type = int\n')

    def test_non_ascii_policy_is_refused(self):
        with self.assertRaisesRegex(ValueError,'ASCII'):
            compose('refinement.main.target = é\n'.encode())


@unittest.skipUnless(NATIVE,'Requires native Phenix PHIL; run this module with phenix.python')
class NativeComposition(unittest.TestCase):
    def parsed(self,text):
        from iotbx.cli_parser import CCTBXParser
        import io
        p=CCTBXParser(program_class=Program,logger=io.StringIO());m=p.master_phil
        m.adopt_scope(p.data_manager.master_phil)
        f,unused=m.fetch(source=iotbx.phil.parse(text.decode()),track_unused_definitions=True)
        self.assertFalse(unused)
        return f.extract().refinement

    def test_all_repeated_fields_replaced_without_scattering_rounding(self):
        text,receipt=compose();p=self.parsed(text)
        self.assertEqual(len(p.refine.sites.individual),1)
        self.assertEqual(len(p.refine.adp.group),1)
        self.assertEqual(p.refine.adp.group_adp_refinement_mode,'group_selection')
        self.assertNotIn('all',p.refine.sites.individual)
        self.assertNotIn('all',p.refine.adp.group)
        self.assertIn(b'-8.100181579589844',text)
        self.assertIn(b'0.005101799964904785',text)
        self.assertEqual(p.refine.anomalous_scatterers.group[0].f_double_prime,3.123456789012345)
        self.assertEqual(p.main.target,'mlhl');self.assertTrue(p.main.use_experimental_phases)
        self.assertEqual(receipt['removed_definitions'],4)
        self.assertEqual(receipt['owned_fields'],8)
        self.assertTrue(receipt['non_owned_literals_unchanged'])

    def test_native_membership_remains_exact(self):
        from iotbx import pdb
        text,_=compose();p=self.parsed(text);source,_=inputs()
        cache=pdb.input(source_info='synthetic',lines=source.decode().splitlines()).construct_hierarchy().atom_selection_cache()
        self.assertEqual(list(cache.iselection(p.refine.sites.individual[0])),[0,2])
        self.assertEqual(list(cache.iselection(p.refine.adp.group[0])),[0,1])
        self.assertEqual(p.refine.strategy,['individual_sites','group_adp'])
        self.assertFalse(p.main.apply_overall_isotropic_scale_to_adp)
        self.assertFalse(p.bulk_solvent_and_scale.apply_back_trace)
        self.assertFalse(p.pdb_interpretation.sort_atoms)

    def test_no_original_selections_is_supported(self):
        text,r=compose(b'refinement.main.target = mlhl\n')
        self.assertEqual(r['removed_definitions'],0)
        self.assertEqual(len(self.parsed(text).refine.adp.group),1)

    def test_duplicate_nested_scopes_are_supported(self):
        raw=POLICY+b'\nrefinement { refine { adp { group = "chain M" } } }\n'
        text,r=compose(raw);self.assertEqual(r['removed_definitions'],5)
        self.assertEqual(len(self.parsed(text).refine.adp.group),1)

    def test_other_parameter_values_are_retained(self):
        raw=POLICY+b'\nrefinement.target_weights.wxc_scale = 0.12345678901234567\n'
        text,_=compose(raw);self.assertIn(b'0.12345678901234567',text)
        self.assertEqual(self.parsed(text).target_weights.wxc_scale,0.12345678901234567)

    def test_unknown_policy_field_refuses(self):
        with self.assertRaisesRegex(ValueError,'unused'):
            compose(POLICY+b'\nrefinement.main.not_a_setting = 1\n')

    def test_disabled_policy_field_refuses(self):
        with self.assertRaisesRegex(ValueError,'[Dd]isabled'):
            compose(POLICY+b'\n!refinement.main.nproc = 8\n')

    def test_source_scope_binding_is_still_required(self):
        source,_=inputs()
        with self.assertRaisesRegex(ValueError,'checksum'):
            compose(source=source+b'REMARK changed\n')

    def test_repeated_composition_has_same_effect(self):
        first,_=compose();second,_=compose(first)
        a,b=self.parsed(first),self.parsed(second)
        self.assertEqual(a.refine.sites.individual,b.refine.sites.individual)
        self.assertEqual(a.refine.adp.group,b.refine.adp.group)
        self.assertEqual(a.refine.anomalous_scatterers.group[0].f_prime,b.refine.anomalous_scatterers.group[0].f_prime)


if __name__=='__main__':
    unittest.main()
