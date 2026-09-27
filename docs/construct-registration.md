# Construct registration and the Registration Net

Status: **design contract with core semantics and conservative Scout v1 now
implemented on the Birch development branch; not yet wired into live
AutoMR/PostMR execution.** This layer is intended to make NASolve robust to real
crystallographic coordinate representations without changing the logical
construct intent supplied by the user.

The current machine-readable development policy is
[`construct-registration-intent.json`](construct-registration-intent.json).
Inference-policy changes should update both that record and this document so
later validation can distinguish a code regression from an intentional policy
revision.

## Primary inference domain

The primary target is **designed self-assembling nucleic-acid crystals**, not an
arbitrary biological polymer with unknown composition.

NASolve should normally know the intended strand sequences, modified sites,
sticky ends, termini and other dataset-level construct intent before MR. Those
designed strands are generally short and deliberately chosen to reduce
accidental correspondence ambiguity. That makes registration better constrained
than generic sequence alignment.

This is a useful prior, not permission to force a mapping. Short repeated motifs
can still occur; some three-nucleotide patterns may be constrained to repeat;
and a single-base sticky end can be intrinsically non-identifying. Such cases
must remain able to produce an ambiguous/guided outcome.

The intended direction is therefore **design-aware but explicit**: sequence,
modified-site intent and boundary definitions may later participate as named
evidence when they make a registration unique, but must not become a hidden
similarity score that silently decides between competing crystallographic
interpretations. Scout v1 deliberately does not use sequence similarity to
break chain-assignment ties.

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
| Search-model Scout looks simple but MR output reorganizes the ASU | Re-run authoritative registration on the actual Phaser solution and discard the Scout as downstream authority | Guided review if the solved ASU has ambiguous multiplicity/cut |
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
  pre-MR Scout in a scientifically meaningful way; or
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

### Current Scout v1 implementation boundary

Birch currently implements the pure registration record, checksum-bound
freeze/load provenance, logical-site propagation across complete registered
copies, and a conservative non-mutating Scout for:

- exact logical/coordinate site identity;
- same-named chains with constant residue-number offsets;
- unique whole-chain renames with the same length/residue-number pattern; and
- unique whole-chain rename plus constant residue-number offset.

Scout v1 intentionally refuses to infer split chains, copy multiplicity,
symmetry-dependent cuts, partial copies or topology. It also does **not** use
sequence or modified-site similarity as a tie-breaker.

Birch now additionally records a **descriptive design-evidence matrix** for
every simple chain candidate. It reports target/coordinate residue matches and
mismatches—including intended modified-site differences—but schema semantics
fix `used_for_assignment = false` and explicitly state that identity-match
counts are not a score. This gives guided mode and future reviewed inference a
transparent evidence trail without changing Scout v1's decision rule.

Scout results themselves can now be frozen as checksum-bound
`Model/registration_scout.json` artifacts, including unresolved/ambiguous
cases. A separate pure transition comparator can describe how registration
changes between a search-model stage and a later authoritative MR-solution
registration: copy coverage, complete/partial multiplicity, complete-copy
identity classes and single-copy coordinate realization remain separate
dimensions with no acceptance or PostMR verdict.

The first focused Birch registration checkpoint reported **23 passing tests**
at code head `4452295c3330de6d55bddd75b01be21f39afb222`. The later merged
Birch registration/model-candidate bundle reached **44 focused tests passing**
plus a full NASolve regression of **664 tests and 222 subtests**. Oak's
experimental Scout v2 helper subsequently reached **41 focused tests passing**;
its real-W shadow history is frozen in
[`construct-registration-intent.json`](construct-registration-intent.json).

### Experimental design-aware Scout v2 proposal

Oak adds a separate **experimental, non-runtime** proposal helper to test the
lesson from the renamed real-W validation without changing Scout v1.

The helper evaluates every complete simple one-to-one chain mapping and
classifies each target-identity difference as:

- `DECLARED_TARGET_HISTORY` when the observed residue identity appears in an
  earlier explicit target assignment at that logical site;
- `REVIEWED_PROVIDER_BASELINE` when it matches an explicitly supplied provider
  baseline identity for that logical site; or
- `UNEXPLAINED` otherwise.

It may return a proposal only when **exactly one** complete mapping has zero
unexplained mismatches and every alternative has at least one. It never chooses
the mapping with merely the lowest mismatch count and never constructs a
weighted sequence-similarity score.

