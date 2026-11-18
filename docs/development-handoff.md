# NASolve development handoff — current state

Updated **2026-11-18, C400 matched pair controls and longer-control integration — Rowan**.
Active branch **cedar**, worktree **NASolve-c96**. Integrated code **`4f7aeb84`**
is source/test/packaging-identical to full-tested candidate **`d8656b22`**:
**12,008 passed, 2 existing native opt-in skips, 293 subtests passed** in 3581.07 s,
with exact NARestraints `a9264f9e`. All 1,415 candidate tracked files stayed unchanged;
the test process stopped. C394 log parsing is included. No duplicate full run.

## Current checkpoint and next bounded work

**C400 complete — added pair restraints have a matched native comparison.**
The explicit Python-only 100-cap control is integrated after focused, installed,
actual-native and full-suite checks. Older v3–v7 emitted workers remain exact;
ordinary defaults and CLI/campaign support do not change. Each arm uses the same
starting state, data, native parameters and existing plane-force correction.
A genuinely zero-addition recipe reproduces the native restraint set's entire
actual-return history, stopping receipt, model, scattering state and reflection
arrays. Passive observation also reproduces the ordinary full-recipe endpoint.

The complete recipe adds seventeen terms. On the same fourteen canonical pairs,
selected G:C plane mismatch improves 27.30→6.30°, selected A:T 8.85→4.59° and
pair-distance RMS error 0.247→0.200 Å. These are written-PDB measurements with
declared crystal images; the independent full-precision twelve-core-pair comparison
is separate. The A:T contacts remain long. Final Rwork worsens 0.2267→0.2271,
Rfree improves slightly 0.2613→0.2609, and clashscore worsens 23.27→24.77.
Both final R values remain worse than their common initial 0.2245/0.2599.

All arms stop with the lower-bound line-search error: full 73 iterations/82 actual
returns, native/zero 75/86, below the configured 100 cap. Same-coordinate score
jumps are accounted for by changed restraint-count denominators with unchanged
raw geometry, diffraction and weights; this does not prove stopping causality.
This closes the bounded canonical control matrix, not convergence or Q06 chemistry.

The first zero fixture retained stale full-library metadata and correctly refused
before refinement. A fresh recipe built by the existing owner changes only that
metadata; the already completed full/native arms are reused. The original failed
record remains failed. Independent reviews, explicit successful-control joins and
a byte-verified local archive preserve both attempts. Final clashscore comes from
PDB REMARKs: the original runner's log-only value 32.28 is INITIAL and remains
unchanged, with a separate hash-bound correction. No runtime parser fix is needed.

**Next — publish corrected PDU through genuine preparation, then test survival.**
C327's corrected definitions have no ordinary checkpoint authority. Do not replace
C303's old CIFs or manufacture historical ancestry. Reuse genuine fresh AutoMR /
PostMR preparation with the explicit bond-target request, then its unselected
refinement descendant. Determine whether fresh construction reproduces the intended
chemistry before spending another refinement run. Q06 still requires useful PDU/DF
geometry after Phenix and broader protocol qualification.

**C397–C399 diagnostic branch is complete.** Actual-state FFT score/force checks
fail the sampled agreement test while direct calculation agrees; matched fresh
histories still stop at rounding/iteration cap without repairing sugar–base/metal
strain. Reuse those receipts rather than repeat derivative, weight or iteration
sweeps. The exact state, failed attempts and numerical boundaries remain in the ledger.

**C396 complete — changing the geometry screen does not yet repair PDU.**
A private five-cycle control excludes only source-matched declared pairing from
Phenix's eligibility means: 51 distances and 84 angles. Six protected terminal
angles and every unclassified native contribution remain. Complete forces,
normalization, native thresholds, fallback and ties are unchanged. This is
“eligibility without declared pairing,” not a covalent-only classifier.

The 40 actual trials retain the same 2,559-term /855-heavy-atom inventory. Cycles
1/3 are singletons; searches 2/4/5 have 15/9/10 eligible choices. All six recorded preflight
comparison fields match C395; Linden independently reproduces source assignments, physical
arithmetic and every decision, with original observations and Free-R preserved.
Both native phases stopped; complete control 256.41 s. No automatic adoption.

PDU's triple length improves from 1.213226 to 1.179105 Å (target 1.174), but angles
change from 175.4494°/174.4251° to 174.8943°/176.9231°: one still exceeds the unchanged
five-degree bend screen. Terminal single length improves 1.49956→1.46532 Å (target
1.470), while terminal carbon distance from the fitted six-atom ring plane worsens
0.17481→0.36556 Å. Chi stays −112.59°→−112.70° and all three captured sugar chirality
signs are preserved. These are descriptive full-native-coordinate measurements,
not a new acceptance threshold. Final Rwork/Rfree worsen 0.2125/0.2265→0.2277/0.2444.
The final ordinary pooled geometry is 0.083 Å/1.972°, separate from eligibility means.
Q06 remains open; no production selector, normalization or scientific criterion changed.

