"""Complete-request intake retains image roles without authorizing execution."""
import json
import shutil
from unittest.mock import patch

import pytest
pytest.importorskip('gemmi')

from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb,file_sha256
from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
from .test_cif_postmr_request import entry_case,case
from .test_cif_model_context import model,report
from .test_construct_registration import target
from .test_cif_repair_attempt import inventory


def registered_case(entry):
    m,args,sdk,store,generations,calls=entry
    path=args['model'];temp=path.parent/'template.pdb';model(temp)
    template=[line for line in temp.read_text().splitlines() if line.startswith(('ATOM  ','HETATM')) and line[22:26].strip()=='1' and line[12:16].strip()!='OP3']
    rows=[];targets=[];mapping={};strands=[]
    for chain,code,y in [('A','ZZZ',0),('B','YYY',40)]:
        ids=[]
        for number,index,residue in [(1,0,'DC'),(4,1,code),(9,2,'DA')]:
            site=chain+':'+str(number);targets.append((site,residue));mapping[site]=site;ids.append(site)
            for line in template:
                xyz=[float(line[p:p+8]) for p in (30,38,46)]
                xyz=[xyz[0]+index*5.53,xyz[1]+index*.76+y,xyz[2]+index*1.308]
                rows.append('ATOM  '+f'{len(rows)+1:5d}'+line[11:17]+f'{residue:>3}'+line[20:21]+chain+f'{number:4d}'+line[26:30]+''.join(f'{v:8.3f}' for v in xyz)+line[54:])
        rows.append('TER');strands.append(dict(strand_id=chain,sites=ids,five_prime_boundary='representation',three_prime_boundary='representation'))
    path.write_text('CRYST1   18.000  100.000  100.000  90.00  90.00  90.00 P 1           1\n'+'\n'.join(rows)+'\nEND\n')
    reg=path.parent/'registration.json';reg.write_text(json.dumps(build_construct_registration(inspect_pdb(path),target(*targets),{'source':mapping},source='fixture')))
    disc=path.parent/'discovery.json';disc.write_text(json.dumps(dict(schema_version=1,kind='topostitch-end-discovery-input',model_sha256=file_sha256(path),registration_sha256=file_sha256(reg),copy_id='source',strands=strands,duplex_pairs=[],protected_sites=[],do_not_connect_sites=[],pairing_inventory_complete=False)))
    edges=path.parent/'edges.json';edges.write_text(json.dumps([dict(continuation_id=i,source_site=c+':9',target_site=c+':1',target_operator_xyz='x+1,y,z') for i,c in enumerate(('A','B'),1)]))
    args.update(report=report(),supplementary_phils=[],registered_preparation=dict(registration_model=path,registration=reg,discovery=disc,continuations=edges))
    return entry


def test_ordinary_intake_freezes_registered_role_and_holds_execution(entry_case):
    m,args,sdk,store,generations,calls=registered_case(entry_case)
    before=inventory(args['model'].parent)
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        request=initialize_postmr_dictionary_request(**args)
    c=request['configuration']
    assert 'model_context' not in c and c['registered_backbone']['path']=='inputs/registered_backbone'
    assert c['controls']['expected_links']==[['A:1','A:4'],['A:4','A:9'],['B:1','B:4'],['B:4','B:9']]
    assert c['controls']['sites']['ZZZ']['contexts']==[dict(site='A:4',incoming_site='A:1',outgoing_site='A:9',five_prime_state='linked',three_prime_state='linked')]
    saved=m.inspect_dictionary_request(args['output']);assert saved['attempts']==[]
    assert saved['availability']=='BLOCKED' and saved['retry_authorized'] is False
    assert 'native/result consumer' in saved['blocked_reason']
    frozen=inventory(args['output'])
    with pytest.raises(ValueError,match='[Rr]egistered.*execution|execution.*registered'):
        m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generations,after_attempt=0)
    assert inventory(args['output'])==frozen and not calls
    for name,value in before.items():assert inventory(args['model'].parent)[name]==value


@pytest.mark.parametrize('allow_source_recovery', [False, True])
def test_registered_hold_survives_independent_source_recovery_permission(entry_case, allow_source_recovery):
    m,args,*_=registered_case(entry_case)
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        request=initialize_postmr_dictionary_request(**args,automatic_connected_order=allow_source_recovery)
        saved=m.inspect_dictionary_request(args['output'])
    config=request['configuration']
    assert ('connected_order_policy' in config) is allow_source_recovery
    assert 'registered_backbone' in config and 'registered_execution_policy' not in config
    assert saved['availability']=='BLOCKED' and saved['attempts']==[]
    assert saved['retry_authorized'] is False


def test_registered_request_relocates_without_original_source(entry_case,tmp_path):
    m,args,*_=registered_case(entry_case);request=initialize_postmr_dictionary_request(**args)
    destination=tmp_path/'relocated';shutil.move(args['output'],destination)
    for key in ('model',):args[key].unlink()
    for key,path in args['registered_preparation'].items():
        if path.exists():path.unlink()
    assert not args['output'].exists()
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read only')):
        assert m.inspect_dictionary_request(destination)['request']==request


@pytest.mark.parametrize('damage',['source','image','extra'])
def test_frozen_registered_role_cannot_change(entry_case,damage):
    m,args,*_=registered_case(entry_case);initialize_postmr_dictionary_request(**args)
    root=args['output']/'inputs/registered_backbone'
    if damage=='source':(root/'source.pdb').write_bytes((root/'source.pdb').read_bytes()+b'\n')
    elif damage=='image':
        p=root/'continuations.json';rows=json.loads(p.read_text());rows[0]['target_operator_xyz']='x-1,y,z';p.write_text(json.dumps(rows))
    else:(root/'extra').write_text('unrequested')
    with pytest.raises(ValueError):m.inspect_dictionary_request(args['output'])


def test_modified_image_endpoint_is_not_silently_local(entry_case):
    m,args,*_=registered_case(entry_case)
    # An explicitly selected endpoint requires separate image-aware projection.
    from nasolve.cif_registered_preparation_input import local_component_view
    from nasolve.cif_registered_preparation_context import derive_registered_preparation_context
    record=derive_registered_preparation_context(args['model'],args['report'],['DC'],**args['registered_preparation'])
    with pytest.raises(ValueError,match='image endpoint|image-endpoint'):local_component_view(args['model'],record)
