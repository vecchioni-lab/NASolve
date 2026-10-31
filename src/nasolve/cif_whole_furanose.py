"""Explicit whole-furanose diagnostic placement, independent of residue names.

A proper rigid transform preserves the complete numerical sugar/base geometry.
Only declared neutral port deletions are allowed. Link geometry, partner chemistry,
native restraint preparation and adoption remain separate qualifications.
"""
from itertools import combinations
import math
from pathlib import Path
import re
import tempfile

from .cif_attachment_profiles import inspect_attachment_profile
from .cif_attachment_sites import (_model, _object, _site, _projection_values,
    _neutral_hydroxyl_hydrogens, inspect_attachment_site)
from .cif_candidate_usability import reassess_complete_candidate
from .cif_construction_provenance import _pdb_inventory
from .cif_fana_component import _digest, _load, _save
from .cif_fragment_restoration import _frame, _dot, _sub, _cross
from .cif_stereochemistry_audit import _values, _graph, _coordinates, _volume, VOLUME_EPSILON

POLICY_ID = 'cif-rigid-whole-furanose-linked-control-v1'
_PROFILES = {'unbridged-furanose-phosphate-v1', 'two-o-four-c-methylene-furanose-phosphate-v1'}
_INPUTS = {'source.cif', 'numerical.cif', 'host.cif', 'Ligands.xlsx', 'frame.pdb', 'context.json', 'selection.json'}
_OUTPUTS = {'model.pdb', 'placement.json'}


def _hand(a, b):
    return (a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
            and min(abs(a), abs(b)) > VOLUME_EPSILON and (a > 0) == (b > 0))


