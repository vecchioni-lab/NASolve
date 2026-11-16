# NASolve development handoff — current state

Updated **2026-11-16, C350 held-out ring qualification — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. C349 pushed at `3b11fdf0`; C350 is this
completed code/evidence checkpoint. No full suite, branch, default activation or
merge. Linden owns Pine/Willow; frozen restoration/C331/C338 unchanged. Simon
confirmed work through **23:00 London**. All Rowan jobs stopped at this checkpoint.

## Current result and next bounded task

**C350 complete:** public PIM passes all21 isolated native checks after an explicit
reader-copy correction to its contradictory SINGLE/aromatic bridge flag. Native
bridge remains single; no plane spans both rings. No name exception/default change.
Root `350_Cedar_PIM-ring-control-3_11z738`,11.75s/~3.49MB, all jobs stopped.
Cold relocation preserves106 files/timestamps, removes2.81MB scratch. Complete
Phenix2.2.1-6174 generation/qualification; formal-charge readback unsupported.
350 focused/29.72s and350 installed relocated/30.70s pass. Historical input bytes,
DY contract and native worker exact. Two failed attempts remain preserved.
Evidence: `cycle_local_public_ring_control_2026_11_16`.

**Next:** independent ring rotation/bending response, then deterministic prelaunch
timeout cold-reader repair. Restricted focused testing exposed missing
`representation_validation` when a0.5s allowance expires before candidate launch;
proper process access passes but that branch still needs a deterministic check.
Qualified source/context selection and Q06 geometry stay open. No full suite.
Simon now explicitly permits coordination with Hazel as well as Linden.
Older next statements below are historical.


**Earlier C344 complete — Rowan.** C343 pushed `e4f7ef7f`; C344 is this docs/evidence
checkpoint. All jobs stopped, no code/default changes or new pytest run; C343's
36 direct / 186 installed focused passes remain current. Continue through 23:00.
Successful root `NASolve-live-tests/344_Cedar_DY-free-end-native-ah13s9fb`, 7.85 s,
about 7.41 MB. Existing terminal-resource/site APIs qualify explicit free-OH DY,
then ordinary Coot constructs it using that exact projected dictionary. Native
counts: initial 65 PASS, actual Coot model 66 PASS, each one UNSUPPORTED formal
charge readback. No phosphate atoms at the free end; base/parent chi/outgoing link
survive. Coot1.3.3, Phenix2.2.1-6174. Cold relocation preserves119 files and exact
results, launches nothing. First `344_Cedar_DY-free-end-native-ee6th6ki` harness
mis-unpacked `(path,code)`; all jobs dead before fresh retry; failed files retained.

**Important correction to older C343 planning:** `sanitize_phosphates` removes
only OP3 with a proven incoming bond, not a whole phosphate at a free end. The
successful route prepares the explicit free-OH dictionary before Coot. Do not
weaken the sanitizer or infer end state from missing atoms. Ordinary automatic
per-site dictionary selection is still open; this is an explicit caller control.

**C345 completed:** Coot adds internal DY beside the C344 free-OH DY in one
fragment. Existing bundle preparation yields 87 PASS / two unavailable formal-charge
readbacks. Observed ReadySet passes all eight checks, preserves heavy coordinates
and exact numerics, and calls no observed builder/template. Fresh endpoint native
mechanics pass; the existing decision chooses `readyset_checked_model`, diagnostic
continuation only. No inferred DY pairing or automatic alias/per-site selection.
Root `345_Cedar_DY-mixed-ends-readyset-ghxi92ze`: 16.78 s, 5.92 MB; all jobs stopped.
Cold relocation reproduces the exact result with execution forbidden; 136 original
files/timestamps preserved, 5.70 MB temporary replay copy removed. Coot1.3.3,
Phenix2.2.1-6174. C343 focused tests remain current; no new pytest/full suite.
Compact evidence: `mixed_dy_end_states_readyset_2026_11_16`.

