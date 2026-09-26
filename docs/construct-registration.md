# Construct registration and the Registration Net

Status: **design contract; not yet implemented.** This layer is intended to make
NASolve robust to real crystallographic coordinate representations without
changing the logical construct intent supplied by the user.

## Core idea

A logical construct site such as `A:12` must not permanently mean "PDB chain A,
residue 12." It means a site in the intended construct. A search model or MR
solution may represent that same site using different chain IDs, numbering,
chain splits, crystallographic cuts, symmetry mates, or multiple copies.

NASolve should therefore insert an explicit registration layer:

```text
logical construct intent
        -> construct registration
        -> coordinate realization in this model/ASU
        -> PostMR chemistry and refinement
```

Registration is a mapping/provenance problem. It is separate from chemistry,
topology, MR success and donor eligibility.

## Why this is needed

Real models and solved ASUs may differ from the logical construct in several
representation-level ways without representing a genuinely different assembly:

- a logical strand may use a different coordinate chain name;
- residue numbering may start at an arbitrary offset or contain insertion codes;
- one logical strand may be split across several coordinate chains;
- several coordinate chains may together represent one logical strand;
- the same periodic object may be cut through a different part of the lattice,
  producing a different but crystallographically equivalent ASU representation;
- sticky ends or arm boundaries may be too long, too short or cut differently;
- required terminal chemistry such as a 5-prime phosphate may be absent;
- an unexpected space group may yield two complete construct copies instead of
  one; or
- an ASU may contain one complete copy plus a partial second copy.

These cases must not be collapsed into a generic "sequence mismatch."

## Motivating crystallographic cases

The initial design is motivated by recurring lab failure modes rather than an
abstract renumbering problem.

Representative cases include:

- **3GBI/8D93-style equivalent cuts:** the same broad periodic object can be
  represented by a duplex-like or junction-containing ASU cut. A correct model
  may therefore look different in chain boundaries without being a different
  construct.
- **3GBI/5W6W-style slice/boundary differences:** a search representation may
  have the right overall geometry but a different sticky-end/boundary cut and
  may omit terminal chemistry that the intended construct requires.
- **8D31-style multiplicity surprises:** an unexpected space-group/ASU
  interpretation may contain an additional complete construct copy. Dataset
  sequence/chemistry intent must then be propagated to both complete registered
  copies.
- **partial-copy ASUs:** one complete logical construct may coexist with only a
  fragment of another. That fragment must not be silently coerced into a second
  complete copy.
- **messy imported MR models:** chain names may be unrelated to the logical
  design, residue numbering may begin at arbitrary values, and one logical
  strand may be split across several coordinate chains.
- **multi-PDB dataset folders:** several plausible search models may coexist and
  need bounded registration scouting plus MR attempts rather than filename-based
  guessing.

These examples are meant to exercise one common abstraction: the logical
construct is stable even when its coordinate serialization is not.

## Failure-mode triage matrix

Registration should make the response to common problems explicit and
deterministic.

| Observed problem | Automatic response when unambiguous | Escalation / guided response |
| --- | --- | --- |
| Chain renamed, e.g. logical A appears as M | Register by sequence/connectivity; retain coordinate label as provenance | Ask only if several non-equivalent strand assignments remain |
| Residue numbering offset/arbitrary numbering | Map logical residue order/site identity to coordinate IDs | Ask if gaps/insertions create multiple plausible correspondences |
| One logical strand split across coordinate chains | Join the fragments in the logical registration without editing coordinates | Guided fragment assignment if several joins are plausible |
| Equivalent alternative ASU cut | Recognize by reviewed symmetry/cut recipe or unique symmetry-aware registration | Show Registration Net and candidate cuts when more than one non-equivalent cut survives |
| Sticky end/arm too long or too short | Record coverage/boundary difference; apply only a reviewed recipe | Guided review if the intended boundary cannot be established uniquely |
| Required terminal phosphate absent | Keep registration separate; pass the logical terminus to the existing chemistry audit/construction path | Stop if boundary identity itself is ambiguous or chemistry is unsupported |
| Extra complete ASU copy | Register each complete copy and propagate logical sequence/mutations to every complete instance | Guided review if copies are non-equivalent or map differently |
| One complete plus partial extra copy | Register the complete copy; classify the fragment as partial; do not propagate complete-copy chemistry into it | Expanded report plus guided interpretation; later topology layer may explain it |
| Search-model scout looks simple but MR output reorganizes the ASU | Re-run authoritative registration on the actual Phaser solution and discard the scout as downstream authority | Guided review if the solved ASU has ambiguous multiplicity/cut |
| Ordinary MR fails but representation mismatch is plausible | Spawn a bounded Registration/Recut Rescue candidate under a reviewed recipe | User chooses/edits the cut when no reviewed deterministic rescue applies |
| Several PDBs in the dataset | Scout each bounded candidate; reject models lacking required logical coverage; run eligible MR attempts | Preserve a shortlist if multiple successful models imply materially different interpretations |
| Same logical target but sequence differences | Register first, then express differences in logical coordinates for PostMR | Stop if the mapping itself is ambiguous; do not let sequence mutation hide a registration problem |
| Topology/connectivity genuinely differs | Do not force a registration merely because sequence can be aligned | Stop/guided review; defer genuinely topology-rich interpretation to the later topology layer |

