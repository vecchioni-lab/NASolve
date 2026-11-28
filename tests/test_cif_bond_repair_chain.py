"""Reference-backed target chains reuse existing source and fallback owners.

Native/library qualification is stubbed here; its actual-reader tests are separate.
These controls exercise ordering, authority propagation and public selection only.
"""
import json
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest
from tests.test_cif_repair_chain import fixture as plane_fixture


def fixture(tmp_path,monkeypatch):
    from nasolve import cif_energy_library as library
    chain,selector,root,args,state,plane=plane_fixture(tmp_path,monkeypatch)
    bond=root/'bond';(bond/'inputs').mkdir(parents=True)
    for side in ('before','after'):shutil.copytree(plane/'inputs/after',bond/'inputs'/side)
    (bond/'inputs/after/0.cif').write_text('LINEAR PLANE AND REFERENCE TARGET')
    p=bond/'inputs/after/native_receipt.json';r=json.loads(p.read_text());r['stage']=3;p.write_text(json.dumps(r))
    shutil.copyfile(root/'prepared/components/AAA/source.cif',bond/'inputs/source.cif')
    (bond/'captured_bond_attribution.json').write_text(json.dumps(dict(status='LIBRARY_BOUND_BOND_ATTRIBUTION_PASS',component='AAA',dictionary_index=0)))
    support=root/'library';support.mkdir();(support/'spec.json').write_text(json.dumps({'consumer':{'synthetic':'same-consumer'}}));(support/library.REPORT).write_text('EXACT SYNTHETIC LIBRARY AUTHORITY')
    def bound(directory,lib,*,consumer):
        assert consumer=={'synthetic':'same-consumer'}
        if (Path(lib)/library.REPORT).read_text()!='EXACT SYNTHETIC LIBRARY AUTHORITY':raise ValueError('Library authority changed')
        r=json.loads((Path(directory)/'captured_bond_attribution.json').read_text())
        return dict(status=r['status'],dictionary_index=r['dictionary_index'],reference=dict(component=r['component']))
    monkeypatch.setattr(library,'qualify_bond_attribution_reference',bound)
    shutil.rmtree(root/'repaired/capture');shutil.copytree(bond/'inputs/after',root/'repaired/capture')
    return chain,selector,root,args,state,plane,bond,support


def compose(f):
    chain,_,root,_,_,plane,bond,support=f
    return chain.prepare_repair_chain([plane],root/'chain',linear_attribution=root/'attribution',bond_attributions=[bond],energy_library=support)


