# NASolve development handoff — current state

Updated **2026-11-13**, C245. Active **cedar**, checkout NASolve-c96.
Base C244 plus planning audit / be69b1d; current HEAD supplies final identity.
The [queue](cif-doctor-completion-queue.md) owns order and the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

`nasolve cif-doctor prepare-run RUN --automatic-plane-support` now freezes the
existing bounded support-generation choice through prepared/ordinary intake.
Invalid non-booleans refuse before source freezing/tool setup; absent/false keep
previous intent. Continuation uses the frozen request, with no new flag override,
repeat construction or new generation framework.

Exact result/continuation reading reports each component's generation outcome:
source-checked support obtained, no missing coverage within the supported screen,
or a classified failed generation whose output was excluded. It names initially
screened centres. Generation success does not prove final plane adoption in the
selected restraints, and preparation does not establish diffraction refinement.
Source-graph eligibility, independent qualification, phosphates and NAR ownership
are unchanged. Direct `postmr --checked-preparation` and campaigns still do not
forward this option; defaults remain unchanged.

Prior-work review: C220 already owns the command/result/recovery path; C244 already
owns support generation and real success/timeout checks. C223 recomputes published
messages during saved-checkpoint validation. Therefore C245 changes display-only
limitations and preserves the persisted message, avoiding old receipt invalidation.
No new executor, chemical rule, request schema or altered time/storage budget.

## Validation and reviewer handoff

Source: `cif_postmr_request.py`, `cif_ordinary_postmr.py`, `cli.py`. Tests extend
five existing intake/result/CLI/publication modules. Guides, queue, changelog and
existing ledger updated. No new test module or scientific artifact in Git.
Before: support choice stopped at complete intake and results had generic notes.
After: explicit prepare-run/intake reaches the same owner and reports exact
outcomes. Historical request intent and publication bytes keep their meaning.

Python 3.12.14, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- `-m pytest -q -p no:cacheprovider tests/test_cif_postmr_request.py tests/test_cif_ordinary_postmr.py tests/test_cif_ordinary_outcome.py tests/test_cif_ordinary_cli.py tests/test_cif_postmr_publication.py tests/test_cif_preparation_view.py`: **166 passed in 67.36 s**.
- Added afterward: `-m pytest -q -p no:cacheprovider tests/test_cif_postmr_publication.py -k plane_display_notes`: **1 passed in 5.88 s**. 167 distinct affected tests total.
- Six new option/result/CLI controls fail before implementation. Strict intake,
  frozen continuation, usable/fallback/unusable display and unchanged publication
  all have focused checks. No full suite.

Read-only replay uses both actual C244 Phenix 2.2.1-6174 / dispatcher 2.2.1 requests.
The ordinary-location adapter points to those existing validation capsules; full
scientific replay is real. This is not fresh ordinary construction/publication.
All 698 success and 506 timeout request files retain bytes/mtimes, each result keeps
its selected ReadySet model and five ordered PHIL files, and the new notes distinguish
generation success from timeout. Original inputs/cache/SDK and execution are
forbidden. No new Phenix, Coot, refinement, bulk copy or scientific capsule.
Code stayed fixed during replay. Exact commands/hashes/scope are in ledger entry
`ordinary_plane_support_entry_2026_11_13`. All jobs are stopped.

Changed Python AST/top-level duplicates, documentation targets and Git whitespace
checks pass. Last wholly green full remains C220/583d30df: 9,178 tests + 276
subtests. C222 failures were fixed focused; no later full-suite revalidation claim.

## Next work — finish Q04/Q05

1. Connect the explicit choice to direct PostMR/campaign declarations and truthful
   publication display. Reuse the already validated result when publishing; avoid
   another full proof read just to format notes. Preserve old publication messages
   and frozen campaign/request meaning. Distinguish generated support from final
   selected-plane adoption; mixed/failure/interruption coverage remains necessary.
2. Define later preparation-child publication without replacing an immutable root
   or implying fresh MR construction descends from a refined model. Reuse existing
   C223–C225 publication and recovery, including genuine fallback receipts.
3. Implement known-stopped, interruption-safe retirement of redundant successful
   working output. Retain reproducible inputs/proof, test relocation and measure
   whole-request, temporary disk and memory. No persistent verdict cache.

The C244-based 6–9 patch estimate remains in the queue; C245 completes its first
intake/command/reporting slice. Q06 real refinement and Q07 combined/held-out tests
follow Q04/Q05. Broader chemistry remains queued without rebuilding completed work.
Morning audit identified old nested review duplication; the inventory stays local
outside product Git. No scientific cleanup. Consolidate current explanations while
preserving historical evidence/anchors; no need to reproduce old transport fixes.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its untracked science, patches, environments and
Linden snapshots. Work only in NASolve-c96/cedar; no new branch or merge.
