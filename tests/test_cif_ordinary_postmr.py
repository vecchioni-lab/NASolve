"""Ordinary preparation reaches one request boundary; synthetic intake is not science."""
from pathlib import Path
from unittest.mock import patch
import json
import pytest
from tests.test_postmr_runtime import setup
from tests.test_cif_phenix_configuration import sdk_at
from nasolve.postmr import PostMRPreparationError


def call(run,sdk,data,**kwargs):
    from nasolve.cif_ordinary_postmr import initialize_ordinary_postmr_request
    return initialize_ordinary_postmr_request(run,sdk,expected_dialect='CHEMICAL_COMPONENTS_CIF',data_root=data,**kwargs)


def test_checked_postmr_binds_the_whole_model_compiler_output_once(tmp_path, monkeypatch):
    import nasolve.cif_ordinary_postmr as entry

    run, ready, _, data = setup(tmp_path)
    sdk, _ = sdk_at(tmp_path / 'sdk')
    sdk.executables['phenix.ready_set'].write_bytes(ready.read_bytes())
    compiled = run / 'PostMR' / 'Restraints' / 'full_model' / 'compiled'
    phil = compiled / 'explicit_na_policy.phil'
    receipt = compiled / 'explicit_na_policy.json'

    def full_model(model, output, **kwargs):
        assert output == compiled.parent
        compiled.mkdir(parents=True)
        phil.write_text("refinement {\n pdb_interpretation {\n  secondary_structure {\n   enabled = False\n  }\n }\n}\n")
        receipt.write_text('{}')
        return {'restraint_file': 'compiled/' + phil.name, 'compiler_receipt': 'compiled/' + receipt.name}

    def receive(model, report, components, source_output, output, **kwargs):
        assert kwargs['explicit_na_policy'] == compiled
        assert list(kwargs['supplementary_phils']) == [phil]
        assert kwargs.get('literal_na_inputs') is None
        return {'test_intake': True}

    monkeypatch.setattr('nasolve.full_model_restraints.prepare_full_model_restraints', full_model)
    monkeypatch.setattr(entry, 'initialize_postmr_dictionary_request', receive)
    with patch.object(entry, 'prepare_postmr_literal_inputs', side_effect=AssertionError('Compiled restraints were reinterpreted')):
        result = call(run, sdk, data, restraint_scope='all')
    assert result.request == {'test_intake': True}


@pytest.mark.parametrize('targets',[False,True])
@pytest.mark.parametrize('automatic',[False,True])
@pytest.mark.parametrize('with_phil',[False,True])
def test_ordinary_input_preparation_stops_before_legacy_and_uses_existing_request(tmp_path,monkeypatch,with_phil,automatic,targets):
    import nasolve.cif_ordinary_postmr as entry
    from nasolve.postmr_lineage import read_postmr_construction
    run,ready,_,data=setup(tmp_path);sdk,_=sdk_at(tmp_path/'sdk');sdk.executables['phenix.ready_set'].write_bytes(ready.read_bytes())
    calls=[]
    def initialize(model,report,components,source_output,output,**kwargs):
        bound=read_postmr_construction(run)
        assert bound['model']==model and source_output is None
        assert kwargs.get('automatic_plane_support',False) is automatic
        assert kwargs.get('bond_targets') == ({'DE': [['R','Y']]} if targets else None)
        if not targets: assert 'bond_targets' not in kwargs
        assert kwargs['construction_inputs']==run and kwargs['frozen_sources'].is_dir()
        assert kwargs['ready_set_executable'] is None and components[0]['code']=='DE'
        assert components[0]['generation'].get('source_input_policy')==('cif-source-reader-preparation-v1' if automatic else None)
        assert bool(kwargs['supplementary_phils']) is with_phil
        assert (kwargs['literal_na_inputs'] is not None) is with_phil
        assert kwargs['max_attempts']==2 and kwargs['continuation_options']=={'readyset_timeout_seconds':120,'restore_serialization':True}
        calls.append(output);output.mkdir();(output/'request.json').write_text('{"synthetic":true}\n');return {'synthetic':True}
    monkeypatch.setattr(entry,'initialize_postmr_dictionary_request',initialize)
    compiled=[]
    def compile_literal(model,phils,sources,output,**kwargs):
        assert model.is_file() and all(p.is_file() for p in phils);compiled.append(list(phils));output.mkdir();return {}
    monkeypatch.setattr(entry,'prepare_postmr_literal_inputs',compile_literal)
    def builder(model,compatibility,pairs,output):
        pairs.write_text('A 12\nB 4\n');output.write_text('geometry_restraints.edits {}\n')
        return {'retained_pair_count':1,'retained_pairs':[{'first':'A:12','second':'B:4'}]}
    with patch('nasolve.cif_postmr_cache.prepare_postmr_dictionaries',side_effect=AssertionError('No legacy reuse')),patch('nasolve.postmr.write_linked_profile',side_effect=AssertionError('No legacy modifiers')),patch('nasolve.postmr._run_readyset',side_effect=AssertionError('No legacy ReadySet')):
        result=call(run,sdk,data,automatic_plane_support=automatic,
            bond_targets={'DE': [['Y','R']]} if targets else None,
            generation_options={'source_input_policy':'cif-source-reader-preparation-v1'} if automatic else None,max_attempts=2,continuation_options={'readyset_timeout_seconds':120,'restore_serialization':True},
            **({'modified_pairs_only':True,'modified_pair_builder':builder} if with_phil else {}))
    assert result.request_directory==calls[0] and result.request=={'synthetic':True}
    assert set(result.generation)=={'DE'} and result.generation['DE']['phenix_version']==sdk.version
    assert 'keep-this-live-only' not in repr(result)
    assert len(compiled)==int(with_phil) and not (run/'PostMR/report.json').exists()
    assert json.loads((run/'report.json').read_text())['status']=='MR_SUCCESS'
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    with pytest.raises(PostMRPreparationError,match='already exists'):call(run,sdk,data)
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items()) and len(calls)==1


