"""Fixed coordinates and explicit chemistry changes are not an optimization result."""
from copy import deepcopy
from unittest.mock import patch
import pytest
from .test_cif_topology_gate import base, sync


def case(tmp_path):
    n,p,e=base(tmp_path)
    n.update(installed_api_sources=[],restraint_policy={},parameter_consumers={},phil_adaptations=[])
    g=n['geometry'];g['custom_proxy_requests']=[]
    for kind in ('angle','chirality','dihedral','const_dihedral','planarity','parallelity'):
        g['proxy_details'][kind]=[]
    # One within-site scalar proxy, separate from the declared intersite link.
    ids=[a['i_seq'] for a in n['atoms'] if a['identity']['resseq'].strip()=='1'][:2]
    g['proxy_details']['bond_simple'].append({'i_seqs':ids,'atoms':[n['atoms'][i]['label'] for i in ids],
        'distance_ideal':1.22,'weight':2500.,'origin_id':0,'symmetry_operation':None})
    sync(n)
    return n,p,e


def compare(a,b,p,e,sites=None):
    from nasolve.cif_native_target_comparison import review_native_target_comparison
    return review_native_target_comparison(a,b,p,['A:1'] if sites is None else sites,e)


def test_target_and_weight_changes_do_not_become_geometry_improvement(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a);old=deepcopy(a)
    b['geometry']['proxy_details']['bond_simple'][1].update(distance_ideal=1.534,weight=1/.036**2)
    sync(b)
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):r=compare(a,b,p,e)
    row=next(x for x in r['scalar_comparisons']['bond_simple']['matched'] if x['target_changed'])
    assert row['before']['observed']==row['after']['observed']
    assert row['before']['target']==1.22 and row['after']['target']==1.534
    assert row['weight_changed'] and r['coordinates_unchanged']
    assert r['optimization']=='NOT_RUN' and r['chemical_qualification']=='NOT_ESTABLISHED'
    assert not r['automatic_adoption'] and not r['geometry_accepted'] and a==old


@pytest.mark.parametrize('defect',['coordinates','identity','topology','policy','api','request','outside_definition',
    'missing_mapping','duplicate_mapping','literal_identity','proxy_count','proxy_label','duplicate_proxy','empty_sites','unknown_site','duplicate_site'])
def test_non_dictionary_changes_or_ambiguous_evidence_refuse(tmp_path,defect):
    a,p,e=case(tmp_path);b=deepcopy(a);sites=['A:1']
    if defect=='coordinates':b['atoms'][0]['xyz'][0]+=.1
    if defect=='identity':b['atoms'][0]['identity']['resname']='BAD'
    if defect=='topology':b['geometry']['proxy_details']['bond_simple'].pop(0);sync(b)
    if defect=='policy':b['restraint_policy']['enabled']=True
    if defect=='api':b['installed_api_sources']=['changed']
    if defect=='request':b['geometry']['custom_proxy_requests']=[{'changed':True}]
    if defect=='outside_definition':b['monomer_mappings']['rows'][1]['metadata']['group']='changed'
    if defect=='missing_mapping':b['monomer_mappings']['rows'].pop()
    if defect=='duplicate_mapping':b['monomer_mappings']['rows'].append(deepcopy(b['monomer_mappings']['rows'][0]))
    if defect=='literal_identity':b['monomer_mappings']['rows'][0]['literal_identity']['resname']='BAD'
    if defect=='proxy_count':b['geometry']['proxy_counts']['bond_simple']+=1
    if defect=='proxy_label':b['geometry']['proxy_details']['bond_simple'][1]['atoms'][0]='bad'
    if defect=='duplicate_proxy':b['geometry']['proxy_details']['bond_simple'].append(deepcopy(b['geometry']['proxy_details']['bond_simple'][1]));sync(b)
    if defect=='empty_sites':sites=[]
    if defect=='unknown_site':sites=['A:99']
    if defect=='duplicate_site':sites=['A:1','A:1']
    with pytest.raises(ValueError):compare(a,b,p,e,sites)


def test_missing_phosphate_and_formal_charge_remain_visible(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a)
    m=b['monomer_mappings']['rows'][0]
    m['missing_non_hydrogen_atoms']['atom_ids']=['OP3']
    m['missing_hydrogen_atoms']={'status':'RECORDED','atom_ids':['HOP2','HOP3']}
    m['metadata']['effective_definition']['atoms'][0].update(charge=None,partial_charge=-.3)
    r=compare(a,b,p,e);row=r['site_definitions']['A:1']['after']
    assert row==m and row['metadata']['effective_definition']['atoms'][0]['charge'] is None
    assert not r['automatic_adoption']


def test_ordered_endpoints_are_not_silently_normalized(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a);proxy=b['geometry']['proxy_details']['bond_simple'][1]
    proxy['i_seqs'].reverse();proxy['atoms'].reverse();sync(b)
    rows=compare(a,b,p,e)['scalar_comparisons']['bond_simple']
    assert len(rows['removed'])==len(rows['added'])==1 and len(rows['matched'])==1


def test_deferred_mechanics_and_outside_site_proxies_are_preserved(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a)
    ids=[x['i_seq'] for x in b['atoms'] if x['identity']['resseq'].strip()=='2'][:2]
    proxy={'i_seqs':ids,'atoms':[b['atoms'][i]['label'] for i in ids],'unknown_convention':1}
    for n in (a,b):n['geometry']['proxy_details']['planarity']=[deepcopy(proxy)];sync(n)
    r=compare(a,b,p,e)
    assert r['deferred_proxy_kinds']['planarity']['before']['count']==1
    b['geometry']['proxy_details']['planarity'][0]['unknown_convention']=2
    with pytest.raises(ValueError,match='Outside-site proxies'):compare(a,b,p,e)


