# NASolve development handoff — current state

Updated **2026-10-09**. **Active candidate: `cedar`; integration branch: `pine`.**
Finish Cedar's existing validation gates and merge it into Pine, then retire
Cedar. Finish the bounded Pine scientific gates, merge [Pine PR #23](https://github.com/vecchioni-lab/NASolve/pull/23)
into `main`, then the **blind AlphaFold geometry baseline**, then
**operational Scout**. No GUI/Topo Net implementation is a prerequisite.
This is the compact active handoff, not a chronology. The complete previous
handoff is [archived](history/development-handoff-2026-10-08-pre-consolidation.md).

## Executive state

| Workstream | Verified result | Remaining gate |
| --- | --- | --- |
| NARestraints | **v1.1.3 released and installed** ([release](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3), `main a9264f9`); Python 3.10/3.12/3.14 CI, wheel/sdist and SHA256SUMS passed. Active user .venv imported 1.1.3 from site-packages; workbook SHA-256 `94a66af42081188fd95f3fdcbe04cb01bed8f1826772597272320a8b4c0433b2`. | Combined Z:P/B:S/K:X/D:T native challenge pending; raw CCD source chemistry is found and Coot construction validated, but refinement parameters still need native proof. |
| Modified-W Saenger overlay | [NASolve PR #24](https://github.com/vecchioni-lab/NASolve/pull/24) **MERGED into Pine** at `0017081`. Exact reconciled branch `612881d` passed **40 focused + 2 subtests** and **967 full + 226 subtests (85.38 s)**; combined D:T/B:S(IGU:IMC)/Z:P/K:X plus 5CM:G/DF:A workbook regression passed. Earlier native Z:P `run_003/refine-001` SOLVED numerically with user Coot visual PASS. | No combined-family native execution yet. Resolve IGU/IMC/CGY/DX monomer definitions through existing libraries and validated generic preparation before freezing that challenge. |
| Coot viewing | [PR #25](https://github.com/vecchioni-lab/NASolve/pull/25) **merged** into Pine at `e8613bf`; isolated **59 focused + 30 subtests**, **960 full + 226 subtests**. User fast-forwarded their Pine checkout, manually selected `run_003`, then confirmed **bare `./nasolve show` works in real Coot**, with screenshot. | **USER LIVE PASS** for pathless view of a selected run. Auto-activation following *new* single-dataset execution is regression-tested, not independently live-trialled. |
| P2 modified-component preparation | Published at `dec56c2`; **276 focused + 20 subtests**, **927 full + 224 subtests** at that code point. Source-derived `1W5→DZ` and `1WA→DP` preparation implemented. | True native source-component/DP preparation and refinement with artifact provenance; fixture-only and W Z:P runs do not close this. |
| Campaigns / full auto | Ordinary guarded MR→PostMR→conditional AutoSol→refinement and immutable checkpoints work. Separate EA/DiU/Q5cm/QiC full-auto campaign reached numerical SOLVED for all four, preserving EA MR_REVIEW and QiC provisional (not user-approved) selection. | Bounded evidence review and user-veto/resume where still missing; do not rerun passed cohorts merely to refresh docs. |
| Prepared nonstandard P5 | Explicit per-dataset PDB/sequence and mixed schema-2 campaigns implemented and fixture-tested. | Small **3–5-member real geometry-diverse** native smoke check; W-only successes cannot substitute. |
| Scout / registration / Topo / GUI | Registration/Scout shadow primitives and earlier scoped checks are recorded. | Operational Scout, symmetry surgery, Topo and GUI remain separate future work, **not** claimed complete. |

**Integrated code regression:** the last pre-merge PR #24 head contained
PR #25 pathless `show` and the NARestraints v1.1.3 dependency pin; this
combined head returned **967 tests + 226 subtests PASS** before squash
merge. The post-merge Pine checkout has not been rerun on the user's terminal.
One earlier first-pass mixed fixture with S6G instead of the lab's IMC correctly
failed closed as B:G; the reviewed IMC replacement passed. Neither unit
tests nor numerical `SOLVED` establish experimental chemistry or deposition
approval.

## Immediate next scientific work — one bounded sequence

1. **Next engineering slice — library-first generic monomer resolver.**
   With [PR #24](https://github.com/vecchioni-lab/NASolve/pull/24)
   merged, the combined-family workbook regression is green, but four
   monomer dictionaries **IGU, IMC, CGY, DX** are not bundled in NASolve,
   but Phenix 2.2.1's `chem_data/chemical_components` contains all four.
   User ran **real headless Coot**: dictionaries loaded (41–44) and all four
   monomers constructed (0–3). Each CCD graph passes NASolve identity
   validation; none contains numerical geometry parameters. A **Cedar draft
   patch** now resolves these from configured Phenix before Coot, with
   SHA256 source snapshots and a fail-closed numerical ReadySet gate.
   **Latest user-local validation (2026-10-09):** tested commit
   `1443979b2308e4a2e507f0859370b44e0e124a86`, including the Phenix symlink
   fix: focused Cedar **16 passed + 31 subtests (2.45 s)**; full suite
   **983 passed + 257 subtests (80.81 s)**. Both ran from `NASolve-cedar`
   with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"`
   and `../NASolve/.venv/bin/python -m pytest -q`; the focused run selected
   `tests/test_cedar_ccd_resolver.py`. The earlier isolated relocation check
   also passed. Native PostMR/ReadySet and combined-family scientific
   validation remain pending; the regression receipt does not close them.
   **Reassess the nine bundled entries by evidence:** the
   [ligand audit](modified-component-preparation.md#bundled-ligand-audit-2026-10-09)
   separates actual overrides, identity bridges, construction recipes and
   unchanged supplier copies. 5CM is unchanged upstream data; 5IU's long-bond
   failure was the corrected C5/C5' parser bug. C38 and 5IU exactly match
   the user's installed Phenix 2.2.1-6174 sources by SHA-256. S6G also matches
   after removing trailing whitespace, with no chemical difference. These
   remain candidate generic sources, with construction recipes and
   numerical-generation checks retained.
   **DE's old geometry
   repair remains unresolved**; do not label it validated simply because it
   is bundled. Preserve 1AP/DZ/DP profiles and `A1AAZ→DF`. Current code still
   loads all nine locally and fails closed when missing/invalid; no resource
   or guard is removed by the audit. `OHU.cif` stays local-first, non-curated.
   The expanded Cedar matrix audits all nine source paths and Coot loaders;
   Python regression evidence does not certify native chemical geometry.
   Lab Q/DQ denotes S6G; lab S/DS denotes N-linked IMC, distinct from
   C-linked hachimoji S. Q works today; DQ/S/DS aliases are not implemented.
   Preserve the mandatory 1W5/1WA -> DZ/DP overrides. The two Phenix paths
   per component are verified aliases of one file (`python3.1 -> python3.11`).
   Cedar now deduplicates resolved paths while rejecting separate competing
   files. The fix now has full local regression coverage; next compare
   DF/A1AAZ contents with the component-label bridge accounted for.
   Placement recipes and dictionary-source selection have separate purposes; see the
   [scope decision](modified-component-preparation.md#lab-labels-and-placement-scope).
   Prefer validated Phenix/CCD monomers only for non-curated components, and
   where supported produce an **audited, frozen derivative**, never
   fabricate bonds/stereochemistry from NARestraints' atom-role mappings.
   Keep exceptional local recipes only for demonstrated broken cases.
   Review prospective HelixWeld/HelixMeld implementations before making
   them providers; no verified integration yet. Pin/run against released
   NARestraints v1.1.3 with exact import verification; don't edit the
   user's dirty workbook or historical native models.
2. **Attempt one simultaneous four-family W model first**, as explicitly
   requested by the user on 2026-10-08. Use distinct original W paired sites:
   **D:T at A:5/C:11** (1AP/DT), **B:S at A:6/C:10** (IGU/IMC),
   **Z:P at A:12/B:4** (DZ/DP, existing `pair=Z:P` route), and
   **K:X at A:20/D:3** (CGY/DX). Keep the prior off-pair A:7/C:9
   **5CM:G** and A:19/D:4 **DF:A** simultaneously. These sites align
   their source A:T/G:C/C:G templates with reviewed NARestraints roles,
   but are still **proposed design intent**, not frozen/validated.
   The Saenger overlay should retain **12 original Saenger blocks and
   replace 5 with explicit pairs**; the central Z:P stays in Std_padd.
   **Before any native run**, locate source-verified `IGU`, `IMC`, `CGY`, `DX`
   monomer dictionaries (absent from committed NASolve resources) and
   audit the actual W model/42-site sequence targets, restraint interfaces,
   atom names and phosphate policy. Do not invent CIFs, force chemistry
   to G:C, or silently downgrade to the old five-independent-matrix plan.
   One *new* frozen single-member campaign, one stage boundary at a time,
   with preserved failures and human Coot/.geo checks; independent A:T,
   D:T, B:S, Z:P, K:X datasets remain a **diagnostic fallback**, not
   today's required first trial. **D:A is unsupported**; D:T is the
   reviewed three-hydrogen-bond D-family recipe, while `DA` means
   ordinary DNA adenine.
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

The exact **combined-first site layout**, candidate chain sequences,
dictionary sourcing gate, optional independent controls, immutable Z:P
attempt history and human-verdict limits live in the
[native modified-pair ledger](native-modified-pair-live-validation.md).
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

- **Read the relevant doc swarm before inferring context:** start here and
  follow the documentation map to subsystem contracts and prior evidence.
  Verify historical claims against the actual commit and returned output.
- **One active development branch and one everyday checkout.** Follow the
  [branch lifecycle](collaboration.md#branch-and-worktree-lifecycle): merge when
  the scoped scientific gates support it, then retire completed branches and
  disposable worktrees promptly. Additional worktrees are bounded exceptions.
  **Cleanup verified user-local on 2026-10-08:** PR #24/#25 worktrees and
  remote branches are retired after local-file audits and exact file-tree
  equivalence with their squash merges in Pine. Their original commits remain
  accessible through the merged PR histories. Nine historical local branches
  were removed only after proving full containment in Pine; the stale temporary
  worktree registration was pruned with its commit preserved in main/Pine.
  Local `main` was fast-forwarded to `fec66eb`. The final worktree inventory
  contains only the original `NASolve` checkout on Pine and active detached
  `NASolve-cedar`; retire Cedar after its existing gates and integration.
  On 2026-10-09 the clean `NARestraints-pairfix` checkout and merged role-fix
  remote branch were also retired after verifying equivalence with v1.1.3;
  original NARestraints remains protected. `NASolve-lab-notes` is intentionally
  retained as a private notebook at the user's request.
- **One terminal action per user turn** for live NASolve debugging, then
  inspect the output before proceeding. Preserve the user's dirty
  `../NARestraints` tree (including unpublished `Ligands.xlsx` and Excel
  lockfile), the original NASolve
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