def test_target_chain_keeps_all_repairs_and_one_shared_library_after_move(tmp_path,monkeypatch):
    f=fixture(tmp_path,monkeypatch);chain,_,root,_,_,plane,bond,support=f;q=compose(f)
    assert q['policy_id']=='cif-ordered-source-repair-chain-v2'
    assert [s['kind'] for s in q['steps']]==['declared_linear_torsion','source_trigonal_plane','source_linear_bond_target']
    assert q['all_steps_attributed'] and not q['automatic_adoption']
    moved=(root/'chain').rename(tmp_path/'moved');shutil.rmtree(root)
    before={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No execution during chain read')):
        assert chain.read_repair_chain(moved)==q
        assert chain.repair_chain_inputs(moved)['after_dictionaries'][0].read_text()=='LINEAR PLANE AND REFERENCE TARGET'
    assert {p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}==before


def test_bond_only_chain_needs_no_dummy_plane_or_linear_stage(tmp_path,monkeypatch):
    chain,_,root,_,_,plane,bond,support=fixture(tmp_path,monkeypatch)
    q=chain.prepare_repair_chain([],root/'chain',bond_attributions=[bond],energy_library=support)
    assert q['controls']==dict(linear=False,plane_count=0,bond_count=1) and len(q['steps'])==1
    assert not (root/'chain/planes').exists()


@pytest.mark.parametrize('defect',['missing_library','unused_library','bad_library','model','join','unowned_slot','no_change','index_bool','duplicate'])
def test_unbound_or_nonconsecutive_target_chains_refuse_before_reservation(tmp_path,monkeypatch,defect):
    chain,_,root,_,_,plane,bond,support=fixture(tmp_path,monkeypatch);bonds=[bond]
    if defect=='missing_library':support=None
    if defect=='unused_library':bonds=[]
    if defect=='bad_library':(support/'energy_library_receipt.json').write_text('different authority')
    if defect=='model':(bond/'inputs/before/model.pdb').write_text('different model')
    if defect=='join':(bond/'inputs/before/0.cif').write_text('different starting target')
    if defect=='unowned_slot':(bond/'inputs/after/1.cif').write_text('unowned change')
    if defect=='no_change':shutil.copyfile(bond/'inputs/before/0.cif',bond/'inputs/after/0.cif')
    if defect in ('index_bool','duplicate'):
        p=bond/'captured_bond_attribution.json';r=json.loads(p.read_text())
        if defect=='index_bool':r['dictionary_index']=False;p.write_text(json.dumps(r))
        else:bonds.append(bond)
    with pytest.raises(ValueError):chain.prepare_repair_chain([plane],root/'chain',bond_attributions=bonds,energy_library=support)
    assert not (root/'chain').exists()


@pytest.mark.parametrize('mode',['repaired','fallback','bad_source','wrong_owner','wrong_derivative'])
def test_target_chain_uses_existing_source_and_derivative_selection(tmp_path,monkeypatch,mode):
    f=fixture(tmp_path,monkeypatch);chain,selector,root,args,_,plane,bond,support=f
    if mode=='fallback':
        p=bond/'captured_bond_attribution.json';r=json.loads(p.read_text());r['status']='REVIEW';p.write_text(json.dumps(r))
    if mode=='bad_source':(bond/'inputs/source.cif').write_text('another chemical source')
    if mode=='wrong_owner':
        p=bond/'captured_bond_attribution.json';r=json.loads(p.read_text());r['component']='BBB';p.write_text(json.dumps(r))
    if mode=='wrong_derivative':shutil.copyfile(plane/'inputs/after/native_receipt.json',root/'repaired/capture/native_receipt.json')
    compose(f);args.update(attribution_directory=root/'chain',repair_chain=True)
    if mode in ('bad_source','wrong_owner','wrong_derivative'):
        with pytest.raises(ValueError):selector.inspect_dictionary_bundle_repair(**args)
    else:
        r=selector.inspect_dictionary_bundle_repair(**args)
        assert r['decision']['selected']==('repaired_prepared_bundle' if mode=='repaired' else 'verified_prepared_bundle')


@pytest.mark.parametrize('field,value',[('bond_count',True),('bond_count',0),('plane_count',-1),('linear',1)])
def test_new_chain_policy_cannot_be_reinterpreted_or_forge_counts(tmp_path,monkeypatch,field,value):
    f=fixture(tmp_path,monkeypatch);chain,_,root,*_=f;compose(f);p=root/'chain'/chain.REPORT;r=json.loads(p.read_text());r['controls'][field]=value;p.write_text(json.dumps(r))
    with pytest.raises(ValueError):chain.read_repair_chain(root/'chain')


@pytest.mark.parametrize('fallback',[False,True])
def test_target_chain_public_runtime_preserves_repair_or_verified_fallback(tmp_path,monkeypatch,fallback):
    f=fixture(tmp_path,monkeypatch);chain,selector,root,args,_,plane,bond,support=f
    if fallback:(root/'repaired/captured_mixed_gradients.json').write_text(json.dumps(dict(status='REVIEW')))
    compose(f);args.update(attribution_directory=root/'chain',repair_chain=True)
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_runtime_readyset import _parent
    target=tmp_path/'runtime';runtime.prepare_repaired_component_runtime_bundle(output=target,**args)
    expected=(root/'prepared/0.cif' if fallback else bond/'inputs/after/0.cif').read_bytes()
    shutil.rmtree(root);target=target.rename(tmp_path/'relocated')
    with patch('subprocess.Popen',side_effect=AssertionError('No execution during runtime replay')):
        assert resolve_runtime_bundle(target)['dictionaries'][0].read_bytes()==expected
        assert _parent(target)['dictionaries'][0].read_bytes()==expected


def test_bond_chain_cannot_claim_historical_plane_policy(tmp_path,monkeypatch):
    f=fixture(tmp_path,monkeypatch);chain,_,root,*_=f;compose(f)
    p=root/'chain'/chain.REPORT;r=json.loads(p.read_text());r['policy_id']=chain.POLICY_ID;p.write_text(json.dumps(r))
    with pytest.raises(ValueError):chain.read_repair_chain(root/'chain')


def test_two_component_targets_share_one_library_but_keep_exact_order(tmp_path,monkeypatch):
    chain,_,root,_,_,plane,bond,support=fixture(tmp_path,monkeypatch)
    second=root/'second-bond';(second/'inputs').mkdir(parents=True)
    for side in ('before','after'):shutil.copytree(bond/'inputs/after',second/'inputs'/side)
    (second/'inputs/after/1.cif').write_text('SECOND COMPONENT REFERENCE TARGET')
    shutil.copyfile(root/'prepared/components/BBB/source.cif',second/'inputs/source.cif')
    (second/'captured_bond_attribution.json').write_text(json.dumps(dict(
        status='LIBRARY_BOUND_BOND_ATTRIBUTION_PASS',component='BBB',dictionary_index=1)))
    q=chain.prepare_repair_chain([],root/'chain',bond_attributions=[bond,second],energy_library=support)
    assert [s['component'] for s in q['steps']]==['AAA','BBB']
    assert len(list((root/'chain').rglob('energy_library_receipt.json')))==1
    assert [p.read_text() for p in chain.repair_chain_inputs(root/'chain')['after_dictionaries']]==[
        'LINEAR PLANE AND REFERENCE TARGET','SECOND COMPONENT REFERENCE TARGET']
    with pytest.raises(ValueError,match='consecutive'):
        chain.prepare_repair_chain([],root/'reversed',bond_attributions=[second,bond],energy_library=support)
    assert not (root/'reversed').exists()
