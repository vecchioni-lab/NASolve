"""Prepare an explicit whole-original-asym CIF draft without writing a file.

This is a specialist, source-bound output boundary, not an automatic CIF
converter. Every coordinate-block category requires a caller-reviewed raw-row
digest. That declaration is retained evidence, not independent semantic approval.
Native restart, chemical interpretation and deposition acceptance remain separate.
"""
from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path

from .topostitch_cif_annotations import _rows, _operations, _image_owner
from .topostitch_cif_source import load_relabel_cif_source
from .topostitch_cif_tls import observe_relabel_cif_tls
from .topostitch_cif_assembly import observe_relabel_cif_assemblies
from .topostitch_registration import _fingerprint
from .topostitch_transport import IDENTITY_IMAGE

_SOURCE_KEYS = ('expected_receipt_sha256', 'expected_model_sha256', 'component_aliases',
    'max_coordinate_component_error_angstrom', 'max_u_component_error_angstrom_squared',
    'max_b_error_angstrom_squared', 'max_occupancy_error')
_BOUNDS = ('max_rotation_component_error', 'max_translation_component_error_angstrom',
           'max_assembly_position_error_angstrom')
_SYMMETRIC = ((1,1),(2,2),(3,3),(1,2),(1,3),(2,3))


def _number(value):
    if not math.isfinite(value):
        raise ValueError('Nonfinite whole-asym output value')
    return format(value, '.17g')


def _put(block, category, rows):
    """Edit existing scalar/loop items; grow one category without duplicating it."""
    import gemmi
    columns = list(block.get_mmcif_category(category))
    if not columns or any(set(row) != set(columns) for row in rows):
        raise ValueError('Whole-asym draft cannot invent or omit category columns')
    table = block.find_mmcif_category(category)
    if len(table) == len(rows):
        for target, row in zip(table, rows):
            for i, key in enumerate(columns):
                value = row[key]
                target[i] = '?' if value is None else '.' if value is False else gemmi.cif.quote(value)
    else:
        table.erase()
        block.set_mmcif_category(category, {key:[row[key]for row in rows] for key in columns})