def _derive(root):
    selection = _load(root/'selection.json')
    _object(selection, ('code',))
    code = selection['code']
    if not isinstance(code, str) or not re.fullmatch('[A-Z0-9]{1,3}', code):
        raise ValueError('Require an explicit PDB-compatible component code')
    context = _load(root/'context.json')
    _object(context, ('schema_version', 'site', 'ports'))
    if type(context['schema_version']) is not int or context['schema_version'] != 1:
        raise ValueError('Unsupported context schema')
    selected = _site(context['site']); _object(context['ports'], ('phosphate', 'alcohol'))
    payload = (root/'frame.pdb').read_bytes(); sites = _model(payload)
    if selected not in sites:
        raise ValueError('Selected host site is absent')
    host = sites[selected]
    profiles = [inspect_attachment_profile(root/name, component, workbook=root/'Ligands.xlsx')
                for name, component in [('source.cif', code), ('host.cif', host['component'])]]
    if any(p['topology_status'] != 'MATCH' or p['matched_profile'] not in _PROFILES for p in profiles):
        raise ValueError('Require unique supported source and host furanose graphs')
    roles, host_roles = [p['bindings'] for p in profiles]
    _projection_values(root/'source.cif', code); _projection_values(root/'numerical.cif', code)
    assessment = reassess_complete_candidate(root/'source.cif', root/'numerical.cif', code)
    if assessment['candidate_status'] != 'CANDIDATE_REVIEW':
        raise ValueError('Require a complete source-preserving numerical candidate')
    values = _values(root/'source.cif', code)
    elements, bonds, charges, neighbors = _graph(values)
    terms = assessment['finished_stereo']['terms']
    # This audit includes both atom R/S labels and fixed source chirality loops.
    centers = {r['center'] for r in terms}
    if not centers or any(r['handedness'] != 'PRESERVED' for r in terms):
        raise ValueError('Require every source-declared stereocentre to be preserved')
    family, xyz = _coordinates(_values(root/'numerical.cif', code), source=False)
    if set(xyz) != set(elements):
        raise ValueError('Require complete finite candidate coordinates')
    host_elements = _graph(_values(root/'host.cif', host['component']))[0]
    if (any(e in {'H', 'D'} for row in sites.values() for e in row['atoms'].values())
            or any(host_elements.get(n) != e for n, e in host['atoms'].items())
            or any(n not in host['atoms'] for n in host_roles.values())):
        raise ValueError('Require a heavy-only frame with source-bound host core atoms')
    removed = set(); partners = []
    for port, role, expected in [('phosphate', 'phosphate', 'O'), ('alcohol', 'three_o', 'P')]:
        intent = context['ports'][port]
        _object(intent, ('state', 'partner', 'symmetry_operation') + (('leaving_atom',) if port == 'phosphate' else ()))
        if intent['state'] != 'linked' or intent['symmetry_operation'] != 'x,y,z':
            raise ValueError('Require two explicit identity-symmetry linked ports')
        p = intent['partner']; _object(p, ('site', 'component', 'atom_id')); ps = _site(p['site'])
        if (ps == selected or sites.get(ps, {}).get('component') != p['component']
                or sites[ps]['atoms'].get(p['atom_id']) != expected):
            raise ValueError('Declared partner absent or wrong component/element')
        partners.append((ps, p['atom_id'], roles[role], host_roles[role]))
        atom = roles[role]
        if port == 'phosphate':
            atom = intent['leaving_atom']
            if (not isinstance(atom, str) or elements.get(atom) != 'O'
                    or {n for n in neighbors[atom] if elements[n] not in {'H', 'D'}} != {roles[role]}
                    or bonds.get(tuple(sorted((atom, roles[role])))) != 'SINGLE'):
                raise ValueError('Leaving atom is not a source terminal single-bonded phosphate oxygen')
            removed.add(atom)
        hydrogens = _neutral_hydroxyl_hydrogens(atom, elements, bonds, charges, neighbors)
        if hydrogens is None:
            raise ValueError('Require explicit neutral hydroxyl state at each reacting source port')
        removed.update(hydrogens)
    if partners[0][0] == partners[1][0] or removed & centers:
        raise ValueError('Require distinct flanks and retained stereocentres')
    lines = payload.decode('utf-8').splitlines(keepends=True)
    if any(l[:6].strip() not in {'ATOM', 'HETATM', 'REMARK', 'CRYST1', 'TER', 'END', ''} for l in lines):
        raise ValueError('Unsupported frame records require reconciliation')
    inventory = _pdb_inventory(root/'frame.pdb'); chain, resid = selected.split(':')
    center = {k[-1]: a['xyz'] for k, a in inventory.items() if k[:2] == (chain, resid)}
    checks = []
    for role, adjacent in [('anomeric', ('ring_o', 'ring_c2', 'base')),
                            ('ring_c3', ('ring_c2', 'ring_c4', 'three_o')),
                            ('ring_c4', ('ring_o', 'ring_c3', 'five_c'))]:
        a = _volume(xyz, roles[role], [roles[r] for r in adjacent])
        b = _volume(center, host_roles[role], [host_roles[r] for r in adjacent])
        if not _hand(a, b):
            raise ValueError('Host and target sugar hands differ or are degenerate: ' + role)
        checks.append({'role': role, 'target_volume': a, 'host_volume': b})
    frame_roles = ('anomeric', 'ring_o', 'ring_c2')
    a, b = ([xyz[roles[r]] for r in frame_roles], [center[host_roles[r]] for r in frame_roles])
    u, v = _frame(a), _frame(b)
    determinant = _dot(u[0], _cross(u[1], u[2])) * _dot(v[0], _cross(v[1], v[2]))
    if not math.isfinite(determinant) or abs(determinant - 1) > 1e-10:
        raise ValueError('Require a proper rigid transform')
    heavy = sorted(n for n in elements if elements[n] not in {'H', 'D'} and n not in removed)
    moved = {n: [float(f'{b[0][i] + sum(_dot(_sub(xyz[n], a[0]), u[j])*v[j][i] for j in range(3)):.3f}')
                  for i in range(3)] for n in heavy}
    error = max(abs(math.dist(xyz[x], xyz[y]) - math.dist(moved[x], moved[y])) for x, y in combinations(heavy, 2))
    if not math.isfinite(error) or error > .002:
        raise ValueError('PDB rounding changed internal distances')
    hands = []
    for atom in sorted(centers):
        ns = sorted(n for n in neighbors[atom] if elements[n] not in {'H', 'D'})
        if len(ns) not in {3, 4}:
            raise ValueError('Source centre needs three or four retained heavy neighbors')
        for ordered in combinations(ns, 3):
            left, right = _volume(xyz, atom, ordered), _volume(moved, atom, ordered)
            if not _hand(left, right):
                raise ValueError('Placed heavy stereochemistry changed or is degenerate')
            hands.append({'center': atom, 'ordered_neighbors': list(ordered), 'before_volume': left, 'after_volume': right})
    serials = [int(l[6:11]) for l in lines if l[:6] in {'ATOM  ', 'HETATM'}]
    if len(serials) != len(set(serials)):
        raise ValueError('Duplicate frame atom serial')
    serial = max(serials); replacement = []
    for n in heavy:
        serial += 1; fields = [f'{x:8.3f}' for x in moved[n]]
        if len(n) > 4 or serial > 99999 or any(len(f) != 8 for f in fields):
            raise ValueError('Placed atom exceeds supported PDB fields')
        replacement.append(f'HETATM{serial:5d} {n:>4} {code:>3} {" " if chain == "_" else chain}{int(resid):4d}    {"".join(fields)}  1.00 20.00          {elements[n]:>2}\n')
    result = []; inserted = False
    for line in lines:
        if line[:6] in {'ATOM  ', 'HETATM'} and (line[21].strip() or '_', str(int(line[22:26]))) == (chain, resid):
            if not inserted:result.extend(replacement); inserted = True
        else:result.append(line)
    model = ''.join(result)
    if _model(model.encode())[selected]['atoms'] != {n: elements[n] for n in heavy}:
        raise ValueError('Output inventory differs from source projection')
    # Reuse the existing chemical-state authority, including its leaving-stereo checks.
    with tempfile.TemporaryDirectory(prefix='nasolve-whole-site-') as temporary:
        path = Path(temporary)/'model.pdb'; path.write_text(model)
        projection = inspect_attachment_site(root/'source.cif', code, workbook=root/'Ligands.xlsx', model=path, context=root/'context.json')
    if projection['plan_status'] != 'PROPOSED' or projection['permitted_source_projection']['deleted_atoms'] != sorted(removed):
        raise ValueError('Existing attachment authority does not permit this projection')
    junctions = []
    for site, atom, target, old in partners:
        pc, pr = site.split(':'); partner = inventory[(pc, pr, '', '', atom)]['xyz']
        junctions.append({'partner': site+':'+atom, 'target_atom': target,
                          'before_angstrom': math.dist(partner, center[old]), 'after_angstrom': math.dist(partner, moved[target])})
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'PLACED_FOR_LINK_REVIEW',
            'component': code, 'context': context, 'source_profile': profiles[0]['matched_profile'],
            'host_profile': profiles[1]['matched_profile'], 'coordinate_family': family,
            'rotation_determinant': determinant, 'frame_roles': list(frame_roles),
            'host_hand_checks': checks, 'retained_hands': hands, 'source_projection': projection,
            'max_internal_distance_error_angstrom': error, 'model_heavy_atoms': heavy,
            'junction_distances': junctions, 'bystander_records_preserved': True,
            'selected_occupancy': 1.0, 'selected_b_factor': 20.0,
            'native_linkage': 'NOT_ASSESSED', 'partner_chemistry': 'NOT_ASSESSED',
            'model_optimization': 'NOT_RUN', 'clash_assessment': 'NOT_RUN', 'automatic_adoption': False}, model