**C346 complete:** canonical MR → A:12 DA/B:4 DY, full-scaffold native
preparation (103 PASS / one unsupported formal-charge readback), observed ReadySet,
then five actual Phenix cycles with original Free-R and D:1 protection. This is a
covalent-only substitution control, without NAR pair/stack restraints or a DY
pairing hypothesis. It uses the separately declared C303 scaffold, not the original
symmetry-linked B:1 case. Exact actual-manager definitions/targets survive, final
model is bound. The two ring RMS plane deviations finish 0.02070 / 0.002515 Å;
bridge 1.377807 Å against 1.377 Å, chi changes 10.95°, all three sugar signs remain.
N1T bridge elevation improves 8.39°→2.84°; no added plane/weight or common ring plane.
Root `346_Cedar_DY-covalent-refinement-ljkqwcjn`, 56.07 s / 36.95 MB; all jobs dead.
Cold replay preserves168 files, removes36.95 MB temporary copy. Compact evidence
`dy_actual_refinement_survival_2026_11_16`. Raw scientific files remain local.

**C347 complete:** ordinary Coot execution checks the actual residue identity
immediately after canonical mutation, before parent snapshots or ligand placement.
Native success code alone is insufficient. Eleven new regressions fail on C346;
109 focused pass /2.23s and109 installed/relocated pass /2.46s. Three historical
script comparisons retain exact bytes. Complete Coot1.3.3 negative PDU→DT and
positive canonical→DA/DY controls pass; all jobs stopped. Root
`347_Cedar_Coot-canonical-identity-j1ybx5y8`,1.78s/~0.82MB. First `wjk8attm`
ran both controls then failed a local buffered-stdout assertion; it is preserved.
Fresh positive verification uses saved model identities. No new refinement/full
suite, alias, source chemistry or weight changes. Frozen restoration/C331/C338
helpers untouched. See `coot_canonical_identity_2026_11_16`.

**C348 complete:** pure explicit `canonical_parent_seed` preserves the incoming
DNA sugar/phosphate/anchor and places the complete supplied canonical base rigidly.
33 new regressions;142 focused /2.42s,142 installed/relocated /2.89s. Actual Coot1.3.3
PDU→DT→DY and DY→DT→PDU both pass, all11 scaffold coordinates exact, unselected
heavy coordinates unchanged, final chi within0.02° of original. Root
`348_Cedar_modified-canonical-roundtrip-2onapiub`,2.09s/~1.41MB; source files unchanged.
A native generic torsion matcher missed by5.18899° (guard retained); local prototype
success and a bare-TER format refusal also remain preserved. No Phenix rerun.
Evidence: `source_bound_canonical_roundtrip_2026_11_16`.

**C349 complete:** existing `construct_postmr_model` now accepts explicit per-site
incoming-source/canonical-template pairs. One ordinary Coot stage follows the saved
seed; original model/actions remain phosphate context authority. Both PDU/DY round
trips pass with `CONTEXT_PREPARED`, only proven internal OP3 removed and all11 input
scaffold coordinates exact. Root `349_Cedar_ordinary-canonical-input-isgh8jh6`;
all source/process checks pass. Exact cold replay preserves53 source files/times,
removes335205B temporary copies, launches nothing. Only input/final model are saved
for any number of seeds; shared dictionary copies and per-site proofs suffice.
160 focused /4.27s,83 existing-caller checks /8.85s,160 installed/relocated /3.48s.
The earlier successful prototype `mnj0fwxk` remains intact with exact changed source
preserved separately. No new Phenix/refinement/full-suite/default call. Evidence:
`ordinary_explicit_canonical_input_2026_11_16`.

**Next:** qualified source/context selection and held-out rotating-ring control.
No automatic DY alias yet. Explicit template/source choice is not fresh chemical
qualification; modified sugars and cross-family placement remain outside this rule.
Both C346 failures remain preserved: unsupported native PDU parent conversion,
and a harness scope mismatch for refinement-only terminal angle changes. C346's
successful canonical-input result is independent evidence, not a repaired failure.
Older active/next paragraphs below are retained evidence, superseded here.

**Latest C343 complete — Rowan, 2026-11-16.** C342 pushed `d17dd326`; C343 is this
code/evidence checkpoint. All Rowan jobs stopped. Continue through 23:00 London,
focused tests only. Older active/next statements below are superseded by this
paragraph; their evidence is preserved for continuity.

