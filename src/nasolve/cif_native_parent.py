"""One qualified Phenix interpretation of a typed geometry parent.

Create the service before installing the worker's model and selected-site hooks.
It captures geometry on the caller's stable model. The caller owns candidate
diffraction, coordinate transfer, subsequent checks and disposal on failure.
"""
from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
from pathlib import Path
import threading
from types import SimpleNamespace

from . import cif_interpretation_controls as reader


# Scoped to the reviewed Phenix 2.2.1-6174 interpretation and PHIL APIs.
_SOURCES = {
    "mmtbx.model.model": "e35c7cdffa57ee3a6dac73c0dbdc46f382faf69780ba7a71c16aa6d58aa359ee",
    "mmtbx.utils": "7e7890bfb37807ef67a5e65aada46d28836b5a0f1554f788eac27ca828ba3542",
    "iotbx.pdb": "7a1502d4a98f8d164b0c2e86f223245a5d9d6fcc50df14e86523cd46959905a8",
    "iotbx.phil": "3b0ddf62dc86e37e55fcad8c03f19b5795ba2279baf34afa6a1969cf403b8c08",
    "libtbx.phil": "0eb65cfba816370a91b98b54198fb83cad2f542916681457b33e9cef1cbbe491",
}
_SERVICE_LOCK = threading.Lock()
_THREAD = threading.local()


def _digest(payload):
    return sha256(payload).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _native_api():
    from mmtbx.monomer_library import pdb_interpretation

    modules = {name: importlib.import_module(name) for name in _SOURCES}
    for name, module in modules.items():
        _require(_digest(Path(module.__file__).read_bytes()) == _SOURCES[name],
                 f"Unqualified Phenix parent-service source: {name}")
    manager = modules["mmtbx.model.model"].manager
    server = modules["mmtbx.utils"].process_pdb_file_srv
    pdb_input = modules["iotbx.pdb"].input
    for method, name, qualified in ((manager.process, "mmtbx.model.model", "manager.process"),
            (server.process_pdb_files, "mmtbx.utils", "process_pdb_file_srv.process_pdb_files"),
            (pdb_input, "iotbx.pdb", "input")):
        _require(method.__module__ == name and method.__qualname__ == qualified
                 and method.__globals__ is vars(modules[name])
                 and Path(method.__code__.co_filename).resolve() == Path(modules[name].__file__).resolve(),
                 f"Capture the native {qualified} before installing any wrapper")
    return SimpleNamespace(manager=manager, server=server, process=manager.process,
        monomer_summary=pdb_interpretation.monomer_mapping.summary,
        process_files=server.process_pdb_files, pdb_input=pdb_input, phil=modules["iotbx.phil"],
        scope_type=modules["libtbx.phil"].scope_extract, profile="phenix-2.2.1-6174-parent-service-v1")


def _checked_bytes(payload, record):
    _require(type(payload) is bytes and record["size"] == len(payload)
             and record["sha256"] == _digest(payload), "Typed input bytes differ from the source report")


def _bound_inputs(bound, pin):
    payload = bound.source_report_json
    _require(type(payload) is bytes and _digest(payload) == pin, "Typed compiler-report digest differs")
    report = json.loads(payload)
    _require(_canonical(report) == payload and report["policy_id"] == "cif-typed-native-literal-inputs-v1"
             and report["execution_context"]["ordinary_handoff_allowed"] is False
             and report["scientific_approval"] == "NOT_RUN" and bound.runtime_authority is False
             and bound.chemical_admission is False, "Require a canonical observation-only typed source")
    _checked_bytes(bound.parent_bytes, report["model"])
    phils, controls = bound.compiled_restraint_phils, bound.interpretation_control_phils
    for inputs, records in ((phils, report["compiled_phils"]),
                            (controls, [row["input"] for row in report["captured_controls"]])):
        _require(type(inputs) is tuple and inputs and len(inputs) == len(records),
                 "Missing or merged ordered PHIL role")
        for data, record in zip(inputs, records):
            _checked_bytes(data, record)
    _require(bound.reader_policy == reader.POLICY_ID
             and tuple(k for k, _ in bound.reader_controls) == tuple(sorted(reader.CONTROLS))
             and all(value is False for _, value in bound.reader_controls), "Four False reader controls required")
    seen = set()
    for data in controls:
        reader.control_definitions(data, seen)
    _require(seen == reader.CONTROLS, "Typed PHIL lacks a required reader control")
    return bound.parent_bytes, phils


def _check_controls(scope):
    for path in reader.CONTROLS:
        value = scope
        for part in path.split(".")[1:]:
            value = getattr(value, part)
        _require(value is False, f"Native reader control differs: {path}")


def _live_geometry(api, params):
    def extract(value):
        if isinstance(value, api.scope_type):
            return {k: extract(v) for k, v in vars(value).items() if not k.startswith("__phil_")}
        if isinstance(value, (list, tuple)):
            return [extract(v) for v in value]
        if value is None or type(value) in (bool, int, float, str):
            return value
        raise ValueError(f"Unqualified native PHIL value of type {type(value).__name__}")
    return _digest(_canonical([extract(params.geometry_restraints),
                               params.pdb_interpretation.secondary_structure.enabled]))


