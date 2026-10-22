# NASolve architecture

NASolve orchestrates external crystallographic programs; it does not reimplement them.

## Runtime precedence

Phenix is resolved in this order:

1. `--phenix-root`
2. `NASOLVE_PHENIX_ROOT`
3. saved user configuration
4. current `PATH`
5. validated installations in standard platform locations
6. a clear request to run `nasolve configure phenix PATH`

When multiple standard installations exist, NASolve selects the highest validated version.
An automatically discovered path is saved and revalidated on use. Each structure-solution report will record the exact
Phenix version and executable paths used.

Coot uses the same pattern independently: a one-run path, `NASOLVE_COOT`,
saved configuration, `PATH`, then bounded standard locations. Validation checks
both `coot --version` and the embedded Python API required by headless mutation.

## AutoMR input contract

`nasolve automr DATASET` uses one shared `nasolve.txt` schema for standard and
nonstandard models. The file records user intent; computed paths, checksums,
model statistics, and resolved ligand codes belong in the run log and JSON
report.

Standard example:

```ini
[automr]
mode = standard
frame = W
pair = D:T
```

Nonstandard example:

```ini
[automr]
mode = nonstandard
model = custom_model.pdb
sequence_file = construct.fasta
mirror = false

[mutations]
A:3 = 5IU
```

`sequence_file` accepts chain-labelled FASTA or `CHAIN = SEQUENCE` records.
Inline `[sequences]` remains an exclusive alternative. The effective sequence
is frozen inline in the run snapshot, with the source path and checksum retained
in the report.

If `nasolve.txt` is absent, the command infers a nonstandard run from exactly
one top-level PDB, or takes a standard frame from `-W`, `-3GBI`, or `--frame`.
It then writes the minimal canonical file. Existing input is never overwritten.
CLI frame and pair values override file values and are captured in the frozen
run snapshot.

Current standard models are found in repository `MR_frames/`, through
`NASOLVE_MR_FRAMES`, or with `--frames-dir`. Approved models will later move
into package data for installed releases. `W` and `5W6W` resolve to the same
frame; absence of an explicit standard frame never defaults to W.

The model catalogue is organized by frame and ordered pair:

```text
MR_frames/
├── 5W6W/
│   ├── A_G.pdb
│   ├── C_G.pdb
│   └── D_F.pdb
└── 3GBI/
    └── C_C.pdb
```

Names use `FIRST_SECOND.pdb`, where each component is either a configured alias
or a literal NARestraints ligand code. Selection compares the resolved ligand
codes, not just filename spelling. Thus `D_F.pdb` matches either `D:F` or
`1AP:DF`. The deterministic fallbacks are `5W6W/C_G.pdb` and
`3GBI/C_C.pdb`. An exact pair model needs no pair mutation; a fallback records
the requested post-MR mutation. Missing fallbacks, malformed names, and
duplicate exact matches stop the run. An unrelated catalogue entry with an
unrecognized ligand token is skipped and recorded as a warning; it does not
block a valid requested pair. Requesting that unknown token still fails normal
ligand validation.

Every preflight receives an isolated directory:

```text
DATASET/AutoMR/run_001/
├── nasolve.input.txt
├── automr.log
├── report.json
└── Model/
    ├── source_model.pdb  # only when mirroring
    ├── input_model.pdb
    └── assessment.json
```

Adding `--execute` continues that same frozen run with an isolated Phaser
directory:

```text
DATASET/AutoMR/run_001/Phaser/
├── phaser.eff
├── phaser.log
├── PHASER.1.pdb
├── PHASER.1.mtz
├── mr_solution.pdb
└── mr_solution.mtz
```

The generated PHIL defines exactly one explicit ensemble named
`nasolve_model`; NASolve does not also use Phaser's `model` shortcut. It sets
`use_hetatm = True` and an explicit model RMSD of 1.0 A for compatibility with
Phenix builds that require either RMSD or fractional identity. It supplies one
NA composition using the model checker's polymer-residue count (`nres`), and
searches for one copy in H3/R3. The guarded
P1 shunt sets both composition and search copies to three. Phaser's original
outputs remain untouched, while stable `mr_solution` copies identify the
result selected for the next layer.

Without mirroring, the copied model is checksum-verified, so HETATM records and
all other bytes are preserved. With `--mirror` (or `mirror = true`), NASolve
copies the untouched source into the run, calls
`restraints.mirror_pdb.mirror_pdb`, and assesses/checksums the transformed
`input_model.pdb` that Phaser will consume. The mirror is rejected if atom,
polymer-residue, chain, or HETATM inventories change unexpectedly.

Residues written as HETATM whose residue names occur in the
NARestraints ligand library are counted as modified polymer residues, not as
detached ligands. This keeps chain lengths correct for modified nucleotides
while retaining separate counts for all HETATM atoms and nonpolymer hetero
residues. Full sequences must match the resulting model-chain residue count,
and explicit mutation targets must exist. Mutation precedence is full sequence,
standard pair, then explicit mutation.

A standard-frame input may additionally declare `force = FIRST:SECOND` to
override **NARestraints pair-recipe classes only** for the designed standard
pair. This is orthogonal to residue identity and model selection. For example,
`pair = G:Z` plus `force = G:C` keeps the prepared residues G/Z while using
the G:C H-bond recipe at the frame's designated pair sites. The override is
site-scoped, frozen in provenance, and must not affect neighboring template
pairs or rewrite coordinate residue names.

### Proposed model input contract

**Future scope; no new input mode is implemented by this document.** The
current search-model reader accepts PDB; prepared-nonstandard campaigns require
a complete chain-labelled sequence target. A collaborator-supplied AlphaFold
coordinate CIF without a separate sequence file motivates two independent
extensions: accept **coordinate mmCIF and PDB**, and allow an explicitly
declared **trust-model mode** without a separate sequence target. That mode is
format-neutral; no CLI flag or configuration spelling is committed yet.

Preserve the exact supplied model and its hash. Validate the coordinate format,
model/assembly selection, chain/residue/atom identifiers, alternate conformers,
modified component identities and connectivity before execution. A component
dictionary CIF is not a coordinate mmCIF. When an external tool needs a converted
format, freeze a separate derivative with an explicit identifier and assembly
mapping; stop the affected operation if the required representation cannot be
preserved unambiguously. Never truncate identifiers or select an assembly
silently.

Trust-model mode declares that the supplied coordinates define the intended
working model; it does not establish independent sequence agreement or final
structural correctness. Record `sequence independently unverified` explicitly,
skip sequence-driven mutation/reconstruction, and gate only operations needing
an independently supplied sequence. Missing sequence must not select this mode
implicitly. Keep ordinary model integrity, MR, crystallographic symmetry,
chemistry, reflection and Free-R validation. Existing explicit sequence inputs
remain authoritative when provided under the corresponding sequence-driven
mode. Implementation and blind-test ordering belong in the
[development handoff](development-handoff.md).

### Dataset and symmetry discovery

Dataset discovery currently accepts the usual autoPROC/STARANISO naming variants
rather than renaming raw inputs. It prefers a unique MTZ whose
punctuation-insensitive name contains both `staraniso` and `alldata`, falling
back to the only top-level MTZ when there is exactly one. Metadata is the unique
case-insensitive `Data_1*.cif`; multiple candidates stop the run. The current
runtime also requires `summary.html`.

These companion-file requirements are an **input-adapter limitation**, not a
scientific invariant. The durable architecture should distinguish the reflection
payload from optional/richer processing metadata.

Future input adapters should compile source-specific material into one frozen
internal crystallographic input record with independent capabilities:

- `mr_ready`: observations + cell/symmetry sufficient for Phaser;
- `refinement_ready`: validated refinement observations + authoritative Free-R;
- `anomalous_ready`: complete anomalous arrays plus wavelength/element context;
- `deposition_ready`: sufficient collection/processing metadata for downstream
  curation/deposition.

AutoPROC/STARANISO + `Data_1*.cif` + `summary.html` is the first rich adapter.
Generic MTZ should become another adapter without requiring Global Phasing
filenames. SCA/Scalepack should also be admissible as a direct MR reflection
source because Phenix can consume it for molecular replacement. The original
SCA remains the frozen authoritative source. If a downstream stage later needs
an MTZ-style array container, NASolve may derive one under a separate immutable
conversion record/checksum rather than making conversion a prerequisite for MR.
Downstream stages consume the frozen internal record/capabilities rather than
branching on the name of the upstream processing suite.

A missing capability should disable only the dependent stage. In particular,
missing deposition metadata must not invalidate an otherwise legitimate
MR/refinement dataset, while missing/ambiguous Free-R must still block guarded
refinement unless an explicit future policy safely creates and freezes one.

The symmetry gate applies only to standard W/3GBI recipes. NASolve compares:

1. the MTZ file symbol, number, and matrix symbol reported by
   `phenix.mtz.dump`;
2. every explicit space-group value in `Data_1*.cif`; and
3. only the final (bottom-most) `Spacegroup name` entry in `summary.html`.

Earlier indexing and POINTLESS alternatives in the HTML are ignored. `H 3`,
`H3`, `R 3`, `R3`, and the MTZ matrix form `R 3 :H` are accepted as one
equivalent class and use one MR copy. The exact MTZ label is retained in the
report as a required final-output patch after structure solution. A genuine P1
standard run stops by default; `--allow-p1-standard` records a strong red flag
and plans three MR copies. Other groups and disagreements between authoritative
sources stop the run. Nonstandard mode does not apply this symmetry rule.

## Pipeline gates

1. Validate and freeze AutoMR input; optionally mirror the search model; assess
   the exact model supplied to Phaser.
2. Run Phaser in an isolated `Phaser/` directory without stripping heteroatoms.
3. Classify the selected model's final TFZ-equivalent (or unambiguous available
   translation score): `>= 8.0` pass; `7.0–7.99` review; `< 7.0` fail.
4. `nasolve postmr RUN` applies supported site changes, builds the restraint
   stack, and runs ReadySet with hydrogens disabled. CIF Doctor records
   read-only, report-only assessments before dictionary-based mutation, before
   ReadySet and after effective-dictionary selection. These receipts preserve
   the existing continuation gates and do not automatically prepare/adopt a repair.
5. If PostMR finds nucleotide-bound I, Br, or Se, `nasolve autosol RUN` performs
   guarded MR-SAD phasing and validates at least one heavy-atom site against
   the model under crystallographic symmetry.
6. `nasolve autorefine RUN` performs one quiet five-cycle default refinement,
   validates the output model and statistics, and appends an immutable
   checkpoint.
7. `nasolve refine-doctor RUN` audits a selected refinement and, when safe,
   runs a finite set of sibling diagnostic branches without changing the
   current checkpoint.

