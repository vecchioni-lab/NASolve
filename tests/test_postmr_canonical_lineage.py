"""Canonical construction proofs travel with the existing ordinary input closure."""
import shutil
from unittest.mock import patch

import pytest

from nasolve.campaign_records import read_record, write_record
from nasolve.postmr_lineage import begin_postmr_construction, finish_postmr_construction, read_postmr_construction, RECORD_PATH
from nasolve.postmr_canonical_input import canonical_input_plan, prepare_canonical_parent_input, REPORT
from tests.test_postmr_canonical_input import setup
from tests.test_cif_complete_request import case


def run_case(tmp_path, *, seal=True, free=False):
    originals=tmp_path/'originals';originals.mkdir()
    model,source,template,action,target=setup(originals)
    if free:
        model.write_text(''.join(line for line in model.read_text().splitlines(keepends=True)
            if not (line.startswith(('ATOM  ','HETATM')) and
                    (line[21]=='B' or line[12:16].strip() in {'P','OP1','OP2','OP3'}))))
    run=tmp_path/'run';models=run/'PostMR/Model';models.mkdir(parents=True)
    dictionaries=run/'PostMR/Coot/source_dictionaries';dictionaries.mkdir(parents=True)
    original=models/'mr_solution.pdb';original.write_bytes(model.read_bytes())
    chosen=dictionaries/'ZZZ.cif';chosen.write_bytes(target.read_bytes())
    started=begin_postmr_construction(run,original,original,{'ZZZ':chosen},(action,))
    saved=prepare_canonical_parent_input(original,canonical_input_plan((action,),{'A:1':(source,template)}),run/'PostMR/Coot/canonical_seeds')
    after=models/'after_coot.pdb';after.write_bytes(original.read_bytes().replace(b'PDU',b'ZZZ'))
    prepared=models/'prepared_model.pdb';prepared.write_bytes(after.read_bytes())
    construction=dict(model=after,raw_model=None,coot_log=None,canonical_parent_input=saved)
    if seal:finish_postmr_construction(run,started,prepared,construction)
    return run,started,prepared,construction


