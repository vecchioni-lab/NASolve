# Metal development handoff — current state

Updated **20 November 2026**. Active feature branch: **Alder**. The
[root integration handoff](development-handoff.md) owns the current combined
source, full validation and delivery. The [A01–A09 roadmap](metal-development-roadmap.md)
owns feature completion. The earlier chronological diary is preserved as
[evidence through 18 November](history/metal-development-handoff-2026-11-18.md),
not a second queue.

## A01 current checkpoint: explicit coordination topology

The shared topology reviewer now accepts an optional, exactly declared metal
contact inventory. The metal adapter reuses the existing recipe preview and PHIL
export, binds exact source-model bytes and the complete native atom inventory,
and emits only enabled metal-containing distances. The reviewer requires one
matching request and one matching native bond with the same endpoints, origin,
target and weight. Coordination, NAR soft restraints and covalent links remain
separate. Same-residue metal–metal contacts are checked explicitly; an unknown
neighbor or competing request is not hidden by its element or origin.

Default calls retain their schema-1 result. Explicit `coordination_bonds` calls
return schema 2, policy `cif-declared-coordination-topology-v1`, with typed
`coordination_restraints`; no stored run migration or native default changes.
Angles, nonmetal distances, full force semantics, source/capture authentication,
modified/metal endpoint admission and scientific acceptance remain separate.
The shared checker still requires a nonempty explicit covalent topology and its
existing supported PDB subset. A cluster-only model without such a declaration
is not newly admitted. The adapter refuses explicit MODEL records, nonblank
segments, alternatives and insertion codes under this capture contract.

**FT_Hg saved-evidence result:** all **210** supplied requests are realized
exactly: 51 distances (49 NAR plus two Hg contacts), 83 angles, 57 parallelities
and 19 planes. The complete 859-atom native capture has 38 covalent cross-site
links, all O3′–P, and no extra inter-base covalent bond. All **1,009** bonds in
the saved initial/final metal-centred `.geo` files retain endpoints, categories,
targets and weights at printed precision. This rules out that specific unwanted
link in these saved controls, not the remaining ligand strain.

**Keep the whole-topology result at REVIEW.** This older experiment carries
independent preparation authority for four selected-site junctions only. Its
34 other observed backbone links and 49 historical supplied-PHIL contacts remain
visible, without fabricating a current NAR compiler-authority receipt. Existing
shared supplied-PHIL readers verify delivery separately. No complete retained
manager, whole-model chemical qualification or accepted f″ parent follows.
The B:1/formal-charge and open XYZ/B limitations persist. **A01 partial; A02 gated.**

Validation: **309 focused tests pass in 29.91 s** under Python 3.12.14,
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder>/src`, using
`python -B -m pytest -q -p no:cacheprovider` on
`tests/test_{metal_coordination_topology,cif_topology_gate,metal_native_terms,cif_attachment_native,cif_na_policy,cif_native_context,cif_restraint_context,metal_motion_scope}.py`.
The exact expanded command, source hashes, XML and log are in
`topology-coordination-20261120-01/focused-tests/`. The process stopped and source
files stayed exact. The new positive regression fails before implementation;
controls cover undeclared covalent neighbors, declared crosslinks, changed or
duplicate requests/proxies, symmetry, source identity and same-residue contacts.
No full suite is repeated for this bounded adapter; the prior integration record
above the metal scope in the root handoff is unchanged.

Cold readback with `python -B <Alder-artifacts>/runners/A263_coordination_readback.py`
passes **269 checks**, using the same environment. Receipts are
`topology-coordination-20261120-01/ft-hg-{readback,topology}.json` under the existing
Alder artifact anchor. Evidence is from completed **Phenix 2.2.1-6174** runs;
no new Phenix/Coot execution or f″ measurement was made. The local table checkout
is `ScienceCheckouts/Hazel/2026-11-20_coordination-topology/open_report.py`:
three files, **6,074 bytes**, linking existing models/maps rather than copying
them. Generated science, private runners and reports remain outside Git;
no parent or trial data is pruned.

Changed runtime files are `cif_topology_gate.py` and the new
`metal/coordination_topology.py`, with one focused regression module. Current
handoff, roadmap, feature contract and changelog change together. Shared-owner
review accepts the narrow opt-in boundary and preserves the legacy REVIEW.
**Next:** consume source-bound parent topology and the shared retained-manager
boundary before modified/metal motion admission. Separate donor pose and Hg
placement, then qualify open XYZ/B before branch-specific environmental B and
frozen f″/Q. Do not repeat this readback or the completed 25-point pivot grid.

### Completed-batch provenance handoff

`metal publish-fdp-inputs` now publishes a bounded explicit completed batch and a
shared parent/trial/result index, using the unchanged packing reader, archive
sync primitive and durable create-only campaign record writer. The new
`metal-fdp-review-publication` v1 receipt is independently pinned by
`record_sha256`; `inspect-recorded-fdp` can consume it or the original explicit
pins. Existing source formats/defaults stay unchanged; no migration is required.
**16 final focused tests** pass in 10.94 s. An installed two-trial synthetic
producer/readback uses 1,538 B of receipt metadata; all results survive source
removal and relocation. Indexing adds no parent replay; existing packing still
performs eight parent reads for two trials. Interrupted publication issues no
selectable completed receipt. No native fit, cleanup, whole suite or A01/A02
advance follows. Local evidence: `fdp-publication-20261120-01/{validation.json,
installed/result.json}`. See the
[storage contract](metal-campaign-storage.md#completed-batch-publication-and-selection-receipt).

**Real historical FT_Hg qualification:** the same installed wheel now publishes
three complete existing attempts (008/013/014), producing a **134,901 B archive**
and **1,810 B receipt**. The archive is byte-identical to the independently pinned
19 November archive. With original science/source reads blocked, all executable
inputs, frozen atom states, parent identities, full reflection arrays and saved
results match exactly: **48 checks in 9.50 s**. `FreeR_flag` selects 2,128 anomalous
observations, including 109 free observations; `SA_flag` is not selected. Existing
packing makes twelve source-parent replays; indexing adds zero. Originals remain
unchanged. Protected-parent storage is additional, and this proof grants no
retirement authority.

These are historical **Phenix 2.2.1-6174** poor-fit controls at Q=0.60 and B=25 Å²:
f″=29.000000/35.309143/35.309136 e, expected 8.678570 e, Rwork≈0.397 and
Rfree≈0.424. Exact recovery does not improve geometry, calibrate f″, count metals
or qualify convergence. No new native execution or full suite ran. Command:
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B
<Alder-artifacts>/runners/A301_real_publication.py`. Evidence and the compact
visually checked comparison are `real-publication-20261120-01/{review.json,
delivery-review.json,science-review.html,science-comparison.svg}` under the
existing private artifact anchor. The runner reuses the already qualified wheel;
no runtime/schema changes or migration are introduced by this follow-up.
Generated inputs, results and figures remain outside Git. A01 partial, A02 gated,
A04 partial; next qualify the scientific parent and compact child lifecycle.

### Ordinary recorded-result CLI

