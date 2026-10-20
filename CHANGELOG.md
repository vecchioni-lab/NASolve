# Changelog

All notable user-visible, compatibility, schema, and reproducibility changes
to NASolve are recorded here.

The format follows Keep a Changelog. Until the first tagged release, historical
entries are reconstructed from repository history.

## [Unreleased]

### Declared triple-bond screening and isolated installed-library controls

- Verify all 1,387 Cedar 37 payloads. DP now preserves declared bond orders;
  its separate explicit charge control passes while raw omitted charges remain
  recorded. PDU requires no assignment. No generation or optimization ran.
- Add a generic declared-triple-edge audit of target lengths, linear angles,
  positive ESDs/weights, exact native membership, measured bending and torsions
  through linear axes. Review thresholds never generate replacement targets.
- Add Cedar 38's exact installed monomer lookup/source capture and comparison
  with explicit installed-CIF replay and the saved PDU candidate, at identical
  fixed isolated seed coordinates. Empty explicit dictionaries require a new
  explicit installed-library-only opt-in; existing callers retain their guard.
- Add the unchanged public 5PC CCD as an independent C7/C8 control. Preserve
  duplicate NARestraints records without selecting roles. Native SS inference
  is disabled; production defaults, dependencies and NARestraints policy stay
  fixed. No ReadySet, minimization, refinement or adoption is requested.
  All 79 new regressions, 143 focused and 2,279 full tests pass, with two skips
  and 276 subtests. Actual C37 replay passes after removed/relocated clean builds,
  with aliased temp paths, poisoned imports and the everyday edit preserved.
  Installed triple-bond qualification awaits the Mac return.

### Declared monomer order tokens and isolated formal-charge control

- Verify all 1,355 Cedar 36 payloads. Both installed readers complete; PDU
  passes raw inventory checks. DP retains route/atoms/coordinates/signed markers
  while five double orders become single and two declared -1 charges become zero.
- Translate declared bond-order aliases to the monomer reader's case-sensitive
  lowercase vocabulary in a separate consumer input. Preserve original source,
  graph, signed declarations and chemical order; leave CCD control bytes fixed.
- Add Cedar 37's explicit source-charge population control on a temporary native
  component. Require exact graph/coordinate preconditions and pinned charge-API
  source proofs; retain raw reader results, block conflicts and independently
  check post-population charges/total and unchanged recorded graph/stereo fields.
  No production default, dependency, generator, optimizer or adoption changes.
  All 48 new regressions, 180 focused and 2,200 full tests pass, with two skips
  and 276 subtests. Actual-capsule replay also passes after deleted/relocated
  builds, through an aliased temp root with poisoned ambient imports. Installed
  token/charge-control acceptance awaits the Mac return.

### Portable temporary graph checks and preserved failed preflight

- Verify all 1,327 Cedar 35 payloads. The audit stops before native parsing;
  source graphs, the PDU control and prior mechanics/rotation evidence survive.
- Resolve only the freshly created graph-check temporary directory, supporting
  aliased system temp roots while retaining strict caller-output symlink and
  overwrite checks. Both source dialects keep identical consumer bytes.
- Add Cedar 36's exact failed-capsule gate and parser retry. Preserve the full
  failed attempt and replay nested source/stereo evidence; no new chemistry,
  generation request, dependency or production-default change is introduced.
  All 16 new regressions, 132 focused and 2,152 full tests pass, with two skips
  and 276 subtests. Deleted-build, relocated-runner transport also passes with
  an aliased temp root and poisoned ambient imports. Native acceptance remains
  pending the Mac return.

### Preserved source reader dialect and accurate constructor scope

- Verify all 1,320 Cedar 34 payloads: DP's 35 unknown native markers reproduce
  the chirality assertion; PDU's known-marker constructor passes. Correct the
  scope record: that constructor internally minimizes local chiral templates.
  Historical NOT_RUN flags did not measure those operations; no whole-molecule
  dictionary trial or saved-model change occurred.
- Add an explicit source-dialect adapter preserving original comp_list monomer
  routing, signed declarations and exact coordinate aliases in a separate
  target-free input. Keep CCD controls unchanged; infer no N/R/S atom labels.
- Add Cedar 35 bounded installed parser/dispatch/readback controls and two exact
  parser snapshots, without a chiral-constructor or generation request. Keep
  raw disagreements, unqualified charge semantics and signed stereo visible.
  All 41 new regressions, 310 focused and 2,136 full tests pass, with two skips
  and 276 subtests. Deleted-source/poisoned-import transport and documentation
  checks pass; exact commands are recorded in the existing native ledger. Production defaults and dependencies stay unchanged;
  installed acceptance awaits the returned Mac evidence.

### Read-only source and native-reader stereochemistry evidence

- Verify all 1,288 Cedar 33 payloads and replay prior mechanics/rotation evidence.
  Both readers pass; DP stops before optimization in chirality handling. PDU
  writes a nonconverged candidate with omitted R/S labels and preserved graph,
  formal charges and source-relative signed sugar hands. Preserve both phases.
- Add an explicit Cedar 34 stereo action: replay saved chemical/numerical
  comparisons, compare labels and signed coordinate volumes, and retain the
  printed energy trajectory without inferring an optimum or convergence.
- Add bounded installation-bound reader/chiral-constructor controls and exact
  molecule/topology/chirality source snapshots. Preserve unknown declarations;
  no false nonchiral labels, independent CIP validation, whole-molecule trial, dictionary
  generation, captured-code execution, pickle loading or adoption is requested.
  This isolated reader constructor is not a full builder replay.
- Add 55 generic stereo, chemical-integrity, capsule and fake-native isolation
  regressions. All 269 focused and 2,095 full tests pass, with two skips and
  276 subtests; deleted-source/poisoned-import transport and documentation
  checks pass. Exact commands are recorded in the existing native ledger. No new dependency or production-default change;
  returned installed controls are recorded above with their corrected scope.

### Reader-dialect projection and explicit bounded eLBOW trial

- Verify all 1,229 Cedar 32 payloads and four installed source snapshots: PDU
  passes read-only input; DP needs a legacy-restraint/CCD format projection.
- Add a separate checked consumer adapter for declared charge, bond-order and
  aromatic/stereo aliases. Preserve unknown atom metadata, original fields and
  signed chiral volumes. Refuse conflicts and unsupported order localization.
  PDU consumer bytes remain unchanged; no chemistry or targets are inferred.
- Add opt-in, help-checked single-block step control, with actual installed
  options-parser proof of one block/requested steps before generation. Recheck
  installed/captured sources and unchanged default tolerance; avoid the captured
  failing macro-restart condition without patching Phenix or loading pickles.
- Preserve nonconvergence evidence independently of exit status/file creation,
  and retain original source/candidate/charge/numerical gates. All 39 new
  regressions, 214 focused and 2,040 full tests pass, with two skips and 276
  subtests; actual-input deleted-source transport passes. Returned native attempts
  retain DP preparation and PDU nonconvergence review. Production
  defaults, NARestraints policy, dependencies and adoption gates are unchanged.

### Installed eLBOW input contract and alias metadata

- Verify all 1,209 Cedar 31 payloads and distinguish DP's missing alias-field
  parser failure from PDU's optimizer/restart crash after nonconvergence.
  Neither attempt produces a dictionary or chemical rejection verdict.
- Supply exact primary atom IDs for an absent graph-source alt_atom_id column,
  preserving existing aliases and all chemical declarations. Record the added
  naming metadata; the rule has no component-code allowlist.
- Add an explicit --native-contract-only action: capture four anchored installed
  eLBOW source files and run bounded, help-verified read-only input checks.
  Preserve all prior evidence, reject changed/escaped source files and retain
  both failure phases. Captured code and serialized molecule objects are not
  executed; no optimizer setting, installed source or scientific gate is changed.
- All 29 new regressions, 175 focused and 2,001 full tests pass, with two skips
  and 276 subtests. Actual-input deleted-source/poisoned-import transport passes.
  Installed source capture/read-only checks await
  the user Mac. Numerical generation and native/scientific qualification remain
  open; production defaults, dependencies and NARestraints policy are unchanged.

### Canonical graph-source tags and explicit PDU control

- Verify Cedar 30's 1,185 payloads: installed eLBOW fails in the input parser
  before producing a dictionary. Preserve its complete failed attempt and
  distinguish absent numerical assessment from a zero-review count.
- Emit canonical mixed-case CCD Cartn coordinate tags for both source-coordinate
  families. The corrected DP export has exactly equal parsed fields/values;
  no chemical state or target is changed.
- Add explicit hash-pinned public PDU control bundling and source/NARestraints
  recipe-compiler tests, including full propynyl triple-bond preservation,
  source H/charge/stereo, mapped AT contacts and both stacking orders.
  The fixture is separate from the production curated library and old local
  18-component ZIP. No residue is inserted into the frozen scaffold.
- All 23 new regressions, 146 focused and 1,972 full tests pass, with two skips
  and 276 subtests. Actual-input deleted-source/poisoned-import transport passes.
- Cedar 31 retries DP and separately generates PDU using existing isolated
  generation/state/numerical gates. Installed generation remains pending;
  no native dictionary replacement, policy guessing, refinement or adoption.

### Source-graph numerical candidates and branch artifact storage

- Verify Cedar 29: all 1,173 payloads, 17 mechanics prerequisites and 96 sampled
  rotation directions pass. Each independent coarse grid favors the starting
  angle; nonzero slopes and the DP angle/plane conflict retain REVIEW.
- Add explicit Cedar 30 graph-only numerical recovery. Preserve exact declared
  chemistry, distinguish source-coordinate seed origin, remove old numerical
  targets/types from generator inputs and reuse isolated eLBOW guards. Compare
  candidates against the original source too; require complete formal-charge
  preservation. No model optimization or native dictionary replacement occurs.
- Put generated live-test runners in ignored `branch-artifacts/<branch>/runners/`.
  The optional builder checkout argument establishes the local ignore rule in
  older frozen checkouts without tracked edits. Record Cedar merge-time
  inventory/hash/archive cleanup; no laptop files have been moved or deleted.
- All 47 new regressions, 123 focused and 1,949 full tests pass, with two skips
  and 276 subtests. Actual-input transport passes after deleting both clean
  source copies, with poisoned ambient imports.
- Existing production defaults, dependencies and NARestraints intent remain
  fixed. Installed candidate generation/native qualification are pending;
  no modifier composition, ReadySet retry, refinement or adoption.

### Fixed-policy base-orientation diagnostic

- Add Cedar 29 from the verified Cedar 28 return. Select connected base groups
  from nominal geometry outliers through graph/context rules and retain all
  unsupported or unprobed sites. Temporary proper rotations preserve the
  scaffold and internal base geometry; no coordinate model is written.
- Require unchanged native inventory, qualified correction/source identities,
  complete corrected initial and endpoint-family snapshots before scanning.
  Nine angular samples at both precisions retain category contributions,
  four-step rotational derivatives, repeat/additivity/periodic controls and
  exact selected scalar/angle/plane source context. Cap total energy calls at
  3,000 and supported groups at six; keep all review outcomes.
- All 40 new regressions, 88 focused tests and 1,902 full tests pass, with two
  skips and 276 passing subtests. Actual-input offline inspection and synthetic
  deleted-build transport pass. Installed native orientation execution is
  pending. Existing defaults, dependencies and NARestraints policy remain
  fixed; no optimization, target tuning, refinement or adoption.

### Saved full-precision geometry continuation

- Add an explicit opt-in continuation for a completed corrected trial whose
  stopping remains limited and whose endpoint derivatives/native mechanics
  are qualified. Recompute prior raw derivative evidence and match native
  sources/static definitions, the saved target and the entire corrected
  gradient before optimization. Changed, rounded or reordered seeds refuse.
