# Construct Registration human live-check queue

Status: **living minimum checklist**. Keep this short. Add or remove checks as the
registration architecture changes.

This file is not a substitute for unit/regression tests. It records the smallest
set of **human-visible / real-workflow checks** that should not be forgotten as
implementation moves across branches, chats and campaign work.

Do not mark a check complete before the relevant layer is actually wired into
the live pipeline.

**Separate live chemistry/human qualification:** the
[five-member B:S, Z:P, K:X, D:T and A:T native matrix](native-modified-pair-live-validation.md)
has its own frozen-input, released upstream NARestraints v1.1.3 workbook,
PostMR, refinement and manual Coot checks. A **separate** Z:P + 5CM:G/DF:A
integration run already reached numerical SOLVED with overall visual Coot
PASS, using the still-unmerged NASolve Saenger-overlay PR #24. The *new
five-member matrix itself remains NOT RUN*; required dictionaries may still
block B:S/K:X. None of this promotes registration, Topo Net or GUI tests
to complete; the Scout shadow evidence below retains its original, narrower
scope.

| Status | Trigger | Human check | Minimum pass condition |
| --- | --- | --- | --- |
| ☑ | **Before merging a substantial registration backend branch** | Run the focused registration/model-candidate tests **and the full NASolve regression suite**. | **Birch complete:** focused bundle 44/44 green; full suite 664 tests + 222 subtests green. **Oak Scout v2 complete for its backend-only scope:** 43 focused tests green; full suite 672 tests green; final authority/diff/runtime readiness sweep also passed. No unrelated regression observed. |
| ☐ | **When Registration Scout / registration is first wired into AutoMR/PostMR** | Run one known, ordinary **clean W** dataset end-to-end through the existing path. | It takes the boring identity fast path, adds no unnecessary prompt, preserves the expected MR/PostMR result, and the frozen registration artifacts accurately describe the known construct. |
| ☑ | **During Oak Scout v2 evaluation** | Re-run the renamed ED `run_011` real-W shadow case with the complete verified `5W6W/C_G.pdb` provider identity set (`A:12=DC`, `A:13=DC`, `B:3=DG`, `B:4=DG`). | **Complete:** exactly one zero-unexplained proposal `A->M, B->N, C->P, D->Q`; 38 exact + 4 provider-explained sites; every alternative retained >=10 unexplained mismatches; `runtime_authority = false`. |
| ☐ | **Before symmetry-spanning covalent enforcement is automated** | On a disposable ordinary DNA PDB, compare no symmetry bond versus an explicit Phenix symmetry-operation bond across a representation seam; inspect the resulting `.geo`/refinement behavior and nonbonded contacts around the phosphate. | The experiment establishes whether bond-only enforcement keeps P-O3-prime geometry and nearby OP/O3-prime contacts chemically sane without unsupported cross-symmetry angle assumptions. Until then, no automatic symmetry bond policy. |
| ☐ | **Before Coot seam repair is automated** | Practice several disposable recut cases where a seam leaves the phosphate/O3-prime connection too long; apply only a single-residue Coot RSR repair and audit before/after coordinates plus Phenix interpretation. | The intended local linkage becomes interpretable without moving unrelated model regions, damaging residue identity, or creating new geometry/clash problems. The exact bounded Coot action is repeatable enough to become a reviewed primitive. |
| ☐ | **When Topo Net / non-identity recut surgery first becomes executable** | Perform the planned **8D93 -> 3GBI-style** blind recut: transformation code receives 8D93 + symmetry + requested cut intent but cannot read 3GBI coordinates; inspect the preview in Topo Net and the materialized result in Coot. | The periodic graph is preserved while ASU ownership, chain decomposition and sticky ends become the requested representation; representation seams remain chemically continuous, true nicks remain distinct, the result is reconstructible from provenance, and only afterward does an independent 3GBI comparison confirm equivalence. |
| ☐ | **When multiplicity handling first becomes live** | Use an **8D31-like extra-copy** case, plus a partial-copy case when available. | Complete registered copies receive the intended logical sequence/modification actions; a partial copy is visibly classified as partial and is never silently treated as a complete second copy. |
| ☐ | **When guided ambiguity handling gets a UI/CLI** | Exercise a deliberately ambiguous short repeat / single-base-overhang mapping. | NASolve shows the alternatives instead of guessing; the user can select one minimal mapping decision; that choice freezes/replays exactly and does not silently become a global recipe. |
| ☐ | **When bounded multi-PDB MR selection is enabled** | Put several plausible PDBs in one dataset and inspect the candidate report before/after MR attempts. | Every candidate and rejection remains visible with immutable file identity; no filename or registration-score shortcut silently chooses a model; any automatic choice follows the reviewed MR policy and materially different successful interpretations remain inspectable. |

