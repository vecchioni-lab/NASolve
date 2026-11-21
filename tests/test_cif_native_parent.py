"""The pending geometry manager must consume the bound parent exactly once."""
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import threading
from types import SimpleNamespace as NS

import pytest

from nasolve import cif_native_parent as owner
from nasolve.cif_interpretation_controls import CONTROLS, POLICY_ID


def digest(data):
    return sha256(data).hexdigest()


def record(data):
    return {"sha256": digest(data), "size": len(data)}


@dataclass(frozen=True)
class Bound:
    parent_bytes: bytes
    source_report_json: bytes
    compiled_restraint_phils: tuple
    interpretation_control_phils: tuple
    reader_controls: tuple
    reader_policy: str = POLICY_ID
    runtime_authority: bool = False
    chemical_admission: bool = False


def source():
    parent = b"parent PDB"
    restraints = (b"first", b"second")
    controls = ("\n".join(f"{k} = False" for k in sorted(CONTROLS)) + "\n").encode()
    report = {"policy_id": "cif-typed-native-literal-inputs-v1", "model": record(parent),
              "compiled_phils": list(map(record, restraints)), "captured_controls": [{"input": record(controls)}],
              "execution_context": {"ordinary_handoff_allowed": False}, "scientific_approval": "NOT_RUN"}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    return Bound(parent, payload, restraints, (controls,), tuple((k, False) for k in sorted(CONTROLS)))


def controls():
    return NS(sort_atoms=False, use_ncs_to_build_restraints=False,
              restraints_library=NS(cdl=False, cdl_nucleotides=NS(enable=False)))


class DeliberateFailure(Exception):
    pass


@pytest.fixture
def setup(monkeypatch):
    bound = source()
    params = NS(pdb_interpretation=controls(), geometry_restraints="original")
    processed = NS(all_chain_proxies=NS(pdb_hierarchy=object()))
    candidate = object()
    state = NS(mode="ok", inputs=[], native_calls=0, foreign=None)
    class Service:
        def process_pdb_files(self, **kwargs):
            state.inputs.append(kwargs["pdb_inp"])
            if state.mode == "wrong_return":
                return processed, candidate
            return processed, kwargs["pdb_inp"]
    original = Service.process_pdb_files

    class Model:
        def __init__(self):
            self._processed_pdb_file = None
            self._model_input = candidate
            self.restraints_manager = None
            self.hierarchy = None
        def get_hierarchy(self):
            return self.hierarchy
        def process(self, **kwargs):
            state.native_calls += 1
            self._pdb_interpretation_params = kwargs["pdb_interpretation_params"]
            service = Service()
            service.pdb_interpretation_params = params.pdb_interpretation
            call = dict(pdb_inp=candidate, hierarchy=None, allow_missing_symmetry=True)
            if state.mode == "nested":
                try:
                    state.nested()
                except ValueError:
                    pass
            if state.mode == "other_thread":
                other = threading.Thread(target=service.process_pdb_files,
                                         kwargs=dict(call, pdb_inp="independent model"))
                other.start()
                other.join()
            if state.mode == "foreign_success":
                state.foreign = lambda *args, **kwargs: None
                Service.process_pdb_files = state.foreign
                return 17
            if state.mode == "exception":
                raise DeliberateFailure("first native exception")
            if state.mode == "foreign":
                state.foreign = lambda *args, **kwargs: None
                Service.process_pdb_files = state.foreign
                raise DeliberateFailure("first native exception")
            if state.mode == "wrong_input":
                call["pdb_inp"] = object()
            if state.mode == "wrong_parameters":
                service.pdb_interpretation_params = controls()
            if state.mode != "zero":
                result, _ = service.process_pdb_files(**call)
                self.hierarchy = result.all_chain_proxies.pdb_hierarchy
            if state.mode == "swallow_duplicate":
                try:
                    service.process_pdb_files(**call)
                except ValueError:
                    pass
            if state.mode == "control_changed":
                params.pdb_interpretation.sort_atoms = True
            if state.mode == "geometry_changed":
                params.geometry_restraints = "changed"
            if state.mode == "wrong_hierarchy":
                self.hierarchy = object()
            self.restraints_manager = NS(geometry=object())
            return 17

    api = NS(manager=Model, server=Service, process=Model.process, process_files=original,
             pdb_input=lambda *, source_info, lines: lines, profile="test")
    monkeypatch.setattr(owner, "_native_api", lambda: api)
    monkeypatch.setattr(owner, "_compiled_geometry", lambda api, phils: "original")
    monkeypatch.setattr(owner, "_live_geometry", lambda api, params: params.geometry_restraints)
    options = dict(pdb_interpretation_params=params, make_restraints=True)
    return NS(bound=bound, pin=digest(bound.source_report_json), loader=owner.load_native_parent_service,
              model=Model(), options=options, state=state, server=Service, original=original)