def test_seed_proofs_are_in_exact_relocatable_construction_closure(tmp_path):
    run,_,_,construction=run_case(tmp_path)
    (run/'PostMR/Coot/canonical_seeds/unrelated-note').write_text('not an input')
    original=read_postmr_construction(run)
    assert original['report']['policy_id']=='postmr-canonical-construction-lineage-v1'
    ref=original['report']['canonical_parent_input']
    assert ref['path']=='PostMR/Coot/canonical_seeds/canonical_input.json'
    seed_root=construction['canonical_parent_input']['directory']
    expected={str(p.relative_to(run)) for p in seed_root.iterdir() if p.name!='unrelated-note'}
    assert expected <= original['files'].keys()
    assert not any('unrelated' in n for n in original['files'])
    copy=tmp_path/'copy'
    for name,data in original['files'].items():
        path=copy/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    moved=tmp_path/'relocated';copy.rename(moved);shutil.rmtree(run);shutil.rmtree(tmp_path/'originals')
    before={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('Cold closure may not execute')):
        assert read_postmr_construction(moved)['files']==original['files']
    assert before=={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect',['input','action','passthrough','directory','model','receipt','dropped'])
def test_canonical_lineage_refuses_mismatched_producer_join_before_sealing(tmp_path,defect):
    run,started,prepared,c=run_case(tmp_path,seal=False)
    if defect=='input':
        original=run/started['inputs']['model']['path'];original.write_bytes(original.read_bytes()+b'REMARK changed\n')
        from nasolve.postmr_lineage import _reference
        started['inputs']['model']=_reference(original,run);started['inputs']['reference_model']=_reference(original,run)
    elif defect=='action':started['controls']['actions'][0]['parent_code']='DC'
    elif defect=='passthrough':started['controls']['passthrough_sites']=['A:1']
    elif defect=='directory':c['canonical_parent_input']['directory']=tmp_path
    elif defect=='model':c['canonical_parent_input']['model']=prepared
    elif defect=='receipt':c['canonical_parent_input']['receipt']['steps'][0]['proof']['chi_difference_degrees']=99
    else:c.pop('canonical_parent_input')
    with pytest.raises(ValueError):finish_postmr_construction(run,started,prepared,c)
    assert not (run/RECORD_PATH).exists()


@pytest.mark.parametrize('defect',['seed_bytes','seed_ref','action','passthrough','policy','drop_field','false_seed_proof'])
def test_cold_lineage_refuses_tampering_and_resigned_false_seed(tmp_path,defect):
    run,_,_,c=run_case(tmp_path)
    path=run/RECORD_PATH;r=read_record(path)
    if defect=='seed_bytes':c['canonical_parent_input']['model'].write_bytes(b'changed')
    elif defect=='seed_ref':r['canonical_parent_input']['path']='../elsewhere'
    elif defect=='action':r['controls']['actions'][0]['parent_code']='DC'
    elif defect=='passthrough':r['controls']['passthrough_sites']=['A:1']
    elif defect=='policy':r['policy_id']='postmr-construction-lineage-v1'
    elif defect=='drop_field':r.pop('canonical_parent_input')
    else:
        seed=c['canonical_parent_input']['directory']/REPORT
        s=read_record(seed);s['steps'][0]['proof']['chi_difference_degrees']=99;write_record(seed,s,replace=True)
        from nasolve.postmr_lineage import _reference
        r['canonical_parent_input']=_reference(seed,run)
    write_record(path,r,replace=True)
    with pytest.raises(ValueError):read_postmr_construction(run)


def test_existing_complete_input_join_retains_seed_closure_and_context(tmp_path):
    from nasolve.cif_complete_request import _construction_input
    run,started,prepared,_=run_case(tmp_path)
    sources={'ZZZ':{'source':run/started['inputs']['dictionaries']['ZZZ']['path']}}
    context={'intent':{'post_mr_plan':{'allow_op3_sites':[], 'backbone_policy':{'experimental_passthrough_sites':[]}}}}
    bound=_construction_input(run,prepared,sources,context)
    assert 'PostMR/Coot/canonical_seeds/canonical_input.json' in bound['files']
    context['intent']['post_mr_plan']['backbone_policy']['experimental_passthrough_sites']=['A:1']
    with pytest.raises(ValueError):_construction_input(run,prepared,sources,context)


def test_complete_request_freezes_new_lineage_policy_and_exact_seed_files(case, tmp_path):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_model_context import derive_prepared_model_context
    from tests.test_cif_model_context import report
    m,args,output,_,_,generations,calls=case
    parent=tmp_path/'canonical';parent.mkdir()
    run,started,prepared,_=run_case(parent,free=True)
    data=tmp_path/'canonical-data';(data/'ligands').mkdir(parents=True)
    source=run/started['inputs']['dictionaries']['ZZZ']['path']
    (data/'ligands/ZZZ.cif').write_bytes(source.read_bytes())
    sources=tmp_path/'canonical-sources';freeze_acquisition_sources(['ZZZ'],sources,data_root=data)
    context=derive_prepared_model_context(prepared,report(),['ZZZ'])
    args.update(source_selection=sources,model=prepared,model_context=context,
        components=[dict(code='ZZZ',generation=generations['ZZZ'],contexts=context['contexts']['ZZZ'])],
        expected_links=context['expected_links'],construction_inputs=run,
        native_context=dict(policy_id='cif-explicit-site-native-context-v2',monomer_inventory='full_model',custom_restraints='absent'))
    before=read_postmr_construction(run)['files']
    with patch('subprocess.Popen',side_effect=AssertionError('Initializer may not execute')):
        saved=m.initialize_dictionary_request(output=output,**args)
    assert saved['configuration']['construction_inputs']['policy_id']=='postmr-canonical-construction-lineage-v1'
    assert read_postmr_construction(output/'inputs/construction')['files']==before
    shutil.rmtree(parent);shutil.rmtree(data);shutil.rmtree(sources)
    moved=tmp_path/'relocated-complete';output.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold request may not execute')):
        state=m.inspect_dictionary_request(moved)
    assert state['availability']=='AVAILABLE' and not state['attempts'] and not calls
    assert read_postmr_construction(moved/'inputs/construction')['files']==before


def test_legacy_lineage_shape_and_unrelated_folder_semantics_stay_exact(tmp_path):
    run,started,prepared,construction=run_case(tmp_path,seal=False)
    shutil.rmtree(construction.pop('canonical_parent_input')['directory'])
    r=finish_postmr_construction(run,started,prepared,construction)
    assert r['policy_id']=='postmr-construction-lineage-v1'
    assert set(r)=={'schema_version','policy_id','status','scientific_qualification','native_interpretation',
        'automatic_adoption','inputs','controls','outputs','evidence','record_sha256'}
    before=read_postmr_construction(run)
    folder=run/'PostMR/Coot/canonical_seeds';folder.mkdir();(folder/'unrelated').write_text('not historical authority')
    assert read_postmr_construction(run)==before
