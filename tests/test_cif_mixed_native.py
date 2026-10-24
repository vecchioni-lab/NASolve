"""Artificial transport contracts; no Coot/Phenix or chemical qualification."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from nasolve.cif_mixed_native import (audit_mixed_native, read_mixed_native,
    qualify_mixed_native, select_native_dictionaries, _chemistry_pass)


def fixture(tmp_path, monkeypatch):
    """Mock the already-tested fixture reader, leaving byte references real."""
    from tests.test_cif_postmr_construction import dictionary
    from nasolve.cif_mixed_pair_fixture import _artifact
    root = tmp_path / 'artificial_fixture'; root.mkdir()
    model = root / 'model.pdb'
    model.write_text("HETATM    1   C1 PDU A   1       1.000   2.000   3.000  1.00 20.00           C\nEND\n")
    source = root / 'PDU.cif'; dictionary(source, 'PDU')
    phil = root / 'explicit_policy'; phil.mkdir()
    active = phil / 'explicit_na_policy.phil'
    active.write_text('refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n}\n')
    data = active.read_bytes()
    policy = {'pair_count': 20, 'stack_count': 38, 'compiled_phil': {'path': 'explicit_na_policy.phil', 'sha256': sha256(data).hexdigest(), 'size': len(data)}}
    report = {'status': 'MIXED_PAIR_CONSTRUCTION_PASS', 'policy_compilation': policy,
        'plan': {'target_site_components': {'A:1': 'PDU'}, 'stack_edges': []},
        'outputs': {'model': _artifact(model, root)},
        'source_bindings': {'PDU': {'authority': 'ARTIFICIAL_SOURCE', 'source': _artifact(source, root)}}}
    monkeypatch.setattr('nasolve.cif_mixed_pair_fixture.read_mixed_pair_fixture', lambda p: deepcopy(report))
    monkeypatch.setattr('nasolve.cif_explicit_na_policy.read_explicit_na_policy', lambda p: deepcopy(policy))
    return root, report


def test_inspect_only_is_source_removed_portable_and_starts_no_process(tmp_path, monkeypatch):
    root, parent = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('inspect-only started a process'))
    output = tmp_path / 'prepared'
    report = audit_mixed_native(root, None, output)
    assert report['status'] == 'PREPARED_ONLY'
    assert report['new_readyset_calls'] == report['new_native_calls'] == 0
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    shutil.rmtree(root); moved = tmp_path / 'relocated'; output.rename(moved)
    assert read_mixed_native(moved) == report


@pytest.mark.parametrize('defect', ['status', 'source', 'extra', 'source_escape', 'symlink', 'native_without_effective'])
def test_reader_rejects_forged_success_or_modified_frozen_inputs(tmp_path, monkeypatch, defect):
    root, _ = fixture(tmp_path, monkeypatch); output = tmp_path / 'prepared'
    report = audit_mixed_native(root, None, output)
    if defect == 'status':
        report['status'] = 'MIXED_NATIVE_MEMBERSHIP_PASS'
        (output / 'mixed_native.json').write_text(json.dumps(report))
    elif defect == 'native_without_effective':
        report.update(status='REVIEW', new_native_calls=1)
        (output / 'mixed_native.json').write_text(json.dumps(report))
    elif defect == 'source': (output / 'inputs/PDU.cif').write_text('CHANGED')
    elif defect == 'extra': (output / 'unexpected.txt').write_text('EXTRA')
    elif defect == 'source_escape':
        report['inputs']['sources']['PDU']['path'] = '../outside.cif'
        (output / 'mixed_native.json').write_text(json.dumps(report))
    else:
        path = output / 'inputs/PDU.cif'; path.unlink(); path.symlink_to(root / 'PDU.cif')
    with pytest.raises(ValueError): read_mixed_native(output)


@pytest.mark.parametrize('timeout', [0, 601, True, 1.5])
def test_invalid_deadline_stops_before_fixture_or_output(tmp_path, timeout):
    output = tmp_path / 'absent'
    with pytest.raises(ValueError): audit_mixed_native(tmp_path / 'absent_fixture', None, output, timeout_seconds=timeout)
    assert not output.exists()


def test_failed_ordinary_readyset_keeps_evidence_and_starts_no_native(tmp_path, monkeypatch):
    from nasolve.postmr import PostMRPreparationError
    root, _ = fixture(tmp_path, monkeypatch)
    executable = tmp_path / 'phenix.ready_set'; executable.write_text('ARTIFICIAL_DISPATCHER')
    phenix = SimpleNamespace(executables={'phenix.ready_set': executable}, environment={}, version='ARTIFICIAL')
    calls = []
    def failed(model, ready, run, cifs, environment, **kwargs):
        calls.append((model, ready, tuple(cifs), kwargs))
        (run / 'ready_set.log').write_text('ARTIFICIAL_READYSET_FAILURE')
        raise PostMRPreparationError('ARTIFICIAL_READYSET_FAILURE')
    monkeypatch.setattr('nasolve.postmr._run_readyset', failed)
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle', lambda *a, **k: pytest.fail('Native called after failed ReadySet'))
    report = audit_mixed_native(root, phenix, tmp_path / 'result', timeout_seconds=43)
    assert report['status'] == 'REVIEW' and report['error'] == 'ARTIFICIAL_READYSET_FAILURE'
    assert len(calls) == 1 and isinstance(calls[0][2], tuple) and len(calls[0][2]) == 1
    assert calls[0][2][0].name == 'PDU.cif'
    assert report['new_native_calls'] == 0 and report['source_inputs_preserved']
    assert report['deadlines'] == {'readyset_seconds': 43, 'each_native_seconds': 43, 'maximum_native_calls': 2}
    assert read_mixed_native(tmp_path / 'result') == report


def test_bounded_dispatcher_retains_timeout_log_and_owned_group(tmp_path, monkeypatch):
    root, _ = fixture(tmp_path, monkeypatch)
    executable = tmp_path / 'phenix.ready_set'; executable.write_text('ARTIFICIAL_DISPATCHER')
    phenix = SimpleNamespace(executables={'phenix.ready_set': executable}, environment={}, version='ARTIFICIAL')
    events = []
    class Process:
        returncode = -9
        def __init__(self, command, **kwargs):
            events.append(kwargs)
            kwargs['stdout'].write(b'ARTIFICIAL_TIMED_OUT_OUTPUT')
        def wait(self, timeout):
            import subprocess
            assert timeout == 7
            raise subprocess.TimeoutExpired('ARTIFICIAL', timeout)
    monkeypatch.setattr('subprocess.Popen', Process)
    monkeypatch.setattr('nasolve.cif_generation._terminate_owned_group', lambda p: events.append('terminated'))
    report = audit_mixed_native(root, phenix, tmp_path / 'result', timeout_seconds=7)
    assert report['status'] == 'REVIEW' and report['new_readyset_calls'] == 1 and report['new_native_calls'] == 0
    assert report['readyset']['execution']['status'] == 'TIMED_OUT'
    assert events[-1] == 'terminated' and events[0]['start_new_session'] is True
    assert (tmp_path / 'result/readyset/dispatcher.log').read_text() == 'ARTIFICIAL_TIMED_OUT_OUTPUT'
    assert (tmp_path / 'result/readyset/ready_set.log').read_text() == 'ARTIFICIAL_TIMED_OUT_OUTPUT'


def test_canonical_ccd_graphs_do_not_override_installed_numerical_monomers(tmp_path, monkeypatch):
    from tests.test_cif_postmr_construction import dictionary
    from nasolve.ligand_profiles import _parameterized_codes
    source = tmp_path / 'DA.cif'; dictionary(source, 'DA')
    raw = source.read_text().replace('_chem_comp_atom.type_energy', '_chem_comp_atom.unused_type')
    source.write_text(raw)
    assert not _parameterized_codes(source)
    modified = tmp_path / 'PDU.cif'; dictionary(modified, 'PDU')
    selected, canonical = select_native_dictionaries([source, modified], {'DA': source, 'PDU': modified})
    assert selected == [modified] and canonical == ['DA']
    changed = tmp_path / 'changed.cif'; changed.write_bytes(source.read_bytes() + b'\n# changed\n')
    with pytest.raises(ValueError, match='exact frozen source'):
        select_native_dictionaries([changed], {'DA': source})


def test_chemical_changes_cannot_be_promoted_by_native_membership():
    assert _chemistry_pass({'DA': {'status': 'INSTALLED_CANONICAL_NUMERICS_PENDING_NATIVE_READBACK', 'source_graph_retained': True}, 'PDU': {'status': 'CANDIDATE_REVIEW'}})
    for wrong in [{'status': 'REJECTED'}, {'status': 'REVIEW'}, {'status': 'INSTALLED_CANONICAL_NUMERICS_PENDING_NATIVE_READBACK', 'source_graph_retained': False}]:
        assert not _chemistry_pass({'PDU': {'status': 'CANDIDATE_REVIEW'}, '5PC': wrong})


def test_active_requests_are_resolved_against_reordered_native_indices(tmp_path, monkeypatch):
    from tests.test_cif_na_policy import fixture as native_fixture
    from nasolve.cif_na_policy import compile_na_policy, _requests
    model, ph, native = native_fixture(tmp_path)
    compiled = compile_na_policy(model, [ph], native, tmp_path / 'compiled')
    active = tmp_path / 'compiled' / compiled['compiled_phil']
    original = _requests(active.read_text(), native['atoms'])
    atoms = list(reversed(native['atoms']))
    for index, atom in enumerate(atoms): atom['i_seq'] = index
    expected = _requests(active.read_text(), atoms)
    assert expected[0]['i_seqs'] != original[0]['i_seqs']
    seen = []
    def membership(before, after, policy):
        seen.append(policy['compiled_requests'])
        return {'mechanics_checks_pass': True}
    monkeypatch.setattr('nasolve.cif_na_policy.qualify_na_policy', membership)
    monkeypatch.setattr('nasolve.cif_fragment_restoration._model', lambda *a, **k: {})
    native['atoms'] = atoms
    qualify_mixed_native(native, native, model, active,
        {'all_pairs': [{}, {}], 'stack_edges': [['Z:1', 'Z:2']], 'target_site_components': {}}, {})
    assert seen == [expected]


@pytest.mark.parametrize('missing', ['effective_dictionaries', 'native_dictionary_selection', 'chemical_comparisons'])
def test_native_summary_cannot_skip_effective_chemical_replay(tmp_path, monkeypatch, missing):
    root, _ = fixture(tmp_path, monkeypatch); output = tmp_path / 'prepared'
    report = audit_mixed_native(root, None, output)
    report.update(status='MIXED_NATIVE_MEMBERSHIP_PASS', new_readyset_calls=1, new_native_calls=2,
        source_chemistry_comparisons_pass=True, qualification={'mechanics_checks_pass': True},
        effective_dictionaries=[report['inputs']['sources']['PDU']],
        native_dictionary_selection={'dictionaries': [report['inputs']['sources']['PDU']]},
        chemical_comparisons={'PDU': {'status': 'REJECTED'}})
    report['readyset'].update(execution={'status': 'COMPLETED'}, unchanged_named_heavy_coordinates=True)
    del report[missing]
    (output / 'mixed_native.json').write_text(json.dumps(report))
    with pytest.raises(ValueError, match='Incomplete mixed native effective source evidence'):
        read_mixed_native(output)
