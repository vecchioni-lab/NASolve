# NASolve development handoff — current state

Updated **2026-11-13**, C246. Active **cedar**, checkout NASolve-c96.
Base C245/e7081d1; current HEAD supplies final identity. The
[queue](cif-doctor-completion-queue.md) owns order and the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

`nasolve postmr RUN --checked-preparation --automatic-plane-support` and schema-2
`[postmr] automatic_plane_support = true` now request the existing bounded plane
support through ordinary preparation/campaigns. True requires checked preparation;
invalid types/combinations refuse before preparation or tool discovery. Campaign
plans freeze the explicit boolean without inserting it into older policies.
Absent/false keeps earlier preparation intent. Continuation reads the saved choice.

Prior-work review: C244 owns generation/recovery; C245 freezes and forwards intake;
C224/C225 own ordinary publication and campaign handoff. Reuse all four. No new
executor, changed chemistry/default, native invocation or request/checkpoint schema.
New optional preset fields require a current reader; old policies/receipts need no
migration. Partial output remains protected; qualified fallback is not an unchecked
second preparation. Generation still does not certify final selected-plane adoption.

## Validation and reviewer handoff

Changed source: `postmr.py`, `cli.py`, `campaign_policy.py`, `presets.py`,
`campaign_stages.py`; four existing test modules extended. User guides, queue,
changelog and existing evidence ledger updated. AutoPhase technical audit/queue
from the preceding task is retained; rename implementation remains deferred.
No new test module, scientific artifact or shared-environment change.

Python 3.12.14; commands use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- Seven affected modules: **298 passed, 47 subtests**, 79.71 s.
- Added policy/interruption controls: **9 passed**, 0.95 s.
- Smoke profile: **139 passed, 6 subtests passed in 9.98s**. Focused development, not full regression.
- Before implementation: **19 expected failures** in the new/expanded checks.
- Frozen campaign replay passes after moving its root/removing the source preset,
  with old paths absent, subprocess execution forbidden and plan bytes unchanged.

The sandbox could not signal temporary worker groups; its workflow run was stopped.
The authorized workflow rerun was deliberately bounded after 457 passes + 25
subtests (403.53 s); it is not a completed profile. Focused process tests then
passed 22 + 19 subtests (2.86 s), and the smaller smoke profile passed as above.
No recovery code was weakened. Do not repeat the broad workflow profile for a
small caller-only change when the affected modules and smoke cover its boundaries.
Exact commands, source/test hashes, triage and scope are in ledger entry
`ordinary_campaign_plane_support_2026_11_13`. No fresh Phenix/Coot/refinement run.
Last wholly green full remains C220/583d30df: 9,178 tests + 276 subtests.
No new full-suite claim. All listed test jobs have stopped.

## Next work — finish Q04/Q05

1. Carry truthful generation notes through publication/ordinary output using the
   same verified result; do not read the expensive proof twice or change historical
   publication messages. Final selected-plane reporting and wider mixed/failure/
   interruption coverage remain necessary.
2. Define later preparation-child publication without replacing the immutable root
   or falsely making new MR construction descend from a refined model. Reuse
   existing C223–C225 publication and recovery, including genuine fallback receipts.
3. Implement known-stopped, interruption-safe retirement of redundant successful
   working output; retain reproducible inputs/proof and measure whole-request,
   temporary disk and memory after relocation. No persistent verdict cache.

C245–C246 complete intake and explicit ordinary/campaign forwarding within the
C244-based 6–9 patch estimate. Q06 real refinement and Q07 combined/held-out controls
follow Q04/Q05. Linden's read-only TopoStitch work is isolated on Willow; preserve
proposal versus adopted model/restraint distinctions and do not edit that worktree.

AutoPhase naming is queued as the **final Q16 implementation task**, followed
by final combined regression and merge review. The [commit-pinned machine-readable
audit](autophase-rename-plan.json) records native-call and saved-run compatibility,
plus the Alder phase-label/Cedar preparation-validation differences to preserve.
This is planning only; Q04/Q05 remain next and no commands have been renamed.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its untracked science, patches, environments and
Linden snapshots. Work only in NASolve-c96/cedar; no new branch or merge.
