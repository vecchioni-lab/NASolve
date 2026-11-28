"""Original-only selection/publication; upstream science fixtures are synthetic."""
import json
import shutil
import pytest
from tests.test_cif_dictionary_bundle_repair import fixture


def original_case(tmp_path, monkeypatch):
    m, root, old, state = fixture(tmp_path, monkeypatch)
    candidate = root/'candidate'
    shutil.copytree(old['attribution_directory']/'captures/000', candidate)
    shutil.rmtree(old['attribution_directory'])
    shutil.rmtree(root/'repaired')
    args = dict(bundle=old['bundle'], baseline_receipt=old['baseline_receipt'],
        candidate_receipt=candidate/'native_receipt.json', original_gradient_directory=root/'original')
    return m, root, args, state


def test_original_qualification_needs_no_repair_plan_or_attribution(tmp_path, monkeypatch):
    m, root, args, state = original_case(tmp_path, monkeypatch)
    q = m.inspect_dictionary_bundle_original(**args)
    assert q['decision']['selected'] == 'verified_prepared_bundle'
    assert q['policy_id'] == m.ORIGINAL_POLICY_ID and 'attribution' not in q
    assert q['automatic_adoption'] is False and q['new_native_calls'] == 0
    result = m.original_dictionary_bundle_inputs(**args)
    assert result['dictionaries'] == [root/'prepared/0.cif', root/'prepared/1.cif']
    assert result['phils'] == [root/'prepared/0.phil']


@pytest.mark.parametrize('defect', ['missing-gradient','failed-gradient','source-unusable','inverted'])
def test_original_without_its_own_qualification_never_becomes_fallback(tmp_path, monkeypatch, defect):
    m, root, args, state = original_case(tmp_path, monkeypatch)
    if defect == 'missing-gradient': args['original_gradient_directory'] = None
    if defect == 'failed-gradient': (root/'original/captured_mixed_gradients.json').write_text('{"status":"REVIEW"}')
    if defect == 'source-unusable': state['source_usable'] = False
    if defect == 'inverted': state['stereo'] = 'INVERTED'
    assert m.inspect_dictionary_bundle_original(**args)['decision']['selected'] is None
    with pytest.raises(ValueError, match='No usable'): m.original_dictionary_bundle_inputs(**args)


@pytest.mark.parametrize('defect', ['model','dictionary','order','phil','full-policy','full-proof','copying','wrong-gradient','baseline-name','candidate-name'])
def test_original_capture_must_be_exact_and_complete(tmp_path, monkeypatch, defect):
    m, root, args, state = original_case(tmp_path, monkeypatch)
    if defect in {'model','dictionary','phil'}:
        (root/'candidate'/{'model':'model.pdb','dictionary':'0.cif','phil':'0.phil'}[defect]).write_text('OTHER')
    if defect == 'order':
        a,b = root/'candidate/0.cif',root/'candidate/1.cif'
        first,second = a.read_bytes(),b.read_bytes(); a.write_bytes(second);b.write_bytes(first)
    if defect in {'full-policy','full-proof','copying'}:
        p=args['candidate_receipt']; q=json.loads(p.read_text())
        if defect == 'full-policy': del q['full_monomer_inventory_policy']
        if defect == 'full-proof': del q['native_validation']['full_monomer_inventory']
        if defect == 'copying': q['native_validation']['full_monomer_inventory']['use_ncs_to_build_restraints']=True
        p.write_text(json.dumps(q))
    if defect == 'wrong-gradient': (root/'original/capture/native_receipt.json').write_text('{}')
    if defect in {'baseline-name','candidate-name'}:
        key='baseline_receipt' if defect=='baseline-name' else 'candidate_receipt'
        p=args[key].with_name('other.json'); p.write_bytes(args[key].read_bytes()); args[key]=p
    with pytest.raises(ValueError): m.inspect_dictionary_bundle_original(**args)


def test_original_inspection_detects_mutation_during_read(tmp_path, monkeypatch):
    m, root, args, state = original_case(tmp_path, monkeypatch); old=m.read_captured_mixed_gradients
    def changed(path):
        result=old(path); (root/'prepared/0.cif').write_text('CHANGED'); return result
    monkeypatch.setattr(m,'read_captured_mixed_gradients',changed)
    with pytest.raises(ValueError, match='changed'): m.inspect_dictionary_bundle_original(**args)


def test_public_original_bundle_replays_after_relocation(tmp_path, monkeypatch):
    from nasolve.cif_component_runtime import prepare_original_component_runtime_bundle, ORIGINAL_POLICY_ID
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_component_runtime import component_runtime_summary
    m, root, args, state = original_case(tmp_path, monkeypatch)
    runtime=tmp_path/'runtime'; value=prepare_original_component_runtime_bundle(output=runtime,**args)
    assert value['policy_id']==ORIGINAL_POLICY_ID and not value['automatic_adoption']
    assert value['decision']['selected']=='verified_prepared_bundle'
    before={p.relative_to(runtime):(p.read_bytes(),p.stat().st_mtime_ns) for p in runtime.rglob('*') if p.is_file()}
    moved=runtime.rename(tmp_path/'moved'); shutil.rmtree(root)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Read executed a child'))
    resolved=resolve_runtime_bundle(moved)
    assert resolved['manifest']==value and len(resolved['dictionaries'])==2
    assert 'independently verified' in component_runtime_summary(value)['text']
    assert all(((moved/p).read_bytes(),(moved/p).stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['evidence','selected-resource','manifest','extra-evidence'])
def test_original_runtime_refuses_tampering(tmp_path, monkeypatch, defect):
    from nasolve.cif_component_runtime import prepare_original_component_runtime_bundle
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    m, root, args, state=original_case(tmp_path,monkeypatch); runtime=tmp_path/'runtime'
    prepare_original_component_runtime_bundle(output=runtime,**args)
    if defect=='evidence': (runtime/'evidence/bundle/0.cif').write_text('OTHER')
    if defect=='selected-resource': (runtime/'dictionaries/000.cif').write_text('OTHER')
    if defect=='manifest':
        p=runtime/'runtime_bundle.json';v=json.loads(p.read_text());v['decision']['selected']='repaired_prepared_bundle';p.write_text(json.dumps(v))
    if defect=='extra-evidence': (runtime/'evidence/attribution').mkdir()
    with pytest.raises(ValueError): resolve_runtime_bundle(runtime)
