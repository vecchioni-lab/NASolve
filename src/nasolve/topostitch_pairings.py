"""Factorized one-partner alternatives over a declared candidate graph.

This is combinatorial capacity analysis, not physical topology adoption. In
particular, special-position atom equivalence is not inferred from end centers.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math

from .topostitch import DuplexEnd
from .topostitch_periodic import _gemmi, _op_key


def _fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _candidate_graph(report):
    kinds = {'topostitch-end-candidate-report', 'topostitch-periodic-candidate-report'}
    if (not isinstance(report, dict) or type(report.get('schema_version')) is not int
            or report['schema_version'] != 1 or report.get('kind') not in kinds
            or report.get('runtime_authority') is not False):
        raise ValueError('Expected a read-only schema-1 TopoStitch candidate report')
    inputs = report.get('inputs')
    if not isinstance(inputs, dict) or _fingerprint(inputs) != report.get('input_sha256'):
        raise ValueError('Candidate input fingerprint mismatch')
    if inputs.get('source_model_sha256') != report.get('source_model_sha256'):
        raise ValueError('Candidate source fingerprint mismatch')
    try:
        rows = [DuplexEnd(**row) for row in inputs['ends']]
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed candidate endpoint inventory') from exc
    if len({e.end_id for e in rows}) != len(rows):
        raise ValueError('Duplicate candidate endpoint identifier')
    ends = {e.end_id: e for e in rows if e.state == 'available' and e.sequence is not None}
    candidates = report.get('candidates')
    if not isinstance(candidates, list):
        raise ValueError('Expected candidate list')
    periodic = report['kind'] == 'topostitch-periodic-candidate-report'
    gemmi = _gemmi() if periodic else None
    edges, deferred, identities = {}, [], set()
    complement = str.maketrans('ACGT', 'TGCA')
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError('Malformed candidate')
        pair = candidate.get('ends')
        if (not isinstance(pair, list) or len(pair) != 2
                or any(not isinstance(e, str) or e not in ends for e in pair)
                or candidate.get('edge_type') != 'base_pairing'):
            raise ValueError('Invalid candidate endpoint or edge type')
        a, b = (ends[e] for e in pair)
        if (a.polarity != b.polarity or a.sequence != b.sequence.translate(complement)[::-1]
                or candidate.get('residue_pairs') != [[j, len(b.sequence)-1-j] for j in range(len(a.sequence))]):
            raise ValueError('Invalid candidate full-overhang register')
        if periodic:
            try:
                if type(candidate['candidate_index']) is not int or candidate['candidate_index'] != i:
                    raise ValueError('Invalid periodic candidate index')
                op = gemmi.Op(candidate['target_image']['operator_xyz'])
                inverse = gemmi.Op(candidate['reciprocal_image']['operator_xyz'])
                if _op_key(op.inverse()) != _op_key(inverse):
                    raise ValueError('Invalid reciprocal candidate operator')
            except (KeyError, TypeError, RuntimeError) as exc:
                raise ValueError('Invalid periodic candidate image') from exc
            image = _op_key(op)
            if a.end_id == b.end_id:
                if op.triplet() == 'x,y,z':
                    raise ValueError('Identity self candidate cannot pair an end to itself')
                if _op_key(op) != _op_key(inverse):
                    deferred.append({'candidate_index': i,
                        'reason': 'SELF_ORBIT_CAPACITY_UNRESOLVED',
                        'detail': 'Forward and inverse images differ; one-partner capacity needs atom-orbit review'})
                    continue
        else:
            if a.end_id == b.end_id:
                raise ValueError('Nonperiodic self candidate is unsupported')
            image = None
        identity = (tuple(pair), image)
        if identity in identities:
            raise ValueError('Duplicate candidate edge')
        identities.add(identity)
        edges[i] = frozenset(pair)
    return sorted(ends), edges, deferred


def describe_pairing_alternatives(candidate_report: dict, *,
                                  max_alternatives_per_component: int = 256,
                                  max_search_states: int = 100_000) -> dict:
    """Enumerate all one-partner matchings in each independent candidate group.

    Includes empty and partial matchings. Never ranks by contact distance or
    treats the most-connected scheme as correct. Output is a factored Cartesian
    product, avoiding exponential expansion across independent components.
    Exceeding either explicit budget raises without a partial success report.
    """
    for value in (max_alternatives_per_component, max_search_states):
        if type(value) is not int or value < 1:
            raise ValueError('Pairing search budgets must be positive integers')
    names, edges, deferred = _candidate_graph(candidate_report)
    incident = {name: [] for name in names}
    for index, ends in edges.items():
        for name in ends:
            incident[name].append(index)
    unseen, components, states = set(names), [], 0
    while unseen:
        first = min(unseen)
        pending, group, indices = [first], set(), set()
        while pending:
            name = pending.pop()
            if name in group:
                continue
            group.add(name)
            unseen.remove(name)
            for index in incident[name]:
                indices.add(index)
                pending.extend(edges[index]-group)
        # Resolve the lexicographically first remaining end either unmatched,
        # or by one incident edge. This visits every matching exactly once.
        stack = [(frozenset(group), ())]
        alternatives = []
        while stack:
            remaining, chosen = stack.pop()
            states += 1
            if states > max_search_states:
                raise ValueError('Pairing search state budget exceeded; no partial alternatives returned')
            if not remaining:
                if len(alternatives) >= max_alternatives_per_component:
                    raise ValueError('Pairing alternative budget exceeded; no partial alternatives returned')
                used = set().union(*(edges[i] for i in chosen)) if chosen else set()
                alternatives.append({'candidate_indices': sorted(chosen),
                                     'unmatched_ends': sorted(group-used)})
                continue
            name = min(remaining)
            stack.append((remaining-{name}, chosen))
            for index in reversed(incident[name]):
                if edges[index] <= remaining:
                    stack.append((remaining-edges[index], chosen+(index,)))
        alternatives.sort(key=lambda a: a['candidate_indices'])
        components.append({'end_ids': sorted(group), 'candidate_indices': sorted(indices),
                           'alternatives': alternatives})
    return {
        'schema_version': 1, 'kind': 'topostitch-pairing-alternatives',
        'algorithm': 'factorized-one-partner-matchings-v1',
        'source_model_sha256': candidate_report['source_model_sha256'],
        'source_bytes_verified': False,
        'candidate_report_sha256': _fingerprint(candidate_report),
        'components': components,
        'scheme_count': math.prod(len(c['alternatives']) for c in components),
        'deferred_candidates': deferred, 'search_states': states,
        'max_alternatives_per_component': max_alternatives_per_component,
        'max_search_states': max_search_states,
        'complete_for_admitted_candidate_graph': True,
        'all_screened_candidates_admitted': not deferred,
        'no_connection_alternative': True, 'selected_scheme': None,
        'physical_orbit_capacity_validated': False,
        'geometry_validated': False, 'runtime_authority': False,
        'inspection_required': True,
        'limitations': [
            'One-partner capacity on supplied end identifiers only; no inferred junction topology',
            'Atom-orbit equivalence and special-position capacity remain unvalidated',
            'Deferred self-image edges remain unresolved, not scientifically rejected',
            'No candidate ranking, partner adoption, construction or checkpoint selection'],
    }
