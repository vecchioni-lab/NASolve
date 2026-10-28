# NASolve development handoff — current state

Updated **2026-10-28** from native receipts, user visual review and verified geometry/DF
bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The preserved historical laptop Cedar checkout remains at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, with only the explicitly
authorized `src/nasolve/phaser.py` fix modified after the GeoTest rerun.
Its other 45 frozen source hashes, including the distinct curated source,
are preserved. Preserve this local unpublished diagnostic head; do not pull or
replace it with a remote head to continue the run. Diagnostic scripts/derivatives are
not general production support. Earlier wording remains in Git and the
[exact pre-reconciliation backup](history/development-handoff-2026-10-10-pre-reconciliation.md.txt).

## C110 full-model recipe and L-3GBI

Implementation, live checks and full regression pass. No job is active.
Output: `live_tests_directory/110_Cedar_L-3GBI-6sgsjhko/validation/full-suite.log`.
Tested implementation: `799ecc60a31f5b6264b40a4f6d6dc967a43da645`, published and verified on `origin/cedar`.
Continue on existing `cedar`; no other branch or checkout is part of this change.

The operator supplied diffraction data and exact `3gbi.pdb`, requesting its
original sequence mirrored into L-DNA and full-model NAR restraints. The new
`[automr] restraint_scope = all` card (or explicit PostMR override) now survives
ordinary/campaign freezing, selects model-derived NAR pairs plus same-chain
stacks, and uses the existing source-bound explicit compiler. It reports
unpaired sites and never adds W-specific scaffold defaults. Source dictionary
lookup is independent of choosing a Coot D-sugar parent. Mutation safety and
NAR recipes/workbook remain unchanged. New selection schema 1; run/checkpoint
schemas unchanged. Old inputs retain their behavior; old versions reject the
new key. See [human guide and methods](full-model-restraints.md).

Actual Phenix 2.2.1-6174 results: mirror maps all 855 atoms/42 residues, reverses
126 distinct sugar centres (147 ordered checks), and round-trips atom fields
exactly. Phaser passes TFZ 15.8 / LLG 324. NAR selects 19 pairs and 38 stacks;
native checks confirm 49 bonds, 82 angles and 57 parallelities with other proxy
families preserved. All 38 in-model links and 126 sugar signs survive. Ordinary
PostMR reaches POSTMR_READY and its exact recorded bundle passes a fresh native
membership check. Two installed-library controls fail; four generated-dictionary
controls pass. Two ReadySet executions; no Coot or coordinate refinement.

Do not call this fully repaired or scientifically qualified. Source-state
comparisons reject the generated phosphate deprotonation/charge changes, with
omitted R/S metadata and representation changes also recorded. L-sugar signs
are preserved; this is not an L-flip failure. A:101/A:102/D:101/D:102 have no
selected partner inside the ASU; symmetry coverage remains open. Next: qualify
source-preserving L-component numerical chemistry and periodic end pairs, then
fresh bounded refinement and measured pair improvement. C109/G2 and PDU gates
below remain open.

151 focused tests plus 34 subtests pass (15.04 s), including new recipe/source
lookup, frozen campaign, ordinary preparation and relocation regressions. Full
suite: **6012 tests + 276 subtests pass in 933.15 seconds**. The complete recipe
and PostMR bundle also replay in a fresh relocated checkout with original
paths unavailable and native execution blocked. No code changes followed these
checks; this publication handoff only records the tested commit. Exact commands/hashes: `l_dna_full_model_recipe_2026_10_28` in the
[evidence ledger](cif-linked-native-registration-evidence.json). The local capsule
preserves every attempt; raw data/models/logs/dictionaries/runners stay outside
Git. A new `nasolve.txt` was placed beside the original four supplied files;
their hashes and timestamps are unchanged.

— Rowan · Codex desktop

## Generalizer milestones and interruption boundary

**Scope revised 2026-10-28; C110 published and validated within the limits above.** Every ligand in the selected
NARestraints catalogue is a target for automatic source inspection, bounded
repair/regeneration and qualified usable fallback. ATL, PNA and other backbone
families are included in this programme. Catalogue membership is not evidence
that a ligand already works. The earlier narrow Cedar integration estimate is
not an estimate for complete catalogue support.

| Milestone | Completion evidence | State |
| --- | --- | --- |
| G1 — Catalogue baseline | Reproducible audit of every row/code, duplicate operational mappings, explicit source availability, graph/role findings and unqualified families; no code disappears silently. | **C105 complete.** Exact sources, rows, mapping gaps and cold relocation validated; qualification remains separate. |
| G2 — Chemical and attachment contracts | Explicit family/site profiles for connectivity, leaving groups, terminal state, stereochemistry and source authority; held-out ligands test transfer. | **C109 exact source/native link audit validated. G2 remains partial.** DNA naming/protonation differences and ATL numerical dictionaries need explicit reconciliation/qualification; PNA and terminal reconstruction remain open. |
| G3 — Bounded recovery and usable fallback | Immutable attempts repair only authorized source/representation defects, regenerate when justified, preserve identity and NAR mappings, and select only a qualified usable result. | Decision/reuse pieces exist; general orchestration remains open. |
| G4 — Native and numerical qualification | Exact consumer inventories, energy/gradient attribution, derivatives and round-trip checks for each changed manager/family; failures remain explicit. | **PDU C104 inventory passes; energy/gradient and derivative proof remains open.** |
| G5 — Ordinary workflow | Recovery, qualification, adoption/checkpoints and plain-language reporting run together on representative and held-out cases. | C110 opt-in full-model NAR recipe passes ordinary L-DNA PostMR and exact native membership. Chemical-state/refinement qualification and general recovery remain open. |
| G6 — Catalogue coverage and release | Coverage matrix distinguishes qualified, recoverable and genuinely unresolved cases; all families attempted with actionable evidence. Full regression, scientific review, verified runner archive and integration review complete. | Planned; merges remain separate. |

These are acceptance milestones, not a fixed count of coding pushes. G2–G5
iterate by chemically meaningful family; a catalogue full of `UNSUPPORTED`
results does not complete the generalizer. A fresh temporary component alias
may isolate definitions, but never authorizes changing connectivity, charge,
protonation or stereochemistry to obtain convergence. Ask for scientific intent
only when available evidence and safe usable fallbacks cannot settle it.
ChemDraw-derived source references/restraint bundles remain future input scope;
building a model from a drawing stays outside CIF Doctor.

### C109 published interruption boundary

**Safe resume point:** C109 tested implementation commit
`7907eca49db0803b4c694bc58ffb5aff8024d88a` is published and verified on GitHub `cedar`.
This continuity follow-up changes documentation only. No job is active.
Continue on existing `cedar`; preserve other branches, shared-restraint work
and every scientific run. The next implementation boundary is recorded below.

Before C109, C108 required reciprocal source ports but did not compare those
literal endpoints with native captures. C109 adds
`src/nasolve/cif_attachment_native.py`, public `cif-doctor link-native MANIFEST
--native-receipt FILE` and `tests/test_cif_attachment_native.py`. The read-only
reader checks native input/output hashes, exact model bytes, maintained worker,
requested/consumed dictionary/PHIL order, spec/report agreement and unique
atom identity. It handles native reordering with only 1e-9 A coordinate roundoff;
occupancy remains exact. All inter-site bonds touching selected sites must match
the literal declared endpoints once. Wrong/extra/duplicate/symmetry links cannot
hide behind counts. Source atom names/elements, retained adjacency and available
formal charges are compared separately from bond membership.

Three complete interpretation attempts ran in **Phenix 2.2.1-6174** (dispatcher
reports 2.2.1; setup-script version and dispatcher/API hashes are recorded).
Synthetic CCD-ideal pairs were translated to a declared 1.607 A link; this tests
representation, not experimental geometry or numerical quality. DA–DT built the
exact O3prime–P bond (target 1.607 A, weight 6944.444444444444), with observed OC2/P
types. Its definitions still require review: DA source OP3/HOP2 differs from
native O3T/no HOP2; DT source C7/H71/H72/H73 differs from C5M/H5M1/H5M2/H5M3,
and source HO3prime/HOP2 are absent from the effective definition. These findings
do not imply coordinate deletion of terminal phosphate. Formal-charge readback
is unavailable and partial charge is not substituted. DA–ATL and ATL–DA fail
explicitly with 22/23 unknown nonbonded energy types. All failures are preserved;
no native retry, optimizer, Coot, ReadySet or refinement ran.

The additive report schema 1 remains overall `REVIEW`, with distinct native,
link and definition outcomes. Observed types/targets are not chemical/numerical
authority. Captured worker code is data and never executed by the reader; the
initial reader accepts the exact maintained base worker, not augmented energy
workers or unrelated historic versions. Existing capture/runtime/checkpoint
schemas, preparation, NAR ownership, dependencies and thresholds are unchanged;
no migration or automatic adoption. The evidence ledger lists all 14 changed
files; maintained contracts, human overview and editable figure are updated.

Validation: **5989 passed, 276 subtests passed in 931.90s (0:15:31)**; **183 focused tests pass**, including **49 new native-link
regressions**. Before/after logs cover the absent CLI, measured roundoff,
JSON replay and contradictory consumed-input records. The three real captures
plus three adversarial variants replay exactly through API/CLI in a new process
after moving source/input copies, with original owned paths absent and SDK/
historical reads and subprocesses blocked. All original bytes/timestamps remain
preserved. Compilation, doc links/JSON, whitespace and rendered SVG pass. Exact
commands, hashes, version evidence and timings: `native_attachment_link_audit_2026_10_28`
in the [evidence ledger](cif-linked-native-registration-evidence.json).

Primary local evidence: `live_tests_directory/109_Cedar_native-link-confirm-9m1r807r`. Its parent capture
record points to `109_Cedar_native-links-theuy88j`, which owns the three original
native attempts. The initial full-suite run was intentionally stopped after
383.55 seconds for the consumed-input-order fix; its partial log/reason remain
preserved. The final full suite completed in a fresh attempt after the old PID
was confirmed dead. Frozen workbooks/CCD files, models, candidates, native
captures/logs and generated runners remain local; only source, synthetic tests,
maintained documentation and compact technical evidence enter Git.

**Next G2 boundary:** establish explicit native atom-name mappings and separate
protonation policies using DNA controls. The hash-matched installed source exposes
`monomer_mapping.atom_names_mappings`, `expected_atoms` and `mon_lib_names`;
capture their actual per-site/index bindings before accepting aliases. These
fields have only been inspected in source, not yet captured/qualified. Preserve
C109's worker-version compatibility when extending native captures.
Names alone must not silently reconcile
OP3/O3T or C7/C5M, and protonation differences must not become automatic deletions.
Recover/generate a source-preserving numerical ATL candidate through existing
bounded machinery, validate its graph/stereo/NAR identities, then qualify both
native link directions. Installed-library failure is not a blanket ATL exclusion.
Keep native types, full numerical definitions and scientific qualification
separate from membership. PNA amine/carboxyl operations and free-OH reconstruction
remain open; APN (+1/three H) and 40A (0/two H) cannot share implicit neutralization.
Further cores, GNP source/label reconciliation and A66 record conflict remain open.

**Preserved baselines:** C105 covers 618 rows/599 codes; C106 covers 37 source
profiles (26 unique matches, ten unmatched, one conflicting record group).
C107 supplies site projections; C108 supplies reciprocal source ports. C104 PDU
inventory still needs energy/gradient attribution and fresh derivatives before
any optimizer. C100 remains unqualified and `verified_recovered_model` stays
selected. No Pine/main merge occurs.

— Rowan · Codex desktop

## Preserved PDU continuation boundary (C104)

**C104 remains the current PDU omission-inventory proof.**
A separate candidate applies the existing declaration-based policy to all PDU
rows. Two complete Phenix 2.2.1-6174 native interpretations of the current C98
863-atom model pass: the original reproduces C98 exactly, and the candidate
removes six PDU definition rows and three active dihedral proxies (610 → 607).
All 21 remaining inventory-category comparisons pass, including the 5PC
bystander, phosphate/linkage state, NAR terms and model coordinates.

Before C104, C103 established row-level declaration and numerical-sensitivity
evidence. New `cif_linked_linear_torsion.py` rebuilds the complete candidate plan,
checks native triple/180° prerequisites at every modeled occurrence, and permits
only the planned omissions. New synthetic tests cover complete-plan binding,
bystanders, multiple occurrences, reversed proxies, chemistry/policy changes,
ambiguity, type changes and relocation. The schema-1 result remains `REVIEW`
with `inventory_checks_pass`; energy/derivative/scientific gates remain `NOT_RUN`.
No CLI/runtime schema, dependency, threshold or migration changes.

Validation: **5798 passed, 276 subtests passed in 1033.68s (0:17:13)**; **57 focused regressions pass**. Cold replay preserves 126 relocated files
and timestamps with the original temporary path gone and historical live/SDK
reads and processes blocked. Four scientific-inventory alterations fail.
All 497 C98–C103 parent files retain bytes/timestamps. The C103 maintained reader
replays the complete prior lineage. Candidate preparation and two native
interpretations are complete executions, not dry-runs; no Coot, ReadySet,
optimizer or model edit runs. Inputs, candidate CIFs, captures and logs stay
local. Git contains source, synthetic tests, maintained docs and compact evidence.
Exact commands and hashes: `linked_pdu_omission_inventory_2026_10_27` in the
[evidence ledger](cif-linked-native-registration-evidence.json).

**Next boundary:** fixed-coordinate original/candidate energy and gradient
attribution, then derivative checks at relevant initial/saved endpoint coordinates.
The native captures contain energy observations but this inventory gate does not
qualify their deltas. Do not inherit C99 derivatives for the changed objective,
retry optimization, adopt the candidate or requalify C100 from inventory alone.
`verified_recovered_model` remains selected. The old isolated impact worker
explicitly rejects parallelity managers; reuse its attribution concepts through
the current mixed-model corrected evaluator, preserving the NAR stacking terms.
Callers must authenticate native
capture/input provenance; this helper is not a standalone artifact reader.

