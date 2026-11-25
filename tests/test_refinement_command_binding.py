"""Complete command binding: real input owners, synthetic files, no refinement."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from nasolve.refinement_command_binding import bind_command
from nasolve.autorefine import ReflectionPlan, build_refine_command
from nasolve.checkpoints import _file_reference
from nasolve.refinement_parallelity import prepare_execution
from nasolve.refinement_parameter_files import rebind_miller_files
from nasolve.campaign_records import read_record, write_record

try:
    from phenix.programs.phenix_refine import Program
except ImportError:
    NATIVE = False
else:
    NATIVE = True


@unittest.skipUnless(NATIVE, 'Native PHIL qualification required')
class CommandChecks(unittest.TestCase):
    def fixture(self, root, phases=False):
        run = root/'dataset/AutoMR/run_001'
        first = run/'AutoRefine/round_001'; first.mkdir(parents=True)
        second = run/'AutoRefine/round_002'; second.mkdir()
        paths = []
        for name, data in [('original.mtz', b'observations'), ('start.pdb', b'initial model'), ('dictionary.cif', b'data_component'), ('bond.phil', b'refinement.geometry_restraints.edits.bond { atom_selection_1="name N3"\natom_selection_2="element Hg"\ndistance_ideal=2.1\nsigma=.02\n}\n')]:
            p=run/name;p.write_bytes(data);paths.append(p)
        if phases:
            p=run/'original-HL.mtz';p.write_bytes(b'original phases');paths.append(p)
        original=first/'autorefine.params'
        raw='data_manager.miller_array { file='+json.dumps(str(paths[0]))+'\nlabels { name="F,SIGF" }\nlabels { name="FreeR_flag" }\n}\n'
        if phases:
            raw+='data_manager.miller_array { file='+json.dumps(str(paths[-1]))+'\nlabels { name="HLAM,HLBM,HLCM,HLDM" }\n}\n'
        raw+='refinement.main.target=auto\nrefinement.refine.anomalous_scatterers.group { selection="element Hg"\nf_prime=-8.100181579589844\nf_double_prime=0\nrefine=None\n}\n'
        original.write_text(raw)
        phase=paths[-1] if phases else None
        plan=ReflectionPlan(('F','SIGF'),'FreeR_flag',0,False,('HLAM','HLBM','HLCM','HLDM') if phases else (),phase,False,False,None)
        command=build_refine_command(Path(sys.executable),paths[1],paths[0],paths[2:4],original,plan)
        inputs=[*paths,original]
        request,_,_=prepare_execution(run,checkpoint='refine-001',parent='postmr',inputs=inputs,command=command,python_executable=Path(sys.executable),macro_cycles=5)
        endpoint=first/'refined_001.pdb';endpoint.write_bytes(b'returned endpoint differs from start')
        rows=[dict(historical_file=str(p),resolved_file=str(p),sha256=_file_reference(p,run)['sha256'],source_reference=_file_reference(p,run)) for p in [paths[0],*([phase] if phase else [])]]
        derived,receipt=rebind_miller_files(original.read_bytes(),expected_policy_sha256=_file_reference(original,run)['sha256'],bindings=rows)
        target=second/'autorefine.params';target.write_bytes(derived)
        options=dict(request_reference=request,source_checkpoint='refine-001',endpoint_reference=_file_reference(endpoint,run),parameters_reference=_file_reference(target,run),parameter_receipt=receipt,executable=Path(sys.executable))
        return run,options,paths,original,target

    def bind(self,run,options):
        with patch('subprocess.Popen',side_effect=AssertionError('command assembly must not execute')):
            return bind_command(run,**options)

    def mutate_request(self,run,options,mutate):
        p=run/options['request_reference']['relative_path'];record=read_record(p)
        mutate(record);write_record(p,record,replace=True)
        options['request_reference']=_file_reference(p,run)

    def test_complete_command_uses_returned_model_ordered_restraints_and_exact_settings(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,paths,_,_=self.fixture(Path(td).resolve())
            cmd,inputs,receipt=self.bind(run,o)
            self.assertEqual(cmd[2],str(run/o['endpoint_reference']['relative_path']))
            self.assertNotEqual(cmd[2],str(paths[1]))
            self.assertEqual(cmd[1:1+len(inputs)],[str(p) for p in inputs])
            self.assertEqual(inputs[2:4],paths[2:4]);self.assertIn('xray_data.r_free_flags.label=FreeR_flag',cmd)
            self.assertNotIn('experimental_phases', ' '.join(cmd))
            self.assertTrue(receipt['non_file_arguments_unchanged'])
            self.assertEqual(receipt['endpoint'],o['endpoint_reference'])

    def test_phase_source_and_labels_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,p,_,_=self.fixture(Path(td).resolve(),True)
            cmd,inputs,r=self.bind(run,o)
            self.assertIn('experimental_phases.file_name='+str(p[-1]),cmd)
            self.assertIn('experimental_phases.labels=HLAM,HLBM,HLCM,HLDM',cmd)
            self.assertEqual(inputs[-2],p[-1]);self.assertTrue(r['has_phases'])

    def test_changed_input_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,p,_,_=self.fixture(Path(td).resolve());p[2].write_bytes(b'changed dictionary')
            with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_changed_endpoint_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve());(run/o['endpoint_reference']['relative_path']).write_bytes(b'changed endpoint')
            with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_unapproved_scientific_derivative_refuses_even_with_updated_file_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,target=self.fixture(Path(td).resolve());target.write_bytes(target.read_bytes().replace(b'-8.100181579589844',b'-8.1'))
            o['parameters_reference']=_file_reference(target,run)
            with self.assertRaisesRegex(ValueError,'derivative'):self.bind(run,o)

    def test_forged_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve());o['parameter_receipt']['non_file_literals_unchanged']=False
            with self.assertRaisesRegex(ValueError,'receipt'):self.bind(run,o)

    def test_changed_source_labels_cannot_be_hidden_by_argv(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve())
            self.mutate_request(run,o,lambda r:r['command'].__setitem__(r['command'].index('xray_data.labels=F,SIGF'),'xray_data.labels=I,SIGI'))
            with self.assertRaisesRegex(ValueError,'selector'):self.bind(run,o)

    def test_saflags_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve())
            self.mutate_request(run,o,lambda r:r['command'].__setitem__(r['command'].index('xray_data.r_free_flags.label=FreeR_flag'),'xray_data.r_free_flags.label=SAflags'))
            with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_extra_argument_and_duplicate_override_refuse(self):
        for arg in ['other.eff','main.target=mlhl','refinement.main.target=auto']:
            with self.subTest(arg=arg), tempfile.TemporaryDirectory() as td:
                run,o,_,_,_=self.fixture(Path(td).resolve());self.mutate_request(run,o,lambda r:r['command'].append(arg))
                with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_phase_command_without_positional_source_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve())
            self.mutate_request(run,o,lambda r:r['command'].extend(['experimental_phases.file_name=/unknown/phases.mtz','experimental_phases.labels=HLA,HLB,HLC,HLD']))
            with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_binding_must_match_exact_input_reference(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve());o['parameter_receipt']['bindings'][0]['source_reference']['relative_path']='other.mtz'
            with self.assertRaises((ValueError, RuntimeError)):self.bind(run,o)

    def test_relocated_full_command_has_no_old_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();run,o,_,_,_=self.fixture(root)
            old=run.parents[1];new=root/'moved dataset';old.rename(new);self.assertFalse(old.exists())
            run=new/'AutoMR/run_001'
            from nasolve.refinement_parallelity import read_execution_request
            from nasolve.refinement_inputs import _bound_path
            request=read_execution_request(run,o['request_reference'],checkpoint='refine-001')
            original=_bound_path(request['inputs'][-1],'policy',run)
            rows=[dict(historical_file=request['command'][1],resolved_file=str(_bound_path(request['inputs'][0],'data',run)),sha256=request['inputs'][0]['sha256'],source_reference=request['inputs'][0])]
            raw,receipt=rebind_miller_files(original.read_bytes(),expected_policy_sha256=request['inputs'][-1]['sha256'],bindings=rows)
            target=run/o['parameters_reference']['relative_path'];target.write_bytes(raw);o['parameters_reference']=_file_reference(target,run);o['parameter_receipt']=receipt
            cmd,inputs,r=self.bind(run,o)
            self.assertNotIn(str(old),' '.join(cmd));self.assertTrue(all(p.exists() for p in inputs))
            self.assertEqual(cmd[2],str(run/o['endpoint_reference']['relative_path']))

    def test_hidden_policy_file_and_target_override_refuse(self):
        for extra in [b'\nrefinement.reference_model.file="/unbound/reference.pdb"\n', b'\nrefinement.main.target=mlhl\n']:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as td:
                run,o,_,original,target=self.fixture(Path(td).resolve())
                original.write_bytes(original.read_bytes()+extra)
                self.mutate_request(run,o,lambda r:r['inputs'].__setitem__(-1,_file_reference(original,run)))
                raw,receipt=rebind_miller_files(original.read_bytes(),expected_policy_sha256=_file_reference(original,run)['sha256'],bindings=o['parameter_receipt']['bindings'])
                target.write_bytes(raw);o['parameters_reference']=_file_reference(target,run);o['parameter_receipt']=receipt
                with self.assertRaises(ValueError):self.bind(run,o)

    def test_existing_owner_freezes_bound_command_without_new_executor(self):
        with tempfile.TemporaryDirectory() as td:
            run,o,_,_,_=self.fixture(Path(td).resolve());cmd,inputs,r=self.bind(run,o)
            ref,preflight,refine=prepare_execution(run,checkpoint='refine-002',parent='refine-001',inputs=inputs,command=cmd,python_executable=Path(sys.executable),macro_cycles=5)
            request=read_record(run/ref['relative_path'])
            self.assertEqual(request['command'],cmd);self.assertEqual(request['parent'],'refine-001')
            self.assertIn('refinement.dry_run=True',preflight);self.assertEqual(refine[4:],cmd[1:])


if __name__=='__main__':unittest.main()
