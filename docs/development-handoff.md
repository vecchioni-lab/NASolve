# NASolve development handoff — current state

Updated **2026-10-11** from native receipts, user visual review and verified geometry/DF
bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The current laptop Cedar checkout remains at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, with only the explicitly
authorized `src/nasolve/phaser.py` fix modified after the GeoTest rerun.
Its other 45 frozen source hashes, including the distinct curated source,
are preserved. Preserve this local unpublished diagnostic head; do not pull or
replace it with a remote head to continue the run. Diagnostic scripts/derivatives are
not general production support. Earlier wording remains in Git and the
[exact pre-reconciliation backup](history/development-handoff-2026-10-10-pre-reconciliation.md.txt).

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
