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
  2026-09-28, merge `fec66ebeddbd525684576b705460324ec0a14`. Its remaining remote
  branch has no additional work to merge. Check local-only work before retiring
  local references. Closing Oak does not promote Scout into runtime authority.
- Simon authorized routine integration/merge decisions and compact validation
  ferries at our discretion. That is not permission to skip the evidence gates
  below, overwrite scientific artifacts, or force-delete unmerged local work.

## Current evidence, not new validation

| Capability | Supported state |
| --- | --- |
| Standalone AutoMR -> PostMR -> conditional AutoSol -> AutoRefine | Operational guarded spine with immutable checkpoints. |
| Four-member W campaign and campaign-owned Refine Doctor | Live-validated: DOHU/EG/QE solved numerically; QiC Doctor recommended `refine-002` at 0.1500/0.1502, leaving `postmr` current. |
| Prepared nonstandard and mixed schema-2 campaigns | Implemented and fixture-tested, including relocation. Real geometry-diverse campaign still pending; schema-1 support retained. |
| `pair = G:Z` / `force = G:C` | Separate identity/recipe pathways, regression-tested; real NARestraints generation and experimental PostMR audits passed. Not a production GZ11 refinement pass. |
| Category-based intermediate mutation hops (`88e2f53`) | Retained in the dictionary patch and its passing full regression. New production live integration pending. |
| Effective dictionary compatibility and DZ (`66cb7a2`) | Implemented and full-checkout regression-tested: 151 focused tests; 771 full tests + 224 subtests. Packaged DZ, content-based torsion adaptation and effective-bundle handling still require native GZ11 validation. |
| Pre-patch nine-member TestSets campaign | Command returned at `dd59b4f`: plan/run/status exits 0/3/3; copied source-input bytes unchanged. Only the footer was supplied; per-dataset outcomes and gate completion are not established. |
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
Its full-checkout regression is now green; the next native check must use a
fresh ordinary GZ11 attempt without an experimental registry override. The
category-hop table remains unchanged. Specific 1W5/1WA conversions remain P2.

The baseline campaign finished before the patch was applied:
`~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`. Returned footer: plan 0,
run 3, status 3, original copied-input bytes unchanged, outputs retained.
First obtain its read-only per-dataset status, including GZ11, before selecting
a campaign-owned fresh retry or a separate fresh validation run. Do not infer
which datasets solved or why any blocked from aggregate exit codes. Preserve
old attempts and input/Free-R provenance; do not reuse old PostMR as new patch
validation or run standalone Doctor on a campaign-owned run.
Use [modified-component preparation](modified-component-preparation.md) and
[component intent](modified-component-preparation-intent.json). Construction,
component identity, pairing recipes and dictionary compatibility stay separate.

## Pine close-out

This is the finite merge path mirrored by PR #23. P1 is implemented with full
regression evidence; native confirmation remains pending under P3. P4 has a
returned pre-patch footer, not reviewed member outcomes. No gate is closed by
this documentation update. Record exact code/evidence when closing each.

| Gate | Completion evidence |
| --- | --- |
| **P1 — Effective dictionary compatibility** | Generalize the supported CCP4 alternative-torsion handling beyond the 1AP-only dispatch; the effective refinement bundle retains it after ReadySet/checkpoint creation. Regress 1AP and ordinary/curated cases, ordered/reversed quartets, periods, existing alternatives and unequal uncertainties. Preserve source/derivative provenance; no arbitrary chemical repair. |
| **P2 — Specific component normalization** | Implement the requested standing `1W5 -> DZ` and `1WA -> DP` preparation policy with usable target definitions, reviewed atom correspondence and conversion provenance. Preserve raw/frozen originals; do not assume changing a name realizes the target chemistry. |
| **P3 — Normal GZ11 live path** | Fresh ordinary preparation/refinement without the temporary registry override. Audit DG/DZ identities, G/Z -> G/C force application, effective dictionaries, and local component/backbone geometry. Usable REVIEW is acceptable; no fabricated numerical pass. |
| **P4 — Nine-member TestSets campaign** | One frozen disposable campaign through explicit campaign-owned `--through refine-doctor`, accounting for every dataset and checking integrity/resume/isolation/current-pointer behavior. Solved, recommended, REVIEW, NO_SOLUTION and genuine BLOCKED outcomes all remain reportable; nine greens are not required. |
| **P5 — Prepared-nonstandard live campaign** | Real 3-5-member geometry-diverse prepared-PDB + exact-sequence campaign with Phenix/Coot. Check ownership and review/block behavior. W-only or simulated workers do not replace this gate; no new registration/model generator is required. |
| **P6 — Final candidate regression/review** | Focused and full suite on the final code, exact SHA/commands/results/runtime versions, available CI/diff checks, and consistent user guide/subsystem/handoff/intent/changelog. No scientific data is uploaded implicitly. |
| **P7 — Merge and retire branches** | Merge PR #23 only after P1-P6; verify ancestry, inspect Simon's status/worktrees/local-only commits, then switch/pull main and retire merged Pine/Oak references without force or data cleanup. |

TestSets members: **DOHU, DT, DiU, EA, ED, FA, GZ11, Q5cm, QiC**. They have the
current AutoPROC/STARANISO input profile. Preserve all existing histories,
including EA/ED and GZ11 runs. The returned baseline footer alone does not
validate the nine-member gate. Use [campaign execution](campaign-execution.md)
for receipt ownership and stage semantics.

The merge does **not** require GUI/Design implementation, Scout runtime
promotion, Topo Net/Surgeon, donor rescue, more model providers, generic MTZ/SCA
input, a workflow-recipe builder, or a universal chemistry library. Known
residue fixes are welcome; recognition of every possible component is not a
gate. Changes to this finite scope must be explicit, not added by implication.

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
