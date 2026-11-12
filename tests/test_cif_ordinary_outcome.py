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