The existing source-DNA metadata adapter now forwards optional representation
policy through source assessment and both native checks; default receipts and
all chemical/numerical rows stay unchanged. Actual Coot 1.3.3 / Phenix 2.2.1-6174
construct internal DY at A:12 of an explicit A:11–13 test fragment. Parent chi,
whole-base transport, both native links and intended phosphate state survive:
67 PASS / one UNSUPPORTED formal-charge readback. Diagnostic continuation only.
Successful root `NASolve-live-tests/343_Cedar_DY-internal-native-m_w8cvlk`, 5.63 s,
about 5.97 MB. Exact cold native/header replay passes; 80 files/timestamps preserved.
First harness `343_Cedar_DY-internal-native-9k0l_bjs` used an invalid PHIL adapter
name after successful Coot; preserved and verified stopped before fresh retry.

Validation: 36 direct focused tests / 1.15 s; 186 installed relocated / 13.26 s. Eight new
regressions fail on C342. One initial fixture-directory mistake was corrected and
covered by both later passes. Exact commands/hashes:
`explicit_metadata_linked_dy_2026_11_16`. No full suite; last full remains C220.
No raw scientific artifacts committed; ignored runners/receipts use `c343_*` and
`branch-artifacts/cedar/c343-dy-source/` under the everyday checkout.

**Next C344:** free-end DY, using ordinary construction followed by the existing
explicit phosphate sanitizer and captured terminal-resource preparation. The
shared construction helper alone proves internal OP3 removal; inspect its raw
fallback at a free end before altering anything. Reuse the later ordinary PostMR
sanitizer with the original reference, then exact site/native checks. Do not
invent another phosphate rule. ReadySet/refinement and alias activation follow.
The C4–N1T bond remains rotatable; do not add weights just to pass a screen.

**C343 active:** existing source-DNA metadata adapter predates explicit aromatic
representation policies. Forward the same optional caller policy through its
assessment and native equivalence; default serialization unchanged. Eight new
regressions fail on C342. Then use this source-owned numerical header for actual
Coot construction and existing linked/free-end native preparation, without manual
header edits or a second chemical validator. C342 pushed `d17dd326`.

**C342 complete:** pure `compose_dna_source` preserves the explicitly selected
DNA sugar/phosphate and the complete reference base. Source H/D/charge/stereo,
matching deoxy hand and relative configuration are checked; source/atom provenance
accompanies new constructed-seed coordinates. No native targets, source edits,
model mutation or alias activation. Conventional unbridged N-glycosidic deoxy
scope only; no E/Z or extra stereocentres. Reuses C291 frame and C116 atom ordering;
`postmr_restoration.py` bytes and historical frozen policies remain untouched.

Fresh successful native control:
`NASolve-live-tests/342_Cedar_DY-DNA-source-native-1veizued`, 25.73 s, about 5.21 MB.
Phenix 2.2.1-6174 / dispatcher 2.2.1: all 21 isolated checks pass. Candidate SHA
`692d27c45775f13bf017deaa3b822ea315466b0b8f1b6a854eb47d786cf0a732`.
Cold relocated acquisition and exact source recomposition pass without native
execution; 104 original files/timestamps preserved. The first failed lexical-order
attempt, `342_Cedar_DY-DNA-source-native-ga0h4avb`, remains intact: eLBOW added a
nonchemical C3T–C1′ bond at 7.72 Å, the known C116 Z-matrix ordering failure.
Connected whole-row ordering changes no declarations and succeeds in a fresh run.

Validation: **192 focused / 5.90 s; 192 installed relocated / 6.02 s**. An installed
harness initially lacked one legacy test's tree-relative data fixture; corrected
from wheel resources, not a product change. Successful build/replay scratch copies
removed. Exact evidence: `explicit_reference_composition_2026_11_16`. Last full
suite remains C220/583d30df, 9178 +276 subtests; no full suite this turn.

**Next C343:** use existing stored-dictionary site preparation and native context
owners for linked/internal and free-OH/terminal controls, then whole-base mutation.
Do not bypass source authority or add a new execution owner. Source DT OP3/HOP3 is
a declared leaving cap, not model OP3 authority; OP2 H/charge remains explicit.
C342 is an isolated source qualification, not linked/refinement approval. Preserve
DY C4–N1T rotation and inspect junction survival rather than adding weights now.

**C340 complete:** the new explicit neutral five-membered C/N aromatic policy
recognizes the source-declared triazole without changing native bond orders.
It requires complete conversion, two nonadjacent doubles, one valence-complete
pyrrolic nitrogen, fixed H/isotopes/charges and single bridge substituents. Related
pyrrole/diazole/triazole, renamed/reordered and negative cases are covered; old
six-ring/purine/oxo policies and worker contracts remain unchanged.

