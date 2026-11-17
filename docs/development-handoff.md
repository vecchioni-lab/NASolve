# NASolve development handoff — current state

Updated **2026-11-17, C365 source-to-construction join — Rowan**.
Active branch **cedar**, worktree **NASolve-c96**. C364 / `88ba9d27` is pushed.
C365 is complete: 135 affected checks, 38 ordinary compatibility checks and
173 installed/relocated checks pass. Real C363 construction plus C364 composition
passes ordinary prepared-request intake and cold readback. No new Phenix/Coot run,
full suite or merge. All Rowan jobs stopped; failed scientific attempts are preserved.

## Immediate work and peer boundary

**Next: forward explicit source/parent/projection choices before Coot in ordinary
PostMR.** C365 closes a concrete integration mismatch: C196's old equality check
confused chemical acquisition source with numerical construction CIF. C363 already
proved each actual site dictionary against its qualified projection. Its reader now
returns that original chemical source/authority; acquisition compares those, while
all numerical/end-state checks remain independent. Old non-projected lineage keeps
its byte-equality rule. No new stored schema or weaker chemistry checks were needed.

The actual mixed-end C363 DY model and C364 retained composition now enter
`initialize_postmr_dictionary_request` and replay cold with no SDK/new process:
46 files / 2,772,164 bytes. Original temporary copies and output location are gone;
149 prior files/timestamps are unchanged. This is prepared-request initialization,
not a fresh Coot/ReadySet/refinement or fabricated NARestraints pairing qualification.

Prior-work orientation for the next bounded integration:
- C354/C364 retain exact packaged-base/backbone composition through source selection.
- C358 plans explicit source/temporary-parent mutations; C359 reloads exact per-site
  Coot dictionaries; C362 derives those projections from canonical model/end intent.
- C363/C365 bind original model, selected CIFs, qualified source and actual prepared
  ends through existing construction and complete-request owners. Reuse these APIs.
- `_prepare_postmr` still calls catalogue-only planning and `ligand_definition`/
  `ligand_dictionary`; it does not forward explicit source/parent/projection choices.
  `initialize_ordinary_postmr_request` currently rediscovers sources after Coot.
- Forward a complete explicitly frozen selection and checked per-component projection
  choices, preserving exact input model, component/site coverage, selected consumer,
  source authority and phosphate intent. Copy only declared closures into existing
  run-local roles before sealing. Never add a NAR pairing row to bypass lookup.
- The selected-Phenix configuration currently omits the existing `multiple_planes`
  recipe option used by DY. Carry that explicit option if this route needs it; do
  not silently regenerate using a different recipe or change old default bytes.
- Prove one fresh ordinary mixed-end construction/prepared request, compare its exact
  model/dictionaries to the accepted controls, then cold readback. Full frame pairing,
  automatic CLI activation and modified-input canonical seeding need separate scope.

After the bounded DY integration, return to Q06 achieved refinement geometry and
Linden's queued native owner/lifetime contract. No target/sigma change, new process
owner, automatic adoption or Q06 closure is implied by successful preparation.

**DF diagnostic complete; production restoration remains open.** C361 uses Hazel's
separately prepared canonical parent, with its recorded D:1 terminal-phosphate
operation intentionally moved before fresh Coot. Source-declared DNA metadata
passes existing native equivalence against the exact saved isolated model/PHIL.
C360 padding proof and the unchanged sanitizer independently authorize only A:12
OP3 removal. Existing whole-base transport preserves all 11 scaffold coordinates
and 838 other atom states; C1′–N1 is 1.49958 Å instead of curated placement's
1.60172 Å. The independent full construction audit passes, including final phosphate
checks. This is construction evidence, not linked/refinement acceptance.

Hazel completed the matched linked/recipe-preflight and five-cycle comparison using
coordinate-only intake with B/Q, Hg and outside-site states preserved. Declared links,
source and custom restraints survive, but C1′–N1 stretches again to 1.66244 Å
(and N1–C2 also worsens). Construction is not sufficient under the diffraction
objective. Do not adopt the endpoint or tighten sigmas ad hoc. Hazel's pushed Alder note is `47e7b333`; the C363 ledger binds the exact compact
review/preflight/refinement receipts. C361 construction evidence remains valid.
Serialized C1′–N1 is 1.662146 Å; the native full-precision endpoint is 1.662440 Å. Historical curated sulfur/iodine
placements may repair bad raw substituents, so blindly switching every curated
residue to whole-base transport is not justified. Reuse C17/C62's frozen primitive;
a general production selection rule remains a specific Q06 follow-up.

