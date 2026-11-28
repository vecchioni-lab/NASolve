"""Separate reader settings reach the existing owner; synthetic inputs are not chemistry proof."""
from pathlib import Path
from unittest.mock import patch
import json
import shutil

import pytest

from tests.test_cif_dictionary_bundle import fixture
from tests.test_cif_literal_na_controls import setup, prepare, TEXT

from tests.test_cif_complete_request import case
from tests.test_cif_literal_na_inputs import bound_request
from tests.test_cif_attachment_native import artifact, rebind, save
from tests.test_cif_literal_na_controls import CONTROLS
from tests.test_cif_repair_attempt import inventory
from hashlib import sha256


POLICY = 'cif-captured-reader-control-handoff-v1'


def test_opted_compiler_intake_retains_separate_controls(tmp_path):
    from nasolve.cif_complete_request import _compiler_input
    case = setup(tmp_path)
    root = tmp_path/'typed'
    report = prepare(case, root)
    with pytest.raises(ValueError, match='ordinary'):
        _compiler_input('literal_na_inputs', root)
    result = _compiler_input('literal_na_inputs', root, reader_control_policy=POLICY)
    assert result['report'] == report
    assert [p.read_text() for p in result['interpretation_control_phils']] == [TEXT]
    assert all(p not in result['phils'] for p in result['interpretation_control_phils'])
    assert report['execution_context']['ordinary_handoff_allowed'] is False


