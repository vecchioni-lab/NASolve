import hashlib
import unittest
from pathlib import Path
import tempfile
import shutil

from nasolve.refinement_parameter_files import rebind_miller_files


def digest(data):return hashlib.sha256(data).hexdigest()


def policy():
    return b'''data_manager { miller_array {
 file = "/old data/original.mtz"
 labels { name = "F(+),SIGF(+),F(-),SIGF(-)" }
 labels { name = "FreeR_flag" }
} }
refinement.main.target = mlhl
refinement.refine.anomalous_scatterers.group {
 selection = "element Hg"
 f_prime = -8.100181579589844
 f_double_prime = 0.0
 refine = None
}
'''


def bindings():return [{'historical_file':'/old data/original.mtz','resolved_file':'/declared data/original.mtz','sha256':'a'*64,'source_reference':dict(anchor='dataset',relative_path='original.mtz',sha256='a'*64)}]


class InputChecks(unittest.TestCase):
    def test_source_checksum_required(self):
        with self.assertRaises(ValueError):rebind_miller_files(policy(),expected_policy_sha256='b'*64,bindings=bindings())

    def test_bindings_complete_and_unique(self):
        for rows in [[],bindings()*2,[dict(bindings()[0],sha256='bad')],[dict(bindings()[0],extra=1)],[dict(bindings()[0],resolved_file='')]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):rebind_miller_files(policy(),expected_policy_sha256=digest(policy()),bindings=rows)

    def test_unanchored_or_conflicting_source_reference(self):
        for ref in [dict(anchor='absolute',relative_path='/old/a.mtz',sha256='a'*64),dict(anchor='run',relative_path='../a.mtz',sha256='a'*64),dict(anchor='run',relative_path='a.mtz',sha256='b'*64)]:
            rows=[dict(bindings()[0],source_reference=ref)]
            with self.subTest(ref=ref),self.assertRaises(ValueError):rebind_miller_files(policy(),expected_policy_sha256=digest(policy()),bindings=rows)

    def test_no_includes_or_variables(self):
        for extra in [b'include file other.phil\n',b'x = $OTHER\n']:
            raw=policy()+extra
            with self.assertRaises(ValueError):rebind_miller_files(raw,expected_policy_sha256=digest(raw),bindings=bindings())


try:
    from iotbx import phil
    from iotbx.cli_parser import CCTBXParser
    from phenix.programs.phenix_refine import Program
except ImportError:
    NATIVE=False
else:NATIVE=True


@unittest.skipUnless(NATIVE,'Native PHIL qualification required')
class NativeChecks(unittest.TestCase):
    def rebind(self,raw=None,rows=None):
        raw=raw or policy();return rebind_miller_files(raw,expected_policy_sha256=digest(raw),bindings=rows or bindings())

    def test_only_file_literals_change(self):
        raw,r=self.rebind();self.assertIn(b'"/declared data/original.mtz"',raw)
        self.assertNotIn(b'/old data/',raw);self.assertIn(b'-8.100181579589844',raw)
        self.assertIn(b'FreeR_flag',raw);self.assertTrue(r['non_file_literals_unchanged']);self.assertEqual(r['rebound_definitions'],1)

    def test_relocated_source_uses_declared_reference_after_old_path_is_gone(self):
        from nasolve.refinement_inputs import _bound_path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();old=root/'old';old.mkdir()
            data=old/'original.mtz';data.write_bytes(b'synthetic diffraction fixture')
            original=str(data);raw=policy().replace(b'/old data/original.mtz',original.encode())
            dataset=root/'relocated';run=dataset/'AutoMR/run_001';run.mkdir(parents=True)
            new=dataset/'original.mtz';shutil.copyfile(data,new);shutil.rmtree(old)
            self.assertFalse(data.exists())
            ref=dict(anchor='dataset',relative_path='original.mtz',sha256=digest(new.read_bytes()),size=new.stat().st_size)
            resolved=_bound_path(ref,'declared relocated observations',run)
            rows=[dict(historical_file=original,resolved_file=str(resolved),sha256=ref['sha256'],source_reference=ref)]
            out,r=self.rebind(raw,rows)
            self.assertNotIn(original.encode(),out);self.assertIn(str(new).encode(),out)
            self.assertEqual(r['bindings'][0]['source_reference'],ref)
            self.assertTrue(r['non_file_literals_unchanged'])

    def test_unknown_historical_path_refuses(self):
        with self.assertRaisesRegex(ValueError,'declared'):self.rebind(rows=[dict(bindings()[0],historical_file='/other/original.mtz')])

    def test_unused_mapping_refuses(self):
        with self.assertRaisesRegex(ValueError,'unused'):self.rebind(rows=bindings()+[dict(bindings()[0],historical_file='/not/in/policy.mtz',resolved_file='/also/new.mtz')])

    def test_distinct_files_cannot_collapse(self):
        with self.assertRaises(ValueError):self.rebind(rows=bindings()+[dict(bindings()[0],historical_file='/second.mtz')])

    def test_second_phase_file_retains_labels(self):
        raw=policy()+b'data_manager.miller_array {\n file="/original/phase.mtz"\n labels { name="HLAM,HLBM,HLCM,HLDM" }\n}\n'
        rows=bindings()+[dict(historical_file='/original/phase.mtz',resolved_file='/declared/phase.mtz',sha256='b'*64,source_reference=dict(anchor='run',relative_path='phases.mtz',sha256='b'*64))]
        out,r=self.rebind(raw,rows);self.assertEqual(r['rebound_definitions'],2);self.assertIn(b'HLAM,HLBM,HLCM,HLDM',out)

    def test_absent_phases_are_not_added(self):
        out,r=self.rebind();self.assertNotIn(b'HLAM',out);self.assertNotIn(b'experimental_phases',out)

    def test_non_miller_path_literal_is_not_rebound(self):
        raw=policy()+b'output.prefix="/old data/original.mtz"\n'
        out,r=self.rebind(raw);self.assertIn(b'prefix = "/old data/original.mtz"',out)
        self.assertEqual(r['scope'],'DataManager Miller-array selectors only; no command or other file rebinding')

    def test_invalid_native_field_refuses(self):
        with self.assertRaises(ValueError):self.rebind(policy()+b'refinement.main.not_a_setting=1\n')

    def test_disabled_field_refuses(self):
        with self.assertRaises(ValueError):self.rebind(policy()+b'!refinement.main.number_of_macro_cycles=3\n')

    def test_repeated_same_source_blocks_preserved(self):
        raw=policy()+b'data_manager.miller_array {\n file="/old data/original.mtz"\n labels { name="HLAM,HLBM,HLCM,HLDM" }\n}\n'
        out,r=self.rebind(raw);self.assertEqual(r['rebound_definitions'],2)


if __name__=='__main__':unittest.main()
