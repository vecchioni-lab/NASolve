# NASolve development handoff — current state

Updated **2026-11-12**, C223. Active branch **cedar**, checkout `NASolve-c96`.
Base: `d66dc4a6c785f030204260ef697646ecbe09fc80` (C222).
The [scientific queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Use laboratory language first. No merge is authorized.

## Current checkpoint — keep a checked preparation together in normal use

**Before → after:** `cif-doctor publish-preparation RUN --attempt N` now saves
that exact checked model and ordered restraints as the initial **REVIEW** checkpoint.
A verified fallback remains usable after optional ReadySet failure, with the
actual outcome reported. Ordinary inspection, trial refinement and AutoSol check
the same original evidence. Preparation is not successful diffraction refinement.

An interrupted save resumes the same choice under the existing request lock,
without rerunning Coot/ReadySet or replacing earlier work. Repeating a completed
save cannot reset a later selected checkpoint. Later models retain the ordered
restraints and recorded phosphate connections while coordinates may move.
A regression demonstrated that a severed phosphate link previously passed ordinary
model validation; the existing connectivity audit now catches it. No chemical
thresholds, OP3 permission, Free-R rules or NARestraints ownership changed.

**Files/schema:** new `cif_postmr_publication.py`; small changes to the existing
ordinary result reader, checkpoints, Coot, AutoSol, CLI and model/phosphate checks;
one regression module and its workflow-profile registration. These explicitly
published runs use checkpoint schema **3**, an immutable checksummed
`PostMR/report.json`, and compact `checked_model_topology`. Legacy schema 1/2 runs
retain their meaning. Older checkpoint readers reject schema 3. No conversion or
overwrite of an existing PostMR choice/registry is supported.

**Validation:** final affected checks pass: **294 tests + 48 subtests**, with
source hashes unchanged during the run. All 668 Python source/test/script files
compile without warnings or bytecode output. The earlier focused workflow profile
passes **2230 tests + 45 subtests**; the final affected run covers the
subsequently added connectivity guard. A final wording clarification passes 57
command/result/publication cases. Saved real PDU evidence passes publication and
cold relocation, with 1,501 files unchanged and original paths/SDK/execution denied.
Its two CIFs, five PHIL files and checked phosphate connections remain intact.
No full suite this pass, per Simon's testing cadence. C222's full run exposed one
CLI compatibility bug, corrected by its focused follow-up; C220/`583d30df` remains
the last entirely green full-suite revision. See the
[C222 handoff](https://github.com/vecchioni-lab/NASolve/blob/d66dc4a6c785f030204260ef697646ecbe09fc80/docs/development-handoff.md)
for that exact full-run scope.

Evidence and exact commands: ledger key
`checked_preparation_publication_2026_11_12`; local capsule
`live_tests_directory/223_Cedar_checked-preparation-handoff-zszq2aif`.
Use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`; Python 3.12.14.
No fresh native Phenix/Coot scientific execution: ordinary refinement uses test
executables; the real PDU control reuses C219 proof with synthetic observation/map
path fixtures. No MTZ interpretation or diffraction-refinement claim.
Generated scientific files, logs and local receipts are deliberately excluded
from Git. Both replay workers are verified stopped, and the workflow/affected test commands
have completed. No native or GUI job remains.

## Next — let normal preparation use this same handoff

Q05 remains open for ordinary PostMR/campaign entry and later preparation-child
adoption. Reuse this publisher, the existing request owner and exact reader.
The campaign PostMR caller still requires a ReadySet log from every result; a
verified fallback must instead carry its actual preparation receipt. Freeze the
mode in campaign intent, preserve default compatibility, and do not rerun Coot
on partial work. Do not invent another chemistry or recovery framework.

Q04 still needs general plane-repair composition; reuse C208–C216. Q06 is real
complete-restraint refinement. Q07 combines the mixed scaffold with ATL alongside
and the separate unfamiliar-ligand challenge. Q08–Q16 retain chemistry/coverage/
reporting/release work. Near-planar PDU coordinates do not establish plane coverage.
DP ambiguity, source-H/charge limits and nonstandard-backbone qualification remain.
The exact proof reader is still costly on the large PDU control; this patch avoids
double replay within each ordinary read, but does not claim a performance cure.

## Preserve local evidence and continuity

C220's audited build retirement and runner archive remain in its local capsule.
Preserve `NASolve-cedar` at `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, its
local `phaser.py` change and unpublished data. Everyday pine and metal work remain
separate. Never clean raw runs, partial outputs, environments or unrelated files.
Current queue/handoff prose is replaced in place; older decisions remain in Git
and the existing evidence ledger. No extra milestone diary or owner was added.

— Rowan · Codex desktop
