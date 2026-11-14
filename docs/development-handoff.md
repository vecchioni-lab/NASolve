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

## Separate Willow work — 2026-11-13

**Willow update W47; next W48.** W33 introduced human update numbers without
renumbering old history. Use these labels in conversation; the roadmap JSON
retains exact code provenance.

[TopoStitch](topostitch.md) on `willow` starts from Pine `d7913dd`; its
[intent record](topostitch-intent.json) is development metadata, not runtime
permission. The [current inspector contract](topostitch-periodic.md) owns usage,
schemas, validation commands and limits; the [bend-preview guide](topostitch-preview.md)
owns explicit candidate generation. The [audited completion roadmap](topostitch-roadmap.md)
is the one work queue for the sticky-end and Pine ASU-slicing tracks; its JSON
ledger and audit command keep status, dependencies and closure evidence aligned.

Implemented: verified PDB end frames; metric-bounded periodic image search;
NARestraints contact observations; factorized one-partner alternatives; logical
end mapping through Pine registration; bounded discovery within declared chemical
routes/core pairing; and whole-pair window proposals with fixed inner anchors.
Incomplete pairing, missing mappings, uncertain cuts, protected junctions and
declared free ends remain explicit. A separate explicit preview writer now
applies a tapered paired-step transform in a new candidate, preserves source and
anchors, rotates ANISOU tensors and audits serialized backbone changes. Frozen
input snapshots and run-relative checksums support replay after relocation.
Inspector execution stays NOT_ATTEMPTED; actual previews are CANDIDATE_BUILT,
UNREVIEWED and unrefined. No existing model/checkpoint is changed.
An optional bounded fitter now proposes a terminal transform for one explicit
pairing/image and window, counting Jacobian evaluations and rechecking serialized
limits. No partner/window selection is inferred. The roadmap currently prioritizes
F02/S03 physical image/connection identity (periodic fitting now requires a
clear selected-coordinate source audit), then S04/S05 local geometry closure
before S06 matched refinement. A verified offline source/candidate/mate view
now supports rotation, atomic inspection and measured contact comparisons. It
has no selection/refinement/approval API; Pine cut choice/materialization and
campaign integration are still open. Unassisted coordinate
topology discovery, reconstruction, refinement and campaign adoption remain
unimplemented.

**Current W47 edge:** one exact reciprocal-incidence owner now connects the
pairing and atom-image audits. A periodic fit requires one partner within the
selected-coordinate scope; lattice shifts are never wrapped away. Ambiguity and
global/molecular identity remain open. Full Willow: 1,424 + 229 subtests;
focused/installed-relocated: 68. Existing public 8D93 placement reproduces exactly
apart from added capacity metadata and algorithm v5. No native runtime/Cedar edits.
Next prototype the minimum declared periodic graph for one Pine cut, retaining
edge kinds, unknown coverage and winding; materialization/physical approval stay
behind the existing F02/Pine gates. S05 ordinary refinement remains separate.

**Prior W46 edge:** endpoint review now composes maintained Cedar torsion/plane
kernels with checked live proxy semantics and complete family target/gradient
parity. Six native controls pass; individual regressions remain visible even when
aggregate scores improve. Full Willow: 1,416 + 229 subtests; installed/relocated:
159 and byte-identical native review. Temporary installed Cedar C289 composition
also passes 159 focused tests and exact native review through its owned runner.
No branch merge, Cedar changes or chemical acceptance.
S05 still needs qualified chemistry and an ordinary refinement consumer; Rowan's
C289 reported full-objective native-force discrepancy is not a supported corrected
runtime. Next address shared explicit-connection physical capacity (F02/S03),
keeping global inference and special-position equivalences under review.

