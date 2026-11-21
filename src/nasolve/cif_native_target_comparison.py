"""Read-only dictionary controls at identical captured coordinates.

Changed targets, weights and chemical definitions are different objectives, not
an optimization trajectory. This diagnostic neither projects source chemistry
nor approves the chemical state of a linked residue.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import math

from .cif_attachment_native import _capture, _identity
from .cif_captured_geometry import review_captured_geometry
from .cif_terminal_qualification import _proxy_subset
from .cif_topology_gate import review_native_topology

POLICY_ID = 'cif-native-fixed-coordinate-target-comparison-v1'


def _mappings(native):
    inventory = native['monomer_mappings']
    if inventory.get('status') != 'RECORDED':
        raise ValueError('Require complete monomer mappings')
    result = {}
    expected = {_identity(a)[:2] for a in native['atoms']}
    for row in inventory['rows']:
        site = row['site']
        if site in result or (site, row['resname']) not in expected:
            raise ValueError('Duplicate or unexpected monomer mapping')
        if not isinstance(row.get('metadata', {}).get('effective_definition'), dict):
            raise ValueError('Effective monomer definition unavailable')
        literal = row.get('literal_identity', {})
        expected_identity = next(a['identity'] for a in native['atoms'] if _identity(a)[:2] == (site, row['resname']))
        if (literal.get('status') != 'RECORDED'
                or any(not isinstance(literal.get(k), str) or literal[k].strip() != v.strip()
                       for k, v in expected_identity.items())):
            raise ValueError('Monomer mapping literal identity differs from model')
        result[site] = row
    if {(s, r['resname']) for s, r in result.items()} != expected:
        raise ValueError('Incomplete monomer mappings')
    return result


def _scalar_rows(native, rows):
    result = {}
    for row in rows:
        key = (tuple(_identity(native['atoms'][i]) for i in row['i_seqs']), row['origin_id'])
        if key in result:
            raise ValueError('Ambiguous duplicate scalar proxy endpoints/origin')
        result[key] = row
    return result


def review_native_target_comparison(before, after, model_payload, changed_sites, expected_links,
                                    *, na_policy=None, na_phil=None):
    """Compare complete inventories; caller binds receipts and source declarations.

    Only explicitly declared sites may change definitions. Ordered named scalar
    endpoints are matched conservatively; reversed or absent proxies remain
    visible as additions/removals. No geometrical nearest-neighbour matching.
    """
    if (not isinstance(changed_sites, (list, tuple)) or not changed_sites
            or any(not isinstance(s, str) for s in changed_sites)
            or len(set(changed_sites)) != len(changed_sites)):
        raise ValueError('Require distinct explicitly declared changed sites')
    topology = [review_native_topology(n, model_payload, expected_links,
                na_policy=na_policy, na_phil=na_phil) for n in (before, after)]
    if any(t['link_status'] != 'MATCH' for t in topology):
        raise ValueError('Both dictionary controls require the exact declared topology')
    geometry = [review_captured_geometry(n) for n in (before, after)]
    for field in ('atoms', 'installed_api_sources', 'restraint_policy', 'parameter_consumers', 'phil_adaptations'):
        if field not in before or field not in after or before[field] != after[field]:
            raise ValueError('Fixed native context differs: ' + field)
    for field in ('sites_cart_exact', 'custom_proxy_requests'):
        if field not in before['geometry'] or before['geometry'][field] != after['geometry'].get(field):
            raise ValueError('Fixed native geometry context differs: ' + field)
    mappings = [_mappings(n) for n in (before, after)]
    changed = set(changed_sites)
    if not changed <= mappings[0].keys() or mappings[0].keys() != mappings[1].keys():
        raise ValueError('Changed sites must exist in both exact models')
    for site in mappings[0].keys()-changed:
        if mappings[0][site] != mappings[1][site]:
            raise ValueError('Outside-site definition changed: ' + site)
    kinds = before['geometry']['proxy_details'].keys()
    if kinds != after['geometry']['proxy_details'].keys():
        raise ValueError('Native proxy category inventory differs')
    outside = {}; proxy_changes = {}
    for kind in kinds:
        for n in (before, after):
            rows = n['geometry']['proxy_details'][kind]
            if not isinstance(rows, list) or n['geometry']['proxy_counts'].get(kind) != len(rows):
                raise ValueError('Complete proxy category/count required: ' + kind)
        complete = [_proxy_subset(n, set(), kind) for n in (before, after)]
        proxy_changes[kind] = {
            'removed_or_changed': [json.loads(s) for s in sorted((complete[0]-complete[1]).elements())],
            'added_or_changed': [json.loads(s) for s in sorted((complete[1]-complete[0]).elements())]}
        subsets = [_proxy_subset(n, changed, kind) for n in (before, after)]
        if subsets[0] != subsets[1]:
            raise ValueError('Outside-site proxies changed: ' + kind)
        outside[kind] = sum(subsets[0].values())
    comparisons = {}
    for kind in geometry[0]['measurements']:
        left, right = [_scalar_rows(n, g['measurements'][kind]) for n, g in zip((before, after), geometry)]
        matched = []
        for key in left.keys() & right.keys():
            a, b = left[key], right[key]
            if a['observed'] != b['observed']:
                raise ValueError('Matched scalar geometry differs at fixed coordinates')
            split = {'status': 'UNASSESSED', 'reason': 'Require ranked scalars with unchanged sign convention'}
            if (a['nominal_deviation'] is not None and b['nominal_deviation'] is not None
                    and a.get('both_signs') == b.get('both_signs')):
                split = {'status': 'DESCRIPTIVE_ONLY',
                    'target_only_nominal_at_before_weight': b['difference'] * math.sqrt(a['weight']),
                    'weight_only_nominal_at_before_target': a['difference'] * math.sqrt(b['weight'])}
            matched.append({'endpoints': [list(p) for p in key[0]], 'origin_id': key[1],
                            'before': deepcopy(a), 'after': deepcopy(b),
                            'target_changed': a['target'] != b['target'],
                            'weight_changed': a['weight'] != b['weight'],
                            'convention_changed': a.get('both_signs') != b.get('both_signs'),
                            'target_weight_controls': split})
        comparisons[kind] = {'matched': sorted(matched, key=lambda r: r['before']['proxy_index']),
            'removed': [deepcopy(v) for k, v in left.items() if k not in right],
            'added': [deepcopy(v) for k, v in right.items() if k not in left]}
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW',
        'model_sha256': sha256(model_payload).hexdigest(), 'changed_sites': list(changed_sites),
        'coordinates_unchanged': True, 'topology': topology,
        'outside_site_proxy_counts': outside, 'named_proxy_changes': proxy_changes,
        'site_definitions': {s: {'changed': mappings[0][s] != mappings[1][s],
            'before': deepcopy(mappings[0][s]), 'after': deepcopy(mappings[1][s])} for s in sorted(mappings[0])},
        'scalar_comparisons': comparisons,
        'scalar_summary': {'before': geometry[0]['summary'], 'after': geometry[1]['summary']},
        'deferred_proxy_kinds': {k: {'before': geometry[0]['deferred_proxy_kinds'][k],
            'after': geometry[1]['deferred_proxy_kinds'][k]} for k in geometry[0]['deferred_proxy_kinds']},
        'objective_interpretation': 'DIFFERENT_DEFINITIONS_NOT_AN_OPTIMIZATION_TRAJECTORY',
        'native_execution': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN',
        'chemical_qualification': 'NOT_ESTABLISHED', 'geometry_accepted': False, 'automatic_adoption': False,
        'limitations': [
            'Source graph, H/D, formal charge and linked-state permission require independent qualification.',
            'Missing heavy atoms, including OP3, are observations, never instructions to add atoms.',
            'Changed targets/weights can change deviations without changing geometry.',
            'All captured proxy parameter changes are retained; deferred categories have no scalar/residual comparison.',
            'Target-only and weight-only nominal controls are descriptive, not native energies or chemical proposals.',
            'Nonbonded mechanics are not compared by this report.',
            'Ordered endpoint matching does not infer equivalent permutations or chemical aliases.']}


def inspect_native_target_comparison(before_receipt, after_receipt, model_path, changed_sites,
                                     expected_links, *, na_policy=None, na_phil=None):
    """Bind the diagnostic to two unchanged captures and identical ordered PHIL.

    Dictionary substitutions are recorded by ordered input index and checksum;
    complete source chemistry is deliberately a separate gate.
    """
    model_path = Path(model_path); payload = model_path.read_bytes()
    paths = [Path(p).expanduser().resolve(strict=True) for p in (before_receipt, after_receipt)]
    captured = [_capture(p, payload) for p in paths]
    receipts = [c[0] for c in captured]
    for field in ('phenix_version', 'executable_sha256', 'api_sources',
                  'dictionary_source_policy', 'phil_namespace_policy'):
        if receipts[0].get(field) != receipts[1].get(field):
            raise ValueError('Native capture context differs: ' + field)
    inputs = [r['inputs'] for r in receipts]
    if [(i['role'], i['input_index']) for i in inputs[0]] != [(i['role'], i['input_index']) for i in inputs[1]]:
        raise ValueError('Ordered native inputs differ')
    changes = []
    for a, b in zip(*inputs):
        if (a['sha256'], a['size']) == (b['sha256'], b['size']):
            continue
        if a['role'] != 'dictionary':
            raise ValueError('Only dictionary inputs may change')
        changes.append({'input_index': a['input_index'],
            'before': {k: a[k] for k in ('sha256', 'size')},
            'after': {k: b[k] for k in ('sha256', 'size')}})
    if not changes:
        raise ValueError('Require an explicit dictionary control')
    result = review_native_target_comparison(captured[0][1], captured[1][1], payload,
                changed_sites, expected_links, na_policy=na_policy, na_phil=na_phil)
    result['dictionary_changes'] = changes
    result['receipt_sha256'] = {name: sha256(c[2][p]).hexdigest()
                                for name, p, c in zip(('before', 'after'), paths, captured)}
    if model_path.read_bytes() != payload or any(p.read_bytes() != data for c in captured for p, data in c[2].items()):
        raise ValueError('Target comparison evidence changed during review')
    return result
