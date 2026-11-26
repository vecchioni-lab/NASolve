"""Exact projected definitions and preserved native mechanics for explicit trials."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Mapping

from .cif_linked_preparation import atom_rows, component_values
from .cif_linked_qualification import _site, _number, qualify_linked_bundle
from .dictionary_compatibility import normalize_torsion_block

_CATEGORIES={
    'atoms':('_chem_comp_atom',('atom_id','type_symbol','type_energy','partial_charge')),
    'bonds':('_chem_comp_bond',('atom_id_1','atom_id_2','type','value_dist','value_dist_esd','value_dist_neutron')),
    'angles':('_chem_comp_angle',('atom_id_1','atom_id_2','atom_id_3','value_angle','value_angle_esd')),
    'torsions':('_chem_comp_tor',('id','atom_id_1','atom_id_2','atom_id_3','atom_id_4','value_angle','alt_value_angle','value_angle_esd','period')),
    'chirality':('_chem_comp_chir',('atom_id_centre','atom_id_1','atom_id_2','atom_id_3','volume_sign')),
    'plane_atoms':('_chem_comp_plane_atom',('plane_id','atom_id','dist_esd')),
}
_NUMERIC={'partial_charge','value_dist','value_dist_esd','value_dist_neutron','value_angle','value_angle_esd','period','dist_esd'}
PROXY_COMPARISON_POLICY = 'cif-native-named-proxy-comparison-v1'
CUSTOM_REQUEST_POLICY = 'cif-native-ordered-named-custom-requests-v1'


def custom_request_policy_fields(policy):
    """Absent opt-in preserves historical comparison and serialized fields."""
    if policy is None: return {}
    if type(policy) is not str or policy != CUSTOM_REQUEST_POLICY:
        raise ValueError('Unsupported explicit request comparison policy')
    return dict(explicit_request_policy=policy)


def _value(key,value):
    if value is None or value in ('','.','?'):return None
    if key=='alt_value_angle':
        values=value if isinstance(value,(list,tuple)) else str(value).split(',')
        return tuple(_number(v) for v in values)
    if key in _NUMERIC:return _number(value)
    return value


def _rows(values,category):
    prefix=category+'.';columns={k[len(prefix):]:v for k,v in values.items() if k.startswith(prefix)}
    if not columns:return []
    sizes={len(v) for v in columns.values()}
    if len(sizes)!=1:raise ValueError('Ragged projected numerical category')
    return [{k:v[i] for k,v in columns.items()} for i in range(next(iter(sizes)))]


def _signature(row,fields):
    return tuple((k,_value(k,row.get(k))) for k in fields)


def projection_site_plan(path: Path, code: str, site: str) -> dict:
    values=component_values(path,code);atoms=atom_rows(values);bonds=_rows(values,'_chem_comp_bond')
    return {'site':site,'component':code,'expected_atoms':sorted(atoms),
        'expected_energy_types':{n:r.get('type_energy') for n,r in atoms.items()},
        'expected_formal_charges':{n:r.get('charge',r.get('pdbx_formal_charge')) for n,r in atoms.items()},
        'expected_hydrogen_attachments':{n:sorted(r['atom_id_2'] if r['atom_id_1']==n else r['atom_id_1']
            for r in bonds if n in (r['atom_id_1'],r['atom_id_2']))
            for n,r in atoms.items() if r['type_symbol'].upper() in {'H','D'}}}


def definition_projection_checks(native: dict, projections: Mapping[str,tuple[Path,str]]) -> list[dict]:
    """Compare every recorded numerical row with the selected projected source.

    Formal charge has its own existing gate. Missing optional numerical fields
    remain missing; an explicitly supplied native target cannot match absence.
    """
    checks=[];mappings={r['site']:r for r in native['monomer_mappings']['rows']}
    for site,(path,code) in projections.items():
        values,_=normalize_torsion_block(component_values(path,code))
        definition=mappings.get(site,{}).get('metadata',{}).get('effective_definition',{})
        checks.extend(definition_value_checks(values,definition,site))
    return checks


def definition_value_checks(values, definition, site):
    """Compare normalized in-memory rows against one recorded native definition."""
    checks = []
    for name,(category,fields) in _CATEGORIES.items():
        expected=_rows(values,category);actual=definition.get(name)
        try:
            left=Counter(_signature(row,fields) for row in expected)
            right=Counter(_signature(row,fields) for row in actual) if actual is not None else Counter()
            passed=actual is not None and left==right
            detail={'expected_rows':len(expected),'observed_rows':len(actual) if actual is not None else None,
                'missing_or_changed_rows':sum((left-right).values()),'extra_or_changed_rows':sum((right-left).values())}
        except (TypeError,ValueError) as exc:passed=False;detail={'error':str(exc)}
        checks.append({'check':'projected-native-'+name+':'+site,'status':'PASS' if passed else 'REVIEW',**detail})
    return checks


def _native_atom_identities(native, *, pdb_spaces_only=False):
    """Existing structured identities shared by named-proxy comparisons."""
    atoms={}; identities={}; seen=set()
    padding = " " if pdb_spaces_only else None
    fields=('model_id','chain_id','resseq','icode','resname','altloc')
    for atom in native['atoms']:
        index=atom['i_seq']; identity=atom['identity']
        if type(index) is not int or index<0 or index in atoms:
            raise ValueError('Invalid or duplicate native atom index')
        values=[identity[k] for k in fields]+[atom['atom_id']]
        if any(not isinstance(v,str) for v in values) or not isinstance(atom['label'],str):
            raise ValueError('Incomplete native atom identity')
        key=tuple(v.strip(padding) for v in values)
        if not key[2] or not key[4] or not key[-1] or key in seen:
            raise ValueError('Missing or ambiguous named native atom')
        element=atom.get('element')
        if element is not None and (not isinstance(element,str) or not element.strip()):
            raise ValueError('Invalid native element')
        atoms[index]=atom
        identities[index]=key+(element.strip(padding) if element is not None else None,)
        seen.add(key)
    return atoms, identities


def _bound_proxy_endpoints(row, atoms, identities):
    """Bind both ordered endpoint lists to their own capture's atom labels."""
    named={}; indices=[]
    if ('j_seqs' in row)!=('j_atoms' in row):raise ValueError('Incomplete native second-plane endpoints')
    for endpoint,labels in [('i_seqs','atoms'),*([('j_seqs','j_atoms')] if 'j_seqs' in row else [])]:
        ids=row[endpoint]
        if (not isinstance(ids,list) or not ids or any(type(i) is not int or i not in atoms for i in ids)
                or row[labels]!=[atoms[i]['label'] for i in ids]):
            raise ValueError('Native proxy labels do not bind to exact atom indices')
        indices.extend(ids); named[labels]=[identities[i] for i in ids]
    return indices, named


