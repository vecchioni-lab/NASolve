"""Read-only selection dependence of captured geometry and native repulsion.

Descriptive covalent deviations are never promoted to native energy estimates.
A fixed-only dependency cannot change while its coordinates/manager remain fixed;
selected or boundary dependencies are not promises of a feasible repair.
"""
from copy import deepcopy
from collections import Counter
from hashlib import sha256
import math

from .cif_attachment_native import _capture
from .cif_catalogue import _digest
from .cif_captured_geometry import review_captured_geometry
from .cif_fana_geometry import inspect_fana_selected_geometry
from .cif_fana_junction import _path
from .cif_mixed_gradient import _manager_digest
from .cif_native_nonbonded import review_native_nonbonded
from .cif_selected_geometry import SelectedCoordinates

POLICY_ID = 'cif-selected-environment-review-v1'
SCOPES = ('selected_only', 'boundary', 'fixed_only')


def _scope(indices, selected):
    count = sum(i in selected for i in indices)
    return 'fixed_only' if count == 0 else 'selected_only' if count == len(indices) else 'boundary'


def review_selected_environment(native, moving_indices):
    """Partition validated evidence by dependency, without optimization or acceptance."""
    space = SelectedCoordinates(native['geometry']['sites_cart_exact'], moving_indices)
    geometry = review_captured_geometry(native)
    pairs = review_native_nonbonded(native)
    selected = set(space.indices)
    groups = {}
    for family, measurements in geometry['measurements'].items():
        groups[family] = {}
        for scope in SCOPES:
            rows = [deepcopy(r) for r in measurements if _scope(r['i_seqs'], selected) == scope]
            ranked = sorted((r for r in rows if r['nominal_deviation'] is not None),
                            key=lambda r: (-abs(r['nominal_deviation']), r['proxy_index']))
            groups[family][scope] = {
                'rows': rows, 'proxy_count': len(rows),
                'status_counts': dict(Counter(r['status'] for r in rows)),
                'unranked_count': len(rows)-len(ranked),
                'nominal_abs_ge_3': sum(abs(r['nominal_deviation']) >= 3 for r in ranked),
                'nominal_abs_ge_5': sum(abs(r['nominal_deviation']) >= 5 for r in ranked),
                'sign_conflicts': sum(r['sign_agreement'] is False for r in rows),
                'worst': ranked[:10]}
    nonbonded = {}
    for scope in SCOPES:
        rows = [deepcopy(r) for r in pairs['measurements'] if _scope(r['i_seqs'], selected) == scope]
        nonbonded[scope] = {
            'pair_count': len(rows), 'positive_residual_pairs': sum(r['residual'] > 0 for r in rows),
            'native_residual': math.fsum(r['residual'] for r in rows),
            'rows': rows, 'worst': sorted(rows, key=lambda r: (-r['residual'], r['i_seqs']))[:10]}
    if not math.isclose(math.fsum(v['native_residual'] for v in nonbonded.values()),
                        pairs['total_residual'], rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError('Selection buckets do not reproduce native nonbonded residual')
    energy = native['energy_inventory']['snapshots'][-1]
    gradient = energy['gradient']; space.project(gradient)
    full_norm = math.hypot(*gradient)
    if not math.isclose(full_norm, energy['gradient_norm'], rel_tol=1e-12, abs_tol=1e-10):
        raise ValueError('Recorded full gradient norm differs from the complete vector')
    fixed_gradient = [v for i in range(len(space.points)) if i not in selected for v in gradient[3*i:3*i+3]]
    projected_norm = math.hypot(*space.project(gradient)); fixed_norm = math.hypot(*fixed_gradient)
    return {
        'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW',
        'manager_sha256': _manager_digest(native), 'moving_indices': space.indices,
        'moving_labels': [native['atoms'][i]['label'] for i in space.indices],
        'selected_atom_count': len(selected), 'fixed_atom_count': len(space.points)-len(selected),
        'geometry': groups, 'deferred_proxy_kinds': deepcopy(geometry['deferred_proxy_kinds']),
        'nonbonded': {'groups': nonbonded, 'total_native_residual': pairs['total_residual'],
                      'raw_pair_arithmetic_replayed': True},
        'gradient': {'selected_norm': projected_norm, 'fixed_norm': fixed_norm, 'full_norm': full_norm,
                     'norm_partition_squared': projected_norm**2+fixed_norm**2},
        'full_native_target': energy['target'], 'covalent_native_residuals': 'UNASSESSED',
        'total_objective_partition': 'NOT_ESTABLISHED', 'convergence': 'NOT_ASSESSED',
        'native_execution': 'NOT_RUN', 'model_editing': 'NOT_RUN',
        'chemical_qualification': 'NOT_ESTABLISHED', 'geometry_accepted': False, 'automatic_adoption': False,
        'limitations': [
            'Selection dependency is not proof that a feasible or chemically valid repair exists.',
            'Covalent scalar deviations are descriptive; unknown and deferred categories remain visible.',
            'Only captured native nonbonded residuals are partitioned; no complete objective floor is inferred.',
            'Full gradients on held atoms are not the selected optimizer convergence gradient.',
            'Receipt authenticity, fixed mechanics, topology and source chemistry require separate binding.']}


def inspect_fana_environment(control, bridge_seed, trial, endpoint_receipt, pair_receipt):
    """Compose the established FANA endpoint gates with the selection report."""
    bound = inspect_fana_selected_geometry(control, bridge_seed, trial, endpoint_receipt, pair_receipt)
    root = _path(trial, directory=True); path = _path(pair_receipt)
    payload = (root/'candidate.pdb').read_bytes()
    if sha256(payload).hexdigest() != bound['trial']['candidate_sha256']:
        raise ValueError('Selected candidate changed during environment review')
    if _digest(path.read_bytes()) != bound['bindings']['pair_receipt']:
        raise ValueError('Bound pair receipt changed during environment review')
    _, native, frozen = _capture(path, payload)
    result = review_selected_environment(native, bound['trial']['moving_indices'])
    result['fana_endpoint'] = {
        'candidate_checks_pass': bound['candidate_checks_pass'], 'checks': bound['checks'],
        'candidate_sha256': bound['trial']['candidate_sha256'], 'bindings': bound['bindings'],
        'stopping_classification': bound['trial']['stopping_classification']}
    if any(p.read_bytes() != data for p, data in frozen.items()):
        raise ValueError('Native environment evidence changed during review')
    return result
