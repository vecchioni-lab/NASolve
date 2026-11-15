# NASolve development handoff — current state

Updated **2026-11-15, C304/C305 native validation complete**. Worktree NASolve-c96, branch
**cedar**, source fix **a2e73603**, compact PDU evidence **f28b0dbc**. Simon's window is **08:20–10:20 London**;
interruptions expected. Focused checks only; no full suite, new branch or merge.
Linden owns Pine/Willow; no Cedar edits from that work.

## Current stopping state and next work

**All C304/C305 native jobs, readbacks and C304 retention have stopped.** No source
lock or pending retry remains. Native sources: C304 **9489077a**, C305 **a2e73603**;
C305 consumer/readback source differs only by compact documentation. No full suite.
Completed controls use Phenix 2.2.1-6174 / dispatcher 2.2.1; C305 also uses Coot
1.3.3 revision 0. See exact records, source pins and limits in the evidence ledger.

**Next bounded task:** retain the PDU endpoint and diagnose its residual bending
through existing numerical/force readers and source/native parameter provenance.
C206 already flagged the 1.607 Å C5B–C5M target; do not rediscover that as a new
bug or invent a replacement from model coordinates. Distinguish numerical target
calibration, local contacts and diffraction/restraint compromise. Do not silently
copy 5PC weights, flatten the whole substituent, rerun Coot or rebuild Q04/Q05.
The related control passes its scoped geometry check, but **PDU and Q06 remain open**.

## C305 related control

The predeclared **G:5PC** ordinary campaign completed preparation, automatic archive
and five real checked-plane-force refinement cycles, with no experimental phases.
It retains the five C270 inputs/Free-R and D:1 terminal-phosphate intent; only the
new recipe pair changed A:5IU→G:5PC (A:12 DG / B:4 5PC). It is a mechanical
substitution control, **not data from a 5PC crystal** or a solved structure.

Owned result: `305_Cedar_5PC-campaign-nu1t7jyw/relocated/DiU/AutoMR/run_001`
under local live tests. Old campaign anchor absent; 349 campaign files unchanged
on cold read. Registry current refine-001 parent postmr; terminal audit PASS.
All 45 plane groups and 58 parallelity groups/weights agree between prepared and
refined native captures and actual printed refinement geometry. Consumer read
preserves all 297 run files. Native runtime reports five cycles and 42 observed
process/parameter combinations. No installed SDK changes.

5PC chi -108.45°→-108.64°; C5 attachment elevation 5.04°→1.05°; propyne angles
172.37°/176.97°→177.38°/178.14°; triple length 1.20212→1.19514 Å. Existing-plane
terminal methyl distance 0.664→0.141 Å. Linked native targets pass; coordinate
screen REVIEW→PASS. All three recorded sugar chirality signs survive in both
PDU and 5PC. The 5PC dictionary's seed-coordinate review is a different observation.
Both bases, partners and numerical parameters differ between the controls: this
is not a one-variable causal comparison or universal ligand acceptance.

Automatic storage retires 694 authenticated working duplicates (174.3 MB logical)
into a 16.65 MB archive, leaving the whole request **39.74 MB**. Exact archive-backed
reads survive relocation. Full delivery at native completion 58.68 MB; optional
native-consumer diagnostics add 20.52 MB. These are persistent logical bytes, not
physical peak disk/RAM or native 100-dataset capacity. The session had a wall-clock
discontinuity; recorded worker monotonic duration (~908 s) is not elapsed wall time.

Local ignored runners are `c305_start.py`, `c305_worker.py`, `c305_readback.py`,
`c305_consumer_*`, `c305_native_linked_geometry_review.py`. Older unexecuted c304
5PC drafts are not active. Ledger key: `related_5pc_ordinary_refinement_2026_11_15`.

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

After all observations, the existing retention owner archived successful attempt 2
only. Request size falls **388.38→231.02 MB**; all 744 failed-attempt files and all
998 other prior files stay unchanged. Public model/restraint paths and current
refine-001 remain; archive-backed read verifies all 1057 remaining run files.
No failed output was deleted. C304 successful archive/read took 242.76 s locally.

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
installed composition is separate from Cedar chemical acceptance. Linden's W68
reports native angle kernels can handle explicit images, but ordinary manager
evaluation omits unit-cell context and pickle/deepcopy can lose operators. Treat
that as separate source-bound Willow evidence: no Cedar symmetry-angle support or
bond activation. The current plane-force bridge wraps the evaluation kernel; it
has no custom-proxy metadata reconstruction hook and explicitly refuses symmetry
planes. Future reuse of the existing round owner needs separate angle lifecycle
and evaluation qualification, not another refinement driver.

Simon authorized code/tests/compact evidence pushes. Models, diffraction data,
logs and runners stay local. Retain failed work; use existing qualified archive
owners for successful duplicates, never ad hoc deletion. Keep execution serial
and one expensive scientific reader at a time. No native 100-dataset capacity claim.

Next after Q06: Q07 combined and unfamiliar-modification controls; Q08–Q14 retain
sugar/backbone/chemical-state learning; Q15 scientist report/PDF; Q16 AutoPhase
compatibility rename and full integration/release review. No automatic merge.
Cross-agent notes are signed **— Rowan**.
