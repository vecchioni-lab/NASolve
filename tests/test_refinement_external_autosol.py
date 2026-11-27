"""Explicit external phasing keeps the parent unphased and originals authoritative.

Tiny real MTZs and synthetic producer receipts test binding, not AutoSol science.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from . import test_refinement_mixed_parent as fixtures
from nasolve.checkpoints import initialize_registry,registry_path


@unittest.skipUnless(fixtures.NATIVE,'Explicit native Phenix libraries required')
class ExternalAutoSol(unittest.TestCase):
    ref=fixtures.NativeParent.ref
    save=fixtures.NativeParent.save
    bind=fixtures.NativeParent.bind
    snapshot=fixtures.NativeParent.snapshot
    scene=fixtures.NativeParent.scene

    def setUp(self):
        fixtures.NativeParent.setUp(self)
        source_policy='external-autosol-rehearsal-source-v1'
        binding_policy='ordinary-mixed-external-autosol-binding-v2'
        # Keep measured amplitudes and original flags; add an anomalous input quartet.
        anomalous=self.fo.generate_bijvoet_mates().set_observation_type_xray_intensity()
        mtz=self.fo.as_mtz_dataset(column_root_label='F')
        mtz.add_miller_array(self.flags,column_root_label='FreeR_flag')
        mtz.add_miller_array(anomalous,column_root_label='I');mtz.mtz_object().write(str(self.data))
        mr=self.run/'Phaser/mr_solution.pdb';mr.parent.mkdir();mr.write_bytes(self.source)
        sequence=self.run/'Model/seq_base.txt';sequence.parent.mkdir();sequence.write_text('>DNA\nACGT\n')
        rp=self.run/'report.json';report=json.loads(rp.read_text());report.pop('autosol')
        report['inputs'].update(reflections_sha256=self.ref(self.data)['sha256'],frame_sequence=self.ref(sequence))
        rp.write_text(json.dumps(report));registry_path(self.run).unlink();initialize_registry(self.run)
        registry=json.loads(registry_path(self.run).read_text())
        registry['checkpoints'][0]['restraints']=[self.ref(p) for p in self.restraints]
        registry_path(self.run).write_text(json.dumps(registry))
        inputs=self.run/'external-source';inputs.mkdir()
        heavy=inputs/'heavy.pdb'
        heavy.write_text(self.source.decode().splitlines()[0]+'\n'+
            self.source.decode().splitlines()[3].replace('  1.00','  1.60')+'\nEND\n')
        parameters=inputs/'autosol.eff'
        parameters.write_text('''autosol {
 data = "/old/data.mtz"
 seq_file = "/old/sequence.txt"
 atom_type = "Hg"
 lambda = 0.920085
 labels = "I(+) SIGI(+) I(-) SIGI(-)"
 sites = None
 phasing {
  input_partpdb_file = "/old/mr.pdb"
  mad_ha_add_list = None
 }
 model_building {
  build = False
  phase_improve_and_build = False
 }
 general {
  nproc = 2
 }
}
''')
        from nasolve.autosol import _pdb_atoms
        command=['/historical/phenix.autosol','autosol.data=/old/data.mtz','autosol.seq_file=/old/sequence.txt',
          'autosol.atom_type=Hg','autosol.lambda=0.920085','autosol.labels=I(+) SIGI(+) I(-) SIGI(-)',
          'autosol.phasing.input_partpdb_file=/old/mr.pdb','autosol.model_building.build=False',
          'autosol.model_building.phase_improve_and_build=False','autosol.general.nproc=2']
        producer=inputs/'producer.json'
        result=dict(adoption='EXPERIMENT_ONLY',exit_code=0,primary_species='Hg',additional_species=None,
          wavelength=0.920085,sites_argument=None,input_model_sha256=self.ref(mr)['sha256'],
          input_reflections_sha256=self.ref(self.data)['sha256'],sequence_sha256=self.ref(sequence)['sha256'],
          refinement_data_sha256=self.ref(self.phase)['sha256'],heavy_atom_sha256=self.ref(heavy)['sha256'],
          command=command,effective=dict(build=False,phase_improve_and_build=False,sites=None,nproc=2),
          observation_labels=['I(+)','SIGI(+)','I(-)','SIGI(-)'],sites=_pdb_atoms(heavy),discovered_site_count=1)
        producer.write_text(json.dumps(dict(status='AUTOSOL_OUTPUTS_CAPTURED_NOT_ADOPTED',
          production_phase_adoption=False,phenix_version_output='Synthetic test record; not a native execution',autosol=result)))
        self.external=dict(policy_id=source_policy,element='Hg',wavelength_A=.920085,
          phase_labels=['HLA','HLB','HLC','HLD'],sources={k:self.ref(p) for k,p in dict(
            producer=producer,parameters=parameters,mr_model=mr,sequence=sequence,observations=self.data,
            phases=self.phase,heavy_atoms=heavy).items()})
        self.request.update(schema_version=2,policy_id=binding_policy,external_autosol=self.external)
        self.request['parent'].update(observations=self.ref(self.data),phases=None,report=self.ref(rp),registry=self.ref(registry_path(self.run)))
        self.request['policy']['bindings'][0]['source_reference']=self.ref(self.data)
        self.save()

    def change_producer(self,change):
        p=self.run/'external-source/producer.json';r=json.loads(p.read_text());change(r);p.write_text(json.dumps(r))
        self.external['sources']['producer']=self.ref(p);self.save()

    def test_explicit_source_reaches_guard_without_adopting_phases_or_raw_occupancy(self):
        before=self.snapshot()
        with patch('subprocess.Popen',side_effect=AssertionError('No process')):
            bound=self.bind();driver,hooks,_=self.scene()
            with patch('nasolve.refinement_mixed_runtime._native_bindings',return_value=(hooks,{'fixture':'native arrays'},lambda:None)):
                with bound.guard() as guard:
                    driver.initialize();guard.finish(driver,dry_run=True)
        receipt=bound.receipt()
        self.assertEqual(receipt['phase_origin'],'external-declared-autosol')
        self.assertIsNone(receipt['parent_sources']['phases'])
        self.assertEqual(receipt['external_autosol']['sites'][0]['occupancy'],1.6)
        self.assertFalse(receipt['external_autosol']['ordinary_autosol_approval'])
        self.assertEqual(receipt['observations'],3);self.assertEqual(receipt['free_count'],1)
        self.assertEqual(before,self.snapshot())
        self.assertNotIn('autosol',json.loads((self.run/'report.json').read_text()))

    def test_v1_request_still_refuses_an_unphased_parent(self):
        from nasolve.refinement_mixed_parent import POLICY_ID
        self.request.update(schema_version=1,policy_id=POLICY_ID);self.request.pop('external_autosol');self.save()
        with self.assertRaisesRegex(ValueError,'approved'):self.bind()

    def test_relocation_needs_no_historical_path_and_leaves_parent_unphased(self):
        old=self.root/'original';new=self.root/'moved';old.rename(new);self.run=new/'dataset/AutoMR/run_001'
        self.assertFalse(old.exists())
        with patch('subprocess.Popen',side_effect=AssertionError('No process')):bound=self.bind()
        self.assertIsNone(bound.receipt()['parent_sources']['phases'])
        self.assertEqual(bound.receipt()['phases'],3)

    def test_changed_original_free_assignments_cannot_attach_old_phase_producer(self):
        from cctbx.array_family import flex
        from iotbx import reflection_file_reader
        aa=reflection_file_reader.any_reflection_file(str(self.data)).as_miller_arrays()
        flags=next(a for a in aa if a.info().labels==['FreeR_flag'])
        changed=flags.customized_copy(data=flex.int([0,1,0]))
        mtz=aa[0].as_mtz_dataset(column_root_label='F')
        mtz.add_miller_array(changed,column_root_label='FreeR_flag')
        mtz.add_miller_array(next(a for a in aa if a.anomalous_flag()),column_root_label='I');mtz.mtz_object().write(str(self.data))
        # Even a newly declared parent cannot make the historical producer match changed flags.
        rp=self.run/'report.json';r=json.loads(rp.read_text());r['inputs']['reflections_sha256']=self.ref(self.data)['sha256'];rp.write_text(json.dumps(r))
        self.request['parent']['report']=self.ref(rp)
        reg=json.loads(registry_path(self.run).read_text());reg['checkpoints'][0]['observations']=self.ref(self.data)
        registry_path(self.run).write_text(json.dumps(reg));self.request['parent']['registry']=self.ref(registry_path(self.run))
        self.external['sources']['observations']=self.ref(self.data);self.request['parent']['observations']=self.ref(self.data)
        self.request['policy']['bindings'][0]['source_reference']=self.ref(self.data);self.save()
        with self.assertRaisesRegex(ValueError,'producer differs from observations'):self.bind()

    def test_conflicting_approved_parent_phases_cannot_be_replaced(self):
        rp=self.run/'report.json';r=json.loads(rp.read_text())
        r['autosol']=dict(use_for_refinement=True,outputs=dict(refinement_data=str(self.phase),
          refinement_data_sha256=self.ref(self.phase)['sha256'],refinement_data_phase_labels=['HLA','HLB','HLC','HLD']))
        rp.write_text(json.dumps(r));self.request['parent']['report']=self.ref(rp);self.save()
        with self.assertRaises((ValueError,RuntimeError)):self.bind()

    def test_mismatches_refuse_before_runtime_hooks(self):
        mutations={
          'mr_hash':lambda r:r['autosol'].update(input_model_sha256='0'*64),
          'observation_hash':lambda r:r['autosol'].update(input_reflections_sha256='0'*64),
          'sequence_hash':lambda r:r['autosol'].update(sequence_sha256='0'*64),
          'phase_hash':lambda r:r['autosol'].update(refinement_data_sha256='0'*64),
          'heavy_hash':lambda r:r['autosol'].update(heavy_atom_sha256='0'*64),
          'failed':lambda r:r['autosol'].update(exit_code=1),
          'identity':lambda r:r['autosol'].update(primary_species='Ag'),
          'wavelength':lambda r:r['autosol'].update(wavelength=1.0),
          'mixed':lambda r:r['autosol'].update(additional_species='Au'),
          'adopted':lambda r:r.update(production_phase_adoption=True),
          'command':lambda r:r['autosol']['command'].append('autosol.sites=1'),
          'sites':lambda r:r['autosol'].update(discovered_site_count=2),
        }
        p=self.run/'external-source/producer.json';original=p.read_bytes()
        for name,change in mutations.items():
            with self.subTest(name=name):
                p.write_bytes(original);self.change_producer(change)
                with patch('nasolve.refinement_mixed_runtime._native_bindings',side_effect=AssertionError('No hooks')):
                    with self.assertRaises(ValueError):self.bind()

    def test_missing_or_modified_evidence_refuses_and_guard_rechecks_it(self):
        bound=self.bind();p=self.run/'external-source/autosol.eff';p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaises((ValueError,RuntimeError)):bound.guard()

    def test_unrelated_parameter_cannot_mask_changed_building_scope(self):
        p=self.run/'external-source/autosol.eff'
        p.write_text(p.read_text().replace('  build = False','  build = True')+'\nunrelated {\n build = False\n}\n')
        self.external['sources']['parameters']=self.ref(p);self.save()
        with self.assertRaisesRegex(ValueError,'building scope'):self.bind()

    def test_wrong_hl_order_or_saflags_refuses(self):
        self.request['selectors']['phase_labels']=['HLB','HLA','HLC','HLD'];self.save()
        with self.assertRaisesRegex(ValueError,'labels'):self.bind()
        self.request['selectors']['phase_labels']=['HLA','HLB','HLC','HLD']
        self.request['selectors']['free_label']='SAflags';self.save()
        with self.assertRaisesRegex(ValueError,'Free-R'):self.bind()
