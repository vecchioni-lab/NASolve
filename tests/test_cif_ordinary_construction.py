"""Explicit construction choices reuse ordinary owners; toy Coot is not science."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,shutil

import pytest

from nasolve import cif_ordinary_postmr as entry
from nasolve.cif_acquisition_sources import freeze_acquisition_sources,read_acquisition_sources
from nasolve.cif_dictionary_sites import read_dictionary_sites
from nasolve.postmr_lineage import read_postmr_construction
from tests.test_postmr_projection_lineage import projection_case
from tests.test_cif_phenix_configuration import sdk_at
from tests.test_cif_complete_request import case
from tests.test_cif_model_context import report


@pytest.fixture
def chosen(case,tmp_path,monkeypatch):
    _,args,_,_,_,generations,calls=case
    parent=tmp_path/'original-choice';parent.mkdir()
    original,started,after,_=projection_case(parent)
    projection=original/'PostMR/Coot/construction_projections/ZZZ';saved=read_dictionary_sites(projection)
    frozen=parent/'sources';freeze_acquisition_sources(['ZZZ'],frozen,explicit_sources={'ZZZ':saved['snapshot']['source']})
    run=tmp_path/'ordinary-run';(run/'Phaser').mkdir(parents=True)
    (run/'Phaser/mr_solution.pdb').write_bytes(saved['canonical_model'].read_bytes())
    intent=report('A:1');intent.update(workflow='automr',stage='phaser',status='MR_SUCCESS')
    intent['post_mr_plan']['mutations']={s:{'ligand_code':'ZZZ'} for s in saved['projections']}
    (run/'report.json').write_text(json.dumps(intent))
    sdk,_=sdk_at(tmp_path/'sdk-real')
    config=SimpleNamespace(consumer=saved['report']['consumer'],generation=generations['ZZZ'],ready_set_executable=sdk.executables['phenix.ready_set'])
    monkeypatch.setattr(entry,'configure_dictionary_engine',lambda *a,**k:config)
    from nasolve import postmr
    # C358 separately tests source stereochemistry/planning. This fixture keeps
    # its synthetic qualification honest and checks only orchestration forwarding.
    source_bytes=saved['snapshot']['source'].read_bytes()
    def plan(intent,model,**kwargs):
        supplied=kwargs['construction_sources']
        assert supplied['ZZZ'][0].read_bytes()==source_bytes
        assert supplied['ZZZ'][1]=='DT'
        return tuple(postmr.MutationAction(site,postmr.residue_name(model,site),'ZZZ','coot-parent-overlap','DT')
            for site in intent['post_mr_plan']['mutations'])
    monkeypatch.setattr(postmr,'build_mutation_plan',plan)
    native_calls=[]
    def construct(model,actions,dictionaries,out,**kwargs):
        # Check all actual forwarding before returning a synthetic prepared model.
        assert read_acquisition_sources(run/'PostMR/DictionaryEngine/sources')['report']['components']==['ZZZ']
        assert set(kwargs['site_dictionary_paths'])==set(saved['projections'])
        for site,path in kwargs['site_dictionary_paths'].items():
            assert path.read_bytes()==saved['projections'][site][0].read_bytes()
        assert dictionaries['ZZZ'].read_bytes()==saved['snapshot']['dictionary'].read_bytes()
        assert all(a.parent_code=='DT' and a.after=='ZZZ' for a in actions)
        native_calls.append(out);out.write_bytes(after.read_bytes())
        return dict(model=out,raw_model=None,coot_log=None,coordinate_restoration={},site_dictionary_paths=kwargs['site_dictionary_paths'])
    monkeypatch.setattr(postmr,'construct_postmr_model',construct)
    def forbidden(*a,**k):raise AssertionError('Explicit input must not invent a catalogue entry or run legacy preparation')
    monkeypatch.setattr(postmr,'ligand_definition',forbidden);monkeypatch.setattr(postmr,'ligand_dictionary',forbidden)
    monkeypatch.setattr(postmr,'_run_readyset',forbidden)
    options=dict(expected_dialect='CHEMICAL_COMPONENTS_CIF',frozen_sources=frozen,construction_choices={'ZZZ':(projection,'DT')})
    return run,sdk,options,parent,native_calls,config


def test_ordinary_construction_uses_frozen_choices_and_complete_request(chosen,tmp_path):
    run,sdk,options,parent,calls,_=chosen
    with patch('subprocess.Popen',side_effect=AssertionError('No process in synthetic orchestration')):
        result=entry.initialize_ordinary_postmr_request(run,sdk,**options)
    assert len(calls)==1 and result.request_directory==run/'PostMR/DictionaryEngine/request'
    source=read_acquisition_sources(result.request_directory/'inputs/sources')
    assert source['report']['policy_id']=='cif-acquisition-explicit-sources-v1'
    lineage=read_postmr_construction(run)
    assert lineage['report']['policy_id']=='postmr-projected-dictionary-construction-lineage-v1'
    assert read_postmr_construction(result.request_directory/'inputs/construction')['files']==lineage['files']
    shutil.rmtree(parent);moved=tmp_path/'relocated';run.rename(moved)
    from nasolve.cif_complete_request import inspect_dictionary_request
    from nasolve.cif_postmr_publication import _check_new_mutation_intent
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read must not execute')):
        request = moved/'PostMR/DictionaryEngine/request'
        state = inspect_dictionary_request(request)
        live = json.loads((moved/'report.json').read_bytes())
        verified = {'construction_inputs':read_postmr_construction(request/'inputs/construction')}
        _check_new_mutation_intent(moved,live,request,verified)
        del live['post_mr_plan']['mutations']['B:1']
        with pytest.raises(ValueError,match='mutation intent'):
            _check_new_mutation_intent(moved,live,request,verified)
    assert state['availability']=='AVAILABLE' and not state['attempts']
    before={str(p.relative_to(moved)):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with pytest.raises(RuntimeError,match='already exists'):
        entry.initialize_ordinary_postmr_request(moved,sdk,**dict(options,frozen_sources=moved/'PostMR/DictionaryEngine/sources',construction_choices={'ZZZ':(moved/'PostMR/Coot/construction_projections/ZZZ','DT')}))
    assert before=={str(p.relative_to(moved)):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect',['no_sources','no_choices','empty','extra_code','model','source','consumer','phosphate','missing_site'])
def test_invalid_choices_refuse_before_coot(chosen,defect):
    run,sdk,options,parent,calls,config=chosen;options=deepcopy(options)
    if defect=='no_sources':options['frozen_sources']=None
    elif defect=='no_choices':options['construction_choices']=None
    elif defect=='empty':options['construction_choices']={}
    elif defect=='extra_code':options['construction_choices']['QQQ']=options['construction_choices']['ZZZ']
    elif defect=='model':
        p=run/'Phaser/mr_solution.pdb';p.write_bytes(p.read_bytes()+b'REMARK changed canonical input\n')
    elif defect=='source':
        p=parent/'other.cif';p.write_bytes(read_acquisition_sources(options['frozen_sources'])['sources']['ZZZ']['source'].read_bytes()+b'# changed\n')
        other=parent/'other-source';freeze_acquisition_sources(['ZZZ'],other,explicit_sources={'ZZZ':p});options['frozen_sources']=other
    elif defect=='consumer':config.consumer=deepcopy(config.consumer);config.consumer['version']='different'
    else:
        p=run/'report.json';r=json.loads(p.read_text())
        if defect=='phosphate':r['post_mr_plan']['allow_op3_sites']=[];r['post_mr_plan'].pop('phosphate_intent',None)
        else:r['post_mr_plan']['mutations'].pop('B:1')
        p.write_text(json.dumps(r))
    with pytest.raises((ValueError,RuntimeError)):
        entry.initialize_ordinary_postmr_request(run,sdk,**options)
    assert not calls and not (run/'PostMR/DictionaryEngine/request/request.json').exists()


def test_retained_recipe_multiple_planes_is_explicit_and_default_unchanged(tmp_path):
    from nasolve.cif_phenix_configuration import configure_dictionary_engine
    from nasolve.cif_generation_acquisition import generation_dictionary_options
    sdk,_=sdk_at(tmp_path/'sdk')
    default=configure_dictionary_engine(sdk,expected_dialect='CHEMICAL_COMPONENTS_CIF')
    chosen=configure_dictionary_engine(sdk,expected_dialect='CHEMICAL_COMPONENTS_CIF',multiple_planes=True)
    assert 'multiple_planes' not in default.generation
    assert generation_dictionary_options(chosen.generation)['recipe']['multiple_planes'] is True
    for value in (None,1,'true'):
        with pytest.raises(ValueError):configure_dictionary_engine(sdk,expected_dialect='CHEMICAL_COMPONENTS_CIF',multiple_planes=value)


def test_extra_frozen_component_refuses_before_coot(chosen):
    from tests.test_cif_acquisition_sources import dictionary
    run,sdk,options,parent,calls,_=chosen
    selected=read_acquisition_sources(options['frozen_sources'])['sources']['ZZZ']['source']
    extra=parent/'YYY.cif';extra.write_text(dictionary('YYY'))
    frozen=parent/'extra-selection';freeze_acquisition_sources(['ZZZ','YYY'],frozen,explicit_sources={'ZZZ':selected,'YYY':extra})
    with pytest.raises((ValueError,RuntimeError)):
        entry.initialize_ordinary_postmr_request(run,sdk,**dict(options,frozen_sources=frozen))
    assert not calls


def test_interrupted_construction_preserves_frozen_inputs_and_refuses_in_place(chosen,monkeypatch):
    from nasolve import postmr
    run,sdk,options,parent,calls,_=chosen
    def interrupted(*a,**k):
        (run/'PostMR/Coot/partial.log').write_text('Interrupted fixture; not native evidence')
        raise RuntimeError('construction interrupted')
    monkeypatch.setattr(postmr,'construct_postmr_model',interrupted)
    with pytest.raises(RuntimeError,match='construction interrupted'):
        entry.initialize_ordinary_postmr_request(run,sdk,**options)
    assert read_acquisition_sources(run/'PostMR/DictionaryEngine/sources')['report']['components']==['ZZZ']
    assert read_dictionary_sites(run/'PostMR/Coot/construction_projections/ZZZ')['report']['component']=='ZZZ'
    before={str(p.relative_to(run)):(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    with pytest.raises(RuntimeError,match='already exists'):
        entry.initialize_ordinary_postmr_request(run,sdk,**options)
    assert before=={str(p.relative_to(run)):(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    assert not (run/'PostMR/DictionaryEngine/request/request.json').exists()