**Reuse the completed evidence, rather than repeat it:**

| Evidence | What it establishes |
| --- | --- |
| C392 / C395 | Original PDU five-cycle behavior and passive observation reproduce exact model, native state, reflection arrays and 1,962 correction calls. All original searches fall back; exact actual trial membership explains that supplied pairing dominates pooled unweighted bond delta², not necessarily energy. |
| C393 / W134 | Chemical/pair observation coexistence and an ordinary canonical second refinement work within their distinct scopes. Modest pair improvements do not establish chemical or diffraction improvement. Combined ordinary chemistry-descendant coverage is still separate. |
| C394 | Actual numbered `1_realsrl2` stage no longer hides final log geometry. Only log parsing changed; 64 affected tests +31 subtests and 148 smoke tests +6 subtests pass. Native worker bytes remain exact. |
| C396 | Narrow eligibility intervention changes actual choices, improves some local lengths, but worsens other geometry and diffraction agreement. Independent cold review passes; scientific result remains REVIEW. |
| Hazel A79 / A85 | A79 finds two same-coordinate normalization jumps. A85's private fixed-denominator intervention removes nine lower-bound line-search errors but leaves rounding/iteration-limit stops; slightly improved R values coexist with worse DF attachment/metal angle. No production remedy or converged model. |

Exact commands, source identities, failed attempts, validation and archived evidence
remain in the existing ledger; private models, maps and diagnostic traces stay local.

**Next bounded work, in order:**

1. Reuse C397–C399 rather than repeating derivatives or iteration/weight sweeps.
   Actual-state FFT score/force mismatch is isolated; direct calculation agrees
   locally and progresses to the declared cap, but neither restart repairs geometry.
   Native convergence and physical chemistry remain distinct. Do not infer lost
   PDU restraints: C396 retains the captured C5A plane and local definitions.
2. C400's explicit longer control and native/zero/full matrix are complete.
   Carry corrected PDU through genuine new preparation; verify requested chemistry,
   full restraints and checkpoint lineage before its ordinary refinement. Reuse
   the existing owners; no retrospective authority for diagnostic copies.
3. Close ordinary combined-descendant coverage when that route is needed, using the
   existing process/checkpoint owners. No parallel recovery engine or repeated
   copies of frozen inventories. Keep density fitting separately gated on explicit
   map-generation/work-free/fill policy, not finite coefficient membership alone.
4. Q06 still requires useful PDU/DF geometry after refinement. Then run the original
   mixed scaffold with ATL alongside, the held-out modified-pair challenge and the
   retained sugar/backbone programme. Keep Q15 explanation and final Q16 AutoPhase /
   combined-source validation / merge review; no automatic merge or wider defaults.

## Completed foundations to reuse

| Work | Result and boundary |
| --- | --- |
| C381–C385 | Sealed preflight, original-intent continuation, checked input copies, refusal of missing ancestry and exact written-model proof. Reuse existing attempt/process/archive owners. |
| C386/C389 | Explicit bounded counted control through ordinary AutoRefine, including newly supplied portable restraint files and checkpoint inheritance. Native results agree; no CLI/default activation. |
| C387/C394 | Final native step-table reporting; the digit-suffix gap is closed. Pooled geometry is not covalent-only. |
| C388 | Existing source-selected PDU triple observation coexists with counted forces. On/off controls agree within each provider arrangement; cross-arrangement native states differ despite identical rounded PDBs. Short-control Rwork/Rfree 0.4230/0.8360 is poor. |
| C390/C391 | Pure W131 pair report plus explicit v7 actual-final-state capture. Same canonical control PDB/full atom state/15 counted evaluations as C386/C389; one separate descriptive energy call. Fourteen pairs, 107 native +17 added requested terms; covalent chemistry unassessed. |

C391 installed/relocated panel passes **305 tests +24 subtests**. Nine new integration
regressions fail against C390; the historical-byte regression already passes. Moved
cold reports agree; wrong PDB and v7→v6 loss refuse before allocation. All v3–v6
worker bytes remain exact. Linden W133 independently verifies 303 Git/wheel/installed
files, actual native/writer/force joins and physical report arithmetic; 77 current
and 72 baseline files/timestamps stay unchanged. W133 source `1a1db576`. No new
native fit in that audit. Earlier exact commands/results are retained in the
[evidence ledger](cif-linked-native-registration-evidence.json), including
`final_refined_pair_geometry_2026_11_18`; no historical evidence is relabelled.

