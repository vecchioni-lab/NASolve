# NASolve development handoff

Updated 2026-10-01. **Finish Pine, merge to main, then make Scout operational.**
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
| Four-member W campaign and campaign-owned Refine Doctor | Earlier explicit continuation was live-validated: DOHU/EG/QE solved numerically; QiC Doctor recommended `refine-002` at 0.1500/0.1502, leaving `postmr` current. Same-invocation continuation has a newly identified defect below. |
| Prepared nonstandard and mixed schema-2 campaigns | Implemented and fixture-tested, including relocation. Real geometry-diverse campaign still pending; schema-1 support retained. |
| `pair = G:Z` / `force = G:C` | Separate identity/recipe pathways, regression-tested; earlier real NARestraints and experimental PostMR audits passed. Fresh production GZ11 now reached SOLVED; its detailed force audit has not yet been returned. |
| Category-based intermediate mutation hops | Included in passing dictionary-patch regression and the fresh successful GZ11 workflow. Do not infer new live validation for every category. |
| Effective dictionary compatibility and DZ (`66cb7a2`) | 151 focused tests and 771 full tests + 224 subtests passed. Fresh ordinary campaign-owned GZ11 reached `SOLVED` at `run_002/refine-001`; the former execution blocker no longer prevents refinement. Detailed effective-bundle/local-geometry inspection remains pending. |
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

This is live ordinary-pipeline execution evidence for the dictionary fix, not
merely another unit-test or temporary-probe pass. Do not rerun it merely to
collect evidence: inspect the successful checkpoint and its reports. The
transcript does not contain exact R factors, native tool versions, final atom
inventory, detailed force/effective-dictionary audit or local geometry values;
those are pending inspection, not inferred from SOLVED. The AutoSol stage name
alone does not show whether its engine ran or the conditional gate skipped it.
Structural approval and P2 component conversions are not established.

Next: inspect `GZ11/AutoMR/run_002`, `refine-001`, and the existing PostMR/refinement
receipts for identities, G/Z -> G/C application, effective dictionaries and local
geometry. Then fix/test the bounded same-invocation Doctor transition below;
track DiU and 5CM resource issues without touching successful runs. No new full
campaign or Scout execution is needed to inspect this result.

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
| GZ11 | Initially missing `DZ.cif`; patched attempt_002 now `SOLVED`, `run_002/refine-001`, integrity OK. Detailed inspection pending. |
| DiU | `BLOCKED` in PostMR: implausible ideal C5-I5 distance **8.843 A at B:4**. Inspect dictionary coordinates/atom correspondence; not a measured refined bond or a reason to widen the guard. |
| EA | `AWAITING_INSPECTION` at MR, **TFZ 7.60**. No review acceptance is implied by older manual work. |
| Q5cm | `BLOCKED` in PostMR: missing local `5CM.cif`; not supplied by the DZ patch. |
| QiC | `AWAITING_INSPECTION`, `refine-001`, next stage `refine-doctor`. Eligibility is not a completed Doctor trial. |

The initial ferry requested `--through refine-doctor`, yet QiC stopped before
that stage. `campaign_execution.execute_campaign` at `79588ac` has a post-stage
break admitting only DISCOVERED/PAUSED, while `_runnable(item, through)` already
permits eligible refinement REVIEW for the explicit Doctor endpoint. A second
invocation can enter Doctor; the single-invocation transition needs a code/test
fix. Cover default-endpoint behavior, MR review isolation, recommendation
non-selection and resumed versus fresh execution. No fix or new Doctor result
is implied by the GZ11 retry, which deliberately ended at AutoRefine.

Member-local failure isolation is demonstrated; P4's Doctor/resume/current-pointer
coverage and P5 remain separate. Preserve attempts. Retry/status can return 3
because other members are flagged; do not suppress a successful selected retry
with an unconditional `&&` chain.

## Pine close-out

P1 has implementation, full regression and fresh live execution evidence. P3's
normal execution passed; its detailed identity/force/bundle/local-geometry
inspection remains. P4 has member outcomes plus a concrete coordinator defect.
Do not automatically close every gate or approve a structure from a SOLVED flag.

| Gate | Completion evidence |
| --- | --- |
| **P1 — Effective dictionary compatibility** | Generalized input/effective torsion handling and authoritative selection are implemented and regression-tested; fresh GZ11 numerical execution passed. Check its exact effective-bundle receipt alongside P3 inspection. |
| **P2 — Specific component normalization** | Implement standing `1W5 -> DZ` and `1WA -> DP` preparation with target definitions, atom correspondence and conversion provenance. Preserve raw/frozen originals. |
| **P3 — Normal GZ11 live path** | Fresh ordinary execution passed on 66cb7a2. Finish inspection of DG/DZ identities, G/Z -> G/C force audit, effective dictionaries and local component/backbone geometry in the existing successful checkpoint. |
| **P4 — Nine-member TestSets campaign** | Account for every member and validate integrity/resume/isolation/current-pointer behavior through campaign-owned Doctor; fix and validate the same-invocation transition. Legitimate REVIEW/NO_SOLUTION/BLOCKED outcomes are not failures to manufacture away. |
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
