# NASolve development handoff — current state

Updated **2026-11-13**, C243. Active branch **cedar**, checkout NASolve-c96.
C243 builds on pushed C242/5708f59; use current HEAD for the final commit identity.
The [queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

Doctor can now recognize a generator that completed normally but produced a
source-chemically rejected dictionary. The existing failure reader repeats the
full source/native-handoff/candidate assessment, binds the exact request and
stopped worker, and returns a distinct rejection proof with its checked diagnostic.
That output stays unusable; the proof itself allows neither fallback nor retry.
Existing successful support and nonzero failed/timed-out proofs remain unchanged.

Prior-work review: C193 diagnostics explain failures but do not qualify evidence;
C240 supplies strict launched-negative execution evidence; C242 already freezes
supplied plane support through complete repair/ReadySet. C243 fills the narrow
completed chemical-rejection gap using the same positive replay and ownership
checks. It does not create another generator or complete automatic scheduling.
Capability/prelaunch failures, incomplete handoffs and caught builder exceptions
remain outside this new outcome. Never classify arbitrary errors as permission.

C242's real Phenix 2.2.1-6174 / dispatcher 2.2.1 control remains the complete-request
checkpoint: repaired plane bundle, then ReadySet-checked model, explicit PDU C5
coverage and all five NAR files. Whole request 181.6 MB; final publication 5.8 MB;
cold read 81.4 MB temporary evidence / 645.1 MB resident memory. Its 698 files
survive relocation unchanged. Evidence: `complete_request_plane_support_2026_11_12`.
Automatic acquisition of missing support is still Q04; later preparation children
are Q05. Neither C242 nor C243 establishes diffraction refinement.

## Validation and reviewer handoff

Before: the negative reader accepted launched nonzero failed/timed-out jobs only.
After: it additionally accepts a fully replayed completed source rejection. A
normal exit without a complete, consistent rejected build is still insufficient.
Changed source: `cif_plane_generation.py`, `cif_source_representation.py`;
regressions extend `test_cif_plane_generation.py`. No new test module, executor,
worker, generation option, chemical gate or altered time/storage bound.

Derived proof: `cif-owned-plane-generation-rejection-v1`, with
`failure_kind=REJECTED_CANDIDATE`, source rejection and its rechecked diagnostic.
Existing failure proofs are exactly unchanged, including the saved actual C240
proof. No saved-format migration or historical resealing. Sources, phosphate
state, Free-R behavior and NAR stacking selections are unchanged.

Python 3.12.14 focused commands, with PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:

- `-m pytest -q -p no:cacheprovider tests/test_cif_plane_generation.py tests/test_cif_source_representation.py tests/test_cif_generation_attempt.py tests/test_cif_acquisition_attempt.py`: **249 passed in 73.57 s**.
- After two corrupt-receipt routing controls, `-m pytest -q -p no:cacheprovider tests/test_cif_plane_generation.py`: **90 passed in 32.68 s**. Sets overlap; do not sum.

Three new rejection cases fail before implementation; two malformed-routing cases
also fail before their domain-error guard. The initial restricted run could not
verify shutdown in two existing timeout controls; rerunning with process access
passes without changing ownership rules or test timeouts. The synthetic cases
exercise actual small subprocesses but make no Phenix chemical-validation claim.

Relocated temporary code reads a new synthetic rejection and the earlier actual
C215 success/C240 timeout with original code/request paths absent and old source,
SDK and process access forbidden. All 73 temporary request files and 49 original
native files retain bytes/mtimes; the 1.42 MB temporary copies are removed.
No new Phenix, Coot or diffraction refinement execution. No active job remains.
Exact commands, source hashes and scope: ledger entry
`completed_plane_generation_rejection_2026_11_13`. Scientific captures, ignored
runners and logs stay outside Git. Changed-file AST/duplicate-definition and
Git whitespace checks pass. Methods, human explanation and queue are updated.

No full suite this push. Last entirely green full remains C220/583d30df:
9,178 tests + 276 subtests. C222's later failures were fixed with focused checks;
no subsequent full-suite revalidation claim.

## Next work — finish Q04/Q05

1. Obtain missing plane support through the existing complete-request generation
   owner using graph findings, exact numbered children, shared deadlines and finite
   attempts. Generated support belongs to owned child attempts; never append it to
   frozen outer inputs or silently change C242's explicit reuse meaning. Reuse
   `generate_source_candidate_attempt`'s parent identity and remaining-time binding;
   extend the complete owner's child inspection/sealing and recovery consistently.
   Consume C240/C243 classified outcomes only with a separately qualified fallback.
   Unknown processes/corrupt proof still block retry. Preserve all partial outputs.
2. Define later preparation-child publication without replacing an immutable root
   or claiming fresh MR construction descends from a refined model. C223–C225
   already supply initial checkpoint, ordinary PostMR and frozen campaign entry.
3. Design interruption-safe retirement of redundant successful working files only
   after owners stop and the sealed result verifies. Keep reproducible inputs and
   necessary proof; measure whole request, temporary disk and memory separately.
   Reuse existing scoped reads; do not add persistent verdict caches.

Reuse C160/C163/C164 ownership/recovery, C207 full-model plans, C213/C232 generation
binding, C226 whole-plane numerics, C227 composition and C228–C233 compact/shared
reads. Q06 real refinement and Q07 combined/held-out chemistry follow Q04/Q05.
NAR's reviewed base-role atoms still define stacking; Cedar's substituent planes
do not enlarge those stacking selections automatically.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its pre-existing untracked science, patches and venv.
Work only in NASolve-c96/cedar. No new branch, incidental cleanup or merge.