## Project-scoped future Topo Net human test bank

These checks are intentionally grouped by real project/fixture rather than as
one universal topology checklist. Do not run them until the corresponding
backend/UI primitive exists. Preserve exact input model/run/commit and the
observed human/Coot behavior when a check is eventually completed.

### Junction declaration / persistent-workbench project

- **Minimal semi-junction primitive:** declare a junction whose defining
  topological content is one backbone passage/connection rather than a fixed
  multi-arm object. Verify Topo Net does not require a four-arm label to
  preserve or manipulate it.
- **Variable-valence junctions:** exercise ordinary four-arm plus emergent
  six- and eight-arm neighborhoods. Verify arm count is reported as derived
  context and does not change the identity of the underlying junction
  primitive(s).
- **Declared junction survives ASU recut:** define a junction from logical
  strands/residue ranges, then reslice the ASU so the junction spans several
  coordinate/symmetry fragments. Verify the logical junction identity and true
  nicks/termini remain unchanged even when the displayed arm neighborhood
  changes.
- **Junction reconstruction:** withhold the explicit junction declaration and
  verify that the periodic graph can propose the same junction only when
  connectivity/strand/symmetry evidence is unique; otherwise retain a
  `CANDIDATE`/`UNRESOLVED` state and request expert confirmation.
- **False junction candidate:** create or identify a close packing contact that
  resembles a node in one ASU/tile cut but lacks defensible backbone/topological
  support. Verify it can be explicitly `REJECTED` without altering the periodic
  graph.
- **Sticky-end/junction separation:** verify that a sticky end associated with
  a junction neighborhood remains a real design feature while nearby
  representation seams may move or disappear under reslicing.
- **Persistent surgery/refine loop:** from one open Topo session, create a
  surgery child checkpoint, perform optional bounded Coot repair, launch a
  short audited AutoRefine child and return to the same session without losing
  selection/provenance context.
- **Compact metric panel:** verify that default display shows only checkpoint,
  Rwork/Rfree/refinement state and a local-warning summary; selecting a
  residue/seam/junction expands only relevant local Phenix geometry, phosphate
  connectivity/clashes, base-plane/sugar/backbone and reviewed stacking/pairing
  diagnostics.
- **Coot round-trip:** clicking one local diagnostic centers/selects the same
  atoms in Coot, and selecting the corresponding Topo object repopulates the
  same diagnostic context without changing the active checkpoint.
- **Refine lineage:** every Refine action creates an immutable checkpoint child
  rather than overwriting the surgical model; rejected refinement children
  remain inspectable/replayable.

### Generic model-tree GUI project

- **Forty-refine readability:** render a deliberately long refinement lineage
  and verify repetitive sequential refine nodes can collapse/expand without
  hiding branch points or changing checkpoint state.
- **Mixed-stage lineage:** show MR, PostMR, AutoSol, AutoRefine, Refine Doctor,
  manual imports, topology surgery and a later re-MR-from-refined-model branch
  in one graph with stage/type visually distinguishable.
- **Pinned panels:** pin several important historical nodes as comparison cards
  while traversing elsewhere in the tree; pinned views must not change the
  current checkpoint.
- **Branch from history:** choose an eligible older model and launch a new
  explicit branch without deleting descendants or silently rewinding the
  current lineage.
- **Inspect without select:** open any resolvable model/checkpoint in Coot from
  the tree without changing the current pointer.
- **Shared graph component:** verify normal-mode GUI and Topo Net show the same
  underlying checkpoint/model lineage rather than independent histories.
### 3GBI / 8D93 recut project

- **Representation-seam chemistry:** verify that an ASU-cut "false nick"
  preserves logical phosphodiester continuity and continuation-phosphate intent
  while a true chemical nick remains a distinct edit.
- **Symmetry-bond experiment:** on a disposable ordinary DNA PDB, compare no
  symmetry bond with an explicit Phenix symmetry-operation P-O3-prime bond;
  inspect `.geo`, refinement, phosphate angles/orientation and local
  cross-symmetry contacts before allowing any automatic symmetry-bond policy.
