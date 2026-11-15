# NASolve development handoff — current state

Updated **2026-11-15, C317 bounded checkpoint complete — Rowan**.
Worktree **NASolve-c96**, branch **cedar**, published source **393aea60** (C307).
Focused checks only; no full suite, new branch, default activation or merge.
Linden owns Pine/Willow; no Cedar edits from that work.

## Current work and interruption recovery

**All native jobs are stopped and source remains unchanged.** C308’s matched
refinements and C309–C317 diagnostics are complete; do not rerun them to recover
context. C310–C317 preserved all 1,146 original PDU run files and the
selected `refine-001`. The last control is local
`317_Cedar_native-output-sync-i18n6frt`; `driver-result.json` verifies exit 0,
known-stopped ownership and unchanged source. There is no pending native process.

**Next is a bounded Q06 output-consistency patch.** Native group-ADP final scaling
updates current scattering B factors but leaves the output hierarchy/PDB stale.
C317 qualifies native `model.set_xray_structure(current_xrs)` before serialization
in isolation: PDB/mmCIF agree, coordinates/scattering/geometry owner stay intact.
Integrate through the existing refinement owner with a **new qualified helper
version**, retain frozen v1 sources/readers and old results, then verify actual
written PDB/mmCIF/scattering agreement. Do not overwrite `_SOURCE_DIGESTS` and
invalidate earlier checkpoints; do not repair historical files or infer B shifts.
Ordinary numerical-candidate delivery and whole-substituent survival follow.

**C307 is committed/pushed as 393aea60.** The additive
`cif_linear_bond_reference.py` selects triples and neighboring single bonds from
source connectivity. It compares supplied MMFF94s or exact source-compatible
energy-library rows and writes separate explicit target-only candidates. Every
existing ESD, chemical declaration, coordinate and other restraint is preserved.
Unknown neighbors remain unsupported; supplied references are not automatically
authenticated or approved. No ordinary repair caller/default changed.

**C308 matched refinements are complete and read back.** Target 1.470 Å gives:

| Control | Previous → new terminal bond | New triple angles | Result |
| --- | --- | --- | --- |
| A:PDU | 1.6242 → 1.4818 Å | 175.02° / 173.94° | Still REVIEW; terminal plane offset 0.258 Å |
| G:5PC | 1.3564 → 1.4864 Å | 176.27° / 175.76° | Scoped triple PASS; plane offset 0.035 Å |

Both use their original postmr parent, observations/Free-R, recipe, strengths and
five cycles. PDU uses four processors; the original 5PC control uses **ten**.
All recorded bonded/plane parameters survive; printed GEO agrees with all 45
planes and 58 parallelities. Each retains all three local sugar signs, protected
terminal phosphate and original selected `refine-001`. New unselected endpoints:
PDU `refine-002`, matched 5PC `refine-003`. The earlier four-processor 5PC
`refine-002` remains intact. These substituted-scaffold controls are not modified-
crystal data or structure approvals. No original symmetry-linked PDU:PDU resolution.

Dictionary and equivalent PHIL candidates have identical fixed-coordinate energies
and gradients, but PHIL changes the selected bond's native origin 0→4. That
provenance difference is explicit; diagnostic overrides do not establish ordinary
corrected-CIF delivery. Original automatic data/geometry weight optimization stays
enabled, so realized weights can differ between trajectories.

**C309 geometry-force diagnosis is complete.** The maintained corrected-gradient
audit passes (1,367 evaluations; 3,328 plane-order pairs). Two source-selected small
arm rotations open the remaining PDU angles while preserving bond lengths. Their
geometry derivatives are −1.10682/−1.34741 native units per opening degree, entirely
angle forces; nonbonded and plane derivatives are zero. Native covalent boundaries
agree. This local result does not establish finite-move behavior or diffraction
forces and does not authorize stronger restraints.

**C310–C314 recover the diffraction comparison honestly.** C310’s first import
failed before native work; its fresh cold-start derivative attempt remains REVIEW.
C311 reproduces saved scattering/fit, but direct recalculation from the PDB shifts
Rwork 0.20624→0.25679. Its numerical PASS does not qualify historical force signs.
C312 rules out startup ADP/occupancy changes and direct-versus-FFT alone. C313’s
FCALC-only comparison suggests −51.82 Å², matching the independent final log.
C314 uses that logged value only in an ephemeral reconstruction: FFT fit returns
to Rwork/Rfree 0.206238/0.236232; direct control 0.206271/0.236327, with all six
finite differences passing. Data favors the first opening (−7.13452e−6) and
opposes the second (+4.86788e−6 per degree). Geometry favors both. Units differ;
no combined weight, relaxed move, trajectory or full-bend explanation is claimed.

