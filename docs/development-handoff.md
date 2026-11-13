# NASolve development handoff — current state

Updated **2026-11-13**, C272 native consumer/closure consolidation. Active **cedar**,
NASolve-c96; product HEAD before this documentation is C271 `cedc28d`.
Simon extended work to **00:30 Europe/London, 14 November**. Focused checks only;
no full suite, new branch or merge. Finish Q04/Q05 before Q06. The
[queue](cif-doctor-completion-queue.md) owns ordering.

## Completed checkpoint — the chosen result reaches AutoSol and Coot

C269 `f2345a8` preserves actually observed phosphate names under explicit native
context v4 without changing chemistry or pinned numerical workers. Native C270
passes Phaser, Coot/NAR construction, original/repaired derivatives, plane repair,
ReadySet/native endpoint and AutoSol: `POSTMR_READY`, `AUTOSOL_READY`, 1.449 Å
site match, HLAM/HLBM/HLCM/HLDM phases, seven restraints and OP3 retained at D:1.
This is an explicit A:5IU/free-end fixture using real DiU observations, not donor
chemistry or diffraction-refinement success. Whole retained request: 35,122,742 B
/ 168 files, including shared acquisition and continuation.

Two stopped diagnostic failures remain preserved: the first driver used the wrong
checkpoint attribute after native success; followthrough-001 exposed missing view
checkpoint metadata. C271 fixes that existing field, with 68 tests + 23 subtests
and two moved-checkout checks. No native rerun was needed.

C270 followthrough-002 now PASSES: current postmr does not replace the saved
manual-001 AutoSol comparison. The run is under
`270_Cedar_selected-autosol-pspkne9n/relocated/DiU/AutoMR/run_001` in live-tests;
its original path is gone. Guarded cold reading forbids original/cache/SDK reads
and native calls; all 389 run files keep bytes/timestamps. Original input bytes
match frozen inputs, and five originals remain unchanged during followthrough.
The failed initial driver did not persist pre-native timestamp baselines; do not
claim retrospective timestamp comparison. Full diagnostic control is about 62.3 MB.

C272 `272_Cedar_native-coot-consumer-us_fv7b_` passes actual headless Coot 1.3.3
loading of copied final display inputs: dictionary return 41, comparison and HA
models, FWT/PHWT map via ordinary --auto. All 389 original files remain unchanged.
No model edits, optimization, effective-plane or diffraction-refinement claim.
Both controls stopped cleanly, source unchanged. Exact commands/hashes/results:
evidence ledger `native_selected_autosol_2026_11_13` and
`native_coot_final_consumer_2026_11_13`. Raw science/scripts stay local.

## Next bounded work — make inspection practical without weakening evidence

An ordinary selected-view read takes about 99 s. cProfile cold read takes 302.9 s
(overhead included), with 630.7 MB peak Python memory. Seven repaired-bundle
inspections repeat fourteen mixed-gradient replays; deepcopy and repeated vector
norms dominate. Existing C231/C250 request-wide history reuse and C254/C256 bounded
archive object sharing already solve different duplication problems. Reuse them.

Investigate narrowly scoped reuse of identical pure numerical validation within
one exact request read. Every file/source/owner binding must still validate; changed
inputs must recalculate, and failed validations must not be cached. No persistent
trust cache. Do not edit historical numerical worker bytes: they are compared
exactly during old evidence replay. Record speed and unchanged outcomes against
this stopped saved C270 result, without new native work or scientific modification.

Then reconcile Q04/Q05 scope explicitly: supported opt-in preparation, preserved
but not automatically adopted interrupted AutoSol publication, historical campaign
migration and measured serial resource use. Repeated-failure/100-dataset bounds
remain unproven. Q06 actual complete-restraint refinement follows; Q07 mixed and
held-out chemistry and Q08–Q14 retained chemistry learning are not dropped.
Q13 still owns charged 1AP leaving-port authority. Q15 reporting and Q16 AutoPhase
compatibility naming/full integration review remain later. No automatic merge.

Last full suite: **C220/583d30df, 9,178 tests + 276 subtests**. Subsequent focused
validation is recorded in the ledger; this is not a current full-suite claim.
Linden works on Willow/Pine; ordinary bond-edit exclusion changes must not be
confused with additive contact energy. Reported Willow evidence is attributed,
not a combined-build validation. Everyday NASolve/pine and protected local science
remain untouched. Signed inter-agent handoffs: **— Rowan**.
