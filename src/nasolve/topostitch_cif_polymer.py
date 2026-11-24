"""Original polymer declarations and observed-site coverage for a saved recut.

This is a read-only relational inventory, not a new sequence, chemical entity,
terminus assignment or CIF writer. Cedar supplies its separate sequence audit.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .topostitch_cif_annotations import _known, _rows, _deposition_owner
from .topostitch_registration import _fingerprint

CATEGORIES = ('_entity.', '_entity_poly.', '_struct_asym.',
              '_entity_poly_seq.', '_pdbx_poly_seq_scheme.')


def _position(value):
    if not _known(value):
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    return number if number > 0 else None


def _coverage(tables, atoms, registered):
    """Join supplied declarations without filling absent identities or rows."""
    issues = []

    def issue(category, reason, **context):
        item = dict(category=category, reason=reason, **context)
        if item not in issues:
            issues.append(item)

    def unique(category, key):
        grouped = {}
        for i,row in enumerate(tables[category], 1):
            value = row.get(key)
            if not _known(value):
                issue(category, 'Missing identifier', source_row=i); continue
            grouped.setdefault(value, []).append(row)
        for value, rows in grouped.items():
            if len(rows) != 1:
                issue(category, 'Duplicate identifier', identifier=value)
        # Conflicting/duplicated rows stay in original_tables, never last-wins.
        return {key:rows[0] for key,rows in grouped.items() if len(rows)==1}

    entities = unique('_entity.', 'id')
    polymers = unique('_entity_poly.', 'entity_id')
    asym = unique('_struct_asym.', 'id')
    for eid, row in polymers.items():
        if entities.get(eid, {}).get('type') != 'polymer':
            issue('_entity_poly.', 'Polymer declaration lacks one matching polymer entity', entity_id=eid)
        if not _known(row.get('type')):
            issue('_entity_poly.', 'Missing polymer type', entity_id=eid)
    for eid, row in entities.items():
        if row.get('type') == 'polymer' and eid not in polymers:
            issue('_entity.', 'Polymer entity lacks one polymer declaration', entity_id=eid)
    for aid, row in asym.items():
        if row.get('entity_id') not in entities:
            issue('_struct_asym.', 'Asymmetric-unit element lacks one entity', asym_id=aid)

    def sequence(category, owner, number):
        grouped = {}; seen = set()
        for i,row in enumerate(tables[category], 1):
            eid = row.get(owner); pos = _position(row.get(number)); comp = row.get('mon_id')
            if not _known(eid) or pos is None or not _known(comp):
                issue(category, 'Incomplete sequence position or monomer', source_row=i); continue
            key = (eid,pos,comp)
            if key in seen:
                issue(category, 'Duplicate monomer at one sequence position', identifier=list(key))
            seen.add(key); grouped.setdefault((eid,pos), []).append(row)
            if category == '_entity_poly_seq.' and eid not in polymers:
                issue(category, 'Sequence row lacks one polymer entity', entity_id=eid)
            if category == '_pdbx_poly_seq_scheme.':
                if (eid not in asym or row.get('entity_id') != asym[eid].get('entity_id')
                        or row.get('entity_id') not in polymers):
                    issue(category, 'Scheme row lacks matching asym/polymer entity', source_row=i)
        return grouped

    sequence_rows = sequence('_entity_poly_seq.', 'entity_id', 'num')
    scheme_rows = sequence('_pdbx_poly_seq_scheme.', 'asym_id', 'seq_id')
    for eid in polymers:
        positions = sorted(pos for entity,pos in sequence_rows if entity==eid)
        previous = 0; gaps = []
        for pos in positions:
            if pos > previous+1: gaps.append([previous+1,pos-1])
            previous = pos
        if gaps:
            issue('_entity_poly_seq.', 'Noncontiguous declared sequence numbering', entity_id=eid, missing_ranges=gaps)
    by_atom = {atom_id:site for site in registered for atom_id in site['original_atom_ids']}
    polymer_ids = []; other_ids = []; unresolved = []; observed = {}
    for atom in atoms:
        aid, eid = atom.get('label_asym_id'), atom.get('label_entity_id')
        reason = None; entity = entities.get(eid, {}); kind = entity.get('type')
        if aid not in asym or eid not in entities or asym[aid].get('entity_id') != eid:
            reason = 'Atom lacks matching unique asym/entity identifiers'
        elif kind == 'polymer':
            if eid not in polymers or not _known(polymers[eid].get('type')):
                reason = 'Atom lacks a complete polymer declaration'
            elif _position(atom.get('label_seq_id')) is None or not _known(atom.get('label_comp_id')):
                reason = 'Polymer atom lacks a sequence position or component'
        elif kind not in ('non-polymer', 'water', 'branched') or eid in polymers:
            reason = 'Unclassified or contradictory entity type'
        elif atom['id'] in by_atom:
            reason = 'Registered backbone site is declared nonpolymeric'
        if reason:
            unresolved.append(dict(original_atom_id=atom['id'], reason=reason,
                label_asym_id=aid, label_entity_id=eid, label_seq_id=atom.get('label_seq_id')))
            continue
        if kind != 'polymer':
            other_ids.append(atom['id']); continue
        polymer_ids.append(atom['id']); pos = _position(atom['label_seq_id'])
        key = (aid,eid,pos)
        if key not in observed:
            observed[key] = dict(label_asym_id=aid, label_entity_id=eid, label_seq_id=pos,
                original_components=[], original_atom_ids=[], original_author_sites=[],
                registered_node_ids=[], proposed_path_positions=[])
        site = observed[key]
        site['original_atom_ids'].append(atom['id'])
        for field, value in (('original_components',atom['label_comp_id']),
            ('original_author_sites',{k:atom.get(k) for k in ('auth_asym_id','auth_seq_id','auth_comp_id','pdbx_PDB_ins_code')})):
            if value not in site[field]: site[field].append(value)
        if atom['id'] in by_atom:
            bound = by_atom[atom['id']]
            if bound['node_id'] not in site['registered_node_ids']:
                site['registered_node_ids'].append(bound['node_id'])
                site['proposed_path_positions'].append(bound['proposed_path_position'])

    for (aid,eid,pos), site in sorted(observed.items()):
        expected = {row['mon_id'] for row in sequence_rows.get((eid,pos), [])}
        mapped = {row['mon_id'] for row in scheme_rows.get((aid,pos), []) if row.get('entity_id')==eid}
        site['original_components'].sort()
        if not set(site['original_components']) <= expected:
            issue('_entity_poly_seq.', 'Observed monomer not covered by declared position', asym_id=aid, entity_id=eid, seq_id=pos)
        if not set(site['original_components']) <= mapped:
            issue('_pdbx_poly_seq_scheme.', 'Observed monomer not covered by matching scheme', asym_id=aid, entity_id=eid, seq_id=pos)

    raw_positions = {}
    for atom in atoms:
        aid, pos = atom.get('label_asym_id'), _position(atom.get('label_seq_id'))
        if _known(aid) and pos is not None:
            raw_positions.setdefault((aid,pos), []).append(atom['id'])
    def uncertain_at(aid, eid, pos):
        for row in unresolved:
            chain, entity = row['label_asym_id'], row['label_entity_id']
            number = _position(row['label_seq_id'])
            if _known(chain):
                if chain != aid: continue
            else:
                # A uniquely declared water/nonpolymer cannot occupy a DNA
                # position merely because its own asym identifier is missing.
                declaration = entities.get(entity, {})
                kind = declaration.get('type')
                if (kind in ('water','non-polymer','branched') and entity not in polymers
                        and row['original_atom_id'] not in by_atom):
                    continue
                if kind=='polymer' and entity in polymers and entity != eid:
                    continue
            if number is not None and number != pos: continue
            return True
        return False

    declared = []; attached_entities = set()
    for aid, asym_row in sorted(asym.items()):
        eid = asym_row.get('entity_id')
        if eid not in polymers: continue
        attached_entities.add(eid)
        positions = sorted(pos for entity,pos in sequence_rows if entity==eid)
        if not positions:
            issue('_entity_poly_seq.', 'Polymer asym element has no declared sequence', asym_id=aid, entity_id=eid)
        for pos in positions:
            seq = sequence_rows[eid,pos]; schemes = scheme_rows.get((aid,pos), [])
            expected = sorted({row['mon_id'] for row in seq})
            mapped = {row['mon_id'] for row in schemes if row.get('entity_id')==eid}
            if set(expected) != mapped:
                issue('_pdbx_poly_seq_scheme.', 'Declared position and scheme monomers differ', asym_id=aid, entity_id=eid, seq_id=pos)
            site = observed.get((aid,eid,pos), {})
            raw_ids = raw_positions.get((aid,pos), [])
            uncertain_locator = uncertain_at(aid, eid, pos)
            state = ('UNRESOLVED' if set(raw_ids)!=set(site.get('original_atom_ids', []))
                     or not raw_ids and uncertain_locator else 'OBSERVED' if raw_ids else 'UNMODELED')
            declared.append(dict(label_asym_id=aid, label_entity_id=eid, label_seq_id=pos,
                declared_components=expected, sequence_rows=seq, scheme_rows=schemes,
                original_atom_ids=raw_ids,
                observed_components=site.get('original_components', []),
                registered_node_ids=site.get('registered_node_ids', []),
                proposed_path_positions=site.get('proposed_path_positions', []),
                coordinate_status=state))
    for (aid,pos), rows in scheme_rows.items():
        eid = asym.get(aid, {}).get('entity_id')
        if (eid,pos) not in sequence_rows:
            issue('_pdbx_poly_seq_scheme.', 'Scheme position lacks a declared sequence position', asym_id=aid, seq_id=pos)
    unattached = sorted(set(polymers)-attached_entities)
    for eid in unattached:
        issue('_struct_asym.', 'Polymer entity has no unique asym element', entity_id=eid)
    if unresolved:
        issue('_atom_site.', 'Some original atoms have unresolved source entity/site coverage', atom_count=len(unresolved))
    partition = polymer_ids+other_ids+[row['original_atom_id'] for row in unresolved]
    if len(partition)!=len(set(partition)) or set(partition)!={row['id'] for row in atoms}:
        raise ValueError('Original atom coverage is not a complete disjoint partition')
    return dict(issues=issues, observed_polymer_sites=list(observed.values()), declared_positions=declared,
        unmodeled_positions=[row for row in declared if row['coordinate_status']=='UNMODELED'],
        polymer_entities_without_asym_ids=unattached, original_atom_count=len(atoms),
        polymer_atom_count=len(polymer_ids), nonpolymer_atom_ids=other_ids, unresolved_atoms=unresolved,
        unregistered_polymer_atom_ids=[atom_id for atom_id in polymer_ids if atom_id not in by_atom],
        all_atoms_accounted_once=True,
        all_observed_polymer_atoms_registered=not unresolved and bool(polymer_ids) and all(atom_id in by_atom for atom_id in polymer_ids))


def observe_relabel_cif_polymer(directory, model, *, expected_deposition_owner_sha256,
                               cedar_source=None, **source_binding):
    """Observe original declared polymer coverage, including absent coordinates.

    W257 source controls are unchanged. Raw original tables, author identifiers,
    nonstandard linkage flags and component alternatives are retained. No entity
    or sequence is synthesized from the new paths. Cedar's separately pinned
    public reader supplies sequence evidence; its overall geometry status never
    substitutes for metadata coverage. Unknown tables or conflicts need review.
    """
    import gemmi
    from .topostitch_cif_source import observe_relabel_cif_paths
    from .topostitch_recut_bundle import _FILES

    root = Path(directory); model = Path(model); manifest = root/'preview.json'
    frozen = {p:p.read_bytes() for p in [manifest, *(root/n for n in _FILES.values()), model]}
    paths = observe_relabel_cif_paths(root, model, **source_binding)
    if (sha256(frozen[model]).hexdigest()!=paths['original_model_sha256']
            or sha256(frozen[manifest]).hexdigest()!=paths['preview_receipt_sha256']):
        raise ValueError('Original source changed before polymer coverage')
    doc = gemmi.cif.read_string(frozen[model].decode('ascii'))
    block = next(b for b in doc if '_atom_site.' in b.get_mmcif_category_names())
    tables = {category:_rows(block,category) for category in CATEGORIES}
    missing = [category for category,rows in tables.items() if not rows]
    inventory = _coverage(tables, _rows(block,'_atom_site.'), paths['registered_original_sites'])
    with _deposition_owner(cedar_source, expected_deposition_owner_sha256) as owner:
        inspect = getattr(owner, 'inspect_deposition_links', None)
        if not callable(inspect):
            raise ValueError('Selected Cedar owner lacks inspect_deposition_links')
        try:
            evidence = inspect(model)['model']
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            semantic = dict(status='UNAVAILABLE', reason='Cedar sequence inspection could not complete', error_type=type(exc).__name__)
        else:
            if evidence.get('sha256') != paths['original_model_sha256']:
                raise ValueError('Cedar sequence inspection differs from bound original source')
            checked = evidence.get('sequence_tables_checked'); conflicts = evidence.get('sequence_conflicts')
            unlabelled = evidence.get('unlabelled_polymer_atom_rows')
            if (not isinstance(checked,list) or not isinstance(conflicts,list)
                    or type(unlabelled) is not int or unlabelled < 0):
                raise ValueError('Cedar sequence observation has incompatible fields')
            semantic = dict(status='OBSERVED', source_inspection_status=evidence.get('status'),
                sequence_tables_checked=checked, sequence_conflicts=conflicts,
                unlabelled_polymer_atom_rows=unlabelled)
    semantic_clear = (semantic['status']=='OBSERVED' and not semantic['sequence_conflicts']
        and semantic['unlabelled_polymer_atom_rows']==0
        and set(semantic['sequence_tables_checked'])=={'_entity_poly_seq.','_pdbx_poly_seq_scheme.'})
    status = 'UNAVAILABLE' if missing else ('CONSISTENT_DECLARATIONS' if not inventory['issues'] and semantic_clear else 'REVIEW_REQUIRED')
    if any(p.read_bytes()!=data for p,data in frozen.items()):
        raise ValueError('Original CIF or saved packet changed during polymer coverage')
    report = dict(schema_version=1, kind='topostitch-original-cif-polymer-coverage',
        status='OBSERVED_REVIEW_REQUIRED', metadata_coverage_status=status,
        original_model_sha256=paths['original_model_sha256'], preview_receipt_sha256=paths['preview_receipt_sha256'],
        source_context_sha256=paths['source_context_sha256'], path_projection_sha256=paths['report_sha256'],
        deposition_owner_sha256=expected_deposition_owner_sha256, deposition_owner_api='inspect_deposition_links',
        gemmi_version=gemmi.__version__, original_tables=tables, missing_tables=missing,
        cedar_sequence_evidence=semantic, **inventory,
        original_document_retained_by_source_binding=True, coordinates_written=False,
        author_numbering_semantics_validated=False, canonical_sequence_text_validated=False,
        source_semantics_approved=False, chemical_entities_assigned=False,
        runtime_authority=False, scientific_acceptance=False,
        limitations=['Original declarations and observed-site coverage only, not chemical sequence truth or topology acceptance',
            'Unknown/missing tables and unregistered polymers remain explicit; absent coordinates are not newly built',
            'Author numbering and one-letter sequence text are preserved, not inferred or rewritten',
            'No output chain/entity names, new sequence, termini, annotation, restraint or coordinate file'])
    report['report_sha256'] = _fingerprint(report)
    return report
