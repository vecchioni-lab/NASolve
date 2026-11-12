# NASolve development handoff — current state

Updated **2026-11-12**, C221. Active branch **cedar**, checkout `NASolve-c96`.
Base for this change: `583d30df9c2bb8fd76e802e0eaa51d749c2b6eeb` (C220).
The [scientific queue](cif-doctor-completion-queue.md) owns the work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Use laboratory language first. No merge is authorized.

## Completed checkpoint: C221

Prior review: Q05 already requires exact selected model/CIF/PHIL handoff. C220
provides truthful preparation result and continuation commands. Before publishing
those results as ordinary checkpoints, inspection must protect all their inputs.
A concrete gap existed: Coot's checkpoint view skipped unresolved non-CIF files,
although refinement resolves its recorded restraint references.

**Before → after:** missing/changed pair or stacking PHIL now stops inspection,
as does damage to a modification-only CIF. Every recorded restraint uses the
existing path/checksum reader before display filtering. Exact selected checkpoint,
dictionary order and duplicate entries are preserved. No new proof/owner layer.

**Changed files/schema:** `coot_view.py`, new `test_checkpoint_view_integrity.py`,
changelog and maintained docs/ledger. No saved schema or chemical-policy change.
Malformed recorded lists/entries now refuse; legacy omitted/null lists and
unchecksummed schema-1 references retain their existing meaning. No native
Coot/Phenix execution, model editing, default adoption or refinement claim.

**Checks:** nine genuine fail-before cases; **124 affected tests + 56 subtests**
and **139 smoke tests + 6 subtests** pass. The relocated synthetic older-checkpoint
control passes after the original directory is removed; bytes and timestamps stay
unchanged. An initial test attribute typo and a diagnostic-wording regression were
corrected and retained in the local logs. Full suite was not repeated for this
local view-reader change; the last full baseline is **C220/583d30d: 9,178 tests +
276 subtests**. No validation worker remains active.

Commands use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` with the existing Python
3.12.14 environment. Affected pytest files: checkpoint-view integrity, Coot view,
checkpoints, CLI, Coot anomalous maps and AutoRefine; profile: `scripts/run_tests.py
smoke`. Exact commands/log hashes are recorded in the existing evidence ledger,
`checkpoint_view_restraint_integrity_2026_11_12`; local capsule:
`live_tests_directory/221_Cedar_checkpoint-restraint-integrity-mjnxp38t`.
No generated scientific artifacts or logs are committed.

## Next: publish the exact checked preparation as an ordinary checkpoint

Q05 remains open. Use the existing exact request reader to carry one chosen
model and its ordered dictionaries/PHIL into reports and checkpoints. Preserve
its request/attempt and construction/compiler evidence, truthful pre-ReadySet
fallback labels, and recovery after interrupted publication without another
native attempt. Validate the saved binding on later inspection/refinement reads,
not only at creation. Coot and refinement have different display/usability needs;
share the evidence validation without preventing inspection of failed results.

Q04 still needs general plane-repair composition; reuse C208–C216 rather than
recreating it. Q06 is actual complete-restraint refinement; Q07 combines the mixed
scaffold plus ATL and the separate unfamiliar-ligand challenge. Q08–Q16 retain
sugar/hand/PNA/catalogue/state-authority/reporting/release work. PDU C5 geometry
alone does not prove complete plane coverage. Keep DP and source-H/charge limits.

## Preserve local evidence and continuity

C220 retired 89 audited build copies, archived 1,353 older runners with byte
verification, and consolidated four duplicate test cases without losing distinct
coverage. Exact audit and archive remain in its local C220 capsule. The preserved
`NASolve-cedar` checkout at `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, including
its authorized local `phaser.py` change and unpublished data, remains untouched.
Everyday pine and metal-coordination work remain separate. Never clean raw runs,
partial outputs, environments or unrelated local material.

The [C220 handoff](https://github.com/vecchioni-lab/NASolve/blob/583d30df9c2bb8fd76e802e0eaa51d749c2b6eeb/docs/development-handoff.md)
and older linked history retain prior evidence. Consult them before reopening an
old problem. No unfinished bounded implementation or active job remains here.

— Rowan · Codex desktop
