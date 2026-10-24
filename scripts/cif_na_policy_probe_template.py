#!/usr/bin/env python3
"""Validate explicit NARestraints membership on two preserved coordinate sets."""
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
REVIEW_SHA256 = '8d77695925536335963fd351a91961091798ee1a3a680f1bc72368ae9732091e'
CAPTURE_PREFIX = 'native_roundtrip/cif-native-wlhcmfyc'
INITIAL_MODEL = 'inputs/completed_trial/geometry_trial/cif-fixed-geometry-d26rllkv/inputs/000_model.pdb'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_na_policy_review.zip')
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


def _read_capsule(path, expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 20 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries];manifest=json.loads(z.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=367:
            raise ValueError('Unexpected Cedar 20 payload inventory')
        members={}
        for e in entries:
            if not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16):raise ValueError('Unsafe review path')
            data=z.read(e)
            if e.filename!='manifest.json' and (len(data)!=manifest[e.filename]['bytes'] or _sha(data)!=manifest[e.filename]['sha256']):
                raise ValueError('Review payload integrity mismatch')
            members[e.filename]=data
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-fixed-native-geometry-probe' or prior.get('delivery_prefix')!='20_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not False
            or prior.get('original_archive_preserved') is not True or prior.get('native_execution')!='COMPLETED'
            or prior.get('model_optimization')!='REUSED_COMPLETED_TRIAL' or prior.get('automatic_adoption') is not False
            or prior.get('error')!='Geometry candidate changed native identities, definitions or proxies'):
        raise ValueError('Require preserved Cedar 20 serialization/readback evidence')
    from collections import Counter
    if Counter(c['status'] for c in prior['native_mechanics']['checks'])!={'PASS':11,'REVIEW':3}:
        raise ValueError('Unexpected original exact-manager verdict')
    capture=json.loads(members[CAPTURE_PREFIX+'/native_receipt.json'])
    if (capture!=prior['native_roundtrip'] or capture.get('status')!='REVIEW'
            or capture.get('execution',{}).get('returncode')!=0 or not capture.get('source_preserved')
            or not capture.get('frozen_inputs_preserved')
            or capture['native_validation']!=json.loads(members[CAPTURE_PREFIX+'/native_validation.json'])):
        raise ValueError('Inconsistent completed native readback')
    roles=Counter(r['role'] for r in capture['inputs'])
    if roles!={'model':1,'dictionary':19,'phil':12}:raise ValueError('Unexpected native input roles')
    for row in capture['inputs']+capture['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsupported native anchor')
        data=members[CAPTURE_PREFIX+'/'+row['path']]
        if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Native artifact mismatch')
    model=next(r for r in capture['inputs'] if r['role']=='model')
    if members[CAPTURE_PREFIX+'/'+model['path']]!=members['candidate/geometry_trial_model.pdb']:
        raise ValueError('Endpoint serialization differs from interpreted model')
    if INITIAL_MODEL not in members:raise ValueError('Missing declared initial coordinate input')
    return members,prior,capture,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/20_Cedar_cif-geometry-trial-3mgfe_a0/20_Cedar_3mgfe_a0_cif_geometry_trial_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=180)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None
    receipt={'schema_version':1,'kind':'cif-na-policy-native-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN',
        'automatic_adoption':False,'diffraction_data':'NOT_READ','policy_authority':'NARestraints'}
    try:
        if not 1<=args.timeout_seconds<=600:raise ValueError('Invalid native timeout bound')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True)
        parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,capture,original=_read_capsule(review)
        parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-na-policy-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_na_policy import compile_na_policy,qualify_na_policy
        from nasolve.cif_captured_geometry import review_captured_geometry
        root=frozen/CAPTURE_PREFIX
        paths=lambda role:[root/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
        endpoint=paths('model')[0];initial=frozen/INITIAL_MODEL
        print('NARestraints pairing/stacking policy:',BUNDLE['delivery_prefix'],flush=True)
        print('Compiling declared generic pairs/stacks; preserving explicit edits and component modifiers.',flush=True)
        policy=compile_na_policy(endpoint,paths('phil'),capture['native_validation'],session/'policy')
        _json(session/'policy_report.json',policy);receipt['compiled_policy']=policy
        print('Compiled:',policy['pair_count'],'pairs,',policy['stack_count'],'stacks;',policy['request_counts'],flush=True)
        receipt.update(prior_archive={'sha256':REVIEW_SHA256,'bytes':len(original),'verified_payloads':367},
            prior_native_mechanics=prior['native_mechanics'],prior_convergence=prior.get('convergence'),
            selected_models=[{'role':role,'anchor':'probe_directory','path':path.relative_to(session).as_posix(),
                'sha256':_sha(path.read_bytes())} for role,path in [('initial',initial),('saved_endpoint',endpoint)]],
            objective=policy['objective'],limitations=policy['limitations']+[
                'Two interpretation-only mechanics cases with one policy; no new optimization or cross-objective energy ranking.',
                'Source/charge, absolute stereochemistry, pucker, convergence and scientific qualification remain open.'])
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            from nasolve.cif_native_validation import inspect_native_bundle
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,capture);receipt['baseline_api_sources']=fingerprints
            phils=[session/'policy'/p for p in policy['retained_phils']+[policy['compiled_phil']]]
            receipt['native_cases']={};api_sources=None
            for name,model in [('initial',initial),('saved_endpoint',endpoint)]:
                print('Checking exact native membership at',name,'coordinates.',flush=True)
                receipt['native_execution']='ATTEMPTED'
                native=inspect_native_bundle(model,paths('dictionary'),session/('native_'+name),phenix.executables['phenix.python'],
                    environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds,
                    phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True)
                receipt['native_cases'][name]={'native':native};receipt['native_execution']=native['execution']['status']
                if native['status']!='REVIEW' or native['execution'].get('returncode')!=0:raise ValueError('Native policy interpretation did not complete: '+name)
                actual=native['native_validation'];now=_fingerprints(phenix,{**capture,'native_validation':actual})
                if api_sources is not None and now!=api_sources:raise ValueError('Native policy API sources changed between cases')
                api_sources=now
                mechanics=qualify_na_policy(capture['native_validation'],actual,policy)
                geometry=review_captured_geometry(actual)
                receipt['native_cases'][name].update(mechanics=mechanics,descriptive_geometry=geometry)
                _json(session/(name+'_mechanics.json'),mechanics);_json(session/(name+'_geometry.json'),geometry)
                print(name,'mechanics:', 'PASS' if mechanics['mechanics_checks_pass'] else 'REVIEW',flush=True)
            if _fingerprints(phenix,capture)!=fingerprints:raise ValueError('Captured baseline APIs changed')
            if _fingerprints(phenix,{**capture,'native_validation':actual})!=api_sources:raise ValueError('Native policy APIs changed')
            receipt['policy_api_sources']=api_sources
            receipt['membership_invariant']=all(c['mechanics']['mechanics_checks_pass'] for c in receipt['native_cases'].values())
            receipt['native_execution']='COMPLETED'
        for name,data in members.items():
            if (frozen/PurePosixPath(name)).read_bytes()!=data:raise ValueError('Frozen review input changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (explicit policy mechanics; geometry qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('NARestraints policy diagnostic stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
