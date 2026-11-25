"""Opt-in process-local enforcement of reciprocal XYZ/group-B plus exact MLHL.

This separately versioned guard surrounds the existing native execution owner.
It starts no process, supplies no forces and changes no historical worker. The
caller admits the prepared endpoint, scientific policy, sources and output/stop
proof. Real-space/sliced models and multiprocess dispatch are outside v1.
"""
from collections import Counter
from copy import deepcopy
from functools import wraps
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import platform

from .refinement_parameter_scope import ParameterScope, scope_digest
from .refinement_parameter_native import observe_model, observe_xyz, observe_group, capture_atoms
from .refinement_diffraction_observation import DiffractionReference, observe_diffraction, observe_target

POLICY_ID = 'native-reciprocal-xyz-group-b-guard-v1'
_ACTIVE = None


def _native_bindings():
    """Admit the callback sources, without modifying a native installation."""
    profile = json.loads(Path(__file__).with_name('data').joinpath('refinement-mixed-native-profile.json').read_text())
    if (platform.system(), platform.machine()) != (profile['system'], profile['machine']):
        raise ValueError('Mixed runtime callback platform is not qualified')
    modules = {name:importlib.import_module(name) for name in profile['modules']}
    def verify():
        for name, module in modules.items():
            if sha256(Path(module.__file__).read_bytes()).hexdigest() != profile['modules'][name]:
                raise ValueError('Mixed runtime callback source changed: ' + name)
    verify()
    hooks = {}
    for role, (name, klass, method) in profile['bindings'].items():
        cls = getattr(modules[name], klass)
        original = getattr(cls, method)
        if (getattr(original, '__module__', None) != name
                or getattr(original, '__qualname__', None) != klass + '.' + method
                or not hasattr(original, '__code__')
                or Path(original.__code__.co_filename).resolve() != Path(modules[name].__file__).resolve()):
            raise ValueError('Mixed runtime callback already replaced: ' + role)
        hooks[role] = (cls, method)
    return hooks, profile, verify


