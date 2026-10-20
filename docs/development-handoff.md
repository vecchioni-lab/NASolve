# NASolve development handoff — current state

Updated **2026-10-20** from native receipts, user visual review and verified geometry/DF
bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The current laptop Cedar checkout remains at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, with only the explicitly
authorized `src/nasolve/phaser.py` fix modified after the GeoTest rerun.
Its other 45 frozen source hashes, including the distinct curated source,
are preserved. Preserve this local unpublished diagnostic head; do not pull or
replace it with a remote head to continue the run. Diagnostic scripts/derivatives are
not general production support. Earlier wording remains in Git and the
[exact pre-reconciliation backup](history/development-handoff-2026-10-10-pre-reconciliation.md.txt).

## Completed and open work

| Workstream | Verified result | Still open |
| --- | --- | --- |
| NARestraints | **v1.1.3 released and installed** (`a9264f9`); corrected Z:P/K:X roles, unchanged workbook. Docs-only PR #5 merged to main at `ef1a5a1`. | Combined-model geometry qualification belongs to the NASolve native trial. |
| W Saenger overlay / viewing | PR #24 merged at `0017081`; prior Z:P `run_003/refine-001` numerically SOLVED and overall user Coot visual PASS. PR #25 merged at `e8613bf`; bare `show` user-live PASS. | New-campaign automatic workspace activation has regression coverage, not a separate returned live verdict. |
| Cedar source lookup | Installed Phenix CCD lookup for IGU/IMC/CGY/DX and Coot construction verified; symlink duplicates resolved. Nine bundled-source roles audited. | Acquisition, parameter generation and linkage must become a repeatable ordinary workflow; source availability alone does not certify geometry. |
| Combined 42-residue W trial | **Preflight, Phaser and PostMR passed**; 42/42 identities, 12 retained + 5 replaced Saenger blocks, 8 explicit pairs, stacking enabled. | Effective geometry qualification, explicit phosphate-state review, refinement and human review. |
| Generic linkage diagnostic | **GENERIC_LINKAGE_MECHANICS_PASS** with fresh IMC, no missing heavy atoms, preserved links and D:1 terminal phosphate. | Diagnostic-only derivatives, not integrated general PostMR support or chemistry approval. |
| Custom restraint coverage | **21/21 bonds, 34/34 angles, 8/8 planes, 23/23 parallelities** matched; no exact duplicate planes/parallelities or overlap candidates. | Custom proxies remained preserved after native 5CM/DF adoption; coverage is not achieved geometry. |
| Effective 5CM / DF recovery | **REPAIRED_NATIVE_INTERPRETATION_PASS**: corrected 5CM and linked DF adopted in a separate native diagnostic; 42 mappings, DF bonds/chirality, preserved custom/other proxies and unchanged 868-atom model verified. | Separate minimization and user visual review completed; full numerical qualification remains pending. |
| Combined geometry trials | First trial received user Coot visual PASS. The DP-specific trial relieves the N5 conflict (worst 6.15→0.483 sigma); all 158 chirality signs and 38 backbone links survive. User also reports base visual PASS for the exact new model. | Sugars were not assessed by eye; numerical sugar/termination review and full qualification remain open. Convergence is not claimed. |
| Ordinary/full-auto campaigns | Prior EA/DiU/Q5cm/QiC cohort reached numerical SOLVED with review/provisional distinctions preserved. | This does not prove a fresh arbitrary-component run without a prepared resource bundle. |
| CIF Doctor first slice | Offline dictionary and frozen-checkpoint assessment; report-only pre-mutation/pre-ReadySet/effective PostMR receipts; explicit torsion-alternate and hash-scoped historical 5CM preparation. | Native consumer/proxy verification, mapped descriptors, generation/adoption and geometry/stitching remain separate slices. |
| P2 / prepared nonstandard P5 | P2 preparation and nonstandard campaign paths implemented and fixture-tested. | Source-native `1W5→DZ` / `1WA→DP` provenance/refinement; 3–5 real geometry-diverse P5 models. |
| Scout / Topo / GUI | Existing registration/shadow primitives and scoped evidence retained. | Operational Scout and topology surgery remain future work. |

**Latest returned Cedar regression:** `1443979b2308e4a2e507f0859370b44e0e124a86`,
**16 focused + 31 subtests (2.45 s)** and **983 full + 257 subtests
(80.81 s)**, using `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"`
and `../NASolve/.venv/bin/python -m pytest -q` (focused file:
`tests/test_cedar_ccd_resolver.py`). This receipt does not certify the current
local head or the later diagnostic derivatives. NARestraints installed workbook
SHA-256 remains
`94a66af42081188fd95f3fdcbe04cb01bed8f1826772597272320a8b4c0433b2`.

