# NASolve development handoff — current state

Updated **2026-11-13**, C244. Active branch **cedar**, checkout NASolve-c96.
Base C243/9f37d91; use current HEAD for final commit identity. The
[queue](cif-doctor-completion-queue.md) owns order and
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

The explicit complete-request API can now obtain missing source-supported plane
evidence itself and feed the existing repair/ReadySet machinery. It screens acquired
source dictionaries, generates only for types with missing supported coverage,
and uses one owned generation attempt per needed type per fresh outer attempt.
The choice is frozen; generated support belongs to child attempts, not edits to
frozen outer inputs. Old requests and C242's supplied-support mode are unchanged.
Ordinary PostMR/campaign callers do not yet activate this option.

C157/C170 already own generation and parent time; C240/C243 classify stopped
negative outcomes; C242 already connects supplied support to complete repair and
ReadySet. C244 reuses those pieces. No new executor, optimizer, graph rule, bounds,
stacking selection or phosphate behavior. Exact source/dictionary correspondence
is required. Do not turn arbitrary exceptions into chemical verdicts or fallback.

Two actual Phenix 2.2.1-6174 / dispatcher 2.2.1 controls use ordinary C218 PDU/NAR
inputs and an exact primary cache copy; neither supplies plane support. Success
obtains it and carries explicit C5 coverage plus all five ordered NAR files through
repair and ReadySet. The second deliberately caps only the candidate subprocess at
0.25 s. Its output stays unusable; independent linear-repair qualification and
ReadySet still succeed, with C5 missing coverage recorded. Both results cold-replay
after relocation without original paths, source/cache/SDK or process access.
All original input bytes/mtimes and all saved request bytes/mtimes are unchanged.
No new Coot invocation or diffraction refinement. All workers are known stopped.

Success retains 181.6 MB in 698 files; final ReadySet publication 5.8 MB. Cold read expands at most 81.4 MB temporary evidence and peaks at 570.6 MB resident memory.
The stopped-generator control retains 134.8 MB; its cold read expands 69.7 MB and peaks at 493.5 MB resident memory.
Whole-request retention, safe working-file retirement and campaign-scale memory/
concurrency still need work; a small publication is not the entire storage cost.

## Validation and reviewer handoff

Before: completed support had to be supplied explicitly. After: opt-in automatic
support uses exact graph findings and existing owned generation. Children must be
validated before repair and on readback; unknown ownership blocks recovery. Known
negative proof still requires explicit fallback policy and independent qualification.
A failed qualification yields no runtime. Preserve every previous/partial attempt.

Source: `cif_complete_request.py`; tests extend `test_cif_complete_request.py`.
Optional `configuration.plane_generation_policy` freezes
`cif-complete-owned-plane-generation-v1`; result `plane_generation` contains exact
per-component screening/outcome proof. Old absent/false and explicit supplied support
keep their meaning; new mode requires current reader. No migration/resealing.
Updated existing methods, human overview, queue, architecture/maps and changelog.

Python 3.12.14, exact focused command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_cif_complete_request.py tests/test_cif_plane_generation.py tests/test_cif_prepared_plane_support.py
```

**237 passed in 300.60 s.** New choice fails against previous HEAD; a foreign-owner
regression fails before the pre-repair guard and passes afterward. Controls cover
no-needed-support, exclusive choices, fresh history, interruption, corrupt proofs,
owner/recipe changes, qualified negative handling, exact readback and legacy reuse.
No new test module. AST/top-level duplicate and Git whitespace checks pass.

Native capsules under `live_tests_directory`:
- `244_Cedar_automatic-plane-request-19zp3y8k`
- `244_Cedar_automatic-plane-failure-ch6m6b9g`

Both requests now live at their capsule's `relocated/request`; `artifact-location.json`
is the anchored locator. `start.json` pins sources; driver records confirm source
unchanged and stopped. Exact commands/measurements: ledger entry
`automatic_plane_support_acquisition_2026_11_13`. Scientific files, ignored runners,
logs and pin lists remain local outside Git. Temporary code/expanded views removed.
No full suite. Last entirely green full remains C220/583d30df: 9,178 tests + 276
subtests. C222 failures were fixed focused; no later full-suite revalidation claim.

## Next work — finish Q04/Q05

1. Freeze/forward this explicit choice through ordinary checked PostMR/campaign
   callers, with cache/reuse/failure/interruption checks. Do not silently change old
   requests or turn on defaults without the declared integration contract. Keep
   current graph-correspondence limits and missing-plane notes visible in ordinary
   result/status reporting. Broader representations and native
   prelaunch/incomplete-build outcomes require explicit qualification, not catch-all
   fallback. Reuse current C244 native evidence instead of rerunning unchanged cases.
2. Define later preparation-child publication without replacing immutable roots
   or claiming fresh MR construction descends from a refined model. Reuse C223–C225's
   initial checkpoint, ordinary PostMR and frozen campaign entry.
3. Design interruption-safe retirement of redundant successful working files only
   after owners stop and sealed results verify. Keep reproducible inputs and proof;
   measure whole-request, temporary disk and memory separately. No verdict caches.

Q06 real refinement and Q07 combined/held-out chemistry follow Q04/Q05. NAR's
reviewed base-role atoms still define stacking; Cedar substituent planes do not
automatically enlarge those selections. No separate replacement plane engine.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains pre-existing untracked science, patches and venv.
Work only in NASolve-c96/cedar. No new branch, incidental cleanup or merge.
