"""Existing source-bound compiler evidence joins the existing request owner.

Synthetic role graphs/repair transport exercise ownership, not native chemistry.
No prior native capture, alternate relationship selection or new compiler is used.
"""
from copy import deepcopy
import json
import shutil
from unittest.mock import patch

import pytest

from tests.test_cif_complete_request import case
from tests.test_cif_literal_na_inputs import prepared_request
from tests.test_cif_explicit_na_policy import fixture as explicit_fixture
from tests.test_cif_repair_attempt import inventory


def declared(case,tmp_path):
    from nasolve.cif_explicit_na_policy import compile_explicit_na_policy
    from nasolve.cif_restraint_context import derive_restraint_context
    from nasolve.cif_native_context import FULL_MODEL_POLICY_ID
    m,args,root=prepared_request(case,tmp_path)
    graph_root=tmp_path/'role-graphs';graph_root.mkdir()
    _,_,_,sources,_=explicit_fixture(graph_root)
    pairs=[dict(sites=['Z:1','Z:2'],components=['DA','DT'],scope='requested')]
    compiled=tmp_path/'compiled'
    with patch('subprocess.Popen',side_effect=AssertionError('Compiler must not require native capture')):
        report=compile_explicit_na_policy(args['model'],pairs,[('Z:2','Z:3')],
            {code:sources[code] for code in ['DA','DT']},compiled,orientation_controls=deepcopy(pairs))
    inputs=[compiled/report['compiled_phil']['path']]
    args.update(explicit_na_policy=compiled,supplementary_phils=inputs,
        restraint_context=derive_restraint_context(args['model'],inputs),
        native_context=dict(policy_id=FULL_MODEL_POLICY_ID,monomer_inventory='full_model',custom_restraints='required'))
    return m,args,root


def test_explicit_compiler_artifact_freezes_without_native_or_relationship_guess(case,tmp_path):
    from nasolve.cif_explicit_na_policy import POLICY_ID
    m,args,root=declared(case,tmp_path);before=inventory(args['explicit_na_policy'])
    with patch('subprocess.Popen',side_effect=AssertionError('Initialize/read must not execute')):
        request=m.initialize_dictionary_request(**args)
        assert m.inspect_dictionary_request(root)['attempts']==[]
    assert request['configuration']['explicit_na_policy']==dict(anchor=m.ANCHOR,path='inputs/explicit_na',policy_id=POLICY_ID)
    assert 'literal_na_inputs' not in request['configuration']
    assert inventory(args['explicit_na_policy'])==before
    assert (root/'inputs/explicit_na/orientation_controls/000_0.phil').is_file()
    assert request['configuration']['controls']['supplementary_phils']==['phils/000.phil']


def test_explicit_compiler_executes_and_recovers_with_one_preserved_outer_artifact(case,tmp_path):
    m,args,root=declared(case,tmp_path);m.initialize_dictionary_request(**args)
    proof=inventory(root/'inputs/explicit_na')
    first=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5]);old=inventory(root/'attempts/attempt-0001')
    second=m.execute_dictionary_request_attempt(root,case[3],case[4],generation=case[5])
    assert second['attempt_number']==2 and second['attempt_id']!=first['attempt_id']
    exact=m.read_dictionary_request_result(root,1)
    assert exact['result']['explicit_na_policy']['path']=='inputs/explicit_na'
    assert exact['explicit_na_policy']['report']['orientation_control_count']==2
    assert inventory(root/'inputs/explicit_na')==proof and inventory(root/'attempts/attempt-0001')==old
    assert not (root/'attempts/attempt-0001/preparation/inputs/explicit_na').exists()
    moved=tmp_path/'moved';shutil.copytree(root,moved);shutil.rmtree(root)
    shutil.rmtree(args['explicit_na_policy']);shutil.rmtree(args['source_selection']);shutil.rmtree(case[3].root)
    args['model'].unlink();before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(moved,1)['result']==first['result']
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['model','compiled_bytes','extra_phil','orientation_control','context','missing_context','compiler_pin','both_modes'])
def test_explicit_compiler_disagreement_never_publishes_request(case,tmp_path,defect):
    m,args,root=declared(case,tmp_path)
    if defect=='model':args['model'].write_text(args['model'].read_text()+'REMARK other\n')
    elif defect=='compiled_bytes':
        p=tmp_path/'other.phil';p.write_bytes(args['supplementary_phils'][0].read_bytes()+b'\n');args['supplementary_phils']=[p]
    elif defect=='extra_phil':
        p=tmp_path/'extra.phil';p.write_text('# another input\n');args['supplementary_phils'].append(p)
    elif defect=='orientation_control':args['supplementary_phils']=[args['explicit_na_policy']/'orientation_controls/000_0.phil']
    elif defect=='context':args['restraint_context']['requests'][0]['weight']*=2
    elif defect=='missing_context':args.pop('restraint_context')
    elif defect=='compiler_pin':
        p=args['explicit_na_policy']/'explicit_na_policy.json';r=json.loads(p.read_bytes());r['implementation_sha256']['restraints.builder']='0'*64;p.write_text(json.dumps(r))
    elif defect=='both_modes':args['literal_na_inputs']=tmp_path/'not-needed'
    with pytest.raises(ValueError):m.initialize_dictionary_request(**args)
    assert not (root/'request.json').exists()


def test_explicit_compiler_source_bytes_match_selected_acquisition_source(case,tmp_path):
    m,args,root=declared(case,tmp_path);artifact=args['explicit_na_policy']
    original=artifact/'inputs/sources/DA.cif';same=tmp_path/'selected-DA.cif';same.write_bytes(original.read_bytes())
    source={'DA':dict(source=same)}
    assert m._compiler_input('explicit_na_policy',artifact,source)['model'].read_bytes()==args['model'].read_bytes()
    same.write_bytes(same.read_bytes()+b'# same graph but another frozen source\n')
    with pytest.raises(ValueError,match='source'):m._compiler_input('explicit_na_policy',artifact,source)


def test_postmr_entry_accepts_existing_compiler_and_never_reselects_pairs(case,tmp_path,monkeypatch):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    import restraints.guesser as guesser
    m,args,root=declared(case,tmp_path)
    monkeypatch.setattr(guesser,'guess_pairs',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Do not re-guess frozen intent')))
    kwargs=dict(model=args['model'],report=args['model_context']['intent'],
        components=[{k:v for k,v in item.items() if k!='contexts'} for item in args['components']],source_output=tmp_path/'selected',
        output=root,consumer=args['consumer'],ready_set_executable=case[3].executables['phenix.ready_set'],data_root=tmp_path/'data',
        supplementary_phils=args['supplementary_phils'],explicit_na_policy=args['explicit_na_policy'])
    with patch('subprocess.Popen',side_effect=AssertionError('Entry must not execute')):
        result=initialize_postmr_dictionary_request(**kwargs)
    assert result['configuration']['restraint_context']==args['restraint_context']
    assert m.inspect_dictionary_request(root)['attempts']==[]
    kwargs.update(source_output=tmp_path/'other-selected',output=tmp_path/'other-request',supplementary_phils=[])
    with pytest.raises(ValueError):initialize_postmr_dictionary_request(**kwargs)
    assert not kwargs['source_output'].exists() and not kwargs['output'].exists()
