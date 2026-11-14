"""C94 preserves one exact C93 parent and replays only declared data views."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import base64
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests.test_mixed_endpoint_window_probe import capsule as c92_capsule, pack

ROOT = Path(__file__).parents[1]


def module():
    spec = importlib.util.spec_from_file_location('endpoint_replay_ferry', ROOT/'scripts/mixed_endpoint_replay_probe_template.py')
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def capsule(tmp_path, defect='none'):
    support, c92, prior, _ = c92_capsule(tmp_path, 'hash' if defect == 'nested' else 'none')
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-saved-endpoint-resolution-window-v1',
        'status': 'MIXED_ENDPOINT_QUALIFIED', 'new_native_calls': 2, 'parent_archive_sha256': support.SCIENCE_PARENT_SHA256,
        'automatic_adoption': False, 'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED'}
    mutations = {'schema_bool': ('schema_version', True), 'policy': ('policy_id', 'OTHER'),
        'status': ('status', 'REVIEW'), 'calls_bool': ('new_native_calls', True), 'calls': ('new_native_calls', 1),
        'parent': ('parent_archive_sha256', '0'*64), 'adoption': ('automatic_adoption', True),
        'approval': ('requires_cif_review', True), 'science': ('scientific_qualification', 'APPROVED')}
    if defect in mutations:report[mutations[defect][0]] = mutations[defect][1]
    data = json.dumps(report).encode()
    receipt = {'schema_version': 1, 'kind': 'mixed-endpoint-window-probe', 'delivery_prefix': '93_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'parent_review_preserved': True, 'frozen_runtime_preserved': True, 'model_optimization_requested': False,
        'captured_code_execution': 'NOT_RUN', 'mixed_endpoint_window': {'directory': {'anchor': 'probe_directory', 'path': 'mixed_endpoint_window'},
            'report_sha256': sha256(data).hexdigest(), 'report_size': len(data), 'status': 'MIXED_ENDPOINT_QUALIFIED', 'new_native_calls': 2},
        'parent_review': {'artifact': {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
            'sha256': sha256(c92.read_bytes()).hexdigest(), 'size': c92.stat().st_size}, 'preserved': True, 'payload_count': len(prior)}}
    # c92_capsule returns payloads without the ZIP manifest.
    if defect == 'header_bool':receipt['schema_version'] = True
    elif defect == 'header_kind':receipt['kind'] = 'OTHER'
    elif defect == 'header_prefix':receipt['delivery_prefix'] = '92_Cedar'
    elif defect == 'incomplete':receipt['analysis_completed'] = False
    elif defect == 'header_count_bool':receipt['mixed_endpoint_window']['new_native_calls'] = True
    elif defect == 'report_hash':receipt['mixed_endpoint_window']['report_sha256'] = '0'*64
    elif defect == 'parent_count_bool':receipt['parent_review']['payload_count'] = True
    elif defect == 'parent_count':receipt['parent_review']['payload_count'] += 1
    elif defect == 'parent_ref':receipt['parent_review']['artifact']['size'] += 1
    elif defect == 'optimizer':receipt['model_optimization_requested'] = True
    members = {'probe_receipt.json': json.dumps(receipt).encode(), 'inputs/parent_review.zip': c92.read_bytes(),
        'mixed_endpoint_window/mixed_endpoint_window_qualification.json': data,
        'mixed_endpoint_window/job/captured.py': b'raise RuntimeError("CAPTURED_C93_PYTHON_MUST_NOT_EXECUTE")\n',
        'unrelated/model.pdb': b'DECOY'}
    if defect == 'path':members['../outside'] = b'BAD'
    if defect == 'oversize':members['large.bin'] = b'X'*(33*1024*1024)
    path = tmp_path/'c93.zip';path.write_bytes(pack(members, defect))
    ferry = module();ferry.REVIEW_SHA256 = sha256(path.read_bytes()).hexdigest()
    return ferry, support, path, members


def test_exact_c93_and_bounded_nested_ancestry_are_preserved_as_data(tmp_path):
    ferry, support, path, members = capsule(tmp_path)
    actual, prior = ferry._read_capsule(path, support)
    assert all(actual[n] == d for n, d in members.items())
    views = support._materialize_inputs(prior, tmp_path/'views')
    assert len(views) == 6 and not any(p.suffix == '.zip' for p in (tmp_path/'views').rglob('*'))
    destination = tmp_path/'window';ferry._stage_window(actual, destination)
    assert (destination/'job/captured.py').read_bytes() == members['mixed_endpoint_window/job/captured.py']
    assert not (destination/'unrelated').exists()
    with pytest.raises(FileExistsError):ferry._stage_window(actual, destination)


@pytest.mark.parametrize('defect', ['schema_bool', 'policy', 'status', 'calls_bool', 'calls', 'parent', 'adoption',
    'approval', 'science', 'header_bool', 'header_kind', 'header_prefix', 'incomplete', 'header_count_bool',
    'report_hash', 'parent_count_bool', 'parent_count', 'parent_ref', 'optimizer', 'nested',
    'path', 'oversize', 'hash', 'inventory', 'duplicate', 'symlink'])
def test_rebound_parent_defects_are_refused_before_any_scientific_replay(tmp_path, defect):
    ferry, support, path, _ = capsule(tmp_path, defect)
    before = path.read_bytes()
    with pytest.raises((ValueError, KeyError)):ferry._read_capsule(path, support)
    assert path.read_bytes() == before and not (tmp_path/'outside').exists()


def test_outer_c93_checksum_is_required(tmp_path):
    ferry, support, path, _ = capsule(tmp_path);ferry.REVIEW_SHA256 = '0'*64
    with pytest.raises(ValueError):ferry._read_capsule(path, support)


@pytest.mark.parametrize('reject', [False, True])
def test_main_is_saved_only_and_preserves_parent_once_on_success_or_reader_rejection(tmp_path, monkeypatch, capsys, reject):
    import nasolve, restraints, subprocess
    from nasolve import cif_mixed_endpoint_replay as maintained
    ferry, support, path, _ = capsule(tmp_path)
    ferry.BUNDLE = {'delivery_prefix': '94_Cedar'}
    runtime = {'src/nasolve/__init__.py': b'', 'restraints/__init__.py': b''}
    monkeypatch.setattr(ferry, '_runtime_members', lambda: runtime)
    def isolate(root, session, members):
        for n, d in members.items():ferry._write(root/n, d)
        monkeypatch.setattr(nasolve, '__file__', str(root/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints, '__file__', str(root/'restraints/__init__.py'))
    monkeypatch.setattr(ferry, '_isolate', isolate)
    monkeypatch.setattr(ferry, '_support', lambda runtime: support)
    def replay(root, **kwargs):
        assert root.name == 'window' and kwargs['torsion_directory'].name == 'torsion'
        assert kwargs['parent_archive_sha256'] == support.SCIENCE_PARENT_SHA256
        assert (root/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')
        if reject:raise ValueError('EXPLICIT_READER_REJECTION')
        return {'status': 'SAVED_ENDPOINT_REPLAY_PASS', 'new_native_calls': 0,
            'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'qualified_geometry_endpoint'}}
    monkeypatch.setattr(maintained, 'replay_saved_endpoint_window', replay)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Saved-only ferry launched process'))
    monkeypatch.setattr('sys.argv', ['replay', '--review-zip', str(path), '--output-parent', str(tmp_path/'output')])
    assert ferry.main() == 2
    archives = list((tmp_path/'output').glob('*/*_review.zip'));assert len(archives) == 1
    with ZipFile(archives[0]) as z:
        assert z.read('inputs/parent_review.zip') == path.read_bytes()
        assert not any('parents/' in n or n.startswith('runtime/') for n in z.namelist())
        receipt = json.loads(z.read('probe_receipt.json'))
        assert receipt['analysis_completed'] is not reject and receipt['new_native_calls'] == 0
        if reject:assert receipt['error'] == 'EXPLICIT_READER_REJECTION'
        else:assert receipt['saved_endpoint_replay']['status'] == 'SAVED_ENDPOINT_REPLAY_PASS'
    assert 'REVIEW ZIP:' in capsys.readouterr().out


@pytest.mark.parametrize('flag', ['--phenix-root', '--max-iterations', '--timeout-seconds'])
def test_no_native_or_optimizer_flags_are_exposed(tmp_path, monkeypatch, flag):
    ferry = module()
    monkeypatch.setattr(ferry, '_runtime_members', lambda: pytest.fail('Invalid CLI unpacked runtime'))
    monkeypatch.setattr('sys.argv', ['replay', '--review-zip', str(tmp_path/'absent.zip'), flag, '1'])
    with pytest.raises(SystemExit) as stopped:ferry.main()
    assert stopped.value.code == 2


@pytest.mark.parametrize('defect', ['none', 'missing_support', 'size_bool', 'changed_support'])
def test_only_checksummed_current_build_support_can_be_imported(defect):
    ferry = module()
    members = {'src/nasolve/__init__.py': b'', ferry.SUPPORT_PATH: b'# CURRENT_BUILD_SUPPORT\n'}
    refs = {n: {'size': len(d), 'sha256': sha256(d).hexdigest()} for n, d in members.items()}
    if defect == 'missing_support':del members[ferry.SUPPORT_PATH];del refs[ferry.SUPPORT_PATH]
    elif defect == 'size_bool':refs['src/nasolve/__init__.py']['size'] = False
    elif defect == 'changed_support':members[ferry.SUPPORT_PATH] += b'# TAMPER\n'
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as z:
        for n, d in members.items():z.writestr(n, d)
    ferry.RUNTIME_BASE64 = base64.b64encode(raw.getvalue()).decode()
    ferry.BUNDLE = {'runtime_archive_sha256': sha256(raw.getvalue()).hexdigest(), 'runtime_files': refs}
    if defect == 'none':assert ferry._runtime_members() == members
    else:
        with pytest.raises(ValueError):ferry._runtime_members()