This is deliberately not runtime authority:

- it cannot apply its proposal;
- AutoMR/PostMR do not call it;
- repeated/indistinguishable strands remain ambiguous;
- assignment enumeration is bounded and fails closed; and
- provider baseline evidence must remain provenance-bound to the assessed
  provider model and reviewed/provider record; caller-supplied residue-code
  dictionaries are not accepted.

The point of Oak is to test whether categorical design evidence is strong enough
to disambiguate the real W rename case safely before any policy is promoted.

The first renamed-real-W v2 shadow attempt remained `AMBIGUOUS`, which was the
correct fail-closed result for incomplete evidence. Only A:13=DC and B:3=DG had
been supplied; the intended mapping therefore still contained two unexplained
differences. Direct inspection of the actual `MR_frames/5W6W/C_G.pdb`
provider verified the complete relevant identity set:
`A:12=DC`, `A:13=DC`, `B:3=DG`, `B:4=DG`.

Repeating the same shadow case with all four verified provider identities
produced exactly one zero-unexplained proposal:
`A->M, B->N, C->P, D->Q`. It contained 38 exact identities and 4
`REVIEWED_PROVIDER_BASELINE` differences; every alternative retained at least
10 `UNEXPLAINED` mismatches. The helper still reported
`runtime_authority = false`. This validates the experimental categorical rule
on the real rename nuisance case without promoting it into runtime authority.

Oak's next code slice now binds that provenance explicitly. Scout v2 no longer
accepts an ad hoc site->code dictionary. Optional provider-baseline evidence must
arrive as the actual assessed provider model plus NASolve's existing
model-provider record. The helper accepts only standard frame-catalogue
provenance, requires exact logical-site coverage, verifies that the provider
selector matches the assessed source model, derives every residue code from the
provider coordinates, and records the source-model SHA-256 in the returned
baseline evidence.

This provenance-bound implementation remains experimental and non-runtime.
The focused Construct Registration suite now passes **43 tests locally** at
checkout/test head `507745a0b7166f05229f6c3501d5e1f694db93e2`; the underlying
source-behavior head remains
`c515a37dc41fa8bb1935d2c80c825ebef8153177`. The two added guardrail tests
explicitly reject incomplete provider target coverage and provider-selector/source
mismatch.

The renamed real-W shadow case has now also passed through the new
`provider_assessment + model_provider` interface with exactly one
zero-unexplained A->M/B->N/C->P/D->Q proposal (38 exact + 4 provider-explained;
alternatives 12/11/16/17/10 unexplained). Provider evidence was bound, no caller
residue-code dictionary was supplied, and `runtime_authority` remained false.
Because historical ED `run_011` predates the structured provider field, the
shadow script reconstructed only provider facts first verified independently
from the run's model path, model_source and recorded model SHA-256, then checked
that SHA against the assessed current `C_G.pdb` before Scout ran.

That historical bridge was then removed from the validation entirely: a fresh
current-schema ED `run_013` AutoMR preflight was created from the same
scientific intent and supplied native structured `model_provider` provenance.
Repeating the renamed-W shadow case directly from `run_013` reproduced the
same unique zero-unexplained mapping with provider binding true, caller codes
false and `runtime_authority = false`.

### Guided mode

Guided mode is for a dataset whose crystallographic interpretation itself has
become important.

The user may inspect the proposed registration, choose among non-equivalent
mappings, assign coordinate fragments to logical strands, choose an ASU cut,
mark a fragment as partial/extraneous, or select a reviewed cut recipe.

A guided decision is frozen as run-local registration provenance. It does not
silently change a global NASolve rule. Promotion of a successful run-local
mapping into a reusable lab recipe is a separate explicit action.

Birch now implements the first UI-independent guided primitive for simple
ambiguous Scout cases: an explicit logical-chain -> coordinate-chain selection
can be applied only if every chosen pair was already present in Scout's frozen
candidate set. The selection must cover every logical chain and remain
one-to-one. This helper does not choose for the user, edit coordinates, infer
split chains/symmetry/topology, or promote the result into a global recipe.

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
   solved coordinate model again; the pre-MR Scout is evidence, not authority.
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

## Timing: Scout, MR, authoritative registration, rescue

NASolve should not require heavy coordinate surgery before ordinary MR when MR
itself may provide the most useful coordinate registry.

