"""Source-graph-selected ordinary PostMR base transport.

This rule restores a standard unbridged DNA sugar/backbone from its Coot parent
snapshot while transporting the *whole* attached raw base by a proper rotation.
It does not optimize, infer chemistry, edit dictionaries, or certify geometry.
Unsupported or ambiguous sites are retained intact by the caller.
"""
from __future__ import annotations

from hashlib import sha256
from math import dist, isfinite, sqrt
from pathlib import Path

from .cif_linked_preparation import atom_rows, component_values

POLICY_ID = 'postmr-source-graph-fragment-restoration-v1'
_FRAME = ("C1'", "O4'", "C2'")
_SUGAR = {"C1'": 'C', "C2'": 'C', "C3'": 'C', "C4'": 'C', "O4'": 'O',
          "C5'": 'C', "O5'": 'O', "O3'": 'O'}
_SUGAR_EDGES = {frozenset(p) for p in [("C1'", "O4'"), ("C1'", "C2'"),
    ("C2'", "C3'"), ("C3'", "C4'"), ("C4'", "O4'"), ("C4'", "C5'"),
    ("C5'", "O5'"), ("C3'", "O3'")]}
_SINGLE = {'SINGLE', 'SING', '1'}
_ALIASES = {'O1P': 'OP1', 'O2P': 'OP2', 'O3P': 'OP3'}


def canonical_name(name):
    return _ALIASES.get(name, name)


def source_graph_fragment(dictionary: Path, component: str) -> dict:
    """Partition an explicit source graph, refusing bridges and sugar branches.

    Phosphate-bound terminal oxygens belong to the protected backbone; explicit
    source H/D are ignored for this heavy-atom construction rule. No component
    name, NARestraints class or base atom-name list selects the fragment.
    """
    dictionary = Path(dictionary)
    before = dictionary.read_bytes()
    values = component_values(dictionary, component)
    declarations = [str(v).strip().upper() for k in ('_chem_comp.group', '_chem_comp.type')
                    for v in values.get(k, []) if str(v).strip() not in {'', '.', '?'}]
    if not declarations or any(v not in {'DNA', 'DNA LINKING'} for v in declarations):
        raise ValueError('Require explicit consistent source DNA classification')
    original = atom_rows(values)
    atoms = {canonical_name(name): row['type_symbol'].strip().upper() for name,row in original.items()}
    if len(atoms) != len(original):
        raise ValueError('Duplicate source phosphate aliases')
    if any(atoms.get(name) != element for name,element in _SUGAR.items()):
        raise ValueError('Require the complete explicit DNA sugar/backbone graph')
    heavy = {name for name,element in atoms.items() if element not in {'H', 'D'}}
    adjacency = {name: set() for name in heavy}
    a = values.get('_chem_comp_bond.atom_id_1', [])
    b = values.get('_chem_comp_bond.atom_id_2', [])
    orders = values.get('_chem_comp_bond.type', values.get('_chem_comp_bond.value_order', []))
    if not a or len(a) != len(b) or len(a) != len(orders):
        raise ValueError('Incomplete source bond graph')
    edges = {}
    for x,y,order in zip(a,b,orders):
        x,y = canonical_name(x),canonical_name(y); edge = frozenset((x,y))
        if x not in atoms or y not in atoms or x == y or edge in edges:
            raise ValueError('Ambiguous or invalid source bond graph')
        edges[edge] = order.strip().upper()
        if x in heavy and y in heavy:
            adjacency[x].add(y); adjacency[y].add(x)
    if {e for e in edges if e <= _SUGAR.keys()} != _SUGAR_EDGES or any(edges[e] not in _SINGLE for e in _SUGAR_EDGES):
        raise ValueError('Unsupported DNA sugar connectivity or bond orders')
    scaffold = set(_SUGAR)
    phosphate = set()
    if 'P' in heavy:
        if atoms['P'] != 'P' or "O5'" not in adjacency['P'] or edges[frozenset(('P', "O5'"))] not in _SINGLE:
            raise ValueError('Unsupported phosphate attachment')
        oxygen = adjacency['P']-{"O5'"}
        if not 2 <= len(oxygen) <= 3 or any(atoms[n] != 'O' or adjacency[n] != {'P'} for n in oxygen):
            raise ValueError('Unsupported phosphate branch')
        phosphate = {'P', *oxygen}; scaffold |= phosphate
    fragment = heavy-scaffold
    boundary = [(x,y) for x in scaffold for y in adjacency[x] if y in fragment]
    if len(boundary) != 1 or boundary[0][0] != "C1'" or edges[frozenset(boundary[0])] not in _SINGLE:
        raise ValueError('Require one unbridged base-fragment attachment at C1 prime')
    anchor = boundary[0][1]; reached = set(); pending = [anchor]
    while pending:
        name = pending.pop()
        if name in reached: continue
        reached.add(name); pending.extend((adjacency[name]&fragment)-reached)
    if reached != fragment:
        raise ValueError('Disconnected source base fragment')
    if dictionary.read_bytes() != before:
        raise ValueError('Source dictionary changed during graph selection')
    return {'policy_id': POLICY_ID, 'component': component, 'scaffold_atoms': sorted(scaffold),
            'sugar_atoms': sorted(_SUGAR), 'phosphate_atoms': sorted(phosphate),
            'fragment_atoms': sorted(fragment), 'attachment_atom': anchor,
            'frame_atoms': list(_FRAME), 'elements': {n: atoms[n] for n in heavy},
            'source_sha256': sha256(before).hexdigest()}


