# NASolve development handoff — current state

Updated **2026-11-16, C336 exact-checkpoint chemistry reader — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. C336 validation complete; no full suite,
new branch, default activation or merge. Linden owns Pine/Willow, currently W99
native trials on unchanged C331. Simon directly confirmed work through **23:00
London**. No Rowan native/controller job is active.

## Current work and interruption recovery

**C336:** a read-only Python report follows an exact refinement checkpoint to its
own selected preparation and source-bound site projections. Optional preserved
native evidence must describe the exact final PDB and ordered execution CIF/PHIL;
namespace adaptation is reused. Existing triple screening separates target and
coordinate results, keeps real bending REVIEW, and reports absent evidence or no
supported triples as UNASSESSED. No changes to forces, numerical acceptance,
checkpoint schemas, saved scientific files, C331 or frozen v2 helper sources.

Prior-work review: C334 supplied the site-scoped screen. Ordinary v2 refinement
records output synchronization/parallelity usage but not the complete final native
inventory. The new report therefore labels separate final-model reinterpretation
explicitly; it does not claim the actual refinement manager was captured. The
registry reader retains call-local preparation results instead of replaying the
complete history twice; its existing public return and validation stay intact.

**Validation:** 359 focused tests +29 subtests pass (31.38 s), including 21 new
report checks. Fresh installed/relocated wheel: 21 pass (3.93 s), with temporary
build source and original installation absent. C329/C334 native-evidence replay
reproduces every scoped triple result in 0.97 s, preserving all 190 historical
files/timestamps and launching no native job. Prepared geometry passes; final
PDU targets pass while the existing 173.9366° bend remains REVIEW. Recorded
capture build: Phenix **2.2.1-6174 / dispatcher 2.2.1**, not rerun; Coot not run.
Initial new-entry regression fails on the prior revision with ModuleNotFoundError.
No full suite; last Cedar full gate remains C220/583d30df, 9178 +276 subtests.

Exact focused command (Cedar cwd):
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_refinement_chemistry.py tests/test_checkpoints.py tests/test_autorefine.py tests/test_coot_view.py tests/test_refinement_parallelity.py tests/test_refinement_inputs.py tests/test_cif_postmr_publication.py tests/test_cif_campaign_first_refinement.py tests/test_cif_triple_bond_audit.py tests/test_cif_construction_native.py --tb=short`.
Installed runner: `branch-artifacts/cedar/runners/c336_package_check.py` with
Phenix Python, offline wheel build; replay: `c336_site_readback.py` with project
Python and `PYTHONDONTWRITEBYTECODE=1`. Both live in the everyday ignored runner
folder. Wheel SHA `f96325d9c7465d80de3258ee75c0b23d526b11152ac485001201e242ef89e21e`;
1,363,261 bytes, temporary 10,602,399 bytes removed. Compact ledger entry:
`refinement_geometry_report_2026_11_16`. No raw scientific artifacts committed.

Changed source: `refinement_chemistry.py` and call-local result plumbing in
`checkpoints.py`; new tests and maintained docs. Report schema/policy v1 is a live
read result, not a checkpoint migration. Historical bytes and defaults unchanged.

**Next:** connect collection/reporting through the existing refinement owner;
the Python reader is complete, automatic capture and normal saved output are not.
Retain actual-manager versus separate-interpretation limits, bounded storage,
explicit unavailable evidence and independently usable fallback. Then take the
queued DY qualification slice; whole-substituent/held-out survival still gates Q06.

**C335:** DY is now a packaged reusable chemical reference under
`data/chemical_references/DY.cif` with relative-path/hash provenance in `DY.json`.
It is the retained triazole free nucleoside, renamed from the user-approved YTR
preview with coordinates/graph unchanged and explicit sugar stereo added.
No runtime mutation, NAR edit, numerical restraints or phosphate inference.
The current Q06 step below stays first; then start the bounded
[DY qualification task](cif-doctor-completion-queue.md#dy--packaged-retained-triazole-reference-and-mutation-support).
Prior custom-input scope and source/context owners are recorded there. The original
visualization remains untouched; packaged data now removes dependence on its local
path. **54 focused tests pass (11.25 s); 4 installed/relocated checks pass
(0.14 s)** after removing the temporary build source and original install path.
ChimeraX **1.12**, complete file-read check: DY has the exact 33 atoms/35 bonds;
no Phenix/eLBOW/ReadySet native chemistry execution. The initial four reference
tests fail before data is added. No full suite; package/runtime defaults unchanged.

Validation command (Cedar cwd):
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaged_dy_reference.py tests/test_residue_aliases.py tests/test_curated_cif_loops.py --tb=short`.
Offline wheel command: `phenix.python -m pip wheel --no-deps --no-build-isolation
--no-index`; the ignored everyday runner
`branch-artifacts/cedar/runners/c335_package_check.py` removes its temporary source,
relocates the installed wheel, asserts the imported package location and runs the
four reference tests. Exact receipt: `branch-artifacts/cedar/c335-dy-reference/package-check.json`.
Wheel SHA `69cc5fab427fc0eab40a0195e43fdb539923050ab0d2614e6fc6e94078647849`;
1,360,216 bytes. Its 5,927,434 bytes of temporary build/install files were removed.

