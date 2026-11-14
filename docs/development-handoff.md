# NASolve development handoff — current state

Updated **2026-11-14**, C275 ordinary-command recovery. Active **cedar**,
NASolve-c96; base before this patch is C274 `6403407`.
Simon authorized **12:36–14:36 Europe/London, 14 November**. Focused checks only;
no full suite, new branch or merge. Finish Q04/Q05 before Q06. The
[queue](cif-doctor-completion-queue.md) owns ordering.

## Completed — the ordinary command returns the exact saved result

C275 checks for C274's receipt before Phenix discovery when the user requests
`nasolve autosol RUN`. It uses the same completion/validation owner, reports no
native rerun, and never falls through after invalid/active/conflicting evidence.
Absent receipts retain prior fresh-launch/refusal behavior. Completion-only mode
still requires a receipt. Execution API and campaign-stage caller are unchanged.

Validation: 145 focused tests + 16 subtests in 28.79 s. Before the change the new
ordinary-command regression failed on SDK discovery. The final CLI reads real
relocated C274 without SDK/old/source access or subprocess calls: 57.41 s, all 392
files unchanged. Source pins and exact commands are in evidence-ledger entry
`autosol_cli_completion_2026_11_14`. No schema, migration or new native execution.

## Completed — finish saving phasing work after interruption

C274 adds `nasolve autosol RUN --complete-publication`. New checked AutoSol runs
record their existing producer/inherited group before launch, then seal the exact
completed result and previous/intended run report. Completion reuses preparation,
site/phase checks and the existing lock/guarded writer. Both producer and entire
group must be known stopped before a pending save; already exact completion is
read-only. Later checkpoint selections survive. No native discovery or rerun.

Two additive small records: `AutoSol/execution.json` and `publication.json`;
policies `autosol-inherited-process-observation-v1` and
`autosol-result-publication-v1`. Native commands, group ownership, scientific
thresholds and old result meanings stay unchanged. Old partial runs are not
retrofitted. No new campaign-stage receipt is fabricated.

A fresh complete Phenix 2.2.1-6174 AutoSol control deliberately interrupts after
sealing: AUTOSOL_READY, 1.449 Å, HLAM/HLBM/HLCM/HLDM. After verified worker/group
stop and moving the copy, completion passes without old/source/SDK reads or native
launches. Saved comparison remains manual-001; later current stays postmr. Only
report.json changes, persistent publication lock appears, 390 other existing files
retain bytes/timestamps. Repeat is read-only. All 394 original source files remain
unchanged. Both workers stopped and code stayed pinned. Coot was not run.

Control `274_Cedar_autosol-publication-tc0cilcn` in live-tests holds 61.6 MB / 413
files. It copies/revalidates C270 preparation and resets only its own old AutoSol
state before a fresh launch: derived test fixture, not production migration or
in-place retry. No new MR/ReadySet or diffraction refinement. Scientific files and
runner remain local, excluded from Git.

Validation: 136 focused tests + 16 subtests in 26.28 s. Final concurrent-report
rollback guard: 26 tests in 8.81 s and 26 in 9.00 s from a relocated checkout
after its old path is gone. Native control precedes that two-line read guard;
no native behavior changed or rerun is claimed. Before implementation,
CLI regression failed on the missing option. Exact commands, changed files,
compatibility, negative controls and local source/result hashes:
`autosol_saved_publication_2026_11_14` in the evidence ledger.

## Reuse completed evidence; do not rebuild its machinery

C270 native Phaser/Coot/NAR/plane repair/ReadySet/AutoSol passes for the explicit
A:5IU/free-end fixture, seven restraints, protected OP3 at D:1. This uses real DiU
observations but is not donor-chemistry or diffraction-refinement acceptance.
C271 fills the saved AutoSol view/checkpoint identity. C272 native Coot 1.3.3
loads the final dictionary, comparison/HA models and FWT/PHWT map. Cold relocated
inspection preserves all 389 files and later choice. Original diagnostic failures
remain preserved; details and exact claims are in their evidence-ledger entries.

C273 bounds reuse of identical pure numerical calculations within one inspection.
Every artifact/source/owner/qualification check remains; no persistent trust cache
or historical worker-byte change. One saved-native comparison falls from 103.72 s
/ fourteen calculations to 59.04 s / two, with identical view and unchanged files.
Python peaks 716.6/635.8 MB; single-pair measurement, not a general speed guarantee.
Keep one expensive reader at a time. Earlier C258/C260 retirement and C251/C252
alternative-publication machinery remain the owners of those completed jobs.

## Next — reconcile the remaining recovery and rollout boundary

Q04/Q05 are not declared closed. C274 completes sealed saves only. Crashes before
sealing, unfinished native work, shared/foreign/unknown groups and missing outer
campaign receipts stay preserved/unadopted. Direct AutoSol still lacks standalone
isolated child ownership. Campaign inherited supervision is unchanged; do not
move native work outside its tracked group. No guessed stop or native retry in place.
Normal CLI reuse is now connected. Explicitly reconcile the remaining limits
with the supported opt-in route before Q06; avoid a parallel recovery stack.

Single successful/failing requests are measured. Repeated-failure/100-dataset
bounds, historical campaign migration and default activation remain explicit
scope/release limits. Q06 actual full-restraint refinement follows reconciliation.
Q07 mixed/held-out chemistry and Q08–Q14 retained chemistry learning stay queued;
charged 1AP leaving-port authority is Q13. Q15 reports and Q16 AutoPhase naming,
full integration validation and reviewed merge remain later. No automatic merge.

Last full suite: **C220/583d30df, 9,178 tests + 276 subtests**; not a current pass.
Linden works Willow/Pine, separately qualifying TopoStitch periodic-policy behavior;
reported Willow findings are not combined-build validation. Ordinary bond edits
and additive contact energy stay distinct. Everyday NASolve/pine and protected
local science remain untouched. Signed inter-agent handoffs: **— Rowan**.
