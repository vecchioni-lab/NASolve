#!/usr/bin/env python3
"""Audit saved native gradients and dictionary/pair evidence without optimization."""
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
REVIEW_SHA256 = '81a4b5cdfea373abcf7bcd740f276545b318134d6f3613ccb701e945dd4476f4'
CAPTURE_PREFIX = 'geometry_trial/cif-fixed-geometry-t2c9xuw6'
NATIVE_PREFIX = 'native_roundtrip/cif-native-wd459r67'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_gradient_audit_review.zip')
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


def _read_capsule(path,expected_sha=None):
    from collections import Counter
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 22 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        manifest=json.loads(archive.read('manifest.json'))
        if set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=609:raise ValueError('Unexpected Cedar 22 payload inventory')
        members={e.filename:archive.read(e) for e in entries}
        for name,row in manifest.items():
            if len(members[name])!=row['bytes'] or _sha(members[name])!=row['sha256']:raise ValueError('Review payload integrity mismatch')
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-na-policy-geometry-probe' or prior.get('delivery_prefix')!='22_Cedar'
            or prior.get('analysis_completed') is not True or prior.get('status')!='REVIEW'
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='EXPLICIT_BOUNDED_TRIAL'
            or prior.get('automatic_adoption') is not False or prior.get('convergence')!='NOT_CONVERGED_ERROR'):
        raise ValueError('Require preserved completed Cedar 22 mechanics and stopping evidence')
    trial=prior['geometry_trial'];result=trial['result'];native=prior['native_roundtrip']
    if (trial!=json.loads(members[CAPTURE_PREFIX+'/geometry_receipt.json']) or result!=json.loads(members[CAPTURE_PREFIX+'/geometry_result.json'])
            or native!=json.loads(members[NATIVE_PREFIX+'/native_receipt.json'])
            or native['native_validation']!=json.loads(members[NATIVE_PREFIX+'/native_validation.json'])):raise ValueError('Inconsistent captured native evidence')
    for receipt,prefix in [(trial,CAPTURE_PREFIX),(native,NATIVE_PREFIX)]:
        if (receipt.get('status')!='REVIEW' or receipt.get('execution',{}).get('status')!='COMPLETED' or receipt['execution'].get('returncode')!=0
                or receipt.get('source_preserved') is not True or receipt.get('frozen_inputs_preserved') is not True):raise ValueError('Native prerequisite did not complete')
        if Counter(r['role'] for r in receipt['inputs'])!={'model':1,'dictionary':19,'phil':13}:raise ValueError('Unexpected native input roles')
        for row in receipt['inputs']+receipt['outputs']:
            if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsupported native artifact anchor')
            payload=members[prefix+'/'+row['path']]
            if len(payload)!=row['size'] or _sha(payload)!=row['sha256']:raise ValueError('Native artifact mismatch')
    if (not result.get('captured_inventory_matches') or result.get('policy_inventory') is not True
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')
            or result['stopping'].get('native_criterion_met') is not False or not result['stopping'].get('error')):
        raise ValueError('Incomplete fixed-manager or stopping evidence')
    mechanics=prior['native_mechanics']
    if (mechanics!=json.loads(members['native_mechanics.json']) or mechanics.get('mechanics_checks_pass') is not True
            or len(mechanics['checks'])!=17 or any(c['status']!='PASS' for c in mechanics['checks'])
            or len({c['check'] for c in mechanics['checks']})!=17):raise ValueError('Unresolved native mechanics prerequisite')
    expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json'])
    actual=json.loads(members[CAPTURE_PREFIX+'/native_validation.json'])
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Saved manager does not match expected inventory')
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs'] if r['role']!='model']
    if signature(trial)!=signature(native):raise ValueError('Readback used different fixed definitions')
    frozen=json.loads(members['inputs/review/manifest.json'])
    if len(frozen)!=491:raise ValueError('Incomplete preserved Cedar 21 evidence')
    for name,row in frozen.items():
        if not _safe(name):raise ValueError('Unsafe frozen evidence anchor')
        data=members['inputs/review/'+name]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Prior evidence changed')
    return members,prior,trial,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/22_Cedar_cif-na-geometry-nnvwx71c/22_Cedar_nnvwx71c_cif_na_geometry_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;review=None;original=None;members=None
    receipt={'schema_version':1,'kind':'cif-native-gradient-audit-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN','refinement':'NOT_RUN','diffraction_data':'NOT_READ',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'policy_authority':'NARestraints'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid native timeout')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,trial,original=_read_capsule(review);parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-gradient-audit-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry,classify_stopping
        from nasolve.cif_gradient_audit import review_distance_groups,run_native_gradient_audit
        from nasolve.cif_doctor import assess_dictionaries
        expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json']);result=trial['result']
        after=prior['native_roundtrip']['native_validation'];candidate=frozen/'candidate/na_policy_geometry_model.pdb'
        mechanics=qualify_fixed_policy_geometry(expected,after,candidate,prior['serialization'])
        if mechanics!=prior['native_mechanics'] or not mechanics['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        if classify_stopping(result['stopping'])!=prior['convergence']:raise ValueError('Saved stopping evidence does not replay')
        root=frozen/CAPTURE_PREFIX
        paths=lambda role:[root/PurePosixPath(r['path']) for r in trial['inputs'] if r['role']==role]
        full=result['final_sites_cart'];rounded=[[float('%.3f'%v) for v in p] for p in full]
        groups=review_distance_groups(expected,full);_json(session/'distance_group_review.json',groups)
        dictionaries=assess_dictionaries(paths('dictionary'),stage='saved-fixed-native-gradient-audit')
        _json(session/'dictionary_review.json',dictionaries)
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':609},
            prior_convergence=prior['convergence'],prerequisite_mechanics_replayed=True,
            distance_group_summary={'groups':len(groups['groups']),'selected_indices':groups['selected_indices'],'selected_labels':groups['selected_labels']},
            dictionary_review_status=dictionaries['status'],limitations=[
                'Two saved coordinate cases, fixed inputs and sampled native derivative evaluations only; no optimization or new candidate.',
                'Individual-family flags are diagnostic controls; full NARestraints policy remains fixed and no alternative objective is adopted.',
                'Finite-difference step/tolerance evidence is separate from unchanged exact native mechanics checks.',
                'Agreement in sampled directions does not prove every gradient component, convergence, chemistry or experimental fit.'])
        print('Saved native gradient audit:',BUNDLE['delivery_prefix'],flush=True)
        print('Frozen distance groups:',len(groups['groups']),'; probing',len(groups['selected_indices']),'outlier-selected atoms.',flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            capture={**trial,'native_validation':expected};fingerprints=_fingerprints(phenix,capture)
            numeric_capture={**capture,'native_validation':{'installed_api_sources':result['installed_optimizer_sources']}}
            numerical=_fingerprints(phenix,numeric_capture);receipt.update(installed_api_sources=fingerprints,installed_numeric_sources=numerical,native_execution='ATTEMPTED')
            audit=run_native_gradient_audit(paths('model')[0],paths('dictionary'),paths('phil'),expected,
                {'full_precision':full,'pdb_rounded':rounded},{'full_precision':result['final'],'pdb_rounded':result['serialized']},
                groups['selected_indices'],result['installed_optimizer_sources'],result['constraint_signature_before'],
                session/'native_gradients',phenix.executables['phenix.python'],environment=phenix.environment,
                phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['native_gradient_audit']=audit;receipt['native_execution']=audit['execution']['status']
            if audit['status']!='REVIEW':raise ValueError('Native gradient audit did not complete; inspect retained worker evidence')
            if _fingerprints(phenix,capture)!=fingerprints or _fingerprints(phenix,numeric_capture)!=numerical:raise ValueError('Installed native sources changed')
            receipt['gradient_case_summary']={name:{'sampled_gradients_consistent':case['sampled_gradients_consistent'],
                'families_requiring_review':[f for f,v in case['families'].items() if not v['sampled_directions_consistent']],
                'baseline_repeats_consistent':case['baseline_repeats_consistent'],'captured_snapshot_match':case['captured_snapshot_match']['consistent'],
                'target_additivity':case['target_additivity']['consistent'],'gradient_additivity':case['gradient_additivity']['consistent']}
                for name,case in audit['result']['cases'].items()}
            for name,summary in receipt['gradient_case_summary'].items():print(name+':',summary,flush=True)
            print('Native energy evaluations:',audit['result']['evaluation_calls'],'/ 4000',flush=True)
        if any((frozen/PurePosixPath(name)).read_bytes()!=data for name,data in members.items()):raise ValueError('Frozen review inputs changed')
        if review.read_bytes()!=original:raise ValueError('Original archive changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (sampled numerical/dictionary evidence; no optimization or adoption)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(review and original is not None and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members and all((session/'inputs/review'/PurePosixPath(n)).is_file() and (session/'inputs/review'/PurePosixPath(n)).read_bytes()==d for n,d in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Native gradient audit stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())


