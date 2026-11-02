"""Coordinator wiring with synthetic adapters; real chemistry is tested separately."""
from pathlib import Path
from types import SimpleNamespace
import json
import shutil
import pytest


@pytest.fixture
def case(tmp_path,monkeypatch):
    from nasolve import cif_prepared_repair_execution as m
    bundle=tmp_path/'source';bundle.mkdir()
    for name in ('model.pdb','a.cif','b.cif','policy.phil','bundle_receipt.json'):
        (bundle/name).write_text('SYNTHETIC '+name)
    sdk=tmp_path/'sdk';sdk.mkdir()
    phenix=SimpleNamespace(root=sdk,version='TEST',environment={},
        executables={'phenix.python':sdk/'python','phenix.ready_set':sdk/'ready'})
    state={'source':True,'original':True,'repaired':True,'attribution':True,'steps':True,'consumer':True}
    calls=[]
    def prepared(p):
        p=Path(p)
        return dict(report={'consumer':{'test':'identity'},'components':['Q17','Q18']},model=p/'model.pdb',
            before_dictionaries=[p/'a.cif',p/'b.cif'],after_dictionaries=[p/'a.cif',p/'b.cif'],
            before_phils=[p/'policy.phil'],after_phils=[p/'policy.phil'])
    def plan(ds,codes,out):
        assert codes==['Q17','Q18'];out.mkdir()
        for i,d in enumerate(ds):shutil.copyfile(d,out/f'{i}.cif')
        (out/'candidate.cif').write_text('SYNTHETIC REPAIR')
        inputs=[{'path':'0.cif'},{'path':'1.cif'}];final=[{'path':'candidate.cif'},{'path':'1.cif'}]
        value=dict(inputs=inputs,steps=[dict(dictionaries_after=final)] if state['steps'] else [])
        (out/'linear_torsion_bundle.json').write_text(json.dumps(value));return value
    def consumer(*a):calls.append('consumer');return state['consumer']
    def native(model,ds,out,executable,**kwargs):
        calls.append('native-'+out.name)
        assert kwargs['full_monomer_inventory'] and kwargs['policy_inventory'] and kwargs['energy_inventory']
        assert kwargs['inventory_detail']=='linked' and kwargs['phil_namespace_policy']=='refinement-root-to-interpreter-v1'
        assert kwargs['timeout_seconds']==7
        child=out/'unique-capture';child.mkdir(parents=True)
        (child/'native_receipt.json').write_text(json.dumps({'stage':out.name}))
        return {'native_directory':str(child),'execution':{'status':'COMPLETED','returncode':0}}
    def source(root,before,after):
        calls.append('source');assert before.parent.parent.name=='baseline' and after.parent.parent.name=='000'
        return dict(diagnostic_continuation=dict(allowed=state['source']))
    def gradients(receipt,sdk,out,**kwargs):
        label='original' if out.name=='original-gradient' else 'repaired';calls.append(label)
        assert receipt.parent.parent.name==('000' if label=='original' else '001') and kwargs['timeout_seconds']==11
        out.mkdir();value={'status':'CAPTURED_MIXED_DERIVATIVES_PASS' if state[label] else 'REVIEW'}
        (out/'captured_mixed_gradients.json').write_text(json.dumps(value));return value
    def attribution(plan,receipts,sdk,out,**kwargs):
        calls.append('attribution');assert [p.parent.parent.name for p in receipts]==['000','001'] and kwargs['timeout_seconds']==9
        out.mkdir();value={'status':'CAPTURED_LINEAR_ATTRIBUTION_PASS' if state['attribution'] else 'REVIEW'}
        (out/'captured_linear_attribution.json').write_text(json.dumps(value));return value
    def select(**options):
        calls.append('selection')
        assert options['original_gradient_directory'].name=='original-gradient'
        assert options['repaired_gradient_directory'].name=='repaired-gradient'
        return {'decision':{'selected':('repaired_prepared_bundle' if state['repaired'] and state['attribution'] else
            'verified_prepared_bundle' if state['original'] else None)}}
    def publish(output,**options):
        calls.append('publication');output.mkdir()
        value=select(**options);(output/'runtime_bundle.json').write_text(json.dumps(value));return value
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'verify_current_consumer',consumer)
    monkeypatch.setattr(m,'prepare_linear_torsion_bundle',plan)
    monkeypatch.setattr(m,'inspect_native_bundle',native)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_native',source)
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradients)
    monkeypatch.setattr(m,'audit_captured_linear_attribution',attribution)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_repair',select)
    monkeypatch.setattr(m,'prepare_repaired_component_runtime_bundle',publish)
    monkeypatch.setattr(m,'resolve_runtime_bundle',lambda p:dict(manifest=json.loads((p/'runtime_bundle.json').read_text())))
    return m,bundle,phenix,tmp_path/'execution',state,calls,dict(native_timeout_seconds=7,attribution_timeout_seconds=9,derivative_timeout_seconds=11)