### 1. Registration Scout inside AutoMR preflight

Before Phaser, NASolve performs a cheap, non-mutating Scout of each candidate
search model:

- literal polymer inventory;
- backbone connectivity;
- possible logical-strand registrations;
- coverage of required logical sites;
- obvious boundary/sticky-end differences;
- candidate complete/partial copy patterns; and
- applicability of any reviewed cut recipe.

For a clean standard W model this should be a fast identity case.

The Scout may reject a model whose required logical sites cannot be registered
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
  model Scout.

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

If ordinary MR fails, or if the Scout identifies a known representation problem,
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

When several PDBs are present, AutoMR may run Registration Scout on a bounded candidate
set. Models that cannot represent required logical sites are excluded with a
diagnostic. Eligible candidates may be tried under a preset-declared MR budget.

Birch now implements the **read-only precursor** to that future behavior without
changing current AutoMR selection. A separate candidate-inventory module:

- enumerates every top-level dataset PDB;
- retains invalid PDBs with diagnostics instead of hiding them;
- records SHA-256 and byte size for every candidate, valid or invalid;
- computes one stable fingerprint for the entire candidate set; and
- can run conservative Registration Scout independently on each valid candidate
  while leaving `selection = null`.

Current AutoMR behavior is intentionally unchanged: a nonstandard dataset with
multiple unselected PDBs still stops as ambiguous. Candidate inventory/scouting
does not authorize MR and registration status is explicitly not an MR-quality
score.

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

## Registration Net and Topo Net

The user-facing visualization should stay simple, attractive and functional
rather than becoming a second molecular graphics package.

The general **Registration Net** remains the ordinary mapping view. It explains
how logical construct sites map onto one coordinate realization and is useful
for renamed chains, numbering offsets, split fragments, copy multiplicity,
partial copies and guided registration.

The preferred Registration Net is a clean 2-D SVG/HTML schematic with:

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

### Topo Net: explicit periodic-framework surgery mode

**Topo Net** is a framework-specific extension of Registration Net, not the
default registration UI. It may be invoked only by explicit user/campaign intent
for a designed periodic self-assembling framework. NASolve must not infer
"framework topology mode" merely from a crystal structure or campaign
membership.

Topo Net should show one central ASU plus only the symmetry mates that actually
connect to it. Its underlying preview model is a periodic molecular graph rather
than a PDB serialization. Residue/fragment instances retain logical identity,
coordinate identity, symmetry operation/unit-cell translation and current ASU
ownership. Edge types remain explicit, for example:

- covalent backbone continuity;
- designed sticky-end/pairing connectivity;
- symmetry/ASU correspondence; and
- later reviewed topology-specific relationships.

A reslice changes which symmetry-equivalent residues belong to the chosen ASU
representative; it does not move the physical periodic object. The preview must
recompute chain decomposition, exposed sticky ends, termini, logical mapping,
expected backbone continuity, mutation/chemistry propagation and downstream
restraint consequences immediately.

Useful Topo Net actions include:

- move an ASU seam past a residue;
- move a symmetry-equivalent fragment from one side of the ASU representation
  to the other;
- split/join/relabel/renumber coordinate chains;
- move a **true chemical nick** only through an explicitly stronger operation;
- inspect the symmetry mate that completes one periodic connection;
- preview newly exposed sticky ends or termini; and
- open the affected residues/symmetry mates in Coot.

### Representation seams ("false nicks") versus chemical nicks

An ASU cut may force a chemically continuous strand to be serialized as two
coordinate-chain fragments. This is a **representation seam**, informally a
"false nick": the coordinate file is broken at the ASU boundary, but the logical
polymer remains covalently continuous through a crystallographic symmetry
operation.

Representation seams and true chemical nicks must never share semantics.

For a representation seam:

- logical backbone continuity remains present across the recorded symmetry
  operation;
- the continuation phosphate remains part of the continuous backbone even when
  it appears at the start of a coordinate chain;
- that phosphate must not be reinterpreted as an ordinary free 5-prime terminus
  or receive terminal-OP3 chemistry merely because the PDB serialization starts
  a chain there; and
- moving the seam changes ASU representation, not construct chemistry.

A true chemical nick instead changes the covalent graph and creates real
termini. Moving such a nick can change phosphate/terminus intent and therefore
requires explicit user intent plus downstream chemistry/restraint regeneration.

