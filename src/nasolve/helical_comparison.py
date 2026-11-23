"""Compare explicitly corresponding pairs in two byte-pinned model states.

This composes the shared measurement readers. Correspondence and strand roles
are caller declarations, never inferred from nearby coordinates or numbering.
No alignment, coordinate movement, curvature measurement or acceptance follows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import re

from .helical_geometry import PairedRegion, _label, inspect_phosphate_spans
from .topostitch_recipe import recipe_digest

METHOD = 'declared-helical-state-comparison-v1'


@dataclass(frozen=True)
class HelicalState:
    name: str
    model_path: Path
    region: PairedRegion
    expected_model_sha256: str

    def __post_init__(self):
        _label(self.name, 'state name')
        if not isinstance(self.region, PairedRegion):
            raise ValueError('Each state requires an explicit PairedRegion')
        if not isinstance(self.expected_model_sha256, str) or re.fullmatch('[0-9a-f]{64}', self.expected_model_sha256) is None:
            raise ValueError('Each state requires a lowercase model SHA256')
        object.__setattr__(self, 'model_path', Path(self.model_path))


@dataclass(frozen=True)
class PairCorrespondence:
    logical_pair_id: str
    reference_pair_id: str | None
    candidate_pair_id: str | None

    def __post_init__(self):
        _label(self.logical_pair_id, 'logical_pair_id')
        for value in (self.reference_pair_id, self.candidate_pair_id):
            if value is not None:
                _label(value, 'state pair_id')
        if self.reference_pair_id is None and self.candidate_pair_id is None:
            raise ValueError('A correspondence must identify at least one state pair')


def _validate_correspondence(reference, candidate, rows):
    if not isinstance(rows, (list, tuple)) or not rows or any(not isinstance(r, PairCorrespondence) for r in rows):
        raise ValueError('Require explicit PairCorrespondence records')
    if len({r.logical_pair_id for r in rows}) != len(rows):
        raise ValueError('Logical correspondence IDs must be unique')
    for state, attr in ((reference, 'reference_pair_id'), (candidate, 'candidate_pair_id')):
        ids = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
        known = {p.pair_id for p in state.region.pairs}
        if len(set(ids)) != len(ids):
            raise ValueError('A state pair cannot be reused by multiple correspondences')
        if set(ids) != known:
            raise ValueError('Correspondence must cover every declared state pair exactly once; use None for an unmatched mate')


def _delta(first, second, key, *, units, absent, angular=False):
    result = {'status': 'UNAVAILABLE', 'reason': None, 'units': units,
              'reference_value': None, 'candidate_value': None, 'delta': None}
    for label, row in (('reference', first), ('candidate', second)):
        result[label+'_status'] = row['status'] if row is not None else 'UNMAPPED'
        result[label+'_reason'] = row.get('reason') if row is not None else label.upper()+'_'+absent
        if row is not None:
            result[label+'_value'] = row.get(key)
    for label, row in (('reference', first), ('candidate', second)):
        if row is None:
            return {**result, 'reason': label.upper()+'_'+absent}
        if row['status'] != 'MEASURED':
            return {**result, 'reason': label.upper()+'_MEASUREMENT_UNAVAILABLE'}
    delta = second[key]-first[key]
    if angular:
        delta = (delta+180) % 360-180
        if abs(abs(delta)-180) <= 1e-8:
            return {**result, 'reason': 'AMBIGUOUS_ANGLE_DELTA'}
    return {**result, 'status': 'MEASURED', 'delta': delta}


_STACKING_METRICS = ('plane_angle_deg', 'centroid_distance_angstrom',
                     'normal_spacing_angstrom', 'lateral_offset_angstrom')


def _stacking_delta(first, second, key):
    # Per-metric availability matters: perpendicular planes still supply an
    # angle and centroid distance, even though their mean normal is ambiguous.
    def metric(row):
        if row is None or row[key] is None:
            return row
        return {**row, 'status': 'MEASURED', 'reason': None}
    return _delta(metric(first), metric(second), key,
                  units='degree' if key=='plane_angle_deg' else 'angstrom',
                  absent='ADJACENT_STEP_UNMAPPED')


def compare_helical_states(reference, candidate, *, correspondence,
                           strand_correspondence, simple_twist=False,
                           max_ring_fit_rmsd_angstrom=None, include_half_span=False,
                           include_stacking=False):
    """Return candidate-minus-reference changes without inferring site identity.

    Require explicit I-to-I/II-to-II strand correspondence and complete pair
    accounting, including None for unmatched mates. Reversed or missing adjacency
    has no comparable step. Both states use the same measurement options.
    Optional simple twist requires the existing topology extra and explicit fit
    limit. include_stacking explicitly requires simple_twist=True and compares
    the same fitted frames, preserving independent strand/metric availability.
    State-scoped source anchors retain exact filenames/hashes on relocation.
    """
    if not isinstance(reference, HelicalState) or not isinstance(candidate, HelicalState):
        raise ValueError('Require two explicit HelicalState records')
    if reference.name == candidate.name:
        raise ValueError('State names must be distinct')
    if strand_correspondence != 'I_TO_I_II_TO_II':
        raise ValueError('Explicit I_TO_I_II_TO_II strand correspondence is required; no strand-direction inference')
    if any(type(value) is not bool for value in (simple_twist, include_half_span, include_stacking)):
        raise ValueError('Measurement options must be boolean')
    if include_stacking and not simple_twist:
        raise ValueError('Stacking comparison requires simple_twist=True and an explicit ring-fit policy')
    if not simple_twist and max_ring_fit_rmsd_angstrom is not None:
        raise ValueError('Ring-fit limit requires simple_twist=True')
    _validate_correspondence(reference, candidate, correspondence)
    reports = []
    for state in (reference, candidate):
        kwargs = dict(expected_model_sha256=state.expected_model_sha256,
                      include_half_span=include_half_span)
        if simple_twist:
            from .helical_twist import inspect_helical_region
            report = inspect_helical_region(state.model_path, state.region,
                max_ring_fit_rmsd_angstrom=max_ring_fit_rmsd_angstrom,
                include_stacking=include_stacking, **kwargs)
        else:
            report = inspect_phosphate_spans(state.model_path, state.region, **kwargs)
        reports.append(report)
    # Recheck both inputs after all measurements. No filesystem lock is claimed.
    for state in (reference, candidate):
        if sha256(state.model_path.read_bytes()).hexdigest() != state.expected_model_sha256:
            raise ValueError('State model bytes changed during comparison')
    pair_maps = [{p['pair_id']: p for p in r['pairs']} for r in reports]
    declarations = [{p.pair_id: p for p in s.region.pairs} for s in (reference, candidate)]
    pairs = []
    for row in correspondence:
        a, b = pair_maps[0].get(row.reference_pair_id), pair_maps[1].get(row.candidate_pair_id)
        da, db = declarations[0].get(row.reference_pair_id), declarations[1].get(row.candidate_pair_id)
        item = {**asdict(row), 'correspondence_status': 'DECLARED' if da and db else 'UNRESOLVED',
                'component_changes': None if da is None or db is None else [strand for strand in ('strand_i', 'strand_ii') if getattr(da,strand).component != getattr(db,strand).component],
                'role_changed': None if da is None or db is None else da.role != db.role,
                'phosphate_span': _delta(a,b,'distance_angstrom',units='angstrom',absent='PAIR_UNMAPPED')}
        if include_half_span:
            item['half_span'] = _delta(a,b,'half_span_angstrom',units='angstrom',absent='PAIR_UNMAPPED')
        pairs.append(item)
    # Enumerate actual declared adjacency in each state, never compress away a
    # missing pair or infer direction for reversed/reordered correspondences.
    step_maps = []
    stacking_maps = []
    for report, attr in zip(reports, ('reference_pair_id', 'candidate_pair_id')):
        logical = {getattr(r,attr): r.logical_pair_id for r in correspondence if getattr(r,attr) is not None}
        observed = report['simple_step_twist'].get('steps')
        if observed is None:
            ids = [p['pair_id'] for p in report['pairs']]
            observed = [dict(pair_ids=[a,b],status='NOT_MEASURED',reason='SIMPLE_TWIST_NOT_REQUESTED') for a,b in zip(ids,ids[1:])]
        step_maps.append({tuple(logical[p] for p in step['pair_ids']):step for step in observed})
        if include_stacking:
            stacking_maps.append({tuple(logical[p] for p in step['pair_ids']):step
                                  for step in report['stacking_geometry']['steps']})
    keys = list(dict.fromkeys([*step_maps[0], *step_maps[1]]))
    steps = [{'logical_pair_ids':list(key), 'simple_step_twist': _delta(
        step_maps[0].get(key),step_maps[1].get(key),'twist_deg',units='degree',
        absent='ADJACENT_STEP_UNMAPPED',angular=True)} for key in keys]
    if include_stacking:
        for item, key in zip(steps, keys):
            a, b = (mapping.get(key) for mapping in stacking_maps)
            item['stacking_geometry'] = [dict(strand=strand, **{
                metric: _stacking_delta(a['strands'][i] if a else None,
                                        b['strands'][i] if b else None, metric)
                for metric in _STACKING_METRICS})
                for i, strand in enumerate(('strand_i', 'strand_ii'))]
    manifest = [asdict(r) for r in correspondence]
    result = dict(schema_version=1, kind='helical-state-comparison', method=METHOD,
        state_names={'reference':reference.name,'candidate':candidate.name},
        states={'reference':reports[0],'candidate':reports[1]},
        source_anchor_scope='Each embedded state owns its model_directory anchor',
        correspondence=manifest, correspondence_sha256=recipe_digest(manifest),
        strand_correspondence=strand_correspondence, correspondence_authority='CALLER_DECLARED',
        physical_correspondence_validated=False, pairing_validated=False,
        delta_convention='candidate minus reference; angles wrapped to (-180,180), exact half-turn unavailable',
        pairs=pairs, steps=steps,
        coverage={'declared_correspondences':len(pairs),
                  'matched_pairs':sum(p['correspondence_status']=='DECLARED' for p in pairs),
                  'measured_span_changes':sum(p['phosphate_span']['status']=='MEASURED' for p in pairs),
                  'declared_step_union':len(steps),
                  'measured_twist_changes':sum(s['simple_step_twist']['status']=='MEASURED' for s in steps)},
        axis_radii={'status':'NOT_MEASURED'}, helix_bending={'status':'NOT_MEASURED'},
        runtime_authority=False, coordinate_changes=False)
    if include_stacking:
        result['stacking_delta_convention'] = 'Candidate minus reference without angular wrapping; acute unoriented plane angle is not a signed bend'
        result['coverage']['stacking_changes'] = {
            metric: sum(row[metric]['status']=='MEASURED' for step in steps
                        for row in step['stacking_geometry']) for metric in _STACKING_METRICS}
    return result