- Add Cedar 28 from the verified 980-payload Cedar 27 return. Continue saved
  coordinates with fresh L-BFGS history for at most 1,000 further iterations;
  retain prior/new stopping and cumulative optimizer counts independently.
- Repeat fresh endpoint derivative and all 17 native PDB mechanics checks;
  preserve NARestraints pairing/stacking policy, original energy/targets and
  exact source identities. Source-bundled offline and deleted-build inspection
  pass. The returned continuation verifies all 1,104 payloads, all 17 native
  mechanics checks and 336 sampled endpoint directions. Its target falls
  another 3.64%; stopping remains NOT_CONVERGED_LIMIT after 2,000 cumulative
  iterations. The same three distance/ten angle outliers persist; review
  exact remaining terms/sources before selecting another trial.
- Add 36 generic proof/seed/worker/capsule/transport regressions; 241 focused
  tests and all 1,862 full tests pass, with two skips and 276 subtests.
  Existing corrected/uncorrected defaults, production behavior and
  dependencies are unchanged. No target tuning, refinement or adoption.

### Bounded geometry trial with qualified native gradients

- Verify the 857-payload Cedar 26 return: all 504 sampled full/category and
  1,080 corrected per-plane directions pass, with unchanged native energies,
  both plane orders and three rigid-rotation controls. Retain all original
  native-kernel failures and historical Cedar 22 stopping evidence.
- Add Cedar 27 as an explicit bounded trial from the original initial
  coordinates under the exact qualified correction and fixed NARestraints
  policy. Recompute raw derivative evidence and match native source identities,
  static constraints and the entire corrected initial vector before optimization.
- Keep actual stopping, fresh endpoint derivative audits and 17-check native
  PDB mechanics as independent outcomes. Limits, errors and bad derivatives
  remain visible regardless of energy reduction. No native installation edits,
  target changes, policy guessing, refinement or adoption.
- All 1,826 tests pass, with two skips and 276 passing subtests, including 38
  new proof/source/worker/capsule regressions. Actual-input offline inspection
  and deleted-build source transport pass. The returned installed trial
  verifies all 980 payloads, 17 native mechanics checks and 336 sampled
  endpoint directions. Its target falls 28.72% with all accepted steps
  descending; stopping remains NOT_CONVERGED_LIMIT after 1,000 iterations.
  A bounded full-precision continuation is the next proposed test. No new
  dependencies, migration or production-default change.

### Both native first-plane roles for fixed gradients

- Verify the 794-payload Cedar 25 return and all 732 preserved prior payloads.
  Both endpoints pass every sampled derivative; initial coordinates retain six
  failures. An independent normal-orientation sign model reproduces the stored
  initial gradient and explains the remaining discrepancies without target edits.
- Add an explicit evaluator policy using each native first-plane derivative
  in original/swapped orders. Preserve manager membership, all copied parameters
  and native energies; retain the accumulation-only policy as the default.
- Add Cedar 26 with fresh per-plane and full-objective checks at all three
  coordinate cases. Exercise both orders and rigidly rotated equal/unequal
  tilted controls, preserving original kernel failures and numerical tolerances.
  All 1,788 tests pass, with two skips and 276 passing subtests, including 30
  new regressions and actual-input offline/deleted-build inspection. The
  returned installed audit passes every corrected sampled derivative while
  retaining original kernel failures. No optimization, production-default
  change, installed native edit, new dependency or adoption in Cedar 26.

### Explicit native plane-gradient accumulation correction

- Add an opt-in NASolve evaluator that retains native energies and replaces
  only the accumulated parallelity gradient with complete original i/j
  contributions. Preserve targets, weights, origin IDs and NARestraints policy;
  support shared atoms and already-correct native accumulation. Refuse
  symmetry-bearing planes and audit special positions explicitly.
- Add Cedar 25 from the verified 732-payload Cedar 24 return. Freshly check
  four-step derivatives at initial and both saved coordinate cases under the
  full objective and seven category controls, after exact raw-snapshot,
  source/static-constraint and 17-check mechanics prerequisites.
- All 1,758 tests pass, with two skips and 276 passing subtests. The 36 new
  regressions include independent analytic oracles, deliberately bad individual
  derivatives, source drift and deleted-build transport. Actual-input offline
  inspection passes. Returned installed execution passes both endpoints and
  retains six initial-coordinate directions; the next orientation correction
  audit is supplied by Cedar 26 before any new geometry trial. No
  production-default change, optimization, installed native file edit, new
  dependency, migration or automatic adoption.

### Installed plane-gradient accumulation diagnostic

- Add Cedar 24 from the exact verified 670-payload Cedar 23 return. Preserve
  earlier evidence and replay all 17 mechanics checks before native work.
- Compare complete single-restraint gradients with singleton/full-container
  accumulation and the fixed manager at both saved coordinate precisions.
  Repeat every plane in both orders and add tilted equal/unequal size controls;
  retain four numerical steps, repeated arrays and all disagreement.
- Record available installed C++ source bytes and pinned binary/API identities.
  No optimization, native patch, policy/target change or candidate adoption.
  All 1,722 tests pass; actual-input offline inspection and synthetic
  deleted-build transport pass. The returned 732-payload capsule completes
  native execution and reproduces omitted second-plane gradients in every
  captured/toy order. All 714 sampled individual-restraint directions agree.
  The installed loop-bound model exactly reproduces accumulation, and saved-data
  recombination explains every prior sampled discrepancy. The subsequent
  correction and fresh derivative audit are supplied by Cedar 25; no new
  dependencies or migration.

### Saved native gradient audit

- Add a separate Cedar 23 diagnostic from the verified Cedar 22 capsule.
  Rebuild and exactly match its initial manager, policy and numerical sources,
  then evaluate saved full-precision and rounded endpoints without optimization.
- Compare native directional gradients to four central-difference step sizes
  under the full objective and seven isolated category controls. Record repeat
  evaluations, target/gradient additivity, descent profiles and neighbour counts;
  retain every discrepancy without changing native mechanics gates.
- Reuse CIF Doctor's dictionary assessment and report all declared intersite
  distance groups. Select coordinate probes from ranked outlier endpoints,
  with no residue-code/site allowlist. Add source-bundled Git delivery and
  generic biased-gradient, drift, provenance, budget and deleted-build checks.
  All 1,691 tests pass. The returned 670-payload audit verifies 2,734 native
  evaluations and stable parallelity-gradient disagreement at both precisions;
  the other six families pass all sampled directions. Independent plane
  calculations and the public CCTBX accumulation-loop bounds reproduce the
  saved evidence, strongly indicating omitted second-plane gradient terms.
  Installed per-proxy/source confirmation remains open. No target edits,
  optimization, model writes or adoption.

### Bounded geometry trial under verified NARestraints policy

- Add Cedar 22 from the exact verified Cedar 21 endpoint, retaining all 19
  dictionaries and 13 compiled PHIL inputs. Replay both membership prerequisites
  offline; do not guess or compile relationships again on moved coordinates.
- Extend the existing fixed-definition engine with opt-in policy inventory
  matching. Require unchanged native controls, origin registry and APIs before
  optimization and after exact-identity PDB serialization, alongside every
  existing identity/definition/request/static-proxy check.
- Record one bounded trial's stopping, native gradients, full-precision and
  PDB-rounded objectives, displacement and separate readback evidence. Limits
  and warnings retain their actual classification; scientific approval remains
  REVIEW. All 1,669 tests and actual-input offline replay pass. The returned
  609-payload capsule verifies 17/17 native readback checks and a 24.26% objective
  decrease, while retaining NOT_CONVERGED_ERROR after a line-search stall.
  CGY–DX pairing and local angles remain strained. No new dependencies,
  diffraction/refinement or production integration.

### Explicit NARestraints pairing/stacking membership diagnostic

- Compile frozen generic pair/stack declarations with NARestraints recipes and
  mapped base planes; preserve existing explicit edits, component modifiers and
  source bytes. Reject ambiguous/unsupported intent or duplicate selections.
- Represent every requested generic stack explicitly before disabling competing
  secondary-structure construction in the separate bundle. Add opt-in native
  control/origin/source readback and exact membership/unaffected-proxy checks.
- Add a source-bundled Cedar 21 shuttle applying one policy to preserved initial
  and endpoint coordinates. Actual-input offline compilation and synthetic
  deleted-build transport pass. The returned 491-payload capsule verifies both
  native interpretations, each with 14/14 exact membership checks. All prior
  inputs and captured static proxies survive; geometry qualification stays open.
  No model edit, minimization, objective ranking, production change or adoption.


### Pairing and stacking authority for the next diagnostic

- Record NARestraints' existing permissive pair guesser, antiparallel-run rescue
  and recipe builder as inputs to the pending membership policy. Distinguish
  guessed pairs, reviewed/frame selections and native-generated proxies; retain
  score, warning and overlap evidence before freezing a trial. This is a
  source-verified documentation clarification, with no runtime or gate change.
- Record the accepted precedence: NARestraints pairing selections and recipe
  targets supersede automatic Phenix secondary-structure guesses. The pending
  explicit membership compiler must prevent competing inferred terms and
  distance-based loss of intended contacts; native enforcement remains planned.
- Apply the same authority to NARestraints' general stacking/plane mapping.
  Preserve its explicitly selected canonical native stacks and modified-base
  parallelities when suppressing competing inference; retain unknown-mapping
  warnings and verify actual coverage separately from base-pair plane terms.
  Eight existing upstream stacking/role tests pass; no runtime change.

### Cedar 20 native reread and conditional-restraint attribution

- Verify all 367 returned payloads and byte-exact serialization. Preserve the
  original 11 PASS/three REVIEW result: five new native hydrogen bonds and ten
  angles accompany unchanged input bytes, identities and component definitions.
- Add explicit-origin/cutoff read-only attribution. Require complete original
  proxy preservation, unambiguous cutoff crossings and two covalent-stem-linked
  endpoint angles per added bond; other changes remain unexplained. Explanations
  never pass or alter the original exact native comparison.
- Compare actual reread coordinates to the saved fixed-manager rounded vector,
  reporting PDB precision/float roundoff and preserving historical energy basis.
  Record the fixed-versus-fresh objective distinction and pending membership/
  convergence policy. All 1,628 full tests and actual-return replay pass. No new
  native run, optimization, target/dependency/production change or adoption.

### Native/PDB identity mapping and saved geometry continuation

- Verify Cedar 19's 310 payloads and completed fixed-manager optimization.
  Preserve its 500-iteration limit/false convergence criterion and stored final
  endpoints; record that serialization stopped before candidate/native postcheck.
- Replace positional PDB/native pairing with a checked one-to-one supported
  atom identity map. Preserve record order, headers and metadata; reject
  ambiguous/missing/changed correspondence. Actual saved-coordinate replay
  recovers all 877 atoms, including 157 reordered records.
- Add explicit Cedar 20 continuation from the exact completed capsule, without
  rerunning optimization. Verify hashes, inputs and manager evidence, then keep
  the unchanged native postcheck. Add generic order/identity, capsule, reuse and
  deleted-build regressions; the complete 1,612-test suite passes. Native
  postcheck/scientific approval stay pending.
  No new dependencies, target changes, production integration or adoption.

### Cedar 18 return and fixed-definition geometry trial

- Verify all 252 returned payloads, source-preserving DF generation, 68 passing
  dictionary checks/one unavailable charge readback and 14 fragment checks.
  Replay linked outputs and the nine-atom candidate byte for byte. Retain
  unresolved raw geometry and pairing evidence, source/charge reviews and REVIEW.
- Add an explicit one-pass native geometry-only trial after exact captured-manager
  matching. Hold definitions/flags fixed; record native terms/gradients, actual
  stopping/limit/error evidence and optimizer provenance. Preserve full precision
  separately from a new PDB's rounding, displacement and native proxy postcheck.