**Prior W45 edge:** one matched native control retains the same 12 core pairs
as the paired trial and toggles only the intended contacts. Existing APIs suffice;
no runtime changes. All source/endpoint derivatives and fresh rounded native
readback pass, but both arms remain capped with packing regressions. Core-only
protects core pair totals while one selected pair worsens; adding selected terms
improves both selected totals. Next compose Cedar's maintained torsion/plane
kernels into endpoint observations; do not invent missing proxy policy or treat
container parity as chemical approval.

**Prior W44 edge:** native per-term attribution reproduces container scores and
preserves every selected/core pair change. Whole-window paired control improves
all pair totals; cleanup alone worsens two core pairs and one selected pair.
Contacts still need repair, capped outcomes and packing regressions remain.
Full Willow: 1,397 tests + 229 subtests; installed/relocated: 140 and byte-identical
native endpoint review. Compact JSON preserves existing tables and cuts report
size by about 55%. No Cedar changes. Next declare a bend/cleanup comparison using
these existing owners, then qualify chemistry before matched diffraction.

**Prior W43 edge:** the same package/CLI can read an explicit masked endpoint
and compare source/full-precision/rounded native ASU packing through Cedar owners.
Five complete Phenix 2.2.1-6174 controls pass; independently reinterpreted rounded
PDBs agree in full native target/gradient and matched pair residuals. Differing
neighbor rows contribute zero in these controls. Precision-dependent contact
changes remain visible; the original trials are still capped and unselected.
Full Willow: 1,384 tests + 229 subtests; installed/relocated focused: 127 and a
byte-identical complete endpoint review with original paths blocked. Native core
interfaces are unchanged through Cedar af9aee87; no merge or Cedar edits.
Next attribute individual intended/core pair contributions before a declared
bend/cleanup comparison. Broader chemistry and S06 diffraction remain open;
density-aware placement stays in its existing later queue.

**Prior W42 edge:** the installed `run_captured_objective` API owns the existing
capture/trial orchestration; the developer CLI remains compatible. Cedar owns
capture, observation layering and process execution; uncertain cleanup errors
escape after saving evidence. Source native results reproduce W41 exactly.
Installed/relocated Willow and a temporary Cedar 948a7860 overlay pass native
read-only execution, including the injected owned runner. Full Willow: 1,372
tests + 229 subtests; installed focused: 74; temporary combined focused: 244 + 19
subtests. No branch merge, complete combined suite or campaign adoption is claimed.
Next close full-precision/serialized packing and affected chemistry before S06
matched refinement. Density-supported curvature remains in its later queue.

