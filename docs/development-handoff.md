# NASolve development handoff — current state

Updated **2026-11-13**, C269 protected-phosphate name integration, based on
C268 `35ad05a`. Active **cedar**, NASolve-c96. Simon authorized work through
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

## Next — finish the actual chosen-model handoff

1. Use a fresh owned C270 run derived from ignored c267 worker/driver. It uses real
   DiU observations with an explicitly declared A:5IU software-control pair,
   free ends A:1/B:1/C:8 and protected D:1 phosphate. This is not donor chemistry.
   Keep C263's source-input recipe and C118's explicit aromatic permission.
2. Verify checked preparation, original-Phaser AutoSol input, chosen-model site
   comparison, exact phase labels, later-selection preservation and relocated
   inspection. C267 stopped before ReadySet/AutoSol; do not claim their success.
3. Reconcile opt-in Q04/Q05 acceptance/resource limits. Interrupted AutoSol result
   publication is preserved but not automatically adopted; its recovery remains
   a separate ownership problem. Then Q06 real complete-restraint refinement,
   Q07 combined/held-out chemistry, retained Q08–Q14 chemistry learning, Q15 report,
   and Q16 AutoPhase compatibility naming plus integration validation/review.

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
