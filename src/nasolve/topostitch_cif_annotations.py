"""Read-only transport of original deposited connection endpoints through a recut.

Raw rows survive even when their endpoints cannot be resolved. This module does
not write CIF chains, infer bonds, validate chemical semantics or activate forces.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import importlib
import json
import math
from pathlib import Path
import re

from .topostitch_registration import _fingerprint


def _rows(block, category):
    columns = block.get_mmcif_category(category)
    return [dict(zip(columns, row)) for row in zip(*columns.values())]


def _known(value):
    return isinstance(value, str) and bool(value)


@contextmanager
def _deposition_owner(source, expected_sha256):
    """Pin one Cedar deposition owner before and after isolated import."""
    from .topostitch_captured_job import _cedar
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('Require exact image owner SHA-256')
    package = Path(__file__).resolve().parent if source is None else Path(source).resolve(strict=True)/'nasolve'
    path = package/'cif_deposition_links.py'
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Cedar image owner differs from requested binding')
    with _cedar(source) as modules:
        namespace = modules['cif_native_validation'].__package__
        module = importlib.import_module(namespace+'.cif_deposition_links')
        if Path(module.__file__).resolve() != path.resolve():
            raise ValueError('Cedar image owner resolved outside the selected package')
        yield module
        if path.read_bytes() != data:
            raise ValueError('Cedar image owner changed during connection transport')


@contextmanager
def _image_owner(source, expected_sha256):
    """Keep W258's decoder interface while sharing its pinned owner binding."""
    with _deposition_owner(source, expected_sha256) as module:
        decoder = getattr(module, 'resolve_deposition_image', None)
        if not callable(decoder):
            raise ValueError('Selected Cedar owner lacks resolve_deposition_image')
        yield decoder


def _operations(block, gemmi):
    operations = {}; issues = []
    for category, field in (('_space_group_symop.', 'operation_xyz'),
                            ('_symmetry_equiv.', 'pos_as_xyz')):
        seen = set()
        for row in _rows(block, category):
            key, xyz = row.get('id'), row.get(field)
            if not _known(key) or not _known(xyz):
                issues.append('Incomplete declared operation ID or expression'); continue
            op = gemmi.Op(xyz)
            if key in seen:
                issues.append('Repeated operation ID in '+category+key)
            if key in operations and operations[key] != op:
                issues.append('Conflicting declared operation ID '+key)
            seen.add(key); operations[key] = op
    if not operations:
        issues.append('No explicit original symmetry operation table')
    return operations, issues


def _endpoint(row, side, atoms):
    """Resolve all supplied identity fields together; never take the first hit."""
    pairs = [(f'ptnr{side}_{field}', field) for field in (
        'label_asym_id', 'label_seq_id', 'label_comp_id', 'label_atom_id',
        'auth_asym_id', 'auth_seq_id', 'auth_comp_id', 'auth_atom_id')]
    pairs += [(f'ptnr{side}_label_alt_id', 'label_alt_id'),
              (f'pdbx_ptnr{side}_label_alt_id', 'label_alt_id'),
              (f'pdbx_ptnr{side}_auth_alt_id', 'auth_alt_id'),
              (f'pdbx_ptnr{side}_PDB_ins_code', 'pdbx_PDB_ins_code')]
    constraints = [(source, target, row[source]) for source, target in pairs
                   if source in row and (_known(row[source]) or row[source] is False
                                         and target in ('label_alt_id', 'auth_alt_id', 'pdbx_PDB_ins_code'))]
    supplied = {target for _, target, value in constraints if _known(value)}
    for names in (('label_atom_id','auth_atom_id'), ('label_asym_id','auth_asym_id'),
                  ('label_comp_id','auth_comp_id')):
        if not supplied.intersection(names):
            return None, ['Missing explicit endpoint '+names[0]+' or '+names[1]]
    matches = []
    for i, atom in enumerate(atoms):
        if all((atom.get(field) is False if value is False else atom.get(field) == value)
               for _, field, value in constraints):
            matches.append(i)
    if len(matches) != 1:
        return None, ['Endpoint identity matches '+str(len(matches))+' original atoms']
    index = matches[0]
    if (_known(atoms[index].get('label_seq_id'))
            and not supplied.intersection(('label_seq_id', 'auth_seq_id'))):
        return None, ['Polymer endpoint lacks an explicit residue sequence locator']
    for field in ('label_alt_id', 'pdbx_PDB_ins_code'):
        if _known(atoms[index].get(field)) and field not in supplied:
            return None, ['Endpoint lacks explicit '+field+' for a nonblank original value']
    return index, []


