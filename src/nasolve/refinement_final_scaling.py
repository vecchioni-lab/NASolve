"""Read printed final-scaling evidence without changing or accepting a model.

Qualified against the four-stage Phenix 2.2.1-6174 log format. This does not
replay a native calculation, authenticate the producer, infer Free-R membership,
or replace autorefine's final statistics parser. Missing evidence remains absent.
"""
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import math
import re

MAX_LOG_BYTES = 16 * 1024 * 1024
_FINAL = re.compile(r'^=+\s+Final\s+=+$')
_ROW = re.compile(
    r'^(start|re-set all scales|overall B=(\S+) to atoms|bulk-solvent and scaling):\s*'
    r'r\(all,work,free\)=(\S+)\s+(\S+)\s+(\S+)\s+n_refl\.:\s*(\S+)\s*$')
_NAMES = ('before_scaling', 'scales_reset', 'b_transferred', 'solvent_scaled')
_PREFIXES = ('start:', 're-set all scales:', 'overall B=', 'bulk-solvent and scaling:')
_LIMITS = (
    'Printed log evidence only; not native replay or model authentication.',
    'Final scaling resets and optimizes scales/solvent; R changes cannot be attributed solely to B transfer.',
    'Reflection totals do not identify observations or the Free-R test set.',
)


def _bound(max_bytes):
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_LOG_BYTES:
        raise ValueError('Require a positive log byte bound no larger than 16 MiB')


def _finite(token, *, nonnegative=False):
    try:
        exact = Decimal(token)
        value = float(exact)
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise ValueError('Invalid printed number') from exc
    if (not exact.is_finite() or not math.isfinite(value)
            or (exact != 0 and value == 0) or (nonnegative and value < 0)):
        raise ValueError('Nonfinite, underflowed or invalid printed number')
    return value


def parse_final_scaling(log_text, *, max_bytes=MAX_LOG_BYTES):
    """Describe one complete, ordered final block; never select a partial block.

    Returned line numbers are one-based in the provided text. The checksum binds
    its UTF-8 bytes. A transfer is exposed only for a unique complete matched-count
    sequence; an explicitly printed zero differs from unavailable evidence.
    """
    _bound(max_bytes)
    if not isinstance(log_text, str):
        raise ValueError('Require log text')
    raw = log_text.encode('utf-8')
    if len(raw) > max_bytes:
        raise ValueError('Log exceeds byte bound')
    result = dict(kind='nasolve-printed-final-scaling', schema_version=1,
        format_id='phenix-four-stage-final-scaling-v1', status='NO_FINAL_SECTION',
        source=dict(sha256=sha256(raw).hexdigest(), size_bytes=len(raw)),
        final_header_line=None, stages=[], b_transfer_A2=None,
        b_transfer_printed=None, diagnostics=[], limitations=list(_LIMITS),
        native_execution_performed=False, model_changed=False,
        scientific_acceptance='NOT_ASSESSED')
    lines = log_text.splitlines()
    starts = [i for i, line in enumerate(lines) if _FINAL.fullmatch(line.strip())]
    if len(starts) != 1:
        if starts:
            result['status'] = 'AMBIGUOUS_FINAL_SECTION'
        result['diagnostics'].append('Require exactly one explicit Final section; no last-block selection.')
        return result
    result['final_header_line'] = starts[0]+1
    malformed = False
    for i in range(starts[0]+1, len(lines)):
        line = lines[i].strip()
        if not line.startswith(_PREFIXES):
            continue
        match = _ROW.fullmatch(line)
        try:
            if match is None:
                raise ValueError('Unrecognized final-scaling row')
            label, shift, rall, work, free, count = match.groups()
            stage = ('b_transferred' if shift is not None else
                     {'start':'before_scaling', 're-set all scales':'scales_reset',
                      'bulk-solvent and scaling':'solvent_scaled'}[label])
            if not re.fullmatch(r'[0-9]{1,15}', count) or int(count) <= 0:
                raise ValueError('Invalid reflection count')
            row = dict(stage=stage, line_number=i+1, printed_line=lines[i],
                r_all=_finite(rall, nonnegative=True), r_work=_finite(work, nonnegative=True),
                r_free=_finite(free, nonnegative=True), n_refl=int(count),
                b_transfer_A2=_finite(shift) if shift is not None else None,
                b_transfer_printed=shift)
            result['stages'].append(row)
        except (ValueError, KeyError) as exc:
            malformed = True
            result['diagnostics'].append(f'Line {i+1}: {exc}')
    sequence = [r['stage'] for r in result['stages']]
    if malformed:
        result['status'] = 'UNSUPPORTED_FINAL_SCALING'
    elif len(sequence) < 4 and sequence == [n for n in _NAMES if n in sequence]:
        result['status'] = 'INCOMPLETE_FINAL_SCALING'
    elif sequence != list(_NAMES):
        result['status'] = 'AMBIGUOUS_FINAL_SCALING'
        result['diagnostics'].append('Expected one ordered start/reset/transfer/solvent sequence.')
    elif len({r['n_refl'] for r in result['stages']}) != 1:
        result['status'] = 'INCONSISTENT_REFLECTION_COUNT'
    else:
        result.update(status='OBSERVED',
            b_transfer_A2=result['stages'][2]['b_transfer_A2'],
            b_transfer_printed=result['stages'][2]['b_transfer_printed'])
    return result


