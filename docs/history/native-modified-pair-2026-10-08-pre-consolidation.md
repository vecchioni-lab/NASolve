# Historical snapshot — docs/native-modified-pair-live-validation.md

> **ARCHIVE ONLY (2026-10-08)**. Exact previous body as found in Pine at `eaa6b201b947fbd19dcf17648947d513ca8a053a` follows. Historical next-step instructions, branch states and release claims have been superseded. Start at [the current handoff](../development-handoff.md) and [current native matrix](../native-modified-pair-live-validation.md). Source file remains recoverable in Git at the commit above; the banner is not part of the original source body.

---

# Native modified-pair matrix and human-test ledger

Updated 2026-10-08. **Native W Z:P+5CM:G+DF:A integration reached SOLVED
(numerical), attempt_003/run_003/refine-001**, using isolated candidate NASolve
PR #24 and NARestraints PR #4, Phenix 2.2.1 and Coot 1.3.3. The two earlier
failed attempts are retained, the 17→15+2 post-MR restraint overlay has a
returned read-only audit, and the full NASolve regression passed **961 tests
plus 224 subtests**. **Human Coot inspection of the refined model has now been reported
PASS for overall software-generated model quality**: visible bond and plane
geometry with some acceptable base-plane wobble; do not tighten restraint
weights to erase that observation. The user did not provide individual
per-site map/clash measurements or `.geo` deviations. Real experimental
chemistry acceptance, the separate five-case family matrix and eventual
merges/releases remain **PENDING**. This is a software-integrity challenge
on unrelated GZ11 data, not a demonstrated experimental Z:P crystal.

## Scope and original failed observation

The single-dataset frozen run is retained at
`~/NASolve-live-tests/zp-paired-native-oiipj_t2/GZ11_ZP/AutoMR/run_001`.
Its frozen W model, GZ11 donor reflections and sequence-family target passed
planning/preflight/integrity; native Phaser returned MR_SUCCESS, **TFZ 12.9**,
**LLG 210.0**. Native PostMR stopped:

```text
PostMRPreparationError: NARestraints failed:
A:12 (Z) has no mapped atom 'N2' for GC recipe
```

The recovered `narestraints_input.pdb` and installed workbook were inspected
read-only. A:12 DZ has O2/N3/N4 roles but no N2; B:4 DP has N1/N2/O6.
The NARestraints recipe registry did recognize Z:P but had assigned Z the
G-like GC-template role and P the C-like role. An *in-memory* correction to
P=G-like/Z=C-like passed three-contact selection, reversed input order and
stacking-plane checks; installed files and the failed run remained unchanged.

