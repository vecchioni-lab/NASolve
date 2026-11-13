# NASolve development handoff — current state

Updated **2026-11-13**, C247. Active **cedar**, checkout NASolve-c96.
Base C246/903c371 (pushed); current HEAD supplies final identity. The
[queue](cif-doctor-completion-queue.md) owns order and the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

C246 connects explicit automatic plane support through checked PostMR and frozen
schema-2 campaign recipes. C247 now carries already-verified generation notes
through publication and ordinary output, without rereading the proof. The
receipt-only API remains; historical preparation/checkpoint messages stay unchanged.
Campaign PostMR receipts may contain validated `preparation_notes`; text/JSON status
retains those notes through later stages and remains read-only. Descriptive notes
do not change scientific gates, selection or warning classification.

Historical results without a generation record say so; they no longer suggest
that support is unavailable globally. Generated support still does not prove final
plane adoption or diffraction-refinement success. Malformed proof cannot produce
a fallback or a usable result. No new executor, proof cache or native command.

Prior-work review: reuse C223 publication/partial-save recovery, C245 exact notes
and C246 forwarding. The existing writer already has the verified result; return
its notes rather than rereading science or changing receipt hashes.

## Validation and reviewer handoff

Source: ordinary result/publication helpers, PostMR return value, CLI, campaign
stage/receipt/status readers. Existing tests extended; no new test module or
scientific artifact. Additive live API and optional campaign display metadata only;
older readers may omit notes, old records need no migration. All earlier run choices
and the selected model/CIF/PHIL set remain unchanged.

Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- Initial publication/ordinary callers: **148 passed**, 17.20 s.
- Final campaign/publication callers: **151 passed, 13 subtests**, 16.66 s.
- Historical no-generation wording: **23 passed**, 0.54 s.
- New publication tests fail before implementation; campaign status/typed-note
  checks likewise fail before their connection. Repeated publication verifies once;
  saved receipt bytes/mtimes stay fixed. Existing relocation/recovery checks pass.
- Read-only campaign status retains notes after later refinement without altering
  any saved bytes/mtimes or changing the scientific outcome.

Exact commands and hashes: ledger `published_preparation_notes_2026_11_13`.
No full suite or new Phenix/Coot run. C246 already passed 298 affected tests + 47
subtests, 139 smoke tests + 6 subtests and 22 process tests + 19 subtests. Its large
workflow profile was deliberately bounded, not completed. Keep focused scope;
do not repeat thousands of unchanged tests for display-only integration.
Last wholly green full remains C220/583d30df: 9,178 tests + 276 subtests.

## Selected-plane investigation completed

Read-only C244 proof replay plus the existing source/graph screen found explicit
C2/C4/C5 planes in the selected successful PDU CIF; the timeout control's selected
CIF still lacks C5. All 698/506 files retain bytes/mtimes. No native execution or
numerical/refinement approval. Exact results and runner hash are under C247's
`selected_plane_investigation` ledger record; local runner is in the everyday
checkout's ignored `branch-artifacts/cedar/runners/c247_selected_plane_probe.py`.
This diagnostic is not yet integrated into ordinary selected-plane reporting.
Both proof-read jobs and all test jobs are stopped. Do not rerun merely to recover
context; preserve the generation-versus-selected-coverage distinction.

## Next work — finish Q04/Q05

1. Establish what final selected-plane coverage can honestly report; preserve
   source/selection/graph boundaries and reuse current screens. Finish wider mixed,
   failure and interruption coverage before claiming Q04 closure.
2. Define later preparation-child publication without replacing the immutable root
   or falsely making new MR construction descend from a refined model. Reuse
   existing C223–C225 publication and recovery, including genuine fallback receipts.
3. Implement known-stopped, interruption-safe retirement of redundant successful
   working output; retain reproducible inputs/proof and measure whole-request,
   temporary disk and memory after relocation. No persistent verdict cache.

C245–C247 close explicit ordinary/campaign forwarding and generation reporting.
Q06 real refinement and Q07 combined/held-out controls follow Q04/Q05. Linden's
read-only TopoStitch is isolated on Willow; preserve proposal versus adopted
model/restraint distinctions and do not edit that worktree.

AutoPhase naming is queued as the **final Q16 implementation task**, followed
by final combined regression and merge review. The [commit-pinned machine-readable
audit](autophase-rename-plan.json) records native-call and saved-run compatibility,
plus the Alder phase-label/Cedar preparation-validation differences to preserve.
This is planning only; Q04/Q05 remain next and no commands have been renamed.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its untracked science, patches, environments and
Linden snapshots. Work only in NASolve-c96/cedar; no new branch or merge.
