"""Honest preparation outcomes; native qualification belongs to the existing reader."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest


def selected_result(tmp_path, selected='readyset_checked_model', status='QUALIFIED_DIAGNOSTIC_RUNTIME'):
    root=tmp_path/'run/PostMR/DictionaryEngine/request/attempts/attempt-0001'
    root.mkdir(parents=True)
    runtime=dict(model=root/'model.pdb',dictionaries=[root/'first.cif',root/'second.cif'],
                 phils=[root/'pairs.phil',root/'stacking.phil'],
                 manifest_path=root/'runtime_bundle.json',manifest=dict(decision=dict(selected=selected)))
    return dict(result=dict(status=status),construction_inputs={'already_validated':True},
                runtime=runtime if status=='QUALIFIED_DIAGNOSTIC_RUNTIME' else None,
                continuation=dict(report=dict(phases={'baseline':'COMPLETED','readyset':'FAILED' if selected=='verified_parent_runtime' else 'COMPLETED','endpoint':'COMPLETED'})) if status=='QUALIFIED_DIAGNOSTIC_RUNTIME' else None)


@pytest.mark.parametrize('choice',['readyset_checked_model','readyset_ordered_checked_model','verified_parent_runtime'])
def test_exact_result_uses_existing_reader_once_and_keeps_matching_order(tmp_path,monkeypatch,choice):
    import nasolve.cif_ordinary_postmr as m
    exact=selected_result(tmp_path,choice);calls=[]
    def read(root,number):calls.append((root,number));return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',read)
    with patch('subprocess.Popen',side_effect=AssertionError('Reading must not launch tools')):
        result=m.read_ordinary_postmr_result(tmp_path/'run',attempt_number=1)
    assert calls==[(tmp_path/'run/PostMR/DictionaryEngine/request',1)]
    assert result.model_path==exact['runtime']['model']
    assert result.dictionary_paths==tuple(exact['runtime']['dictionaries'])
    assert result.restraint_paths==tuple(exact['runtime']['phils'])
    assert result.selected==choice and result.refinement_ready is False
    assert result.readyset_status==('FAILED' if choice=='verified_parent_runtime' else 'COMPLETED')
    assert ('retained' in result.message.lower()) == (choice=='verified_parent_runtime')
    assert 'refinement' in ' '.join(result.limitations).lower()
    assert 'no recorded automatic plane-generation outcome' in ' '.join(result.limitations)
    assert 'still needs integration' not in ' '.join(result.limitations)
    assert not (tmp_path/'run/report.json').exists() and not (tmp_path/'run/PostMR/report.json').exists()


@pytest.mark.parametrize('status',['NO_USABLE_BUNDLE','SOURCE_PREPARATION_UNQUALIFIED','NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED'])
def test_unqualified_result_cannot_expose_a_model_as_ready(tmp_path,monkeypatch,status):
    import nasolve.cif_ordinary_postmr as m
    exact=selected_result(tmp_path,status=status)
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    result=m.read_ordinary_postmr_result(tmp_path/'run',attempt_number=1)
    assert result.model_path is None and not result.dictionary_paths and not result.restraint_paths
    assert result.selected is None and result.readyset_status=='NOT_RUN' and not result.refinement_ready
    assert result.status==status and 'not' in result.message.lower()


def test_reader_refusal_is_not_relabelled_as_usable_fallback(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as m
    def fail(*a):raise ValueError('changed exact evidence')
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',fail)
    with pytest.raises(ValueError,match='changed exact evidence'):m.read_ordinary_postmr_result(tmp_path,attempt_number=2)


def test_a_generic_request_cannot_claim_ordinary_construction(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as m
    exact=selected_result(tmp_path);del exact['construction_inputs']
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    with pytest.raises(ValueError,match='construction'):m.read_ordinary_postmr_result(tmp_path/'run',attempt_number=1)


@pytest.mark.parametrize('attempt',[None,True,0,-1,1.0])
def test_result_needs_an_exact_positive_attempt_before_any_read(tmp_path,monkeypatch,attempt):
    import nasolve.cif_ordinary_postmr as m
    with patch('nasolve.cif_complete_request.read_dictionary_request_result',side_effect=AssertionError('no read')):
        with pytest.raises(ValueError):m.read_ordinary_postmr_result(tmp_path,attempt_number=attempt)


def test_new_preparation_executes_once_without_reconfiguring_or_second_construction(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as m
    root=tmp_path/'run';sdk=object();generation={'PDU':{'live':'only'}};calls=[]
    prepared=m.PreparedPostMRRequest(root,root/'PostMR/DictionaryEngine/request',{},generation)
    def initialize(run,phenix,**kw):
        assert run==root and phenix is sdk and kw['continuation_options']['restore_serialization'] is True
        calls.append('construct');return prepared
    def execute(request,phenix,store,**kw):
        assert request==prepared.request_directory and kw['generation']==generation and kw['after_attempt']==0
        calls.append('execute');return {'attempt_number':1}
    monkeypatch.setattr(m,'initialize_ordinary_postmr_request',initialize)
    monkeypatch.setattr('nasolve.cif_complete_request.execute_dictionary_request_attempt',execute)
    monkeypatch.setattr(m,'read_ordinary_postmr_result',lambda run,**kw:(run,kw))
    assert m.prepare_checked_postmr(root,sdk,store_root=tmp_path/'store')==(root,{'attempt_number':1})
    assert calls==['construct','execute']


def test_resume_uses_frozen_recipe_and_limits_without_running_construction(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as m
    recipe=dict(expected_dialect='CHEMICAL_COMPONENTS_CIF',single_block_steps=71,policy_id='recorded')
    saved=dict(options=dict(recipe=recipe),binding=dict(timeout_seconds=83,max_attempts=1))
    request=dict(configuration=dict(construction_inputs={'bound':True},controls=dict(sites={'PDU':{'generation':saved},'5PC':{'generation':deepcopy(saved)}})))
    monkeypatch.setattr('nasolve.cif_complete_request._request',lambda p:request)
    settings=[]
    def configure(sdk,**kw):settings.append(kw);return SimpleNamespace(generation={'recorded':True})
    monkeypatch.setattr(m,'configure_dictionary_engine',configure)
    calls=[]
    def execute(root,sdk,store,**kw):calls.append(kw);return {'attempt_number':3}
    monkeypatch.setattr('nasolve.cif_complete_request.execute_dictionary_request_attempt',execute)
    monkeypatch.setattr(m,'read_ordinary_postmr_result',lambda run,**kw:kw)
    with patch.object(m,'initialize_ordinary_postmr_request',side_effect=AssertionError('No repeat Coot/NAR')):
        assert m.continue_checked_postmr(tmp_path,object(),after_attempt=2,store_root=tmp_path/'store')=={'attempt_number':3}
    assert settings==[dict(expected_dialect='CHEMICAL_COMPONENTS_CIF',single_block_steps=71,timeout_seconds=83,max_attempts=1,bond_representation_policy=None)]
    assert calls==[dict(generation={'PDU':{'recorded':True},'5PC':{'recorded':True}},after_attempt=2)]


@pytest.mark.parametrize('after',[None,True,-1,1.0])
def test_resume_refuses_missing_or_ambiguous_previous_attempt(tmp_path,after):
    import nasolve.cif_ordinary_postmr as m
    with patch('nasolve.cif_complete_request._request',side_effect=AssertionError('no request read')):
        with pytest.raises(ValueError):m.continue_checked_postmr(tmp_path,object(),after_attempt=after)


@pytest.mark.parametrize('choice',['readyset_checked_model','verified_parent_runtime',None])
def test_plane_generation_notes_never_claim_selected_plane_adoption(tmp_path,monkeypatch,choice):
    import nasolve.cif_ordinary_postmr as m
    exact=selected_result(tmp_path,selected=choice,status='NO_USABLE_BUNDLE' if choice is None else 'QUALIFIED_DIAGNOSTIC_RUNTIME')
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    old=m.read_ordinary_postmr_result(tmp_path/'run',attempt_number=1)
    exact['result']['plane_generation']=dict(policy_id='cif-complete-owned-plane-generation-v1',components={
        'PDU':dict(status='OWNED_SUPPORT_READY',missing_centres=['C5']),
        'AAA':dict(status='NO_GENERATION_NEEDED',missing_centres=[]),
        'YYY':dict(status='KNOWN_GENERATION_FAILURE',missing_centres=['N7'],proof=dict(failure_kind='TIMED_OUT')),
        'ZZZ':dict(status='KNOWN_GENERATION_FAILURE',missing_centres=['Q9'],proof=dict(failure_kind='REJECTED_CANDIDATE'))})
    before=deepcopy(exact)
    with patch('subprocess.Popen',side_effect=AssertionError('Read must not execute')):
        result=m.read_ordinary_postmr_result(tmp_path/'run',attempt_number=1)
    notes=' '.join(result.limitations)
    assert 'PDU: generated source-checked support' in notes and 'C5' in notes
    assert 'AAA: no missing planes' in notes and 'supported source-graph screen' in notes
    assert 'YYY: optional plane generation timed out' in notes and 'N7' in notes
    assert 'ZZZ: optional plane generation was chemically rejected' in notes
    assert 'does not establish final plane adoption' in notes
    assert 'still needs integration' not in notes
    assert result.message==old.message and result.model_path==old.model_path
    assert result.refinement_ready is False and exact==before


def test_resume_keeps_frozen_automatic_plane_choice(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as m
    request=dict(configuration=dict(plane_generation_policy='cif-complete-owned-plane-generation-v1',construction_inputs={},
        controls=dict(sites={'PDU':dict(generation=dict(options=dict(recipe=dict(expected_dialect='CHEMICAL_COMPONENTS_CIF',single_block_steps=180)),binding=dict(timeout_seconds=240,max_attempts=1)))})))
    monkeypatch.setattr('nasolve.cif_complete_request._request',lambda p:request)
    monkeypatch.setattr(m,'configure_dictionary_engine',lambda *a,**k:SimpleNamespace(generation={'original_recipe':True}))
    def execute(root,sdk,store,**kw):
        assert request['configuration']['plane_generation_policy']=='cif-complete-owned-plane-generation-v1'
        assert kw==dict(after_attempt=1,generation={'PDU':{'original_recipe':True}})
        return {'attempt_number':2}
    monkeypatch.setattr('nasolve.cif_complete_request.execute_dictionary_request_attempt',execute)
    monkeypatch.setattr(m,'read_ordinary_postmr_result',lambda run,**kw:kw)
    with patch.object(m,'initialize_ordinary_postmr_request',side_effect=AssertionError('No repeat construction')):
        assert m.continue_checked_postmr(tmp_path,object(),after_attempt=1,store_root=tmp_path/'store')=={'attempt_number':2}



@pytest.mark.parametrize('covered', [False, True])
def test_ordinary_notes_distinguish_generation_from_selected_dictionary_coverage(tmp_path, monkeypatch, covered):
    from copy import deepcopy
    from nasolve import cif_ordinary_postmr as m
    from tests.test_cif_plane_coverage import values, plane, write, bound
    exact = selected_result(tmp_path)
    source = values(); selected = deepcopy(source)
    if covered: plane(selected, ['C', 'O', 'N', 'R'])
    bundle = tmp_path/'bundle'; folder = bundle/'components/XYZ/snapshot/entry'; folder.mkdir(parents=True)
    source_path = write(folder, source, 'source.cif')
    dictionary = write(tmp_path, selected, 'selected.cif')
    exact['runtime']['dictionaries'] = [dictionary]
    exact['runtime']['manifest']['resources'] = {'dictionaries': [dict(sha256=bound(dictionary)['sha256'])]}
    exact['preparation'] = {'bundle_directory': bundle, 'report': {'selected_attempts': {'XYZ': 1}}}
    exact['result']['plane_generation'] = {'components': {'XYZ': dict(status='OWNED_SUPPORT_READY',
        missing_centres=['C'], source_sha256=bound(source_path)['sha256'])}}
    calls = []
    def read(*args): calls.append(args); return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result', read)
    result = m.read_ordinary_postmr_result(tmp_path/'run', attempt_number=1)
    notes = '\n'.join(result.limitations)
    assert 'generated source-checked support' in notes
    assert ('selected dictionary has explicit planes' if covered else 'selected dictionary lacks explicit planes') in notes
    assert 'XYZ' in notes and 'screened centres C' in notes
    assert 'alternative restraints' in notes and 'native' in notes
    assert len(calls) == 1 and result.refinement_ready is False
