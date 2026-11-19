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


def source_literal_case(tmp_path):
    """Toy role graphs exercise identity/transport, not source chemistry."""
    model,phil,native=policy_fixture(tmp_path)
    text=phil.read_text();a=text.index(' apply_cif_modification {');b=text.index(' }',a)
    text=text[:a]+text[b+3:]
    text+='refinement {\n geometry_restraints.edits {\n planarity {\n action = add\n atom_selection = (chain Z and resid 1 and (name C4 or name C5 or name C6)) or (chain Z and resid 3 and (name C4 or name C5 or name C6))\n sigma = 0.025\n }\n }\n}\n'
    phil.write_text(text)
    by_code={}
    for line in model.read_text().splitlines():
        if line.startswith('ATOM'):
            by_code.setdefault(line[17:20].strip(),{})[line[12:16].strip()]=line[76:78].strip()
    sources={}
    for code,atoms in by_code.items():
        path=tmp_path/(code+'.cif');names=list(atoms)
        path.write_text(f'data_{code}\n_chem_comp.id {code}\nloop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
            +''.join(f'{code} {name} {element}\n' for name,element in atoms.items())
            +'loop_\n_chem_comp_bond.comp_id\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
            +''.join(f'{code} {a} {b} SING\n' for a,b in zip(names,names[1:])))
        sources[code]=path
    return model,phil,native,sources


def test_source_literal_compilation_preserves_exact_declared_bytes_without_capture(tmp_path,monkeypatch):
    from nasolve import cif_literal_na_inputs as literal
    from nasolve.cif_na_policy import _compile_na_policy_payload
    model,phil,native,sources=source_literal_case(tmp_path)
    _,expected=_compile_na_policy_payload(model,[phil],native)
    before=inventory(tmp_path)
    def forbidden(*a,**k):raise AssertionError('Source-bound compilation must not acquire or fabricate a native capture')
    monkeypatch.setattr(literal,'_capture',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):
        result=literal.prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'frozen')
    assert result['policy_id']=='cif-source-literal-na-inputs-v1'
    assert result['index_basis']=='PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES'
    assert result['native_membership']=='NOT_ASSESSED_FOR_COMPILED_INPUTS'
    assert result['compilation']['pair_count']==result['compilation']['stack_count']==1
    assert result['restraint_context']['request_counts']=={'angle':2,'bond':2,'parallelity':2,'planarity':1}
    assert 'native_receipt' not in result and not (tmp_path/'frozen/native').exists()
    assert {n:(tmp_path/'frozen/compiled'/n).read_bytes() for n in expected}==expected
    assert all(inventory(tmp_path)[n]==v for n,v in before.items())
    selected=literal.resolve_literal_na_inputs(tmp_path/'frozen')
    assert selected['report']==result and len(selected['phils'])==2


def test_source_literal_mode_does_not_claim_numeric_source_qualification(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs
    model,phil,native,sources=source_literal_case(tmp_path)
    p=sources['DA'];p.write_text(p.read_text()+'loop_\n_chem_comp_angle.comp_id\n_chem_comp_angle.atom_id_1\n_chem_comp_angle.atom_id_2\n_chem_comp_angle.atom_id_3\n_chem_comp_angle.value_angle\nDA N1 C2 N3 INVALID_NUMERICAL_TARGET\n')
    result=prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'frozen')
    assert result['scientific_approval']=='NOT_RUN' and result['automatic_adoption'] is False
    assert result['native_membership']=='NOT_ASSESSED_FOR_COMPILED_INPUTS'
    assert (tmp_path/'frozen/sources/DA.cif').read_bytes()==p.read_bytes()


