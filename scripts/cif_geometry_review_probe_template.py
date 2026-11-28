#!/usr/bin/env python3
"""Read-only scalar geometry review of the exact returned Cedar 14 capture."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
REVIEW_SHA256 = 'd94ac53972a8843b8b2cc3d87b32fdbbc4617dc47179d184850833fb91bf8bb3'
CAPTURE_PREFIX = 'native_candidate/cif-native-47i0u3af'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(name):
    return isinstance(name, str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        p not in {'', '.', '..'} for p in name.split('/'))


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def _runtime_members():
    data = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(data) != BUNDLE['runtime_archive_sha256']:
        raise ValueError('Embedded runtime checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if len(entries) != len({e.filename for e in entries}) or any(
                not _safe(e.filename) or stat.S_ISLNK(e.external_attr >> 16) for e in entries):
            raise ValueError('Unsafe or duplicate runtime member')
        members = {e.filename: z.read(e) for e in entries}
    if set(members) != set(BUNDLE['runtime_files']):
        raise ValueError('Runtime inventory mismatch')
    for name, data in members.items():
        expected = BUNDLE['runtime_files'][name]
        if len(data) != expected['size'] or _sha(data) != expected['sha256']:
            raise ValueError('Runtime file integrity mismatch')
    return members


def _materialize(members, names, target):
    for name in sorted(set(names)):
        if not _safe(name) or name not in members:
            raise ValueError('Missing explicit capsule member: ' + str(name))
        path = target / PurePosixPath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(members[name])


def _read_capsule(path, expected_sha=None):
    original = path.read_bytes()
    if _sha(original) != (expected_sha or REVIEW_SHA256):
        raise ValueError('Require the exact hash-bound 14_Cedar review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries = z.infolist(); names = [e.filename for e in entries]
        manifest = json.loads(z.read('manifest.json'))
        if len(names) != len(set(names)) or set(names) != set(manifest) | {'manifest.json'} or len(manifest) != 141:
            raise ValueError('Unexpected 14_Cedar payload inventory')
        members = {}
        for entry in entries:
            name = entry.filename
            if not _safe(name) or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Unsafe review path')
            data = z.read(entry)
            if name != 'manifest.json' and (len(data) != manifest[name]['bytes'] or _sha(data) != manifest[name]['sha256']):
                raise ValueError('Review payload integrity mismatch')
            members[name] = data
    prior = json.loads(members['probe_receipt.json'])
    qualification = json.loads(members['bundle_qualification.json'])
    if (prior.get('kind') != 'cif-outgoing-bundle-native-probe' or prior.get('delivery_prefix') != '14_Cedar'
            or prior.get('status') != 'REVIEW' or prior.get('original_archive_preserved') is not True
            or prior.get('frozen_inputs_preserved') is not True or prior.get('qualification') != qualification
            or Counter(c['status'] for c in qualification['checks']) != {'PASS': 138, 'UNSUPPORTED': 9}
            or any(c['status'] != 'PASS' and not c['check'].startswith('effective-site-formal-charges:')
                   for c in qualification['checks'])):
        raise ValueError('Require the verified completed Cedar 14 mechanics review')
    return members, prior, original


def _freeze_capture(session, members, prior):
    read = lambda name: json.loads(members[name])
    capture = read(CAPTURE_PREFIX + '/native_receipt.json')
    native = read(CAPTURE_PREFIX + '/native_validation.json')
    if (capture != prior.get('native_validation') or capture.get('native_validation') != native
            or capture.get('audit_kind') != 'cif_native_bundle_inspection'
            or capture.get('policy_id') != 'cif-native-bundle-inventory-v1'
            or capture.get('status') != 'REVIEW' or capture.get('execution', {}).get('returncode') != 0
            or capture['execution'].get('status') != 'COMPLETED'
            or capture.get('source_preserved') is not True or capture.get('frozen_inputs_preserved') is not True
            or capture.get('automatic_adoption') is not False):
        raise ValueError('Captured native receipt is incomplete or inconsistent')
    names = {CAPTURE_PREFIX + '/native_receipt.json'}
    roles = Counter(row['role'] for row in capture['inputs'])
    if roles != {'model': 1, 'dictionary': 18, 'phil': 11}:
        raise ValueError('Unexpected captured bundle roles')
    for row in capture['inputs'] + capture['outputs']:
        if row.get('anchor') != 'native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported native artifact anchor/path')
        name = CAPTURE_PREFIX + '/' + row['path']
        data = members[name]
        if len(data) != row['size'] or _sha(data) != row['sha256']:
            raise ValueError('Captured native artifact integrity mismatch')
        names.add(name)
    if CAPTURE_PREFIX + '/native_validation.json' not in names:
        raise ValueError('Native report is not anchored in its receipt')
    _materialize(members, names, session / 'inputs/review')
    manifest = read('manifest.json')
    state = {
        'prior_archive': {'sha256': REVIEW_SHA256, 'verified_payloads': 141},
        'prior_build': {k: prior['build'][k] for k in ('nasolve_source', 'narestraints_source')},
        'captured_native_receipt': {'anchor': 'returned_capsule', 'path': CAPTURE_PREFIX + '/native_receipt.json',
                                    'sha256': _sha(members[CAPTURE_PREFIX + '/native_receipt.json'])},
        'prior_qualification': {'status': 'REVIEW', 'counts': {'PASS': 138, 'UNSUPPORTED': 9},
                                'sha256': _sha(members['bundle_qualification.json']), 'new_execution': False},
        'source_assessments': [{'component': p['component'], 'site': a['site'],
                                'before': a['before']['status'], 'after': a['after']['status']}
                               for p in prior['outgoing_preparations'] for a in p['projected_assessments']],
        'frozen_members': {name: manifest[name] for name in sorted(names)}}
    _json(session / 'prior_evidence.json', state)
    return native, state


def _verify_frozen(session, state):
    anchor = session / 'inputs/review'
    for name, row in state['frozen_members'].items():
        path = anchor / PurePosixPath(name)
        if path.is_symlink() or not path.resolve().is_relative_to(anchor.resolve()):
            raise ValueError('Frozen capture escaped its declared anchor')
        data = path.read_bytes()
        if len(data) != row['bytes'] or _sha(data) != row['sha256']:
            raise ValueError('Frozen capture changed: ' + name)


def _review_zip(session):
    token = session.name.rsplit('-', 1)[-1]
    destination = session / (BUNDLE['delivery_prefix'] + '_' + token + '_cif_geometry_review.zip')
    files = {}
    for path in sorted(session.rglob('*')):
        if path == destination or path.is_relative_to(session / 'runtime'):
            continue
        if path.is_symlink():
            raise ValueError('Unexpected output symlink')
        if path.is_file() and path.suffix not in {'.pyc', '.pkl', '.pickle'}:
            files[path.relative_to(session).as_posix()] = path.read_bytes()
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)} for n, d in files.items()}, indent=2))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, default=Path.home() / 'NASolve-live-tests/14_Cedar_cif-outgoing-bundle-7qm2tnry/14_Cedar_7qm2tnry_cif_outgoing_bundle_review.zip')
    parser.add_argument('--output-parent', type=Path, default=Path.home() / 'NASolve-live-tests')
    args = parser.parse_args(); session = None; original = None; review = None
    receipt = {'schema_version': 1, 'kind': 'cif-captured-geometry-review-probe',
               'delivery_prefix': BUNDLE['delivery_prefix'], 'build': BUNDLE,
               'native_execution': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN',
               'refinement': 'NOT_RUN', 'scientific_approval': 'NOT_RUN', 'automatic_adoption': False}
    try:
        runtime = _runtime_members(); review = args.review_zip.expanduser().resolve(strict=True)
        parent = args.output_parent.expanduser().resolve()
        if parent == review.parent or parent.is_relative_to(review.parent):
            raise ValueError('Output must be outside the preserved diagnostic directory')
        members, prior, original = _read_capsule(review)
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix'] + '_cif-geometry-review-', dir=parent))
        _materialize(runtime, runtime, session / 'runtime')
        sys.path[:0] = [str(session / 'runtime/src'), str(session / 'runtime')]
        sys.dont_write_bytecode = True
        from nasolve.cif_captured_geometry import review_captured_geometry
        print('Captured CIF geometry review:', BUNDLE['delivery_prefix'], flush=True)
        native, state = _freeze_capture(session, members, prior)
        report = review_captured_geometry(native)
        _json(session / 'captured_geometry_review.json', report)
        lines = ['Captured Cartesian geometry; descriptive comparisons only.']
        for kind, summary in report['summary'].items():
            text = '{}: {} proxies; {} nominal deviations >= 5; {} sign conflicts'.format(
                kind, summary['captured_proxies'], summary['nominal_abs_ge_5'], summary['sign_conflicts'])
            lines.append(text); print(text, flush=True)
        lines += ['Native residuals, deferred geometry categories and absolute stereochemistry remain unassessed.',
                  'No coordinate changes, new native interpretation, optimization, refinement or adoption.']
        (session / 'summary.txt').write_text('\n'.join(lines) + '\n')
        _verify_frozen(session, state)
        if review.read_bytes() != original:
            raise ValueError('Preserved review archive changed')
        receipt.update(status='REVIEW', analysis_completed=True, frozen_inputs_preserved=True,
                       original_archive_preserved=True, prior_evidence='prior_evidence.json',
                       geometry_policy=report['policy_id'], geometry_summary=report['summary'])
        _json(session / 'probe_receipt.json', receipt)
        print('Diagnostic: REVIEW (descriptive geometry; qualification remains open)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        receipt.update(status='REVIEW', analysis_completed=False, error=str(exc))
        if session:
            receipt['original_archive_preserved'] = bool(original is not None and review and review.read_bytes() == original)
            if not (session / 'probe_receipt.json').exists():
                _json(session / 'probe_receipt.json', receipt)
            print('REVIEW ZIP:', _review_zip(session), flush=True)
        print('Captured geometry review stopped:', str(exc), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