**Storage and redundancy.** C391's added geometry archive is 15,492 bytes; complete
matched run trees differ by 33,323 bytes, including other receipt/path differences.
C396's verified local archive is 3,222,821 bytes for 9,344,431 raw bytes; all originals
remain. C392's weight receipt is 17,984 bytes; its verified archive is 2,468,484 bytes for
14,586,919 raw bytes, retaining successful and early failed roots. This is an evidence
archive, not a portable native-command claim or 100-dataset capacity measurement.
An audit of 3,965 test definitions finds seven exact-body groups, mostly distinct
owners/parameters; no accidental imported-test collection. No tests removed without
demonstrated redundancy. Current build copies still serve historical-reader/native
qualification and are retained. Unrelated local material and peer work are untouched.

The eight-file local science checkout (about 1.1 MB) is
`ScienceCheckouts/Rowan/2026-11-18/review.html` under the sibling GitHub root. It shows
the matched pair-control effect, PDU geometry and weight choices, with links to retained
evidence rather than duplicated raw datasets. It links the existing Linden and
Hazel checkouts, including independent continuation/full regression and the separate
DF/metal stopping-event diagnosis and its separately labelled A85 normalization
follow-up. Signed local continuity notes remain outside
the product repo.

Keep working-frame choice explicit; W115's MTZ/PDB cell precision difference does
not justify widening tolerances. A launch marker is not proof of process death.
Preserve failed/unknown attempts, original Free-R and terminal intent. B:1 symmetry
continuation and D:1 terminal protection are separate scientific declarations.

## DY integration boundary

C354/C364 own package/backbone composition; C358 plans explicit source/parent
mutations; C359 selects exact site dictionaries; C362 derives them from canonical
input/end intent; C363/C365 bind derivation, original chemical source and actual
prepared-model context. C366 now joins those parts in ordinary PostMR. Reuse them.
Modified-input canonical seeds have separate C348/C349/C353 proof; forwarding that
choice through this new ordinary route, automatic public selection and real DY
pairing semantics still require explicit scope. A covalent control cannot invent
NARestraints relationships or general modified-sugar support.

**DF construction improves but refinement still stretches it.** C361's existing
whole-base transport preserves the exact 11-atom scaffold and 838 other atom states,
with C1′–N1 1.49958 Å rather than curated placement's 1.60172 Å. Hazel's matched five
cycles retain all declared links/restraints but stretch it to 1.662440 Å at native
precision (serialized 1.662146 Å). Alder `47e7b333` and C363's ledger bind that result.
Do not adopt the endpoint or blindly replace curated sulfur/iodine protections.

## Scientific findings and preserved evidence

- **Modified → canonical → modified works explicitly.** C348/C349 demonstrate
  PDU→DT→DY and DY→DT→PDU through ordinary Coot. All 11 shared scaffold coordinates
  and unselected heavy coordinates remain exact; final chi differs by <0.02°.
  C353 carries compact canonical evidence through ordinary lineage/request freezing.
  Modified-sugar/cross-family placement is outside this deoxy rule.
- **Keep the two DY rings independently rotatable.** DY is the retained triazole
  nucleoside, with a direct C4–N1T single bond. C341/C351 test rotation/bending and
  derivatives; public PIM is a held-out control. C350's graph-based reader correction
  preserves a single inter-ring bridge. No common ring plane or arbitrary weight
  increase follows. C346's five-cycle covalent-only DY substitution control preserves
  source/targets, sugar hand and near-planar rings; it supplies no DY pairing rule
  or modified-crystal diffraction validation.
- **PDU refinement is still REVIEW.** C333 delivers the qualified 1.470 Å terminal
  target through existing owners. C329 achieves 1.481829 Å, but angles
  175.019°/173.937° and a 0.258 Å plane offset remain. C338's separate actual-manager
  reporting control also retains bending (175.4494°/174.4251°). Preserve these
  distinctions; do not rerun identical trials or strengthen restraints to force a pass.
- **ReadySet provenance matters.** C323 traced the old 1.607 Å target to upstream
  RM1/GDIIS output after reported nonconvergence; observed ReadySet retained the
  supplied dictionary without builder calls. Prefer a demonstrably better native
  source-faithful route when available, not longer identical runs or coordinate-to-target copying.
- **Phosphate intent is explicit.** Original PDU:PDU B:1 is an incoming symmetry
  continuation with P/OP1/OP2 and no OP3, superseding the earlier free-OH answer.
  C295's B:7 O3′ image is a candidate, not confirmed linkage. D:1 terminal phosphate
  is separately protected; C303's substitution scaffold has separately declared intent.
  The sanitizer removes only OP3 with a proven incoming bond, not a whole phosphate
  at a free end. No blanket OP3 deletion or unsupported symmetry-angle inference.
