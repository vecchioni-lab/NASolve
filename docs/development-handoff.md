# NASolve development handoff — Willow

**Current maintained slice: W257, 2026-11-24**, code `dc50cf4e92dce776b67ca92bbe9a7713406b35bb`.
[Declared paths on original CIF sites](topostitch-preview.md#project-declared-paths-onto-original-cif-sites-w257)
binds every resolved registered node to a complete original site and partitions
every declared backbone edge into local adjacency or an explicit image boundary.
Original identities, chemical/unknown boundaries, protected/do-not-connect flags
and unregistered atoms remain visible. Branches, uncut identity cycles, incomplete
sites and multiple components aliasing one label-chain/sequence position refuse.
Path numbers are not new output chains; no writer or chemical inference is added.

**121 focused source / 121 relocated installed checks pass.** The complete Willow
suite passes **2,705 tests, four skips and 234 subtests**, with process inspection
permissions available. Hazel's independent review exposed one missing-entity position collision; its
regression fails before the fix, the reviewed final bytes pass, and the whole
validation is repeated for that semantic correction. Installed imports/help pass.
206 installation-file hashes verify after temporary build and old-install removal.
Four original 3LNA/5LNA cases reproduce W249 paths/operators exactly: all
1,271/1,275 atoms and 62 nodes/60 backbone edges; 4 paths/2 seams become 8 paths/
6 seams. No new native calculation, refinement or coordinate file is generated.
Exact commands, original failures, hashes and evidence are in NASolve anchor
`branch-artifacts/willow/w257-original-path-projection/`.

**P03 stays partial; next:** transport all original connection annotations through
the bound atom/image lineage, retaining unresolved rows and reasons. Cedar owns
sequence/backbone chemistry semantics; its O3′–P filter cannot establish coverage
of hydrogen bonds or other annotations. Compare complete references rather than
trust standalone CHECKED or unchanged scattering. Keep complete original polymer
coverage, general/special-position source validity, supported writing, P02 GUI,
native lifecycle and changed-child/inverse-edit binding as separate gates.
Rowan confirmed this ownership split; no Cedar source or shared caller changed.

W256's original byte/ID/component/raw-double XYZ/U context remains unchanged.
Its 217 source/217 installed and four exact numerical replays stay valid; the
W256 full-suite sandbox failure and five-test permission retry remain recorded,
not relabelled as a clean invocation. W257 now supplies the clean Willow suite.
This is not combined-branch integration or scientific/model acceptance.

**Coordinated geometry context: W255.**
[Cap and feasible-step diagnostics](topostitch-periodic.md#w255--record-the-coordinated-cap-and-feasible-step-diagnostics)
replace the previously queued 1.5→2 Å experiment: it has run once and stopped
after 27 accepted steps, with OP2's next proposal beyond the bound. The last
accepted bond/angle improves, but there is no candidate or optimum. A separate
projected diagnostic reaches its 100-iteration limit with residual 5.1565.
The feasible-basis native derivative audit passes (4.963e-5 against 1e-3), while
old centered endpoint checks remain unavailable and rounded PDB exceeds the cap.

Alder owns the independently reviewed pure helpers at
`7c2e1c41d969db7b047b242d847bf18ace49b531`; 53 focused/99 adjacent/53 installed tests
and 531 cold replay assertions pass. Nothing was merged into Willow, no trial
default changed and no repeated native experiment ran for this documentation.
Scope an explicit opt-in boundary-endpoint contract before receiving candidates:
gradient accuracy, projected stationarity, chemical geometry and actual serialized
point qualification are separate gates. Prefer existing full-precision receiving
support before new PDB lattice machinery. Hazel's pinned output review finds the
native worker already requests mmCIF, but its wrapper defaults to five-place XYZ
and Alder's endpoint auditor currently admits only three-place PDB. Format
availability is not receiving authority; qualify precision and admission together.
A separately named, opt-in constructed receiving seed need not claim optimizer
stationarity: it must retain complete source chemistry/atoms, evaluated actual
output, fixed context and a matched receiving control. Current W238 optimizer
acceptance and diagnostic no-candidate verdicts remain unchanged. This is a
planned distinct role, not permission to reuse an old native capture for new bytes.
No cap grid or automatic enlargement.
Later density-aware receiving and the existing fixed-weight confound remain open.

**Human checkout:** GitHub anchor
`ScienceCheckouts/Linden/2026-11-24_original-source-paths/index.html` and
`open_report.py` show the original/recut atom, path and connection counts with
links to exact local evidence. Four links and the Python 3.10 opener syntax pass.
This is a compact static science report, not the required future P02 editor.
Hazel's separate geometry report remains at
`ScienceCheckouts/Hazel/2026-11-24_feasible-helper-extraction/index.html`.
No newly bent model or deposition-ready recut is claimed. Exact W255–W257 scope,
failures and next actions are in the periodic ledger and machine roadmap.

W254's compact failed-proposal reporting remains validated (274 source/274
installed, one skip each); W255 used it to identify the rejected OP2 proposal.
It cannot retroactively recover W253's missing rejected atom. Earlier science
and native limitations below remain evidence; closed controls should not be rerun
merely because the handoff advances.

**W252 native implementation and validation.**
[The first phased six-role fit now completes](topostitch-periodic.md#w251w252--separate-native-output-completion-from-local-repair).
W251 finished its three refinement cycles but failed while writing optional
next-run defaults. W252 disables that output only for phased jobs; the same
request reproduces every native atom record exactly and passes Cedar's unchanged
written-model and returned-state guards. No force, fit setting or selection changed.

**Technical completion is not chemical recovery.** All 859 atoms, 853 fixed
positions, thermal state, 1,151 observations/HL quartets, 59 original Free-R flags
and complete fixed scattering survive. The actual MLHL target is observed at
97 evaluations (94 requesting gradients), with 97 complete image-force gradient
calls. Rwork/Rfree are 0.306743/0.342453. The image O3′–P gap shortens from 3.029
to 1.997 Å, but OP2–P–O5′ collapses to about 58°. No scientific acceptance,
checkpoint, density success or healthy closure is claimed. Hazel's independent
returned-state/boundary audit passes 4,720 cold checks and confirms the strain
(full-precision O3′–P 1.997399 Å); earlier raw-output diagnosis is retained.

W253 above records the subsequent same-parent geometry diagnostic and its stop.
The separate outward-phosphate whole-model child is not this parent. S05/S06
remain partial; no density support or accepted repair follows from technical completion.

Validation: **213 source/213 relocated installed tests, two skips each**, plus
one real Phenix PHIL regression passing before install and after relocation.
The regression fails against the previous code at `write_def_file=True`.
All 214 relocated installation files hash-match after build/original path removal;
Python 3.10 syntax and installed CLI help pass. Exact commands/logs are under the
NASolve artifact anchor `branch-artifacts/willow/w252-validation-qualified/`.
Two earlier test-launch environment failures remain recorded; neither is a code
pass. Full suite deferred per coordinated scoped development; merge integration
remains required. Source command: `PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=src:<qualified-test-dependencies> python -m pytest -p no:cacheprovider
-q tests/test_topostitch_phosphate.py tests/test_topostitch_endpoint.py
tests/test_topostitch_fit.py tests/test_topostitch_captured_job.py
tests/test_topostitch_capture.py`. Native regression commands are preserved in
`validation.json`; host test dependencies are appended after Phenix's own packages.

Complete native execution uses **Phenix 2.2.1-6174**, the installed owner, explicit
Cedar source, 3 cycles × 60 iterations, 1.5 Å maximum movement, `wxc_scale=0.5`
and a 600-second per-phase cap. This is adaptive native weighting, not a fixed
objective. Saved result: `branch-artifacts/willow/w252-phased-output-qualified/`;
original W251 and the earlier W252 host-dependency refusal are retained. The
reproduction authority is the full-precision frozen request and inputs, not
printed `.eff`/`.def` files. No request migration; legacy ML is unchanged.
Phased failure reports now retain admitted target-call counts without implying
successful evaluation or completion. Original W251 counts cannot be recovered.

W250's source/installed dry-run evidence, Hg spelling correction, strict-frame
refusal and phased-only arithmetic bounds remain in the
[admission contract](topostitch-preview.md#admit-experimental-phases-and-fixed-scattering-w250).
All scientific inputs, captures, generated coordinates and maps remain local.
Installation relocation does not establish portability of a moved native job.

[W249 carries the whole boundary graph in original mmCIF](topostitch-periodic.md#w249--carry-the-whole-boundary-graph-in-full-precision-mmcif):
all 62 sites/60 backbone edges, original atom IDs/A1C3T and 80/87 connection rows
survive. Eight recut paths carry 54 ordinary plus six image-spanning edges;
6/5 rows are added because one 5LNA boundary was already explicit. Native
full-precision Fcalc agrees around 1e-15; unchanged controls are zero. Scalar-CIF
formatting failure retained, separate retry passes. Removing a declaration leaves
Fcalc unchanged but bound Cedar comparison catches it. Diagnostic only: originals
untouched, no product writer or refinement. Formalize source/alias/polymer and
complete annotation lineage through existing owners before widening P03 support.


[W248 makes exported-model inspection reusable](topostitch-preview.md#inspect-a-serialized-recut-against-its-saved-source-w248):
237 source/237 relocated installed checks; all 12 W247 cases replay identically,
including the two expected default-mmCIF tensor-precision failures. Complete
identity permutations, thermal state, parsed crystal and numerical precision are
bound to both saved receipt and export. External links remain separate from file
annotations. All 60 backbone links are measured: recutting makes two old seams
local and introduces six image-spanning seams elsewhere. Export must carry the
whole boundary graph. P03 remains partial; no writer, new native fit or acceptance.
Next reuse Cedar's deposition-link reader to qualify annotation/polymer mapping.
The full-suite attempt was interrupted by coordination after sandbox process-control
failures; no full pass is claimed. Scientific files remain local.

Queued with Cedar: review OP1/OP2 orientation in the named local duplex before/after
filling or bending. A112 in 5LNA motivates the question, but its source provenance
is still under investigation. Preserve alternatives/nicks; chemistry and correction
stay with Rowan. A pure recut must preserve relative orientation.

[W247 qualifies serialization precision](topostitch-periodic.md#w247--qualify-serialization-precision-before-a-recut-writer):
12 Gemmi/12 independent Phenix readbacks retain all ordered atoms and thermal
inventory. Default mmCIF rounds rotated U beyond the planned bound; the separate
full-precision CIF control retains represented XYZ/U exactly. Native U rereads
within 3.56e-15 Å²; native source scattering is not exactly Gemmi float32 state.
Both links remain external graph intent, with zero coordinate annotations.
Retain the first precision failure and native ordering-harness failure. Next is
a small read-only export observer; polymer/connection metadata, whole-ASU writer,
coupled fits and acceptance remain open. No new native refinement or product code.

[W246 observes two declared R3 routes together](topostitch-periodic.md#w246--observe-both-declared-r3-routes-in-one-saved-recut):
82 atoms/four canonical sites change representatives; all 1271/1275 atoms remain.
Both connections retain their image-aware lengths and declared chemistry. All
1484/2375 supplied HKLs give relative complex-Fcalc differences of about 1.5e-9;
unchanged controls are exactly zero. No physical bend, model export or native fit.
The compact checkout is at GitHub sibling anchor
`ScienceCheckouts/Linden/2026-11-23_two-route-recut/index.html`; saved data, hashes
and local links pass, but browser file-policy restrictions prevented interactive
revalidation. P03 remains partial; simultaneous representation does not qualify
simultaneous restraint/refinement. Keep W241/W242 and Cedar restart separate.

[W245 binds scattering to the saved recut](topostitch-preview.md#observe-scattering-for-a-pinned-saved-recut-w245):
**208 source/208 isolated installed tests**, six new boundary regressions. The
read-only API requires the exact preview receipt, derives explicit/forest image
choices and declared continuations, and reuses existing independent scattering
without manual reconstruction. Drift and mismatched calculations refuse; original
sources/build can be absent. All 222 relocated archive files hash-match, and the
installed package imports at its new location. No native run or model emission.
P03 remains partial: sampled neutral-atom Fcalc and float32 ANISOU transport do
not establish serialized or complete crystal/scattering acceptance.

[W244 audits four coordinated live returns](topostitch-periodic.md#w244--audit-coordinated-live-anisotropic-phosphate-returns).
Rowan completed three-cycle/six-atom Phenix fits on four initially healthy R3
cuts: bonds 1.605–1.613 Å, all eight local terms within 1.82 σ. Independent
export rereading preserves all Cartesian tensors within 8.89e-15 Å²; original
ANISOU/B/Q and measured/Free membership stay. Linden verified 84 frozen-input
hashes and source/candidate/runtime/state bindings without duplicate runs.
This closes W243's fresh local return/export check; general damaged-seam repair,
whole-ASU scattering, fixed-objective comparison and scientific acceptance remain
open. Rowan's fixed-unit bond-only/complete controls now give O3′–P–O5′
95.19°/102.46° against a 104° target; the released-link control opens to 3.261 Å.
The one-junction-at-a-time two-crystal test is qualified; simultaneous two-junction
refinement remains separate. This does not repeat or close W241's different
starting-geometry/weight-policy question.

[The scheduled phosphate follow-up](topostitch.md#coordinated-phosphate-recut-follow-up)
places processed-mmCIF link verification at P01/S03, chosen-image recuts at
P01/P02, unrefined scattering/chemistry invariance at P03, simultaneous-cut
qualification at P04/S05 and checkpoint restart at P05/S07. Reuse existing
panels and include real-nick/undecidable-partner negatives. Planning only;
W241/W242's distinct receiving comparison remains open. Cedar's processed
3LNA V51 comparison now confirms preserved geometry/thermal state but omission
of the entire submitted connection table: annotation-retention check complete,
**NOT RETAINED**. Curator action and independent 5LNA return remain open; this
updates P01/S03 observation only and does not invalidate native/local evidence.

[W243 fixes anisotropic return round-off](topostitch-preview.md#preserve-cartesian-adps-through-native-return-w243):
**293 source/293 isolated installed tests**, both real 1271/1275-atom preflight
failures reproduced and replayed cold, twelve real tensor-change refusals. All
six Cartesian ADP components compare at absolute 1e-12 Å² in the exact native
cell/group/frame; modes/Uiso and isotropic behavior stay strict. Source ANISOU
and ATOM B/Q export bytes remain exact. Installed/source/read-only cctbx replay
agree; no new fits or manuscript edits. Rowan has the frozen package at NASolve
anchor `branch-artifacts/willow/w243-cartesian-return/installed` for the separate
live qualification now audited in W244. New state receipts carry frame and ADP
comparison evidence; use fresh jobs, preserve old failures. Whole-ASU scattering
gates stay open.

[W242 observes saved native XYZ weights](topostitch-preview.md#observe-printed-native-xyz-weights-w242)
without changing refinement: **278 source/278 isolated installed tests**, exact
readback of all ten W241 cycle summaries, including a standard-library-only
installed replay. SHA/cycle/summary/completion checks preserve raw printed strings,
line numbers and rounding limits; equal printed weights do not establish fixed
policy or objective equality. No native execution or full-suite repeat.
Cedar already owns a fixed-unit counted-cycle protocol; its one-cycle scope is
not transferable to Willow's five-cycle/bulk-scaling experiment. A matched
fixed-objective control stays queued for explicit scope qualification.

The installed [native-phosphate entry](topostitch-preview.md#refine-one-registered-phosphate-connection-w240)
now runs an explicitly registered six-atom continuation through Cedar C545:
**261 source/261 installed checks**, complete Phenix 2.2.1-6174 preflight and
one-cycle execution, exact source/installed candidate parity. Original 862 atoms,
856 held coordinates/BQ, 1909 indices and 124 Free assignments survive; common
native F/SIG scaling is recorded. Standalone Willow requires explicit compatible
Cedar modules; no campaign activation or branch merge is implied.

**Seeded-receiving science:** [W241's two five-cycle receiving runs](topostitch-periodic.md#w241--compare-geometry-seeded-and-direct-native-receiving)
show that the W235 geometry seed survives: O3′–P 1.613075 Å, phosphate oxygen
angles 107.179°/109.761°, local bond/angle residuals at most 0.398/1.614 σ.
The original-start control remains at 1.819145 Å and 74.607°/149.406°, with a
2.003 Å P–OP2 bond. All atoms/fixed context/BQ and original observations/Free stay.
Seeded torsions still reach 2.955 σ; Rwork/Rfree are 0.311730/0.368844 versus
0.314296/0.363045 for the original-start control. Neither is scientifically accepted.

**Interpretation limit:** native first-cycle effective diffraction weights are
309.164 versus 0.585627 despite identical requested settings. Phenix estimates
weights from gradients and adapts the scale in this resolution range, even with
weight-optimization search disabled. Seeded movement is only 0.00658 Å. We have
same-recipe geometry survival, not a fixed-objective initialization/basin test.
Next qualify explicit weight policy/evidence, reusing existing native/Cedar owners;
no Free-R-driven sweep. Keep residual torsions and density review explicit.

W240 software and W241 science evidence are local at NASolve anchors
`branch-artifacts/willow/w240-native-phosphate/` and
`branch-artifacts/willow/w241-seeded-receiving/`. Open the compact local checkout:
`ScienceCheckouts/Linden/2026-11-23_seeded-receiving/index.html` under the GitHub
sibling anchor. It includes a Python-openable ChimeraX comparison, the existing
fixed-source-map inspector and a rendered bond/angle figure. No model copies or
new FFT; display meshes and source hashes verified, ChimeraX 1.12 headless initial
view passed. Interactive browser/GUI behavior was not retested.

W239's staggered-duplex integration coverage still passes through the current
focused set. Correct-duplex inference, native precision-preserving ASU construction
and end-to-end Pine replay remain open P03/P04 gates. Rowan owns the local manuscript
repair/deposition packaging. A repeat boundary is not a chemical nick; do not carry
5W6W connection intent to a different construct. Keep an explicitly reviewed
unrestrained-edge fallback when intended phosphate oxygen geometry cannot recover,
without deleting atoms or silently adopting a different topology.

The existing native input binder now accepts an explicitly selected dictionary-only
parent policy from Cedar C526. Default literal inputs still require compiled
restraints. W214 binds a real X11_22 PostMR checkpoint and original observations;
W215 binds that exact model, original native observation and four reader controls
without inventing pair restraints. S04/S05/S06 remain PARTIAL.

**Geometry-seed science (W235):** [W235](topostitch-periodic.md#w235--close-the-local-symmetry-connection-with-all-rings-held)
uses the complete Cedar image forces to close 2.824 → 1.613 Å with only six
connecting atoms moving, all 856 others/BQ held. Boundary bonds recover to
1.512/1.440 Å; local/seam torsions remain up to 2.25/2.94 σ. Three full derivative
audits and 34 cold checks pass; 50-iteration cap, no diffraction fit or acceptance.
[W237 fixed-source density](topostitch-periodic.md#w237--inspect-the-local-proposal-in-the-fixed-original-map)
shows more positive residual samples at proposed P/OP2, with weak ordinary-map
support remaining; no independent validation or density optimization claim.
The map checkout is `ScienceCheckouts/Linden/2026-11-23_fixed-source-density/index.html`.
The three-state ChimeraX checkout is at the GitHub sibling anchor
`ScienceCheckouts/Linden/2026-11-23_symmetry-connection/index.html`.

**Larger-motion science:** A constrained geometry warm-start now lets the original
five-cycle protocol recover the 10 Å synthetic perturbation without the direct
attempt's sugar inversion. W223 reaches its 20-iteration cap (not convergence);
W224 retains 126/126 sugar signs, gives 1.612–1.621 Å flank links and
Rwork/Rfree 0.007123/0.007274. Three moving-region bond/angle outliers remain,
including one newly worsened angle. All original atoms, chemistry and data stay.
The endpoint returns near source; no distinct 1 nm placement or experimental
repair is claimed. W225 shows that the requested centroid needs at least
29.011 Å between fixed anchors versus the 21.057 Å source pair-center path.
[Exact staged result, residuals and feasibility limits](topostitch-periodic.md#w222w225--corrected-collective-warm-start-and-matched-receiving-refinement).

**Receiving boundary:** W213's private motion fixture has no campaign ancestry.
W214 now supplies a different, genuine current PostMR parent (2603 atoms, 128
canonical residues), but its frozen recipe declares no pairing or movable region.
The saved 55 NARestraints guesses are retrospective evidence, not independent
intent. W215 closes controls-only source binding; neither step creates motion or
ordinary dispatch. [Evidence and limits](topostitch-periodic.md#w214w215--real-checkpoint-and-dictionary-only-parent-binding).

Start with the [machine roadmap](topostitch-roadmap.json) and
[human roadmap](topostitch-roadmap.md). Detailed failed attempts, exact commands
and past interpretations remain in [periodic/native evidence](topostitch-periodic.md)
and [preview/API documentation](topostitch-preview.md), not a second action queue.
The longer pre-consolidation handoff is preserved at Git `86e7489c2314f738bd7fe14f611bddcde7642199`.

W216 now supplies the queued [intrinsic local shoulder proposal](topostitch-preview.md#propose-an-intrinsic-local-backbone-orientation-w216):
247 source/247 relocated installed tests and 48-state real replay. It moves only
O5′/C5′ around fixed P/C4′, retaining local distances and relative C4′ handedness.
Source-PDB precision limits historical parity to 0.001830 Å. Cross-Python
regeneration changes last bits; frozen points replay exact endpoint audits.
No motion permission, scientific acceptance or ordinary workflow follows.

W218 adds [explicit displacement summaries](topostitch-preview.md#measure-explicit-region-displacement-w218)
to the existing mask: 310 source/310 relocated installed tests and identical
saved-endpoint measurements in Python 3.12/Phenix 3.11. Centroid/RMS/max remain
separate; no centerline, correspondence or frame is inferred.

W227 adds [an explicit measurement subset](topostitch-preview.md#keep-the-measured-core-fixed-when-a-window-expands-w227)
inside the unchanged complete-motion validation: 392 source/392 installed tests,
21 saved-endpoint checks in each of source, installed 3.12 and Phenix 3.11.
This prevents changing the scientific target by including newly editable flanks:
the saved core's 10 Å becomes 7.143 Å if the unchanged flanks are averaged in.
No window expansion or new recovery was executed; default reports and motion
arithmetic remain unchanged.

W228 independently qualifies the Willow-facing boundary of Cedar C539's
[registered phosphate reader](topostitch-periodic.md#w228--review-the-shared-registered-phosphate-reader):
20 canonical/16 exact-checkpoint cold checks, no new native call. It reuses the
shared graph, resolves actual coordinate labels and the reciprocal image, and
keeps chemical intent distinct from the original checkpoint's nonbonded-only
record. This source-frame observation is not a recut, force grant or branch merge.

W230 adds opt-in [internal stacking descriptors](topostitch-preview.md#measure-internal-stacking-placement-w230)
from existing canonical frames: 116 source/116 relocated installed tests and
96 cold checks per saved-model readback with exact source/installed parity.
The initial large translation preserves plane angles but raises maximum lateral
ring-centroid offset from 3.50 to 10.53 Å; staged recovery returns near 3.48 Å.
This measures spacing and lateral placement separately from within-pair geometry
and twist. It does not establish overlap, an ideal structure or seam closure.

W233 carries those [stacking measurements through named-state comparison](topostitch-preview.md#compare-internal-stacking-between-named-states-w233):
125 source/125 relocated installed tests, 254 cold checks per readback and exact
parity. Explicit directed correspondence and independent strand/metric coverage
stay intact. Actual C543 PDU rings remain unsupported while their P spans are
retained. No new force/native run or full-suite repeat; W230's complete suite
remains tied to its recorded earlier checkpoint.

W238 tightens the existing atomic trial's completion checks to match the
collective driver: returned errors, inconsistent counts and unaccepted final
coordinates remain failures. Five fail-before cases and an unchanged-start
control; **398 focused source/398 relocated installed tests**. Seven cold checks
show the saved W235 endpoint already satisfies the new rules; no scientific rerun.
The complete software invocation at W238 source hashes records **2491 passed,
3 skipped, 234 passing subtests and five sandbox process-control failures**.
Those exact five pass a permitted focused replay; this is not one clean full-suite
invocation. Commands, hashes and logs are retained under the NASolve anchor
`branch-artifacts/willow/w238-accepted-endpoint/`. No remaining observed test
failure; skipped cases remain unqualified. [Completion contract](topostitch-preview.md#admit-only-accepted-atomic-trial-endpoints-w238).

## Current development edge

| Component | Proven scope | Still open |
| --- | --- | --- |
| W243/W244 Cartesian ADP return | 293 source/293 installed; four coordinated real fits and reopened local exports preserve tensors, source bytes and observations | General damaged-seam repair, whole-ASU scattering and scientific acceptance |
| W242 weight observer | Source-pinned ordered native summaries, rounding/no-authority limits; 278 source/278 installed, exact saved-log parity | Live/fixed-policy qualification; no parameter changes or extra fits |
| W241 seeded receiving | Two five-cycle native fits; seed keeps healthy local bonds/oxygen angles, exact fixed context and data | Strong adaptive-weight confound, residual torsions, density/statistical acceptance |
| W240 native product entry | Installed preflight/one-cycle execution, exact six-atom return and data/thermal preservation; 261 source/261 installed checks | Original-start oxygen angles; explicit weight evidence, general repair and ordinary campaign integration |
| W235 local image connection | Six-atom capped native optimization, 856 held, three derivative audits/34 cold checks; seam 1.613 Å and healthy sugar-boundary lengths | Residual torsions, effective-weight qualification, maps/packing and general repair |
| W214/W215 real parent + typed binding | Exact real checkpoint/data; 225 source/225 relocated installed, 19 real-source checks, Phenix Python 3.11 parity | Independent intended motion, Cedar ordinary request/dispatch and chemical admission |
| W208 maintained parent builder |217 source/217 relocated installed;54 actual-native cold checks, exact W207 prepared state and disposable post-parent failure | Cedar-owned versioned ordinary request/dispatch; C516 early entry qualified |
| W211/W212 intrinsic local recovery | Four matched arms, 38/40 checks per pair and 28 cross-arm; both seeds survive, original chemistry/data retained | General/experimental recovery, residual stereochemistry and maintained proposal consumer |
| W213 source/motion trace | Exact same-parent preview and typed source replay; 18 cold checks | Genuine checkpoint ancestry and Cedar ordinary receiving route |
| W207 larger fixed-flank recovery |4.96 Å maximum displacement, one five-cycle fit,39/41 cold checks; retained source chemistry, content and fixed context | Local geometry investigated in W209–W212; experimental/general recovery |
| W206 original native bytes | Opt-in detached original source observation; 191 source/191 installed and 16 real-source checks × three environments | Explicit native use and ordinary receiving route; no lifetime grant |
| W205 source chemistry + transfer | 42 source site definitions/eight families/3451 retained terms; 72 cold checks; exact post-transfer state/diffraction | Full formal-charge readback and maintained ordinary execution/lifetime route |
| W204 native service composition | C509 + W203/W200; 99 cold checks, actual dry-run/failure; exact W202 prepared state and diffraction | Original-source chemical admission and ordinary lifetime/execution route |
| W203 typed source binding | Immutable parent/report and ordered separate PHIL roles; 175 source/175 installed; real-source 3.12/3.11 parity | Concrete Cedar service and full chemical/ordinary admission |
| W202 shared live collector | Installed Cedar C507; four authenticated reader controls; exact live prepared state and failure cleanup | Maintained source-qualified builder, full chemical admission and ordinary dispatcher |
| W200 native preparation context | One-shot stage order, stable manager, exact W198 mapping, fail-closed result; installed real success/failure | Versioned ordinary execution integration and retained-file lifetime composition |
| W198/W199 native atom order | Candidate/parser and parent/prepared orders separately bound; real OP3 reorder and live parity | Broader conformers, modified moving residues, tensors and registered recuts |
| W196 interior initializer | Registered whole-pair windows, explicit weights and two fixed flanks | Successful general repair; cross-Python whole-preview last-bit audit replay |
| W197 fixed-frame recovery | Three matched native synthetic controls; original data/Free and source topology retained | Residual chemical cost, experimental evidence, larger/general deformation |
| W191–W195 helix measurements | Declared paired-P spans, canonical simple twist and explicit named-state/weighted comparisons | Modified frames, crystal-image assignments, local axes/radii, historical 7SDG provenance |
| W173/W174/W186–W190 input/preparation readers | Exact checkpoint/current parent, frozen execution inputs, original reader controls and observed native support | Complete ordinary chemical/paired-target authority for a real bend |
| W138/W139 counted refinement | Qualified explicit longer protocol and actual final-writer pair readback | Broader efficacy and user-facing enforcement/Doctor activation |
| W149/W154 density inspector | Installed prepared-scene renderer and explicit map/model roles | Stage adoption, source/frame proof, campaign actions and browser/GPU scope |
| Pine editable periodic graph | Intent, previews and source/image correspondence | Faithful recut refinement, seam chemistry and persistent human review |

W200 adds `topostitch_native_preparation.NativeEndpointPreparation`, using the
unchanged W198 endpoint owner. The builder owns actual interpretation and
chemistry/diffraction evidence; the outer worker owns source qualification,
retained-input/process lifetime, native binding cleanup and failed-model disposal.
No returned boolean/None or coordinate mapping alone is chemical authority.
[Contract](topostitch-preview.md#prepare-parent-geometry-once-w200).

W215 broader validation: one complete-suite attempt yielded 1947 passed,
131 skipped, 51 environment failures and 234 passing subtests. All 51 failures
pass on a focused replay with optional Gemmi and permitted test-process cleanup.
No clean full-suite or skipped-case qualification is claimed; no suite rerun.

## Earlier implementation and bounded controls

W226 closes the maintained collective-trial contract: 378 source/378 relocated
installed tests and 26 cold installed-native checks. The exact W223 optimizer
trajectory/end coordinates reproduce; two derivative audits and baseline
restoration pass, with 77 callbacks/80 outer geometry evaluations. No new fit,
writer, rounded-endpoint admission or ordinary activation follows. The cap
remains distinct from convergence. [API, commands and limitations](topostitch-preview.md#run-a-bounded-collective-trial-w226).
The W226/W227 evening slice deferred the complete suite to the merge gate.
For W230, the coordinated complete Willow checkpoint run passes: **2481 passed,
3 skipped and 234 passing subtests** at `c4b95b20b1d045c5f06a9572c3774b3da952c6a2`.
Skipped cases remain unqualified; this software result is separate from native science.

[W229's route preflight](topostitch-periodic.md#w229--the-current-interior-window-cannot-simply-grow)
finds no larger declared interval for the same 205 atoms and both fixed flanks:
13 cold checks/three refused anchor releases, no new coordinates or native run.
The source B chain has seven sites and the discovery boundaries remain unknown.
Rowan confirms that the reviewed B7–B1 connection does not independently grant
movement of A8–A9 or A15–A16. Keep that junction choice explicit; representation
boundaries must not be relabelled as chemical sticky ends to obtain a window.
A fresh terminal/coupled/periodic declaration is the next prerequisite; neither
a bigger pair cap nor W227's reporting subset creates movement permission.
[W231's independently checked context](topostitch-periodic.md#w231--distinguish-the-central-crossover-from-a-stacked-duplex-step)
finds the central seam bases nearly perpendicular (81.976°) despite the 2.795 Å
O3′–P gap. Covalent continuation must not imply a stacking-plane restraint.
[W232 now binds a six-atom connecting-backbone scope](topostitch-periodic.md#w232--bind-a-six-atom-connecting-backbone-scope)
with all 856 other atoms held: 23 cold checks, no displaced candidate or native
run. All captured base-plane terms are fixed. W235 subsequently qualifies the
constrained original-ancestor trial below; do not repeat this preparation or
re-perturb the already closed child. Whole-pair junction mobility stays separate.

[W234's donor graft](topostitch-periodic.md#w234--a-closed-seam-can-still-strain-the-fixed-sugar-boundaries)
closes that seam but strains the two fixed-sugar bonds (−9.60/+16.45 native
sigmas), despite retained chirality signs and unchanged stacking. Twenty-two
cold checks, one diagnostic PDB, no fit or acceptance. This rules out simple
coordinate transplantation; it does not rule out a constrained six-atom solution.
[W235 now performs that constrained trial](topostitch-periodic.md#w235--close-the-local-symmetry-connection-with-all-rings-held)
with the full seam forces and retains healthy boundary bonds. Do not repeat it:
the next question is matched diffraction receiving, residual torsions and packing,
using Cedar's qualified restart lifecycle and unchanged original data/Free.

**Internal helix focus (Simon, 2026-11-22):** retain the rough but recoverable
molecular placement as a useful intermediate, then explicitly assess stacking
recovery within the duplex. Track neighbouring base-plane orientation, spacing,
lateral offset/overlap and twist before deformation, after placement and after
restrained recovery, including transitions into fixed flanks. Distinguish
within-pair coplanarity from stacking between successive pairs. Allow genuine
curvature and nonuniform twist; do not force every plane parallel or impose an
uncalibrated universal cutoff. A connected backbone, retained sugar signs or
better R factors alone do not qualify internal stacking. Reuse the existing
pair/frame measurements and Cedar/NARestraints owners; this clarifies the current
placement/recovery gate rather than starting another subsystem or run tonight.

[W236 preflights](topostitch-periodic.md#w236--bind-the-saved-candidate-to-matched-receiving-preflights)
and W237 fixed-map inspection are retained historical preparation. W241 now
completes two receiving arms through W240, with a documented policy difference:
outlier rejection is False in both arms to preserve exact observation membership.
New preflights qualify that change. The old W239 local controller remains unrun;
its reserved folder name is not a completed milestone. Do not launch it now to
repeat the already answered same-protocol question.

The existing W239 written-geometry arithmetic was reused for 116 native-target
values and 12 source-relative handedness checks. All 38 source adjacent native
plane terms (including four PDU-adjacent terms) remain fixed; canonical-only frame
support is not the native force inventory. W241 preserves those planes by holding
all rings, not by proving that broad deformed helices have recovered stacking.
No native job remains active. A future matched fixed-weight control needs an
explicit common policy and predeclared question; the ledger itself grants no
new native run or weight sweep.

The next experiment must answer a new question, not repeat W224:

1. **Feasible window:** declare source, intended endpoint/image, ordered pairs,
   fixed flanks, protected junctions and a stable measurement core distinct
   from the editable window. Apply W225's necessary center-path
   bound before fitting; allow only predeclared window expansion up to those
   hard stops. This bound cannot certify DNA curvature, stacking or torsion.
2. **Independent placement:** qualify the unchanged reference and freeze a
   target or map-supported region independently of the initializer. Test a bend
   or straightening direction not generated and recovered through the same
   six-parameter family. Declare the comparison, call budget and stop rules
   before launch; use geometry warm-start plus matched restrained recovery.
3. **Scientific readback:** compare final coordinates, individual stacking and
   covalent residuals, sugars, source content, contacts and original FreeR/data.
   Inspect supported/unsupported density before interpreting R differences.
   Report a failure or near-reference return honestly; low synthetic R is not
   evidence of a distinct experimental structure.

The 5 Å centerline target remains separate and unrun until the local axis is
defined. Rowan owns the ordinary receiving boundary and concrete 5W6W seam
intent (`9d5030fbc06f436f428ec2cb88308e73c72b8c74`,
`docs/recipes/5w6w-central-continuation.json` on Cedar): B7 O3′ to B1 P through
`-y,x-y,z`, reciprocal `-x+y,-x,z`. It is a closed periodic strand, so an identity
ASU representative can retain the cycle; do not force every connection into a
single image-spanning tree. Preserve B1 P/OP1/OP2 and separate D1 terminal intent.
The W196/W219 interior fixture fixes A9/B7 and A15/B1 as its two flanks:
its mask cannot close the B7–image(B1) gap. C539 supplies connectivity intent,
not permission to release those anchors. Declare a separate terminal/coupled
window and its partner/junction context before a seam-placement experiment.
That exact declared source must be verified before any new run; no missing-intent
search or invented X11_22 motion is permitted. This note does not qualify a new
native seam restraint or all three junction closures.

**Ordinary integration remains Cedar-owned:** the versioned request must carry the
bound geometry-parent/source and admitted candidate motion. Rowan's **C516**
(`7ed50ffab8ecfcd232a50abfda41c45e9cf545ce`) now owns early validation/finalization/
pending-process ordering and reproduces W208's success and failure natively.
The linked owner receipt binds our exact prior records; do not repeat that panel.
[Receiving handoff](topostitch-preview.md#cedar-native-entry-handoff-c516).

The ordinary receiver still needs W206 bound source, admitted current-parent/
candidate motion, a pending native model/process options, and qualified native
readers/writer. Bind builder, W200 context, input class and W198 mapping from the
same qualified Willow module namespace. Require both context.result() and
builder.result()/evidence(). Source qualification, input/process lifetime and
failed-manager disposal remain with existing outer owners; v3/v9 request and
helper bytes retain their meanings. No extra optimizer or generic quota owner.

W207 remains immutable. W209–W212 close a separate bounded local-recovery
comparison; no failed or completed run is relabelled. Investigator-requested stress
benchmarks are separately **10 Å segment-centroid displacement** and **5 Å from
a declared helix centerline**, not maximum atom displacement or P–P span. W207
actually shifts the unweighted 205-atom centroid 0.253 Å (largest pair centroid
0.885 Å); no local helix centerline is measured. Define
and qualify those measurements before claiming either target. W219 has now
run and rejected direct recovery; W223/W224 demonstrate staged synthetic
recovery. The centerline test remains unrun. W206 opt-in bytes must be non-None
and source MATCH
must precede movement; ordinary immutable round ownership remains separate from
Alder's frozen-metal budgets and Cedar's counted prepared/native scope.


The shared collector boundary is agreed and tested; the ordinary execution
extension remains proposed. W201's five cold controls show that ordinary v3 has no typed
geometry-only parent role: old capture/default helpers remain readable/unchanged,
while an extra field, proposed policy and untyped sidecar are refused. The
[unfinalized contract](topostitch.md#versioned-parent-preparation-execution-contract-w201)
is named `topostitch-bound-parent-preparation-v1`; its proposed v10 execution
policy and `parent_preparation` field are not implemented or accepted.

Bind existing W173/W174 joins, W200 and current Cedar chemistry/reader intent;
keep the candidate as the ordinary diffraction-model argument. The maintained
builder now exists; its native readers and early ordinary placement still need
the agreed shared source qualification before dispatch. Counted
`original_model` is original pair provenance, not an automatic immediate-parent
geometry reference. Distinguish original observations from a separately computed
parent F-model, and require separate evidence if the latter is requested. Preserve
all old helper bytes, policies and defaults. No new private refinement or request
reader is warranted.

Keep input lifetime separate from model preparation. Hazel reports qualified
Alder `7d84c84d6b16b352f4d2717ce3e8ea8c01718f98`: whole audited-session
admission reserves before owned preflight and stays held through postflight/review;
settlement binds the scientific reader and exact retained-parent grant. Cross-session
request substitution refuses. Owner validation: 146 focused/67 relocated installed;
no new native calls. This is receiving-owner evidence, not Willow combined adoption.
Inner read completion is not outer release or physical reclaim. Unknown/interrupted
sessions remain charged. Alder `3b83edce40202b0595230aa5f92ed6a3c3f102b6` adds
explicit settlement only for newly bound, verified-stopped failed sessions after
completed owned preflight (165 focused/86 installed owner checks; no native calls).
Incomplete preflight and unsealed/old failures remain charged; campaign admission
and physical retirement stay open. Neither Alder delivery is a Willow integration claim.
Reuse this owner rather than adding a second storage/process mechanism.

The real X11_22 PostMR root (2603 atoms) is available and relocates, but lacks the
independently checked pair/stack target and chemical authority of the separate
859-atom canonical diagnostic. Do not fabricate ancestry or infer topology from
stretched distances. W196 is prospective; W163 historical motion is not.

After supported integration, choose an independently authorized target or a
matched generalization control before raising deformation amplitude. Existing
W148/W152/W163/W164/W168/W197 fits and W170 map sampling need not be repeated.
Cedar owns chemical repair; Alder owns cluster scope/storage. Coupled helix
opening/closing remains planned, including sugar/backbone movement; P–P span is
not radius to an axis. [Cluster contract](topostitch.md) and
[shared helix plan](helical-geometry-plan.json) retain those constraints.

User-requested regional helicity generation (9 versus 11 bp/turn) is now a
[late-stage geometric model-building plan](topostitch-preview.md#regional-helicity-model-building-planned),
with explicit step convention, endpoint phase, transition and backbone-repair
gates in the shared helix plan. It adds no implementation and does not displace the current service/chemistry integration.

Density stays in the pipeline: use original fixed data/Free, a recovery interval,
no-op control and both geometry and map review. Early post-bend R deterioration
is not a rejection by itself. After full recovery, worsening Rfree merits map
inspection even below the user's ~0.3 operational gate; above it, reconsider
connectivity/sequence/junction/rotation and other structural hypotheses. These
are scientific investigation rules, not an implemented classifier or permission
for repeated Rfree-guided tuning. No noisy phosphate detector is qualified.

## Validation and scientific interpretation

- W211/W212: four completed Phenix 2.2.1-6174 preflights and four five-cycle
  refinements; 38/40 checks per pair, 28 cross-arm checks. W213: 18 cold source/
  motion/identity checks, zero native calls. No source runtime changes, no new
  install claim and no full-suite repeat. Original scientific artifacts stay local.
  Eight roadmap tests and the synchronized 16-job roadmap audit pass; ChimeraX
  1.12 opens all three checkout models and five view actions in headless validation.
  The graph was visually inspected; no interactive GUI-render claim follows.

- W209/W210: 38/26 cold checks; 31/50 native geometry evaluations, 55 direct
  work-only scattering calls; zero refinement. Exact original source bindings,
  coordinate/data preservation and stopped process records; earlier failed
  adapters/closure retained. W209 full-region derivative disagreement is not
  promoted to a qualified force. No runtime/schema changes or full-suite repeat.

- W208: 217 focused source/217 relocated installed;54 native cold checks on
  one completed Phenix 2.2.1-6174 dry-run and one intentional post-parent refusal.
  Initial last-bit cell-representation refusal is preserved; raw values prove
  at most 2.85e-14 difference, bounded below 1e-10 in the worker reader. All native
  processes stopped; no refinement or full-suite repeat.
- W207: Phenix 2.2.1-6174 actual one preflight/one five-cycle fit;39/41 cold
  checks. Local helical/covalent readback and ChimeraX 1.12 headless three-model/
  five-control check pass; figure visually inspected. No full suite or new runtime code.
- W206: 191 focused source/191 freshly relocated installed; 16 actual-source
  cold checks each in source/installed Python 3.12 and Phenix Python 3.11, identical
  output. Original temporary input/build/install paths removed. No native call.
- W205: 72 cold checks; one Phenix 2.2.1-6174 complete dry-run and one
  source-byte rejection before interpretation/transfer. Original 42 definitions
  match, full prior final state/diffraction retained; profile/server/outer hooks
  restore and both children stop. Zero refinements; formal-charge limits explicit.
- W204: 99 cold checks; one complete Phenix 2.2.1-6174 dry-run and one
  deliberate pre-transfer failure; exact W202 geometry/model/diffraction parity.
  Both children stopped, five outer bindings and Cedar server binding restored.
  Initial import-only failure preserved. No refinements or complete chemistry claim.
- W203: 175 focused source/175 relocated installed tests; 14 real-source cold
  checks each in source/installed Python 3.12 and Phenix Python 3.11, identical
  output. Wrong parent/report and tampered captured controls refuse. Temporary
  original input/build/install paths are gone. Zero native interpretations or
  refinements; existing W200 protocol and native execution policies unchanged.
- W202: 12 cold source checks plus one actual Phenix 2.2.1-6174 dry-run and
  one injected failure, 84 cold checks. All four authenticated controls are False
  before/after interpretation and transfer. Exact prior prepared geometry and
  candidate diffraction survive; failed model is discarded. NCS=True in W200
  is preserved as historical fact, not relabelled. Installed Cedar C507 is source
  pinned; its code is not merged into Willow. No new refinement/full suite.
- W201: five actual cold owner controls, source/input immutability and temporary
  cleanup pass; zero native calls. Proposed execution contract remains unimplemented.

- W200: **160 focused source + 160 relocated installed tests**, Python 3.10 syntax;
  one actual Phenix **2.2.1-6174 dry-run** and one injected preparation failure,
  **81 cold checks**, zero refinements. Complete prepared state/diffraction and
  all three mapping digests match earlier controls. Failed manager is discarded;
  no model rollback/retry is claimed.
- Full-suite attempt was **interrupted**, not passed: 446 passed, 15 skipped,
  133 subtests and five process tests failed on sandbox denial of `/bin/ps`.
  The owned invocation was stopped at the coordinated branch-specific scope;
  a subsequent scoped process listing found no remaining matching test workers.
  Log retained locally. No unrelated process code was patched or retried.
- W199: one completed native dry-run and one injected failure, 71 cold checks;
  initial missing-`openpyxl` startup failure preserved separately.
- W198: 141 source/141 installed tests and nine saved stages/63 cold checks.
  Raw source index and default parser index are distinct. Native D1 OP3 reorder
  was real; W197's existing label-based transfer was already correct.
- W197: three actual dry-runs and three complete five-cycle refinements;
  74 preflight/80 final cold checks. Local chemical cost and fixed-context scope
  remain explicit; no ordinary or experimental acceptance.

See [W200 methods](topostitch-periodic.md#w200--maintain-one-shot-native-parent-preparation)
for exact commands, source/wheel hashes, local evidence and limitations. Older
full-suite qualifications remain their own historical scoped results. No new
merge, scientific payload publication or default activation is authorized here.

## Local science checkout

Latest read-only science: GitHub anchor
`ScienceCheckouts/Linden/2026-11-23_stacking/index.html`. One visually inspected
figure distinguishes plane angle, normal spacing and lateral displacement in
both strands, and the report explains the nearly perpendicular crossover.
It links the existing ChimeraX comparison rather than copying more models.
Source hashes and links pass; browser rendering is not claimed.


Latest physical result: GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_fixed-frame-recovery/index.html`.
One figure shows signed phosphate displacement, boundary-bond recovery and the
remaining local phosphate-angle cost. Models are linked/hash checked, not copied.
The associated ChimeraX script uses gray/silhouettes/soft/orthographic/thin rings;
it was prepared and checked, not GUI-executed for W197.

For the user's larger-displacement inspection, GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_half-nanometer-comparison/open_comparison.py`
reuses six checksummed W163/W164 models with five clickable Log comparisons.
ChimeraX 1.12 headless verifies six × 859 coordinates unchanged and all five
view actions; no rendered GUI review or new refinement. Positive recovered
B2/B3 phosphate angle remains ~76.71°; the original ~4.79 Å maximum start
motion is not the residual displacement. All 859 atoms could refine in those
older controls. Manifest and viewer evidence stay local.

W198–W206 add no geometry effect to illustrate. W207 now supplies a new
three-model comparison under `ScienceCheckouts/Linden/2026-11-21_fixed-flank-recovery/`
(`review.html`, `open_comparison.py`), including the unresolved A11/A14 close-ups. W206 binding/installation
receipts are under `NASolve:branch-artifacts/willow/w206-source-observation-binding/`. W205 source-chemistry/transfer
receipts are under `NASolve:branch-artifacts/willow/w205-source-chemistry-transfer/`. W204 local receipts are under
`NASolve:branch-artifacts/willow/w204-parent-service/`; see the
[service composition audit](topostitch-periodic.md#w204--compose-the-installed-cedar-parent-service). W203 cold/installation receipts
are under `NASolve:branch-artifacts/willow/w203-source-input-binding/`. W202 source/live receipts are
under `NASolve:branch-artifacts/willow/w202-typed-native-builder/`. Earlier receipts
remain under NASolve anchor `branch-artifacts/willow/w198-native-handoff/`,
`w199-live-preparation/` and `w200-native-context/`; checksummed references are in
the machine roadmap. Scientific runs, failed attempts and native observations
remain immutable/local. Reuse the existing inspector for the next physical result.

## Scientific limits and demonstration gates

- **Bending:** W100 uses actual-input tethers and three matched controls. All
  pass full/PDB-rounded derivative checks but stop `NOT_CONVERGED_LIMIT`;
  endpoints remain `REVIEW`. Some individual packing/torsion/plane terms worsen.
  [Exact results and inspection files](topostitch-periodic.md#w100--source-displaced-controls)
  are local evidence, not selected repaired models. W91 found no benefit from the
  small coarse polish; do not restart it without a different justified question.
- **Diffraction and density:** W34 found no meaningful held-out benefit from
  bend-plus-cleanup (Rfree .2276 versus .2274 for cleanup), with worse bond/angle
  RMSDs. W140 adds exact saved-map sampling and identifies a persistent C102
  phosphate difference feature; it does not identify its cause. S06 still needs
  healthy/noisy/displaced calibration before sustained negative-backbone-density
  detection. Noise, resolution,
  occupancy and ADPs matter. Keep straight→bent, bent→straight and changed,
  nonuniform or distal curvature as general cases; 4T28/8SJW interpretation remains
  unverified. No density-aware repair is implemented by W107.
- **B09 final gate:** geotest altered arms, including **X11_18 in P4_3** and
  X11_22, must align and survive matched refinement with healthy arms/junctions
  preserved. The local inventory passed 204 hash/size checks; remaining sequence,
  arm and partner mappings are not frozen. Preserve X11_18's P4_1-input/P4_3-model
  lineage for explicit audit. See the [gate contract](topostitch.md#final-geotest-alignment-gate-planned).
- **Blunts and asymmetry:** designed blunts can depend on one base-stack contact
  and need density-aware placement. Three labelled triangle orientations must
  start **after PostMR and the first refinement**, with fixed data/Free-R and
  separate bending/refinement. Re-running MR can erase those alternatives.
  [Blunt scope](topostitch.md#designed-blunt-contacts-and-single-base-stacking-w93-planned)
  and [rotation scope](campaign-model-roadmap.md#three-orientation-asymmetric-triangle-check-w93-planned)
  remain plans; no new dataset solve is claimed.
- **Publication:** the [shared shortlist](campaign-model-roadmap.md#nasolve-publication-demonstrations)
  records A2T7 rotations, recuts with bending, standard datasets including DOHU,
  and Hazel's metal cases, with separate readiness and scientific evidence gates.

## Pine recuts and shared ownership

Pine owns editable periodic intent; TopoStitch exposes it; Cedar owns native
chemistry/enforcement. Preserve **P/OP1/OP2** for declared continuations even when
partners are unresolved. No automatic OP3/dephosphorylation or isolated symmetry
bond while surrounding geometry/exclusions remain unqualified. See the
[shared connectivity contract](construct-registration.md#shared-periodic-connectivity-intent-pine-topostitch-and-cedar).

For pure representative recuts, prefer one computational/source frame throughout
the native process, deriving views at explicit boundaries. Bind atom/operator/tensor
correspondence and checkpoint lineage. Refined children need fresh bindings;
Coot edits and re-entered exports need checked inverse mappings. Additions,
deletions, renames or changed intent require new qualification. P03/P04 physical
identity and seam chemistry precede ASU materialization; recutting cannot close a
physical gap. Native reporting, copying, ADPs and writers retain their own gates.

## Historical Pine references

The inherited October queue is historical, not today's Willow instructions.
The [October handoff](history/development-handoff-2026-10-08-pre-consolidation.md)
and [native modified-pair ledger](native-modified-pair-live-validation.md) preserve
chemistry, run and user-review evidence. The full pre-cleanup Willow handoff is
retained in Git at `6352c8aa45b1e464fda03794bc302591f5a79ab5`.
Existing agent-readable references below remain valid historical pointers.

### Pine close-out

See the [archived Pine gates](history/development-handoff-2026-10-08-pre-consolidation.md#pine-close-out).
They do not establish current Cedar or Pine completion.

### Nine-member baseline results

See the [archived baseline](history/development-handoff-2026-10-08-pre-consolidation.md#nine-member-baseline-results).

### After Pine: blind AlphaFold geometry campaign, then Scout

See the [historical sequencing](history/development-handoff-2026-10-08-pre-consolidation.md#after-pine-blind-alphafold-geometry-campaign-then-scout)
and current [registration contract](construct-registration.md). Predictions are
candidate models, not solved truth; preserve frozen sequences, diffraction and
Free-R, and do not consult outcome structures during blind selection.

## Work discipline and doc ownership

Use [AGENTS.md](../AGENTS.md) and the [collaboration contract](collaboration.md).
Keep branch-local state out of Git. Preserve immutable runs, failures, maps,
Free-R, pinned diagnostic environments and other authors' untracked work.
Scientific archives are local forensic records, **not automatically portable or
resumable runs**. No scientific payload is included in this documentation update.

Keep this handoff concise. The roadmap owns milestone status, subsystem guides
own behavior, and the periodic/preview ledgers own exact validation commands and
historical evidence. Do not append repeated session diaries or promote a numerical
or software PASS into scientific acceptance.
