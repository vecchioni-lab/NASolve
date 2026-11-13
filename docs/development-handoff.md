# NASolve development handoff — current state

Updated **2026-11-13**, C252. Active **cedar**, checkout NASolve-c96.
Production source C251/14cfb00 is pushed and unchanged by this validation checkpoint.
The [queue](cif-doctor-completion-queue.md) owns work order; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

C251 saves later checked attempts as explicit, unselected REVIEW alternatives from
the same frozen construction. It preserves the initial preparation and current
choice, binds exact model/CIF/PHIL inputs, and guards against stale registry edits.
Use `cif-doctor publish-preparation RUN --attempt N --as-alternative`.
The alternative is not claimed to descend from a selected refined model.

C252 now exercises that machinery with actual Phenix **2.2.1-6174 / 2.2.1**:
a deliberately timed-out optional plane generator retains a qualified ReadySet
result with honest missing-C5 notes. A fresh attempt obtains source-checked support,
passes repair/ReadySet and saves `prepare-002`. Its selected dictionary explicitly
covers screened centres C2/C4/C5. Original report, receipt, root and selection stay
fixed; all **467 first-attempt files** are unchanged.

After relocation with the original path absent and old/cache/SDK reads plus native
execution forbidden, Coot resolves the exact alternative and AutoRefine resolves
its model, **five PHIL files and two CIFs in order**. Coot uses the component CIF;
the modification-only CIF remains in refinement's input set.
A follow-through imports the exact unchanged model as a REVIEW manual child,
explicitly selects it, and confirms repeat preparation publication preserves that
choice and inherited restraints. This is an input/lineage check, not a chemical edit.

## Validation and reviewer handoff

- Two complete native attempts, publication and relocated Coot read: **1727.15 s**;
  **1190 files unchanged** during cold inspection. Owned native workers stopped.
- AutoRefine input read: **196.96 s**, same 1190 files unchanged.
- Manual import/explicit selection/repeat/inspection: **806.54 s**;
  all **1183 request files**, three preparation receipts and inherited inputs preserved.
- A second relocation after manual import leaves its historical source absent:
  **1191 files unchanged**, exact selected model/restraints retained,
  **225.12 s**, no native execution.
- Each ordinary operation replays each exact attempt once. Source remains C251.
  Commands, runner hashes and compact results: ledger
  `native_preparation_alternatives_2026_11_13`; C251 regression commands/results
  remain in `preparation_alternatives_2026_11_13`.
- No full suite or repeated unchanged unit suite. Last wholly green full:
  C220/583d30df, **9,178 tests + 276 subtests**. C251 focused checks remain the
  latest source-regression evidence; integration still needs the full suite.
- Documentation checks pass: five Markdown files, 205 local file-link targets,
  nine evidence hashes, unique JSON keys and `git diff --check`.

This checkpoint changes documentation/evidence metadata only; C251 compatibility
and schema remain unchanged. Scientific outputs/runners stay local and no old
runs were retired. Observation/map files are **synthetic path fixtures**: no MTZ,
Free-R or diffraction-refinement validation, new Coot launch or AutoSol execution
is claimed. Explicit plane membership is not achieved-geometry qualification.

All C252 native/readback jobs have finished. Evidence anchor `live_tests_directory`:
`252_Cedar_native-preparation-alternatives-8s_l2y96/final/ordinary run`.
Final test choice is `manual-001`, deliberately selected by the manual control;
initial and `prepare-002` records remain intact. Runners live in the everyday
checkout's ignored `branch-artifacts/cedar/runners/` and are hashed in the ledger.
Do not rerun the completed mutating control in place.

## Next work — Q04/Q05 closure

1. **Compare heavy-atom sites with the chosen model.** AutoSol must keep the
   original Phaser MR model as its phasing input. Connect the chosen prepared
   model's candidate coordinates/unit cell and saved validation identity, and
   have phase/map readers verify that binding. Preserve thresholds and old runs.
   C251 currently refuses schema-4 non-root selection rather than using the wrong
   initial reference. Do not merely replace a model path and retain old coordinates.
2. **Keep necessary evidence without redundant working copies.** The two-attempt
   request retains **315,299,065 B**. A read-only C244 audit found
   **181,566,343 B** of logical files, **88,181,923 B** of distinct bytes and
   **93,384,420 B** repeated. Independent compression estimates 16.0 MB before
   indices/retained-public-path requirements; it is not a usable compact request.
   Reuse bounded archive machinery; preserve public model/restraint references and
   every owner's inventory, known-stopped recovery and interruption safety.
3. Reconcile remaining caller/recovery acceptance against C156/C170, C223–C225,
   C248, C251/C252 rather than rebuilding them. Then Q06 real complete-restraint
   refinement and Q07 combined/held-out examples. The queue estimates roughly
   3–6 remaining implementation patches for supported Q04/Q05, plus validation;
   this is not an estimate for the entire catalogue programme or permission to merge.

Native Python worker peak was **702,218,240 B**; the read-only refinement
process peaked at **547,979,264 B**. These are not combined external-Phenix
peaks. Campaign-scale disk, temporary expansion and concurrency remain open.

Linden's TopoStitch coordinate-end work remains isolated on Willow/Pine; later
checkpoint adoption requires explicit interface qualification. No cross-branch edit.
AutoPhase naming stays the **final Q16 implementation task**; preserve the
[commit-pinned audit](autophase-rename-plan.json), native AutoSol calls and saved
identities, including Alder phase-label/Cedar preparation validation differences.
Protected NASolve-cedar and everyday NASolve/pine science, patches and environments
remain untouched. Continue on NASolve-c96/cedar; no new branch or merge.
