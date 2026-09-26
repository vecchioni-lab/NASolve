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
not a single composite registration score or raw TFZ alone. If multiple
successful candidates imply materially different ASU/multiplicity
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
