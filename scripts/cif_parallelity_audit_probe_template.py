#!/usr/bin/env python3
"""Isolate installed native plane gradients and accumulation without optimization."""
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
REVIEW_SHA256 = '8acd86fcac72db6380f40f6f1b3851eabe12b9a6267be750bf97e482a11509bc'
CAPTURE_PREFIX = 'native_gradients/cif-gradient-audit-ilzjo7_w'
GEOMETRY_PREFIX = 'geometry_trial/cif-fixed-geometry-t2c9xuw6'
READBACK_PREFIX = 'native_roundtrip/cif-native-wd459r67'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_parallelity_audit_review.zip')
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


def _fingerprints(phenix,capture):
    if not phenix.root or phenix.version!=capture['phenix_version']:
        raise ValueError('Selected Phenix differs from captured native version')
    executable=phenix.executables.get('phenix.python')
    if not executable or _sha(Path(executable).read_bytes())!=capture['executable_sha256']:
        raise ValueError('Phenix dispatcher changed since the captured bundle')
    historical=Path(capture['executable_provenance']).parent.parent;rows=[]
    for row in capture['native_validation']['installed_api_sources']:
        relative=Path(row['historical_path']).relative_to(historical).as_posix()
        if not _safe(relative):raise ValueError('Unsupported native source anchor')
        path=Path(phenix.root)/relative
        if not path.resolve().is_relative_to(Path(phenix.root).resolve()) or _sha(path.read_bytes())!=row['sha256']:
            raise ValueError('Installed native API source changed')
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':row['sha256']})
    return rows


def _verify_manifest(members, count):
    manifest=json.loads(members['manifest.json'])
    if set(members)!=set(manifest)|{'manifest.json'} or len(manifest)!=count:
        raise ValueError('Unexpected preserved payload inventory')
    for name,row in manifest.items():
        if not _safe(name) or len(members[name])!=row['bytes'] or _sha(members[name])!=row['sha256']:
            raise ValueError('Preserved payload integrity mismatch')


def _native_artifacts(members, receipt, prefix, *, bytecode_excluded=False):
    from collections import Counter
    if (receipt.get('status')!='REVIEW' or receipt.get('execution',{}).get('status')!='COMPLETED'
            or receipt['execution'].get('returncode')!=0 or not receipt.get('source_preserved') or not receipt.get('frozen_inputs_preserved')):
        raise ValueError('Incomplete captured native execution')
    if Counter(row['role'] for row in receipt['inputs'])!={'model':1,'dictionary':19,'phil':13}:
        raise ValueError('Unexpected frozen native input roles')
    for row in receipt['inputs']+receipt['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported native artifact anchor')
        name=prefix+'/'+row['path']
        if bytecode_excluded and name not in members and row in receipt['outputs'] and Path(row['path']).suffix=='.pyc':
            continue
        if name not in members or len(members[name])!=row['size'] or _sha(members[name])!=row['sha256']:
            raise ValueError('Captured native artifact mismatch')


