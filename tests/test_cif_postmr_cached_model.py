"""Exact whole-model readback and multi-component ordinary ReadySet controls."""
from copy import deepcopy
from pathlib import Path
import json
import pytest

@pytest.mark.parametrize('defect',['none','coordinate','definition','proxy_target','lost_proxy','added_proxy','link','counts','ss','energy','missing'])
def test_roundtrip_requires_all_named_fixed_restraints(tmp_path,defect):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_postmr_cached_model import qualify_cached_model_roundtrip
    before,after,model,_,_=case(tmp_path)
    after['geometry']['custom_proxy_requests']=[];after['installed_api_sources']=[]
    before=deepcopy(after)
    if defect=='coordinate':after['atoms'][0]['xyz'][0]+=.1
    if defect=='definition':after['monomer_mappings']['rows'][1]['metadata']['group']='BROKEN'
    if defect=='proxy_target':after['geometry']['proxy_details']['angle'][0]['angle_ideal']+=1
    if defect=='lost_proxy':after['geometry']['proxy_details']['bond_simple'].pop()
    if defect=='added_proxy':after['geometry']['proxy_details']['angle'].append(deepcopy(after['geometry']['proxy_details']['angle'][0]))
    if defect=='link':after['geometry']['simple_bonds'].pop()
    if defect=='counts':after['geometry']['proxy_counts']['angle']+=1
    if defect=='ss':after['restraint_policy']['secondary_structure_enabled']=True
    if defect=='energy':after['energy_inventory']['snapshots'][1]['target']+=1
    if defect=='missing':after={}
    q=qualify_cached_model_roundtrip(before,after,model,model)
    assert q['mechanics_checks_pass'] is (defect=='none'),q
    assert not q['requires_cif_review'] and not q['automatic_adoption']
    assert q['scientific_qualification']=='NOT_ASSESSED'


def bundle(tmp_path,monkeypatch,behavior='noop'):
    from tests.test_cif_postmr_readyset import setup
    from nasolve.ligand_profiles import combine_dictionary_inputs
    s,c,m,p,consumer=setup(tmp_path,monkeypatch,behavior)
    s2=tmp_path/'source2.cif';s2.write_bytes(s.read_bytes().replace(b'Q17',b'Q18'))
    c2=tmp_path/'candidate2.cif';c2.write_bytes(c.read_bytes().replace(b'Q17',b'Q18'))
    sources=tmp_path/'sources.cif';dictionaries=tmp_path/'dictionaries.cif'
    combine_dictionary_inputs([s,s2],sources);combine_dictionary_inputs([c,c2],dictionaries)
    line=m.read_text().splitlines()[0];m.write_text(m.read_text().replace('END\n','')+line.replace('Q17 A   1','Q18 A   2')+'\nEND\n')
    return sources,dictionaries,m,p,consumer

@pytest.mark.parametrize('behavior',['noop','child','builder','fail'])
def test_multi_component_control_keeps_original_gates_and_portable_inputs(tmp_path,monkeypatch,behavior):
    from nasolve.cif_postmr_readyset import audit_readyset_bundle_consumption,read_readyset_consumption
    s,c,m,p,consumer=bundle(tmp_path,monkeypatch,behavior)
    q=audit_readyset_bundle_consumption(s,c,m,['Q17','Q18'],p,consumer,tmp_path/'bundle')
    assert q['status']==('READYSET_CACHED_INPUT_PASS' if behavior=='noop' else 'REVIEW')
    assert q['components']==['Q17','Q18'] and 'component' not in q
    assert q['scope']=='WHOLE_MODEL_ORDINARY_READYSET_CONSUMPTION; LINKED_NATIVE_QUALIFICATION_SEPARATE'
    assert read_readyset_consumption(tmp_path/'bundle')['dictionary'].read_bytes()==c.read_bytes()
    assert not q['requires_cif_review'] and not q['automatic_adoption']

@pytest.mark.parametrize('codes',[[],['Q17'],['Q17','Q17'],['Q17','Q19'],['Q17','BAD/CODE']])
def test_bundle_scope_must_match_explicit_dictionary_and_model(tmp_path,monkeypatch,codes):
    from nasolve.cif_postmr_readyset import audit_readyset_bundle_consumption
    s,c,m,p,consumer=bundle(tmp_path,monkeypatch)
    with pytest.raises(ValueError):audit_readyset_bundle_consumption(s,c,m,codes,p,consumer,tmp_path/'out')
    assert not (tmp_path/'out').exists()

@pytest.mark.parametrize('initial,ready,endpoint,expected',[(True,True,True,'readyset_checked_model'),
    (True,True,False,'verified_constructed_model'),(True,False,True,'verified_constructed_model'),
    (False,True,True,None),(None,True,True,None)])
def test_optional_roundtrip_cannot_discard_a_verified_start(initial,ready,endpoint,expected):
    from nasolve.cif_postmr_cached_model import coordinate_decision
    r=coordinate_decision(initial,ready,endpoint)
    assert r['selected']==expected
    assert not r['requires_cif_review'] and not r['automatic_adoption']
    assert r['status']==('CONTINUE_WITH_NOTES' if initial is True else 'NO_USABLE_MODEL')


def test_roundtrip_uses_structured_monomer_identity_when_display_padding_changes(tmp_path):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_postmr_cached_model import qualify_cached_model_roundtrip
    _,after,model,_,_=case(tmp_path)
    after['geometry']['custom_proxy_requests']=[];after['installed_api_sources']=[]
    before=deepcopy(after)
    for side,padding in [(before,' DG'),(after,'DG ')]:
        for row in side['monomer_mappings']['rows']:
            row['literal_identity']={'model_id':'','chain_id':'A','resseq':'  2','icode':' ','resname':padding,'altloc':''}
            row['interpreted_residue_name']=padding;row['residue_label']='display '+padding
    assert qualify_cached_model_roundtrip(before,after,model,model)['mechanics_checks_pass']
    after['monomer_mappings']['rows'][0]['literal_identity']['resname']='DT'
    assert not qualify_cached_model_roundtrip(before,after,model,model)['mechanics_checks_pass']

@pytest.mark.parametrize('defect',['none','changed','traversal','duplicate','symlink'])
def test_cached_model_reader_requires_hash_bound_relative_artifacts(tmp_path,defect):
    from hashlib import sha256
    from nasolve.cif_postmr_cached_model import read_cached_model,POLICY_ID
    folder=tmp_path/'portable';folder.mkdir();p=folder/'frozen.cif';p.write_bytes(b'FROZEN TEST INPUT')
    ref={'anchor':'cached_model_directory','path':p.name,'size':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()}
    r={'policy_id':POLICY_ID,'requires_cif_review':False,'outputs':[ref]}
    if defect=='changed':p.write_bytes(b'CHANGED')
    if defect=='traversal':ref['path']='../outside.cif'
    if defect=='duplicate':r['outputs'].append(dict(ref))
    if defect=='symlink':
        other=tmp_path/'original';other.write_bytes(p.read_bytes());p.unlink();p.symlink_to(other)
    (folder/'cached_model.json').write_text(json.dumps(r))
    if defect=='none':
        moved=folder.rename(tmp_path/'relocated');assert read_cached_model(moved)==r
    else:
        with pytest.raises((ValueError,OSError)):read_cached_model(folder)