def _compiled_geometry(api, phils):
    sources = []
    def definitions(scope):
        return [(row.path.removeprefix("refinement."), tuple(w.value for w in row.object.words))
                for row in scope.all_definitions()]
    for data in phils:
        original = api.phil.parse(input_string=data.decode("utf-8"), process_includes=False)
        pieces = [child.as_str() for obj in original.objects
                  for child in (obj.objects if obj.is_scope and obj.name == "refinement" else (obj,))]
        scope = api.phil.parse(input_string="\n".join(pieces), process_includes=False)
        declared = definitions(scope)
        _require(declared == definitions(original), "Changing PHIL root altered a declaration")
        for path, _ in declared:
            _require(path.startswith(("geometry_restraints.edits.", "geometry_restraints.remove."))
                     or path == "pdb_interpretation.secondary_structure.enabled",
                     f"Unexpected parameter in compiled geometric restraints: {path}")
        sources.append(scope)
    effective, unused = api.manager.get_default_pdb_interpretation_scope().fetch(
        sources=sources, track_unused_definitions=True)
    _require(not unused, "Compiled geometry PHIL contains unused definitions")
    return _live_geometry(api, effective.extract())


@dataclass(frozen=True)
class NativeParentInterpretation:
    processed: object
    native_result: object
    receipt: dict


class _ParentService:
    def __init__(self, api):
        self._api = api
        self._used = False
        self._invalid = False

    def interpret(self, model, bound_inputs, *, expected_report_sha256, process_options,
                  source_native_json=None):
        """Interpret once. Optional original native bytes require a component and restraint match."""
        active = getattr(_THREAD, "owner", None)
        if active is not None:
            active._invalid = True
            raise ValueError("Nested parent interpretation; discard the active model")
        _require(not self._used, "Cannot reuse a parent interpretation service")
        _require(_SERVICE_LOCK.acquire(blocking=False), "Another parent interpretation is active")
        try:
            _require(not self._used, "Cannot reuse a parent interpretation service")
            self._used = True
            _THREAD.owner = self
            options = dict(process_options)
            if source_native_json is None:
                return self._interpret(model, bound_inputs, expected_report_sha256, options)
            from .cif_native_parent_chemistry import compare_parent_chemistry
            return compare_parent_chemistry(self, model, bound_inputs, expected_report_sha256,
                                            options, source_native_json)
        finally:
            _THREAD.owner = None
            _SERVICE_LOCK.release()

    def _interpret(self, model, bound, pin, options):
        api = self._api
        parent, phils = _bound_inputs(bound, pin)
        _require(type(model) is api.manager and model._model_input is not None
                 and model._processed_pdb_file is None, "Require the pending native model and candidate input")
        _require(options.get("make_restraints") is True and options.get("pdb_interpretation_params") is not None
                 and options.get("custom_nb_excl") is None
                 and not (set(options) - {"make_restraints", "pdb_interpretation_params", "grm_normalization",
                      "plain_pairs_radius", "custom_nb_excl", "run_clash_guard"}),
                 "Require native geometry-building process options")
        params = options["pdb_interpretation_params"]
        _check_controls(params.pdb_interpretation)
        expected_geometry = _compiled_geometry(api, phils)
        _require(_live_geometry(api, params) == expected_geometry, "Effective compiled geometry differs")
        candidate_input = model._model_input
        parent_input = api.pdb_input(source_info="NASolve bound geometry parent", lines=parent.decode("ascii"))
        original = api.process_files
        thread = threading.get_ident()
        seen = []
        entered = False

        def read_parent(server, *args, **kwargs):
            nonlocal entered
            if threading.get_ident() != thread and kwargs.get("pdb_inp") is not candidate_input:
                return original(server, *args, **kwargs)
            try:
                _require(threading.get_ident() == thread and not entered and type(server) is api.server
                         and not args and set(kwargs) == {"pdb_inp", "hierarchy", "allow_missing_symmetry"}
                         and kwargs["pdb_inp"] is candidate_input and model._model_input is candidate_input
                         and kwargs["hierarchy"] is None and kwargs["allow_missing_symmetry"] is True,
                         "Unexpected, repeated or foreign parent-service call")
                entered = True
                _require(server.pdb_interpretation_params is params.pdb_interpretation,
                         "Native server detached the interpretation parameters")
                _check_controls(server.pdb_interpretation_params)
                result = original(server, **dict(kwargs, pdb_inp=parent_input))
                _require(isinstance(result, tuple) and len(result) == 2 and result[1] is parent_input,
                         "Native server did not return the bound geometry input")
                seen.append(result[0])
                return result
            except BaseException:
                self._invalid = True
                raise

        _require(api.server.process_pdb_files is original, "Native service has a different current owner")
        api.server.process_pdb_files = read_parent
        try:
            native_result = api.process(model, **options)
        finally:
            if api.server.process_pdb_files is read_parent:
                api.server.process_pdb_files = original
            else:
                # Preserve a foreign binding and any native exception already in flight.
                self._invalid = True
        _require(not self._invalid and len(seen) == 1, "Incomplete or invalid native parent interpretation")
        processed = seen[0]
        _require(model._pdb_interpretation_params is params and model.restraints_manager is not None
                 and model.restraints_manager.geometry is not None
                 and processed.all_chain_proxies.pdb_hierarchy is model.get_hierarchy(),
                 "Retained geometry does not belong to this interpretation")
        _check_controls(params.pdb_interpretation)
        _require(_live_geometry(api, params) == expected_geometry, "Effective geometry changed during interpretation")
        return NativeParentInterpretation(processed, native_result, {
            "policy_id": "cif-native-parent-interpretation-v1", "profile": api.profile,
            "source_report_sha256": pin, "parent_sha256": _digest(parent),
            "compiled_geometry_sha256": expected_geometry, "native_interpretations": 1,
            "reader_controls": {k: False for k in sorted(reader.CONTROLS)},
            "chemical_admission": False, "ordinary_handoff_allowed": False})


def load_native_parent_service():
    """Capture the native entry points before the model and selected-site observers."""
    return _ParentService(_native_api())
