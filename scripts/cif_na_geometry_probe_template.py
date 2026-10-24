#!/usr/bin/env python3
"""Run one bounded geometry trial under the verified fixed NARestraints policy."""
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
REVIEW_SHA256 = 'f8162ed4d2ee548131a6b248e85fb59c12916ca52644ae66b15572b78e32700d'
CAPTURE_PREFIX = 'native_saved_endpoint/cif-native-nd_9eaqz'
INITIAL_PREFIX = 'native_initial/cif-native-eoq5ilbf'
ORIGINAL_PREFIX = 'inputs/review/native_roundtrip/cif-native-wlhcmfyc'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_na_geometry_review.zip')
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
    from collections import Counter
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 21 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):
            raise ValueError('Unsafe or duplicate review member')
        manifest=json.loads(archive.read('manifest.json'))
        if set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=491:
            raise ValueError('Unexpected Cedar 21 payload inventory')
        members={e.filename:archive.read(e) for e in entries}
        for name,row in manifest.items():
            if len(members[name])!=row['bytes'] or _sha(members[name])!=row['sha256']:
                raise ValueError('Review payload integrity mismatch')
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-na-policy-native-probe' or prior.get('delivery_prefix')!='21_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('model_editing')!='NOT_RUN' or prior.get('automatic_adoption') is not False
            or prior.get('membership_invariant') is not True or prior.get('policy_authority')!='NARestraints'):
        raise ValueError('Require completed preserved Cedar 21 policy membership evidence')
    if prior['compiled_policy']!=json.loads(members['policy_report.json']):raise ValueError('Inconsistent frozen policy report')
    if set(prior['native_cases'])!={'initial','saved_endpoint'}:raise ValueError('Require both verified membership cases')
    for name,prefix in [('initial',INITIAL_PREFIX),('saved_endpoint',CAPTURE_PREFIX)]:
        case=prior['native_cases'][name];capture=case['native'];mechanics=case['mechanics']
        if (capture!=json.loads(members[prefix+'/native_receipt.json']) or capture.get('status')!='REVIEW'
                or capture.get('execution',{}).get('status')!='COMPLETED' or capture['execution'].get('returncode')!=0
                or capture.get('source_preserved') is not True or capture.get('frozen_inputs_preserved') is not True
                or capture['native_validation']!=json.loads(members[prefix+'/native_validation.json'])):
            raise ValueError('Inconsistent completed native policy interpretation')
        if (mechanics!=json.loads(members[name+'_mechanics.json']) or mechanics.get('mechanics_checks_pass') is not True
                or Counter(c['status'] for c in mechanics['checks'])!={'PASS':14}
                or len({c['check'] for c in mechanics['checks']})!=14):
            raise ValueError('Unresolved native membership prerequisite')
        if Counter(r['role'] for r in capture['inputs'])!={'model':1,'dictionary':19,'phil':13}:
            raise ValueError('Unexpected native policy input roles')
        for row in capture['inputs']+capture['outputs']:
            if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsupported native anchor')
            payload=members[prefix+'/'+row['path']]
            if len(payload)!=row['size'] or _sha(payload)!=row['sha256']:raise ValueError('Native artifact mismatch')
        phils=[r for r in capture['inputs'] if r['role']=='phil']
        policy=prior['compiled_policy'];sources=policy['retained_phils']+[policy['compiled_phil']]
        if len(phils)!=len(sources):raise ValueError('Unexpected compiled policy inputs')
        for row,source in zip(phils,sources):
            if not _safe(source) or members[prefix+'/'+row['path']]!=members['policy/'+source]:
                raise ValueError('Native input differs from frozen compiled policy')
    endpoint=prior['native_cases']['saved_endpoint']['native']
    baseline=prior['native_cases']['initial']['native']
    invariant=lambda c:[(r['role'],r['sha256'],r['size']) for r in c['inputs'] if r['role']!='model']
    if invariant(endpoint)!=invariant(baseline):raise ValueError('Membership cases used different fixed definitions')
    # Retain every earlier payload and its manifest, including the old REVIEW.
    frozen=json.loads(members['inputs/review/manifest.json'])
    if len(frozen)!=367:raise ValueError('Incomplete preserved Cedar 20 evidence')
    for name,row in frozen.items():
        if not _safe(name):raise ValueError('Unsafe prior evidence anchor')
        payload=members['inputs/review/'+name]
        if len(payload)!=row['bytes'] or _sha(payload)!=row['sha256']:raise ValueError('Preserved prior evidence changed')
    return members,prior,endpoint,original


