#!/usr/bin/env python3
"""Source-preserving recovery from the verified Cedar 17 native capsule."""
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
REVIEW_SHA256 = '42f6021b1cadb2f26f783b39aa6a999af754f7c486da5df959712cdc2c0630c1'
CAPTURE_PREFIX = 'native_candidate/cif-native-sdthxn7z'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_source_recovery_review.zip')
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
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):
        raise ValueError('Require the exact hash-bound 17_Cedar review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[r.filename for r in entries];manifest=json.loads(z.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=129:
            raise ValueError('Unexpected 17_Cedar payload inventory')
        members={}
        for entry in entries:
            if not _safe(entry.filename) or stat.S_ISLNK(entry.external_attr>>16):
                raise ValueError('Unsafe review path')
            data=z.read(entry)
            if entry.filename!='manifest.json' and (len(data)!=manifest[entry.filename]['bytes'] or _sha(data)!=manifest[entry.filename]['sha256']):
                raise ValueError('Review payload integrity mismatch')
            members[entry.filename]=data
    prior=json.loads(members['probe_receipt.json']);capture=json.loads(members[CAPTURE_PREFIX+'/native_receipt.json'])
    native=json.loads(members[CAPTURE_PREFIX+'/native_validation.json']);mechanics=json.loads(members['native_mechanics.json'])
    if (prior.get('kind')!='cif-fragment-restoration-native-probe' or prior.get('delivery_prefix')!='17_Cedar'
            or prior.get('analysis_completed') is not True or prior.get('status')!='REVIEW'
            or not prior.get('original_archive_preserved') or not prior.get('frozen_inputs_preserved')
            or prior.get('native_validation')!=capture or capture.get('native_validation')!=native
            or capture.get('execution',{}).get('status')!='COMPLETED' or capture['execution'].get('returncode')!=0
            or prior.get('native_mechanics')!=mechanics or not mechanics.get('mechanics_checks_pass')
            or not mechanics.get('checks') or any(c.get('status')!='PASS' for c in mechanics['checks'])):
        raise ValueError('Require the completed preserved Cedar 17 native capture')
    for row in capture['inputs']+capture['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported captured native reference')
        data=members[CAPTURE_PREFIX+'/'+row['path']]
        if len(data)!=row['size'] or _sha(data)!=row['sha256']:
            raise ValueError('Captured native artifact integrity mismatch')
    return members,prior,capture,original


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


def _plan(session,capture,extra_sources):
    from nasolve.cif_effective_source_recovery import plan_effective_source_recovery
    from nasolve.cif_construction_provenance import declared_coot_references
    root=session/'inputs/review';run=root/'inputs/review/inputs/run'
    evidence=json.loads((root/'inputs/review/construction_evidence.json').read_text())
    declarations=declared_coot_references((run/'PostMR/Coot/mutate.py').read_text(),evidence['historical_run_provenance'])
    if declarations!=evidence['saved_script_declarations']:raise ValueError('Saved Coot declarations disagree')
    parents={s:run/PurePosixPath(p) for s,p in declarations['parents'].items()}
    if any(not _safe(p) for p in declarations['parents'].values()):raise ValueError('Unsafe declared parent path')
    audit=json.loads((run/'PostMR/Restraints/cif_doctor_source.json').read_text())
    directory=root/CAPTURE_PREFIX
    def paths(role):return [directory/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
    models,cifs,phils=paths('model'),paths('dictionary'),paths('phil')
    if len(models)!=1 or len(cifs)!=18 or len(phils)!=11:raise ValueError('Unexpected captured bundle roles')
    resources={name:session/'runtime'/PurePosixPath(name) for name in BUNDLE['runtime_files']
        if name.startswith('src/nasolve/data/ligands/') and name.endswith('.cif')}
    for i,value in enumerate(extra_sources):
        code,separator,path=value.partition('=')
        if not separator or not code.isalnum() or not 1<=len(code)<=3:raise ValueError('Source override must be CODE=/explicit/path')
        from nasolve.cif_linked_preparation import component_values
        from nasolve.ligand_profiles import dictionary_component_codes
        explicit=Path(path).expanduser().resolve(strict=True)
        component_values(explicit,code)
        resources={name:p for name,p in resources.items() if code not in dictionary_component_codes(p)}
        resources['explicit/'+code+'/'+str(i)]=explicit
    plan=plan_effective_source_recovery(capture['native_validation'],models[0],audit,resources,list(parents))
    _json(session/'source_recovery_plan.json',plan)
    sources={}
    for item in plan['selected']:
        data=resources[item['source_resource']].read_bytes()
        if len(data)!=item['source_size'] or _sha(data)!=item['source_sha256']:raise ValueError('Matched source changed')
        target=session/'sources'/(item['component']+'_source.cif');target.parent.mkdir(exist_ok=True)
        with target.open('xb') as handle:handle.write(data)
        sources[item['component']]=target
    return {'plan':plan,'model':models[0],'cifs':cifs,'phils':phils,'parents':parents,'sources':sources}


def _run_recovery(session,state,capture,phenix,timeout,receipt):
    from nasolve.cif_generation import generate_elbow_candidate
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.cif_linked_qualification import declared_linear_links
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_terminal_qualification import qualify_terminal_bundle
    from nasolve.cif_effective_source_recovery import mechanics_can_continue,recovery_modifier_check
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration,qualify_fragment_restoration
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.ligand_profiles import dictionary_component_codes
    if state['plan']['blocked'] or not state['plan']['recovery_codes']:
        raise ValueError('Recovery plan is blocked or has no eligible component')
    elbow=phenix.executables.get('phenix.elbow')
    if not elbow or not Path(elbow).resolve().is_relative_to(Path(phenix.root).resolve()):
        raise ValueError('An installation-bound eLBOW is required')
    receipt['elbow_executable_sha256']=_sha(Path(elbow).read_bytes())
    chains={'A':[str(i) for i in range(1,22)],'B':[str(i) for i in range(1,8)],
            'C':[str(i) for i in range(8,15)],'D':[str(i) for i in range(1,8)]}
    links=declared_linear_links(chains);incoming={b:a for a,b in links};outgoing=dict(links)
    free=['A:1','B:1','C:8','D:1','E:1'];prepared=[];projections={};cifs=list(state['cifs']);phils=list(state['phils'])
    for item in state['plan']['selected']:
        code=item['component'];source=state['sources'][code]
        print('Generating a source-preserving whole-component candidate:',code,flush=True)
        receipt['dictionary_generation']='ATTEMPTED'
        generated=generate_elbow_candidate(source,code,session/'generation',elbow,environment=phenix.environment,
            phenix_version=phenix.version,timeout_seconds=timeout)
        receipt.setdefault('generation',{})[code]=generated
        if generated['status']!='CANDIDATE_REVIEW':raise ValueError('Source-preserving generation requires review: '+code)
        candidates=[p for p in cifs if code in dictionary_component_codes(p)]
        if len(candidates)!=1 or dictionary_component_codes(candidates[0])!={code}:
            raise ValueError('Recovery requires one independent component dictionary')
        contexts=[]
        for site in item['sites']:
            if site not in incoming or site not in outgoing:
                raise ValueError('This recovery slice requires explicitly declared internal links')
            contexts.append({'site':site,'incoming_site':incoming[site],'outgoing_site':outgoing[site],
                'five_prime_state':'linked','three_prime_state':'linked'})
        directory=session/'preparation'/code
        prep=prepare_linked_component(source,Path(generated['candidate_directory'])/'candidate.cif',state['model'],contexts,directory,code=code)
        prepared.append(prep);cifs.remove(candidates[0])
        cifs.extend(directory/prep['outputs'][key]['path'] for key in ['dictionary','modifications'])
        phils.append(directory/prep['outputs']['parameters']['path'])
        for site in item['sites']:projections[site]=(directory/('projected_'+site.replace(':','_')+'.cif'),code)
    receipt['linked_preparations']=prepared
    common={'environment':phenix.environment,'phenix_version':phenix.version,'timeout_seconds':timeout,
            'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','phil_files':phils}
    print('Interpreting recovered definitions with unchanged candidate coordinates.',flush=True)
    receipt['native_execution']='ATTEMPTED'
    dictionary_trial=inspect_native_bundle(state['model'],cifs,session/'native_dictionary',phenix.executables['phenix.python'],**common)
    receipt['native_dictionary']=dictionary_trial
    receipt['native_execution']=dictionary_trial['execution']['status']
    if dictionary_trial['status']!='REVIEW':raise ValueError('Recovered dictionary interpretation did not complete')
    check=qualify_terminal_bundle(capture['native_validation'],dictionary_trial['native_validation'],prepared,links,free,projections)
    check['checks'].append(recovery_modifier_check(capture['native_validation'],dictionary_trial['native_validation'],prepared))
    check['status']='REVIEW';receipt['dictionary_qualification']=check
    _json(session/'dictionary_qualification.json',check)
    _json(session/'dictionary_geometry_review.json',review_captured_geometry(dictionary_trial['native_validation']))
    if not mechanics_can_continue(check):raise ValueError('Recovered definitions have unresolved native mechanics checks')
    selected={site:state['parents'][site] for item in state['plan']['selected'] for site in item['sites']}
    run=session/'inputs/review/inputs/review/inputs/run'
    model=session/'candidate/recovered_fragment_model.pdb'
    fragment=prepare_fragment_restoration(run/'PostMR/Model/after_coot_raw.pdb',state['model'],model,
        dictionary_trial['native_validation'],selected)
    receipt['fragment_preparation']=fragment;_json(session/'fragment_preparation.json',fragment)
    print('Interpreting the separately restored fragment with fixed recovered definitions.',flush=True)
    after=inspect_native_bundle(model,cifs,session/'native_fragment',phenix.executables['phenix.python'],**common)
    receipt['native_fragment']=after
    receipt['native_execution']=after['execution']['status']
    if after['status']!='REVIEW':raise ValueError('Recovered fragment interpretation did not complete')
    mechanics=qualify_fragment_restoration(dictionary_trial['native_validation'],after['native_validation'],model,fragment)
    receipt['fragment_mechanics']=mechanics;_json(session/'fragment_mechanics.json',mechanics)
    if not mechanics['mechanics_checks_pass']:raise ValueError('Recovered fragment changed native mechanics')
    geometry=review_captured_geometry(after['native_validation']);_json(session/'native_geometry_review.json',geometry)
    receipt['native_geometry_summary']=geometry['summary'];receipt['native_execution']='COMPLETED'
    if _sha(model.read_bytes())!=fragment['candidate_sha256'] or _sha(Path(elbow).read_bytes())!=receipt['elbow_executable_sha256']:
        raise ValueError('Candidate or selected generator changed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/17_Cedar_cif-fragment-restoration-t9rsj7b2/17_Cedar_t9rsj7b2_cif_fragment_restoration_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--source',action='append',default=[])
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None
    receipt={'schema_version':1,'kind':'cif-effective-source-recovery-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'SEPARATE_CANDIDATE_ONLY',
        'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Timeout must be 1-3600 seconds')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,capture,original=_read_capsule(review);parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-source-recovery-',dir=parent))
        _materialize(runtime,session/'runtime');_materialize(members,session/'inputs/review')
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        print('CIF effective/source recovery:',BUNDLE['delivery_prefix'],flush=True)
        state=_plan(session,capture,args.source);receipt['source_plan']=state['plan']
        receipt.update(prior_archive={'sha256':REVIEW_SHA256,'bytes':len(original),'verified_payloads':129},
            prior_qualification=prior['prior_qualification'],prior_source_assessments=prior['source_assessments'])
        print('Eligible recovery components:',', '.join(state['plan']['recovery_codes']) or '(none)',flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,capture);receipt['installed_api_sources']=fingerprints
            _run_recovery(session,state,capture,phenix,args.timeout_seconds,receipt)
            if _fingerprints(phenix,capture)!=fingerprints:raise ValueError('Installed API source changed')
        for name,data in members.items():
            if (session/'inputs/review'/PurePosixPath(name)).read_bytes()!=data:raise ValueError('Frozen source evidence changed')
        for item in state['plan']['selected']:
            data=state['sources'][item['component']].read_bytes()
            if len(data)!=item['source_size'] or _sha(data)!=item['source_sha256']:raise ValueError('Frozen source resource changed')
        if review.read_bytes()!=original:raise ValueError('Original review archive changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (separate source/fragment candidate; geometry qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(status='REVIEW',analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Effective/source recovery stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':
    raise SystemExit(main())
