#!/usr/bin/env python3
"""Source-preserving linked-state diagnostic from the exact returned Cedar 05 ZIP."""
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
ARCHIVE_SHA256 = '7ab8f0dee87a5490539017e2af006f23b4c989f6794f1670db8db821da9d3db4'
NATIVE_OVERRIDES = {'PYTHONPATH','PYTHONHOME','PHENIX','PHENIX_ROOT','PHENIX_VERSION','LIBTBX_BUILD','LIBTBX_DIST','BOOST_ADAPTBX_FPE_DEFAULT'}
TARGETS = {'IGU':('A:6','A:5','A:7',7), 'IMC':('C:10','C:9','C:11',8),
           'CGY':('A:20','A:19','A:21',2), 'DX':('D:3','D:2','D:4',5)}
CHAINS = {'A':[str(i) for i in range(1,22)],'B':[str(i) for i in range(1,8)],
          'C':[str(i) for i in range(8,15)],'D':[str(i) for i in range(1,8)]}


def _sha(data): return hashlib.sha256(data).hexdigest()


def _json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle:
        json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _safe_name(name):
    return (isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name
            and all(part not in {'','.','..'} for part in name.split('/')))


def _runtime_members():
    data=base64.b64decode(RUNTIME_BASE64,validate=True)
    if _sha(data)!=BUNDLE['runtime_archive_sha256']: raise ValueError('Embedded runtime checksum mismatch')
    members={}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            if not _safe_name(entry.filename) or entry.filename in members or stat.S_ISLNK(entry.external_attr>>16):
                raise ValueError('Unsafe or duplicated runtime member')
            members[entry.filename]=archive.read(entry)
    if set(members)!=set(BUNDLE['runtime_files']): raise ValueError('Runtime member inventory mismatch')
    for name,data in members.items():
        expected=BUNDLE['runtime_files'][name]
        if _sha(data)!=expected['sha256'] or len(data)!=expected['size']: raise ValueError('Runtime input integrity mismatch')
    return members


def _freeze_review(path,session):
    original=path.read_bytes()
    if _sha(original)!=ARCHIVE_SHA256: raise ValueError('Require the exact hash-bound Cedar 05 review ZIP')
    target=session/'baseline'; target.mkdir()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)): raise ValueError('Duplicate review ZIP members')
        manifest=json.loads(archive.read('manifest.json'))
        if set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=57:
            raise ValueError('Unexpected Cedar 05 payload inventory')
        for entry in archive.infolist():
            name=entry.filename
            if not _safe_name(name) or stat.S_ISLNK(entry.external_attr>>16): raise ValueError('Unsafe review ZIP path')
            data=archive.read(entry)
            if name!='manifest.json' and (_sha(data)!=manifest[name]['sha256'] or len(data)!=manifest[name]['bytes']):
                raise ValueError('Review ZIP payload checksum mismatch')
            destination=target/PurePosixPath(name);destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('xb') as handle: handle.write(data)
    return target,original


