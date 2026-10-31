"""Owned fake workers verify C59 scope and failure-to-fallback orchestration."""
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('outcome',['pass','candidate_failure','baseline_failure','inspect_only','preparation_failure'])
def test_scaffold_action_bounds_native_scope_and_automatic_fallback(tmp_path,monkeypatch,outcome):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar59action',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    from nasolve import cif_scaffold_candidate,cif_native_validation,cif_linked_qualification,phenix_runtime
    session=tmp_path/'session';frozen=session/'inputs/review';frozen.mkdir(parents=True);root=tmp_path/'phenix';root.mkdir();pins=[]
    for name in ['flags.py','energies.py','manager.py']:
        data=('EXPLICIT_FAKE_SOURCE_'+name).encode();(root/name).write_bytes(data);pins.append({'path':name,'sha256':sha256(data).hexdigest()})
    metadata={'preparation':{'directory':{'path':'metadata/DP'},'candidate':{'path':'candidate.cif'}},
      'base_candidate':{'path':'old/DP/candidate.cif'},'coordinate_cases':{'generated_output':{'qualification':{'candidate_qualification':{'explicit_fake':True}}}}}
    members={'probe_receipt.json':json.dumps({'linked_control_audit':{'cases':{'DP':{'qualification':{'status':'LINKED_CONTROL_MECHANICS_PASS'}}}}}).encode(),
      'inputs/review/probe_receipt.json':json.dumps({'source_classification_audit':{'cases':{'DP':metadata}}}).encode(),
      'inputs/review/inputs/review/inputs/review/probe_receipt.json':json.dumps({'candidate_usability_audit':{'energy_sources':pins}}).encode(),
      'inputs/review/metadata/DP/candidate.cif':b'EXPLICIT_FAKE_CANDIDATE','inputs/review/inputs/review/old/DP/candidate.cif':b'EXPLICIT_FAKE_BASE',
      'inputs/review/inputs/review/old/DP/source.cif':b'EXPLICIT_FAKE_SOURCE'}
    for name,data in members.items():target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    source_root=session/'source';directory=source_root/m.ROTATION_PREFIX;directory.mkdir(parents=True)
    for name in ['dict.cif','policy.phil']:(directory/name).write_text('EXPLICIT_FAKE_ORIGINAL')
    model=source_root/'inputs/review/candidate/continued_geometry_model.pdb';model.parent.mkdir(parents=True);model.write_text('EXPLICIT_FAKE_FROZEN_MODEL')
    review=tmp_path/'prior.zip';review.write_bytes(b'EXPLICIT_FAKE_ARCHIVE')
    captured={'monomer_mappings':{'rows':[{'site':'B:4','resname':'DP'}]}}
    prior={'native_roundtrip':{'native_validation':captured}}
    capture={'inputs':[{'role':'dictionary','path':'dict.cif'},{'role':'phil','path':'policy.phil'}]}
    def prepare(source,numerical,original_model,dictionaries,phils,baseline,contexts,out,**kwargs):
        assert baseline==captured and contexts==[{'site':'B:4','incoming_site':'B:3','outgoing_site':'B:5','five_prime_state':'linked','three_prime_state':'linked'}]
        assert kwargs=={'code':'DP','native_qualification':{'explicit_fake':True}}
        if outcome=='preparation_failure':raise ValueError('EXPLICIT_FAKE_UNSUPPORTED_CONTEXT')
        out.mkdir();outputs={'model':{'path':'model.pdb'},'dictionaries':[{'path':'dictionary.cif'}],'phils':[{'path':'policy.phil'}]}
        (out/'model.pdb').write_bytes(model.read_bytes());(out/'dictionary.cif').write_text('EXPLICIT_FAKE_CANDIDATE');(out/'policy.phil').write_text('EXPLICIT_FAKE_POLICY')
        return {'outputs':outputs}
    calls=[]
    def native(model,dictionaries,parent,executable,**kwargs):
        assert kwargs['timeout_seconds']==60 and kwargs['energy_inventory'] and kwargs['policy_inventory']
        assert kwargs['phil_namespace_policy']=='refinement-root-to-interpreter-v1'
        calls.append(parent.name);parent.mkdir(parents=True)
        failed=(outcome=='candidate_failure' and len(calls)==2) or outcome=='baseline_failure'
        return {'native_directory':str(parent),'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,
          'execution':{'status':'FAILED' if failed else 'COMPLETED','returncode':1 if failed else 0},
          'native_validation':{'energy_inventory':{'installed_sources':[{'historical_path':str(root/p['path']),'sha256':p['sha256']} for p in pins]}}}
    decisions=[]
    def decide(preparation,qualification,baseline_usable,*,candidate_execution):
        assert baseline_usable is True;decisions.append(candidate_execution)
        return {'status':'CONTINUE_WITH_NOTES','selected_candidate':'separate_scaffold_candidate' if qualification.get('native_usable') else 'original_frozen_bundle'}
    monkeypatch.setattr(cif_scaffold_candidate,'prepare_scaffold_candidate',prepare)
    monkeypatch.setattr(cif_scaffold_candidate,'qualify_scaffold_candidate',lambda *a,**kw:{'status':'SCAFFOLD_CANDIDATE_MECHANICS_PASS','native_usable':True,'checks':[]})
    monkeypatch.setattr(cif_scaffold_candidate,'select_scaffold_candidate',decide)
    monkeypatch.setattr(cif_native_validation,'inspect_native_bundle',native)
    monkeypatch.setattr(cif_linked_qualification,'native_backbone_links',lambda n:{('B:3','B:4'):{},('B:4','B:5'):{}})
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *a,**kw:SimpleNamespace(root=root,version='EXPLICIT_FAKE_VERSION',environment={},executables={'phenix.python':root/'fake-python'}))
    monkeypatch.setattr(m,'_fingerprints',lambda *a:[]);monkeypatch.setattr(m,'_review_zip',lambda *a:'EXPLICIT_FAKE_REVIEW_ZIP')
    monkeypatch.setattr(m,'_scaffold_baseline_qualification',lambda *a:{'native_usable':True,'checks':{'explicit_fake':True}})
    receipt={};args=SimpleNamespace(component=['DP'],inspect_only=outcome=='inspect_only',phenix_root=root,timeout_seconds=600)
    if outcome=='baseline_failure':
        with pytest.raises(ValueError,match='Frozen original'):m._run_scaffold_candidate_action(args,receipt,session,review,review.read_bytes(),members,frozen,capture,{},source_root,prior)
        assert len(calls)==1 and not decisions;return
    assert m._run_scaffold_candidate_action(args,receipt,session,review,review.read_bytes(),members,frozen,capture,{},source_root,prior)==2
    assert len(calls)==(0 if outcome=='inspect_only' else 1 if outcome=='preparation_failure' else 2)
    assert receipt['analysis_completed'] and receipt['requires_cif_review'] is False
    report=receipt['scaffold_candidate_audit']
    if outcome!='inspect_only':assert report['decision']['selected_candidate']==('separate_scaffold_candidate' if outcome=='pass' else 'original_frozen_bundle')
    assert report['model_editing']==report['model_optimization']==report['dictionary_generation']=='NOT_RUN'


@pytest.mark.parametrize('defect',['none','static_target','coordinate','definition','policy','api','energy_repeat'])
def test_fallback_requires_fresh_exact_original_manager(tmp_path,defect):
    from copy import deepcopy
    from tests.test_cif_scaffold_candidate import native_case
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar59baseline',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    _,native,model,_=native_case(tmp_path);captured=deepcopy(native)
    if defect=='static_target':native['geometry']['proxy_details']['bond_simple'][0]['distance_ideal']+=.1
    if defect=='coordinate':native['atoms'][0]['xyz'][0]+=.01
    if defect=='definition':native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['changed']=[]
    if defect=='policy':native['restraint_policy']['secondary_structure_enabled']=True
    if defect=='api':native['installed_api_sources'][0]['sha256']='b'*64
    if defect=='energy_repeat':native['energy_inventory']['snapshots'][1]['target']+=1
    q=m._scaffold_baseline_qualification(captured,native,model)
    assert q['native_usable'] is (defect=='none'),q