**Prior W41 edge:** the existing capture probe can explicitly run a bounded
native trial with complete source/full-precision/rounded derivative audits and
a matched cleanup switch. Five Phenix 2.2.1-6174 trials pass derivatives and fresh
rounded native target readback but reach the 200-iteration limit. Whole-window
pairing improves its score at a different geometry/packing tradeoff from cleanup;
fixed-base pair terms are constant. No repair, refinement or adoption is claimed.
Full Willow: 1,364 tests + 229 subtests. Source and installed validation, retained
failures and compatibility are in the [validation receipt](topostitch-periodic.md#current-validation-receipt--2026-11-13).
Next extract one installed captured-job boundary using Cedar's anchored inputs,
observation ordering and process runner; no Cedar merge/edit or second executor.
S05 still needs broader chemistry/packing closure; S06 needs matched diffraction.
Density-supported bend location remains in the later audited queue.

**Prior W40 edge:** exact full-precision/mask/PDB-byte binding is available
through an optional extension of the existing packing reader. Cedar owns native
mechanics and selected/boundary/fixed environment review; unchanged legacy packing
content is tested. Three complete Phenix 2.2.1-6174 endpoint captures pass mechanics
and explicit Cartesian ANISOU preservation; initial default rejections remain.
Lower global repulsion can still accompany worse individual contacts. All outputs
remain descriptive, unselected and local. Full Willow: 1,358 tests + 229 subtests;
installed focused: 101; relocated focused: 69 and byte-identical complete review
with original reads blocked. No optimizer or endpoint derivative qualification.
Next connect a bounded trial to the established initial-context and endpoint
boundaries, retaining failed/capped outcomes and matched controls. Density-aware
curvature placement stays in the audited later queue.

**Prior W39 edge:** a developer-only reconstruction probe reuses Cedar capture,
worker builders, native process ownership and inventory replay. Fresh native
contexts match the authenticated initial full-monomer/geometry/energy/ASU-pair
observations for both prior 8D93 masks and independent 7R96; repeated masked
energies exactly reproduce W38. Tampered workers and wrong request hashes fail.
Full Willow: 1,338 tests + 229 subtests; installed and relocated focused: 60 each.
Installed and relocated native reconstruction also pass (Phenix 2.2.1-6174).
The guide retains initial environment/harness failures and exact validation scope.
No optimizer, candidate, refinement, adoption or complete exclusion-policy proof
is added. This is full Pine-derived Willow coverage, not Cedar or a combined build.
Next qualify one bounded trial's native lifecycle and endpoint geometry/packing;
matching initial observations alone does not freeze future neighbors or prove
physical acceptance. Avoid native/additive pair double counting. Preserve the
separate Pine recut route and consumer-specific PHIL handling (Cedar C278 finding).
Scientific files stay local. Density-supported bend-center/width alternatives
and construct 4T28/PDB 8SJW are queued, not implemented; exact B:11 interpretation
remains unverified.

**Prior W38 edge:** bounded coordinate masks and direct native/pair/tether
composition pass all-coordinate derivative checks for both movement scopes and
7R96, including ten negative controls. Full Willow: 1,323 + 229 subtests;
installed focused: 410 + 18; relocated: 107. No optimizer or ordinary refinement
adapter was added. Its static-definition hash is not complete policy authentication.

**Prior W37 checks:** reusable explicit canonical image recipes and a native
pair-energy compiler replace local-only binding code. Complete source suite:
1,312 tests + 229 subtests; focused source: 88; installed: 438 + 18 subtests;
relocated copied checkout with its original absent: 96. Isolated installed native
execution matches the 14-pair energy/components. Phenix 2.2.1-6174 complete
derivative probes pass 8D93, 7R96, P43 and P21 controls; 5W6W and strained P1 keep
REVIEW at the larger difference step. Per-coordinate convergence diagnostics are
retained, not used to relabel those outcomes. See W37 in the preview guide for
API, exact scopes and native evidence; the inspector guide owns validation commands.
The new packet/binding/probe schemas are additive; existing previews and entry
points remain unchanged. Virtual L/R recipe labels must never be treated as
ordinary refinement selections on the source model. No optimizer, manager hook,
native exclusion edit or checkpoint is introduced. Scientific artifacts remain
local. Generality is explicit: benchmark IDs/transforms belong in fixture inputs,
not algorithm rules. Calibrated read-only negative-backbone-density detection is
queued in S06, then review, then later density-guided motion.

**Prior W35 checks:** W35's three parser regressions reproduce the missing native
bond/angle RMSDs and preserve log precedence/incomplete-output behavior. Focused
source: 53 tests + 16 subtests; full source: 1,295 tests + 229 subtests; rebuilt
installed wheel: 421 focused tests + 18 subtests. The isolated installed parser
matches all three final Phenix 2.2.1-6174 PDB/log outputs. No refinement was rerun
for this readback fix. Existing statistics keys and checkpoint behavior are
unchanged; model/log summaries outside the recognized formats remain unmeasured.
Earlier W33 relocation: 376 focused tests + 2 subtests with the original copied
path absent; this parser-only patch does not change paths or artifact schemas.
Actual native packing
comparison output is byte-identical after copied source/models/captures relocate,
with Python reads of original live evidence blocked. Both frozen Cedar `cd744e2`
and `f2345a8` authenticate/replay the same measurements. The comparator preserves
relative image identity, directed multiplicity and per-contact regressions; it
adds no native worker or geometry acceptance. The installed numerical comparison
and image-transport cores need no native/Gemmi dependencies.
The offline viewer includes its asset; exact coordinate and JavaScript mock-DOM
checks pass. Rendered browser validation remains pending after a local-file
automation policy block.
Schema-2 preview
and fitting add nonbridging phosphate angles and circular epsilon/zeta/alpha
changes, while retaining exact schema-1 replay. The selected-image audit retains
coincident-label/occupancy uncertainty and gates periodic fitting. A second
audit now withholds serialized transforms that introduce selected-image
coincidences. Public source
bytes remain unchanged; generated coordinates and diagnostic artifacts stay local.
Public 8D93 native interpretation is REVIEW throughout. The original fit adds an
angle outlier; tighter controls and the new extended-audit fit add no nominal ≥5
captured scalar outliers with matched native contexts/proxies. This remains
source-change/descriptive evidence, not ideal geometry, native symmetry closure
or diffraction/refinement validation. The reproducible native image probe retains failing raw plane gradients;
Cartesian image pullback plus Cedar's existing parallelity correction passes
synthetic and public controls. This is diagnostic, not a production native adapter.
Masked native controls now preserve fixed bases explicitly or permit the selected
window's atoms under bounded motion. Adding the chosen image contacts improves
them beyond matched cleanup; adding existing core-pair terms limits duplex drift.
Derivative/readback checks now also pass with complete emitted NARestraints
plane selections/sigmas; all trials hit the iteration cap. A broader bend followed
by fixed-base cleanup removes its added angle outlier, but collateral periodic
contacts and individual geometry terms worsen. Native bond edits also change
exclusions/LINK bookkeeping, unlike additive contact energies. S05 remains partial:
a supported masked policy must audit intended edits and the surrounding packing
before matched refinement. No candidate is promoted.
W34 completes three matched public-reference refinements with the same 3,333
observations and 176 free reflections. Bending retains better selected contacts,
but Rfree (.2276) is essentially tied with cleanup alone (.2274), while bond/angle
RMSDs worsen. No extra bending benefit or candidate adoption is established.
This is a reference pilot; the private MR repair and density-inspection gates stay open.
W36's read-only native callback probe passes added-term derivatives but confirms
that all-atom selection and symmetry discard drop the callback; normalization
and enablement also require explicit policy. Before further bending/refinement,
qualify a complete periodic recipe through the intended manager lifecycle or a
separately qualified Pine recut. No production adapter or extra refinement was
added. The existing guide records both routes and their acceptance gates.
See the current inspector/preview guides for exact commands, versions, policies and limits.

**Compatibility:** Pine registration/model-assessment interfaces remain unchanged.
Frozen Cedar through `f2345a8` was tested for native readback; current Cedar through C278/C279 adds first-campaign refinement admission and
consumer-specific round-local PHIL wrapping after sealed AutoSol recovery; the consumed registration/model/context/package interfaces
remain unchanged against the Pine base. The consumed correction/audit/selected-geometry helpers remain unchanged through
Cedar `b6d6dfe`; C278 changes AutoRefine input handling, not its statistics parser. Willow consumes no new Cedar production interfaces and edits
no Cedar code or shared environment. The separate native comparison reused the
existing diagnostic helper only; see the preview guide for exact options.
Rowan confirms no qualified selective-coordinate adapter exists: Cedar's current
trial declares all captured atoms variable, and derivative sample indices are
not a movement mask. A future fixed-base objective needs its own explicit mask,
policy identity, frozen definitions and ASU endpoint derivative evidence.
Five local single-job Phaser placement controls also completed through existing
interfaces, including the supplied PDF-report input as an explicit frozen
selection. See the inspector contract for scope and unresolved copy/cut/chemistry
assumptions. No deformation/refinement comparison is yet established.
Shared guides/changelog need reconciliation at integration. No combined
Willow/Cedar build has been validated. Keep completed patches pushed and current
contracts concise rather than adding handoff diaries.

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
