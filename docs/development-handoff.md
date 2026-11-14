# NASolve development handoff — current state

Updated **2026-11-14, C289**. Active **cedar** in NASolve-c96; latest pushed
code **C287 `cbece417`**, C288 observations pushed as `5441a199`; C289 tested, being published. Scoped Q04/Q05 reconciliation is C285 `d5996bc4`. Simon's active cutoff is **23:00 Europe/London, 2026-11-14**;
connectivity interruptions expected. Focused checks only: **no full suite, new
branch or merge**. Linden owns Pine/Willow; everyday NASolve code stays untouched.

## Where we are

**Q04/Q05 are accepted for the explicit supported route and recorded controls.**
The [completion queue](cif-doctor-completion-queue.md) is the sole work order and
owns the exclusions. This means prepare/check/repair, preserve attempts, recover
known-stopped work and deliver exactly the chosen model/restraints. It does not
approve every chemistry, enable defaults or qualify a native 100-dataset workload.

- C276–C279 join the normal campaign through actual Phaser/Coot/NAR/ReadySet,
  AutoSol and five refinement cycles, then read the exact endpoint after relocation.
  Preserve original Free-R, ordered restraints and D:1 terminal phosphate. C279's
  R-work 0.1971 / R-free 0.2222 is a software control, not structural approval.
- C280 executes repeated native failure under the original allowance: both results
  remain unqualified, third attempt/publication/retirement refuse, moved reads pass.
- C282 executes a second native preparation after the first was archived, publishes
  prepare-002 unselected and retires only eligible new working duplicates. All 207
  earlier campaign references and the current postmr choice remain intact.
- C281/C283 run 100 synthetic datasets (50 failures/50 prepared) and two explicit
  fresh retries. C283 reduces initial file-hash reads 651,504 → 13,104 by checking
  active science at stage boundaries, retaining full entry/exit/status audits.
- C284 scopes existing pure numerical reuse to status/archive-eligibility reads.
  170 focused tests pass; four saved-native C282 reads return identical complete
  results and unchanged 327 files. Replay falls 28 → 2; observed status 219 → 107 s,
  archive eligibility 206 → 97 s. All source/owner/archive checks remain fresh.

Whole requests retain 35.1 MB for one success, 65.7 MB for two archived successes,
and 70.7 MB for two native failures. Historical unretired PDU retains 315.3 MB.
Keep work serial and one expensive reader at a time; these figures are not hard
scratch/RAM quotas. Explicit campaign retry creates a new run/request allowance.
All failed/unknown science stays preserved. C283's task-owned 8.7 MB temporary
source copy was removed after relocation validation; compact receipts remain.

Exact commands, hashes, outcomes and limitations are in the existing evidence
ledger under C280–C285 keys, ending `q04_q05_supported_scope_2026_11_14`.
C283 focused: 271 tests +92 subtests, plus 5 sandbox-blocked process tests passing
with ps access; relocated temporary source: 16 pass. C284: 170 pass in 485.09 s.
C280–C287 validation groups stopped; no active jobs remain.
No raw science/logs/runners are committed. Last full suite remains
**C220/583d30df, 9,178 tests +276 subtests**, not a current-source pass.

## Next bounded work — Q06: what refinement actually does

- C286/C287: exact prepared/final inventories and GEO agree on 45 planes and
  58 ordered parallelities (54 unequal groups). Checked reader fixes only GEO
  observation; no native restraint reconstruction or inferred exact weights.
- C288: ordinary startup's family-isolation diagnostic changes its contact cache
  and normalization. Four failed/refused attempts remain preserved (23.34 MB).
  Fixed-scale raw/corrected scores agree; corrected sampled derivatives pass.
- **C289: whole-objective check passes its software/native-control contract.**
  Actual Phenix 2.2.1-6174 ordinary dry-run, zero cycles. No family switching:
  8004 contacts, 11284 terms, normalization 1/11284, pair-list updates=1 and exact
  static restraints remain unchanged. Raw forces fail 17/20 sampled directions;
  existing diagnostic correction passes 20/20 at identical target 1.1401030244830264.
  Each arm 162 calls; all 410 original run and 64 C286 files unchanged. Driver/native
  return zero; all processes stopped; source and installed files unchanged.

New `cif_objective_probe` reuses the existing finite-difference tolerances without
editing pinned workers/cores. Pure replay distinguishes absent/changed context
from numerical agreement; it does not authenticate native execution. Focused
command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHON -m pytest -q -p no:cacheprovider
 tests/test_cif_objective_probe.py tests/test_cif_gradient_audit.py` → 30 pass,
1.58 s. Eighteen new cases fail before the API exists. Moved-copy cold replay of
both native reports passes with no native process and 44 original files unchanged.
Native output `289_Cedar_whole-objective-8zz96zko` (local live-tests anchor) is
~5.7 MB; compact read receipt under ignored runners `c289_read_records/`.

**Next:** native consumer limitation is now demonstrated, not merely suspected
from C23–C26/source inspection. Choose and qualify a supported compatible remedy
before claiming ordinary corrected refinement. No installed SDK patch, dropped
restraint, altered chemical target or default runtime change. Current upstream
public parallelity.h still contains the accumulation loop (blob
`25d3a75f20d3611dcb32d919a893bc0beb18e6a0`); no upgrade remedy is established.
Separately inspect PDU chemical survival using existing exact source/control
artifacts, not another preparation/phasing rerun or a PDU-name repair switch.
Linden's W46 now reuses Cedar's native plane/torsion kernels for endpoint
attribution; do not duplicate that observer. These scalar/derivative findings do
not approve sugar pucker, chemistry or a refined structure.

Simon's reported PDU distortion after collaborator refinement is explicitly Q06,
then reused in Q07. Exact collaborator files/revision/settings remain unidentified;
no cause is diagnosed. Compare built/ReadySet/refined ring, trigonal C5, propyne
coplanarity/internal geometry and chi, preserving sugar/phosphate/pair/Free-R intent.
Use source connectivity and a held-out substituent; no PDU-name repair switch.
A 5IU input or numerical R-factor pass does not establish PDU survival.

Linden reports W43 fixed-manager full-precision/rounded ASU observations agree
with its independent rounded PDB capture on target/full gradient and common pairs;
extra neighbors have zero residual. That is adjacent evidence, not a Cedar merge,
ordinary-refinement result or general neighbor-generation proof. Keep NAR pair/
stack intent separate from intramolecular plane repair and additive contact energy.

Q07 mixed/held-out controls and Q08–Q14 retained chemistry learning follow. Q15
reporting and Q16 AutoPhase compatibility, deployment/integration/full regression
and reviewed merge remain later. Signed cross-agent handoffs: **— Rowan**.
