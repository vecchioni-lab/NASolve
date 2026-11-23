# NASolve development handoff — Willow

**Current audit: W234; maintained implementation: W233, 2026-11-23.**
The existing native input binder now accepts an explicitly selected dictionary-only
parent policy from Cedar C526. Default literal inputs still require compiled
restraints. W214 binds a real X11_22 PostMR checkpoint and original observations;
W215 binds that exact model, original native observation and four reader controls
without inventing pair restraints. S04/S05/S06 remain PARTIAL.

**Latest science:** A constrained geometry warm-start now lets the original
five-cycle protocol recover the 10 Å synthetic perturbation without the direct
attempt's sugar inversion. W223 reaches its 20-iteration cap (not convergence);
W224 retains 126/126 sugar signs, gives 1.612–1.621 Å flank links and
Rwork/Rfree 0.007123/0.007274. Three moving-region bond/angle outliers remain,
including one newly worsened angle. All original atoms, chemistry and data stay.
The endpoint returns near source; no distinct 1 nm placement or experimental
repair is claimed. W225 shows that the requested centroid needs at least
29.011 Å between fixed anchors versus the 21.057 Å source pair-center path.
[Exact staged result, residuals and feasibility limits](topostitch-periodic.md#w222w225--corrected-collective-warm-start-and-matched-receiving-refinement).

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

W227 adds [an explicit measurement subset](topostitch-preview.md#keep-the-measured-core-fixed-when-a-window-expands-w227)
inside the unchanged complete-motion validation: 392 source/392 installed tests,
21 saved-endpoint checks in each of source, installed 3.12 and Phenix 3.11.
This prevents changing the scientific target by including newly editable flanks:
the saved core's 10 Å becomes 7.143 Å if the unchanged flanks are averaged in.
No window expansion or new recovery was executed; default reports and motion
arithmetic remain unchanged.

W228 independently qualifies the Willow-facing boundary of Cedar C539's
[registered phosphate reader](topostitch-periodic.md#w228--review-the-shared-registered-phosphate-reader):
20 canonical/16 exact-checkpoint cold checks, no new native call. It reuses the
shared graph, resolves actual coordinate labels and the reciprocal image, and
keeps chemical intent distinct from the original checkpoint's nonbonded-only
record. This source-frame observation is not a recut, force grant or branch merge.

W230 adds opt-in [internal stacking descriptors](topostitch-preview.md#measure-internal-stacking-placement-w230)
from existing canonical frames: 116 source/116 relocated installed tests and
96 cold checks per saved-model readback with exact source/installed parity.
The initial large translation preserves plane angles but raises maximum lateral
ring-centroid offset from 3.50 to 10.53 Å; staged recovery returns near 3.48 Å.
This measures spacing and lateral placement separately from within-pair geometry
and twist. It does not establish overlap, an ideal structure or seam closure.

W233 carries those [stacking measurements through named-state comparison](topostitch-preview.md#compare-internal-stacking-between-named-states-w233):
125 source/125 relocated installed tests, 254 cold checks per readback and exact
parity. Explicit directed correspondence and independent strand/metric coverage
stay intact. Actual C543 PDU rings remain unsupported while their P spans are
retained. No new force/native run or full-suite repeat; W230's complete suite
remains tied to its recorded earlier checkpoint.

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

W226 closes the maintained collective-trial contract: 378 source/378 relocated
installed tests and 26 cold installed-native checks. The exact W223 optimizer
trajectory/end coordinates reproduce; two derivative audits and baseline
restoration pass, with 77 callbacks/80 outer geometry evaluations. No new fit,
writer, rounded-endpoint admission or ordinary activation follows. The cap
remains distinct from convergence. [API, commands and limitations](topostitch-preview.md#run-a-bounded-collective-trial-w226).
The W226/W227 evening slice deferred the complete suite to the merge gate.
For W230, the coordinated complete Willow checkpoint run passes: **2481 passed,
3 skipped and 234 passing subtests** at `c4b95b20b1d045c5f06a9572c3774b3da952c6a2`.
Skipped cases remain unqualified; this software result is separate from native science.

[W229's route preflight](topostitch-periodic.md#w229--the-current-interior-window-cannot-simply-grow)
finds no larger declared interval for the same 205 atoms and both fixed flanks:
13 cold checks/three refused anchor releases, no new coordinates or native run.
The source B chain has seven sites and the discovery boundaries remain unknown.
Rowan confirms that the reviewed B7–B1 connection does not independently grant
movement of A8–A9 or A15–A16. Keep that junction choice explicit; representation
boundaries must not be relabelled as chemical sticky ends to obtain a window.
A fresh terminal/coupled/periodic declaration is the next prerequisite; neither
a bigger pair cap nor W227's reporting subset creates movement permission.
[W231's independently checked context](topostitch-periodic.md#w231--distinguish-the-central-crossover-from-a-stacked-duplex-step)
finds the central seam bases nearly perpendicular (81.976°) despite the 2.795 Å
O3′–P gap. Covalent continuation must not imply a stacking-plane restraint.
[W232 now binds a six-atom connecting-backbone scope](topostitch-periodic.md#w232--bind-a-six-atom-connecting-backbone-scope)
with all 856 other atoms held: 23 cold checks, no displaced candidate or native
run. All captured base-plane terms are fixed; complete image-force restart
remains Cedar-owned. Next test the original 2.824 Å ancestor under this narrow
constraint once that force path is ready. Do not re-perturb the already closed
child or repeat the whole-model fit; whole-pair junction mobility stays separate.

[W234's donor graft](topostitch-periodic.md#w234--a-closed-seam-can-still-strain-the-fixed-sugar-boundaries)
closes that seam but strains the two fixed-sugar bonds (−9.60/+16.45 native
sigmas), despite retained chirality signs and unchanged stacking. Twenty-two
cold checks, one diagnostic PDB, no fit or acceptance. This rules out simple
coordinate transplantation; it does not rule out a constrained six-atom solution.
The next optimization must retain those boundary terms with the full seam forces.

**Internal helix focus (Simon, 2026-11-22):** retain the rough but recoverable
molecular placement as a useful intermediate, then explicitly assess stacking
recovery within the duplex. Track neighbouring base-plane orientation, spacing,
lateral offset/overlap and twist before deformation, after placement and after
restrained recovery, including transitions into fixed flanks. Distinguish
within-pair coplanarity from stacking between successive pairs. Allow genuine
curvature and nonuniform twist; do not force every plane parallel or impose an
uncalibrated universal cutoff. A connected backbone, retained sugar signs or
better R factors alone do not qualify internal stacking. Reuse the existing
pair/frame measurements and Cedar/NARestraints owners; this clarifies the current
placement/recovery gate rather than starting another subsystem or run tonight.

The next experiment must answer a new question, not repeat W224:

1. **Feasible window:** declare source, intended endpoint/image, ordered pairs,
   fixed flanks, protected junctions and a stable measurement core distinct
   from the editable window. Apply W225's necessary center-path
   bound before fitting; allow only predeclared window expansion up to those
   hard stops. This bound cannot certify DNA curvature, stacking or torsion.
2. **Independent placement:** qualify the unchanged reference and freeze a
   target or map-supported region independently of the initializer. Test a bend
   or straightening direction not generated and recovered through the same
   six-parameter family. Declare the comparison, call budget and stop rules
   before launch; use geometry warm-start plus matched restrained recovery.
3. **Scientific readback:** compare final coordinates, individual stacking and
   covalent residuals, sugars, source content, contacts and original FreeR/data.
   Inspect supported/unsupported density before interpreting R differences.
   Report a failure or near-reference return honestly; low synthetic R is not
   evidence of a distinct experimental structure.

The 5 Å centerline target remains separate and unrun until the local axis is
defined. Rowan owns the ordinary receiving boundary and concrete 5W6W seam
intent (`9d5030fbc06f436f428ec2cb88308e73c72b8c74`,
`docs/recipes/5w6w-central-continuation.json` on Cedar): B7 O3′ to B1 P through
`-y,x-y,z`, reciprocal `-x+y,-x,z`. It is a closed periodic strand, so an identity
ASU representative can retain the cycle; do not force every connection into a
single image-spanning tree. Preserve B1 P/OP1/OP2 and separate D1 terminal intent.
The W196/W219 interior fixture fixes A9/B7 and A15/B1 as its two flanks:
its mask cannot close the B7–image(B1) gap. C539 supplies connectivity intent,
not permission to release those anchors. Declare a separate terminal/coupled
window and its partner/junction context before a seam-placement experiment.
That exact declared source must be verified before any new run; no missing-intent
search or invented X11_22 motion is permitted. This note does not qualify a new
native seam restraint or all three junction closures.

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
and qualify those measurements before claiming either target. W219 has now
run and rejected direct recovery; W223/W224 demonstrate staged synthetic
recovery. The centerline test remains unrun. W206 opt-in bytes must be non-None
and source MATCH
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

Latest read-only science: GitHub anchor
`ScienceCheckouts/Linden/2026-11-23_stacking/index.html`. One visually inspected
figure distinguishes plane angle, normal spacing and lateral displacement in
both strands, and the report explains the nearly perpendicular crossover.
It links the existing ChimeraX comparison rather than copying more models.
Source hashes and links pass; browser rendering is not claimed.


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