Fresh native root `NASolve-live-tests/340_Cedar_DY-five-ring-native-m14ht3ff`:
actual eLBOW construction plus existing two-seed isolated qualification succeeds
in 12.99 s, Phenix 2.2.1-6174 / dispatcher 2.2.1. Candidate SHA
`8099ad00e640d941e1ff0289a3fb56ca558360d92acfe0c4c707a60516cd2c1e`, 12,742 bytes.
Whole local control about 4.73 MB, active=false, all children/controller stopped.
Source unchanged. Cold relocation passes with original temporary path absent and
native execution forbidden; all 102 original files/timestamps preserved. No
ReadySet, Coot, linked mutation or refinement approval. Native formal-charge
readback is unsupported; absolute CIP assignment NOT_RUN.

**Validation:** 346 focused tests pass (23.60 s); 184 installed/relocated tests pass
(14.41 s). New positive regression fails on C339. Wheel SHA
`f8b1f7f4ddf13c817192672801c8b3382488d3775a62fe3aef0b3abda8024274`, 1,373,537 bytes.
10,700,189 package bytes and 3,973,709 successful replay-copy bytes removed. One
local replay harness initially assumed the wrong API return wrapper; corrected,
with its temporary copy removed. No production defect or failed native attempt
was erased. Exact command/evidence in `neutral_five_ring_representation_2026_11_16`.
No full suite; last full C220/583d30df: 9178 tests +276 subtests.

**C341 complete:** one fresh successful fixed-manager response control in
`NASolve-live-tests/341_Cedar_DY-junction-response-jkoofks8`, 2,229,480 bytes.
Exact C340 native inventory/manager match; 1,877 native evaluations. Rigid ring
spin at ±30/90 degrees leaves every covalent target unchanged (numerical error
below 1e-12); only nonbonded contacts change. Tilting the ring about its pyrrolic
junction leaves internal distances/bridge length fixed and increases the angle
target: +5/10/20 degrees give +0.00652/+0.10587/+1.64511. Initial/spin30/bend10
sampled gradients pass, with all static restraints unchanged. No optimizer,
model, force, plane or dictionary change; no quantum torsion-barrier claim.
No need to add a junction plane solely because it is absent. Adequacy under
linked/refinement forces stays open. The first local harness run used the wrong
atom-record field; it stopped before controls, is preserved at
`341_Cedar_DY-junction-response-ovxv4xh_`, and was verified dead before the fresh
run. All jobs stopped and all C340 files/source unchanged. Exact compact evidence
is `dy_junction_response_2026_11_16`; runners `c341_start.py`/`c341_native.py` remain
in the usual ignored local runner folder. No new pytest run for this docs-only
checkpoint; C340 focused tests remain current. No full suite.

**Prior planning (superseded by C342/C343 above):** source-owned linked/terminal DY preparation, then whole-base
mutation. Read C133–C139 plus later construction docs before choosing the path.
The packaged reference is a free nucleoside: explicitly verify the existing
backbone-source/context contract, rather than inventing a phosphate or bypassing
source authority. Reuse existing preparation/acquisition/qualification owners.
ReadySet/Coot/refinement and related controls still gate mutation activation.
Keep nitrogen-junction survival visible without changing weights pre-emptively.

C339's complete CCD model-coordinate adapter and failed reader attempt remain
recorded in `declared_model_coordinate_seed_2026_11_16`; source/model coordinates
are non-independent seeds, not calibrated targets. DY packaged definition/metadata
and aliases remain unchanged. C4–N1T is not a phosphate or an inter-residue link.

Ignored local runners `c340_start.py`, `c340_worker.py`, `c340_readback.py`,
`c340_package_check.py` live under everyday `branch-artifacts/cedar/runners/`;
compact receipts under `branch-artifacts/cedar/c340-dy-source/`. Source/tests/docs
and compact evidence only committed; native outputs remain local. NAR untouched.

Linden completed W99/read-only C338 boundary review and is running sequential W100
source controls, one nice-10 worker. No direct C338/pinned-C331 interface conflict
found; combined-runtime qualification is not claimed. A later full Cedar suite
is queued for consolidation/before merge; current instruction is focused only.

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
