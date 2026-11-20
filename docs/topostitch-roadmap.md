# TopoStitch and Pine completion roadmap

**Current audited work queue: 2026-11-20.** Generated from
[the machine-readable ledger](topostitch-roadmap.json); edit that ledger and run
`python scripts/audit_topostitch_roadmap.py --write`, then `--check`.
This is one queue with two linked tracks, not two competing implementations.
The [design](topostitch.md) owns semantics, the [handoff](development-handoff.md)
owns the current code/validation edge, and cited evidence owns scientific claims.
A recut changes representation; a bend changes the physical structure. Neither
operation authorizes a chemical nick or chemistry change.

**Current update: W174 — Join checked motion to frozen child inputs.** Next: W175.

Use these numbers in human updates. Exact commits remain in the machine ledger;
earlier history is not renumbered. An update number does not close a scientific gate.

## Recent Willow updates

| Update | Work | Record |
| --- | --- | --- |
| W165 | Plan a default backbone-fit check with separate repair review | RECORDED |
| W166 | Carry known parent geometry without a global cutoff change | RECORDED |
| W167 | Align intact-cluster placement and coupled DNA opening | RECORDED |
| W168 | Retain parent chemistry through child diffraction and recovery | RECORDED |
| W169 | Reuse the existing coordinate-only admission guard | RECORDED |
| W170 | Inspect saved maps at the remaining B2/A13 distortion | RECORDED |
| W171 | Bind a saved motion to the current parent snapshot | RECORDED |
| W172 | Require declared topology before parent-coordinate transfer | RECORDED |
| W173 | Bind motion to selected checkpoint inputs | RECORDED |
| W174 | Join checked motion to frozen child inputs | RECORDED |

## Finish lines

- **First explicit stitch:** One explicitly chosen canonical connection can be placed, locally qualified, compared against a matched refinement control and inspected as an immutable unselected child (S01, S03-S07). Final altered-arm end-to-end demonstration: pass the frozen geotest panel (B09), including X11_18 in P4_3 and X11_22, after the general geometry/refinement gates.
- **Campaign stitching:** Add qualified end inference and bounded campaign-local transfer/review (S02, S08), without repeated member prompts or silent promotion.
- **Pine ASU slicing:** A scientist can choose, preview and materialize a faithful ASU cut, prove physical/scattering invariance, preserve seam chemistry and complete the persistent graphical review/refine loop (P01-P06).

## Current order and audit discipline

**Immediate focus:** F02, S03, S04, S05, S06, P01.
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
- Classify designed blunts from construct intent and observed coverage; allow one supported stacking pair and same-polarity contact without inferring covalent continuation.