### Tile design, periodic object and ASU are distinct layers

Topo Net should be biased toward the actual family of problems NASolve is being
built for first: **designed 3-D DNA lattices / periodic nucleic-acid
frameworks**. Generalization to other polymer crystals can come later. Avoid
weakening the first implementation by pretending every crystallographic object
has the same design semantics.

For these systems, four distinct state layers should remain explicit:

1. **Input strand inventory** — the real synthesized/declared full strand
   sequences, modifications and intended stoichiometry/copy counts when known.
2. **Tile hypothesis** — the intended or inferred finite assembly unit:
   junctions, sticky ends, strand connectivity, internal nicks/termini and
   design-level multiplicity. This is usually supplied by the user/project, but
   it may be incomplete or wrong.
3. **Periodic crystal graph** — the actual repeating molecular connectivity
   implied by the solved coordinates plus crystallographic symmetry.
4. **ASU serialization** — one coordinate-file cut of that periodic object,
   including representation seams, chain labels, residue numbering and the
   number/fragments of tile copies that happen to fall inside the ASU.

These layers must not be collapsed. In particular:

- an ASU may contain two copies of a triangle tile without redefining the
  triangle itself;
- symmetry may slice a tile through junctions, sticky ends or ordinary backbone
  segments;
- a representation seam can create a coordinate-file nick that is not a
  chemical nick;
- a declared strand may be absent from the observed crystal structure;
- the crystal may use a different effective stoichiometry/copy number from the
  input recipe; and
- in difficult cases, the scientifically meaningful "tile" may emerge only
  after the periodic graph is understood.

Topo Net should therefore treat the tile as a **hypothesis with provenance**,
not a permanent truth. A tile record may be:

- `DECLARED` — supplied explicitly by the user/project;
- `INFERRED` — reconstructed uniquely from full input strands plus observed
  periodic connectivity under reviewed rules;
- `EMERGENT` — proposed from the solved periodic graph because the observed
  assembly cannot be represented faithfully by the declared tile without
  contradiction; or
- `UNRESOLVED` — more than one non-equivalent tile interpretation remains.

A declared tile always remains visible as experimental intent even if the
observed crystal suggests another organization.

### Full-strand input and tile reconstruction

When the user can provide the actual complete strand list, that strand inventory
should outrank ASU-derived chain sequences as design evidence. ASU chain
sequences are coordinate serialization; they may be fragments or symmetry-cut
pieces of the real strands.

A future Topo Net compiler may therefore attempt:

```text
full input strands
    -> candidate strand-to-periodic-graph mappings
    -> tile hypothesis/hypotheses
    -> ASU representation
```

This must remain fail-closed. It must allow:

- a supplied strand that is not observed in the final structure;
- several copies of one input strand;
- fewer/more effective tile copies than the input recipe expected;
- one input strand split among ASU/symmetry fragments;
- different tile hypotheses compatible with the same local sequence evidence;
  and
- the possibility that no faithful finite tile decomposition is yet known.

The goal is not to force nature back into the synthesis spreadsheet. It is to
use the spreadsheet as high-authority experimental intent while allowing the
solved periodic object to disagree visibly.

### Topo Surgeon / Topo Doctor

Topo Net surgery will sometimes produce locally awkward coordinate geometry,
especially after mutation, reslicing or chain reconstruction from imperfect MR
models. These failures are not all equivalent and should not be hidden inside a
single deterministic "fix" command.

A future bounded **Topo Surgeon** (or Topo Doctor) may consume one immutable
surgery proposal and try a small declared repair budget. Candidate operations
might include reviewed combinations of:

- exact symmetry materialization without coordinate relaxation;
- local mutation before versus after seam materialization;
- one-residue Coot RSR at the affected phosphate/backbone junction;
- a slightly broader local Coot repair only after the one-residue variant fails;
- alternate reviewed split/join orderings; and
- later, experimentally validated symmetry-spanning bond policies.

Each repair attempt must be a separate immutable branch with before/after
coordinates, exact Coot/Phenix actions and stopping reason.

Comparison must be chemically local rather than merely numerical. Candidate
repairs should be audited for, as applicable:

- Phenix bond/angle outliers and local `.geo` interpretation;
- phosphate orientation and cross-symmetry clashes;
- base-plane integrity;
- base-pair/stacking geometry from reviewed NARestraints targets when
  applicable;
