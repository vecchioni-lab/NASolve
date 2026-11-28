"""The live diagnostic sees both registered phosphate groups at one unchanged native model."""
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
import json
import sys
from types import SimpleNamespace as NS

import pytest

from nasolve import cif_phosphate_phase as phase
from nasolve import cif_refinement_output


@pytest.mark.parametrize("variant", ["observe", "raise", "move", "single", "refine", "existing"])
def test_grouped_observer_is_scoped_to_a_fresh_zero_step_preflight(tmp_path, monkeypatch, variant):
    root = tmp_path / "parallelity_runtime"
    root.mkdir()
    monkeypatch.chdir(tmp_path)
    raw = [tmp_path / name for name in ("data.mtz", "model.pdb")]
    for p in raw:
        p.write_bytes(p.name.encode())
    inputs = [dict(size=p.stat().st_size, sha256=sha256(p.read_bytes()).hexdigest()) for p in raw]
    inspections = [dict(registered_continuation=dict(continuation_id=i), o3_image="image",
                        model_sha256=inputs[1]["sha256"]) for i in (4, 9)]
    intent = {"inspection": inspections[0]} if variant == "single" else {"inspections": inspections}
    command = ["phenix.refine", *map(str, raw), "output.prefix=refined"]
    request = (json.dumps(dict(command=command, inputs=inputs, phosphate=intent,
                               policy_id='round-local-registered-phosphate-set-execution-v12')) + "\n").encode()
    (root / "request.json").write_bytes(request)
    args = [*map(str, raw), "output.prefix=parallelity_runtime/preflight/native", "refinement.dry_run=True"]
    reading = "refine" if variant == "refine" else "preflight"
    if variant == "existing":
        (root / "preflight").mkdir()

    class Program:
        def validate(self):
            return None

    original = Program.validate
    monkeypatch.setitem(sys.modules, "phenix.programs.phenix_refine", NS(Program=Program))
    owners = []
    entered = []

    class Owner:
        def __init__(self, inspection, model_bytes):
            self.inspection = inspection
            self.full = None
            self.calls = Counter()
            self.joint_calls = Counter()
            self.bond = {"neighbours": 2}
            self.live_terms = [{"kind": "ANGLE"}] * 4 + [{"kind": "TORSION"}] * 3
            self.owned = {}
            self.restored = False
            owners.append(self)

        @contextmanager
        def active(self, *additional):
            try:
                yield
            finally:
                for owner in (self, *additional):
                    owner.restored = True

        def attach(self, model):
            self.full = model
            self.owned[geometry] = NS(check_proxies=lambda g: None)

    class Geometry:
        def energies_sites(self, **kwargs):
            assert kwargs["compute_gradients"] and not any(o.restored for o in owners)
            for o in owners:
                o.calls[7, True] += 1
            owners[0].joint_calls[(7,) * len(owners), True] += 1

    geometry = Geometry()
    xrs = NS(sites_cart=lambda: [(0., 0., 0.)])
    model = NS(get_xray_structure=lambda: xrs, restraints_manager=NS(geometry=geometry), coordinate=1.)
    def compatible(arguments, *, evidence_directory, **kwargs):
        entered.append(True)
        evidence_directory.mkdir()
        program = Program()
        program.joint_xn = False
        program.fmodel = object()
        program.validate()
        return NS(model=model, iparams=NS(refinement=NS(dry_run=True)),
                  fmodels=NS(fmodel_xray=lambda: program.fmodel, fmodel_neutron=lambda: None))

    monkeypatch.setattr(phase, "RegisteredPhosphateRuntime", Owner)
    monkeypatch.setattr(phase, "run_compatible_refinement", compatible)
    monkeypatch.setattr(phase, "verify_phosphate_bond", lambda *a: {"neighbours": 2})
    monkeypatch.setattr(phase, "_observations", lambda f: {(1, 0, 0): (5., 1., False)})
    monkeypatch.setattr(cif_refinement_output, "_hierarchy", lambda m: [m.coordinate])
    monkeypatch.setattr(cif_refinement_output, "_scattering", lambda x: ({"atoms": [1.]}, []))
    visited = []
    def observer(live, observed, counts):
        assert live is model and all(o.full is live and not o.restored for o in owners)
        assert [e["continuation_id"] for e in observed["edges"]] == [4, 9]
        assert observed["reflections"]["start"]["work"] == 1
        first = counts()
        geometry.energies_sites(sites_cart=xrs.sites_cart(), compute_gradients=True)
        second = counts()
        assert first["joint_full_gradients"] == 1 and second["joint_full_gradients"] == 2
        assert second["groups"] == [dict(continuation_id=i, full_gradients=2) for i in (4, 9)]
        observed["edges"].clear()
        visited.append(counts)
        if variant == "raise":
            raise LookupError("observer failed")
        if variant == "move":
            live.coordinate = 2.

    def run():
        return phase.run_phase(root, reading, sha256(request).hexdigest(), command[1:] if reading == "refine" else args,
                               observe_preflight=observer)

    if variant == "observe":
        result = run()
        assert result["bindings_restored"] and len(result["edges"]) == 2
    else:
        expected = LookupError if variant == "raise" else ValueError
        with pytest.raises(expected):
            run()
    assert bool(entered) == bool(visited) == (variant in {"observe", "raise", "move"})
    if visited:
        with pytest.raises(ValueError, match="active"):
            visited[0]()
    assert all(o.restored for o in owners) and Program.validate is original
    assert not (root / reading / "phosphate.json").exists()
