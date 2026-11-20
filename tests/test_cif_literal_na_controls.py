"""Typed control evidence is replayable but cannot enter ordinary execution."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,shutil
from unittest.mock import patch
import pytest
from tests.test_cif_literal_na_inputs import capture
from tests.test_cif_attachment_native import artifact,rebind,save
from tests.test_cif_repair_attempt import inventory

CONTROLS=('pdb_interpretation.sort_atoms','pdb_interpretation.restraints_library.cdl',
          'pdb_interpretation.restraints_library.cdl_nucleotides.enable','pdb_interpretation.use_ncs_to_build_restraints')
TEXT='\n'.join(p+' = False' for p in CONTROLS)+'\n'


def setup(tmp_path,text=TEXT):
    model,receipt=capture(tmp_path/'source');folder=receipt.parent;p=folder/'inputs/controls.phil';p.write_text(text)
    r=json.loads(receipt.read_text());r['inputs'].append(dict(artifact(p,folder),input_index=2,role='phil'))
    spec=json.loads((folder/'native_spec.json').read_text());spec['phil_files'].append('inputs/controls.phil');save(folder/'native_spec.json',spec)
    r['native_validation']['phil_adaptations'].append(dict(input='inputs/controls.phil',policy='refinement-root-to-interpreter-v1',definitions_preserved=4,
        field_mapping=[dict(source=k,interpreter=k,value_tokens=['False']) for k in CONTROLS]))
    save(receipt,r);rebind(receipt)
    rows=json.loads(receipt.read_text())['inputs']
    roles=[dict(input_index=row['input_index'],role='literal_restraints' if i==0 else 'interpretation_controls',sha256=row['sha256']) for i,row in enumerate(rows[1:])]
    return model,receipt,roles


def prepare(case,output,**kwargs):
    from nasolve.cif_literal_na_controls import prepare_typed_literal_na_inputs
    model,receipt,roles=case
    return prepare_typed_literal_na_inputs(model,receipt,output,phil_roles=roles,
        expected_receipt_sha256=sha256(receipt.read_bytes()).hexdigest(),**kwargs)


def test_typed_artifact_binds_roles_controls_and_refuses_execution(tmp_path):
    from nasolve.cif_literal_na_inputs import read_literal_na_inputs,resolve_literal_na_inputs
    from nasolve.cif_literal_na_controls import inspect_typed_literal_na_inputs
    from nasolve.cif_complete_request import _compiler_input
    case=setup(tmp_path);before=inventory(tmp_path/'source');out=tmp_path/'typed';report=prepare(case,out)
    assert report['phil_roles']==case[2]
    assert report['execution_context']['ordinary_handoff_allowed'] is False
    assert len(report['captured_controls'])==1 and report['captured_controls'][0]['values']==dict.fromkeys(CONTROLS,False)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read must not execute')):
        assert read_literal_na_inputs(out)==report
        observed=inspect_typed_literal_na_inputs(out)
        assert 'phils' not in observed and len(observed['compiled_restraint_phils'])==2
        assert observed['interpretation_control_phils'][0].read_text()==TEXT
        with pytest.raises(ValueError,match='ordinary'):resolve_literal_na_inputs(out)
        with pytest.raises(ValueError,match='ordinary'):_compiler_input('literal_na_inputs',out)
    assert inventory(tmp_path/'source')==before


@pytest.mark.parametrize('text',[TEXT+'geometry_restraints.edits {\n}\n',TEXT+'unknown = False\n',
    TEXT+CONTROLS[0]+' = False\n',TEXT.replace('sort_atoms = False','sort_atoms = True'),
    TEXT.replace('False','Auto',1),TEXT+'include file = elsewhere.phil\n',TEXT+'pdb_interpretation.unknown {\n}\n',
    TEXT.replace('sort_atoms = False','sort_atoms = "False"'),'',TEXT.replace('False','False; evil = False',1)])
def test_control_roles_reject_edits_unknowns_repeats_and_nonliteral_values(tmp_path,text):
    case=setup(tmp_path,text)
    with pytest.raises(ValueError):prepare(case,tmp_path/'no')
    assert not (tmp_path/'no').exists()


@pytest.mark.parametrize('change',['swap_roles','order','digest','missing','repeat','unknown_role','extra_field','wrong_index'])
def test_ordered_role_substitution_refuses_before_publication(tmp_path,change):
    model,rp,roles=setup(tmp_path)
    if change=='swap_roles':roles[0]['role'],roles[1]['role']=roles[1]['role'],roles[0]['role']
    elif change=='order':roles.reverse()
    elif change=='digest':roles[1]['sha256']='0'*64
    elif change=='missing':roles.pop()
    elif change=='repeat':roles.append(deepcopy(roles[-1]))
    elif change=='unknown_role':roles[1]['role']='ignore'
    elif change=='extra_field':roles[1]['extra']=False
    else:roles[1]['input_index']=1
    with pytest.raises(ValueError):prepare((model,rp,roles),tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_receipt_pin_prevents_rebound_capture(tmp_path):
    from nasolve.cif_literal_na_controls import prepare_typed_literal_na_inputs
    model,rp,roles=setup(tmp_path)
    with pytest.raises(ValueError,match='receipt'):
        prepare_typed_literal_na_inputs(model,rp,tmp_path/'no',phil_roles=roles,expected_receipt_sha256='0'*64)


@pytest.mark.parametrize('change',['tokens','target','omitted','count'])
def test_native_definition_readback_must_match_controls(tmp_path,change):
    model,rp,roles=setup(tmp_path)
    def mutate(r):
        a=r['native_validation']['phil_adaptations'][1]
        if change=='tokens':a['field_mapping'][0]['value_tokens']=['True']
        elif change=='target':a['field_mapping'][0]['interpreter']='other'
        elif change=='count':a['definitions_preserved']=3
        else:a['field_mapping'].pop()
    rebind(rp,mutate)
    with pytest.raises(ValueError):prepare((model,rp,roles),tmp_path/'no')


def test_relocation_without_original_inputs_and_tamper_detection(tmp_path):
    from nasolve.cif_literal_na_inputs import read_literal_na_inputs
    case=setup(tmp_path);out=tmp_path/'old';report=prepare(case,out)
    moved=out.rename(tmp_path/'relocated');shutil.rmtree(tmp_path/'source')
    assert not out.exists() and read_literal_na_inputs(moved)==report
    p=moved/'native/inputs/controls.phil';p.write_bytes(p.read_bytes()+b'# changed\n')
    with pytest.raises(ValueError):read_literal_na_inputs(moved)


def test_bounded_existing_parser_handles_scope_and_flat_spellings(tmp_path):
    text='refinement {\n pdb_interpretation {\n sort_atoms = False\n restraints_library.cdl = False\n restraints_library.cdl_nucleotides.enable = False\n use_ncs_to_build_restraints = False\n }\n}\n'
    model,rp,roles=setup(tmp_path,text)
    def mutate(r):
        for row in r['native_validation']['phil_adaptations'][1]['field_mapping']:row['source']='refinement.'+row['source']
    rebind(rp,mutate)
    assert len(prepare((model,rp,roles),tmp_path/'typed')['captured_controls'][0]['values'])==4


def test_rehashed_manifest_cannot_drop_control_roles_or_handoff_hold(tmp_path):
    from nasolve.cif_literal_na_inputs import read_literal_na_inputs
    case=setup(tmp_path);root=tmp_path/'typed';report=prepare(case,root)
    report['execution_context']['ordinary_handoff_allowed']=True
    save(root/'literal_na_inputs.json',report)
    with pytest.raises(ValueError):read_literal_na_inputs(root)


@pytest.mark.parametrize('repeated',[False,True])
def test_multiple_control_inputs_preserve_order_and_reject_cross_file_repeats(tmp_path,repeated):
    model,rp,roles=setup(tmp_path);folder=rp.parent
    first=folder/'inputs/controls.phil';first.write_text(CONTROLS[0]+' = False\n')
    second=folder/'inputs/second.phil'
    second.write_text('\n'.join(k+' = False' for k in CONTROLS[0 if repeated else 1:])+'\n')
    r=json.loads(rp.read_text());r['inputs'][2].update(artifact(first,folder))
    r['inputs'].append(dict(artifact(second,folder),input_index=3,role='phil'))
    adaptation=r['native_validation']['phil_adaptations'][1];other=deepcopy(adaptation)
    adaptation['field_mapping']=adaptation['field_mapping'][:1];adaptation['definitions_preserved']=1
    other['input']='inputs/second.phil';other['field_mapping']=other['field_mapping'][0 if repeated else 1:]
    other['definitions_preserved']=len(other['field_mapping']);r['native_validation']['phil_adaptations'].append(other)
    spec=json.loads((folder/'native_spec.json').read_text());spec['phil_files'].append('inputs/second.phil')
    save(folder/'native_spec.json',spec);save(rp,r);rebind(rp)
    roles[1]['sha256']=sha256(first.read_bytes()).hexdigest()
    roles.append(dict(input_index=3,role='interpretation_controls',sha256=sha256(second.read_bytes()).hexdigest()))
    if repeated:
        with pytest.raises(ValueError,match='Repeated'):prepare((model,rp,roles),tmp_path/'typed')
    else:
        report=prepare((model,rp,roles),tmp_path/'typed')
        assert [r['input_index'] for r in report['captured_controls']]==[2,3]


def test_control_namespace_must_match_capture(tmp_path):
    case=setup(tmp_path)
    def mutate(r):r['native_validation']['phil_adaptations'][1]['policy']='direct'
    rebind(case[1],mutate)
    with pytest.raises(ValueError,match='namespace'):prepare(case,tmp_path/'typed')
