"""Source-declared group and incoming-phosphate context, with fixed mechanics.

This diagnostic adapts an already interpreted numerical bundle. It does not
declare ReadySet's chemical state source-preserving, repair numerical targets,
or adopt the result. The verified linked parent remains an explicit anchor.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

POLICY_ID='cif-mixed-linked-context-v1'
ANCHOR='mixed_context_directory'
PARENT_ANCHOR='linked_parent_directory'
REPORT='mixed_context.json'
BASELINE_SCOPE='SAME_CONTEXT_BUNDLE_WITH_DECLARED_NA_POLICY_DISABLED; SAVED_PARENT_MECHANICS_COMPARED_SEPARATELY'
_SCOPE_FIELDS=('coot_execution','readyset_execution','dictionary_generation','model_optimization',
    'refinement','cache_writes','captured_code_execution')


def _ref(path,root,*,parent=False):
    from .cif_mixed_recovery import _safe
    path,root=Path(path),Path(root)
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Context artifact traverses a symlink')
    name=path.relative_to(root).as_posix()
    if not _safe(name):raise ValueError('Unsafe context artifact path')
    data=path.read_bytes()
    return {'anchor':PARENT_ANCHOR if parent else ANCHOR,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}


def _resolve(root,parent,ref):
    from .cif_mixed_recovery import _safe
    if not isinstance(ref,dict) or ref.get('anchor') not in {ANCHOR,PARENT_ANCHOR} or not _safe(ref.get('path')):
        raise ValueError('Unsafe context artifact reference')
    external=ref['anchor']==PARENT_ANCHOR;directory=Path(parent) if external else Path(root)
    path=directory/ref['path']
    if _ref(path,directory,parent=external)!=ref:raise ValueError('Context artifact bytes differ')
    return path


def _dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _external(root,ref):
    from .cif_mixed_linked_recovery import _resolve as resolve
    return _ref(resolve(root,ref),root,parent=True)


def _parent_inputs(root):
    from .cif_mixed_linked_recovery import read_mixed_linked_recovery,_resolve as resolve,_capture
    from .cif_mixed_native import _native_ok
    root=Path(root);parent=read_mixed_linked_recovery(root)
    if parent['status']=='PREPARED_ONLY':raise ValueError('Require two saved linked native captures')
    refs=parent['inputs'];bundle=parent['bundle']
    model=resolve(root,refs['model']);active=resolve(root,refs['active_policy']);disabled=resolve(root,refs['disabled_policy'])
    plan=json.loads(resolve(root,refs['plan']).read_bytes());sources={c:resolve(root,r) for c,r in refs['sources'].items()}
    dictionaries=[resolve(root,r) for r in bundle['effective_dictionaries']]
    native=[resolve(root,r) for r in bundle['native_dictionaries']];contexts=[resolve(root,r) for r in bundle['context_phils']]
    captures=[]
    for name,policy in [('native_baseline',disabled),('native_active',active)]:
        if 'receipt' not in parent[name]:raise ValueError('Require complete saved linked captures')
        capture=_capture(root,parent[name]['receipt'],model,native,[policy,*contexts])
        if not _native_ok(capture):raise ValueError('Require successful saved linked captures')
        captures.append(capture)
    q=json.loads(resolve(root,parent['qualification']['artifact']).read_bytes())
    allowed={'baseline:complete_heavy_sites','baseline:dna_classification','active:complete_heavy_sites','active:dna_classification'}
    if any(v is not True for k,v in q['membership']['checks'].items() if k not in allowed):
        raise ValueError('Saved linked parent has unrelated mechanical failures')
    if any(c['status'] not in {'PASS','UNSUPPORTED'} and c['check']!='full-model-narestraints-membership' for c in q['checks']):
        raise ValueError('Saved linked parent has unrelated selected-site failures')
    return parent,model,active,disabled,plan,sources,dictionaries,captures


def _effective_graph(source,numerical,code):
    from .cif_source_classification import _source_declarations
    from .postmr_restoration import source_graph_fragment
    from .cif_linked_preparation import atom_rows,component_values
    declarations=_source_declarations(source,code);graph=source_graph_fragment(source,code)
    source_values=component_values(source,code);source_atoms=atom_rows(source_values);values=component_values(numerical,code);atoms=atom_rows(values)
    heavy=lambda rows:{n:r['type_symbol'].strip().upper() for n,r in rows.items() if r['type_symbol'].strip().upper() not in {'H','D'}}
    left,right=heavy(source_atoms),heavy(atoms)
    if set(right)-set(left) or set(left)-set(right)-{'OP3'} or any(left[n]!=e for n,e in right.items()):
        raise ValueError('Effective heavy names/elements exceed source-bound context')
    a=values.get('_chem_comp_bond.atom_id_1',[]);b=values.get('_chem_comp_bond.atom_id_2',[])
    if not a or len(a)!=len(b):raise ValueError('Incomplete effective phosphate graph')
    edges=[frozenset((x,y)) for x,y in zip(a,b)]
    if any(len(e)!=2 or not e<=atoms.keys() for e in edges) or len(edges)!=len(set(edges)):
        raise ValueError('Ambiguous effective phosphate graph')
    source_edges={frozenset((x,y)) for x,y in zip(source_values.get('_chem_comp_bond.atom_id_1',[]),
        source_values.get('_chem_comp_bond.atom_id_2',[])) if {x,y}<=left.keys()}
    effective_edges={e for e in edges if e<=right.keys()}
    if effective_edges!={e for e in source_edges if e<=right.keys()}:
        raise ValueError('Effective heavy adjacency exceeds the source-bound context')
    required={'P','OP1','OP2',"O5'","C5'","C3'","O3'"}
    if not required<=atoms.keys() or 'O3P' in atoms:raise ValueError('Unsupported effective phosphate atom convention')
    if not all(frozenset(pair) in edges for pair in [('P','OP1'),('P','OP2'),('P',"O5'"),("O3'","C3'")]):
        raise ValueError('Effective graph does not support the declared phosphate linkage')
    if 'OP3' in atoms:
        neighbors={next(iter(e-{'OP3'})) for e in edges if 'OP3' in e}
        if atoms['OP3']['type_symbol'].upper()!='O' or {n for n in neighbors if atoms[n]['type_symbol'].upper() not in {'H','D'}}!={'P'}:
            raise ValueError('OP3 is not an unbridged phosphate oxygen leaf')
        for name in neighbors-{'P'}:
            if {next(iter(e-{name})) for e in edges if name in e}!={'OP3'}:raise ValueError('OP3 hydrogen has another attachment')
    return {'source_declarations':declarations,'source_graph':graph,'heavy_name_elements_bound':True}


def _select_context(model,plan,sources,dictionaries,baseline,active):
    from .cif_mixed_linked_recovery import _contexts
    from .cif_linked_preparation import _model_inventory
    from .cif_fragment_restoration import _model
    from .ligand_profiles import dictionary_component_codes,_parameterized_codes
    inventory=_model_inventory(Path(model));expected=plan['target_site_components']
    if {s:v['code'] for s,v in inventory.items()}!=expected or set(sources)!=set(expected.values()):
        raise ValueError('Context model, source and declared plan scopes differ')
    providers={}
    for path in dictionaries:
        for code in dictionary_component_codes(Path(path)):
            if code in providers:raise ValueError('Ambiguous context numerical provider')
            providers[code]=Path(path)
    if set(providers)!=set(sources):raise ValueError('Context numerical provider scope differs')
    _model(baseline,Path(model),coordinates_match=True);_model(active,Path(model),coordinates_match=True)
    selected={};states=[]
    for native in [baseline,active]:
        rows=native['monomer_mappings']['rows'];mapping={r['site']:r for r in rows}
        if len(rows)!=len(mapping) or {s:r['resname'].strip() for s,r in mapping.items()}!=expected:
            raise ValueError('Saved native monomer scope differs')
        state={}
        for site,row in mapping.items():
            meta=row['metadata'];missing=row.get('missing_non_hydrogen_atoms',{});extra=row.get('unexpected_atoms',{})
            if (missing.get('status')!='RECORDED' or extra.get('status')!='RECORDED' or extra.get('atom_ids')!=[]
                    or missing.get('atom_ids') not in [[],['OP3']]
                    or meta.get('classification')!={'status':'RECORDED','value':'DNA'}):
                raise ValueError('Unsupported saved native classification or atom deficit: '+site)
            state[site]={'group':meta.get('group'),'missing':missing['atom_ids'],'definition':meta.get('effective_definition'),
                'modifications':row.get('chem_mod_ids')}
            reasons={'group':meta.get('group')!='DNA','missing_op3':missing['atom_ids']==['OP3']}
            if any(reasons.values()):selected[site]=reasons
        states.append(state)
    if states[0]!=states[1]:raise ValueError('Baseline/active saved component context differs')
    codes=sorted({expected[s] for s in selected})
    if not codes:raise ValueError('No supported linked context defects were recorded')
    contexts=_contexts(Path(model),plan,codes);eligibility={}
    for code in codes:
        if code not in _parameterized_codes(providers[code]):raise ValueError('Context target lacks complete numerical rows')
        eligibility[code]=_effective_graph(sources[code],providers[code],code)
        for context in contexts[code]:
            if selected.get(context['site'],{}).get('missing_op3') and not context['incoming_site']:
                raise ValueError('Missing OP3 has no declared incoming phosphate linkage')
    return {'components':codes,'contexts':contexts,'site_reasons':{s:selected[s] for s in sorted(selected)},'source_eligibility':eligibility}


def _prepare_component(source,numerical,model,contexts,output,*,code,normalize_group):
    from .cif_linked_preparation import (component_values,atom_rows,hydrogen_neighbors,_model_inventory,
        _selection,_prune,_render)
    from .cif_terminal_qualification import projection_site_plan
    from .ligand_profiles import _emit
    source,numerical,model,output=map(Path,(source,numerical,model,output))
    if (output.exists() or any(p.is_symlink() for p in [output,*output.parents])
            or any(output.resolve().is_relative_to(p.parent.resolve()) for p in [source,numerical,model])):
        raise ValueError('Require separate context component output')
    eligibility=_effective_graph(source,numerical,code);original=component_values(numerical,code);values=deepcopy(original)
    if type(normalize_group) is not bool:raise ValueError('Require explicit group normalization selection')
    if normalize_group:values['_chem_comp.group']=['DNA']
    atoms=atom_rows(values);inventory=_model_inventory(model)
    if (not contexts or len({c['site'] for c in contexts})!=len(contexts)
            or {c['site'] for c in contexts}!={s for s,v in inventory.items() if v['code']==code}):
        raise ValueError('Context plan must cover every model site sharing the component')
    projected=[];sites=[];mod_blocks=[];phils=[];output.mkdir(parents=True)
    base=output/'base_dictionary.cif';base.write_text(_render(values,code))
    if component_values(base,code)!=values:raise ValueError('Context header serialization changed parsed rows')
    for context in contexts:
        site=context['site'];selection=_selection(site,code);incoming=context.get('incoming_site');outgoing=context.get('outgoing_site')
        if inventory[site]['code']!=code:raise ValueError('Context component/site identity differs')
        if context.get('symmetry_operation') not in {None,'x,y,z'} or context.get('experimental_passthrough'):
            raise ValueError('Unsupported context symmetry or experimental pass-through')
        if context.get('five_prime_state') not in ({'linked'} if incoming else {'free_OH','phosphate'}) or context.get('three_prime_state')!=('linked' if outgoing else 'free_OH'):
            raise ValueError('Context terminal state and declared edges disagree')
        for neighbor,name in [(incoming,"O3'"),(outgoing,'P')]:
            if neighbor and (neighbor==site or neighbor not in inventory or name not in inventory[neighbor]['atoms']):
                raise ValueError('Context link endpoint is absent or self-linked')
        coordinate=inventory[site]['atoms'];removed=set()
        if incoming:
            if not {'P','OP1','OP2'}<=coordinate or 'OP3' in coordinate:raise ValueError('Internal model phosphate differs')
            if 'OP3' in atoms:removed={'OP3',*hydrogen_neighbors(values,'OP3')}
        elif context['five_prime_state']=='phosphate':
            if not {'P','OP1','OP2','OP3'}<=coordinate:raise ValueError('Terminal phosphate must retain OP3')
        elif coordinate&{'P','OP1','OP2','OP3'}:raise ValueError('Free terminal phosphate inventory differs')
        if removed&coordinate:raise ValueError('Context preparation would remove a coordinate atom')
        derivative=_prune(values,removed,outgoing=False)
        if coordinate-atom_rows(derivative).keys():raise ValueError('Context projection lacks coordinate atoms')
        identifier='NASC'+sha256((code+'|'+site+'|'+json.dumps(context,sort_keys=True)).encode()).hexdigest()[:10] if removed else None
        if identifier:
            mod={'data_':'mod_'+identifier}
            for i,field in enumerate(['mod_id','function','atom_id','new_atom_id','new_type_symbol','new_type_energy','new_partial_charge']):
                mod['_chem_mod_atom.'+field]=[[identifier,'delete',name,'.','.','.','.'][i] for name in sorted(removed)]
            mod_blocks.append(_emit(mod));phils.append('refinement.pdb_interpretation.apply_cif_modification {\n'
                f'  data_mod = {identifier}\n  residue_selection = {selection}\n}}\n')
        path=output/('projected_'+site.replace(':','_')+'.cif');path.write_text(_render(derivative,code))
        if component_values(path,code)!=derivative:raise ValueError('Context projection serialization changed parsed rows')
        row={**context,**projection_site_plan(path,code,site),'selection':selection,'modification_id':identifier,'deleted_atoms':sorted(removed)}
        sites.append(row);projected.append(path)
    modifications=output/'site_modifications.cif';modifications.write_text('\n'.join(mod_blocks) if mod_blocks else 'data_mod_context_sites\n# No atom modifications required.\n')
    parameters=output/'site_modifications.phil';parameters.write_text(''.join(phils))
    receipt={'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'PREPARED_ONLY','source_eligibility':eligibility,
        'source_sha256':sha256(source.read_bytes()).hexdigest(),'numerical_sha256':sha256(numerical.read_bytes()).hexdigest(),
        'model_sha256':sha256(model.read_bytes()).hexdigest(),'metadata_change':{'field':'_chem_comp.group','before':original.get('_chem_comp.group'),'after':values.get('_chem_comp.group')},
        'sites':sites,'other_parsed_rows_preserved':True,'outgoing_hydrogens_and_energy_types':'UNCHANGED',
        'source_state_repair':'NOT_PERFORMED','automatic_adoption':False,'requires_cif_review':False,
        'outputs':{k:{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
            for k,p in [('dictionary',base),('modifications',modifications),('parameters',parameters)]}}
    _dump(output/'context_preparation.json',receipt)
    return receipt


def _prepare_bundle(root,parent_root,parent,model,plan,sources,dictionaries,captures):
    from .cif_linked_preparation import component_values
    from .ligand_profiles import _exclude_components,_blocks,dictionary_component_codes
    from .cif_mixed_native import select_native_dictionaries
    selection=_select_context(model,plan,sources,dictionaries,*(c['native_validation'] for c in captures))
    codes=set(selection['components']);providers={c:p for p in dictionaries for c in dictionary_component_codes(p)}
    preparations={};projections={s:{'component':v['component'],'dictionary':_external(parent_root,v['dictionary'])}
        for s,v in parent['bundle']['site_projections'].items()}
    files=[];context_phils=[_external(parent_root,r) for r in parent['bundle']['context_phils']]
    for code in selection['components']:
        out=root/'bundle/prepared'/code
        receipt=_prepare_component(sources[code],providers[code],model,selection['contexts'][code],out,code=code,
            normalize_group=any(r['group'] for s,r in selection['site_reasons'].items() if plan['target_site_components'][s]==code))
        preparations[code]={'directory':{'anchor':ANCHOR,'path':out.relative_to(root).as_posix()},'receipt':receipt}
        files.append(out/receipt['outputs']['dictionary']['path'])
        if any(s['modification_id'] for s in receipt['sites']):
            files.append(out/receipt['outputs']['modifications']['path']);context_phils.append(_ref(out/receipt['outputs']['parameters']['path'],root))
        for row in receipt['sites']:
            site=row['site']
            if site in projections:raise ValueError('Context target overlaps an existing prepared site')
            projections[site]={'component':code,'dictionary':_ref(out/('projected_'+site.replace(':','_')+'.cif'),root)}
    resources=root/'bundle/resources';resources.mkdir(parents=True);retained=[];delta=[]
    for i,path in enumerate(dictionaries):
        present=dictionary_component_codes(path);selected=present&codes
        if not selected:
            retained.append(path);delta.append({'input_index':i,'removed_components':[],'retained_components':sorted(present),
                'exact_original':_ref(path,parent_root,parent=True)});continue
        out=resources/f'{i:03d}.cif';filtered,kept=_exclude_components(path,codes,out);bystanders=present-codes
        def blocks(p):
            return Counter(b.text.rstrip('\r\n') for b in _blocks(p) if not (set(b.values.get('_chem_comp_atom.comp_id',[]))&codes)
                and not ('_chem_comp.id' in b.values and not b.values.get('_chem_comp_atom.comp_id'))) if p else Counter()
        if (kept!=bystanders or not all(component_values(path,c)==component_values(filtered,c) for c in bystanders)
                or blocks(path)!=blocks(filtered)):
            raise ValueError('Context filtering changed unrelated parsed rows or blocks')
        if filtered:retained.append(filtered)
        delta.append({'input_index':i,'removed_components':sorted(selected),'retained_components':sorted(kept),
            'unrelated_rows_preserved':True,'unrelated_blocks_preserved':True,'retained':_ref(filtered,root) if filtered else None,
            'block_separator_policy':'TRAILING_CR_LF_ONLY; ALL_OTHER_RETAINED_BLOCK_BYTES_EXACT'})
    effective=[*retained,*files];native,canonical=select_native_dictionaries(effective,sources)
    all_codes=[c for p in effective for c in dictionary_component_codes(p)]
    if len(all_codes)!=len(set(all_codes)) or set(all_codes)!=set(sources):raise ValueError('Prepared context component scope differs')
    def bound(p):return _ref(p,root) if p.is_relative_to(root) else _ref(p,parent_root,parent=True)
    return {'selection':selection,'preparations':preparations,'site_projections':projections,'resource_delta':delta,
        'effective_dictionaries':[bound(p) for p in effective],'native_dictionaries':[bound(p) for p in native],
        'context_phils':context_phils,'installed_canonical_components':canonical,
        'preserved_source_findings':deepcopy(parent['bundle']['preserved_source_findings'])}


def _mechanical_equivalence(old,new):
    from .cif_construction_native import NATIVE_KINDS
    from .cif_terminal_qualification import _proxy_subset
    from .cif_linked_qualification import native_backbone_links
    from .cif_candidate_usability import _close,energy_inventory_checks
    identity_fields={'model_id','chain_id','resseq','icode','resname','altloc'}
    atom_fields={'atom_id','atom_name_field','element','i_seq','identity','label','occupancy','xyz'}
    def atoms(record):
        inventory={};indices=set()
        for atom in record['atoms']:
            identity=atom['identity'];index=atom['i_seq'];point=atom['xyz'];occupancy=atom['occupancy']
            if (set(atom)!=atom_fields or not isinstance(identity,dict) or set(identity)!=identity_fields
                    or any(not isinstance(v,str) for v in identity.values())
                    or not isinstance(atom['atom_id'],str) or not atom['atom_id'] or atom['atom_id'].strip()!=atom['atom_id']
                    or not isinstance(atom['atom_name_field'],str) or atom['atom_name_field'].strip()!=atom['atom_id']
                    or not isinstance(atom['element'],str) or not atom['element'].strip()
                    or not isinstance(atom['label'],str) or not atom['label'] or type(index) is not int or index<0 or index in indices
                    or type(occupancy) not in (int,float) or not math.isfinite(occupancy)
                    or not isinstance(point,list) or len(point)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in point)):
                raise ValueError('Incomplete structured native atom inventory')
            key=tuple(identity[k].strip() for k in ['model_id','chain_id','resseq','icode','resname','altloc'])+(atom['atom_id'],atom['element'].strip())
            if not key[2] or not key[4] or key in inventory:raise ValueError('Ambiguous structured native atom identity')
            inventory[key]={'xyz':point,'occupancy':occupancy};indices.add(index)
        if indices!=set(range(record['atom_count'])):raise ValueError('Incomplete native gradient index coverage')
        return inventory
    checks={'exact_named_native_atoms':atoms(old)==atoms(new),'exact_backbone_links':native_backbone_links(old)==native_backbone_links(new),
        'same_installed_api_sources':old['installed_api_sources']==new['installed_api_sources']}
    for kind in sorted(NATIVE_KINDS):checks['unchanged-native-proxies:'+kind]=_proxy_subset(old,set(),kind)==_proxy_subset(new,set(),kind)
    for label,record in [('saved',old),('context',new)]:checks.update({label+':'+k:v for k,v in energy_inventory_checks(record).items()})
    def named(record,snapshot):
        gradient=snapshot['gradient'];result={}
        for a in record['atoms']:
            identity=a['identity'];key=tuple(identity[k].strip() for k in ['model_id','chain_id','resseq','icode','resname','altloc'])+(a['atom_id'],a['element'].strip())
            if key in result:raise ValueError('Duplicate named native gradient identity')
            result[key]=gradient[3*a['i_seq']:3*a['i_seq']+3]
        return result
    old_snapshots=old['energy_inventory']['snapshots'];new_snapshots=new['energy_inventory']['snapshots']
    equal=len(old_snapshots)==len(new_snapshots)==2;terms_equal=equal;counts_equal=equal
    for a,b in zip(old_snapshots,new_snapshots):
        left,right=named(old,a),named(new,b)
        equal &= (_close(a['target'],b['target']) and left.keys()==right.keys()
            and all(len(left[k])==len(right[k])==3 and all(_close(x,y) for x,y in zip(left[k],right[k])) for k in left))
        terms_equal &= (isinstance(a.get('terms'),dict) and isinstance(b.get('terms'),dict) and bool(a['terms'])
            and a['terms'].keys()==b['terms'].keys() and all(_close(v,b['terms'][k]) for k,v in a['terms'].items()))
        counts_equal &= (isinstance(a.get('proxy_counts'),dict) and isinstance(b.get('proxy_counts'),dict) and bool(a['proxy_counts'])
            and a['proxy_counts'].keys()==b['proxy_counts'].keys()
            and all(type(v) is type(b['proxy_counts'][k]) and (v is None or type(v) is int and v>=0)
                and v==b['proxy_counts'][k] for k,v in a['proxy_counts'].items()))
    checks['same_full_targets_and_named_gradients']=equal
    checks['same_energy_terms']=terms_equal;checks['same_energy_proxy_counts']=counts_equal
    return {'checks':checks,'mechanics_unchanged':bool(checks) and all(v is True for v in checks.values()),
        'comparison_policy':'EXACT_STRUCTURED_NAMED_PROXY_COUNTERS; ESTABLISHED_NATIVE_ENERGY_REPEAT_TOLERANCE',
        'scope':'FIXED_COORDINATES_ONLY','nonbonded_pair_identity':'NOT_ASSESSED'}


def _qualify(before,after,parent_captures,model,active,plan,sources,dictionaries,bundle,root,parent_root,parent):
    from .cif_mixed_native import qualify_mixed_native
    from .cif_linked_qualification import site_definition_checks
    from .cif_terminal_qualification import definition_projection_checks
    from .cif_mixed_linked_recovery import _canonical_qualification
    from .cif_effective_source_recovery import mechanics_can_continue
    projections={s:(_resolve(root,parent_root,v['dictionary']),v['component']) for s,v in bundle['site_projections'].items()}
    membership=qualify_mixed_native(before,after,model,active,plan,sources,dictionaries,site_projections=projections)
    equivalence={label:_mechanical_equivalence(old['native_validation'],new) for label,old,new in zip(['baseline','active'],parent_captures,[before,after])}
    checks=[]
    def check(name,ok,**detail):checks.append({'check':name,'status':'PASS' if ok else 'REVIEW',**detail})
    check('full-model-narestraints-membership',membership['mechanics_checks_pass'])
    all_preparations=[v['receipt'] for v in parent['bundle']['preparations'].values()]+[v['receipt'] for v in bundle['preparations'].values()]
    for label,native in [('baseline',before),('active',after)]:
        check(label+':saved-parent-native-mechanics-unchanged',equivalence[label]['mechanics_unchanged'])
        checks.extend(dict(c,check=label+':'+c['check']) for c in site_definition_checks(native,all_preparations))
        checks.extend(dict(c,check=label+':'+c['check']) for c in definition_projection_checks(native,projections))
        mappings={r['site']:r for r in native['monomer_mappings']['rows']}
        for preparation in all_preparations:
            for site in preparation['sites']:
                expected={'status':'RECORDED','ids':[site['modification_id']] if site['modification_id'] else []}
                check(label+':exact-context-modifier:'+site['site'],mappings[site['site']].get('chem_mod_ids')==expected)
    normalized={'checks':[dict(c,check=c['check'].split(':',1)[1]) if c['check'].startswith(('baseline:effective-site-formal-charges:','active:effective-site-formal-charges:')) else c for c in checks]}
    usable=mechanics_can_continue(normalized)
    return _canonical_qualification({'schema_version':1,'policy_id':POLICY_ID,'status':'MIXED_CONTEXT_MECHANICS_PASS' if usable else 'REVIEW',
        'mechanics_checks_pass':usable,'membership':membership,'saved_parent_equivalence':equivalence,'checks':checks,
        'source_chemical_findings':'PRESERVED_SEPARATELY; NOT_PROMOTED_BY_CONTEXT_OR_NATIVE_MEMBERSHIP',
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False})


def _decision(usable):
    return {'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model','native_usable':True if usable else 'NOT_YET_QUALIFIED',
        'requires_cif_review':False,'automatic_adoption':False}


def _publish(root,parent_root,report):
    if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('Context output contains a symlink')
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}]
    _dump(root/REPORT,report);read_mixed_context(root,linked_parent_directory=parent_root)
    return report


def audit_mixed_context(linked_parent_directory,phenix,output,*,timeout_seconds=60):
    from .cif_native_validation import inspect_native_bundle
    from .cif_mixed_native import _native_ok
    from .cif_mixed_linked_recovery import _capture
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=60:raise ValueError('Require an integer fixed native deadline from 1 to 60 seconds')
    parent_root=Path(linked_parent_directory);root=Path(output).absolute()
    if root.exists() or any(p.is_symlink() for p in [root,*root.parents]) or root.resolve().is_relative_to(parent_root.resolve()):
        raise ValueError('Require fresh separate context output')
    parent,model,active,disabled,plan,sources,dictionaries,old_captures=_parent_inputs(parent_root)
    originals={p:p.read_bytes() for p in [parent_root/'mixed_linked_recovery.json',model,active,disabled,*sources.values(),*dictionaries]}
    root.mkdir(parents=True);bundle=_prepare_bundle(root,parent_root,parent,model,plan,sources,dictionaries,old_captures)
    refs=parent['inputs']
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','targets':bundle['selection']['components'],
        'inputs':{'linked_parent_report':_ref(parent_root/'mixed_linked_recovery.json',parent_root,parent=True),
            **{k:_external(parent_root,refs[k]) for k in ['model','active_policy','disabled_policy','plan']},
            'sources':{c:_external(parent_root,r) for c,r in refs['sources'].items()}},'bundle':bundle,
        'native_baseline':{'status':'NOT_RUN'},'native_active':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'new_native_calls':0,'saved_native_calls':2,'maximum_native_calls':2,'timeout_seconds':timeout_seconds,
        'policy_authority':'NARestraints','baseline_scope':BASELINE_SCOPE,'source_inputs_preserved':True,'model_preserved':True,
        'unrelated_numerics_preserved':True,'source_state_repair':'NOT_PERFORMED',
        **{k:'NOT_RUN' for k in _SCOPE_FIELDS},'production_checkpoint':'NOT_CREATED','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False,'requires_cif_review':False,'mtz_used':False,'coordinate_decision':_decision(False)}
    if phenix is not None:
        native_files=[_resolve(root,parent_root,r) for r in bundle['native_dictionaries']];contexts=[_resolve(root,parent_root,r) for r in bundle['context_phils']]
        captures=[];report.update(status='REVIEW',phenix_version=phenix.version)
        try:
            for name,policy in [('native_baseline',disabled),('native_active',active)]:
                capture=inspect_native_bundle(model,native_files,root/'native'/name,phenix.executables['phenix.python'],
                    environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=timeout_seconds,
                    phil_files=[policy,*contexts],inventory_detail='linked',policy_inventory=True,energy_inventory=True,
                    phil_namespace_policy='refinement-root-to-interpreter-v1')
                if 'returncode' in capture.get('execution',{}):report['new_native_calls']+=1
                report[name]={'receipt':_ref(Path(capture['native_directory'])/'native_receipt.json',root)};captures.append(capture)
                if not _native_ok(capture):break
            if len(captures)==2 and all(_native_ok(c) for c in captures):
                q=_qualify(*(c['native_validation'] for c in captures),old_captures,model,active,plan,sources,native_files,bundle,root,parent_root,parent)
                _dump(root/'qualification.json',q);report['qualification']={'artifact':_ref(root/'qualification.json',root)}
                if q['mechanics_checks_pass']:report.update(status='MIXED_CONTEXT_MECHANICS_PASS',coordinate_decision=_decision(True))
        except (ValueError,OSError,KeyError,TypeError,IndexError,StopIteration) as exc:report['error']=type(exc).__name__+': '+str(exc)
    if not all(p.read_bytes()==data for p,data in originals.items()):raise ValueError('Context audit changed preserved parent inputs')
    return _publish(root,parent_root,report)


def read_mixed_context(directory,*,linked_parent_directory):
    from .cif_mixed_linked_recovery import _capture,qualification_replays
    from .cif_mixed_native import _native_ok
    root,parent_root=Path(directory),Path(linked_parent_directory)
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe context directory')
    record=root/REPORT
    if record.is_symlink():raise ValueError('Unsafe context report')
    report=json.loads(record.read_bytes())
    if (report.get('schema_version')!=1 or report.get('policy_id')!=POLICY_ID or report.get('status') not in {'PREPARED_ONLY','REVIEW','MIXED_CONTEXT_MECHANICS_PASS'}
            or any(report.get(k)!='NOT_RUN' for k in _SCOPE_FIELDS) or report.get('source_state_repair')!='NOT_PERFORMED'
            or report.get('production_checkpoint')!='NOT_CREATED' or report.get('scientific_qualification')!='NOT_ASSESSED'
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False or report.get('mtz_used') is not False
            or report.get('policy_authority')!='NARestraints' or report.get('baseline_scope')!=BASELINE_SCOPE
            or any(report.get(k) is not True for k in ['source_inputs_preserved','model_preserved','unrelated_numerics_preserved'])
            or type(report.get('timeout_seconds')) is not int or not 1<=report['timeout_seconds']<=60):
        raise ValueError('Context report claims unsupported scope')
    refs=report['outputs']
    if len(refs)!=len({r['path'] for r in refs}) or any(r.get('anchor')!=ANCHOR for r in refs):raise ValueError('Context output inventory differs')
    for ref in refs:_resolve(root,parent_root,ref)
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Context output contains a symlink')
        if p.is_file() and p!=record and p.suffix not in {'.pickle','.pkl','.pyc'}:actual.add(p.relative_to(root).as_posix())
    if actual!={r['path'] for r in refs}:raise ValueError('Context output inventory differs')
    parent,model,active,disabled,plan,sources,dictionaries,old_captures=_parent_inputs(parent_root)
    parent_refs=parent['inputs'];expected={'linked_parent_report':_ref(parent_root/'mixed_linked_recovery.json',parent_root,parent=True),
        **{k:_external(parent_root,parent_refs[k]) for k in ['model','active_policy','disabled_policy','plan']},
        'sources':{c:_external(parent_root,r) for c,r in parent_refs['sources'].items()}}
    if report['inputs']!=expected:raise ValueError('Context parent bindings differ')
    with TemporaryDirectory(prefix='cif-context-reader-') as temporary:
        replay=Path(temporary).resolve();bundle=_prepare_bundle(replay,parent_root,parent,model,plan,sources,dictionaries,old_captures)
        if report['bundle']!=bundle or report['targets']!=bundle['selection']['components']:raise ValueError('Context preparation does not reproduce')
        for p in replay.rglob('*'):
            if p.is_file() and (root/p.relative_to(replay)).read_bytes()!=p.read_bytes():raise ValueError('Context preparation bytes differ')
    bundle=report['bundle'];native=[_resolve(root,parent_root,r) for r in bundle['native_dictionaries']];contexts=[_resolve(root,parent_root,r) for r in bundle['context_phils']]
    captures=[];count=0
    for name,policy in [('native_baseline',disabled),('native_active',active)]:
        evidence=report[name]
        if 'receipt' not in evidence:
            if evidence!={'status':'NOT_RUN'}:raise ValueError('Unexplained context native capture')
            continue
        if evidence['receipt'].get('anchor')!=ANCHOR:raise ValueError('Context native capture must be newly local')
        # The maintained reader binds exact staged dictionaries, worker, spec,
        # result and every output; its reference anchor is local to that reader.
        ref={**evidence['receipt'],'anchor':'mixed_linked_recovery_directory'}
        capture=_capture(root,ref,model,native,[policy,*contexts])
        if capture.get('execution',{}).get('timeout_seconds')!=report['timeout_seconds'] or capture.get('phenix_version')!=report.get('phenix_version'):
            raise ValueError('Context native deadline/version differs')
        count+=int('returncode' in capture.get('execution',{}));captures.append(capture)
    if (type(report.get('new_native_calls')) is not int or report['new_native_calls']!=count or count>2
            or report.get('maximum_native_calls')!=2 or report.get('saved_native_calls')!=2):raise ValueError('Context native counters differ')
    if len(captures)==2 and any(captures[0].get(k)!=captures[1].get(k) for k in ['executable_provenance','executable_sha256']):
        raise ValueError('Context reads use different selected interpreters')
    q=None
    if 'artifact' in report['qualification']:
        if len(captures)!=2 or not all(_native_ok(c) for c in captures):raise ValueError('Context qualification lacks two complete captures')
        q=json.loads(_resolve(root,parent_root,report['qualification']['artifact']).read_bytes())
        fresh=_qualify(*(c['native_validation'] for c in captures),old_captures,model,active,plan,sources,native,bundle,root,parent_root,parent)
        if not qualification_replays(q,fresh):raise ValueError('Context qualification does not reproduce')
    elif report['qualification']!={'status':'NOT_RUN'}:raise ValueError('Unexplained context qualification')
    if report['status']=='PREPARED_ONLY' and (count or q is not None):raise ValueError('Prepared context claims execution')
    usable=q is not None and q['mechanics_checks_pass'] is True
    if (report['coordinate_decision']!=_decision(usable) or usable and report['status']!='MIXED_CONTEXT_MECHANICS_PASS'
            or report['status']=='MIXED_CONTEXT_MECHANICS_PASS' and (not usable or count!=2)
            or q is not None and not usable and report['status']!='REVIEW'):
        raise ValueError('Context qualification/decision does not reproduce')
    return report
