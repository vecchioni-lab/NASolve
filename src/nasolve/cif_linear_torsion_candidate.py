"""Separate candidates for torsions undefined by explicit linear chemistry.

This opt-in diagnostic does not change installed dictionaries, models or the
production repair recipes. Selection uses declarations, never achieved angles.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .ligand_profiles import _blocks, _emit
from .cif_stereochemistry_audit import _values, _graph
from .cif_triple_bond_audit import _key, _numeric, _rows

POLICY_ID = 'cif-declared-linear-torsion-candidate-v1'
T = '_chem_comp_tor.'


def _columns(values, stem, required):
    columns = {k:v for k,v in values.items() if k.lower().startswith(stem)}
    if not all(stem+k in columns for k in required) or len({len(v) for v in columns.values()}) != 1:
        raise ValueError('Require complete unambiguous '+stem+' columns')
    return columns


def _linear_triples(values):
    elements, orders, _, neighbors = _graph(values)
    triples = [p for p,o in orders.items() if o == 'TRIPLE']
    if not triples:
        raise ValueError('No explicitly declared triple bond')
    _columns(values, '_chem_comp_angle.', ['atom_id_1','atom_id_2','atom_id_3','value_angle','value_angle_esd'])
    angles = _rows(values, 'angle', 3); linear = []
    for pair in triples:
        if tuple(sorted(elements[n] for n in pair)) not in [('C','C'), ('C','N')]:
            raise ValueError('Unsupported triple-bond element pair')
        for center,other in [pair,pair[::-1]]:
            flanks = neighbors[center]-{other}
            if len(flanks)>1:
                raise ValueError('Ambiguous linear-center connectivity')
            for flank in sorted(flanks):
                atoms = [flank,center,other]
                matches = [r for r in angles if _key(r['atoms']) == _key(atoms)]
                if (len(matches)!=1 or _numeric(matches[0].get('value_angle')) != 180.
                        or (_numeric(matches[0].get('value_angle_esd')) or 0)<=0):
                    raise ValueError('Require one explicit 180-degree angle and positive finite ESD')
                linear.append({'atoms':atoms,'triple_bond':list(pair),'declared_angle':deepcopy(matches[0])})
    if not linear:
        raise ValueError('No explicitly restrained linear defining angle')
    return linear, neighbors


def prepare_linear_torsion_candidate(source, code, output):
    """Omit only rows containing a declared-linear defining triple.

    All parsed CIF fields outside those complete rows must compare exactly.
    Unmodified data blocks retain their original text. The input is immutable.
    """
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if (output.exists() or output.is_symlink() or output==source
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require a fresh separate candidate without symlink parents')
    original = source.read_bytes(); values = _values(source, code)
    linear, neighbors = _linear_triples(values)
    _columns(values,T,['comp_id','id','atom_id_1','atom_id_2','atom_id_3','atom_id_4','value_angle','value_angle_esd','period'])
    blocks = _blocks(source); expected = []; rendered = []; removed = []
    keys = {_key(r['atoms']) for r in linear}
    for block in blocks:
        v = deepcopy(block.values); cols = {k:x for k,x in v.items() if k.startswith(T)}; selected = []
        if cols:
            _columns(v,T,['comp_id','id','atom_id_1','atom_id_2','atom_id_3','atom_id_4','value_angle','value_angle_esd','period'])
            for i,comp in enumerate(v[T+'comp_id']):
                if comp != code:
                    continue
                atoms = [v[T+'atom_id_'+str(j)][i] for j in range(1,5)]
                if not any(_key(atoms[j:j+3]) in keys for j in (0,1)):
                    continue
                if (len(set(atoms))!=4 or any(n not in neighbors for n in atoms)
                        or any(b not in neighbors[a] for a,b in zip(atoms,atoms[1:]))):
                    raise ValueError('Selected torsion is not a unique consecutive graph path')
                row = {k:x[i] for k,x in cols.items()}
                target, esd, period = [_numeric(row[T+k]) for k in ['value_angle','value_angle_esd','period']]
                if target is None or esd is None or esd<=0 or period is None or period<0 or period!=int(period):
                    raise ValueError('Selected torsion has unsupported numerical parameters')
                selected.append(i); removed.append(row)
            if selected:
                for k,col in cols.items():
                    remain = [x for i,x in enumerate(col) if i not in selected]
                    if remain: v[k]=remain
                    else: del v[k]
        expected.append(v); rendered.append(_emit(v) if selected else block.text)
    if not removed or len({_key([r[T+'atom_id_'+str(j)] for j in range(1,5)]) for r in removed})!=len(removed):
        raise ValueError('Require unique graph-selected torsions')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        f.write(''.join(rendered))
    actual = [b.values for b in _blocks(output)]
    if actual!=expected or source.read_bytes()!=original:
        raise ValueError('Candidate exceeded exact parsed omission allowlist or source changed')
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'CANDIDATE_REVIEW',
        'source_sha256':sha256(original).hexdigest(),'candidate_sha256':sha256(output.read_bytes()).hexdigest(),
        'removed_torsion_count':len(removed),'removed_torsions':removed,'declared_linear_angles':linear,
        'parsed_allowlist_pass':True,'source_preserved':True,'selection_coordinates':'NOT_USED',
        'model_editing':'NOT_RUN','optimization':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'limitations':['Explicit triple orders and exact 180-degree targets are required; other linear chemistries are unsupported.',
            'Candidate formatting may change in affected blocks; all other parsed values remain identical.',
            'Chemical-state, stereochemistry, native mechanics and scientific approval remain separate gates.']}


def qualify_linear_torsion_candidate(before, after, plan):
    """Require exactly the planned definition/proxy omissions, nothing else."""
    expected = deepcopy(before); removed = plan['removed_torsions']; code = plan['component']
    checks = {}; counts = {'dihedral':0,'const_dihedral':0}
    def atoms(row): return _key([row['atom_id_'+str(j)] for j in range(1,5)])
    requested = {atoms({k[len(T):]:v for k,v in r.items()}):r for r in removed}
    mappings = expected['monomer_mappings']['rows']
    if len(requested)!=len(removed) or len(mappings)!=1:
        raise ValueError('Require one isolated component and unique planned omissions')
    definition = mappings[0]['metadata']['effective_definition']; old = definition['torsions']; selected = []
    for row in old:
        key = atoms(row)
        if key in requested:
            r = requested[key]
            if any(row[k]!=(_numeric(r[T+k]) if k in ['value_angle','value_angle_esd','period'] else r[T+k])
                   for k in ['id','value_angle','value_angle_esd','period']):
                raise ValueError('Native effective torsion differs from planned parameters')
            selected.append(key)
    if len(selected)!=len(removed) or set(selected)!=set(requested):
        raise ValueError('Planned torsion definition membership differs')
    definition['torsions'] = [r for r in old if atoms(r) not in requested]
    index = {a['i_seq']:a['atom_id'] for a in before['atoms']}
    if (len(index)!=len(before['atoms']) or len(set(index.values()))!=len(index)
            or any(a['identity']['resname'].strip()!=code for a in before['atoms'])):
        raise ValueError('Require unique isolated native atom identities')
    heavy = {p for p in requested if all(n in index.values() for n in p)}; seen = []
    for kind in counts:
        rows = expected['geometry']['proxy_details'][kind]; keep = []
        for row in rows:
            key = _key([index[i] for i in row['i_seqs']])
            if key in requested:
                seen.append(key); counts[kind]+=1
            else: keep.append(row)
        expected['geometry']['proxy_details'][kind]=keep
        expected['geometry']['proxy_counts'][kind]-=counts[kind]
    if set(seen)!=heavy or len(seen)!=len(heavy) or not seen:
        raise ValueError('Active planned omission membership is missing or ambiguous')
    for key in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']:
        checks[key+'_exact']=after.get(key)==expected.get(key)
    checks['native_report_valid']=(after.get('status')=='REVIEW' and after.get('fatal_problems') is None
        and after.get('unsupported_fields')==[] and after.get('unused_definitions')==[])
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','checks':checks,
        'mechanics_checks_pass':all(checks.values()),'removed_native_proxy_counts':counts,
        'removed_effective_torsions':len(selected),'model_editing':'NOT_RUN','optimization':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False}
