"""Native capture integrity and literal source-port identity, without type transfer."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.cli import main
from nasolve.cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
from nasolve.cif_linked_preparation import component_values
from .test_cif_attachment_links import case,record
from .test_cif_catalogue import snapshot


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def artifact(path,root):
    return dict(record(path,root),anchor='native_directory')


def fixture(root):
    inputs=root/'source';inputs.mkdir();manifest=case(inputs)
    declaration=json.loads(manifest.read_text());model=inputs/'model.pdb'
    native_dir=root/'native';native_dir.mkdir();(native_dir/'inputs').mkdir()
    frozen=native_dir/'inputs/model.pdb';frozen.write_bytes(model.read_bytes())
    atoms=[];mappings=[]
    for line in model.read_text().splitlines():
        if not line.startswith('HETATM'):continue
        i=len(atoms);atoms.append({'i_seq':i,'atom_id':line[12:16].strip(),'label':str(i),
            'element':line[76:78],'xyz':[float(line[j:j+8]) for j in (30,38,46)],'occupancy':float(line[54:60]),
            'identity':{'chain_id':line[21:22],'resseq':line[22:26],'resname':line[17:20],'icode':'','model_id':'','altloc':''}})
    for i,entry in enumerate(declaration['sites']):
        v=component_values(inputs/entry['candidate']['path'],entry['component']);names=v['_chem_comp_atom.atom_id']
        definition={'atoms':[{'atom_id':a,'type_symbol':e,'charge':float(q),'type_energy':'TEST'} for a,e,q in zip(names,v['_chem_comp_atom.type_symbol'],v['_chem_comp_atom.charge'])],
            'bonds':[{'atom_id_1':a,'atom_id_2':b} for a,b in zip(v['_chem_comp_bond.atom_id_1'],v['_chem_comp_bond.atom_id_2'])]}
        ident={'chain_id':'A','resseq':str(i+1),'resname':entry['component'],'icode':'','model_id':'','altloc':''}
        mappings.append({'site':f'A:{i+1}','resname':entry['component'],'literal_identity':dict(ident,status='RECORDED'),
            'metadata':{'group':'TEST','classification':{'status':'RECORDED','value':'TEST'},'effective_definition':definition},
            'unexpected_atoms':{'status':'RECORDED','atom_ids':[]},'missing_non_hydrogen_atoms':{'status':'RECORDED','atom_ids':[]}})
    left=next(a['i_seq'] for a in atoms if a['identity']['resseq'].strip()=='1' and a['atom_id']=="O3'")
    right=next(a['i_seq'] for a in atoms if a['identity']['resseq'].strip()=='2' and a['atom_id']=='P')
    bond={'i_seqs':[left,right],'atoms':[str(left),str(right)],'distance_ideal':1.607,'weight':1000.,'symmetry_operation':None}
    native={'schema_version':1,'policy_id':NATIVE_POLICY_ID,'status':'REVIEW','automatic_adoption':False,
        'scientific_approval':'NOT_RUN','model_editing':'NOT_RUN','optimization':'NOT_RUN','dictionary_loading':[],
        'inventory_detail':'linked','atoms':atoms,'atom_count':len(atoms),'monomer_mappings':{'status':'RECORDED','rows':mappings},
        'fatal_problems':None,'unused_definitions':[],'unsupported_fields':[],
        'geometry':{'status':'RECORDED','simple_bonds':[bond],'asu_bonds':[],'proxy_counts':{'bond_simple':1,'bond_asu':0},
                    'proxy_details':{'bond_simple':[bond],'bond_asu':[]},'sites_cart_exact':[a['xyz'] for a in atoms]}}
    save(native_dir/'native_spec.json',{'policy_id':NATIVE_POLICY_ID,'model':'inputs/model.pdb','dictionaries':[],
        'phil_files':[],'phil_namespace_policy':'direct','inventory_detail':'linked','installed_library_only':True})
    (native_dir/'native_worker.py').write_text(_NATIVE_WORKER);(native_dir/'native.log').write_text('synthetic fixture, not native proof\n')
    save(native_dir/'native_validation.json',native)
    receipt={'schema_version':1,'audit_kind':'cif_native_bundle_inspection','policy_id':NATIVE_POLICY_ID,
        'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,'symlink_outputs':[],
        'automatic_adoption':False,'scientific_approval':'NOT_RUN','optimization':'NOT_RUN','model_editing':'NOT_RUN','readyset_retry':'NOT_RUN',
        'phenix_version':'synthetic-test','execution':{'status':'COMPLETED','returncode':0},
        'inputs':[dict(artifact(frozen,native_dir),role='model',input_index=0)],'outputs':[],
        'phil_namespace_policy':'direct','dictionary_source_policy':'INSTALLED_LIBRARY_ONLY','native_validation':native}
    path=native_dir/'native_receipt.json';save(path,receipt);rebind(path)
    return manifest,path


def rebind(path,change=None):
    r=json.loads(path.read_text())
    if change:change(r)
    save(path.parent/'native_validation.json',r['native_validation'])
    r['outputs']=[artifact(p,path.parent) for p in sorted(path.parent.rglob('*')) if p.is_file() and p!=path]
    save(path,r)


def audit(paths):
    from nasolve.cif_attachment_native import inspect_native_attachment_links
    return inspect_native_attachment_links(*paths)


def test_public_native_link_command_fails_before_implementation(tmp_path,capsys):
    paths=fixture(tmp_path);before=snapshot(tmp_path)
    with patch('subprocess.Popen') as launch:
        assert main(['cif-doctor','link-native',str(paths[0]),'--native-receipt',str(paths[1]),'--json'])==2
    result=json.loads(capsys.readouterr().out)
    assert result['link_status']=='MATCH' and result['definition_status']=='MATCH'
    assert result['status']=='REVIEW' and result['native_qualification']=='NOT_ASSESSED'
    assert snapshot(tmp_path)==before and not result['automatic_adoption'];launch.assert_not_called()


@pytest.mark.parametrize('defect',['wrong_atom','missing','extra','duplicate','symmetry'])
def test_counts_and_names_cannot_replace_exact_ports(tmp_path,defect):
    paths=fixture(tmp_path)
    def alter(r):
        n=r['native_validation'];g=n['geometry'];bond=g['simple_bonds'][0]
        if defect=='wrong_atom':
            i=next(a['i_seq'] for a in n['atoms'] if a['identity']['resseq'].strip()=='1' and a['atom_id']=="O5'")
            bond['i_seqs'][0]=i;bond['atoms'][0]=str(i)
        if defect=='missing':g['simple_bonds']=[]
        if defect in {'extra','duplicate'}:
            new=deepcopy(bond)
            if defect=='extra':new['i_seqs'][0]=0;new['atoms'][0]='0'
            g['simple_bonds'].append(new)
        if defect=='symmetry':g['asu_bonds']=[g['simple_bonds'].pop()]
        g['proxy_counts']={'bond_simple':len(g['simple_bonds']),'bond_asu':len(g['asu_bonds'])}
        g['proxy_details']={'bond_simple':g['simple_bonds'],'bond_asu':g['asu_bonds']}
    rebind(paths[1],alter)
    assert audit(paths)['link_status']=='REVIEW'


@pytest.mark.parametrize('defect',['hash','embedded','worker','duplicate_output','escape','bool_code','model','index','label','xyz','geometry_xyz','weight','target','spec','identity','atom_count','proxy_count','proxy_details'])
def test_capture_or_native_contradictions_fail_closed(tmp_path,defect):
    paths=fixture(tmp_path);receipt=paths[1];r=json.loads(receipt.read_text());n=r['native_validation']
    if defect=='hash':(receipt.parent/'native.log').write_text('changed');
    elif defect=='embedded':r['native_validation']['atom_count']+=1;save(receipt,r)
    elif defect=='worker':(receipt.parent/'native_worker.py').write_text('unexpected code');rebind(receipt)
    elif defect=='duplicate_output':r['outputs'].append(r['outputs'][0]);save(receipt,r)
    elif defect=='escape':r['outputs'][0]['path']='../escape';save(receipt,r)
    elif defect=='bool_code':r['execution']['returncode']=False;save(receipt,r)
    elif defect=='model':
        p=receipt.parent/'inputs/model.pdb';p.write_text(p.read_text()+'REMARK altered\n');r['inputs'][0].update(artifact(p,receipt.parent));save(receipt,r);rebind(receipt)
    elif defect=='spec':
        p=receipt.parent/'native_spec.json';s=json.loads(p.read_text());s['model']='other.pdb';save(p,s);rebind(receipt)
    else:
        if defect=='index':n['atoms'][0]['i_seq']=True
        if defect=='label':n['geometry']['simple_bonds'][0]['atoms'][0]='bad'
        if defect=='xyz':n['atoms'][0]['xyz'][0]+=1
        if defect=='geometry_xyz':n['geometry']['sites_cart_exact'][0][0]+=1
        if defect=='weight':n['geometry']['simple_bonds'][0]['weight']=float('nan')
        if defect=='target':n['geometry']['simple_bonds'][0]['distance_ideal']=0
        if defect=='identity':n['atoms'][0]['identity']['altloc']='A'
        if defect=='atom_count':n['atom_count']+=1
        if defect=='proxy_count':n['geometry']['proxy_counts']['bond_simple']+=1
        if defect=='proxy_details':n['geometry']['proxy_details']['bond_simple']=[]
        if defect in {'label','weight','target'}:n['geometry']['proxy_details']['bond_simple']=n['geometry']['simple_bonds']
        save(receipt,r);rebind(receipt)
    with pytest.raises(ValueError):audit(paths)


@pytest.mark.parametrize('defect',['missing_atom','extra_atom','element','bond','charge','mapping','literal'])
def test_effective_definition_disagreement_is_separate_from_correct_link(tmp_path,defect):
    paths=fixture(tmp_path)
    def alter(r):
        row=r['native_validation']['monomer_mappings']['rows'][0];d=row['metadata']['effective_definition']
        if defect=='missing_atom':d['atoms'].pop()
        if defect=='extra_atom':d['atoms'].append(dict(d['atoms'][0],atom_id='EXTRA'))
        if defect=='element':d['atoms'][0]['type_symbol']='S'
        if defect=='bond':d['bonds'].pop()
        if defect=='charge':d['atoms'][0]['charge']=3
        if defect=='mapping':row['unexpected_atoms']['atom_ids']=['EXTRA']
        if defect=='literal':row['literal_identity']['resname']='BAD'
    rebind(paths[1],alter);result=audit(paths)
    assert result['link_status']=='MATCH' and result['definition_status']=='REVIEW'


def test_types_are_observations_and_partial_charge_is_never_formal_charge(tmp_path):
    paths=fixture(tmp_path)
    def alter(r):
        for row in r['native_validation']['monomer_mappings']['rows']:
            for atom in row['metadata']['effective_definition']['atoms']:
                atom.update(charge=None,partial_charge=0,type_energy='UNQUALIFIED_TYPE')
    rebind(paths[1],alter);result=audit(paths)
    assert result['definition_status']=='MATCH'
    for row in result['definitions'].values():
        assert row['formal_charge_status']=='UNSUPPORTED' and not row['partial_charge_substituted']
        assert row['energy_type_authority']=='NOT_QUALIFIED'
    assert result['native_qualification']=='NOT_ASSESSED'


def test_failed_native_capture_cannot_become_empty_success(tmp_path,capsys):
    paths=fixture(tmp_path)
    def fail(r):
        r.update(status='FAILED',execution={'status':'FAILED','returncode':2})
        r['native_validation'].update(status='FAILED',error='Unknown native type',geometry={'status':'NOT_RUN'})
    rebind(paths[1],fail);result=audit(paths)
    assert result['native_status']=='FAILED' and result['link_status']=='NOT_ASSESSED'
    assert result['definition_status']=='NOT_ASSESSED'
    assert main(['cif-doctor','link-native',str(paths[0]),'--native-receipt',str(paths[1])])==2
    assert 'FAILED' in capsys.readouterr().out


def test_exact_relocation_preserves_bytes_and_never_runs_worker(tmp_path):
    old=tmp_path/'original';old.mkdir();paths=fixture(old);expected=audit(paths)
    moved=tmp_path/'moved';old.rename(moved);before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Read-only')):
        assert audit(tuple(moved/p.relative_to(old) for p in paths))==expected
    assert not old.exists() and snapshot(moved)==before


def test_selected_input_changes_during_audit_are_rejected(tmp_path):
    import nasolve.cif_attachment_native as module
    paths=fixture(tmp_path);original=module._definitions
    def mutate(*args):
        result=original(*args);paths[0].write_bytes(paths[0].read_bytes()+b'\n');return result
    with patch.object(module,'_definitions',mutate),pytest.raises(ValueError,match='changed'):audit(paths)


def test_native_reordering_and_float_roundoff_do_not_change_model_identity(tmp_path):
    paths=fixture(tmp_path)
    def alter(r):
        n=r['native_validation'];count=len(n['atoms']);n['atoms'].reverse()
        for i,atom in enumerate(n['atoms']):
            atom['i_seq']=i;atom['xyz'][0]+=1e-14
        for bond in n['geometry']['simple_bonds']:bond['i_seqs']=[count-1-i for i in bond['i_seqs']]
        n['geometry']['proxy_details']['bond_simple']=n['geometry']['simple_bonds']
        n['geometry']['sites_cart_exact']=[a['xyz'] for a in n['atoms']]
    rebind(paths[1],alter)
    assert audit(paths)['link_status']=='MATCH'


def test_coordinate_change_beyond_roundoff_is_not_accepted(tmp_path):
    paths=fixture(tmp_path)
    def alter(r):
        n=r['native_validation'];n['atoms'][0]['xyz'][0]+=1e-7
        n['geometry']['sites_cart_exact']=[a['xyz'] for a in n['atoms']]
    rebind(paths[1],alter)
    with pytest.raises(ValueError,match='coordinates'):audit(paths)


def test_literal_port_names_are_not_an_o3_p_heuristic(tmp_path):
    paths=fixture(tmp_path);manifest,receipt=paths;root=manifest.parent
    declaration=json.loads(manifest.read_text())
    for entry in declaration['sites']:
        for role in ['source','context','candidate']:
            p=root/entry[role]['path'];p.write_text(p.read_text().replace("O3'",'X3X'));entry[role]=record(p,root)
    p=root/declaration['model']['path'];p.write_text(p.read_text().replace("O3'",'X3X'));declaration['model']=record(p,root);save(manifest,declaration)
    def rename(value):
        if isinstance(value,dict):return {k:rename(v) for k,v in value.items()}
        if isinstance(value,list):return [rename(v) for v in value]
        return 'X3X' if value=="O3'" else value
    r=json.loads(receipt.read_text());r['native_validation']=rename(r['native_validation'])
    frozen=receipt.parent/r['inputs'][0]['path'];frozen.write_bytes(p.read_bytes());r['inputs'][0].update(artifact(frozen,receipt.parent));save(receipt,r);rebind(receipt)
    assert audit(paths)['link_status']=='MATCH'


@pytest.mark.parametrize('mode',['missing','shape','symlink','source_size','receipt_limit','duplicate_mapping','duplicate_definition'])
def test_missing_ambiguous_or_malformed_evidence_never_passes(tmp_path,mode):
    import nasolve.cif_attachment_native as module
    paths=fixture(tmp_path);receipt=paths[1];r=json.loads(receipt.read_text())
    if mode=='missing':r['outputs']=[o for o in r['outputs'] if o['path']!='native.log'];save(receipt,r)
    if mode=='shape':save(receipt,[])
    if mode=='symlink':
        p=receipt.parent/'native.log';p.rename(receipt.parent/'original.log');p.symlink_to(receipt.parent/'original.log')
    if mode=='source_size':r['inputs'][0]['size']+=1;save(receipt,r)
    if mode=='duplicate_mapping':r['native_validation']['monomer_mappings']['rows'].append(deepcopy(r['native_validation']['monomer_mappings']['rows'][0]));save(receipt,r);rebind(receipt)
    if mode=='duplicate_definition':
        a=r['native_validation']['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'];a.append(deepcopy(a[0]));save(receipt,r);rebind(receipt)
    with patch.object(module,'MAX_RECEIPT_BYTES',1 if mode=='receipt_limit' else module.MAX_RECEIPT_BYTES):
        with pytest.raises(ValueError):audit(paths)


def test_geometry_coordinate_roundoff_is_distinct_from_model_movement(tmp_path):
    paths=fixture(tmp_path)
    def alter(r):r['native_validation']['geometry']['sites_cart_exact'][0][0]+=1e-14
    rebind(paths[1],alter)
    assert audit(paths)['link_status']=='MATCH'


def test_report_is_exact_json_replay_data(tmp_path):
    result=audit(fixture(tmp_path))
    assert json.loads(json.dumps(result,allow_nan=False))==result


@pytest.mark.parametrize('kind',['dictionary','phil'])
def test_successful_capture_must_record_the_exact_consumed_input_order(tmp_path,kind):
    paths=fixture(tmp_path);receipt=paths[1];r=json.loads(receipt.read_text());n=r['native_validation']
    p=receipt.parent/'inputs'/('definition.cif' if kind=='dictionary' else 'parameters.phil')
    p.write_text('synthetic preserved input\n');ref=dict(artifact(p,receipt.parent),role=kind,input_index=1)
    r['inputs'].append(ref);spec_path=receipt.parent/'native_spec.json';spec=json.loads(spec_path.read_text())
    if kind=='dictionary':
        spec.update(dictionaries=[ref['path']],installed_library_only=False);r['dictionary_source_policy']='EXPLICIT_DICTIONARIES'
        n['dictionary_loading']=[{'status':'RECORDED','input':ref['path']}]
    else:
        spec['phil_files']=[ref['path']];n['phil_adaptations']=[{'input':ref['path']}]
    save(spec_path,spec);save(receipt,r);rebind(receipt)
    assert audit(paths)['link_status']=='MATCH'
    def alter(r):r['native_validation']['dictionary_loading' if kind=='dictionary' else 'phil_adaptations'][0]['input']='inputs/unselected.file'
    rebind(receipt,alter)
    with pytest.raises(ValueError,match='consumed'):audit(paths)
