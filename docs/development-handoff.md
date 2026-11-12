# NASolve development handoff — current state

Updated **2026-11-12**, C242. Active branch **cedar**, checkout NASolve-c96.
C242 builds on pushed 8981f9d (C240–C241); use current HEAD for its final commit.
The [queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

The complete dictionary request now accepts explicitly supplied, completed plane
support. It freezes the exact source/request/attempt evidence, uses the same
repair machinery and passes the selected repaired model/restraints through
ReadySet. Actual Phenix selects the repaired bundle and then the checked ReadySet
model, retaining explicit PDU C5 plane coverage and all five ordered NAR files.
This closes the complete-request reuse connection. Automatically obtaining missing
support is still the next Q04 job; no default/CLI switch was added.

Prior-work review: C234–C239 already validate source-owned support and run combined
linear/plane repair; C184/C229 already own complete request/ReadySet continuation.
C242 shares those validators/owners instead of adding replacements. C240 supplies
narrow evidence for launched stopped failed generation; C241 preserves the existing
multiple-plane recipe through acquisition identity. That negative proof alone
allows neither fallback nor retry. Earlier capability/prelaunch failures and
zero-exit unqualified builds still need explicit treatment.

Actual Phenix **2.2.1-6174 / dispatcher 2.2.1** control uses C218's frozen ordinary
Coot/NAR inputs, exact cached dictionaries and completed C215 plane support. No new
generation, Coot or diffraction refinement. The outer attempt returns and every
owner stops; source files remain pinned and old input bytes/mtimes unchanged.
The request is then moved, not copied, and read from relocated source with old
request/source/support/cache/SDK paths and process calls forbidden. All
698 files preserve bytes/mtimes; temporary views are removed.
**No active job remains.** Native/cold receipts and artifact-location.json live at
`live_tests_directory/242_Cedar_complete-plane-request-2r0jv29f`.

Storage: whole complete request **181.6 MB**, final ReadySet publication
**5.8 MB**. Cold read expands at most **81.4 MB** temporary evidence and peaks
at **645.1 MB** resident memory. This is a complete request, unlike C238's
134.4 MB standalone repair. Original worker/partial evidence stays intact. Safe
retirement and campaign-scale memory/storage qualification remain open; small
publications do not authorize 100 simultaneous readers.

## Validation and reviewer handoff

Before: only the prepared-repair request accepted supplied completed plane support.
After: the complete request freezes it, passes the exact choice to repair, verifies
child identity and continues the checked result through ReadySet. The preceding
site-preparation inputs correctly exclude evidence owned by the repair stage.

Changed source: `cif_complete_request.py`, `cif_prepared_repair_execution.py`.
Regression tests extend `test_cif_complete_request.py`; existing support/recovery
coverage checks the shared validator. No new test module/profile or executor.
Methods/capability table, human overview, documentation map, queue, changelog and
existing evidence ledger are updated. The overview replaces older overlapping
storage narratives with the present whole-workflow measurement.

Compatibility: optional complete-request `configuration.plane_support` reuses
`cif-prepared-owned-plane-support-v1`; it is absent by default. Old requests retain
their meaning and need no migration. New mode requires a current reader. No changed
chemical gates, limits, source/phosphate state, Free-R rules or stacking selections.
Support never authorizes wholesale replacement by an unrelated generated CIF.

Focused command (Python 3.12.14 from the existing test environment):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <python3.12> -m pytest -q -p no:cacheprovider tests/test_cif_complete_request.py tests/test_cif_prepared_plane_support.py tests/test_cif_repair_attempt.py
```

**210 passed in 221.76 s.** Eight new transport cases cover independent frozen
reuse, immutable fresh attempts, relocation, wrong source/attempt, overlap,
concurrent changes and dropped parent/child choices. The first new regression
failed before implementation (missing API argument). Initial development exposed
and fixed preparation-versus-repair evidence ownership before the final passing
run. Changed-file AST/duplicate-definition review and `git diff --check` pass.
Exact native/cold commands, locations and pins are recorded in ledger entry
`complete_request_plane_support_2026_11_12`; no scientific artifacts, logs, local
runners or large source-pin lists are included in Git.

No full suite this push, as requested. Last entirely green full remains
C220/583d30df: 9,178 tests + 276 subtests. C222's later failures were fixed with
focused checks; no subsequent full-suite revalidation claim.

## Next work — finish Q04/Q05

1. Obtain missing plane support through the existing complete-request generation
   owner using graph findings, exact numbered children, shared deadlines and finite
   attempts. Preserve a separately checked parent on explicitly classified optional
   failure. C242 already supplies freezing/reuse/repair/ReadySet: do not rebuild it.
   C240's negative proof is narrow; unknown processes or malformed proof still block
   retry. Preserve old request meanings and every partial output.
2. Define later preparation-child publication without replacing an immutable root
   or claiming fresh MR construction descends from a refined model. C223–C225
   already supply initial checkpoint, ordinary PostMR and frozen campaign entry.
3. Design interruption-safe retirement of redundant successful working files only
   after owners stop and the sealed result verifies. Keep reproducible inputs and
   necessary proof; measure whole request, temporary disk and memory separately.
   Avoid repeat validation where an existing scoped read can be safely shared;
   do not replace integrity checks with a persistent verdict cache.

Reuse C160/C163/C164 ownership/recovery, C207 full-model plans, C213/C232 generation
binding, C226 maintained whole-plane numerics, C227 composition/selection and
C228–C233 compact evidence/shared reads. Q06 real complete-restraint refinement
and Q07 combined/held-out chemistry follow Q04/Q05. NAR's reviewed base-role atoms
still define stacking; Cedar's substituent planes do not enlarge it automatically.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its pre-existing untracked science, patches and venv.
Work only in NASolve-c96/cedar. No new branch, incidental cleanup or merge.
