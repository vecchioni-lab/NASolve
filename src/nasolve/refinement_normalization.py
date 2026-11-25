"""Exact array states connected only by witnessed native normalization events.

This is not permission to infer a scale from an arbitrary changed target. The
runtime guard owns the pinned native hook, manager identity and ordered indices.
Original sources remain immutable; memory holds one current array capture plus
at most 128 compact event receipts, not target-by-target array snapshots.
"""
from copy import deepcopy
import math

from .refinement_diffraction_observation import DiffractionReference, _require, _validate
from .metal.fdp import audit_reflections
from .metal.xyz import audit_phases
from .refinement_parameter_scope import scope_digest


class NativeScaleWitness:
    def __init__(self, source):
        _require(isinstance(source,DiffractionReference),'Require original diffraction reference')
        self.source=source
        self._original=source.record()
        self._current=deepcopy(self._original['observations'])
        self._order=None
        self._events=[]
        self._multiplier=1.

    @property
    def current(self):
        return deepcopy(self._current)

    def record(self):
        return self.source.record()

    def check_order(self, indices, *, initial=False):
        order=[tuple(h) for h in indices]
        if initial:
            _require(self._order is None,'Native reflection order already bound')
            _require(sorted(order)==[tuple(r[0]) for r in self._current['rows']],
                     'Native reflection inventory differs from source')
            self._order=order
        _require(self._order is not None and order==self._order,
                 'Ordered native reflection indices changed')

    def state(self, observations, phases, *, target):
        _require(target=='mlhl','Require the declared MLHL target')
        _validate(observations,phases)
        audit_phases(self._original['phases'],phases,[tuple(r[0]) for r in observations['rows']])
        _require(observations==self._current,'Unwitnessed native observation state')
        return dict(reference_sha256=scope_digest(self._original),
                    exact_source_values=observations==self._original['observations'],
                    active_observations_sha256=observations['hash'],
                    normalization_events=len(self._events),observations=observations['count'],
                    free_count=observations['free_count'],phases=phases['count'],target=target)

    def record_event(self, before, after, phases_before, phases_after, *, divisor, r_before, r_after):
        _require(self._order is not None,'Native order must be bound before normalization')
        _require(len(self._events)<128,'Native normalization event bound exceeded')
        self.state(before,phases_before,target='mlhl')
        _require(type(divisor) in (int,float) and math.isfinite(divisor) and divisor>0,
                 'Require finite positive witnessed native divisor')
        audit=audit_reflections(before,after,anomalous=False)
        audit_phases(self._original['phases'],phases_after,[tuple(r[0]) for r in after['rows']])
        division=1. if .9<divisor<1.1 else divisor
        _require(all(b[1]==a[1]/division and b[2]==a[2]/division
                     for a,b in zip(before['rows'],after['rows'])),
                 'Arrays differ from the exact witnessed F/sigma division')
        _require(len(r_before)==len(r_after)==2 and all(
            type(x) in (int,float) and type(y) in (int,float)
            and math.isfinite(x) and math.isfinite(y)
            and math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12)
            for x,y in zip(r_before,r_after)),
            'Native normalization changed Rwork or Rfree')
        event=dict(index=len(self._events)+1,computed_divisor=divisor,division=division,
                   input_hash=before['hash'],output_hash=after['hash'],
                   uniform_F_sigma_scale=audit['uniform_F_sigma_scale'],
                   Rwork_before=r_before[0],Rwork_after=r_after[0],
                   Rfree_before=r_before[1],Rfree_after=r_after[1],
                   indices_flags_HL='UNCHANGED',exact_witnessed_division=True)
        self._current=deepcopy(after);self._events.append(event)
        self._multiplier/=division

    def summary(self):
        return deepcopy(dict(policy_id='witnessed-native-common-scale-v1',
            source_reference_sha256=scope_digest(self._original),
            current_observations_sha256=self._current['hash'],
            ordered_indices_sha256=scope_digest(self._order),
            cumulative_F_sigma_multiplier=self._multiplier,events=self._events))