- **Preserve native identity and historical readers.** C318/C319 synchronize final
  ADPs from the same native owner. Frozen restoration/C331/C338 helpers, original
  Free-R, native targets and historical receipts retain their contracts. A missing
  optional improvement may retain a qualified parent; unknown process ownership
  never authorizes retry or in-place repair.

Exact controls, commands, hashes and limitations are in the
[evidence ledger](cif-linked-native-registration-evidence.json). Start with
`ordinary_frozen_construction_intake_2026_11_17`,
`projected_construction_source_join_2026_11_17`,
`composed_acquisition_sources_2026_11_17`,
`construction_projection_lineage_2026_11_17`,
`canonical_input_projection_2026_11_17`,
`df_existing_whole_base_diagnostic_2026_11_17`,
`construction_component_padding_2026_11_17`,
`per_site_construction_dictionaries_2026_11_17`,
`explicit_construction_planning_2026_11_17`,
`packaged_dy_mixed_context_replay_2026_11_16`,
`explicit_custom_source_selection_2026_11_16`,
`canonical_construction_lineage_2026_11_16`,
`compact_refinement_observation_2026_11_16` and
`corrected_cif_refinement_survival_2026_11_15`. The full C356-era narrative remains
[available at its exact Git revision](https://github.com/vecchioni-lab/NASolve/blob/162ffe1d2562eec2759f02546ccf8540317b378b/docs/development-handoff.md);
[history index](history/README.md#november-16-cedar-handoff-consolidation) records its
blob/checksum and offline retrieval. Historical next steps are not current instructions.

## Validation and limits

Earlier construction/selection checks (C355–C366) are retained in the exact
ledger entries above. They qualify their original source/consumer contexts, not
new runtime policies. Reuse those results unless a changed boundary requires a
new control; do not repeat broad suites for documentation or unchanged sources.

- Latest unfiltered Cedar run: **C386 / `d5c2fb7b`: 11,873 passed, 46 failed,
  2 skipped, 281 subtests; 3266.71 s**. W132 resolves all 46 original failures
  without a product fix or new skip: the exact failed-node rerun with host process
  permissions gives 45 passed /1 failed (84.71 s); the remaining source-bundle
  test passes with Git metadata from the byte-identical NARestraints
  `a9264f9e` source (0.96 s). Original failed full run and diagnostic reruns remain
  distinct. This is not an uninterrupted full pass or validation of later Cedar.
  Evidence: ledger `full_c386_regression_resolution_2026_11_18`, Linden W132
  `5c107fb9`; all 1,405 source files unchanged, owners stopped. Last uninterrupted
  Cedar full pass remains C220 `583d30df` (9,178 +276 subtests). W112/C366's
  separate temporary composition passed 12,138 +284 subtests /1 skipped; it is
  not a branch merge or current-source validation. Final combined source needs
  its own full/native/relocation checks.
- Recorded native versions: **Phenix 2.2.1-6174** (dispatcher 2.2.1), **Coot 1.3.3**.
  Package references and source/recipe qualification do not imply universal support.
  Formal-charge readback remains unsupported where reported; Q06 geometry is open.
- Q04/Q05 acceptance is the supported explicit route through **C285 / `d5996bc4`**.
  Defaults, historical migration and 100-native-dataset capacity are not qualified.
  Q07–Q14 retain combined controls, L-DNA/FANA/L-FANA/L-FDNA, PNA, locked sugars,
  catalogue coverage, chemical-state distinctions and false alarms. Q15 reporting
  and Q16 AutoPhase/full integration follow; no automatic merge.

## Queue, compatibility and collaboration

Cedar targets eventual reviewed integration with pine/main. Keep one Cedar line.
Linden owns Pine/Willow; Hazel owns Alder/metal coordination. Signed coordination
is authorized; their separate successes are not a combined Cedar qualification.
The [shared guard contract](architecture.md#live-nonbonded-policy-guard-c331) remains
explicit and unactivated by documentation. Read each branch's current handoff
before touching shared interfaces; do not edit another agent's worktree. C368/W114
qualify direct ownership; C386 adds the bounded explicit ordinary route, while
broader refinement remains gated and C331 stays callback-free. Hazel owns the DF competing-force diagnostic.

Keep scientific data, native logs, SDK snapshots, local inventories and runners
outside Git. Use the ignored everyday `branch-artifacts/cedar/` for local receipts
and `runners/` for generated scripts. Preserve failed runs, immutable attempts,
checkpoint selections, old environments and unrelated untracked work. The C357
local audit records the retained legacy worktree and large historical-run footprint;
retiring scientific runs requires dependency/retention checks, not directory-name
or age heuristics. Inspect before deletion; never blanket-clean the repository.

Check history before redesigning a solved problem. Finish the active bounded task
before diverting to a new idea unless explicitly redirected. Update this short
handoff in place; detailed results belong in the existing ledger and work order
in the existing queue. Sign peer notes **— Rowan**.