The maintained historical inspector now has a stdout-only normal CLI consumer,
`metal inspect-recorded-fdp`. It requires external archive/projection/trial/parent
pins and prints Q/B/f″ or exact JSON without original-run or native discovery.
**53 focused tests** passed in 32.13 s; a relocated installation recovered both
historical Hg and Ag₄ results exactly and refused changed parents/partial work.
Its 723 checks include package integrity; no native fit or full suite ran.
Local evidence: `recorded-cli-20261120-01/validation.json` and `installed/result.json`.
Only the CLI and its focused test file change runtime behavior. No persisted
schema, scientific default, migration or cleanup authority changes. A04 remains
partial; this closes the explicit ordinary command-line inspection gap, not
campaign orchestration or retirement. See the
[storage contract](metal-campaign-storage.md#normal-cli-inspection-of-one-recorded-attempt).

### Independent FT declarations and remaining symmetry input

**Investigator clarification received after this audit:** B:7 O3′ → B:1 P is
an explicitly declared symmetry continuation forming the triangle's central
strand. This supersedes the earlier absence of B:1 chemical intent below.
The investigator subsequently confirmed the C/D crossover conditional on A
having 21 residues. That condition holds in all three pinned models: A:1–A:21.
The D:7 O3′ → C:8 P correspondence remains source-derived, and native symmetry
enforcement still needs qualification. D:1 retains its terminal phosphate.
The coordinate-derived operators have not become user-specified geometry or
native qualification. In the current pinned model, `-y,x-y,z` places B:7 O3′
relative to identity B:1 P; the directed B:7 O3′ → B:1 P edge therefore uses
the **inverse** target image `-x+y,-x,z`. Retain that direction explicitly.
Local current authority: `ft-symmetry-contacts-20261120-03/user-connection-intent-v2.json`;
the earlier declaration and audit/contact records remain historical evidence, not overwritten.
Cedar leads deeper construct-topology review against its existing records.
No executable recipe, recut packet, model change or accepted parent follows.

A source-only audit of the actual `d69966…` parent preserves all nine input pins
and passes **90 checks** without a native call or model edit. The frozen 5W6W
recipe/report explicitly permits terminal OP3 only at **D:1**. The maintained
ordinary phosphate auditor refuses **B:1**; a separate site-scoped audit also
refuses **C:8**. Both retain P/OP1/OP2 but lack an ordinary verified incoming link
or an explicit FT cross-symmetry partner/operator in the audited intent. The
earlier selected-site preparation intentionally left this whole-model context
unqualified. Do not transfer the investigator's separate PDU B:1 symmetry
interpretation automatically, delete phosphate atoms, classify these sites as
free termini, or infer an angle restraint from proximity. The precise open input
is a user-editable connection with atom identities, symmetry operator/cell image
and intended chemistry for this FT construct. D:1 remains its distinct declared
terminal phosphate.

A subsequent read-only geometric comparison makes the open input concrete.
In the current model, B:1 P is **3.10034 Å** from B:7 O3′ under `-y,x-y,z`;
C:8 P is **3.02708 Å** from D:7 O3′ under `-x+y,-x,z`. Both lattice shifts are
zero in this explicit operator representation. These are contact hypotheses,
not accepted covalent links. The 3 Å query finds none in the current model;
one expanded 6 Å query retains every candidate and separates same-residue
identity contacts. No nearest contact is automatically adopted.

The pinned original MR model already has these chain starts and analogous
partner identities (2.79492/2.91895 Å in its own cell/pose); original PostMR gives
3.24056/3.08112 Å. No pinned FT representative-slicing packet is declared, so
slicing origin remains unestablished. D:1 P is absent from the selected `noPO4`
MR source and present after PostMR; its current terminal-OP3 declaration is
preserved despite a nearby symmetry O3′ contact. These observations do not
justify copying the separate PDU construct's connection intent.

The private diagnostic consumes Willow's crystal/operator/Cartesian-image
owners without fabricating duplex-end or recut declarations. Independent
compiled Gemmi periodic enumeration matches all candidates/distances. **46
consumer checks** also replay the existing explicitly declared non-FT synthetic
continuation packet and retain unresolved/chemical-boundary alternatives.
That fixture is not an experimental solved control and does not qualify FT.
Local `ft-symmetry-contacts-20261120-03/` contains the editable interpretations,
exact source/operator records, compact table figure and validation. No production
symmetry adapter, new chemistry, native calculation or checkpoint is introduced.

The generic frozen frame sequence lists A:13=T and B:3=A, whereas the independently
pinned selected MR model and original PostMR model already contain C/G there,
matching today's parent. This is a historical sequence/model declaration
distinction, not new research-model drift. The frozen compatibility report calls
complete recipient residue identity UNKNOWN. Current sites otherwise match the
selected source model plus the declared QF1/QT1 aliases and placed Hg.

Available pairing intent comprises **17 frozen frame Saenger pairs** and **two
explicit standard-site flanks** (A:11–B:5, A:13–B:3). The original **19 pair planes**
must be retained separately if C21 emits a fresh policy with `planes=False`.
The 49 supplied NAR distances, 82 angles, 57 parallelity terms and 19 planes stay
distinct from the two Hg distances and one donor-vertex angle. The PDB contains
102 LINK rows repeating 51 supplied base/metal links; none involves phosphorus
or supplies the missing symmetry connection. Neither these serialized records
nor the 38+49+2 native observations establish whole-model intended connectivity.
No prospective whole-model recipe was compiled from incomplete authority.

W173 separately requires an ordinary selected checkpoint; this private FT
endpoint has no such saved registry. A deliberately isolated synthetic consumer
control reuses Willow's existing fixture: actual W173 input binding reaches the
unchanged endpoint auditor and refuses both modified-donor and metal permission
masks (**13 checks**). Only upstream motion replay is substituted, so this is
neither full modified-preview authentication nor chemical/native qualification.
No artificial FT registry or canonical native rerun was created. Shared owners
and endpoint restrictions are unchanged.

Local receipts: `ft-declaration-audit-20261120-03/{review.json,
terminal-connections.json,synthetic-w173/review.json,editable-connection-intent.json}` under the Alder artifact
anchor. The editable review preserves the current P/OP1/OP2/O5′ coordinates,
B and Q at B:1/C:8, with unknown partner/operator/cell image/chemistry left null;
D:1's declared OP3 is shown separately. It is not an executable recipe. The
synthetic checkpoint consumer used the then-current working-tree source hashes
recorded in its receipt, including checkpoint SHA `9120e4…`; it does not qualify
the concurrently updated W174 adapter or claim an exact released revision. The
validation record pins private runners A279–A284, their entrypoints/environment,
the scientific input bindings and shared source hashes. Earlier audit-harness stops are
preserved: the preset-policy hash has a different scope from the dataset INI;
generic frame sequence equality was false; and the PDB does contain LINK rows,
though none supplies the missing phosphate connection. No source/default/schema
change, full suite, native refinement or f″ test follows. A01 remains partial;
A02 remains gated.

### Current-parent interpretation and motion-intake boundary

The next A01 check distinguishes a supplied topology declaration from an admitted
movement. A fully declared **synthetic** control passes typed topology with two
metal–ligand contacts and one same-residue metal–metal contact. A 0.02 Å
canonical-atom displacement within a 0.05 Å mask passes the existing exact-byte
audit, preserving B/Q and fixed records, but stops at the absent supported
retained-manager entry. A mask containing a metal remains refused even for a
no-op. Changed parent bytes stop before topology; an unrequested covalent
neighbor stops before endpoint auditing; changed candidate B/Q stops before
manager preparation. Contact **declarations**, not post-movement distances or
forces, remain fixed. No metal motion, complete chemical capture or manager
retention is qualified by this fixture.

The six-case diagnostic passes **17 checks** and independent replay passes
**32**, including maintained-adapter refusal of changed parent metadata, XYZ,
B and Q. Small complete synthetic inputs are retained with hashes. This is a
consumer-order rehearsal, not an installed execution hook or a second B/Q guard.
The canonical movement owner and its restrictions remain unchanged.

The real FT_Hg parent-state comparison passes **15 checks**. The original full
capture input and later unchanged-continuation endpoint have identical 859 atom
identities, but **all 859 XYZ and B values differ**; Q and ANISOU do not change.
The existing reader correctly refuses the old capture against the later parent.

| Printed PDB state | Original capture input | Later retained endpoint |
| --- | ---: | ---: |
| DF base-only mean B (Å²) | 20.00 | 100.22 |
| DT base-only mean B (Å²) | 47.91 | 161.18 |
| Hg B (Å²) | 72.95 | 141.34 |
| Hg Q (occ) | 1.00 | 1.00 |

One new **fixed-coordinate interpretation**, not a refinement, now observes the
actual later parent using the same dictionaries and ordered PHIL. Phenix
**2.2.1-6174** completes in **2.25 s** within a 120 s bound; the owned process
stops and all nine source-input fingerprints remain exact. The maintained full
capture authenticates and passes **260 cold checks**: 859 current atoms, 38
observed O3′–P links, 49 supplied NAR distances and two Hg contacts; all **210**
supplied terms and **1,009** simple-bond endpoints/origins/values are retained.
No extra nonbackbone covalent cross-site link appears.

This closes the stale-coordinate observation gap only. Fresh interpretation is
not retention of the historical final manager. Legacy whole-parent chemical/NAR
authority stays **REVIEW**; the capture observes coordinates/occupancies but not
dual hierarchy/scattering ADPs. Modified/metal movement, checkpoint/dispatch
binding, complete packing and the supported retained-manager entry remain open.
The existing B:1/formal-charge and geometry limits persist. Before any frozen
anomalous terms, verify actual endpoint XYZ/ADPs, obtain an accepted open XYZ/B
state, then derive environmental B from that branch. The arithmetic equal-base
mean would differ (33.95 versus 130.70 Å²); neither value is applied here.

Local receipts are under `motion-intake-20261120-01/`: `review.json`,
`cold-review.json`, `parent-state-review.json` and
`current-parent-capture/{execution,review}.json`. Reproducible private runners are
`A267_motion_intake_boundary.py`, `A268_review_motion_intake.py`,
`A269_parent_state_boundary.py`, `A270_capture_current_parent.py` and
`A271_review_current_parent_capture.py` under the established Alder artifact
anchor, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder>/src` and Python 3.12.14.
Native execution uses the recorded selected Phenix interpreter/environment.
No product code/schema/default changes or new pytest suite follow; the existing
309-test source pin is unchanged. Scientific data remain local, no old inputs
are copied into Git or pruned, and A01 remains partial/A02 gated. Shared movement
admission stays with its existing owner; A04 software/execution binding is the
parallel next bounded task while that interface is pending.

### Fixed-endpoint donor motion (preceding diagnostic)

A bounded private coordinate study now consumes the connected-region inventory
and existing shared `TaperedMotion` / `CoordinateMask` arithmetic. Each complete
selected nucleotide rotates around its original P–O3′ line. Both axis endpoints
are explicitly excluded from movement, leaving all four flanking bond lengths
at their source values. The 41-atom region has **37 active atoms**; surrounding
atoms stay fixed. Hg follows the mean N3 displacement, retaining its original
vector from the donor midpoint. This is a declared transport rule, not a metal
optimizer, new motion engine or general backbone-closure solver.

The prospective grid uses −5, −2.5, 0, +2.5 and +5° independently for each
residue: **25 observations**, with a **0.8 Å** atom-displacement bound. The source
is the saved unchanged-continuation FT_Hg model, not a human endpoint. Original
source chemistry, captured targets and inherited internal strain remain intact.

| Measured quantity | Result |
| --- | --- |
| Four flanking bond-length changes | Exactly zero in full precision and rounded-coordinate observations |
| Maximum atom displacement | 0.730 Å |
| Maximum flanking-angle change from the source | 2.27°; descriptive, not an acceptance threshold |
| N3 donor span | 3.379–3.938 Å; source 3.492 Å |
| N3–Hg–N3 under midpoint-following | 115.5–123.2° |
| DF C1′–N1 | 1.623 Å retained; inherited strain remains |

Internal pair distances differ by at most **3.6e−15 Å** before rounding, a
numerical identity check rather than experimental precision. All six selected
chirality signs are retained. None of the sampled spans reaches the 4.20 Å
implied by the tested idealized linear two-contact, 2.10 Å Hg recipe. Some Hg
contacts worsen. The largest-span grid point is descriptive, not selected.
This shows useful donor reorientation without stretching the four bonds; it
does not resolve coordination or establish a diffraction-supported alternative.

**Qualification:** 174 generation checks and **243 independent cold-readback
checks** pass, including changed-coordinate, changed-angle and stale-source
negative controls. Readback reconstructs saved masked displacements and compares
them with the shared `CartesianImage` route. Full/rounded coordinate hashes,
source models and shared code stay bound. The canonical endpoint guard still
refuses these modified/metal atoms; no guard is weakened or copied, and no PDB
candidate is emitted. Torsion/parallelity energy, complete symmetry packing,
fresh likelihood/maps, source chemical acceptance and ordinary admission remain
unassessed. The prior B:1/formal-charge limitations persist. **A01 partial;
A02 gated; no native scientific execution or new f″ measurement.**

Exact reproducible commands use
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder>/src <Python-3.12.14> -B`
with `<Alder-artifacts>/runners/A258_pivot_motion.py` for the fresh numbered
observation directory, and `A259_review_pivot_motion.py` for cold readback.
The immutable plan, all 25 compact displacements, summaries and hashes are in
`a01-pivot-motion-20261120-01/{plan,observations,summary,cold-review}.json` under
the Alder artifact anchor. Source pin: `9f490b6903917692b55fc63526132e37242ec499`.
No production source, schema, default, native worker or migration changes.
Existing scientific/pytest suites are not repeated for this documentation-only
delivery. The previous focused/full validation remains preserved below and in
the root handoff; generated scientific artifacts and private runners stay out
of Git. No scientific parent or trial files are pruned.

The five-file local checkout is **240,593 bytes** at
`ScienceCheckouts/Hazel/2026-11-20_pivot-motion/open_report.py`, with PNG,
editable SVG, HTML and provenance. Its two heatmaps show donor separation and
flanking-angle changes; the small table retains Hg contacts and the unchanged
base attachment. Rendering uses Phenix 2.2.1-6174's Python 3.11.15 only for
Matplotlib, with no refinement. The plot was visually inspected and the owned
render process stopped. Large models/maps are referenced, not copied. The complete
new evidence is about **0.80 MB** before delivery metadata. Source, local links,
publication hashes and document scope pass **82 checks** with
`python -B <Alder-artifacts>/runners/A262_check_pivot_delivery.py`;
`delivery-review.json` records the result and `git diff --check` passes. This
validation sentence is added after that review; product/science files stay exact.

**Next:** use this demonstrated restricted motion without repeating the same
grid. Separate donor-pose and Hg-placement choices, review all crossing geometry
and packing, and qualify source-bound modified/metal admission with protected
B/Q/tensor state and fresh child diffraction before any matched native recovery.
Preserved inherited attachment strain still needs its source/geometry owner;
it cannot be repaired by a whole-residue rigid move. A changed XYZ endpoint
needs open XYZ/B and scientific review before environmental B and frozen f″/Q.
This single-Hg study does not qualify cluster placement or count inference.

### Implemented region inventory and preceding junction check

`nasolve.metal.motion_scope.inspect_movement_scope` is the existing read-only
owner, described in the [feature contract](metal-restraint-builder.md#inspecting-the-connected-movement-region).
The hash-bound C410 native capture supplies 41 selected/818 fixed atoms, four
flanks (A:11/A:13/B:3/B:5), and 36 crossing terms: four bonds, sixteen angles,
twelve torsions and four parallelities. The full capture is required; V9's
intra-site-only capture does not substitute for crossing geometry.

Its source-bound saved-model review and 2,922 checks remain in
`movement-scope-20261120-01/ft-hg-{scope,review}.json`. Original and saved refined
junctions, plus twenty initial/final native bond/angle targets, are accounted
for without a new interpretation. The earlier five-file junction checkout
remains at `ScienceCheckouts/Hazel/2026-11-20_movement-scope/`.
Initial direct/helper tests: 86 passed; final new module: 28 passed; workflow
intent: 25 passed. The named chemistry profile retained 1,744 passes, eleven
sandbox process failures and ten subtests; the exact eleven cases passed with
process permissions and unchanged sources. Both owned test processes stopped.
Exact commands/logs/XML and the 107-check delivery review remain in the same
movement-scope anchor; the complete preceding handoff is preserved at commit
`9f490b6903917692b55fc63526132e37242ec499`. This is not a new all-green profile.

Coordination with Linden reuses the unchanged shared motion arithmetic and
explicitly fixed endpoint masks. His independent registered-preview parent
binding work does not admit modified metals. Cedar retains chemical geometry/
regional measurement ownership; the shared canonical byte guard retains its
existing limits. Cluster motion remains planned A03/A07 work.

### Retained preceding coordination result

The completed five-cycle metal-centred angular alternative replaces the
donor-vertex 0°, σ 2° term with a different, locally stronger 180°, σ 2° term.
It opens N3–Hg–N3 to 154.5°, but leaves Hg–O4 at 1.686 Å and DF C1′–N1 at
1.642 Å. Rwork/Rfree are 0.3057/0.3338 versus 0.2802/0.2902 in the unchanged
continuation. B/scaling also differ; reduced negative Hg density is not an
independent occupancy measurement. No endpoint or recipe is selected.
The complete result/263-check validation remains in
`a01-local-angle-20261120-01/science-comparison.json`, its local-angle checkout,
and this document at commit `f8a48683a6395981d377f8d6f62113bb368f3674`.
Reuse the completed angle/force comparisons rather than repeating Hg-only
shifts or unchanged weight sweeps. Cluster coordination is a separate hypothesis.

## A01 preceding checkpoint: native bridge objective

The bounded 20 November diagnostic returns to the exact selected XYZ state of
the **first five-cycle neutral parent**, before the final group-ADP/core/mask
refresh. It does not measure the later continuations' different B/scales.
Phenix **2.2.1-6174** reproduces all **105** returned-state records, makes **16**
diagnostic evaluations and stops irreversibly; no optimizer resumes, new model
is selected or f″ parent is accepted. The complete owned replay takes **555.02 s**;
the diagnostic evaluations take **4.14 s**.

Moving Hg toward the N3 donor line has native directional slopes of **+0.028262**
for the phased-likelihood term, **−0.010150** for the explicit metal recipe and
**−0.011380** for the remaining geometry (nonbonded), giving **+0.006732 per Å**
overall. Both geometry subsets favour straightening locally; the retained
likelihood/phase/ADP/Q context opposes it. This distinguishes the tested conflict
from a missing recipe or an opposing nonbonded force. It is not independent
experimental evidence or a general explanation of every endpoint.

All six Hg-direction finite-difference checks pass. Hg movements of
**0.05/0.10/0.25 Å** raise the combined target by
**0.001273/0.004374/0.023916** while shortening the contacts; the 11,222-term
inventory remains unchanged. Hg-only repositioning does not solve the donor-span
problem. The fixed-sugar outward base-rotation tangent passes five of six checks;
its combined check at 0.001 rad misses the predeclared tolerance
(**1.20e−5** error versus **6.85e−6** bound). The 0.0001-rad check passes. Its
finite profile is withheld without changing tolerances or rerunning it. This is
a numerical qualification limit, not a chemical angular cutoff or evidence of
a native derivative defect. Native family sums and restored objectives close.

Validation: **34** kinematic checks and **287** independent cold readback checks;
original inputs remain exact and both owned phases are stopped. Exact native
commands/processes are in `a01-bridge-forces-20261120-01/native/execution.json`
under the Alder artifact anchor. Preparation/adaptation failures are retained;
one text-adapter syntax failure occurred before any native call. Cold command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder>/src <Python-3.12.14> -B <Alder-artifacts>/runners/A231_review_bridge.py`.
Documentation validation with `python3 <Alder-artifacts>/runners/A237_check_bridge_docs.py`
passes **40** scope/reference/result/report checks; `git diff --check` passes.
Changed files are this handoff, the root integration handoff, metal roadmap and
changelog. No production runtime/schema/default changed and no full suite was repeated.
The last full shared-runtime qualification remains in the root handoff.

The current local checkout is
`ScienceCheckouts/Hazel/2026-11-20_bridge-objective-v2/open_report.py`, with HTML,
editable SVG and PNG. It links the **260-check** donor-span review at
`ScienceCheckouts/Hazel/2026-11-20_donor-span/open_report.py` and the earlier
matched maps. Reports link exact models/evidence without copying large artifacts;
all generated science, reports and private scripts stay excluded from Git.
A01 remains partial and A02 gated. The explicitly declared local coordination
alternative proposed at this checkpoint is now complete above. Neither result
justifies another Hg-only shift, tiny-input restart, global weight sweep or repeat
of completed controls.

The [cluster placement contract](metal-restraint-builder.md#cluster-placement-and-coupled-dna-accommodation-20-november-intent)
remains planned A03/A07 work, with default nucleobase participation. No cluster
movement or universal linearity rule follows from this single-Hg diagnostic.
Cedar Q15/Q16 owns the shared regional measurement/export plan (Cedar
`84257082`); Willow W167 (`da8794d7`) owns the planned displacement/frame boundary.
Those follow-ons are not silently adopted into this build. Donor span, sugar
anchors, phosphate spans and axis radii remain distinct measurements.

## Current scientific and engineering boundary

**Day session, 20 November:** the matched ordinary continuations are complete
and stopped. Five additional XYZ/real-space XYZ/group-B cycles improve final
Rwork/Rfree to **0.2802/0.2902** (unchanged restart) and **0.2820/0.2910**
(3°/0.05 Å coupled input). DF attachment lengths are essentially identical,
**1.622942/1.622245 Å**; the initial movement has no established advantage.
Final fitted B values rise substantially, with an explicit final scale update.
The known bent Hg coordination and negative difference density remain review
issues. No accepted endpoint or new f″ result follows. See
[matched continuation](#a01-matched-ordinary-continuation) below. That continuation checkout is
`ScienceCheckouts/Hazel/2026-11-20_matched-continuation/review.html`;
its adjacent `open_report.py` opens it with standard Python, without native work.
A04 now has qualified explicit parent-layout transport, separately from geometry
acceptance; trusted software and the lean child lifecycle remain next.

**Early session, 20 November:** the selected-state capture and two bounded
FT_Hg motion profiles are complete. The modest coupled movement was ready for
the matched continuation subsequently completed above; this earlier checkpoint
itself supplied no new refined model or f″ parent.
Fractional-degree changes are descriptive, not rejection criteria. All owned
native processes are stopped. The [current-state profiles](#a01-current-state-profiles)
record the evidence, limitations and next geometry-aware gate. The compact local
checkout is `ScienceCheckouts/Hazel/2026-11-20_current-state-profile/review.html`
beside the repositories.

**Evening session, 19 November:** the approved matched neutral/deprotonated
DF–Hg–DT research comparison is complete and independently read back. Two
five-cycle open XYZ/group-B fits used matched generated sources, identical
starting atom states, data/Free-R/phases, common original planes and Hg terms.
DF C1′–N1 changes **1.652534 → 1.601336 Å**, against targets **1.499 → 1.501 Å**;
Rwork/Rfree change **0.3082/0.3384 → 0.3087/0.3380**. The DF ring becomes flatter,
but its attachment remains long and C2–S1 moves farther from its target.
This is a partial response, not a repair or experimental protonation assignment.
Both jobs stopped and sealed; no f″ fit or checkpoint selection followed.

The whole-model context checker still refuses unrelated terminal B:1. The local
comparison preserves that state and uses the existing selected-site phosphate
and linked-preparation owners. Formal-charge readback is unavailable, and the
original V9 execution did not record individual optimizer stop reasons. The new
neutral passive replay records them below; the anion fit is not retrospectively
qualified, and completed macrocycles do not prove convergence. Routine donor-state integration
remains deferred until after the build. Do not repeat this pair without a new
question. Local evidence: `ft-hg-donor-comparison-20261119-01/` under the Alder
artifact anchor; independent endpoint review is
`cedar/c410-matched-neutral/matched-endpoint-review.json` under `branch-artifacts`.
The small local science checkout is
`ScienceCheckouts/Hazel/2026-11-19_donor-comparison/review.html` alongside the repos.

**A01 remains partial: ligand geometry and open XYZ/B refinement. A02 stays
gated.** Whole-base construction and exact restraint delivery have evidence, but
the FT_Hg open fit still stretches the sugar–base attachment. A readable CIF,
completed process, or Rwork below 0.30 alone does not establish useful geometry.
No new accepted geometry or f″ parent follows from current integration work.

Cedar C409 subsequently qualifies the declared DF/DT imide-anion sources and
their isolated two-seed native usability (separate Cedar source `452b7c45`).
Independent cold readback preserves all 145 files and confirms the exact H3-only
removal/N3 formal-charge delta with all other graph/charge state retained. Native
formal charge is not exposed by the API, and absolute CIP remains unassigned;
source-relative sugar handedness is preserved. This source change is not yet
adopted here. The investigator's later 19 November scope decision defers routine
donor-state integration until after NASolve is built. It is not an immediate
A01 gate or a prerequisite for another otherwise qualified FT_Hg open fit.
The approved matched neutral/deprotonated research comparison is now complete
as described above. Its aliases, selected polymer links and common planes were
checked through the shared owners; the whole-model terminal limitation remains.
Existing A01 geometry and evidence standards remain unchanged.
The retained C409 `site-compatibility.json` maps the exact A109 input: selected
A:12/B:4 atoms already match the derived sources by name, with OP3 as the sole
extra source heavy atom. Preserve eight unrelated DT sites and all Hg targets.
Use an actual site-relabelled child and the existing linked preparation owner;
the canonical-only construction projection cannot represent the existing DF
input. Recover declared links from preparation before pruning terminal atoms;
neighbor distances are inventory evidence, not link authority. This read-only
map is under the shared local `cedar/c409-declared-donor-state/` artifact anchor.

**A04 modern-parent recovery, 20 November: complete diagnostic proof.** The
retained modern checked root recovers all four checkpoints through unchanged
installed readers, with original science/source reads denied: **876 checks**,
one full registry read (**105.35 s**), subsequent resolutions **0.027 s**, and
zero native calls. All 392 original files remain exact. The private bounded
multipart layout stores **35,686,175 B**; its explicit peak disk bound is
**246,609,670 B**, including reader workspace. Temporary copies are removed.
Sixteen synthetic entry/exit refusal checks pass. A04 remains partial: the adapter below now supports explicit layout transport;
complete scientific session/software identity, campaign reservations and
retirement remain unimplemented. The
[storage contract](metal-campaign-storage.md#modern-parent-recovery-proof)
records preserved failed attempts, scope and next steps. Evidence:
`modern-parent-20261120-04/` under the Alder artifact anchor.

The call-path audit confirms current frozen metal trials already replay saved
context/source inputs; they do not perform C414's full registry walk per point.
The measured registry cost belongs to parent intake. Do not introduce a redundant
validation cache or describe it as a measured per-point performance improvement.

**A04 parent transport adapter, 20 November: implemented and qualified.**
The explicit portable-layout adapter reuses unchanged archive owners, releases
its transport scope before ordinary readers and checks its declared disk bound.
**96 focused tests pass**; the relocated **346-file installation** then recovers
the modern parent with **876 cold checks**, source reads denied and no native
calls. Registry intake takes **99.78 s**, subsequent resolutions **0.031 s**.
All owned processes and temporary views stop/close. Public transport is additive;
no existing run schema or native science changes. The
[storage contract](metal-campaign-storage.md#implemented-fourth-step-explicit-parent-layout-transport)
owns exact bounds, methods, evidence levels and remaining lifecycle limits.
Receipts: `parent-adapter-20261120-01/` under the Alder artifact anchor.

**A04 recorded-result inspector, 20 November: implemented and qualified.**
`input_archive.inspect_recorded_fdp` reads a selected historical result using
external archive/projection/trial/expected-parent pins and validates all internal
record links. It preserves separate attempts and refuses failed/incomplete
records, mismatched parents and partial archives without changing evidence.
The explicit recorded status grants no fresh scientific audit, current-parent
verification, execution, reuse or retirement. **117 focused tests / 34.76 s**
pass; a relocated **348-file installation / 718 checks** recovers exact saved
Hg and Ag4 results with original reads denied and no native calls. See the
[storage contract](metal-campaign-storage.md#implemented-result-inspection-from-the-input-archive)
for the API, exact command, failures and scope. Only the additive input-archive
API, its focused tests and documentation change; v1 archives remain readable
without migration. Existing full replay and shared retention owners are unchanged.

**A04 remains partial: lean frozen-trial storage.** Read-only inventory, scenario
forecast, lossless compact projection, exact input archives and explicit parent
transport/lifetime separation are implemented. The adapter reuses the shared archive/temporary-view owner, preserves
all attempts and reconstructs inputs without original-data lookup. Production
shared-parent retention, native regeneration, campaign budgets and safe retirement
remain separate gates; the bounded feasibility result below does not close them. Do not prune old immutable trials through an input-transport receipt.

A bounded A04 rehearsal now recovers two old legacy PostMR roots and their
metal parents through the existing installed readers from **782,402 bytes**
(**4,730,256 logical bytes**), with original science/source access denied and
seven missing/changed-dependency refusals. Exact archived-request reproductions
then return identical complete result records in **7.83 s (Hg)** and
**17.15 s (four Ag)** under the original trusted worker/native hashes.
These are diagnostic recovery checks, not scientific solutions. No new public
storage interface or deletion follows. Modern checked ancestry is now recovered in the separate diagnostic proof above;
production retention and full software identity remain open. Receipt anchors are in the
[storage contract](metal-campaign-storage.md#bounded-protected-parent-and-regeneration-rehearsal).

Construction is chemistry/connectivity driven. PDU and DF are qualification
examples, not names selecting special repairs. Related supported cases, unchanged
good cases and unsupported/ambiguous contexts need their own evidence. Label
invariance is useful mechanism coverage, not another chemical specimen.

## Reuse these results before proposing another experiment

| Evidence | Established result and remaining limit |
| --- | --- |
| Whole-base construction and native state export | Initial FT_Hg C1′–N1 is 1.49958 Å; source chemistry/link context and active-state B export are preserved. Construction does not qualify the subsequent open fit. |
| Matched weight/iteration/phase/normalization controls | Private controls expose pooled pairing/covalent weight-selection effects, actual stopping limits and a geometry/R tradeoff. None is an adopted repair; do not repeat the matrix without a new hypothesis. |
| Source/effective/native local audit | All 20 surviving local heavy atoms, 21 bonds, 30 angles and the 10-heavy-atom plane match the declared scope/targets/weights. Three removed source bonds touch explicitly deleted HO3′/HOP3/OP3. Missing local targets do not explain the retained strain. |
| Retained pooled versus covalent-eligibility controls | Attachment 1.66243991 versus 1.57775796 Å, against 1.499 ± 0.038 Å; Rwork/Rfree 0.28553/0.29088 versus 0.32905/0.34210. Geometry improves locally while diffraction fit worsens. These are independent old diagnostic fits, not successive accepted stages. |
| Shared C406 non-triple observation | Two one-cycle native arms with observation off/on have identical complete PDB bytes, output state and kernel counts. Local capture exposes 20/859 atoms and actual proxies. The 1.92975 Å attachment remains unaccepted; it is not comparable as a five-cycle endpoint. |
| Compact result projection | Three old FT_Hg trials produce 25,884 B of projection; the Ag4 trial produces 54,643 B. Every attempt and complete result remains. Original inputs/native evidence are still required; these are not safe-reclamation or accepted atom-count claims. |

The local audit passes 1,703 checks and rejects seven corruptions. Two complete
relabellings preserve all 51 bond/angle rows. Independent C406 readback passes
700 checks with the original root absent and 66 native files unchanged. H atoms,
cross-site/link/symmetry interactions and deferred native categories are not
qualified by the local scalar audit. Source phosphate chemistry is a separate
shared question; do not silently change protonation, targets or sigmas.

Exact native producer: **Phenix 2.2.1-6174**. Those native executions belong to
the retained controls; cold readback/projection/integration launches no new
Phenix or Coot job. All diagnostic values retain their actual source context.

## A01 matched ordinary continuation

Two complete **Phenix 2.2.1-6174** executions use the existing V9 owner and
unchanged native code, five additional macrocycles each, one process, seed 42,
original Free-R/MLHL phases, all declared chemistry/NA/metal restraints and
open XYZ/group B. Q/f′/f″ remain fixed; f″=0 is not a fitted result. Only nine
graph-selected starting coordinates differ. Source inputs and previous runs
remain unchanged; both endpoints are unselected. No production refactor or
schema change was made.

| Endpoint | Rwork / Rfree | DF C1′–N1 (Å) | DF / DT base B (Å²) | Hg B (Å²) | N3–Hg–N3 (°) |
| --- | --- | ---: | --- | ---: | ---: |
| Parent | 0.3082 / 0.3384 | 1.652534 | 30.32 / 85.68 | 63.37 | 117.89 |
| Unchanged restart | 0.2802 / 0.2902 | 1.622942 | 100.22 / 161.18 | 141.34 | 117.24 |
| Coupled input restart | 0.2820 / 0.2910 | 1.622245 | 84.78 / 146.39 | 123.43 | 119.14 |

Base means exclude sugar/backbone. The native final scale stage transfers
**43.10/51.92 Å²** to atoms in the two arms. Before final scaling, unchanged-arm
Rwork/Rfree are **0.3021/0.3261**. Report final B/R with that stage explicitly;
the result does not diagnose Cedar's current replacement-B behavior.

Both continuations flatten the DF base but retain the attachment/coordination
issue. Hg difference density changes from **−2.56 σ** in the parent to
**−5.55/−5.27 σ**, using each endpoint's unfilled model-assisted coefficients,
whole-cell sigma normalization and Q=1. The maps include Free-R reflections;
they are inspection evidence, not an independent occupancy/count measurement.
Do not choose between the arms on tiny differences. The known recipe is a
donor-vertex zero-angle term, not a metal-centered angle. Earlier native delivery,
finite-difference and stronger-geometry controls already exist; no missing-term
bug or reason to repeat those controls was established. Explicit current pair
edits do not add an A:12/B:4 hydrogen-bond restraint.

Validation: **205 cold checks** reproduce maintained native geometry readbacks,
target inventories, atom/Q identity, source hashes and stopping summaries; all
selected chirality signs remain. The maintained stopping module's **26 tests
pass in 4.90 s** (one sandbox pytest-cache warning). The full suite was not run.
The native observer records **75/92 XYZ calls**: **73/84** reach the iteration
cap and **2/8** have unreported reasons. This includes weight-search trials;
selected-endpoint convergence and group-ADP stopping are not inferred.
Execution times including preflight are **373.39/422.62 s**; both owned groups
are verified stopped. Rendering reads saved coefficients only; no new native
refinement or Coot launch occurs during report generation.

Evidence: `a01-continuation-20261120-01/` under the Alder artifact anchor,
including per-arm `execution.json`, `science-comparison.json`,
`recipe-history-review.json`, map settings, focused-test and publication receipts.
Exact native commands and process identities are in those execution records.
Cold review command uses `A194_review_continuation.py` with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder>/src` and Python 3.12.14;
`A195_continuation_maps.py` uses the recorded Phenix Python. Generated models,
maps, scripts and reports stay local, excluded from Git. Existing artifact
schemas/defaults remain unchanged; no migration or cleanup is authorized.

**Decision:** close the small-movement continuation subgoal. A01 remains partial
and A02 gated on broad geometry/coordination review. Do not start another tiny
starting-coordinate search or unchanged cycle series. The next bounded
engineering bridge is A04's once-per-session protected modern parent, retaining
complete evidence while avoiding full ancestry expansion for every cheap trial.

## A01 current-state profiles

The completed 19 November C397–C399/A166 history remains evidence, not a queue
to rerun. Its historical fixed-normalization state is not the current neutral
fit. The new work closes the **current objective-state capture and finite-profile
gap**, while leaving A01 geometry partial and A02 gated.

A passive five-cycle **Phenix 2.2.1-6174** run reproduces the neutral source
PDB bytes and every output MTZ array exactly. All **105 reciprocal XYZ trials**
report their native **25-iteration cap**. The chosen final-cycle state is return
105, before core/mask refresh and the last group-ADP update. The selected search
parameter is 15.234577; it is not the actual geometry multiplier, which is **1**.
The native normalization denominator is **11,222**. This observes stopping; it
does not prove the cap causes the distorted geometry.

Two separate diagnostic replays reproduce the full returned-state prefix and
selected source state, then retain the actual likelihood core, observations,
Free-R, phases, scales, masks, ADPs, scattering and restraints. Only the profile
uses direct factors. Each new direction passes central differences at ±0.0001
and ±0.001 (Å for contraction, radians for rotation). The profiles retain the
same 11,222 term memberships/captured parameters and restore their own targets
and gradients exactly. No optimizer resumes after a probe.

| Motion | Attachment (Å) | Change in combined target |
| --- | ---: | ---: |
| 0.02 Å contraction | 1.632534 | −0.000169979 |
| 0.05 Å contraction | 1.602534 | +0.000126095 |
| 0.10 Å contraction | 1.552534 | +0.002096913 |
| 3° reorientation + 0.05 Å contraction | 1.602534 | −0.000358296 |
| 3° reorientation + 0.10 Å contraction | 1.552534 | +0.001687939 |

Lower target is favourable only in this diagnostic objective. The starting
attachment is 1.652534 Å against a 1.499 Å target. Straight contraction leaves
the four glycosidic angles unchanged. The retained gradient suggests a small
rigid N1-pivot reorientation, which was tested at predeclared 1°/3° and two
coupled points. It lowers the target at some points. C1′–N1–C2 changes
132.32 → 132.63°, against a 121.76° restraint target: **effectively unchanged
for scientific review, not a failure criterion**. The larger existing offset
is context to inspect with overall base shape, coordination and maps, not an
automatic veto. Small angle/distance differences must not be mistaken for
experimental precision. Rigid motion preserves existing internal base geometry;
it is not a chi flip or ideal-base reconstruction. The coupled point remains
a reasonable test candidate, not an accepted refined structure.

The exact input DF/DT base means are **20.00/47.9056 Å²**, selected pre-final-ADP
means **34.3675/87.2376 Å²**, and final written means **30.32/85.6756 Å²**.
Hg B is **72.95 → 64.4891 → 63.37 Å²** across those stages. Means exclude sugar
and backbone. Hg **Q=1, f″=0 and f′ fixed** are settings, not fitted anomalous
results. No environmental metal-B assignment has run. These stage comparisons
alone do not establish why fitted B values are low; reuse the earlier
B/scaling controls before making a causal claim.

Validation: **299 passive + 339 contraction + 161 rotation cold checks**, plus
**12 directional finite-difference checks** and **25 cold projection/scalar
checks**. The native profiles use 11/12 evaluations in 2.511/2.946 seconds after
takeover; reaching the selected state requires the separate bounded replay.
The first replay stopped before probes on an identity tuple/list comparison;
the representation-only correction and altered-identity/order refusals remain
recorded. A later overly strict cross-profile gradient equality check is also
preserved: zero-angle pivot arithmetic changes last bits (raw-gradient maximum
1.70×10⁻¹²; targets identical). The existing 10⁻¹⁰ restoration tolerance passes,
with four corruptions refused. No native rerun was needed for that cold fix.

Evidence is under `a01-current-profile-20261120-01/` at the Alder artifact anchor:
`passive/`, the preserved failed `replay/`, `replay-identity-fix/`, `rotation/`,
`directional-anatomy.json` and the final publication/validation receipts.
Exact native commands/owned processes are in each `execution.json`; cold
commands use `A172_review_current_profile.py passive`,
`A176_review_identity_retry.py replay`, `A180_directional_anatomy.py` and
`A184b_review_rotation_profile.py`, with `PYTHONDONTWRITEBYTECODE=1` and the
declared Alder source/Python. The original strict A184 failure is retained.
No full suite, new map generation for the report or Coot session is claimed.

The staged comparison has now executed as described below. Its 199 input
checks remain evidence of preparation; the later execution receipts own the
completed state. Do not repeat the passive/profile experiments or small-movement
comparison without a new question. No wider weight/iteration/donor-state matrix
is queued. The private capture boundary remains distinct from scientific
acceptance or a general prerequisite for other chemistry repairs.

The capture seam is a private **ML/MLHL** precedent, not an LS-general supported
API. Future consumers need their own parent/stage qualification. Reuse the
existing `parallelity_parameters` collector on the actual frame to include
`limit`; the retained C397 inventory alone is insufficient to reconstruct all
native energies. Its dihedral inventory also omits `limit`, `top_out` and
`slack`; historical captures cannot be retroactively completed. Willow's existing
`topostitch_native_terms.checked_proxy_rows` already checks those live fields and
refuses unsupported nondefaults: this is a private capture-scope limitation,
not a newly discovered supported-reader defect. No repeated fit is needed to
qualify the older inventory's narrower recorded scope. Per-atom gradient projections and shared scalar geometry are
not per-restraint energies. Runtime, public schemas and migration remain unchanged.

## New readbacks and declared donor state

C407's shared final-site scalar report reproduces 112 existing PDU/DF rows;
installed readback is exact. No second coordinate calculator or changed numerical
worker is introduced. The saved one-cycle DF fit retains C1′–N1 = 1.92975 Å
against 1.499 ± 0.038 Å, C2–N1 = 1.67415 Å against 1.396 ± 0.030 Å,
and C2–S1 = 1.74920 Å against 1.638 ± 0.026 Å. These are descriptive local
observations, not native energies, new fits or a later stage of the five-cycle
controls. Missing hydrogen/link/symmetry context remains explicit.

The source DF dictionary includes neutral NH1 at N3 and an N3–H3 bond; the
A:12 DF/B:4 DT model has no H3 coordinates. Its recorded modification changes
terminal atoms, not this donor state. The investigator confirmed that Hg replaces
both N3 hydrogens. Shared chemistry Q13 owns explicit site-scoped state derivation
and native qualification, preserving neutral sources and unrelated residues.
Routine integration is deferred until after NASolve is built; the completed
matched research comparison is separate from product implementation and A01 completion.
Absent H3 coordinates do not establish equivalent heavy-atom restraint chemistry.
The delivered neutral and regenerated definitions differ in local bonds, angles
and plane membership, so those differences cannot all be attributed to H loss.
Preserve the approved plane policy and Hg terms in the matched comparison, record
remaining generation differences, and judge the local heavy-atom response without
assuming a repair. Intent does not establish new numerical targets, formal-charge
readback or the cause of the observed strain. No routine donor-state workflow is
implemented here.
Evidence and confirmed intent are in the integration anchor's
`coordination-state-question.json` and `coordination-state-authority.json`.

Cedar C408 separately supplies a matching-data PDU positive control. With
noise-free atomic amplitudes and the original restraints, the perturbed terminal
ring-plane offset falls 0.500205→0.088035 Å; the reference relaxes
0.094297→0.088595 Å. Independent cold review passes 70 checks and preserves
all 96 files. Eight separate scalar/count checks reproduce the two endpoints'
0.023303 Å selected-atom RMSD after background alignment. Both endpoints move
from the generator and R values rise, so this is bounded recovery, not exact
truth or experimental PDU/FT_Hg qualification. Reuse this completed control.
Receipts: `coordination-c408-native-review-20261119.json` and
`coordination-c408-endpoint-review-20261119.json` under the Alder artifact anchor.

A04's private four-request input archive is 251,197 bytes and reconstructs
all 36 declared files exactly after staging removal. Complete parent/audit and
environment identity, native regeneration and retirement remain open; see the
[storage contract](metal-campaign-storage.md). Original runs remain untouched.

That rehearsal is followed by the explicit Python input-transport adapter at
`26b0f41c`: 86 focused tests, including corruption, changed/missing source evidence,
pre-expansion byte caps and relocated source/data controls, pass in 51.35 s.
The source-free relocated installation preserves all 345 package files. Public
packing/expansion recovers three saved FT_Hg requests plus their full compact
records from 134,901 bytes (913,800 logical bytes), and one Ag4 request from
130,351 bytes (431,484 logical bytes). These archives differ from the earlier
private layout: they include complete result projections and remain per-run.
Original trials stay exact. This is input recovery, not native regeneration or
standalone scientific replay. See `input-archive-20261119-01/` under the local
Alder artifact anchor for exact commands, source pins and installed records.
The only source follow-up after those checks clarifies a comment about filesystem
expansion versus decoder RAM; its AST is unchanged. Peer static review found no
blocking issue. The focused validation is not a new whole-repository full pass.

## Evening validation and coordination

The private runners under `branch-artifacts/Alder/runners/` used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder checkout>/src
/private/tmp/willow-w94-pivot/env/bin/python -B <runner>` for the owned execution
and analysis. Cold recovery reviewers used the same Python with the existing
source-free installation explicitly selected; no source fallback or native job
was allowed during readback. Exact commands, hashes and timings are in each
experiment's progress/readback records.

- A138–A140: linked preparation, three fixed-coordinate Phenix captures and
  matched source/proxy checks; independent review passes. Preserve the initial
  atom-order harness correction; native atom identity, not row index, owns comparison.
- A141–A143: two complete five-cycle open XYZ/group-B jobs, final sealed scalar
  readback and saved-map rendering. Both processes stopped. The Hg capitalization
  and renderer-environment/PHIL-token setup corrections required no extra fit.
- A145–A148: shared archive and installed parent/root recovery; seven adversarial
  dependency checks refuse. The initial unresolved temporary-path attempt is retained.
- A149–A150: exact historical-worker/native-source preflight and two complete
  frozen-f″ reproductions, 180-second bounds, both stopped and exactly reproduced.
  No experiment in this session selects a checkpoint or changes ordinary defaults.

C412's independent cold review preserves the actual checked-preparation PostMR
root, its existing C403 descendant and both new registered chemistry/pair
continuations, all 855 fixed Q/ADP states, original observation/Free-R values,
D:1 protection and original recipe identity. All six requested pair terms already
have native owners; zero terms are added. Poor Rfree remains explicit. This is
shared mechanical evidence, not a qualified FT_Hg or experimental PDU endpoint.
This is modern ordinary continuation evidence, unlike C408/C411's private
synthetic-data parent. Root-free archive closure and Refine Doctor forwarding
remain separate. Receipt: `coordination-c412-review-20261119.json` under the
Alder artifact anchor.
C413 `1a4094fd` adds the shared literal plane reader on Cedar. Its final review
reuses 55 source and 55 relocated installed checks plus seven models/nine planes;
an independent missing-centre counterexample now passes without changing the
fitted plane. Exact FT_Hg model bindings reproduce the common-plane RMS values
**0.026598→0.010827 Å (DF)** and **0.008082→0.008355 Å (DT)**. These include the
recorded ten members, including C1′, and differ from ring-only fits. Symmetry
context and native residuals remain unassessed. No Alder runtime adoption follows.
Receipt: `coordination-c413-review-20261119.json` under the Alder artifact anchor.
C415 `a1620839` then qualifies explicit Python Refine Doctor forwarding of that
ordinary declared-site observation, preserving defaults and counted-ancestry refusals.
Its 80 focused tests plus 10 subtests pass. One bounded native standard group-B
trial preserves the selected PostMR root, named parent and measured inputs;
independent sealed-trial/plane readback preserves all 302 dataset files. Lower
Rfree accompanies a slightly worse terminal plane departure, so recommendation
is not geometry acceptance. These are substituted-scaffold PDU mechanics, not
experimental PDU/FT_Hg validation. The first setup attempt stopped before native
work because its version-string assertion expected a build suffix; it is retained.
Receipts: `coordination-c415-static-review-20261119.json` and
`coordination-c415-native-review-20261119.json`. No Alder runtime adoption or
separate installed/full-suite claim follows from this peer review.

The native Doctor check also identifies a separate counting issue: its ADP
eligibility ratio uses assigned flag groups rather than measured observations.
Rowan owns that correction. Existing metal XYZ/f″ adapters use the audit for flag
validity and do not consume that ratio; tonight's explicit group-B/f″ requests
are unaffected. Preserve the valid historical flag statistics and introduce an
explicitly measured-data count through its own qualification.
C414 supplies the modern-root dependency census for the existing C412 lineage;
its ten returned endpoint inputs omit most preparation/ancestry evidence.
The [storage contract](metal-campaign-storage.md#modern-checked-parent-dependency-boundary)
records the measured scope and next bounded parent-validation design.
W154's independent static/published-payload review finds no blocker in separate
model/map labels and confirms unchanged scientific display fields. Its completed
source/installed tests are reused; no renderer adoption or browser/GPU claim.
Receipt: `coordination-w154-review-20261119.json` at the same anchor.
W155's separate prescribed complex-F contrasts show that displacement, excess
model occupancy and an ADP mismatch can each produce negative density at P.
Independent cold checks preserve its six original files and exact source/variant
identity; the original version API field is empty and remains an explicit limit.
These are synthetic, commonly normalized complex differences, not experimental
Fo–Fc attribution or detector calibration. Receipt: `coordination-w155-review-20261119.json`.

The later isolated shared-reader rehearsal combines baseline `fb4f93d7` with
only the eight source/test files from C413 `1a4094fd` and C415 `a1620839`.
Alder's active scientific source remains unchanged. Two Doctor regression probes
fail on the baseline before the new option exists. On the private candidate,
**2,761 tests plus 70 subtests pass in two bounded parts**: 2,101 tests/50 subtests
before a graceful time-bound interruption, then only the 660 unfinished tests/20
subtests. All 1,505 candidate files remain exact. This is complete coverage of the
selected 80-file workflow/direct-consumer scope, not an uninterrupted profile run
or a full-suite pass. The earlier restricted-environment attempt retains its
eight process-inspection/termination failures and partial results; corrected
process permissions precede the successful checks. No scientific refinement runs.

The relocated installed candidate has **346 exact package files**. With original
build/install/development-source paths unavailable, it reproduces two existing
FT_Hg plane reports, recovers four old frozen-f″ requests and verifies all 35
referenced input files. Invalid Doctor observation intent refuses before work
allocation. The original geometry evidence is deliberately available; old f″ run
paths are denied. This qualifies those installed interfaces, not a self-contained
scientific archive, accepted geometry or general deployment. The explicit pinned
NARestraints dependency remains available. No new combined full gate or active
runtime integration is claimed; later Cedar fixes are outside these source pins.

Exact source patches, manifests, commands/environments, failed/partial results,
XML, split coverage, wheel and installed probe are retained under the Alder
artifact anchor `shared-readers-integration-20261119-01/`. Runners A157–A164
record the preparation, bounded execution, cold review and owned-scratch seal.
All recorded rehearsal processes stopped; only its owned private workspace was
retired (1,115,855,482 logical bytes), preserving 29 evidence/package files and
all original scientific runs. The small `mechanics.html`/`mechanics.json`
addendum beside the evening checkout records this result without changing the
original science report.
Reuse this evidence before scheduling another unchanged check. W153's separate
saved-stage review verifies 84 native rows and keeps initial scaling, XYZ steps
and final scaling distinct; the endpoint missing-work observation does not prove
stagewise reflection identity. Its two `coordination-w153-stage*` receipts remain
local, with no new fit, convergence claim or change to metal acceptance criteria.

The preceding peer readbacks changed documentation only. The later A04 parent
transport adapter above is a separate qualified runtime addition; its own focused
and installed receipts apply. Generated science, reports, private runners and
experimental archives remain local and excluded from Git. No scientific-policy
default or existing-run cleanup follows.

**A04 software census, 20 November:** one import-only probe and one exact
historical frozen-Hg replay complete and stop. The actual fit adds 22 modules
and 69 external resource reads beyond imports; 390 OS-image paths lack readable
backing files. Complete environment identity is not established. Preserve
historical results and share a scoped software profile across trial rows; do not
copy large binaries/fingerprints per point. The
[storage contract](metal-campaign-storage.md#software-identity-measured-boundary-and-next-contract)
owns exact sizes, versions, limits and the poor-fit fixture's scientific scope.
No production software collector or new scientific endpoint is adopted.

**A04 recorded execution cross-binding, 20 November:** the existing archive,
parent and frozen-state owners now compose in a private cold read of one saved
historical Hg execution. All nine input files rederive from the exact relocated
legacy parent, and the complete result matches its compact record and observed
software profile. **213 assertions / 11 refusals** pass in **1.26 s**, without
native execution; the bundle is **1,265,221 B**. This is a completed engineering
proof, not scientific acceptance, a modern-parent execution proof or an installed
reuse/retirement lifecycle. The 390 unavailable OS images remain unqualified.
Use the [storage contract](metal-campaign-storage.md#recorded-execution-and-parent-cross-binding)
for identities, failures, scope and exact evidence. Sources, schemas and defaults
are unchanged; only documentation is committed. Local generated evidence and
private runners stay excluded. No unchanged runtime tests or full suite reran.

## Next work, in order

1. Reuse the integrated development base qualified by the complete runtime
   execution and reviewed test-only correction under the agreed focused cadence.
   The root handoff preserves exact limits; no fresh full-green result is claimed.
   Do not repeat unchanged controls merely to relabel the original full failure.
2. Reuse the isolated C413/C415 source and installed consumer rehearsal when
   qualifying the next shared integration. Preserve scalar-versus-native-energy
   distinctions, global atom identities, missing evidence and unassessed science.
   Later peer fixes need their own source-bound review; do not build a second
   geometry calculator or repeat unchanged completed cases.
3. Reuse C412's checked-parent ordinary continuation evidence for the next A01
   consumer qualification; continue unresolved open XYZ/B geometry work under
   the existing evidence standards. C415 now qualifies shared Refine Doctor
   declared-site forwarding; consume that patch when integrating the shared
   runtime rather than implementing it again. Routine
   donor-state integration is deferred until after NASolve is built; C409 site
   application is not the immediate gate. Preserve its read-only compatibility
   map and the completed matched neutral/deprotonated research comparison.
   Reuse the completed [current-state profiles](#a01-current-state-profiles).
   The matched small-movement continuations are complete with no preferred
   endpoint. The saved-model donor-span decomposition is also complete (see
   pause checkpoint): both compressed donor separation and off-line Hg matter,
   while matching C1′ spans do not establish matching base pose. The new actual-state
   bridge diagnostic also closes: phased likelihood opposes tested Hg straightening,
   while both recipe and nonbonded geometry favour it. The base-opening finite
   profile is withheld on a predeclared numerical check; do not relax the tolerance
   or repeat it to obtain a pass. Scope an explicit local coordination alternative
   before any new fit, reusing the completed unchanged continuation as appropriate.
   Broad geometry/maps/refinement guide review; fractional deviations are not
   vetoes. No repeated control matrix is queued.
4. A04 explicit parent transport is qualified. The software census shows lazy
   modules/resources and unreadable OS components; store one scoped profile per
   identity, not one broad fingerprint/binary copy per trial. Define the supported
   execution identity and compact child audit/regeneration lifecycle before any
   retirement. Keep important nodes protected; geometry-moving work retains the
   stronger shared retention discipline. Reuse the completed legacy/modern cold
   recovery, exact historical reproductions and the completed recorded-execution
   cross-binding instead of repeating them. Distinguish historical evidence
   validity, a separately identified new computation and exact reproduction
   when defining the next supported execution contract.
5. Return to A02 only with a qualified open XYZ/B endpoint. Keep A05 GUI co-design
   and A07 reconstruction from experimental inputs explicit on the roadmap.

## Deferred post-development request

[A09 — hydration shells and counterion coordination](metal-development-roadmap.md#a09--post-development-hydration-shells-and-counterion-coordination)
records the 19 November request: investigate metal water shells and counterions
such as Mg when resolution is better than 3 Å or the user explicitly enables it.
Explicit, editable coordination spheres distinguish water ligands, other donors
and CoHex ammines. This remains after the main build; it changes no current
priority, scientific gate or runtime behavior. Structural shell changes retain
full geometry-parent protection before later frozen-f″ trials.
The same deferred milestone includes a sub-2 Å water-placement inspector (also
explicitly accessible for approximately 2 Å/noisy cases): bounded recipe batches,
numerical local map/geometry comparison, compact ranked alternatives and
uncertainty-aware review. Map movement, unsettled fits and model-assisted evidence
must remain visible; score calibration and automatic selection are future work.

## Scientific contracts that must survive

- Open XYZ/group-B refinement precedes environmental metal-B preparation. Use
  the actual refined base-only or donor environment, excluding sugar/backbone
  for base means; record inter-base mismatch and the chosen assumption.
- Frozen f″ trials fix XYZ, all ADPs and f′, with Q fixed at each declared point.
  Occupancy fitting is a separately declared stage. Preserve original Free-R,
  observations, wavelength, phase/scattering policies and all background scatterers.
- Cluster comparisons retain signed group/per-element sums and cancellation.
  A fitted f″ sum alone is not a unique count/identity or an acceptance rule.
- Human-solved models are endpoint comparisons, not hidden construction/search
  priors. Their f″ may be missing or from a later deposition refinement.
- Existing FT_Hg N3–Hg–N3 terms and source authority remain unchanged. Source
  distance targets, environmental B and acceptance gates are not tuned to force
  agreement with a reference endpoint.
- Scientific data remain local and immutable; no automatic checkpoint selection,
  new GUI execution route or campaign fan-out is introduced by this integration.

## Validation and evidence navigation

Last separately qualified metal runtime: `e002e2037048a4f5778898c7682174e96da5a01b`,
**6,432 tests and 276 subtests**, plus source-free installed real-data replay
and source/data relocation. Separate Cedar C406 runtime `58965920` passed
**12,043 tests and 293 subtests**, with two expected native opt-in skips.
These passes do not automatically qualify a new integrated revision.

Under the existing local Alder artifact anchor, retain:

- `df-source-native-audit-20261118-01/`: exact input contract, local term audit,
  label controls and checkout validation.
- `coordination-c406-native-review-20261118.json`: independent cold native check.
- `compact-projection-20261118-01/` and `compact-full-suite-20261118-01/`:
  real-data projections, installed checks and exact full qualification.
- `integration-rehearsal-20261118-01/` and `integration-delta-20261118-01/`:
  earlier scoped compatibility, package/relocation and owned-cleanup receipts.
- `integration-20261119-01/`: current combined candidate, exact patches,
  validation ownership/results and delivery status.

Exact historical commands, failed harness attempts and scope limits are linked in
the archived handoff. Publishers refuse old output locations; a replay requires
a fresh owned destination. No raw models/maps/native output are committed.

The earlier geometry checkout is
`ScienceCheckouts/Hazel/2026-11-18_FT-Hg_terms/review.html` beside the repositories;
the compact-record checkout is `ScienceCheckouts/Hazel/2026-11-18_compact/review.html`.
Both remain intact. Today's two-file afternoon checkout is at
`ScienceCheckouts/Hazel/2026-11-19_integration/review.html`. It retains the failed
integration gate explicitly beside measured geometry and storage results; it
provides the evidence trail for the evening report without new native work.
The subsequent mechanics checkout is
`ScienceCheckouts/Hazel/2026-11-19_input-transport/review.html`, with measured
archive sizes, preserved old diagnostic Q/B/f″ values and the scoped C409 result.

The evening checkout is
`ScienceCheckouts/Hazel/2026-11-19_evening-checkout/review.html`, beside its compact
`summary.json`. It links the new donor-comparison figure without copying it and
keeps historical bad-fit regeneration values separate from the new XYZ/B fits.
Source hashes and all four local report links validate; browser visual review is
not claimed. Total new report payload is 90,325 bytes.
