# TopoStitch: periodic DNA connections, recutting and repair

Current scope, **2026-11-20**: explicit placement proposals and source-bound
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


## Output sequence and fragment policy gate (W260)

**Planning, not an available export mode.** Reuse the four layers in
[construct registration](construct-registration.md#tile-design-periodic-object-and-asu-are-distinct-layers):
input oligos, tile hypothesis, periodic graph and ASU serialization. W259 covers
original entity/asym/sequence declarations; W260 compares their original text.
Neither turns a displayed path into a new synthesized molecule.

The real both-route controls have eight visible paths from four original asym
labels. One path joins original A16/entity 1 to D1/entity 4; another wraps B17 to
B1 in entity 2. Original A and B each occupy three paths, and D occupies two.
The source explicitly describes A+D as parts of one 31-nt strand and B as a 17-nt
repeat of a linear 51-nt strand with a symmetry-averaged nick. These supplied
semantics must survive; their physical interpretation is not re-inferred from
short local sequences. No new coordinates were generated for this audit.

The W249 diagnostic's entity-per-path labels, default `nstd_linkage=no` and
canonical-string indexing were local experimental conveniences, not a production
contract. A production plan must separately bind:

- original atom/site labels and chemical component identities;
- original deposited entities/asym elements and declared but unmodeled positions;
- reviewed logical strand/copy/repeat assignments, retaining unknown nick phase;
- proposed visible paths and candidate output fragment labels; and
- every affected annotation/reference and its explicit symmetry frame.

Do not duplicate the full original sequence into each fragment, discard absent
positions to make a shorter sequence, infer free termini from a new chain start,
or turn a geometric cut into a new chemical entity without an explicit supported
fragment policy. The [mmCIF linkage flag](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_entity_poly.nstd_linkage.html)
concerns link chemistry, not whether the representative crosses a cell boundary.
Rowan supports a scoped internal ASU-fragment preview only with residue-by-residue
original oligo/copy/position binding and separate A16→D1 and B17→B1 boundary
records. Its deposition entity representation remains an explicit decision gate.
The current API does not implement that output mode.

**Next bounded gate:** build a read-only proposed-declaration/reference plan before
any writer. Keep author numbering distinct from sequence positions; inventory
source categories whose identity or frame could change (including assemblies,
NCS/TLS, geometry and unobserved-site records) rather than assuming `_struct_conn`
is the only dependency. Unsupported categories and ambiguous unmodeled placement
must be explicit. Reuse Cedar component-parent identity when source-bound evidence
exists, and preserve its competing-partner check before inherited-restraint
refinement. Reuse the already qualified source/scattering controls; a new native
run is not the first next step. P02 graphical review and changed-child/inverse-edit
lifecycle remain separate acceptance gates.

### Narrow first writer route: whole original asym units (W270)

**Agreed with Rowan; eligibility contract only.** A first writer can be narrower
than the full eight-path LNA cut. Require one proper crystal image for every atom
of each original `struct_asym` and one image for every declared TLS group. Preserve
source entity, sequence, copy, author and atom labels. Mixed memberships are an
explicit unsupported case, not a reason to split a chemical entity or independently
refine derived TLS groups. Existing source/frame, connection, TLS and assembly
owners supply the observations; no new parser or symmetry engine is needed.

The actual-file no-write check covers both original/recut LNA controls and a
nonidentity in-memory 3LNA whole-A proposal (all 16 registered A sites). That
proposal and the unchanged controls pass uniform membership. Both eight-path cuts
fail on original A/B/D and four TLS groups. This checks the narrow scope only:
all 82/75 source category occurrences, including two attached component blocks
per file, are inventoried but not all have qualified output actions. Unclassified
categories block writing. Component template coordinates are retained, not moved
with the observed model. Source scalar/loop layout must also survive.

The existing `sequence-family-target` plus source-bound construct registration can
name caller-declared full strands and copies when supplied and verified through
W262. For these actual files, however, the only saved target is the coordinate-
derived 62-site `reviewed-R3-pdb-coordinates` target, with one `COMPLETE` copy named
`R3`. That means complete ASU mapping, not complete physical strand/copy knowledge.
The fragment reports remain `SOURCE_LINEAGE_ONLY`; no independent oligo target is
bound. Original source prose names A+D as a 31-nt strand, C as a 14-nt strand, and
B as a 17-nt repeat of a linear 51-nt strand. It explicitly leaves the one physical
nick symmetry-averaged and unassigned to a copy. Preserve that unresolved state,
original operators and declared sequence; do not infer a circular strand, choose
a nick phase or create termini from the visible cut.

**Before emission:** enumerate explicit retain/transform/review actions for every
category and attached block; retain raw matrix namespaces/rounding, resolve the
native TLS convention and original shared-group policy, and qualify scalar layout
and endpoint references through existing owners. A uniform-membership pass is not
writer permission. Keep full mixed-path relabeling, physical repeat/nick phase,
entity assignment and the persistent P02 edit/refine loop queued separately.


W271 now [plans the output categories and native TLS boundary](topostitch-periodic.md#w271--plan-output-fields-and-separate-native-tls-interpretation).
Recalculate supplied present-polymer centers only under an explicit source-matched
weighting convention; preserve null/absent centers. Keep raw TLS field transport
separate from native S33 zeroization and restart compatibility. Derived assembly
operators must update inline matrices and membership flags together. No category
plan alone is permission to emit an unqualified file. W272 now provides the
[explicit in-memory draft boundary](topostitch-preview.md#prepare-a-reviewed-whole-asym-cif-draft-w272)
with readback and a source-specific native control. Complete declared-backbone
coverage is qualified by W273/W274. W275 adds immutable diagnostic save/replay;
ordinary command/inspector wiring remains next. Native restart and mixed-path
output stay separate.

The fragmented W246 two-rung ASU is a stress test, not a preferred physical cut.
Prioritize readable contiguous duplex segments for final inspection/export;
physical nicks and symmetry boundaries remain distinct.


W273's [serialized backbone audit](topostitch-periodic.md#w273--account-for-serialized-backbone-links)
accounts for all 60 declared edges in the actual whole-A draft, distinguishing
ordinary adjacency from explicit connection/image annotations. Coverage does not
activate native restraints or assign the R3 physical nick. The next ordinary-save
boundary now has [maintained per-step evidence through Cedar’s public interface](topostitch-preview.md#account-for-serialized-backbone-links-through-cedar-w274).
The local experiment’s pinned private helpers are not a production dependency;
[immutable diagnostic publication/replay](topostitch-preview.md#save-and-replay-an-immutable-whole-asym-export-w275) is now qualified for the supported whole-asym route.
Existing cut-preview command/inspector wiring is next; checkpoint selection and
native restart remain separate owners and gates.


## Maximally fragmented ASU refinement stress test (planned)

**B11 / PUB05; requested by Simon, 2026-11-25. Planning only: no new models,
refinement, benchmark result or figure.** Revisit this after the relevant P03
mixed-image export, P04 chemistry and P05 restart capabilities are qualified.
Keep W276's ordinary export/inspector integration first. This is a downstream
publication experiment, not another initial-release blocker or an instruction
to create a parallel refinement engine.

**Question:** can NASolve accept an intentionally fragmented representation of
DNA, preserve the same periodic molecule and refine it as reliably as a readable
representation? Call this a *maximally fragmented ASU representation*, not a
worst physical model. Each whole nucleotide changes its chosen image; no atoms
are removed, no chemical bonds are cut and no repair is implied. Preserving an
already good model tests invariance and workflow robustness, not recovery from
damage. A later, separately declared perturbation can test recovery.

### Revisit gates and ownership

- **P03, Pine/Willow:** qualified per-residue mixed-image serialization and inverse
  mapping, with original atom/sequence/component identity, all connection endpoints,
  entity/reference/assembly fields, occupancies, total deposited ADPs and labelled
  orbit multiplicity retained. W275 supports uniform original-asym/TLS images;
  it does not pass this gate. Reuse W246/W249's awkward cuts and W256–W275's
  source/metadata/readback owners; add only the missing scale/composition evidence.
- **P04, Cedar with Willow audit:** complete source-bound chemistry across all
  affected seams: bonds, angles, torsions, chirality, planes, declared pair/stack
  terms, nonbonded interactions and exclusions. Inspect the *actual native*
  inventory and effective parameters, not just connection records. True nicks,
  absent atoms and undecidable partners retain their original meanings.
- **P05, existing checkpoint/process owners:** a reviewed child can be saved,
  reloaded and refined with the same image/identity mappings and declared policy;
  stale mappings, interrupted outputs and duplicate force installation refuse.
  Reuse the persistent inspector and receipt/digest ownership. The experiment
  needs this scoped restart capability, not unrelated completion of the whole GUI.
- **P06, publication audit:** predeclare the exact case, protocol, numerical
  tolerances, comparisons and claims before native execution. Revisit B11 when
  each preceding scoped gate changes; record which remains missing rather than
  rerunning the earlier small-cut controls. Linden owns this plan; Rowan owns
  native execution/chemistry coordination. No chemistry-owner code is changed here.

### Separate two legitimate refinement routes

**Route A — preserved computational frame, preferred first.** Accept and inspect
arbitrary representative images, authenticate an inverse mapping into the same
qualified native frame, refine there, then return the result to each requested
representation. Verify the actual process inputs and output mapping. This tests
end-to-end representation independence. It is not evidence that Phenix directly
refined a model with every backbone edge represented by a symmetry proxy.

**Route B — native refinement in the dispersed representatives, later.** Run in
the fragmented frame only after the complete native interaction and exclusion
machinery supports it. Compare source/transformed target terms and correctly
rotated Cartesian gradients at matched physical coordinates before fitting.
Include a bounded seam finite-difference check through existing audit owners.
A bond-only implementation or a silently canonicalized model cannot support this
claim. If Route B is unavailable, publish Route A with that limitation instead of
blocking the useful workflow or overstating the result.

### Minimal, frozen experiment panel

Use one source with reviewed topology, usable observations and a bound Free-R
assignment for the first refinement panel; choose it at the readiness audit.
Existing 3LNA can supply representation precedents, but its unassigned R3 nick
phase cannot become an invented chemical truth. Prefer a simpler fully declared
case for the first all-seam chemistry claim; qualification on one case is not a
claim about all groups, special positions or modified residues.

| Condition | Chosen representatives | Purpose |
| --- | --- | --- |
| Control | Original readable representation; the same export/reload path | Isolate fragmentation from serialization or workflow changes. |
| Blocks | One predeclared block size, 2 **or** 3 consecutive nucleotides along declared strand paths | Intermediate boundary density; block size chosen before results, preserve real nicks/junctions. |
| Single nucleotides | One distinct full image transform per nucleotide | Maximum residue-boundary fragmentation for this source. |

Move every atom and alternate conformer of a nucleotide coherently. Keep all
non-nucleotide context and special-position multiplicities accounted for. Distinct
images mean a space-group operation **plus integer lattice translation**; there
need not be as many distinct rotational operations as nucleotides. Use a
reproducible bounded image assignment, including nonidentity rotations where
available and nonzero translations, rather than arbitrarily distant coordinates
that mostly test numeric range. Record the transform table and inverse, occupied
cell span and number of physical backbone edges requiring nonidentity relative
operators. Any symmetry-related duplicate orbit is an error, not a new molecule.

Keep the starting per-atom deposited ADPs fixed and equivalent for the initial
coordinate-refinement comparison, with matched occupancies and scattering policy.
Do not create an independent TLS group per fragment or add TLS U to total
already-deposited U. A later thermal-parameter refinement claim needs separately
qualified shared TLS/native convention and equal degrees of freedom. Freeze or
explicitly qualify any grouping, restraint or NCS policy that would otherwise
be re-inferred differently from the new chain representation.

### Chemistry extensions: Hg and LNA (planned)

Simon added these two extensions on 2026-11-25. Keep them in B11 / PUB05 after
the simpler first panel, with case-specific readiness audits; they do not expand
W276 or authorize new runs. Hazel owns the metal case and its evidence, Rowan
owns native chemistry, and Linden owns representative selection/comparison.

**Hg in an independently chosen image — Alder/Cedar stress.** Select an existing
modeled Hg site with reviewed donor/coordination intent and suitable bound data.
Move that site's representative independently of its DNA partners, carrying its
exact image relations so coordination crosses the chosen ASU boundary. This is
one existing Hg orbit, not an added mercury, an extra copy or a new species. Keep
site identity, multiplicity, occupancy, B/U and scattering assignments; rotate
anisotropic U through the existing owner. A genuinely new Hg hypothesis belongs
to a separate composition/metal-inference experiment.

Audit every declared donor–Hg distance, applicable donor–Hg–donor angle and
coordination restraint/exclusion against the same physical neighborhood before
and after the recut. Retain the actual interaction type and force policy: metal
coordination is not automatically a covalent bond, and close atoms do not create
missing intent. Bind wavelength, anomalous data/mate convention, f′/f″ settings,
Free-R assignment and any supplied experimental-phase inputs. Include anomalous
complex-scattering and donor-image checks where supported; a neutral-atom Fcalc
comparison alone does not qualify the metal claim. Do not add phase information
or merge anomalous mates to make the comparison pass.

Use a small isolation sequence: unchanged representation, Hg-only re-imaging,
then (once the DNA-only panel passes) the combined fragmented-DNA/Hg case. Reuse
the earlier control and DNA-only evidence only when exact input hashes, runtime
and protocol match; otherwise declare a matched panel. This separates metal-site
handling from backbone handling without a combinatorial search. Preserve Alder's
fixed-site/fixed-B/occupancy/f″ guards and actual active-variable policy in every
sibling. A fixed-Hg run can validate image handling, not recovery or fitting of
the Hg site. Release metal variables only in a separately qualified matched scope.

**LNA in fragmented DNA — Cedar stress.** Reuse a reviewed existing 3LNA/5LNA
source as a candidate, preserving the modified components, all atoms, locked-sugar
ring bonds, attachment geometry, chirality, source-supported pucker and applicable
pair/stack restraints. Keep dictionary versions and atom mappings exact; a
canonicalizing alias, deleted modification or altered restraint target cannot
count as success. Working aliases such as the previously bound A1C3T→ACL mapping
remain explicit working mappings, not permission to relabel deposited chemistry.
Re-image each complete modified nucleotide together, then audit both its internal
chemistry and the adjacent phosphodiester neighborhoods after native interpretation,
refinement and reload. Compare to the same unfragmented LNA model, not a DNA mutant.

Existing 3LNA/5LNA metadata and recut evidence are reusable precedents, not a
qualified all-fragment refinement result. The unassigned R3 physical nick remains
unassigned; an LNA case does not justify closing it. Freeze an explicitly supported
chemistry/continuation scope, or choose another known-topology case if that ambiguity
prevents the proposed claim. Candidate choice and exact readiness are pending the
owner review; no metal or LNA model is selected by this note.

The paper may add a donor–Hg–donor view across the boundary and a locked-sugar/
phosphate detail, reconstructed in the common physical frame beside the dispersed
ASU. Label coordination intent, fixed versus fitted quantities and retained
modifications. Combine LNA and metal stress in one model only if an existing
qualified source actually contains both; do not invent a hybrid for the figure.

### Staged measurements and stop rules

1. **Before refinement:** audit all atoms, orbit multiplicities, graph edges and
   true terminal chemistry; independently read native output and compare complex
   Fcalc in the same cell/setting over the predeclared common reflection set
   (prefer all available applicable indices). Preserve anomalous conventions.
   Compare mapped geometry/ADPs and inverse round trips. Record numeric tolerances
   from serialization/native controls before seeing the stress result. Equal
   R values alone cannot establish equivalence; missing connectivity can leave
   Fcalc unchanged.
2. **Matched refinement and restart:** use identical measured data, Free-R flags,
   refinement variables, scientific target, weights/policy, cycle/stopping budget,
   mask/scale treatment, software versions and declared seeds. Capture actual
   retained reflection membership and effective settings; do not assume matching
   PHIL files imply matching objectives. Qualify mask/scaling invariance rather
   than silently disabling the production treatment. Save/reload a child through
   the ordinary owner. Reuse a matched identity control; add a bounded repeat only
   if needed to establish numerical nondeterminism before equivalence thresholds.
3. **After refinement:** map atoms back with the saved exact transforms, without
   an unconstrained best-fit alignment. Compare density on the same fixed crystal
   grid; do not move a global map independently with each residue. Report
   Rwork/Rfree, reflection/test counts, maximum/RMS coordinate differences, all
   seam lengths/angles/torsions, chirality, pair/stack geometry, clashes and
   residual density. Compare common-frame densities with explicit map provenance.
   Log runtime and memory as observations; do not tune representations on Rfree.
   Comparable endpoints within predeclared bounds are the hypothesis, not
   guaranteed identical optimizer trajectories. A generic R < 0.3 gate does not
   establish representation equivalence.

Stop escalation at the first missing invariant or unsupported native term. Keep
that failure and its exact scope; a successful 2–3-nt panel remains a valid bounded
result if the single-nucleotide case is unsupported. Do not loosen geometry or
remove atoms to improve R factors. Reuse existing deliberate missing/wrong-image,
ADP, duplication and nick negatives; add a new one only for an uncovered boundary.
If recovery is studied later, perturb once in the common physical frame, map that
same perturbed model into every representation, and predeclare the recovery budget.
Do not mix that result with the initial representation-preservation experiment.

### Paper figure and retained record

Three compact panels: **(A)** readable / block / single-nucleotide ASUs, colored
by original strand and labelled as representative choices; **(B)** those same
models reconstructed into one identical, bounded crystal neighborhood to show
continuous DNA; **(C)** before/after refinement and seam-geometry comparisons,
including failures, alongside explicit Route A/B and ADP/TLS policy labels. Use
common views/scales for comparable panels; an exploded inset must be labelled as
schematic, never presented as the physical lattice. Reuse the inspector and shared
ChimeraX styling. A figure of fragmentation alone is not a refinement result.

Retain one frozen declaration, transform/identity mappings, original data/Free-R
bindings, native versions/effective targets, immutable model/checkpoint receipts
and a compact comparison table. Link large local science artifacts rather than
copying them into another test bank. The [publication shortlist](campaign-model-roadmap.md#nasolve-publication-demonstrations)
and machine roadmap B11 point here; no new run directory is needed until a gated
experiment is actually authorized and ready.

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

A numerical stop alone does not justify expanding the editable window. Separate
an unevaluated/rejected optimizer proposal or line-search failure from evidence
that a chemically admissible connection is unreachable under the current scope.
The W253 stop is an example: a later proposal exceeded a hard bound, but the last
accepted point was not a constrained optimum. W254 records future rejected-move
evidence without changing that boundary. Review initialization, chemical frames,
complete native terms and source/context binding before selecting a new motion
experiment. Necessary-distance bounds may help identify obvious conflicts, but
small differences from exact restraint ideals are not physical impossibility
criteria and passing such a bound does not establish closure. Automatic whole-
step expansion still needs the existing topology/permission and geometry gates.

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

### Preserve chemistry before a bend (W175, integration contract)

A source model and the bent candidate must share declared chemistry, even when
stretching temporarily puts a known link beyond native distance discovery.
Freeze the source contract **before deformation** and retain it through the
existing ordinary request/executor. Do not reconstruct the intended graph from
the displaced coordinates or promote observed native bonds into declarations.

The first capture must preserve:

- Exact parent identity/bytes, component/source definitions and declared links,
  nicks, terminal-phosphate choices and any supported symmetry intent.
- Original literal pair/stack/plane declarations, compiler/source provenance,
  compiled ordered PHIL and retained edits. Changed geometry does not rerun a
  pairing guesser or discard a supplied plane.
- Complete native input/version identity, model-to-native atom mapping and the
  required policy/monomer/geometry evidence, distinguished from chemical intent.
- Anchored checksummed references joining those records to the ordinary selected
  parent, exact child inputs and actual preparation lifetime. W173/W174 bind
  inputs; they do not supply this missing chemical authority.

Reuse existing producers rather than another chemistry format:

| Existing owner | What it already preserves | Remaining join |
| --- | --- | --- |
| `cif_model_context` | Audited prepared-model links, identities and phosphate intent | Freeze before the move; its distance audit cannot reconstruct stretched intent |
| `cif_literal_na_inputs` | Original and compiled NAR inputs, source/compiler provenance and replay | Native-index and source/PDB-index policies remain distinct; no policy-ID substitution |
| `cif_complete_request` / `cif_postmr_request` | Exact model/restraint contexts and compiler references in dictionary preparation | Carry authenticated provenance into the applicable ordinary motion route |
| `cif_native_validation.inspect_native_bundle` | Explicit native input capture with policy and optional full monomer inventory | Select required capture scope; later actual-manager retention is separate |
| `refinement_parallelity` / `refinement_counted` | Frozen child inputs/code, original counted-pair intent, admission and launch | Their current request policy does not bind a complete chemical contract for this motion |

The native transfer gate must check moving atoms, crossing terms and untouched
remainder against the **same** declared parent. Reuse Cedar's named-proxy and
supplied-restraint owners. A complete cross-site `link_status=MATCH` still reports
`chemical_qualification=NOT_ESTABLISHED`; it is not a chemical acceptance flag.
The fixed-coordinate dictionary-comparison owner is not applicable to moved
parent/child coordinates and must not be weakened to make them pass.

W175 binds this boundary on the existing private W172 control, including a
separate naming-only request copy. It creates no ordinary registry or MR history.
C412 remains a genuine ordinary but modified-parent request control; FT lacks
whole-model declaration authority. No verified canonical ordinary checkpoint
currently carries the exact W172 policy. Ordinary producer/request integration
and a supported retained-manager hook remain open, owned with Cedar.

W176 supplies the missing maintained fixed-coordinate parent capture, including
42 complete effective monomer mappings, consumed PHIL definitions and policy/API
provenance. All captured named proxy definitions match the older private parent.
These are observations of the native interpretation; they do not independently
approve its chemical definitions, record nonbonded forces, or supply ordinary
checkpoint ancestry. [Exact scope](topostitch-periodic.md#w176--capture-the-complete-fixed-parent-through-the-maintained-native-owner).

**Smallest ordinary integration step.** Reuse Cedar's
`cif_postmr_publication.validate_published_preparation` and
`cif_complete_request.read_dictionary_request_result`. Existing checked publication
already binds its prepared model, inherited restraints, topology and request/result
references; the complete result exposes model/restraint contexts and compiler
inputs where they were frozen. W177 now reports that availability through a Willow-side read-only adapter
for the exact published parent, without another producer, copied evidence,
new history or an implicit chemical verdict. Legacy missing contexts stay missing. Its source/installed checks and real C412
read qualify reporting only; W173 remains schema-2/canonical-motion scoped.
The source/PDB-index compiler policy is not the native-index C128 policy.

The selected descendant still needs its own identity/byte binding and the
published preparation lineage; a refined child's coordinates need not equal its
prepared ancestor. Before bending, retain the qualified parent declaration rather
than validating intended connectivity by distances in the deformed candidate.
Only after that join is qualified should the existing request/executor gain the
supported retained-chemistry lifetime. A modified ordinary input may qualify this
reader's evidence reporting without qualifying modified motion. Rowan owns the
publication/execution boundary; no shared Cedar code changes in W176.

**W178 source-producer evidence.** The existing canonical source selection and
`prepare_postmr_literal_inputs` produce a legitimate `literal_na_inputs` artifact
from frozen original pair/stack declarations and retained planes. Its compiler
manifest digest is `97a2b6f38a89fa5c904237765ee41512eb74d4de473bc13f7181685301f44d7b`.
All 213 terms agree with W176 native readback and compiled PHIL is byte-identical
to W172. Selection, old-path-gone relocation and changed-input refusals pass.
This is source-bound evidence, not an ordinary request or C128 native policy.

The existing native-index producer `prepare_literal_na_inputs` requires a genuine
capture of original literal intent. W176 already contains compiled edits: no
literal relationships remain to compile, and recompiling original declarations
against those populated edits would overlap them. W172's separately declared
private recipe is not a maintained original-capture artifact. A fresh original-
intent capture could use the existing producer; no replacement compiler is needed.
The separate ordinary canonical PostMR context is still unavailable for this
private parent. Do not create it retrospectively from native observations.
[Exact roles, checks and limits](topostitch-periodic.md#w178--bind-the-existing-source-producer-without-inventing-ordinary-authority).

**W179 original-intent capture.** A fresh maintained fixed-coordinate capture
preserves the original pair/stack declarations, retained planes and all
interpreter settings. The complete literal artifact producer refuses those flat
interpreter controls in its line-oriented restraint parser. An explicitly labelled
diagnostic partition of just the two independent literal/plane inputs lets the
unchanged native-index compiler reproduce W172 PHIL and all 213 W176 requests;
all fourteen native mechanics checks pass. Capture settings are retained in the
full evidence, not silently discarded or reclassified as restraints.

**W180–W182 update.** Cedar `ac339d3e` now supplies that typed artifact:
`cif-typed-native-literal-inputs-v1` preserves ordered restraint/control roles and
reconstructs the unchanged compiler result. It deliberately grants no ordinary
execution authority. The public PostMR entry still refuses it before request
creation. Cedar `f27a8dd2` separately adds an opt-in, native-identity-bound comparison
for ReadySet atom-name padding; it does not change reader-control admission.

The next owner is the existing `initialize_postmr_dictionary_request` /
`cif_complete_request` contract, carrying typed controls through the dictionary
bundle into `execute_prepared_dictionary_repair.capture`. Its native launcher
already freezes the exact ordered PHIL list and command/spec inputs. Keep controls
out of the explicit-restraint grammar, preserve original role order and bytes,
and reconcile `FULL_MODEL_PHIL`'s generated `use_ncs_to_build_restraints=False`
with the captured declaration. Require changed/missing/reordered/conflicting
control refusals and a relocated cold read before a new native check. Native
readback of the required effective settings remains necessary; a dispatch probe
alone does not prove Phenix honored them. [W182 boundary proof](topostitch-periodic.md#w182--locate-the-ordinary-control-owner-without-admitting-execution).

The read-only Willow preparation inspector remains reporting-only. Neither this
handoff nor typed input capture supplies ordinary canonical ancestry, selected-child
lineage, an atomic launch lock, or the retained chemical-manager lifetime for motion.
The W167 cluster accommodation plan remains downstream of those gates.

**5W6W scaffold default (22 November, via Rowan).** For 5W6W and derivatives
preserving its central strand/junction, carry Simon's default covalent intent
B:7 O3′ → B:1 P. Pine must keep that intent editable, let construct-specific
nicks/topology changes override it, and resolve logical endpoints after
renumbering or re-slicing. A large spatial gap does not make B:1 terminal:
retain P/OP1/OP2, without OP3. See Cedar's canonical
[central-strand chemistry guide](https://github.com/vecchioni-lab/NASolve/blob/e493e7f2b3a31d78d37d4882c2830e021b6490d6/docs/backbone-chemistry.md#the-central-strand-in-the-5w6w-scaffold).

In Cedar's pinned original-frame/no-Hg PDU cases, hold B:1 P fixed and transform
**B:7 O3′** by `-x+y,-x,z`. This is a measured image realization of
investigator-supplied covalent intent, not a universal matrix for every ASU or
origin. Keep the transformed endpoint explicit; the FT convention below images
the opposite endpoint in its own pinned model. Rebind/recompute the operation
when the representation changes. Other physical nicks, occupancies and
whole-strand closure need their own evidence. This documentation records the
scaffold default; it does not activate a symmetry bond without its full native
angular/exclusion context or retroactively alter older diagnostic chemistry.

**FT connectivity clarification (20 November, via Hazel).** The investigator
now declares B:7 O3′ → B:1 P as a symmetry continuation. B:1 is therefore not
assumed to be a free terminus. The current coordinate-derived realization images
the **target P** by `-x+y,-x,z`; the inverse `-y,x-y,z` belongs to the alternate
view holding P fixed and imaging O3′. Both have zero lattice translation in this
specific pinned model. These image assignments are geometric evidence, not
separately user-specified operators or qualified native symmetry restraints.
The investigator subsequently confirmed C/D crossover conditional on chain A
having 21 residues. Hazel verified A:1–A:21 in the exact current, PostMR and
selected MR models. The condition is met; the residue-level D:7 O3′ → C:8 P
correspondence and its image remain source-derived geometric realization.
D:1 terminal intent is unchanged. Preserve OP1/OP2 continuation intent; do not
materialize an unqualified symmetry bond or infer missing whole-model authority.

Alder owns the exact local declaration:
`NASolve:branch-artifacts/Alder/ft-symmetry-contacts-20261120-03/user-connection-intent-v2.json`,
SHA-256 `64bb43560c27dbb6f34eb3166f7de69e808fa88402ba156982a7118826a3d09f`.
Version 2 supersedes earlier C/D tentativeness after the initial B:1 declaration.
Older receipts remain immutable; slicing provenance and native seam angles/
exclusions remain unresolved. No new inference or executable recipe follows.

### Cluster accommodation: bounded helix opening and closing (W167, planned)

The user clarified the nanocluster architecture with Hazel: first place and
rotate an intact cluster, then, if needed, open or close the surrounding DNA
through bounded coupled motions and restrained recovery. This is a distinct
planned motion, not a result established by the signed-bend controls or W166.
It belongs after supported parent-derived chemistry/child-diffraction integration;
it does not replace the current bending/map-review queue.

**Shared ownership.** Alder owns donor-defined Ag–Ag network hypotheses, cluster
rigid-body pose and the A03/A07 assessment experiment in
[Cluster extension and chemical declarations](metal-restraint-builder.md#cluster-extension-and-chemical-declarations).
The clarification is pinned to Alder `928aa8e6`, subsection **Cluster placement
and coupled DNA accommodation (20 November intent)**. Linking it here does not
merge the branches or qualify their combined runtime.
Willow owns the bounded DNA proposal and its local frames/windows. Cedar owns
source chemical definitions and native geometry/exclusion validation. Use one
explicit parent/candidate atom mapping and declared topology across the three;
do not introduce another chemistry dictionary, launcher or refinement lifecycle.
Cedar Q15 owns the planned shared offline regional twist/width report
(`84257082ee9c15ce76ff809d06c0cd4f3ac1c0a2`, `docs/helical-geometry-plan.json`).
Willow will consume that qualified owner for matched regions; it will not build
another helical-analysis engine. Keep paired-P distance and each strand's
P-to-local-axis radius separate from C1′ spans and donor/cluster measurements.
Hazel reconfirmed W167 as the current architecture; the later single-Hg objective
diagnostic is not cluster or width-change qualification.

Alder now supplies the read-only connected-region inventory through
`nasolve.metal.motion_scope.inspect_movement_scope` at commit
`9f490b6903917692b55fc63526132e37242ec499`. It consumes complete Cedar native
captures plus explicit prepared residue/flank contexts and metal labels, and
records whole-residue/metal membership, fixed flanks and crossing bonded terms.
Plan to reuse that owner for cluster proposals. Its content fingerprint does
not authenticate the source; caller binding remains required. Source review
confirms the narrow identity-symmetry scope, with no movement, closure, B/Q
admission, packing or diffraction qualification. The inspector is on Alder;
this reference neither imports it into Willow nor validates a combined build.

**Motion and chemistry.** Rigid cluster placement preserves internal cluster
geometry during that proposal. Later internal flexibility is a separate declared
hypothesis, under Alder's supported restraints. Do not apply the near-linear
donor–metal–donor preference of a low-coordinate bridge to an entire cluster:
cluster shape, each metal's local coordination and oxidation-state assumptions
are separate. Nucleobase participation is the default cluster hypothesis;
nonparticipating alternatives need strong recorded evidence, not silent fallback.

For DNA, use oriented local base/pair frames and an explicit editable window on
both strands, with a displacement bound, boundary context and protected
junctions. Exact pivots, neighborhood, mobility boundaries, displacement limits,
boundary restraints, kinematic parameterization and ranking remain open; no
particular pair or implementation has been selected. Opening can involve base
pose, glycosidic orientation, sugar pucker and sugar-phosphate paths, coupled to
rise/twist and asymmetric strand motion. Preserving chemistry does **not** freeze
sugar or backbone coordinates: their connected atoms may move together to make
room. The constraints preserve chemical identity and supported geometry; they
do not require the initial conformation to remain fixed. Hazel reconfirmed this
interpretation of W167 on 20 November; it adds no new motion implementation.
Move intact base geometry and let supported torsions/angles and backbone geometry
relax; do not radially scale all atoms or stretch ring/sugar bonds to manufacture
room. Retain atom identities, chemistry, nicks, declared source covalent links,
flank angles, applicable torsions/chirality and nonbonded exclusions. Any change
to pair/register or coordination intent must be explicit; canonical pairing
restraints apply only where that pairing remains the declared hypothesis.
W166's exact-identity mapping and W168's private native lifecycle are reusable
prerequisites, not proof for a metal-containing or width-changing model. W168
observes child diffraction being constructed before parent-only chemical
interpretation; the earlier pre-fmodel wording does not describe that entry.
Symmetry covalent seams remain outside this qualification.

**Measurements and comparison.** Record source, proposed and recovered states:

- Cluster pose and donor/metal identities; donor spans, metal offsets and local
  coordination, internal metal–metal distances, DNA participation and clashes.
- Opening in declared local frames: report C1′ spans, relevant donor spans,
  phosphate-path separation and cluster clearance separately. A C1′–C1′ distance
  is a local anchor measurement, not a universal helix diameter; define the
  measured atoms, projection and frame, including asymmetric/curved cases.
- Both neighboring pair steps and transitions into fixed context: rise, shift,
  slide, roll, tilt and twist; pair orientation/contacts, stacking separation and
  overlap; glycosidic/sugar/backbone geometry, link angles and periodic clashes.
- Source-bound ordinary/difference maps at donors, sugars and phosphates;
  molecular content, unchanged observations/Free and matched post-recovery
  Rwork/Rfree. Density fit and geometry must be reviewed together.

Compare a matched no-opening control and prospectively bounded opening/closing
alternatives, with the cluster-pose proposal and recovery budget recorded so
their effects can be distinguished. Follow Alder's admitted sequence: restrained
open XYZ/B refinement, environment-B preparation, then f″/Q assessment with
XYZ/ADP/f′ frozen. Refresh the branch's environment B after changed geometry;
do not carry old frozen B into the new assessment. Do not silently reset or relax
that phase policy; allow the declared recovery window before judging initial Rfree. Cluster-summed f″ can
support count hypotheses but does not uniquely determine an atom count.

**Available motion is narrower than this plan.** The canonical whole-residue
preview gives a residue/pair step one rigid transform, preserving its internal
shape (including glycosidic geometry when all involved atoms share the transform)
before rounding. A shared pair transform does not open that pair. Different
residue transforms can strain flanking polymer junctions; the preview audits
those changes but does not solve closure. `TaperedMotion` is bounded arithmetic
with caller-supplied atom weights, not a geometry-preserving two-donor opening
solver. No qualified modified-base/sugar/metal opening move preserves both
flanking junctions today. W168 retains source geometry during a private canonical
recovery diagnostic; W169 protects bytes/mask/B/Q. Neither supplies that missing
closure primitive. Hazel and Rowan received this exact scope.

**Evidence boundary.** Hazel's FT_Hg single-bridge review motivates measuring
base pose and donor spacing independently of sugar-anchor span; its human model
is descriptive, not an ideal geometry target. No cluster accommodation or helix
widening/narrowing experiment is qualified. `TaperedMotion` currently supplies
one six-parameter tapered rotation/translation, not a dedicated width mode.
No new fit, angle target, operational flag or automatic adoption is introduced
by this plan. S04/S05/S06 and Alder A03/A07 retain their open qualification gates.

Documentation validation: eight focused `tests/test_topostitch_roadmap.py` tests
with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, generated roadmap `--check`,
JSON/reference checks and `git diff --check` pass. No product code or runtime
schema/default changes, no migration, native execution or raw scientific
artifacts in this patch. Installation and full-suite checks are not repeated
for this planning-only update.

### Planned default backbone-fit check (W165)

**User direction after viewing the 11:20 larger-bend checkout:** make a backbone
fit check enabled by default, while keeping repair execution and adoption separate.
This is a pipeline decision, not a currently installed switch. The planned human
label is **Check backbone fit**; no CLI spelling or runtime schema is finalized.

Run the read-only check after the first usable refinement and at explicitly
refreshed checkpoints, once model/map provenance and frame correspondence are
qualified. Its trigger combines the named project **high-Rfree review criterion**
with either **coherent negative difference density at actual phosphate/backbone
atoms** or **significant coherent positive density near a plausible backbone path**.
Record extent, affected atoms/residues, ordinary density support and the evidence
for an alternative placement. Do not adopt a universal numeric cutoff here or
reuse the inspector's 3.5σ display setting as a detector threshold. Resolution,
map processing, local noise and model-wide repeated testing require calibration.

Detection first distinguishes a plausible displacement from ADP/occupancy errors,
missing atoms/alternate conformations, wrong sequence/register or junction/
connectivity issues. Green density alone need not mean an existing duplex should
bend; a red phosphate alone is not a displacement instruction. Ambiguous cases
produce an explanation and review flag, not a forced structural hypothesis.

When supported, propose a bounded bend/recovery trial through the existing
TopoStitch and refinement owners. Execute only with explicit approval or an
already-authorized automatic campaign policy. Preserve the parent and all
outcomes, keep the original data/Free and declared chemistry, and compare with
an equivalently refined unchanged control. Allow the declared restraint-driven
recovery window before judging initial R statistics. Geometry, maps, molecular
content and known topology govern review alongside the statistics; adoption or
checkpoint replacement remains a separate recorded decision.

W163–W164 justify this as useful development direction, not a qualified automatic
repair: the positive synthetic endpoint has low Rfree but retains a local
phosphate-angle distortion. W155/W160 density ambiguity and noisy calibration
remain prerequisites. Put the detector in **S06**, its evidence/proposal UI in
**S07**, and bounded campaign execution/review in **S08**. Keep default detection,
permission to try a candidate and acceptance of a result distinct.

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

**W160 completes the independent noiseless model-assisted panel below.** Known
position and B errors both give negative modeled-P density, while own-map σ can
amplify a numerical-scale zero-control residual. Common truth normalization is
synthetic evidence, not an experimental display or acceptance policy. Noise and
scientist calibration remain open; no detector follows.
[W160 evidence](topostitch-periodic.md#w160--retain-ambiguity-and-normalization-context-in-model-assisted-maps).

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
recovery task; W160 completes the bounded noiseless map panel independently.
Its remaining noise/uncertainty qualification does not block geometry-only
benchmarks. Reciprocal target shapes, larger/nonuniform bends and junction-limited window expansion remain the
existing S04 queue. W150 receiving integration, B09 geotest and B10 explicit sticky
activation remain separately open. No acceptance threshold, chemistry, production
policy or runtime schema changes here.

<a id="next-capture-qualification-after-w159w161-planning-only"></a>
### Actual-state capture boundary after W162

The bounded passive/replay experiment is now recorded in
[W162](topostitch-periodic.md#w162--bind-the-selected-backbone-state-and-retain-the-derivative-limit).
It qualifies consumed LS/ML core values, actual selected-trial attribution,
explicit plane parameters and exact captured-prefix/output neutrality within
its private scope. Direct geometry/combined directional checks pass, but data-only
checks miss the prospective bound. The finite scan is withheld; both direct and
original FFT targets/gradients restore exactly. No new optimization or tolerance
change is authorized by that evidence.

Historical C397-derived dihedral observations omit limit/top-out/slack. Future
capture must use the existing live-policy owner rather than assume defaults from
descriptive rows. W164's nine reconstructed saved managers establish their own
explicit default policies, not the missing historical callback values. Native
likelihood/core, masks/scales, normalization, callbacks and full retained forces
must remain bound for any new supported profile. Saved final F-model arrays are
still distinct from an earlier selected-XYZ objective.

Keep this a closed bounded mechanism study, not a universal repair prerequisite.
No repeated C395–C400 control, derivative sweep or protocol search is queued.
Ordinary ancestry, density noise/normalization and complete scientific acceptance
remain separate. W156's matched recovery window and map review govern physical
repair, without demanding a perfect no-op or monotonic Rfree.

### Preserve declared topology through deformation (W163–W164; next integration)

The larger canonical control exposes a concrete boundary: native preparation
can interpret a stretched known O3′–P link as absent, also dropping its flank
angles. A private matched 4 Å envelope retains the native source context and
allows recovery. **Do not turn that value into a production default or infer
chemical connectivity from distance alone.**

The next supported contract should reuse existing registration, native coverage,
preparation and execution owners:

- Bind the explicit source model/construct mapping and declared canonical
  same-ASU links before deformation. Unknown links, true nicks, sequence changes,
  missing atoms and symmetry-image seams are different scopes.
- Carry complete native link context, including flank angles, applicable
  torsions and nonbonded exclusions/type/function policy. A bond-only edit is
  insufficient. Existing live-policy readers must check fields absent from
  older descriptive captures.
- Reinterpret a new candidate only under an explicit prospective policy, then
  compare intended graph and supported geometry definitions with the source.
  Refuse added/lost links or unexplained context changes. Coordinate-dependent
  nonbonded neighbor membership may change; graph exclusions must not silently
  follow a lost link.
- Preserve parent/child identity and raw observations/Free. Keep the native
  prepare/refine boundary inspectable and do not invent ordinary checkpoint
  ancestry for a private direct diagnostic.
- Assess atomic geometry and density after a matched recovery budget. W164's
  positive arm has low synthetic Rfree but a 31.32° local phosphate-angle error;
  checked chirality signs and R statistics alone cannot approve it.

W166 qualifies the first bounded geometry-only seam: prepare the intact parent
at the default 3 Å cutoff, bind a complete unique atom-identity bijection, and
evaluate displaced coordinates using that same native manager. Both signed
starts retain all 38 source links, the long bond's four flank angles and fixed
exclusion context; physical energies/gradients agree with independent 4 Å
controls, and restoring the parent reproduces the baseline exactly. Native
preparation reorders terminal OP3 even with `sort_atoms=False`; input row order
cannot be used as proxy identity. Compare input chemical state with input state,
and preserve/check the separately prepared native state (including B/Q).

This does **not** qualify changing coordinates after diffraction preparation:
the next execution boundary must bind candidate hierarchy/scattering coordinates,
native geometry/site symmetry and fresh diffraction state before optimizer use.
No production API, cutoff default, new link or accepted child follows from the
dry-run. [Exact scope and validation](topostitch-periodic.md#w166--carry-known-parent-geometry-without-a-global-cutoff-change).

This remains an integration specification, not a new installed feature. Reciprocal
curved/straight target shapes, nonuniform bending, larger experimental cases,
B09 geotest, B10 sticky enforcement and symmetry-phosphate chemistry remain open.

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


### Single-call parent preparation boundary (W199/W200)

W199's private live qualification identifies the interpretation call before the
counted driver as the required boundary. Candidate diffraction must be built from
the candidate, while geometry interpretation receives the bound original parent.
The admitted W198 mapping handles initial parser order and prepared native order
separately; its candidate coordinates restore the same live manager before
preparation continues. Do not enlarge the link cutoff or re-infer stretched bonds.

W200 now provides the opt-in one-shot `NativeEndpointPreparation` context. Explicit inputs are the
bound parent/candidate/motion plus a trusted, source-qualified native builder.
The context requires complete candidate→parent→candidate identity checks and
fixed/moving scope, exactly one interpretation/transfer and success-only closure.
The native builder retains chemistry/topology and diffraction evidence; the outer
worker owns retained input lifetime, process and disposal of failed managers.
No exception grants a reusable manager or an implicit retry. Preserve the first
failure and restore only owned bindings; foreign replacement requires refusal.
This is not a new execution format. Existing counted/native policies remain
versioned and unchanged until a separate integration is agreed with Cedar.
[Qualification and limits](topostitch-periodic.md#w199--use-the-installed-handoff-during-live-preparation).


### Versioned parent preparation execution contract (W201)

**Planning, no dispatch:** named opt-in route
`topostitch-bound-parent-preparation-v1`, with proposed existing-owner policy
`round-local-parent-geometry-execution-v10`. Neither identifier is registered or
accepted by current code. The [intent JSON](topostitch-intent.json) records the
same unfinished contract; it is not a runtime request schema.

Five cold controls against Cedar `ed4fa6d7` establish the current ordinary v3
boundary: historical capture readable; fresh default helper bytes unchanged;
rehashed extra parent field and proposed policy refused; parent sidecar absent
from the native command refused before allocation. The parent must be a typed
geometry-only reference, separate from the command's candidate model input.
Do not pass two models or quietly overload counted `original_model`: that field
records original pair provenance and need not equal the immediate current parent.

| Required role | Existing authority to bind |
| --- | --- |
| Geometry parent | Exact selected/current checkpoint plus applicable Cedar source/preparation context |
| Diffraction candidate | Exact admitted preview candidate in ordinary model input; W174 ordered request join |
| Motion scope | Existing full-precision preview/endpoint audit, raw-record index basis and complete moving/fixed identities |
| Chemistry | Current phosphate/topology intent, literal and compiled pair/stack/plane policy, reader controls and effective definitions |
| Diffraction | Original observations/Free and phases, plus actual candidate F-model invariance around parent interpretation |
| Native builder | Maintained, source-qualified bridge for one interpretation under the same manager and complete Cedar verification |
| Lifetime | Actual outer retained-input/process scope, never a cold release receipt |

Parent/candidate roles remain explicit for a byte-identical neutral control.
Original observation provenance and a computed parent-model F-model are distinct.
If the latter is required, supply separately bound evidence or refuse; do not
rename candidate F-model evidence as the parent. This contract does not invent
a missing ordinary pair assignment or chemical approval for X11_22.

The proposed `parent_preparation` request field belongs only to a new versioned
policy in the existing owner. Shared edits must be agreed before changing
`prepare_execution`, `read_execution_request`, `_code`/`_expected_code`, its frozen
entry/helper set or the new live builder. Keep old helper bytes/readers/defaults
unchanged. Old readers must refuse the new policy. W200 alone is not the native
builder or a replacement for those owners.

At runtime, verify retained inputs; build candidate diffraction; interpret the
bound parent once; require complete parent proof; transfer via W200 in current
native order; require exact fixed context, retained chemistry/scattering and
unchanged candidate diffraction; then close preparation. A separate successful
preflight/admission must precede refinement. Failure preserves the first error,
restores only owned temporary bindings/settings and discards the failed process/
manager; it grants no rollback/reuse. Keep inputs held until every consumer stops.

Next is agreement on that shared extension and a bounded maintained dry-run/failure
qualification, not another private refinement or another Willow request reader.
[Exact audit](topostitch-periodic.md#w201--identify-the-missing-geometry-only-parent-input-role).


### Shared live geometry boundary (W202)

Cedar C507 exposes `cif_native_validation.collect_live_atoms` before geometry
exists and `collect_live_geometry` with the retained interpretation afterward.
These use Cedar's pinned native readers; the geometry observer checks selection
identity/index correspondence and reads current coordinates. TopoStitch consumes
the existing topology reviewer separately. [W202 qualification](topostitch-periodic.md#w202--qualify-typed-controls-and-the-maintained-live-collector)
binds all four authenticated reader settings in an actual dry-run/failure pair.
Original literal capture, compiled restraint intent and current live geometry
remain distinct evidence roles. A successful collector does not establish full
chemistry or authorize transfer/refinement. The next maintained builder must
compose this evidence with W200, exact source/current-parent identity, candidate
diffraction and the separately owned outer lifetime before public dispatch.


### Shared seven-site 5W6W intent recipe (Cedar)

Cedar commit `9d5030fbc06f436f428ec2cb88308e73c72b8c74` owns
`docs/recipes/5w6w-central-continuation.json`: fixed B:7 O3′, transformed B:1 P
uses `-y,x-y,z`; the reciprocal P-fixed/O3′-transformed view uses `-x+y,-x,z`.
This is the investigator's explicit central-strand convention, remapped through
Pine's existing packet observer. The tested seven-site scope leaves other atoms
as unchanged context. D:1 terminal chemistry is separate. It does not assert
whole-assembly/triple-junction closure, approve geometry or enable native
bonds automatically. Keep the source frame/operator roles explicit after recuts.


## Coordinated phosphate recut follow-up

**Scheduled after W244/C547; planning only (2026-11-23).** Incorporate the new
OneDep validation when available and bind its exact processed mmCIF/version
before interpreting any changed connectivity. Validation is evidence to review,
not permission to infer a partner or change chemistry. This is a dependency order,
not authorization for an immediate scientific rerun or a second force engine.

**Processed 3LNA V51 observation (Cedar/Rowan, 2026-11-23):** the external
annotation-retention check is **complete: NOT RETAINED**. Cedar's installed
comparison reports all 58 ordinary steps in both models, no long steps and a
maximum length of 1.6214 Å. All 1,271 sites, coordinates, B/Q and six anisotropic
U components match exactly. V51 omits the entire submitted 80-row connection
table, including all nine phosphate `covale` rows and both cross-copy links.
The two reported symmetry close contacts match the declared relative operators
and V51 distances of 1.60946/1.60802 Å. Thus physical/local native evidence
survives, but the processed file does not retain the declared connectivity.
Do not interpret missing annotations as a real nick or infer fresh bonds from
proximity. Keep the source-bound construct/image declarations separate from the
processed-file observation. Curator action and an independent 5LNA return remain
open. This is Cedar's reported comparison, recorded by Willow without rereading
or altering the manuscript packet; exact input provenance remains with Cedar.
No P01/S03 milestone or later recut/coupled-fit gate is closed by this observation.

| Order | Existing gate and owner | Required result before advancing |
| --- | --- | --- |
| 1 | P01/S03; Pine intent, Cedar chemistry/readers | Verify both declared links in the exact processed mmCIF: atom/residue/strand identities, directed partner images and translation, chemistry and source hash. Cross-check serialized connection records against declared construct intent and coordinates. Missing or ambiguous records remain unresolved; do not invent connectivity from proximity or assume an absent record proves a nick. |
| 2 | P01/P02 with F02; Pine | Carry the scientist's chosen strand/image/connection intent through the existing recut preview and source-bound choice. Preserve both directed routes, paired-rung correspondence and reciprocal images; show real nicks and undecidable partners distinctly. Recutting cannot reconnect a physical gap. |
| 3 | P03; Pine with Cedar scattering/serialization owners | Before any refinement, independently compare source and reselected ASU in one cell/setting. Preserve atom-orbit inventory/multiplicity, components, occupancy and properly transformed anisotropic tensors; compare unrefined calculated structure factors and reciprocal round trips. Check chemical graph equivalence modulo the chosen representatives. Equal R values or a locally preserved tensor is insufficient. |
| 4 | P04/S05; Willow qualification, Cedar sole force owner | Activate both explicitly registered cuts together in one bounded diagnostic fit using the combined movable-atom selection. Qualify both complete bond/angle/torsion/exclusion neighborhoods and their interaction, preserving protected rings, chemistry, thermal state and observations/Free. Reject duplicate or inconsistent restraint installation. This is the open coupled-junction gate, not a repeat of four independent single-junction fits. |
| 5 | P05/S07; Pine workflow, existing checkpoint controller and Cedar | Restart from the immutable reviewed child with freshly bound intent and native inputs. Reuse Cedar's single force owner and existing process/checkpoint lifetimes; prove both links survive restart without stale image mappings, duplicate forces or silent checkpoint selection. The persistent GUI/review loop remains a separate release requirement. |

**Reuse and negatives:** W239 already exercises explicit staggered directed
routes and coordinate/tensor round trips; W240 supplies the installed local
native entry; W243/W244 prove bounded return/export behavior and individual
healthy-cut execution. W241/W242 retain the receiving comparison and weight
observer. Reuse the existing rotated, screw and physical-gap panels and stored
controls, running only the new composition or changed boundary. Add the missing
combined-scope evidence rather than recreating readers, tensor transforms,
restraint engines or benchmark collections.

Include a declared **real nick** and an **undecidable partner** in the applicable
intent/recut/force-admission checks. The real nick must remain chemically a nick
under representative selection; an undecidable partner must stay unresolved and
must not acquire a covalent force. Existing phosphates and explicit terminal
chemistry remain governed by intent, never by the accidental ASU boundary. A gap
must remain a gap under a pure recut; any coordinate repair is a separate S-track
child. Use an existing negative fixture when it already covers the required
boundary; otherwise record the precise missing case before adding one.

**Ownership and non-duplication:** unrefined scattering/ASU equivalence belongs
at P03, before coupled refinement; coupling belongs at P04/S05; restart belongs
at P05/S07. OneDep/deposition decisions and Cedar's independent Q06 AutoRefine
item are outside this follow-up. C547's bond-only/complete fixed-unit diagnostic
does not close W241's different original-start versus geometry-seed question.
Keep W241/W242 and S06's common-policy, residual torsion, density and matched
recovery comparison open. No weights are selected from Rfree, and no new
supported fixed-weight mode is implied by this schedule.


### Local phosphate orientation in the named duplex

**Queued with Cedar, 2026-11-23; no new implementation or force.** Simon/Rowan
identified inward-facing OP1/OP2 at 5LNA A111→A112 despite near-1.6 Å bond lengths
and conventional phosphate handedness; source provenance is still being tested.
Cedar owns that diagnosis and any correction. The downstream S05 review should
inspect local duplex-relative OP orientation before/after filling or deforming a
backbone, using explicit sequence/pair correspondence and named crystal images.
Do not infer a universal outward rule, relabel OP atoms merely to improve a score,
or reject legitimate alternative rotamers/nicks. Missing or ambiguous duplex
correspondence remains unresolved. For P03 pure recuts, this relative orientation
must remain invariant; a pre-existing source defect is distinct from recut damage.
