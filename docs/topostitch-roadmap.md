# TopoStitch and Pine completion roadmap

**Current audited work queue: 2026-11-14.** Generated from
[the machine-readable ledger](topostitch-roadmap.json); edit that ledger and run
`python scripts/audit_topostitch_roadmap.py --write`, then `--check`.
This is one queue with two linked tracks, not two competing implementations.
The [design](topostitch.md) owns semantics, the [handoff](development-handoff.md)
owns the current code/validation edge, and cited evidence owns scientific claims.
A recut changes representation; a bend changes the physical structure. Neither
operation authorizes a chemical nick or chemistry change.

**Current update: W37 — Bind complete canonical recipes to exact atom images.** Next: W38.

Use these numbers in human updates. Exact commits remain in the machine ledger;
earlier history is not renumbered. An update number does not close a scientific gate.

## Recent Willow updates

| Update | Work | Record |
| --- | --- | --- |
| W33 | Human-readable Willow update numbers | RECORDED |
| W34 | Matched 8D93 reference refinement control | RECORDED |
| W35 | Read final Phenix bond and angle RMSDs | RECORDED |
| W36 | Audit native periodic-restraint callback lifecycle | RECORDED |
| W37 | Bind complete canonical recipes to exact atom images | RECORDED |

## Finish lines

- **First explicit stitch:** One explicitly chosen canonical connection can be placed, locally qualified, compared against a matched refinement control and inspected as an immutable unselected child (S01, S03-S07).
- **Campaign stitching:** Add qualified end inference and bounded campaign-local transfer/review (S02, S08), without repeated member prompts or silent promotion.
- **Pine ASU slicing:** A scientist can choose, preview and materialize a faithful ASU cut, prove physical/scattering invariance, preserve seam chemistry and complete the persistent graphical review/refine loop (P01-P06).

## Current order and audit discipline

**Immediate focus:** F02, S03, S04, S05.
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

**Delivered:** Metric-bounded periodic enumeration and exact reciprocal image records exist; physical orbit distinctness is still explicitly unvalidated. Optional selected present-atom orbit/overlap audit reports stabilizer observations, coincident source labels and uncertainty without merging identities; public 8D93 selected coordinates are distinct within that scope. Improving serialized fits repeat the exact selected-image coincidence audit; ambiguous moved candidates are withheld without re-searching partner indices.

**Closure audit:**

- Qualify selected atom/site orbits and coincident/special-position cases; do not infer identity from endpoint centers or duplicate labels.
- Check nonorthogonal cells, screw/centering operations, self images, coordinates outside the cell and bounded failure; preserve uncertainty instead of merging ambiguous sites.

