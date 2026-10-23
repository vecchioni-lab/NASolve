"""Compile declared site pairs and chain-order stacks through NARestraints.

This is a coordinate-bound compiler control, not native proxy qualification.
Input indices are PDB record ordinals. No relationship or target is inferred
from a distance, and swapped plane-order controls never enter the live PHIL.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace

POLICY_ID = 'narestraints-explicit-site-policy-v1'
ANCHOR = 'explicit_na_policy_directory'
_COMPILED = 'EXPLICIT_NA_POLICY_COMPILED'
_SITE = re.compile(r'[A-Za-z0-9]:-?(?:0|[1-9][0-9]*)\Z')
_CODE = re.compile(r'[A-Z0-9]{1,3}\Z')


def _regular(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
        raise ValueError('Require a regular input without symlink traversal')
    return path


def _ref(name, data):
    return {'anchor': ANCHOR, 'path': name, 'size': len(data),
            'sha256': sha256(data).hexdigest()}


def _dump(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def _model(path):
    from Bio.PDB import PDBParser
    raw = _regular(path).read_bytes()
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeError as exc:
        raise ValueError('Require an ASCII fixed-column PDB') from exc
    atoms = []; site_codes = {}; order = []; by_key = {}
    for line in lines:
        if line[:6] not in {'ATOM  ', 'HETATM'}:
            continue
        if len(line) < 78 or line[16].strip() or line[26].strip():
            raise ValueError('Alternate, insertion or incomplete PDB identity')
        chain, resid, code, name = line[21], line[22:26].strip(), line[17:20].strip(), line[12:16].strip()
        site = chain + ':' + resid
        element = line[76:78].strip().upper()
        if not _SITE.fullmatch(site) or not _CODE.fullmatch(code) or not name or not element:
            raise ValueError('Unsupported fixed-column atom or site identity')
        try:
            xyz = [float(line[i:i+8]) for i in (30, 38, 46)]
        except ValueError as exc:
            raise ValueError('Malformed PDB coordinates') from exc
        if not all(math.isfinite(v) for v in xyz):
            raise ValueError('Non-finite PDB coordinates')
        key = (site, name)
        if key in by_key:
            raise ValueError('Duplicate PDB atom identity')
        if site in site_codes and site_codes[site] != code:
            raise ValueError('Multiple component identities at one PDB site')
        if site in site_codes and order[-1] != site:
            raise ValueError('Noncontiguous PDB residue identity')
        if site not in site_codes:
            site_codes[site] = code; order.append(site)
        i = len(atoms)
        row = {'i_seq': i, 'atom_id': name, 'label': f'pdb-record-{i}:{site}:{code}:{name}',
               'element': element,
               'identity': {'model_id': '0', 'chain_id': chain, 'resseq': resid,
                            'icode': '', 'resname': code, 'altloc': ''}}
        atoms.append(row); by_key[key] = row
    if not atoms:
        raise ValueError('PDB has no coordinate atoms')
    structure = PDBParser(QUIET=True).get_structure('explicit_policy', str(path))
    models = list(structure.get_models())
    if len(models) != 1:
        raise ValueError('Require exactly one PDB model')
    residues = {}
    observed = set()
    for chain in models[0]:
        for residue in chain:
            site = chain.id + ':' + str(residue.id[1])
            if site in residues or residue.id[2].strip():
                raise ValueError('Ambiguous parsed PDB site')
            residues[site] = residue
            if residue.resname.strip() != site_codes.get(site):
                raise ValueError('Parsed PDB component differs from fixed-column identity')
            for atom in residue:
                if atom.is_disordered():
                    raise ValueError('Disordered PDB atom requires a separate policy')
                observed.add((site, atom.name))
    if observed != set(by_key):
        raise ValueError('Parsed and fixed-column PDB identities differ')
    adjacency = {frozenset((a, b)) for a, b in zip(order, order[1:])
                 if a.split(':')[0] == b.split(':')[0]}
    return raw, atoms, residues, site_codes, by_key, adjacency


def _pair(row, site_codes):
    if (not isinstance(row, dict) or set(row) != {'sites', 'components', 'scope'}
            or row['scope'] not in {'requested', 'background'}
            or not isinstance(row['sites'], (list, tuple)) or len(row['sites']) != 2
            or not isinstance(row['components'], (list, tuple)) or len(row['components']) != 2):
        raise ValueError('Require explicit sites, components and pair scope')
    sites = list(row['sites']); codes = list(row['components'])
    if (any(not isinstance(s, str) or not _SITE.fullmatch(s) for s in sites)
            or any(not isinstance(c, str) or not _CODE.fullmatch(c) for c in codes)
            or sites[0] == sites[1]
            or any(site_codes.get(s) != c for s, c in zip(sites, codes))):
        raise ValueError('Declared pair component/site does not match the actual PDB')
    return {'sites': sites, 'components': codes, 'scope': row['scope']}


def _wrap(blocks):
    return ('refinement {\n pdb_interpretation {\n  secondary_structure {\n   enabled = False\n  }\n }\n'
            ' geometry_restraints {\n  edits {\n' + '\n\n'.join(blocks) + '\n  }\n }\n}\n')


def _implementation():
    from restraints import builder, phenix, recipe_library, residue_library, stacking
    rows = {}
    for module in [builder, phenix, recipe_library, residue_library, stacking]:
        path = _regular(module.__file__)
        rows[module.__name__] = sha256(path.read_bytes()).hexdigest()
    workbook = _regular(Path(residue_library.__file__).parent / 'data/Ligands.xlsx')
    rows['restraints/data/Ligands.xlsx'] = sha256(workbook.read_bytes()).hexdigest()
    return rows


def _payload(model, pairs, stacks, sources, orientation_controls):
    from .cif_na_policy import _requests, _signature
    from .cif_stereochemistry_audit import _values, _graph
    from .curated_ligands import validate_ligand_dictionary
    from .component_records import resolve_component_record
    from .postmr import _patch_narestraints_records
    from restraints.builder import pair_residue_from_pdb
    from restraints.phenix import generate_pair_restraints
    from restraints.recipe_library import recipe_for
    from restraints.residue_library import load_residue_records
    from restraints.stacking import _manual_parallelity

    if (not isinstance(pairs, (list, tuple)) or not 1 <= len(pairs) <= 64
            or not isinstance(stacks, (list, tuple)) or len(stacks) > 256
            or not isinstance(sources, dict) or not sources):
        raise ValueError('Explicit policy scope exceeds supported bounds')
    raw, atoms, residues, site_codes, by_key, adjacency = _model(model)
    declared = [_pair(row, site_codes) for row in pairs]
    pair_edges = [frozenset(row['sites']) for row in declared]
    used_pairs = [s for row in declared for s in row['sites']]
    if len(set(pair_edges)) != len(pair_edges) or len(set(used_pairs)) != len(used_pairs):
        raise ValueError('Duplicate or multiply paired declared site')
    edges = []
    for edge in stacks:
        if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                or any(not isinstance(s, str) or not _SITE.fullmatch(s) or s not in site_codes for s in edge)
                or frozenset(edge) not in adjacency):
            raise ValueError('Require a declared same-chain PDB-order adjacent stack')
        edges.append(list(edge))
    if len({frozenset(e) for e in edges}) != len(edges):
        raise ValueError('Duplicate or reversed duplicate stack')
    sites = set(used_pairs) | {s for edge in edges for s in edge}
    codes = {site_codes[s] for s in sites}
    if set(sources) != codes:
        raise ValueError('Source component coverage differs from declared pair/stack sites')
    source_data = {}; source_elements = {}; files = {'inputs/model.pdb': raw}
    for code, path in sorted(sources.items()):
        if not isinstance(code, str) or not _CODE.fullmatch(code):
            raise ValueError('Unsupported source component id')
        path = _regular(path); before = path.read_bytes()
        validate_ligand_dictionary(code, path)
        elements = _graph(_values(path, code))[0]
        if path.read_bytes() != before:
            raise ValueError('Source changed while compiling policy')
        source_data[code] = before; source_elements[code] = elements
        files[f'inputs/sources/{code}.cif'] = before
    records, corrections = _patch_narestraints_records(load_residue_records(), codes)
    mappings = {}; role_evidence = {}
    for site in sorted(sites):
        code = site_codes[site]; record, proof = resolve_component_record(records, code)
        mapping = pair_residue_from_pdb([record], residues[site])
        graph_identity = SimpleNamespace(get_resname=lambda c=code: c,
            has_id=lambda name, e=source_elements[code]: name in e,
            id=('', int(site.split(':')[1]), ''),
            get_parent=lambda c=site.split(':')[0]: SimpleNamespace(get_id=lambda: c))
        expected = pair_residue_from_pdb([record], graph_identity)
        if mapping.base_class != expected.base_class or mapping.atoms != expected.atoms:
            raise ValueError('Missing or inconsistent actual/source NARestraints atom roles at ' + site)
        for name in mapping.atoms.values():
            if (site, name) not in by_key or by_key[site, name]['element'] != source_elements[code].get(name):
                raise ValueError('Mapped atom element differs from its selected source at ' + site)
        mappings[site] = mapping
        role_evidence[site] = {'component': code, 'base_class': mapping.base_class,
            'mapped_atoms': dict(sorted(mapping.atoms.items())), 'role_resolution': proof,
            'source_graph_and_actual_atoms_match': True}
    blocks = []; relationships = []; compiled = []; requested = []
    def append(kind, row, block, **extra):
        requests = _requests(_wrap([block]), atoms)
        if not requests:
            raise ValueError('Declared relationship emitted no requests')
        start = len(compiled); compiled.extend(requests); blocks.append(block)
        relationships.append({'kind': kind, **row, **extra,
            'request_indices': list(range(start, len(compiled)))})
        if row.get('scope') == 'requested':requested.extend(requests)
    for row in declared:
        first, second = [mappings[s] for s in row['sites']]
        recipe = recipe_for(first.base_class, second.base_class)
        if recipe is None:
            raise ValueError('No NARestraints recipe for the explicit pair at ' + ', '.join(row['sites']))
        block = generate_pair_restraints(first, second, planes=False)
        if not block:
            raise ValueError('Configured NARestraints pair produced no restraints')
        append('base_pair', row, block, recipe=recipe.name,
               base_classes=[first.base_class, second.base_class])
    for edge in edges:
        first, second = [mappings[s] for s in edge]
        append('stacking_pair', {'sites': edge, 'components': [site_codes[s] for s in edge],
            'scope': 'declared_chain_adjacency'}, _manual_parallelity(first, second),
            recipe='mapped-base-class-stacking', base_classes=[first.base_class, second.base_class])
    signatures = [_signature(q['kind'], q, values=False) for q in compiled]
    if len(set(signatures)) != len(signatures):
        raise ValueError('Pair/stack requests overlap and would double a restraint')
    for q in compiled:
        target = {'bond': 'distance_ideal', 'angle': 'angle_ideal', 'parallelity': 'target_angle_deg'}[q['kind']]
        if not math.isfinite(q[target]) or not math.isfinite(q['weight']) or q['weight'] <= 0:
            raise ValueError('Non-finite or nonpositive NARestraints parameter')
    controls = [] if orientation_controls is None else orientation_controls
    if not isinstance(controls, (list, tuple)) or len(controls) > 64:
        raise ValueError('Orientation-control scope exceeds supported bounds')
    control_rows = [_pair(row, site_codes) for row in controls]
    requested_edges = {frozenset(row['sites']) for row in declared if row['scope'] == 'requested'}
    control_edges = [frozenset(row['sites']) for row in control_rows]
    if (len(set(control_edges)) != len(control_edges) or any(row['scope'] != 'requested' for row in control_rows)
            or not set(control_edges) <= requested_edges):
        raise ValueError('Orientation controls must be unique declared requested pairs')
    orientation_rows = []
    for number, row in enumerate(control_rows):
        order_requests = []
        for order in [row['sites'], row['sites'][::-1]]:
            text = _wrap([_manual_parallelity(*(mappings[s] for s in order))])
            requests = _requests(text, atoms)
            if len(requests) != 1 or requests[0]['kind'] != 'parallelity':
                raise ValueError('Incomplete standalone plane-order control')
            order_requests.append(requests[0])
        if _signature('parallelity', order_requests[0]) != _signature('parallelity', order_requests[1]):
            raise ValueError('Swapped plane-order target or mapped membership differs')
        for order_index, (order, request) in enumerate(zip([row['sites'], row['sites'][::-1]], order_requests)):
            name = f'orientation_controls/{number:03d}_{order_index}.phil'
            files[name] = _wrap([_manual_parallelity(*(mappings[s] for s in order))]).encode()
            orientation_rows.append({'sites': order, 'components': [site_codes[s] for s in order],
                'request': request, 'file': _ref(name, files[name]),
                'included_in_active_policy': False, 'swapped_membership_targets_equal': True})
    files['explicit_na_policy.phil'] = _wrap(blocks).encode()
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': _COMPILED,
        'policy_authority': 'NARestraints', 'requires_cif_review': False, 'automatic_adoption': False,
        'index_basis': 'PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES',
        'pair_count': len(declared), 'requested_pair_count': sum(r['scope'] == 'requested' for r in declared),
        'background_pair_count': sum(r['scope'] == 'background' for r in declared),
        'stack_count': len(edges), 'orientation_control_count': len(orientation_rows),
        'source_component_count': len(codes), 'pairs': declared, 'stacks': edges,
        'orientation_control_pairs': control_rows, 'relationships': relationships,
        'compiled_requests': compiled, 'request_counts': dict(sorted(Counter(q['kind'] for q in compiled).items())),
        'requested_request_counts': dict(sorted(Counter(q['kind'] for q in requested).items())),
        'orientation_controls': orientation_rows, 'site_roles': role_evidence,
        'atom_identities': atoms, 'record_corrections': corrections,
        'implementation_sha256': _implementation(),
        'inputs': {'model': _ref('inputs/model.pdb', raw),
                   'sources': {c: _ref(f'inputs/sources/{c}.cif', d) for c, d in sorted(source_data.items())}},
        'compiled_phil': _ref('explicit_na_policy.phil', files['explicit_na_policy.phil']),
        'outputs': [_ref(n, d) for n, d in sorted(files.items())],
        'stack_topology': 'CALLER_DECLARED_PDB_CHAIN_ORDER_ADJACENCY; NOT_DISTANCE_OR_COVALENT_GEOMETRY_EVIDENCE',
        'orientation_control_scope': 'BOTH_ORDERS_OF_EACH_REQUESTED_PAIR; SEPARATE_COMPILER_CONTROLS_NOT_PHYSICAL_STACK_EDGES',
        'native_execution': 'NOT_RUN', 'native_membership': 'NOT_ASSESSED', 'model_editing': 'NOT_RUN',
        'model_optimization': 'NOT_RUN', 'readyset_execution': 'NOT_RUN', 'dictionary_generation': 'NOT_RUN',
        'refinement': 'NOT_RUN', 'production_checkpoint': 'NOT_CREATED', 'scientific_qualification': 'NOT_ASSESSED',
        'limitations': ['Only explicitly declared relationships enter the policy; no pair or stack guessing.',
            'PDB role/selection binding does not establish active native proxies, source chemistry or achieved geometry.',
            'Plane-order compiler controls are separate files and are never included in the active policy.',
            'Source priority and authority are supplied by the acquisition caller; this compiler does not reselect sources.']}
    if _regular(model).read_bytes() != raw or any(_regular(sources[c]).read_bytes() != d for c, d in source_data.items()):
        raise ValueError('Policy input changed while compiling')
    return report, files


def compile_explicit_na_policy(model: Path, pairs: list[dict], stacks: list[tuple[str, str]],
                               sources: dict[str, Path], output: Path,
                               orientation_controls: list[dict] | None = None) -> dict:
    """Freeze an explicit coordinate-bound NARestraints policy without native calls."""
    output = Path(output).absolute()
    if output.exists() or any(p.is_symlink() for p in [output, *output.parents]):
        raise FileExistsError('Require a fresh regular explicit-policy output')
    report, files = _payload(model, pairs, stacks, sources, orientation_controls)
    output.mkdir(parents=True)
    for name, data in sorted(files.items()):
        path = output / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:handle.write(data)
    with (output / 'explicit_na_policy.json').open('xb') as handle:handle.write(_dump(report))
    return report


def read_explicit_na_policy(directory: Path) -> dict:
    """Verify portable inputs, outputs and maintained compiler reconstruction."""
    root = Path(directory).absolute()
    if any(p.is_symlink() for p in [root, *root.parents]):
        raise ValueError('Explicit-policy directory cannot traverse a symlink')
    record = _regular(root / 'explicit_na_policy.json')
    report = json.loads(record.read_bytes())
    if (not isinstance(report, dict) or report.get('schema_version') != 1
            or report.get('policy_id') != POLICY_ID or report.get('status') != _COMPILED):
        raise ValueError('Unsupported explicit-policy report')
    refs = report.get('outputs')
    if not isinstance(refs, list) or not refs:
        raise ValueError('Missing explicit-policy file inventory')
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError('Malformed explicit-policy reference')
        name = ref.get('path')
        if (ref.get('anchor') != ANCHOR or not isinstance(name, str) or not name
                or '\\' in name or ':' in name or name.startswith('/')
                or any(v in {'', '.', '..'} for v in name.split('/')) or name in seen):
            raise ValueError('Unsafe or duplicate explicit-policy reference')
        path = _regular(root / PurePosixPath(name)); data = path.read_bytes(); seen.add(name)
        if _ref(name, data) != ref:
            raise ValueError('Explicit-policy referenced bytes differ')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Explicit-policy file inventory contains a symlink')
        if path.is_file():actual.add(path.relative_to(root).as_posix())
    if actual != seen | {'explicit_na_policy.json'}:
        raise ValueError('Explicit-policy file inventory differs')
    inputs = report.get('inputs', {})
    if not isinstance(inputs, dict):
        raise ValueError('Malformed explicit-policy inputs')
    source_refs = inputs.get('sources', {})
    indexed = {ref['path']: ref for ref in refs}
    if (inputs.get('model') != indexed.get('inputs/model.pdb')
            or not isinstance(source_refs, dict) or not source_refs
            or any(not isinstance(c, str) or not _CODE.fullmatch(c)
                   or ref != indexed.get(f'inputs/sources/{c}.cif')
                   for c, ref in source_refs.items())
            or report.get('compiled_phil') != indexed.get('explicit_na_policy.phil')):
        raise ValueError('Explicit-policy operational inputs differ from checked inventory')
    model = root / 'inputs/model.pdb'
    sources = {c: root / f'inputs/sources/{c}.cif' for c in source_refs}
    fresh, files = _payload(model, report['pairs'], report['stacks'], sources, report['orientation_control_pairs'])
    if fresh != report or any((root / name).read_bytes() != data for name, data in files.items()):
        raise ValueError('Explicit-policy maintained reconstruction differs')
    return report
