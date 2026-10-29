"""Passive native fit readback and deterministic, offline scale diagnostics.

This module is also imported directly by phenix.python workers: stdlib only.
It never fits atomic parameters, removes observations or selects a solution.
"""
import hashlib
import math
from pathlib import Path
import re

PROTOCOL = 'metal-fit-diagnostics-v1'


def capture(fmodel):
    """Read the active final Fmodel, preserving complex amplitudes and indices."""
    calculated = fmodel.f_model()
    observed = fmodel.f_obs()
    if list(calculated.indices()) != list(observed.indices()):
        raise ValueError('Diagnostic calculated/observed indices differ')
    rows = sorted([list(h), float(d), float(z.real), float(z.imag)]
                  for h, d, z in zip(calculated.indices(), observed.d_spacings().data(), calculated.data()))
    return dict(protocol=PROTOCOL, implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                rows=rows, work_scale=fmodel.scale_k1_w(), free_scale=fmodel.scale_k1_t())


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError('Invalid fit diagnostic number')
    return float(value)


def _ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else None


def _partition(rows, scale, native_r):
    if scale is not None and _number(scale) < 0:
        raise ValueError('Invalid native fit scale')
    if not rows:
        if native_r is not None:
            raise ValueError('Nonempty native R for empty partition')
        return dict(count=0, r_native=None, scale=scale, highest_scale_leverage=[], largest_residuals=[])
    scale = _number(scale)
    den = math.fsum(r['fo'] for r in rows)
    residual = math.fsum(abs(r['fo'] - scale*r['fc']) for r in rows)
    r_value = _ratio(residual, den)
    if r_value is None or not math.isclose(r_value, _number(native_r), rel_tol=1e-7, abs_tol=1e-9):
        raise ValueError('Captured Fmodel does not reproduce native R')
    groups = {}
    for row in rows:
        h = tuple(row['hkl'])
        # Group exact Friedel mates for sensitivity only. Never merge observations.
        key = min(h, tuple(-v for v in h))
        groups.setdefault(key, []).append(row)
    fc2 = math.fsum(r['fc']**2 for r in rows)
    entries = []
    for key, members in groups.items():
        term = math.fsum(r['fc']**2 for r in members)
        error = math.fsum(abs(r['fo'] - scale*r['fc']) for r in members)
        entries.append(dict(indices=[r['hkl'] for r in members],
            d_range_A=[min(r['d'] for r in members), max(r['d'] for r in members)],
            observed_amplitudes=[r['fo'] for r in members],
            calculated_amplitudes=[r['fc'] for r in members],
            absolute_residual=error, residual_fraction=_ratio(error, residual),
            scale_denominator_fraction=_ratio(term, fc2), _key=key, _term=term))
    leverage = sorted(entries, key=lambda e: (-e['_term'], e['_key']))[:5]
    largest = sorted(entries, key=lambda e: (-e['absolute_residual'], e['_key']))[:5]
    def public(e):
        return {k:v for k,v in e.items() if not k.startswith('_')}
    top = []
    for entry in leverage:
        keys = {tuple(h) for h in entry['indices']}
        remaining = [r for r in rows if tuple(r['hkl']) not in keys]
        k = _ratio(math.fsum(r['fo']*r['fc'] for r in remaining), math.fsum(r['fc']**2 for r in remaining))
        rr = None if k is None else _ratio(math.fsum(abs(r['fo']-k*r['fc']) for r in remaining), math.fsum(r['fo'] for r in remaining))
        top.append(dict(public(entry), remaining_scalar_sensitivity=dict(count=len(remaining), scale=k, r=rr,
            used_for_refinement=False, interpretation='diagnostic_only_not_replacement_R_or_exclusion_advice')))
    return dict(count=len(rows), r_native=native_r, scale=scale, sum_observed_amplitudes=den,
                sum_absolute_residual=residual, highest_scale_leverage=top,
                largest_residuals=[public(e) for e in largest])


def summarize(evidence, reflections, r_work, r_free):
    """Reproduce reported R, then expose scalar leverage without editing data."""
    if (evidence['protocol'] != PROTOCOL
            or not isinstance(evidence['implementation_sha256'], str)
            or re.fullmatch('[a-f0-9]{64}', evidence['implementation_sha256']) is None):
        raise ValueError('Unsupported fit diagnostic protocol/source')
    source = reflections['rows']
    captured = evidence['rows']
    if not isinstance(captured, list) or not captured or len(source) != len(captured):
        raise ValueError('Incomplete fit diagnostic inventory')
    keys = []; partitions = {False:[], True:[]}
    for row, observed in zip(captured, source):
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError('Invalid calculated row')
        h, d, real, imag = row
        if (not isinstance(h, list) or len(h) != 3 or any(type(v) is not int for v in h)
                or h != observed[0] or type(observed[3]) is not bool):
            raise ValueError('Fit diagnostic indices/flags changed')
        d = _number(d)
        if d <= 0:
            raise ValueError('Invalid reflection spacing')
        fo = _number(observed[1])
        if fo < 0:
            raise ValueError('Negative observed amplitude')
        partitions[observed[3]].append(dict(hkl=h, d=d, fo=fo, fc=math.hypot(_number(real), _number(imag))))
        keys.append(tuple(h))
    if keys != sorted(set(keys)):
        raise ValueError('Duplicated or unordered fit diagnostic indices')
    return dict(protocol=PROTOCOL, implementation_sha256=evidence['implementation_sha256'],
                work=_partition(partitions[False], evidence['work_scale'], r_work),
                free=_partition(partitions[True], evidence['free_scale'], r_free),
                observation_policy='all_captured_observations_retained', automatic_exclusion=False,
                scientific_acceptance='NOT_ASSESSED',
                limitation='Scalar sensitivity only; no atomic refit, independent validation, or data-rejection decision')
