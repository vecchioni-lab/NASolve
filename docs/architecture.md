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

### Dataset and symmetry discovery

Dataset discovery accepts the usual autoPROC/STARANISO naming variants rather
than renaming raw inputs. It prefers a unique MTZ whose punctuation-insensitive
name contains both `staraniso` and `alldata`, falling back to the only top-level
MTZ when there is exactly one. Metadata is the unique case-insensitive
`Data_1*.cif`; multiple candidates stop the run.

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
3. Classify the best TFZ: `>= 8.0` pass; `7.0–7.99` review; `< 7.0` fail.
4. `nasolve postmr RUN` applies supported site changes, builds the restraint
   stack, and runs ReadySet with hydrogens disabled.
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

## PostMR contract

PostMR is deliberately a separate command so an accepted Phaser result can be
inspected and rerun deterministically before refinement. It refuses to
overwrite an existing `PostMR/` directory. `MR_SUCCESS` is accepted;
`MR_REVIEW` requires an explicit override; other statuses stop.

The W-frame manifest assigns requested pair roles to `A:12` and `B:4`.
Canonical DNA/RNA changes use a generated headless Coot script. Curated
modified nucleotides use a canonical-parent mutation followed by dictionary
monomer construction, overlap, and residue replacement. Coot runs with its
backup directory redirected beneath the run and removes hydrogens before
writing. Full sequences expand over the frozen per-chain residue inventory;
application precedence is sequence, standard pair, then explicit mutation.
Every ordinary base change restores the pre-Coot sugar/phosphate coordinates.
Arbitrary modified-base construction remains a closed gate rather than being
silently inferred.

For mirrored runs, canonical targets are translated to the NARestraints L-side
codes (`0DA`, `0DC`, `0DG`, `0DT`, and RNA equivalents). Exact mirrored models
therefore are not accidentally mutated back to D chemistry. A required
mirror-side sequence change stops until the guarded
unmirror/Coot/remirror construction path is implemented.

For curated modifications, Coot also writes a canonical-parent snapshot.
NASolve copies the coordinates, occupancies, and B factors of every shared
atom back into the replaced residue and requires the complete sugar/phosphate
atom set to survive. Thus dictionary overlap positions only the new chemistry;
it cannot rotate or curl the existing phosphate. The restoration inventory is
recorded in the run report.

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

For W/5W6W, NARestraints consumes the packaged `Std_padd.txt` specification
(`A 11:13` / `B 5:3`) and remains the sole source of stacking restraints. The
portable 5W6W secondary-structure template contains 17 non-overlapping
scaffold base pairs, no stacking pairs, and no historical input paths, cell,
map, output, or GUI settings.

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

Problematic Phenix components are explicit curated-library entries. User token
`E` maps to the laboratory PDB-compatible `DE`, not official CCD `8RO`, whose
topology describes a different sulfur-ring compound. `F` maps to `DF`, with
official deposition identity `A1AAZ`; `D` maps to official `1AP`; and `Q` maps
to official `S6G` with canonical parent `DG`. The registry
defines canonical parents and required/forbidden sulfur bonds, which are
validated before Coot or ReadySet runs. ReadySet receives the curated CIF,
executes with `actions.hydrogens=False`, and is run with `cwd` set to its own
directory because Phenix 1.20.1 accepts but ignores `input.output_dir`. The
output is rejected if it contains hydrogen coordinates or changes total or
HETATM atom counts.

Coot/model editing, component CIFs, NARestraints, and ReadySet have separate
roles. Coot establishes coordinate identity and placement; CIFs establish
intra-residue topology; NARestraints establishes selected inter-residue
geometry. ReadySet is the uniform post-edit normalization and validation gate,
even where Phenix refinement could technically consume the edited PDB and CIF
directly.

NARestraints v1.1.1 has a legacy `DF` mapping of canonical `O2` to `S2`; the
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

## AutoRefine contract

AutoRefine separates immutable scientific inputs from evolving coordinates.
Each round inherits an improved model from one selected parent checkpoint, but
always retains the original STARANISO observations and original Free-R array.
Refinement-generated MTZ files are outputs and evidence; they cannot become the
observation source of a child by accident.

