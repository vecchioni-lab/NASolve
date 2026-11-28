"""Receive one source-bound parent preparation in an isolated Phenix worker."""
from contextlib import contextmanager
from functools import wraps
import importlib
from pathlib import Path
import re
from threading import Lock, get_ident
from types import SimpleNamespace

from .cif_native_parent import _digest, _require, load_native_parent_service


_SOURCES = {
    "phenix.programs.phenix_refine": "86a2bfe8ca994aec6f3a97a70d7609b0ea53ea4c21f4e9c9a9940e313d95a088",
    "phenix.refinement.fsr.preprocess": "6cdd7a0ae669a03c0869e4e49c9d4eee45f83d820b9b2e784eb8f5a8b49f826c",
}
_ENTRY_LOCK = Lock()


def _native_entry():
    service = load_native_parent_service()
    modules = {name: importlib.import_module(name) for name in _SOURCES}
    application, preprocess = modules.values()
    for name, function, qualified in (
            (application.__name__, application.Program.validate, "Program.validate"),
            (preprocess.__name__, preprocess.finalize_model, "finalize_model")):
        path = Path(modules[name].__file__).resolve()
        _require(_digest(path.read_bytes()) == _SOURCES[name] and function.__module__ == name
                 and function.__qualname__ == qualified and function.__globals__ is vars(modules[name])
                 and Path(function.__code__.co_filename).resolve() == path,
                 f"Capture the qualified native {qualified} before installing any wrapper")
    return SimpleNamespace(program=application.Program, preprocess=preprocess, manager=service._api.manager,
                           validate=application.Program.validate, finalize=preprocess.finalize_model,
                           process=service._api.process), service


@contextmanager
def native_parent_entry(*, observe_candidate, prepare_parent):
    """Scope the native hooks for one validated candidate and its pending manager.

    Both callbacks are trusted worker code. observe_candidate(program) returns
    its admitted candidate mapping. prepare_parent(program, options, mapping,
    service) returns the closed coordinate context and its chemistry builder.
    The outer owner retains inputs and discards the worker on any failure.
    """
    _require(callable(observe_candidate) and callable(prepare_parent), "Require both parent-entry callbacks")
    _require(_ENTRY_LOCK.acquire(blocking=False), "A native parent entry is already active")
    installed = []
    first_error = None
    state = "pending"
    thread = get_ident()
    selected = candidate_model = candidate_fmodel = mapping = audit = None

    def guarded(function):
        @wraps(function)
        def call(*args, **kwargs):
            nonlocal first_error
            try:
                if first_error is not None:
                    raise first_error
                _require(get_ident() == thread, "Foreign thread entered the isolated native parent worker")
                return function(*args, **kwargs)
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
                elif first_error is not exc:
                    raise first_error from exc
                raise
        return call

    try:
        api, service = _native_entry()

        @guarded
        def validate(program, *args, **kwargs):
            nonlocal state, selected, candidate_model, candidate_fmodel, mapping, audit
            _require(state == "pending", "Repeated native candidate validation")
            state = "validating"
            result = api.validate(program, *args, **kwargs)
            _require(not program.joint_xn and program.fmodel is not None
                     and program.model.restraints_manager is None, "Require candidate diffraction before geometry")
            selected, candidate_model, candidate_fmodel = program, program.model, program.fmodel
            mapping = observe_candidate(program)
            audit = getattr(mapping, "endpoint_audit_sha256", None)
            _require(getattr(mapping, "native_model_role", None) == "candidate"
                     and isinstance(audit, str) and re.fullmatch("[0-9a-f]{64}", audit) and program.model is candidate_model
                     and program.fmodel is candidate_fmodel, "Initial mapping must identify the diffraction candidate")
            state = "validated"
            return result

        @guarded
        def finalize(*args, **kwargs):
            nonlocal state
            _require(state == "validated" and not args and kwargs.get("model") is candidate_model
                     and selected.model is candidate_model and selected.fmodel is candidate_fmodel,
                     "Native finalization does not own the validated candidate")
            state = "finalizing"
            result = api.finalize(**kwargs)
            _require(state == "prepared" and selected.model is candidate_model and selected.fmodel is candidate_fmodel,
                     "Native finalization did not complete the same candidate preparation")
            state = "complete"
            return result

        @guarded
        def process(model, *args, **options):
            nonlocal state
            _require(state == "finalizing" and model is candidate_model and selected.model is model
                     and selected.fmodel is candidate_fmodel and not args
                     and options.get("make_restraints") is True, "Unexpected pending geometry manager or process options")
            state = "preparing"
            context, builder = prepare_parent(selected, options, mapping, service)
            closed = context.result()
            _require(selected.model is candidate_model and selected.fmodel is candidate_fmodel
                     and closed.native_model_role == "candidate"
                     and closed.endpoint_audit_sha256 == audit
                     and builder.model is model, "Completed preparation belongs to a different candidate or manager")
            interpretation = builder.result()
            evidence = builder.evidence()
            _require(evidence["status"] == "COMPLETE" and evidence["service"] == interpretation.receipt
                     and evidence["runtime_authority"] is False and evidence["scientific_acceptance"] is False,
                     "A completed source-bound chemistry reading is required")
            state = "prepared"
            return interpretation.native_result

        bindings = ((api.program, "validate", api.validate, validate),
                    (api.preprocess, "finalize_model", api.finalize, finalize),
                    (api.manager, "process", api.process, process))
        for owner, name, original, hook in bindings:
            _require(getattr(owner, name) is original, f"Native binding changed before entry: {name}")
            setattr(owner, name, hook)
            installed.append((owner, name, original, hook))
        yield
        if first_error is not None:
            raise first_error
        _require(state == "complete", "Native worker left before completing parent preparation")
        _require(all(getattr(owner, name) is hook for owner, name, _, hook in installed),
                 "Native parent entry lost ownership of a binding")
    finally:
        for owner, name, original, hook in reversed(installed):
            if getattr(owner, name) is hook:
                setattr(owner, name, original)
        _ENTRY_LOCK.release()
