"""The existing construction owner retains the exact chemical derivation."""
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from nasolve.campaign_records import read_record,write_record
from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites
from nasolve.postmr import MutationAction
from nasolve.postmr_lineage import begin_postmr_construction,finish_postmr_construction,read_postmr_construction,RECORD_PATH,_reference
from tests.test_cif_construction_projection import construction_inputs
from tests.test_cif_complete_request import case


def projection_case(tmp_path, *, seal=True):
    originals=tmp_path/'originals';originals.mkdir();args,actual=construction_inputs(originals,chi_frame=True)
    from tests.test_cif_model_context import model as backbone_model
    reference=backbone_model(originals/'linked-reference.pdb',chains=(('A','ZZZ'),('B','ZZZ')),last=2)
    coordinates={(l[21],l[22:26].strip(),l[12:16].strip()):l[30:54]
        for l in reference.read_text().splitlines() if l.startswith(('ATOM  ','HETATM'))}
    for p in (args['model'],actual):
        p.write_text(''.join(l[:30]+coordinates.get((l[21],l[22:26].strip(),l[12:16].strip()),l[30:54])+l[54:]
            if l.startswith(('ATOM  ','HETATM')) else l for l in p.read_text().splitlines(keepends=True)))
    run=tmp_path/'run';models=run/'PostMR/Model';models.mkdir(parents=True)
    model=models/'mr_solution.pdb';model.write_bytes(args['model'].read_bytes());args['model']=model
    projected=run/'PostMR/Coot/construction_projections/ZZZ'
    prepare_dictionary_sites(output=projected,**args);saved=read_dictionary_sites(projected)
    base=run/'PostMR/Coot/source_dictionaries/ZZZ.cif';base.parent.mkdir();base.write_bytes((originals/'inputs/source.cif').read_bytes())
    choices={};actions=[]
    for i,(site,(p,code)) in enumerate(sorted(saved['projections'].items())):
        chosen=run/f'PostMR/Coot/site_dictionaries/{i:03d}.cif';chosen.parent.mkdir(exist_ok=True);chosen.write_bytes(p.read_bytes());choices[site]=chosen
        actions.append(MutationAction(site,'DT','ZZZ','coot-parent-overlap','DT'))
    started=begin_postmr_construction(run,model,model,{'ZZZ':base},tuple(actions),
        allow_op3_sites=('A:1',),site_dictionary_paths=choices,construction_projections={'ZZZ':projected})
    after=models/'after_coot.pdb';after.write_bytes(actual.read_bytes());prepared=models/'prepared_model.pdb';prepared.write_bytes(after.read_bytes())
    result=dict(model=after,raw_model=None,coot_log=None,site_dictionary_paths=choices)
    if seal:finish_postmr_construction(run,started,prepared,result)
    return run,started,prepared,result


