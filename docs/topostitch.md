# TopoStitch: periodic DNA connections, recutting and repair

Current scope, **2026-11-18**: explicit placement proposals and source-bound
ASU-cut inspection are implemented on `willow`. Automatic sticky-end repair,
new-ASU materialization and campaign integration remain future work. The
[audited roadmap](topostitch-roadmap.md) owns milestones and evidence; the full
design below is not a claim that those later operations are available.

TopoStitch helps a crystallographer separate two problems: whether DNA needs to
move to make an intended contact, and whether an already connected periodic object
would be clearer in a different asymmetric-unit representation. Present tools use
explicit model/construct assignments and chosen connections. They keep the original
model and report missing information, competing choices and unsupported chemistry.

| Installed command | Present behavior |
| --- | --- |
| `nasolve-topostitch-inspect` | Describe verified ends, periodic images, canonical contacts and declared-topology windows; print a review report. |
| `nasolve-topostitch-fit` | Propose bounded motion for one explicitly chosen canonical pairing; convergence does not establish a successful repair. |
| `nasolve-topostitch-preview` | Write a separate bend-preview candidate with fixed anchors, transformed ANISOU and serialized-backbone checks. |
| `nasolve-topostitch-cut-preview` | Describe verified graph IDs/binding with `--describe-graph`, or freeze an explicit image/forest proposal; write no replacement ASU. |
| `nasolve-topostitch-view` | Inspect replayed proposals in an offline HTML view, compare explicit cuts and save a source-bound preference. |

A declared backbone continuation can now retain its directed partner and exact
symmetry image across proposed cuts. Both endpoint boundaries must already be
marked as representation boundaries; a chemical nick, unknown boundary or
explicit do-not-connect choice is not overridden. Missing coordinates stay
visible. P/OP1/OP2 intent, geometric partner resolution and native enforcement
remain separate: a resolved connection does not activate a symmetry bond or
qualify its surrounding angles.

The [coordinate adapter](topostitch-coordinates.md), [periodic usage guide](topostitch-periodic.md)
and [bend-preview guide](topostitch-preview.md) describe inputs, optional dependencies,
commands and limits. Software, installed-package and viewer-logic checks exist;
actual browser/download/human cut review remains open. Native scientific gates
also remain open: the tested angle kernel can handle images, but the ordinary
manager evaluation and proxy-persistence paths are not a qualified seam route.
Saved preferences do not select a checkpoint or constitute scientific approval.

[Machine-readable intent](topostitch-intent.json) is development metadata, not
runtime authorization. Existing NASolve `full-auto` does not enable this work.

## Purpose and ownership

TopoStitch should help NASolve represent and repair designed periodic DNA:
identify intended connections, find their crystallographic realization, recut
an ASU when useful, and gently reshape or locally reconstruct a distorted arm
so ordinary refinement can work. It must run without an AI service or agent.

Use **TopoStitch** as the umbrella tool name, adopting the user's latest spelling
(previous discussion used TopoStich). It replaces the tentative repair names
Topo Surgeon / Topo Doctor. Registration Scout and registration mapping remain
shared infrastructure; Topo Net describes the specialized workbench/graph view.
TopoTrace remains the separate file-conversion and topology-export project.
No executable command, import, or package is renamed by this planning change.

The [construct-registration contract](construct-registration.md) remains the
owner of logical-site registration, periodic representation, junctions and cuts.
This document adds connection inference and geometry-repair policy. Integrate
these operations over one graph, not separate recut and stitch ontologies:

- **Recut:** choose different symmetry-equivalent ASU representatives and change
  serialization, without deforming the physical periodic structure.
- **Repair:** move/rebuild permitted atoms in a new model to realize an intended
  connection. Symmetry-related images remain tied to the same ASU variables.
- **Chemistry change:** alter true covalent connectivity or terminal chemistry.
  This is a separately declared operation, never implied by sticky-end repair.

Keep implementation isolated on Willow while reusing Pine foundations. At
branch creation Willow and Pine have the same source commit: no merge is
needed. Later synchronize deliberately with reviewed upstream changes; do not
merge unrelated active Cedar work just to acquire a future construction API.
The live GeoTest campaign is a later example, not a hard-coded design target.

A representation-only recut must also conserve the complete periodic scattering
object: no lost/duplicated orbit representatives, correct special-position
multiplicity, preserved chemical identity/occupancy/displacement parameters, and
proper transformation of anisotropic displacement tensors when present. Its
unrefined calculated structure factors should remain equivalent within numerical
tolerance in the same setting. Later refinement may respond differently to a
changed restraint/chain interpretation; record that separately from the recut.

## Explicit sticky-end enforcement during refinement (planned W122)

**User direction, 2026-11-17: planning only; no implementation or new runs.**
Offer **Enforce sticky-end contacts during refinement** as an explicit opt-in
through the existing refinement owner. This is a general, input-driven feature
for supported models, not a special case for the benchmark PDBs. Ordinary
refinement remains unchanged when disabled. CLI spelling and runtime schema are
not finalized; this section does not document an available flag.

**Pipeline position:** after versioned saved-request/preflight/admission and
continuation integration (C377/C378 prerequisites), make declared canonical
sticky-end enforcement the first user-facing refinement application. Test known,
already feasible contacts before requiring automatic end finding or large-bend
repair. Reuse the existing contact/registration and NARestraints/Cedar owners;
do not build a second refinement engine. A distant or misregistered partner may
still require placement first; strong restraints do not solve that problem.

1. **Canonical full-pair mode first:** explicitly identified A–T/G–C contacts use
   their H-bond heavy-atom distances, directional angles, joint planarity and
   parallelity at exact symmetry images. Bind residue identities/register,
   sequence, polarity, model/frame and image translations. Reuse native terms and
   add only missing coverage. No duplicate weighting, new covalent phosphate bond,
   automatic phosphate deletion or silent nonbonded-exclusion changes.
2. **Separate plane-only mode next:** permit explicitly requested mismatched-pair
   plane/parallelity hypotheses after independent recipe, coverage, gradient and
   native-lifetime qualification. The current canonical packet/compiler does not
   support arbitrary mismatches; do not bypass it by relabelling a pair. Do not
   invent canonical H-bonds or report H-bond recovery in this mode. Planes alone
   leave in-plane translation/rotation and pairing register underdetermined;
   retain native chemistry, packing and diffraction checks. Joint coplanarity is
   not an inter-base stacking or blunt-end model, and is not appropriate for every
   mismatch merely because bases are nearby.
3. **Inference later:** accept a declared scheme or an already reviewed contact
   proposal first. General model availability does not authorize binding every
   nearby end. Bounded automatic inference and campaign transfer reuse the
   existing explicit permission policy; unsupported chemistry and ambiguous
   partners remain visible rather than silently coerced.

**Validation order, not new executions:** start with declared canonical 8D93
sticky-end contacts, then an independent 5W6W/DOHU case. Inventory exact sequences,
residues and symmetry partners before using 7R96 as the user-proposed mismatch /
plane-only challenge. Include healthy contacts, modest deliberate displacement,
wrong partner/image/register, missing atoms and duplicate native terms. A generic
model can exercise geometry without data; R statistics require its matching
observations and original Free-R flags. Compare otherwise identical enabled and
disabled refinement siblings with a frozen budget and weights, preserving good
contacts, backbone/sugar geometry, chirality, junctions and periodic packing.
Report before/after pair distances/angles/plane measures, collateral changes,
maps and Rwork/Rfree where available. Restraint-satisfied geometry alone does not
validate the chosen pairing, and no Rfree improvement is promised.

Do not promote W37's first-guessed 5W6W AT/GC fixture to a healthy sticky-end
control. It was an identity-image numerical probe, not a reviewed end assignment;
a selected angle reached 175.96° and the declared large-step derivative gate stayed
REVIEW. Retain that result and review exact sequence/image/contact identity before
choosing B10 inputs. This does not diagnose the deposited structure or authorize
loosening the earlier derivative threshold.

A read-only inventory of the declared local W catalogue also distinguishes its
actual search-model variants from `seq_base.txt`. The `C_G.pdb` variant differs
at A:12/A:13/B:3/B:4; `5W6W_noPO4.pdb` differs at A:13/B:3 under the explicit
legacy strand map. Their D:1 terminal phosphate inventories differ as well.
These may be intended catalogue choices, not defects or mutation instructions.
Do not treat a filename, a family template or a missing/present terminal atom as
proof of healthy sequence, pairing or free-end chemistry. Bind actual identities,
terminal intent and reviewed operators before B10. The existing sequence-family
comparison owner supplied the inventory; no coordinates, connections or targets
were edited. Local NASolve-anchored receipt:
`branch-artifacts/willow/b10-catalog-inventory-2026-11-18.json`, SHA
`f37eae630c894b709ac32d41a0c0ff4d863320d11ef30e09c7fea4fbeb15ddcf`.
It is preparation evidence, not a qualified contact or a new diffraction run.

The review UI should show which contacts/images and restraint families were
requested, which actually ran, and the result or refusal. Retain the request
through fresh checked parent rebinding and manual/Doctor ancestry. Off-path
compatibility, installability, cold read/relocation, failure retention and matching
native scope must pass before the option is advertised. This plans an S05/S06
application; it closes no repair, inference, stacking or covalent-closure gate.


<a id="next-bounded-coordinate-control-planned-after-w135"></a>
### Longer coordinate control and matched scientific gate

