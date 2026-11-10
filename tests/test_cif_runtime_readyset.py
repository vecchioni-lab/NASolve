"""Selected-runtime continuation wiring with explicit synthetic parent/native proof.

The real bundle, observer, source binding and public replay execute. Scientific
qualification itself is mocked here and exercised separately by live controls.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json, shutil
from unittest.mock import patch
import pytest


def inventory(root):
    return {p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}


def parent_case(tmp_path, monkeypatch, *, repaired=True, single=False):
    from tests.test_cif_dictionary_bundle_readyset import control
    from nasolve import cif_component_runtime as runtime
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle
    b,installation=control(tmp_path,monkeypatch,single=single)
    proofs=tmp_path/'parent-proofs';proofs.mkdir()
    for name in ('baseline','candidate','gradient','attribution'):
        folder=proofs/name;folder.mkdir();(folder/'native_receipt.json').write_text('{}')
    for code,path in b['component_dictionaries'].items():
        (proofs/'attribution'/(code+'.cif')).write_bytes(path.read_bytes()+('\n# SELECTED_REPAIR_'+code+'\n').encode())
    def selected(root, controls):
        prepared=read_dictionary_bundle(root/'evidence/bundle');dictionaries=list(prepared['after_dictionaries'])
        if repaired:
            for code,p in prepared['component_dictionaries'].items():
                dictionaries[dictionaries.index(p)]=root/'evidence/attribution'/(code+'.cif')
        choice='repaired_prepared_bundle' if repaired else 'verified_prepared_bundle'
        decision=dict(status='CONTINUE_WITH_NOTES',selected=choice,scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY',
                      requires_cif_review=False,automatic_adoption=False,notes=['Synthetic upstream qualification for wiring only.'])
        return dict(synthetic_parent_qualification=True),decision,dict(model=prepared['model'],dictionaries=dictionaries,
            phils=prepared['after_phils']),[dict(check='synthetic-native-charge',status='UNSUPPORTED')]
    monkeypatch.setattr(runtime,'_repaired_selection' if repaired else '_original_selection',selected)
    parent=tmp_path/'parent'
    if repaired:
        runtime.prepare_repaired_component_runtime_bundle(tmp_path/'bundle',proofs/'baseline/native_receipt.json',
            proofs/'attribution',parent,repaired_gradient_directory=proofs/'gradient')
    else:
        runtime.prepare_original_component_runtime_bundle(tmp_path/'bundle',proofs/'baseline/native_receipt.json',
            proofs/'candidate/native_receipt.json',parent,original_gradient_directory=proofs/'gradient')
    return parent,installation


def observed(tmp_path,monkeypatch,**kwargs):
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption,runtime_readyset_endpoint_inputs
    parent,installation=parent_case(tmp_path,monkeypatch,**kwargs);control=tmp_path/'selected-readyset'
    report=audit_runtime_readyset_consumption(parent,installation,control)
    return parent,installation,control,report,runtime_readyset_endpoint_inputs(parent,control)


def native_wiring(tmp_path,monkeypatch,parent,endpoint_inputs,*,wrong_baseline=False,full=True,accepted=True):
    """Native physics is explicitly synthetic; exact selected-input binding is real."""
    from nasolve import cif_runtime_readyset as module
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle
    from nasolve.cif_native_monomers import POLICY_ID
    selected=resolve_runtime_bundle(parent);receipts=[]
    for label,inputs in [('baseline',selected),('endpoint',endpoint_inputs)]:
        folder=tmp_path/('native-'+label);folder.mkdir();path=folder/'native_receipt.json'
        dictionaries=inputs['dictionaries']
        if label=='baseline' and wrong_baseline:
            dictionaries=read_dictionary_bundle(parent/'evidence/bundle')['after_dictionaries']
        record=dict(label=label,model=sha256(inputs['model'].read_bytes()).hexdigest(),
            dictionaries=[sha256(p.read_bytes()).hexdigest() for p in dictionaries],
            phils=[sha256(p.read_bytes()).hexdigest() for p in inputs['phils']],
            full_monomer_inventory_policy=POLICY_ID if full else 'missing')
        path.write_text(json.dumps(record));receipts.append(path)
    def capture(path,model):
        data=path.read_bytes();record=json.loads(data)
        assert sha256(model).hexdigest()==record['model']
        return record,dict(label=record['label']),{path:data}
    def bind(record,consumer,model,dictionaries,phils):
        if (record['model']!=sha256(model.read_bytes()).hexdigest()
            or record['dictionaries']!=[sha256(p.read_bytes()).hexdigest() for p in dictionaries]
            or record['phils']!=[sha256(p.read_bytes()).hexdigest() for p in phils]):
            raise ValueError('Native capture does not match the exact selected runtime')
    monkeypatch.setattr('nasolve.cif_attachment_native._capture',capture)
    monkeypatch.setattr(module,'_bind_capture',bind)
    monkeypatch.setattr('nasolve.cif_native_monomers.review_full_monomers',lambda n:None)
    monkeypatch.setattr('nasolve.cif_postmr_cached_model.qualify_cached_model_roundtrip',lambda *a:
        dict(mechanics_checks_pass=accepted,checks={'synthetic_native_wiring':accepted}))
    return receipts


@pytest.mark.parametrize('repaired',[False,True])
@pytest.mark.parametrize('single',[False,True])
def test_selected_repair_reaches_existing_readyset_observer(tmp_path,monkeypatch,repaired,single):
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption,runtime_readyset_endpoint_inputs
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle
    parent,installation=parent_case(tmp_path,monkeypatch,repaired=repaired,single=single)
    before=inventory(parent);selected=resolve_runtime_bundle(parent);b=read_dictionary_bundle(parent/'evidence/bundle')
    report=audit_runtime_readyset_consumption(parent,installation,tmp_path/'selected-readyset')
    assert report['status']=='READYSET_CACHED_INPUT_PASS' and len(report['checks'])==8 and all(report['checks'].values())
    for code,path in b['component_dictionaries'].items():
        index=b['after_dictionaries'].index(path);actual=tmp_path/'selected-readyset'/report['component_inputs'][code]['path']
        assert actual.read_bytes()==selected['dictionaries'][index].read_bytes()
        assert (actual.read_bytes()!=path.read_bytes()) is repaired
    endpoint=runtime_readyset_endpoint_inputs(parent,tmp_path/'selected-readyset')
    assert [p.read_bytes() for p in endpoint['phils']]==[p.read_bytes() for p in selected['phils']]
    assert len(endpoint['dictionaries'])==1+len(b['after_dictionaries'])-len(b['component_dictionaries'])
    assert endpoint['native_options']=={'full_monomer_inventory':True} and inventory(parent)==before


@pytest.mark.parametrize('missing',['readyset','baseline','endpoint'])
def test_missing_optional_evidence_retains_selected_repaired_parent(tmp_path,monkeypatch,missing):
    from nasolve.cif_runtime_readyset import inspect_runtime_readyset
    parent,_,control,_,inputs=observed(tmp_path,monkeypatch)
    baseline,endpoint=native_wiring(tmp_path,monkeypatch,parent,inputs)
    if missing=='readyset':control=tmp_path/'absent-readyset'
    if missing=='baseline':baseline=None
    if missing=='endpoint':endpoint=None
    review=inspect_runtime_readyset(parent,baseline,control,endpoint)
    assert review['decision']['selected']=='verified_parent_runtime'
    assert review['parent_selected']==review['decision']['parent_selected']=='repaired_prepared_bundle'
    assert review['endpoint_error'] and not review['automatic_adoption']


@pytest.mark.parametrize('defect',['pre_repair_baseline','incomplete_native','native_comparison'])
def test_endpoint_never_falls_back_to_older_unselected_dictionaries(tmp_path,monkeypatch,defect):
    from nasolve.cif_runtime_readyset import inspect_runtime_readyset
    parent,_,control,_,inputs=observed(tmp_path,monkeypatch)
    baseline,endpoint=native_wiring(tmp_path,monkeypatch,parent,inputs,wrong_baseline=defect=='pre_repair_baseline',
        full=defect!='incomplete_native',accepted=defect!='native_comparison')
    review=inspect_runtime_readyset(parent,baseline,control,endpoint)
    assert review['decision']['selected']=='verified_parent_runtime'
    assert review['parent_selected']=='repaired_prepared_bundle'


@pytest.mark.parametrize('repaired',[False,True])
@pytest.mark.parametrize('accepted',[False,True])
def test_public_continuation_replays_cold_and_keeps_exact_parent_fallback(tmp_path,monkeypatch,repaired,accepted):
    from nasolve.cif_component_runtime import prepare_runtime_readyset_bundle,CONTINUATION_POLICY_ID
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle,assess_runtime_bundle
    parent,_,control,_,inputs=observed(tmp_path,monkeypatch,repaired=repaired)
    original=resolve_runtime_bundle(parent);expected=[p.read_bytes() for p in original['dictionaries']]
    baseline,endpoint=native_wiring(tmp_path,monkeypatch,parent,inputs,accepted=accepted)
    out=tmp_path/'public';manifest=prepare_runtime_readyset_bundle(parent,baseline,control,out,endpoint_receipt=endpoint)
    assert manifest['policy_id']==CONTINUATION_POLICY_ID and not manifest['automatic_adoption']
    assert manifest['decision']['selected']==('readyset_checked_model' if accepted else 'verified_parent_runtime')
    moved=out.rename(tmp_path/'relocated')
    for p in list(tmp_path.iterdir()):
        if p==moved:continue
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay executed')):
        resolved=resolve_runtime_bundle(moved);summary=assess_runtime_bundle(moved)['solution_report']
    if not accepted:assert [p.read_bytes() for p in resolved['dictionaries']]==expected
    assert summary['selected_candidate']==manifest['decision']['selected'] and not summary['automatic_adoption']
    assert resolved['manifest']['unavailable_native_checks']==[dict(check='synthetic-native-charge',status='UNSUPPORTED')]
    assert inventory(moved)==before


@pytest.mark.parametrize('where',['inside','same','ancestor'])
def test_readyset_output_cannot_overlap_parent(tmp_path,monkeypatch,where):
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption
    parent,installation=parent_case(tmp_path,monkeypatch);before=inventory(parent)
    output=parent/'nested' if where=='inside' else parent if where=='same' else tmp_path
    with patch('subprocess.Popen',side_effect=AssertionError('Invalid output executed')):
        with pytest.raises(ValueError,match='overlaps'):
            audit_runtime_readyset_consumption(parent,installation,output)
    assert inventory(parent)==before


@pytest.mark.parametrize('policy',['unknown','cif-qualified-selected-runtime-readyset-bundle-v1'])
def test_parent_policy_is_checked_before_recursive_resolution(tmp_path,monkeypatch,policy):
    from nasolve import cif_runtime_readyset as module
    parent=tmp_path/'parent';parent.mkdir();(parent/'runtime_bundle.json').write_text(json.dumps({'policy_id':policy}))
    monkeypatch.setattr(module,'resolve_runtime_bundle',lambda *a:pytest.fail('Unsupported parent recursed'))
    with pytest.raises(ValueError,match='qualified original or repaired'):
        module.audit_runtime_readyset_consumption(parent,None,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_parent_mutation_during_observation_is_not_an_optional_fallback(tmp_path,monkeypatch):
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption
    parent,installation=parent_case(tmp_path,monkeypatch)
    def changed(*a,**k):
        (parent/'model/model.pdb').write_text('CHANGED');return {'status':'REVIEW'}
    monkeypatch.setattr('nasolve.cif_postmr_readyset.audit_readyset_bundle_consumption',changed)
    with pytest.raises(ValueError,match='parent runtime changed'):
        audit_runtime_readyset_consumption(parent,installation,tmp_path/'out')


@pytest.mark.parametrize('defect',['selection','parent_choice','parent_manifest','resource','rehashed_resource','extra_root','unsafe_control'])
def test_forged_public_continuation_cannot_bypass_parent_proof(tmp_path,monkeypatch,defect):
    from nasolve.cif_component_runtime import prepare_runtime_readyset_bundle
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle,_reference
    parent,_,control,_,inputs=observed(tmp_path,monkeypatch)
    out=tmp_path/'public';value=prepare_runtime_readyset_bundle(parent,None,control,out)
    if defect=='selection':value['decision']['selected']='readyset_checked_model'
    elif defect=='parent_choice':value['source_review']['parent_selected']='verified_prepared_bundle'
    elif defect=='parent_manifest':
        p=out/'evidence/runtime/runtime_bundle.json';v=json.loads(p.read_bytes());v['decision']['selected']='verified_prepared_bundle';p.write_text(json.dumps(v))
    elif defect in {'resource','rehashed_resource'}:
        r=value['resources']['dictionaries'][0];p=out/r['relative_path'];p.write_text('PRE_REPAIR_OR_OTHER')
        if defect=='rehashed_resource':
            value['resources']['dictionaries'][0]=_reference(p,out)
            value['files']=[_reference(out/r['relative_path'],out) for r in value['files']]
    elif defect=='extra_root':(out/'evidence/extra').mkdir()
    else:value['source_selection']['runtime']='../parent'
    (out/'runtime_bundle.json').write_text(json.dumps(value))
    with pytest.raises(ValueError):resolve_runtime_bundle(out)


@pytest.mark.parametrize('resource',['model','dictionary'])
def test_optional_inputs_changed_during_comparison_cannot_be_selected(tmp_path,monkeypatch,resource):
    from nasolve.cif_runtime_readyset import inspect_runtime_readyset
    parent,_,control,_,inputs=observed(tmp_path,monkeypatch)
    baseline,endpoint=native_wiring(tmp_path,monkeypatch,parent,inputs)
    def changed(*args):
        p=inputs['model'] if resource=='model' else inputs['dictionaries'][0]
        p.write_bytes(p.read_bytes()+b'\n# CHANGED_AFTER_NATIVE_BINDING\n')
        return dict(mechanics_checks_pass=True,checks={'synthetic_native_wiring':True})
    monkeypatch.setattr('nasolve.cif_postmr_cached_model.qualify_cached_model_roundtrip',changed)
    review=inspect_runtime_readyset(parent,baseline,control,endpoint)
    assert review['decision']['selected']=='verified_parent_runtime' and review['endpoint_error']


def test_atom_order_continuation_reuses_exact_evidence_and_publishes(tmp_path,monkeypatch):
    from nasolve.cif_readyset_atom_order import prepare_readyset_atom_order
    from nasolve.cif_runtime_readyset import runtime_readyset_endpoint_inputs
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_component_runtime import prepare_runtime_readyset_bundle
    parent,_,control,_,raw=observed(tmp_path,monkeypatch)
    selected=resolve_runtime_bundle(parent);order=tmp_path/'order'
    prepare_readyset_atom_order(selected['model'],raw['model'],order)
    inputs=runtime_readyset_endpoint_inputs(parent,control,atom_order_directory=order)
    baseline,endpoint=native_wiring(tmp_path,monkeypatch,parent,inputs)
    manifest=prepare_runtime_readyset_bundle(parent,baseline,control,tmp_path/'public',
        endpoint_receipt=endpoint,atom_order_directory=order)
    assert manifest['decision']['selected']=='readyset_ordered_checked_model'
    assert manifest['source_review']['atom_order_receipt_sha256']==sha256((order/'atom_order.json').read_bytes()).hexdigest()


def test_output_dot_segments_cannot_write_inside_parent(tmp_path,monkeypatch):
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption
    parent,installation=parent_case(tmp_path,monkeypatch);sibling=tmp_path/'sibling';sibling.mkdir()
    output=sibling/'..'/parent.name/'nested';before=inventory(parent)
    with patch('subprocess.Popen',side_effect=AssertionError('Overlapping output executed')):
        with pytest.raises(ValueError,match='overlaps'):
            audit_runtime_readyset_consumption(parent,installation,output)
    assert inventory(parent)==before and not (parent/'nested').exists()


def test_publication_dot_segments_cannot_create_inside_source_evidence(tmp_path,monkeypatch):
    from nasolve.cif_component_runtime import prepare_runtime_readyset_bundle
    parent,_=parent_case(tmp_path,monkeypatch);sibling=tmp_path/'sibling';sibling.mkdir()
    output=sibling/'..'/parent.name/'new-work'/'runtime';before=inventory(parent)
    with pytest.raises(ValueError,match='Cannot publish inside source evidence'):
        prepare_runtime_readyset_bundle(parent,None,None,output)
    assert inventory(parent)==before and not (parent/'new-work').exists()
