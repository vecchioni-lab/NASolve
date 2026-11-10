"""Literal input provenance is immutable evidence, never native qualification."""
from copy import deepcopy
import json
import shutil
from unittest.mock import patch

import pytest

from tests.test_cif_na_policy import fixture as policy_fixture
from tests.test_cif_attachment_native import artifact, rebind, save
from tests.test_cif_repair_attempt import inventory
from nasolve.cif_native_validation import _NATIVE_WORKER, NATIVE_POLICY_ID


def capture(root, *, model=None, phil_text=None):
    root.mkdir()
    original, phil, native = policy_fixture(root)
    if model is not None:
        original.write_bytes(model.read_bytes())
    else:
        # The complete dictionary composer owns site modifiers, even though
        # the lower-level C21 compiler can preserve them for other consumers.
        text = phil.read_text()
        a = text.index(' apply_cif_modification {'); b = text.index(' }', a)
        phil.write_text(text[:a] + text[b+3:])
    if phil_text is not None: phil.write_text(phil_text)
    native['atoms'] = []
    for line in original.read_text().splitlines():
        if line[:6] not in ('ATOM  ', 'HETATM'): continue
        i = len(native['atoms'])
        native['atoms'].append(dict(i_seq=i, label=f'native-{i}', atom_id=line[12:16].strip(),
            element=line[76:78].strip(), xyz=[float(line[j:j+8]) for j in (30,38,46)], occupancy=float(line[54:60]),
            identity=dict(model_id='', chain_id=line[21], resseq=line[22:26].strip(), resname=line[17:20].strip(), altloc='', icode='')))
    native.update(schema_version=1, policy_id=NATIVE_POLICY_ID, status='REVIEW', automatic_adoption=False,
        scientific_approval='NOT_RUN', model_editing='NOT_RUN', optimization='NOT_RUN', dictionary_loading=[],
        inventory_detail='linked', atom_count=len(native['atoms']), fatal_problems=None, unused_definitions=[], unsupported_fields=[],
        phil_adaptations=[dict(input='inputs/original.phil')],
        restraint_policy=dict(secondary_structure_enabled=True, origin_ids={'hydrogen bonds':1, 'edits':2,
            'basepair stacking':3, 'basepair parallelity':4, 'basepair planarity':5}))
    native['geometry'].update(status='RECORDED',simple_bonds=[],asu_bonds=[], sites_cart_exact=[a['xyz'] for a in native['atoms']])
    folder=root/'capture'; folder.mkdir(); (folder/'inputs').mkdir()
    (folder/'inputs/model.pdb').write_bytes(original.read_bytes()); (folder/'inputs/original.phil').write_bytes(phil.read_bytes())
    save(folder/'native_spec.json',dict(policy_id=NATIVE_POLICY_ID, model='inputs/model.pdb', dictionaries=[],
        phil_files=['inputs/original.phil'], phil_namespace_policy='refinement-root-to-interpreter-v1',
        inventory_detail='linked', policy_inventory=True, installed_library_only=True))
    (folder/'native_worker.py').write_text(_NATIVE_WORKER)
    (folder/'native.log').write_text('Synthetic transport fixture; not actual Phenix evidence.\n')
    inputs=[dict(artifact(folder/'inputs'/n,folder), role=role,input_index=i)
        for i,(n,role) in enumerate([('model.pdb','model'),('original.phil','phil')])]
    receipt=dict(schema_version=1,audit_kind='cif_native_bundle_inspection',policy_id=NATIVE_POLICY_ID,
        status='REVIEW',source_preserved=True,frozen_inputs_preserved=True,symlink_outputs=[],automatic_adoption=False,
        scientific_approval='NOT_RUN',optimization='NOT_RUN',model_editing='NOT_RUN',readyset_retry='NOT_RUN',
        phenix_version='synthetic-test',execution=dict(status='COMPLETED',returncode=0),inputs=inputs,outputs=[],
        phil_namespace_policy='refinement-root-to-interpreter-v1',dictionary_source_policy='INSTALLED_LIBRARY_ONLY',native_validation=native)
    path=folder/'native_receipt.json';save(path,receipt);rebind(path)
    return original,path


def test_literal_compilation_can_replay_without_writing(tmp_path):
    from nasolve.cif_na_policy import _compile_na_policy_payload, compile_na_policy
    model,phil,native=policy_fixture(tmp_path)
    before=inventory(tmp_path)
    expected,files=_compile_na_policy_payload(model,[phil],native)
    assert inventory(tmp_path)==before
    assert compile_na_policy(model,[phil],native,tmp_path/'legacy')==expected
    assert {p.name:p.read_bytes() for p in (tmp_path/'legacy').iterdir()}==files