def test_projection_is_part_of_exact_existing_closure_and_replays_cold(tmp_path):
    run,_,_,_=projection_case(tmp_path);before=read_postmr_construction(run)
    assert before['report']['policy_id']=='postmr-projected-dictionary-construction-lineage-v1'
    prefix='PostMR/Coot/construction_projections/ZZZ/'
    assert prefix+'site_receipt.json' in before['files']
    assert prefix+'snapshot/entry/source.cif' in before['files']
    assert prefix+'inputs/model.pdb' in before['files']
    assert prefix+'prepared/projected_A_2.cif' in before['files']
    (run/'unrelated.txt').write_text('Do not collect')
    assert read_postmr_construction(run)['files']==before['files']
    moved=tmp_path/'relocated'
    for n,data in before['files'].items():
        p=moved/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    shutil.rmtree(run);shutil.rmtree(tmp_path/'originals')
    stamps={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native replay')):
        assert read_postmr_construction(moved)['files']==before['files']
    assert stamps=={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect',['dropped','no_choices','input','action','phosphate','choice','passthrough','role','component','partial_choices'])
def test_invalid_join_refuses_before_sealing(tmp_path,defect):
    run,start,prepared,result=projection_case(tmp_path,seal=False)
    if defect=='dropped':start.pop('construction_projections')
    elif defect=='no_choices':start.pop('site_dictionaries');result.pop('site_dictionary_paths');shutil.rmtree(run/'PostMR/Coot/site_dictionaries')
    elif defect=='input':
        p=run/start['inputs']['model']['path'];p.write_bytes(p.read_bytes()+b'REMARK changed\n');start['inputs']['model']=_reference(p,run);start['inputs']['reference_model']=_reference(p,run)
    elif defect=='action':start['controls']['actions'][0]['before']='DA'
    elif defect=='phosphate':start['controls']['allow_op3_sites']=[]
    elif defect=='choice':
        p=result['site_dictionary_paths']['A:2'];p.write_bytes(p.read_bytes()+b'# changed\n');start['site_dictionaries']['A:2']=_reference(p,run)
    elif defect=='passthrough':start['controls']['passthrough_sites']=['A:2']
    elif defect=='role':start['construction_projections']['ZZZ']['path']=start['site_dictionaries']['A:2']['path']
    elif defect=='component':start['construction_projections']={'QQQ':start['construction_projections']['ZZZ']}
    else:start['site_dictionaries'].pop('B:1');result['site_dictionary_paths'].pop('B:1')
    with pytest.raises(ValueError):finish_postmr_construction(run,start,prepared,result)
    assert not (run/RECORD_PATH).exists()


@pytest.mark.parametrize('defect',['old_policy','drop_field','drop_choices','tampered_projection','wrong_before','wrong_phosphate'])
def test_reader_rechecks_resigned_false_derivation(tmp_path,defect):
    run,_,_,_=projection_case(tmp_path);path=run/RECORD_PATH;r=read_record(path)
    if defect=='old_policy':r['policy_id']='postmr-site-dictionary-construction-lineage-v1'
    elif defect=='drop_field':r.pop('construction_projections')
    elif defect=='drop_choices':r.pop('site_dictionaries')
    elif defect=='tampered_projection':
        p=run/'PostMR/Coot/construction_projections/ZZZ/prepared/projected_A_2.cif';p.write_bytes(p.read_bytes()+b'# changed\n')
    elif defect=='wrong_before':r['controls']['actions'][0]['before']='DA'
    else:r['controls']['allow_op3_sites']=[]
    write_record(path,r,replace=True)
    with pytest.raises(ValueError):read_postmr_construction(run)


def test_complete_input_owner_collects_projection_without_another_tree(tmp_path):
    from nasolve.cif_complete_request import _construction_input
    run,start,prepared,_=projection_case(tmp_path)
    source=run/start['inputs']['dictionaries']['ZZZ']['path']
    from nasolve.cif_model_context import derive_prepared_model_context
    from tests.test_cif_model_context import report
    context=derive_prepared_model_context(prepared,report('A:1'),['ZZZ'])
    original=read_postmr_construction(run)
    bound=_construction_input(run,prepared,{'ZZZ':{'source':source}},context)
    assert bound['files']==original['files']
    assert bound['report']['policy_id']=='postmr-projected-dictionary-construction-lineage-v1'
    assert sum(n.endswith('site_receipt.json') for n in bound['files'])==1


def test_complete_request_freezes_derivation_after_original_run_is_gone(case,tmp_path):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_model_context import derive_prepared_model_context
    from tests.test_cif_model_context import report
    m,args,output,_,_,generations,calls=case
    parent=tmp_path/'projection-source';parent.mkdir();run,start,prepared,_=projection_case(parent)
    source=run/start['inputs']['dictionaries']['ZZZ']['path']
    frozen=tmp_path/'frozen-projection';freeze_acquisition_sources(['ZZZ'],frozen,explicit_sources={'ZZZ':source})
    context=derive_prepared_model_context(prepared,report('A:1'),['ZZZ'])
    args.update(source_selection=frozen,model=prepared,model_context=context,
        components=[dict(code='ZZZ',generation=generations['ZZZ'],contexts=context['contexts']['ZZZ'])],
        expected_links=context['expected_links'],construction_inputs=run,
        native_context=dict(policy_id='cif-explicit-site-native-context-v2',monomer_inventory='full_model',custom_restraints='absent'))
    before=read_postmr_construction(run)['files']
    with patch('subprocess.Popen',side_effect=AssertionError('Initialization must not execute')):
        saved=m.initialize_dictionary_request(output=output,**args)
    assert saved['configuration']['construction_inputs']['policy_id']=='postmr-projected-dictionary-construction-lineage-v1'
    assert read_postmr_construction(output/'inputs/construction')['files']==before
    shutil.rmtree(parent);shutil.rmtree(frozen)
    moved=tmp_path/'relocated-complete-projection';output.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold request must not execute')):
        state=m.inspect_dictionary_request(moved)
    assert state['availability']=='AVAILABLE' and not state['attempts'] and not calls
    assert read_postmr_construction(moved/'inputs/construction')['files']==before


@pytest.mark.parametrize('defect',['links','end_state','missing_component'])
def test_complete_owner_checks_projection_against_actual_model_context(tmp_path,defect):
    from nasolve.cif_complete_request import _construction_input
    from nasolve.cif_model_context import derive_prepared_model_context
    from tests.test_cif_model_context import report
    run,start,prepared,_=projection_case(tmp_path)
    context=derive_prepared_model_context(prepared,report('A:1'),['ZZZ'])
    if defect=='links':context['expected_links']=[]
    elif defect=='end_state':context['contexts']['ZZZ'][0]['three_prime_state']='free_OH'
    else:context['contexts']={}
    source=run/start['inputs']['dictionaries']['ZZZ']['path']
    with pytest.raises(ValueError,match='actual prepared-model context'):
        _construction_input(run,prepared,{'ZZZ':{'source':source}},context)
