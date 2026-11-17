"""Passive, bounded native minimizer evidence; never select a fitted endpoint.

The native worker imports this file directly. Only the offline summarizer uses
NASolve package imports. Internal weight-search trials can appear in the same
receipt as final refinement calls; endpoint attribution remains unassessed.
"""
from functools import wraps
import hashlib
import inspect
import json
import math
from pathlib import Path
import re

PROTOCOL = 'metal-optimizer-stopping-v1'
MAX_CALLS = 4096
_SOURCE_NAMES = {'lbfgs_python', 'minimization_python', 'lbfgs_kernel'}
_CALL_FIELDS = {'sequence', 'kind', 'iterations', 'function_evaluations',
                'max_iterations', 'max_calls', 'reason', 'error',
                'is_unusual_error', 'native_criterion_met'}


class _StopLog:
    """Retain stop messages only, while preserving an existing native log."""
    def __init__(self, original):
        self.original = original
        self.pending = ''
        self.reasons = []

    def write(self, text):
        if self.original is not None:
            self.original.write(text)
        self.pending += text
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            prefix = 'lbfgs minimizer stop: '
            if line.startswith(prefix):
                self.reasons.append(line[len(prefix):])
                if len(self.reasons) > 8:
                    raise ValueError('Unexpected native optimizer stop inventory')
        if len(self.pending) > 16384:
            raise ValueError('Unbounded native optimizer log line')
        return len(text)

    def flush(self):
        if self.original is not None:
            self.original.flush()