def _run_trial(session,capture,phenix,iterations,timeout,receipt):
    from nasolve.cif_fixed_geometry import (run_fixed_geometry,write_geometry_candidate,
        review_fixed_coordinates,qualify_fixed_policy_geometry)
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_captured_geometry import review_captured_geometry
    root=session/'inputs/review'/CAPTURE_PREFIX
    def paths(role):return [root/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
    model=paths('model')[0];cifs=paths('dictionary');phils=paths('phil');before=capture['native_validation']
    _json(session/'initial_geometry_review.json',review_captured_geometry(before))
    print('Matching the verified NARestraints manager before one bounded geometry-only trial.',flush=True)
    receipt.update(native_execution='ATTEMPTED',model_optimization='EXPLICIT_BOUNDED_TRIAL')
    trial=run_fixed_geometry(model,cifs,phils,before,session/'geometry_trial',phenix.executables['phenix.python'],
        environment=phenix.environment,phenix_version=phenix.version,max_iterations=iterations,
        timeout_seconds=timeout,policy_inventory=True)
    receipt['geometry_trial']=trial;receipt['native_execution']=trial['execution']['status']
    if trial['status']!='REVIEW':raise ValueError('NA policy geometry trial did not complete; inspect retained worker evidence')
    result=trial['result'];receipt['convergence']=trial['convergence']
    candidate=session/'candidate/na_policy_geometry_model.pdb'
    serialization=write_geometry_candidate(model,candidate,before,result['final_sites_cart'])
    receipt['serialization']=serialization;_json(session/'serialization_review.json',serialization)
    full=review_fixed_coordinates(before,result['final_sites_cart'])
    _json(session/'full_precision_geometry_review.json',full)
    print('Checking serialized candidate identities, definitions and every fixed policy proxy.',flush=True)
    after=inspect_native_bundle(candidate,cifs,session/'native_roundtrip',phenix.executables['phenix.python'],
        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=timeout,
        phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True)
    receipt['native_roundtrip']=after;receipt['native_execution']=after['execution']['status']
    if after['status']!='REVIEW' or after['execution'].get('returncode')!=0:
        raise ValueError('Serialized candidate did not complete native interpretation')
    mechanics=qualify_fixed_policy_geometry(before,after['native_validation'],candidate,serialization)
    receipt['native_mechanics']=mechanics;_json(session/'native_mechanics.json',mechanics)
    if not mechanics['mechanics_checks_pass']:raise ValueError('Geometry candidate changed native identities, definitions, proxies or policy')
    rounded=review_captured_geometry(after['native_validation'])
    _json(session/'rounded_native_geometry_review.json',rounded)
    receipt['geometry_summaries']={'full_precision':full['summary'],'serialized_native':rounded['summary']}
    if _sha(candidate.read_bytes())!=serialization['candidate_sha256']:raise ValueError('Geometry candidate changed')
    receipt['native_execution']='COMPLETED'
    print('Native mechanics checks: PASS',flush=True)
    print('Stopping evidence:',trial['convergence'],'('+result['stopping']['reason']+')',flush=True)
    print('Fixed-policy target:',result['initial']['target'],'->',result['final']['target'],flush=True)
    print('Gradient norm:',result['initial']['gradient_norm'],'->',result['final']['gradient_norm'],flush=True)
    print('Separate candidate:',candidate,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/21_Cedar_cif-na-policy-jh154g91/21_Cedar_jh154g91_cif_na_policy_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--max-iterations',type=int,default=1000)
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None;members=None
    receipt={'schema_version':1,'kind':'cif-na-policy-geometry-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'SEPARATE_CANDIDATE_ONLY','model_optimization':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN',
        'automatic_adoption':False,'diffraction_data':'NOT_READ','policy_authority':'NARestraints','convergence':'NOT_ASSESSED',
        'limits':{'max_iterations':args.max_iterations,'max_calls':args.max_iterations*20,'timeout_seconds':args.timeout_seconds}}
    try:
        if not 1<=args.max_iterations<=1000 or not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid iteration or timeout bound')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,capture,original=_read_capsule(review)
        parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-na-geometry-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_na_policy import qualify_na_policy
        original_native=json.loads(members[ORIGINAL_PREFIX+'/native_validation.json'])
        replay={name:qualify_na_policy(original_native,case['native']['native_validation'],prior['compiled_policy'])
            for name,case in prior['native_cases'].items()}
        if any(value!=prior['native_cases'][name]['mechanics'] or not value['mechanics_checks_pass'] for name,value in replay.items()):
            raise ValueError('Verified native membership evidence does not replay')
        _json(session/'prerequisite_membership_replay.json',replay)
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':491},
            prerequisite_membership_replayed=True,selected_case='saved_endpoint',
            selected_native_receipt={'anchor':'probe_directory','path':'inputs/review/'+CAPTURE_PREFIX+'/native_receipt.json'},
            prior_convergence=prior.get('prior_convergence'),objective=prior['objective'],limitations=[
                'One separate geometry-only trial under the verified NARestraints policy; source dictionaries and PHIL remain fixed.',
                'No pair guessing, policy recompilation, dictionary generation, diffraction refinement or automatic adoption.',
                'Only this new objective is compared within the trial; Cedar 19/20 energies and iteration-limit outcomes retain their old basis.',
                'Native symmetry/exclusions and dynamic nonbonded neighbours remain active; static proxy equality is checked separately.',
                'Full-precision and PDB-rounded fixed-manager energies/gradients are separate; fresh-manager energies are not equated.',
                'A target decrease or native stopping criterion does not approve full geometry, charge, pucker, absolute stereochemistry or experimental fit.'])
        print('Fixed NARestraints geometry trial:',BUNDLE['delivery_prefix'],flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,capture);receipt['installed_api_sources']=fingerprints
            _run_trial(session,capture,phenix,args.max_iterations,args.timeout_seconds,receipt)
            if _fingerprints(phenix,capture)!=fingerprints:raise ValueError('Installed native API source changed')
        if any((frozen/PurePosixPath(name)).read_bytes()!=data for name,data in members.items()):raise ValueError('Frozen source evidence changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (fixed NA policy geometry trial; scientific qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members is not None and all(
                (session/'inputs/review'/PurePosixPath(n)).is_file() and (session/'inputs/review'/PurePosixPath(n)).read_bytes()==d for n,d in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('NA policy geometry trial stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())


