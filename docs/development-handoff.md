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

## Separate Willow work — 2026-11-15

**W73 recorded; next W74.** Runtime implementation is W73 `c4add34c` on isolated
`willow`. The [audited roadmap](topostitch-roadmap.md) is generated from the one
JSON status queue; the [intent record](topostitch-intent.json) lists owners without
granting authority. Exact commands, native evidence and historical limits live in
[periodic topology](topostitch-periodic.md) and [bend previews](topostitch-preview.md).
Do not repeat completed probes merely because this compact handoff omits chronology.

**Current behavior:** the existing graph/packet owners freeze explicit image or
chosen-forest proposals, replay them after relocation, compare 2–8 cuts through
one viewer/camera and save source-bound preferences. These are review inputs,
not model/checkpoint selection or authenticated approval. Optional native-link
and backbone-intent observations expose image seams, incomplete graph coverage,
declared/chemical/unknown boundaries and exact phosphate inventory.

W67 resolves explicitly declared directed 3′→5′ partners through schema-2
representative/forest requests. Both endpoints must already be representation
boundaries. Chemical/unknown/interior/do-not-connect sites, competing partners
and stale graph digests refuse. Exact images, periodic winding and unresolved
coordinate partners survive replay. Old schema-1 packets/default observations
remain exact; old readers reject schema 2. The public development control adds
one declared existing source link, preserves all 855 proposed coordinates exactly,
and covers one of two native seams; the other remains outside the partial routes.
No partner is inferred, atom edited, restraint activated or new ASU written.
W70 adds read-only `cut-preview --describe-graph`: graph IDs/hash and optional
request MATCH/MISMATCH, with cut_selection_validated=false. It writes no directory,
never rebinds a request, and leaves ordinary preview validation unchanged.

**W71 angle component:** `topostitch_native_terms` freezes complete live angle
metadata against captured definitions, then reconstructs a private proxy array
with explicit cell evaluation. JSON/deepcopy/pickle and fresh installed native
reload preserve exact observations. Two public cuts retain all 1,467 angles;
source energy/rotated gradients and predeclared directional checks agree. This is
read-only and must not be added to an objective already containing those angles.
No source manager, native installation, chemistry or refinement is changed.

**Code validation:** full Willow **1,727 + 229 subtests**; installed/relocated
**521**, six helps, lean import and Python 3.10 syntax. Old/new packets and graph
replay stay exact with original paths blocked. Initial missing-Gemmi and native
Python/NumPy ABI environment failures are retained; correctly isolated checks pass.

Installed virtual composition with published Cedar `393aea60` passes
**640 + 16 subtests** (521 TopoStitch, 76 combined autorefine/refinement-runtime/
parallelity and 43 Cedar numerical-reference checks), six helps and exact default-owner native/packet/graph replay.
Seven documentation conflicts and zero source conflicts remain. No actual merge,
full combined suite or ordinary native refinement qualification is claimed.

