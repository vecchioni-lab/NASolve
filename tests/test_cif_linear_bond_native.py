"""Target-only dictionary repair must reach every native copy without other edits."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest

from tests.test_cif_linear_bond_reference import reference
from tests.test_cif_triple_bond_audit import fixture as source_fixture
from nasolve.cif_linear_bond_reference import linear_bond_query,prepare_linear_bond_candidate
from nasolve.cif_native_monomers import capture_full_monomers


def fixture(tmp_path,code='Q17'):
    source,values=source_fixture(tmp_path,code)
    ref=reference(linear_bond_query(source,code));candidate=tmp_path/'candidate.cif'
    prepare_linear_bond_candidate(source,source,code,ref,candidate,bonds=[['Y','R']])
    definition=dict(bonds=[dict(atom_id_1=a,atom_id_2=b,type=order,value_dist=float(length),value_dist_esd=.02,value_dist_neutron=None)
        for a,b,order,length in zip(['L','X','Y'],['X','Y','R'],['single','triple','single'],['1.4','1.2','1.4'])],planes=['preserved'],chirality=['preserved'])
    atoms=[];mappings=[];proxies=[]
    for chain,component in [('A',code),('B',code),('C','OTH')]:
        identity=dict(model_id='',chain_id=chain,resseq='1',icode='',altloc='',resname=component)
        mappings.append(dict(literal_identity=dict(status='RECORDED',**identity),resname=component,site=chain+':1',chain_id=chain,
            metadata=dict(id=component,effective_definition=deepcopy(definition)),chem_mod_ids=['preserved']))
        offset=len(atoms)
        for i,name in enumerate(['L','X','Y','R'],offset):
            atoms.append(dict(i_seq=i,atom_id=name,identity=deepcopy(identity),label=chain+':'+name,xyz=[float(i),0.,0.]))
        for i,target in enumerate([1.4,1.2,1.4],offset):
            proxies.append(dict(i_seqs=[i,i+1],atoms=[atoms[i]['label'],atoms[i+1]['label']],distance_ideal=target,weight=2500.,origin_id=0,symmetry_operation=None))
    before=dict(status='REVIEW',fatal_problems=None,unsupported_fields=[],unused_definitions=[],inventory_detail='linked',
        atom_count=len(atoms),atoms=atoms,monomer_mappings=dict(status='RECORDED',rows=mappings),
        dictionary_loading=[dict(input='dictionary.cif',component_metadata=[dict(id=code,effective_definition=deepcopy(definition))])],
        geometry=dict(simple_bonds=deepcopy(proxies),asu_bonds=[],proxy_details=dict(bond_simple=proxies,bond_asu=[],planarity=['ring'],parallelity=['NAR']),
            proxy_counts=dict(bond_simple=9,bond_asu=0),sites_cart_exact=[a['xyz'] for a in atoms]),
        energy_inventory=dict(target=10),installed_api_sources=['preserved'])
    before['full_monomer_inventory']=capture_full_monomers(before,False)
    after=deepcopy(before);after['energy_inventory']['target']=9
    after['dictionary_loading'][0]['component_metadata'][0]['effective_definition']['bonds'][2]['value_dist']=1.459
    for row in after['monomer_mappings']['rows'][:2]:row['metadata']['effective_definition']['bonds'][2]['value_dist']=1.459
    for rows in (after['geometry']['simple_bonds'],after['geometry']['proxy_details']['bond_simple']):
        for i in (2,5):rows[i]['distance_ideal']=1.459
    return before,after,source,source,code,ref,candidate


def qualify(args):
    from nasolve.cif_linear_bond_native import qualify_linked_linear_bond_candidate
    return qualify_linked_linear_bond_candidate(*args,bonds=[['Y','R']])


@pytest.mark.parametrize('code',['Q17','PDU','A1AAZ'])
def test_target_changes_every_copy_and_preserves_unrelated_chemistry(tmp_path,code):
    args=fixture(tmp_path,code);original=deepcopy(args[:2]);files={p:p.read_bytes() for p in tmp_path.iterdir()}
    with patch('subprocess.Popen',side_effect=AssertionError('read-only qualification')):
        result=qualify(args)
    assert result['inventory_checks_pass'] and result['modeled_occurrences']==2
    assert result['changed_native_bonds']==2 and result['component_origin_preserved']
    assert result['energy_delta_qualification']=='NOT_RUN' and not result['automatic_adoption']
    assert args[:2]==original and all(p.read_bytes()==v for p,v in files.items())


@pytest.mark.parametrize('defect',['second_copy','bystander','weight','origin','symmetry','simple_summary','plane','nar','asu','coordinate','charge','unknown','counts','producer'])
def test_any_unplanned_native_change_is_visible(tmp_path,defect):
    args=fixture(tmp_path);after=args[1];geo=after['geometry'];proxies=geo['proxy_details']
    if defect=='second_copy':proxies['bond_simple'][5]['distance_ideal']=1.4
    elif defect=='bystander':proxies['bond_simple'][8]['distance_ideal']=1.459
    elif defect=='weight':proxies['bond_simple'][2]['weight']=100.
    elif defect=='origin':proxies['bond_simple'][2]['origin_id']=4
    elif defect=='symmetry':proxies['bond_simple'][2]['symmetry_operation']='-x,-y,z'
    elif defect=='simple_summary':geo['simple_bonds'][2]['distance_ideal']=1.4
    elif defect=='plane':proxies['planarity']=[]
    elif defect=='nar':proxies['parallelity']=[]
    elif defect=='asu':proxies['bond_asu']=[dict(i_seqs=[0,11])]
    elif defect=='coordinate':geo['sites_cart_exact'][2]=[9.,0.,0.]
    elif defect=='charge':after['monomer_mappings']['rows'][2]['metadata']['charge']=1
    elif defect=='unknown':after['unknown_category']={}
    elif defect=='counts':geo['proxy_counts']['bond_simple']=True
    elif defect=='producer':after['installed_api_sources']=[]
    assert not qualify(args)['inventory_checks_pass']


@pytest.mark.parametrize('defect',['candidate','provider','definition','mapping','metadata','atom','missing_atom','missing_proxy','duplicate_proxy','weight','label','origin','asu','unsupported','missing_full_mapping'])
def test_missing_ambiguous_or_unbound_starting_state_refuses(tmp_path,defect):
    args=fixture(tmp_path);before=args[0];rows=before['geometry']['proxy_details']['bond_simple']
    if defect=='candidate':args[-1].write_text(args[-1].read_text()+'\n')
    elif defect=='provider':before['dictionary_loading']*=2
    elif defect=='definition':before['dictionary_loading'][0]['component_metadata'][0]['effective_definition']['bonds'][2]['value_dist']=1.9
    elif defect=='mapping':before['monomer_mappings']['rows'].pop()
    elif defect=='metadata':before['monomer_mappings']['rows'][0]['metadata']['id']='OTH'
    elif defect=='atom':before['atoms'][1]['i_seq']=0
    elif defect=='missing_atom':before['atoms'][3]['atom_id']='absent'
    elif defect=='missing_proxy':rows.pop(2)
    elif defect=='duplicate_proxy':rows.append(deepcopy(rows[2]))
    elif defect=='weight':rows[2]['weight']=100.
    elif defect=='label':rows[2]['atoms'][0]='wrong'
    elif defect=='origin':rows[2]['origin_id']=4
    elif defect=='asu':before['geometry']['proxy_details']['bond_asu']=[dict(i_seqs=[2,3])]
    elif defect=='unsupported':before['unsupported_fields']=['opaque']
    elif defect=='missing_full_mapping':before.pop('full_monomer_inventory')
    with pytest.raises(ValueError):qualify(args)


def test_exact_endpoint_reversal_preserves_labels_and_parameters(tmp_path):
    args=fixture(tmp_path)
    for native in args[:2]:
        for rows in (native['geometry']['simple_bonds'],native['geometry']['proxy_details']['bond_simple']):
            for row in rows:row['i_seqs'].reverse();row['atoms'].reverse()
    assert qualify(args)['inventory_checks_pass']


def test_moved_inputs_work_without_original_location(tmp_path):
    old=tmp_path/'old';old.mkdir();args=list(fixture(old));new=tmp_path/'moved';old.rename(new)
    for i in (2,3,6):args[i]=new/args[i].name
    assert not old.exists() and qualify(args)['inventory_checks_pass']


def captured_fixture(tmp_path,monkeypatch):
    """Mock only the established capture authenticator, testing our composition."""
    import json
    from nasolve.cif_native_monomers import POLICY_ID as MONOMER_POLICY
    from nasolve import cif_captured_mixed_gradients as captured
    args=fixture(tmp_path);before,after,source,dictionary,code,ref,candidate=args
    model=tmp_path/'model.pdb';model.write_text('synthetic shared model')
    bystander=tmp_path/'other.cif';bystander.write_text('unchanged other component')
    phils=[]
    for name in ('first','second'):
        p=tmp_path/(name+'.phil');p.write_text(name);phils.append(p)
    entries={};receipts=[]
    for side,native,selected in [('before',before,dictionary),('after',after,candidate)]:
        root=tmp_path/side;root.mkdir();receipt=root/'native_receipt.json';receipt.write_text('{}')
        spec=dict(policy_inventory=True,energy_inventory=True,full_monomer_inventory=True,inventory_detail='linked')
        (root/'native_spec.json').write_text(json.dumps(spec));receipts.append(receipt)
        record=dict(phenix_version='SYNTHETIC',executable_sha256='a'*64,api_sources=['synthetic'],
            phil_namespace_policy='direct',dictionary_source_policy='EXPLICIT_DICTIONARIES',full_monomer_inventory_policy=MONOMER_POLICY)
        native['energy_inventory']['installed_sources']=['synthetic']
        entries[root]=(record,model,[bystander,selected],list(phils),native,{})
    monkeypatch.setattr(captured,'_inputs',lambda p:entries[p])
    return (source,code,ref,candidate,*receipts),dict(dictionary_index=1,bonds=[['Y','R']]),entries


def test_capture_composition_uses_exact_slot_and_existing_cold_reader(tmp_path,monkeypatch):
    from nasolve.cif_linear_bond_native import qualify_captured_linear_bond_candidate
    args,options,entries=captured_fixture(tmp_path,monkeypatch)
    with patch('subprocess.Popen',side_effect=AssertionError('native execution forbidden')):
        result=qualify_captured_linear_bond_candidate(*args,**options)
    assert result['capture_checks_pass'] and result['inventory_checks_pass']
    assert result['reference_authority']=='NOT_QUALIFIED'
    assert result['captures']['before']['anchor']=='before_native_directory'
    assert result['inventory_qualification']['changed_native_bonds']==2


@pytest.mark.parametrize('defect',['slot','bool_slot','dictionary_order','model','phil_order','producer','energy_producer','options','full_mapping','unexpected_change'])
def test_capture_composition_refuses_mismatched_context(tmp_path,monkeypatch,defect):
    import json
    from nasolve.cif_linear_bond_native import qualify_captured_linear_bond_candidate
    args,options,entries=captured_fixture(tmp_path,monkeypatch);entry=list(entries[args[-1].parent])
    if defect=='slot':options['dictionary_index']=0
    elif defect=='bool_slot':options['dictionary_index']=True
    elif defect=='dictionary_order':entry[2].reverse()
    elif defect=='model':p=tmp_path/'other.pdb';p.write_text('different');entry[1]=p
    elif defect=='phil_order':entry[3].reverse()
    elif defect=='producer':entry[0]['api_sources']=['different']
    elif defect=='energy_producer':entry[4]['energy_inventory']['installed_sources']=['different']
    elif defect=='options':
        p=args[-1].parent/'native_spec.json';v=json.loads(p.read_text());v['atom_name_mapping']=True;p.write_text(json.dumps(v))
    elif defect=='full_mapping':entry[0].pop('full_monomer_inventory_policy')
    elif defect=='unexpected_change':entry[4]['geometry']['proxy_details']['parallelity']=[]
    entries[args[-1].parent]=tuple(entry)
    with pytest.raises(ValueError):qualify_captured_linear_bond_candidate(*args,**options)


@pytest.mark.parametrize('field',['executable_sha256','api_sources'])
def test_both_captures_missing_the_same_producer_identity_still_refuse(tmp_path,monkeypatch,field):
    from nasolve.cif_linear_bond_native import qualify_captured_linear_bond_candidate
    args,options,entries=captured_fixture(tmp_path,monkeypatch)
    for entry in entries.values():entry[0].pop(field)
    with pytest.raises(ValueError,match='producer identity'):
        qualify_captured_linear_bond_candidate(*args,**options)