def _review_zip(session):
    token=session.name.rsplit('-',1)[-1]
    destination=session/(BUNDLE['delivery_prefix']+'_'+token+'_cif_linked_review.zip')
    files={}
    for path in sorted(session.rglob('*')):
        if not path.is_file() or path==destination or path.is_relative_to(session/'runtime'): continue
        if path.is_symlink(): raise ValueError('Unexpected output symlink')
        if path.suffix in {'.pyc','.pkl','.pickle'}: continue
        files[path.relative_to(session).as_posix()]=path.read_bytes()
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({name:{'sha256':_sha(data),'bytes':len(data)} for name,data in files.items()},indent=2))
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/05_Cedar_cif-native-probe-dy4qx3qg/05_Cedar_dy4qx3qg_cif_native_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',default=str(Path.home()/'Applications/phenix-2.2.1-6174'))
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args()
    session=None; original=None
    receipt={'schema_version':1,'kind':'cif-linked-native-probe','build':BUNDLE,
             'delivery_prefix':BUNDLE['delivery_prefix'],'automatic_adoption':False,
             'model_optimization':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN',
             'native_validation':'NOT_RUN','source_recovery':{},'preparations':{},'scientific_approval':'NOT_RUN'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Timeout must be 1–3600 seconds')
        members=_runtime_members()
        path=args.review_zip.expanduser().resolve(strict=True)
        parent=args.output_parent.expanduser().resolve()
        if parent==path.parent or parent.is_relative_to(path.parent):raise ValueError('Output must be outside the original diagnostic directory')
        parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-linked-probe-',dir=parent))
        for name,data in members.items():
            dest=session/'runtime'/PurePosixPath(name);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_generation import inspect_component_generation,generate_elbow_candidate
        from nasolve.cif_linked_preparation import prepare_linked_component
        from nasolve.cif_linked_qualification import declared_linear_links,native_backbone_links,qualify_linked_bundle,site_definition_checks
        from nasolve.cif_native_validation import inspect_native_bundle
        from nasolve.ligand_profiles import dictionary_component_codes,_exclude_components
        from nasolve.phenix_runtime import installation_from_candidate
        print('CIF linked-state diagnostic:',BUNDLE['delivery_prefix'],flush=True)
        baseline,original=_freeze_review(path,session)
        receipt['baseline_archive']={'sha256':ARCHIVE_SHA256,'size':len(original),'verified_payloads':57}
        native_root=baseline/'native/cif-native-90b84f1c'
        old_native=json.loads((native_root/'native_validation.json').read_text())
        expected_links=declared_linear_links(CHAINS)
        if set(native_backbone_links(old_native))!=set(expected_links):raise ValueError('Returned native links differ from declared linear-strand contract')
        model=baseline/'inputs/prepared_model.pdb'
        if model.read_bytes()!=(native_root/'inputs/000_model.pdb').read_bytes():raise ValueError('Baseline model snapshots disagree')
        spec=json.loads((native_root/'native_spec.json').read_text())
        if any(not _safe_name(name) for name in spec['dictionaries']+spec['phil_files']):raise ValueError('Unsafe native bundle input path')
        old_cifs=[native_root/name for name in spec['dictionaries']]
        parameters=[native_root/name for name in spec['phil_files']]
        for selected in old_cifs+parameters:
            if not selected.is_file():raise ValueError('Selected native input missing')
        phenix=None
        if not args.inspect_only:
            environment={key:value for key,value in os.environ.items() if key not in NATIVE_OVERRIDES}
            phenix=installation_from_candidate(args.phenix_root,base_environment=environment)
            if not all(phenix.executables.get(name) for name in ['phenix.python','phenix.elbow']):
                raise ValueError('Selected Phenix requires installation-bound python and eLBOW')
        chosen={};sources={};recovery_required=[]
        for code,(_,_,_,index) in TARGETS.items():
            source=baseline/'inputs/sources'/f'{index}_{code}.cif';sources[code]=source
            selected=[p for p in old_cifs if code in dictionary_component_codes(p)]
            if len(selected)!=1:raise ValueError('Ambiguous effective definition: '+code)
            inspection=inspect_component_generation(source,selected[0],code)
            _json(session/'source_inspections'/f'{code}.json',inspection)
            if inspection['status']=='CANDIDATE_REVIEW':
                chosen[code]=selected[0];receipt['source_recovery'][code]={'status':'EXISTING_SOURCE_PRESERVING_CANDIDATE'}
                continue
            recovery_required.append(code)
            receipt['source_recovery'][code]={'status':'SOURCE_PRESERVING_GENERATION_REQUIRED','reasons':inspection['rejection_reasons']}
            if args.inspect_only:continue
            print('Generating a source-preserving whole-component candidate:',code,flush=True)
            generated=generate_elbow_candidate(source,code,session/'generation',phenix.executables['phenix.elbow'],
                environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['source_recovery'][code]=generated
            if generated['status']=='CANDIDATE_REVIEW':chosen[code]=Path(generated['candidate_directory'])/'candidate.cif'
        receipt['source_recovery_required']=recovery_required
        if len(chosen)!=len(TARGETS):
            receipt['status']='INSPECTED_SOURCE_RECOVERY_REQUIRED' if args.inspect_only else 'SOURCE_RECOVERY_REVIEW'
        else:
            selected_dir=session/'selected_bundle';selected_dir.mkdir()
            cifs=[]
            for old in old_cifs:
                codes=dictionary_component_codes(old)
                if not codes & set(TARGETS):cifs.append(old);continue
                if codes-set(TARGETS):
                    retained,_=_exclude_components(old,set(TARGETS),selected_dir/'retained_components.cif')
                    if retained:cifs.append(retained)
            prepared=[]
            for code,(site,incoming,outgoing,_) in TARGETS.items():
                context={'site':site,'incoming_site':incoming,'outgoing_site':outgoing,
                         'five_prime_state':'linked','three_prime_state':'linked'}
                directory=session/'preparation'/code
                result=prepare_linked_component(sources[code],chosen[code],model,[context],directory,code=code)
                receipt['preparations'][code]=result;prepared.append(result)
                cifs += [directory/result['outputs'][key]['path'] for key in ['dictionary','modifications']]
                parameters.append(directory/result['outputs']['parameters']['path'])
            _json(session/'selected_bundle.json',{'schema_version':1,
                'inputs':[{'path':p.relative_to(session).as_posix(),'sha256':_sha(p.read_bytes()),'size':p.stat().st_size} for p in cifs+parameters],
                'automatic_adoption':False})
            if args.inspect_only:
                receipt['status']='INSPECTED_PREPARED_REVIEW'
            else:
                print('Recording the original manager with full proxy details.',flush=True)
                original_parameters=[native_root/name for name in spec['phil_files']]
                common={'environment':phenix.environment,'phenix_version':phenix.version,
                        'timeout_seconds':args.timeout_seconds,'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked'}
                before=inspect_native_bundle(model,old_cifs,session/'native_baseline',phenix.executables['phenix.python'],
                    phil_files=original_parameters,**common)
                receipt['native_baseline']=before
                print('Interpreting the source-preserving, site-selected linked bundle.',flush=True)
                after=inspect_native_bundle(model,cifs,session/'native_linked',phenix.executables['phenix.python'],
                    phil_files=parameters,**common)
                receipt['native_validation']=after
                if before['status']=='REVIEW' and after['status']=='REVIEW':
                    qualification=qualify_linked_bundle(before['native_validation'],after['native_validation'],prepared,
                        expected_links,['A:1','B:1','C:8','D:1'])
                    receipt['qualification']=qualification
                    _json(session/'linked_qualification.json',qualification)
                    # One shared IGU base definition, two distinct site contexts:
                    # the original A:6 internal residue and an isolated free-OH E:1.
                    control_dir=session/'mixed_context_control';control_dir.mkdir()
                    lines=model.read_text().splitlines(keepends=True)
                    control_lines=[line for line in lines if not line.startswith(('END','CONECT','MASTER'))]
                    serial=max(int(line[6:11]) for line in lines if line.startswith(('ATOM  ','HETATM')))
                    for line in lines:
                        if not line.startswith(('ATOM  ','HETATM')) or line[21]!='A' or line[22:26].strip()!='6':continue
                        if line[12:16].strip() in {'P','OP1','OP2','OP3','O3P'}:continue
                        serial+=1
                        xyz=[float(line[a:b])+20 for a,b in [(30,38),(38,46),(46,54)]]
                        control_lines.append(line[:6]+f'{serial:5d}'+line[11:21]+'E'+f'{1:4d}'+line[26:30]+''.join(f'{x:8.3f}' for x in xyz)+line[54:])
                    control_model=control_dir/'model.pdb';control_model.write_text(''.join(control_lines)+'TER\nEND\n')
                    contexts=[{key:prepared[0]['sites'][0][key] for key in ['site','incoming_site','outgoing_site','five_prime_state','three_prime_state']},
                              {'site':'E:1','incoming_site':None,'outgoing_site':None,
                              'five_prime_state':'free_OH','three_prime_state':'free_OH'}]
                    # TARGETS begins with IGU; operational references remain explicit.
                    control_preparation=prepare_linked_component(sources['IGU'],chosen['IGU'],control_model,contexts,
                        session/'mixed_context_preparation',code='IGU')
                    control_inputs=[p for p in cifs if not p.is_relative_to(session/'preparation/IGU')]
                    control_inputs += [session/'mixed_context_preparation'/control_preparation['outputs'][key]['path'] for key in ['dictionary','modifications']]
                    control_parameters=[p for p in parameters if not p.is_relative_to(session/'preparation/IGU')]
                    control_parameters.append(session/'mixed_context_preparation/site_modifications.phil')
                    print('Testing shared-code internal/free-OH IGU contexts.',flush=True)
                    control=inspect_native_bundle(control_model,control_inputs,session/'native_control',phenix.executables['phenix.python'],
                        phil_files=control_parameters,**common)
                    receipt['mixed_context_control']={'preparation':control_preparation,'native':control}
                    control_pass=False
                    if control['status']=='REVIEW':
                        control_report=control['native_validation']
                        checks=site_definition_checks(control_report,[control_preparation])
                        receipt['mixed_context_control']['checks']=checks
                        rows={row['site']:row for row in control_report['monomer_mappings']['rows']}
                        control_pass=(len(rows)==43 and not control_report.get('unsupported_fields')
                            and all(row['status']=='PASS' for row in checks)
                            and all(not rows.get(plan['site'],{}).get('missing_non_hydrogen_atoms',{}).get('atom_ids')
                                    for plan in control_preparation['sites']))
                    receipt['mixed_context_control']['status']='PASS' if control_pass else 'REVIEW'
                    receipt['status']='LINKED_MECHANICS_PASS' if qualification['status']=='LINKED_MECHANICS_PASS' and control_pass else 'REVIEW'
                else:receipt['status']='NATIVE_REVIEW'
        if path.read_bytes()!=original:raise ValueError('Original review ZIP changed during diagnostic')
        receipt['original_archive_preserved']=True
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic:',receipt['status'],flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Original run preserved. Dictionary candidates only; no ReadySet retry, refinement or adoption.',flush=True)
        return 0 if receipt['status'] in {'LINKED_MECHANICS_PASS','INSPECTED_SOURCE_RECOVERY_REQUIRED','INSPECTED_PREPARED_REVIEW'} else 2
    except (Exception,KeyboardInterrupt) as exc:
        receipt.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=f'{type(exc).__name__}: {exc}')
        if session is not None:
            receipt['original_archive_preserved']=original is not None and path.read_bytes()==original
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print(receipt['error'],file=sys.stderr,flush=True)
        return 130 if isinstance(exc,KeyboardInterrupt) else 2


if __name__=='__main__':raise SystemExit(main())