class MixedRuntimeGuard:
    """One explicit scope, one existing native call, bounded observation memory.

    Call ``finish(returned_driver, dry_run=...)`` inside the context after the
    existing owner returns. A caller-caught callback failure remains latched.
    A successful summary means these observations/restorations passed, not that
    output files, ancestry, external process closure or geometry are accepted.
    The caller persists the summary even when the guarded operation raises.
    """
    def __init__(self, scope, diffraction):
        if not isinstance(scope, ParameterScope) or not isinstance(diffraction, DiffractionReference):
            raise ValueError('Require pinned parameter and diffraction references')
        if scope.record()['real_space']:
            raise ValueError('This runtime version excludes real-space/sliced-model refinement')
        self.scope = scope
        self.diffraction = diffraction
        self._hooks = {}; self._originals = {}; self._wrappers = {}
        self._driver = None; self._entered = False; self._finished = False
        self._failed = None; self._verify = None; self._pid = None
        self._counts = Counter()
        self._record = dict(schema_version=1, policy_id=POLICY_ID, status='NOT_STARTED',
            scope_sha256=scope_digest(scope.record()),
            source_model_sha256=scope.record()['source_model_sha256'],
            diffraction_sha256=scope_digest(diffraction.record()),
            bindings_restored=False, counts={},
            scientific_approval='NOT_RUN', real_space=False, single_process=True)

    def _fail(self, exc):
        if self._failed is None:
            self._failed = dict(type=type(exc).__name__, message=str(exc))
        self._record.update(status='FAILED', error=self._failed)

    def _live(self):
        if self._failed is not None:
            raise ValueError('Mixed runtime has a latched failed observation')
        if not self._entered or self._finished or self._pid != os.getpid():
            raise ValueError('Mixed runtime requires one active unfinished process')
        if any(getattr(cls, name) is not self._wrappers[role]
               for role,(cls,name) in self._hooks.items()):
            raise ValueError('Mixed runtime callback binding changed')

    def _model(self, driver, *, initial=False):
        if type(driver.params.main.nproc) is not int or driver.params.main.nproc != 1:
            raise ValueError('Mixed runtime requires declared single-process execution')
        if driver.fmodels.fmodel_neutron() is not None:
            raise ValueError('Mixed runtime requires one X-ray diffraction model')
        fm = driver.fmodels.fmodel_xray()
        state = observe_model(self.scope, driver.model, fm, driver.params, initial=initial)
        observe_diffraction(self.diffraction, fm)
        observe_target(self.diffraction, fm, fm.target_functor(alpha_beta=fm.alpha_beta()))
        self._counts['model'] += 1
        return state

    def _optimizer(self, role, minimizer):
        if self._driver is None:
            raise ValueError('Optimizer entered before checked initialization')
        if role == 'xyz':
            observe_xyz(self.scope, minimizer)
            fm = minimizer.fmodels.fmodel_xray()
            target = minimizer.fmodels.target_functor_xray
        else:
            observe_group(self.scope, minimizer)
            fm = minimizer.fmodel; target = minimizer.target_functor
        self.scope.state(capture_atoms(fm.xray_structure))
        observe_target(self.diffraction, fm, target)

    def _wrapper(self, role, original):
        @wraps(original)
        def observed(native, *args, **kwargs):
            try:
                self._live()
                if role == 'initialize':
                    if self._driver is not None:
                        raise ValueError('Duplicate mixed runtime initialization')
                    self._record['initial'] = self._model(native, initial=True)
                    self._driver = native
                    value = original(native, *args, **kwargs)
                    self._model(native)
                elif role == 'stage':
                    if self._driver is None:
                        raise ValueError('Macro stage entered before checked initialization')
                    func = args[0] if args else kwargs['func']
                    enabled = native.tt.status(func)
                    if enabled:self._model(native)
                    value = original(native, *args, **kwargs)
                    if enabled:
                        self._model(native);self._counts['enabled_stages'] += 1
                else:
                    self._optimizer(role, native)
                    value = original(native, *args, **kwargs)
                    self._optimizer(role, native)
                self._live()
                self._counts[role] += 1
                return value
            except BaseException as exc:
                self._fail(exc)
                raise
        return observed

    def __enter__(self):
        global _ACTIVE
        if self._entered or self._record['status'] != 'NOT_STARTED' or _ACTIVE is not None:
            raise ValueError('Mixed runtime guards cannot nest or be reused')
        try:
            hooks, profile, self._verify = _native_bindings()
            if set(hooks) != {'initialize','stage','xyz','group_B'}:
                raise ValueError('Incomplete native callback contract')
            self._hooks = hooks
            self._originals = {key:getattr(cls,name) for key,(cls,name) in hooks.items()}
            self._wrappers = {key:self._wrapper(key, original) for key,original in self._originals.items()}
            self._pid = os.getpid();self._entered = True;_ACTIVE = self
            self._record.update(status='OBSERVING', native_profile=profile)
            for key,(cls,name) in hooks.items():setattr(cls,name,self._wrappers[key])
            return self
        except BaseException as exc:
            self._fail(exc);self._restore()
            raise

    def finish(self, returned_driver, *, dry_run):
        """Observe the existing owner's exact returned driver, without adopting it."""
        try:
            self._live()
            if returned_driver is not self._driver or self._driver is None:
                raise ValueError('Require the checked initialized driver returned by the existing owner')
            if type(dry_run) is not bool or returned_driver.iparams.refinement.dry_run is not dry_run:
                raise ValueError('Native execution mode differs from the explicit declaration')
            if dry_run:
                if self._counts['xyz'] or self._counts['group_B'] or self._counts['enabled_stages']:
                    raise ValueError('Dry initialization unexpectedly evaluated refinement targets')
            elif (not self._counts['xyz'] or not self._counts['group_B'] or not self._counts['enabled_stages']
                    or returned_driver.macro_cycle != returned_driver.params.main.number_of_macro_cycles):
                raise ValueError('Incomplete observed XYZ/group-B refinement')
            self._record['final'] = self._model(returned_driver)
            self._verify()
            self._record.update(dry_run=dry_run, macro_cycles=0 if dry_run else returned_driver.macro_cycle)
            self._finished = True
        except BaseException as exc:
            self._fail(exc)
            raise

    def _restore(self):
        global _ACTIVE
        for role,(cls,name) in self._hooks.items():
            if getattr(cls,name) is self._wrappers.get(role):
                setattr(cls,name,self._originals[role])
        self._record['bindings_restored'] = all(getattr(cls,name) is self._originals.get(role)
                                               for role,(cls,name) in self._hooks.items())
        if _ACTIVE is self:_ACTIVE = None

    def __exit__(self, kind, exc, tb):
        pending = None
        try:
            if exc is not None:self._fail(exc)
            elif self._failed is not None:raise ValueError('Mixed runtime has a latched failed observation')
            elif not self._finished:raise ValueError('Mixed runtime requires explicit returned-state completion')
            if any(getattr(cls,name) is not self._wrappers[role] for role,(cls,name) in self._hooks.items()):
                raise ValueError('Mixed runtime callback changed before restoration')
            if self._verify is not None:self._verify()
        except BaseException as failure:
            self._fail(failure);pending = failure
        finally:
            self._restore()
            if not self._record['bindings_restored']:
                failure = ValueError('Mixed runtime callback restoration is incomplete')
                self._fail(failure);pending = pending or failure
        if self._failed is None:self._record['status'] = 'OBSERVED'
        if exc is None and pending is not None:raise pending
        return False

    def summary(self):
        record = deepcopy(self._record)
        record['counts'] = dict(self._counts)
        return record