- Add the Cedar 19 pinned Git shuttle and generic synthetic/worker/transport
  regressions; the initial 1,598-test suite passes. Returned optimization and
  serialization continuation are recorded above.
  Production PostMR,
  qualification gates and existing schemas are unchanged; no target retuning,
  ReadySet retry, diffraction/refinement or adoption and no new dependencies.

### Cedar 17 return and explicit effective/source recovery

- Verify all 129 returned payloads and 14 native mechanics checks; reproduce
  the fragment candidate byte for byte. Preserve unchanged definitions,
  detailed proxies and source/charge reviews. Record remaining/worsened pair
  contacts separately from improved intrasite geometry; retain REVIEW.
- Select recovery by unsupported effective graphs and exact recorded original
  source hashes/content, with shared-context and modifier-composition guards.
  Reuse source-preserving whole-component generation and linked/native
  projection checks at fixed coordinates before a separate fragment trial.
  DF's frozen source has single sugar bonds; the aromatic declarations belong
  to the effective dictionary. No target is inferred from residual strain.
- Add the Cedar 18 shuttle, strict continuation/phase-order regressions and
  source-isolated actual-input planning. The 1,568-test suite passes. Native
  generation/interpretation is pending. Production PostMR and existing schemas/
  gates are unchanged; model minimization, ReadySet retry, refinement and
  adoption do not run, and no private scientific payload enters Git.

### Cedar 16 return and separate fragment-restoration candidate

- Verify all 74 returned payloads and replay the construction report. Record
  55 raw→restored crossings and a byte-exact legacy restoration replay from
  frozen inputs, reproducing the damaging coordinate-copy operation for those
  captured transitions. Preserve the original receipt and all earlier issues.
- Add an explicit DNA graph rule that transports a complete raw base through
  the preserved sugar frame. Keep backbone/unselected coordinates, atom
  identities and metadata; refuse unsupported graphs, attachments and frames.
  DF's aromatic sugar remains unchanged and under review. Eight supported
  contexts/84 base atoms form a separate candidate; descriptive bond/angle
  outliers decrease 50/107→34/72 without target changes or geometry approval.
- Add the Cedar 17 source-bundled runner and native identity/definition/full
  proxy comparison against the unchanged captured bundle. Preserve prior
  source/charge reviews and retain REVIEW. Generic regressions, the complete
  1,543-test suite and actual-input deleted-build transport pass; installed
  interpretation remains pending. Existing production PostMR and schemas/gates
  are unchanged; new schema-1 diagnostics add no dependencies or private data.

### Original construction provenance and Cedar 16 ferry

- Add an explicit read-only stage audit bound to the reviewed original model.
  Snapshot exact run artifacts and AST-declared Coot references, with anchored
  relocation, source/frozen hash checks and visible missing evidence. Never
  execute the saved script or collect outside-run paths.
- Compare captured intrasite bond/angle findings across exact PDB atom,
  component and element identities. Record observed threshold crossings only
  across adjacent comparable stages; retain the distinction between same-name
  parent coordinate matches, semantic correspondence and causal proof.
- Add the source-bundled Cedar 16 runner, regressions and partial-witness
  relocation validation. Full original Mac stage collection remains pending.
  No production PostMR, target, coordinate, native-tool, dependency or adoption
  change; new schema-1 diagnostic formats are separate from existing receipts.

### Cedar 15 return and coordinate provenance review

- Verify all 51 returned payloads and 47 unchanged frozen native members.
  Replay the captured geometry report, matching identities, targets, weights,
  statuses and counts with only computed-scalar platform roundoff at most
  7.11e-14. Confirm 50 bond/107 angle nominal deviations at least five and
  zero recorded chirality sign conflicts; aggregate REVIEW remains.
- Compare large intrasite deviations with declared dictionary coordinates and
  trace all 858 common atom identities unchanged from Cedar 05. Record earlier
  coordinate distortion and the next bounded construction/atom-correspondence
  audit. Root cause remains unestablished; no target, runtime, schema, coordinate,
  qualification-gate, optimization or adoption change. Native payloads stay
  outside Git.

### Captured Cartesian geometry review and Cedar 15 ferry

- Add a read-only diagnostic for Cartesian simple-bond distances, angles and
  ordered chirality volumes from a verified native inventory. Validate atom
  identities, indices, coordinate correspondence and detail counts; retain
  missing/zero-weight, degenerate, symmetry and deferred-category limitations.
  Nominal weighted deviations are descriptive rankings, not native residuals
  or scientific acceptance gates.
- Add the source-bundled Cedar 15 runner for the exact verified Cedar 14 ZIP,
  preserving all inputs and earlier qualification/source reviews. Write a fresh
  JSON report, short summary and review capsule. No new native execution,
  coordinate changes, target retuning, optimization, refinement or adoption;
  existing production paths and schemas remain unchanged. No new dependencies.
- Validate synthetic geometry/transport regressions, the full suite and actual
  captured-input relocation after deletion of both source-build fixtures.

### Cedar 14 native return and generality scope

- Verify all 141 returned payloads and completed baseline/candidate interpretation
  under Phenix 2.2.1-6174. Offline replay reproduces 138 PASS and nine unsupported
  formal-charge readbacks. All four outgoing-H findings clear; projected
  definitions, exact modifier IDs, captured-baseline replay and retained
  definitions/proxies pass. Aggregate REVIEW and source/geometry limits remain.
- Record the graph/context rule's existing synthetic `ZZZ`, misleading H-name,
  deuterium and true-end regression coverage. Distinguish the supported linkage
  motif from the hash-bound Cedar probe and source-specific reviewed corrections.
  Documentation/evidence only; no runtime, schema, gate, coordinate or adoption
  change. Private native payloads remain outside Git.

### Outgoing probe Phenix default and Cedar 14 retry

- Restore the versioned user-home Phenix default used by Cedar 12 when
  `--phenix-root` is omitted. Cedar 13 passed `None` to the explicit-installation
  loader after successful preparation, stopping before native execution.
  Explicit relocated installations and all captured-source hash checks remain
  supported; no scientific candidate, target, schema or gate changes.
- Add native-CLI regressions through the real installation loader and
  executable/version discovery, using explicit shell fixtures for external
  programs. Cover both the omitted option and an explicit path containing spaces.
- Verify all 58 returned Cedar 13 payloads, 35 unchanged frozen members and
  24 passing source/native projection checks. Deliver the corrected runner as
  Cedar 14 while preserving Cedar 13 and its capsule; installed qualification
  remains pending.

### Explicit outgoing-oxygen bundle validation

- Add a diagnostic preparation layer for graph-identified O3′ hydroxyl H/D at
  explicitly declared outgoing DNA links. Require all captured source/native
  rows to agree first, then use the captured canonical OC2 type. Add separate
  per-site modifiers while preserving existing modifiers, true free ends,
  retained formal/partial charges and every remaining numerical target.
- Add cumulative native qualification for exact projected definitions,
  modifier IDs, replay of the captured baseline and all existing link, custom
  proxy, unaffected-definition/proxy, reviewed-torsion and charge gates.
- Add the source-bundled Cedar 13 probe for the exact Cedar 12 return. Offline
  preparation validates all 116 payloads and reproduces the four bounded
  corrections without changing the 877-atom model or original dictionaries.
  Installed interpretation remains a separate validation. Existing source
  reviews and unavailable formal-charge readback remain visible; no production
  PostMR change, target retuning, optimization, refinement or adoption.

### Default conditional Git delivery and Cedar 12 return

- Make one pasteable subshell with `&&` the default for reviewed live-test
  handoffs: fetch, full-SHA detached worktree, build and run with explicit
  paths. Preserve the everyday checkout and old deliveries; keep required
  installation commands as separate one-liners. Agent instructions point to
  the existing collaboration contract; no private personality notes are added.
- Verify all 116 Cedar 12 payloads and completed baseline/candidate native
  interpretation under Phenix 2.2.1-6174. Record 95 passing checks, six
  unsupported formal-charge checks and four existing curated outgoing-O3′-H
  reviews. Terminal/5CM projected rows, corrected torsion/alternate proxy and
  unaffected definitions/proxies pass; the overall verdict remains REVIEW.
  Documentation/evidence only; no runtime, schema or qualification-gate change.

### Explicit modified-terminal and reviewed-bundle validation

- Add selected 5′-OH preparation from a successful captured native `5*END`
  control. Retain the shared base/internal contexts, copy exact hydroxyl
  numerical targets and types, and keep the new hydrogen's formal charge
  unassessed rather than substituting the native partial charge.
- Add exact projected native-definition, reviewed torsion/alternate-proxy and
  unaffected-proxy comparisons. Audit every declared outgoing O3′ endpoint by
  hydrogen adjacency, exposing pre-existing curated linked-state reviews.
  Preserve all existing qualification gates and distinguish these findings
  from the new selected candidate changes.
- Add the source-bundled Cedar 12 probe using the exact returned Cedar 09/11
  capsules. Reuse the 43-site shared-code model, apply the explicit reviewed
  5CM recipe, and compare baseline/candidate native interpretation with
  installation/source hashes checked before and after. Detailed schema-1
  inventories add neutron bond targets and torsion alternate readback.
  No model optimization, ReadySet retry, refinement or production adoption.

### Cedar 11 terminal-source return

- Verify all nine returned payloads, the exact reviewed 5CM candidate and
  successful installed Phenix 2.2.1-6174 canonical terminal control. Record
  native PDB-to-library identity resolution, hydroxyl atom/type/targets and
  unchanged unrelated restraint rows and source files.
- Record the canonical free-OH control's `undetermined` classification alongside
  retained DNA group and unavailable formal-charge readback. Classification
  alone does not distinguish the earlier modified-end defect. The actual
  missing modified-end hydroxyl treatment still requires implementation.
  This is evidence/documentation only; no runtime, schema or gate change.

### Native canonical residue-name resolution

- Resolve canonical terminal-resource controls through the installed native
  residue-name interpreter instead of sending a PDB name to the direct library
  lookup. Record requested/interpreted/resolved identities and the additional
  `iotbx.pdb` source hash under terminal-resource policy v2. Schema 1 remains
  additive; unavailable APIs or components remain unsupported.
- Record Cedar 10's exact reviewed 5CM preparation and captured installed
  `5*END` rows separately from its failed direct `DG` lookup. The Cedar 11
  retry preserves all prior runs and supplies one conditional command block.
  Terminal-recipe implementation, native candidate qualification and refinement
  remain separate work.

### Explicit terminal-source review delivery

- Add a reusable installed-resource inventory for exact native modification
  IDs and a canonical in-memory control. Record native CIF row fields,
  numerical values, module/source hashes and preservation; missing interfaces
  or modifications remain explicit. Formal and partial charge stay distinct.
- Add the source-bundled `10_Cedar` probe for the exact returned Cedar 09 ZIP.
  Verify all 207 payloads, prepare a separate 5CM candidate through the existing
  hash-scoped recipe, and collect installed `5*END` plus its DG control.
  The numerical-source evidence is for subsequent terminal-recipe review;
  no terminal recipe, model editing, minimization, refinement or adoption runs.
- Preserve all prior deliveries, explicit path overrides and inspect-only
  operation. The actual returned 09 source reproduces the reviewed 5CM candidate
  hash offline; installed terminal-resource capture remains the next live check.

### Cedar 09 returned native evidence

- Verify all 207 returned payloads. Installed Phenix 2.2.1-6174 now reads
  DNA group/classification for all four linked sites; 29 qualification checks
  pass and four formal-charge checks remain UNSUPPORTED. Preserve the REVIEW
  verdict and unchanged model, 38 links and exact custom proxy coverage.
- Record the separate read-only comparison: all 148 source/candidate formal
  charges agree, and 12 ordered sugar-centre signs agree with source ideal
  coordinates and native proxies. This does not replace absent native charge
  readback or establish independent absolute stereochemistry.
