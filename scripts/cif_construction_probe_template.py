#!/usr/bin/env python3
"""Read-only construction provenance for the verified Cedar 15 geometry review."""
from __future__ import annotations

import argparse
import base64
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
REVIEW_SHA256 = 'b545664e11d09b728b045bfe44fbb786520e8e82997f25aa753b06622e3c9be9'
CAPTURE_PREFIX = 'inputs/review/native_candidate/cif-native-47i0u3af'
RUN_RELATIVE = 'NASolve-live-tests/synthetic-dna-mechanics-om4jv7qq/synthetic-dna-combined-2n4kszi5/dataset/AutoMR/run_001'
HISTORICAL_RUN = '/Users/svecchio/' + RUN_RELATIVE
MODEL_BINDING = {'path': 'PostMR/Model/prepared_model.pdb', 'sha256': '51b6c2acf403b1377e73bdbeae4c35ab4fdd9c105bb20a5ca3c52ee03b0ae845', 'size': 70150}
SOURCE_AUDIT_BINDING = {'path': 'PostMR/Restraints/cif_doctor_source.json', 'sha256': '31ff002a4794a011c4470b6dd294a4cfea5f29bdc5f280742eb20cbfa71b6fb1', 'size': 1370223}


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


def _review_zip(session):
    token = session.name.rsplit('-', 1)[-1]
    destination = session / (BUNDLE['delivery_prefix'] + '_' + token + '_cif_construction_review.zip')
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


def _read_capsule(path, expected_sha=None):
    original = path.read_bytes()
    if _sha(original) != (expected_sha or REVIEW_SHA256):
        raise ValueError('Require the exact hash-bound 15_Cedar review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries = z.infolist(); names = [e.filename for e in entries]
        manifest = json.loads(z.read('manifest.json'))
        if len(names) != len(set(names)) or set(names) != set(manifest) | {'manifest.json'} or len(manifest) != 51:
            raise ValueError('Unexpected 15_Cedar payload inventory')
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
    report = json.loads(members['captured_geometry_review.json'])
    capture = json.loads(members[CAPTURE_PREFIX + '/native_receipt.json'])
    native = json.loads(members[CAPTURE_PREFIX + '/native_validation.json'])
    if (prior.get('kind') != 'cif-captured-geometry-review-probe' or prior.get('delivery_prefix') != '15_Cedar'
            or prior.get('status') != 'REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('geometry_summary') != report.get('summary') or capture.get('native_validation') != native
            or capture.get('execution', {}).get('status') != 'COMPLETED' or capture['execution'].get('returncode') != 0):
        raise ValueError('Require the completed preserved Cedar 15 capture')
    for row in capture['inputs'] + capture['outputs']:
        if row.get('anchor') != 'native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported captured native reference')
        data = members[CAPTURE_PREFIX + '/' + row['path']]
        if len(data) != row['size'] or _sha(data) != row['sha256']:
            raise ValueError('Captured native artifact integrity mismatch')
    return members, native, report, original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, default=Path.home() / 'NASolve-live-tests/15_Cedar_cif-geometry-review-01pvz5n5/15_Cedar_01pvz5n5_cif_geometry_review.zip')
    parser.add_argument('--run', type=Path, default=Path.home() / RUN_RELATIVE)
    parser.add_argument('--output-parent', type=Path, default=Path.home() / 'NASolve-live-tests')
    args = parser.parse_args(); session = None; original = None; review = None
    receipt = {'schema_version': 1, 'kind': 'cif-construction-provenance-probe',
               'delivery_prefix': BUNDLE['delivery_prefix'], 'build': BUNDLE,
               'native_execution': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN',
               'refinement': 'NOT_RUN', 'scientific_approval': 'NOT_RUN', 'automatic_adoption': False}
    try:
        runtime = _runtime_members(); review = args.review_zip.expanduser().resolve(strict=True)
        run = args.run.expanduser().resolve(strict=True); parent = args.output_parent.expanduser().resolve()
        if (parent == review.parent or parent.is_relative_to(review.parent)
                or parent == run or parent.is_relative_to(run)):
            raise ValueError('Output must be outside both preserved input directories')
        members, native, geometry, original = _read_capsule(review)
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix'] + '_cif-construction-', dir=parent))
        _materialize(runtime, runtime, session / 'runtime')
        _materialize(members, members, session / 'inputs/review')
        sys.path[:0] = [str(session / 'runtime/src'), str(session / 'runtime')]
        sys.dont_write_bytecode = True
        from nasolve.cif_construction_provenance import (
            audit_construction_stages, snapshot_construction_run, verify_construction_snapshot)
        print('CIF construction provenance:', BUNDLE['delivery_prefix'], flush=True)
        state = snapshot_construction_run(run, session / 'inputs/run', MODEL_BINDING, HISTORICAL_RUN)
        source_audit = state['records'].get(SOURCE_AUDIT_BINDING['path'])
        if source_audit and source_audit['status'] == 'RECORDED' and any(
                source_audit[k] != SOURCE_AUDIT_BINDING[k] for k in ('sha256', 'size')):
            raise ValueError('Original source assessment differs from the reviewed binding')
        report = audit_construction_stages(native, geometry, state['stages'], state['parents'])
        _json(session / 'construction_provenance.json', report)
        evidence = {'schema_version': 1, 'original_run_provenance': str(run), 'historical_run_provenance': HISTORICAL_RUN,
                    'binding': MODEL_BINDING, 'source_artifacts': state['records'], 'saved_script_declarations': state['references'],
                    'frozen_run_anchor': {'anchor': 'probe_directory', 'path': 'inputs/run'},
                    'prior_archive': {'sha256': REVIEW_SHA256, 'bytes': len(original), 'verified_payloads': 51},
                    'frozen_review_files': {name: {'bytes': len(data), 'sha256': _sha(data)} for name,data in members.items()}}
        _json(session / 'construction_evidence.json', evidence)
        verify_construction_snapshot(run, session / 'inputs/run', state['records'])
        for name, data in members.items():
            if (session / 'inputs/review' / PurePosixPath(name)).read_bytes() != data:
                raise ValueError('Frozen captured evidence changed')
        if review.read_bytes() != original:
            raise ValueError('Preserved review archive changed')
        receipt.update(status='REVIEW', analysis_completed=True, original_run_preserved=True,
                       original_archive_preserved=True, frozen_inputs_preserved=True,
                       selected_sites=report['selected_sites'], finding_count=len(report['findings']),
                       first_observed_outlier_counts=report['first_observed_outlier_counts'],
                       threshold_crossing_count=report['threshold_crossing_count'], root_cause='NOT_ESTABLISHED')
        _json(session / 'probe_receipt.json', receipt)
        print('Selected sites:', ', '.join(report['selected_sites']), flush=True)
        print('Earliest observed outlier stages:', json.dumps(report['first_observed_outlier_counts'], sort_keys=True), flush=True)
        print('Adjacent-stage threshold crossings:', report['threshold_crossing_count'], flush=True)
        print('Diagnostic: REVIEW (stage evidence; causal step requires review)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        receipt.update(status='REVIEW', analysis_completed=False, error=str(exc))
        if session:
            receipt['original_archive_preserved'] = bool(original is not None and review and review.read_bytes() == original)
            if not (session / 'probe_receipt.json').exists(): _json(session / 'probe_receipt.json', receipt)
            print('REVIEW ZIP:', _review_zip(session), flush=True)
        print('Construction provenance stopped:', str(exc), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
