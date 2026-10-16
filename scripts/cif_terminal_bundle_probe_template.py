#!/usr/bin/env python3
"""Validate an explicit hydroxyl/5CM bundle from the reviewed Cedar 09/11 returns."""
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
LINKED_ARCHIVE_SHA256='db9f39ff423f0331ab26e4e3b7e65b176a767c5d64b0c698ce043f552f9dcb2a'
TERMINAL_ARCHIVE_SHA256='87b62be8b669a54a8f2e67b5a18a439cb88e6b187354b95847fa29c96bb02cbc'
CONTROL_PREFIX='native_control/cif-native-_eplfatc'
RESOURCE_MEMBER='terminal_resources/cif-terminal-resources-7ntk0ctv/resources_receipt.json'
IGU_SOURCE_MEMBER='baseline/inputs/sources/7_IGU.cif'
IGU_NUMERICAL_MEMBER='baseline/native/cif-native-90b84f1c/inputs/007_dictionary.cif'
CHAINS={'A':[str(i) for i in range(1,22)],'B':[str(i) for i in range(1,8)],
        'C':[str(i) for i in range(8,15)],'D':[str(i) for i in range(1,8)]}
NATIVE_OVERRIDES={'PYTHONPATH','PYTHONHOME','PHENIX','PHENIX_ROOT','PHENIX_VERSION','LIBTBX_BUILD','LIBTBX_DIST','BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data):return hashlib.sha256(data).hexdigest()


def _json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _safe_name(name):
    return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in {'','.','..'} for p in name.split('/'))