- Preserve remaining scientific reviews: synthetic E:1 demonstrates site
  isolation but not complete free-OH terminal chemistry; its classification
  is undetermined and O5′ retains O2 typing without an attached H. Existing
  plane/angle findings and the retained 5CM C2/C2′ torsion issue remain visible.
  This is evidence/documentation only; no runtime, gate or schema change.

### Native component-list metadata

- Preserve the singleton `_chem_comp` row as a loop in linked base and
  projected dictionaries. The native `comp_list` reader ignores scalar fields,
  leaving the declared DNA group absent. Parsed metadata, atom definitions,
  numerical targets, modifier bytes and PHIL selections remain unchanged.
- Add schema-1 `component_list_policy` provenance, detailed native
  classification readback, and separate atom-inventory/polymer-group checks.
  Missing or incorrect native DNA group still prevents complete qualification;
  unavailable formal charges remain explicitly unqualified.
- Record Cedar 08's completed baseline, linked and shared-code native
  interpretations. All 207 payloads verify; site atoms/H/types, 38 backbone
  links, custom proxies and unaffected definitions agree. Group metadata and
  charge readback keep that result at REVIEW. Cedar 09's returned installed
  check is recorded above; no optimization, refinement or adoption occurred.

### Native registration of site modifiers

- Fix linked preparation to emit one `data_mod_<requested ID>` block per
  site modifier. The native reader registers block suffixes; the previous
  shared `linked_sites` block ignored the distinct atom-loop IDs and collided
  across component files. Preserve the exact modifier IDs, PHIL selections,
  atom operations, base dictionaries and projected site chemistry.
- Add schema-1 preparation `modification_block_policy` evidence. Detailed
  native inventories record formal-charge attribute availability and null
  values; qualification separates unavailable readback from actual charge
  contradictions and never substitutes partial charges. Missing readback
  remains unqualified. Native failure summaries now show the recorded error.
- Record Cedar 07's successful source recovery and baseline interpretation,
  followed by the linked reader's missing-modifier failure. All 164 payloads
  verify. Exact returned-input replay preserves site plans and input bytes;
  the subsequent Cedar 08 native result is recorded above.

### Source-declared aromatic bond representation

- Correct the independent generation gate's false rejection of CGY's six
  source-declared aromatic ring bonds after eLBOW writes aromatic bond types.
  Generation-v4 admits only complete isolated alternating six-member C/N
  rings with explicit neutral ring charges, affirmative source bond flags,
  unchanged single-bond substituents and non-stereogenic ring bonds. No
  aromaticity perception, source rewriting or replacement targets are added.
- Preserve all raw comparison differences and numerical/stereochemical reviews;
  add policy-bound `bond_representation` evidence within schema-1 inspection
  receipts. Retain independent atom, hydrogen, charge and numerical rejection
  checks. The native diagnostic accepts completed source-retaining v3 and v4
  receipts and re-inspects their dictionaries under the current policy.
- Record Cedar 06's three completed source-retaining eLBOW executions and the
  CGY representation blocker separately from native bundle interpretation,
  which did not run. Offline replay prepares all four linked derivatives;
  Cedar 07 installed qualification remains pending. Source-recovery console
  output now identifies each blocked component and its recorded reasons.

### Source-preserving linked-state diagnostic

- Add explicit connectivity-selected DNA dictionary preparation, with source-
  preserving candidate requirements, graph-selected leaving atoms/hydrogens,
  source-derived DNA metadata, per-site modifiers and projected CIF Doctor
  audits. Require declarations for every same-code model site; retain OP2
  protonation and requested terminal phosphates. No PostMR adoption.
- Add opt-in detailed native monomer/proxy inventories and exact custom
  selection/target/weight coverage checks. Preserve the existing basic native
  inventory interface and schema-1 receipts; missing detail remains explicit.
- Add the source-bundled `06_Cedar` diagnostic for the exact returned 05 ZIP.
  Reuse existing whole-component generation when ReadySet lost source state,
  preserve all prior inputs, and test shared-code internal/free-OH contexts.
  Its returned generation-stage blocker and the next native retry are recorded
  in the source-declared aromatic representation entry above.
- Record Cedar 05's completed interpretation and the newly identified
  CGY/IMC/DX OP2-hydrogen loss separately from the four linked OP3 expectations.

### Explicit native bundle diagnostics

- Add a separate installation-bound `phenix.python` diagnostic for an exact
  model/CIF/PHIL bundle, with frozen input hashes, bounded execution and raw
  native-reader, atom-mapping and proxy evidence. Inventory successful native
  interpretation as REVIEW; unsupported APIs/parameters and failures stay
  explicit. No optimization, model replacement, ReadySet retry or adoption.
- Add a prefixed `05_Cedar` shuttle that binds an accepted generation receipt
  to the failed run's source audit and prepared PDB, preserves frozen runtime
  numerical precedence and ancillary parameters, and writes an external
  diagnostic bundle/receipt/review ZIP. Preserve explicit paths and offline
  inspect-only operation; refuse input/hash mismatches.
- Record the returned `04_Cedar` repeat: exact CIF values and all 37 PDB atom
  rows reproduce v3; only generation timestamps differ. Native interpretation
  and generic polymer-link qualification remain separate pending laptop checks.

### Visible shuttle identifiers and native source-retention evidence

- Prefix the CIF-generation shuttle, output session and review ZIP with a short
  delivery identifier; include the run token near the ZIP's beginning and print
  the delivery/policy in the console. Record the identifier additively in
  schema-1 metadata/receipts and preserve exact explicit builder output paths.
- Adopt leading identifiers for future user-facing ferries so truncated file
  cards do not hide the version. Preserve all older deliveries and runs.
- Record the v3 native IGU candidate: all 37 atoms, hydrogen attachments,
  normalized bond orders and formal charges retained, C2–N3 1.397 ± 0.030 Å.
  Numerical/metadata review and native polymer-link qualification remain
  separate; no dictionary was adopted or refinement rerun.

### eLBOW source-state retention and candidate review

- Require the installed valued `--pH` control and explicitly use its `low`
  input-chemistry retention mode. Record this as source-state preservation,
  with experimental pH and solution protonation unassessed. Preserve the
  hydrogen, charge, connectivity and declared-stereo rejection checks.
- Keep complete candidates with supported soft numerical findings at
  `CANDIDATE_REVIEW`; reject invalid/incomplete targets and unresolved plane
  compatibility. Preserve the assessor's findings without inventing strain
  thresholds or automatically adopting candidates.
- Record the completed Phenix 2.2.1-6174 RM1/GDIIS optimization separately from
  its chemical-state rejection: the collapsed IGU bond was restored, but default
  phosphate deprotonation changed the source. Update the human descriptor and
  machine-readable evidence; the source-preserving native retry remains pending.

### Installed eLBOW option compatibility

- Probe the selected eLBOW executable's help before numerical generation;
  select exact supported dashed/underscored aliases while preserving initial
  geometry, naming, hydrogen, chirality and optimization controls. Record help
  output, supported definitions, selected aliases and executable identity.
- Reject unavailable controls, failed help or capability races before chemistry;
  keep the source/frozen seed unchanged. Correct probe summaries so failed
  generation does not appear as a candidate awaiting review. Preserve the
  returned Phenix 2.2.1-6174 CLI failure as separate native evidence.

### General generated-dictionary quarantine and numerical candidates

- Generalize the returned IGU defect into exact coincident bonded-heavy-atom
  detection for numerical dictionaries, including positive-target collisions.
  Preserve graph-only source and achieved-model assessment boundaries; add atom
  identifiers to invalid bond findings and advance the assessor policy to v2.
- Diagnose and quarantine unusable generated generic components in PostMR,
  preserving trusted numerical inputs and native output. Emit an exclusive
  failure receipt; never fill in a zero bond with a guessed target.
- Add explicit whole-component eLBOW candidate generation from frozen chemical
  input and independently derived source ideal geometry, with bounded native
  execution and source/candidate graph, hydrogen, charge and numerical evidence.
  Discover eLBOW as an optional installation-bound capability. Candidates are
  not automatically adopted or used to retry ReadySet.
- Add a source-bundled native probe and returned-evidence record; update the
  human descriptor and editable figure. General source-state/native reader and
  polymer-link qualification remain pending the laptop candidate run.

### Fresh synthetic DNA mechanics recipe and shuttle

- Stage the exact 42-target combined K:X/B:S/Z:P/D:T DNA recipe from canonical
  W coordinates and copied donor files, including explicit full-chain sequence
  references, free 5′-OH preparation and exact input/edit receipts. Require all
  donor metadata before allocation; preserve originals and internal phosphates.
- Add a one-file source-bundled runner with isolated NASolve/NARestraints imports,
  configuration and fresh campaign outputs. Freeze AutoSol off, retain honest
  numerical/linkage blockers, and display space-group evidence in final output.
  Add opt-in native environment cleanup after campaign worker bootstrap.
- Document algorithm/tools, methods wording, evidence and limits; regression
  checks cover relocation and source preservation. Native execution is pending;
  generic automatic dictionary generation/adoption is not newly certified.

### Explicit campaign AutoSol opt-out

- Permit schema-2 recipes to set `autosol.policy = "disabled"` with a frozen,
  nonempty reason. Record the skip without invoking AutoSol; retain nucleotide
  anomalous classification, iodine diagnostics, observation arrays and Free-R.
- Refine the prepared PostMR model with experimental phases explicitly disabled
  and phase-free checkpoints for subsequent Doctor trials. Refuse reuse of an
  existing AutoSol execution/report. Keep schema-1 and conditional defaults
  unchanged; add relocated offline regressions and a human methods description.
  Native synthetic-model validation remains a separate live check.

### Human feature documentation and offline CCD shuttle

- Add a human/manuscript CIF Doctor overview with an adaptable methods
  paragraph, implemented-versus-planned scope, tools, references, and an editable
  SVG pipeline figure with its standard-library layout source.
- Require human feature descriptors to accompany substantial features and
  remain current with behavior, dependency and limitation changes; link this
  convention from the contributor contract and documentation map.
- Add a builder/template for a single-file, offline public CCD ZIP auditor.
  Embed the reviewed assessor and unchanged required reader definitions, verify
  all archive/source hashes, and write 36 audits into a fresh portable output
  folder without changing the laptop checkout. Graph-only source PASS and
  effective REVIEW remain distinct from native or scientific approval.
- Record the small reviewed upstream NARestraints metadata corrections and the
  subsequently authorized C5 whitespace cleanup. Keep frozen control provenance
  and downstream compatibility adapters; test both legacy and corrected DF data.

### CIF Doctor assessment and reviewed preparation

- Add deterministic offline component/restraint assessment and explicit
  `cif-doctor assess` commands for dictionaries or a frozen run/checkpoint.
  Inventory exact atom IDs, graphs, numeric terms, torsions, chirality and
  angle/plane compatibility; retain unassessed native/site/geometry layers.
  Compare explicitly selected same-code source/candidate declarations without
  guessing aliases, protonation or source authority. Preserve zero-sigma native
  constant-term conventions and signed torsion periodicities in the inventory.
- Record source screening before PostMR mutations, separate frozen source and
  runtime assessments before ReadySet, and the selected effective bundle after
  ReadySet. These receipts are report-only and do not add a campaign gate,
  change dictionary precedence or edit an existing run.
- Add explicit source-preserving preparation for supported torsion alternatives
  and the exact hash-scoped reviewed historical 5CM correction. Preserve original
  files, refuse overwrites and record before/after evidence; candidate creation
  does not adopt or qualify new chemistry.

### Machine-readable CIF Doctor implementation map

- Add the scientific/engineering blueprint covering exact chemical cases,
  deterministic assessment rules, bounded repair policy, ReadySet/PostMR hooks,
  site-linked chemistry, effective native proxies, geometry/stitching, caching
  and regression controls. Link it from the methods, documentation map and
  current handoff. Preserve snapshot hashes without duplicating active contracts.
