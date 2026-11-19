"""Ordered repair composition; existing native verifiers are synthetic here.

These tests exercise chain/selection/publication contracts, not chemical energy.
The maintained plane and linear readers have their own native replay tests.
"""
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest
from tests.test_cif_dictionary_bundle_repair import fixture as linear_fixture


def fixture(tmp_path, monkeypatch):
    from nasolve import cif_repair_chain as chain
    selector, root, args, state = linear_fixture(tmp_path, monkeypatch)
    # Keep the same synthetic capture format as the existing selector fixture.
    monkeypatch.setattr(chain, '_inputs', selector._inputs)
    monkeypatch.setattr(chain, 'read_captured_linear_attribution', selector.read_captured_linear_attribution)
    monkeypatch.setattr(chain, 'read_linear_torsion_bundle', selector.read_linear_torsion_bundle)
    monkeypatch.setattr(chain, 'read_captured_plane_attribution',
        lambda p: json.loads((Path(p)/'captured_plane_attribution.json').read_text()))
    for p in (root/'attribution/captures').glob('*/native_receipt.json'):
        r=json.loads(p.read_text());r['native_validation']['energy_inventory']={'installed_sources':[]}
        p.write_text(json.dumps(r))
    shutil.copyfile(root/'attribution/captures/000/native_receipt.json', root/'original/capture/native_receipt.json')
    plane=root/'plane';(plane/'inputs').mkdir(parents=True)
    for side in ('before','after'):
        shutil.copytree(root/'attribution/captures/001',plane/'inputs'/side)
    (plane/'inputs/after/0.cif').write_text('LINEAR REPAIR PLUS SOURCE-QUALIFIED PLANE')
    p=plane/'inputs/after/native_receipt.json';r=json.loads(p.read_text());r['stage']=2;p.write_text(json.dumps(r))
    shutil.copyfile(root/'prepared/components/AAA/source.cif',plane/'inputs/source.cif')
    (plane/'captured_plane_attribution.json').write_text(json.dumps(dict(
        status='CAPTURED_PLANE_ATTRIBUTION_PASS',kernel_execution_authentication='MAINTAINED_FRESH_NATIVE_JOB',
        controls=dict(component='AAA',dictionary_index=0))))
    shutil.rmtree(root/'repaired/capture');shutil.copytree(plane/'inputs/after',root/'repaired/capture')
    return chain,selector,root,args,state,plane


def compose(chain,root,plane):
    output=root/'chain'
    chain.prepare_repair_chain([plane],output,linear_attribution=root/'attribution')
    return output


