# NASolve development handoff — current state

Updated **2026-11-12**, C226. Active branch **cedar**, checkout `NASolve-c96`.
Base: `7edc95b2a0703c6c16ff5cbf55804102ef4858ca`. The
[scientific queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Use laboratory language first. No merge authorized.

## Q05 checkpoint published — campaigns retain the checked preparation

**Before → after:** schema-2 presets can explicitly set
`postmr.checked_preparation = true`. Planning freezes and validates the choice;
the campaign uses C224's ordinary checked caller and C223's exact publisher.
The stage collects the genuine preparation receipt/evidence and actual ReadySet
outcome, including an independently checked retained model without a fictional
log. The checkpoint remains REVIEW; this is not diffraction-refinement success.

Omitted fields retain old policy fingerprints and legacy preparation. Schema 1
refuses the field; older stage implementations reject the expanded policy. No
new owner, unchecked fallback, chemical threshold or artifact schema. Completed
campaign receipts resume normally. Interrupted stages preserve all evidence;
explicit campaign retry starts a new run after prior processes are known stopped.
Standalone recovery does not retrospectively manufacture a campaign receipt.

**Files:** four existing campaign/preset modules and three existing test modules;
existing guides, queue, descriptor and changelog. **Validation:** 7 fail-before
cases; final affected campaign/preset/publication checks pass **295 tests + 59
subtests in 26.80s**. One initial test expected a raw interruption error instead
of PostMR's documented wrapped error; corrected, with preserved-receipt recovery
passing. Frozen recipe relocation is checked after the original path/preset are
gone. No full suite or fresh scientific Phenix/Coot execution. Test doubles and
fixture executables establish caller behavior, not new chemical support.

Exact command/results/hashes: ledger key `checked_campaign_preparation_2026_11_12`.
Local logs: `live_tests_directory/225_Cedar_checked-campaign-tjtzjeg9`.
Use Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`.
Last entirely green full revision remains C220/`583d30df`; C222's later full-run
CLI failure and focused correction remain recorded. Generated logs/science are
excluded from Git. Tests completed; no native/GUI worker is active.

## Current Q04 checkpoint — replayable chemical-plane calculations (C226)

Base C225/`7edc95b`. The new `cif_captured_plane_attribution.py` and focused test
module join C213/C214 owned source/capture proof to C215's whole-plane numerics.
One bounded process rebuilds both fixed managers using maintained code, checks
exact native/effective-PHIL output, and evaluates complete old/new groups.
The caller uses the existing repair runner; no new owner or chemistry thresholds.
A read-only relocated replay rederives every claim without the original SDK/code.
Schema: `cif-captured-owned-plane-attribution-v1`; old artifacts are unchanged.

**Validation:** missing-API fail-before; **114 focused tests pass**, including 30
adapter cases. Actual Phenix **2.2.1-6174 / dispatcher 2.2.1** passes PDU/5PC with
four full fixed-manager rebuilds in two owned jobs, both STOPPED. Cold source/evidence
relocation passes with 141 files unchanged and original paths/SDK/processes denied.
First native attempt exposed omitted regenerated PHIL outputs; exact captured-byte
checks fixed accounting and a fresh attempt passed. Earlier partial evidence stays.
No new derivatives, geometry optimization, Coot, ReadySet, refinement or full suite.
Controls have zero parallelity and no special positions; no broader support claim.

Exact commands/results: ledger `maintained_plane_attribution_2026_11_12`;
local capsule `live_tests_directory/226_Cedar_owned-plane-numerics-mceapmbq`.
Generated models/CIFs/logs/runners remain local. No native/GUI job is active.

## Continue the bounded push — finish Q04/Q05 before Q06

Work window began 19:46 UTC and ends about 22:46 UTC; no full suite. C225 is
published (`7edc95b`); C226 is ready for publication. Next compose the maintained
plane evidence into existing source-bound selection/publication and automatic
repair. Prior review confirms the current owner/selector still supports only
linear-torsion repair; do not call C226 automatic plane adoption.
Preserve separate ring planes, NAR stacking selections, source authority and
independently checked fallback. Q05 still needs later preparation children without
replacing earlier choices. Q06/Q07 stay queued until Q04/Q05 are finished.

## Preserve local evidence

Keep earlier runners/build evidence and protected `NASolve-cedar` at `e7451eed`
with its local `phaser.py` change and unpublished data. Everyday pine and metal
work remain separate. Never clean partial runs, environments or unrelated files.
The current queue and handoff are edited in place; history/evidence remain in Git.

— Rowan · Codex desktop
