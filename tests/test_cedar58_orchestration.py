"""Owned fake calls verify native action scope and PHIL consumer policy only."""
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('inspect_only',[False,True])
def test_linked_action_uses_one_reference_three_workers_and_explicit_namespace(tmp_path,monkeypatch,inspect_only):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar58action',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    from nasolve import cif_linked_control,cif_linked_preparation,cif_native_validation,phenix_runtime
    session=tmp_path/'session';frozen=session/'inputs/review';frozen.mkdir(parents=True);root=tmp_path/'phenix';root.mkdir();pins=[]
    for name in ['flags.py','energies.py','manager.py']:
        data=('EXPLICIT_FAKE_SOURCE_'+name).encode();(root/name).write_bytes(data);pins.append({'path':name,'sha256':sha256(data).hexdigest()})
    cases={};members={}
    for code in ['DP','PDU','5PC']:
        cases[code]={'preparation':{'directory':{'path':'metadata/'+code},'candidate':{'path':'candidate.cif'}},
          'base_candidate':{'path':'old/'+code+'/candidate.cif'},'decision':{'status':'CONTINUE_WITH_NOTES','explicit_fake':code},
          'coordinate_cases':{'generated_output':{'qualification':{'candidate_qualification':{'explicit_fake':code}},
          'native':{'directory':{'path':'native/'+code},'inputs':[{'role':'phil','path':'policy.phil'}]}}}}
        members.update({'metadata/'+code+'/candidate.cif':b'EXPLICIT_FAKE_CANDIDATE','inputs/review/old/'+code+'/candidate.cif':b'EXPLICIT_FAKE_BASE',
           'inputs/review/old/'+code+'/source.cif':b'EXPLICIT_FAKE_SOURCE','native/'+code+'/policy.phil':b'pdb_interpretation.secondary_structure.enabled = False\n'})
    members['probe_receipt.json']=json.dumps({'source_classification_audit':{'cases':cases}}).encode()
    members['inputs/review/inputs/review/probe_receipt.json']=json.dumps({'candidate_usability_audit':{'energy_sources':pins}}).encode()
    for name,data in members.items():target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    review=tmp_path/'prior.zip';review.write_bytes(b'EXPLICIT_FAKE_ARCHIVE')
    def prepare_models(frame,candidate,code,out):
        out.mkdir(parents=True);(out/'reference.pdb').write_text('EXPLICIT_FAKE_REFERENCE');(out/'model.pdb').write_text('EXPLICIT_FAKE_MODEL')
        return {'context':{'site':'A:2'},'outputs':{'model':{'path':'model.pdb'},'reference':{'path':'reference.pdb'}}}
    def prepare_link(source,candidate,model,contexts,out,*,code,native_qualification):
        assert native_qualification=={'explicit_fake':code};out.mkdir(parents=True)
        outputs={k:{'path':name} for k,name in [('dictionary','base.cif'),('modifications','mods.cif'),('parameters','mods.phil')]}
        for row in outputs.values():(out/row['path']).write_text('EXPLICIT_FAKE_PREPARATION')
        return {'outputs':outputs}
    calls=[]
    def native(model,dictionaries,parent,executable,**kwargs):
        assert kwargs['phil_namespace_policy']=='refinement-root-to-interpreter-v1'
        assert kwargs['timeout_seconds']==60 and kwargs['energy_inventory'] and kwargs['policy_inventory'] and kwargs['inventory_detail']=='linked'
        if not calls:assert not dictionaries and kwargs['installed_library_only'] and len(kwargs['phil_files'])==1
        else:assert len(dictionaries)==2 and len(kwargs['phil_files'])==2
        calls.append(kwargs);parent.mkdir(parents=True);return {'native_directory':str(parent),'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,
          'execution':{'status':'COMPLETED'},'native_validation':{'energy_inventory':{'installed_sources':[{'historical_path':str(root/p['path']),'sha256':p['sha256']} for p in pins]}}}
    monkeypatch.setattr(cif_linked_control,'prepare_linked_control_models',prepare_models)
    monkeypatch.setattr(cif_linked_control,'qualify_linked_control',lambda *a:{'status':'REVIEW','checks':[],'explicit_fake_only':True})
    monkeypatch.setattr(cif_linked_preparation,'prepare_linked_component',prepare_link)
    monkeypatch.setattr(cif_native_validation,'inspect_native_bundle',native)
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *a,**kw:SimpleNamespace(root=root,version='EXPLICIT_FAKE_VERSION',environment={},executables={'phenix.python':root/'fake-python'}))
    monkeypatch.setattr(m,'_fingerprints',lambda *a:[]);monkeypatch.setattr(m,'_review_zip',lambda *a:'EXPLICIT_FAKE_REVIEW_ZIP')
    receipt={};args=SimpleNamespace(inspect_only=inspect_only,phenix_root=root,timeout_seconds=600)
    assert m._run_linked_control_action(args,receipt,session,review,review.read_bytes(),members,frozen,{}, {})==2
    assert len(calls)==(0 if inspect_only else 4)
    assert receipt['analysis_completed'] and receipt['model_editing']=='SEPARATE_SYNTHETIC_CONTROL_MODELS'
    assert set(receipt['linked_control_audit']['cases'])=={'DP','PDU','5PC'}
