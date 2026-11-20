"""Exact declared chemical links, with explicitly bound NAR soft restraints.

A declaration is supplied authority, not proof of its author's provenance.
No recipe is regenerated, chemical graph guessed, or origin ID broadly exempted.
"""
from collections import Counter
from copy import deepcopy
from math import isfinite

from .cif_attachment_native import _links, _native_atoms
from .cif_na_policy import POLICY_ID as NA_POLICY_ID, _requests, _parse, _path

POLICY_ID = 'cif-declared-native-topology-v1'
_ORIGINS = {'hydrogen bonds', 'edits', 'basepair stacking', 'basepair parallelity', 'basepair planarity'}


def _edge(endpoints):
    return tuple(sorted(tuple(e) for e in endpoints))


def _declared(expected, keys):
    edges = []
    for row in expected:
        ends = [(e['site'], e['component'], e['atom_id']) for e in row['endpoints']]
        if len(ends) != 2 or ends[0][0] == ends[1][0] or any(e not in keys for e in ends):
            raise ValueError('Declared chemical link has absent or same-site endpoints')
        edges.append(_edge(ends))
    if not edges or len(set(edges)) != len(edges):
        raise ValueError('Require a nonempty unambiguous declared chemical topology')
    return Counter(edges)


def _soft(native, keys, links, expected, policy, phil):
    if policy is None and phil is None:
        return []
    if not isinstance(policy, dict) or not isinstance(phil, str):
        raise ValueError('NARestraints policy and compiled PHIL must be supplied together')
    if (type(policy.get('schema_version')) is not int or policy['schema_version'] != 1
            or policy.get('policy_id') != NA_POLICY_ID or policy.get('policy_authority') != 'NARestraints'
            or policy.get('automatic_adoption') is not False):
        raise ValueError('Require a frozen explicit NARestraints policy declaration')
    nodes, _ = _parse(phil)
    scopes = {'refinement', 'geometry_restraints.edits', 'pdb_interpretation.secondary_structure'}
    for node in nodes:
        path = _path(node)
        kind = path.removeprefix('geometry_restraints.edits.')
        fields = node['fields']
        if path in scopes:
            allowed = {'enabled'} if path == 'pdb_interpretation.secondary_structure' else set()
            if set(fields) - allowed or (allowed and fields.get('enabled') != 'False'):
                raise ValueError('Unsupported compiled NARestraints policy control')
        elif kind in {'bond','angle','parallelity'}:
            target = {'bond':'distance_ideal','angle':'angle_ideal','parallelity':'target_angle_deg'}[kind]
            allowed = {'action','sigma',target,'atom_selection_1','atom_selection_2'} | ({'atom_selection_3'} if kind == 'angle' else set())
            if set(fields) - allowed or fields.get('action','add') != 'add':
                raise ValueError('Unsupported compiled NARestraints action or setting')
        else:
            raise ValueError('Unsupported compiled NARestraints PHIL scope')
    requests = _requests(phil, native['atoms'])
    if requests != policy.get('compiled_requests') or not requests:
        raise ValueError('NARestraints compiled PHIL differs from policy requests')
    detail = native.get('restraint_policy', {}); origins = detail.get('origin_ids', {})
    if (set(origins) != _ORIGINS or any(type(v) is not int for v in origins.values())
            or len(set(origins.values())) != len(origins) or detail.get('secondary_structure_enabled') is not False):
        raise ValueError('Require explicit native edit origin and disabled competing secondary structure')
    pairs = set()
    for relationship in policy['relationships']:
        if relationship['kind'] != 'base_pair':
            continue
        sites = relationship['sites']
        if (len(sites) != 2 or len(set(sites)) != 2
                or relationship['provenance'] != 'FROZEN_EXPLICIT_DECLARATION_COMPILED_BY_NARESTRAINTS'):
            raise ValueError('Ambiguous NARestraints pair declaration')
        pairs.add(tuple(sorted(sites)))
    soft = []; seen = set()
    for q in requests:
        if native['geometry']['custom_proxy_requests'].count(q) != 1:
            raise ValueError('Compiled NARestraints request must occur exactly once in native readback')
        if q['kind'] != 'bond':
            continue
        ends = [keys[i] for i in q['i_seqs']]; edge = _edge(ends)
        if (q['action'] != 'add' or len(ends) != 2 or edge in seen or edge in expected
                or tuple(sorted(e[0] for e in ends)) not in pairs
                or any(native['atoms'][i]['element'].strip().upper() not in {'N', 'O'} for i in q['i_seqs'])
                or any(type(q[k]) not in (int, float) or not isfinite(q[k]) or q[k] <= 0
                       for k in ('distance_ideal', 'weight'))):
            raise ValueError('Soft bond conflicts with declared chemical topology or pairing authority')
        seen.add(edge)
        matches = [r for r in links if _edge(r['endpoints']) == edge]
        if (len(matches) != 1 or type(matches[0]['origin_id']) is not int or matches[0]['origin_id'] != origins['edits']
                or any(matches[0][k] != q[k] for k in ('distance_ideal', 'weight'))):
            raise ValueError('Declared NARestraints soft bond has no unique exact native realization')
        soft.append(matches[0])
    return soft