Included: user-authorized computed DY reference, compact provenance, packaging,
tests and maintained docs. Excluded: vendor drawing/HTML, local viewing outputs,
logs and all diffraction/live-test artifacts. New resource metadata version 1 is
not a request/checkpoint schema; no historical migration. Existing visualization
and unrelated dirty NARestraints files remain untouched.

**C334 read-only result:** the existing declared-projection reader now confirms
B:4's 22 heavy atoms match its linked B:3/B:5 intent exactly. C329's full-runtime-CIF
comparison carried an isolated-versus-linked OP3 warning; the projected replay
removes only that warning. Prepared triple geometry passes the existing screen;
after refinement the target screen passes but the terminal-side angle stays
173.9366° and coordinate status stays REVIEW. All geometric measurements and
screen settings are unchanged, all 190 historical files/timestamps preserved,
zero new native jobs, 0.47 s replay. No runtime/schema/model changes. Exact binding
and commands: `declared_linked_site_geometry_readback_2026_11_16`. All Rowan jobs
are stopped; no further heavy checks are queued.

**C333 qualified:** explicit `automatic_bond_targets=True` now reaches checked
PostMR/ordinary/complete/prepared Python entry. Source/library-discovered pairs
are frozen after prior linear/plane stages, then use the existing candidate,
attribution, derivative selection, fallback and ReadySet route. One captured
library serves all eligible components. Matching/unsupported/nuclear-distance
cases remain visible; empty selection is not chemical approval. Defaults and
explicit pairs retain their previous shape. Automatic and manual choices cannot
mix; ordinary fresh requests use v4, with unchanged storage limits.

**Validation complete:** **658 focused passes (553.80 s)**, including 52 new
checks; **52 fresh-wheel passes (48.40 s)**. No full suite. The installed native
PDU control independently discovers C5B–C5M and returns the **same final model
and corrected CIF hashes as C327**, retaining 1.470 Å / ESD .020 Å, named heavy
coordinates and ordered PHIL. Original/final derivative and ReadySet checks pass.
Phenix **2.2.1-6174 / dispatcher 2.2.1, Darwin arm64**; no Coot or diffraction
refinement rerun. All 14 native phases and the outer owner are stopped. Historical
79 input files remain unchanged. Request retirement: **234,015,903 → 40,719,525
bytes**; moved cold read preserves all 141 files in 88.44 s with original code/
inputs/SDK/store blocked. Entire control 980.56 s. No active Rowan job remains.

Live-test anchor: `333_Cedar_automatic-bond-readyset-e73fslc3`; exact commands,
source pins, runner/output references and limitations are in
`automatic_preparation_bond_discovery_2026_11_16`. Local runners/logs stay in the
everyday checkout's ignored `branch-artifacts/cedar/`. Temporary native-copy code
was removed; raw science stays local. Fresh wheel SHA:
`5501b04b5495811de3487b5e7683d7853273c4d6c70958ef7b07434efc77c7c8`.

**Prior solutions:** C326–C328 already own prepared/complete/ordinary explicit
repair, fallback and immutable attempts; C332 supplies source/library selection
and historical PDU/5PC replay (182 files unchanged). C327's first v3 storage failure
remains failed/unpacked; never repair it in place. Its successful fresh v4 control
separates native captures from derived evidence without enlarging per-part or
shared archive bounds. These owners and their exact older evidence remain in the
ledger; do not rebuild them or repeat native controls after context compaction.