def test_source_literal_mode_replays_after_originals_disappear(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs,read_literal_na_inputs
    source=tmp_path/'source';source.mkdir();model,phil,native,sources=source_literal_case(source)
    result=prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'frozen')
    moved=(tmp_path/'frozen').rename(tmp_path/'moved with spaces');shutil.rmtree(source)
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read cannot execute')):
        assert read_literal_na_inputs(moved)==result
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['missing_source','extra_source','element','role','modifier','recipe','scope'])
def test_source_literal_mode_refuses_unbound_roles_and_intent_before_writing(tmp_path,defect):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs
    model,phil,native,sources=source_literal_case(tmp_path)
    if defect=='missing_source':sources.pop('DT')
    elif defect=='extra_source':sources['ZZZ']=sources['DT']
    elif defect=='element':sources['DA'].write_text(sources['DA'].read_text().replace('DA N6 N','DA N6 O'))
    elif defect=='role':sources['DA'].write_text(sources['DA'].read_text().replace('N6','XX'))
    elif defect=='modifier':phil.write_text(phil.read_text()+'refinement {\n pdb_interpretation.apply_cif_modification {\n data_mod = BAD\n residue_selection = chain Z and resid 1\n }\n}\n')
    elif defect=='recipe':phil.write_text(phil.read_text().replace('saenger_class = 20','saenger_class = 19'))
    else:phil.write_text(phil.read_text().replace('(name C4 or name C5 or name C6)','name C4 or name C5 or name C6'))
    with pytest.raises(ValueError):prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()


@pytest.mark.parametrize('defect',['original','source','model','compiled','basis','role','native_claim','extra'])
def test_source_literal_mode_rejects_changed_or_relabelled_evidence(tmp_path,defect):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs,read_literal_na_inputs
    model,phil,native,sources=source_literal_case(tmp_path);root=tmp_path/'frozen'
    result=prepare_source_literal_na_inputs(model,[phil],sources,root)
    path=root/'literal_na_inputs.json'
    files={'original':'original/000.phil','source':'sources/DA.cif','model':'model.pdb','compiled':'compiled/explicit_na_policy.phil'}
    if defect in files:
        p=root/files[defect];p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='extra':(root/'native_capture.json').write_text('{}\n')
    else:
        if defect=='basis':result['index_basis']='NATIVE'
        elif defect=='role':result['compilation']['site_roles']['Z:1']['base_class']='T'
        else:result['native_membership']='PASS'
        save(path,result)
    with pytest.raises(ValueError):read_literal_na_inputs(root)


def source_literal_request(case,tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs,resolve_literal_na_inputs
    from nasolve.cif_native_context import FULL_MODEL_POLICY_ID
    m,args,root=prepared_request(case,tmp_path)
    folder=tmp_path/'source-literal';folder.mkdir()
    model,phil,native,sources=source_literal_case(folder);model.write_bytes(args['model'].read_bytes())
    output=tmp_path/'source-literal-artifact';prepare_source_literal_na_inputs(model,[phil],sources,output)
    selected=resolve_literal_na_inputs(output)
    args.update(literal_na_inputs=output,supplementary_phils=selected['phils'],restraint_context=selected['report']['restraint_context'],
        native_context=dict(policy_id=FULL_MODEL_POLICY_ID,monomer_inventory='full_model',custom_restraints='required'))
    return m,args,root,phil,sources


def test_source_literal_existing_entry_freezes_original_intent_and_policy(case,tmp_path):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,root,phil,sources=source_literal_request(case,tmp_path)
    components=[{k:v for k,v in row.items() if k!='contexts'} for row in args['components']]
    with patch('subprocess.Popen',side_effect=AssertionError('Initializer cannot execute')):
        result=initialize_postmr_dictionary_request(args['model'],args['model_context']['intent'],components,
            tmp_path/'selected',root,consumer=args['consumer'],ready_set_executable=case[3].executables['phenix.ready_set'],
            supplementary_phils=[phil],data_root=tmp_path/'data',literal_na_inputs=args['literal_na_inputs'])
    assert result['configuration']['literal_na_inputs']['policy_id']=='cif-source-literal-na-inputs-v1'
    assert (root/'inputs/literal_na/original/000.phil').read_bytes()==phil.read_bytes()
    assert m.inspect_dictionary_request(root)['attempts']==[]


def test_source_literal_and_construction_evidence_share_existing_recovery_owner(case,tmp_path):
    from nasolve.postmr_lineage import begin_postmr_construction,finish_postmr_construction
    m,args,root,phil,sources=source_literal_request(case,tmp_path)
    run=tmp_path/'ordinary';models=run/'PostMR/Model';models.mkdir(parents=True)
    for name in ('mr_solution.pdb','after_coot.pdb','prepared_model.pdb'):
        (models/name).write_bytes(args['model'].read_bytes())
    start=begin_postmr_construction(run,models/'mr_solution.pdb',models/'mr_solution.pdb',{},[],
        allow_op3_sites=args['model_context']['intent']['post_mr_plan']['allow_op3_sites'])
    finish_postmr_construction(run,start,models/'prepared_model.pdb',dict(model=models/'after_coot.pdb',raw_model=None,coot_log=None))
    args['construction_inputs']=run
    m.initialize_dictionary_request(**args)
    first=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5]);old=inventory(root/'attempts/attempt-0001')
    second=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5])
    assert first['attempt_id']!=second['attempt_id'] and inventory(root/'attempts/attempt-0001')==old
    assert second['result']['literal_na_inputs']['policy_id']=='cif-source-literal-na-inputs-v1'
    assert second['result']['construction_inputs']['policy_id']=='postmr-construction-lineage-v1'
    assert not (root/'attempts/attempt-0001/preparation/inputs/literal_na').exists()
    moved=root.rename(tmp_path/'relocated source request');shutil.rmtree(args['literal_na_inputs']);shutil.rmtree(run)
    shutil.rmtree(phil.parent);args['model'].unlink();before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read cannot execute')):
        result=m.read_dictionary_request_result(moved,2)
        assert all(a['state']=='STOPPED' for a in m.inspect_dictionary_request(moved)['attempts'])
    assert result['literal_na_inputs']['report']['index_basis'].startswith('PDB_RECORD_ORDER')
    assert result['construction_inputs']['model'].is_file() and inventory(moved)==before


