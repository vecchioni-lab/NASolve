"""Full native context survives numerical adapters; synthetic SDK is not chemistry."""
from copy import deepcopy
from pathlib import Path
import json,shutil
import pytest


def bind(receipt, native, spec=None, worker=None):
    from nasolve.cif_native_validation import _artifact
    r=json.loads(receipt.read_text());root=receipt.parent
    r['native_validation']=native;(root/'native_validation.json').write_text(json.dumps(native))
    if spec is not None:(root/'native_spec.json').write_text(json.dumps(spec))
    if worker is not None:(root/'native_worker.py').write_text(worker)
    r['outputs']=[_artifact(root/x['path'],root) for x in r['outputs']]
    receipt.write_text(json.dumps(r))


def full_parent(tmp_path,monkeypatch,execute=False,geometry=False):
    from tests.test_cif_captured_mixed_gradients import parent
    if geometry:
        from tests.test_cif_mixed_geometry import qualified_gradient_parent
        _,context,linked,sdk,_=qualified_gradient_parent(tmp_path,monkeypatch,optimizer='limit')
        monkeypatch.setattr('tests.test_cif_mixed_gradient.fake_sdk_parent',lambda *a:(context,linked,sdk))
        lbfgs=sdk/'scitbx/lbfgs.py';lbfgs.write_text(lbfgs.read_text().replace("Path('fake_optimizer_called')",'Path('+repr(str(sdk/'fake_optimizer_called'))+')'))
    receipt,phenix,sdk=parent(tmp_path,monkeypatch,'correct' if execute else None)
    from nasolve import cif_native_monomers as monomers
    if execute:
        # Existing analytic SDK bootstrap supplies complete saved mappings. Its
        # fake wrapper is explicit; actual maintained worker composition is
        # exercised in preparation tests and installed native validation.
        monkeypatch.setattr(monomers,'native_monomer_worker',lambda base:base+'\n# EXPLICIT_FAKE_FULL_MONOMER_WORKER\n')
    root=receipt.parent;r=json.loads(receipt.read_text());n=r['native_validation']
    identities={a['identity']['chain_id'].strip()+':'+a['identity']['resseq'].strip():a['identity'] for a in n['atoms']}
    n['monomer_mappings']['status']='RECORDED'
    for row in n['monomer_mappings']['rows']:
        identity=identities[row['site']];row['chain_id']=identity['chain_id']
        row['literal_identity']=dict(status='RECORDED',**identity)
    n['full_monomer_inventory']=monomers.capture_full_monomers(n,False)
    r['full_monomer_inventory_policy']=monomers.POLICY_ID;receipt.write_text(json.dumps(r))
    spec=json.loads((root/'native_spec.json').read_text());spec['full_monomer_inventory']=True
    worker=monomers.native_monomer_worker((root/'native_worker.py').read_text())
    bind(receipt,n,spec,worker)
    if execute:Path(phenix.environment['EXPLICIT_FAKE_NATIVE']).write_text(json.dumps(n))
    return receipt,phenix,sdk