**W138:** candidate `d8656b22` on the Cedar code base qualifies the explicit
100-cap protocol through focused, installed, full-source and actual ordinary
native checks. It preserves old workers/defaults and requires v8/cycle-v2 final
writer/pair capture. The configured maximum is exactly 100; actual optimization
may stop earlier. This is an implemented opt-in mechanics route, not recommended
scientific weighting or a generally accepted repair.

The same-start short/long comparison improves the selected GC plane angle
17.78→6.29°, while Rfree stays .2609 and Rwork worsens .2251→.2271. It does not
isolate restraint efficacy. W139 completes the separate C400 matched matrix below,
including passive actual stopping/count history. Native/zero are exact; full
improves common14-pair geometry but worsens Rwork/final clashes. Both stop
`stpmin()`. Same-coordinate count-driven score discontinuity is recorded, not
fixed by a new policy. Do not duplicate these controls or conflate local benefit
with accepted repair.
See [W138 evidence](topostitch-periodic.md#w138--qualify-the-explicit-longer-coordinate-control).

Use the existing controller, actual-preflight admission, counted owner and writer.
The new explicit versioned scope leaves old v3–v7 worker bytes, cold readers and
the old 1–10-iteration guard unchanged. Preserve original pair intent and fresh
parent rebinding; unsupported settings refuse instead of being overridden.
Freeze identical source, core PHIL, observations, Free-R and unrelated restraints
for three siblings: native core with no counted owner, the same core with zero
addition, and the full declared pair recipe. Native/zero equality is an identity
control; full versus core is a different physical objective. Retain exact endpoint
coordinates once through the existing observation seam so W123's complete-recipe
readback can compare the same measurements; a digest cannot reconstruct them.

The current counted owner adds the fixed supported contribution to each actual
native restraint count; it does not freeze that native count. The observed
11,382 +17 endpoint is not a general invariant. Its current statistics retain the
last successful call, so longer controls need passive history from actual returned
evaluations, without extra energy or neighbor-cache queries. Standalone masked
bending already uses `UNNORMALIZED_SUM` with native normalization disabled; the
ordinary-refinement denominator question does not retroactively diagnose those
older bending trajectories.

Record actual iterations/evaluations and termination, not only completed cycles.
Reuse qualified passive observations of raw geometry, term counts/normalization,
data terms and gradients where compatible. Hazel's A79/A84 metal replay exposes
two identical-coordinate denominator jumps at line-search lower-bound failures;
other rounding failures remain unexplained. This is not canonical evidence or
permission to freeze a denominator, replace normalization or tune against Rfree.
Any such numerical policy needs separate derivative, neighbor-update and
native/zero/full qualification. A larger cap alone is not a repair.

The native denominator counts included nonbonded candidate proxies, including
potentially zero-energy ones; it is not an active-force count. Buffered cached
lists can depend on their construction history. This source observation supports
a mechanism, not a per-member diagnosis of the recorded events. A57/A58 already
cover a geometry-only same-site count change and fixed-denominator control;
do not recreate them. Counting only active contacts would introduce another
coordinate-dependent denominator, not remove the need for qualification.

Compare pair, retained-core, backbone/sugar, stacking and periodic packing geometry
with matched diffraction statistics, preserving failed/ambiguous REVIEW outcomes.
A universal covalent classifier is not a prerequisite for this explicitly labelled
fixed-weight control; it remains a gate before semantic geometry-driven weight
selection. B10 healthy/displaced/wrong-contact controls, density calibration and
CLI/Doctor activation follow their own milestones. The archived planning-only
record in W135 grants no execution authority and changes no current protocol.

<a id="longer-control-implementation-review-map-planning-only"></a>
### Longer-control implementation review map (completed in W138)

W138 implemented this bounded review across the existing admission, scope,
worker and writer owners. This table records the completed extension and the
invariants future changes must preserve; it is not another pending patch:

| Existing owner | Required review for the new explicit scope |
| --- | --- |
| `refinement_counted.validate_autorefine_control` and AutoRefine parameter/report writers | Protocol admission, emitted native cap and recorded cap must agree; old protocol/default strings and values stay exact. |
| `cif_counted_refinement.refinement_scope` | Inspect both actual preflight and actual driver parameters; preserve unit weights, XYZ-only strategy, one cycle/process and all other exclusions. |
| `refinement_counted._scope`, `_observation` and saved admission readers | Accept only the new explicitly identified scope; preserve old <=10 validation and fresh prepared-versus-actual equality. |
| `refinement_parallelity._code`, source digests and phase dispatch | Freeze affected old worker bytes before adding a new policy; preserve every historical payload and reader refusal. |
| `cif_counted_phase`, completed-phase readers and `_require_policy_continuation` | Review every exact-v7 check: a newer policy must not silently skip final pair capture/publication or lose native written-model proof. Preserve original intent and chemistry inheritance. |

W138 regressions cover old-protocol refusal of >10, unsupported combinations,
stale scopes and descendants losing proof/capture; existing wrong-writer,
namespace, relocation and installed-package checks remain in place. W139 completes
the native/core-only-zero/full comparison with actual stopping/count history.
These are completed gates, not another experiment queue; a newer policy name
alone never establishes a stronger scientific capability.

### Stable-objective invariants (deferred design; unimplemented)

This is an S06 design note, not a newly scheduled experiment or numerical policy.
Rowan's shared Cedar execution queue remains authoritative; its current fresh
corrected-PDU preparation/publication gate is separate and owned by Rowan.
Willow does not start another canonical matrix automatically or edit that chemistry.

**Use the evidence already obtained.** A85 applied fixed normalization to both
returned geometry values and gradients in the actual FT_Hg minimizer. Its
fixed-denominator trace showed no same-coordinate count-change events, but
stopping and chemistry were not rescued. Candidate counts remained dynamic;
this is not a measured zero discontinuity at matched cache transitions. C397–C399
separate FFT score/force disagreement from normalization: direct derivatives
agree at one saved state, yet the reset direct optimization still caps without
chemical repair. C400 independently establishes a canonical count-driven scalar
discontinuity; it does not establish that this is the sole cause of `stpmin()`.
Do not repeat these observations as new discoveries.

**Remaining canonical question:** can an explicitly scoped policy give the same
combined objective and gradient at the same complete scientific state across
real neighbor-cache rebuilds, while preserving complete pair semantics and the
ordinary execution/reporting contract? C400 observes the existing policy; A85
does not qualify this composed canonical/ordinary protocol. Before a new run,
state which part of this question remains unanswered and what result would
falsify the proposed policy. No fixed denominator value is selected here.

The required invariants are:

- Bind coordinates, non-XYZ state, observations/Free-R, scales, likelihood core,
  absolute weights, policy and active physical term definitions. Same bound state
  must produce consistent objective and gradient within predeclared justified
  tolerances. A coordinate hash alone is insufficient.
- Keep repeatability and derivative correctness separate: equal values/gradients
  on repeated state/cache paths do not prove the gradient differentiates the
  objective. Require qualified derivative-consistency evidence for the actual
  composed objective; reuse prior evidence only where its applicability is shown.
- Preserve every intended physical force, including repulsion and pair terms.
  Cached candidate-list membership may change when mathematically inactive terms
  enter or leave; do not require list-byte identity or equate candidate counts
  with active forces, covalent chemistry or a topology change.
- Normalize the objective and its gradient consistently. Specify initial weight
  meaning and any rescaling explicitly; never choose a denominator or weights
  by looking for a better Rfree. Keep the raw and normalized contributions
  separately inspectable through existing passive observations.
- Audit every affected consumer: evaluator, native monitoring, weight selection,
  output summaries and saved/replayed scope. A private evaluator-only correction
  does not qualify a whole-pipeline policy. Preserve old worker bytes and refuse
  unsupported compositions rather than silently changing existing runs.
- If a candidate survives those checks and the shared queue authorizes execution,
  predeclare one bounded canonical comparison with native/zero identity and full
  intent, actual stopping, original data/Free-R and independent geometry review.
  Stop on failure; do not launch a sweep or retry until Rfree looks favorable.
  Numerical consistency, physical benefit and scientific acceptance are separate.

Density calibration, explicit sticky-end activation and larger bending remain
later gates. This note adds no runtime behavior, test harness or active native job.

## Ordinary-owner integration boundary (W126; planning)

**W128 implementation status:** Cedar C386 now satisfies the initial owner join
under the explicit Python-only `counted-xyz-fixed-unit-v1` protocol. It preserves
original intent, optional declared recipe frame, existing input/process owners
and final-writer proof before publishing an unselected REVIEW. Ordinary settings
remain unchanged. C388 subsequently qualifies passive site-scoped chemistry
observation; broader terminal and phase protocols remain separate gates.
See the [audited result](topostitch-periodic.md#w128--carry-explicit-pair-restraints-through-ordinary-autorefine).
The original contract below remains the boundary for broader qualification;
it is not a claim that the user-facing W122 option or Doctor integration is ready.

Before automatic weights, compare the actual geometry statistics used to select
them across equivalent native/additive provider splits. Provider-independent
objective normalization alone cannot establish provider-independent selection.
Keep covalent, NA-pair and metal geometry distinct in scientific readback. W129
now measures that summary dependence in one frozen-state comparison,
without an actual weight decision. Use semantic coverage to separate geometry;
origin 4 edits can also contain legitimate covalent/terminal protections. Coordinate
selector policy with Cedar/Hazel; do not repeat the passive comparison or add a
new optimizer.


The next classification seam should combine Cedar's source-backed component/link
provenance, declared canonical-pair coverage and Alder's existing
`nasolve.metal.native_terms.describe_native_terms` adapter. The latter declares
explicit metal distances/angles against exact atom identities and targets; it is
not a general covalent classifier and currently requires identity images.
Hazel confirms the origin-0 eligibility filter used in private FT_Hg experiments
has no maintained general implementation or broader qualification. Do not adopt
it as a default, or label every term left after pair/metal matching as covalent.
Unknown and conflicting ownership remain unclassified until source-backed.

W131 adds the optional **cold pair-geometry report** outside the frozen refinement
helper closure. The caller first obtains existing `NativePairRecipe.describe_terms`
at exact force coordinates, `describe_compiled_pair_terms`, a v2
`observe_native_pair_terms` record, and the already frozen provider selection:

```python
from nasolve.topostitch_pair_geometry import review_pair_geometry
from nasolve.topostitch_recipe import recipe_digest

records = [attribution, compiled_declarations, native_observation, provider_selection]
frozen_digest = recipe_digest(records)  # freeze at the trusted observation boundary
report = review_pair_geometry(*records, expected_inputs_sha256=frozen_digest)
```

The caller authenticates the original observations. Recomputing a checksum after
changing evidence does not authenticate it. The reader checks source/recipe/atom
identity, compiled binding, exact force-site digest, complete coverage and measured
targets. It imports no native engine and writes no files. Complete pair measurements
are independent of which provider supplies each term. Output kind
`topostitch-covered-pair-geometry`, schema 1, is descriptive only:

- `pair_geometry` and per-pair `pairs` keep unweighted distance/angle deviations
  separate from `pair_energy` and its existing normalization.
- Plane RMS is RMS of per-plane RMS distances, **not** pooled per-atom RMS;
  parallelity uses the native delta in degrees. No acceptance cutoffs are supplied.
- `coverage` retains exact requested/provider/observed IDs. The
  `unclassified_native_terms` preserve native IDs/families/origins;
  `covalent_geometry` remains `UNASSESSED`. Origins 0/4 do not classify chemistry.
  This remainder covers the four observed families only; dihedral, chirality and
  nonbonded families are outside this inventory.

This report does not change ordinary refinement, automatic weights, existing
saved records or frozen v5/v6 helper bytes. It is not part of the native worker
closure. Independent covalent/terminal ownership and density evidence remain
future integration work with Cedar; no CLI/Doctor activation follows.

W133 independently qualifies Cedar C391's explicit v7 final-state capture with
`execute_autorefine(..., counted_pair_geometry=True)` inside the existing bounded
counted protocol. The writer runs while counted forces are active; observation
occurs after that owner closes, using the same returned model and frozen provider
selection. Hierarchy **and** scattering digests join the full-precision force-site
attribution to the completed writer and exact PDB bytes. One descriptive energy-only
kernel call is counted separately from optimizer activity. Old v3/v4/v5/v6 workers
remain exact. A v7 descendant cannot silently drop its requested report; unsupported
broader protocols still refuse. The cold controller reuses the compact evidence
archive owner. This is an explicit Python API, not W122 CLI/Doctor activation or
an accepted repair. See the [W133 audit](topostitch-periodic.md#w133--bind-complete-pair-measurements-to-the-actual-final-writer).

C381–C385 now qualify explicit saved admission, registered same-intent
continuation, existing C278 PHIL namespace copies and v6 native-written-model
binding. At W126/W127 they did not activate the ordinary AutoRefine/Doctor
route. The join was specified as follows; C386 closes only its bounded initial scope:

1. **Factory identity:** W118 accepts coordinate/B/ANISOU changes within the
   unchanged atom identities/order, occupancy, chemistry, internal chain breaks
   and crystal frame. PHIL scope spelling through C278 is not an atom/residue
   namespace change. Extra terminal restraints or chemistry projections require
   their own checked join; never infer compatibility from filenames or atom count.
2. **Working frame:** bind one declared frame before compiling images and native
   preparation. Preserve exact space-group setting and lattice translations.
   W115's explicit model-cell override is a diagnostic control, not a general
   PDB-over-MTZ policy. Resolve representation precision internally with declared
   provenance; do not silently relax the compiled-state tolerance or ask users to
   arbitrate insignificant decimal differences. Changed frames require explicit
   registration/qualification, not same-frame recipe rebinding.
3. **Requested versus actual protocol:** reuse the existing parameter writer with
   an explicit supported request/profile. Refuse incompatible ordinary options
   rather than silently narrowing their defaults. C377 currently qualifies one
   all-site XYZ cycle, 1–10 iterations, one process, fixed unit weights and no
   target/identity-changing phases. Actual resolved native preflight remains the
   authority; copied CLI strings are insufficient. This is not a recommended
   scientific refinement default. Broader weights, ADPs, scaling and phases are
   separate gates.
4. **Ordinary ownership:** consume the existing input-adaptation proof, processes,
   stopped-preflight admission, temporary prepared view, result and checkpoint
   publication through AutoRefine's existing owner. C385 now binds the actual
   native-written model to the usable checkpoint for explicit v6; a valid checksum
   for another model is insufficient. New ordinary rounds promising this guarantee
   must request v6. The continuation helper preserves inherited v5/v6 policy; an
   explicit v5→v6 transition requires fresh preparation/admission and retains the
   old evidence's narrower meaning. Preserve native errors and partial outputs. No second executor, recipe engine or untracked side path.
   Keep initial counted diagnostics unselected REVIEW using existing selection
   controls, even if a metric improves; mechanical usability is not adoption.
5. **Next validation:** cross that actual owner/publication boundary once with a
   frozen supported request. Reuse C381/C382 lifecycle and failure evidence where
   unchanged; repeat only boundaries changed by the new owner. Independent
   structures, matched controls, broader native scope and full integration checks
   still precede a supported feature or merge. Do not run more short cycles merely
   to improve presentation or tune repeatedly against Rfree.

This is a planning contract, not new runtime schema or CLI behavior. The planned
W122 application remains canonical declared sticky-end contacts first; automatic
inference, mismatch/plane-only variants and large-bend repair stay later.

## Human intent and unattended campaigns

The concise human option should be **Find and repair sticky ends**. Exact CLI
flags and serialized policy keys are deferred until backend implementation.
The same backend policy serves standalone CLI, Pine's eventual workbench and
the Campaign desk UI; there must be no GUI-only inference rules.

| Context | Proposed behavior |
| --- | --- |
| Isolated request without connection intent | Scan and show a concrete proposal; ask whether these ends should associate before moving atoms. |
| Isolated request explicitly allowing inference | Use the bounded policy without asking again about every proposed connection. |
| Campaign without the option | Preserve existing execution behavior. |
| Campaign with the option | Infer and test eligible connections without per-member prompts; save alternatives/failures and queue human review. |
| Ambiguous or unsupported case | Retain the original model; optionally test bounded alternatives if separately permitted, otherwise defer that repair and continue other members. |

Freeze inference authority, applicable members/designs, operation classes,
search/motion/refinement budgets, scheme-sharing permission and selection policy
in the new campaign's recipe. Existing `full-auto` alone does not gain this
power. Missing permission means off. Explicit do-not-connect declarations win
over inference. Requesting one named connection does not authorize editing all
other ends. An unresolved inference is not a batch-wide interactive prompt.

Core TopoStitch preserves current. Trying a candidate and provisionally selecting
it are separate actions. An explicit campaign selection policy may select a
qualified result, with the previous checkpoint retained, `user_approved=false`
and inspection required. Resume must honor a subsequent human veto/current
selection and must not repeat completed attempts. Review warnings survive a
numerical SOLVED label. Reusing a scheme does not inherit its human approval.

## Four layers of representation

1. **Logical construct:** strand/domain identities, sequence and register,
   duplexes, junction routing, intended termini and chemistry. Model-derived
   assignments retain uncertainty when full design inputs are unavailable.
2. **Connection scheme:** which logical end roles associate, their pairing
   register/orientation and permitted edge types. This can be campaign-shared.
3. **Dataset realization:** actual model sites, symmetry operations, lattice
   translations and editable windows for this checkpoint and cell setting.
4. **Evidence and decisions:** unedited observations, inference alternatives,
   construction/refinement results, authorizations and human review.

Keep covalent backbone, base pairing, stacking and symmetry correspondence as
different edge types. Cohesive sticky ends can form a continuous-looking duplex
while remaining chemically nicked. Neither proximity nor a completed stack
licenses a new phosphodiester, missing phosphate, OP3 or changed strand routing.
An ASU seam is not a chemical nick; a PDB chain end is not necessarily either.

## Designed blunt contacts and single-base stacking (W93; planned)

A designed blunt interface is a noncovalent stacking contact, not a request to
continue the backbone or enforce coaxial duplex-end frames. Classify it from
frozen construct/strand pairing and terminal chemistry, with observed coordinates
as supporting evidence. A truncated model alone cannot prove a designed blunt.
Keep unknown ends and the no-contact hypothesis explicit. Mixed sticky/blunt
constructs need per-interface intent rather than one global repair rule.

[Blunt-force assembly](https://doi.org/10.1038/s41467-026-69973-1) demonstrates
noncanonical terminal polarity and twist. Public [9PGR](https://www.rcsb.org/structure/9PGR)
(P321, 3.62 Angstrom) is the single-pyrimidine-pair stacking challenge. Local SI
version 2.8, Table S4 and Fig. S6, inspected 2026-11-16, records the 18_7 G|A
5-prime/5-prime face at -123 degrees and the other face at -38.2 degrees.
The local PDF was not verified byte-identical to the publisher supplement.
These are signed interface twists, not plane-normal tilt targets; exact ordered
atom frames/symmetry mates and the sign convention still need reconstruction.
Do not translate prose about inverted motif orientation into an improper
crystallographic operation or a change of DNA handedness.

Represent contact evidence at the individual-base/ring level. A single supported
stacking pair can be sufficient; do not require both terminal bases to overlap,
Watson-Crick complementarity, opposite polarity, or B-DNA twist across the blunt.
Measure plane separation/angle, lateral overlap and in-plane twist separately,
using full labelled frames where needed to distinguish polarity. Normals alone
lose the signed twist. Keep within-duplex covalent geometry, chirality, junction
routing and periodic clashes constrained. A stacking edge never authorizes a
phosphodiester bond, phosphate deletion, terminal cap or missing-residue fill.

Schedule classification with S02; qualify contact-specific S04/S05 targets only
with S06 map/model/data binding and density-aware matched refinement. A small
stack provides fewer orientational constraints, so report uncertainty and let
diffraction support resolve motion. Retain multiple plausible contacts rather
than forcing helical alignment. The newly merged TopoTrace 0.4.0/NAtopo-derived
terminal-stack detector is reusable candidate evidence, not yet a NASolve
restraint policy or proof that its fixed thresholds cover 9PGR. Existing Cedar
pair/plane and NARestraints atom-mapping owners need explicit supported recipes.
Benchmark preserved 9PGR contact, perturbed contacts and healthy no-op/wrong-mate
controls; do not hard-code its angle into a general acceptance threshold.

## Finding candidate connections

Start read-only from an explicit, checksummed checkpoint and its frozen target,
chemistry, cell and symmetry. Describe existing healthy contacts before edits.
Use mapped sequence/strand direction plus observed pairing and stacking runs to
locate duplex ends. Distinguish overhangs, blunt ends, intended free ends,
internal unmodeled intervals, true nicks, junctions and representation seams.
Missing atoms or weak density are coverage uncertainty, not evidence of a
sticky end. Support detection with incomplete inputs but restrict what it may
conclude or repair. Keep distinct model/alternate conformers uncombined.

For each eligible end, propose neighboring duplex-end images using the actual
cell metric, full space-group operators (including screw/glide/centering), and
bounded lattice translations. The search bound derives from permitted editable
length and displacement, not just an H-bond cutoff: the desired partner may
currently be far away. Enumeration must cover the declared bound even in a
skewed cell or when coordinates lie outside the reference unit cell. A truncated
search cannot support a claim of unique assignment.

Evaluate evidence separately:

- sequence complementarity, possible registers and 5-prime/3-prime direction;
- full base-pair/end-frame orientation, helical phase and stacking compatibility;
- established contacts, strand routing and declared arm/domain relationships;
- available deformable length and reachable endpoint position/orientation;
- steric compatibility with both strands and surrounding symmetry images;
- recipient density support where available, with source/model bias explicit.

Use verified NARestraints role mappings and supported pair recipes, not raw
column-header matches or invented chemistry. Canonical DNA is the first repair
scope. Designed noncanonical contacts can later use explicit supported recipes;
a blanket Watson-Crick rule must not redefine the intended design.

Find mutually compatible assignments, not independent nearest-neighbor joins.
In the initial simple-duplex scope each overhang pairing site has at most one
partner; more complex junction relationships require an explicit richer model.
Include the no-connection hypothesis. Existing contacts provide evidence and
constraints, but an inferred expected degree must not force every end to pair.
Symmetry-equivalent candidate edges are one orbit, not independent votes. A
logical self-edge can validly connect different images of the same site.
Reciprocal transformations must agree. Track winding through the lattice;
periodic graph cycles need not have zero lattice translation.

Record a connection as observed/intended separately from whether it is healthy,
distorted, absent or unknown in this model. A useful dangling-end hypothesis
means an eligible end lacks a supported association under a proposed scheme;
it does not simply mean a long distance or absence from a bond table.

## Geometry search and construction

The core use case is an existing duplex with usable local geometry but the wrong
larger-scale shape. Explicit benchmark classes are: a straight MR/predicted
(including future AlphaFold-derived) duplex that must curve to fit recipient
data; a bent MR duplex that must straighten; and a curved template that must
bend in a different direction or redistribute curvature. Preserve useful local
pair/sugar geometry and sequence in these cases. Do not assume every failure
requires new residues, a single preferred bend direction or increasing curvature.
AlphaFold integration is planned separately; no prediction service is required
by this tool and no such integration is implemented by these notes. Damaged or
incomplete duplexes remain additional, harder cases rather than the default.

Apply the smallest feasible operation first:

1. Resolve whether a representation-only recut suffices. Recutting cannot heal
   an actual physical gap; measure periodic distances before and after.
2. Bend/twist existing DNA over a small permitted paired window, keeping
   anchors, identities, handedness and local chemistry intact.
3. Expand the window by whole paired steps on both strands when local closure
   fails, subject to displacement/length/trial budgets and junction boundaries.
4. Only under a separately enabled rebuilding capability, reconstruct a local
   interval from known sequence and residue count using oriented base frames,
   then solve and regularize the sugar-phosphate paths.
5. Audit full atomic geometry and native interpretation; refine a new child
   and test whether the intended connection survives.

Use full frames, not plane normals alone: position, in-plane rotation, groove
orientation and strand direction are necessary. Optimize base-pair-step rise,
shift, slide, roll, tilt and twist within a benchmarked sequence/context model.
Stack preservation allows appropriate overlap and curvature; exact parallelism
of every plane would defeat bending. A phosphate envelope/centroid is useful
for coarse feasibility but is not sufficient to place a valid backbone.
Non-clashing atoms alone do not establish covalent closure or valid torsions.

As an illustration only, 30 degrees spread evenly over seven base pairs means
six steps, approximately 5 degrees per step in a planar construction. This is
not a universal allowed bend. Actual local rotations must be composed in their
rotating frames; benchmark distributions rather than adopting this number as
a target or cutoff. Frozen objective terms, initialization, candidate order,
solver tolerances, library versions and any random seed must be recorded.

The product is a general, input-driven duplex placement/reshaping tool. Public
8D93, the supplied hexagonal dataset and the other named structures are
replaceable benchmarks, not special cases in the algorithm. Keep structure IDs,
example transforms, model coordinates and benchmark-specific thresholds out of
production decisions. Behavior follows explicit sequence/identity mappings,
crystal symmetry, connection evidence, editable boundaries and qualified
geometry/data policies. Broader claims require independent structures and
forward/reverse/change-direction controls within the declared chemistry scope.

The first smooth taper is an initialization, not a physical claim that bending
is uniformly distributed or that both strands must move equally. A later
qualified local relaxation may redistribute roll/tilt/twist unevenly, or move
one sugar-phosphate path more than the other while maintaining pairing, stacking
and chemical geometry. Record the initial proposal and the post-refinement
movement separately; do not mistake an imposed taper for a measured conformation.

Bending and elongation must allow coupled changes in step twist/rise and in
both sugar-phosphate paths: the backbone needs room to breathe. Do not impose a
universal twist change or keep phosphate positions/radii rigid while moving base
frames. Qualify local torsions, sugar geometry, stacking, pairing and clashes
after relaxation, including the transition into fixed context. The small imposed
preview demonstrates motion only; it does not qualify this coupled relaxation.

Density-aware placement is a later capability. A cluster of negative difference
density at phosphates is a useful review signal, but does not uniquely prescribe
a displacement: occupancy/ADPs and model/map errors can contribute. Combine
signed difference features, nearby positive support, ordinary map fit and
backbone geometry. Freeze map provenance, coefficients/labels, origin, cell,
resolution and source model; no unrecorded map sharpening or origin guessing.
Use bounded local evidence and matched refinement, not repeated Rfree-guided
retuning. Phenix documents a combined map/restraint target and fragment morphing
in [real-space refinement](https://phenix-online.org/documentation/reference/real_space_refine.html);
its [map interpretation notes](https://phenix-online.org/phenixwebsite_static/mainsite/files/presentations/latest/pavel_maps.pdf)
distinguish coordinate and electron-count explanations for difference features.
Those capabilities require native qualification before integration here.

Schedule the first density feature as a **read-only S06 diagnostic**, then expose
its evidence in S07/campaign review; direct density-guided motion follows later.
Look for sustained negative difference-density patches along sugar-phosphate
paths, retaining patch extent, peak/integrated signal, affected atoms and
consecutive residues, nearby positive support and ordinary map fit. A single red
voxel or universal sigma cutoff is insufficient. Calibrate the interpretation
with the scientist against healthy/noisy and deliberately displaced controls,
accounting for resolution, map processing, spatial correlation, repeated tests
across the model and occupancy/ADP alternatives. Freeze calibration separately
from later evaluation; do not use held-out Rfree to tune detection thresholds.
Initially flag for review only, with no automatic deletion or displacement.

**W153/W155 qualification boundary:** the experimental comparison now demonstrates
why the matched no-op and scattering state matter: geometry can improve while
the reference moves and phosphate residuals persist. W155's prescribed
complex-F controls give negative modeled-P features from coordinate, occupancy
and B errors separately; nearby positive density and every atom sharing one sign
are not reliable general rules. Those known-phase, noiseless contrasts are not
ML-map or detector calibration. Keep them as counterexamples before adding a
motion trigger. Future comparisons must also declare effective work filtering:
W153 preserved raw data/Free but native filtering changed one arm's work set.
[Experimental evidence](topostitch-periodic.md#w153--separate-experimental-backbone-recovery-from-geometry-driven-relaxation)
and [counterexamples with provenance limits](topostitch-periodic.md#w155--record-density-counterexamples-before-proposing-backbone-motion).

**Next assay preparation, not implementation:** use an existing local map/model
correlation only as an additional observation, with explicit X-ray scattering,
resolution, masking radius, occupancy/ADP treatment and frame handling. Installed
Phenix **2.2.1-6174** `mmtbx.maps.map_model_cc.master_params_str` defaults to
`electron`; `run()` passes the selected table into the scattering registry.
Do not inherit that default for these X-ray data. Its `map_correlations` owner
also offers model/map offsets and B-zeroing; keep them off unless a separately
recorded comparison explicitly requires them. [Phenix's correlation documentation](https://phenix-online.org/download/documentation/phenix/prerelease/reference/map_correlations.html)
describes those modes. Native execution and backbone calibration remain open.

An omit calculation is a distinct phase/solvent experiment, not an automatic
cure for model bias. [Phenix's polder documentation](https://phenix-online.org/version_docs/dev-3297/reference/polder.html)
separates bulk-solvent exclusion from de-biasing and discourages single-atom
omissions. Any future selected-region omission needs frozen region/mask,
work/free generation and scale/phase policies through the existing native owner;
do not repurpose W155's three-scatterer contrast as a qualified omit protocol.
No correlation threshold, omit-map run or new search is queued by this note.

**Existing map owner to reuse (18 November):** Hazel's maintained
`nasolve.metal.map_diagnostics` and saved-coefficient audit provide a starting
point for exact map/source hashes, coefficient labels, cell/symmetry and work-set
membership, whole-cell sigma scaling, and periodic sampling. The private A72
comparison checks own-endpoint and common-reference positions separately;
these answer different questions and neither is independent of model phases.
Reuse that provenance/sampling boundary through a shared interface rather than
adding another map reader. Its Hg radii, sigma values and occupancy/scattering
assumptions are not phosphate calibration. The backbone detector and motion
policy remain unimplemented; this note does not advance B06 or S06.

**W140 read-only step:** the saved C400 native/full ordinary ML outputs now have
exact coefficient/model/parameter binding and four periodic map samples at 456
sugar/phosphate atoms each. This reuses A72's unchanged sampler; no second
production map reader was added. Alder's maintained capture is still MLHL-only,
so a future shared adapter must explicitly distinguish ordinary ML from that
protocol. Labels, fill/isotropization/sharpening, test membership and own/common
positions are recorded. All 176 test indices are included; these are inspection
maps, not a work-only search target. C102's persistent negative phosphate feature
coexists with improved base planes and nearly unchanged backbone deviations.
It does not uniquely prescribe motion, occupancy or ADP changes. The inherited
1.5 Å sphere is a probe, not calibrated phosphate support. No detector, motion
policy or threshold is enabled. [Measurements and checks](topostitch-periodic.md#w140--audit-backbone-response-and-saved-density).

**W141 shared implementation:** Alder now exposes bounded periodic grid sampling
through its existing `nasolve.metal.map_diagnostics` module. Both existing metal
capture adapters reuse it without changing policy or standalone worker imports.
Independent relocated-wheel replay reproduces all W140 own/common samples exactly
in both import modes. This is a sampling primitive, not a general map reader or
backbone detector. Do not introduce a Willow dependency on unmerged Alder;
reuse this owner after integration, with the ordinary ML source/policy adapter
still explicit. [Qualification and limits](topostitch-periodic.md#w141--qualify-the-shared-periodic-grid-sampler).

<a id="saved-map-inspection-boundary-w142-design-not-implemented"></a>

### Saved-map inspection boundary (W142 design; W145 selection identity delivered)

W146 delivers the first read-only inspection projection over existing owners.
Producer/frame interpretation and cross-stage rendering remain after shared
integration. It must not add another checkpoint registry,
map finder, sampling engine or native writer wrapper. The cold audit covers Cedar
`4bfffbca` and Alder `9c4c3b05`; it changes no runtime policy.

| Responsibility | Existing owner / missing proof |
| --- | --- |
| Model, observations, map bytes and ancestry | AutoRefine output references, checkpoint validation and `run_context` anchored resolution already own these. `coot_view.resolve_view_profile` exposes stage-appropriate views; its inherited-map checks retain the ancestor and unchanged observations. Reuse or extract that shared resolution boundary rather than infer paths from basenames. |
| Actual refined model | `refinement_parallelity.validate_checkpoint_execution` joins frozen inputs, native result and written-model bytes. This proves the model output, not the derivation of its map coefficients. |
| Coefficient generation | Bind exact labels, target/phase context, missing-data filling, filtering, isotropization/sharpening and work/free treatment to the producer. A saved resolved EFF is useful descriptive evidence; ordinary output hashes and the input `autorefine.params` do not by themselves witness every resolved native map option. Missing producer evidence stays explicit for legacy inspection. |
| Coordinates and frame | Record the map-producing model separately from the inspected descendant and common-reference model. Require exact atom/image correspondence, cell/space-group setting and origin evidence. Reader representation differences need an explicit bridge; never broaden the compiled pair-recipe tolerance or silently regenerate symmetry images. |
| Grid measurements | Reuse Alder's qualified `sample_grid` after integration. Caller-owned radius, spacing, normalization and own/common positions remain recorded. Metal radii and sigma values are not backbone calibration. |

Keep **artifact integrity**, **generation evidence**, **frame compatibility** and
**permitted scientific use** separate. An inherited or partly documented map can
remain useful to a crystallographer without being called a newly calculated map
for the child, an independent validation map or an automatic-motion objective.
The existing viewer must retain its current compatibility; this design adds no
new refusal to that viewer and no retroactive authority to old runs.

The installed Phenix **2.2.1-6174** source makes the work/free distinction concrete:
`mmtbx.map_tools.electron_density_map.map_coefficients` builds the map helper and
combined coefficients before `exclude_free_r_reflections` masks rows.
`f_model.manager.map_calculation_helper` passes Free-R flags to
`maxlik.alpha_beta_est_manager`, which selects true-flag observations when they
exist. Thus an output with no test rows does not establish that its upstream
weights avoided test amplitudes. This is a source-path audit, not a dynamic trace
of historical map generation. Preserve ordinary inspection maps; qualify the
whole declared generation procedure before claiming a work-only search objective.
Do not equate such an objective with independent validation of model phases.

The C400 frame example is also reader-specific: Gemmi reports identical PDB/MTZ
cells; the saved CCTBX readings differ by at most **2.93×10⁻⁶ Å** and agree at
float32 precision. The first audit incorrectly expected Gemmi to expose that
difference and failed; the corrected receipt retains both readers and the failed
assumption. This is not evidence for a universal cell tolerance. Cropped maps,
changed origins and Pine image/ASU transformations need their own explicit mapping.

W144 now exercises those existing owners on a genuine ordinary counted child:
its written model and numerical map contents match the full diagnostic, inherited
maps retain their labels, and changed observations/substituted maps refuse after
relocation. Existing viewing permits a changed-cell model, so the adapter must
report frame conflicts independently without changing legacy viewing behavior.

A separate W144 R3 probe measures up to 0.28σ variation between equivalent image
queries from eight-point interpolation; direct Fourier values agree. Composing
the existing complete `ReferenceFrame` inverse mapping and shared sampler keeps
16,416 source-frame comparisons consistent to 6.75×10⁻¹⁴σ. Use declared source/image
correspondence rather than treating tiny image-space score changes as physical
support. This does not remove absolute interpolation error, prove an undeclared
origin or define a new sampling/noise policy. The existing native/metal sampler
and its defaults are unchanged.

W145 delivers the first selection-identity slice through `ViewProfile.map_origin`:
map stage, associated refinement checkpoint and ordered consuming checkpoints.
It reuses existing resolution and keeps legacy Coot behavior unchanged, including
maps whose ancestor model is absent. Standalone full/installed gates pass; the
Cedar adaptation is focused-qualified and awaits the combined gate. This is map
navigation provenance, not proof of generating XYZ/ADPs. W146 now binds displayed
artifacts in a measured snapshot, rechecks them and retains generation/frame
evidence as unassessed. Its standalone full/installed and external-consumer checks
pass; it is not part of the frozen combined W145 integration candidate.

W147 exposes the native preview's exact complex-array selector and descriptive
headers through a shared dependency-free helper. Source/installed native checks
and saved-preview parity pass. The separate worker adapter hashes captured helper
source bytes rather than a later file read; it awaits integration. Header equality
still does not prove a common origin or coefficient-generation procedure.

The further inspection projection should only report validated source/ancestor identity,
generation evidence or its absence, frame correspondence and descriptive samples.
Its distinct regressions should cover substituted bytes/labels, inherited maps,
unproven frames and relocation through declared anchors. Existing W141 arithmetic
tests need not be duplicated. Healthy/noisy/displaced calibration, sustained
backbone-patch detection and any motion policy follow separately. No new native
fit, coefficient generation, threshold, force or selection is scheduled here.


Small Rwork/Rfree and clashscore fluctuations are descriptive context, not
standalone rejection thresholds. Judge local physical improvement, global fit,
uncertainty and numerical stopping separately; do not convert an optimizer error
into an assertion that every resulting coordinate is physically wrong.

Before using density as a search objective, bind its generation policy as well
as its bytes: work/free reflection treatment, missing-data filling, filtering,
isotropization and sharpening. Ordinary display-map columns need not be work-only;
C391's existing output includes finite coefficients at test indices and a filled
2mFo-DFc column. Coefficient membership alone does not prove which observed
amplitudes contributed, so inspect that derivation separately. This does not
invalidate ordinary inspection maps or change the current output. Hazel's private
work-only, unfilled map policy is an explicit example, not an inherited default
for all NASolve maps or independent validation of the resulting model.

The later search must vary **where curvature sits**, not only the end transform:
seed a bend using local density support, then consider bounded localized,
distributed, distally shifted or staged curvature profiles. A sharper bend may
be the data-supported answer; smoothness is a regularizer, not ground truth.
Assess support before seeding and after matched refinement, protect supported
regions, preserve weak-support uncertainty and keep junction/routing boundaries
explicit. Reuse existing windows and exact masks rather than starting another
backbone editor. Freeze candidate/iteration budgets, retain all attempted
variants and use working-set evidence for search. Reserve the unchanged Free-R
set for a small declared validation comparison to limit selection bias.

A proposed control is construct **4T28**, whose PDB entry is
[8SJW](https://www.rcsb.org/structure/8SJW) (7.64 Å). Simon reports a localized
bend around chain B residue 11 that was chosen from density. Entry identity and
resolution are verified; the exact residue/frame mapping and that density
interpretation still need inspection. Compare localized and redistributed
curvature without treating the deposited shape or greater smoothness as an
automatic winner. The detector, density-driven bend placement and this benchmark
remain planned work, not implemented features.


Junctions are hard boundaries for automatic extension and topology changes.
Initially hold junction coordinates fixed. A later explicit hinge capability
may allow coordinated arm bending without changing strand routing or tearing
connected parts apart. Do not freeze every junction angle as a general physical
law; 7R96 is a useful bent-junction architectural control.

Canonical-first reconstruction is a development strategy, not authority to
replace modified chemistry in an accepted result. Where supported, restore
modifications and repeat chemistry/geometry checks before scientific acceptance.
Backbone, sugar or pairing changes may invalidate a canonical surrogate entirely.
Cedar can supply supported construction/chemistry capabilities after interface
qualification; its mutation path is not assumed to be an arbitrary frame-fitting
or closure solver. NARestraints supplies reviewed inter-residue targets, not
independent proof that an inferred connection is correct.

## Evaluation: contacts and diffraction must both be considered

When the scientist explicitly declares that ends must meet, that intended
sequence/connectivity drives the repair search. Preserve its source and distinguish
it from inferred partners, registers or symmetry images. Better Rwork/Rfree is a
useful expectation, not a necessary monotonic outcome: a structurally faithful
connection can be acceptable despite some worsening after recovery. The user's
project gate is 0.30, applied to named post-recovery statistics with structural
and map review; it is not standalone proof of a correct or complete model.

### Post-deformation recovery window (W156 planning)

A raw deformation can initially give poor Rwork/Rfree because the backbone,
local contacts and scattering model have not relaxed. **Do not reject a proposed
placement solely for its initial or early-cycle Rfree.** This is the user's
19 November crystallographic clarification, not a promise that every placement
will recover. Optional NASolve smoothing may reduce that initial penalty; it
does not replace restraint-driven Phenix recovery or final evidence.

Keep four states distinct: the parent, raw deformation, optional locally smoothed
proposal and post-Phenix recovery checkpoints. Before evaluation, declare the
restraint protocol, staged cycle/iteration budget and continuation/stopping rules
for candidate and matched no-repair control. Allow non-monotonic early Rfree;
report the trajectory and endpoint rather than selecting the lowest cycle.
Judge recovered contacts, geometry, density and R statistics after the declared
recovery window, not from the raw proposal. Numerical/chemical failure remains
separate from a temporary R penalty.

If the budget ends while the model is still settling, record **recovery unresolved
within budget**, not irrecoverable placement or convergence. Any further bounded
continuation retains the parent and all prior attempts; do not tune parameters
or keep extending solely until the same Free-R set looks favorable. W153's fixed
five-cycle result is a mixed post-budget observation, not a test of initial-Rfree
rejection or proof that later recovery is impossible. This is a planning gate;
no current refinement thresholds, runtime schema or automatic continuation change.

**Post-recovery review (W156 user clarification):**

- Rwork at or below 0.30 can meet the stated project fit gate when required
  sequence, connectivity, molecular content and defensible geometry survive.
  A lower residual cannot compensate for deleted atoms or lost structural intent.
- Worse final Rfree triggers careful map review even when it remains below 0.30.
  Compare both the starting model and the matched refined no-repair control;
  expose actual movement against a fixed map and each model's own maps. Meeting
  a numerical gate does not silently approve the candidate.
- Rwork or Rfree above 0.30 after recovery triggers explicit structural diagnosis:
  missing/misplaced junctions or connections, wrong register, bulges, sequence
  assignment, triangle orientation and phosphate completeness/placement. Carry
  the finding into a bounded alternative bend or structural hypothesis, not
  repeated identical cycles. Sequence/topology revisions remain explicit proposals
  checked against construct intent; do not silently change the intended molecule.
- Keep non-structural explanations in the diagnostic differential. The
  [Phenix refinement FAQ](https://phenix-online.org/documentation/faqs/refine.html)
  notes that high R values can persist with effects such as twinning or
  translational NCS. The project threshold routes review; it cannot uniquely
  identify a missing feature. No runtime gate is changed by this planning note.

Freeze the parent and preserve a no-repair control. Compare repaired-plus-refined
and unmodified-plus-equivalently-refined siblings using the same original
observations, Free-R flags, phase policy, cycle/strategy budget and unrelated
restraints. The repair-specific restraints are an explicit difference, with
their strength and persistence recorded. If a suitable matched control does
not exist, run one within the declared trial budget rather than attribute an
extra round of refinement to the repair. Keep atom count, chemistry, occupancy
and parameter-count changes visible; missing-residue addition is a separate
comparison from moving an equal-atom model.

Report parent/control/candidate Rwork and Rfree and their absolute deltas,
local map support when available, intended pairing/stacking realization,
bond/angle/torsion/sugar geometry, periodic clashes, unintended displacement,
protected-contact preservation and native interpretation. Smaller is better
for R values, but tiny changes or sparse/noisy Free-R do not establish a win.
Numerical meaningful-change thresholds remain a benchmark decision, not invented
constants. A lower Rwork with worse Rfree is not an automatic improvement.

Contact improvement measures the named intended contacts, not total contact
count. Good contacts elsewhere must survive. Contacts created by construction
or restraints are achieved geometry, not new independent evidence for the
hypothesis. Refinement with restraints can preserve a wrong assignment. Validate
with recipient diffraction/map evidence and known-answer benchmarks; a separately
budgeted release/relaxation diagnostic may be useful after native qualification.

Generate/order the bounded trial set using design and geometry before consulting
candidate Rfree. Do not repeatedly retune frames, weights or donors against the
same Free-R set. Failure, ambiguity and no-op are legitimate outcomes. Keep
connection evidence, geometric feasibility, diffraction outcome, numerical
readiness and human approval as separate dimensions, not one confidence score.

Phenix's documented nucleic-acid secondary-structure restraints are not
symmetry-aware. Custom symmetry bond edits do not by themselves establish full
angle/plane/nonbonded correctness. A future native capability gate must verify
exact effective restraints and symmetry behavior for the actual Phenix/Coot
versions. Unsupported enforcement leaves a candidate for review, not a claimed
automatic repair. No native tool execution is claimed by this design.

### Next discriminating experiments (W158 planning)

**W159 execution update:** the matched ordinary-recipe diagnostic is complete
and leaves the reference baseline unresolved; opposite-start expansion is paused.
Because the deposited diagnostic has no legitimate ordinary PostMR root, the
existing recipe/command and native execution owners were used directly, with
Rowan's ownership review. No ancestry was fabricated. Complete ordinary checkpoint
qualification remains open. [Results and exact limits](topostitch-periodic.md#w159--compare-ordinary-recovery-with-the-fixed-unit-baseline).
The independent model-assisted density panel below remains planned.

The next scientific question is whether W153's experimental reference drift is
specific to its fixed-unit XYZ recovery protocol. This is not evidence that a
larger bend is impossible. Keep the completed W148/W152 controls, W153 common-HKL
rescore, W157 stage audit and C397–C400 derivative/restart work closed; none needs
repeating merely to establish the next baseline.

**First: one matched, undeformed protocol comparison (S05/S06).** Start from the
same deposited 5W6W coordinates and scattering state used in W153, with the same
original observations/Free flags, intended pair/stack definitions and phase
policy. Compare the recorded fixed-unit protocol with one prospectively frozen
ordinary recovery recipe, through Cedar's existing `execute_autorefine` owner.
Rowan identifies C403's five-cycle, one-process route and W134's canonical
continuation as precedents, not a qualified same-source comparator. Choose the
mean/anomalous mode from the actual data; do not copy a metal recipe's mode.

Before execution, qualify the ordinary parent and actual restraint readback.
Never strip counted ancestry to bypass admission: use a legitimate common upstream
state or a qualified handoff. Record every protocol difference, including real-space
steps, weights, group ADPs, eligible occupancies and scale updates. Audit whether
any native weight selection consults Free reflections and disclose that use;
do not treat reused Free data as an independent selection test. A multi-option
ordinary recipe is a **protocol contrast**, not a pure weight or ADP experiment.
Freeze exact native/version/source pins, five-cycle budget and any bounded
continuation rule before reading new results. Reuse W153's saved control only
if complete input and protocol identity permits the comparison; otherwise one
matched control is required, with the changed context explained.

Retain exact effective reflection membership, not just totals. Prefer an explicitly
qualified common fixed-work policy for a trajectory comparison; if native filtering
remains adaptive, label that limitation and compare endpoint common-HKL arithmetic
separately. Report stage-labelled scaling/XYZ histories, actual iteration stops,
geometry and pair/stack residuals, molecular content, fixed-frame motion and own-map
versus fixed-control-map views. Use W156's post-recovery review. If the reference
still drifts with unresolved map support, inspect the named changed terms and
scattering context before adding another displacement matrix. If the ordinary
baseline is defensible, extend that frozen recipe to the existing opposite starts
with a matched control; this qualifies recovery under that recipe, not general
sticky-end repair. A capped/failed/unsettled trial is a legitimate outcome.

**Second, independently bounded: model-assisted density counterexamples (S06).**
Reuse W155's zero, prescribed displacement and B-mismatch hypotheses and exact atom
inventory as a proposed first three-case panel. Through the maintained native map
owner, freeze one common truth-derived amplitude set and separately declared model
states, X-ray scattering, scale/phase policy, resolution, coefficient membership,
mask and sampling positions. The zero case means no intentional model error;
model-assisted coefficients need not give an algebraically zero difference map.
Test the map-generation interface before creating a new panel. This extends the noiseless known-phase counterexamples to a declared
model-assisted map protocol; it is not a phase-only intervention or experimental
calibration. Keep model-dependent phases and per-map sigma visible, with fixed-map
cross-sampling distinguished from own-model sampling. Preserve zero/false-positive
outcomes. No fitted detector threshold, coordinate proposal, or inference that
W153's B2 feature has a particular cause follows. Noisy controls and scientist
calibration come afterward; do not add a new map reader.

The W158 text records the pre-execution plan; W159 above supplies its diagnostic
result and owner limitation. The protocol comparison is no longer an unexecuted
recovery task; the map panel can proceed independently once its
owner is qualified and does not block geometry-only benchmarks. Reciprocal target
shapes, larger/nonuniform bends and junction-limited window expansion remain the
existing S04 queue. W150 receiving integration, B09 geotest and B10 explicit sticky
activation remain separately open. No acceptance threshold, chemistry, production
policy or runtime schema changes here.

## Campaign-local memory and transfer

Campaign memory is useful even with an excellent finder: it retains design
intent, expensive search outcomes, ambiguity, negative results and provenance.
It is a cache of hypotheses and evidence, not a new source of experimental truth.

Save an abstract logical scheme separately from each dataset's embedding.
Transfer end/domain roles, strand orientation, pairing register, edge types,
protected nicks and applicability conditions. Never blindly transfer chain
letters, residue numbers, symmetry-operator indices, cell translations or
coordinates. Recipients independently map the scheme and resolve their actual
space-group realization, even when donor and recipient have the same group.

Authorize reuse within explicitly related design/family members. Validate
sequence and register, arm length changes, junction routing, copy number,
chemistry/chirality and coverage. Unknown mappings remain unknown; membership
in the same campaign or a similar filename is insufficient. A scheme can be
partially applicable, but do not silently treat an incomplete assignment as
complete. Contradictory donors remain alternatives instead of a majority vote.

Before each recipient attempt, freeze the selected scheme version/hash, donor
checkpoint and model/evidence hashes, ancestry, applicability facts, local
mapping, alternatives and policy. Changing the library creates a new attempt
input, never an in-place change to a frozen campaign plan or completed receipt.
Use deterministic passes: local scans first, freeze a campaign scheme snapshot,
then a bounded transfer pass. Later feedback is another explicit version/pass,
not scheduling-dependent hidden learning. A successful recipient may propose a
new scheme version but cannot erase its inherited hypothesis ancestry.

Tentative schemes may be tried under the opt-in policy without per-member
approval. Store observed contacts, inferred hypotheses, geometry/refinement
results and user decisions separately. Descendants of one MR model or one
transferred scheme are correlated evidence, not independent confirmations.
Prevent A-to-B-to-A reinforcement; preserve independent evidence roots and
include failed/rejected trials. A rejection can mean wrong partner, incompatible
recipient, or insufficient geometry support: keep its reason and scope rather
than blacklisting the entire family automatically.

Campaign-local reuse does not silently promote a global reviewed recipe.
Explicit promotion must declare applicability, invariants and reviewed evidence,
as required by the existing registration contract. User approval of one model
is not approval of every future realization of its connection scheme.

## Campaign execution and review

Proposed first hook: after an ordinary usable initial refinement, scan for
connection issues even if numerical SOLVED was reached. If enabled, perform a
bounded TopoStitch branch followed by a short ordinary audited AutoRefine child.
Future explicit invocation after registration/PostMR may be supported once
validated. Do not make this depend solely on Refine Doctor failure: global
R-factor gates can miss a disconnected arm. Prevent TopoStitch/Doctor retry loops
with frozen stage order and per-source attempt budgets.

The coordinator must own these stages and their receipts. Do not launch an
out-of-band mutation against a completed campaign run. The core candidate engine
must not let ordinary AutoRefine's success auto-selection leak through: it needs
a tested preserve-current trial adapter, followed by a separate policy-owned
selection action. Do not assume such an adapter already exists for TopoStitch.

Proposed outcome reasons include already connected, no eligible ends, ambiguous
partner/register, incompatible scheme, geometry infeasible within budget,
unsupported native enforcement, refinement failed, improved candidate and
tradeoff requiring review. Preserve original usable results and continue other
campaign members. Transient execution errors do not become scientific rejection
of the hypothesized topology.

In the chosen **Campaign desk**, show a compact connection-review item:

- proposed end pairing and whether locally inferred or borrowed;
- why it was proposed, with unresolved alternatives;
- what moved/rebuilt and the actual symmetry mate;
- contact/geometry changes plus matched Rwork/Rfree deltas;
- before/after view, Open in Coot, Keep original, Use candidate, or Reject pairing.

Group repeated issues for review, but apply a batch decision only to its explicitly
selected compatible scope. Distinguish rejecting an intended connection from
rejecting one attempted geometry. Show provisional/unreviewed status plainly;
keep low-level provenance available on expansion rather than in the main flow.
No renderer or GUI implementation is selected here.

### Density presentation: local chemistry and continuous backbones (W143)

The scientist prefers Hazel's restrained contour presentation for individual
residues and metal sites. Preserve that view: chemically oriented molecular
drawings, thin ordinary/signed-difference contours and explicit out-of-plane
offsets make those local questions legible. An endpoint-following chemical plane
is not a shared spatial slice; its limitation must stay visible.

Backbones need a complementary **rotatable continuous 3D path**. Keep actual
sugar/phosphate atoms and native bonds solid and depth-tested. Show genuine
isodensity contours as sparse section bands and surface silhouettes, with an
optional faint shell. The architectural/pencil-like feel comes from restrained
colour, line weight and opacity, never random jitter, invented lines or a
smoothed/fabricated density signal. A density-only front cutaway can expose the
chain without drawing an occluded atom falsely on top of a nearer solid object.

Keep the camera, crystal frame and crop fixed when switching source and candidate
models. Permit a map to stay fixed while comparing coordinates, with that
reference-map choice explicit; a matched-map view answers a different question.
Report true-scale displacement. Do not invent movement to make a small effect
visible, or present a graphical interpolation as a refined intermediate model.
Both contour levels and clipping are display choices, not detection thresholds.

The local W143 prototype uses the existing C400 maps, 30 sugar/phosphate atoms and
32 recorded native bonds in C101–C103. CCTBX produces the real display surfaces;
no fitting or new coefficients are involved. Its compact self-contained view
offers rotation, fixed-frame model/map switching, contour-sketch/soft-shell modes
and density-only clipping. The user confirmed that v1 rotates and looks nice.
The user reviewed v2, preferred Slate, liked the off-atom residual fade and
requested stronger contours. The final v3 study defaults to Slate, increases
Paper's pen contrast and strengthens red/green on Slate. Soft directional model
lighting stays subtle. A small contour-target dropdown chooses difference density
(both signs together) or ordinary 2mFo−DFc, remembering independent levels. The
slider offers 0.5σ steps through 6σ: difference starts at ±3.5σ (minimum 1.5σ),
ordinary starts at +1σ (minimum 1σ). A quiet contrast control under View options
scales contour opacity without changing levels, surfaces or coordinates.
An optional fade preserves full signed-contour opacity within 1.5 Å of displayed
atoms, reducing smoothly to 15% beyond 3.5 Å. Vertex distances are interpolated
across triangles and follow the displayed model. No surface is deleted and no
feature is classified as noise; turn the fade off to inspect the full crop.
Lowering σ reveals more residual density, so contour sensitivity and spatial
emphasis remain separate controls. The GPU-buffer cache is bounded to three
contour/map choices; no continual animation is needed.

Source/mesh checks and 16 offline control contracts pass, including all 21
ordinary/difference level choices, independent remembered values and contrast.
The latter use mock WebGL and do not establish shader compilation, GPU appearance
or browser layout. The user subsequently approved v3's appearance and explicitly
requested reuse as the shared NASolve inspector throughout the workflow, without
opening Coot for routine inspection. This human visual approval is recorded
separately from automated coverage; broad stage integration is still planned. Browser URL policy blocked automated
local-file inspection; no alternative route was attempted.

This is S07's approved shared-inspector direction, with a local prototype rather
than a deployed general GUI/schema. Preserve Hazel's residue/metal view. Share
the native map-display boundary with Alder and the existing TopoStitch viewer;
reuse the component across MR/PostMR/AutoSol, refinement/Doctor, Pine proposals
and campaign comparisons through the [shared architecture contract](architecture.md#shared-in-app-modeldensity-inspector).
Do not promote a parallel map reader, mesh pipeline or checkpoint history. Campaign desk should focus the same
declared chain window/image and expose original, proposed and refined states
without changing scientific selection. No automatic backbone correction follows.

## Proposed records, not deployed schemas

Future records should include a connection proposal, logical scheme, recipient
realization, repair trial, comparison and review decision. Each needs a version,
stable ID, declared authority, source checksums and policy/algorithm provenance.
Endpoint identities need logical strand/domain/site, coordinate model/chain/
residue/insertion/alternate and explicit image transform. Evidence references
must distinguish pre-repair observations from derived geometry and shared ancestry.

Use existing run/dataset/campaign anchors plus relative paths and checksums;
absolute paths may be provenance only. Preserve existing checkpoint lineage,
immutable numbered runs, observations, Free-R and old schema behavior. New
runtime schemas and migration/version gates require a later implementation
review; this intent JSON must never be loaded as an authorization manifest.

## Implementation sequence and benchmark gates

The [audited completion roadmap](topostitch-roadmap.md) is the single current
work queue for sticky-end repair and Pine ASU slicing. Its machine-readable
ledger records dependencies, delivered scope, closure criteria, evidence and
next actions; update it at each substantial checkpoint. The benchmark obligations
below and Pine's live-check bank are acceptance resources, not separate queues.

Essential tests include healthy no-op controls; perturbed known structures;
known-length missing intervals; wrong register and twist; nearest wrong partner;
repeated complementary ends with multiple solutions; intentionally free ends;
true nicks versus representation seams; valid periodic self-edges/winding;
non-orthogonal cells and screw operations; changed space group/ASU/arm length;
protected junctions; chemistry/alternate ambiguity; and impossible closures.

For campaign tests include correlated MR donors, contradictory schemes,
rejected proposals, deterministic order/resume, drifted checksums, moved storage,
user veto, stale model-bound review, finite budgets and preserved Free-R.
Partition geometry calibration and held-out validation by structure/design family,
not random residues of the same crystal. 7R96 is an architectural bending control,
not a high-resolution source of local torsion targets. No live-test-specific
chain labels, distances or symmetry operators are baked into the algorithm.

The user proposes 8D93 as a starting model for a hexagonal recipient dataset
(to be supplied). Keep that diffraction benchmark separate from the current
public 8D93 coordinate-only smoke test. Freeze the recipient's actual space-group
setting, cell, observations, Free-R flags and maps when available; do not transfer
8D93 symmetry or assume that a successful file transformation is data-supported
repair. Compare initial placement and post-stitch refinement to reveal where
curvature and strand-specific backbone adjustment are actually supported.

Before adding coordinate-based pairing discovery, inspect NARestraints' existing
base-pair inference for damaged MR models. The reviewed `restraints.guesser`
seeds geometric candidates, builds antiparallel runs and iteratively rescues
weaker edge pairs. Current traversal uses chain labels/integer residue adjacency,
and greedy selection does not preserve every competing alternative. Reuse that
candidate/recovery evidence through logical route mapping rather than treating
the selected output as a complete topology inventory. Preserve ambiguity and original evidence;
do not treat a guessed pair inventory as complete chemical routing or automatic
permission to join sticky ends.

Later behavior patches require meaningful failing-before/passing-after regression
tests and focused checks with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`; run the
complete suite when shared/global mechanics change. Retain clean-install
checks, relocation tests for artifact changes, and exact native tool versions
with dry-run versus full-execution receipts. Known-answer scientific recovery
and human inspection are separate from unit-test success.

### Final geotest alignment gate (planned)

The user-requested end-to-end gate is the altered-arm family from the local
`geotest-fullauto-fqce98w3` campaign: X11_18 (18/21/21 bp arms, **P4_3** as
requested), X11_22 (22/21/21), and additional members selected when the panel is
inventoried. These are benchmark labels, not operational file references.
Before execution, freeze the exact members, sequence/chain correspondence,
observations, Free-R flags, source checkpoints, cell/setting and intended
symmetry-partner connections in checksummed run/dataset-anchored receipts.
Do not infer other members' space groups from X11_18 or search by basename.

Read-only inventory on 2026-11-16 binds nine historical members and the two
named seeds through their existing receipts/checkpoint registries; all 204
recorded hash/size comparisons pass. X11_18 means **dataset2, P4_3,
refine-002**, whose recorded state remains REVIEW and whose current checkpoint
is still `postmr`. Its original observation MTZ is labelled P4_1: audit the exact
model/data/setting lineage before execution, without relabelling observations
or selecting this seed implicitly. X11_22's bound seed is `refine-001`.
Independent sequence agreement and residue-to-arm/partner mapping remain
unverified; the other panel members have not been selected. Raw HKL/Free-R
column hashes are recorded, but do not establish a complete changed-setting or
refinement Free-R audit. No new native run, coordinate edit or adoption occurred.

The local receipt lives at the ordinary NASolve repository anchor,
`branch-artifacts/willow/geotest-inventory-2026-11-16/inventory.json`, SHA256
`82a1ba1cd70bbf587b2c2c96b1a75bf8b03514082bac9fa6ce283daa3f9b9f02`.
It carries campaign/member/run anchors, historical root provenance, model/map/
observation/parameter hashes and Gemmi 0.7.5 readback. Private coordinates,
reflections, sequences and historical statistics stay local; this receipt is
an inventory, not a portable autonomous campaign or a scientific acceptance.

Pass only when the intended altered-arm sticky ends align in their exact
periodic images with correct register, pairing/stacking and qualified local
backbone geometry, while junctions and already aligned 21-bp arms remain sound.
Allow coupled bending, extension/compression, twist and strand-specific backbone
relaxation within declared editable windows. Check the seam, surrounding packing
and window boundaries; visual proximity or a representation-only recut is not
closure. Preserve nicks and chemical intent; no unsupported symmetry bond is
introduced just to make a display look connected.

The connection must survive a matched refinement comparison with unchanged
observations/Free-R, budget and unrelated restraints, supported by maps and
reported Rwork/Rfree alongside geometry and contacts. Predeclare trial budgets
and acceptance criteria; retain ambiguous/failed cases and tradeoffs. Lower R
values alone do not establish the right connection, and repeated Rfree-driven
tuning cannot substitute for validation. Show source, proposed and refined
coordinates with the connected mates for human review. This is final B09
acceptance evidence after S04-S07, not an immediate rerun or a structure-specific
algorithm. Independent families and healthy/wrong-partner controls remain required.

## References and design limits

- [3DNA](https://doi.org/10.1093/NAR/GKG680): base-pair frames/step parameters and
  reconstruction; backbone feasibility still requires atomistic checks.
- [emDNA](https://pmc.ncbi.nlm.nih.gov/articles/PMC9177622/): precedent for
  constrained base-pair-step optimization; no dependency selected here.
- [7R96](https://www.rcsb.org/structure/7R96): reported crossover bending;
  5.68-A data require care when interpreting local geometry.
- [Phenix secondary-structure documentation](https://phenix-online.org/documentation/reference/secondary_structure.html):
  nucleic-acid restraint symmetry limitations and explicit-edit mechanism.
- [Campaign full-auto](campaign-full-auto.md), [campaign model roadmap](campaign-model-roadmap.md)
  and [GUI contract](gui.md): existing ownership, provisional selection and
  future transfer/workbench boundaries.

These sources establish useful methods and limitations; they do not validate
TopoStitch. Search ranges, objective weights, meaningful improvement thresholds,
exact serialization, native restraint strategy and construction APIs remain
open benchmark/interface decisions. Current Campaign Doctor has read-only donor
facts, not the automatic scheme-transfer engine proposed here.

## Planning handoff and validation receipt

Before: recut/Topo workbench and bounded surgery were described separately, with
tentative repair names and no specified campaign sticky-end inference policy.
After: this document and `topostitch-intent.json` record a unified proposed tool,
explicit inference/transfer authority and a benchmark plan. Runtime behavior is
unchanged. Existing documents linked here are `docs/README.md`,
`docs/development-handoff.md`, `docs/construct-registration.md` and
`docs/campaign-full-auto.md`; `CHANGELOG.md` records the planning addition.

Validation in the Willow checkout on 2026-11-13:

- `git diff --check` — passed.
- `python3 -m json.tool docs/topostitch-intent.json > /dev/null` — passed.
- An ephemeral read-only Python check parsed the intent, asserted planning-only
  authority, and resolved 58 local Markdown links across the five edited/added
  contract/index/handoff documents — passed.
- A second-agent read-only design review checked inference, transfer and
  geometry/refinement reasoning; the recut scattering-invariance guard above
  incorporates its substantive correction.

No regression test was added and no runtime suite or native scientific tool was
run: this patch changes documentation only. No code, runtime artifact schema,
installation, dependency, compatibility or migration change is included. No
generated coordinates, maps, diffraction data or local workspace state are
included. Remaining work is the staged implementation and benchmark/native
qualification above; no TopoStitch scientific success is claimed.
