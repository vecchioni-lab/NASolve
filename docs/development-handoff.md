# NASolve development handoff — current state

Updated **2026-10-08**. **Working branch: `pine`.** Finish the bounded
Pine scientific gates, merge [Pine PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
into `main`, then the **blind AlphaFold geometry baseline**, then
**operational Scout**. No GUI/Topo Net implementation is a prerequisite.
This is the compact active handoff, not a chronology. The complete previous
handoff is [archived](history/development-handoff-2026-10-08-pre-consolidation.md).

## Executive state

| Workstream | Verified result | Remaining gate |
| --- | --- | --- |
| NARestraints | **v1.1.3 released** ([release](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3), `main a9264f9`); Python 3.10/3.12/3.14 CI, wheel/sdist and SHA256SUMS passed. Corrected Z:P and K:X role/stacking orientation; B:S and D:T retained. Bundled workbook unchanged. | Independent native B:S/K:X/D:T matrix; locally installed package may still be v1.1.2. |
| Modified-W Saenger overlay | [NASolve PR #24](https://github.com/vecchioni-lab/NASolve/pull/24) in **separate candidate branch, not yet in Pine**. Isolated **34 focused** and **961 full + 224 subtests** passed. Native `GZ11_ZP` `run_003/refine-001` reached **SOLVED (numerical)**; user inspected bonds/planes positively in Coot. | Reconcile PR #24 with latest Pine and 1.1.3 dependency, rerun focused/full tests, integrate after review. |
| Coot viewing | [PR #25](https://github.com/vecchioni-lab/NASolve/pull/25) **merged** into Pine at `e8613bf`; isolated **59 focused + 30 subtests**, **960 full + 226 subtests**. User fast-forwarded their Pine checkout, manually selected `run_003`, then confirmed **bare `./nasolve show` works in real Coot**, with screenshot. | **USER LIVE PASS** for pathless view of a selected run. Auto-activation following *new* single-dataset execution is regression-tested, not independently live-trialled. |
| P2 modified-component preparation | Published at `dec56c2`; **276 focused + 20 subtests**, **927 full + 224 subtests** at that code point. Source-derived `1W5→DZ` and `1WA→DP` preparation implemented. | True native source-component/DP preparation and refinement with artifact provenance; fixture-only and W Z:P runs do not close this. |
| Campaigns / full auto | Ordinary guarded MR→PostMR→conditional AutoSol→refinement and immutable checkpoints work. Separate EA/DiU/Q5cm/QiC full-auto campaign reached numerical SOLVED for all four, preserving EA MR_REVIEW and QiC provisional (not user-approved) selection. | Bounded evidence review and user-veto/resume where still missing; do not rerun passed cohorts merely to refresh docs. |
| Prepared nonstandard P5 | Explicit per-dataset PDB/sequence and mixed schema-2 campaigns implemented and fixture-tested. | Small **3–5-member real geometry-diverse** native smoke check; W-only successes cannot substitute. |
| Scout / registration / Topo / GUI | Registration/Scout shadow primitives and earlier scoped checks are recorded. | Operational Scout, symmetry surgery, Topo and GUI remain separate future work, **not** claimed complete. |

**Do not combine these test totals:** PR #24 and PR #25 passed in *different
isolated checkout heads*. The post-integration Pine composition has not
been reported through a fresh full suite. Numerical `SOLVED` is not
experimental-chemistry confirmation, user approval or deposition authority.

## Immediate next scientific work — one bounded sequence

1. **Integrate the proven modified-W overlay.** [PR #24](https://github.com/vecchioni-lab/NASolve/pull/24)
   still diverges from current Pine (including the NARestraints `v1.1.3`
   pin and pathless-show merge). Reconcile code/docs without overwriting
   native attempts or dirty worktrees. Execute focused and full regression on
   the **actual combined head**, verify exact NARestraints import/version from
   NASolve's environment, and merge only once green. Do **not** remove
   Saenger protection globally or weaken D:1 terminal-phosphate policy.
2. **Stage the independent W pairing matrix:** canonical **A:T control**,
   **D:T**, **B:S**, **Z:P** and **K:X**. This is **one frozen campaign with five
   distinct dataset members**, *not* one molecule simultaneously carrying all
   four experimental pairs. Each member differs at A:12/B:4, while retaining
   A:7 5CM:G and A:19 DF:A for common modified-context coverage. The
   released NARestraints source has staging-only
   `scripts/stage_nasolve_pair_matrix.py`; review its missing-dictionary
   manifest *before planning*. At last audit **IGU, CGY and DX** native CIFs
   were absent from NASolve, so B:S/K:X may legitimately **BLOCK**. No
   invented monomers or silent `force = G:C`. Run stage boundaries
   sequentially, keep every result and human-inspect eligible models.
   The **D-family test is D:T (1AP/DT)**; **DA/DT** is the *canonical A:T*
   control. There is **no registered D:A pairing recipe**.
3. **Close the independent P2 source-native gate** (`1W5→DZ`,
   `1WA→DP`) with actual source components and verified dictionaries,
   source-to-target atom mapping, raw preservation and native refinement.
   This is not the same as already successful Z:P synthetic-target model.
4. **Finish the bounded Pine close-out:** retain existing GZ11 and multi-member
   saved receipts; resolve remaining exact effective-dictionary evidence (P1),
   saved normal-GZ11 evidence (P3), and limited campaign human-veto/current-
   pointer evidence (P4), plus **P5** geometry-diverse real smoke check.
   Then final integrated tests/review **P6**, followed by [PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
   merge/ancestry verification **P7**. Do not clean, reset or prune original
   scientific artifacts to retire branches.

The exact five-case recipes, alias names, staging procedure, individual
scientific gates, immutable Z:P attempt history and human-verdict limits live
in the [native modified-pair ledger](native-modified-pair-live-validation.md).
The [modified-component contract](modified-component-preparation.md) owns
1W5/1WA mapping and source-preservation rules. [Campaign execution](campaign-execution.md)
owns CLI semantics; [full-auto checkpoint](full-auto-patch-handoff.md) retains
the completed four-member validation.

## Preserved W native evidence and user review

The original frozen synthetic-target dataset is
`~/NASolve-live-tests/zp-paired-native-oiipj_t2`. It uses **real GZ11
diffraction observations** but altered target chemistry; it is **not**
evidence the experimental crystal contained the tested modifications.

- **`run_001`:** retained Z:P PostMR **BLOCKED** by the former reversed
  role mapping (Z lacked G-like N2). Native Phaser TFZ **12.9**, LLG **210**.
- **`run_002`:** corrected NARestraints Z:P PostMR **PASS**: expected
  `P.N2/Z.O2`, `P.N1/Z.N3`, `P.O6/Z.N4` contacts, all 42 target
  identities checked, no `force` override. First AutoRefine **BLOCKED**
  before refinement by old W Saenger classes at modified 5CM:G and DF:A.
- **`run_003`:** PR #24 candidate; frozen integrity **OK**, 17 template
  pairs → **15 unchanged Saenger + 2 explicit modified** (5CM:G GC/3 bonds;
  DF:A AT/2). D:1 phosphate protection retained, sequence-family
  mismatches empty, AutoSol correctly skipped; native AutoRefine returned
  **`SOLVED`, `refine-001`**. User's Coot inspection reported **good bonds
  and planes**, tolerable nonideal planarity: **INSPECTED_PASS for overall
  visual software integration**, not site-resolved density or experimental
  chemistry. Exact Rwork/Rfree, `.geo` and per-site map/clash metrics are
  still to be recorded if needed.
- **`./nasolve show`:** after PR #25 integration the user selected
  `run_003` as their active workspace and confirmed bare `show` launched
  the expected model in Coot. **Live usability gate passed**.

**Separately parked geometry question:** user noticed tilted/directional
hydrogen-bond contacts in the displayed modified pair (named N1/N3 and
O4/N6 sites). First verify the exact donor–H–acceptor assignment, atom
definitions, existing restraint angular terms and achieved geometry before
deciding whether directional terms are appropriate. **Do not simply fix a
heavy-atom angle at 180°, enforce flat base planes, or edit `run_003`.**
Not a blocker for `show` or for the successful native integration.

## After Pine: blind AlphaFold baseline, then operational Scout

The user requested this order on 2026-10-07. Use the existing prepared-
nonstandard path with **frozen** supplied predictions, complete chain-labelled
sequences and untouched diffraction/Free-R; audit chain/residue correspondence,
coordinate/ASU completeness, model confidence/B factors and input metadata.
Predicted coordinates are *unseen candidate models*, not solved truth.
Do not consult outcome structures during blind candidate selection. Preserve
every success and failure; later hypotheses get new attempts.

Then promote Scout along the
[registration contract](construct-registration.md) and
[human live-check queue](construct-registration-live-checks.md); keep guided
ambiguity, symmetry seams and topology edits guarded. A GUI/Topo Net and
[metal restraint builder](metal-restraint-builder.md) are separate later scopes.

## Work discipline and doc ownership

- **One terminal action per user turn** for live NASolve debugging, then
  inspect the output before proceeding. Prefer isolated Git worktrees
  for candidates. Preserve the user's dirty `../NARestraints` tree (including
  unpublished `Ligands.xlsx` and Excel lockfile), the original NASolve
  untracked files/patches, all immutable numbered runs, maps and Free-R.
- Do not represent an unrun test as passing. Keep native-tool receipt,
  chemical identity, numerical statistics and human Coot verdict as
  separate fields. Confirm environment imports instead of assuming the
  v1.1.3 metadata pin upgraded a preexisting `.venv`.
- **This file** owns current priorities/results; the
  [documentation map](README.md) routes to active subsystem contracts;
  the [native ledger](native-modified-pair-live-validation.md) owns exact
  pair-matrix evidence and per-member status. Earlier full chronology
  is preserved [in history](history/development-handoff-2026-10-08-pre-consolidation.md)
  and Git. Do not re-append old session logs here.