The root checkpoint is the ReadySet model. Its restraint set prefers
ReadySet's generated combined ligand CIF over the individual curated CIFs that
were supplied to ReadySet, while retaining the NARestraints PHIL and project
EFF files. An approved AutoSol file is a separate phase source. Explicit
reflection file names and labels prevent duplicate observations in the AutoSol
file from competing with the authoritative STARANISO array.
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

Refine Doctor is a finisher and diagnostic layer, not an unconstrained
R-factor optimizer. It starts from the current or explicitly named checkpoint,
records that pointer, and requires every trial to be an immutable sibling of
the same source. A successful trial is recommended for inspection but is never
selected automatically by the engine. In an interactive CLI session the user
receives a final `[y/N/i]` prompt: `y` performs the ordinary audited checkpoint
selection, while `n` or `i` leaves the pointer unchanged and prints commands
for inspection, later selection, and returning to the diagnosed source.

Before launching Phenix it audits the authoritative Free-R array with the
Phenix/CCTBX runtime. The audit measures the independent Friedel-group count,
test fraction, mate consistency, and test-set population across resolution.
Inconsistent mate flags, fewer than ten independent free groups, or a guarded
fraction outside 2-20% stop all trials. A small or shell-sparse test set is
classified as noisy rather than invalid. Refine Doctor never tries alternate
test-flag values and never regenerates flags merely to reverse an R-factor
ordering.

When the source checkpoint contains a refined anomalous group, its refined and
Henke-calculated `f''`, wavelength, model occupancy, B factor, and source
checkpoint are frozen as a benchmark in the Doctor report. If no benchmark
exists but a PostMR heavy atom does, one short benchmark branch is permitted.
Subsequent validation branches may disable anomalous-parameter refinement while
continuing to use the authoritative F+/F- observations; the benchmark remains
available to later metal-aware recipes.

The default bounded branches are:

- ML without HL phases, reciprocal-space XYZ, residue-group ADPs, no occupancy
  search, and anomalous-parameter refinement off; and
- the same parameterization with approved HL phases, allowing Phenix's
  automatic target to use MLHL.

An individual-ADP branch is eligible only at 3.2 A or better and with at least
three independent observations per modeled atom. This prevents low-resolution
DNA models from gaining a nominal R-factor improvement through an unsupported
parameter count. Trial definitions are declarative `RefineDoctorTrial`
records, so future project presets may supply additional reviewed strategies
without changing checkpoint or audit behavior.

A branch is strictly successful when its compatible model has `Rwork < Rfree`
and `Rwork < 0.30`. If no branch passes but the source has `Rwork < 0.30`, a gap
of at least -0.01, and a valid or merely noisy test set, Doctor may report the
source as good enough under review rather than manipulate the flags. All other
cases remain explicit user-review results.

## Stage-aware Coot views

`nasolve show RUN` resolves the most advanced viewable completed stage;
`nasolve show last DATASET` first chooses the highest numbered run. Explicit
`--stage` selection is available for comparison. `--checkpoint refine-NNN`
opens an arbitrary refinement checkpoint and its map in a checkpoint-specific
Coot pen without changing the current pointer. Profiles deliberately differ:

- AutoMR: Phaser model and Phaser MTZ;
- PostMR: ReadySet model, Phaser MTZ, and ReadySet-generated dictionary;
- AutoSol: original Phaser model, AutoSol HA model, and density-modified map
  coefficients; and
- AutoRefine: current refined checkpoint model, map coefficients, and its
  frozen dictionaries.

Every graphical process starts in `RUN/CootGUI/STAGE/` with its backup
directory redirected underneath the same pen. Run discovery uses numbered
directories and reports, never filesystem modification times.

## Project preset direction

Frame and project policy should become declarative data rather than additional
conditionals keyed to names such as `5W6W`. A future preset manifest beside each
frame catalogue can declare:

- model providers, exact-pair catalogues, fallbacks, and copy/symmetry policy;
- standard sites, chain sequences, and restraint resources or modes;
- metalation recipes and anomalous-element policy;
- the AutoSol sequence resource and phasing defaults; and
- approved discovery providers, including a later AlphaFold route.

The orchestration layers consume a frozen model plus declared capabilities.
This permits a new experimental campaign to ship a versioned preset directory
without changing common run allocation, provenance, safety gates, Coot/Phenix
isolation, or downstream reporting.
