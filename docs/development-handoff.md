# NASolve development handoff — current state

Updated **2026-11-12**, C222. Active branch **cedar**, checkout
`NASolve-c96`. Base for this change: `6c87f6b7f272b34effd97bfeaa9329f5508bb0fb` (C221).
The [scientific queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Use laboratory language first. No merge is authorized.

**Testing cadence after C222:** subsequent bounded Cedar pushes use affected
tests and the relevant focused profile. Retain this full-run evidence and its
focused correction; defer the next full regression to an integration checkpoint.

## Completed checkpoint: inspect an exact checked preparation

Prior review: C181–C184 already retain independently verified parents after
optional ReadySet failure; C220 exposes that exact result, and C221 checks every
checkpoint restraint before display. Reuse these, not another chemistry engine,
validator or process owner. Q05 publication remains larger work; this bounded
step makes the existing result useful for inspection before checkpoint adoption.

**Before → after:** `show RUN --preparation-attempt N` now opens that attempt's
checked model and matching ordered CIFs, including a retained safe fallback.
It states the actual ReadySet outcome and uses the original Phaser map, explicitly
not recalculated for this model. It never substitutes a newer selected checkpoint.
The exact reader validates PHIL and modification CIFs before display filtering.
Missing trustworthy preparation/map evidence prevents this view; saved results
remain available. Optional improvement failure does not erase a usable result.

**Files/schema:** `coot_view.py`, `cli.py`, preparation-view/CLI regressions,
maintained docs and evidence ledger. No scientific saved schema or chemistry
change. Additive optional view arguments/dataclass fields; the local Coot launch
receipt names the preparation attempt. Existing show/default refinement behavior
and checkpoint selection stay unchanged. No migration.

**Validation:** 18 genuine fail-before cases; initial affected checks pass
(118 tests + 37 subtests), as does smoke (139 + 6). The full run on battery took
**2,191.90s**: **9,210 tests + 273 subtests passed**, with three tests and three
subtests failing in the same Refine Doctor→Coot handoff. The newly optional
`preparation_attempt` field was absent from that older internal caller. A one-line
absent-option default fixes it; **124 affected tests + 40 subtests pass**, including
every failed case. Only `cli.py` changed after the frozen full run. No full repeat;
C220/583d30d remains the last entirely green full-suite revision. Do not relabel
this as a fully green C222 regression.

Actual C219 PDU evidence passes after relocation: all 1,497 files retain bytes and
timestamps, with historical paths, SDK reads and execution denied. Both CIFs and
five PHIL files verify; the phosphate modification CIF is correctly omitted from
Coot's component display. The initial cold-test expectation was corrected; its
original failure log is retained. The map-path fixture is synthetic, not a native
MTZ. No fresh Coot/Phenix scientific execution or refinement claim.

Exact commands/results/hashes are in the existing ledger key
`exact_preparation_view_2026_11_12`. Python 3.12.14; all checks use
`PYTHONDONTWRITEBYTECODE=1` and the checkout's `src` on `PYTHONPATH`.
Local capsule: `live_tests_directory/222_Cedar_exact-preparation-view-y4dee6dg`.
Full/cold workers are verified stopped; no active native/GUI job remains.
No generated models, restraint files, maps, logs or receipts are committed.

## Next: publish the exact choice as an ordinary checkpoint

Q05 remains open. Carry the existing exact result into ordinary reports and
checkpoints with its request/attempt and construction/compiler evidence, truthful
fallback labels, and interrupted-publication recovery without a native rerun.
Validate the saved binding on later reads. Inspection and refinement have different
usability needs; do not promote diagnostic preparation into refinement readiness.
Before adoption, reject malformed inherited restraint entries rather than silently
skipping them (`checkpoints._inherited_paths`); C221 already protects viewing.
Preserve intentionally empty legacy lists. Later refined/manual models must retain
the preparation ancestry without being required to equal the original coordinates.
A failed optional repair must leave checked fallbacks and unrelated work available.
If no trustworthy model/restraint combination remains, block the dependent step
and retain its evidence and recovery options.

Q04 still needs general plane-repair composition; reuse C208–C216. Q06 is actual
complete-restraint refinement; Q07 combines the mixed scaffold plus ATL and the
separate unfamiliar-ligand challenge. Q08–Q16 retain sugar/hand/PNA/catalogue/
state-authority/reporting/release work. PDU C5 geometry alone does not prove plane
coverage. Keep DP and source-H/charge limits.

## Preserve local evidence and continuity

C220's audited build retirement and runner archive remain in its local capsule.
Preserve `NASolve-cedar` at `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, its
local `phaser.py` change and unpublished data. Everyday pine and metal work remain
separate. Never clean raw runs, partial outputs, environments or unrelated files.
The [C221 handoff](https://github.com/vecchioni-lab/NASolve/blob/6c87f6b7f272b34effd97bfeaa9329f5508bb0fb/docs/development-handoff.md)
and its linked history preserve prior validation and cleanup evidence.

— Rowan · Codex desktop
