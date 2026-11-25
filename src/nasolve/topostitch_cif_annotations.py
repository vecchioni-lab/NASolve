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



def prepare_connection_annotation_proposal(model, *, expected_model_sha256,
        changes, evidence, expected_image_owner_sha256, cedar_source=None):
    """Return an unapplied, source-bound review of explicit connection edits.

    Each change names one existing connection ID, its canonical original-row
    digest, proposed fields, and evidence IDs for each field. Evidence maps IDs
    to explicit ``path``/``sha256`` pairs. Only contact type (covale/hydrog) and
    the two partner image codes may be proposed. Unknown untouched rows survive.

    This does not require or repair entity metadata, resolve endpoints, infer
    chemical intent, or read meaning from evidence contents. File hashes bind
    evidence bytes, not their scientific validity. The original operation table
    and an explicitly pinned Cedar decoder must validate proposed image codes.
    Return values contain hashes, not host paths; replay requires the caller's
    original inputs. No CIF writer, approval, checkpoint or native job is invoked.
    """
    import gemmi

    def digest(value):
        return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None

    model=Path(model)
    data=model.read_bytes()
    if not digest(expected_model_sha256) or sha256(data).hexdigest()!=expected_model_sha256:
        raise ValueError('Annotation proposal source differs from requested binding')
    doc=gemmi.cif.read_string(data.decode('ascii'))
    blocks=[b for b in doc if '_atom_site.' in b.get_mmcif_category_names()]
    if len(blocks)!=1:
        raise ValueError('Annotation proposal requires one original coordinate block')
    block=blocks[0]; rows=_rows(block,'_struct_conn.')
    by_id={}
    for number,row in enumerate(rows,1):
        key=row.get('id')
        if not _known(key):raise ValueError('Missing original connection ID')
        if key in by_id:raise ValueError('Duplicate original connection ID: '+key)
        by_id[key]=(number,row)
    operations,issues=_operations(block,gemmi)
    if issues:raise ValueError('Unresolved original operation table: '+'; '.join(issues))
    if not isinstance(changes,list) or not changes:
        raise ValueError('Require nonempty explicit annotation changes')
    try:
        changes=json.loads(json.dumps(changes,allow_nan=False))
    except (TypeError,ValueError) as exc:
        raise ValueError('Annotation changes must be finite JSON values') from exc
    if not isinstance(evidence,dict) or not evidence:
        raise ValueError('Require explicitly pinned annotation evidence')
    snapshots={model:data}; documents={}
    for key,reference in evidence.items():
        if not isinstance(key,str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',key) is None:
            raise ValueError('Invalid annotation evidence ID')
        if not isinstance(reference,dict) or set(reference)!={'path','sha256'} or not digest(reference['sha256']):
            raise ValueError('Require explicit evidence path and SHA-256')
        path=Path(reference['path']); raw=path.read_bytes()
        if sha256(raw).hexdigest()!=reference['sha256']:
            raise ValueError('Annotation evidence differs from requested binding: '+key)
        if path in snapshots and snapshots[path]!=raw:
            raise ValueError('Annotation source or evidence changed during snapshot')
        snapshots[path]=raw
        documents[key]=dict(sha256=reference['sha256'],size_bytes=len(raw))
    permitted={'conn_type_id','ptnr1_symmetry','ptnr2_symmetry'}
    proposed={};used=set();added=set()
    columns=list(block.get_mmcif_category('_struct_conn.'))
    with _image_owner(cedar_source,expected_image_owner_sha256) as decode:
        for change in changes:
            if not isinstance(change,dict) or set(change)!={'connection_id','expected_row_sha256','fields','evidence'}:
                raise ValueError('Unsupported annotation change fields')
            key=change['connection_id']
            if not isinstance(key,str) or key not in by_id:
                raise ValueError('Unknown original connection ID')
            if key in proposed:raise ValueError('Duplicate proposed connection ID: '+key)
            number,row=by_id[key]
            if not digest(change['expected_row_sha256']) or _fingerprint(row)!=change['expected_row_sha256']:
                raise ValueError('Original connection row differs from requested binding: '+key)
            fields=change['fields'];support=change['evidence']
            if not isinstance(fields,dict) or not fields or set(fields)-permitted:
                raise ValueError('Unsupported annotation field; identities and other metadata are immutable')
            if not isinstance(support,dict) or set(support)!=set(fields):
                raise ValueError('Every proposed field needs its own evidence IDs')
            details={};new=dict(row)
            for field,value in sorted(fields.items()):
                ids=support[field]
                if (not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in documents for i in ids)
                        or len(set(ids))!=len(ids)):
                    raise ValueError('Missing, duplicate or unknown annotation evidence ID')
                if not _known(value):raise ValueError('Proposed annotation field must be an explicit string')
                if field in row and row[field]==value:
                    raise ValueError('Proposed annotation field is unchanged: '+field)
                item=dict(original_present=field in row,original_value=row.get(field),
                    proposed_value=value,evidence_ids=list(ids))
                if field=='conn_type_id':
                    if value not in ('covale','hydrog'):
                        raise ValueError('Unsupported proposed connection type')
                else:
                    op=decode(value,operations)
                    if op is None:raise ValueError('Proposed image code is unresolved: '+value)
                    item['operator_xyz']=op.triplet()
                used.update(ids);new[field]=value;details[field]=item
                if field not in columns:added.add(field)
            proposed[key]=dict(source_row_number=number,original_row_sha256=_fingerprint(row),
                original_fields=dict(row),proposed_fields=new,field_changes=details)
    if used!=set(documents):raise ValueError('Unused annotation evidence would overstate proposal scope')
    if any(path.read_bytes()!=raw for path,raw in snapshots.items()):
        raise ValueError('Annotation source or evidence changed before proposal return')
    connections=[proposed.get(row['id'],dict(source_row_number=number,
        original_row_sha256=_fingerprint(row),original_fields=dict(row),
        proposed_fields=dict(row),field_changes={})) for number,row in enumerate(rows,1)]
    result=dict(schema_version=1,kind='topostitch-connection-annotation-proposal',
        original_model_sha256=expected_model_sha256,coordinate_block=block.name,
        original_connection_category_sha256=_fingerprint(rows),source_columns=columns,
        source_row_count=len(rows),proposed_row_count=len(proposed),
        proposed_added_columns=sorted(added),image_owner_sha256=expected_image_owner_sha256,
        evidence=documents,connections=connections,source_and_evidence_hashes_verified=True,
        applied=False,coordinates_written=False,evidence_semantics_validated=False,
        endpoint_identity_validated=False,chemical_semantics_validated=False,
        native_restart_qualified=False,runtime_authority=False,scientific_acceptance=False,
        limitations=['Explicit proposal only; hash-bound evidence is not independent semantic approval',
            'Original rows and unknown metadata retained; no sequence/entity/identity repair',
            'Image-code decoding does not verify physical endpoint identity or chemical meaning',
            'Only covale/hydrog type and two partner image fields; no CIF application or portable replay packet'])
    result['report_sha256']=_fingerprint(result)
    return result


