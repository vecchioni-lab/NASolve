# NASolve development handoff — current state

Updated **2026-11-14, C287**. Active **cedar** in NASolve-c96; latest pushed
code **C287 `cbece417`**; scoped Q04/Q05 reconciliation is C285 `d5996bc4`. Simon's active cutoff is **23:00 Europe/London, 2026-11-14**;
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

**C286 completed and stopped:** exact prepared/final input interpretation and
native GEO observation retain 410 original files. Both fresh native inventories
have the same 45 planes and 58 parallelities; all printed final plane members and
rounded weights agree. The installed GeoParser returns only 1/58 parallelities
and misassigns unequal-plane tails. No SDK edits or diffraction rerun.

**C287 tested and pushed (`cbece417`):** pure checked GEO parallelity reader retains all
58 groups before/after, exactly matching ordered native membership, including 54
unequal-plane groups. Nineteen focused tests pass, including a native nonbonded
header regression and relocated read. All 64 C286 files and 410 original files
unchanged. Printed values are observations only; no exact weight/target inference.
**C288 observed; all jobs stopped:** four preserved fresh attempts under local
live-tests. Last is `288_Cedar_ordinary-derivatives-4vf0oir2`; compact reviewed
receipts are `c288_saved_records/` under ignored Cedar runners. Exact ordinary
Phenix dry-run retains 853 atoms, 45 planes and 58 parallelities, with zero cycles.
All four derivative audits completed, but its final cross-audit equality refused:
isolating restraint families rebuilds contacts and changes normalization (11284
versus 11151 terms). Fixed-scale raw and corrected targets agree exactly; raw
all/parallelity fail 18/21 directions, corrected all eight families pass. Earlier
attempts preserve import/normalization assumption failures. No attempt is called
exit-zero. All 410 original run files, 64 C286 files, source and observed SDK pins
remain unchanged. Four attempts total 23.34 MB; failed evidence retained.

**Next C289:** a small whole-objective probe must keep every restraint active
throughout and retain actual native normalization. Existing family-audit helpers
change the manager cache, so they do not isolate this question. Reuse existing
finite-difference tolerances/probe design without modifying historical pinned
worker/core sources. No source/SDK patch or diffraction rerun is justified yet.


Start from saved C279's successful ordinary refinement and its exact chosen
bundle. Reuse existing native inventory, source-selected trigonal measurements
and derivative owners. Compare effective plane/parallelity membership and target/
weight meaning with actual refinement outputs, then inspect achieved geometry.
Do not rerun preparation/phasing merely to make a new diagnostic folder.

Prior work checked: C23/C24 reproduce installed parallelity accumulation failure;
C25/C26 and maintained numerical owners correct it only in explicit diagnostic
evaluators. C215 validates plane-completion energy accounting with zero parallelity;
C216 measures general source-selected trigonal geometry. These do not qualify
ordinary phenix.refine derivatives. Installed local source still has the earlier
accumulation loop; source inspection alone is not a new ordinary-consumer test.
C287 supplies checked parallelity observations after the installed GeoParser
failed count/column agreement. Printed precision must not become exact authority.

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
