"""Explicit bond repairs use existing attempts, source gates and fallback.

Coordinator adapters below are synthetic; native chemistry/library replay has
separate controls. No PDU-specific names or decisions are used here.
"""
from pathlib import Path
import json
import os
import sys
import pytest
from tests.test_cif_prepared_repair_execution import case
from tests.test_cif_repair_attempt import setup,inventory


def test_target_choices_are_source_graph_bound_and_canonical(tmp_path):
    from nasolve.cif_prepared_repair_execution import _source_bond_target_choices
    from tests.test_cif_triple_bond_audit import fixture
    source,_=fixture(tmp_path,'Q17');before=source.read_bytes()
    q=_source_bond_target_choices({'Q17':source},{'Q17':[['Y','R'],['Y','X']]})
    assert q['choices']=={'Q17':[['R','Y'],['X','Y']]}
    assert source.read_bytes()==before and _source_bond_target_choices({},None) is None


@pytest.mark.parametrize('value',[{},[],{'OTHER':[['R','Y']]},{'Q17':[]},{'Q17':['R','Y']},
    {'Q17':[['R','Y'],['Y','R']]},{'Q17':[['L','R']]},{'Q17':[['Y','absent']]},{'Q17':[[True,'R']]}])
def test_bad_target_declarations_refuse_without_outputs(tmp_path,value):
    from nasolve.cif_prepared_repair_execution import _source_bond_target_choices
    from tests.test_cif_triple_bond_audit import fixture
    source,_=fixture(tmp_path,'Q17')
    with pytest.raises(ValueError):_source_bond_target_choices({'Q17':source},value)