def test_full_capture_prepares_exact_worker_and_relocates_without_downgrade(tmp_path,monkeypatch):
    from nasolve import cif_captured_mixed_gradients as m
    from nasolve.cif_native_monomers import POLICY_ID,native_monomer_worker
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    receipt,_,_=full_parent(tmp_path,monkeypatch);before={p:p.read_bytes() for p in receipt.parent.rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Unexpected execution'))
    out=tmp_path/'out';q=m.audit_captured_mixed_gradients(receipt,None,out)
    assert json.loads((out/'job/native_spec.json').read_text())['full_monomer_inventory'] is True
    assert (out/'job/native_worker.py').read_text()==native_monomer_worker(native_energy_worker(_NATIVE_WORKER))
    assert q['preparation']['full_monomer_inventory_policy']==POLICY_ID
    assert q['status']=='PREPARED_ONLY' and not q['automatic_adoption']
    assert all(p.read_bytes()==v for p,v in before.items())
    out.rename(tmp_path/'moved');shutil.rmtree(receipt.parent)
    assert m.read_captured_mixed_gradients(tmp_path/'moved')==q


@pytest.mark.parametrize('defect',['missing','extra','duplicate','wrong_chain','wrong_site','wrong_name','copying','numeric_flag','policy','proof_count','unrequested','unknown_flag'])
def test_incomplete_full_capture_refuses_before_attempt(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    receipt,_,_=full_parent(tmp_path,monkeypatch);r=json.loads(receipt.read_text());n=r['native_validation'];rows=n['monomer_mappings']['rows'];spec=json.loads((receipt.parent/'native_spec.json').read_text())
    if defect=='missing':rows.pop()
    if defect=='extra':rows.append(deepcopy(rows[-1]));rows[-1]['site']='B:9'
    if defect=='duplicate':rows.append(deepcopy(rows[-1]))
    if defect=='wrong_chain':rows[-1]['literal_identity']['chain_id']='B'
    if defect=='wrong_site':rows[-1]['site']='B:8'
    if defect=='wrong_name':rows[-1]['resname']='BAD'
    if defect=='copying':n['full_monomer_inventory']['use_ncs_to_build_restraints']=True
    if defect=='numeric_flag':spec['full_monomer_inventory']=1
    if defect=='proof_count':n['full_monomer_inventory']['mapping_count']=0
    if defect=='policy':r['full_monomer_inventory_policy']='unknown'
    if defect=='unrequested':del spec['full_monomer_inventory']
    if defect=='unknown_flag':spec['future_inventory']=True
    receipt.write_text(json.dumps(r));bind(receipt,n,spec)
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt,None,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',[None,'missing_proof','incomplete','copying','boolean_count'])
def test_fresh_derivative_job_and_rehashed_full_proof(tmp_path,monkeypatch,defect):
    from nasolve import cif_captured_mixed_gradients as m
    receipt,phenix,sdk=full_parent(tmp_path,monkeypatch,execute=True);out=tmp_path/'out'
    q=m.audit_captured_mixed_gradients(receipt,phenix,out,timeout_seconds=30)
    assert q['status']=='CAPTURED_MIXED_DERIVATIVES_PASS',q.get('error')
    n=json.loads((out/'job/native_validation.json').read_text())
    assert n['full_monomer_inventory']==json.loads(receipt.read_text())['native_validation']['full_monomer_inventory']
    if defect=='missing_proof':del n['full_monomer_inventory']
    if defect=='incomplete':n['monomer_mappings']['rows'].pop()
    if defect=='copying':n['full_monomer_inventory']['use_ncs_to_build_restraints']=True
    if defect=='boolean_count':n['full_monomer_inventory']['schema_version']=True
    if defect:
        (out/'job/native_validation.json').write_text(json.dumps(n));q['outputs']=[m.numerical._ref(out/r['path'],out) for r in q['outputs']];(out/m.REPORT).write_text(json.dumps(q))
        with pytest.raises(ValueError):m.read_captured_mixed_gradients(out)
    else:
        moved=out.rename(tmp_path/'moved');shutil.rmtree(receipt.parent);shutil.rmtree(sdk)
        monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Reader executed'))
        assert m.read_captured_mixed_gradients(moved)==q


@pytest.mark.parametrize('execute',[False,True])
def test_geometry_keeps_full_context_in_initial_job_and_endpoint(tmp_path,monkeypatch,execute):
    from nasolve import cif_captured_mixed_gradients as g,cif_captured_geometry_trial as m
    receipt,phenix,sdk=full_parent(tmp_path,monkeypatch,execute=True,geometry=True)
    gradient=tmp_path/'full-gradient';g.audit_captured_mixed_gradients(receipt,phenix,gradient,timeout_seconds=30)
    out=tmp_path/'geometry';q=m.trial_captured_geometry(gradient,phenix if execute else None,out,max_iterations=5,timeout_seconds=30)
    assert json.loads((out/'job/native_spec.json').read_text())['full_monomer_inventory'] is True
    assert q['preparation']['full_monomer_inventory_policy']=='cif-native-full-monomer-inventory-v1'
    assert q['status']==('CAPTURED_GEOMETRY_MECHANICS_PASS' if execute else 'PREPARED_ONLY'),q.get('optional_trial_finding')
    if execute:
        ref=q['native_readback']['receipt'];r=json.loads((out/ref['path']).read_text())
        assert r['full_monomer_inventory_policy']=='cif-native-full-monomer-inventory-v1'
        assert r['native_validation']['full_monomer_inventory']['mapping_count']==3
    moved=out.rename(tmp_path/'moved');shutil.rmtree(gradient);shutil.rmtree(receipt.parent);shutil.rmtree(sdk)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Reader executed'))
    assert m.read_captured_geometry_trial(moved)==q


@pytest.mark.parametrize('defect',['initial_proof','endpoint_downgrade','endpoint_proof','prepared_worker'])
def test_geometry_cannot_discard_identity_evidence_after_rehash(tmp_path,monkeypatch,defect):
    from nasolve import cif_captured_mixed_gradients as g,cif_captured_geometry_trial as m
    from nasolve.cif_native_validation import _NATIVE_WORKER
    receipt,phenix,_=full_parent(tmp_path,monkeypatch,execute=True,geometry=True)
    gradient=tmp_path/'full-gradient';g.audit_captured_mixed_gradients(receipt,phenix,gradient,timeout_seconds=30)
    out=tmp_path/'geometry';q=m.trial_captured_geometry(gradient,phenix,out,max_iterations=5,timeout_seconds=30)
    assert q['status']=='CAPTURED_GEOMETRY_MECHANICS_PASS'
    if defect=='initial_proof':
        p=out/'job/native_validation.json';n=json.loads(p.read_text());del n['full_monomer_inventory'];p.write_text(json.dumps(n))
    elif defect=='prepared_worker':(out/'job/native_worker.py').write_text(_NATIVE_WORKER)
    else:
        p=out/q['native_readback']['receipt']['path'];r=json.loads(p.read_text());n=r['native_validation'];spec=json.loads((p.parent/'native_spec.json').read_text())
        if defect=='endpoint_proof':n['full_monomer_inventory']['mapping_count']=True
        else:
            del r['full_monomer_inventory_policy'];del n['full_monomer_inventory'];del spec['full_monomer_inventory']
            p.write_text(json.dumps(r))
        bind(p,n,spec,_NATIVE_WORKER if defect=='endpoint_downgrade' else None)
        q['native_readback']['receipt']=m.geometry._ref(p,out)
    q['outputs']=[m.geometry._ref(out/r['path'],out) for r in q['outputs']];(out/m.REPORT).write_text(json.dumps(q))
    with pytest.raises(ValueError):m.read_captured_geometry_trial(out)
