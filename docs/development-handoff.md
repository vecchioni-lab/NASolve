# NASolve development handoff — current state

Updated **2026-11-15, C304 starting**. Active **cedar** in NASolve-c96. C304 native recovery
pinned published C303 `9489077a` and has now completed five refinement cycles.
C295 records corrected phosphate intent and a read-only symmetry observation. Simon's
current window is **08:20–10:20 Europe/London, 2026-11-15**; interruptions expected. Focused tests
only: **no full suite, new branch or merge**. Linden owns Pine/Willow.

**Active scope:** C304 explicitly recovered C303 with fresh attempt 2 under the
unchanged 900-second allowance, then published that exact result and completed
five ordinary checked-plane-force refinement cycles. All owned processes stopped;
source pins, 904 prior run files (apart from legitimately updated report.json),
30 campaign bookkeeping files and the frozen request remained unchanged.
Original campaign BLOCKED and failed attempt 1 stay preserved. Output:
`304_Cedar_PDU-recovery-1f37ak8q`; scientific run remains in C303's campaign for
now. Native Phenix 2.2.1-6174, no Coot/NAR repeat; all 58 parameter records retained.
Next: cold relocation, staged PDU geometry and native effective membership.

C302 also dropped the `ARTIFACT_POLICY` re-export used by ordinary cleanup.
Direct reproduction raises ImportError; existing preparation-retention tests give
6 failed / 5 passed in 9.58 s. Four new current/legacy policy cases fail at the same
import (0.90 s). Restored the existing export after C304 stopped; current-only
automatic cleanup, legacy reads and scientific validation stay unchanged.
Focused checks: **147 passed in 170.03 s**, no full suite. Exact command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHON -m pytest -q -p no:cacheprovider tests/test_cif_preparation_retention.py tests/test_cif_attempt_retention.py tests/test_cif_complete_attempt_archive.py tests/test_cif_complete_child_bounds.py tests/test_cif_ordinary_postmr.py tests/test_cif_postmr_publication.py --tb=short`.
PYTHON is the everyday NASolve `.venv/bin/python`; cwd is Cedar. Includes actual
archive retirement, interrupted cleanup and relocated reads with the old path gone.
Changed source: only `cif_attempt_retention.py`; tests and changelog accompany it.
No schema/migration changes; raw science and runners remain excluded from Git.
Local ignored runners: `c304_recovery_*`, `c304_readback.py`, `c304_consumer_*`.
The unexecuted related 5PC control is now `c305_*`; do not use older c304 5PC drafts.

Linden's W65 composition tested published C303 separately; it is not Cedar native
chemistry acceptance. Linden owns today's isolated Willow browser/viewer work.

## Corrected intent and publication

- **B:1 intent:** Simon explicitly superseded his earlier free-OH reply: preserve
  P/OP1/OP2, no OP3, with intended incoming covalent continuation to a symmetry
  copy. C295's read-only native calculation finds B:7 O3′ under `-x+y,-x,z`
  nearest at 3.34019 Å in both original MR and prepared coordinates. This is a
  candidate image, not a confirmed partner or formed bond. All 19 original inputs
  and 72 C290 files remain unchanged. D:1's separately declared complete terminal
  phosphate is distinct; no new blanket OP3 policy or atom edits.
- **Shared ownership:** Pine carries editable declared topology; TopoStitch
  previews it; Cedar distinguishes intent, coordinate evidence and actual native
  enforcement. Reslicing must map identities/images or flag unresolved mappings,
  retaining previous choices. No absent Cartesian neighbor implies free OH.
- **GitHub publication:** after the initial automatic rejection Simon explicitly
  authorized pushing compact evidence. Code/tests/compact notes may be pushed;
  raw science, models, diffraction data, logs and runners remain local.

## Accepted foundations

**Q04/Q05 are accepted for the explicit supported route and recorded controls**
at C285 `d5996bc4`. The [completion queue](cif-doctor-completion-queue.md) is the
sole work order. Prepare/check/repair, retain alternatives and failed attempts,
recover known-stopped work, and deliver exactly the chosen model/restraints.
C276–C279 join actual preparation, phasing and five-cycle refinement; C280 preserves
native exhaustion; C282 retains earlier archived alternatives and current choice.
C283's 100 synthetic datasets reduce hash reads 651,504 → 13,104. C284 reuses pure
math within a read; source/ownership checks stay fresh. Do not rebuild these owners.

Recorded whole-request retention: one success 35.1 MB, two archived successes
65.7 MB, two native failures 70.7 MB. These are not native 100-dataset disk/RAM
capacity or hard quotas. Keep work serial, one expensive reader at a time.
Defaults, old-run migration, broader capacity/platform checks and full integration
remain Q16. Last full suite: **C220/583d30df, 9,178 tests +276 subtests**.

## Q06 — real refinement preserves the intended chemistry

**Established C291–C300 foundation:** complete plane parameters, corrected native
forces across five cycles/forks/replacement managers, frozen helper code, isolated
zero-cycle setup, ordinary AutoRefine/checkpoint readback and explicit CLI,
schema-2 campaign and Doctor forwarding. Corrected ancestry cannot silently lose
the choice; defaults remain unchanged. C299 `b4739c76` and C300 `d9f3bbb8` native
controls retain all 58 parameters and cold relocation. C299's outer driver failure
(wrong zero-cycle PDB expectation) stays preserved separately from its successful
CLI refinement. C300's Doctor trial leaves the earlier checkpoint current.
The existing ledger owns exact commands/counts/limits; do not repeat those controls
without a new reason. Preserve Free-R, NAR membership, observations and targets.
No SDK edits: qualification binds exact local Phenix 2.2.1-6174 / dispatcher 2.2.1,
Darwin/arm64 source; a version label alone does not qualify another installation.

**PDU control intent:** C301–C303 use C270's declared mechanics scaffold with
A:12 DA / B:4 PDU and D:1 terminal phosphate, no experimental phases. Original
observations/Free-R are retained; this is not PDU crystal data or a solved structure,
and does not unblock original PDU:PDU/B:1.

**C301 `bea76681`:** mixed canonical/modified Coot serial authority now includes
the declared A:12 DC→DA mutation, bound to actual identities. C80 covered related
curated sites; the missing canonical scope had prevented B:4 graph restoration
and correctly triggered the outgoing phosphate guard. The fix passes 237 tests
+10 subtests and read-only replay of all 31 unchanged failed-run files. Scope is
serial-only; graph/OP3/phosphate rules, old policy and rollback remain intact.

**C302 committed/pushed `d32825e9`:** `302_Cedar_PDU-campaign-fig6ru2e` passes
construction, PDU generation/repair and ReadySet, then refuses v2 outer completion
before checkpoint/refinement: parent bucket 143.7 MB also counted the owned repair
child. All processes stopped; source pins and five original inputs unchanged.
V3 separates that exact child, retaining 128 MiB/1024 files per part, 32 MiB members
and 128 MiB shared physical expansion. Actual unique attempt contents 94.0 MB;
all 743 observed attempt files unchanged. V2 still refuses the original grouping.
Old archive/retention and relocated new-format tests pass; exact frozen policy
is bound on read. No migration or retirement of failed C302. Native retries need
a fresh request/run. Full validation commands/results are in the existing ledger.

**C303 stopped, not successful:** fresh PDU campaign on `d32825e9`,
`303_Cedar_PDU-campaign-btuh5sop`, passes the new storage partition and completes
repair/ReadySet/native continuation, but final outer validation exhausts the frozen
900-second allowance. Outer receipt is RAISED/TimeoutError; no checkpoint or
refinement. Driver rc0 only reports a returned BLOCKED campaign. All owned jobs
stopped, source pins/five original inputs/dictionary unchanged. Preserve the whole
failed attempt. No in-place completion, policy rewrite or increased allowance.

**C303 fix committed/pushed `c9736e39`:** C184's coordinator called `_children`/`_result` immediately before
`_seal` repeated both. Sealing now owns that full validation once and uses C284's
existing bounded pure numerical scope. File/ownership/checksum checks, final
frozen deadline and artifact headroom remain unchanged; no new cache/schema or
allowance. The exact saved artifacts produce identical result/inventory hashes:
profiled unscoped replay 301.31 s versus scoped 144.35 s; numerical evaluations
14→2, all 852 request files unchanged. These are instrumented local timings, not
a production benchmark or proof that the next native attempt fits. New reader
still reports C303 STOPPED/RAISED/TimeoutError; all 963 run files unchanged.

Focused validation: **196 passed in 371.67 s** across complete-request,
continuation and numerical-replay tests. New deadline and identical-proof cases
fail before the fix; changed numerical evidence still refuses. No full suite.
Exact commands, fingerprints and limitations are in the existing ledger.

Read-only preparation geometry (Phenix 2.2.1-6174 native chi evaluator, no
optimization): B:4 chi differs from the parent by 0.0061° after construction and
ReadySet; C5 attachment elevation 0.9428°, triple flanks 176.401°/176.885°, bond
1.18943 Å. Terminal methyl is 0.11239 Å from the descriptive existing plane fit.
ReadySet preserves these measured coordinates; no actual refinement survival is
claimed. The selected dictionary's triple targets pass the existing screen
(180° ±3° angles; 1.174 ±0.02 Å bond), while its separate seed coordinates remain
REVIEW (174.83°/170.95°). Do not confuse those seed values with the built model,
or target correctness with achieved geometry. Compact values and local geometry receipt are in the same ledger.

**Next:** use the existing explicit continuation owner
on C303 (`continue-preparation RUN --after-attempt 1`) for one fresh numbered
attempt, if its frozen ownership/allowance/source checks still permit it. C220–C224
already define this route; preserve attempt 1 and do not repeat Coot/NAR or edit
its outcome. Publish only the new exact successful attempt, then run explicit
checked-plane-force refinement and inspect staged geometry/native membership.
The prior campaign's BLOCKED stage remains historical evidence; this explicit
recovery is not an automatic campaign-resume claim. G:5PC stays deferred until
PDU actually refines. Q06 and original symmetry-linked PDU:PDU/B:1 remain open.

## PDU control remains separate

C290 current ordinary PDU A:12/B:4 construction preserves parent chi (0.027°/0.006°
deviation; old construction both ~+53°). Current C5 elevations are 1.114°/1.016°
before repair. Old/current literal dictionaries differ despite equal parsed
atom/bond graphs; bond-length changes are not a one-patch causal comparison.
The known raw-W B:1 guard (C188/C189/C270) then stops intake. No repair, ReadySet,
publication or refinement ran. NAR has no T:T pair recipe and does not invent one.
All 19 original inputs and 72 attempt files stay fixed. Output:
`290_Cedar_PDU-pair-current-k3sdohpc`; read receipt `c290_read_records/geometry.json`
under ignored runners. C252's A:9/synthetic observations are a different control.

Simon's collaborator before/after files, native version and settings remain
unidentified. Compare built/ReadySet/refined ring, trigonal C5, propyne geometry
and chi while retaining sugar/phosphate/pair/Free-R intent. PDU and a held-out
substituent must demonstrate graph-based transfer. Q07 mixed/held-out scaffold,
Q08–Q14 retained chemistry learning, Q15 reporting and Q16 AutoPhase/integration
follow. Signed cross-agent notes: **— Rowan**.