- sugar/backbone distortion;
- unintended movement of neighboring or remote atoms;
- preservation of residue/deposition identity; and
- whether the intended periodic connectivity is actually realized.

No single composite "topology score" should silently pick a result. A reviewed
policy may apply hard gates and then present surviving candidates for
inspection.

If the bounded repair budget cannot produce a trustworthy result, expert manual
Coot work is an expected fallback, not a pipeline failure. Topo mode already
implies an expert user. NASolve should open the exact model/maps/symmetry context
needed for repair, instruct the user what seam/fragment requires attention, then
allow the user to save/import a corrected PDB as a new immutable checkpoint.
That manual model must retain the failed automated attempts and user-review
provenance rather than erasing them.

### Materialization, Coot repair and Phenix enforcement

Topo Net itself should remain preview/intent logic. Applying a reviewed surgery
writes an immutable transformation manifest first. Coot/controlled coordinate
tooling then materializes the selected symmetry-equivalent coordinates,
split/join/relabel/renumber operations and any approved local coordinate repair.
The resulting model is re-assessed and passed through Phenix interpretation
before refinement.

Some recuts may place a phosphate and its symmetry-related O3-prime partner too
far apart for Phenix to recognize/refine the intended backbone cleanly. A
single-residue Coot real-space-refinement repair near the seam is therefore a
plausible future primitive, but it must be learned empirically before
automation. Validation should measure which atoms move, confirm that the
intended connection becomes geometrically sensible, verify that unrelated
coordinates are preserved, and re-run Phenix geometry interpretation after
every repair.

Likewise, NASolve must not automatically force a symmetry-spanning covalent bond
yet. Phenix supports custom bonds to symmetry copies, but the full
symmetry-spanning phosphate angle geometry must be validated separately. A
bond-distance restraint without trustworthy O3-prime-P-O angle control may
still permit a locally wrong phosphate orientation or clash. Until a dedicated
live experiment demonstrates safe behavior, symmetry-bond enforcement remains
experimental-only and visibly provenance-tagged.

### Blind topology-surgery validation

The preferred end-to-end Topo Net fixture is **8D93 -> 3GBI-style
representation without coordinate cheating**. The surgery engine receives the
8D93 periodic object, crystallographic symmetry and requested logical/cut intent;
it must not read 3GBI coordinates while generating the transformed model.
3GBI is used only afterward as an independent validator of the resulting
periodic graph, chain boundaries/sticky ends and symmetry-equivalent coordinate
representation.

Coot remains the atomic coordinate editor/viewer throughout. Registration Net
and Topo Net explain/select logical and topological intent; Coot materializes
local coordinate consequences; Phenix audits/enforces the resulting chemistry
and geometry.

Both nets should have static report forms suitable for final campaign, curation
and deposition provenance.

## Reporting

Routine identity registrations should generate compact machine-readable
provenance with a terse human summary.

When the mapping is non-identity, multicopy, partial, ambiguous or user-guided,
NASolve should automatically expand the documentation burden.

Planned artifacts may include:

```text
Model/registration_scout.json
Phaser/asu_registration.json
Model/topology_surgery_manifest.json
Reports/registration-net.svg
Reports/registration-net.html
Reports/topo-net.svg
Reports/topo-net.html
```

The final solution/campaign report should retain:

- original candidate model identity/checksum;
- applied registration/cut recipe, if any;
- search-model Registration Scout;
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
4. Disposable symmetry-spanning phosphate experiment: compare no symmetry bond
   with an explicit Phenix symmetry-operation bond and inspect full local
   geometry/nonbonded behavior before defining any automatic bond policy.
5. Several disposable Coot single-residue RSR seam repairs with before/after
   coordinate and Phenix-interpretation audits.
6. Blind 8D93 -> 3GBI-style Topo Net surgery with 3GBI withheld until
   post-transform validation.
7. Sticky-end boundary change while preserving representation-seam versus true
   chemical-nick semantics.
8. Two complete registered copies caused by an unexpected ASU multiplicity.
9. One complete plus one partial copy.
10. Multiple dataset PDB candidates with bounded MR attempts.
11. Guided Registration Net correction and exact replay from the frozen manifest.
12. Campaign Doctor consumption of registration-aware donor/recipient facts.

Topology-rich/non-equivalent lattice interpretation remains a later layer.