- Keep collaboration/personality notes outside this repository document.
  Distinguish the 5CM C2/C2′ torsion defect from the 5IU C5/C5′ reader collision.
  This is implementation design, not a new runtime command, schema or repair.

### X11_18 alternative symmetry interpretation

- Record the user's analytical preference for X11_18 P4₃: inspection Rfree
  0.3418 versus 0.4859 in P2₁ (`P 1 21 1`). Preserve the two different
  processing datasets, frozen Free-R populations and existing Doctor review
  status; this comparison is not an automatic same-data winner selection.

### GeoTest campaign wrapped and coordinated Doctor scope

- Verify the corrected native laptop ferry: 462 included files, 138 declared
  compact omissions, nine completed workers and 14 successful native refinement
  processes. Six members are numerically ready, two remain Doctor reviews and
  one has no MR solution. The parser-only installation, original-code backup,
  free 5′-OH preparation, unchanged inputs and displayed space groups are verified.
- Close the GeoTest orchestration trial at the user's requested scope; retain
  provisional scientific status, X11_17's large Rwork/Rfree gap and the two
  X11_18 reviews. P4₃ selected models and P4₁ input headers remain separate.
- Plan one coordinated Doctor workflow for data/Free-R diagnostics, effective
  component/restraint assessment and model geometry/connectivity assessment,
  including guided sticky-end arm repair. Record the user's fractured-arm
  diagnosis as motivation; high Rwork alone does not establish its cause.
  Keep frozen Free-R flags, declared routing and true nicks/5′-OH ends intact.
  The deterministic restraint assessor remains the first implementation slice;
  geometry checking and stitching are planned modules, not current capability.

### GeoTest laptop rerun shuttle and space-group display

- Record the updated standalone shuttle's explicit `--install-parser-fix`:
  verify the returned laptop runtime, back up and atomically replace only the
  known Phaser parser source, then run a fresh batch. Unknown source changes
  block installation; the exact installed fix is a no-op on later launches.
  Preserve the laptop-specific curated-ligand source and existing runs.
- Add space group to the terminal final summary, CSV and Coot result menu.
  Prefer the displayed checkpoint/selected model's CRYST1, retain the exact
  input-MTZ space group separately, and label data-only fallback. Optional
  metadata failures do not change scientific verdicts; provenance carries
  declared artifact paths and hashes.
- Ninety-four adapter tests and 22 subtests pass; assembled installation,
  preparation and repeat staging pass with explicit offline fixtures. The
  subsequent corrected native rerun is verified above. Repo edits here are
  documentation; the standalone script remains the deliverable.

### Selected-model Phaser scores and GeoTest native results

- Fix MR gating to use the selected Phaser PDB's final TFZ-equivalent and LLG,
  rather than the first score in a solution-history line or an unrelated
  solution's score. Require its matching MTZ, record score-source provenance,
  and preserve failures when score association is ambiguous. Thresholds remain
  unchanged; existing reports and completed runs are not rewritten.
- Verify the returned 361-file full-auto GeoTest ferry: four ready refinements
  and one Doctor review. Both cohorts' selected outputs have seven final scores
  meeting the ≥8 gate, one borderline model and one no-solution case; three new
  candidates were stopped by the old score reader. Native continuation of those
  candidates remains pending.
- Record the two user-supplied Coot examples and planned guided arm connection
  under Scout/Topo Surgeon: declared strand routing, symmetry-aware preview,
  preserved true nicks/5′-OH termini and separately bounded geometry repair.
  This is distinct from the generalized CIF/restraint doctor and is not yet
  implemented. Coordinate, reflection and screenshot files are not committed.

### GeoTest declared-end preflight and full-auto adapter

- Verify the first ferry: eight placed models correspond to four MR passes,
  two borderline reviews and three failures. Four PostMR attempts stopped on
  undeclared terminal OP3; recorded placed-model groups are P2₁, P4₃ and P1.
- Record the user's linear 5′-OH chemistry and the updated standalone runner:
  audited terminal-phosphate removal before fresh native preflight/MR, eligible
  AutoRefine and bounded Refine Doctor, provisional checkpoint selection and
  exact Coot result viewing. Original inputs and the first cohort are preserved;
  no fake sequences or successful-status rewrites are used.
- Adapter receipt schema 2 and a frozen recipe describe this isolated workflow.
  Seventy-six offline tests and 20 subtests pass; native revised execution is
  pending. Native campaign input/recipe integration remains future work. These
  repo changes are documentation only; the runner is a separate deliverable.

### GeoTest first live report and continuation request

- Record the user's 8/9-good report across P2₁2₁2, P4₃ and P1, with exact
  member results/stopping points awaiting the ferry. Queue one-launch verified
  continuation through refinement, eligible bounded Refine Doctor and convenient
  result viewing; preserve completed MR and checkpoint lineage. This is a
  documentation-only plan, not an implemented extension or verified refinement.

### Generalized restraint doctor priority

- Queue the read-only assessor as the next development task using the returned
  5CM/DF/DP evidence, with historical 8RO/DE and failed 1AP challenge cases and
  valid controls before general repair claims. Retain the distinction between
  official 8RO, laboratory DE and the current curated 1AP source.
- Bound the remaining combined-model review and park optional further edits;
  keep GeoTest native execution/ferry pending. This documentation-only decision
  changes no runtime, schema, dictionary, scientific input or approval status.

### GeoTest exploratory batch adapter

- Record the optional standalone GeoTest script: isolated CIF/PDB intake,
  nested processing/model trials named from the outer folder, existing native
  stage gates, trust-model provenance and a compact review ferry. Native
  campaign CIF/no-sequence integration and live execution remain unvalidated.

### DP model base visual review

- Record user base visual PASS for the exact DP geometry output, with sugars
  explicitly unassessed by eye. Retain numerical sugar/termination review and
  full qualification as open; distinguish residual sugar torsions from the
  resolved N5 conflict and earlier checker-only failure.

### DP geometry trial returned

- Record the completed DP-specific bounded geometry run and verified 56-file
  bundle, with fixed within-trial manager and original inputs preserved.
  Record relief of the DP N5 conflict and preserved chirality/links, with modest
  residual strain. Queue Coot review of the exact new model; preserve the earlier
  visual PASS separately. The general read-only assessor remains unimplemented;
  no convergence, refinement or production full-auto claim is added.

### DP native interpretation passed

- Record returned DP native v2 PASS, verified 33-file evidence bundle, effective
  B:4 linkage/type and preserved original coordinates/other restraints. Queue a
  fresh 5×500 geometry trial with this manager from original pre-minimization
  coordinates; new geometry qualification remains pending. No native charge,
  convergence, refinement or production full-auto claim is added.

### DP native checker correction

- Preserve the blocked torsion-coverage receipt and partial checks. All 19 DP
  heavy torsions match after verified cctbx index/sign normalization; queue a
  checker-only v2 rerun with identical inputs/modifications. Record the lesson
  in `TOR-01`; no chemical change or native full PASS is claimed.

### DP candidate generated and reviewed

- Record successful v2 installed-reader preflight/generation and reviewed graph,
  H/charge/chirality preservation. Separate four aromatic annotation changes
  from unchanged explicit bond orders; audit broader numerical regeneration and
  retain dropped alias provenance.
  Queue native DP interpretation with complementary B:4 outgoing-link H/type
  handling; adoption and geometry qualification remain pending. Documentation only.

### DP seed-parser retry

- Record the blocked first DP generation: AceDRG misread single-quoted primed
  IDs, with source bytes unchanged and no candidate/adoption. Add consumer-parser
  agreement to `GRAPH-01` and queue a double-quoted seed plus installed-reader
  preflight before retry. The prior model's user visual PASS is preserved;
  numerical repair remains open. Documentation only.

### CIF/restraint audit methods

- Capture automatable audit methods, known 5CM/DF/DP cases and proposed evidence
  schema/review boundaries in one linked design document. This records the
  implementation plan; no runtime audit or automatic repair is added.

### Combined geometry trial completed

- Record returned bounded minimization, verified 57-file bundle, preserved
  manager/original inputs and before/after metrics. The geometry target fell
  97.45% and chirality signs were retained. Record the demonstrated DP angle/plane
  conflict. Record the user's Coot visual PASS for the exact relaxed model; next
  is a disposable DP candidate/audit before a clean rerun. Convergence and full
  numerical qualification remain open. No MTZ/Free-R
  refinement or production full-auto result is implied. Documentation only.

### Repaired native interpretation

- Record returned 5CM/DF repaired-native PASS, verified 34-file evidence bundle,
  preserved original inputs/custom restraints and unchanged 868-atom model.
  Next is disposable minimization with the same interpreted geometry manager;
  achieved geometry and MTZ/Free-R refinement are not claimed. Documentation only.

### Combined geometry recovery plan

- Record the checksum-verified linked geometry bundle, confirmed active 5CM
  atom-reference defect, defective effective ReadySet DF, and source-audited
  native-generated DF candidate. Neither candidate is yet adopted in a corrected
  native interpretation; geometry minimization remains pending. Define the
  fresh diagnostic, linkage/coverage checks and subsequent geometry trial.
- Preserve the verified local Cedar head and distinguish mixed source phosphate
  states from an inferred pH correction. Expand the post-geometry audit plan
  into staged deterministic assessment and separately validated, policy-bounded
  generation/continuation; no AI is required for ordinary passing cases.
- Documentation only: no runtime/schema, source CIF, frozen model, observation,
  Free-R or workbook change; no raw scientific bundle committed.

### Planned grouped processing inputs

- Record shared parent-folder models with separate processing subfolders,
  including alternative space-group solutions, as a future campaign capability.
  Distinguish current shallow discovery from grouped inventory, explicit model
  inheritance and separate MR comparison. Preserve per-candidate inputs and
  results; no parser, CLI/schema or runtime behavior changes in this update.
- Record the approved NARestraints documentation PR #5 merge; its released
  scientific source and workbook are unchanged.

### October 10 documentation reconciliation

- Record the returned combined W preflight/Phaser/PostMR, fresh IMC structural
  audit, generic linkage diagnostic and exact restraint-coverage results.
  Geometry qualification and a fresh ordinary full-auto run remain pending.
- Reconcile current source/ReadySet precedence and implemented recipe-controlled
  full-auto behavior across contracts; replace superseded live queues with
  authoritative pointers. Preserve shortened documents and development-intent
  records byte-for-byte in the dated history archive; older changelog entries
  below describe their original implementation checkpoints.
- Queue a SMILES-assisted molecular-graph audit after the combined geometry
  trial and before Topo/Scout. Record requested PDB/coordinate-mmCIF support and
  an explicit trusted-model/no-sequence mode before the blind AlphaFold trial;
  these are planned capabilities, with no new runtime option in this change.
- Documentation checks: active links, intent JSON and exact archive hashes pass.
  Isolated Linux/Python 3.12 regression returned **981 passed, 2 skipped,
  257 subtests passed (29.50 s)**; this is not a new Phenix/Coot native receipt.
- No source, dictionary, workbook, native run, reflection or Free-R changes.

### Cedar native probe scope

- Record successful installed-source lookup for IGU/IMC/CGY/DX and the native
  IGU construction result. Correct the ad hoc mutation-probe inventory to
  expect OP3 absence; preserve production phosphate cleanup and explicit
  terminal intent. Refresh the native ledger with the existing 983-test
  receipt and verified source hashes. ReadySet/native PostMR qualification
  remains pending. No runtime, dictionary, coordinate or schema changes.

### Phenix CCD symlink discovery

- Count unique resolved CCD paths in the configured Phenix installation.
  Phenix 2.2.1-6174 exposes its Python 3.11 library through a `python3.1`
  symlink; treating both paths as separate dictionaries falsely blocked
  generic lookup. Separate files still fail as ambiguous, even with identical
  bytes. Curated precedence, identity checks and numerical-generation gates
  are unchanged; no CIF, placement recipe or artifact schema changes.
