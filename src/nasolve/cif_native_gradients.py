"""Fixed-coordinate native derivative evidence; no optimization or chemistry approval."""
from copy import deepcopy
from hashlib import sha256
from inspect import getsource
import hashlib
import importlib
import json
import math
from pathlib import Path

from . import cif_gradient_audit as core
from .cif_gradient_audit import audit_gradients, fixed_signature, FAMILIES
from .cif_mixed_gradient import _manager_digest, _gradient_replay, _numeric_equal, MAX_CALLS
from .cif_candidate_usability import energy_inventory_checks
from .cif_captured_geometry import review_captured_geometry
from .cif_fixed_geometry import _fixed_policy

POLICY_ID = 'cif-native-fixed-gradient-inventory-v1'
NUMERIC_MODULES = ('cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.energies',
                   'cctbx.geometry_restraints.manager', 'cctbx_geometry_restraints_ext',
                   'cctbx.array_family.flex')


def validate_gradient_request(indices, *, linked, energy, policy, mapping, nonbonded):
    """Reject ambiguous probes/compositions before allocating a native attempt."""
    if (not isinstance(indices, (list, tuple)) or not 1 <= len(indices) <= 6
            or any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices)):
        raise ValueError('Require one to six distinct nonnegative integer gradient indices')
    if not linked or not energy or not policy or mapping or nonbonded:
        raise ValueError('Gradient capture requires linked energy/policy inventories without mapping or pair capture')