def prepare_whole_furanose_control(source, numerical, host_source, workbook, frame, output, *, code, context):
    """Write a fresh bound diagnostic, never modify a model or retry in place."""
    paths = dict(zip(('source.cif', 'numerical.cif', 'host.cif', 'Ligands.xlsx', 'frame.pdb'),
                    [Path(p).expanduser().resolve(strict=True) for p in (source, numerical, host_source, workbook, frame)]))
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or any(p.is_relative_to(out.resolve()) for p in paths.values()):
        raise ValueError('Output must be separate and cannot traverse symlinks')
    before = {name: p.read_bytes() for name, p in paths.items()}
    # Validate before making the durable attempt, then rederive from frozen inputs.
    with tempfile.TemporaryDirectory(prefix='nasolve-whole-preflight-') as temporary:
        stage = Path(temporary)
        for name, data in before.items():(stage/name).write_bytes(data)
        _save(stage/'context.json', context); _save(stage/'selection.json', {'code': code})
        expected, model = _derive(stage)
        out.mkdir(parents=True, exist_ok=False)
        for name in _INPUTS:
            with (out/name).open('xb') as stream:stream.write((stage/name).read_bytes())
    actual, frozen = _derive(out)
    if actual != expected or frozen != model or any(p.read_bytes() != before[n] for n, p in paths.items()):
        raise ValueError('Placement inputs changed during freezing')
    with (out/'model.pdb').open('x') as stream:stream.write(model)
    _save(out/'placement.json', actual)
    _save(out/'receipt.json', {'schema_version': 1, 'policy_id': POLICY_ID, 'files': {n: _digest(out/n) for n in sorted(_INPUTS | _OUTPUTS)}})
    return read_whole_furanose_control(out)


def read_whole_furanose_control(control):
    """Verify the exact frozen capsule and recompute chemistry/geometry offline."""
    root = Path(control).expanduser().resolve(strict=True); paths = list(root.rglob('*'))
    names = _INPUTS | _OUTPUTS | {'receipt.json'}
    if any(p.is_symlink() or not p.is_file() for p in paths) or {p.name for p in paths} != names:
        raise ValueError('Require an exact nonsymlinked placement capsule')
    before = {p: p.read_bytes() for p in paths}; receipt = _load(root/'receipt.json')
    if (set(receipt) != {'schema_version', 'policy_id', 'files'} or type(receipt['schema_version']) is not int
            or receipt['schema_version'] != 1 or receipt['policy_id'] != POLICY_ID
            or receipt['files'] != {n: _digest(root/n) for n in sorted(_INPUTS | _OUTPUTS)}):
        raise ValueError('Invalid completion receipt or checksums')
    report, model = _derive(root)
    if report != _load(root/'placement.json') or model.encode() != (root/'model.pdb').read_bytes() or any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError('Saved placement differs from fresh derivation')
    return report