**Next action:** Qualify physical partner capacity and complete molecular/image equivalences; the selected-source coordinate precondition is now consumed by periodic fitting.
**Evidence:** [E_SOFTWARE](#e_software), [E_IMAGE_AUDIT](#e_image_audit), [E_POST_IMAGE](#e_post_image).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/a3e497825be1b7983739b35af83fb280897559c2); Source and transformed selected-coordinate evidence, not full physical identity.

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

**Delivered:** Exact nearby images and factorized one-partner alternatives exist; no physical/global assignment is approved. Periodic fitting now returns IMAGE_IDENTITY_REVIEW_REQUIRED with zero solver calls for selected-coordinate coincidences or occupancy uncertainty; no connection is automatically selected.

**Closure audit:**

- A selected edge has verified physical image identity, sequence/register/orientation and capacity; wrong, ambiguous, self-orbit and impossible cases stay distinct.
- Standalone use binds a concrete choice; opt-in inference freezes its scope and alternatives without creating undeclared covalent links.

**Next action:** Close one explicit canonical periodic pairing before broad automatic scheme selection.
**Evidence:** [E_SOFTWARE](#e_software), [E_IMAGE_AUDIT](#e_image_audit).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/84cb847a493654cca8a0ae79f28e000615d5afc3); Conservative source-image precondition, not a global assignment or physical capacity proof.

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

**Delivered:** Three public 8D93 native interpretations preserve atom/proxy membership. The fitted candidate still adds one severe captured angle deviation. Three predeclared tighter-backbone public controls retain exact native definitions/proxies and avoid the original added angle outlier while improving the pair target less; no successful closure claimed. Schema-2 fit/preview adds nonbridging phosphate angles and circular epsilon/zeta/alpha changes; schema-1 replay preserved. Native public 8D93 comparison adds no new severe captured scalar outliers under the explicit development policy. Local native exact-image bond/angle values and gradients qualified for the declared diagnostic; matched fixed-base backbone relaxations pass endpoint/capture checks and resolve three source angle outliers, with iteration-limit caveats. Synthetic and public probes identify unsupported raw native plane gradients; Cartesian image pullback with Cedar existing parallelity correction passes the declared derivative controls. A shared checked Cartesian image/gradient core now drives the viewer and native probe, retaining repeated ASU contributions and failed raw native controls. Local masked native controls bind explicit movement scopes, check every movable Cartesian derivative and compare cleanup versus chosen contacts, with and without existing core-pair terms; native readback remains REVIEW. Complete emitted NARestraints recipes pass local masked derivative/readback checks. Native bond edits demonstrably change exclusions/LINK bookkeeping. Broader bend plus fixed-base cleanup removes its added scalar outlier but worsens other periodic contacts; no candidate is promoted. A thin read-only packing comparator now authenticates/replays Cedar directed native captures, matches relative symmetry transforms and retains per-contact regressions/multiplicity; native capture lifecycle remains owned by Cedar. Native added-term arithmetic passes a bounded probe, but selection/rebuild drops the callback and normalization/enablement need explicit policy; no supported production adapter is claimed. W37 provides a reusable complete canonical pair recipe packet and native additive evaluator, with exact atom/image binding and explicit Cedar correction; independent derivative review outcomes remain visible.

**Closure audit:**

- Audit and, where qualified, relax all affected backbone/sugar geometry, chirality, stacking, planes and periodic clashes; retain unchanged/protected regions and intended contacts.
- Prove native enforcement for the supported symmetry case. Bond-only constraints, source-relative change limits and successful interpretation cannot substitute for full local qualification.

**Next action:** Qualify a captured masked native objective that consumes the complete explicit recipe, preserves fixed atoms and declares normalization/exclusions. Resolve derivative step convergence under a declared general policy; prove lifecycle/identity through intended execution or qualify a Pine recut. Then audit individual geometry and surrounding images with Cedar owners.
**Evidence:** [E_NATIVE_8D93](#e_native_8d93), [E_TIGHTER_NATIVE](#e_tighter_native), [E_EXTENDED_BACKBONE](#e_extended_backbone), [E_NATIVE_TRANSPORT_RELAX](#e_native_transport_relax), [E_NATIVE_PLANES](#e_native_planes), [E_TRANSPORT](#e_transport), [E_MASKED_NATIVE](#e_masked_native), [E_PACKING](#e_packing), [E_NATIVE_CALLBACK](#e_native_callback), [E_PAIR_RECIPE](#e_pair_recipe).
**Last audit:** 2026-11-14, Linden, [W37](https://github.com/vecchioni-lab/NASolve/commit/8653b96f6b79bb1c66b12afb59261ceb4b6ef9be); Complete recipe binding/arithmetic; independent controls and failures retained; no geometry or refinement acceptance.

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
| [P02](#p02) | Offer cut choices in a required graphical preview | OPEN | P01 |
| [P03](#p03) | Materialize a cut without changing the crystal | OPEN | P02 |
| [P04](#p04) | Qualify seam chemistry and native interpretation | OPEN | P03 |
| [P05](#p05) | Complete the persistent Pine surgery/refine GUI loop | OPEN | P04 |
| [P06](#p06) | Pass blind, multiplicity and ordinary-workflow controls | OPEN | P05 |

<a id="p01"></a>
### P01 — Build the periodic molecular graph and declared scope

Represent the observed periodic object independently of a tile hypothesis or PDB chain cut.

**Delivered:** Logical registration and typed end/image observations exist; a complete recut-ready periodic molecular graph does not.

**Closure audit:**

- Retain covalent routes, pairing, stacking and symmetry correspondence as distinct edges, with true nicks, seams, junction passages and unknown coverage explicit.
- Handle complete/partial copies, tile versus ASU multiplicity and repeat-phase/winding without forcing the design stoichiometry or zero translation around every cycle.

**Next action:** Build the minimum graph required for one declared recut; retain broader emergent topology as explicit unsupported scope.
**Evidence:** [E_REGISTRATION](#e_registration), [E_SOFTWARE](#e_software).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="p02"></a>
### P02 — Offer cut choices in a required graphical preview

Let the scientist decide where to slice the ASU while seeing the same physical periodic object.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Enumerate bounded, intent-compatible cut alternatives; show central ASU plus connected mates, ownership, real nicks, seams, exposed ends and affected logical sites.
- Provide an actual selectable graphical before/after preview with explicit ambiguity and unchanged-source identity. No fake Apply action before materialization is supported.

**Next action:** Reuse the offline coordinate viewer where useful, but first supply P01 periodic graph ownership and bounded cut alternatives; implement actual cut selection/materialization preview and human validation.
**Evidence:** [E_VIEW](#e_view).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/0f176a965223af7aafbc433939d2d054f608524a); Shared viewer is available; no Pine cut capability delivered, so P02 stays OPEN.

<a id="p03"></a>
### P03 — Materialize a cut without changing the crystal

Write a new ASU representative while preserving the physical scattering object exactly within validated numerical tolerance.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Preserve atom-orbit inventory/multiplicity, chemistry, occupancy and displacement parameters; rotate ANISOU correctly and update logical mappings without losing or duplicating atoms.
- Independently verify before/after unrefined calculated structure factors in the same cell/setting, reciprocal round trips and relocation. Recutting must not be used to hide a physical gap.

**Next action:** Start with an explicit small cut and an independent scattering/inventory oracle before general cut optimization.
**Evidence:** None yet.
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="p04"></a>
### P04 — Qualify seam chemistry and native interpretation

Make a representation seam remain a continuous backbone where chemistry says it is continuous.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Keep true termini/nicks distinct from ASU seams; preserve continuation phosphates and forbid automatic terminal OP3 chemistry caused only by serialization.
- Qualify native bonds, angles, planes and nonbonded behavior at the seam. Separate any required coordinate repair into a new S-track child; successful recutting itself cannot deform the crystal.

**Next action:** Reuse Pine phosphate intent and Cedar/native diagnostics; execute the existing symmetry-bond and local seam controls.
**Evidence:** [E_PINE_TEST_BANK](#e_pine_test_bank).
**Last audit:** 2026-11-13, Linden, [earlier work](https://github.com/vecchioni-lab/NASolve/commit/ce0a1bfee9d9d63edd09be84fe7a3117c65a6c69); Backend implementation and documented evidence; no new scientific approval.

<a id="p05"></a>
### P05 — Complete the persistent Pine surgery/refine GUI loop

Keep cut, preview, child creation, refinement and review in one usable workbench.

**Delivered:** No implemented capability is claimed.

**Closure audit:**

- Use the shared model tree and exact selection/Coot APIs; keep inspect, select and approve distinct, preserve current choice and return refinement diagnostics to the same session.
- Graphical actions bind source hashes and show actual nicks/seams/mates. Test stale views, competing choices, interrupted actions, manual imports and relocation without duplicating campaign/checkpoint machinery.

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
| B06 — Density-guided and nonuniform/strand-specific relaxation | PLANNED_EXTENSION | S04, S06 | After qualified geometric placement and matched refinement, add a read-only model/map-bound detector of sustained negative difference-density patches along sugar-phosphate backbones. Calibrate with Simon against healthy/noisy and displaced controls across resolution, occupancy/ADP and map-processing conditions before proposing motion. Then consider nonuniform/strand-specific density-guided fitting; a red voxel or universal sigma cutoff is not a displacement instruction. |

## Evidence and limits

<a id="e_software"></a>
### E_SOFTWARE — software_validation

[Evidence contract](topostitch-periodic.md#current-validation-receipt--2026-11-13) at [W37](https://github.com/vecchioni-lab/NASolve/commit/8653b96f6b79bb1c66b12afb59261ceb4b6ef9be).
W37 freezes complete canonical pair recipes and evaluates exact atom images. Focused source: 88 tests; full source: 1,312 tests + 229 subtests. Installed wheel: 438 focused tests + 18 subtests. Relocated copied checkout with original absent: 96 tests. Isolated installed native compiler reproduces complete 14-pair energy/components. Python 3.10 syntax and lean optional imports pass. Existing preview schemas/entry points remain unchanged.
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

## Deferred extensions, not hidden blockers

- **Canonical rebuilding / missing-residue generation:** Only after intact-duplex placement is qualified and an explicit rebuilding case requires it; preserve sequence and separately qualify chemistry.
- **Junction hinges and broader modified/RNA/backbone chemistry:** Explicit capability and native tests; fixed junctions and canonical DNA remain the first supported scope.
- **AlphaFold provider integration:** Separate input-provider work; existing predicted coordinates can be benchmark inputs without an AI runtime dependency.
- **Calibrated negative backbone difference-density detection:** S06 after exact map/model/data binding and matched-refinement baselines; read-only patch evidence and scientist-calibrated false-positive controls first, S07/campaign review next, direct coordinate fitting later. Retain nearby positive support, ordinary map fit, spatial correlation, occupancy/ADP and processing uncertainty.
- **Direct density-guided fitting:** After frozen map/data identity and matched-refinement baselines exist; ordinary data validation is already required in S06.
- **Broad emergent topology and global reusable recipe promotion:** After bounded explicit cut/repair workflows and independent held-out evidence; do not make these hidden initial release blockers.

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
