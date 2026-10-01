# NASolve development handoff

Updated 2026-10-01. **Finish Pine, merge to main, then make Scout operational.**
This is the single current-state and close-out entry point. Subsystem documents
own detailed contracts; history owns the earlier experiments and superseded
plans. Do not load every historical handoff for an ordinary implementation turn.

## Branches and scope

- Active work: `pine`, draft [PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
  into `main`. Latest user-tested dictionary code was committed and pushed as
  `66cb7a2295bd9ea79fb946b2312ea7e3acd7eb08`. Re-read the live ref before editing.
- Oak is already merged: [PR #22](https://github.com/vecchioni-lab/NASolve/pull/22),
  2026-09-28, merge `fec66ebeddbd525684824576b705460324ec0a14`. Its remaining remote
  branch has no additional work to merge. Check local-only work before retiring
  local references. Closing Oak does not promote Scout into runtime authority.
- Simon authorized routine integration/merge decisions and compact validation
  ferries at our discretion. That is not permission to skip the evidence gates
  below, overwrite scientific artifacts, or force-delete unmerged local work.

## Current evidence, not new validation

| Capability | Supported state |
| --- | --- |
| Standalone AutoMR -> PostMR -> conditional AutoSol -> AutoRefine | Operational guarded spine with immutable checkpoints. |
| Four-member W campaign and campaign-owned Refine Doctor | Earlier explicit continuation was live-validated: DOHU/EG/QE solved numerically; QiC Doctor recommended `refine-002` at 0.1500/0.1502, leaving `postmr` current. Same-invocation continuation has a newly identified defect below. |
| Prepared nonstandard and mixed schema-2 campaigns | Implemented and fixture-tested, including relocation. Real geometry-diverse campaign still pending; schema-1 support retained. |
| `pair = G:Z` / `force = G:C` | Separate identity/recipe pathways, regression-tested; real NARestraints generation and experimental PostMR audits passed. Not a production GZ11 refinement pass. |
| Category-based intermediate mutation hops (`88e2f53`) | Retained in the dictionary patch and its passing full regression. New production live integration pending. |
| Effective dictionary compatibility and DZ (`66cb7a2`) | Implemented and full-checkout regression-tested: 151 focused tests; 771 full tests + 224 subtests. Packaged DZ, content-based torsion adaptation and effective-bundle handling still require native GZ11 validation. |
| Pre-patch nine-member TestSets campaign | Member status returned: four numerical solutions, three PostMR blockers and two inspection cases; all integrity OK. QiC did not enter Doctor in the initial invocation. See baseline details below; P4 is not closed. |
| Component normalization | Standing `1W5 -> DZ` and `1WA -> DP` conversions and the DP resource remain pending; dictionary compatibility does not implement them. |
| Registration/Scout | Merged backend primitives and validated design-aware shadow proposal; not yet the operational AutoMR/PostMR decision path. |

The latest local transcript reports **151 focused tests in 3.66 s** and
**771 tests + 224 subtests in 66.78 s**. The apply/validate/publish ferry started
from `dd59b4f`, tested the patched working tree, then committed and pushed that
code as `66cb7a2`. This is returned user-local pytest evidence, not GitHub CI or
new native Coot/Phenix validation. The earlier 735-test report and 694 + 224
transcript are historical baselines. Do not repeat unchanged full regression
merely to update documentation.

## Immediate live check

Fresh `examples/TestSets/GZ11/AutoMR/run_002` reached MR_SUCCESS, TFZ 12.20, with
DG/DZ frozen as the target and G/C only as the pair-restraint recipe. At that
code head, PostMR stopped before mutation on the missing DZ construction parent.
The category-hop implementation subsequently addressed that lookup.

The copied-MR DZ-via-DC probe reached POSTMR_READY: B:4 DG -> DC -> DZ, A:12 DG,
with an actual G/Z -> recipe G/C audit. Refinement then failed before R statistics
on DZ B:4 C2e/C3e alternative sugar torsions over C4'-O4'-C1'-C2'. The actual
command consumed **PostMR/ReadySet/prepared_model.ligands.cif**, whose definition
still contained competing rows. This is the historical failure the new patch
targets, not a post-patch result.

The retained experiment was `nasolve-dz-dc-probe-kad1eax8` in Simon's macOS temp
area (`MR_snapshot/`, `probe_receipt.json`); availability must be checked, not
assumed. Preserve its failed checkpoint and the original GZ11 run. `Refine_74`
is Simon's manual pre-NASolve model and is not evidence NASolve introduced 1W5.
The probe is evidence, not the production solution or a permanent override.

The published patch supplies DZ locally, normalizes supported source/effective
torsions and freezes the selected bundle independently of phosphate profiles.
Its full-checkout regression is now green. Next: explicitly retry **only GZ11**
in the existing baseline campaign, then run that member through `autorefine`
to isolate native dictionary validation from the Doctor continuation defect.
Use campaign retry/run, not standalone edits to a campaign-owned run. This
creates a new attempt and numbered run while retaining the frozen input plan
and previous outputs. No post-patch native result is recorded yet.
The category-hop table remains unchanged. Specific 1W5/1WA conversions remain P2.
Use [modified-component preparation](modified-component-preparation.md) and
[component intent](modified-component-preparation-intent.json). Construction,
component identity, pairing recipes and dictionary compatibility stay separate.

## Nine-member baseline results

The pre-patch campaign at `~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`
finished before the dictionary patch was applied. Returned footer: plan/run/status
0/3/3, original copied-input bytes unchanged, outputs retained. Subsequent
read-only status reports `COMPLETE_WITH_FLAGS`, nine planned members, frozen
input integrity OK and integrity OK for every member. All reported runs are
`DATASET/AutoMR/run_001` under this campaign root.

| Member(s) | Returned outcome |
| --- | --- |
| DOHU, DT, ED, FA | `SOLVED`, checkpoint `refine-001`; numerical criteria passed, model/map inspection still required. ED retained `w-metal-scaffold`. |
| DiU | `BLOCKED` in PostMR: implausible ideal C5-I5 distance **8.843 A at B:4**. Investigate dictionary ideal coordinates/atom correspondence; this is not a measured refined bond or a reason to widen the construction guard. |
| EA | `AWAITING_INSPECTION` at MR, **TFZ 7.60**. No review acceptance for this new attempt is implied by older manual work. |
| GZ11 | `BLOCKED` in PostMR: missing local `DZ.cif` on the pre-patch code. The new resource is installed; its native construction/refinement check remains pending. |
| Q5cm | `BLOCKED` in PostMR: missing local `5CM.cif`. Separate resource follow-up; do not infer it was supplied by the DZ patch. |
| QiC | `AWAITING_INSPECTION`, `refine-001`, next stage `refine-doctor`. Status reports eligibility, not a completed Doctor trial or a recommendation. |

The initial ferry requested `--through refine-doctor`, yet QiC stopped before
that stage. Inspection of `campaign_execution.execute_campaign` at `79588ac`
finds the cause: its post-stage loop break still admits only DISCOVERED/PAUSED,
whereas `_runnable(item, through)` already permits eligible refinement REVIEW
for the explicitly requested Doctor endpoint. A second invocation can enter
Doctor; the single-invocation transition is not complete. Fix/test this bounded
coordinator defect separately, including ordinary default-endpoint behavior,
MR review isolation, recommendation non-selection and resumed-vs-fresh runs.
No coordinator patch or new Doctor execution is implied by this note.

This baseline demonstrates member-local stops with other members reaching
numerical solutions; it does not close P4's Doctor/resume/current-pointer gates
or replace P5. Preserve all attempts. Campaign retry/status may still return 3
because other members are flagged; do not mistake that for a failed retry or
suppress the selected run with an unconditional `&&` chain.

## Pine close-out

This is the finite merge path mirrored by PR #23. P1 is implemented with full
regression evidence; native confirmation remains pending under P3. P4 now has
reviewed member status and a concrete same-invocation Doctor defect, not a
completed gate. Record exact code/evidence when closing each.

| Gate | Completion evidence |
| --- | --- |
| **P1 — Effective dictionary compatibility** | Generalize the supported CCP4 alternative-torsion handling beyond the 1AP-only dispatch; the effective refinement bundle retains it after ReadySet/checkpoint creation. Regress 1AP and ordinary/curated cases, ordered/reversed quartets, periods, existing alternatives and unequal uncertainties. Preserve source/derivative provenance; no arbitrary chemical repair. |
| **P2 — Specific component normalization** | Implement the requested standing `1W5 -> DZ` and `1WA -> DP` preparation policy with usable target definitions, reviewed atom correspondence and conversion provenance. Preserve raw/frozen originals; do not assume changing a name realizes the target chemistry. |
| **P3 — Normal GZ11 live path** | Fresh ordinary preparation/refinement without the temporary registry override. Audit DG/DZ identities, G/Z -> G/C force application, effective dictionaries, and local component/backbone geometry. Usable REVIEW is acceptable; no fabricated numerical pass. |
| **P4 — Nine-member TestSets campaign** | One frozen disposable campaign through explicit campaign-owned `--through refine-doctor`, accounting for every dataset and checking integrity/resume/isolation/current-pointer behavior. Fix and validate the identified same-invocation Doctor transition. Solved, recommended, REVIEW, NO_SOLUTION and genuine BLOCKED outcomes all remain reportable; nine greens are not required. |
| **P5 — Prepared-nonstandard live campaign** | Real 3-5-member geometry-diverse prepared-PDB + exact-sequence campaign with Phenix/Coot. Check ownership and review/block behavior. W-only or simulated workers do not replace this gate; no new registration/model generator is required. |
| **P6 — Final candidate regression/review** | Focused and full suite on the final code, exact SHA/commands/results/runtime versions, available CI/diff checks, and consistent user guide/subsystem/handoff/intent/changelog. No scientific data is uploaded implicitly. |
| **P7 — Merge and retire branches** | Merge PR #23 only after P1-P6; verify ancestry, inspect Simon's status/worktrees/local-only commits, then switch/pull main and retire merged Pine/Oak references without force or data cleanup. |

Use [campaign execution](campaign-execution.md) for receipt ownership and stage
semantics. The merge does **not** require GUI/Design implementation, Scout
runtime promotion, Topo Net/Surgeon, donor rescue, more model providers, generic
MTZ/SCA input, a workflow-recipe builder, or a universal chemistry library.
Known residue fixes are welcome; recognition of every possible component is
not a gate. Changes to this finite scope must be explicit, not implied.

## After Pine: operational Scout

**Next priority after returning to main: make Scout usable in the ordinary
CLI/AutoMR/PostMR workflow. Do not wait for GUI, Topo Net or donor rescue.**
The existing [registration contract](construct-registration.md),
[registration intent](construct-registration-intent.json) and
[live-check queue](construct-registration-live-checks.md) remain the technical
basis. This priority statement does not silently grant runtime authority.

Plan the next bounded integration around:

1. Cheap, non-mutating Scout preflight on the actual frozen candidate/construct,
   with persisted results and clear CLI/campaign reporting; keep the ordinary W
   path simple and try plausible preserved MR candidates before expensive recuts.
2. Post-MR registration and logical-site handoff under an explicit reviewed
   promotion/application policy. Proposal, accepted mapping and coordinate edit
   remain different events; ambiguous mappings retain guided review.
3. Real ordinary-W, renamed/renumbered-W and ambiguity checks plus provenance,
   continuation and regression checks before claiming operational coverage.

Reuse the validated provider-bound zero-unexplained uniqueness rule; no hidden
similarity ranking or caller-supplied unbound residue dictionary. Broader ASU
cuts, multiplicity, topology and rescue follow their own reviewed/live gates.
Design-before-GUI remains intact but is not a new prerequisite for CLI Scout.

## Working and documentation discipline

Continue on library-backed chemistry when missing NASolve recognition is only
an optional annotation/diagnostic limitation; record provenance and warnings.
Necessary stops belong to unusable required operations or scientific-integrity
failures, scoped to the affected dataset. This is agreed continuation direction,
not a claim that all broader runtime gates have already been changed.

Use one coherent implementation slice and one sequential ferry, then diagnose
the first meaningful outcome. Final code changes get focused/full regression
and exact live-tool evidence where relevant. Documentation-only edits get
link/JSON/diff checks and must not promote scientific validation status.

Keep current status and ordering here, component policy in its subsystem doc,
registration policy in its own contract, and archival detail in history. Update
machine development intent with references rather than repeating entire diaries.
PR #23 tracks review/check boxes against this path. Update the public README
only for changed usable behavior; do not expand it with session notes.

Preserve immutable models, dictionaries, observations/Free-R, maps and failed
attempts. No unrelated untracked sheep, patches, environments or local-only
commits are staged/deleted. Historical DE/sulfur and 1AP issues remain in the
[earlier audits](history/README.md); this consolidation approves no chemistry.
The [October 1 addendum](development-handoff-2026-10-01-addendum.md) is now a
redirect, not another current-state authority.