No row above is an overall compatibility score. Several dimensions may apply at
once and should remain separately visible.

## Escalation policy: when the user must be involved

Automatic mode is appropriate only when the remaining choices are
crystallographically equivalent under reviewed deterministic rules.

NASolve should switch to guided mode when any of the following occurs:

- more than one non-symmetry-equivalent logical registration remains;
- a proposed recut/split/join/boundary operation is not already covered by a
  reviewed recipe;
- an unexpected complete copy is not equivalent to the other registered
  copies;
- any partial copy is present and its interpretation affects downstream
  chemistry or model choice;
- required logical coverage differs in a way that cannot be explained by a
  reviewed boundary/cut recipe;
- multiple MR candidates pass ordinary MR gates but imply materially different
  cuts, multiplicities or logical-site mappings;
- the MR solution changes the registration interpretation relative to the
  pre-MR scout in a scientifically meaningful way; or
- the mapping begins to depend on topology rather than sequence/connectivity
  correspondence.

Guided mode is not a failure state. It means the crystallographic
representation itself has become part of the scientific result and therefore
deserves an explicit human decision plus richer documentation.

## Reporting escalation

Documentation effort should scale with the scientific importance of the
registration.

- **Identity-like single-copy W case:** compact machine-readable registration
  plus a terse human summary; no interactive interruption.
- **Automatic but non-identity case:** retain a rendered Registration Net,
  mapping table and applied recipe/transform evidence even if the pipeline
  continues automatically.
- **Multicopy case:** report every registered copy and exactly which logical
  mutation/chemistry actions were propagated to each.
- **Partial-copy, ambiguous, or user-guided case:** produce the full
  Registration Net, competing mappings/cuts, symmetry evidence, coverage
  differences, user selections, rejected alternatives and any recut preview.
- **MR rescue case:** retain the original failed candidate, every transformed
  candidate, transformation manifest, MR statistics and the reason the rescue
  branch was attempted/accepted/rejected.

These records should flow into the final dataset/campaign report and later
curation/deposition provenance rather than living only in a temporary setup
screen.

## Logical construct manifest

Dataset intent should ultimately compile to a logical construct manifest. It may
include:

- logical strand IDs and complete sequences;
- logical residue IDs;
- important subranges such as junction arms and sticky ends;
- explicit modified-residue identities;
- terminal-phosphate intent;
- backbone chemistry declarations;
- expected copy-number/symmetry context when known; and
- later, reviewed topology metadata.

All mutation and chemistry requests remain expressed in logical coordinates.
For example:

```text
logical A:12 = 1AP
logical D:1  = 5-prime phosphate
```

Registration translates those requests to the coordinate sites that actually
exist in a specific model or solved ASU.

## Two operating modes

### Automatic mode

Automatic mode is the common path. It should continue without prompting only
when the registration is sufficiently unambiguous under reviewed deterministic
rules.

A normal W model should usually produce an identity-like registration and make
this layer nearly invisible.

Automatic mode may:

- recognize harmless chain renaming/renumbering;
- recognize reviewed chain split/merge patterns;
- recognize a reviewed equivalent ASU cut;
- identify complete repeated construct copies;
- propagate logical mutations to every complete registered copy; and
- apply an already reviewed cut/registration recipe.

Every automatic action remains frozen in provenance and reconstructible in the
final report.

### Guided mode

Guided mode is for a dataset whose crystallographic interpretation itself has
become important.

The user may inspect the proposed registration, choose among non-equivalent
mappings, assign coordinate fragments to logical strands, choose an ASU cut,
mark a fragment as partial/extraneous, or select a reviewed cut recipe.

