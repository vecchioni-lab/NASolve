# NASolve development handoff — Willow

**Current audit: W219, 2026-11-22. Maintained implementation: W218.**
The existing native input binder now accepts an explicitly selected dictionary-only
parent policy from Cedar C526. Default literal inputs still require compiled
restraints. W214 binds a real X11_22 PostMR checkpoint and original observations;
W215 binds that exact model, original native observation and four reader controls
without inventing pair restraints. S04/S05/S06 remain PARTIAL.

**Latest science:** W219 closes one true 10 Å centroid stress experiment with a
**negative recovery**. Five cycles shorten the four boundary links, but A11 C1′
inverts; worst chain bond/angle deviations are 18.92σ/32.19σ. Final centroid
remains 7.776 Å away, maximum atom motion is 18.486 Å, and Rwork/Rfree are
0.3670/0.4148. Source chemistry/content/data survive; no accepted closure or retry.
[Exact negative evidence](topostitch-periodic.md#w219--a-true-10-a-centroid-stress-case-fails-bounded-recovery).
W217 remains the separate successful small local-repair receiving control.

**Receiving boundary:** W213's private motion fixture has no campaign ancestry.
W214 now supplies a different, genuine current PostMR parent (2603 atoms, 128
canonical residues), but its frozen recipe declares no pairing or movable region.
The saved 55 NARestraints guesses are retrospective evidence, not independent
intent. W215 closes controls-only source binding; neither step creates motion or
ordinary dispatch. [Evidence and limits](topostitch-periodic.md#w214w215--real-checkpoint-and-dictionary-only-parent-binding).

Start with the [machine roadmap](topostitch-roadmap.json) and
[human roadmap](topostitch-roadmap.md). Detailed failed attempts, exact commands
and past interpretations remain in [periodic/native evidence](topostitch-periodic.md)
and [preview/API documentation](topostitch-preview.md), not a second action queue.
The longer pre-consolidation handoff is preserved at Git `86e7489c2314f738bd7fe14f611bddcde7642199`.

W216 now supplies the queued [intrinsic local shoulder proposal](topostitch-preview.md#propose-an-intrinsic-local-backbone-orientation-w216):
247 source/247 relocated installed tests and 48-state real replay. It moves only
O5′/C5′ around fixed P/C4′, retaining local distances and relative C4′ handedness.
Source-PDB precision limits historical parity to 0.001830 Å. Cross-Python
regeneration changes last bits; frozen points replay exact endpoint audits.
No motion permission, scientific acceptance or ordinary workflow follows.

W218 adds [explicit displacement summaries](topostitch-preview.md#measure-explicit-region-displacement-w218)
to the existing mask: 310 source/310 relocated installed tests and identical
saved-endpoint measurements in Python 3.12/Phenix 3.11. Centroid/RMS/max remain
separate; no centerline, correspondence or frame is inferred.

## Current development edge

| Component | Proven scope | Still open |
| --- | --- | --- |
| W214/W215 real parent + typed binding | Exact real checkpoint/data; 225 source/225 relocated installed, 19 real-source checks, Phenix Python 3.11 parity | Independent intended motion, Cedar ordinary request/dispatch and chemical admission |
| W208 maintained parent builder |217 source/217 relocated installed;54 actual-native cold checks, exact W207 prepared state and disposable post-parent failure | Cedar-owned versioned ordinary request/dispatch; C516 early entry qualified |
| W211/W212 intrinsic local recovery | Four matched arms, 38/40 checks per pair and 28 cross-arm; both seeds survive, original chemistry/data retained | General/experimental recovery, residual stereochemistry and maintained proposal consumer |
| W213 source/motion trace | Exact same-parent preview and typed source replay; 18 cold checks | Genuine checkpoint ancestry and Cedar ordinary receiving route |
| W207 larger fixed-flank recovery |4.96 Å maximum displacement, one five-cycle fit,39/41 cold checks; retained source chemistry, content and fixed context | Local geometry investigated in W209–W212; experimental/general recovery |
| W206 original native bytes | Opt-in detached original source observation; 191 source/191 installed and 16 real-source checks × three environments | Explicit native use and ordinary receiving route; no lifetime grant |
| W205 source chemistry + transfer | 42 source site definitions/eight families/3451 retained terms; 72 cold checks; exact post-transfer state/diffraction | Full formal-charge readback and maintained ordinary execution/lifetime route |
| W204 native service composition | C509 + W203/W200; 99 cold checks, actual dry-run/failure; exact W202 prepared state and diffraction | Original-source chemical admission and ordinary lifetime/execution route |
| W203 typed source binding | Immutable parent/report and ordered separate PHIL roles; 175 source/175 installed; real-source 3.12/3.11 parity | Concrete Cedar service and full chemical/ordinary admission |
| W202 shared live collector | Installed Cedar C507; four authenticated reader controls; exact live prepared state and failure cleanup | Maintained source-qualified builder, full chemical admission and ordinary dispatcher |
| W200 native preparation context | One-shot stage order, stable manager, exact W198 mapping, fail-closed result; installed real success/failure | Versioned ordinary execution integration and retained-file lifetime composition |
| W198/W199 native atom order | Candidate/parser and parent/prepared orders separately bound; real OP3 reorder and live parity | Broader conformers, modified moving residues, tensors and registered recuts |
| W196 interior initializer | Registered whole-pair windows, explicit weights and two fixed flanks | Successful general repair; cross-Python whole-preview last-bit audit replay |
| W197 fixed-frame recovery | Three matched native synthetic controls; original data/Free and source topology retained | Residual chemical cost, experimental evidence, larger/general deformation |
| W191–W195 helix measurements | Declared paired-P spans, canonical simple twist and explicit named-state/weighted comparisons | Modified frames, crystal-image assignments, local axes/radii, historical 7SDG provenance |
| W173/W174/W186–W190 input/preparation readers | Exact checkpoint/current parent, frozen execution inputs, original reader controls and observed native support | Complete ordinary chemical/paired-target authority for a real bend |
| W138/W139 counted refinement | Qualified explicit longer protocol and actual final-writer pair readback | Broader efficacy and user-facing enforcement/Doctor activation |
| W149/W154 density inspector | Installed prepared-scene renderer and explicit map/model roles | Stage adoption, source/frame proof, campaign actions and browser/GPU scope |
| Pine editable periodic graph | Intent, previews and source/image correspondence | Faithful recut refinement, seam chemistry and persistent human review |

W200 adds `topostitch_native_preparation.NativeEndpointPreparation`, using the
unchanged W198 endpoint owner. The builder owns actual interpretation and
chemistry/diffraction evidence; the outer worker owns source qualification,
retained-input/process lifetime, native binding cleanup and failed-model disposal.
No returned boolean/None or coordinate mapping alone is chemical authority.
[Contract](topostitch-preview.md#prepare-parent-geometry-once-w200).

W215 broader validation: one complete-suite attempt yielded 1947 passed,
131 skipped, 51 environment failures and 234 passing subtests. All 51 failures
pass on a focused replay with optional Gemmi and permitted test-process cleanup.
No clean full-suite or skipped-case qualification is claimed; no suite rerun.

## Next bounded work

Examine the existing constrained whole-residue motion against saved/native
geometry before considering another diffraction fit. W219 is a closed negative
control, not a reason for an undeclared retry or amplitude sweep. W85 only
qualified small-motion derivatives; W209's broad-direction discrepancy remains.
The 5 Å centerline target is still open. Do not repeat missing-intent searches
or invent a target on the real X11_22 root. Rowan owns ordinary receiving and
native qualification of the one shared W215 dictionary-parent artifact.


**Ordinary integration remains Cedar-owned:** the versioned request must carry the
bound geometry-parent/source and admitted candidate motion. Rowan's **C516**
(`7ed50ffab8ecfcd232a50abfda41c45e9cf545ce`) now owns early validation/finalization/
pending-process ordering and reproduces W208's success and failure natively.
The linked owner receipt binds our exact prior records; do not repeat that panel.
[Receiving handoff](topostitch-preview.md#cedar-native-entry-handoff-c516).

The ordinary receiver still needs W206 bound source, admitted current-parent/
candidate motion, a pending native model/process options, and qualified native
readers/writer. Bind builder, W200 context, input class and W198 mapping from the
same qualified Willow module namespace. Require both context.result() and
builder.result()/evidence(). Source qualification, input/process lifetime and
failed-manager disposal remain with existing outer owners; v3/v9 request and
helper bytes retain their meanings. No extra optimizer or generic quota owner.

W207 remains immutable. W209–W212 close a separate bounded local-recovery
comparison; no failed or completed run is relabelled. Investigator-requested stress
benchmarks are separately **10 Å segment-centroid displacement** and **5 Å from
a declared helix centerline**, not maximum atom displacement or P–P span. W207
actually shifts the unweighted 205-atom centroid 0.253 Å (largest pair centroid
0.885 Å); no local helix centerline is measured. Define
and qualify those measurements and bounded recovery before running them. No
such stress test has run. W206 opt-in bytes must be non-None and source MATCH
must precede movement; ordinary immutable round ownership remains separate from
Alder's frozen-metal budgets and Cedar's counted prepared/native scope.


The shared collector boundary is agreed and tested; the ordinary execution
extension remains proposed. W201's five cold controls show that ordinary v3 has no typed
geometry-only parent role: old capture/default helpers remain readable/unchanged,
while an extra field, proposed policy and untyped sidecar are refused. The
[unfinalized contract](topostitch.md#versioned-parent-preparation-execution-contract-w201)
is named `topostitch-bound-parent-preparation-v1`; its proposed v10 execution
policy and `parent_preparation` field are not implemented or accepted.

Bind existing W173/W174 joins, W200 and current Cedar chemistry/reader intent;
keep the candidate as the ordinary diffraction-model argument. The maintained
builder now exists; its native readers and early ordinary placement still need
the agreed shared source qualification before dispatch. Counted
`original_model` is original pair provenance, not an automatic immediate-parent
geometry reference. Distinguish original observations from a separately computed
parent F-model, and require separate evidence if the latter is requested. Preserve
all old helper bytes, policies and defaults. No new private refinement or request
reader is warranted.

Keep input lifetime separate from model preparation. Hazel reports qualified
Alder `7d84c84d6b16b352f4d2717ce3e8ea8c01718f98`: whole audited-session
admission reserves before owned preflight and stays held through postflight/review;
settlement binds the scientific reader and exact retained-parent grant. Cross-session
request substitution refuses. Owner validation: 146 focused/67 relocated installed;
no new native calls. This is receiving-owner evidence, not Willow combined adoption.
Inner read completion is not outer release or physical reclaim. Unknown/interrupted
sessions remain charged. Alder `3b83edce40202b0595230aa5f92ed6a3c3f102b6` adds
explicit settlement only for newly bound, verified-stopped failed sessions after
completed owned preflight (165 focused/86 installed owner checks; no native calls).
Incomplete preflight and unsealed/old failures remain charged; campaign admission
and physical retirement stay open. Neither Alder delivery is a Willow integration claim.
Reuse this owner rather than adding a second storage/process mechanism.

The real X11_22 PostMR root (2603 atoms) is available and relocates, but lacks the
independently checked pair/stack target and chemical authority of the separate
859-atom canonical diagnostic. Do not fabricate ancestry or infer topology from
stretched distances. W196 is prospective; W163 historical motion is not.

After supported integration, choose an independently authorized target or a
matched generalization control before raising deformation amplitude. Existing
W148/W152/W163/W164/W168/W197 fits and W170 map sampling need not be repeated.
Cedar owns chemical repair; Alder owns cluster scope/storage. Coupled helix
opening/closing remains planned, including sugar/backbone movement; P–P span is
not radius to an axis. [Cluster contract](topostitch.md) and
[shared helix plan](helical-geometry-plan.json) retain those constraints.

User-requested regional helicity generation (9 versus 11 bp/turn) is now a
[late-stage geometric model-building plan](topostitch-preview.md#regional-helicity-model-building-planned),
with explicit step convention, endpoint phase, transition and backbone-repair
gates in the shared helix plan. It adds no implementation and does not displace the current service/chemistry integration.

Density stays in the pipeline: use original fixed data/Free, a recovery interval,
no-op control and both geometry and map review. Early post-bend R deterioration
is not a rejection by itself. After full recovery, worsening Rfree merits map
inspection even below the user's ~0.3 operational gate; above it, reconsider
connectivity/sequence/junction/rotation and other structural hypotheses. These
are scientific investigation rules, not an implemented classifier or permission
for repeated Rfree-guided tuning. No noisy phosphate detector is qualified.

## Validation and scientific interpretation

- W211/W212: four completed Phenix 2.2.1-6174 preflights and four five-cycle
  refinements; 38/40 checks per pair, 28 cross-arm checks. W213: 18 cold source/
  motion/identity checks, zero native calls. No source runtime changes, no new
  install claim and no full-suite repeat. Original scientific artifacts stay local.
  Eight roadmap tests and the synchronized 16-job roadmap audit pass; ChimeraX
  1.12 opens all three checkout models and five view actions in headless validation.
  The graph was visually inspected; no interactive GUI-render claim follows.

- W209/W210: 38/26 cold checks; 31/50 native geometry evaluations, 55 direct
  work-only scattering calls; zero refinement. Exact original source bindings,
  coordinate/data preservation and stopped process records; earlier failed
  adapters/closure retained. W209 full-region derivative disagreement is not
  promoted to a qualified force. No runtime/schema changes or full-suite repeat.

- W208: 217 focused source/217 relocated installed;54 native cold checks on
  one completed Phenix 2.2.1-6174 dry-run and one intentional post-parent refusal.
  Initial last-bit cell-representation refusal is preserved; raw values prove
  at most 2.85e-14 difference, bounded below 1e-10 in the worker reader. All native
  processes stopped; no refinement or full-suite repeat.
- W207: Phenix 2.2.1-6174 actual one preflight/one five-cycle fit;39/41 cold
  checks. Local helical/covalent readback and ChimeraX 1.12 headless three-model/
  five-control check pass; figure visually inspected. No full suite or new runtime code.
- W206: 191 focused source/191 freshly relocated installed; 16 actual-source
  cold checks each in source/installed Python 3.12 and Phenix Python 3.11, identical
  output. Original temporary input/build/install paths removed. No native call.
- W205: 72 cold checks; one Phenix 2.2.1-6174 complete dry-run and one
  source-byte rejection before interpretation/transfer. Original 42 definitions
  match, full prior final state/diffraction retained; profile/server/outer hooks
  restore and both children stop. Zero refinements; formal-charge limits explicit.
- W204: 99 cold checks; one complete Phenix 2.2.1-6174 dry-run and one
  deliberate pre-transfer failure; exact W202 geometry/model/diffraction parity.
  Both children stopped, five outer bindings and Cedar server binding restored.
  Initial import-only failure preserved. No refinements or complete chemistry claim.
- W203: 175 focused source/175 relocated installed tests; 14 real-source cold
  checks each in source/installed Python 3.12 and Phenix Python 3.11, identical
  output. Wrong parent/report and tampered captured controls refuse. Temporary
  original input/build/install paths are gone. Zero native interpretations or
  refinements; existing W200 protocol and native execution policies unchanged.
- W202: 12 cold source checks plus one actual Phenix 2.2.1-6174 dry-run and
  one injected failure, 84 cold checks. All four authenticated controls are False
  before/after interpretation and transfer. Exact prior prepared geometry and
  candidate diffraction survive; failed model is discarded. NCS=True in W200
  is preserved as historical fact, not relabelled. Installed Cedar C507 is source
  pinned; its code is not merged into Willow. No new refinement/full suite.
- W201: five actual cold owner controls, source/input immutability and temporary
  cleanup pass; zero native calls. Proposed execution contract remains unimplemented.

- W200: **160 focused source + 160 relocated installed tests**, Python 3.10 syntax;
  one actual Phenix **2.2.1-6174 dry-run** and one injected preparation failure,
  **81 cold checks**, zero refinements. Complete prepared state/diffraction and
  all three mapping digests match earlier controls. Failed manager is discarded;
  no model rollback/retry is claimed.
- Full-suite attempt was **interrupted**, not passed: 446 passed, 15 skipped,
  133 subtests and five process tests failed on sandbox denial of `/bin/ps`.
  The owned invocation was stopped at the coordinated branch-specific scope;
  a subsequent scoped process listing found no remaining matching test workers.
  Log retained locally. No unrelated process code was patched or retried.
- W199: one completed native dry-run and one injected failure, 71 cold checks;
  initial missing-`openpyxl` startup failure preserved separately.
- W198: 141 source/141 installed tests and nine saved stages/63 cold checks.
  Raw source index and default parser index are distinct. Native D1 OP3 reorder
  was real; W197's existing label-based transfer was already correct.
- W197: three actual dry-runs and three complete five-cycle refinements;
  74 preflight/80 final cold checks. Local chemical cost and fixed-context scope
  remain explicit; no ordinary or experimental acceptance.

See [W200 methods](topostitch-periodic.md#w200--maintain-one-shot-native-parent-preparation)
for exact commands, source/wheel hashes, local evidence and limitations. Older
full-suite qualifications remain their own historical scoped results. No new
merge, scientific payload publication or default activation is authorized here.

## Local science checkout

Latest physical result: GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_fixed-frame-recovery/index.html`.
One figure shows signed phosphate displacement, boundary-bond recovery and the
remaining local phosphate-angle cost. Models are linked/hash checked, not copied.
The associated ChimeraX script uses gray/silhouettes/soft/orthographic/thin rings;
it was prepared and checked, not GUI-executed for W197.

For the user's larger-displacement inspection, GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_half-nanometer-comparison/open_comparison.py`
reuses six checksummed W163/W164 models with five clickable Log comparisons.
ChimeraX 1.12 headless verifies six × 859 coordinates unchanged and all five
view actions; no rendered GUI review or new refinement. Positive recovered
B2/B3 phosphate angle remains ~76.71°; the original ~4.79 Å maximum start
motion is not the residual displacement. All 859 atoms could refine in those
older controls. Manifest and viewer evidence stay local.

W198–W206 add no geometry effect to illustrate. W207 now supplies a new
three-model comparison under `ScienceCheckouts/Linden/2026-11-21_fixed-flank-recovery/`
(`review.html`, `open_comparison.py`), including the unresolved A11/A14 close-ups. W206 binding/installation
receipts are under `NASolve:branch-artifacts/willow/w206-source-observation-binding/`. W205 source-chemistry/transfer
receipts are under `NASolve:branch-artifacts/willow/w205-source-chemistry-transfer/`. W204 local receipts are under
`NASolve:branch-artifacts/willow/w204-parent-service/`; see the
[service composition audit](topostitch-periodic.md#w204--compose-the-installed-cedar-parent-service). W203 cold/installation receipts
are under `NASolve:branch-artifacts/willow/w203-source-input-binding/`. W202 source/live receipts are
under `NASolve:branch-artifacts/willow/w202-typed-native-builder/`. Earlier receipts
remain under NASolve anchor `branch-artifacts/willow/w198-native-handoff/`,
`w199-live-preparation/` and `w200-native-context/`; checksummed references are in
the machine roadmap. Scientific runs, failed attempts and native observations
remain immutable/local. Reuse the existing inspector for the next physical result.

## Scientific limits and demonstration gates

- **Bending:** W100 uses actual-input tethers and three matched controls. All
  pass full/PDB-rounded derivative checks but stop `NOT_CONVERGED_LIMIT`;
  endpoints remain `REVIEW`. Some individual packing/torsion/plane terms worsen.
  [Exact results and inspection files](topostitch-periodic.md#w100--source-displaced-controls)
  are local evidence, not selected repaired models. W91 found no benefit from the
  small coarse polish; do not restart it without a different justified question.
- **Diffraction and density:** W34 found no meaningful held-out benefit from
  bend-plus-cleanup (Rfree .2276 versus .2274 for cleanup), with worse bond/angle
  RMSDs. W140 adds exact saved-map sampling and identifies a persistent C102
  phosphate difference feature; it does not identify its cause. S06 still needs
  healthy/noisy/displaced calibration before sustained negative-backbone-density
  detection. Noise, resolution,
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
