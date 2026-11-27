"""Explicit whole-furanose diagnostic placement, independent of residue names.

A proper rigid transform preserves the numerical geometry. The explicit uracil
pairing-frame policy also transfers the measured sugar–base torsion before fitting.
Only declared neutral port deletions are allowed. Link geometry, partner chemistry,
native restraint preparation and adoption remain separate qualifications.
"""
from hashlib import sha256
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
from .cif_dictionary_sites import _read as _read_site_artifact
from .cif_fana_component import _digest, _load, _save
from .cif_fragment_restoration import _frame, _dot, _sub, _cross
from .cif_stereochemistry_audit import _values, _graph, _coordinates, _volume, VOLUME_EPSILON

POLICY_ID = 'cif-rigid-whole-furanose-linked-control-v1'
BASE_POLICY_ID = 'cif-base-anchored-whole-furanose-control-v1'
MODEL_BASE_POLICY_ID = 'cif-model-linked-base-anchored-furanose-v1'
_MAPPED_RING_FRAME = 'source-ring-and-workbook-roles-v1'
_EDGE_FRAME = 'canonical-uracil-pairing-edge-v1'
_PDB_ATOM_FIELDS = 'element-aligned-pdb-name-v1'
MODEL_EDGE_POLICY_ID = 'cif-model-linked-canonical-uracil-edge-v1'
_LEAVING_FLAG = '_chem_comp_atom.pdbx_leaving_atom_flag'
_RETAINED_PHOSPHATE_OXYGENS = {'OP1', 'OP2', 'O1P', 'O2P'}
_PROFILES = {'unbridged-furanose-phosphate-v1', 'two-o-four-c-methylene-furanose-phosphate-v1'}
_INPUTS = {'source.cif', 'numerical.cif', 'host.cif', 'Ligands.xlsx', 'frame.pdb', 'context.json', 'selection.json'}
_OUTPUTS = {'model.pdb', 'placement.json'}


def _pdb_atom_field(name, element):
    """Position a source atom ID in the four-column PDB atom-name field."""
    if len(name) < 4 and len(element) == 1 and name[0].isalpha():
        return ' ' + name.ljust(3)
    return name.ljust(4)


def _hand(a, b):
    return (a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
            and min(abs(a), abs(b)) > VOLUME_EPSILON and (a > 0) == (b > 0))


def base_fragment_atoms(roles, neighbors):
    """Find the complete base-side fragment after cutting its one glycosidic edge."""
    base, sugar = roles['base'], roles['anomeric']
    fragment = set(); pending = [base]
    while pending:
        atom = pending.pop()
        if atom in fragment:continue
        fragment.add(atom)
        pending.extend(n for n in neighbors[atom]
            if {atom, n} != {base, sugar} and n not in fragment)
    if sugar in fragment:
        raise ValueError('Base must separate from the source sugar at its declared edge')
    return fragment


def _base_frame_bindings(profile, values, frame_roles):
    """Bind explicit NAR roles to the base side of the source glycosidic edge."""
    mapping = profile['operational_signature']['atom_roles']
    elements, bonds, _, neighbors = _graph(values)
    roles = profile['bindings']; base = roles['base']
    names = [mapping.get(role) for role in frame_roles]
    if (len(set(names)) != 3 or names[0] != base
            or any(elements.get(n) in {None, 'H', 'D'} for n in names)):
        raise ValueError('Require distinct heavy NAR base anchors, glycosidic atom first')
    if not set(names) <= base_fragment_atoms(roles,neighbors):
        raise ValueError('Frame anchors must lie on the separated source base fragment')
    edges = [bonds.get(tuple(sorted((base, n)))) for n in names[1:]]
    if any(edge is None for edge in edges):
        raise ValueError('Require two source-bonded neighbors of the glycosidic base atom')
    return names, [elements[n] for n in names], edges


