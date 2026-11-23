"""Read printed per-cycle X-ray weights; never grant refinement authority.

The qualified format is Phenix 2.2.1-6174's ordinary XYZ summary. A complete
log and a trusted caller-supplied digest are required. Printed values are rounded:
matching them cannot prove identical native objectives or scientific acceptance.
"""
from hashlib import sha256
import math
import re


_CYCLE = re.compile(r'\*+\s*REFINEMENT MACRO_CYCLE ([1-9][0-9]*) OF ([1-9][0-9]*)\s*\*+')
_NUMBER = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?'
_WEIGHTS = re.compile(r'\s*\|\s*wxc\s*=\s*('+_NUMBER+r')\s+wxc_scale\s*=\s*('+_NUMBER+r')\s+wc\s*=\s*('+_NUMBER+r')\s*\|\s*')
_EQUATION = 'XYZ refinement: T = Eexperimental * wxc * wxc_scale + Echem * wc'


def observe_native_xyz_weights(log_bytes, *, expected_log_sha256, expected_cycles):
    """Return one observed XYZ summary per declared cycle from pinned log bytes.

    No paths are resolved, files written, native modules imported or parameters
    changed. Reject partial/concatenated runs, missing/duplicate/out-of-order
    cycles or summaries, unknown objective equations and malformed weights.
    A completion marker is log evidence only, not a verified native-run receipt.
    """
    if type(log_bytes) is not bytes or not 0 < len(log_bytes) <= 64_000_000:
        raise ValueError('Require nonempty bounded native log bytes')
    if (not isinstance(expected_log_sha256, str)
            or not re.fullmatch(r'[0-9a-f]{64}', expected_log_sha256)
            or sha256(log_bytes).hexdigest() != expected_log_sha256):
        raise ValueError('Native log checksum differs or is missing')
    if type(expected_cycles) is not int or not 1 <= expected_cycles <= 1000:
        raise ValueError('Require an explicit bounded native cycle count')
    try:
        lines = log_bytes.decode('utf-8').splitlines()
    except UnicodeError as exc:
        raise ValueError('Require a UTF-8 native log') from exc
    rows = []; cycle = 0; summary = equation = complete = False
    for line_number, line in enumerate(lines, 1):
        match = _CYCLE.fullmatch(line.strip())
        if 'REFINEMENT MACRO_CYCLE' in line:
            if (not match or complete or summary or len(rows) != cycle
                    or int(match[1]) != cycle+1 or int(match[2]) != expected_cycles):
                raise ValueError('Missing, repeated or inconsistent native cycle')
            cycle += 1
        elif line.strip('= ') == 'Compute data/restraints target weights':
            if complete or not cycle or summary or len(rows) == cycle:
                raise ValueError('Unexpected or duplicate native weight summary')
            summary = True; equation = False
        elif 'XYZ refinement: T =' in line:
            if not summary or equation or line.strip().strip('|').strip() != _EQUATION:
                raise ValueError('Unsupported native XYZ objective equation')
            equation = True
        elif re.match(r'\s*\|\s*wxc\b', line):
            match = _WEIGHTS.fullmatch(line)
            if not match or not summary or not equation or complete:
                raise ValueError('Incomplete or malformed native XYZ weight summary')
            printed = dict(zip(('wxc', 'wxc_scale', 'wc'), match.groups()))
            values = {k: float(v) for k, v in printed.items()}
            product = values['wxc'] * values['wxc_scale']
            ratio = product/values['wc'] if values['wc'] else None
            if any(not math.isfinite(v) or v < 0 for v in [*values.values(), product]
                   + ([] if ratio is None else [ratio])):
                raise ValueError('Nonfinite or negative printed native weight')
            rows.append(dict(cycle=cycle, line=line_number, printed=printed,
                **values, printed_data_factor=product,
                printed_data_to_chemistry_ratio=ratio))
            summary = equation = False
        elif line.strip() == 'Job complete':
            if complete or summary or cycle != expected_cycles or len(rows) != expected_cycles:
                raise ValueError('Incomplete or repeated native completion marker')
            complete = True
    if not complete or summary or len(rows) != expected_cycles:
        raise ValueError('Incomplete native weight log')
    return dict(schema_version=1, kind='native-xyz-weight-observation',
        format='phenix-refine-xyz-summary-v1', log_sha256=expected_log_sha256,
        cycles=rows, log_completion_observed=True, rounded_display_values=True,
        identical_printed_weights=len({(r['wxc'], r['wxc_scale'], r['wc']) for r in rows}) == 1,
        native_policy_inferred=False, runtime_authority=False, scientific_acceptance=False,
        limitation='Printed, rounded weights only. A complete log is not a native execution receipt; equal printed weights do not prove equal objectives.')
