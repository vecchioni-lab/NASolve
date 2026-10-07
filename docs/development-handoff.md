# NASolve development handoff

Updated 2026-10-07. **Finish Pine -> main -> blind AlphaFold geometry campaign -> Scout.**
This is the current-state and finite close-out entry point. Subsystem contracts
own policy, the linked validation records own detailed evidence, and Git/history
preserves earlier states. Do not ingest every historical handoff for routine work.

## Branches and scope

- Active branch: `pine`, draft [PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
  into `main`. Latest **published and locally regression-tested runtime** is
  **`9ef67fcc98ee1e923e70a86126ffe880d363dd17`**; previous P2 code
  `dec56c2` and annotated grammar `719c6e` are ancestors. The returned native
  Z:P attempt failed in NARestraints PostMR, not in the earlier tests.
  Re-read the live ref before editing; documentation-only commits may follow.
- Oak was merged in [PR #22](https://github.com/vecchioni-lab/NASolve/pull/22)
  on 2026-09-28. Check ancestry and local-only work before retiring references.
  A remaining Oak branch does not imply another implementation prerequisite.
- Simon authorized routine integration decisions and compact sequential ferries.
  Preserve scientific and local-only work. No main merge has been performed by
  this update; passing Git mergeability is not the remaining validation evidence.

## Current implementation slice and continuity

The annotated chain-sequence grammar is published as `719c6e`, with the
reviewed literal `(A1AAZ)` -> working PDB code `DF` bridge, paired-site
targeting and regression at **`9ef67fc`**. Simon returned **175 focused tests +
23 subtests** and **955 full tests + 224 subtests**, all passing. The frozen W
matrix keeps A:7 5CM/C:9 DG, A:19 DF/D:4 DA, and A:12 DZ/B:4 DP with
`pair = Z:P` (no `force` override).

The *first actual native* GZ11_ZP test is already underway:
`~/NASolve-live-tests/zp-paired-native-oiipj_t2/GZ11_ZP/AutoMR/run_001`.
Its 42-residue preflight/integrity and native Phaser passed with **TFZ 12.9,
LLG 210**. PostMR correctly **BLOCKED** on a real NARestraints role error:
`A:12 (Z) has no mapped atom 'N2' for GC recipe`. The installed model audit
showed Z is cytosine-like (O2/N3/N4) and P guanine-like (N1/N2/O6).
An in-memory corrected-role and stacking test passed without changing the
installed package. A separate [NARestraints draft PR #4](https://github.com/vecchioni-lab/NARestraints/pull/4)
contains the proposed Z:P and K:X role/stacking corrections, workbook-backed
B:S/Z:P/K:X/D:T regression and a staging-only native W matrix helper.
Its [GitHub Actions run 37688052270](https://github.com/vecchioni-lab/NARestraints/actions/runs/37688052270)
passed Python 3.10/3.12/3.14, including wheel/sdist and the separate
source-checkout stager tests (publish skipped). **Do not merge/ship it until
user-local clean-candidate testing and native checks have returned.** CI
does not validate the modified local workbook or the native chemistry and
does not waive other P2 source-alias conversion evidence or human approval.

The sibling `../NARestraints` checkout is on
`feature/terminal-phosphate-op3-angles` with a modified
`restraints/data/Ligands.xlsx`, other uncommitted work and an Excel lockfile.
**Do not checkout/reset/stash/clean/reinstall over that directory.** Validate the
PR using an independent worktree/clone in the same NASolve terminal. The
[bounded live modified-pair matrix and human evidence ledger](native-modified-pair-live-validation.md)
records the new B:S/Z:P/K:X/D:T plus canonical A:T cases, missing native
dictionary blockers, steps, and human Coot/PHIL/.geo review. It links but does
not close the separately scoped [Registration/Topo human tests](construct-registration-live-checks.md)
or [GUI human tests](gui-live-checks.md).

**P2 implementation, fixture recovery, full-checkout regression and publication
are complete. Native DP/alias validation remains the next live check.**
Do not reapply or resume either P2 installer merely to refresh this record.

| Returned local P2 regression | Result |
| --- | --- |
| Focused conversion/PostMR/dictionary/campaign checks | 276 passed, 20 subtests passed in 20.59 s |
| Full NASolve suite | 927 passed, 224 subtests passed in 78.72 s |

The recovered tree was based on `e13df41` and committed/pushed as `dec56c2`
after unstaged and staged diff hygiene passed. Returned status showed no tracked
changes and only existing untracked files. These are Simon's local pytest
results, not independently executed CI or a native DP refinement result.

Original failed evidence: `~/NASolve-live-tests/p2-components-lh21asu3/receipt.json`
and `focused.log`. Successful recovery/publication receipt:
`~/NASolve-live-tests/p2-components-lh21asu3/fixture-geometry-recovery/receipt.json`.
Those are user-local provenance, not repository inputs; preserve both histories.

The four initial integration failures came from synthetic incoming O3' placement,
not conversion-induced geometry. The fixture correction changed one test file
and its documentation, not the production phosphate guard or supplier geometry.
See [P2 details](modified-component-preparation.md#standing-preferred-component-preparation-p2)
and its [returned regression](modified-component-preparation.md#returned-local-p2-regression).

P2 supplies new prepared-derivative `1W5 -> DZ` and `1WA -> DP` normalization,
explicit atom correspondence, target dictionaries and source/target provenance.
DP uses the DG construction hop; DZ uses DC. Other intermediate rules and the
separate pair-geometry override remain settled. Frozen raw inputs and completed
checkpoints are not retrospectively relabelled.

The [metal-restraint builder](metal-restraint-builder.md) remains planned,
not implemented or a Pine gate. Its examples/numerical targets will come from
Simon. The post-Pine blind study has not yet supplied files for inspection here.

## New authorized slice: recipe-controlled full auto

[Full auto](campaign-full-auto.md) is implemented, published and exercised by a
fresh four-member native campaign. Its typed schema-2 recipe authorizes retained
borderline MR trials, explicit rejected-phase fallback, bounded Doctor and
reversible provisional selection. Core Doctor and old guarded recipes remain
non-selecting. Automatic selection never writes USER_APPROVED or changes Free-R.
A new policy requires a new frozen plan, not editing the old TestSets manifest.

Native EA/DiU/Q5cm/QiC execution and the actual supplied phase inputs are recorded
in the [full-auto checkpoint](full-auto-patch-handoff.md). The reporting-only
phase-use correction was published as `debd4af`, with 109 focused tests and
878 full tests + 224 subtests before P2. Old inaccurate audit Booleans remain
historical; no stored receipts were rewritten. No repeat campaign is needed
for that completed diagnostic correction.

## Current evidence

| Capability | Supported state |
| --- | --- |
| Ordinary AutoMR -> PostMR -> conditional AutoSol -> AutoRefine | Operational spine with immutable checkpoints. |
| Category hops/effective dictionaries/DZ | Published and regression-tested; fresh ordinary GZ11 and Simon's requested visual check passed. Detailed saved receipt review remains. |
| Guarded campaign Doctor | Fresh QiC entered Doctor within one invocation; recommended refine-002 while current remained postmr; preservation checks passed. |
| Full-auto campaign | EA, DiU, Q5cm and QiC all SOLVED numerically. EA retained MR_REVIEW/TFZ 7.60; DiU supplied anomalous observations and HL phases; QiC provisionally selected refine-002 without user approval. |
| P2 preferred components | `dec56c2` published after 276 focused / 927 full tests; DP resource and conversions implemented. Native conversion/DP check pending. |
| Prepared nonstandard/mixed campaigns | Implemented and fixture-tested, including relocation; small real geometry-diverse check remains P5. |
| Scout | Backend primitives exist; not yet the ordinary runtime registration/decision path. |

Older 694/735/771/785/851/878 test totals are historical, not the current P2
baseline. Do not rerun an unchanged full suite solely for documentation changes.

## Fresh GZ11 result and immediate next action

Guarded root: `~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`.
On `66cb7a2`, fresh GZ11 attempt_002 / `GZ11/AutoMR/run_002` reached SOLVED
at `refine-001`. Simon opened its matching refined model/maps in Coot and,
asked to inspect DG A:12 / DZ B:4 and adjoining backbone, reported a passed
local visual check: "It's a perfect speckled sheep." No repeated run or
repeated visual confirmation is needed for that check.

Read remaining exact identity/force/effective-bundle and geometry evidence from
the saved outputs. Do not invent numerical values or treat a stage name alone
as proof AutoSol ran rather than skipped. This successful campaign run is not
the earlier blocked standalone `examples/TestSets/GZ11/AutoMR/run_002`, the
failed temporary DZ-provider MR_snapshot, or manual Refine_74. Preserve them.

**Immediate next live work is P2**, using a bounded new preparation/refinement
check with explicit source components and recorded provenance. First identify
suitable local source inputs; distinguish genuine source components from any
synthetic exercise. Do not relabel the successful GZ11 model and call that
independent DP validation, overwrite old outputs, or claim the already-passed
DZ workflow proves the new conversion path. Current P2 native evidence is absent.

## Nine-member baseline results

The old guarded plan and attempts remain historical evidence, all last reported
with integrity OK. Its initial failures were isolated rather than blocking the
whole campaign. Later full-auto results belong to a NEW root:
`~/NASolve-live-tests/full-auto-984f75d-kaxrtv9w`.

| Member(s) | Preserved evidence |
| --- | --- |
| DOHU, DT, ED, FA | Guarded run_001/refine-001 SOLVED numerically; inspection separate. ED retains w-metal-scaffold. |
| GZ11 | Guarded run_002/refine-001 SOLVED; requested user visual check passed. |
| DiU | Guarded history stopped on the prime-stripping lookup bug; new full-auto run_001/refine-001 SOLVED, 0.2072/0.2202. |
| EA | Guarded MR review at TFZ 7.60; new full-auto run_001/refine-001 SOLVED, 0.1603/0.1776, retaining the warning. |
| Q5cm | Guarded history lacked 5CM.cif; new full-auto run_001/refine-001 SOLVED, 0.2094/0.2304. |
| QiC | Guarded run_002 recommended refine-002 with postmr current. New full-auto run_001 provisionally selected refine-002, 0.1500/0.1502, ML-fixed-scattering, no experimental phases. |

Full-auto preservation checks passed for the old state, new frozen plan and
code head. Numerical outcomes are not structural approval. User-veto/resume
still needs its recorded live exercise; rejected-AutoSol fallback was not
exercised by these successful/skipped gates. Do not manufacture a failure or
repeat the whole cohort just to make a scenario occur. Campaign exit 3 can
reflect retained warnings/other members, so do not accidentally suppress a
selected retry with an unconditional retry && run chain.

## Pine close-out

Keep the existing gates finite. Code and test completion are not native
validation, and native numerical success is not model/map approval.

| Gate | Remaining completion evidence |
| --- | --- |
| **P1 — Effective dictionary compatibility** | Published, regression-tested and used in ordinary GZ11; finish exact effective-bundle review alongside P3. |
| **P2 — Specific component normalization** | Implementation/full regression/publication passed at dec56c2. Native alias preparation and DP refinement; confirm raw preservation, target definitions, atom correspondence and conversion provenance. |
| **P3 — Normal GZ11 live path** | Ordinary execution and requested user visual check passed. Finish saved receipt/numerical evidence; no repeated execution or visual check. |
| **P4 — Nine-member TestSets campaign** | Member isolation, guarded Doctor and fresh four-member full-auto behaviors demonstrated. Finish bounded inspection/resume/user-veto/current-pointer evidence without demanding every scientific outcome be green. |
| **P5 — Prepared-nonstandard live campaign** | Existing small 3-5-member real prepared-PDB/exact-sequence geometry-diverse check with native engines and ownership/review checks. W-only/fixture evidence is not a substitute. |
| **P6 — Final candidate regression/review** | Exact final code/test commands/results/tool versions, diff/available CI review and consistent docs. P2's 927+224 is the current returned full-suite baseline; new code changes require their relevant regression. |
| **P7 — Merge and retire branches** | After P1-P6, merge PR #23, verify ancestry/local worktrees/commits, switch/pull main and retire merged Pine/Oak references without force or data cleanup. |

GUI/Design implementation, Scout promotion, Topo Net/Surgeon, donor rescue,
new providers, generic MTZ/SCA import, recipe builders and a universal chemistry
library are not additional Pine merge prerequisites.

## After Pine: blind AlphaFold geometry campaign, then Scout

Simon requested this order on 2026-10-07. He has diffraction datasets, predicted
PDBs and sequences but does not know the experimental answers. No study files
or prediction variants have been inspected/selected here.

Start with the [prepared nonstandard route](campaign-planning.md#prepared-nonstandard-providers):
explicit dataset-local PDB, complete chain-labelled target and normal frozen
reflection inputs. Scout is unnecessary when actual chain/residue correspondence
is usable. Check it rather than assuming it from AlphaFold's name. Registration,
recuts or extra copies merit a specific limitation, not a blanket Scout gate.
Correct sequence is not evidence of crystal geometry or ASU composition.

Inspect format/conversion, chain IDs, numbering, polymer identity, completeness,
confidence-versus-B-field meaning and current AutoPROC/STARANISO/Free-R input
requirements. Preserve raw prediction/confidence files and record preparation
as derivatives. Do not blindly apply protein-specific pLDDT trimming to DNA.
Freeze the first candidate set and recipe before viewing outcomes; retain all
successes/reviews/failures. No solved answer models or outcome-driven candidate
selection enter the blind baseline. Later hypotheses get new attempts.

This larger post-Pine study does not enlarge Pine or silently waive the existing
small P5 smoke check. Numerical success is not independent truth validation;
inspect density and geometry. No new AlphaFold runtime adapter is claimed.

<a id="after-pine-operational-scout"></a>
### Operational Scout follows the blind baseline

The [registration contract](construct-registration.md),
[registration intent](construct-registration-intent.json) and
[live-check queue](construct-registration-live-checks.md) remain authoritative.
Prioritize ordinary CLI/AutoMR preflight, persisted evidence and PostMR logical
site handoff without waiting for GUI or the metal editor. Keep proposals,
accepted mappings and coordinate edits distinct; preserve provider-bound
zero-unexplained uniqueness and ordinary/renamed/ambiguous live checks.
Reprioritization does not grant Scout runtime authority.

## Working and documentation discipline

One coherent slice and one sequential ferry, then the first meaningful outcome.
Missing optional NASolve annotations should not veto supported library-backed
chemistry. Necessary integrity/required-operation stops remain dataset-local.
Retain explicit known-component corrections, not arbitrary chemistry guessing.

Keep current status here, policy in subsystem docs, archaeology in history and
PR #23 as the review tracker. Docs-only updates must not promote unseen native
validation. Preserve models, dictionaries, observations/Free-R, maps, attempts
and unrelated untracked files/environments/patches. Do not reset, stash, clean or
upload those scientific artifacts as part of a code/documentation ferry.

## Doctor-transition patch validation

Historical patch d3e1fa3 passed 148 campaign tests + 85 subtests and 785 full
tests + 224 subtests. The guarded native QiC result and preservation evidence
are recorded above and in the [full-auto checkpoint](full-auto-patch-handoff.md).
It is not pending recovery. The old detailed handoff remains available in Git
at dec56c2; the [history index](history/README.md) owns earlier experiments.