Upstream [NARestraints PR #4](https://github.com/vecchioni-lab/NARestraints/pull/4)
is **merged and released** as
[v1.1.3](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3),
`main` commit **a9264f9**. It corrects Z:P and K:X role orientation
and stacking planes, retains correct B:S/D:T handling and adds workbook-based
regression checks. The upstream `GC` designation is a **shared geometry
template**, not a requested or silently inserted `force = G:C`.
Final [release run 37702686885](https://github.com/vecchioni-lab/NARestraints/actions/runs/37702686885)
passed **Python 3.10, 3.12 and 3.14**, verified noneditable wheel and
source-distribution tests, and published a new immutable tag plus wheel,
tarball and SHA-256 manifest. The committed workbook, existing v1.1.2
tag/release and user's modified local `Ligands.xlsx` were not altered.
NASolve Pine now declares the v1.1.3 Git tag as its install dependency;
the existing user-local NASolve `.venv` is **not automatically upgraded**.

The user earlier verified the clean candidate import and reported **21/21
focused NARestraints tests green**. The first full-suite run from the
wrong working directory returned **30 passed / 5 failed** solely due to
relative `examples/D3X3.pdb` and `examples/9L5Z.pdb` fixture paths;
rerunning from the clean NAR worktree was reported green (exact totals
not supplied). Actual Z:P native PostMR, the combined NASolve Phenix
numerical refinement and overall human Coot visual review subsequently
passed as described below. This does **not** validate the user's
uncommitted workbook edits or complete missing-component native B:S/K:X
tests; scientific controls remain in place.

## Local-workspace protection — mandatory

The sibling `../NARestraints` checkout was returned as branch
`feature/terminal-phosphate-op3-angles`, with uncommitted changes including
`examples/nucleic_acids.py`, `restraints/data/Ligands.xlsx`, macOS metadata
and the untracked Excel lockfile `restraints/data/~$Ligands.xlsx`.
**Do not checkout, reset, stash, clean, rebase, overwrite, pip-install/editable
from, or remove anything in that existing tree as part of this test.** The
uncommitted workbook may contain scientifically important unreleased work and
must not be treated as the same data as the committed packaged workbook.

For local validation, fetch the PR candidate and allocate an **independent
sibling worktree** such as `../NARestraints-pairfix`, using
`git -C ../NARestraints fetch` / `git -C ../NARestraints worktree add`.
Worktree creation only changes Git bookkeeping in the original checkout and
does not change its tracked/untracked scientific data. Alternatively, clone
the candidate into `~/NASolve-live-tests`.

Use the **same NASolve terminal and .venv** for the tests with a temporary,
process-local `PYTHONPATH` pointing at the clean candidate root *before*
`$PWD/src`. First record `restraints.__file__`, and confirm that it resolves
to the clean candidate, rather than to an older installed package or the dirty
sibling tree. Do not overwrite an installed NARestraints distribution before
this controlled check; record package version, branch commit and workbook
blob hash. Run the upstream focused and complete pytest suites using that
candidate, including tests under `tests/test_modified_pair_roles.py`.

## Corrected native Z:P replay — completed through PostMR

The user fetched the candidate, created an independent detached worktree
`../NARestraints-pairfix` at `f367a961cf7ba39425e455742ea5ef8fa5272c25`,
and supplied `PYTHONPATH="$PWD/../NARestraints-pairfix:$PWD/src"` to the
existing NASolve executor. The old failure was preserved as `run_001`.
The explicit `campaign retry` created **attempt_002**, which passed native
preflight and Phaser and returned **POSTMR_READY** at
`~/NASolve-live-tests/zp-paired-native-oiipj_t2/GZ11_ZP/AutoMR/run_002`.
The campaign reported frozen input integrity `OK` and paused before AutoSol.
The rerun transcript did not report a new TFZ; the original attempt's TFZ
12.9/LLG 210 remain the recorded native MR figures.

The user ran a separate **read-only audit** of the new
`run_002/PostMR/report.json`, its `prepared_model` and the actual
`narestraints_Std_padd.phil`. Returned evidence:

- `A:7=5CM`, `C:9=DG`, `A:19=DF`, `D:4=DA`, `A:12=DZ`,
  `B:4=DP`, **all six correct**.
- Exactly one restraint bond per intended Z:P contact:
  `P.N2/Z.O2`, `P.N1/Z.N3`, `P.O6/Z.N4`, **3/3**.
- No `restraint_geometry_override`; user did not request `force = G:C`.
- `requested_target_changes` includes A:19 `A1AAZ -> DF` with
  `basis=reviewed-deposition-to-pdb-code`.
- `sequence_family_audit.status=PASS`, `target_count=42`,
  `mismatches=[]`, scope explicitly **residue identities only**.
  Prepared-model SHA256:
  `69fe6cf642365ba5157095a4195e75d62894937913ce75e2ae0ca7916558c4af`.

This **closes the previously blocked native PostMR construction/NARestraints
contact-selection gate for Z:P**, but not effective Phenix geometry,
Rwork/Rfree, Coot visual review, source-native `1W5/1WA` normalization,
the remaining family matrix, human approval or release. Do not erase or
rewrite `run_001`; do not repeat `run_002` after it advances.

## AutoRefine blocker after successful Z:P PostMR — pending resolution

The user continued corrected native `GZ11_ZP/AutoMR/run_002` through the
conditional AutoSol boundary. The read-only report showed zero anomalous
candidates, `autosol_required=False`, no phase import and no iodine warnings.
The campaign advanced to `autorefine`.

The first native `--through autorefine` then returned
`AutoRefineError`: `phenix.pdb_interpretation` exited 1 while
`_prepare_terminal_phosphate_protection` was obtaining a pre-refinement
`.geo` file, **before refinement was started**. Its terminal error was:

```text
('A', 'U') A F 20
DA D   4    DF A  19
Sorry: Saenger class does not match residue names
```

The canonical W frame template at
`src/nasolve/data/restraints/5W6W_secondary_structure.eff` contains a
fixed `saenger_class = 20` `base_pair` for A:19/D:4, historically the
unmodified A:T-like pair, while native PostMR prepared A:19=DF
(2-thiothymidine) opposite D:4=DA. It also contains `saenger_class = 19`
at the newly modified A:7=5CM/C:9=DG pair. These legacy fixed-class
annotations are suspect when reused with sequence-level modified targets.
**This is a separate secondary-structure compatibility problem, not a
regression in the repaired Z:P hydrogen-bond contacts**, which passed their
independent native PostMR audit.

Next gate: read-only inspect the *actual run-local* 17-pair secondary
template against the prepared model and enumerate every modified site using
hardcoded Saenger classes. Then design a **scoped, audited, per-run**
secondary-structure adjustment for affected pairs, preserving constraints
through compatible NARestraints atom-role recipes (or blocking when no
chemically reviewed replacement exists). Do not edit the frozen plan,
postmr outputs, historic attempts, site-specific phosphate policy, or
remove all secondary-structure restraints. Do not silently substitute
`saenger_class=0` or disable hydrogen bonds as a passing shortcut.

Actual round/checkpoint creation has not been observed and no Rwork/Rfree
was returned; this error happened during proactive geometry generation.
The campaign is `COMPLETE_WITH_FLAGS` / `BLOCKED`. Resume only through
an explicit fresh retry or a scientifically reviewed, separately frozen
new campaign, not by overwriting `run_002` or its report.

## Native attempt_003 — numerical refinement success, human gate still open

After isolated candidate [NASolve PR #24](https://github.com/vecchioni-lab/NASolve/pull/24)
was fetched into a **detached** `../NASolve-saengerfix` worktree at
`6f93c43`, with `../NARestraints-pairfix` providing the corrected
NARestraints, the user ran focused regression (**34 passed**) and full
NASolve regression (**961 passed, 224 subtests passed, 93.84 seconds**).
Tests were executed using the NASolve project's existing `.venv`,
`PYTHONPATH` pointing to the isolated code, and the committed NARestraints
workbook; original dirty NAR and NASolve checkouts were preserved.

The user performed `campaign retry` for the immutable frozen
`~/NASolve-live-tests/zp-paired-native-oiipj_t2` campaign, creating
`attempt_003` and **new** `GZ11_ZP/AutoMR/run_003`. With both patched
libraries in `PYTHONPATH`, native preflight, Phaser and PostMR completed
and paused at AutoSol. The read-only native `run_003/PostMR/report.json`
audit returned:

- `base_pair_count=17`, `retained_saenger_count=15`,
  `replaced_saenger_count=2`, `explicit_new_pair_count=2`.
- A:7/C:9 5CM:G mapped to **GC/3 explicit H bonds**;
  A:19/D:4 DF:A to **AT/2 explicit H bonds**.
- The run-local secondary file contained exactly 15 Saenger blocks; both
  reviewed modified pairs appeared in the run-local pair input.
- `restraint_geometry_override` absent, D:1 terminal-phosphate OP3
  authorization preserved, and sequence-family mismatches empty.
- The actual source template, model and older `run_001`/`run_002` records
  were not modified.

The campaign then continued to the AutoSol boundary and paused at AutoRefine.
A subsequent `--through autorefine` executed native Phenix and returned:

```text
GZ11_ZP: SOLVED; Numerical refinement criteria passed; inspect the model and maps before approval
Campaign execution: COMPLETE; frozen input integrity: OK
Run: .../GZ11_ZP/AutoMR/run_003
Checkpoint: refine-001
```

**Human follow-up on refine-001:** user launched
`nasolve show ... --checkpoint refine-001`. The CLI printed
`AutoRefine/round_001/refined_001.pdb` and `refined_001.mtz` as
explicit model and map sources, and Coot launched under
`CootGUI/autorefine/refine-001`. The user subsequently reported that
the refinement **looks great in Coot**, with bonds and planes present,
and planes slightly wobbly but acceptably so; no stronger restraint
forcing is requested. Record **HUMAN_INSPECTED_PASS — visible
model/bond/plane quality**, not numerical or experimental endorsement.
The user also reported an apparent MR-model display despite CLI
selection of the refined checkpoint; provenance output identifies the
correct refined paths. Treat that as an unconfirmed GUI/window/source
display discrepancy, not evidence of a falsely selected checkpoint.
A separate CLI usability improvement should make bare `nasolve show`
target the just-completed single-dataset campaign run.

**Refinement metrics not yet copied into this ledger:** Rwork/Rfree,
exact .geo deviations and individual-site electron-density/clash assessments
should be read from the checkpoint. The campaign is not permission to
deposit or claim these modified bases exist in GZ11 reflections.
Neither B:S, K:X nor D:T has yet cleared its own native matrix gate.
NARestraints v1.1.3 is published; the separate NASolve Saenger-overlay
PR #24 remains a candidate pending final integration into Pine.
A passed W integration is not a proxy for unavailable B:S/K:X
component dictionaries.

## Five independent native W challenges

A repeatable **staging-only** helper is available in released NARestraints
source (introduced in upstream PR #4) at
`scripts/stage_nasolve_pair_matrix.py`. Called from the NASolve checkout
with `--nasolve-root "$PWD"`, it copies the known GZ11 MTZ/CIF/HTML and
`MR_frames/5W6W/5W6W_noPO4.pdb` into a new, disjoint
`~/NASolve-live-tests/nar-pair-matrix-*` directory and hashes all copies.
It writes `nasolve.txt` per member and a `staging-manifest.json`. **It does not
plan a campaign or run Phenix/Coot**, modify the donor, use the original dirty
NAR checkout, or modify the earlier frozen Z:P attempt.

All members use the same 42-residue W model, the reviewed
`w-metal-scaffold` reference, GZ11 diffraction inputs, and off-pair annotated
sequences:

```ini
[sequences]
A = GAGCAG(5CM)CTGTATGGACA(A1AAZ)CA
C = G(DG)CTGCT
```

These keep A:7(5CM):C:9(DG) and A:19(A1AAZ->DF):D:4(DA) paired while
testing the two-, three- and five-character annotated codes. The independent
standard W pair is always A:12/B:4. Each member differs **only** in its ordered
`pair =` request; never set `force = G:C` to manufacture a passing result.

| New member | Ordered pair | Target component labels at A:12/B:4 | Gate |
| --- | --- | --- | --- |
| A_T_CONTROL | A:T | DA / DT | Canonical A:T control; DA is ordinary DNA adenine, not D-class 1AP |
| D_T | D:T | 1AP / DT | The separate diaminopurine-like D:T template (D sheet) |
| B_S | B:S | IGU / S6G | Verify B/S workbook mappings and dictionary readiness before native PostMR |
| Z_P | Z:P | DZ / DP | Repeat the failed Z:P chemistry under the corrected upstream role orientation |
| K_X | K:X | CGY / DX | Verify X/K workbook mappings and dictionary readiness before native PostMR |

Component names above are the currently registered NASolve aliases, not a
claim of ligand-dictionary availability. The helper reports missing
`src/nasolve/data/ligands/<CODE>.cif` files. **At the 2026-10-07 Pine
checkpoint, IGU, CGY and DX are not packaged**, so B:S and K:X can legitimately
block at PostMR rather than passing natively. Missing/unsupported definitions
must not be invented, downloaded implicitly, or relabeled as a pass. Such a
blocker distinguishes recipe-layer qualification from native structure
preparation. D:T and Z:P have packaged targets.

Additional NARestraints recipe audit: `I:C` has an explicit AT-shaped entry,
and opt-in noncanonical `A:G` and `G:T` have separate recipes. Their atom-role
compatibility is **not yet established by this five-case W matrix**. Track
them as separate workbook/recipe follow-ups rather than silently equating
their labels with the GC family. A `D:A` recipe does not exist; never silently
substitute it for `D:T` or the canonical `DA:T` control.

## Sequential gate and provenance requirements

1. **Upstream unit/workbook gate:** run full candidate NARestraints regression
   from its clean checkout and inspect workbook-backed B:S/Z:P/K:X/D:T results,
   contact atom selections, ordered/reversed geometry and stacking planes.
   Record version, commit, workbook identity and full test summary; inspect
   any failures before publishing.
2. **Freeze the matrix once:** after reviewing the helper's missing-dictionary
   list, stage its five dataset copies; use NASolve `campaign plan` on that
   fresh root with `--preset 5w6w`, explicit `--frames-dir` and the
   process-local clean NARestraints import. Check that all five have frozen
   input integrity OK and no inherited `force` override. A blocked member
   remains a useful diagnosis and must not stop evidence collection for others.
3. **Native execution one boundary at a time:** run through `preflight`,
   `phaser`, then `postmr` (not full-auto). Capture actual Phaser TFZ/LLG and
   report status for each. For every PostMR pass verify prepared A:12/B:4
   identities, A:7 5CM, A:19 DF, C:9 DG, explicit A1AAZ->DF provenance,
   required target dictionaries, three-contact role mappings and absence of
   upstream `N2` misuse. Preserve blocked logs as failures, not warnings.
4. **Refinement only after compatible preparation:** with stable data/Free-R,
   run conditional AutoSol and AutoRefine for eligible members. Do not rerun
   historic successes. Record numerical Rwork/Rfree, dictionary authority,
   geometry warnings and any unmodeled/unsupported chemistry separately.
5. **Human inspection (not an automatic green checkbox):** inspect all eligible
   models/maps in Coot. Explicitly check A:12/B:4 hydrogen-bond candidates,
   A:7/C:9 and A:19/D:4 modified pairs, local sugar/phosphate continuity,
   P/OP oxygen geometry, potential clashes and stacking. Review the exact
   prepared restraint PHIL and the `.geo` geometry audit rather than
   assuming a low Rfree validates the synthetic chemistry. Record outcome as
   `INSPECTED_PASS`, `INSPECTED_REVIEW` or `INSPECTED_FAIL`, with the
   reviewing human, date, code SHA, input/run/checkpoint and evidence paths.
   Never set `user_approved` based on a numerical solver result alone.

**This is a software-integrity/native-compatibility experiment on diffraction
from an unrelated dataset.** A numerical solution does not establish that the
actual GZ11 crystal contains the hypothesized B:S, K:X, Z:P or D:T chemistry,
nor authorize structural deposition. No change to historical model/map data
or reflection/Free-R files is implied.

## Human-test trackers and stale-status handling

The earlier **[Construct Registration human live-check queue](construct-registration-live-checks.md)**
is genuine: it records completed shadow Scout checks but leaves runtime Scout,
Topo Net surgery, symmetry seams and multiplicity tests intentionally pending.
It is **not** replaced by the chemistry tests above. Likewise, the
[GUI live checks](gui-live-checks.md) are future UI/human acceptance tests,
not evidence that GUI features are currently live. [DOHU validation](validation-dohu.md)
is a historical milestone, not the current project-wide gate.

This chemistry matrix is the current **P2/NARestraints human/native complement**
to those separately scoped queues. It must be visible in the
[development handoff](development-handoff.md) until tested, and must not
automatically close Pine P5 prepared-nonstandard or future Scout/GUI gates.

### Execution ledger (do not mark complete without observed receipts)

| Gate | Status at this handoff | Evidence / required next observation |
| --- | --- | --- |
| Existing Z:P donor native MR | **PASSED** | TFZ 12.9, LLG 210.0, frozen inputs intact in retained run_001 |
| Existing Z:P donor native PostMR | **BLOCKED** | Z assigned G-role, unmapped N2; original logs retained |
| Corrected in-memory Z:P role probe | **PASSED (probe only)** | Three anchors, inverse order and stacking-plane mapping; package unchanged |
| Upstream NARestraints 1.1.3 / workbook regressions | **RELEASED, CI PASS 3.10/3.12/3.14** | main a9264f9; immutable tag, wheel/tarball/SHA256SUMS; 21/21 focused local; full worktree-cwd run reported green |
| Fresh 5-case matrix stage/plan/native run | **NOT RUN** | Each frozen case has its own immutable files and status |
| Z:P native replay and contact/identity audit | **PASSED THROUGH POSTMR** | Preserved run_001; attempt_002 run_002; six correct identities, three correct pair contacts, A1AAZ->DF, 42 targets zero mismatches, no force |
| Z:P AutoSol / first AutoRefine continuation | **AutoSol SKIPPED; AutoRefine BLOCKED before refinement** | No anomalous candidate, then A:19 DF / D:4 DA failed frozen W Saenger-20 class check during Phenix geometry preparation |
| Z:P corrected W native AutoRefine `run_003` | **SOLVED (numerical), HUMAN REVIEW PENDING** | Campaign COMPLETE, frozen integrity OK, checkpoint `refine-001`; full 961/224 regression; no Rwork/Rfree copied into ledger yet |
| Other family matrix | **NOT RUN** | D:T, B:S, K:X and A:T control still require independent native tests; dictionaries may BLOCK |
| Human Coot overall model/bond/plane review | **INSPECTED_PASS (reported by user)** | refine-001 opened; bonds and planes present, acceptable moderate plane deviations; site-resolved maps/.geo still unreported |
| Site-resolved maps, contacts and .geo audit | **PENDING** | Not inferred from overall Coot inspection; experimental chemistry unverified |
| Pine P5 geometry-diverse nonstandard test | **SEPARATELY PENDING** | Not discharged by W-only modified-base matrix |
| Topo/Registration/GUI human cases | **AS RECORDED IN THEIR QUEUES** | No status change from this note |
