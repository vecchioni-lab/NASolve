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
    from tests.helpers import pdb_record
    (bundle/'model.pdb').write_text(''.join(pdb_record('HETATM', i+1, 'C1', c, 'A', i+1, element='C')
        for i,c in enumerate(['Q17','Q18'])) + 'END\n')
    sdk=tmp_path/'sdk';sdk.mkdir()
    phenix=SimpleNamespace(root=sdk,version='TEST',environment={},
        executables={'phenix.python':sdk/'python','phenix.ready_set':sdk/'ready'})
    state={'source':True,'original':True,'repaired':True,'attribution':True,'steps':True,'consumer':True}
    calls=[]
    def prepared(p):
        p=Path(p)
        return dict(report={'consumer':{'test':'identity'},'components':['Q17','Q18']},model=p/'model.pdb',
            before_dictionaries=[p/'a.cif',p/'b.cif'],after_dictionaries=[p/'a.cif',p/'b.cif'],
            before_phils=[p/'policy.phil'],after_phils=[p/'policy.phil'],
            native_options=dict(full_monomer_inventory=True,**({'atom_name_mapping':True} if state.get('mapped') else {})))
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
    assert r['automatic_adoption'] is False and r['total_deadline']=='NOT_CONFIGURED'


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


@pytest.mark.parametrize('source,derivatives,expected', [(True,True,'QUALIFIED_DIAGNOSTIC_RUNTIME'),
    (True,False,'NO_USABLE_BUNDLE'), (False,True,'SOURCE_PREPARATION_UNQUALIFIED')])
def test_explicit_no_repair_mode_qualifies_original_independently(case,monkeypatch,source,derivatives,expected):
    m,b,sdk,out,state,calls,o=case;state.update(steps=False,source=source,original=derivatives)
    def select(**options):
        calls.append('original-selection')
        assert set(options)=={'bundle','baseline_receipt','candidate_receipt','original_gradient_directory'}
        return {'decision':{'selected':'verified_prepared_bundle' if state['original'] else None}}
    def publish(output,**options):
        calls.append('original-publication');output.mkdir()
        (output/'runtime_bundle.json').write_text(json.dumps(select(**options)))
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',select,raising=False)
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',publish,raising=False)
    result=m.execute_prepared_dictionary_repair(b,sdk,out,qualify_no_repair=True,**o)
    assert result['status']==expected and result['qualify_no_repair'] is True
    assert not {'native-001','attribution','repaired','selection','publication'} & set(calls)
    assert len(result['native_receipts'])==2 and (out/'runtime').exists()==(expected=='QUALIFIED_DIAGNOSTIC_RUNTIME')
    assert ('original' in calls)==source


@pytest.mark.parametrize('value',[1,0,None,'yes'])
def test_no_repair_mode_requires_explicit_boolean(case,value):
    m,b,sdk,out,state,calls,o=case
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair(b,sdk,out,qualify_no_repair=value,**o)
    assert not out.exists() and not calls


@pytest.mark.parametrize('original,expected',[(True,'QUALIFIED_DIAGNOSTIC_RUNTIME'),(False,'NO_USABLE_BUNDLE')])
def test_classified_optional_native_failure_can_only_select_proven_original(case,monkeypatch,original,expected):
    m,b,sdk,out,state,calls,o=case;state['original']=original;native=m.inspect_native_bundle
    def failed(*a,**k):
        value=native(*a,**k)
        if a[2].name=='001':value['execution']={'status':'TIMED_OUT','returncode':-15}
        return value
    proof={'phase':'native-001','status':'KNOWN_STOPPED_NATIVE_FAILURE'}
    monkeypatch.setattr(m,'inspect_native_bundle',failed)
    monkeypatch.setattr(m,'inspect_prepared_native_failure',lambda *a:proof,raising=False)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',lambda **k:{'decision':{'selected':'verified_prepared_bundle' if state['original'] else None}})
    def publish(output,**k):output.mkdir();(output/'runtime_bundle.json').write_text(json.dumps({'decision':{'selected':'verified_prepared_bundle'}}))
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',publish)
    result=m.execute_prepared_dictionary_repair(b,sdk,out,optional_failure_policy='cif-owned-native-failure-original-v1',**o)
    assert result['status']==expected and result['optional_failure']==proof
    assert not {'attribution','repaired','selection','publication'} & set(calls)
    assert (out/'native/001/unique-capture/native_receipt.json').exists() and (out/'runtime').exists()==original