The default command still stops after step 1. `nasolve automr ... --execute`
runs step 2 and applies step 3. A passing run exits 0; TFZ 7.0–7.99 is retained
for review and exits 3; failure or missing output exits 4.

Score authority follows the selected numbered Phaser PDB and its matching MTZ.
Read the final `TFZ==` and final LLG from that model's solution annotation;
initial `TFZ=` values and scores from other models are not substitutes. The
report records the score kind, source and raw annotation. A headerless legacy
output may use an unambiguous single-solution log fallback; conflicting or
unassociated scores cannot authorize progression. See the
[Phenix annotation reference](https://www.phenix-online.org/documentation/reference/phaser.html#annotation).
This corrects the October 11 GeoTest under-gating without changing thresholds
or rewriting historical runs.

## PostMR contract

PostMR is deliberately a separate command so an accepted Phaser result can be
inspected and rerun deterministically before refinement. It refuses to
overwrite an existing `PostMR/` directory. `MR_SUCCESS` is accepted;
`MR_REVIEW` requires an explicit override; other statuses stop.

The W-frame manifest assigns requested pair roles to `A:12` and `B:4`.
Canonical DNA/RNA changes use a generated headless Coot script. Supported
modified nucleotides use a canonical-parent mutation followed by dictionary
monomer construction, overlap, and residue replacement. Coot runs with its
backup directory redirected beneath the run and removes hydrogens before
writing. Full sequences expand over the frozen per-chain residue inventory;
application precedence is sequence, standard pair, then explicit mutation.
Every ordinary base change restores the pre-Coot sugar/phosphate coordinates.
For mutations outside the curated registry, `ligand_definition` requires one
NARestraints record and derives a Coot construction parent from `Sugar Type`
and the recognized `Source sheet`, with `Base Analog` as the category fallback.
`ligand_dictionary` prefers a local `ligands/CODE.cif`; otherwise, for registered
non-curated components, it uses the CCD library beside the configured Phenix
ReadySet executable. Symlink aliases count as one resolved source; separate
files remain ambiguous even if their bytes match. No network retrieval or
alternate-installation search occurs. The generic dictionary check verifies
`_chem_comp.id`, while curated entries retain their explicit topology checks,
local precedence and missing-file guard. Raw CCD graphs still need usable
numerical restraints from ReadySet before `POSTMR_READY`. The existing local
OHU route remains available without implying general topology or atom-mapping
inference. A construction parent is not necessarily the official CCD parent.

For mirrored runs, canonical targets are translated to the NARestraints L-side
codes (`0DA`, `0DC`, `0DG`, `0DT`, and RNA equivalents). Exact mirrored models
therefore are not accidentally mutated back to D chemistry. A required
mirror-side sequence change stops until the guarded
unmirror/Coot/remirror construction path is implemented.

For supported dictionary modifications, Coot also writes a canonical-parent
snapshot. NASolve copies the coordinates, occupancies, and B factors of every shared
atom back into the replaced residue and requires the complete sugar/phosphate
atom set to survive. Thus dictionary overlap positions only the new chemistry;
it cannot rotate or curl the existing phosphate. The restoration inventory is
recorded in the run report.

The returned Cedar 16 evidence demonstrates a limitation of this legacy
same-name/element restoration: it introduces 55 captured threshold crossings,
and an offline replay reproduces the restored model byte for byte. Shared
atom names do not establish semantic base correspondence or compatible local
geometry. The explicit Cedar 17 attached-fragment candidate keeps the existing
scaffold and moves a complete graph-selected base together, with unsupported
graphs visibly refused. Its installed native mechanics and the separate
source-recovered DF definitions now pass their checked mechanics, with charge readback still unsupported. A
separate bounded fixed-definition geometry trial records numerical stopping
and round-trip evidence. Its serializer maps exact atom identities across
native/PDB order changes while preserving original records; verified saved
endpoints can resume the native postcheck without another optimization. Full
scientific qualification remains under review. Cedar 20 shows that fresh native
managers can add distance-filtered hydrogen bonds despite unchanged input
bytes. Read-only attribution preserves the old exact comparison and separately
records fixed-manager endpoint equivalence; it changes no native gate.
It is separate from production PostMR. See the
[restoration diagnostic](cif-doctor.md#separate-attached-fragment-restoration-candidate)
and [current handoff](development-handoff.md).

Dictionary resolution follows mutation actions. Curated components present in
the prepared model are also collected even when unchanged, so their CIFs and
`component_identity` entries survive a no-op mutation plan. This does not imply
automatic resolution of every pre-existing noncurated residue. Generic
definitions add no inferred sulfur substitutions or ring-substituent rules.

The registry also declares exact parent/target atom substitutions. `DE`, `DF`,
and `S6G` place sulfur along the canonical `C-O` vector, use the transformed
dictionary model only for the reviewed C-S bond length, and inherit occupancy
and B factor from the replaced oxygen. This prevents an otherwise valid Coot
graph overlap from placing the one new sulfur atom on the wrong side of a base.
`C38` and `5IU` use the same guarded construction with parents `DC` and `DT`.
Their iodine is placed along the external bisector defined by the mapped
`C4-C5-C6` ring atoms, using the C-I distance from the dictionary's ideal
coordinate set and the parent `C5` occupancy and B factor. The transformed Coot
monomer is not trusted for the halogen bond length.


A separate [explicit membership diagnostic](cif-doctor.md#explicit-narestraints-membership-diagnostic)
now compiles frozen pair/stack declarations through NARestraints recipes and
mapped base planes, then suppresses competing native secondary-structure terms.
It checks exact membership at two saved coordinate sets without optimization.
Both returned Phenix interpretations pass exact membership checks; geometry
qualification remains open and this is not integrated into ordinary PostMR.

Cedar 22 adds a separate bounded trial from that verified endpoint, using the
same dictionary/compiled-PHIL bytes. An opt-in fixed-policy inventory extends
pre-minimization matching to native controls and origin IDs; native PDB readback
also requires the same policy/APIs and every original static proxy. The trial
records stopping, gradients and full-precision versus rounded coordinates. It
does not rediscover pairs or transfer Cedar 19/20 energies to the new objective.
Returned Cedar 22 passes all 17 native readback checks and preserves the fixed
manager through optimization. The objective decreases, but a line-search error
at 905 iterations retains NOT_CONVERGED_ERROR. Scientific qualification remains
open, including CGY–DX pairing and local angle discrepancies.

The separate Cedar 23 gradient audit reuses Cedar 22's exact initial manager
and numerical-source fingerprints. It evaluates saved endpoints under the full
fixed policy plus isolated category controls, comparing analytical directional
derivatives with central differences at four steps. Repeat/additivity and
neighbour-count evidence distinguish sampled numerical inconsistencies without
altering definitions or native equality checks. Existing CIF Doctor checks and
generic outlier-selected distance groups accompany the audit. No optimization,
model change or scientific approval occurs. Returned Cedar 23 matches all
prerequisites and records stable sampled parallelity-gradient disagreement at
both precisions; the other six families pass sampled checks. Independent plane
energy/derivative calculations and a public CCTBX accumulation-loop model
indicate missing second-plane gradient contributions. Cedar 24 reproduces
that defect in the installed path; any causal role in the prior line-search
failure remains open. NARestraints policy and exact native gates are preserved.
Cedar 24 adds that isolated installed check: complete per-restraint gradients
are scattered by atom identity and compared with singleton/full-container and
manager gradients, both saved cases and both plane orders. Tilted equal/unequal
controls test the same APIs without residue definitions. Source availability
and binary identity are recorded separately. Returned native execution
verifies all 732 payloads and all sampled single-restraint derivatives, while
accumulation fails every tested order. The installed loop-bound model exactly
reproduces the saved accumulation vectors. Recombining complete plane
contributions explains all earlier sampled discrepancies without new energy
evaluations or coordinate changes.

Cedar 25 adds an explicit NASolve-local evaluation adapter: retain the native
unnormalized energy and full gradient, subtract the native accumulated plane
gradient, and add every original single-restraint i/j contribution by atom
index. It changes no native proxy, parameter or installed file and works as
an identity operation when native accumulation already agrees. Symmetry-bearing
planes and special positions are refused. This opt-in audit is separate from
production PostMR/refinement. Fresh four-step directional checks cover the
initial coordinates and both saved endpoints under the full objective and seven
category controls, with exact source/static-constraint gates and preserved raw
baselines. Returned Cedar 25 verifies 4,101 evaluations: both saved endpoints
pass all 168 sampled directions; the initial case retains six failures in
the full/parallelity terms. A spectral reference plus the installed header's
normal-orientation sign handling reproduces the remaining initial gradient.

Cedar 26 adds an opt-in plane-order policy to the same evaluator. It consumes
the original first-plane derivative and a native swapped proxy copy's
first-plane derivative for the other side. It checks every copied parameter
and both residuals, scatters all contributions, subtracts the old native
container gradient and leaves the full native energy untouched. The manager's
proxies are never replaced. The existing accumulation-only policy remains the
default. All three raw/captured plane arrays are matched before fresh global
and per-plane derivatives. Both orders, 4/4–4/6–6/4 controls and 30-degree rigid
rotations test the general policy without residue allowlists. Returned Cedar 26
passes all 504 global/category and 1,080 corrected per-plane directions. Native
complete gradients reproduce the four initial sign cases and rotated controls;
the corrected gradients retain order/rotation invariance and unchanged energy.

Cedar 27 explicitly supplies that qualified evidence to the existing bounded
fixed-geometry engine. A small verifier recomputes the stored derivative samples
before optimization. Exact correction-source identity, native sources, static
constraints and the complete corrected initial gradient must match Cedar 26.
The trial starts from the original initial coordinates with the same native
energy, definitions and compiled policy as Cedar 22. Only the explicit trial's
gradient evaluator changes; existing defaults remain fixed. Native L-BFGS
stopping evidence is retained, followed by fresh full/rounded endpoint category
derivatives and the existing identity-preserving PDB serializer and 17 native
mechanics checks. Convergence, endpoint derivatives, mechanics and scientific
approval are separate verdicts. Returned Cedar 27 verifies all 980 payloads,
17 exact mechanics checks and 336 sampled endpoint directions. It preserves
NOT_CONVERGED_LIMIT after 1,000 iterations / 1,028 calls, with no recorded
optimizer error and the native criterion false. Every accepted target decreases,
including the last 100 transitions. A separately bounded full-precision
continuation is now prepared; it must freshly match the entire
starting corrected vector/target and unchanged sources/static constraints,
then repeat endpoint derivatives and native PDB mechanics. Cedar 28 implements
that opt-in coordinate continuation. Its host/native worker recompute the prior
endpoint proof, match the original manager, then require an exact saved
full-precision start vector/target under unchanged native sources and proxies.
The new optimizer uses fresh L-BFGS history, with at most 1,000 further
iterations and 20,000 calls. It records prior stopping, new stopping and
cumulative optimizer counts separately; full/rounded endpoint audits and all
17 native PDB mechanics checks run again. Seed changes, PDB rounding, atom-order
changes or unqualified prior derivatives refuse optimization. Existing
initial-coordinate/default policies remain fixed. Returned Cedar 28 verifies
all 1,104 payloads, all 17 mechanics checks and all 336 sampled endpoint
directions. The new stage reaches its 1,000-iteration limit, cumulative
2,000 iterations / 2,064 calls, with the native criterion false and no recorded
optimizer error. Target reduction is 3.64% for this stage, 31.32% from the
original initial model. The same three distance and ten angle outliers persist.
Review the tail, category contributions and exact remaining source/term conflicts
before choosing another optimization. Cedar 29 supplies a separate temporary
base-orientation audit. Ranked nominal bond/angle outliers select supported
graph-defined connected bases, with no component-code or attachment-name
allowlist. Proper rotations about each C1-prime/attachment axis preserve the
scaffold and internal base geometry. Nine fixed angles are evaluated separately
at full and PDB-rounded precision, with unchanged native targets and NA policy.
Fresh original-manager/initial-vector and endpoint-family-vector matches precede
the scan. Full-objective rotational derivatives at every sample and isolated
family derivatives at zero angle use four central-difference steps. Repeat,
additivity, periodic-energy and rigid-distance controls accompany exact source
and selected scalar/angle/plane context. Bounds are six supported groups, 3,000
total energy evaluations and 1,200 s by default. Returned Cedar 29 verifies
1,173 payloads and all 96 sampled rotational derivatives. The three independent
coarse scans favor zero degrees, while nonzero validated slopes remain.
Cedar 30 separately selects declared source plane/angle contradictions, exports
a graph-only generation input and reuses the guarded eLBOW adapter. Complete
source-declared coordinates may seed naming/initial geometry when ideal
coordinates are absent; the receipt labels their origin explicitly. Original
chemical declarations are compared at both seed and candidate boundaries,
including complete formal-charge preservation. All original numerical
parameters and metadata remain frozen. Returned Cedar 30 stops before
generation because installed eLBOW accesses the exact mixed-case CCD Cartn
attribute, while graph export normalized its tag. Cedar 31 preserves canonical
external tag spelling with unchanged parsed values, retains the failed attempt,
and adds an explicit public PDU source/control to the same generation workflow.
Its actual NARestraints mappings, A:T pair recipe and both stacking orders are
checked as compiler controls on source atom identities. The canonical partner
is a role template, not an observed pair. The PDU fixture stays under tests;
no production dictionary is installed. Returned Cedar 31 stops DP on absent
alt_atom_id metadata and PDU in an optimizer restart after nonconvergence,
without output dictionaries. A missing alias column now copies exact primary
IDs with an explicit receipt; existing alias/chemical declarations are preserved.
Cedar 32 captures four anchored installed eLBOW modules and performs bounded
read-only input checks. It does not retry optimization, alter installed code or
relax chemical/numerical gates. Source/dispatcher bytes are checked throughout.
Returned Cedar 32 passes PDU and identifies DP's full legacy/CCD dialect mismatch.
Cedar 33 projects declared aliases into a separate CCD consumer input, retaining
unknown atom flags and signed source chirality. It verifies the installed option
parser's effective block/step/tolerance values before an explicit bounded trial
that avoids the captured default restart condition. Source and consumer inputs
are distinct; all original comparisons and nonconvergence evidence survive.
Returned Cedar 33 passes both readers, stops DP before optimization in chirality
handling, and writes a nonconverged PDU dictionary. Cedar 34 adds an explicit
read-only stereo action: replay saved chemical/numerical comparisons, compare
signed volumes in source/generated coordinates and retain omitted R/S labels.
Bounded selected-installation reader controls record native markers and the
reader's isolated chiral constructor, with four exact module snapshots and
before/after integrity checks. This is not a full builder replay, absolute CIP
assignment or dictionary qualification; exceptions and nonconvergence stay open.
Returned Cedar 34 verifies all 1,320 payloads. DP marks all 35 unknown tokens as
native chirality and reproduces the constructor assertion; PDU's known markers
and constructor pass. The constructor invokes local ChiralClass.Optimise, so its
legacy NOT_RUN optimization flag is not evidence of no internal optimization.
The frozen files and whole-molecule generation remain untouched. Cedar 35
preserves an original comp_list monomer-reader route in a target-free consumer,
retaining signed volumes and adding equal source-coordinate aliases. CCD source
routing stays unchanged. Selected-installation parsing records dispatch and raw
atom/bond/charge/coordinate values, with two exact parser snapshots; no chiral
constructor or numerical generation is requested. Parsed value equality alone
does not qualify charge semantics, signed stereo or another generation.
Cedar 35 stops before that parser request: its internal graph check passes an
aliased system temporary path to the strict output guard. Cedar 36 resolves only
the freshly created, tool-owned temporary directory. Caller-selected output
symlink checks remain strict; the retry retains the complete failed capsule
and replays its nested source, stereo and mechanics evidence.
Returned Cedar 36 completes both readers. DP keeps atom identities/elements,
source coordinates and signed markers, but all native bonds are single and its
two declared -1 charges become zero. The captured monomer parser's bond lookup
is case sensitive and its atom-construction loop reads no charge field. PDU
passes raw route/inventory checks. Cedar 37 maps only explicit order aliases to
the parser's lowercase vocabulary, leaving chemical order unchanged. A separate
opt-in declared-charge control checks exact identities/elements/orders/coordinates
and a complete integer source charge map before populating an otherwise zero
native monomer object. Conflicts block population; already-preserved CCD charges
are verified without assignment. Pinned Utilities/MoleculeClass sources bind
the integer charge API. Raw parser findings, before/after recorded graph and
stereo fields and a separately recomputed control result remain distinct.
Returned Cedar 37 verifies all 1,387 payloads and preserves all declared orders.
DP raw charges remain zero; explicit population restores the two source -1
charges on the temporary object while retaining every other recorded field.
PDU requires no assignment. No generator or scaffold repair ran.

Cedar 38 adds a graph-selected triple-bond screen and selected-installation
resource capture. Every declared triple edge selects its own linear neighbors;
component names do not encode chemistry. Isolated fixed source-seed models
compare default monomer lookup against exact captured installed CIFs and, for
PDU, its saved nonconverged candidate. Active native targets, positive weights,
unique membership, observed geometry and torsions containing a linear axis are
recorded separately. Empty explicit dictionary lists require a new explicit
installed-library-only opt-in; existing callers still require dictionaries.
PDU and 5PC public fixtures are pinned; 5PC's ambiguous NARestraints records do
not prevent graph/native component checks and never cause a role selection.
No new dictionary, optimizer, ReadySet run or production integration is invoked.
Returned Cedar 38 verifies 1,446 payloads. Both default monomer resolvers return
no component and both isolated interpretations stop on unknown energy types.
The explicitly supplied PDU dictionary loads: active triple distance 1.174 Å
with ESD 0.020 Å and two 180° angles with ESD 3° pass target/membership screening;
six linear-axis torsions remain. Its native coordinates are the fixed public
source seeds, not the nonconverged generated candidate coordinates.

Cedar 39 reads the installed CCD at the existing configured Python-library
anchor and exact chem_data/chemical_components/<initial>/data_<CODE>.cif
contract. It compares chemical declarations, source geometry/stereo and all
SMILES descriptor text with pinned public controls. A bounded worker records
fresh direct/wrapped monomer lookups plus DG/DC canonical controls and declared
library roots. Proven server/cif_types sources bind imports; Utilities and its
GeoStd/monomer/CCD helpers are captured as text, along with the ReadySet
dispatcher. Those helpers and dispatcher are not executed. Installed CCD files
receive separate simple native reader checks, without a constructor, numerical
generation or optimization. Float replay tolerance accommodates cross-platform
math rounding; identities, state, counts, hashes and input bytes remain exact.
Returned Cedar 39 confirms both installed CCD declaration/text comparisons
and six raw reader checks per component; direct/wrapped monomer lookups are
missing while DG/DC canonical resolution succeeds. Cedar 40 adds an exact C39
return gate, independent source/inventory replay, literal dispatcher-target and
bounded import-text capture, and a <=30 s pinned native CCD filename/SMILES
accessor worker. ReadySet modules remain text evidence and never run. Static
coverage limits are explicit; returned descriptor text stays separate from
mapped graph and numerical restraint qualification.
Returned Cedar 40 verifies both selected CACTVS canonical descriptors and 24
static source snapshots. In one inspected branch ReadySet deletes SMILES and
requests chemical_component; this does not establish an executed route.
Cedar 41 observes original builder/template calls during bounded isolated
ReadySet API generation (180 s/control), retaining exceptions and fallback
results separately. Fixed source-ideal heavy-atom seeds support independent
candidate/native triple-target checks; all raw source chemistry and hydrogen
inventory differences remain visible. No linked scaffold or experimental
coordinates change. Internal template geometry operations are not instrumented.
Returned C41 stops in the preparatory file-input builder call: nested eLBOW
reparses process argv and rejects leaked ReadySet PHIL options. Its worker exits
zero to save the native exception; that is not ReadySet success. Both owned CIFs
are unchanged public-source copies, without numerical targets. C42 follows the
captured ReadySet entrypoint's separation of explicit API args from process
options. Builder kwargs and chemistry stay unchanged. Record process argv per
observed call, classify unchanged/partial/completed output separately, and retain
the old failed calls without executing captured code.

Returned C42 verifies 1,747 payloads, both completed file-input builder calls,
23-atom isolated native managers and independent triple-target screens. Neither
call supplies a SMILES argument. Six generated torsions use linear atom triples;
three survive in each heavy-only manager. Generated phosphate charge differs
from the neutral source (−2, with HOP2/HOP3 omitted); sugar stereo declarations
are also handled separately. No historical floppy-chain cause is established.
C43 adds a read-only native dihedral-conditioning action. Rebuild each exact
C42 manager, pin six numerical modules/binaries, and check selected membership
and default function/symmetry parameters. Single-restraint and singleton-container
kernels are compared with central differences at saved seed and generated
full/rounded coordinates. Plane-normal sines, repeats, reversal and nonchemical
bent/collinear controls keep undefined geometry separate from finite zero
gradients. Original manager signatures, source bytes and installed hashes stay
fixed. Returned C43 passes all 234 real-coordinate directional checks; all
selected proxies are near-collinear. Approaching exact linearity produces large
phase-sensitive forces, while exact-collinear native zero gradients remain
undefined evidence. This audit changes no restraint.

C44 adds opt-in separate dictionary candidates. Select a torsion only when its
consecutive graph path contains an explicitly declared C-C/C-N triple flank
with a unique exact 180° target and positive ESD. Do not use achieved geometry,
component names or atom-name lists. Omit the six complete selected rows while
requiring all other parsed fields unchanged; unsupported/ambiguous inputs fail
before writing. Rebuild the original native manager and require exact C43
matching, then interpret the candidate under the same model/PHIL/APIs. Only six
effective-definition rows and three active heavy-atom proxies/counts may differ.
Every other definition, coordinate, proxy and policy must compare exactly;
unexpected inferred terms remain REVIEW. Both interpretations have a 60 s
deadline per control. No generator, optimizer, charge/stereo correction,
scaffold change or adoption runs. Production repair recipes stay unchanged.
Returned C44 passes both exact comparisons: dihedral proxies change 28→25,
with all other inventory fields and triple targets intact.

C45 evaluates the preserved original and candidate managers at the same three
saved coordinate cases. Pin numerical module/binary identities and selected-root
adapters; rebuild both exact C44 inventories and preserve their static signatures.
Record full and seven family-control targets, Cartesian gradients and counts,
with repeats before/after. Full/dihedral original-minus-candidate deltas must
match the saved sum of the three omitted original torsions, scattered by exact
indices. Unrelated family values remain equal, and family sums must reproduce
each full objective. Sample candidate full/dihedral derivatives at six central
steps in Cartesian, alternating and gradient directions from the graph-selected
six atoms. Perturbed proxy counts must remain equal to their baseline counts.
Special-position or parallelity-bearing managers are outside this isolated
slice. Cap each control at 2,000 evaluations/180 s. Gradient norms are descriptive;
removing cancelling contributions need not reduce the total norm. Native impact
results return with all arithmetic and omitted-term deltas passing. Two 5PC
cases retain strict count review: 71→75 and 70→67, with repeated energy/gradient
values exactly unchanged. Pair identities/contributions were not captured, so
the cache explanation is not yet a native proof. No scientific adoption occurs.

C46 preserves those failures and replays all raw arithmetic. A separate preflight
uses each native energy object's actual nonbonded pair list, avoiding a lookup
that could rebuild it. Record two full/family cycles at each case with pair
identities, VDW/function parameters, individual/native-container contributions
and cache state. Require complete single/container sums, unchanged common pairs
and exactly zero residual/gradient for added/removed pairs. Repeat full/nonbonded
memberships and original/candidate lists must agree; failed proof blocks retry.
Only then run the unchanged strict C45 routine from that settled state, retaining
count/tolerance requirements and additionally monitoring pair identities and
function parameters through all evaluations. Support explicit prolsq simple
identity-symmetry pairs only. Capture installed cache source text and preserve
all pinned source/input/static signatures. Bound each control to 2,000 manager
energy calls plus 5,000 pair kernels/180 s. Returned C46 passes all six
cache preflights and strict cases. The 48 raw transition proofs independently
recompute: the four added and three removed 5PC pair identities each have
exactly zero residual/gradient, with unchanged common pairs and native sums.
All 246 strict derivative directions replay. The pinned worker reports stable
identities through temporary perturbations; raw perturbed lists are not stored
for independent offline replay. No dictionary/model, generator, optimizer,
state selection or adoption runs. Chemical-state and scaffold review remain open.

C47 verifies the exact C46 return and recomputes its pair proofs and strict
arithmetic with maintained code. It then exports the original DP/PDU/5PC graphs
through the preserved source dialect, checking C37 consumer-byte reproduction
for DP/PDU. A selected-root worker retains the raw reader inventory, applies
only the explicit declared-source charge control, promotes through the native
return_molecule_class(simple=False) API and requires the promoted inventory to
match. The original native Chiralise method runs on that temporary component;
complete before/after snapshots, exceptions and source hashes are retained.
Seven source modules are captured, with six existing source pins; wrapper argv
is isolated and each owned worker is capped at 60 s. Generic qualification checks
identities/elements/orders/charges, declared stereo metadata and source-relative
nondegenerate signed volumes, allowing proper rigid rotations/translations.
The native constructor may optimize local chiral templates internally. No
whole-molecule optimization, full builder, dictionary writer, scaffold or
absolute CIP validation is requested. Returned C47 records three exceptions:
DP/PDU stop with `not chiralised`; 5PC reaches the unavailable legacy
`OptimiseBFGS`. Graph/charge/promotion and marker gates pass. The absent
`after_format` on exception explains the reported route gate, without proving
route mutation. Failed local coordinates remain evidence only.

C48 adds an explicit native-CCTBX preparation policy and exact C47 return gate.
Recompute original exceptions/qualifications and all earlier prerequisites.
Start from byte-identical original consumers, never partial failed endpoints.
AST-check the selected native reader's same-object `SetCCTBX(True)` then
`Chiralise` sequence. Resolve/capture selected-root setter/getter sources and
signatures; retain flags and complete inventories. Require identical chemistry,
coordinates and reader format across backend selection, then invoke original
Chiralise. Four additional backend gates complement all existing stereo gates.
Exception snapshots now also retain format. Old qualifications/defaults remain
unchanged unless the new action is explicit. Each owned worker retains the
60 s cap. Returned C48 completes all three constructors and all backend,
graph/charge/marker gates, retaining source-relative sugar-hand warnings. This
is not a full builder/generation/adoption result.

C49 verifies the exact C48 return and extends independent orientation checks
to all four graph-neighbor triples plus the four-neighbor determinant. The
saved DP C4-prime endpoint adds a review beyond the previously selected basis;
5PC C4-prime has a mixed-basis finding with preserved four-neighbor orientation.
Neither constitutes an independent absolute CIP or final-configuration verdict.
For each original source, separate fresh unobserved and observed native workers
use the same reader/charge/backend/constructor setup. Selected-source process-
local wrappers record outer/local chiral construction, Z-matrix setup,
restraint construction, CCTBX optimization, tightening and native R/S-return
boundaries. Original arguments/returns are forwarded once; complete parent
states, local atom order/index/shared-object evidence, exceptions and available
minimizer error fields are retained. Class methods are restored in finally.
Maintained replay checks nesting, fixed chemical fields and finite snapshots,
then reports first observed orientation reviews and adjacent crossings. Native
method boundaries are observed; optimizer kernels remain uninstrumented. Exact
fresh endpoint agreement and old C48 comparison stay separate from science.
Random state is not reset, so differences remain REVIEW. At most six 30 s owned
workers and 256 observed calls per constructor are allowed. No target, chemistry,
full-builder, scaffold or adoption changes. Returned C49 completes all six
constructors: observed endpoints match fresh controls and C48 exactly. All
three retain source-relative hand review. DP additionally changes native
chiral marker fields while separate signed-volume metadata survives. Its
chemical-metadata continuity check remains failed; PDU/5PC trace replay passes.

C50 requires exact C49 and independently replays six qualifications, raw traces,
method-source definitions and fresh/previous comparisons. It adds opt-in local
coordinate mapping observation: selected native GetCoordinates, SetCoordinates
and GetNewManager calls retain original arguments/returns and kernels. Capture
local named order/global indices, vectors and actual native manager chirality
proxy indices, signed volume target, weight and both-sign flag. Maintained
replay maps each proxy basis to source names, checks exact getter/setter order
and unchanged outside atoms, and reports source-volume/target sign agreement.
Separately compare the final tightening-to-R/S boundary gap with the observed
sorted-index coordinate transfer and local before/after hands. Shared parent
atoms may occupy different temporary frames; no completed-molecule stereo or
causal-bug inference follows. Keep original hand/metadata gates, targets and
NARestraints authority. Bounds remain six 30 s workers/256 calls each, with
64-row vector/proxy caps. Returned C50 passes 18 getters, nine setters and all
fresh/previous comparisons; all nine observed sorted-index transfers match.
The original local-order proxy view has one invalid origin basis per component.
A separate offline sorted-index hypothesis matches all nine source graphs and
all PDU/5PC target signs, with DP C1-prime still opposed. This is a hypothesis
about native restraint order, not proof or authority to reindex computation.

C51 requires exact C50 and preserves every original predicate/report. Existing
hooks additionally record native restraint dictionary atom keys, indices,
live sharing/stored coordinates and original returned arrays/parameters.
Capture selected RestraintClass.py and geometry_manager.py and fingerprint
the original bound GetRestraints and module factory methods without additional
GetRestraints calls. Maintained replay requires unique stored vectors and exact
returned-array alignment with named keys sorted by native index. It separately
maps the same proxy offsets in the observed local getter order. Retain both source-volume/target
views and all original hand/metadata warnings; no arrays are rewritten.
Dictionary shape is bounded to 256 entries and parameter sequences to 64.
The three native components/six 30 s workers remain fixed. A third bundled
public control, ATL, independently checks its bridged source graph/four centres
and existing T-class NARestraints pairing/stacking compiler. It performs no
native ATL construction or scaffold insertion. No NAR workbook/release edit,
standard-DNA pucker replacement, recipe change or ninth live-pair addition.
Native named-index evidence, full generation and scientific approval remain open.

Returned C51 verifies all 2,395 payloads and six completed constructors. Fresh
and previous endpoints match; nine empty named-key inventories expose an
observer mismatch: RestraintClass stores coordinates under integer keys.
C52 replays the failed observation and records integer entries, native link
positions and named local atoms (unique_index takes precedence over index).
Exact inventories, selected native method sources and returned vectors must
agree. No native getter is called again and no array is reordered in native
computation. Returned C52 passes all nine bindings and exact repeats. All six PDU/5PC
source target signs agree; DP C1-prime remains opposed, while original temporary
hand/marker warnings remain. This does not establish final molecular inversion.

C53 tests the native builder's Setup prerequisite before isolated Chiralise.
Pin selected builder/Setup source and require the normal same-object call order.
Call original Setup once per worker, proving unchanged component/format and
exact retained input_xyz. Capture cache values again after construction.
Separate fresh prepared controls/observers must be compared; the old unprepared
endpoint comparison remains a separate outcome. Preserve every original target,
weight, kernel and warning. This does not replay the complete builder or assign
independent absolute CIP. Returned C53 passes all six setup/cache qualifications
and fresh comparisons; all nine native-basis source target signs agree. Only DP
changes from its unprepared endpoint. Temporary hand/marker warnings remain.

C54 uses the selected native full-builder run API with the source-prepared
molecule, explicit charge transfer and native CCTBX preparation. The installed
run owns Setup, construction, optimization and output. Source/API fingerprints,
one 180-step optimization block and a 600-second worker deadline bound each of
three independent candidates. Written output survives nonconvergence or later
errors; raw evidence is retained and serialized molecule payloads stay excluded.
Finished-coordinate checks use the four named neighbors of each declared centre,
separate from temporary local frames and central deformation. Complete chemical,
charge and numerical checks remain active. This supplies evidence for the later
native usability/adoption adapter, without changing native kernels or ordinary
PostMR. Returned C54 completes all three builders with preserved explicit
charges and nine finished source-relative configurations. DP's raw rejection
concerns one omitted phosphate `both` volume term; fixed sugar hands match.
PDU reports nonconvergence and DP/5PC stopping is unreported.

C55 adds opt-in isolated usability on the frozen C54 dictionaries, without
generation or optimization. Six 60-second native workers check source-seed and
generated coordinates, exact effective definitions and covalent proxies, and
two finite repeatable unnormalized energy/gradient evaluations each. A general
`both` omission reassessment preserves the raw rejection and requires all four
bonds and six angles at that centre, without changing native kernels or targets.
Verified evidence reaches the existing decision core for this isolated generated
pool only. Usable nonconvergence is a note; unusable output remains unselected
and existing production dictionaries are preserved. Returned C55 completes six
native interpretations with finite repeatable energy/gradient values. Its v1
auditor rejects roundoff and period-zero/zero-ESD native constant rows. V2
compares Cartesian roundtrips within 1e-12 A, requires exact constant-container
rows/weights and canonical signed torsion permutations, and passes all six cases
with three isolated CONTINUE_WITH_NOTES decisions. C56 verifies/pins the saved
receipts and replays them without new native calls or captured-code execution.
Returned C56 verifies all 2,774 payloads, six saved passes and three isolated
continue decisions without new native calls. Historical failures remain intact.

C57 adds `cif-source-declared-dna-metadata-v1`: accept only explicit consistent
source DNA group/type declarations, then prepare a separate candidate changing
only `_chem_comp.group` and `_chem_comp.type`. Existing native classifications
already say DNA; written generated groups are ligand/non-polymer. Six bounded
workers reuse the same two models and PHIL per component, requiring native DNA
metadata, exact name-normalized covalent proxies and matching full targets and
named gradients. The verified original remains an automatic isolated fallback.
Returned C57 verifies all 2,854 payloads, six native equivalence passes and
three source-metadata selections with notes. No polymer link, production
adoption or pipeline change is implied. Unsupported native formal-charge readback is
explicit, not substituted with partial charges. Nonbonded pair identity is not
qualified by the target/gradient comparison.

C58 adds separate three-residue controls using explicit 5W6W A:1-3 sites. Keep
canonical backbone/flanking coordinates and rigidly transport the graph-selected
base in its sugar frame. The linked-preparation API accepts an optional hash-bound
passed isolated qualification: fresh source reassessment remains mandatory,
legacy DNA group metadata is allowed only through that bridge, and old callers
keep the type-only gate. Prepare graph-selected incoming OP3 and outgoing-H
deletions plus the reviewed OC2 type. Do not infer OP2 protonation or targets.
One canonical reference and three modified workers use the existing PHIL
namespace adapter, fixed native kernels and 60-second limits. Require exact
two-link membership/targets, projected definitions/heavy proxies, all phosphate
tetrahedral bonds/angles and unchanged flanking mechanics. Returned C58 verifies
all 2,940 payloads and four completed Phenix 2.2.1-6174 workers. The three
modified cases pass; eight finite energy/gradient evaluations repeat exactly.
Unavailable formal-charge readback remains explicit, with no contradiction.

C59 tests a separately assembled DP B:4 bundle in the preserved 877-atom,
43-site scaffold at its saved PDB-rounded coordinates. A fresh original native
manager must match the captured baseline before testing the candidate. Replace
only the selected component dictionary and that site's previous modifier
requests. Shared modification definitions and other sites' requests retain
their exact bytes; source-graph incoming/outgoing preparation supplies the new
site modifier. Preserve the model, every unselected effective definition and
proxy, all 38 backbone links and the complete explicit NARestraints custom
pairing/stacking requests. Require exact projected heavy restraints and finite
repeatable fixed evaluations. Each of the two workers has a 60-second limit;
there is no generation or optimizer. Select the qualified candidate or retain
the verified original automatically. Returned C59 verifies all 3,097 payloads:
the original baseline passes all twelve checks, and the candidate passes 67
checks with only unavailable formal-charge readback unsupported. The separate
automatic decision selects qualified_candidate with notes. All 877 atoms,
43 sites, 38 links and explicit NARestraints mechanics survive.

C60 performs one bounded geometry trial from this verified C59 PDB-rounded
start under the replacement manager's fixed definitions. A new initial
corrected-gradient audit must pass before the existing native optimizer runs.
Carry the C26 plane correction proof only if the complete plane/parallelity
inventories, named atom mapping and native API/source pins match; calculate a
new constraint signature for the replacement covalent manager. The old
manager's signature or derivative verdict cannot qualify changed targets.
The additive cif-replacement-manager-gradient-qualification-v1 validator keeps
this boundary explicit. The qualified local plane correction and native kernels
remain unchanged. The existing geometry worker, optimizer and termination rules
retain a 1,000-iteration bound under the unchanged native trial policy
cif-fixed-na-corrected-geometry-trial-v1. Check endpoint derivatives at full
precision and PDB-rounded coordinates, exact native readback and serialization
bound to the verified source-model hash. Both the full-precision endpoint and
the freshly reread rounded PDB must have zero fixed-hand sign conflicts and a
target no worse than the new trial's initial target under the same objective.
The cif-qualified-scaffold-geometry-choice-v1 adapter
`cif_scaffold_candidate.select_scaffold_geometry` chooses a usable endpoint or
retains the verified C59 initial model automatically, including when no endpoint
is produced. Nonconvergence, pucker and residual outliers are notes, not forced
continuation cycles or failure conditions by themselves. This is a
new fixed objective, not a continuation of C28 or an energy comparison with its
old dictionary. Returned C60 verifies all 3,300 payloads and unchanged C59
parent. The initial and both endpoint sampled derivative cases pass; all 17
native readback checks pass. Its eight selection checks retain the usable
endpoint with notes while preserving NOT_CONVERGED_LIMIT at 1,000 iterations.
Production adoption and scientific qualification remain separate.

C61 adds cif-qualified-runtime-bundle-v1 in `cif_runtime_bundle.py`. It stages
the exact selected written model, 19 dictionary resources and 14 PHIL resources
in a standalone directory with ordered relative hash-bound references and
activation evidence. The generic resolver validates the schema and resource
integrity and resolves within the bundle root after relocation. The public
`cif-doctor assess --bundle PATH` uses this resolver and the ordinary read-only
assessor, without constructing an AutoMR run or checkpoint. Assessment does not
upgrade the inherited native/scientific qualification.

The separate C61 activation diagnostic replays C60 and performs one fresh
native interpretation from the staged layout, requiring the same identities,
definitions, proxies, backbone links and explicit NARestraints policy as C60's
rounded readback. It does not regenerate parameters, compile a new pairing/stack
policy, optimize, read diffraction or refine. Source resources remain intact;
curated precedence and NARestraints authority stay fixed. Ordinary automated
acquisition/repair, PostMR adoption, production checkpoints/refinement and PDF
rendering remain future integration work. No production workflow is fabricated
from a capsule without observations or a PostMR checkpoint.

The [automatic continuation contract](cif-doctor.md#automatic-continuation-and-student-facing-decisions)
separates internal diagnostics from student workflow. The pure decision core
excludes demonstrated unusable candidates, respects source authority and ranks
only comparable fixed-objective endpoints. Nonconvergence and pucker changes
are nonfatal notes; inversion is a candidate exclusion, triggering automatic
fallback. PostMR includes an additive plain-language solution_report summary.
Automatic acquisition, production qualification/adoption and the PDF renderer
remain planned; the policy core and isolated adapter are not an integrated
recovery pipeline.


The component-control auditor compares duplicate records by all atom roles and
operational category/sugar/phosphate/attachment context. Descriptive aliases and
explicit C5-mod/C7-mod annotations do not select atoms. Equal operational records
compile once with raw aliases retained; conflicts stay blocked. Canonical
partners among registered recipes precede modified-family synthetic controls.
5PC's two C-sheet records therefore compile the existing G:C and stacking
controls. NARestraints code, workbook and recipe policy remain unchanged.
Full linked ReadySet reproduction, mapped-SMILES graphs, native stereo and
scientific qualification remain open. All production/default resource and curated-ligand
precedence rules remain fixed.


For W/5W6W, NARestraints consumes the packaged `Std_padd.txt` specification
(`A 11:13` / `B 5:3`) and remains the sole source of stacking restraints. The
portable 5W6W secondary-structure template contains 17 non-overlapping
scaffold base pairs, no stacking pairs, and no historical input paths, cell,
map, output, or GUI settings.

When prepared W residues make a template Saenger class inappropriate, PostMR
uses the reviewed NARestraints atom-role mapping to replace only those scaffold
blocks with explicit pair restraints, retaining unaffected pairs and the usual
stacking source. Component identity, monomer geometry and pair-recipe roles
remain distinct; neither a CIF nor a construction parent invents a pair class.

`--modified-pairs-only` generates a model-derived restraint selection in either
standard or nonstandard mode. After all coordinate edits,
the NARestraints guesser runs with `allow_noncanonical=True`. NASolve defines
modified sites by noncanonical nucleotide residue identity and retains a
candidate when either partner is modified. It writes pair restraints with
stacking disabled. When a project also supplies a scaffold EFF, the generated
PHIL is authoritative: matching scaffold base-pair blocks are removed and the
remaining project overlay is retained. A zero-pair result is a successful
no-op; warnings, candidate counts, retained pairs, and removed overlaps remain
in the report.

The bundled registry combines source adaptations, construction recipes and
identity bridges; it is not a list of proven supplier defects. The
[component source audit](modified-component-preparation.md#bundled-ligand-audit-2026-10-09)
records their roles and the unresolved DE numerical-geometry review. User token
`E` maps to the laboratory PDB-compatible `DE`, not official CCD `8RO`, whose
topology describes a different sulfur-ring compound. `F` maps to `DF`, with
official deposition identity `A1AAZ`; `D` maps to official `1AP`; and `Q` maps
to official `S6G` with canonical parent `DG`. The registry
defines canonical parents and required/forbidden sulfur bonds, which are
validated before Coot or ReadySet runs. ReadySet receives the curated CIF,
executes with `actions.hydrogens=False`, and is run with `cwd` set to its own
directory because Phenix 1.20.1 accepts but ignores `input.output_dir`. The
output is rejected if it contains hydrogen coordinates. A phosphate check
removes verified internal OP3/O3P additions before comparing total and HETATM
atom counts to the prepared input; other count changes remain errors.

`phosphate.sanitize_phosphates` also runs before NARestraints. It scopes checks
to nucleotide-like residues with OP3/O3P and to sites repaired in the first
pass. An incoming O3'-P contact must be unique within a model/chain/TER segment,
with a 1.2–2.1 A separation. Remaining P, OP1/O1P, OP2/O2P and O5'/O5* atoms
must be unambiguous. Their P-O distances use the same broad bounds, and their
O-P-O angles must be between 60 and 160 degrees. These are coarse corruption
guards, not chemical target values. Reference-known incoming and outgoing
links must survive. OP3/O3P requires explicit per-site user consent, including
at termini. Selecting an annotated recipe is also explicit consent for exactly
its declared `chemistry.terminal_phosphate_sites`: the W/5W6W card declares
D:1, confirmed by Simon as part of the design on 2026-09-15. This is resolved
before AutoMR freezing, not inferred later from coordinates or residue numbers.
An explicit dataset `allow_op3_sites` replaces the entire recipe list, including
an empty override. Unrequested unlinked OP3 stops for review. A request must not
permit an extra OP3 on an internal phosphate. Ambiguous explicit or symmetry
links require inspection. Only verified extra atoms and associated
ANISOU/SIGATM/SIGUIJ/CONECT records are removed; surviving coordinates,
occupancies, and B factors are untouched.

Atom serials need not be unique for this coordinate cleanup: selected atoms
are identified by their validated coordinate records, while ANISOU/SIGATM/
SIGUIJ records use exact atom name, alternate, residue identity, model and
TER segment. Unrelated records sharing the same serial are preserved. Because
CONECT identifies atoms only by serial, affected bonds must have unique
endpoints before they can be interpreted or edited. Cleanup does not renumber
the raw or surviving coordinate records.

PostMR's additive `phosphate_cleanup.before_restraints` and `after_readyset`
reports record checked sites, removed/retained atoms, connectivity, and measured
geometry. Raw ReadySet output remains at `readyset.updated_model`; the new
`readyset.phosphate_checked_model` points to the separately checked copy used
for the final model. Immutable earlier runs require no migration and are never
rewritten.

The first parameterized monomer override uses selected-site `NASnoOP3`
modifications for reviewed 1AP chemistry. The original integration/validation
diary is preserved under `history/1ap-phosphate-integration.md`; it is no longer
the active contract.
The current connectivity-selected profile supports 1AP, DZ, DP and 5CM;
legacy profiles without an explicit component scope remain 1AP-only.
New runs freeze authoritative refinement/view artifact lists with hashes,
so ReadySet cannot silently supersede an explicit parameterized CIF or omit the
modification at checkpoint creation. Incoming/outgoing profile links and
explicit OP3 consent are checked after preparation, around refinement, before
Doctor triage and on manual import. Existing histories are never rewritten.

Coot/model editing, component CIFs, NARestraints, and ReadySet have separate
roles. Coot establishes coordinate identity and placement; CIFs establish
intra-residue topology; NARestraints establishes selected inter-residue
geometry. ReadySet is the uniform post-edit normalization and validation gate,
even where Phenix refinement could technically consume the edited PDB and CIF
directly.

The legacy NARestraints `DF` mapping names canonical `O2` as `S2`; the
A1AAZ-derived component uses `S1`. The PostMR adapter patches a copied residue
record in process memory, restores the builder's original loader in a `finally`
block, and records the correction. The installed workbook is never mutated,
and a future upstream `S1` mapping requires no correction.
The same adapter trims the exact legacy `S6G C5` value `C5 ` to `C5`.

The ReadySet model is scanned by element rather than by a closed residue list.
Iodine, bromine, and selenium in nucleotide-like residues are the initial
anomalous trigger set. The PDB element column is authoritative; a conservative
atom-name fallback is recorded when the column is blank. This allows a new
modified residue to trigger the later AutoSol branch without first adding its
residue code to an AutoSol allowlist.

## AutoSol contract

AutoSol is conditional and deliberately separate from PostMR. It requires a
`POSTMR_READY` report containing one supported heavy-atom element and refuses
to overwrite an existing `AutoSol/` directory. The current trigger elements
are iodine, bromine, and selenium; the element registry is intentionally open
to reviewed additions.

When a standard-frame catalogue supplies `seq_base.txt`, AutoMR freezes a
checksummed copy under `Model/` and AutoSol copies that run-local snapshot into
its input. Legacy runs recover the exact declared frame directory without
requiring the old pair-model filename to remain present. For a nonstandard
model, complete sequences recorded in the frozen run may be written to the same
input instead. The wavelength is read from `summary.html`, preferring the
high-precision assignment and rejecting inconsistent repeated values.
`phenix.mtz.dump` must confirm a complete anomalous intensity or amplitude
quartet before execution.

The AutoSol request is MR-SAD guided by the original Phaser solution PDB, not
the modified PostMR model. This avoids using the modeled heavy atom to validate
its own anomalous signal. NASolve supplies the heavy-atom element and
wavelength, leaves the number of sites unspecified, uses every logical CPU,
and explicitly sets both `build=False` and
`phase_improve_and_build=False`. After execution it reads `autosol.eff` and
rejects the run unless both build controls remain false, every `sites` value is
unset, and the requested processor count is effective.

Output discovery is content-based. The refinement input must contain a full
Hendrickson-Lattman phase quartet and anomalous observations. The AutoSol HA
PDB is compared with every expected nucleotide heavy atom of the same element.
For H3/R3, matching expands the three point operators, R-centering
translations, and neighboring unit cells; P1 uses lattice translations. The
branch automatically accepts phases when at least one expected atom has a
same-element HA site within 4 A. A nearest site between 4 and 8 A produces an
`AUTOSOL_REVIEW` result and requests inspection. A more distant or absent site,
or an AutoSol execution/output failure, produces `AUTOSOL_WARNING`. Review and
warning outcomes do not block the ordinary MR refinement path, but their phase
files are not automatically approved for use. All sites and match attempts are
retained in the report, while extra unmatched sites do not block this phase of
the pipeline.

AutoSol also records an optional `outputs.density_modified_map` portable
reference and SHA-256, plus `density_modified_map_status` and a diagnostic.
Discovery prefers a unique `overall_best_denmod_map_coeffs.mtz`, then a unique
`resolve_histograms*.mtz`, excluding TEMP/PDS products. Missing, ambiguous, or
unreadable view maps do not change phase acceptance. This viewing product is
distinct from the HL-bearing `refinement_data` input.

## AutoRefine contract

AutoRefine separates immutable scientific inputs from evolving coordinates.
Each round inherits an improved model from one selected parent checkpoint, but
always retains the original STARANISO observations and original Free-R array.
Refinement-generated MTZ files are outputs and evidence; they cannot become the
observation source of a child by accident.

The root checkpoint is the prepared ReadySet model. Its restraint set consumes
the frozen effective PostMR bundle: explicit parameterized component inputs
take precedence over generated copies, while construction-only CCD graphs
defer to usable generated numerical definitions. Selection is by component
content, not filename; other generated components and modification-only CIFs
remain included. The NARestraints PHIL and project EFF files are retained.
Raw ReadySet output is preserved as provenance. See
[effective dictionary preparation](modified-component-preparation.md#effective-dictionary-preparation).
An approved AutoSol file is a separate phase source. Explicit
reflection file names and labels prevent duplicate observations in the AutoSol
file from competing with the authoritative STARANISO array.
AutoRefine derives one fail-closed reflection-selector policy from the
discovered Phenix version before allocating a round. Phenix 1.20.x uses
`legacy-explicit`: the command retains exact observation, Free-R, and optional
HL phase file/label selectors, but the unsupported Data Manager block is
omitted. Phenix 2.1.x and 2.2.x use `data-manager-file-scoped`: the same explicit
selectors are retained and the parameter file additionally binds each label
set to its MTZ through the Data Manager. Unknown, malformed, and unvalidated
families are rejected rather than mapped by version ordering. The exact
version and selected mode are frozen in the round report and checkpoint, and
Refine Doctor passes the same policy to every trial.
AutoRefine hashes that phase source once immediately before use, captures its
filesystem identity, and checks the identity again after all external work and
output hashing. Replacement, modification, or deletion is retained as a failed
checkpoint, never selected as current, so the next attempt receives a new
immutable round number.

The default recipe is intentionally conservative and named
`AutoRefine/default`:

- five macrocycles;
- reciprocal- and real-space coordinate refinement;
- group ADPs and eligible occupancies;
- automatic target selection, optimized XYZ/geometry and ADP weights, and the
  `n_gaussian` scattering table;
- no rigid body, individual ADP, TLS, NCS, reference-model, water-update,
  hydrogen-addition, or simulated-annealing strategy; and
- every logical processor available to the process.

When PostMR has no anomalous candidate, AutoRefine selects supported mean
observations. With a candidate, it requires an amplitude quartet
`F(+),SIGF(+),F(-),SIGF(-)`, forces anomalous observations to remain separate,
adds `group_anomalous`, and defines one exact atom selection per known model
site. A validated AutoSol MTZ supplies its discovered HL quartet at the same
time while the target remains explicitly `auto`. If AutoSol is approved but
F+/F- amplitudes are missing, a non-anomalous mean-data fallback may finish,
but the command returns a final error and marks the result for review.

Subprocess output is redirected to `phenix.refine.log`; the console receives
only a start notification and a curated result card. Rwork/Rfree history,
clashscore, bond/angle RMSDs, labels, selections, commands, outputs, and
acceptance decisions are written to the round report and a small metrics TSV.
Before computation, the same command is run through Phenix's dry-run parser in
the isolated round directory. An invalid parameter or input therefore produces
a small failed checkpoint and never launches the expensive refinement.

## Checkpoint graph

`AutoRefine/checkpoints.json` is the run-local registry. Nodes are immutable
and contain a stable ID, parent, recipe, status, model checksum, frozen input
references, metrics, compatibility result, and outputs. `SUCCESS` nodes become
current automatically. `REVIEW` nodes remain reusable but require explicit
selection; `FAILED` nodes remain visible and cannot be selected.

Checkpoint listing is read-only: it validates an existing
registry without rewriting it, or derives a validated PostMR root in memory
without creating files. Modifying operations still initialize the registry.

### Future graphical checkpoint-tree view

The immutable checkpoint registry is also the natural data model for a future
generic NASolve GUI. The GUI must visualize the existing graph rather than
create a second lineage system.

A **tree/graph mode** should show stage and model lineage across MR, PostMR,
AutoSol, ordinary refinements, Refine Doctor branches, manual imports, topology
surgery children and later re-MR attempts started from refined models. A
forty-refinement run should remain navigable as a graph rather than a flat
chronological list.

Useful graph operations are read/select/branch operations already compatible
with checkpoint semantics:

- pan/zoom through the lineage tree;
- collapse repetitive refinement chains into expandable groups;
- pin/bookmark important models as visible panels/cards;
- compare siblings or parent/child metrics without changing the current pointer;
- select any eligible node as the current checkpoint through the existing
  audited selection operation;
- launch `show`/Coot for one node without selecting it;
- branch a new refinement, Doctor, topology-surgery or later MR attempt from an
  explicit source node; and
- traverse back to an earlier model without deleting descendants.

The same graph component should be usable standalone in normal NASolve mode and
embedded in specialized workspaces such as Topo Net. Specialized workspaces may
add domain-specific overlays, but all state-changing actions still create
ordinary immutable checkpoint/model-lineage nodes.

The durable application-shell, scientific hierarchy, color/status semantics,
CLI-to-GUI coverage and capability-driven extensibility rules are defined in
[the GUI design contract](gui.md).

`nasolve checkpoints add RUN --name NAME` creates a bookmark without copying
the current node. Supplying `--model` imports a manual model into the run as a
new review child. `--mtz` is a deliberate observation replacement for an
external refinement and remains subject to label and Free-R validation before
the next round. `nasolve checkpoints use` changes only the current pointer;
all branches and provenance remain intact.

Automatic readiness requires a successful Phenix exit, a compatible model,
`Rwork < Rfree`, and `Rwork < 0.30`. These numerical tests permit continued
automation but do not replace visual inspection or user approval.

## Refine Doctor contract

**Planned coordinated Doctor scope:** the October 11 GeoTest follow-up bundles
the existing refinement/data/Free-R diagnostics below with the next deterministic
component/restraint assessor and future model geometry/connectivity assessment,
including guided sticky-end repair. This broader orchestration is not implemented
by the current `refine-doctor` command. Geometry findings must be assessed before
choosing more refinement strategies; high Rwork alone does not identify noise,
dictionary defects or fractured arms. Declared assembly/routing and bounded
checkpoint repair follow the [guided connection contract](construct-registration.md#geotest-guided-arm-connection).
Frozen Free-R flags remain unchanged. The
[handoff](development-handoff.md#restraint-doctor-and-subsequent-roadmap) owns
implementation order and returned evidence.

Refine Doctor is a finisher and diagnostic layer, not an unconstrained
R-factor optimizer. It starts from the current or explicitly named checkpoint,
records that pointer, and requires every trial to be an immutable sibling of
the same source. A successful trial is recommended for inspection but is never
selected automatically by the engine. In an interactive CLI session the user
receives a final `[y/N/i]` prompt, with each answer confirmed by Enter. `i`
opens the exact recommended checkpoint through the ordinary Coot view path,
then repeats the prompt without waiting for Coot to close or rerunning Doctor.
Only `y` performs the ordinary audited checkpoint selection. `n`, blank input,
EOF or Ctrl-C at the prompt finishes with the pointer unchanged and prints
commands for inspection, later selection, and returning to the diagnosed
source. A Coot discovery or view error preserves the prompt for another choice.
Noninteractive sessions print commands without prompting or launching Coot.

Before launching Phenix it audits the authoritative Free-R array with the
Phenix/CCTBX runtime. The audit measures the independent Friedel-group count,
test fraction, mate consistency, and test-set population across resolution.
Inconsistent mate flags, fewer than ten independent free groups, or a guarded
fraction outside 2-20% stop all trials. A small or shell-sparse test set is
classified as noisy rather than invalid. Refine Doctor never tries alternate
test-flag values and never regenerates flags merely to reverse an R-factor
ordering.

An unavailable audit also stops all trials. A source that already passed the
numerical gate needs no default trials. Otherwise the declared sequence stops
at its first numerical pass, technical failure, or trial budget. Both
`--max-trials` (default five) and macrocycles per trial (default three) accept
1-10. Every attempted/skipped recipe and its reason is recorded.

Source anomalous benchmarks retain their wavelength, occupancy, B factor and
checkpoint. For selected anomalous observations, default Doctor trials use
explicit Henke f'/f'' values calculated with Phenix/CCTBX at the recorded
AutoSol wavelength. The sequence tries ML and eligible MLHL with those values
fixed, then f''-only refinement, coordinate-only, and B-only fixed-scattering
fallbacks. Missing wavelength or failed calculation skips these recipes for
inspection; zero is not substituted. A successful f''-only execution can supply
a missing benchmark. Fixed values are distinguished from fitted values in the
metrics. The ordinary AutoRefine default remains unchanged.

The ordinary mean-data branches are:

- ML without HL phases, reciprocal-space XYZ, residue-group ADPs, no occupancy
  search, and anomalous-parameter refinement off; and
- the same parameterization with approved HL phases, allowing Phenix's
  automatic target to use MLHL.

An individual-ADP branch is eligible only at 3.2 A or better and with at least
three independent observations per modeled atom. This prevents low-resolution
DNA models from gaining a nominal R-factor improvement through an unsupported
parameter count. Trial definitions are declarative `RefineDoctorTrial`
records, so future project presets may supply additional reviewed strategies
without changing checkpoint or audit behavior. Coordinate-only and group-B-only
fallbacks follow; these are independent sibling trials, not chained stages.
Weight optimization is enabled only for the coordinate/ADP strategies being
refined, and occupancies stay fixed in every default Doctor recipe.

A branch is strictly successful only after a successful compatible AutoRefine
execution with finite valid R values, `Rwork < Rfree` and `Rwork < 0.30`.
Failed or incompatible outputs cannot win because they printed favorable
statistics. If none passes, Doctor returns `REFINE_DOCTOR_REVIEW` (exit 2),
leaves `recommended_checkpoint` empty, and separately identifies a usable
`inspection_checkpoint` by Rfree then Rwork. This descriptive ranking does not
quantify uncertainty or establish superiority. A small inversion no longer
endorses the original source as good enough. The additive `triage` and
`ranking` report fields explain budgets, skipped recipes, the stop and next
inspection steps. Campaign-owned execution and optional full-auto provisional
selection are described below; richer diagnostic-driven restraint/data
alternatives remain future work in `campaigns.md`. Immediate implementation
state is tracked in `development-handoff.md`.

## Stage-aware Coot views

`nasolve show` resolves the active workspace; an explicit run remains supported.
When a checkpoint registry exists, the selected current model takes precedence
over newer unselected attempts, including when current is manual or PostMR.
`nasolve show last DATASET` first chooses the highest numbered run. Explicit
`--stage` or `--checkpoint` opens a comparison without changing the current
pointer. Without a registry, the default prefers accepted AutoSol with a usable
density map, then completed PostMR, then Phaser. Profiles differ:

- AutoMR: Phaser model and Phaser MTZ;
- PostMR: ReadySet model and dictionaries with accepted AutoSol density when
  available, otherwise an explicitly labelled Phaser map;
- AutoSol: ReadySet model and dictionaries, separate AutoSol HA model, and
  density-modified map coefficients; and
- AutoRefine: current refined checkpoint model, map coefficients, and its
  frozen dictionaries.

Manual checkpoints keep their own model and dictionaries. Maps may be inherited
through the checkpoint ancestry only when frozen observations agree; the source
label states they were not recalculated for the manual coordinates. Raw HL-only
phase data are never substituted for a density map. Declared sources and their
checksums take precedence; ambiguity, corruption, or a missing declared map is
an error. Legacy AutoSol runs retain bounded discovery within their own stage.

Every view retains ordinary `--auto` map loading and adds a run-local Python
startup script. In Coot, `valid_labels` checks the exact `ANOM`/`PHANOM` pair.
The script uses `make_and_draw_map` with no weights and the difference-map flag,
then names the overlay and sets its initial contour to 3 sigma. It adds no
phase shift. Existing maps with the same MTZ and column pair are reused, and
the original refinement-map and scroll-wheel selections are restored.

Candidates are the selected map MTZ followed, for refinement checkpoints, by
the explicitly recorded `refinement_reflections` MTZ if different. Both follow
the existing relocation and checksum rules; a corrupt or missing declared
source stops launch. Manual checkpoints inherit these candidates from the
same observation-compatible ancestor as their ordinary maps. Other stages
check only their selected map. There is no search across refinement rounds,
dependence on an anomalous-refinement flag, or substitution of HL coefficients.
Missing columns simply leave the normal view in place. Optional Coot API/read/
display failures are logged without closing the ordinary view.

`launch.json` has an additive `anomalous_map` request with paths, labels,
contour, script path, and `status: check-in-coot`; this is not a claim that an
asynchronously started GUI loaded the map. `NASOLVE_ANOMALOUS_MAP` JSON lines
in `coot_gui.log` record `loaded`, `reused`, `absent`, or `error`. No checkpoint
or scientific report schema changes, regeneration, or dependency installation
are required. Tests execute the generated script against a simulated Coot
Python API; graphical validation on the user's Coot 1.3.3 / Phenix 2.2.1-6174
outputs remains a live check, not a claimed execution in the test environment.

Every graphical process starts in `RUN/CootGUI/STAGE/` with its backup
directory redirected underneath the same pen, plus a checkpoint subdirectory
when selected. Console output and `launch.json` identify the run, checkpoint,
model, and map source. Run discovery uses numbered directories and reports,
never filesystem modification times.

## Campaign planning contract

`presets.load_preset` validates a schema-1 or schema-2 TOML policy and its declared
resource bytes. The packaged `5w6w` preset covers the existing standard workflow. Unknown
settings and unsupported policies stop loading. Paths resolve within the preset
root, and exact source and resource hashes accompany the canonical configuration
fingerprint. Python 3.10 uses the conditional `tomli` dependency; newer Python
uses `tomllib`.

The optional `[chemistry] terminal_phosphate_sites` list is a typed, explicit
site declaration. The W frame points to the packaged `5w6w` card (now version
1.1.0) for standalone input resolution. Campaign planning passes its selected
card to the same resolver; a custom card does not silently inherit the built-in
card's chemistry. The card is the single source of the D:1 declaration.

New resolutions freeze `phosphate_intent` (schema 1, effective list, source
`recipe`/`dataset`/`none`, recipe id/version/frame and source/config SHA-256)
in each campaign `effective_config` and AutoMR `post_mr_plan`. The existing
`allow_op3_sites` field is the operational list, so PostMR, ReadySet validation,
AutoRefine, Doctor and manual children use the same permission unchanged.
Campaign loading validates recipe provenance against the frozen preset and
checks the effective list against its source. Execution does not consult the
current card to add permissions. CLI plan/status reports sites and their source.
`format_intent` always emits even an empty `allow_op3_sites` field, preventing
re-read snapshots from acquiring later defaults.

Old runs/plans lacking this additive provenance still use their original frozen
list (or no consent if absent). Do not patch an existing run or campaign in
place just because a recipe changed; prepare a fresh attempt with explicitly
selected chemistry. Failed ED run_002 remains historical evidence.

`campaigns.plan_campaign` composes existing AutoMR input discovery, intent parsing,
alias resolution and catalogue selection without allocating a scientific run.
Discovery is limited to immediate dataset children. A malformed or incomplete
dataset becomes `BLOCKED` while other entries are retained. The planner freezes
the dataset list, explicitly resolved settings, checksums and duplicate MTZ
groups. Per-file references use a campaign anchor and relative path; external
selected models and preset resources are snapshotted into plan storage.

`NASolveCampaign/plan.json` is an immutable schema-1 planning record. Publication
must not overwrite an existing plan or incomplete planning directory. The
manifest is exposed only after its resource snapshots are complete. Status
validates the existing record and input identities without rewriting it or
admitting new datasets. Relocation tests remove the old campaign, source preset
and model catalogue before checking the copied plan.

Planning commands do not discover Phenix/Coot, touch workspace settings, select
checkpoints or execute stages. `DISCOVERED` confirms only input and model
selection. Full model/symmetry/array validation and downstream chemistry gates
remain with the existing engines. The executor verifies the frozen plan before
consuming it and stores execution progress separately. See
[campaign planning](campaign-planning.md).

## Campaign execution contract

`campaign_execution` composes one frozen candidate per dataset through the
existing scientific engines. New campaign plans use **schema 2** and may contain
standard W/5W6W members, prepared nonstandard PDB+sequence members, or a mixture
of both; existing schema-1 W plans remain readable and executable. The
foreground executor is local and sequential, while individual Phenix stages
retain their normal processor allocation. Execution consumes the plan's frozen
resolved configuration and resource snapshots rather than rediscovering a model,
sequence source, frame catalogue, or project policy.

The validated default coordinator stage order is:

```text
preflight -> Phaser -> PostMR -> conditional AutoSol -> AutoRefine
```

Pine also contains a regression- and live-validated continuation from
`AUTOREFINE_REVIEW` into a campaign-owned `refine-doctor` stage. Guarded recipes
require an explicit endpoint and leave the recommendation unselected.
[Preset schema 2 full auto](campaign-full-auto.md) can instead freeze bounded
Doctor escalation and a separate provisional selection of its verified
passing recommendation. Core Doctor does not select a checkpoint; the campaign
records that action separately, with `user_approved=false`.

AutoSol is a **conditional stage gate**, not a mandatory scientific operation.
PostMR records whether a supported anomalous candidate exists. When it does not,
the campaign records accepted status `SKIPPED` and does not launch
`phenix.autosol`. When it does, the frozen AutoSol policy applies. A plain
`campaign run ROOT` uses the frozen recipe endpoint: AutoRefine for guarded
defaults, or Doctor when the full-auto recipe enables it. `--through STAGE`
explicitly overrides that endpoint.

Separate schema-1 execution state under `NASolveCampaign/execution/` records
the plan fingerprint, exact attempt/run ownership, stage progress, checkpoint,
diagnostic and inspection requirement. Atomic updates, campaign/dataset locks,
process identity and heartbeat records protect against competing execution and
expose interrupted work. Stage workers execute in owned process groups so
cancellation can terminate their external-tool children. A pause request
finishes the active stage before stopping.

Resumption verifies saved stage results and checksummed artifacts before
continuing. It never adopts an unrelated newest run, guesses artifacts by
basename, or overwrites an incomplete stage. An explicit retry preserves the
old attempt and schedules a new preflight with a fresh numbered run. Live or
uncertain prior processes prevent duplicate work. Whole-campaign relocation
requires all workers to be stopped first and preserves relative artifact
references; tool configuration is rediscovered on the current computer.

Under guarded policy, MR review, unaccepted AutoSol phases and refinement review
stop the affected dataset while other selected datasets continue. Full auto
may trial a usable borderline MR result without changing its raw classification,
continue without rejected phases, and run bounded Doctor under its frozen
permissions. Required chemistry and input-integrity checks remain in force.
A numerical pass records its selected checkpoint as `SOLVED` with both
`numerical_success = true` and `inspection_required = true`. Final structural
approval and deposition remain separate from numerical or provisional selection.
The existing observation, Free-R, chemistry and checkpoint selection
gates are preserved.

The executor still uses a fixed supported stage order. Schema 2 already freezes
the bounded full-auto permissions and derives the endpoint from that recipe.
A richer declarative conditional stage graph remains future work; it must
preserve per-dataset required-input checks and immutable stage provenance.

See [campaign execution](campaign-execution.md) for the command and recovery
contract.

## Project preset direction

The first planning preset makes a bounded set of project settings declarative.
Further frame and project policy should use data rather than additional
conditionals keyed to names such as `5W6W`. The current schema already freezes
W/nonstandard AutoMR defaults, PostMR policy, conditional
`autosol.policy = when-anomalous`, AutoRefine recipe/cycle count, resources and
declared chemistry.

A richer preset/workflow manifest could extend the current schema-2 bounded
policies into an explicit **campaign journey**. It should
be able to declare, in typed data:

- the intended terminal stage or terminal outcome for the campaign recipe;
- conditional stage transitions such as AutoSol only when PostMR evidence
  requires it;
- whether an unaccepted optional branch stops for inspection or may fall back
  to a reviewed ordinary path;
- bounded Doctor/recovery policies, retaining the existing separation between
  escalation and provisional-selection permissions; and
- human-facing recipe identity/version suitable for provenance and GUI display.

Further frame/project policy may also declare:

- model providers, exact-pair catalogues, fallbacks, and copy/symmetry policy;
- standard sites, chain sequences, and restraint resources or modes;
- reviewed construct-registration/cut recipes;
- metalation recipes and anomalous-element policy;
- the AutoSol sequence resource and phasing defaults; and
- imported external-provider provenance/capabilities.

The orchestration layers consume frozen models, targets, policy and capabilities.
This permits a new experimental campaign to ship a versioned preset/workflow
directory without changing common run allocation, provenance, safety gates,
Coot/Phenix isolation, or downstream reporting.

The GUI is a second control surface over this same contract. The **visual recipe builder**
may expose defaults, toggles and validated option sets, but it must serialize to
the same frozen backend workflow recipe and may not invent a GUI-only scientific
stage or policy. Likewise, interactive CLI transitions
(inspection, yes/no confirmation, continuation from review, Doctor inspection
and checkpoint selection) must map to equivalent backend actions in the GUI.

Model generation is not part of NASolve's runtime contract. A separate optional
NAPrep package may manage design/data records and externally generated model
candidates (including AlphaFold outputs), but NASolve consumes only the frozen
handoff and then owns the downstream crystallographic/campaign decision tree.

## Next development priorities

Earlier end-to-end local validation is preserved in
`history/validation-dohu.md`. Current validation state and the immediate
implementation edge are maintained in `development-handoff.md`.

Completed four-member native full-auto and campaign-owned Doctor evidence lives
in the [full-auto checkpoint](full-auto-patch-handoff.md). The current combined
modified-W test has passed prepared-bundle PostMR, generic-linkage/coverage
diagnostics and repaired 5CM/DF native interpretation. Bounded geometry
minimization completed, and the relaxed model has user-reported visual PASS.
A source-preserving DP replacement now passed native target/linkage checks;
its fresh geometry trial relieved the N5 conflict with preserved chirality/links.
The new model has user-reported base visual PASS; numerical sugar review,
full qualification and ordinary full-auto reproduction
remain open. The
[native ledger](native-modified-pair-live-validation.md) owns the exact scope.
Neither this diagnostic nor the four-member campaign closes the independent P2
source-native conversion or P5 geometry-diverse prepared-nonstandard gates.

After the combined geometry test, the proposed
[SMILES/graph audit](modified-component-preparation.md#proposed-smiles-and-cif-audit)
precedes the Topo/Scout work. Its initial assessor reports graph differences
separately from numerical geometry; subsequent separately tested integration
may regenerate and continue only under explicit bounded policy, preserving
source/candidate/native evidence. It must not invent chemical intent. The handoff
owns the complete ordering, including bounded Pine close-out and the blind
AlphaFold baseline; future features must not become extra merge gates.

Construct registration remains a later structural robustness layer: a cheap
non-mutating Registration Scout before Phaser, authoritative ASU Registration
on the MR solution before PostMR, a guided Registration Net for ambiguous
cases, and bounded Registration/Recut Rescue candidates only when ordinary MR
or representation mapping needs them. The merged Scout-v2 helper remains
experimental/non-runtime; current clean W runs must retain an identity-like fast
path.

The superseded campaign-state discussion is retained in the
[pre-reconciliation archive](history/architecture-2026-10-10-pre-reconciliation.md.txt).

Additional diagnostic-driven rescue policies and richer inspection summaries
remain later orchestration work; they do not reopen completed campaign-owned
Doctor or bounded full-auto validation.

Campaign orchestration should reuse frozen inputs, immutable numbered runs,
and checkpoint lineage, with resumable per-dataset progress and explicit
reporting of a blocked dataset. Supported residue mappings should run without
per-residue prompts; unavailable or ambiguous chemistry must retain a useful
diagnostic. Numerical readiness, recommended branches, and user inspection
must remain distinct states. Project presets should carry scientific policy
instead of adding project-name branches to the orchestration code.

NARestraints follow-up is separate from the completed PostMR connectivity fix.
User inspection of Q:E found a collapsed modified-base wobble arrangement with
suspect angles despite plausible contact distances; sulfur–nitrogen contact
targets also need review. Resolve these against atom identities, maps, and the
generated restraints before changing angle or distance targets. No such
restraint-target change is included here.

Reports should retain raw validation scores together with model and lattice
context. Simon identifies the DOHU structure as an intentionally interconnected
symmetry-related crystal, where the reported clashes are expected. That
interpretation belongs alongside inspection evidence; it does not require
altering the recorded clashscore. Future campaign acceptance policies should
be preset-specific and should preserve the distinction between numerical
acceptance and structural assessment.
