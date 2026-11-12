# NASolve development handoff — current state

Updated **2026-11-12**, C220. Active branch: **cedar**, checkout `NASolve-c96`.
This change was developed from `654328105f193f25011fe927dc1db860cb82bca0`.
Proposed integration remains Cedar → pine → main, subject to review. The
[scientific completion queue](cif-doctor-completion-queue.md) is the sole work
order; the [capability table](cif-doctor.md#current-capability-boundary) owns
supported-scope claims. Use laboratory language first under the
[working-language policy](collaboration.md#working-language).

## Completed checkpoint: C220

**Before:** ordinary Coot/NAR construction and the checked dictionary/ReadySet
request existed, but needed manual execution/readback assembly. The current
handoff had become a 10,686-line diary; unused build copies and repeated delivery
checks obscured current work.

**After:** [explicit preparation commands](cif-doctor.md#checked-preparation-and-honest-recovery-c220)
construct/check once, read saved attempt state, read one exact result and continue
saved preparation through a fresh existing-owner attempt. The report identifies
the checked ReadySet model or independently checked pre-ReadySet model and its
matching ordered restraints. Failed evidence cannot become a fallback. The exact
previous attempt count is checked under the existing lock; no repeat Coot/NAR,
in-place retry, renewed allowance or latest-file selection.

**Files/compatibility:** `cif_ordinary_postmr.py`, `cif_complete_request.py`, CLI,
focused tests/profile, maintained docs/ledger and language policy. New live return
value and optional execution argument; no saved schema migration. Existing default
PostMR/campaigns and checkpoint selection retain their behavior. This is checked
preparation, not a successful diffraction-refinement or ordinary-adoption claim.

**Validation:** 20 API/owner and 6 CLI cases fail before implementation; **213
focused tests pass**. The full suite passes **9,178 tests + 276 subtests**;
source/tests/scripts stayed unchanged throughout. This C220 change is the new
full-tested baseline; exact file hashes are retained with the evidence. Syntax
compilation of 592 Python files in memory passes without warnings; `git diff
--check` and changed-document link/anchor checks pass.

The real C219 Phenix result rereads after relocation: one exact replay, 1,495 files
unchanged, original paths/SDK/process execution denied. Phenix settings restored
from the saved recipe match exactly, preserving its original timeout/attempt
limits; that check stops before any scientific execution (1,255 request files
unchanged). Phenix **2.2.1-6174 / dispatcher 2.2.1** and Coot **1.3.3 revision-count
0** scientific evidence is reused from C218/C219. No new native chemistry or
refinement run. All C220 validation workers are stopped.

**Exact checks:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` with the existing
Python environment; focused pytest covers ordinary outcome/CLI/entry, complete
request/continuation, CIF Doctor CLI and consolidated delivery cases. The full
command is `python scripts/run_tests.py full --junitxml <fresh-local-output>`.
Complete argument lists, outputs and hashes are in
[the evidence ledger](cif-linked-native-registration-evidence.json), key
`checked_preparation_handoff_2026_11_12`, and local capsule
`live_tests_directory/220_Cedar_preparation-handoff-p2_xisz6`.

## Cleanup and retained evidence

Retired **89** detached source-build copies (**5,152,171,002 logical bytes**) without
force, after verifying retained Cedar ancestry, local/ignored files, processes and
maintained-source references. Exact heads and archived Finder metadata remain in
the local audit. No scientific run directory was removed. **1,353** inactive
pre-C218 validation scripts were archived outside the product checkout and every
byte verified before removing duplicate originals; recent/unclassified runners
remain. Eleven repeated test functions became one table retaining all **32**
distinct cases; only four identical cases were removed.

Raw models, CIFs, datasets, attempts, logs, test XML, runner archive and audit
inventories remain local. The preserved `NASolve-cedar` checkout at
`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9` still has its authorized local
`src/nasolve/phaser.py` change and frozen unpublished evidence. Do not replace it.
Everyday pine and the metal-coordination checkout remain separate and untouched.

## Next: make inspection and refinement use the same chosen result

Q05 should carry this exact checked model/CIF/PHIL set into ordinary PostMR,
campaigns and immutable checkpoints, with honest pre-ReadySet fallback labels and
interrupted-publication recovery. Reuse the existing request reader/owner; do not
rebuild construction, compiler, scheduler or a second source validator.

Q04 remains open overall. General plane completion still needs composition into
the repair owner: PDU C5 near-planarity does not prove complete restraint coverage.
Reuse C208–C216's graph-selected PDU/5PC work. Q06 must validate real refinement
with all NAR terms and Free-R intact; Q07 then covers the mixed scaffold plus ATL
and the separate unfamiliar-ligand challenge. Q08–Q16 retain chemistry, coverage,
reports and release work. DP correspondence, source H/charge and numerical targets
remain visible. No merge is authorized by this checkpoint.

The old handoff and its anchors remain in
[immutable Git history](https://github.com/vecchioni-lab/NASolve/blob/654328105f193f25011fe927dc1db860cb82bca0/docs/development-handoff.md).
Consult the prior evidence before reopening an old problem; history is not a
second queue. C220 leaves no active worker or unfinished bounded implementation.
Paused at Simon’s request after the full pass; resume with the Q05 step above.

— Rowan · Codex desktop
