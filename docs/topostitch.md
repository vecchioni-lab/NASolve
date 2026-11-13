# TopoStitch: periodic DNA connections, recutting and repair

Status: **BOUNDED_BEND_PREVIEW_IMPLEMENTED**, 2026-11-13. Branch:
`willow`, based on Pine `d7913dd`. The full design below remains future work.
The [first backend slice](topostitch-backend.md) screens explicitly supplied
canonical DNA overhangs; the [coordinate adapter](topostitch-coordinates.md)
verifies PDB bytes and derives sequences/descriptive end frames from explicit
site assignments. The [periodic inspector](topostitch-periodic.md) now searches explicit end
images and prints review-only reports; optional contact inspection measures
canonical recipe distances/angles in those images. Logical end mapping and
bounded discovery within declared strand/core-pair topology are available through
the inspector. An [explicit bend preview](topostitch-preview.md) now writes a new
checksum-bound candidate with fixed anchors and ANISOU preservation. Automatic
placement, atomistic closure, reconstruction and refinement remain future work. [Machine-readable intent](topostitch-intent.json)
is development metadata, not runtime authorization.

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

The first smooth taper is an initialization, not a physical claim that bending
is uniformly distributed or that both strands must move equally. A later
qualified local relaxation may redistribute roll/tilt/twist unevenly, or move
one sugar-phosphate path more than the other while maintaining pairing, stacking
and chemical geometry. Record the initial proposal and the post-refinement
movement separately; do not mistake an imposed taper for a measured conformation.

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

1. Read-only end/contact finder and explicit proposal record. Validate invariance
   under chain renaming, residue numbering, equivalent ASU cuts and coordinates
   outside the reference cell. Verify no edits or pointer changes. Recut-only
   fixtures must preserve orbit inventory and calculated structure factors.
2. One explicitly chosen connection: small bend, atomic checks, matched control
   and refinement child. Canonical DNA first, with qualified symmetry handling.
3. Adaptive windows and optional rebuilding; junction hinge remains a separate
   capability. Benchmark geometry/reachability and stop cleanly when impossible.
4. Opt-in campaign trials and review receipts, then logical-scheme transfer.
   Transfer can initially be read-only before it drives a construction attempt.
5. Human-reviewed reusable recipes and broader chemistry/topology only after
   known-answer and held-out validation. Preserve installability after every
   substantial implementation patch.

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
base-pair inference for damaged MR models. Reuse its demonstrated candidate and
recovery logic where appropriate, preserving ambiguity and original evidence;
do not treat a guessed pair inventory as complete chemical routing or automatic
permission to join sticky ends.

Later behavior patches require meaningful failing-before/passing-after regression
tests and focused checks with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`; run the
complete suite when shared/global mechanics change. Retain clean-install
checks, relocation tests for artifact changes, and exact native tool versions
with dry-run versus full-execution receipts. Known-answer scientific recovery
and human inspection are separate from unit-test success.

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
