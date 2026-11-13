# NASolve development handoff — current state

Updated **2026-11-13**, C256. Active **cedar**, checkout NASolve-c96.
The [queue](cif-doctor-completion-queue.md) owns work order; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.
Simon authorized this pass through **23:00 Europe/London**, focused tests only.

## Latest completed step — C256 complete-attempt archive read

C255 is committed/pushed as `aef7911`. C256 reuses the existing v2 owner partitions
in an explicit complete-attempt archive. Every partition retains its logical bound;
one object store/root view retains the unchanged physical allowance. The original
finished-file checksum and sealed inventory are checked before exposing paths.
Changed source/foreign seal/rehashed logical substitutions refuse. Archive bytes
are synced, existing destinations never overwritten, and no source file is removed.

**61 focused storage tests pass, 29.69 s.** The actual complete C244 attempt also
passes its existing owner/chemistry/result validator from a **15,518,933 B** archive
of **179,979,354 B / 659 files**. Original-attempt reads/native launch forbidden;
shared request/acquisition inputs remain original. Same model, five PHILs/two CIFs;
peak archive expansion **87,440,990 B / 134,217,728 B**, Python peak **740,114,432 B**,
**102.09 s**. Original files unchanged; temporary archive/views removed.
The final stricter transport check passes on the exact same archive bytes in
**5.95 s**, without repeating chemistry. Earlier single-tree bytes reproduce exactly.
Evidence: `complete_attempt_archive_2026_11_13`.

This is transport/read validation, not source retirement or ordinary-reader
integration. Next preserve all returned paths (prepared bundle, repair runtime,
continuation runtime and its parent runtime), connect the view to ordinary history
reads, then add a durable known-stopped retirement transaction with interruption
and repeat recovery. No existing scientific run has been compacted in place.

## Latest integration correction — C255 exact phase labels

C254 is committed/pushed as `39c5ae0`. C255 reuses only Alder `5561bfb`'s two
reviewed HL-discovery functions and unchanged regression file. New phase
references carry a complete HL coefficient family, not intensity labels; mixed
families refuse. All other C253 AutoSol functions are unchanged. The final
AutoPhase rename remains queued. The machine-readable audit now records this
Cedar correctness reconciliation separately, without claiming other branches changed.

Before: **6 failures / 4 passes** in the copied regression. After: **89 tests +
15 subtests, 20.92 s** across phase labels, AutoSol, selected references and
AutoRefine. Actual Phenix **2.2.1-6174 / dispatcher 2.2.1** performs a complete
MTZ-header read of the documented DiU result: **HLAM/HLBM/HLCM/HLDM**, 2.33 s.
The old report's intensity-label list and the MTZ bytes/timestamp remain unchanged.
No AutoSol/Coot/refinement rerun. Evidence: `phase_label_reconciliation_2026_11_13`.

## Latest completed step — C254 storage view

C253 is committed/pushed as `f337660`. C254 adds one root-only working-evidence
reconstruction around the two existing runtime-proof layers. Both scopes use one
decoder/object pool and the unchanged 128 MiB physical limit. Nested working views
are refused; normal/error exits clean temporary paths and restore accounting.
No old request, public path, archive format, chemistry or runtime depth changes.

**49 focused tests pass in 26.99 s**: working-scope controls, existing runtime
archives and compact workflow. The actual C244 complete ReadySet-continuation
reader also passes with original-request reads and native execution forbidden:
116 source-file checksums unchanged, five PHILs/two CIFs, owners STOPPED;
42,349,420 B logical reconstructed from 11,244,253 B compressed; 87,147,928 B peak
archive expansion (limit 134,217,728), 687,292,416 B Python peak, 81.63 s.
Temporary archive/views are removed; all original files remain. No new native
Phenix/Coot execution. Evidence: `bounded_working_view_2026_11_13`.

This closes the bounded-view/lifetime prerequisite, not working-file retirement.
The next storage step must bind archives to existing owner inventories, retain
public model/restraint paths and recover interruptions before removing any files.
Prior work checked: C228, C233, C237/C238 and C252; reuse these mechanisms.

## Current result

C253 compares AutoSol heavy-atom sites with the **chosen model's coordinates and
unit cell**, including a preparation alternative or manual/refined descendant.
The **original Phaser MR model remains the native phasing input**. Initial
preparation, chemistry, distance gates and later selections remain unchanged.
A selected model with no eligible heavy atom cannot reuse initial candidates.

