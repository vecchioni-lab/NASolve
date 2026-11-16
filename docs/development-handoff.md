# NASolve development handoff — current state

Updated **2026-11-16, C339 standard CCD model-coordinate seeds — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. C338 is pushed at `80c10e2c`;
C339 is this completed source checkpoint. No full suite, new branch, default
activation or merge. Linden owns Pine/Willow; C331 unchanged. Simon confirmed work
through **23:00 London**. All Rowan native/controller jobs stopped.

## Current result and next bounded task

**C339 complete:** DY exposed a generic format gap. The source-generation adapter
now accepts complete finite CCD `model_Cartn_x/y/z` when ideal/plain families are
absent, preserving source atoms/charges/stereo and marking the seed explicitly
non-independent. No mixing/filling incomplete coordinate families; all old accepted
seed precedence and bytes remain fixed. No DY-specific repair or target generation.

One real bounded eLBOW reader/handoff in
`NASolve-live-tests/339_Cedar_DY-source-native-fqx7w9mm` stops before construction:
exactly the five explicitly aromatic triazole bonds become order 1.5. Source
identities, charges, coordinates and sugar markers survive. Existing isolated-six
and fused-purine representation rules correctly refuse this unsupported five-ring
conversion. No candidate, native qualification, ReadySet, Coot, linkage or refinement.
All owned attempts/controller stopped; active=false, 444,638 bytes retained locally.
The failed request replays after relocation with its temporary original absent and
native execution forbidden; 366,992 temporary replay bytes removed.

Focused command/result in ledger `declared_model_coordinate_seed_2026_11_16`:
263 pass initially; five process-identity tests cannot observe macOS process state
under the restricted sandbox, then **all five pass** with approved host visibility
(2.72 s), with no process-owner code change. Initial two new regressions fail on
C338. Installed/relocated package: **56 pass (5.30 s)** after source/original-install
removal. Wheel SHA `258ce832fb68efb4199f43c49c725443763601335cf231dce7e37266a3fc8194`;
1,371,603 bytes, 10,683,201 temporary bytes removed. A test's checkout-relative ligand
lookup was corrected to the packaged resource. No full suite; last full remains
C220/583d30df: 9178 tests +276 subtests.

**Next:** add a separate explicit neutral C/N five-membered aromatic representation
rule. Reuse C117/C118/C121 source/native contracts, require source-declared aromatic
edges, complete valence, one pyrrolic donor, unchanged H/charges and single bridge
substituents, and test negative controls/renamed related rings. Keep historical
policies fixed; no inferred tautomer, protonation or native bond-order edit. The
C4–N1T bridge remains single and inter-ring rotation stays legitimate. Then a fresh
owned DY attempt, not in-place retry. The numerical/reference/mutation gates remain
open. This is the next bounded task after the completed Q06 reporting connection.

Runners `c339_start.py`, `c339_worker.py`, `c339_package_check.py` live in everyday
ignored `branch-artifacts/cedar/runners/`; compact local checks are under
`branch-artifacts/cedar/c339-dy-source/`. Only source/tests/docs and compact evidence
committed; raw native outputs remain local. Historical runs and NAR workbook unchanged.

Linden reviewed C338's helper/registry boundary and found no direct conflict with
pinned C331/Willow, **not** combined-runtime qualification. Intra-site triple reporting
must not become backbone/seam approval. Queue one complete Cedar suite at a sensible
consolidation/before merge, respecting Simon's current no-full-suite instruction.

**C338 complete:** the explicit checked refinement route now observes selected
source-declared triple sites inside the actual Phenix manager, recording original
monomer definitions, heavy-atom geometry and local effective restraints. It retains
original summary behavior and verifies identity in the final model. Final-export
state and exact written model bytes are bound; filename resolution occurs before
Phenix advances its output serial. Full native coordinates remain distinct from
rounded PDB coordinates. No extra native capture or whole-model inventory.

Normal AutoRefine reports/checkpoint metrics now expose this scoped chemistry
screen. Real REVIEW preserves usable output and prevents automatic selection.
Optional unavailable observation stays UNASSESSED; it does not discard usable
refinement. Damaged saved evidence still refuses. This is reporting, not a force,
target, phosphate, Free-R or threshold change. Only explicit source triples are
screened; whole-substituent and diffraction approval remain separate.

**Validation:** 423 focused tests +19 subtests pass (37.00 s). Fresh wheel installed
and moved after build source/original installation removal: 155 pass (20.58 s).
Wheel SHA `cbf8aa329cc1dbd5db8a1d95c279388e3e505dadd3e8fd4a8cff574683890c14`;
1,371,485 bytes; 10,678,831 temporary bytes removed. New writer-observation regression
fails on parent `649e41a4`. Frozen v1/v2 cold/relocated readers pass. No full suite;
last full remains C220/583d30df: 9178 tests +276 subtests.

Actual **Phenix 2.2.1-6174 / dispatcher 2.2.1**: isolated zero-cycle preflight plus
five real cycles, nice 10, one process, 270.10 s. Local root
`NASolve-live-tests/338_Cedar_compact-refinement-567jpr2k`; active=false, all two
native and one controller processes verified stopped. All 168 historical C329
files/timestamps unchanged. Compact observations 27,099/27,361 bytes; whole control
7,301,945 bytes (not a peak-memory/campaign-capacity claim). No Coot run.

The 22 selected heavy atoms in the 855-atom model, monomer definitions and all
selected proxies exactly match C337; the written whole-model inventory matches as
well. PDU targets PASS; 1.213226 Å triple distance, angles 175.4494°/174.4251° keep
coordinates REVIEW. Native/PDB rounding differs by up to 0.000483945 Å. This is a
reporting acceptance control, not a new target/force experiment or modified-crystal
validation. Cold replay preserves all 57 control files and launches no process.

**Compatibility:** frozen helper/runtime v3 adds optional source-projection and
compact observation fields to the existing request/receipt, plus ordinary
`chemical_geometry` statistics. Checkpoint-registry schema/public registry APIs are
unchanged. Old v1/v2 helper identities remain frozen; explicit separate native
receipts retain C336's different interpretation scope. No historical migration.

Exact commands, source/receipt pins and scope:
`compact_refinement_observation_2026_11_16` in the maintained evidence ledger.
Everyday ignored runners: `c338_start.py`, `c338_worker.py`, `c338_readback.py`,
`c338_package_check.py` under `branch-artifacts/cedar/runners/`; package/replay
receipts under `branch-artifacts/cedar/c338-refinement-observation/`. Source/tests,
maintained docs and compact evidence only are committed; models/data/logs remain
local. Runtime modules and normal reporting changed; no new execution owner.

**Next:** qualify the already packaged DY chemical reference through existing
source/native boundaries. This follows the completed bounded reporting connection;
it does not close Q06. Then resume whole-substituent/held-out survival. Keep original
PDU bending visible, full precision distinct, and source-graph-selected mechanics
independent of ligand code. Consult the queue/history before adding another route.

**C335:** DY is now a packaged reusable chemical reference under
`data/chemical_references/DY.cif` with relative-path/hash provenance in `DY.json`.
It is the retained triazole free nucleoside, renamed from the user-approved YTR
preview with coordinates/graph unchanged and explicit sugar stereo added.
No runtime mutation, NAR edit, numerical restraints or phosphate inference.
C338 reporting is complete; continue the bounded
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
