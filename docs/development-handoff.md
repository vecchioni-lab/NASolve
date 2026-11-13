# NASolve development handoff — current state

Updated **2026-11-13**, C257. Active **cedar**, checkout NASolve-c96.
The [queue](cif-doctor-completion-queue.md) owns work order; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.
Simon authorized this pass through **23:00 Europe/London**, focused tests only.

## Latest completed step — ordinary reads of archived attempts

C256 is committed/pushed as `ebc9ccf`. Prior work checked: C228/C229 exact archive
storage and frozen request choices, C237/C238 owner partitions, C252 normal
alternative publication, C254 bounded outer views and C256 complete-attempt
transport. Those mechanisms are reused, not replaced. The remaining gap is
ordinary history/result reading with stable public paths, then safe retirement.

C257 adds an explicit archive-preparation API under the existing request lock.
It replays the original complete owner, verifies every returned path, and publishes
an immutable storage receipt beside the attempt. Original request, attempt and
finished records remain unchanged. Normal history and exact-result readers
reconstruct archived working evidence but return persistent model/CIF/PHIL paths.
The prepared bundle, repair runtime, continuation runtime and parent runtime stay
intact. Every selected owner is still rechecked; all historical attempts validate.

A complete unpublished archive can be recovered without repacking. Partial
archives are preserved and refused by the explicit storage operation; they do not
change ordinary reads. Unsupported legacy layouts, changed owners/archives/public
files, extra files and symlinks refuse. No product source-deletion operation yet.
The explicit storage receipt is a new compatibility boundary: older readers reject
the retention folder. Requests without it preserve their previous behavior.

**22 new checks pass** (19 in 126.09 s, three late-corruption/legacy controls
in 26.35 s); **255 affected owner/continuation/publication checks pass in 406.35 s**.
Actual C244 copy acceptance passes: 181,566,343 B / 698 source files become
33,660,939 B / 96 retained files; same model, five PHILs/two CIFs, 51 returned
persistent paths. Original-request reads/native execution forbidden; all original
bytes/timestamps unchanged. The copy and temporary views are removed. Archive
expansion peak 87,440,990 B (128 MiB limit), Python peak 748,552,192 B; archive
preparation plus ordinary exact read 322.80 s. A moved temporary checkout also passes the targeted relocation/fresh-attempt
control (15.71 s), with its old checkout and request paths absent. No native
process remains running.

Only the new throwaway copy had 604 working files manually removed for acceptance;
product deletion is not yet implemented. Exact commands, source/test hashes and
local runner/summary references: `ordinary_attempt_archive_2026_11_13` in the ledger.
Code changes: new `cif_attempt_retention.py`, complete-request history/exact-read
integration, new focused regression. New storage receipt schema only; no request,
scientific-result, checkpoint or chemistry migration. Generated science/runners
are deliberately excluded from Git.

## Other completed work this pass

- **C253 / f337660:** AutoSol compares sites against the chosen checkpoint's
  coordinates and cell, while native phasing still uses the original Phaser model.
  Immutable chosen-reference/result checks, guarded schema-5 publication, exact
  Coot inspection and unchanged distance gates. 196 tests + 31 subtests and
  53 adjacent tests + 2 subtests pass. Native selected-reference acceptance remains.
- **C254 / 39c5ae0:** one outer working view shares the existing 128 MiB physical
  archive allowance with two runtime layers; actual continuation replay passes.
- **C255 / aef7911:** reuse Alder's exact HL-label discovery correction, with
  89 tests + 15 subtests and a real Phenix MTZ-header read. No phasing rerun.
- **C256 / ebc9ccf:** whole-attempt archive preserves existing v2 partitions,
  original finished checksum and inventory. 61 storage tests; actual C244 replay
  passes from 15.5 MB compressed / 180.0 MB logical, with 87.4 MB expanded archive
  peak and 740.1 MB Python peak. All original files unchanged. Exact details and
  commands remain in the existing evidence ledger and those immutable commits.

## Next — Q04/Q05 closure

1. C257 ordinary-reader/native-copy acceptance is complete. Next add a durable,
   known-stopped retirement transaction: archive binding before deletion,
   preserve public files and every failed/active output, recover interruption and
   repetition without native retry or changed selection. Measure whole-request
   disk, temporary expansion and memory; validate representative campaign behavior.
2. Qualify the C253 selected-model AutoSol route natively. Interrupted AutoSol
   result saving retains outputs without automatic adoption; keep that separate
   from existing preparation-publication recovery. Reconcile earlier evidence
   rather than duplicating preparation, alternative or campaign machinery.
3. Q06 actual complete-restraint diffraction refinement, then Q07 combined and
   held-out examples. Q08–Q14 retain earlier chemistry learning. The queue's
   supported Q04/Q05 estimate remains roughly 2–5 implementation patches plus
   native/integration validation; prerequisites are not automatic closure.
4. Q16 includes the final AutoPhase naming change under the pinned audit, full
   regression, integration review and honest release scope. No merge authorized.

No full suite this pass. Last wholly green full: **C220/583d30df, 9,178 tests +
276 subtests**. Full integration validation remains required before merge.
Phenix evidence uses **2.2.1-6174 / dispatcher 2.2.1**. C252 preparation observations/
maps are synthetic fixtures; neither C252 nor archive reads prove diffraction
refinement. Scientific data/runners remain local, excluded from Git.

Linden works on Willow/Pine TopoStitch; no cross-branch edits. Protected
NASolve-cedar and everyday NASolve/pine science, patches and environments remain
untouched. Continue on NASolve-c96/cedar; no new branch. Keep this handoff short;
use the existing ledger and immutable history for prior milestone details.
