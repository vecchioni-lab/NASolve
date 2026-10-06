# NASolve development handoff

Updated 2026-10-06. **Finish Pine, merge to main, then make Scout operational.**
This is the single current-state and close-out entry point. Subsystem documents
own detailed contracts; history owns the earlier experiments and superseded
plans. Do not load every historical handoff for an ordinary implementation turn.

## Branches and scope

- Active work: `pine`, draft [PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
  into `main`. Latest user-tested dictionary code was committed and pushed as
  `66cb7a2295bd9ea79fb946b2312ea7e3acd7eb08`. The fresh GZ11 transcript explicitly
  prints checkout `66cb7a2`. Re-read the live ref before editing.
- Oak is already merged: [PR #22](https://github.com/vecchioni-lab/NASolve/pull/22),
  2026-09-28, merge `fec66ebeddbd525684576b705460324ec0a14`. Its remaining remote
  branch has no additional work to merge. Check local-only work before retiring
  local references. Closing Oak does not promote Scout into runtime authority.
- Simon authorized routine integration/merge decisions and compact validation
  ferries at our discretion. Preserve scientific artifacts and local-only work;
  mergeability alone does not satisfy the evidence gates below.

## Current evidence

| Capability | Supported state |
| --- | --- |
| Standalone AutoMR -> PostMR -> conditional AutoSol -> AutoRefine | Operational guarded spine with immutable checkpoints. |
| Four-member W campaign and campaign-owned Refine Doctor | Earlier explicit continuation was live-validated: DOHU/EG/QE solved numerically; QiC Doctor recommended `refine-002` at 0.1500/0.1502, leaving `postmr` current. The same-invocation fix is implemented below; new native confirmation remains pending. |
| Prepared nonstandard and mixed schema-2 campaigns | Implemented and fixture-tested, including relocation. Real geometry-diverse campaign still pending; schema-1 support retained. |
| `pair = G:Z` / `force = G:C` | Separate identity/recipe pathways, regression-tested; earlier real NARestraints and experimental PostMR audits passed. Fresh production GZ11 now reached SOLVED and passed Simon's requested visual check; its detailed force receipt has not yet been returned. |
| Category-based intermediate mutation hops | Included in passing dictionary-patch regression and the fresh successful GZ11 workflow. Do not infer new live validation for every category. |
| Effective dictionary compatibility and DZ (`66cb7a2`) | 151 focused tests and 771 full tests + 224 subtests passed. Fresh ordinary GZ11 reached `SOLVED` at `run_002/refine-001`; Simon subsequently inspected that model/maps in Coot and reported a successful visual result. Detailed effective-bundle receipts and numerical local-geometry values remain unreturned. |
| Nine-member campaign after the GZ11 retry | Five numerical solutions, two preparation blockers and two inspection cases; frozen input/member integrity OK. P4 Doctor/resume coverage is not yet complete. |
| Component normalization | Standing `1W5 -> DZ` and `1WA -> DP` conversions and the DP resource remain pending; dictionary compatibility does not implement them. |
| Registration/Scout | Merged backend primitives and validated design-aware shadow proposal; not yet the operational AutoMR/PostMR decision path. |

Latest returned regression: **151 focused tests in 3.66 s**, then **771 tests +
224 subtests in 66.78 s**. The ferry tested a working tree based on `dd59b4f`,
then committed/pushed it as `66cb7a2`. This is user-local pytest evidence, not CI.
The 735-test report and 694 + 224 transcript remain historical baselines.
Do not repeat unchanged full regression merely to update documentation.

## Fresh GZ11 result and immediate next action

Campaign root: `~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`.
On checkout **66cb7a2**, Simon used ordinary `campaign retry --dataset GZ11`
followed by `campaign run --dataset GZ11 --through autorefine`. It allocated
**attempt_002 / GZ11/AutoMR/run_002**, rather than reusing failed PostMR outputs.
The returned stage trace proceeds through preflight, Phaser, PostMR, the AutoSol
gate and AutoRefine, ending **SOLVED**, checkpoint **refine-001**, integrity OK.
No temporary dictionary/provider injection appears in this invocation.

The final campaign status remains `COMPLETE_WITH_FLAGS`; retry/run/status all
returned 3 because other members remain flagged. GZ11 itself passed numerical
refinement criteria. The four earlier numerical solutions retain their original
run/checkpoint paths. The old GZ11 campaign `run_001` remains historical.

Simon then ran `nasolve show` for this exact `run_002/refine-001`. The returned
launch trace names `AutoRefine/round_001/refined_001.pdb` and its matching
`refined_001.mtz`, not a manual model or temporary probe. Asked to check DG A:12,
DZ B:4, base placement in density and the adjoining sugar/phosphate, Simon
reported: "It's a perfect speckled sheep." Record this as a **passed
user-reported visual Coot inspection of the requested local G/Z check**.
No additional rerun or repeated visual confirmation is needed for that check.

Exact R factors, native tool versions, an extracted atom inventory, detailed
force/effective-dictionary receipts and numerical local-geometry values have
not been returned. Read those from the existing outputs when completing the
merge evidence; do not infer numbers from the visual report. The AutoSol stage
name alone does not establish whether its engine ran or the gate skipped it.
This documentation record does not change the local checkpoint's approval
state, assert deposition readiness or implement P2 component conversions.

Next live slice: validate the same-invocation Doctor fix with a fresh campaign-owned QiC attempt.
Complete the remaining GZ11 receipt review from its saved outputs without
rerunning the successful structure. Track DiU and 5CM resource issues without
touching successful runs. Scout remains after Pine campaign closure.

Historical distinction: `examples/TestSets/GZ11/AutoMR/run_002` in the source
checkout was an earlier blocked standalone run, not this successful campaign
run. The temporary `nasolve-dz-dc-probe-kad1eax8/MR_snapshot` reached preparation
but failed on DZ sugar alternatives; it too is historical. Manual `Refine_74`
is not proof NASolve introduced 1W5. Preserve all three histories. Details are
in [history](history/README.md); current component policy is in
[modified-component preparation](modified-component-preparation.md) and
[component intent](modified-component-preparation-intent.json).

## Nine-member baseline results

Before the patch, the campaign at the root above returned plan/run/status
0/3/3 with copied source-input bytes unchanged and all input/member integrity
OK. Every initial member used `DATASET/AutoMR/run_001`. After the patched GZ11
retry, the returned status is:

| Member(s) | Returned outcome |
| --- | --- |
| DOHU, DT, ED, FA | `SOLVED`, original `run_001/refine-001`; inspection still required. ED retains `w-metal-scaffold`. |
| GZ11 | Initially missing `DZ.cif`; patched attempt_002 now `SOLVED`, `run_002/refine-001`, integrity OK, with a subsequent passed user visual inspection. Detailed receipt review remains. |
| DiU | `BLOCKED` in PostMR: implausible ideal C5-I5 distance **8.843 A at B:4**. Inspect dictionary coordinates/atom correspondence; not a measured refined bond or a reason to widen the guard. |
| EA | `AWAITING_INSPECTION` at MR, **TFZ 7.60**. No review acceptance is implied by older manual work. |
| Q5cm | `BLOCKED` in PostMR: missing local `5CM.cif`; not supplied by the DZ patch. |
| QiC | `AWAITING_INSPECTION`, `refine-001`, next stage `refine-doctor`. Eligibility is not a completed Doctor trial. |

The baseline's same-invocation Doctor skip is addressed by reusing
`_runnable(item, through)` at the post-stage break. An explicitly requested
Doctor endpoint can now consume a new AutoRefine REVIEW; the default
endpoint, other stops, pause, verified receipts and non-selection remain
unchanged. Tests cover fresh/resumed invocation, early review/failure,
once-only execution, drift, member isolation and the real stage engines
with fixture executables/checkpoints. Full-checkout validation is recorded
by the ferry below; fresh native QiC confirmation is still separate.

Member-local failure isolation is demonstrated; P4's Doctor/resume/current-pointer
coverage and P5 remain separate. Preserve attempts. Retry/status can return 3
because other members are flagged; do not suppress a successful selected retry
with an unconditional `&&` chain.

## Pine close-out

P1 has implementation, full regression and fresh live execution evidence. P3's
normal execution and requested user visual inspection passed; detailed saved
receipts and numerical audit values remain to be reviewed. P4 has member outcomes
plus an implemented coordinator fix pending new native confirmation. This update does not close every gate or
change checkpoint approval state.

| Gate | Completion evidence |
| --- | --- |
| **P1 — Effective dictionary compatibility** | Generalized input/effective torsion handling and authoritative selection are implemented and regression-tested; fresh GZ11 numerical execution and user visual inspection passed. Check its exact effective-bundle receipt alongside P3. |
| **P2 — Specific component normalization** | Implement standing `1W5 -> DZ` and `1WA -> DP` preparation with target definitions, atom correspondence and conversion provenance. Preserve raw/frozen originals. |
| **P3 — Normal GZ11 live path** | Fresh ordinary execution passed on 66cb7a2; the requested G/Z model/map visual inspection subsequently passed according to Simon. Complete exact identity/force/effective-input and numerical geometry evidence from saved reports; no repeated execution or visual check required. |
| **P4 — Nine-member TestSets campaign** | Account for every member and validate integrity/resume/isolation/current-pointer behavior through campaign-owned Doctor; validate the implemented same-invocation transition on fresh native QiC. Legitimate REVIEW/NO_SOLUTION/BLOCKED outcomes are not failures to manufacture away. |
| **P5 — Prepared-nonstandard live campaign** | Real 3-5-member geometry-diverse prepared-PDB + exact-sequence campaign with Phenix/Coot, ownership and review/block checks. W-only or simulated workers do not substitute. |
| **P6 — Final candidate regression/review** | Final-code focused/full suite, exact SHA/commands/results/tool versions, diff/available CI review and consistent documentation. No scientific-data upload implied. |
| **P7 — Merge and retire branches** | Merge PR #23 after P1-P6; verify ancestry and local status/worktrees/commits, switch/pull main and retire merged Pine/Oak references without force or data cleanup. |

Use [campaign execution](campaign-execution.md) for receipt ownership. GUI/Design,
Scout runtime promotion, Topo Net/Surgeon, donor rescue, new providers, generic
MTZ/SCA input, workflow-recipe builders and a universal chemistry library are
not Pine merge prerequisites. Keep the scope finite and changes explicit.

## After Pine: operational Scout

**Next after returning to main: operational CLI/AutoMR/PostMR Scout, without
waiting for GUI, Topo Net or donor rescue.** The [registration contract](construct-registration.md),
[registration intent](construct-registration-intent.json) and
[live-check queue](construct-registration-live-checks.md) remain authoritative.
This priority statement does not grant runtime authority.

1. Cheap non-mutating preflight on actual frozen candidates/constructs, persisted
   evidence and CLI/campaign reporting; ordinary W remains simple.
2. Post-MR registration and logical-site handoff under reviewed application
   rules; proposals, accepted mappings and coordinate edits stay distinct.
3. Ordinary/renamed/renumbered-W and ambiguity live checks plus provenance,
   continuation and regression before claiming operational coverage.

Reuse provider-bound zero-unexplained uniqueness, not hidden similarity ranking
or unbound caller dictionaries. Broader ASU cuts/multiplicity/topology/rescue
keep their own gates. Design-before-GUI is not a prerequisite for CLI Scout.

## Working and documentation discipline

Library-backed chemistry should continue when missing NASolve recognition is
only an optional annotation/diagnostic limitation; retain warnings/provenance.
Necessary stops belong to unusable required operations or scientific-integrity
failures and remain dataset-local. Broader gate relaxation is not yet claimed.

One coherent slice and one sequential ferry, then diagnose the first meaningful
outcome. Code changes get focused/full regression and relevant live evidence;
docs-only edits must not promote unobserved scientific validation. Keep status
here, policy in subsystem docs, archaeology in history and PR #23 as the review
tracker. Update machine intent without copying entire diaries. Public README
changes require changed usable behavior, not another session note.

Preserve immutable models/dictionaries, observations/Free-R, maps and attempts.
Do not stage/delete unrelated untracked data, patches, environments or commits.
Historical DE/sulfur and 1AP issues remain in the [earlier audits](history/README.md);
their chemistry is not approved by this result. The
[October 1 addendum](development-handoff-2026-10-01-addendum.md) is a redirect.

## Doctor-transition patch validation

The local apply/validate ferry tested the working tree based on `a3353c5`.
Campaign family: **148 passed, 85 subtests passed in 37.94s**. Full suite: **785 passed, 224 subtests passed in 67.75s (0:01:07)**.
Tested coordinator Git blob: `23a4cab2f32d3e91e65c8e4ad4fe7b794e1eac27`.
This is local regression evidence, not CI or a new native Doctor result.
The command prints the resulting commit and retains exact logs/receipts outside Git.

The next live ferry explicitly retries only QiC and requests the Doctor
endpoint in one run invocation. Old QiC and successful GZ11 runs remain
intact. If ordinary refinement passes directly, report that result rather
than manufacturing a review; it does not exercise the Doctor transition.
P4 and the main merge remain open until their evidence is reviewed.
