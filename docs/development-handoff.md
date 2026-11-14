# NASolve development handoff — current state

Updated **2026-11-14**, C273 bounded inspection improvement. Active **cedar**,
NASolve-c96; base before this patch is C272 `35f12d9`.
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

## Completed — faster exact inspection, unchanged science

C273 lets one exact request read reuse only identical pure numerical calculations.
Every artifact/source/owner/qualification check still runs. Scope is temporary,
limited to sixteen small verdicts, discarded on success/error; changed inputs
recalculate and exceptions never cache. Historical worker bytes remain identical.
C231/C250 history sharing and C254/C256 bounded object sharing remain the owners
of their different jobs; no second scientific validator or persistent trust cache.

Validation: 205 focused checks pass, then 19 final-code checks in a relocated
checkout pass (including order/type distinctions, warm-evidence tampering and
scope disposal). Saved native C270 reads in fresh guarded processes take 103.72 s
without reuse and 59.04 s with it; fourteen numerical replays become two. Exact
view and all 389 file bytes/timestamps agree. Python peaks: 716.6/635.8 MB. No new
native calls, chemistry changes or scientific copies. Single-pair timing only.
Local control `273_Cedar_read-cost-617w29jd` is stopped, source unchanged. Commands,
hashes, revision details and limits: `inspection_local_numerical_reuse_2026_11_13`.

## Next — finish saving phasing work safely after interruption

Q04/Q05 are not declared closed. Successful preparation/phasing/inspection now
has native acceptance. The remaining concrete recovery boundary is AutoSol's
stage-result save followed by guarded run-report publication: interruption can
leave completed outputs unadopted. Direct AutoSol lacks standalone durable child
ownership; campaign outer-worker ownership is separate. Reuse existing owners,
locks and immutable result checks for future owned runs; do not put native children
outside a campaign's tracked ownership or infer process death from a saved file.
Old unowned partial outputs stay preserved/unadopted. No in-place native retry.
Inspect `autosol._record_result`, `execute_autosol`, `campaign_stages`, the existing
campaign process owner and selected-reference conflict tests before implementation.
This boundary audit is recorded in `q04_q05_remaining_boundary_audit_2026_11_13`.

Keep one expensive reader at a time. Single successful/failing requests are
measured; repeated-failure/100-dataset bounds, historical campaign migration and
default activation remain explicit scope/release limits. Q06 actual full-restraint
refinement follows Q04/Q05 reconciliation. Q07 mixed/held-out chemistry and Q08–Q14
retained chemistry learning stay queued; charged 1AP leaving-port authority is Q13.
Q15 reporting and Q16 AutoPhase compatibility naming/full integration review
remain later. No merge or new native refinement tonight.

Last full suite: **C220/583d30df, 9,178 tests + 276 subtests**. Subsequent focused
validation is recorded in the ledger; this is not a current full-suite claim.
Linden works on Willow/Pine; ordinary bond-edit exclusion changes must not be
confused with additive contact energy. Reported Willow evidence is attributed,
not a combined-build validation. Everyday NASolve/pine and protected local science
remain untouched. Signed inter-agent handoffs: **— Rowan**.
