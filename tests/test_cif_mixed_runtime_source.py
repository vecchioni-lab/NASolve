"""Bounded capsule lineage and numerical replay precede ordinary activation."""
from copy import deepcopy
from hashlib import sha256
import json
import math
import subprocess

import pytest

from nasolve import cif_mixed_runtime_source as source
from tests.test_mixed_endpoint_replay_probe import capsule as c93_capsule
from tests.test_mixed_endpoint_window_probe import pack


def capsule(tmp_path):
    _, support, c93, members = c93_capsule(tmp_path)
    saved = {'schema_version': 1, 'policy_id': 'cif-saved-endpoint-portable-replay-v1',
        'status': 'SAVED_ENDPOINT_REPLAY_PASS', 'new_native_calls': 0, 'automatic_adoption': False,
        'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED',
        'scientific_parent_archive_sha256': support.SCIENCE_PARENT_SHA256}
    data = json.dumps(saved).encode()
    receipt = {'schema_version': 1, 'kind': 'mixed-endpoint-replay-probe', 'analysis_completed': True,
        'requires_cif_review': False, 'automatic_adoption': False, 'new_native_calls': 0,
        'model_optimization_requested': False, 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED',
        'captured_code_execution': 'NOT_RUN', 'parent_review_preserved': True, 'frozen_runtime_preserved': True,
        **{k: 'NOT_RUN' for k in ['dictionary_generation', 'cache_writes', 'coot_execution', 'readyset_execution', 'refinement']},
        'saved_endpoint_replay': {'directory': {'anchor': 'probe_directory', 'path': 'saved_replay'},
            'report_sha256': sha256(data).hexdigest(), 'report_size': len(data), 'status': saved['status'], 'new_native_calls': 0},
        'parent_review': {'artifact': {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
            'sha256': sha256(c93.read_bytes()).hexdigest(), 'size': c93.stat().st_size}, 'preserved': True, 'payload_count': len(members)}}
    rows = {'probe_receipt.json': json.dumps(receipt).encode(), 'inputs/parent_review.zip': c93.read_bytes(),
            'saved_replay/mixed_endpoint_saved_replay.json': data}
    return rows


def test_six_declared_views_are_taken_from_exact_nested_capsules_without_recursion(tmp_path):
    rows = capsule(tmp_path); raw = pack(rows)
    saved, views = source._lineage(source.archive_members(raw, sha256(raw).hexdigest()))
    assert [name for _, _, name in views] == ['window', 'torsion', 'geometry', 'gradient', 'context', 'linked_parent']
    assert saved['status'] == 'SAVED_ENDPOINT_REPLAY_PASS'
    assert all(not prefix.startswith('/') for _, prefix, _ in views)


@pytest.mark.parametrize('defect', ['checksum', 'inventory', 'duplicate', 'symlink', 'path', 'case_alias', 'bool_size', 'oversize'])
def test_bad_envelopes_are_refused_before_replay_or_staging(tmp_path, defect):
    rows = capsule(tmp_path); rows['captured.py'] = b'raise AssertionError("NEVER_EXECUTE")'
    if defect == 'path': rows['../outside'] = b'BAD'
    if defect == 'case_alias': rows['PROBE_RECEIPT.JSON'] = rows['probe_receipt.json']
    if defect == 'oversize': rows['large'] = b'X'*(33*1024*1024)
    raw = pack(rows, 'hash' if defect == 'checksum' else defect)
    if defect == 'bool_size':
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(raw)) as z: data = {n: z.read(n) for n in z.namelist()}
        manifest = json.loads(data['manifest.json']); manifest['captured.py']['bytes'] = True
        data['manifest.json'] = json.dumps(manifest).encode(); stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            for n, d in data.items(): z.writestr(n, d)
        raw = stream.getvalue()
    with pytest.raises(ValueError): source.archive_members(raw, sha256(raw).hexdigest())
    assert not (tmp_path/'outside').exists()