A guided decision is frozen as run-local registration provenance. It does not
silently change a global NASolve rule. Promotion of a successful run-local
mapping into a reusable lab recipe is a separate explicit action.

The user-facing goal is not to ask the user to rebuild a model manually before
NASolve can proceed. NASolve should present its best deterministic proposal,
explain what is uncertain, and ask only for the smallest crystallographic
decision required to make the mapping authoritative.

## Chosen design rationale

The preferred architecture is intentionally asymmetric: **understand first,
edit only when necessary**.

The design decisions are:

1. **Logical construct identity outranks PDB labels.** Chain names, residue
   numbers and ASU boundaries are coordinate serialization, not construct
   identity.
2. **Registration comes before sequence mutation conceptually.** A mutation such
   as `A:12` must be attached to a logical site before NASolve decides which
   coordinate residue(s) to edit.
3. **Ordinary MR gets an early chance.** A plausible search model should not be
   heavily recut/mutated before Phaser merely to make its labels resemble the
   intended construct. MR often supplies the best oriented coordinate registry.
4. **The actual MR solution is downstream authority.** PostMR must register the
   solved coordinate model again; the pre-MR scout is evidence, not authority.
5. **Representation rescue is a separate branch.** Recutting, chain
   split/join/relabel operations and reviewed boundary adjustments become
   explicit AutoMR/MR-Doctor rescue candidates rather than invisible setup
   edits.
6. **Independent facts stay independent.** Registration, sequence identity,
   coverage, terminal chemistry, copy multiplicity, MR statistics and later
   topology should not be collapsed into one score.
7. **Humans resolve scientific ambiguity, not bookkeeping.** NASolve handles
   deterministic renaming/renumbering/copy propagation automatically and asks
   the user only when genuinely different crystallographic interpretations
   remain.
8. **Every unusual interpretation earns provenance.** The stranger the ASU,
   multiplicity or cut, the richer the report should become.
9. **Successful local knowledge can become a recipe only explicitly.** Guided
   mappings may later be promoted into reviewed lab recipes, but neither one
   successful run nor Campaign Doctor repetition silently changes global rules.
10. **Backward compatibility matters.** Clean W runs should remain fast and
    boring; historical literal `CHAIN:RESID` runs remain readable.

This arrangement gives NASolve useful deterministic "intelligence" without
turning inference into hidden scientific authority.

## Timing: scout, MR, authoritative registration, rescue

NASolve should not require heavy coordinate surgery before ordinary MR when MR
itself may provide the most useful coordinate registry.

### 1. Registration Scout inside AutoMR preflight

Before Phaser, NASolve performs a cheap, non-mutating scout of each candidate
search model:

- literal polymer inventory;
- backbone connectivity;
- possible logical-strand registrations;
- coverage of required logical sites;
- obvious boundary/sticky-end differences;
- candidate complete/partial copy patterns; and
- applicability of any reviewed cut recipe.

For a clean standard W model this should be a fast identity case.

The scout may reject a model whose required logical sites cannot be registered
at all, but it should not require expensive recutting/mutation merely to make a
plausible model cosmetically match the target before MR.

### 2. Ordinary MR first when plausible

If a candidate is scientifically plausible, Phaser should normally see the
preserved candidate coordinates first.

A successful MR solution is valuable evidence: it establishes an oriented
coordinate realization in the recipient diffraction data and may reveal the
actual ASU multiplicity/cut.

### 3. Authoritative ASU Registration after Phaser

Before PostMR mutates anything, NASolve re-runs registration on the actual MR
solution.

This is the authoritative mapping used by downstream chemistry.

It records:

- logical-site -> coordinate-site mapping;
- symmetry operator/translation when a logical continuation crosses the ASU;
- complete and partial construct instances;
- missing/unexpected sites;
- boundary/sticky-end differences;
- multiplicity surprises;
- ambiguity evidence; and
- whether the MR solution changed the interpretation relative to the search
  model scout.

PostMR then applies dataset-level sequence/chemistry to every **complete,
unambiguous registered instance** of each logical site.

For example, a dataset request such as `logical A:12 = 1AP` may resolve after
MR to one coordinate site in an ordinary ASU or to several sites in a
multicopy ASU. The mutation request remains singular in logical intent; the
registration layer expands it deterministically to all complete registered
instances and records that propagation.

Partial or ambiguous instances are never silently mutated as though they were a
complete second copy.

### 4. Registration/Recut Rescue when MR or registration needs it

Some models may require a different crystallographic cut or other reviewed
representation change before they become effective search models.

