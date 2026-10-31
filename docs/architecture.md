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

### Future chemical references and restraints

A user-declared chemical reference must be able to seed a qualified restraints
bundle, with exact source/conversion provenance, chemical-state preservation,
explicit polymer context and NARestraints ownership. ChemDraw documents and
exported chemical representations are future input candidates; no format is
selected or implemented. Drawing-to-model construction is a separate workflow.
The [CIF Doctor scope](cif-doctor.md#future-chemical-reference-input) owns the
requirements and qualification boundary.

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
snapshot. Ordinary restoration now uses
postmr-source-graph-fragment-restoration-v1: source connectivity selects a
complete heavy base fragment attached only at C1-prime. A proper rigid transform
maps the raw Coot C1-prime/O4-prime/C2-prime frame to the parent frame. Restore
the parent sugar/backbone while moving the entire connected base together;
never partly overwrite it by shared atom names. Preserve raw base internal
geometry and attachment handedness within PDB rounding. Unsupported, ambiguous
or bridged-sugar sites retain their entire raw Coot site automatically with notes.
Canonical mutate_base backbone behavior and explicit curated sulfur/ring
placements keep their existing semantics. Restoration choices remain in the run
report; a dictionary or parent name never licenses a partial base copy.

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
Those geometry/native trials remain separate diagnostics. Ordinary PostMR now
uses the connected-base construction rule through the shared
`postmr.construct_postmr_model` API; fresh controls call that same API. C63 adds
source-proven internal-phosphate context preparation before transport, with
unchanged phosphate policy and automatic whole-raw-site fallback. See the
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
from a capsule without observations or a PostMR checkpoint. Returned C61
verifies all 3,406 payloads and the unchanged C60 parent; one fresh native worker
passes all 15 staged-layout checks with two finite repeatable evaluations of
the same serialized objective. The selected model/19 CIFs/14 PHILs retain their
exact bytes. Ordinary assessment stays REVIEW with solution notes; this does
not erase the inherited stopping or scientific limitations.

Ordinary `prepare_postmr` and fresh MTZ-free controls share
`construct_postmr_model`, including Coot construction and graph-selected rigid
base restoration. Returned C62 completes Coot 1.3.3, but unmatched OP3 causes
all three sites to retain their whole raw coordinates; it proves the fallback,
not successful base transport.

C63 adds postmr-source-graph-internal-phosphate-context-v1 to this ordinary
default path. Frozen inherited CONECT and unchanged unselected atom identities
permit selected-site serial normalization when needed. A discarded shadow
places only graph-matched scaffold coordinates in the frozen parent frame;
the unchanged phosphate sanitizer, with the frozen allowed-OP3/passthrough
policy, must prove the selected internal OP3 deletions. Transfer only those
deletions and authorized serial fields to original raw records, never shadow
coordinates. Then perform the existing proper whole-base transform and recheck
with the same sanitizer. Ambiguous/unsupported proof retains the complete raw
context with notes; curated special placements and independent ATL scope stay
intact. All source files remain immutable.

The controls use one fresh Coot construction process bounded at 600 seconds, leaving ordinary
default timing unchanged. The C63 saved-C62 context study is offline replay. Returned C63 separately
completes Coot 1.3.3: all three controls restore whole bases, three internal OP3
atoms are removed, serial authority and unchanged final sanitation pass, and no
raw fallback is selected. This is fresh construction evidence, not native
restraint or scientific geometry qualification. Completed composition reports distinguish observed
raw/context inventories; inspect-only remains unobserved. The narrow
cif-review-diagnostic-transport-v1 mapping preserves timestamped opaque Coot
backup names and bytes across relocation without relaxing scientific paths.
Dictionary chemistry, curated precedence, NARestraints authority, native kernels
and the qualified correction remain unchanged. No ReadySet, observations,
optimizer, new pairing/stacking policy or fabricated checkpoint is introduced.
C64 adds a separate native readback of that exact constructed model and the
canonical reference. Existing source-qualified site modifiers preserve the
numerical inputs; two fixed Phenix interpretations check all canonical backbone
links, selected heavy-atom proxies/effective definitions, triple targets and
finite repeatable energies/gradients. Native secondary-structure guessing stays
disabled; NARestraints remains authoritative and no pairing/stacking compilation
runs in this test. Native kernels, the plane correction and optimizers are
unchanged. Automatic resource repair/adoption and generic NAR compilation still
precede the planned fresh eight-pair full run.

Returned C64 completes both native interpretations and passes active triple
targets. Its six unaffected-proxy reviews arise from residue-name padding in
display labels. The shared cif-native-named-proxy-comparison-v1 signature binds
each label to its own index, then compares complete structured atom identities
with padding stripped, retaining ordered endpoints, all parameters, symmetry,
origins and multiplicities. Duplicate identities/indices and unbound labels fail.
All 3,148 unaffected terms match; no scientific tolerance or target changes.
C65 replays exact saved preparations, workers/specifications, input/result bytes
and implementation fingerprints before applying that comparison. It runs no
native process and preserves the old C64 verdict. This is a saved-data mechanics
qualification, not a new interpretation or production adoption.

Returned C65 preserves all 3,587 payloads and the exact C64 parent. Independent
maintained replay reproduces 93 PASS, zero REVIEW and three unsupported
formal-charge checks, with all 3,148 unaffected terms matching across eight
families. No new native process executes. The construction-only DP:C context
does not declare a supported pairing recipe; pairing integration must use
explicit supported intent, including the planned Z:P combination.


The bundle assessment summary distinguishes inherited native evidence from a
new native operation: native_selection is VERIFIED_SOURCE_CAPTURE and
native_selection_executed is false. Historical C61 receipts remain byte-identical;
this additive reporting correction does not change their selection or physics.

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

The shared `cif-qualified-dictionary-store-v1` component resolver now implements
persistent local reuse independently of ordinary PostMR orchestration. Its
semantic lookup binds source/state/authority, original-name graph mapping,
numerical recipe and generator family. Immutable entry digests additionally
bind numerical bytes, complete original producer and consumer provenance,
current isolated native evidence and stopping/limitations. Store publication
is atomic; corrupt/unusable entries are excluded without overwrite. Current
consumer or native-policy changes requalify saved numerics before generation,
including a combined Phenix upgrade; original producer provenance is retained.

The resolver consults this store before its verified acquisition callback and
freezes independently hash-bound relative run artifacts. Cache-write failure
retains a verified per-run copy. No site modifier or model is cached as reusable
component numerics; new coordinates need fresh geometry assessment and site
checks. Curated/explicit source authority remains upstream and in the key.
C66 separately exercises persistence, repeated reuse, invalidation and snapshot
portability for DP/PDU/5PC with inherited saved native fingerprints, without a
new native process or installed energy-library qualification. Ordinary automatic
acquisition/repair/adoption, pairing/stacking integration and solution PDF use
remain subsequent work. See [local repair reuse](cif-doctor.md#persistent-local-reuse-of-qualified-repairs).

Returned C66 verifies all 3,659 payloads and the unchanged C65 parent. All
30 source/authority/consumer/reuse controls reproduce under maintained code.
Nine returned snapshots resolve independently with exact numerical and
stopping evidence, every subprocess and external scientific read forbidden.
This closes component-reuse transport, without changing the ordinary
acquisition/adoption or current-site qualification boundary.


The opt-in [full-model NARestraints recipe](full-model-restraints.md) uses
`[automr] restraint_scope = all`, frozen through AutoMR and campaign resources,
or an explicit PostMR `--restraint-scope all` override. It supersedes frame
restraint selection for that invocation, requires registered nucleotide
identities, records NAR-guessed pairs and same-chain stacks without bridging
TER boundaries, and calls the existing explicit-site source/selector compiler.
Native secondary-structure guessing is disabled in its PHIL; no W scaffold
overlay is mixed into this policy. Conflicting modified-only/forced-geometry
choices fail before output allocation. Unpaired/unrestrained sites, guessing
warnings and absent symmetry search remain explicit. Source lookup no longer
requires a supported Coot construction parent; L-sugar mutation safeguards
remain unchanged. Existing inputs without the field preserve their semantics.
The new selection receipt is schema 1 with relative compiler paths; PostMR uses
run-anchored hashes. Chemical candidate adoption, refinement qualification and
periodic relationship discovery remain separate from recipe compilation.

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

### Ordinary dictionary acquisition preflight (Cedar 67)

Returned C67 verifies all **3,713 payloads**, including the unchanged C66
parent and manifest. The ordinary source selector passes **15/15 sources**
(six curated, nine installed CCD), and NARestraints compiles **8/8 declared
pairs and 16/16 stacking orientations**. Independent maintained replay
reproduces all 39 source/PHIL files exactly; report differences are limited
to historical source paths. DP/PDU/5PC saved repairs correctly miss because
their raw source bytes/authority differ; all inventoried chemical declarations
match. No repair is substituted by component name.
No native process or adoption occurs; full-run integration remains open.

The existing ligand_dictionary Path API delegates to the shared ligand_source
selector. Source priority is unchanged. Operational aliases share the same
complete role/context comparison as the existing diagnostic; the ordinary
NAR loader collapses only required equivalent records in memory. Unknown role
columns remain operational. Scalar and loop metadata must declare one exact
component, consistent with all component-labelled rows.

The source/role preflight freezes exact source bytes and compiler PHIL through
acquisition_directory references with hashes and sizes. It compares C66 repairs
through their original recipe/producer/consumer evidence without adopting them
or certifying a current runtime. A different source projection or authority can
correctly miss the cache. This leaves automatic recovery/adoption as subsequent
integration rather than treating a three-letter code as chemical authority.

## Ordinary source-to-numerics reuse (Cedar 68)

C68 adds an ordinary-source reuse API without weakening exact cache keys.
It selects the ordinary source first, verifies a saved projection against its
named chemistry and configuration, then requires current isolated native
usability before publishing a new source/authority-bound entry. Numerical bytes,
original producer and stopping notes are retained; repeats reuse them. Failed
candidates retain the selected source for standard preparation. No student
CIF inspection, generation, optimizer or production adoption is introduced.
Returned C68 preserves all 3,766 payloads and the complete C67 parent.
All three source projections pass, but native input/output placement triggers
the preservation guard before any worker launches. Its historical call count
of three records attempts; it supplies no fresh native qualification.
Returned C69 completes all three native reads: 63/63 usability checks and
six fixed repeat evaluations pass. A later reporting call supplies two mutually
exclusive auditor inputs, so source-bound publication/repeats are not selected.
Returned C70 verifies all 4,008 payloads and the complete C69 parent. DP,
PDU and 5PC each publish a qualified source-bound entry and immediately REUSE
the exact numerical bytes. Maintained code reproduces all 63 native checks,
both triple reports and 72 result artifacts; only explicitly nonoperational
source paths rebase. All six frozen copies resolve after original source/cache/
evidence removal with external scientific reads forbidden. Original producer
and stopping notes survive, including PDU nonconvergence. No new native process
runs. Current installation/site/model checks and ordinary PostMR/full-run
integration remain separate; no repeat of this saved cache gate is needed.

C71 connects local reuse to ordinary PostMR. Before ReadySet,
`prepare_postmr_dictionaries` selects and freezes ordinary sources, then checks
eligible source-bound cached numerics. Original sources still drive Coot and
remain in source receipts. The existing normalization/combination and dictionary
precedence receive cached numerical inputs only when their exact source,
authority, supported recipe/backend and current native consumer match.
Fresh version discovery is lazy and runs once per eligible batch; the selected
native dispatcher and all eight recorded API/three energy source hashes must
match inside the configured installation. This is the recorded identity scope,
not an exhaustive compiled-kernel or energy-library-data fingerprint.

Missing, corrupt, unsupported or changed-consumer entries retain ordinary
preparation with notes. Missing curated sources keep their existing refusal.
The cache is read-only and each run freezes independent relative/hash-bound
copies with original producer/stopping evidence. Nonconvergence remains a note;
no student inspects CIFs. PostMR records reuse/fallback and plain-language notes.
This adapter does not generate or optimize a dictionary. Uncached components
continue through the existing preparation path.

Methods: validate indexed entries against the selected source and the existing
isolated qualifier, verify the current recorded consumer identity, use the
existing automatic usable-candidate policy and exact-key resolver, then freeze
source and numerics separately. C71's explicit `--postmr-dictionary-reuse-only`
probe consumes exact returned C70 and calls this same ordinary API. The actual
Mac return verifies all three REUSED cases and POSTMR_CACHE_HANDOFF_PASS: exact
saved numerical bytes pass all 63 checks in three fresh Phenix 2.2.1-6174 native
readbacks. Six fixed energy/gradient evaluations are finite and exactly repeated;
all worker dispatcher/API/energy inventories match the selected recorded consumer.
Existing normalization changes none of the three dictionaries. The combined
31,252-byte ReadySet input reproduces exactly. Both triple/180-degree target
screens pass for PDU/5PC; linear-axis torsions and seed bending remain notes.

All 4,231 payloads, the unchanged C70 parent and 159 runtime members verify.
Reconstructing only NAR dirty-state metadata reproduces the reported runner SHA.
All three independent run copies resolve after original source/cache/evidence
removal with external scientific reads and every subprocess forbidden. Original
producer/stopping notes, including usable PDU nonconvergence, are unchanged.
No ReadySet, Coot, generator or optimizer executes in this probe. The next
boundary is observing ordinary ReadySet consumption/no-regeneration and current
linked/whole-model NARestraints membership. The eight-pair full run, refinement
and solution PDF remain separate. Inspect-only remains a captured-source fallback
check with no current-consumer/cache-hit/native claim. This returned-evidence
update changes no runtime, schema, chemistry, mechanics or dependency.

C72 methods: consume the exact verified C71 capsule and preserve all 4,231
payloads. Separate DP/PDU/5PC controls use the ordinary `_run_readyset` helper
and its unchanged CLI arguments. An optional private execution hook launches
the selected Phenix Python on the dispatcher's verified literal entrypoint as
`__main__`; the shell dispatcher itself is not executed. A process-local profile
observer records selected eLBOW builder/template calls, Python subprocess calls
and effective ReadySet actions. It replaces no native function and overrides no
native argument. Fresh bounded source snapshots and the recorded consumer
identity are verified before/after execution. An absent call is reported only
within this observer scope, never as exhaustive native/optimizer coverage.

The copied heavy seed omits H/D records while retaining exact heavy coordinates.
Require a completed untruncated observation, the requested actions, no observed
builder/template/child calls, unchanged named heavy sites and exact cached
numerics under ordinary parameterized-input precedence. Only then read back
effective terms on the unchanged C71 full-H seed, with current consumer checks,
the existing 21-check qualifier and separate triple screens. The native H sites
are saved control coordinates, not new ReadySet placements. Each of at most
three ReadySet calls is capped at 180 seconds; each fixed readback at 60 seconds.
There are no retries. Failed observations retain verified inputs and notes.

Frozen relative/hash-bound inputs, outputs, worker/spec and source evidence make
the diagnostic auditable. Inspect-only prepares three input controls without
any installed process or cache access. Default ordinary execution, chemical
definitions, target mechanics, native kernels and NARestraints remain unchanged.
No dependency, cache migration or NAR release is needed. Actual Mac consumption,
whole-model links and exact pairing/stacking, the eight-pair full live run,
refinement and solution PDF remain separate; students do not approve CIFs.

Returned C72 verifies all 4,482 payloads, unchanged C71 parent, 160 runtime
members and the reported runner SHA (only NAR dirty-state metadata differs).
The source scanner captured 24 files, including the routing module that imports
`elbow.command_line.builder`, but does not traverse that non-ReadySet module.
The required observer target is absent, so the source guard stops before any
ReadySet or fixed native readback. Preserve the original failure receipt and its
false completion/preservation flags; independent replay verifies the four copied
5PC inputs and complete C71 lineage without changing those recorded flags.

C73 methods: retain the bounded literal-import scan and explicitly freeze each
named observer module that it does not discover. Enforce the same selected-root,
32-file, 1 MiB per-file, 8 MiB total and before/after hash checks. Add explicit
observer-root/source metadata without claiming transitive or native-internal
coverage. The actual captured 24-file layout plus 13 identical prior builder
snapshots reproduces a 25-file source inventory without executing captured code.
A generic indirect-import fixture now covers both no-builder and observed-builder
paths; missing, escaped, oversized and changed sources remain blocked.

Returned C73 verifies 4,830 payloads, the unchanged C72 parent and reported
runner SHA; only recorded NAR dirty-state metadata differs from the clean build.
Three Phenix 2.2.1-6174 ReadySet controls complete with all 25 source proofs,
exact cached effective numerics, unchanged heavy sites and requested effective
actions. Maintained replay reproduces all 24 checks: 21 true and three false
no-subprocess checks. Each untruncated trace records one Popen constructor call,
zero builder/template calls, and no command or caller. The child activity remains
unclassified; no fixed native readback runs. Preserve the original receipt's
generic native_execution label while reading its explicit zero native counter.

C74 methods: observe literal subprocess arguments, executable, shell and cwd
separately, with bounded caller source/function/line metadata. Do not capture the
environment or call conversion methods on opaque values. Preserve bytes as hex
metadata; mark truncated or unsupported parameters explicitly. Cap 64 arguments,
2,048 characters/bytes each, 8,192 total before encoding and 16 caller frames;
retain the 128-event cap. These are constructor-call observations, not a child
completion or exhaustive native-internals proof. No native function or argument
is replaced, and the existing no-child acceptance rule remains unchanged.

Returned C74 verifies all 5,304 payloads, the exact C73 parent, runtime inventory
and reported runner checksum. Each completed control preserves cached numerics
and heavy sites and records the same literal system_profiler hardware query.
The five nearest caller frames lead through libtbx machine-memory introspection
to scitbx neighbor-grid initialization. The remaining import frames are truncated,
but the trace/event/parameter budgets are complete. C74 captures no source for
these three caller modules; its v1 no-child review and zero native-readback count
remain unchanged. Current upstream CCTBX source supports the memory-query purpose,
but does not establish identity with this installed Phenix version.

C75 methods: capture libtbx easy_run/introspection and scitbx cubicle_neighbors
with the same selected-root, 32-file/1 MiB each/8 MiB total and before/after hash
guards. Parse those frozen bytes without executing them. Require the literal
system_profiler program/hardware argument and the native producer, process-wrapper,
memory-constructor and neighbor-grid call structure. Match all five observed
caller paths/functions and call-line spans against this source. Require the exact
recorded shell command and complete literal parameters; deeper import-frame
truncation is permitted only after the complete checked prefix.

V2 keeps the seven other consumption checks and replaces the blanket no-child
guard with no unclassified subprocesses. Preserve every raw event/count; record
known resource queries separately. Extra commands, different programs/arguments,
nonempty loader prefixes, changed callers/sources or incomplete evidence retain
review. Old v1 reports remain readable and retain their original verdicts. No
native function, ordinary argument, numerical dictionary or target changes.

The C75 retry preserves exact C74 and all prior evidence, reuses verified C71
inputs and performs the same three bounded controls. Only passing controls receive
the unchanged fixed native checks on the unchanged full-H seeds. No installation,
generation, optimization or student CIF approval is requested. Returned C75
verifies all 5,949 payloads and the exact C74 parent. All three Phenix 2.2.1-6174
controls pass their eight checks. Each retains zero builder/template calls and
one source-proved resource query with zero unclassified children. Fresh native
readback passes all 63 usability checks and six finite repeated evaluations with
matching consumer identity. The 28-source installed snapshots, classifier and
native qualification replay as data; no captured Python is executed. Original
C73/C74 reviews, nonconvergence and retained torsion/bending notes remain intact.

C76 methods: resolve current-source-bound resources from exact C75 and the full
constructed model/canonical reference from the verified C63/C64 lineage. Reuse
the existing source-qualified site modifiers at DP A:6, 5PC A:7 and PDU A:9.
Require a fixed native readback to pass the unchanged construction qualifier
against the saved canonical reference, with freshly matching dispatcher/version,
eight API and three energy-source fingerprints. No Coot or optimizer is rerun.

Merge only the three prepared base dictionaries for one ordinary whole-model
ReadySet call. The bundle wrapper requires matching declared source/numerical
components and their presence in the model; it uses the same arguments, observer,
resource-query proof and eight consumption checks. A passing result receives one
fixed native readback with unchanged site modifiers and explicit PHILs. Require
all backbone links, exact projected site definitions and every ordered named
proxy/parameter/origin/symmetry/multiplicity in all eight families to survive.
Only display padding in structured identities is normalized. Both fixed reads
retain the existing finite/repeatable energy/gradient checks; no derivative or
scientific geometry verdict is inferred.

Select the checked endpoint only after every gate passes; otherwise retain the
verified constructed start with notes. Unverified starts cannot be selected.
Inspect-only prepares portable inputs and reports NOT_ASSESSED. This is at most
one ReadySet call (180 seconds) and two native reads (60 seconds each), with no
retry, generation or model optimization requested. No cache key/entry, numerical
target, ordinary production behavior or NARestraints policy changes. Pair/stack
guessing stays disabled; the intended eight-pair/16-stacking live-model membership
and full-run qualification remain separate. No student CIF approval is required.

Returned C76: all 6,691 payloads, exact C75 parent, clean runtime inventory and
reported runner identity verify. Native mechanics pass (93 PASS, three unsupported
formal-charge readbacks), including all 38 links and 3,148 unaffected named terms.
ReadySet finishes with unchanged heavy sites and exact cached numerical bytes,
but three builder calls fail the unchanged consumption guard. The verified
constructed model remains selected; the endpoint native readback was not run.
Its original REVIEW and decision are preserved, rather than relabeled as a pass.

C77 methods: freeze each already-prepared DP/PDU/5PC dictionary independently and
require one parameterized component per file, exact declared coverage and a
byte-identical recombination to the original combined dictionary. Supply separate
repeatable CIF arguments to the same ordinary helper. Native actions, observer,
resource-query proof, all eight consumption checks, site modifiers and native
qualifiers stay unchanged. The captured input reader registers one returned mol.id
per file and skips objects without id; together with C75/C76 traces this supports
a combined-container registration mismatch. The native parser return type was
not independently probed. C77 stops during staging; returned C78 establishes the
separate-file route below. At C77 delivery, default production orchestration still
supplied the combined path; C79 changes that narrow handoff.

The v2 report separates intentionally excluded serialized outputs from required
portable files. A v1 reader recognizes only exact matching nested exclusion
metadata for absent opaque payloads; no pickle is loaded. Saved preparation replay
also allows the existing 1e-12 bound for duplicated derived determinant/eigenvalue
notes only. Scientific bytes, parameters, hashes and verdicts stay exact. These
are compatibility and argument-transport changes; cache identity and chemical
mechanics remain unchanged. The same verified-start fallback and bounds apply.

C77 consumer transport failure and C78 methods: the reported macOS trace stops
in `stage_review_members` before the native phase, then its exception handler
repeats the long-path lookup. No C77 ZIP was created. The verified C76 archive
has a 939-byte logical member path; Linux transport checks did not impose the
consumer limit. This is transport evidence, not a new chemistry verdict.

Explicit `cif-review-member-transport-v2` stages all accepted members at bounded
hash-derived object paths. Its checked index binds exact logical names, sizes
and SHA-256 values; readers and archive export preserve every original byte/name
and manifest without materializing the historical path. The cached-model action
uses this layout and a shallow prerequisite view selected through the declared
C29 lineage prefix (1,174 files, maximum relative path 281 bytes). The legacy
v1 layout/backup-name exception remains supported, and scientific references
retain their strict validation. No captured Python or opaque backup is executed.

Bulk preservation validation reads each indexed payload once. Incomplete staging
reports false. Failure reporting prints the original exception first and writes
an owned atomic receipt. If complete collection is unavailable, a reduced-scope
failure ZIP retains the receipt and verified input members directly from memory;
it explicitly excludes uncollected outputs and never claims incomplete staging
was preserved. A ZIP-writing failure leaves the receipt and secondary diagnostic.
C78 repeats C77 on exact C76, retaining the same chemical definitions, separate
CIF arguments, native checks and automatic verified-start fallback. At delivery,
fresh Mac qualification was pending; returned C78 is recorded below. Prior failed
directories and runs stay untouched.

Returned C78 closes the explicit whole-model cached-dictionary/ReadySet gate.
The verified 8,741-payload archive preserves the exact C76 parent and manifest.
Phenix 2.2.1-6174 completes one ReadySet control and two fixed native readbacks.
All eight consumption checks pass with no observed builder/template calls and
one source-verified memory query. Before and after each pass 93 checks with only
three unsupported formal-charge readbacks; all 28 roundtrip checks pass. Exact
cached numerics, heavy coordinates, 38 backbone links and 3,148 unaffected named
restraints survive. The automatic decision selects `readyset_checked_model` with
notes. This evidence qualifies the preserved construction control, not an eight-pair
solution or a diffraction experiment.

C79 ordinary handoff methods: after shared source/cache acquisition and existing
normalization, pass the ordered complete component-file tuple (or no input when
empty) to the existing ordinary ReadySet helper. Include cached, curated and
uncached fallback files; do not reselect sources or infer coverage by filenames.
Keep the combined dictionary for assessment/refinement and its existing
`readyset_dictionary_input` receipt reference. Add ordered checksum-bound
`readyset_dictionary_inputs` references and `per-component-files-v1` policy so
receipts identify the operational arguments. Source authority, cache keys,
normalization, generic numerical-generation checks, effective precedence, native
mechanics and NARestraints are unchanged. Local validation passes 139 focused / 4,408 full tests, including five
fail-before cases and source-removed cold ordinary-route checks; no new native cycle is required only to repeat C78's
qualified argument representation.

C80 provides the separate explicitly mapped eight-pair construction fixture.
It starts from the packaged `MR_frames/5W6W/C_G.pdb`, whose twenty disjoint pairs
come from seventeen literal secondary-structure declarations and the three-pair
central stretch. The eight requested replacements bind sixteen unique internal
sites; twelve modified sites require Coot parent overlap and four canonical
partners already have the requested identity. Full annotated chain sequences and
all source/declaration hashes are frozen. Existing free-five-prime preparation
removes ten declared terminal atoms in a separate input; the public source frame
is preserved. The prior DP:C construction control is not reused as pair intent.

| Requested pair | Exact components | First site | Second site |
| --- | --- | --- | --- |
| K:X | CGY:DX | A:20 | D:3 |
| D:T | 1AP:DT | A:5 | C:11 |
| Z:P | DZ:DP | A:12 | B:4 |
| B:S | IGU:IMC | A:6 | C:10 |
| PDU:A | PDU:DA | D:5 | A:18 |
| 5PC:G | 5PC:DG | A:4 | C:12 |
| 5CM:Q | 5CM:S6G | A:7 | C:9 |
| F:A | DF:DA | A:19 | D:4 |

Methods: freeze the fifteen ordinary selected requested-component sources plus
canonical DC for background roles, preserving ordinary authority and priority.
The exact source copies feed the ordinary `construct_postmr_model` entrypoint for
one Coot construction with a deadline of at most 600 seconds. Ordinary Coot
version and embedded-Python validation probes are recorded separately. First
check global atom composition, metadata, unchanged unselected coordinates and
internal-phosphate context. Ten graph-selected sites use the existing independent
connected-fragment or exact whole-raw-site auditor. S6G at C:9 and DF at A:19 use
exact replays of their existing curated placement rules, frozen-parent scaffolds
and declared substitution bond intent. Their existing parent occupancy/B transfer
is checked by exact replay; rigid preservation of raw curated fragments is not
claimed. A separate identity check covers all sixteen requested sites. Audited
whole-raw-site fallback retains notes, while a failed mixed fixture cannot select
its canonical template as though the requested chemistry were built.

The original C80 mixed-batch regression fixes an ordinary-path serial-authority
error: explicitly mutated curated sites join serial collision repair. That
delivery still excludes them from graph/OP3 context candidates; C81's separately
recorded extension below applies only after the existing source-graph proofs.
Frozen passthrough sites remain excluded and final placement/sanitizer mechanics
are unchanged.

The new explicit-site compiler uses the pinned NARestraints role table and pair
recipes on the actual constructed PDB. It preserves twelve canonical background
pairs and compiles all twenty pairs. It also emits one mapped parallelity for
each of the thirty-eight declared consecutive-chain relationships, following
NARestraints' existing chain-order policy. Chain adjacency is declared topology;
it is not evidence that a physical stack or covalent link has been observed.
All emitted selectors bind to actual PDB atoms and frozen source graph roles.
Request indices are explicitly `PDB_RECORD_ORDER`, not native capture indices.
Native secondary-structure guessing is disabled in the resulting PHIL.

The earlier sixteen stacking orientations are two plane-order compiler controls
per requested pair. C80 writes them as separate files and never concatenates both
orders into the active policy. They are not sixteen physical stacking edges;
including both orders would duplicate restraints. The requested eight pair
recipes emit 38 angle, 22 bond and eight pair-parallelity requests. Native proxy
membership and achieved geometry are still unassessed.

`80_Cedar_probe_mixed_pairs.py` carries an independent frozen runtime and public
frame; it accepts no historical review capsule and reads no donor observations.
Inspect-only mode freezes the plan/sources without Coot. Fresh mode records one
construction and its PDB-selector compiler evidence, not a fabricated MR result
or completed NASolve run. Relative checksum-bound artifacts support independent
readback; existing opaque Coot-backup transport and first-error/failure capsules
preserve diagnostics. ATL remains an independent public source-graph control.
The mixed-context, existing-context and construction regression passes 53 tests
in 2.05 seconds after the new case fails before the serial-authority fix. Combined
focused validation passes 154 tests in 30.71 seconds, followed by one additional
fixture integration test. The four new files contain 68 cases: twenty-one fixture,
thirty-one compiler, twelve delivery and four mixed-context cases. These groups
overlap and their counts are not additive.

Source-removed inspect-only validation passes with 162 frozen runtime members
and fifty capsule payloads, all subprocesses forbidden, a poisoned ambient import
path, aliased temporary directory and macOS path budgets. A standalone reader
passes after the source clones are removed. It uses fifteen exact ordinary C67
component sources and an explicit synthetic nonnative DC fixture; it establishes
transport and plan integrity, not chemical or native SDK qualification. The full
suite passes 4,475 tests, with two skips and 276 subtests, in 420.39 seconds. One
integration test added after collection passes separately in 1.99 seconds, with
no production-code change; these two runs cover all current test cases. Maintained
C76 and prior-lineage replay also pass with every subprocess forbidden and no
captured Python executed. These are the original local-delivery checks. Returned
Mac C80 completes Coot 1.3.3 and verifies all 138 capsule payloads, its frozen
runtime, source/preflight artifacts and all forty-two final site identities.
Maintained replay reproduces the original context receipt and all twelve
restoration-rule outcomes exactly without executing captured Python or a new
external process. The original REVIEW receipt remains unchanged.

The context transaction retains raw coordinates because curated DF A:19 has an
implausibly short raw incoming O3'-P distance in the proof shadow. Eight generic
sites therefore retain their whole raw site; only 5PC A:4 and IGU A:6 exercise
graph transport. Both curated placement rules complete, but DF retains OP3,
which has no frozen-parent counterpart. The independent scaffold guard correctly
stops here. Common DF scaffold coordinates and the entire S6G C:9 scaffold match
their frozen parents exactly. This is an unproved polymer context, not permission
to relax the guard. Constructed twenty-pair policy compilation does not run;
the separate source-only eight-pair/sixteen-orientation preflight does pass.

C81 extends the ordinary context eligibility check to explicit source-validated
curated DNA. Methods: run the same source-connectivity and discarded proper-frame
transport preflight used for supported DNA sites; build a discarded shadow with
only exact frozen-parent scaffold coordinates; let the existing phosphate
sanitizer prove selected internal OP3 removals. Transfer only those exact deletions
and independently authorized selected serial fields to the original raw records.
Retained raw coordinates and metadata stay exact. The unchanged graph transport
and explicit curated final placement rules then run, followed by the unchanged
final sanitizer recheck. Source graph, parent correspondence, inherited CONECT,
unselected identity/coordinates, frozen passthrough and phosphate-intent guards
remain active. A failed proof retains the complete raw context transaction.

The additive `curated_context` receipt uses
`postmr-source-graph-curated-phosphate-context-v1` and binds eligible/candidate
sites to exact source and parent hashes, scaffold atoms and discarded preflight.
It records context scope only; it does not turn curated final placements into
generic rigid-fragment transport. Generic-only and invalid-curated source
receipts keep their existing scope. No component-specific oxygen exception,
source dictionary edit, target change or native-mechanics change is introduced.

The C81 delivery uses the same builder and independent source runtime with
`--delivery-prefix 81_Cedar`, no historical review ZIP and one fresh Coot
construction. Exact saved-C80 replay is private local evidence, not a new public
replay API or fresh native result. Final combined focused validation passes 132
cases in 26.45 seconds, including eight new curated-context cases and seven new
receipt-binding cases. The source/parent/site/candidate/scope checks are independently
audited; tampered declarations are rejected. Original fail-before evidence is
preserved separately from overlapping focused totals.

Current maintained replay on exact saved-C80 bytes proves nine internal OP3
deletions and 267 selected serial repairs, with original sources, raw coordinates
and parent snapshots preserved. All ten graph transports and both existing curated
rules pass the independent mixed audit, with no whole-raw-site fallback. The same
phosphate auditor rechecks all nine final sites and changes no candidate bytes.
All twenty declared pairs, thirty-eight chain-adjacency stacks and sixteen separate
orientation controls compile and pass portable readback. This uses no captured
Python or new Coot/Phenix/ReadySet process and establishes no active native
membership. Source-removed cold replay passes on code checkpoint
`b568129b639aba400680b61b90378f7486f70d8c` using all sixteen exact C80 source
files, including captured background DC. Both build clones are removed before
launch; original repository/archive reads and subprocesses are forbidden, ambient
imports are poisoned, and an aliased temporary path passes macOS byte budgets.
The complete context/restoration/audit/compiler result reproduces, and standalone
policy readback passes after original scientific inputs, candidate and runtime
paths are removed. Everyday edits, configuration and component storage are
preserved. This uses no synthetic DC and provides no fresh SDK qualification.
Maintained C76 and all prior-lineage checks also pass under the current code,
with subprocesses forbidden and original reviews/fallbacks preserved. The full
suite passes 4,491 tests, two skips and 276 subtests in 424.25 seconds. All fifteen
new cases are collected before launch; no supplement is needed. These original
local checks remain separate from the subsequent Mac return.

Returned C81 verifies all 175 payloads and completes Coot 1.3.3. Independent
trusted-source replay reproduces nine OP3 deletions, 267 selected serial repairs,
ten graph transports and both curated rules, with no raw fallback. All forty-two
site identities and the twenty-pair/thirty-eight-stack policy match the declared
fixture; all sixteen plane-order controls remain separate from the active policy.
The final model matches the private saved-data prediction exactly. No ReadySet or
native interpretation ran in C81. Active native dictionary/link/triple-target and
pair/stack membership, ordinary end-to-end execution, observations/refinement,
solution PDF and scientific qualification remain separate. Students do not inspect
or approve CIF tables.

C82 connects that exact construction to the ordinary numerical handoff. Its
independent `build_mixed_native_probe.py` ferry reads the exact verified C81 ZIP
as data, preserves it through indexed transport and materializes a shallow
scientific view. It freezes the constructed model, all sixteen source components
and the active NARestraints PHIL without another Coot process. `--inspect-only`
stages and checks these inputs without discovering or running an external SDK.

Methods: call the existing ordinary ReadySet helper once with separate component
CIF arguments and its unchanged hydrogen/ligand actions. Preserve parameterized
input precedence through the ordinary effective-dictionary selector; source-only
CCD graphs may require native numerical generation. All sixteen still enter
ReadySet; omit only exact single-component, unparameterized canonical CCD graphs
from native dictionary arguments so the installed canonical numerical library
remains authoritative. Never rewrite a mixed container. Retain raw generated output
and per-component source comparisons, including chemical-state differences.
Compare actual native site definitions to the effective inputs; context mismatches
remain review findings, without a site-modifier or DNA-header repair in this slice.
Require unchanged named heavy coordinates and complete modified-component numerics
before at most two fixed native reads: secondary-structure guessing disabled,
then the same inputs plus the exact explicit NAR policy. Resolve that policy's
selections against fresh native atoms; compiler PDB-order indices are never reused.
The existing membership qualifier requires the exact added requests, every
unaffected proxy and no competing native secondary-structure terms. Separate
checks cover the declared backbone links, effective site inventory, finite
parameters/repeated evaluations and PDU/5PC triple targets. The sixteen separate
plane-order controls do not enter the active policy.

ReadySet has a maximum 600-second deadline; each fixed interpretation has at most
60 seconds. This test may generate dictionaries but requests no model optimization,
refinement or checkpoint. Chemical-source changes cannot be hidden by a native
membership pass, and the original constructed model remains available with notes
without a student CIF gate. Native internal operations are not exhaustively
instrumented. Final local validation on code checkpoint
`3aabb468ee668e12db3fa0ef2fd14448ad868f20` passes 188 focused tests and the complete
4,519-test suite (two skips, 276 subtests, 406.52 seconds), with all twenty-eight
new cases collected before launch. Source-removed cold preparation preserves all
sixteen actual C81 sources, the exact constructed model and declared policy;
all 175 parent payloads and its manifest survive, with no captured program
materialized into the scientific view. The prepared reader still passes after
original sources, fixture, session and runtime are removed. Configuration, everyday
edits and component storage remain untouched; simulated macOS path checks pass.
These original packaging/prepared-input and fake-tool checks use no local Phenix
or Coot. The subsequent C82 return and C83 recovery boundary are recorded below.
Returned C82 verifies all 364 payloads and the exact runtime, with ordinary
effective-authority replay matching the saved bytes. Its single Phenix 2.2.1-6174
ReadySet call completes in 65.95 seconds with unchanged named heavy coordinates.
The nested C81 manifest verifies all 175 parent payloads; the original C81 ZIP is
absent from this verification snapshot, so direct original-archive comparison is
not claimed. IGU alone fails numerical capability: its generated C2/N3 coordinates
coincide and the written C2–N3 target is 0.000 Å with 0.020 Å ESD. Source ideal,
source model and constructed distances are 1.327, 1.361 and 1.362 Å respectively.
Other generated IGU bonds stretch to 1.9–2.5 Å. The guard correctly prevents every
fixed native interpretation; the original REVIEW remains immutable. Phosphate
hydrogen/charge changes in generated definitions are separate source-state
findings. The saved evidence does not identify a specific native causal step or
prove a SMILES/seed defect.

C83 tests a separate source-preserving recovery for the saved numerically deficient
component set, currently IGU, through `audit_mixed_recovery` and its source-bundled
`build_mixed_recovery_probe.py` ferry. Read the exact C82 capsule as data, preserve
its full logical members through indexed transport, and use a temporary shallow
scientific view outside the new returned session. Explicit 128 MiB total and
32 MiB member limits accommodate the verified 52.9 MB parent and 20.8 MB receipt;
checksums, safe names and the exact input archive pin remain required.
Selection recomputes hard capability failures from the actual frozen numerical
rows, independent of residue code. Renamed-component, multiple-failure and valid-
bystander regressions protect the same general rule; at most four components
may enter a single bounded recovery. IGU is the observed case, with no exception.

Methods: freshly probe the selected installed Python-library anchor and capture
four complete-builder source modules as hash-bound text. This supplies new
installation evidence, not borrowed historical qualification. Reuse the existing
source-native complete-candidate adapter: the explicit source reader, declared
charge handoff and prepared-object CCTBX route feed the native complete builder
with original source ideal geometry. The source graph, names, charge, protonation
and stereo declarations remain authoritative. The default bounded block is 180
steps with at most 600 seconds per selected component. Retain regular written
outputs and stopping evidence across nonconvergence and worker failure. A usable
candidate is tested at source-seed and generated-output coordinates through the
existing isolated native qualifier, finite repeated evaluations, exact fixed
covalent-proxy comparison and automatic decision-with-notes. Each read has at most
60 seconds; secondary-structure guessing stays disabled. The resource-anchor
probe and generator help/version checks are separate from these fixed reads.

The mixed constructed model and all original dictionaries remain unchanged.
This slice requests no new Coot or ReadySet run, model optimization, linked/full
scaffold substitution, component-store publication, refinement or production
checkpoint. Isolated usability is not full NAR membership or scientific approval;
other C82 source-state reviews remain open. Local focused validation passes 242
tests in 28.86 seconds on code checkpoint
`6b941bcc37a6603ca24ecc3b4245eeeef8c3f7f0`. The frozen full suite passes
4,553 tests, two skips and 276 subtests in 520.98 seconds, including all thirty-four
new recovery/ferry cases. Earlier fail-before runs record eighteen recovery and
ten ferry failures on C82; those are distinct from the expanded final case set.
Source-removed cold preparation/readback passes with 163 frozen runtime members
and a 398-payload capsule preserving all 364 parent payloads exactly. All
subprocesses are forbidden; the standalone reader survives parent/session/runtime
removal.
Configuration, everyday edits and storage are preserved, with 52,410 simulated
macOS path operations bounded at 210 absolute/68 component bytes. These are
packaging and prepared-input checks; the subsequent fresh C83 result and C84
linked-mechanics boundary are recorded below.

Returned C83 verifies all 445 payloads, the exact 163-member runtime and the
complete C82 parent: all 364 payloads plus its manifest remain byte-identical.
Maintained trusted-source replay reproduces the source pins, prepared-object
worker, candidate and isolated decision without executing captured Python.
The Phenix 2.2.1-6174 source-native complete builder finishes in 20.95 seconds
with exit zero and stopping `NOT_REPORTED`. It preserves the neutral source's
37 atoms, 39 bonds, formal charges and finished source-relative sugar
configuration. The recovered C2–N3 target is 1.397 Å / 0.030 Å ESD; the original
zero target remains immutable in C82. Source-seed and generated-output native
reads each pass all twenty-one usability checks and two finite repeated fixed
energy/gradient evaluations, with the same covalent proxies and installed API
sources. Native formal-charge readback remains unsupported. NASolve selects
`source_native_generated` with `CONTINUE_WITH_NOTES`, without student CIF review.
This is isolated usability: the written group is still non-polymer despite native
DNA classification, and A:6 requires explicit source-qualified internal context.
Convergence, independent absolute CIP, other source-state findings and linked
mixed-model membership remain separate.

C84 tests that remaining linked mechanics boundary in a separate bundle. Select
recovered components from the verified isolated choices and actual model sites,
independently of residue name; IGU is the current observed case. Reuse existing
`prepare_linked_component` source-qualified DNA metadata and site-context
preparation. Replace only the selected component definitions in copied mixed
containers, preserving every unselected parsed row and unrelated resource byte.
The exact constructed coordinates, frozen plan and declared NARestraints
pairing/stacking policy remain unchanged. Only recovered-component metadata is
projected; unrelated non-polymer/ligand groups and the existing full-model DNA
classification gate are retained. Overall REVIEW may therefore coexist with
passing specific link/NAR checks. No general header or source-state repair is
claimed. An additive optional `site_projections` argument binds the existing
mixed native qualifier to exact declared site/component projections; calls
without it retain their original behavior. Retained parsed block text is exact
after the existing reader's newline normalization and trailing CR/LF separator
trimming; unselected parsed rows are exact.
Parent report/source hashes bind preserved findings without using derived
floating geometry as a content identity.

Methods: `audit_mixed_linked_recovery` reads the same prepared bundle twice at
fixed coordinates: the baseline disables declared NA additions, and the active
read uses the original NARestraints policy and declared contexts. Native
secondary-structure guessing stays disabled in both. Supported nonbranched
contexts follow frozen declared incoming/outgoing topology and exact terminal
inventory; ambiguous or branched contexts require a wider explicit adapter.
Require exact named native membership/link checks, finite fixed evaluations,
selected modifiers/heavy proxies and linked-phosphate neighbor/angle coverage.
Each interpretation has at most sixty seconds. The existing unsupported-formal-charge allowance is
retained without claiming native charge confirmation. Chemical-state findings
remain visible separately from mechanics. The ferry accepts the exact C83 ZIP,
explicit Phenix root, native deadline and inspect-only mode, with no generation/step flags. Parent transport
retains 128 MiB total / 32 MiB member limits and all original payloads; compact
report references avoid another large receipt copy. Keep the original model and
resources available with notes. This diagnostic requests no Coot, ReadySet, generation,
model optimization, component-store publication, production adoption,
refinement or diffraction input. Local focused validation passes 343 tests in
45.73 seconds across sixteen files on code checkpoint
`2ba5f388405196f550bd98cde7bf64c8ff45748c`. All forty-five new cases (thirty-two
module, thirteen ferry) are frozen before full-suite collection. The full suite
passes 4,598 tests, two skips and 276 subtests in 637.71 seconds, with no source,
script or test changes after the checkpoint and no post-collection supplement. Source-removed cold preparation and standalone readback pass with
164 frozen runtime members and a 543-payload capsule preserving all 445 C83
payloads plus its manifest exactly. The original sixteen sources, nine effective
dictionary files, model, plan and active/disabled policy remain intact. The IGU
internal A:6 projection has 34 atoms/22 heavy atoms, removes only `OP3`, `HOP3`
and `HO3'`, and retains `HOP2`. Source clones are absent and all subprocesses are forbidden.
Configuration, everyday edits and the component store remain unchanged; 88,707
simulated macOS path operations stay within 237 absolute/68 component bytes.
Standalone readback succeeds after parent/archive/session/runtime removal and
explicit retirement of owned temporary views. Private OS instrumentation
disturbed temporary cleanup, so guarded automatic cleanup is not qualified;
no product cleanup defect is inferred. These original prepared-input/fake-tool
checks are not SDK qualification; the actual C84 return and next replay boundary
are recorded below.

The original C84 report contract is
`cif-mixed-linked-component-recovery-v1`, stored in `mixed_linked_recovery.json`
under the `mixed_linked_recovery_directory` anchor. Its portable reader verifies
exact frozen selection, preparation, native input/specification/output and
qualification; a mechanics pass does not adopt the bundle.

Returned C84 verifies all 580 payloads, the exact 164-member runtime and the
complete C83 parent (445 payloads plus its manifest). Both Phenix 2.2.1-6174
fixed reads complete with exit zero in 4.35 and 1.52 seconds, each recording 863
atoms, forty-two sites and two fixed evaluations. The same prepared bundle
preserves the model and sixteen source files. All thirty-eight backbone links,
exact declared NARestraints additions, selected linked projections and active
PDU/5PC triple targets pass. Full membership still records REVIEW on four
baseline/active heavy-coverage and DNA-group gates. Actual native classification
is DNA at all forty-two sites, with no unexpected atoms. The recorded group fields retain six non-polymer
components and one ligand, and ten sites record only OP3 missing against their
effective definitions. Selected IGU A:6 has DNA group/classification and complete
heavy inventory. Keep those existing four verdicts unchanged pending separate
group/context coverage work. The automatic coordinate decision retains the
verified constructed model with notes; no bundle is adopted.

The subsequent report-reader exception is separate. Two UNSUPPORTED
formal-charge evidence lists contain identical complete rows for thirty-four
unique atoms each, but their order changes from the preparation dictionary's
insertion order to JSON's sorted keys. Sixty-six positional differences are
confined to those two `unavailable` lists; all other qualification fields and
verdicts match exactly. Formal-charge readback remains unsupported, with no new
contradiction. Preserve the failed receipt and original REVIEW; do not relax
coverage or DNA-classification gates to repair evidence ordering.

C85 makes that evidence deterministic and replays the saved native work. The
mixed-linked qualification writer orders atom-keyed formal-charge evidence
by atom ID. The shared `site_definition_checks` helper and its other legacy
consumers stay unchanged. A narrow legacy comparison accepts permutations only
in the named formal-charge `unavailable` and `contradictions` evidence lists,
with unique atom IDs and exact complete row types, values, statuses and every
other field/list order. This rule supports valid site identities, including
insertion codes, independently of residue code; it does not sort native proxies,
promote a verdict or make chemistry changes.

Methods: build the existing linked-recovery ferry with `--delivery-prefix
85_Cedar` and run `--saved-native-only` against the exact verified C84 archive.
Preserve the complete parent, including its failed receipt, through indexed
transport. The maintained reader verifies saved preparation, native inputs,
worker/specification/output bindings and qualification using a temporary shallow
view outside the returned session. Emit only a compact `saved_linked_recovery.json`
summary with hash-bound logical report/qualification references under
`preserved_review`; the probe receipt points to that summary under
`probe_directory`. The schema-1 policy is `cif-saved-mixed-linked-recovery-v1`.
Historical native calls remain two and new calls remain zero. No scientific
subtree is copied into the new result, and no new public replay API is added.

C85 requests no SDK discovery, native process, Coot, ReadySet, generation,
coordinate optimization, store write, adoption or refinement. It preserves the
C84 REVIEW and all four hard failures, without a PDU/5PC or broader state/header
fix. Final focused validation passes 395 tests in 26.83 seconds across sixteen
files on `919cd7a96f0609e76e91afaeacba1af24b5e66f6`. All thirty-eight new cases
(twenty module, eighteen ferry) are frozen before full-suite collection. The full
suite passes 4,636 tests, two skips and 276 subtests in 627.18 seconds, with no
source/script/test changes after the checkpoint or post-collection supplement. Independent actual-C84 replay preserves all 132 scientific files,
the original REVIEW and all four gates with zero processes. Source-removed cold
ferry/readback also passes with 164 runtime members and a 584-payload capsule
preserving all 580 C84 payloads plus its manifest exactly. Both historical native
captures remain exact; no SDK is discovered and no process starts. Configuration,
everyday edits and the store remain intact; 78,013 simulated macOS path operations
stay within 220 absolute/68 component bytes. Standalone readback passes after
parent/archive/session/runtime removal and explicit owned-view retirement; guarded
automatic temporary cleanup is not claimed. These original local checks are
preserved; the actual C85 return and source-bound context boundary are below.

Returned C85 verifies all 584 payloads and the exact 580-payload C84 parent plus
its manifest. Saved-summary and scientific-reader replay match exactly with zero
new native calls and two historical calls. All 132 scientific files, original
qualification hash, model and fallback decision remain unchanged. The same four
coverage/written-group gates retain REVIEW; source-state findings and scientific
qualification are not promoted. The saved replay path is now observed on the
user's Mac without SDK execution.

C86 tests only source-declared group metadata and incoming-phosphate context.
Selection follows the exact old native findings and frozen model topology,
independently of residue code: the current fixture selects eleven components,
ten incoming OP3 site modifications and seven group changes. Four canonical
components and the already-qualified IGU context remain unchanged. Require
explicit source DNA declarations and the original strict `source_graph_fragment`
for a complete unbridged deoxy sugar, one base at C1 and ordinary phosphate.
Bind the effective heavy atom names/elements, heavy-atom adjacency and relevant
phosphate endpoints, allowing only the already-recorded source OP3 omission.
These are context-eligibility checks; existing DF aromatic-sugar/six-delocalized-
phosphate findings and all other chemical-state reviews remain recorded.

The separate preparation changes only group metadata to source-declared DNA and
applies site-specific deletion of incoming OP3 plus hydrogens attached to that
atom. `_chem_comp.type`, outgoing O3′ hydrogen/energy type, surviving charges,
bond orders, stereo and all surviving numerical rows remain unchanged. No
whole-component OP3 deletion or broader source-state recipe is introduced.
Preserve all surviving parsed rows and bystanders, the exact constructed
coordinates, plan and original NARestraints policy.

Methods: `audit_mixed_context(linked_parent_directory, phenix, output, *,
timeout_seconds=60)` prepares a new result bound to the exact C84 native/effective
inputs retained inside C85. At most two fresh Phenix reads use the same prepared
bundle with declared NA additions disabled or the original active policy, keeping
native secondary-structure guessing disabled. Compare each new read with its
corresponding saved C84 read: all eight structured named-proxy families must be
exact, with exact structured atom inventories and energy proxy counts. Fixed
same-policy total/category targets and named gradients must satisfy the
established energy-repeat tolerance. These comparisons are at fixed coordinates;
nonbonded pair identities are not independently compared. Apply the existing
strict full qualifier, including backbone links, NAR additions, definitions,
group and coverage gates, without relaxation. Local SDK execution is unavailable;
actual Mac equivalence and mechanics remain unassessed until their native return.

The report is `mixed_context.json`, policy `cif-mixed-linked-context-v1`, under
`mixed_context_directory`. `read_mixed_context(directory, *,
linked_parent_directory)` requires its explicit hash-bound external parent anchor.
The ferry preserves the complete C85 parent once through indexed transport and
materializes only a temporary external C84 view; it does not copy the old 31 MB
scientific subtree into the new result. Status is `PREPARED_ONLY`, `REVIEW` or
`MIXED_CONTEXT_MECHANICS_PASS`. No Coot, ReadySet, generation, optimization, store
write, adoption, refinement or diffraction input is requested. Actual Mac C86
fixed-native checks remain pending; scientific qualification and ordinary
end-to-end solving remain separate.

Final local validation passes 413 focused tests in 31.60 seconds and 4,710 full
tests (two skips, 276 subtests) in 555.57 seconds on
`ffeb6e9f7d7c180985743baf64e99df94284d887`. All seventy-four final new cases
are frozen before full collection, with no later source/script/test changes or
supplement. Generic selection, source/adjacency binding, terminal preservation,
unchanged bystanders, exact row scope and anchored reader controls are covered.
Copied saved-native-record controls accept consistent reindexing/padding and
reject coordinate, target, canceling-category and count changes; these checks
provide no fresh SDK qualification.

Source-removed cold preparation/readback passes with 165 runtime members and a
643-payload capsule preserving all 584 C85 payloads plus its manifest exactly.
The new context data are 452,735 bytes, without a second old scientific subtree;
eleven selected components, seven group changes and ten OP3 site modifications
reproduce with canonical/IGU resources unchanged. SDK/native/other process calls
remain zero. Configuration, everyday edits and store fixtures survive; 112,812
simulated macOS path operations stay within 217 absolute/68 component bytes.
Standalone readback reconstructs its explicit parent from the copied new capsule
after original ZIP/session/runtime removal and explicit owned-view retirement;
guarded automatic temporary cleanup is not claimed. Prepared-input and fake-tool
QA remain separate from installed native execution. These original C86 local
checks are preserved; the subsequent return and C87 boundary are below.

Returned C86 stops at a native modifier grammar boundary before model
interpretation. Its first Phenix 2.2.1-6174 worker exits two while loading the
1AP OP3-only modification; the active read and full qualification do not run.
Biopython's `MMCIFIO` serializes a category containing one row as scalar items.
The native modification reader expects a loop table, so its conversion returns
no table object before `atom_list` access. This is a serialization failure;
it supplies no new verdict on the model's coordinates or restraint parameters.
All 697 payloads and the exact 584-payload C85 parent plus its manifest verify.
The context and parent readers reproduce exactly with zero verification
processes; all 110 context files and the fallback remain unchanged. All ten new
OP3-only modifiers have the same scalar shape. Original C86 local validation
remains unchanged, and the return supplies no new model/energy qualification.

C87 makes the modifier grammar independent of row count. Every nonempty
`_chem_mod_atom` category is written as an explicit `loop_` table, for both
single-row and multiple-row deletions. Keep the same MMCIF value formatter and
require one nonempty rectangular atom-modification category. Parsed rows and
modifier IDs are unchanged.
The shared `_emit`, previous linked preparation, native kernels, source selection,
chemical state and all strict mechanics/qualification gates stay unchanged.
Existing DF source-state findings and the verified fallback remain separate.

Methods: the context writer records `cif-mixed-linked-context-v2` in the existing
schema-1 `mixed_context.json`. The maintained reader accepts v1 and v2 and
regenerates each using its recorded policy. Legacy
`cif-mixed-linked-context-v1` retains its exact scalar serialization and original
failed report bytes; replaying it does not relabel the old attempt as successful.
V2 artifacts require the updated reader; legacy files are not migrated.
The public audit/reader signatures, `mixed_context_directory` local anchor and
required hash-bound `linked_parent_directory` anchor remain unchanged.

Build the existing `scripts/build_mixed_context_probe.py` with explicit
`--delivery-prefix 87_Cedar`; the builder default remains `86_Cedar` for
compatibility. The ferry verifies the exact failed C86 capsule as data through
the v1 reader, preserves every payload once with indexed transport, and prepares
a separate v2 retry. A temporary external C84 view avoids copying the old
scientific subtree. At most two fresh fixed native reads, sixty seconds each,
use the same disabled/original active NARestraints policy and existing native
secondary-structure settings. Require unchanged structured atom/proxy inventories,
fixed-coordinate total/category targets, named gradients and strict full
qualification. Nonbonded pair identities are not independently compared.
No Coot, ReadySet, generation, optimization, cache write, adoption, refinement
or scientific qualification is requested. Actual Mac C87 modifier parsing and
native context qualification remain pending.

Final local validation passes 451 focused tests in 32.33 seconds and 4,748 full
tests (two skips, 276 subtests) in 641.54 seconds on
`b8da8cb21b69087248ddcd9e4c5d0ff40b422ef1`. All thirty-eight final new cases
are frozen before full collection, with no later source/script/test changes or
supplement. Generic single/multiple-row grammar, token formatting, exact legacy
replay, input binding, failure preservation and strict unchanged mechanics are
covered. Initial fail-before subsets remain separate from the final case count.

Source-removed cold preparation/readback passes with 165 runtime members and a
756-payload capsule preserving all 697 C86 payloads plus its manifest exactly.
Its 452,195 bytes of new context data contain ten explicit one-row modifier loops;
base dictionaries, projected definitions, site PHIL, canonical/IGU resources and
the one no-op remain unchanged. No old scientific subtree is duplicated and no
SDK/native/other process starts. Configuration, everyday edits and store fixtures
survive; 141,546 simulated macOS path operations stay within 217 absolute/68
component bytes. Standalone legacy v1 and new v2 readers pass from the copied
new capsule after original ZIP/session/runtime removal and explicit owned-view
retirement; guarded automatic temporary cleanup is not claimed. These are local
grammar/preparation/replay checks, not fresh installed native qualification. These
original local checks remain preserved; the actual C87 return is below.

Returned C87 completes both Phenix 2.2.1-6174 reads with
`MIXED_CONTEXT_MECHANICS_PASS`. All 865 payloads and the complete 697-payload C86
parent plus its manifest verify. The workers exit zero in 3.962889 / 1.460846
seconds, each with 863 atoms, forty-two complete DNA sites and two fixed energy
snapshots. All thirty-four membership checks and all twenty saved-parent
equivalence checks on each side pass. The qualification contains 291 PASS and
24 unsupported formal-charge checks, with no contradiction. Source-state
findings and scientific qualification remain separate; no optimization,
refinement or adoption occurs.

The envelope fails later on check-row order: site-projection insertion order
changes when JSON sorts map keys, moving 132 positions among 315 unique complete
check rows. Every row matches recursively by full check ID, including value
types and nested list order; every other qualification field and the PASS verdict
are identical. Preserve the failed receipt and original report/qualification
bytes. The native-mechanics PASS precedes this replay error. Original C87 local
validation remains unchanged, with the actual return recorded separately.

C88 deterministically orders only the context qualification's top-level check
rows by unique complete ID. The legacy reader accepts a row permutation only
with exactly the same unique IDs, complete typed rows, statuses and other fields.
Nested order remains exact under the existing unchanged C85 atom-keyed formal-
charge evidence rule; C88 adds no nested-list allowance. Duplicate or missing IDs
and changed values/statuses remain rejected; no verdict is promoted. Shared C85 comparison,
other qualification helpers, context policies v1/v2, source chemistry, native
kernels and all scientific gates remain unchanged.

Methods: build the existing `scripts/build_mixed_context_probe.py` with explicit
`--delivery-prefix 88_Cedar` and run `--saved-native-only` on the exact C87
capsule. Builder default 86 remains compatible. The maintained reader reconstructs
temporary external context/linked-parent views and verifies the saved native
inputs, captures, preparation and qualification without SDK discovery or a native
process. Preserve every parent payload once through indexed transport; do not
copy another scientific subtree. Emit only `saved_mixed_context.json`, schema 1,
policy `cif-saved-mixed-context-v1`, with hash-bound logical report/qualification
references under `parent_review`. The receipt references this compact summary
under `probe_directory`; original scientific files remain byte-exact.

The saved summary retains `MIXED_CONTEXT_MECHANICS_PASS`, two historical and zero
new native calls, and the original `CONTINUE_WITH_NOTES` coordinate decision with
`native_usable: true`. Students do not approve CIF tables. Scientific qualification,
source-state findings, formal-charge API limits, ordinary full-run integration
and production adoption remain separate. No Coot, ReadySet, generation,
optimization, store write, refinement or new native qualification is requested.
The actual Mac C88 saved replay is verified below; it requests no new native
qualification.

Final local validation passes 512 focused tests in 25.61 seconds and 4,809 full
tests (two skips, 276 subtests) in 599.28 seconds on
`aaed1955b166c507ba94be8157bf1bc89c69fd6e`. All sixty-one final new cases are
frozen before full collection, with no later source/script/test changes or
supplement. Generic unique-ID order, complete typed rows, missing/duplicate IDs,
nested order, statuses, legacy replay, input binding and failure preservation
are covered. Initial fail-before subsets remain separate from final case counts.

Source-removed cold saved replay passes with 165 runtime members and an
869-payload capsule preserving all 865 C87 payloads plus its manifest exactly.
Its compact summary is 1,088 bytes, with no duplicated scientific subtree.
All 297 scientific/context/parent files remain exact; 315 checks reproduce the
original 291 PASS / 24 unsupported-formal-charge result and mechanics PASS.
SDK discovery, context audit and process calls are forbidden. Configuration,
everyday edits and store fixtures survive; 119,864 simulated macOS path operations
stay within 217 absolute/68 component bytes. The standalone reader reconstructs
its explicit parent from the copied new capsule after original ZIP/session/
runtime removal and explicit owned-view retirement; guarded automatic temporary
cleanup is not claimed. Shared C85 readers remain byte-exact. This validates
saved evidence and packaging, with zero new native qualification.

Returned C88 verifies all 869 payloads plus the outer manifest, including all
866 original C87 members byte-exact. The archive has 870 entries and 121,527,577
uncompressed bytes. Its 1,088-byte summary reproduces exactly, retaining all 315
checks (291 PASS / 24 unsupported formal-charge readbacks), all 297 scientific
context/parent files and the original mechanics PASS. The saved native-call count
is two; new native calls are zero. The maintained explicit-parent reader preserves
`CONTINUE_WITH_NOTES`, native usability and the original failed C87 envelope.
No scientific verdict or student CIF approval is added.

### Fresh initial-only gradients of the exact mixed manager (C89)

The exact mixed manager has 863 atoms, forty-two sites and fifty-eight parallelity
restraints. Earlier geometry/plane qualifications belong to a different
877-atom/forty-three-site manager and cannot be relabeled as proof for this model.
C89 therefore supplies one fresh initial-only audit before a geometry trial;
it does not invent historical endpoints or optimize coordinates.

Methods: verify the exact C88 capsule and its explicit context/linked-parent
anchors, then rebuild and match the saved active C87 manager. Captured programs remain
data and are never imported or executed. Bind the fresh job's native API/source
pins and unchanged correction core before applying the existing
`native-parallelity-both-first-planes-v1` correction with unchanged native energy
and fixed chemical definitions and NARestraints pairing/stacking policy. Use the
existing fixed evaluator, finite-difference category/global gradient audit and
per-plane order audit on all fifty-eight actual restraints, with six fresh
tilted/rotated controls. The single coordinate case is the saved initial state.
Selection of sampled atoms follows numerical/outlier evidence rather than a
component-name exception. Bind the trusted worker, correction core, inputs and
saved numerical evidence in `mixed_initial_gradients.json`, policy
`cif-mixed-initial-native-gradient-v1`; its reader recomputes qualification from
the saved records. Keep external parent references explicit and preserve the
complete parent once through indexed transport, without another scientific-tree
copy or a larger archive bound.

The new `scripts/build_mixed_gradient_probe.py` creates
`89_Cedar_probe_mixed_initial_gradients.py`; `--inspect-only` prepares inputs
without SDK execution, while the fresh audit uses one native worker bounded at
600 seconds. With six sampled atoms, the expected algorithm uses 1,367 whole-
energy evaluations within a 2,000 maximum and 3,328 plane/control evaluation
pairs within a 5,000 maximum; the actual Mac counts and qualification are verified below.
No Coot, ReadySet, dictionary generation, optimizer, store publication, production
adoption, refinement or diffraction run is added. A failed derivative check
retains usable input and notes for the next bounded step; students do not approve
CIF tables. Local focused validation passes 600 tests across twenty-two files
in 83.01 seconds on `cad81fb394433767d270577cfbc923792672c01f`; all 106 final
new cases (61 module / 45 ferry) are frozen before full collection. Initial
fail-before subsets contain four module and four ferry cases, separate from the
final case count. Actual-parent inspect prepares 455,931 bytes and 3,328 plane
pairs with zero SDK calls and all 297 parent scientific files exact. The complete
suite passes 4,915 tests, two skips and 276 subtests in 694.66 seconds at that
checkpoint. No source, script, test or figure changes follow full collection and
there is no later test supplement. Actual Mac C89 derivative qualification passes
as recorded below; source-state findings and scientific qualification remain separate.

Source-removed cold inspect passes at the same checkpoint with 166 runtime members.
The 918-payload capsule preserves every C88 payload and its manifest byte-exact
once, totaling 122,235,229 uncompressed bytes; the largest member is 20,829,148
bytes. Its 484,997 bytes of new data leave 11,982,499 bytes below the unchanged
128 MiB limit. The standalone explicitly anchored reader passes after the owned
source clones, original input copy, session and runtime are removed; all 165
context, 132 linked-parent and 46 new files remain exact. Inspect stays
`PREPARED_ONLY` with zero SDK/discovery/subprocess/captured-code calls. Configuration,
everyday edits and store fixtures remain intact; 164,380 guarded path operations
stay within 232 absolute/68 component bytes. Temporary views are explicitly
retired; guarded automatic cleanup is not claimed. This is preparation/portability
evidence, not a fresh installed derivative result.

Returned C89 passes the fresh installed audit in one Phenix 2.2.1-6174 job
(24.122224 seconds, exit zero). The exact 863-atom/forty-two-site manager matches
the saved inputs. All eight sampled gradient families, repeats, target/gradient
additivity and the captured snapshot pass in 1,367 of 2,000 energy evaluations.
All fifty-eight actual planes pass in both orders, together with six tilted/
rotated controls and three rotation checks, in 3,328 of 5,000 evaluation pairs.
The original native complete-gradient controls retain twelve actual and six toy
review orders; the order-safe correction has none. This verifies the correction
rather than changing targets: native energy remains 27,518.185419949943, with
coordinates, source definitions, source pins and static constraints unchanged.
All 937 payloads and the exact C88 parent verify. The maintained reader replays
qualification with zero new SDK processes; captured programs remain data. These
are sampled numerical results, not convergence, source-state repair or scientific
qualification. Original C89 local validation remains unchanged.

### Bounded geometry from the qualified mixed manager (C90)

C90 supplies one optional geometry-only trial from the exact C89 initial state.
The existing geometry worker, native corrected evaluator, optimizer settings and
atom-identity serializer remain unchanged. A separate precondition adapter verifies
the genuine C89 initial-only proof, source fingerprints, static constraints and
corrected initial target/gradient before optimization; it does not relabel an old
three-coordinate-case qualification. Chemical definitions, weights and the
NARestraints pairing/stacking policy remain fixed, with native secondary-structure
guessing disabled.

Methods: bind C89 through explicit gradient/context/linked-parent anchors; stage
trusted current Git sources and a fresh optimizer history; run one trial bounded
at 1,000 iterations and 600 seconds, with at most 20,000 optimizer calls and the
existing 1e-5 convergence tolerance. Check full-precision and PDB-rounded endpoint
derivatives, serialize by exact atom identity, then interpret the separate PDB
with the same dictionary/PHIL bundle and exact fixed-policy proxy checks. Select
a usable endpoint only when its fixed objective does not worsen and its mechanics
and derivative evidence qualify.
Retain the verified usable initial model automatically when the optional phase
cannot qualify an endpoint. Usable nonconvergence, iteration limits and descriptive
pucker/chirality findings become notes, with no student CIF inspection or approval.
Fixed definitions and mechanically unusable evidence remain strict.

The report is `mixed_geometry_trial.json`, schema 1, policy
`cif-mixed-qualified-geometry-trial-v1`. The builder
`scripts/build_mixed_geometry_probe.py` creates `90_Cedar_probe_mixed_geometry.py`.
`--inspect-only` prepares the trial without SDK execution; a complete diagnostic
allows at most two SDK jobs including native candidate readback, bounded at the
smaller of the requested timeout and sixty seconds. Preserve the
original C89 ZIP byte-exact once as opaque `inputs/parent_review.zip`, rather than
flattening its 128,249,071-byte ancestry again. The exact 10,963,258-byte parent
archive and all its payloads remain available. Only three declared scientific
views are materialized temporarily; captured programs are never executed. The
128 MiB total, 32 MiB member and 1,024-entry outer limits stay unchanged.

Focused local validation passes 917 tests across thirty files in 149.00 seconds
on `f759d4c9561d0af1a82d5f9336eb1fa8496f2fb4`. All 116 final new cases (64
module / 52 ferry) are frozen before complete-suite collection. The original
four-case fail-before subsets remain distinct from final counts. The real C89
prepared trial and maintained reader pass with zero SDK processes, 53 prepared
files and 7,256,286 bytes. The genuine 863-atom precondition adapter passes and
rejects a tampered proof without SDK execution. The complete suite passes 5,031
tests, two skips and 276 subtests in 718.58 seconds at the same frozen checkpoint.
No source, script, test or figure changes follow full collection, and there is no
later test supplement.

Source-removed inspect and standalone readback also pass after removing the
original session, runtime and input archive, with zero SDK/subprocess launches.
The portable runtime has 167 members; the new outer archive has 57 payloads plus
its manifest and 18,257,745 uncompressed bytes. Its largest member is the exact
10,963,258-byte original C89 ZIP, preserved once with all 937 payloads and its
original manifest. New data occupies 7,285,687 bytes, leaving 115,959,983 bytes
under the unchanged 128 MiB limit without duplicating the old scientific tree.
The standalone reader reproduces all 65 gradient, 165 context, 132 parent and 54
new files unchanged. The path guard checks 125,071 operations, with maximum path
and component lengths of 232 and 45 bytes. Authorized edits, user configuration,
the component store and ambient import isolation remain intact. Owned temporary
views are explicitly retired; guarded automatic cleanup is not claimed.

Those original local checks precede the installed C90 return below. No Coot,
ReadySet, dictionary generation, cache publication, production adoption,
refinement or ordinary diffraction solve is added. Source-state findings and
scientific qualification remain separate from optional coordinate usability.

Returned C90 completes one Phenix 2.2.1-6174 geometry worker in 53.99432 seconds.
The fixed target falls from 27,518.185419949943 to 4,294.46458796323 (84.394%)
over 257 iterations and 311 calls, then stops on a line-search rounding error.
This objective decrease does not qualify the endpoint: the full-precision global
and dihedral audits each retain three REVIEW directions out of twenty-one;
the other six families pass, while all eight PDB-rounded families pass. Repeats,
snapshot matching and target/gradient additivity remain consistent. The saved
full-precision gradient norm is 88,852.6173130985, versus 14,419.934751481616 after
PDB rounding. Native candidate readback does not run. The report retains its
`Mixed geometry evidence does not reproduce` finding and automatically keeps the
verified usable initial model with `CONTINUE_WITH_NOTES`; no student CIF approval
or production adoption occurs.

The strongest endpoint forces involve the PDU propynyl atoms C5A/C5B/C5M at D:5.
Its triple-bond distance is about 1.196736 Å against a 1.203 Å target, with an
adjacent angle about 179.999810°. These observations motivate a fixed-coordinate
torsion-conditioning test; they do not establish a native gradient defect.
All 76 returned payloads, the trusted 167-member runtime and exact opaque C89
archive verify; all 937 C89 payloads and its original manifest remain byte-exact.
Independent maintained read-only replay reproduces the original `REVIEW`, one
historical native call and the same initial-model selection in 38.73 seconds.
All 435 scientific-view files remain unchanged, with SDK discovery, new native
calls, pickle loading and captured-program execution forbidden. The actual return
is appended separately to `mixed_qualified_geometry_trial_2026_10_24` without
changing its original local validation. Source chemistry, static
constraints, scientific qualification and ordinary full-run scope remain separate.

### Fixed-endpoint torsion conditioning (C91)

C91 investigates the saved C90 endpoint without moving its atoms or changing
restraints. It rebuilds the exact fixed manager from four explicit geometry,
gradient, context and linked-parent anchors, with the original C90 archive SHA-256
bound into the report. Source fingerprints, atom identities, fixed definitions,
NARestraints pairing/stacking targets and the existing plane-gradient correction
remain authoritative. The verified initial-model fallback is unchanged.

Methods: rank ordinary native dihedral proxies by near-collinearity and atom-
gradient evidence across the initial, saved full-precision and PDB-rounded cases,
independently of residue code. Record declared bond-path support for each row.
Select at most six near-linear proxies and two atom-disjoint non-near-linear
high-gradient controls, capped at eight; record ranking and truncation. The
near-linear screen uses the sine of five degrees. Constant zero-weight torsions
remain inventoried separately. In all three coordinate cases, compare each
selected native single-proxy evaluation with its container, in both endpoint
orders. Sample up to fourteen Cartesian, local-gradient and alternating directions
over seven finite-difference steps from
1e-3 to 1e-9 Å, retaining separate original-coarse (1e-3 through 1e-6) and finer
(1e-7 through 1e-9) agreement counters. Adjacent-step agreement is diagnostic and
never requalifies the endpoint. Use the unchanged earlier native torsion
evaluator; compare the selected group, remainder and complete dihedral family
with fixed-coordinate energy/gradient additivity checks. At most 10,000 paired
single/container evaluations and 600 group evaluations are allowed, in one
native worker with a 120-second default and a 600-second hard maximum. These are
separate diagnostic caps; the unchanged native energy worker additionally records
two initial raw full-manager snapshots for source/manager binding, visible in
`native_validation.energy_inventory`.

The schema-1 report is `mixed_torsion_audit.json`, policy
`cif-mixed-fixed-torsion-audit-v1`, anchored at `mixed_torsion_directory`.
`audit_mixed_torsions` and `read_mixed_torsions` require the four explicit parent
views and original C90 archive checksum. `PREPARED_ONLY` means no SDK execution.
`MIXED_TORSION_AUDIT_COMPLETE` means bounded numerical evidence and arithmetic
replay completed; it does not approve derivatives, converge a model or prove a
native defect. Numerical disagreement and near-collinearity remain explicit
findings. Missing or unreproducible evidence retains `REVIEW`. This is an additive
diagnostic and report schema; existing artifact readers, native kernels and
production paths remain unchanged, with no migration of earlier runs.

The builder `scripts/build_mixed_torsion_probe.py` and its maintained template
`scripts/mixed_torsion_probe_template.py` produce `91_Cedar_probe_mixed_torsions.py`.
The ferry preserves the exact compressed C90 archive once as opaque parent data,
reconstructing only declared temporary views. Its C89 archive stays
nested and byte-exact; no old scientific tree is flattened. Existing 128 MiB
total, 32 MiB member and 1,024-entry outer bounds remain. Captured programs remain
data. No optimizer, generator, Coot, ReadySet, cache publication, chemical edit,
mechanical correction, refinement, adoption or student CIF approval is added.
SDK-free selection on the actual saved parent inventories 975 torsions: 607
positive-weight ordinary terms and 368 zero-weight constants. It selects all six
near-linear rows without truncation and two disjoint gradient controls; all eight
have native bond-path support. The worst minimum sine is 3.314055611181453e-6.
No native kernel is evaluated by this selection check. At the maximum eight rows
and three cases, the declared schedule requires at most 9,504 paired kernels and
528 group calls, within its unchanged 10,000/600 caps. All 131 final new cases
are frozen before complete-suite collection: 66 module cases pass in 67.57 seconds
and 65 ferry cases pass in 3.09 seconds. The initial nine module / four ferry
fail-before subsets remain distinct from those final counts. The frozen code
checkpoint is `c6a3743f4294a7cce4b87d9053a7952a95799b13`. Actual-parent SDK-free
preparation and standalone exact replay pass in 152.49 seconds, with all 435
protected scientific-view files unchanged and zero SDK processes. The report
stays `PREPARED_ONLY`; the original C90 REVIEW and usable initial-model decision
remain unchanged. Combined focused validation passes 1,133 tests across thirty-five
files in 229.90 seconds at that frozen checkpoint. All 131 final new cases enter
complete-suite collection before launch. The complete suite passes 5,162 tests,
two skips and 276 subtests in 862.21 seconds at the same checkpoint. Source,
script, test and figure bytes remain frozen after collection, with no later
supplement.

Source-removed inspect and standalone readback pass after removing the original
session, runtime and input archive, with zero SDK/subprocess launches. The frozen
runtime has 168 members. The new outer capsule has 50 payloads plus manifest and
18,366,235 uncompressed bytes; its largest member is the exact 12,504,004-byte C90
ZIP, preserved once with all 76 payloads and its manifest. The embedded original
C89 archive also remains byte-exact, with all 937 payloads and its manifest.
New data occupies 5,854,629 bytes, leaving 115,851,493 bytes under the unchanged
128 MiB cap without duplicating old scientific trees. All 73 geometry, 65
gradient, 165 context, 132 parent and 47 new files replay unchanged. The path
guard checks 186,255 operations at maximum path/component lengths of 231/45 bytes;
configuration, authorized edits, the component store and ambient import isolation
remain intact. Five owned temporary views are explicitly retired; guarded
automatic cleanup is not claimed. The report stays `PREPARED_ONLY`. Actual Mac
C91 fixed-endpoint execution was pending at that original validation checkpoint;
its actual return is recorded separately below. Scientific qualification and the
ordinary full run remain separate.

### Returned fixed-endpoint torsion evidence

Returned C91 completes one Phenix 2.2.1-6174 worker in 6.156328 seconds. All 68
payloads and their manifest verify; the exact compressed C90 archive and its
embedded C89 archive remain byte-identical. The 168-member runtime and reported
runner hash reproduce exactly. All 9,504 paired single/container and 528 group
evaluations complete within their separate limits. Full/selected/remainder
attribution, saved-family agreement and finer group derivatives pass at all
three saved coordinate cases. Initial and PDB-rounded local derivatives pass.

Six full-precision local direction/order pairs remain under review: three unique
directions in both orders of one PDU D:5 C5-C5A-C5B-C5M torsion. Every smallest
1e-9 Å sample agrees within the original tolerance, but 1e-8 Å does not, so the
required adjacent passing pair is absent. The roughly hundredfold error decrease
for a tenfold step reduction supports second-order finite-step conditioning near
collinearity; it does not establish a native analytical-gradient defect. This
returned component/site is an observation, not a selection exception.

Maintained SDK-free replay reproduces the report in 52.203912 seconds, preserving
all 500 staged scientific files with zero subprocess, native or pickle calls.
Original C90/C91 records and C91 local validation remain unchanged. C91 does not
requalify the endpoint: `verified_constructed_model` remains selected with
`CONTINUE_WITH_NOTES`, source-state findings and scientific qualification intact.

### Current source declarations in mixed assessment (C97)

After saved endpoint/context replay, `cif_mixed_source_review` derives a read-only
same-ID comparison of hash-bound original sources and current base dictionaries.
The existing dictionary assessor owns parsing and declaration normalization;
this adapter retains chemical-field differences, source/current graph statuses,
declared site contexts and historical generation findings as separate evidence.
Canonical graph inputs explicitly exclude installed-library numerics. Neither
field equality nor a historical rejection is promoted to current chemical
approval or current candidate rejection.

The public bundle resolver returns this derived inventory separately from its
unchanged schema-1 manifest. Ordinary assessment includes it under
`solution_report.source_state_review`, with an owned-capsule reference; temporary
view paths never become operational provenance. Complete staged-view and capsule
hash checks follow use. No new native execution, source repair, selection policy,
checkpoint adoption or migration is introduced. The
[C97 contract](cif-doctor.md#current-source-declaration-inventory-c97) defines scope
and the distinction between base declarations and site modifications.

### Qualified mixed runtime handoff (C95)

`cif-qualified-mixed-runtime-bundle-v1` extends the public ordinary bundle
reader to the qualified mixed endpoint. Its manifest binds one exact source
capsule, the selected PDB and every dictionary/PHIL in native input order.
Six bounded shallow views feed the maintained saved-evidence replay at each
resolution; captured programs remain data. The ordinary assessor consumes the
resolved paths and follows with a hash-only integrity check. Nonconvergence,
source-state findings and scientific limits remain in solution notes. C95
tests this handoff after relocation with no new native process or optimizer;
no observation, AutoMR checkpoint or production adoption is fabricated.
The [C95 contract](cif-doctor.md#qualified-mixed-runtime-handoff-c95) owns schemas
and bounds. The existing single-component runtime policy remains supported.

### Portable saved-endpoint report replay (C94)

C94 uses a separate `cif_mixed_endpoint_replay` adapter over the unchanged C93
recipe and evidence readers. It retains source hashes, native-response and
derivative replay, exact PDB serialization, proxy mechanics and the original
coordinate decision. The shared `cif_geometry_report_replay` policy permits
only bounded derived-scalar roundoff in Cartesian reports; all chemical fields,
types, warning classes, ranks and signs remain exact. Its allowance is unrelated
to native ESDs or derivative qualification. See the
[C94 contract](cif-doctor.md#portable-saved-endpoint-report-replay-c94).

The saved-only ferry accepts the exact completed C93 ZIP, preserves it once and
records zero new native calls. Trusted current C93 ferry support is checksummed
inside the build runtime; captured code remains data. It verifies opaque nested
ancestry and stages bounded temporary views. Ordinary pipeline behavior, cache
publication, checkpoints and scientific qualification do not change.

### Uniform saved-endpoint resolution window (C93)

Returned C93 qualifies all six local and six broader derivative rechecks,
retains 330 earlier passing directions, and passes all seventeen native PDB
mechanics checks. It selects the saved endpoint automatically without another
optimizer. Independent Linux replay reproduces derivatives, PDB bytes and
native mechanics, but the original reader rejects last-bit differences in
calculated angle summaries. C94 adds bounded descriptive-report replay while
keeping chemistry, derivative evidence, native proxies and warning classes
exact. No new native process or student CIF inspection is requested; ordinary
full-run integration and scientific qualification remain separate.

The separately versioned module `cif_mixed_endpoint_window.py` preserves the old
C92 worker bytes and reader. It adds 3e-8 A to a fixed 1-3-10 grid, requires exact
step/tolerance metadata, and caps 120 rows within the existing 2,000-call budget.
One audit and conditional native PDB readback are allowed; the actual parent
schedules 228 adaptive calls. The schema-1 report and anchor are
`mixed_endpoint_window_qualification.json` / `mixed_endpoint_window_directory`.
The core remains bound to C91 scientific inputs; the ferry independently replays
C92 first and preserves the exact C92 ZIP once. Six shallow temporary views do
not flatten opaque ancestor archives. Native mechanics, optimizer, serializer,
NARestraints policy and ordinary pipeline behavior stay fixed. See the
[resolution-window contract](cif-doctor.md#uniform-saved-endpoint-resolution-window-c93).

### Guarded qualification of a saved endpoint (C92)

C92 qualifies the already saved endpoint through a separate evidence policy;
it does not rerun optimization or relabel the original C90/C91 verdicts. Its
inputs are five explicit torsion, geometry, gradient, context and linked-parent
views, bound to the exact original C91 archive. The bound C91 report supplies
the C90 checksum required by the unchanged earlier reader. All source chemistry,
NARestraints pairing/stacking authority, native kernels and previous run artifacts
remain unchanged.

Methods: select unresolved local direction/order pairs from verified C91 evidence
and reconstruct the exact failed original C90 whole-objective/family directions,
without residue-name or proxy-index exceptions. Retain every original positive
sampled proof. At fixed coordinates evaluate a six-step resolution window,
1e-7, 1e-8, 3e-9, 1e-9, 3e-10 and 1e-10 Å, using the same absolute/relative 1e-4
tolerances. These are fresh observations, not six steps all smaller than C91's;
the wider window is needed when the tiniest displacements become quantized.
Require two adjacent passing new samples, actual representable central
displacement, central symmetry and derivative floating-point resolution.
Representation and target-ULP resolution screens each consume at most ten percent
of the unchanged comparison bound; they do not rigorously bound every internal
native-kernel error. Fresh repeated baselines for all eight
families at the initial, full-precision and PDB-rounded coordinates must match
the pinned sources, exact manager and saved objective. Failed, unresolved or
unsupported numerical evidence cannot qualify a new endpoint.

Only positive complete sampled derivative evidence permits serialization of the
saved endpoint and a conditional fresh native PDB readback. The unchanged atom-
identity serializer and native definition/proxy validators must pass, and the
same fixed objective must not worsen, before the separate endpoint can be
selected as `qualified_geometry_endpoint`. Any failed or missing optional gate
retains `verified_constructed_model` automatically, with notes. Native stopping,
sugar pucker, source-state limitations and scientific qualification stay distinct
from this selection; students do not inspect or approve CIF tables.

The additive schema-1 report is `mixed_endpoint_qualification.json`, policy
`cif-mixed-saved-endpoint-qualification-v1`, anchored at
`mixed_endpoint_directory`. The API is `qualify_saved_mixed_endpoint` with
`read_saved_mixed_endpoint` for independent saved arithmetic replay. A fresh
adaptive worker and at most one conditional native readback are allowed, with a
120-second default and 600-second maximum deadline. The shared adaptive budget
is 2,000 calls and 128 selected direction/order or family-direction rows; its
maximum schedule needs 1,840 calls including 48 fresh family snapshots. The
actual verified parent selects six local and six family rows, scheduling 204
calls including those 48 snapshots. Two initial raw full-manager bootstrap
snapshots are recorded separately and are not part of the adaptive-call counter.
`PREPARED_ONLY` means no SDK execution. `ADAPTIVE_ENDPOINT_DERIVATIVES_PASS` describes the new sampled proof;
`MIXED_ENDPOINT_QUALIFIED` additionally requires serialized native readback and
selection gates. Neither status proves convergence or scientific correctness.

`scripts/build_mixed_endpoint_probe.py` and
`scripts/mixed_endpoint_probe_template.py` build `92_Cedar_probe_mixed_endpoint.py`.
The ferry preserves the exact original C91 ZIP once; C90 and C89 stay nested and
byte-exact, with only five declared temporary views materialized. Existing
128 MiB total, 32 MiB member and 1,024-entry bounds remain. Captured programs stay
data. No optimizer, generator, Coot, ReadySet, chemical/mechanical edit, cache
publication, refinement or production adoption is added.

All 149 final new cases are frozen before complete-suite collection at
`514db13083e50ac75d53cbf325b7e242dabb7443`: 61 module cases pass in 116.41 seconds
and 88 ferry cases pass in 5.13 seconds. The module suite executes the actual new
adaptive worker and conditional native PDB readback through a pinned fake SDK;
no installed Phenix execution is claimed. Initial fail-before subsets record
four core API, seven core integration and four ferry failures, separately from
the final case totals. Broader focused validation passes 1,282 tests across
thirty-seven files in 446.93 seconds on the same frozen checkpoint. The complete
suite passes 5,311 tests, two skips and 276 subtests in 1,027.37 seconds. All eight
source, script, test and figure hashes remain frozen after collection, with no
later supplement. Final source-removed inspect and independent replay also pass;
the actual Mac C92 result is recorded separately under C93.

Source-removed inspect and standalone replay pass at the same frozen checkpoint.
Both original source clones are gone before launch; the original session, runtime
and input archive are removed before independent readback from the new capsule.
The 169-member runtime is fixed by SHA-256. The outer archive contains 54 payloads
plus manifest and 23,571,221 uncompressed bytes. Its largest member is the exact
15,023,841-byte C91 archive, preserving all 68 parent payloads and its manifest;
C90 and C89 remain nested and byte-exact, with 76 and 937 payloads respectively.
New data occupies 8,539,119 bytes, leaving 110,646,507 bytes beneath the unchanged
128 MiB bound. No ancestor scientific tree is duplicated.

All 65 torsion, 73 geometry, 65 gradient, 165 context, 132 linked-parent and 51 new
files replay unchanged, with zero SDK, native-discovery or subprocess calls.
The Mac path guard checks 370,241 operations at maximum path/component lengths
of 237/45 bytes. Configuration, the authorized everyday edit, the component
store and ambient import isolation remain intact. Thirty-two owned temporary
views are explicitly retired; guarded automatic cleanup is not claimed.
QA-only in-place forbidden-entrypoint guards and import-only profiling preserve
existing function aliases. Independent review blocks all 105 canary calls and
preserves 129 source files; process, captured-code, original-path, archive and
preservation guards remain unchanged. No application source or native kernel is
changed by this QA instrumentation. The inspect report remains `PREPARED_ONLY`;
the actual Mac C92 native return is recorded separately under C93; scientific approval remains open.















Methods: compare all seven inventoried named chemical fields and the repair
recipe/backend; reassess completed source-relative configuration; require
current isolated native qualification; publish a new entry bound to the selected
raw source/authority while crediting the original numerical producer. Keep the
old entry immutable and freeze both provenance records with relative hashes.
A failed or mutating adapter receives disposable inputs and excludes only that
candidate. A changed consumer requalifies saved bytes first. Optional cache-write
failure retains a qualified run copy. An unparameterized fallback source still
requires ordinary preparation; it is not a native-usability verdict.

Local integration uses actual returned source bytes and saved native data:
all 63 checks pass and six qualified/reused results survive source/cache removal
and relocation, with external scientific reads forbidden. This does not claim
fresh Phenix execution. C68 stops before launch; C69 corrects that layout and
completes all three native reads. C70 replays their exact inputs, worker/specs,
outputs and consumer bindings, recomputes the unchanged usability checks and
finishes the source-bound store/repeat stage. Owned source-layout replay uses
the captured C69 bytes/authority, not a new live installation selection. Separate
dictionary/native triple reports preserve torsion and seed-bending findings.
No captured Python or new native process is executed.
Native guessing stays disabled. Native energy resource files are not inventoried;
current linked/model qualification and production PostMR adoption remain open.


### Preserved candidate recovery in a current mixed context (C98)

The [C98 diagnostic contract](cif-doctor.md#preserved-candidate-source-recovery-c98)
adds a source-bound reuse path alongside generation. The existing endpoint
reader optionally exposes its verified temporary context/native view to a
caller that freezes the declared resources into a new owned directory. Ordinary
callers retain the same default reader result and runtime manifest behavior.

`cif_mixed_source_recovery` reuses the maintained complete-candidate, isolated
native, linked preparation and full-model membership qualifiers. A candidate
archive source must equal the current source; code identity alone is insufficient.
The bounded replacement policy rejects existing selected-site modifiers and
shared component containers. All four controls bind one native interpreter;
unchanged current proxies are compared by structured atom identity. Readback
reproduces input selection, preparation and qualifications from owned capsules,
with anchored paths/checksums and no process launch. Native mechanics success
cannot transfer derivative or endpoint qualification across the changed objective.


### Derivative qualification after source recovery (C99)

`cif_recovered_gradient` adapts the verified recovery schema to the unchanged
C89 preparation, numerical worker and numerical replay functions. The parent
reader must reproduce C98 source chemistry, linkage and full-model mechanics
before its exact resources and active manager can be used. Parent and job
references have explicit independent directory anchors; host paths are only
historical provenance. The outer receipt validates the recovery-specific scope,
complete output inventory, exact maintained preparation, source fingerprints,
process outcome and numerical qualification. Historical worker/core bytes are
not refactored, so prior evidence remains replayable.

The [C99 contract](cif-doctor.md#recovered-manager-derivatives-c99) defines the
additive schema and diagnostic API. One bounded native process samples the
initial coordinates only. A changed parent, manager, executable or saved sample
cannot inherit qualification. A failed attempt remains immutable; no optimizer,
Coot, ReadySet, dictionary generator, runtime selection or checkpoint is invoked.
Readback reconstructs the preparation in temporary storage and never executes
captured code. The qualified object is this fixed manager and local evaluator,
not ordinary refinement or a scientifically approved structure.


### Geometry after source recovery (C100)

`cif_recovered_geometry` connects replayed C98/C99 bindings to the unchanged
`cif_mixed_geometry` preparation, endpoint and native-mechanics validators.
It supplies the real initial proof and expected manager; historical packages
and optimizer kernels remain byte-identical. A verified C98-owned endpoint
capsule supplies the legacy worker's archive field, while independent C98/C99
references bind the actual repaired objective. The [C100 contract](cif-doctor.md#recovered-objective-geometry-c100)
defines the additive schema and explicit diagnostic APIs.

An endpoint is eligible only after derivative, identity serialization, native
mechanics, rounded-target and nonworse-objective checks. Failure retains the
verified recovered starting model, not an old-objective endpoint. Process
success does not imply numerical qualification, and stopping does not itself
exclude a usable endpoint. Every attempt requires fresh storage, preserves
failed outputs and remains separate from runtime/checkpoint adoption. Native
reread is never launched for an unqualified derivative endpoint. This adapter
does not alter the independent metal-authoring backend or NAR role/target logic.


### Fixed-coordinate diagnosis after source recovery (C101)

`cif_recovered_torsion` binds the unchanged mixed-torsion selector, worker and
replay validator to the current C100/C99/C98 lineage. The completed geometry
worker supplies exact initial/full/rounded coordinates and saved torsion-family
references even when its endpoint remains unqualified. Parent readers establish
the repaired objective once; anchored references retain ordered dictionaries,
parameters, installed-source pins and the exact native manager. The current
consumer must match C100 before a fresh output directory is created.

The one-job diagnostic separates individual single/container kernels in both
orders from full/selected/remainder attribution. It never optimizes or changes
a definition. A completed diagnostic can contain derivative reviews; its outer
status cannot promote C100's coordinate decision. The additive receipt and
read-only reconstruction contract are documented in the
[C101 contract](cif-doctor.md#recovered-endpoint-torsions-c101).

The complete native trial localizes 22 remaining local full-precision reviews
to PDU D:5 C5–C5A–C5B–C5M while seven other sampled torsions and the remainder pass.
Initial/rounded sampled checks agree at finer steps, and native/saved-family
attribution passes for all representations. The same full-precision PDU torsion
also retains strict atom-order reversal review; within-order repeats and
single/container comparisons agree. This supports a resolution-aware
investigation without claiming a derivative defect, chemical correction or
endpoint qualification. No NAR workbook/shared compiler, GUI, runtime manifest,
CLI, source-state or terminal-phosphate policy changes are involved.


### Resolution diagnostics after source recovery (C102)

`cif_recovered_resolution` uses C101's maintained reader to establish current
C100/C99/C98 lineage once, then connects the same inputs to the unchanged C93
plan, worker and numerical replay. The strict original optimizer/precondition
metadata, installed sources and native manager bind every new evaluation.
A new outer diagnostic receipt preserves selection independently of numerical
qualification; no serialization, conditional native reread or adoption exists
in this adapter. Fresh atom-order comparisons are reconstructed from recorded
local baselines, with absent-order coverage stated explicitly. See the
[C102 contract](cif-doctor.md#recovered-endpoint-resolution-c102).

The live audit passes 2/22 local and 4/10 broader rechecks, reproduces all 24
family snapshots and the strict PDU reversal discrepancy, and retains the three
failed original prerequisites. Displacement-resolution guards reject some
otherwise close full-precision derivatives. The captured native definition
contains an explicit triple bond, two 180-degree flank targets and the active
central torsion. This motivates independent arithmetic and source-declaration
comparison with prior linear-axis evidence; it does not authorize chemical or
numerical policy changes. Historical workers, NAR targets, phosphate behavior,
ordinary refinement and the parallel metal GUI remain unchanged.


### Independent torsion arithmetic after source recovery (C103)

`cif_torsion_precision` expresses ordinary positive-period torsion energy through
normalized plane normals and integer complex powers. Forward automatic
differentiation, two private Decimal precisions and independent Cartesian
differences separate a mathematical reference from the native floating-point
kernel. Exact binary inputs, mathematical pi, unsupported alternate functions,
one-ULP sensitivity and native comparison limits remain explicit.

`cif_recovered_precision` replays C102's maintained reader before consuming the
bound C101 selection, coordinate cases and native observations. It reinspects
individual dictionary/native rows through the existing triple/180° declaration
prerequisites. The [C103 contract](cif-doctor.md#independent-recovered-torsion-precision-c103)
defines the additive report/parent anchors and type-sensitive complete replay.
No scientific inputs are searched by basename, captured code executed, native
process launched or model/dictionary selected or changed.

All 21 supported cases pass the independent controls; the full-precision PDU
torsion retains strict native/reference differences and much greater one-ULP
sensitivity. Six selected PDU/5PC rows match declaration prerequisites without
creating a complete candidate plan. C100 qualification and source chemistry
remain unchanged; native omission/delta checks in the current linked manager
are required before optimization of a separate candidate.


## Linked declaration-based omission inventory (C104)

`cif_linked_linear_torsion.py` adds a pure inventory comparison around the
existing C44 preparation policy and C103 declaration inspector. It rebuilds the
complete candidate and requires identical bytes, then checks each native
provider/site definition before deriving active omissions from full literal
residue identities. It compares every remaining native inventory field with
JSON type sensitivity. Only `energy_inventory` is excluded, explicitly leaving
energy, derivative and scientific qualification unperformed. The caller owns
native capture/input authentication through the maintained reader; this is not
a new runtime bundle or automatic selection path.

The local Phenix 2.2.1-6174 test captures the original and candidate current C98
manager. Exactly six PDU definition rows and three active torsion proxies are
removed; all 21 other/exact inventory checks pass. The original native inventory
reproduces C98. 5PC, linkage/phosphate definitions, NAR targets and coordinates
remain unchanged. C103 lineage and selected-start decisions are preserved.
The new schema-1 diagnostic result uses
`cif-linked-linear-torsion-inventory-v1`; no existing schema needs migration.
See the [C104 contract](cif-doctor.md#linked-pdu-omission-inventory-c104).


## Catalogue coverage before generalization (C105)

The read-only catalogue command consumes two explicit anchors: a selected
NARestraints workbook and a CCD source directory. It uses NAR's loader, verifies
its sheet/row correspondence, and applies the shared operational-role resolver.
It never substitutes the bundled workbook for an explicit one. Each exact code
maps to the declared CCD layout; no basename search, native discovery, generation
or network acquisition occurs. Available resources are assessed through the
ordinary source checker; hashes are checked across the complete census.

The additive schema-1 report preserves raw context/roles, duplicate conflicts,
missing sources, unassessed checks and exact sugar-label groups. Graph validity,
mapped-name presence and native qualification are distinct. NAR's `/` marker is
retained as evidence, not treated as an atom. Phosphorus neighbors and boundary
bonds are descriptive; they do not establish attachment sites, leaving groups or
terminal state. No profile, chemistry repair, numerical qualification or fallback
is selected by the census. Repeating with relocated explicit anchors must return
the identical report. Existing runtime schemas and receipts remain unchanged.

All catalogue families belong in the generalizer programme. Family/site contracts
and bounded recovery must preserve source identity, charge/stereo intent and
NAR ownership. A component alias can isolate definitions, never justify changing
chemistry for convergence. See the [C105 contract](cif-doctor.md#catalogue-coverage-census-c105)
and maintained [milestones](development-handoff.md#generalizer-milestones-and-interruption-boundary).


## Source attachment topology and state evidence (C106)

`cif_attachment_profiles.inspect_attachment_profile` is a read-only layer between
explicit source/NAR records and future site-operation planning. It reuses the
ordinary source assessment and operational-record resolver. Immutable graph
patterns bind source atoms by element, normalized order, induced connectivity
and heavy degree, using NAR mappings only for base membership. A completed unique
embedding across all patterns is required; bounded or ambiguous searches do not
choose a result. Codes, labels and naming conventions do not choose a pattern.

The initial single-phosphate furanose, O/C-bridged furanose and primary-amine PNA
core patterns expose source charge/H/D/stereo and neighbors at their ports.
They do not infer protonation, assign equivalent terminal phosphate oxygens to
leaving roles, compile NAR recipes or alter existing DNA preparation. Source and
workbook anchors and hashes allow exact cold replay; schema 1 is additive.
The [command contract](cif-doctor.md#source-attachment-topology-and-ports-c106)
records search limits, actual coverage and the remaining site-context/permitted-
delta boundary. No ordinary runtime hook or native execution is added.


## Explicit site source-projection contracts (C107)

`cif_attachment_sites.inspect_attachment_site` reuses the C106 profile and adds
an explicit source/workbook/model/context binding for one PDB site. Complete
port declarations and a strict PDB identity subset prevent implicit adjacency,
conformer/model collapse and accidental coverage of other sites. Source-state
retention or bounded neutral furanose deletions produce a proposed source-table
projection; missing chemical-state authority prevents any partial plan.

Optional candidate comparison preserves every retained column/row, ignoring
row order only, and rejects unselected components/blocks. External bonds remain
caller-declared intent. Neither a plan nor an exact match qualifies partner
chemistry, native numerical types or final linkage. PNA state and free-OH
reconstruction remain unresolved. The source/model and existing DNA preparation
are unchanged. Additive schema 1 uses explicit per-input directory anchors and
hashes and replays after cold relocation. See the
[C107 contract](cif-doctor.md#explicit-single-site-source-projections-c107).


## Reciprocal source-link composition (C108)

`cif_attachment_links.inspect_attachment_links` consumes an explicitly anchored,
hash-bound manifest and reruns C107 for each selected site. Every source code
has one exact authority; every declared partner belongs to the selected set.
The partner atom must be the complementary source-bound port and must declare
the same bond back. Edges are deduplicated and oriented by chemical role rather
than names, sequence order or proximity. No cached site-report file is trusted.

Source binding, site-operation resolution and candidate coverage are distinct.
Any unresolved operation or mismatching candidate withholds the complete joint
proposal; unselected model sites remain outside its claim. Strict path, size,
identity and before/after byte checks preserve exact cold replay. The additive
schema does not change native preparation, runtime manifests or checkpoints.
Existing DNA OC2 authority cannot silently transfer to ATL/PNA. The next layer
must bind these endpoint identities to authenticated native effective definitions
and inter-site proxies. See the [C108 contract](cif-doctor.md#reciprocal-source-link-contracts-c108).


## Source/native attachment-link audit (C109)

`cif_attachment_native.inspect_native_attachment_links` reruns the C108 plan and
reads a hash-bound capture from the maintained base native worker. Exact model
bytes, input/output records, spec, worker and report agreement bind the evidence.
Native indices map through literal atom identities; 1e-9 A coordinate roundoff
is allowed, while changed elements, occupancy or larger movements fail. All
inter-site bonds touching selected sites participate in the exact comparison;
extra, duplicate and symmetry connections cannot disappear behind counts.

Native failure, link membership and source-definition comparison are separate
results. The latter compares exact atom names/elements, bond adjacency and
available formal charges, not all numerical/stereochemical fields. Aliases are
not guessed, partial charge never replaces formal charge, and observed types
carry no new chemical authority. Overall REVIEW persists. This additive reader
changes no capture/runtime/checkpoint schema or preparation path and never
executes saved code. The three fresh DNA/ATL interpretations and cold replay
are documented in the [C109 contract](cif-doctor.md#native-attachment-link-audit-c109).


## Observed native atom-name mappings (C112)

`cif_native_atom_mapping` adds an opt-in extension to the maintained native
worker without changing its historical bytes. It captures actual monomer
bindings, then validates complete model-site/index/name and effective-element
agreement. Final expected/unexpected bindings govern the comparison;
intermediate library names remain observations. Ambiguous or colliding aliases
cannot reconcile a source difference. Missing native APIs remain unsupported.

The C109 reader keeps its literal result and adds a separate mapped result for
explicit mapping captures. Only observed model-bound names are translated;
unmodelled hydrogen names, protonation and charge authority cannot be inferred.
Native failure and unavailable formal charges remain distinct. This changes
no coordinates, chemistry, preparation, checkpoints or adoption. Old default
captures remain readable; older readers reject the new extension. DNA, both
failed ATL directions, L-DNA and a legacy capture pass exact cold replay. See
the [C112 contract](cif-doctor.md#observed-native-atom-name-mappings-c112).


## Bound source/native hydrogen inventories (C113)

`cif_native_hydrogens.compare_hydrogen_inventory` groups retained source and
effective native H/D/T atoms by observed heavy-atom bindings. Both heavy-atom
sets and single-parent hydrogen adjacency must be complete and unambiguous
before a comparison is recorded. The report separates isotope/count differences,
label differences and named hydrogen attachment changes, including equal-count
swaps between parents. It never generates unobserved H aliases or chemical-state
permission. Charge/stereo/numerical qualification and C109/C112 outcomes stay
independent. The C109 reader exposes this additive report only for C112 mapped
comparisons; old default captures retain their results. No worker or preparation
change is involved. See the [C113 contract](cif-doctor.md#bound-hydrogen-inventories-c113).


## Explicit neutral PNA chemical-state operations (C114)

The optional `neutral-pna-amide-v1` operation extends C107/C108 with local
neutral-amine/carboxylic-acid source deletion rules. The source graph and unique
PNA core bind the ports; the context must select exact leaving identities and
reciprocal endpoints. `cif_pna_operations.py` checks reactive formal charge,
explicit H/D count/attachment and complete local neighborhoods. Site inspection
retains the existing model/table/stereo gates; network composition withholds all
permitted projections when any operation is unresolved or candidate mismatches.
Unreacted charged termini retain their original source state. No general charge
conversion, numerical generator or production linkage path is added.

Schema-1 contexts with the new fields use v2 site/link policy identifiers;
proposed sites include a policy-bound operation ledger. Omission preserves v1
behavior and exact legacy reports. Parent source descriptors/coordinates remain
provenance, not a generated linked chemical identity. See the
[C114 contract](cif-doctor.md#explicit-neutral-pna-amide-operations-c114).

## Candidate generation diagnostic projection (C115)

`cif_source_candidate.candidate_generation_diagnostic` explains the existing
receipt without reclassifying it. Failed preconditions identify source handoff
issues before construction; inspection differences distinguish unsupported
bond orders from actual atom/hydrogen changes. Native exceptions remain separate
from retained candidate state, so completed output can still reach the existing
usability gates. `generate_source_candidate` emits the optional schema-1 field;
`read_mixed_recovery` recomputes it when present and accepts legacy omission.
This projection is not a standalone receipt validator. Native workers and all
chemical acceptance policies remain unchanged. See the
[C115 contract and controls](cif-doctor.md#candidate-generation-diagnostics-and-pna-controls-c115).

## Explicit connected atom-order preparation (C116)

`cif_connected_atom_order.prepare_connected_atom_order` is a separate opt-in
source adapter after dialect preparation. It canonically traverses the declared
connected heavy graph and permutes complete atom rows, leaving all atom values,
other tables and legacy metadata bytes intact. Terminal H/D/T are retained;
ambiguous/disconnected inputs and existing outputs are refused. Its schema-1
report binds source/output hashes and permutations. It changes neither the
native worker nor default recovery/acceptance. A successful construction is
still subject to the existing source-identity and native qualification gates.
The [C116 contract](cif-doctor.md#explicit-connected-atom-ordering-c116) records
the observed coordinate-reference promotion, bounded workaround and remaining
purine/linked-PNA limits. No run/checkpoint migration is required.

## Explicit neutral purine representation assessment (C117)

`cif_purine_representation` extends the legacy representation comparison only
when the caller supplies its named policy. A graph/valence whitelist permits
complete source-declared neutral fused purines with unchanged single-bridge
substituents and exact whole-component atoms/H/formal charges. No chemical
perception or source mutation occurs. Inspection-v5 and usability-v3 reports
carry separate policy identity; default reports and worker bytes remain exact.
All source-relative stereo, numerical and native checks remain independent.
The [C117 contract](cif-doctor.md#explicit-neutral-purine-representation-c117)
records preserved-candidate qualification and exclusions. C118 below extends
the explicit generation handoff; neither linked PNA targets nor ordinary adoption
is established by the isolated assessment.

## Explicit source-native representation handoff (C118)

The optional C117 representation policy now derives an explicit source contract
before generation. A separately versioned worker checks reader, controlled charge,
class-conversion and finished inventories without editing native aromatic orders.
The default worker is byte-identical. Candidate chemistry/stereo/numerical/native
qualification remains independent; retained partial output is never erased by
an execution failure. The standalone v2 reader recomputes the specification,
source/worker/API bindings, stage evidence and actual candidate, without captured
code execution or native object deserialization. Legacy mixed recovery is unchanged.
See the [C118 contract](cif-doctor.md#explicit-purine-generation-handoff-c118).

## Explicit PNA source network preparation (C119)

`cif_pna_source_network` consumes fresh C114/C108 source authority and builds one
connected, site-qualified graph with exact retained source atoms/bonds and explicit
amide edges. It freezes manifest-declared inputs and writes a completion receipt
last in a fresh directory. Its reader verifies hashes and recomputes both the
source inspection and complete graph; a stored pass never replaces source proof.
Coordinates, energy types, numerical restraints and final stereochemistry remain
unassigned. This separates chemical construction input from numerical dictionaries
and avoids treating pruned isolated restraints as linked evidence. Existing
contexts/reports and ordinary generation remain unchanged. See the
[C119 contract](cif-doctor.md#explicit-pna-source-network-packages-c119).


## FANA source/candidate boundary (C120)

An explicit read-only family gate composes the existing attachment matcher and
complete-candidate assessor. Topology binds the sugar positions; neutral terminal
C2′ fluorine, explicit local H/D/charge state and source R/S declarations define
the bounded beta-D/L FANA pattern. No workbook label or residue-code allowlist
selects chemistry. Candidate assessment retains whole-source chemistry and
requires preserved coordinates at all four source sugar centres. Unknown hands
remain unresolved. Schema-1 reports use `cif-source-declared-fana-v1`; CLI and
API perform no writes or native calls. Ordinary Coot construction remains gated
because its parent-DNA restoration does not establish modified-sugar fidelity.
Native A/C/T/U isolated controls pass in C120; C121 below subsequently qualifies
GFL's carbonyl-purine reader representation. Linked numerical qualification remains
open. See the
[FANA contract](cif-doctor.md#fana-source-and-candidate-preservation-c120).


## Explicit neutral 6-oxo purine representation (C121)

A separate graph/valence whitelist authorizes complete source-declared aromatic
conversion of the five-membered ring, including its shared fusion bond. The
6-carbonyl, nonshared spectator orders and whole-source chemical state remain
fixed. Its explicit policy is dispatched through existing assessment and source-native
contracts; standalone replay recomputes the recorded policy instead of assuming
C117. The old default and whole-purine rule and both worker texts are unchanged.
Existing schema-1 parameterized envelopes carry the new policy ID; no migration.
GFL/0DG/40G pass isolated native controls. DG generation passes but its standard
native name interpreter fails on HOP2, a separate consumer boundary. See the
[6-oxo contract](cif-doctor.md#neutral-6-oxo-purine-source-representation-c121).


## Explicit FANA enantiomer source relation (C122)

A read-only API requires explicit whole-component inversion intent and distinct
parent/target codes. It reuses the parent FANA/NAR topology, requires exact full
graph/H/charge/bond annotations and reversed four-centre declarations, and checks
all pair distances plus every ordered sugar-neighbour triple in all supplied
standard coordinate families. Nonfinite computed geometry cannot pass. Extra or
unknown centres, numerical targets and target descriptor tables remain outside
this source-only scope. Schema-1 reports use
`cif-explicit-fana-enantiomer-source-v1`; no existing behavior or schema migrates.
One explicitly derived L-FANA-C control passes generation and two isolated native
checks, with cold source/candidate/native replay. Target NAR registration, model
insertion, linked chemistry and independent CIP remain separate. See the
[enantiomer contract](cif-doctor.md#explicit-fana-enantiomer-source-check-c122).


## Local FANA component package and NAR overlay (C123)

An explicitly supplied C122 enantiomer becomes a fresh immutable package only
when its PDB-compatible code is absent from declared CCD filenames, the explicit
workbook and caller-reserved codes. Filename/record comparisons fold case on all
platforms; CCD directory symlinks cannot expand the declared namespace. The derived record preserves NAR base roles
and chemical context, changing component identity/sugar label and clearing
inherited descriptive claims. The original workbook stays byte-identical.
A fixed file manifest and last-written completion receipt bind the package;
reads recompute the full relation and record rather than trusting saved status.
Binding into consumer records rechecks the live declared namespace and returns
a local copy without patching the global loader. Neither snapshot nor recheck
is an atomic/global reservation. Schema-1 policy is
`cif-local-fana-enantiomer-component-v1`; ordinary construction and existing
schemas are unchanged. The [component contract](cif-doctor.md#local-fana-component-identity-and-narestraints-binding-c123)
records NAR compiler/native controls and remaining whole-sugar placement work.


## Whole-residue FANA construction control (C124)

A separate immutable three-residue control binds a C123 component package and
complete source-preserving candidate. It validates explicit internal link state,
source-named neutral leaving groups and workbook-bound host glycosidic identity.
A proper sugar-frame rotation moves the whole selected residue; no DNA scaffold
is restored. It checks internal distances and all four sugar hands after PDB
serialization, preserves flanking records and exposes both junction distances.
The offline reader recomputes chemistry and model bytes from frozen authority,
rather than trusting recorded success. Schema-1 policy is
`cif-rigid-whole-fana-linked-control-v1`; existing CLI/PostMR and run/checkpoint
schemas are unchanged. Local native diagnostics retain the central FANA
projection/proxies, but lose the incoming link. C110 flank chemistry remains
unqualified. Placement is implemented; junction repair, complete native linkage
and production mutation are separate. A translation-only control restores the
incoming bond but exposes missing O3′–P–O1P/O2P angles; complete source-named
junction restraints are also required. See the
[placement contract](cif-doctor.md#whole-residue-fana-placement-control-c124).


## Source-bound FANA junction angle adapter (C125)

The separate schema-1 `cif-source-bound-fana-junction-angles-v1` package binds a
C124 source projection, exact native model and explicit RNA/DNA link template.
It resolves template phosphate roles independently, preserving the source names,
and emits only the two potentially missing incoming angles. Existing native
bond/anchor-angle targets, four P neighbours and complete internal angles are
prerequisites; an absent bond never becomes an angle-only connection.
Readback rederives the text and source bindings from frozen files. Independent
native readback must add exactly the requested proxies, retain all other captured
covalent categories and complete six-angle coverage. Existing captures and inputs
are preserved. Ordinary PostMR and installed libraries are unchanged; no run or
checkpoint migration is required. This corrects the mixed-name consumer gap in
the translated L-FANA-C control, without qualifying its protonation/numerical
chemistry or repairing junction geometry. See the
[angle contract](cif-doctor.md#source-bound-fana-junction-angles-c125).


## Source-preserving FANA bridge construction (C126)

The schema-1 `cif-fana-torsion-bridge-seed-v1` package extends the C124 diagnostic
with a bounded three-rotor search and proper rigid fit. A graph-bound leaving
oxygen is a virtual direction target for the incoming oxygen, never an added
model atom. Internal source heavy bonds/angles, ring geometry, four sugar hands
and exact flanks are preserved; the score selects a seed without accepting its
chemistry or physical energy. Readback reruns the same bounded calculation from
frozen inputs on the recorded NumPy runtime, with no native execution.

The optional `bridge_seed` input to the C125 adapter adds the separate policy
`cif-source-bound-fana-seed-junction-angles-v1`. Exact placement/model binding and
both-link/outgoing-angle prerequisites extend the shared validator. Native
qualification still requires only the requested incoming angle additions and
all other captured covalent proxies unchanged. Old translation-only packages
replay unchanged. Source definitions and installed libraries remain untouched;
there is no CLI, production mutation or run/checkpoint migration. See the
[bridge contract](cif-doctor.md#source-preserving-fana-bridge-seed-c126) for search
bounds, serialization, runtime portability and remaining chemistry/geometry gates.


## Native nonbonded attribution (C127)

The opt-in `nonbonded_inventory` extension requires linked energy evidence and
freezes two fixed native pair snapshots under schema-1
`cif-native-nonbonded-attribution-v1`. It reuses the existing bounded native cache
evaluator and its actual energy-object pair lists. Default worker bytes remain
unchanged. Offline review binds atom identities/coordinates, replays positive-
parameter prolsq arithmetic, sums per-pair residuals/gradients, and matches the
captured full manager and repeated membership. All pairs remain visible.
Unsupported symmetry/functions fail the explicit diagnostic, without adding
chemical or geometry approval. No production or run/checkpoint migration occurs.
The FANA controls show why topology must precede score comparisons: the translated
control lacks its outgoing backbone bond and has a native inferred base–base
bond; the connected bridge has significant next-residue crowding. See the
[pair contract](cif-doctor.md#native-nonbonded-pair-attribution-c127).


## Exact FANA construction topology (C128)

The additive source-bound reader combines C109's captured artifact/identity/proxy
checks with C124 placement and C126 seed rederivation. It compares every native
inter-residue bond with the explicit two-link source context, retaining missing,
extra, duplicate and symmetry evidence. Optional frozen NARestraints policy/PHIL
separates only exactly declared and materialized N/O pairing bonds; origin IDs
alone never exempt a proxy. This checks supplied intent, not fresh recipe origin.
The strict prerequisite raises on topology mismatch before future construction
or score-comparison work; it does not accept geometry, bond-order/numerical
chemistry or flank definitions. Existing mechanics packages remain readable.

Schema-1 policies are `cif-declared-native-topology-v1` and
`cif-source-bound-fana-topology-v1`. Capture readback now recognizes the exact
maintained optional energy/nonbonded worker compositions without changing their
bytes or granting score qualification. There is no runtime default, CLI or
checkpoint migration. See the [gate contract](cif-doctor.md#declared-fana-topology-gate-c128).


## Ordinary fixed native derivative evidence (C129)

An optional native inspection extension reuses the fixed directional audit and
raw-number replay at one initial coordinate set. The helper namespace is isolated
from the legacy worker, whose bytes remain unchanged when the option is absent.
The capture records raw numerical evidence, selected probes, static signatures,
manager digest and native source fingerprints before/after. The read-only reviewer
recomputes the result; a numerical disagreement is REVIEW, malformed evidence is
an error. C109 binds the exact request, maintained worker and artifact checksums.

Schema-1 `cif-native-fixed-gradient-inventory-v1` requires explicit fixed policy
and excludes nonzero parallelity, special positions and nonidentity symmetry.
It adds no optimizer, production default, CLI or checkpoint migration. The FANA
bridge passes these sampled ordinary derivatives with the same manager and both
declared links; crowding and angle repair remain separate. See the
[methods and scope](cif-doctor.md#fixed-native-derivative-capture-c129).


## Selected-coordinate native geometry (C130)

A separate optional trial optimizes an explicit Cartesian subset while evaluating
the full fixed-policy native environment. Frozen coordinates are reconstructed
on every evaluation; the candidate serializer preserves all unselected PDB
records byte-for-byte. A fresh ordinary manager must exactly match the C129
qualified start before optimization. The attempt retains raw trace/stopping,
source fingerprints, owned execution state and full-precision/serialized numerical
evidence. Failed attempts remain intact and every new trial gets a fresh directory.

Read-only replay binds schema-1 `cif-selected-native-geometry-v1` artifacts,
maintained helpers, exact candidate bytes and raw numerical evidence. A separate
`cif-source-bound-fana-selected-geometry-v1` reviewer binds the source bridge and
fresh native derivative/pair captures, preserving declared topology, native
mechanics and four source-relative sugar hands. Changed cached neighbour pairs
require the established exact-zero contribution proof. Fixed PDB/optimizer
coordinates remain exact; native conversion uses the existing capture roundoff
bound. No ordinary worker, numerical kernel, CLI or checkpoint behavior changes.

The first central-only L-FANA-C trial reduces crowding and outgoing-angle strain
but reaches its iteration limit. It remains diagnostic and unadopted; residual
geometry and source/target qualification remain open. See the
[methods and evidence](cif-doctor.md#selected-native-fana-geometry-c130).


## Selection-dependent environment reporting (C131)

The read-only `cif-selected-environment-review-v1` report composes existing
captured Cartesian geometry and verified native nonbonded arithmetic. It partitions
each measured dependency into selected-only, boundary or fixed-only groups without
losing unsupported rows or deferred categories. Only actual native nonbonded
residuals are summed; descriptive covalent deviations remain separate from energies
and no complete objective floor is inferred. Selected and held full-gradient
components are reported separately, without a new convergence criterion.

The FANA adapter first runs the complete C130 endpoint gates and retains their
bindings, check results and stopping classification. It rechecks candidate and
pair-receipt identity before reading the native inventory. This adds no coordinate
or worker change, process execution, checkpoint migration or production default.
See the [methods and measured limits](cif-doctor.md#selected-environment-review-c131).


## Fixed-coordinate dictionary comparisons (C132)

The optional `cif-native-fixed-coordinate-target-comparison-v1` reader binds two
complete maintained native captures to identical model bytes and declared links.
Only ordered dictionary inputs and definitions at explicitly named sites may
change. Native context, PHIL, atoms and all outside-site proxy parameters remain
exact. Every captured named proxy change is retained; scalar target/weight effects
are separated from unchanged observations and deferred calculations stay explicit.

The reader never equates a lower objective under changed definitions with geometry
improvement, convergence or chemical permission. Source graph, H/D, formal charge
and linked/terminal state require independent qualification. It adds no worker,
optimizer, CLI, checkpoint migration or production-default change. See the
[methods and controlled evidence](cif-doctor.md#fixed-coordinate-dictionary-controls-c132).


## Source-bound preparation qualification

Explicit representation-qualified candidates cross the linked/terminal boundary
only after fresh whole-source reassessment and the complete named isolated-native
contract. Exact bytes, declared graph/H/charge and every source fixed/R/S centre
bind the permission; codes and labels identify records, not chemical families.
Every retained source centre must keep its declared neighbours through projection.
Changing that neighbourhood requires separate linked-configuration authority.

The opt-in linked v3 and terminal v2 receipts record these bindings and projected
centre states. Previous callers and policy identifiers remain unchanged. Explicit
DNA/L-DNA source declarations select existing native polymer machinery; conventional
backbone names remain the default. An explicit source-named internal-phosphate
adapter also checks unique aliases against the graph and neutral-reacting-port
state; it preserves literal names and does not authorize aliased terminal operations. Generic source ports do not yet imply a universal
native adapter. Native effective definitions, formal-charge availability, actual
model coordinates and numerical derivatives remain separate qualifications.
No new CLI, run/checkpoint migration, installed-library mutation or automatic
adoption is introduced. See the [contract and evidence](cif-doctor.md#source-bound-qualified-site-preparation-c133).


## Qualified component bundles and ReadySet endpoint checks

The opt-in bundle contract composes independent stored source/numerical entries
under one exact model, consumer, declared links, native context and ordered input
list. Ownership is explicit by component, site and modifier. Readback rederives
all generated files; whole-model before/after captures qualify all selected sites
together. Source-name phosphate aliases are opt-in, graph-bound internal operations.

Ordinary per-component ReadySet consumption remains the preparation step. Its
observer/argument/source/effective-output proof is replayed before a fresh native
readback of the final model and effective dictionaries. Failed or missing endpoint
evidence keeps the qualified starting diagnostic; a damaged start is refused.
Strict ordered proxies are unchanged: harmless-looking atom reorderings still
need a separate equivalence proof. No automatic ordinary adoption or checkpoint
migration follows. See the [contract](cif-doctor.md#qualified-component-bundles-and-final-readyset-readback-c139).