def test_literal_inputs_freeze_and_reconstruct_all_original_intent_read_only(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs,read_literal_na_inputs,resolve_literal_na_inputs
    model,receipt=capture(tmp_path/'source');before=inventory(tmp_path/'source')
    result=prepare_literal_na_inputs(model,receipt,tmp_path/'frozen')
    assert result['compilation']['pair_count']==1 and result['compilation']['stack_count']==1
    assert result['restraint_context']['request_counts']=={'angle':2,'bond':2,'parallelity':2}
    assert result['native_membership']=='NOT_ASSESSED_FOR_COMPILED_INPUTS'
    assert result['automatic_adoption'] is False and result['implementation']['restraints/data/Ligands.xlsx']
    assert inventory(tmp_path/'source')==before
    frozen=inventory(tmp_path/'frozen')
    with patch('subprocess.Popen',side_effect=AssertionError('Reading must not execute')):
        assert read_literal_na_inputs(tmp_path/'frozen')==result
        selected=resolve_literal_na_inputs(tmp_path/'frozen')
    assert selected['model'].read_bytes()==model.read_bytes()
    assert len(selected['phils'])==2 and inventory(tmp_path/'frozen')==frozen
    assert 'saenger_class = 20' in (tmp_path/'frozen/native/inputs/original.phil').read_text()
    assert 'enabled = False' in selected['phils'][-1].read_text()
    with pytest.raises(FileExistsError):prepare_literal_na_inputs(model,receipt,tmp_path/'frozen')


def test_literal_input_replay_survives_original_removal_and_relocation(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs,read_literal_na_inputs
    model,receipt=capture(tmp_path/'source');expected=prepare_literal_na_inputs(model,receipt,tmp_path/'original')
    shutil.copytree(tmp_path/'original',tmp_path/'moved');shutil.rmtree(tmp_path/'original');shutil.rmtree(tmp_path/'source')
    before=inventory(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay must not execute')):
        assert read_literal_na_inputs(tmp_path/'moved')==expected
    assert inventory(tmp_path/'moved')==before


@pytest.mark.parametrize('defect',['compiled','retained','model','native','worker','extra','empty_dir','manifest_extra',
    'pin','order','context','compilation','approval','duplicate_json','symlink'])
def test_literal_bundle_rejects_tampering_and_unrequested_members(tmp_path,defect):
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs,read_literal_na_inputs
    model,receipt=capture(tmp_path/'source');root=tmp_path/'frozen';r=prepare_literal_na_inputs(model,receipt,root)
    p=root/'literal_na_inputs.json'
    names={'compiled':'compiled/explicit_na_policy.phil','retained':'compiled/retained_000.phil','model':'model.pdb',
           'native':'native/native_validation.json','worker':'native/native_worker.py'}
    if defect in names:
        q=root/names[defect];q.write_bytes(q.read_bytes()+b'\n')
    elif defect=='extra':(root/'surprise').write_text('extra')
    elif defect=='empty_dir':(root/'empty').mkdir()
    elif defect=='manifest_extra':r['extra']='unrequested'
    elif defect=='pin':r['implementation']['restraints.builder']='0'*64
    elif defect=='order':r['compiled_phils'].reverse()
    elif defect=='context':r['restraint_context']['requests'][0]['weight']*=2
    elif defect=='compilation':r['compilation']['pair_count']+=1
    elif defect=='approval':r['automatic_adoption']=True
    elif defect=='symlink':
        q=root/'model.pdb';q.unlink();q.symlink_to(model)
    if defect=='duplicate_json':p.write_text('{"schema_version":1,'+p.read_text()[1:])
    elif defect not in names:save(p,r)
    with pytest.raises(ValueError):read_literal_na_inputs(root)


@pytest.mark.parametrize('defect',['failed','coordinates','input_order','missing_capture','extra_capture','modifier','unknown_setting','ungrouped_names'])
def test_literal_input_compilation_rejects_unbound_or_ambiguous_source(tmp_path,defect):
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs
    model,receipt=capture(tmp_path/'source')
    if defect=='failed':
        def change(r):r.update(status='FAILED',execution=dict(status='FAILED',returncode=1));r['native_validation']['status']='FAILED'
        rebind(receipt,change)
    elif defect=='coordinates':rebind(receipt,lambda r:r['native_validation']['atoms'][0]['xyz'].__setitem__(0,999.))
    elif defect=='input_order':
        r=json.loads(receipt.read_text());r['inputs'].reverse();save(receipt,r)
    elif defect=='missing_capture':(receipt.parent/'native.log').unlink()
    elif defect=='extra_capture':(receipt.parent/'extra').write_text('unrecorded')
    else:
        p=receipt.parent/'inputs/original.phil';text=p.read_text()
        if defect=='modifier':text+='refinement {\n pdb_interpretation {\n apply_cif_modification {\n data_mod = BAD\n residue_selection = chain Z and resid 1\n }\n }\n}\n'
        elif defect=='unknown_setting':text=text.replace('saenger_class = 20','saenger_class = 20\n unknown = True')
        else:text+='refinement {\n geometry_restraints.edits {\n parallelity {\n action = add\n atom_selection_1 = chain Z and resid 1 and name C4 or name C5 or name C6\n atom_selection_2 = chain Z and resid 3 and (name C4 or name C5 or name C6)\n target_angle_deg = 0\n sigma = 0.02\n }\n }\n}\n'
        p.write_text(text);r=json.loads(receipt.read_text());r['inputs'][1].update(artifact(p,receipt.parent));save(receipt,r);rebind(receipt)
    with pytest.raises((ValueError,FileNotFoundError)):prepare_literal_na_inputs(model,receipt,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()


from tests.test_cif_complete_request import case
from tests.test_cif_model_context import bind


def prepared_request(case, tmp_path):
    from nasolve.cif_model_context import derive_prepared_model_context
    m,args,root,sdk,store,generations,calls=case
    args=bind(args);folder=tmp_path/'canonical';folder.mkdir();model,_,_=policy_fixture(folder)
    combined=args['model'].read_text().replace('END\n','')+model.read_text()
    lines=[];i=0
    for line in combined.splitlines(keepends=True):
        if line[:6] in ('ATOM  ','HETATM'):
            i+=1;line=line[:6]+f'{i:5d}'+line[11:]
        lines.append(line)
    args['model'].write_text(''.join(lines))
    args['model_context']=derive_prepared_model_context(args['model'],args['model_context']['intent'],['YYY','ZZZ'])
    args["output"]=root
    return m,args,root


def bound_request(case, tmp_path):
    from nasolve.cif_native_context import FULL_MODEL_POLICY_ID
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs,resolve_literal_na_inputs
    m,args,root=prepared_request(case,tmp_path)
    original,receipt=capture(tmp_path/'literal-source',model=args['model'])
    # capture(model=...) deliberately preserves the legacy modifier for refusal
    # tests; remove it in this independently declared owner fixture.
    p=receipt.parent/'inputs/original.phil';text=p.read_text();a=text.index(' apply_cif_modification {');b=text.index(' }',a)
    p.write_text(text[:a]+text[b+3:]);r=json.loads(receipt.read_text());r['inputs'][1].update(artifact(p,receipt.parent));save(receipt,r);rebind(receipt)
    frozen=tmp_path/'literal';prepare_literal_na_inputs(original,receipt,frozen);resolved=resolve_literal_na_inputs(frozen)
    args.update(literal_na_inputs=frozen,supplementary_phils=resolved['phils'],restraint_context=resolved['report']['restraint_context'],
        native_context=dict(policy_id=FULL_MODEL_POLICY_ID,monomer_inventory='full_model',custom_restraints='required'))
    return m,args,root,receipt


def test_literal_provenance_is_frozen_with_existing_request_and_reads_cold(case,tmp_path):
    m,args,root,receipt=bound_request(case,tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('Initialize/read must not execute')):
        r=m.initialize_dictionary_request(**args)
        assert r['configuration']['literal_na_inputs']==dict(anchor=m.ANCHOR,path='inputs/literal_na',policy_id='cif-literal-na-inputs-v1')
        assert m.inspect_dictionary_request(root)['attempts']==[]
    moved=tmp_path/'moved-request';shutil.copytree(root,moved);shutil.rmtree(root)
    shutil.rmtree(args['literal_na_inputs']);shutil.rmtree(receipt.parent.parent);args['model'].unlink()
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read must not execute')):
        assert m.inspect_dictionary_request(moved)['attempts']==[]
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['model','order','bytes','context','missing_context'])
def test_owned_request_rejects_literal_provenance_disagreement(case,tmp_path,defect):
    m,args,root,_=bound_request(case,tmp_path)
    if defect=='model':args['model'].write_text(args['model'].read_text()+'REMARK other\n')
    elif defect=='order':args['supplementary_phils'].reverse()
    elif defect=='bytes':
        p=tmp_path/'other.phil';p.write_bytes(args['supplementary_phils'][0].read_bytes()+b'\n');args['supplementary_phils'][0]=p
    elif defect=='context':args['restraint_context']=deepcopy(args['restraint_context']);args['restraint_context']['requests'][0]['weight']*=2
    elif defect=='missing_context':args.pop('restraint_context')
    with pytest.raises(ValueError):m.initialize_dictionary_request(**args)
    assert not (root/'request.json').exists()


def test_postmr_entry_binds_original_order_before_selecting_compiled_inputs(case,tmp_path):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,root,receipt=bound_request(case,tmp_path)
    components=[{k:v for k,v in item.items() if k!='contexts'} for item in args['components']]
    kwargs=dict(model=args['model'],report=args['model_context']['intent'],components=components,source_output=tmp_path/'selected',
        output=root,consumer=args['consumer'],ready_set_executable=case[3].executables['phenix.ready_set'],data_root=tmp_path/'data',
        supplementary_phils=[receipt.parent/'inputs/original.phil'],literal_na_inputs=args['literal_na_inputs'])
    with patch('subprocess.Popen',side_effect=AssertionError('Entry must not execute')):
        result=initialize_postmr_dictionary_request(**kwargs)
    assert result['configuration']['restraint_context']==args['restraint_context']
    assert (root/'inputs/literal_na/native/inputs/original.phil').read_bytes()==kwargs['supplementary_phils'][0].read_bytes()
    other=tmp_path/'incorrect.phil';other.write_bytes(kwargs['supplementary_phils'][0].read_bytes()+b'\n')
    kwargs.update(source_output=tmp_path/'other-selection',output=tmp_path/'other-request',supplementary_phils=[other])
    with pytest.raises(ValueError,match='original'):initialize_postmr_dictionary_request(**kwargs)
    assert not kwargs['source_output'].exists() and not kwargs['output'].exists()



def test_literal_requests_execute_under_existing_owner_and_keep_prior_attempts(case,tmp_path):
    m,args,root,_=bound_request(case,tmp_path)
    m.initialize_dictionary_request(**args)
    frozen=inventory(root/'inputs/literal_na')
    first=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5])
    old=inventory(root/'attempts/attempt-0001')
    second=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5])
    assert first['attempt_id']!=second['attempt_id'] and second['attempt_number']==2
    exact=m.read_dictionary_request_result(root,1)
    assert exact['result']['literal_na_inputs']==dict(anchor=m.ANCHOR,path='inputs/literal_na',policy_id='cif-literal-na-inputs-v1')
    assert exact['literal_na_inputs']['report']['compilation']['pair_count']==1
    assert inventory(root/'inputs/literal_na')==frozen and inventory(root/'attempts/attempt-0001')==old
    assert all(row['state']=='STOPPED' for row in m.inspect_dictionary_request(root)['attempts'])