def _numeric_sources():
    rows = []
    for name in NUMERIC_MODULES:
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve(strict=True)
        rows.append({'module': name, 'historical_path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return rows


def _capture_gradients(geo, sites, native, selected):
    """Trusted worker helper; capture actual ordinary native evaluations."""
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    points = [[float(x) for x in p] for p in sites]
    if (any(i >= len(points) for i in selected) or geo.parallelity_proxies
            or list(geo.site_symmetry_table.special_position_indices())):
        raise ValueError('Unsupported gradient probes, parallelity or special positions')
    details = native['geometry']['proxy_details']
    if details['bond_asu'] or any(p['symmetry_operation'] not in (None, 'x,y,z') for p in details['bond_simple']):
        raise ValueError('Gradient capture requires identity-only covalent proxies')
    signature = fixed_signature(geo, sites)
    sources = _numeric_sources()
    baselines = {f: [] for f in FAMILIES}
    def evaluate(p, family):
        active = flags.flags(default=family == 'all')
        if family != 'all': setattr(active, family, True)
        e = geo.energies_sites(sites_cart=flex.vec3_double(p), flags=active, compute_gradients=True, normalization=False)
        if family in ('all', 'nonbonded'):
            nb = e.nonbonded_proxies
            if nb is None or len(nb.asu) or any(q.rt_mx_ji is not None and not q.rt_mx_ji.is_unit_mx() for q in nb.simple):
                raise ValueError('Gradient capture requires identity-only nonbonded proxies')
        row = {'target': float(e.target), 'gradient': [float(v) for v in e.gradients.as_double()],
               'proxy_counts': {k: v for k, v in vars(e).items() if k.startswith('n_') and k.endswith('_proxies')}}
        if p == points: baselines[family].append(deepcopy(row))
        return row
    raw = native['energy_inventory']['snapshots'][0]
    audit = audit_gradients(evaluate, {'initial': points}, selected,
        references={'initial': {k: raw[k] for k in ('target', 'gradient_norm')}}, max_calls=MAX_CALLS)
    after = fixed_signature(geo, sites)
    sources_after = _numeric_sources()
    if signature != after or points != [list(p) for p in sites] or sources != sources_after:
        raise RuntimeError('Derivative audit changed coordinates, constraints or native numerical sources')
    return {'schema_version': 1, 'policy_id': INVENTORY_POLICY, 'status': 'RECORDED', 'normalization': False,
            'symmetry_scope': 'IDENTITY_ONLY', 'parallelity_scope': 'NO_PARALLELITY',
            'selected_indices': list(selected), 'coordinates_unchanged': True, 'special_position_indices': [],
            'constraint_signature_before': signature, 'constraint_signature_after': after,
            'manager_sha256': _manager_digest(native), 'installed_numeric_sources': sources,
            'installed_numeric_sources_after': sources_after, 'gradient_audit': audit, 'baseline_evaluations': baselines}


# The helper is also callable in synthetic worker tests; audit POLICY_ID remains separate.
INVENTORY_POLICY = POLICY_ID


def native_gradient_worker(base):
    """Embed maintained numerical helpers in an isolated namespace; leave old workers intact."""
    header = 'try:\n    from iotbx import phil\n'
    token = '    report["energy_inventory"]["status"]="RECORDED"\n'
    if (base.count(header) != 1 or base.count(token) != 1
            or 'gradient_inventory' in base or 'nonbonded_inventory' in base):
        raise ValueError('Unsupported native energy worker for derivative capture')
    helper = 'from copy import deepcopy\nfrom hashlib import sha256\nimport hashlib,importlib,json,math\nfrom pathlib import Path\n'
    for name in ('POLICY_ID', 'FAMILIES', 'STEPS', 'FD_ABSOLUTE', 'FD_RELATIVE'):
        helper += name + '=' + repr(getattr(core, name)) + '\n'
    helper += 'INVENTORY_POLICY=' + repr(POLICY_ID) + '\nMAX_CALLS=' + repr(MAX_CALLS) + '\nNUMERIC_MODULES=' + repr(NUMERIC_MODULES) + '\n'
    for function in (core._norm, core._unit, core._close, audit_gradients, fixed_signature, _manager_digest, _numeric_sources, _capture_gradients):
        helper += getsource(function) + '\n'
    block = '_gradient_helpers = {}\nexec(' + repr(helper) + ', _gradient_helpers)\n'
    extra = '    report["gradient_inventory"] = _gradient_helpers["_capture_gradients"](geo, sites, report, spec["gradient_indices"])\n'
    return base.replace(header, block + header).replace(token, token + extra)


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def review_native_gradients(native):
    """Recompute all saved directional tests without SDK access or writes.

    Frozen input/worker/output receipts and source chemistry require separate
    attestation. A numerical disagreement is REVIEW; malformed evidence raises.
    """
    try:
        review_captured_geometry(native)
        if not all(energy_inventory_checks(native).values()) or not _fixed_policy(native):
            raise ValueError('Require repeatable energy and explicit fixed restraint policy')
        q = native['gradient_inventory']; selected = q['selected_indices']
        validate_gradient_request(selected, linked=True, energy=True, policy=True, mapping=False, nonbonded=False)
        details = native['geometry']['proxy_details']
        if (type(q['schema_version']) is not int or q['schema_version'] != 1 or q['policy_id'] != POLICY_ID
                or q['status'] != 'RECORDED' or q['normalization'] is not False
                or q['symmetry_scope'] != 'IDENTITY_ONLY' or q['parallelity_scope'] != 'NO_PARALLELITY'
                or q['coordinates_unchanged'] is not True or q['special_position_indices'] != []
                or details['parallelity'] or details['bond_asu']
                or any(p['symmetry_operation'] not in (None, 'x,y,z') for p in details['bond_simple'])
                or any(i >= native['atom_count'] for i in selected)
                or not _digest(q['constraint_signature_before'])
                or q['constraint_signature_before'] != q['constraint_signature_after']
                or q['manager_sha256'] != _manager_digest(native)):
            raise ValueError('Unsupported or differently bound native derivative evidence')
        sources = q['installed_numeric_sources']
        if (not isinstance(sources, list) or [s['module'] for s in sources] != list(NUMERIC_MODULES)
                or sources != q['installed_numeric_sources_after']
                or any(not _digest(s['sha256']) or not isinstance(s['historical_path'], str) or not s['historical_path'] for s in sources)
                or native['energy_inventory']['installed_sources'] != sources[:3]):
            raise ValueError('Native numerical source fingerprints differ or are incomplete')
        audit = q['gradient_audit']; case = audit['cases']['initial']; raw = native['energy_inventory']['snapshots'][0]
        if (type(audit['evaluation_calls']) is not int or not 0 < audit['evaluation_calls'] <= MAX_CALLS
                or type(audit['max_evaluation_calls']) is not int or audit['max_evaluation_calls'] != MAX_CALLS
                or case['captured_snapshot_match']['comparisons'].keys() != {'target', 'gradient_norm'}
                or any(case['captured_snapshot_match']['comparisons'][k]['captured'] != raw[k] for k in ('target', 'gradient_norm'))):
            raise ValueError('Derivative budget or captured reference differs')
        if not _numeric_equal(raw, native['energy_inventory']['snapshots'][1]):
            raise ValueError('Fixed native energy snapshots differ')
        for rows in q['baseline_evaluations'].values():
            for row in rows:
                if not isinstance(row['proxy_counts'], dict) or any(
                        v is not None and (type(v) is not int or v < 0) for v in row['proxy_counts'].values()):
                    raise ValueError('Invalid native proxy accounting')
        expected = {k: raw[k] for k in ('target', 'gradient', 'proxy_counts')}
        if not _numeric_equal(q['baseline_evaluations']['all'][0], expected):
            raise ValueError('Derivative baseline differs from fixed native energy/gradient')
        passed = _gradient_replay(audit, native['geometry']['sites_cart_exact'], q['baseline_evaluations'], list(selected))
        return {'schema_version': 1, 'policy_id': POLICY_ID,
                'status': 'SAMPLED_DERIVATIVES_PASS' if passed else 'REVIEW', 'sampled_derivatives_pass': passed,
                'family_checks': {f: v['sampled_directions_consistent'] and v['repeat_consistent'] for f, v in case['families'].items()},
                'evaluation_calls': audit['evaluation_calls'], 'selected_indices': list(selected),
                'selected_labels': [native['atoms'][i]['label'] for i in selected], 'manager_sha256': q['manager_sha256'],
                'numerical_evidence_replayed': True, 'native_execution': 'NOT_RUN', 'model_optimization': 'NOT_RUN',
                'chemical_qualification': 'NOT_ESTABLISHED', 'automatic_adoption': False,
                'limitations': ['Agreement covers sampled directions at these exact coordinates, not every component or global convergence.',
                    'No parallelity, special positions or nonidentity symmetry; no geometry or chemical acceptance.',
                    'Frozen input/worker/output receipts require separate attestation.']}
    except (KeyError, TypeError, IndexError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete native derivative evidence') from exc