**W68 native finding:** complete fresh Phenix **2.2.1-6174** reconstruction matches
the authenticated source. Eight crossing source-native angle terms per cut preserve
image-aware energies/rotated gradients; subset/reindexing preserves operators.
But native proxy pickle/generic manager deepcopy lose `sym_ops`, and the isolated
geometry manager already omits unit-cell evaluation context before serialization.
Correct image-bearing proxies alone therefore do not qualify a seam. Direct kernels
and the ordinary manager are distinct; this was not a full refinement execution.
Three setup failures and all negative controls are retained. See the
[angle/lifecycle audit](topostitch-periodic.md#w68--inspect-source-seam-angles-and-proxy-persistence).

**W72 scientific result:** retaining the complete source geometry and inverse-
mapping chosen representatives preserves the full target/gradients, including
forced native neighbor rebuilding with changed membership. Source seams contain
two bonds/eight angles/six torsions. Twelve actual mmtbx energy-entry controls pass
normalization and gradient-buffer combinations. A local facade's identity selection
**drops its mapping** and remains a demonstrated failure. No runtime hook or
ordinary refinement was installed; a recut PDB alone lacks this geometry context.

**W73 binding component:** immutable `ReferenceFrame` keeps complete source labels,
proper numerical images and caller-owned context through explicit full permutations.
The local mmtbx facade now passes 36 identity/reverse/cyclic cases; partial selection
and actual cell drift refuse before evaluation. Plain frames reopen from the installed
wheel in a fresh native interpreter after relocation. The facade itself remains
local; no native selection hook or ordinary refinement support is claimed. The
caller must authenticate/recompute context, not merely repeat an old digest.

**Next P04 work:** bind source/frame identity and explicitly handle selection,
reconstruction and supported coordinate/ADP/NCS/callback policies through Cedar.
Whole-objective evaluation is promising; neither its local facade nor W71's angle
observer qualifies ordinary refinement. Preserve P02/P03 and no-bond-alone gates.
Cedar's `cif_refinement_runtime` wraps/audits the
parallelity kernel; it does not restore missing metadata, and its kernel rejects
symmetry-bearing proxies. `refinement_parallelity` owns reusable frozen helpers,
zero-cycle preflight and exact checkpoint/round ancestry, not existing angle support.
Do not fork a refinement driver or patch Cedar during Rowan's pinned native work.

**Other gates stay open:** actual browser rendering/download and human cut review
remain blocked by the explicit local-file URL policy; no workaround was attempted.
P01/P02 remain partial. W62 proves labelled orbit permutations/complete source-atom
ownership; W55 observes sampled Fcalc and in-memory ANISOU transport. Physical unique
identity, special-position weights and serialized tensors remain distinct. Do not
materialize an ASU before P03/P04 qualify its physical identity and seam chemistry;
recutting cannot repair a physical gap.

**Stitch capability:** source-bound frames, periodic image search, logical
registration, declared routes, fixed-anchor paired windows, explicit previews and
bounded fitting exist. Selected-image reciprocal incidence is checked; complete
molecular/global identity, unassisted inference, rebuilding and campaign adoption
remain open. Native observers/trials reuse Cedar owners; all whole-window trials
remain capped/failed, unselected and local. W51 line-search rounding failures remain
failures. W53/W54 pass full/rounded accepted-point diagnostics without adopting a
candidate. W61 shows scalar/pair improvements can coexist with worse individual
packing/torsion/plane terms. Do not relax stopping policy merely to produce a pass.

W34's matched same-data/Free-R controls give bend-plus-cleanup Rfree .2276 versus
cleanup .2274, with worse bond/angle RMSDs: no meaningful extra held-out benefit.
Private MR repair remains open. General tools must handle straight→bent,
bent→straight and changed/nonuniform/distal curvature. Benchmark IDs/transforms
belong in requests. Calibrated read-only negative-backbone-density detection stays
in **S06**, after exact model/map/data binding and matched refinement, then review,
then density-guided placement. Construct 4T28/PDB 8SJW is a future example;
its exact B:11 interpretation remains unverified.

**Shared boundary:** Pine owns editable periodic intent; TopoStitch exposes it;
Cedar owns native enforcement. Preserve **P/OP1/OP2** on declared continuation even
with unresolved partners. No automatic OP3/dephosphorylation or lone symmetry bond
while surrounding geometry/exclusions are unqualified. Virtual L/R recipe labels
are not ordinary source-model selections. See the [shared contract](construct-registration.md#shared-periodic-connectivity-intent-pine-topostitch-and-cedar).

Keep dirty Pine/Cedar worktrees, immutable runs, maps and Free-R untouched.
Scientific inputs/results and failed probes remain in Git-ignored local evidence;
archives are forensic records, not resumable portable runs. Do not rerun W34's
plane-free controls merely to test a parallelity correction.

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