def _proxy_subset(native,changed,kind):
    """Compare ordered named endpoints and every parameter, not display labels.

    Strip only padding in structured identity fields. Bind each proxy label to
    its own manager index before replacing it with that atom's identity; do not
    parse labels, infer aliases, reorder endpoints or round numerical values.
    Duplicate indices/names and incomplete identities cannot become a match.
    """
    atoms, identities = _native_atom_identities(native)
    rows=native['geometry']['proxy_details'][kind]
    if not isinstance(rows,list):raise ValueError('Native proxy detail unavailable: '+kind)
    selected=[]
    for row in rows:
        indices, named = _bound_proxy_endpoints(row, atoms, identities)
        if all(_site(atoms[i]) not in changed for i in indices):
            parameters={k:v for k,v in row.items() if k not in {'i_seqs','j_seqs','atoms','j_atoms'}}
            selected.append(json.dumps({**parameters,**named},sort_keys=True,allow_nan=False))
    return Counter(selected)


def _angle(value):return _number(float(value)%360)


def _request_display_label(atom):
    """Normalize only the verified four-column name in the native PDB label."""
    label=atom['label'];field=atom.get('atom_name_field')
    # Other native display formats remain opaque and must match raw bytes.
    if (field is None or len(label)!=21 or not label.startswith('pdb="')
            or not label.endswith('"') or label.count('"')!=2
            or '\n' in label or '\r' in label):
        return None
    if (not isinstance(field,str) or len(field)!=4 or field!=label[5:9]
            or field.strip(' ')!=atom['atom_id']):
        raise ValueError('Native atom-name field contradicts its display or identity')
    return label[:5]+atom['atom_id'].ljust(4)+label[9:]