- **Coot seam-repair practice:** create several deliberately awkward recuts
  where the intended phosphate/O3-prime distance is initially too long; try
  one-residue Coot RSR first, record exactly which atoms move, then expand the
  repair radius only when the minimal attempt fails. Re-run Phenix
  interpretation after every attempt.
- **Mutation/surgery ordering:** on the same local seam, compare reviewed
  mutation-before-materialization versus mutation-after-materialization paths
  when both are scientifically meaningful; reject routes that curse base
  planes, stacking, sugar/backbone geometry or residue identity.
- **Topo Surgeon bounded rescue:** require each automated repair recipe to
  produce a separate immutable candidate with local geometry/stacking audits;
  if none passes hard gates, prompt for expert Coot repair and import the saved
  PDB as a new immutable user-reviewed checkpoint.
- **Blind end-to-end transform:** transform 8D93 into a 3GBI-style ASU without
  reading 3GBI coordinates during surgery. Only afterward compare periodic
  graph, ASU ownership, chain decomposition, sticky ends and symmetry-equivalent
  coordinates with 3GBI.

### P4_132 cubic / two-triangle-ASU project

- **Tile versus ASU multiplicity:** preserve the triangle as the tile hypothesis
  even when the crystallographic ASU contains two complete triangle copies;
  report tile multiplicity and ASU multiplicity separately.
- **Copy registration:** map input strands/logical sites into both complete tile
  copies without silently treating one ASU as a new tile definition.
- **Symmetry slicing:** verify that junctions, sticky ends and ordinary backbone
  segments can be cut by ASU boundaries while immutable design features remain
  attached to the tile/strand model rather than to incidental PDB chain ends.
- **Mutation/restraint propagation:** apply logical mutations/restraints to
  every appropriate complete registered copy while preserving copy-specific
  coordinate provenance.

### Repeat-bearing / root-strand symmetry-frustration project

- **Sequence-sheet semantics:** enter a tile with a declared root/center strand,
  intended per-strand tile stoichiometry and an internal n-fold repeat. Verify
  that intended copies-per-tile and internal repeat order remain separate
  fields and are not reconstructed from ASU chain counts.
- **Ordinary local closure:** use a design where root-strand repeat phases map
  cleanly around the intended tile; verify each repeated domain can be mapped
  to the periodic graph and the repeat phase closes locally without creating
  extra strand copies.
- **Long-period closure:** use the known-style fivefold repeat-bearing object in
  a fourfold/screw lattice. Verify that Topo Net can follow repeat phase through
  symmetry and report closure only after the observed twenty-unit-cell path
  rather than calling the structure stoichiometrically invalid.
- **Indistinguishable repeats:** remove/withhold phase-discriminating evidence
  from a repeat-bearing strand and verify that identical repeat units remain
  phase-ambiguous instead of being arbitrarily numbered.
- **Partial root-strand use:** exercise a structure in which only part of one
  supplied repeat-bearing strand is ordered/incorporated. Report exact
  residue/repeat-domain coverage as `PARTIALLY_USED`; do not force the missing
  part into density or mark the entire strand absent.
- **Reorganized root use:** use a structure whose observed repeat/copy
  organization differs from the declared tile while the strand itself remains
  present. Preserve the declared repeat/stoichiometry as input intent and mark
  the observed organization `REORGANIZED` or `LONG_PERIOD` as appropriate.
- **Emergent polyhedral assembly:** use the known-style incomplete-triangle
  input that yields a cuboctahedral assembly. Verify that the original strand
  stoichiometry/repeat annotations survive as provenance while the tile/periodic
  interpretation is permitted to become `EMERGENT`.
### Full-strand / emergent-tile project

- **Declared full-strand inventory:** supply complete synthesized strand lists
  and verify they outrank ASU-derived chain fragments as design evidence.
- **Missing-strand case:** include a declared input strand that is not observed
  in the solved structure; NASolve must report the discrepancy rather than
  invent coordinates or force it into the tile.
- **Unexpected stoichiometry/copy case:** allow the crystal to use more/fewer
  effective copies than the input recipe declared; preserve both experimental
  intent and observed periodic multiplicity.
- **Tile reconstruction:** when a declared tile maps uniquely from full strands
  into the periodic graph, mark it `INFERRED`/confirmed with explicit evidence;
  do not derive it merely from ASU chain names.
- **Emergent tile:** construct a case where the observed periodic graph cannot
  be faithfully represented by the declared tile. Produce an `EMERGENT` tile
  hypothesis while retaining the declared tile as experimental intent.