def load_connection_annotation_proposal(proposal, model, *, expected_proposal_sha256,
        expected_model_sha256, changes, evidence, expected_image_owner_sha256,
        cedar_source=None):
    """Reproduce a saved review against independently supplied original inputs.

    The trusted proposal digest binds raw file bytes, not its self-reported
    fingerprint. Reuse the proposal builder and compare canonical typed JSON;
    a rehashed edit, even false replaced by zero, cannot become approval. Paths,
    change requests and evidence bindings are never adopted from the report.
    This is read-only replay, not application or a portable packet loader.
    """
    from .topostitch_preview import _json
    path = Path(proposal); raw = path.read_bytes()
    if (not isinstance(expected_proposal_sha256, str)
            or re.fullmatch(r'[0-9a-f]{64}', expected_proposal_sha256) is None
            or sha256(raw).hexdigest() != expected_proposal_sha256):
        raise ValueError('Annotation proposal differs from requested file binding')
    saved = _json(raw)
    # Existing canonical serialization rejects nonfinite JSON and distinguishes
    # booleans from integers; Python object equality alone cannot do the latter.
    saved_digest = _fingerprint(saved)
    rebuilt = prepare_connection_annotation_proposal(model,
        expected_model_sha256=expected_model_sha256, changes=changes, evidence=evidence,
        expected_image_owner_sha256=expected_image_owner_sha256, cedar_source=cedar_source)
    if saved_digest != _fingerprint(rebuilt):
        raise ValueError('Annotation proposal does not reproduce from its explicit sources')
    if path.read_bytes() != raw:
        raise ValueError('Annotation proposal changed during replay')
    return saved
