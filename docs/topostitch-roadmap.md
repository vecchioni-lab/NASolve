# TopoStitch and Pine completion roadmap

**Current audited work queue: 2026-11-15.** Generated from
[the machine-readable ledger](topostitch-roadmap.json); edit that ledger and run
`python scripts/audit_topostitch_roadmap.py --write`, then `--check`.
This is one queue with two linked tracks, not two competing implementations.
The [design](topostitch.md) owns semantics, the [handoff](development-handoff.md)
owns the current code/validation edge, and cited evidence owns scientific claims.
A recut changes representation; a bend changes the physical structure. Neither
operation authorizes a chemical nick or chemistry change.

**Current update: W76 — Represent captured native contacts in chosen crystal images.** Next: W77.

Use these numbers in human updates. Exact commits remain in the machine ledger;
earlier history is not renumbered. An update number does not close a scientific gate.

## Recent Willow updates

| Update | Work | Record |
| --- | --- | --- |
| W67 | Resolve explicit representation-boundary partners | RECORDED |
| W68 | Inspect source seam angles and proxy persistence | RECORDED |
| W69 | Audit installed virtual Willow/Cedar integration | RECORDED |
| W70 | Describe verified graph identity before building a cut | RECORDED |
| W71 | Preserve angle images through explicit diagnostic reconstruction | RECORDED |
| W72 | Audit complete reference-frame geometry and native entry boundaries | RECORDED |
| W73 | Keep complete source-frame bindings through explicit reindexing | RECORDED |
| W74 | Check joint diffraction geometry and actual model-copy boundaries | RECORDED |
| W75 | Observe native copy weighting and report consumers | RECORDED |
| W76 | Represent captured native contacts in chosen crystal images | RECORDED |

## Finish lines

- **First explicit stitch:** One explicitly chosen canonical connection can be placed, locally qualified, compared against a matched refinement control and inspected as an immutable unselected child (S01, S03-S07).
- **Campaign stitching:** Add qualified end inference and bounded campaign-local transfer/review (S02, S08), without repeated member prompts or silent promotion.
- **Pine ASU slicing:** A scientist can choose, preview and materialize a faithful ASU cut, prove physical/scattering invariance, preserve seam chemistry and complete the persistent graphical review/refine loop (P01-P06).

## Current order and audit discipline

**Immediate focus:** F02, S03, S04, S05, P01.
The two tracks share F01/F02. Intact-duplex repair does not require finishing
the whole ASU editor; ASU slicing cannot be used to disguise a physical gap.
Prototype work may precede a dependency, but scientific closure cannot.

- **Stitch:** F01 → S01 → F02 → S03 → S04 → S05 → S06 → S07 → S02 → S08.
- **Pine:** F01 → F02 → P01 → P02 → P03 → P04 → P05 → P06.

Audit at every substantial checkpoint, not only at the end of a session:

1. Read this queue and the current handoff at session start; identify the job and its exact missing acceptance gate before coding.
2. At each substantial tested/pushed slice, native result, changed assumption, blocker or handoff, update delivered scope, evidence, status and next action together; rerun the roadmap audit.
3. A job closes only when every criterion is supported in the declared scope and dependencies are qualified for that same scope. Unit tests, optimizer convergence, native interpretation and scientific/human acceptance are distinct.
4. Keep partial/negative results and original caveats. Reopen a closed scope when new evidence contradicts it; record why rather than silently rewriting a pass.
5. Before a new helper or subsystem, check existing Pine, NARestraints, Cedar and campaign owners. Missing shared interfaces are a coordination task, not a reason to fork their machinery.
6. Do not advance sideways into deferred chemistry, providers or elaborate UI polish to avoid a failed physical gate. Keep failed/ambiguous/no-op outcomes legitimate.
7. Validate focused behavior and installation during development; complete integration/full regression, native/platform/relocation and human checks before a supported release or merge. Pushing experimental work does not authorize merging.
8. Keep scientific inputs/results local unless explicitly authorized for publication. Runtime artifacts use declared anchors and checksums; this roadmap grants no runtime permission.
9. Build an input-driven general method, not a fit to named benchmark structures or datasets. Keep fixture-specific identifiers/transforms in requests, and require independent structure/symmetry and forward/reverse controls before widening supported claims.

**Status meanings:** SCOPED_COMPLETE closes only its stated supported scope;
PARTIAL records delivered work with open acceptance; OPEN has not met its gate;
DEFERRED is outside the current finish line. COMPLETE requires the full declared
gate. The audit script checks consistency and references, not scientific truth.

## Shared foundations

