# NASolve development handoff — current state

Updated **2026-11-15, C304 complete / C305 active**. Worktree NASolve-c96, branch
**cedar**, published tip **a2e73603**. Simon's window is **08:20–10:20 London**;
interruptions expected. Focused checks only; no full suite, new branch or merge.
Linden owns Pine/Willow; no Cedar edits from that work.

## Active work and stopping boundary

C305 runs the predeclared related **G:5PC** mechanics control through the ordinary
campaign. Source is pinned at **a2e73603**: **do not edit src while it is active**.
Owned directory under `NASolve-live-tests`: `305_Cedar_5PC-campaign-nu1t7jyw`;
exec session **18783**, runner `branch-artifacts/cedar/runners/c305_start.py`
in the everyday checkout. Worker bound 2400 s, outer owner 3000 s. Check actual
process ownership before any recovery; preserve failed/partial output.
Use exact `active.json`, `driver-result.json`, progress and process receipts.

C305 retains the five declared C270 inputs, observations/Free-R, D:1 terminal
phosphate; only recipe pair A:5IU changes to G:5PC (A:12 DG / B:4 5PC). Explicit
checked preparation, automatic graph-selected plane support and checked native
plane forces; AutoSol disabled, no experimental phases. This is a mechanical
substitution control, **not data from a 5PC crystal** or structure solution.
It compares transfer after PDU actually refines; PDU chemical acceptance is open.

After C305 stops: inspect exact outcome; if successful, use prepared
`c305_readback.py` for cold relocation and staged geometry, then exact native
restraint membership if needed. Preserve the ordinary campaign's genuine status.
Do not reuse old unexecuted c304 5PC drafts. No unbounded retry or increased limits.
Wrap all owned jobs and update this handoff by 10:20.

## Where the pipeline stands

**Q04/Q05 accepted for the explicit supported route** at C285/d5996bc4:
preparation, independent fallback, stopped-work recovery, retained alternatives,
chosen-input delivery, serial bookkeeping and archived evidence. Reuse those
owners. Defaults, migration, deployment capacity and integration remain Q16.
The [completion queue](cif-doctor-completion-queue.md) is the sole work order.
Last full suite is C220/583d30df: **9178 tests +276 subtests**; not current.

**Q06 active: does real refinement preserve the intended chemistry?** C291–C300
already establish complete parallelity parameters, corrected native forces,
frozen helpers, zero-cycle setup and explicit AutoRefine/campaign/Doctor routes.
Only the recorded Phenix 2.2.1-6174 / dispatcher 2.2.1 Darwin arm64 source is
qualified. No SDK edits or default activation. Do not repeat those controls
without a new question. Keep Free-R, NAR membership, chemical targets and thresholds.

C301 bea76681 fixes mixed canonical/modified Coot serial authority. C302 d32825e9
separates the actual repair owner in storage v3 while retaining old layouts.
C303 c9736e39 removes duplicate final validation through the existing bounded
pure-math scope. Their full evidence remains in the existing ledger, not this diary.

## C304 result and remaining chemical question

Native code pinned **9489077a**. Existing explicit continuation created attempt 2
in C303's frozen request, completing within the same 900 s allowance. It published
that exact result and completed five ordinary refinement cycles, four processors.
All jobs stopped and source pins unchanged. 904 earlier run files remained exact;
report.json changed only through legitimate publication/refinement updates. 30 campaign
bookkeeping files and failed attempt 1 remain unchanged. Historical BLOCKED is
not rewritten. No Coot/NAR repeat or automatic campaign-resume claim.

The owned C303 campaign was moved, not copied, to
`303_Cedar_PDU-campaign-btuh5sop/relocated-after-c304` under local live tests.
Its old campaign path is absent. Cold read preserves all 1787 files, campaign
integrity OK, current refine-001 parent postmr, terminal audit PASS. Native
readback retains all **45 planarity /58 parallelity** groups and weights;
prepared/refined inventories agree with actual printed refinement geometry.
C304 compact/local records: `304_Cedar_PDU-recovery-1f37ak8q`.

PDU B:4 chi changes from -109.04° to -111.17°: no flip. C5 attachment elevation
changes 0.94°→2.48°; propyne angles 176.40°/176.88°→174.65°/173.45°;
triple distance 1.18943→1.19765 Å. Existing-plane descriptive terminal methyl
distance grows 0.112→0.261 Å. Authenticated linked-site native target screen
passes; coordinate screen goes PASS→REVIEW under the existing 5° rule. **Q06 is
not closed.** Printed targets remain 180° ±3°; no dropped-restraint explanation.
C206 already left the 1.607 Å terminal propyne bond target unqualified. Distinguish
target calibration, packing and the data/restraint compromise; do not invent
replacement targets or tighten thresholds to obtain a pass.

The first local triple diagnostic used the unlinked component and reported its
extra OP3. Final audit reuses the verified linked-site projection: no inventory
mismatch, only the two bending findings. Both diagnostics are preserved locally.
This is a separate A:PDU mechanics scaffold, not the original PDU:PDU case.

C304 also restores the storage-policy export removed at C302; ordinary cleanup
otherwise raises ImportError after publication. Published fix **a2e73603** changes
one import, adds current/legacy policy regression and changelog. Before: six
existing failures, four new failures. After: **147 passed in 170.03 s** across
preparation retention, attempt retention/archive/bounds, ordinary PostMR and
publication; includes interrupted cleanup and moved reads. No schema, chemistry,
allowance or default changes. Exact commands, hashes and native measurements:
`pdu_recovery_refinement_survival_2026_11_15` in the existing evidence ledger.

## Scientific and collaboration boundaries

B:1 in the original PDU:PDU scaffold means intended incoming symmetry continuation:
preserve **P/OP1/OP2, no OP3**, superseding Simon's earlier free-OH reply. C295's
nearest B:7 O3′ image `-x+y,-x,z` at 3.34019 Å is a candidate, not confirmed linkage.
D:1's separately declared complete terminal phosphate remains distinct. No blanket
OP3 rule, lone symmetry bond, inferred free OH or invented angle enforcement.
Pine carries editable intent; TopoStitch previews; Cedar separates declarations,
coordinates and actual native enforcement. Linden W66/W67 preserve those boundaries;
installed composition is separate from Cedar chemical acceptance.

Simon authorized code/tests/compact evidence pushes. Models, diffraction data,
logs and runners stay local. Retain failed work; use existing qualified archive
owners for successful duplicates, never ad hoc deletion. Keep execution serial
and one expensive scientific reader at a time. No native 100-dataset capacity claim.

Next after Q06: Q07 combined and unfamiliar-modification controls; Q08–Q14 retain
sugar/backbone/chemical-state learning; Q15 scientist report/PDF; Q16 AutoPhase
compatibility rename and full integration/release review. No automatic merge.
Cross-agent notes are signed **— Rowan**.
