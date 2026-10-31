#!/usr/bin/env python3
"""Check recovered component dictionaries in the fixed mixed model.

Explicit source-qualified site contexts preserve the frozen model and original
NARestraints policy. Two fixed native reads are separate from production adoption.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
REVIEW_SHA256 = 'd2e5895125f41982b9bae7bc869a94dac925aef700d47a15f79ef1bf4bcbfbde'
SAVED_REVIEW_SHA256 = 'a3d2a63edb33a3da76fa55ea785349fc3191638a2b39815b73663b7b7205ef54'
NATIVE_OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'PHENIX', 'PHENIX_ROOT', 'PHENIX_VERSION',
                    'LIBTBX_BUILD', 'LIBTBX_DIST', 'BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(name):
    return (isinstance(name, str) and bool(name) and not name.startswith('/')
            and '\\' not in name and ':' not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and all(p not in {'', '.', '..'} for p in name.split('/')))


def _runtime_members():
    if not isinstance(BUNDLE, dict) or not isinstance(RUNTIME_BASE64, str):
        raise ValueError('Use the assembled probe, not its source template')
    data = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(data) != BUNDLE['runtime_archive_sha256']:
        raise ValueError('Runtime archive checksum differs')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if (len(entries) > 512 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 32 * 1024 * 1024
                or any(not _safe(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 8 * 1024 * 1024 for e in entries)):
            raise ValueError('Unsafe or oversized runtime archive')
        members = {e.filename: z.read(e) for e in entries}
    if set(members) != set(BUNDLE['runtime_files']):
        raise ValueError('Runtime inventory differs')
    for name, value in members.items():
        ref = BUNDLE['runtime_files'][name]
        if len(value) != ref['size'] or _sha(value) != ref['sha256']:
            raise ValueError('Runtime member checksum differs')
    return members


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    with path.open('xb') as handle:
        handle.write(data)


def _configuration_source():
    if os.environ.get('NASOLVE_CONFIG_FILE'):
        return Path(os.environ['NASOLVE_CONFIG_FILE']).expanduser()
    if sys.platform == 'darwin':
        return Path.home()/'Library/Application Support/NASolve/config.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'nasolve/config.json'


def _isolate(runtime, session, members):
    if any(n == p or n.startswith(p+'.') for n in sys.modules for p in ['nasolve', 'restraints']):
        raise ValueError('Start the probe in a fresh Python process')
    config = {'schema_version': 1}
    source = _configuration_source()
    if source.is_file():
        old = json.loads(source.read_bytes())
        if not isinstance(old, dict):
            raise ValueError('Saved configuration must be an object')
        config.update({k: old[k] for k in ['phenix', 'coot'] if k in old})
    _write(session/'runtime-config.json', config)
    for name, data in members.items():
        _write(runtime/name, data)
    sys.path[:0] = [str(runtime/'src'), str(runtime)]
    os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])
    os.environ['NASOLVE_CONFIG_FILE'] = str(session/'runtime-config.json')
    os.environ['NASOLVE_NATIVE_ENV_ISOLATION'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True


def _save_receipt(session, receipt):
    path = session/'probe_receipt.json'
    if path.is_symlink():
        raise ValueError('Receipt cannot be a symlink')
    descriptor, temporary = tempfile.mkstemp(prefix='.receipt-', dir=session)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _review_zip(session, *, receipt_only=False):
    token = session.name.rsplit('-', 1)[-1]
    suffix = '_failure_review.zip' if receipt_only else '_mixed_linked_recovery_review.zip'
    destination = session/(BUNDLE['delivery_prefix']+'_'+token+suffix)
    if receipt_only:
        files = {'probe_receipt.json': (session/'probe_receipt.json').read_bytes()}
    else:
        from nasolve.cif_review_transport import review_archive_files
        files = review_archive_files(session, destination)
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)}
                                                     for n, d in files.items()}, indent=2))
    return destination


def _report_failure(session, receipt, exc):
    """Keep the first failure and a receipt when full collection is unavailable."""
    receipt.update(analysis_completed=False, error_type=type(exc).__name__, error=str(exc))
    _save_receipt(session, receipt)
    try:
        return _review_zip(session)
    except Exception as collection_error:
        receipt.update(archive_collection_error=str(collection_error),
                       failure_archive_scope='RECEIPT_ONLY; OTHER_OUTPUTS_REMAIN_IN_SESSION')
        _save_receipt(session, receipt)
        return _review_zip(session, receipt_only=True)


def _read_capsule(path, *, saved_native_only=False):
    """Verify the action's exact return before exposing saved data to readers.

    The preserved C82 parent includes two 20 MiB reports. Its explicit 128 MiB total / 32 MiB member
    limits preserve those real artifacts without relaxing embedded-runtime bounds.
    """
    from nasolve.cif_review_transport import is_safe_review_member, _parse_json
    original = path.read_bytes()
    expected = SAVED_REVIEW_SHA256 if saved_native_only else REVIEW_SHA256
    if _sha(original) != expected:
        raise ValueError('Require the exact verified '+('C84 linked-recovery' if saved_native_only else 'C83 mixed-recovery')+' review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = archive.infolist()
        if (len(entries) > 1024 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 128 * 1024 * 1024
                or any(not is_safe_review_member(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 32 * 1024 * 1024 for e in entries)):
            raise ValueError('Unsafe or oversized review archive')
        members = {entry.filename: archive.read(entry) for entry in entries}
    manifest = _parse_json(members['manifest.json'])
    if not isinstance(manifest, dict) or set(manifest) != set(members) - {'manifest.json'}:
        raise ValueError('Review inventory differs')
    for name, ref in manifest.items():
        if (not isinstance(ref, dict) or type(ref.get('bytes')) is not int
                or ref != {'sha256': _sha(members[name]), 'bytes': len(members[name])}):
            raise ValueError('Review member checksum differs')
    receipt = _parse_json(members['probe_receipt.json'])
    if saved_native_only:
        main = _parse_json(members['mixed_linked_recovery/mixed_linked_recovery.json'])
        if (receipt.get('kind') != 'mixed-linked-recovery-probe' or receipt.get('delivery_prefix') != '84_Cedar'
                or receipt.get('analysis_completed') is not False or receipt.get('error_type') != 'ValueError'
                or receipt.get('error') != 'Linked native qualification does not reproduce'
                or main.get('status') != 'REVIEW' or main.get('new_native_calls') != 2
                or main.get('maximum_native_calls') != 2
                or not all(isinstance(main.get(k), dict) and 'receipt' in main[k]
                           for k in ['native_baseline', 'native_active'])
                or not isinstance(main.get('qualification'), dict) or 'artifact' not in main['qualification']):
            raise ValueError('Require the exact C84 saved linked-native failure evidence')
    else:
        main = _parse_json(members['mixed_recovery/mixed_recovery.json'])
        if (receipt.get('kind') != 'mixed-deficient-numerics-recovery-probe' or receipt.get('delivery_prefix') != '83_Cedar'
                or receipt.get('analysis_completed') is not True or main.get('status') != 'MIXED_RECOVERY_ISOLATED_PASS'
                or receipt.get('mixed_recovery') != {'directory': {'anchor': 'probe_directory', 'path': 'mixed_recovery'}, **main}):
            raise ValueError('Require the exact completed C83 isolated recovery evidence')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _replay_saved_native(members):
    """Read the original bound scientific subtree; never rewrite its evidence."""
    from nasolve.cif_mixed_linked_recovery import read_mixed_linked_recovery, _resolve
    prefix = 'mixed_linked_recovery/'
    with tempfile.TemporaryDirectory(prefix='nasolve-saved-linked-native-') as temporary:
        view = Path(temporary).resolve()/'data'
        for name, data in members.items():
            if name.startswith(prefix):
                if not _safe(name):
                    raise ValueError('Unsafe saved linked-native member')
                _write(view/name[len(prefix):], data)
        result = read_mixed_linked_recovery(view)
        qualification = json.loads(_resolve(view, result['qualification']['artifact']).read_bytes())
    def ref(name):
        data = members[name]
        return {'anchor': 'preserved_review', 'path': name, 'sha256': _sha(data), 'size': len(data)}
    return {'schema_version': 1, 'policy_id': 'cif-saved-mixed-linked-recovery-v1',
        'status': result['status'], 'targets': result['targets'],
        'coordinate_decision': result['coordinate_decision'],
        'saved_native_calls': result['new_native_calls'], 'new_native_calls': 0,
        'report': ref(prefix+'mixed_linked_recovery.json'),
        'qualification': {'artifact': ref(prefix+result['qualification']['artifact']['path']),
            'status': qualification['status'], 'mechanics_checks_pass': qualification['mechanics_checks_pass'],
            'checks': qualification['checks'], 'membership': qualification['membership']['checks']},
        'policy_authority': 'NARestraints', 'captured_code_execution': 'NOT_RUN',
        'automatic_adoption': False, 'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED'}


def _materialize_parents(members, destination):
    """Make shallow parent data views; saved programs are never executed."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Parent data destination already exists')
    views = []
    for prefix, leaf in [('mixed_recovery/', 'recovery'),
                         ('inputs/review/mixed_native/', 'native')]:
        view = destination/leaf
        for name, data in members.items():
            if name.startswith(prefix) and _safe(name):
                _write(view/name[len(prefix):], data)
        if not view.is_dir():
            raise ValueError('Missing declared parent scientific view')
        views.append(view)
    return tuple(views)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C83 ZIP, or C84 with --saved-native-only; captured programs stay data')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--inspect-only', action='store_true', help='Verify and stage source-bound recovery without an SDK process')
    mode.add_argument('--saved-native-only', action='store_true', help='Replay the completed C84 native captures without Phenix or another native process')
    parser.add_argument('--timeout-seconds', type=int, default=60, help='Deadline 1–60 seconds for each fixed native read')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 60:
        parser.error('The native deadline must be from 1 to 60 seconds')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-linked-recovery-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'generation_execution': 'NOT_RUN', 'model_optimization_requested': False,
        'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-linked-recovery-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        for package in [nasolve, restraints]:
            if not Path(package.__file__).resolve().is_relative_to(runtime):
                raise ValueError('Probe imported an ambient runtime')
        members = _read_capsule(args.review_zip.expanduser().resolve(strict=True), saved_native_only=args.saved_native_only)
        from nasolve.cif_review_transport import stage_review_members, staged_review_members_match
        stage_review_members(members, session/'inputs/review', indexed=True)
        receipt['parent_review'] = {'historical_path': str(args.review_zip),
            'sha256': SAVED_REVIEW_SHA256 if args.saved_native_only else REVIEW_SHA256,
            'payload_count': len(members)-1, 'preserved': True,
            'scope': ('EXACT_C84_PARENT' if args.saved_native_only else 'EXACT_C83_PARENT')+'; INDEXED_OPAQUE_TRANSPORT; CAPTURED_CODE_NOT_EXECUTED'}
        phenix = None
        if not (args.inspect_only or args.saved_native_only):
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n == 'phenix.python'}}
        from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery, read_mixed_linked_recovery
        from nasolve.cif_mixed_native import read_mixed_native
        from nasolve.cif_mixed_recovery import read_mixed_recovery
        if args.saved_native_only:
            print('Saved mixed-model linked-native replay:', BUNDLE['delivery_prefix'], flush=True)
            print('Verifying both completed native captures; no new native process.', flush=True)
            result = _replay_saved_native(members)
            _write(session/'saved_linked_recovery.json', result)
            data = (session/'saved_linked_recovery.json').read_bytes()
            receipt['saved_linked_recovery'] = {'artifact': {'anchor': 'probe_directory',
                'path': 'saved_linked_recovery.json', 'sha256': _sha(data), 'size': len(data)},
                'status': result['status'], 'saved_native_calls': result['saved_native_calls'], 'new_native_calls': 0}
        else:
            print('Recovered dictionaries in the fixed mixed model:', BUNDLE['delivery_prefix'], flush=True)
            print('Preparing explicit linked contexts; preserving coordinates and the declared NARestraints policy.', flush=True)
            # The full parent remains indexed. Its scientific read view is
            # temporary and does not duplicate reports in the new ZIP.
            with tempfile.TemporaryDirectory(prefix='nasolve-mixed-linked-parent-') as temporary:
                recovery, native = _materialize_parents(members, Path(temporary).resolve()/'data')
                read_mixed_recovery(recovery)
                read_mixed_native(native)
                result = audit_mixed_linked_recovery(recovery, native, phenix, session/'mixed_linked_recovery',
                    timeout_seconds=args.timeout_seconds)
            if read_mixed_linked_recovery(session/'mixed_linked_recovery') != result:
                raise ValueError('Portable recovery report differs after parent view removal')
            report_bytes = (session/'mixed_linked_recovery/mixed_linked_recovery.json').read_bytes()
            receipt['linked_recovery'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_linked_recovery'},
                'report_sha256': _sha(report_bytes), 'report_size': len(report_bytes), 'status': result['status'],
                'targets': result['targets'], 'new_native_calls': result['new_native_calls']}

        if not staged_review_members_match(members, session/'inputs/review'):
            raise ValueError('Preserved parent review differs')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Selected components:', ', '.join(result.get('targets', [])), flush=True)
        print('Linked recovery:', result['status'], flush=True)
        if args.saved_native_only:
            print('Preserved native calls:', result['saved_native_calls'], '; new native calls: 0', flush=True)
            followup = [name for name, ok in result['qualification']['membership'].items() if ok is not True]
            print('Remaining whole-model checks:', ', '.join(followup) or 'none', flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (fixed linked-model mechanics; source-state findings and full-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed linked recovery test stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
