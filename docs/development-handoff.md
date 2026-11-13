# NASolve development handoff — current state

Updated **2026-11-13**, C260 implementation/validation complete, commit pending.
Active **cedar**, checkout NASolve-c96. Simon authorized this pass through
**23:00 Europe/London**, focused tests only. No merge authorized. Finish Q04/Q05
before Q06. The [queue](cif-doctor-completion-queue.md) owns ordering; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.

## Latest completed step — ordinary preparation uses safe storage

C260 connects C258 retirement after a new checked result is published, before a
campaign freezes its files. It reuses the same archive, owner, public-path and
chemistry checks. Optional storage failure keeps a result available only after an
exact reread proves it still usable. Chemical/publication failures and interrupts
remain visible. No native retry or unchecked fallback.

Campaign capture uses existing archive transport checks to exclude only archived
working duplicates. The archive, binding, original records and public scientific
files remain artifacts. Later explicit completion of partial cleanup does not
invalidate them. Inspection, historical publication and alternatives do not clean
files. Older unarchived campaign receipts still naming working files need a separate
migration; do not silently retire those paths. Failed/uncertain work and shared
inputs/acquisitions stay unpacked. No new schema; existing storage records require
a current reader. No change to chemistry, source priority or checkpoint selection.

Changed: cif_ordinary_postmr.py, cif_attempt_retention.py, campaign_stages.py and
11 new focused cases in test_cif_preparation_retention.py. Before/after behavior,
exact commands/hashes and limits are in ledger `ordinary_campaign_retention_2026_11_13`.

- Final ordinary/campaign/cleanup checks: **92 passed, 29.54 s**. A broader
  **125 passed, 25.93 s** preceded the final campaign artifact filter.
- Moved temporary checkout and request, original temporary paths absent:
  **1 passed, 13.48 s** (14.38 s whole runner).
- Actual C244 evidence copy: interrupt ordinary cleanup after **17** removals,
  retain usable result, freeze **97** campaign artifact references excluding
  **604** disposable paths, relocate, resume, verify every reference and exact result.
  Same model/five PHILs/two CIFs/**51** stable paths. Whole request **33,661,526 B /
  98 files**, versus **181,566,343 B / 698 files**. All original bytes/times unchanged.
  Expanded archive peak **87,440,990 B** (128 MiB bound), Python resident peak
  **756,350,976 B**, whole multi-read probe **517.56 s**. No native execution.
  Temporary copy removed. 100 identical requests would retain **3,366,152,600 B**;
  this is arithmetic, not a 100-dataset execution or a bound for other chemistry.

No jobs remain. Runners/summaries are ignored `branch-artifacts/cedar/runners/c260_*`
in the everyday checkout. Generated science is excluded from Git. Last full suite:
**C220/583d30df, 9,178 tests + 276 subtests**; no full suite this pass.

## C259 native acceptance boundary — preserve before continuing

C259 is pushed as `cd744e2`. Fresh Phaser passed (MR_SUCCESS, TFZ 17.10) and Coot
constructed the declared fixture, but curated 1AP acquisition stopped at an ideal-only
seed requirement. The CIF has source-declared x/y/z. No checked checkpoint, ReadySet,
AutoSol or diffraction refinement was reached. Driver confirms stopped ownership
and unchanged C258 code. All partial outputs preserved:
`/Users/svecchio/NASolve-live-tests/259_Cedar_selected-autosol-wxv04px_`.
Exact hashes/tool versions are in `native_selected_autosol_control_2026_11_13`.

Raw DiU first reproduced the known C188/C189 B:1 phosphate refusal. The fresh
software fixture used explicit free ends A:1/B:1/C:8, preserving D:1 phosphate
records exactly. This does not infer DiU terminal chemistry. All donor inputs remain.

Prior work for the next step: C30/C31 graph-source/CCD reader adapters explicitly
record source-declared coordinates as NOT independent ideal coordinates; C54 owns
source-preserving native generation. Read-only reassessment shows original 1AP
cannot simply be accepted as its own qualified numerical candidate (plane/angle
compatibility findings), while 5IU is graph-only and needs numerical generation.
Do not bypass these gates, relabel coordinates silently, substitute fitted-model
positions, or change source chemistry. A bounded control using those existing
adapters should establish the right integration route before changing production.

## Next — Q04/Q05 closure

1. Finish committing/pushing C260; review the retained historical-campaign boundary
   and representative resource scope. Do not rebuild storage machinery.
2. Test the existing declared-source/reader adapters for the C259 acquisition gap,
   preserving exact original sources and complete generation/qualification evidence.
   Then qualify C253 chosen-model AutoSol natively from a fresh owned request.
   Interrupted AutoSol result publication remains separate: outputs are preserved,
   not automatically adopted. No synthetic reflection fixture as phasing evidence.
3. Reconcile supported opt-in Q04/Q05 closure; Q06 actual complete-restraint
   diffraction refinement, then Q07 combined/held-out cases. Q08–Q14 retain the
   prior chemistry learning. Q15 report/PDF, Q16 final AutoPhase naming, full suite,
   integration review and an explicitly authorized merge. No merge authorized now.

Earlier same-day checkpoints C253–C258 remain in immutable commits and the ledger,
not repeated here. Linden works independently on Willow/Pine; named-proxy helper
advice was shared locally, signed Rowan. Their three short stricter-backbone
captures finished; no Cedar edits or competing geometry subsystem. Protected
NASolve-cedar and everyday NASolve/pine science, patches and environments are untouched.
Continue on NASolve-c96/cedar; no new branch.
