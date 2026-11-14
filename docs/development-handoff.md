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
| NARestraints | **v1.1.3 released** ([release](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3), `main a9264f9`); Python 3.10/3.12/3.14 CI, wheel/sdist and SHA256SUMS passed. Corrected Z:P and K:X role/stacking orientation; B:S and D:T retained. Bundled workbook unchanged. | One combined Z:P/B:S/K:X/D:T native stress run; verify old local .venv version and missing IGU/IMC/CGY/DX CIFs first. |
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
One earlier first-pass mixed fixture with S6G instead of Benner IMC correctly
failed closed as B:G; the reviewed IMC replacement passed. Neither unit
tests nor numerical `SOLVED` establish experimental chemistry or deposition
approval.

## Immediate next scientific work — one bounded sequence

1. **Next engineering slice — library-first generic monomer resolver.**
   With [PR #24](https://github.com/vecchioni-lab/NASolve/pull/24)
   merged, the combined-family workbook regression is green, but four
   monomer dictionaries **IGU, IMC, CGY, DX** are not bundled in NASolve.
   NASolve currently requires a local `CODE.cif` before Coot parent-overlap,
   whereas ReadySet normally runs *after* that placement. Resolve existing
   validated Phenix/CCD monomers before asking for curated overrides, and
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

## Separate Willow work — 2026-11-14

**Willow update W65; next W66.** Human W-numbers and exact code provenance live
in the [audited roadmap](topostitch-roadmap.md); its JSON is the one status queue.
The [intent record](topostitch-intent.json) lists implemented owners but grants no
runtime authority. The [periodic guide](topostitch-periodic.md) and
[bend-preview guide](topostitch-preview.md) retain exact commands, native failures,
versions, historical validation and scientific limits. Git retains earlier handoffs.
Do not restart completed probes merely because their chronological notes were
removed here.

**Current edge:** W56 freezes explicit representative-image proposals with unchanged
source/discovery/registration and anchored replay. W57 displays them through the
existing installed `nasolve-topostitch-view`: all atoms, logical ownership, exact
edge-image endpoints, unit cell, declared boundaries and missing scope. Its
before/after comparison is read-only; no replacement ASU, chemical bond, approval
or checkpoint is written. Full Willow: **1,630 plus 229 subtests**; focused57;
installed/relocated424, six helps, lean import and 3.10 syntax. Public and legacy
replay agree exactly. JavaScript DOM/canvas checks pass, but actual browser/user
visual review remains open after the earlier local-file automation policy block.

**W59 addition:** the existing graph owner now calculates representative images
along an explicitly chosen acyclic set of links, with one fixed anchor per component.
It preserves exact path order and full graph winding; no partner/tree/cut is inferred.
Two predeclared public alternatives pass packet/view/scattering observations but
remain unselected. Their partial topology is not a complete ASU or chemistry proof.

W60 retains those chosen edges/anchors in a `topostitch-forest-proposal` request
through the existing packet command. Reopening derives the same images and verifies
compact selection provenance; direct-image packets/scenes remain exact. The viewer
shows the fixed logical sites and chosen links. This is proposal intent, not review.

W63 adds an optional authenticated source-native link comparison to those packets
and the viewer. Each public cut moves two existing O3′–P bonds across the proposed
ASU boundary that are absent from the partial declared graph. Exact-image distance
and source P/OP1/OP2 are preserved. Source symmetry bonds and surrounding angle/
exclusion policy remain unqualified. Source interpretation is evidence, not full
intended topology; the observer neither extends the graph nor activates a bond.
One complete Phenix 2.2.1-6174 source capture passed (no optimization/refinement);
initial input/output-parent setup refusal is preserved. P04 is partial for this
observation only. Exact hashes, commands and limits are in the W63 periodic guide.

W64 lets the existing view compare 2–8 explicit same-source/graph packets through
`--compare`, with human Cut numbers and one camera/scale. Switching refreshes native
seams/provenance and clears old atom/edge inspection. No packet changes or saved
human decision; legacy scenes are exact. Public replay and actual JavaScript
interaction controls pass, but rendered/browser review is still open.

W65 adds saved preferences (prefer cut / keep original / needs revision) and
`--preference` readback bound to the exact ordered comparison. Backend validation
replays explicit packet paths; no model/checkpoint selection or authenticated
approval is implied. The old comparison/scene stays exact. Actual JavaScript
exports validate after relocation; browser downloads/human review remain open.
Existing Pine/Campaign record and checkpoint owners will consume this evidence;
no parallel history or model writer was added.

**Next bounded work:** actual browser cut inspection, preference download and human review
still need qualification. W61 completed the two read-only W54 failed-point reviews
under one common complete recipe: selected/core pair and scalar geometry improve,
but individual packing/torsion/plane regressions remain visible. Original FAILED
outcomes persist; no optimizer rerun, candidate or acceptance. See the W61 preview
guide audit. W62 now proves exact labelled group-image permutations/inverse lattice
shifts and complete atom ownership for explicit proposals, with independent point
binding. Special-position weights, ADP serialization and physical unique-atom
identity remain separate. Continue P02 choices/review and coordinate complete Cedar native
enforcement without treating recutting as geometry repair. P01 and P02 remain partial. Do not materialize an ASU before the
P03 identity/scattering and P04 seam-chemistry gates. W55 supplies an independent
sampled complex-Fcalc/ANISOU transport diagnostic, not complete invariance proof.

**Stitch capability and scientific boundary:** source-bound end frames, periodic
image search, logical registration, declared-route discovery, fixed-anchor paired
windows, explicit bend previews and bounded fitting exist. Periodic fitting checks
selected source/transformed atom identity and reciprocal incidence; complete
molecular/global image equivalence remains open. Unassisted partner inference,
reconstruction and campaign adoption are unimplemented. Native capture/trial and
endpoint observers reuse Cedar owners and preserve intended/core pair changes,
packing regressions, derivatives and rounded-coordinate readback separately.
All fixed-base/whole-window trials remain capped or failed, unselected and local.

W51's 500-iteration controls retain line-search rounding failures. W53 exactly
replays their last accepted points: complete derivatives pass, while predeclared
precision probes support score-resolution limits. This is not convergence or
chemistry approval. W54 preserves separately audited last-accepted diagnostics
without converting failed jobs to success or emitting candidates. Do not relax
stopping policy merely to obtain a pass. Scalar outlier improvements can coexist
with worse individual contacts and affected geometry.

W34's three matched reference refinements used the same observations/Free-R:
bend-plus-cleanup Rfree .2276 versus cleanup .2274 gives no meaningful additional
held-out benefit, with worse bond/angle RMSDs. No candidate adoption follows.
The private MR repair and density-inspection gates remain open. General tools
must handle straight→bent, bent→straight and changed/nonuniform/distal curvature;
benchmark IDs and transforms belong in requests, not algorithm branches.
Calibrated read-only negative-backbone-density observation is queued in S06,
then human review, then later density-guided placement. Construct 4T28/PDB 8SJW
is a future example; the exact B:11 interpretation remains unverified.

**Shared Pine/Cedar boundary:** Pine retains editable periodic connectivity and
user choices across reslicing; TopoStitch exposes them, Cedar reports enforcement.
A declared periodic bond preserves **P/OP1/OP2** independently of partner resolution.
No automatic OP3/dephosphorylation and no lone symmetry-bond restraint while the
surrounding phosphate-angle/exclusion policy is unqualified. See the
[shared contract](construct-registration.md#shared-periodic-connectivity-intent-pine-topostitch-and-cedar).
Virtual L/R recipe labels are not ordinary source-model refinement selections.
Callback lifetime, normalization, native exclusions/LINK bookkeeping and exact
movement masks require their own qualified consumer policy.

**Compatibility:** Willow remains isolated from dirty Pine/Cedar checkouts. W63's
temporary installed composition with published Cedar C302 `d32825e9` passes 397
Willow + 238 Cedar tests and 19 subtests, six helps and exact old/new packet/orbit/
view/scattering/source-native replay through the default installed Cedar owners.
Metadata union is explicit (extras, entry points, exact viewer asset); runtime
overlays have source hashes. This is scoped compatibility, not a merge, full
combined suite, combined human-guide review or native execution.

Do not edit Cedar or its installation. Preserve immutable runs, unpublished inputs,
maps, Free-R and all negative evidence. Scientific artifacts stay local; evidence
archives are forensic records, not resumable portable runs. Retained W34 controls
have no parallelity proxies, so they were not rerun merely to test C299's correction.

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
