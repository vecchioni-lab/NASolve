"""Private composition helpers; neither owns nor resumes an enclosing request."""
import math
from .cif_generation_process import _valid_attempt_identity


def parent_identity(identity):
    """Detach a supplied parent claim before caller-owned data can change."""
    if identity is None:
        return None
    if not _valid_attempt_identity(identity):
        raise ValueError('Invalid enclosing attempt identity')
    return dict(identity)


class OuterAllowance:
    """Clamp a callback to the earliest observed monotonic deadline.

    Callback time itself consumes allowance. An increasing or constant callback
    cannot move a previously observed deadline later. No clock value is persisted
    or used as proof of process death; the enclosing request must own recovery.
    """
    def __init__(self, callback, clock, error_type=TimeoutError):
        if callback is not None and not callable(callback):
            raise ValueError('Invalid enclosing remaining allowance callback')
        self.callback = callback
        self.clock = clock
        self.error_type = error_type
        self.deadline = None
        if callback is not None:
            self.remaining()

    def remaining(self):
        if self.callback is None:
            return None
        before = self.clock()
        value = self.callback()
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Invalid enclosing remaining allowance value')
        deadline = before + value
        self.deadline = deadline if self.deadline is None else min(self.deadline, deadline)
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise self.error_type('Enclosing attempt allowance exhausted; preserve partial output')
        return remaining
