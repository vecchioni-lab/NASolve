"""Site dictionaries travel with the ordinary construction owner, without extra trees."""
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest
from nasolve.campaign_records import read_record, write_record
from nasolve.postmr_lineage import begin_postmr_construction, finish_postmr_construction, read_postmr_construction, RECORD_PATH
from nasolve.postmr import MutationAction
from tests.test_postmr_canonical_lineage import run_case
from tests.test_cif_complete_request import case


def site_case(tmp_path, *, seal=True, free=False):
    run, old, prepared, construction=run_case(tmp_path,seal=False,free=free)
    folder=run/'PostMR/Coot/site_dictionaries';folder.mkdir()
    source=run/old['inputs']['dictionaries']['ZZZ']['path'];chosen=folder/'000.cif'
    chosen.write_bytes(source.read_bytes()+b'\n# Explicit site choice\n')
    model=run/old['inputs']['model']['path'];actions=tuple(MutationAction(**a) for a in old['controls']['actions'])
    started=begin_postmr_construction(run,model,model,{'ZZZ':source},actions,site_dictionary_paths={'A:1':chosen})
    construction['site_dictionary_paths']={'A:1':chosen}
    if seal:finish_postmr_construction(run,started,prepared,construction)
    return run,started,prepared,construction


def test_site_and_canonical_choices_share_exact_relocatable_closure(tmp_path):
    run,_,_,_=site_case(tmp_path);before=read_postmr_construction(run)
    assert before['report']['policy_id']=='postmr-site-dictionary-construction-lineage-v1'
    assert 'canonical_parent_input' in before['report']
    assert before['site_dictionary_paths']=={'A:1':run/'PostMR/Coot/site_dictionaries/000.cif'}
    (run/'PostMR/Coot/site_dictionaries/unrelated').write_text('ignore')
    assert read_postmr_construction(run)['files']==before['files']
    moved=tmp_path/'moved'
    for name,data in before['files'].items():
        p=moved/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    shutil.rmtree(run);shutil.rmtree(tmp_path/'originals')
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read must not execute')):
        assert read_postmr_construction(moved)['files']==before['files']


@pytest.mark.parametrize('defect',['dropped_choice','added_choice','changed_file','wrong_site','wrong_role','passthrough'])
def test_site_choice_mismatch_refuses_before_sealing(tmp_path,defect):
    run,started,prepared,c=site_case(tmp_path,seal=False)
    if defect=='dropped_choice':c.pop('site_dictionary_paths')
    elif defect=='added_choice':started.pop('site_dictionaries')
    elif defect=='changed_file':c['site_dictionary_paths']['A:1'].write_text('changed')
    elif defect=='wrong_site':c['site_dictionary_paths']={'B:9':c['site_dictionary_paths']['A:1']}
    elif defect=='wrong_role':started['site_dictionaries']['A:1']['path']='PostMR/Coot/source_dictionaries/ZZZ.cif'
    else:started['controls']['passthrough_sites']=['A:1']
    with pytest.raises(ValueError):finish_postmr_construction(run,started,prepared,c)
    assert not (run/RECORD_PATH).exists()


@pytest.mark.parametrize('defect',['old_policy','drop','wrong_component','wrong_parent','wrong_role'])
def test_cold_site_lineage_rechecks_resigned_claims(tmp_path,defect):
    from nasolve.postmr_lineage import _reference
    run,_,_,c=site_case(tmp_path);path=run/RECORD_PATH;r=read_record(path)
    if defect=='old_policy':r['policy_id']='postmr-canonical-construction-lineage-v1'
    elif defect=='drop':r.pop('site_dictionaries')
    elif defect=='wrong_parent':r['controls']['actions'][0]['parent_code']='DA'
    elif defect=='wrong_role':r['site_dictionaries']['A:1']=r['inputs']['dictionaries']['ZZZ']
    else:
        selected=c['site_dictionary_paths']['A:1'];selected.write_bytes(selected.read_bytes().replace(b'ZZZ',b'QQQ'))
        r['site_dictionaries']['A:1']=_reference(selected,run)
    write_record(path,r,replace=True)
    with pytest.raises(ValueError):read_postmr_construction(run)


def test_site_choice_without_canonical_seed_uses_same_owner(tmp_path):
    run,started,prepared,c=site_case(tmp_path,seal=False)
    shutil.rmtree(c.pop('canonical_parent_input')['directory'])
    r=finish_postmr_construction(run,started,prepared,c)
    assert r['policy_id']=='postmr-site-dictionary-construction-lineage-v1'
    assert 'canonical_parent_input' not in r
    assert read_postmr_construction(run)['site_dictionary_paths']==c['site_dictionary_paths']


def test_complete_request_keeps_site_choices_after_all_originals_disappear(case, tmp_path):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_model_context import derive_prepared_model_context
    from tests.test_cif_model_context import report
    m,args,output,_,_,generations,calls=case
    parent=tmp_path/'site-source';parent.mkdir()
    run,started,prepared,_=site_case(parent,free=True)
    source=run/started['inputs']['dictionaries']['ZZZ']['path']
    frozen=tmp_path/'frozen';freeze_acquisition_sources(['ZZZ'],frozen,explicit_sources={'ZZZ':source})
    context=derive_prepared_model_context(prepared,report(),['ZZZ'])
    args.update(source_selection=frozen,model=prepared,model_context=context,
        components=[dict(code='ZZZ',generation=generations['ZZZ'],contexts=context['contexts']['ZZZ'])],
        expected_links=context['expected_links'],construction_inputs=run,
        native_context=dict(policy_id='cif-explicit-site-native-context-v2',monomer_inventory='full_model',custom_restraints='absent'))
    before=read_postmr_construction(run)['files']
    with patch('subprocess.Popen',side_effect=AssertionError('Initialize must not execute')):
        saved=m.initialize_dictionary_request(output=output,**args)
    assert saved['configuration']['construction_inputs']['policy_id']=='postmr-site-dictionary-construction-lineage-v1'
    assert read_postmr_construction(output/'inputs/construction')['files']==before
    shutil.rmtree(parent);shutil.rmtree(frozen)
    moved=tmp_path/'relocated-complete';output.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold request must not execute')):
        state=m.inspect_dictionary_request(moved)
    assert state['availability']=='AVAILABLE' and not state['attempts'] and not calls
    assert read_postmr_construction(moved/'inputs/construction')['files']==before
