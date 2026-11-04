#!/usr/bin/env python3
"""Validate explicit outgoing-O3 candidates from the preserved Cedar 12 bundle."""
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
REVIEW_SHA256='19ed5a59b1196f8d329dc18df98dee94d05a6c090ce2fd0064dc3be79a1ec597'
CAPTURE_PREFIX='native_candidate/cif-native-rv4coqxe'
CHAINS={'A':[str(i) for i in range(1,22)],'B':[str(i) for i in range(1,8)],
        'C':[str(i) for i in range(8,15)],'D':[str(i) for i in range(1,8)]}
FREE_FIVE_SITES=['A:1','B:1','C:8','D:1','E:1']
NATIVE_OVERRIDES={'PYTHONPATH','PYTHONHOME','PHENIX','PHENIX_ROOT','PHENIX_VERSION',
    'LIBTBX_BUILD','LIBTBX_DIST','BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data):return hashlib.sha256(data).hexdigest()


def _safe(name):
    return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        p not in {'','.','..'} for p in name.split('/'))


def _json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _runtime_members():
    data=base64.b64decode(RUNTIME_BASE64,validate=True)
    if _sha(data)!=BUNDLE['runtime_archive_sha256']:raise ValueError('Embedded runtime checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries=z.infolist()
        if len(entries)!=len({e.filename for e in entries}) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):
            raise ValueError('Unsafe or duplicate runtime member')
        members={e.filename:z.read(e) for e in entries}
    if set(members)!=set(BUNDLE['runtime_files']):raise ValueError('Runtime inventory mismatch')
    for name,data in members.items():
        if len(data)!=BUNDLE['runtime_files'][name]['size'] or _sha(data)!=BUNDLE['runtime_files'][name]['sha256']:
            raise ValueError('Runtime file integrity mismatch')
    return members


def _materialize(members,names,target):
    for name in sorted(set(names)):
        if not _safe(name) or name not in members:raise ValueError('Missing explicit capsule member: '+name)
        path=target/PurePosixPath(name);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle:handle.write(members[name])


def _read_capsule(path,expected_sha=REVIEW_SHA256):
    original=path.read_bytes()
    if _sha(original)!=expected_sha:raise ValueError('Require the exact hash-bound 12_Cedar review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries];manifest=json.loads(z.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=116:
            raise ValueError('Unexpected 12_Cedar payload inventory')
        members={}
        for entry in entries:
            name=entry.filename
            if not _safe(name) or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe review path')
            data=z.read(entry)
            if name!='manifest.json' and (len(data)!=manifest[name]['bytes'] or _sha(data)!=manifest[name]['sha256']):
                raise ValueError('Review payload integrity mismatch')
            members[name]=data
    prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-terminal-bundle-probe' or prior.get('delivery_prefix')!='12_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('original_archives_preserved')!={'09_Cedar':True,'11_Cedar':True}):
        raise ValueError('Require the completed preserved Cedar 12 bundle receipt')
    return members,prior,original


def _freeze_inputs(session,path):
    from nasolve.cif_linked_qualification import declared_linear_links
    members,prior,original=_read_capsule(path)
    capture=json.loads(members[CAPTURE_PREFIX+'/native_receipt.json'])
    names={CAPTURE_PREFIX+'/native_receipt.json'}
    for record in capture['inputs']+capture['outputs']:
        if record.get('anchor')!='native_directory' or not _safe(record.get('path')):
            raise ValueError('Unsupported captured native anchor/path')
        names.add(CAPTURE_PREFIX+'/'+record['path'])
    _materialize(members,names,session/'inputs/review')
    qualification=json.loads(members['bundle_qualification.json'])
    if qualification!=prior.get('qualification'):raise ValueError('Prior qualification receipt disagrees')
    findings=[r for r in qualification['checks'] if r['check'].startswith('declared-outgoing-oxygen-hydrogens:') and r['status']=='REVIEW']
    native=capture['native_validation'];mappings={r['site']:r for r in native['monomer_mappings']['rows']}
    links=declared_linear_links(CHAINS);incoming={b:a for a,b in links};outgoing=dict(links)
    selected=[r['check'].split(':',1)[1] for r in findings]
    if len(selected)!=4 or len(set(selected))!=4:raise ValueError('Unexpected returned outgoing-hydrogen scope')
    codes={mappings[s]['resname'] for s in selected}
    contexts={code:[{'site':site,'incoming_site':incoming.get(site),'outgoing_site':outgoing.get(site),
        'five_prime_state':'linked' if site in incoming else 'free_OH' if site in FREE_FIVE_SITES else 'phosphate',
        'three_prime_state':'linked' if site in outgoing else 'free_OH'}
        for site,row in mappings.items() if row['resname']==code] for code in sorted(codes)}
    prior_evidence=json.loads(members['prior_evidence.json'])
    manifest=json.loads(members['manifest.json'])
    state={'prior_archive':{'sha256':REVIEW_SHA256,'bytes':len(original),'verified_payloads':116,'materialized_payloads':len(names)},
        'prior_build':{k:prior['build'][k] for k in ['nasolve_source','narestraints_source']},
        'installed_terminal_authorities':prior['installed_terminal_authorities'],
        'existing_preparations':[prior['terminal_preparation'],*prior_evidence['other_preparations']],
        'selected_sites':sorted(selected),'contexts':contexts,'links':links,
        'capture_receipt':CAPTURE_PREFIX+'/native_receipt.json','authority_site':'A:4',
        'frozen_members':{name:manifest[name] for name in sorted(names)}}
    _json(session/'prior_evidence.json',state)
    return state,original