@pytest.mark.parametrize('linear',[False,True])
@pytest.mark.parametrize('outcome',['pass','unsupported','no-change','library-failed','library-failed-no-policy','negative-attribution','bad-derivative','bad-reference','interrupt','changed-library','deadline','native-failed'])
def test_explicit_targets_keep_existing_source_order_derivatives_and_fallback(case,monkeypatch,linear,outcome):
    m,b,sdk,out,state,calls,options=case;state['steps']=linear;declared={'Q17':[['R','Y']]}
    config=dict(policy_id='cif-prepared-source-bond-targets-v1',choices=declared)
    monkeypatch.setattr(m,'_bond_target_choices',lambda root,value:config if value is not None else None,raising=False)
    original=m.read_dictionary_bundle
    def prepared(root):
        r=original(root);r['component_dictionaries']={'Q17':r['after_dictionaries'][0]};return r
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',lambda p:dict(source=Path(p).parents[2]/'a.cif'))
    clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    if outcome=='deadline':options['total_timeout_seconds']=20
    if outcome=='library-failed':options['optional_failure_policy']=m.FALLBACK_POLICY_ID
    def library(phenix,consumer,output,**kw):
        assert kw['timeout_seconds']==7 and output==out/'energy-library';calls.append('library')
        output.mkdir();r=dict(status='REVIEW' if outcome.startswith('library-failed') else 'SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED')
        (output/'energy_library_receipt.json').write_text(json.dumps(r));(output/'energy-library.cif').write_text('SYNTHETIC LIBRARY')
        if outcome=='interrupt':raise KeyboardInterrupt()
        if outcome=='deadline':clock[0]=21.
        return r
    monkeypatch.setattr(m,'capture_energy_library',library,raising=False)
    monkeypatch.setattr(m,'read_energy_library',lambda p:json.loads((p/'energy_library_receipt.json').read_text()),raising=False)
    def reference(*args):
        calls.append('reference');return {'bonds':[dict(atoms=['R','Y'],status='UNSUPPORTED' if outcome=='unsupported' else 'SUPPORTED')]}
    monkeypatch.setattr(m,'energy_library_linear_reference',reference,raising=False)
    def qualify(*a,**k):
        if outcome=='bad-reference':raise ValueError('Reference contradicts source')
        calls.append('reference-bound');return dict(reference_authority='EXACT_ROWS_FROM_SELECTED_NATIVE_LIBRARY')
    monkeypatch.setattr(m,'qualify_energy_reference',qualify,raising=False)
    monkeypatch.setattr(m,'compare_linear_bond_reference',lambda *a:dict(bonds=[dict(atoms=['R','Y'],target_angstrom=1.47 if outcome=='no-change' else 1.6,reference_equilibrium_angstrom=None if outcome=='unsupported' else 1.47)]),raising=False)
    def candidate(source,dictionary,code,reference,output,*,bonds):
        assert bonds==[['R','Y']] and code=='Q17';calls.append('bond-candidate');output.parent.mkdir(parents=True,exist_ok=True);output.write_text('REFERENCE TARGET')
        if outcome=='changed-library':(out/'energy-library/energy_library_receipt.json').write_text('changed')
        return dict(status='CANDIDATE_REVIEW')
    monkeypatch.setattr(m,'prepare_linear_bond_candidate',candidate,raising=False)
    def attribute(source,code,ref,before,after,index,phenix,output,**kw):
        assert index==0 and kw['bonds']==[['R','Y']] and kw['timeout_seconds']==9
        assert before.parent.parent.name==('001' if linear else '000') and after.parent.parent.name==('002' if linear else '001')
        calls.append('bond-attribution');output.mkdir();r=dict(status='REVIEW' if outcome=='negative-attribution' else 'CAPTURED_BOND_TARGET_ATTRIBUTION_PASS')
        (output/'captured_bond_attribution.json').write_text(json.dumps(r))
        if outcome=='negative-attribution':state['attribution']=False
        return r
    monkeypatch.setattr(m,'audit_captured_bond_attribution',attribute,raising=False)
    chains=[]
    def chain(planes,output,*,linear_attribution=None,bond_attributions=(),energy_library=None):
        assert planes==[] and linear_attribution==(out/'attribution' if linear else None)
        assert bond_attributions==[out/'bond-attribution-000'] and energy_library==out/'energy-library'
        chains.append(output);calls.append('chain');output.mkdir();(output/'repair_chain.json').write_text('{}')
    monkeypatch.setattr(m,'prepare_repair_chain',chain)
    old_gradient=m.audit_captured_mixed_gradients
    def gradient(receipt,sdk,output,**kwargs):
        if output.name=='original-gradient':return old_gradient(receipt,sdk,output,**kwargs)
        expected='001' if outcome in {'unsupported','no-change','library-failed','library-failed-no-policy'} else '002' if linear else '001'
        assert receipt.parent.parent.name==expected
        if outcome=='bad-derivative':state['repaired']=False
        calls.append('repaired');output.mkdir();(output/'captured_mixed_gradients.json').write_text('{}')
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradient)
    original_select=m.inspect_dictionary_bundle_repair
    def select(**kw):
        if chains:assert kw['repair_chain'] is True and kw['attribution_directory']==chains[-1]
        return original_select(**kw)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_repair',select)
    def original_selection(**kw):calls.append('original-selection');return dict(decision=dict(selected='verified_prepared_bundle'))
    def original_publication(output,**kw):output.mkdir();(output/'runtime_bundle.json').write_text(json.dumps(original_selection(**kw)))
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',original_selection)
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',original_publication)
    native=m.inspect_native_bundle
    def capture(*a,**kw):
        r=native(*a,**kw)
        if outcome=='native-failed' and a[2].name==('002' if linear else '001'):r['execution']=dict(status='FAILED',returncode=1)
        return r
    monkeypatch.setattr(m,'inspect_native_bundle',capture)
    if outcome=='native-failed':
        options['optional_failure_policy']=m.FALLBACK_POLICY_ID
        monkeypatch.setattr(m,'inspect_prepared_native_failure',lambda root,phase:dict(phase=phase,status='KNOWN_STOPPED_NATIVE_FAILURE'))
    if outcome in {'bad-reference','changed-library','deadline','interrupt','library-failed-no-policy'}:
        with pytest.raises((ValueError,m.PreparedRepairBudgetExceeded,KeyboardInterrupt)):
            m.execute_prepared_dictionary_repair(b,sdk,out,bond_targets=declared,**options)
        assert out.exists() and not (out/'repair_execution.json').exists() and not (out/'runtime').exists()
    else:
        r=m.execute_prepared_dictionary_repair(b,sdk,out,bond_targets=declared,**options)
        assert r['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME' and r['bond_targets']==config
        fallback=outcome in {'negative-attribution','bad-derivative','native-failed'} or (not linear and outcome in {'unsupported','no-change','library-failed'})
        assert r['selection']['decision']['selected']==('verified_prepared_bundle' if fallback else 'repaired_prepared_bundle')
        assert calls.index('source')<calls.index('original')<calls.index('library') and calls.count('library')==1
        if outcome in {'unsupported','no-change','library-failed','native-failed'}:assert 'bond-attribution' not in calls
        else:assert calls.index('bond-attribution')<calls.index('chain')<calls.index('repaired')
    assert all(not p.exists() for p in chains)


@pytest.mark.parametrize('phase',['energy-library','bond-attribution-000'])
def test_new_jobs_use_the_existing_stop_and_path_owner(tmp_path,phase):
    from nasolve.cif_repair_process import PreparedRepairProcesses,inspect_prepared_repair_processes
    (tmp_path/'bundle').mkdir();(tmp_path/'bundle/source.cif').write_text('SOURCE')
    owner=PreparedRepairProcesses(tmp_path);work=tmp_path/phase
    if phase!='energy-library':work=work/'job'
    work.mkdir(parents=True);log=work/('native.log' if phase=='energy-library' else 'execution.log')
    assert owner.runner(phase)([sys.executable,'-c','print("SYNTHETIC")'],cwd=work,log_path=log,environment=dict(os.environ),timeout_seconds=3)==0
    assert owner.finish('RETURNED');before=inventory(tmp_path)
    r=inspect_prepared_repair_processes(tmp_path)
    assert r['state']=='STOPPED' and r['phases'][phase]['activity'] is False and inventory(tmp_path)==before


def test_target_request_freezes_choices_and_retries_only_in_new_attempt(setup,monkeypatch):
    m,args,options,calls=setup;choices={'Q17':[['R','Y']]}
    def config(root,value):return None if value is None else dict(policy_id='cif-prepared-source-bond-targets-v1',choices=value)
    monkeypatch.setattr(m,'_bond_target_choices',config,raising=False)
    original=m.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        assert kw['bond_targets']==choices;r=original(*a,**kw);r['bond_targets']=config(a[0],choices)
        (a[2]/'repair_execution.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    first=m.execute_prepared_dictionary_repair_attempt(*args,bond_targets=choices,**options)
    saved=inventory(args[-1]/'attempts/attempt-0001')
    second=m.execute_prepared_dictionary_repair_attempt(*args,bond_targets=choices,**options)
    assert second['attempt_number']==2 and first['attempt_id']!=second['attempt_id'] and inventory(args[-1]/'attempts/attempt-0001')==saved
    assert m.inspect_prepared_repair_request(args[-1])['state']=='RECORDED'
    with pytest.raises(ValueError,match='identity differs'):
        m.execute_prepared_dictionary_repair_attempt(*args,bond_targets={'Q17':[['X','Y']]},**options)
    assert len(calls)==2


@pytest.mark.parametrize('bad',[True,[],{}, {'policy_id':'wrong','choices':{'Q17':[['R','Y']]}},
    {'policy_id':'cif-prepared-source-bond-targets-v1','choices':None}])
def test_malformed_frozen_target_configuration_refuses_as_data_error(setup,bad):
    from nasolve.campaign_records import read_record,write_record
    m,args,options,calls=setup;m.execute_prepared_dictionary_repair_attempt(*args,**options)
    path=args[-1]/'request.json';r=read_record(path);r['configuration']['bond_targets']=bad;write_record(path,r,replace=True)
    before=inventory(args[-1])
    with pytest.raises(ValueError):m.inspect_prepared_repair_request(args[-1])
    assert inventory(args[-1])==before
