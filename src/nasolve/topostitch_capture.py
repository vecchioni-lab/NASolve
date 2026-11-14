"""Compare observed initial native contexts; not a complete exclusion-policy proof.

Cedar authenticates the source capture and owns native interpretation. This small
boundary compares a fresh reconstruction before the masked evaluator is used.
It neither executes captured code nor infers future neighbour membership.
"""
from hashlib import sha256
import json

POLICY = 'topostitch-observed-native-reconstruction-v1'
_REQUIRED = ('atoms', 'atom_count', 'monomer_mappings', 'geometry',
             'installed_api_sources', 'restraint_policy', 'full_monomer_inventory',
             'energy_inventory', 'nonbonded_inventory', 'phil_adaptations',
             'dictionary_loading', 'parameter_consumers')


def _observed(value):
    if isinstance(value, dict):
        # Source location is provenance. Module identity and exact bytes remain
        # operational checks; no other path or report field is ignored.
        if set(value) == {'module', 'sha256', 'historical_path'}:
            return {k: value[k] for k in ('module', 'sha256')}
        return {k: _observed(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_observed(v) for v in value]
    return value


def _bytes(value):
    return json.dumps(_observed(value), sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode()


def compare_reconstructed_context(expected, rebuilt):
    """Require exact observed context, including initial directed ASU pair lists.

    Both inventories must first be authenticated/reviewed by Cedar. A match is
    only evidence for this initial construction, not permission to move atoms.
    """
    for report in (expected, rebuilt):
        if (not isinstance(report, dict) or report.get('status') != 'REVIEW'
                or type(report.get('schema_version')) is not int
                or report['schema_version'] != 1
                or report.get('automatic_adoption') is not False
                or report.get('fatal_problems') is not None
                or report.get('unused_definitions') or report.get('unsupported_fields')
                or any(k not in report for k in _REQUIRED)):
            raise ValueError('Require complete reviewed native reconstruction inventories')
        for key in ('optimization', 'model_editing', 'scientific_approval'):
            if report.get(key) != 'NOT_RUN':
                raise ValueError('Native reconstruction must remain read-only')
        if (report['nonbonded_inventory'].get('policy_id') != 'cif-native-nonbonded-asu-attribution-v1'
                or report['energy_inventory'].get('normalization') is not False
                or report['restraint_policy'].get('secondary_structure_enabled') is not False):
            raise ValueError('Require explicit ASU nonbonded and unnormalized fixed native policy')
    if _bytes(expected) != _bytes(rebuilt):
        keys = sorted(set(expected) | set(rebuilt))
        different = [k for k in keys if k not in expected or k not in rebuilt
                     or _bytes(expected[k]) != _bytes(rebuilt[k])]
        raise ValueError('Reconstructed native context differs: '+', '.join(different))
    return {'schema_version': 1, 'policy_id': POLICY,
            'status': 'INITIAL_OBSERVED_CONTEXT_MATCH',
            'observed_context_sha256': sha256(_bytes(expected)).hexdigest(),
            'compared_fields': sorted(expected), 'runtime_authority': False,
            'complete_exclusion_policy_authenticated': False,
            'future_neighbour_membership_qualified': False,
            'scientific_acceptance': False}