def _runtime_members():
    data=base64.b64decode(RUNTIME_BASE64,validate=True)
    if _sha(data)!=BUNDLE['runtime_archive_sha256']:raise ValueError('Embedded runtime checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries=archive.infolist()
        if len(entries)!=len({e.filename for e in entries}) or any(not _safe_name(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):
            raise ValueError('Unsafe or duplicate runtime member')
        members={e.filename:archive.read(e) for e in entries}
    if set(members)!=set(BUNDLE['runtime_files']):raise ValueError('Runtime inventory mismatch')
    for name,payload in members.items():
        expected=BUNDLE['runtime_files'][name]
        if _sha(payload)!=expected['sha256'] or len(payload)!=expected['size']:raise ValueError('Runtime file integrity mismatch')
    return members


def _read_capsule(path,sha,count,kind,delivery):
    original=path.read_bytes()
    if _sha(original)!=sha:raise ValueError('Require the exact hash-bound '+delivery+' review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        manifest=json.loads(archive.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=count:
            raise ValueError('Unexpected '+delivery+' payload inventory')
        members={}
        for entry in entries:
            name=entry.filename
            if not _safe_name(name) or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe review path')
            payload=archive.read(entry)
            if name!='manifest.json' and (_sha(payload)!=manifest[name]['sha256'] or len(payload)!=manifest[name]['bytes']):
                raise ValueError('Review payload integrity mismatch')
            members[name]=payload
    prior=json.loads(members['probe_receipt.json'])
    if prior.get('kind')!=kind or prior.get('delivery_prefix')!=delivery or prior.get('original_archive_preserved') is not True:
        raise ValueError('Require the preserved '+delivery+' probe receipt')
    return members,prior,original


def _materialize(members,names,target):
    for name in sorted(set(names)):
        if not _safe_name(name) or name not in members:raise ValueError('Missing explicit capsule member: '+name)
        path=target/PurePosixPath(name);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle:handle.write(members[name])


def _freeze_inputs(session,linked_path,terminal_path):
    linked,old,linked_original=_read_capsule(linked_path,LINKED_ARCHIVE_SHA256,207,'cif-linked-native-probe','09_Cedar')
    terminal,new,terminal_original=_read_capsule(terminal_path,TERMINAL_ARCHIVE_SHA256,9,'cif-terminal-source-review','11_Cedar')
    if old.get('status')!='REVIEW' or new.get('status')!='PREPARATION_AND_RESOURCES_REVIEW':
        raise ValueError('Prior native returns do not match the reviewed trial scope')
    spec=json.loads(linked[CONTROL_PREFIX+'/native_spec.json'])
    names=spec['dictionaries']+spec['phil_files']+[spec['model']]
    if any(not _safe_name(n) for n in names) or len(names)!=len(set(names)):
        raise ValueError('Unsafe or duplicated declared native input')
    selected={CONTROL_PREFIX+'/native_spec.json',IGU_SOURCE_MEMBER,IGU_NUMERICAL_MEMBER}
    selected.update(CONTROL_PREFIX+'/'+n for n in names)
    _materialize(linked,selected,session/'inputs/linked')
    _materialize(terminal,set(terminal)-{'manifest.json','probe_receipt.json'},session/'inputs/terminal')
    reference=next(row for row in old['mixed_context_control']['native']['native_validation']['monomer_mappings']['rows'] if row['site']=='A:7')
    state={'linked_build':{k:old['build'][k] for k in ['nasolve_source','narestraints_source']},
        'terminal_build':{k:new['build'][k] for k in ['nasolve_source','narestraints_source']},
        'control_preparation':{k:old['mixed_context_control']['preparation'][k] for k in ['policy_id','sites','outputs']},
        'other_preparations':[{k:p[k] for k in ['component','policy_id','sites']} for code,p in old['preparations'].items() if code!='IGU'],
        'five_cm_reference_atoms':reference['metadata']['atom_ids'],
        'five_cm_preparation':{k:new['five_cm_preparation'][k] for k in ['recipe_id','source','output','source_preserved']},
        'verified_archives':{'09_Cedar':{'sha256':LINKED_ARCHIVE_SHA256,'bytes':len(linked_original),'verified_payloads':207,'materialized_payloads':len(selected)},
            '11_Cedar':{'sha256':TERMINAL_ARCHIVE_SHA256,'bytes':len(terminal_original),'verified_payloads':9,'materialized_payloads':len(terminal)-2}}}
    _json(session/'prior_evidence.json',state)
    return state,{'09_Cedar':(linked_path,linked_original),'11_Cedar':(terminal_path,terminal_original)}


def _unique_by_sha(paths,sha):
    found=[p for p in paths if _sha(p.read_bytes())==sha]
    if len(found)!=1:raise ValueError('Require one exact declared frozen input: '+sha)
    return found[0]


def _prepare_candidate(session,state):
    from nasolve.cif_doctor_repair import prepare_dictionary
    from nasolve.cif_linked_preparation import _prune,_render,atom_rows,component_values
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    from nasolve.ligand_profiles import dictionary_component_codes
    linked=session/'inputs/linked';terminal=session/'inputs/terminal'
    root=linked/CONTROL_PREFIX;spec=json.loads((root/'native_spec.json').read_text())
    cifs=[root/n for n in spec['dictionaries']];phils=[root/n for n in spec['phil_files']];model=root/spec['model']
    old=state['control_preparation'];outputs=old['outputs']
    igu_base=_unique_by_sha(cifs,outputs['dictionary']['sha256'])
    igu_mod=_unique_by_sha(cifs,outputs['modifications']['sha256'])
    igu_phil=_unique_by_sha(phils,outputs['parameters']['sha256'])
    contexts=[{k:s[k] for k in ['site','incoming_site','outgoing_site','five_prime_state','three_prime_state']} for s in old['sites']]
    directory=session/'preparation/IGU'
    preparation=prepare_terminal_component(linked/IGU_SOURCE_MEMBER,linked/IGU_NUMERICAL_MEMBER,model,contexts,
        terminal/RESOURCE_MEMBER,directory,code='IGU')
    if (directory/'base_dictionary.cif').read_bytes()!=igu_base.read_bytes():raise ValueError('Shared IGU base dictionary changed')
    for before,after in zip(old['sites'],preparation['sites']):
        if before['five_prime_state']!='free_OH' and before!=after:raise ValueError('Unselected shared-code context changed')
    source=terminal/'inputs/5CM_source.cif'
    old_five=_unique_by_sha(cifs,state['five_cm_preparation']['source']['sha256'])
    if dictionary_component_codes(old_five)!={'5CM'}:raise ValueError('5CM override is not one exact component')
    five=session/'preparation/5CM_candidate.cif'
    five_receipt=prepare_dictionary(source,five,recipe='5cm-reviewed-torsion-v1')
    if five.read_bytes()!=(terminal/'5cm_preparation/5CM_candidate.cif').read_bytes():raise ValueError('Reviewed 5CM candidate differs')
    _json(session/'preparation/5CM_preparation_receipt.json',five_receipt)
    replacements={igu_base:directory/'base_dictionary.cif',igu_mod:directory/'site_modifications.cif',old_five:five}
    selected=[replacements.get(p,p) for p in cifs]
    parameters=[directory/'site_modifications.phil' if p==igu_phil else p for p in phils]
    values=component_values(five,'5CM');removed=set(atom_rows(values))-set(state['five_cm_reference_atoms'])
    if removed!={'OP3'}:raise ValueError('Reviewed 5CM native projection differs from declared linked atom context')
    projection=session/'preparation/projected_5CM_A_7.cif';projection.write_text(_render(_prune(values,removed,outgoing=False),'5CM'))
    projections={'A:7':(projection,'5CM')}
    projections.update({s['site']:(directory/('projected_'+s['site'].replace(':','_')+'.cif'),'IGU')
                        for s in preparation['sites'] if s.get('terminal_hydroxyl')})
    _json(session/'selected_bundle.json',{'schema_version':1,'model':model.relative_to(session).as_posix(),
        'inputs':[{'path':p.relative_to(session).as_posix(),'sha256':_sha(p.read_bytes()),'bytes':p.stat().st_size} for p in selected+parameters],
        'selected_definition_changes':sorted(projections),'automatic_adoption':False})
    return {'model':model,'old_cifs':cifs,'old_phils':phils,'cifs':selected,'phils':parameters,
        'preparations':[preparation,*state['other_preparations']],'projections':projections,
        'five_cm_preparation':five_receipt,'resource_receipt':terminal/RESOURCE_MEMBER}


def _installation_fingerprints(phenix,resource_receipt):
    receipt=json.loads(resource_receipt.read_text());native=receipt['native_resources']
    executable=phenix.executables.get('phenix.python')
    if not executable or not phenix.root or phenix.version!=receipt['phenix_version']:
        raise ValueError('Selected Phenix does not match the captured terminal-source installation')
    if _sha(Path(executable).read_bytes())!=receipt['executable_sha256']:
        raise ValueError('Phenix dispatcher changed since terminal-source collection')
    historical=Path(receipt['executable_provenance']).parent.parent
    records=[]
    for row in native['api_sources']+native['source_files']:
        relative=Path(row['historical_path']).relative_to(historical)
        path=Path(phenix.root)/relative
        if not path.resolve().is_relative_to(Path(phenix.root).resolve()) or _sha(path.read_bytes())!=row['sha256']:
            raise ValueError('Installed terminal authority changed: '+relative.as_posix())
        records.append({'anchor':'phenix_installation','path':relative.as_posix(),'sha256':row['sha256']})
    return records


def _review_zip(session):
    token=session.name.rsplit('-',1)[-1];destination=session/(BUNDLE['delivery_prefix']+'_'+token+'_cif_terminal_bundle_review.zip')
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
    parser.add_argument('--linked-review-zip',type=Path,default=Path.home()/'NASolve-live-tests/09_Cedar_cif-linked-probe-nn9cyghr/09_Cedar_nn9cyghr_cif_linked_review.zip')
    parser.add_argument('--terminal-review-zip',type=Path,default=Path.home()/'NASolve-live-tests/11_Cedar_cif-terminal-probe-ggtpccwv/11_Cedar_ggtpccwv_cif_terminal_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',default=str(Path.home()/'Applications/phenix-2.2.1-6174'))
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;originals={}
    receipt={'schema_version':1,'kind':'cif-terminal-bundle-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'FAILED','automatic_adoption':False,'model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','native_validation':'NOT_RUN'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Timeout must be 1-3600 seconds')
        members=_runtime_members();linked=args.linked_review_zip.expanduser().resolve(strict=True);terminal=args.terminal_review_zip.expanduser().resolve(strict=True)
        parent=args.output_parent.expanduser().resolve()
        if any(parent==p.parent or parent.is_relative_to(p.parent) for p in [linked,terminal]):raise ValueError('Output must be outside preserved diagnostic directories')
        parent.mkdir(parents=True,exist_ok=True);session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-terminal-bundle-',dir=parent))
        _materialize(members,members,session/'runtime');sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_linked_qualification import declared_linear_links
        from nasolve.cif_native_validation import inspect_native_bundle
        from nasolve.cif_terminal_qualification import qualify_terminal_bundle
        from nasolve.phenix_runtime import installation_from_candidate
        print('CIF terminal/bundle diagnostic:',BUNDLE['delivery_prefix'],flush=True)
        state,originals=_freeze_inputs(session,linked,terminal);receipt['prior_archives']=state['verified_archives']
        print('Preparing selected free-OH IGU and the reviewed 5CM candidate.',flush=True)
        bundle=_prepare_candidate(session,state)
        receipt['terminal_preparation']=bundle['preparations'][0];receipt['five_cm_preparation']=bundle['five_cm_preparation']
        if args.inspect_only:receipt['status']='PREPARED_REVIEW_NATIVE_NOT_RUN'
        else:
            environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix=installation_from_candidate(args.phenix_root,base_environment=environment)
            fingerprints=_installation_fingerprints(phenix,bundle['resource_receipt']);receipt['installed_terminal_authorities']=fingerprints
            common={'environment':phenix.environment,'phenix_version':phenix.version,'timeout_seconds':args.timeout_seconds,
                'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked'}
            print('Interpreting the preserved shared-context baseline.',flush=True)
            before=inspect_native_bundle(bundle['model'],bundle['old_cifs'],session/'native_baseline',phenix.executables['phenix.python'],phil_files=bundle['old_phils'],**common)
            receipt['native_baseline']=before
            print('Interpreting the selected hydroxyl / reviewed 5CM bundle.',flush=True)
            after=inspect_native_bundle(bundle['model'],bundle['cifs'],session/'native_candidate',phenix.executables['phenix.python'],phil_files=bundle['phils'],**common)
            receipt['native_validation']=after
            if before['status']=='REVIEW' and after['status']=='REVIEW':
                report=qualify_terminal_bundle(before['native_validation'],after['native_validation'],bundle['preparations'],
                    declared_linear_links(CHAINS),['A:1','B:1','C:8','D:1',*{s['site'] for s in bundle['preparations'][0]['sites'] if s.get('terminal_hydroxyl')}],
                    bundle['projections'],reviewed_torsions={'A:7':'C2e-nyu0'})
                receipt['qualification']=report;receipt['status']=report['status'];_json(session/'bundle_qualification.json',report)
                failures=[r['check'] for r in report['checks'] if r['status']!='PASS']
                print('Checks requiring review:',', '.join(failures),flush=True)
            else:
                receipt['status']='NATIVE_REVIEW'
                for label,result in [('baseline',before),('candidate',after)]:
                    if result['status']!='REVIEW':print('Native '+label+' requires review:',result.get('error') or result['status'],flush=True)
            if _installation_fingerprints(phenix,bundle['resource_receipt'])!=fingerprints:raise ValueError('Installed authority changed during validation')
        receipt['original_archives_preserved']={name:path.read_bytes()==data for name,(path,data) in originals.items()}
        if not all(receipt['original_archives_preserved'].values()):raise ValueError('Preserved review archive changed')
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic:',receipt['status'],flush=True);print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Dictionary/native mechanics only; no coordinate edits, optimization, refinement or adoption.',flush=True)
        return 0 if receipt['status'] in {'PREPARED_REVIEW_NATIVE_NOT_RUN','TERMINAL_BUNDLE_MECHANICS_PASS'} else 2
    except (Exception,KeyboardInterrupt) as exc:
        receipt.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
        if session is not None:
            receipt['original_archives_preserved']={name:path.read_bytes()==data for name,(path,data) in originals.items()}
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print(receipt['error'],file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
