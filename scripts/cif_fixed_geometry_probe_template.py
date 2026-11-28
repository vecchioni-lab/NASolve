#!/usr/bin/env python3
"""A fixed-definition geometry-only trial from the verified Cedar 18 capsule."""
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
REVIEW_SHA256 = '8c049215a46f3f1fe0c628b7e2552e6aa59f4149853285edf5e208d72e813146'
CAPTURE_PREFIX = 'native_fragment/cif-native-418b76gi'
COMPLETED_TRIAL_SHA256 = 'efec1713eaa05b51568ff6135cfac1cf649f6907fc4fb49c51b59fa8e1d2cebd'
COMPLETED_TRIAL_PREFIX = 'geometry_trial/cif-fixed-geometry-d26rllkv'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_geometry_trial_review.zip')
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
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 18 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries];manifest=json.loads(z.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=252:
            raise ValueError('Unexpected Cedar 18 payload inventory')
        members={}
        for e in entries:
            if not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16):raise ValueError('Unsafe review path')
            data=z.read(e)
            if e.filename!='manifest.json' and (len(data)!=manifest[e.filename]['bytes'] or _sha(data)!=manifest[e.filename]['sha256']):
                raise ValueError('Review payload integrity mismatch')
            members[e.filename]=data
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-effective-source-recovery-probe' or prior.get('delivery_prefix')!='18_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or not prior.get('original_archive_preserved') or not prior.get('frozen_inputs_preserved')
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('automatic_adoption') is not False):raise ValueError('Require completed preserved Cedar 18 evidence')
    for name in ['dictionary_qualification','fragment_mechanics']:
        evidence=json.loads(members[name+'.json'])
        if evidence!=prior.get(name) or not evidence.get('checks'):raise ValueError('Inconsistent prerequisite checks')
        for check in evidence['checks']:
            allowed=(name=='dictionary_qualification' and check.get('status')=='UNSUPPORTED'
                and check.get('check','').startswith('effective-site-formal-charges:') and not check.get('contradictions'))
            if check.get('status')!='PASS' and not allowed:raise ValueError('Unresolved prerequisite mechanics')
    if prior['fragment_mechanics'].get('mechanics_checks_pass') is not True:raise ValueError('Fragment mechanics did not pass')
    capture=json.loads(members[CAPTURE_PREFIX+'/native_receipt.json'])
    if capture!=prior.get('native_fragment') or capture.get('native_validation')!=json.loads(members[CAPTURE_PREFIX+'/native_validation.json']):
        raise ValueError('Inconsistent captured native manager')
    if capture.get('status')!='REVIEW' or capture.get('execution',{}).get('status')!='COMPLETED' or capture['execution'].get('returncode')!=0:
        raise ValueError('Require completed native fragment interpretation')
    if not capture.get('source_preserved') or not capture.get('frozen_inputs_preserved'):raise ValueError('Captured inputs were not preserved')
    roles=[r['role'] for r in capture['inputs']]
    if roles.count('model')!=1 or roles.count('dictionary')!=19 or roles.count('phil')!=12 or len(roles)!=32:
        raise ValueError('Unexpected fixed bundle roles')
    for row in capture['inputs']+capture['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsupported native artifact anchor')
        data=members[CAPTURE_PREFIX+'/'+row['path']]
        if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Native artifact integrity mismatch')
    return members,prior,capture,original



