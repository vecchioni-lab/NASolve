# Bounded coordinate search and feasible derivative checks

These explicit Python helpers support local geometry investigations before a
model is admitted to open XYZ/B refinement. Every tested atom stays inside a
specified movement ball around its source coordinate. They evaluate a supplied
objective; they do not infer chemistry, run Phenix, choose a structure or publish
a checkpoint. Ordinary refinement and L-BFGS callers are unchanged.

## What is implemented

`nasolve.topostitch_feasible_search.minimize` starts from zero displacement and
performs spectral projected-gradient steps with an Armijo decrease check. A
projection constructs a feasible trial position, then the callback calculates
its actual scalar and Cartesian gradient. A clipped coordinate never inherits
a gradient evaluated somewhere else. Backtracking follows the feasible segment
between the old and projected points. The scalar is not rescaled or substituted.

`project_balls` projects Cartesian triples into equal origin-centred balls.
`projected_residual` reports `||x - P(x - g)||`: at a constrained boundary optimum,
the Cartesian gradient can remain nonzero. The result separates projected
stationarity, iteration/evaluation limits and failures. None is scientific
acceptance. Only the last accepted point is returned as the final diagnostic;
valid rejected trials and an attempted but invalid callback remain distinct.

`nasolve.topostitch_feasible_derivatives.check` supplements an existing derivative
audit when ordinary centred probes would exceed the movement limit. Interior
atoms use Cartesian directions. Boundary atoms use one inward radial direction
and two orthonormal tangent directions. Tangent samples follow sphere arcs at
the atom's **actual** displacement radius; they are not snapped to the cap.
Inward probes use a second-order one-sided stencil; tangent and interior probes
use centred differences. Both 1e-4 and 1e-5 Å steps and the 1e-3 absolute
directional-error bound are fixed. Insufficient clearance, collapsed probes,
nonfinite values or a changing repeated baseline fail explicitly.

The derivative callback's scalar/gradient are copied immediately, so reused
native buffers cannot mutate the baseline or hide repeat drift. Unrelated native
metadata is not copied. A successful first probe survives a failed partner;
the report may then end with an incomplete sample pair and no derivative row.
`frames` exposes the directional frames for read-only inspection.

## Explicit caller contract

```python
from nasolve.topostitch_feasible_search import minimize
from nasolve.topostitch_feasible_derivatives import check

# objective(x) returns (scalar, gradient) for the actual supplied displacements.
search = minimize(objective, variable_count=18, radius=2.0,
                  max_iterations=100, max_evaluations=300)
# audit_objective(x) returns {"target": scalar, "gradient": gradient}.
# This separate audit does not promote an unconverged search result.
audit = check(audit_objective, selected_displacements, radius=2.0)
```

Inputs are 1–400 finite Cartesian triples. Search limits are explicit: at most
500 iterations/5,000 objective calls; defaults are 100/300. The search records
its Armijo constant, backtracking policy and spectral-step bounds. The audit
needs `2 + 4*n` evaluations for `n` scalar coordinates, including an exact repeat.
Reports are bounded in-memory diagnostic dictionaries, not a campaign artifact
schema or retention policy. Callers should select a small mask and budget rather
than use these maxima as operational targets.

The caller owns atom ordering, source identity, units, objective provenance,
frozen state, native processes, wall-clock deadlines and output validation.
These synchronous helpers cannot interrupt a blocked external callback. Invalid
controls raise before evaluation; callback exceptions become diagnostic failures.
Process interrupts such as `KeyboardInterrupt` and `SystemExit` propagate to the
process owner. An internal budget stop is distinct from a callback exception,
so callback `StopIteration` cannot impersonate convergence or budget completion.

A feasible-basis pass validates the sampled ambient gradient. It does **not**
replace required centred/serialized checks, establish constrained convergence,
validate chemical targets or authorize a model. Native adapters, ordinary
refinement integration and automatic adoption remain outside this addition.
There is no dependency, CLI, default, migration or existing artifact change.

## Evidence and present scientific limit

The [A01 handoff](metal-development-handoff.md#a01-feasible-step-2026-11-24)
records the prior Phenix 2.2.1-6174 prototype execution: 100 iterations, 209 search
calls, projected residual 5.1565, and a separately checked derivative error
4.96255e-5. The search stopped at its iteration limit. Centred/rounded endpoint
checks remained unavailable; no candidate was emitted. This is prototype native
evidence, not a fresh maintained-code native execution or accepted structure.

Maintained extraction has 53 focused regressions and 99 adjacent coordinate/
native-interface checks, plus the same 53 tests against an offline installed
wheel with source-checkout access blocked. The initial installed harness stopped
before tests on a macOS /var versus /private/var path assertion; correcting that
assertion reused the same wheel. Disposable installation files were removed.
Fourteen hardening regressions first fail against the
preceding implementations; the second collapsed-probe witness adds the same
failure mechanism at a different scale. A cold replay checks every one of the
209 saved search requests and all 74 derivative requests, with **531 assertions**
and exact numerical results. Saved scalar lookup is not a new native evaluation;
probe gradients absent from the archive are not inferred. Source data remain
unchanged. Exact commands, hashes and test outputs are in the local evidence
anchor `Alder/a01-feasible-maintained-20261124-01/` under `branch-artifacts/`.
The full suite and a receiving native integration remain separate gates.

**Methods wording.** Local displacement variables were restricted to a product
of equal-radius Cartesian balls. A spectral projected-gradient search evaluated
the unchanged objective at feasible proposals, accepting sufficient decrease
along feasible segments. Constrained stationarity was assessed separately from
the Cartesian gradient norm. Supplemental derivative checks used a full-rank
feasible basis with radial one-sided and sphere-tangent centred differences,
retaining both sample sizes and all valid partial evidence. Numerical outcomes
were kept separate from chemical assessment and model adoption.