**Shared guard:** C331 source/profile remain byte-identical. Linden reports W96
and W97 qualify optional direct/captured callers, including installed relocation;
W98/7faff1a1 forwards explicit displaced starts through its existing trial and has
focused/full/installed results on Willow. Its native recovery comparison remains
separate/pending. Rowan reviewed the exact W98 runtime/test diff read-only, finding
no Cedar compatibility blocker; that is not native or combined-merge approval.
The [guard contract](architecture.md#live-nonbonded-policy-guard-c331) retains its
source/identity/cache obligations. No Pine/Willow edits or integration here.

**C329 complete:** exact C327 selected runtime → isolated zero-cycle preflight →
five real refinement cycles through the existing frozen v2 helper. Same C319 model,
ordered PHIL, observations/Free-R, four-process recipe and D:1 protection; corrected
CIF replaces old dictionary plus extra target-edit PHIL. No new checkpoint or
historical edits. Six native jobs and outer owner stop; source stays at C328.

Actual final GEO retains **1.470 Å / 0.020 Å ESD, component origin 0**; achieved
length **1.481829 Å**. All **45 planes/58 parallels** remain; complete prepared/final
native restraint definitions agree. PDB/mmCIF reproduce saved scattering, original
Free-R mapping intact, Rwork/Rfree **0.206236/0.236192**. Native build unchanged.
All **1,234 C303 files +141 C327 files** stay unchanged. Local control
`329_Cedar_corrected-CIF-refinement-3j49p8v8`: **30.63 MB**, 294.89 s total; no peak
or campaign-capacity claim. No raw model/CIF/MTZ/log upload.

**Q06 remains REVIEW:** PDU angles **175.019°/173.937°**, terminal plane offset
**0.258 Å**. C319 written atom records reproduce exactly; C308 native coordinates
and every restraint agree after accounting only for old edit-origin 4 versus
component-origin 0. Reuse C309/C314 force work instead of repeating it. The generic
isolated-reference triple diagnostic also sees OP3 absent at linked B:4; actual
native missing/unexpected heavy lists are empty under the existing declared site
modifier. This is a diagnostic reference-scope warning, distinct from bending;
never use it to add OP3 or alter the protected D:1 terminal state.

**Remaining scientific work:** whole-substituent and held-out achieved-geometry
reviews, using the established owners. Source-aware discovery is implemented by C333. Do not re-run
this same corrected-CIF delivery or strengthen restraints to force a pass. Any
new finite-motion/parameter experiment needs a specific hypothesis using prior
force/target evidence. Q06 still needs whole-substituent and related held-out
survival; Q07 mixed challenges remain downstream. Changed intent needs a fresh
request/run. Profile repeated evidence reads before optimizing and preserve exact
file/owner checks. No default activation or merge.

No combined-source pass is claimed. The older C322 combined check remains
4 failed/11,109 passed +284 subtests; eventual integration must resolve its failures
and preserve both TopoStitch HTML and Cedar replay data.

## Scientific findings and preserved evidence

**ReadySet reminder / C323 provenance audit:** the exact PDU source starts at
1.472376 Å. The source-preserving 180-step RM1/GDIIS output already writes a
1.607 Å target/0.020 Å ESD after reported nonconvergence; source and generated graphs
agree. Historical C206's 600-step control also writes 1.607 Å (ESD 0.040 Å), with
NOT_REPORTED stopping: no convergence claim. C304 ReadySet makes zero builder calls,
keeps the supplied dictionary and emits the same target. Local read-only audit:
`323_Cedar_target-origin-vehkjax0`; 10 original files unchanged. This establishes the
observed upstream failure/retention route, not failure of every fresh ReadySet path.
Keep native builders primary. Prefer a demonstrably better source-faithful native
route if available; do not repeat the same longer run without a new hypothesis,
copy coordinates into restraint targets or universally reject nonconvergence.

**C320–C322 completed foundation:** exact source/reference candidate delivery and
full native inventory checks; target-only single/container/whole energy and force
attribution; shared plane/bond owned lifecycle and SDK-free cold replay. PDU/5PC
energy differences are −55.15143/−11.10162 native units, force errors below 6e−14.
Actual options stay slack 0, limit −1, top-out false. C322 root
`322_Cedar_durable-bond-attribution-yn1bos1w` retains 60.8 MB diagnostic evidence,
not a new ordinary storage policy. The old plane worker bytes/readers remain exact.
Actual old PDU preparation/checkpoint read preserves all 1,234 files, selected
refine-001 and checkpoints through refine-003. Earlier checks need no repetition.

**C318/C319 final output repair:** a versioned explicit checked-refinement helper
synchronizes only stale final ADPs from the exact native scattering object before
export, keeping coordinates, FCALC and geometry owner. Actual five-cycle PDU
refine-003 remains unselected; PDB and mmCIF independently reproduce the saved
scattering result (Rwork/Rfree 0.206236/0.236192). Coordinates/printed geometry match
C308; old model files/selections remain. Roots `319_Cedar_ordinary-output-sync-_ycu9ff8`
and `319_Cedar_written-output-readback-0ed6xqcd`. No SDK edit, guessed combined
weight, restraint strengthening or optimizer-history reconstruction.

C308's matched 1.470 Å terminal target gives PDU/5PC lengths 1.4818/1.4864 Å.
PDU angles 175.02°/173.94° remain REVIEW; 5PC passes its scoped triple screen.
Geometry favors opening both tested PDU angles; reconstructed final diffraction
forces favor one and oppose the other. These are substituted-scaffold controls,
not diffraction from modified crystals. Do not call Q06 closed.

PDU run: `303_Cedar_PDU-campaign-btuh5sop/relocated-after-c304/DiU/AutoMR/run_001`.
5PC run: `305_Cedar_5PC-campaign-nu1t7jyw/relocated/DiU/AutoMR/run_001`.
Both are relative to the local live-test anchor, selected refine-001. Original
observations/Free-R, protected terminal chemistry and previous attempts remain.

## Queue, compatibility and collaboration

**Q04/Q05 accepted explicit route:** C285/d5996bc4. Q06 remains open; Q08 supplies
numerical diagnosis. The [completion queue](cif-doctor-completion-queue.md) is the
sole work order: mixed/unfamiliar controls, sugar/fluorine learning, PNA, locked
sugars, catalogue coverage, chemical states and false alarms remain. Q15 PDF and
Q16 AutoPhase/integration/platform/full-suite/release work follow. Last full Cedar
pass remains **C220/583d30df, 9,178 +276 subtests**, not this revision.

The existing `cif-linked-native-registration-evidence.json` ledger holds exact
commands, hashes, anchor-relative evidence and limitations. New entries:
`selected_native_energy_library_2026_11_15` and
`reference_bound_ordered_bond_chain_2026_11_15`, plus
`installed_historical_construction_resource_2026_11_15` and
`prepared_reference_bond_execution_2026_11_15` and
`complete_reference_target_delivery_2026_11_15` and
`ordinary_reference_target_entry_2026_11_15` and
`corrected_cif_refinement_survival_2026_11_15` and
`live_nonbonded_policy_contract_2026_11_15` and
`live_nonbonded_policy_guard_2026_11_16` and
`source_aware_bond_discovery_2026_11_16` and
`automatic_preparation_bond_discovery_2026_11_16` and
`declared_linked_site_geometry_readback_2026_11_16`. The packaged public PDB
retains its original fixed-column padding and exact hash. C325 whitespace checking
excludes only that byte-pinned PDB (`git diff HEAD^ HEAD --check -- .
':(exclude)src/nasolve/data/replay/5W6W_noPO4.pdb'`); all code/docs pass. Reuse the earlier C307–C322 entries
for target, force, writer and native identity evidence rather than duplicating it.

Original PDU:PDU **B:1 = incoming symmetry continuation P/OP1/OP2, no OP3**,
superseding free-OH. C295's B:7 O3′ image `-x+y,-x,z`, 3.34019 Å, is a candidate,
not confirmed linkage. D:1's separately declared complete terminal phosphate is
distinct. No blanket OP3 removal or lone symmetry bond without surrounding forces.
Pine owns editable intent; TopoStitch previews; Cedar enforces qualified chemistry.

The shared live-policy guard is now explicit; its caller integration and the
pure-view tensor/frame alternative remain separate, unactivated work. Generic deepcopy/pickle can drop native nonbonded
parameter tables; final ADP synchronization retains the same geometry owner.
Pure representative recuts may keep one computational owner and derive views, but
require explicit identity/tensor/inverse-edit checks; no chemistry approval follows.

Simon authorizes code/tests and compact evidence pushes. Raw science, full logs,
SDK source and local runners stay local. Preserve failed/active work; remove only
successful owned duplicates through qualified procedures. Check history before
new diagnosis; keep ideas queued unless explicitly redirected. Signed peer notes:
**— Rowan**.