def receipt_pair(tmp_path):
    import json
    import shutil
    from .test_cif_attachment_native import artifact, rebind, save
    folder=tmp_path/'before';folder.mkdir();n,p,e=case(folder)
    receipt=folder/'native/native_receipt.json';r=json.loads(receipt.read_text())
    dictionary=receipt.parent/'inputs/control.cif';dictionary.write_text('data_test\n# first definition\n')
    phil=receipt.parent/'inputs/fixed.phil';phil.write_text('# fixed control\n')
    n['dictionary_loading']=[{'input':'inputs/control.cif','status':'RECORDED'}]
    n['phil_adaptations']=[{'input':'inputs/fixed.phil','status':'UNCHANGED'}]
    r['native_validation']=n;r['dictionary_source_policy']='EXPLICIT_DICTIONARIES'
    r['inputs'] += [dict(artifact(dictionary,receipt.parent),role='dictionary',input_index=1),
                    dict(artifact(phil,receipt.parent),role='phil',input_index=2)]
    save(receipt,r)
    spec=receipt.parent/'native_spec.json';v=json.loads(spec.read_text());v.update(dictionaries=['inputs/control.cif'],phil_files=['inputs/fixed.phil'],installed_library_only=False);save(spec,v)
    rebind(receipt)
    shutil.copytree(folder,tmp_path/'after');after=tmp_path/'after/native/native_receipt.json'
    dictionary=after.parent/'inputs/control.cif';dictionary.write_text('data_test\n# second definition\n')
    r=json.loads(after.read_text());r['inputs'][1].update(artifact(dictionary,after.parent));save(after,r);rebind(after)
    return receipt,after,folder/'source/model.pdb',e


def test_bound_comparison_relocates_without_writing_or_executing(tmp_path):
    from .test_cif_catalogue import snapshot
    from nasolve.cif_native_target_comparison import inspect_native_target_comparison
    old=tmp_path/'original';old.mkdir();a,b,m,e=receipt_pair(old)
    before=snapshot(old)
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):
        result=inspect_native_target_comparison(a,b,m,['A:1'],e)
    assert snapshot(old)==before and len(result['dictionary_changes'])==1
    moved=old.rename(tmp_path/'relocated');assert not old.exists()
    paths=[moved/p.relative_to(old) for p in (a,b,m)]
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):
        assert inspect_native_target_comparison(*paths,['A:1'],e)==result
    assert snapshot(moved)==before


@pytest.mark.parametrize('defect',['hash','worker','model','phil','version','no_change','mid_read_mutation'])
def test_binding_rejects_tampering_and_non_dictionary_controls(tmp_path,defect,monkeypatch):
    import json
    from .test_cif_attachment_native import artifact,rebind,save
    import nasolve.cif_native_target_comparison as module
    a,b,m,e=receipt_pair(tmp_path)
    if defect=='hash':(b.parent/'native.log').write_text('tampered')
    if defect=='worker':(b.parent/'native_worker.py').write_text('tampered');rebind(b)
    if defect=='model':m.write_bytes(m.read_bytes()+b'REMARK changed\n')
    if defect=='phil':
        p=b.parent/'inputs/fixed.phil';p.write_text('# changed\n');r=json.loads(b.read_text());r['inputs'][2].update(artifact(p,b.parent));save(b,r);rebind(b)
    if defect=='version':r=json.loads(b.read_text());r['phenix_version']='other';save(b,r)
    if defect=='no_change':
        p=b.parent/'inputs/control.cif';p.write_bytes((a.parent/'inputs/control.cif').read_bytes());r=json.loads(b.read_text());r['inputs'][1].update(artifact(p,b.parent));save(b,r);rebind(b)
    if defect=='mid_read_mutation':
        original=module.review_native_target_comparison
        def mutate(*args,**kwargs):
            result=original(*args,**kwargs);(b.parent/'native.log').write_text('changed during read');return result
        monkeypatch.setattr(module,'review_native_target_comparison',mutate)
    with pytest.raises(ValueError):module.inspect_native_target_comparison(a,b,m,['A:1'],e)


def test_target_only_and_weight_only_controls_keep_distinct_meanings(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a)
    b['geometry']['proxy_details']['bond_simple'][1].update(distance_ideal=1.534,weight=1/.036**2)
    sync(b);r=compare(a,b,p,e)
    row=next(x for x in r['scalar_comparisons']['bond_simple']['matched'] if x['target_changed'])
    controls=row['target_weight_controls'];observed=row['before']['observed']
    assert controls['target_only_nominal_at_before_weight']==pytest.approx((observed-1.534)/.02)
    assert controls['weight_only_nominal_at_before_target']==pytest.approx((observed-1.22)/.036)
    assert controls['status']=='DESCRIPTIVE_ONLY'
    assert len(r['named_proxy_changes']['bond_simple']['removed_or_changed'])==1
    assert len(r['named_proxy_changes']['bond_simple']['added_or_changed'])==1


def test_unranked_geometry_never_gets_a_target_weight_control(tmp_path):
    a,p,e=case(tmp_path);b=deepcopy(a)
    b['geometry']['proxy_details']['bond_simple'][1]['weight']=None;sync(b)
    r=compare(a,b,p,e)
    row=next(x for x in r['scalar_comparisons']['bond_simple']['matched'] if x['weight_changed'])
    assert row['target_weight_controls']['status']=='UNASSESSED'
    assert row['after']['nominal_deviation'] is None