def test_composed_repairs_keep_both_changes_and_replay_after_originals_disappear(tmp_path,monkeypatch):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    out=compose(chain,root,plane);q=chain.read_repair_chain(out)
    assert q['status']=='ATTRIBUTED_REPAIR_CHAIN' and len(q['steps'])==2
    assert [s['kind'] for s in q['steps']]==['declared_linear_torsion','source_trigonal_plane']
    assert not q['automatic_adoption'] and q['derivative_qualification']=='NOT_RUN'
    moved=out.rename(tmp_path/'moved');shutil.rmtree(root)
    before={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('Read must not execute')):
        assert chain.read_repair_chain(moved)==q
        inputs=chain.repair_chain_inputs(moved)
    assert inputs['after_dictionaries'][0].read_text()=='LINEAR REPAIR PLUS SOURCE-QUALIFIED PLANE'
    assert before=={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect',['broken_join','model','phil','consumer','energy_consumer','unowned_slot','no_change','index_bool','duplicate','extra_stage'])
def test_incompatible_or_ambiguous_repairs_refuse_before_reservation(tmp_path,monkeypatch,defect):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    if defect=='broken_join':(plane/'inputs/before/0.cif').write_text('different starting dictionary')
    if defect in ('model','phil'):
        (plane/'inputs/before'/('model.pdb' if defect=='model' else '0.phil')).write_text('different context')
    if defect in ('consumer','energy_consumer'):
        p=plane/'inputs/before/native_receipt.json';r=json.loads(p.read_text())
        if defect=='consumer':r['phenix_version']='different'
        else:r['native_validation']['energy_inventory']['installed_sources']=[{'module':'other'}]
        p.write_text(json.dumps(r))
    if defect=='unowned_slot':(plane/'inputs/after/1.cif').write_text('changed bystander')
    if defect=='no_change':shutil.copyfile(plane/'inputs/before/0.cif',plane/'inputs/after/0.cif')
    if defect=='index_bool':
        p=plane/'captured_plane_attribution.json';r=json.loads(p.read_text());r['controls']['dictionary_index']=False;p.write_text(json.dumps(r))
    if defect=='extra_stage':(root/'attribution/captures/999').mkdir()
    planes=[plane]
    if defect=='duplicate':planes.append(plane)
    with pytest.raises(ValueError):chain.prepare_repair_chain(planes,root/'chain',linear_attribution=root/'attribution')
    assert not (root/'chain').exists()


@pytest.mark.parametrize('field,value',[('plane_count',True),('plane_count',0),('linear',1)])
def test_changed_chain_controls_are_not_trusted(tmp_path,monkeypatch,field,value):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    out=compose(chain,root,plane);p=out/chain.REPORT;r=json.loads(p.read_text());r['controls'][field]=value;p.write_text(json.dumps(r))
    with pytest.raises(ValueError):chain.read_repair_chain(out)


@pytest.mark.parametrize('mode',['repaired','fallback','none','bad_source','wrong_owner','changed_before_identity','wrong_derivative'])
def test_chain_uses_existing_source_identity_derivative_and_whole_bundle_gates(tmp_path,monkeypatch,mode):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    if mode in ('fallback','none'):
        p=plane/'captured_plane_attribution.json';r=json.loads(p.read_text());r['status']='REVIEW';p.write_text(json.dumps(r))
    if mode=='bad_source':(plane/'inputs/source.cif').write_text('unrelated chemical authority')
    if mode=='wrong_owner':
        p=plane/'captured_plane_attribution.json';r=json.loads(p.read_text());r['controls']['component']='BBB';p.write_text(json.dumps(r))
    if mode=='changed_before_identity':
        p=plane/'inputs/before/native_receipt.json';r=json.loads(p.read_text());r['native_validation']['atoms'][0]['identity']['chain_id']='X';p.write_text(json.dumps(r))
    out=compose(chain,root,plane);args.update(attribution_directory=out,repair_chain=True)
    if mode=='none':args['original_gradient_directory']=None
    if mode=='wrong_derivative':shutil.copyfile(root/'attribution/captures/001/native_receipt.json',root/'repaired/capture/native_receipt.json')
    if mode in ('bad_source','wrong_owner','changed_before_identity','wrong_derivative'):
        with pytest.raises(ValueError):selector.inspect_dictionary_bundle_repair(**args)
        return
    result=selector.inspect_dictionary_bundle_repair(**args)
    assert result['policy_id']==selector.COMPOSED_POLICY_ID
    assert result['decision']['selected']=={'repaired':'repaired_prepared_bundle','fallback':'verified_prepared_bundle','none':None}[mode]
    assert result['attribution']['path']=='repair_chain.json'


@pytest.mark.parametrize('fallback',[False,True])
def test_composed_runtime_uses_existing_public_api_and_readyset_parent_contract(tmp_path,monkeypatch,fallback):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    if fallback:
        p=root/'repaired/captured_mixed_gradients.json';p.write_text(json.dumps(dict(status='REVIEW')))
    out=compose(chain,root,plane);args.update(attribution_directory=out,repair_chain=True)
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_runtime_readyset import _parent
    target=tmp_path/'runtime';report=runtime.prepare_repaired_component_runtime_bundle(output=target,**args)
    assert report['policy_id']==runtime.COMPOSED_REPAIRED_POLICY_ID
    expected=(root/'prepared/0.cif' if fallback else plane/'inputs/after/0.cif').read_bytes()
    shutil.rmtree(root);target=target.rename(tmp_path/'relocated')
    with patch('subprocess.Popen',side_effect=AssertionError('No replay execution')):
        assert resolve_runtime_bundle(target)['dictionaries'][0].read_bytes()==expected
        assert _parent(target)['dictionaries'][0].read_bytes()==expected
    # A changed policy cannot reinterpret this layout as the old linear proof.
    report['policy_id']=runtime.REPAIRED_POLICY_ID
    (target/'runtime_bundle.json').write_text(json.dumps(report))
    with pytest.raises((ValueError,FileNotFoundError)):resolve_runtime_bundle(target)


def test_plane_only_chain_needs_no_fictitious_linear_attempt(tmp_path,monkeypatch):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    q=chain.prepare_repair_chain([plane],root/'chain')
    assert q['controls']==dict(linear=False,plane_count=1) and len(q['steps'])==1


@pytest.mark.parametrize('bound',['MAX_FILES','MAX_BYTES'])
def test_combined_chain_cannot_borrow_larger_evidence_allowance(tmp_path,monkeypatch,bound):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(chain,bound,1)
    with pytest.raises(ValueError):compose(chain,root,plane)
    assert not (root/'chain').exists()


def test_two_different_component_planes_remain_one_consecutive_whole_bundle(tmp_path,monkeypatch):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    second=root/'second';(second/'inputs').mkdir(parents=True)
    for side in ('before','after'):shutil.copytree(plane/'inputs/after',second/'inputs'/side)
    (second/'inputs/after/1.cif').write_text('SECOND COMPONENT PLANE REPAIR')
    shutil.copyfile(root/'prepared/components/BBB/source.cif',second/'inputs/source.cif')
    r=json.loads((plane/'captured_plane_attribution.json').read_text());r['controls']=dict(component='BBB',dictionary_index=1)
    (second/'captured_plane_attribution.json').write_text(json.dumps(r))
    q=chain.prepare_repair_chain([plane,second],root/'chain',linear_attribution=root/'attribution')
    assert [s['component'] for s in q['steps']]==['AAA','AAA','BBB']
    inputs=chain.repair_chain_inputs(root/'chain')
    assert [p.read_text() for p in inputs['after_dictionaries']]==[
        'LINEAR REPAIR PLUS SOURCE-QUALIFIED PLANE','SECOND COMPONENT PLANE REPAIR']
    # Reversing valid independent proofs is not permission to reorder repairs.
    with pytest.raises(ValueError,match='consecutive'):
        chain.prepare_repair_chain([second,plane],root/'reversed',linear_attribution=root/'attribution')
    assert not (root/'reversed').exists()


@pytest.mark.parametrize('defect',['extra_file','extra_directory','claim','missing_step','reordered_steps','source_symlink'])
def test_chain_replays_its_contents_instead_of_trusting_the_summary(tmp_path,monkeypatch,defect):
    chain,selector,root,args,state,plane=fixture(tmp_path,monkeypatch)
    out=compose(chain,root,plane);p=out/chain.REPORT;r=json.loads(p.read_text())
    if defect=='extra_file':(out/'planes/000/unrequested').write_text('unexpected')
    if defect=='extra_directory':(out/'planes/000/empty').mkdir()
    if defect=='claim':r['automatic_adoption']=True
    if defect=='missing_step':r['steps'].pop()
    if defect=='reordered_steps':r['steps'].reverse()
    if defect=='source_symlink':
        source=out/'planes/000/inputs/source.cif';source.unlink();source.symlink_to(plane/'inputs/source.cif')
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):chain.read_repair_chain(out)