def _coordination(native, keys, labels, expected, soft, declarations):
    """Validate supplied typed coordination bonds without trusting origin alone."""
    if declarations is None:
        return []
    if not isinstance(declarations, list) or not declarations:
        raise ValueError('Require explicit nonempty coordination bond declarations')
    origins = native.get('restraint_policy', {}).get('origin_ids', {})
    if (set(origins) != _ORIGINS or any(type(v) is not int or v < 0 for v in origins.values())
            or len(set(origins.values())) != len(origins)):
        raise ValueError('Require unambiguous captured restraint origins')
    geometry = native['geometry']
    proxies = geometry['simple_bonds'] + geometry['asu_bonds']
    requests = geometry.get('custom_proxy_requests', [])
    seen = set(); term_ids = set(); result = []
    for row in declarations:
        if (not isinstance(row, dict)
                or set(row) != {'kind', 'term_id', 'roles', 'origin_id', 'endpoints', 'request'}
                or row['kind'] != 'metal_coordination'
                or not isinstance(row['term_id'], str) or not row['term_id']
                or row['term_id'] in term_ids
                or not isinstance(row['roles'], list) or len(row['roles']) != 2
                or 'metal' not in row['roles'] or any(r not in {'metal', 'donor', 'atom'} for r in row['roles'])
                or type(row['origin_id']) is not int or row['origin_id'] != origins['edits']):
            raise ValueError('Unsupported or ambiguous coordination bond authority')
        q = row['request']
        if (not isinstance(q, dict) or set(q) != {'kind', 'action', 'atoms', 'i_seqs',
                'selections', 'distance_ideal', 'weight'}
                or q['kind'] != 'bond' or q['action'] != 'add'
                or not isinstance(q['i_seqs'], list) or len(q['i_seqs']) != 2
                or any(type(i) is not int or not 0 <= i < len(keys) for i in q['i_seqs'])
                or len(set(q['i_seqs'])) != 2
                or q['atoms'] != [labels[i] for i in q['i_seqs']]
                or row['endpoints'] != [list(keys[i]) for i in q['i_seqs']]
                or not isinstance(q['selections'], list) or len(q['selections']) != 2
                or any(not isinstance(s, str) or not s.strip() for s in q['selections'])
                or any(type(q[k]) not in (int, float) or not isfinite(q[k]) or q[k] <= 0
                       for k in ('distance_ideal', 'weight'))):
            raise ValueError('Malformed coordination bond request or endpoint binding')
        edge = _edge(row['endpoints'])
        if edge in expected or edge in seen or any(_edge(s['endpoints']) == edge for s in soft):
            raise ValueError('Coordination bond overlaps another declared authority')
        matching_requests = [r for r in requests if r.get('kind') == 'bond'
                             and sorted(r.get('i_seqs', [])) == sorted(q['i_seqs'])]
        if (len(matching_requests) != 1 or matching_requests[0] != q
                or any(type(i) is not int for i in matching_requests[0]['i_seqs'])
                or any(type(matching_requests[0][k]) not in (int, float)
                       for k in ('distance_ideal', 'weight'))):
            raise ValueError('Coordination request must occur exactly once in native readback')
        matches = [p for p in proxies if sorted(p['i_seqs']) == sorted(q['i_seqs'])]
        if (len(matches) != 1 or matches[0] not in geometry['simple_bonds']
                or matches[0].get('symmetry_operation') not in (None, 'x,y,z')
                or type(matches[0].get('origin_id')) is not int
                or matches[0]['origin_id'] != row['origin_id']
                or any(type(matches[0].get(k)) not in (int, float) or matches[0][k] != q[k]
                       for k in ('distance_ideal', 'weight'))):
            raise ValueError('Coordination bond has no unique exact native realization')
        seen.add(edge); term_ids.add(row['term_id'])
        result.append(dict(deepcopy(row), native_bond=deepcopy(matches[0])))
    return result


