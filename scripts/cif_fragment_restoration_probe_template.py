#!/usr/bin/env python3
"""Separate graph-selected fragment candidate from the verified Cedar 16 capsule."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
REVIEW_SHA256 = 'e6be273bafd9fd6b4a6c6b2125496f1353592b36d3e6e0709da8fab25ea95c8e'
CAPTURE_PREFIX = 'inputs/review/inputs/review/native_candidate/cif-native-47i0u3af'
NATIVE_OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'PHENIX', 'PHENIX_ROOT', 'PHENIX_VERSION',
                    'LIBTBX_BUILD', 'LIBTBX_DIST', 'BOOST_ADAPTBX_FPE_DEFAULT'}


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


def _materialize(members, target):
    for name, data in members.items():
        if not _safe(name):
            raise ValueError('Unsafe materialization path')
        path = target / PurePosixPath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(data)


def _review_zip(session):
    token = session.name.rsplit('-', 1)[-1]
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_fragment_restoration_review.zip')
    files = {}
    for path in sorted(session.rglob('*')):
        if path == destination or path.is_relative_to(session/'runtime'):
            continue
        if path.is_symlink():
            raise ValueError('Unexpected output symlink')
        if path.is_file() and path.suffix not in {'.pyc', '.pkl', '.pickle'}:
            files[path.relative_to(session).as_posix()] = path.read_bytes()
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)} for n,d in files.items()}, indent=2))
    return destination


def _read_capsule(path, expected_sha=None):
    original = path.read_bytes()
    if _sha(original) != (expected_sha or REVIEW_SHA256):
        raise ValueError('Require the exact hash-bound 16_Cedar review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries = z.infolist(); names = [e.filename for e in entries]
        manifest = json.loads(z.read('manifest.json'))
        if len(names) != len(set(names)) or set(names) != set(manifest)|{'manifest.json'} or len(manifest) != 74:
            raise ValueError('Unexpected 16_Cedar payload inventory')
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
    construction = json.loads(members['construction_provenance.json'])
    evidence = json.loads(members['construction_evidence.json'])
    capture = json.loads(members[CAPTURE_PREFIX+'/native_receipt.json'])
    native = json.loads(members[CAPTURE_PREFIX+'/native_validation.json'])
    if (prior.get('kind') != 'cif-construction-provenance-probe' or prior.get('delivery_prefix') != '16_Cedar'
            or prior.get('analysis_completed') is not True or prior.get('status') != 'REVIEW'
            or not all(prior.get(k) is True for k in ('original_run_preserved','original_archive_preserved','frozen_inputs_preserved'))
            or construction.get('analysis_completed') is not True or capture.get('native_validation') != native
            or capture.get('execution',{}).get('status') != 'COMPLETED' or capture['execution'].get('returncode') != 0):
        raise ValueError('Require the completed preserved Cedar 16 capture')
    for relative, row in evidence['source_artifacts'].items():
        if row.get('anchor') != 'run' or not _safe(relative) or row.get('path') != relative:
            raise ValueError('Unsupported construction source reference')
        name = 'inputs/run/'+relative
        if row['status'] == 'NOT_PRESENT':
            if name in members:
                raise ValueError('Missing construction artifact unexpectedly present')
        elif row['status'] != 'RECORDED' or len(members[name]) != row['size'] or _sha(members[name]) != row['sha256']:
            raise ValueError('Construction source artifact integrity mismatch')
    for row in capture['inputs']+capture['outputs']:
        if row.get('anchor') != 'native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported captured native reference')
        data = members[CAPTURE_PREFIX+'/'+row['path']]
        if len(data) != row['size'] or _sha(data) != row['sha256']:
            raise ValueError('Captured native artifact integrity mismatch')
    return members, evidence, capture, original


def _prepare(session, evidence, capture):
    from nasolve.cif_fragment_restoration import (
        assess_fragment_contexts, prepare_fragment_restoration, review_model_with_captured_proxies)
    from nasolve.cif_construction_provenance import declared_coot_references
    run = session/'inputs/review/inputs/run'
    declared = declared_coot_references((run/'PostMR/Coot/mutate.py').read_text(), evidence['historical_run_provenance'])
    if declared != evidence['saved_script_declarations']:
        raise ValueError('Saved Coot declarations disagree with frozen evidence')
    parents = {}
    for site, relative in declared['parents'].items():
        if not _safe(relative) or evidence['source_artifacts'][relative]['status'] != 'RECORDED':
            raise ValueError('Missing explicit parent control')
        parents[site] = run/PurePosixPath(relative)
    directory = session/'inputs/review'/CAPTURE_PREFIX
    def paths(role):
        return [directory/PurePosixPath(r['path']) for r in capture['inputs'] if r['role'] == role]
    models, cifs, phils = paths('model'), paths('dictionary'), paths('phil')
    if len(models) != 1 or len(cifs) != 18 or len(phils) != 11:
        raise ValueError('Unexpected captured bundle input roles')
    eligibility = assess_fragment_contexts(capture['native_validation'],models[0],parents)
    _json(session/'fragment_eligibility.json',eligibility)
    selected = {s:parents[s] for s in eligibility['supported_sites']}
    model = session/'candidate/fragment_restored_model.pdb'
    report = prepare_fragment_restoration(run/'PostMR/Model/after_coot_raw.pdb',models[0],model,
                                          capture['native_validation'],selected)
    report['unsupported_sites_preserved'] = eligibility['unsupported_sites']
    _json(session/'fragment_preparation.json',report)
    predicted = review_model_with_captured_proxies(capture['native_validation'],model)
    _json(session/'predicted_geometry_review.json',predicted)
    return model,cifs,phils,report,predicted


def _fingerprints(phenix, capture):
    if not phenix.root or phenix.version != capture['phenix_version']:
        raise ValueError('Selected Phenix differs from captured native version')
    executable = phenix.executables.get('phenix.python')
    if not executable or _sha(Path(executable).read_bytes()) != capture['executable_sha256']:
        raise ValueError('Phenix dispatcher changed since the captured bundle')
    historical = Path(capture['executable_provenance']).parent.parent
    rows = []
    for row in capture['native_validation']['installed_api_sources']:
        relative = Path(row['historical_path']).relative_to(historical).as_posix()
        if not _safe(relative):
            raise ValueError('Unsupported native source anchor')
        path = Path(phenix.root)/relative
        if not path.resolve().is_relative_to(Path(phenix.root).resolve()) or _sha(path.read_bytes()) != row['sha256']:
            raise ValueError('Installed native API source changed')
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':row['sha256']})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/16_Cedar_cif-construction-2liuorr_/16_Cedar_2liuorr__cif_construction_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    args = parser.parse_args(); session = None; original = None; review = None
    receipt = {'schema_version':1,'kind':'cif-fragment-restoration-native-probe','delivery_prefix':BUNDLE['delivery_prefix'],
        'build':BUNDLE,'automatic_adoption':False,'model_editing':'SEPARATE_CANDIDATE_ONLY','optimization':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','native_execution':'NOT_RUN'}
    try:
        if not 1 <= args.timeout_seconds <= 3600:
            raise ValueError('Timeout must be 1-3600 seconds')
        runtime = _runtime_members(); review = args.review_zip.expanduser().resolve(strict=True)
        parent = args.output_parent.expanduser().resolve()
        if parent == review.parent or parent.is_relative_to(review.parent):
            raise ValueError('Output must be outside the preserved input directory')
        members,evidence,capture,original = _read_capsule(review)
        parent.mkdir(parents=True,exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-fragment-restoration-',dir=parent))
        _materialize(runtime,session/'runtime'); _materialize(members,session/'inputs/review')
        sys.path[:0] = [str(session/'runtime/src'),str(session/'runtime')]; sys.dont_write_bytecode = True
        print('CIF attached-fragment restoration:',BUNDLE['delivery_prefix'],flush=True)
        model,cifs,phils,preparation,predicted = _prepare(session,evidence,capture)
        receipt.update(preparation=preparation,prior_archive={'sha256':REVIEW_SHA256,'bytes':len(original),'verified_payloads':74},
            predicted_geometry_summary=predicted['summary'],status='REVIEW',analysis_completed=True)
        prior_state = json.loads(members['inputs/review/prior_evidence.json'])
        receipt['prior_qualification'] = prior_state['prior_qualification']
        receipt['source_assessments'] = prior_state['source_assessments']
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            from nasolve.cif_native_validation import inspect_native_bundle
            from nasolve.cif_fragment_restoration import qualify_fragment_restoration
            from nasolve.cif_captured_geometry import review_captured_geometry
            phenix = installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints = _fingerprints(phenix,capture); receipt['installed_api_sources'] = fingerprints
            print('Interpreting the separate candidate with the unchanged dictionaries and parameters.',flush=True)
            after = inspect_native_bundle(model,cifs,session/'native_candidate',phenix.executables['phenix.python'],
                environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds,
                phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked')
            receipt.update(native_validation=after,native_execution=after['execution']['status'])
            if after['status'] == 'REVIEW':
                qualification = qualify_fragment_restoration(capture['native_validation'],after['native_validation'],model,preparation)
                _json(session/'native_mechanics.json',qualification);receipt['native_mechanics'] = qualification
                measured = review_captured_geometry(after['native_validation'])
                _json(session/'native_geometry_review.json',measured);receipt['native_geometry_summary'] = measured['summary']
                print('Native mechanics checks:', 'PASS' if qualification['mechanics_checks_pass'] else 'REVIEW',flush=True)
            else:
                receipt['analysis_completed'] = False
                print('Native interpretation requires review:',after.get('error') or after['status'],flush=True)
            if _fingerprints(phenix,capture) != fingerprints:
                raise ValueError('Installed API source changed during validation')
        for name,data in members.items():
            if (session/'inputs/review'/PurePosixPath(name)).read_bytes() != data:
                raise ValueError('Frozen source evidence changed')
        if review.read_bytes() != original or _sha(model.read_bytes()) != preparation['candidate_sha256']:
            raise ValueError('Original archive or candidate changed')
        receipt.update(original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Separate candidate:',model,flush=True)
        print('Descriptive deviations >=5:',json.dumps({k:v['nominal_abs_ge_5'] for k,v in predicted['summary'].items()},sort_keys=True),flush=True)
        print('Diagnostic: REVIEW (native/scientific geometry qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True)
        return 2
    except Exception as exc:
        receipt.update(status='REVIEW',analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved'] = bool(original is not None and review and review.read_bytes() == original)
            if not (session/'probe_receipt.json').exists():
                _json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Fragment restoration stopped:',str(exc),file=sys.stderr,flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
