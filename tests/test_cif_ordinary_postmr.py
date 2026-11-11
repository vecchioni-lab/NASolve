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


@pytest.mark.parametrize('with_phil',[False,True])
def test_ordinary_input_preparation_stops_before_legacy_and_uses_existing_request(tmp_path,monkeypatch,with_phil):
    import nasolve.cif_ordinary_postmr as entry
    from nasolve.postmr_lineage import read_postmr_construction
    run,ready,_,data=setup(tmp_path);sdk,_=sdk_at(tmp_path/'sdk');sdk.executables['phenix.ready_set'].write_bytes(ready.read_bytes())
    calls=[]
    def initialize(model,report,components,source_output,output,**kwargs):
        bound=read_postmr_construction(run)
        assert bound['model']==model and source_output is None
        assert kwargs['construction_inputs']==run and kwargs['frozen_sources'].is_dir()
        assert kwargs['ready_set_executable'] is None and components[0]['code']=='DE'
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
        result=call(run,sdk,data,max_attempts=2,continuation_options={'readyset_timeout_seconds':120,'restore_serialization':True},
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