**C315–C317 isolate the output bug and a native remedy.** C315’s current model/
fmodel scattering stays consistent, so the initial copied-object hypothesis was
not reproduced. C316 instead finds stale hierarchy and serialized PDB B values,
51.8198315 Å² above current scattering after native final scaling. C317 uses the
exact current object with Phenix’s synchronization API; in-memory PDB/mmCIF B
errors fall to 0.0001685/0.00000153 Å². Coordinates, FCALC and geometry owner remain
unchanged. No output model is written or adopted and no ordinary runtime changes.
The final-scaling controls run with native parallelity bindings restored. This
is not a historical optimizer replay or a universal Phenix-version claim.

## Evidence and retained controls

The evidence ledger owns exact methods, commands, hashes, limits and earlier
history; do not duplicate it into another notebook or rerun completed controls:

- `linear_neighborhood_reference_candidates_2026_11_15` (C307).
- `matched_linear_neighbor_refinement_2026_11_15` (C308).
- `linear_arm_opening_force_review_2026_11_15` (C309).
- `pdu_scattering_state_and_opening_forces_2026_11_15` (C310–C317).

Final C308 comparison root: `308_Cedar_target-comparison-rhj4xwif`.
PDU execution: `308_Cedar_target-only-25kntshu`; matched 5PC execution:
`308_Cedar_target-only-lwjckkug`; C309: `309_Cedar_opening-forces-kc610ury`.
All are under the local live-test anchor. Preserve the earlier layout/origin,
mutable-summary and processor-mismatch guard failures. PDU refinement succeeded
before its diagnostic wrapper refused the ordinary run-report update: separate
readback reconstructs the prior report's exact hash and verifies all other old
files/records. Do not rerun it. Root reports append ordinary history; numbered
scientific outputs and old checkpoint records are unchanged.

Scientific run anchors under `NASolve-live-tests`:

- PDU: `303_Cedar_PDU-campaign-btuh5sop/relocated-after-c304/DiU/AutoMR/run_001`.
- 5PC: `305_Cedar_5PC-campaign-nu1t7jyw/relocated/DiU/AutoMR/run_001`.

Old campaign anchors are absent. C304/C305 already passed moved archive-backed
reads; new run-relative PHIL/checkpoint inputs validate at these anchors. C308 is
not a new move-after-execution portability experiment. Actual native build is
**Phenix 2.2.1-6174 / dispatcher 2.2.1, Darwin arm64**. No Coot repeat in this block.

## Validation and next work

C307: **161 focused passes**, including 43 new cases. Broader chemistry profile:
1,735 passes +10 subtests, with 11 sandbox-denied process-signal/inspection failures.
All four affected files then passed with the required process access: **192 passed**.
Do not call the original sandboxed invocation green. No source/test changes after
C307, redundant pytest rerun or full suite. Last full suite remains C220/583d30df:
9,178 tests +276 subtests, not current.

**Q04/Q05 are accepted for the explicit supported route** at C285/d5996bc4.
Keep their preparation, fallback, recovery, selection, delivery and archive owners.
**Q06 remains open**, with Q08 supplying the numerical/force diagnosis. Finish the
versioned output-state handoff above, then qualify numerical repair through those
existing owners.
Do not confuse a working parameter candidate with ordinary background delivery,
a triple-only PASS with whole-ligand approval, or scaffold fitting with validation
of the modified molecule. Keep all neighboring targets and unsupported states visible.

The [completion queue](cif-doctor-completion-queue.md) is the sole work order.
Next packages retain the combined/unfamiliar modifications, sugar handedness and
fluorine learning, PNA backbone, locked sugars, catalogue coverage, chemical states
and false-alarm checks. Then the scientist report/PDF, AutoPhase compatibility
rename, full integration/platform validation and reviewed release cleanup. No merge.

## Scientific and collaboration boundaries

Original PDU:PDU B:1 means intended incoming symmetry continuation: **P/OP1/OP2,
no OP3**, superseding the earlier free-OH reply. C295's B:7 O3′ image `-x+y,-x,z`
at 3.34019 Å is a candidate, not confirmed linkage. D:1's separately declared
complete terminal phosphate remains distinct. No blanket OP3 removal, inferred
free OH or lone symmetry bond without its surrounding chemistry/forces.
Pine owns editable intent; TopoStitch previews; Cedar separates intent, coordinate
support and actual enforcement. Linden W73–W75 source-frame tests are separate
experimental evidence, not an installed adapter or Cedar symmetry qualification.
Energy entry alone is insufficient: selection/copies, pair tables, ADPs and native
reporting also need explicit lifecycle contracts. Current checked plane forces
remain source-bound and refuse symmetry planes; no SDK edits.

Simon authorized code/tests and compact evidence pushes. Models, reflections,
CIFs, full inventories, logs and runners stay local. Keep work serial with one
expensive scientific reader at a time. Preserve failed work; retire successful
duplicates only through existing qualified owners. No native 100-dataset disk/RAM
capacity claim. Cross-agent notes are signed **— Rowan**.