def _mapped_ring_frame(profile, values):
    """Identify the three alignment roles from the ring and this component's workbook row."""
    from .cif_doctor import _bridges

    elements, _, _, neighbors = _graph(values)
    roles = profile['bindings']
    base = roles['base']
    fragment = base_fragment_atoms(roles, neighbors)
    adjacent = {n for n in neighbors[base] & fragment if elements[n] not in {'H','D','T'}}
    bridges = _bridges(neighbors)
    if len(adjacent) != 2 or any(frozenset((base, n)) in bridges for n in adjacent):
        raise ValueError('Base alignment requires two ring neighbours of the glycosidic atom')
    mapped = {}
    for atom in {base, *adjacent}:
        labels = [role for role, n in profile['operational_signature']['atom_roles'].items() if n == atom]
        if len(labels) != 1:
            raise ValueError('Base ring alignment requires one distinct workbook role for each anchor')
        mapped[atom] = labels[0]
    return [mapped[base], *sorted(mapped[n] for n in adjacent)]


def _derive_base(root):
    return _derive(root, base_anchored=True)


def _derive_model_base(root):
    return _derive(root, base_anchored=True, model_ports=True)


def _derive_model_edge(root):
    return _derive(root, base_anchored=True, model_ports=True, canonical_at_edge=True)


def _source_phosphate_leaving_atom(values, roles):
    """Require one source-marked terminal P–OH on the bound phosphate."""
    elements, bonds, charges, neighbors = _graph(values)
    names = values['_chem_comp_atom.atom_id']
    flags = values.get(_LEAVING_FLAG, ())
    if len(flags) != len(names):
        raise ValueError('Missing or incomplete source phosphate leaving flags')
    by_atom = {name: flag.upper() for name, flag in zip(names, flags)}
    phosphorus = roles['phosphate']
    adjacent = neighbors[phosphorus]
    if (elements[phosphorus] != 'P' or len(adjacent) != 4
            or any(elements[n] != 'O' or by_atom[n] not in {'Y', 'N'} for n in adjacent)):
        raise ValueError('The phosphate needs four oxygen neighbours with explicit leaving flags')
    selected = [n for n in adjacent if by_atom[n] == 'Y']
    if len(selected) != 1:
        raise ValueError('The source must flag exactly one phosphate oxygen as leaving')
    atom = selected[0]
    if atom == roles['five_o'] or atom.upper() in _RETAINED_PHOSPHATE_OXYGENS:
        raise ValueError('Source leaving flag identifies a retained phosphate oxygen')
    heavy = {n for n in neighbors[atom] if elements[n] not in {'H', 'D'}}
    if (heavy != {phosphorus} or bonds[tuple(sorted((atom, phosphorus)))] != 'SINGLE'
            or _neutral_hydroxyl_hydrogens(atom, elements, bonds, charges, neighbors) is None):
        raise ValueError('Source leaving flag requires a singly bonded terminal neutral P–OH')
    return atom


def declared_internal_ports(row, sites, leaving_atom):
    """Describe the two same-image partners of an already audited model site."""
    if (row['five_prime_state'] != 'linked' or row['three_prime_state'] != 'linked'
            or row.get('symmetry_operation') not in (None, 'x,y,z') or row.get('experimental_passthrough')):
        raise ValueError('Placement requires an internal site with two audited backbone links')
    ports = {}
    for port, partner, atom in (('phosphate', row['incoming_site'], "O3'"),
                                ('alcohol', row['outgoing_site'], 'P')):
        ports[port] = dict(state='linked', symmetry_operation='x,y,z',
                           partner=dict(site=partner, component=sites[partner]['component'], atom_id=atom))
    ports['phosphate']['leaving_atom'] = leaving_atom
    return dict(schema_version=1, site=row['site'], ports=ports)


def _ordinary_ports(frame, site, leaving_atom, report):
    """Resolve the two partners from the ordinary phosphate audit on these coordinates."""
    from .cif_model_context import derive_prepared_model_context

    site = _site(site)
    frame = Path(frame).expanduser()
    payload = _read_site_artifact(frame)
    sites = _model(payload)
    if site not in sites:
        raise ValueError('Selected host site is absent')
    if not isinstance(leaving_atom, str) or not leaving_atom.strip():
        raise ValueError('Require the explicit source phosphate leaving atom')
    if leaving_atom.upper() in _RETAINED_PHOSPHATE_OXYGENS:
        raise ValueError('Ordinary placement cannot remove a retained phosphate oxygen')
    code = sites[site]['component']
    topology = derive_prepared_model_context(frame, report, [code])
    if topology['model_sha256'] != sha256(payload).hexdigest():
        raise ValueError('Host model changed during ordinary link determination')
    row, = (r for r in topology['contexts'][code] if r['site'] == site)
    context = declared_internal_ports(row, sites, leaving_atom)
    binding = dict(model_sha256=topology['model_sha256'], intent=topology['intent'])
    return context, binding, code