def _verify_frozen_inputs(session,state):
    for name,record in state['frozen_members'].items():
        path=session/'inputs/review'/PurePosixPath(name)
        if path.is_symlink() or not path.resolve().is_relative_to((session/'inputs/review').resolve()):
            raise ValueError('Frozen bundle input escaped its declared anchor')
        data=path.read_bytes()
        if len(data)!=record['bytes'] or _sha(data)!=record['sha256']:
            raise ValueError('Frozen bundle input changed: '+name)


def _prepare_candidate(session,state):
    from nasolve.cif_linked_preparation import component_values
    from nasolve.cif_outgoing_preparation import prepare_outgoing_component
    receipt_path=session/'inputs/review'/state['capture_receipt'];capture=json.loads(receipt_path.read_text())
    def paths(role):return [receipt_path.parent/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
    models=paths('model');cifs=paths('dictionary');phils=paths('phil')
    if len(models)!=1 or len(cifs)!=14 or len(phils)!=7:raise ValueError('Unexpected captured bundle input roles')
    model=models[0];preparations=list(state['existing_preparations']);new_preparations=[];projections={}
    for code,contexts in state['contexts'].items():
        sources=[]
        for path in cifs:
            try:component_values(path,code)
            except ValueError:continue
            sources.append(path)
        if len(sources)!=1:raise ValueError('Require one declared curated dictionary definition: '+code)
        directory=session/'preparation'/code
        prepared=prepare_outgoing_component(sources[0],model,contexts,receipt_path,directory,
            code=code,expected_links=state['links'],authority_site=state['authority_site'])
        new_preparations.append(prepared);preparations.append(prepared)
        for plan in prepared['sites']:
            projections[plan['site']]=(directory/('projected_'+plan['site'].replace(':','_')+'.cif'),code)
    if sorted(projections)!=state['selected_sites']:raise ValueError('Candidate changes differ from the returned review scope')
    _verify_frozen_inputs(session,state)
    additions=[session/'preparation'/p['component']/'site_modifications.cif' for p in new_preparations]
    parameters=[session/'preparation'/p['component']/'site_modifications.phil' for p in new_preparations]
    _json(session/'selected_bundle.json',{'schema_version':1,'model':model.relative_to(session).as_posix(),
        'inputs':[{'path':p.relative_to(session).as_posix(),'sha256':_sha(p.read_bytes()),'bytes':p.stat().st_size}
            for p in cifs+additions+phils+parameters],
        'selected_definition_changes':sorted(projections),'original_dictionaries_and_parameters_unchanged':True,
        'automatic_adoption':False})
    return {'model':model,'old_cifs':cifs,'old_phils':phils,'cifs':cifs+additions,'phils':phils+parameters,
        'preparations':preparations,'new_preparations':new_preparations,'projections':projections,
        'capture':capture,'captured_baseline':capture['native_validation']}


def _installation_fingerprints(phenix,state,capture):
    if not phenix.root or phenix.version!=capture['phenix_version']:
        raise ValueError('Selected Phenix differs from the captured outgoing authority')
    executable=phenix.executables.get('phenix.python')
    if not executable or _sha(Path(executable).read_bytes())!=capture['executable_sha256']:
        raise ValueError('Phenix dispatcher changed since the captured bundle')
    historical=Path(capture['executable_provenance']).parent.parent
    records={}
    for row in capture['native_validation']['installed_api_sources']:
        relative=Path(row['historical_path']).relative_to(historical).as_posix()
        records[relative]=row['sha256']
    for row in state['installed_terminal_authorities']:
        if row.get('anchor')!='phenix_installation' or not _safe(row.get('path')):
            raise ValueError('Unsupported terminal-source installation anchor')
        if row['path'] in records and records[row['path']]!=row['sha256']:
            raise ValueError('Conflicting captured native source hashes')
        records[row['path']]=row['sha256']
    result=[]
    for relative,digest in sorted(records.items()):
        path=Path(phenix.root)/relative
        if not path.resolve().is_relative_to(Path(phenix.root).resolve()) or _sha(path.read_bytes())!=digest:
            raise ValueError('Installed outgoing authority changed: '+relative)
        result.append({'anchor':'phenix_installation','path':relative,'sha256':digest})
    return result


def _review_zip(session):
    token=session.name.rsplit('-',1)[-1];destination=session/(BUNDLE['delivery_prefix']+'_'+token+'_cif_outgoing_bundle_review.zip')
    files={}
    for path in sorted(session.rglob('*')):
        if path==destination or path.is_relative_to(session/'runtime'):continue
        if path.is_symlink():raise ValueError('Unexpected output symlink')
        if path.is_file() and path.suffix not in {'.pyc','.pkl','.pickle'}:files[path.relative_to(session).as_posix()]=path.read_bytes()
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({n:{'sha256':_sha(d),'bytes':len(d)} for n,d in files.items()},indent=2))
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/12_Cedar_cif-terminal-bundle-q46plqwk/12_Cedar_q46plqwk_cif_terminal_bundle_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None
    receipt={'schema_version':1,'kind':'cif-outgoing-bundle-native-probe','delivery_prefix':BUNDLE['delivery_prefix'],
        'build':BUNDLE,'automatic_adoption':False,'model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Timeout must be 1-3600 seconds')
        members=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside the preserved diagnostic directory')
        parent.mkdir(parents=True,exist_ok=True);session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-outgoing-bundle-',dir=parent))
        _materialize(members,members,session/'runtime');sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_native_validation import inspect_native_bundle
        from nasolve.cif_outgoing_qualification import qualify_outgoing_bundle
        from nasolve.phenix_runtime import installation_from_candidate
        print('CIF outgoing/bundle diagnostic:',BUNDLE['delivery_prefix'],flush=True)
        state,original=_freeze_inputs(session,review);receipt['prior_archive']=state['prior_archive']
        print('Preparing graph-selected outgoing-O3 candidates; preserving existing sources and modifiers.',flush=True)
        bundle=_prepare_candidate(session,state);receipt['outgoing_preparations']=bundle['new_preparations']
        if args.inspect_only:receipt['status']='PREPARED_REVIEW_NATIVE_NOT_RUN'
        else:
            environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix=installation_from_candidate(args.phenix_root,base_environment=environment)
            fingerprints=_installation_fingerprints(phenix,state,bundle['capture']);receipt['installed_authorities']=fingerprints
            common={'environment':phenix.environment,'phenix_version':phenix.version,'timeout_seconds':args.timeout_seconds,
                'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked'}
            print('Replaying the preserved Cedar 12 candidate as the unchanged baseline.',flush=True)
            before=inspect_native_bundle(bundle['model'],bundle['old_cifs'],session/'native_baseline',phenix.executables['phenix.python'],phil_files=bundle['old_phils'],**common)
            receipt['native_baseline']=before
            print('Interpreting the selected outgoing-oxygen bundle.',flush=True)
            after=inspect_native_bundle(bundle['model'],bundle['cifs'],session/'native_candidate',phenix.executables['phenix.python'],phil_files=bundle['phils'],**common)
            receipt['native_validation']=after
            if before['status']=='REVIEW' and after['status']=='REVIEW':
                report=qualify_outgoing_bundle(before['native_validation'],after['native_validation'],bundle['preparations'],state['links'],
                    FREE_FIVE_SITES,bundle['projections'],captured_baseline=bundle['captured_baseline'],reviewed_torsions={'A:7':'C2e-nyu0'})
                receipt['qualification']=report;receipt['status']=report['status'];_json(session/'bundle_qualification.json',report)
                print('Checks requiring review:',', '.join(c['check'] for c in report['checks'] if c['status']!='PASS'),flush=True)
            else:
                receipt['status']='NATIVE_REVIEW'
                for label,result in [('baseline',before),('candidate',after)]:
                    if result['status']!='REVIEW':
                        print('Native '+label+' requires review:',result.get('error') or result['status'],flush=True)
            if _installation_fingerprints(phenix,state,bundle['capture'])!=fingerprints:raise ValueError('Installed authority changed during validation')
        _verify_frozen_inputs(session,state);receipt['frozen_inputs_preserved']=True
        receipt['original_archive_preserved']=review.read_bytes()==original
        if not receipt['original_archive_preserved']:raise ValueError('Preserved review archive changed')
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic:',receipt['status'],flush=True);print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Dictionary/native mechanics only; no coordinate edits, optimization, refinement or adoption.',flush=True)
        return 0 if receipt['status'] in {'PREPARED_REVIEW_NATIVE_NOT_RUN','OUTGOING_BUNDLE_MECHANICS_PASS'} else 2
    except Exception as exc:
        receipt.update(status='REVIEW',error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            path=session/'probe_receipt.json'
            if not path.exists():_json(path,receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('CIF outgoing/bundle diagnostic stopped:',str(exc),file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':raise SystemExit(main())