def test_source_literal_compiler_source_join_rejects_selected_byte_disagreement(tmp_path):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs
    from nasolve.cif_complete_request import _compiler_input
    model,phil,native,sources=source_literal_case(tmp_path);root=tmp_path/'frozen'
    prepare_source_literal_na_inputs(model,[phil],sources,root)
    _compiler_input('literal_na_inputs',root,{'DA':{'source':sources['DA']}})
    sources['DA'].write_bytes(sources['DA'].read_bytes()+b'\n')
    with pytest.raises(ValueError,match='source differs'):
        _compiler_input('literal_na_inputs',root,{'DA':{'source':sources['DA']}})


def test_source_literal_input_change_during_freezing_preserves_partial_evidence(tmp_path,monkeypatch):
    from nasolve import cif_literal_na_inputs as literal
    model,phil,native,sources=source_literal_case(tmp_path);write=literal._write_payload
    def changed(*a,**k):
        write(*a,**k);sources['DA'].write_bytes(sources['DA'].read_bytes()+b'\n')
    monkeypatch.setattr(literal,'_write_payload',changed)
    with pytest.raises(ValueError,match='changed while freezing'):
        literal.prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'partial')
    assert (tmp_path/'partial/sources/DA.cif').is_file()


def test_source_literal_coordinate_changes_cannot_reselect_relationships(tmp_path,monkeypatch):
    from nasolve.cif_literal_na_inputs import prepare_source_literal_na_inputs
    from restraints import guesser
    def forbidden(*a,**k):raise AssertionError('Frozen literal relationships cannot be guessed again')
    monkeypatch.setattr(guesser,'guess_pairs',forbidden)
    model,phil,native,sources=source_literal_case(tmp_path)
    first=prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'first')
    model.write_text(''.join(line[:30]+f'{float(line[30:38])+200.:8.3f}'+line[38:] if line.startswith('ATOM') else line
        for line in model.read_text().splitlines(keepends=True)))
    second=prepare_source_literal_na_inputs(model,[phil],sources,tmp_path/'second')
    assert first['compilation']['relationships']==second['compilation']['relationships']
    assert (tmp_path/'first/compiled/explicit_na_policy.phil').read_bytes()==(tmp_path/'second/compiled/explicit_na_policy.phil').read_bytes()
    assert first['model']['sha256']!=second['model']['sha256']
