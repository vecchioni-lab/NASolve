"""Charge-availability evidence is keyed by atoms; scientific values stay exact."""
from copy import deepcopy

import pytest


def evidence():
    return {'status':'REVIEW','checks':[{'check':'baseline:effective-site-formal-charges:A:6',
        'status':'UNSUPPORTED','unavailable':[{'atom_id':'P','expected':'0','observed':None},
            {'atom_id':"C1'",'expected':'0','observed':None}],
        'contradictions':[],'native_readback':{'status':'UNSUPPORTED'},'partial_charge_substituted':False},
        {'check':'active:effective-site-formal-charges:B:4','status':'REVIEW','unavailable':[],
        'contradictions':[{'atom_id':'N2','expected':'0','observed':'1'},
            {'atom_id':'C2','expected':'0','observed':'-1'}]},
        {'check':'ordered-native-proxy-evidence','status':'PASS','atoms':['P','OP1','OP2']}],
        'mechanics_checks_pass':False,'membership':{'checks':{'complete_heavy_sites':False,'dna_classification':False}}}


@pytest.mark.parametrize('site',['A:6','A:6B','_:1','A:-6','long:17'])
def test_atom_keyed_charge_evidence_replays_after_json_dictionary_sorting_without_mutation(site):
    from nasolve.cif_mixed_linked_recovery import qualification_replays
    old=evidence();old['checks'][0]['check']='baseline:effective-site-formal-charges:'+site
    fresh=deepcopy(old)
    fresh['checks'][0]['unavailable'].reverse();fresh['checks'][1]['contradictions'].reverse()
    before=deepcopy((old,fresh))
    assert qualification_replays(old,fresh)
    assert (old,fresh)==before
    assert old['status']=='REVIEW' and old['mechanics_checks_pass'] is False


@pytest.mark.parametrize('defect',['expected','observed','status','missing','extra','duplicate','row_field',
    'other_list','other_check','check_order','verdict','number_type','unrecognized_scope'])
def test_charge_replay_cannot_hide_changed_values_or_unrelated_order(defect):
    from nasolve.cif_mixed_linked_recovery import qualification_replays
    old=evidence();fresh=deepcopy(old);row=fresh['checks'][0]
    if defect=='expected':row['unavailable'][0]['expected']='-1'
    elif defect=='observed':row['unavailable'][0]['observed']='0'
    elif defect=='status':row['status']='PASS'
    elif defect=='missing':row['unavailable'].pop()
    elif defect=='extra':row['unavailable'].append({'atom_id':'OP3','expected':'0','observed':None})
    elif defect=='duplicate':row['unavailable'].append(deepcopy(row['unavailable'][0]))
    elif defect=='row_field':row['unavailable'][0]['ignored']=True
    elif defect=='other_list':fresh['checks'][2]['atoms'].reverse()
    elif defect=='other_check':
        old['checks'][0]['check']=row['check']='unrelated-charge-observation:A:6'
        row['unavailable'].reverse()
    elif defect=='check_order':fresh['checks'].reverse()
    elif defect=='verdict':fresh['mechanics_checks_pass']=True
    elif defect=='number_type':
        old['checks'][0]['unavailable'][0]['expected']=0
        row['unavailable'][0]['expected']=0.0
    else:
        old['checks'][0]['check']=row['check']='untrusted:effective-site-formal-charges:A:6'
        row['unavailable'].reverse()
    assert not qualification_replays(old,fresh)


def test_duplicate_atom_identity_is_invalid_even_when_both_reports_repeat_it():
    from nasolve.cif_mixed_linked_recovery import qualification_replays
    old=evidence();old['checks'][0]['unavailable'].append(deepcopy(old['checks'][0]['unavailable'][0]))
    assert not qualification_replays(old,deepcopy(old))


def test_only_new_linked_writer_sorts_charge_evidence_and_shared_legacy_order_stays_unchanged(tmp_path,monkeypatch):
    from nasolve.cif_linked_qualification import site_definition_checks
    from nasolve.cif_mixed_linked_recovery import _qualify,_ref
    expected={'site':'A:6','expected_atoms':['P','C1'],
        'expected_energy_types':{'P':'P','C1':'C'},'expected_formal_charges':{'P':'0','C1':'0'},
        'expected_hydrogen_attachments':{}}
    native={'monomer_mappings':{'rows':[{'site':'A:6','metadata':{'group':'DNA',
        'effective_definition':{'atoms':[{'atom_id':'P','type_energy':'P','type_symbol':'P','charge':None},
            {'atom_id':'C1','type_energy':'C','type_symbol':'C','charge':None}],'bonds':[]}}}]}}
    a=site_definition_checks(native,[{'sites':[expected]}])
    charge=lambda rows:next(v for v in rows if v['check']=='effective-site-formal-charges:A:6')
    assert [r['atom_id'] for r in charge(a)['unavailable']]==['P','C1']
    # Isolate the new writer's serialization contract; these artificial stubs
    # provide no native or chemical qualification.
    monkeypatch.setattr('nasolve.cif_mixed_native.qualify_mixed_native',lambda *a,**k:{'mechanics_checks_pass':False})
    monkeypatch.setattr('nasolve.cif_linked_control._heavy_proxy_checks',lambda *a,**k:{})
    native['atoms']=[];native['monomer_mappings']['rows'][0]['chem_mod_ids']={'status':'RECORDED','ids':[]}
    projected=tmp_path/'projected.cif';projected.write_text('ARTIFICIAL_PROJECTION_REFERENCE')
    expected.update(component='Q17',modification_id=None,incoming_site=None)
    bundle={'site_projections':{'A:6':{'component':'Q17','dictionary':_ref(projected,tmp_path)}},
        'preparations':{'Q17':{'receipt':{'sites':[expected]}}}}
    first=_qualify(native,native,tmp_path/'unused.pdb',tmp_path/'unused.phil',{}, {},[],bundle,tmp_path)
    expected['expected_formal_charges']={'C1':'0','P':'0'}
    second=_qualify(native,native,tmp_path/'unused.pdb',tmp_path/'unused.phil',{}, {},[],bundle,tmp_path)
    assert first==second
    for check in first['checks']:
        if ':effective-site-formal-charges:' in check['check']:
            assert [r['atom_id'] for r in check['unavailable']]==['C1','P']
