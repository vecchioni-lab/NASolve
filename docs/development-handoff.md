# NASolve development handoff — current state

Updated **2026-11-13**, C249. Active **cedar**, checkout NASolve-c96.
Base C248/de117a2 (pushed); current HEAD supplies final identity. The
[queue](cif-doctor-completion-queue.md) owns work order and the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

C249 reports explicit source-graph planes in the exact selected dictionaries,
separately from generation outcomes. Reuse C208's graph screen and the existing
single complete proof read. Ambiguous/unsupported definitions remain unassessed;
changed input hashes refuse. No guess about dictionary precedence, effective
native modifiers, alternative restraints, achieved geometry or refinement success.
C247 already carries these notes through publication, PostMR and campaign status.
Old messages/receipts, selections, fallback rules and saved schemas stay unchanged.

Source changes: `cif_plane_coverage.py`, `cif_ordinary_postmr.py`; extend the two
existing test modules. No native command, new executor, proof cache or science
artifact. Additive descriptive live reporting only; old requests need no migration.
C246 explicit ordinary/campaign forwarding and C248 mixed ownership controls
remain intact. C248 found no production defect; its 23 distinct focused cases
passed across the original run and corrected exception-type assertion rerun.

## Validation and reviewer handoff

Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- New C249 regressions before implementation: **11 expected failures**.
- Five affected coverage/ordinary/publication/PostMR/campaign modules:
  **176 passed**, 11.62 s.
- After final returned-assessment hash binding: both changed test modules
  **61 passed**, 0.71 s.
- Actual retained C244 Phenix 2.2.1-6174 / dispatcher 2.2.1 proof: success/timeout
  ordinary-reader controls both pass, **698/506 files unchanged**. The successful
  selected PDU dictionary has explicit C2/C4/C5 planes; timeout still lacks C5.
  Runtime remains `readyset_checked_model` with five ordered PHIL files. No
  diffraction-refinement claim. Read times 103.63/88.19 s; process peak 667,795,456 B.

Exact commands/hashes and scope: ledger `selected_dictionary_planes_2026_11_13`.
The saved-native replay substitutes only the request-location adapter, forbids
native processes and old source/SDK paths, and checks all bytes/timestamps.
It is not fresh ordinary construction/publication. No new native run or full suite.
Last wholly green full remains C220/583d30df: **9,178 tests + 276 subtests**.
No native or test jobs remain active; use focused checks for the next bounded change.

## Next work — finish Q04/Q05

1. Audit remaining prelaunch/deadline/failure boundaries against existing process
   ownership tests before adding machinery. Unknown ownership must never authorize
   retry or fallback; preserve every partial output and require a fresh attempt.
2. Define later preparation-child publication without replacing the immutable root
   or falsely making new MR construction descend from refined coordinates. Reuse
   C223–C225 publication/recovery and genuine fallback receipts.
3. Implement known-stopped, interruption-safe retirement of redundant successful
   working output; retain reproducible inputs/proof and measure whole-request,
   temporary disk and memory after relocation. No persistent verdict cache.

Q06 real complete-restraint refinement and Q07 combined/held-out controls follow
Q04/Q05. Scoped selected-CIF reporting does not need a second universal chemistry
screen; effective native restraints and achieved geometry belong to Q06.
Linden's read-only TopoStitch is isolated on Willow; keep proposal versus adoption
clear and do not edit that worktree. Local coordination is authorized.

AutoPhase naming is queued as the **final Q16 implementation task**, followed by
combined regression and merge review. The [commit-pinned machine-readable audit](autophase-rename-plan.json)
records native-call/saved-run compatibility and Alder phase-label/Cedar preparation
validation differences. Planning only; no commands have been renamed.

## Preserve local evidence

Protected NASolve-cedar stays at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains untracked science, patches, environments and Linden
snapshots. Work only in NASolve-c96/cedar; no new branch or merge. Local runner:
`branch-artifacts/cedar/runners/c249_selected_read.py` in the everyday checkout.
No retained scientific artifacts are copied into Git or silently retired.