class _Observer:
    def __init__(self, module, minimizer_type, source_hashes):
        self.module = module
        self.minimizer_type = minimizer_type
        self.sources = dict(source_hashes)
        self.calls = []
        self.binding_restored = False
        self.capture_complete = False
        self.entered = False

    def __enter__(self):
        if self.entered or hasattr(self.module, '_nasolve_metal_stopping_owner'):
            raise ValueError('Native optimizer observation already owned')
        self.entered = True
        self.original = self.module.run
        signature = inspect.signature(self.original)

        @wraps(self.original)
        def observed(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            target = bound.arguments.get('target_evaluator')
            if not isinstance(target, self.minimizer_type):
                return self.original(*args, **kwargs)
            xyz = getattr(target, 'refine_xyz', False)
            adp = getattr(target, 'refine_adp', False)
            if not (xyz or adp):
                return self.original(*args, **kwargs)
            if type(xyz) is not bool or type(adp) is not bool or xyz == adp:
                raise ValueError('Unsupported native minimizer selection')
            if bound.arguments.get('use_fortran', False) is not False:
                raise ValueError('Unsupported Fortran optimizer observation')
            params = bound.arguments.get('termination_params')
            if params is None:
                raise ValueError('Native optimizer termination settings missing')
            if len(self.calls) >= MAX_CALLS:
                raise ValueError('Native optimizer observation limit reached')
            log = _StopLog(bound.arguments.get('log'))
            bound.arguments['log'] = log
            result = self.original(*bound.args, **bound.kwargs)
            if len(log.reasons) > 1:
                raise ValueError('Ambiguous native optimizer stopping reason')
            reason = log.reasons[0] if log.reasons else 'unreported'
            self.calls.append(dict(sequence=len(self.calls)+1,
                kind='XYZ' if xyz else 'ADP', iterations=result.iter(),
                function_evaluations=result.nfun(),
                max_iterations=params.max_iterations, max_calls=params.max_calls,
                reason=reason, error=result.error,
                is_unusual_error=result.is_unusual_error,
                native_criterion_met=True if reason == 'traditional_convergence_test' else None))
            return result

        self.wrapper = observed
        self.module._nasolve_metal_stopping_owner = self
        self.module.run = observed
        return self

    def __exit__(self, exc_type, exc, tb):
        owned = self.module.run is self.wrapper
        if owned:
            self.module.run = self.original
        if getattr(self.module, '_nasolve_metal_stopping_owner', None) is self:
            del self.module._nasolve_metal_stopping_owner
        self.binding_restored = owned and self.module.run is self.original
        self.capture_complete = exc_type is None and self.binding_restored
        if not owned and exc_type is None:
            raise ValueError('Native optimizer observation lost ownership')
        return False

    def receipt(self):
        return dict(protocol=PROTOCOL,
            implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            native_sources=dict(self.sources), entry_binding_authentication='NOT_ASSESSED',
            capture_complete=self.capture_complete,
            binding_restored=self.binding_restored, calls=[dict(c) for c in self.calls])


def observe(*, _lbfgs=None, _minimizer_type=None, _source_hashes=None):
    """Observe supported XYZ/ADP calls in this process and restore the binding."""
    if _lbfgs is None:
        import scitbx.lbfgs as lbfgs
        import mmtbx.refinement.minimization as minimization
        import scitbx_lbfgs_ext
        _lbfgs, _minimizer_type = lbfgs, minimization.lbfgs
        _source_hashes = {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name, module in [('lbfgs_python', lbfgs),
                                 ('minimization_python', minimization),
                                 ('lbfgs_kernel', scitbx_lbfgs_ext)]}
    return _Observer(_lbfgs, _minimizer_type, _source_hashes)


def _integer(value, optional=False):
    if value is None and optional:
        return
    if type(value) is not int or value < 0:
        raise ValueError('Invalid native optimizer count or limit')


def summarize(evidence, *, required_kinds=()):
    """Replay the shared conservative classifier without running native code."""
    from ..cif_fixed_geometry import classify_stopping
    if (not isinstance(evidence, dict) or evidence.get('protocol') != PROTOCOL
            or evidence.get('capture_complete') is not True
            or evidence.get('binding_restored') is not True
            or evidence.get('entry_binding_authentication') != 'NOT_ASSESSED'):
        raise ValueError('Incomplete native optimizer observation')
    sources = evidence.get('native_sources', {})
    if not isinstance(sources, dict) or set(sources) != _SOURCE_NAMES:
        raise ValueError('Missing native optimizer source provenance')
    for value in [evidence.get('implementation_sha256'), *sources.values()]:
        if not isinstance(value, str) or re.fullmatch('[a-f0-9]{64}', value) is None:
            raise ValueError('Invalid native optimizer source fingerprint')
    calls = evidence.get('calls')
    if not isinstance(calls, list) or len(calls) > MAX_CALLS:
        raise ValueError('Invalid native optimizer inventory')
    required = set(required_kinds)
    if not required <= {'XYZ', 'ADP'}:
        raise ValueError('Unsupported required optimizer kind')
    rows = []
    for i, call in enumerate(calls, 1):
        if not isinstance(call, dict) or set(call) != _CALL_FIELDS:
            raise ValueError('Invalid native optimizer call fields')
        for name in ('sequence', 'iterations', 'function_evaluations'):
            _integer(call[name])
        for name in ('max_iterations', 'max_calls'):
            _integer(call[name], optional=True)
        if call['sequence'] != i or call['kind'] not in {'XYZ', 'ADP'}:
            raise ValueError('Changed native optimizer sequence or kind')
        reason, error = call['reason'], call['error']
        if not isinstance(reason, str) or not reason or len(reason) > 256:
            raise ValueError('Invalid native optimizer stopping reason')
        if error is not None and (not isinstance(error, str) or not error or len(error) > 16384):
            raise ValueError('Invalid native optimizer error')
        if call['is_unusual_error'] is not None and type(call['is_unusual_error']) is not bool:
            raise ValueError('Invalid native optimizer unusual-error flag')
        if error is None and call['is_unusual_error'] is not None:
            raise ValueError('Unusual-error flag without a native error')
        expected_criterion = True if reason == 'traditional_convergence_test' else None
        if call['native_criterion_met'] is not expected_criterion:
            raise ValueError('Changed native optimizer criterion evidence')
        stopping = dict(call)
        if stopping['max_iterations'] is None:
            stopping['max_iterations'] = math.inf  # Unbounded native setting; never serialized.
        status = classify_stopping(stopping)
        rows.append(dict(sequence=i, kind=call['kind'], status=status,
            iterations=call['iterations'], function_evaluations=call['function_evaluations'],
            max_iterations=call['max_iterations'], max_calls=call['max_calls'],
            reason=reason, native_error=error, is_unusual_error=call['is_unusual_error']))
    if not required <= {row['kind'] for row in rows}:
        raise ValueError('Required native optimizer kind was not observed')
    return dict(protocol=PROTOCOL, implementation_sha256=evidence['implementation_sha256'],
        native_sources=dict(sources), entry_binding_authentication='NOT_ASSESSED',
        source_scope='On-disk native files; not authentication of a pre-existing runtime callable', calls=rows,
        needs_review=not rows or any(row['status'] != 'NATIVE_CRITERION_MET' for row in rows),
        scope='Supported native XYZ/ADP minimizers, including internal trial fits; not all native optimizers',
        selected_endpoint_attribution='NOT_ASSESSED',
        convergence='NOT_INDEPENDENTLY_ASSESSED', scientific_acceptance='NOT_ASSESSED',
        automatic_checkpoint_selection=False)


def verify_file(evidence, directory):
    """Require agreement between the native payload and its compact sidecar."""
    path = Path(directory) / 'optimizer-stopping.json'
    if 'optimizer_stopping' not in evidence:
        if path.exists() or path.is_symlink():
            raise ValueError('Unexpected optimizer stopping sidecar')
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing optimizer stopping sidecar')
    saved = json.loads(path.read_text())
    encode = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
    if encode(saved) != encode(evidence['optimizer_stopping']):
        raise ValueError('Optimizer stopping sidecar differs from native evidence')
