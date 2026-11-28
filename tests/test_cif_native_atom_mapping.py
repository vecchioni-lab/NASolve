"""Observed native aliases cannot authorize chemical changes or rewrite history."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import pytest
from .test_cif_attachment_native import fixture, rebind, save, audit


def mapped_fixture(root, rename=False):
    from nasolve.cif_native_atom_mapping import native_mapping_worker, POLICY_ID
    from nasolve.cif_native_validation import _NATIVE_WORKER
    paths=fixture(root);p=paths[1];r=json.loads(p.read_text());n=r['native_validation']
    for row in n['monomer_mappings']['rows']:
        atoms=[a for a in n['atoms'] if a['identity']['resseq'].strip()==row['literal_identity']['resseq'].strip()]
        row['atom_name_mapping']={'status':'RECORDED','aliases':{},'mon_lib_names_available':False,
            'active':[{'model_i_seq':a['i_seq'],'model_atom_id':a['atom_id'],'mon_lib_name':None} for a in atoms],
            'expected':[{'model_i_seq':a['i_seq'],'model_atom_id':a['atom_id'],'dictionary_atom_id':a['atom_id']} for a in atoms],
            'unexpected':[],'duplicates':[]}
    if rename:
        row=n['monomer_mappings']['rows'][0];old="O5'";new='O5X';d=row['metadata']['effective_definition']
        for a in d['atoms']:
            if a['atom_id']==old:a['atom_id']=new
        for b in d['bonds']:
            for k in ('atom_id_1','atom_id_2'):
                if b[k]==old:b[k]=new
        row['atom_name_mapping']['aliases'][old]=new
        next(a for a in row['atom_name_mapping']['expected'] if a['model_atom_id']==old)['dictionary_atom_id']=new
    n['atom_name_mapping_policy']=POLICY_ID;r['atom_name_mapping_policy']=POLICY_ID
    spec=json.loads((p.parent/'native_spec.json').read_text());spec['atom_name_mapping']=True;save(p.parent/'native_spec.json',spec)
    (p.parent/'native_worker.py').write_text(native_mapping_worker(_NATIVE_WORKER));save(p,r);rebind(p)
    return paths


def test_observed_alias_reconciles_names_without_erasing_literal_findings(tmp_path):
    paths=mapped_fixture(tmp_path,True)
    with patch('subprocess.Popen') as launch:r=audit(paths)
    assert r['definition_status']=='REVIEW' and r['mapped_definition_status']=='MATCH'
    assert r['atom_name_mapping']['alias_count']==1
    assert r['mapped_definitions']['A:1']['atom_name_aliases']=={"O5'":'O5X'}
    assert r['link_status']=='MATCH' and r['status']=='REVIEW' and not r['automatic_adoption']
    launch.assert_not_called()


def test_legacy_worker_output_remains_unchanged(tmp_path):
    r=audit(fixture(tmp_path))
    assert 'atom_name_mapping' not in r and 'mapped_definitions' not in r


@pytest.mark.parametrize('defect',['worker','spec','receipt_policy','report_policy','index','name','dictionary_name','duplicate_expected','duplicate_active','alias_missing','alias_wrong','alias_unbound','wrong_element','wrong_site','active_missing','mon_lib_length','duplicates','non_bool'])
def test_mapping_cannot_hide_ambiguous_or_contradictory_identity(tmp_path,defect):
    paths=mapped_fixture(tmp_path,True);p=paths[1];r=json.loads(p.read_text());n=r['native_validation'];row=n['monomer_mappings']['rows'][0];m=row['atom_name_mapping']
    if defect=='worker':(p.parent/'native_worker.py').write_text('unknown worker')
    elif defect=='spec':s=json.loads((p.parent/'native_spec.json').read_text());s['atom_name_mapping']=False;save(p.parent/'native_spec.json',s)
    elif defect=='receipt_policy':r['atom_name_mapping_policy']='other'
    elif defect=='report_policy':n['atom_name_mapping_policy']='other'
    elif defect=='index':m['expected'][0]['model_i_seq']=True
    elif defect=='name':m['expected'][0]['model_atom_id']='WRONG'
    elif defect=='dictionary_name':m['expected'][0]['dictionary_atom_id']='WRONG'
    elif defect=='duplicate_expected':m['expected'].append(deepcopy(m['expected'][0]))
    elif defect=='duplicate_active':m['active'].append(deepcopy(m['active'][0]))
    elif defect=='alias_missing':m['aliases']={}
    elif defect=='alias_wrong':m['aliases']["O5'"]='WRONG'
    elif defect=='alias_unbound':m['aliases']['ABSENT']='OTHER'
    elif defect=='wrong_element':row['metadata']['effective_definition']['atoms'][0]['type_symbol']='Xe'
    elif defect=='wrong_site':row['site']='Z:99'
    elif defect=='active_missing':m['active'].pop()
    elif defect=='mon_lib_length':m['active'][0].pop('mon_lib_name')
    elif defect=='duplicates':m['duplicates']=[deepcopy(m['expected'][0])]
    elif defect=='non_bool':m['mon_lib_names_available']=1
    save(p,r);rebind(p)
    with pytest.raises(ValueError):audit(paths)


@pytest.mark.parametrize('defect',['charge','missing_hydrogen','bond'])
def test_native_alias_is_not_permission_to_change_chemistry(tmp_path,defect):
    paths=mapped_fixture(tmp_path,True)
    def change(r):
        d=r['native_validation']['monomer_mappings']['rows'][0]['metadata']['effective_definition']
        if defect=='charge':d['atoms'][0]['charge']=2
        if defect=='missing_hydrogen':
            h=next(a['atom_id'] for a in d['atoms'] if a['type_symbol']=='H');d['atoms']=[a for a in d['atoms'] if a['atom_id']!=h];d['bonds']=[b for b in d['bonds'] if h not in b.values()]
        if defect=='bond':d['bonds'].pop()
    rebind(paths[1],change);r=audit(paths)
    assert r['mapped_definition_status']=='REVIEW' and r['definition_status']=='REVIEW'


def test_recorded_mon_lib_names_are_observations_not_final_alias_authority(tmp_path):
    paths=mapped_fixture(tmp_path,True)
    def change(r):
        for row in r['native_validation']['monomer_mappings']['rows']:
            m=row['atom_name_mapping'];m['mon_lib_names_available']=True
            for a in m['active']:a['mon_lib_name']='initial-name' if a['model_atom_id']=="O5'" else None
    rebind(paths[1],change)
    assert audit(paths)['mapped_definition_status']=='MATCH'


def test_missing_native_api_stays_explicitly_unassessed(tmp_path):
    paths=mapped_fixture(tmp_path)
    rebind(paths[1],lambda r:r['native_validation']['monomer_mappings']['rows'][0].update(atom_name_mapping={'status':'UNSUPPORTED','missing_fields':['expected_atoms']}))
    r=audit(paths);assert r['atom_name_mapping']['status']=='UNSUPPORTED' and r['mapped_definition_status']=='NOT_ASSESSED'


@pytest.mark.parametrize('value',[None,0,1,'yes',[],{}])
def test_capture_request_requires_explicit_boolean(tmp_path,value):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError,match='mapping'):
        inspect_native_bundle(tmp_path/'absent',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='test',atom_name_mapping=value)
    assert not (tmp_path/'out').exists()


def test_capture_records_final_binding_and_intermediate_names_separately():
    from types import SimpleNamespace as NS
    from nasolve.cif_native_atom_mapping import capture_atom_name_mapping
    atom=NS(i_seq=17,name=' OP3');mm=NS(expected_atoms={'O3T':atom},unexpected_atoms={},duplicate_atoms={},
        atom_names_mappings={'OP3':'O3T'},active_atoms=[atom],mon_lib_names=['OP3'])
    r=capture_atom_name_mapping(mm)
    assert r['expected']==[{'dictionary_atom_id':'O3T','model_i_seq':17,'model_atom_id':'OP3'}]
    assert r['active'][0]['mon_lib_name']=='OP3' and r['aliases']=={'OP3':'O3T'}
    mm.mon_lib_names=[]
    with pytest.raises(ValueError):capture_atom_name_mapping(mm)
    assert capture_atom_name_mapping(NS())['status']=='UNSUPPORTED'


def test_worker_extension_preserves_original_and_rejects_unknown_seam():
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_native_atom_mapping import native_mapping_worker
    from hashlib import sha256
    assert sha256(_NATIVE_WORKER.encode()).hexdigest()=='9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78'
    worker=native_mapping_worker(_NATIVE_WORKER);compile(worker,'native_worker.py','exec')
    assert worker!=_NATIVE_WORKER
    with pytest.raises(ValueError):native_mapping_worker('unknown code')


@pytest.mark.parametrize('options',[{'inventory_detail':'basic'},{'inventory_detail':'linked','energy_inventory':True}])
def test_capture_rejects_unqualified_worker_combinations_before_allocation(tmp_path,options):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError,match='mapping'):
        inspect_native_bundle(tmp_path/'absent',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='test',atom_name_mapping=True,**options)
    assert not (tmp_path/'out').exists()


def test_all_bound_indices_may_be_reordered_without_changing_alias_meaning(tmp_path):
    paths=mapped_fixture(tmp_path,True);original=audit(paths)
    def change(r):
        n=r['native_validation'];n['atoms'].reverse();translation={a['i_seq']:i for i,a in enumerate(n['atoms'])}
        for i,a in enumerate(n['atoms']):a['i_seq']=i
        g=n['geometry'];g['sites_cart_exact']=[a['xyz'] for a in n['atoms']]
        for row in g['simple_bonds']:row['i_seqs']=[translation[i] for i in row['i_seqs']]
        g['proxy_details']['bond_simple']=deepcopy(g['simple_bonds'])
        for row in n['monomer_mappings']['rows']:
            for k in ('active','expected','unexpected','duplicates'):
                for a in row['atom_name_mapping'][k]:a['model_i_seq']=translation[a['model_i_seq']]
    rebind(paths[1],change);result=audit(paths)
    assert result['mapped_definitions']==original['mapped_definitions'] and result['link_status']=='MATCH'


def test_alias_cannot_merge_a_retained_unmodelled_source_hydrogen(tmp_path):
    paths=mapped_fixture(tmp_path,True)
    def change(r):
        row=r['native_validation']['monomer_mappings']['rows'][0];d=row['metadata']['effective_definition']
        h=next(a['atom_id'] for a in d['atoms'] if a['type_symbol']=='H')
        d['atoms']=[a for a in d['atoms'] if a['atom_id']!=h]
        for a in d['atoms']:
            if a['atom_id']=='O5X':a['atom_id']=h
        for b in d['bonds']:
            for k in ('atom_id_1','atom_id_2'):
                if b[k]=='O5X':b[k]=h
        m=row['atom_name_mapping'];m['aliases']["O5'"]=h
        next(a for a in m['expected'] if a['model_atom_id']=="O5'")['dictionary_atom_id']=h
    rebind(paths[1],change)
    with pytest.raises(ValueError,match='collapse'):audit(paths)


def test_text_cli_reports_observed_aliases_without_promoting_chemistry(tmp_path,capsys):
    from nasolve.cli import main
    paths=mapped_fixture(tmp_path,True)
    with patch('subprocess.Popen') as launch:
        assert main(['cif-doctor','link-native',str(paths[0]),'--native-receipt',str(paths[1])])==2
    text=capsys.readouterr().out
    assert 'Observed native atom aliases: 1; mapped source definitions: MATCH' in text
    assert 'source definitions: REVIEW' in text
    launch.assert_not_called()