def read_final_scaling(log_path, *, expected_sha256=None, max_bytes=MAX_LOG_BYTES):
    """Read only the explicitly supplied file, with a bounded read and optional pin."""
    _bound(max_bytes)
    if expected_sha256 is not None and (not isinstance(expected_sha256, str)
            or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256)):
        raise ValueError('Invalid expected log SHA-256')
    with Path(log_path).expanduser().open('rb') as handle:
        raw = handle.read(max_bytes+1)
    if len(raw) > max_bytes:
        raise ValueError('Log exceeds byte bound')
    if expected_sha256 is not None and sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Log checksum differs from expected SHA-256')
    return parse_final_scaling(raw.decode('utf-8'), max_bytes=max_bytes)


def describe_b_frame(log_text, written_b_A2, *, reference_labels=()):
    """Explain an additive export offset for explicit caller-supplied B values.

    Values may be atoms or caller-computed base means; this API does not infer
    membership or verify model linkage. References, when supplied, are averaged
    equally. No automatic choice of ligands, atoms, occupancies or environments.
    """
    if not isinstance(written_b_A2, Mapping) or not 1 <= len(written_b_A2) <= 128:
        raise ValueError('Require 1–128 named written B values')
    values = {}
    for label, value in written_b_A2.items():
        if (not isinstance(label, str) or not label.strip() or len(label)>128
                or type(value) not in (int, float)):
            raise ValueError('Require nonempty labels and finite numeric B values')
        values[label] = _finite(str(value))
    if (not isinstance(reference_labels, (list, tuple))
            or any(not isinstance(k, str) or k not in values for k in reference_labels)
            or len(set(reference_labels)) != len(reference_labels)):
        raise ValueError('Reference labels must be explicit unique members of written values')
    evidence = parse_final_scaling(log_text)
    result = dict(kind='nasolve-final-offset-B-description', schema_version=1,
        frame_status='UNAVAILABLE', model_binding='CALLER_VALUES_NOT_VERIFIED',
        log=evidence, written_A2=values, offset_adjusted_A2=None,
        reference_labels=list(reference_labels), relative_to_equal_reference_mean_A2=None,
        limitations=[
            'Written B minus the printed final transfer is not an exact pre-scaling state or a complete common physical scale.',
            'Printed transfer and caller values have limited precision; earlier ADP/scaling trajectories may differ.',
            'No B values are applied to a model; local contrasts remove only a uniform additive offset.',
        ])
    if evidence['status'] != 'OBSERVED':
        return result
    adjusted = {k:_finite(str(v-evidence['b_transfer_A2'])) for k,v in values.items()}
    relative = None
    if reference_labels:
        # Divide before summing to avoid overflowing a representable mean.
        mean = math.fsum(values[k]/len(reference_labels) for k in reference_labels)
        relative = {k:_finite(str(v-mean)) for k,v in values.items()}
    result.update(frame_status='APPROXIMATE_FINAL_OFFSET_ONLY',
                  offset_adjusted_A2=adjusted, relative_to_equal_reference_mean_A2=relative)
    return result
