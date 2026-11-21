"""Frozen proposal integration uses real source/reference readers, synthetic capture."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import pytest
from tests.test_cif_energy_library import case, fake_runner
from tests.test_cif_repair_attempt import inventory


@pytest.fixture
def discovery(tmp_path,monkeypatch):
    from nasolve import cif_prepared_bond_discovery as m
    from nasolve.cif_energy_library import capture_energy_library
    sdk,consumer,source,library=case(tmp_path)
    root=tmp_path/'execution';bundle=root/'bundle';bundle.mkdir(parents=True)
    frozen=bundle/'source.cif';frozen.write_bytes(source.read_bytes())
    dictionary=root/'plan/0.cif';dictionary.parent.mkdir();dictionary.write_bytes(source.read_bytes())
    def prepared(p):
        p=Path(p)
        return dict(report=dict(components=['Q17'],consumer=consumer),
            after_dictionaries=[p/'source.cif'],component_dictionaries={'Q17':p/'source.cif'})
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',lambda p:dict(source=Path(p).parents[2]/'source.cif'))
    capture_energy_library(sdk,consumer,root/'energy-library',_process_runner=fake_runner(library))
    return m,root,dictionary,sdk,source,consumer


def test_real_discovery_plan_is_frozen_replayable_and_passes_existing_choices(discovery):
    m,root,dictionary,sdk,source,consumer=discovery
    before=inventory(root)
    with patch('subprocess.Popen',side_effect=AssertionError('Discovery cannot execute')):
        record=m.bond_discovery_plan(root,[dictionary])
    assert record['choices']=={'Q17':[['L','X']]} and record['status']=='DISCOVERED'
    assert record['proposals']['Q17']['new_native_calls']==0
    assert record['queries']['Q17']['selected_bonds'] and inventory(root)==before
    assert m.read_bond_discovery_plan(root,[dictionary],record)==record
    moved=root.rename(root.with_name('moved'));shutil.rmtree(sdk.root);source.unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read cannot execute')):
        assert m.read_bond_discovery_plan(moved,[moved/'plan/0.cif'],record)==record


@pytest.mark.parametrize('field',['choices','dictionary','source','policy','proposal','library'])
def test_discovery_plan_rejects_detached_or_edited_decisions_read_only(discovery,field):
    m,root,dictionary,*_=discovery;record=m.bond_discovery_plan(root,[dictionary]);bad=deepcopy(record)
    if field=='choices':bad['choices']={'Q17':[['R','Y']]}
    elif field=='dictionary':dictionary.write_text(dictionary.read_text()+'# changed dictionary\n')
    elif field=='source':(root/'bundle/source.cif').write_text((root/'bundle/source.cif').read_text()+'# changed source\n')
    elif field=='policy':bad['policy_id']='unknown'
    elif field=='proposal':bad['proposals']['Q17']['automatic_adoption']=True
    else:(root/'energy-library/energy-library.cif').write_text('data_changed\n')
    before=inventory(root)
    with pytest.raises(ValueError):m.read_bond_discovery_plan(root,[dictionary],bad)
    assert inventory(root)==before


@pytest.mark.parametrize('value',[None,1,[],{},'yes'])
def test_discovery_intent_requires_real_boolean(value):
    from nasolve.cif_prepared_bond_discovery import bond_discovery_fields
    with pytest.raises(ValueError):bond_discovery_fields(value)


def test_explicit_and_automatic_choices_cannot_compete():
    from nasolve.cif_prepared_bond_discovery import bond_discovery_fields,POLICY_ID
    assert bond_discovery_fields(False)=={}
    assert bond_discovery_fields(True)=={'bond_discovery_policy':POLICY_ID}
    with pytest.raises(ValueError):bond_discovery_fields(True,{'Q17':[['L','X']]})


# Native captures/derivatives below are synthetic coordinator controls. Source
# graph, library capture reader, discovery, candidate writer and cold replay are real.
from tests.test_cif_prepared_repair_execution import case as execution_case


@pytest.fixture
def automatic_execution(execution_case,tmp_path,monkeypatch):
    from nasolve import cif_prepared_bond_discovery as binding
    from nasolve.cif_energy_library import capture_energy_library
    m,b,sdk,out,state,calls,options=execution_case;state['steps']=False
    chemical=tmp_path/'chemical';chemical.mkdir()
    native,consumer,source,library=case(chemical)
    (b/'a.cif').write_bytes(source.read_bytes())
    (b/'b.cif').write_text(source.read_text().replace('Q17','Q18'))
    original=m.read_dictionary_bundle
    def prepared(root):
        value=original(root);value['report']['consumer']=consumer
        value['component_dictionaries']={'Q17':Path(root)/'a.cif','Q18':Path(root)/'b.cif'}
        return value
    def source_at(p):return dict(source=Path(p).parents[2]/('a.cif' if Path(p).parent.name=='Q17' else 'b.cif'))
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(binding,'read_dictionary_bundle',prepared)
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',source_at)
    monkeypatch.setattr(binding,'resolve_dictionary_snapshot',source_at)
    def lookup(sdk,consumer,out,**kw):
        calls.append('library')
        return capture_energy_library(native,consumer,out,timeout_seconds=kw['timeout_seconds'],
            _process_runner=fake_runner(library,state.get('lookup','pass')))
    monkeypatch.setattr(m,'capture_energy_library',lookup)
    def attribution(source,code,ref,before,after,index,sdk,out,**kw):
        assert kw['bonds']==[['L','X']] and index==int(code=='Q18')
        calls.append('bond-attribution');out.mkdir()
        result=dict(status='CAPTURED_BOND_TARGET_ATTRIBUTION_PASS' if state['attribution'] else 'REVIEW')
        (out/'captured_bond_attribution.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(m,'audit_captured_bond_attribution',attribution)
    def chain(planes,out,**kw):
        assert planes==[] and kw['bond_attributions'];calls.append('chain');out.mkdir()
        (out/'repair_chain.json').write_text('{}')
    monkeypatch.setattr(m,'prepare_repair_chain',chain)
    gradient=m.audit_captured_mixed_gradients
    def gradients(receipt,sdk,out,**kw):
        if out.name=='original-gradient':return gradient(receipt,sdk,out,**kw)
        calls.append('repaired');out.mkdir();(out/'captured_mixed_gradients.json').write_text('{}')
    monkeypatch.setattr(m,'audit_captured_mixed_gradients',gradients)
    def select_original(**kw):return dict(decision=dict(selected='verified_prepared_bundle' if state['original'] else None))
    def publish_original(output,**kw):
        output.mkdir();(output/'runtime_bundle.json').write_text(json.dumps(select_original(**kw)))
    monkeypatch.setattr(m,'inspect_dictionary_bundle_original',select_original)
    monkeypatch.setattr(m,'prepare_original_component_runtime_bundle',publish_original)
    return execution_case,binding


@pytest.mark.parametrize('outcome',['pass','one-match','all-match','nuclear','no-triple','source-unqualified',
    'lookup-failed','no-fallback-policy','interrupt','bad-derivative','negative-attribution','native-failed'])
def test_automatic_choices_use_real_discovery_and_existing_native_gates(automatic_execution,monkeypatch,outcome):
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.ligand_profiles import _emit
    (m,b,sdk,out,state,calls,options),binding=automatic_execution
    for code,name in [('Q17','a.cif'),('Q18','b.cif')]:
        values=_values(b/name,code)
        if outcome=='all-match' or (outcome=='one-match' and code=='Q18'):
            values['_chem_comp_bond.value_dist'][0]='1.470'
        elif outcome=='nuclear':values['_chem_comp_bond.value_dist_nucleus']=['.']*len(values['_chem_comp_bond.atom_id_1'])
        elif outcome=='no-triple':values['_chem_comp_bond.value_order']=['SING']*len(values['_chem_comp_bond.atom_id_1'])
        (b/name).write_text(_emit(values))
    if outcome=='source-unqualified':state['source']=False
    if outcome in {'lookup-failed','no-fallback-policy'}:state['lookup']='failed'
    if outcome=='lookup-failed':options['optional_failure_policy']=m.FALLBACK_POLICY_ID
    if outcome=='interrupt':state['lookup']='interrupt'
    if outcome=='bad-derivative':state['repaired']=False
    if outcome=='negative-attribution':state['attribution']=False
    if outcome=='native-failed':
        options['optional_failure_policy']=m.FALLBACK_POLICY_ID;native=m.inspect_native_bundle
        def failed(*a,**kw):
            result=native(*a,**kw)
            if a[2].name=='001':result['execution']=dict(status='FAILED',returncode=1)
            return result
        monkeypatch.setattr(m,'inspect_native_bundle',failed)
        monkeypatch.setattr(m,'inspect_prepared_native_failure',lambda root,phase:dict(phase=phase,status='KNOWN_STOPPED_NATIVE_FAILURE'))
    before=inventory(b)
    if outcome in {'interrupt','no-fallback-policy'}:
        with pytest.raises((KeyboardInterrupt,ValueError)):
            m.execute_prepared_dictionary_repair(b,sdk,out,automatic_bond_targets=True,**options)
        assert not (out/'repair_execution.json').exists() and not (out/'runtime').exists()
        assert (out/'energy-library/spec.json').exists()
    else:
        result=m.execute_prepared_dictionary_repair(b,sdk,out,automatic_bond_targets=True,**options)
        assert result['bond_discovery_policy']==binding.POLICY_ID and 'bond_targets' not in result
        assert calls.count('library')==(0 if outcome in {'no-triple','source-unqualified'} else 1)
        if outcome in {'no-triple','source-unqualified'}:assert 'bond_discovery' not in result
        else:
            record=json.loads((out/'bond_discovery.json').read_text())
            selected=outcome not in {'all-match','nuclear','lookup-failed'}
            assert bool(record['choices'])==selected
            if outcome=='one-match':assert list(record['choices'])==['Q17']
            if selected:
                assert calls.index('source')<calls.index('original')<calls.index('library')
                assert len(result['bond_plans'])==(1 if outcome in {'one-match','native-failed'} else 2)
            expected='repaired_prepared_bundle' if outcome in {'pass','one-match'} else 'verified_prepared_bundle'
            assert result['selection']['decision']['selected']==expected
        evidence=inventory(out)
        with patch('subprocess.Popen',side_effect=AssertionError('Readback cannot execute')):
            binding.validate_prepared_bond_discovery(out,result)
        assert inventory(out)==evidence
    assert inventory(b)==before


@pytest.mark.parametrize('defect',['drop','rechoose','dictionary','stage','consumer','library'])
def test_completed_discovery_cannot_be_detached_or_rechosen(automatic_execution,defect):
    from nasolve.cif_mixed_geometry import _ref
    (m,b,sdk,out,state,calls,options),binding=automatic_execution
    result=m.execute_prepared_dictionary_repair(b,sdk,out,automatic_bond_targets=True,**options)
    if defect=='drop':result.pop('bond_discovery')
    elif defect=='stage':
        ref=result['bond_plans'][0];p=out/ref['path'];row=json.loads(p.read_text());row['requested_bonds']=[['R','Y']]
        p.write_text(json.dumps(row));result['bond_plans'][0]=_ref(p,out,'repair_directory')
    elif defect=='dictionary':(out/'plan/0.cif').write_text((out/'plan/0.cif').read_text()+'# changed\n')
    elif defect=='library':(out/'energy-library/energy-library.cif').write_text('data_changed\n')
    elif defect=='consumer':
        original=binding.read_dictionary_bundle
        def changed(root):
            r=deepcopy(original(root));r['report']['consumer']['version']='different';return r
        binding.read_dictionary_bundle=changed
    else:
        p=out/'bond_discovery.json';row=json.loads(p.read_text());row['choices']={}
        p.write_text(json.dumps(row));result['bond_discovery']=_ref(p,out,'repair_directory')
    before=inventory(out)
    with pytest.raises(ValueError):binding.validate_prepared_bond_discovery(out,result)
    assert inventory(out)==before
