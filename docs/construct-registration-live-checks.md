# Construct Registration human live-check queue

Status: **living minimum checklist**. Keep this short. Add or remove checks as the
registration architecture changes.

This file is not a substitute for unit/regression tests. It records the smallest
set of **human-visible / real-workflow checks** that should not be forgotten as
implementation moves across branches, chats and campaign work.

Do not mark a check complete before the relevant layer is actually wired into
the live pipeline.

| Status | Trigger | Human check | Minimum pass condition |
| --- | --- | --- | --- |
| ☑ | **Before merging a substantial registration backend branch** | Run the focused registration/model-candidate tests **and the full NASolve regression suite**. | **Birch complete: focused bundle 44/44 green; full suite 664 tests + 222 subtests green.** No unrelated regression observed. |
| ☐ | **When Registration Scout / registration is first wired into AutoMR/PostMR** | Run one known, ordinary **clean W** dataset end-to-end through the existing path. | It takes the boring identity fast path, adds no unnecessary prompt, preserves the expected MR/PostMR result, and the frozen registration artifacts accurately describe the known construct. |
| ☐ | **When non-identity registration / recut rescue first becomes executable** | Use the planned **8D93-style -> W** validation case and inspect the proposed mapping/recut in the Registration Net + Coot. | Chain mapping/cut is scientifically sensible; sticky-end/boundary differences are shown correctly; required terminal-phosphate intent remains separate and correct; the transformed model is reconstructible from provenance. |
| ☐ | **When multiplicity handling first becomes live** | Use an **8D31-like extra-copy** case, plus a partial-copy case when available. | Complete registered copies receive the intended logical sequence/modification actions; a partial copy is visibly classified as partial and is never silently treated as a complete second copy. |
| ☐ | **When guided ambiguity handling gets a UI/CLI** | Exercise a deliberately ambiguous short repeat / single-base-overhang mapping. | NASolve shows the alternatives instead of guessing; the user can select one minimal mapping decision; that choice freezes/replays exactly and does not silently become a global recipe. |
| ☐ | **When bounded multi-PDB MR selection is enabled** | Put several plausible PDBs in one dataset and inspect the candidate report before/after MR attempts. | Every candidate and rejection remains visible with immutable file identity; no filename or registration-score shortcut silently chooses a model; any automatic choice follows the reviewed MR policy and materially different successful interpretations remain inspectable. |

## Current validation note

The earlier Birch checkpoint at code head
`4452295c3330de6d55bddd75b01be21f39afb222` had **23 focused registration
tests passing locally**.

The current Birch focused bundle has **44 tests passing locally** across
`tests/test_construct_registration.py` and `tests/test_model_candidates.py`.
The full NASolve regression suite also passed locally with **664 tests and 222
subtests** in **61.70 s** on checkout
`cc0ad6ab537cc61e17e13bc562e4ae8667461e8d`.

When a live check above is completed, record the dataset/run/checkpoint and code
commit in the development handoff or the machine-readable intent ledger. Avoid
writing only "passed": the point is to preserve *what exact behavior was seen*.