@pytest.mark.parametrize('original,repaired,attribution,selected',[
 (True,True,True,'repaired_prepared_bundle'),(False,True,True,'repaired_prepared_bundle'),
 (True,False,True,'verified_prepared_bundle'),(True,True,False,'verified_prepared_bundle'),(False,False,True,None)])
def test_uses_existing_source_derivative_attribution_and_selection_gates(case,original,repaired,attribution,selected):
    m,b,sdk,out,state,calls,options=case;state.update(original=original,repaired=repaired,attribution=attribution)
    before=m._tree(b);r=m.execute_prepared_dictionary_repair(b,sdk,out,**options)
    assert r['selection']['decision']['selected']==selected and m._tree(b)==before
    assert calls[:9]==['consumer','native-baseline','native-000','source','original','native-001','attribution','repaired','selection']
    assert (out/'runtime').exists()==bool(selected) and len(r['native_receipts'])==3
    assert r['status']==('QUALIFIED_DIAGNOSTIC_RUNTIME' if selected else 'NO_USABLE_BUNDLE')
    assert r['automatic_adoption'] is False and r['total_deadline']=='NOT_IMPLEMENTED'


def test_no_graph_fault_does_not_claim_native_usability_or_launch_jobs(case):
    m,b,sdk,out,state,calls,o=case;state['steps']=False
    r=m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert r['status']=='NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED'
    assert calls==['consumer'] and r['runtime'] is None and r['selection'] is None


def test_source_qualification_refusal_stops_before_numerical_repair(case):
    m,b,sdk,out,state,calls,o=case;state['source']=False
    r=m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert r['status']=='SOURCE_PREPARATION_UNQUALIFIED' and calls==['consumer','native-baseline','native-000','source']
    assert not (out/'original-gradient').exists() and not (out/'runtime').exists()


