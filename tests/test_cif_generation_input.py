"""Original chemical authority survives native reader input preparation."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from tests.test_cif_generation_acquisition import case

POLICY='cif-source-reader-preparation-v1'


def test_acquisition_qualifies_original_and_cache_hit_needs_no_preparation(case, monkeypatch):
    module,args,kwargs,calls,c,q=case
    kwargs['generation']['source_input_policy']=POLICY
    result=module.resolve_generated_dictionary(*args,**kwargs)
    assert result['status']=='PREPARED_AND_FROZEN' and calls==['generate','qualify']
    from nasolve.cif_generation_attempt import inspect_source_generation_request
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    state=inspect_source_generation_request(args[4]);config=state['request']['configuration']
    assert config['source']['sha256']==sha256(args[0].read_bytes()).hexdigest()
    assert config['source_preparation']['consumer']['sha256']!=config['source']['sha256']
    saved=resolve_dictionary_snapshot(args[3])
    assert saved['source'].read_bytes()==args[0].read_bytes()
    assert saved['manifest']['request']['recipe']['source_input_policy']==POLICY
    assert saved['provenance']['generation_acquisition']['source_preparation']==config['source_preparation']
    shutil.rmtree(kwargs['generation']['installation_root'])
    import nasolve.cif_generation_input as prepared
    monkeypatch.setattr(prepared,'source_input_files',lambda *a,**k:pytest.fail('qualified cache hit must not prepare inputs'))
    second=module.resolve_generated_dictionary(*args[:3],args[3].with_name('second'),args[4],args[5].with_name('unused'),**kwargs)
    assert second['status']=='REUSED' and calls==['generate','qualify']



@pytest.mark.parametrize('value', ['', 'unknown', False, 1])
def test_unknown_input_policy_is_not_a_silent_legacy_fallback(case, value):
    module,args,kwargs,calls,*_=case
    kwargs['generation']['source_input_policy']=value
    with pytest.raises(ValueError,match='source input'):
        module.resolve_generated_dictionary(*args,**kwargs)
    assert not calls and not args[4].exists()


def test_projection_records_declared_coordinates_and_original_monomer_dialect():
    from nasolve.cif_generation_input import source_input_files
    original=(Path(__file__).resolve().parents[1]/'src/nasolve/data/ligands/1AP.cif').read_bytes()
    binding,files=source_input_files(original,'1AP')
    report=json.loads(files['prepared/preparation.json'])
    assert report['coordinate_origin']=='SOURCE_DECLARED_COORDINATES_NOT_INDEPENDENT_IDEAL'
    assert binding['reader_dialect']=='MONOMER_LIBRARY_CIF'
    assert report['source']['sha256']==sha256(original).hexdigest()
    assert report['phosphate_order']['changed'] is True
    assert binding['consumer']['sha256']==sha256(files['prepared/consumer.cif']).hexdigest()
    assert source_input_files(original,'1AP')==(binding,files)
    assert not any('/Users/' in json.dumps(value) for value in (binding,report))


def test_input_policy_changes_cache_recipe_but_not_source_authority(case):
    module,args,kwargs,*_=case
    old=module.generation_dictionary_options(kwargs['generation'])
    new=module.generation_dictionary_options(dict(kwargs['generation'],source_input_policy=POLICY))
    assert new['generator']==old['generator']
    assert new['recipe']==dict(old['recipe'],source_input_policy=POLICY)


@pytest.mark.parametrize('member', ['graph.cif','reader.cif','consumer.cif','preparation.json'])
def test_changed_prepared_inputs_refuse_even_with_rehashed_binding(case, member):
    module,args,kwargs,*_=case
    kwargs['generation']['source_input_policy']=POLICY
    module.resolve_generated_dictionary(*args,**kwargs)
    from nasolve.campaign_records import read_record,write_record
    from nasolve.cif_generation_attempt import inspect_source_generation_request
    root=args[4];path=root/'inputs/prepared'/member;path.write_bytes(path.read_bytes()+b'\n')
    request=read_record(root/'request.json')
    request['configuration']['source_preparation']['input_files']['prepared/'+member]={'sha256':sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}
    if member=='consumer.cif':
        request['configuration']['source_preparation']['consumer']=dict(request['configuration']['source_preparation']['input_files']['prepared/'+member])
    write_record(root/'request.json',request,replace=True)
    with pytest.raises(ValueError,match='projection differs'):
        inspect_source_generation_request(root)


def test_shared_generation_cannot_switch_input_policy_on_retry(case):
    module,args,kwargs,*_=case
    kwargs['generation']['source_input_policy']=POLICY
    module.resolve_generated_dictionary(*args,**kwargs)
    from nasolve.cif_generation_attempt import generate_source_candidate_attempt
    old=dict(kwargs['generation']);old.pop('source_input_policy')
    with pytest.raises(ValueError,match='identity differs'):
        generate_source_candidate_attempt(source=args[0],code=args[1],request_directory=args[4],**old)
    assert not (args[4]/'attempts/attempt-0002').exists()


@pytest.mark.parametrize('mode', ['success','rejected','failed'])
def test_owned_plane_support_keeps_original_source_with_prepared_native_input(tmp_path,monkeypatch,mode):
    import nasolve.cif_generation_attempt as owner
    generate=owner.generate_source_candidate_attempt
    def projected(*args,**kwargs):
        return generate(*args,**kwargs,source_input_policy=POLICY)
    monkeypatch.setattr(owner,'generate_source_candidate_attempt',projected)
    from tests.test_cif_plane_generation import plane_generation
    from nasolve.cif_plane_generation import read_owned_plane_support,inspect_owned_plane_generation_failure
    source,_,request,directory=plane_generation(tmp_path,
        mode='process_failure' if mode=='failed' else 'none',candidate_defect='charge' if mode=='rejected' else None)
    reader=read_owned_plane_support if mode=='success' else inspect_owned_plane_generation_failure
    report=reader(source,'Q17',request,1)
    assert report['source_sha256']==sha256(source.read_bytes()).hexdigest()
    assert report['recipe']['source_input_policy']==POLICY
    native=json.loads((directory/'source_candidate_receipt.json').read_text())
    assert native['source_sha256']!=report['source_sha256']
    original=source.read_bytes();moved=tmp_path/'relocated';request.rename(moved)
    source.unlink();shutil.rmtree(tmp_path/'phenix') if (tmp_path/'phenix').exists() else None
    import subprocess
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('cold plane read must not execute'))
    from tests.test_cif_repair_process import inventory
    before=inventory(moved)
    assert reader(moved/'inputs/source.cif','Q17',moved,1)==report
    assert inventory(moved)==before and (moved/'inputs/source.cif').read_bytes()==original
