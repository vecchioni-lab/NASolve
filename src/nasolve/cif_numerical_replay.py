"""Inspection-local reuse of pure numerical validation; no file trust cache.

The caller still reads and authenticates every artifact. Only a calculation over
identical complete JSON inputs may be reused, within one synchronous inspection.
No paths, capture contents or native processes are retained by this helper.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from hashlib import sha256
import json

_ACTIVE = ContextVar('cif_numerical_replay', default=None)
MAX_ENTRIES = 16
MAX_RESULT_BYTES = 65536


def _json_only(value):
    kind = type(value)
    if kind in (str, int, float, bool, type(None)):
        return True
    if kind is list:
        return all(_json_only(v) for v in value)
    if kind is dict:
        return all(type(k) is str and _json_only(v) for k, v in value.items())
    return False


def _bytes(value):
    # Reject JSON's lossy tuple/list and integer/string-key conversions. Unusual
    # inputs still go to the original validator; they do not gain reuse.
    if not _json_only(value):
        return None
    try:
        return json.dumps(value, separators=(',', ':'),
                          allow_nan=False).encode('utf-8')
    except (ValueError, TypeError):
        return None


@contextmanager
def numerical_replay_scope():
    """Share at most sixteen small verdicts; discard them even on failed reads."""
    if _ACTIVE.get() is not None:
        yield
        return
    token = _ACTIVE.set({})
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def validate_mixed_result(validator, result, expected, selected_indices):
    """Reuse only the same validator and complete, byte-equivalent JSON inputs.

    Exceptions are never stored. A valid REVIEW verdict retains its exact meaning.
    Cache saturation simply repeats validation; it creates no scientific failure.
    Returned verdicts are independent copies, never shared mutable authority.
    """
    cache = _ACTIVE.get()
    if cache is None:
        return validator(result, expected, selected_indices)
    encoded = _bytes([result, expected, selected_indices])
    if encoded is None:
        return validator(result, expected, selected_indices)
    key = (validator, sha256(encoded).digest())
    if key in cache:
        return deepcopy(cache[key])
    verdict = validator(result, expected, selected_indices)
    saved = _bytes(verdict)
    if len(cache) < MAX_ENTRIES and saved is not None and len(saved) <= MAX_RESULT_BYTES:
        cache[key] = deepcopy(verdict)
    return verdict