@pytest.mark.parametrize('adapter',['inspect_native_bundle','inspect_dictionary_bundle_native','audit_captured_mixed_gradients','audit_captured_linear_attribution','inspect_dictionary_bundle_repair'])
def test_adapter_exception_never_becomes_usable_fallback(case,monkeypatch,adapter):
    m,b,sdk,out,state,calls,o=case
    def fail(*a,**k):raise ValueError('Contradictory evidence')
    monkeypatch.setattr(m,adapter,fail)
    with pytest.raises(ValueError,match='Contradictory'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert (out/'bundle').exists() and not (out/'runtime').exists() and not (out/'repair_execution.json').exists()
    assert 'NO_RECOVERY_AUTHORITY' in (out/'progress.jsonl').read_text()


@pytest.mark.parametrize('phase',['baseline','000','001'])
def test_failed_native_capture_retains_outputs_without_selection(case,monkeypatch,phase):
    m,b,sdk,out,state,calls,o=case;original=m.inspect_native_bundle
    def native(*a,**k):
        r=original(*a,**k)
        if a[2].name==phase:r['execution']={'status':'TIMED_OUT','returncode':-9}
        return r
    monkeypatch.setattr(m,'inspect_native_bundle',native)
    with pytest.raises(ValueError,match='did not complete'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert (out/'native'/phase/'unique-capture/native_receipt.json').is_file() and not (out/'runtime').exists()


@pytest.mark.parametrize('target',['source','frozen'])
def test_input_mutation_during_qualification_stops_before_publication(case,monkeypatch,target):
    m,b,sdk,out,state,calls,o=case;original=m.audit_captured_mixed_gradients
    def gradient(*a,**k):
        value=original(*a,**k);((b if target=='source' else out/'bundle')/'a.cif').write_text('OTHER SOURCE');return value
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradient)
    with pytest.raises(ValueError,match='changed'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert not (out/'attribution').exists() and not (out/'runtime').exists()


@pytest.mark.parametrize('field,value',[('native_timeout_seconds',0),('native_timeout_seconds',True),('native_timeout_seconds',601),
 ('attribution_timeout_seconds',301),('derivative_timeout_seconds',float('inf')),('derivative_timeout_seconds',0)])
def test_invalid_deadlines_refuse_before_outputs(case,field,value):
    m,b,sdk,out,state,calls,o=case;o[field]=value
    with pytest.raises(ValueError,match='bounded'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert not out.exists() and calls==[]


@pytest.mark.parametrize('obstacle',['existing','source_overlap','installation_overlap','symlink_parent','file_parent','consumer'])
def test_preflight_refuses_without_native_work_or_mutation(case,obstacle):
    m,b,sdk,out,state,calls,o=case
    if obstacle=='existing':out.mkdir();(out/'sentinel').write_text('keep')
    elif obstacle=='source_overlap':out=b/'child'
    elif obstacle=='installation_overlap':out=sdk.root/'child'
    elif obstacle=='symlink_parent':
        link=out.with_name('link');link.symlink_to(sdk.root,target_is_directory=True);out=link/'child'
    elif obstacle=='file_parent':out.write_text('keep');out=out/'child'
    else:state['consumer']=False
    before=m._tree(b)
    with pytest.raises((ValueError,FileExistsError)):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert m._tree(b)==before and not any(c.startswith('native') for c in calls)


def test_native_receipt_from_another_phase_is_rejected(case,monkeypatch):
    m,b,sdk,out,state,calls,o=case;original=m.inspect_native_bundle
    def native(*a,**k):
        r=original(*a,**k);r['native_directory']=str(b);return r
    monkeypatch.setattr(m,'inspect_native_bundle',native)
    with pytest.raises(ValueError,match='another phase'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert not (out/'runtime').exists()


def test_completed_directory_is_never_resumed_or_overwritten(case):
    m,b,sdk,out,state,calls,o=case;m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    before=m._tree(out);count=len(calls)
    with pytest.raises(FileExistsError):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert m._tree(out)==before and len(calls)==count


@pytest.mark.parametrize('artifact',['receipt','plan'])
def test_changed_execution_reference_refuses_before_runtime_publication(case,monkeypatch,artifact):
    m,b,sdk,out,state,calls,o=case;original=m.audit_captured_mixed_gradients
    def gradient(*a,**k):
        value=original(*a,**k)
        path=a[0] if artifact=='receipt' else out/'plan/linear_torsion_bundle.json'
        path.write_bytes(path.read_bytes()+b' ')
        return value
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradient)
    with pytest.raises(ValueError,match='reference changed'):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert not (out/'runtime').exists()


@pytest.mark.parametrize('error',[KeyboardInterrupt,SystemExit])
def test_interruption_preserves_partial_work_and_grants_no_retry(case,monkeypatch,error):
    m,b,sdk,out,state,calls,o=case
    def interrupt(*a,**k):raise error('synthetic coordinator interruption')
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',interrupt)
    with pytest.raises(error):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
    assert (out/'native/000/unique-capture/native_receipt.json').exists()
    assert not (out/'runtime').exists() and not (out/'repair_execution.json').exists()
    assert 'NO_RECOVERY_AUTHORITY' in (out/'progress.jsonl').read_text()
    with pytest.raises(FileExistsError):m.execute_prepared_dictionary_repair(b,sdk,out,**o)
