"""Read-only recut fragments with original and explicitly declared oligo lineage.

The saved ASU registration is not silently promoted to a synthesized-oligo map.
This module composes existing registration, source coverage and graph owners.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from .construct_registration import build_construct_registration, validate_construct_registration
from .topostitch_cif_annotations import _rows
from .topostitch_cif_polymer import observe_relabel_cif_polymer
from .topostitch_cif_source import _declared_paths
from .topostitch_inspect import _unique_object
from .topostitch_registration import _coordinate_site, _fingerprint


def _declared_oligos(data, source_bytes):
    """Reuse the existing registration contract; verify its observed identities."""
    from .topostitch_coordinates import _read_atoms
    registration = validate_construct_registration(json.loads(data, object_pairs_hook=_unique_object))
    if registration['model']['sha256'] != sha256(source_bytes).hexdigest():
        raise ValueError('Oligo registration is not bound to the saved working model')
    reference = registration['target']['reference']
    if (not isinstance(reference,dict) or not isinstance(reference.get('content_sha256'),str)
            or re.fullmatch(r'[0-9a-f]{64}',reference['content_sha256']) is None):
        raise ValueError('Explicit oligo registration needs a target content reference')
    atoms = _read_atoms(source_bytes)
    positions = {}; counts = {}
    for site in registration['target']['sites']:
        strand = site.split(':',1)[0];counts[strand]=counts.get(strand,0)+1
        positions[site]=(strand,counts[strand])
    mappings = {}
    for copy in registration['copies']:
        for row in copy['mappings']:
            coordinate = row['coordinate_site']
            groups = atoms.get(_coordinate_site(coordinate))
            if (groups is None or len(groups)!=1
                    or {atom[1] for atom in next(iter(groups.values()))}!={row['coordinate_residue_code']}):
                raise ValueError('Oligo registration differs from actual working-coordinate identity')
            strand,position = positions[row['logical_site']]
            mappings[coordinate]=dict(**row,copy_id=copy['copy_id'],copy_status=copy['status'],
                strand_id=strand,target_strand_position=position)
    summary=dict(registration_sha256=sha256(data).hexdigest(),target=registration['target'],
        source=registration['source'],copies=[dict(copy_id=c['copy_id'],status=c['status'],
            mapped_site_count=c['mapped_site_count'],target_site_count=c['target_site_count'])
            for c in registration['copies']],
        unmapped_logical_sites_by_copy={c['copy_id']:c['missing_logical_sites'] for c in registration['copies']},
        declaration_only=True,target_reference_content_loaded=False,physical_copy_placement_validated=False)
    return mappings,summary


def _bind_target_document(data, registration_data, source, coverage, aliases):
    """Rebuild the existing contract from actual target and coordinate evidence.

    Source CIF polymer membership supplies modified-residue roles; the supplied
    registration cannot classify arbitrary HETATMs as polymer by itself.
    """
    from .model_assessment import inspect_pdb

    target = json.loads(data, object_pairs_hook=_unique_object)
    registration = validate_construct_registration(
        json.loads(registration_data, object_pairs_hook=_unique_object))
    polymer_codes = {
        aliases.get(code, code)
        for site in coverage['observed_polymer_sites']
        for code in site['original_components']
    }
    assessment = inspect_pdb(source, polymer_ligand_codes=polymer_codes)
    copies = {
        copy['copy_id']: {row['logical_site']: row['coordinate_site']
                         for row in copy['mappings']}
        for copy in registration['copies']
    }
    rebuilt = build_construct_registration(
        assessment, target, copies, source=registration['source'])
    if rebuilt != registration:
        raise ValueError('Target document does not reproduce the supplied oligo registration')
    return [{'site': row['site'], 'residue_code': row['residue_code']}
            for row in target['sites']]


def _oligo_relation(a,b):
    if a is None or b is None:return 'UNASSIGNED'
    if a['identity_relation']!='SAME' or b['identity_relation']!='SAME':return 'TARGET_IDENTITY_CONFLICT'
    if (a['copy_id'],a['strand_id'])!=(b['copy_id'],b['strand_id']):
        return 'DIFFERENT_DECLARED_COPY_OR_STRAND'
    if b['target_strand_position']==a['target_strand_position']+1:
        return 'ADJACENT_IN_DECLARED_SEQUENCE'
    return 'NONADJACENT_OR_REPEAT_PHASE_REVIEW'


def observe_relabel_cif_fragments(directory, model, *, oligo_registration_path=None,
        expected_oligo_registration_sha256=None, oligo_target_path=None,
        expected_oligo_target_sha256=None, **polymer_binding):
    """Compose original sites, saved paths and an optional explicit oligo mapping.

    The optional file is the existing construct-registration schema, bound to the
    same working-model bytes. Its logical target/copy assignments remain caller
    declarations, not proof of physical copy placement or repeat/nick phase.
    Unmapped target positions are not relabelled as unmodeled source residues.
    An optional SHA-bound sequence-family-target document must exactly rebuild
    the supplied registration through its existing public owner. This binds
    declared sequence and copy mapping; it does not verify the referenced source
    file or independently establish the physical oligo/copy/nick placement.
    No output CIF labels, entities, coordinates or new graph edges are written.
    """
    import gemmi
    from .topostitch_recut_bundle import _FILES

    root=Path(directory);model=Path(model);manifest=root/'preview.json'
    if (oligo_registration_path is None)!=(expected_oligo_registration_sha256 is None):
        raise ValueError('Explicit oligo registration requires both path and exact SHA-256')
    if (oligo_target_path is None)!=(expected_oligo_target_sha256 is None):
        raise ValueError('Explicit oligo target requires both path and exact SHA-256')
    if oligo_target_path is not None and oligo_registration_path is None:
        raise ValueError('Explicit oligo target requires a supplied registration')
    frozen={p:p.read_bytes() for p in [model,manifest,*(root/n for n in _FILES.values())]}
    oligos={};oligo_summary=None
    if oligo_registration_path is not None:
        path=Path(oligo_registration_path);data=path.read_bytes();frozen[path]=data
        if (not isinstance(expected_oligo_registration_sha256,str)
                or re.fullmatch(r'[0-9a-f]{64}',expected_oligo_registration_sha256) is None
                or sha256(data).hexdigest()!=expected_oligo_registration_sha256):
            raise ValueError('Explicit oligo registration checksum mismatch')
        oligos,oligo_summary=_declared_oligos(data,frozen[root/_FILES['source']])
    target_data = None
    if oligo_target_path is not None:
        target_path = Path(oligo_target_path)
        target_data = target_path.read_bytes()
        frozen[target_path] = target_data
        if (not isinstance(expected_oligo_target_sha256, str)
                or re.fullmatch(r'[0-9a-f]{64}', expected_oligo_target_sha256) is None
                or sha256(target_data).hexdigest() != expected_oligo_target_sha256):
            raise ValueError('Explicit oligo target checksum mismatch')
    coverage=observe_relabel_cif_polymer(root,model,**polymer_binding)
    if target_data is not None:
        target_sites = _bind_target_document(
            target_data, frozen[Path(oligo_registration_path)], root/_FILES['source'],
            coverage, polymer_binding.get('component_aliases', {}))
        oligo_summary.update(target_document_sha256=sha256(target_data).hexdigest(),
            target_document_sites=target_sites, target_document_verified=True,
            target_document_status='LOADED_REGISTRATION_MATCH',
            target_reference_status='NOT_LOADED')

    if (sha256(frozen[model]).hexdigest()!=coverage['original_model_sha256']
            or sha256(frozen[manifest]).hexdigest()!=coverage['preview_receipt_sha256']):
        raise ValueError('Source or saved preview changed before fragment observation')
    preview=json.loads(frozen[manifest],object_pairs_hook=_unique_object)['observation']
    bound=preview['registered_graph'];graph=preview['graph_relabeling']['periodic_graph']
    registration=validate_construct_registration(json.loads(frozen[root/_FILES['registration']],object_pairs_hook=_unique_object))
    source_target_reused=(oligo_summary is not None and
        oligo_summary['target']['reference']==registration['target']['reference'])
    if oligo_summary is not None:
        oligo_summary['source_target_reference_reused']=source_target_reused
    nodes={n['node_id']:n for n in bound['nodes']}
    paths,boundaries=_declared_paths(nodes,graph['edges'])
    doc=gemmi.cif.read_string(frozen[model].decode('ascii'))
    block=next(b for b in doc if '_atom_site.' in b.get_mmcif_category_names())
    atoms={a['id']:a for a in _rows(block,'_atom_site.')}
    original={n:s for s in coverage['observed_polymer_sites'] for n in s['registered_node_ids']}
    if set(original)!=set(nodes):
        raise ValueError('Original polymer coverage does not account for every registered node')
    images={r['node_id']:r['image']['operator_xyz'] for r in preview['graph_relabeling']['proposed_node_images']}
    field_names=('label_asym_id','label_entity_id','label_seq_id','label_comp_id')
    projected={};used_coordinates=set();fragments=[]
    for path in paths:
        sites=[]
        for position,number in enumerate(path['node_ids'],1):
            node=nodes[number];site=original[number];ids=site['original_atom_ids']
            labels={tuple(atoms[atom_id][k]for k in field_names)for atom_id in ids}
            if len(labels)!=1 or number in projected:
                raise ValueError('Fragment projection requires unique complete original sites')
            coordinate=node['mapping']['coordinate_site'];assignment=oligos.get(coordinate)
            if assignment is not None:used_coordinates.add(coordinate)
            row=dict(node_id=number,path_position=position,original_label=dict(zip(field_names,next(iter(labels)))),
                original_atom_ids=ids,original_author_sites=site['original_author_sites'],
                registered_copy_id=node['copy_id'],registered_logical_site=node['logical_site'],
                registered_coordinate_site=coordinate,declared_route_id=node['strand_id'],
                representative_operator_xyz=images.get(number,'x,y,z'),
                declared_protected=node['protected'],declared_do_not_connect=node['do_not_connect'],
                declared_mapping=assignment,oligo_assignment=(assignment
                    if target_data is not None and not source_target_reused else None))
            sites.append(row);projected[number]=dict(path_number=path['path_number'],**row)
        fragments.append(dict(path_number=path['path_number'],sites=sites,
            ordinary_edge_ids=path['ordinary_edge_ids'],output_chain_id=None,output_entity_id=None))
    before={e['edge_id']:e for e in bound['periodic_graph']['edges'] if e['kind']=='covalent_backbone'}
    after={e['edge_id']:e for e in graph['edges'] if e['kind']=='covalent_backbone'}
    if set(before)!=set(after):raise ValueError('Recut changed the declared backbone edge inventory')
    origins={r['edge_id']:r['origin']for r in bound['edge_origins']}
    boundary_ids={e['edge_id']for e in boundaries};edges=[]
    for number,e in sorted(after.items()):
        a,b=projected[e['source']],projected[e['target']]
        x,y=a['original_label'],b['original_label']
        same_asym=x['label_asym_id']==y['label_asym_id']
        same_entity=x['label_entity_id']==y['label_entity_id']
        successor=same_asym and same_entity and int(y['label_seq_id'])==int(x['label_seq_id'])+1
        edges.append(dict(edge_id=number,source_node_id=e['source'],target_node_id=e['target'],
            source_path_number=a['path_number'],target_path_number=b['path_number'],
            original_target_operator_xyz=before[number]['target_operator_xyz'],
            representative_target_operator_xyz=e['target_operator_xyz'],
            declared_origin=origins[number],representation_boundary=number in boundary_ids,
            crosses_original_asym=not same_asym,crosses_original_entity=not same_entity,
            original_sequence_successor=successor,
            oligo_relation=_oligo_relation(a['declared_mapping'],b['declared_mapping'])))
    missing=[n for n,s in projected.items()if s['declared_mapping'] is None]
    conflicts=[n for n,s in projected.items()if s['declared_mapping'] is not None
               and s['declared_mapping']['identity_relation']!='SAME']
    adjacency_review=[e['edge_id']for e in edges if e['oligo_relation'] not in ('UNASSIGNED','ADJACENT_IN_DECLARED_SEQUENCE')]
    status=('SOURCE_LINEAGE_ONLY' if oligo_summary is None else 'SOURCE_TARGET_REUSED'
            if source_target_reused else 'DECLARED_MAPPING_REVIEW_REQUIRED'
            if missing or conflicts or adjacency_review else 'TARGET_DOCUMENT_BOUND'
            if target_data is not None else 'DECLARED_REGISTRATION_ONLY')
    if any(p.read_bytes()!=data for p,data in frozen.items()):
        raise ValueError('Original source, preview or oligo declaration changed during fragment observation')
    report=dict(schema_version=1,kind='topostitch-original-cif-fragment-lineage',status='OBSERVED_REVIEW_REQUIRED',
        oligo_mapping_status=status,original_model_sha256=coverage['original_model_sha256'],
        preview_receipt_sha256=coverage['preview_receipt_sha256'],polymer_coverage_sha256=coverage['report_sha256'],
        metadata_coverage_status=coverage['metadata_coverage_status'],
        registered_graph_sha256=bound['report_sha256'],source_registration_sha256=bound['registration_file_sha256'],
        source_registration_target=registration['target'],source_registration_copy_id=bound['copy_id'],
        oligo_registration=oligo_summary,fragments=fragments,backbone_edges=edges,
        declared_routes=bound['declared_routes'],declared_continuations=bound.get('declared_continuations',[]),
        registered_site_count=len(nodes),original_atom_count=coverage['original_atom_count'],
        source_positions_without_fragment=[s for s in coverage['declared_positions']if not s['registered_node_ids']],
        unregistered_polymer_atom_ids=coverage['unregistered_polymer_atom_ids'],
        unresolved_source_atoms=coverage['unresolved_atoms'],nonpolymer_atom_ids=coverage['nonpolymer_atom_ids'],
        oligo_mappings_without_fragment=[r for coordinate,r in oligos.items()if coordinate not in used_coordinates],
        registered_nodes_without_declared_mapping=missing,target_identity_conflicts=conflicts,
        sequence_adjacency_review_edge_ids=adjacency_review,
        all_registered_nodes_projected_once=True,all_declared_backbone_edges_retained=True,
        explicit_target_document_verified=target_data is not None,physical_copy_placement_validated=False,physical_nick_inferred=False,
        assembly_transformed=False,tls_transformed=False,coordinates_written=False,
        chemical_entities_assigned=False,writer_authorized=False,runtime_authority=False,scientific_acceptance=False,
        limitations=['Saved ASU registration is not automatically a full synthesized-oligo declaration',
            'Optional oligo target/copy mapping is caller-declared; physical copy/repeat phase remains unproved',
            'Target reference digest is retained; its external content is not loaded by this observer',
            'Existing one-coordinate-per-logical-assignment contract is unchanged; symmetry occurrence expansion is not supplied',
            'Unmapped logical targets are distinct from source positions without coordinates',
            'Target adjacency is descriptive; wrapped/nonadjacent mappings cannot locate a physical nick',
            'No output labels/entities, assembly/TLS transformation, chemistry change or model writer'])
    report['report_sha256']=_fingerprint(report)
    return report


def _reference_integer(value):
    if isinstance(value, str) and re.fullmatch(r'-?[0-9]+', value):
        return int(value)
    return None


def _project_reference_range(row, tables, lineage, alignment_counts):
    """Project source entity positions only; database alignment is not inferred."""
    issues = []
    align_id = row.get('align_id')
    references = [r for r in tables['_struct_ref.'] if r.get('id') == row.get('ref_id')]
    if not isinstance(align_id, str) or not align_id or alignment_counts[align_id] != 1:
        issues.append('Missing or ambiguous alignment identifier')
    if not isinstance(row.get('ref_id'), str) or len(references) != 1:
        issues.append('Missing or ambiguous reference identifier')
    reference = references[0] if len(references) == 1 else {}
    entity = reference.get('entity_id')
    start, end = (_reference_integer(row.get(k)) for k in ('seq_align_beg','seq_align_end'))
    if start is None or end is None or start < 1 or end < start:
        issues.append('Unsupported or reversed entity sequence range')
    strand = row.get('pdbx_strand_id')
    scheme = tables['_pdbx_poly_seq_scheme.']
    candidates = sorted({r['asym_id'] for r in scheme
        if isinstance(entity, str) and r.get('entity_id') == entity
        and isinstance(strand, str) and r.get('pdb_strand_id') == strand
        and isinstance(r.get('asym_id'), str)})
    if len(candidates) != 1:
        issues.append('Missing or ambiguous source strand-to-asym mapping')
    asym = candidates[0] if len(candidates) == 1 else None
    positions = []; segments = []
    author_issues = []
    if lineage['metadata_coverage_status'] != 'CONSISTENT_DECLARATIONS':
        issues.append('Original polymer declarations require review')
    if asym is not None and start is not None and end is not None and 0 < start <= end:
        declared = sorted({_reference_integer(r.get('num')) for r in tables['_entity_poly_seq.']
            if r.get('entity_id') == entity and _reference_integer(r.get('num')) is not None
            and start <= _reference_integer(r.get('num')) <= end})
        if len(declared) != end-start+1:
            issues.append('Range endpoints or intervening entity positions are undeclared')
        projected = {(s['original_label']['label_asym_id'],int(s['original_label']['label_seq_id'])):
            (fragment['path_number'],s) for fragment in lineage['fragments'] for s in fragment['sites']}
        outside = {(s['label_asym_id'],s['label_seq_id']):s
            for s in lineage['source_positions_without_fragment']}
        authors = []
        for number in declared:
            location = projected.get((asym,number))
            absent = outside.get((asym,number),{})
            state = 'OBSERVED' if location else absent.get('coordinate_status','UNRESOLVED')
            rows = [r for r in scheme if r.get('asym_id') == asym and r.get('entity_id') == entity
                    and _reference_integer(r.get('seq_id')) == number]
            author_keys = ('pdb_strand_id','auth_seq_num','pdb_seq_num','pdb_ins_code')
            identities = {tuple(r.get(k) for k in author_keys) for r in rows}
            author = dict(zip(author_keys,next(iter(identities)))) if len(identities) == 1 else None
            if author is None:
                author_issues.append('Ambiguous or absent author scheme at entity position '+str(number))
            if location is None:
                issues.append('Range position has no fragment assignment: '+str(number)+' ('+state+')')
            else:
                raw_authors = location[1]['original_author_sites']
                if (author is None or len(raw_authors) != 1
                        or raw_authors[0].get('auth_asym_id') != author['pdb_strand_id']
                        or raw_authors[0].get('auth_seq_id') != author['auth_seq_num']
                        or (raw_authors[0].get('pdbx_PDB_ins_code') is not None
                            and raw_authors[0]['pdbx_PDB_ins_code'] != author['pdb_ins_code'])):
                    author_issues.append('Author scheme conflicts with original atoms at position '+str(number))
            if author is not None:
                numeric = _reference_integer(author['auth_seq_num'])
                if (numeric is None or author['pdb_seq_num'] != author['auth_seq_num']
                        or author['pdb_ins_code'] is not False):
                    author_issues.append('Author numbering/insertion is outside the uninserted numeric scope at '+str(number))
                authors.append(numeric)
            positions.append(dict(source_seq_id=number,coordinate_status=state,
                original_author_scheme_rows=rows,
                original_author_sites=location[1]['original_author_sites'] if location else [],
                node_id=location[1]['node_id'] if location else None,
                fragment_position=dict(path_number=location[0],position=location[1]['path_position']) if location else None))
        if len(authors) == len(declared) and all(n is not None for n in authors):
            if any(b != a+1 for a,b in zip(authors,authors[1:])):
                author_issues.append('Author numbering is reversed, gapped or non-monotonic')
        for number, label in ((start,'beg'),(end,'end')):
            matching = [p for p in positions if p['source_seq_id'] == number]
            if not matching or len(matching[0]['original_author_sites']) != 1:
                author_issues.append('Original author endpoint unavailable: '+label)
                continue
            original = matching[0]['original_author_sites'][0]
            if row.get('pdbx_auth_seq_align_'+label) != original.get('auth_seq_id'):
                author_issues.append('Author alignment endpoint differs from original atoms: '+label)
            insertion = row.get('pdbx_seq_align_'+label+'_ins_code')
            # An optional '?' does not assert blank; observed scheme/atoms above
            # must independently establish a known uninserted endpoint. An atom
            # '?' can be resolved by the explicit scheme; it is never rewritten.
            endpoint_schemes = matching[0]['original_author_scheme_rows']
            if insertion is not None and (not endpoint_schemes or any(
                    s.get('pdb_ins_code') != insertion for s in endpoint_schemes)):
                author_issues.append('Author alignment insertion endpoint differs: '+label)
        for position in sorted((p for p in positions if p['fragment_position'] is not None),
                               key=lambda p:(p['fragment_position']['path_number'],p['fragment_position']['position'])):
            loc = position['fragment_position']
            if (segments and segments[-1]['path_number'] == loc['path_number']
                    and segments[-1]['positions'][-1]['fragment_position']['position']+1 == loc['position']
                    and segments[-1]['positions'][-1]['source_seq_id']+1 == position['source_seq_id']):
                segments[-1]['positions'].append(position)
            else:
                segments.append(dict(path_number=loc['path_number'],positions=[position],
                    original_align_id=align_id,original_ref_id=row.get('ref_id'),
                    original_entity_id=entity,original_asym_id=asym,
                    output_chain_id=None,output_entity_id=None,output_db_align_beg=None,output_db_align_end=None))
    else:
        author_issues.append('Author range cannot be qualified without unique source entity/strand bounds')
    issues.extend(author_issues)
    discrepancies = [r for r in tables['_struct_ref_seq_dif.'] if r.get('align_id') == align_id]
    return dict(raw_fields=row,source_reference_rows=references,source_entity_id=entity,source_asym_id=asym,
        status='REVIEW_REQUIRED' if issues else 'SOURCE_RANGE_PROJECTED',issues=issues,
        author_range_status='REVIEW_REQUIRED' if author_issues else 'CONSISTENT_UNINSERTED_FORWARD_RANGE',
        positions=positions,segments=segments,discrepancy_rows=discrepancies,
        database_correspondence_status='ENDPOINT_DECLARATION_ONLY',
        output_fields_requiring_mapping=['New chain/entity and alignment identifiers',
            'Database endpoints for each fragment; equal span lengths do not prove gapless alignment',
            'Sequence-discrepancy and depositor-reference relabeling'])


def observe_relabel_cif_reference_ranges(directory, model, **fragment_binding):
    """Observe original sequence-reference ranges across saved recut fragments.

    Supported membership uses entity_poly_seq positions and a unique declared
    PDB-strand/asym mapping. Author numbering is checked separately in the narrow
    forward, numeric, uninserted scope. Ambiguity never removes the raw row.
    This is not a database alignment engine or a deposition writer.
    """
    from collections import Counter
    import gemmi

    model = Path(model)
    data = model.read_bytes()
    lineage = observe_relabel_cif_fragments(directory, model, **fragment_binding)
    if model.read_bytes() != data or sha256(data).hexdigest() != lineage['original_model_sha256']:
        raise ValueError('Original CIF changed during sequence-reference observation')
    doc = gemmi.cif.read_string(data.decode('ascii'))
    block = next(b for b in doc if '_atom_site.' in b.get_mmcif_category_names())
    categories = ('_struct_ref.','_struct_ref_seq.','_struct_ref_seq_dif.',
        '_pdbx_struct_ref_seq_depositor_info.','_pdbx_seq_map_depositor_info.',
        '_pdbx_poly_seq_scheme.','_entity_poly_seq.')
    tables = {category:_rows(block,category) for category in categories}
    counts = Counter(row.get('align_id') for row in tables['_struct_ref_seq.'])
    alignments = [_project_reference_range(row,tables,lineage,counts) for row in tables['_struct_ref_seq.']]
    orphan = [dict(raw_fields=row,reason='Missing or ambiguous alignment identifier')
              for row in tables['_struct_ref_seq_dif.']
              if not isinstance(row.get('align_id'),str) or counts[row.get('align_id')] != 1]
    report = dict(schema_version=1,kind='topostitch-original-cif-reference-ranges',
        status='UNAVAILABLE' if not alignments else 'OBSERVED_REVIEW_REQUIRED',
        original_model_sha256=lineage['original_model_sha256'],fragment_lineage_sha256=lineage['report_sha256'],
        original_tables=tables,alignments=alignments,unresolved_discrepancy_rows=orphan,
        unprojected_reference_tables={category:tables[category] for category in categories[3:5]},
        source_range_projected_count=sum(r['status']=='SOURCE_RANGE_PROJECTED' for r in alignments),
        source_range_review_count=sum(r['status']=='REVIEW_REQUIRED' for r in alignments),
        database_positions_inferred=False,output_alignment_rows_written=False,writer_authorized=False,
        runtime_authority=False,
        chemical_entities_assigned=False,coordinates_written=False,scientific_acceptance=False,
        limitations=['Source range membership only; new output sequence/reference identifiers are unset',
            'Database endpoints and equal range lengths do not establish per-residue correspondence',
            'Unknown, inserted, reversed or conflicting author numbering requires explicit review',
            'Discrepancy/depositor rows retained without inventing new references or dropping link slots',
            'No chemistry, assembly/TLS, coordinate or native changes'])
    if model.read_bytes() != data:
        raise ValueError('Original CIF changed during sequence-reference observation')
    report['report_sha256'] = _fingerprint(report)
    return report
