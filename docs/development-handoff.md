# NASolve development handoff — current state

Updated **2026-11-12**, C224. Active branch **cedar**, checkout `NASolve-c96`.
Base: `0366d7f9ac246c8e4d2d22a05c67a7a1210d2e43` (C223).
The [scientific queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Use laboratory language first. No merge is authorized.

## Current checkpoint — checked preparation through ordinary PostMR

**Before → after:** `postmr RUN --checked-preparation` now constructs once,
executes one attempt through the existing owner and saves the exact checked model
and restraints as the initial REVIEW checkpoint. A verified fallback after optional
ReadySet failure remains usable. The CLI reports the actual outcome and real
preparation receipt, without inventing a legacy ReadySet log.

The default PostMR and campaign routes are unchanged. Shared installation checks
reject conflicting dispatchers/environments before preparation writes. Missing
qualification stops the dependent step while preserving its evidence; no unchecked
second preparation is attempted. An interrupted save finishes through the existing
exact publication command. An existing partial PostMR directory cannot be rebuilt
in place. No chemical thresholds, OP3 intent, Free-R or NARestraints rules changed.

**Files/schema:** `postmr.py`, `cif_ordinary_postmr.py`, `cli.py`, the existing
PostMR runtime test module and maintained docs. No new saved schema: C223's
checksummed preparation receipt/checkpoint schema 3 is reused. The live
`PostMRResult.readyset_log` is optional on the checked route; its additive
`readyset_status` reports the actual outcome. Legacy explicit-path callers work
as before; the checked API requires a selected Phenix installation.

**Validation:** nine fail-before cases; 196 affected tests + 34 subtests pass.
Final ordinary-PostMR controls pass **20 tests**, including the last added
no-rebuild control; smoke passes **139 tests + 6 subtests**. Source hashes stayed
unchanged during the final checks. All 668 Python files compile without warnings
or bytecode. No full suite and no fresh scientific Phenix/Coot execution.
Tests use controlled constructor/executor seams and test executables; this is
caller/recovery evidence, not new chemical or diffraction-refinement qualification.

Exact commands, results and hashes: ledger key `ordinary_checked_postmr_2026_11_12`.
Local capsule: `live_tests_directory/224_Cedar_ordinary-checked-postmr-lx_vcv3s`.
Use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, Python 3.12.14.
C223's saved PDU/native-source relocation evidence is reused; its synthetic
observation/map fixtures do not prove MTZ interpretation. C223's workflow profile
passed 2,230 tests + 45 subtests. C220/`583d30df` remains the last entirely green
full revision; C222's full-run CLI failure and focused correction remain recorded.
See the [C223 handoff](https://github.com/vecchioni-lab/NASolve/blob/0366d7f9ac246c8e4d2d22a05c67a7a1210d2e43/docs/development-handoff.md).
No native/GUI job is active; validation commands completed. Generated outputs,
logs and local receipts are deliberately excluded from Git.

## Next — use the same result in campaigns

Q05 remains open for campaign mode/receipt integration and later preparation
children. Freeze the preparation choice in campaign intent; use the genuine
preparation receipt when no legacy ReadySet log exists. Reuse the shared
constructor/executor/publisher and existing recovery owner. Keep default behavior
compatible, never reconstruct partial work or replace an immutable earlier choice.

Q04 still needs general plane-repair composition; reuse C208–C216. Q06 is real
complete-restraint refinement. Q07 combines the mixed scaffold with ATL alongside
and the separate unfamiliar-ligand challenge. Q08–Q16 retain chemistry/coverage/
reporting/release work. PDU plane completeness, DP ambiguity, source-H/charge and
nonstandard-backbone qualification remain explicit limits. The new option does
not broaden checked-route chemical eligibility or make catalogue-wide promises.

## Preserve local evidence and continuity

Keep C220's archived runner/build evidence. Preserve `NASolve-cedar` at
`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, its local `phaser.py` change and
unpublished data. Everyday pine and metal work remain separate. Never clean raw
runs, partial outputs, environments or unrelated files. The current queue and
handoff are edited in place; older decisions remain in Git and the evidence ledger.

— Rowan · Codex desktop