Linden's W111 local counted-extension control reconciles native/subset restraint
counts and forces through the actual model manager. It remains an unqualified
local facade, deliberately refused by C331. Preserve both hierarchy Cartesian and
scattering fractional coordinates in any later owner contract. No active callback
admission, altered weights or lifecycle approval is implied; shared owner work is
queued separately and Cedar's C331 remains unchanged.

## Current result and next bounded task

**DY is an explicit, tested chemical source; ordinary automatic mutation is still
open.** Installed package lookup, source composition and explicit source freezing
now feed the existing acquisition owner. C355 reuses C342's exact isolated native
qualification without its SDK. C356 reproduces all 25 files of C345's mixed
free-OH/internal DY bundle and the exact saved ReadySet/native result after
relocation: 87 PASS, two unsupported formal-charge readbacks. Selection remains
`readyset_checked_model` for a diagnostic phase, not automatic adoption.

The [DY task](cif-doctor-completion-queue.md#dy--packaged-retained-triazole-reference-and-mutation-support)
has three remaining integration steps:

1. **Explicit planning now works (C358).** A chosen chemical source and canonical
   parent pass existing DNA graph/chi-frame and explicit D-deoxy stereo checks.
   Ordinary request forwarding remains open; no pairing record or Y/YTR alias.
2. **One mixed-end Coot request now works (C359/C362/C363).** Explicit site dictionaries build
   both DY sites in either order with exact scaffold/neighbours and chi <0.014degrees.
   Phenix passes87 checks/two unsupported charge readbacks. C362 now derives the
   projections from canonical input and C363 retains that exact derivation.
3. **Carry the source and choice through existing lineage.** Bind composition inputs
   and selected dictionaries through the existing construction/request owners;
   C364 completes composition retention; C365 completes the qualified source join.
   Ordinary pre-Coot forwarding above is next.
   C353 retains canonical seed proof; C355/C364 own frozen source bytes/composition; C359 carries
   exact site dictionaries through existing lineage and complete requests.
   Verify installed, relocated readback without original paths. Do not add another
   source, process or proof owner.

Reuse completed controls instead of regenerating unchanged dictionaries. C356's
machine-readable audit names the existing functions and acceptance criteria.
After this bounded integration, return to **Q06 achieved refinement geometry**,
then Q07's combined and unfamiliar-ligand challenges. The
[completion queue](cif-doctor-completion-queue.md#pipeline-position) is the sole
unfinished-work order. A readable CIF or passing derivative check does not close Q06.

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

- C365: **135 focused / 100.82s; 38 ordinary compatibility / 8.49s;
  173 installed/relocated**. Six new source-join cases fail before the correction.
  Actual composed DY/prepared intake replays cold; no native execution/full suite.

- C364: **299 passed in 331.20s (0:05:31) focused**; installed/relocated result is in the
  evidence ledger. 34 new cases, with 19 missing-API failures and one later
  unbound-member failure before implementation. No native execution/full suite.

- C360: **281 focused / 12.19s;281 installed/relocated / 10.26s**.15 new
  cases;14 initial failures before implementation. Real Coot control ~4.00MB,
 67 native PASS/one unavailable formal-charge readback. No full suite.
- C359: **264 affected tests / 9.09s**, then **31 changed-file checks / 3.26s**
  including two further regressions; **266 installed/relocated / 8.73s**. Native
  control ~4.59MB;335 prior files preserved. Initial pre-launch harness failure
  retained; missing-fixture installed harness corrected and disposable copies removed.
- C358: **143 focused / 3.58 s; 143 installed/relocated / 2.94 s**.25 new
  planning cases; initial23 fail before the API. No native execution/full suite.
- C355: **160 focused tests / 63.45 s; 160 installed/relocated / 65.00 s**.
  Default source-selection bytes exactly match C354; old/new readers cross-read.
  C356 is exact saved-evidence replay, not another native run. C357 checks documents,
  historical retrieval and cleanup inventories; no pytest/full-suite rerun.
- Last full Cedar suite remains **C220 / `583d30df`: 9,178 tests + 276 subtests**.
  It is not a full pass for current Cedar. The older C322 combined-source result
  was four failures / 11,109 passes + 284 subtests; integration must resolve those
  failures and preserve both TopoStitch HTML and Cedar replay resources.
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
before touching shared interfaces; do not edit another agent's worktree. Linden's
W109 proposal remains gated on active callback ownership, buffers and actual model
normalization/counts; C331 stays idle. Hazel's DF rebuild control must distinguish
base reconstruction from repairing an already strained glycosidic anchor/sugar.

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
