"""Bounded logical end discovery from declared strands and duplex-core pairs.

No PDB chain boundary, residue-number gap, missing atom or nearest neighbor is
promoted to chemical topology. Coordinate geometry is assessed downstream.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re

from .topostitch_registration import LogicalEndAssignment


@dataclass(frozen=True)
class BackboneStrand:
    """One declared 5'->3' route; boundary meanings are explicit input intent."""
    strand_id: str
    sites: tuple[str, ...]
    five_prime_boundary: str
    three_prime_boundary: str

    def __post_init__(self):
        if not isinstance(self.strand_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', self.strand_id) is None:
            raise ValueError('Invalid strand identifier')
        if (not isinstance(self.sites, (tuple, list)) or not self.sites
                or any(not isinstance(s, str) or re.fullmatch(r'[^:\s]+:[^:\s]+', s) is None for s in self.sites)
                or len(set(self.sites)) != len(self.sites)):
            raise ValueError('Strand sites must be distinct logical identifiers in chemical order')
        for value in (self.five_prime_boundary, self.three_prime_boundary):
            if value not in ('chemical', 'representation', 'unknown'):
                raise ValueError('Strand boundaries must be chemical, representation or unknown')
        object.__setattr__(self, 'sites', tuple(self.sites))


def discover_logical_end_assignments(strands, duplex_pairs, *, copy_id: str,
                                     protected_sites=(), max_overhang_length: int = 12,
                                     pairing_inventory_complete: bool = False, do_not_connect_sites=()):
    """Discover single-stranded chemical-terminal overhangs next to a paired core.

    Each seed core needs at least two consecutive antiparallel paired steps.
    Both outward routes must end at declared chemical boundaries; exactly one
    may have unpaired sites. Internal intervals, route changes and two-tail
    cases remain explicit outcomes, never guessed overhangs. No geometry or
    noncanonical-contact inference is performed by this purely logical step.
    """
    if not isinstance(copy_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', copy_id) is None:
        raise ValueError('Invalid copy identifier')
    if type(pairing_inventory_complete) is not bool:
        raise ValueError('pairing_inventory_complete must be a boolean')
    if type(max_overhang_length) is not int or max_overhang_length < 1:
        raise ValueError('max_overhang_length must be a positive integer')
    routes = list(strands)
    if any(not isinstance(s, BackboneStrand) for s in routes):
        raise ValueError('Expected BackboneStrand records')
    if len({s.strand_id for s in routes}) != len(routes):
        raise ValueError('Duplicate strand identifier')
    routes.sort(key=lambda s: s.strand_id)
    owner = {}
    for strand in routes:
        for i, site in enumerate(strand.sites):
            if site in owner:
                raise ValueError('A logical site cannot belong to multiple strands')
            owner[site] = (strand, i)
    protected = list(protected_sites)
    if any(not isinstance(s, str) or s not in owner for s in protected):
        raise ValueError('Protected sites contain an unknown logical site')
    protected = set(protected)
    free_sites = list(do_not_connect_sites)
    if any(not isinstance(s, str) or s not in owner for s in free_sites):
        raise ValueError('Do-not-connect declarations contain an unknown logical site')
    free_sites = set(free_sites)
    matched_free_sites = set()
    partner, pairs = {}, []
    for pair in duplex_pairs:
        if (not isinstance(pair, (tuple, list)) or len(pair) != 2
                or any(not isinstance(s, str) or s not in owner for s in pair)):
            raise ValueError('Duplex pair contains an unknown logical site')
        a, b = pair
        if a == b or a in partner or b in partner:
            raise ValueError('Each declared core site must have exactly one distinct pairing partner')
        partner[a], partner[b] = b, a
        pairs.append(tuple(sorted(pair)))
    pairs.sort()

    def neighbor(site, direction):
        strand, i = owner[site]
        j = i+direction
        return strand.sites[j] if 0 <= j < len(strand.sites) else None

    def tail(site, direction):
        strand, i = owner[site]
        found, j = [], i+direction
        while 0 <= j < len(strand.sites):
            following = strand.sites[j]
            if following in protected:
                return {'status': 'PROTECTED_JUNCTION', 'sites': found}
            if following in partner:
                return {'status': 'INTERNAL_UNPAIRED_INTERVAL' if found else 'PAIRED_ROUTE_BOUNDARY', 'sites': found}
            if not pairing_inventory_complete:
                return {'status': 'PAIRING_COVERAGE_UNKNOWN', 'sites': found}
            found.append(following)
            if len(found) > max_overhang_length:
                return {'status': 'OVERHANG_LENGTH_LIMIT', 'sites': found}
            j += direction
        boundary = strand.five_prime_boundary if direction == -1 else strand.three_prime_boundary
        return {'status': 'CHEMICAL_TERMINUS' if boundary == 'chemical' else 'UNRESOLVED_BOUNDARY',
                'boundary': boundary, 'sites': list(reversed(found)) if direction == -1 else found}

    assignments, boundaries, isolated = [], [], []
    for a, b in pairs:
        inward = []
        for direction in (-1, 1):
            x, y = neighbor(a, direction), neighbor(b, -direction)
            if x is not None and y is not None and {x, y} != {a, b} and partner.get(x) == y:
                inward.append((direction, x, y))
        if len(inward) == 2:
            continue
        if not inward:
            isolated.append([a, b])
            continue
        direction, ia, ib = inward[0]
        ta, tb = tail(a, -direction), tail(b, direction)
        status = None
        if {a, b, ia, ib} & protected:
            status = 'PROTECTED_JUNCTION'
        else:
            for reason in ('PROTECTED_JUNCTION', 'INTERNAL_UNPAIRED_INTERVAL', 'PAIRED_ROUTE_BOUNDARY',
                           'OVERHANG_LENGTH_LIMIT', 'PAIRING_COVERAGE_UNKNOWN', 'UNRESOLVED_BOUNDARY'):
                if reason in (ta['status'], tb['status']):
                    status = reason
                    break
        if status is None:
            if ta['sites'] and tb['sites']:
                status = 'TWO_UNPAIRED_TAILS'
            elif not ta['sites'] and not tb['sites']:
                status = 'NO_SINGLE_STRAND_OVERHANG'
            else:
                status = 'OVERHANG_FOUND'
        record = {'terminal_pair': [a, b], 'inner_pair': [ia, ib], 'status': status,
                  'outward_routes': [ta, tb], 'end_id': None}
        if status == 'OVERHANG_FOUND':
            overhang, terminal, inner, step = ((ta['sites'], (a,b), (ia,ib), -direction)
                if ta['sites'] else (tb['sites'], (b,a), (ib,ia), direction))
            descriptor = {'copy_id': copy_id, 'overhang_sites': overhang,
                          'terminal_pair': terminal, 'inner_pair': inner,
                          'polarity': '5prime' if step == -1 else '3prime'}
            digest = sha256(json.dumps(descriptor, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            matched = free_sites & (set(overhang) | set(terminal))
            matched_free_sites.update(matched)
            end = LogicalEndAssignment('end_'+digest[:20], state='free' if matched else 'available', **descriptor)
            assignments.append(end)
            record['end_id'] = end.end_id
        boundaries.append(record)
    unanchored = [s.strand_id for s in routes if not any(site in partner for site in s.sites)]
    inputs = json.loads(json.dumps({'copy_id': copy_id, 'strands': [asdict(s) for s in routes],
        'duplex_pairs': pairs, 'protected_sites': sorted(protected), 'max_overhang_length': max_overhang_length,
        'pairing_inventory_complete': pairing_inventory_complete, 'do_not_connect_sites': sorted(free_sites)}))
    complete = (not (free_sites-matched_free_sites) and pairing_inventory_complete and not isolated and not unanchored and all(b['status'] in (
        'OVERHANG_FOUND', 'NO_SINGLE_STRAND_OVERHANG', 'PROTECTED_JUNCTION') for b in boundaries))
    report = {'schema_version': 1, 'kind': 'topostitch-logical-end-discovery',
              'algorithm': 'declared-route-overhang-discovery-v1',
              'topology_source': 'caller_declared_strands_and_duplex_core_pairs',
              'inputs': inputs,
              'input_sha256': sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
              'boundaries': boundaries, 'isolated_pairs': isolated, 'unanchored_strands': unanchored,
              'unmatched_do_not_connect_sites': sorted(free_sites-matched_free_sites),
              'logical_assignments': json.loads(json.dumps([asdict(a) for a in sorted(assignments, key=lambda a: a.end_id)])),
              'coverage_complete': complete, 'geometry_validated': False,
              'runtime_authority': False, 'changes': [],
              'limitations': ['Chemical routes and core pairing are declared, not inferred from PDB labels',
                              'No pair geometry, junction conformation or periodic-cut validation',
                              'No chemistry changes, reconstruction or connection adoption']}
    return tuple(sorted(assignments, key=lambda a: a.end_id)), report


def plan_editable_windows(discovery_report: dict, *, max_base_pairs: int,
                          fixed_anchor_pairs: int = 2) -> dict:
    """Describe whole-pair window expansions; no coordinate motion is attempted.

    The innermost pairs of each proposed window stay fixed. Junctions and
    uncertain routing stop expansion. Physical closure, source mapping and
    overlapping windows need qualification before a geometry trial.
    """
    if (type(max_base_pairs) is not int or type(fixed_anchor_pairs) is not int
            or fixed_anchor_pairs < 1 or max_base_pairs <= fixed_anchor_pairs):
        raise ValueError('Window bounds require positive fixed anchors and at least one movable pair')
    if (not isinstance(discovery_report, dict)
            or discovery_report.get('kind') != 'topostitch-logical-end-discovery'
            or type(discovery_report.get('schema_version')) is not int
            or discovery_report['schema_version'] != 1):
        raise ValueError('Expected a schema-1 logical discovery report')
    try:
        values = discovery_report['inputs']
        routes = [BackboneStrand(**s) for s in values['strands']]
        assignments, replay = discover_logical_end_assignments(routes, values['duplex_pairs'],
            copy_id=values['copy_id'], protected_sites=values['protected_sites'],
            max_overhang_length=values['max_overhang_length'],
            pairing_inventory_complete=values['pairing_inventory_complete'],
            do_not_connect_sites=values.get('do_not_connect_sites', ()))
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed discovery input') from exc
    original_digest = sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if original_digest != discovery_report.get('input_sha256'):
        raise ValueError('Stale discovery input fingerprint')
    normalized = json.loads(json.dumps(discovery_report))
    # The original schema-1 writer predates optional free-site declarations.
    # Interpret only that absent extension as empty, without modifying the input.
    normalized['inputs'].setdefault('do_not_connect_sites', [])
    normalized.setdefault('unmatched_do_not_connect_sites', [])
    normalized['input_sha256'] = sha256(json.dumps(normalized['inputs'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if replay != normalized:
        raise ValueError('Stale or inconsistent discovery report; recompute from declared input')
    owner = {site: (strand, i) for strand in routes for i, site in enumerate(strand.sites)}
    partners = {a: b for pair in values['duplex_pairs'] for a, b in (pair, pair[::-1])}
    protected = set(values['protected_sites'])

    def neighbor(site, step):
        strand, i = owner[site]
        j = i+step
        return strand.sites[j] if 0 <= j < len(strand.sites) else None

    records = []
    for end in assignments:
        if end.state != 'available':
            records.append({'end_id': end.end_id, 'copy_id': end.copy_id,
                            'status': 'EXCLUDED_END_STATE', 'stop_reason': 'DECLARED_'+end.state.upper(),
                            'available_base_pairs': 0, 'windows': []})
            continue
        direction = 1 if neighbor(end.terminal_pair[0], 1) == end.inner_pair[0] else -1
        pairs = [end.terminal_pair]
        while True:
            left, right = pairs[-1]
            a, b = neighbor(left, direction), neighbor(right, -direction)
            if a is None or b is None:
                stop = 'ROUTE_SCOPE_BOUNDARY'
                break
            if {a, b} & protected:
                stop = 'PROTECTED_JUNCTION'
                break
            if partners.get(a) != b or frozenset((a,b)) in {frozenset(p) for p in pairs}:
                stop = 'PAIRING_ROUTE_BOUNDARY'
                break
            if len(pairs) >= max_base_pairs:
                stop = 'PAIR_COUNT_LIMIT'
                break
            pairs.append((a,b))
        windows = []
        for size in range(fixed_anchor_pairs+1, len(pairs)+1):
            selected = pairs[:size]
            moving = selected[:-fixed_anchor_pairs]
            anchors = selected[-fixed_anchor_pairs:]
            value = {'end_id': end.end_id, 'copy_id': end.copy_id,
                     'base_pair_count': size, 'overhang_sites': list(end.overhang_sites),
                     'movable_pairs': [list(p) for p in moving],
                     'fixed_pairs': [list(p) for p in anchors],
                     'movable_sites': list(end.overhang_sites)+[s for p in moving for s in p],
                     'fixed_sites': [s for p in anchors for s in p]}
            digest = sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            value['window_id'] = 'window_'+digest[:20]
            windows.append(value)
        records.append({'end_id': end.end_id, 'copy_id': end.copy_id,
                        'status': 'WINDOWS_FOR_REVIEW' if windows else 'INSUFFICIENT_PAIRED_CONTEXT',
                        'stop_reason': stop, 'available_base_pairs': len(pairs), 'windows': windows})
    return {'schema_version': 1, 'kind': 'topostitch-editable-window-proposals',
            'discovery_sha256': sha256(json.dumps(discovery_report, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'max_base_pairs': max_base_pairs, 'fixed_anchor_pairs': fixed_anchor_pairs,
            'ends': records, 'selected_window': None, 'runtime_authority': False,
            'geometry_feasibility_evaluated': False, 'combined_overlap_checked': False,
            'changes': [], 'limitations': [
                'Logical movement scope only; source coordinate mapping still required',
                'No closure, strain, packing, density or periodic realization qualification',
                'Multiple selected windows require a shared atom/anchor conflict check']}