def observe_relabel_cif_connections(directory, model, *, expected_image_owner_sha256,
                                   cedar_source=None, **source_binding):
    """Preserve every original struct_conn row and observe exact image transport.

    Source controls forward unchanged to ``observe_relabel_cif_paths``. The
    explicitly selected Cedar source directory (containing ``nasolve``), or a
    compatible installed owner, supplies only symmetry-code decoding. Unknown,
    missing, conflicting and third-partner rows remain unresolved with reasons.
    For a source endpoint g(x) and representative y=h(x), its new operator is
    g h^-1. This preserves the absolute physical endpoint, not just its distance.
    Path positions are descriptive; no new atom/chain/entity labels are written.
    """
    import gemmi
    from .topostitch_cif_source import observe_relabel_cif_paths
    from .topostitch_recut_bundle import _FILES
    from .topostitch_graph import _compose, _inverse
    from .topostitch_recut import _arithmetic_bound
    from .topostitch_transport import crystallographic_image

    root = Path(directory); model = Path(model); manifest = root/'preview.json'
    frozen = {p: p.read_bytes() for p in [manifest, *(root/n for n in _FILES.values()), model]}
    paths = observe_relabel_cif_paths(root, model, **source_binding)
    if (sha256(frozen[model]).hexdigest() != paths['original_model_sha256']
            or sha256(frozen[manifest]).hexdigest() != paths['preview_receipt_sha256']):
        raise ValueError('Original source changed before connection transport')
    doc = gemmi.cif.read_string(frozen[model].decode('ascii'))
    block = next(b for b in doc if '_atom_site.' in b.get_mmcif_category_names())
    atoms = _rows(block, '_atom_site.'); rows = _rows(block, '_struct_conn.')
    operations, issues = _operations(block, gemmi)
    preview = json.loads(frozen[manifest])['observation']
    graph = preview['graph_relabeling']
    crystal = graph['periodic_graph']['crystal']
    images = {r['node_id']: r['image']['operator_xyz'] for r in graph['proposed_node_images']}
    sites = {atom_id: site for site in paths['registered_original_sites']
             for atom_id in site['original_atom_ids']}
    counts = {}
    for row in rows:
        if _known(row.get('id')): counts[row['id']] = counts.get(row['id'], 0)+1
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    observed = []; identity = gemmi.Op('x,y,z')
    with _image_owner(cedar_source, expected_image_owner_sha256) as decode:
        for number, row in enumerate(rows, 1):
            reasons = list(issues); endpoints = []
            if not _known(row.get('id')): reasons.append('Missing original connection ID')
            elif row['id'] in duplicates: reasons.append('Duplicate original connection ID')
            if any('ptnr3_' in key and _known(value) for key, value in row.items()):
                reasons.append('Third-partner annotation is outside two-endpoint transport')
            for side in (1, 2):
                index, errors = _endpoint(row, side, atoms)
                reasons.extend(f'Partner {side}: '+error for error in errors)
                op = None if issues else decode(row.get(f'ptnr{side}_symmetry'), operations)
                if op is None:
                    reasons.append(f'Partner {side}: unresolved explicitly declared symmetry code')
                if index is None or op is None:
                    continue
                atom = atoms[index]; site = sites.get(atom['id'])
                image = images.get(site['node_id'], 'x,y,z') if site else 'x,y,z'
                inverse = _inverse(gemmi.Op(image), identity)
                transformed = _compose(op, inverse).triplet()
                point = tuple(float(atom['Cartn_'+axis]) for axis in 'xyz')
                representative = crystallographic_image(**crystal, operator_xyz=image).apply(point)
                original_point = crystallographic_image(**crystal, operator_xyz=op.triplet()).apply(point)
                final_point = crystallographic_image(**crystal, operator_xyz=transformed).apply(representative)
                error = math.dist(original_point, final_point)
                bound = _arithmetic_bound(point, representative, original_point, final_point)
                if error > bound:
                    raise ValueError('Connection image transport changed a physical endpoint')
                endpoints.append(dict(partner=side, original_atom_id=atom['id'],
                    original_atom_labels={k:v for k,v in atom.items() if k.startswith(('label_', 'auth_')) or k=='pdbx_PDB_ins_code'},
                    registered_node_id=site['node_id'] if site else None,
                    proposed_path_position=site['proposed_path_position'] if site else None,
                    original_operator_xyz=op.triplet(), representative_image_xyz=image,
                    representative_operator_xyz=transformed,
                    original_physical_position_angstrom=original_point,
                    representative_physical_position_angstrom=final_point,
                    endpoint_error_angstrom=error, arithmetic_bound_angstrom=bound))
            record = dict(source_row_number=number, raw_fields=row, endpoints=endpoints,
                          status='UNRESOLVED' if reasons else 'TRANSPORTED_REVIEW_REQUIRED', reasons=reasons)
            if len(endpoints) == 2:
                a,b = endpoints
                record.update(original_distance_angstrom=math.dist(a['original_physical_position_angstrom'],b['original_physical_position_angstrom']),
                    representative_distance_angstrom=math.dist(a['representative_physical_position_angstrom'],b['representative_physical_position_angstrom']),
                    maximum_endpoint_error_angstrom=max(e['endpoint_error_angstrom'] for e in endpoints))
            observed.append(record)
    if any(p.read_bytes() != data for p,data in frozen.items()):
        raise ValueError('Original CIF or saved packet changed during connection transport')
    unresolved = sum(r['status']=='UNRESOLVED' for r in observed)
    report = dict(schema_version=1, kind='topostitch-original-cif-connection-transport',
        status='OBSERVED_REVIEW_REQUIRED', original_model_sha256=paths['original_model_sha256'],
        preview_receipt_sha256=paths['preview_receipt_sha256'],
        source_context_sha256=paths['source_context_sha256'], path_projection_sha256=paths['report_sha256'],
        image_owner_sha256=expected_image_owner_sha256, image_owner_api='resolve_deposition_image',
        gemmi_version=gemmi.__version__, connection_category_present='_struct_conn.' in block.get_mmcif_category_names(),
        source_row_count=len(rows), transported_row_count=len(rows)-unresolved,
        unresolved_row_count=unresolved, duplicate_connection_ids=duplicates,
        operation_table_issues=issues, connections=observed, all_original_rows_retained=True,
        original_document_retained_by_source_binding=True, coordinates_written=False,
        chemical_connectivity_validated=False, complete_construct_connectivity_validated=False,
        runtime_authority=False, scientific_acceptance=False,
        limitations=['Read-only endpoint/image transport, not a CIF writer or chain/entity assignment',
            'Raw field values retain CIF null/unknown distinctions; exact lexical document remains in source binding',
            'Unresolved/third-partner rows remain visible; no inferred missing bonds or automatic deletion',
            'Physical endpoint invariance does not establish chemical, sequence, density or restraint validity'])
    report['report_sha256'] = _fingerprint(report)
    return report
