"""Read-only recut fragments with original and explicitly declared oligo lineage.

The saved ASU registration is not silently promoted to a synthesized-oligo map.
This module composes existing registration, source coverage and graph owners.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from .construct_registration import validate_construct_registration
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


def _oligo_relation(a,b):
    if a is None or b is None:return 'UNASSIGNED'
    if a['identity_relation']!='SAME' or b['identity_relation']!='SAME':return 'TARGET_IDENTITY_CONFLICT'
    if (a['copy_id'],a['strand_id'])!=(b['copy_id'],b['strand_id']):
        return 'DIFFERENT_DECLARED_COPY_OR_STRAND'
    if b['target_strand_position']==a['target_strand_position']+1:
        return 'ADJACENT_IN_DECLARED_SEQUENCE'
    return 'NONADJACENT_OR_REPEAT_PHASE_REVIEW'


def observe_relabel_cif_fragments(directory, model, *, oligo_registration_path=None,
        expected_oligo_registration_sha256=None, **polymer_binding):
    """Compose original sites, saved paths and an optional explicit oligo mapping.

    The optional file is the existing construct-registration schema, bound to the
    same working-model bytes. Its logical target/copy assignments remain caller
    declarations, not proof of physical copy placement or repeat/nick phase.
    Unmapped target positions are not relabelled as unmodeled source residues.
    No output CIF labels, entities, coordinates or new graph edges are written.
    """
    import gemmi
    from .topostitch_recut_bundle import _FILES

    root=Path(directory);model=Path(model);manifest=root/'preview.json'
    if (oligo_registration_path is None)!=(expected_oligo_registration_sha256 is None):
        raise ValueError('Explicit oligo registration requires both path and exact SHA-256')
    frozen={p:p.read_bytes() for p in [model,manifest,*(root/n for n in _FILES.values())]}
    oligos={};oligo_summary=None
    if oligo_registration_path is not None:
        path=Path(oligo_registration_path);data=path.read_bytes();frozen[path]=data
        if (not isinstance(expected_oligo_registration_sha256,str)
                or re.fullmatch(r'[0-9a-f]{64}',expected_oligo_registration_sha256) is None
                or sha256(data).hexdigest()!=expected_oligo_registration_sha256):
            raise ValueError('Explicit oligo registration checksum mismatch')
        oligos,oligo_summary=_declared_oligos(data,frozen[root/_FILES['source']])
    coverage=observe_relabel_cif_polymer(root,model,**polymer_binding)
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
                declared_mapping=assignment,oligo_assignment=None)
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
            if missing or conflicts or adjacency_review else 'DECLARED_REGISTRATION_ONLY')
    if any(p.read_bytes()!=data for p,data in frozen.items()):
        raise ValueError('Original source, preview or oligo registration changed during fragment observation')
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
        explicit_target_document_verified=False,physical_copy_placement_validated=False,physical_nick_inferred=False,
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
