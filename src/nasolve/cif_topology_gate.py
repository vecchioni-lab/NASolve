"""Exact declared chemical links, with explicitly bound NAR soft restraints.

A declaration is supplied authority, not proof of its author's provenance.
No recipe is regenerated, chemical graph guessed, or origin ID broadly exempted.
"""
from collections import Counter
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


def review_native_topology(native, model_payload, expected, *, na_policy=None, na_phil=None):
    """Compare every cross-site bond to supplied source-bound declarations.

    Callers bind source chemistry and capture integrity. This shared layer reuses
    C109 atom/coordinate/proxy validation and verifies explicit soft membership.
    Frozen PHIL and policy are declarations, not fresh recipe/library approval.
    """
    try:
        keys, labels = _native_atoms(native, model_payload)
        declared = _declared(expected, keys)
        links, symmetry = _links(native, keys, labels, {e[0] for e in keys})
        soft = _soft(native, keys, links, declared, na_policy, na_phil)
        chemical = [r for r in links if r not in soft]
        observed = Counter(_edge(r['endpoints']) for r in chemical)
        match = observed == declared and not symmetry
        return {'schema_version':1, 'policy_id':POLICY_ID, 'status':'REVIEW',
                'link_status':'MATCH' if match else 'REVIEW', 'links':chemical,
                'declared_links':[[list(p) for p in e] for e in declared.elements()],
                'missing_links':[[list(p) for p in e] for e in (declared-observed).elements()],
                'unexpected_links':[[list(p) for p in e] for e in (observed-declared).elements()],
                'symmetry_bonds_touching_selected_sites':symmetry, 'soft_restraints':soft,
                'soft_restraint_authority':'FROZEN_EXPLICIT_NARESTRAINTS_DECLARATION' if na_policy is not None else 'NONE',
                'chemical_qualification':'NOT_ESTABLISHED', 'geometry_acceptance':'NOT_ASSESSED',
                'automatic_adoption':False}
    except (KeyError, TypeError, IndexError, AttributeError, ArithmeticError) as exc:
        raise ValueError('Malformed topology evidence: ' + str(exc)) from exc