def test_intake_failure_preserves_prepared_work_without_falling_through(tmp_path,monkeypatch):
    import nasolve.cif_ordinary_postmr as entry
    run,ready,_,data=setup(tmp_path);sdk,_=sdk_at(tmp_path/'sdk')
    def fail(*args,**kwargs):raise ValueError('unsupported chemistry remains visible')
    monkeypatch.setattr(entry,'initialize_postmr_dictionary_request',fail)
    with patch('nasolve.postmr._run_readyset',side_effect=AssertionError('No fallback to legacy')):
        with pytest.raises(ValueError,match='unsupported chemistry'):call(run,sdk,data)
    assert (run/'PostMR/Model/prepared_model.pdb').is_file()
    assert (run/'PostMR/DictionaryEngine/sources/source_selection.json').is_file()
    assert not (run/'PostMR/report.json').exists()


def test_invalid_generation_configuration_refuses_before_preparation(tmp_path):
    run,ready,_,data=setup(tmp_path);sdk,_=sdk_at(tmp_path/'sdk')
    with pytest.raises(ValueError,match='generation option'):call(run,sdk,data,generation_options={'invent_targets':True})
    assert not (run/'PostMR').exists()


@pytest.mark.parametrize('value',[None,1,'yes',{}])
def test_invalid_automatic_plane_choice_refuses_before_tool_configuration(tmp_path,value):
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',side_effect=AssertionError('No tool setup')):
        with pytest.raises(ValueError,match='boolean'):
            call(tmp_path/'run',object(),None,automatic_plane_support=value)
    assert not (tmp_path/'run').exists()


@pytest.mark.parametrize('table',[None,{'sha256':'a'*64}])
def test_source_selection_reads_frozen_component_before_binding_generation(tmp_path, monkeypatch,table):
    from nasolve import cif_ordinary_postmr as entry
    from nasolve.cif_acquisition_sources import read_acquisition_sources
    from nasolve.cif_generation_input import ordinary_generation_options

    run, ready, _, data = setup(tmp_path)
    sdk, _ = sdk_at(tmp_path / "sdk")
    sdk.executables["phenix.ready_set"].write_bytes(ready.read_bytes())
    selected = {}

    def select(source, code, settings):
        sources = run / "PostMR/DictionaryEngine/sources"
        assert source == read_acquisition_sources(sources)["sources"][code]["source"]
        assert "select_source_representation" not in settings
        selected[code] = dict(settings, bond_representation_policy="fixture")
        return selected[code]

    def freeze(model, report, components, source_output, output, **kwargs):
        assert kwargs["select_anionic_phosphate"] is True
        assert kwargs["saved_connected_order_store"] == tmp_path / "explicit-store"
        assert kwargs["automatic_connected_order"] is True
        assert kwargs["source_ribose_workbook"].is_file() and kwargs['select_native_rna_pucker'] is True
        assert components == [dict(code="DE", generation=selected["DE"])]
        frozen={} if table is None else {'rna_pucker_table':table}
        return {'configuration':{'components':{'DE':{'dictionary_request':{'recipe':frozen}}}}}

    monkeypatch.setattr("nasolve.cif_generation_input.source_selected_generation", select)
    monkeypatch.setattr(entry, "initialize_postmr_dictionary_request", freeze)
    result = call(run, sdk, data, store_root=tmp_path / "explicit-store",
                  generation_options=ordinary_generation_options("source-preserving-v2"))
    expected=selected['DE'] if table is None else dict(selected['DE'],rna_pucker_table=table)
    assert result.generation=={'DE':expected} and 'rna_pucker_table' not in selected['DE']


