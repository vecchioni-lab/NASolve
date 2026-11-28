"""Owned bond-attribution contracts; synthetic captures assert no chemistry."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from tests.test_cif_attachment_native import save,artifact,rebind


def fixture(tmp_path):
    from tests.test_cif_linear_bond_energy import case
    from nasolve.cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID,API_SOURCES
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_monomers import native_monomer_worker,POLICY_ID as MONOMER_POLICY
    root=tmp_path/'original';root.mkdir();args,refs=case(root)
    before,after,source,dictionary,code,reference,candidate=args
    reference_file=root/'reference.json';save(reference_file,reference)
    model=root/'model.pdb';lines=[]
    for a in before['atoms']:
        i=a['identity'];x,y,z=a['xyz']
        lines.append(f"HETATM{a['i_seq']+1:5d} {a['atom_id']:>4} {i['resname']:>3} {i['chain_id']}{int(i['resseq']):4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{20.:6.2f}           C\n")
    model.write_text(''.join(lines)+'END\n');receipts=[]
    for side,native,selected in [('before',before,dictionary),('after',after,candidate)]:
        folder=root/side;folder.mkdir();(folder/'inputs').mkdir();resources=[]
        for ordinal,(role,path) in enumerate([('model',model),('dictionary',selected)]):
            p=folder/'inputs'/f'{ordinal:03d}_{role}{path.suffix}';p.write_bytes(path.read_bytes())
            resources.append(dict(artifact(p,folder),role=role,input_index=ordinal))
        for a in native['atoms']:a.update(element='C',occupancy=1.)
        native.update(schema_version=1,policy_id=NATIVE_POLICY_ID,automatic_adoption=False,scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',readyset_retry='NOT_RUN',phil_adaptations=[])
        native['geometry']['status']='RECORDED';native['dictionary_loading'][0].update(input=resources[1]['path'],status='RECORDED')
        spec=dict(policy_id=NATIVE_POLICY_ID,model=resources[0]['path'],dictionaries=[resources[1]['path']],phil_files=[],phil_namespace_policy='direct',inventory_detail='linked',policy_inventory=True,energy_inventory=True,full_monomer_inventory=True)
        save(folder/'native_spec.json',spec);(folder/'native_worker.py').write_text(native_monomer_worker(native_energy_worker(_NATIVE_WORKER)));(folder/'native.log').write_text('SYNTHETIC fixture, not native execution\n');(folder/'native_effective.phil').write_text('# synthetic effective policy\n')
        record=dict(schema_version=1,audit_kind='cif_native_bundle_inspection',policy_id=NATIVE_POLICY_ID,status='REVIEW',source_preserved=True,frozen_inputs_preserved=True,symlink_outputs=[],automatic_adoption=False,scientific_approval='NOT_RUN',optimization='NOT_RUN',model_editing='NOT_RUN',readyset_retry='NOT_RUN',phenix_version='SYNTHETIC',executable_sha256=sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),api_sources=API_SOURCES,execution=dict(status='COMPLETED',returncode=0),inputs=resources,outputs=[],phil_namespace_policy='direct',dictionary_source_policy='EXPLICIT_DICTIONARIES',full_monomer_inventory_policy=MONOMER_POLICY,native_validation=native)
        receipt=folder/'native_receipt.json';save(receipt,record);rebind(receipt);receipts.append(receipt)
    call=(source,code,reference_file,*receipts,0)
    sdk=SimpleNamespace(executables={'phenix.python':sys.executable},version='SYNTHETIC',environment=os.environ)
    return call,sdk,refs


def fake_runner(refs,mode='pass'):
    def run(command,*,cwd,log_path,environment,timeout_seconds):
        from nasolve import cif_captured_bond_attribution as m
        log_path.write_text('SYNTHETIC runner, not native execution\n')
        if mode=='interrupt':raise KeyboardInterrupt()
        if mode in ('timeout','unknown_timeout'):
            exc=subprocess.TimeoutExpired(command,timeout_seconds)
            if mode=='timeout':exc.returncode=-15;exc.stopped_verified=True
            raise exc
        if mode=='failed':return 3
        for name,data in m.native_auxiliary(cwd.parent).items():(cwd.parent/name).write_bytes(data)
        spec=json.loads((cwd/'spec.json').read_text());pins=spec['installed_sources']+[dict(module=n,sha256='b'*64,historical_path='/missing/'+n) for n in m.MODULES[3:]];sides={}
        for side in ('before','after'):
            ref=spec[side]['inventory_ref'];raw=(cwd.parent/ref['path']).read_bytes()
            assert len(raw)==ref['size'] and sha256(raw).hexdigest()==ref['sha256']
            save(cwd/side/'native_validation.json',json.loads(raw))
            sides[side]=dict(exact_native_inventory=True,special_position_indices=[],references=[deepcopy(r[side]) for r in refs])
        if mode=='numeric':
            for e in sides['after']['references'][0]['evaluations']:e['single_target']+=1;e['accumulated_target']+=1
        save(cwd/'result.json',dict(spec_sha256=sha256((cwd/'spec.json').read_bytes()).hexdigest(),evaluator_sha256=sha256((cwd/'evaluator.py').read_bytes()).hexdigest(),installed_sources=pins,installed_sources_after=deepcopy(pins),sides=sides));return 0
    return run


def test_prepare_only_does_not_need_native_tools_and_relocates(tmp_path):
    from nasolve import cif_captured_bond_attribution as m
    args,sdk,refs=fixture(tmp_path);out=tmp_path/'out'
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        report=m.audit_captured_bond_attribution(*args,None,out,bonds=[['Y','R']])
        assert report['status']=='PREPARED_ONLY' and report['new_native_calls']==0
        moved=out.rename(tmp_path/'moved');shutil.rmtree(tmp_path/'original')
        assert m.read_captured_bond_attribution(moved)==report
    spec=json.loads((moved/'job/spec.json').read_text())
    assert 'inventory_ref' in spec['before'] and 'inventory' not in spec['before']


@pytest.mark.parametrize('mode',['pass','numeric','failed','timeout'])
def test_owned_outcomes_preserve_scope_and_cold_read_after_move(tmp_path,mode):
    from nasolve import cif_captured_bond_attribution as m
    args,sdk,refs=fixture(tmp_path);out=tmp_path/'out'
    report=m.audit_captured_bond_attribution(*args,sdk,out,bonds=[['Y','R']],_process_runner=fake_runner(refs,mode))
    assert report['status']==('CAPTURED_BOND_TARGET_ATTRIBUTION_PASS' if mode=='pass' else 'REVIEW')
    assert report['reference_authority']=='NOT_QUALIFIED' and not report['automatic_adoption']
    assert report['new_native_calls']==1
    with pytest.raises(ValueError):m.audit_captured_bond_attribution(*args,sdk,out,bonds=[['Y','R']])
    moved=out.rename(tmp_path/'moved');shutil.rmtree(tmp_path/'original')
    with patch('subprocess.Popen',side_effect=AssertionError('No native readback execution')):
        assert m.read_captured_bond_attribution(moved)==report


@pytest.mark.parametrize('mode',['interrupt','unknown_timeout'])
def test_unknown_stop_or_interruption_does_not_seal_an_attribution(tmp_path,mode):
    from nasolve import cif_captured_bond_attribution as m
    from nasolve.campaign_process import CampaignProcessError
    args,sdk,refs=fixture(tmp_path);out=tmp_path/'out'
    with pytest.raises(KeyboardInterrupt if mode=='interrupt' else CampaignProcessError):
        m.audit_captured_bond_attribution(*args,sdk,out,bonds=[['Y','R']],_process_runner=fake_runner(refs,mode))
    assert (out/'job/spec.json').is_file() and not (out/m.REPORT).exists()


@pytest.mark.parametrize('defect',['reference','selection','options','kernel','spec','rebuilt','pins','extra_input','claim'])
def test_rehashed_changed_bond_proofs_cannot_be_promoted(tmp_path,defect):
    from nasolve import cif_captured_bond_attribution as m
    args,sdk,refs=fixture(tmp_path);out=tmp_path/'out'
    report=m.audit_captured_bond_attribution(*args,sdk,out,bonds=[['Y','R']],_process_runner=fake_runner(refs))
    if defect=='reference':
        p=out/'inputs/reference.json';r=json.loads(p.read_text());r['bonds'][0]['equilibrium_angstrom']+=.1;save(p,r)
    elif defect=='selection':report['controls']['bonds']=[['L','X']]
    elif defect in ('options','pins'):
        p=out/'job/result.json';r=json.loads(p.read_text())
        if defect=='options':r['sides']['after']['references'][0]['native_parameters']['slack']=.1
        else:r['installed_sources_after'][0]['sha256']='f'*64
        save(p,r)
    elif defect=='kernel':p=out/'job/evaluator.py';p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='spec':
        p=out/'job/spec.json';r=json.loads(p.read_text());r['before']['inventory_ref']['anchor']='other';save(p,r)
    elif defect=='rebuilt':
        p=out/'job/after/native_validation.json';r=json.loads(p.read_text());r['geometry']['proxy_details']['parallelity']=[];save(p,r)
    elif defect=='extra_input':(out/'inputs/unrelated').write_text('not declared')
    elif defect=='claim':report['reference_authority']='APPROVED'
    report['outputs'],report['directories']=m._inventory(out);save(out/m.REPORT,report)
    with pytest.raises(ValueError):m.read_captured_bond_attribution(out)
