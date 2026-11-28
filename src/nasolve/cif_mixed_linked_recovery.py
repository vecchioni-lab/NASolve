"""Fixed full-model readback of independently usable component recoveries.

The repaired resource bundle is shared by the disabled-policy baseline and the
declared NARestraints policy. An unusable original numerical definition is not a
native baseline. Source-state findings stay separate from mechanical checks.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory

POLICY_ID='cif-mixed-linked-component-recovery-v1'
ANCHOR='mixed_linked_recovery_directory'
REPORT='mixed_linked_recovery.json'
BASELINE_SCOPE='SAME_REPAIRED_BUNDLE_WITH_DECLARED_NA_POLICY_DISABLED; NOT_THE_INVALID_ORIGINAL'
QUALIFICATION_REPLAY_POLICY='EXACT_WITH_ATOM_KEYED_FORMAL_CHARGE_EVIDENCE_ORDER_ONLY'


def _canonical_qualification(value):
    """Canonicalize atom-keyed charge notes only in this new audit's scope.

    The shared legacy qualifier retains its existing serialization contract.
    """
    if not isinstance(value,dict) or not isinstance(value.get('checks'),list) or not value['checks']:
        raise ValueError('Missing qualification checks')
    result=deepcopy(value)
    for check in result['checks']:
        if not isinstance(check,dict):raise ValueError('Invalid qualification check')
        name=check.get('check')
        if not isinstance(name,str) or not re.fullmatch(
                r'(?:baseline:|active:)?effective-site-formal-charges:[^:\s]+:[^:\s]+',name):continue
        for field in ['unavailable','contradictions']:
            rows=check[field]
            if not isinstance(rows,list):raise ValueError('Invalid formal-charge evidence')
            names=[]
            for row in rows:
                if (not isinstance(row,dict) or set(row)!={'atom_id','expected','observed'}
                        or not isinstance(row['atom_id'],str) or not row['atom_id']):
                    raise ValueError('Unbound formal-charge evidence row')
                names.append(row['atom_id'])
            if len(names)!=len(set(names)):raise ValueError('Duplicate formal-charge atom identity')
            check[field]=sorted(rows,key=lambda row:row['atom_id'])
    return result


def qualification_replays(recorded,fresh):
    """Replay legacy charge evidence without assigning meaning to atom order.

    Only unavailable/contradiction rows emitted by the named formal-charge
    checks are keyed by atom identity. Every row, type, value, status, other
    list order and qualification field remains exact; nothing is rounded.
    """
    def exact(a,b):
        if type(a) is not type(b):return False
        if isinstance(a,dict):return a.keys()==b.keys() and all(exact(v,b[k]) for k,v in a.items())
        if isinstance(a,(list,tuple)):return len(a)==len(b) and all(exact(v,w) for v,w in zip(a,b))
        if isinstance(a,float):return math.isfinite(a) and math.isfinite(b) and a==b
        return a==b
    try:return exact(_canonical_qualification(recorded),_canonical_qualification(fresh))
    except (ValueError,KeyError,TypeError):return False


def _coordinate_decision(usable):
    return {'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model',
        'native_usable':True if usable else 'NOT_YET_QUALIFIED','requires_cif_review':False,'automatic_adoption':False}


def _ref(path,root):
    from .cif_mixed_recovery import _safe
    path,root=Path(path),Path(root)
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Linked recovery artifact traverses a symlink')
    name=path.relative_to(root).as_posix()
    if not _safe(name):raise ValueError('Unsafe linked recovery path')
    data=path.read_bytes()
    return {'anchor':ANCHOR,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}


def _resolve(root,ref):
    from .cif_mixed_recovery import _safe
    if not isinstance(ref,dict) or ref.get('anchor')!=ANCHOR or not _safe(ref.get('path')):raise ValueError('Unsafe linked recovery reference')
    path=Path(root)/ref['path']
    if _ref(path,root)!=ref:raise ValueError('Linked recovery artifact differs')
    return path


def _dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _same_bytes(a,b):return a.get('sha256')==b.get('sha256') and a.get('size')==b.get('size')


def _candidate(root,recovery,code):
    from .cif_mixed_recovery import _resolve as resolve,_safe
    from .cif_candidate_usability import reassess_complete_candidate
    from .ligand_profiles import _parameterized_codes
    case=recovery['components'][code];generation=case['generation'];directory=generation['directory'];ref=generation['candidate']
    if directory.get('anchor')!='mixed_recovery_directory' or not _safe(directory.get('path')) or ref.get('anchor')!='candidate_directory' or not _safe(ref.get('path')):
        raise ValueError('Unbound recovered candidate')
    path=root/directory['path']/ref['path'];data=path.read_bytes()
    if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Recovered candidate bytes differ')
    source=resolve(root,recovery['inputs']['sources'][code]);q=case['isolated_qualification'];decision=case['decision']
    assessment=reassess_complete_candidate(source,path,code)
    if (case.get('source')!=recovery['inputs']['sources'][code] or q.get('component')!=code or q.get('native_usable') is not True
            or q.get('candidate_sha256')!=ref['sha256'] or decision.get('continue_solving') is not True
            or decision.get('selected_sha256')!=ref['sha256'] or assessment['candidate_status']!='CANDIDATE_REVIEW'
            or code not in _parameterized_codes(path)):
        raise ValueError('Require the independently usable source-bound recovered selection')
    return source,path,q


def _contexts(model,plan,targets):
    from .cif_linked_preparation import _model_inventory
    inventory=_model_inventory(model);expected=plan['target_site_components'];edges=plan['stack_edges']
    if {s:v['code'] for s,v in inventory.items()}!=expected:raise ValueError('Declared plan does not cover the exact model sites')
    if (not isinstance(edges,list) or any(not isinstance(e,list) or len(e)!=2 or e[0]==e[1]
            or any(s not in inventory for s in e) for e in edges) or len({tuple(e) for e in edges})!=len(edges)):
        raise ValueError('Unsupported declared phosphodiester topology')
    result={}
    for code in targets:
        selected=sorted(s for s,c in expected.items() if c==code)
        if not selected:raise ValueError('Recovered component has no declared model site')
        rows=[]
        for site in selected:
            incoming=[a for a,b in edges if b==site];outgoing=[b for a,b in edges if a==site]
            if len(incoming)>1 or len(outgoing)>1:raise ValueError('Branched site requires an explicit wider context adapter')
            atoms=inventory[site]['atoms'];phosphate={'P','OP1','OP2','OP3'}
            if incoming:
                if not {'P','OP1','OP2'}<=atoms or 'OP3' in atoms:raise ValueError('Declared internal phosphate inventory differs')
                five='linked'
            elif not atoms&phosphate:five='free_OH'
            elif phosphate<=atoms:five='phosphate'
            else:raise ValueError('Terminal phosphate state is incomplete or ambiguous')
            rows.append({'site':site,'incoming_site':incoming[0] if incoming else None,
                'outgoing_site':outgoing[0] if outgoing else None,'five_prime_state':five,
                'three_prime_state':'linked' if outgoing else 'free_OH'})
        result[code]=rows
    return result


def _selection(root,recovery,plan):
    from .cif_mixed_recovery import _resolve as resolve,_targets
    if recovery.get('status')!='MIXED_RECOVERY_ISOLATED_PASS':raise ValueError('Require passed isolated component recovery')
    refs=recovery['inputs'];sources={c:resolve(root,r) for c,r in refs['sources'].items()}
    dictionaries=[resolve(root,r) for r in refs['effective_dictionaries']]
    summary=json.loads(resolve(root,refs['parent_summary']).read_bytes());required=summary['required_modified_parameterization']
    targets=_targets(required['components'],required['missing'],sources,dictionaries)
    if recovery['targets']!=targets or set(recovery['components'])!=set(targets):raise ValueError('Recovered target scope differs')
    if set(sources)!=set(plan['target_site_components'].values()):raise ValueError('Declared source scope differs from the full model')
    for code in targets:_candidate(root,recovery,code)
    return sources,dictionaries,targets,_contexts(resolve(root,refs['model']),plan,targets),summary


def _compact_findings(sources,dictionaries):
    from .cif_mixed_native import compare_effective_chemistry
    from .ligand_profiles import dictionary_component_codes
    comparisons=compare_effective_chemistry(sources,dictionaries)
    return {c:{'status':v.get('status'),'rejection_reasons':v.get('rejection_reasons',[]),
        'source_graph_retained':v.get('source_graph_retained'),
        'source_sha256':sha256(sources[c].read_bytes()).hexdigest(),
        'effective_input_sha256':[sha256(p.read_bytes()).hexdigest() for p in dictionaries if c in dictionary_component_codes(p)],
        'detail_authority':'PRESERVED_PARENT_REPORT_BOUND_BY_RECOVERY_SUMMARY; DERIVED_FLOATS_NOT_HASHED'}
        for c,v in sorted(comparisons.items())}


def _prepare_bundle(root,recovery_root,recovery,plan):
    from .cif_mixed_recovery import _resolve as resolve
    from .cif_linked_preparation import prepare_linked_component,component_values
    from .ligand_profiles import _exclude_components,_blocks,dictionary_component_codes,_parameterized_codes
    from .cif_mixed_native import select_native_dictionaries,CANONICAL
    sources,dictionaries,targets,contexts,_=_selection(recovery_root,recovery,plan)
    model=resolve(recovery_root,recovery['inputs']['model']);bundle=root/'bundle';bundle.mkdir()
    preparations={};projections={};prepared_files=[];context_phils=[]
    for code in targets:
        source,candidate,q=_candidate(recovery_root,recovery,code);out=bundle/'prepared'/code
        receipt=prepare_linked_component(source,candidate,model,contexts[code],out,code=code,native_qualification=q)
        preparations[code]={'directory':{'anchor':ANCHOR,'path':out.relative_to(root).as_posix()},'receipt':receipt}
        prepared_files.extend(out/receipt['outputs'][k]['path'] for k in ['dictionary','modifications'])
        context_phils.append(out/receipt['outputs']['parameters']['path'])
        for row in receipt['sites']:
            site=row['site'];projections[site]={'component':code,'dictionary':_ref(out/('projected_'+site.replace(':','_')+'.cif'),root)}
    resources=bundle/'resources';resources.mkdir();filtered=[];proof=[]
    for i,path in enumerate(dictionaries):
        codes=dictionary_component_codes(path);selected=codes&set(targets);out=resources/f'{i:03d}.cif'
        if selected:
            retained,present=_exclude_components(path,set(targets),out)
            bystanders=codes-set(targets)
            rows_equal=all(component_values(path,c)==component_values(retained,c) for c in bystanders) if retained else not bystanders
            def blocks(p):
                return Counter(b.text.rstrip('\r\n') for b in _blocks(p) if not (dictionary_component_codes_from_block(b)&set(targets))
                    and not ('_chem_comp.id' in b.values and not dictionary_component_codes_from_block(b))) if p else Counter()
            block_equal=blocks(path)==blocks(retained)
            if present!=bystanders or not rows_equal or not block_equal:raise ValueError('Selected exclusion changed unrelated component rows or blocks')
            if retained:filtered.append(retained)
            proof.append({'input_index':i,'removed_components':sorted(selected),'retained_components':sorted(present),
                'unrelated_rows_preserved':rows_equal,'unrelated_blocks_preserved':block_equal,
                'block_separator_policy':'TRAILING_CR_LF_ONLY; ALL_OTHER_RETAINED_BLOCK_BYTES_EXACT',
                'retained':_ref(retained,root) if retained else None})
        else:
            out.write_bytes(path.read_bytes());filtered.append(out)
            proof.append({'input_index':i,'removed_components':[],'retained_components':sorted(codes),
                'exact_copy':_same_bytes(_ref(out,root),recovery['inputs']['effective_dictionaries'][i]),'retained':_ref(out,root)})
    all_dictionaries=[*filtered,*prepared_files]
    parameterized=set().union(*(_parameterized_codes(p) for p in all_dictionaries))
    if set(sources)-CANONICAL-parameterized:raise ValueError('Repaired bundle still lacks modified-component numerics')
    selected,canonical=select_native_dictionaries(all_dictionaries,sources)
    all_codes=[c for p in all_dictionaries for c in dictionary_component_codes(p)]
    if len(all_codes)!=len(set(all_codes)) or set(all_codes)!=set(sources):raise ValueError('Repaired component coverage is missing or ambiguous')
    return {'contexts':contexts,'preparations':preparations,'site_projections':projections,'resource_delta':proof,
        'effective_dictionaries':[_ref(p,root) for p in all_dictionaries],
        'native_dictionaries':[_ref(p,root) for p in selected],'context_phils':[_ref(p,root) for p in context_phils],
        'installed_canonical_components':canonical,'modified_numerical_components':sorted(parameterized),
        'component_metadata':{c:{'group':component_values(p,c).get('_chem_comp.group'),
            'type':component_values(p,c).get('_chem_comp.type')} for p in all_dictionaries for c in dictionary_component_codes(p)},
        'preserved_source_findings':_compact_findings(sources,dictionaries)}


def dictionary_component_codes_from_block(block):
    return set(block.values.get('_chem_comp_atom.comp_id',[]))


def _qualify(before,after,model,active,plan,sources,dictionaries,bundle,root):
    from .cif_mixed_native import qualify_mixed_native
    from .cif_linked_qualification import site_definition_checks,_site
    from .cif_linked_control import _heavy_proxy_checks
    from .cif_effective_source_recovery import mechanics_can_continue
    from itertools import combinations
    projections={s:(_resolve(root,v['dictionary']),v['component']) for s,v in bundle['site_projections'].items()}
    membership=qualify_mixed_native(before,after,model,active,plan,sources,dictionaries,site_projections=projections)
    checks=[]
    def check(name,ok,**detail):checks.append({'check':name,'status':'PASS' if ok else 'REVIEW',**detail})
    check('full-model-narestraints-membership',membership['mechanics_checks_pass'])
    preparations=[v['receipt'] for v in bundle['preparations'].values()]
    for label,native in [('baseline',before),('active',after)]:
        checks.extend(dict(c,check=label+':'+c['check']) for c in site_definition_checks(native,preparations))
        mappings={v['site']:v for v in native['monomer_mappings']['rows']};atoms={v['i_seq']:v for v in native['atoms']}
        for prep in preparations:
            for context in prep['sites']:
                site=context['site'];code=context['component'];projected=projections[site][0]
                check(label+':exact-selected-modifier:'+site,mappings.get(site,{}).get('chem_mod_ids')=={
                    'status':'RECORDED','ids':[context['modification_id']] if context['modification_id'] else []})
                for name,ok in _heavy_proxy_checks(native,projected,code,site).items():check(label+':'+name+':'+site,ok)
                if context['incoming_site']:
                    p=next(i for i,a in atoms.items() if _site(a)==site and a['atom_id']=='P')
                    neighbors={next(i for i in row['i_seqs'] if i!=p) for row in native['geometry']['proxy_details']['bond_simple'] if p in row['i_seqs']}
                    angles={min(tuple(row['i_seqs']),tuple(row['i_seqs'])[::-1]) for row in native['geometry']['proxy_details']['angle']}
                    expected={(context['incoming_site'],"O3'"),(site,"O5'"),(site,'OP1'),(site,'OP2')}
                    check(label+':linked-phosphate-coverage:'+site,{(_site(atoms[i]),atoms[i]['atom_id']) for i in neighbors}==expected
                        and all(min((a,p,b),(b,p,a)) in angles for a,b in combinations(neighbors,2)))
    # Keep the existing unavailable-formal-charge API allowance local and exact.
    normalized={'checks':[dict(c,check=c['check'].split(':',1)[1]) if c['check'].startswith(('baseline:effective-site-formal-charges:','active:effective-site-formal-charges:')) else c for c in checks]}
    usable=mechanics_can_continue(normalized)
    return _canonical_qualification({'policy_id':POLICY_ID,'status':'MIXED_LINKED_RECOVERY_MECHANICS_PASS' if usable else 'REVIEW',
        'mechanics_checks_pass':usable,'membership':membership,'checks':checks,'scientific_qualification':'NOT_ASSESSED',
        'source_chemical_findings':'PRESERVED_SEPARATELY; NOT_PROMOTED_BY_NATIVE_MEMBERSHIP','automatic_adoption':False})


def _capture(root,ref,model,dictionaries,phils):
    from .cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    from .cif_mixed_recovery import _safe
    receipt=_resolve(root,ref);folder=receipt.parent;capture=json.loads(receipt.read_bytes())
    if (capture.get('policy_id')!=NATIVE_POLICY_ID or capture.get('automatic_adoption') is not False
            or capture.get('phil_namespace_policy')!='refinement-root-to-interpreter-v1'
            or capture.get('dictionary_source_policy')!='EXPLICIT_DICTIONARIES'
            or any(capture.get(k)!='NOT_RUN' for k in ['model_editing','optimization','readyset_retry','scientific_approval'])
            or receipt.name!='native_receipt.json'
            or (folder/'native_worker.py').read_bytes()!=native_energy_worker(_NATIVE_WORKER).encode()):
        raise ValueError('Native maintained worker or scope differs')
    expected=[('model',model),*[('dictionary',p) for p in dictionaries],*[('phil',p) for p in phils]];inputs=capture['inputs']
    if len(inputs)!=len(expected):raise ValueError('Native shared input scope differs')
    for i,((role,path),row) in enumerate(zip(expected,inputs)):
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')) or row.get('role')!=role or row.get('input_index')!=i:raise ValueError('Native input role differs')
        data=(folder/row['path']).read_bytes()
        if data!=path.read_bytes() or len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Native fixed input bytes differ')
    spec={'policy_id':NATIVE_POLICY_ID,'model':inputs[0]['path'],'dictionaries':[r['path'] for r in inputs if r['role']=='dictionary'],
        'phil_files':[r['path'] for r in inputs if r['role']=='phil'],'phil_namespace_policy':'refinement-root-to-interpreter-v1',
        'inventory_detail':'linked','policy_inventory':True,'energy_inventory':True}
    if json.loads((folder/'native_spec.json').read_bytes())!=spec:raise ValueError('Native fixed input specification differs')
    if capture.get('native_validation') is not None:
        result=folder/'native_validation.json'
        if not result.is_file() or result.is_symlink() or json.loads(result.read_bytes())!=capture['native_validation']:
            raise ValueError('Native result is missing or differs')
    for row in capture['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):raise ValueError('Unsafe native output reference')
        data=(folder/row['path']).read_bytes()
        if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Native output bytes differ')
    names=[r['path'] for r in capture['outputs']]
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if len(names)!=len(set(names)) or set(names)|{'native_receipt.json'}!=actual:raise ValueError('Native capture output inventory differs')
    return capture


def _publish(root,report):
    if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('Linked recovery output contains a symlink')
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}]
    _dump(root/REPORT,report);read_mixed_linked_recovery(root);return report


def audit_mixed_linked_recovery(recovery_directory,parent_native_directory,phenix,output,*,timeout_seconds=60):
    from .cif_mixed_recovery import read_mixed_recovery,_resolve as resolve
    from .cif_mixed_native import read_mixed_native,_resolve as parent_resolve,_native_ok
    from .cif_native_validation import inspect_native_bundle
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=60:raise ValueError('Require an integer native deadline from 1 to 60 seconds')
    recovery_directory,parent_native_directory,output=map(Path,(recovery_directory,parent_native_directory,output))
    output=output.absolute()
    if output.exists() or any(p.is_symlink() for p in [output,*output.parents]) or any(output.resolve().is_relative_to(p.resolve()) for p in [recovery_directory,parent_native_directory]):raise ValueError('Require a fresh separate linked recovery output')
    recovery=read_mixed_recovery(recovery_directory);parent=read_mixed_native(parent_native_directory)
    summary=json.loads(resolve(recovery_directory,recovery['inputs']['parent_summary']).read_bytes())
    if (sha256((parent_native_directory/'mixed_native.json').read_bytes()).hexdigest()!=summary['parent_report_sha256']
            or parent['inputs']!=summary['parent_input_bindings'] or parent['effective_dictionaries']!=summary['parent_effective_bindings']
            or parent['source_authorities']!=summary['source_authorities'] or parent['required_modified_parameterization']!=summary['required_modified_parameterization']):
        raise ValueError('Recovered selection does not bind the preserved native parent')
    plan_path=parent_resolve(parent_native_directory,parent['inputs']['plan']);plan=json.loads(plan_path.read_bytes())
    disabled=parent_resolve(parent_native_directory,parent['inputs']['disabled_policy'])
    _selection(recovery_directory,recovery,plan)
    originals={p:p.read_bytes() for p in [recovery_directory/'mixed_recovery.json',plan_path,disabled,
        *[resolve(recovery_directory,r) for r in recovery['outputs']]]}
    output.mkdir(parents=True);frozen=output/'inputs/recovery';frozen.mkdir(parents=True)
    for ref in recovery['outputs']:
        source=resolve(recovery_directory,ref);target=frozen/ref['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
    (frozen/'mixed_recovery.json').write_bytes((recovery_directory/'mixed_recovery.json').read_bytes())
    plan_copy=output/'inputs/plan.json';plan_copy.write_bytes(plan_path.read_bytes())
    disabled_copy=output/'inputs/disabled_policy.phil';disabled_copy.write_bytes(disabled.read_bytes())
    bundle=_prepare_bundle(output,frozen,recovery,plan)
    model=resolve(frozen,recovery['inputs']['model']);active=resolve(frozen,recovery['inputs']['active_policy'])
    sources={c:resolve(frozen,r) for c,r in recovery['inputs']['sources'].items()}
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','targets':recovery['targets'],
        'inputs':{'recovery_report':_ref(frozen/'mixed_recovery.json',output),'model':_ref(model,output),
            'active_policy':_ref(active,output),'disabled_policy':_ref(disabled_copy,output),'plan':_ref(plan_copy,output),
            'sources':{c:_ref(p,output) for c,p in sources.items()}},'bundle':bundle,
        'native_baseline':{'status':'NOT_RUN'},'native_active':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'new_native_calls':0,'maximum_native_calls':2,'timeout_seconds':timeout_seconds,'policy_authority':'NARestraints',
        'baseline_scope':BASELINE_SCOPE,
        'source_inputs_preserved':True,'model_preserved':True,'unrelated_numerics_preserved':True,
        'coot_execution':'NOT_RUN','readyset_execution':'NOT_RUN','dictionary_generation':'NOT_RUN','model_optimization':'NOT_RUN',
        'refinement':'NOT_RUN','cache_writes':'NOT_RUN','production_checkpoint':'NOT_CREATED','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False,'requires_cif_review':False,'captured_code_execution':'NOT_RUN','mtz_used':False,
        'coordinate_decision':_coordinate_decision(False)}
    if phenix is not None:
        dictionaries=[_resolve(output,r) for r in bundle['native_dictionaries']];contexts=[_resolve(output,r) for r in bundle['context_phils']]
        captures=[];report['status']='REVIEW';report['phenix_version']=phenix.version
        try:
            for name,policy in [('native_baseline',disabled_copy),('native_active',active)]:
                capture=inspect_native_bundle(model,dictionaries,output/'native'/name,phenix.executables['phenix.python'],
                    environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=timeout_seconds,
                    phil_files=[policy,*contexts],inventory_detail='linked',policy_inventory=True,energy_inventory=True,
                    phil_namespace_policy='refinement-root-to-interpreter-v1')
                if 'returncode' in capture.get('execution',{}):report['new_native_calls']+=1
                report[name]={'receipt':_ref(Path(capture['native_directory'])/'native_receipt.json',output)}
                captures.append(capture)
                if not _native_ok(capture):break
            if len(captures)==2 and all(_native_ok(c) for c in captures):
                qualification=_qualify(*(c['native_validation'] for c in captures),model,active,plan,sources,dictionaries,bundle,output)
                _dump(output/'qualification.json',qualification);report['qualification']={'artifact':_ref(output/'qualification.json',output)}
                if qualification['mechanics_checks_pass']:
                    report['status']='MIXED_LINKED_RECOVERY_MECHANICS_PASS';report['coordinate_decision']=_coordinate_decision(True)
        except (ValueError,OSError,KeyError,TypeError,StopIteration,IndexError) as exc:report['error']=type(exc).__name__+': '+str(exc)
    report['source_inputs_preserved']=all(p.read_bytes()==data for p,data in originals.items())
    if not report['source_inputs_preserved']:raise ValueError('Linked recovery changed a preserved input')
    return _publish(output,report)


def read_mixed_linked_recovery(directory):
    from .cif_mixed_recovery import read_mixed_recovery,_resolve as resolve
    from .cif_mixed_native import _native_ok
    from .cif_postmr_cached_model import cached_preparation_replays
    root=Path(directory)
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe linked recovery directory')
    report=json.loads((root/REPORT).read_bytes())
    if (report.get('policy_id')!=POLICY_ID or report.get('status') not in {'PREPARED_ONLY','REVIEW','MIXED_LINKED_RECOVERY_MECHANICS_PASS'}
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
            or report.get('scientific_qualification')!='NOT_ASSESSED' or report.get('production_checkpoint')!='NOT_CREATED'
            or report.get('policy_authority')!='NARestraints' or report.get('baseline_scope')!=BASELINE_SCOPE
            or any(report.get(k) is not True for k in ['source_inputs_preserved','model_preserved','unrelated_numerics_preserved'])
            or report.get('mtz_used') is not False or any(report.get(k)!='NOT_RUN' for k in ['coot_execution','readyset_execution','dictionary_generation',
                'model_optimization','refinement','cache_writes','captured_code_execution'])
            or type(report.get('timeout_seconds')) is not int or not 1<=report['timeout_seconds']<=60):raise ValueError('Linked recovery claims unsupported scope')
    refs=report['outputs']
    if len(refs)!=len({r['path'] for r in refs}):raise ValueError('Duplicate linked recovery artifact')
    for ref in refs:_resolve(root,ref)
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Linked recovery contains a symlink')
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}:actual.add(p.relative_to(root).as_posix())
    if actual!={r['path'] for r in refs}:raise ValueError('Linked recovery artifact inventory differs')
    inputs=report['inputs'];frozen=_resolve(root,inputs['recovery_report']).parent
    recovery=read_mixed_recovery(frozen);plan=json.loads(_resolve(root,inputs['plan']).read_bytes())
    sources,_,targets,_,summary=_selection(frozen,recovery,plan)
    if targets!=report['targets']:raise ValueError('Linked recovery target scope differs')
    expected={'model':resolve(frozen,recovery['inputs']['model']),'active_policy':resolve(frozen,recovery['inputs']['active_policy'])}
    if (any(_resolve(root,inputs[k])!=p for k,p in expected.items())
            or set(inputs['sources'])!=set(sources) or any(_resolve(root,inputs['sources'][c])!=p for c,p in sources.items())
            or not _same_bytes(inputs['plan'],summary['parent_input_bindings']['plan'])
            or not _same_bytes(inputs['disabled_policy'],summary['parent_input_bindings']['disabled_policy'])):
        raise ValueError('Linked recovery parent bindings differ')
    with TemporaryDirectory(prefix='cif-linked-recovery-reader-') as temporary:
        replay_root=Path(temporary).resolve();bundle=_prepare_bundle(replay_root,frozen,recovery,plan)
        if not cached_preparation_replays(report['bundle'],bundle):raise ValueError('Linked recovery preparation does not reproduce')
        for p in (replay_root/'bundle').rglob('*'):
            if not p.is_file():continue
            target=root/p.relative_to(replay_root)
            if p.name=='preparation_receipt.json':
                if not cached_preparation_replays(json.loads(target.read_bytes()),json.loads(p.read_bytes())):raise ValueError('Linked preparation receipt differs')
            elif target.read_bytes()!=p.read_bytes():raise ValueError('Linked preparation bytes differ')
    bundle=report['bundle'];model=expected['model'];active=expected['active_policy'];disabled=_resolve(root,inputs['disabled_policy'])
    dictionaries=[_resolve(root,r) for r in bundle['native_dictionaries']];contexts=[_resolve(root,r) for r in bundle['context_phils']]
    captures=[];count=0
    for name,policy in [('native_baseline',disabled),('native_active',active)]:
        evidence=report[name]
        if 'receipt' not in evidence:
            if evidence!={'status':'NOT_RUN'}:raise ValueError('Unexplained native evidence')
            continue
        capture=_capture(root,evidence['receipt'],model,dictionaries,[policy,*contexts])
        if (capture.get('execution',{}).get('timeout_seconds')!=report['timeout_seconds']
                or capture.get('phenix_version')!=report.get('phenix_version')):raise ValueError('Native deadline or version differs')
        count+=int('returncode' in capture.get('execution',{}));captures.append(capture)
    if report['new_native_calls']!=count or report.get('maximum_native_calls')!=2 or count>2:raise ValueError('Linked native counters differ')
    if len(captures)==2 and any(captures[0].get(k)!=captures[1].get(k) for k in ['executable_provenance','executable_sha256']):
        raise ValueError('Native captures use different selected interpreters')
    if 'artifact' in report['qualification']:
        if len(captures)!=2 or not all(_native_ok(c) for c in captures):raise ValueError('Qualification lacks two completed native captures')
        qualification=json.loads(_resolve(root,report['qualification']['artifact']).read_bytes())
        fresh=_qualify(*(c['native_validation'] for c in captures),model,active,plan,sources,dictionaries,bundle,root)
        if not qualification_replays(qualification,fresh):raise ValueError('Linked native qualification does not reproduce')
    else:
        if report['qualification']!={'status':'NOT_RUN'}:raise ValueError('Unexplained linked qualification')
        qualification=None
    if report['status']=='PREPARED_ONLY' and (count or report['qualification']!={'status':'NOT_RUN'}):raise ValueError('Prepared linked recovery claims execution')
    if report['status']=='MIXED_LINKED_RECOVERY_MECHANICS_PASS' and (count!=2 or qualification is None
            or qualification.get('mechanics_checks_pass') is not True or report['coordinate_decision'].get('native_usable') is not True):
        raise ValueError('Incomplete linked recovery PASS evidence')
    usable=qualification is not None and qualification.get('mechanics_checks_pass') is True
    if (report['coordinate_decision']!=_coordinate_decision(usable)
            or qualification is not None and report['status']!=('MIXED_LINKED_RECOVERY_MECHANICS_PASS' if usable else 'REVIEW')):
        raise ValueError('Linked recovery coordinate decision does not reproduce')
    return report