A small immutable `AutoSol/site-reference.json` binds the chosen checkpoint/model,
original phasing input, candidates/cell and distance controls before native launch.
The existing guarded registry save advances this checked run to **schema 5**.
A conflicting preflight selection prevents launch. A later selection is preserved.
New results use anchored output references and an immutable AutoSol report; phase
and map consumers check the reference and repeat the saved site comparison.
Explicit AutoSol inspection shows that saved model/dictionaries, while ordinary
inspection follows the user's current choice. Native failure retains MR continuation.
Changed inputs or a conflicting report save retain outputs without phase adoption.

## Validation and reviewer handoff

Before: the separated-coordinate regression returned AUTOSOL_WARNING using initial
coordinates. After: selected iodine matches at 0 Å while the native command still
receives the original MR model. C253's 23 new controls cover corruption, relocation,
selection conflicts, native failure, alternatives, exact inspection and old readers.

Focused command (Python is the everyday checkout's `.venv/bin/python`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_autosol_selected_reference.py tests/test_autosol.py tests/test_cif_postmr_publication.py tests/test_checkpoints.py tests/test_coot_view.py tests/test_autorefine.py
```

**196 passed + 31 subtests, 22.91 s.** Adjacent inspection/candidate and ordinary
entry checks: **53 passed + 2 subtests, 1.04 s**. Documentation checks pass: seven
Markdown files, 322 local links, nine hashes, JSON uniqueness, syntax and whitespace.
The evidence ledger records the absolute
interpreter command and changed-source/test hashes. No full suite; last wholly
green full remains C220/583d30df, **9,178 tests + 276 subtests**. Full integration
validation remains required before merge.

The existing C252 native preparation also reads cold under C253: exact current
`manual-001`, parent `prepare-002`, five PHILs and two CIFs; histories 1/2 each
replayed once; **1,191 files unchanged**, **198.23 s**, Python peak **654,458,880 B**.
Old/cache/SDK paths and native execution were forbidden. Its schema stays 4.
That job is finished. No new native AutoSol, Coot or diffraction refinement claim.
C252 generated the preparation with Phenix 2.2.1-6174 / dispatcher 2.2.1; its
observation/map inputs are synthetic fixtures. Native evidence stays local.

Changed modules: autosol/reference, checkpoints, preparation publication, Coot
and AutoRefine consumers. Schema 5 is introduced only for a newly frozen checked
AutoSol reference; older readers refuse it, later alternative saves preserve it.
Existing schemas/results are not rewritten. Scientific files/runners are excluded
from Git; the ledger entry is `selected_autosol_reference_2026_11_13`.

## Next work — Q04/Q05 closure

1. **Keep necessary evidence without redundant working copies.** The C252
   two-attempt request retains **315,299,065 B**. C244 had **181,566,343 B** logical,
   **88,181,923 B** distinct and **93,384,420 B** repeated. Existing compression
   reconstructs one 131.7 MB subtree from an **8.3 MB** archive (418 files,
   57.7 MB physical temporary bytes), within the unchanged 128 MiB logical bound.
   Original-source reads were forbidden; temporary probe artifacts were removed.
   C254 closes the ReadySet extra-view refusal; C256 binds a complete attempt
   archive to the original owner inventory and replays it. Normal C252 reading
   also passes. Next integrate ordinary history reads and stable public references
   with known-stopped, interruption-safe retirement. Preserve failed/active work and partial outputs. No originals retired.
2. **Qualify/reconcile the remaining normal callers.** C253's selected-model
   AutoSol connection needs native acceptance. Interrupted AutoSol result saving
   retains outputs but does not automatically adopt them; keep it separate from
   existing preparation-publication recovery. Reconcile C156/C170, C223–C225,
   C248, C251–C255 rather than duplicating their machinery. Alder's HL-label fix
   is now reconciled on Cedar; preserve it alongside C253 during Q16 integration.
3. Q06 real complete-restraint diffraction refinement, then Q07 combined and
   held-out examples. The queue now allows roughly **2–5 further implementation
   patches plus validation** for supported Q04/Q05; storage remains uncertain.
   This is not an estimate for the entire catalogue programme or permission to merge.

C252 run: live-tests anchor
`252_Cedar_native-preparation-alternatives-8s_l2y96/final/ordinary run`.
Do not rerun completed mutating controls in place. Runners/metadata are in the
ordinary checkout's ignored `branch-artifacts/cedar/runners/`.

Linden works independently on Willow/Pine TopoStitch; C253 schema/interface notice
sent locally, signed Rowan. No cross-branch edit. AutoPhase naming remains the
**final Q16 implementation task** under the [pinned audit](autophase-rename-plan.json).
Protected NASolve-cedar and everyday NASolve/pine science, patches and environments
remain untouched. Continue on NASolve-c96/cedar; no new branch or merge.
