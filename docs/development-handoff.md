# NASolve development handoff — current state

Updated **2026-11-13**, C259 native diagnostic complete; C260 caller integration next. Active **cedar**, checkout NASolve-c96.
The [queue](cif-doctor-completion-queue.md) owns work order; the
[capability table](cif-doctor.md#current-capability-boundary) owns support limits.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.
Simon authorized this pass through **23:00 Europe/London**, focused tests only.

## Latest native control — C259 blocked before phasing

C258 is committed/pushed as `3d87abc`. The fresh C259 control completed Phaser
(MR_SUCCESS, TFZ 17.10) and Coot construction, then stopped at curated 1AP acquisition:
`_ideal_seed` requires CCD ideal coordinates, while this source supplies x/y/z.
The C30 numerical-recovery adapter already distinguishes source-declared coordinates
from independent ideal coordinates; ordinary acquisition has not connected that
case. Do not silently relabel coordinates or change curated chemistry to pass.
No checked checkpoint, ReadySet, AutoSol or diffraction refinement was reached.

Raw DiU first reproduced the known C188/C189 B:1 terminal-phosphate refusal. The
fresh benchmark used the explicit C80-style free-end fixture at A:1/B:1/C:8,
retaining D:1's original declared phosphate exactly. This is a software-test state,
not a claim about DiU terminal chemistry. All donor inputs and partial outputs remain.
The final owner confirms stopped processes and unchanged source code. Local evidence:
`/Users/svecchio/NASolve-live-tests/259_Cedar_selected-autosol-wxv04px_`;
`/private/tmp/c259-root.txt` points there. Exact hashes/versions and earlier refused
controls are in ledger `native_selected_autosol_control_2026_11_13`.

## Active next bounded step — C260 ordinary storage integration

Reuse C258 retirement after successful checked publication, without allowing optional
storage failure to discard usable science. Inspect campaign receipt ownership and
ordinary/alternative publication first; retain read-only inspection and all failed
work. No second archive/owner/chemical validator. Curated-source acquisition above
is a distinct, recorded Q05 acceptance prerequisite, not a silent detour.

## Latest completed step — remove reproducible successful working copies safely

C257 is committed/pushed as `ecafc98`. C258 adds explicit
`retire_attempt_working_files` under the same request lock. It reuses C257 ordinary
archive reads and C256 transport, with no second scientific/ownership validator.
Prior work checked: C228/C229 storage choices, C237/C238 owner partitions,
C252 ordinary alternatives, C254 outer scope, C256 archive and C257 stable paths.

Before: ordinary reads could use a manually compacted test copy, but the product
had no removal/recovery operation. After: only qualified, successful, stopped
native work can be retired. Archive bytes and immutable intent are durable before
any checksum-matching duplicate is removed. Public models/restraints, original
scientific records, shared inputs/acquisitions and failed/uncertain work stay in
place. Interruptions remain readable and resume explicitly without native retry.
Changed files/archives/intent stop cleanup; completion binds exact retired counts.
Complete unpublished archives are synced during recovery; partial archives stay
preserved/refused. No ordinary/campaign automatic invocation yet.

New schema-1 storage receipts: `retire-intent.json` and `retired.json`, policy
`cif-complete-attempt-working-retirement-v1`. Original request, attempt, result,
finished and checkpoint schemas/identities remain unchanged. Older readers reject
new storage records; untouched requests retain their behavior. Changed code is
`cif_attempt_retention.py`, with a separate retirement regression file. The existing
22-case retention suite remains intact. Overlapping storage documentation has been
consolidated into one current contract, keeping historical anchors and Git evidence.

## Validation

- **35 focused cases, 233.28 s:** initial retirement cases plus all C257 read cases.
- **3 targeted cases, 21.64 s:** recovered-archive flush failure and changed archive/
  working-file guards; **1 final intent-race case, 6.54 s**.
- **1 moved-checkout/moved-request case, 9.93 s:** final source, fully retired exact
  read and repeat retirement; old temporary checkout/request paths absent.
- Actual C244 native evidence, copied: interrupt after **17** removals, read while
  partial, resume product cleanup, then exact read. **604 duplicates / 163,424,933 B**
  retired; whole request **33,661,526 B / 98 files** versus **181,566,343 B / 698**.
  Same model, five PHILs/two CIFs, **51** persistent paths. All original file bytes/
  timestamps unchanged; old request reads/native execution forbidden. Temporary
  copy removed. Archive expansion peak **87,440,990 B** (128 MiB limit), Python
  peak **752,664,576 B**, total **527.33 s**.

The native-copy probe began before the final archive-sync/completion-intent
hardening; the latter has explicit failure controls and the final relocated positive
control above. It changes no chemistry, archive bytes, selection or public paths.
No native process remains. Exact commands/hashes/sequence:
`working_attempt_retirement_2026_11_13` in the existing ledger. Runners/summaries
are in the everyday checkout's ignored `branch-artifacts/cedar/runners/c258_*`.
Generated scientific data and runners are deliberately excluded from Git.

No full suite this pass. Last wholly green full: **C220/583d30df, 9,178 tests +
276 subtests**. Full integration validation remains required before merge.
Archived Phenix evidence uses **2.2.1-6174 / dispatcher 2.2.1**; no new Phenix/Coot
execution or diffraction-refinement claim belongs to this storage checkpoint.

## Next — Q04/Q05 closure

1. Connect successful-attempt storage to normal callers without allowing optional
   storage failure to discard usable science. Check campaign ownership/receipt
   boundaries first. Complete representative campaign disk/temporary-memory
   acceptance. Reuse C258; do not rebuild transport, reader or retirement machinery.
2. Qualify C253 chosen-model AutoSol natively. The earlier real DiU result has
   anomalous data and a matching 1AP/5IU construct; its original AutoSol took 18.29 s.
   Prepare a fresh owned control from its exact upstream Phaser result/inputs,
   preserving all originals, and obtain genuinely checked preparation before
   chosen-model phasing. Do not use the C252 synthetic reflection/map fixture as
   native phasing evidence. Interrupted AutoSol result saving remains distinct from
   preparation publication recovery: outputs are kept, not automatically adopted.
3. Q06 actual complete-restraint diffraction refinement, then Q07 combined and
   held-out examples. Q08–Q14 retain earlier chemistry learning. The supported
   Q04/Q05 estimate is now roughly **1–3 further implementation patches plus
   native/integration validation**, not the entire catalogue programme.
4. Q16 includes final AutoPhase naming under the pinned audit, full regression,
   integration review and honest release scope. No merge authorized.

Earlier this pass: C253/f337660 chosen-model AutoSol reference (native acceptance
open); C254/39c5ae0 bounded outer view; C255/aef7911 exact Alder HL-label fix;
C256/ebc9ccf complete archive; C257/ecafc98 ordinary archive reads. Their exact
validation remains in the ledger and immutable commits, not a second diary here.
Linden works independently on Willow/Pine TopoStitch. Native audit-interface
advice was shared locally, signed Rowan; no cross-branch or shared-environment edits.
Protected NASolve-cedar and everyday NASolve/pine science, patches and environments
remain untouched. Continue on NASolve-c96/cedar; no new branch.
