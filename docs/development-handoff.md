# NASolve development handoff — current state

Updated **2026-11-13**, C271 AutoSol view identity fix; native C270 ran at
C269 `f2345a8`. Active **cedar**, NASolve-c96. Simon authorized work through
**00:00 Europe/London, 14 November**, focused tests only; no full suite or merge.
Finish Q04/Q05 before Q06. The [queue](cif-doctor-completion-queue.md) owns ordering.

## Current checkpoint — preserve the phosphate Phenix actually read

C266 carries explicit ordinary permission for protected background terminal
phosphates into native checks. C267 then exposes a naming mismatch: Phenix p5*END
binds coordinate OP3 to native O3T. The chemical definitions are unchanged.
C268 qualifies combined full-model energy/name observation on 853 real atoms;
energies, gradients, geometry and definitions exactly match the prior capture.
Its first driver had a post-completion analysis assertion error; the stopped
failure is preserved and separate no-launch relocated readback passes.

C269 uses these observed bindings under explicit native context v4, retaining
complete before/after definition/name equality, terminal graph and all existing
source/link/proxy checks. It also preserves the names in existing numerical and
plane-attribution reconstruction. No native kernel, mathematical worker, chemical
state or coordinates change. Old v1/v2/v3 reads retain their original meanings;
new requests require a current reader. No alias whitelist or automatic adoption.
Focused validation: **327 passed**, then **298 affected-consumer checks passed**;
one additional stopped-failure binding test and three moved-checkout checks pass.
A no-launch read of 853-atom native evidence also passes; all 432 inspected files
keep their bytes/timestamps. Exact commands and scopes are recorded in ledger
`retained_phosphate_observed_names_2026_11_13`; fresh native acceptance follows.

## Saved C270 result — finish diagnostic readback, not native work

Live-tests root `270_Cedar_selected-autosol-pspkne9n` contains actual successful
preparation and AutoSol on `f2345a8`: `POSTMR_READY`, `AUTOSOL_READY`, 1.449 Å site
match and HLAM/HLBM/HLCM/HLDM phases. Original/repaired derivatives, plane repair
and ReadySet/native endpoint pass. Automatic retirement leaves the whole request
at 35,122,742 B / 168 files, with seven public restraints and OP3 only at D:1.
This is an explicit A:5IU/free-end software fixture, not donor chemistry.

Two diagnostic failures are preserved, with all processes stopped and source
unchanged. The first driver used nonexistent `CheckpointRecord.model_path` after
native completion; its reusable ignored template now uses `model`. The fresh
`followthrough-001` successfully changed current selection to postmr, then exposed
that the correct AutoSol model's view omitted its checkpoint ID. C271 fills that
existing field with the safe saved ID and binds the GUI launch record/workspace.
Validation: 68 tests + 23 subtests; two moved-checkout checks. No native rerun.

Next use fresh owned `followthrough-002` on this saved result. Current selection
is already postmr; verify AutoSol still opens manual-001, then relocate and perform
guarded cold inspection/profile. Preserve both earlier failures and their workers.
Read the followthrough's own active/process/progress/result records before any
further action. Keep source fixed while it runs. Native launches must be forbidden.
Original input checksums remain verifiable; pre-native source timestamps were not
persisted by the first failed driver. Do not invent that comparison; subsequent
readback records its own before/after timestamps.

## Next — reconcile Q04/Q05 acceptance

Finish this exact saved-result control. Then assess the documented storage,
read-cost and opt-in rollout scope. Interrupted AutoSol result publication remains
preserved but not automatically adopted; do not hide that ownership boundary.
Q06 actual complete-restraint refinement follows Q04/Q05 scope reconciliation;
Q07 combined/held-out chemistry and Q08–Q14 retained chemistry learning remain.
Q15 report and Q16 AutoPhase compatibility naming/full integration review follow.
No new ownership system, full suite, merge or native repeat is authorized by a
post-processing test-driver typo.

## Completed foundations and boundaries — reuse

- C263's explicit source-reader recipe reuses source graph export, reader
  preservation and whole-bond-row ordering. Original-source 1AP/5IU isolated
  native acquisitions and relocated reads pass. Raw 1AP generation still reports
  its historical in-memory issues; independent written-CIF qualification passes.
  Do not relabel that raw verdict. C265 correctly refuses charged 1AP OP3 under
  the neutral-hydroxyl linking operation; generalized charge-aware linking is Q13.
- C252 validates native preparation alternatives, relocated Coot/refinement-input
  reads and manual-choice preservation. C253 implements chosen-model AutoSol
  reference without replacing original MR phasing; live acceptance remains above.
- C260 connects existing successful-working retirement to new ordinary/campaign
  publication. Actual C244 copy: 181.6 MB → 33.7 MB, same public model/five PHILs/two
  CIFs/51 paths. Optional cleanup failure requires exact usable-result reread.
  Failed/uncertain work/shared acquisitions remain unpacked. Old unarchived
  campaign references need separate migration. One expensive reader at a time
  until concurrency is measured; do not rebuild storage machinery.

Exact commands, hashes, ownership and historical evidence live in
`cif-linked-native-registration-evidence.json`. Raw science and ignored cNNN
runners remain local. Last full suite: **C220/583d30df, 9,178 tests + 276 subtests**.
Linden works on Willow/Pine; shared parallelity correction was identified to avoid
repeating it. No qualified selective-coordinate adapter exists in Cedar.
Everyday NASolve/pine and protected NASolve-cedar data/environments remain untouched.
No new branch. Signed handoffs between agents: **— Rowan**.
