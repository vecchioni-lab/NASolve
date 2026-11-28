"""Owned fake phases verify one bounded trial and usable-start fallback."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json
import pytest


@pytest.mark.parametrize('mode',['pass','nonconverged_error','initial_failure','trial_timeout','hand_inversion','rounded_hand_inversion','readback_failure','inspect_only'])
def test_one_replacement_trial_keeps_fixed_inputs_and_automatic_fallback(tmp_path,monkeypatch,mode):
    from tests.test_cif_scaffold_geometry_selection import case
    from nasolve import cif_corrected_geometry as validation,cif_replacement_geometry as initial_module
    from nasolve import cif_fixed_geometry as fixed,cif_native_validation as native,cif_gradient_audit as gradient,cif_captured_geometry,phenix_runtime
    q,t,mechanics,full,serialization=case()
    if mode=='nonconverged_error':t['result']['stopping']['error']='rounding errors'
    if mode=='hand_inversion':full['summary']['chirality']['sign_conflicts']=1
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar60action',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    session=tmp_path/'session';frozen=session/'inputs/review';frozen.mkdir(parents=True)
    core=session/'runtime/src/nasolve/cif_parallelity_correction.py';core.parent.mkdir(parents=True);core.write_bytes(b'EXPLICIT_FAKE_QUALIFIED_CORE')
    before={'atom_count':2,'geometry':{'sites_cart_exact':[[.4,.2,.6],[.8,.2,.4]]}}
    capture={'directory':{'path':'native_candidate'},'native_validation':before,
        'inputs':[{'role':'model','path':'model.pdb'},{'role':'dictionary','path':'dictionary.cif'},{'role':'phil','path':'policy.phil'}]}
    prior={'component':'ZZZ','selected_sites':['A:2'],'candidate':capture,'qualification':q,'decision':{'selected_candidate':'qualified_candidate'}}
    members={'probe_receipt.json':json.dumps({'scaffold_candidate_audit':prior}).encode(),
        'native_candidate/model.pdb':b'EXPLICIT_FAKE_SAVED_MODEL','native_candidate/dictionary.cif':b'EXPLICIT_FAKE_FIXED_DICTIONARY',
        'native_candidate/policy.phil':b'EXPLICIT_FAKE_NA_POLICY'}
    for name,data in members.items():target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    archive=tmp_path/'input.zip';archive.write_bytes(b'EXPLICIT_FAKE_ARCHIVE')
    monkeypatch.setattr(m,'_replacement_plane_parent',lambda data:({'explicit_fake':'parent'},{'explicit_fake':'inventory'},core.read_bytes(),{'anchor':'input_capsule','path':'explicit_fake_parent.json'}))
    monkeypatch.setattr(validation,'replacement_manager_view',lambda n:{'explicit_fake':'matching-view'})
    monkeypatch.setattr(validation,'validate_replacement_manager_bridge',lambda *a:True)
    monkeypatch.setattr(validation,'validate_gradient_qualification',lambda *a:True)
    monkeypatch.setattr(gradient,'review_distance_groups',lambda *a:{'selected_indices':[0],'groups':[]})
    root=tmp_path/'phenix';root.mkdir();calls=[]
    monkeypatch.setattr(phenix_runtime,'installation_from_candidate',lambda *a,**kw:SimpleNamespace(root=root,version='EXPLICIT_FAKE_VERSION',environment={},executables={'phenix.python':root/'python'}))
    monkeypatch.setattr(m,'_fingerprints',lambda *a:[]);monkeypatch.setattr(m,'_review_zip',lambda *a:'EXPLICIT_FAKE_OUTPUT_ZIP')
    def initial(model,dictionaries,phils,expected,parent_proof,parent_inventory,indices,output,executable,**kwargs):
        calls.append('initial');assert indices==[0] and kwargs['max_calls']==2000 and kwargs['timeout_seconds']==600
        assert expected==before and len(dictionaries)==len(phils)==1
        if mode=='initial_failure':raise ValueError('EXPLICIT_FAKE_INITIAL_FAILURE')
        output.mkdir();return {'native_directory':str(output),'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},
            'source_preserved':True,'frozen_inputs_preserved':True,'result':{'explicit_fake':'fresh-proof'},'correction_core_sha256':'c'*64}
    def trial(model,dictionaries,phils,expected,output,executable,**kwargs):
        calls.append('trial');assert kwargs['max_iterations']==1000 and kwargs['timeout_seconds']==600 and kwargs['policy_inventory'] is True
        assert kwargs['validated_correction']=={'result':{'explicit_fake':'fresh-proof'},'archive_sha256':m.CEDAR59_SHA256,'correction_core_sha256':'c'*64}
        assert 'continuation' not in kwargs
        output.mkdir();t['native_directory']=str(output);t['convergence']='NOT_CONVERGED_ERROR' if mode=='nonconverged_error' else 'NOT_CONVERGED_LIMIT'
        if mode=='trial_timeout':t['status']='FAILED';t['execution']['status']='TIMED_OUT'
        return t
    def serialize(model,candidate,expected,points):
        candidate.parent.mkdir(parents=True);candidate.write_bytes(b'EXPLICIT_FAKE_COORDINATE_CANDIDATE');return serialization
    def readback(model,dictionaries,output,executable,**kwargs):
        calls.append('readback');assert kwargs['timeout_seconds']==60 and kwargs['policy_inventory'] is True
        assert kwargs['phil_namespace_policy']=='refinement-root-to-interpreter-v1'
        output.mkdir();return {'native_directory':str(output),'status':'FAILED' if mode=='readback_failure' else 'REVIEW',
            'execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'native_validation':{'explicit_fake':'readback'}}
    monkeypatch.setattr(initial_module,'run_initial_replacement_audit',initial)
    monkeypatch.setattr(fixed,'run_fixed_geometry',trial);monkeypatch.setattr(fixed,'write_geometry_candidate',serialize)
    monkeypatch.setattr(fixed,'review_fixed_coordinates',lambda *a:full);monkeypatch.setattr(fixed,'qualify_fixed_policy_geometry',lambda *a:mechanics)
    rounded=deepcopy(full)
    if mode=='rounded_hand_inversion':rounded['summary']['chirality']['sign_conflicts']=1
    monkeypatch.setattr(cif_captured_geometry,'review_captured_geometry',lambda *a:rounded)
    monkeypatch.setattr(native,'inspect_native_bundle',readback)
    args=SimpleNamespace(inspect_only=mode=='inspect_only',phenix_root=root,timeout_seconds=600,max_iterations=1000);receipt={}
    assert m._run_scaffold_geometry_action(args,receipt,session,archive,archive.read_bytes(),members,frozen)==2
    report=receipt['scaffold_geometry_audit'];assert receipt['analysis_completed'] and not receipt['requires_cif_review']
    assert calls==([] if mode=='inspect_only' else ['initial'] if mode=='initial_failure' else ['initial','trial'] if mode=='trial_timeout' else ['initial','trial','readback'])
    assert report['decision']['selected_candidate']==('qualified_geometry_endpoint' if mode in {'pass','nonconverged_error'} else 'verified_initial_scaffold')
    assert report['decision']['continue_solving'] and not report['automatic_adoption']
    assert archive.read_bytes()==b'EXPLICIT_FAKE_ARCHIVE' and all((frozen/n).read_bytes()==b for n,b in members.items())