@pytest.mark.parametrize('field,value', [('new_native_calls', True), ('new_native_calls', 1),
    ('requires_cif_review', True), ('analysis_completed', False), ('captured_code_execution', 'EXECUTED'),
    ('model_optimization_requested', True), ('mtz_used', True), ('production_checkpoint', 'CREATED')])
def test_rebound_c94_claims_cannot_grant_ordinary_usability(tmp_path, field, value):
    rows = capsule(tmp_path); receipt = json.loads(rows['probe_receipt.json']);receipt[field] = value
    rows['probe_receipt.json'] = json.dumps(receipt).encode(); raw = pack(rows)
    with pytest.raises(ValueError): source._lineage(source.archive_members(raw, sha256(raw).hexdigest()))


def comparison():
    value = {'consistent': True, 'issue_count': 0, 'policy_id': 'cif-derived-cartesian-report-replay-v1',
        'changed_derived_values': 0, 'maximum_absolute_difference': 0., 'maximum_allowed_difference': 1e-12}
    return {'decision': 'qualified', 'descriptive_geometry_replay': {'full_precision': deepcopy(value), 'pdb_rounded': deepcopy(value)}}


def test_platform_local_roundoff_counts_do_not_change_an_exact_saved_decision():
    a = comparison(); b = deepcopy(a)
    b['descriptive_geometry_replay']['full_precision'].update(changed_derived_values=3, maximum_absolute_difference=1e-15)
    source._same_replay(a, b)
    assert a == comparison()


@pytest.mark.parametrize('defect', ['decision', 'bound', 'policy', 'count', 'negative', 'nan', 'inconsistent_count', 'failed'])
def test_roundoff_observations_cannot_change_recipes_decisions_or_pass_limits(defect):
    a = comparison(); b = deepcopy(a); row = b['descriptive_geometry_replay']['full_precision']
    if defect == 'decision': b['decision'] = 'fallback'
    elif defect == 'bound': row['maximum_allowed_difference'] *= 2
    elif defect == 'policy': row['policy_id'] = 'OTHER'
    elif defect == 'count': row['changed_derived_values'] = True
    elif defect == 'negative': row['maximum_absolute_difference'] = -1.
    elif defect == 'nan': row['maximum_absolute_difference'] = math.nan
    elif defect == 'inconsistent_count': row['changed_derived_values'] = 1
    elif defect == 'failed': row['consistent'] = False
    with pytest.raises(ValueError): source._same_replay(a, b)


def test_real_maintained_replay_is_required_before_resources_are_yielded(tmp_path, monkeypatch):
    from tests.test_cif_mixed_endpoint import coherent_torsion_parent, C92_PARENT_SHA256
    from nasolve.cif_mixed_endpoint_window import qualify_saved_mixed_endpoint
    from nasolve.cif_mixed_endpoint_replay import replay_saved_endpoint_window
    *parents, _, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    window = tmp_path/'window'
    qualify_saved_mixed_endpoint(*parents, phenix, window, parent_archive_sha256=C92_PARENT_SHA256, timeout_seconds=30)
    saved = replay_saved_endpoint_window(window, torsion_directory=parents[0], geometry_directory=parents[1],
        gradient_directory=parents[2], context_directory=parents[3], linked_parent_directory=parents[4], parent_archive_sha256=C92_PARENT_SHA256)
    names = ['window', 'torsion', 'geometry', 'gradient', 'context', 'linked_parent']
    views = []
    for name, folder in zip(names, [window, *parents]):
        views.append(({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}, '', name))
    # The transport envelope and complete scientific replay have independent tests.
    monkeypatch.setattr(source, '_lineage', lambda members: (saved, views))
    raw = pack({'probe_receipt.json': b'{}'}); path = tmp_path/'data.zip'; path.write_bytes(raw)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Saved source reader launched process'))
    with source.verified_endpoint_source(path, sha256(raw).hexdigest()) as verified:
        assert verified['replay']['coordinate_decision']['endpoint_usable'] is True
        assert verified['resources'][0][2] == (window/'candidate/saved_mixed_endpoint.pdb').read_bytes()
        assert verified['resources'][0][0] == 'model'