- **Ambiguous tile:** if multiple non-equivalent finite tile decompositions
  survive, remain `UNRESOLVED` and require an expert choice rather than hiding
  the ambiguity behind one preferred graph.

## Completed shadow live checks

### Clean W registration semantics — ED run_011

A read-only shadow test was run against the existing ED `run_011` search model
and PostMR ReadySet model using the frozen 42-site sequence-family target.

Observed:

- search model: `REGISTERED`, `identity-site-map`, **4 identity mismatches**;
- PostMR model: `REGISTERED`, `identity-site-map`, **0 identity mismatches**;
- registration transition:
  - copy structure: `SAME`;
  - copy multiplicity: `SAME`;
  - complete-copy identity classes: `DIFFERENT`;
  - single-copy coordinate realization: `SAME`.

Interpretation: the logical-to-coordinate registration remained stable while
PostMR changed residue identities to the intended target. This is the desired
separation between **where a logical site is represented** and **what identity
that site should have**.

This was a manual/read-only invocation of the registration layer against an
existing completed run. It does **not** complete the future checklist item for
Registration Scout/registration being wired into live AutoMR/PostMR execution.

### Renamed-chain real W ambiguity — ED run_011

A temporary read-only copy of the real ED `run_011` search model was created
with chain labels changed `A/B/C/D -> M/N/P/Q`. Coordinates and residue
identities were otherwise unchanged.

Scout v1 correctly returned:

- status: `AMBIGUOUS`;
- method: none;
- reason: more than one simple one-to-one chain assignment satisfied the current
  length/offset rules, and Scout refused to rank them by sequence similarity.

Descriptive design evidence nevertheless strongly separated the intended
mapping:

- logical A -> M: 19 matches / 2 mismatches;
- logical B -> N: 5 matches / 2 mismatches, versus 1/6 for P or Q;
- logical C -> P: 7/0, versus 1/6 for N or Q;
- logical D -> Q: 7/0, versus 2/5 for N and 1/6 for P.

An explicit guided choice `A->M, B->N, C->P, D->Q` then produced
`REGISTERED_COMPLETE`, one complete copy, 4 target-identity mismatches and
zero coordinate edits.

Interpretation: the conservative Scout behavior is correct for its current
policy, and the guided backend resolves the real ambiguous case cleanly. The
evidence also motivates a future **design-aware hard-rule layer** that
distinguishes mismatches already explained by declared dataset/reference
changes from unexpected ordinary-base mismatches. This should be evaluated as
explicit categorical evidence, not introduced as a generic sequence-similarity
score.

### Oak Scout v2 first real-W attempt — incomplete provider evidence

The first v2 shadow run used the renamed ED `run_011` model plus only
`A:13=DC` and `B:3=DG` as provider evidence. Scout v2 returned
`AMBIGUOUS`: 6 complete mappings, 0 zero-unexplained mappings. The intended
A->M/B->N/C->P/D->Q mapping had 38 exact identities, 2 provider-explained
differences and 2 unexplained differences.

Inspection of the actual standard provider `MR_frames/5W6W/C_G.pdb` verified
that the two missing identities are `A:12=DC` and `B:4=DG`. Thus the
provider-specific four-site identity set is A:12/A:13=DC and B:3/B:4=DG.
This is a validation of fail-closed behavior, not a failed scientific mapping.

### Oak Scout v2 second real-W attempt — complete provider evidence

The same renamed ED `run_011` shadow case was repeated with the full verified
provider identity set from `MR_frames/5W6W/C_G.pdb`:
`A:12=DC`, `A:13=DC`, `B:3=DG`, `B:4=DG`.

Observed:

- status: `PROPOSED`;
- complete assignments enumerated: 6;
- zero-unexplained assignments: **1**;
- proposed mapping: `A->M, B->N, C->P, D->Q`;
- intended mapping evidence: **38 exact, 0 target-history, 4 provider, 0 unexplained**;
- the five alternatives retained **12, 11, 16, 17, and 10** unexplained
  mismatches respectively; and
- `runtime_authority = false`.

Interpretation: the categorical zero-unexplained uniqueness rule disambiguated
the real renamed-W case only after the missing provider identities became
explicit evidence. It did not choose a merely best-scoring mapping.

### Oak Scout v2 third real-W attempt — provenance-bound provider interface

