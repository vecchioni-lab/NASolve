"""Compile declared pairing/stacking with pinned NARestraints recipes.

Diagnostic first slice: single-model, unambiguous residue selections; declared
Saenger 19/20 pairs and mapped stacks. Existing explicit edits and component
modifications survive. No distance-based pair guessing or coordinate editing.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

POLICY_ID='narestraints-explicit-membership-v1'
SS='pdb_interpretation.secondary_structure'


def _parse(text):
    """Read the bounded line-oriented PHIL emitted by the existing builders.

    This is not a PHIL evaluator. Unsupported syntax/settings stop compilation;
    the installed native parser remains the eventual parameter consumer.
    """
    nodes=[];stack=[];lines=text.splitlines(keepends=True)
    for index,line in enumerate(lines):
        line=line.split('#',1)[0].strip()
        if not line:continue
        if line=='}':
            if not stack:raise ValueError('Unbalanced PHIL')
            stack.pop()['end']=index+1;continue
        m=re.fullmatch(r'([\w.]+)\s*\{',line)
        if m:
            path=(stack[-1]['path']+'.' if stack else '')+m[1]
            node={'path':path,'start':index,'end':None,'fields':{},'children':[]}
            if stack:stack[-1]['children'].append(node)
            nodes.append(node);stack.append(node);continue
        m=re.fullmatch(r'([\w.]+)\s*=\s*(.+)',line)
        if not m or not stack:raise ValueError('Unsupported line-oriented PHIL syntax')
        if m[1] in stack[-1]['fields']:raise ValueError('Duplicate PHIL field')
        stack[-1]['fields'][m[1]]=m[2].strip()
    if stack:raise ValueError('Unbalanced PHIL')
    return nodes,lines


def _path(node):
    path=node['path'];return path[len('refinement.'):] if path.startswith('refinement.') else path


def _site_selection(text):
    m=re.fullmatch(r'''chain\s+(['"]?)([A-Za-z0-9])\1\s+and\s+resid\s+(-?\d+)''',text)
    if not m:raise ValueError('Require one explicit chain/residue selection')
    return m[2],m[3]


def _resolve(text,atoms):
    m=re.fullmatch(r'(.*?)\s+and\s+(\(?name\s+[A-Za-z0-9_]+(?:\s+or\s+name\s+[A-Za-z0-9_]+)*\)?)',text)
    if not m:raise ValueError('Unsupported generated atom selection')
    site=_site_selection(m[1]);names=re.findall(r'name\s+([A-Za-z0-9_]+)',m[2])
    selected=[a for a in atoms if (a['identity']['chain_id'].strip(),a['identity']['resseq'].strip())==site and a['atom_id'] in names]
    if len(selected)!=len(set(names)):raise ValueError('Generated selection has missing or ambiguous atoms')
    return selected


def _requests(text,atoms):
    nodes,_=_parse(text);result=[]
    for n in nodes:
        kind=_path(n).removeprefix('geometry_restraints.edits.')
        if kind not in {'bond','angle','parallelity'}:continue
        f=n['fields'];size=3 if kind=='angle' else 2
        expressions=[f['atom_selection_'+str(i+1)] for i in range(size)]
        selected=[_resolve(s,atoms) for s in expressions]
        if kind!='parallelity' and any(len(s)!=1 for s in selected):raise ValueError('Expected single atom endpoints')
        if kind=='parallelity' and any(len(s)<3 for s in selected):raise ValueError('Insufficient mapped plane atoms')
        endpoints=selected[0] if kind=='parallelity' else [s[0] for s in selected]
        row={'kind':kind,'action':'add','selections':expressions,'i_seqs':[a['i_seq'] for a in endpoints],
             'atoms':[a['label'] for a in endpoints],'weight':1./float(f['sigma'])**2}
        target={'bond':'distance_ideal','angle':'angle_ideal','parallelity':'target_angle_deg'}[kind]
        row[target]=float(f[target])
        if kind=='parallelity':row.update(j_seqs=[a['i_seq'] for a in selected[1]],j_atoms=[a['label'] for a in selected[1]])
        result.append(row)
    return result


def _signature(kind,row,*,values=True):
    atoms=tuple(row['atoms'])
    if kind=='bond_simple':kind='bond'
    if kind=='bond':key=(kind,tuple(sorted(atoms)));fields=('distance_ideal','weight')
    elif kind=='angle':key=(kind,min(atoms,atoms[::-1]));fields=('angle_ideal','weight')
    elif kind=='parallelity':
        key=(kind,tuple(sorted((tuple(sorted(atoms)),tuple(sorted(row['j_atoms']))))));fields=('target_angle_deg','weight')
    else:raise ValueError('Unsupported generated request kind')
    return key+tuple(row[f] for f in fields) if values else key


def compile_na_policy(model: Path, phils: list[Path], captured: dict, output: Path) -> dict:
    """Write separate derived inputs, preserving every non-SS input line.

    The source bundle's explicit edits are retained. Only previously declared
    generic pairs/stacks are compiled; the guesser is not rerun on moved sites.
    Unsupported declarations stop before any output is written.
    """
    from Bio.PDB import PDBParser
    from restraints.builder import pair_residue_from_pdb
    from restraints.phenix import generate_pair_restraints
    from restraints.recipe_library import recipe_for
    from restraints.residue_library import load_residue_records
    from restraints.stacking import _manual_parallelity
    model,output=Path(model),Path(output)
    if output.exists() or output.is_symlink():raise FileExistsError('Policy output already exists')
    atoms=captured['atoms']
    if [a['i_seq'] for a in atoms]!=list(range(len(atoms))):raise ValueError('Native atom indices are not a bijection')
    if any(a['identity'].get('altloc','').strip() or a['identity'].get('icode','').strip() for a in atoms):
        raise ValueError('Alternate/insertion contexts need a separate reviewed compiler')
    if len({a['identity']['model_id'] for a in atoms})!=1:raise ValueError('Require one native model')
    structure=PDBParser(QUIET=True).get_structure('policy',str(model))
    if len(list(structure.get_models()))!=1:raise ValueError('Require one PDB model')
    residues={};observed=set()
    for chain in structure[0]:
        for residue in chain:
            if residue.id[2].strip():raise ValueError('Insertion-code context requires review')
            key=(chain.id,str(residue.id[1]))
            if key in residues:raise ValueError('Ambiguous PDB site')
            residues[key]=residue
            for atom in residue:
                if atom.is_disordered():raise ValueError('Alternate PDB atoms require review')
                observed.add((*key,residue.resname.strip(),atom.name))
    expected={(a['identity']['chain_id'].strip(),a['identity']['resseq'].strip(),a['identity']['resname'].strip(),a['atom_id']) for a in atoms}
    if len(expected)!=len(atoms) or expected!=observed:raise ValueError('PDB/native atom identity mismatch')
    records=load_residue_records();blocks=[];relationships=[];retained=[];sources=[];seen=set()
    for number,path in enumerate(phils):
        raw=Path(path).read_bytes();nodes,lines=_parse(raw.decode('utf-8'));ranges=[]
        for n in nodes:
            p=_path(n)
            if p!=SS:continue
            if set(n['fields'])-{'enabled'} or n['fields'].get('enabled','True')!='True':raise ValueError('Unsupported SS control')
            ranges.append((n['start'],n['end']))
            for na in n['children']:
                if _path(na)!=SS+'.nucleic_acid' or na['fields']:raise ValueError('Unsupported secondary-structure scope')
                for declaration in na['children']:
                    kind=_path(declaration).removeprefix(SS+'.nucleic_acid.')
                    allowed={'base1','base2'}|({'saenger_class'} if kind=='base_pair' else set())
                    f=declaration['fields']
                    if kind not in {'base_pair','stacking_pair'} or set(f)!=allowed or declaration['children']:
                        raise ValueError('Unsupported explicit SS declaration settings')
                    sites=[_site_selection(f[k]) for k in ('base1','base2')]
                    key=(kind,tuple(sorted(sites)))
                    if sites[0]==sites[1] or key in seen:raise ValueError('Duplicate or self relationship')
                    seen.add(key)
                    try:pair=[pair_residue_from_pdb(records,residues[s]) for s in sites]
                    except (KeyError,ValueError) as exc:raise ValueError('Unmapped declared site') from exc
                    if kind=='base_pair':
                        recipe=recipe_for(pair[0].base_class,pair[1].base_class)
                        if recipe is None or recipe.name!={'19':'GC','20':'AT'}.get(f['saenger_class']):
                            raise ValueError('Declared class does not match the configured NARestraints recipe')
                        block=generate_pair_restraints(*pair,planes=False);recipe_name=recipe.name
                    else:block=_manual_parallelity(*pair);recipe_name='mapped-base-class-stacking'
                    blocks.append(block);relationships.append({'kind':kind,'sites':[':'.join(s) for s in sites],
                        'recipe':recipe_name,'source_input':number,'source_scope':_path(declaration),
                        'source_values':deepcopy(f),'provenance':'FROZEN_EXPLICIT_DECLARATION_COMPILED_BY_NARESTRAINTS'})
        # Flat controls or unexpected SS descendants must not escape trimming.
        for n in nodes:
            if SS in _path(n) and not any(start<=n['start']<end for start,end in ranges):raise ValueError('Unsupported flat SS scope')
            for field in n['fields']:
                if SS in (_path(n)+'.'+field) and not any(start<=n['start']<end for start,end in ranges):raise ValueError('Unsupported flat SS setting')
        keep=[line for i,line in enumerate(lines) if not any(start<=i<end for start,end in ranges)]
        retained.append(''.join(keep));sources.append({'input_index':number,'sha256':sha256(raw).hexdigest(),
            'removed_ss_scopes':len(ranges),'retained_sha256':sha256(retained[-1].encode()).hexdigest()})
    if not relationships:raise ValueError('No explicit relationships to compile')
    text='refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n geometry_restraints.edits {\n'+'\n\n'.join(blocks)+'\n }\n}\n'
    requests=_requests(text,atoms)
    old=captured['geometry']['custom_proxy_requests']
    edges=[_signature(r['kind'],r,values=False) for r in requests]
    preserved={_signature(r['kind'],r,values=False) for r in old if r['kind'] in {'bond','angle','parallelity'}}
    if len(edges)!=len(set(edges)) or set(edges)&preserved:raise ValueError('Compiled relationships overlap preserved or generated edits')
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','policy_authority':'NARestraints',
        'model_optimization':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'relationships':relationships,'pair_count':sum(r['kind']=='base_pair' for r in relationships),
        'stack_count':sum(r['kind']=='stacking_pair' for r in relationships),'sources':sources,
        'compiled_requests':requests,'request_counts':dict(sorted(Counter(r['kind'] for r in requests).items())),
        'compiled_phil':'explicit_na_policy.phil','retained_phils':[f'retained_{i:03d}.phil' for i in range(len(phils))],
        'objective':'NEW_EXPLICIT_NARESTRAINTS_OBJECTIVE_NOT_A_CONTINUATION_OF_OLD_ENERGY',
        'limitations':['Frozen explicit edits are retained, not regenerated or chemically requalified.',
            'Saenger 19/20 declarations and unambiguous mapped stacks only; unsupported intent requires review.',
            'No new pairing guess, coordinate edit, minimization, refinement or adoption.']}
    output.mkdir(parents=True)
    for name,data in zip(result['retained_phils'],retained): (output/name).write_text(data)
    (output/result['compiled_phil']).write_text(text)
    return result


def qualify_na_policy(before: dict, after: dict, policy: dict) -> dict:
    """Check exact custom membership and every unaffected proxy, retaining REVIEW."""
    checks=[]
    def check(name,value,**extra):checks.append({'check':name,'status':'PASS' if value else 'REVIEW',**extra})
    check('native-interpreter',after.get('status')=='REVIEW' and after.get('fatal_problems') is None
          and not after.get('unused_definitions') and not after.get('unsupported_fields'))
    check('atom-identities',[{k:v for k,v in a.items() if k!='xyz'} for a in before['atoms']]==
          [{k:v for k,v in a.items() if k!='xyz'} for a in after['atoms']])
    check('component-definitions',before['monomer_mappings']==after['monomer_mappings'])
    detail=after.get('restraint_policy',{});ids=detail.get('origin_ids',{})
    labels=['hydrogen bonds','edits','basepair stacking','basepair parallelity','basepair planarity']
    valid=set(ids)==set(labels) and all(type(v) is int for v in ids.values()) and len(set(ids.values()))==len(ids)
    check('native-policy-readback',valid and detail.get('secondary_structure_enabled') is False)
    if not valid:return {'schema_version':1,'status':'REVIEW','mechanics_checks_pass':False,'checks':checks}
    ssids={ids[k] for k in labels if k!='edits'}
    expected=before['geometry']['custom_proxy_requests']+policy['compiled_requests']
    # Preserve full request dictionaries, including selections/actions and plane order.
    dump=lambda row:json.dumps(row,sort_keys=True,allow_nan=False)
    check('exact-custom-requests',Counter(map(dump,expected))==Counter(map(dump,after['geometry']['custom_proxy_requests'])))
    check('no-competing-native-ss-proxies',not any(r.get('origin_id') in ssids for rows in after['geometry']['proxy_details'].values() for r in rows))
    for kind,old_rows in before['geometry']['proxy_details'].items():
        remaining=deepcopy(after['geometry']['proxy_details'][kind]);failures=[]
        requested=[r for r in policy['compiled_requests'] if ('bond_simple' if r['kind']=='bond' else r['kind'])==kind]
        for request in requested:
            matches=[i for i,row in enumerate(remaining) if row.get('origin_id')==ids['edits'] and _signature(kind,row)==_signature(request['kind'],request)]
            if len(matches)!=1:failures.append({'request':request,'matches':len(matches)})
            else:remaining.pop(matches[0])
        retained=[r for r in old_rows if r.get('origin_id') not in ssids]
        check('exact-proxies:'+kind,not failures and Counter(map(dump,retained))==Counter(map(dump,remaining)),
              generated_requests=len(requested),unmatched_requests=failures,
              missing=sum((Counter(map(dump,retained))-Counter(map(dump,remaining))).values()),
              extra=sum((Counter(map(dump,remaining))-Counter(map(dump,retained))).values()))
    return {'schema_version':1,'status':'REVIEW','mechanics_checks_pass':all(c['status']=='PASS' for c in checks),
        'checks':checks,'policy_id':POLICY_ID,'scientific_approval':'NOT_RUN','automatic_adoption':False}
