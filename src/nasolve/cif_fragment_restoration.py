"""Explicit graph-selected base-fragment candidates; production PostMR is unchanged.

This bounded DNA scaffold rule transports a whole connected base fragment from
raw Coot coordinates into the preserved sugar frame. It never copies parent
base atoms by name, changes targets, or approves the resulting geometry.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from math import dist, sqrt
from pathlib import Path

from .cif_captured_geometry import _observed, review_captured_geometry
from .cif_construction_provenance import _pdb_inventory

FRAGMENT_POLICY = 'cif-dna-attached-fragment-restoration-v1'
_SCAFFOLD = {"P": 'P', "OP1": 'O', "OP2": 'O', "O5'": 'O', "C5'": 'C',
             "C4'": 'C', "O4'": 'O', "C1'": 'C', "C2'": 'C', "C3'": 'C', "O3'": 'O'}
_EDGES = {frozenset(pair) for pair in [("P", "OP1"), ("P", "OP2"), ("P", "O5'"),
    ("O5'", "C5'"), ("C5'", "C4'"), ("C4'", "O4'"), ("O4'", "C1'"),
    ("C1'", "C2'"), ("C2'", "C3'"), ("C3'", "C4'"), ("C3'", "O3'")]}
_FRAME = ("C1'", "O4'", "C2'")


def _key(atom):
    i = atom['identity']
    return (i['chain_id'].strip() or '_', i['resseq'].strip(), i['icode'].strip(),
            i['altloc'].strip(), atom['atom_id'])


def _model(native, path, *, coordinates_match=False):
    inventory = _pdb_inventory(path)
    expected = {_key(a): a for a in native['atoms']}
    if len(expected) != len(native['atoms']) or inventory.keys() != expected.keys():
        raise ValueError('Candidate and captured atom identities differ')
    for key, atom in inventory.items():
        original = expected[key]
        if atom['element'] != original['element'].strip().upper() or atom['code'] != original['identity']['resname'].strip():
            raise ValueError('Candidate component or element differs from native inventory')
        if coordinates_match and dist(atom['xyz'], original['xyz']) > 1e-9:
            raise ValueError('Baseline coordinates differ from captured native inventory')
    return inventory


def _sub(a, b):
    return [x-y for x, y in zip(a, b)]


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _frame(points):
    origin, first, second = points
    v = _sub(first, origin); length = sqrt(_dot(v, v))
    if length < .5:
        raise ValueError('Degenerate sugar frame')
    u = [x/length for x in v]; v = _sub(second, origin)
    orthogonal = [x-_dot(v, u)*y for x, y in zip(v, u)]
    length = sqrt(_dot(orthogonal, orthogonal))
    if length < .5:
        raise ValueError('Degenerate sugar frame')
    v = [x/length for x in orthogonal]
    return [u, v, _cross(u, v)]


def _fragment(definition, atoms):
    records = definition['atoms']
    elements = {a['atom_id']: a['type_symbol'].strip().upper() for a in records}
    if len(elements) != len(records) or any(elements.get(a) != row['element'] for a, row in atoms.items()):
        raise ValueError('Captured component elements do not match selected model atoms')
    if any(row['element'] in {'H', 'D'} for row in atoms.values()):
        raise ValueError('Hydrogen-bearing coordinate grafts require a separate rule')
    if any(elements.get(a) != e or a not in atoms for a, e in _SCAFFOLD.items()):
        raise ValueError('Require the complete explicit DNA scaffold')
    edges = set(); adjacency = {a: set() for a in atoms}
    for row in definition['bonds']:
        a, b = row['atom_id_1'], row['atom_id_2']
        edge = frozenset((a, b))
        if a not in elements or b not in elements or a == b or edge in edges:
            raise ValueError('Ambiguous or invalid captured component bond graph')
        edges.add(edge)
        if a in atoms and b in atoms:
            adjacency[a].add(b); adjacency[b].add(a)
        if a in _SCAFFOLD and b in _SCAFFOLD and 'P' not in edge and row.get('type', '').lower() not in {'single', 'sing', '1'}:
            raise ValueError('Unsupported DNA scaffold bond type')
    if {edge for edge in edges if edge <= _SCAFFOLD.keys()} != _EDGES:
        raise ValueError('Unsupported DNA scaffold connectivity')
    fragment = set(atoms)-_SCAFFOLD.keys()
    boundary = [(a, b) for a in _SCAFFOLD for b in adjacency[a] if b in fragment]
    if len(boundary) != 1 or boundary[0][0] != "C1'":
        raise ValueError('Require one base-fragment attachment at C1 prime')
    anchor = boundary[0][1]; reached = set(); pending = [anchor]
    while pending:
        a = pending.pop()
        if a in reached:
            continue
        reached.add(a); pending.extend((adjacency[a] & fragment)-reached)
    if reached != fragment:
        raise ValueError('Disconnected base fragment')
    return sorted(fragment), anchor


def assess_fragment_contexts(native: dict, baseline_model: Path, parent_models: dict[str, Path]) -> dict:
    """Partition explicit controls by supported graph, retaining every refusal.

    This eligibility assessment does not approve chemistry or coordinates.
    Preparation still validates all source, parent and frame correspondence.
    """
    review_captured_geometry(native)
    baseline = _model(native, baseline_model, coordinates_match=True)
    rows = native['monomer_mappings']['rows']
    if len({r['site'] for r in rows}) != len(rows):
        raise ValueError('Ambiguous captured site mappings')
    mappings = {r['site']: r for r in rows}; supported = []; unsupported = []
    for site in sorted(parent_models):
        if site.count(':') != 1 or site not in mappings:
            raise ValueError('Unsupported selected site identity')
        chain, resid = site.split(':')
        atoms = {k[-1]: a for k, a in baseline.items() if k[:2] == (chain, resid)}
        try:
            fragment, anchor = _fragment(mappings[site]['metadata']['effective_definition'], atoms)
        except ValueError as exc:
            unsupported.append({'site': site, 'component': mappings[site]['resname'],
                                'status': 'UNSUPPORTED', 'reason': str(exc)})
        else:
            supported.append(site)
    return {'status': 'REVIEW', 'supported_sites': supported, 'unsupported_sites': unsupported,
            'automatic_adoption': False}


def prepare_fragment_restoration(raw_model: Path, baseline_model: Path, output_model: Path,
                                 native: dict, parent_models: dict[str, Path]) -> dict:
    """Write a separate candidate with intact raw base fragments and fixed scaffold.

    The native inventory supplies the effective component graph. The baseline
    supplies composition and the already restored sugar/backbone, which must
    match each frozen parent. Only raw fragment coordinates are borrowed;
    extra raw atoms absent from the reviewed baseline are recorded, not added.
    No component-code or base-atom-name allowlist selects the fragment.
    """
    output_model = Path(output_model)
    if output_model.exists() or output_model.is_symlink():
        raise FileExistsError(output_model)
    sources = [Path(raw_model), Path(baseline_model), *map(Path, parent_models.values())]
    if not parent_models or output_model.resolve() in {p.resolve() for p in sources}:
        raise ValueError('Require explicit parent controls and a separate output')
    snapshots = {p: p.read_bytes() for p in sources}
    review_captured_geometry(native)  # Validate the complete captured inventory first.
    baseline = _model(native, baseline_model, coordinates_match=True)
    raw = _pdb_inventory(raw_model)
    mappings = native['monomer_mappings']['rows']
    if len({r['site'] for r in mappings}) != len(mappings):
        raise ValueError('Ambiguous captured site mappings')
    mappings = {r['site']: r for r in mappings}; moved = {}; sites = []
    for site, parent_path in sorted(parent_models.items()):
        if site.count(':') != 1 or site not in mappings:
            raise ValueError('Unsupported selected site')
        chain, resid = site.split(':')
        keys = {k[-1]: k for k in baseline if k[:2] == (chain, resid)}
        if not keys or any(k[2] or k[3] for k in baseline if k[:2] == (chain, resid)):
            raise ValueError('Insertion or alternate contexts require a separate rule')
        if any(k[2] or k[3] for k in raw if k[:2] == (chain, resid)):
            raise ValueError('Ambiguous raw alternate context')
        atoms = {a: baseline[k] for a, k in keys.items()}
        row = mappings[site]
        if any(a['code'] != row['resname'] for a in atoms.values()):
            raise ValueError('Captured component identity disagrees with selected site')
        fragment, anchor = _fragment(row['metadata']['effective_definition'], atoms)
        parent = _pdb_inventory(parent_path)
        for a, k in keys.items():
            if k not in raw or raw[k]['code'] != atoms[a]['code'] or raw[k]['element'] != atoms[a]['element']:
                raise ValueError('Raw fragment atom correspondence differs')
        for a in _SCAFFOLD:
            k = keys[a]
            if k not in parent or parent[k]['element'] != atoms[a]['element'] or parent[k]['xyz'] != atoms[a]['xyz']:
                raise ValueError('Baseline scaffold differs from frozen parent coordinates')
        source = [raw[keys[a]]['xyz'] for a in _FRAME]
        target = [atoms[a]['xyz'] for a in _FRAME]
        left, right = _frame(source), _frame(target)
        rotation = [[sum(left[k][i]*right[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        determinant = _dot(rotation[0], _cross(rotation[1], rotation[2]))
        if abs(determinant-1.) > 1e-10:
            raise ValueError('Fragment transport must be a proper rigid rotation')
        for a in fragment:
            local = [_dot(_sub(raw[keys[a]]['xyz'], source[0]), axis) for axis in left]
            moved[keys[a]] = [round(target[0][i]+sum(local[j]*right[j][i] for j in range(3)), 3) for i in range(3)]
        names = ["C1'", *fragment]; maximum = 0.
        for i, a in enumerate(names):
            for b in names[i+1:]:
                maximum = max(maximum, abs(dist(raw[keys[a]]['xyz'], raw[keys[b]]['xyz'])-
                    dist(moved.get(keys[a], atoms[a]['xyz']), moved.get(keys[b], atoms[b]['xyz']))))
        if maximum > .002:
            raise ValueError('Serialized fragment geometry changed beyond PDB rounding')
        before = _observed('chirality', [source[0], source[1], source[2], raw[keys[anchor]]['xyz']])
        after = _observed('chirality', [target[0], target[1], target[2], moved[keys[anchor]]])
        if abs(before) < .01 or abs(after) < .01 or before*after <= 0:
            raise ValueError('Glycosidic attachment orientation is degenerate or changed')
        extras = sorted(k[-1] for k in raw if k[:2] == (chain, resid) and k[-1] not in keys)
        sites.append({'site': site, 'component': row['resname'], 'fragment_atoms': fragment,
            'attachment_atom': anchor, 'frame_atoms': list(_FRAME), 'raw_extra_atoms_not_borrowed': extras,
            'rotation_determinant': determinant, 'max_fragment_distance_change': maximum,
            'attachment_orientation_preserved': True})
    lines = []
    for line in Path(baseline_model).read_text().splitlines(keepends=True):
        if line[:6] in {'ATOM  ', 'HETATM'}:
            key = (line[21].strip() or '_', line[22:26].strip(), line[26].strip(), line[16].strip(), line[12:16].strip())
            if key in moved:
                fields = [f'{v:8.3f}' for v in moved[key]]
                if any(len(v) != 8 for v in fields):
                    raise ValueError('Candidate coordinate exceeds PDB field width')
                line = line[:30]+''.join(fields)+line[54:]
        lines.append(line)
    if any(p.read_bytes() != data for p, data in snapshots.items()):
        raise ValueError('Fragment source changed during preparation')
    output_model.parent.mkdir(parents=True, exist_ok=True)
    with output_model.open('x') as handle:
        handle.write(''.join(lines))
    return {'schema_version': 1, 'audit_kind': 'cif_fragment_restoration_candidate', 'policy_id': FRAGMENT_POLICY,
        'status': 'REVIEW', 'sites': sites, 'changed_atom_count': sum(baseline[k]['xyz'] != v for k, v in moved.items()),
        'transported_atom_count': len(moved), 'scaffold_preserved': True, 'other_atoms_preserved': True,
        'metadata_preserved': True, 'source_preserved': True, 'candidate_sha256': hashlib.sha256(output_model.read_bytes()).hexdigest(),
        'model_editing': 'SEPARATE_CANDIDATE_ONLY', 'optimization': 'NOT_RUN', 'refinement': 'NOT_RUN',
        'scientific_approval': 'NOT_RUN', 'automatic_adoption': False,
        'limitations': ['Complete explicit unbranched DNA scaffold with one connected heavy-atom base fragment only.',
            'The raw Coot base geometry is retained; existing defects are not optimized or certified.',
            'Sugar geometry and all intersite scaffold coordinates remain the reviewed baseline.',
            'This candidate is not integrated into production PostMR; native and scientific review remain separate.']}


def review_model_with_captured_proxies(native: dict, model: Path) -> dict:
    """Predict descriptive scalars at an explicit model, without native execution."""
    inventory = _model(native, model); projected = deepcopy(native)
    for i, a in enumerate(projected['atoms']):
        a['xyz'] = list(inventory[_key(a)]['xyz']); projected['geometry']['sites_cart_exact'][i] = list(a['xyz'])
    report = review_captured_geometry(projected)
    report.update(coordinate_source='EXPLICIT_CANDIDATE_PDB', proxy_source='CAPTURED_NATIVE_MANAGER',
                  model_editing='SEPARATE_CANDIDATE_ONLY')
    return report


def qualify_fragment_restoration(before: dict, after: dict, model: Path, preparation: dict) -> dict:
    """Require unchanged native identities, definitions and every captured proxy.

    All geometry outcomes remain descriptive REVIEW, even when these mechanics
    checks pass. No charge readback or previous chemical review is waived.
    """
    checks = []
    def check(name, passes, **evidence):
        checks.append({'check': name, 'status': 'PASS' if passes else 'REVIEW', **evidence})
    original = [{k:v for k,v in a.items() if k != 'xyz'} for a in before['atoms']]
    candidate = [{k:v for k,v in a.items() if k != 'xyz'} for a in after['atoms']]
    check('exact-native-atom-identities', original == candidate)
    def rows(value):
        return Counter(json.dumps(r, sort_keys=True, allow_nan=False) for r in value)
    check('exact-native-site-definitions', rows(before['monomer_mappings']['rows']) == rows(after['monomer_mappings']['rows']))
    try:
        _model(after, model, coordinates_match=True)
        matches = True
    except (ValueError, KeyError):
        matches = False
    check('exact-candidate-coordinates', matches)
    left, right = before['geometry'], after['geometry']
    check('exact-custom-proxy-requests', left.get('custom_proxy_requests') == right.get('custom_proxy_requests'))
    for kind in sorted(set(left['proxy_details']) | set(right['proxy_details'])):
        a, b = rows(left['proxy_details'].get(kind, [])), rows(right['proxy_details'].get(kind, []))
        check('exact-proxies:'+kind, a == b, missing=sum((a-b).values()), extra=sum((b-a).values()))
    check('exact-proxy-counts', left['proxy_counts'] == right['proxy_counts'])
    check('candidate-bytes', hashlib.sha256(Path(model).read_bytes()).hexdigest() == preparation['candidate_sha256'])
    return {'schema_version': 1, 'audit_kind': 'cif_fragment_native_mechanics', 'policy_id': FRAGMENT_POLICY,
        'status': 'REVIEW', 'checks': checks, 'mechanics_checks_pass': all(c['status']=='PASS' for c in checks),
        'scientific_approval': 'NOT_RUN', 'automatic_adoption': False,
        'limitations': ['Native inventory equality does not approve achieved geometry or independent stereochemistry.',
            'Previous source/charge/pucker and experimental qualification remain open.']}
