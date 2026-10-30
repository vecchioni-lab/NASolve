"""Bind explicit isolated evidence before source-preserving site preparation.

This is a read-only eligibility check, not linked native qualification or an
absolute CIP assignment. Chemical identity comes from the source graph; residue
codes and atom names identify records, never a supported-family whitelist.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .cif_candidate_usability import reassess_complete_candidate
from .cif_purine_representation import validate_policy

POLICY_ID = 'cif-source-bound-preparation-qualification-v1'
REQUIRED_NATIVE_CHECKS = frozenset({
    'source_chemistry_and_configuration', 'native_completed',
    'no_native_fatal_or_unused', 'exact_model_and_component',
    'native_coordinate_roundtrip', 'one_complete_monomer',
    'exact_effective_definitions', 'no_contradictory_native_formal_charges',
    'effective_declared_bond_orders', 'no_competing_native_ss',
    'proxy_counts_complete', 'finite_active_proxy_parameters',
    'exact_active_bonds', 'exact_active_angles', 'exact_active_torsions',
    'exact_active_planes', 'exact_fixed_chirality_membership',
    'omitted_unoriented_volume_coverage', 'energy_inventory',
    'finite_energy_and_gradient', 'fixed_coordinate_repeats',
})


def bind_preparation_qualification(source: Path, candidate: Path, code: str,
        qualification: dict, *, bond_representation_policy: str) -> dict:
    """Reassess exact source/candidate bytes under the recorded explicit policy.

    Every source fixed or R/S-declared centre must have a preserved four-neighbour
    coordinate configuration. The number and names of those centres are derived
    from the source. A partial or unassessable sugar cannot pass by satisfying a
    fixed three-centre checklist. Caller-supplied native evidence is an existing
    qualification contract; this function does not run or authenticate Phenix.
    """
    validate_policy(bond_representation_policy)
    if bond_representation_policy is None:
        raise ValueError('Require an explicit bond representation policy')
    paths = [Path(source), Path(candidate)]
    payloads = [p.read_bytes() for p in paths]
    q = qualification
    if not isinstance(q, dict):
        raise ValueError('Require isolated native qualification evidence')
    checks = q.get('checks')
    if (type(q.get('schema_version')) is not int or q['schema_version'] != 1
            or q.get('policy_id') != 'cif-isolated-candidate-native-usability-v3'
            or q.get('status') != 'ISOLATED_NATIVE_USABILITY_PASS'
            or q.get('native_usable') is not True or q.get('component') != code
            or q.get('scope') != 'ISOLATED_COMPONENT_ONLY'
            or not isinstance(checks, dict) or set(checks) != REQUIRED_NATIVE_CHECKS
            or any(value is not True for value in checks.values())
            or q.get('candidate_sha256') != sha256(payloads[1]).hexdigest()):
        raise ValueError('Require complete bound isolated native qualification')
    fresh = reassess_complete_candidate(*paths, code,
        bond_representation_policy=bond_representation_policy)
    recorded = q.get('source_assessment')
    if not isinstance(recorded, dict):
        raise ValueError('Require recorded source assessment')
    # Filenames are provenance, not chemical identity; exact byte hashes and
    # recomputed semantic evidence remain valid after an anchored relocation.
    fields = ('policy_id', 'component', 'candidate_status', 'rejection_reasons',
              'formal_charges_preserved', 'unoriented_volume_omissions',
              'requires_native_tetrahedral_coverage', 'finished_stereo')
    legacy = recorded.get('legacy_inspection')
    if (fresh['candidate_status'] != 'CANDIDATE_REVIEW'
            or any(recorded.get(key) != fresh[key] for key in fields)
            or not isinstance(legacy, dict)
            or legacy.get('bond_representation') != fresh['legacy_inspection'].get('bond_representation')):
        raise ValueError('Isolated evidence does not bind the current source, candidate and policy')
    stereo = fresh['finished_stereo']
    if any(term['handedness'] != 'PRESERVED' for term in stereo['terms']):
        raise ValueError('Every source-declared configuration must be assessable and preserved')
    if any(p.read_bytes() != data for p, data in zip(paths, payloads)):
        raise ValueError('Input changed during qualification binding')
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'BOUND_REVIEW',
        'component': code, 'bond_representation_policy': bond_representation_policy,
        'source_sha256': sha256(payloads[0]).hexdigest(),
        'candidate_sha256': sha256(payloads[1]).hexdigest(),
        'candidate_reassessment': fresh, 'source_configuration': stereo,
        'linked_qualification': 'NOT_RUN', 'automatic_adoption': False}



def project_source_configurations(binding: dict, before: dict, after: dict) -> list[dict]:
    """Retain each surviving source centre's declared first-neighbour graph.

    A removed chemical group may carry its centre away. A centre retained across
    a substitution needs a separately qualified linked configuration; deleting
    one of its neighbours must not silently erase its signed restraint. This
    check makes no absolute CIP or phosphorus-stereochemistry assignment.
    """
    def neighbors(values):
        graph = {name: set() for name in values['_chem_comp_atom.atom_id']}
        for a, b in zip(values['_chem_comp_bond.atom_id_1'], values['_chem_comp_bond.atom_id_2']):
            graph[a].add(b)
            graph[b].add(a)
        return graph
    old, new = neighbors(before), neighbors(after)
    checks = []
    for term in binding['source_configuration']['terms']:
        center = term['center']
        if center not in new:
            status = 'REMOVED_WITH_EXPLICIT_GROUP'
        else:
            if new[center] != old[center]:
                raise ValueError('Operation changes a retained source configuration: ' + center)
            status = 'RETAINED_SOURCE_NEIGHBORS'
        checks.append({'center': center, 'status': status,
                       'ordered_neighbors': term['ordered_neighbors']})
    return checks



def qualify_native_backbone_ports(values: dict, context: dict) -> dict:
    """Check the conventional native adapter's elements and source port state.

    This is intentionally narrower than generic graph recognition. Other element
    substitutions, charged reacting ports or bridged oxygen states need their own
    operation authority; conventional atom names cannot grant that permission.
    Retained nonreacting phosphate oxygen protonation is not normalized.
    """
    from .cif_attachment_sites import _neutral_hydroxyl_hydrogens
    from .cif_stereochemistry_audit import _graph
    elements, bonds, charges, neighbors = _graph(values)
    expected = {'P': 'P', 'OP1': 'O', 'OP2': 'O', 'OP3': 'O',
                "O5'": 'O', "C5'": 'C', "C3'": 'C', "O3'": 'O'}
    if any(elements.get(name) != element for name, element in expected.items()):
        raise ValueError('Unsupported elements at conventional native backbone ports')
    def heavy(atom):
        return {n for n in neighbors[atom] if elements[n] not in {'H', 'D'}}
    def single(a, b):
        return bonds.get(tuple(sorted((a, b)))) == 'SINGLE'
    if (neighbors['P'] != {'OP1', 'OP2', 'OP3', "O5'"}
            or any(heavy(n) != {'P'} for n in ('OP1', 'OP2', 'OP3'))
            or neighbors["O5'"] != {'P', "C5'"}
            or charges["O5'"] != 0 or not single('P', "O5'")
            or not single("O5'", "C5'") or heavy("O3'") != {"C3'"}
            or not single("C3'", "O3'")):
        raise ValueError('Unsupported graph/state at conventional native backbone ports')
    outgoing = _neutral_hydroxyl_hydrogens("O3'", elements, bonds, charges, neighbors)
    if outgoing is None:
        raise ValueError('Source O3-prime hydroxyl requires separate chemical-state authority')
    leaving = None
    if context.get('incoming_site'):
        leaving = _neutral_hydroxyl_hydrogens('OP3', elements, bonds, charges, neighbors)
        if not single('P', 'OP3') or leaving is None:
            raise ValueError('Source phosphate leaving port requires separate chemical-state authority')
    return {'scope': 'CONVENTIONAL_NATIVE_DNA_PORTS', 'elements': expected,
        'source_o3_hydrogens': sorted(outgoing),
        'incoming_leaving_hydrogens': sorted(leaving) if leaving is not None else [],
        'op2_protonation': 'PRESERVED', 'protonation_inferred': False}
