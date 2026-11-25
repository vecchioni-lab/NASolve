"""Bounded, opt-in wall-clock attribution for synchronous runtime observations.

Exclusive times partition the measured intervals; inclusive times may overlap.
This is diagnostic evidence, not a CPU profiler or a scientific acceptance gate.
No process, file, timer thread or checkpoint owner is introduced.
"""
from contextlib import contextmanager
from copy import deepcopy
import math
import time


class RuntimeTiming:
    """One synchronous clock and bounded labels, including interrupted calls.

    The caller owns persistence. ``summary`` includes open intervals without
    mutating them, so a saved partial snapshot does not imply completion. Clock
    calls/instrumentation overhead is included in surrounding wall time.
    """
    def __init__(self, *, clock=time.perf_counter, max_labels=128):
        if type(max_labels) is not int or not 1 <= max_labels <= 1024:
            raise ValueError('Require a bounded timing label count')
        self._clock=clock;self._limit=max_labels;self._rows={};self._stack=[]
        self._last=self._now();self._start=self._last
        self._unattributed=0.0

    def _now(self):
        now=self._clock()
        if type(now) not in (int,float) or not math.isfinite(now):
            raise ValueError('Require a finite monotonic timing clock')
        if hasattr(self,'_last') and now < self._last:
            raise ValueError('Timing clock moved backwards')
        return now

    def _charge(self, now):
        delta=now-self._last
        if self._stack:
            self._rows[self._stack[-1][0]]['exclusive_seconds']+=delta
        else:self._unattributed+=delta
        self._last=now

    @contextmanager
    def measure(self, category, label):
        if category not in ('observer','native','telemetry') or not isinstance(label,str) or not label or len(label)>128:
            raise ValueError('Invalid runtime timing category or label')
        if len(self._stack)>=128:raise ValueError("Runtime timing nesting bound exceeded")
        key=(category,label)
        if key not in self._rows:
            if len(self._rows)>=self._limit:raise ValueError('Runtime timing label bound exceeded')
            self._rows[key]=dict(category=category,label=label,entered=0,completed=0,
                interrupted=0,inclusive_seconds=0.0,exclusive_seconds=0.0)
        now=self._now();self._charge(now)
        row=self._rows[key];row['entered']+=1;frame=(key,now);self._stack.append(frame)
        completed=False
        try:
            yield
            completed=True
        finally:
            now=self._now();self._charge(now)
            popped=self._stack.pop()
            if popped is not frame:raise ValueError('Timing stack changed')
            row['inclusive_seconds']+=now-popped[1]
            row['completed' if completed else 'interrupted']+=1

    def summary(self):
        now=self._now();rows=deepcopy(self._rows);unattributed=self._unattributed
        if self._stack:rows[self._stack[-1][0]]['exclusive_seconds']+=now-self._last
        else:unattributed+=now-self._last
        for key,start in self._stack:rows[key]['inclusive_seconds']+=now-start
        totals={name:sum(r['exclusive_seconds'] for r in rows.values() if r['category']==name)
                for name in ('observer','native','telemetry')}
        return dict(schema_version=1,kind='synchronous-runtime-wall-timing',
            elapsed_seconds=now-self._start,exclusive_seconds=totals,
            unattributed_seconds=unattributed,
            active=[dict(category=k[0],label=k[1]) for k,start in self._stack],
            calls=list(rows.values()),
            interpretation='Exclusive times partition elapsed wall time with unattributed time; inclusive times overlap. Includes instrumentation overhead; not CPU cost or scientific acceptance.')
