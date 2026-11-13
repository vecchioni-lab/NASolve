# NASolve development handoff — current state

Updated **2026-11-13**, C260 pushed as `ef2805c`; C261 diagnostics complete,
documentation checkpoint pending. Active **cedar**, checkout NASolve-c96.
Simon authorized this pass through **23:00 Europe/London**, focused tests only,
no full suite or merge. Finish Q04/Q05 before Q06. The
[queue](cif-doctor-completion-queue.md) owns ordering; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.

## Latest result — original-source 1AP and 5IU qualification

C259 fresh Phaser/Coot passed but ordinary acquisition stopped at 1AP's source
x/y/z versus the generator's ideal-only seed. C261 reuses C30 target-free graph,
C37 source-reader dialect/charge handling and C118 explicit neutral-purine
representation permission. Both curated components now pass existing isolated
qualification against their exact originals. No production routing change yet.

1AP required a diagnostic complete-bond-row permutation: installed eLBOW's
SetPhosphatesOrder makes the first terminal P–O double even if another P=O exists.
Presenting the source-declared double first avoids the unwanted OP1–P change.
All declared bonds, H/charges, coordinates and fixed stereo stay unchanged. A
prior candidate with two P=O bonds was correctly rejected. CCD unknown-stereo
failures and insufficient connected-atom ordering are preserved, not retried in
place. No invented stereo, phosphate state or fitted-model seed; no installed edits.

All six C261 controls are stopped and code-pinned to ef2805c. Phenix 2.2.1-6174,
complete bounded generation and isolated source/candidate-seed checks. No ReadySet,
AutoSol, diffraction refinement, adoption or full suite. Exact outcomes/hashes and
negative controls: ledger `declared_source_generation_controls_2026_11_13`.
Local final control: `261_Cedar_declared-bond-order-generation-1jjl2ssv` under
NASolve-live-tests; ignored runners in everyday checkout branch-artifacts/cedar/runners.
Original sources retain bytes/timestamps. Raw science excluded from Git.

## Next — Q04/Q05 closure

1. Implement the small graph-based bond-row input adapter with focused preservation,
   refusal and portability tests. Read C261/native source evidence; do not duplicate
   C30/C37/C118 or weaken chemistry gates.
2. Bind explicit source/reader preparation into the existing owned acquisition,
   retaining original source authority plus derived-input/recipe identity. Qualification
   must still compare with the original. Avoid a new executor or untracked retry.
3. Retry C253 chosen-model AutoSol native acceptance from a fresh owned request.
   C259 explicit terminal fixture preserved D:1 phosphate; it does not infer DiU
   chemistry. Interrupted AutoSol result publication remains preserved/unadopted.
4. Reconcile supported opt-in Q04/Q05 closure, then Q06 real complete-restraint
   refinement and Q07 combined/held-out cases. Retain Q08–Q14 chemistry learning;
   Q15 reporting/PDF and Q16 final AutoPhase naming/full validation/integration review.

## Completed foundations — reuse, do not rebuild

C260 ordinary checked publication invokes existing C258 successful-working-file
retirement. Optional storage failure returns usable science only after exact reread.
Campaign capture excludes transport-verified archived duplicates; later partial
cleanup completion preserves its references. Read-only inspection and historical
publication never clean files. Older unarchived campaigns that still reference
working files require a separate migration. Failed/uncertain work stays unpacked.

Final C260 checks: 92 passed; moved checkout/request: 1 passed. Actual C244 copy:
604 duplicates removed after deliberate interruption/resume, 97 campaign references
survive relocation, same model/five PHILs/two CIFs/51 public paths. Whole request
181.6 MB → 33.7 MB; temporary expansion 87.4 MB, Python resident peak 756.4 MB.
Original 698 files/timestamps unchanged; temporary validation copy removed.
Exact commands/results: `ordinary_campaign_retention_2026_11_13`. This is one
representative request, not a 100-dataset or concurrent-memory guarantee.
Last full suite remains **C220/583d30df: 9,178 tests + 276 subtests**.

Linden works independently on Willow/Pine. Named-proxy advice and the distinction
between native symmetry capture and restraint-authoring interfaces were shared
locally, signed Rowan. No Cedar edits requested. Protected NASolve-cedar and everyday
NASolve/pine science/patches/environments remain untouched; no new branch.