If ordinary MR fails, or if the scout identifies a known representation problem,
NASolve may create a bounded rescue candidate using an explicit reviewed recipe.

Possible reviewed operations include:

- choose a different equivalent ASU cut;
- split or join coordinate chains;
- relabel or renumber chains/residues;
- trim or restore a sticky-end boundary;
- materialize symmetry-equivalent residues needed for the chosen cut; and
- apply explicitly reviewed boundary chemistry needed by that search-model
  representation.

The original model remains immutable. Every transformed search model is a new
candidate with a transformation manifest and checksum.

This rescue path belongs to AutoMR/MR Doctor reasoning, not ordinary PostMR
target mutation.

## Registration outcomes

Suggested descriptive outcomes are:

- `REGISTERED_COMPLETE`
- `REGISTERED_COMPLETE_MULTICOPY`
- `REGISTERED_WITH_IDENTITY_DIFFERENCES`
- `REGISTERED_WITH_BOUNDARY_DIFFERENCES`
- `PARTIAL_COPY_PRESENT`
- `AMBIGUOUS_REGISTRATION`
- `TOPOLOGY_DIFFERENT`

These are interpretation states, not overall model-quality scores.

A model may simultaneously have, for example, a complete registration plus
sequence differences and a boundary-phosphate difference. The machine record
should retain independent dimensions rather than force every case into one
label.

## Multiplicity

Registration should decompose the solved coordinate set into construct
instances.

Examples:

```text
copy 1: COMPLETE  42/42 logical sites
copy 2: COMPLETE  42/42 logical sites
```

or:

```text
copy 1: COMPLETE  42/42 logical sites
copy 2: PARTIAL   17/42 logical sites
```

A complete second copy may receive the same logical dataset mutation plan after
the registration is verified.

A partial copy is crystallographically important evidence. It should trigger
expanded reporting/guided review rather than be coerced into an ordinary second
copy. Later topology logic may explain such fragments more deeply.

## Coverage and boundary chemistry

Registration success does not certify chemistry.

NASolve should separately audit:

- missing/extra logical sites;
- sticky-end lengths;
- arm lengths and junction boundaries;
- intended chain termini;
- requested terminal phosphates;
- unsupported backbone chemistry; and
- later, topology/connectivity constraints.

Thus a model can be "registered correctly" while still requiring a boundary or
terminal-phosphate correction.

## Multiple PDBs in one dataset

Dataset PDBs are candidate providers, not automatic truth.

When several PDBs are present, AutoMR may registration-scout a bounded candidate
set. Models that cannot represent required logical sites are excluded with a
diagnostic. Eligible candidates may be tried under a preset-declared MR budget.

Automatic selection should use existing scientific MR gates and explicit policy,
not a single composite registration score or raw TFZ alone. A candidate can
have a beautiful registration and still fail MR; another can have weaker
pre-MR correspondence but solve cleanly and become easy to register after
Phaser. MR evidence therefore remains an important part of the bounded
candidate decision.

If multiple successful candidates imply materially different ASU/multiplicity
interpretations, guided review should preserve the alternatives rather than
silently choosing one.

The dataset PDB basename is never itself evidence of construct identity.

## Reviewed cut/registration recipes

Lab-specific representation knowledge should be versioned as data rather than
hard-coded exceptions.

A reviewed recipe may declare:

- source representation/family identity;
- target logical construct representation;
- chain split/merge/relabel rules;
- residue-number transforms;
- symmetry operators/translations;
- cut boundaries;
- allowed sticky-end/boundary transforms;
- explicitly reviewed boundary-chemistry transforms;
- invariants that must remain true; and
- recipe version/checksum.

A recipe must still validate against the actual input model before use.

A guided run may save a run-local mapping. Reusing it globally requires explicit
promotion into a reviewed recipe.

Recipe promotion should capture *why* the mapping is reusable: required
invariants, acceptable source representation, symmetry/cut assumptions, and
validation checks. Campaign Doctor may observe repeated successful mappings,
but repeated observation alone must not silently manufacture a global recipe.

An 8D93-style representation transformed into the standard W representation is
a strong planned validation fixture because it exercises an equivalent ASU cut,
different chain labels, sticky-end boundary change and terminal-phosphate
difference while retaining the same broad geometry.

## Registration Net

The user-facing visualization should be simple, attractive and functional rather
than a second molecular graphics package.

The preferred view is a clean 2-D SVG/HTML schematic with:

- logical strands drawn as rounded ribbons with consistent strand colors;
- residue ticks grouped into ranges rather than one large text table;
- important logical sites shown as labeled dots/badges;
- coordinate-chain fragments drawn above or beside the logical strands;
- soft connecting bands showing coordinate -> logical registration;
- dashed seams for ASU/symmetry cuts;
- compact symmetry-operation labels at seam crossings;
- sticky ends and termini visibly exposed;
- complete repeated copies shown as aligned repeated cards/tiles;
- partial copies shown clipped/dashed rather than pretending they are complete;
- missing logical regions shown as gaps;
- unexpected coordinate fragments shown in a neutral detached lane; and
- modified/boundary chemistry marked with small, restrained icons.

Hover/click details may show, for example:

```text
logical A:12
coordinate M:104
copy 2
symop x-y, x, z + [0,1,0]
identity DA -> target 1AP
```

Guided controls should remain few and direct:

- accept proposed registration;
- assign/reassign a coordinate fragment to a logical strand;
- split or join a proposed fragment;
- choose among proposed equivalent cuts;
- select a reviewed cut recipe;
- mark a fragment partial/extraneous;
- preview a recut; and
- open the corresponding coordinates in Coot.

Coot remains the coordinate editor/viewer. The Registration Net explains and
selects the logical mapping; accepted recut/split/join operations may then be
materialized through controlled Coot/coordinate tooling with full provenance.

The same net should have a static report form suitable for final campaign,
curation and deposition provenance.

## Reporting

Routine identity registrations should generate compact machine-readable
provenance with a terse human summary.

When the mapping is non-identity, multicopy, partial, ambiguous or user-guided,
NASolve should automatically expand the documentation burden.

Planned artifacts may include:

```text
Model/registration_scout.json
Phaser/asu_registration.json
Reports/registration-net.svg
Reports/registration-net.html
```

The final solution/campaign report should retain:

- original candidate model identity/checksum;
- applied registration/cut recipe, if any;
- search-model registration scout;
- MR-solution authoritative registration;
- copy decomposition;
- missing/extra/boundary differences;
- logical-site mutation propagation to coordinate copies;
- user decisions and timestamps;
- transformed candidate checksums;
- symmetry/cut evidence; and
- unresolved ambiguity/partial-copy warnings.

## NAPrep boundary

NAPrep is a separate upstream design/data-management tool, analogous in
separation to NARestraints.

NAPrep may organize design records, sequences, chemistry metadata, raw/processed
dataset folders and externally generated model candidates. If AlphaFold or
another model-generation workflow is used, that invocation belongs upstream in
NAPrep or another provider tool.

NASolve does **not** invoke AlphaFold.

NASolve owns the crystallographic decision tree from frozen dataset/model intent
through AutoMR, registration, PostMR, AutoSol, refinement, campaign management,
Campaign Doctor, final curation/reporting and deposition preparation/submission.
Splitting those downstream responsibilities into another package would discard
or duplicate the exact intent/provenance NASolve already maintains.

## Backward compatibility

This layer must be additive for current clean W workflows.

A standard W run that already has expected chains/sites should produce a trivial
identity-like registration and continue through the existing pipeline without
requiring user interaction.

Historical runs without registration artifacts remain readable under their
existing literal chain/residue semantics.

Hemlock/Moss and later sequence/compatibility layers should eventually consume
logical-site registration when one is present rather than assuming raw
`CHAIN:RESID` equality. That migration should occur only after registration is
validated against controlled fixtures and must preserve legacy report support.

Campaign Doctor should consume these registration-aware facts rather than
re-infer chain correspondence from donor and recipient PDB labels. Differences
can therefore accumulate coherently across solved siblings—sequence,
boundaries, multiplicity, ASU cut and later topology—without letting one
dataset's coordinate serialization become the next dataset's assumed truth.

## Planned validation ladder

1. Identity registration on an ordinary current W model.
2. Chain rename and arbitrary residue-number offset with unchanged geometry.
3. One logical strand split across multiple coordinate chains.
4. Reviewed equivalent ASU cut using the 8D93-style -> W representation.
5. Sticky-end boundary change and terminal-phosphate difference.
6. Two complete registered copies caused by an unexpected ASU multiplicity.
7. One complete plus one partial copy.
8. Multiple dataset PDB candidates with bounded MR attempts.
9. Guided Registration Net correction and exact replay from the frozen manifest.
10. Campaign Doctor consumption of registration-aware donor/recipient facts.

Topology-rich/non-equivalent lattice interpretation remains a later layer.