The same renamed ED `run_011` shadow case was then repeated through the newer
`provider_assessment + model_provider` interface. The historical run predates
the structured `model_provider` field, so the provider record was reconstructed
manually and read-only **only after** verifying all explicit historical facts:

- source model path resolves to `MR_frames/5W6W/C_G.pdb`;
- model source is `standard frame catalogue (W; fallback C_G.pdb)`;
- recorded source-model SHA-256 is
  `d26ebf248a0a597a3884a6d6b2c6ec8f9bba27c9cad9f0604da136e13bfb1817`;
- that SHA-256 matches the current assessed provider model exactly.

No residue-code dictionary was supplied.

Observed:

- provider baseline provenance bound: **true**;
- caller-supplied provider codes: **false**;
- status: `PROPOSED`;
- complete assignments: **6**;
- zero-unexplained assignments: **1**;
- proposed mapping: `A->M, B->N, C->P, D->Q`;
- intended mapping: **38 exact, 0 target-history, 4 provider, 0 unexplained**;
- alternatives retained **12, 11, 16, 17, and 10** unexplained mismatches; and
- `runtime_authority = false`.

Interpretation: the provenance-bound interface reproduced the same scientific
answer without laundering an old run's missing structured metadata into
certainty. Historical provider provenance was bridged only from explicit
verified path/source/checksum facts; residue identities came from the assessed
provider coordinates.

### Oak Scout v2 fourth real-W attempt — fresh native provider provenance

A fresh current-schema AutoMR preflight was then created as ED `run_013`,
reproducing the scientific intent of `run_011` (standard W, pair E:D,
`w-metal-scaffold` sequence reference, D:1 5-prime phosphate). Phaser was not
run; the purpose was to generate a fresh frozen run with native structured
`model_provider` provenance.

The renamed-W shadow case was repeated directly from `run_013` using:

- the run's native `inputs.model_provider` record;
- the literal provider model referenced by the run;
- a fresh `ModelAssessment` of that provider model; and
- the run's frozen `sequence_family_target.json`.

Observed:

- provider: standard-frame catalogue W fallback `C_G.pdb`;
- provider SHA-256:
  `d26ebf248a0a597a3884a6d6b2c6ec8f9bba27c9cad9f0604da136e13bfb1817`;
- provider baseline provenance bound: **true**;
- caller-supplied provider codes: **false**;
- status: `PROPOSED`;
- complete assignments: **6**;
- zero-unexplained assignments: **1**;
- proposed mapping: `A->M, B->N, C->P, D->Q`;
- intended mapping: **38 exact, 0 target-history, 4 provider, 0 unexplained**;
- alternatives retained **12, 11, 16, 17, and 10** unexplained mismatches; and
- `runtime_authority = false`.

Interpretation: the same scientific answer is reproduced from a fresh
current-schema run with native provider provenance, eliminating the historical
schema-reconstruction caveat. This completes the intended validation for the
current backend-only Scout v2 scope. It still does not authorize live
AutoMR/PostMR integration or runtime authority.

## Current validation note

The earlier Birch checkpoint at code head
`4452295c3330de6d55bddd75b01be21f39afb222` had **23 focused registration
tests passing locally**.

The current Birch focused bundle has **44 tests passing locally** across
`tests/test_construct_registration.py` and `tests/test_model_candidates.py`.
The full NASolve regression suite also passed locally with **664 tests and 222
subtests** in **61.70 s** on checkout
`cc0ad6ab537cc61e17e13bc562e4ae8667461e8d`.

Oak's earlier Scout v2 checkpoint at code head
`189fd4589a8c8f2a0191e21e99cec22b428e6a1c` had **41 focused tests passing**.
After binding provider evidence to the assessed catalogue model/provenance and
adding explicit fail-closed tests for incomplete provider coverage and
provider-selector/source mismatch, the focused suite passed **43 tests locally**
at checkout/test head
`507745a0b7166f05229f6c3501d5e1f694db93e2`; the underlying source-behavior
head remains `c515a37dc41fa8bb1935d2c80c825ebef8153177`.

The current Oak checkout at
`316ac43eaf85a63cf675828bb8960a28f0db2773` then passed the **full NASolve
regression suite: 672 tests locally**. No runtime or subtest count was reported
for this checkpoint. This is user-local validation, not GitHub CI.

When a live check above is completed, record the dataset/run/checkpoint and code
commit in the development handoff or the machine-readable intent ledger. Avoid
writing only "passed": the point is to preserve *what exact behavior was seen*.
