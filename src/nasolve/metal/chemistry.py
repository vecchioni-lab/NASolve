"""Checked component graphs for base selection and presentation connectivity."""
import io
import re
import hashlib
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from .recipe import RecipeError, canonical

# Explicit standard base inventories; no sugar/phosphate naming heuristic.
_CANONICAL = {
 'A': 'N9 C8 N7 C5 C6 N6 N1 C2 N3 C4',
 'G': 'N9 C8 N7 C5 C6 O6 N1 C2 N2 N3 C4',
 'C': 'N1 C2 O2 N3 C4 N4 C5 C6',
 'T': 'N1 C2 O2 N3 C4 O4 C5 C7 C6',
 'U': 'N1 C2 O2 N3 C4 O4 C5 C6',
}


def dictionaries(resources):
    """Read captured CIF bytes, splitting blocks outside semicolon text."""
    result = {}
    for name, raw in resources:
        if not name.lower().endswith('.cif'):
            continue
        lines=raw.decode('utf-8').splitlines(keepends=True);starts=[];inside=False
        for i,line in enumerate(lines):
            if line.startswith(';'):inside=not inside
            elif not inside and re.match(r'^\s*data_\S+\s*(?:#.*)?$',line,re.I):starts.append(i)
        if inside or not starts:raise RecipeError('Invalid captured component dictionary')
        for first,last in zip(starts,[*starts[1:],len(lines)]):
            try:values=dict(MMCIF2Dict(io.StringIO(''.join(lines[first:last]))))
            except (ValueError,StopIteration,IndexError) as exc:raise RecipeError('Cannot parse captured component dictionary') from exc
            names=values.get('_chem_comp_atom.atom_id',[])
            if not names:continue
            codes=values.get('_chem_comp_atom.comp_id',[]);elements=values.get('_chem_comp_atom.type_symbol',[])
            if len(names)!=len(set(names)) or len(codes)!=len(names) or len(set(codes))!=1 or len(elements)!=len(names):
                raise RecipeError('Ambiguous captured component inventory')
            left=values.get('_chem_comp_bond.atom_id_1',[]);right=values.get('_chem_comp_bond.atom_id_2',[])
            if len(left)!=len(right):raise RecipeError('Invalid component bond inventory')
            edges=sorted(set(tuple(sorted((a,b))) for a,b in zip(left,right)))
            if any(a==b or a not in names or b not in names for a,b in edges):raise RecipeError('Invalid component bond endpoint')
            graph=dict(elements=dict(zip(names,elements)),edges=edges)
            code=codes[0]
            if code in result and canonical(result[code]['graph'])!=canonical(graph):raise RecipeError('Conflicting captured component graphs: '+code)
            result[code]=dict(graph=graph,sha256=hashlib.sha256(raw).hexdigest())
    return result


def base_names(code, chemistry):
    if code not in chemistry:
        standard=code[1:] if code in {'DA','DC','DG','DT','DU'} else code
        if standard not in _CANONICAL:raise RecipeError('Nucleobase graph unavailable for '+code+'; choose donor-mean explicitly')
        return set(_CANONICAL[standard].split()), 'standard_nucleobase_inventory_v1'
    entry=chemistry[code];graph=entry['graph'];elements=graph['elements']
    adjacency={n:set() for n,e in elements.items() if e.upper() not in {'H','D'}}
    for a,b in graph['edges']:
        if a in adjacency and b in adjacency:adjacency[a].add(b);adjacency[b].add(a)
    # Cut the explicit glycosidic edge. The base may include modified substituents,
    # but must have no second connection to the sugar/backbone environment.
    anchors=[n for n in adjacency.get("C1'",()) if n not in {"C2'","O4'"}]
    if len(anchors)!=1:raise RecipeError('Ambiguous nucleobase attachment for '+code)
    seen=set();pending=[anchors[0]]
    while pending:
        node=pending.pop()
        if node in seen or node=="C1'":continue
        seen.add(node);pending.extend(adjacency[node]-seen)
    sugar={"C2'","C3'","C4'","C5'","O2'","O3'","O4'","O5'",'P','OP1','OP2','OP3'}
    if seen & sugar:raise RecipeError('Nucleobase has multiple backbone attachments: '+code)
    return seen, dict(kind='captured_component_graph',sha256=entry['sha256'])


def display_connections(atoms, chemistry):
    """CIF bonds when known; conservative within-residue visual contacts otherwise.

    Distance contacts are explicitly presentation-only, never a restraint graph
    or a source for environmental B. Metals are excluded from this fallback.
    """
    import math
    from itertools import combinations
    residues={}
    for atom in atoms:
        key=atom['key'];identity=canonical({k:v for k,v in key.items() if k!='atom_name'})
        residues.setdefault(identity,[]).append(atom)
    result=[]
    for members in residues.values():
        code=members[0]['key']['component_id'];entry=chemistry.get(code)
        edges=set(tuple(edge) for edge in entry['graph']['edges']) if entry else None
        for a,b in combinations(members,2):
            if edges is not None:
                linked=tuple(sorted((a['key']['atom_name'],b['key']['atom_name']))) in edges
                source='captured_component_graph'
            else:
                elements={a['element'],b['element']}
                cutoff=2.05 if 'S' in elements else 1.9 if 'P' in elements else 1.8
                linked=elements<={'C','N','O','S','P'} and .65<math.dist(a['xyz'],b['xyz'])<=cutoff
                source='distance_display_only'
            if linked:result.append(dict(keys=[a['key'],b['key']],source=source))
    return result
