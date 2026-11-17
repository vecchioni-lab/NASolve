# NASolve development handoff — Willow

Updated **2026-11-17**. This is the **`willow` branch** handoff, not the
project-wide status of Pine, Cedar or Alder. **W110 is audited; W111 is next.**
Runtime code is W109 (`f732f2ed`); W110 is diagnostic and protocol evidence.
Native refinement activation remains open.
The [machine roadmap](topostitch-roadmap.json) owns milestone status; its
[generated human view](topostitch-roadmap.md) owns the numbered progress queue.

## Read this first: current development edge

The reusable backend can bind source atoms and periodic images, replay declared
recuts, preview bounded bending, and inspect native geometry without selecting a
repaired structure. Whole-window trials remain unselected, capped or failed.
**General sticky-end repair and ordinary recut refinement are not qualified.**
S04/S05/S06 and P01/P02 remain partial; use the roadmap for individual gates.

| Current component | Proven scope | Boundary still open |
| --- | --- | --- |
| W104 `review_pair_coverage` | Read-only comparison of explicit requested/native/additive terms; rejects missing, duplicate, stale, image and parameter mismatches | Caller authenticates complete declarations; no activation |
| W105 `describe_compiled_pair_terms` | Exports terms from the existing compiled recipe and original bound packet | Not a native force or lifecycle qualification |
| W106 `observe_native_pair_terms` | Callback-free actual-manager inventory with checksum-bound Cedar policy checks and exact rational image comparison | Special positions unsupported; source authenticity and active callback policy remain upstream |
| W108 `select_pair_providers` | Plans exact term-level native/additive ownership, including partial individual pairs; conflicts refuse | No activation authority |
| W109 `NativePairRecipe.evaluate_terms` | Evaluates a frozen exact subset using the existing kernels, with per-call binding checks and full/complement derivative controls | No active callback/policy or ordinary refinement lifecycle |
| W107 native composition diagnostic | 107 native core terms plus 17 explicitly missing periodic terms preserve coverage and normalization in the tested managers | Active guarding, provider-independent weighting, exclusions and production refinement remain open |

W107 passed **eight 20/20 directional controls (1,296 evaluations), twelve
negative controls and exact zero-callback preservation**, before and after
explicit select-all rebinding. This was complete native diagnostic execution with
**Phenix 2.2.1-6174**, not optimization or diffraction refinement. It retains native
periodic repulsion; it does not approve an exclusion policy. See the
[W107 receipt](topostitch-periodic.md#w107--native-core-plus-only-the-missing-periodic-terms)
for exact commands, failed preparations, archive checksums and limitations.

## Next bounded work

1. Qualify the separate **active contribution admission/buffer owner** with Cedar.
   The [W110 contract](topostitch-periodic.md#w110--provider-normalization-and-active-contribution-contract)
   is reviewed but not implemented. Keep C331 callback-free; do not detach a callback
   to fake an idle guard or duplicate the reader. Restart must rebuild a trusted
   callable, and cleanup must not overwrite a foreign replacement.
2. Choose and qualify **provider-independent model-level weighting**. W110 shows
   a three-term native→callback move preserves raw forces but shifts normalized
   targets by ~0.026% because native N drops by three. An arithmetic candidate count
   is not a qualified runtime. Then integrate active callback, gradient-buffer,
   normalization and source-policy guards through Cedar's existing
   prepare/frozen-round/actual-manager/final-writer
   owners. The idle C331 observer does not qualify an active callback.
3. Qualify periodic exclusion policy explicitly. Retain repulsion until justified;
   do not activate a symmetry phosphate bond without qualified surrounding angles.
4. Only then compare repaired and no-repair models with matched observations,
   Free-R, budgets and maps; retain geometry/packing, healthy and wrong-connection
   controls, forward/reverse shape cases and B09 final validation.

Use the [ordinary refinement boundary](topostitch-periodic.md#next-ordinary-refinement-boundary)
and [integration contract](topostitch-periodic.md#next-implementation-contract).
Do not fork a refinement runner or repeat passed arithmetic probes as a substitute
for lifecycle integration. Coordinate owner changes with Rowan before native work.
No native jobs remain active at the W110 checkpoint. W108/W109 optional APIs
remain compatible; W110 makes no production normalization change.

## Validation and compatibility

Latest production-code validation, **W109**: **117 focused, 1,964 full tests +229
subtests, and 257 installed tests** passed. Fresh sdist/wheel relocation with source
stages removed, six CLI helps, `pip check`, lean import and Python 3.10 syntax pass.
Six Phenix 2.2.1-6174 derivative cases (20/20 directions each; 972 evaluations),
twelve composition controls and twelve negatives qualify subset arithmetic.
Default results exactly match W108; selected+complement gradients agree within
7.11e-15. The initial panel remains FAILED after four passing cases because the
harness sorted the synthetic fixture; only that fixture was corrected/rerun.
See the [W109 receipt](topostitch-periodic.md#w109--evaluate-the-exact-frozen-additive-subset).
W108 separately qualifies six actual-manager partial-pair provider cases. No new
callback, CLI, packet schema, dependency or ordinary refinement activation.

The latest recorded installed **virtual** Willow/Cedar C338 combination passed
**1,062 tests +22 subtests**, six CLI helps and saved graph/frame/native-link/packing
replay. It was not a branch merge, complete combined suite or native combined
refinement. Seven documentation conflicts and the package-data union required
integration review at that pin. Later Cedar work is outside that qualification;
see the [compatibility receipt](topostitch-periodic.md#installed-c338-compatibility-during-w100).
Check current branches again before integration; textual compatibility alone is
not a runtime test. The W110 read-only check against Cedar `678f0198`
finds all eight consumed owner/profile files byte-identical to the pinned
installation. Shared `autorefine.py` changes merge textually and parse; shared
documentation/package metadata still require integration review. No actual merge
or current combined suite was run. Earlier full virtual-build failures remain recorded, not
superseded by claims of a full green combined suite.

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