def ordered_custom_requests_match(before,after):
    """Permit only verified atom-name padding; preserve all other display text."""
    left,right=_ordered_named_custom_requests(before),_ordered_named_custom_requests(after)
    return len(left)==len(right) and all(
        a==b and len(x)==len(y) and all(
            raw_a==raw_b or (name_a is not None and name_b is not None and name_a==name_b)
            for (raw_a,name_a),(raw_b,name_b) in zip(x,y))
        for (a,x),(b,y) in zip(left,right))


def _ordered_named_custom_requests(native):
    """Compare exact ordered requests after same-capture label/index binding.

    Unlike native proxy multisets, request indices and list order stay exact.
    All selections/parameters survive; labels retain separate raw/field evidence.
    This helper neither qualifies capture provenance nor selects a model.
    """
    from .cif_native_context import _bound_request_signature as validate_request
    atoms, identities = _native_atom_identities(native, pdb_spaces_only=True)
    if any(not a['label'].strip() or not isinstance(a.get('element'),str)
           or not a['element'].strip() for a in atoms.values()):
        raise ValueError('Missing explicit-request atom label or element')
    rows = native['geometry']['custom_proxy_requests']
    if not isinstance(rows,list): raise ValueError('Missing explicit request inventory')
    result = []
    for row in rows:
        _, named = _bound_proxy_endpoints(row, atoms, identities)
        kind = row['kind']
        count = {'bond':2, 'angle':3, 'dihedral':4, 'planarity':1, 'parallelity':2}.get(kind)
        selections = row['selections']
        if (count is None or not isinstance(selections,list) or len(selections)!=count
                or any(not isinstance(s,str) or not s.strip() for s in selections)
                or not isinstance(row['action'],str) or not row['action'].strip()
                or ('j_seqs' in row) != (kind=='parallelity')):
            raise ValueError('Incomplete explicit request or selections')
        # Existing shape, target, weight, and both-plane membership validator.
        # Its unordered signature is deliberately not used for comparison.
        validate_request(kind, row)
        ids=[*row['i_seqs'],*row.get('j_seqs',[])]
        displays=[(atoms[i]['label'],_request_display_label(atoms[i])) for i in ids]
        result.append((json.dumps({**row,**named},sort_keys=True,allow_nan=False),displays))
    return result


def declared_outgoing_hydrogen_checks(native,expected_links):
    """Audit declared linked O3 endpoints by graph, including misleading H names."""
    mappings={r['site']:r for r in native['monomer_mappings']['rows']};checks=[]
    for left,right in expected_links:
        definition=mappings.get(left,{}).get('metadata',{}).get('effective_definition',{})
        atoms={r['atom_id']:r for r in definition.get('atoms') or []}
        bonds=definition.get('bonds');available="O3'" in atoms and bonds is not None
        neighbors=[] if not available else [r['atom_id_2'] if r['atom_id_1']=="O3'" else r['atom_id_1']
            for r in bonds if "O3'" in {r['atom_id_1'],r['atom_id_2']}]
        hydrogens=sorted(n for n in neighbors if atoms.get(n,{}).get('type_symbol','').upper() in {'H','D'})
        checks.append({'check':'declared-outgoing-oxygen-hydrogens:'+left,
            'status':'UNSUPPORTED' if not available or any(n not in atoms for n in neighbors) else 'REVIEW' if hydrogens else 'PASS',
            'outgoing_site':right,'observed_hydrogens':hydrogens,'oxygen_energy_type':atoms.get("O3'",{}).get('type_energy'),
            'scope':'Declared standard outgoing linkage; no valence, pH or alternative target inferred.'})
    return checks


