"""Passive exact merged-observation/HL checks, independent of parameter strategy.

Existing owners admit and independently read original diffraction/phase files.
This module compares their pinned captures with native managers and target arrays;
it discovers no files, installs no callback and starts no refinement. Source hashes
identify bytes, not checkpoint ancestry. Crystal/chemistry and parameter protection
remain separate. Frozen individual-ADP and coordinate-only protocols are unchanged.
"""
from copy import deepcopy
import json
import math
import re
from types import SimpleNamespace

from .metal._diffraction_audit import audit_reflections, audit_phases
from .refinement_parameter_scope import scope_digest

POLICY_ID = 'exact-merged-hl-observation-v1'


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _validate(observations, phases):
    audit_reflections(observations, observations, anomalous=False)
    _require(all(row[1] > 0 for row in observations['rows']),
             'Positive original amplitudes required for this scope')
    audit_phases(phases, phases, [tuple(row[0]) for row in observations['rows']])


def make_reference(*, observations, phases, data_sha256, phases_sha256):
    """Pin independently admitted source captures; permit no amplitude rescaling.

    Captures use existing metal reflection/phase signatures after explicit,
    independently qualified Bijvoet averaging. This function does not average,
    filter or supply missing observations, Free-R flags or phases.
    """
    for value in (data_sha256, phases_sha256):
        _require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value),
                 'Require exact source-data and phase SHA-256 values')
    _validate(observations, phases)
    result=dict(schema_version=1, policy_id=POLICY_ID,
                data_sha256=data_sha256, phases_sha256=phases_sha256,
                observations=observations, phases=phases)
    # Require finite JSON; detach the caller's mutable captures.
    return json.loads(json.dumps(result, allow_nan=False))


class DiffractionReference:
    """Caller-pinned source state; each receipt describes only one observation."""
    def __init__(self, record, *, expected_sha256):
        _require(isinstance(record, dict) and set(record) == {
            'schema_version', 'policy_id', 'data_sha256', 'phases_sha256',
            'observations', 'phases'}, 'Unexpected diffraction-reference fields')
        _require(type(record['schema_version']) is int and record['schema_version'] == 1
                 and record['policy_id'] == POLICY_ID, 'Unsupported diffraction-reference policy')
        rebuilt = make_reference(**{k:v for k,v in record.items()
                                    if k not in ('schema_version','policy_id')})
        _require(scope_digest(rebuilt) == expected_sha256, 'Diffraction-reference checksum mismatch')
        self._record = rebuilt
        self._digest = expected_sha256

    def record(self):
        return deepcopy(self._record)

    def state(self, observations, phases, *, target):
        _require(target == 'mlhl', 'Require the declared MLHL target')
        original = self._record
        _validate(observations, phases)
        audit_reflections(original['observations'], observations, anomalous=False)
        audit_phases(original['phases'], phases,
                     [tuple(row[0]) for row in observations['rows']])
        # The shared frozen-fdp audit allows a common F/sigma scale. This scope
        # intentionally requires the original merged numerical values exactly.
        _require(original['observations'] == observations,
                 'Require exact original merged observations, sigmas and Free-R')
        return dict(reference_sha256=self._digest, exact_source_values=True,
                    observations=observations['count'], free_count=observations['free_count'],
                    phases=phases['count'], target=target)


def _cell_roundoff_policy(value):
    _require(type(value) is int and value in (0, 4),
             'Cell roundoff allowance must be explicitly 0 or 4 ULP')
    return value


def _same_cell(left, right, allowance):
    if allowance == 0:
        return left == right
    return len(left) == len(right) == 6 and all(
        math.isfinite(a) and math.isfinite(b)
        and abs(a-b) <= allowance * max(math.ulp(a), math.ulp(b))
        for a, b in zip(left, right))


def _capture(fo, flags, hl, *, cell_roundoff_ulps=0):
    allowance = _cell_roundoff_policy(cell_roundoff_ulps)
    _require(fo is not None and flags is not None and hl is not None,
             'Missing native observations, Free-R or HL')
    _require(list(fo.indices()) == list(flags.indices()) == list(hl.indices()),
             'Native diffraction arrays must be index-aligned')
    _require(not flags.anomalous_flag() and not hl.anomalous_flag()
             and hl.is_hendrickson_lattman_array(), 'Require merged Free-R and HL arrays')
    _require(fo.is_xray_amplitude_array() and fo.sigmas() is not None,
             'Require native amplitudes with sigmas')
    _require(all(type(value) is bool for value in flags.data()),
             'Native Free-R assignments must be boolean membership')
    _require(all(array.space_group() == fo.space_group()
                 and _same_cell(array.unit_cell().parameters(), fo.unit_cell().parameters(), allowance)
                 for array in (flags, hl)), 'Native diffraction crystal frames differ')
    from .metal._xyz_native import reflection_signature, phase_signature
    holder=SimpleNamespace(f_obs=lambda:fo, r_free_flags=lambda:flags)
    # Existing signature owners sort rows; alignment is checked above first.
    return json.loads(json.dumps([reflection_signature(holder), phase_signature(hl)],
                                 allow_nan=False))


def observe_diffraction(reference, fmodel, *, cell_roundoff_ulps=0):
    """Observe the active manager; caller retains native-source/version binding."""
    captures=_capture(fmodel.f_obs(), fmodel.r_free_flags(), fmodel.hl_coeffs(),
                      cell_roundoff_ulps=cell_roundoff_ulps)
    return reference.state(*captures, target=fmodel.target_name)


def observe_target(reference, fmodel, functor, *, cell_roundoff_ulps=0):
    """Observe actual target arrays for XYZ or group B without broadening either."""
    _require(functor.manager is fmodel, 'Target owns a different diffraction manager')
    observe_diffraction(reference, fmodel, cell_roundoff_ulps=cell_roundoff_ulps)
    core=functor.core
    _require(getattr(core,'spacialization',None) == 'hl', 'Target is not HL-specialized')
    captures=_capture(getattr(core,'f_obs',None), getattr(core,'r_free_flags',None),
                      getattr(core,'experimental_phases',None),
                      cell_roundoff_ulps=cell_roundoff_ulps)
    return reference.state(*captures, target=fmodel.target_name)