The October 10 documentation snapshot also passed the isolated Linux suite:
**981 passed, 2 skipped, 257 subtests (29.21 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
This is separate from the laptop receipt and is not native Phenix validation.

## Immediate next work

**Default command passage:** follow the
[Git delivery and terminal handoff contract](collaboration.md#git-delivery-and-terminal-handoffs).
Give one pasteable subshell containing the reviewed fetch, full-SHA detached
worktree, build and run commands joined by `&&`, with explicit quoted paths.
Keep necessary install commands as separate one-liners. This operating
convention belongs in the repo; private personality handoffs remain private.

**Cedar 21 returned and verified (2026-10-18): native membership PASS.** All
**491 payloads** verify, including the 367 unchanged Cedar 20 payloads and their
byte-identical manifest. Runner `6f7813d5…` matches clean NASolve `edafbf52…` /
NARestraints `a7b6a0c9…`; all 106 embedded runtime members verify. Independent
replay reproduces the compiler report and every derived PHIL byte for byte.

Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes both interpretation-only
cases: **6.298652 s** at the initial coordinates and **1.450339 s** at the saved
endpoints, exit zero. Each passes **14/14 exact mechanics checks**. The 877 atom
identities/43 sites, all component definitions, 19 dictionary files, modifiers
and 38 backbone links survive. All captured static proxy rows and the effective
native PHIL are identical across the two coordinate sets. Eight installed API
fingerprints agree, including the origin registry and secondary-structure source.
Native SS construction is disabled and no competing SS-origin proxies remain.

NARestraints compiles the 12 generic pair/23 generic stack declarations into
31 bonds, 52 angles and 35 parallelities. The retained 21 bonds, 34 angles,
eight planes and 23 parallelities survive exactly. Both managers therefore
contain **52 explicit bonds / 86 angles / eight planes / 58 parallelities**,
accounting separately for 20 paired relationships and 38 physical stacks.
This closes the **declared membership/consumer mechanics** gate for this
bounded first slice, not chemistry, achieved geometry or production integration.
The original Cedar 20 11 PASS/three REVIEW receipt remains unchanged.

Descriptive measurements under the same new policy are:

| Saved coordinates | Bond nominal deviations >=5 | Angle nominal deviations >=5 | Recorded chirality sign conflicts |
| --- | ---: | ---: | ---: |
| Initial | 30 | 68 | 0/158 |
| Cedar 19/20 endpoint | 4 | 10 | 0/158 |

Cedar 21 changes no coordinates and runs no optimization; these are two existing
models, not an improvement produced by this probe or evidence of convergence.
Local descriptive replay differs only by floating roundoff (maximum 7.11e-14);
all discrete counts and exact native comparisons agree. The historical
**NOT_CONVERGED_LIMIT** remains recorded. Energies from the old native SS
objective cannot be transferred to this NARestraints-owned objective.

**Cedar 22 returned and verified (2026-10-18): native mechanics PASS;
optimization remains unconverged.** All **609 payloads** verify, including all
491 unchanged Cedar 21 payloads and their manifest. Runner `e600a2b9…` matches
clean NASolve `2408c9ee…` / NARestraints `a7b6a0c9…`; all 106 runtime members
verify. Exact initial manager matching includes SS controls, the origin registry
and eight API fingerprints. The same 19 CIF/13 PHIL inputs remain fixed, without
new guessing or policy compilation. Phenix 2.2.1-6174 completes the trial in
**4.4478 s** and native PDB readback in **1.737436 s**, both exit zero. All
**17/17 exact readback checks** pass: 877 atoms/43 sites, 38 backbone links,
definitions, requests, static proxies, native policy and APIs survive. Separate
candidate serialization replays byte for byte.

The full-precision objective falls **3784.7499 → 2866.5556 (24.26%)** and
gradient norm **1033.6782 → 91.2772 (91.17%)**. At **905 iterations / 970 calls**
the line search reports rounding errors preventing progress; the native
criterion is false. Preserve **NOT_CONVERGED_ERROR**. This happens before PDB
serialization. The rounded vector has a separate target **2870.0305** and
gradient norm **907.0440**; retain full precision for future numerical review.

Nominal deviations >=5 change from **four to three distance terms**, **ten to
ten angles**, with no sign conflicts among 158 recorded chirality proxies. All
three remaining distance outliers are CGY A:20–DX D:3 hydrogen bonds, still
**4.34–5.58 Å** versus 2.8 Å targets; the longest worsens slightly. Nine angle
outliers involve that pair. DP B:4 also retains its C6–N5–C7 discrepancy,
**127.87° versus 109.471°**. These findings do not authorize target changes.

**Cedar 23 returned and verified (2026-10-19): sampled numerical REVIEW.**
`scripts/build_cif_gradient_audit_probe.py` builds
`23_Cedar_probe_cif_gradient_audit.py` from the verified Cedar 22 capsule.
It repeats dictionary assessment, records all 20 explicit intersite distance
groups and selects six probe atoms from the largest captured bond/angle
deviations. The K:X pair's existing GC-like intent is preserved. CIF Doctor
already detects the retained DP N5 planar-angle conflict; no new target is
inferred from the residuals.

The native phase exactly matches the initial manager, eight native APIs and
six numerical-source hashes, then evaluates full-precision and PDB-rounded
endpoints under the full objective and seven isolated category controls.
Four central-difference steps, per-family gradients, repeat/additivity checks,
descent profiles and neighbour counts are retained. The cap is 4,000 energy
evaluations / 1,200 seconds; no minimizer runs or new coordinate model is
written. These numerical controls do not change the NARestraints policy or
relax any exact native gate. Sampled agreement cannot establish full gradient
correctness, convergence or chemistry. Source/charge, pucker, absolute stereochemistry,
complete geometry, refinement and adoption remain open. Ordinary PostMR and
historical gates are unchanged; private capsules/models/logs are not committed.
Cedar 23 passes **70 focused checks (7.14 s)** and **1,691 full tests, two
skips and 276 subtests (83.63 s)**, with actual-input offline inspection and
synthetic deleted-build transport. Its returned **670 payloads** and all 609
prior payloads plus their manifest verify byte for byte. Native execution
completes in **7.8046 s**, exit zero, with **2,734/4,000** energy evaluations.
Initial manager, eight API sources, six numerical sources and the static
constraint signature match. All 17 prerequisite mechanics checks replay.

Both coordinate cases fail **18/21 sampled directions** for parallelity and
the full objective; bond, angle, dihedral, chirality, planarity and nonbonded
controls each pass **21/21**. Repeats, captured snapshots and target/gradient
additivity agree. At CGY A:20 N4 x, the native parallelity derivative is
**−2.9313** while the four central differences stabilize near **+7.4647**.
The disagreement survives PDB rounding and step reduction.

An independent centered-scatter eigensolver reproduces both parallelity
energies within 6e-12 and selected finite differences within 1.2e-6. Modeling
the second-plane accumulation-loop bounds in the public CCTBX header reproduces
all **2,631 saved gradient components per case** to about 1.5e-12 in norm.
The public loop omits/truncates second-plane contributions. This strongly
indicates a native accumulation defect; the installed C++ header was not
captured, and the audit does not prove it caused the earlier line-search stall.

**Cedar 24 returned and verified (2026-10-19): installed accumulation defect reproduced.**
`scripts/build_cif_parallelity_audit_probe.py` builds
`24_Cedar_probe_cif_parallelity_audit.py` from the exact verified Cedar 23 ZIP.
The new diagnostic replays all 17 mechanics checks and matches the initial
manager, eight API sources, six numerical sources and static constraints.
It compares complete individual-restraint gradients, identity-scattered sums,
singleton/full native containers and the unchanged manager. Every one of the
58 plane restraints is checked at both saved coordinate sets and both plane
orders. Three tilted controls exercise 4/4, 4/6 and 6/4 atoms, also both orders.

Each order retains three directions, four central-difference steps and complete
repeated arrays. The expected budget is 6,188 single/container evaluation pairs
under a 7,000-pair cap, plus two full-batch comparisons, with a 1,200 s timeout.
Native C++ header/binding sources are copied only if present beside the imported
geometry module; missing source is recorded and does not imply binary origin.
No optimizer, native patch, new crystal model, target edits or adoption occurs.
NARestraints selections/planes/weights and exact native gates remain fixed.

The 31 new regressions are covered by **101 focused tests (10.92 s)**; the
full suite passes **1,722 tests, two skips and 276 subtests (84.32 s)**.
The real 670-payload input passes the new source-bundled offline inspection,
including the exact 17-check prerequisite replay; deleted-build/poisoned-import
transport and explicit synthetic native-worker guards pass. Full-suite results
are recorded in the native evidence ledger. Those software checks remain
distinct from the returned installed result below.

All **732 returned payloads** verify, including 670 unchanged Cedar 23 payloads
and their manifest. The runner matches clean NASolve `5eb9d752…` /
NARestraints `a7b6a0c9…`; all 108 runtime members verify. Installed Phenix
**2.2.1-6174** (dispatcher `2.2.1`) completes in **3.483823 s**, exit zero,
with **6,188 evaluation pairs**. The exact initial manager, eight native APIs,
six numerical sources and static constraints match; all 17 prerequisites replay.

All **714 sampled individual-restraint directions pass**. Accumulation fails
at least one direction in **all 238 tested orders**: 116 at each saved
precision and six tilted controls. In every order, the first-plane direction
passes while the second-plane and alternating directions fail. Individual
gradients are invariant under plane-order swaps; accumulated gradients are not.
For the equal-size 4/4 control, the second-plane gradient norm is **2.21375**
individually and **exactly zero** after accumulation. Energies and repeats agree.

Both installed C++ source files match the recorded public blobs. The loop
starts the second-plane index at `i_size` but stops at `j_size`, retaining only
`max(0, j_size - i_size)` second-plane contributions. That model reproduces all
returned per-order accumulation arrays **exactly**. The full manager matches
the same incomplete batch gradient; it is not an isolated test-wrapper effect.
This confirms the defect in the tested installed path, without claiming every
version/overload or proving why the previous optimizer stalled.

Algebraically replacing only Cedar 23's parallelity gradient with complete
individual-restraint sums yields **84/84 passing sampled directional checks**,
explaining all 72 previous failures at the same energies and coordinates. This
is a saved-data replay, not a newly corrected manager or optimization. The
recombined full-precision full-gradient norm is 222.798, not the old incomplete
91.277; this is a different derivative calculation at the same endpoint.

**Cedar 25 returned and verified (2026-10-19): endpoints pass, initial sign review.**
`scripts/build_cif_corrected_gradient_probe.py` builds
`25_Cedar_probe_cif_corrected_gradient.py` from the verified 732-payload Cedar 24
return. `src/nasolve/cif_parallelity_correction.py` implements an explicit
NASolve-local evaluator: subtract only the native accumulated plane gradient
and add the complete original per-restraint i/j gradients by atom index.
The native energy and energy object, targets, weights, proxies, NARestraints
policy and installed Phenix files stay fixed. Already-correct native
accumulation is a no-op; symmetry-bearing planes and special positions fail
visibly. Production PostMR/refinement defaults are unchanged.

The new probe replays all 17 mechanics checks, pins the same eight native APIs,
six numerical modules, two adapters and two installed C++ sources, and matches
all three raw native snapshots before correction. It freshly evaluates four
central-difference steps at the initial coordinates, saved full precision and
PDB-rounded endpoint under the full objective and seven category controls.
Corrected gradient norms are recorded separately from the old incomplete
baselines. The 5,500-evaluation budget excludes five recorded preflight calls;
no minimizer runs. Sampled agreement is a derivative check, not scientific
approval. A deliberately bad single-restraint derivative remains visible in
regression tests.

The returned **794-payload** capsule verifies all 732 prior payloads and their
manifest, exact native input/output/worker sources and all 17 mechanics checks.
Installed Phenix 2.2.1-6174 / dispatcher 2.2.1 completes **4,101 evaluations
plus five preflight calls in 30.804996 s**, native exit zero. Native energy
change is **0.0**. Both endpoints pass **168/168** sampled directions; initial
coordinates pass **162/168**, retaining three failures each for full and
parallelity. Repeats/additivity pass throughout. The overall correction remains
**DERIVATIVE_REVIEW**; Cedar 22 remains **NOT_CONVERGED_ERROR**.

An independent centered-scatter spectral derivative and the installed header's
normal-sign branch reproduce the initial stored plane gradient within **3e-12**
in norm. Four ordinary stacks enter that branch: the header negates the second
normal but differentiates through its original row vectors without the matching
chain-rule sign. Both saved endpoints avoid the branch. Recombining spectral
plane derivatives makes **504/504 saved directions** agree at identical energy
samples and tolerances. This is source/model inference, not fresh native proof
of the second defect or the cause of the optimizer stall. The affected indices
in the evidence ledger are observations, never correction selectors.

**Cedar 26 returned and verified (2026-10-19): sampled native derivatives PASS.**
`scripts/build_cif_plane_order_probe.py` builds `26_Cedar_probe_cif_plane_order.py`
from the exact verified Cedar 25 ZIP. The evaluator adds an explicit
`plane_order_safe=True` policy: use i's first-plane block, copy the native proxy
with i/j reversed and use its first-plane block for j. Verify all copied
parameters, origin IDs and residuals; scatter shared atoms completely. The
manager's proxies, native full energy and other gradient terms stay fixed.
The existing accumulation-only policy remains the default. Symmetry-bearing
planes and special positions stay unsupported. No Phenix file is edited.

The worker pins the same native sources and static constraints, matches all
three raw snapshots and all three old complete/container plane arrays, then
runs fresh full-objective/category finite differences at all three cases.
A separate per-proxy audit checks all **58** planes in both orders, three local
directions and four steps. Six tilted controls cover 4/4, 4/6 and 6/4 atoms,
unrotated and after a 30-degree rigid rotation about x; energy and gradient
rotation invariance are checked. The rotation enters the normal-sign branch
without changing the physical plane angle. Original kernel failures remain
recorded alongside corrected derivatives.

Expected work is **4,101 global evaluations / 5,500**, **six preflight calls**
and **9,360 two-kernel plane-order pairs / 10,000**, with a 1,200 s timeout.
Local validation passes **30 new regressions**, **167 focused tests (18.98 s)**
and **1,788 full tests, two skips and 276 subtests (96.44 s)**. A deliberately
bad first-plane derivative remains visible; deleted-build/poisoned-import
transport and actual-input 794-payload offline replay pass. These software
checks are separate from the installed result below.

All **857 returned payloads** verify, including 794 unchanged Cedar 25 payloads
and their manifest. Runner `fd952513…` matches clean NASolve `628c2594…` /
NARestraints `a7b6a0c9…`; all 109 runtime members verify. Phenix
**2.2.1-6174** (dispatcher `2.2.1`) completes in **53.402075 s**, exit zero,
using the expected global/preflight/per-plane budgets. Independent saved-data
replay recomputes **504/504 passing global/category directions** and
**1,080/1,080 passing corrected per-plane directions**. All **360 plane
orders**, including 12 tilted/rotated controls, retain repeated arrays,
unchanged energies, order invariance and all three rotation controls.
The original native-complete kernel still fails 28 of 1,080 directions across
eight initial and six tilted/rotated orders; those failures remain recorded.
No optimizer or new crystal model was used in Cedar 26.

The corrected initial norm is **1,110.5207**, at the same **3,784.7499** target.
The corrected full-precision endpoint norm is **222.7981**, with rounded norm
**929.4534**. These differ from Cedar 22's incomplete native norms and cannot
be compared as a change in coordinates or convergence. Native energies change
by exactly zero. Eight API/six numerical/two adapter/two C++ fingerprints,
the full static signature and all 17 prior mechanics checks agree. This
qualifies the sampled correction for the captured supported installed profile;
it does not prove every gradient, native version, chemistry or convergence.

**Cedar 27 returned and verified (2026-10-19): mechanics/derivatives PASS; iteration limit.**
`scripts/build_cif_corrected_geometry_probe.py` builds
`27_Cedar_probe_cif_corrected_geometry.py` from the exact Cedar 26 ZIP.
The trial starts at the **same original initial coordinates as Cedar 22**,
using the unchanged native objective and the exact qualified both-first-plane
correction source. It does not continue from the prior unconverged endpoint.
Before any optimizer call, the host/native worker recompute the raw qualified
proof and require the exact native manager, source fingerprints, static
constraints, full corrected initial gradient vector and target. NARestraints
pairing recipes, plane mappings, stacking matrix and compiled selections stay
fixed; no relationships are guessed or compiled again.

The opt-in trial uses at most **1,000 iterations / 20,000 calls**, gradient
epsilon **1e-5** and a **1,200 s** native timeout. Preserve actual stopping
criteria/errors/limits. Fresh full-precision and PDB-rounded endpoint audits
use the same four steps, tolerances and frozen six probe atoms, with a separate
**4,000-evaluation** cap. Serialize a separate candidate by exact atom identity
and require all **17 native PDB mechanics checks** again. Stopping, derivative
qualification and native mechanics are independent; a lower target cannot
upgrade any failure or imply scientific approval.

Local validation passes **38 new regressions**, **205 focused tests (31.01 s)**
and **1,826 full tests, two skips and 276 subtests (107.25 s)**. The tests
exercise proof/source/manager drift before optimization, retained limit/error
stopping, and a deliberately bad endpoint gradient that remains REVIEW even
with a synthetic native criterion pass. Actual 857-payload offline inspection
and deleted-build/poisoned-import source transport pass. These worker checks
use explicit fakes; this Linux environment has no installed Phenix/Coot.

All **980 returned payloads** verify, including all 857 unchanged Cedar 26
payloads and their manifest. Runner `5cf0f2d2…` matches clean NASolve
`12d7fcc4…` / NARestraints `a7b6a0c9…`; all 110 runtime members verify.
Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes the corrected trial/audit in
**75.822869 s** and native PDB readback in **1.565038 s**, both exit zero.
All **17 exact mechanics checks** pass, preserving 877 atoms/43 sites, 38
backbone links, all definitions/proxies/compiled policy and native sources.
Candidate serialization reproduces byte for byte using exact atom identities.
Independent replay verifies all **336 passing endpoint directions** and
recomputes their **1,344 four-step samples**; 2,734 native audit evaluations
remain below the 4,000 cap. No captured source is executed in local replay.

The target changes **3784.7499458394077 -> 2697.762263611603 (28.72%)** and the
corrected norm **1110.520668509296 -> 372.53738052839816 (66.45%)**. The outcome
is **NOT_CONVERGED_LIMIT** at **1,000 iterations / 1,028 calls**: no recorded
optimizer error, native criterion false. All accepted targets decrease,
including **31.2321** from iteration 900 to 1000. Norms fluctuate, and the last
100 accepted steps span **109.81-456.05**; do not claim a nearby minimum or a
cause for slow convergence. The final target is 5.89% below Cedar 22's endpoint
under the same energy definition, without transferring its incomplete gradient
norms into this comparison. The rounded fixed-manager target/norm are
**2700.856094619088 / 905.6214940891548** and remain separate from full precision.

Both precisions retain **three nominal distance / ten angle deviations >=5**,
with **zero sign conflicts among 158 chirality proxies**. The three CGY A:20-DX
D:3 contact distances remain **4.4235 / 5.4261 / 5.6204 Å** versus 2.8 A targets;
nine angle outliers involve that pair. DP B:4 N5 remains **127.6378 degrees**
versus 109.471 degrees. Preserve these findings, pairing intent and recipe
targets; numerical descent does not resolve their scientific interpretation.

**Cedar 28 returned and verified: mechanics/derivatives PASS; iteration limit.**
`scripts/build_cif_geometry_continuation_probe.py` builds
`28_Cedar_probe_cif_geometry_continuation.py` from the verified 980-payload Cedar
27 ZIP. The reusable `continuation` opt-in recomputes the qualified endpoint
proof and preserves original source/policy/static identities. The native worker
first matches the original initial manager and corrected snapshot, then loads
Cedar 27's full-precision native atom-order coordinates and requires a fresh
match of the entire starting corrected gradient and target:
**2697.762263611603 / 372.53738052839816**. No rounded PDB is used as optimizer
state. The new L-BFGS history starts fresh; only coordinates are continued.

The stage permits **1,000 additional iterations / 20,000 calls**, epsilon
**1e-5** and a **1,200 s** timeout. It preserves prior stopping, actual new
stopping and cumulative optimizer iteration/call counts separately. Fresh
full/rounded endpoint derivative audits retain the **4,000-evaluation** cap;
all **17 native PDB mechanics checks** must pass again. Separate candidate:
`candidate/continued_geometry_model.pdb`. New-stage displacement from the prior
endpoint is recorded separately from original-model serialization displacement.

All **12 fail-before precondition regressions** now pass. The 36 new regressions
cover raw proof/policy/source defects, changed/rounded/reordered seeds refused
before the optimizer, all three native stopping outcomes, cumulative counts,
coherent captured-worker forgery, unsafe/duplicate/symlink capsules and deleted
builds with poisoned ambient/captured code. **241 focused tests pass (45.09 s)**.
The actual 980-payload source-bundled offline inspector and exact 17-check
mechanics replay pass. The full suite passes **1,862 tests, two skips and
276 subtests (122.57 s)**. Exact commands are recorded in the evidence ledger. These native-worker controls use explicit fakes; no installed
Phenix/Coot runs here.

All **1,104 returned payloads** verify, including the 980 unchanged Cedar 27
payloads and their manifest. Runner `61f64e79...` matches clean NASolve
`56101b09...` / NARestraints `a7b6a0c9...`; all 110 runtime members verify.
Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes the continuation/audit in
**76.066902 s** and native readback in **1.692405 s**, both exit zero. Original
manager and saved full-precision start/target/entire gradient match; installed
source identities, definitions, compiled NARestraints policy and static proxies
survive. All **17 mechanics checks** and **336 sampled endpoint directions**
pass. Independent review recomputes all 1,344 four-step samples/bounds and
candidate serialization byte for byte, without executing captured code.

The new target changes **2697.762263611603 -> 2599.5275576416398 (3.64%)** and
corrected norm **372.53738052839816 -> 144.16496914598542 (61.30%)**.
Stopping remains **NOT_CONVERGED_LIMIT**: **1,000 new iterations / 1,036 calls**,
cumulative **2,000 / 2,064**, no recorded error and native criterion false.
All accepted targets decrease; the last 100 iterations lower the target by
**8.7054**, with fluctuating corrected norms. Overall corrected-stage target
and norm drops are **31.32% / 87.02%**. PDB-rounded target/norm remain separate:
**2602.971189992592 / 950.90556704461**.

Both precisions retain **three distance / ten angle nominal deviations >=5**
and zero sign conflicts among 158 chirality proxies. CGY A:20-DX D:3 contacts
are **5.3540 / 4.3596 / 5.5828 A** versus 2.8 A, for N1-O2 / N3-N1 / N4-O6;
nine angle outliers involve that pair. DP B:4 C6-N5-C7 remains **127.7493
degrees** versus 109.471. Native target contributions are **1193.6456 angles**,
**553.0823 bonds**, **552.5565 dihedrals**, **225.9220 nonbonded**, **51.9768
parallelity**, **11.6966 planarity** and **10.6477 chirality**. Category gradient
norms can cancel; they do not add. The cause of slow convergence is not proven.

**Cedar 29 returned and verified: sampled rotation derivatives PASS.**
`scripts/build_cif_base_rotation_probe.py` builds
`29_Cedar_probe_cif_base_rotation.py` from the verified Cedar 28 capsule. The
reusable planner ranks nominal bond/angle outliers, then selects supported
connected base graphs without code/attachment-name allowlists. Offline actual
replay selects A:20, D:3 and B:4, each with 11 base atoms; N/C attachments and
unsupported cases have generic regression controls.

The diagnostic rebuilds the exact original native inventory and matches its
whole corrected initial vector, then both saved endpoint family targets and
entire gradients before any scan. Proper independent rotations about each
C1-prime/attachment axis preserve the scaffold, attachment and internal base
geometry. Nine fixed angular samples at full/rounded precision report the
unchanged full objective, isolated category contributions, selected scalar
measurements and source angle/type/plane context. Fresh four-step rotational
derivatives, baseline repeats, additivity, +/-180 periodic energy and rigid
distance controls remain independent outcomes. Limits are **six supported
groups / 3,000 total energy calls / 1,200 s**. All **17 preflight evaluations**
count toward the cap. A lower sampled target is not an adoptable model or a
minimum; internal base parameter conflicts remain visible.

All **17 initial fail-before regressions** now pass. **40 new tests** cover
generic graph/axis controls, an independent right-handed rotation oracle,
biased derivatives, incomplete/changed endpoint and source evidence, native
manager drift, budgets/timeouts, coherent captured-source forgery and deleted
builds with poisoned ambient/captured code. **88 focused pass (30.38 s)** and
**1,902 full pass, two skips, 276 subtests (136.61 s)**. The actual 1,104-payload
source-bundled offline inspector and exact prior mechanics replay pass. There
is no installed Phenix/Coot here; native worker tests use explicit fakes.

All **1,173 returned payloads** verify, with all 1,104 Cedar 28 payloads and
manifest preserved byte for byte. Clean build/runner hashes, 111 runtime files,
source/static identities and all 17 prerequisite mechanics checks replay.
Phenix **2.2.1-6174 / dispatcher 2.2.1** completes in **31.56962 s**, exit zero,
using **1,201/3,000** energy calls. All **96 rotational derivative directions /
384 four-step samples** recompute as consistent. Both precision cases retain
repeat/additivity/periodic/rigid controls. Each of A:20, D:3 and B:4 favors zero
degrees on the coarse grid. Nonzero validated slopes remain; this is no proof
of a minimum, complete pose search or scientific qualification. DP's retained
N5 targets still sum to **339.714 degrees** against a shared planar constraint.

**Cedar 30 returned: preserved input-parser failure, no candidate produced.**
`scripts/build_cif_numerical_recovery_probe.py` builds the next runner from the
exact Cedar 29 ZIP. The generic planner selects declared source plane/angle
reviews independently of residue name or model residual. This bounded probe
explicitly selects DP; five other eligible source contexts stay deferred.
The original 35 atoms, 37 bond declarations, explicit charges/H and four
chirality declarations survive a graph-only export. Old numerical targets and
energy types are excluded from the generator input, with all original fields
preserved in the frozen source. Complete declared source x/y/z seed naming and
initial geometry, explicitly labelled as non-independent ideal coordinates.

Existing isolated eLBOW generation/capability and chemistry/numerical gates are
reused. The candidate is compared against both the graph-only input and original
numerical source; complete formal-charge declarations must match. New raw
reviews/refusals remain visible. Up to three explicitly selected components and
a default **600 s per component** bound the candidate phase. No dictionary is
applied to a manager, no existing modifier is recomposed, and no crystal-model
optimization, policy recompilation, ReadySet retry, refinement or adoption runs.
All **47 new regressions** pass; **123 focused tests (13.63 s)**
and **1,949 full tests, two skips and 276 subtests (140.81 s)** pass.
Actual-input deleted-build/poisoned-import transport verifies 112 runtime files,
all prior evidence and the unchanged DP graph seed. Installed generation is
pending; exact validation commands and boundaries are recorded in the ledger. Existing geometry/convergence, charge, pucker, stereochemistry
and experimental gates remain independent.

All **1,185 returned payloads** verify, including the 1,173 unchanged Cedar 29
payloads and manifest. Runner `8aedfb0e…`, clean source pins and all 112 runtime
members match. The 17 mechanics/96 rotation prerequisites replay. Installed
eLBOW **2.2.1-6174** stops in **2.358774 s**, exit one, before producing any
candidate: its reader accesses `pdbx_model_Cartn_x_ideal`, while graph export
emitted the lower-case `cartn` spelling. Chemical rejection and generated
plane/angle assessment are **NOT_ASSESSED**, despite the wrapper's REJECTED and
zero-review console lines. No model was optimized or changed.

**Cedar 31 prepared: general tag-case correction plus the requested PDU control.**
The same builder accepts `--delivery-prefix 31_Cedar --component-control PDU`.
Canonical external CCD coordinate tags are emitted for both source ideal and
curated coordinate families. Old/corrected DP exports have exactly equal parsed
fields/values after tag-case normalization. The reader preserves the complete
Cedar 30 failure capsule and rechecks its predecessor proof before retrying.
Absent generated dictionaries now print numerical assessment NOT_RUN.

PDU is a separate **public component control**: its unmodified CCD fixture is
hash pinned under tests and is not added to the production curated library.
The source has **38 atoms / 23 heavy atoms / 39 bonds**, a C5A-C5B triple bond,
three specified D-sugar centres, and declared neutral phosphate state. Its O3-prime
hydrogen is named H2; the graph-based rule identifies the bond correctly.
The existing NARestraints row maps it to T, with the C7 plane role mapped to
C5A. Actual source-atom/compiler checks pass for the existing AT recipe
(two bonds/two angles/one pair parallelity) and both stacking orders. These
are compiler controls with a synthetic partner role template, not proposed
experimental/native pair geometry. DP and PDU generation remain independently
reviewed, with all chemistry/state rejection gates retained. No PDU site is
inserted into the frozen model. **23 new regressions, 146 focused tests
(16.16 s) and 1,972 full tests, two skips and 276 subtests (140.70 s)** pass.
The actual-input relocated runner passes after both clean source copies are
removed and ambient imports poisoned: 114 runtime files, all prior proof and
both graph sources verify. These were the pre-delivery checks; installed
results are recorded below.

**Cedar 31 returned and verified (2026-10-20): two execution failures; no dictionaries.**
All **1,209 payloads** verify, including every preserved Cedar 30 payload and
manifest. Rebuilding the trusted C31 runner at clean NASolve 36c75495 / pinned
NARestraints reproduces SHA-256 308c53d1; all 114 runtime members match. The
17 mechanics and 96 sampled rotational prerequisites replay.

Installed eLBOW **2.2.1-6174** (dispatcher 2.2.1) stops DP in **2.600242 s**
on absent alt_atom_id metadata. PDU runs **58.275747 s**: it reads 38 atoms /
39 bonds and three R/S/R sugar centres, performs RM1/GDIIS, reports geometry
not converged at the first 60-step limit (61 logged evaluations), then fails
loading a zero-byte candidate.elbow_opt.xyz with an UnboundLocalError for smc.
Both exit one without candidate.cif. The wrapper REJECTED values are execution
outcomes, not chemical rejection. PDU source/NARestraints compiler controls
still pass; generated chemical/numerical assessment remains NOT_RUN. Two
pickle outputs were excluded by the prior shuttle and are never loaded.

**Cedar 32 prepared: general alias compatibility and read-only native evidence.**
The exporter copies exact primary IDs into alt_atom_id only when the entire
alias column is absent; existing aliases and all chemistry remain unchanged.
The receipt records that added naming metadata. DP graph SHA-256 is
3cfff153966194861451113747ba8f1ebbd7b47d58c8aa9acfd50ddfcc4783dd;
PDU graph bytes remain unchanged. The same builder uses --delivery-prefix
32_Cedar --component-control PDU; the runner uses --native-contract-only.

Before another generation, capture four declared eLBOW modules under the
already verified installed library anchor, with exact bytes/hashes and a static
reader-attribute inventory. Run bounded installed read-only checks for both
prepared sources, with state-retention options and no optimizer request.
Source/dispatcher/snapshot checks surround these calls. This is an input-contract
diagnostic, not a Phenix patch, numerical candidate, chemical qualification or
policy change. Installed capture/checks are pending. All **29 new regressions, 175 focused
tests (19.02 s) and 2,001 full tests, two skips and 276 subtests (142.51 s)**
pass. Deleted-source/poisoned-import replay verifies all 115 runtime files,
1,209 prior payloads, mechanics/rotation proof and both graph sources. See
the native ledger for exact commands, hashes and scope.

**Cedar 32 returned and verified: PDU input PASS; DP dialect REVIEW.**
All **1,229 payloads**, the 1,209-payload predecessor and four exact installed
eLBOW source snapshots verify. Trusted runner 11d3946b matches clean NASolve
88bca3c1 / pinned NARestraints and all 115 runtime members. Prior mechanics and
rotation proof replay. Phenix 2.2.1-6174 read-only PDU exits zero in 1.371951 s;
DP exits one in 3.551229 s on missing atom pdbx_aromatic_flag. The source shows
the complete legacy/CCD dialect gap, including atom stereo and bond order.
The optimizer source confirms the empty-XYZ unbound-local path and a positive
opt_steps control that bypasses its default restart condition. Captured code
was inspected as text, never executed or patched.

**Cedar 33 prepared: checked reader projection and bounded candidate trial.**
Use the same builder with --delivery-prefix 33_Cedar --component-control PDU;
run against the exact Cedar 32 ZIP with --single-block-steps 180. A separate
consumer adapter translates only declared charge/order/flag aliases, refuses
conflicts and unsupported orders, and leaves unknown atom aromatic/CIP metadata
as ?. Original fields and signed chiral volumes survive. PDU input is unchanged;
DP consumer SHA-256 is
6b914d7fed9a98e30ed68b2381507e6d5bb0dc9b351fee48d42ced085c9501fa.

Fresh read-only checks gate each generator. Before any trial, the four installed
source identities must match, and the selected installed options parser must
prove exactly one block with 180 steps. Its module path/hash and default
tolerance are recorded and checked again after generation. Captured source is
not executed; only the installed parser is interrogated. Candidate generation
retains the 600-second per-component bound. No XYZ/pickle is reused, no native
code is patched and no tolerance is relaxed. Nonconvergence is reported as such;
exit zero/file creation never establishes a native criterion. All existing
source/consumer/numerical/formal-charge gates and raw reviews remain in force.
All **39 new regressions, 214 focused tests (24.58 s), and 2,040 full tests,
two skips and 276 subtests (155.92 s)** pass. Actual-input deleted-build and
poisoned-import transport verify all 116 runtime files and the complete
1,229-payload C32 capsule. Installed execution is pending; exact commands
and scope are recorded in the existing native ledger.

**Cedar 33 returned and verified: reader PASS; DP chirality failure / PDU candidate REVIEW.**
All **1,288 payloads** and preserved predecessor manifests verify. Rebuilding
clean NASolve d939d2e0 / pinned NARestraints reproduces runner 63cfbc19 and all
116 runtime members. Both installed read-only inputs pass, and both options
proofs select one 180-step block with unchanged default tolerance. Phenix
**2.2.1-6174** stops DP in **1.923945 s**, exit one, at preparatory
Chiralise/ChiralClass before optimization. The captured CCD reader stores every
stereo token except N as an atom chiral marker; all 35 DP tokens are ?. Its
four source signed-volume declarations are still preserved. Do not replace
unknown tokens with false nonchiral or invented R/S declarations to bypass it.

PDU generation completes in **155.347732 s**, exit zero, and writes candidate
10798e33 while explicitly reporting **NOT_CONVERGED_REPORTED**. Fresh original
chemical/numerical comparisons reproduce its review: exact graph, triple bond,
H and complete formal charges survive, with zero retained plane/angle findings.
All three R/S labels disappear, but three generated signed sugar terms agree
with both source ideal and generated coordinate handedness. This is not an
independent absolute CIP assignment. Its 181 printed energy rows reach
-517.4105 at row 146, rise to -477.2222 at 147 and end at -480.5612; no captured
intermediate coordinate trajectory establishes the cause. No dictionary is adopted.

**Cedar 34 prepared: read-only source/candidate and native reader stereo audit.**
Use the same builder with --delivery-prefix 34_Cedar --component-control PDU,
then the exact Cedar 33 ZIP with --component DP --stereochemistry-audit-only.
The gate preserves both returned phases, installed source/options proofs and
all prior native mechanics/rotation evidence. Offline checks compare missing
labels, exact chemistry, ordered signed targets and both coordinate hands;
absent/unsigned/unknown evidence stays review and inversions/conflicts reject.
Printed energy trajectories are descriptive, never convergence criteria.

The native diagnostic captures Utilities.py plus MoleculeClass.py,
TopologyMixins.py and ChiralClass.py under the verified installation anchor.
A maximum 30-second worker per component records actual reader markers and
separately exercises the reader's chirals=True constructor. It is not a full
builder replay. Constructor exceptions stay evidence; selected module identity,
snapshots, input and dispatcher hashes are checked throughout. No whole-molecule trial,
dictionary writer, captured source or serialized molecule is requested. Linux
subprocess controls are explicit fakes; the installed stereo result is pending.
The **55 new regressions**, **269 focused tests (31.11 s)** and **2,095 full
tests, two skips and 276 subtests (160.49 s)** pass. Actual-input replay verifies
all 118 runtime members after deleting both clean build copies and poisoning
ambient imports. The older-checkout tracked edit and local runner ignore survive.
Exact commands and bounds are recorded in the native ledger.

**Cedar 34 returned and verified: DP constructor assertion; PDU known-marker PASS.**
All **1,320 payloads**, the preserved 1,288-payload predecessor and all source,
worker and input hashes verify. Trusted runner ffc4d69a matches clean NASolve
efd63bd3 / pinned NARestraints and all 118 runtime members. The original 17
mechanics and 96 rotation checks replay; saved PDU stereo/trajectory summaries
also reproduce. DP marks every unknown token as chiral and fails the same
ChiralClass assertion; PDU's three known markers and constructor pass.

The captured code corrects the earlier constructor-scope description:
Chiralise invokes ChiralClass.Optimise on local templates, with native RS
notation. Legacy optimization/CIP NOT_RUN flags did not instrument these
operations. Preserve the historical receipts and this explicit interpretation;
no whole-molecule dictionary trial or saved source/candidate/model edit ran.
Future constructor reports use policy v2 and uninstrumented-internals fields.

The original DP has data_comp_list, but the graph export removed it. The
installed dispatcher therefore selects CCD instead of the monomer reader.
**Cedar 35 prepared:** an explicit source-dialect adapter preserves original
comp_list routing, source metadata, signed declarations and equal x/y/z aliases
in a separate target-free input. It invents no atom chirality, adds no old
numerical target/energy type and leaves PDU's CCD consumer byte-identical.
DP consumer SHA-256 is
4648c37ce867cce5a285d5f31a394a334b2cb9e347936511525a947927798bfa.

Use --delivery-prefix 35_Cedar --component-control PDU, then the exact Cedar 34
ZIP with --component DP --source-dialect-audit-only. A maximum 30-second selected
native parser read per component records dispatch and atom/bond/charge/coordinate
inventory, with exact dispatcher and monomer-parser snapshots. It requests no
chiral constructor or numerical generation; parser internals remain uninstrumented.
Raw mismatches retain review, and charge semantics/signed stereo remain separately
unqualified pending the returned parser source. All **41 new regressions**, **310 focused tests (36.04 s)** and **2,136 full
tests, two skips and 276 subtests (164.60 s)** pass. Actual-input transport
verifies 119 runtime members after removing both clean build copies and poisoning
ambient imports; tracked local edits and runner ignores survive. Documentation
mirrors, 148 relative links and the rendered editable figure pass. Exact commands
and bounds are recorded in the native ledger. Installed
source-reader acceptance remains pending; default generation is unchanged.

**Cedar 35 returned: pre-native temporary-path failure.** All **1,327 payloads**
and the preserved Cedar 34 capsule verify. The clean pinned runner matches;
the prior 17 mechanics checks and 96 rotation directions replay. Both graph
previews and the public PDU control match their predecessor. The receipt records
an empty consumer preparation and no native parsing or generation. The adapter's
internal TemporaryDirectory path hits the strict symlink-parent guard. A
synthetic aliased system temp root reproduces the exact error for both monomer
and CCD sources; the returned capsule does not capture the actual temp path.

**Cedar 36 prepared:** resolve only that newly created, tool-owned temporary
directory before the exact graph check. Preserve caller-output symlink and
overwrite refusals, exact source/consumer bytes and every chemistry gate. The
retry accepts the exact failed Cedar 35 capsule, preserves it whole and reads
its verified nested Cedar 34 source/constructor evidence. No chemistry-specific
exception, dependency or production-default change is introduced. All **16 new
regressions**, **132 focused tests (13.55 s)** and **2,152 full tests, two skips
and 276 subtests (173.76 s)** pass. The relocated runner replays all 1,327
actual payloads through an aliased system temp root after both clean build copies
are removed, with poisoned ambient imports and the everyday tracked edit intact.
Both consumer hashes are unchanged. Exact commands and bounds are recorded in
the native ledger.

**Cedar 36 returned: native reads complete; DP order/charge boundary exposed.**
All **1,355 payloads**, all byte-identical predecessor members, pinned clean
runner/build and 119 runtime members verify. The 17 mechanics and 96 rotation
checks replay. Both parser snapshots match in both native cases. PDU passes all
six raw route/inventory checks. DP preserves route, 35 atoms/elements, 37 bond
memberships, source coordinates and four signed markers, but every bond is
single and both source -1 charges are zero. The captured parser's lookup accepts
lowercase order words and defaults unknown spelling to single; its atom loop
reads no charge field. No new optimizer, generation or saved model change ran.

**Cedar 37 prepared:** translate explicit monomer order aliases to the exact
lowercase vocabulary, preserving order semantics and original source/graph
bytes. Separately test source-declared charge population on the temporary parsed
component using --declared-charge-control. Exact route/identities/elements/bond
orders/coordinates and complete integer charges bounded by the reviewed native
Chargise constraint are preconditions. Conflicts block assignment; only an
otherwise zero monomer object is populated by identity and source total.
Already-correct CCD charges are checked without assignment. Raw reader findings
stay separate; before/after recorded graph/stereo fields and a fresh host-side
inventory/total check accompany the control. Two additional Utilities/MoleculeClass
snapshots must match the verified Cedar 34 source proofs. No constructor,
Chargise, optimizer, generator or production-default change is requested.
All **48 new regressions**, **180 focused tests (22.36 s)** and **2,200 full
tests, two skips and 276 subtests (172.19 s)** pass. The relocated runner
replays all 1,355 actual payloads after both clean build copies are removed, with
an aliased temp root and poisoned ambient imports. It replays raw reader
findings, retains the tracked local edit and keeps PDU bytes unchanged. The
120-member runtime is verified; exact commands and bounds are in the native ledger.

**Cedar 37 returned:** all **1,387 payloads**, the clean pinned runner/build,
120 runtime files and byte-identical predecessors verify. All declared DP orders
now survive native reading. Its raw charges remain zero; the explicit control
passes, changing only OP2/OP3 to source -1 with total -2. Recorded graph,
coordinates and stereo fields stay fixed. PDU passes raw inventory and its
already-preserved charge control. No new generation or optimization ran.

**Cedar 38 prepared:** generic declared-triple-edge and neighbor selection,
exact installed resource/API capture, and fixed isolated component/native
comparisons. Read default monomer lookup, replay the captured installed CIF and
check the saved PDU candidate with the same seed/SS-disabled policy. Record active
distance/angle membership, targets, ESDs/weights, geometry and linear-axis
torsions; infer no replacement targets. Add hash-pinned public 5PC as an
independent C7/C8 naming control. Two 5PC workbook records remain ambiguous;
no role record or 5PC pairing/stacking policy is selected. General screening
thresholds are review policy, not chemical approval. The saved PDU candidate
still has six linear-axis torsions, bent coordinates and reported nonconvergence.
Native isolated triple-bond results await the selected Mac installation.
All **95 new regressions**, **159 focused tests (17.89 s)** and **2,295 full
tests, two skips and 276 subtests (185.91 s)** pass. The 124-member runtime
replays the actual C37 archive with raw/controlled charge checks after deleted
builds and relocation, with poisoned imports, an aliased temporary root and the
protected everyday edit intact. JSON mirrors, 149 links and the rendered editable
figure verify. Exact methods, commands and hashes are in the native ledger.

**Cedar 38 returned:** all **1,446 payloads**, clean published build/runner,
124 runtime files and exact nested lineage verify. Both default monomer
lookups return no component; native interpretations stop with 38/39 unknown
energy types. The supplied PDU candidate loads with active 1.174 Å / ESD 0.020 Å
and two 180° / ESD 3° terms, plus six linear-axis torsion reviews. Those native
coordinates are fixed public source seeds, not a repaired generated candidate.
No optimization, new generation, ReadySet retry or adoption ran.

**Cedar 39 returned and verified:** all **1,486 payloads**, the clean published
runner/build and 125 runtime members match. Both exact installed CCDs preserve
public chemical declarations and SMILES descriptor text. Both simple native
readers pass all six inventory checks. All four direct/wrapped numerical monomer
lookups are missing; DG/DC canonical controls resolve through GeoStd. Source
comparison and raw reader replay are independent of numerical restraint
qualification. No ReadySet, constructor, generation or optimization ran. Full
ReadySet selection, mapped SMILES, native stereo and geometry remain open.
Exact hashes, paths and scope are in the native ledger.

**Cedar 40 returned and verified:** all **1,529 payloads**, the clean published
runner/build and 126 runtime members match. Both accessors select CACTVS
canonical SMILES and 24 static source files fit the captured import budget.
ReadySet itself did not run. A static branch reads then deletes SMILES before
requesting chemical_component; observe the actual call before assigning cause.

**5PC policy review resolved in the auditor:** two existing cytosine-sheet rows
share all operational C-like roles and context. Descriptive aliases/entry counts
and modification-description columns do not make different atom mappings.
Equivalent role records now compile once with both raw rows retained; conflicts
and missing roles still review/fail. Explicit C5-mod/C7-mod annotations stay out
of atom inventories. A registered canonical partner precedes modified-family
synthetic controls, so 5PC checks G:C and both stacking orders. The existing
NARestraints workbook/recipes are correct for this scope; no edit/release is
needed under the user's conditional missing-entry authorization.

**Cedar 41 prepared:** original ReadySet API generation on separate fixed
heavy-atom source-seed PDU/5PC models. Observe unchanged builder/template calls,
retaining exceptions, fallback results and partial files. Each generation has a
180 s deadline; eligible output gets <=60 s native interpretation with SS off.
Raw source chemistry, dictionary targets and active triple terms stay separate.
Native internal template operations may optimize geometry; AM1/final-H options
are disabled. No linked scaffold, refinement or adoption is changed. Software
checks and exact provenance are in the native ledger.

**Current action:** build with --delivery-prefix 41_Cedar --component-control PDU
--component-control 5PC, then run the exact Cedar 40 ZIP with --component DP
--readyset-generation-audit-only under Phenix **2.2.1-6174** (dispatcher **2.2.1**).
Return console/review ZIP. DP is only the preserved prerequisite; the new
ReadySet controls are PDU and 5PC. Expect scientific REVIEW, not adoption.
Preserve the everyday checkout and all
earlier evidence. The ignored branch-artifact destination and merge-time
inventory/hash/archive policy remain in force. No new dictionary, native-model
result, policy guess or refinement is adopted. Private source snapshots, logs,
capsules, generated candidates and runners stay outside Git.

The prior membership implementation suite passed **1,646 tests, two skips and
276 subtests (71.72 s)**. Cedar 22 passes **107 focused (10.81 s)** and
**1,669 full tests, two skips and 276 subtests (76.03 s)**, including synthetic
deleted-build transport and actual-input offline replay. This Linux environment
has no Phenix; these checks do not claim a new native optimization. Exact
capsule, replay, native and descriptive evidence lives in the existing ledger.

**Cedar 20 returned and reviewed (2026-10-17):** all **367 payloads** verify,
including 311 byte-identical frozen Cedar 19 members. Runner `e38625e1…` matches
clean NASolve `7acca935…` / NARestraints `a7b6a0c9…`. Saved endpoints were reused;
no new optimization. Serialization reproduces candidate `27d534e3…` byte for
byte. Phenix 2.2.1-6174 completes its fresh native reread in **3.406067 s**, exit
zero; 877 identities/43 sites, component definitions, custom requests and all
19 CIF/12 PHIL bytes survive. Native dispatcher/four recorded API hashes match.

The original mechanics result correctly remains **11 PASS / three REVIEW**:
five extra simple bonds, ten extra angles and changed proxy counts. No original
proxy is lost or changed. All added rows have captured origin 2; each added bond
crosses the unchanged **3.4 Å** cutoff, and each gains two endpoint angles
through original covalent stems. Native logs report 25→30 hydrogen bonds and
50→60 associated angles, with the same 12 declared base pairs and 23 stacking
pairs. The effective native PHIL is byte-identical. These observations match
the public CCTBX distance-filter mechanism; the capsules do not fingerprint its
secondary-structure source, so this is cutoff-consistent attribution, not a new
installed-source causal experiment or a passed exact-manager comparison.

| Native contact | Before (Å) | After (Å) |
| --- | ---: | ---: |
| A:2 N1 – C:14 N3 | 3.458774 | 3.182690 |
| A:4 N3 – C:12 N1 | 3.484427 | 3.342721 |
| A:10 O6 – B:6 N4 | 3.983422 | 2.789232 |
| A:16 N6 – D:7 O4 | 3.626803 | 2.826950 |
| A:17 N4 – D:6 O6 | 3.420955 | 2.989775 |

Every reread coordinate matches Cedar 19's saved rounded vector at PDB precision;
maximum floating-component difference is **7.11e-15 Å**. Its recorded fixed-manager
PDB evaluation remains **3,679.853670**, gradient norm **978.673025**. This is a
preserved historical evaluation at that rounded vector, not a new energy of
the freshly rebuilt manager. The 500-iteration **NOT_CONVERGED_LIMIT** result
remains. Fixed captured proxies at the reread points give four bond/ten angle
nominal deviations at least five; the fresh manager has five/ten because it
contains additional terms. All 158 recorded chirality proxies have no sign
conflicts. None of these counts certifies geometry, pucker or experimental fit.

**Cedar 20 review outcome:** the Cedar 20 return is fully reviewed from saved evidence;
no repeated Mac/native inventory is needed. `cif_native_reload` adds reusable
read-only attribution and endpoint-equivalence reports without changing the
old checks, targets or production behavior. Origin/cutoff are explicit caller
evidence; synthetic origin 37/ZZZ tests prevent a hardcoded native-origin or
residue exception. Missing/changed terms, unpaired angles and other mutations
stay unexplained. No new native execution or geometry trial is delivered here.

**Next scientific gate:** prepare a geometry/convergence trial under Cedar 21's
verified explicit NARestraints-owned pairing and stacking policy. The accepted project
policy is that NARestraints pair selections, stacking relationships, mapped
planes and recipe targets supersede
Phenix's automatic secondary-structure guesses. The native consumer must apply
that policy without adding competing inferred contacts or silently dropping
intended contacts because their starting geometry is poor. Keep native geometry
measurement and component/covalent restraint validation independent of pairing
authority. This precedence is decided; the separate diagnostic compiler now
passes both returned native membership checks. Ordinary PostMR is unchanged.
Rebuilding from new coordinates can change that set even when all input bytes
are identical. Preserve the new terms in Cedar 20's historical evidence; do not
increase its cutoff or reclassify its failed comparison to manufacture PASS.
The new authority policy defines a separately documented objective. Its contact
compiler and bounded native membership checks pass; full qualification,
refinement and adoption stay open. The documentation ledger owns the exact
return, original checks and separate fixed-versus-fresh evidence.

**Pairing provenance for that gate:** reuse NARestraints' existing topology-assisted
pair guesser and recipe builder. At pinned source `a7b6a0c9…`, the guesser scores
mapped contact distances, angles and planes, then uses antiparallel run continuity
to rescue weak pairs and extend run ends. These are pairing hypotheses, not
independent confirmation of donor/acceptor chemistry or achieved geometry.
NASolve's opt-in `--modified-pairs-only` path already uses this guesser with
noncanonical recipes enabled, retains pairs touching a modified nucleotide and
writes explicit recipe restraints without stacking. This source inspection does
not establish that the frozen Cedar 20 declarations came from that mode.
Before freezing a future trial, trace NARestraints-guessed versus reviewed/frame-selected
pairs through recipe-mapped contacts to actual native proxies, retaining scores,
warnings and overlap evidence. Check missing, extra or doubly applied terms and
unresolved pairing chemistry; a fixed membership alone does not make a guess
correct. Phenix-inferred alternatives may be recorded diagnostically but do not
override or supplement the NARestraints-owned policy. The exact source record
and authority decision are in the existing native-reload ledger.

**Stacking authority is the same:** reuse NARestraints' general base-class plane
mapping and chain-neighbour stacking builder. Its twelve mapped classes share
reviewed A/T/G/C-like plane templates, including the corrected P/X versus Z/K
roles. Canonical neighbours are explicitly selected with native `stacking_pair`
records; mapped modified neighbours use explicit parallelities (target 0 degrees,
sigma 0.027). Both representations express NARestraints policy. A generic native
declaration is not permission for Phenix to infer different relationships.
Do not disable the entire secondary-structure machinery and thereby lose the
requested canonical stacks; preserve or explicitly compile those relationships.
Unknown mappings currently retain a generic declaration with a warning, so
actual native coverage still needs checking. Track stacking separately from
base-pair parallelity/planarity, verify planes/targets/weights and check missing,
extra or duplicate physical relationships on readback. This extends the decided
authority and is now represented by the separate diagnostic compiler; ordinary
PostMR is unchanged. The unchanged NARestraints stacking/role
tests pass **8 tests (0.33 s)** with
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ../check-venv/bin/python -m pytest -q --tb=short tests/test_stacking.py tests/test_modified_pair_roles.py`.

**Validation:** fourteen initial regressions fail before the audit module exists.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_native_reload.py tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_captured_geometry.py tests/test_cif_fragment_restoration.py`
passes **89 tests (3.18 s)**. The same command without file arguments passes
**1,628 tests, two skips and 276 subtests (72.30 s)**.
Actual capsule/serialization/mechanics replay and saved endpoint comparison
complete locally without a new native execution. New separate schema-1 audit
reports add no dependencies or private scientific payloads; existing receipt,
qualification and native gate behavior are unchanged.

**Cedar 19 returned; serialization continuation implementation (2026-10-17):** all
**310 payloads** verify, including 253 byte-identical frozen Cedar 18 members.
Runner `899562f5…` matches clean NASolve `5e848eba…` / NARestraints `a7b6a0c9…`.
Actual Phenix 2.2.1-6174 matches the captured manager and completes one native
trial in **2.805701 s**, exit zero. Fixed constraint signatures agree. It reaches
**500 iterations / 524 calls**, with no optimizer error, native criterion false
and final gradient norm **408.374112**: **NOT_CONVERGED_LIMIT**. The fixed-manager
target changes **35,629.733600→3,676.065436** (89.6826% lower); PDB-rounding energy
was separately evaluated at **3,679.853670**. This is numerical progress, not
convergence or scientific approval.

The runner then stops **before writing a candidate/native postcheck** because
its serializer incorrectly assumes PDB line order equals native hierarchy order.
All 877 atom identities are present; 157 have different positions in those
orderings. The general fix uses the supported single-model identity bijection
(chain, residue, insertion, alternate location, atom name), retaining component,
element and original-coordinate guards. Output record order/headers/metadata
remain exact, and each saved native endpoint maps to its own atom.

Offline replay of the actual saved endpoints writes all **877 coordinates**
correctly, candidate `27d534e3…`; maximum PDB rounding distance **0.000827 Å**.
RMS displacement is **0.980980 Å**, maximum **5.137862 Å**, so pose and later
scientific review remain material. Captured-proxy full-precision measurements
show four bond/ten angle deviations at least five and no recorded sign conflicts
among 158 chirality proxies. These are projected descriptive measurements, not
a new installed readback, contact inventory or stereochemical approval.

**Cedar 20 delivery:** use the same
`scripts/build_cif_fixed_geometry_probe.py` with `--delivery-prefix 20_Cedar`,
fresh `20_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`20_Cedar_probe_cif_geometry_trial.py`. The one-block ferry starts from
`19_Cedar_probe_build`. Run with `--completed-trial-zip` pointing to the exact
returned Cedar 19 ZIP; the normal Cedar 18 ZIP remains the independently verified
baseline. Both files already exist on the Mac. This path verifies the completed
capsule, frozen prior inputs, model/CIF/PHIL hashes, manager/native API equality
and fixed constraint signatures. It reuses the saved endpoints, preserves their
stopping evidence and performs **no new minimization**. It then serializes by
identity and executes the pending native PDB postcheck with unchanged restraints.
Existing exact identity/definition/full-proxy/count/custom checks still apply.
Both source ZIPs/frozen payloads, all earlier runs and source/charge reviews
survive; no captured script or pickle is executed. No new installation.
The returned Cedar 20 native postcheck is recorded above. Scientific
qualification remains REVIEW; no repeat of this delivery is required.

**Validation:** three initial identity-order regressions fail before the fix.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_fragment_restoration.py tests/test_cif_effective_source_recovery.py tests/test_cif_native_validation.py tests/test_synthetic_dna_shuttle.py`
passes **105 tests (7.71 s)**. The same command without file arguments passes
**1,612 tests, two skips and 276 subtests (73.75 s)**. Reordered
synthetic ZZZ, blank chains and distinct alternate identities pass; reuse never
calls the optimizer and altered native definitions still block the postcheck.
Actual completed-capsule inspection after deleting both build fixtures verifies
**310 source / 312 output payloads**, 104 runtime files and unused poisoned
imports. No new native execution is claimed by that transport proof. Additive
schema-1 fields record correspondence/mismatch counts and anchored saved-trial
reuse; production behavior, existing gates and runtime dependencies stay fixed.

**Cedar 18 returned and verified (2026-10-17):** all **252 payloads** verify,
including 130 byte-identical frozen Cedar 17 members. Runner `25004008…` matches
clean NASolve `6b1000bf…` and NARestraints `a7b6a0c9…`. Phenix 2.2.1-6174 eLBOW
completes in **28.738290 s**, CANDIDATE_REVIEW; both native phases complete
(exit zero, **3.055300 / 1.573842 s**). Dictionary checks are **68 PASS / one
UNSUPPORTED formal-charge readback**, without contradictions; fragment mechanics
are **14 PASS**. Source selection and generator inspection replay; linked
outputs and the nine-atom DF A:19 fragment candidate reproduce byte for byte.
Computed-scalar roundoff is at most **8.89e-13**. One charge-evidence array has
different dictionary iteration order; its atom-keyed content agrees exactly.
Generator pickles are deliberately excluded from review capsules and never
loaded. All 877 atom identities/43 sites and previous reviews remain preserved.

Definition and coordinate effects remain separate. With recovered definitions
fixed, the fragment phase changes bond deviations at least five **31→32** and
angles **72→72**; its inherited raw C4–O4 distance is **1.401011 Å** against
**1.218 Å**. The 158 chirality proxies have no recorded sign conflicts.
CGY–DX contacts remain **9.357476 / 6.818964 / 4.600879 Å** versus 2.8 Å targets.
Source/native mechanics are demonstrated; raw geometry, pair placement and
scientific qualification remain REVIEW. Different restraint objectives must
not be compared as like-for-like model rankings.

**Cedar 19 fixed-definition geometry trial implementation (2026-10-17):** the separate
trial first reconstructs the captured manager and requires exact identities,
coordinates, site definitions, full proxies/custom requests and native API
sources. It then runs one geometry-only scitbx L-BFGS trial with fixed definitions,
all installed geometry flags enabled and normalization false. Default limits
are **500 iterations / 10,000 calls / 1,200 seconds**; no repeated/adaptive cycles.
Special-position coordinates require a separate constraint policy and stop.
The receipt records symmetry, installed optimizer Python/compiled source hashes,
constraint signatures, per-term energies, gradients, actual stopping log,
accepted-step history and errors. Hitting a limit or a tolerated rounding
error cannot report convergence. Even NATIVE_CRITERION_MET is only the native
numerical criterion, not scientific approval.

Full-precision coordinates/energy and 8.3 PDB round-trip energy are distinct.
Only xyz fields change in a fresh candidate, preserving headers/metadata; report
per-site displacement and rounding. A new native interpretation must preserve
identities, effective definitions, all detailed proxies/counts and custom
requests, and match the exact serialized coordinates. Existing source/charge,
independent stereochemistry, pucker, separate contact/clash inventory, pose and
experimental approval remain open. Prior outputs and ordinary PostMR survive;
no target retuning, dictionary generation, ReadySet retry, diffraction input,
refinement, automatic selection or adoption runs.

**Delivery:** `scripts/build_cif_fixed_geometry_probe.py`, fresh
`19_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`19_Cedar_probe_cif_geometry_trial.py`; fetch from `18_Cedar_probe_build` and use
the one-block pinned Git ferry. The exact returned Cedar 18 ZIP is sufficient;
existing Python and Phenix 2.2.1-6174 suffice with no new installation. Explicit
options: `--review-zip`, `--output-parent`, `--phenix-root`, `--max-iterations`,
`--timeout-seconds` and `--inspect-only`. Completed analysis stays REVIEW/exit 2.
The returned optimization and remaining native round-trip are recorded above.

**Validation:** twelve initial regression failures precede the implementation.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_fragment_restoration.py tests/test_cif_effective_source_recovery.py tests/test_cif_native_validation.py tests/test_synthetic_dna_shuttle.py`
passes **91 tests (6.49 s)**. The same command without file arguments passes
**1,598 tests, two skips and 276 subtests (70.93 s)**.
Standalone worker/driver paths use explicit native fakes. Actual-input inspection
after both build fixtures are deleted verifies **252 source / 254 output payloads**
and 104 runtime files, with poisoned imports unused. This proves transport,
not installed Phenix minimization. Separate schema-1 diagnostics add no new
runtime dependencies or private scientific payloads to Git; existing production
behavior and gate schemas are unchanged.

**Cedar 18 effective/source recovery implementation (2026-10-16):** generic source
selection requires an unsupported effective scaffold, one recorded original
component/input index, an exact source SHA-256/size match in an explicitly
supplied resource inventory, and a supported source DNA graph. Matching uses
content/hashes, not component or filename exceptions. Missing/ambiguous/changed
sources, unsupported source graphs, incomplete shared-code contexts and prior
site modifiers without a composition policy are blocked. The actual plan
selects only DF A:19; eight supported contexts remain unchanged. DF's original
source `27f83c85…`, 8,941 bytes, has **single** sugar bonds. The aromatic
declarations belong to the **effective** dictionary, not that frozen source.

The diagnostic reuses source-preserving whole-component eLBOW generation and
linked preparation. Source atoms/H/bonds/formal charges/stereochemistry and
explicit internal links are checked before native projected-definition,
unaffected-proxy, custom-restraint and modifier-ID gates. The first native
trial holds all Cedar 17 coordinates fixed. Only PASS checks and the separately
reported unavailable formal-charge API allow a diagnostic continuation;
contradictions and all other REVIEW/UNSUPPORTED states stop it. A second phase
restores only the newly supported fragment and validates its identities,
definitions, full proxies and exact coordinates against the fixed recovered
manager. Definition and coordinate effects have separate reports; objectives
with changed targets are not comparable model-quality rankings.

**Delivery:** `scripts/build_cif_effective_source_recovery_probe.py`, fresh
`18_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`18_Cedar_probe_cif_source_recovery.py`; use the one-block ferry from
`17_Cedar_probe_build`. The exact Cedar 17 ZIP supplies prior inputs.
Existing Python/Biopython and Phenix 2.2.1-6174 with eLBOW suffice; no new
installation. Explicit options are `--review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds`, `--source CODE=/explicit/path` and
`--inspect-only`. Captured dispatcher/four API hashes are checked before/after;
the selected eLBOW dispatcher/capabilities are recorded. Successful analysis
remains REVIEW/exit 2. Dictionary generation may optimize its independent
component; model minimization, pairing-pose changes, ReadySet retry, refinement,
production integration and adoption do not run. Return console output and ZIP.

**Validation:** eight initial regressions fail before the new module exists.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_effective_source_recovery.py tests/test_cif_effective_source_recovery_probe.py tests/test_cif_generation.py tests/test_cif_linked_preparation.py tests/test_cif_terminal_qualification.py tests/test_cif_fragment_restoration.py tests/test_synthetic_dna_shuttle.py`
passes **140 tests (19.27 s)**. The same command without file arguments passes
**1,568 tests, two skips and 276 subtests (112.10 s)**. Generic `ZZZ` covers
recorded-hash selection, graph/source/modifier guards, strict continuation,
phase ordering with explicit native fakes and deleted-build transport. Actual
Cedar 17 planning after deletion of both build fixtures verifies **129 input /
133 output payloads**, with poisoned imports unused. Generation and both installed native phases are verified in the returned result above. Existing production behavior,
inventory/gate schemas and originals are unchanged; separate schema-1
diagnostics add no dependencies or private scientific payloads to Git.

**Cedar 17 returned and verified (2026-10-16):** all **129 payloads** verify,
including 75 byte-identical frozen Cedar 16 members. Returned runner SHA
`d611965d…` matches clean NASolve `274f2043…` and NARestraints `a7b6a0c9…`.
Phenix 2.2.1-6174 completes in **5.215362 s**, exit zero; all **14 mechanics
checks pass**, preserving 877 identities/43 sites, 18 dictionaries/11 parameter
files, effective definitions and every detailed proxy/target/weight. Preparation
replays byte for byte. Native/predicted and offline report comparisons agree
except computed-scalar roundoff at most **8.89e-13**; no raw input or target is
normalized. Aggregate REVIEW and prior source/charge limits remain.

Native measurements confirm 34 bond/72 angle nominal deviations at least five,
with zero recorded chirality sign conflicts. Intrasite counts improve
41→24 bonds and 52→22 angles; intersite counts are 9→10 and 55→50. Lower totals
do not establish a pairing-pose repair. Three CGY–DX contacts are 9.357476,
6.818964 and 4.600879 Å versus 2.8 Å targets; they were 8.963664, 2.947120 and
2.736735 Å before the fragment candidate. The latter two worsen despite
restored base integrity. Retain this evidence for a later separate pose/
geometry intervention. DF source/effective recovery comes before optimization
against those changed sugar definitions.

**Cedar 17 separate restoration implementation (2026-10-16):** the returned
stage evidence below reproduces a coordinate-restoration defect. The new
`cif_fragment_restoration` diagnostic keeps the reviewed sugar/phosphate and
transports each complete, graph-selected base fragment from raw Coot into the
preserved C1′/O4′/C2′ frame by a proper rigid rotation. It borrows no canonical
parent base atom by name. The supported graph requires the complete explicit
DNA scaffold, one connected heavy-atom base attached once at C1′, exact
component/element correspondence and unambiguous single-model coordinates.
Unsupported attachments, aromatic sugar bonds, alternate/insertion contexts,
degenerate frames and changed parent/source correspondence are refused.

All nine original parent-controlled contexts are assessed. Eight qualify;
DF A:19 retains UNSUPPORTED because its captured C1′–C2′, C2′–C3′ and C3′–C4′
bonds are aromatic. That entire site stays unchanged. The candidate changes
84 base-atom coordinates, preserving all scaffold/unselected coordinates,
identities, metadata and all 877 model atoms. Raw fragment distances including
the C1′ attachment change by at most **0.001040 Å**, within the explicit
0.002 Å PDB-rounding guard. This is not a chemical acceptance threshold.
Captured-proxy prediction reduces bond deviations at least five **50→34**
and angles **107→72**, with zero recorded chirality sign conflicts. It clears
48 of the 55 previously recorded crossings; remaining raw/sugar/source problems
stay visible. DX C2–O2 becomes 1.340133 Å; its 1.215 Å target is unchanged.
No minimization or full geometry approval is claimed.

**Delivery:** `scripts/build_cif_fragment_restoration_probe.py` builds
`17_Cedar_probe_cif_fragment_restoration.py` from a fresh `17_Cedar_probe_build`
and the existing pinned NARestraints source. Use the one-block ferry from
`16_Cedar_probe_build`. The exact returned Cedar 16 ZIP supplies all frozen
inputs; no read of the original run is needed. `--review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds` and `--inspect-only` remain explicit.
The default native trial uses Phenix 2.2.1-6174, checks the captured dispatcher
and four native API source hashes before/after, and interprets the candidate
with the unchanged 18 dictionaries and 11 parameter files. Every native atom
identity, site definition, custom request and detailed proxy/target/weight
must match the capture; observed coordinates must match the exact candidate.
The captured baseline is not re-executed. Source/charge reviews are preserved.
Successful mechanics still retain REVIEW/exit 2. Return terminal output and
the new review ZIP before selecting a later intervention or adoption.

**Validation:** thirteen initial synthetic regressions fail before the new
module exists. The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fragment_restoration.py tests/test_cif_fragment_restoration_probe.py tests/test_cif_construction_provenance.py tests/test_cif_construction_probe.py tests/test_synthetic_dna_shuttle.py`
passes **51 tests (7.28 s)**. Synthetic `ZZZ` includes N- and C-linked and
misleading-name bases, rigid reorientation, shared-code site isolation,
aromatic-sugar/multi-attachment/disconnection refusals, source/parent/frame
guards, native success/failure fakes and deleted-build transport. The same
command without file arguments passes **1,543 tests, two skips and 276 subtests
(126.63 s)**. Actual-input relocation after deletion of both build fixtures
verifies all 74 source and 80 output payloads, with poisoned imports unused.
The complete receipt is recorded in the
[evidence record](cif-linked-native-registration-evidence.json).
The installed result is recorded above. Production PostMR,
existing schemas/gates and all original runs remain unchanged; separate
schema-1 diagnostic kinds and no new dependencies/private payloads enter Git.

**Cedar 16 returned and verified (2026-10-16):** all **74 payloads** verify,
including 52 unchanged Cedar 15 members and 19 recorded original artifacts;
the optional normalized model and PostMR report remain absent. Returned runner
SHA-256 `b87ed97f…` matches clean NASolve `4e81f5ca…` and pinned NARestraints
`a7b6a0c9…`. The report replay matches all identities, statuses and counts,
with only 62 computed-scalar differences at most **2.85e-14**. It records 93
findings over 21 sites: first observed at MR input 25, raw Coot 10, restored
55, and not located three. All **55** adjacent crossings are raw→restored,
at eight sites. The later synthetic E:1 control is absent from this original
run and accounts for all three unlocated cases.

Replaying `_restore_shared_parent_coordinates` on the frozen raw model and all
nine saved parent controls reproduces `after_coot_geometry.pdb` **byte for
byte** (70,798 bytes, `d12d171b…`). This establishes the legacy same-name/
same-element coordinate-copy algorithm as the reproducible damaging operation
for these captured transitions. It does not explain every raw/MR outlier or
certify source chemistry. DX C2–O2 was already 1.340398 Å in raw Coot, then
became 5.129713 Å; CGY N1–C2–C1 changed 118.960748°→4.434092°. The original
read-only receipt correctly retains root cause NOT_ESTABLISHED; this subsequent
controlled replay supplies the narrower causal evidence. No original file,
target, native manager, optimization, refinement or production path was changed.

**Cedar 15 returned and verified (2026-10-16):** all **51 payloads** in
`15_Cedar_01pvz5n5_cif_geometry_review.zip` verify. All 47 frozen native members
are byte-identical to Cedar 14. The returned runner SHA-256 matches
`5ce0ce42372e5d6ee774fcd161fc93d39d065f333ef3ae0b30b0ea1b1558495e`,
from clean NASolve `5733bb290dada1edde98a52ddb815d7ad13e823f` and pinned
NARestraints `a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Analysis completes
with deliberate REVIEW, preserving the archive/model and running no new native
interpretation. Offline report replay matches identities, targets, weights,
statuses, ranks and counts. Only computed scalar values show platform roundoff:
722 repeated/report fields differ by at most **7.11e-14**, within the explicitly
checked 1e-10 absolute replay tolerance; no input or gate is normalized.

The returned inventory confirms 1,026 measured bonds (50 nominal absolute
deviations at least five), 1,590 angles (107) and 155 chirality proxies (zero),
with no sign conflicts against the recorded chirality targets. These are
descriptive Cartesian comparisons, not native residuals or full geometry approval.

The largest intrasite deviations expose existing model distortions. Comparison
uses only dictionaries declared by the captured receipt, selected by component
content; their coordinate values are evidence, not replacement targets:

| Measurement | Captured model | Dictionary coordinates | Native target |
| --- | ---: | ---: | ---: |
| DX D:3 C2–O2 distance (Å) | 5.129713 | 1.215504 | 1.215 |
| DX D:3 C7–C8 distance (Å) | 2.881660 | 1.368845 | 1.369 |
| CGY A:20 N1–C2–C1 angle (°) | 4.434092 | 123.779864 | 123.78 |

Identity-matched lineage comparison proves all **858** Cedar 05 model atoms
survive in the later 877-atom shared-context control with **zero coordinate
displacement**. Thus these distortions predate the linked/terminal dictionary
diagnostics. This does not identify the responsible construction step or prove
the complete source chemistry. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the exact return hashes, replay and source/coordinate comparison details.

**Next bounded work:** trace original Coot construction, canonical-parent
restoration and atom correspondence using frozen before/after models and
mutation receipts. Select suspect sites by measured graph/geometry evidence;
do not build a component-name exception list or retune dictionary targets to
fit these coordinates. Source-versus-model agreement narrows the investigation
but does not establish a mutation or restoration bug by itself. Root cause
remains NOT_ESTABLISHED. Cedar 16 above now collects that missing stage evidence;
coordinate repair, minimization, full native geometry/refinement and adoption
remain separate gates. The Cedar 15 return changed documentation/evidence
only; later runtime validation is recorded in the current delivery above.

**Cedar 15 captured geometry implementation (2026-10-16):** the user requested
the next script. This bounded diagnostic reads the exact verified Cedar 14 ZIP,
checks all 141 payloads, and materializes only the captured candidate's 47
anchored native members. It measures simple-bond distances, angles and ordered
chirality volumes from recorded Cartesian manager sites. It preserves all
coordinates, dictionaries and prior qualification outcomes, and runs no new
Phenix interpretation, ReadySet, optimization or refinement.

The reusable `cif_captured_geometry.review_captured_geometry` API validates
atom/index/label/coordinate correspondence and proxy detail counts. It retains
all measured, unsupported, zero-weight and degenerate rows. The signed nominal
deviation is `(observed - target) * sqrt(recorded weight)`; recorded `both_signs`
uses absolute ordered volume. This is a descriptive ranking, **not a native
residual or acceptance gate**: the capture lacks some symmetry/slack/top-out
conventions. Nonidentity bond symmetry is unsupported. Angle/chirality values
describe the recorded Cartesian endpoints without inferred symmetry transforms.
Dihedrals, planes, parallelities, ASU bonds, pucker, absolute stereochemistry
and complete geometry qualification remain explicitly unassessed. No source
defect, target change or chemical approval is inferred from a large score.

Actual-input replay measures **1,026 bonds, 1,590 angles and 155 chirality
proxies**. Nominal absolute deviations at least five occur at 50 bonds and 107
angles; none occurs among chirality proxies, and no recorded chirality sign
conflicts are observed. These describe the existing unoptimized model. Existing
source reviews and nine unavailable formal-charge readbacks stay open.

**Completed delivery:** `15_Cedar_probe_cif_geometry_review.py` was built with
`scripts/build_cif_geometry_review_probe.py`, the new pinned
`15_Cedar_probe_build` and existing `05_Cedar_narestraints_build`. Use the
one-block `fetch && worktree && build && run` ferry from the preserved
`14_Cedar_probe_build`. The default input is the returned Cedar 14 path;
`--review-zip` and `--output-parent` remain explicit overrides. The runner uses
Python's standard library and needs no new installation or Phenix argument.
It writes `captured_geometry_review.json`, a short `summary.txt`, provenance,
frozen evidence and a new review ZIP. Successful analysis deliberately returns
**REVIEW/exit 2**; return that output/capsule for review. Full scientific
qualification and a later geometry intervention remain separate decisions.

**Validation:** all 13 scalar regressions fail before the module exists, then
pass. The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_captured_geometry.py tests/test_cif_geometry_review_probe.py tests/test_synthetic_dna_shuttle.py`
passes **30 tests (3.94 s)**. The same command without file arguments passes
**1,501 tests, two skips and 276 subtests (111.78 s)**. Synthetic `ZZZ` fixtures
cover rigid motions, reflected/unsigned chirality, zero/missing/negative
weights, inconsistent captures, deferred categories, capsule tampering and
deleted-build/poisoned-import transport. A separate actual-input relocation
also completes after both source-build fixtures are deleted; all **51** output
payloads verify and the Cedar 14 ZIP is unchanged. The user return above also
verifies the same complete captured-evidence analysis. This is captured-evidence
analysis, not new installed-tool execution. Schema 1 gains only a new diagnostic
report/receipt; existing inventory, qualification and production formats/gates
are unchanged. No private scientific payloads enter Git. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the methods, exact input hash and software/transport receipts.

**Cedar 14 returned and verified (2026-10-16):** all **141 payloads** in
`14_Cedar_7qm2tnry_cif_outgoing_bundle_review.zip` verify, including every
anchored native input/output and all 35 unchanged Cedar 12 materialized members.
The runner hash matches `487d8aa2…` from clean NASolve
`56d4dae912e36dd7cfe8d905a68e1d09412546a2` and pinned NARestraints
`a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Both installed Phenix
**2.2.1-6174** interpretations completed, exit 0 (5.903950 s / 1.358828 s).
Qualification records **138 PASS and nine UNSUPPORTED formal-charge checks**;
no individual check remains REVIEW, but the aggregate remains **REVIEW**.
Offline replay reproduces all 147 outcomes and evidence after sorting only
unavailable-charge items by atom ID. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the exact archive, receipt and qualification hashes.

All four curated outgoing-O3′-H findings clear, and all **38** outgoing-H
audits pass. The native modifier IDs are exactly prior `NASnoOP3` plus the
selected new ID; all six projected-definition categories, including atom types,
match.
Captured-baseline replay, all unselected definitions, every recorded unaffected
proxy, reviewed 5CM torsion/alternate, 38 links and custom 21/34/8/23 coverage
pass. The same 877 coordinate atoms and 43 sites are preserved. Both managers
contain 1,026 simple bonds, 1,590 angles, 155 chirality proxies, 387 constant
dihedrals, 571 dihedrals, 58 parallelities and 54 planes. Equal totals alone
are not the proof: full recorded rows are compared by the qualification gates.
The candidate appends four dictionaries and four parameter files to the
unchanged 14-dictionary/seven-parameter baseline.

**Generality:** the preparation rule uses explicit links, the H/D bond graph
and captured canonical type authority; it has no four-component or hydrogen-name
allowlist. Existing regressions use synthetic `ZZZ`, misleading H names and D,
same-code outgoing/free-end contexts, retained OP2 H and terminal phosphate.
They also reject missing contexts, changed authorities/inputs and coordinate-H
deletion; qualification guards exact modifier IDs and retained numerical rows.
This establishes reusable behavior within the declared OH1 O3′–C3′/H motif.
The Cedar probe remains hash-bound to its reviewed experiment. Other chemistry,
the source-specific 5CM correction and production integration keep their own
authority and qualification requirements; arbitrary-component support is not
established by this result.

**Next bounded work:** review the remaining source/numerical/stereochemical
evidence and define geometry qualification from this validated bundle, preserving
the original coordinates and manager. The nine charge readbacks are unavailable
in this API, with no contradictory values or partial-charge substitution;
repeating the unchanged inventory does not resolve them. The added terminal H
formal charge remains unassessed, and 1AP/DP Doctor source assessments remain
REVIEW. Achieved geometry, experimental protonation, refinement, human review
and production adoption remain separate gates. Cedar 15 above now implements
the next descriptive evidence slice; no model editing, optimization, ReadySet retry, refinement
or adoption occurred. Runtime and schemas are unchanged. The existing Cedar 14
software suite below remains the latest code validation; this documentation-only
change adds capsule/replay, JSON, link and figure verification.

**Cedar 13 return and Cedar 14 launcher correction (2026-10-16):** all 58
payloads in `13_Cedar_4o9_vhuk_cif_outgoing_bundle_review.zip` verify, including
35 unchanged frozen members and 24 passing source/native projection checks.
The user runner hash matches `68a2b9ae…` from clean NASolve
`5295992209fc1435b260bc926c89d54208fd7a83` and the same pinned NARestraints.
All four candidates completed preparation. The runner then passed an empty
default `--phenix-root` to `installation_from_candidate`, reproducing the
returned `NoneType` path error. No new native interpretation was reached;
the REVIEW capsule is not a native chemistry verdict.

The corrected template defaults to
`$HOME/Applications/phenix-2.2.1-6174`, matching Cedar 12's working selection,
and retains `--phenix-root` for explicit relocation. Only launcher selection
changes; the four candidates and all authority/qualification gates are unchanged.
The new regression keeps the actual installation loader and executable/version
discovery, with explicit external-program shell fixtures. It fails before the
fix for the omitted option while the explicit path already passes (one failed,
one passed, 12 deselected), then both pass after the fix.

**Completed delivery:** `14_Cedar_probe_build` at
`56d4dae912e36dd7cfe8d905a68e1d09412546a2` built
`14_Cedar_probe_cif_outgoing_bundle.py` with `--delivery-prefix 14_Cedar`.
The user ran the one-block conditional Git ferry with explicit `--phenix-root`.
Input remains the preserved Cedar 12 ZIP; retain all builds, runners and capsules.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_outgoing_bundle_probe.py tests/test_phenix_runtime.py tests/test_synthetic_dna_shuttle.py`
passes **27 tests (18.67 s)**. The same command without test-file arguments
passes **1,480 tests, two skips and 276 subtests (118.05 s)**. A Cedar 14
actual-input inspect-only run succeeds after both original build trees are
deleted, with poisoned imports unused; all 58 payloads verify and the original
Cedar 12 ZIP is preserved. This is preparation/transport evidence, not installed
Phenix execution. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the full-suite and retry receipts. Installed Cedar 14 execution is verified
above; no optimization/refinement or adoption occurred.

**Cedar 13 outgoing candidate implementation (2026-10-16):** the user authorized the
next source review and validation delivery. All 24 complete curated-to-native
projection checks pass on the exact Cedar 12 inputs. The bounded candidates
remove only graph-identified O3′ H at 1AP A:5 (`HO31`), 5CM A:7 (`HO3'`),
DZ A:12 (`H2`) and DP B:4 (`H3`). Their projected dictionary atom counts are
34, 33, 33 and 33. The O3′ OC2 authority is captured canonical DC A:4, with
only C3′ adjacency; its partial charge and numerical targets are not copied.
Existing `NASnoOP3` and all other modifiers remain; four new per-site modifier
IDs compose with them. Source dictionaries, parameters and coordinates stay
unchanged. True free 3′ ends and retained OP2 H are protected generically by
explicit context and graph, including H/D with misleading names.

`prepare_outgoing_component` is a separate diagnostic layer for captured
curated inputs, not a whole-component generation pass or production repair.
It verifies every anchored native input/output and exact source projection,
refuses coordinate-H deletion and changed/unsupported authorities, and records
before/after Doctor assessments. Existing 1AP and DP assessments remain REVIEW;
5CM and DZ assessments pass. No replacement targets or charge values are guessed.

The new native probe replays Cedar 12 unchanged, then interprets the selected
bundle. Qualification retains all existing gates and adds full captured-baseline
replay plus exact old/new modifier IDs at every site. It checks all 38 declared
outgoing endpoints, all four projected numerical definitions, the corrected
5CM torsion/alternate proxy and all unselected definitions and unaffected
proxies, including the earlier IGU terminal/internal contexts. The dispatcher,
four captured native API sources and prior terminal authorities must match
before and after. Every materialized input is rechecked, and the original ZIP
is preserved. Formal-charge readback remains unsupported in the captured API;
adding the three newly checked curated sites can increase those findings.
Successful interpretation may therefore still end at REVIEW/exit 2.

**Original delivery:** `scripts/build_cif_outgoing_bundle_probe.py`, new
`13_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, output
`13_Cedar_probe_cif_outgoing_bundle.py`. Supply the exact published full-SHA
Git ferry in one `&&` subshell. The default input is the returned
`12_Cedar_q46plqwk_cif_terminal_bundle_review.zip`; `--review-zip`,
`--output-parent`, `--phenix-root`, `--timeout-seconds` and `--inspect-only`
remain explicit overrides. Preserve the frozen everyday checkout and all
earlier deliveries. Cedar 13's installed selection stopped as recorded above;
Cedar 14 carries the launcher correction. Local native checks use explicit
fake APIs or offline returned inputs.
No ReadySet retry, optimization, refinement or adoption is part of this trial.

**Validation:** six selected graph/H-D regressions fail before the new module
exists (11 deselected). The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
with `tests/test_cif_outgoing_preparation.py tests/test_cif_outgoing_qualification.py
tests/test_cif_outgoing_bundle_probe.py tests/test_cif_terminal_preparation.py
tests/test_cif_terminal_qualification.py tests/test_cif_terminal_bundle_probe.py
tests/test_cif_native_validation.py tests/test_cif_linked_preparation.py
tests/test_cif_linked_qualification.py tests/test_synthetic_dna_shuttle.py`
passes **138 tests (16.44 s)**. The same command without test-file arguments
passes **1,478 tests, two skips and 276 subtests (124.12 s)**. A successful
actual-input `--inspect-only` trial also runs from a relocated runner after
both original build trees are deleted, with poisoned imports unused. All 58
review payloads verify, and the original Cedar 12 ZIP is unchanged. This is
preparation/transport evidence, not installed Phenix execution. The
[native evidence record](cif-linked-native-registration-evidence.json) owns the
complete software/transport receipts. Schema 1 gains a new diagnostic
preparation receipt and qualification policy; existing receipt formats,
generation gates and production behavior are unchanged. No new runtime
dependencies or private native payloads are added to Git.

**Cedar 12 returned and verified (2026-10-16):** all **116 payloads** in
`12_Cedar_q46plqwk_cif_terminal_bundle_review.zip` verify. The runner SHA-256
matches delivery `2144968031c659f69c4d71eb81f1aeb8ef7d79962c45e03daa4bfe2460352845`,
from clean NASolve `e5b1be6198eae73fedbc497d003502bfb31c2247` and NARestraints
`a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Baseline and candidate native
interpretations completed under Phenix **2.2.1-6174**, both exit 0
(5.651856 s / 1.256861 s). Qualification is **95 PASS, six UNSUPPORTED
formal-charge checks and four REVIEW outgoing-O3′-H checks**; aggregate
**REVIEW**, not complete scientific approval. Offline qualification replay
reproduces all 105 outcomes and evidence after sorting only unavailable-charge
items by atom ID. The [native evidence record](cif-linked-native-registration-evidence.json)
owns the exact hashes, checks and preservation evidence.

The source-bundled probe reuses the
exact Cedar 09 shared-code control and Cedar 11 installed numerical authority.
It verifies all 207/nine payloads, materializes only declared members and
preserves both original ZIPs. `prepare_terminal_component` wraps the existing
linked preparation; only free-OH contexts receive captured native O5′/H atom
operations, bond and angle. Actual-input offline replay produces E:1 with
32 dictionary atoms and leaves the 34-atom A:6 internal plan and shared base
byte-identical. All retained formal charges stay unchanged; the new H formal
charge is `?`, never copied from its native partial charge. No H coordinates
or new numerical targets are invented.

The selected candidate also explicitly reproduces reviewed 5CM output
`61bf14a1…`. Its native projection removes only the declared OP3. Baseline and
candidate use the same 877-atom/43-site coordinate control; no optimization.
New detailed schema-1 fields record neutron bond targets and torsion alternates.
Qualification retains all existing gates and adds exact projected numerical
rows, the corrected 5CM `C2e-nyu0` quartet/340.7°/6.3°/period-1/2.8° alternate
proxy, unchanged unselected definitions and every recorded unaffected native
proxy. The selected Phenix dispatcher, modules and numerical source hashes
must match the Cedar 11 authority before and after execution. Relocation uses
the declared installation anchor, not basename search.

**Read-only review class:** every declared outgoing O3′ endpoint is audited
by element and adjacency. Cedar 12 confirms the prior Cedar 09 findings:
1AP A:5→A:6 `HO31`, 5CM A:7→A:8 `HO3'`, DZ A:12→A:13 `H2` and DP B:4→B:5
`H3`, all on O3′ with OH1 typing. These pre-existing curated reviews are not
silently fixed or hidden by the two selected candidate changes. Native charge
readback and new-H formal charge remain unqualified; `REVIEW`/exit 2 is
retained while these gates remain unresolved, despite successful interpretation.

**Delivery:** `scripts/build_cif_terminal_bundle_probe.py`, pinned
`12_Cedar_probe_build`, same `05_Cedar_narestraints_build`, output
`12_Cedar_probe_cif_terminal_bundle.py`. Use one subshell containing fetch,
pinned detached worktree, build and run joined by `&&`. Explicit archive,
installation, timeout and inspect-only overrides remain available. Preserve
the frozen everyday checkout and all old scripts/worktrees/native sessions.
The returned one-block Git ferry also worked from an unrelated working
directory. No ReadySet retry, model optimization, refinement, adoption or
production PostMR change occurred.

**Follow-up from that return:** source review and explicit preparation of the
four internal O3′-H contexts were implemented in Cedar 13 and pass installed
Cedar 14 validation above. Native formal-charge readback and the earlier added H formal
charge remain open evidence limits; repeating an unchanged inventory does not
resolve them. Geometry/refinement and human review remain separate later gates.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,437 tests, two skips and 276 subtests (92.78 s)**. The same command
with `tests/test_cif_terminal_preparation.py tests/test_cif_terminal_qualification.py
tests/test_cif_terminal_bundle_probe.py tests/test_cif_native_validation.py
tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_synthetic_dna_shuttle.py` passes **97 tests (6.84 s)**. Nine selected
regressions fail before the new implementation/readback fields exist. New
native tests use explicit fake APIs; transport survives deleted build trees
and poisoned imports. Actual returned-input offline preparation/replay and
prior-native outgoing-H audit are distinct from the completed installed
Cedar 12 execution above. This follow-up changes documentation/evidence only;
JSON, link and figure checks apply, with no runtime/schema migration or new
dependencies. Native payloads stay outside Git; qualification gates are unchanged.

Documentation follow-up verification: all 16 documentation JSON files parse,
116 local links in changed Markdown resolve, and `git diff --check` is clean.
`python docs/figures/build_cif_doctor_overview.py` reproduces the SVG;
its 1200×1190 render is byte-identical to the preceding visual QA image.

**Cedar 11 returned; terminal numerical sources complete (2026-10-15):** all
**nine** payloads in `11_Cedar_ggtpccwv_cif_terminal_review.zip` verify, including
anchored native outputs, repeated receipt content and the exact published
worker/build. The user's runner hash is `9aa0afa3…`, from clean source
`e6ec5d66e283a138c0ac8e9585146e5c994ac243` and the same pinned NARestraints.
The explicit 5CM preparation again reproduces `61bf14a1…` with source/original
09 ZIP preserved. Phenix **2.2.1-6174** resource execution completes at exit
zero in **0.837208 s**; status is `PREPARATION_AND_RESOURCES_REVIEW`.

Native resolution records DG → metadata `Gd`. The unchanged canonical base
has 33 atoms; effective `5*END` has 31: P/OP1/OP2 removed, O5′ changed from
OC2 to OH1, HO5′ added with HOH1 type and the exact installed bond/angle
targets. All unaffected bond/angle/torsion/chirality/plane rows remain equal,
with no dangling references. Both installed sources remain unchanged and
the modification rows exactly match Cedar 10. The compact registration evidence
owns all hashes, counts, exact targets and source/module provenance.

**Scientific interpretation:** both canonical states retain DNA group, but
the effective canonical 5′-OH classification is also `undetermined`. That label
alone cannot distinguish the earlier synthetic modified end from the canonical
control. It does not erase the earlier missing O5′ hydrogen/OH typing, and
no qualification gate changes. Both canonical states lack native formal-charge
readback; recorded partial charges remain distinct. Native metadata atom
counts are retained as returned, not rewritten to imply qualification.

**Next work:** implement an explicit source-traceable modified-terminal
adaptation and validate the revised bundle, including the separate prepared
5CM candidate, before a new bounded geometry trial. No further unchanged source
inventory is needed. No new delivery is queued by this evidence-only update;
no model edits, optimization, ReadySet retry, refinement or adoption ran.
Runtime/schema and dependency behavior are unchanged; the 1,406-test software
receipt below still applies, separately from this actual native return.

**Cedar 10 returned; Cedar 11 canonical lookup retry (2026-10-15):** all
**nine** payloads in `10_Cedar__7ap0ddc_cif_terminal_review.zip` verify. Its
clean NASolve source is `f681b9bd5355905fbee0797302d5984cc40e5d6a`, with the same
clean pinned NARestraints. The runner prepared the exact reviewed 5CM
derivative (`61bf14a1…`) with unchanged source/archive, then used installed
Phenix **2.2.1-6174** to capture the `5*END` fields and source hashes. The resource
worker returned UNSUPPORTED at **Missing canonical monomer: DG** after
**3.726048 s**; the aggregate probe is `NATIVE_RESOURCES_REVIEW`. No canonical
control, terminal adaptation, native 5CM qualification or refinement ran.

The v1 worker incorrectly used direct library lookup for a PDB residue name.
Primary cctbx `server.py` delegates name translation to the installed
`get_comp_comp_id_and_atom_name_interpretation` method; `iotbx.pdb` translates
explicit DG to library GD (and DA/DC/DT to AD/CD/TD). Policy
**`cif-installed-terminal-resources-v2`** now uses that native API with an empty
atom-name list, retaining no coordinate model or local alias table. Additive
schema-1 control evidence records the method, empty input atom list,
interpreted residue name and resolved component ID; provenance also hashes
`iotbx.pdb`. Missing native resolution APIs/components remain unsupported and
retain the already captured modification evidence. All numeric targets,
formal-charge boundaries and existing qualification gates are unchanged.

**Validation:** the new fixture reproduces the untranslated-name failure:
**five failures / seven passes** before the fix. Focused validation is
**55 passed (4.37 s)** using the five terminal/resource/repair/linked/shuttle
test files in the Cedar 10 command below. The full command below passes
**1,406 tests, two skips and 276 subtests (64.49 s)**. These are explicit fake
native API and transport checks, including all four canonical DNA names,
unsupported resolution, preservation and relocation. Corrected installed
canonical-control execution remains pending. The registration evidence owns
the exact returned hashes, source rows' provenance and primary-code references.

**Next delivery:** build the existing terminal probe with explicit
`--delivery-prefix 11_Cedar` and output
`11_Cedar_probe_cif_terminal_review.py`, from pinned `11_Cedar_probe_build` and
the same `05_Cedar_narestraints_build`. It still reads the exact original
Cedar 09 ZIP; no replacement ZIP or new dependency is required. The user
requests one pasteable conditional command block: fetch, add pinned detached
worktree, build, run, joined by `&&` inside a subshell. Stop after any nonzero
status. Preserve the everyday checkout, all old build trees and every native
session. Inspect the returned control before implementing terminal adaptation
or proceeding to a separate bounded geometry trial. No native outputs are
committed; this change includes source/tests/docs and compact evidence only.

**Cedar 10 terminal-source review ready (2026-10-15):** the user requested a
few executable steps and clarified whether the whole run had completed. Only
the native linkage diagnostic has completed; no complete refinement run is
claimed. The next delivery advances the two known dictionary reviews without
rerunning the same linked inventory for an unavailable charge attribute.

`scripts/build_cif_terminal_probe.py` packages
`10_Cedar_probe_cif_terminal_review.py` from pinned source and the same
`05_Cedar_narestraints_build`. It accepts the exact hash-bound returned Cedar
09 capsule, verifies all **207** payloads and snapshots only its explicitly
declared frozen 5CM source. The existing `5cm-reviewed-torsion-v1` recipe
prepares a separate candidate: source `38378c7d…`, output **`61bf14a1…`**.
No selected bundle or old native input is replaced. The actual returned 09
source reproduces the complete reviewed candidate hash in inspect-only replay;
its implemented assessment passes, with native bundle and geometry validation
still NOT_RUN for this preparation.

The new reusable `cif_terminal_resources.inspect_terminal_resources` API
reads explicit native modification IDs (default `5*END`) and applies them only
to an in-memory canonical library control (default DG). It records all native
row fields in atom/bond/angle/torsion/chirality/plane categories, numerical
values, source/module hashes, charge readback and base preservation. No target,
energy type, hydrogen name or formal charge is invented for IGU. This captures
the installed numerical authority needed to complete the terminal treatment;
it is **not** implementation or qualification of that new recipe. Native
source/control errors, unsupported APIs and owned-process timeout remain
explicit. The selected Phenix environment is isolated as in earlier probes.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,400 tests, two skips and 276 subtests (63.87 s)**. The same command
with `tests/test_cif_terminal_resources.py tests/test_cif_terminal_probe.py
tests/test_cif_doctor_repair.py tests/test_cif_linked_probe.py
tests/test_synthetic_dna_shuttle.py` passes **49 tests (3.64 s)**. New native
tests use explicit fake APIs, including exact target retention, unknown charge,
missing resource and owned timeout. The resource tests fail before the new
module exists and pass afterward. Transport tests delete original build paths,
poison imports and preserve both successful/unsupported review capsules.
Real-09 inspect-only replay verifies exact source/output hashes and preserved
original ZIP; installed resource execution remains **PENDING**. No new
dependencies, production PostMR changes or old qualification-gate changes.

**User delivery:** a pinned `10_Cedar_probe_build`, then the source-bundled
builder/run sequence. The user now explicitly permits a few sequential
commands together. Preserve the frozen everyday NASolve checkout, existing
05–09 trees/runners and every native session. Inspect the new review ZIP before
implementing the terminal recipe or entering a separate bounded geometry trial.
No model interpretation, model optimization, ReadySet retry, diffraction
refinement or adoption is part of Cedar 10. Only code/tests/docs and compact
evidence enter Git; actual source dictionaries/native outputs remain outside it.

**Cedar 09 returned; native metadata recovered (2026-10-15):** all **207**
payloads in `09_Cedar_nn9cyghr_cif_linked_review.zip` verify. Source is clean
NASolve `4f1cde11b540c24adc27c97cb5f891f6710bf17e` with the same pinned clean
NARestraints source. Phenix **2.2.1-6174** completes baseline/linked/control at
exit zero in **2.924922 / 1.354201 / 1.272176 s**. All four linked sites now
have native group and classification **DNA**. Qualification records **29 PASS,
four UNSUPPORTED**: every noncharge check passes, while the installed atom API
has no formal-charge attribute. There is no known-charge contradiction. Keep
the aggregate **REVIEW** and raw charge evidence; do not substitute partial
charges, source values or zero, weaken the gate, or repeat an unchanged native
inventory to seek an attribute absent from this installation.

The linked manager retains 858 atoms, 42 mappings, all **38** declared links,
custom **21 bonds / 34 angles / 8 planes / 23 parallelities**, all 58 native
parallelities and unaffected definitions. The 877-atom/43-residue control has
**10 PASS / two charge UNSUPPORTED**; original atoms, all 42 definitions and
38 links are unchanged. Its E:1 group is DNA but classification is
**undetermined**. The projected E:1 O5′ remains type **O2**, bonded only to C5′
with no explicit O5′ H. This proves selected atom/context isolation under one
code, not complete free-OH end parameterization or general terminal support.
Do not infer that the original four internal sites failed classification.

Read-only arithmetic replay compares **148/148** source/candidate formal charges
with no difference or unavailable source value. All **12** generated ordered
sugar-centre signs match source ideal coordinates; native proxy signs and the
initial model agree under each actual proxy order. The determinant convention
is checked against the primary cctbx chirality implementation. This is
source-coordinate/sign consistency, not independent CIP/R-S assignment or
experimental validation, and it does not satisfy the native charge gate.
Projected plane-angle reviews remain **IGU five / IMC two / CGY five / DX zero**;
their material-strain threshold is uncalibrated. The selected 5CM A:7 still
contains `C4′–O4′–C1′–C2` (`C2e-nyu0`, 340.7 ± 6.3°, period 1). Preserve that
known C2/C2′ defect until an explicit, hash-scoped preparation is reviewed;
do not silently substitute the historical repaired derivative.

The [registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns exact archive/source/API hashes, native counts and these review limits.
**Next work is dictionary chemistry/geometry review:** complete the declared
free-OH terminal treatment through a traceable numerical source, use explicit
reviewed 5CM preparation where its exact source hash permits it, and preserve
charge/protonation and generated metadata reviews before a new bounded geometry
trial. The subsequent Cedar 10 source-resource delivery is described above;
it does not repeat this linked inventory. No ReadySet retry,
minimization, refinement, adoption or gate change occurred. These updates are
documentation/evidence only; the runtime's existing 1,386-test receipt below
and its returned installed execution remain the validation. Original private
payloads and the frozen everyday checkout remain outside Git and unchanged.

**Cedar 08 returned; Cedar 09 component-list retry (2026-10-14):** all 207
payloads in `08_Cedar_g4gzbeeb_cif_linked_review.zip` verify. The runner matches
the expected SHA-256 and clean NASolve `147c1fbaabb41f73f5680852625189b0e1295ca7`,
with the same clean NARestraints `a7b6a0c93365f7a480b7eee9cc4e860b13f702de`.
Phenix **2.2.1-6174** completed baseline, linked and synthetic shared-code
interpretation at exit zero (**2.522322, 1.381361 and 1.412638 s**). Native
modifier registration now matches every requested ID. All four expected atom
sets, H adjacency and energy types agree; no dangling references remain.
All **38 links**, custom **21 bonds / 34 angles / 8 planes / 23 parallelities**,
all 58 native parallelities, unaffected definitions and the original 858 atoms
are preserved. Internal IGU A:6 and free-OH IGU E:1 have distinct selected
definitions in the 877-atom/43-residue control; the original 42 definitions
and 38 links remain unchanged. The control's added residue is synthetic.

The returned status is still **REVIEW**, with two precise limitations:
the native formal-charge attributes are absent, and the declared `_chem_comp`
DNA group was not read. Our singleton `comp_list` writer collapsed its metadata
to scalar fields; native `convert_list_block` only iterates the category loop.
Both loaded base and effective group are null. Native logs nevertheless classify
all 42 residues as DNA: group metadata and interpreted classification are
distinct, and the old worker did not record the latter per site. The old
`effective-site-atoms` check combined matching atoms with the missing group;
there is no observed atom-inventory mismatch.

The writer now retains one-row list metadata as a loop, using the existing CIF
quoting implementation. It adds `component_list_policy =
cif-native-component-list-loop-v1`; detailed native metadata records
classification separately. Qualification reports exact atoms and required DNA
group independently, preserving both gates. Exact returned-input replay keeps
every parsed base/projected dictionary, site plan, modifier and PHIL request
unchanged; only list serialization changes. The
[registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns native hashes/counts, the group blocker, source preservation and replay.
Missing formal charge is still `UNSUPPORTED`; no partial/source/zero substitute
is introduced, and a subsequent REVIEW can persist after the group is corrected.

**Next action:** deliver the clean published source through a pinned detached
`09_Cedar_probe_build`, build `09_Cedar_probe_cif_linked.py` using
`scripts/build_cif_linked_probe.py --delivery-prefix 09_Cedar` and the existing
`05_Cedar_narestraints_build`, then run it against the original checksum-bound
05 capsule. Issue one terminal command at a time. Preserve the frozen everyday
checkout, all 05–08 build trees/runners, native sessions and source models.
Installed list metadata, complete qualification, numerical/stereochemical
review and ordinary fresh full-auto recovery remain open. No ReadySet retry,
model optimization, diffraction refinement or adoption is authorized by this
diagnostic result. Generated private CIFs/coordinates/native receipts stay
outside Git; only code/tests/docs and compact evidence are committed.

**Cedar 09 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,386 tests, two skips and 276 subtests (89.41 s)**. The same command
with `tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_cif_linked_probe.py tests/test_cif_native_validation.py` passes
**70 focused tests (4.75 s)**. Four targeted cases fail before the change and
pass after it. Explicit fake native controls reproduce skipped scalar metadata
and retained loop metadata; quoting/multiline values round-trip unchanged.
Exact real-return replay checks every base/projection value and preserved
modifier/PHIL/input bytes. Classification readback is additive to detailed
inventories; basic defaults and schema-1 compatibility remain unchanged.
No new dependencies are added. The editable figure is regenerated/rendered and
visually inspected. These software/replay checks are not installed Phenix
execution of the new metadata layout; that remains the Cedar 09 action.

**Cedar 07 returned; Cedar 08 registration retry (2026-10-14):** all 164
payloads in `07_Cedar_okkb2are_cif_linked_review.zip` verify. Source-retaining
IMC/CGY/DX generation reached `CANDIDATE_REVIEW`; IGU was reused. Detailed
baseline interpretation completed at exit zero (2.896598 s), with 858 atoms,
42 mappings and 38 backbone links. Linked interpretation failed at exit two
(1.082309 s): `Missing CIF modification: data_mod_NASL9809b6bd9c`.
The four modifier files registered `linked_sites`, overwriting that key, rather
than the distinct requested IDs. The
[registration record](cif-linked-native-registration-evidence.json) owns exact
archive/build/reader hashes, failure and replay. No linked qualification or
shared-code control completed; no coordinates or frozen inputs changed.

The writer now emits one native `data_mod_<ID>` block for each requested
modifier, with identical operations and PHIL IDs. Schema-1 preparation adds
`modification_block_policy = cif-native-modification-blocks-v1`. Replaying all
four actual returned candidates preserves each site plan, base dictionary and
PHIL file byte-for-byte while registering four distinct IDs. Reader-contract
tests reproduce the old missing-ID failure and cover multiple same-code end
contexts and cross-component collisions. These tests use explicit fake APIs;
they are not installed Phenix evidence.

The baseline native atom records also have no formal-charge values. New
detailed worker metadata distinguishes missing attributes from null readback;
site qualification records unavailable values as `UNSUPPORTED` separately from
actual charge contradictions (`REVIEW`). Never substitute partial charges or
zero. Source charge preservation remains separate evidence. Other mechanics
checks continue, but missing native charge readback cannot silently qualify.
The native console now prints the failed layer and its recorded error.

**Next:** Git-build and run
`08_Cedar_probe_cif_linked.py` with `--delivery-prefix 08_Cedar`, using the same
pinned NARestraints source. Keep the everyday laptop checkout, Cedar 07 runner,
all native sessions and original model/source inputs intact. The runner remains
an external diagnostic with no ReadySet retry, refinement or adoption. Native
registration, full linked mechanics, the shared-code control, numerical and
generated stereochemical review, and fresh full-auto recovery remain open.
Only code/tests/docs and compact hash/count evidence enter Git.

**Cedar 08 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,380 tests, two skips and 276 subtests (98.88 s)**. Focused
preparation/qualification/shuttle/native-worker checks pass **64 tests (5.38 s)**.
Two registry regressions fail with the old shared block and pass with distinct
blocks. The fake-reader boundary also reproduces the missing-ID failure with
legacy packaging and accepts the exact requested IDs with corrected packaging.
Native charge controls distinguish missing/nonfinite readback from actual
contradictions and retain the partial/formal-charge separation. Exact real
candidate replay checks unchanged base/PHIL/site plans and input preservation.
Existing shuttle relocation tests retire original build paths and poison imports.
The editable figure was regenerated, rendered and visually inspected. New
schema-1 fields are preparation layout provenance and detailed native charge
readback metadata; formal-charge check rows retain explicit unavailable and
contradictory observations. No new dependencies or installed native execution
were added to this validation. Generated coordinates/CIFs/native payloads stay
outside Git. The subsequent installed Cedar 08 result is recorded above.

**Cedar 06 returned; Cedar 07 representation retry (2026-10-14):** all 87
payloads in `06_Cedar_rkmjesl4_cif_linked_review.zip` verify. Native eLBOW
completed source-retaining IMC/CGY/DX generation on Phenix 2.2.1-6174
(RM1/GDIIS); IMC and DX reached `CANDIDATE_REVIEW`. CGY alone was rejected for
six alternating single/double ring orders becoming aromatic types. Every source
ring bond already declares aromaticity; connectivity, hydrogen attachments and
explicit formal charges survived. No new native bundle interpretation ran.
The [source-recovery record](cif-linked-source-recovery-evidence.json) owns
exact archive/source/candidate hashes, commands and offline replay.

Generation-v4 now recognizes only complete isolated source-declared aromatic
six-member alternating neutral C/N rings, with unchanged single bridges and
non-stereogenic ring bonds. Schema-1 inspection adds `bond_representation`;
raw comparison differences, numerical reviews and independent atom/H/charge/
stereo checks remain intact. Native diagnostics retain v3 receipt compatibility
and re-inspect supported v3/v4 candidates. Source-recovery console output names
blocked components and reasons. Offline reanalysis prepares all four returned
candidates with their OP2 H retained and the original model hash unchanged.

**Delivery history:** `07_Cedar_probe_cif_linked.py` was built from the checked Cedar revision with
`scripts/build_cif_linked_probe.py --delivery-prefix 07_Cedar`, using the pinned
NARestraints build source. Use delivery build worktrees and write the runner
into the everyday NASolve directory: macOS refused Python access to Downloads
before the Cedar 06 script could run. Preserve the frozen everyday checkout,
old deliveries and native sessions. These worktrees isolate pinned delivery
sources on the single Cedar development line; audit and retire them after the
linked qualification gate closes. Publish code, test/contract changes and
compact hash/count evidence only; unpublished coordinates, dictionaries and
native payload bytes stay outside Git. Installed Cedar 07 qualification,
numerical/achieved geometry review and full-auto recovery remain pending.

**Cedar 07 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,370 tests, two skips and 276 subtests (97.41 s)**. The initial
generator/native/preparation/qualification/shuttle focus passed **192 tests
(38.98 s)**; the final aromatic/orchestration focus passed **36 tests (1.84 s)**.
The two source-declared-ring acceptance regressions fail before the change and
pass after it. Negative controls retain rejection for partial/missing/conflicting
declarations, fused or charged rings, exocyclic and outside-ring changes,
altered H/formal charges/elements and invalid numerical targets. Existing
relocation tests delete original build checkouts and poison normal imports.
The same returned four candidates prepare offline, retaining source-specific
OP2 H. No new Phenix/Coot process ran in this validation environment.
Changed runtime files are `src/nasolve/cif_generation.py` and the linked/native
probe templates; source-bundled transport needs no new dependency. Inspection
schema 1 gains additive representation evidence, generation policy advances to
v4, and the native probe keeps completed v3 receipts readable. Generated
coordinate/CIF/native payloads remain excluded from Git. Descriptors,
machine-readable evidence and the editable figure/caption are updated together.

**Cedar 05 returned; Cedar 06 prepared (2026-10-14):** all 57 payloads in
`05_Cedar_dy4qx3qg_cif_native_review.zip` verify. Native interpretation completed
at exit 0 with 42 mappings, 38 intra-strand O3′–P links and zero coordinate
OP3/O3P. REVIEW is the worker's deliberate successful inventory status. Four
generic monomers still expect isolated OP3. The fresh trial has free 5′-OH
ends A:1/B:1/C:8/D:1; the older W trial's D:1 phosphate consent does not apply.

Source/effective audit also finds lost OP2 H in the CGY/IMC/DX ReadySet
definitions; only IGU's accepted candidate preserves its complete source state.
`06_Cedar_probe_cif_linked.py` therefore reuses existing source-preserving eLBOW
generation for rejected components before per-site preparation. It keeps all
raw inputs, numerical findings, model coordinates and NARestraints parameters.
Opt-in detailed native inventory checks actual monomers, all declared links,
exact custom target/weight coverage and pair/stacking parallelities, plus a
shared-code internal/free-OH IGU control. No runtime is installed on the
laptop, no frozen run is rewritten, and no ReadySet/refinement/adoption starts.

The Cedar 06 native generation return and next retry are recorded above.
Review the next prefixed capsule before considering integration or full-auto retry.
Source-state regeneration, linked mechanics and numerical/achieved geometry
remain separate verdicts. Known 5CM/DP reviews remain visible. Public source,
tests and contract updates belong on Cedar; unpublished input bytes remain
outside Git. Baseline Cedar's complete Linux suite passed 1,308 tests, two
skips and 276 subtests. Final new-suite validation is recorded below after
completion; offline/fake native tests are not installed Phenix evidence.

**Cedar 06 implementation's offline validation:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q`
passed **1,345 tests, two skips and 276 subtests (96.43 s)**. The focused
native/preparation/qualification/shuttle files passed **75 tests (25.07 s)**.
The assembled runner replayed the exact 05 ZIP offline, identifying IGU reuse
and CGY/IMC/DX source-state regeneration requirements. Actual IGU projection
removes OP3/HOP3/HO3′ and retains HOP2. Relocation tests delete both source
checkouts and poison normal imports; input corruption remains a preserved
failure capsule. The editable SVG was regenerated, rendered and inspected.
Regression controls reject changed targets/weights, duplicate planes, lost
links/H, incorrect types/charges, missing mappings and undeclared same-code
end states. The new native worker/detail interface is tested using explicit
fake installed APIs. No new Phenix/Coot execution occurred in this environment.

**Cedar 04 reproduction and Cedar 05 diagnostic (2026-10-12):** the returned
`04_Cedar_r2cunjcc_cif_generation_review.zip` verifies all 22 manifest entries.
The [compact repeat evidence](elbow-source-retention-evidence.json) records
exact parsed CIF/PDB atom-row equality to v3; only generation timestamps differ.
Native eLBOW completed in **22.019048 s**, with source retention and numerical
findings unchanged. The prefix is present in console, receipt, output directory
and review ZIP. This is reproduction and delivery evidence, not native-reader
or linkage qualification.

The new `05_Cedar_probe_cif_native.py` freezes an external diagnostic bundle
from the source-audit runtime stack and prepared model, with the accepted
candidate substituted only in the copied dictionary input list. The prior
generation probe hash-binds the source audit/raw ReadySet baseline and the exact
candidate receipt; explicit caller paths remain operational references.
Parameterized source precedence, torsion normalization and every recorded
ancillary PHIL/EFF/site-modification input are retained. The installation-bound
`phenix.python` worker inventories native readers, effective monomer/missing-atom
mapping and interpreted atom/proxy evidence. Its explicit native-parser PHIL
namespace adapter retains all definitions and rejects unused parameters.
The subsequently returned native inventory is recorded above. Success is REVIEW, with no
model replacement, optimization, ReadySet retry, adoption or certification.
The human descriptor and editable figure/caption reflect this diagnostic scope.
Final offline validation: **16 native-boundary tests pass (1.62 s)** using
explicitly fake installed APIs, **22 shuttle tests pass (9.48 s)** with deleted
source checkouts and poisoned imports, and **19 discovery/CLI tests pass
(0.48 s)**. The established full-suite command passes **1,308 tests, 2 skipped,
276 subtests (54.09 s)** after final mapping/provenance changes. Fake APIs verify
process, hash and reporting boundaries; they are not native Phenix evidence.
The figure was regenerated and rendered for visual QA. New schemas are
schema-1 native inspection/probe receipts and selected-bundle evidence; the
generation policy remains v3. Private crystallographic inputs stay outside Git.

**Native v3 source-state retention and visible ferry IDs (2026-10-12):** the
user returned the 22-file [source-retention capsule](elbow-source-retention-evidence.json).
Installed Phenix 2.2.1-6174 completed RM1/GDIIS generation with `--pH=low` in
**19.958581 seconds**. All 37 atoms, 39 normalized bonds, 14 hydrogen
attachments and zero formal charges are retained, including HOP2/HOP3.
**C2–N3 = 1.397 ± 0.030 Å**. The three sugar centers retain source coordinate
handedness under identical atom order. Five finite PSD plane reviews remain
visible. Candidate status is **CANDIDATE_REVIEW**, not adoption or chemistry
approval: source CIP/aromatic metadata is absent, generated signed chirality is
not equivalent metadata, and the dictionary group remains non-polymer rather
than DNA LINKING. The actual native log names RM1 even though the CIF header
says AM1; preserve both as provenance.

The immediately preceding return was a repeat of v2, with no `--pH=low`; it was
not a failed retention attempt. New ferries use a leading identifier such as
`04_Cedar_probe_cif_generation.py`; sessions and ZIPs carry the same identifier,
and ZIPs add their unique run token near the front. Console and additive schema-1
receipt fields identify the delivery/policy explicitly. The collaboration
contract records the user's preference for visible prefixes and one exact
terminal command. Older runs and explicit output paths remain intact.

Next: qualify an external candidate derivative against the original prepared
model and complete effective bundle, including source-derived DNA metadata,
site-specific internal leaving atoms, true ends/nicks, native parser/proxy
coverage and generic IGU/IMC/CGY/DX linkage. Current production linked profiles
cover only 1AP/DZ/DP/5CM. No old candidate/model is substituted into the fresh
campaign, no checkpoint is selected, and full-auto recovery remains pending
these native checks. Geometry/sticky-end stitching is a separate planned layer.
Validation of the naming/receipt change: **26 focused tests pass (6.36 s)**,
including relocation after deletion of the source checkout, preserved prior
runs, leading ZIP/run identifiers and invalid-prefix refusal. The established
full-suite command passes **1,269 tests, 2 skipped, 276 subtests (42.49 s)**.
The numerical generator policy remains v3; only delivery metadata/names and
console identification changed. Private source/candidate/model payloads stay
outside Git. No native Phenix/Coot invocation ran in this Linux validation.

**Optimized candidate and source-state retention (2026-10-12):** the returned
22-file capsule is checksum-verified in
[the native evidence record](elbow-optimized-state-evidence.json). Installed
Phenix 2.2.1-6174 selected underscored initial-geometry/hydrogen aliases and
completed optimization in **24.107482 seconds**, using **RM1/GDIIS**. IGU's
collapsed C2–N3 target became **1.387 ± 0.029 Å** with distinct coordinates.
The candidate still fails source-state preservation: HOP2/HOP3 were removed,
OP2/OP3 formal charges changed from 0 to −1 and phosphate orders became DELOC.
Four plane-angle reviews have positive-semidefinite Gram matrices and small
0.06–0.13° sum residuals; numerical REVIEW must not be labeled incomplete.

Generation-v3 requires the installed valued `--pH` option and selects `low`
as the generator's exact-input-chemistry mode. It explicitly leaves experimental
pH and intended crystal protonation unassessed. The candidate gate preserves
supported soft numerical reviews, while rejecting invalid/incomplete numerics,
unresolved plane compatibility and chemical-state changes. No source or old
run is overwritten, no individual target is guessed and no candidate is
adopted. The next laptop probe demonstrated source-state retention as recorded
above; native reader/polymer-link qualification and full-auto recovery remain pending.
The requested optimization option and the observed native backend are separate
evidence. Human/manuscript descriptors and the figure caption are current.
Final isolated Linux validation with the established full-suite command passes
**1,264 tests, 2 skipped, 276 subtests (43.26 s)**. Regressions cover exact valued
source-state control negotiation, refusal of missing controls or ignored
hydrogen preservation, complete soft reviews, impossible/missing/nonfinite
plane evidence, missing numerical coverage and collapsed coordinates. Native
source-preserving generation was pending at that validation; no native tool ran
in the Linux check. The subsequently returned native result is recorded above.

**Native generator CLI compatibility (2026-10-11):** the returned 18-file
[capsule](elbow-cli-compatibility-evidence.json) confirms installed Phenix
2.2.1-6174 rejected `--initial-geometry` before reading chemistry (exit 2,
2.071012 seconds). No new candidate was generated; original/frozen source
hashes survived. The wrapper had used a spelling from the documented option
table; the example uses a different alias. Generation-v2 now probes the exact
installed executable's help, negotiates advertised spellings/value semantics,
and refuses missing controls before chemistry. Help and executable hashes are
retained. Probe summaries now distinguish failed/rejected generation from
actual candidates awaiting review. The corrected native retry completed as
recorded above; this first CLI failure supplies no numerical-quality or
chemical-state verdict.
Final isolated Linux validation with the established full-suite command passes
**1,246 tests, 2 skipped, 276 subtests (42.81 s)**. New regressions cover dashed,
underscored and mixed flags, misleading help examples/prefixes, valued versus
switch controls, unsupported controls, help timeout/error and executable races.
The original failed receipt and run stay intact. Generation receipt schema 1 adds installed capability
evidence under policy `cif-independent-elbow-candidate-v2`.

**Fresh ReadySet defect generalized (2026-10-11):** the user returned a
checksum-verified 16-file capsule from the new combined DNA run. Preflight and
Phaser passed: **TFZ 13.10 / LLG 196, H 3**. PostMR correctly blocked IGU,
whose generated C2–N3 target is **0.000 ± 0.020 Å** and whose dictionary C2/N3
coordinates coincide. Other local targets are distorted; source HOP2/HOP3
were omitted and OP2/OP3 formal charges changed. This is actual numerical
generation, not a raw-graph copy. The
[evidence record](igu-readyset-generation-evidence.json) and
[synthetic descriptor](synthetic-dna-mechanics-test.md) preserve exact hashes.

The generalized assessor checks dictionary coordinate degeneracy and PostMR
records a component quarantine with exact atom/target diagnostics. The new
explicit `cif-doctor generate-candidate` API/CLI regenerates a whole component
from frozen chemical input plus complete supplier ideal-coordinate seeds; it
does not patch one bond or borrow MR coordinates/older prepared candidates.
A one-file probe selects invalid generic components and collects native
generation/comparison evidence into a review ZIP without altering the old run.
Native source-state preservation, candidate quality and generic polymer-link
qualification remain pending. Automatic adoption and a full-auto retry are
not claimed complete. Update the human overview/figure with each extension.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,222 tests, 2 skipped, 276 subtests (43.87 s)**. Nine probe delivery
regressions use invented XRAWR/Q99/Y components, deleted original source
checkouts and poisoned imports; all runtime/source/review-ZIP hashes validate.
The source-bundled inspect-only probe also selects IGU from the real returned
capsule with its original source hashes verified. Native eLBOW optimization and
candidate acceptance were NOT_RUN here. The updated editable figure was
regenerated and rendered for visual QA. Changed runtime files are the assessor,
general candidate module, CLI/optional Phenix discovery and PostMR quarantine;
receipt schema 1 gains explicit dictionary geometry and generation evidence.
Private dictionaries and native outputs remain outside Git.

**Fresh combined DNA mechanics inputs (2026-10-11):** user authorized a new
synthetic K:X/B:S/Z:P/D:T test on copied donor diffraction with AutoSol off.
The [human descriptor and recipe](synthetic-dna-mechanics-test.md) own the exact
42 targets, real free-5′OH preparation, isolated one-file shuttle and limits.
This is an ordinary fresh source-acquisition/ReadySet test; no prior numerical
bundle or relaxed coordinates are substituted. Input preparation and campaign
policy are offline-tested; native laptop execution remains pending. The frozen
Cedar checkout is preserved and no pull is required to use the shuttle.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,124 tests, 2 skipped, 276 subtests (38.50 s)**. The nine shuttle
regressions include deleted source checkouts, poisoned laptop imports and exact
module-origin receipts. A separate stage-only check using the real local QiC
donor also produced a valid frozen DISCOVERED plan; no native programs ran.
Only code, the recipe and documentation enter Git. Generated donor copies,
receipts and standalone deliveries stay outside the repository.
The user has also returned a successful laptop execution of the public CCD
shuttle: all 18 source PASS / effective REVIEW / numerical UNASSESSED. That
result confirms the offline audit path, not native dictionary generation.

**Human overview, public ZIP runner and upstream data review (2026-10-11):**
The [human/manuscript descriptor](cif-doctor-human-overview.md) now explains
the implemented algorithm, tools, placement and limits, with an adaptable
methods paragraph and [editable SVG/layout source](figures/README.md).
`AGENTS.md` and the collaboration contract require descriptors and figures to
stay current when features change. No geometry/stitching capability is added.

The single-file `run_cif_doctor_ccd_controls.py` embeds the unchanged assessor
and required reader/normalizer code. SHA-256:
`e1d54f1dab5c5dde733aa65fcf9dd66a82b720b7ee753a9c589cf9946912680e`.
The exact previously delivered public ZIP runs offline with **18 source PASS,
18 effective REVIEW, 36 receipts**, every input unchanged and native tools
NOT_RUN. Graph-only numerical UNASSESSED is expected in source mode; effective
screening does not generate numerical dictionaries or run ReadySet.
The established laptop Python can run this artifact without installing or
pulling NASolve; it creates a fresh output folder beside the ZIP. The frozen
laptop source state remains separate from the published Cedar feature.

Validation with the same isolated environment: **12 shuttle tests pass**,
including exact receipt parity, unsafe/tampered ZIPs, exclusive output and
relocation with the original checkout removed. The complete NASolve command
below now passes **1,090 tests, 2 skipped, 276 subtests (36.37 s)** with the
corrected upstream workbook. Overlay tests explicitly cover both legacy DF
S2 mappings and corrected S1 mappings; the compatibility adapter is retained.

The separately reviewed NARestraints source workbook corrects 5BU/BRU sugar
metadata and abbreviations, DF/S6G mappings and all 129 literal C5 trailing
spaces. Its **138 exact cell changes** are documented in its Markdown/JSON
audit. Workbook SHA-256 after the patch:
`afed0f332c3d70cd14c395005fcbccf38201e2818bb9b765c86decda309707f5`.
All other cell values/types/styles, sheet order/dimensions, and unrelated
uncompressed XLSX parts are preserved. NARestraints passes **42 tests**;
the seven new regressions failed before their corresponding corrections.
This remains unreleased source data; the pinned v1.1.3/laptop installation
has not been updated. PSU's coupled attachment/base-plane issue stays open.
Native interpretation/refinement was not run for these metadata corrections.

Changed files are the overview/figure source and maintenance/index documents,
the shuttle builder/template and tests, and the legacy/corrected overlay test.
Shuttle schema 1 adds artifact-build provenance and output-anchored references;
existing NASolve runtime/checkpoint schemas and frozen runs are unchanged.
The manuscript PDF export, standalone runner and generated audits remain
outside Git; neither private coordinate/reflection data nor the public CCD
payloads are added. The existing native/proxy/geometry follow-up remains open.

**CIF Doctor implementation validation (2026-10-11, isolated Linux):**
Published implementation: Cedar **`8c181c5d47cd987318c48568f13d93ef6bdfbb87`**,
tree-equivalent to local **`105f2bb`** at tested tree
`fbaaab578c4737b35cbfd1fa145f1e153f1b86e0`. Subsequent handoff bookkeeping
does not change that tested runtime. The frozen laptop checkout remains untouched.

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,077 tests, 2 skipped, 276 subtests (35.06 s)**. The five new Doctor
test files pass **88 tests and 7 subtests (1.05 s)** with the same environment.
Independent review is clear; source and run-adapter regressions exercise
relocation with the original paths removed, immutable selection and input-race
rejection. No native Phenix/Coot execution occurred for this implementation.

The final assessor source SHA-256 is
`7eb53fb2b8c1782fae9f3785a9ae2295baa664982237c01b5a5edf86ec496798`.
Fifty-six source/effective assessments cover **18 public CCDs plus 10 packaged
dictionaries** with every input byte preserved. All public CCDs pass graph
inventory with numerical parameterization unassessed; all need review when
presented as effective numerical dictionaries. The six exact historical
5CM/DF/DP replays preserve their hashes. The standalone comparison additionally
exposes the DF source/generated bond-order, aromatic, hydrogen, charge and
numerical-field differences without declaring which chemistry is correct.
The reviewed historical 5CM preparation reproduces `61bf14a…` exactly.

Changed runtime files are `cif_doctor.py`, `cif_doctor_repair.py`,
`cif_doctor_run.py`, `cli.py` and `postmr.py`; new schema-1 assessment,
comparison and preparation receipts are documented in the runtime guide.
Existing runs and legacy profile scopes need no migration. Public control
provenance is committed; downloaded CCDs and generated audit receipts remain
outside Git. A frozen public-only control capsule preserves 18 CCDs and
36 receipts (SHA-256 `085f4077828d1b5ee6503dfd73dbb9c89a87c7b3fff3779520809e77e67b042b`),
without private models, maps, reflections or diagnostic CIFs. Runtime native
proxy verification and dictionary/coordinate adoption remain open.

**GeoTest orchestration trial wrapped:** the corrected native rerun verifies
six numerically ready refinements, two bounded Doctor reviews and one MR failure.
All nine workers and 14 native refinements completed, the one-file parser fix
was installed with its original backup, and model/data space groups are recorded.
The three candidates blocked by the previous parser now progress past MR.
The user explicitly closes this campaign at its orchestration scope without
further scientific repair; preserve its provisional checkpoints and reviews.
The [guided arm-connection module](construct-registration.md#geotest-guided-arm-connection)
is now bundled into the planned Doctor workflow alongside data/Free-R diagnostics
and the generalized restraint assessor, using Scout/Topo primitives.

1. **CIF Doctor's first implementation slice is complete in this change.**
   User decision **2026-10-11**: build from the saved blueprint, screen source
   dictionaries before PostMR mutations and assess effective files after ReadySet.
   [The runtime guide](cif-doctor.md) owns the new commands and exact scope.
   Assessments are deterministic and read-only, with report-only pipeline hooks.
   Explicit preparation wraps existing supported torsion normalization and the
   exact reviewed historical 5CM correction; it does not adopt a new dictionary.
   The [machine-readable implementation map](cif-restraint-doctor-implementation.json)
   preserves the scientific cases, checks, ReadySet/PostMR placement, repair
   boundaries, cache keys and regression plan. Its runtime-progress section
   distinguishes this initial implementation from future recovery;
   collaboration/personality notes remain outside the repository.
   The 5CM/DF/DP evidence is sufficient to implement the first assessment slice;
   it does not yet establish general automatic repair. This proposed restraint
   doctor is distinct from the existing refinement-strategy `refine-doctor`.
   Public CCD access is verified. Eighteen public source graphs selected
   from NARestraints cover halogens, C-glycosides, L-DNA, missing O3′ and
   diphosphates. The workbook is pairing/target-selection evidence rather than
   a universal chemical authority. Recover and freeze the exact historical
   **8RO/DE and failed 1AP** inputs as additional challenge cases; synthetic
   connectivity regressions must remain labelled as reproductions. Apply the same rules before adding any new
   component-specific exception; include valid controls and retain unsupported
   findings. The [fixture plan](cif-restraint-audit-methods.md#learning-cases-and-future-regression-fixtures)
   distinguishes known defects, source adaptations and unresolved chemistry.
   **Doctor bundle decision, 2026-10-11:** retain the existing refinement/Free-R
   diagnostic module and add the restraint assessor plus model geometry and
   connectivity assessment under one coordinated workflow. The user attributes
   GeoTest's high Rwork to arms fractured at sticky ends; record that diagnosis
   as the motivation for examining the actual model/maps and intended assembly,
   not as a causal proof from Rwork. Check geometry/connectivity before choosing
   further refinement strategies, including numerically ready models. Guided
   stitching requires declared arm pairing, strand routing and symmetry mates;
   preserve true nicks/5′-OH termini and frozen Free-R, create a bounded child
   checkpoint and validate/refine it. The assessor remains the first slice;
   geometry integration is future work, not an additional Cedar/Pine merge gate.
2. **Bound the remaining combined-model numerical review.**
   The [native ledger](native-modified-pair-live-validation.md#dp-geometry-trial--n5-conflict-relieved-review-pending)
   records verified N5 relief and preserved chirality, links and pair coverage;
   modest residual strain remains. The user reports **base visual PASS** for
   the exact new model, with sugars explicitly unassessed by eye. Review the
   remaining sugar torsions and minimizer termination numerically before a
   full-qualification or scientific continuation decision; do not request another sugar
   verdict by eye or infer a dictionary defect from residual strain alone.
   These are bespoke component diagnostics. Park further multi-modified-model
   edits/refinement unless a specific unresolved finding needs fresh evidence.
   The user's optional multi-letter-edit continuation is not a prerequisite
   for starting the assessor, and is not being declared complete. Reuse the
   returned receipts; do not chase zero residual strain or repeat passed trials.
3. **Turn demonstrated preparation into ordinary fresh full-auto behavior.**
   The current trial used selected numerical CIFs in a frozen resource bundle
   and ad hoc linked derivatives. Acceptance is a new run from declared
   model/sequence intent and component codes, without per-run source patches
   or a hand-prepared bundle. Cover already-present modified residues as well
   as mutations; distinguish library acquisition/cache, numerical preparation,
   verified polymer context and a small justified override registry. This is
   the product goal, not an achieved result or an unlimited new Cedar gate.
4. **Close the existing bounded Cedar/Pine gates.** Retain the prior P1/P3/P4
   receipts and fill only missing effective-dictionary, normal-GZ11 and
   user-veto/current-pointer evidence. Source-native P2 and real P5 remain
   separate. Then integrated tests/review P6, Cedar→Pine and Pine→main P7
   with ancestry verification and audited retirement. Do not rerun passed
   cohorts just to refresh documentation.

The [component contract](modified-component-preparation.md) owns source
chemistry and overrides; the [native ledger](native-modified-pair-live-validation.md)
owns exact sites, hashes and returned stage results. **1W5→DZ and 1WA→DP
remain mandatory reviewed transformations; A1AAZ→DF is a label bridge.**
DE geometry remains unresolved. Q is implemented; DQ/S/DS aliases are not.
Lab S/DS means N-linked IMC, not S6G or C-linked hachimoji S. Ordinary
supplier copies must not become permanent exceptions merely because used.

## Optional GeoTest side trial

Requested **2026-10-11** as a separate exploratory run; the restraint-doctor
priority above remains active. The standalone `run_geotest_campaign.py` reads
`examples/GeoTest`, preserves outer design names, and schedules each coordinate
CIF/PDB model against each coherent nested processing set. It declares trust in
supplied coordinates without inventing sequence evidence or requesting sequence
mutations. One whole-model copy and 1.0 Å MR RMSD remain the search hypothesis;
no winning model/processing combination is selected.

**First native ferry verified:** all 192 included files match their recorded
hashes and sizes; 39 large/reflection files were deliberately omitted. The
user's **8/9 good** describes eight placed models, not eight MR gate passes.
The receipts show four `MR_SUCCESS`, two `MR_REVIEW` and three `MR_FAILED`.
These are the original recorded gates; the later selected-model score audit
below identifies why they undercounted good MR candidates:

| Member | TFZ | Verified stopping point |
| --- | ---: | --- |
| X11_12 | — | No MR solution |
| X11_16 | 7.0 | MR REVIEW |
| X11_17 | 8.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_18 / dataset1 | 6.0 | MR FAILED, placed model retained |
| X11_18 / dataset2 | 7.2 | MR REVIEW |
| X11_19 | 9.2 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_20 | 15.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_22 | 14.9 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_25 | 6.8 | MR FAILED, placed model retained |

The placed-model space groups are **P2₁, P4₃ and P1**; the earlier user shorthand
P2₁2₁2 is not the P2₁ recorded in these files. This ferry used Phenix
**2.2.1-6174**, Coot **1.3.3**, Python **3.12.14** and clean Cedar
`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`. No completed refinement or Doctor
result is established by it.

**Real input preparation, not a repaired status:** the user explicitly clarified
that the strands are linear, with **free 5′ hydroxyls and no terminal phosphates**.
The updated runner copies the originals, validates CIF-to-PDB preservation, then
removes only complete P/OP1/OP2/OP3 groups at the seven declared chain starts.
All nine supplied member models lose exactly **28 atoms each**; O5′ and every
retained atom record remain unchanged. The prepared inputs pass the native
phosphate audit. Ambiguous/incomplete terminal groups block that member; internal
phosphates are not stripped. Preparation records exact deletions, hashes and
before/after audits. No fake sequence, phosphate allowlist or coordinate repair
is used. This corrected search model is the input to a **fresh** native preflight
and Phaser run; the original cohort and its failed receipts remain intact.

**One-launch full auto:** default endpoint is `refine-doctor`, using existing
native stage APIs and bounded policy. Eligible borderline MR continues with its
review warning; failed MR and chemistry/integrity failures remain blocked.
PostMR is followed by AutoSol when anomalous data warrant it, five-cycle
AutoRefine, and Doctor only for eligible `AUTOREFINE_REVIEW` (at most five trials
of three cycles). Unaccepted AutoSol phases are excluded. Verified successful
Doctor recommendations may be selected provisionally, without user approval or
overwriting checkpoint history; ordinary ready refinements need no Doctor trial.
Each member keeps its observations/Free-R and failures do not stop other members.

Every launch creates a fresh `geotest-fullauto-*` directory under the selected
output parent, with a frozen `geotest_recipe.json`, schema-2 adapter receipt,
per-member provenance, summary, compact `GeoTest_review.zip`, and
`View_results.command`. The final menu and double-click launcher open the exact
verified refined checkpoints/models/maps in Coot. Full observations/results stay
local. The single downloadable script is the adapter deliverable; these repo
changes document it and do not patch NASolve runtime or scientific inputs.

Offline validation: **76 tests, 20 subtests passed**, including all nine real
inputs, exact terminal deletions, original preservation, preparation before the
worker, full-auto handoffs, member failure isolation and exact Coot checkpoint
selection. The assembled script loads all embedded modules. An actual X11_20
model also passes real NASolve preflight and PostMR code without sequences,
using explicitly stubbed external MTZ/Phaser/ReadySet programs and fixture
reflections; this is not native execution. The unchanged core suite passes
**981 tests, 2 skipped, 257 subtests (29.58 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The revised native run has now returned as described below.
This is **not native NASolveCampaign CIF/no-sequence support**. Integrating
declared terminal chemistry and preparation into a native single recipe/button
remains the product follow-up; this side trial does not close the formal blind
baseline, production input-adapter or geometry-qualification gates.

**Returned full-auto native run, 2026-10-11:** `GeoTest_review(1).zip`
(SHA-256 `7fdaeee177c3e3eed63d49fb280bb4314ad05a88f94c3564f78b244291e4b458`)
contains **361 verified files**, with **98 deliberately omitted** large or
reflection files. All originals remain unchanged. The laptop again used clean
Cedar `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, Python **3.12.14**,
Phenix **2.2.1-6174** and Coot **1.3.3**. This was a real native execution,
not the earlier stubbed integration check. The user reports success for the
trial's scope, with arm/triangle connectivity requiring further guided work.

| Member | Recorded TFZ: first → 5′-OH run | Selected-model final TFZ-equivalent: first → 5′-OH run | Returned full-auto result |
| --- | ---: | ---: | --- |
| X11_12 | — → 2.9 | no selected model | MR FAILED; no solution |
| X11_16 | 7.0 → 7.4 | 14.0 → 14.5 | AUTOREFINE READY, Rwork/Rfree 0.2940/0.3404 |
| X11_17 | 8.0 → 5.1 | 12.3 → 12.2 | Recorded MR FAILED; refinement not attempted |
| X11_18 / dataset1 | 6.0 → 7.8 | 7.8 → 7.7 | REFINE DOCTOR REVIEW, inspection 0.4691/0.4859 |
| X11_18 / dataset2 | 7.2 → 6.2 | 8.0 → 8.0 | Recorded MR FAILED; refinement not attempted |
| X11_19 | 9.2 → 9.9 | 13.3 → 13.8 | AUTOREFINE READY, 0.2421/0.2890 |
| X11_20 | 15.0 → 15.2 | 17.0 → 16.9 | AUTOREFINE READY, 0.2262/0.2336 |
| X11_22 | 14.9 → 15.2 | 15.2 → 15.3 | AUTOREFINE READY, 0.2647/0.2770 |
| X11_25 | 6.8 → 6.1 | 9.6 → 9.8 | Recorded MR FAILED; refinement not attempted |

All eight native refinement processes exited zero (five ordinary refinements
plus three eligible Doctor trials). Four ready results are `refine-001`.
X11_18/dataset1 remains REVIEW: inspection checkpoint `refine-002`, current
checkpoint `postmr`, no recommendation or provisional selection. Numerical
readiness does not certify intended triangle connectivity. Native reports still
leave bond/angle RMSD summary fields null despite geometry values in the raw
Phenix output; do not infer a clean geometry verdict from those missing fields.
The compact ferry omits MTZs, so reflection/Free-R preservation is supported by
native receipts/audits rather than an independent replay of omitted arrays.

**Apparent MR loss is a score-association defect:** all nine original model,
reflection and metadata hashes, all 46 NASolve source hashes and normalized
Phaser settings match between runs. Search models differ only by the declared
28 terminal-atom removals; every retained atom record is unchanged. The parser
previously took the first TFZ/LLG from each solution-history line. Phaser writes
later `TFZ==` values after orientation refinement; these must be associated with
the selected output model, not maximized across unrelated solutions. See the
[Phenix annotation reference](https://www.phenix-online.org/documentation/reference/phaser.html#annotation).
For X11_17 the selected output records `TFZ=5.1` followed by `TFZ==10.8` and
`TFZ==12.2`; its final LLG is 353, rather than the initially parsed 304.
Both cohorts therefore contain **seven selected models meeting the ≥8 gate,
one borderline model and one no-solution case** when audited by final associated
scores. This is a retrospective evidence assessment, not a rewrite of old
statuses or a claim that the three newly eligible candidates were refined.

**Parser fix validation:** selected-output annotations, final score/LLG
association, matching PDB/MTZ stems, ambiguous/invalid headers and legacy
single-output fallback pass **17 focused tests and 12 subtests**. The complete
suite passes **989 tests, 2 skipped, 269 subtests (32.75 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The worker/preflight/full-auto-driver checks also pass **54 tests**. Read-only
parsing of all 16 actual selected PDBs reproduces the table above. The report
adds versioned `score_evidence` and selected-output checksums; existing fields
and TFZ thresholds remain compatible. This initial validation did not rerun
native Phaser or change any old receipt. The subsequent fresh laptop run below
installed the small fix at the recorded diagnostic head; do not pull a different
head over that distinct local state merely to replay these results.

**Authorized laptop rerun shuttle:** the user requests a fresh run with the
corrected parser and space groups in final output. The updated standalone
script accepts `--install-parser-fix`. It verifies the exact 46-source laptop
manifest (including the laptop's distinct `curated_ligands.py`), compiles and
checksums the embedded replacement, backs up original `phaser.py` in the fresh
workspace, preserves permissions and atomically installs only the known parser
update before loading it. Old parser SHA-256 is
`d277a10e4a6c7b843c3e5cd1af4b09dd835872054b7b3cd887f9215177788331`;
replacement SHA-256 is
`18aedbb3b414d2dd86e8c284219ca078e682e08003a8f82637f2b462d23a3570`.
Unknown local edits or compatibility drift stop the update; an exact installed
replacement is an idempotent no-op. This explicitly authorized one-file update
leaves Git dirty at the existing laptop head. Do not replace the whole checkout
or pull remote Cedar over the distinct diagnostic state.

The resulting fresh run retains the prior 5′-OH input policy and full-auto
bounds. Terminal final output, `campaign_summary.csv` and the Coot menu show
the exact displayed checkpoint's space group, falling back to the selected
Phaser model. The checksum-verified input MTZ header is retained separately;
when no model exists its space group is labelled as data-derived. Receipts add
`space_group`, source/artifact/hash provenance and `input_space_group`; absent
metadata remains explicit and cannot alter MR/refinement status.

Validation: **94 adapter tests and 22 subtests pass**. The assembled download
also passes parser installation, original-code backup, actual X11_20 terminal
preparation, source-preserving staging and a second already-fixed launch.
That integration is offline: reflection metadata are fixtures and only the
unavailable laptop-specific curated-source manifest entry is substituted with
the local fixture's hash. That offline check launched no native Phenix process;
the subsequent returned native rerun is verified below.

**Corrected native run and close-out, 2026-10-11:** `GeoTest_review(2).zip`
(SHA-256 `8ef30e37729d74631eae8b91b0ac1d04c52f4879cb5d96c0f9f30addc7c0a9f9`)
contains **462 hash/byte-verified files** and **138 declared compact omissions**.
The runtime reports Python **3.12.14**, Phenix **2.2.1-6174** and discovered
Coot **1.3.3**; the native batch completed in about 13 minutes. All nine workers
exited zero; 44 stage
snapshots, nine final native reports and per-case provenance match the aggregate.
The installer verified 46 source files, preserved the exact old parser backup,
and changed only `phaser.py` to the fixed hash above. Original inputs and all
other source hashes remain unchanged. All nine preparations remove exactly 28
terminal phosphate atom records; every other byte is preserved, including O5′,
and their native frozen search models match the preceding 5′-OH cohort.

| Member | Displayed space group | Final selected TFZ | Returned result | Rwork / Rfree |
| --- | --- | --- | --- | --- |
| X11_12 | P6 (input data only) | — | MR FAILED; no selected model | — |
| X11_16 | P2₁ | 14.5 | AUTOREFINE READY, refine-001 | 0.2940 / 0.3404 |
| X11_17 | P2₁ | 12.2 | AUTOREFINE READY, refine-001 | 0.2165 / 0.3325 |
| X11_18/dataset1 | P2₁ | 7.7 | Doctor REVIEW, inspection refine-002 | 0.4691 / 0.4859 |
| X11_18/dataset2 | P4₃ | 8.0 | Doctor REVIEW, inspection refine-002 | 0.3230 / 0.3418 |
| X11_19 | P4₃ | 13.8 | AUTOREFINE READY, refine-001 | 0.2421 / 0.2890 |
| X11_20 | P1 | 16.9 | AUTOREFINE READY, refine-001 | 0.2262 / 0.2336 |
| X11_22 | P1 | 15.3 | AUTOREFINE READY, refine-001 | 0.2647 / 0.2770 |
| X11_25 | P2₁ | 9.8 | AUTOREFINE READY, refine-001 | 0.2781 / 0.3179 |

All eight selected-model final TFZ/LLG annotations and displayed checkpoint
CRYST1 records match their checksummed provenance. X11_18/dataset2 and X11_19
have selected/refined **P4₃**, while their input headers remain **P4₁**; retain
both values. The user notes that X11_18's alternatives are different space
groups: the P4₃ inspection result has markedly lower Rfree (**0.3418**) than
the P2₁ / `P 1 21 1` result (**0.4859**) and analytically favors P4₃. Record
this as the user's structural interpretation and comparative evidence, without
changing either review/selection status. The two processing datasets have
distinct observation hashes and Free-R populations; this is not a controlled
same-data space-group ranking. Exactly **14 native refinement processes exited zero**: eight
ordinary refinements and six Doctor trials. Every command keeps original
`IMEAN,SIGIMEAN` observations, `FreeR_flag`, test value 0 and `generate=False`;
each of the eight registries retains its member's original observation hash. Both X11_18
cases keep current `postmr`, inspection-only `refine-002`, no recommendation
and no automatic selection. Their audits remain `NOISY` (546/10377 and 223/3937
free groups) with zero detected inconsistent flags and the explicit unavailable
Friedel-mate comparison limitation. Omitted reflection arrays were not replayed.

No infrastructure blocker remains. The user reports campaign success and asks
to wrap without further scientific repair. All members retain provisional,
inspection-required and unapproved status. In particular, X11_17 passes the
current numerical gate despite a **0.116 Rfree−Rwork gap** and **66.93 clashscore**;
the bond/angle RMSD summary limitation and local assembly/geometry issues remain.
These are fixtures for the planned Doctor geometry module, not approval of the
structures. Native campaign input/recipe integration remains separate future
work; this closes the standalone GeoTest orchestration test.

**Guided geometry follow-up:** the user requests geometry assessment and a
Scout-based guided arm/triangle stitcher bundled with Doctor, available after
MR or refinement once intended connections are declared. The
[contract](construct-registration.md#geotest-guided-arm-connection)
and [live-check queue](construct-registration-live-checks.md) retain this as
planned scope. The supplied Coot examples are `Screenshot 2026-10-11 at
13.53.45.png` (SHA-256
`215ae2967cb6fb5225d141636c766102c641bd87cfe000d7280bd246dd12d25f`) and
`Screenshot 2026-10-11 at 13.56.53.png` (SHA-256
`53fbade3270de9c19c9fc107a87d41a2b9cb7ba66836b5dd04a9c1ca3511e59b`).
They show local model/density discrepancies, without identified checkpoint or
residue selection; no atom-level connection is inferred from the pictures.
Original screenshots, coordinate models and reflection data remain outside Git.

## Restraint doctor and subsequent roadmap

The October 11 priority decision advances the **SMILES-assisted CIF/restraint
assessor** to the first implementation slice of the coordinated Doctor workflow
using the completed trials as evidence. Remaining combined-model qualification
stays explicit and may proceed
alongside it. The Doctor geometry/connectivity module will reuse Scout/Topo
primitives for guided repair; broader Topo slicing / operational Scout remains
later work. None becomes an additional Cedar/Pine merge gate.

- **SMILES-assisted CIF audit (planned, not implemented):** assessment first,
  comparing molecular graphs with atom mapping, charge/H/stereochemistry and
  descriptor provenance. Keep self-consistency separate from independent
  chemistry, and graph checks separate from numerical-restraint validation.
  Reviewed transformations such as 1W5→DZ remain explicit. Follow the initial
  assessor with separately tested, policy-bounded generation/validation and
  automatic continuation for ordinary passing cases. Exact reviewed repairs
  need version/hash policies; ambiguous chemistry needs declared intent, not
  an AI guess. Ordinary runs should not require AI or user source patches. The
  detailed [assessor and automation contract](modified-component-preparation.md#proposed-smiles-and-cif-audit)
  owns findings, uncertainty and repair boundaries. The
  [audit methods](cif-restraint-audit-methods.md) capture the reusable checks,
  5CM/DF/DP lessons, 8RO/DE and 1AP challenge cases, and proposed evidence schema
  for implementation. Broader repair requires those checks and negative controls,
  not merely successful regeneration of the three development cases.
- **Blind AlphaFold baseline after bounded Pine close-out:** preserve frozen
  predictions, observations and Free-R; avoid solved outcomes during blind
  candidate selection. Before this trial, add **PDB and coordinate mmCIF input**
  and an explicit **trust-model / no-sequence-file mode**, since supplied
  predictions may have no separate sequences. These are requested adapter
  capabilities, not implemented options. Record sequence as independently
  unverified, skip sequence-driven mutations, and retain ordinary model/MR
  checks. See [model roadmap](campaign-model-roadmap.md) and
  [architecture](architecture.md) for the proposed contract.
- **Campaign input follow-up:** support shared parent-folder models and nested
  processing datasets, including alternative space groups. Inventory/count
  candidates, run selected MR alternatives separately and compare their evidence.
  [Grouped-processing design](campaign-model-roadmap.md#planned-shared-model-folders-and-processing-alternatives)
  records the requested behavior; current flat discovery does not implement it.
- **Then operational Scout / later Topo surgery**, following the existing
  [registration contract](construct-registration.md) and
  [live checks](construct-registration-live-checks.md). The earlier order
  (blind AlphaFold baseline before operational Scout) remains. GUI/Topo Net
  and the metal-restraint builder remain separate later scopes.

## Evidence and preservation

The combined trial uses real GZ11 observations with hypothetical target
modifications: it is a software integration test, not proof of the crystal's
chemistry or deposition approval. Native completion, chemistry, numerical
metrics and human review remain separate verdicts. The earlier Z:P overall
Coot PASS is not a combined-model geometry verdict. The earlier directional
hydrogen-bond question remains parked; never impose an arbitrary heavy-atom
180° target or modify the successful old run to satisfy it.

Follow the [branch/worktree lifecycle](collaboration.md#branch-and-worktree-lifecycle).
One terminal action per user turn for native debugging, then inspect output.
Preserve the original dirty NASolve checkout, unpublished NARestraints
`Ligands.xlsx`/lockfiles, scientific runs, maps and Free-R. October 8–9
completed-worktree cleanup remains recorded in the backup; the private
lab-notes checkout was intentionally retained. Verify current laptop status
before integration; the returned clean Cedar check does not authorize cleaning
other laptop checkouts or changing the unpublished diagnostic head.

**Status ownership:** this handoff = current priorities; native ledger =
exact trial evidence; subsystem docs = durable contracts; history/Git =
earlier decisions. The October 10 reconciliation archives superseded text
before shortening it and keeps chronology out of the active queue.
