# NASolve development handoff — Willow

Updated **2026-11-17**. **W126 registered continuation and inherited input
adaptation are audited. Ordinary AutoRefine ownership is next.** This is Willow's
handoff, not the project-wide status of Pine, Cedar or Alder. Willow's latest
periodic/factory source is W118; counted execution/continuation is committed on
Cedar through C383. These audits are not a whole-branch merge or supported release.

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
| W126 / C382–C383 continuation | Validated registered parent, preserved original intent, fresh rebind/preflight/admission; existing C278 namespace-only restraint copies | Ordinary AutoRefine/Doctor execution and broader protocol/chemistry |
| W125 / C381 admission | Durable original/current request, exact prepared state, immutable admission, complete native cycle and truthful failure outcomes | No ordinary CLI activation or scientific acceptance |
| W123 / W126 scientific readback | Modest local contact/plane improvement in saved endpoints; later descendants flatten further | Residual defects, worsening R stats, unqualified backbone/packing/density; descendants have no matched efficacy control |
| W118 same-frame recipe rebind | Coordinates/B/ANISOU may change with exact identity, chemistry and frame invariants | No renamed/reordered atoms, changed occupancy/chemistry or frame migration |
| W100 bending / existing Pine graph | Bounded source-driven trials, periodic identity and preview/cut machinery | Coupled physical repair, ordinary recut refinement and final demonstration gates |

Exact numerical results, failures and pins are in the
[periodic/native ledger](topostitch-periodic.md). Historical probes are evidence,
not another work queue; do not repeat them because this handoff is shorter.

## Next bounded work

1. Join the qualified counted path to the **existing AutoRefine owner** with an
   explicit supported protocol, input proofs and normal checkpoint publication.
   Follow the [W126 integration contract](topostitch.md#ordinary-owner-integration-boundary-w126-planning).
   Rowan owns shared execution; Linden owns periodic geometry/factory semantics.
   First close the final-writer/checkpoint-model binding gap: Rowan's read-only
   C383 follow-up accepted a checksum-valid previous model substituted in a copied
   registry. Actual C382 output hashes are independently correct; reader
   rejection of that substitution is a separate pending gate.
   C278 PHIL namespace adaptation is now consumed; terminal-source additions and
   chemistry projections remain distinct gates. C291 is whole-base transport.
2. Preserve one declared working frame and original data/Free-R. Do not turn the
   diagnostic PDB-cell override into a campaign default or loosen exact compiled
   bindings to hide precision differences. W118 is a same-frame rebind, not a
   crystallographic setting conversion.
3. Keep the first owner-level counted result unselected REVIEW. The qualified
   native protocol is deliberately narrow: one all-site coordinate cycle,
   1–10 iterations, one process and fixed unit weights, with target-changing
   phases disabled. Ordinary automatic weights/ADPs/scaling are not qualified by
   relabelling this diagnostic. Reuse existing owners; no new optimizer.
4. After that join, qualify broader native scope and periodic exclusions
   deliberately, then matched candidate/no-repair controls with geometry, packing
   and diffraction/density evidence. Retain repulsion while exclusions are open;
   never activate an isolated symmetry phosphate bond.

**W122 remains planning-only:** the first intended user-facing application is
[explicit canonical sticky-end enforcement](topostitch.md#explicit-sticky-end-enforcement-during-refinement-planned-w122),
then separately qualified plane-only mismatch hypotheses. Automatic inference and
large-bend repair follow later. No CLI/default activation follows from these docs.

## Validation and scientific interpretation

- **W126 / C382–C383:** 360 relocated installed tests +13 subtests for C382;
  a separate 62-test installed adaptation panel for C383. Independent 298-file
  committed-source checks for both, 24 unchanged frozen native files per round,
  relocated cold registry reads with no launches/writes. Two complete registered
  Phenix 2.2.1-6174 cycles preserve intent and parent-output linkage; both stay
  unselected REVIEW. [Exact W126 evidence](topostitch-periodic.md#w126--audit-registered-continuation-and-inherited-input-adaptation).
- **W125 / C381:** actual complete cycle, unsupported-scope refusal and final-MTZ
  failure independently audited; final 347 installed tests +13 subtests.
  [Exact admission evidence](topostitch-periodic.md#w125--audit-durable-counted-admission-and-native-outcomes).
- **Latest Willow source W118 / `c08f3370`:** 237 focused, 2,033 full tests +229
  subtests, 326 installed tests; relocated installation, six CLI helps, pip check,
  lean import/Python3.10 and complete native compiler/evaluator checks.
  [Source validation](topostitch-periodic.md#w118--rebind-frozen-pair-intent-to-a-compatible-child).

The **12,138-test /284-subtest W112/C366 source-only** full suite and later W121
joined-package checks remain historical, not current C383 full-suite results.
Current peer panels are focused; no duplicate native/full-suite run was launched
by Linden for these audits. Integration/merge qualification remains separate.

The matched W116/W123 control shows maximum extra motion about **0.034 Å** and
modest selected-pair improvement, with no Rfree benefit. Subsequent C382 descendants
reduce PDB G·C plane mismatch **18.69→17.77→16.77°**, but logged Rfree worsens
**.2599→.2609→.2611**. Those descendants lack matched native-only siblings; do not
attribute all changes to the added terms or claim repair. Full-precision native
and serialized-PDB measurements remain distinguished.

## Local science checkout

Use the shared **GitHub workspace** anchor, relative path
`ScienceCheckouts/Linden/2026-11-17/review.html`. Five local files provide a compact
scientific diagram, matched display-only PDBs, a ChimeraX script and measurements.
The declared symmetry image, contact-distance monitors and fitted base planes are
visible; no alignment, motion magnification or chemical bonds are added. The
coordinate-only derivatives omit ANISOU/LINK and are not refinement inputs.
ChimeraX 1.12 headless loading, figure inspection and local-link checks pass;
automated browser layout preview is unavailable because local-file URLs were blocked.
Follow the [lightweight checkout policy](collaboration.md#lightweight-science-checkouts).
Keep raw data and reports local; this is not permission to publish scientific files.

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