- Record the user's exact installed-source hashes: bundled C38 and 5IU match
  Phenix byte-for-byte; S6G differs only in trailing whitespace, verified by
  reproducing the installed hash from normalized bundled bytes. DF/A1AAZ
  also matches after component-label and line-end normalization; preserve
  the short-label bridge and the user-reported DF-to-A1AAZ deposition history.
  The source audit is complete; DE geometry remains unresolved, and no CIF
  or placement rule is removed. Add a symlink regression and retain the
  genuine-ambiguity check. User-local validation at
  `1443979` passed **16 focused + 31 subtests (2.45 s)** and **983 full +
  257 subtests (80.81 s)**. Native preparation/geometry validation remains
  separate and pending.

### Cedar regression diagnostic alignment

- Update the construction-hop regression to expect the specific missing-curated-DZ
  diagnostic. It still requires `FileNotFoundError`; curated dictionary precedence,
  the no-fallback guard and runtime behavior are unchanged. The old expectation
  was the sole failure in the user-local full suite at `d1bf3ea`. The corrected
  `ccb7608` passed **982 tests + 257 subtests (75.90 s)** locally; native
  ReadySet and combined-family validation remain separate gates.

### Bundled ligand provenance audit

- Distinguish parameterized adaptations, identity/construction exceptions and
  unchanged supplier resources in the existing component guide. Confirm the
  unchanged 5CM source and 5IU parser defect; restore the unresolved DE geometry
  warning from the archived review. Dictionary bytes, lookup policy and runtime
  chemistry are unchanged; installed-source comparison remains pending.
- Clarify lab Q/DQ -> S6G and S/DS -> N-linked IMC intent, distinguishing the
  currently implemented Q alias from pending DQ/S/DS aliases and the different
  C-linked hachimoji S chemistry. Separate sulfur/iodine placement from CIF
  defects; record the duplicate-path diagnosis needed for installed CCD lookup.
  No alias, coordinate, dictionary or resolver implementation changes here.

### Contributor continuity and branch lifecycle

- Consult the existing documentation and validation history before inferring
  project intent. Prefer one active development branch and everyday checkout,
  integrate after scoped scientific gates pass, and promptly retire audited
  completed branches/worktrees. Runtime behavior and scientific gates are unchanged.

### Modified-base W Saenger overlays — isolated native integration PASS

- In new W PostMR derivatives, match actual prepared modified bases against
  the reviewed NARestraints v1.1.3 atom-role workbook and replace **only**
  incompatible legacy Saenger class blocks with one run-local explicit
  NARestraints pair input. Retain all unaffected canonical W pairs, normal
  stacking, input/model/Free-R provenance and D:1 phosphate protection.
- With B:S, K:X and D:T on three additional distinct W sites, the new
  workbook-backed regression exercises four named modified families
  **simultaneously**, including Z:P in the existing Std_padd range and the
  already tested 5CM:G / DF:A off-pair context. This extra regression still
  needs user-local execution on the integrated Pine head; no native
  mixed-family run or missing-CIF fabrication is claimed. The first local
  mixed-fixture run correctly **failed closed** for an incorrectly chosen
  `S6G` thioguanine (B:G instead of B:S): **39 passed, 1 failed,
  2 subtests passed**. The user's corrected Benner S candidate **IMC**
  replaces S6G in the still-unexecuted revised regression; the test now
  asserts the actual S workbook category and expected bond counts.
  `IMC.cif` remains absent from committed NASolve resources.
- The original isolated W Z:P+5CM:G+DF:A patch passed 34 focused and 961 full
  NASolve tests + 224 subtests, native Phenix numerical SOLVED/refine-001,
  frozen inputs OK, and user Coot visual inspection of bonds/planes PASS.
  Historical attempts, original W resource and upstream NARestraints workbook
  remain untouched. Experimental chemistry is not proven by the donor data.

### Pathless campaign result viewing — tested

- An **explicit single-dataset** `campaign run` now selects its verified,
  viewable numbered AutoMR run as the **machine-local active workspace run**
  on a successful/pause-for-review stage boundary. A following bare
  `nasolve show` opens that run's **current selected checkpoint**, not an old
  MR run, while still respecting the explicit `--checkpoint` and `--stage`
  overrides and not altering scientific checkpoint selection or user approval.
- `nasolve show` also works after `workspace use DATASET` (without an active
  run) by selecting the dataset's last numbered readable run. It never scans
  unrelated datasets or silently guesses a campaign target.
- Multi-dataset runs, blocked/drifted/unviewable stages and explicit
  `campaign run --no-activate` do **not** overwrite active workspace state.
  The activation is a convenience stored in user configuration only, not in
  the frozen plan, run directory, Free-R, Coot models or checkpoint registry.
- The earlier explicit `show RUN --checkpoint refine-001` printed
  `refined_001.pdb` and matching refined maps correctly. This patch addresses
  stale active-workspace selection, not an unverified corruption of Coot's
  actual loaded model or window focus. User-local focused 59 tests + 30 subtests and full 960 tests + 226 subtests passed.

### NARestraints 1.1.3 released dependency

- Use the immutable [NARestraints v1.1.3](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3)
  Git tag as NASolve's declared Python dependency. It fixes upstream Z:P
  and K:X geometry-role orientation and modified-base stacking, preserves
  B:S and D:T roles, and retains the original committed Ligands.xlsx.
- The native W Z:P+5CM:G+DF:A integration path reached numerical SOLVED
  with a separate candidate NASolve Saenger overlay and user Coot visual PASS.
  Source-native 1W5/1WA alias conversion and independent B:S/K:X/D:T
  native matrix checks remain separately pending.
- Updating dependency metadata does not mutate the user's existing installed
  .venv, original dirty NARestraints source checkout, frozen inputs or
  completed scientific runs.

### Reviewed long deposition component names in annotated sequences

- Exact `(A1AAZ)` token remains frozen literally but becomes native PDB residue
  **DF** at PostMR preparation via the reviewed DF deposition-code mapping;
  requested/prepared provenance is explicit. Other long CCD tokens still stop
  rather than being truncated or chemically guessed. Added a W Z:P + modified
  off-pair-site paired W sequence regression (5CM:G, DF:A, C:G, Z:P). Native chemistry remains to be tested.

### Annotated CCD sequence tokens

- Chain-labelled FASTA, `CHAIN = SEQUENCE`, inline `[sequences]`, frozen campaign
  targets and sequence-family/thread overlays accept `(CCD)` as one residue.
  Validate literal modified-component tokens against the ligand registry;
  ordinary one-letter sequences retain their previous meaning and behavior.
- AutoMR sequence-length checks and PostMR target construction now count parsed
  residues rather than characters. Keep exact per-site chemistry and provenance;
  `[mutations]` retains its higher-precedence per-site declarations.
- Explicitly reject long CCD targets at the PDB-only native-emission boundary,
  rather than silently truncating or inventing equivalences. Dictionary, model,
  phosphate and experimental-evidence gates are unchanged; no historical runs
  are rewritten.

### Recipe-controlled autonomy and component lookup

- Added opt-in preset schema 2 full-auto workflow: preserve borderline MR REVIEW
  while trialling downstream refinement, optional unaccepted-phase fallback,
  recipe-owned Doctor endpoint and separately audited provisional selection of
  its verified passing recommendation. Schema-1/guarded behavior is unchanged.
  No automatic USER_APPROVED state, global Rfree search or old-plan upgrade.
- Fixed ideal-coordinate CIF atom parsing that confused C5' with C5 and produced
  DiU's false 8.843-A C5-I5 distance; supplied dictionary coordinates are unchanged.
- Added a pinned parameterized 5CM resource/DC route and connectivity-scoped
  phosphate handling; no NARestraints workbook or pair-class changes.
- Record iodine expectations and actual phasing/anomalous-refinement diagnostics
  for ordinary refinement and the presented Doctor trial. Insufficient anomalous
  data is flagged rather than fabricated.


### Fixed

- An explicit campaign `--through refine-doctor` now continues a newly
  encountered AutoRefine REVIEW into campaign-owned Doctor in the same
  invocation. Entry, resume and post-stage progression share the existing
  endpoint-aware eligibility rule. The default AutoRefine endpoint, other
  review/failure stops, receipt checks, pause handling and non-selection
  of Doctor recommendations are unchanged. No schema migration.

### Dictionary compatibility

- Generalized recognized CCP4 alternative-torsion conversion beyond 1AP,
  including the effective ReadySet bundle. Preserve primary sigma with explicit
  unequal-uncertainty provenance rather than claiming lossless weight conversion.
- Freeze parameterized input dictionary authority independently of phosphate
  profiles; retain construction-only CCD fallback to ReadySet and portable
  effective refinement/view references. Unknown representation conflicts warn
  and remain for native interpretation rather than receiving guessed repairs.
- Added a pinned parameterized DZ dictionary and its DC construction route,
  plus connectivity-selected DZ linked-phosphate handling without reinterpreting
  legacy 1AP profiles. Existing category intermediates are unchanged.
- Standing 1W5 -> DZ / 1WA -> DP conversions remain a separate pending slice.

### Changed

- Generic modified-component construction now selects temporary Coot parents by
  the user-reviewed sheet/category policy: Z/S/K/unique -> C, P/B/X -> G,
  D/I -> A, with C for an unclassified intermediate. A recognized Source sheet
  takes precedence; legacy records use Base Analog as the category. DNA/RNA
  selects the corresponding sugar form. Existing curated recipes retain priority.
  This replaces the proposed N9/purine-pyrimidine inference gate, without changing
  final component identity, NARestraints mappings/recipes, or frozen old runs.
  Final dictionary and geometry validation remain separate; no automatic bond
  repair, tautomer conversion, new dictionary or torsion policy is introduced.

- Added schema-1 semantic `terminal_geometry_protection` checkpoint provenance. Protected sites, sigma, Phenix-derived ideal source, mechanism, and the run-local protection restraint artifact now inherit with refinement/manual children; attempts to stack a second protection record fail closed.
- Generalized the OP3-specific policy into an explicit standard-phosphodiester backbone contract. `five_prime_phosphate_sites` is the preferred user-facing name (legacy `allow_op3_sites` remains readable). PostMR now treats a requested 5'-terminal phosphate as the complete P/OP1/OP2/OP3 group, preserving a complete group, completing missing OP3 from existing P/OP1/OP2, or seeding a whole missing group from O5'-C5' with recorded idealized starting geometry. Partial ambiguous groups still fail closed.
- Terminal-phosphate native geometry remains owned by Phenix. NASolve now audits declared terminal phosphates from Phenix geometry output and provides provenance-tracked local `action = change` protection using Phenix-derived ideals; NARestraints remains responsible for reviewed pairing/stacking geometry and does not duplicate native terminal-phosphate restraints. Automatic first-AutoRefine protection is now implemented and live-validated: NASolve obtains native ideals from a pre-refinement `phenix.pdb_interpretation` geometry snapshot, applies six local sigma=1-degree P-centered `action = change` restraints, freezes the source geometry/log/protection artifact into checkpoint provenance, and inherits that protection without duplicate stacking.
- Added site-scoped `experimental_passthrough` for explicitly declared non-standard backbones. Standard phosphate rules are skipped only at those sites; no custom linkage is inferred. Passthrough requires explicit user authorization, persists in run/campaign provenance, and has a two-step `backbone-review` Coot/confirmation workflow that records the inspected model hash without erasing provenance. Reviewed custom backbone recipes and 3'-phosphate construction remain future work.

- Added explicit `[chemistry] terminal_phosphate_sites` to recipe cards. The
  built-in W/5W6W card is now version 1.1.0 and declares D:1, confirmed by Simon
  as a designed 5-prime phosphate. Standalone W selection and campaign planning
  resolve this same card; custom cards declare their own lists. Dataset
  `allow_op3_sites` replaces recipe sites, including an explicit empty override.
