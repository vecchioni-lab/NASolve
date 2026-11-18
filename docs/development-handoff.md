# NASolve development handoff — Willow

Updated **2026-11-18**. **W139 demonstrates bounded local sticky-end benefit**
against matched native-only and zero-addition controls. Their coordinates/history
match exactly; adding the pair restraints reduces GC plane mismatch 27.30→6.30°.
Rfree improves slightly against that control (.2613→.2609), but stays worse than
the initial .2599; Rwork and final clashscore worsen. Both optimizations stop by
line-search error. **This is useful local movement, not an accepted repair.**

W138's explicit 100-cap ordinary mechanics pass full, focused, relocated installed
and actual native gates, integrated by Rowan into Cedar `4f7aeb84`
with exact qualified source/tests/package configuration. C400's passive observer
and native/zero/full comparison are complete; do not rerun them. The next numerical
boundary is the recorded normalization discontinuity at identical coordinates,
before larger physical motions. Willow helpers remain W118 with W131 cold reporting.
The [current four-file science view](#local-science-checkout) shows the matched effect.

The backend can bind explicit periodic pair intent, apply the missing geometry
terms during one qualified native refinement cycle, retain their original meaning
across compatible registered descendants and refuse unsupported or unproven
continuations. **General sticky-end repair and ordinary recut refinement remain
unqualified.** S04/S05/S06 and P01/P02 remain partial. The
[machine roadmap](topostitch-roadmap.json) is the status authority; its
[human view](topostitch-roadmap.md) is generated from it.

## Current development edge

| Component | Proven scope | Still open |
| --- | --- | --- |
| W139 matched canonical control | Native/zero identity, passive full observer and common14-pair local improvement | Both stop stpmin; worse Rwork/final clashes, no whole-model acceptance |
| W138 ordinary longer control | Explicit v8 100-cap route, actual final writer/pair capture; full/installed/native gates pass | Broader protocols, semantic weighting and CLI/Doctor activation |
| W125–W134 shared execution/readback | Original pair intent, fresh admission, actual output proof and compatible registered continuation | Ordinary modified-chemistry descendants, unclassified native remainder and broader efficacy |
| W137 chemistry/numerical audit | Source-bound ordinary versus standalone preparation; same-state FFT/direct arithmetic | No retroactive chemical adoption or production numerical-policy change |
| W118/W100 periodic geometry | Same-identity/frame recipe rebind; source-driven bounded bending trials | Larger/general bends, stable optimization and diffraction/density acceptance |
| Pine editable periodic graph | Intent, preview/cut and source/image correspondence machinery | Faithful recut refinement, seam chemistry and persistent user review |

Exact numerical results, failures and pins are in the
[periodic/native ledger](topostitch-periodic.md). Historical probes are evidence,
not another work queue; do not repeat them because this handoff is shorter.

## Next bounded work

1. Keep the [stable-objective invariant sketch](topostitch.md#stable-objective-invariants-deferred-design-unimplemented)
   deferred under S06, using the exact recorded
   C400 same-coordinate normalization jump and prior C397–C399/A85 evidence.
   Coordinate with Rowan/Hazel; do not repeat the completed matched control or
   equivalent derivative/restart/iteration sweeps. Declare the invariant and
   matched test before changing numerical policy; retain all physical forces,
   repulsion, original data/Free-R and unselected REVIEW. No further native work
   is scheduled in the 18 November window. Rowan's shared execution queue owns
   timing; its fresh corrected-PDU preparation/publication gate is separate.
   This sketch does not queue a new matrix or numerical-policy patch.

2. W133 closes the bounded final-state pair-capture seam. Keep native remainder
   unclassified until chemical ownership is explicit. Reuse Cedar's source-backed
   component/link provenance, canonical pair coverage and Alder's explicit metal
   declarations; never classify covalent/terminal edits solely by origin IDs.
   Hazel's private origin-0 selector is not a maintained general classifier.
   W129's summary-dependence probe is complete; no new weight policy follows.
   A universal covalent classifier is not a prerequisite for explicitly labelled
   fixed-weight canonical controls; it remains a separate gate before semantic
   weight selection. Predeclare longer-coordinate budgets and matched controls
   before broadening beyond the qualified fixed-weight coordinate protocols.
3. Keep ordinary protocols explicit: one all-site XYZ cycle, fixed unit weights,
   one process and seed 1; existing ten-cap route or opt-in v8 exactly 100-cap
   with mandatory final capture. Neither cap proves convergence. `counted_frame="recipe"`
   is an explicit, recorded choice; do not generalize it into model-cell preference.
   Broader weights/ADPs/scaling/phases, extra terminal sources need separate qualification through existing owners.
   C388 qualifies passive chemistry coexistence and focused ordinary forwarding;
   it does not establish a successful repaired structure.
4. Then use matched B10 controls and geometry, packing and diffraction/density
   evidence before physical acceptance. Preserve original data/Free-R, unselected
   REVIEW and exact pair intent. Retain repulsion while exclusions are open;
   never activate an isolated symmetry phosphate bond.

**W122 remains planning-only:** the first intended user-facing application is
[explicit canonical sticky-end enforcement](topostitch.md#explicit-sticky-end-enforcement-during-refinement-planned-w122),
then separately qualified plane-only mismatch hypotheses. Automatic inference and
large-bend repair follow later. No CLI/default activation follows from these docs.

## Validation and scientific interpretation

- **W138 source qualification:** candidate `d8656b22` passes **12,008 tests +293
  subtests**, two existing native opt-in skips (3,581.07 s), with all 1,415 tracked
  files unchanged. The 334 focused/334 relocated installed tests and final 35 pin
  checks pass. All 304 packaged resources match; installed checks run after the
  build-source copy and old install path are gone. Published Cedar `4f7aeb84`
  matches all 792 source/test/package/CI files exactly; no second full-suite run
  is claimed. The clean qualification worktree has been retired after archival;
  installed resources and all scientific runs remain. [Commands, schemas, compatibility and retained attempts](topostitch-periodic.md#w138--qualify-the-explicit-longer-coordinate-control).
- **W138 actual ordinary execution:** complete Phenix **2.2.1-6174** cycle,
  280.319 s; original intent, actual writer/final geometry and unselected REVIEW
  lineage verify independently. This uses the existing diagnostic PostMR parent,
  not a fresh MR/ordinary chemical preparation.
- **W139 scientific comparison:** Hazel's 82-check independent union and Linden's
  common14-pair rounded-PDB measurements pass without new native evaluations.
  The actual full native/zero controls and fresh zero correction are stopped.
  A separate model-bound amendment distinguishes initial log clashscore from
  final PDB values. [Results, stopping evidence and limitations](topostitch-periodic.md#w139--measure-matched-sticky-end-benefit-without-claiming-repair).

Earlier tests, failed attempts and qualification pins remain in the existing
[periodic/native ledger](topostitch-periodic.md) and Git history (the full W138
handoff is `c33db066`). They are not a queue to repeat. W131 cold reporting and
W118 numerical helpers retain their exact original scopes; no later software
PASS upgrades older diagnostic models to accepted structures.

## Local science checkout

**Current W139 matched view:** GitHub workspace anchor,
`ScienceCheckouts/Linden/2026-11-18_matched-sticky-ends/review.html`.
Open `open_inspection.py` to toggle native-only versus full pair restraints.
Four new files reuse the preceding full display PDB through a checksum-bound
relative reference; keep the Linden folder together. GC plane mismatch changes
27.30→6.30° without alignment or magnification. The report includes adverse
Rwork/clashes and actual stopping. Headless ChimeraX 1.12 validates two 1,140-atom
models, four child planes and five contacts each; five local links/checksums pass.
No browser-layout validation is claimed. Display PDBs omit ANISOU/connectivity
and must not be used as refinement or deposition inputs.

Earlier, preserved views at the same anchor:
`ScienceCheckouts/Linden/2026-11-18_long-control/review.html` compares same-start
restrained caps 10/100; `ScienceCheckouts/Linden/2026-11-18/review.html` is the
morning readback summary; `ScienceCheckouts/Linden/2026-11-17/review.html` shows
the earlier short matched effect. They answer different questions.

Rowan owns the shared 17:00 UK report and its existing one-time reminder; do not
duplicate it. His local report links this matched view and Hazel's metal work.
Follow the [lightweight checkout policy](collaboration.md#lightweight-science-checkouts).
All scientific payloads and reports remain local; documentation pushes do not
authorize raw-data publication.

## Scientific limits and demonstration gates

- **Bending:** W100 uses actual-input tethers and three matched controls. All
  pass full/PDB-rounded derivative checks but stop `NOT_CONVERGED_LIMIT`;
  endpoints remain `REVIEW`. Some individual packing/torsion/plane terms worsen.
  [Exact results and inspection files](topostitch-periodic.md#w100--source-displaced-controls)
  are local evidence, not selected repaired models. W91 found no benefit from the
  small coarse polish; do not restart it without a different justified question.
- **Diffraction and density:** W34 found no meaningful held-out benefit from
  bend-plus-cleanup (Rfree .2276 versus .2274 for cleanup), with worse bond/angle
  RMSDs. S06 requires exact model/map/data binding and matched refinement before
  calibrated sustained negative-backbone-density detection. Noise, resolution,
  occupancy and ADPs matter. Keep straight→bent, bent→straight and changed,
  nonuniform or distal curvature as general cases; 4T28/8SJW interpretation remains
  unverified. No density-aware repair is implemented by W107.
- **B09 final gate:** geotest altered arms, including **X11_18 in P4_3** and
  X11_22, must align and survive matched refinement with healthy arms/junctions
  preserved. The local inventory passed 204 hash/size checks; remaining sequence,
  arm and partner mappings are not frozen. Preserve X11_18's P4_1-input/P4_3-model
  lineage for explicit audit. See the [gate contract](topostitch.md#final-geotest-alignment-gate-planned).
- **Blunts and asymmetry:** designed blunts can depend on one base-stack contact
  and need density-aware placement. Three labelled triangle orientations must
  start **after PostMR and the first refinement**, with fixed data/Free-R and
  separate bending/refinement. Re-running MR can erase those alternatives.
  [Blunt scope](topostitch.md#designed-blunt-contacts-and-single-base-stacking-w93-planned)
  and [rotation scope](campaign-model-roadmap.md#three-orientation-asymmetric-triangle-check-w93-planned)
  remain plans; no new dataset solve is claimed.
- **Publication:** the [shared shortlist](campaign-model-roadmap.md#nasolve-publication-demonstrations)
  records A2T7 rotations, recuts with bending, standard datasets including DOHU,
  and Hazel's metal cases, with separate readiness and scientific evidence gates.

## Pine recuts and shared ownership

Pine owns editable periodic intent; TopoStitch exposes it; Cedar owns native
chemistry/enforcement. Preserve **P/OP1/OP2** for declared continuations even when
partners are unresolved. No automatic OP3/dephosphorylation or isolated symmetry
bond while surrounding geometry/exclusions remain unqualified. See the
[shared connectivity contract](construct-registration.md#shared-periodic-connectivity-intent-pine-topostitch-and-cedar).

For pure representative recuts, prefer one computational/source frame throughout
the native process, deriving views at explicit boundaries. Bind atom/operator/tensor
correspondence and checkpoint lineage. Refined children need fresh bindings;
Coot edits and re-entered exports need checked inverse mappings. Additions,
deletions, renames or changed intent require new qualification. P03/P04 physical
identity and seam chemistry precede ASU materialization; recutting cannot close a
physical gap. Native reporting, copying, ADPs and writers retain their own gates.

## Historical Pine references

The inherited October queue is historical, not today's Willow instructions.
The [October handoff](history/development-handoff-2026-10-08-pre-consolidation.md)
and [native modified-pair ledger](native-modified-pair-live-validation.md) preserve
chemistry, run and user-review evidence. The full pre-cleanup Willow handoff is
retained in Git at `6352c8aa45b1e464fda03794bc302591f5a79ab5`.
Existing agent-readable references below remain valid historical pointers.

### Pine close-out

See the [archived Pine gates](history/development-handoff-2026-10-08-pre-consolidation.md#pine-close-out).
They do not establish current Cedar or Pine completion.

### Nine-member baseline results

See the [archived baseline](history/development-handoff-2026-10-08-pre-consolidation.md#nine-member-baseline-results).

### After Pine: blind AlphaFold geometry campaign, then Scout

See the [historical sequencing](history/development-handoff-2026-10-08-pre-consolidation.md#after-pine-blind-alphafold-geometry-campaign-then-scout)
and current [registration contract](construct-registration.md). Predictions are
candidate models, not solved truth; preserve frozen sequences, diffraction and
Free-R, and do not consult outcome structures during blind selection.

## Work discipline and doc ownership

Use [AGENTS.md](../AGENTS.md) and the [collaboration contract](collaboration.md).
Keep branch-local state out of Git. Preserve immutable runs, failures, maps,
Free-R, pinned diagnostic environments and other authors' untracked work.
Scientific archives are local forensic records, **not automatically portable or
resumable runs**. No scientific payload is included in this documentation update.

Keep this handoff concise. The roadmap owns milestone status, subsystem guides
own behavior, and the periodic/preview ledgers own exact validation commands and
historical evidence. Do not append repeated session diaries or promote a numerical
or software PASS into scientific acceptance.