def _read_capsule(path, expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):
        raise ValueError('Require the exact verified Cedar 23 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):
            raise ValueError('Unsafe or duplicate review member')
        members={e.filename:archive.read(e) for e in entries}
    _verify_manifest(members,670)
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-native-gradient-audit-probe' or prior.get('delivery_prefix')!='23_Cedar'
            or prior.get('analysis_completed') is not True or prior.get('status')!='REVIEW'
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('automatic_adoption') is not False or prior.get('prior_convergence')!='NOT_CONVERGED_ERROR'
            or prior.get('prerequisite_mechanics_replayed') is not True or prior.get('policy_authority')!='NARestraints'):
        raise ValueError('Require preserved completed Cedar 23 evidence')
    audit=prior['native_gradient_audit'];result=audit['result']
    _native_artifacts(members,audit,CAPTURE_PREFIX,bytecode_excluded=True)
    if audit!=json.loads(members[CAPTURE_PREFIX+'/gradient_receipt.json']) or result!=json.loads(members[CAPTURE_PREFIX+'/gradient_result.json']):
        raise ValueError('Inconsistent captured gradient receipt/result')
    if (result.get('policy_id')!='cif-fixed-native-gradient-audit-v1' or result.get('status')!='REVIEW'
            or not result.get('analysis_completed') or not result.get('captured_inventory_matches')
            or result.get('model_optimization')!='NOT_RUN' or result.get('automatic_adoption') is not False
            or set(result.get('cases',{}))!={'full_precision','pdb_rounded'} or not 0<result.get('evaluation_calls',0)<=4000
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')):
        raise ValueError('Incomplete gradient audit prerequisite')
    frozen={name.removeprefix('inputs/review/'):data for name,data in members.items() if name.startswith('inputs/review/')}
    _verify_manifest(frozen,609)
    geometry=json.loads(frozen['probe_receipt.json']);trial=geometry['geometry_trial'];readback=geometry['native_roundtrip']
    if (geometry.get('kind')!='cif-na-policy-geometry-probe' or geometry.get('delivery_prefix')!='22_Cedar'
            or geometry.get('convergence')!='NOT_CONVERGED_ERROR' or not geometry.get('analysis_completed')
            or geometry.get('automatic_adoption') is not False or not geometry.get('original_archive_preserved')
            or not geometry.get('frozen_inputs_preserved')):
        raise ValueError('Invalid preserved Cedar 22 prerequisite')
    for receipt,prefix in [(trial,GEOMETRY_PREFIX),(readback,READBACK_PREFIX)]:
        _native_artifacts(frozen,receipt,prefix)
    if (trial!=json.loads(frozen[GEOMETRY_PREFIX+'/geometry_receipt.json'])
            or trial['result']!=json.loads(frozen[GEOMETRY_PREFIX+'/geometry_result.json'])
            or readback!=json.loads(frozen[READBACK_PREFIX+'/native_receipt.json'])
            or readback['native_validation']!=json.loads(frozen[READBACK_PREFIX+'/native_validation.json'])):
        raise ValueError('Inconsistent preserved trial evidence')
    mechanics=geometry['native_mechanics']
    if (mechanics!=json.loads(frozen['native_mechanics.json']) or not mechanics.get('mechanics_checks_pass')
            or len(mechanics['checks'])!=17 or any(c['status']!='PASS' for c in mechanics['checks'])
            or len({c['check'] for c in mechanics['checks']})!=17):
        raise ValueError('Unresolved native mechanics prerequisite')
    expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json'])
    if expected!=json.loads(frozen[GEOMETRY_PREFIX+'/expected_inventory.json']):
        raise ValueError('Gradient manager is not the frozen trial manager')
    fields=['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']
    for snapshot in [json.loads(members[CAPTURE_PREFIX+'/native_validation.json']),json.loads(frozen[GEOMETRY_PREFIX+'/native_validation.json'])]:
        if any(snapshot.get(k)!=expected.get(k) for k in fields):
            raise ValueError('Saved manager differs from expected inventory')
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs']]
    if signature(audit)!=signature(trial):
        raise ValueError('Gradient audit changed frozen native inputs')
    coordinates={'full_precision':trial['result']['final_sites_cart'],
                 'pdb_rounded':[[float('%.3f'%v) for v in p] for p in trial['result']['final_sites_cart']]}
    spec=json.loads(members[CAPTURE_PREFIX+'/gradient_spec.json'])
    if (spec['coordinate_cases']!=coordinates or spec['expected_numeric_sources']!=result['installed_numeric_sources']
            or result['installed_numeric_sources']!=trial['result']['installed_optimizer_sources']
            or result['constraint_signature_before']!=trial['result']['constraint_signature_before']):
        raise ValueError('Captured coordinates, numerical sources or constraints differ')
    for case in result['cases'].values():
        baseline=case['families']['parallelity']['baseline']
        if len(baseline['gradient'])!=3*expected['atom_count'] or not case['baseline_repeats_consistent'] or not case['captured_snapshot_match']['consistent']:
            raise ValueError('Incomplete captured parallelity baseline')
    return members,prior,geometry,coordinates,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/23_Cedar_cif-gradient-audit-ip09ein6/23_Cedar_ip09ein6_cif_gradient_audit_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;review=None;original=None;members=None
    receipt={'schema_version':1,'kind':'cif-native-parallelity-audit-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
             'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
             'dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN','refinement':'NOT_RUN','diffraction_data':'NOT_READ',
             'scientific_approval':'NOT_RUN','automatic_adoption':False,'policy_authority':'NARestraints'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid native timeout')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,geometry,coordinates,original=_read_capsule(review)
        parent.mkdir(parents=True,exist_ok=True);session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-parallelity-audit-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry,classify_stopping
        from nasolve.cif_parallelity_audit import run_native_parallelity_audit,toy_planes
        expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json']);audit=prior['native_gradient_audit'];result=audit['result']
        candidate=frozen/'inputs/review/candidate/na_policy_geometry_model.pdb'
        mechanics=qualify_fixed_policy_geometry(expected,geometry['native_roundtrip']['native_validation'],candidate,geometry['serialization'])
        if mechanics!=geometry['native_mechanics'] or not mechanics['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        if classify_stopping(geometry['geometry_trial']['result']['stopping'])!='NOT_CONVERGED_ERROR':raise ValueError('Saved stopping evidence does not replay')
        root=frozen/CAPTURE_PREFIX;paths=lambda role:[root/PurePosixPath(row['path']) for row in audit['inputs'] if row['role']==role]
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':670},
                       prior_convergence='NOT_CONVERGED_ERROR',prerequisite_mechanics_replayed=True,
                       parallelity_proxy_count=len(expected['geometry']['proxy_details']['parallelity']),
                       toy_plane_sizes=[[len(row['proxy']['i_seqs']),len(row['proxy']['j_seqs'])] for row in toy_planes()],
                       limitations=['No optimization, target/weight edits or new coordinate model.',
                                    'Native plane-order and singleton-container controls do not change NARestraints policy.',
                                    'Installed source availability does not establish the source used to build the pinned extension binary.',
                                    'Sampled derivative results do not prove why a previous optimizer stalled or establish chemical correctness.'])
        print('Native plane-gradient accumulation audit:',BUNDLE['delivery_prefix'],flush=True)
        print('Captured plane restraints:',receipt['parallelity_proxy_count'],'; testing both orders and equal/unequal tilted controls.',flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            capture={**audit,'native_validation':expected};fingerprints=_fingerprints(phenix,capture)
            numeric_capture={**audit,'native_validation':{'installed_api_sources':result['installed_numeric_sources']}}
            numerical=_fingerprints(phenix,numeric_capture)
            receipt.update(installed_api_sources=fingerprints,installed_numeric_sources=numerical,native_execution='ATTEMPTED')
            native=run_native_parallelity_audit(paths('model')[0],paths('dictionary'),paths('phil'),expected,coordinates,
                {name:case['families']['parallelity']['baseline'] for name,case in result['cases'].items()},
                result['installed_numeric_sources'],result['constraint_signature_before'],session/'native_parallelity',
                phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['native_parallelity_audit']=native;receipt['native_execution']=native['execution']['status']
            if native['status']!='REVIEW':raise ValueError('Native accumulation audit did not complete; inspect retained worker evidence')
            if _fingerprints(phenix,capture)!=fingerprints or _fingerprints(phenix,numeric_capture)!=numerical:raise ValueError('Installed native sources changed')
            receipt['case_summary']={name:case['summary'] for name,case in native['result']['cases'].items()}
            receipt['toy_summary']=native['result']['toy_summary']
            for name,summary in receipt['case_summary'].items():print(name+':',summary,flush=True)
            print('tilted controls:',receipt['toy_summary'],flush=True)
            print('Native single/container evaluation pairs:',native['result']['evaluation_pairs'],'/ 7000',flush=True)
        if review.read_bytes()!=original or any((frozen/PurePosixPath(name)).read_bytes()!=data for name,data in members.items()):raise ValueError('Original or frozen evidence changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (installed per-plane numerical evidence; no optimization or adoption)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(review and original is not None and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members and all((session/'inputs/review'/PurePosixPath(name)).is_file() and (session/'inputs/review'/PurePosixPath(name)).read_bytes()==data for name,data in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Native accumulation audit stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())