- Freeze recipe phosphate origin/id/version/hashes beside the effective sites in
  AutoMR and campaign records. Report sites in AutoMR and campaign plan/status.
  Existing frozen runs/plans never gain permissions from a later recipe version.
  Fresh PostMR attempts may construct an explicitly requested 5-prime terminal
  phosphate under the current guarded chemistry contract; old runs remain immutable.

- OP3/O3P terminal intent is strictly explicit and is frozen into
  AutoMR/campaign provenance. For a requested 5-prime terminal site, PostMR may
  preserve a complete group, add missing OP3 to P/OP1/OP2, or construct a wholly
  missing P/OP1/OP2/OP3 group from the local sugar frame. Ambiguous partial
  groups, unrequested unlinked OP3, cyclic/incoming-link conflicts, and an extra
  oxygen on an internal phosphate still fail closed.
- Replaced the bundled raw 1AP CCD graph with the tested parameterized monomer
  library dictionary, preserving numerical values and adapting its group to
  DNA. New PostMR 1AP profiles generate residue-selected OP3 modifications and
  freeze checksummed refinement/view artifacts. ReadySet cannot supersede the
  reviewed 1AP definition or swallow modification files during checkpoint
  creation. Normal dictionaries and coordinate/raw run evidence remain intact.
- Added phosphate/profile gates to AutoRefine, Doctor triage and manual imports;
  retained inherited modifiers after relocation, with missing or changed
  artifacts failing closed. Combined dictionary inputs merge their component
  lists instead of concatenating conflicting data blocks.
- NASolve now installs the released NARestraints `v1.1.2` dependency. No DE,
  sulfur pair-target, observations, Free-R, or NARestraints workbook changes are
  implied by this backbone work. ReadySet/Phenix interpretation and live
  refinement of a wholly constructed terminal phosphate have now been exercised;
  the earlier 1AP integration diary is archived under `docs/history/`.

### Added

- Added an explicit sequence-reference target compiler with the reviewed
  W-scaffold reference, chain/residue correspondence, thread/dataset overlays,
  assignment provenance and read-only inventory comparison.
- Added opt-in standalone `[automr] sequence_reference` integration. Fresh
  AutoMR runs freeze exact reference bytes and effective targets; PostMR reuses
  existing mutation routes and audits complete prepared residue identities.
  Snapshot/intent drift fails closed. Ordinary W defaults and legacy runs are
  unchanged. Campaign planning now snapshots an explicitly selected per-dataset
  reference into content-addressed resources; campaign preflight consumes that
  frozen copy rather than reopening the installed or dataset source.
- Added explicit campaign sequence threads through root
  `nasolve-campaign.toml`. Threads freeze named dataset membership, inherit the
  reviewed W sequence reference plus shared chain/site overlays, and preserve
  provenance into run-local sequence-family targets. Dataset declarations remain
  more specific. Membership does not imply MR-model compatibility or reuse.
- Added explicit standard-frame model providers through `[automr] model`
  and `automr --model`. A forced PDB may come from the dataset or selected frame
  catalogue, is frozen with structured provider provenance, and retains the
  frame's symmetry/recipe/sequence context. Forced filenames never imply pair
  compatibility; required W PostMR sites are checked literally before MR.
  Campaign plans snapshot the exact model bytes and provider so execution remains
  portable after the original model/catalogue disappears.
- Added checksum-verified search-model mismatch provenance for runs with a
  complete explicit residue target. The frozen comparison records chain/site
  inventory, missing/unexpected sites, literal residue mismatches, and the target
  source layer for each expected PostMR correction. It is descriptive only:
  no compatibility score, mutation-route guarantee, donor eligibility, or
  automatic model reuse is inferred.
- Added checksum-verified model compatibility fact sheets for every fresh
  AutoMR run. They record provider/frame declarations, exact candidate
  chain/residue inventory, target-dependent site/identity relations when
  available, mirror-transform state, recipient terminal/backbone chemistry and
  recipient symmetry/copy-number evidence. Unknown dimensions remain explicitly
  unknown. Schema 1 forbids scores, overall compatibility verdicts, donor
  eligibility and automatic reuse authorization.
- Added explicit provider-side `[automr] model_family` declarations for named
  search models. The declaration is bound to the selected model, frozen through
  campaign relocation, and compared literally with an explicit recipient
  sequence-reference identifier when both exist. Frames, filenames, sequence
  threads and similarity never create family membership implicitly, and the
  resulting SAME/DIFFERENT fact still carries no donor-eligibility decision.
- Added read-only checkpoint model-candidate descriptors as a prerequisite for
  future Campaign Doctor rescue. Descriptors verify checkpoint lineage, model
  and source-observation checksums, literal residue inventory, frozen chemistry,
  source-provider provenance and complete sequence-family target context when
  available. Checkpoint models are compared afresh with the frozen target.
  Local checkpoint reusability is recorded separately from cross-dataset donor
  eligibility, which remains null; no model is selected, exported or reused.
- Added a read-only donor-checkpoint versus recipient-run comparison layer.
  It re-verifies Fern donor provenance, consumes only the recipient run's frozen
  AutoMR target/context, compares literal donor residue inventory to the
  recipient target, and records mode/frame/reference/mirror/symmetry context as
  separate descriptive dimensions. Scores, ranking, donor eligibility,
  recipient compatibility, rescue authorization and automatic reuse remain
  explicitly unset/false.
- Clarified that experimental-family membership and MR-model reuse eligibility
  are separate, and that a metal-adapted scaffold does not imply metal pairing.

- `show` now opens an additional anomalous difference map at 3 sigma when
  Coot finds `ANOM`/`PHANOM` in the selected map MTZ or that checkpoint's
  declared refinement MTZ. This also applies to Refine Doctor inspection and
  compatible manual-checkpoint ancestors, irrespective of whether f'' was
  refined. Existing overlays are reused; ordinary maps and their controls are
  preserved. Startup diagnostics record loaded, reused, absent, or error.
- Refine Doctor now tries a bounded mean-data recovery list including
  coordinate-only and group-B-only siblings. Anomalous trials explicitly fix
  wavelength-calculated scattering or refine f'' alone. `--max-trials` defaults
  to five; it and `--cycles` accept 1-10. Trials stop at the first numerical
  pass, technical failure, or budget. Additive reports preserve scattering
  provenance, skipped-recipe reasons, descriptive ranking and inspection steps.
- Unresolved Doctor inversions now remain `REFINE_DOCTOR_REVIEW` (exit 2), with
  a separate inspection candidate. They no longer endorse the source or choose
  a review branch by its R-factor gap. Unavailable Free-R audits stop trials;
  failed/incompatible outputs cannot win by favorable printed statistics.
- Documented the proposed Refine Doctor triage sequence for noisy mean-data
  refinement, conditional anomalous recipes, and campaign stop/inspection
  rules, distinguishing the implemented standalone options from future work.
- Added foreground sequential `campaign run`, stage boundaries, pause requests
  and explicit fresh-attempt retries for frozen schema-1 plans. Scientific
  stages retain their existing gates; blocked and review datasets stop locally
  while other selected datasets continue. Separate schema-1 execution records
  preserve attempt/run ownership, stage results, process identity and recovery
  diagnostics. Resume verifies completed artifacts, refuses to overwrite
  incomplete work, and preserves checkpoint lineage. Campaign status now shows
  exact runs, next stages and checkpoints; numerical success still requires
  model/map inspection. Execution initially supports macOS/Linux.
- Added schema-1 project presets and a built-in `5w6w` planning policy, with
  strict TOML validation and checksummed local resources. Added `preset check`,
  `campaign plan` and read-only `campaign status`: campaigns freeze dataset
  selection, configuration, input hashes and portable model/preset snapshots,
  retain blocked datasets with diagnostics, report duplicate observations and
  detect changed or missing inputs after relocation. These commands plan input
  and model selection; scientific preflight and execution remain separate
  commands. Existing stage and checkpoint schemas are unchanged.
- Published the DOHU input dataset (configuration, authoritative MTZ, autoPROC/STARANISO
  CIF, and summary) for collaborator reruns. Added `examples/README.md` and an
  eight-file SHA-256 manifest covering DOHU and the existing dated QiC example.
  The uploaded short-name QiC inputs match that existing example byte for byte;
  no duplicate dataset or new run history is added. Input bytes are preserved.
- Added local dictionary construction for modified-residue mutations with one
  unambiguous NARestraints record and a supported DNA/RNA construction parent.
  Included `OHU.cif` supports the D:OHU example. Curated overrides take priority;
  missing dictionaries are not downloaded automatically.
- Added Phenix 2.2.x to the file-scoped Data Manager selector policy, alongside
  2.1.x; 1.20.x retains legacy explicit selectors. Other version families still
  stop before allocating refinement state.
- Added a two-stage PostMR phosphate audit. Verified internal OP3/O3P leaving
  atoms are removed before NARestraints and after ReadySet, authorized terminal
  oxygens remain (see explicit recipe/dataset policy above), raw products are preserved, and measured geometry/removals are
  recorded under `phosphate_cleanup`. Ambiguous or damaged phosphates stop
  preparation instead of receiving guessed coordinate repairs.
- AutoSol reports now record an optional checksummed density-map reference,
  availability status, and diagnostic independently of phase acceptance.

- Added a tracked POSIX `./nasolve` source-checkout launcher. It resolves
  symbolic links, uses the checkout's `.venv` by default, accepts an explicit
  `NASOLVE_PYTHON`, and scopes `src` path injection to the launched process.
- Added portable run, dataset, and repository artifact anchors. Newly created
  checkpoint registries no longer depend on a collaborator's checkout path.
- Added compatibility rebasing for legacy run reports containing absolute
  paths from another computer.
- Added `nasolve workspace use`, `status`, and `clear`. An active dataset/run is
  stored in the existing user configuration, allowing stage commands to omit
  repeated paths.
- Added collaboration and AI-review guidance in `AGENTS.md`,
  `docs/collaboration.md`, and the pull-request template.
- Added a frozen SHA-256 for authoritative reflections to new AutoMR reports.
- Added a checksummed, run-local `Model/seq_base.txt` snapshot for new standard
  frame runs when the selected catalogue supplies it, so conditional AutoSol
  can continue without the source catalogue.
- Added SHA-256 values for AutoSol heavy-atom and refinement-phase outputs.

### Fixed

- Checkpoint listing now validates and displays an uninitialized PostMR root
  without creating a registry or directories; existing registries are read
  without migration. Modifying checkpoint operations still initialize normally.
- Standalone AutoRefine prints a shell-quoted inspection command for its exact
  result checkpoint when the existing `show` resolver can resolve its model and
  maps, including unselected results and recorded map fallbacks. Resolution
  failures are reported explicitly, and failed results no
  longer receive a generic suggestion to select them.

- ReadySet exit status 0 with the explicit `No unknown residues` result is now accepted as a successful no-op when Phenix writes no `*.updated.pdb`. NASolve preserves the already-prepared model, still runs its phosphate/atom-count audits, and records the no-op output mode; missing ReadySet output without that explicit success condition still fails closed.

- Refine Doctor's interactive `i` answer now opens the recommended checkpoint
  in Coot and returns to the same selection prompt. Answers take effect after
  Enter; only `y` selects a checkpoint. Declining, blank input, EOF or Ctrl-C
  preserves the current selection, and an inspection-launch error allows a
  retry. Printed inspection/selection commands now quote paths with spaces.
- AutoSol now uses fully qualified PHIL parameter paths, including nested
  phasing, model-building and general settings. This fixes Phenix 2.2 rejecting
  the ambiguous `data=` argument before reading inputs. Standalone and campaign
  AutoSol retain the same MR model, anomalous labels, wavelength and no-building
  policy. The external-tool fixture now rejects abbreviated parameter names.