@pytest.mark.parametrize('declaration',[False,{}, {'report':{}}, {'registration_model':'missing'}])
def test_registered_source_shape_refuses_before_construction(tmp_path,declaration):
    from nasolve.cif_ordinary_postmr import initialize_ordinary_postmr_request
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',side_effect=AssertionError('No tool configuration')):
        with pytest.raises(ValueError,match='registered|Registered'):
            initialize_ordinary_postmr_request(tmp_path/'run',object(),expected_dialect='CHEMICAL_COMPONENTS_CIF',
                                               registered_preparation=declaration)


@pytest.mark.parametrize('mutation',[None,'construction','request'])
def test_registered_sources_survive_ordinary_construction_and_forward_explicitly(tmp_path,monkeypatch,mutation):
    pytest.importorskip('gemmi')
    from nasolve import cif_ordinary_postmr as entry, postmr
    from nasolve.cif_registered_preparation_input import FILES
    from tests.test_registered_preparation_context import case
    # This is a transport test; the final real context owner is tested separately.
    graph=case(tmp_path/'graph');declaration={key:graph[key] for key in FILES}
    (tmp_path/'ordinary').mkdir()
    run,ready,_,data=setup(tmp_path/'ordinary');sdk,_=sdk_at(tmp_path/'sdk')
    sdk.executables['phenix.ready_set'].write_bytes(ready.read_bytes())
    calls=[]
    def changed():
        path=declaration['continuations'];path.write_bytes(path.read_bytes()+b'\n')
    def initialize(*args,**kwargs):
        assert kwargs['registered_preparation']==declaration
        calls.append(kwargs)
        if mutation=='request':changed()
        return {'synthetic':True}
    monkeypatch.setattr(entry,'initialize_postmr_dictionary_request',initialize)
    original=postmr._prepare_postmr
    def construct(*args,**kwargs):
        handler=kwargs['_dictionary_handler']
        def wrapped(inputs):
            if mutation=='construction':changed()
            return handler(inputs)
        kwargs['_dictionary_handler']=wrapped
        return original(*args,**kwargs)
    monkeypatch.setattr(postmr,'_prepare_postmr',construct)
    if mutation:
        with pytest.raises(ValueError,match='Registered preparation source changed'):
            call(run,sdk,data,registered_preparation=declaration)
        assert len(calls)==int(mutation=='request')
    else:
        result=call(run,sdk,data,registered_preparation=declaration)
        assert result.request=={'synthetic':True} and len(calls)==1


def test_registered_bad_graph_refuses_before_tools(tmp_path):
    pytest.importorskip('gemmi')
    from nasolve.cif_registered_preparation_input import FILES
    from tests.test_registered_preparation_context import case
    graph=case(tmp_path/'graph');declaration={key:graph[key] for key in FILES}
    declaration['registration_model'].write_bytes(declaration['registration_model'].read_bytes()+b'\n')
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',side_effect=AssertionError('No tool configuration')):
        with pytest.raises(ValueError):call(tmp_path/'run',object(),None,registered_preparation=declaration)


def test_registered_source_symlink_cannot_hide_a_changed_input(tmp_path):
    pytest.importorskip('gemmi')
    from nasolve.cif_registered_preparation_input import FILES
    from tests.test_registered_preparation_context import case
    graph=case(tmp_path/'graph');declaration={key:graph[key] for key in FILES}
    link=tmp_path/'redirect.json';link.symlink_to(declaration['continuations'])
    declaration['continuations']=link
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',side_effect=AssertionError('No tool configuration')):
        with pytest.raises(ValueError,match='symlink'):
            call(tmp_path/'run',object(),None,registered_preparation=declaration)