| Job | Laboratory outcome | Status | Depends on |
| --- | --- | --- | --- |
| [F01](#f01) | Bind the intended construct to exact model inputs | SCOPED_COMPLETE | — |
| [F02](#f02) | Prove which symmetry images are physically distinct | PARTIAL | F01 |

<a id="f01"></a>
### F01 — Bind the intended construct to exact model inputs

Keep logical sites, coordinate copies, chemistry intent and immutable source identity distinct.

**Delivered:** Existing Pine registration resolves explicit copies and logical sites; TopoStitch verifies model/manifest bytes and actual residue identities.

**Closure audit:**

- Explicit mapping survives renamed/split chains, numbering changes, partial copies and relocation without guessing missing sites.
- This closure covers backend identity plumbing only; authoritative live Scout wiring, symmetry cuts and automatic chemistry are excluded.

**Next action:** Reuse the existing registration and anchored-artifact APIs; reopen only for a demonstrated missing interface.
**Evidence:** [E_SOFTWARE](#e_software), [E_REGISTRATION](#e_registration).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="f02"></a>
### F02 — Prove which symmetry images are physically distinct

Give both tools exact atom/site image identity, including stabilizers, reciprocal operators and lattice translations.

**Delivered:** Metric-bounded periodic enumeration and exact reciprocal image records exist; physical orbit distinctness is still explicitly unvalidated. Optional selected present-atom orbit/overlap audit reports stabilizer observations, coincident source labels and uncertainty without merging identities; public 8D93 selected coordinates are distinct within that scope. Improving serialized fits repeat the exact selected-image coincidence audit; ambiguous moved candidates are withheld without re-searching partner indices. W47 binds exact forward/reciprocal incidence to fresh selected source/transformed atom audits. Periodic fitting requires one partner in that scope; screw/centering/translation and ambiguity controls pass. Complete molecular/global identity remains open. W50 extends the same bounded orbit engine to all present ATOM/HETATM records, retaining unregistered content and occupancy/identity ambiguity. Two exact public-derived sources have no coordinate-orbit coincidences; physical molecular identity remains open.

**Closure audit:**

- Qualify selected atom/site orbits and coincident/special-position cases; do not infer identity from endpoint centers or duplicate labels.
- Check nonorthogonal cells, screw/centering operations, self images, coordinates outside the cell and bounded failure; preserve uncertainty instead of merging ambiguous sites.

**Next action:** Qualify physical partner capacity and complete molecular/image equivalences; the selected-source coordinate precondition is now consumed by periodic fitting.
**Evidence:** [E_SOFTWARE](#e_software), [E_IMAGE_AUDIT](#e_image_audit), [E_POST_IMAGE](#e_post_image), [E_SINGLE_EDGE_CAPACITY](#e_single_edge_capacity), [E_PRESENT_MODEL_ORBITS](#e_present_model_orbits).
**Last audit:** 2026-11-14, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/19a58a2ee08cb0ed33b18b821b0bab02d61f1ed9); All-present-coordinate observation only; F02 remains PARTIAL, special-position identity and molecular graph equivalence remain open..

## Roadmap A — working sticky-end repair

| Job | Laboratory outcome | Status | Depends on |
| --- | --- | --- | --- |
| [S01](#s01) | Inspect explicitly declared duplex ends | SCOPED_COMPLETE | F01 |
| [S02](#s02) | Find eligible ends from design and damaged-model evidence | PARTIAL | F01, S01 |
| [S03](#s03) | Choose a defensible periodic connection scheme | PARTIAL | S01, F02 |
| [S04](#s04) | Place an intact duplex by bounded bending or straightening | PARTIAL | S03 |
| [S05](#s05) | Close and qualify the local atomic geometry | PARTIAL | S04 |
| [S06](#s06) | Demonstrate improvement against diffraction data | PARTIAL | S05 |
| [S07](#s07) | Expose one ordinary, inspectable repair trial | PARTIAL | S06 |
| [S08](#s08) | Run bounded opt-in campaigns and transfer schemes | OPEN | S02, S07 |

<a id="s01"></a>
### S01 — Inspect explicitly declared duplex ends

Describe existing ends and canonical pairing geometry without moving atoms or selecting a partner.

**Delivered:** Verified end frames, canonical NARestraints contact observations, strict manifests and explicit incomplete outcomes are implemented.

**Closure audit:**

- Known explicit ends produce source-bound observations; missing atoms, free ends and unsupported chemistry remain visible.
- Closure is limited to the declared canonical PDB scope, not automatic end discovery or valid stereochemistry.

**Next action:** Reuse this inspector as the observation layer for all later trials.
**Evidence:** [E_SOFTWARE](#e_software).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="s02"></a>
### S02 — Find eligible ends from design and damaged-model evidence

Reduce manual end declarations while retaining true nicks, protected junctions, uncertainty and user intent.

**Delivered:** Declared chemical routes/core pairs can produce logical ends and windows. NARestraints run-based recovery was reviewed but is not integrated.

**Closure audit:**

- Reuse NARestraints geometric seeds and weak-pair run rescue through logical routes; preserve alternatives, gaps, missing coverage and explicit do-not-connect declarations.
- Validate intact and mangled models, repeated/single-base overhangs and false neighbors; a guessed pair list cannot silently become complete topology.

**Next action:** Build a bounded evidence adapter after the explicit-placement physics is qualified; do not reimplement the guesser.
**Evidence:** [E_SOFTWARE](#e_software), [E_NAR_REVIEW](#e_nar_review).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="s03"></a>
### S03 — Choose a defensible periodic connection scheme

Identify which duplex ends should meet and in which image/register, with a no-connection alternative.

**Delivered:** Exact nearby images and factorized one-partner alternatives exist; no physical/global assignment is approved. Periodic fitting now returns IMAGE_IDENTITY_REVIEW_REQUIRED with zero solver calls for selected-coordinate coincidences or occupancy uncertainty; no connection is automatically selected. W47 binds exact forward/reciprocal incidence to fresh selected source/transformed atom audits. Periodic fitting requires one partner in that scope; screw/centering/translation and ambiguity controls pass. Complete molecular/global identity remains open.

**Closure audit:**

- A selected edge has verified physical image identity, sequence/register/orientation and capacity; wrong, ambiguous, self-orbit and impossible cases stay distinct.
- Standalone use binds a concrete choice; opt-in inference freezes its scope and alternatives without creating undeclared covalent links.

**Next action:** Close one explicit canonical periodic pairing before broad automatic scheme selection.
**Evidence:** [E_SOFTWARE](#e_software), [E_IMAGE_AUDIT](#e_image_audit), [E_SINGLE_EDGE_CAPACITY](#e_single_edge_capacity).
**Last audit:** 2026-11-14, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/c887c65ea966b3a7107a1220289fde646587e875); Exact one-edge incidence conditional on selected present-atom coordinate audit; no global/molecular identity or connection approval.

<a id="s04"></a>
### S04 — Place an intact duplex by bounded bending or straightening

Move a usable duplex toward the chosen connection while preserving local residue geometry and fixed boundaries.

**Delivered:** Explicit tapered previews and one-window six-parameter fitting work; ANISOU, anchors, source bytes, budgets and rounded-output limits are tested. Three predeclared tighter-backbone public controls retain exact native definitions/proxies and avoid the original added angle outlier while improving the pair target less; no successful closure claimed. Schema-2 fit/preview adds nonbridging phosphate angles and circular epsilon/zeta/alpha changes; schema-1 replay preserved. Native public 8D93 comparison adds no new severe captured scalar outliers under the explicit development policy.

**Closure audit:**

- Known-answer straight-to-curved, bent-to-straight and changed-direction cases recover within predeclared scope; healthy controls do not receive unjustified changes.
- Qualify whole-pair window expansion, nonuniform curvature and finite failure without crossing protected junctions. A fixed taper is initialization, not measured conformation.

**Next action:** Use the current fitter as a baseline; qualify one physical connection and expand only when the smaller window fails.
**Evidence:** [E_SOFTWARE](#e_software), [E_NATIVE_8D93](#e_native_8d93), [E_TIGHTER_NATIVE](#e_tighter_native), [E_EXTENDED_BACKBONE](#e_extended_backbone).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/6fc48984b5170a2411f576ab3262826963384226); Schema-2 source-change coverage and matched native diagnostic; no scientific closure.

<a id="s05"></a>
### S05 — Close and qualify the local atomic geometry

Turn a plausible placement into a chemically usable candidate before refinement is trusted.

**Delivered:** Three public 8D93 native interpretations preserve atom/proxy membership. The fitted candidate still adds one severe captured angle deviation. Three predeclared tighter-backbone public controls retain exact native definitions/proxies and avoid the original added angle outlier while improving the pair target less; no successful closure claimed. Schema-2 fit/preview adds nonbridging phosphate angles and circular epsilon/zeta/alpha changes; schema-1 replay preserved. Native public 8D93 comparison adds no new severe captured scalar outliers under the explicit development policy. Local native exact-image bond/angle values and gradients qualified for the declared diagnostic; matched fixed-base backbone relaxations pass endpoint/capture checks and resolve three source angle outliers, with iteration-limit caveats. Synthetic and public probes identify unsupported raw native plane gradients; Cartesian image pullback with Cedar existing parallelity correction passes the declared derivative controls. A shared checked Cartesian image/gradient core now drives the viewer and native probe, retaining repeated ASU contributions and failed raw native controls. Local masked native controls bind explicit movement scopes, check every movable Cartesian derivative and compare cleanup versus chosen contacts, with and without existing core-pair terms; native readback remains REVIEW. Complete emitted NARestraints recipes pass local masked derivative/readback checks. Native bond edits demonstrably change exclusions/LINK bookkeeping. Broader bend plus fixed-base cleanup removes its added scalar outlier but worsens other periodic contacts; no candidate is promoted. A thin read-only packing comparator now authenticates/replays Cedar directed native captures, matches relative symmetry transforms and retains per-contact regressions/multiplicity; native capture lifecycle remains owned by Cedar. Native added-term arithmetic passes a bounded probe, but selection/rebuild drops the callback and normalization/enablement need explicit policy; no supported production adapter is claimed. W37 provides a reusable complete canonical pair recipe packet and native additive evaluator, with exact atom/image binding and explicit Cedar correction; independent derivative review outcomes remain visible. W38 adds explicit bounded coordinate masks and a direct native/pair/tether evaluator using Cedar owners; source and perturbed full-coordinate checks pass for two movement scopes and an independent 7R96 mask, with no optimization or scientific acceptance. W39 reuses Cedar capture authentication and trusted native reconstruction, matching all initial observed inventories/ASU pairs before masked evaluation; three native controls reproduce W38 and no optimizer or complete exclusion-policy proof is claimed. W40 binds full-precision points and exact serialized PDB bytes to the explicit mask, then reuses Cedar native mechanics/selected-environment and existing packing review. Explicit Cartesian ANISOU preservation and local collateral regressions remain visible; no optimization or scientific acceptance. W41 composes a bounded native optimizer with complete initial/full-precision/serialized derivative gates and a matched cleanup control. Five native trials and fresh rounded readback pass the declared numerical checks; all remain iteration-capped with individual packing regressions and no acceptance. W42 extracts one installed captured-job API, preserving the CLI/native results and reusing Cedar observation/process owners. Installed/relocated and temporary same-package compatibility checks pass; uncertain process ownership escapes with retained evidence. No branch merge or scientific acceptance. W43 adds explicit full-precision/rounded fixed-manager ASU endpoint observations through existing Cedar capture/review owners. Five controls agree with independent rounded native target/gradient readback; changed neighbor entries contribute zero in these cases. Binary displacement rounding, per-contact changes and failed evidence remain explicit; no physical acceptance. W44 attributes every native pair term, verifies complete container sums and retains selected/core changes for all five endpoints. Cleanup exposes individually worsening pairs; compact JSON preserves old review tables. No objective or acceptance change. W45 uses existing APIs for a matched core-only control against the paired trial. Complete derivative/endpoint/fresh-readback checks pass; intended-contact benefit is separated from core preservation, with capped outcomes and packing regressions retained. W46 composes Cedar native torsion/plane kernels into endpoint observations with explicit live-policy, single-proxy and full-family target/gradient checks. Six controls retain individual regressions and unchanged fixed terms; no chemical acceptance or ordinary refinement route is added. W51 predeclared500-iteration paired/core-only controls reproduce the old200-iteration traces, then retain native rounding line-search failures; no candidate or endpoint qualification follows. W53 fresh native contexts reproduce both W51 last accepted points exactly and pass unchanged complete612-variable derivatives. Predeclared directional probes show score quantization and local steepest-direction quadratic decreases below one score ULP; this supports a precision limit, not convergence or acceptance. W54 separately audits only callback-confirmed last accepted points after optimizer errors. Both native W51 trajectories/errors reproduce exactly; full/rounded612-variable diagnostics pass and original FAILED/no-adoption status remains. Source drift, absent accepted steps, budget shortage and partial diagnostic failure remain explicit. W61 reuses existing read-only native endpoint observation for both W54 failed accepted points under a common complete recipe. Source/full/rounded cases reproduce; scalar and selected/core-pair improvements coexist with individual packing/torsion/plane regressions. Both original optimizer failures persist; no candidate, new threshold or acceptance.

**Closure audit:**

- Audit and, where qualified, relax all affected backbone/sugar geometry, chirality, stacking, planes and periodic clashes; retain unchanged/protected regions and intended contacts.
- Prove native enforcement for the supported symmetry case. Bond-only constraints, source-relative change limits and successful interpretation cannot substitute for full local qualification.

**Next action:** Qualify affected chemistry and complete ordinary native enforcement through Cedar before a supported repair/refinement route. Preserve failed/capped outcomes; passing accepted-point derivatives do not justify tolerance relaxation or adoption. Continue shared physical identity and Pine preview/scattering gates without treating recutting as repair.
**Evidence:** [E_NATIVE_8D93](#e_native_8d93), [E_TIGHTER_NATIVE](#e_tighter_native), [E_EXTENDED_BACKBONE](#e_extended_backbone), [E_NATIVE_TRANSPORT_RELAX](#e_native_transport_relax), [E_NATIVE_PLANES](#e_native_planes), [E_TRANSPORT](#e_transport), [E_MASKED_NATIVE](#e_masked_native), [E_PACKING](#e_packing), [E_NATIVE_CALLBACK](#e_native_callback), [E_PAIR_RECIPE](#e_pair_recipe), [E_MASKED_COMPOSITION](#e_masked_composition), [E_CAPTURED_COMPOSITION](#e_captured_composition), [E_ENDPOINT_REVIEW](#e_endpoint_review), [E_BOUNDED_TRIAL](#e_bounded_trial), [E_CAPTURED_JOB_API](#e_captured_job_api), [E_ENDPOINT_OBSERVATIONS](#e_endpoint_observations), [E_PAIR_ATTRIBUTION](#e_pair_attribution), [E_CORE_CONTROL](#e_core_control), [E_NATIVE_TERMS](#e_native_terms), [E_NATIVE_STOPPING_LIMIT](#e_native_stopping_limit), [E_NATIVE_PRECISION](#e_native_precision), [E_FAILED_ENDPOINT_DIAGNOSTIC](#e_failed_endpoint_diagnostic), [E_FAILED_ENDPOINT_CHEMISTRY](#e_failed_endpoint_chemistry).
**Last audit:** 2026-11-14, Linden, [W61](https://github.com/vecchioni-lab/NASolve/commit/27878592c8d06975fa9c8a6dc11272ff5d7ef3c2); Two complete read-only native observations of authenticated failed points; diagnostic improvement does not close chemistry, enforcement or convergence.

<a id="s06"></a>
### S06 — Demonstrate improvement against diffraction data

Compare repaired and unmodified models fairly, then determine where data support curvature and strand-specific motion.

**Delivered:** Three matched public-reference coordinate-only refinements now preserve deposited observations/Free-R and measure contact, geometry and diffraction tradeoffs; no repaired-MR success or meaningful extra Rfree benefit of bending is claimed. Supplied-data input checks and five local native MR placement controls completed, including forward and reverse-shape candidates; no repair/refinement comparison yet.

**Closure audit:**

- Use identical observations, Free-R flags, phase policy, refinement budget and unrelated restraints for candidate and no-repair siblings; report contacts, geometry, maps, Rwork/Rfree and tradeoffs.
- Run compatible forward and reverse shape benchmarks plus healthy/wrong-connection controls. Freeze trial policies before Rfree; density interpretation must distinguish displacement from occupancy/ADP/model errors.

**Next action:** First prove that a complete periodic pair policy survives the intended refinement path and is reported with its actual normalization/exclusion semantics. Then compare a frozen damaged/mismatched duplex with unmodified and cleanup controls; keep the healthy reference pilot and resolve supplied-data copy/composition before claiming private-data repair.
**Evidence:** [E_MR_LOCAL](#e_mr_local), [E_PUBLIC_REFERENCE](#e_public_reference), [E_NATIVE_CALLBACK](#e_native_callback).
**Last audit:** 2026-11-14, Linden, [W36](https://github.com/vecchioni-lab/NASolve/commit/a890fffacc12e62046b7ecac96b60a2cf101c23b); Read-only native callback lifecycle diagnosis; no change to partial status, scientific acceptance or ordinary refinement support.

<a id="s07"></a>
### S07 — Expose one ordinary, inspectable repair trial

Let a scientist see what was proposed, built, refined and reviewed through the existing NASolve/Pine workflow.

**Delivered:** Standalone inspect/fit/preview commands exist; ordinary checkpoint/campaign publication and GUI actions are not integrated. Verified standalone source/candidate/mate viewer exists with rotation, point inspection, contact distances and explicit unrefined/unreviewed state; it does not publish an ordinary trial.

**Closure audit:**

- Create immutable children with exact model/CIF/PHIL inputs, preserve current selection, and reuse existing Coot/model-tree paths; viewing never selects or approves.
- Show actual before/after coordinates, moved/fixed sites, mates, geometry and matched refinement deltas. Test stale evidence, interruption, relocation and explicit keep/reject/use decisions.

**Next action:** Finish human browser validation, then reuse this display component when a qualified ordinary trial can connect to existing checkpoint/review owners; do not invent a second history system.
**Evidence:** [E_SOFTWARE](#e_software), [E_VIEW](#e_view).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/0f176a965223af7aafbc433939d2d054f608524a); Read-only display component only; native/refinement/ordinary-trial gates stay open.

<a id="s08"></a>
### S08 — Run bounded opt-in campaigns and transfer schemes

Avoid repetitive prompts while keeping inferred/borrowed connections tentative and reviewable.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Freeze campaign authorization once; re-resolve logical schemes in each member, preserve donor ancestry and negative evidence, honor vetoes and bound retries/resources.
- Use the existing Campaign Doctor and Campaign desk; verify mixed success/failure, deterministic resume and held-out families before claiming unattended support. No automatic global recipe promotion.

**Next action:** Reuse the qualified standalone engine and campaign owners; enable broad inference only after member-level evidence is reliable.
**Evidence:** None yet.
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

## Roadmap B — Pine ASU slicing and required GUI

| Job | Laboratory outcome | Status | Depends on |
| --- | --- | --- | --- |
| [P01](#p01) | Build the periodic molecular graph and declared scope | PARTIAL | F01, F02 |
| [P02](#p02) | Offer cut choices in a required graphical preview | PARTIAL | P01 |
| [P03](#p03) | Materialize a cut without changing the crystal | PARTIAL | P02 |
| [P04](#p04) | Qualify seam chemistry and native interpretation | PARTIAL | P03 |
| [P05](#p05) | Complete the persistent Pine surgery/refine GUI loop | OPEN | P04 |
| [P06](#p06) | Pass blind, multiplicity and ordinary-workflow controls | OPEN | P05 |

<a id="p01"></a>
### P01 — Build the periodic molecular graph and declared scope

Represent the observed periodic object independently of a tile hypothesis or PDB chain cut.

**Delivered:** Logical registration and typed end/image observations exist; a complete recut-ready periodic molecular graph does not. W48 binds one declared discovery copy to a typed periodic graph, retaining missing/unknown/excluded scope and exact fundamental loop operators, including noncommuting screw/translation winding. W49 checks explicit representative-image relabeling with complete source replay, exact noncommuting edge transformation, root-loop conjugacy and inverse graph recovery. W52 composes the fresh registered graph, all-present atom observations and exact image transport into a source-bound in-memory whole-residue preview, preserving fixed context and checking graph-edge geometry. W56 freezes explicit image proposals with unchanged source/discovery/registration and anchored artifacts; full replay verifies derived observations after relocation. This is a durable review input, not editable chemical intent, a new ASU or graphical approval. W67 resolves explicitly declared directed representation-boundary partners through existing graph and schema-2 proposal owners. Strict endpoint/capacity/intent checks, exact images and winding survive replay; no partner inference, atom editing or native enforcement.

**Closure audit:**

- Retain covalent routes, pairing, stacking and symmetry correspondence as distinct edges, with true nicks, seams, junction passages and unknown coverage explicit.
- Handle complete/partial copies, tile versus ASU multiplicity and repeat-phase/winding without forcing the design stoichiometry or zero translation around every cycle.

**Next action:** Use the saved explicit representative packet for P02 before/after graphical inspection and persistent reviewed choices; retain incomplete whole-object identity and chemistry scope.
**Evidence:** [E_REGISTRATION](#e_registration), [E_SOFTWARE](#e_software), [E_DECLARED_GRAPH](#e_declared_graph), [E_GRAPH_RELABEL](#e_graph_relabel), [E_REGISTERED_RELABEL_PREVIEW](#e_registered_relabel_preview), [E_REPRESENTATIVE_BUNDLE](#e_representative_bundle), [E_EXPLICIT_CONTINUATIONS](#e_explicit_continuations).
**Last audit:** 2026-11-15, Linden, [W67](https://github.com/vecchioni-lab/NASolve/commit/baac9850e2a8df086fd6cbe236c5ff31e00930aa); Explicit boundary partners only; partial topology, physical identity, rendered review and complete seam enforcement remain open.

<a id="p02"></a>
### P02 — Offer cut choices in a required graphical preview

Let the scientist decide where to slice the ASU while seeing the same physical periodic object.

**Delivered:** W57 reuses the offline renderer for a verified explicit representative proposal: all present atoms, exact typed edge-image endpoints, logical ownership, declared boundaries, missing scope, unit cell and atom/edge inspection. It does not enumerate cut alternatives, record human choices, write a model or claim rendered-browser validation. W58 fails before output creation on missing assets and qualifies an explicit temporary installed C299 package/owner composition; no rendered visual review or branch merge. W59 computes node images from an explicit selected forest and fixed anchors using existing path/relabel owners; full winding and unselected vertices remain. Two public alternatives compose with existing packets/view/scattering. No automatic alternatives or human selection. W60 persists explicit chosen edges/anchors in the existing source-bound packet and recomputes derivation on load; viewer exposes that proposal intent. Old direct-image packets/scenes retain exact behavior; no human acceptance or editing UI. W63 reuses authenticated Cedar source-native links to expose existing bonds crossing the proposed ASU, exact image geometry, missing declared-graph coverage and source P/OP1/OP2. Optional viewer text is read-only; no chemistry or model change. W64 compares 2–8 explicit same-source/graph packets in the existing viewer with a shared camera and local Cut numbers; switching refreshes seam/provenance details and clears stale inspection. Exact old scenes remain; no model selection/approval or rendered review claimed. W65 adds a source-bound preference download/readback for prefer-cut, keep-original or needs-revision. Fresh comparison replay rejects stale choices; scene remains unchanged and no authenticated approval/model selection is claimed. Browser/download validation still open. W66 projects declared directed backbone continuation, representation/chemical/unknown boundaries and existing phosphate inventory from replayed packets. Unresolved partners retain P/OP1/OP2 intent; OP3 conflicts are scoped to continuation, with terminal phosphate consent separate. Exact route-image transport, optional view and preference context are read-only; no new edge or native enforcement. W67 resolves explicitly declared directed representation-boundary partners through existing graph and schema-2 proposal owners. Strict endpoint/capacity/intent checks, exact images and winding survive replay; no partner inference, atom editing or native enforcement. W70 exposes verified graph node/link IDs and checksum through existing cut-preview --describe-graph, with optional request MATCH/MISMATCH and explicit cut_selection_validated=false. No output directory or stale-hash rewrite; default preview semantics remain.

**Closure audit:**

- Enumerate bounded, intent-compatible cut alternatives; show central ASU plus connected mates, ownership, real nicks, seams, exposed ends and affected logical sites.
- Provide an actual selectable graphical before/after preview with explicit ambiguity and unchanged-source identity. No fake Apply action before materialization is supported.

**Next action:** Qualify actual browser rendering, preference downloads and human review; then wire the source-bound choice into existing Pine/Campaign owners. Keep physical identity, model materialization and seam chemistry gated.
**Evidence:** [E_VIEW](#e_view), [E_REPRESENTATIVE_VIEW](#e_representative_view), [E_VIEW_PACKAGE_BOUNDARY](#e_view_package_boundary), [E_EXPLICIT_FOREST](#e_explicit_forest), [E_SAVED_FOREST_INTENT](#e_saved_forest_intent), [E_NATIVE_REPRESENTATION_SEAMS](#e_native_representation_seams), [E_CUT_COMPARISON](#e_cut_comparison), [E_CUT_PREFERENCE](#e_cut_preference), [E_BACKBONE_INTENT](#e_backbone_intent), [E_EXPLICIT_CONTINUATIONS](#e_explicit_continuations), [E_GRAPH_DESCRIPTION](#e_graph_description).
**Last audit:** 2026-11-15, Linden, [W70](https://github.com/vecchioni-lab/NASolve/commit/01069fe01e005bb5e53a4d29ad8bc3dd8c59b31a); Read-only pre-proposal graph description and current installed composition; graphical/user review and scientific gates remain open.

<a id="p03"></a>
### P03 — Materialize a cut without changing the crystal

Write a new ASU representative while preserving the physical scattering object exactly within validated numerical tolerance.

**Delivered:** W55 adds a source-bound read-only sampled complex Fcalc observer with in-memory Cartesian ANISOU transport and explicit scope. Synthetic P43/R3/P21, wrong-tensor/coordinate controls and independent native allowed-reflection observations exist; no coordinate materializer or full scattering qualification. W62 proves exact labelled group-image permutations and inverse integer lattice shifts for each explicit representative, covers every source atom once and independently binds proposed coordinates. Special-position images remain a labelled multiset, not a unique physical-atom or occupancy proof; no materializer. W74 native synthetic diffraction and geometry targets agree with all855 anisotropic tensors transported in memory; source work/test values and derivatives are invariant across both cuts. Actual model copy/selection reveals an unsupported pair_proxies protocol. No ordinary refinement or tensor serialization is qualified.

**Closure audit:**

- Preserve atom-orbit inventory/multiplicity, chemistry, occupancy and displacement parameters; rotate ANISOU correctly and update logical mappings without losing or duplicating atoms.
- Independently verify before/after unrefined calculated structure factors in the same cell/setting, reciprocal round trips and relocation. Recutting must not be used to hide a physical gap.

**Next action:** Qualify P02 graphical choice/review and full physical inventory/tensor serialization before a model writer. Reuse W62 exact labelled image correspondence alongside W55 independent sampled scattering; keep special-position weights, missing content and seam chemistry explicit.
**Evidence:** [E_REPRESENTATIVE_SCATTERING](#e_representative_scattering), [E_ORBIT_PERMUTATIONS](#e_orbit_permutations), [E_JOINT_FRAME_TARGET](#e_joint_frame_target).
**Last audit:** 2026-11-15, Linden, [W74](https://github.com/vecchioni-lab/NASolve/commit/c4add34c3cdee0582e50efbf9f104e6b63de7698); Native synthetic joint target, in-memory fixed tensors and actual model energy/copy boundary; no physical/materialization/ordinary-refinement closure.

<a id="p04"></a>
### P04 — Qualify seam chemistry and native interpretation

Make a representation seam remain a continuous backbone where chemistry says it is continuous.

**Delivered:** W63 reuses authenticated Cedar source-native links to expose existing bonds crossing the proposed ASU, exact image geometry, missing declared-graph coverage and source P/OP1/OP2. Optional viewer text is read-only; no chemistry or model change. W66 projects declared directed backbone continuation, representation/chemical/unknown boundaries and existing phosphate inventory from replayed packets. Unresolved partners retain P/OP1/OP2 intent; OP3 conflicts are scoped to continuation, with terminal phosphate consent separate. Exact route-image transport, optional view and preference context are read-only; no new edge or native enforcement. W67 resolves explicitly declared directed representation-boundary partners through existing graph and schema-2 proposal owners. Strict endpoint/capacity/intent checks, exact images and winding survive replay; no partner inference, atom editing or native enforcement. W68 observes eight existing source-native crossing angles per explicit cut: exact image energies, rotated gradients and native energies path agree. Live source symmetry/slack are verified; native proxy pickle loses sym_ops. This narrows lifecycle qualification without enabling restraints. A follow-up native angular manager omits cell context before serialization; subset/reindexing retains images, generic deepcopy does not. W71 freezes complete live angle metadata and rebuilds private image-bearing proxies with explicit unit-cell evaluation. JSON/deepcopy/pickle and a fresh native interpreter preserve two complete 1467-angle cut evaluations. Source-manager behavior and complete seam chemistry remain unchanged. W72 observes complete source-frame objective transport, changed-neighbor cache rebuilds and mmtbx normalization/shared-gradient-buffer agreement. Identity selection drops the local facade mapping and remains a negative control; no runtime activation. W73 adds a complete immutable source/image binding and explicit full reindexing.36 local mmtbx entry controls preserve geometry through identity/reverse/cyclic orders; partial selection and changed cell refuse. This is a numerical backend component, not an installed native selection hook. W74 native synthetic diffraction and geometry targets agree with all855 anisotropic tensors transported in memory; source work/test values and derivatives are invariant across both cuts. Actual model copy/selection reveals an unsupported pair_proxies protocol. No ordinary refinement or tensor serialization is qualified. W75 observes the stock source-only dry-run and coordinate-cycle consumer path; geometry, weight regularization and reports bypass a model-energy-only hook. Matched profiling controls agree; complete frame-aware native integration remains open. W76 adds source-bound representative native contact reports preserving exact image operations, directed membership and native multiplicity; native pair-table/report consumers remain unqualified.

**Closure audit:**

- Keep true termini/nicks distinct from ASU seams; preserve continuation phosphates and forbid automatic terminal OP3 chemistry caused only by serialization.
- Qualify native bonds, angles, planes and nonbonded behavior at the seam. Separate any required coordinate repair into a new S-track child; successful recutting itself cannot deform the crystal.
- Retain declared periodic P/OP1/OP2 chemistry independently of partner resolution; emit no symmetry bond alone while complete phosphate-angle enforcement is unqualified.

**Next action:** With Cedar, bind the source only after native model construction, then qualify one geometry owner across copies, pair tables, statistics, weight regularization and report/export consumers. Start with explicitly fixed source-bound weights or correctly transported weighting; distinguish inactive ADP/NCS entries from unsupported active branches. Prove fresh-process source/representative refinement before enabling an adapter; preserve P02/P03.
**Evidence:** [E_PINE_TEST_BANK](#e_pine_test_bank), [E_NATIVE_REPRESENTATION_SEAMS](#e_native_representation_seams), [E_BACKBONE_INTENT](#e_backbone_intent), [E_EXPLICIT_CONTINUATIONS](#e_explicit_continuations), [E_SEAM_ANGLE_LIFECYCLE](#e_seam_angle_lifecycle), [E_ANGLE_SNAPSHOT](#e_angle_snapshot), [E_REFERENCE_FRAME_GEOMETRY](#e_reference_frame_geometry), [E_REFERENCE_FRAME_BINDING](#e_reference_frame_binding), [E_JOINT_FRAME_TARGET](#e_joint_frame_target), [E_NATIVE_CONSUMER_PROTOCOL](#e_native_consumer_protocol), [E_REPRESENTATIVE_PACKING](#e_representative_packing).
**Last audit:** 2026-11-15, Linden, [W76](https://github.com/vecchioni-lab/NASolve/commit/4ef71008f1a654816bde10ff24f334ab8bb720f2); Read-only contact representation, focused/installed checks and authenticated native-capture replay; no native table or ordinary recut-refinement closure.

<a id="p05"></a>
### P05 — Complete the persistent Pine surgery/refine GUI loop

Keep cut, preview, child creation, refinement and review in one usable workbench.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Use the shared model tree and exact selection/Coot APIs; keep inspect, select and approve distinct, preserve current choice and return refinement diagnostics to the same session.
- Graphical actions bind source hashes and show actual nicks/seams/mates. Test stale views, competing choices, interrupted actions, manual imports and relocation without duplicating campaign/checkpoint machinery.
- Expose editable Pine periodic connectivity beyond the ASU, preserving prior user choices and exact logical/image mappings across reslicing or explicitly marking unresolved mappings. Keep intent, proximity and enforcement support separate.

**Next action:** Extend the P02 preview into the real immutable operation/refine loop; GUI completion is a release requirement.
**Evidence:** None yet.
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="p06"></a>
### P06 — Pass blind, multiplicity and ordinary-workflow controls

Prove ASU slicing is useful beyond a single convenient representation.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Run blind 8D93-to-3GBI-style slicing without giving the transformer 3GBI coordinates; independently compare cut/topology afterward. Scattering invariance compares 8D93 with its own recut, not two different crystals.
- Pass extra/partial-copy, repeated-root, wrong-cut and healthy no-op controls through the ordinary Pine GUI/workflow; finish human review and supported-scope integration validation.

**Next action:** Use the existing Pine live-check bank, then add held-out cases only for genuinely untested behavior.
**Evidence:** [E_PINE_TEST_BANK](#e_pine_test_bank).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

## Benchmark register

Private input/result bindings stay in local frozen receipts; these labels are not
operational paths or proof that an arbitrary model/dataset combination is solvable.

| Case | State | Jobs | Remaining evidence |
| --- | --- | --- | --- |
| B01 — Public 8D93 coordinate and native controls | PARTIAL_DIAGNOSTIC | S04, S05 | Qualify surrounding periodic packing and individual geometry under an explicit native masked policy; broad bend cleanup fixes its added angle but worsens collateral contacts. |
| B02 — 8D93 and 5W6W into user-supplied hex_data | MR_PREFLIGHT_COMPLETE_REPAIR_PENDING | S04, S06 | Resolve one-copy/composition and ASU-cut assumptions; qualify a repair before matched no-repair refinement. Original PDF/MTZ/CIF and native results stay local. |
| B03 — Bent 8CS1 / 7R96 into suitable DOHU / DT straight-frame data | BASIC_DATASET_MR_CONTROLS_COMPLETE | S04, S06 | Straight reference and both bent public models placed into one basic dataset. Resolve sequence/ASU-cut comparability, then qualify unbending or changed-direction trials and matched refinement. |
| B04 — Blind 8D93-to-3GBI-style ASU cut | PLANNED | P03, P04, P06 | Withhold reference coordinates during surgery; use same-crystal before/after scattering invariance and independent later topology/cut comparison. |
| B05 — Healthy, wrong/ambiguous, impossible and representation controls | PARTIAL_SYNTHETIC | F02, S02, S03, S04, P01, P06 | Extend current synthetic controls to physically qualified and held-out structures; include special positions, partial copies and winding. |
| B06 — Density-guided and nonuniform/strand-specific relaxation | PLANNED_EXTENSION | S04, S06 | After qualified geometric placement and matched refinement, add a read-only model/map-bound detector of sustained negative difference-density patches along sugar-phosphate backbones. Calibrate with Simon against healthy/noisy and displaced controls across resolution, occupancy/ADP and map-processing conditions before proposing motion. Then consider nonuniform/strand-specific density-guided fitting; a red voxel or universal sigma cutoff is not a displacement instruction. Also qualify bend center/width and localized, distributed or distal curvature variants using support before and after refinement. Construct 4T28/PDB 8SJW at 7.64 A is a user-proposed localized B:11 bend control; entry identity verified, residue/density interpretation pending. Predeclare search budgets and retain all attempts; avoid repeated Rfree-guided tuning. |

## Evidence and limits

<a id="e_software"></a>
### E_SOFTWARE — software_validation

[Evidence contract](topostitch-periodic.md#current-validation-receipt--2026-11-13) at [W38](https://github.com/vecchioni-lab/NASolve/commit/5f7aad230eb04728de4211e69c496fa75948eef2).
W38 explicit mask/direct native composition: 45 focused source tests; full Willow checkout 1,323 tests + 229 subtests. Five sandbox-only /bin/ps failures in campaign process tests clear in the full rerun with required access. Installed wheel from separate test tree: 410 tests + 18 subtests (all TopoStitch plus construct-registration/run-context/AutoRefine/Doctor); relocated original-copied-path-absent selection: 107. Lean imports/mask arithmetic and isolated installed native source/perturbed targets pass. This is the Pine-derived Willow suite, not Cedar or a combined integration.
**Limit:** Current installed check is focused, not a platform matrix. Native compatibility is the tested read-only capture/review path, not a combined Cedar/Willow build or scientific acceptance.

<a id="e_registration"></a>
### E_REGISTRATION — existing_backend

[Evidence contract](construct-registration.md) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69).
Existing explicit logical/copy registration is reused; focused existing registration tests pass.
**Limit:** No new authoritative Scout wiring, symmetry-dependent registration or recut execution is implied.

<a id="e_native_8d93"></a>
### E_NATIVE_8D93 — native_diagnostic

[Evidence contract](topostitch-preview.md#public-8d93-native-interpretation-comparison--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69).
Public source, explicit preview and fitted candidate complete Phenix 2.2.1-6174 interpretation via Cedar ecafc98: REVIEW, 855 atoms and unchanged inputs. Fitted contact target improves but one additional severe captured angle deviation remains.
**Limit:** No diffraction refinement, density-aware fit, full periodic geometry approval or scientific acceptance; raw diagnostic artifacts remain local.

<a id="e_nar_review"></a>
### E_NAR_REVIEW — source_review

[Evidence contract](topostitch.md#implementation-sequence-and-benchmark-gates) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69).
NARestraints v1.1.3 guesser source matches the local checkout: geometric seeds, antiparallel runs and repeated weak edge rescue; raw traversal uses chain/integer adjacency and greedy selection.
**Limit:** Review only; no TopoStitch integration or complete-topology authority.

<a id="e_pine_test_bank"></a>
### E_PINE_TEST_BANK — planned_acceptance_bank

[Evidence contract](construct-registration-live-checks.md) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69).
Existing blind recut, seam, multiplicity, repeat and persistent-GUI controls are retained as the acceptance bank.
**Limit:** Unchecked planned tests are not execution evidence.

<a id="e_image_audit"></a>
### E_IMAGE_AUDIT — Selected present-atom image observations

[Evidence contract](topostitch-periodic.md#selected-atom-image-audit) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/2d7544bb5fa6902e667039c6c9b090e5299bb301).
Exact operator/lattice records, metric-bounded orbit coincidences, source-label ambiguity and selected-image overlap are inspected with finite work/output bounds. Public 8D93: 240 selected atoms and 274,916 tests; no orbit coincidences or selected overlaps. Sources unchanged.
**Limit:** Coordinate coincidence is tolerance-bound evidence, not an identity merge. Periodic fitting now refuses ambiguous selected source coordinates before optimization; missing/unselected atoms, global capacity and Pine cut/scattering invariance remain unqualified.

<a id="e_mr_local"></a>
### E_MR_LOCAL — Local native MR placement preflight

[Evidence contract](topostitch-periodic.md#local-diffraction-benchmark-preflight--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/fe4388facbd3450086f16c645db09de918931a1c).
Five serial single-job Phenix 2.2.1-6174 MR executions completed for the supplied hexagonal and basic-dataset controls. Exact scientific results, source bindings and outputs remain in local frozen receipts; no scientific data committed.
**Limit:** One-copy/source-chemistry assumptions and different ASU cuts remain relevant. This is placement preflight, not TopoStitch deformation, matched refinement, PDF-discovery support or scientific acceptance.

<a id="e_tighter_native"></a>
### E_TIGHTER_NATIVE — Matched native tighter-backbone controls

[Evidence contract](topostitch-preview.md#stricter-backbone-controls--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/84cb847a493654cca8a0ae79f28e000615d5afc3).
Three predeclared public 8D93 backbone-penalty controls improve the pair target with less source-relative strain. Complete Phenix 2.2.1-6174 read-only captures, Cedar cd744e2 mechanics checks, exact named proxy multisets and matched scalar identities show no new nominal >=5 bond/angle/chirality outliers; the original fit adds one angle outlier.
**Limit:** Source outliers remain. This is a local descriptive tradeoff, not closure, torsion/packing/native residual qualification or diffraction improvement. Native inputs and derived models remain local; no new product default is calibrated.

<a id="e_extended_backbone"></a>
### E_EXTENDED_BACKBONE — Extended source-change geometry and native diagnostic

[Evidence contract](topostitch-preview.md#extended-backbone-checks--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/6fc48984b5170a2411f576ab3262826963384226).
Schema 2 audits four junction angles and circular epsilon/zeta/alpha changes in fitting and serialized previews. Public 8D93 extended fit improves the contact target; complete Phenix 2.2.1-6174 capture, bound Cedar cd744e2 receipts, contexts and named proxies match; no new nominal >=5 captured scalar outliers. Schema 1 remains replayable.
**Limit:** Source-relative change only: no torsion ideal/pucker, phosphate valence, full packing, atomic closure or diffraction qualification. Source outliers remain; scientific artifacts stay local.

<a id="e_post_image"></a>
### E_POST_IMAGE — Post-transform exact image audit

[Evidence contract](topostitch-preview.md#periodic-source-and-candidate-image-checks) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/a3e497825be1b7983739b35af83fb280897559c2).
An improving serialized fit is rechecked against the original exact selected image and atom identities. The demonstrated source-clear/candidate-colliding regression now returns TRANSFORMED_IMAGE_REVIEW_REQUIRED with no trial. New evidence binds candidate bytes and source selection; no partner re-search.
**Limit:** Selected present-atom coincidence evidence only; no full van der Waals packing, physical capacity, native closure or approval.

<a id="e_native_transport_relax"></a>
### E_NATIVE_TRANSPORT_RELAX — Native symmetry gradients and fixed-base relaxation controls

[Evidence contract](topostitch-preview.md#native-transport-and-backbone-only-relaxation-diagnostics--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/a3e497825be1b7983739b35af83fb280897559c2).
Complete local Phenix 2.2.1-6174 probes match 5 periodic bond and 8 angle values/ASU gradients. Source and placed models separately relax 107 sugar/phosphate atoms with fixed bases/anchors; fresh captures match contexts/proxies, lower native targets and resolve three severe angles each without new severe scalar outliers. All 321 endpoint coordinates pass finite-difference checks.
**Limit:** Local diagnostic only, no new production native policy. Both stop at 200 iterations; some geometry components increase. No contact, dictionary or chemical-link edits, plane transport qualification, diffraction refinement or adoption. Reuse Cedar lifecycle at integration; artifacts remain local.

<a id="e_native_planes"></a>
### E_NATIVE_PLANES — Reproducible native plane integration gate

[Evidence contract](topostitch-preview.md#reproducible-native-plane-gate) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/7255bfd70e4ffa84068bd008ca1b3360b72848af).
A committed synthetic probe reproduces Phenix 2.2.1-6174 raw symmetry-planarity and Cartesian-parallelity derivative failures. Explicit Cartesian image pullback passes for planarity and, reusing Cedar both-first-planes correction, parallelity. Public 8D93 two-plane controls also pass the corrected composition; raw negatives remain.
**Limit:** No production native adapter, manager attachment, optimization or blanket API qualification. Native symmetry-parallelity constructor is unsupported. Existing Cedar correction/lifecycle remain owners; no native installation or Cedar files modified.

<a id="e_view"></a>
### E_VIEW — Verified read-only coordinate comparison

[Evidence contract](topostitch-preview.md#offline-originalcandidate-view) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/0f176a965223af7aafbc433939d2d054f608524a).
Standalone offline view replays frozen previews, displays actual source/candidate and optional exact mate, and exposes points, traces, contact distances, geometry changes and unrefined/unreviewed state. Public 8D93 installed artifact has 404 atom instances, 204 moved.
**Limit:** No Apply/Refine/Approve or campaign/checkpoint state; no Pine cut choices or recut graph. Browser visual/interaction validation blocked by local-file automation policy; mock-DOM checks are not rendered-browser evidence.

<a id="e_transport"></a>
### E_TRANSPORT — Shared image-coordinate and ASU-gradient transport

[Evidence contract](topostitch-preview.md#shared-image-coordinate-transport) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/3cb9723a4effa6cb58ea97c1972b369c77e154fd).
The viewer and committed native probe share proper Cartesian images and accumulated transpose-gradient pullback. Tests compare independent fractional paths, inverses, repeated shared ASU indices and finite-difference derivatives. Phenix 2.2.1-6174 corrected Cartesian plane checks pass using the shared core; raw negative controls remain.
**Limit:** Numerical arithmetic only; explicit matrices alone do not prove crystallographic membership. No production native optimizer, new chemical topology, symmetry equivalence/packing proof or scientific acceptance.

<a id="e_masked_native"></a>
### E_MASKED_NATIVE — Local masked native and contact-preservation controls

[Evidence contract](topostitch-preview.md#complete-recipes-native-exclusions-and-broader-bend-controls--2026-11-13) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/7f4d334713479b26eee26fb6e2208ad42d9c3f50).
Complete Phenix 2.2.1-6174 local masked trials validate every movable ASU derivative before/after optimization and PDB rounding. Complete NAR recipes and matched core-pair controls pass readback; broader bend plus fixed-base cleanup removes its added angle and three inherited ones with all base coordinates fixed. Native bond edits alter exclusions; collateral periodic overlap and individual geometry regressions remain.
**Limit:** All trials hit 200 iterations. Additive and native-edit objectives are different physics. Better intended contacts, lower total energy and fewer severe scalar outliers do not qualify surrounding packing. No production masked adapter, diffraction comparison or scientific acceptance. Local scientific files/workers excluded from Git.

<a id="e_packing"></a>
### E_PACKING — Authenticated native directed packing comparison

[Evidence contract](topostitch-preview.md#captured-native-packing-comparison) at [earlier work](https://github.com/vecchioni-lab/NASolve/commit/7f4d334713479b26eee26fb6e2208ad42d9c3f50).
Thin comparison reuses Cedar capture/authentication and directed pair replay. Exact relative-image matching preserves multiplicity and separates new overlap from neighbor-list change. Real original/broad-cleanup captures confirm 20 directed rows newly overlap and 103 worsen despite lower total native nonbonded energy; relocated copied evidence produces byte-identical output with original reads blocked.
**Limit:** Read-only unchanged-policy scope. Directed counts are not unique physical contacts, a clashscore or chemical acceptance. No independent neighbor enumeration, torsion/plane comparison, native optimizer or model promotion.

<a id="e_public_reference"></a>
### E_PUBLIC_REFERENCE — Matched public-reference diffraction pilot

[Evidence contract](topostitch-preview.md#w34--matched-public-reference-diffraction-control) at [W34](https://github.com/vecchioni-lab/NASolve/commit/50e82386b0b8d8e91d3c3c4f93bc1a4fdf8b2c6b).
Three complete Phenix 2.2.1-6174 coordinate-only runs preserve the same 3,333 observations and 176 free reflections. Final Rwork/Rfree: original .1776/.2284; cleanup .1779/.2274; bend+cleanup .1772/.2276. Selected contacts remain better with bending, but no meaningful additional held-out benefit is established. Native geometry/packing tradeoffs and exact readbacks are retained.
**Limit:** One already-refined public reference, no artificial MR damage or broader scientific acceptance. No added pair restraints, density inspection, weight tuning, campaign publication or adoption. S05 remains partial; generated artifacts stay local.

<a id="e_native_callback"></a>
### E_NATIVE_CALLBACK — native_api_diagnostic

[Evidence contract](topostitch-preview.md#w36--native-restraint-callback-useful-arithmetic-incomplete-lifecycle) at [W36](https://github.com/vecchioni-lab/NASolve/commit/a890fffacc12e62046b7ecac96b60a2cf101c23b).
Complete Phenix 2.2.1-6174 read-only energy/derivative/lifecycle probe: added two-atom image-term derivative error <5.4e-10, wrapper and energy-only calls pass; all-atom selection and symmetry discard drop the callback, normalized target count is unchanged, ordinary geometry flags do not disable it. Original 855 atoms and native definitions unchanged.
**Limit:** Artificial term, no full DNA recipe, optimizer/refinement or production callback integration. No generic normal-CLI callback loader demonstrated; captures remain local. Existing raw plane-gradient failures and bond-edit exclusion semantics still apply.

<a id="e_pair_recipe"></a>
### E_PAIR_RECIPE — complete_native_pair_recipe_binding

[Evidence contract](topostitch-preview.md#w37--complete-canonical-pair-recipe-backend) at [W37](https://github.com/vecchioni-lab/NASolve/commit/8653b96f6b79bb1c66b12afb59261ceb4b6ef9be).
Complete Phenix 2.2.1-6174 energy/derivative probes bind actual NARestraints full planes/contacts using Cedar correction and shared exact image transport. 8D93 14-pair/798-coordinate, independent 7R96/114-coordinate, synthetic P43 and P21 controls pass. Independent 5W6W and strained P1 retain DERIVATIVE_REVIEW at larger step; per-coordinate step convergence is recorded. Eight negative controls pass throughout; native atom sorting is explicitly disabled after an independent fixture exposed changed order.
**Limit:** Unnormalized additive pair energies only, no native exclusions/bond edits, movement mask, optimization, callback/lifecycle integration, density or scientific acceptance. General input-driven backend; fixture identities never enter algorithm rules. Scientific inputs and receipts stay local.

<a id="e_masked_composition"></a>
### E_MASKED_COMPOSITION — direct_masked_native_composition

[Evidence contract](topostitch-preview.md#w38--explicit-movable-coordinates-and-direct-native-composition) at [W38](https://github.com/vecchioni-lab/NASolve/commit/5f7aad230eb04728de4211e69c496fa75948eef2).
Complete Phenix 2.2.1-6174 checks of all 321 fixed-base and 612 whole-window variables on the prior exact-source-bound control, plus all 246 variables of an independent 7R96 canonical-pair mask, pass at source and declared nonuniform perturbations. Ten negative controls reject identity/reference/definition/callback changes, invalid masks, motion/weight failures and budget exhaustion. Exact fixed coordinates and native/pair/tether component sums reproduce; installed native targets match.
**Limit:** Direct unnormalized evaluator only. Native construction/context and complete nonbonded/exclusion-policy authentication remain caller-owned; Cedar fixed_signature does not cover that entire policy. No optimizer, manager rebuild/continuation, refinement, packing acceptance or model promotion. Artifacts stay local.

<a id="e_captured_composition"></a>
### E_CAPTURED_COMPOSITION — authenticated_initial_native_reconstruction

[Evidence contract](topostitch-preview.md#w39--reconstruct-the-observed-native-starting-context) at [W39](https://github.com/vecchioni-lab/NASolve/commit/9cfd5e1c1bed50a89b815c53014dc156195f10d6).
Cedar-authenticated captures rebuild through fresh trusted workers and exactly match complete initial observed monomer/geometry/energy/ASU inventories. Phenix 2.2.1-6174 107-atom, 204-atom and independent 82-atom controls exactly reproduce W38 source/nonuniform composed energies. Request-hash and resealed-worker negatives reject before execution. Installed and relocated reconstruction pass; full Willow 1338 tests plus 229 subtests.
**Limit:** Developer-only initial reconstruction/evaluation. No complete exclusion/neighbor-generation authentication, optimizer, candidate, refinement or adoption. Native capture and numerical owners remain Cedar; scientific artifacts stay local. No combined Cedar/Willow build is claimed.

<a id="e_endpoint_review"></a>
### E_ENDPOINT_REVIEW — masked_endpoint_capture_review

[Evidence contract](topostitch-preview.md#w40--bind-endpoint-review-to-movement-and-serialized-bytes) at [W40](https://github.com/vecchioni-lab/NASolve/commit/a2382bcad6043cdd3441ccd6c4f2f5231ef9a110).
Exact source/full-precision/mask/PDB binding and Cedar-owned mechanics/environment review pass three complete Phenix 2.2.1-6174 endpoint captures. Default ANISOU rejection is retained before explicit Cartesian preservation. Lower aggregate repulsion coexists with 38 worsened directed contacts in one control. Legacy packing content is unchanged; wrong request hashes reject. Installed audits match; relocated review is byte-identical with original reads blocked. Full Willow 1358 tests plus 229 subtests.
**Limit:** Nonuniform perturbation controls, not optimized repairs. Full-precision native energies/packing and endpoint derivatives are not evaluated by the read-only reviewer. Native scalar deferrals, pucker/absolute stereochemistry, ADP and diffraction qualification remain open. No adoption or combined Cedar build; scientific files remain local.

<a id="e_bounded_trial"></a>
### E_BOUNDED_TRIAL — bounded_native_trial_and_endpoint_derivatives

[Evidence contract](topostitch-preview.md#w41--bounded-native-trials-and-matched-cleanup-controls) at [W41](https://github.com/vecchioni-lab/NASolve/commit/84e1c3092e4c4bc7a36a6cd0a77ab8ff3a028bc5).
Five complete Phenix 2.2.1-6174 trials pass all source/full-precision/serialized derivative checks and fresh rounded native target readback. Paired/cleanup controls expose constant fixed-base pair terms and whole-window geometry/packing tradeoffs. Budget and authenticated preexisting-edit negatives reject. Full Willow 1364 tests plus 229 subtests; 107 installed/relocated focused tests and a complete installed/relocated native trial plus default read-only compatibility pass.
**Limit:** Every 200-iteration control remains NOT_CONVERGED_LIMIT with individual packing regressions. No complete chemistry, full-precision fresh packing, diffraction, repair or adoption qualification. Diagnostic reports only, not resumable campaign runs; scientific files remain local. No Cedar edits/merge.

<a id="e_captured_job_api"></a>
### E_CAPTURED_JOB_API — installed_captured_native_job_boundary

[Evidence contract](topostitch-preview.md#w42--one-installed-captured-job-boundary) at [W42](https://github.com/vecchioni-lab/NASolve/commit/25ca9d6ac76f72e1f670096a76a6dcee87b7f416).
Installed API and thin compatible CLI reuse Cedar capture, observation layering and owned execution. Complete Phenix 2.2.1-6174 source readonly/trial content matches W41 exactly. Installed/relocated Willow and temporary Cedar 948a7860 plus explicit Willow modules complete native evaluation, including injected runner. Three actual-owner failure controls preserve receipts and exception semantics without native launch. Full Willow 1372 tests plus 229 subtests; installed focused 74; temporary combined focused 244 plus 19 subtests.
**Limit:** Temporary adapter compatibility only, not a branch merge or full combined suite. Willow alone retains explicit trusted Cedar source requirement for execution. No new chemistry/packing qualification, diffraction, campaign registration, checkpoint or adoption authority. Scientific captures and combined artifacts stay local.

<a id="e_endpoint_observations"></a>
### E_ENDPOINT_OBSERVATIONS — full_precision_and_rounded_native_endpoint_observations

[Evidence contract](topostitch-preview.md#w43--full-precision-endpoint-observations) at [W43](https://github.com/vecchioni-lab/NASolve/commit/ab48c235e463bfbc3d97ec0f55a8025be106ebcb).
Five complete Phenix 2.2.1-6174 source/full-precision/rounded observations replay through Cedar ASU and selected-environment owners. Rounded observations agree with independent W41 PDB captures in full native energy/gradient and matched pair residuals; changed neighbor rows contribute zero in these controls. Binary displacement roundtrip failure is retained and covered explicitly. Full Willow 1384 tests plus 229 subtests; installed/relocated focused 127 and byte-identical complete endpoint review. Wrong hashes and fixed motion reject before launch; default native behavior reproduces W41.
**Limit:** Fixed-manager coordinate observations, not ordinary full-precision model reinterpretation or universal exclusion/neighbor completeness. Capped trials and per-contact regressions remain; no broader chemistry, diffraction, physical repair or adoption qualification. Scientific files stay local; no Cedar edits/merge.

<a id="e_pair_attribution"></a>
### E_PAIR_ATTRIBUTION — native_selected_and_core_pair_attribution

[Evidence contract](topostitch-preview.md#w44--individual-pair-attribution) at [W44](https://github.com/vecchioni-lab/NASolve/commit/f448549b96a90d4035e3479c297212bbb5a339e5).
Five complete Phenix 2.2.1-6174 endpoint controls reproduce native container sums and expose individual pair changes. Whole-window paired improves all pair totals; cleanup worsens one selected and two core pairs. Full Willow 1397 plus 229 subtests; focused 50; installed/relocated 140 and byte-identical native report. Existing review dictionaries remain identical after removing only the new field; compact JSON reduces size about 55%.
**Limit:** Read-only diagnostic attribution, not calibrated chemistry acceptance. Original trials remain capped with packing regressions and imperfect contacts. No objective changes, ordinary refinement-consumer qualification, Cedar edits/merge or campaign adoption. Scientific files stay local.

<a id="e_core_control"></a>
### E_CORE_CONTROL — matched_retained_core_native_control

[Evidence contract](topostitch-preview.md#w45--matched-retained-core-control) at [W45](https://github.com/vecchioni-lab/NASolve/commit/a8531f5958a9d3c8857ed4e2f224b1a8a4f3c108).
One complete Phenix 2.2.1-6174 core-only trial uses the same source, mask, tether and caps as W41 paired trial. All 612-variable initial/full/rounded derivative checks pass, as do complete endpoint observations and independent rounded target/gradient/packing parity. All core pair totals improve; one selected pair worsens without its terms, while both improve with them. Existing APIs suffice; W44 full/installed validation remains applicable.
**Limit:** Both trials remain NOT_CONVERGED_LIMIT; per-contact regressions, imperfect contacts, broader chemistry and ordinary refinement enforcement remain open. No runtime/schema change, new chemical policy, Cedar edits, diffraction or adoption. Generated scientific evidence stays local.

<a id="e_native_terms"></a>
### E_NATIVE_TERMS — native_torsion_and_plane_endpoint_observations

[Evidence contract](topostitch-preview.md#w46--native-torsion-and-monomer-plane-observations) at [W46](https://github.com/vecchioni-lab/NASolve/commit/17d0efe6df451f22535db9253c1588dd4e248896).
Maintained Cedar kernels match original live proxies and complete native family targets/gradients in six Phenix 2.2.1-6174 endpoint controls. Live missing/nondefault torsion policy and nonidentity images reject. Per-term scope/measurements retain local regressions hidden by aggregates. Full Willow 1416 plus 229 subtests; focused 40; installed/relocated 159 plus exact native report. Temporary installed Cedar 7e843af7 composition passes 159 focused tests and byte-identical native review via its owned runner.
**Limit:** Fixed-point identity-only torsion/plane observations, not new derivative or chemical qualification. Other families remain deferred; no pucker assignment, ordinary corrected refinement, Cedar edits, branch merge, complete combined suite or adoption. Initial sandbox permission and temporary missing-wrapper failures are retained. Scientific evidence remains local.

<a id="e_single_edge_capacity"></a>
### E_SINGLE_EDGE_CAPACITY — selected_single_periodic_edge_capacity

[Evidence contract](topostitch-preview.md#w47--one-periodic-edge-and-its-reciprocal-partners) at [W47](https://github.com/vecchioni-lab/NASolve/commit/c887c65ea966b3a7107a1220289fde646587e875).
Shared exact reciprocal incidence retains lattice translations for selected source/transformed audits. P1/P2/C2/P43 controls distinguish one versus two self-image partners; ambiguity stays under review. Periodic fitter consumes scoped capacity. Full Willow 1424 plus 229 subtests; focused/installed-relocated 68. Public 8D93 numerical report exactly reproduces apart from added capacity metadata and algorithm v5, including after relocation with old paths blocked.
**Limit:** One declared edge under present selected-coordinate/tolerance assumptions; full molecular identity, special-position equivalence, global scheme, sequence/orientation, geometry and connection acceptance remain unqualified. No native Phenix/Coot execution, chemical link, recut, Cedar edits or adoption. Generated evidence stays local.

<a id="e_declared_graph"></a>
### E_DECLARED_GRAPH — declared_periodic_graph_and_registered_scope

[Evidence contract](topostitch-periodic.md#w48--declared-periodic-graph-for-pine) at [W48](https://github.com/vecchioni-lab/NASolve/commit/a542ea8dc375faeab85cc6196cf5e400603bccc8).
20 new graph regressions pass and fail on the pre-patch checkout. Full Willow: 1444 plus 229 subtests. Installed/relocated graph and owner tests: 113. Public 8D93 registered graph reproduces exactly with original paths blocked and original temporary checkout absent; all input bytes preserved. Five installed entrypoint helps, lean import and Python 3.10 syntax checks pass.
**Limit:** Declared one-copy scope only; other copies, unrepresented coordinates, unknown boundaries and missing sites remain explicit. No physical orbit quotient, complete molecular graph, covalent seam creation, coordinate materialization, scattering invariance, Phenix/Coot run or Cedar changes. Scientific artifacts stay local.

<a id="e_graph_relabel"></a>
### E_GRAPH_RELABEL — exact_periodic_graph_representative_relabeling

[Evidence contract](topostitch-periodic.md#w49--preview-a-change-of-graph-representatives) at [W49](https://github.com/vecchioni-lab/NASolve/commit/a46c15008f790e86c0194f2ef6d734f6df55f420).
34 graph tests pass, including 14 new regressions that fail against installed W48. Full Willow: 1458 plus 229 subtests. Installed/relocated shared-owner tests: 127. Complete public registered graph and relabel preview reproduce exactly with original paths blocked; selected pairing edges become identity-image edges, loop conjugacy and inverse graph recovery pass. Five entrypoint helps, lean import and Python 3.10 syntax pass.
**Limit:** Exact graph algebra only; no physical orbit or scattering proof, coordinate materialization, chemistry authorization, persistent cut choice or graphical review. Low-level graph binding does not replace the registered source/atom ownership audit. No Phenix/Coot runs or Cedar changes; scientific artifacts stay local.

<a id="e_present_model_orbits"></a>
### E_PRESENT_MODEL_ORBITS — all_present_atom_orbit_observation

[Evidence contract](topostitch-periodic.md#w50--observe-all-present-model-atom-orbits) at [W50](https://github.com/vecchioni-lab/NASolve/commit/19a58a2ee08cb0ed33b18b821b0bab02d61f1ed9).
10 new regressions fail against W49 and pass now; focused graph/image tests 76. Full Willow 1468 plus 229 subtests. Installed/relocated shared-owner tests 155; two public-derived 855-atom source reports reproduce exactly with old paths blocked and the original temporary checkout absent. Both show no present-coordinate orbit coincidences at the recorded tolerance. Five command helps, lean import and Python 3.10 syntax pass.
**Limit:** Present-coordinate observations only, not chemical identity, molecular multiplicity, complete deposited-entry inventory, ASU-cut or scattering qualification. Occupancy/alternate/TER ambiguity stays visible. No filtering or identity merging, native execution or Cedar changes. All scientific inputs/results stay local.

<a id="e_native_stopping_limit"></a>
### E_NATIVE_STOPPING_LIMIT — predeclared_500_iteration_native_controls

[Evidence contract](topostitch-preview.md#w51--native-convergence-ceiling-control) at [W51](https://github.com/vecchioni-lab/NASolve/commit/6ff9eb874bc3f07cd64231f52cf21e3485f657ec).
Two complete Phenix 2.2.1-6174 executions retain FAILED line-search rounding outcomes at358/351 accepted steps. Initial derivative gates pass and both old200-iteration traces reproduce exactly. Source/input bytes preserved. Last accepted coordinate changes beyond200 are below0.000105 Å, but no post-exception endpoint derivative gate or candidate emission occurs.
**Limit:** Negative evidence only; no convergence, scientific acceptance, stopping tolerance relaxation, ordinary refinement or Cedar change. Runtime code remains W50, whose full/installed validation applies; roadmap/doc checks pass. Generated runs/traces stay local.

<a id="e_registered_relabel_preview"></a>
### E_REGISTERED_RELABEL_PREVIEW — registered_source_atom_image_preview

[Evidence contract](topostitch-periodic.md#w52--bind-an-image-preview-to-registered-source-atoms) at [W52](https://github.com/vecchioni-lab/NASolve/commit/9deb105da5c0cf769cdba7046175b6e330f3cf24).
Nine regressions pass; the prior package fails to import the absent module. Full Willow 1477 plus 229 subtests; installed/relocated shared-owner tests178. Public source:36 atoms in2 requested residues,819 exact fixed atoms,38 edge arithmetic checks; legacy graph/relabel/orbit reports reproduce exactly. Installed preview is identical after relocation with original paths blocked. Five command helps, lean import and Python3.10 syntax pass. Subsequent temporary installed Cedar C295 c7414919 plus23 Willow modules passes264 focused owner/API tests and exact public preview replay; no merge, full combined-suite or combined CLI metadata claim.
**Limit:** In-memory whole-residue representative preview only. Missing/ambiguous requested coordinates refuse; other scope/occupancy uncertainty remains. No coordinate serialization, ANISOU transport, native seam restraints, graphical approval, physical/scattering acceptance or Cedar changes. Scientific outputs stay local.

<a id="e_native_precision"></a>
### E_NATIVE_PRECISION — predeclared_failed_trial_precision_observation

[Evidence contract](topostitch-preview.md#w53--measure-precision-at-the-last-accepted-failed-trial-points) at [W53](https://github.com/vecchioni-lab/NASolve/commit/5cecbb513264c2f534db759a5822fa8d36eea444).
Two complete Phenix2.2.1-6174 read-only probes reproduce last accepted target components and gradient norms exactly. Both complete612-variable derivative checks pass unchanged1e-3 bounds at1e-4/1e-5 Angstrom. Eight fixed directions at nine scales retain score quantization; local quadratic decrease estimates6.60e-13/7.31e-13 are below9.095e-13 score ULP. Baselines repeat exactly.
**Limit:** Numerical diagnostic only, not native convergence, geometry acceptance or a new stopping policy. No optimizer/candidate emission/SDK or Cedar edits. Product code unchanged from W52; prior full/installed tests apply. Generated inputs and observations remain local.

<a id="e_failed_endpoint_diagnostic"></a>
### E_FAILED_ENDPOINT_DIAGNOSTIC — last_accepted_failed_trial_observation

[Evidence contract](topostitch-preview.md#w54--audit-last-accepted-points-without-recovering-failed-trials) at [W54](https://github.com/vecchioni-lab/NASolve/commit/6bdc16884bbd9a5c47450d67f3f08743c56e7992).
11 new capability regressions fail against preceding runtime; all33 focused trial/job tests pass. Full Willow1489 plus229 subtests; installed/relocated276,5helps,lean import and3.10syntax. Both complete Phenix2.2.1-6174 controls reproduce W51 traces,accepted history and errors exactly. Nested full/rounded612-variable checks pass; full samples match independentW53. Failed jobs return2, sources remain unchanged.
**Limit:** Additive diagnostic metadata only. Original FAILED/error preserved; no rejected-trial fallback, candidate emission, tolerance change or scientific acceptance. Native observations remain local; no Cedar/runtime SDK change, schema migration or full combined-branch qualification.

<a id="e_representative_scattering"></a>
### E_REPRESENTATIVE_SCATTERING — sampled_complex_scattering_observation

[Evidence contract](topostitch-periodic.md#w55--observe-sampled-scattering-before-and-after-representative-relabeling) at [W55](https://github.com/vecchioni-lab/NASolve/commit/52fb6d471df249546518f70bdb2021794336fa70).
22 synthetic tests; focused107, full1511 plus229 subtests, installed/relocated298,5helps,lean import,3.10syntax and exact public/legacy replay. Public855 atoms,36 transported tensors,343 reflections: Gemmi maximum difference8.24e-7; coordinate-only negative106.36. Independent complete Phenix2.2.1-6174/cctbx direct calculation on115 allowed indices gives3.05e-12 with the same negative control. Source bytes preserved. Temporary installed Cedar C297 fe7e9fd73988fc2ffb5501c3740fd9e06da0b45d plus24 Willow modules passes298 focused owner/API checks and exact public preview/scattering replay; no merge or full combined-suite/CLI metadata claim.
**Limit:** Finite sampled observation only; no acceptance threshold, coordinate serialization, whole-object/multiplicity/scattering proof or chemistry/refinement approval. NCS and unsupported scattering inputs refuse. Initial unsupported centering-absence native output and failed launch evidence retained locally. No SDK/Cedar changes or scientific data committed.

<a id="e_representative_bundle"></a>
### E_REPRESENTATIVE_BUNDLE — immutable_representative_proposal

[Evidence contract](topostitch-periodic.md#w56--freeze-and-replay-an-explicit-representative-proposal) at [W56](https://github.com/vecchioni-lab/NASolve/commit/73642f5fd1309c75b2986659c106f4a53db83d61).
22 new regressions,67focused,full1533 plus229subtests,320installed/relocated,6helps,lean import,3.10syntax. Original inputs absent; exact public855-atom/36-image replay and installed CLI packet. Existing preview/scattering replay unchanged.
**Limit:** New additive schema1 proposal/receipt only; no model, chemical intent edit, GUI review, refinement or checkpoint. Exact algorithm/Gemmi replay required; no silent migration. Scientific artifacts excluded from Git; no Cedar/runtime-native changes.

<a id="e_representative_view"></a>
### E_REPRESENTATIVE_VIEW — read_only_periodic_view

[Evidence contract](topostitch-periodic.md#w57--inspect-periodic-representative-proposals-in-the-shared-viewer) at [W57](https://github.com/vecchioni-lab/NASolve/commit/295482ad78e0959f415a2397a3a384012a29ebee).
11 new regressions; focused40,full1544 plus229subtests,installed/relocated338,6helps,lean import,3.10syntax. Public855 atoms/42nodes/38edges and legacy replay exact. Actual packaged JS runs with DOM/canvas doubles through edge selection/focus, atom inspection, modes, cell and missing anchors.
**Limit:** No rendered-browser or human visual approval, bounded cut alternatives, persistent review, materialized ASU or chemical link. Existing schemas/commands remain compatible. Scientific artifacts local only; no Cedar or native-tool changes.

<a id="e_view_package_boundary"></a>
### E_VIEW_PACKAGE_BOUNDARY — installed_package_compatibility

[Evidence contract](topostitch-periodic.md#w58--qualify-the-installed-viewer-boundary-with-cedar) at [W58](https://github.com/vecchioni-lab/NASolve/commit/fa170e21e33bd6740790072e83524545601fd606).
Missing-asset regression fails before fix; focused41,full1545 plus229subtests,installed/relocated339,6helps. Temporary package union with C299 passes339Willow and162Cedar plus19subtests and exact public replay after original source removal.
**Limit:** Initial unchanged-Cedar metadata omitted the HTML asset:335passed/3failed retained. No merge, combined human-doc/full-suite/native qualification or rendered visual review. Scientific evidence local. Zero-parallelity W34 recipes were not rerun.

<a id="e_explicit_forest"></a>
### E_EXPLICIT_FOREST — explicit_forest_image_proposal

[Evidence contract](topostitch-periodic.md#w59--calculate-representatives-along-explicitly-chosen-links) at [W59](https://github.com/vecchioni-lab/NASolve/commit/1b4d79134331f8777c2a7f3ba53efed5f8cca410).
21forest cases plus typed replay regression; focused78,full1567 plus229subtests,installed/relocated361,6helps. P43/R3/P21/unwrapped/reversed/disconnected/winding and source packet/view controls. Two predeclared public anchors move282/286 atoms and preserve sampled scattering within stated raw differences.
**Limit:** No inferred partner/tree/cut, saved forest edit intent, model, chemistry or graphical approval. Partial public graph is not a full molecular object. No native execution; all scientific data local only.

<a id="e_saved_forest_intent"></a>
### E_SAVED_FOREST_INTENT — saved_forest_proposal_intent

[Evidence contract](topostitch-periodic.md#w60--preserve-selected-link-and-anchor-intent-in-saved-proposals) at [W60](https://github.com/vecchioni-lab/NASolve/commit/f4d27cc06cad0c7d3f1f228a3815b61a72a341fd).
9 new regressions; focused71,full1576 plus229subtests,installed/relocated370,6helps. Both public alternatives reproduce exact prior observations while retaining graph-link/anchor choice; installed forest and legacy commands pass. JS intent display/interactions checked with doubles.
**Limit:** Proposal intent is not human approval; no GUI editing, automatic cut, coordinate writer, chemical seam or native execution. Browser visual review open. Old direct-image packets unchanged; new kind requires compatible reader. Scientific artifacts local only.

<a id="e_failed_endpoint_chemistry"></a>
### E_FAILED_ENDPOINT_CHEMISTRY — failed_endpoint_chemistry_observations

[Evidence contract](topostitch-preview.md#w61--read-only-chemistry-at-failed-last-accepted-points) at [W61](https://github.com/vecchioni-lab/NASolve/commit/27878592c8d06975fa9c8a6dc11272ff5d7ef3c2).
Two complete Phenix2.2.1-6174 fixed-manager controls using frozen Cedar f2345a8. Exact source equality/input preservation and all receipt inventories verified. Both selected/core target effects, scalar geometry, ordinary torsions/planes and8316 native contacts reviewed at full/rounded precision.
**Limit:** Original FAILED outcomes retained. No candidate model, fresh candidate reinterpretation, geometry threshold, optimization, ordinary refinement or scientific acceptance. Zero-weight constant inventory is not a missing positive force. Runtime unchanged; W60 tests/install remain applicable. Scientific data local only.

<a id="e_orbit_permutations"></a>
### E_ORBIT_PERMUTATIONS — exact_labelled_orbit_permutations

[Evidence contract](topostitch-periodic.md#w62--exact-labelled-orbit-permutations-for-a-proposed-cut) at [W62](https://github.com/vecchioni-lab/NASolve/commit/ea27b49bdbb08f4806eb9b200d223050c46e3164).
16 regressions; independent rational checks across65 Sohncke groups; focused47,full1592 plus229subtests,installed/relocated386,6helps,lean/3.10. Both public proposals preserve855 labelled atoms and7695 cell-image incidences; exact replay and old outputs preserved.
**Limit:** No special-position weighting, unique physical atom/molecule identity, tensor serialization, model writer, chemical connection, native execution or graphical approval. Source data and scientific outputs stay local; schema additive.

<a id="e_native_representation_seams"></a>
### E_NATIVE_REPRESENTATION_SEAMS — native_source_link_representation_observation

[Evidence contract](topostitch-periodic.md#w63--show-existing-source-bonds-at-proposed-asu-seams) at [W63](https://github.com/vecchioni-lab/NASolve/commit/23939692f20f16ffaecc0352d4e3060e47f6ed20).
11 regressions; focused52,full1603 plus229subtests,installed/relocated397,six helps. Complete Phenix2.2.1-6174 source capture:855 atoms/956simple/0ASU/38interresidue links. Both explicit public cuts expose two source-native seams outside the declared backbone graph, retaining P/OP1/OP2 and exact-image geometry. Temporary installed C302 composition passes397Willow/238Cedar plus19subtests and exact default-owner native/old replay.
**Limit:** Observation only: source interpretation is not complete intent; existing symmetry bonds/angles/exclusions unqualified. No new bond, atom edit, model, native refinement, graphical approval or scientific acceptance. Scientific artifacts local; original setup refusal preserved.

<a id="e_cut_comparison"></a>
### E_CUT_COMPARISON — explicit_cut_comparison_view

[Evidence contract](topostitch-periodic.md#w64--compare-explicit-cuts-in-one-shared-view) at [W64](https://github.com/vecchioni-lab/NASolve/commit/9375440e401ae04ecfa1b5dcb3611eba7e39013e).
12 regressions; focused42,full1615 plus229subtests. Public explicit alternatives preserve exact W63 scenes and relocate with source paths blocked. Actual JavaScript checks shared camera, repeated cut switching, refreshed seam details, stale selection clearing and legacy controls. Installed/relocated409,six helps,lean/3.10 and exact installed comparison/legacy replay pass.
**Limit:** No automatic alternatives, saved human choice/approval, model or chemistry action. Browser rendering/user review still open. Stale installed-wheel refusal retained; scientific artifacts local only.

<a id="e_cut_preference"></a>
### E_CUT_PREFERENCE — source_bound_cut_preference

[Evidence contract](topostitch-periodic.md#w65--save-and-reopen-a-source-bound-cut-preference) at [W65](https://github.com/vecchioni-lab/NASolve/commit/3993bb3abce5ef64157e08a07658d7698fc4b652).
15 regressions; focused57,full1630 plus229subtests. Actual JavaScript exports all three choices; backend validates those requests after public packet/capture relocation with old paths blocked. Reopened note and legacy interactions pass doubles; old comparison remains exact. Installed/relocated424,six helps,lean/3.10 and exact installed preference/comparison/legacy readback pass. Temporary installed C303 composition passes424Willow/221Cedar plus6subtests and exact default-owner capture/preference/legacy replay.
**Limit:** Preference is caller-supplied evidence, not authenticated human or scientific approval; no model/checkpoint action or separate campaign history. Real browser/download/human review remains open. Scientific artifacts local only.

<a id="e_backbone_intent"></a>
### E_BACKBONE_INTENT — declared_backbone_intent_observation

[Evidence contract](topostitch-periodic.md#w66--observe-declared-backbone-intent-across-a-cut) at [W66](https://github.com/vecchioni-lab/NASolve/commit/d042f586e7ea2427cbfc7d34b3e079a2bafecfca).
18 new regressions; full1648 plus229subtests; installed/relocated442,six helps,lean import,3.10syntax. Exact public and old comparison replay; three JavaScript-exported preferences validate after relocation. Public partial graph has24 declared continuations and0 route seams while the independent native observer retains2 source-native out-of-route seams. Actual viewer logic passes DOM/canvas controls. Temporary installed C303 composition passes442 Willow and221 Cedar tests plus6 subtests, six helps and exact default-owner public/legacy/native/intent replay.
**Limit:** No inferred partner, chemistry change, atom edit, native enforcement or scientific acceptance. Browser URL policy again refused local-file opening; no bypass and no rendered/download/human review claim. Scientific artifacts local only. Scoped installed owner/package compatibility only; no merge or complete combined-suite qualification.

<a id="e_explicit_continuations"></a>
### E_EXPLICIT_CONTINUATIONS — explicit_representation_boundary_partners

[Evidence contract](topostitch-periodic.md#w67--resolve-explicitly-declared-boundary-partners) at [W67](https://github.com/vecchioni-lab/NASolve/commit/baac9850e2a8df086fd6cbe236c5ff31e00930aa).
26 new regressions; full1674 plus229subtests; installed/relocated468,six helps,lean/3.10. Exact old/new public and three JavaScript preference replay after relocation. Two public controls preserve855 proposed coordinates exactly; one of two source-native seams gains declared coverage, other stays outside routes. Temporary installed Cedar a2e73603 composition passes468 Willow/221 Cedar plus6subtests and exact default-owner replay.
**Limit:** No inferred topology, chemistry approval, native enforcement or model materialization. Schema2 requests required for new declarations; old readers refuse. Scientific outputs local only; real browser/download/human review remains open.

<a id="e_seam_angle_lifecycle"></a>
### E_SEAM_ANGLE_LIFECYCLE — source_native_seam_angle_lifecycle_diagnostic

[Evidence contract](topostitch-periodic.md#w68--inspect-source-seam-angles-and-proxy-persistence) at [W68](https://github.com/vecchioni-lab/NASolve/commit/98302b2b901318db9d81f1bc683d7474ac5c716b).
Complete Phenix2.2.1-6174 reconstruction matches the authenticated855-atom context. All1467 live source angle sym_ops/slack inspected. Each cut has8crossing terms/12atoms; energy, rotated gradient and native energies path agree. Finite-difference maxima3.08e-7/3.35e-7. Selection retains operators; native angle/shared-array pickle loses them, changing residual20.3688 to5631.8498 and11.6365 to5458.7742. Frozen inputs and dispatcher match. Follow-up subset/reindexing preserves operators, but an isolated native angular manager omits unit-cell context and returns the same wrong residuals before pickle; generic deepcopy also loses image metadata.
**Limit:** Experimental local scaffold and three setup failures preserved; no public API, optimization, refinement, native activation or Cedar/cctbx patch. Does not establish ordinary refinement uses pickle. Complete terms/exclusions and supported lifecycle remain unqualified; code validation remains W67.

<a id="e_virtual_cedar_integration"></a>
### E_VIRTUAL_CEDAR_INTEGRATION — installed_virtual_merge_compatibility

[Evidence contract](topostitch-periodic.md#w69--audit-the-virtual-willowcedar-integration) at [W69](https://github.com/vecchioni-lab/NASolve/commit/6cfe42e967fb7680e5596a112d126d69c8622689).
Virtual Willow6cfe42e9/Cedar a2e73603 tree has0source conflicts and7documentation conflicts. Runtime equals W67 composition except the existing11-line autorefine final-PDB RMSD fallback. Installed relocated combined autorefine/refinement runtime/parallelity controls pass76 tests plus16 subtests; six helps pass.
**Limit:** No actual merge/ref change or conflict resolution; no full combined-suite, native execution or scientific qualification. Shared parser gap audited only. All generated evidence local.

<a id="e_graph_description"></a>
### E_GRAPH_DESCRIPTION — read_only_registered_graph_cli

[Evidence contract](topostitch-periodic.md#w70--describe-the-registered-graph-before-choosing-a-cut) at [W70](https://github.com/vecchioni-lab/NASolve/commit/01069fe01e005bb5e53a4d29ad8bc3dd8c59b31a).
14 added cases; focused115; full1688 plus229subtests; installed/relocated482,six helps,lean import,3.10syntax and exact old/new public replay. Source-bound graph IDs/hash and optional request MATCH/MISMATCH are read-only; stale builder rejection remains. Current Cedar dca8ee82 installed virtual composition passes558 plus16subtests, six helps and exact default-owner native/packet/graph replay.
**Limit:** Graph description is not cut selection/geometry validation or approval; no request rebinding, new registry or model/chemistry edit. Initial sandboxed full run had5 process-permission failures; unfiltered permission-enabled rerun passed. Seven documentation conflicts remain; no real merge/full combined-suite/native execution. Scientific evidence local.

<a id="e_angle_snapshot"></a>
### E_ANGLE_SNAPSHOT — native_angle_snapshot_reconstruction

[Evidence contract](topostitch-periodic.md#w71--reconstruct-image-bearing-angle-diagnostics-explicitly) at [W71](https://github.com/vecchioni-lab/NASolve/commit/0e8e62986158f8b4373506c5ea34baece223621f).
Checked complete live angle records preserve operators/slack/scalars and explicitly reconstruct private proxies with unit-cell evaluation. Phenix 2.2.1-6174 synthetic and two 1467-angle public cuts pass JSON/deepcopy/pickle and fresh installed-interpreter reload; source energy/rotated gradients and directional derivatives agree. Full Willow 1715 +229 subtests; installed509; virtual Cedar dca8ee82 composition585 +16 subtests, six helps and exact old/new default-owner replay.
**Limit:** Read-only numerical family observer, not an additive correction, manager patch or refinement integration. Raw native pickle/cell-omission negative controls remain failures. Complete seam terms/exclusions, supported lifecycle and physical identity remain open. Scientific artifacts local; seven doc conflicts and no actual merge/full combined suite.

<a id="e_reference_frame_geometry"></a>
### E_REFERENCE_FRAME_GEOMETRY — complete_native_reference_frame_diagnostic

[Evidence contract](topostitch-periodic.md#w72--evaluate-complete-geometry-in-a-retained-reference-frame) at [W72](https://github.com/vecchioni-lab/NASolve/commit/0e8e62986158f8b4373506c5ea34baece223621f).
Two cuts cross2 bonds/8 angles/6 torsions. Complete Phenix2.2.1-6174 source-frame objective/gradient transport agrees through perturbations and forced neighbor rebuilds with changed membership. Actual mmtbx energy entry passes12 gradient/normalization/shared-buffer cases; source definitions unchanged.
**Limit:** Local diagnostic facade only; identity selection demonstrably drops mapping. No installed/runtime change, ordinary refinement, ADP/NCS/rebuild qualification, missing-link repair, materialization or diffraction improvement. W71 remains code/test baseline; scientific evidence local.

<a id="e_reference_frame_binding"></a>
### E_REFERENCE_FRAME_BINDING — complete_frame_binding_and_native_reindex_diagnostic

[Evidence contract](topostitch-periodic.md#w73--retain-complete-frame-bindings-through-explicit-reindexing) at [W73](https://github.com/vecchioni-lab/NASolve/commit/c4add34c3cdee0582e50efbf9f104e6b63de7698).
Immutable ReferenceFrame retains complete source labels/images/context and full permutations.12 new regressions; focused113; full1727 +229; installed521. Actual local mmtbx facade passes36 identity/reverse/cyclic entry cases and refuses partial/duplicate selection and cell drift before evaluation. Installed fresh-native reload survives relocation. Virtual Cedar393aea60 composition640 +16 passes including43 new Cedar reference tests.
**Limit:** Caller authenticates/recomputes context and verifies crystal operations; numerical matrices are not standalone crystallographic proof. No native selection hook, subset/rebuild/ADP/NCS support, ordinary refinement, model materialization or complete scientific acceptance. Seven doc conflicts; no actual merge/full combined suite. Generated science local.

<a id="e_joint_frame_target"></a>
### E_JOINT_FRAME_TARGET — native_synthetic_joint_target_and_model_boundary_diagnostic

[Evidence contract](topostitch-periodic.md#w74--check-diffraction-agreement-and-deeper-model-boundaries) at [W74](https://github.com/vecchioni-lab/NASolve/commit/c4add34c3cdee0582e50efbf9f104e6b63de7698).
Phenix2.2.1-6174 direct synthetic1008-reflection target with855 transported anisotropic tensors preserves Fcalc, target, work/test R and rotated gradients across both cuts. Joint geometry/data directional derivatives pass. Actual model energy entry matches; identity selection/deep_copy explicitly refuse the missing pair_proxies protocol.
**Limit:** First isotropic-only guard failure and omitted-tensor negative control retained. No experimental reflection/Free-R changes, ADP refinement, serialization, optimization or ordinary refinement. Partial selections, model-copy/pair-table reporting, ADP/NCS/callback/rebuild protocols remain open. W73 runtime/test baseline unchanged; science local.

<a id="e_native_consumer_protocol"></a>
### E_NATIVE_CONSUMER_PROTOCOL — stock_source_only_native_consumer_observation

[Evidence contract](topostitch-periodic.md#w75--observe-stock-native-consumers-before-choosing-an-integration-hook) at [W75](https://github.com/vecchioni-lab/NASolve/commit/c4add34c3cdee0582e50efbf9f104e6b63de7698).
Stock Phenix 2.2.1-6174 source-only synthetic dry-run and one individual_sites cycle complete. Call/state tracing identifies copies, pair tables, geometry L-BFGS, weight-shaking dynamics, statistics and mmCIF link exports beyond the model energy entry. Matched unprofiled and caller-aware runs preserve saved coordinate/tensor/cell records and .geo bytes.
**Limit:** Five-module Python-call inventory is a lower bound, not a complete native protocol or ordinary recut-refinement qualification. Disabled ADP/NCS entries are distinguished from active calculations. No adapter, source chemistry change, experimental input or scientific adoption. W73 runtime and full/install/composition checks unchanged; generated outputs and initial setup failures local.

<a id="e_representative_packing"></a>
### E_REPRESENTATIVE_PACKING — captured_native_contact_representation

[Evidence contract](topostitch-periodic.md#w76--represent-captured-native-contacts-in-chosen-crystal-images) at [W76](https://github.com/vecchioni-lab/NASolve/commit/4ef71008f1a654816bde10ff24f334ab8bb720f2).
Exact g_i h g_j^-1 contact operations preserve source directed rows, weights/multiplicity and distances. Focused118 and installed/relocated564 pass; 22 new packing controls. Authenticated saved Phenix2.2.1-6174 replay preserves8305 directed rows in each cut, max distance error1.69e-14 Angstrom.
**Limit:** Read-only captured-coordinate report, not native pair-table reconstruction, new neighbors/exclusions, physical identity or refinement support. Full1748 +229 passed before the final finite-output guard; final full-suite recheck is queued after Cedar native work. Generated reports remain local; caller authenticates source through Cedar.

## Deferred extensions, not hidden blockers

- **Canonical rebuilding / missing-residue generation:** Only after intact-duplex placement is qualified and an explicit rebuilding case requires it; preserve sequence and separately qualify chemistry.
- **Junction hinges and broader modified/RNA/backbone chemistry:** Explicit capability and native tests; fixed junctions and canonical DNA remain the first supported scope.
- **AlphaFold provider integration:** Separate input-provider work; existing predicted coordinates can be benchmark inputs without an AI runtime dependency.
- **Calibrated negative backbone difference-density detection:** S06 after exact map/model/data binding and matched-refinement baselines; read-only patch evidence and scientist-calibrated false-positive controls first, S07/campaign review next, direct coordinate fitting later. Retain nearby positive support, ordinary map fit, spatial correlation, occupancy/ADP and processing uncertainty.
- **Direct density-guided fitting:** After frozen map/data identity and matched-refinement baselines exist; ordinary data validation is already required in S06.
- **Broad emergent topology and global reusable recipe promotion:** After bounded explicit cut/repair workflows and independent held-out evidence; do not make these hidden initial release blockers.
- **Symmetry-spanning phosphate angle enforcement:** W68 narrows the gate: existing symmetry-angle kernels pass synthetic/source-native controls, but ordinary input/reconstruction and proxy persistence remain unqualified. Coordinate a complete image-bearing term lifecycle with Cedar, including exclusions and surrounding terms. Preserve P/OP1/OP2 intent; never activate a symmetry bond alone.

## Reconciliation: reuse what is already delivered

<details><summary>Earlier implementation references</summary>

- b2ae9dc planning: retain the design, but this queue now owns work order; historical Next paragraphs are not another queue.
- 6b1dbbd through 71af8ad: reuse candidate/coordinate/periodic/contact/pairing/registration/discovery/window modules; missing scientific closure is not a reason to rebuild them.
- 149a82a: explicit bend preview and portable replay are delivered; they do not close local chemistry or refinement.
- aae51be and 3ef2fad: density, forward/reverse shape and NARestraints-reuse requirements remain acceptance obligations, not implemented capabilities.
- ce0a1bf: bounded fitting is delivered and native limitations recorded; S04/S05 remain partial.
- Pine construct-registration and live-check contracts retain semantics/test cases; this linked queue owns TopoStitch scheduling, not unrelated Scout or Cedar work.
- Selected atom-image audit 2d7544b adds bounded coordinate evidence without an identity merge; do not reimplement it as a second symmetry finder. Native MR preflight does not close the diffraction repair gate.
- Periodic fit guard 84cb847 consumes the existing selected-image audit. Tighter native controls establish a contact/strain tradeoff, not scientific closure; preserve the original failed angle result.
- Schema-2 extended backbone patch 6fc4898 preserves schema-1 replay; S04/S05 remain partial pending native image-aware closure and matched refinement.
- Post-transform image guard a3e4978 catches source-clear candidates that collide after fitting. Native bond/angle derivative and fixed-base relaxation diagnostics narrow S05 uncertainty without creating another Cedar engine or closing scientific gates.
- Native plane probe 7255bfd reuses Cedar correction and records raw failures. A plausible energy is not derivative qualification; do not repeat C23–C27 diagnosis or create another plane-correction implementation.

</details>

Modeled on Cedar’s separation of completion queue, capability contract and
evidence ledger. No queue edit grants runtime authority, scientific approval
or permission to merge branches.