def review_native_topology(native, model_payload, expected, *, na_policy=None, na_phil=None,
                           coordination_bonds=None):
    """Compare every cross-site bond to supplied source-bound declarations.

    Callers bind source chemistry and capture integrity. This shared layer reuses
    C109 atom/coordinate/proxy validation and verifies explicit soft membership.
    Frozen PHIL and policy are declarations, not fresh recipe/library approval.
    Optional typed coordination bonds require unique exact requests and native
    realizations. Their source authority is caller-supplied, never inferred from
    elements or origins. This does not review coordination angles or geometry.
    """
    try:
        keys, labels = _native_atoms(native, model_payload)
        declared = _declared(expected, keys)
        links, symmetry = _links(native, keys, labels, {e[0] for e in keys})
        soft = _soft(native, keys, links, declared, na_policy, na_phil)
        coordination = _coordination(native, keys, labels, declared, soft, coordination_bonds)
        coordination_edges = {_edge(r['endpoints']) for r in coordination}
        chemical = [r for r in links if r not in soft and _edge(r['endpoints']) not in coordination_edges]
        observed = Counter(_edge(r['endpoints']) for r in chemical)
        match = observed == declared and not symmetry
        result = {'schema_version':1, 'policy_id':POLICY_ID, 'status':'REVIEW',
                'link_status':'MATCH' if match else 'REVIEW', 'links':chemical,
                'declared_links':[[list(p) for p in e] for e in declared.elements()],
                'missing_links':[[list(p) for p in e] for e in (declared-observed).elements()],
                'unexpected_links':[[list(p) for p in e] for e in (observed-declared).elements()],
                'symmetry_bonds_touching_selected_sites':symmetry, 'soft_restraints':soft,
                'soft_restraint_authority':'FROZEN_EXPLICIT_NARESTRAINTS_DECLARATION' if na_policy is not None else 'NONE',
                'chemical_qualification':'NOT_ESTABLISHED', 'geometry_acceptance':'NOT_ASSESSED',
                'automatic_adoption':False}
        if coordination_bonds is not None:
            result.update(schema_version=2, policy_id='cif-declared-coordination-topology-v1',
                coordination_restraints=coordination,
                coordination_restraint_authority='EXPLICIT_CALLER_BOUND_METAL_RECIPE',
                coordination_angles='NOT_ASSESSED')
        return result
    except (KeyError, TypeError, IndexError, AttributeError, ArithmeticError) as exc:
        raise ValueError('Malformed topology evidence: ' + str(exc)) from exc