def test_postmr_literal_original_change_during_source_freeze_prevents_request(case,tmp_path,monkeypatch):
    import nasolve.cif_postmr_request as entry
    m,args,root,receipt=bound_request(case,tmp_path)
    original=receipt.parent/'inputs/original.phil';freeze=entry.freeze_acquisition_sources
    def changed(*a,**k):
        result=freeze(*a,**k);original.write_bytes(original.read_bytes()+b'# concurrent edit\n');return result
    monkeypatch.setattr(entry,'freeze_acquisition_sources',changed)
    with pytest.raises(ValueError,match='original'):
        entry.initialize_postmr_dictionary_request(model=args['model'],report=args['model_context']['intent'],
            components=[{k:v for k,v in item.items() if k!='contexts'} for item in args['components']],
            source_output=tmp_path/'selected',output=root,consumer=args['consumer'],ready_set_executable=case[3].executables['phenix.ready_set'],
            data_root=tmp_path/'data',supplementary_phils=[original],literal_na_inputs=args['literal_na_inputs'])
    assert (tmp_path/'selected').exists() and not root.exists()


def test_literal_native_indices_are_not_replaced_with_pdb_record_positions(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_literal_na_inputs
    model,receipt=capture(tmp_path/'source')
    def reorder(r):
        rows=r['native_validation']['atoms'];rows.reverse()
        for i,row in enumerate(rows):row['i_seq']=i
        r['native_validation']['geometry']['sites_cart_exact']=[row['xyz'] for row in rows]
    rebind(receipt,reorder)
    result=prepare_literal_na_inputs(model,receipt,tmp_path/'frozen')
    requests=result['compilation']['compiled_requests']
    assert all(a.startswith('native-') for row in requests for a in row['atoms'])
    assert all(a.startswith('pdb-record-') for row in result['restraint_context']['requests'] for a in row['atoms'])
    assert requests[0]['i_seqs']!=result['restraint_context']['requests'][0]['i_seqs']