def interpret(x, *, bound=None, pin=None, service=None):
    return (service or x.loader()).interpret(x.model, bound or x.bound,
        expected_report_sha256=pin or x.pin, process_options=x.options)


def test_one_native_parent_and_owned_restoration(setup):
    x = setup
    service = x.loader()
    result = interpret(x, service=service)
    assert result.native_result == 17
    assert result.processed.all_chain_proxies.pdb_hierarchy is x.model.get_hierarchy()
    assert x.state.inputs == [x.bound.parent_bytes.decode()]
    assert x.server.process_pdb_files is x.original
    assert result.receipt["native_interpretations"] == 1
    assert result.receipt["chemical_admission"] is False
    assert result.receipt["ordinary_handoff_allowed"] is False
    with pytest.raises(ValueError):
        interpret(x, service=service)
    assert x.state.native_calls == 1


@pytest.mark.parametrize("change", ["wrong_pin", "parent", "reorder", "control_bytes", "missing_control",
                                    "numeric_false", "authority", "params", "no_restraints", "geometry",
                                    "custom_exclusions"])
def test_inconsistent_inputs_never_enter_native(setup, change):
    x = setup
    data, pin = x.bound, x.pin
    if change == "wrong_pin":
        pin = "0" * 64
    elif change == "parent":
        data = replace(data, parent_bytes=b"different")
    elif change == "reorder":
        data = replace(data, compiled_restraint_phils=data.compiled_restraint_phils[::-1])
    elif change == "control_bytes":
        data = replace(data, interpretation_control_phils=(b"changed",))
    elif change == "missing_control":
        data = replace(data, reader_controls=data.reader_controls[:-1])
    elif change == "numeric_false":
        data = replace(data, reader_controls=tuple((k, 0) for k, _ in data.reader_controls))
    elif change == "authority":
        data = replace(data, runtime_authority=True)
    elif change == "params":
        x.options["pdb_interpretation_params"].pdb_interpretation.sort_atoms = True
    elif change == "no_restraints":
        x.options["make_restraints"] = False
    elif change == "geometry":
        x.options["pdb_interpretation_params"].geometry_restraints = "different"
    elif change == "custom_exclusions":
        x.options["custom_nb_excl"] = object()
    with pytest.raises(ValueError):
        interpret(x, bound=data, pin=pin)
    assert x.state.native_calls == 0
    assert x.server.process_pdb_files is x.original


@pytest.mark.parametrize("mode", ["zero", "wrong_input", "wrong_parameters", "swallow_duplicate",
                                  "control_changed", "geometry_changed", "wrong_hierarchy", "exception",
                                  "foreign", "foreign_success", "wrong_return", "nested"])
def test_failure_discards_result_and_preserves_original_error_or_binding(setup, mode):
    x = setup
    x.state.mode = mode
    x.state.nested = lambda: interpret(x)
    error = DeliberateFailure if mode in {"exception", "foreign"} else ValueError
    with pytest.raises(error):
        interpret(x)
    assert x.server.process_pdb_files is (x.state.foreign if mode.startswith("foreign") else x.original)
    assert len(x.state.inputs) <= 1


def test_independent_native_call_passes_through_during_owned_interpretation(setup):
    x = setup
    x.state.mode = "other_thread"
    assert interpret(x).receipt["native_interpretations"] == 1
    assert x.state.inputs == ["independent model", "parent PDB"]


def test_refuse_service_changed_after_qualification(setup):
    x = setup
    service = x.loader()
    foreign = lambda *args, **kwargs: None
    x.server.process_pdb_files = foreign
    with pytest.raises(ValueError, match="different current owner"):
        interpret(x, service=service)
    assert x.server.process_pdb_files is foreign and x.state.native_calls == 0


def test_geometry_fingerprint_keeps_order_and_full_precision():
    api = NS(scope_type=NS)
    geometry = NS(edits=NS(bond=[NS(distance_ideal=1.4700000001), NS(distance_ideal=1.47)]))
    params = NS(geometry_restraints=geometry, pdb_interpretation=NS(secondary_structure=NS(enabled=False)))
    first = owner._live_geometry(api, params)
    geometry.edits.bond.reverse()
    assert owner._live_geometry(api, params) != first
    geometry.edits.bond.reverse()
    geometry.edits.bond[0].distance_ideal = 1.4700000002
    assert owner._live_geometry(api, params) != first