**Next action:** Build a bounded evidence adapter after the explicit-placement physics is qualified; do not reimplement the guesser.
**Evidence:** [E_SOFTWARE](#e_software), [E_NAR_REVIEW](#e_nar_review), [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan).
**Last audit:** 2026-11-16, Linden, [W93](https://github.com/vecchioni-lab/NASolve/commit/5965d8588984c6991f587bdaec049639264d03e4); Planning acceptance extended for blunt/asymmetric controls; prior delivered runtime scope and open scientific gates unchanged. No new native solve..

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

**Delivered:** Checked tapered six-parameter previews/fitting preserve declared anchors, atom order, ANISOU, budgets and rounded-output limits; saved previews and explicit pivot rotations reuse exact Cartesian image ownership. W85–W91 qualify derivative pullback, captured diagnostic starts and immutable motion compilation. Matched small coarse seeds give no demonstrated benefit over atomic cleanup; rounding/precision failures are retained. W96–W100 qualify guarded full-window source-driven atomic controls. Three displaced controls pass numerical/binding checks but stop at iteration limits; selected/core pair gains coexist with individual geometry/packing tradeoffs. No accepted repair. W138/Cedar4f7aeb84 qualifies the explicit v8 100-cap ordinary coordinate route with complete source/installed/native gates. The earlier short route retains its original scope; neither cap proves convergence. W139 closes the matched native/core-only-zero/full matrix: exact zero/native output/history, passive full equivalence and common14-pair local benefit. Both line-search stops and repeated-coordinate normalization discontinuity remain separate limitations; no numerical policy is adopted. W148 reuses the exact W100 +5-degree canonical displacement with matching noiseless diffraction and fixed native refinement. Selected 204-atom RMS error falls 0.917427 to 0.029167 Å; endpoint-to-endpoint RMS is 0.026449 Å. Local covalent bonds recover, 126 sugar-volume signs survive, and Rowan independently reproduces the controls. Existing reference-link distortion remains explicit. W151 deposited 8D93 polymer positions3/4 map to PDB B107/B111: the numbering jump is not three missing residues. The existing phosphate-angle distortion is already deposited. W115 unvalidated-preview lineage remains explicit; recovery is distinct from a healthy-reference qualification. W152 independent deposited5W6W opposite displacements recover from0.7641A RMS to0.05152/0.04653A; relaxed-reference drift0.01436A. Local232 bonds/363 angles,38 links,126 sugar signs and2569 common targets independently audited. Identical58 parallelity groups retain explicit source/boundary residuals; idealized matching data only. W153 deposited5W6W experimental comparison preserves5137 raw observations/507originalFree, but positive native filtering drops one work reflection. Endpoints approach relaxed control0.21485/0.14566A; reference itself moves0.52152A and Rfree rises~0.019. Geometry improves, strong B2P negative density remains. Common4629work/507Free endpoint arithmetic reuses saved F-model without refit; mixed outcome, not accepted repair. W163: Signed15degree tapered starts move205atoms2.288A RMS, up to4.79A. Default3A interpretation drops one3.836A O3P bond and4angles; that first attempt is held without fitting. Matched private4A interpretation retains38links,58complete planes, captured proxy definitions and fixed nonbonded exclusions. Five-cycle recovery reaches.758/.279A RMS; unchanged reference reproduces W152 atoms/maps exactly. Known canonical same-ASU links and noiseless matching diffraction only; no production cutoff change, automatic bond inference or symmetry-seam qualification. Original inherited torsion inventory is incomplete and explicitly qualified. W164: One matched further5cycle restart reaches.25257/.03972A RMS from the generator; no-op remains.01436A. Final Rwork/Rfree .0211/.0259 and.0086/.0100. All859atoms,38links,126sugar signs and7554raw/effective endpoint F/SIGF/Free tuples survive. Positive B2O3-prime remains1.41A away and a local angle deviates31.32degrees. Nine reconstructed managers have identical explicit443torsion/62plane policies through the existing live owner. 601cold checks;51offline view checks and6-model ChimeraX1.12 headless load pass. Five plus five cycles with a rounded-PDB restart, not uninterrupted10cycles or convergence proof. Low R values do not accept the positive distortion. Noiseless synthetic data and one target shape; reconstructed manager policy does not retroactively fill omitted optimizer fields. Browser/GPU/human review and broad repair remain open. W166 retains 38 known same-ASU backbone links, the 3.8359 A bond and four flank angles using the default-cutoff parent manager with identity-mapped displaced sites. Complete geometry/planes/torsion policies and fixed exclusions agree with independent 4 A controls; raw energy/gradient comparisons pass and parent restoration is exact. Three qualified dry-runs, seven energy calls, 77 cold checks; no refinement. Geometry-only returned-manager scope, not pre-fmodel integration, optimizer execution, automatic topology or accepted repair. Five setup refusals are preserved; native OP3 reordering requires exact atom mapping. No production source/schema/default change. W167 records user/Hazel/Rowan coordination: intact cluster rigid pose, then bounded coupled DNA opening/closing when needed, source chemical geometry/exclusions, neighboring-step/donor/width measurements and Alder A03/A07 recovery/assessment. Bridge linearity, cluster shape/local coordination/oxidation and count hypotheses remain distinct. Planning only. No dedicated width mode, cluster experiment, new target/default or combined-runtime qualification; W166 signed-bend geometry transport and FT_Hg descriptive evidence cannot qualify cluster accommodation. W168 carries parent-derived same-ASU chemistry through child-native diffraction preparation at the default 3 A cutoff. Two dry-runs pass 102 checks with exact initial Fcalc/Fmodel/masks and 7554 original tuples/389 Free; 38 links, the stretched bond/four angles and complete fixed geometry/policies remain. One admitted five-cycle native fit passes 39 cold checks and improves selected RMS 2.287991 to 0.271141 A (prior 4 A control 0.279044);RW/RF .0467/.0589. Local covalent RMS .007954 A/1.965877 deg, largest angle deviation 10.54 deg; all 126 sugar signs remain. Endpoints differ .008788 A RMS, not exact replay. One canonical signed synthetic control, private process-local wrappers, not an installed/ordinary workflow, new link inference, modified chemistry, cluster widening, symmetry-seam qualification or accepted repair. Native diffraction is constructed before chemical interpretation, so the former pre-fmodel description is superseded for this entry. Complete source topology and input-admission/execution integration remain separate gates; no further fit queued. W169 reuses audit_masked_endpoint and rebind_pair_recipe on actual W168 source/candidate bytes. Real displacement and no-op pass; eight altered children are refused by the endpoint owner, while generic rebinding keeps its intended B-change and unrestricted-coordinate scope. Source 27 / existing installed C407 29 checks pass with exact scientific readback; five owner modules are byte-identical. No missing fixed-B/Q helper was found, no product code changed and no native call or fit ran. Cold byte/mask binding only. Supplied coordinates are saved three-decimal PDB points; the 5 A audit bound is declared posthoc and does not authenticate the original unrounded proposal or prospective admission. A fresh seven-pair recipe exercises binding only and does not replace executed native restraints. Existing installed-package replay is not a fresh installation qualification. Source chemistry/site symmetry, native topology/exclusions, fresh diffraction, callback lifetime and ordinary ancestry still require supported integration. W171: Optional parent_model_bytes on load_bend_motion compares the admitting caller's immutable parent snapshot with the pinned preview source before returning the existing full-precision motion. Both preview schemas compose with the unchanged strict endpoint audit. Coordinate, B/Q, identity and metadata drift, mutable/non-byte input and sub-rounding bound violations are refused. Twelve new cases fail before; 118 focused and 118 source-free relocated installed tests pass, with 93 package-file hashes, pip check and six entry-point helps. Snapshot binding only: caller still owns checkpoint identity, dispatch freshness and retained-parent/native lifecycle integration. Existing calls/returns and artifacts need no migration; no default, tensor policy, chemistry, CLI or native execution changes. Canonical registered-terminal-preview scope; no modified-metal opening, covalent closure, new refinement or scientific acceptance. No full-suite rerun for this isolated additive API change. W172 binds a fresh registered 60-atom,0.048166 A maximum preview through W171 and the strict endpoint owner, then checks actual parent topology before and after private native transfer. No optimizer or installed/ordinary lifecycle qualification. W173 binds a saved canonical preview to an exact selected/current checkpoint and its anchored model, observations, ordered restraints and declared phases. It rechecks inputs around strict endpoint replay and supports a context pin for a fresh dispatch read. 138 focused plus 6 subtests and the same relocated/source-free installed suite pass; 25 added cases include selection drift, input races and old-path-gone relocation. Read-only admission only; no native hook, run lock, schema migration or scientific acceptance. W174 joins W173 to Cedar-owned frozen execution requests, distinguishing parent/candidate model roles and ordered inherited/adapted/extra restraints, phases and generated round parameters.159 focused+6 subtests and relocated installed tests pass;21 new cases,223 cold checks on real C412 v3/v7 requests and17 synthetic supported-reader checks in both source and installed contexts. No native call, chemical admission, lock or ordinary motion qualification.

**Closure audit:**

- Known-answer straight-to-curved, bent-to-straight and changed-direction cases recover within predeclared scope; healthy controls do not receive unjustified changes.
- Qualify whole-pair window expansion, nonuniform curvature and finite failure without crossing protected junctions. A fixed taper is initialization, not measured conformation.
- Qualify coupled bending/elongation, step twist/rise and strand-specific sugar-phosphate relaxation, including fixed-window boundaries; rigid-base preview motion alone is insufficient.

**Next action:** Join W172 complete independently declared canonical chemistry and the exact candidate to W174 child-input binding; audit moving and untouched regions against one parent. Use a supported source-bound native owner only with complete policy for that actual parent. A private diagnostic control cannot supply ordinary checkpoint ancestry; C412 modified PDU is not canonical preview authority. Keep FT and legacy soft-policy gaps at REVIEW, and coordinate the maintained native transfer hook with Cedar before any fit.
**Evidence:** [E_SOFTWARE](#e_software), [E_NATIVE_8D93](#e_native_8d93), [E_TIGHTER_NATIVE](#e_tighter_native), [E_EXTENDED_BACKBONE](#e_extended_backbone), [E_COARSE_NATIVE_DERIVATIVES](#e_coarse_native_derivatives), [E_BOUNDED_NATIVE_MOTION](#e_bounded_native_motion), [E_MATCHED_COARSE_TRIALS](#e_matched_coarse_trials), [E_SAVED_BEND_MOTION](#e_saved_bend_motion), [E_COARSE_RESOLUTION](#e_coarse_resolution), [E_ATOMIC_DIAGNOSTIC_START](#e_atomic_diagnostic_start), [E_MATCHED_ATOMIC_STARTS](#e_matched_atomic_starts), [E_LIVE_NONBONDED_CONTRACT](#e_live_nonbonded_contract), [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan), [E_PIVOT_ROTATION](#e_pivot_rotation), [E_GUARD_INTEGRATION_PREP](#e_guard_integration_prep), [E_LIVE_POLICY_CONSUMER](#e_live_policy_consumer), [E_GUARDED_CAPTURED_WORKER](#e_guarded_captured_worker), [E_CAPTURED_DIAGNOSTIC_START](#e_captured_diagnostic_start), [E_FULL_WINDOW_NATIVE_CONTROL](#e_full_window_native_control), [E_C338_INSTALLED_COMPOSITION](#e_c338_installed_composition), [E_SOURCE_DISPLACED_NATIVE](#e_source_displaced_native), [E_SEPARATE_SCREENING_NORMALIZATION](#e_separate_screening_normalization), [E_MATCHING_BACKBONE_RECOVERY](#e_matching_backbone_recovery), [E_REFERENCE_SEQUENCE_ADJACENCY](#e_reference_sequence_adjacency), [E_INDEPENDENT_OPPOSITE_RECOVERY](#e_independent_opposite_recovery), [E_EXPERIMENTAL_BACKBONE_TRADEOFF](#e_experimental_backbone_tradeoff), [E_LARGER_DECLARED_LINKS](#e_larger_declared_links), [E_LARGER_RECOVERY_WINDOW](#e_larger_recovery_window), [E_PARENT_GEOMETRY_TRANSPORT](#e_parent_geometry_transport), [E_CLUSTER_ACCOMMODATION_PLAN](#e_cluster_accommodation_plan), [E_PARENT_PREPARATION_RECOVERY](#e_parent_preparation_recovery), [E_EXISTING_COORDINATE_ADMISSION](#e_existing_coordinate_admission), [E_SAVED_PARENT_BINDING](#e_saved_parent_binding), [E_LIVE_PARENT_TOPOLOGY](#e_live_parent_topology), [E_CHECKPOINT_MOTION_BINDING](#e_checkpoint_motion_binding), [E_EXECUTION_MOTION_BINDING](#e_execution_motion_binding).
**Last audit:** 2026-11-20, Linden; Cedar interface reviewed by Rowan, [W174](https://github.com/vecchioni-lab/NASolve/commit/02411806ad7d444672803a27e6699f68b11d888d); Frozen request/input join and installed supported-reader controls; no native transfer or general repair closure.

<a id="s05"></a>
### S05 — Close and qualify the local atomic geometry

Turn a plausible placement into a chemically usable candidate before refinement is trusted.

**Delivered:** Canonical recipe/image/gradient, masked native/pair/tether composition and captured-job owners are qualified for explicit movement scopes. Exact source binding, full/rounded derivative checks, native geometry/packing observers and failed endpoint evidence remain available. W51–W61 and W85–W100 establish numerical-resolution, coarse/atomic and source-tether boundaries. Matched failures are preserved; repeat closed controls only for a declared new question. W104–W118 bind requested canonical terms to exact actual native coverage, evaluate only missing forces and explicitly rebind compatible parent bytes without changing original chemistry/images. Covalent/terminal ownership is not inferred from origin IDs. Cedar integration through W125–W134 owns durable admission, actual prepared state, registered same-intent continuation, original writer identity and final pair capture. Historical payloads retain narrower proof. Ordinary chemistry observation can coexist; broad chemistry repair remains separate. W138/Cedar4f7aeb84 qualifies the explicit v8 100-cap ordinary coordinate route with complete source/installed/native gates. The earlier short route retains its original scope; neither cap proves convergence. W139 closes the matched native/core-only-zero/full matrix: exact zero/native output/history, passive full equivalence and common14-pair local benefit. Both line-search stops and repeated-coordinate normalization discontinuity remain separate limitations; no numerical policy is adopted. W140 measures1268 recorded native sugar/phosphate/glycosidic supports,38existingO3P links and126preserved ordered sugar signs. Independent3804printed-geometry+342torsion checks pass; local backbone deviations remain similar while end bases move. No complete pucker/packing/closure acceptance. W122 explicit sticky-end enforcement is planning-only. General seam closure, mismatch/blunt qualification, larger bending and density-supported repair remain open. W148 reuses the exact W100 +5-degree canonical displacement with matching noiseless diffraction and fixed native refinement. Selected 204-atom RMS error falls 0.917427 to 0.029167 Å; endpoint-to-endpoint RMS is 0.026449 Å. Local covalent bonds recover, 126 sugar-volume signs survive, and Rowan independently reproduces the controls. Existing reference-link distortion remains explicit. W151 deposited 8D93 polymer positions3/4 map to PDB B107/B111: the numbering jump is not three missing residues. The existing phosphate-angle distortion is already deposited. W115 unvalidated-preview lineage remains explicit; recovery is distinct from a healthy-reference qualification. W152 independent deposited5W6W opposite displacements recover from0.7641A RMS to0.05152/0.04653A; relaxed-reference drift0.01436A. Local232 bonds/363 angles,38 links,126 sugar signs and2569 common targets independently audited. Identical58 parallelity groups retain explicit source/boundary residuals; idealized matching data only. W153 deposited5W6W experimental comparison preserves5137 raw observations/507originalFree, but positive native filtering drops one work reflection. Endpoints approach relaxed control0.21485/0.14566A; reference itself moves0.52152A and Rfree rises~0.019. Geometry improves, strong B2P negative density remains. Common4629work/507Free endpoint arithmetic reuses saved F-model without refit; mixed outcome, not accepted repair. W159 completes one five-cycle ordinary-recipe diagnostic on the same undeformed5W6W source. Exact859atoms,2569initial bond/angle definitions,58pair/stack groups and5137effective observations/507originalFree survive;38links and126sugar signs remain. Selected drift0.591A versus0.522A; common Rwork/Rfree0.2264/0.2677 versus0.2392/0.2600. B2P B90.39→112.52 while own residual remains−8.38σ versus−8.09σ. This does not resolve the reference baseline; no opposite-start matrix or accepted repair. W161 cold review covers42residues,459backbone atoms at3states in4held maps (5508samples),41P versus38existingO3-P links, and unchanged4bond/angle families. A10C5-prime moves2.543A into higher ordinary density in both held sources; D2OP1 moves2.520A into lower density. All76printed weight trials fail the.015A first bond screen, requiring native fallback; final51pair distances contribute99.11% of pooled squared bond deviations, not energy/force. Reuses C395/C396 diagnosis; one posthoc A9-11 viewer added. No refinement or selector change. W162: Passive LS/ML observation reproduces all859 final atom records, both saved MTZ arrays and printed trials. Replay matches73returned states and the selected cycle5 weight7 frame. Geometry/combined local derivatives pass; data-only checks miss their prospective bound, so no finite profile runs. Both direct and FFT target/gradient restorations are exact. 194passive and120profile cold checks pass. Private diagnostic, not ordinary PostMR ancestry, a complete generic state serializer or accepted motion. Historical dihedral limit/top_out/slack are omitted; no complete six-family state claim. No tolerance retuning or new numerical-policy sweep follows. W163: Signed15degree tapered starts move205atoms2.288A RMS, up to4.79A. Default3A interpretation drops one3.836A O3P bond and4angles; that first attempt is held without fitting. Matched private4A interpretation retains38links,58complete planes, captured proxy definitions and fixed nonbonded exclusions. Five-cycle recovery reaches.758/.279A RMS; unchanged reference reproduces W152 atoms/maps exactly. Known canonical same-ASU links and noiseless matching diffraction only; no production cutoff change, automatic bond inference or symmetry-seam qualification. Original inherited torsion inventory is incomplete and explicitly qualified. W164: One matched further5cycle restart reaches.25257/.03972A RMS from the generator; no-op remains.01436A. Final Rwork/Rfree .0211/.0259 and.0086/.0100. All859atoms,38links,126sugar signs and7554raw/effective endpoint F/SIGF/Free tuples survive. Positive B2O3-prime remains1.41A away and a local angle deviates31.32degrees. Nine reconstructed managers have identical explicit443torsion/62plane policies through the existing live owner. 601cold checks;51offline view checks and6-model ChimeraX1.12 headless load pass. Five plus five cycles with a rounded-PDB restart, not uninterrupted10cycles or convergence proof. Low R values do not accept the positive distortion. Noiseless synthetic data and one target shape; reconstructed manager policy does not retroactively fill omitted optimizer fields. Browser/GPU/human review and broad repair remain open. W166 retains 38 known same-ASU backbone links, the 3.8359 A bond and four flank angles using the default-cutoff parent manager with identity-mapped displaced sites. Complete geometry/planes/torsion policies and fixed exclusions agree with independent 4 A controls; raw energy/gradient comparisons pass and parent restoration is exact. Three qualified dry-runs, seven energy calls, 77 cold checks; no refinement. Geometry-only returned-manager scope, not pre-fmodel integration, optimizer execution, automatic topology or accepted repair. Five setup refusals are preserved; native OP3 reordering requires exact atom mapping. No production source/schema/default change. W167 records user/Hazel/Rowan coordination: intact cluster rigid pose, then bounded coupled DNA opening/closing when needed, source chemical geometry/exclusions, neighboring-step/donor/width measurements and Alder A03/A07 recovery/assessment. Bridge linearity, cluster shape/local coordination/oxidation and count hypotheses remain distinct. Planning only. No dedicated width mode, cluster experiment, new target/default or combined-runtime qualification; W166 signed-bend geometry transport and FT_Hg descriptive evidence cannot qualify cluster accommodation. W168 carries parent-derived same-ASU chemistry through child-native diffraction preparation at the default 3 A cutoff. Two dry-runs pass 102 checks with exact initial Fcalc/Fmodel/masks and 7554 original tuples/389 Free; 38 links, the stretched bond/four angles and complete fixed geometry/policies remain. One admitted five-cycle native fit passes 39 cold checks and improves selected RMS 2.287991 to 0.271141 A (prior 4 A control 0.279044);RW/RF .0467/.0589. Local covalent RMS .007954 A/1.965877 deg, largest angle deviation 10.54 deg; all 126 sugar signs remain. Endpoints differ .008788 A RMS, not exact replay. One canonical signed synthetic control, private process-local wrappers, not an installed/ordinary workflow, new link inference, modified chemistry, cluster widening, symmetry-seam qualification or accepted repair. Native diffraction is constructed before chemical interpretation, so the former pre-fmodel description is superseded for this entry. Complete source topology and input-admission/execution integration remain separate gates; no further fit queued. W169 reuses audit_masked_endpoint and rebind_pair_recipe on actual W168 source/candidate bytes. Real displacement and no-op pass; eight altered children are refused by the endpoint owner, while generic rebinding keeps its intended B-change and unrestricted-coordinate scope. Source 27 / existing installed C407 29 checks pass with exact scientific readback; five owner modules are byte-identical. No missing fixed-B/Q helper was found, no product code changed and no native call or fit ran. Cold byte/mask binding only. Supplied coordinates are saved three-decimal PDB points; the 5 A audit bound is declared posthoc and does not authenticate the original unrounded proposal or prospective admission. A fresh seven-pair recipe exercises binding only and does not replace executed native restraints. Existing installed-package replay is not a fresh installation qualification. Source chemistry/site symmetry, native topology/exclusions, fresh diffraction, callback lifetime and ordinary ancestry still require supported integration. W170 saved-map review locates signed residuals at both remaining distorted sites; A13 C5-prime has higher ordinary density at the misplaced point. Geometry and signed context remain necessary in this noiseless example. Repair and causal diagnosis remain open; see E_SAVED_RESIDUAL_MAP_REVIEW. W172 reproduces saved declared/unintended-bond controls and holds legacy W168 soft-policy ambiguity. The separate explicit-policy live control retains38 backbone links,51 soft distances,all213 supplied terms and phosphate identities;35 cold checks. Chemistry and symmetry seams remain separate. W173 binds a saved canonical preview to an exact selected/current checkpoint and its anchored model, observations, ordered restraints and declared phases. It rechecks inputs around strict endpoint replay and supports a context pin for a fresh dispatch read. 138 focused plus 6 subtests and the same relocated/source-free installed suite pass; 25 added cases include selection drift, input races and old-path-gone relocation. Read-only admission only; no native hook, run lock, schema migration or scientific acceptance. W174 joins W173 to Cedar-owned frozen execution requests, distinguishing parent/candidate model roles and ordered inherited/adapted/extra restraints, phases and generated round parameters.159 focused+6 subtests and relocated installed tests pass;21 new cases,223 cold checks on real C412 v3/v7 requests and17 synthetic supported-reader checks in both source and installed contexts. No native call, chemical admission, lock or ordinary motion qualification.

**Closure audit:**

- Audit and, where qualified, relax all affected backbone/sugar geometry, chirality, stacking, planes and periodic clashes; retain unchanged/protected regions and intended contacts.
- Prove native enforcement for the supported symmetry case. Bond-only constraints, source-relative change limits and successful interpretation cannot substitute for full local qualification.
- For advertised explicit sticky-end enforcement modes, qualify exact-image contact geometry and native/additive coverage; independently validate any plane-only mismatch recipe without inventing canonical H-bonds, stacking or covalent closure.

**Next action:** Join W172 complete independently declared canonical chemistry and the exact candidate to W174 child-input binding; audit moving and untouched regions against one parent. Use a supported source-bound native owner only with complete policy for that actual parent. A private diagnostic control cannot supply ordinary checkpoint ancestry; C412 modified PDU is not canonical preview authority. Keep FT and legacy soft-policy gaps at REVIEW, and coordinate the maintained native transfer hook with Cedar before any fit.
**Evidence:** [E_NATIVE_8D93](#e_native_8d93), [E_TIGHTER_NATIVE](#e_tighter_native), [E_EXTENDED_BACKBONE](#e_extended_backbone), [E_NATIVE_TRANSPORT_RELAX](#e_native_transport_relax), [E_NATIVE_PLANES](#e_native_planes), [E_TRANSPORT](#e_transport), [E_MASKED_NATIVE](#e_masked_native), [E_PACKING](#e_packing), [E_NATIVE_CALLBACK](#e_native_callback), [E_PAIR_RECIPE](#e_pair_recipe), [E_MASKED_COMPOSITION](#e_masked_composition), [E_CAPTURED_COMPOSITION](#e_captured_composition), [E_ENDPOINT_REVIEW](#e_endpoint_review), [E_BOUNDED_TRIAL](#e_bounded_trial), [E_CAPTURED_JOB_API](#e_captured_job_api), [E_ENDPOINT_OBSERVATIONS](#e_endpoint_observations), [E_PAIR_ATTRIBUTION](#e_pair_attribution), [E_CORE_CONTROL](#e_core_control), [E_NATIVE_TERMS](#e_native_terms), [E_NATIVE_STOPPING_LIMIT](#e_native_stopping_limit), [E_NATIVE_PRECISION](#e_native_precision), [E_FAILED_ENDPOINT_DIAGNOSTIC](#e_failed_endpoint_diagnostic), [E_FAILED_ENDPOINT_CHEMISTRY](#e_failed_endpoint_chemistry), [E_COARSE_NATIVE_DERIVATIVES](#e_coarse_native_derivatives), [E_BOUNDED_NATIVE_MOTION](#e_bounded_native_motion), [E_MATCHED_COARSE_TRIALS](#e_matched_coarse_trials), [E_SAVED_BEND_MOTION](#e_saved_bend_motion), [E_ATOMIC_DIAGNOSTIC_START](#e_atomic_diagnostic_start), [E_MATCHED_ATOMIC_STARTS](#e_matched_atomic_starts), [E_LIVE_NONBONDED_CONTRACT](#e_live_nonbonded_contract), [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan), [E_GUARD_INTEGRATION_PREP](#e_guard_integration_prep), [E_LIVE_POLICY_CONSUMER](#e_live_policy_consumer), [E_GUARDED_CAPTURED_WORKER](#e_guarded_captured_worker), [E_CAPTURED_DIAGNOSTIC_START](#e_captured_diagnostic_start), [E_FULL_WINDOW_NATIVE_CONTROL](#e_full_window_native_control), [E_C338_INSTALLED_COMPOSITION](#e_c338_installed_composition), [E_SOURCE_DISPLACED_NATIVE](#e_source_displaced_native), [E_DUAL_NATIVE_STATE](#e_dual_native_state), [E_FROZEN_PAIR_CONTRIBUTION](#e_frozen_pair_contribution), [E_COUNTED_OWNER_LIFETIME](#e_counted_owner_lifetime), [E_ACTUAL_PREPARED_STATE](#e_actual_prepared_state), [E_BOUNDED_ORDINARY_LIFECYCLE](#e_bounded_ordinary_lifecycle), [E_EXACT_IMAGE_FASTPATH](#e_exact_image_fastpath), [E_SAME_FRAME_PAIR_REBIND](#e_same_frame_pair_rebind), [E_C374_JOINED_PACKAGE](#e_c374_joined_package), [E_STRONG_PREPARED_PHASE](#e_strong_prepared_phase), [E_STRONG_COMPLETE_CYCLE](#e_strong_complete_cycle), [E_CURRENT_JOINED_INSTALLATION](#e_current_joined_installation), [E_C377_MAINTAINED_PHASE](#e_c377_maintained_phase), [E_FROZEN_PHASE_AND_FAILURE](#e_frozen_phase_and_failure), [E_EXPLICIT_STICKY_REFINEMENT_PLAN](#e_explicit_sticky_refinement_plan), [E_ORDINARY_PAIR_ATTRIBUTION](#e_ordinary_pair_attribution), [E_PACKAGE_OWNED_INTEGRATION](#e_package_owned_integration), [E_DURABLE_COUNTED_ADMISSION](#e_durable_counted_admission), [E_REGISTERED_COUNTED_CONTINUATION](#e_registered_counted_continuation), [E_SEPARATE_SCREENING_NORMALIZATION](#e_separate_screening_normalization), [E_ACTUAL_STATE_AND_LINEAGE](#e_actual_state_and_lineage), [E_LONGER_ORDINARY_CONTROL](#e_longer_ordinary_control), [E_MATCHED_CANONICAL_LONG_CONTROL](#e_matched_canonical_long_control), [E_BACKBONE_SAVED_DENSITY](#e_backbone_saved_density), [E_MATCHING_BACKBONE_RECOVERY](#e_matching_backbone_recovery), [E_REFERENCE_SEQUENCE_ADJACENCY](#e_reference_sequence_adjacency), [E_INDEPENDENT_OPPOSITE_RECOVERY](#e_independent_opposite_recovery), [E_EXPERIMENTAL_BACKBONE_TRADEOFF](#e_experimental_backbone_tradeoff), [E_DISCRIMINATING_RECOVERY_PLAN](#e_discriminating_recovery_plan), [E_ORDINARY_RECOVERY_DIAGNOSTIC](#e_ordinary_recovery_diagnostic), [E_SAVED_RECOVERY_CONTEXT](#e_saved_recovery_context), [E_CURRENT_BACKBONE_STATE](#e_current_backbone_state), [E_LARGER_DECLARED_LINKS](#e_larger_declared_links), [E_LARGER_RECOVERY_WINDOW](#e_larger_recovery_window), [E_PARENT_GEOMETRY_TRANSPORT](#e_parent_geometry_transport), [E_CLUSTER_ACCOMMODATION_PLAN](#e_cluster_accommodation_plan), [E_PARENT_PREPARATION_RECOVERY](#e_parent_preparation_recovery), [E_EXISTING_COORDINATE_ADMISSION](#e_existing_coordinate_admission), [E_SAVED_RESIDUAL_MAP_REVIEW](#e_saved_residual_map_review), [E_LIVE_PARENT_TOPOLOGY](#e_live_parent_topology), [E_CHECKPOINT_MOTION_BINDING](#e_checkpoint_motion_binding), [E_EXECUTION_MOTION_BINDING](#e_execution_motion_binding).
**Last audit:** 2026-11-20, Linden; Cedar interface reviewed by Rowan, [W174](https://github.com/vecchioni-lab/NASolve/commit/02411806ad7d444672803a27e6699f68b11d888d); Frozen request/input join and installed supported-reader controls; no native transfer or general repair closure.

<a id="s06"></a>
### S06 — Demonstrate improvement against diffraction data

Compare repaired and unmodified models fairly, then determine where data support curvature and strand-specific motion.

**Delivered:** W34 public-reference and supplied-data MR controls retain exact observations/Free-R and show local geometry/diffraction tradeoffs; these are not repaired-MR success cases. Actual pair/native coverage, provider complement, hierarchy/scattering state and counted ownership are qualified through existing compiler and Cedar lifecycle owners. Default/native/zero equality, failure retention, relocated installed proof and original writer lineage are separate checks. W129/W131/W133 expose provider-dependent pooled summaries while retaining complete physical pair metrics and actual final-state observations; unclassified native remainder is not a semantic weighting policy. W132/W135/W138 complete unfiltered shared regressions at their exact pins; installed compositions and native executions retain separate evidence. W142 closes C402 at12016+293 passes/two native opt-in skips; final C404 completes at 12032+293 passes/two existing native opt-in skips. W136/W137 retain ordinary-versus-standalone chemical lineage and FFT/direct/fixed-normalization boundaries. No private policy, derivative/restart matrix or chemical adoption is promoted. W138/Cedar4f7aeb84 qualifies the explicit v8 100-cap ordinary coordinate route with complete source/installed/native gates. The earlier short route retains its original scope; neither cap proves convergence. W139 closes the matched native/core-only-zero/full matrix: exact zero/native output/history, passive full equivalence and common14-pair local benefit. Both line-search stops and repeated-coordinate normalization discontinuity remain separate limitations; no numerical policy is adopted. W140 reuses A72 periodic sampling on four existing ordinary ML maps at456backbone atoms, binding generation policy and own/common coordinates. All176Free-R indices are included: inspection-only, distinct from maintained metal MLHL capture; no threshold or density-guided motion. W141 qualifies Alder shared periodic-grid arithmetic in exact191-file relocated wheel and native bare imports; both reproduce3648W140own/common samples exactly. W142 closes exact Alder full6406+276 passes/no skips and421independent review checks; no new coefficient/data/phase policy or detector. W142 cold owner audit separates artifact integrity, coefficient-generation evidence, reader/frame compatibility and permitted use. Existing checkpoints/views and shared sampler are the future adapter owners; no new reader, threshold or motion policy. W144 cold ordinary/diagnostic join and owned-copy inheritance/relocation controls pass. R3 image-space interpolation differs by up to 0.28 sigma; direct Fourier agrees. Existing complete 855-atom ReferenceFrame plus shared sampler preserves 16,416 source-frame comparisons within 6.75e-14 sigma. No new objective, policy or acceptance. W145 exposes structured map stage/checkpoint/consuming ancestry through existing view resolution; standalone full/installed and focused Cedar adaptation pass. Legacy viewing stays compatible; producer coordinates, generation policy and frame equivalence remain unproven. W146 adds a read-only measured inspection snapshot over existing view/reference owners; 2061 full+234 subtests and 120 relocated installed+53 subtests pass. Genuine W138 compatibility over the installed combined owner preserves all inputs. Producer/frame evidence stays unassessed; W146 remains outside the frozen combined gate. W147 extracts exact native complex-array selection and descriptive headers:2070 full+234 subtests,129 relocated installed+53 subtests, source/installed native reads and exact19054-segment preview parity. Worker-v2 candidate binds executed helper bytes and passes2stale/change controls; it remains outside frozen combined integration. W148 reuses the exact W100 +5-degree canonical displacement with matching noiseless diffraction and fixed native refinement. Selected 204-atom RMS error falls 0.917427 to 0.029167 Å; endpoint-to-endpoint RMS is 0.026449 Å. Local covalent bonds recover, 126 sugar-volume signs survive, and Rowan independently reproduces the controls. Existing reference-link distortion remains explicit. W150 exact shared-base composition passes192 focused+37 subtests and the same source-free installed profile.348 package files, genuine two-checkpoint reads, saved W143 HTML and19054 native preview segments remain exact. Candidate bundle is ready for receiving-owner review; no active merge or new full-pass claim. W152 independent deposited5W6W opposite displacements recover from0.7641A RMS to0.05152/0.04653A; relaxed-reference drift0.01436A. Local232 bonds/363 angles,38 links,126 sugar signs and2569 common targets independently audited. Identical58 parallelity groups retain explicit source/boundary residuals; idealized matching data only. W153 deposited5W6W experimental comparison preserves5137 raw observations/507originalFree, but positive native filtering drops one work reflection. Endpoints approach relaxed control0.21485/0.14566A; reference itself moves0.52152A and Rfree rises~0.019. Geometry improves, strong B2P negative density remains. Common4629work/507Free endpoint arithmetic reuses saved F-model without refit; mixed outcome, not accepted repair. W155 prescribed complex-F contrasts at identical7554HKLs/3.06A show negative modeledP from displacement, Q excess and B mismatch separately, with zero control. Only3scatterers vary; full/group additivity≤4.82e-12 and direct/FFT≤1.18e-14. Hazel cold review passes with explicit missing original version-API capture. Common reference normalization is not ML difference-map sigma; no detector or experimental attribution. W157 reads84 archived native stages,15 minimizer records and18 scaling counts with independent Hazel review. Initial unscaled Rfree0.3207/0.3437/0.3376 becomes0.2413/0.2637/0.2624 at first bulk/scaling before XYZ; final0.2600/0.2579/0.2611. Reference hits100iterations in all5cycles. Existing report gains a verified inline stage plot; no new refinement. W159 completes one five-cycle ordinary-recipe diagnostic on the same undeformed5W6W source. Exact859atoms,2569initial bond/angle definitions,58pair/stack groups and5137effective observations/507originalFree survive;38links and126sugar signs remain. Selected drift0.591A versus0.522A; common Rwork/Rfree0.2264/0.2677 versus0.2392/0.2600. B2P B90.39→112.52 while own residual remains−8.38σ versus−8.09σ. This does not resolve the reference baseline; no opposite-start matrix or accepted repair. W160 closes the planned noiseless model-assisted three-case panel: one higher-B truth, 7554 common HKLs, 389 synthetic Free and 859 unchanged atom identities. Known position and B errors both give negative modeled-P density. Common truth-map samples are −3.11e−15/−0.804/−1.524 for zero/position/B; zero own-map normalization gives −1.624σ from numerical-scale residuals. Native formula/readback/direct-FFT checks and Hazel80-check cold review pass. No refinement, scale fitting, detector or experimental attribution. W161 cold review covers42residues,459backbone atoms at3states in4held maps (5508samples),41P versus38existingO3-P links, and unchanged4bond/angle families. A10C5-prime moves2.543A into higher ordinary density in both held sources; D2OP1 moves2.520A into lower density. All76printed weight trials fail the.015A first bond screen, requiring native fallback; final51pair distances contribute99.11% of pooled squared bond deviations, not energy/force. Reuses C395/C396 diagnosis; one posthoc A9-11 viewer added. No refinement or selector change. W162: Passive LS/ML observation reproduces all859 final atom records, both saved MTZ arrays and printed trials. Replay matches73returned states and the selected cycle5 weight7 frame. Geometry/combined local derivatives pass; data-only checks miss their prospective bound, so no finite profile runs. Both direct and FFT target/gradient restorations are exact. 194passive and120profile cold checks pass. Private diagnostic, not ordinary PostMR ancestry, a complete generic state serializer or accepted motion. Historical dihedral limit/top_out/slack are omitted; no complete six-family state claim. No tolerance retuning or new numerical-policy sweep follows. W163: Signed15degree tapered starts move205atoms2.288A RMS, up to4.79A. Default3A interpretation drops one3.836A O3P bond and4angles; that first attempt is held without fitting. Matched private4A interpretation retains38links,58complete planes, captured proxy definitions and fixed nonbonded exclusions. Five-cycle recovery reaches.758/.279A RMS; unchanged reference reproduces W152 atoms/maps exactly. Known canonical same-ASU links and noiseless matching diffraction only; no production cutoff change, automatic bond inference or symmetry-seam qualification. Original inherited torsion inventory is incomplete and explicitly qualified. W164: One matched further5cycle restart reaches.25257/.03972A RMS from the generator; no-op remains.01436A. Final Rwork/Rfree .0211/.0259 and.0086/.0100. All859atoms,38links,126sugar signs and7554raw/effective endpoint F/SIGF/Free tuples survive. Positive B2O3-prime remains1.41A away and a local angle deviates31.32degrees. Nine reconstructed managers have identical explicit443torsion/62plane policies through the existing live owner. 601cold checks;51offline view checks and6-model ChimeraX1.12 headless load pass. Five plus five cycles with a rounded-PDB restart, not uninterrupted10cycles or convergence proof. Low R values do not accept the positive distortion. Noiseless synthetic data and one target shape; reconstructed manager policy does not retroactively fill omitted optimizer fields. Browser/GPU/human review and broad repair remain open. W165 plans an enabled-by-default read-only backbone-fit check after usable refinement: high Rfree plus coherent atom-associated negative phosphate density or significant coherent positive backbone density. Separate detection, permissioned bounded trial and adoption; matched recovery/control and geometry/map/content review remain required. Planning only: no detector, operational thresholds, CLI flag, automatic displacement or checkpoint replacement. Density ambiguity/noise calibration and source/frame binding remain gates; W164 synthetic recovery is not experimental acceptance. W166 retains 38 known same-ASU backbone links, the 3.8359 A bond and four flank angles using the default-cutoff parent manager with identity-mapped displaced sites. Complete geometry/planes/torsion policies and fixed exclusions agree with independent 4 A controls; raw energy/gradient comparisons pass and parent restoration is exact. Three qualified dry-runs, seven energy calls, 77 cold checks; no refinement. Geometry-only returned-manager scope, not pre-fmodel integration, optimizer execution, automatic topology or accepted repair. Five setup refusals are preserved; native OP3 reordering requires exact atom mapping. No production source/schema/default change. W167 records user/Hazel/Rowan coordination: intact cluster rigid pose, then bounded coupled DNA opening/closing when needed, source chemical geometry/exclusions, neighboring-step/donor/width measurements and Alder A03/A07 recovery/assessment. Bridge linearity, cluster shape/local coordination/oxidation and count hypotheses remain distinct. Planning only. No dedicated width mode, cluster experiment, new target/default or combined-runtime qualification; W166 signed-bend geometry transport and FT_Hg descriptive evidence cannot qualify cluster accommodation. W168 carries parent-derived same-ASU chemistry through child-native diffraction preparation at the default 3 A cutoff. Two dry-runs pass 102 checks with exact initial Fcalc/Fmodel/masks and 7554 original tuples/389 Free; 38 links, the stretched bond/four angles and complete fixed geometry/policies remain. One admitted five-cycle native fit passes 39 cold checks and improves selected RMS 2.287991 to 0.271141 A (prior 4 A control 0.279044);RW/RF .0467/.0589. Local covalent RMS .007954 A/1.965877 deg, largest angle deviation 10.54 deg; all 126 sugar signs remain. Endpoints differ .008788 A RMS, not exact replay. One canonical signed synthetic control, private process-local wrappers, not an installed/ordinary workflow, new link inference, modified chemistry, cluster widening, symmetry-seam qualification or accepted repair. Native diffraction is constructed before chemical interpretation, so the former pre-fmodel description is superseded for this entry. Complete source topology and input-admission/execution integration remain separate gates; no further fit queued. W169 reuses audit_masked_endpoint and rebind_pair_recipe on actual W168 source/candidate bytes. Real displacement and no-op pass; eight altered children are refused by the endpoint owner, while generic rebinding keeps its intended B-change and unrestricted-coordinate scope. Source 27 / existing installed C407 29 checks pass with exact scientific readback; five owner modules are byte-identical. No missing fixed-B/Q helper was found, no product code changed and no native call or fit ran. Cold byte/mask binding only. Supplied coordinates are saved three-decimal PDB points; the 5 A audit bound is declared posthoc and does not authenticate the original unrounded proposal or prospective admission. A fresh seven-pair recipe exercises binding only and does not replace executed native restraints. Existing installed-package replay is not a fresh installation qualification. Source chemistry/site symmetry, native topology/exclusions, fresh diffraction, callback lifetime and ordinary ancestry still require supported integration. W170 completes descriptive review of six saved W164 maps, 44 backbone atoms and four coordinate states per map, with 108 checks and unchanged observations/Free. This is model-assisted synthetic evidence, not an independent validation or experimental detector calibration; see E_SAVED_RESIDUAL_MAP_REVIEW. W172 completes one private Phenix2.2.1-6174 dry-run after declared-topology admission, retaining child diffraction during parent interpretation and original observations/Free. No refinement, physical-recovery or independent child-diffraction comparison; no repeat fit queued. W173 binds a saved canonical preview to an exact selected/current checkpoint and its anchored model, observations, ordered restraints and declared phases. It rechecks inputs around strict endpoint replay and supports a context pin for a fresh dispatch read. 138 focused plus 6 subtests and the same relocated/source-free installed suite pass; 25 added cases include selection drift, input races and old-path-gone relocation. Read-only admission only; no native hook, run lock, schema migration or scientific acceptance. W174 joins W173 to Cedar-owned frozen execution requests, distinguishing parent/candidate model roles and ordered inherited/adapted/extra restraints, phases and generated round parameters.159 focused+6 subtests and relocated installed tests pass;21 new cases,223 cold checks on real C412 v3/v7 requests and17 synthetic supported-reader checks in both source and installed contexts. No native call, chemical admission, lock or ordinary motion qualification.

**Closure audit:**

- Use identical observations, Free-R flags, phase policy, refinement budget and unrelated restraints for candidate and no-repair siblings; report contacts, geometry, maps, Rwork/Rfree and tradeoffs.
- Do not reject a deformation solely on initial/early Rfree. Compare raw, optionally smoothed and post-Phenix states after a predeclared matched restraint-driven recovery window; retain non-monotonic trajectories and unsettled-budget outcomes without claiming convergence or irrecoverability.
- Preserve explicitly required sequence/connectivity/content through recovery. Apply the user-declared0.30 post-recovery project review gate to named Rwork/Rfree: worsening final Rfree requires map review even below0.30; above-threshold values trigger structural and alternative-cause diagnosis, not automatic sequence/topology changes or a universal geometry diagnosis.
- Run compatible forward and reverse shape benchmarks plus healthy/wrong-connection controls. Freeze trial policies before Rfree; density interpretation must distinguish displacement from occupancy/ADP/model errors.
- Blunt and asymmetric-orientation trials retain matched observations/Free-R and independent bends/maps; calibrate inconclusive outcomes rather than force alignment or a statistical winner.
- Final B09 geotest gate: intended altered-arm symmetry contacts survive matched refinement with defensible geometry/density and reported Rwork/Rfree; preserve junctions and healthy 21-bp arms. No visual-only closure or repeated Rfree-driven tuning.
- Before advertising the sticky-end option, pass matched enabled/disabled controls, off-path compatibility, fresh-parent/manual/Doctor intent retention and honest refusal/review outcomes for each supported mode. Plane-only and unsupported cases remain visibly distinct; restraint satisfaction alone does not prove partner assignment.

**Next action:** Join W172 complete independently declared canonical chemistry and the exact candidate to W174 child-input binding; audit moving and untouched regions against one parent. Use a supported source-bound native owner only with complete policy for that actual parent. A private diagnostic control cannot supply ordinary checkpoint ancestry; C412 modified PDU is not canonical preview authority. Keep FT and legacy soft-policy gaps at REVIEW, and coordinate the maintained native transfer hook with Cedar before any fit.
**Evidence:** [E_MR_LOCAL](#e_mr_local), [E_PUBLIC_REFERENCE](#e_public_reference), [E_NATIVE_CALLBACK](#e_native_callback), [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan), [E_PAIR_KERNEL_COMPOSITION](#e_pair_kernel_composition), [E_PAIR_MODEL_ENTRY](#e_pair_model_entry), [E_PAIR_NATIVE_INVENTORY](#e_pair_native_inventory), [E_PAIR_COVERAGE](#e_pair_coverage), [E_COMPILED_PAIR_DECLARATIONS](#e_compiled_pair_declarations), [E_NATIVE_PAIR_OBSERVER](#e_native_pair_observer), [E_MISSING_PAIR_ARITHMETIC](#e_missing_pair_arithmetic), [E_PAIR_PROVIDER_SELECTION](#e_pair_provider_selection), [E_SELECTED_PAIR_FORCES](#e_selected_pair_forces), [E_PROVIDER_NORMALIZATION](#e_provider_normalization), [E_COUNTED_CONTRIBUTION](#e_counted_contribution), [E_DUAL_NATIVE_STATE](#e_dual_native_state), [E_FROZEN_PAIR_CONTRIBUTION](#e_frozen_pair_contribution), [E_COUNTED_OWNER_LIFETIME](#e_counted_owner_lifetime), [E_FULL_SOURCE_C366](#e_full_source_c366), [E_ACTUAL_PREPARED_STATE](#e_actual_prepared_state), [E_BOUNDED_ORDINARY_LIFECYCLE](#e_bounded_ordinary_lifecycle), [E_EXACT_IMAGE_FASTPATH](#e_exact_image_fastpath), [E_SAME_FRAME_PAIR_REBIND](#e_same_frame_pair_rebind), [E_C374_JOINED_PACKAGE](#e_c374_joined_package), [E_STRONG_PREPARED_PHASE](#e_strong_prepared_phase), [E_STRONG_COMPLETE_CYCLE](#e_strong_complete_cycle), [E_CURRENT_JOINED_INSTALLATION](#e_current_joined_installation), [E_C377_MAINTAINED_PHASE](#e_c377_maintained_phase), [E_FROZEN_PHASE_AND_FAILURE](#e_frozen_phase_and_failure), [E_EXPLICIT_STICKY_REFINEMENT_PLAN](#e_explicit_sticky_refinement_plan), [E_ORDINARY_PAIR_ATTRIBUTION](#e_ordinary_pair_attribution), [E_PACKAGE_OWNED_INTEGRATION](#e_package_owned_integration), [E_DURABLE_COUNTED_ADMISSION](#e_durable_counted_admission), [E_REGISTERED_COUNTED_CONTINUATION](#e_registered_counted_continuation), [E_NATIVE_WRITTEN_MODEL_BINDING](#e_native_written_model_binding), [E_ORDINARY_COUNTED_OWNER](#e_ordinary_counted_owner), [E_PROVIDER_GEOMETRY_SUMMARIES](#e_provider_geometry_summaries), [E_COUNTED_CHEMISTRY_COEXISTENCE](#e_counted_chemistry_coexistence), [E_SEMANTIC_PAIR_GEOMETRY](#e_semantic_pair_geometry), [E_FULL_SUITE_PREREQUISITES](#e_full_suite_prerequisites), [E_FINAL_PAIR_GEOMETRY](#e_final_pair_geometry), [E_ORDINARY_PAIR_CONTINUATION](#e_ordinary_pair_continuation), [E_FULL_C391_AND_COEXISTENCE](#e_full_c391_and_coexistence), [E_SEPARATE_SCREENING_NORMALIZATION](#e_separate_screening_normalization), [E_ACTUAL_STATE_AND_LINEAGE](#e_actual_state_and_lineage), [E_LONGER_ORDINARY_CONTROL](#e_longer_ordinary_control), [E_MATCHED_CANONICAL_LONG_CONTROL](#e_matched_canonical_long_control), [E_BACKBONE_SAVED_DENSITY](#e_backbone_saved_density), [E_SHARED_GRID_SAMPLER](#e_shared_grid_sampler), [E_SHARED_GATES_MAP_BOUNDARY](#e_shared_gates_map_boundary), [E_MAP_FRAME_COMPOSITION](#e_map_frame_composition), [E_SHARED_C406_COMPATIBILITY](#e_shared_c406_compatibility), [E_MAP_SELECTION_ORIGIN](#e_map_selection_origin), [E_INSPECTION_SNAPSHOT](#e_inspection_snapshot), [E_COEFFICIENT_SELECTION_HEADERS](#e_coefficient_selection_headers), [E_MATCHING_BACKBONE_RECOVERY](#e_matching_backbone_recovery), [E_SHARED_INSPECTION_COMPOSITION](#e_shared_inspection_composition), [E_INDEPENDENT_OPPOSITE_RECOVERY](#e_independent_opposite_recovery), [E_EXPERIMENTAL_BACKBONE_TRADEOFF](#e_experimental_backbone_tradeoff), [E_DENSITY_SCATTERING_COUNTEREXAMPLES](#e_density_scattering_counterexamples), [E_POST_DEFORMATION_RECOVERY_PLAN](#e_post_deformation_recovery_plan), [E_NATIVE_RECOVERY_STAGE_HISTORY](#e_native_recovery_stage_history), [E_DISCRIMINATING_RECOVERY_PLAN](#e_discriminating_recovery_plan), [E_ORDINARY_RECOVERY_DIAGNOSTIC](#e_ordinary_recovery_diagnostic), [E_MODEL_ASSISTED_DENSITY_CONTROLS](#e_model_assisted_density_controls), [E_SAVED_RECOVERY_CONTEXT](#e_saved_recovery_context), [E_CURRENT_BACKBONE_STATE](#e_current_backbone_state), [E_LARGER_DECLARED_LINKS](#e_larger_declared_links), [E_LARGER_RECOVERY_WINDOW](#e_larger_recovery_window), [E_DEFAULT_BACKBONE_CHECK_PLAN](#e_default_backbone_check_plan), [E_PARENT_GEOMETRY_TRANSPORT](#e_parent_geometry_transport), [E_CLUSTER_ACCOMMODATION_PLAN](#e_cluster_accommodation_plan), [E_PARENT_PREPARATION_RECOVERY](#e_parent_preparation_recovery), [E_EXISTING_COORDINATE_ADMISSION](#e_existing_coordinate_admission), [E_SAVED_RESIDUAL_MAP_REVIEW](#e_saved_residual_map_review), [E_LIVE_PARENT_TOPOLOGY](#e_live_parent_topology), [E_CHECKPOINT_MOTION_BINDING](#e_checkpoint_motion_binding), [E_EXECUTION_MOTION_BINDING](#e_execution_motion_binding).
**Last audit:** 2026-11-20, Linden; Cedar interface reviewed by Rowan, [W174](https://github.com/vecchioni-lab/NASolve/commit/02411806ad7d444672803a27e6699f68b11d888d); Frozen request/input join and installed supported-reader controls; no native transfer or general repair closure.

<a id="s07"></a>
### S07 — Expose one ordinary, inspectable repair trial

Let a scientist see what was proposed, built, refined and reviewed through the existing NASolve/Pine workflow.

**Delivered:** Standalone inspect/fit/preview commands exist; ordinary checkpoint/campaign publication and GUI actions are not integrated. Verified standalone source/candidate/mate viewer exists with rotation, point inspection, contact distances and explicit unrefined/unreviewed state; it does not publish an ordinary trial. W139/W140 local science checkouts reuse exact native/full coordinates, explicit mate, planes/contacts and phosphate highlights. Headless ChimeraX1.12 and10reference/link checks pass; no map surfaces or browser-layout validation. W143 local 3D backbone-density prototype retains genuine contours and fixed-frame model/map comparison. User confirms v1 rotation and reviews v2 appearance/dropoff. Final v3 defaults to Slate, strengthens Paper/red/green contrast and remembers independent map contour levels through 6 sigma. Seven inputs and 30 prior surfaces are unchanged; 6,277 mesh checks and 16 offline contracts pass. User then approved v3 appearance and requested shared dynamic inspection throughout NASolve without opening Coot; main docs record the direction. W145 exposes structured map stage/checkpoint/consuming ancestry through existing view resolution; standalone full/installed and focused Cedar adaptation pass. Legacy viewing stays compatible; producer coordinates, generation policy and frame equivalence remain unproven. W146 adds a read-only measured inspection snapshot over existing view/reference owners; 2061 full+234 subtests and 120 relocated installed+53 subtests pass. Genuine W138 compatibility over the installed combined owner preserves all inputs. Producer/frame evidence stays unassessed; W146 remains outside the frozen combined gate. W147 extracts exact native complex-array selection and descriptive headers:2070 full+234 subtests,129 relocated installed+53 subtests, source/installed native reads and exact19054-segment preview parity. Worker-v2 candidate binds executed helper bytes and passes2stale/change controls; it remains outside frozen combined integration. W148 adds a verified four-model actual-coordinate ChimeraX checkout and visually checked scientific figure for the idealized recovery control; no alignment or scientific acceptance. W149 packages the approved two-state offline inspector with bounded display geometry, explicit missing maps and caller-supplied source/frame notes. Final full Willow2091+234 subtests and source-free installed158+53 pass. Original W143 science/shaders and source/installed output match exactly; the same renderer displays actual W148 recovery coordinates. Rowan verifies corrected camera/work bounds; browser/GPU review remains separate. W150 exact shared-base composition passes192 focused+37 subtests and the same source-free installed profile.348 package files, genuine two-checkpoint reads, saved W143 HTML and19054 native preview segments remain exact. Candidate bundle is ready for receiving-owner review; no active merge or new full-pass claim. W154 optional map_labels separates density provenance text from coordinate-state names while preserving defaults and science.30focused,2092full+234subtests,159relocatedinstalled+53subtests;93package files unchanged; exact saved-scene/source-installed HTML and17mock controls. Hazel reviews source and published payloads. Two owned scratch roots retired after archived verification:3956files/29020618bytes. W165 plans an enabled-by-default read-only backbone-fit check after usable refinement: high Rfree plus coherent atom-associated negative phosphate density or significant coherent positive backbone density. Separate detection, permissioned bounded trial and adoption; matched recovery/control and geometry/map/content review remain required. Planning only: no detector, operational thresholds, CLI flag, automatic displacement or checkpoint replacement. Density ambiguity/noise calibration and source/frame binding remain gates; W164 synthetic recovery is not experimental acceptance. W170 adds a checked PNG/SVG report and matched map/geometry table, preserving common and own-map sigma scales. The static figure was inspected directly; browser/GPU rendering is unqualified. No runtime viewer or detector change; see E_SAVED_RESIDUAL_MAP_REVIEW.

**Closure audit:**

- Create immutable children with exact model/CIF/PHIL inputs, preserve current selection, and reuse existing Coot/model-tree paths; viewing never selects or approves.
- Show actual before/after coordinates, moved/fixed sites, mates, geometry and matched refinement deltas. Test stale evidence, interruption, relocation and explicit keep/reject/use decisions.
- For final B09 review, show source, proposed and refined geotest coordinates with the intended periodic mates and per-member pass/review/failure evidence.

**Next action:** After shared receiving-owner qualification, compose W146 selection and W147 coefficient/header evidence with the W149 renderer through existing map/frame owners. Show missing/stale/unassessed evidence explicitly. Do not build another reader/history or treat display settings as scientific authority. Stage/campaign/Pine actions and ordinary repair publication remain separate; preserve Hazel residue/metal views. W165 default-check planning stays in its pipeline position: qualify source-bound noisy density detection before operational triggers; expose read-only findings before permissioned trials and separate adoption.
**Evidence:** [E_SOFTWARE](#e_software), [E_VIEW](#e_view), [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan), [E_BACKBONE_SAVED_DENSITY](#e_backbone_saved_density), [E_BACKBONE_DENSITY_PRESENTATION](#e_backbone_density_presentation), [E_MAP_SELECTION_ORIGIN](#e_map_selection_origin), [E_INSPECTION_SNAPSHOT](#e_inspection_snapshot), [E_COEFFICIENT_SELECTION_HEADERS](#e_coefficient_selection_headers), [E_MATCHING_BACKBONE_RECOVERY](#e_matching_backbone_recovery), [E_PACKAGED_DENSITY_INSPECTOR](#e_packaged_density_inspector), [E_SHARED_INSPECTION_COMPOSITION](#e_shared_inspection_composition), [E_INDEPENDENT_MAP_LABELS](#e_independent_map_labels), [E_DEFAULT_BACKBONE_CHECK_PLAN](#e_default_backbone_check_plan), [E_SAVED_RESIDUAL_MAP_REVIEW](#e_saved_residual_map_review).
**Last audit:** 2026-11-20, Linden; scope shared with Rowan and Hazel, [W170](https://github.com/vecchioni-lab/NASolve/commit/42bf701be453b20673fa88bdda64c20db5c6411e); Read-only saved-map calculation and inspected static figure, not repair/detector qualification.

<a id="s08"></a>
### S08 — Run bounded opt-in campaigns and transfer schemes

Avoid repetitive prompts while keeping inferred/borrowed connections tentative and reviewable.

**Delivered:** W165 plans an enabled-by-default read-only backbone-fit check after usable refinement: high Rfree plus coherent atom-associated negative phosphate density or significant coherent positive backbone density. Separate detection, permissioned bounded trial and adoption; matched recovery/control and geometry/map/content review remain required. Planning only: no detector, operational thresholds, CLI flag, automatic displacement or checkpoint replacement. Density ambiguity/noise calibration and source/frame binding remain gates; W164 synthetic recovery is not experimental acceptance.

**Closure audit:**

- Freeze campaign authorization once; re-resolve logical schemes in each member, preserve donor ancestry and negative evidence, honor vetoes and bound retries/resources.
- Use the existing Campaign Doctor and Campaign desk; verify mixed success/failure, deterministic resume and held-out families before claiming unattended support. No automatic global recipe promotion.
- Optional asymmetric-triangle check preserves three distinct sequence-labelled physical placements, detects duplicates and bounds multi-copy branching; GUI/export retains all matched outcomes.

**Next action:** Reuse the qualified standalone engine and campaign owners; enable broad inference only after member-level evidence is reliable. W165 default-check planning stays in its pipeline position: qualify source-bound noisy density detection before operational triggers; expose read-only findings before permissioned trials and separate adoption.
**Evidence:** [E_BLUNT_ASYM_PLAN](#e_blunt_asym_plan), [E_DEFAULT_BACKBONE_CHECK_PLAN](#e_default_backbone_check_plan).
**Last audit:** 2026-11-20, Linden; user-confirmed detection/trial/adoption distinction, [W165](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a); Pipeline intent only; no implementation or milestone closure.

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

**Delivered:** W55 adds a source-bound read-only sampled complex Fcalc observer with in-memory Cartesian ANISOU transport and explicit scope. Synthetic P43/R3/P21, wrong-tensor/coordinate controls and independent native allowed-reflection observations exist; no coordinate materializer or full scattering qualification. W62 proves exact labelled group-image permutations and inverse integer lattice shifts for each explicit representative, covers every source atom once and independently binds proposed coordinates. Special-position images remain a labelled multiset, not a unique physical-atom or occupancy proof; no materializer. W74 native synthetic diffraction and geometry targets agree with all855 anisotropic tensors transported in memory; source work/test values and derivatives are invariant across both cuts. Actual model copy/selection reveals an unsupported pair_proxies protocol. No ordinary refinement or tensor serialization is qualified. W80 binds complete Cartesian tensor transport to the same source labels/context/full permutation as coordinates and reuses the rotation in existing ANISOU previews. Installed native two-cut/three-order Fcalc and tensor controls pass; physical inventory and serialization remain separate gates. W82 replays an exactly pinned saved preview into the existing complete numerical ReferenceFrame, preserving source identity/order and unchanged context atoms; no model writer or child rebinding. W83 native synthetic special-position/partial-occupancy controls preserve the supplied labelled scattering object and fresh native multiplicity/weights in three settings and orders; source scientific validity remains separate.

**Closure audit:**

- Preserve atom-orbit inventory/multiplicity, chemistry, occupancy and displacement parameters; rotate ANISOU correctly and update logical mappings without losing or duplicating atoms.
- Independently verify before/after unrefined calculated structure factors in the same cell/setting, reciprocal round trips and relocation. Recutting must not be used to hide a physical gap.

**Next action:** First evaluate one computational native frame with explicitly bound derived views at workflow boundaries. Qualify P02 graphical review and full physical inventory/tensor serialization before any model writer. Bind each refined child afresh through verified checkpoint lineage; never silently rebase old preferences. Standalone exports and inverse-mapped edits remain separate qualification gates.
**Evidence:** [E_REPRESENTATIVE_SCATTERING](#e_representative_scattering), [E_ORBIT_PERMUTATIONS](#e_orbit_permutations), [E_JOINT_FRAME_TARGET](#e_joint_frame_target), [E_BOUND_TENSOR_TRANSPORT](#e_bound_tensor_transport), [E_SAVED_FRAME_BINDING](#e_saved_frame_binding), [E_SPECIAL_POSITION_SCATTERING](#e_special_position_scattering).
**Last audit:** 2026-11-15, Linden, [W83](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5); Native fresh-table special-position/mixed-ADP preservation; no serialized writer or source scientific acceptance.

<a id="p04"></a>
### P04 — Qualify seam chemistry and native interpretation

Make a representation seam remain a continuous backbone where chemistry says it is continuous.

**Delivered:** W63 reuses authenticated Cedar source-native links to expose existing bonds crossing the proposed ASU, exact image geometry, missing declared-graph coverage and source P/OP1/OP2. Optional viewer text is read-only; no chemistry or model change. W66 projects declared directed backbone continuation, representation/chemical/unknown boundaries and existing phosphate inventory from replayed packets. Unresolved partners retain P/OP1/OP2 intent; OP3 conflicts are scoped to continuation, with terminal phosphate consent separate. Exact route-image transport, optional view and preference context are read-only; no new edge or native enforcement. W67 resolves explicitly declared directed representation-boundary partners through existing graph and schema-2 proposal owners. Strict endpoint/capacity/intent checks, exact images and winding survive replay; no partner inference, atom editing or native enforcement. W68 observes eight existing source-native crossing angles per explicit cut: exact image energies, rotated gradients and native energies path agree. Live source symmetry/slack are verified; native proxy pickle loses sym_ops. This narrows lifecycle qualification without enabling restraints. A follow-up native angular manager omits cell context before serialization; subset/reindexing retains images, generic deepcopy does not. W71 freezes complete live angle metadata and rebuilds private image-bearing proxies with explicit unit-cell evaluation. JSON/deepcopy/pickle and a fresh native interpreter preserve two complete 1467-angle cut evaluations. Source-manager behavior and complete seam chemistry remain unchanged. W72 observes complete source-frame objective transport, changed-neighbor cache rebuilds and mmtbx normalization/shared-gradient-buffer agreement. Identity selection drops the local facade mapping and remains a negative control; no runtime activation. W73 adds a complete immutable source/image binding and explicit full reindexing.36 local mmtbx entry controls preserve geometry through identity/reverse/cyclic orders; partial selection and changed cell refuse. This is a numerical backend component, not an installed native selection hook. W74 native synthetic diffraction and geometry targets agree with all855 anisotropic tensors transported in memory; source work/test values and derivatives are invariant across both cuts. Actual model copy/selection reveals an unsupported pair_proxies protocol. No ordinary refinement or tensor serialization is qualified. W75 observes the stock source-only dry-run and coordinate-cycle consumer path; geometry, weight regularization and reports bypass a model-energy-only hook. Matched profiling controls agree; complete frame-aware native integration remains open. W76 adds source-bound representative native contact reports preserving exact image operations, directed membership and native multiplicity; native pair-table/report consumers remain unqualified. W77 binds representative contact reports through the immutable native-preview context, preserving old link/view defaults and proving source/cell/proposed-coordinate correspondence; native copy/refinement integration remains open. W78 distinguishes exact source identity/model copies from generic geometry deepcopy that drops nonbonded policy despite retaining contact rows. Isolated native parameter-object control reproduces table loss; complete live policy/copy ownership stays unqualified. W79 observes actual native outlier-query frame mixing despite correct scalar geometry; explicit local callback remapping restores source outlier identities. Source-frame geo records compare semantically, with raw presentation differences preserved.

**Closure audit:**

- Keep true termini/nicks distinct from ASU seams; preserve continuation phosphates and forbid automatic terminal OP3 chemistry caused only by serialization.
- Qualify native bonds, angles, planes and nonbonded behavior at the seam. Separate any required coordinate repair into a new S-track child; successful recutting itself cannot deform the crystal.
- Retain declared periodic P/OP1/OP2 chemistry independently of partner resolution; emit no symmetry bond alone while complete phosphate-angle enforcement is unqualified.

**Next action:** With Cedar, authenticate complete live source policy including nonbonded and exclusion tables. For pure recuts, first keep the entire native process in one computational frame and derive bound views at workflow boundaries. This does not repair physical gaps or missing links. Require checked inverse mapping for re-entered edits and fresh qualification for changed identity/intent. If an in-engine facade is actually needed, retain full copy, pair-table, outlier/report, weighting and native source/representative controls. Preserve P02/P03; never activate a symmetry bond alone.
**Evidence:** [E_PINE_TEST_BANK](#e_pine_test_bank), [E_NATIVE_REPRESENTATION_SEAMS](#e_native_representation_seams), [E_BACKBONE_INTENT](#e_backbone_intent), [E_EXPLICIT_CONTINUATIONS](#e_explicit_continuations), [E_SEAM_ANGLE_LIFECYCLE](#e_seam_angle_lifecycle), [E_ANGLE_SNAPSHOT](#e_angle_snapshot), [E_REFERENCE_FRAME_GEOMETRY](#e_reference_frame_geometry), [E_REFERENCE_FRAME_BINDING](#e_reference_frame_binding), [E_JOINT_FRAME_TARGET](#e_joint_frame_target), [E_NATIVE_CONSUMER_PROTOCOL](#e_native_consumer_protocol), [E_REPRESENTATIVE_PACKING](#e_representative_packing), [E_PREVIEW_PACKING_BINDING](#e_preview_packing_binding), [E_NATIVE_SOURCE_COPY](#e_native_source_copy), [E_NATIVE_REPORT_FRAMES](#e_native_report_frames), [E_COMBINED_FULL_AUDIT](#e_combined_full_audit), [E_C325_INSTALLED_COMPOSITION](#e_c325_installed_composition).
**Last audit:** 2026-11-15, Linden, [W84](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5); Focused installed composition verifies C325 historical-reader repair; original full failures retained, seam/runtime qualification unchanged.

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
| B06 — Density-guided and nonuniform/strand-specific relaxation | PLANNED_EXTENSION | S04, S06 | After qualified geometric placement and matched refinement, add a read-only model/map-bound detector of sustained negative difference-density patches along sugar-phosphate backbones. Calibrate with Simon against healthy/noisy and displaced controls across resolution, occupancy/ADP and map-processing conditions before proposing motion. Then consider nonuniform/strand-specific density-guided fitting; a red voxel or universal sigma cutoff is not a displacement instruction. Also qualify bend center/width and localized, distributed or distal curvature variants using support before and after refinement. Construct 4T28/PDB 8SJW at 7.64 A is a user-proposed localized B:11 bend control; entry identity verified, residue/density interpretation pending. Predeclare search budgets and retain all attempts; avoid repeated Rfree-guided tuning. Reuse Hazel's maintained nasolve.metal.map_diagnostics and saved-coefficient provenance/periodic-sampling checks through a shared owner; keep own-endpoint versus common-reference sampling distinct. Hg sigma/radius and occupancy/scattering assumptions are not phosphate calibration; no new map reader or density decision implementation is authorized by this reuse note. Before density-guided search, bind coefficient generation including work/free selection, missing-data fill, filtering/isotropization/sharpening. Ordinary display maps are not implicitly work-only; exact coefficient membership does not alone establish use of observed amplitudes. W153 adds an experimental counterexample to geometry-only acceptance: no-op/reference drift, more ideal planes and persistent B2P negative density with fixed B/occupancy. Preserve original raw observations/Free and explicitly record adaptive effective-work filtering. Common endpoint R arithmetic does not retroactively equalize trajectories. W155 now records prescribed known-phase displacement/Q/B scattering counterexamples, not an experimental/model-assisted/noisy attribution matrix. Its original version-API capture is unavailable and explicitly retained. Hazel's matched global-scale and own/common-position controls remain separate precedents. W160 adds the declared noiseless model-assisted zero/position/B panel and near-zero normalization caveat; noisy/experimental attribution and detector calibration remain open. |
| B07 — 9PGR designed blunt single-base stacking | PLANNED_EXTENSION | S02, S04, S05, S06 | Reconstruct labelled contact frames/operators and signed-twist convention; qualify density-supported single-pair contact and healthy/wrong-mate controls without coaxial or covalent closure. Local SI table inspected; no fit/refinement executed. |
| B08 — 7U3O and three user-supplied asymmetric-triangle datasets | READ_ONLY_INVENTORY_PLANNED | S04, S06, S07, S08 | Bind chosen examples, sequences, motif/copy mapping, molecular pivot/axis and common Free-R data. User confirms available three examples suffice; third local AlphaFold source is optional follow-up. Compare independently bent 0/120/240-degree placed siblings strictly after PostMR and first refinement, with no MR rerun, fixed data and per-model maps. Retain ambiguous/duplicate/failed states; blinded known-answer and degraded-resolution controls before unresolved benchmarks. |
| B09 — Final geotest altered-arm alignment: X11_18 (P4_3), X11_22 and frozen related members | READ_ONLY_INVENTORY_BOUND_REPAIR_PENDING | S04, S05, S06, S07 | Nine historical members inventoried locally with 204 recorded hash/size comparisons passing. Named seeds bound: X11_18 dataset2/P4_3/refine-002 (REVIEW, current checkpoint remains postmr) and X11_22/refine-001. X11_18 input MTZ is labelled P4_1; preserve exact saved model/data setting lineage before repair. Raw Free-R columns are bound, not a complete workflow audit. Remaining panel selection, independent sequence/arm/symmetry-partner mapping, coupled geometry and matched refinement/human review remain open. No new solve or adoption; see docs/topostitch.md#final-geotest-alignment-gate-planned. |
| B10 — Explicit opt-in sticky-end enforcement, independent of automatic placement | PLANNED_NOT_IMPLEMENTED | S05, S06 | Reuse registered inputs where appropriate: declared canonical 8D93 contacts first, independent 5W6W/DOHU next, then 7R96 user-proposed mismatches after exact sequence/contact inventory and separate plane-only qualification. Include healthy/displaced, wrong partner/image/register, missing-atom and duplicate-native controls; compare matched enabled/disabled refinement, geometry/packing and original data/Free-R where available. No new inputs, execution or validated geometry result from this plan. W37 first-guessed5W6W identity-image pairs are numerical fixtures, not reviewed healthy sticky ends; retain their175.96degree-angle/large-step DERIVATIVE_REVIEW and audit exact contact/image identity before reuse. Local W-catalogue identity/terminal inventory is now recorded through the existing sequence-family owner; actual C_G and noPO4 variants differ from seq_base and have distinct D1 phosphate content. These are derived search models, not automatically healthy deposited controls. No inference, mutation, native fit or geometry qualification; bind exact actual inventory/terminal intent before use. |

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
**Limit:** Read-only captured-coordinate report, not native pair-table reconstruction, new neighbors/exclusions, physical identity or refinement support. W77 final full1756 +229 includes the finite-output guard; generated reports stay local and Cedar owns authentication.

<a id="e_preview_packing_binding"></a>
### E_PREVIEW_PACKING_BINDING — saved_preview_authenticated_native_contact_binding

[Evidence contract](topostitch-periodic.md#w77--bind-contact-reports-to-immutable-saved-previews) at [W77](https://github.com/vecchioni-lab/NASolve/commit/78ecdc54c28775364e1e9cf3641bdd208f2ffe3c).
Shared immutable native-preview context preserves old link observations and binds complete native order, cell, source/proposed points and receipt bytes to W76 packing.7 new regressions; focused167; full1756 +229; installed/relocated571. Both saved cuts exactly reproduce W76 packing reports, preserving8305 rows each; proposed-coordinate error<=1.43e-14 Angstrom.
**Limit:** Read-only saved evidence, not fresh native execution, native table reconstruction, model copying, live neighbor policy, output serialization or refinement. Existing CLI/view defaults and packet formats unchanged; source/capture APIs remain Cedar-owned; science local.

<a id="e_native_source_copy"></a>
### E_NATIVE_SOURCE_COPY — source_native_copy_policy_and_installed_composition_diagnostic

[Evidence contract](topostitch-periodic.md#w78--distinguish-source-manager-copying-from-policy-preservation) at [W78](https://github.com/vecchioni-lab/NASolve/commit/78ecdc54c28775364e1e9cf3641bdd208f2ffe3c).
Phenix2.2.1-6174 source identity geometry/model selection and model.deep_copy preserve target/gradients at three coordinate controls. Generic geometry deepcopy retains8305 rows but loses1115.631 nonbonded residual; isolated parameter-object control reproduces dropped tables with scalar preservation. Current Cedar794e0d7b installed virtual composition passes782 +16, six helps and exact old/new plus W77 packing replay.
**Limit:** Source-only diagnostics; inspected proxy inventory is not a complete policy fingerprint. Successful identity selection shares nonbonded parameters. No recut copy/ordinary refinement, SDK/runtime change or complete exclusion qualification. Initial failure preserved; science local. Seven doc conflicts, no actual merge/full combined suite. W77 runtime full1756 +229 and installed571 unchanged.

<a id="e_native_report_frames"></a>
### E_NATIVE_REPORT_FRAMES — native_statistics_and_source_geo_frame_diagnostic

[Evidence contract](topostitch-periodic.md#w79--keep-outlier-queries-in-the-same-frame-as-the-energy) at [W79](https://github.com/vecchioni-lab/NASolve/commit/78ecdc54c28775364e1e9cf3641bdd208f2ffe3c).
Actual Phenix2.2.1-6174 statistics retain scalar geometry but lose/substitute torsion-outlier quartets under an energy-only representative facade. Explicit callback coordinate remapping restores all measured source lists and scalar statistics within3.55e-11 across two cuts/two coordinate controls. Source-frame geo semantic comparisons agree after explicit +/-180 ideal display and directed-record ordering treatment.
**Limit:** Local diagnostic only; no runtime hook, arbitrary reorder, representative export or ordinary refinement. Raw geo bytes differ and cached contact counts are not forced-rebuild evidence. Optional-Gemmi setup failure retained. Existing W77/W78 full/install/composition validation unchanged; science local.

<a id="e_bound_tensor_transport"></a>
### E_BOUND_TENSOR_TRANSPORT — bound_Cartesian_tensor_transport_and_installed_native_scattering

[Evidence contract](topostitch-periodic.md#w80--bind-cartesian-displacement-tensors-to-the-coordinate-frame) at [W80](https://github.com/vecchioni-lab/NASolve/commit/cc9fe96d456f9c3fbbf819e9afe7541f03aec361).
Shared Cartesian R U R^T and complete ReferenceFrame forward/inverse tensor transport retain labels/context/full permutation; existing preview ANISOU writer reuses rotation.13 fail-before regressions; focused184; full1769 +229; installed/relocated668. Installed Phenix2.2.1-6174:855 tensors,2cuts×3orders,1008 Fcalc values maxerror4.43e-11; independent native fractional tensor comparison and omitted-rotation negative control pass.
**Limit:** Arithmetic and complete in-memory diagnostic only; caller owns fractional conversion, ADP presence/flags and physical validation. No new writer/schema, ADP optimization, experimental data, model materialization or ordinary recut refinement. Scientific evidence local; P03/P04 remain partial.

<a id="e_combined_full_audit"></a>
### E_COMBINED_FULL_AUDIT — installed_combined_audit_with_explicit_limitations

[Evidence contract](topostitch-periodic.md#w81--audit-the-combined-installation-and-narrow-the-pine-boundary) at [W81](https://github.com/vecchioni-lab/NASolve/commit/cc9fe96d456f9c3fbbf819e9afe7541f03aec361).
Frozen Willow2a76967c + Cedar dc82aee1 full installed virtual audit:4failed,11109passed+284subtests. Two source-test assumptions and two default historical-reader resource failures diagnosed. Affected source modules90+20pass; explicit historical runtime-source installed C62/C63 replay passes with originals/processes blocked. Exact old/new graph/native-link/packing replay and six helps pass. Eight separate installed Phenix2.2.1-6174 cross-setting Fcalc/tensor cases pass.
**Limit:** Default installed canonical-frame resource gap remains Cedar-owned. Original full failures retained; no full combined rerun or green full claim. C323/W82 excluded from pin; seven documentation conflicts and no actual merge. No native workflow activation, writer, physical repair or recut-refinement qualification. Later C325/W84 repairs and verifies the default reader at a new pin; this original full result remains unchanged.

<a id="e_saved_frame_binding"></a>
### E_SAVED_FRAME_BINDING — replayed_preview_to_complete_numerical_reference_frame

[Evidence contract](topostitch-periodic.md#w82--bind-numerical-frames-to-immutable-saved-previews) at [W82](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5).
Exactly pinned immutable preview compiles complete identity/image frame including unchanged context.12 fail-before regressions; focused99; full1781 +229; installed/relocated680; six helps/lean imports/Python3.10 syntax. Both855-atom old/new packets reproduce exactly in three orders with original paths blocked.
**Limit:** Receipt context is preview identity, not native policy/checkpoint lineage. No writer, changed-child rebind, edit import, chemistry/refinement activation or new packet schema. Physical/scattering and P02/P03/P04 gates remain. W81 combined full build predates this runtime and retains the installed historical-reader limitation.

<a id="e_special_position_scattering"></a>
### E_SPECIAL_POSITION_SCATTERING — native_fresh_symmetry_table_scattering_preservation

[Evidence contract](topostitch-periodic.md#w83--preserve-the-labelled-scattering-object-at-special-positions) at [W83](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5).
Installed Phenix2.2.1-6174 complete synthetic C2/R3:H/P4 diagnostic:five mixed-ADP/partial/zero-occupancy scatterers, coincident separately labelled special-position atoms, three orders. Nine cases preserve native multiplicity/weights/flags and Fcalc<=7.62e-13 with freshly reconstructed target symmetry tables. Dropped-label, omitted-tensor and overwritten-occupancy controls fail strongly; source unchanged.
**Limit:** Full-precision in-memory supplied-scattering-object preservation only; no source physical/chemical validity, unique molecular identity, classification-tolerance boundary, serialization, refinement or writer. Source runtime/schema unchanged; W82full/install baseline. P02/P03/P04 remain partial; science stays local.

<a id="e_c325_installed_composition"></a>
### E_C325_INSTALLED_COMPOSITION — focused_installed_virtual_composition_after_C325

[Evidence contract](topostitch-periodic.md#w84--verify-the-repaired-installed-composition) at [W84](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5).
Willow29723067dff6e3ad12bac5dd15e8a51e46105091 plus Cedar cad829a60a6ecc97643e220d4f5d16496bca39e6, resolved virtual tree b61a58636501a86b6aef4d969d5baf9f74eb9ce5: 873 tests and16 subtests pass in a fresh installation with original source path absent. Exactly28 TopoStitch modules plus seven shared/Cedar modules, six entrypoint helps, saved old/new graph/native-link/packing/frame replay and both packaged resources checked. C325 repairs default historical readers.
**Limit:** No full combined rerun or native execution; original W81 failures remain recorded. Zero source conflicts, seven documentation conflicts and one package-data conflict resolved only in the virtual tree by retaining both HTML and replay PDB resources. No actual branch merge, runtime/schema changes, source writer or refinement qualification.

<a id="e_coarse_native_derivatives"></a>
### E_COARSE_NATIVE_DERIVATIVES — local_coarse_motion_native_derivatives_and_forced_contact_rebuild

[Evidence contract](topostitch-periodic.md#w85--check-coarse-motion-derivatives-against-native-geometry) at [W85](https://github.com/vecchioni-lab/NASolve/commit/e570d15f308ec46a0b2bc6f62c43c3346e17abb5).
Complete Phenix2.2.1-6174 local diagnostic reuses authenticated W38/W41 source,204-atom mask,14-pair recipe and existing NativeMaskedObjective.60 independent motion controls pass. Five declared six-parameter controls, two finite-difference steps, cached and forced-reset evaluations:270 native objective calls, max derivative discrepancy9.98e-7 below predeclared1e-3. Cached/rebuilt energy and Cartesian gradients match exactly; changed directed buffered rows have zero repulsion residual and common multiplicities are unchanged.
**Limit:** Local probe only, no installed coarse optimizer, new runtime/schema, model output, density or refinement. Maximum tested physical displacement0.064 Angstrom; fixed taper and one window do not qualify large bending/window expansion. A lower total repulsion still worsens48 individual directed overlaps in one control. The complete live nonbonded/exclusion guard remains open, separate from CedarQ06 refinement chemistry; source chemistry and original failed/capped optimizers remain unaccepted.

<a id="e_bounded_native_motion"></a>
### E_BOUNDED_NATIVE_MOTION — installed_bounded_tapered_motion_and_native_chain_rule

[Evidence contract](topostitch-periodic.md#w86--expose-bounded-tapered-motion-through-the-existing-native-objective) at [W86](https://github.com/vecchioni-lab/NASolve/commit/82ac2b3f695fe81bdb09b4347d2f6e6b0adfd782).
Immutable TaperedMotion reuses preview rotation and exact CoordinateMask bounds/order; NativeMaskedObjective.evaluate_motion preserves native/pair/tether target and Cartesian gradient, adding six physical-unit derivatives.21 fail-before controls; focused156; full1802+229; installed/relocated712; six helps, lean imports, Python3.10 syntax and exact saved replay. Complete Phenix2.2.1-6174 installed replay: five controls,270 calls, two derivative steps and forced contact rebuilds pass; W85 targets/gradients reproduce within9.1e-13/5.8e-13.
**Limit:** No optimizer/CLI/packet schema/model writer/tensor/scattering changes or physical acceptance. Caller owns weight/pivot provenance; current 3N optimizer protocol is unchanged. Full live nonbonded/exclusion policy remains Cedar-owned. Sandbox process-list failures and a host reviewer import correction are retained; no native rerun, actual branch merge or full combined-suite claim.

<a id="e_matched_coarse_trials"></a>
### E_MATCHED_COARSE_TRIALS — complete_native_matched_coarse_failure_observations

[Evidence contract](topostitch-periodic.md#w87--compare-matched-six-variable-placements-without-promoting-failures) at [W87](https://github.com/vecchioni-lab/NASolve/commit/82ac2b3f695fe81bdb09b4347d2f6e6b0adfd782).
Phenix2.2.1-6174 paired/core-only trials both FAILED rounding after11/10 accepted steps; exact callback replay and full/rounded Cartesian derivative checks pass. Common14-recipe observers complete: selected-pair target -7.122/-5.318, nonbonded1077.722→1055.746/1059.585, retained pairs invariant, motions .0538/.0444 Angstrom. Individual packing/AT component regressions retained with severity, not count-based rejection.
**Limit:** No success endpoint, candidate, refinement, scientific acceptance, runtime/schema changes or new full-suite run. Host/native arithmetic mismatch preserved and resolved through exact same-interpreter replay; the live-policy guard remains open, separate from CedarQ06 refinement chemistry. Geometry-only observations do not close S04/S05.

<a id="e_saved_bend_motion"></a>
### E_SAVED_BEND_MOTION — source_bound_saved_preview_motion

[Evidence contract](topostitch-periodic.md#w88--compile-source-bound-motions-from-saved-bend-previews) at [W88](https://github.com/vecchioni-lab/NASolve/commit/109ee1f8e6a61f466b1c4d2659ed0c80f2c25e5f).
Pinned preview replay compiles exact source-order mask, registered pair weights and pivot; full-precision bound/exact coordinate fields/input snapshots checked. Native view rejects changed source bytes.19 fail-before,111 focused,1821 full+229 subtests,731 installed/relocated,6 helps,lean imports,Python3.10 syntax and public saved motion/frame replay pass.
**Limit:** No schema migration, optimizer, writer, tensor transport or native policy change. Existing numerical callers remain supported. Conservatively rejects unrounded bound or exact-serialization mismatch; other parameters need fresh audits. No native rerun or actual branch merge; W87 remains FAILED.

<a id="e_coarse_resolution"></a>
### E_COARSE_RESOLUTION — native_read_only_coarse_resolution_observation

[Evidence contract](topostitch-periodic.md#w89--separate-coarse-step-resolution-from-atomic-cleanup) at [W89](https://github.com/vecchioni-lab/NASolve/commit/82ac2b3f695fe81bdb09b4347d2f6e6b0adfd782).
Two240-call Phenix2.2.1-6174 probes exactly replay W87 points/gradients and rebuilt contexts. Stable positive local six-variable Hessians; estimated additional motions8.05e-9/2.70e-8 Angstrom and decreases .52/3.80 scoreULPs. Actual sampled scores rise4/6ULPs while coarse gradients drop~1e-10.
**Limit:** OriginalW86/C325 pins, no optimizer/restart/relaxed tolerance/new candidate/current-combined qualification. Supports numerical-resolution explanation, not convergence or atomic geometry. W87 remains FAILED; no new source tests for evidence-only update.

<a id="e_atomic_diagnostic_start"></a>
### E_ATOMIC_DIAGNOSTIC_START — explicit_original_source_atomic_initialization

[Evidence contract](topostitch-periodic.md#w90--add-explicit-diagnostic-starts-to-the-existing-atomic-trial) at [W90](https://github.com/vecchioni-lab/NASolve/commit/5965d8588984c6991f587bdaec049639264d03e4).
Existing atomic trial accepts frozen explicit mask displacements, records diagnostic initialization and audits that start without rebasing source/tether or modifying stopping/failure policy. Remaining-budget preflight now includes prior calls.14 fail-before,75 focused,1835 full+229 subtests,745 installed/relocated,6 helps,lean import,syntax and saved replay pass.
**Limit:** Additive low-level API and optional initialization observation only; no CLI/candidate/writer/campaign promotion or native-policy change. Caller authenticates parent/failure provenance. W91 matched native validation pending; no actual branch merge.

<a id="e_matched_atomic_starts"></a>
### E_MATCHED_ATOMIC_STARTS — complete_native_matched_atomic_initialization

[Evidence contract](topostitch-periodic.md#w91--compare-cold-and-explicitly-coarse-seeded-atomic-cleanup) at [W91](https://github.com/vecchioni-lab/NASolve/commit/5965d8588984c6991f587bdaec049639264d03e4).
Two complete Phenix2.2.1-6174 trials use installedW90 and pinnedC325 owners. Cold/seeded FAILED rounding at358/363 accepted steps,390/401 optimizercalls; both failed-point full/rounded derivatives pass. Common-recipe observers complete. Max endpoint difference2.65e-7 Angstrom; all855 rounded triplets identical; no demonstrated seed benefit. Active bond/angle nominal>=3 counts9/14→0, boundary angle1→0; packing severity retained.
**Limit:** No parent failure promotion, numerical/scientific acceptance, model/checkpoint/refinement or default change. One small coarse polish is not large-shape qualification. Live-policy mutation guard is distinct from CedarQ06 chemistry survival. Evidence-only update; W90 software checks retained.

<a id="e_live_nonbonded_contract"></a>
### E_LIVE_NONBONDED_CONTRACT — proposed_shared_live_native_policy_contract

[Evidence contract](topostitch-periodic.md#w92--shared-live-nonbonded-policy-contract-qualification-pending) at [W92](https://github.com/vecchioni-lab/NASolve/commit/5965d8588984c6991f587bdaec049639264d03e4).
Cedar owner/Willow consumer contract records full supported parameter/assignment/exclusion/symmetry and invocation scope, cache-state separation, unchanged defaults and mandatory equal-energy hidden-mutation controls.
**Limit:** Historical W92 contract/C330 preparation; W96 direct and W97 explicit captured-diagnostic consumers now qualify with C331. Automatic adoption and scientific/chemistry gates remain open; Q06 separate.

<a id="e_blunt_asym_plan"></a>
### E_BLUNT_ASYM_PLAN — requirements_and_read_only_inventory

[Evidence contract](topostitch.md#designed-blunt-contacts-and-single-base-stacking-w93-planned) at [W93](https://github.com/vecchioni-lab/NASolve/commit/5965d8588984c6991f587bdaec049639264d03e4).
Paper/local SI inspected; 9PGR single-base stacking and 7U3O molecular-axis orientation controls distinguished from covalent closure and representative recuts. Three private dataset triplets inventoried locally, two top-level model sources present. Three matched sequence-labelled orientation siblings and uncertain outcomes specified in campaign-model-roadmap.md.
**Limit:** Design only: no CLI, runtime schema, guard, benchmark solve, operator rederivation or scientific adoption. Copy/motif and selected sequence mapping must be bound before execution; user confirms missing third local AlphaFold model is not a gate. Local SI not verified identical to publisher supplement; private paths/hashes/inputs excluded from Git.

<a id="e_pivot_rotation"></a>
### E_PIVOT_ROTATION — software_regression_and_installation

[Evidence contract](topostitch-preview.md#w94-validation--2026-11-16) at [W94](https://github.com/vecchioni-lab/NASolve/commit/eb8e5d6ed55a75ce33863c1fc4e6f37a95d23465).
Existing CartesianImage gains checked R(x-p)+p+t construction, reused for preview ANISOU without changing centered coordinate rounding. Nine fail-before cases; 139 focused, 1844 full plus 229 subtests, 139 installed/relocated tests, six CLI helps and pip check pass. Source/installed module bytes match; Python 3.10 syntax passes. PostMR/first-refinement-only orientation plan corrected, no re-MR; missing third local AlphaFold model is optional follow-up.
**Limit:** Numerical transform only; no axis inference, placement authorization, new schema, three-sibling campaign implementation, native Phenix/Coot execution or scientific acceptance. First install harness omitted relative-import test helpers; complete relocated test package passes against the unchanged fresh wheel. Shared Cedar live-policy consumer remains gated; no Cedar edits or combined-build qualification. Generated test/build artifacts stay local.

<a id="e_guard_integration_prep"></a>
### E_GUARD_INTEGRATION_PREP — implementation_boundary_review

[Evidence contract](topostitch-periodic.md#w95--prepare-the-qualified-guard-consumer) at [W95](https://github.com/vecchioni-lab/NASolve/commit/eb8e5d6ed55a75ce33863c1fc4e6f37a95d23465).
Reviewed actual NativeMaskedObjective and Cedar correction/static-signature paths. Plan checks before pair_proxies can rebuild, same flags/options on the real energy call, immutable primitive baseline, preserved failures, opt-in provenance and installed profile/resource closure. Direct consumer and later captured-worker adoption are separate acceptance steps.
**Limit:** Documentation only. C331 implementation is under Rowan qualification; uncommitted source/profile are not pinned dependencies. No Willow guard, new runtime/schema, native execution, scientific closure or automatic campaign adoption. W94 full/install validation remains current.

<a id="e_live_policy_consumer"></a>
### E_LIVE_POLICY_CONSUMER — software_and_bounded_native_qualification

[Evidence contract](topostitch-periodic.md#w96--optional-direct-live-policy-consumer) at [W96](https://github.com/vecchioni-lab/NASolve/commit/c6549408137f83b431f8519480702656bf9183c6).
Optional NativeMaskedObjective owner/expected-snapshot binding checks construction/static/energy boundaries, freezes caller data and records opt-in provenance. Nine fail-before cases; 84 focused, 1853 full plus 229 subtests, 84 fresh-wheel tests and six CLI helps pass. Eight complete Phenix 2.2.1-6174 source and installed-composition checks pass, including real construction, exact guarded/unguarded native values/gradients across movement/reset, full six-variable derivatives and hidden/mid-call mutation refusals.
**Limit:** Direct explicit consumer only. Synthetic three-atom native manager with zero additive-pair control; no canonical DNA/packing/physical-gap/diffraction acceptance. Captured worker, CLI and campaign defaults unchanged. No Cedar merge or full merged-branch regression. First installed-native harness mixed Python 3.12 dependencies with Phenix 3.11 and failed; corrected pure-Python wheel staging passes with native dependencies. Sequential checks do not prove concurrent/transient mutation protection.

<a id="e_guarded_captured_worker"></a>
### E_GUARDED_CAPTURED_WORKER — worker_software_native_and_installed_relocation_qualification

[Evidence contract](topostitch-periodic.md#w97--explicit-guarded-captured-diagnostics) at [W97](https://github.com/vecchioni-lab/NASolve/commit/1d6008791c730cc576d21fb7f7872f5c1eb36466).
Explicit boolean guard_live_policy on run_captured_objective stages C331 guard/profile with source hashes, freezes model/capture-bound fresh baseline only after reconstructed-context comparison, and verifies child identity/digest/binding before accepting success. Legacy worker and default metadata unchanged. Ten fail-before cases;84 focused,1864 full+229 subtests,84 fresh-wheel tests,six CLI helps,pip check pass. Complete Phenix 2.2.1-6174 capture and guarded/unguarded read-only workers on855 atoms/204 movable/14 pair recipes match exactly. Installed guarded worker after original input/capture paths are removed reproduces values,gradients,binding and anchored checksum references.
**Limit:** Explicit installed/developer Cedar route on the pinned native profile only, not a full merged build or universal portability. Fresh baseline does not authenticate unknown historical policy fields. No CLI/campaign-default activation, optimization, edited model, refinement or scientific acceptance. Long guarded trajectories, endpoint combinations and displaced/bent DNA/density qualification remain open. Scientific payload stays local.

<a id="e_captured_diagnostic_start"></a>
### E_CAPTURED_DIAGNOSTIC_START — captured_explicit_start_interface_and_displaced_recovery_diagnostic

[Evidence contract](topostitch-periodic.md#w98--declared-starts-through-captured-native-trials) at [W98](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Twelve fail-before cases; 96 focused, 1,876 full plus 229 subtests, 96 installed tests, six CLI help checks, pip check and Python 3.10 syntax pass. The frozen 3N start matches complete mask/radial bounds before allocation and reaches the unchanged W90 trial. Complete installed Phenix 2.2.1-6174 guarded controls with 41 atoms/123 variables at 25 and 300 iterations pass initial/full/rounded derivatives and baseline/source checks; all retain NOT_CONVERGED_LIMIT. Extended RMS from reference is 0.065399/0.064062 Angstrom with/without pair forces, from 1.150583. Three guarded endpoint observers pass consistency; the changing core pair penalty goes from 14.9391 to 10.6100/21.1327, but individual contacts, packing and torsions retain trade-offs and environment REVIEW. The full-window attempt was interrupted without a verdict; its original OWNERSHIP_ERROR is retained and process-group absence was independently verified.
**Limit:** The original 0.1 Angstrom tether biases toward the known source. No selected sticky-end change, full-window/broad recovery, convergence, density/refinement, Coot check, adoption or merged-build claim. PDB rounding alters stationarity despite passing derivatives. Scientific data remain local; the archive is forensic, not autonomous portable execution. Profile instrumentation and observed approximately 0.28 s/evaluation wall-rate are distinct; no guard optimization, new CLI/dependency or schema version.

<a id="e_full_window_native_control"></a>
### E_FULL_WINDOW_NATIVE_CONTROL — complete_full_window_native_control_and_endpoint_audit

[Evidence contract](topostitch-periodic.md#w99--complete-full-window-native-bend-controls) at [W99](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Both predeclared installed Phenix 2.2.1-6174 204-atom/612-variable controls pass initial/full/rounded derivatives and guards; initial components/points match. Both remain NOT_CONVERGED_LIMIT at 300 iterations, with 7661/7663 total evaluations. RMS from original source 0.074182/0.058718 A from 0.917496. Three common guarded endpoint observers pass; scalar affected screens improve, both selected contacts and core total improve with pair forces, but individual packing/torsion regressions persist.
**Limit:** Original-source 0.1 A tether favors known-reference recovery. PDB rounding changes stationarity; no convergence, broad or blind recovery, chemical acceptance, end closure, density/R statistics, adoption or merged-build qualification.

<a id="e_c338_installed_composition"></a>
### E_C338_INSTALLED_COMPOSITION — focused_installed_virtual_composition_with_C338

[Evidence contract](topostitch-periodic.md#installed-c338-compatibility-during-w100) at [W100](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Exact Willow06323002 plus Cedar80c10e2c virtual tree685811d0: 1062 tests +22 subtests in82.65s, exactly28 TopoStitch and11 shared modules, six CLI helps and saved old/new graph/frame/default-owner native-link/packing replay. Original build path absent; replay originals blocked. Viewer/replay package resources and legacy-v2 reader source pins verified.
**Limit:** No actual merge, full combined suite, native combined refinement or scientific acceptance. Zero source conflicts, seven documentation conflicts and one package-data union resolved only temporarily. Retain scheduling refusal and incorrect local packaged-v2 assertion; corrected read-only validation needs no product change. C340 not included; W100 native trials completed separately, pinned to C331; no ordinary combined refinement is implied.

<a id="e_source_displaced_native"></a>
### E_SOURCE_DISPLACED_NATIVE — complete_actual_input_tether_controls

[Evidence contract](topostitch-periodic.md#w100--source-displaced-controls) at [W100](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Three complete installed Phenix2.2.1-6174 source controls and common full-recipe observers pass all initial/full/rounded derivatives and input/policy guards. Matched displaced initial points/components are exact. Paired/unpaired reference RMS0.698233/0.942609 A from0.917427; raw pair333.793/1292.302 from835.308. Reference control itself moves0.421001 A. Affected230 bonds/356 angles fall below nominal3;39 chiral signs remain. Individual packing/torsion/plane tradeoffs persist.
**Limit:** All300-iteration NOT_CONVERGED_LIMIT; no stationary solution, blind repair, physical end closure, density/R statistics, adoption or ordinary-refinement qualification. Actual-input tethers differ across source models; do not rank their total objectives. Reference source is already native geometry REVIEW. ADPs stay unchanged.

<a id="e_pair_kernel_composition"></a>
### E_PAIR_KERNEL_COMPOSITION — native_pair_kernel_composition_microprobe

[Evidence contract](topostitch-periodic.md#w101--pair-kernel-composition-before-ordinary-refinement) at [W101](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Two exact W100 source recipes × raw/global-Cedar-corrected kernel contexts:4 cases each20/20 directions,162 evaluations and unchanged context/repeat. Baseline targets/gradients exactly equal; existing subtraction/replacement is idempotent here, so no fix needed. Complete owned Phenix2.2.1-6174 execution,18.04s,600s cap; native profile verified; original binding restored; inputs/software fixed.
**Limit:** Pair arithmetic only, not ordinary manager attachment/rebuild, combined normalization/exclusions, native full refinement or scientific acceptance. Retain initial Python3.12→3.11 NumPy ABI launcher failure; V2 package-only import isolation and old-process absence check do not change numerical policy. No runtime/schema change.

<a id="e_pair_model_entry"></a>
### E_PAIR_MODEL_ENTRY — native_actual_model_entry_diagnostic

[Evidence contract](topostitch-periodic.md#w102--complete-pair-arithmetic-through-actual-model-entry) at [W102](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Two sources × original/select-all actual model managers × native-only/pair-active objectives: eight cases each20/20 directions and162 evaluations, unchanged context and baseline repeat. Zero-valued callback leaves target/all gradients exact. Pair residual/forces share native normalization without increasing count; counts11389healthy/11263displaced. Twelve unsupported-setting controls reject. Complete owned Phenix2.2.1-6174 execution168.92s under900s cap; bindings restored and inputs/software fixed.
**Limit:** Explicit checked per-call binding, not automatic manager reconstruction/selection interception or ordinary refinement. C331 snapshots are idle callback-free/default energy-only observations, not qualification of internal shared buffers/custom callback. Static fingerprint does not independently inventory every angle/plane symmetry field. No exclusion changes, diffraction/optimizer/final writer/adoption or runtime/schema change.

<a id="e_pair_native_inventory"></a>
### E_PAIR_NATIVE_INVENTORY — native_pair_support_and_exclusion_diagnostic

[Evidence contract](topostitch-periodic.md#w103--actual-pair-membership-and-ordinary-phil-exclusions) at [W103](https://github.com/vecchioni-lab/NASolve/commit/7faff1a1247e78de1c48adb4ca620a93307660f4).
Six actual original/select-all/selected-reinterpreted managers preserve956bonds,1467angles,42planes; all124 requested terms absent from native supports, all36 requested Hbond contacts retain39 directed repulsion rows and no shell exclusion. Two ordinary identity-core PHIL controls instead install107 matching terms with verified targets/weights, preserve prior definitions, exclude31core contacts and remove117 directed nonbonded rows; native normalization count changes by-10. Independent Gemmi exact-image matching and Cedar pair-residual replay pass; observations leave each manager target/forces/sites exact.
**Limit:** Read-only local diagnostic, not a production observer or runtime activation. General-position atoms only. Initial rt_mx operator API failure retained; corrected multiplication leaves inputs/policy unchanged. Reinterpretation changes cell/coordinates by1.42e-14 and therefore exact policy SHA; retain/requalify rather than weaken C331. No callback-aware guard, duplicate/missing/stale activation rejection, periodic exclusion policy, diffraction/refinement or scientific acceptance.

<a id="e_pair_coverage"></a>
### E_PAIR_COVERAGE — read_only_declared_pair_coverage_checker

[Evidence contract](topostitch-periodic.md#w104--explicit-nativeadditive-term-coverage) at [W104](https://github.com/vecchioni-lab/NASolve/commit/97f5bbec3b410338586481893855c635ef684831).
New optional pure review_pair_coverage API requires exact frozen context/inventory digests, explicit providers, complete score parameters and unwrapped rational images.35new regressions,1911full+229subtests,204installed/relocated tests,sixhelps,pipcheck,leanimport,Python3.10syntax pass. Eight retained W103 native inventories replay exactly from installed wheel;12actual-derived negatives reject, including107duplicate native core terms,missing/changed terms,wrongimages andtinyreconstructed-context drift.
**Limit:** Checks caller-authenticated declarations only; cannot discover omitted native observations or establish valid group/general-position scope. No native producer, callback, exclusion/force/normalization qualification, lifecycle/finalwriter integration or scientific acceptance. Initial installed-test harness omitted an existing developer-script fixture;203passed/1failed retained,fixture-only correction passes204 with unchangedwheel. No new native execution or combined Cedar runtime test.

<a id="e_compiled_pair_declarations"></a>
### E_COMPILED_PAIR_DECLARATIONS — optional_compiled_recipe_declaration_exporter

[Evidence contract](topostitch-periodic.md#w105--declarations-from-the-existing-compiled-recipe) at [W105](https://github.com/vecchioni-lab/NASolve/commit/4253e378cc353cf26f1c2ae93b46c359e6f636aa).
Twelve new regressions;47 focused,1923 full+229 subtests,216 installed tests,six CLI helps,pipcheck,leanimport,Python3.10syntax pass. Existing compiler/worker bytes unchanged. Installed Phenix2.2.1-6174 exporter exactly matches124 independently derived terms in four healthy/displaced raw/Cedar-kernel cases; energies/fullgradients/bindings unchanged.18 native negatives reject drift.
**Limit:** Requested compiled recipe only, not complete actual-manager observation, exclusion approval or runtime activation. Initial native harness read-only C++ property failure preserved; separate V2 corrects harness with unchanged package. No refinement,density,scientific acceptance or latest-Cedar combined execution.

<a id="e_native_pair_observer"></a>
### E_NATIVE_PAIR_OBSERVER — callback_free_actual_manager_pair_observer

[Evidence contract](topostitch-periodic.md#w106--complete-callback-free-native-inventory-observation) at [W106](https://github.com/vecchioni-lab/NASolve/commit/ff0059f9a0cdf274636a2fcf84f2a697ea2da52f).
Optional native observer reuses checksum-bound C331 policy owner.13new regressions,60focused,1936full+229subtests,229installed,sixhelps,pipcheck,leanimport,Py3.10syntax pass. Eight native managers match independent2465/2572term inventories,bind107native+17additive coverage,andpreserve energies/gradients/sites.12negativecontrols reject callbacks,stale rebuiltpolicy andchangednative targets. Separatefive-rowC++codec/Gemmi audit covers actualASU denominators andretainedlattice offsets.
**Limit:** Callback-free general-position native-profile scope only. Caller owns source/recipe provenance and helper lifetime. Pair-cache refresh possible; no energy evaluation byobserver,noactivation,wholeobjective normalization,frozenlifecycle/finalwriter orscientificacceptance. Nativeparallelity constructorrejectssym_ops;virtualexpandedrecipe remainsowner. Preserve bothfailedcodec attempts:unsupportedparallelity argument anddenominator-sensitive native membershipassertion; exactrational productfixpassesV3 andrerunmanagerpanel.

<a id="e_missing_pair_arithmetic"></a>
### E_MISSING_PAIR_ARITHMETIC — actual_model_core_plus_missing_periodic_arithmetic

[Evidence contract](topostitch-periodic.md#w107--native-core-plus-only-the-missing-periodic-terms) at [W107](https://github.com/vecchioni-lab/NASolve/commit/ff0059f9a0cdf274636a2fcf84f2a697ea2da52f).
Complete107native+17additive coverage before/after explicit all-atomrebinding;8x20/20derivative controls,1296objectivecalls,12unsupported-settingrefusals. Zero callback exactlypreserves target/fullgradients; addedenergy/forces useactualnative N11379healthy/N11253displaced. Maxforcecompositionerror1.39e-17;192.80s Phenix2.2.1-6174 completeexecution. Sourceinputs/software/definitions/exclusions/kernelbindings preserved. Independentreviewreplaypasses;6Cedarowners/profilefilesmatch162ffe1d.
**Limit:** Bounded diagnostic with explicitly declared whole-pair split, not a general provider selector. C331 guards restored idle policy, not activecallback/internalgradientbuffers. Existing periodicrepulsion retained; noexclusionapproval,automaticlifecycle/refinement/density/geometryacceptance ormergedruntime. Initialpreparationwrongimport andarchiveprefixfailure retained/corrected; productioncodeunchanged.

<a id="e_pair_provider_selection"></a>
### E_PAIR_PROVIDER_SELECTION — frozen_term_level_provider_selection

[Evidence contract](topostitch-periodic.md#w108--frozen-term-level-provider-selection) at [W108](https://github.com/vecchioni-lab/NASolve/commit/9b7f8b17511a62af2e062f3c8790734a5e9ea103).
Optional selector handles partial individual pairs using exact support and score matching. 15 fail-before tests; 76 focused, 1952 full +229 subtests, 245 installed tests, fresh sdist/wheel relocation, six helps and lean import pass. Six complete Phenix 2.2.1-6174 cases change 107 native/17 additive to 104/20 after three within-pair removals; select-all replay and twelve negative controls pass. Complete native energies/gradients and coordinates unchanged; independent installed replay passes. Native execution51.20s.
**Limit:** Read-only planning from caller-authenticated complete declarations. No selected-subset evaluator, callback activation, active-policy/buffer qualification, exclusion approval, ordinary refinement or scientific acceptance. C331 pinned composition, not merged current Cedar. Existing image/general-position scope unchanged.

<a id="e_selected_pair_forces"></a>
### E_SELECTED_PAIR_FORCES — frozen_selected_native_pair_evaluation

[Evidence contract](topostitch-periodic.md#w109--evaluate-the-exact-frozen-additive-subset) at [W109](https://github.com/vecchioni-lab/NASolve/commit/f732f2ed4f25b703d232d390df265cf80918a843).
Optional evaluate_terms revalidates the complete compiled binding and exact ordered selected declarations before using the same kernel/correction/pullback path. Twelve fail-before regressions; 117 focused,1964 full+229 subtests,257 installed, fresh sdist/wheel relocation,six helps,pip check,lean import,Python3.10 syntax pass. Six native20/20 directional cases(972 evaluations),12 complement/full/empty/energy-only controls and12 negatives pass on two retained sources plus independent P43 screw fixture. Default target/full gradients exactly match W108; complement gradient maxerror7.11e-15.
**Limit:** Numerical subset evaluator only; no actual-manager callback, active policy/buffer or automatic lifetime, exclusions, ordinary refinement or scientific acceptance. First native attempt remains FAILED after four passing cases because the harness sorted the synthetic source; only synthetic fixture rerun with original atom order passes. Compiler behavior and captured worker remain unchanged; shared evaluation implementation changes.

<a id="e_provider_normalization"></a>
### E_PROVIDER_NORMALIZATION — actual_model_provider_normalization_and_shared_protocol

[Evidence contract](topostitch-periodic.md#w110--provider-normalization-and-active-contribution-contract) at [W110](https://github.com/vecchioni-lab/NASolve/commit/f732f2ed4f25b703d232d390df265cf80918a843).
Six complete actual-manager cases preserve raw energy/forces after moving three terms from native to W109 additions, but native restraint count falls by3 and normalized target shifts0.02637/0.02667%. Native energy-only, gradient, normalization-on/off and select-all controls pass; raw gradient maxerror1.14e-13. Twelve negatives pass;59.97s Phenix2.2.1-6174 execution and independent audit. Reviewed separate active-admission/lifetime contract reuses Cedar reader and existing frozen execution; process-local callback identity/restart, buffer ownership and conditional restoration explicit.
**Limit:** Native-N preservation is diagnostic, not provider-independent geometry/data weighting. Candidate complete counts are arithmetic only; no qualified counted runtime, active policy guard, automatic lifetime, exclusion change, ordinary refinement or scientific acceptance. No production change after W109. Configured-callback admission remains proposed; C331 stays callback-free. Native extension objects are not forwarded by the ordinary mmtbx manager.

<a id="e_counted_contribution"></a>
### E_COUNTED_CONTRIBUTION — local_actual_model_counted_contribution

[Evidence contract](topostitch-periodic.md#w111--counted-contributions-through-actual-model-entry) at [W111](https://github.com/vecchioni-lab/NASolve/commit/f732f2ed4f25b703d232d390df265cf80918a843).
Six actual-model full/partial/select-all cases give provider-invariant complete counts11396healthy/11270displaced and normalized target/fullgradients; max target error4.44e-16 and gradient1.39e-17. Four20/20 directional controls(648 calls),18negatives incl6C331facade refusals, empty-subset identity and energy-only/normalization controls pass.212.27s complete Phenix2.2.1-6174 execution. Independent roundtrip control restores both hierarchy and fractional scattering state exactly.
**Limit:** Local geometry-method facade forwards native energies_add; not installed/qualified active owner or automatic refinement lifecycle. Counting scope is four canonical proxy families with unchanged repulsion. Attempt1 wrong module/class reference and attempt2 exact-restoration failure remain failed; isolated controls identify7.11e-15 force-site roundoff and dual restoration fixes harness without tolerance/product change. Production code stays W109; no ordinary refinement/density/scientific acceptance.

<a id="e_dual_native_state"></a>
### E_DUAL_NATIVE_STATE — opt_in_dual_native_state_observation

[Evidence contract](topostitch-periodic.md#w112--bind-both-hierarchy-and-scattering-coordinates) at [W112](https://github.com/vecchioni-lab/NASolve/commit/9c4529080e3558e2c0d0f8a98e0c934e38db554d).
Opt-in v2 reuses Cedar output readers and separately hashes hierarchy, scattering, original fractional and force coordinates.17 fail-before regressions;105 focused,1981 full+229 subtests,274 installed checks pass with relocated sdist/wheel,six helps,pip check,lean import and Python3.10 syntax. Six native cases and12 negatives pass in53.46s Phenix2.2.1-6174 complete execution. Four no-motion roundtrips alter scattering fingerprints while legacy v1 stays exact; dual restoration and native target/gradient/count preservation verified.
**Limit:** Read-only callback-free observation, not active owner or lifetime authority. No setters, ADP synchronization, force activation, exclusion or refinement change. Caller authenticates source/helper and single-owner access; double-read does not establish concurrency safety. Existing v1 result remains default; v2 requires explicit state owner/source digest.

<a id="e_frozen_pair_contribution"></a>
### E_FROZEN_PAIR_CONTRIBUTION — fresh_frozen_selected_pair_contribution

[Evidence contract](topostitch-periodic.md#w113--freeze-the-selected-pair-contribution-factory) at [W113](https://github.com/vecchioni-lab/NASolve/commit/3f5806106bdb233e648ad3c8442d878998c846da).
NativePairContribution freshly compiles exact inputs, freezes existing W108 selection and revalidates via W104/W105.19 fail-before regressions;153focused,2000full+229subtests,293final-installed checks pass. Eight actual native full/partial/select-all/all-native-core cases and16negatives pass87.59s in Phenix2.2.1-6174. All16 energy/gradient outputs exactly match old subset evaluator; source arrays/native target/gradients/counts unchanged. Prior public class/function AST unchanged; final source and relocated wheel match.
**Limit:** No active owner, callback, correction installer, persistent runtime schema or refinement activation. Cedar must authenticate factory/modules/native sources, supply complete admitted native terms/context and revalidate entry/exit. Count policy applies only to four supported canonical families. Full suite precedes only exported source-tuple naming change; final installed/native checks use final code. Separate W112/C366 full-source composition remains independent.

<a id="e_counted_owner_lifetime"></a>
### E_COUNTED_OWNER_LIFETIME — cross_branch_direct_counted_owner_lifecycle

[Evidence contract](topostitch-periodic.md#w114--qualify-the-shared-counted-owner-lifetime) at [W114](https://github.com/vecchioni-lab/NASolve/commit/fb6475ff5b2e52e47278f32a41b0348e2d4d578b).
Complete Phenix 2.2.1-6174 diagnostic: 8 cases, 16 fresh owners/compilers, 28 actual-model calls, 302.62s. Zero additions reproduce native exactly; scattering-only movement preserves stale hierarchy and binds force sites; exact fractional/state restoration, select-all rebinding and fresh restart pass. Provider switch17→20 preserves complete counts11396/11270; maximum target difference4.44e-16 and gradient difference1.39e-17. Exact source/input pins and clean closure independently audited. Rowan separately reports155 focused/155 relocated-installed/32 native owner controls.
**Limit:** Direct cross-branch calls only, no ordinary runtime/optimizer/refinement, exclusion change, new derivative panel or accepted repair. C368 candidate source/wheel is pinned independently of Willow; W114 changes docs only. Native usage wrapper and selected-copy report/weight/final-writer consumers still require qualification.

<a id="e_full_source_c366"></a>
### E_FULL_SOURCE_C366 — full_source_virtual_branch_composition

[Evidence contract](topostitch-periodic.md#separate-full-source-compatibility-baseline) at [W114](https://github.com/vecchioni-lab/NASolve/commit/fb6475ff5b2e52e47278f32a41b0348e2d4d578b).
Unfiltered source suite:12138 passed,284 subtests passed,1 opt-in native module skipped,2982.99s. Exact W112 e005b0da/C366 09303e80 and NARestraints a9264f9 source/Git metadata. No source/test/script conflicts; package-data union only; clean source afterward. Raw logs, controller receipt and source archives verified.
**Limit:** Not an actual branch merge, complete installed suite, current W113/C367/C368 qualification or native refinement. Eight documentation conflicts remain. Earlier W81 installed-context failures stay preserved. Local Git alternates and forensic archives do not establish portable campaign execution.

<a id="e_actual_prepared_state"></a>
### E_ACTUAL_PREPARED_STATE — ordinary_zero_cycle_prepared_state_observation

[Evidence contract](topostitch-periodic.md#w115--observe-the-actual-prepared-model) at [W115](https://github.com/vecchioni-lab/NASolve/commit/72962bf4c1f611a1b88d99efea0e2b635bb666da).
Four complete Phenix2.2.1-6174 zero-cycle preflights: first inspection refuses source/native cell mismatch, second records full observation while refusing selection, third explicit-frame control passes, fourth installed C371 reader exactly reproduces independent records.855 ordered atoms and anisotropic scatterers,3333 reflections/176 original Free-R selections unchanged;2572 native supported-family proxies,124 requested terms=107native+17missing. Each native preflight2energy-only calls/0gradient calls. Saved readers and independent audit pass; all processes stopped.
**Limit:** Diagnostic returned-model entry reuses current runtime API; not the normal command-line entry, durable admission, owner activation, coordinate optimization or accepted repair. Default MTZ cell differs by2.93e-6Å; unchanged1e-10 frame gate refuses. Explicit source-cell control matches2.84e-14, not a production default. Current healthy geometry input is prior0.17855Å bend preview, not original deposited model. No new Willow API/schema/install or full-suite repeat.

<a id="e_bounded_ordinary_lifecycle"></a>
### E_BOUNDED_ORDINARY_LIFECYCLE — bounded_actual_ordinary_counted_lifecycle

[Evidence contract](topostitch-periodic.md#w116--qualify-one-bounded-ordinary-refinement-cycle) at [W116](https://github.com/vecchioni-lab/NASolve/commit/eb98c6f1ab4fa9dbce97d9133642a97545d1528d).
Phenix2.2.1-6174:3actual1cycle coordinate refinements plus3zero-cycle preflights. Actual fixedwx=wx_scale=wc=1,10iterations/12functions,nproc1,seed2679941. Native-only versus zero owner full states/statistics/geometry scores EXACT. Full17-added recipe gives distinct max0.033571Å/RMS0.002797Å endpoint. Both owners16successful calls, same model through final writer, checked identities before cleanup/restored; original3333data/176FreeR and non-coordinate scattering preserved. finish/validate_execution and independent audit pass. All processes stopped.
**Limit:** Diagnostic module-level driver.run/optimizer observer with immutable preflight records; no production admission/schema/default or branch merge. Full recipe changes requested chemistry; Rfree .25991557 versus core .25989801, both worse than preflight .25919212. No repair/diffraction benefit/adoption. Native-family reports omit additions. Standalone Cedar lacks existing Willow W35 PDB RMSD fallback; both readouts retained. Historical v3 competing-hook recovery not tested. Native refine12.10s, zero78.14s, full83.21s;6.46x overhead needs measured optimization, not fewer checks.

<a id="e_exact_image_fastpath"></a>
### E_EXACT_IMAGE_FASTPATH — stateless_exact_image_arithmetic_optimization

[Evidence contract](topostitch-periodic.md#w117--cancel-identical-validated-images-without-repeated-matrix-products) at [W117](https://github.com/vecchioni-lab/NASolve/commit/89eccdf261e92efd0c67564ce2cae24a8432ff9c).
Equal validated full images cancel exactly without repeated matrix products; distinct images retain exact lattice arithmetic. Nine regression cases: four fail before, five retain refusals. 223 focused,2009 full +229 subtests,302 installed tests pass; relocated sdist/wheel,six CLI helps,pip check,lean import,Python3.10 syntax and old worker bytes pass. Saved2572-term inventory exact,26415 redundant products become zero. C373 Phenix2.2.1-6174 complete direct native old/new call4.6208s to1.5670s with exact full target/gradient/count/normalization,call statistics,prepared selection/binding; inventory/policy poisoning refusals retained,source/state restored,process stopped.
**Limit:** No cache, schema, tolerance, provider policy or physical objective change. Single native call timing is not whole-refinement speed or scientific acceptance; W116 remains historical at its original pins. Initial full-suite sandbox run had five /bin/ps permission failures, retained; one complete process-enabled rerun passes. Coordinated package ownership and production admission remain open.

<a id="e_same_frame_pair_rebind"></a>
### E_SAME_FRAME_PAIR_REBIND — data_only_same_frame_pair_recipe_rebind

[Evidence contract](topostitch-periodic.md#w118--rebind-frozen-pair-intent-to-a-compatible-child) at [W118](https://github.com/vecchioni-lab/NASolve/commit/c08f337024f8901c583c0988f652e9a1c3156a49).
Only source-model digest changes after original packet/source and destination hash checks. Ordered identities, element, charge, occupancy, internal chain breaks and conventional frame are preserved; coordinates/ADPs may change. Frozen pair/library/PHIL/image/purpose fields remain exact, without regeneration or inference. 24 new regressions (23 recorded fail-before), 237 focused, 2033 full +229 subtests, 326 installed tests pass. Three saved W116 parent replays pass. Phenix 2.2.1-6174 complete compiler/direct evaluation gives identical 124 terms/images, energy and full 855-atom gradients at the same child coordinates; 1.32s owned wall, sources/kernel unchanged, stopped verified.
**Limit:** Data API only: not complete native packet validation, parent-lineage authority, provider selection, admission or continued refinement. PDB/CRYST1 only; explicit chemistry/occupancy required. No recut, renaming, reordering or chemistry changes. S05/S06 remain PARTIAL.

<a id="e_c374_joined_package"></a>
### E_C374_JOINED_PACKAGE — coordinated_relocated_installed_package

[Evidence contract](development-handoff.md#validation-and-compatibility) at [W118](https://github.com/vecchioni-lab/NASolve/commit/c08f337024f8901c583c0988f652e9a1c3156a49).
Cedar C374: one temporary joined installed namespace at W117/C373 pins, no source/test conflicts; explicit package-data union. 308 focused tests pass; exactly 22 missing-Gemmi skips then pass in existing Gemmi environment. Actual Phenix 2.2.1-6174 consumer completes in 27.43s with exact target/gradient/count/normalization, prepared selection, current wrapper and mutation refusal controls. 305 Python/resource files verified; original source/install removed, native process stopped.
**Limit:** No branch merge, full suite, W118 qualification or ordinary activation. Eight documentation conflicts retained. Cedar joined_installed_counted_consumer_2026_11_17 is the authoritative exact receipt.

<a id="e_strong_prepared_phase"></a>
### E_STRONG_PREPARED_PHASE — actual_strong_preflight_to_driver_boundary

[Evidence contract](topostitch-periodic.md#w119--consume-strong-preflight-state-at-the-real-driver-boundary) at [W119](https://github.com/vecchioni-lab/NASolve/commit/574b43273b8706c62df4fd4b9f1701153cb1c9e2).
Installed W118/C375, Phenix 2.2.1-6174: genuine isolated zero-cycle preflight (7.93s), controller validation and sealed stronger state, then fresh non-dry preprocessing reaches actual driver.run (9.57s). Strong bonded/normalization/pair/dual-state checks pass without replanning. One checked full-gradient call, native 11392 +17 additions =11409, one inner/extension, native-owned buffer. Original 3333 observations/176 Free-R and all model state remain unchanged; phase diffraction is exact. All bindings restore and both processes stop; independent audit passes.
**Limit:** Actual runtime retains FAILED/BoundaryObserved for intentional stop before original driver/optimizer. Diagnostic BOUNDARY_OBSERVED is not completed refinement; no final model, successful execution receipt, usable checkpoint, production admission or scientific acceptance. W119 changes Willow docs only. Separate installs, not a newer joined-package claim.

<a id="e_strong_complete_cycle"></a>
### E_STRONG_COMPLETE_CYCLE — strong_prepared_complete_cycle_historical_replay

[Evidence contract](topostitch-periodic.md#w120--replay-the-complete-cycle-with-stronger-prepared-ownership) at [W120](https://github.com/vecchioni-lab/NASolve/commit/e2c8218bea2154711207413a5af0c0b1b748daec).
Installed W118/C375, Phenix 2.2.1-6174: original W116 full-recipe inputs, genuine sealed stronger preflight and complete fixed-weight 1-cycle/10-iteration refinement through final writing. Final full state, physical PDB records, optimizer trace, R statistics, counted score and owner statistics match historical W116 exactly. Original 3333 observations/176 Free-R and non-coordinate scattering remain unchanged. All bindings restore, both processes stop and independent saved-evidence audit passes. Current refinement phase 37.03s versus historical 83.21s, a single observed phase comparison.
**Limit:** Diagnostic module-level lifetime around explicit unchanged v4; separate installed packages, not maintained controller admission or newer joined-package qualification. No new physical improvement, accepted repair, campaign checkpoint selection, default/schema change or claim of general speedup. Fixed weights and one coordinate-only cycle; broader phases and failure injection remain separate. Willow docs-only update.

<a id="e_current_joined_installation"></a>
### E_CURRENT_JOINED_INSTALLATION — current_joined_relocated_installed_package

[Evidence contract](topostitch-periodic.md#w121--qualify-the-current-joined-installation-and-maintained-lifetime) at [W121](https://github.com/vecchioni-lab/NASolve/commit/77e3902be413f65c276c13a02efa90c5d966c62b).
One installed namespace at Willow dbb5ae24 (code W118) / Cedar C377 0aaec4bd: 556 focused tests, zero skips in 25.06s, all six CLI entry points and pip check pass after source and original installation removal. All 306 Python/resource files match qualified sources. No source/test conflicts; explicit package-data union. Independent saved evidence audit and 70-file archive readback pass.
**Limit:** Eight documentation conflicts retained as unresolved. No actual branch merge, current-source complete suite, actual native run of this joined package, production activation or scientific acceptance. C377 native proof remains separate installed composition.

<a id="e_c377_maintained_phase"></a>
### E_C377_MAINTAINED_PHASE — cedar_maintained_prepared_refinement_lifetime

[Evidence contract](topostitch-periodic.md#w121--qualify-the-current-joined-installation-and-maintained-lifetime) at [W121](https://github.com/vecchioni-lab/NASolve/commit/77e3902be413f65c276c13a02efa90c5d966c62b).
Cedar C377 supplies explicit PreparedCountedRefinement around unchanged v4, one source-qualified module-level driver entry through final writing, actual prepared-parameter scope, same-model checks, foreign-binding preservation and original-error retention. Phenix 2.2.1-6174 actual preflight 7.79s and full bounded cycle 34.92s exactly match W120 preparation, endpoint, physical PDB, optimizer trace and diffraction. 15 checked calls omit the diagnostic extra score; all bindings restore/jobs stop. Native foreign-driver refusal/preservation, 46 final helper tests and 230 relocated installed tests pass.
**Limit:** Separate installed Cedar/Willow packages; initial scope fixed unit weights, one process/cycle and at most 10 iterations of all-site coordinates. Two earlier representation failures remain stopped preflights. No durable original-request/admission/descendant controller, ordinary default activation, new joined native/full-suite proof or repair acceptance.

<a id="e_frozen_phase_and_failure"></a>
### E_FROZEN_PHASE_AND_FAILURE — cedar_isolated_frozen_phase_and_final_output_failure

[Evidence contract](topostitch-periodic.md#w121-follow-up--c378-failure-recovery-and-frozen-worker-code) at [W121](https://github.com/vecchioni-lab/NASolve/commit/d23ff8bcfab0e0b1c2dc3b07bdba087d8a4a1f08).
C378 runs a complete actual Phenix 2.2.1-6174 phase with 18 frozen modules and three profiles (342,556 bytes) from W121, all native imports under the owned directory and no live NASolve namespace. Preparation, full endpoint, physical records, trace and diffraction exactly match W120; 15 calls, restored bindings and stopped processes. A distinct deliberate MTZ collision fails during final writing after optimization, retaining the first native error, partial outputs, closed/poisoned owner and restored bindings; native return codes 0/1 and no usable execution.
**Limit:** Failure occurred later than planned and remains failed, not a successful refinement or campaign recovery test. The isolated native worker uses frozen code, but the installed outer controller remains separate. No production admission, ordinary activation, optional chemistry-site observations, arbitrary protocol, portable campaign, independent SDK, branch merge or new complete-suite claim.

<a id="e_explicit_sticky_refinement_plan"></a>
### E_EXPLICIT_STICKY_REFINEMENT_PLAN — planning_only_explicit_sticky_end_refinement

[Evidence contract](topostitch.md#explicit-sticky-end-enforcement-during-refinement-planned-w122) at [W122](https://github.com/vecchioni-lab/NASolve/commit/f72ee37404adced6502fbdecfaa1d2d4ecf38b3c).
User-requested feature is placed after durable saved-request/preflight/admission and continuation integration, before automatic inference and large-bend repair. First expose declared canonical full-pair enforcement; independently qualify explicitly requested plane-only mismatch hypotheses afterward. Define enabled/disabled controls using 8D93, independent 5W6W/DOHU and later inventoried 7R96 contacts, reusing existing inputs/owners.
**Limit:** Planning only: no implementation, available CLI flag, runtime schema/default change, new refinement run or scientific acceptance. General supported-model scope is not universal chemistry support. Plane-only geometry leaves register and in-plane motion unresolved and does not establish H-bonds, stacking or covalent closure.

<a id="e_ordinary_pair_attribution"></a>
### E_ORDINARY_PAIR_ATTRIBUTION — read_only_saved_ordinary_endpoint_pair_attribution

[Evidence contract](topostitch-periodic.md#w123--attribute-saved-ordinary-refinement-pair-geometry) at [W123](https://github.com/vecchioni-lab/NASolve/commit/7361cad48c9136661391494f21e3e74f1b9b00d2).
Read-only Phenix 2.2.1-6174 evaluation reuses the existing compiler/attribution API on verified W116 full-precision endpoints through the W121 installed package. All 124 terms/14 pairs reproduce complete native sums; native-only and zero endpoints are exact. Full vs native selected penalties decrease 23.486130; 12 retained-core pairs decrease 0.102301 in aggregate, with two small increases. Selected plane deviations improve modestly. Independent readback, input/source hashes, serialization sensitivity and stopped processes verified; successful analysis 1.42s, no new refinement.
**Limit:** Residual selected-pair defects remain (GC distance 2.207122 A; AT distances 3.401875/3.491959 A) and Rfree slightly worsens. First failed attempt retains inability to reconstruct exact prepared initial force sites; source comparisons explicitly use serialized PDB only. Raw pair penalties are not whole-model normalized geometry scores. No backbone/stacking/packing/density acceptance, retuning, new implementation or repaired checkpoint. S05/S06 remain PARTIAL.

<a id="e_package_owned_integration"></a>
### E_PACKAGE_OWNED_INTEGRATION — maintained_library_integration_and_refused_admission

[Evidence contract](topostitch-periodic.md#w124--audit-package-owned-integration-and-refused-admission) at [W124](https://github.com/vecchioni-lab/NASolve/commit/93600202f84d84be9394cf0988a5287e779268fa).
Cedar C379 preserves native preflight success plus separate refused admission/NOT_LAUNCHED outcome with immutable anchored raw evidence and unusable checkpoint. C380 integrates unchanged W118 library at original paths:18 modules,17 tests,one script/514308bytes, optional topology extra and early source qualification. 662 focused source tests and 887 relocated installed tests+13subtests pass. Linden independently verifies36 imported files, preserved shared files,296 installed source/resources against committed C380, wheel hash and saved test receipt. No duplicate peer tests. Separate existing installed campaign/Doctor caller panel:15 tests pass in4.24s, no skips, exact C380 fixture/package bytes unchanged and process stopped; no native execution.
**Limit:** No new native execution, full-suite qualification, whole-branch merge, positive counted admission, continuation or ordinary sticky-end activation. Schema2 refusal requires updated reader; original schema1/default native protocols unchanged. Source integration is exact maintained upstream, not a vendor fork; bounded worker closure remains separately qualified. S05/S06 remain PARTIAL.

<a id="e_durable_counted_admission"></a>
### E_DURABLE_COUNTED_ADMISSION — maintained_counted_admission_independent_audit

[Evidence contract](topostitch-periodic.md#w125--audit-durable-counted-admission-and-native-outcomes) at [W125](https://github.com/vecchioni-lab/NASolve/commit/e6eb1f4d56a4f784d78ca297702f9b984b356923).
W125 independently audits C381 saved original/current intent, actual native preflight, immutable admission and exact same-phase consumption. Success reproduces W120 preparation/final hierarchy/scattering/force sites/physical PDB; 15 owner calls,11379+17=11396. Unsupported scope preserves native0 with refusal/no refine; final-MTZ failure preserves native1/original error/partial outputs and closed poisoned owner. Final347 installed tests+13subtests pass; independent298-file committed-source equality and24 unchanged frozen-native-file checks pass. Final readers cold-read all three outcomes without launches/persistent writes; successful root relocated with original absent.
**Limit:** Explicit one-cycle/unit-weight/all-site programmatic scope only. Ordinary AutoRefine/Doctor refuse counted ancestry including manual descendants to prevent silent intent loss; positive registered continuation remains next. No new Willow runtime code, ordinary CLI activation, selected campaign checkpoint, broader protocols, current full suite or scientific repair. No independent full-precision R-stat comparison in this audit. Pending historical commands are not resumable after relocation; W122 feature stays planning-only.

<a id="e_registered_counted_continuation"></a>
### E_REGISTERED_COUNTED_CONTINUATION — registered_counted_continuation_independent_audit

[Evidence contract](topostitch-periodic.md#w126--audit-registered-continuation-and-inherited-input-adaptation) at [W126](https://github.com/vecchioni-lab/NASolve/commit/1b19d556996ef660ffa756a24b239a5dc35f52f1).
W126 independently audits C382 registered same-intent continuation through two complete Phenix 2.2.1-6174 cycles and C383 reuse of existing C278 namespace-only restraint copies. Exact parent outputs, original intent, fresh preparations and 24 frozen native files per round verify; both descendants stay unselected REVIEW. C382 has 360 installed tests +13 subtests; C383 has 62 installed tests. Independent 298-file committed-source checks and relocated cold reads pass. PDB G.C plane mismatch falls 18.69 to 17.77 to 16.77 degrees, while logged Rfree worsens .2599 to .2609 to .2611. C384 closes skipped intervening refinements without execution records: two negative-before regressions, 144 source/144 installed tests, independent 298-file/source equality and unchanged 117-file cold registry /24-file native payload checks.
**Limit:** No matched native-only continuation siblings, scientific repair, ordinary CLI activation, whole-branch merge or current full-suite claim. W122 remains planning-only. Rowan follow-up on a copied C382 registry found C383 accepts a checksum-valid previous model substituted as the latest output; actual outputs above are independently verified, but final-writer/checkpoint binding must close before ordinary ownership. Broader protocol/chemistry, terminal-source changes, periodic exclusions, physical geometry and density remain open.

<a id="e_native_written_model_binding"></a>
### E_NATIVE_WRITTEN_MODEL_BINDING — native_written_model_publication_independent_audit

[Evidence contract](topostitch-periodic.md#w127--bind-the-published-checkpoint-to-the-native-written-model) at [W127](https://github.com/vecchioni-lab/NASolve/commit/99da97d210d7c428fb4b07eee96e77c871de8adc).
W127 independently audits Cedar C385 explicit v6 final-writer provenance and usable checkpoint binding. One completed Phenix 2.2.1-6174 cycle exactly reproduces C382 first-cycle PDB bytes, output synchronization and counted-owner observation;15 calls,11392+17=11409. Checksum-valid previous-model substitution refuses. Peer197 source/282 installed tests pass; independent299-file committed-source equality,24-file current/historical payload checks and immutable cold reads of64 current/117 historical files pass.
**Limit:** Explicit v6 only; old v3/v4/v5 payload bytes and their narrower proof retain meaning. Inherited v5 continuation is not implicitly upgraded. No new geometry/Rfree benefit, scientific acceptance, native v6 descendant, ordinary AutoRefine/Doctor activation, whole-branch merge or current full-suite claim. Initial missing-Gemmi harness stopped before native allocation and remains retained. W122 stays planning-only; broader protocol, chemistry/terminal-source joins, periodic exclusions and density remain open.

<a id="e_ordinary_counted_owner"></a>
### E_ORDINARY_COUNTED_OWNER — ordinary_counted_owner_independent_audit

[Evidence contract](topostitch-periodic.md#w128--carry-explicit-pair-restraints-through-ordinary-autorefine) at [W128](https://github.com/vecchioni-lab/NASolve/commit/d5c2fb7be944aae5e048903e1de495c67baa4b05).
C386 explicit named bounded protocol joins existing AutoRefine input/process/publication ownership, preserves original intent and records frame choice. Actual Phenix 2.2.1-6174 ordinary cycle reproduces C385 PDB exactly,15 calls11392+17=11409,unselected REVIEW. Independent299-file committed/install equality,32 unchanged ordinary parameter/command cases,72 current/64 historical immutable cold reads and exact label-only data/Free-R adaptation pass. Peer345 installed+13 subtests.
**Limit:** Python API only, one XYZ cycle/process, fixed unit weights/seed1/10 iterations. No broad weighting/phases/chemistry/terminal-source qualification, CLI/Doctor activation, repair benefit or whole-branch merge. C386 full source suite is RUNNING separately; no full pass yet. Native fixture needs no C278 namespace copy; test coverage is separate. Geometry RMS parser fields unavailable, not zero. Actual native control starts from a fresh diagnostic PostMR import; ordinary counted-parent continuation has synthetic coverage, not a new native descendant run.

<a id="e_provider_geometry_summaries"></a>
### E_PROVIDER_GEOMETRY_SUMMARIES — passive_native_provider_geometry_statistics

[Evidence contract](topostitch-periodic.md#w129--measure-provider-dependent-geometry-summaries) at [W129](https://github.com/vecchioni-lab/NASolve/commit/d5c2fb7be944aae5e048903e1de495c67baa4b05).
One20.68s Phenix2.2.1-6174 passive full/partial comparison preserves coordinates, force sites and complete normalized score0.6756064118611885; target/gradient errors9.09e-13/4.55e-13. Native default angle RMS2.30831009→2.30892601deg(count1519→1518) while origin0 statistics remain identical. Independent304-software/5-input audit, pooled variance and direct removed-angle reconstruction pass; native proxies/kernel restored.
**Limit:** One retained reference, not accepted healthy geometry. No optimization, weight search, actual selector-decision change, new active runtime or repair benefit. Origin4 is edits, not blanket noncovalent classification. Initial optional-niceness setup refused before native launch and remains preserved. Production source/policies unchanged; C386 full regression separate and still running with failures pending traces.

<a id="e_counted_chemistry_coexistence"></a>
### E_COUNTED_CHEMISTRY_COEXISTENCE — independent_counted_chemistry_integration_audit

[Evidence contract](topostitch-periodic.md#w130--keep-chemistry-observation-beside-counted-pair-forces) at [W130](https://github.com/vecchioni-lab/NASolve/commit/a67df6b7a70dad94d0f14e3cdabea5f8f5a9c21e).
299 Git/wheel/installed sources match;125+126 relocated and57 historical files unchanged. Two actual matched Phenix2.2.1-6174 observer off/on pairs with10998+0 and10997+1 terms preserve exact within-pair writer/native-state/lifetime. Source projection/PHIL derivative verified.377 distinct installed passes+24subtests after12 missing-fixture retries.
**Limit:** Low-level native mechanics versus synthetic ordinary forwarding/continuation. Cross-provider full precision differs despite exact rounded PDB. Rwork/Rfree0.4230/0.8360, bond/angleRMS0.116A/4.368deg do not qualify scientific acceptance. Old C386 reader refuses new optional v6 chemistry combination; v5 remains excluded. C386 full suite separate and unfinished.

<a id="e_semantic_pair_geometry"></a>
### E_SEMANTIC_PAIR_GEOMETRY — cold_pair_geometry_adapter_and_native_qualification

[Evidence contract](topostitch-periodic.md#w131--report-complete-pair-geometry-across-force-providers) at [W131](https://github.com/vecchioni-lab/NASolve/commit/ead86be9f70280cb7c76e2df9416aadbea301463).
203 focused/relocated installed;2050 full+229subtests after5 sandbox /bin/ps failures, all retained. Pure optional reader joins full attribution/declarations/v2 exact force sites/coverage. One15.13s Phenix2.2.1-6174 report comparison107+17vs104+20 preserves complete pair metrics/energy and2465 unclassified native terms.305software+5inputs verified; cold report and physical RMS audit pass;9 frozen helpers unchanged.
**Limit:** Descriptive caller-authenticated evidence, not authentication of arbitrary records. Native remainder/covalent geometry unclassified. No optimizer, selector, covalent/terminal classification, global default, CLI or scientific approval. Separate frozen C386 full run unfinished. Initial install harness expected source-only notes and lacked test helpers; corrected closure without product change.

<a id="e_full_suite_prerequisites"></a>
### E_FULL_SUITE_PREREQUISITES — full_regression_and_exact_source_failure_diagnosis

[Evidence contract](topostitch-periodic.md#w132--resolve-full-suite-environment-and-source-prerequisites) at [W132](https://github.com/vecchioni-lab/NASolve/commit/d5c2fb7be944aae5e048903e1de495c67baa4b05).
Complete unfiltered C386 run11873pass/46fail/2skip/281subtests,3266.71s; owned process stopped,1405tracked files unchanged. Exact failed-node rerun with host process permission45pass/1fail; remaining ATL source-bundle test passes with Git source metadata at exact installed NAR a9264f9e revision.14 dependency library/resource files exact. All46 original failures resolve without production fix/test skip.
**Limit:** Original failed full attempt retained; this is not an uninterrupted full pass or qualification of later Cedar revisions. Existing2 pinned-native opt-in skips remain. Full source-bundle gate requires real Git metadata and explicit dependency source path; installed-wheel checks are separate. Next full run waits for final validated integration pin.

<a id="e_final_pair_geometry"></a>
### E_FINAL_PAIR_GEOMETRY — independent_actual_final_pair_geometry_audit

[Evidence contract](topostitch-periodic.md#w133--bind-complete-pair-measurements-to-the-actual-final-writer) at [W133](https://github.com/vecchioni-lab/NASolve/commit/8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6).
303Git/wheel/installed files exact; actual52.84sPhenix2.2.1-6174 reproduces C386/C389 PDB/full native state and15counted calls. Cold reader and independent saved-measurement aggregation pass;77current/72baseline files unchanged. Complete14pairs,107native+17added;2465four-family remainder unclassified. One separate energy-only kernel call52to53;36gradient calls unchanged. Peer305installed+24subtests; complete suite running.
**Limit:** One explicit fixed-unit XYZcycle/10iterations/oneprocess only; no new structural or R benefit, no whole-model/covalent/packing/density acceptance, no CLI/Doctor activation. W131 passive original coordinates differ from actual starting model; no cross-table before/after claim. Raw science excluded from Git.

<a id="e_ordinary_pair_continuation"></a>
### E_ORDINARY_PAIR_CONTINUATION — actual_ordinary_native_continuation_and_cold_audit

[Evidence contract](topostitch-periodic.md#w134--continue-the-ordinary-run-with-final-pair-readback) at [W134](https://github.com/vecchioni-lab/NASolve/commit/8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6).
One69.94s complete Phenix2.2.1-6174 ordinary descendant; exact C382 second PDB and15-call owner11382+17=11399. Original intent, prepared NAR PHIL, data/Free-R, ancestry and selected postmr retained. Independent cold audit:138descendant/77source/117historical files+mtimes unchanged,303installed sources exact; wrong parent PDB refused.
**Limit:** Ten-iteration fixed-unit XYZ canonical scope only; no additional extra-restraint files or chemistry observer. Pair RMS improves slightly but RW/RF .2251/.2609 to .2253/.2611 and clashscore31.53 to33.78 worsen. No matched native-only descendant efficacy control or accepted repair. Two setup failures before native launch retained; no production changes.

<a id="e_full_c391_and_coexistence"></a>
### E_FULL_C391_AND_COEXISTENCE — full_regression_and_native_coexistence_cold_audit

[Evidence contract](topostitch-periodic.md#w135--close-the-full-integration-regression-and-observer-coexistence) at [W135](https://github.com/vecchioni-lab/NASolve/commit/8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6).
One complete unfiltered C391 suite11983pass/292subtests/2existingnativeoptinskips,3196.08s;1413tracked files unchanged,14exact NAR source resources,cleanGit,process stopped. C393 actual Phenix2.2.1-6174 preflight12.61s/refine42.78s,independent cold equality of old PDB/native state/common owner/chemistry/MTZ arrays;75current/126baseline files unchanged,303installed sources exact. C395 follow-up independently verifies48 actual reporting trials,141unique source matches,exact prior model/weight receipt/native calls/maps; unknown terms remain unclassified.
**Limit:** Frozen C391 only, not later source or whole-branch merge. C393 low-level coexistence is not ordinary chemistry continuation; poor RW/RF .423/.836 and pair geometry remain. Native opt-in skips retained; separate installed/native evidence keeps its scope. Canonical longer100-iteration control and normalization-history observation are planning only; no count/weight/force policy or scientific approval.

<a id="e_separate_screening_normalization"></a>
### E_SEPARATE_SCREENING_NORMALIZATION — independent_cold_review_of_private_diagnostics

[Evidence contract](topostitch-periodic.md#w136--separate-trial-screening-from-optimizer-normalization) at [W136](https://github.com/vecchioni-lab/NASolve/commit/8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6).
C396:40actual trials, exact2559-term inventory/141source matches, retained956bonds+1468angles, native criteria/fallback/tie replay and3239HKL-FreeR assignments verified; RW/RF worsens .2125/.2265 to .2277/.2444. A85:matched inputs/A71 baseline/common27evaluator inputs, target+gradient scaling/21entrycounts/choices/stops audited;9stpmin+12rounding becomes16rounding+5limits, RF .314876 to .312645. Neither is accepted.
**Limit:** Private PDU and metal diagnostics, not canonical TopoStitch efficacy. Native remainder stays unclassified; actual reporting model is not W131 full force-site proof. A85 retains private A71 selector and dynamically normalized native summaries; final amplitudes differ by qualified common F/sigma scaling. No runtime policy, general classifier, convergence or repair adoption.

<a id="e_actual_state_and_lineage"></a>
### E_ACTUAL_STATE_AND_LINEAGE — independent_actual_state_and_lineage_review

[Evidence contract](topostitch-periodic.md#w137--audit-actual-state-derivatives-and-ordinary-chemistry-lineage) at [W137](https://github.com/vecchioni-lab/NASolve/commit/8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6).
Exact2779-return state; FFT rawgeometry13/13,data0/13,combined0/13; direct13/13allcomponents at declared adjacent-step criterion. C398 retained full baseline/restored vectors repeat exactly. C303/C327 lineage and1.607versus1.470A target distinction independently verified.
**Limit:** Stopped private preADP diagnostics, no completed refinement/optimizer causality/production algorithm adoption. At W137, detached100-cap candidate d8656b22 had focused+installed passes with full/native gates pending; W138 subsequently qualifies those gates. Corrected standalone chemistry is not ordinary adoption.

<a id="e_longer_ordinary_control"></a>
### E_LONGER_ORDINARY_CONTROL — longer_ordinary_control_qualification

[Evidence contract](topostitch-periodic.md#w138--qualify-the-explicit-longer-coordinate-control) at [W138](https://github.com/vecchioni-lab/NASolve/commit/4f7aeb84b8762b3bd4ebcc1741c6b1116443632a).
334 focused +35 final pin checks;334 relocated installed tests;12008 passed, 2 skipped, 293 subtests passed in 3581.07s (0:59:41). Actual Phenix2.2.1-6174 ordinary280.319s; original intent/writer/final capture verified, child unselected REVIEW. Same-start GC17.775729→6.287164deg, Rfree.2609 unchanged, Rwork.2251→.2271 worse.
**Limit:** Mechanics only; both endpoints restrained. C400 matched native/core-only-zero/full and passive stopping history separately owned by Rowan. No convergence, density or whole-model repair acceptance. No default/CLI activation.

<a id="e_matched_canonical_long_control"></a>
### E_MATCHED_CANONICAL_LONG_CONTROL — matched_canonical_control_cold_review

[Evidence contract](topostitch-periodic.md#w139--measure-matched-sticky-end-benefit-without-claiming-repair) at [W139](https://github.com/vecchioni-lab/NASolve/commit/4f7aeb84b8762b3bd4ebcc1741c6b1116443632a).
Hazel82-checkunion PASS; native/zero exact history/model/MTZ and full W138 passive equivalence. Common14 rounded-PDB pairs: GC27.298448→6.298366deg, pairdistanceRMS.247180→.200020A. Final Rfree.2613→.2609, Rwork.2267→.2271 worse, finalPDBclash23.27→24.77 worse. Both stpmin at75/73iterations,86/82actualreturns; same-coordinate count-driven scalarjump independently reproduced.
**Limit:** Bounded local effect only; no convergence/overall repair/density/backbone acceptance. Initial zero refused stale effective library; corrected fresh compiler-built zero retained full/native. Log-only initialclash32.28 superseded only for finalstatistics by explicit model-bound amendment. No numerical-policy adoption.

<a id="e_backbone_saved_density"></a>
### E_BACKBONE_SAVED_DENSITY — read_only_backbone_and_saved_map_inspection

[Evidence contract](topostitch-periodic.md#w140--audit-backbone-response-and-saved-density) at [W140](https://github.com/vecchioni-lab/NASolve/commit/4f7aeb84b8762b3bd4ebcc1741c6b1116443632a).
1268native supports; independent3804printed-geometry/342torsion checks PASS;38existinglinks/126sugarsigns preserved. Near bondRMS .005764→.005993A; angleRMS2.748→2.765deg. Four saved ordinaryML maps×456atoms preserve signed own/common samples; C102P Fo-Fc -6.641→-6.677sigma persists. Headless ChimeraX viewer and10packet references pass.
**Limit:** No new fit, map coefficients, covalent connection, native weight policy or selected checkpoint. All176testindices included; model-assisted map phases and per-map sigma prevent independent validation claims. Sphere is uncalibrated; no displacement diagnosis, threshold, pucker/packing/whole-model acceptance.

<a id="e_shared_grid_sampler"></a>
### E_SHARED_GRID_SAMPLER — shared_sampler_installed_native_replay

[Evidence contract](topostitch-periodic.md#w141--qualify-the-shared-periodic-grid-sampler) at [W141](https://github.com/vecchioni-lab/NASolve/commit/9c4c3b050fedd42f6be1fd6f26aa03873709bd76).
Alder focused82PASS and independent source review. Exact191-file relocated wheel; CLI/package/bare imports pass. Both Phenix2.2.1-6174 read-only modes reproduce3648own/common samples exactly, four periodic checks each; original7source refs and191installed files unchanged.
**Limit:** Full Alder suite was pending at W141; W142 closes it at the same exact source pin. No new fitting, coefficient generation, metal full-capture repetition, map-reader/provenance adapter, density threshold or scientific acceptance. Willow does not import unmerged Alder.

<a id="e_shared_gates_map_boundary"></a>
### E_SHARED_GATES_MAP_BOUNDARY — shared_regression_and_cold_map_owner_audit

[Evidence contract](topostitch-periodic.md#w142--close-shared-qualification-and-map-the-density-boundary) at [W142](https://github.com/vecchioni-lab/NASolve/commit/4bfffbca068cfe74cc926ff68fefca5ba5c83c3a).
C402 full12016+293 passes/two native opt-in skips; installed143+19 joined pass/304resources. Alder full6406+276 passes/no skips,421independent sampler checks. Nine map-owner source files and seven science inputs unchanged; two model/map frames agree at reader-specific precision. Final C404 full 12032+293 passes/two existing native opt-in skips, 1416 tracked files unchanged; clean source/dependency and stopped process.
**Limit:** No new runtime source/schema/default, coefficient generation, native fit, detector, calibration, scientific acceptance or work-only search objective. Raw science excluded from Git.

<a id="e_backbone_density_presentation"></a>
### E_BACKBONE_DENSITY_PRESENTATION — local_scientific_display_study

[Evidence contract](topostitch-periodic.md#w143--make-backbone-density-inspectable-in-3d) at [W143](https://github.com/vecchioni-lab/NASolve/commit/081a532ce46a46ec67fbcd310e500e06ecd2ee8e).
Fixed-frame common/orthogonal 2D slices; 30 atoms and 32 native bonds from four saved C400 maps. User confirms v1 rotation and reviews v2 themes/dropoff. V3: 62 genuine contour meshes, 6,277 interpolation checks, 120 atom samples match W140, seven inputs and 30 prior meshes unchanged; 16 offline rendering/control checks pass. User subsequently approved v3 appearance and requested reuse throughout NASolve.
**Limit:** Human v3 visual approval recorded; no automated GPU/shader/browser qualification or general stage integration. Display-only FFT/triangulation, no fitting or new coefficients. Off-atom fade and contour levels are presentation settings, not noise classification. Prototype and scientific payloads stay local; no deployed GUI/schema or accepted repair.

<a id="e_map_frame_composition"></a>
### E_MAP_FRAME_COMPOSITION — cold_and_native_read_only_map_frame_composition

[Evidence contract](topostitch-periodic.md#w144--bind-saved-density-to-the-inspected-frame) at [W144](https://github.com/vecchioni-lab/NASolve/commit/0a398d15ee465b12ed44b7e749221e54a8e343a9).
Ordinary refine-002 and diagnostic full PDB bytes match; 8344x16 MTZ numeric entries/NaNs match. Inherited-map relocation and substitution/observation refusals pass. 16416 R3 image samples show up to 0.28 sigma interpolation variation; direct Fourier and existing complete source-frame sampling agree to numerical precision. Hazel independently passes 278 archive/frame/scalar checks without repeating native FFTs.
**Limit:** No maintained adapter, new coefficients, fitting, density threshold, force gradients, generalized origin proof or accepted repair. Existing viewing remains compatible. Separate C406 source qualification is recorded under E_SHARED_C406_COMPATIBILITY; local science excluded from Git.

<a id="e_shared_c406_compatibility"></a>
### E_SHARED_C406_COMPATIBILITY — full_source_and_cold_old_checkpoint_compatibility

[Evidence contract](topostitch-periodic.md#shared-c406-qualification) at [W144](https://github.com/vecchioni-lab/NASolve/commit/589659201a15b4284e93e2c4dcfc47cdefbdcb64).
12043 tests +293 subtests pass; two expected native opt-in collection skips; 3104.30s. All 1417 tracked files unchanged, source/dependency clean and process stopped. Cold genuine W138 v8 checkpoint/native output/map join remains compatible. Archive verified; owned source/test scratch retired on 2026-11-19 after archive/ownership rechecks.
**Limit:** Frozen Cedar source qualification and old-map continuity only. Separate installed/native and Alder integration evidence retain their scope. No active Willow/Alder merge, new sampling policy, browser qualification or scientific acceptance. Scientific payloads excluded from Git.

<a id="e_map_selection_origin"></a>
### E_MAP_SELECTION_ORIGIN — additive_view_map_selection_identity

[Evidence contract](topostitch-periodic.md#w145--expose-map-selection-ancestry-through-the-shared-view-owner) at [W145](https://github.com/vecchioni-lab/NASolve/commit/efbb0336e8cd9380fc12145e0ba4e26d7e54fbab).
MapOrigin exposes selected map stage/checkpoint and ordered consumers without parsing labels or requiring ancestor-model reads. Five new cases fail before; 114 focused+53 subtests, 2055 full+234 subtests and 114 relocated installed+53 subtests pass. 720 tracked source files and 89 installed files unchanged. Cedar adaptation passes 182+31 and preserves preparation/saved AutoSol contracts.
**Limit:** Navigation provenance only, not producing XYZ/ADPs, coefficient-generation policy or frame equivalence. No GUI launch, FFT, native fit, detector, schema migration or scientific acceptance. Combined Alder/Cedar gate pending; no active merge. Initial setup/test failures preserved and owned qualification scratch retired.

<a id="e_inspection_snapshot"></a>
### E_INSPECTION_SNAPSHOT — read_only_measured_inspection_projection

[Evidence contract](topostitch-periodic.md#w146--bind-a-read-only-model-and-map-inspection-snapshot) at [W146](https://github.com/vecchioni-lab/NASolve/commit/c3f52e2945f23ca77eb0c728a1353763a39c1a45).
W146 adds a read-only measured inspection snapshot over existing view/reference owners; 2061 full+234 subtests and 120 relocated installed+53 subtests pass. Genuine W138 compatibility over the installed combined owner preserves all inputs. Producer/frame evidence stays unassessed; W146 remains outside the frozen combined gate.
**Limit:** Freshly measured hashes are not producer evidence. No map parsing, generation, native fit, checkpoint selection or new frame/motion authority. Initial sandbox failures retained; combined integration separate; all owned qualification scratch retired after archival.

<a id="e_coefficient_selection_headers"></a>
### E_COEFFICIENT_SELECTION_HEADERS — native_coefficient_selection_and_header_description

[Evidence contract](topostitch-periodic.md#w147--share-exact-native-coefficient-selection-and-descriptive-headers) at [W147](https://github.com/vecchioni-lab/NASolve/commit/5319a870b92d82adbba2c817c3bdc1073aaae402).
W147 extracts exact native complex-array selection and descriptive headers:2070 full+234 subtests,129 relocated installed+53 subtests, source/installed native reads and exact19054-segment preview parity. Worker-v2 candidate binds executed helper bytes and passes2stale/change controls; it remains outside frozen combined integration.
**Limit:** Headers do not prove common origin, generation XYZ/ADPs or work/free policy. No new coefficients/refinement/threshold or accepted model. Prior adapter identity weakness retained with corrected executed-source binding; combined integration separate, owned scratch retired and scientific outputs local only.

<a id="e_matching_backbone_recovery"></a>
### E_MATCHING_BACKBONE_RECOVERY — idealized_matching_diffraction_backbone_recovery

[Evidence contract](topostitch-periodic.md#w148--recover-a-known-backbone-displacement-with-matching-diffraction) at [W148](https://github.com/vecchioni-lab/NASolve/commit/f83562b0c1f61eb5b696d1ba75ebb4578b22c7ad).
W148 reuses the exact W100 +5-degree canonical displacement with matching noiseless diffraction and fixed native refinement. Selected 204-atom RMS error falls 0.917427 to 0.029167 Å; endpoint-to-endpoint RMS is 0.026449 Å. Local covalent bonds recover, 126 sugar-volume signs survive, and Rowan independently reproduces the controls. Existing reference-link distortion remains explicit.
**Limit:** One idealized fixed-budget positive control, not experimental repair, density-noise calibration, new seam chemistry or a healthy whole-model qualification. No independent alignment, no fixed context during refinement, no convergence claim, no native-policy or runtime change. Raw science local; archival integrity is not portable executable lineage.

<a id="e_packaged_density_inspector"></a>
### E_PACKAGED_DENSITY_INSPECTOR — installed_readonly_scene_renderer

[Evidence contract](topostitch-periodic.md#w149--package-the-reusable-offline-density-inspector) at [W149](https://github.com/vecchioni-lab/NASolve/commit/04b6402a274f27b84da298d23ce5c0db58776438).
W149 packages the approved two-state offline inspector with bounded display geometry, explicit missing maps and caller-supplied source/frame notes. Final full Willow2091+234 subtests and source-free installed158+53 pass. Original W143 science/shaders and source/installed output match exactly; the same renderer displays actual W148 recovery coordinates. Rowan verifies corrected camera/work bounds; browser/GPU review remains separate.
**Limit:** Prepared-scene rendering only: no native map reader/generation, source authentication, frame proof, fitting, stage/CLI adapter or campaign adoption. No new scientific data or accepted repair. W146/W147/W149 remain outside shared integration; S07 remains partial.

<a id="e_shared_inspection_composition"></a>
### E_SHARED_INSPECTION_COMPOSITION — receiving_owner_compatibility

[Evidence contract](topostitch-periodic.md#w150--qualify-the-inspection-follow-on-against-shared-alder) at [W150](https://github.com/vecchioni-lab/NASolve/commit/04b6402a274f27b84da298d23ce5c0db58776438).
W150 exact shared-base composition passes192 focused+37 subtests and the same source-free installed profile.348 package files, genuine two-checkpoint reads, saved W143 HTML and19054 native preview segments remain exact. Candidate bundle is ready for receiving-owner review; no active merge or new full-pass claim.
**Limit:** No new runtime on active branches, stage adapter, inference, refinement or scientific acceptance. Focused/installed composition is not a new combined full pass; deposited adjacency is not geometry health.

<a id="e_reference_sequence_adjacency"></a>
### E_REFERENCE_SEQUENCE_ADJACENCY — deposited_sequence_reference_audit

[Evidence contract](topostitch-periodic.md#w151--separate-deposited-sequence-continuity-from-reference-geometry) at [W151](https://github.com/vecchioni-lab/NASolve/commit/04b6402a274f27b84da298d23ce5c0db58776438).
W151 deposited 8D93 polymer positions3/4 map to PDB B107/B111: the numbering jump is not three missing residues. The existing phosphate-angle distortion is already deposited. W115 unvalidated-preview lineage remains explicit; recovery is distinct from a healthy-reference qualification.
**Limit:** No new runtime on active branches, stage adapter, inference, refinement or scientific acceptance. Focused/installed composition is not a new combined full pass; deposited adjacency is not geometry health.

<a id="e_independent_opposite_recovery"></a>
### E_INDEPENDENT_OPPOSITE_RECOVERY — independent_matched_data_recovery

[Evidence contract](topostitch-periodic.md#w152--recover-opposite-backbone-displacements-in-an-independent-deposited-model) at [W152](https://github.com/vecchioni-lab/NASolve/commit/04b6402a274f27b84da298d23ce5c0db58776438).
W152 independent deposited5W6W opposite displacements recover from0.7641A RMS to0.05152/0.04653A; relaxed-reference drift0.01436A. Local232 bonds/363 angles,38 links,126 sugar signs and2569 common targets independently audited. Identical58 parallelity groups retain explicit source/boundary residuals; idealized matching data only.
**Limit:** Not experimental data, reciprocal straight/curved target recovery, general junction/stack health, larger bending, automatic window expansion or physical seam closure. Fixed budgets do not establish convergence; all XYZ active, B/occupancy fixed. No runtime/schema/default-policy change.

<a id="e_experimental_backbone_tradeoff"></a>
### E_EXPERIMENTAL_BACKBONE_TRADEOFF — experimental_adaptive_filtering_comparison

[Evidence contract](topostitch-periodic.md#w153--separate-experimental-backbone-recovery-from-geometry-driven-relaxation) at [W153](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W153 deposited5W6W experimental comparison preserves5137 raw observations/507originalFree, but positive native filtering drops one work reflection. Endpoints approach relaxed control0.21485/0.14566A; reference itself moves0.52152A and Rfree rises~0.019. Geometry improves, strong B2P negative density remains. Common4629work/507Free endpoint arithmetic reuses saved F-model without refit; mixed outcome, not accepted repair.
**Limit:** Not fixed-work-set trajectories, noise calibration or scientific repair. Maps include test reflections/model phases; fixed B/occupancy leave scattering/ADP alternatives. No weight retuning or accepted winner. Cold saved-coordinate decomposition leaves0.50357A all-atom RMS after diagnostic proper rigid fitting; no aligned XYZ exported. Broad covalent/plane RMS reductions are associations, not identification of the causal restraint family.

<a id="e_independent_map_labels"></a>
### E_INDEPENDENT_MAP_LABELS — independent_density_source_presentation

[Evidence contract](topostitch-periodic.md#w154--name-map-sources-independently-of-coordinate-states) at [W154](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W154 optional map_labels separates density provenance text from coordinate-state names while preserving defaults and science.30focused,2092full+234subtests,159relocatedinstalled+53subtests;93package files unchanged; exact saved-scene/source-installed HTML and17mock controls. Hazel reviews source and published payloads. Two owned scratch roots retired after archived verification:3956files/29020618bytes.
**Limit:** Presentation API only; no new source/frame proof, native policy, stage adapter, browser/GPU review or receiving-owner adoption. W150 remains frozen/deferred.

<a id="e_density_scattering_counterexamples"></a>
### E_DENSITY_SCATTERING_COUNTEREXAMPLES — prescribed_scattering_counterexamples

[Evidence contract](topostitch-periodic.md#w155--record-density-counterexamples-before-proposing-backbone-motion) at [W155](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W155 prescribed complex-F contrasts at identical7554HKLs/3.06A show negative modeledP from displacement, Q excess and B mismatch separately, with zero control. Only3scatterers vary; full/group additivity≤4.82e-12 and direct/FFT≤1.18e-14. Hazel cold review passes with explicit missing original version-API capture. Common reference normalization is not ML difference-map sigma; no detector or experimental attribution.
**Limit:** Known-phase noiseless complex differences, not measured/model-assisted ML maps or calibrated local attribution. Original native version API empty; separate installation identity does not retroactively capture that execution. No refinement, automatic motion, runtime/schema changes or accepted repair.

<a id="e_post_deformation_recovery_plan"></a>
### E_POST_DEFORMATION_RECOVERY_PLAN — user_clarified_planning_gate

[Evidence contract](topostitch.md#post-deformation-recovery-window-w156-planning) at [W156](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
User clarified that poor initial/early-cycle Rfree after deformation can recover with restraint-driven refinement. Separate parent, raw deformation, optional smoothing and post-Phenix trajectory; assess after a predeclared matched recovery window, without requiring monotonic early Rfree. Explicit required connectivity drives the search. User-declared post-recovery0.30 project gate does not require improved R statistics: worsened final Rfree even below0.30 requires maps; values above0.30 trigger named junction/connection/register/bulge/sequence/orientation/phosphate review with other causes retained.
**Limit:** Planning only. No runtime thresholds, schema, native run, automatic continuation or convergence claim. Budget exhaustion while still settling is unresolved, not proof of irrecoverability; no parameter search or repeated extension solely to improve held-out Rfree. Gate is planning, not a unique diagnosis, automatic approval or permission to rewrite sequence/topology.

<a id="e_native_recovery_stage_history"></a>
### E_NATIVE_RECOVERY_STAGE_HISTORY — archived_native_recovery_history

[Evidence contract](topostitch-periodic.md#w157--separate-scaling-and-coordinate-recovery-in-saved-histories) at [W157](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W157 reads84 archived native stages,15 minimizer records and18 scaling counts with independent Hazel review. Initial unscaled Rfree0.3207/0.3437/0.3376 becomes0.2413/0.2637/0.2624 at first bulk/scaling before XYZ; final0.2600/0.2579/0.2611. Reference hits100iterations in all5cycles. Existing report gains a verified inline stage plot; no new refinement.
**Limit:** No convergence or recovery acceptance. Stage totals do not identify per-stage HKL/Free membership; endpoint work exclusion remains separately audited. Native log-hit order is not a macrocycle trajectory. Original display wording and corrected identical numeric data are preserved. No production parser, source schema or runtime change.

<a id="e_discriminating_recovery_plan"></a>
### E_DISCRIMINATING_RECOVERY_PLAN — bounded_next_experiment_plan

[Evidence contract](topostitch.md#next-discriminating-experiments-w158-planning) at [W158](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
Audit completed controls and specify one undeformed fixed-unit versus ordinary recovery protocol comparison, followed conditionally by the existing opposite starts. Separately plan a three-case model-assisted density counterexample panel through the maintained map owner. Rowan confirms ordinary execution and parent/ancestry constraints; C403/W134 are precedents, not a same-source comparator.
**Limit:** Planning only; no new run, runtime authority, schema change or scientific closure. Ordinary parent/restraint/protocol qualification and explicit effective-reflection policy remain execution prerequisites. Model-assisted noiseless controls are not experimental/noise calibration or a detector.

<a id="e_ordinary_recovery_diagnostic"></a>
### E_ORDINARY_RECOVERY_DIAGNOSTIC — ordinary_recipe_diagnostic_comparison

[Evidence contract](topostitch-periodic.md#w159--compare-ordinary-recovery-with-the-fixed-unit-baseline) at [W159](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W159 completes one five-cycle ordinary-recipe diagnostic on the same undeformed5W6W source. Exact859atoms,2569initial bond/angle definitions,58pair/stack groups and5137effective observations/507originalFree survive;38links and126sugar signs remain. Selected drift0.591A versus0.522A; common Rwork/Rfree0.2264/0.2677 versus0.2392/0.2600. B2P B90.39→112.52 while own residual remains−8.38σ versus−8.09σ. This does not resolve the reference baseline; no opposite-start matrix or accepted repair.
**Limit:** Direct shared recipe/native owner, not complete ordinary PostMR lineage. Several policies change together; XYZ weight selection consults Free. Four selected-weight XYZ counts hit100, final90; stopping reasons/internal trial totals not qualified. No detector, causal attribution, runtime/schema change, general repair or scientific closure.

<a id="e_model_assisted_density_controls"></a>
### E_MODEL_ASSISTED_DENSITY_CONTROLS — model_assisted_synthetic_map_counterexamples

[Evidence contract](topostitch-periodic.md#w160--retain-ambiguity-and-normalization-context-in-model-assisted-maps) at [W160](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W160 closes the planned noiseless model-assisted three-case panel: one higher-B truth, 7554 common HKLs, 389 synthetic Free and 859 unchanged atom identities. Known position and B errors both give negative modeled-P density. Common truth-map samples are −3.11e−15/−0.804/−1.524 for zero/position/B; zero own-map normalization gives −1.624σ from numerical-scale residuals. Native formula/readback/direct-FFT checks and Hazel80-check cold review pass. No refinement, scale fitting, detector or experimental attribution.
**Limit:** Noiseless synthetic amplitudes and fixed unit scales/zero solvent. Native model phases and ML weights both change; synthetic Free participates in map weights and maps. Common truth normalization is available only because truth is known, not an experimental policy. No threshold, classifier, motion proposal or runtime/schema change.

<a id="e_saved_recovery_context"></a>
### E_SAVED_RECOVERY_CONTEXT — saved_recovery_context_and_screening_audit

[Evidence contract](topostitch-periodic.md#w161--locate-mixed-local-recovery-and-reuse-the-known-screening-diagnosis) at [W161](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W161 cold review covers42residues,459backbone atoms at3states in4held maps (5508samples),41P versus38existingO3-P links, and unchanged4bond/angle families. A10C5-prime moves2.543A into higher ordinary density in both held sources; D2OP1 moves2.520A into lower density. All76printed weight trials fail the.015A first bond screen, requiring native fallback; final51pair distances contribute99.11% of pooled squared bond deviations, not energy/force. Reuses C395/C396 diagnosis; one posthoc A9-11 viewer added. No refinement or selector change.
**Limit:** Posthoc description, not causal target attribution or accepted motion. Rounded trial tables prove the empty first screen, not full-precision tie replay or per-trial source inventory. No full-objective reconstruction, production policy, new refinement or browser/GPU qualification.

<a id="e_current_backbone_state"></a>
### E_CURRENT_BACKBONE_STATE — e_current_backbone_state

[Evidence contract](topostitch-periodic.md#w162--bind-the-selected-backbone-state-and-retain-the-derivative-limit) at [W162](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
Passive LS/ML observation reproduces all859 final atom records, both saved MTZ arrays and printed trials. Replay matches73returned states and the selected cycle5 weight7 frame. Geometry/combined local derivatives pass; data-only checks miss their prospective bound, so no finite profile runs. Both direct and FFT target/gradient restorations are exact. 194passive and120profile cold checks pass.
**Limit:** Private diagnostic, not ordinary PostMR ancestry, a complete generic state serializer or accepted motion. Historical dihedral limit/top_out/slack are omitted; no complete six-family state claim. No tolerance retuning or new numerical-policy sweep follows.

<a id="e_larger_declared_links"></a>
### E_LARGER_DECLARED_LINKS — e_larger_declared_links

[Evidence contract](topostitch-periodic.md#w163--retain-known-backbone-links-before-larger-displacement-recovery) at [W163](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
Signed15degree tapered starts move205atoms2.288A RMS, up to4.79A. Default3A interpretation drops one3.836A O3P bond and4angles; that first attempt is held without fitting. Matched private4A interpretation retains38links,58complete planes, captured proxy definitions and fixed nonbonded exclusions. Five-cycle recovery reaches.758/.279A RMS; unchanged reference reproduces W152 atoms/maps exactly.
**Limit:** Known canonical same-ASU links and noiseless matching diffraction only; no production cutoff change, automatic bond inference or symmetry-seam qualification. Original inherited torsion inventory is incomplete and explicitly qualified.

<a id="e_larger_recovery_window"></a>
### E_LARGER_RECOVERY_WINDOW — e_larger_recovery_window

[Evidence contract](topostitch-periodic.md#w164--measure-a-matched-recovery-window-and-retain-local-distortion) at [W164](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
One matched further5cycle restart reaches.25257/.03972A RMS from the generator; no-op remains.01436A. Final Rwork/Rfree .0211/.0259 and.0086/.0100. All859atoms,38links,126sugar signs and7554raw/effective endpoint F/SIGF/Free tuples survive. Positive B2O3-prime remains1.41A away and a local angle deviates31.32degrees. Nine reconstructed managers have identical explicit443torsion/62plane policies through the existing live owner. 601cold checks;51offline view checks and6-model ChimeraX1.12 headless load pass.
**Limit:** Five plus five cycles with a rounded-PDB restart, not uninterrupted10cycles or convergence proof. Low R values do not accept the positive distortion. Noiseless synthetic data and one target shape; reconstructed manager policy does not retroactively fill omitted optimizer fields. Browser/GPU/human review and broad repair remain open.

<a id="e_default_backbone_check_plan"></a>
### E_DEFAULT_BACKBONE_CHECK_PLAN — planned_default_backbone_fit_check

[Evidence contract](topostitch.md#planned-default-backbone-fit-check-w165) at [W165](https://github.com/vecchioni-lab/NASolve/commit/71dda01aecc616a8bc8f94506567ef3a3218842a).
W165 plans an enabled-by-default read-only backbone-fit check after usable refinement: high Rfree plus coherent atom-associated negative phosphate density or significant coherent positive backbone density. Separate detection, permissioned bounded trial and adoption; matched recovery/control and geometry/map/content review remain required.
**Limit:** Planning only: no detector, operational thresholds, CLI flag, automatic displacement or checkpoint replacement. Density ambiguity/noise calibration and source/frame binding remain gates; W164 synthetic recovery is not experimental acceptance.

<a id="e_parent_geometry_transport"></a>
### E_PARENT_GEOMETRY_TRANSPORT — same_asu_parent_geometry_transport

[Evidence contract](topostitch-periodic.md#w166--carry-known-parent-geometry-without-a-global-cutoff-change) at [W166](https://github.com/vecchioni-lab/NASolve/commit/7fb3b094a9fa2406d09f71b48bec6a847c8861df).
W166 retains 38 known same-ASU backbone links, the 3.8359 A bond and four flank angles using the default-cutoff parent manager with identity-mapped displaced sites. Complete geometry/planes/torsion policies and fixed exclusions agree with independent 4 A controls; raw energy/gradient comparisons pass and parent restoration is exact. Three qualified dry-runs, seven energy calls, 77 cold checks; no refinement.
**Limit:** Geometry-only returned-manager scope, not pre-fmodel integration, optimizer execution, automatic topology or accepted repair. Five setup refusals are preserved; native OP3 reordering requires exact atom mapping. No production source/schema/default change.

<a id="e_cluster_accommodation_plan"></a>
### E_CLUSTER_ACCOMMODATION_PLAN — shared_cluster_dna_accommodation_design

[Evidence contract](topostitch.md#cluster-accommodation-bounded-helix-opening-and-closing-w167-planned) at [W167](https://github.com/vecchioni-lab/NASolve/commit/f772132ae0e2933a5157fd61c2601f124f7e3d79).
W167 records user/Hazel/Rowan coordination: intact cluster rigid pose, then bounded coupled DNA opening/closing when needed, source chemical geometry/exclusions, neighboring-step/donor/width measurements and Alder A03/A07 recovery/assessment. Bridge linearity, cluster shape/local coordination/oxidation and count hypotheses remain distinct.
**Limit:** Planning only. No dedicated width mode, cluster experiment, new target/default or combined-runtime qualification; W166 signed-bend geometry transport and FT_Hg descriptive evidence cannot qualify cluster accommodation.

<a id="e_parent_preparation_recovery"></a>
### E_PARENT_PREPARATION_RECOVERY — same_asu_parent_chemistry_child_diffraction_recovery

[Evidence contract](topostitch-periodic.md#w168--retain-parent-chemistry-through-child-diffraction-and-recovery) at [W168](https://github.com/vecchioni-lab/NASolve/commit/da8794d779a04e9601a480f3eb8de3aee91bd0ae).
W168 carries parent-derived same-ASU chemistry through child-native diffraction preparation at the default 3 A cutoff. Two dry-runs pass 102 checks with exact initial Fcalc/Fmodel/masks and 7554 original tuples/389 Free; 38 links, the stretched bond/four angles and complete fixed geometry/policies remain. One admitted five-cycle native fit passes 39 cold checks and improves selected RMS 2.287991 to 0.271141 A (prior 4 A control 0.279044);RW/RF .0467/.0589. Local covalent RMS .007954 A/1.965877 deg, largest angle deviation 10.54 deg; all 126 sugar signs remain. Endpoints differ .008788 A RMS, not exact replay.
**Limit:** One canonical signed synthetic control, private process-local wrappers, not an installed/ordinary workflow, new link inference, modified chemistry, cluster widening, symmetry-seam qualification or accepted repair. Native diffraction is constructed before chemical interpretation, so the former pre-fmodel description is superseded for this entry. Complete source topology and input-admission/execution integration remain separate gates; no further fit queued.

<a id="e_existing_coordinate_admission"></a>
### E_EXISTING_COORDINATE_ADMISSION — existing_coordinate_only_owner_admission

[Evidence contract](topostitch-periodic.md#w169--reuse-the-existing-coordinate-only-admission-guard) at [W169](https://github.com/vecchioni-lab/NASolve/commit/cd05d4ec06a3e336009910cfc8c897f34d20244d).
W169 reuses audit_masked_endpoint and rebind_pair_recipe on actual W168 source/candidate bytes. Real displacement and no-op pass; eight altered children are refused by the endpoint owner, while generic rebinding keeps its intended B-change and unrestricted-coordinate scope. Source 27 / existing installed C407 29 checks pass with exact scientific readback; five owner modules are byte-identical. No missing fixed-B/Q helper was found, no product code changed and no native call or fit ran.
**Limit:** Cold byte/mask binding only. Supplied coordinates are saved three-decimal PDB points; the 5 A audit bound is declared posthoc and does not authenticate the original unrounded proposal or prospective admission. A fresh seven-pair recipe exercises binding only and does not replace executed native restraints. Existing installed-package replay is not a fresh installation qualification. Source chemistry/site symmetry, native topology/exclusions, fresh diffraction, callback lifetime and ordinary ancestry still require supported integration.

<a id="e_saved_residual_map_review"></a>
### E_SAVED_RESIDUAL_MAP_REVIEW — saved_matching_data_local_residual_maps

[Evidence contract](topostitch-periodic.md#w170--inspect-saved-maps-at-the-remaining-b2a13-distortion) at [W170](https://github.com/vecchioni-lab/NASolve/commit/42bf701be453b20673fa88bdda64c20db5c6411e).
W170 completes the queued saved-map review: six W164 arrays, 44 backbone atoms and four coordinate states per fixed map pass 108 checks. Both known positive-arm residual sites have negative difference samples at the recovered atom and positive samples at the generator. A13 C5-prime ordinary density is higher at the wrong point (3.812 vs 3.329 common reference-map sigma); its red centre is only -2.30 own-map sigma while the generating position is +7.35. Geometry deviations remain 31.32/23.06 degrees despite synthetic Rfree .0259. Common/own map scales, unchanged 7554 observations/389 Free, matched controls and a small static figure are retained. No new coefficients, coordinate change or fit.
**Limit:** Posthoc noiseless model-assisted maps include Free reflections; not independent validation, causal force diagnosis, an experimental threshold calibration or accepted repair. A single ordinary-map hill climb/red-only atom cutoff is insufficient in this example, without establishing a general detector. Three native parameter-reader setup stops are preserved; final read-only Phenix 2.2.1-6174 analysis passes. No product/default/schema or install change.

<a id="e_saved_parent_binding"></a>
### E_SAVED_PARENT_BINDING — optional_current_parent_snapshot_binding

[Evidence contract](topostitch-periodic.md#w171--bind-a-saved-motion-to-the-current-parent-snapshot) at [W171](https://github.com/vecchioni-lab/NASolve/commit/ab84322f6697fc29a25c170b1dbdbab11282c6c9).
Optional parent_model_bytes on load_bend_motion compares the admitting caller's immutable parent snapshot with the pinned preview source before returning the existing full-precision motion. Both preview schemas compose with the unchanged strict endpoint audit. Coordinate, B/Q, identity and metadata drift, mutable/non-byte input and sub-rounding bound violations are refused. Twelve new cases fail before; 118 focused and 118 source-free relocated installed tests pass, with 93 package-file hashes, pip check and six entry-point helps.
**Limit:** Snapshot binding only: caller still owns checkpoint identity, dispatch freshness and retained-parent/native lifecycle integration. Existing calls/returns and artifacts need no migration; no default, tensor policy, chemistry, CLI or native execution changes. Canonical registered-terminal-preview scope; no modified-metal opening, covalent closure, new refinement or scientific acceptance. No full-suite rerun for this isolated additive API change.

<a id="e_live_parent_topology"></a>
### E_LIVE_PARENT_TOPOLOGY — private_live_declared_topology_admission

[Evidence contract](topostitch-periodic.md#w172--require-declared-topology-before-parent-coordinate-transfer) at [W172](https://github.com/vecchioni-lab/NASolve/commit/a1df851398fd743b3d1723fdd5c0a31916bef15c).
W172 independently replays C345 declared two-link MATCH and C346 extra DA N6-DY C5T REVIEW. Inside actual Phenix parent preparation, legacy W168 stops before child restoration because SS-enabled soft membership is not C128-authorized. A separately declared C21 control consumes a prospectively bound W171 registered .25-degree motion (60 atoms; max0.048166 A;0.2 A bound). One completed dry-run retains38 declared backbone links,51 exact soft bonds,all213 supplied requests including20 original pair-planarity terms,complete bonded parameters,859 identities and phosphate oxygen inventory. Child diffraction is unchanged during parent interpretation.35 independent cold checks pass; two setup stops and one expected policy stop are preserved; zero optimization/refinement.
**Limit:** Private canonical same-ASU preparation/transfer only; no installed hook, ordinary selected-checkpoint ancestry, modified/metal motion, symmetry-covalent seam, independent child diffraction control or physical recovery qualification. The explicit policy is a distinct objective, not a continuation of W168. DY is a saved negative control, not a fresh live DY trial. No global milestone closes or raw science enters Git.

<a id="e_checkpoint_motion_binding"></a>
### E_CHECKPOINT_MOTION_BINDING — selected_checkpoint_input_binding

[Evidence contract](topostitch-periodic.md#w173--bind-motion-to-the-selected-checkpoint-inputs) at [W173](https://github.com/vecchioni-lab/NASolve/commit/16a5e13478a9fb4be9d559390bb65f3d084d3793).
W173 binds a saved canonical preview to an exact selected/current checkpoint and its anchored model, observations, ordered restraints and declared phases. It rechecks inputs around strict endpoint replay and supports a context pin for a fresh dispatch read. 138 focused plus 6 subtests and the same relocated/source-free installed suite pass; 25 added cases include selection drift, input races and old-path-gone relocation. Read-only admission only; no native hook, run lock, schema migration or scientific acceptance.
**Limit:** Canonical input admission only. No atomic dispatch, native chemical authority, ordinary retained-manager integration, modified/metal movement or scientific acceptance. Saved schema-2 complete references required; existing generic checkpoint APIs unchanged.

<a id="e_execution_motion_binding"></a>
### E_EXECUTION_MOTION_BINDING — read_only_execution_input_binding

[Evidence contract](topostitch-periodic.md#w174--join-checked-motion-to-the-frozen-child-request) at [W174](https://github.com/vecchioni-lab/NASolve/commit/02411806ad7d444672803a27e6699f68b11d888d).
W174 joins W173 to Cedar-owned frozen execution requests, distinguishing parent/candidate model roles and ordered inherited/adapted/extra restraints, phases and generated round parameters.159 focused+6 subtests and relocated installed tests pass;21 new cases,223 cold checks on real C412 v3/v7 requests and17 synthetic supported-reader checks in both source and installed contexts. No native call, chemical admission, lock or ordinary motion qualification.
**Limit:** Real C412 controls qualify request membership only; synthetic canonical fixtures qualify the composed preview API. Standalone Willow lacks Cedar readers; explicit trusted-owner compatibility is separate from combined-runtime support. No complete native chemical admission or accepted repair. Full Willow run:2145+234 passed,5 sandbox process failures; whole process module22+19 passes with required permissions.

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