def _read_completed_trial(path,prior_members,capture,expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or COMPLETED_TRIAL_SHA256):raise ValueError('Require the exact Cedar 19 completed-trial capsule')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries];manifest=json.loads(z.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=310:
            raise ValueError('Unexpected completed-trial payload inventory')
        members={}
        for e in entries:
            if not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16):raise ValueError('Unsafe completed-trial path')
            data=z.read(e)
            if e.filename!='manifest.json' and (len(data)!=manifest[e.filename]['bytes'] or _sha(data)!=manifest[e.filename]['sha256']):
                raise ValueError('Completed-trial payload integrity mismatch')
            members[e.filename]=data
    for name,data in prior_members.items():
        if members.get('inputs/review/'+name)!=data:raise ValueError('Completed trial has different frozen prior evidence')
    prior=json.loads(members['probe_receipt.json']);prefix=COMPLETED_TRIAL_PREFIX
    trial=json.loads(members[prefix+'/geometry_receipt.json']);result=json.loads(members[prefix+'/geometry_result.json'])
    if (prior.get('kind')!='cif-fixed-native-geometry-probe' or prior.get('delivery_prefix')!='19_Cedar'
            or prior.get('error')!='PDB/native atom ordering differs' or prior.get('analysis_completed') is not False
            or prior.get('original_archive_preserved') is not True or prior.get('automatic_adoption') is not False
            or prior.get('geometry_trial')!=trial or trial.get('result')!=result
            or trial.get('status')!='REVIEW' or trial.get('execution',{}).get('status')!='COMPLETED'
            or trial['execution'].get('returncode')!=0 or not trial.get('source_preserved') or not trial.get('frozen_inputs_preserved')
            or not result.get('captured_inventory_matches') or result.get('status')!='REVIEW'
            or result.get('automatic_adoption') is not False or result.get('scientific_approval')!='NOT_RUN'
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')):
        raise ValueError('Require the completed fixed-manager trial stopped only at serialization')
    for row in trial['inputs']+trial['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsupported completed-trial artifact anchor')
        data=members[prefix+'/'+row['path']]
        if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Completed-trial artifact integrity mismatch')
    signature=lambda rows:[(r['role'],r['sha256'],r['size']) for r in rows]
    if signature(trial['inputs'])!=signature(capture['inputs']):raise ValueError('Completed trial used different model or restraints')
    expected=json.loads(members[prefix+'/expected_inventory.json']);native=json.loads(members[prefix+'/native_validation.json'])
    if expected!=capture['native_validation'] or any(native.get(k)!=expected.get(k) for k in
            ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources']):
        raise ValueError('Completed trial manager differs from captured identities, coordinates, definitions, proxies or APIs')
    if trial.get('phenix_version')!=capture.get('phenix_version') or trial.get('executable_sha256')!=capture.get('executable_sha256'):
        raise ValueError('Completed trial native dispatcher differs')
    return members,trial,original


def _run_trial(session,capture,phenix,iterations,timeout,receipt,completed=None,baseline_root=None):
    from nasolve.cif_fixed_geometry import run_fixed_geometry,write_geometry_candidate,review_fixed_coordinates,FIXED_GEOMETRY_POLICY
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_fragment_restoration import qualify_fragment_restoration
    from nasolve.cif_captured_geometry import review_captured_geometry
    root=(baseline_root if baseline_root is not None else session/'inputs/review')/CAPTURE_PREFIX
    def paths(role):return [root/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
    model=paths('model')[0];cifs=paths('dictionary');phils=paths('phil');before=capture['native_validation']
    _json(session/'baseline_geometry_review.json',review_captured_geometry(before))
    if completed is None:
        print('Rebuilding and matching the captured manager before one bounded geometry-only trial.',flush=True)
        receipt['native_execution']='ATTEMPTED'
        trial=run_fixed_geometry(model,cifs,phils,before,session/'geometry_trial',phenix.executables['phenix.python'],
            environment=phenix.environment,phenix_version=phenix.version,max_iterations=iterations,timeout_seconds=timeout)
        receipt['native_execution']=trial['execution']['status']
    else:
        from nasolve.cif_fixed_geometry import classify_stopping
        print('Serializing the verified saved trial endpoints by exact atom identity.',flush=True)
        trial=completed
        if classify_stopping(trial['result']['stopping'])!=trial['convergence']:
            raise ValueError('Saved trial stopping classification differs')
        receipt['geometry_trial_reused']=True
    receipt['geometry_trial']=trial
    if trial['status']!='REVIEW':raise ValueError('Fixed geometry trial did not complete; inspect retained worker evidence')
    result=trial['result'];receipt['convergence']=trial['convergence']
    candidate=session/'candidate/geometry_trial_model.pdb'
    serialization=write_geometry_candidate(model,candidate,before,result['final_sites_cart'])
    receipt['serialization']=serialization;_json(session/'serialization_review.json',serialization)
    full=review_fixed_coordinates(before,result['final_sites_cart'])
    _json(session/'full_precision_geometry_review.json',full)
    print('Checking the separately written PDB against the same definitions and exact native proxies.',flush=True)
    after=inspect_native_bundle(candidate,cifs,session/'native_roundtrip',phenix.executables['phenix.python'],
        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=timeout,
        phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked')
    receipt['native_roundtrip']=after;receipt['native_execution']=after['execution']['status']
    if after['status']!='REVIEW':raise ValueError('Serialized geometry candidate did not complete native interpretation')
    mechanics=qualify_fragment_restoration(before,after['native_validation'],candidate,serialization)
    mechanics.update(audit_kind='cif_fixed_geometry_native_mechanics',policy_id=FIXED_GEOMETRY_POLICY)
    receipt['native_mechanics']=mechanics;_json(session/'native_mechanics.json',mechanics)
    if not mechanics['mechanics_checks_pass']:raise ValueError('Geometry candidate changed native identities, definitions or proxies')
    if after['native_validation']['installed_api_sources']!=before['installed_api_sources']:
        raise ValueError('Native round-trip API sources changed')
    rounded=review_captured_geometry(after['native_validation']);_json(session/'rounded_native_geometry_review.json',rounded)
    receipt['geometry_summaries']={'full_precision':full['summary'],'serialized_native':rounded['summary']}
    if _sha(candidate.read_bytes())!=serialization['candidate_sha256']:raise ValueError('Geometry candidate changed')
    receipt['native_execution']='COMPLETED'
    print('Native mechanics checks: PASS',flush=True)
    print('Stopping evidence:',trial['convergence'],'('+result['stopping']['reason']+')',flush=True)
    print('Fixed-manager target:',result['initial']['target'],'->',result['final']['target'],flush=True)
    print('Separate candidate:',candidate,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/18_Cedar_cif-source-recovery-pfcyb5kk/18_Cedar_pfcyb5kk_cif_source_recovery_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--completed-trial-zip',type=Path,help='Continue the exact verified Cedar 19 endpoints without another optimization')
    parser.add_argument('--max-iterations',type=int,default=500)
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None;completed_path=None;completed_original=None
    receipt={'schema_version':1,'kind':'cif-fixed-native-geometry-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'SEPARATE_CANDIDATE_ONLY',
        'model_optimization':'NOT_RUN' if args.inspect_only else 'REUSED_COMPLETED_TRIAL' if args.completed_trial_zip else 'EXPLICIT_BOUNDED_TRIAL',
        'dictionary_generation':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'diffraction_data':'NOT_READ','convergence':'NOT_ASSESSED'}
    try:
        if not 1<=args.max_iterations<=1000 or not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid iteration or timeout bound')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,capture,original=_read_capsule(review);completed_members=None;completed=None
        if args.completed_trial_zip:
            completed_path=args.completed_trial_zip.expanduser().resolve(strict=True)
            if parent==completed_path.parent or parent.is_relative_to(completed_path.parent):raise ValueError('Output must be outside completed-trial input directory')
            completed_members,completed,completed_original=_read_completed_trial(completed_path,members,capture)
        parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-geometry-trial-',dir=parent))
        _materialize(runtime,session/'runtime')
        if completed_members is None:
            baseline_root=session/'inputs/review';_materialize(members,baseline_root)
        else:
            _materialize(completed_members,session/'inputs/completed_trial')
            baseline_root=session/'inputs/completed_trial/inputs/review'
            receipt['completed_trial_archive']={'sha256':COMPLETED_TRIAL_SHA256,'bytes':len(completed_original),'verified_payloads':310,
                'receipt':{'anchor':'probe_directory','path':'inputs/completed_trial/'+COMPLETED_TRIAL_PREFIX+'/geometry_receipt.json'}}
        receipt['frozen_review_path']=baseline_root.relative_to(session).as_posix()
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        print('Fixed native CIF geometry trial:',BUNDLE['delivery_prefix'],flush=True)
        receipt.update(prior_archive={'sha256':REVIEW_SHA256,'bytes':len(original),'verified_payloads':252},
            prior_dictionary_qualification=prior['dictionary_qualification'],prior_source_assessments=prior['prior_source_assessments'],
            prior_qualification=prior['prior_qualification'],limitations=[
                'One geometry-only local trial with fixed definitions; no diffraction or scientific approval.',
                'Native nonbonded energy uses installed symmetry/exclusion handling; a separate clash/contact inventory is unassessed.',
                'Formal-charge readback, absolute stereochemistry, pucker, pose and full qualification remain review gates.',
                'A limit, warning or target decrease does not establish convergence; no automatic candidate selection.'])
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,capture);receipt['installed_api_sources']=fingerprints
            _run_trial(session,capture,phenix,args.max_iterations,args.timeout_seconds,receipt,completed=completed,baseline_root=baseline_root)
            if _fingerprints(phenix,capture)!=fingerprints:raise ValueError('Installed native API source changed')
        for name,data in members.items():
            if (baseline_root/PurePosixPath(name)).read_bytes()!=data:raise ValueError('Frozen source evidence changed')
        if completed_members is not None:
            for name,data in completed_members.items():
                if (session/'inputs/completed_trial'/PurePosixPath(name)).read_bytes()!=data:raise ValueError('Frozen completed-trial evidence changed')
            if completed_path.read_bytes()!=completed_original:raise ValueError('Original completed-trial archive changed')
            receipt['completed_trial_archive_preserved']=True
        if review.read_bytes()!=original:raise ValueError('Original review archive changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (fixed-definition geometry trial; scientific qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Fixed geometry trial stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':
    raise SystemExit(main())
