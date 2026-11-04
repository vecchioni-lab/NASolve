"""Transactional internal-phosphate context for ordinary Coot construction.

A discarded parent-scaffold shadow lets the existing phosphate sanitizer prove
an internal OP3 deletion. Only that exact deletion and independently authorized
selected-atom serial repairs are transferred to original raw Coot records. Base
coordinates, dictionaries, charge states and native target mechanics stay fixed.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .cif_construction_provenance import _pdb_inventory
from .curated_ligands import CURATED_LIGANDS
from .phosphate import sanitize_phosphates, validate_op3_sites
from .postmr_restoration import canonical_name, restore_graph_site, source_graph_fragment

POLICY_ID = 'postmr-source-graph-internal-phosphate-context-v1'
CURATED_CONTEXT_POLICY_ID = 'postmr-source-graph-curated-phosphate-context-v1'
_COORDINATE = {'ATOM  ', 'HETATM'}
_ASSOCIATED = {'ANISOU', 'SIGATM', 'SIGUIJ'}


def _site(line):
    return (line[21:22].strip() or '_') + ':' + line[22:26].strip() + line[26:27].strip()


def _key(line):
    return (line[21:22].strip() or '_', line[22:26].strip(), line[26:27].strip(),
            line[16:17].strip(), line[12:16].strip())


def _identity(line):
    return {'site': _site(line), 'chain_id': line[21:22].strip() or '_',
            'resseq': line[22:26].strip(), 'icode': line[26:27].strip(),
            'altloc': line[16:17].strip(), 'component': line[17:20].strip(),
            'atom': line[12:16].strip(), 'canonical_atom': canonical_name(line[12:16].strip()),
            'element': line[76:78].strip().upper()}


def _rows(path):
    with Path(path).open(newline='') as handle:
        return handle.read().splitlines(keepends=True)


def _conect(lines):
    result = []
    for line in lines:
        if not line.startswith('CONECT'): continue
        values = [line[i:i+5].strip() for i in range(6,len(line.rstrip()),5)]
        values = [v for v in values if v]
        if len(values) < 2 or any(not v.isdigit() for v in values):
            raise ValueError('Malformed inherited CONECT records')
        result.append([int(v) for v in values])
    return result


def _serial_context(raw_lines, reference_lines, raw_inventory, reference_inventory, selected):
    """Normalize selected serial collisions only through immutable input authority."""
    atoms = [l for l in raw_lines if l[:6] in _COORDINATE]
    serials = [int(l[6:11]) for l in atoms]
    if len(serials) == len(set(serials)):
        return raw_lines, [], {'status': 'NOT_REQUIRED', 'reason': 'Raw atom serials are unique.'}
    reference_atoms = [l for l in reference_lines if l[:6] in _COORDINATE]
    original = {int(l[6:11]): l for l in reference_atoms}
    if len(original) != len(reference_atoms):
        raise ValueError('Serial repair requires unique immutable input atom serials')
    raw_rows, input_rows = _conect(raw_lines),_conect(reference_lines)
    if raw_rows != input_rows:
        raise ValueError('Serial repair requires exactly inherited original CONECT rows')
    unselected = {k: a for k,a in raw_inventory.items() if k[0]+':'+k[1]+k[2] not in selected}
    original_unselected = {k: a for k,a in reference_inventory.items() if k[0]+':'+k[1]+k[2] not in selected}
    if unselected != original_unselected:
        raise ValueError('Serial repair requires unchanged unselected input atoms and coordinates')
    raw_records = {_key(l): l for l in atoms}
    for line in reference_atoms:
        if _site(line) not in selected and raw_records[_key(line)][6:11] != line[6:11]:
            raise ValueError('Serial repair requires unchanged unselected input atom serials')
    endpoints = set(v for row in input_rows for v in row)
    if any(v not in original or _site(original[v]) in selected for v in endpoints):
        raise ValueError('Inherited CONECT endpoints must identify unchanged unselected input atoms')
    fresh = max(serials, default=0)
    repairs = []; replacements = {}
    for line in atoms:
        if _site(line) not in selected: continue
        fresh += 1
        if fresh > 99999: raise ValueError('Selected atom serial repair exceeds PDB field width')
        replacements[line[12:27]] = fresh
        repairs.append({**_identity(line), 'old_serial': int(line[6:11]), 'new_serial': fresh})
    rendered = []
    for line in raw_lines:
        if line[:6] in _COORDINATE | _ASSOCIATED and line[12:27] in replacements:
            line = line[:6]+f'{replacements[line[12:27]]:5d}'+line[11:]
        rendered.append(line)
    all_serials = [int(l[6:11]) for l in rendered if l[:6] in _COORDINATE]
    if len(all_serials) != len(set(all_serials)):
        raise ValueError('Selected serial repair cannot resolve unrelated serial ambiguity')
    return rendered, repairs, {'status': 'ORIGINAL_CONECT_AUTHORITY_PASS',
        'reference_conect_rows': input_rows, 'raw_conect_rows': raw_rows,
        'unchanged_unselected_endpoint_count': len(endpoints),
        'all_endpoints_unselected_and_unchanged': True}


def prepare_construction_context(raw_model, reference_model, actions, dictionary_paths,
                                 parent_models, output_model, *, allow_op3_sites=(),
                                 passthrough_sites=()):
    """Prepare a separate context input or retain the entire immutable raw model.

    Source-graph and proper-transport preflight must succeed before any proposed
    deletion. A failed authority or phosphate proof authorizes no deletion or
    serial change. Explicit curated placements retain their existing final
    coordinate rule. A curated site may join the discarded shadow and proved
    OP3 context only through the same source-graph and proper-transport preflight
    as other sites. Frozen passthrough sites remain excluded. The ordinary final
    model must still pass the same sanitizer.
    """
    raw_model,reference_model,output_model = map(Path,(raw_model,reference_model,output_model))
    allow_op3_sites = validate_op3_sites(allow_op3_sites)
    passthrough_sites = validate_op3_sites(passthrough_sites)
    if set(allow_op3_sites)&set(passthrough_sites):
        raise ValueError('Phosphate and passthrough intent cannot overlap')
    shadow = output_model.with_name(output_model.stem+'_shadow.pdb')
    sanitized = output_model.with_name(output_model.stem+'_shadow_sanitized.pdb')
    for p in (output_model,shadow,sanitized):
        if p.exists() or p.is_symlink(): raise FileExistsError(p)
    inputs = {raw_model,reference_model,*map(Path,dictionary_paths.values()),*map(Path,parent_models.values())}
    if any(p.resolve() in {x.resolve() for x in inputs} for p in (output_model,shadow,sanitized)):
        raise ValueError('Context outputs must be separate from every immutable input')
    snapshots = {p:p.read_bytes() for p in inputs if p.is_file()}
    original = raw_model.read_bytes(); raw_lines = _rows(raw_model)
    report = {'policy_id': POLICY_ID, 'status': 'NO_CONTEXT_CHANGE',
        'raw_model_sha256': sha256(original).hexdigest(),
        'reference_model_sha256': sha256(reference_model.read_bytes()).hexdigest(),
        'allow_op3_sites': list(allow_op3_sites), 'passthrough_sites': list(passthrough_sites),
        'serial_repairs': [], 'removed_atoms': [], 'eligible_sites': [], 'skipped_sites': [],
        'original_raw_coordinates_preserved': True, 'dictionaries_preserved': True,
        'requires_cif_review': False, 'notes': []}
    graphs = {}; candidates = {}; parent_lines_by_site = {}; curated_graphs = {}
    for action in actions:
        ligand = CURATED_LIGANDS.get(action.after)
        curated_placement = bool(ligand and (ligand.atom_substitutions or ligand.ring_substituents))
        if action.site in passthrough_sites:
            reason = ('Explicit curated placement is unchanged.' if curated_placement
                      else 'Frozen experimental backbone passthrough is preserved.')
            report['skipped_sites'].append({'site':action.site,'reason':reason});continue
        if action.method != 'coot-parent-overlap':
            if curated_placement:
                report['skipped_sites'].append({'site':action.site,'reason':'Explicit curated placement is unchanged.'})
            continue
        try:
            graph = source_graph_fragment(dictionary_paths[action.after],action.after)
            selected = [l for l in raw_lines if l[:6] in _COORDINATE and _site(l)==action.site]
            parent_lines = [l for l in _rows(parent_models[action.site]) if l[:6] in _COORDINATE and _site(l)==action.site]
            raw_names = {canonical_name(l[12:16].strip()) for l in selected}
            parent_names = {canonical_name(l[12:16].strip()) for l in parent_lines}
            missing = (raw_names&set(graph['scaffold_atoms']))-parent_names
            # Only the source-declared phosphate leaving oxygen is eligible.
            if missing and missing != {'OP3'}:
                raise ValueError('Unmatched backbone atoms need a separate context rule')
            pruned = [l for l in selected if not(missing and canonical_name(l[12:16].strip())=='OP3')]
            restore_graph_site(pruned,parent_lines,dictionary_paths[action.after],action.after,action.parent_code)
            graphs[action.site] = graph; parent_lines_by_site[action.site] = parent_lines
            if missing:
                candidates[action.site] = next(l for l in selected if canonical_name(l[12:16].strip())=='OP3')
            if curated_placement:
                curated_graphs[action.site] = {'component': action.after,
                    'source_sha256': graph['source_sha256'],
                    'parent_model_sha256': sha256(Path(parent_models[action.site]).read_bytes()).hexdigest(),
                    'scaffold_atoms': graph['scaffold_atoms'],
                    'missing_parent_atoms': sorted(missing),
                    'preflight': 'SOURCE_GRAPH_AND_PROPER_TRANSPORT_PASS; NO_FINAL_GRAPH_TRANSPORT_REQUESTED'}
        except (OSError,ValueError,KeyError,StopIteration) as exc:
            # An unsupported curated graph keeps the older placement/serial
            # authority only. In particular, no curated name authorizes a
            # phosphate edit, and legacy unsupported receipts remain stable.
            reason = 'Explicit curated placement is unchanged.' if curated_placement else str(exc)
            report['skipped_sites'].append({'site':action.site,'reason':reason})
    if curated_graphs:
        report['curated_context'] = {'policy_id': CURATED_CONTEXT_POLICY_ID,
            'scope': 'SOURCE_GRAPH_AND_DISCARDED_PARENT_SCAFFOLD_SHADOW_ONLY; FINAL_CURATED_PLACEMENT_UNCHANGED',
            'sites': sorted(curated_graphs),
            'candidate_sites': sorted(set(curated_graphs) & set(candidates)),
            'source_graphs': dict(sorted(curated_graphs.items()))}
    rendered = raw_lines
    if candidates:
        try:
            raw_inventory,reference_inventory = _pdb_inventory(raw_model),_pdb_inventory(reference_model)
            # Curated sites have also been changed by the declared Coot plan.
            # Calling them unchanged input would falsely reject a mixed batch.
            # Unsupported curated graphs retain serial authority only. Eligible
            # curated graphs independently passed the same chemical preflight.
            curated = {action.site for action in actions
                       if action.method == 'coot-parent-overlap' and action.site not in passthrough_sites
                       and (ligand := CURATED_LIGANDS.get(action.after)) is not None
                       and (ligand.atom_substitutions or ligand.ring_substituents)}
            selected = set(graphs) | curated
            normalized,repairs,authority = _serial_context(raw_lines,_rows(reference_model),raw_inventory,reference_inventory,selected)
            # The shadow receives only exact eligible scaffold parent coordinates.
            # Its base geometry is intentionally ignored and never propagated.
            targets = {}
            for site,lines in parent_lines_by_site.items():
                for line in lines:
                    if canonical_name(line[12:16].strip()) in graphs[site]['scaffold_atoms']:
                        targets[(site,canonical_name(line[12:16].strip()))] = line[30:54]
            shadow_lines = []
            for line in normalized:
                if line[:6] in _COORDINATE:
                    xyz = targets.get((_site(line),canonical_name(line[12:16].strip())))
                    if xyz is not None: line = line[:30]+xyz+line[54:]
                shadow_lines.append(line)
            output_model.parent.mkdir(parents=True,exist_ok=True)
            with shadow.open('x',newline='') as handle: handle.write(''.join(shadow_lines))
            proof = sanitize_phosphates(shadow,sanitized,reference_model=reference_model,
                allow_op3_sites=allow_op3_sites,passthrough_sites=passthrough_sites)
            removed = {(r['site'],canonical_name(r['atom'])) for r in proof['removed']}
            expected = {(site,'OP3') for site in candidates}
            if not expected <= removed or any(atom!='OP3' or site not in candidates for site,atom in removed):
                raise ValueError('Phosphate proof must remove exactly the proposed selected internal OP3 atoms')
            identities = {line[12:27] for line in normalized if line[:6] in _COORDINATE
                          and (_site(line),canonical_name(line[12:16].strip())) in removed}
            raw_serials = {line[12:27]:int(line[6:11]) for line in raw_lines if line[:6] in _COORDINATE}
            removed_records = [{**_identity(line),'serial':int(line[6:11]),
                'old_serial':raw_serials[line[12:27]],'new_serial':int(line[6:11]),
                'reason':'verified-incoming-O3-prime-P-link'} for line in normalized
                if line[:6] in _COORDINATE and line[12:27] in identities]
            if len(removed_records) != len(expected):
                raise ValueError('Ambiguous context deletion identity')
            rendered = [line for line in normalized if not(line[:6] in _COORDINATE | _ASSOCIATED and line[12:27] in identities)]
            report.update(status='CONTEXT_PREPARED',serial_repairs=repairs,removed_atoms=removed_records,
                eligible_sites=sorted(candidates),serial_authority=authority,shadow_sanitizer=proof,
                shadow_sha256=sha256(shadow.read_bytes()).hexdigest(),
                sanitized_shadow_sha256=sha256(sanitized.read_bytes()).hexdigest(),
                notes=['Internal OP3 removal was proved with the existing phosphate policy; original raw base coordinates were retained for rigid transport.'])
            if curated - set(graphs) and repairs:
                report['serial_scope_extension'] = {
                    'sites': sorted(curated - set(graphs)),
                    'authority': 'EXPLICIT_CURATED_PLACEMENT_MUTATION; SERIAL_FIELDS_ONLY',
                    'chemical_context': 'UNCHANGED; CURATED_SITES_ARE_NOT_OP3_CANDIDATES'}
        except (OSError,ValueError,KeyError) as exc:
            report.update(status='RAW_CONTEXT_RETAINED',reason=str(exc),
                notes=['The complete raw Coot context was retained because internal-phosphate or serial authority could not be proved.'])
            rendered = raw_lines
    if any(p.read_bytes()!=data for p,data in snapshots.items()):
        raise ValueError('An immutable context input changed during preparation')
    payload = ''.join(rendered).encode()
    if report['status'] != 'CONTEXT_PREPARED': payload = original
    output_model.parent.mkdir(parents=True,exist_ok=True)
    with output_model.open('xb') as handle: handle.write(payload)
    report['restoration_input_sha256'] = sha256(payload).hexdigest()
    report['source_inputs_preserved'] = True
    return {'model':output_model,'receipt':report,
            'shadow':shadow if shadow.is_file() else None,
            'sanitized_shadow':sanitized if sanitized.is_file() else None}
