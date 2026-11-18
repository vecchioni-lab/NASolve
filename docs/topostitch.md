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

The review UI should show which contacts/images and restraint families were
requested, which actually ran, and the result or refusal. Retain the request
through fresh checked parent rebinding and manual/Doctor ancestry. Off-path
compatibility, installability, cold read/relocation, failure retention and matching
native scope must pass before the option is advertised. This plans an S05/S06
application; it closes no repair, inference, stacking or covalent-closure gate.

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

Final-state capture is a separate qualification gate. The existing native writer
runs while the counted contribution owner is active; the callback-free observer
must not bypass that owner. The proposed read is after the counted owner closes,
using the same returned model, exact force sites and frozen provider selection,
with hierarchy **and** scattering digests joined to the completed writer. Never
reinterpret a rounded PDB or treat a preflight summary as final geometry. Complete
recipe attribution also calls the outer parallelity observer; those descriptive
calls must remain distinct from optimizer/count-owner activity. New native helper
behavior needs its own qualified policy while old v5/v6 bytes stay frozen. This
paragraph is a planning boundary, not an implemented capture route.

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

The user's central prediction is that a correct repair should generally improve
both **Rwork and Rfree**, as well as the intended contacts. Treat this as a
measurable expectation, not a guaranteed outcome or permission to search until
Rfree falls. Favor coherent improvements; a geometry-only improvement with
worse diffraction agreement remains a visible tradeoff for review.

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