@pytest.mark.parametrize('obstacle',['malformed','consumer','baseline','initial','exception'])
def test_failure_policy_never_swallows_unsafe_or_initial_failure(case,monkeypatch,obstacle):
    m,b,sdk,out,state,calls,o=case;native=m.inspect_native_bundle;consumer=m.verify_current_consumer;seen=[0]
    def failed(*a,**k):
        value=native(*a,**k)
        target='baseline' if obstacle=='baseline' else '000' if obstacle=='initial' else '001'
        if a[2].name==target:
            if obstacle=='exception':raise ValueError('adapter contradicted evidence')
            value['execution']={'status':'TIMED_OUT','returncode':-15}
        return value
    def classify(*a):
        if obstacle=='malformed':raise ValueError('malformed failure evidence')
        return {'phase':'native-001','status':'KNOWN_STOPPED_NATIVE_FAILURE'}
    def current(*a):seen[0]+=1;return False if obstacle=='consumer' and seen[0]>1 else consumer(*a)
    monkeypatch.setattr(m,'inspect_native_bundle',failed);monkeypatch.setattr(m,'inspect_prepared_native_failure',classify)
    monkeypatch.setattr(m,'verify_current_consumer',current)
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair(b,sdk,out,optional_failure_policy=m.FALLBACK_POLICY_ID,**o)
    assert not (out/'runtime').exists() and not (out/'repair_execution.json').exists()


@pytest.mark.parametrize('policy',[True,False,'UNKNOWN',1])
def test_unknown_failure_policy_refuses_before_side_effects(case,policy):
    m,b,sdk,out,state,calls,o=case
    with pytest.raises(ValueError):m.execute_prepared_dictionary_repair(b,sdk,out,optional_failure_policy=policy,**o)
    assert not out.exists() and not calls


@pytest.mark.parametrize('bystander', ['DG', 'Z81'])
def test_repair_plan_covers_model_components_outside_selected_dictionary_owners(case, monkeypatch, tmp_path, bystander):
    from tests.helpers import pdb_record
    from tests.test_cif_linear_torsion_candidate import dictionary
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle, read_linear_torsion_bundle
    m, source, sdk, output, state, calls, options = case
    graph = tmp_path / 'graph'; graph.mkdir()
    dictionary_path, _ = dictionary(graph, 'Q17')
    (source / 'a.cif').write_bytes(dictionary_path.read_bytes())
    (source / 'b.cif').write_text('data_mod_control\n_chem_mod.id control\n')
    (source / 'model.pdb').write_text(''.join(
        pdb_record('HETATM', i + 1, 'C1', code, 'A', i + 1, element='C')
        for i, code in enumerate(['Q17', 'Q18', bystander])) + 'END\n')
    before = m._tree(source)

    class Planned(Exception):
        pass

    def stop_after_real_plan(dictionaries, codes, destination):
        prepare_linear_torsion_bundle(dictionaries, codes, destination)
        raise Planned

    monkeypatch.setattr(m, 'prepare_linear_torsion_bundle', stop_after_real_plan)
    with pytest.raises(Planned):
        m.execute_prepared_dictionary_repair(source, sdk, output, **options)
    plan = read_linear_torsion_bundle(output / 'plan')
    assert plan['modeled_components'] == sorted(['Q17', 'Q18', bystander])
    assert next(row for row in plan['scan'] if row['component'] == bystander) == {
        'component': bystander, 'status': 'NO_EXPLICIT_DICTIONARY'}
    assert [step['component'] for step in plan['steps']] == ['Q17']
    assert plan['steps'][0]['plan']['removed_torsion_count'] == 1
    assert m._tree(source) == before and calls == ['consumer']
    assert not (output / 'runtime').exists() and not plan['automatic_adoption']


