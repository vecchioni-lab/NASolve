# NASolve development handoff — current state

Updated **2026-11-16, C331 qualified live-policy guard — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. Current delivery **C331**; prior
published **3bd46f6e (C330)** and product **11fd6ee6 (C328)**.
Focused checks only; no Rowan full suite, branch, default activation or merge.
Linden owns Pine/Willow and does not edit Cedar.

## Current work and interruption recovery

**C331 qualified (source and packaged API):** the C330 read-only
live-policy owner now snapshots complete supported native tables, assignments,
exclusion/symmetry inputs and actual evaluation settings. It catches the observed
native-copy loss while permitting ordinary coordinate-driven and reset/rebuild
changes. No energy evaluator, native copy, manager mutation or ordinary activation.
The [current contract](architecture.md#live-nonbonded-policy-guard-c331) and ledger
`live_nonbonded_policy_guard_2026_11_16` hold the exact API, profile, limits and commands.

**Validation:** 198 focused passes with the opt-in native file skipped in ordinary
Python; 31 initial final-source native passes and **108 fresh-wheel passes**
(76 synthetic +32 native, including the added supported crystal wrapper control).
Phenix 2.2.1-6174 / dispatcher 2.2.1, Darwin arm64; real tiny native energy/gradient
execution, not diffraction refinement. No full suite. A 600-atom/1,797-operation
comparison measured about 29 ms after removing redundant serialization and an
expensive native iterator boundary, versus 205 ms initially; no capacity guarantee.
All probes finished. Raw logs, wheel/build scratch and benchmark runners stay local.

**Next:** Linden qualifies the direct optional consumer with identical actual flags
and explicit `compute_gradients=True`, normalizing nothing. Freeze both helper
and profile; source lifetime, atom identity, other forces and cache completeness
remain with existing owners. Captured-worker adoption is separate. Q06 geometry
is not closed: source-aware automatic bond-target discovery and faithful residual
review reporting remain the direct chemistry work. Do not repeat C329 or strengthen
restraints to force acceptance. No new fixed deadline supplied this morning.

**Prior work reused:** C323 authenticates the selected native numerical library;
C324 composes target-only changes through the existing chain/whole-bundle checks.
C325 supplies the byte-pinned public canonical replay frame from an installed
package. C326 delivers explicit graph-selected bond choices through prepared
execution and its immutable owner. C327 freezes the same choice through the
complete request, actual ReadySet, archive/retirement and moved cold readback.
No second process, chemistry or storage owner is needed. Exact older validation
commands and source/consumer pins remain in the existing ledger, not duplicated
here. Do not repeat native controls merely because context was compacted.

**C327 native boundary:** the fresh v4 control selected the corrected PDU target
**1.470 Å / ESD 0.020 Å**, preserving named heavy coordinates and ordered PHIL.
Original/final full derivatives and ReadySet native comparisons passed under
Phenix **2.2.1-6174 / dispatcher 2.2.1, Darwin arm64**. Whole request retirement:
**234,017,802 → 40,735,983 bytes**; moved cold read preserved all 141 files in
87.15 s with original inputs/SDK/store blocked. Raw science stays local.

The first v3 request completed repair/ReadySet but exceeded the combined repair
working bound. It remains failed and unpacked, with all 853 files preserved.
Fresh explicit v4 separates native captures from derived evidence: each group's
128 MiB/1,024-file and each member's 32 MiB limit remain fixed, as does the shared
128 MiB archive expansion cap. V3 retains its meaning/default. One successful
control does not establish 100-dataset capacity or refinement survival.
Native roots under the live-test anchor:
`327_Cedar_complete-bond-readyset-v0v9evls` (preserved failure),
`327_Cedar_complete-bond-capture-policy-b1fuaz79` (successful archived request).

**C328 complete:** ordinary request constructors and checked `prepare_postmr`
Python entry accept explicit source-neighborhood atom pairs. Shared declaration
validation runs before tool setup; full frozen source validation remains with the
complete owner. These new requests use C327 v4; omitted choices retain the old
shape/default. Existing continuation accepts no changed choice. No CLI/campaign
option or automatic target-discovery rule. Current tests: 30 failures/9 passes
before the handoff, **191 focused passes (74.83 s)** afterward; existing complete
choice/continuation tests add **17 passes (45.21 s)**. Exact commands are in the ledger. C327's actual saved request
configuration rereads with all **141 files unchanged (1.27 s)**, without native
execution. This is configuration compatibility, not a repeated full native replay.

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

**Next:** source-aware automatic target discovery and faithful reporting of
remaining achieved-geometry reviews, using the established owners. Do not re-run
this same corrected-CIF delivery or strengthen restraints to force a pass. Any
new finite-motion/parameter experiment needs a specific hypothesis using prior
force/target evidence. Q06 still needs whole-substituent and related held-out
survival; Q07 mixed challenges remain downstream. Changed intent needs a fresh
request/run. Profile repeated evidence reads before optimizing and preserve exact
file/owner checks. No default activation or merge.

Linden reports W94's independent Willow runtime at eb8e5d6e (delivery 8399512a),
1,844 full tests +229 subtests and 139 fresh-wheel focused tests. W95/c4b601c9
records the proposed caller boundary; C331 integration is not yet qualified.
These are separate-branch checks, not a combined-source pass. The older C322
combined check remains 4 failed/11,109 passed +284 subtests; eventual integration
must resolve its failures and preserve both TopoStitch HTML and Cedar replay data.

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
`live_nonbonded_policy_guard_2026_11_16`. The packaged public PDB
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
