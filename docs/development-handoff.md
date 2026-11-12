# NASolve development handoff — current state

Updated **2026-11-12**, C225. Active branch **cedar**, checkout `NASolve-c96`.
Base: `b69bc3170af5dc7fdcbde36baf581d0506eb0f23`. The
[scientific queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Use laboratory language first. No merge authorized.

## Current checkpoint — campaigns retain the checked preparation

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

## Active push — Q04 chemical-plane repair, then remaining Q05

Started 19:46 UTC, bounded to about 22:46 UTC, no full suite. C225 is ready for
publication. Prior-work review: C208–C214 already provide graph-selected candidate,
owned support and exact native-capture gates. C215's whole-plane energy check is
pure; its kernel execution authentication is local experimental evidence, not a
maintained replayable execution reader. C216 measures geometry separately.

Next close that numerical-evidence handoff using the existing process runner,
then compose it with the existing repair owner/selection. Do not replace the
whole multiple-plane generated CIF. Preserve ring planes and NAR's stacking
selections; only supported intramolecular members may be added. No automatic
plane-repair claim until selection/publication and ordinary invocation are joined.
Q05 still needs later preparation children without replacing earlier choices.
Q06 real refinement and Q07 mixed/held-out chemistry stay queued.

## Preserve local evidence

Keep earlier runners/build evidence and protected `NASolve-cedar` at `e7451eed`
with its local `phaser.py` change and unpublished data. Everyday pine and metal
work remain separate. Never clean partial runs, environments or unrelated files.
The current queue and handoff are edited in place; history/evidence remain in Git.

— Rowan · Codex desktop