Continue directly on **`cedar`**; no new branch, Pine/main merge, or changes to
the separate metal GUI/shared-restraint work. See the [C104 contract](cif-doctor.md#linked-pdu-omission-inventory-c104).

— Rowan · Codex desktop

### Previous C103 delivery

**C103 delivery: independent PDU precision and declaration audit.**
The complete saved-data execution takes 66.15s with zero new native calls.
All 21 supported proxy/case rows pass independent 60/90-digit, reversed-order
and 504 Cartesian direction/order checks at both decimal steps. Three DZ
alternate-ideal cases are explicitly unassessed. Only the full-precision PDU
central torsion disagrees with the saved native gradients at the existing strict
comparison: maximum component differences 2.236935e-4 forward and 2.697555e-4
reversed. Both high-precision orders agree. A one-ULP coordinate change produces
up to 0.227086 gradient-component change there, versus about 3e-8 at initial and
rounded coordinates. See the [C103 contract](cif-doctor.md#independent-recovered-torsion-precision-c103).

Before C103, C102 had resolution/reversal findings without an independent
mathematical reference. New `cif_torsion_precision.py` uses exact binary inputs,
standard-library Decimal arithmetic and automatic differentiation of a plane-normal
energy expression. New `cif_recovered_precision.py` binds that calculation and
read-only declaration checks to maintained C102/C101/C100/C99/C98 readers.
The additive schema-1 `recovered_precision_audit.json` and `precision_result.json`
have explicit anchors/checksums and complete replay. No dependency, CLI/runtime
schema, historical worker or migration changes are required.

Validation: **5772 passed, 276 subtests passed in 1034.42s (0:17:14)**; **49 focused regressions** pass. Cold relocated replay preserves all 497 parent/audit files and timestamps, retains the selected start and rejects four rebound forgeries with zero processes. Compilation, whitespace, 198 document links and rendered-figure inspection pass.

Phenix 2.2.1-6174 supplied the preserved native observations; this step performs
text inspection and mathematical computation only. No fresh Phenix/Coot job,
generation, optimizer, candidate preparation or model edit runs. All C95 and
C98–C102 parent bytes/timestamps are preserved. Inputs, coordinates, native and
decimal observations, inspected installed sources and logs stay local; Git
contains source, synthetic tests, maintained docs and compact technical evidence.
Exact commands/hashes are in `recovered_torsion_precision_2026_10_26`.

The three sampled PDU torsions and three 5PC controls match the existing
triple/180° declaration prerequisites against both current dictionaries and
native effective definitions. This is a row-level finding, not a complete
candidate plan or scientific approval. The independent calculation supports
numerical sensitivity near collinearity; it does not establish a native coding
defect. C100 remains unqualified and the verified recovered start stays selected.

**Next boundary:** prepare a separate PDU candidate with the existing complete
declaration-based omission policy. Check exact original/candidate native
inventories in the current linked model, deriving the planned omission set and
preserving every other term, phosphate state, NARestraints target and 5PC bystander.
Then compare fixed-coordinate energy/gradient deltas and recheck derivatives
before any optimizer. Do not overwrite evidence, relax thresholds or promote
the endpoint based on the independent reference.

Continue directly on **`cedar`**; no new per-fix branch or Pine/main merge.
The separate metal GUI/shared-restraint work is untouched.

— Rowan · Codex desktop

### Previous C102 delivery

**C102 delivery: fixed-coordinate resolution diagnostic.**
One complete Phenix 2.2.1-6174 job (dispatcher 2.2.1) completes in 8.843132s,
with 540 evaluations: 22 local direction/order rows and 10 broader total/dihedral
rows, retaining 326 original passing directions. Only the two local-gradient
rows and four rounded broader rows pass. All six full-precision broader rows
remain under review; displacement-resolution guards reject some arithmetic
agreements. All 24 repeated family snapshots match. The PDU reversal discrepancy
reproduces exactly (maximum component difference 4.606198899637093e-5).
See the [C102 contract](cif-doctor.md#recovered-endpoint-resolution-c102).

Before C102, the recovered endpoint had a coarse torsion audit but no guarded
resolution-window evidence. `cif_recovered_resolution.py` and its regression
tests add the current-parent adapter and fresh reversal summary, reusing the
unchanged C93 plan, worker and replay. The additive schema-1 receipt is
`recovered_resolution_audit.json`; CLI/runtime and historical receipts need no
migration. Three failed prerequisites remain false. Diagnostic completion does
not imply numerical qualification; C100 remains unqualified and the verified
recovered model stays selected. No endpoint serialization or native reread runs.

Validation: **5723 passed, 276 subtests passed in 1006.53s (0:16:46)**; **43 focused regressions** pass. Cold relocated replay preserves all 495 parent/audit files and timestamps, retains the selected start and rejects four rebound forgeries with zero processes. Compilation, whitespace, 195 document links and rendered-figure inspection pass.

All audited C95, C98, C99, C100 and C101 parent bytes/timestamps are preserved. Generated coordinates,
dictionaries, observations, installed-source snapshots and logs stay local;
Git contains code, synthetic tests, maintained docs and concise technical evidence.
Exact commands/hashes are in `recovered_resolution_diagnostic_2026_10_26`.

The captured current PDU definition has a C5A–C5B triple bond (1.203 Å), two
180° flank targets and central torsion Var_34 at -11.22°/30° ESD, period 1.
**Next boundary:** independent higher-precision calculation of this exact
four-atom function in both orders, plus comparison with C43–C46's explicit
linear-axis declarations and candidate policy. Preserve exact binary input
coordinates and every current failure. Do not blindly shrink steps, relax
thresholds, remove a term or retry optimization. Any candidate change needs
separate source authority and current-manager proof that all other terms,
phosphate chemistry and NAR targets survive. Scientific approval and ordinary
refinement remain separate.

Continue directly on **`cedar`**; no new per-fix branch or Pine/main merge.
The independent metal GUI/shared restraint work is untouched.

— Rowan · Codex desktop

### Previous C101 delivery

**C101 delivery: fixed-coordinate recovered-endpoint torsion audit.**
One complete Phenix 2.2.1-6174 job (dispatcher 2.2.1) completes in 5.393327s,
with 9,504 local paired-kernel evaluations and 528 group calls. The unchanged
selector chooses six near-collinear torsions and two disjoint controls.
Initial and rounded local/group derivatives pass at finer existing steps.
At full precision, all 22 remaining local reviews belong to PDU D:5
C5–C5A–C5B–C5M, eleven in each atom order; the other seven selections pass.
The selected group retains four reviews, the full group three, the remainder
none. Native/saved-family, repeat and attribution controls pass. The same PDU
torsion retains a strict atom-order reversal review at full precision: maximum
gradient-component difference 4.6062e-5; the other 23 proxy/case reversals pass.
See the [C101 contract](cif-doctor.md#recovered-endpoint-torsions-c101).

Before C101 there was only a saved geometry screen for the recovered endpoint.
The new `cif_recovered_torsion.py` adapter and `test_cif_recovered_torsion.py`
connect maintained C100/C99/C98 readers to the unchanged torsion worker and
numerical replay. The additive schema-1 receipt is `recovered_torsion_audit.json`;
historical reports and CLI/runtime manifests need no migration. Completion of
the diagnostic does not mean derivative qualification. C100 remains unqualified
and `verified_recovered_model` remains selected with `CONTINUE_WITH_NOTES`.

Validation: **5680 passed, 276 subtests passed in 927.68s (0:15:27)**; **39 focused regressions** pass. Cold relocated replay preserves all 425 parent/audit files and timestamps, retains the selected start and rejects three rebound forgeries with zero processes. Compilation, whitespace, 192 document links and rendered-figure inspection pass.

All 38 C95, 213 C98, 68 C99 and 76 C100 files retain their bytes and timestamps.
Generated coordinates, observations, dictionaries, installed-source captures
and logs remain local; Git includes source, synthetic tests, documentation and
compact technical evidence. Exact commands, hashes and results are in ledger
entry `recovered_mixed_torsions_2026_10_26`.

**Next boundary:** a resolution-aware fixed-coordinate audit of the retained
local and broader total/dihedral directions, including the independent strict
atom-order reversal finding. Keep the existing tolerances,
coarse failures and representability/midpoint/target-resolution controls. The
very small PDU plane normal is a conditioning lead, not proof of wrong chemistry
or permission to remove a restraint. Do not optimize again or transfer old
C91–C93 qualification. Source chemistry, ordinary refinement, runtime adoption
and scientific approval remain separate.

Continue directly on **`cedar`**, with no per-fix branch or Pine/main merge.
The independent metal-base-pair GUI work can proceed; this delivery changes no
GUI, metal recipe, NARestraints workbook or shared compiler.

— Rowan · Codex desktop

### Previous C100 delivery

**C100 delivery: bounded geometry for the repaired objective.**
One complete Phenix 2.2.1-6174 job (dispatcher 2.2.1) lowers the fixed target
12.5367%, from 4900.147192055969 to 4285.828848323326. The native line search
stops after 58 iterations/108 calls with rounding errors and its convergence
criterion false. Six of 168 full-precision and four of 168 rounded directions
remain under derivative review, all in global total/dihedral directions.
Repeat, snapshot and additivity controls pass. No tolerance changes.

The saved result is **REVIEW**, selecting **`verified_recovered_model`** with
`CONTINUE_WITH_NOTES`. Conditional native reread is skipped; no endpoint PDB,
runtime selection or checkpoint is adopted. Full-precision coordinates and
all failed samples/stopping evidence are retained. The 46.001752-second job
preserves all 38 C95, 213 C98 and 68 C99 files. See the
[C100 contract](cif-doctor.md#recovered-objective-geometry-c100).

Before C100, the repaired objective had native and initial derivative proof but
no geometry trial. The new `cif_recovered_geometry.py` adapter binds that proof
to the unchanged worker, optimizer, serializer and endpoint/native qualifiers.
Tests are in `test_cif_recovered_geometry.py`. Its additive schema-1 receipt is
`recovered_geometry_trial.json`; historical reports, CLI and runtime manifests
need no migration. No GUI, metal recipe, NAR workbook or shared compiler changes.
The user-authorized metal-base-pair branch can proceed independently.

Validation: **5641 passed, 276 subtests passed in 820.32s (0:13:40)**; **143 focused tests** pass, including 38 new cases. Cold relocated replay preserves all 357 parent/trial files and timestamps, reproduces the retained start and rejects three rebound forgeries with zero processes. Compilation, whitespace, 189 document links and rendered-figure inspection pass.

Exact validation commands, frozen hashes and compact results are recorded under
`recovered_mixed_geometry_2026_10_26` in the existing evidence ledger. Generated
models, input dictionaries, captured sources, raw observations and logs remain
local; Git includes source, synthetic tests, documentation and concise receipts.

**Next boundary:** a fixed-coordinate torsion/conditioning audit of this saved
endpoint before another optimization. The existing saved-data selector flags
six near-collinear torsions plus two controls; the most severe PDU D:5 minimum
plane-normal sine is 2.95e-7, versus 1.29e-3 initially. That is a diagnostic lead,
not proof of a derivative bug or authority to remove a restraint. Reuse the
established local/group and resolution-window controls with this exact current
objective; old C91-C93 qualification cannot transfer. Source chemistry,
ordinary refinement, runtime adoption and scientific approval remain separate.
Continue directly on **`cedar`**; no new per-fix branch or Pine/main merge.

— Rowan · Codex desktop

### Previous C99 delivery

**C99 delivery: repaired-manager derivative qualification.**
The exact C98 DF recovery now passes a fresh fixed-coordinate audit on Phenix
2.2.1-6174 (dispatcher 2.2.1): 168 sampled directions, both orders of all 58
planes and six tilted/rotated controls. Native energies, all 863 coordinates
and static definitions remain unchanged. Five global/dihedral directions need
the two smallest existing step sizes; no tolerance or scientific policy changes.
One native job completes in 27.315 seconds, using 1,367 energy evaluations and
3,328 plane-evaluation pairs. See the [C99 contract](cif-doctor.md#recovered-manager-derivatives-c99).

Before C99, C98 supplied source/link/native mechanics but explicitly withheld
proof for the changed objective. The new `cif_recovered_gradient.py` adapter
binds that recovery to the unchanged C89 worker and replay validators. Tests are
in `test_cif_recovered_gradient.py`. The additive schema-1 outer receipt is
`recovered_mixed_gradients.json`; old runtime manifests, numerical policies,
CLI behavior and C95 selection remain unchanged, with no migration required.

Validation: **5603 passed, 276 subtests passed in 758.63s (0:12:38)**; **149 focused tests** pass, including 41 new cases. Cold relocated replay preserves all 281 parent/audit files and timestamps, rejects three rebound forgeries and launches no processes. Compilation, whitespace, 186 document links and rendered-figure inspection pass.

Validation results and exact commands are recorded under
`recovered_mixed_derivatives_2026_10_26` in the existing evidence ledger.
Generated inputs, dictionaries, observations, source captures and logs remain
local in the C99 live-test directory. Only code, tests, documentation and concise
technical hashes/receipts are committed. All 213 C98 and 38 C95 files are
preserved. The initial execution adapter and final verified reader are archived
with distinct hashes; only preflight/receipt guards changed after execution,
and all numerical worker/core bytes remain identical.

**Next boundary:** a bounded geometry trial of this repaired objective using
the qualified local evaluator, with fresh full-precision/serialized endpoint
derivatives, exact native reread and automatic usable fallback. Initial sampled
derivatives do not qualify an endpoint, ordinary Phenix refinement or scientific
chemistry. Other source findings, ATL and future chemical-reference work remain
separate. No runtime activation, checkpoint adoption or Pine/main merge occurs.
Continue directly on **`cedar`** in the existing isolated development worktree;
no new per-fix branch. Preserve the everyday Pine checkout and old diagnostics.

— Rowan · Codex desktop

### Previous C98 delivery

**C98 delivery: preserved DF source recovery.**
The exact C18 candidate `8daa21379bba…` and its source `27f83c85e896…`
are bound to verified archive members and requalified against the current C95
endpoint lineage. Two isolated and two full-model native controls pass with
Phenix 2.2.1-6174 (dispatcher 2.2.1). DF A:19 now uses the source-preserving
candidate with explicit A:18/A:20 linkage preparation. All 863 coordinates,
38 backbone links, 20 pairs, 38 stacks and proxies wholly outside DF are
preserved. Linked checks: 25 PASS / 2 explicit unavailable formal-charge
readbacks; full-model membership: 33 PASS. OP3/HOP3 and outgoing HO3′ are
removed at this linked site, while HOP2 is retained. No generation or coordinate
optimization was needed. See the [C98 contract](cif-doctor.md#preserved-candidate-source-recovery-c98).

The new schema-1 `mixed_source_recovery.json` is a separate diagnostic artifact.
Its maintained reader rebuilds preparation and qualification from owned inputs;
current runtime manifests, CLI behavior, C95 selection and historical runs do
not change. Only a dedicated component file with no prior selected-site
modifiers is supported by this bounded reuse policy. Shared containers and
modifier composition require their own explicit adapter.

C98 builds on C97 commit `71a0afd5e9eca014b0c2b7042dbd69ce90e2f06c`.
C96–C98 are consolidated as ordinary commits on **`cedar`**, the continuing
development line. Per-fix branches are retired only after remote Cedar contains
their commits. Everyday Pine, the older detached diagnostic Cedar checkout and
its Phaser edit remain preserved. No Cedar-to-Pine/main merge is performed.

Validation: **5562 passed, 276 subtests passed in 770.65s (0:12:50)**; **154 focused tests**, compilation, whitespace, 186 local document links and the rendered figure pass. Cold relocated replay takes 43.25s, preserves all 213 files byte-for-byte with timestamps intact, launches no native processes and rejects three rebound evidence forgeries. Exact commands, source/test hashes, native
receipt bindings, relocation and preserved-artifact checks are recorded under
`mixed_preserved_source_recovery_2026_10_26` in the existing evidence ledger.
Generated models, dictionaries, controls, capsules and logs remain in the local
live-test root and are excluded from Git; code, tests and concise technical
evidence are included.

**Next boundary:** the repaired DF dictionary changes the full-model restraint
objective. Requalify that exact manager's derivatives with the NASolve-local
corrected evaluator before another geometry trial or runtime activation.
C93's old objective proof cannot be inherited. Other current source findings
(5PC, CGY, DX, IMC, PDU, S6G), IGU declaration metadata, experimental chemical
state and ordinary refinement qualification remain separate. Do not hand-edit
chemical state or numerical targets merely to erase comparison findings.

C97's ordinary read-only inventory remains available and continues to describe
the original C95 resources accurately. Its historical generation findings,
current declarations and site contexts remain separate. C98 does not silently
promote the repaired diagnostic into that runtime bundle.

— Rowan · Codex desktop

### Previous C96 delivery

**C96 delivery: reporting and consolidation after a verified Mac C95 handoff.**
See the [current capability map](cif-doctor.md#current-capability-boundary-c96)
for established contracts, open science and future chemical-reference scope.
C95 ran locally from `3fcedf5bb18f7e482d94b5827478c6b4f26b80e3` and passed:
863 atoms, 23 dictionaries, 12 PHIL files, all five saved selection gates,
relocation before ordinary assessment and zero new native calls. Exit 2 retains
the original `REVIEW` and scientific limits. The exact return is appended to
`mixed_runtime_bundle_handoff_2026_10_25` in the existing evidence ledger;
publication-time validation and earlier receipts remain intact.

C96 changes reporting only: text-mode assessment now displays its solution
summary; mixed-bundle reports distinguish saved corrected-evaluator evidence,
unresolved source chemistry and unqualified ordinary refinement. Existing
selection, thresholds, chemistry, schemas, stopping and NAR policy are retained.
ATL remains an independent source/compiler control. Future ChemDraw-derived
reference-to-restraints support is recorded without claiming an importer or
including drawing-to-model construction in CIF Doctor.

Development branch `codex/cedar-c96-handoff` targets `cedar` for review. Its
isolated checkout preserves the everyday Pine tree and older diagnostic Cedar
checkout/Phaser edit. Retire this development worktree after review and
integration into Cedar, subject to the lifecycle audit. Cedar-to-Pine (#26) and
Pine-to-main (#23) remain later integrations; no merge is performed here.
The 89 loose generated runners have a verified external local archive and
manifest; historical scientific runs and build worktrees retain their paths.
No repeated native optimization or unchanged derivative audit is requested.

C96 validation: **5528 passed, 276 subtests passed in 766.84s (0:12:46)**; 215 focused tests and seven subtests
pass, including both new report regressions. Two existing test fixtures now
canonicalize owned macOS temporary paths; a fake optimizer timeout test allows
interpreter/help startup before testing descendant cleanup. Production symlink
guards and timeout limits are unchanged. Real C95 public CLI readback passes
with all 38 bundle files unchanged and zero SDK/process attempts. Compilation,
whitespace and rendered figure checks pass. Commands and frozen hashes are in
the evidence ledger.

**Returned C81 closes fresh construction of the exact eight-pair fixture.** All
175 payloads, runtime hashes and source bindings verify. Coot 1.3.3 completes;
independent trusted-source replay reproduces nine OP3 deletions, 267 selected
serial repairs, ten graph transports and two unchanged curated rules, with no
raw fallback. All forty-two site identities, twenty declared pairs, thirty-eight
chain-adjacency stacks and sixteen separate plane-order controls verify. The final
model matches the private saved-data prediction exactly. C81 runs no ReadySet or
native interpretation; it is construction and selector evidence, not a full solve.

**Returned C82 stops correctly on invalid generated IGU numerics.** All 364
payloads, the exact 162-member runtime and maintained numerical-authority replay
verify. The nested C81 manifest covers all 175 parent payloads; the original C81
ZIP is absent from this verification snapshot, so no direct original-archive byte
comparison is claimed. Phenix 2.2.1-6174 completes one ReadySet call in 65.95 seconds
with unchanged named heavy coordinates. The generated IGU C2/N3 coordinates
coincide and its bond target is 0.000 Å / 0.020 Å ESD. Source/constructed distances
remain about 1.36 Å. Other long generated IGU bonds and phosphate hydrogen/charge
changes remain recorded. Zero fixed native interpretations run. Preserve this
REVIEW and its correctly triggered guard; do not add an IGU coverage exception.
The exact native causal boundary and any SMILES/seed cause are unobserved.

**Returned C83 passes source-bound isolated recovery.** All 445 payloads, the
163-member runtime and the exact C82 parent verify. The source-native complete
IGU builder finishes in 20.95 seconds with exit zero and `NOT_REPORTED` stopping.
Its separate candidate preserves the neutral source's 37 atoms/39 bonds, charges
and finished source-relative sugar configuration, replacing the zero C2–N3 target
with 1.397 Å / 0.030 Å ESD. Both fixed native cases pass all twenty-one usability
checks, two finite repeated evaluations each and exact covalent/API comparison.
Formal-charge readback is unsupported. The automatic isolated choice is
`source_native_generated` with `CONTINUE_WITH_NOTES`; no CIF approval is required.
Written non-polymer metadata and internal A:6 still require explicit source-bound
DNA/link context. The original C82 REVIEW and all separate source-state findings
remain intact. Original C83 local validation (242 focused / 4,553 full and cold
readback) is unchanged; the return is appended separately in
`mixed_component_recovery_2026_10_24`.

**Returned C84 completes both native reads but retains full native-mechanics
REVIEW; scientific qualification remains unassessed.** All 580 payloads, the 164-member runtime and the exact 445-payload C83
parent verify. Both Phenix 2.2.1-6174 workers exit zero (4.35 / 1.52 seconds),
with 863 atoms, forty-two sites and two fixed evaluations each. All thirty-eight
backbone links, exact declared NARestraints additions, selected linked
projections and PDU/5PC triple targets pass. Full membership retains four
baseline/active heavy-coverage/DNA-group gates. All forty-two actual native
classifications are DNA, with exact site membership and no unexpected atoms;
seven written groups differ, ten sites record only OP3 coverage notes, and
selected IGU A:6 has complete heavy inventory. Those gate verdicts stay intact.
Original C84 local validation (343 focused / 4,598 full and cold) is unchanged and its failed receipt
is retained.

Its reader exception is an evidence-order defect: only two UNSUPPORTED formal-
charge `unavailable` lists reorder their thirty-four unique complete atom rows
after JSON sorts the preparation dictionary's keys. All other fields and the
REVIEW verdict match. Repair that exact serialization boundary without relaxing
any classification, coverage, native or source-state gate. The actual return is
appended in `mixed_linked_recovery_2026_10_24`.

**Returned C85 closes saved-native replay.** All 584 payloads and the complete
580-payload C84 parent verify. The summary and scientific reader reproduce exactly
with zero new / two historical native calls. All 132 scientific files, original
qualification/model hashes and the fallback decision remain unchanged. The same
four coverage/written-group gates retain REVIEW; no scientific qualification or
chemistry change is implied. Original local C85 validation (395 focused / 4,636
full and cold replay) remains unchanged, with the actual return appended in
`saved_mixed_linked_recovery_2026_10_24`.

**Returned C86 reaches a modifier grammar failure before model interpretation.**
The first installed Phenix worker exits two while loading the single-row 1AP
OP3 modification; active native read and full qualification do not run. The CIF
writer emits scalar items for one row, but the native modification reader needs
a loop table. Original C86 local validation (413 focused / 4,710 full and cold)
remains unchanged in its prepared-input/fake-tool scope. All 697 payloads and
the exact C85 parent/manifest verify; maintained context/parent replay preserves
all 110 context files and the fallback with zero verification processes. The
failed worker runs 4.000682 seconds, interprets no model atoms and evaluates no
energy; all ten OP3-only modifiers use the same scalar shape.

**Returned C87 passes native context mechanics.** All 865 payloads and the exact
C86 parent/manifest verify. Both Phenix 2.2.1-6174 workers exit zero, with 863 atoms,
forty-two complete DNA sites and two fixed energy snapshots each. All thirty-four
membership and both sets of twenty saved-parent equivalence checks pass. The
qualification has 291 PASS / 24 unsupported formal-charge checks, no contradiction,
and `MIXED_CONTEXT_MECHANICS_PASS`. Source/scientific findings remain separate.
Original local C87 validation (451 focused / 4,748 full and cold) is unchanged.

The envelope fails only because 132 positions among 315 unique check rows reorder
after JSON sorts site-projection keys. All typed complete rows, nested lists,
other fields and the PASS verdict match exactly. Preserve original failed receipt,
report and qualification; this is an evidence-order defect.

**Completed C88 delivery:** `88_Cedar_probe_mixed_context_replay.py`, using
`scripts/build_mixed_context_probe.py --delivery-prefix 88_Cedar` and
`--saved-native-only` on exact C87. Context-local check IDs get deterministic
writer order and strict legacy row-permutation replay. Only this top-level order
changes; the existing formal-charge compatibility rule, other nested order,
shared C85 helpers, chemistry, native kernels and hard gates stay unchanged.
Context schema 1 and policies v1/v2 remain; no old payload is rewritten.

The maintained reader uses temporary external context/linked-parent views and
emits compact `saved_mixed_context.json` references under `parent_review`, with
its receipt pointer under `probe_directory`. Preserve every original C87 payload
once through indexed transport; do not copy the old scientific subtree. Historical
native calls are two; new SDK discovery/native/generator/optimizer calls are zero.
Original continuation notes and native usability are retained automatically,
without student CIF approval. Final focused validation passes 512 tests in
25.61 seconds across nineteen files on `aaed1955b166c507ba94be8157bf1bc89c69fd6e`.
All sixty-one new cases (twenty-eight module, thirty-three ferry) are frozen
before full collection. The full suite passes 4,809 tests, two skips and
276 subtests in 599.28 seconds, with no source/script/test changes after the
checkpoint or later supplement. Source-removed cold saved replay preserves all
865 C87 payloads plus its manifest and all 297 scientific/context/parent files
exactly, emitting only a 1,088-byte summary. The standalone reader reproduces
315 checks and the original mechanics PASS from the copied new capsule after
original ZIP/session/runtime removal and explicit owned-view retirement; guarded
automatic cleanup is not claimed. SDK discovery, context audit and process calls
are forbidden; configuration, everyday edits and store fixtures remain intact.
Returned Mac C88 saved replay is now verified: all 869 payloads and all 866 C87
members remain exact. The 1,088-byte summary, all 315 original checks and all 297
scientific files reproduce unchanged, with two saved and zero new native calls.
The original mechanics PASS and `CONTINUE_WITH_NOTES` decision remain intact.
The actual return is appended to `saved_mixed_context_2026_10_24` without changing
its original local validation or historical pending-at-publication record.

**Completed C89 delivery:** `89_Cedar_probe_mixed_initial_gradients.py`, built by
`scripts/build_mixed_gradient_probe.py` from the exact C88 capsule. Run one fresh
initial-only corrected-gradient audit of the exact active mixed manager before
geometry optimization. This 863-atom/forty-two-site manager has fifty-eight plane
restraints; the old 877-atom/forty-three-site geometry proof cannot substitute for
its own fresh qualification. Match saved native identities, definitions, policy
and raw evaluations first; then use the unchanged corrected fixed evaluator,
sampled global/category derivatives, both plane orders and tilted/rotated controls.
The report is `mixed_initial_gradients.json`, policy
`cif-mixed-initial-native-gradient-v1`, with explicit context/linked-parent anchors
and independently replayed numerical evidence. `--inspect-only` makes no SDK call.
One bounded fresh native worker is allowed; no optimizer is requested. Preserve
C88 ancestry once with the existing archive bounds and no scientific-tree copy.
Focused validation passes 600 tests across twenty-two files in 83.01 seconds on
`cad81fb394433767d270577cfbc923792672c01f`. All 106 final new cases (61 module /
45 ferry) are frozen before full collection. Actual-parent inspect passes with
zero SDK calls, 455,931 prepared bytes, 3,328 plane pairs and all 297 scientific
files exact. Source-removed cold inspect also passes: 166 runtime members and
918 payloads plus manifest preserve C88 once, with the standalone explicit-parent
reader passing after source clones/original input/session/runtime removal. All
165 context, 132 parent and 46 new files stay exact, with zero SDK/subprocesses.
The capsule is 122,235,229 uncompressed bytes, leaving 11,982,499 bytes below the
unchanged cap. Configuration, everyday edits and store fixtures remain intact;
164,380 guarded path operations stay within 232 absolute/68 component bytes.
Temporary views are explicitly retired; automatic cleanup is not claimed.
The full suite passes 4,915 tests, two skips and 276 subtests in 694.66 seconds
on the same frozen checkpoint. No source, script, test or figure edits follow
full collection and there is no supplement. Returned Mac C89 now fully verifies:
one Phenix 2.2.1-6174 job completes in 24.122224 seconds; all eight gradient families,
all fifty-eight planes in both orders and six tilted/rotated controls pass. Native
energy, coordinates, definitions and static constraints remain fixed. The actual
return is appended separately to `mixed_initial_gradient_audit_2026_10_24`; the
original local evidence and historical pending-at-publication values stay exact.

**Completed C90 delivery:** `90_Cedar_probe_mixed_geometry.py`, built by
`scripts/build_mixed_geometry_probe.py` from the exact C89 ZIP. Run one optional
1,000-iteration/600-second geometry trial from the qualified initial state, using
the unchanged geometry worker, corrected evaluator, optimizer and atom-identity
serializer. A new adapter checks the actual C89 proof rather than borrowing old
three-case evidence. Check full/rounded endpoint derivatives and one fresh native
PDB readback with all fixed NARestraints proxies and source authority unchanged.
Select a qualified separate endpoint whose fixed objective does not worsen, or
retain the usable initial model with notes; usable nonconvergence is not student
CIF review. Descriptive pucker and chirality findings remain separate from exact
restraint definitions and mechanically unusable evidence.

Preserve the exact 10,963,258-byte original C89 ZIP once as opaque
`inputs/parent_review.zip`. Its complete 937 payloads and manifest remain intact;
do not flatten 128,249,071 bytes of ancestry into the next capsule. Materialize
only the three explicitly anchored scientific views temporarily, never execute
captured programs, and retain the existing 128 MiB/32 MiB/1,024 outer bounds.
The report is `mixed_geometry_trial.json`, schema 1, policy
`cif-mixed-qualified-geometry-trial-v1`. Inspect is SDK-free; a full diagnostic
uses at most two native jobs including candidate readback. Focused C90 validation
passes 917 tests across thirty files in 149.00 seconds on
`f759d4c9561d0af1a82d5f9336eb1fa8496f2fb4`; all 116 final new cases (64 module /
52 ferry) are frozen before full collection. The real C89 prepared trial and
reader pass with zero SDK processes, 53 files and 7,256,286 bytes. The genuine
863-atom adapter passes and rejects a tampered proof without SDK calls. The full
suite passes 5,031 tests, two skips and 276 subtests in 718.58 seconds at that same
checkpoint. Source, script, test and figure bytes remain frozen after full
collection, with no later supplement. Source-removed inspect and standalone
readback pass after removing the original session, runtime and input archive:
zero SDK/subprocess launches, 167 runtime members, 57 outer payloads plus manifest
and 18,257,745 uncompressed bytes. The original 10,963,258-byte C89 ZIP remains
byte-exact once, with its 937 payloads and original manifest. The new data uses
7,285,687 bytes and leaves 115,959,983 bytes under the unchanged 128 MiB bound.
All 65 gradient, 165 context, 132 parent and 54 new scientific files reproduce
unchanged. The path guard checks 125,071 operations at maximum path/component
lengths of 232/45 bytes; user config, authorized edits, the component store and
ambient import isolation remain intact. Owned temporary views are explicitly
retired; guarded automatic cleanup is not claimed. These original local checks
precede the actual C90 return below. Scientific/source-state findings, ordinary
full-run qualification, refinement, cache publication and production adoption
remain separate. The record is `mixed_qualified_geometry_trial_2026_10_24`.

Returned C90 completes one Phenix 2.2.1-6174 geometry worker in 53.99432 seconds.
The fixed target falls from 27,518.185419949943 to 4,294.46458796323 (84.394%)
over 257 iterations and 311 calls, then stops on a line-search rounding error.
This objective decrease does not qualify the endpoint: the full-precision global
and dihedral audits each retain three REVIEW directions out of twenty-one;
the other six families pass, while all eight PDB-rounded families pass. Repeats,
snapshot matching and target/gradient additivity remain consistent. The saved
full-precision gradient norm is 88,852.6173130985, versus 14,419.934751481616 after
PDB rounding. Native candidate readback does not run. The report retains its
`Mixed geometry evidence does not reproduce` finding and automatically keeps the
verified usable initial model with `CONTINUE_WITH_NOTES`; no student CIF approval
or production adoption occurs.

The strongest endpoint forces involve the PDU propynyl atoms C5A/C5B/C5M at D:5.
Its triple-bond distance is about 1.196736 Å against a 1.203 Å target, with an
adjacent angle about 179.999810°. These observations motivate a fixed-coordinate
torsion-conditioning test; they do not establish a native gradient defect.
All 76 returned payloads, the trusted 167-member runtime and exact opaque C89
archive verify; all 937 C89 payloads and its original manifest remain byte-exact.
Independent maintained read-only replay reproduces the original `REVIEW`, one
historical native call and the same initial-model selection in 38.73 seconds.
All 435 scientific-view files remain unchanged, with SDK discovery, new native
calls, pickle loading and captured-program execution forbidden. The actual return
is appended separately to `mixed_qualified_geometry_trial_2026_10_24` without
changing its original local validation. Source chemistry, static
constraints, scientific qualification and ordinary full-run scope remain separate.


The unchanged candidate-readback helper retains a narrow diagnostic counter
limit: if `wait` raises `OSError` after launch, its receipt can omit `returncode`.
`new_native_calls` follows completed/stopped receipt evidence and may undercount
that launch. The maximum two requested SDK workers and the verified usable
starting-model fallback remain enforced. This is recorded for maintainers,
without changing the shared helper or adding a student decision.

**Completed C91 delivery:** `91_Cedar_probe_mixed_torsions.py`, built with
`scripts/build_mixed_torsion_probe.py` and `scripts/mixed_torsion_probe_template.py`
from the exact returned C90 capsule. Audit the saved endpoint's ordinary dihedral proxies and
near-linear conditioning without another optimizer. Rebuild from explicit
geometry/gradient/context/linked-parent views and bind the C90 archive checksum;
use the unchanged native numerical kernels, chemical definitions and NARestraints
policy. Generic geometry/gradient ranking across the initial and both endpoint
precisions selects up to six near-linear proxies and two atom-disjoint non-near-
linear high-gradient controls, capped at eight. Record bond-path support, the
five-degree sine screen and any truncation; preserve zero-weight constant torsions
as separate inventory. All three cases, both endpoint orders, single/container
comparisons, up to fourteen local directions and seven steps from 1e-3 through
1e-9 Å separate scale-sensitive
conditioning from reproducible arithmetic disagreement. Keep the original four
coarse steps and three finer steps distinct; adjacent-step agreement is diagnostic
and cannot requalify the endpoint. Use the unchanged native torsion evaluator.
Check full/selected/remainder energy and gradient sums without omitting any
active restraint.

Use `cif_mixed_torsion.py`, schema-1 `mixed_torsion_audit.json`, policy
`cif-mixed-fixed-torsion-audit-v1` and local anchor `mixed_torsion_directory`.
The audit/reader take four explicit parent views plus the original C90 SHA-256.
At most one native worker runs: 120 seconds by default, 600 seconds maximum,
10,000 paired kernels and 600 group evaluations as separate diagnostic caps. The
unchanged native energy worker additionally records two initial raw full-manager
snapshots for source/manager binding in `native_validation.energy_inventory`;
the diagnostic pair/group counts are not a total of every kernel in the job.
SDK-free inspect remains separate.
`MIXED_TORSION_AUDIT_COMPLETE` describes completed bounded evidence/arithmetic
replay, not a derivative approval or proved bug. Keep disagreement as findings;
missing/unreproducible evidence stays `REVIEW`. The module/report are additive;
existing readers, production paths and earlier run schemas are unchanged, with
no migration of saved artifacts.

Preserve the exact 12,504,004-byte C90 ZIP once, including all 76 parent payloads
and manifest and its nested original C89 ZIP. Retain existing archive limits,
explicit temporary views, captured-code-as-data rules and verified usable initial
fallback. No optimization, mechanics/chemistry change, generation, adoption,
cache publication, refinement or student CIF approval is requested. SDK-free
selection on the actual parent inventories 975 terms (607 positive ordinary /
368 zero-weight constants), selecting six near-linear rows without truncation
and two disjoint controls; all eight have native bond-path support. No native
kernel runs. The maximum schedule is 9,504 paired kernels and 528 group calls,
within 10,000/600. All 131 final new cases are frozen before full collection:
66 module cases pass in 67.57 seconds and 65 ferry cases pass in 3.09 seconds.
The initial fail-before subsets are nine module failures in 3.12 seconds and
four ferry failures in 0.24 seconds, distinct from final counts. Frozen checkpoint
`c6a3743f4294a7cce4b87d9053a7952a95799b13` contains all source, scripts, tests and
figure changes. Actual-parent SDK-free preparation and standalone exact replay
pass in 152.49 seconds (105.75 seconds for preparation including publish replay),
with 435 protected files unchanged and zero SDK calls. `PREPARED_ONLY` retains
the original C90 REVIEW and usable initial selection. Combined focused validation
passes 1,133 tests across thirty-five files in 229.90 seconds on the same frozen
checkpoint. All 131 final new cases enter complete-suite collection before
launch. The complete suite passes 5,162 tests, two skips and 276 subtests in
862.21 seconds on that same checkpoint, with source, script, test and figure
bytes frozen after collection and no later supplement.

Source-removed inspect and standalone readback pass after removing the original
session, runtime and input archive, with zero SDK/subprocess launches. The frozen
runtime has 168 members. The new outer capsule has 50 payloads plus manifest and
18,366,235 uncompressed bytes; its largest member is the exact 12,504,004-byte C90
ZIP, preserved once with all 76 payloads and its manifest. The embedded original
C89 archive also remains byte-exact, with all 937 payloads and its manifest.
New data occupies 5,854,629 bytes, leaving 115,851,493 bytes under the unchanged
128 MiB cap without duplicating old scientific trees. All 73 geometry, 65
gradient, 165 context, 132 parent and 47 new files replay unchanged. The path
guard checks 186,255 operations at maximum path/component lengths of 231/45 bytes;
configuration, authorized edits, the component store and ambient import isolation
remain intact. Five owned temporary views are explicitly retired; guarded
automatic cleanup is not claimed. The report stays `PREPARED_ONLY`. Actual Mac
C91 fixed-endpoint execution was pending at that original validation checkpoint;
its actual return is recorded separately below. Scientific qualification and the
ordinary full run remain separate.
The new record is `mixed_fixed_torsion_audit_2026_10_24`.

### Returned fixed-endpoint torsion evidence

Returned C91 completes one Phenix 2.2.1-6174 worker in 6.156328 seconds. All 68
payloads and their manifest verify; the exact compressed C90 archive and its
embedded C89 archive remain byte-identical. The 168-member runtime and reported
runner hash reproduce exactly. All 9,504 paired single/container and 528 group
evaluations complete within their separate limits. Full/selected/remainder
attribution, saved-family agreement and finer group derivatives pass at all
three saved coordinate cases. Initial and PDB-rounded local derivatives pass.

Six full-precision local direction/order pairs remain under review: three unique
directions in both orders of one PDU D:5 C5-C5A-C5B-C5M torsion. Every smallest
1e-9 Å sample agrees within the original tolerance, but 1e-8 Å does not, so the
required adjacent passing pair is absent. The roughly hundredfold error decrease
for a tenfold step reduction supports second-order finite-step conditioning near
collinearity; it does not establish a native analytical-gradient defect. This
returned component/site is an observation, not a selection exception.

Maintained SDK-free replay reproduces the report in 52.203912 seconds, preserving
all 500 staged scientific files with zero subprocess, native or pickle calls.
Original C90/C91 records and C91 local validation remain unchanged. C91 does not
requalify the endpoint: `verified_constructed_model` remains selected with
`CONTINUE_WITH_NOTES`, source-state findings and scientific qualification intact.

### Qualified mixed runtime handoff (C95)

Returned C94 is verified independently on Linux: exact qualification and all
five selection gates reproduce; all 693 scientific files are preserved and no
new process runs. The original nonconvergence remains recorded. Comparison
counts and maximum observed roundoff are platform-local observations; both
recipes and passing verdicts reproduce. The C94 publication-time validation
record remains unchanged; its returned evidence is recorded separately.

C95 supplies a separate portable mixed-runtime activation test through the
existing public `cif-doctor assess --bundle` reader. It freezes the exact
selected PDB, dictionaries and PHIL order alongside one opaque C94 capsule,
then relocates the owned bundle before public assessment. Resolution uses six
bounded temporary data views and the maintained saved reader; no fresh native
or derivative evaluations run. The legacy single-component policy remains
supported. No merge, checkpoint, diffraction run or scientific approval is
authorized by this handoff. See the
[C95 contract](cif-doctor.md#qualified-mixed-runtime-handoff-c95).

### Portable saved-endpoint report replay (C94)

Returned C93 qualifies its saved endpoint on Phenix 2.2.1-6174: six local and
six broader rechecks pass in 228 evaluations, retaining 330 earlier passing
directions. All seventeen native PDB mechanics checks pass and the endpoint is
selected with notes; C90 nonconvergence and scientific boundaries remain.
Independent Linux replay reproduces derivatives, serialized PDB bytes and
native mechanics. The original strict reader fails only on descriptive angle
roundoff, with a maximum difference of 5.684341886080802e-14.

C94 retains the exact C93 producer/worker/reader and adds a separate saved-data
adapter. Its generic comparator propagates a small roundoff allowance only
through three calculated scalar fields. Chemical parameters, identities,
warning/sign/rank classes, recipe bytes and derivative checks stay exact.
The complete C93 ZIP remains opaque and byte-identical, with nested ancestors
preserved once. The new test requests zero native processes and no optimization.
The [C94 contract](cif-doctor.md#portable-saved-endpoint-report-replay-c94) owns
schemas, bounds, methods and validation; ordinary pipeline handoff is the next
integration gate after this replay. No merge is authorized.

### Uniform saved-endpoint resolution window (C93)

Returned C92 completes one Phenix 2.2.1-6174 audit in 9.307028 seconds,
using 204 recorded adaptive calls. All six flagged local direction/order rows
and five of six failed original whole-objective/family directions now qualify.
The full-precision `all/alternating_global` row passes at 1e-8 A, but smaller
steps fail the conservative representation-resolution screen. It lacks two
adjacent resolved passing steps. The original usable constructed model remains
selected automatically with `CONTINUE_WITH_NOTES`; native PDB readback does not
run. This is a numerical-window limitation, not evidence of a new native
analytic-gradient defect. The exact C92 archive SHA-256 is
`5171aa1ba972b5b3fea0a377e5c91e07a798d963162e89c486334743ce4c0371`.

Returned C93 qualifies all six local and six broader derivative rechecks,
retains 330 earlier passing directions, and passes all seventeen native PDB
mechanics checks. It selects the saved endpoint automatically without another
optimizer. Independent Linux replay reproduces derivatives, PDB bytes and
native mechanics, but the original reader rejects last-bit differences in
calculated angle summaries. C94 adds bounded descriptive-report replay while
keeping chemistry, derivative evidence, native proxies and warning classes
exact. No new native process or student CIF inspection is requested; ordinary
full-run integration and scientific qualification remain separate.

See the [C93 contract](cif-doctor.md#uniform-saved-endpoint-resolution-window-c93) for
exact schemas, bounds and the distinction between diagnostic selection and
production adoption. No merge, full diffraction run or new optimization is
authorized by this delivery.

### Guarded qualification of a saved endpoint (C92)

C92 qualifies the already saved endpoint through a separate evidence policy;
it does not rerun optimization or relabel the original C90/C91 verdicts. Its
inputs are five explicit torsion, geometry, gradient, context and linked-parent
views, bound to the exact original C91 archive. The bound C91 report supplies
the C90 checksum required by the unchanged earlier reader. All source chemistry,
NARestraints pairing/stacking authority, native kernels and previous run artifacts
remain unchanged.

Methods: select unresolved local direction/order pairs from verified C91 evidence
and reconstruct the exact failed original C90 whole-objective/family directions,
without residue-name or proxy-index exceptions. Retain every original positive
sampled proof. At fixed coordinates evaluate a six-step resolution window,
1e-7, 1e-8, 3e-9, 1e-9, 3e-10 and 1e-10 Å, using the same absolute/relative 1e-4
tolerances. These are fresh observations, not six steps all smaller than C91's;
the wider window is needed when the tiniest displacements become quantized.
Require two adjacent passing new samples, actual representable central
displacement, central symmetry and derivative floating-point resolution.
Representation and target-ULP resolution screens each consume at most ten percent
of the unchanged comparison bound; they do not rigorously bound every internal
native-kernel error. Fresh repeated baselines for all eight
families at the initial, full-precision and PDB-rounded coordinates must match
the pinned sources, exact manager and saved objective. Failed, unresolved or
unsupported numerical evidence cannot qualify a new endpoint.

Only positive complete sampled derivative evidence permits serialization of the
saved endpoint and a conditional fresh native PDB readback. The unchanged atom-
identity serializer and native definition/proxy validators must pass, and the
same fixed objective must not worsen, before the separate endpoint can be
selected as `qualified_geometry_endpoint`. Any failed or missing optional gate
retains `verified_constructed_model` automatically, with notes. Native stopping,
sugar pucker, source-state limitations and scientific qualification stay distinct
from this selection; students do not inspect or approve CIF tables.

The additive schema-1 report is `mixed_endpoint_qualification.json`, policy
`cif-mixed-saved-endpoint-qualification-v1`, anchored at
`mixed_endpoint_directory`. The API is `qualify_saved_mixed_endpoint` with
`read_saved_mixed_endpoint` for independent saved arithmetic replay. A fresh
adaptive worker and at most one conditional native readback are allowed, with a
120-second default and 600-second maximum deadline. The shared adaptive budget
is 2,000 calls and 128 selected direction/order or family-direction rows; its
maximum schedule needs 1,840 calls including 48 fresh family snapshots. The
actual verified parent selects six local and six family rows, scheduling 204
calls including those 48 snapshots. Two initial raw full-manager bootstrap
snapshots are recorded separately and are not part of the adaptive-call counter.
`PREPARED_ONLY` means no SDK execution. `ADAPTIVE_ENDPOINT_DERIVATIVES_PASS` describes the new sampled proof;
`MIXED_ENDPOINT_QUALIFIED` additionally requires serialized native readback and
selection gates. Neither status proves convergence or scientific correctness.

`scripts/build_mixed_endpoint_probe.py` and
`scripts/mixed_endpoint_probe_template.py` build `92_Cedar_probe_mixed_endpoint.py`.
The ferry preserves the exact original C91 ZIP once; C90 and C89 stay nested and
byte-exact, with only five declared temporary views materialized. Existing
128 MiB total, 32 MiB member and 1,024-entry bounds remain. Captured programs stay
data. No optimizer, generator, Coot, ReadySet, chemical/mechanical edit, cache
publication, refinement or production adoption is added.

All 149 final new cases are frozen before complete-suite collection at
`514db13083e50ac75d53cbf325b7e242dabb7443`: 61 module cases pass in 116.41 seconds
and 88 ferry cases pass in 5.13 seconds. The module suite executes the actual new
adaptive worker and conditional native PDB readback through a pinned fake SDK;
no installed Phenix execution is claimed. Initial fail-before subsets record
four core API, seven core integration and four ferry failures, separately from
the final case totals. Broader focused validation passes 1,282 tests across
thirty-seven files in 446.93 seconds on the same frozen checkpoint. The complete
suite passes 5,311 tests, two skips and 276 subtests in 1,027.37 seconds. All eight
source, script, test and figure hashes remain frozen after collection, with no
later supplement. Final source-removed inspect and independent replay also pass;
the actual Mac C92 result is recorded separately under C93.

Source-removed inspect and standalone replay pass at the same frozen checkpoint.
Both original source clones are gone before launch; the original session, runtime
and input archive are removed before independent readback from the new capsule.
The 169-member runtime is fixed by SHA-256. The outer archive contains 54 payloads
plus manifest and 23,571,221 uncompressed bytes. Its largest member is the exact
15,023,841-byte C91 archive, preserving all 68 parent payloads and its manifest;
C90 and C89 remain nested and byte-exact, with 76 and 937 payloads respectively.
New data occupies 8,539,119 bytes, leaving 110,646,507 bytes beneath the unchanged
128 MiB bound. No ancestor scientific tree is duplicated.

All 65 torsion, 73 geometry, 65 gradient, 165 context, 132 linked-parent and 51 new
files replay unchanged, with zero SDK, native-discovery or subprocess calls.
The Mac path guard checks 370,241 operations at maximum path/component lengths
of 237/45 bytes. Configuration, the authorized everyday edit, the component
store and ambient import isolation remain intact. Thirty-two owned temporary
views are explicitly retired; guarded automatic cleanup is not claimed.
QA-only in-place forbidden-entrypoint guards and import-only profiling preserve
existing function aliases. Independent review blocks all 105 canary calls and
preserves 129 source files; process, captured-code, original-path, archive and
preservation guards remain unchanged. No application source or native kernel is
changed by this QA instrumentation. The inspect report remains `PREPARED_ONLY`;
the actual Mac C92 native return is recorded separately under C93; scientific approval remains open.

The C92 delivery remains pinned at
`3f604b3ec4b1295ca3067d1fc5a4ddaa08d7031a`; its original local validation and
returned REVIEW are preserved separately. C93 was delivered at
`1833b41424c958aee9d5c477edf1df723e532804` and has now returned qualified native
endpoint evidence. The current C94 saved-only replay uses that exact C93 capsule
and the same one-block Git/worktree/build/run contract. Its methods/evidence key
is `mixed_saved_endpoint_portable_replay_2026_10_25`; C94 adds no native cycle.


**Returned C80 completes Coot but retains context review.** All 138 payloads,
the exact runtime, forty-two site identities and source/preflight artifacts verify.
The curated DF A:19 raw backbone invalidates the discarded phosphate shadow with
an implausibly short incoming O3'-P link. Eight generic sites retain their raw
coordinates, two graph transports pass, and two curated rules complete. DF still
has OP3 absent from its frozen parent, so the independent scaffold guard correctly
stops before the constructed twenty-pair compiler. Do not relax that guard or
call the canonical input a qualified mixed model. The original REVIEW, raw model,
sources and completed Coot output remain immutable.

C81 admits source-graph-valid curated DNA to the same discarded frame preflight
and parent-scaffold shadow. Only existing-sanitizer-proved internal OP3 deletions
and authorized selected serial repairs reach the original raw coordinates. The
existing curated final placement, graph transport, phosphate sanitizer, source
authority, NAR policy, passthrough and inherited-CONECT guards stay intact.
An additive `curated_context` receipt binds eligible/candidate sites to source and
parent hashes. Private exact-C80 saved-data replay is local evidence only; there
is no new public replay API, captured-Python execution or new local native call.
Final combined focused validation passes 132 cases in 26.45 seconds across seven
files, including eight new context and seven source/parent/site/candidate/scope
binding cases. All fifteen new cases enter full-suite collection before launch. Exact
saved-C80 replay proves nine OP3 deletions and 267 selected serial repairs, ten
graph transports plus two unchanged curated rules with no raw fallback, the
independent mixed/context audit and unchanged final phosphate recheck at all
nine sites. All twenty declared pairs/thirty-eight stacks/sixteen separate controls
compile and pass portable policy readback. Every original source/raw/parent input
is preserved; subprocesses are forbidden. Source-removed cold replay also passes
on `b568129b639aba400680b61b90378f7486f70d8c` with all sixteen exact C80 sources,
including captured real DC; no synthetic DC or fresh SDK qualification is used.
The standalone policy survives removal of original scientific inputs, candidate
and runtime paths. Configuration, everyday edit and storage are preserved;
ambient import, temporary alias and macOS byte-budget checks pass. Maintained
C76 and all prior-lineage replay pass under the current code, with subprocesses
forbidden and original reviews/fallbacks preserved. The full suite passes 4,491
tests, two skips and 276 subtests in 424.25 seconds, with all fifteen new cases
collected before launch and no supplement. These original local checks remain
unchanged. The subsequent fresh C81 return passes construction; active native
membership remains unassessed.
The record is `curated_phosphate_context_2026_10_23`; C80 original local validation
and its separate returned outcome remain in `mixed_eight_pair_construction_2026_10_23`.

Keep the exact eight requested pairs at sixteen sites, twelve canonical background
pairs, thirty-eight declared chain-adjacency stacks and sixteen separate
plane-order controls. The latter are compiler controls, not sixteen physical
stacking edges or doubled active restraints. ATL remains independent, active
native membership is unassessed, and students do not approve CIF tables.

**Returned C78 closes whole-model cached ReadySet readback.** All 8,741 payloads,
the exact C76 parent and its manifest verify. Phenix 2.2.1-6174 completes one
ReadySet control (8/8 checks, zero observed builder/template calls, one checked
memory query) and two fixed native reads. Before and after each pass 93 checks
with three unsupported formal-charge readbacks. All 28 roundtrip checks preserve
38 links, 3,148 unaffected restraints, exact numerics and heavy coordinates.
`CONTINUE_WITH_NOTES` selects `readyset_checked_model`; no student CIF review.

**C79 integrates the qualified argument representation into ordinary PostMR.**
Pass every normalized selected component separately, including curated and ordinary
fallback sources. Preserve the combined artifact/legacy receipt reference and add
ordered portable actual-input references. Source/cache precedence, native actions,
NAR and all scientific guards are unchanged. Local validation passes 139 focused / 4,408 full tests (two skips, 276 subtests),
including five fail-before cases and source-removed cold ordinary-route checks. No new Mac cycle is needed solely to repeat the
already-qualified C78 argument representation.

**Following scientific boundary:** native dictionary/link/triple-target and
full declared NARestraints membership on the qualified eight-pair fixture, then an ordinary
end-to-end report with observations. The old DP A:6 versus C C:10 control is not
pair intent; C80 explicitly places DZ:DP at A:12/B:4. The legacy Saenger-only
compiler is unchanged. Preserve all historical runs and do not fabricate MR
success, a checkpoint or a diffraction full run.

**C77 stopped before native execution on macOS.** The user trace reports errno
63 during deeply nested history staging and again during failure reporting; no
C77 ZIP exists. Its reported runner SHA matches the published code with only NAR
dirty-state metadata changed. Local C77 Linux tests remain valid in that scope;
they did not simulate the macOS path limit. Preserve the failed directory/worktree.

**C78 delivery and original validation:** `78_Cedar_probe_review_transport.py`, same explicit
`--postmr-cached-model-only` action on exact C76, not incomplete C77. Indexed v2
staging keeps all original logical names/bytes behind short hash-derived paths;
export restores the original parent members and manifest. Materialize the declared
shallow C29 prerequisite view for existing scientific APIs. Native definitions,
per-component arguments, strict gates, fallback, cache identity and NAR remain
unchanged. Robust failure reporting preserves the first error and can export
verified input members from memory when staging is incomplete. Record
`indexed_review_transport_2026_10_23` contains the simulated consumer-limit,
source-removed relocation and regression evidence. Returned Mac C78 passes as recorded above.

**Returned C76 passes initial full-model native mechanics; ReadySet remains under review.**
All 6,691 payloads and exact C75 lineage verify. Native result: 93 PASS, three
unsupported charge readbacks, 38 links and 3,148 unaffected named terms preserved.
ReadySet preserves cached numerics/heavy coordinates but calls three builders.
The strict guard retains `verified_constructed_model`; no endpoint native readback.

**C77 delivery and original validation:** `77_Cedar_probe_postmr_component_inputs.py`,
`--postmr-cached-model-only` on exact C76. Freeze the already-prepared component
files separately, require exact parameterization/coverage/recombination and pass
one repeatable CIF argument per file. All native gates/actions and fallback stay
unchanged. The combined-container registration explanation is source-supported;
a native parser return-type probe has not independently established it. Existing
ordinary orchestration remains unchanged pending this explicit Mac diagnostic.
Readers preserve v1 reports and honor only exact opaque-exclusion metadata;
no serialized payload is loaded. Record `readyset_component_input_registration_2026_10_23`
contains validation and limits. No student CIF inspection, install or NAR release.

**Returned C75 closes isolated ordinary ReadySet consumption.** All 5,949
payloads, exact C74 parent, 161-member runtime inventory and reported runner SHA
verify. Only NAR dirty-state metadata differs from the published clean build.
All three Phenix 2.2.1-6174 controls pass: 24 consumption checks, 63 native
usability checks and six finite repeated fixed evaluations. Each captures 28
sources and classifies its sole subprocess as the exact CCTBX Mac memory query;
zero builder/template calls and zero unclassified children are observed. Full
maintained replay verifies source AST/callers, frozen numerics/full-H seeds,
worker/spec/output/consumer and triple reports without captured-code execution.
Original C73/C74 reviews and retained torsion/bending/nonconvergence notes survive.

**C76 delivery and original validation:** `76_Cedar_probe_postmr_cached_model.py`, explicit
`--postmr-cached-model-only` on exact C75. Resolve its source-bound numerical
copies and the immutable C63 full constructed model. Reprepare the same three
source-qualified linked contexts, require native usability against the verified
saved canonical reference, then run one whole-model ordinary ReadySet control
and one fixed native readback. Compare all 38 backbone links and every named
proxy/definition exactly. A verified start remains automatic fallback with notes.
The wrapper changes diagnostic scope/metadata only; native mechanics, source
priority, cache keys, producer notes, ordinary arguments and NARestraints remain
unchanged. No install, NAR release, Coot, optimizer, observations or checkpoint.
Actual Mac C76 evidence is pending. The declared eight-pair/16-stacking live
model and policy membership are the following integration boundary; ATL stays
independent and students do not inspect CIF tables.

C76 validation: **495 focused / 4,323 full tests pass** (two skips, 276 subtests;
436.19 s), including 52 new tests, a scope fail-before and the direct C75-record
adapter regression. The 162-member runtime passes source-removed cold relocated
inspect-only replay of exact C75 with every subprocess and original build-source
read forbidden, poisoned imports and aliased TMPDIR. All 5,949 parent payloads
and manifest survive in 6,626 output payloads. The standalone whole-model bundle
resolves after original evidence removal; the application store is untouched
and the everyday edit survives. All 165 relative document links, 21 mirrored
records, protected mechanics, NAR workbook and eight-pair plan verify. The
editable figure is deterministic, rendered and visually checked. These local
checks prepare inputs; actual Mac C76 native/ReadySet qualification is pending.
See `whole_model_cached_readyset_2026_10_23` for exact technical evidence.

**Returned C74 identifies a native memory query.** All 5,304 payloads, exact
C73 parent, pinned runtime inventory and reported `c03dbb68...` runner SHA verify;
only NAR dirty-state metadata differs from the clean build. DP/PDU/5PC each keep
exact cached numerics/heavy sites and complete Phenix 2.2.1-6174 ReadySet. Their
one Popen call is `DYLD_LIBRARY_PATH=  exec /usr/sbin/system_profiler SPHardwareDataType`.
The complete nearest five-frame prefix identifies libtbx memory introspection
from scitbx neighbor-grid initialization; deeper import frames are truncated.
Caller source files are not in C74, so keep all original v1 reviews and the
explicit zero fixed-native count. Maintained replay reproduces all 24 checks
and the exact recorded trace without executing captured Python.

**C75 delivery and original validation:** `75_Cedar_probe_postmr_resource_queries.py`, same
explicit action on exact C74. V2 adds fresh captured easy_run/introspection/
cubicle_neighbors source, AST call-span checks and the exact literal command
matcher. Keep raw events and distinguish known resource queries from unknown
children. A full checked five-frame prefix is required even if deeper import
frames are truncated. The seven other consumption checks and every scientific
kernel/parameter remain unchanged. Only passing controls receive the unchanged
native/consumer/triple qualification on original C71 full-H seeds. Old v1 reports
remain readable with their original verdicts; no student CIF approval, package,
NAR release or cache migration is introduced. Actual Mac v2 classification and effective native qualification are verified
above; current whole-model/full-run qualification remains separate.

C75 validation: **365 focused / 4,271 full tests pass** (two skips, 276 subtests;
450.86 s), including 48 new permanent tests and two fail-before cases. The
161-member runtime passes cold inspect-only replay of exact C74 after original
build-source removal and relocation, with original build reads and all subprocesses
forbidden, poisoned imports and aliased TMPDIR. All 5,304 original payloads/manifest
survive in 5,796 output payloads; three independent control copies resolve after
owned evidence removal. The store is untouched and the everyday edit survives.
All 165 relative document links, 20 mirrored records, protected mechanics, NAR
workbook and exact eight-pair plan verify; the deterministic editable figure is
rendered and visually checked. Fake SDK query tests and public upstream context
are distinct from the actual Mac source/native qualification recorded above.

**Returned C73 completes ReadySet but retains unclassified child calls.** All
4,830 payloads, the exact C72 parent, pinned runtime inventory and reported
`bac78b5e...` runner SHA verify. Only NAR dirty-state metadata differs from the
clean build. DP/PDU/5PC each complete Phenix 2.2.1-6174 ReadySet with exact cached
effective numerics, unchanged named heavy sites and requested effective actions.
Maintained replay reproduces all 24 checks: 21 true and three false no-subprocess
checks. Each untruncated trace records one Popen constructor call and zero
builder/template calls; it records no child command or caller. No fixed native
readback runs. Keep the generic legacy native_execution label in the old receipt
and rely on its explicit counters. No captured Python executes during replay.

**C74 delivery and original validation:** `74_Cedar_probe_postmr_readyset_subprocess.py`, same
explicit action on exact C73. Record bounded literal args, executable, shell and
cwd plus caller source/function/line fields. Never capture the environment or
coerce opaque values; mark truncation and retain bytes losslessly within bounds.
Every observed child still requires review: no allowlist or native/argument change.
At most three unchanged ordinary ReadySet controls; fixed native checks remain
conditional on all original consumption checks. New receipts distinguish
ReadySet-only calls from fixed native readbacks. Exact cache bytes/keys, producer/
stopping notes, source priority, mechanics and NARestraints remain unchanged.
Actual Mac command/caller evidence, effective native consumption and current
whole-model/full-run qualification remain pending; no student CIF approval.

C74 validation: **317 focused / 4,223 full tests pass** (two skips, 276 subtests;
445.03 s), including 27 new permanent tests. Five new command/caller cases fail
against C73 before the change. The 160-member runtime passes cold inspect-only
replay of exact C73 after original build-source removal and relocation, with
original build reads and all subprocesses forbidden, poisoned imports and aliased
TMPDIR. All 4,830 original payloads/manifest survive in 5,196 output payloads;
three independent input copies resolve after owned evidence removal. The store
is untouched and the everyday edit survives. All 165 relative document links,
19 mirrored records, protected mechanics, NAR workbook and exact eight-pair plan
verify; the deterministic editable figure is rendered and visually checked.
These local checks preceded the actual C74 process trace above; effective native qualification remains open.

**Returned C72 is a source-coverage prelaunch failure.** All 4,482 payloads,
unchanged C71 parent, pinned 160-member runtime and reported `0ecda735...` runner
SHA verify. The source scan captured 24 files but stopped at the routing module;
that module imports the omitted builder. No ReadySet or fixed native readback
launched. Keep the failed receipt's false completion/preservation flags unchanged;
independent maintained replay verifies its four copied 5PC inputs and C71 lineage.

**C73 delivery and original validation:** `73_Cedar_probe_postmr_readyset_consumption.py`, same
explicit action on exact C72. Capture every named observer module explicitly
when the static import scan omits it, with unchanged root/size/hash/budget guards.
Keep the scan's transitive-coverage limit. The captured installed layout replays
as 25 sources; 13 prior builder snapshots agree. New indirect-import regressions
cover builder/no-builder paths and retain missing/escaped/oversized/changed-source
refusals. C73 preserves the failed capsule and uses verified C71 inputs; original
arguments, observation gates, native mechanics and NARestraints stay unchanged.
Its returned ReadySet controls are verified above; child classification and native consumption remain open.

C73 validation: **290 focused / 4,196 full tests pass** (two skips, 276 subtests;
401.79 s), including 22 new permanent tests. Both indirect-import cases fail
against C72 before the fix. The clean 160-member runtime passes cold relocated
inspect-only replay of exact C72 with original build-source reads and all
subprocesses forbidden, poisoned imports and aliased TMPDIR. All 4,482 input
payloads/manifest survive in 4,722 output payloads; three standalone controls
resolve after owned evidence removal. The original store is untouched and the
everyday edit survives. The captured 24-source layout plus a verified prior builder
snapshot becomes 25 sources without executing captured Python. All 165 relative
document links, 18 mirrored records, protected mechanics, NAR workbook and eight-pair
plan verify; the deterministic editable figure is rendered and visually checked.
These local checks preceded the actual returned C73 ReadySet result above; native consumption remains open.

**Returned C71 closes ordinary cache handoff.** The exact
`71_Cedar_6nki0gti_cif_numerical_recovery_review.zip` verifies all 4,231 payloads,
the unchanged 4,008-payload C70 parent/manifest and 159 runtime members. Only NAR
dirty-state metadata differs from the clean pinned build; reconstructing that
field reproduces the reported `971ca54f...` runner SHA exactly.

DP, PDU and 5PC each REUSE their exact C70 source-bound numerical dictionaries.
All 63 unchanged native-usability checks independently reproduce from three
fresh Phenix 2.2.1-6174 reads of normalized inputs; six energy/gradient evaluations
are finite and exactly repeated. Each worker's recorded dispatcher/version,
eight APIs and three energy sources match its selected cache consumer. Existing
normalization changes no bytes; the 31,252-byte combined ReadySet input also
reproduces. PDU/5PC retain active triple/180-degree targets; six complete-H
linear-axis torsions each and seed bending remain descriptive notes.

All three returned run copies resolve after owned source/cache/evidence removal,
with external scientific reads forbidden. Exact old entries, source authority,
consumer and producer/stopping notes survive, including PDU nonconvergence.
No captured Python or new verification subprocess runs. The actual Mac probe
runs three fixed native reads only, without Coot, ReadySet, generation,
optimization, refinement or a production checkpoint. Both ledgers close the
gate under `ordinary_postmr_cache_acquisition_2026_10_23#returned_2026_10_23`.

Ordinary `prepare_postmr` already uses the shared acquisition API before ReadySet.
Coot keeps original sources; eligible cached numerics use existing normalization,
combination and parameterized-input precedence. Missing/corrupt/unsupported or
changed-consumer entries retain ordinary preparation with notes. Recorded identity
matching is not an exhaustive compiled-kernel/energy-library fingerprint.

**C72 delivery and original validation:** `72_Cedar_probe_postmr_readyset_consumption.py`,
`--postmr-readyset-consumption-only` on exact returned C71. It calls ordinary
`_run_readyset` and `effective_restraints` with exact C71 saved numerical inputs.
An optional private process hook executes the selected dispatcher's literal
Python entrypoint with unchanged ordinary arguments; it does not execute the
dispatcher shell. A profile observer records selected builder/template and
Python subprocess calls plus effective actions without replacing native functions.
Keep the distinction between no observed calls and exhaustive optimization proof.

Three separate heavy-only controls retain named heavy coordinates. Passing
controls require eight consumption checks and may receive one fixed native
readback each on the unchanged C71 full-H seed with the effective dictionary.
H coordinates are original saved controls, not ReadySet placements. Maximum
three ReadySet calls, 180 seconds each, plus three fixed reads, 60 seconds each;
no retry, Coot, cache write, refinement or production checkpoint. Preserve original
producer/stopping notes and usable inputs. Inspect-only freezes controls with
every subprocess forbidden. Local validation is recorded under
`ordinary_readyset_consumption_2026_10_23`; its verified prelaunch failure is
recorded above. C73 retry evidence belongs to `readyset_observer_source_retry_2026_10_23`.

C72 validation: **268 focused / 4,174 full tests pass** (two skips, 276 subtests;
406.13 s), including 37 new permanent tests. The final 37-test scope/controller
check also passes. The final 160-member runtime passes cold inspect-only
transport after build-source removal and relocation, with original build reads
and all subprocesses forbidden, poisoned imports and aliased TMPDIR. All 4,231
C71 payloads/manifest survive in 4,470 output payloads; three standalone controls
resolve after evidence removal. The owned everyday edit survives. No actual
Phenix ReadySet execution is claimed; the C72 return stops at source capture.

Current whole-model links and exact NARestraints pairing/stacking remain separate.
Keep automatic continuation/report notes and the exact eight-pair/16-stacking
plan; ATL stays independent. No observations/MTZ or ordinary production PostMR
report is in this capsule, so do not manufacture a diffraction/full NASolve run.
The completed C71 cache gate needs no repeat and students do not inspect CIFs.

Validation basis: **231 focused / 4,137 full tests pass** (two skips, 276 subtests;
389.49 s), including 40 new regressions, cold source-removed/relocated inspect-only
transport and explicit fake-native action-contract checks. Those fake checks are
separate from this actual Mac native return. Runtime and scientific mechanics
are unchanged by recording the return; current native evidence is now verified.
The same 231 focused tests pass again in 26.32 s for this return record.

**Returned C70 closes source-bound cache completion.** The exact
`70_Cedar_vpx276th_cif_numerical_recovery_review.zip` verifies all 4,008
payloads and the byte-identical 3,849-payload C69 parent plus its manifest.
All 158 runtime members match the pinned C70 build. The build differs only
in recorded NAR dirty-state metadata; no terminal runner SHA was supplied,
so no independent reported-runner SHA match is claimed.

DP, PDU and 5PC each report SOURCE_REQUALIFIED_AND_FROZEN followed by REUSED.
Maintained code reproduces all 63 native checks, separate dictionary/native
triple reports and 72 frozen result artifacts, rebasing only explicitly
PROVENANCE_ONLY source paths. All six returned copies resolve independently
after removing the owned original source/cache/evidence directories, with
external scientific reads forbidden. Old entries, exact numerical bytes,
source authority, consumer identity and original producer/stopping notes survive.
PDU's bounded nonconvergence remains a note. Zero new native, ReadySet,
generator, optimizer or refinement processes run; no captured Python executes.

**Returned C69 passes native usability.** All 3,849 payloads, the complete C68
parent/manifest and 158 runtime members verify. Only NAR dirty-state metadata
differs from the clean runner. Phenix 2.2.1-6174 completes all three workers;
all 63 unchanged v2 usability checks and six finite repeated evaluations pass.
The remaining fallback is a later diagnostic caller error: it passes both
`dictionary` and `native` to an auditor requiring exactly one. Keep that
original failure receipt; it is not a failed native qualification.

C70 separates the two read-only reports and validates native worker/spec/input/
output hashes, exact consumer identity and all 63 checks before using saved
qualification. Source selection is an owned replay of exact C69 ordinary bytes
and authority, not a new live installation selection. Cache keys, source priority,
old entries, numerical bytes, original producer and stopping notes are unchanged.
A changed consumer still requires requalification. No student CIF gate is added.

PDU and 5PC retain active triple/180-degree targets and pass both target screens.
Each complete-H native manager has six linear-axis torsions; seed bending also
remains a descriptive finding. DP has no declared triple and is UNASSESSED by
that screen. These findings do not replace numerical targets or assert scientific
geometry approval. PDU's original nonconvergence remains a continuation note.

Validation: **18 new regressions, 201 focused / 4097 full tests pass** (two
skips, 276 subtests; 374.02 s). The original fresh-caller regression now enforces
the real mutually exclusive auditor contract and fails against published C69.
Fourteen actual-return mutations are rejected. The cold runner, after build-source
deletion and relocation with poisoned imports/aliased TMPDIR and every subprocess
forbidden, publishes three qualified entries and passes three immediate reuses.
All 3,849 parent payloads/manifest survive in 4,008 output payloads. Six independent
qualified/reused copies resolve after deleting the original cache/layout/evidence;
producer/stopping notes survive. The actual returned Mac C70 capsule now
independently reproduces these successes, including 72 result artifacts and
six relocated readbacks. Both ledgers record the verified return under
`source_reuse_saved_completion_2026_10_23`. This is saved qualification/store
completion, not a fresh live-installation or full-run verdict. The current
change records evidence only; the previously passing runtime/tests are unchanged.

Ordinary cache acquisition and isolated current native inputs are verified in
C71; current site/model qualification,
production checkpoints/refinement, the exact eight-pair full live run and solution
PDF remain separate. Energy-library resource files are not fingerprinted; ATL
stays independent. The C68 prelaunch failure and C69 reporting failure remain
immutable inside the lineage.

**C67 source/compiler gate is closed.** All 3,713 returned payloads and
the complete C66 parent verify. Ordinary selection passes 15 sources (six
curated, nine installed CCD), eight exact intended pairs and 16 stacking
orientations. All 39 source/PHIL files independently reproduce. DP/PDU/5PC
inventoried chemistry matches saved projections, while raw bytes/authority
differ; their strict cache misses are expected. C68 addresses that source
relationship through qualified rebinding rather than a relaxed lookup.
All 157 original runtime members and the reported runner match; original
entries and native evidence remain immutable. See
ordinary_source_acquisition_2026_10_22 for exact returned evidence.

The user-facing policy now removes mandatory CIF inspection/approval. Optimize
and repair within bounded budgets, retain the best usable candidate or native
fallback, continue with notes for nonconvergence/residual geometry, and disclose
choices in the eventual solution PDF. Keep chemistry, NARestraints authority
and fixed target mechanics intact. DNA pucker is nonfatal; demonstrated stereo
inversion excludes that candidate rather than being silently allowed.

Implemented: pure `cif-automatic-usable-fallback-v1` selection from verified
adapter evidence and additive PostMR `solution_report` summaries. C55 adds an
opt-in isolated native qualification-to-decision adapter; corrected saved replay
passes the returned native cases. C66 now verifies the shared persistent
component store/resolver on the Mac: all 30 reuse controls and nine frozen
snapshots independently reproduce without native processes.
Ordinary cache acquisition is implemented. Automatic repair on misses, production
bundle qualification and the PDF renderer remain separate. Detailed diagnostic REVIEW results are developer evidence,
not student CIF approval gates. See the [contract](cif-doctor.md#automatic-continuation-and-student-facing-decisions).

Returned C54 verifies all **2,677 payloads**, including the unchanged 2,615-payload
C53 parent. All three native full builders complete and retain written outputs;
explicit formal charges and all **nine finished four-neighbor source-relative
configurations are preserved**. PDU reports nonconvergence. DP/5PC logs do not
provide qualified convergence verdicts. DP retains four plane/angle findings.
Its legacy rejection is solely the omitted source phosphate `both` volume row;
the three fixed sugar-hand definitions match. A `both` term permits either hand
but remains a mechanical volume restraint, so its omission is not equivalence.
The reported runner differs from clean C54 only in NARestraints dirty-state
metadata; reconstructing that field reproduces its SHA with equal runtime bytes.

Returned C55 verifies **2,760 payloads** and all preserved C54 evidence. Six
Phenix 2.2.1-6174 interpretations complete, with twelve finite, exactly repeated
native energy/gradient evaluations. The v1 auditor fails because it demands
bitwise equality across Cartesian roundtrips (maximum difference 3.55e-15 A),
rejects native zero-weight constant rows and divides by their declared zero ESD.
Its six REVIEW results and three unselected decisions remain historical evidence.

**Corrected v2 replay passes all six native cases and three isolated decisions
are CONTINUE_WITH_NOTES.** Compare native/hierarchy Cartesian arrays within
1e-12 A while preserving exact identities, frozen inputs and definitions.
Match every declared period-zero/zero-ESD row to the native constant container,
including zero weight and signed target; active zero-weight restraints remain
invalid. Canonicalize independent outer/central torsion swaps with their target
and alternate-angle sign changes. Do not edit CIFs, native proxies or kernels.
DP retains complete four-bond/six-angle coverage around the omitted `both` term.
All other geometry, charge-access, stopping, classification and CIP notes remain.

**Returned C56 verifies 2,774 payloads**, six saved usability passes and three
CONTINUE_WITH_NOTES decisions with zero new native calls. The runtime matches
the clean pinned C56 build; only NARestraints dirty-state metadata explains the
reported runner SHA. All C55 payloads, failures and current source bytes remain
preserved. See `saved_native_usability_correction_2026_10_22` for exact hashes.

**Returned C57 verifies 2,854 payloads** and the complete C56 parent. Six
Phenix 2.2.1-6174 workers pass every source-DNA metadata/effective-proxy/full
target/named-gradient comparison at both saved coordinate sets. Twelve finite
evaluations repeat exactly; all three isolated decisions select source_declared_dna
with notes. Maintained code replays all preparations, workers/specs/inputs/outputs
and decisions. Only NARestraints dirty-state metadata explains the reported
runner SHA; runtime bytes match the clean pinned build. No optimizer runs.

**Returned C58 verifies 2,940 payloads** and the complete C57 parent. One
canonical and three DP/PDU/5PC Phenix 2.2.1-6174 workers complete. All three
modified cases are LINKED_CONTROL_MECHANICS_PASS: the two canonical backbone
links and targets/weights, projected definitions/heavy restraints, phosphate
four-bond/six-angle coverage and flanking mechanics survive. Eight finite
energy/gradient evaluations repeat exactly. Each modified case records only
the already unsupported formal-charge readback, without contradiction or
partial-charge substitution. The runtime matches the clean pinned build;
only NARestraints dirty-state metadata differs. No optimizer or adoption runs.

**Returned C59 verifies 3,097 payloads** and the complete 2,940-payload C58
parent. Both Phenix 2.2.1-6174 interpretations complete: original baseline in
3.357285 s and replacement DP B:4 candidate in 1.474756 s. The twelve baseline
checks pass; the candidate has 67 PASS and one expected unsupported
formal-charge check, without contradictions or REVIEW findings. The separate
automatic decision is CONTINUE_WITH_NOTES, selecting qualified_candidate.
All 877 atoms, 43 sites, 38 backbone links and every explicit NARestraints
pairing/stacking term survive. Global plane/parallelity inventories are exact.
The runtime matches the clean pinned build; only NARestraints dirty-state
metadata explains the reported runner SHA. No optimizer or production adoption
runs in C59.

DP C6-N5-C7 now uses the independently generated 128.1-degree target rather than
109.471 degrees. At the same coordinates, descriptive bond deviations at least
five sigma change 3 to 4 and angle deviations 10 to 9, with zero chirality sign
conflicts in both managers. These are different fixed objectives, not an
optimization improvement or a convergence result.

**Returned C60 verifies 3,300 payloads** and all 3,097 unchanged C59 payloads.
The fresh replacement-manager initial derivative audit passes (1,367/2,000
native evaluations), as do both full-precision/PDB-rounded endpoint derivative
cases (2,734/4,000 evaluations). All 17 exact native readback checks and all eight
coordinate-selection checks pass. The fixed constraint signature, 877 atoms,
43 sites, 38 backbone links and explicit NARestraints policy survive. Both
geometries have zero sign conflicts across 158 recorded chirality proxies.
Maintained validators reproduce the qualifications and automatic choice without
executing captured code.

The same-objective full-precision target falls **2671.029230 → 2508.431084
(6.09%)** and gradient norm **1507.689322 → 50.997383 (96.62%)**. The written
PDB has a separate target **2511.569430** and gradient norm **878.690317**; do not
substitute these for the full-precision endpoint. Native stopping remains
**NOT_CONVERGED_LIMIT**, 1,000 iterations/1,033 calls, with the native criterion
false. Three bond and nine angle nominal deviations at least five sigma remain
in both coordinate representations. The automatic decision selects
qualified_geometry_endpoint with CONTINUE_WITH_NOTES. No further geometry
continuation is required to progress.

**Returned C61 verifies 3,406 payloads** and all 3,300 unchanged C60 payloads.
The fresh staged-layout Phenix worker completes in 5.281162 s; all 15 native
readback checks pass and two finite energy/gradient evaluations repeat. The
target 2511.569429708212 matches the previously qualified serialized objective.
The selected model SHA e35c0636c654fd007285a94eb4e880ff6a66dfdfa269c861eb4b3214b461d16b,
19 CIFs and 14 PHILs retain their exact bytes. All 877 atoms, 43 sites,
38 links, effective definitions/proxies and explicit NARestraints policy survive.
The ordinary resolver and 33-input assessor replay independently of capsule
paths; the assessment remains REVIEW with the same selection/stopping notes
and PDF PLANNED. No generation, optimizer, diffraction/refinement or production
checkpoint runs.

C61 local validation is complete: **106 new regressions**, **215 focused /
3394 full tests** pass (two skips, 276 subtests; full run 331.01 s).
Actual-C60 replay reproduces the proofs, serialization, native checks and choice.
Deleted-build/relocated transport preserves source payloads, the everyday edit
and ignored runners. Standalone ordinary CLI consumption after source removal,
poisoned imports, aliased temporary roots, 156 links, six evidence mirrors and
protected hash/figure checks pass. The returned native gate is now closed;
this is not an ordinary production checkpoint or a scientific-geometry verdict.

**Returned C62 verifies 3,445 payloads** and all 3,406 unchanged C61 payloads.
One Coot 1.3.3 process from saved configuration completes all three graph
constructions under the 600-second bound. The maintained audit reproduces
CONSTRUCTION_CONTROLS_PASS_WITH_NOTES. DP A:6, PDU A:9 and 5PC A:7 each retain
their whole raw site because OP3 is the sole unmatched scaffold atom. The
857-atom/42-site raw and final models are byte-identical: **successful rigid
base transport was not exercised**. The 788 atoms at 39 unselected sites retain
identities, elements and XYZ from the initial model, not full record bytes.
All numerical dictionary bytes remain exact C57 candidates. Source/runtime
bytes match clean C62; only NARestraints dirty-state metadata explains the
reported runner SHA. No new native execution occurs during return verification.

C62 local validation passed **118 new regressions**, **257 focused / 3512 full
tests** (two skips, 276 subtests; full run 336.16 s). Actual-C61 strict replay,
deleted-build/relocated runner, poisoned imports, aliased temporary roots,
seven mirrors, 156 links and protected hashes/figure checks passed. These local
checks and the returned Coot construction are separate evidence. Scientific
geometry, native restraints and refinement were not assessed in C62. Historical
receipts, including the old unobserved-composition label, stay unchanged.

Returned C63 verifies all **3,489 payloads**, preserves the complete C62 parent,
and completes Coot 1.3.3 through the ordinary construction API. All three
DP/PDU/5PC sites use proper whole-base restoration, with three proved internal
OP3 deletions, 69 selected serial normalizations and no raw fallback. The final
unchanged phosphate recheck removes nothing. Base geometry changes by at most
0.001041 A, consistent with PDB rounding; this is construction evidence, not a
native-restraint or scientific-geometry verdict.

Maintained cif-saved-postmr-construction-replay-v1 reproduces every context,
shadow, sanitizer, serial/deletion delta, proper transform and independent audit
without executing captured code or native software. The final model SHA is
520330ae8531c6a7790f120fbee33832dc176fe12809cd98c055ee39bf375695: 854 atoms,
42 sites; all 788 atoms at 39 unselected sites retain identities/elements/XYZ.
The 69 normalized selected serials leave 66 retained serial changes after three
OP3 deletions. Fresh Coot raw bytes exactly match C62, but final coordinates now
exercise successful graph transport. All source/numerical dictionaries retain
exact bytes. Source/runtime match clean ae665f1; only NARestraints dirty-state
metadata explains the reported runner SHA. Historical C62 outcomes stay intact.

**C64 was delivered and returned.** Runner `64_Cedar_probe_postmr_native.py` uses
`--postmr-construction-native-only` on exact C63. Stage the exact canonical and
constructed models, three qualified source candidates and existing site-modifier
preparations. Interpret one canonical reference and one constructed layout with
Phenix 2.2.1-6174, 60 seconds and two fixed evaluations per worker. Require all
canonical backbone links/targets/weights, complete sites, selected effective
chemical definitions, exact heavy-atom restraints, four-bond/six-angle phosphate
coverage and active triple length/linearity targets. Native secondary structure
stays disabled; native kernels, the plane correction and optimizer are unchanged.
The two models have different objectives and their targets are not ranked.
No Coot rerun, ReadySet, generation, optimizer, observations, fake checkpoint,
refinement or NAR release is requested. ATL stays independent; no ninth pair.

This native readback connects ordinary construction with source-qualified
restraints. Generic NAR compilation, ordinary automatic acquisition/repair and
bundle adoption remain necessary before the exact eight-pair live run; PDF
rendering and scientific geometry/CIP/state qualification stay separate.
Students do not inspect CIF tables. See ordinary_postmr_context_2026_10_22 and
ordinary_constructed_native_readback_2026_10_22 in the mirrored evidence records.
C64 local validation passes **93 new regressions**, **362 focused / 3745 full
tests** (two skips, 276 subtests; full run 344.88 s). Strict actual-C63 replay,
deleted-build/relocated delivery, poisoned ambient imports, aliased TMPDIR and
standalone preparation after source-capsule removal pass. All 3,489 payloads,
the everyday local edit and legacy backup bytes/names survive. Nine evidence
mirrors, 156 relative links, protected mechanics and deterministic figure/raster
checks pass. The C64 local checks did not execute Phenix; the separate returned Mac evidence
is recorded below. C63's historical local suite remains 3652 passed/two skipped.

Returned C64 verifies all **3,552 payloads** and preserves the complete C63
parent. Both Phenix 2.2.1-6174 workers complete with four finite repeatable fixed
evaluations. Active PDU/5PC triple length and linear-angle targets pass at A:9
and A:7. The original qualifier records 87 PASS, six REVIEW and three unsupported
formal-charge checks. All six REVIEW findings compare display labels containing
different residue-name padding (`DG ` versus ` DG`), not changed parameters.

C65 uses the shared cif-native-named-proxy-comparison-v1 comparator: bind each
label to its own manager index, replace it with the complete structured atom
identity, normalize field padding only, and retain endpoint order, every
parameter, symmetry, origin and multiplicity exactly. Reject missing/ambiguous
identities and unbound labels. All **3,148 unaffected restraints** match exactly
by named identity; numerical tolerances, native kernels and source chemistry
are unchanged. Historical C64 receipts remain immutable.

**C65 was delivered, returned and independently verified.**
Returned C65 verifies all **3,587 payloads**, preserves the entire C64
parent and manifest, and reproduces the maintained qualification: **93 PASS,
zero REVIEW, three unsupported formal-charge readbacks**. All eight unaffected
proxy families compare exactly, covering 3,148 restraints. Both active triple
screens pass; three linear-axis torsions per site remain recorded. Independent
replay reproduces the report and prepared scientific bytes with subprocesses
forbidden. No repeat of this construction-native gate is needed.

The returned runner exactly matches published `a846f68` after changing only
the recorded NARestraints dirty-state flag; all 153 runtime members match.
The original six C64 reviews remain immutable. Overall diagnostic REVIEW
continues to describe the full-run/scientific boundary, without student CIF
inspection. No new native process, geometry cycle, release or adoption ran.

**Next integration boundary:** ordinary automatic resource acquisition/repair
using the verified shared reuse API, and authoritative pairing/stacking
compilation remain necessary before the requested eight-pair live run. A local ordinary overlay
preflight shows that the construction-only control places DP at A:6 opposite
canonical C at C:10; NARestraints has no configured P:C recipe. That fixture
tests construction, not declared pairing intent. Use the already requested
DZ:DP (Z:P) combination for the paired integration control; do not invent a
recipe or treat this as another CIF defect. No new native delivery is prepared
by this return-record update. The exact eight-pair plan and independent ATL
scope remain unchanged.

**Required reuse policy:** automatic acquisition/repair integration must persist
usable numerical repairs locally and consult them before regenerating or
optimizing a component for another structure. Reuse keys bind exact source and
declared chemical state, with tool/policy/qualification provenance; code alone
cannot select a repair. Recheck site modifiers/native compatibility separately,
retain nonconvergence notes, and freeze selected bytes in every run. New model
coordinates must not invalidate base-component numerics. See the
[local reuse contract](cif-doctor.md#persistent-local-reuse-of-qualified-repairs).
This requirement is recorded; the store is not implemented by C65.


**C66 was delivered, returned and independently verified.**
Returned C66 verifies all **3,659 payloads** and the byte-identical C65
parent and manifest. DP, PDU and 5PC each pass ten reuse controls: their
first qualified dictionaries are saved and repeated requests reuse the exact
bytes without acquisition. Source/authority mismatches are excluded and a
changed consumer requires requalification before generation. Independent
replay reproduces all 30 controls and nine frozen snapshots, including original
stopping/limitation notes, with every subprocess forbidden. Ordinary PostMR
orchestration and the requested eight-pair live run remain separate work.

The Mac runner matches published `5f90e70` exactly after changing only the
recorded NARestraints dirty-state flag; all 155 runtime members match. The
default application-data store contains immutable source/state/authority-bound
entries, and each run keeps independent source/numerical/evidence copies.
PDU remains explicitly nonconverged; DP/5PC retain unreported stopping notes.
Consumer fingerprints are saved evidence; installed runtime and energy-library
resource files are not newly certified by this diagnostic.
No new builder, optimizer or native process ran, and no student CIF approval
is required. The persistent path is historical provenance; all nine returned
snapshots resolve without reading an external source, dictionary or ZIP.

**Next integration boundary:** connect ordinary acquisition/adoption to this
verified resolver, retain usable fallback and qualify current site/model
context, then compile authoritative intended pairing/stacking for the exact
eight-pair live run. The construction-only DP:C fixture remains outside
supported pairing intent; use declared DZ:DP rather than inventing a recipe.
The C66 transport/reuse gate is closed and needs no repeat. This return-record
update prepares no new native delivery, NAR release or ATL merge gate.

C66 implementation validation remains **76 new regressions**, **389 focused /
3959 full tests** (two skips, 276 subtests; full run 355.38 s). The deleted-build/
relocated actual-C65 delivery passes all 30 controls with subprocesses
forbidden; all 3,587 input payloads and the manifest survive. Poisoned imports,
aliased TMPDIR, the everyday edit and ignored runner pass. Nine local QA
snapshots survive owned-cache removal and relocation with external scientific
reads forbidden. The real Mac return independently reproduces the same
controls and exact frozen payload bytes. Protected mechanics/workbook and
the eight-pair plan are unchanged. See qualified_dictionary_reuse_2026_10_22
in both machine ledgers for hashes and the original full-suite evidence.


C65 validation passes **138 new regressions**, **347 focused / 3883 full
tests** (two skips, 276 subtests; full run 353.98 s). Actual-C64 maintained
replay and deleted-build/relocated delivery reproduce all 96 checks: 93 PASS,
three unsupported formal-charge checks, zero REVIEW. All 3,552 input payloads
and the original manifest survive, including the six original REVIEW findings.
Poisoned imports, aliased TMPDIR, forbidden native subprocesses, the everyday
edit, ignored runner and standalone preparation hashes pass. Ten evidence
mirrors, 161 links and protected mechanics/workbook/eight-pair plan pass.
Visible SVG geometry is exactly the C64 baseline; metadata and caption describe
the new comparison. Full-run and scientific qualification remain open.

## Completed and open work

| Workstream | Verified result | Still open |
| --- | --- | --- |
| NARestraints | **v1.1.3 released and installed** (`a9264f9`); corrected Z:P/K:X roles, unchanged workbook. Docs-only PR #5 merged to main at `ef1a5a1`. | Combined-model geometry qualification belongs to the NASolve native trial. |
| W Saenger overlay / viewing | PR #24 merged at `0017081`; prior Z:P `run_003/refine-001` numerically SOLVED and overall user Coot visual PASS. PR #25 merged at `e8613bf`; bare `show` user-live PASS. | New-campaign automatic workspace activation has regression coverage, not a separate returned live verdict. |
| Cedar source lookup | Installed Phenix CCD lookup for IGU/IMC/CGY/DX and Coot construction verified; symlink duplicates resolved. Nine bundled-source roles audited. | Acquisition, parameter generation and linkage must become a repeatable ordinary workflow; source availability alone does not certify geometry. |
| Combined 42-residue W trial | **Preflight, Phaser and PostMR passed**; 42/42 identities, 12 retained + 5 replaced Saenger blocks, 8 explicit pairs, stacking enabled. | Effective geometry qualification, explicit phosphate-state review, refinement and human review. |
| Generic linkage diagnostic | **GENERIC_LINKAGE_MECHANICS_PASS** with fresh IMC, no missing heavy atoms, preserved links and D:1 terminal phosphate. | Diagnostic-only derivatives, not integrated general PostMR support or chemistry approval. |
| Custom restraint coverage | **21/21 bonds, 34/34 angles, 8/8 planes, 23/23 parallelities** matched; no exact duplicate planes/parallelities or overlap candidates. | Custom proxies remained preserved after native 5CM/DF adoption; coverage is not achieved geometry. |
| Effective 5CM / DF recovery | **REPAIRED_NATIVE_INTERPRETATION_PASS**: corrected 5CM and linked DF adopted in a separate native diagnostic; 42 mappings, DF bonds/chirality, preserved custom/other proxies and unchanged 868-atom model verified. | Separate minimization and user visual review completed; full numerical qualification remains pending. |
| Combined geometry trials | First trial received user Coot visual PASS. The DP-specific trial relieves the N5 conflict (worst 6.15→0.483 sigma); all 158 chirality signs and 38 backbone links survive. User also reports base visual PASS for the exact new model. | Sugars were not assessed by eye; numerical sugar/termination review and full qualification remain open. Convergence is not claimed. |
| Ordinary/full-auto campaigns | Prior EA/DiU/Q5cm/QiC cohort reached numerical SOLVED with review/provisional distinctions preserved. | This does not prove a fresh arbitrary-component run without a prepared resource bundle. |
| CIF Doctor first slice | Offline dictionary and frozen-checkpoint assessment; report-only pre-mutation/pre-ReadySet/effective PostMR receipts; explicit torsion-alternate and hash-scoped historical 5CM preparation. | Native consumer/proxy verification, mapped descriptors, generation/adoption and geometry/stitching remain separate slices. |
| P2 / prepared nonstandard P5 | P2 preparation and nonstandard campaign paths implemented and fixture-tested. | Source-native `1W5→DZ` / `1WA→DP` provenance/refinement; 3–5 real geometry-diverse P5 models. |
| Scout / Topo / GUI | Existing registration/shadow primitives and scoped evidence retained. | Operational Scout and topology surgery remain future work. |

**Latest returned Cedar regression:** `1443979b2308e4a2e507f0859370b44e0e124a86`,
**16 focused + 31 subtests (2.45 s)** and **983 full + 257 subtests
(80.81 s)**, using `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"`
and `../NASolve/.venv/bin/python -m pytest -q` (focused file:
`tests/test_cedar_ccd_resolver.py`). This receipt does not certify the current
local head or the later diagnostic derivatives. NARestraints installed workbook
SHA-256 remains
`94a66af42081188fd95f3fdcbe04cb01bed8f1826772597272320a8b4c0433b2`.

The October 10 documentation snapshot also passed the isolated Linux suite:
**981 passed, 2 skipped, 257 subtests (29.21 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
This is separate from the laptop receipt and is not native Phenix validation.

## Immediate next work

**Default command passage:** follow the
[Git delivery and terminal handoff contract](collaboration.md#git-delivery-and-terminal-handoffs).
Give one pasteable subshell containing the reviewed fetch, full-SHA detached
worktree, build and run commands joined by `&&`, with explicit quoted paths.
Keep necessary install commands as separate one-liners. This operating
convention belongs in the repo; private personality handoffs remain private.

**Cedar 21 returned and verified (2026-10-18): native membership PASS.** All
**491 payloads** verify, including the 367 unchanged Cedar 20 payloads and their
byte-identical manifest. Runner `6f7813d5…` matches clean NASolve `edafbf52…` /
NARestraints `a7b6a0c9…`; all 106 embedded runtime members verify. Independent
replay reproduces the compiler report and every derived PHIL byte for byte.

Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes both interpretation-only
cases: **6.298652 s** at the initial coordinates and **1.450339 s** at the saved
endpoints, exit zero. Each passes **14/14 exact mechanics checks**. The 877 atom
identities/43 sites, all component definitions, 19 dictionary files, modifiers
and 38 backbone links survive. All captured static proxy rows and the effective
native PHIL are identical across the two coordinate sets. Eight installed API
fingerprints agree, including the origin registry and secondary-structure source.
Native SS construction is disabled and no competing SS-origin proxies remain.

NARestraints compiles the 12 generic pair/23 generic stack declarations into
31 bonds, 52 angles and 35 parallelities. The retained 21 bonds, 34 angles,
eight planes and 23 parallelities survive exactly. Both managers therefore
contain **52 explicit bonds / 86 angles / eight planes / 58 parallelities**,
accounting separately for 20 paired relationships and 38 physical stacks.
This closes the **declared membership/consumer mechanics** gate for this
bounded first slice, not chemistry, achieved geometry or production integration.
The original Cedar 20 11 PASS/three REVIEW receipt remains unchanged.

Descriptive measurements under the same new policy are:

| Saved coordinates | Bond nominal deviations >=5 | Angle nominal deviations >=5 | Recorded chirality sign conflicts |
| --- | ---: | ---: | ---: |
| Initial | 30 | 68 | 0/158 |
| Cedar 19/20 endpoint | 4 | 10 | 0/158 |

Cedar 21 changes no coordinates and runs no optimization; these are two existing
models, not an improvement produced by this probe or evidence of convergence.
Local descriptive replay differs only by floating roundoff (maximum 7.11e-14);
all discrete counts and exact native comparisons agree. The historical
**NOT_CONVERGED_LIMIT** remains recorded. Energies from the old native SS
objective cannot be transferred to this NARestraints-owned objective.

**Cedar 22 returned and verified (2026-10-18): native mechanics PASS;
optimization remains unconverged.** All **609 payloads** verify, including all
491 unchanged Cedar 21 payloads and their manifest. Runner `e600a2b9…` matches
clean NASolve `2408c9ee…` / NARestraints `a7b6a0c9…`; all 106 runtime members
verify. Exact initial manager matching includes SS controls, the origin registry
and eight API fingerprints. The same 19 CIF/13 PHIL inputs remain fixed, without
new guessing or policy compilation. Phenix 2.2.1-6174 completes the trial in
**4.4478 s** and native PDB readback in **1.737436 s**, both exit zero. All
**17/17 exact readback checks** pass: 877 atoms/43 sites, 38 backbone links,
definitions, requests, static proxies, native policy and APIs survive. Separate
candidate serialization replays byte for byte.

The full-precision objective falls **3784.7499 → 2866.5556 (24.26%)** and
gradient norm **1033.6782 → 91.2772 (91.17%)**. At **905 iterations / 970 calls**
the line search reports rounding errors preventing progress; the native
criterion is false. Preserve **NOT_CONVERGED_ERROR**. This happens before PDB
serialization. The rounded vector has a separate target **2870.0305** and
gradient norm **907.0440**; retain full precision for future numerical review.

Nominal deviations >=5 change from **four to three distance terms**, **ten to
ten angles**, with no sign conflicts among 158 recorded chirality proxies. All
three remaining distance outliers are CGY A:20–DX D:3 hydrogen bonds, still
**4.34–5.58 Å** versus 2.8 Å targets; the longest worsens slightly. Nine angle
outliers involve that pair. DP B:4 also retains its C6–N5–C7 discrepancy,
**127.87° versus 109.471°**. These findings do not authorize target changes.

**Cedar 23 returned and verified (2026-10-19): sampled numerical REVIEW.**
`scripts/build_cif_gradient_audit_probe.py` builds
`23_Cedar_probe_cif_gradient_audit.py` from the verified Cedar 22 capsule.
It repeats dictionary assessment, records all 20 explicit intersite distance
groups and selects six probe atoms from the largest captured bond/angle
deviations. The K:X pair's existing GC-like intent is preserved. CIF Doctor
already detects the retained DP N5 planar-angle conflict; no new target is
inferred from the residuals.

The native phase exactly matches the initial manager, eight native APIs and
six numerical-source hashes, then evaluates full-precision and PDB-rounded
endpoints under the full objective and seven isolated category controls.
Four central-difference steps, per-family gradients, repeat/additivity checks,
descent profiles and neighbour counts are retained. The cap is 4,000 energy
evaluations / 1,200 seconds; no minimizer runs or new coordinate model is
written. These numerical controls do not change the NARestraints policy or
relax any exact native gate. Sampled agreement cannot establish full gradient
correctness, convergence or chemistry. Source/charge, pucker, absolute stereochemistry,
complete geometry, refinement and adoption remain open. Ordinary PostMR and
historical gates are unchanged; private capsules/models/logs are not committed.
Cedar 23 passes **70 focused checks (7.14 s)** and **1,691 full tests, two
skips and 276 subtests (83.63 s)**, with actual-input offline inspection and
synthetic deleted-build transport. Its returned **670 payloads** and all 609
prior payloads plus their manifest verify byte for byte. Native execution
completes in **7.8046 s**, exit zero, with **2,734/4,000** energy evaluations.
Initial manager, eight API sources, six numerical sources and the static
constraint signature match. All 17 prerequisite mechanics checks replay.

Both coordinate cases fail **18/21 sampled directions** for parallelity and
the full objective; bond, angle, dihedral, chirality, planarity and nonbonded
controls each pass **21/21**. Repeats, captured snapshots and target/gradient
additivity agree. At CGY A:20 N4 x, the native parallelity derivative is
**−2.9313** while the four central differences stabilize near **+7.4647**.
The disagreement survives PDB rounding and step reduction.

An independent centered-scatter eigensolver reproduces both parallelity
energies within 6e-12 and selected finite differences within 1.2e-6. Modeling
the second-plane accumulation-loop bounds in the public CCTBX header reproduces
all **2,631 saved gradient components per case** to about 1.5e-12 in norm.
The public loop omits/truncates second-plane contributions. This strongly
indicates a native accumulation defect; the installed C++ header was not
captured, and the audit does not prove it caused the earlier line-search stall.

**Cedar 24 returned and verified (2026-10-19): installed accumulation defect reproduced.**
`scripts/build_cif_parallelity_audit_probe.py` builds
`24_Cedar_probe_cif_parallelity_audit.py` from the exact verified Cedar 23 ZIP.
The new diagnostic replays all 17 mechanics checks and matches the initial
manager, eight API sources, six numerical sources and static constraints.
It compares complete individual-restraint gradients, identity-scattered sums,
singleton/full native containers and the unchanged manager. Every one of the
58 plane restraints is checked at both saved coordinate sets and both plane
orders. Three tilted controls exercise 4/4, 4/6 and 6/4 atoms, also both orders.

Each order retains three directions, four central-difference steps and complete
repeated arrays. The expected budget is 6,188 single/container evaluation pairs
under a 7,000-pair cap, plus two full-batch comparisons, with a 1,200 s timeout.
Native C++ header/binding sources are copied only if present beside the imported
geometry module; missing source is recorded and does not imply binary origin.
No optimizer, native patch, new crystal model, target edits or adoption occurs.
NARestraints selections/planes/weights and exact native gates remain fixed.

The 31 new regressions are covered by **101 focused tests (10.92 s)**; the
full suite passes **1,722 tests, two skips and 276 subtests (84.32 s)**.
The real 670-payload input passes the new source-bundled offline inspection,
including the exact 17-check prerequisite replay; deleted-build/poisoned-import
transport and explicit synthetic native-worker guards pass. Full-suite results
are recorded in the native evidence ledger. Those software checks remain
distinct from the returned installed result below.

All **732 returned payloads** verify, including 670 unchanged Cedar 23 payloads
and their manifest. The runner matches clean NASolve `5eb9d752…` /
NARestraints `a7b6a0c9…`; all 108 runtime members verify. Installed Phenix
**2.2.1-6174** (dispatcher `2.2.1`) completes in **3.483823 s**, exit zero,
with **6,188 evaluation pairs**. The exact initial manager, eight native APIs,
six numerical sources and static constraints match; all 17 prerequisites replay.

All **714 sampled individual-restraint directions pass**. Accumulation fails
at least one direction in **all 238 tested orders**: 116 at each saved
precision and six tilted controls. In every order, the first-plane direction
passes while the second-plane and alternating directions fail. Individual
gradients are invariant under plane-order swaps; accumulated gradients are not.
For the equal-size 4/4 control, the second-plane gradient norm is **2.21375**
individually and **exactly zero** after accumulation. Energies and repeats agree.

Both installed C++ source files match the recorded public blobs. The loop
starts the second-plane index at `i_size` but stops at `j_size`, retaining only
`max(0, j_size - i_size)` second-plane contributions. That model reproduces all
returned per-order accumulation arrays **exactly**. The full manager matches
the same incomplete batch gradient; it is not an isolated test-wrapper effect.
This confirms the defect in the tested installed path, without claiming every
version/overload or proving why the previous optimizer stalled.

Algebraically replacing only Cedar 23's parallelity gradient with complete
individual-restraint sums yields **84/84 passing sampled directional checks**,
explaining all 72 previous failures at the same energies and coordinates. This
is a saved-data replay, not a newly corrected manager or optimization. The
recombined full-precision full-gradient norm is 222.798, not the old incomplete
91.277; this is a different derivative calculation at the same endpoint.

**Cedar 25 returned and verified (2026-10-19): endpoints pass, initial sign review.**
`scripts/build_cif_corrected_gradient_probe.py` builds
`25_Cedar_probe_cif_corrected_gradient.py` from the verified 732-payload Cedar 24
return. `src/nasolve/cif_parallelity_correction.py` implements an explicit
NASolve-local evaluator: subtract only the native accumulated plane gradient
and add the complete original per-restraint i/j gradients by atom index.
The native energy and energy object, targets, weights, proxies, NARestraints
policy and installed Phenix files stay fixed. Already-correct native
accumulation is a no-op; symmetry-bearing planes and special positions fail
visibly. Production PostMR/refinement defaults are unchanged.

The new probe replays all 17 mechanics checks, pins the same eight native APIs,
six numerical modules, two adapters and two installed C++ sources, and matches
all three raw native snapshots before correction. It freshly evaluates four
central-difference steps at the initial coordinates, saved full precision and
PDB-rounded endpoint under the full objective and seven category controls.
Corrected gradient norms are recorded separately from the old incomplete
baselines. The 5,500-evaluation budget excludes five recorded preflight calls;
no minimizer runs. Sampled agreement is a derivative check, not scientific
approval. A deliberately bad single-restraint derivative remains visible in
regression tests.

The returned **794-payload** capsule verifies all 732 prior payloads and their
manifest, exact native input/output/worker sources and all 17 mechanics checks.
Installed Phenix 2.2.1-6174 / dispatcher 2.2.1 completes **4,101 evaluations
plus five preflight calls in 30.804996 s**, native exit zero. Native energy
change is **0.0**. Both endpoints pass **168/168** sampled directions; initial
coordinates pass **162/168**, retaining three failures each for full and
parallelity. Repeats/additivity pass throughout. The overall correction remains
**DERIVATIVE_REVIEW**; Cedar 22 remains **NOT_CONVERGED_ERROR**.

An independent centered-scatter spectral derivative and the installed header's
normal-sign branch reproduce the initial stored plane gradient within **3e-12**
in norm. Four ordinary stacks enter that branch: the header negates the second
normal but differentiates through its original row vectors without the matching
chain-rule sign. Both saved endpoints avoid the branch. Recombining spectral
plane derivatives makes **504/504 saved directions** agree at identical energy
samples and tolerances. This is source/model inference, not fresh native proof
of the second defect or the cause of the optimizer stall. The affected indices
in the evidence ledger are observations, never correction selectors.

**Cedar 26 returned and verified (2026-10-19): sampled native derivatives PASS.**
`scripts/build_cif_plane_order_probe.py` builds `26_Cedar_probe_cif_plane_order.py`
from the exact verified Cedar 25 ZIP. The evaluator adds an explicit
`plane_order_safe=True` policy: use i's first-plane block, copy the native proxy
with i/j reversed and use its first-plane block for j. Verify all copied
parameters, origin IDs and residuals; scatter shared atoms completely. The
manager's proxies, native full energy and other gradient terms stay fixed.
The existing accumulation-only policy remains the default. Symmetry-bearing
planes and special positions stay unsupported. No Phenix file is edited.

The worker pins the same native sources and static constraints, matches all
three raw snapshots and all three old complete/container plane arrays, then
runs fresh full-objective/category finite differences at all three cases.
A separate per-proxy audit checks all **58** planes in both orders, three local
directions and four steps. Six tilted controls cover 4/4, 4/6 and 6/4 atoms,
unrotated and after a 30-degree rigid rotation about x; energy and gradient
rotation invariance are checked. The rotation enters the normal-sign branch
without changing the physical plane angle. Original kernel failures remain
recorded alongside corrected derivatives.

Expected work is **4,101 global evaluations / 5,500**, **six preflight calls**
and **9,360 two-kernel plane-order pairs / 10,000**, with a 1,200 s timeout.
Local validation passes **30 new regressions**, **167 focused tests (18.98 s)**
and **1,788 full tests, two skips and 276 subtests (96.44 s)**. A deliberately
bad first-plane derivative remains visible; deleted-build/poisoned-import
transport and actual-input 794-payload offline replay pass. These software
checks are separate from the installed result below.

All **857 returned payloads** verify, including 794 unchanged Cedar 25 payloads
and their manifest. Runner `fd952513…` matches clean NASolve `628c2594…` /
NARestraints `a7b6a0c9…`; all 109 runtime members verify. Phenix
**2.2.1-6174** (dispatcher `2.2.1`) completes in **53.402075 s**, exit zero,
using the expected global/preflight/per-plane budgets. Independent saved-data
replay recomputes **504/504 passing global/category directions** and
**1,080/1,080 passing corrected per-plane directions**. All **360 plane
orders**, including 12 tilted/rotated controls, retain repeated arrays,
unchanged energies, order invariance and all three rotation controls.
The original native-complete kernel still fails 28 of 1,080 directions across
eight initial and six tilted/rotated orders; those failures remain recorded.
No optimizer or new crystal model was used in Cedar 26.

The corrected initial norm is **1,110.5207**, at the same **3,784.7499** target.
The corrected full-precision endpoint norm is **222.7981**, with rounded norm
**929.4534**. These differ from Cedar 22's incomplete native norms and cannot
be compared as a change in coordinates or convergence. Native energies change
by exactly zero. Eight API/six numerical/two adapter/two C++ fingerprints,
the full static signature and all 17 prior mechanics checks agree. This
qualifies the sampled correction for the captured supported installed profile;
it does not prove every gradient, native version, chemistry or convergence.

**Cedar 27 returned and verified (2026-10-19): mechanics/derivatives PASS; iteration limit.**
`scripts/build_cif_corrected_geometry_probe.py` builds
`27_Cedar_probe_cif_corrected_geometry.py` from the exact Cedar 26 ZIP.
The trial starts at the **same original initial coordinates as Cedar 22**,
using the unchanged native objective and the exact qualified both-first-plane
correction source. It does not continue from the prior unconverged endpoint.
Before any optimizer call, the host/native worker recompute the raw qualified
proof and require the exact native manager, source fingerprints, static
constraints, full corrected initial gradient vector and target. NARestraints
pairing recipes, plane mappings, stacking matrix and compiled selections stay
fixed; no relationships are guessed or compiled again.

The opt-in trial uses at most **1,000 iterations / 20,000 calls**, gradient
epsilon **1e-5** and a **1,200 s** native timeout. Preserve actual stopping
criteria/errors/limits. Fresh full-precision and PDB-rounded endpoint audits
use the same four steps, tolerances and frozen six probe atoms, with a separate
**4,000-evaluation** cap. Serialize a separate candidate by exact atom identity
and require all **17 native PDB mechanics checks** again. Stopping, derivative
qualification and native mechanics are independent; a lower target cannot
upgrade any failure or imply scientific approval.

Local validation passes **38 new regressions**, **205 focused tests (31.01 s)**
and **1,826 full tests, two skips and 276 subtests (107.25 s)**. The tests
exercise proof/source/manager drift before optimization, retained limit/error
stopping, and a deliberately bad endpoint gradient that remains REVIEW even
with a synthetic native criterion pass. Actual 857-payload offline inspection
and deleted-build/poisoned-import source transport pass. These worker checks
use explicit fakes; this Linux environment has no installed Phenix/Coot.

All **980 returned payloads** verify, including all 857 unchanged Cedar 26
payloads and their manifest. Runner `5cf0f2d2…` matches clean NASolve
`12d7fcc4…` / NARestraints `a7b6a0c9…`; all 110 runtime members verify.
Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes the corrected trial/audit in
**75.822869 s** and native PDB readback in **1.565038 s**, both exit zero.
All **17 exact mechanics checks** pass, preserving 877 atoms/43 sites, 38
backbone links, all definitions/proxies/compiled policy and native sources.
Candidate serialization reproduces byte for byte using exact atom identities.
Independent replay verifies all **336 passing endpoint directions** and
recomputes their **1,344 four-step samples**; 2,734 native audit evaluations
remain below the 4,000 cap. No captured source is executed in local replay.

The target changes **3784.7499458394077 -> 2697.762263611603 (28.72%)** and the
corrected norm **1110.520668509296 -> 372.53738052839816 (66.45%)**. The outcome
is **NOT_CONVERGED_LIMIT** at **1,000 iterations / 1,028 calls**: no recorded
optimizer error, native criterion false. All accepted targets decrease,
including **31.2321** from iteration 900 to 1000. Norms fluctuate, and the last
100 accepted steps span **109.81-456.05**; do not claim a nearby minimum or a
cause for slow convergence. The final target is 5.89% below Cedar 22's endpoint
under the same energy definition, without transferring its incomplete gradient
norms into this comparison. The rounded fixed-manager target/norm are
**2700.856094619088 / 905.6214940891548** and remain separate from full precision.

Both precisions retain **three nominal distance / ten angle deviations >=5**,
with **zero sign conflicts among 158 chirality proxies**. The three CGY A:20-DX
D:3 contact distances remain **4.4235 / 5.4261 / 5.6204 Å** versus 2.8 A targets;
nine angle outliers involve that pair. DP B:4 N5 remains **127.6378 degrees**
versus 109.471 degrees. Preserve these findings, pairing intent and recipe
targets; numerical descent does not resolve their scientific interpretation.

**Cedar 28 returned and verified: mechanics/derivatives PASS; iteration limit.**
`scripts/build_cif_geometry_continuation_probe.py` builds
`28_Cedar_probe_cif_geometry_continuation.py` from the verified 980-payload Cedar
27 ZIP. The reusable `continuation` opt-in recomputes the qualified endpoint
proof and preserves original source/policy/static identities. The native worker
first matches the original initial manager and corrected snapshot, then loads
Cedar 27's full-precision native atom-order coordinates and requires a fresh
match of the entire starting corrected gradient and target:
**2697.762263611603 / 372.53738052839816**. No rounded PDB is used as optimizer
state. The new L-BFGS history starts fresh; only coordinates are continued.

The stage permits **1,000 additional iterations / 20,000 calls**, epsilon
**1e-5** and a **1,200 s** timeout. It preserves prior stopping, actual new
stopping and cumulative optimizer iteration/call counts separately. Fresh
full/rounded endpoint derivative audits retain the **4,000-evaluation** cap;
all **17 native PDB mechanics checks** must pass again. Separate candidate:
`candidate/continued_geometry_model.pdb`. New-stage displacement from the prior
endpoint is recorded separately from original-model serialization displacement.

All **12 fail-before precondition regressions** now pass. The 36 new regressions
cover raw proof/policy/source defects, changed/rounded/reordered seeds refused
before the optimizer, all three native stopping outcomes, cumulative counts,
coherent captured-worker forgery, unsafe/duplicate/symlink capsules and deleted
builds with poisoned ambient/captured code. **241 focused tests pass (45.09 s)**.
The actual 980-payload source-bundled offline inspector and exact 17-check
mechanics replay pass. The full suite passes **1,862 tests, two skips and
276 subtests (122.57 s)**. Exact commands are recorded in the evidence ledger. These native-worker controls use explicit fakes; no installed
Phenix/Coot runs here.

All **1,104 returned payloads** verify, including the 980 unchanged Cedar 27
payloads and their manifest. Runner `61f64e79...` matches clean NASolve
`56101b09...` / NARestraints `a7b6a0c9...`; all 110 runtime members verify.
Phenix **2.2.1-6174** (dispatcher `2.2.1`) completes the continuation/audit in
**76.066902 s** and native readback in **1.692405 s**, both exit zero. Original
manager and saved full-precision start/target/entire gradient match; installed
source identities, definitions, compiled NARestraints policy and static proxies
survive. All **17 mechanics checks** and **336 sampled endpoint directions**
pass. Independent review recomputes all 1,344 four-step samples/bounds and
candidate serialization byte for byte, without executing captured code.

The new target changes **2697.762263611603 -> 2599.5275576416398 (3.64%)** and
corrected norm **372.53738052839816 -> 144.16496914598542 (61.30%)**.
Stopping remains **NOT_CONVERGED_LIMIT**: **1,000 new iterations / 1,036 calls**,
cumulative **2,000 / 2,064**, no recorded error and native criterion false.
All accepted targets decrease; the last 100 iterations lower the target by
**8.7054**, with fluctuating corrected norms. Overall corrected-stage target
and norm drops are **31.32% / 87.02%**. PDB-rounded target/norm remain separate:
**2602.971189992592 / 950.90556704461**.

Both precisions retain **three distance / ten angle nominal deviations >=5**
and zero sign conflicts among 158 chirality proxies. CGY A:20-DX D:3 contacts
are **5.3540 / 4.3596 / 5.5828 A** versus 2.8 A, for N1-O2 / N3-N1 / N4-O6;
nine angle outliers involve that pair. DP B:4 C6-N5-C7 remains **127.7493
degrees** versus 109.471. Native target contributions are **1193.6456 angles**,
**553.0823 bonds**, **552.5565 dihedrals**, **225.9220 nonbonded**, **51.9768
parallelity**, **11.6966 planarity** and **10.6477 chirality**. Category gradient
norms can cancel; they do not add. The cause of slow convergence is not proven.

**Cedar 29 returned and verified: sampled rotation derivatives PASS.**
`scripts/build_cif_base_rotation_probe.py` builds
`29_Cedar_probe_cif_base_rotation.py` from the verified Cedar 28 capsule. The
reusable planner ranks nominal bond/angle outliers, then selects supported
connected base graphs without code/attachment-name allowlists. Offline actual
replay selects A:20, D:3 and B:4, each with 11 base atoms; N/C attachments and
unsupported cases have generic regression controls.

The diagnostic rebuilds the exact original native inventory and matches its
whole corrected initial vector, then both saved endpoint family targets and
entire gradients before any scan. Proper independent rotations about each
C1-prime/attachment axis preserve the scaffold, attachment and internal base
geometry. Nine fixed angular samples at full/rounded precision report the
unchanged full objective, isolated category contributions, selected scalar
measurements and source angle/type/plane context. Fresh four-step rotational
derivatives, baseline repeats, additivity, +/-180 periodic energy and rigid
distance controls remain independent outcomes. Limits are **six supported
groups / 3,000 total energy calls / 1,200 s**. All **17 preflight evaluations**
count toward the cap. A lower sampled target is not an adoptable model or a
minimum; internal base parameter conflicts remain visible.

All **17 initial fail-before regressions** now pass. **40 new tests** cover
generic graph/axis controls, an independent right-handed rotation oracle,
biased derivatives, incomplete/changed endpoint and source evidence, native
manager drift, budgets/timeouts, coherent captured-source forgery and deleted
builds with poisoned ambient/captured code. **88 focused pass (30.38 s)** and
**1,902 full pass, two skips, 276 subtests (136.61 s)**. The actual 1,104-payload
source-bundled offline inspector and exact prior mechanics replay pass. There
is no installed Phenix/Coot here; native worker tests use explicit fakes.

All **1,173 returned payloads** verify, with all 1,104 Cedar 28 payloads and
manifest preserved byte for byte. Clean build/runner hashes, 111 runtime files,
source/static identities and all 17 prerequisite mechanics checks replay.
Phenix **2.2.1-6174 / dispatcher 2.2.1** completes in **31.56962 s**, exit zero,
using **1,201/3,000** energy calls. All **96 rotational derivative directions /
384 four-step samples** recompute as consistent. Both precision cases retain
repeat/additivity/periodic/rigid controls. Each of A:20, D:3 and B:4 favors zero
degrees on the coarse grid. Nonzero validated slopes remain; this is no proof
of a minimum, complete pose search or scientific qualification. DP's retained
N5 targets still sum to **339.714 degrees** against a shared planar constraint.

**Cedar 30 returned: preserved input-parser failure, no candidate produced.**
`scripts/build_cif_numerical_recovery_probe.py` builds the next runner from the
exact Cedar 29 ZIP. The generic planner selects declared source plane/angle
reviews independently of residue name or model residual. This bounded probe
explicitly selects DP; five other eligible source contexts stay deferred.
The original 35 atoms, 37 bond declarations, explicit charges/H and four
chirality declarations survive a graph-only export. Old numerical targets and
energy types are excluded from the generator input, with all original fields
preserved in the frozen source. Complete declared source x/y/z seed naming and
initial geometry, explicitly labelled as non-independent ideal coordinates.

Existing isolated eLBOW generation/capability and chemistry/numerical gates are
reused. The candidate is compared against both the graph-only input and original
numerical source; complete formal-charge declarations must match. New raw
reviews/refusals remain visible. Up to three explicitly selected components and
a default **600 s per component** bound the candidate phase. No dictionary is
applied to a manager, no existing modifier is recomposed, and no crystal-model
optimization, policy recompilation, ReadySet retry, refinement or adoption runs.
All **47 new regressions** pass; **123 focused tests (13.63 s)**
and **1,949 full tests, two skips and 276 subtests (140.81 s)** pass.
Actual-input deleted-build/poisoned-import transport verifies 112 runtime files,
all prior evidence and the unchanged DP graph seed. Installed generation is
pending; exact validation commands and boundaries are recorded in the ledger. Existing geometry/convergence, charge, pucker, stereochemistry
and experimental gates remain independent.

All **1,185 returned payloads** verify, including the 1,173 unchanged Cedar 29
payloads and manifest. Runner `8aedfb0e…`, clean source pins and all 112 runtime
members match. The 17 mechanics/96 rotation prerequisites replay. Installed
eLBOW **2.2.1-6174** stops in **2.358774 s**, exit one, before producing any
candidate: its reader accesses `pdbx_model_Cartn_x_ideal`, while graph export
emitted the lower-case `cartn` spelling. Chemical rejection and generated
plane/angle assessment are **NOT_ASSESSED**, despite the wrapper's REJECTED and
zero-review console lines. No model was optimized or changed.

**Cedar 31 prepared: general tag-case correction plus the requested PDU control.**
The same builder accepts `--delivery-prefix 31_Cedar --component-control PDU`.
Canonical external CCD coordinate tags are emitted for both source ideal and
curated coordinate families. Old/corrected DP exports have exactly equal parsed
fields/values after tag-case normalization. The reader preserves the complete
Cedar 30 failure capsule and rechecks its predecessor proof before retrying.
Absent generated dictionaries now print numerical assessment NOT_RUN.

PDU is a separate **public component control**: its unmodified CCD fixture is
hash pinned under tests and is not added to the production curated library.
The source has **38 atoms / 23 heavy atoms / 39 bonds**, a C5A-C5B triple bond,
three specified D-sugar centres, and declared neutral phosphate state. Its O3-prime
hydrogen is named H2; the graph-based rule identifies the bond correctly.
The existing NARestraints row maps it to T, with the C7 plane role mapped to
C5A. Actual source-atom/compiler checks pass for the existing AT recipe
(two bonds/two angles/one pair parallelity) and both stacking orders. These
are compiler controls with a synthetic partner role template, not proposed
experimental/native pair geometry. DP and PDU generation remain independently
reviewed, with all chemistry/state rejection gates retained. No PDU site is
inserted into the frozen model. **23 new regressions, 146 focused tests
(16.16 s) and 1,972 full tests, two skips and 276 subtests (140.70 s)** pass.
The actual-input relocated runner passes after both clean source copies are
removed and ambient imports poisoned: 114 runtime files, all prior proof and
both graph sources verify. These were the pre-delivery checks; installed
results are recorded below.

**Cedar 31 returned and verified (2026-10-20): two execution failures; no dictionaries.**
All **1,209 payloads** verify, including every preserved Cedar 30 payload and
manifest. Rebuilding the trusted C31 runner at clean NASolve 36c75495 / pinned
NARestraints reproduces SHA-256 308c53d1; all 114 runtime members match. The
17 mechanics and 96 sampled rotational prerequisites replay.

Installed eLBOW **2.2.1-6174** (dispatcher 2.2.1) stops DP in **2.600242 s**
on absent alt_atom_id metadata. PDU runs **58.275747 s**: it reads 38 atoms /
39 bonds and three R/S/R sugar centres, performs RM1/GDIIS, reports geometry
not converged at the first 60-step limit (61 logged evaluations), then fails
loading a zero-byte candidate.elbow_opt.xyz with an UnboundLocalError for smc.
Both exit one without candidate.cif. The wrapper REJECTED values are execution
outcomes, not chemical rejection. PDU source/NARestraints compiler controls
still pass; generated chemical/numerical assessment remains NOT_RUN. Two
pickle outputs were excluded by the prior shuttle and are never loaded.

**Cedar 32 prepared: general alias compatibility and read-only native evidence.**
The exporter copies exact primary IDs into alt_atom_id only when the entire
alias column is absent; existing aliases and all chemistry remain unchanged.
The receipt records that added naming metadata. DP graph SHA-256 is
3cfff153966194861451113747ba8f1ebbd7b47d58c8aa9acfd50ddfcc4783dd;
PDU graph bytes remain unchanged. The same builder uses --delivery-prefix
32_Cedar --component-control PDU; the runner uses --native-contract-only.

Before another generation, capture four declared eLBOW modules under the
already verified installed library anchor, with exact bytes/hashes and a static
reader-attribute inventory. Run bounded installed read-only checks for both
prepared sources, with state-retention options and no optimizer request.
Source/dispatcher/snapshot checks surround these calls. This is an input-contract
diagnostic, not a Phenix patch, numerical candidate, chemical qualification or
policy change. Installed capture/checks are pending. All **29 new regressions, 175 focused
tests (19.02 s) and 2,001 full tests, two skips and 276 subtests (142.51 s)**
pass. Deleted-source/poisoned-import replay verifies all 115 runtime files,
1,209 prior payloads, mechanics/rotation proof and both graph sources. See
the native ledger for exact commands, hashes and scope.

**Cedar 32 returned and verified: PDU input PASS; DP dialect REVIEW.**
All **1,229 payloads**, the 1,209-payload predecessor and four exact installed
eLBOW source snapshots verify. Trusted runner 11d3946b matches clean NASolve
88bca3c1 / pinned NARestraints and all 115 runtime members. Prior mechanics and
rotation proof replay. Phenix 2.2.1-6174 read-only PDU exits zero in 1.371951 s;
DP exits one in 3.551229 s on missing atom pdbx_aromatic_flag. The source shows
the complete legacy/CCD dialect gap, including atom stereo and bond order.
The optimizer source confirms the empty-XYZ unbound-local path and a positive
opt_steps control that bypasses its default restart condition. Captured code
was inspected as text, never executed or patched.

**Cedar 33 prepared: checked reader projection and bounded candidate trial.**
Use the same builder with --delivery-prefix 33_Cedar --component-control PDU;
run against the exact Cedar 32 ZIP with --single-block-steps 180. A separate
consumer adapter translates only declared charge/order/flag aliases, refuses
conflicts and unsupported orders, and leaves unknown atom aromatic/CIP metadata
as ?. Original fields and signed chiral volumes survive. PDU input is unchanged;
DP consumer SHA-256 is
6b914d7fed9a98e30ed68b2381507e6d5bb0dc9b351fee48d42ced085c9501fa.

Fresh read-only checks gate each generator. Before any trial, the four installed
source identities must match, and the selected installed options parser must
prove exactly one block with 180 steps. Its module path/hash and default
tolerance are recorded and checked again after generation. Captured source is
not executed; only the installed parser is interrogated. Candidate generation
retains the 600-second per-component bound. No XYZ/pickle is reused, no native
code is patched and no tolerance is relaxed. Nonconvergence is reported as such;
exit zero/file creation never establishes a native criterion. All existing
source/consumer/numerical/formal-charge gates and raw reviews remain in force.
All **39 new regressions, 214 focused tests (24.58 s), and 2,040 full tests,
two skips and 276 subtests (155.92 s)** pass. Actual-input deleted-build and
poisoned-import transport verify all 116 runtime files and the complete
1,229-payload C32 capsule. Installed execution is pending; exact commands
and scope are recorded in the existing native ledger.

**Cedar 33 returned and verified: reader PASS; DP chirality failure / PDU candidate REVIEW.**
All **1,288 payloads** and preserved predecessor manifests verify. Rebuilding
clean NASolve d939d2e0 / pinned NARestraints reproduces runner 63cfbc19 and all
116 runtime members. Both installed read-only inputs pass, and both options
proofs select one 180-step block with unchanged default tolerance. Phenix
**2.2.1-6174** stops DP in **1.923945 s**, exit one, at preparatory
Chiralise/ChiralClass before optimization. The captured CCD reader stores every
stereo token except N as an atom chiral marker; all 35 DP tokens are ?. Its
four source signed-volume declarations are still preserved. Do not replace
unknown tokens with false nonchiral or invented R/S declarations to bypass it.

PDU generation completes in **155.347732 s**, exit zero, and writes candidate
10798e33 while explicitly reporting **NOT_CONVERGED_REPORTED**. Fresh original
chemical/numerical comparisons reproduce its review: exact graph, triple bond,
H and complete formal charges survive, with zero retained plane/angle findings.
All three R/S labels disappear, but three generated signed sugar terms agree
with both source ideal and generated coordinate handedness. This is not an
independent absolute CIP assignment. Its 181 printed energy rows reach
-517.4105 at row 146, rise to -477.2222 at 147 and end at -480.5612; no captured
intermediate coordinate trajectory establishes the cause. No dictionary is adopted.

**Cedar 34 prepared: read-only source/candidate and native reader stereo audit.**
Use the same builder with --delivery-prefix 34_Cedar --component-control PDU,
then the exact Cedar 33 ZIP with --component DP --stereochemistry-audit-only.
The gate preserves both returned phases, installed source/options proofs and
all prior native mechanics/rotation evidence. Offline checks compare missing
labels, exact chemistry, ordered signed targets and both coordinate hands;
absent/unsigned/unknown evidence stays review and inversions/conflicts reject.
Printed energy trajectories are descriptive, never convergence criteria.

The native diagnostic captures Utilities.py plus MoleculeClass.py,
TopologyMixins.py and ChiralClass.py under the verified installation anchor.
A maximum 30-second worker per component records actual reader markers and
separately exercises the reader's chirals=True constructor. It is not a full
builder replay. Constructor exceptions stay evidence; selected module identity,
snapshots, input and dispatcher hashes are checked throughout. No whole-molecule trial,
dictionary writer, captured source or serialized molecule is requested. Linux
subprocess controls are explicit fakes; the installed stereo result is pending.
The **55 new regressions**, **269 focused tests (31.11 s)** and **2,095 full
tests, two skips and 276 subtests (160.49 s)** pass. Actual-input replay verifies
all 118 runtime members after deleting both clean build copies and poisoning
ambient imports. The older-checkout tracked edit and local runner ignore survive.
Exact commands and bounds are recorded in the native ledger.

**Cedar 34 returned and verified: DP constructor assertion; PDU known-marker PASS.**
All **1,320 payloads**, the preserved 1,288-payload predecessor and all source,
worker and input hashes verify. Trusted runner ffc4d69a matches clean NASolve
efd63bd3 / pinned NARestraints and all 118 runtime members. The original 17
mechanics and 96 rotation checks replay; saved PDU stereo/trajectory summaries
also reproduce. DP marks every unknown token as chiral and fails the same
ChiralClass assertion; PDU's three known markers and constructor pass.

The captured code corrects the earlier constructor-scope description:
Chiralise invokes ChiralClass.Optimise on local templates, with native RS
notation. Legacy optimization/CIP NOT_RUN flags did not instrument these
operations. Preserve the historical receipts and this explicit interpretation;
no whole-molecule dictionary trial or saved source/candidate/model edit ran.
Future constructor reports use policy v2 and uninstrumented-internals fields.

The original DP has data_comp_list, but the graph export removed it. The
installed dispatcher therefore selects CCD instead of the monomer reader.
**Cedar 35 prepared:** an explicit source-dialect adapter preserves original
comp_list routing, source metadata, signed declarations and equal x/y/z aliases
in a separate target-free input. It invents no atom chirality, adds no old
numerical target/energy type and leaves PDU's CCD consumer byte-identical.
DP consumer SHA-256 is
4648c37ce867cce5a285d5f31a394a334b2cb9e347936511525a947927798bfa.

Use --delivery-prefix 35_Cedar --component-control PDU, then the exact Cedar 34
ZIP with --component DP --source-dialect-audit-only. A maximum 30-second selected
native parser read per component records dispatch and atom/bond/charge/coordinate
inventory, with exact dispatcher and monomer-parser snapshots. It requests no
chiral constructor or numerical generation; parser internals remain uninstrumented.
Raw mismatches retain review, and charge semantics/signed stereo remain separately
unqualified pending the returned parser source. All **41 new regressions**, **310 focused tests (36.04 s)** and **2,136 full
tests, two skips and 276 subtests (164.60 s)** pass. Actual-input transport
verifies 119 runtime members after removing both clean build copies and poisoning
ambient imports; tracked local edits and runner ignores survive. Documentation
mirrors, 148 relative links and the rendered editable figure pass. Exact commands
and bounds are recorded in the native ledger. Installed
source-reader acceptance remains pending; default generation is unchanged.

**Cedar 35 returned: pre-native temporary-path failure.** All **1,327 payloads**
and the preserved Cedar 34 capsule verify. The clean pinned runner matches;
the prior 17 mechanics checks and 96 rotation directions replay. Both graph
previews and the public PDU control match their predecessor. The receipt records
an empty consumer preparation and no native parsing or generation. The adapter's
internal TemporaryDirectory path hits the strict symlink-parent guard. A
synthetic aliased system temp root reproduces the exact error for both monomer
and CCD sources; the returned capsule does not capture the actual temp path.

**Cedar 36 prepared:** resolve only that newly created, tool-owned temporary
directory before the exact graph check. Preserve caller-output symlink and
overwrite refusals, exact source/consumer bytes and every chemistry gate. The
retry accepts the exact failed Cedar 35 capsule, preserves it whole and reads
its verified nested Cedar 34 source/constructor evidence. No chemistry-specific
exception, dependency or production-default change is introduced. All **16 new
regressions**, **132 focused tests (13.55 s)** and **2,152 full tests, two skips
and 276 subtests (173.76 s)** pass. The relocated runner replays all 1,327
actual payloads through an aliased system temp root after both clean build copies
are removed, with poisoned ambient imports and the everyday tracked edit intact.
Both consumer hashes are unchanged. Exact commands and bounds are recorded in
the native ledger.

**Cedar 36 returned: native reads complete; DP order/charge boundary exposed.**
All **1,355 payloads**, all byte-identical predecessor members, pinned clean
runner/build and 119 runtime members verify. The 17 mechanics and 96 rotation
checks replay. Both parser snapshots match in both native cases. PDU passes all
six raw route/inventory checks. DP preserves route, 35 atoms/elements, 37 bond
memberships, source coordinates and four signed markers, but every bond is
single and both source -1 charges are zero. The captured parser's lookup accepts
lowercase order words and defaults unknown spelling to single; its atom loop
reads no charge field. No new optimizer, generation or saved model change ran.

**Cedar 37 prepared:** translate explicit monomer order aliases to the exact
lowercase vocabulary, preserving order semantics and original source/graph
bytes. Separately test source-declared charge population on the temporary parsed
component using --declared-charge-control. Exact route/identities/elements/bond
orders/coordinates and complete integer charges bounded by the reviewed native
Chargise constraint are preconditions. Conflicts block assignment; only an
otherwise zero monomer object is populated by identity and source total.
Already-correct CCD charges are checked without assignment. Raw reader findings
stay separate; before/after recorded graph/stereo fields and a fresh host-side
inventory/total check accompany the control. Two additional Utilities/MoleculeClass
snapshots must match the verified Cedar 34 source proofs. No constructor,
Chargise, optimizer, generator or production-default change is requested.
All **48 new regressions**, **180 focused tests (22.36 s)** and **2,200 full
tests, two skips and 276 subtests (172.19 s)** pass. The relocated runner
replays all 1,355 actual payloads after both clean build copies are removed, with
an aliased temp root and poisoned ambient imports. It replays raw reader
findings, retains the tracked local edit and keeps PDU bytes unchanged. The
120-member runtime is verified; exact commands and bounds are in the native ledger.

**Cedar 37 returned:** all **1,387 payloads**, the clean pinned runner/build,
120 runtime files and byte-identical predecessors verify. All declared DP orders
now survive native reading. Its raw charges remain zero; the explicit control
passes, changing only OP2/OP3 to source -1 with total -2. Recorded graph,
coordinates and stereo fields stay fixed. PDU passes raw inventory and its
already-preserved charge control. No new generation or optimization ran.

**Cedar 38 prepared:** generic declared-triple-edge and neighbor selection,
exact installed resource/API capture, and fixed isolated component/native
comparisons. Read default monomer lookup, replay the captured installed CIF and
check the saved PDU candidate with the same seed/SS-disabled policy. Record active
distance/angle membership, targets, ESDs/weights, geometry and linear-axis
torsions; infer no replacement targets. Add hash-pinned public 5PC as an
independent C7/C8 naming control. Two 5PC workbook records remain ambiguous;
no role record or 5PC pairing/stacking policy is selected. General screening
thresholds are review policy, not chemical approval. The saved PDU candidate
still has six linear-axis torsions, bent coordinates and reported nonconvergence.
Native isolated triple-bond results await the selected Mac installation.
All **95 new regressions**, **159 focused tests (17.89 s)** and **2,295 full
tests, two skips and 276 subtests (185.91 s)** pass. The 124-member runtime
replays the actual C37 archive with raw/controlled charge checks after deleted
builds and relocation, with poisoned imports, an aliased temporary root and the
protected everyday edit intact. JSON mirrors, 149 links and the rendered editable
figure verify. Exact methods, commands and hashes are in the native ledger.

**Cedar 38 returned:** all **1,446 payloads**, clean published build/runner,
124 runtime files and exact nested lineage verify. Both default monomer
lookups return no component; native interpretations stop with 38/39 unknown
energy types. The supplied PDU candidate loads with active 1.174 Å / ESD 0.020 Å
and two 180° / ESD 3° terms, plus six linear-axis torsion reviews. Those native
coordinates are fixed public source seeds, not a repaired generated candidate.
No optimization, new generation, ReadySet retry or adoption ran.

**Cedar 39 returned and verified:** all **1,486 payloads**, the clean published
runner/build and 125 runtime members match. Both exact installed CCDs preserve
public chemical declarations and SMILES descriptor text. Both simple native
readers pass all six inventory checks. All four direct/wrapped numerical monomer
lookups are missing; DG/DC canonical controls resolve through GeoStd. Source
comparison and raw reader replay are independent of numerical restraint
qualification. No ReadySet, constructor, generation or optimization ran. Full
ReadySet selection, mapped SMILES, native stereo and geometry remain open.
Exact hashes, paths and scope are in the native ledger.

**Cedar 40 returned and verified:** all **1,529 payloads**, the clean published
runner/build and 126 runtime members match. Both accessors select CACTVS
canonical SMILES and 24 static source files fit the captured import budget.
ReadySet itself did not run. A static branch reads then deletes SMILES before
requesting chemical_component; observe the actual call before assigning cause.

**5PC policy review resolved in the auditor:** two existing cytosine-sheet rows
share all operational C-like roles and context. Descriptive aliases/entry counts
and modification-description columns do not make different atom mappings.
Equivalent role records now compile once with both raw rows retained; conflicts
and missing roles still review/fail. Explicit C5-mod/C7-mod annotations stay out
of atom inventories. A registered canonical partner precedes modified-family
synthetic controls, so 5PC checks G:C and both stacking orders. The existing
NARestraints workbook/recipes are correct for this scope; no edit/release is
needed under the user's conditional missing-entry authorization.

**Cedar 41 returned and verified:** all **1,624 payloads** and the trusted
published build match. Phenix 2.2.1-6174 reaches the early file-input eLBOW call
for both controls, then exits ReadySet with SystemExit 2: the diagnostic wrapper
leaked ReadySet PHIL options into eLBOW's separate process-argument parser.
The receipt workers exit zero after saving those exceptions (PDU 8.487559 s;
5PC 1.713853 s). Neither ReadySet invocation completes. Both surviving CIFs are
byte-identical public-source copies, with no numerical length/angle targets;
native interpretation stays NOT_RUN. No historical floppy-chain cause is
established. PDU T and 5PC C pairing/stacking compiler controls both PASS.

**Cedar 42 returned and verified (2026-10-21):** all **1,747 payloads** and
the rebuilt clean published runner match. Phenix 2.2.1-6174 completes PDU/5PC
ReadySet in **13.447281 / 5.993324 s** and their fixed-source-seed native
interpretations in **0.967536 / 0.796326 s**. Each observed file-input eLBOW call
returns successfully with unchanged kwargs and no SMILES argument. Generated
triple targets are **1.203 / 1.186 Å**, both ESD **0.020 Å**; both adjoining
angles target **180°**, ESD **3°**. All four dictionary/native target screens
PASS. Each heavy-only manager has 23 atoms, with exact captured native output.

Six generated torsions per dictionary include a linear atom triple; three are
active without hydrogens. Those reviews stay visible alongside raw generated
chemistry: HOP2/HOP3 are absent, charge sum changes **0→−2**, R/S metadata is
omitted and generated signed chirality remains separately assessed. 5PC also
retains an angle/plane consistency review. The existing PDU T / 5PC C compiler
controls PASS. No dictionary is adopted and no historical floppy-chain or SMILES
cause is established by this isolated result.

**Cedar 43 returned and reviewed (2026-10-21):** all 1,794 payloads and the
published runner/build metadata verify. Both Phenix 2.2.1-6174 controls complete
at 1,603/3,000 paired evaluations. Single/container, repeat and reversal evidence
passes at all three saved coordinate cases; all 234 real-coordinate directional
checks independently recompute. Every selected torsion remains near-collinear.
The largest full-precision 5PC single-torsion gradient norm is 578,927.34;
approach controls show inverse-radius growth and undefined exact-collinear
geometry. This is conditioning evidence, not another demonstrated gradient bug,
convergence or historical causation. Original manager signatures remain fixed.

**Cedar 44 returned and reviewed (2026-10-21):** all 1,847 payloads and the
trusted published runner/build verify. Four Phenix 2.2.1-6174 interpretations
complete. Both original inventories match C43; both candidate comparisons pass
all preservation checks. Exactly six effective-definition rows and three active
dihedrals disappear (28→25); constants remain eight, with bond/angle/chirality/
plane/API/policy/atom fields intact. Both dictionary/native triple screens PASS,
and no linear-axis torsion remains. Source/generated phosphate and stereo
findings stay open. This is exact native mechanics, without an energy comparison
or adoption.

**Cedar 45 returned and reviewed (2026-10-21):** all 1,910 payloads and the
trusted published runner/build verify. Both native jobs complete at 1,620/2,000
evaluations. All 246 derivative arithmetic directions, omitted-term deltas,
unrelated families and target/gradient additivity pass. Full 5PC gradient norm
falls 578,161→1,363; full PDU 60,288→1,557. PDU passes all strict cases. Two 5PC
cases retain count-only review: full-precision 71→75 and source-seed 70→67;
repeated energies and all gradient components are exactly unchanged. The old
count/combined-derivative failures remain preserved. Pair identities and changed
contributions were not captured; cache behavior is an inference pending proof.

**Cedar 46 returned and independently reviewed (2026-10-21):** all **1,983
payloads**, the clean `e5e79cc8…` published build, runner `89bff37e…` and 131
runtime members verify. All 1,910 prior payloads and their manifest are unchanged.
Both Phenix **2.2.1-6174** jobs complete, in **2.943343 s / 1.587708 s** for
5PC/PDU, with **1,716/2,000** manager calls each and **1,758/1,528** pair kernels.
All six cache preflights and strict numerical cases PASS. Independent replay
recomputes **48 transition proofs**, the 3,286-call pair-kernel budget and
**246 strict derivative directions**, without executing captured code. Four
added 5PC pairs (71→75) and three removed pairs (70→67) each contribute exactly zero residual and all
six gradient components exactly zero; common contributions and native sums
remain fixed. The settled memberships pass the original count/tolerance gates.
The pinned worker reports continuous perturbed membership PASS; those raw
perturbed lists are not stored for independent offline identity replay.

This closes the fixed-coordinate cache question for these controls. Preserve
the earlier C45 count reviews. Charge/protonation (source 0 versus generated
−2 and missing HOP2/HOP3), omitted R/S metadata/absolute CIP, 5PC plane/angle
findings and ordinary whole-scaffold integration remain separate work. No
optimizer, source dictionary, coordinate model, chemical state, production
default or scientific adoption changes. Repeating the unchanged audit is not
the next action.

**Cedar 47 returned and verified (2026-10-21): three constructor exceptions.**
All **2,036 payloads**, clean published `96209831…` build, runner `551d6a5c…`
and 132 runtime members verify, preserving all 1,983 prior payloads and manifest.
Phenix **2.2.1-6174** workers complete in **2.348079 / 0.743316 / 0.737424 s**
for DP/PDU/5PC. Source graph/charge, promotion and marker gates pass. DP/PDU
raise `MoleculeClassError: not chiralised`; 5PC raises missing `OptimiseBFGS`.
The old false route gate reflects omitted after-format metadata on exceptions,
not a demonstrated route change. Partial failed coordinates and failed DP/PDU
hand gates remain recorded; none is an adopted or restart candidate.

The diagnostic omitted native CCTBX backend selection. C48 follows the captured
native reader's `SetCCTBX(True)` prerequisite before original Chiralise.

**Cedar 48 returned and verified (2026-10-21): backend/completion PASS,
source-relative handedness REVIEW.** All **2,092 payloads**, clean published
`bb5efb44…` build, runner `b8ed1739…`, 132 runtime members and unchanged C47
payloads/manifest verify. Phenix **2.2.1-6174** constructors complete in
**1.984474 / 0.817210 / 0.821684 s** for DP/PDU/5PC. All four backend gates and
every graph/charge/promotion/marker/route gate pass. Only source-relative
handedness fails: **DP C1-prime; PDU C1/C3/C4-prime; 5PC C1-prime**. Original
sources/labels remain intact; these temporary coordinate results are unadopted.

An independent offline comparison of all four neighbor triples and the four-
neighbor determinant adds a **DP C4-prime** orientation review that the old
selected basis passes. **5PC C4-prime** preserves four-neighbor orientation
while one triple reverses. Keep both measures; neither independently assigns
absolute CIP or proves a final molecular inversion. Saved endpoints do not
locate the first native change or establish a causal implementation defect.

**Cedar 49 — implemented native action (now returned):** compare a fresh unobserved constructor and
a fresh observed constructor for each original DP/PDU/5PC source. Observe
native outer/local construction, Z-matrix, restraint, CCTBX optimization,
tightening and native R/S-return boundaries without changing arguments or
kernels. Retain complete parent snapshots and local atom order/shared-object
evidence, restore class methods on completion/exception, and replay the call
ledger/all-basis geometry. Report first observed reviews rather than assigning
causality. Fresh-repeat equality and the old C48 endpoint comparison remain
separate; random state is not reset. No failed local endpoint is resumed.

Build `49_Cedar_probe_cif_constructor_trace.py` with both controls; run exact
**48_Cedar_5u8wjea_** using `--component DP
--source-constructor-trace-audit-only`. At most **six owned workers × 30 s**;
cap each observed constructor at **256 calls / 512 boundaries**. Returned
native trace evidence is recorded below. No full builder, numerical dictionary generation,
chemical-state choice, absolute CIP or adoption is requested. See
`source_native_constructor_trace_2026_10_21` in the existing machine ledger.
Software checks pass **231 focused / 2,717 full tests**, two skips and 276
subtests. Actual C48 replay passes after build deletion and relocation, with
poisoned imports, aliased temporary roots and preserved everyday edits. These
checks remain distinct from the native boundary evidence below.

**Cedar 49 returned and verified (2026-10-21): exact fresh repeats PASS;
hand and DP marker reviews remain.** All **2,190 payloads**, clean published
`c5346623…` build, runner `eeae96ce…`, 133 runtime members and every unchanged
C48 payload/manifest verify. Phenix **2.2.1-6174** completes all six constructors.
Observed DP/PDU/5PC times are **1.010668 / 0.979949 / 0.992760 s**; controls are
**2.434568 / 0.767758 / 0.790353 s**. Every fresh comparison gate passes and
each control matches C48 exactly. All **84 calls / 168 enter-exit boundaries**
replay from raw records. PDU/5PC trace integrity passes; DP fails only chemical
metadata continuity. Native signed-volume words become native chiral markers,
then `GetRSNotation(input_xyz=True)` returns None and the chiral field becomes
None. Separate volume_sign fields survive. Keep that review and all hand gates.

No preexisting source hand reviews occur. First warnings mostly appear at
Z-matrix exit; 5PC C4-prime first appears at R/S inspection entry. Warnings
clear and recur while local templates share parent objects. Parent snapshots
can mix temporary local frames, so endpoint signs/timing alone neither qualify
a completed molecule nor identify a unique causal implementation defect.

**Cedar 50 — implemented native action (now returned):** follow named local coordinate order through
native GetCoordinates/SetCoordinates and actual manager chirality proxy bases.
Record vectors, local/global indices, native signed targets/weights/both-sign
flags, and the post-optimizer index transfer. Replay exact assignment and
ordered source-volume/target comparisons; report local hands before/after.
Keep fresh controls and every original source/metadata/hand warning. No native
patch, marker translation, coordinate repair, chemical-state choice or adoption.

Build `50_Cedar_probe_cif_constructor_mapping.py` with both controls; run exact
**49_Cedar_izfiw4xk** using `--component DP
--source-constructor-mapping-audit-only`. Bounds: **six owned workers × 30 s**,
**256 calls / 512 boundaries** each, **64 rows** per vector/proxy capture.
Returned mapping evidence is recorded below. The full builder, generation, absolute CIP,
scaffold qualification and scientific adoption remain separate. See
`source_native_constructor_mapping_2026_10_21` in the existing machine ledger.
Software checks pass **222 focused / 2,760 full tests**, two skips and 276
subtests. The 43 new regressions cover named vector order, target bases,
rigid motions, coordinate transfers, fake owned-worker exceptions and C49
mutation rejection. Actual C49 replay passes after build deletion/relocation,
poisoned imports and aliased temporary roots, preserving everyday edits.
These are software/saved-evidence checks; returned native findings follow.

**Cedar 50 returned and verified (2026-10-21): exact repeats and vector
assignment PASS; proxy-basis REVIEW.** All **2,288 payloads**, clean published
`2e7c48a7…` build, runner `b7718dea…`, 134 runtime members and unchanged C49
payloads/manifest verify. Phenix **2.2.1-6174** completes six constructors.
Observed DP/PDU/5PC times are **1.151182 / 1.048801 / 1.075298 s**; controls are
**1.637737 / 0.758201 / 0.726506 s**. Fresh and previous endpoint matches pass.
All **120 calls / 240 boundaries**, **18 getters / nine setters**, and **nine
sorted-index transfers** replay. Preserve all source-hand and DP marker reviews.

The legacy local-order view has one invalid proxy-origin graph basis in each
component. Independently sorting the saved names by native index matches all
nine source tetrahedral graphs and all PDU/5PC target signs. DP C1-prime still
opposes its source (-2.3736962 versus +2.3867843). This is a hypothesis about
the producer convention, not proof that native arrays can be substituted.

**Cedar 51 returned; Cedar 52 is the next native action.** The original
named-key audit completed six constructors but captured no atom-object keys:
the selected native dictionary uses integers. All 2,395 payloads and fresh/
previous repeats verify. Original mapping/hand/DP-marker findings remain.

ATL passes its independent pinned public graph/four-centre and existing T-class
NARestraints pairing/stacking checks; native ATL construction is NOT_RUN. No NAR
workbook or release change is needed. C52 records native integer entries/link
positions and named local atoms under selected get_key/GetCoordinates source
proofs, with the unchanged three-component/six-worker scope. See the current
continuation boundary at the top and the existing machine records
`source_native_constructor_index_basis_2026_10_21` and
`source_native_constructor_integer_keys_2026_10_21`.

**Requested follow-on after building: a fresh eight-pair synthetic live run.**
Preserve **K:X, D:T, Z:P, B:S, PDU:A, 5PC:G, 5CM:Q and F:A** in one explicitly
declared target. `Q` resolves to **S6G**, `F` to **DF**; the existing reviewed
B:S family is **IGU:IMC**, without adding a general S alias. Prepare a complete
annotated sequence and nonconflicting chain/site map when staging the run;
the pair list alone is not an executable sequence. Preserve the old six-pair
recipe/runs. Use a fresh donor-data test directory, explicit termini and source
hashes, NARestraints-owned pairing/stacking, preserved Free-R and disabled
synthetic AutoSol. Check ordinary construction/linkage, effective triple-bond
terms, chemical-state/stereo/plane findings, numerical/geometry/refinement
evidence and human model/map review separately. This is planned and not run.
The [sequence contract](sequence-family-targets.md#planned-eight-pair-synthetic-live-test)
and machine evidence entry `post_build_mixed_sequence_live_test_2026_10_21` own
the exact requested coverage. The next live delivery retains the single pinned
fetch/worktree/build/run block joined by `&&`.

Preserve the everyday checkout and all earlier evidence. The ignored branch-artifact destination and merge-time
inventory/hash/archive policy remain in force. No new dictionary, native-model
result, policy guess or refinement is adopted. Private source snapshots, logs,
capsules, generated candidates and runners stay outside Git.

The prior membership implementation suite passed **1,646 tests, two skips and
276 subtests (71.72 s)**. Cedar 22 passes **107 focused (10.81 s)** and
**1,669 full tests, two skips and 276 subtests (76.03 s)**, including synthetic
deleted-build transport and actual-input offline replay. This Linux environment
has no Phenix; these checks do not claim a new native optimization. Exact
capsule, replay, native and descriptive evidence lives in the existing ledger.

**Cedar 20 returned and reviewed (2026-10-17):** all **367 payloads** verify,
including 311 byte-identical frozen Cedar 19 members. Runner `e38625e1…` matches
clean NASolve `7acca935…` / NARestraints `a7b6a0c9…`. Saved endpoints were reused;
no new optimization. Serialization reproduces candidate `27d534e3…` byte for
byte. Phenix 2.2.1-6174 completes its fresh native reread in **3.406067 s**, exit
zero; 877 identities/43 sites, component definitions, custom requests and all
19 CIF/12 PHIL bytes survive. Native dispatcher/four recorded API hashes match.

The original mechanics result correctly remains **11 PASS / three REVIEW**:
five extra simple bonds, ten extra angles and changed proxy counts. No original
proxy is lost or changed. All added rows have captured origin 2; each added bond
crosses the unchanged **3.4 Å** cutoff, and each gains two endpoint angles
through original covalent stems. Native logs report 25→30 hydrogen bonds and
50→60 associated angles, with the same 12 declared base pairs and 23 stacking
pairs. The effective native PHIL is byte-identical. These observations match
the public CCTBX distance-filter mechanism; the capsules do not fingerprint its
secondary-structure source, so this is cutoff-consistent attribution, not a new
installed-source causal experiment or a passed exact-manager comparison.

| Native contact | Before (Å) | After (Å) |
| --- | ---: | ---: |
| A:2 N1 – C:14 N3 | 3.458774 | 3.182690 |
| A:4 N3 – C:12 N1 | 3.484427 | 3.342721 |
| A:10 O6 – B:6 N4 | 3.983422 | 2.789232 |
| A:16 N6 – D:7 O4 | 3.626803 | 2.826950 |
| A:17 N4 – D:6 O6 | 3.420955 | 2.989775 |

Every reread coordinate matches Cedar 19's saved rounded vector at PDB precision;
maximum floating-component difference is **7.11e-15 Å**. Its recorded fixed-manager
PDB evaluation remains **3,679.853670**, gradient norm **978.673025**. This is a
preserved historical evaluation at that rounded vector, not a new energy of
the freshly rebuilt manager. The 500-iteration **NOT_CONVERGED_LIMIT** result
remains. Fixed captured proxies at the reread points give four bond/ten angle
nominal deviations at least five; the fresh manager has five/ten because it
contains additional terms. All 158 recorded chirality proxies have no sign
conflicts. None of these counts certifies geometry, pucker or experimental fit.

**Cedar 20 review outcome:** the Cedar 20 return is fully reviewed from saved evidence;
no repeated Mac/native inventory is needed. `cif_native_reload` adds reusable
read-only attribution and endpoint-equivalence reports without changing the
old checks, targets or production behavior. Origin/cutoff are explicit caller
evidence; synthetic origin 37/ZZZ tests prevent a hardcoded native-origin or
residue exception. Missing/changed terms, unpaired angles and other mutations
stay unexplained. No new native execution or geometry trial is delivered here.

**Next scientific gate:** prepare a geometry/convergence trial under Cedar 21's
verified explicit NARestraints-owned pairing and stacking policy. The accepted project
policy is that NARestraints pair selections, stacking relationships, mapped
planes and recipe targets supersede
Phenix's automatic secondary-structure guesses. The native consumer must apply
that policy without adding competing inferred contacts or silently dropping
intended contacts because their starting geometry is poor. Keep native geometry
measurement and component/covalent restraint validation independent of pairing
authority. This precedence is decided; the separate diagnostic compiler now
passes both returned native membership checks. Ordinary PostMR is unchanged.
Rebuilding from new coordinates can change that set even when all input bytes
are identical. Preserve the new terms in Cedar 20's historical evidence; do not
increase its cutoff or reclassify its failed comparison to manufacture PASS.
The new authority policy defines a separately documented objective. Its contact
compiler and bounded native membership checks pass; full qualification,
refinement and adoption stay open. The documentation ledger owns the exact
return, original checks and separate fixed-versus-fresh evidence.

**Pairing provenance for that gate:** reuse NARestraints' existing topology-assisted
pair guesser and recipe builder. At pinned source `a7b6a0c9…`, the guesser scores
mapped contact distances, angles and planes, then uses antiparallel run continuity
to rescue weak pairs and extend run ends. These are pairing hypotheses, not
independent confirmation of donor/acceptor chemistry or achieved geometry.
NASolve's opt-in `--modified-pairs-only` path already uses this guesser with
noncanonical recipes enabled, retains pairs touching a modified nucleotide and
writes explicit recipe restraints without stacking. This source inspection does
not establish that the frozen Cedar 20 declarations came from that mode.
Before freezing a future trial, trace NARestraints-guessed versus reviewed/frame-selected
pairs through recipe-mapped contacts to actual native proxies, retaining scores,
warnings and overlap evidence. Check missing, extra or doubly applied terms and
unresolved pairing chemistry; a fixed membership alone does not make a guess
correct. Phenix-inferred alternatives may be recorded diagnostically but do not
override or supplement the NARestraints-owned policy. The exact source record
and authority decision are in the existing native-reload ledger.

**Stacking authority is the same:** reuse NARestraints' general base-class plane
mapping and chain-neighbour stacking builder. Its twelve mapped classes share
reviewed A/T/G/C-like plane templates, including the corrected P/X versus Z/K
roles. Canonical neighbours are explicitly selected with native `stacking_pair`
records; mapped modified neighbours use explicit parallelities (target 0 degrees,
sigma 0.027). Both representations express NARestraints policy. A generic native
declaration is not permission for Phenix to infer different relationships.
Do not disable the entire secondary-structure machinery and thereby lose the
requested canonical stacks; preserve or explicitly compile those relationships.
Unknown mappings currently retain a generic declaration with a warning, so
actual native coverage still needs checking. Track stacking separately from
base-pair parallelity/planarity, verify planes/targets/weights and check missing,
extra or duplicate physical relationships on readback. This extends the decided
authority and is now represented by the separate diagnostic compiler; ordinary
PostMR is unchanged. The unchanged NARestraints stacking/role
tests pass **8 tests (0.33 s)** with
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ../check-venv/bin/python -m pytest -q --tb=short tests/test_stacking.py tests/test_modified_pair_roles.py`.

**Validation:** fourteen initial regressions fail before the audit module exists.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_native_reload.py tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_captured_geometry.py tests/test_cif_fragment_restoration.py`
passes **89 tests (3.18 s)**. The same command without file arguments passes
**1,628 tests, two skips and 276 subtests (72.30 s)**.
Actual capsule/serialization/mechanics replay and saved endpoint comparison
complete locally without a new native execution. New separate schema-1 audit
reports add no dependencies or private scientific payloads; existing receipt,
qualification and native gate behavior are unchanged.

**Cedar 19 returned; serialization continuation implementation (2026-10-17):** all
**310 payloads** verify, including 253 byte-identical frozen Cedar 18 members.
Runner `899562f5…` matches clean NASolve `5e848eba…` / NARestraints `a7b6a0c9…`.
Actual Phenix 2.2.1-6174 matches the captured manager and completes one native
trial in **2.805701 s**, exit zero. Fixed constraint signatures agree. It reaches
**500 iterations / 524 calls**, with no optimizer error, native criterion false
and final gradient norm **408.374112**: **NOT_CONVERGED_LIMIT**. The fixed-manager
target changes **35,629.733600→3,676.065436** (89.6826% lower); PDB-rounding energy
was separately evaluated at **3,679.853670**. This is numerical progress, not
convergence or scientific approval.

The runner then stops **before writing a candidate/native postcheck** because
its serializer incorrectly assumes PDB line order equals native hierarchy order.
All 877 atom identities are present; 157 have different positions in those
orderings. The general fix uses the supported single-model identity bijection
(chain, residue, insertion, alternate location, atom name), retaining component,
element and original-coordinate guards. Output record order/headers/metadata
remain exact, and each saved native endpoint maps to its own atom.

Offline replay of the actual saved endpoints writes all **877 coordinates**
correctly, candidate `27d534e3…`; maximum PDB rounding distance **0.000827 Å**.
RMS displacement is **0.980980 Å**, maximum **5.137862 Å**, so pose and later
scientific review remain material. Captured-proxy full-precision measurements
show four bond/ten angle deviations at least five and no recorded sign conflicts
among 158 chirality proxies. These are projected descriptive measurements, not
a new installed readback, contact inventory or stereochemical approval.

**Cedar 20 delivery:** use the same
`scripts/build_cif_fixed_geometry_probe.py` with `--delivery-prefix 20_Cedar`,
fresh `20_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`20_Cedar_probe_cif_geometry_trial.py`. The one-block ferry starts from
`19_Cedar_probe_build`. Run with `--completed-trial-zip` pointing to the exact
returned Cedar 19 ZIP; the normal Cedar 18 ZIP remains the independently verified
baseline. Both files already exist on the Mac. This path verifies the completed
capsule, frozen prior inputs, model/CIF/PHIL hashes, manager/native API equality
and fixed constraint signatures. It reuses the saved endpoints, preserves their
stopping evidence and performs **no new minimization**. It then serializes by
identity and executes the pending native PDB postcheck with unchanged restraints.
Existing exact identity/definition/full-proxy/count/custom checks still apply.
Both source ZIPs/frozen payloads, all earlier runs and source/charge reviews
survive; no captured script or pickle is executed. No new installation.
The returned Cedar 20 native postcheck is recorded above. Scientific
qualification remains REVIEW; no repeat of this delivery is required.

**Validation:** three initial identity-order regressions fail before the fix.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_fragment_restoration.py tests/test_cif_effective_source_recovery.py tests/test_cif_native_validation.py tests/test_synthetic_dna_shuttle.py`
passes **105 tests (7.71 s)**. The same command without file arguments passes
**1,612 tests, two skips and 276 subtests (73.75 s)**. Reordered
synthetic ZZZ, blank chains and distinct alternate identities pass; reuse never
calls the optimizer and altered native definitions still block the postcheck.
Actual completed-capsule inspection after deleting both build fixtures verifies
**310 source / 312 output payloads**, 104 runtime files and unused poisoned
imports. No new native execution is claimed by that transport proof. Additive
schema-1 fields record correspondence/mismatch counts and anchored saved-trial
reuse; production behavior, existing gates and runtime dependencies stay fixed.

**Cedar 18 returned and verified (2026-10-17):** all **252 payloads** verify,
including 130 byte-identical frozen Cedar 17 members. Runner `25004008…` matches
clean NASolve `6b1000bf…` and NARestraints `a7b6a0c9…`. Phenix 2.2.1-6174 eLBOW
completes in **28.738290 s**, CANDIDATE_REVIEW; both native phases complete
(exit zero, **3.055300 / 1.573842 s**). Dictionary checks are **68 PASS / one
UNSUPPORTED formal-charge readback**, without contradictions; fragment mechanics
are **14 PASS**. Source selection and generator inspection replay; linked
outputs and the nine-atom DF A:19 fragment candidate reproduce byte for byte.
Computed-scalar roundoff is at most **8.89e-13**. One charge-evidence array has
different dictionary iteration order; its atom-keyed content agrees exactly.
Generator pickles are deliberately excluded from review capsules and never
loaded. All 877 atom identities/43 sites and previous reviews remain preserved.

Definition and coordinate effects remain separate. With recovered definitions
fixed, the fragment phase changes bond deviations at least five **31→32** and
angles **72→72**; its inherited raw C4–O4 distance is **1.401011 Å** against
**1.218 Å**. The 158 chirality proxies have no recorded sign conflicts.
CGY–DX contacts remain **9.357476 / 6.818964 / 4.600879 Å** versus 2.8 Å targets.
Source/native mechanics are demonstrated; raw geometry, pair placement and
scientific qualification remain REVIEW. Different restraint objectives must
not be compared as like-for-like model rankings.

**Cedar 19 fixed-definition geometry trial implementation (2026-10-17):** the separate
trial first reconstructs the captured manager and requires exact identities,
coordinates, site definitions, full proxies/custom requests and native API
sources. It then runs one geometry-only scitbx L-BFGS trial with fixed definitions,
all installed geometry flags enabled and normalization false. Default limits
are **500 iterations / 10,000 calls / 1,200 seconds**; no repeated/adaptive cycles.
Special-position coordinates require a separate constraint policy and stop.
The receipt records symmetry, installed optimizer Python/compiled source hashes,
constraint signatures, per-term energies, gradients, actual stopping log,
accepted-step history and errors. Hitting a limit or a tolerated rounding
error cannot report convergence. Even NATIVE_CRITERION_MET is only the native
numerical criterion, not scientific approval.

Full-precision coordinates/energy and 8.3 PDB round-trip energy are distinct.
Only xyz fields change in a fresh candidate, preserving headers/metadata; report
per-site displacement and rounding. A new native interpretation must preserve
identities, effective definitions, all detailed proxies/counts and custom
requests, and match the exact serialized coordinates. Existing source/charge,
independent stereochemistry, pucker, separate contact/clash inventory, pose and
experimental approval remain open. Prior outputs and ordinary PostMR survive;
no target retuning, dictionary generation, ReadySet retry, diffraction input,
refinement, automatic selection or adoption runs.

**Delivery:** `scripts/build_cif_fixed_geometry_probe.py`, fresh
`19_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`19_Cedar_probe_cif_geometry_trial.py`; fetch from `18_Cedar_probe_build` and use
the one-block pinned Git ferry. The exact returned Cedar 18 ZIP is sufficient;
existing Python and Phenix 2.2.1-6174 suffice with no new installation. Explicit
options: `--review-zip`, `--output-parent`, `--phenix-root`, `--max-iterations`,
`--timeout-seconds` and `--inspect-only`. Completed analysis stays REVIEW/exit 2.
The returned optimization and remaining native round-trip are recorded above.

**Validation:** twelve initial regression failures precede the implementation.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fixed_geometry.py tests/test_cif_fixed_geometry_probe.py tests/test_cif_fragment_restoration.py tests/test_cif_effective_source_recovery.py tests/test_cif_native_validation.py tests/test_synthetic_dna_shuttle.py`
passes **91 tests (6.49 s)**. The same command without file arguments passes
**1,598 tests, two skips and 276 subtests (70.93 s)**.
Standalone worker/driver paths use explicit native fakes. Actual-input inspection
after both build fixtures are deleted verifies **252 source / 254 output payloads**
and 104 runtime files, with poisoned imports unused. This proves transport,
not installed Phenix minimization. Separate schema-1 diagnostics add no new
runtime dependencies or private scientific payloads to Git; existing production
behavior and gate schemas are unchanged.

**Cedar 18 effective/source recovery implementation (2026-10-16):** generic source
selection requires an unsupported effective scaffold, one recorded original
component/input index, an exact source SHA-256/size match in an explicitly
supplied resource inventory, and a supported source DNA graph. Matching uses
content/hashes, not component or filename exceptions. Missing/ambiguous/changed
sources, unsupported source graphs, incomplete shared-code contexts and prior
site modifiers without a composition policy are blocked. The actual plan
selects only DF A:19; eight supported contexts remain unchanged. DF's original
source `27f83c85…`, 8,941 bytes, has **single** sugar bonds. The aromatic
declarations belong to the **effective** dictionary, not that frozen source.

The diagnostic reuses source-preserving whole-component eLBOW generation and
linked preparation. Source atoms/H/bonds/formal charges/stereochemistry and
explicit internal links are checked before native projected-definition,
unaffected-proxy, custom-restraint and modifier-ID gates. The first native
trial holds all Cedar 17 coordinates fixed. Only PASS checks and the separately
reported unavailable formal-charge API allow a diagnostic continuation;
contradictions and all other REVIEW/UNSUPPORTED states stop it. A second phase
restores only the newly supported fragment and validates its identities,
definitions, full proxies and exact coordinates against the fixed recovered
manager. Definition and coordinate effects have separate reports; objectives
with changed targets are not comparable model-quality rankings.

**Delivery:** `scripts/build_cif_effective_source_recovery_probe.py`, fresh
`18_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, and
`18_Cedar_probe_cif_source_recovery.py`; use the one-block ferry from
`17_Cedar_probe_build`. The exact Cedar 17 ZIP supplies prior inputs.
Existing Python/Biopython and Phenix 2.2.1-6174 with eLBOW suffice; no new
installation. Explicit options are `--review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds`, `--source CODE=/explicit/path` and
`--inspect-only`. Captured dispatcher/four API hashes are checked before/after;
the selected eLBOW dispatcher/capabilities are recorded. Successful analysis
remains REVIEW/exit 2. Dictionary generation may optimize its independent
component; model minimization, pairing-pose changes, ReadySet retry, refinement,
production integration and adoption do not run. Return console output and ZIP.

**Validation:** eight initial regressions fail before the new module exists.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_effective_source_recovery.py tests/test_cif_effective_source_recovery_probe.py tests/test_cif_generation.py tests/test_cif_linked_preparation.py tests/test_cif_terminal_qualification.py tests/test_cif_fragment_restoration.py tests/test_synthetic_dna_shuttle.py`
passes **140 tests (19.27 s)**. The same command without file arguments passes
**1,568 tests, two skips and 276 subtests (112.10 s)**. Generic `ZZZ` covers
recorded-hash selection, graph/source/modifier guards, strict continuation,
phase ordering with explicit native fakes and deleted-build transport. Actual
Cedar 17 planning after deletion of both build fixtures verifies **129 input /
133 output payloads**, with poisoned imports unused. Generation and both installed native phases are verified in the returned result above. Existing production behavior,
inventory/gate schemas and originals are unchanged; separate schema-1
diagnostics add no dependencies or private scientific payloads to Git.

**Cedar 17 returned and verified (2026-10-16):** all **129 payloads** verify,
including 75 byte-identical frozen Cedar 16 members. Returned runner SHA
`d611965d…` matches clean NASolve `274f2043…` and NARestraints `a7b6a0c9…`.
Phenix 2.2.1-6174 completes in **5.215362 s**, exit zero; all **14 mechanics
checks pass**, preserving 877 identities/43 sites, 18 dictionaries/11 parameter
files, effective definitions and every detailed proxy/target/weight. Preparation
replays byte for byte. Native/predicted and offline report comparisons agree
except computed-scalar roundoff at most **8.89e-13**; no raw input or target is
normalized. Aggregate REVIEW and prior source/charge limits remain.

Native measurements confirm 34 bond/72 angle nominal deviations at least five,
with zero recorded chirality sign conflicts. Intrasite counts improve
41→24 bonds and 52→22 angles; intersite counts are 9→10 and 55→50. Lower totals
do not establish a pairing-pose repair. Three CGY–DX contacts are 9.357476,
6.818964 and 4.600879 Å versus 2.8 Å targets; they were 8.963664, 2.947120 and
2.736735 Å before the fragment candidate. The latter two worsen despite
restored base integrity. Retain this evidence for a later separate pose/
geometry intervention. DF source/effective recovery comes before optimization
against those changed sugar definitions.

**Cedar 17 separate restoration implementation (2026-10-16):** the returned
stage evidence below reproduces a coordinate-restoration defect. The new
`cif_fragment_restoration` diagnostic keeps the reviewed sugar/phosphate and
transports each complete, graph-selected base fragment from raw Coot into the
preserved C1′/O4′/C2′ frame by a proper rigid rotation. It borrows no canonical
parent base atom by name. The supported graph requires the complete explicit
DNA scaffold, one connected heavy-atom base attached once at C1′, exact
component/element correspondence and unambiguous single-model coordinates.
Unsupported attachments, aromatic sugar bonds, alternate/insertion contexts,
degenerate frames and changed parent/source correspondence are refused.

All nine original parent-controlled contexts are assessed. Eight qualify;
DF A:19 retains UNSUPPORTED because its captured C1′–C2′, C2′–C3′ and C3′–C4′
bonds are aromatic. That entire site stays unchanged. The candidate changes
84 base-atom coordinates, preserving all scaffold/unselected coordinates,
identities, metadata and all 877 model atoms. Raw fragment distances including
the C1′ attachment change by at most **0.001040 Å**, within the explicit
0.002 Å PDB-rounding guard. This is not a chemical acceptance threshold.
Captured-proxy prediction reduces bond deviations at least five **50→34**
and angles **107→72**, with zero recorded chirality sign conflicts. It clears
48 of the 55 previously recorded crossings; remaining raw/sugar/source problems
stay visible. DX C2–O2 becomes 1.340133 Å; its 1.215 Å target is unchanged.
No minimization or full geometry approval is claimed.

**Delivery:** `scripts/build_cif_fragment_restoration_probe.py` builds
`17_Cedar_probe_cif_fragment_restoration.py` from a fresh `17_Cedar_probe_build`
and the existing pinned NARestraints source. Use the one-block ferry from
`16_Cedar_probe_build`. The exact returned Cedar 16 ZIP supplies all frozen
inputs; no read of the original run is needed. `--review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds` and `--inspect-only` remain explicit.
The default native trial uses Phenix 2.2.1-6174, checks the captured dispatcher
and four native API source hashes before/after, and interprets the candidate
with the unchanged 18 dictionaries and 11 parameter files. Every native atom
identity, site definition, custom request and detailed proxy/target/weight
must match the capture; observed coordinates must match the exact candidate.
The captured baseline is not re-executed. Source/charge reviews are preserved.
Successful mechanics still retain REVIEW/exit 2. Return terminal output and
the new review ZIP before selecting a later intervention or adoption.

**Validation:** thirteen initial synthetic regressions fail before the new
module exists. The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_fragment_restoration.py tests/test_cif_fragment_restoration_probe.py tests/test_cif_construction_provenance.py tests/test_cif_construction_probe.py tests/test_synthetic_dna_shuttle.py`
passes **51 tests (7.28 s)**. Synthetic `ZZZ` includes N- and C-linked and
misleading-name bases, rigid reorientation, shared-code site isolation,
aromatic-sugar/multi-attachment/disconnection refusals, source/parent/frame
guards, native success/failure fakes and deleted-build transport. The same
command without file arguments passes **1,543 tests, two skips and 276 subtests
(126.63 s)**. Actual-input relocation after deletion of both build fixtures
verifies all 74 source and 80 output payloads, with poisoned imports unused.
The complete receipt is recorded in the
[evidence record](cif-linked-native-registration-evidence.json).
The installed result is recorded above. Production PostMR,
existing schemas/gates and all original runs remain unchanged; separate
schema-1 diagnostic kinds and no new dependencies/private payloads enter Git.

**Cedar 16 returned and verified (2026-10-16):** all **74 payloads** verify,
including 52 unchanged Cedar 15 members and 19 recorded original artifacts;
the optional normalized model and PostMR report remain absent. Returned runner
SHA-256 `b87ed97f…` matches clean NASolve `4e81f5ca…` and pinned NARestraints
`a7b6a0c9…`. The report replay matches all identities, statuses and counts,
with only 62 computed-scalar differences at most **2.85e-14**. It records 93
findings over 21 sites: first observed at MR input 25, raw Coot 10, restored
55, and not located three. All **55** adjacent crossings are raw→restored,
at eight sites. The later synthetic E:1 control is absent from this original
run and accounts for all three unlocated cases.

Replaying `_restore_shared_parent_coordinates` on the frozen raw model and all
nine saved parent controls reproduces `after_coot_geometry.pdb` **byte for
byte** (70,798 bytes, `d12d171b…`). This establishes the legacy same-name/
same-element coordinate-copy algorithm as the reproducible damaging operation
for these captured transitions. It does not explain every raw/MR outlier or
certify source chemistry. DX C2–O2 was already 1.340398 Å in raw Coot, then
became 5.129713 Å; CGY N1–C2–C1 changed 118.960748°→4.434092°. The original
read-only receipt correctly retains root cause NOT_ESTABLISHED; this subsequent
controlled replay supplies the narrower causal evidence. No original file,
target, native manager, optimization, refinement or production path was changed.

**Cedar 15 returned and verified (2026-10-16):** all **51 payloads** in
`15_Cedar_01pvz5n5_cif_geometry_review.zip` verify. All 47 frozen native members
are byte-identical to Cedar 14. The returned runner SHA-256 matches
`5ce0ce42372e5d6ee774fcd161fc93d39d065f333ef3ae0b30b0ea1b1558495e`,
from clean NASolve `5733bb290dada1edde98a52ddb815d7ad13e823f` and pinned
NARestraints `a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Analysis completes
with deliberate REVIEW, preserving the archive/model and running no new native
interpretation. Offline report replay matches identities, targets, weights,
statuses, ranks and counts. Only computed scalar values show platform roundoff:
722 repeated/report fields differ by at most **7.11e-14**, within the explicitly
checked 1e-10 absolute replay tolerance; no input or gate is normalized.

The returned inventory confirms 1,026 measured bonds (50 nominal absolute
deviations at least five), 1,590 angles (107) and 155 chirality proxies (zero),
with no sign conflicts against the recorded chirality targets. These are
descriptive Cartesian comparisons, not native residuals or full geometry approval.

The largest intrasite deviations expose existing model distortions. Comparison
uses only dictionaries declared by the captured receipt, selected by component
content; their coordinate values are evidence, not replacement targets:

| Measurement | Captured model | Dictionary coordinates | Native target |
| --- | ---: | ---: | ---: |
| DX D:3 C2–O2 distance (Å) | 5.129713 | 1.215504 | 1.215 |
| DX D:3 C7–C8 distance (Å) | 2.881660 | 1.368845 | 1.369 |
| CGY A:20 N1–C2–C1 angle (°) | 4.434092 | 123.779864 | 123.78 |

Identity-matched lineage comparison proves all **858** Cedar 05 model atoms
survive in the later 877-atom shared-context control with **zero coordinate
displacement**. Thus these distortions predate the linked/terminal dictionary
diagnostics. This does not identify the responsible construction step or prove
the complete source chemistry. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the exact return hashes, replay and source/coordinate comparison details.

**Next bounded work:** trace original Coot construction, canonical-parent
restoration and atom correspondence using frozen before/after models and
mutation receipts. Select suspect sites by measured graph/geometry evidence;
do not build a component-name exception list or retune dictionary targets to
fit these coordinates. Source-versus-model agreement narrows the investigation
but does not establish a mutation or restoration bug by itself. Root cause
remains NOT_ESTABLISHED. Cedar 16 above now collects that missing stage evidence;
coordinate repair, minimization, full native geometry/refinement and adoption
remain separate gates. The Cedar 15 return changed documentation/evidence
only; later runtime validation is recorded in the current delivery above.

**Cedar 15 captured geometry implementation (2026-10-16):** the user requested
the next script. This bounded diagnostic reads the exact verified Cedar 14 ZIP,
checks all 141 payloads, and materializes only the captured candidate's 47
anchored native members. It measures simple-bond distances, angles and ordered
chirality volumes from recorded Cartesian manager sites. It preserves all
coordinates, dictionaries and prior qualification outcomes, and runs no new
Phenix interpretation, ReadySet, optimization or refinement.

The reusable `cif_captured_geometry.review_captured_geometry` API validates
atom/index/label/coordinate correspondence and proxy detail counts. It retains
all measured, unsupported, zero-weight and degenerate rows. The signed nominal
deviation is `(observed - target) * sqrt(recorded weight)`; recorded `both_signs`
uses absolute ordered volume. This is a descriptive ranking, **not a native
residual or acceptance gate**: the capture lacks some symmetry/slack/top-out
conventions. Nonidentity bond symmetry is unsupported. Angle/chirality values
describe the recorded Cartesian endpoints without inferred symmetry transforms.
Dihedrals, planes, parallelities, ASU bonds, pucker, absolute stereochemistry
and complete geometry qualification remain explicitly unassessed. No source
defect, target change or chemical approval is inferred from a large score.

Actual-input replay measures **1,026 bonds, 1,590 angles and 155 chirality
proxies**. Nominal absolute deviations at least five occur at 50 bonds and 107
angles; none occurs among chirality proxies, and no recorded chirality sign
conflicts are observed. These describe the existing unoptimized model. Existing
source reviews and nine unavailable formal-charge readbacks stay open.

**Completed delivery:** `15_Cedar_probe_cif_geometry_review.py` was built with
`scripts/build_cif_geometry_review_probe.py`, the new pinned
`15_Cedar_probe_build` and existing `05_Cedar_narestraints_build`. Use the
one-block `fetch && worktree && build && run` ferry from the preserved
`14_Cedar_probe_build`. The default input is the returned Cedar 14 path;
`--review-zip` and `--output-parent` remain explicit overrides. The runner uses
Python's standard library and needs no new installation or Phenix argument.
It writes `captured_geometry_review.json`, a short `summary.txt`, provenance,
frozen evidence and a new review ZIP. Successful analysis deliberately returns
**REVIEW/exit 2**; return that output/capsule for review. Full scientific
qualification and a later geometry intervention remain separate decisions.

**Validation:** all 13 scalar regressions fail before the module exists, then
pass. The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_captured_geometry.py tests/test_cif_geometry_review_probe.py tests/test_synthetic_dna_shuttle.py`
passes **30 tests (3.94 s)**. The same command without file arguments passes
**1,501 tests, two skips and 276 subtests (111.78 s)**. Synthetic `ZZZ` fixtures
cover rigid motions, reflected/unsigned chirality, zero/missing/negative
weights, inconsistent captures, deferred categories, capsule tampering and
deleted-build/poisoned-import transport. A separate actual-input relocation
also completes after both source-build fixtures are deleted; all **51** output
payloads verify and the Cedar 14 ZIP is unchanged. The user return above also
verifies the same complete captured-evidence analysis. This is captured-evidence
analysis, not new installed-tool execution. Schema 1 gains only a new diagnostic
report/receipt; existing inventory, qualification and production formats/gates
are unchanged. No private scientific payloads enter Git. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the methods, exact input hash and software/transport receipts.

**Cedar 14 returned and verified (2026-10-16):** all **141 payloads** in
`14_Cedar_7qm2tnry_cif_outgoing_bundle_review.zip` verify, including every
anchored native input/output and all 35 unchanged Cedar 12 materialized members.
The runner hash matches `487d8aa2…` from clean NASolve
`56d4dae912e36dd7cfe8d905a68e1d09412546a2` and pinned NARestraints
`a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Both installed Phenix
**2.2.1-6174** interpretations completed, exit 0 (5.903950 s / 1.358828 s).
Qualification records **138 PASS and nine UNSUPPORTED formal-charge checks**;
no individual check remains REVIEW, but the aggregate remains **REVIEW**.
Offline replay reproduces all 147 outcomes and evidence after sorting only
unavailable-charge items by atom ID. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the exact archive, receipt and qualification hashes.

All four curated outgoing-O3′-H findings clear, and all **38** outgoing-H
audits pass. The native modifier IDs are exactly prior `NASnoOP3` plus the
selected new ID; all six projected-definition categories, including atom types,
match.
Captured-baseline replay, all unselected definitions, every recorded unaffected
proxy, reviewed 5CM torsion/alternate, 38 links and custom 21/34/8/23 coverage
pass. The same 877 coordinate atoms and 43 sites are preserved. Both managers
contain 1,026 simple bonds, 1,590 angles, 155 chirality proxies, 387 constant
dihedrals, 571 dihedrals, 58 parallelities and 54 planes. Equal totals alone
are not the proof: full recorded rows are compared by the qualification gates.
The candidate appends four dictionaries and four parameter files to the
unchanged 14-dictionary/seven-parameter baseline.

**Generality:** the preparation rule uses explicit links, the H/D bond graph
and captured canonical type authority; it has no four-component or hydrogen-name
allowlist. Existing regressions use synthetic `ZZZ`, misleading H names and D,
same-code outgoing/free-end contexts, retained OP2 H and terminal phosphate.
They also reject missing contexts, changed authorities/inputs and coordinate-H
deletion; qualification guards exact modifier IDs and retained numerical rows.
This establishes reusable behavior within the declared OH1 O3′–C3′/H motif.
The Cedar probe remains hash-bound to its reviewed experiment. Other chemistry,
the source-specific 5CM correction and production integration keep their own
authority and qualification requirements; arbitrary-component support is not
established by this result.

**Next bounded work:** review the remaining source/numerical/stereochemical
evidence and define geometry qualification from this validated bundle, preserving
the original coordinates and manager. The nine charge readbacks are unavailable
in this API, with no contradictory values or partial-charge substitution;
repeating the unchanged inventory does not resolve them. The added terminal H
formal charge remains unassessed, and 1AP/DP Doctor source assessments remain
REVIEW. Achieved geometry, experimental protonation, refinement, human review
and production adoption remain separate gates. Cedar 15 above now implements
the next descriptive evidence slice; no model editing, optimization, ReadySet retry, refinement
or adoption occurred. Runtime and schemas are unchanged. The existing Cedar 14
software suite below remains the latest code validation; this documentation-only
change adds capsule/replay, JSON, link and figure verification.

**Cedar 13 return and Cedar 14 launcher correction (2026-10-16):** all 58
payloads in `13_Cedar_4o9_vhuk_cif_outgoing_bundle_review.zip` verify, including
35 unchanged frozen members and 24 passing source/native projection checks.
The user runner hash matches `68a2b9ae…` from clean NASolve
`5295992209fc1435b260bc926c89d54208fd7a83` and the same pinned NARestraints.
All four candidates completed preparation. The runner then passed an empty
default `--phenix-root` to `installation_from_candidate`, reproducing the
returned `NoneType` path error. No new native interpretation was reached;
the REVIEW capsule is not a native chemistry verdict.

The corrected template defaults to
`$HOME/Applications/phenix-2.2.1-6174`, matching Cedar 12's working selection,
and retains `--phenix-root` for explicit relocation. Only launcher selection
changes; the four candidates and all authority/qualification gates are unchanged.
The new regression keeps the actual installation loader and executable/version
discovery, with explicit external-program shell fixtures. It fails before the
fix for the omitted option while the explicit path already passes (one failed,
one passed, 12 deselected), then both pass after the fix.

**Completed delivery:** `14_Cedar_probe_build` at
`56d4dae912e36dd7cfe8d905a68e1d09412546a2` built
`14_Cedar_probe_cif_outgoing_bundle.py` with `--delivery-prefix 14_Cedar`.
The user ran the one-block conditional Git ferry with explicit `--phenix-root`.
Input remains the preserved Cedar 12 ZIP; retain all builds, runners and capsules.
The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short tests/test_cif_outgoing_bundle_probe.py tests/test_phenix_runtime.py tests/test_synthetic_dna_shuttle.py`
passes **27 tests (18.67 s)**. The same command without test-file arguments
passes **1,480 tests, two skips and 276 subtests (118.05 s)**. A Cedar 14
actual-input inspect-only run succeeds after both original build trees are
deleted, with poisoned imports unused; all 58 payloads verify and the original
Cedar 12 ZIP is preserved. This is preparation/transport evidence, not installed
Phenix execution. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
the full-suite and retry receipts. Installed Cedar 14 execution is verified
above; no optimization/refinement or adoption occurred.

**Cedar 13 outgoing candidate implementation (2026-10-16):** the user authorized the
next source review and validation delivery. All 24 complete curated-to-native
projection checks pass on the exact Cedar 12 inputs. The bounded candidates
remove only graph-identified O3′ H at 1AP A:5 (`HO31`), 5CM A:7 (`HO3'`),
DZ A:12 (`H2`) and DP B:4 (`H3`). Their projected dictionary atom counts are
34, 33, 33 and 33. The O3′ OC2 authority is captured canonical DC A:4, with
only C3′ adjacency; its partial charge and numerical targets are not copied.
Existing `NASnoOP3` and all other modifiers remain; four new per-site modifier
IDs compose with them. Source dictionaries, parameters and coordinates stay
unchanged. True free 3′ ends and retained OP2 H are protected generically by
explicit context and graph, including H/D with misleading names.

`prepare_outgoing_component` is a separate diagnostic layer for captured
curated inputs, not a whole-component generation pass or production repair.
It verifies every anchored native input/output and exact source projection,
refuses coordinate-H deletion and changed/unsupported authorities, and records
before/after Doctor assessments. Existing 1AP and DP assessments remain REVIEW;
5CM and DZ assessments pass. No replacement targets or charge values are guessed.

The new native probe replays Cedar 12 unchanged, then interprets the selected
bundle. Qualification retains all existing gates and adds full captured-baseline
replay plus exact old/new modifier IDs at every site. It checks all 38 declared
outgoing endpoints, all four projected numerical definitions, the corrected
5CM torsion/alternate proxy and all unselected definitions and unaffected
proxies, including the earlier IGU terminal/internal contexts. The dispatcher,
four captured native API sources and prior terminal authorities must match
before and after. Every materialized input is rechecked, and the original ZIP
is preserved. Formal-charge readback remains unsupported in the captured API;
adding the three newly checked curated sites can increase those findings.
Successful interpretation may therefore still end at REVIEW/exit 2.

**Original delivery:** `scripts/build_cif_outgoing_bundle_probe.py`, new
`13_Cedar_probe_build`, existing `05_Cedar_narestraints_build`, output
`13_Cedar_probe_cif_outgoing_bundle.py`. Supply the exact published full-SHA
Git ferry in one `&&` subshell. The default input is the returned
`12_Cedar_q46plqwk_cif_terminal_bundle_review.zip`; `--review-zip`,
`--output-parent`, `--phenix-root`, `--timeout-seconds` and `--inspect-only`
remain explicit overrides. Preserve the frozen everyday checkout and all
earlier deliveries. Cedar 13's installed selection stopped as recorded above;
Cedar 14 carries the launcher correction. Local native checks use explicit
fake APIs or offline returned inputs.
No ReadySet retry, optimization, refinement or adoption is part of this trial.

**Validation:** six selected graph/H-D regressions fail before the new module
exists (11 deselected). The focused command
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
with `tests/test_cif_outgoing_preparation.py tests/test_cif_outgoing_qualification.py
tests/test_cif_outgoing_bundle_probe.py tests/test_cif_terminal_preparation.py
tests/test_cif_terminal_qualification.py tests/test_cif_terminal_bundle_probe.py
tests/test_cif_native_validation.py tests/test_cif_linked_preparation.py
tests/test_cif_linked_qualification.py tests/test_synthetic_dna_shuttle.py`
passes **138 tests (16.44 s)**. The same command without test-file arguments
passes **1,478 tests, two skips and 276 subtests (124.12 s)**. A successful
actual-input `--inspect-only` trial also runs from a relocated runner after
both original build trees are deleted, with poisoned imports unused. All 58
review payloads verify, and the original Cedar 12 ZIP is unchanged. This is
preparation/transport evidence, not installed Phenix execution. The
[native evidence record](cif-linked-native-registration-evidence.json) owns the
complete software/transport receipts. Schema 1 gains a new diagnostic
preparation receipt and qualification policy; existing receipt formats,
generation gates and production behavior are unchanged. No new runtime
dependencies or private native payloads are added to Git.

**Cedar 12 returned and verified (2026-10-16):** all **116 payloads** in
`12_Cedar_q46plqwk_cif_terminal_bundle_review.zip` verify. The runner SHA-256
matches delivery `2144968031c659f69c4d71eb81f1aeb8ef7d79962c45e03daa4bfe2460352845`,
from clean NASolve `e5b1be6198eae73fedbc497d003502bfb31c2247` and NARestraints
`a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Baseline and candidate native
interpretations completed under Phenix **2.2.1-6174**, both exit 0
(5.651856 s / 1.256861 s). Qualification is **95 PASS, six UNSUPPORTED
formal-charge checks and four REVIEW outgoing-O3′-H checks**; aggregate
**REVIEW**, not complete scientific approval. Offline qualification replay
reproduces all 105 outcomes and evidence after sorting only unavailable-charge
items by atom ID. The [native evidence record](cif-linked-native-registration-evidence.json)
owns the exact hashes, checks and preservation evidence.

The source-bundled probe reuses the
exact Cedar 09 shared-code control and Cedar 11 installed numerical authority.
It verifies all 207/nine payloads, materializes only declared members and
preserves both original ZIPs. `prepare_terminal_component` wraps the existing
linked preparation; only free-OH contexts receive captured native O5′/H atom
operations, bond and angle. Actual-input offline replay produces E:1 with
32 dictionary atoms and leaves the 34-atom A:6 internal plan and shared base
byte-identical. All retained formal charges stay unchanged; the new H formal
charge is `?`, never copied from its native partial charge. No H coordinates
or new numerical targets are invented.

The selected candidate also explicitly reproduces reviewed 5CM output
`61bf14a1…`. Its native projection removes only the declared OP3. Baseline and
candidate use the same 877-atom/43-site coordinate control; no optimization.
New detailed schema-1 fields record neutron bond targets and torsion alternates.
Qualification retains all existing gates and adds exact projected numerical
rows, the corrected 5CM `C2e-nyu0` quartet/340.7°/6.3°/period-1/2.8° alternate
proxy, unchanged unselected definitions and every recorded unaffected native
proxy. The selected Phenix dispatcher, modules and numerical source hashes
must match the Cedar 11 authority before and after execution. Relocation uses
the declared installation anchor, not basename search.

**Read-only review class:** every declared outgoing O3′ endpoint is audited
by element and adjacency. Cedar 12 confirms the prior Cedar 09 findings:
1AP A:5→A:6 `HO31`, 5CM A:7→A:8 `HO3'`, DZ A:12→A:13 `H2` and DP B:4→B:5
`H3`, all on O3′ with OH1 typing. These pre-existing curated reviews are not
silently fixed or hidden by the two selected candidate changes. Native charge
readback and new-H formal charge remain unqualified; `REVIEW`/exit 2 is
retained while these gates remain unresolved, despite successful interpretation.

**Delivery:** `scripts/build_cif_terminal_bundle_probe.py`, pinned
`12_Cedar_probe_build`, same `05_Cedar_narestraints_build`, output
`12_Cedar_probe_cif_terminal_bundle.py`. Use one subshell containing fetch,
pinned detached worktree, build and run joined by `&&`. Explicit archive,
installation, timeout and inspect-only overrides remain available. Preserve
the frozen everyday checkout and all old scripts/worktrees/native sessions.
The returned one-block Git ferry also worked from an unrelated working
directory. No ReadySet retry, model optimization, refinement, adoption or
production PostMR change occurred.

**Follow-up from that return:** source review and explicit preparation of the
four internal O3′-H contexts were implemented in Cedar 13 and pass installed
Cedar 14 validation above. Native formal-charge readback and the earlier added H formal
charge remain open evidence limits; repeating an unchanged inventory does not
resolve them. Geometry/refinement and human review remain separate later gates.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,437 tests, two skips and 276 subtests (92.78 s)**. The same command
with `tests/test_cif_terminal_preparation.py tests/test_cif_terminal_qualification.py
tests/test_cif_terminal_bundle_probe.py tests/test_cif_native_validation.py
tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_synthetic_dna_shuttle.py` passes **97 tests (6.84 s)**. Nine selected
regressions fail before the new implementation/readback fields exist. New
native tests use explicit fake APIs; transport survives deleted build trees
and poisoned imports. Actual returned-input offline preparation/replay and
prior-native outgoing-H audit are distinct from the completed installed
Cedar 12 execution above. This follow-up changes documentation/evidence only;
JSON, link and figure checks apply, with no runtime/schema migration or new
dependencies. Native payloads stay outside Git; qualification gates are unchanged.

Documentation follow-up verification: all 16 documentation JSON files parse,
116 local links in changed Markdown resolve, and `git diff --check` is clean.
`python docs/figures/build_cif_doctor_overview.py` reproduces the SVG;
its 1200×1190 render is byte-identical to the preceding visual QA image.

**Cedar 11 returned; terminal numerical sources complete (2026-10-15):** all
**nine** payloads in `11_Cedar_ggtpccwv_cif_terminal_review.zip` verify, including
anchored native outputs, repeated receipt content and the exact published
worker/build. The user's runner hash is `9aa0afa3…`, from clean source
`e6ec5d66e283a138c0ac8e9585146e5c994ac243` and the same pinned NARestraints.
The explicit 5CM preparation again reproduces `61bf14a1…` with source/original
09 ZIP preserved. Phenix **2.2.1-6174** resource execution completes at exit
zero in **0.837208 s**; status is `PREPARATION_AND_RESOURCES_REVIEW`.

Native resolution records DG → metadata `Gd`. The unchanged canonical base
has 33 atoms; effective `5*END` has 31: P/OP1/OP2 removed, O5′ changed from
OC2 to OH1, HO5′ added with HOH1 type and the exact installed bond/angle
targets. All unaffected bond/angle/torsion/chirality/plane rows remain equal,
with no dangling references. Both installed sources remain unchanged and
the modification rows exactly match Cedar 10. The compact registration evidence
owns all hashes, counts, exact targets and source/module provenance.

**Scientific interpretation:** both canonical states retain DNA group, but
the effective canonical 5′-OH classification is also `undetermined`. That label
alone cannot distinguish the earlier synthetic modified end from the canonical
control. It does not erase the earlier missing O5′ hydrogen/OH typing, and
no qualification gate changes. Both canonical states lack native formal-charge
readback; recorded partial charges remain distinct. Native metadata atom
counts are retained as returned, not rewritten to imply qualification.

**Next work:** implement an explicit source-traceable modified-terminal
adaptation and validate the revised bundle, including the separate prepared
5CM candidate, before a new bounded geometry trial. No further unchanged source
inventory is needed. No new delivery is queued by this evidence-only update;
no model edits, optimization, ReadySet retry, refinement or adoption ran.
Runtime/schema and dependency behavior are unchanged; the 1,406-test software
receipt below still applies, separately from this actual native return.

**Cedar 10 returned; Cedar 11 canonical lookup retry (2026-10-15):** all
**nine** payloads in `10_Cedar__7ap0ddc_cif_terminal_review.zip` verify. Its
clean NASolve source is `f681b9bd5355905fbee0797302d5984cc40e5d6a`, with the same
clean pinned NARestraints. The runner prepared the exact reviewed 5CM
derivative (`61bf14a1…`) with unchanged source/archive, then used installed
Phenix **2.2.1-6174** to capture the `5*END` fields and source hashes. The resource
worker returned UNSUPPORTED at **Missing canonical monomer: DG** after
**3.726048 s**; the aggregate probe is `NATIVE_RESOURCES_REVIEW`. No canonical
control, terminal adaptation, native 5CM qualification or refinement ran.

The v1 worker incorrectly used direct library lookup for a PDB residue name.
Primary cctbx `server.py` delegates name translation to the installed
`get_comp_comp_id_and_atom_name_interpretation` method; `iotbx.pdb` translates
explicit DG to library GD (and DA/DC/DT to AD/CD/TD). Policy
**`cif-installed-terminal-resources-v2`** now uses that native API with an empty
atom-name list, retaining no coordinate model or local alias table. Additive
schema-1 control evidence records the method, empty input atom list,
interpreted residue name and resolved component ID; provenance also hashes
`iotbx.pdb`. Missing native resolution APIs/components remain unsupported and
retain the already captured modification evidence. All numeric targets,
formal-charge boundaries and existing qualification gates are unchanged.

**Validation:** the new fixture reproduces the untranslated-name failure:
**five failures / seven passes** before the fix. Focused validation is
**55 passed (4.37 s)** using the five terminal/resource/repair/linked/shuttle
test files in the Cedar 10 command below. The full command below passes
**1,406 tests, two skips and 276 subtests (64.49 s)**. These are explicit fake
native API and transport checks, including all four canonical DNA names,
unsupported resolution, preservation and relocation. Corrected installed
canonical-control execution remains pending. The registration evidence owns
the exact returned hashes, source rows' provenance and primary-code references.

**Next delivery:** build the existing terminal probe with explicit
`--delivery-prefix 11_Cedar` and output
`11_Cedar_probe_cif_terminal_review.py`, from pinned `11_Cedar_probe_build` and
the same `05_Cedar_narestraints_build`. It still reads the exact original
Cedar 09 ZIP; no replacement ZIP or new dependency is required. The user
requests one pasteable conditional command block: fetch, add pinned detached
worktree, build, run, joined by `&&` inside a subshell. Stop after any nonzero
status. Preserve the everyday checkout, all old build trees and every native
session. Inspect the returned control before implementing terminal adaptation
or proceeding to a separate bounded geometry trial. No native outputs are
committed; this change includes source/tests/docs and compact evidence only.

**Cedar 10 terminal-source review ready (2026-10-15):** the user requested a
few executable steps and clarified whether the whole run had completed. Only
the native linkage diagnostic has completed; no complete refinement run is
claimed. The next delivery advances the two known dictionary reviews without
rerunning the same linked inventory for an unavailable charge attribute.

`scripts/build_cif_terminal_probe.py` packages
`10_Cedar_probe_cif_terminal_review.py` from pinned source and the same
`05_Cedar_narestraints_build`. It accepts the exact hash-bound returned Cedar
09 capsule, verifies all **207** payloads and snapshots only its explicitly
declared frozen 5CM source. The existing `5cm-reviewed-torsion-v1` recipe
prepares a separate candidate: source `38378c7d…`, output **`61bf14a1…`**.
No selected bundle or old native input is replaced. The actual returned 09
source reproduces the complete reviewed candidate hash in inspect-only replay;
its implemented assessment passes, with native bundle and geometry validation
still NOT_RUN for this preparation.

The new reusable `cif_terminal_resources.inspect_terminal_resources` API
reads explicit native modification IDs (default `5*END`) and applies them only
to an in-memory canonical library control (default DG). It records all native
row fields in atom/bond/angle/torsion/chirality/plane categories, numerical
values, source/module hashes, charge readback and base preservation. No target,
energy type, hydrogen name or formal charge is invented for IGU. This captures
the installed numerical authority needed to complete the terminal treatment;
it is **not** implementation or qualification of that new recipe. Native
source/control errors, unsupported APIs and owned-process timeout remain
explicit. The selected Phenix environment is isolated as in earlier probes.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,400 tests, two skips and 276 subtests (63.87 s)**. The same command
with `tests/test_cif_terminal_resources.py tests/test_cif_terminal_probe.py
tests/test_cif_doctor_repair.py tests/test_cif_linked_probe.py
tests/test_synthetic_dna_shuttle.py` passes **49 tests (3.64 s)**. New native
tests use explicit fake APIs, including exact target retention, unknown charge,
missing resource and owned timeout. The resource tests fail before the new
module exists and pass afterward. Transport tests delete original build paths,
poison imports and preserve both successful/unsupported review capsules.
Real-09 inspect-only replay verifies exact source/output hashes and preserved
original ZIP; installed resource execution remains **PENDING**. No new
dependencies, production PostMR changes or old qualification-gate changes.

**User delivery:** a pinned `10_Cedar_probe_build`, then the source-bundled
builder/run sequence. The user now explicitly permits a few sequential
commands together. Preserve the frozen everyday NASolve checkout, existing
05–09 trees/runners and every native session. Inspect the new review ZIP before
implementing the terminal recipe or entering a separate bounded geometry trial.
No model interpretation, model optimization, ReadySet retry, diffraction
refinement or adoption is part of Cedar 10. Only code/tests/docs and compact
evidence enter Git; actual source dictionaries/native outputs remain outside it.

**Cedar 09 returned; native metadata recovered (2026-10-15):** all **207**
payloads in `09_Cedar_nn9cyghr_cif_linked_review.zip` verify. Source is clean
NASolve `4f1cde11b540c24adc27c97cb5f891f6710bf17e` with the same pinned clean
NARestraints source. Phenix **2.2.1-6174** completes baseline/linked/control at
exit zero in **2.924922 / 1.354201 / 1.272176 s**. All four linked sites now
have native group and classification **DNA**. Qualification records **29 PASS,
four UNSUPPORTED**: every noncharge check passes, while the installed atom API
has no formal-charge attribute. There is no known-charge contradiction. Keep
the aggregate **REVIEW** and raw charge evidence; do not substitute partial
charges, source values or zero, weaken the gate, or repeat an unchanged native
inventory to seek an attribute absent from this installation.

The linked manager retains 858 atoms, 42 mappings, all **38** declared links,
custom **21 bonds / 34 angles / 8 planes / 23 parallelities**, all 58 native
parallelities and unaffected definitions. The 877-atom/43-residue control has
**10 PASS / two charge UNSUPPORTED**; original atoms, all 42 definitions and
38 links are unchanged. Its E:1 group is DNA but classification is
**undetermined**. The projected E:1 O5′ remains type **O2**, bonded only to C5′
with no explicit O5′ H. This proves selected atom/context isolation under one
code, not complete free-OH end parameterization or general terminal support.
Do not infer that the original four internal sites failed classification.

Read-only arithmetic replay compares **148/148** source/candidate formal charges
with no difference or unavailable source value. All **12** generated ordered
sugar-centre signs match source ideal coordinates; native proxy signs and the
initial model agree under each actual proxy order. The determinant convention
is checked against the primary cctbx chirality implementation. This is
source-coordinate/sign consistency, not independent CIP/R-S assignment or
experimental validation, and it does not satisfy the native charge gate.
Projected plane-angle reviews remain **IGU five / IMC two / CGY five / DX zero**;
their material-strain threshold is uncalibrated. The selected 5CM A:7 still
contains `C4′–O4′–C1′–C2` (`C2e-nyu0`, 340.7 ± 6.3°, period 1). Preserve that
known C2/C2′ defect until an explicit, hash-scoped preparation is reviewed;
do not silently substitute the historical repaired derivative.

The [registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns exact archive/source/API hashes, native counts and these review limits.
**Next work is dictionary chemistry/geometry review:** complete the declared
free-OH terminal treatment through a traceable numerical source, use explicit
reviewed 5CM preparation where its exact source hash permits it, and preserve
charge/protonation and generated metadata reviews before a new bounded geometry
trial. The subsequent Cedar 10 source-resource delivery is described above;
it does not repeat this linked inventory. No ReadySet retry,
minimization, refinement, adoption or gate change occurred. These updates are
documentation/evidence only; the runtime's existing 1,386-test receipt below
and its returned installed execution remain the validation. Original private
payloads and the frozen everyday checkout remain outside Git and unchanged.

**Cedar 08 returned; Cedar 09 component-list retry (2026-10-14):** all 207
payloads in `08_Cedar_g4gzbeeb_cif_linked_review.zip` verify. The runner matches
the expected SHA-256 and clean NASolve `147c1fbaabb41f73f5680852625189b0e1295ca7`,
with the same clean NARestraints `a7b6a0c93365f7a480b7eee9cc4e860b13f702de`.
Phenix **2.2.1-6174** completed baseline, linked and synthetic shared-code
interpretation at exit zero (**2.522322, 1.381361 and 1.412638 s**). Native
modifier registration now matches every requested ID. All four expected atom
sets, H adjacency and energy types agree; no dangling references remain.
All **38 links**, custom **21 bonds / 34 angles / 8 planes / 23 parallelities**,
all 58 native parallelities, unaffected definitions and the original 858 atoms
are preserved. Internal IGU A:6 and free-OH IGU E:1 have distinct selected
definitions in the 877-atom/43-residue control; the original 42 definitions
and 38 links remain unchanged. The control's added residue is synthetic.

The returned status is still **REVIEW**, with two precise limitations:
the native formal-charge attributes are absent, and the declared `_chem_comp`
DNA group was not read. Our singleton `comp_list` writer collapsed its metadata
to scalar fields; native `convert_list_block` only iterates the category loop.
Both loaded base and effective group are null. Native logs nevertheless classify
all 42 residues as DNA: group metadata and interpreted classification are
distinct, and the old worker did not record the latter per site. The old
`effective-site-atoms` check combined matching atoms with the missing group;
there is no observed atom-inventory mismatch.

The writer now retains one-row list metadata as a loop, using the existing CIF
quoting implementation. It adds `component_list_policy =
cif-native-component-list-loop-v1`; detailed native metadata records
classification separately. Qualification reports exact atoms and required DNA
group independently, preserving both gates. Exact returned-input replay keeps
every parsed base/projected dictionary, site plan, modifier and PHIL request
unchanged; only list serialization changes. The
[registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns native hashes/counts, the group blocker, source preservation and replay.
Missing formal charge is still `UNSUPPORTED`; no partial/source/zero substitute
is introduced, and a subsequent REVIEW can persist after the group is corrected.

**Next action:** deliver the clean published source through a pinned detached
`09_Cedar_probe_build`, build `09_Cedar_probe_cif_linked.py` using
`scripts/build_cif_linked_probe.py --delivery-prefix 09_Cedar` and the existing
`05_Cedar_narestraints_build`, then run it against the original checksum-bound
05 capsule. Issue one terminal command at a time. Preserve the frozen everyday
checkout, all 05–08 build trees/runners, native sessions and source models.
Installed list metadata, complete qualification, numerical/stereochemical
review and ordinary fresh full-auto recovery remain open. No ReadySet retry,
model optimization, diffraction refinement or adoption is authorized by this
diagnostic result. Generated private CIFs/coordinates/native receipts stay
outside Git; only code/tests/docs and compact evidence are committed.

**Cedar 09 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,386 tests, two skips and 276 subtests (89.41 s)**. The same command
with `tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_cif_linked_probe.py tests/test_cif_native_validation.py` passes
**70 focused tests (4.75 s)**. Four targeted cases fail before the change and
pass after it. Explicit fake native controls reproduce skipped scalar metadata
and retained loop metadata; quoting/multiline values round-trip unchanged.
Exact real-return replay checks every base/projection value and preserved
modifier/PHIL/input bytes. Classification readback is additive to detailed
inventories; basic defaults and schema-1 compatibility remain unchanged.
No new dependencies are added. The editable figure is regenerated/rendered and
visually inspected. These software/replay checks are not installed Phenix
execution of the new metadata layout; that remains the Cedar 09 action.

**Cedar 07 returned; Cedar 08 registration retry (2026-10-14):** all 164
payloads in `07_Cedar_okkb2are_cif_linked_review.zip` verify. Source-retaining
IMC/CGY/DX generation reached `CANDIDATE_REVIEW`; IGU was reused. Detailed
baseline interpretation completed at exit zero (2.896598 s), with 858 atoms,
42 mappings and 38 backbone links. Linked interpretation failed at exit two
(1.082309 s): `Missing CIF modification: data_mod_NASL9809b6bd9c`.
The four modifier files registered `linked_sites`, overwriting that key, rather
than the distinct requested IDs. The
[registration record](cif-linked-native-registration-evidence.json) owns exact
archive/build/reader hashes, failure and replay. No linked qualification or
shared-code control completed; no coordinates or frozen inputs changed.

The writer now emits one native `data_mod_<ID>` block for each requested
modifier, with identical operations and PHIL IDs. Schema-1 preparation adds
`modification_block_policy = cif-native-modification-blocks-v1`. Replaying all
four actual returned candidates preserves each site plan, base dictionary and
PHIL file byte-for-byte while registering four distinct IDs. Reader-contract
tests reproduce the old missing-ID failure and cover multiple same-code end
contexts and cross-component collisions. These tests use explicit fake APIs;
they are not installed Phenix evidence.

The baseline native atom records also have no formal-charge values. New
detailed worker metadata distinguishes missing attributes from null readback;
site qualification records unavailable values as `UNSUPPORTED` separately from
actual charge contradictions (`REVIEW`). Never substitute partial charges or
zero. Source charge preservation remains separate evidence. Other mechanics
checks continue, but missing native charge readback cannot silently qualify.
The native console now prints the failed layer and its recorded error.

**Next:** Git-build and run
`08_Cedar_probe_cif_linked.py` with `--delivery-prefix 08_Cedar`, using the same
pinned NARestraints source. Keep the everyday laptop checkout, Cedar 07 runner,
all native sessions and original model/source inputs intact. The runner remains
an external diagnostic with no ReadySet retry, refinement or adoption. Native
registration, full linked mechanics, the shared-code control, numerical and
generated stereochemical review, and fresh full-auto recovery remain open.
Only code/tests/docs and compact hash/count evidence enter Git.

**Cedar 08 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,380 tests, two skips and 276 subtests (98.88 s)**. Focused
preparation/qualification/shuttle/native-worker checks pass **64 tests (5.38 s)**.
Two registry regressions fail with the old shared block and pass with distinct
blocks. The fake-reader boundary also reproduces the missing-ID failure with
legacy packaging and accepts the exact requested IDs with corrected packaging.
Native charge controls distinguish missing/nonfinite readback from actual
contradictions and retain the partial/formal-charge separation. Exact real
candidate replay checks unchanged base/PHIL/site plans and input preservation.
Existing shuttle relocation tests retire original build paths and poison imports.
The editable figure was regenerated, rendered and visually inspected. New
schema-1 fields are preparation layout provenance and detailed native charge
readback metadata; formal-charge check rows retain explicit unavailable and
contradictory observations. No new dependencies or installed native execution
were added to this validation. Generated coordinates/CIFs/native payloads stay
outside Git. The subsequent installed Cedar 08 result is recorded above.

**Cedar 06 returned; Cedar 07 representation retry (2026-10-14):** all 87
payloads in `06_Cedar_rkmjesl4_cif_linked_review.zip` verify. Native eLBOW
completed source-retaining IMC/CGY/DX generation on Phenix 2.2.1-6174
(RM1/GDIIS); IMC and DX reached `CANDIDATE_REVIEW`. CGY alone was rejected for
six alternating single/double ring orders becoming aromatic types. Every source
ring bond already declares aromaticity; connectivity, hydrogen attachments and
explicit formal charges survived. No new native bundle interpretation ran.
The [source-recovery record](cif-linked-source-recovery-evidence.json) owns
exact archive/source/candidate hashes, commands and offline replay.

Generation-v4 now recognizes only complete isolated source-declared aromatic
six-member alternating neutral C/N rings, with unchanged single bridges and
non-stereogenic ring bonds. Schema-1 inspection adds `bond_representation`;
raw comparison differences, numerical reviews and independent atom/H/charge/
stereo checks remain intact. Native diagnostics retain v3 receipt compatibility
and re-inspect supported v3/v4 candidates. Source-recovery console output names
blocked components and reasons. Offline reanalysis prepares all four returned
candidates with their OP2 H retained and the original model hash unchanged.

**Delivery history:** `07_Cedar_probe_cif_linked.py` was built from the checked Cedar revision with
`scripts/build_cif_linked_probe.py --delivery-prefix 07_Cedar`, using the pinned
NARestraints build source. Use delivery build worktrees and write the runner
into the everyday NASolve directory: macOS refused Python access to Downloads
before the Cedar 06 script could run. Preserve the frozen everyday checkout,
old deliveries and native sessions. These worktrees isolate pinned delivery
sources on the single Cedar development line; audit and retire them after the
linked qualification gate closes. Publish code, test/contract changes and
compact hash/count evidence only; unpublished coordinates, dictionaries and
native payload bytes stay outside Git. Installed Cedar 07 qualification,
numerical/achieved geometry review and full-auto recovery remain pending.

**Cedar 07 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,370 tests, two skips and 276 subtests (97.41 s)**. The initial
generator/native/preparation/qualification/shuttle focus passed **192 tests
(38.98 s)**; the final aromatic/orchestration focus passed **36 tests (1.84 s)**.
The two source-declared-ring acceptance regressions fail before the change and
pass after it. Negative controls retain rejection for partial/missing/conflicting
declarations, fused or charged rings, exocyclic and outside-ring changes,
altered H/formal charges/elements and invalid numerical targets. Existing
relocation tests delete original build checkouts and poison normal imports.
The same returned four candidates prepare offline, retaining source-specific
OP2 H. No new Phenix/Coot process ran in this validation environment.
Changed runtime files are `src/nasolve/cif_generation.py` and the linked/native
probe templates; source-bundled transport needs no new dependency. Inspection
schema 1 gains additive representation evidence, generation policy advances to
v4, and the native probe keeps completed v3 receipts readable. Generated
coordinate/CIF/native payloads remain excluded from Git. Descriptors,
machine-readable evidence and the editable figure/caption are updated together.

**Cedar 05 returned; Cedar 06 prepared (2026-10-14):** all 57 payloads in
`05_Cedar_dy4qx3qg_cif_native_review.zip` verify. Native interpretation completed
at exit 0 with 42 mappings, 38 intra-strand O3′–P links and zero coordinate
OP3/O3P. REVIEW is the worker's deliberate successful inventory status. Four
generic monomers still expect isolated OP3. The fresh trial has free 5′-OH
ends A:1/B:1/C:8/D:1; the older W trial's D:1 phosphate consent does not apply.

Source/effective audit also finds lost OP2 H in the CGY/IMC/DX ReadySet
definitions; only IGU's accepted candidate preserves its complete source state.
`06_Cedar_probe_cif_linked.py` therefore reuses existing source-preserving eLBOW
generation for rejected components before per-site preparation. It keeps all
raw inputs, numerical findings, model coordinates and NARestraints parameters.
Opt-in detailed native inventory checks actual monomers, all declared links,
exact custom target/weight coverage and pair/stacking parallelities, plus a
shared-code internal/free-OH IGU control. No runtime is installed on the
laptop, no frozen run is rewritten, and no ReadySet/refinement/adoption starts.

The Cedar 06 native generation return and next retry are recorded above.
Review the next prefixed capsule before considering integration or full-auto retry.
Source-state regeneration, linked mechanics and numerical/achieved geometry
remain separate verdicts. Known 5CM/DP reviews remain visible. Public source,
tests and contract updates belong on Cedar; unpublished input bytes remain
outside Git. Baseline Cedar's complete Linux suite passed 1,308 tests, two
skips and 276 subtests. Final new-suite validation is recorded below after
completion; offline/fake native tests are not installed Phenix evidence.

**Cedar 06 implementation's offline validation:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q`
passed **1,345 tests, two skips and 276 subtests (96.43 s)**. The focused
native/preparation/qualification/shuttle files passed **75 tests (25.07 s)**.
The assembled runner replayed the exact 05 ZIP offline, identifying IGU reuse
and CGY/IMC/DX source-state regeneration requirements. Actual IGU projection
removes OP3/HOP3/HO3′ and retains HOP2. Relocation tests delete both source
checkouts and poison normal imports; input corruption remains a preserved
failure capsule. The editable SVG was regenerated, rendered and inspected.
Regression controls reject changed targets/weights, duplicate planes, lost
links/H, incorrect types/charges, missing mappings and undeclared same-code
end states. The new native worker/detail interface is tested using explicit
fake installed APIs. No new Phenix/Coot execution occurred in this environment.

**Cedar 04 reproduction and Cedar 05 diagnostic (2026-10-12):** the returned
`04_Cedar_r2cunjcc_cif_generation_review.zip` verifies all 22 manifest entries.
The [compact repeat evidence](elbow-source-retention-evidence.json) records
exact parsed CIF/PDB atom-row equality to v3; only generation timestamps differ.
Native eLBOW completed in **22.019048 s**, with source retention and numerical
findings unchanged. The prefix is present in console, receipt, output directory
and review ZIP. This is reproduction and delivery evidence, not native-reader
or linkage qualification.

The new `05_Cedar_probe_cif_native.py` freezes an external diagnostic bundle
from the source-audit runtime stack and prepared model, with the accepted
candidate substituted only in the copied dictionary input list. The prior
generation probe hash-binds the source audit/raw ReadySet baseline and the exact
candidate receipt; explicit caller paths remain operational references.
Parameterized source precedence, torsion normalization and every recorded
ancillary PHIL/EFF/site-modification input are retained. The installation-bound
`phenix.python` worker inventories native readers, effective monomer/missing-atom
mapping and interpreted atom/proxy evidence. Its explicit native-parser PHIL
namespace adapter retains all definitions and rejects unused parameters.
The subsequently returned native inventory is recorded above. Success is REVIEW, with no
model replacement, optimization, ReadySet retry, adoption or certification.
The human descriptor and editable figure/caption reflect this diagnostic scope.
Final offline validation: **16 native-boundary tests pass (1.62 s)** using
explicitly fake installed APIs, **22 shuttle tests pass (9.48 s)** with deleted
source checkouts and poisoned imports, and **19 discovery/CLI tests pass
(0.48 s)**. The established full-suite command passes **1,308 tests, 2 skipped,
276 subtests (54.09 s)** after final mapping/provenance changes. Fake APIs verify
process, hash and reporting boundaries; they are not native Phenix evidence.
The figure was regenerated and rendered for visual QA. New schemas are
schema-1 native inspection/probe receipts and selected-bundle evidence; the
generation policy remains v3. Private crystallographic inputs stay outside Git.

**Native v3 source-state retention and visible ferry IDs (2026-10-12):** the
user returned the 22-file [source-retention capsule](elbow-source-retention-evidence.json).
Installed Phenix 2.2.1-6174 completed RM1/GDIIS generation with `--pH=low` in
**19.958581 seconds**. All 37 atoms, 39 normalized bonds, 14 hydrogen
attachments and zero formal charges are retained, including HOP2/HOP3.
**C2–N3 = 1.397 ± 0.030 Å**. The three sugar centers retain source coordinate
handedness under identical atom order. Five finite PSD plane reviews remain
visible. Candidate status is **CANDIDATE_REVIEW**, not adoption or chemistry
approval: source CIP/aromatic metadata is absent, generated signed chirality is
not equivalent metadata, and the dictionary group remains non-polymer rather
than DNA LINKING. The actual native log names RM1 even though the CIF header
says AM1; preserve both as provenance.

The immediately preceding return was a repeat of v2, with no `--pH=low`; it was
not a failed retention attempt. New ferries use a leading identifier such as
`04_Cedar_probe_cif_generation.py`; sessions and ZIPs carry the same identifier,
and ZIPs add their unique run token near the front. Console and additive schema-1
receipt fields identify the delivery/policy explicitly. The collaboration
contract records the user's preference for visible prefixes and one exact
terminal command. Older runs and explicit output paths remain intact.

Next: qualify an external candidate derivative against the original prepared
model and complete effective bundle, including source-derived DNA metadata,
site-specific internal leaving atoms, true ends/nicks, native parser/proxy
coverage and generic IGU/IMC/CGY/DX linkage. Current production linked profiles
cover only 1AP/DZ/DP/5CM. No old candidate/model is substituted into the fresh
campaign, no checkpoint is selected, and full-auto recovery remains pending
these native checks. Geometry/sticky-end stitching is a separate planned layer.
Validation of the naming/receipt change: **26 focused tests pass (6.36 s)**,
including relocation after deletion of the source checkout, preserved prior
runs, leading ZIP/run identifiers and invalid-prefix refusal. The established
full-suite command passes **1,269 tests, 2 skipped, 276 subtests (42.49 s)**.
The numerical generator policy remains v3; only delivery metadata/names and
console identification changed. Private source/candidate/model payloads stay
outside Git. No native Phenix/Coot invocation ran in this Linux validation.

**Optimized candidate and source-state retention (2026-10-12):** the returned
22-file capsule is checksum-verified in
[the native evidence record](elbow-optimized-state-evidence.json). Installed
Phenix 2.2.1-6174 selected underscored initial-geometry/hydrogen aliases and
completed optimization in **24.107482 seconds**, using **RM1/GDIIS**. IGU's
collapsed C2–N3 target became **1.387 ± 0.029 Å** with distinct coordinates.
The candidate still fails source-state preservation: HOP2/HOP3 were removed,
OP2/OP3 formal charges changed from 0 to −1 and phosphate orders became DELOC.
Four plane-angle reviews have positive-semidefinite Gram matrices and small
0.06–0.13° sum residuals; numerical REVIEW must not be labeled incomplete.

Generation-v3 requires the installed valued `--pH` option and selects `low`
as the generator's exact-input-chemistry mode. It explicitly leaves experimental
pH and intended crystal protonation unassessed. The candidate gate preserves
supported soft numerical reviews, while rejecting invalid/incomplete numerics,
unresolved plane compatibility and chemical-state changes. No source or old
run is overwritten, no individual target is guessed and no candidate is
adopted. The next laptop probe demonstrated source-state retention as recorded
above; native reader/polymer-link qualification and full-auto recovery remain pending.
The requested optimization option and the observed native backend are separate
evidence. Human/manuscript descriptors and the figure caption are current.
Final isolated Linux validation with the established full-suite command passes
**1,264 tests, 2 skipped, 276 subtests (43.26 s)**. Regressions cover exact valued
source-state control negotiation, refusal of missing controls or ignored
hydrogen preservation, complete soft reviews, impossible/missing/nonfinite
plane evidence, missing numerical coverage and collapsed coordinates. Native
source-preserving generation was pending at that validation; no native tool ran
in the Linux check. The subsequently returned native result is recorded above.

**Native generator CLI compatibility (2026-10-11):** the returned 18-file
[capsule](elbow-cli-compatibility-evidence.json) confirms installed Phenix
2.2.1-6174 rejected `--initial-geometry` before reading chemistry (exit 2,
2.071012 seconds). No new candidate was generated; original/frozen source
hashes survived. The wrapper had used a spelling from the documented option
table; the example uses a different alias. Generation-v2 now probes the exact
installed executable's help, negotiates advertised spellings/value semantics,
and refuses missing controls before chemistry. Help and executable hashes are
retained. Probe summaries now distinguish failed/rejected generation from
actual candidates awaiting review. The corrected native retry completed as
recorded above; this first CLI failure supplies no numerical-quality or
chemical-state verdict.
Final isolated Linux validation with the established full-suite command passes
**1,246 tests, 2 skipped, 276 subtests (42.81 s)**. New regressions cover dashed,
underscored and mixed flags, misleading help examples/prefixes, valued versus
switch controls, unsupported controls, help timeout/error and executable races.
The original failed receipt and run stay intact. Generation receipt schema 1 adds installed capability
evidence under policy `cif-independent-elbow-candidate-v2`.

**Fresh ReadySet defect generalized (2026-10-11):** the user returned a
checksum-verified 16-file capsule from the new combined DNA run. Preflight and
Phaser passed: **TFZ 13.10 / LLG 196, H 3**. PostMR correctly blocked IGU,
whose generated C2–N3 target is **0.000 ± 0.020 Å** and whose dictionary C2/N3
coordinates coincide. Other local targets are distorted; source HOP2/HOP3
were omitted and OP2/OP3 formal charges changed. This is actual numerical
generation, not a raw-graph copy. The
[evidence record](igu-readyset-generation-evidence.json) and
[synthetic descriptor](synthetic-dna-mechanics-test.md) preserve exact hashes.

The generalized assessor checks dictionary coordinate degeneracy and PostMR
records a component quarantine with exact atom/target diagnostics. The new
explicit `cif-doctor generate-candidate` API/CLI regenerates a whole component
from frozen chemical input plus complete supplier ideal-coordinate seeds; it
does not patch one bond or borrow MR coordinates/older prepared candidates.
A one-file probe selects invalid generic components and collects native
generation/comparison evidence into a review ZIP without altering the old run.
Native source-state preservation, candidate quality and generic polymer-link
qualification remain pending. Automatic adoption and a full-auto retry are
not claimed complete. Update the human overview/figure with each extension.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,222 tests, 2 skipped, 276 subtests (43.87 s)**. Nine probe delivery
regressions use invented XRAWR/Q99/Y components, deleted original source
checkouts and poisoned imports; all runtime/source/review-ZIP hashes validate.
The source-bundled inspect-only probe also selects IGU from the real returned
capsule with its original source hashes verified. Native eLBOW optimization and
candidate acceptance were NOT_RUN here. The updated editable figure was
regenerated and rendered for visual QA. Changed runtime files are the assessor,
general candidate module, CLI/optional Phenix discovery and PostMR quarantine;
receipt schema 1 gains explicit dictionary geometry and generation evidence.
Private dictionaries and native outputs remain outside Git.

**Fresh combined DNA mechanics inputs (2026-10-11):** user authorized a new
synthetic K:X/B:S/Z:P/D:T test on copied donor diffraction with AutoSol off.
The [human descriptor and recipe](synthetic-dna-mechanics-test.md) own the exact
42 targets, real free-5′OH preparation, isolated one-file shuttle and limits.
This is an ordinary fresh source-acquisition/ReadySet test; no prior numerical
bundle or relaxed coordinates are substituted. Input preparation and campaign
policy are offline-tested; native laptop execution remains pending. The frozen
Cedar checkout is preserved and no pull is required to use the shuttle.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,124 tests, 2 skipped, 276 subtests (38.50 s)**. The nine shuttle
regressions include deleted source checkouts, poisoned laptop imports and exact
module-origin receipts. A separate stage-only check using the real local QiC
donor also produced a valid frozen DISCOVERED plan; no native programs ran.
Only code, the recipe and documentation enter Git. Generated donor copies,
receipts and standalone deliveries stay outside the repository.
The user has also returned a successful laptop execution of the public CCD
shuttle: all 18 source PASS / effective REVIEW / numerical UNASSESSED. That
result confirms the offline audit path, not native dictionary generation.

**Human overview, public ZIP runner and upstream data review (2026-10-11):**
The [human/manuscript descriptor](cif-doctor-human-overview.md) now explains
the implemented algorithm, tools, placement and limits, with an adaptable
methods paragraph and [editable SVG/layout source](figures/README.md).
`AGENTS.md` and the collaboration contract require descriptors and figures to
stay current when features change. No geometry/stitching capability is added.

The single-file `run_cif_doctor_ccd_controls.py` embeds the unchanged assessor
and required reader/normalizer code. SHA-256:
`e1d54f1dab5c5dde733aa65fcf9dd66a82b720b7ee753a9c589cf9946912680e`.
The exact previously delivered public ZIP runs offline with **18 source PASS,
18 effective REVIEW, 36 receipts**, every input unchanged and native tools
NOT_RUN. Graph-only numerical UNASSESSED is expected in source mode; effective
screening does not generate numerical dictionaries or run ReadySet.
The established laptop Python can run this artifact without installing or
pulling NASolve; it creates a fresh output folder beside the ZIP. The frozen
laptop source state remains separate from the published Cedar feature.

Validation with the same isolated environment: **12 shuttle tests pass**,
including exact receipt parity, unsafe/tampered ZIPs, exclusive output and
relocation with the original checkout removed. The complete NASolve command
below now passes **1,090 tests, 2 skipped, 276 subtests (36.37 s)** with the
corrected upstream workbook. Overlay tests explicitly cover both legacy DF
S2 mappings and corrected S1 mappings; the compatibility adapter is retained.

The separately reviewed NARestraints source workbook corrects 5BU/BRU sugar
metadata and abbreviations, DF/S6G mappings and all 129 literal C5 trailing
spaces. Its **138 exact cell changes** are documented in its Markdown/JSON
audit. Workbook SHA-256 after the patch:
`afed0f332c3d70cd14c395005fcbccf38201e2818bb9b765c86decda309707f5`.
All other cell values/types/styles, sheet order/dimensions, and unrelated
uncompressed XLSX parts are preserved. NARestraints passes **42 tests**;
the seven new regressions failed before their corresponding corrections.
This remains unreleased source data; the pinned v1.1.3/laptop installation
has not been updated. PSU's coupled attachment/base-plane issue stays open.
Native interpretation/refinement was not run for these metadata corrections.

Changed files are the overview/figure source and maintenance/index documents,
the shuttle builder/template and tests, and the legacy/corrected overlay test.
Shuttle schema 1 adds artifact-build provenance and output-anchored references;
existing NASolve runtime/checkpoint schemas and frozen runs are unchanged.
The manuscript PDF export, standalone runner and generated audits remain
outside Git; neither private coordinate/reflection data nor the public CCD
payloads are added. The existing native/proxy/geometry follow-up remains open.

**CIF Doctor implementation validation (2026-10-11, isolated Linux):**
Published implementation: Cedar **`8c181c5d47cd987318c48568f13d93ef6bdfbb87`**,
tree-equivalent to local **`105f2bb`** at tested tree
`fbaaab578c4737b35cbfd1fa145f1e153f1b86e0`. Subsequent handoff bookkeeping
does not change that tested runtime. The frozen laptop checkout remains untouched.

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,077 tests, 2 skipped, 276 subtests (35.06 s)**. The five new Doctor
test files pass **88 tests and 7 subtests (1.05 s)** with the same environment.
Independent review is clear; source and run-adapter regressions exercise
relocation with the original paths removed, immutable selection and input-race
rejection. No native Phenix/Coot execution occurred for this implementation.

The final assessor source SHA-256 is
`7eb53fb2b8c1782fae9f3785a9ae2295baa664982237c01b5a5edf86ec496798`.
Fifty-six source/effective assessments cover **18 public CCDs plus 10 packaged
dictionaries** with every input byte preserved. All public CCDs pass graph
inventory with numerical parameterization unassessed; all need review when
presented as effective numerical dictionaries. The six exact historical
5CM/DF/DP replays preserve their hashes. The standalone comparison additionally
exposes the DF source/generated bond-order, aromatic, hydrogen, charge and
numerical-field differences without declaring which chemistry is correct.
The reviewed historical 5CM preparation reproduces `61bf14a…` exactly.

Changed runtime files are `cif_doctor.py`, `cif_doctor_repair.py`,
`cif_doctor_run.py`, `cli.py` and `postmr.py`; new schema-1 assessment,
comparison and preparation receipts are documented in the runtime guide.
Existing runs and legacy profile scopes need no migration. Public control
provenance is committed; downloaded CCDs and generated audit receipts remain
outside Git. A frozen public-only control capsule preserves 18 CCDs and
36 receipts (SHA-256 `085f4077828d1b5ee6503dfd73dbb9c89a87c7b3fff3779520809e77e67b042b`),
without private models, maps, reflections or diagnostic CIFs. Runtime native
proxy verification and dictionary/coordinate adoption remain open.

**GeoTest orchestration trial wrapped:** the corrected native rerun verifies
six numerically ready refinements, two bounded Doctor reviews and one MR failure.
All nine workers and 14 native refinements completed, the one-file parser fix
was installed with its original backup, and model/data space groups are recorded.
The three candidates blocked by the previous parser now progress past MR.
The user explicitly closes this campaign at its orchestration scope without
further scientific repair; preserve its provisional checkpoints and reviews.
The [guided arm-connection module](construct-registration.md#geotest-guided-arm-connection)
is now bundled into the planned Doctor workflow alongside data/Free-R diagnostics
and the generalized restraint assessor, using Scout/Topo primitives.

1. **CIF Doctor's first implementation slice is complete in this change.**
   User decision **2026-10-11**: build from the saved blueprint, screen source
   dictionaries before PostMR mutations and assess effective files after ReadySet.
   [The runtime guide](cif-doctor.md) owns the new commands and exact scope.
   Assessments are deterministic and read-only, with report-only pipeline hooks.
   Explicit preparation wraps existing supported torsion normalization and the
   exact reviewed historical 5CM correction; it does not adopt a new dictionary.
   The [machine-readable implementation map](cif-restraint-doctor-implementation.json)
   preserves the scientific cases, checks, ReadySet/PostMR placement, repair
   boundaries, cache keys and regression plan. Its runtime-progress section
   distinguishes this initial implementation from future recovery;
   collaboration/personality notes remain outside the repository.
   The 5CM/DF/DP evidence is sufficient to implement the first assessment slice;
   it does not yet establish general automatic repair. This proposed restraint
   doctor is distinct from the existing refinement-strategy `refine-doctor`.
   Public CCD access is verified. Eighteen public source graphs selected
   from NARestraints cover halogens, C-glycosides, L-DNA, missing O3′ and
   diphosphates. The workbook is pairing/target-selection evidence rather than
   a universal chemical authority. Recover and freeze the exact historical
   **8RO/DE and failed 1AP** inputs as additional challenge cases; synthetic
   connectivity regressions must remain labelled as reproductions. Apply the same rules before adding any new
   component-specific exception; include valid controls and retain unsupported
   findings. The [fixture plan](cif-restraint-audit-methods.md#learning-cases-and-future-regression-fixtures)
   distinguishes known defects, source adaptations and unresolved chemistry.
   **Doctor bundle decision, 2026-10-11:** retain the existing refinement/Free-R
   diagnostic module and add the restraint assessor plus model geometry and
   connectivity assessment under one coordinated workflow. The user attributes
   GeoTest's high Rwork to arms fractured at sticky ends; record that diagnosis
   as the motivation for examining the actual model/maps and intended assembly,
   not as a causal proof from Rwork. Check geometry/connectivity before choosing
   further refinement strategies, including numerically ready models. Guided
   stitching requires declared arm pairing, strand routing and symmetry mates;
   preserve true nicks/5′-OH termini and frozen Free-R, create a bounded child
   checkpoint and validate/refine it. The assessor remains the first slice;
   geometry integration is future work, not an additional Cedar/Pine merge gate.
2. **Bound the remaining combined-model numerical review.**
   The [native ledger](native-modified-pair-live-validation.md#dp-geometry-trial--n5-conflict-relieved-review-pending)
   records verified N5 relief and preserved chirality, links and pair coverage;
   modest residual strain remains. The user reports **base visual PASS** for
   the exact new model, with sugars explicitly unassessed by eye. Review the
   remaining sugar torsions and minimizer termination numerically before a
   full-qualification or scientific continuation decision; do not request another sugar
   verdict by eye or infer a dictionary defect from residual strain alone.
   These are bespoke component diagnostics. Park further multi-modified-model
   edits/refinement unless a specific unresolved finding needs fresh evidence.
   The user's optional multi-letter-edit continuation is not a prerequisite
   for starting the assessor, and is not being declared complete. Reuse the
   returned receipts; do not chase zero residual strain or repeat passed trials.
3. **Turn demonstrated preparation into ordinary fresh full-auto behavior.**
   The current trial used selected numerical CIFs in a frozen resource bundle
   and ad hoc linked derivatives. Acceptance is a new run from declared
   model/sequence intent and component codes, without per-run source patches
   or a hand-prepared bundle. Cover already-present modified residues as well
   as mutations; distinguish library acquisition/cache, numerical preparation,
   verified polymer context and a small justified override registry. This is
   the product goal, not an achieved result or an unlimited new Cedar gate.
4. **Close the existing bounded Cedar/Pine gates.** Retain the prior P1/P3/P4
   receipts and fill only missing effective-dictionary, normal-GZ11 and
   user-veto/current-pointer evidence. Source-native P2 and real P5 remain
   separate. Then integrated tests/review P6, Cedar→Pine and Pine→main P7
   with ancestry verification and audited retirement. Do not rerun passed
   cohorts just to refresh documentation.

The [component contract](modified-component-preparation.md) owns source
chemistry and overrides; the [native ledger](native-modified-pair-live-validation.md)
owns exact sites, hashes and returned stage results. **1W5→DZ and 1WA→DP
remain mandatory reviewed transformations; A1AAZ→DF is a label bridge.**
DE geometry remains unresolved. Q is implemented; DQ/S/DS aliases are not.
Lab S/DS means N-linked IMC, not S6G or C-linked hachimoji S. Ordinary
supplier copies must not become permanent exceptions merely because used.

## Optional GeoTest side trial

Requested **2026-10-11** as a separate exploratory run; the restraint-doctor
priority above remains active. The standalone `run_geotest_campaign.py` reads
`examples/GeoTest`, preserves outer design names, and schedules each coordinate
CIF/PDB model against each coherent nested processing set. It declares trust in
supplied coordinates without inventing sequence evidence or requesting sequence
mutations. One whole-model copy and 1.0 Å MR RMSD remain the search hypothesis;
no winning model/processing combination is selected.

**First native ferry verified:** all 192 included files match their recorded
hashes and sizes; 39 large/reflection files were deliberately omitted. The
user's **8/9 good** describes eight placed models, not eight MR gate passes.
The receipts show four `MR_SUCCESS`, two `MR_REVIEW` and three `MR_FAILED`.
These are the original recorded gates; the later selected-model score audit
below identifies why they undercounted good MR candidates:

| Member | TFZ | Verified stopping point |
| --- | ---: | --- |
| X11_12 | — | No MR solution |
| X11_16 | 7.0 | MR REVIEW |
| X11_17 | 8.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_18 / dataset1 | 6.0 | MR FAILED, placed model retained |
| X11_18 / dataset2 | 7.2 | MR REVIEW |
| X11_19 | 9.2 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_20 | 15.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_22 | 14.9 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_25 | 6.8 | MR FAILED, placed model retained |

The placed-model space groups are **P2₁, P4₃ and P1**; the earlier user shorthand
P2₁2₁2 is not the P2₁ recorded in these files. This ferry used Phenix
**2.2.1-6174**, Coot **1.3.3**, Python **3.12.14** and clean Cedar
`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`. No completed refinement or Doctor
result is established by it.

**Real input preparation, not a repaired status:** the user explicitly clarified
that the strands are linear, with **free 5′ hydroxyls and no terminal phosphates**.
The updated runner copies the originals, validates CIF-to-PDB preservation, then
removes only complete P/OP1/OP2/OP3 groups at the seven declared chain starts.
All nine supplied member models lose exactly **28 atoms each**; O5′ and every
retained atom record remain unchanged. The prepared inputs pass the native
phosphate audit. Ambiguous/incomplete terminal groups block that member; internal
phosphates are not stripped. Preparation records exact deletions, hashes and
before/after audits. No fake sequence, phosphate allowlist or coordinate repair
is used. This corrected search model is the input to a **fresh** native preflight
and Phaser run; the original cohort and its failed receipts remain intact.

**One-launch full auto:** default endpoint is `refine-doctor`, using existing
native stage APIs and bounded policy. Eligible borderline MR continues with its
review warning; failed MR and chemistry/integrity failures remain blocked.
PostMR is followed by AutoSol when anomalous data warrant it, five-cycle
AutoRefine, and Doctor only for eligible `AUTOREFINE_REVIEW` (at most five trials
of three cycles). Unaccepted AutoSol phases are excluded. Verified successful
Doctor recommendations may be selected provisionally, without user approval or
overwriting checkpoint history; ordinary ready refinements need no Doctor trial.
Each member keeps its observations/Free-R and failures do not stop other members.

Every launch creates a fresh `geotest-fullauto-*` directory under the selected
output parent, with a frozen `geotest_recipe.json`, schema-2 adapter receipt,
per-member provenance, summary, compact `GeoTest_review.zip`, and
`View_results.command`. The final menu and double-click launcher open the exact
verified refined checkpoints/models/maps in Coot. Full observations/results stay
local. The single downloadable script is the adapter deliverable; these repo
changes document it and do not patch NASolve runtime or scientific inputs.

Offline validation: **76 tests, 20 subtests passed**, including all nine real
inputs, exact terminal deletions, original preservation, preparation before the
worker, full-auto handoffs, member failure isolation and exact Coot checkpoint
selection. The assembled script loads all embedded modules. An actual X11_20
model also passes real NASolve preflight and PostMR code without sequences,
using explicitly stubbed external MTZ/Phaser/ReadySet programs and fixture
reflections; this is not native execution. The unchanged core suite passes
**981 tests, 2 skipped, 257 subtests (29.58 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The revised native run has now returned as described below.
This is **not native NASolveCampaign CIF/no-sequence support**. Integrating
declared terminal chemistry and preparation into a native single recipe/button
remains the product follow-up; this side trial does not close the formal blind
baseline, production input-adapter or geometry-qualification gates.

**Returned full-auto native run, 2026-10-11:** `GeoTest_review(1).zip`
(SHA-256 `7fdaeee177c3e3eed63d49fb280bb4314ad05a88f94c3564f78b244291e4b458`)
contains **361 verified files**, with **98 deliberately omitted** large or
reflection files. All originals remain unchanged. The laptop again used clean
Cedar `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, Python **3.12.14**,
Phenix **2.2.1-6174** and Coot **1.3.3**. This was a real native execution,
not the earlier stubbed integration check. The user reports success for the
trial's scope, with arm/triangle connectivity requiring further guided work.

| Member | Recorded TFZ: first → 5′-OH run | Selected-model final TFZ-equivalent: first → 5′-OH run | Returned full-auto result |
| --- | ---: | ---: | --- |
| X11_12 | — → 2.9 | no selected model | MR FAILED; no solution |
| X11_16 | 7.0 → 7.4 | 14.0 → 14.5 | AUTOREFINE READY, Rwork/Rfree 0.2940/0.3404 |
| X11_17 | 8.0 → 5.1 | 12.3 → 12.2 | Recorded MR FAILED; refinement not attempted |
| X11_18 / dataset1 | 6.0 → 7.8 | 7.8 → 7.7 | REFINE DOCTOR REVIEW, inspection 0.4691/0.4859 |
| X11_18 / dataset2 | 7.2 → 6.2 | 8.0 → 8.0 | Recorded MR FAILED; refinement not attempted |
| X11_19 | 9.2 → 9.9 | 13.3 → 13.8 | AUTOREFINE READY, 0.2421/0.2890 |
| X11_20 | 15.0 → 15.2 | 17.0 → 16.9 | AUTOREFINE READY, 0.2262/0.2336 |
| X11_22 | 14.9 → 15.2 | 15.2 → 15.3 | AUTOREFINE READY, 0.2647/0.2770 |
| X11_25 | 6.8 → 6.1 | 9.6 → 9.8 | Recorded MR FAILED; refinement not attempted |

All eight native refinement processes exited zero (five ordinary refinements
plus three eligible Doctor trials). Four ready results are `refine-001`.
X11_18/dataset1 remains REVIEW: inspection checkpoint `refine-002`, current
checkpoint `postmr`, no recommendation or provisional selection. Numerical
readiness does not certify intended triangle connectivity. Native reports still
leave bond/angle RMSD summary fields null despite geometry values in the raw
Phenix output; do not infer a clean geometry verdict from those missing fields.
The compact ferry omits MTZs, so reflection/Free-R preservation is supported by
native receipts/audits rather than an independent replay of omitted arrays.

**Apparent MR loss is a score-association defect:** all nine original model,
reflection and metadata hashes, all 46 NASolve source hashes and normalized
Phaser settings match between runs. Search models differ only by the declared
28 terminal-atom removals; every retained atom record is unchanged. The parser
previously took the first TFZ/LLG from each solution-history line. Phaser writes
later `TFZ==` values after orientation refinement; these must be associated with
the selected output model, not maximized across unrelated solutions. See the
[Phenix annotation reference](https://www.phenix-online.org/documentation/reference/phaser.html#annotation).
For X11_17 the selected output records `TFZ=5.1` followed by `TFZ==10.8` and
`TFZ==12.2`; its final LLG is 353, rather than the initially parsed 304.
Both cohorts therefore contain **seven selected models meeting the ≥8 gate,
one borderline model and one no-solution case** when audited by final associated
scores. This is a retrospective evidence assessment, not a rewrite of old
statuses or a claim that the three newly eligible candidates were refined.

**Parser fix validation:** selected-output annotations, final score/LLG
association, matching PDB/MTZ stems, ambiguous/invalid headers and legacy
single-output fallback pass **17 focused tests and 12 subtests**. The complete
suite passes **989 tests, 2 skipped, 269 subtests (32.75 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The worker/preflight/full-auto-driver checks also pass **54 tests**. Read-only
parsing of all 16 actual selected PDBs reproduces the table above. The report
adds versioned `score_evidence` and selected-output checksums; existing fields
and TFZ thresholds remain compatible. This initial validation did not rerun
native Phaser or change any old receipt. The subsequent fresh laptop run below
installed the small fix at the recorded diagnostic head; do not pull a different
head over that distinct local state merely to replay these results.

**Authorized laptop rerun shuttle:** the user requests a fresh run with the
corrected parser and space groups in final output. The updated standalone
script accepts `--install-parser-fix`. It verifies the exact 46-source laptop
manifest (including the laptop's distinct `curated_ligands.py`), compiles and
checksums the embedded replacement, backs up original `phaser.py` in the fresh
workspace, preserves permissions and atomically installs only the known parser
update before loading it. Old parser SHA-256 is
`d277a10e4a6c7b843c3e5cd1af4b09dd835872054b7b3cd887f9215177788331`;
replacement SHA-256 is
`18aedbb3b414d2dd86e8c284219ca078e682e08003a8f82637f2b462d23a3570`.
Unknown local edits or compatibility drift stop the update; an exact installed
replacement is an idempotent no-op. This explicitly authorized one-file update
leaves Git dirty at the existing laptop head. Do not replace the whole checkout
or pull remote Cedar over the distinct diagnostic state.

The resulting fresh run retains the prior 5′-OH input policy and full-auto
bounds. Terminal final output, `campaign_summary.csv` and the Coot menu show
the exact displayed checkpoint's space group, falling back to the selected
Phaser model. The checksum-verified input MTZ header is retained separately;
when no model exists its space group is labelled as data-derived. Receipts add
`space_group`, source/artifact/hash provenance and `input_space_group`; absent
metadata remains explicit and cannot alter MR/refinement status.

Validation: **94 adapter tests and 22 subtests pass**. The assembled download
also passes parser installation, original-code backup, actual X11_20 terminal
preparation, source-preserving staging and a second already-fixed launch.
That integration is offline: reflection metadata are fixtures and only the
unavailable laptop-specific curated-source manifest entry is substituted with
the local fixture's hash. That offline check launched no native Phenix process;
the subsequent returned native rerun is verified below.

**Corrected native run and close-out, 2026-10-11:** `GeoTest_review(2).zip`
(SHA-256 `8ef30e37729d74631eae8b91b0ac1d04c52f4879cb5d96c0f9f30addc7c0a9f9`)
contains **462 hash/byte-verified files** and **138 declared compact omissions**.
The runtime reports Python **3.12.14**, Phenix **2.2.1-6174** and discovered
Coot **1.3.3**; the native batch completed in about 13 minutes. All nine workers
exited zero; 44 stage
snapshots, nine final native reports and per-case provenance match the aggregate.
The installer verified 46 source files, preserved the exact old parser backup,
and changed only `phaser.py` to the fixed hash above. Original inputs and all
other source hashes remain unchanged. All nine preparations remove exactly 28
terminal phosphate atom records; every other byte is preserved, including O5′,
and their native frozen search models match the preceding 5′-OH cohort.

| Member | Displayed space group | Final selected TFZ | Returned result | Rwork / Rfree |
| --- | --- | --- | --- | --- |
| X11_12 | P6 (input data only) | — | MR FAILED; no selected model | — |
| X11_16 | P2₁ | 14.5 | AUTOREFINE READY, refine-001 | 0.2940 / 0.3404 |
| X11_17 | P2₁ | 12.2 | AUTOREFINE READY, refine-001 | 0.2165 / 0.3325 |
| X11_18/dataset1 | P2₁ | 7.7 | Doctor REVIEW, inspection refine-002 | 0.4691 / 0.4859 |
| X11_18/dataset2 | P4₃ | 8.0 | Doctor REVIEW, inspection refine-002 | 0.3230 / 0.3418 |
| X11_19 | P4₃ | 13.8 | AUTOREFINE READY, refine-001 | 0.2421 / 0.2890 |
| X11_20 | P1 | 16.9 | AUTOREFINE READY, refine-001 | 0.2262 / 0.2336 |
| X11_22 | P1 | 15.3 | AUTOREFINE READY, refine-001 | 0.2647 / 0.2770 |
| X11_25 | P2₁ | 9.8 | AUTOREFINE READY, refine-001 | 0.2781 / 0.3179 |

All eight selected-model final TFZ/LLG annotations and displayed checkpoint
CRYST1 records match their checksummed provenance. X11_18/dataset2 and X11_19
have selected/refined **P4₃**, while their input headers remain **P4₁**; retain
both values. The user notes that X11_18's alternatives are different space
groups: the P4₃ inspection result has markedly lower Rfree (**0.3418**) than
the P2₁ / `P 1 21 1` result (**0.4859**) and analytically favors P4₃. Record
this as the user's structural interpretation and comparative evidence, without
changing either review/selection status. The two processing datasets have
distinct observation hashes and Free-R populations; this is not a controlled
same-data space-group ranking. Exactly **14 native refinement processes exited zero**: eight
ordinary refinements and six Doctor trials. Every command keeps original
`IMEAN,SIGIMEAN` observations, `FreeR_flag`, test value 0 and `generate=False`;
each of the eight registries retains its member's original observation hash. Both X11_18
cases keep current `postmr`, inspection-only `refine-002`, no recommendation
and no automatic selection. Their audits remain `NOISY` (546/10377 and 223/3937
free groups) with zero detected inconsistent flags and the explicit unavailable
Friedel-mate comparison limitation. Omitted reflection arrays were not replayed.

No infrastructure blocker remains. The user reports campaign success and asks
to wrap without further scientific repair. All members retain provisional,
inspection-required and unapproved status. In particular, X11_17 passes the
current numerical gate despite a **0.116 Rfree−Rwork gap** and **66.93 clashscore**;
the bond/angle RMSD summary limitation and local assembly/geometry issues remain.
These are fixtures for the planned Doctor geometry module, not approval of the
structures. Native campaign input/recipe integration remains separate future
work; this closes the standalone GeoTest orchestration test.

**Guided geometry follow-up:** the user requests geometry assessment and a
Scout-based guided arm/triangle stitcher bundled with Doctor, available after
MR or refinement once intended connections are declared. The
[contract](construct-registration.md#geotest-guided-arm-connection)
and [live-check queue](construct-registration-live-checks.md) retain this as
planned scope. The supplied Coot examples are `Screenshot 2026-10-11 at
13.53.45.png` (SHA-256
`215ae2967cb6fb5225d141636c766102c641bd87cfe000d7280bd246dd12d25f`) and
`Screenshot 2026-10-11 at 13.56.53.png` (SHA-256
`53fbade3270de9c19c9fc107a87d41a2b9cb7ba66836b5dd04a9c1ca3511e59b`).
They show local model/density discrepancies, without identified checkpoint or
residue selection; no atom-level connection is inferred from the pictures.
Original screenshots, coordinate models and reflection data remain outside Git.

## Restraint doctor and subsequent roadmap

The October 11 priority decision advances the **SMILES-assisted CIF/restraint
assessor** to the first implementation slice of the coordinated Doctor workflow
using the completed trials as evidence. Remaining combined-model qualification
stays explicit and may proceed
alongside it. The Doctor geometry/connectivity module will reuse Scout/Topo
primitives for guided repair; broader Topo slicing / operational Scout remains
later work. None becomes an additional Cedar/Pine merge gate.

- **SMILES-assisted CIF audit (planned, not implemented):** assessment first,
  comparing molecular graphs with atom mapping, charge/H/stereochemistry and
  descriptor provenance. Keep self-consistency separate from independent
  chemistry, and graph checks separate from numerical-restraint validation.
  Reviewed transformations such as 1W5→DZ remain explicit. Follow the initial
  assessor with separately tested, policy-bounded generation/validation and
  automatic continuation for ordinary passing cases. Exact reviewed repairs
  need version/hash policies; ambiguous chemistry needs declared intent, not
  an AI guess. Ordinary runs should not require AI or user source patches. The
  detailed [assessor and automation contract](modified-component-preparation.md#proposed-smiles-and-cif-audit)
  owns findings, uncertainty and repair boundaries. The
  [audit methods](cif-restraint-audit-methods.md) capture the reusable checks,
  5CM/DF/DP lessons, 8RO/DE and 1AP challenge cases, and proposed evidence schema
  for implementation. Broader repair requires those checks and negative controls,
  not merely successful regeneration of the three development cases.
- **Blind AlphaFold baseline after bounded Pine close-out:** preserve frozen
  predictions, observations and Free-R; avoid solved outcomes during blind
  candidate selection. Before this trial, add **PDB and coordinate mmCIF input**
  and an explicit **trust-model / no-sequence-file mode**, since supplied
  predictions may have no separate sequences. These are requested adapter
  capabilities, not implemented options. Record sequence as independently
  unverified, skip sequence-driven mutations, and retain ordinary model/MR
  checks. See [model roadmap](campaign-model-roadmap.md) and
  [architecture](architecture.md) for the proposed contract.
- **Campaign input follow-up:** support shared parent-folder models and nested
  processing datasets, including alternative space groups. Inventory/count
  candidates, run selected MR alternatives separately and compare their evidence.
  [Grouped-processing design](campaign-model-roadmap.md#planned-shared-model-folders-and-processing-alternatives)
  records the requested behavior; current flat discovery does not implement it.
- **Then operational Scout / later Topo surgery**, following the existing
  [registration contract](construct-registration.md) and
  [live checks](construct-registration-live-checks.md). The earlier order
  (blind AlphaFold baseline before operational Scout) remains. GUI/Topo Net
  and the metal-restraint builder remain separate later scopes.

## Evidence and preservation

The combined trial uses real GZ11 observations with hypothetical target
modifications: it is a software integration test, not proof of the crystal's
chemistry or deposition approval. Native completion, chemistry, numerical
metrics and human review remain separate verdicts. The earlier Z:P overall
Coot PASS is not a combined-model geometry verdict. The earlier directional
hydrogen-bond question remains parked; never impose an arbitrary heavy-atom
180° target or modify the successful old run to satisfy it.

Follow the [branch/worktree lifecycle](collaboration.md#branch-and-worktree-lifecycle).
One terminal action per user turn for native debugging, then inspect output.
Preserve the original dirty NASolve checkout, unpublished NARestraints
`Ligands.xlsx`/lockfiles, scientific runs, maps and Free-R. October 8–9
completed-worktree cleanup remains recorded in the backup; the private
lab-notes checkout was intentionally retained. Verify current laptop status
before integration; the returned clean Cedar check does not authorize cleaning
other laptop checkouts or changing the unpublished diagnostic head.

**Status ownership:** this handoff = current priorities; native ledger =
exact trial evidence; subsystem docs = durable contracts; history/Git =
earlier decisions. The October 10 reconciliation archives superseded text
before shortening it and keeps chronology out of the active queue.
