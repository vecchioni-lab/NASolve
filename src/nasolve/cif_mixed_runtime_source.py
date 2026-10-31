"""Read the declared mixed-endpoint capsule lineage as data, in shallow views.

Only maintained Python is imported. Historical paths and captured programs in
the preserved ZIPs are provenance, never discovery or execution instructions.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import io
import math
from pathlib import Path
import stat
import tempfile
import zipfile

from .cif_review_transport import _parse_json, _strict, _unique, is_safe_review_member

POLICY_ID = 'cif-mixed-endpoint-capsule-source-v1'
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024


def _need(value, message='Incomplete or changed mixed endpoint capsule'):
    if not value:
        raise ValueError(message)


def archive_members(data, digest):
    """Verify bounded entries, CRCs and the exact manifest before staging."""
    _need(isinstance(digest, str) and len(digest) == 64
          and len(data) <= MAX_ARCHIVE_BYTES and sha256(data).hexdigest() == digest)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        _need(len(entries) <= 1024 and len(entries) == len({e.filename for e in entries})
              and sum(e.file_size for e in entries) <= MAX_EXPANDED_BYTES
              and all(is_safe_review_member(e.filename) and not e.is_dir() and not e.flag_bits & 1
                      and stat.S_IFMT(e.external_attr >> 16) in {0, stat.S_IFREG}
                      and e.file_size <= MAX_ARCHIVE_BYTES for e in entries))
        _unique(e.filename for e in entries)
        members = {e.filename: archive.read(e) for e in entries}
    inventory = _parse_json(members['manifest.json'])
    _need(isinstance(inventory, dict) and set(inventory) == set(members)-{'manifest.json'})
    for name, ref in inventory.items():
        _need(isinstance(ref, dict) and type(ref.get('bytes')) is int
              and ref == {'sha256': sha256(members[name]).hexdigest(), 'bytes': len(members[name])})
    return members


def _parent(members, receipt):
    ref = receipt['parent_review']['artifact']
    _need(isinstance(ref, dict) and ref.get('anchor') == 'probe_directory' and _strict(ref.get('path'))
          and type(ref.get('size')) is int and receipt['parent_review']['preserved'] is True)
    data = members[ref['path']]
    _need(ref == {'anchor': 'probe_directory', 'path': ref['path'], 'size': len(data), 'sha256': sha256(data).hexdigest()})
    result = archive_members(data, ref['sha256'])
    _need(type(receipt['parent_review'].get('payload_count')) is int
          and receipt['parent_review']['payload_count'] == len(result)-1)
    return result


def _header(members, *, kind, report_name, report_key, policy, status, calls):
    receipt = _parse_json(members['probe_receipt.json'])
    report = _parse_json(members[report_name])
    _need(type(receipt.get('schema_version')) is int and receipt['schema_version'] == 1
          and receipt.get('kind') == kind and receipt.get('analysis_completed') is True
          and receipt.get('automatic_adoption') is False and receipt.get('requires_cif_review') is False
          and type(report.get('schema_version')) is int and report['schema_version'] == 1
          and report.get('policy_id') == policy and report.get('status') == status
          and type(report.get('new_native_calls')) is int and report['new_native_calls'] == calls
          and report.get('automatic_adoption') is False and report.get('requires_cif_review') is False
          and report.get('scientific_qualification') == 'NOT_ASSESSED')
    directory = Path(report_name).parent.as_posix()
    expected = {'directory': {'anchor': 'probe_directory', 'path': directory},
                'report_sha256': sha256(members[report_name]).hexdigest(), 'report_size': len(members[report_name]),
                'status': status, 'new_native_calls': calls}
    _need(receipt[report_key] == expected and type(receipt[report_key]['new_native_calls']) is int)
    return receipt, report


def _lineage(members):
    """Bind six explicit capsule layers; do not recursively discover archives."""
    receipt, saved = _header(members, kind='mixed-endpoint-replay-probe',
        report_name='saved_replay/mixed_endpoint_saved_replay.json', report_key='saved_endpoint_replay',
        policy='cif-saved-endpoint-portable-replay-v1', status='SAVED_ENDPOINT_REPLAY_PASS', calls=0)
    _need(receipt.get('new_native_calls') == 0 and type(receipt['new_native_calls']) is int
          and receipt.get('model_optimization_requested') is False and receipt.get('mtz_used') is False
          and receipt.get('production_checkpoint') == 'NOT_CREATED'
          and receipt.get('captured_code_execution') == 'NOT_RUN'
          and receipt.get('parent_review_preserved') is True and receipt.get('frozen_runtime_preserved') is True
          and all(receipt.get(k) == 'NOT_RUN' for k in ['dictionary_generation', 'cache_writes',
              'coot_execution', 'readyset_execution', 'refinement']))
    c93 = _parent(members, receipt)
    r93, _ = _header(c93, kind='mixed-endpoint-window-probe',
        report_name='mixed_endpoint_window/mixed_endpoint_window_qualification.json', report_key='mixed_endpoint_window',
        policy='cif-mixed-saved-endpoint-resolution-window-v1', status='MIXED_ENDPOINT_QUALIFIED', calls=2)
    c92 = _parent(c93, r93)
    r92, _ = _header(c92, kind='mixed-endpoint-probe', report_name='mixed_endpoint/mixed_endpoint_qualification.json',
        report_key='mixed_endpoint', policy='cif-mixed-saved-endpoint-qualification-v1', status='REVIEW', calls=1)
    c91 = _parent(c92, r92)
    r91, _ = _header(c91, kind='mixed-torsion-probe', report_name='mixed_torsion/mixed_torsion_audit.json',
        report_key='mixed_torsion', policy='cif-mixed-fixed-torsion-audit-v1', status='MIXED_TORSION_AUDIT_COMPLETE', calls=1)
    c90 = _parent(c91, r91)
    r90, _ = _header(c90, kind='mixed-geometry-probe', report_name='mixed_geometry/mixed_geometry_trial.json',
        report_key='mixed_geometry', policy='cif-mixed-qualified-geometry-trial-v1', status='REVIEW', calls=1)
    c89 = _parent(c90, r90)
    _header(c89, kind='mixed-gradient-probe', report_name='mixed_gradient/mixed_initial_gradients.json',
        report_key='mixed_gradient', policy='cif-mixed-initial-native-gradient-v1', status='MIXED_INITIAL_DERIVATIVES_PASS', calls=1)
    _need(saved['scientific_parent_archive_sha256'] == r92['parent_review']['artifact']['sha256'])
    return saved, [
        (c93, 'mixed_endpoint_window/', 'window'), (c91, 'mixed_torsion/', 'torsion'),
        (c90, 'mixed_geometry/', 'geometry'), (c89, 'mixed_gradient/', 'gradient'),
        (c89, 'inputs/review/inputs/review/mixed_context/', 'context'),
        (c89, 'inputs/review/inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/', 'linked_parent')]


def _same_replay(recorded, rebuilt):
    """Qualification is exact; two local roundoff observations may differ."""
    a, b = deepcopy(recorded), deepcopy(rebuilt)
    left, right = a.pop('descriptive_geometry_replay'), b.pop('descriptive_geometry_replay')
    _need(a == b and set(left) == set(right) == {'full_precision', 'pdb_rounded'})
    for key in left:
        x, y = left[key], right[key]
        for row in [x, y]:
            count, delta, bound = (row[k] for k in ['changed_derived_values', 'maximum_absolute_difference', 'maximum_allowed_difference'])
            _need(type(count) is int and count >= 0 and type(delta) in (int, float) and math.isfinite(delta)
                  and type(bound) in (int, float) and math.isfinite(bound) and 0 <= delta <= bound
                  and (count == 0) is (delta == 0) and row['consistent'] is True and row['issue_count'] == 0)
            for field in ['changed_derived_values', 'maximum_absolute_difference']:
                row.pop(field)
        _need(x == y)


@contextmanager
def verified_endpoint_source(path, digest, *, include_context=False):
    """Replay existing native observations and yield their exact ordered inputs."""
    path = Path(path)
    _need(not any(p.is_symlink() for p in [path, *path.parents]) and path.is_file()
          and path.stat().st_size <= MAX_ARCHIVE_BYTES)
    original = path.read_bytes()
    try:
        saved, views = _lineage(archive_members(original, digest))
        with tempfile.TemporaryDirectory(prefix='mixed-runtime-source-') as temporary:
            root = Path(temporary).resolve()
            before = {}
            for members, prefix, name in views:
                for key, data in members.items():
                    if key.startswith(prefix):
                        relative = key[len(prefix):]
                        _need(_strict(relative))
                        target = root/name/relative; target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data); before[name+'/'+relative] = sha256(data).hexdigest()
            from .cif_mixed_endpoint_replay import replay_saved_endpoint_window
            replay = replay_saved_endpoint_window(root/'window', torsion_directory=root/'torsion', geometry_directory=root/'geometry',
                gradient_directory=root/'gradient', context_directory=root/'context', linked_parent_directory=root/'linked_parent',
                parent_archive_sha256=saved['scientific_parent_archive_sha256'])
            _same_replay(saved, replay)
            decision = replay['coordinate_decision']
            _need(decision['selected'] == 'qualified_geometry_endpoint' and decision['endpoint_usable'] is True
                  and decision['continue_solving'] is True and all(v is True for v in decision['checks'].values())
                  and replay['original_status'] == 'MIXED_ENDPOINT_QUALIFIED')
            report = _parse_json((root/'window/mixed_endpoint_window_qualification.json').read_bytes())
            ref = report['native_readback']['receipt']; _need(_strict(ref['path']))
            folder = (root/'window'/ref['path']).parent
            capture = _parse_json((folder/'native_receipt.json').read_bytes())
            resources = []
            for i, row in enumerate(capture['inputs']):
                _need(row['anchor'] == 'native_directory' and _strict(row['path']) and row['input_index'] == i)
                resource = folder/row['path']; data = resource.read_bytes()
                _need(type(row['size']) is int and len(data) == row['size'] and sha256(data).hexdigest() == row['sha256'])
                resources.append((row['role'], resource.name, data))
            _need([r for r, _, _ in resources].count('model') == 1 and resources[0][0] == 'model'
                  and (root/'window/candidate/saved_mixed_endpoint.pdb').read_bytes() == resources[0][2])
            from .cif_mixed_source_review import review_verified_context
            context = _parse_json((root/'context/mixed_context.json').read_bytes())
            source_review = review_verified_context(root/'context', root/'linked_parent', context)
            extra = ({'context_view': (root/'context', root/'linked_parent', context),
                      'native_readback': capture['native_validation']} if include_context else {})
            yield {**extra, 'replay': replay, 'resources': resources, 'atom_count': capture['native_validation']['atom_count'],
                   'source_state_review': source_review,
                   'source_chemical_findings': report['source_chemical_findings']}
            _need(before == {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
                  and path.read_bytes() == original, 'Source or staged evidence changed during mixed handoff')
    except (OSError, KeyError, TypeError, IndexError, OverflowError, zipfile.BadZipFile) as exc:
        raise ValueError('Incomplete or changed mixed endpoint capsule') from exc