def _atom_records(lines, expected_code):
    records = {}
    for line in lines:
        if line[:6].strip() not in {'ATOM','HETATM'}: continue
        if len(line) < 54 or line[16:17].strip():
            raise ValueError('Alternate or malformed atom context requires intact raw-site fallback')
        if line[17:20].strip() != expected_code:
            raise ValueError('Selected site component differs from its declared construction identity')
        name = canonical_name(line[12:16].strip())
        if name in records:
            raise ValueError('Duplicate atom names or phosphate aliases')
        element = line[76:78].strip().upper() if len(line) >= 78 else ''
        if not element:
            letters = ''.join(c for c in line[12:16] if c.isalpha()).upper()
            element = next((e for e in ('BR','SE') if letters.startswith(e)), letters[:1])
        if element in {'H','D'}:
            raise ValueError('Hydrogen-bearing coordinate transport requires intact raw-site fallback')
        try: point = tuple(float(line[i:i+8]) for i in (30,38,46))
        except ValueError as exc: raise ValueError('Invalid selected atom coordinates') from exc
        if not all(isfinite(v) for v in point): raise ValueError('Nonfinite selected atom coordinates')
        records[name] = {'line': line, 'xyz': point, 'element': element}
    if not records: raise ValueError('Selected coordinate site is absent')
    return records


def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _sub(a,b): return [x-y for x,y in zip(a,b)]
def _cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def _frame(points):
    origin,a,b = points; x = _sub(a,origin); size = sqrt(_dot(x,x))
    if size < .5: raise ValueError('Degenerate sugar frame')
    x = [v/size for v in x]; b = _sub(b,origin)
    y = [v-_dot(b,x)*u for v,u in zip(b,x)]; size = sqrt(_dot(y,y))
    if size < .5: raise ValueError('Degenerate sugar frame')
    y = [v/size for v in y]
    return [x,y,_cross(x,y)]


def restore_graph_site(raw_lines, parent_lines, dictionary, component, parent_code):
    """Return same ordered records with only supported site's XYZ replaced."""
    graph = source_graph_fragment(dictionary, component)
    raw = _atom_records(raw_lines, component); parent = _atom_records(parent_lines, parent_code)
    scaffold, fragment = set(graph['scaffold_atoms']), set(graph['fragment_atoms'])
    # A free 5' hydroxyl may omit the entire phosphate branch; an internal site
    # may omit terminal source oxygen leaves. Neither changes the source graph.
    names = set(raw)
    if not set(_SUGAR) <= names or not fragment <= names or names-(scaffold|fragment):
        raise ValueError('Raw site does not contain the complete source base and DNA sugar')
    phosphate = set(graph['phosphate_atoms'])
    if phosphate and names&phosphate and ('P' not in names or len(names&phosphate) < 3):
        raise ValueError('Incomplete raw phosphate context')
    selected_scaffold = names&scaffold
    if not selected_scaffold <= parent.keys():
        raise ValueError('Parent lacks selected sugar/backbone atom correspondence')
    if any(raw[n]['element'] != graph['elements'][n] for n in names) or any(
        parent[n]['element'] != graph['elements'][n] for n in selected_scaffold):
        raise ValueError('Source, raw and parent elements differ')
    source = [raw[n]['xyz'] for n in _FRAME]; target = [parent[n]['xyz'] for n in _FRAME]
    left,right = _frame(source),_frame(target)
    rotation = [[sum(left[k][i]*right[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    determinant = _dot(rotation[0],_cross(rotation[1],rotation[2]))
    if abs(determinant-1.) > 1e-10: raise ValueError('Require proper rigid base rotation')
    moved = {n: parent[n]['xyz'] for n in selected_scaffold}
    for n in fragment:
        local = [_dot(_sub(raw[n]['xyz'],source[0]),axis) for axis in left]
        moved[n] = tuple(round(target[0][i]+sum(local[j]*right[j][i] for j in range(3)),3) for i in range(3))
    attached = ["C1'", *sorted(fragment)]
    maximum = max(abs(dist(raw[a]['xyz'],raw[b]['xyz'])-dist(moved[a],moved[b]))
                  for i,a in enumerate(attached) for b in attached[i+1:])
    if maximum > .002: raise ValueError('PDB serialization changed rigid fragment distances')
    def hand(points,anchor): return _dot(_cross(_sub(points[1],points[0]),_sub(points[2],points[0])),_sub(anchor,points[0]))
    before,after = hand(source,raw[graph['attachment_atom']]['xyz']),hand(target,moved[graph['attachment_atom']])
    if abs(before) < .01 or abs(after) < .01 or before*after <= 0:
        raise ValueError('Degenerate or changed C1 attachment orientation')
    output = []
    for line in raw_lines:
        if line[:6].strip() in {'ATOM','HETATM'}:
            fields = [f'{v:8.3f}' for v in moved[canonical_name(line[12:16].strip())]]
            if any(len(v) != 8 for v in fields): raise ValueError('Coordinates exceed PDB field width')
            line = line[:30]+''.join(fields)+line[54:]
        output.append(line)
    report = {k: graph[k] for k in ('policy_id','component','fragment_atoms','attachment_atom','frame_atoms','source_sha256')}
    report.update(status='GRAPH_FRAGMENT_RESTORED', scaffold_atoms=sorted(selected_scaffold),
        count=len(selected_scaffold), atoms=sorted(selected_scaffold), parent_atom_count=len(parent),
        substitutions=[], rotation_determinant=determinant, max_fragment_distance_change=maximum,
        attachment_orientation_preserved=True, metadata_preserved=True, requires_cif_review=False,
        notes=['The complete raw base was transported rigidly; its internal geometry was not optimized.'])
    return output,report