def _uracil_attachment(source, code, workbook, profile=None):
    """Identify the ring attachment element only for a source-proven uracil pairing edge."""
    from .cif_pyrimidine_edge import source_uracil_edge

    if profile is None:
        profile = inspect_attachment_profile(source, code, workbook=workbook)
    if profile['topology_status'] != 'MATCH' or profile['matched_profile'] not in _PROFILES:
        return None
    graph = _graph(_values(source, code))
    attachment = profile['bindings']['base']
    if source_uracil_edge(graph, attachment) is not None:
        return graph[0][attachment]
    return None


def _derive(root, *, base_anchored=False, model_ports=False, canonical_at_edge=False):
    selection = _load(root/'selection.json')
    fields = ('code', 'base_frame_roles') if base_anchored else ('code',)
    _object(selection, fields + (('ordinary_backbone',) if model_ports else ()),
            ('pdb_atom_name_policy',) + (('leaving_atom_source',) if model_ports else ()))
    if 'pdb_atom_name_policy' in selection and selection['pdb_atom_name_policy'] != _PDB_ATOM_FIELDS:
        raise ValueError('Unknown PDB atom-name field policy')
    automatic_frame = model_ports and selection.get('base_frame_roles') == _MAPPED_RING_FRAME
    if canonical_at_edge and selection['base_frame_roles'] != _EDGE_FRAME:
        raise ValueError('Require the declared canonical uracil pairing frame')
    if base_anchored and not (automatic_frame or canonical_at_edge):
        frame_roles = selection['base_frame_roles']
        if (not isinstance(frame_roles, list) or len(frame_roles) != 3
                or any(not isinstance(r, str) or not r for r in frame_roles)
                or len(set(frame_roles)) != 3):
            raise ValueError('Require three explicit distinct NARestraints base frame roles')
    code = selection['code']
    if not isinstance(code, str) or not re.fullmatch('[A-Z0-9]{1,3}', code):
        raise ValueError('Require an explicit PDB-compatible component code')
    context = _load(root/'context.json')
    _object(context, ('schema_version', 'site', 'ports'))
    if type(context['schema_version']) is not int or context['schema_version'] != 1:
        raise ValueError('Unsupported context schema')
    selected = _site(context['site']); _object(context['ports'], ('phosphate', 'alcohol'))
    if model_ports:
        binding = selection['ordinary_backbone']
        _object(binding, ('intent', 'model_sha256'))
        phosphate = context['ports']['phosphate']
        _object(phosphate, ('state', 'partner', 'symmetry_operation', 'leaving_atom'))
        expected, actual, _ = _ordinary_ports(root/'frame.pdb', selected, phosphate['leaving_atom'], binding['intent'])
        if actual != binding or context != expected:
            raise ValueError('Placement ports or source binding differ from the ordinary backbone audit')
    payload = (root/'frame.pdb').read_bytes(); sites = _model(payload)
    if selected not in sites:
        raise ValueError('Selected host site is absent')
    host = sites[selected]
    profiles = [inspect_attachment_profile(root/name, component, workbook=root/'Ligands.xlsx',
                                           check_at_pair=canonical_at_edge)
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
    if 'leaving_atom_source' in selection:
        if (selection['leaving_atom_source'] != _LEAVING_FLAG or
                _source_phosphate_leaving_atom(values, roles) != context['ports']['phosphate']['leaving_atom']):
            raise ValueError('Recorded phosphate leaving atom differs from its source flag')
    terms = assessment['finished_stereo']['terms']
    # This audit includes both atom R/S labels and fixed source chirality loops.
    centers = {r['center'] for r in terms}
    if not centers or any(r['handedness'] != 'PRESERVED' for r in terms):
        raise ValueError('Require every source-declared stereocentre to be preserved')
    family, xyz = _coordinates(_values(root/'numerical.cif', code), source=False)
    if set(xyz) != set(elements):
        raise ValueError('Require complete finite candidate coordinates')
    host_values = _values(root/'host.cif', host['component'])
    host_graph = _graph(host_values)
    host_elements = host_graph[0]
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
    # Replacement stays in the host Cartesian frame. Crystal axes pass through verbatim.
    allowed = {'ATOM', 'HETATM', 'REMARK', 'CRYST1', 'SCALE1', 'SCALE2', 'SCALE3', 'TER', 'END', ''}
    if any(line[:6].strip() not in allowed for line in lines):
        raise ValueError('Unsupported frame records require reconciliation')
    inventory = _pdb_inventory(root/'frame.pdb'); chain, resid = selected.split(':')
    center = {k[-1]: a['xyz'] for k, a in inventory.items() if k[:2] == (chain, resid)}
    checks = []
    for role, adjacent in [('anomeric', ('ring_o', 'ring_c2', 'base')),
                            ('ring_c3', ('ring_c2', 'ring_c4', 'three_o')),
                            ('ring_c4', ('ring_o', 'ring_c3', 'five_c'))]:
        a = _volume(xyz, roles[role], [roles[r] for r in adjacent])
        b = _volume(center, host_roles[role], [host_roles[r] for r in adjacent])
        if (not base_anchored or canonical_at_edge) and not _hand(a, b):
            raise ValueError('Host and target sugar hands differ or are degenerate: ' + role)
        checks.append({'role': role, 'target_volume': a, 'host_volume': b})
        if base_anchored:checks[-1]['compatible'] = _hand(a, b)
    if canonical_at_edge:
        from .cif_pyrimidine_edge import match_uracil_frame
        target_frame, host_frame, xyz, rotation = match_uracil_frame(
            profiles, [(elements, bonds, charges, neighbors), host_graph], xyz, center)
        frame_roles = ('glycosidic_ring_atom', 'adenine_N1_donor', 'adenine_N6_acceptor')
    elif base_anchored:
        if automatic_frame:
            frame_roles = _mapped_ring_frame(profiles[0], values)
            if _mapped_ring_frame(profiles[1], host_values) != frame_roles:
                raise ValueError('Host and target have different workbook roles at the glycosidic ring')
        target_frame, target_elements, target_edges = _base_frame_bindings(profiles[0], values, frame_roles)
        host_frame, frame_elements, host_edges = _base_frame_bindings(profiles[1], host_values, frame_roles)
        if (target_elements != frame_elements or target_edges != host_edges
                or any(n not in center for n in host_frame)):
            raise ValueError('Host and target base frames require matching elements/edges and present atoms')
    if base_anchored:
        a, b = [xyz[n] for n in target_frame], [center[n] for n in host_frame]
    else:
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
        # Older capsules replay their exact original four-column fields.
        atom_field = _pdb_atom_field(n, elements[n]) if 'pdb_atom_name_policy' in selection else n.rjust(4)
        replacement.append(f'HETATM{serial:5d} {atom_field} {code:>3} {" " if chain == "_" else chain}{int(resid):4d}    {"".join(fields)}  1.00 20.00          {elements[n]:>2}\n')
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
    report = {'schema_version': 1, 'policy_id': BASE_POLICY_ID if base_anchored else POLICY_ID, 'status': 'PLACED_FOR_LINK_REVIEW',
            'component': code, 'context': context, 'source_profile': profiles[0]['matched_profile'],
            'host_profile': profiles[1]['matched_profile'], 'coordinate_family': family,
            'rotation_determinant': determinant, 'frame_roles': list(frame_roles),
            'host_hand_checks': checks, 'retained_hands': hands, 'source_projection': projection,
            'max_internal_distance_error_angstrom': error, 'model_heavy_atoms': heavy,
            'junction_distances': junctions, 'bystander_records_preserved': True,
            'selected_occupancy': 1.0, 'selected_b_factor': 20.0,
            'native_linkage': 'NOT_ASSESSED', 'partner_chemistry': 'NOT_ASSESSED',
            'model_optimization': 'NOT_RUN', 'clash_assessment': 'NOT_RUN', 'automatic_adoption': False}
    if base_anchored:
        report.update(alignment='NAR_BASE_FRAME', target_frame_atoms=target_frame,
            host_frame_atoms=host_frame, base_anchor_residuals_angstrom=[math.dist(moved[n], p) for n, p in zip(target_frame, b)],
            host_sugar_compatibility_required=False, base_chemical_equivalence='NOT_ASSERTED')
    if model_ports:
        report.update(policy_id=MODEL_BASE_POLICY_ID, ordinary_backbone=selection['ordinary_backbone'])
    if canonical_at_edge:
        report.update(policy_id=MODEL_EDGE_POLICY_ID, alignment='CANONICAL_URACIL_EDGE',
                      base_frame_source=_EDGE_FRAME, host_sugar_compatibility_required=True,
                      glycosidic_rotation=rotation, internal_distance_reference='AFTER_GLYCOSIDIC_ROTATION')
    elif automatic_frame:
        report['base_frame_source'] = _MAPPED_RING_FRAME
    if 'leaving_atom_source' in selection:
        report['phosphate_leaving_atom'] = dict(atom=context['ports']['phosphate']['leaving_atom'], source=_LEAVING_FLAG)
    return report, model


def prepare_whole_furanose_control(source, numerical, host_source, workbook, frame, output, *, code, context):
    """Write a fresh bound diagnostic, never modify a model or retry in place."""
    return _prepare_control(source, numerical, host_source, workbook, frame, output,
        context=context, selection={'code': code}, derive=_derive, policy=POLICY_ID)


def prepare_base_anchored_furanose_control(source, numerical, host_source, workbook, frame, output,
                                          *, code, context, base_frame_roles):
    """Explicitly replace the host sugar using a proper source-bound base transform.

    This diagnostic does not assert base equivalence or repair backbone gaps.
    All target stereochemistry remains mandatory; host sugar hands are observations.
    """
    return _prepare_control(source, numerical, host_source, workbook, frame, output,
        context=context, selection={'code': code, 'base_frame_roles': base_frame_roles},
        derive=_derive_base, policy=BASE_POLICY_ID)


def prepare_base_anchored_furanose_from_model(source, numerical, host_source, workbook, frame, output,
                                              *, code, site, postmr_report, base_frame_roles=None, leaving_atom=None,
                                              canonical_at_edge=None):
    """Place an internal replacement using the host's audited asymmetric-unit links.

    Without an explicit leaving atom the source must flag exactly one terminal,
    neutral phosphate hydroxyl. Without explicit base roles, both source graphs
    and workbook rows must agree on the two ring neighbours of the glycosidic
    atom. A change between C- and N-linked uracil rings uses their verified
    adenine-pairing edges and transfers the host glycosidic torsion. An explicit
    True or False selects the corresponding frame directly. Replay checks the
    concrete frame saved in each placement.
    """
    if (canonical_at_edge is not None and type(canonical_at_edge) is not bool) or (canonical_at_edge and base_frame_roles is not None):
        raise ValueError('The canonical pairing frame and an explicit base frame are separate choices')
    if base_frame_roles is not None and not isinstance(base_frame_roles, list):
        raise ValueError('Require three explicit distinct NARestraints base frame roles')
    selection = dict(code=code, base_frame_roles=_MAPPED_RING_FRAME if base_frame_roles is None else base_frame_roles)
    profile = None
    if leaving_atom is None:
        profile = inspect_attachment_profile(source, code, workbook=workbook)
        if profile['topology_status'] != 'MATCH' or profile['matched_profile'] not in _PROFILES:
            raise ValueError('Source leaving flags require a supported furanose phosphate')
        leaving_atom = _source_phosphate_leaving_atom(_values(source, code), profile['bindings'])
        selection['leaving_atom_source'] = _LEAVING_FLAG
    context, binding, host_code = _ordinary_ports(frame, site, leaving_atom, postmr_report)
    if canonical_at_edge is None and base_frame_roles is None:
        target = _uracil_attachment(source, code, workbook, profile)
        if target in {'C', 'N'}:
            host = _uracil_attachment(host_source, host_code, workbook)
            canonical_at_edge = {target, host} == {'C', 'N'}
    if canonical_at_edge:
        selection['base_frame_roles'] = _EDGE_FRAME
    selection['ordinary_backbone'] = binding
    return _prepare_control(source, numerical, host_source, workbook, frame, output,
        context=context, selection=selection, derive=_derive_model_edge if canonical_at_edge else _derive_model_base,
        policy=MODEL_EDGE_POLICY_ID if canonical_at_edge else MODEL_BASE_POLICY_ID)


def _prepare_control(source, numerical, host_source, workbook, frame, output, *, context, selection, derive, policy):
    paths = dict(zip(('source.cif', 'numerical.cif', 'host.cif', 'Ligands.xlsx', 'frame.pdb'),
                    [Path(p).expanduser().resolve(strict=True) for p in (source, numerical, host_source, workbook, frame)]))
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or any(p.is_relative_to(out.resolve()) for p in paths.values()):
        raise ValueError('Output must be separate and cannot traverse symlinks')
    before = {name: p.read_bytes() for name, p in paths.items()}
    selection = {**selection, 'pdb_atom_name_policy': _PDB_ATOM_FIELDS}
    # Validate before making the durable attempt, then rederive from frozen inputs.
    with tempfile.TemporaryDirectory(prefix='nasolve-whole-preflight-') as temporary:
        stage = Path(temporary).resolve(strict=True)
        for name, data in before.items():(stage/name).write_bytes(data)
        _save(stage/'context.json', context); _save(stage/'selection.json', selection)
        expected, model = derive(stage)
        out.mkdir(parents=True, exist_ok=False)
        for name in _INPUTS:
            with (out/name).open('xb') as stream:stream.write((stage/name).read_bytes())
    actual, frozen = derive(out)
    if actual != expected or frozen != model or any(p.read_bytes() != before[n] for n, p in paths.items()):
        raise ValueError('Placement inputs changed during freezing')
    with (out/'model.pdb').open('x') as stream:stream.write(model)
    _save(out/'placement.json', actual)
    _save(out/'receipt.json', {'schema_version': 1, 'policy_id': policy, 'files': {n: _digest(out/n) for n in sorted(_INPUTS | _OUTPUTS)}})
    return _read_control(out, derivations={policy: derive})


def read_whole_furanose_control(control):
    """Verify the exact frozen capsule and recompute chemistry/geometry offline."""
    return _read_control(control, derivations={POLICY_ID: _derive})


def read_base_anchored_furanose_control(control):
    """Recompute a frozen base-anchored placement without external programs."""
    return _read_control(control, derivations={BASE_POLICY_ID: _derive_base, MODEL_BASE_POLICY_ID: _derive_model_base,
                                              MODEL_EDGE_POLICY_ID: _derive_model_edge})


def _read_control(control, *, derivations):
    root = Path(control).expanduser().resolve(strict=True); paths = list(root.rglob('*'))
    names = _INPUTS | _OUTPUTS | {'receipt.json'}
    if any(p.is_symlink() or not p.is_file() for p in paths) or {p.name for p in paths} != names:
        raise ValueError('Require an exact nonsymlinked placement capsule')
    before = {p: p.read_bytes() for p in paths}; receipt = _load(root/'receipt.json')
    if (set(receipt) != {'schema_version', 'policy_id', 'files'} or type(receipt['schema_version']) is not int
            or receipt['schema_version'] != 1 or not isinstance(receipt['policy_id'], str)
            or receipt['policy_id'] not in derivations
            or receipt['files'] != {n: _digest(root/n) for n in sorted(_INPUTS | _OUTPUTS)}):
        raise ValueError('Invalid completion receipt or checksums')
    report, model = derivations[receipt['policy_id']](root)
    if report != _load(root/'placement.json') or model.encode() != (root/'model.pdb').read_bytes() or any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError('Saved placement differs from fresh derivation')
    return report
