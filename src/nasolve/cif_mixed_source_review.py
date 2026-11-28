"""Describe current component inputs separately from historical generation.

This is a read-only declaration inventory, not a chemical-state selector. The
caller must first reproduce the maintained mixed-context/native lineage. Raw
source-to-base differences and declared site projections remain separate: an
internal OP3 deletion does not authorize changing OP2, sugar bonds or charge.
"""
from copy import deepcopy

from .cif_doctor import compare_dictionaries
from .cif_mixed_context import _ref, _resolve
from .ligand_profiles import dictionary_component_codes

POLICY_ID = 'cif-mixed-current-source-declarations-v1'
CHEMICAL_FIELDS = frozenset({
    'atom_elements', 'bond_orders', 'hydrogen_attachments',
    'declared_charge_fields', 'atom_stereo_declarations',
    'bond_aromatic_declarations', 'bond_stereo_declarations', 'signed_chirality',
})
IDENTITY_FIELDS = frozenset({'atom_elements', 'bond_orders', 'hydrogen_attachments'})


def _changes(difference):
    """Keep presence distinct from unknown values; retain charge namespaces."""
    left, right = difference['source'], difference['effective']
    if not isinstance(left, dict) or not isinstance(right, dict):
        return [{'source': deepcopy(left), 'current': deepcopy(right)}]
    return [{'key': key, 'source_present': key in left, 'current_present': key in right,
             'source': deepcopy(left.get(key)), 'current': deepcopy(right.get(key))}
            for key in sorted(left.keys() | right.keys())
            if key not in left or key not in right or left[key] != right[key]]


def review_verified_context(root, parent_root, report):
    """Inventory the exact context inputs after maintained lineage replay.

    References address the two declared views of the owned source capsule,
    never the temporary staging directory or a historical absolute path. This
    helper does not independently grant usability to an unverified report.
    """
    from .cif_runtime_bundle import _load_json
    sources = {code: _resolve(root, parent_root, ref)
               for code, ref in report['inputs']['sources'].items()}
    providers = {}
    references = report['bundle']['effective_dictionaries']
    dictionaries = [_resolve(root, parent_root, ref) for ref in references]
    for path, ref in zip(dictionaries, references):
        for code in dictionary_component_codes(path):
            if code in providers:
                raise ValueError('Ambiguous current source-review component provider')
            providers[code] = ref
    if set(providers) != set(sources):
        raise ValueError('Current source-review component scope differs')
    comparison = compare_dictionaries(list(sources.values()), dictionaries)
    if (comparison['input_integrity'] != 'UNCHANGED'
            or comparison['comparison_scope_complete'] is not True
            or set(comparison['compared_components']) != set(sources)):
        raise ValueError('Current source comparison is incomplete or changed')

    parent = _load_json(_resolve(root, parent_root, report['inputs']['linked_parent_report']))
    preparations = [*parent['bundle']['preparations'].values(),
                    *report['bundle']['preparations'].values()]
    projections = report['bundle']['site_projections']
    contexts = {code: [] for code in sources}
    seen = set()
    for preparation in preparations:
        receipt = preparation['receipt']; code = receipt['component']
        for row in receipt['sites']:
            site = row['site']; projection = projections[site]
            if site in seen or projection['component'] != code or code not in contexts:
                raise ValueError('Ambiguous current source-review site context')
            seen.add(site)
            _resolve(root, parent_root, projection['dictionary'])
            contexts[code].append({key: deepcopy(row[key]) for key in (
                'site', 'incoming_site', 'outgoing_site', 'five_prime_state',
                'three_prime_state', 'modification_id', 'deleted_atoms')})
            contexts[code][-1]['projection'] = deepcopy(projection['dictionary'])
    if seen != set(projections):
        raise ValueError('Current source-review site projection scope differs')

    canonical = set(report['bundle']['installed_canonical_components'])
    if not canonical <= sources.keys():
        raise ValueError('Unknown installed canonical component in source review')
    rows = []
    for code in sorted(sources):
        differences = [row for row in comparison['differences']
                       if row['component_id'] == code and row['field'] in CHEMICAL_FIELDS]
        fields = sorted(row['field'] for row in differences)
        source_component = next(row for row in comparison['source_assessment']['components']
                                if row['component_id'] == code)
        current_component = next(row for row in comparison['effective_assessment']['components']
                                 if row['component_id'] == code)
        rows.append({
            'component': code,
            'source': deepcopy(report['inputs']['sources'][code]),
            'current_dictionary': deepcopy(providers[code]),
            'comparison_scope': ('CANONICAL_GRAPH_INPUT_ONLY; INSTALLED_NUMERICS_NOT_COMPARED'
                                 if code in canonical else 'EXPLICIT_BASE_DICTIONARY_BEFORE_SITE_MODIFICATIONS'),
            'source_graph_status': source_component['verdicts']['graph'],
            'current_graph_status': current_component['verdicts']['graph'],
            'declaration_status': 'DIFFERENCES_RECORDED' if fields else 'NO_DIFFERENCES_IN_COMPARED_FIELDS',
            'changed_fields': fields,
            'differences': [{'field': row['field'], 'changes': _changes(row)} for row in differences],
            'site_contexts': sorted(contexts[code], key=lambda row: row['site']),
            'historical_generation': deepcopy(report['bundle']['preserved_source_findings'][code]),
        })
    explicit = [row for row in rows if row['component'] not in canonical]
    structural = [row['component'] for row in explicit if IDENTITY_FIELDS.intersection(row['changed_fields'])]
    other = [row['component'] for row in explicit if row['changed_fields'] and row['component'] not in structural]
    unchanged = [row['component'] for row in explicit if not row['changed_fields']]
    # Recheck all bound files after parsing; caller also verifies the entire
    # staged view and owned capsule before returning the ordinary assessment.
    for ref in [*report['inputs']['sources'].values(), *references,
                report['inputs']['linked_parent_report'], *[p['dictionary'] for p in projections.values()]]:
        _resolve(root, parent_root, ref)
    return {
        'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'RECORDED',
        'reference_scope': 'DECLARED_CONTEXT_AND_LINKED_PARENT_VIEWS_OF_OWNED_SOURCE_CAPSULE',
        'context_report': _ref(root/'mixed_context.json', root),
        'linked_parent_report': deepcopy(report['inputs']['linked_parent_report']),
        'components': rows,
        'summary': {'explicit_components_compared': len(explicit),
                    'atom_bond_or_hydrogen_difference_components': structural,
                    'other_declaration_difference_components': other,
                    'no_declaration_difference_components': unchanged,
                    'canonical_graph_only_components': sorted(canonical)},
        'input_integrity': 'UNCHANGED', 'source_state_repair': 'NOT_PERFORMED',
        'scientific_qualification': 'NOT_ASSESSED', 'automatic_adoption': False,
        'limitations': [
            'Same-ID declaration differences are evidence, not inferred chemical equivalence, corruption or a repair decision.',
            'Compare source with the current base dictionary before the separately recorded site modifications.',
            'Historical generation rejection does not describe a later recovered input.',
            'Missing declarations remain unknown; partial charge, formal charge and signed/CIP stereo remain distinct.',
            'Canonical graph input equality does not compare installed native component numerics.',
            'Numerical restraints, energy types, coordinate stereochemistry and scientific validity are outside this comparison.',
        ],
    }