def reviewed_torsion_proxy_check(native,path,code,site,term_id):
    values,_=normalize_torsion_block(component_values(path,code))
    terms=[row for row in _rows(values,'_chem_comp_tor') if row['id']==term_id]
    if len(terms)!=1:raise ValueError('Require one exact reviewed projected torsion')
    term=terms[0];quartet=tuple(term['atom_id_'+str(i)] for i in range(1,5))
    atoms={r['i_seq']:r for r in native['atoms']};matches=[]
    for row in native['geometry']['proxy_details']['dihedral'] or []:
        endpoints=[atoms[i] for i in row['i_seqs']]
        names=tuple(r['atom_id'] for r in endpoints)
        if all(_site(r)==site for r in endpoints) and names in {quartet,quartet[::-1]}:matches.append(row)
    expected={'target':_angle(term['value_angle']),'weight':_number(1/float(term['value_angle_esd'])**2),
              'period':int(term['period']),'alternates':tuple(_angle(v) for v in str(term.get('alt_value_angle','.')).split(',') if v not in {'.','?',''})}
    observed=[]
    for row in matches:
        alts=row.get('alt_angle_ideals')
        observed.append({'target':_angle(row['angle_ideal']),'weight':_number(row['weight']),
            'period':row['periodicity'],'alternates':tuple(_angle(v) for v in alts) if alts is not None else ()})
    return {'check':'reviewed-torsion-native-proxy:'+site+':'+term_id,
        'status':'PASS' if observed==[expected] else 'REVIEW','atoms':list(quartet),'expected':expected,'observed':observed,
        'angular_representation':'modulo 360 degrees only; targets and uncertainties unchanged'}


def qualify_terminal_bundle(baseline: dict, candidate: dict, preparations: list[dict],
        expected_links: list[tuple[str,str]], free_sites: list[str],
        projections: Mapping[str,tuple[Path,str]], *, reviewed_torsions: Mapping[str,str] | None=None,
        native_context: dict | None=None) -> dict:
    """Keep existing gates and add exact source projections and unaffected proxies."""
    prepared=list(preparations);known={s['site'] for p in prepared for s in p['sites']}
    extra=[projection_site_plan(path,code,site) for site,(path,code) in projections.items() if site not in known]
    if extra:prepared.append({'sites':extra})
    result=qualify_linked_bundle(baseline,candidate,prepared,expected_links,free_sites,native_context=native_context)
    result['audit_kind']='cif_terminal_native_bundle_qualification'
    checks=result['checks'];checks.extend(definition_projection_checks(candidate,projections))
    checks.extend(declared_outgoing_hydrogen_checks(candidate,expected_links))
    def check(name,passes,**evidence):checks.append({'check':name,'status':'PASS' if passes else 'REVIEW',**evidence})
    before={r['site']:r['metadata'].get('effective_definition') for r in baseline['monomer_mappings']['rows']}
    after={r['site']:r['metadata'].get('effective_definition') for r in candidate['monomer_mappings']['rows']}
    changed=set(projections)
    check('all-unselected-native-definitions-preserved',
        {s:v for s,v in before.items() if s not in changed}=={s:v for s,v in after.items() if s not in changed},
        selected_changes=sorted(changed))
    for kind in baseline['geometry'].get('proxy_details',{}):
        try:
            left,right=_proxy_subset(baseline,changed,kind),_proxy_subset(candidate,changed,kind)
            check('unaffected-native-proxies:'+kind,left==right,missing=sum((left-right).values()),extra=sum((right-left).values()))
        except (KeyError,TypeError,ValueError) as exc:check('unaffected-native-proxies:'+kind,False,error=str(exc))
    for site,term_id in (reviewed_torsions or {}).items():
        path,code=projections[site]
        try:checks.append(reviewed_torsion_proxy_check(candidate,path,code,site,term_id))
        except (KeyError,TypeError,ValueError) as exc:check('reviewed-torsion-native-proxy:'+site+':'+term_id,False,error=str(exc))
    result['status']='TERMINAL_BUNDLE_MECHANICS_PASS' if all(r['status']=='PASS' for r in checks) else 'REVIEW'
    result['policy_id']='cif-native-terminal-bundle-checks-v1' if native_context is None else 'cif-native-terminal-bundle-checks-v2'
    result['automatic_adoption']=False
    return result