@pytest.mark.parametrize('linear', [False, True])
@pytest.mark.parametrize('outcome',['pass','unsupported','bad-evidence','negative-attribution','bad-final-derivative','native-timeout','changed-support','ownership-error','classified-plane-timeout','publication-error'])
def test_plane_support_uses_existing_repair_owner_and_final_selector(case, monkeypatch, linear, outcome):
    from nasolve.campaign_process import CampaignProcessError
    m,b,sdk,out,state,calls,options=case
    state['steps']=linear
    generation=b.parent/'generation';generation.mkdir();(generation/'proof').write_text('owned support')
    declared={'Q17':dict(request_directory=generation,attempt_number=1)}
    def snapshot(bundle, choices):
        assert choices['Q17']['attempt_number']==1
        return dict(policy_id='test-owned-support',choices={'Q17':1},files={'Q17/proof':{'size':13}},directories=['Q17']), {'Q17/proof':b'owned support'}
    monkeypatch.setattr(m,'_plane_support_snapshot',snapshot)
    original=m.read_dictionary_bundle
    def prepared(path):
        result=original(path);result['component_dictionaries']={'Q17':result['after_dictionaries'][0]}
        return result
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',lambda p:dict(source=b/'a.cif'))
    def candidate(source,dictionary,code,request,attempt,output):
        assert code=='Q17' and attempt==1 and request==out/'plane-support/Q17'
        if outcome=='unsupported':raise m.UnsupportedPlaneCompletion('Source supplies no admissible missing row')
        if outcome=='bad-evidence':raise ValueError('Contradictory plane proof')
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text('plane candidate')
        if outcome=='changed-support':(out/'plane-support/Q17/proof').write_text('changed')
        calls.append('plane-candidate');return dict(status='CANDIDATE_REVIEW')
    monkeypatch.setattr(m,'prepare_owned_trigonal_plane_candidate',candidate)
    def plane(source,code,request,attempt,before,after,index,phenix,output,**kwargs):
        assert index==0 and kwargs['timeout_seconds']==9
        assert before.parent.parent.name==('001' if linear else '000')
        assert after.parent.parent.name==('002' if linear else '001')
        if outcome=='ownership-error':raise CampaignProcessError('Unknown plane process')
        output.mkdir();calls.append('plane-attribution')
        (output/'captured_plane_attribution.json').write_text('{}')
        if outcome=='negative-attribution':state['attribution']=False
        return dict(status='REVIEW' if outcome=='negative-attribution' else 'CAPTURED_PLANE_ATTRIBUTION_PASS')
    monkeypatch.setattr(m,'audit_captured_plane_attribution',plane)
    chain_paths=[]
    def chain(planes, output, *, linear_attribution=None):
        chain_paths.append(output)
        assert planes==[out/'plane-attribution-000']
        assert linear_attribution==(out/'attribution' if linear else None)
        output.mkdir();(output/'repair_chain.json').write_text('{}');calls.append('chain')
    monkeypatch.setattr(m,'prepare_repair_chain',chain)
    old_gradient=m.audit_captured_mixed_gradients
    def gradient(receipt,sdk,output,**kwargs):
        if output.name=='original-gradient':return old_gradient(receipt,sdk,output,**kwargs)
        assert receipt.parent.parent.name==('001' if outcome=='unsupported' else '002' if linear else '001')
        if outcome=='bad-final-derivative':state['repaired']=False
        output.mkdir();(output/'captured_mixed_gradients.json').write_text('{}');calls.append('repaired')
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradient)
    old_select=m.inspect_dictionary_bundle_repair
    def select(**kwargs):
        if outcome=='unsupported':assert 'repair_chain' not in kwargs and kwargs['attribution_directory']==out/'attribution'
        else:assert kwargs['repair_chain'] is True and kwargs['attribution_directory']==chain_paths[-1]
        return old_select(**kwargs)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_repair',select)
    def original_selection(**kwargs):
        return dict(decision=dict(selected='verified_prepared_bundle'))
    def original_publication(output,**kwargs):
        output.mkdir();(output/'runtime_bundle.json').write_text(json.dumps(original_selection(**kwargs)))
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',original_selection)
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',original_publication)
    native=m.inspect_native_bundle
    def capture(*a,**kw):
        value=native(*a,**kw)
        if outcome in {'native-timeout','classified-plane-timeout'} and a[2].name==('002' if linear else '001'):
            value['execution']=dict(status='TIMED_OUT',returncode=-15)
        return value
    monkeypatch.setattr(m,'inspect_native_bundle',capture)
    if outcome=='classified-plane-timeout':
        options['optional_failure_policy']=m.FALLBACK_POLICY_ID
        monkeypatch.setattr(m,'inspect_prepared_native_failure',lambda root,phase:dict(phase=phase,status='KNOWN_STOPPED_NATIVE_FAILURE'))
    if outcome=='publication-error':
        def fail_publication(**kwargs):raise OSError('Synthetic publication failure')
        monkeypatch.setattr(m,'prepare_repaired_component_runtime_bundle',fail_publication)
    if outcome in {'bad-evidence','native-timeout','changed-support','ownership-error','publication-error'}:
        with pytest.raises((ValueError,CampaignProcessError,OSError)):
            m.execute_prepared_dictionary_repair(b,sdk,out,plane_support=declared,**options)
        assert out.exists() and not (out/'runtime').exists()
        assert not (out/'repair_execution.json').exists()
        assert all(not p.exists() for p in chain_paths)
        return
    r=m.execute_prepared_dictionary_repair(b,sdk,out,plane_support=declared,**options)
    assert r['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME' and r['plane_support']['choices']=={'Q17':1}
    assert all(not p.exists() for p in chain_paths)
    if outcome=='classified-plane-timeout':
        assert r['selection']['decision']['selected']=='verified_prepared_bundle'
        assert r['plane_results'][0]['status']=='KNOWN_STOPPED_NATIVE_FAILURE'
        assert 'chain' not in calls and 'repaired' not in calls
    elif outcome=='unsupported':
        assert r['plane_results'][0]['status']=='NO_SUPPORTED_PLANE_COMPLETION'
        assert 'plane-attribution' not in calls and 'chain' not in calls
        assert len(r['native_receipts'])==(3 if linear else 2)
    else:
        assert calls.index('plane-attribution') < calls.index('chain') < calls.index('repaired')
        assert len(r['native_receipts'])==(4 if linear else 3)
        assert r['selection']['decision']['selected']==('verified_prepared_bundle'
            if outcome in {'negative-attribution','bad-final-derivative'} else 'repaired_prepared_bundle')


def test_retained_terminal_capture_uses_frozen_native_options(case,monkeypatch):
    m,b,sdk,out,state,calls,o=case;state['mapped']=True;original=m.inspect_native_bundle;seen=[]
    def native(*args,**kwargs):
        seen.append(kwargs.get('atom_name_mapping'));return original(*args,**kwargs)
    monkeypatch.setattr(m,'inspect_native_bundle',native)
    assert m.execute_prepared_dictionary_repair(b,sdk,out,**o)['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME'
    assert seen==[True,True,True]
