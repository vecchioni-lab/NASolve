# NASolve development handoff — current state

Updated **2026-11-13**, C251. Active **cedar**, checkout NASolve-c96.
Base C250/92efb7d (pushed); current HEAD supplies final identity. The
[queue](cif-doctor-completion-queue.md) owns work order and the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

C251 saves a later checked attempt explicitly with
`cif-doctor publish-preparation RUN --attempt N --as-alternative`.
It creates an unselected REVIEW `prepare-NNN` checkpoint from the same frozen
construction. It never claims coordinate descent from a selected refined model.
Original root, run report, preparation receipt and current selection stay fixed.
Coot/refinement consume the exact alternative model and ordered restraints; the
inherited map is labelled as not recalculated for the prepared alternative.

New alternative receipts use schema 4; old readers refuse. Initial-only schema 3
and legacy schema 1/2 retain their meanings. Immutable receipt first, C250 guarded
registry append second. Repeating publication preserves intervening selection/
bookmarks and reuses the same receipt. Root plus named alternatives share one
complete-history replay, without persistent verdicts or duplicate scientific files.
Checked observation reads now use their already-sealed anchor and original checksum,
so a renamed dataset needs no rewritten history or basename search.

Scientific correction from the AutoSol audit: it deliberately phases with the
**original Phaser MR model**, then validates heavy-atom sites against the prepared
model. Its validation reference is still the initial preparation. C251 refuses a
schema-4 non-root selection rather than silently comparing against the wrong
reference. The next Q05 connection must preserve the original phasing input and
acceptance thresholds while binding the exact selected validation reference.

## Validation and reviewer handoff

Source: complete/ordinary result readers, preparation publication, checkpoint
registry/observation resolution, CLI, Coot map resolver and AutoSol input guard.
Existing test modules extended; no new test module, native worker or science
artifact. New schema only on explicit alternative publication. No legacy migration.

Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- Before implementation: **12 expected failures** in alternative regressions.
- Initial integration exposed unsupported Coot checkpoint kind, then a renamed-
  dataset observation-anchor gap. Both are fixed and covered.
- Final six consumer modules: **166 passed + 20 subtests**, 7.55 s.
- Complete-request ownership, ordinary CLI, refinement and campaign callers:
  **244 passed + 26 subtests**, 305.34 s.
- Final strict identity/repeat/schema controls: **67 passed**, 5.52 s.
- Final AutoSol registry pin/diagnostic: **31 passed + 2 subtests**, 5.80 s.
- Actual retained C244 Phenix 2.2.1-6174 / dispatcher 2.2.1 proof: both controls
  pass through the shared reader, each attempt replayed once. **698/506 files
  unchanged**; exact selection and five ordered PHIL files retained. Times
  105.66/89.56 s; process peak **660,389,888 B**. Source files unchanged during read.

Exact commands/hashes/scope: ledger `preparation_alternatives_2026_11_13`.
The native-proof read uses a location-only adapter; it is not native alternative
publication, fresh construction or diffraction refinement. Other consumer checks
use synthetic transport/refinement executables. No new Phenix/Coot run or full
suite. Last wholly green full: C220/583d30df, **9,178 tests + 276 subtests**.
All tests/readback jobs are finished; no native process is active.

## Next work — Q04/Q05 closure

1. Finish binding the selected prepared validation reference through AutoSol's
   anomalous-site check and saved provenance, preserving original-MR phasing.
   Verify remaining native/ordinary caller acceptance for later alternatives.
   Campaign retries still create new runs; no old stage receipt is rewritten.
2. Finish remaining Q04 recovery and campaign-scale storage acceptance. Existing
   prelaunch, no-PID interruption, deadline-before-launch and unknown-descendant
   controls already exist (C156/C170); do not build a second process owner.
3. Define known-stopped, interruption-safe retirement of redundant successful
   working files. Retain reproducible inputs/proof; measure whole-request,
   temporary expansion and memory after relocation. No blind cleanup/verdict cache.

C249 scoped explicit selected-CIF coverage and C250 stale-writer protection are
pushed. Neither selected plane membership nor test transport qualifies diffraction
refinement. Q06 real complete-restraint refinement and Q07 mixed/held-out controls
follow the supported Q04/Q05 checkpoint.

Linden is independently building read-only coordinate-end proposals on Willow
(`topostitch_coordinates.py`); no shared checkpoint/CLI edits. Later adoption needs
an explicit interface integration. Local coordination is authorized.
AutoPhase naming stays the **final Q16 implementation task**; preserve the
[commit-pinned audit](autophase-rename-plan.json), native AutoSol calls and saved
identities, plus Alder phase-label/Cedar preparation validation differences.

## Preserve local evidence

Protected NASolve-cedar remains e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains science, patches, environments and Linden snapshots.
Work only in NASolve-c96/cedar; no new branch or merge. Local readback runner is
`branch-artifacts/cedar/runners/c251_shared_history_read.py` in the everyday checkout.
No retained scientific files were copied into Git or retired.