def test_bundle_carries_controls_once_and_relocates(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle
    args = fixture(tmp_path)
    controls = tmp_path/'controls.phil'
    controls.write_text(TEXT)
    out = tmp_path/'bundle'
    report = prepare_dictionary_bundle(output=out, **args,
        interpretation_control_phils=[controls], reader_control_policy=POLICY)
    assert report['interpretation_controls'] == dict(policy_id=POLICY, phils=['inputs/reader_controls/000.phil'])
    assert not (out/'prepared/native_interpretation.phil').exists()
    selected = read_dictionary_bundle(out)
    assert [p.read_text() for p in selected['before_phils']] == [TEXT]
    assert sum('use_ncs_to_build_restraints' in p.read_text() for p in selected['after_phils']) == 1
    moved = out.rename(tmp_path/'relocated')
    controls.unlink(); args['model'].unlink()
    shutil.rmtree(tmp_path/'first'); shutil.rmtree(tmp_path/'second')
    with patch('subprocess.Popen', side_effect=AssertionError('No launch during replay')):
        assert read_dictionary_bundle(moved)['report'] == report


def typed_request(case, tmp_path, *, split=False):
    """Extend the existing synthetic owned-request fixture with captured roles."""
    from nasolve.cif_literal_na_controls import inspect_typed_literal_na_inputs
    m, args, root, receipt = bound_request(case, tmp_path)
    folder = receipt.parent
    r = json.loads(receipt.read_text())
    spec = json.loads((folder/'native_spec.json').read_text())
    roles = [dict(input_index=1, role='literal_restraints', sha256=r['inputs'][1]['sha256'])]
    groups = [CONTROLS[:1], CONTROLS[1:]] if split else [CONTROLS]
    for i, keys in enumerate(groups, 2):
        p = folder/f'inputs/controls-{i}.phil'
        p.write_text('\n'.join(k+' = False' for k in keys)+'\n')
        relative = p.relative_to(folder).as_posix()
        r['inputs'].append(dict(artifact(p, folder), input_index=i, role='phil'))
        spec['phil_files'].append(relative)
        r['native_validation']['phil_adaptations'].append(dict(input=relative,
            policy='refinement-root-to-interpreter-v1', definitions_preserved=len(keys),
            field_mapping=[dict(source=k, interpreter=k, value_tokens=['False']) for k in keys]))
        roles.append(dict(input_index=i, role='interpretation_controls', sha256=sha256(p.read_bytes()).hexdigest()))
    save(folder/'native_spec.json', spec); save(receipt, r); rebind(receipt)
    typed = tmp_path/'typed'
    prepare((args['model'], receipt, roles), typed)
    inspected = inspect_typed_literal_na_inputs(typed)
    args.update(literal_na_inputs=typed, supplementary_phils=inspected['compiled_restraint_phils'],
        reader_control_policy=POLICY, restraint_context=inspected['report']['restraint_context'])
    return m, args, root, receipt


def test_complete_owner_carries_controls_through_preparation_and_cold_result(case, tmp_path):
    m, args, root, receipt = typed_request(case, tmp_path, split=True)
    request = m.initialize_dictionary_request(**args)
    role = request['configuration']['controls']['interpretation_controls']
    assert role == dict(policy_id=POLICY, phils=['reader_controls/000.phil', 'reader_controls/001.phil'])
    original = inventory(root/'inputs')
    first = m.execute_dictionary_request_attempt(root, case[3], case[4], generation=case[5])
    old_attempt = inventory(root/'attempts/attempt-0001')
    second = m.execute_dictionary_request_attempt(root, case[3], case[4], generation=case[5])
    assert first['attempt_id'] != second['attempt_id']
    assert inventory(root/'inputs') == original and inventory(root/'attempts/attempt-0001') == old_attempt
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle
    for n in (1, 2):
        saved = read_dictionary_bundle(root/f'attempts/attempt-{n:04d}/preparation/bundle')
        assert saved['report']['interpretation_controls']['policy_id'] == POLICY
        expected = [p.read_bytes() for p in args['supplementary_phils']]
        expected += [(root/'inputs'/p).read_bytes() for p in role['phils']]
        assert [p.read_bytes() for p in saved['before_phils']] == expected
        assert not (root/f'attempts/attempt-{n:04d}/preparation/bundle/prepared/native_interpretation.phil').exists()
    moved = root.rename(tmp_path/'relocated request')
    shutil.rmtree(args['literal_na_inputs']); shutil.rmtree(receipt.parent.parent)
    shutil.rmtree(args['source_selection']); args['model'].unlink()
    with patch('subprocess.Popen', side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(moved, 2)['result'] == second['result']


def test_postmr_accepts_only_explicit_typed_handoff(case, tmp_path):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, root, receipt = typed_request(case, tmp_path)
    r = json.loads(receipt.read_text())
    kwargs = dict(model=args['model'], report=args['model_context']['intent'],
        components=[{k:v for k,v in item.items() if k != 'contexts'} for item in args['components']],
        source_output=tmp_path/'selected', output=root, consumer=args['consumer'],
        ready_set_executable=case[3].executables['phenix.ready_set'], data_root=tmp_path/'data',
        supplementary_phils=[receipt.parent/row['path'] for row in r['inputs'] if row['role']=='phil'],
        literal_na_inputs=args['literal_na_inputs'])
    with pytest.raises(ValueError, match='ordinary'):
        initialize_postmr_dictionary_request(**kwargs)
    assert not root.exists() and not kwargs['source_output'].exists()
    with patch('subprocess.Popen', side_effect=AssertionError('Intake must not execute')):
        result = initialize_postmr_dictionary_request(**kwargs, reader_control_policy=POLICY)
    controls = result['configuration']['controls']
    assert controls['interpretation_controls']['policy_id'] == POLICY
    assert controls['supplementary_phils'] == ['phils/000.phil', 'phils/001.phil']
    assert result['configuration']['restraint_context'] == args['restraint_context']


@pytest.mark.parametrize('defect', ['missing', 'changed', 'reverse_names', 'swap_bytes', 'drop_role', 'unknown_policy'])
def test_changed_frozen_controls_refuse_before_new_attempt(case, tmp_path, defect):
    from nasolve.campaign_records import write_record
    m, args, root, receipt = typed_request(case, tmp_path, split=True)
    request = m.initialize_dictionary_request(**args)
    role = request['configuration']['controls']['interpretation_controls']
    paths = [root/'inputs'/n for n in role['phils']]
    if defect == 'missing': paths[0].unlink()
    elif defect == 'changed': paths[0].write_bytes(paths[0].read_bytes()+b'# changed\n')
    elif defect == 'swap_bytes':
        a,b = [p.read_bytes() for p in paths]; paths[0].write_bytes(b); paths[1].write_bytes(a)
    else:
        if defect == 'reverse_names': role['phils'].reverse()
        elif defect == 'drop_role': del request['configuration']['controls']['interpretation_controls']
        else: role['policy_id'] = 'unknown'
        write_record(root/'request.json', {k:v for k,v in request.items() if k != 'record_sha256'}, replace=True)
    with patch('subprocess.Popen', side_effect=AssertionError('Changed input must not launch')):
        with pytest.raises((ValueError, FileNotFoundError)):
            m.execute_dictionary_request_attempt(root, case[3], case[4], generation=case[5])
    assert not (root/'attempts').exists() and not case[6]


@pytest.mark.parametrize('extra', ['True', 'False'])
def test_control_conflict_in_geometry_role_refuses_before_preparation(tmp_path, extra):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle
    args = fixture(tmp_path)
    control = tmp_path/'control.phil'; control.write_text(TEXT)
    other = tmp_path/'other.phil'; other.write_text('refinement.pdb_interpretation.use_ncs_to_build_restraints = '+extra+'\n')
    with patch('subprocess.Popen', side_effect=AssertionError('Conflict must not launch')):
        with pytest.raises(ValueError, match='Conflicting interpretation control'):
            prepare_dictionary_bundle(output=tmp_path/'no', **args, supplementary_phils=[other],
                interpretation_control_phils=[control], reader_control_policy=POLICY)
    assert not (tmp_path/'no').exists()


@pytest.mark.parametrize('defect', ['true', 'unknown', 'duplicate', 'missing_policy', 'unknown_policy', 'empty'])
def test_bad_control_role_refuses_before_preparation(tmp_path, defect):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle
    args = fixture(tmp_path)
    p = tmp_path/'control.phil'; p.write_text(TEXT)
    paths = [p]; policy = POLICY
    if defect == 'true': p.write_text(TEXT.replace('False', 'True', 1))
    elif defect == 'unknown': p.write_text(TEXT+'unknown = False\n')
    elif defect == 'duplicate': paths.append(p)
    elif defect == 'missing_policy': policy = None
    elif defect == 'unknown_policy': policy = 'unknown'
    else: paths = []
    with pytest.raises(ValueError):
        prepare_dictionary_bundle(output=tmp_path/'no', **args,
            interpretation_control_phils=paths, reader_control_policy=policy)
    assert not (tmp_path/'no').exists()


def test_missing_captured_ncs_keeps_one_generated_definition(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle
    args = fixture(tmp_path)
    p = tmp_path/'control.phil'; p.write_text(CONTROLS[0]+' = False\n')
    out = tmp_path/'bundle'
    prepare_dictionary_bundle(output=out, **args, interpretation_control_phils=[p], reader_control_policy=POLICY)
    b = read_dictionary_bundle(out)
    assert len(b['before_phils']) == 2
    assert b['before_phils'][-1] == out/'prepared/native_interpretation.phil'
    assert sum('use_ncs_to_build_restraints' in p.read_text() for p in b['after_phils']) == 1


def test_added_generated_ncs_conflict_cannot_be_rehashed_into_a_bundle(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle, _files
    args = fixture(tmp_path)
    p = tmp_path/'control.phil'; p.write_text(TEXT)
    out = tmp_path/'bundle'
    prepare_dictionary_bundle(output=out, **args, interpretation_control_phils=[p], reader_control_policy=POLICY)
    (out/'prepared/native_interpretation.phil').write_text('pdb_interpretation.use_ncs_to_build_restraints = True\n')
    receipt = out/'bundle_receipt.json'; record = json.loads(receipt.read_text())
    record['files'] = _files(out); receipt.write_text(json.dumps(record))
    with patch('subprocess.Popen', side_effect=AssertionError('Conflicting generated policy must not launch')):
        with pytest.raises(ValueError, match='Unrequested bundle artifact'):
            read_dictionary_bundle(out)


def test_prepared_controls_are_frozen_in_existing_native_dispatch(tmp_path):
    import sys
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle
    from nasolve.cif_native_validation import inspect_native_bundle
    args = fixture(tmp_path)
    p = tmp_path/'control.phil'; p.write_text(TEXT)
    out = tmp_path/'bundle'
    prepare_dictionary_bundle(output=out, **args, interpretation_control_phils=[p], reader_control_policy=POLICY)
    b = read_dictionary_bundle(out); calls = []
    def dispatch(command, *, cwd, log_path, environment, timeout_seconds):
        spec = json.loads((cwd/'native_spec.json').read_text())
        expected = b[calls[-1]+'_phils']
        assert [(cwd/n).read_bytes() for n in spec['phil_files']] == [p.read_bytes() for p in expected]
        assert spec['phil_namespace_policy'] == 'refinement-root-to-interpreter-v1'
        assert spec['full_monomer_inventory'] is True
        assert sum('use_ncs_to_build_restraints' in (cwd/n).read_text() for n in spec['phil_files']) == 1
        return 97  # Stop at the dispatch boundary; this is not native qualification.
    for phase in ('before', 'after'):
        calls.append(phase)
        with patch('subprocess.Popen', side_effect=AssertionError('Synthetic dispatch cannot launch')):
            r = inspect_native_bundle(b['model'], b[phase+'_dictionaries'], tmp_path/phase, Path(sys.executable),
                environment={}, phenix_version='SYNTHETIC_TRANSPORT_ONLY', phil_files=b[phase+'_phils'],
                phil_namespace_policy='refinement-root-to-interpreter-v1', inventory_detail='linked',
                full_monomer_inventory=True, _process_runner=dispatch)
        assert r['execution']['returncode'] == 97 and r['native_validation'] is None
    assert calls == ['before', 'after']


@pytest.mark.parametrize('repaired', [False, True])
def test_selected_runtime_and_readyset_preserve_reader_control_role(tmp_path, monkeypatch, repaired):
    from tests import test_cif_dictionary_bundle_readyset as preparation
    from tests.test_cif_runtime_readyset import parent_case
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    from nasolve.cif_runtime_readyset import audit_runtime_readyset_consumption, runtime_readyset_endpoint_inputs
    prepare_bundle = preparation.prepare_dictionary_bundle
    p = tmp_path/'control.phil'; p.write_text(TEXT)
    def with_controls(*a, **k):
        return prepare_bundle(*a, **k, interpretation_control_phils=[p], reader_control_policy=POLICY)
    monkeypatch.setattr(preparation, 'prepare_dictionary_bundle', with_controls)
    parent, sdk = parent_case(tmp_path, monkeypatch, repaired=repaired)
    selected = resolve_runtime_bundle(parent)
    expected = [p.read_bytes() for p in selected['phils']]
    assert expected.count(TEXT.encode()) == 1
    audit_runtime_readyset_consumption(parent, sdk, tmp_path/'endpoint')
    endpoint = runtime_readyset_endpoint_inputs(parent, tmp_path/'endpoint')
    assert [p.read_bytes() for p in endpoint['phils']] == expected
    assert sum('use_ncs_to_build_restraints' in p.read_text() for p in endpoint['phils']) == 1
    moved = parent.rename(tmp_path/'relocated runtime')
    p.unlink(); shutil.rmtree(tmp_path/'bundle')
    with patch('subprocess.Popen', side_effect=AssertionError('Cold runtime must not execute')):
        assert [p.read_bytes() for p in resolve_runtime_bundle(moved)['phils']] == expected


@pytest.mark.parametrize('policy', [POLICY, 'unknown'])
def test_control_policy_without_typed_provenance_refuses_before_freezing(case, policy):
    m, args, root, *_ = case
    with pytest.raises(ValueError, match='typed literal provenance'):
        m.initialize_dictionary_request(output=root, **args, reader_control_policy=policy)
    assert not root.exists()
