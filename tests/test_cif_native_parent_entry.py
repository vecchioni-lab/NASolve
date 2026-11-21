from types import SimpleNamespace as NS

import pytest

from nasolve import cif_native_parent_entry as entry


def fixture(monkeypatch):
    events = []
    class Manager:
        restraints_manager = None
        def process(self, **options):
            raise AssertionError("Unprepared original call")
    class Program:
        joint_xn = False
        def validate(self):
            events.append("native validation")
            return "valid"
    def finalize(*, model):
        return model.process(make_restraints=True)
    module = NS(finalize_model=finalize)
    process = Manager.process
    p = Program()
    p.model, p.fmodel = Manager(), object()
    api = NS(program=Program, preprocess=module, manager=Manager, validate=Program.validate,
             finalize=finalize, process=process)
    service = object()
    monkeypatch.setattr(entry, "_native_entry", lambda: (api, service))
    initial = NS(endpoint_audit_sha256="a" * 64, native_model_role="candidate")
    def candidate(program):
        assert program is p
        events.append("candidate")
        return initial
    def prepare(program, options, motion, received):
        assert program is p and options == dict(make_restraints=True)
        assert motion is initial and received is service
        events.append("prepare")
        def result():
            events.append("closed mapping")
            return initial
        context = NS(result=result)
        def built():
            events.append("closed chemistry")
            return NS(native_result="native return", receipt={"count": 1})
        builder = NS(model=p.model, result=built, evidence=lambda: dict(
            status="COMPLETE", service={"count": 1}, runtime_authority=False, scientific_acceptance=False))
        return context, builder
    return NS(p=p, api=api, module=module, candidate=candidate, prepare=prepare, events=events)


def test_current_candidate_reaches_one_closed_preparation_and_returns_native_value(monkeypatch):
    c = fixture(monkeypatch)
    with entry.native_parent_entry(observe_candidate=c.candidate, prepare_parent=c.prepare):
        assert c.p.validate() == "valid"
        assert c.module.finalize_model(model=c.p.model) == "native return"
    assert c.events == ["native validation", "candidate", "prepare", "closed mapping", "closed chemistry"]
    assert c.api.program.validate is c.api.validate and c.api.manager.process is c.api.process
    assert c.module.finalize_model is c.api.finalize


@pytest.mark.parametrize("fault", ["missing", "pre_validate", "wrong_model", "twice", "outside", "joint",
                                    "already_interpreted", "no_fmodel", "bad_initial", "other_motion",
                                    "unclosed", "builder_failure", "other_builder", "swallowed",
                                    "replaced_manager", "replaced_diffraction", "wrong_receipt", "missing_audit"])
def test_wrong_phase_identity_or_failed_preparation_cannot_escape(monkeypatch, fault):
    c = fixture(monkeypatch)
    marker = RuntimeError("original native failure")
    def prepare(*args):
        context, builder = c.prepare(*args)
        def failed():
            raise marker
        if fault in {"builder_failure", "swallowed"}:
            builder.result = failed
        if fault == "unclosed":
            context.result = failed
        if fault == "other_motion":
            context.result = lambda: NS(native_model_role="candidate", endpoint_audit_sha256="other")
        if fault == "other_builder":
            builder.model = object()
        if fault == "wrong_receipt":
            builder.evidence = lambda: dict(status="COMPLETE",service={"count":2})
        return context, builder
    callback = (lambda p: NS(native_model_role="parent")) if fault=="bad_initial" else c.candidate
    if fault == "missing_audit":
        callback = lambda p: NS(native_model_role="candidate")
    with pytest.raises((RuntimeError, ValueError)) as error:
        with entry.native_parent_entry(observe_candidate=callback, prepare_parent=prepare):
            if fault == "pre_validate":
                c.module.finalize_model(model=c.p.model)
            if fault == "joint":
                c.p.joint_xn = True
            if fault == "already_interpreted":
                c.p.model.restraints_manager = object()
            if fault == "no_fmodel":
                c.p.fmodel = None
            c.p.validate()
            if fault == "replaced_manager":
                c.p.model = c.api.manager()
            if fault == "replaced_diffraction":
                c.p.fmodel = object()
            if fault == "outside":
                c.p.model.process(make_restraints=True)
            if fault not in ("missing", "swallowed"):
                c.module.finalize_model(model=object() if fault=="wrong_model" else c.p.model)
            if fault == "twice":
                c.module.finalize_model(model=c.p.model)
            if fault == "swallowed":
                with pytest.raises(RuntimeError):
                    c.module.finalize_model(model=c.p.model)
    if fault in {"builder_failure", "unclosed", "swallowed"}:
        assert error.value is marker
    assert c.api.program.validate is c.api.validate and c.api.manager.process is c.api.process
    assert c.module.finalize_model is c.api.finalize


def test_binding_ownership_and_original_exception_survive_cleanup(monkeypatch):
    c = fixture(monkeypatch)
    original = RuntimeError("Phenix failed later")
    replacement = lambda **kw: None
    with pytest.raises(RuntimeError) as error:
        with entry.native_parent_entry(observe_candidate=c.candidate, prepare_parent=c.prepare):
            c.module.finalize_model = replacement
            raise original
    assert error.value is original and c.module.finalize_model is replacement
    assert c.api.program.validate is c.api.validate and c.api.manager.process is c.api.process