def _encode(operation, operations, decode):
    """Use original operation IDs and qualify the code through Cedar's decoder."""
    import gemmi
    op = gemmi.Op(operation); matches = []
    for key, base in operations.items():
        if op.rot != base.rot:
            continue
        delta = [a-b for a,b in zip(op.tran,base.tran)]
        if any(v % op.DEN for v in delta):
            continue
        digits = [v//op.DEN+5 for v in delta]
        if all(0<=v<=9 for v in digits):
            code = key+'_'+''.join(str(v)for v in digits)
            if decode(code,operations) == op:
                matches.append(code)
    if len(matches) != 1:
        raise ValueError('Output symmetry code has no unique source-table encoding')
    return matches[0]


def _assembly_edits(block, report, atoms):
    """Reuse qualified H G^-1 partitions, preserving namespace and multiplicity."""
    import gemmi
    from .topostitch_graph import _compose, _inverse
    identity = gemmi.Op('x,y,z'); changed = []; lineage = []
    all_asym = {r['id']for r in _rows(block,'_struct_asym.')}
    for namespace, evidence in report['namespaces'].items():
        generators = evidence['generators']
        if not generators:
            if evidence['operators'] or evidence['assemblies']:
                raise ValueError('Assembly tables lack supported generator coverage')
            continue
        if any(r['status']=='UNRESOLVED_REVIEW'for r in generators) or any(
                r['status']=='UNRESOLVED_REVIEW'for r in evidence['operators']):
            raise ValueError('Unresolved assembly references cannot be exported')
        if any(r['status']=='UNRESOLVED_REVIEW'for r in evidence['support_references']):
            raise ValueError('Unresolved assembly support reference')
        operators = [dict(r['raw_fields'])for r in evidence['operators']]
        by_id = {r['raw_fields']['id']:r for r in evidence['operators']}
        used = {r['id']for r in operators}; derived = {}; output = []
        row_ids = {g['raw_fields'].get('id')for g in generators if 'id'in g['raw_fields']}
        if row_ids and (any(not isinstance(v,str)or not v.strip()for v in row_ids)or len(row_ids)!=len(generators)):
            raise ValueError('Assembly generator IDs must be complete and unique')
        for source in generators:
            original = source['raw_fields']; partitions = {}
            old_exact=by_id[original['oper_expression']]['symmetry_matches'][0]['operator_xyz']
            if original.get('symmetry_operation')not in(None,False):
                try: agrees=gemmi.Op(original['symmetry_operation']).triplet()==old_exact
                except (TypeError,RuntimeError): agrees=False
                if not agrees:raise ValueError('Conflicting original generator symmetry metadata')
            for field,expected in (
                    ('at_unit_matrix','Y'if old_exact=='x,y,z'else'N'),
                    ('all_chains','Y'if set(source['original_label_asym_ids'])==all_asym else'N')):
                if original.get(field)not in(None,False,expected):
                    raise ValueError('Conflicting original generator flag: '+field)
            if original.get('chain_id_list')not in(None,False):
                supplied=original['chain_id_list']
                authors={a['auth_asym_id']for a in atoms if a['label_asym_id']in source['original_label_asym_ids']}
                if not isinstance(supplied,str)or set(v.strip()for v in supplied.split(','))!=authors:
                    raise ValueError('Conflicting original generator author-chain metadata')
            for p in source['partitions']:
                partitions.setdefault(p['representative_image_xyz'],[]).append(p)
            first_partition = True
            for operation, parts in partitions.items():
                chains = sorted({p['original_label_asym_id']for p in parts})
                exemplar = parts[0]
                if any(p['proposed_cartesian_rotation']!=exemplar['proposed_cartesian_rotation'] or
                       p['proposed_cartesian_translation_angstrom']!=exemplar['proposed_cartesian_translation_angstrom']for p in parts):
                    raise ValueError('Inconsistent whole-asym assembly partition')
                key = (original['oper_expression'], operation)
                old = by_id[key[0]]
                exact = _compose(gemmi.Op(old['symmetry_matches'][0]['operator_xyz']),
                                 _inverse(gemmi.Op(operation),identity)).triplet()
                if operation == 'x,y,z':
                    operator_id = key[0]
                elif key in derived:
                    operator_id = derived[key]
                else:
                    count = 1
                    while 'nst_'+str(count) in used: count += 1
                    operator_id = 'nst_'+str(count); used.add(operator_id); derived[key] = operator_id
                    row = dict(old['raw_fields']); row['id'] = operator_id
                    if 'name'in row: row['name'] = operator_id
                    if 'type'in row: row['type'] = 'identity operation' if exact=='x,y,z' else 'crystal symmetry operation'
                    if 'symmetry_operation'in row and row['symmetry_operation']not in(None,False):row['symmetry_operation']=exact
                    for i in range(3):
                        row[f'vector[{i+1}]'] = _number(exemplar['proposed_cartesian_translation_angstrom'][i])
                        for j in range(3): row[f'matrix[{i+1}][{j+1}]'] = _number(exemplar['proposed_cartesian_rotation'][i][j])
                    operators.append(row)
                row = dict(original);row['oper_expression']=operator_id;row['asym_id_list']=','.join(chains)
                if 'id'in row and not first_partition:
                    count=1
                    while 'nst_gen_'+str(count)in row_ids:count+=1
                    row['id']='nst_gen_'+str(count);row_ids.add(row['id'])
                if row.get('full_matrices')not in(None,False):
                    row['full_matrices']='\n'.join(' '.join(_number(v)for v in [*r,t])for r,t in zip(exemplar['proposed_cartesian_rotation'],exemplar['proposed_cartesian_translation_angstrom']))
                if row.get('symmetry_operation')not in(None,False):row['symmetry_operation']=exact
                if row.get('at_unit_matrix')not in(None,False):row['at_unit_matrix']='Y'if exact=='x,y,z'else'N'
                if row.get('all_chains')not in(None,False):row['all_chains']='Y'if set(chains)==all_asym else'N'
                if row.get('chain_id_list')not in(None,False):
                    names=[]
                    for chain in chains:
                        authors={a['auth_asym_id']for a in atoms if a['label_asym_id']==chain}
                        if len(authors)!=1:raise ValueError('Assembly author-chain membership is ambiguous')
                        names.append(next(iter(authors)))
                    row['chain_id_list']=','.join(sorted(set(names)))
                if any(row.get(k)not in(None,False)for k in ('helical_rotation','helical_rise')):
                    raise ValueError('Helical assembly metadata needs a separate output policy')
                output.append(row)
                lineage.append(dict(namespace=namespace,source_row_number=source['source_row_number'],
                    output_row_number=len(output),source_generator_id=original.get('id'),
                    output_generator_id=row.get('id'),source_operator_id=original['oper_expression'],
                    output_operator_id=operator_id,representative_image_xyz=operation,
                    original_label_asym_ids=chains))
                first_partition = False
        for category,rows in ((evidence['operator_category'],operators),(evidence['generator_category'],output)):
            if rows!=_rows(block,category):_put(block,category,rows);changed.append(category)
    return changed,lineage


def prepare_whole_asym_cif(directory, model, *, reviewed_categories, tls_policy,
                           center_policy, **binding):
    """Return (ASCII CIF bytes, receipt) for an explicitly reviewed original CIF.

    Bind every coordinate-block category by its canonical raw-row fingerprint,
    including metadata retained unchanged. The caller must review that retention
    policy; matching hashes do not approve unknown semantics. Uncertainty and
    additional coordinate fields, mixed asym/TLS images and unresolved assembly
    or connection references are refused. No output file/default is changed.
    Only original connection rows are carried; missing graph annotations are not
    invented. This draft is not a native restart or complete deposition export.
    """
    import gemmi
    from .topostitch_recut_bundle import _FILES
    from .topostitch_cif_annotations import observe_relabel_cif_connections
    if tls_policy!='preserve_raw_no_restart' or center_policy!='unit_occupancy_present_polymer_mass':
        raise ValueError('Require explicit supported TLS and polymer-center policies')
    root=Path(directory);model=Path(model)
    frozen={p:p.read_bytes()for p in [model,root/'preview.json',*(root/n for n in _FILES.values())]}
    allowed=set(_SOURCE_KEYS+_BOUNDS+('cedar_source','expected_deposition_owner_sha256'))
    if set(binding)-allowed:raise ValueError('Unsupported whole-asym source binding option')
    source_kw={k:binding[k]for k in _SOURCE_KEYS}
    source=load_relabel_cif_source(root,model,**source_kw)
    doc=gemmi.cif.read_string(source.document_bytes.decode('ascii'))
    block=doc[source.observation['coordinate_block']]
    original={c:_rows(block,c)for c in block.get_mmcif_category_names()}
    if not isinstance(reviewed_categories,dict) or reviewed_categories!={c:_fingerprint(r)for c,r in original.items()}:
        raise ValueError('Require exact complete source-bound category review')
    reviewed_categories=dict(reviewed_categories)
    atoms=original['_atom_site.'];images={}
    for row,image in zip(atoms,source.frame.images):
        chain=row.get('label_asym_id')
        if not isinstance(chain,str)or not chain:raise ValueError('Missing original asym identity')
        if chain in images and images[chain]!=image:raise ValueError('Require one image per whole original asym')
        images[chain]=image
    for category in ('_atom_site.','_atom_site_anisotrop.','_pdbx_refine_tls.'):
        for row in original.get(category,[]):
            for key,value in row.items():
                if value not in(None,False) and ('esd'in key or 'covar'in key or key.startswith(('fract_','B['))):
                    raise ValueError('Additional coordinate/uncertainty field is unsupported: '+category+key)
    fragment_kw={k:v for k,v in binding.items()if k not in _BOUNDS}
    tls=observe_relabel_cif_tls(root,model,**fragment_kw)
    if tls['orphan_group_rows'] or any(g['status']!='UNIFORM_IMAGE_TRANSPORT_OBSERVED'for g in tls['groups']):
        raise ValueError('Require complete uniform TLS membership for output')
    assembly=observe_relabel_cif_assemblies(root,model,**binding)
    connections=observe_relabel_cif_connections(root,model,expected_image_owner_sha256=binding['expected_deposition_owner_sha256'],
                       cedar_source=binding.get('cedar_source'),**source_kw)
    if connections['unresolved_row_count'] or connections['operation_table_issues']:
        raise ValueError('Unresolved connection references cannot be exported')
    if any(p.read_bytes()!=b for p,b in frozen.items())or frozen[model]!=source.document_bytes:
        raise ValueError('Source changed during whole-asym draft preparation')
    changed=[];new_atoms=[dict(a)for a in atoms];new_points=[]
    for row,xyz,image in zip(new_atoms,source.positions_angstrom,source.frame.images):
        point=xyz if image==IDENTITY_IMAGE else image.apply(xyz);new_points.append(point)
        if image!=IDENTITY_IMAGE:
            for axis,v in zip('xyz',point):row['Cartn_'+axis]=_number(v)
    _put(block,'_atom_site.',new_atoms);changed.append('_atom_site.')
    by_id={a['id']:i for i,a in enumerate(atoms)}
    if '_atom_site_anisotrop.'in original:
        rows=[dict(a)for a in original['_atom_site_anisotrop.']]
        for row in rows:
            i=by_id[row['id']];image=source.frame.images[i]
            if image!=IDENTITY_IMAGE:
                values=image.rotate_tensor(source.u_cart_angstrom_squared[i])
                for (a,b),v in zip(_SYMMETRIC,values):row[f'U[{a}][{b}]']=_number(v)
        _put(block,'_atom_site_anisotrop.',rows);changed.append('_atom_site_anisotrop.')
    if connections['connections']:
        operations,issues=_operations(block,gemmi);assert not issues
        rows=[]
        with _image_owner(binding.get('cedar_source'),binding['expected_deposition_owner_sha256'])as decode:
            for c in connections['connections']:
                row=dict(c['raw_fields'])
                for e in c['endpoints']:row[f"ptnr{e['partner']}_symmetry"]=_encode(e['representative_operator_xyz'],operations,decode)
                rows.append(row)
        _put(block,'_struct_conn.',rows);changed.append('_struct_conn.')
    if tls['groups']:
        rows=[]
        for g in tls['groups']:
            row=dict(g['original_parameter_row']);p=g['transported_parameters']
            if g['operator_xyz']!='x,y,z':
                for axis,v in zip('xyz',p['origin_angstrom']):row['origin_'+axis]=_number(v)
                for prefix,key in [('T','T_angstrom_squared'),('L','L_degrees_squared')]:
                    for (i,j),v in zip(_SYMMETRIC,p[key]):row[f'{prefix}[{i}][{j}]']=_number(v)
                for i in range(3):
                    for j in range(3):row[f'S[{i+1}][{j+1}]']=_number(p['S_angstrom_degrees'][3*i+j])
            rows.append(row)
        _put(block,'_pdbx_refine_tls.',rows);changed.append('_pdbx_refine_tls.')
    center=None
    if '_struct.'in original:
        rows=[dict(r)for r in original['_struct.']];keys=['pdbx_center_of_mass_'+a for a in 'xyz']
        if any(r.get(k)not in(None,False)for r in rows for k in keys):
            polymers={r['entity_id']for r in original.get('_entity_poly.',[])}
            if len(rows)!=1 or any(rows[0].get(k)in(None,False)for k in keys)or any(
                    a.get('label_entity_id')not in polymers or float(a['occupancy'])!=1. for a in atoms):
                raise ValueError('Supplied polymer center has unsupported membership/occupancy convention')
            weights=[gemmi.Element(a['type_symbol']).weight for a in atoms]
            def centroid(points):return [math.fsum(p[i]*w for p,w in zip(points,weights))/math.fsum(weights)for i in range(3)]
            before=centroid(source.positions_angstrom);after=centroid(new_points)
            if max(abs(float(rows[0][k])-v)for k,v in zip(keys,before))>5.01e-7:
                raise ValueError('Supplied polymer center does not match the declared mass convention')
            if any(image!=IDENTITY_IMAGE for image in source.frame.images):
                for k,v in zip(keys,after):rows[0][k]=_number(v)
                _put(block,'_struct.',rows);changed.append('_struct.')
            center=dict(source_recomputed=before,representative_recomputed=after,definition=center_policy)
    assembly_changed,assembly_lineage=_assembly_edits(block,assembly,atoms)
    changed.extend(assembly_changed)
    changed=[c for c in original if _rows(block,c)!=original[c]]
    expected=[{c:_rows(b,c)for c in b.get_mmcif_category_names()}for b in doc]
    data=doc.as_string().encode('ascii');check=gemmi.cif.read_string(data.decode('ascii'))
    if [{c:_rows(b,c)for c in b.get_mmcif_category_names()}for b in check]!=expected:
        raise ValueError('Whole-asym category readback differs from proposed rows')
    if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('Source changed before whole-asym draft return')
    report=dict(schema_version=1,kind='topostitch-whole-asym-cif-draft',
        original_model_sha256=binding['expected_model_sha256'],preview_receipt_sha256=binding['expected_receipt_sha256'],
        source_binding_sha256=source.observation['report_sha256'],output_sha256=sha256(data).hexdigest(),
        reviewed_categories=dict(reviewed_categories),changed_categories=sorted(set(changed)),
        category_readback_exact=True,atom_count=len(atoms),original_asym_ids=sorted(images),
        center_of_mass=center,tls_policy=tls_policy,tls_observation_sha256=tls['report_sha256'],
        assembly_observation_sha256=assembly['report_sha256'],assembly_generator_lineage=assembly_lineage,
        connection_observation_sha256=connections['report_sha256'],
        deposited_adps_transported=True,
        deposited_u_reexpressed_count=sum(u is not None and g!=IDENTITY_IMAGE for u,g in zip(source.u_cart_angstrom_squared,source.frame.images)),
        tls_added_to_deposited_adps=False,source_labels_changed=False,
        native_restart_qualified=False,all_declared_graph_links_written=False,file_written=False,
        retention_semantics_independently_approved=False,scientific_acceptance=False,runtime_authority=False,
        limitations=['Caller-reviewed metadata retention is not independent semantic approval',
            'Existing CIF connections only; absent graph annotations are not invented',
            'Raw TLS transport is not native S33 convention or restart qualification',
            'No mixed-asym/TLS images, uncertainty covariance transport, native readback or deposition approval'])
    report['report_sha256']=_fingerprint(report)
    return data,report



def _backbone_coverage(graph, site_labels, evidence):
    """Match a declared graph to public Cedar rows, without inferring a bond."""
    def label(value):
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise ValueError('Cedar endpoint evidence lacks four label fields')
        if any(not isinstance(v, str) for v in value):
            raise ValueError('Cedar endpoint evidence has unsupported label fields')
        return tuple(value)

    node_by_label = {value: node for node, value in site_labels.items()}
    if len(node_by_label) != len(site_labels):
        raise ValueError('Ambiguous original site labels in backbone coverage')
    ordinary = evidence.get('ordinary', {}).get('steps')
    declared = evidence.get('declared')
    if not isinstance(ordinary, list) or not isinstance(declared, list):
        raise ValueError('Require public Cedar per-step ordinary and declared evidence')
    node_by_position = {(v[0], int(v[1])): n for n, v in site_labels.items()}
    if len(node_by_position) != len(site_labels):
        raise ValueError('Ambiguous registered sequence positions')
    model = evidence['_coverage_model']
    rows = []
    for kind, records in (('ordinary', ordinary), ('explicit', declared)):
        for number, record in enumerate(records, 1):
            left, right = label(record['O3_label']), label(record['P_label'])
            operation = record.get('operator_on_P')
            if operation is not None and not isinstance(operation, str):
                raise ValueError('Unsupported Cedar endpoint image evidence')
            if kind == 'ordinary':
                status = record.get('status')
                expected_op = None if status == 'SEQUENCE_GAP' else 'x,y,z'
                if record.get('model') != model or operation != expected_op:
                    raise ValueError('Ordinary step model/image differs from supported contract')
                if status not in {'MEASURED', 'LONG', 'PARTIAL_ANGLES', 'SEQUENCE_GAP',
                                  'UNMEASURED', 'ALTERNATE_LABEL_REVIEW'}:
                    raise ValueError('Unsupported Cedar ordinary step status')
                observations = [record]
                eligible = status in {'MEASURED', 'LONG', 'PARTIAL_ANGLES'}
                represents_link = status != 'SEQUENCE_GAP'
            else:
                observations = record.get('observations')
                if not isinstance(observations, list):
                    raise ValueError('Missing explicit-link observations')
                eligible = True
                represents_link = True
            measured = [o for o in observations if o.get('model') == model
                        and isinstance(o.get('distance_A'), (int, float))
                        and not isinstance(o['distance_A'], bool)
                        and math.isfinite(o['distance_A']) and o['distance_A'] >= 0]
            a, b = node_by_label.get(left), node_by_label.get(right)
            if kind == 'ordinary':
                # Position associates a missing endpoint with its declared site;
                # it never supplies a component/alternate label or measurement.
                if left is None:
                    a = node_by_position.get((record.get('label_asym_id'), record.get('from_label_seq_id')))
                if right is None:
                    b = node_by_position.get((record.get('label_asym_id'), record.get('to_label_seq_id')))
            rows.append(dict(kind=kind, row_number=number, connection_id=record.get('id'),
                source_node_id=a, target_node_id=b,
                operator_xyz=operation, measurable=eligible and len(measured) == 1,
                represents_link=represents_link, evidence=record))
    results = []; matched = set(); keys = set()
    for edge in graph['edges']:
        if edge['kind'] != 'covalent_backbone':
            continue
        key = (edge['source'], edge['target'], edge['target_operator_xyz'])
        if key in keys or any(node not in site_labels for node in key[:2]):
            raise ValueError('Duplicate or unresolved declared backbone edge')
        keys.add(key)
        candidates = [(i, r) for i, r in enumerate(rows)
            if (r['source_node_id'], r['target_node_id']) == key[:2] and r['represents_link']]
        exact = [(i, r) for i, r in candidates if r['operator_xyz'] == key[2]]
        conflicts = [r for _, r in candidates if r['operator_xyz'] != key[2]]
        usable = [r for _, r in exact if r['measurable']]
        counts = {kind: sum(r['kind'] == kind for r in usable) for kind in ('ordinary', 'explicit')}
        status = ('CONFLICTING_IMAGE' if conflicts else 'AMBIGUOUS' if max(counts.values()) > 1
                  else 'UNMEASURED' if any(not r['measurable'] for _, r in exact)
                  else 'COVERED' if usable else 'MISSING')
        matched.update(i for i, _ in exact)
        results.append(dict(edge_id=edge['edge_id'], source_node_id=key[0], target_node_id=key[1],
            target_operator_xyz=key[2], status=status, ordinary_count=counts['ordinary'],
            explicit_count=counts['explicit'], rows=[r for _, r in exact], conflicts=conflicts))
    unexpected = [r for i, r in enumerate(rows) if i not in matched and r['represents_link']
                  and r['source_node_id'] is not None and r['target_node_id'] is not None]
    outside = [r for r in rows if r['source_node_id'] is None or r['target_node_id'] is None]
    gaps = [r for r in rows if not r['represents_link']]
    return dict(edges=results, unexpected_registered_links=unexpected,
        outside_registered_scope=outside, sequence_gaps=gaps,
        complete_declared_backbone_coverage=bool(results) and not unexpected
            and all(r['status'] == 'COVERED' for r in results))


def observe_whole_asym_cif_backbone(directory, model, serialized_model, *,
        expected_output_sha256, expected_deposition_owner_sha256, cedar_source=None,
        **source_binding):
    """Account for a serialized draft's declared links through Cedar's public API.

    Source labels and atom inventory must be retained. Ordinary sequence gaps,
    missing/ambiguous endpoints, extra links across a declared nick and conflicting
    crystal images remain explicit. Coverage is separate from geometry quality,
    physical nick assignment, coordinate/scattering equivalence and acceptance.
    This observer writes nothing and never activates a restraint or output flow.
    """
    import json
    import gemmi
    from .topostitch_cif_source import observe_relabel_cif_paths
    from .topostitch_cif_annotations import _deposition_owner
    from .topostitch_recut_bundle import _FILES

    root = Path(directory); model = Path(model); output = Path(serialized_model)
    frozen = {p: p.read_bytes() for p in [model, output, root/'preview.json',
              *(root/n for n in _FILES.values())]}
    if sha256(frozen[output]).hexdigest() != expected_output_sha256:
        raise ValueError('Serialized CIF differs from the requested output binding')
    paths = observe_relabel_cif_paths(root, model, **source_binding)
    graph = json.loads(frozen[root/'preview.json'])['observation']['graph_relabeling']['periodic_graph']
    def atom_rows(data):
        doc = gemmi.cif.read_string(data.decode('ascii'))
        blocks = [b for b in doc if '_atom_site.' in b.get_mmcif_category_names()]
        if len(blocks) != 1:
            raise ValueError('Require one coordinate block for serialized coverage')
        rows = _rows(blocks[0], '_atom_site.')
        result = {r['id']: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate serialized atom identity')
        return result
    original = atom_rows(frozen[model]); emitted = atom_rows(frozen[output])
    fields = ('group_PDB', 'type_symbol', 'label_atom_id', 'label_alt_id', 'label_comp_id',
        'label_asym_id', 'label_entity_id', 'label_seq_id', 'auth_atom_id', 'auth_comp_id',
        'auth_asym_id', 'auth_seq_id', 'pdbx_PDB_ins_code', 'pdbx_PDB_model_num')
    if original.keys() != emitted.keys() or any(
            original[k].get(f) != emitted[k].get(f) for k in original for f in fields):
        raise ValueError('Serialized atom inventory or source labels changed')
    models = {r.get('pdbx_PDB_model_num') or '1' for r in emitted.values()}
    if len(models) != 1:
        raise ValueError('Require one unambiguous coordinate model for coverage')
    site_labels = {}
    for row in paths['registered_original_sites']:
        label = row['original_label']
        alts = {emitted[k].get('label_alt_id') or '' for k in row['original_atom_ids']}
        if alts != {''}:
            raise ValueError('Registered alternate labels require a separate coverage policy')
        site_labels[row['node_id']] = (label['label_asym_id'], str(int(label['label_seq_id'])),
                                      label['label_comp_id'], '')
    with _deposition_owner(cedar_source, expected_deposition_owner_sha256) as owner:
        try:
            public = owner.inspect_deposition_links(output, include_ordinary_steps=True)
        except TypeError as exc:
            raise ValueError('Require Cedar public per-step ordinary evidence') from exc
    # The public owner may return tuples; a saved observation must round-trip
    # as exactly the same JSON value, without platform-specific container types.
    public = json.loads(json.dumps(public, allow_nan=False))
    evidence = public['model']
    if evidence.get('sha256') != expected_output_sha256:
        raise ValueError('Cedar observation differs from the bound serialized output')
    coverage = _backbone_coverage(graph, site_labels, {**evidence, '_coverage_model': next(iter(models))})
    if any(p.read_bytes() != data for p, data in frozen.items()):
        raise ValueError('Source or serialized output changed during backbone coverage')
    result = dict(schema_version=1, kind='topostitch-serialized-backbone-coverage',
        status='COMPLETE' if coverage['complete_declared_backbone_coverage'] else 'REVIEW_REQUIRED',
        original_model_sha256=paths['original_model_sha256'], output_sha256=expected_output_sha256,
        preview_receipt_sha256=paths['preview_receipt_sha256'], path_projection_sha256=paths['report_sha256'],
        representative_graph_sha256=graph['graph_sha256'], deposition_owner_sha256=expected_deposition_owner_sha256,
        deposition_owner_api='inspect_deposition_links(include_ordinary_steps=True)',
        original_atom_count=len(original), original_labels_retained=True,
        cedar_observation=public, **coverage,
        coordinates_or_scattering_verified=False, geometry_accepted=False,
        physical_nick_phase_assigned=False, file_written=False, runtime_authority=False,
        scientific_acceptance=False,
        limitations=['Declared links only; no missing bonds, restraints or physical nick inference',
            'Coverage is distinct from geometry quality and coordinate/scattering equivalence',
            'Only retained original labels with one model and no registered alternate labels',
            'Unregistered context and sequence gaps remain explicit, not added to the graph'])
    result['report_sha256'] = _fingerprint(result)
    return result
