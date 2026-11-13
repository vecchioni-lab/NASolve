# NASolve development handoff — current state

Updated **2026-11-13**, C262 pushed as `668668a`; C263 implementation and focused/
native validation complete, publication pending. Active **cedar**, NASolve-c96.
Simon authorized work through **23:00 Europe/London**, no full suite or merge.
Finish Q04/Q05 before Q06. The [queue](cif-doctor-completion-queue.md) owns ordering.

## Latest result — original chemistry survives native input preparation

C263 adds the explicit `cif-source-reader-preparation-v1` recipe. It composes
C30 graph export, C37 reader preservation and C262 complete bond-row ordering
inside the existing generation owner. Original source/authority remain the cache
and qualification basis; separate derived files and actual reader dialect are
bound and rederived on read. Coordinate origin remains explicit. Ordinary intake,
resume, acquisition and plane-support reads retain that choice. Old recipes and
CLI defaults are unchanged; new prepared-input requests need a current reader.

Fresh original-source 1AP and 5IU acquisitions pass isolated native qualification
and relocated read, with original/cache/SDK reads and native launch forbidden.
Phenix 2.2.1-6174, 45.03 seconds whole control, 82.6 MB Python peak. Requests retain
5,056,121 B/82 files and 3,699,998 B/82 files respectively. Original source bytes/
timestamps unchanged. Local root: `263_Cedar_original-source-acquisition-vk0kfckx`;
all jobs stopped, pinned source unchanged. Ignored c263_* runners in everyday checkout.

Keep the scientific distinction: raw 1AP generation remains REJECTED for partial
in-memory purine aromatic representation and legacy unsigned phosphate `both`
omission. The written candidate passes existing original-source reassessment and
independent native qualification. Do not relabel that raw verdict or weaken gates.
C262 fixed the observed unwanted extra P=O by reordering entire source bond rows;
no bonds, charge/H, stereo or coordinates are changed. Native code is untouched.

Focused validation: 333 existing/new checks passed in the first group; four
new tamper-fixture setup errors were corrected. Final targeted group **57 passed**;
ordinary intake/resume/complete owner **159 passed**. Relocated temporary checkout
and request, old temporary paths absent: **1 passed**. Exact commands, hashes and
limits: ledger `original_source_owned_acquisition_2026_11_13`. No full suite.

## Next — finish Q04/Q05 acceptance

1. Publish C263, then retry the real-observation chosen-model AutoSol control in a
   fresh owned run. Reuse ignored c259 worker/driver with C263 explicit input policy
   and C118 neutral-purine permission. C259's software fixture declares free ends
   A:1/B:1/C:8 while preserving D:1 phosphate; it does not infer DiU chemistry.
2. Verify original-Phaser phasing versus chosen-model site comparison, exact phase
   labels, later-selection preservation and relocated inspection. No synthetic
   reflection substitute. Interrupted AutoSol publication remains preserved but
   not automatically adopted; keep this separate remaining recovery boundary.
3. Reconcile opt-in Q04/Q05 scope and default-route rollout; then Q06 real
   complete-restraint refinement and Q07 combined/held-out chemical controls.
   Q08–Q14 retain chemistry learning; Q15 report/PDF; Q16 final AutoPhase naming,
   full regression and reviewed integration. No merge authorized.

## Completed foundations — reuse

C260 connects existing C258 retirement after new checked publication and before
campaign capture. Optional cleanup failure returns science only after exact reread.
Partial cleanup can finish without breaking new campaign artifact references.
Inspection and historical publication never clean files. Old unarchived campaigns
still referencing working files require separate migration. Failed/uncertain work
and shared acquisitions remain unpacked. Actual C244 copy: 181.6 MB → 33.7 MB,
same model/five PHILs/two CIFs/51 public paths; all original science unchanged.
See `ordinary_campaign_retention_2026_11_13`; do not rebuild storage machinery.
Last full suite **C220/583d30df: 9,178 tests + 276 subtests**.

Linden works independently on Willow/Pine. Existing Cedar parallelity audit and
plane-order correction were pointed out to avoid duplicated Cartesian diagnosis;
new symmetry pullback/closure work remains their separate diagnostic scope.
Protected NASolve-cedar and everyday NASolve/pine data/patches/environments remain
untouched. Continue on NASolve-c96/cedar, no new branch.