- Campaign worker shutdown now recognizes macOS process groups containing only
  exited, unreaped workers when group probes return `EPERM`. Cleanup still
  requires verified inactivity, reaps its owned child and checks the group
  afterward; live or unidentified groups retain the existing error and retry
  safeguards.
- Curated residues already present in a model retain their dictionaries and
  component-identity records even when no mutation is needed, including
  nonstandard modified-pair preparation.
- PostMR phosphate cleanup now tolerates reused atom serials when full atom
  identities are unambiguous. Atom-associated records are removed by identity
  within their model/TER segment; unrelated atoms sharing a serial survive.
  Affected CONECT records still stop preparation if their endpoint serials
  cannot be resolved uniquely. Phosphate geometry guards are unchanged.

- Corrected view/AutoSol test expectations for canonical paths on macOS, where
  `/var` aliases `/private/var`. The affected tests now use an explicit symlink
  fixture on every host, preserving relocation and checksum assertions while
  checking resolved output paths. Runtime path resolution is unchanged.

- `show` now follows the selected current checkpoint, including manual and
  PostMR nodes. Newer unselected attempts do not replace that view. Manual
  models inherit clearly labelled ancestor maps only with matching observations.
- PostMR and AutoSol views now load the prepared model and ligand dictionaries.
  PostMR prefers accepted AutoSol density when available; AutoSol displays its
  density-modified map and separate heavy-atom overlay. Console and launch
  records identify the model and map sources, with missing/corrupt declared
  sources reported explicitly.

- AutoRefine now omits unsupported Phenix Data Manager Miller-array blocks on
  Phenix 1.20.x while retaining the exact observation, Free-R, and optional HL
  phase file/label selectors on the command line. Phenix 2.1.x keeps the
  file-scoped Data Manager block that prevents ambiguous MTZ-array selection.
- Refine Doctor now passes the same version-derived reflection-selector policy
  to every bounded AutoRefine branch.
- Fresh-terminal source launches no longer depend on macOS Python loading the
  editable-install `.pth` file; this avoids `ModuleNotFoundError: nasolve` when
  that metadata carries the hidden file flag. The launcher also places the
  checkout package ahead of the current directory, so an unrelated
  `nasolve.py` cannot shadow it.
- Bound AutoRefine observation, Free-R, and experimental-phase Miller arrays
  explicitly to their source MTZ files through the Phenix Data Manager. This
  fixes Phenix 2.1 preflight failures when an MTZ contains multiple equally
  suitable observation arrays, such as `IMEAN,SIGIMEAN` and anomalous
  intensities.
- Committed PostMR runs can now resolve their prepared model, authoritative
  observations, restraints, Phaser outputs, and optional AutoSol inputs after
  the repository is cloned or moved.
- Legacy paths now prefer the selected checkout even when the collaborator's
  old checkout still exists, understand Windows/POSIX path forms, and reject
  traversal or ambiguous rebases.
- AutoRefine recovers approved AutoSol phases after relocation when the root
  checkpoint was created before AutoSol completed.
- AutoRefine now fails closed when an approved phase source is unavailable,
  instead of silently continuing without the requested phases.
- Malformed saved workspace, run-report, and checkpoint JSON now produces a
  guarded NASolve error instead of an uncaught type exception.
- Coot views now fail closed when a reported map, primary refinement MTZ, or
  required ligand dictionary is missing or fails checksum validation.
- AutoSol and Coot now verify available frozen model/data checksums before
  consuming relocated artifacts.
- Legacy AutoSol runs recover the exact declared frame's `seq_base.txt` after
  relocation even when the historical pair-model filename no longer exists;
  the selected checkout wins while an older checkout is still present.
- Coot scratch creation rejects unsafe checkpoint path components and existing
  symlinks that could redirect logs, launch records, or backups outside a run.

### Changed

- Every AutoRefine checkpoint and round report now records the discovered
  Phenix version and the selected `legacy-explicit` or
  `data-manager-file-scoped` reflection-selector mode. Refine Doctor reports
  record the same provenance. Unknown, malformed, and unvalidated Phenix
  version families stop before allocating a refinement or Doctor directory.
- AutoRefine reuses the checksum produced by mandatory phase validation when
  writing the child checkpoint, avoiding a second full read of the AutoSol MTZ
  in each round. A stable file-identity check before and after Phenix rejects
  phase replacement, modification, or deletion during the external process.
- AutoRefine checkpoint serialization hashes each unique output file once, so
  legacy Phenix layouts that use one MTZ for maps and refinement reflections
  no longer read that potentially large file twice.
- AutoRefine now writes file-scoped Miller-array selections into
  `autorefine.params` while retaining the existing `xray_data` refinement
  parameters for compatibility.
- Separate AutoSol phase files receive their own file-scoped
  Hendrickson-Lattman label selection.
- `automr` uses the active workspace dataset when its dataset argument is
  omitted. `postmr`, `autosol`, `autorefine`, `refine-doctor`,
  `checkpoints list`, `checkpoints add`, `checkpoints use CHECKPOINT`, and
  `show` can use the active run.
- Checkpoint schema 2 uses `anchor` plus `relative_path` (or an explicit
  `absolute_path` fallback), SHA-256, and size. Refinement review outputs such
  as maps, reflection/mmCIF files, metrics, and logs use the same references.
- A newly allocated AutoMR run becomes active automatically. Explicit one-off
  paths passed to later stages do not silently change the active workspace.
- Machine-local Coot GUI scratch and PostMR Coot backup directories are ignored;
  portable stage artifacts remain visible for deliberate commits.

### Tests

- Doctor triage regression coverage includes the QiC inversion ranking case,
  ordinary IMEAN fallbacks, fixed and f''-only scattering, alternate selections,
  missing prerequisites, unavailable audits, failed external runs, budgets,
  immutable sibling lineage and inspection without selection. The complete
  local suite passes 393 tests and 129 subtests, with two existing platform
  skips. New Phenix recipes still require live validation on the user runtime.
- The assembled fixes pass 225 tests. The full local run with
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` also passed 51 subtests; the user
  confirmed 225 passing tests on the Apple Silicon checkout.
- On 2026-09-09, DOHU `AutoMR/run_004` completed AutoMR, PostMR, and a full
  five-cycle AutoRefine execution with Phenix 2.2.1-6174 and Coot 1.3.3:
  TFZ 14.30, final Rwork/Rfree 0.147/0.209, and current checkpoint `refine-001`.
  The user confirmed successful Coot inspection. The
  [validation record](docs/validation-dohu.md) preserves the raw clashscore,
  lattice context, execution details, and limits of this check.
- Added coverage for current/manual checkpoint views, AutoSol map provenance,
  relocated and symlinked paths, and phosphate cleanup with duplicate serials
  and atom-associated records.
- Added Phenix 1.20.1-4487 compatibility regressions that emulate rejection of
  the Data Manager block and verify exact anomalous/mean observations, Free-R
  flags, separate HL phases, automatic target selection, Doctor propagation,
  and report/checkpoint provenance without production use of `--unused_ok`.
- Added fail-before-mutation coverage for unknown or unvalidated Phenix
  versions and retained the Phenix 2.1 file-to-array binding regressions.
- Revalidated the post-patch `data-manager-file-scoped` path from a relocated
  temporary Q:iC run with Phenix 2.1-6048. Dry-run preflight and a one-cycle
  refinement both exited successfully; the intentionally short refinement was
  retained as `AUTOREFINE_REVIEW` at Rwork/Rfree 0.177/0.160.
- Added source-launcher coverage for fresh terminals, symlink resolution,
  argument and working-directory preservation, `PYTHONPATH` scoping, explicit
  and default interpreters, current-directory import shadowing, and
  missing, directory-valued, and non-executable interpreter diagnostics.
- Added hash-call regression coverage for inherited/recovered AutoSol phases
  and shared AutoRefine MTZ outputs, plus phase drift during Phenix, immutable
  failed-attempt retention, and successful next-round recovery.
- Added relocation coverage for reports created beneath a collaborator's
  absolute directory.
- Added coverage for anchored run/dataset references and path-escape rejection.
- Added repository-anchor and exact frame-sequence relocation coverage,
  including old and current checkouts existing at the same time.
- Added same-machine-copy, cross-platform legacy-path, schema migration, and
  checksummed-reflection coverage.
- Added legacy AutoSol coverage for reports that predate frozen input hashes.
- Added workspace configuration and optional-target parser coverage.
- Added regression coverage for mean-intensity refinement without AutoSol.
- Expanded coverage for anomalous observations, Free-R flags, and a separate
  experimental-phase MTZ.
- Validated the AutoRefine selector patch with Phenix 2.1-6048 in both a
  `--dry_run` preflight and a complete five-cycle E:G refinement that reached
  `AUTOREFINE_READY`.
- Re-ran all four example workflows end to end with Phenix 2.1-6048 and Coot
  1.3.1. Fresh five-cycle refinements reached `AUTOREFINE_READY` for E:G
  (TFZ 11.80, Rwork/Rfree 0.127/0.168), the F:D synthetic integration fixture
  (TFZ 11.80, 0.131/0.171), Q:E (TFZ 10.80, 0.161/0.208), and Q:iC (TFZ
  10.80, 0.146/0.148). Q:iC retained the expected non-blocking AutoSol warning
  and refined its anomalous iodine without experimental phases.

### Migration

- New phosphate checks apply to newly prepared PostMR outputs; existing models
  and immutable runs are not rewritten. Use a new run to reproduce preparation
  with these checks. The new AutoSol map reference is optional for older reports.
- No configuration or artifact migration is required for the source launcher;
  the generated package entry point remains supported when its editable
  installation metadata loads normally.
- Existing absolute-path reports remain readable; they do not need to be
  rewritten before use.
- Existing checkpoint schema-1 registries are read in place and migrate to
  schema 2 on their next write. Older NASolve versions reject schema 2 instead
  of interpreting an anchor-relative path against the current directory.
- Portably resolvable legacy references are normalized during migration;
  unavailable or external-only legacy evidence is retained explicitly as
  non-operational provenance rather than remaining a raw schema-1 path in a
  schema-2 registry.
- Legacy AutoMR reports without `reflections_sha256` remain usable and are
  marked `legacy-unverified` when a root checkpoint is first initialized,
  rather than silently claiming observation checksum verification.
- Existing failed refinement rounds remain immutable. Running
  `nasolve autorefine RUN` again creates the next numbered checkpoint.
- Workspace state is machine-local and is not intended for Git.

### Known compatibility notes

- Phenix 1.20.x uses explicit file/label command selectors without the newer
  Data Manager block; Phenix 2.1.x and 2.2.x use both. User validation also
  completed Q:iC refinement and bounded Refine Doctor branches on 1.20.1-4487
  with `legacy-explicit` recorded in the refinement report.
- File-scoped Data Manager parameters remain validated with Phenix 2.1-6048
  in preflight and complete refinement runs.
- The new live Phenix 2.2.1-6174 check covers mean-intensity refinement with
  no experimental phases and anomalous refinement off. It does not constitute
  a new live AutoSol or anomalous-refinement validation for that version.
- Large MTZ/map histories may eventually warrant Git LFS; current fixtures are
  intentionally kept in ordinary Git until a repository-wide LFS policy is
  adopted.

## [0.1.0 development baseline] - 2026-08-28

### Added

- External Phenix and Coot discovery and saved runtime configuration.
- Guarded AutoMR with frozen inputs and TFZ classification.
- PostMR model preparation, curated modified nucleotides, NARestraints, and
  hydrogen-free ReadySet.
- Conditional AutoSol for supported nucleotide-bound I, Br, and Se atoms.
- Sequence mutation, modified-pair restraints, and model mirroring.
- Checkpointed AutoRefine and bounded Refine Doctor triage.
