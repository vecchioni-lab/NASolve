# NASolve

NASolve is a guarded command-line workflow for nucleic-acid molecular
replacement and post-MR model preparation. It discovers autoPROC/STARANISO
inputs, selects and validates an approved search model, runs Phenix Phaser with
reproducible settings, preserves modified residues and other heteroatoms, and
classifies the solution by TFZ.

The current release provides **AutoMR**, **PostMR**, and a conditional
**AutoSol** branch. PostMR constructs
supported modified nucleotides through Coot, restores trusted parent
coordinates, can apply complete chain sequences, generates either the 5W6W
restraint stack or modification-scoped pair restraints, supplies reviewed ligand
dictionaries, and runs ReadySet without hydrogens. When PostMR finds iodine,
bromine, or selenium in a nucleotide, AutoSol performs guarded MR-SAD phasing
and verifies a corresponding anomalous site. Refinement and final validation
remain deliberately gated for later releases.

## Quick start

### Install

```bash
git clone https://github.com/vecchioni-lab/NASolve.git
cd NASolve
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

### Check the runtime

```bash
nasolve check
python -m pytest
```

`nasolve check` discovers and validates Phenix, Coot, and NARestraints. If an
external tool is not found automatically, see [Configure external
tools](#configure-external-tools).

### Run AutoMR and PostMR

For a standard W/5W6W-frame dataset:

```bash
DATASET=/absolute/path/to/dataset
nasolve automr "$DATASET" -W --pair F:D --execute
```

NASolve prints the new numbered run directory. Use that exact path for PostMR:

```bash
RUN=/absolute/path/to/dataset/AutoMR/run_001
nasolve postmr "$RUN"
```

If PostMR reports an anomalous heavy-atom candidate, run the conditional
MR-SAD layer:

```bash
nasolve autosol "$RUN"
```

AutoSol is not run for ordinary structures without a nucleotide-bound iodine,
bromine, or selenium atom.

For a nonstandard dataset containing one search-model PDB, omit the frame and
pair options:

```bash
nasolve automr "$DATASET" --execute
```

Useful opt-in variants are:

```bash
# Mirror the selected D/L nucleic-acid search model before Phaser.
nasolve automr "$DATASET" --mirror --execute

# Restrain only guessed base pairs containing a modified nucleotide.
nasolve postmr "$RUN" --modified-pairs-only
```

### Inspect the prepared model in Coot

Launch graphical Coot from a run-local working directory so its histories,
state files, backups, and downloads do not clutter the repository:

```bash
RUN=/absolute/path/to/dataset/AutoMR/run_001
mkdir -p "$RUN/PostMR/CootGUI"
(cd "$RUN/PostMR/CootGUI" && coot \
  --pdb "$RUN/PostMR/Model/readyset_model.pdb" \
  --dictionary "$RUN/PostMR/Restraints/curated_ligands.cif" \
  --auto "$RUN/Phaser/mr_solution.mtz")
```

Omit `--dictionary .../curated_ligands.cif` when the run contains no curated
components. The commands above are the complete normal workflow; the remaining
sections document inputs, decisions, safeguards, and outputs.

## What AutoMR does

For each dataset, AutoMR:

1. locates the reflection MTZ, `Data_1*.cif`, and `summary.html` files;
2. chooses a standard 5W6W/3GBI search model or validates a user-supplied PDB;
3. optionally mirrors the selected model through NARestraints, then checks the
   exact model that Phaser will use, including modified nucleotides written as
   `HETATM`;
4. checks H3/R3 symmetry for standard-frame runs;
5. freezes the effective inputs in a new, numbered run directory;
6. optionally runs Phenix Phaser with one explicit ensemble and preserved
   heteroatoms; and
7. reports the best TFZ and retains both the raw and selected MR outputs.

NASolve does not edit the original dataset or search model.

## Requirements

- Python 3.10 or newer
- Git
- A working Phenix installation containing `phenix.phaser`,
  `phenix.mtz.dump`, `phenix.ready_set`, and `phenix.refine`; the conditional
  heavy-atom branch additionally requires `phenix.autosol`
- Coot with embedded Python when a supported base construction is needed
- [NARestraints](https://github.com/vecchioni-lab/NARestraints), installed
  automatically as a NASolve dependency

Phenix is an external dependency and is not distributed with NASolve.

## Installation

Clone the repository and install it in an isolated Python environment:

```bash
git clone https://github.com/vecchioni-lab/NASolve.git
cd NASolve
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

If you prefer Conda, create an environment in the repository instead:

```bash
conda create -p .venv python=3.12
conda activate ./.venv
python -m pip install -e .
```

For development and testing, install the test dependencies:

```bash
python -m pip install -e ".[test]"
python -m pytest
```

## Configure external tools

Begin with:

```bash
nasolve check
```

NASolve checks the current `PATH`, any saved configuration, and standard
installation locations. On macOS it searches locations such as
`/Applications/phenix-*`; equivalent standard locations are checked on Linux
and Windows. A discovered installation is validated and remembered for later
runs.

If automatic discovery fails, configure Phenix once using its installation
directory, `phenix_env.sh`, or one of its executables:

```bash
nasolve configure phenix /path/to/phenix/phenix_env.sh
```

The saved path is revalidated at startup, so moving or replacing Phenix does
not silently leave NASolve using a stale installation.

For a one-run override, place the global option before the subcommand:

```bash
nasolve --phenix-root /path/to/phenix automr DATASET --execute
```

The environment variable `NASOLVE_PHENIX_ROOT` provides another override.

Coot is discovered independently from the current `PATH`, saved
configuration, and standard platform locations. Configure it explicitly when
needed with:

```bash
nasolve configure coot /path/to/coot
```

## Repository layout

When NASolve is used from a source checkout, the repository is organized as:

```text
NASolve/
├── MR_frames/
│   ├── 5W6W/          approved W-frame search models
│   └── 3GBI/          approved 3GBI-frame search models
├── examples/          optional test datasets
├── src/nasolve/       application source
├── tests/             automated tests
├── docs/              design and architecture notes
├── pyproject.toml     package and dependency definition
└── README.md
```

User datasets may live anywhere. They do not need to be copied into
`examples/` or into the repository.

Each approved standard-frame directory used by AutoSol also contains a
`seq_base.txt` sequence file. It is a required AutoSol input but is never used
for model building, because NASolve disables every AutoBuild path.

## Choosing a run type

| | Standard frame | Nonstandard model |
| --- | --- | --- |
| Search model | Selected from `MR_frames/5W6W` or `MR_frames/3GBI` | Supplied in the dataset |
| Required request | Frame plus ordered pair | One PDB, found or named |
| Space-group rule | H3/R3; P1 only through the explicit shunt | No standard-frame symmetry gate |
| Standard-site change | Exact catalogue pair or recorded fallback mutation | Use explicit mutation sites |
| Complete sequence | May be introduced by a future frame preset | Chain-labelled sequence file or inline chains |
| Optional mirror | `--mirror` on the selected catalogue model | `--mirror` on the selected dataset model |
| Typical command | `nasolve automr DATASET -W --pair E:G --execute` | `nasolve automr DATASET --execute` |

Both routes use the same dataset discovery, model assessment, frozen run
records, Phaser execution, heteroatom preservation, and TFZ gates.

## Dataset layout

AutoMR works on one dataset directory at a time. A typical standard-frame
dataset is:

```text
my_dataset/
├── Data_1_autoPROC_STARANISO_all.cif
├── staraniso_alldata-unique.mtz
└── summary.html
```

The filenames do not have to match this example exactly:

- NASolve prefers the single top-level MTZ whose punctuation-insensitive name
  contains both `staraniso` and `alldata`. If none has that name, the only
  top-level MTZ is accepted.
- The metadata file must be the single top-level `Data_1*.cif`, matched without
  regard to case or punctuation.
- The autoPROC summary must be the single top-level `summary.html`.

Ambiguous or missing inputs stop the run instead of choosing a file silently.

For a nonstandard run, add a good MR model in PDB format:

```text
my_dataset/
├── Data_1_autoPROC_STARANISO_all.cif
├── staraniso_alldata-unique.mtz
├── summary.html
└── search_model.pdb
```

If there is exactly one top-level PDB, NASolve finds it automatically. If the
directory contains more than one PDB, select the intended model in
`nasolve.txt`.

## Quick start: standard frames

Standard mode uses the approved search-model catalogues in `MR_frames/5W6W`
and `MR_frames/3GBI`. `W` is the short name for the 5W6W frame.

Prepare and inspect a 5W6W run without launching Phaser:

```bash
nasolve automr my_dataset -W --pair E:G
```

Run Phaser after the same guarded preflight:

```bash
nasolve automr my_dataset -W --pair E:G --execute
```

Use the 3GBI frame with:

```bash
nasolve automr my_dataset -3GBI --pair C:C --execute
```

The pair is ordered: `E:G` and `G:E` are different catalogue requests. AutoMR
resolves both aliases to ligand codes, searches for an exact
`FIRST_SECOND.pdb` model, and otherwise uses the frame's designated fallback:

| Frame | Catalogue | Fallback model |
| --- | --- | --- |
| `W` / `5W6W` | `MR_frames/5W6W/` | `C_G.pdb` |
| `3GBI` | `MR_frames/3GBI/` | `C_C.pdb` |

An exact catalogue model can proceed directly to MR. A fallback model can also
be used, but the requested standard-site changes are recorded as a required
post-MR mutation plan.

If the catalogue is stored elsewhere, use either:

```bash
nasolve automr my_dataset -W --pair E:G --frames-dir /path/to/MR_frames
```

or set `NASOLVE_MR_FRAMES`.

### Standard-frame symmetry rule

The W and 3GBI recipes are intended for H3/R3 data. NASolve compares the space
group reported by:

- `phenix.mtz.dump` for the MTZ header;
- every explicit space-group entry in `Data_1*.cif`; and
- the final `Spacegroup name` entry in `summary.html`.

`H 3`, `H3`, `R 3`, `R3`, and `R 3 :H` are treated as equivalent and use one
MR copy. The exact MTZ symbol is retained in the report so its notation can be
restored in the final structure-solution layer.

Standard-frame P1 data are blocked by default. An expert may explicitly enable
the discouraged three-copy shunt:

```bash
nasolve automr my_dataset -W --pair E:G --allow-p1-standard --execute
```

This creates a prominent red flag in the run report. Other space groups, or a
real disagreement between the authoritative inputs, stop a standard run.
Nonstandard mode does not apply the H3/R3 gate.

## Quick start: nonstandard models

When a dataset contains exactly one top-level PDB and no standard frame is
requested, AutoMR uses nonstandard mode automatically:

```bash
nasolve automr my_dataset
nasolve automr my_dataset --execute
```

The first command performs preflight only. The second creates a new run and
executes Phaser.

Nonstandard models should already be suitable search models. AutoMR never
changes their sequence before MR; it freezes the requested chain sequences so
PostMR can mutate the accepted Phaser solution through Coot.

To solve the opposite D/L hand, mirror the selected search model before MR:

```bash
nasolve automr my_dataset --mirror --execute
```

NARestraints performs the coordinate and canonical residue/atom-name
transformation. NASolve retains the untouched source as
`Model/source_model.pdb`, assesses and checksums the mirrored
`Model/input_model.pdb`, and gives only the latter to Phaser. A mirrored run
with a required PostMR base change stops until the guarded
unmirror/Coot/remirror path is implemented; this prevents an L model from
silently receiving D-DNA chemistry.

## The `nasolve.txt` input file

If `nasolve.txt` is absent, AutoMR generates a minimal file in the dataset so
the run can be repeated without reconstructing the command. It records user
intent; resolved paths, checksums, Phenix details, model statistics, and scores
belong in the numbered run report.

A standard input file is:

```ini
[automr]
mode = standard
frame = W
pair = E:G
```

The equivalent command is:

```bash
nasolve automr my_dataset --execute
```

A nonstandard input file may name a dataset-relative model, a chain-labelled
sequence file, and later site-specific changes:

```ini
[automr]
mode = nonstandard
model = search_model.pdb
sequence_file = construct.fasta
mirror = false

[mutations]
A:8 = 5IU
B:8 = DT
```

The sequence file may use chain-labelled FASTA:

```text
>A
GCGTACGT
>B
ACGTACGC
```

or `CHAIN = SEQUENCE` lines. Inline `[sequences]` entries remain supported as
an alternative; a run cannot use both forms.

Sequence chain names must occur in the model, and each sequence length must
match the model's polymer-residue count for that chain. Mutation sites use
`CHAIN:RESID` and must exist in the model. Modified nucleotides written as
`HETATM` count toward the chain length when their residue code occurs in the
NARestraints library.

Sequences and mutations are validated and frozen in the numbered run. PostMR
applies the complete sequence first, the standard pair second, and explicit
mutation sites last. Thus an explicit modified nucleotide can intentionally
override the ordinary base specified by the chain sequence.

Command-line frame and pair options override values from `nasolve.txt`; the
effective configuration is always frozen in the new run directory. Use
`--config PATH` to read a different input file.

## Residue aliases

Aliases are case-sensitive. DNA and RNA tokens are deliberately distinct.
Any literal ligand code present in NARestraints may also be used directly.

| Token | Ligand code | Token | Ligand code |
| --- | --- | --- | --- |
| `D` | `1AP` | `rA` | `A` |
| `T` | `DT` | `rC` | `C` |
| `C` | `DC` | `rU` | `U` |
| `G` | `DG` | `rG` | `G` |
| `A` | `DA` | `rB` | `IG` |
| `U` | `DU` | `rP` | `50L` |
| `F` | `DF` | `rZ` | `50N` |
| `E` | `DE` | `rI` | `I` |
| `Q` | `S6G` |  |  |
| `iC` | `C38` |  |  |
| `iU` | `5IU` |  |  |
| `B` | `IGU` |  |  |
| `P` | `DP` |  |  |
| `Z` | `DZ` |  |  |
| `I` | `DI` |  |  |
| `X` | `DX` |  |  |
| `K` | `CGY` |  |  |

`DE` and `DF` are deliberate three-character compatibility labels used by the
laboratory PDB/refinement workflow. `DF` records the official five-character
CCD identity `A1AAZ` for final mmCIF deposition; `1AP` is already an official
CCD code. `C38` and `5IU` are the official DNA-linking components for iodo-dC
and iodo-dU. Component identities are written to the PostMR report.

## Preparing an accepted MR solution

After a run reaches `MR_SUCCESS`, prepare it for refinement with:

```bash
nasolve postmr my_dataset/AutoMR/run_004
```

`MR_REVIEW` runs stop unless the user explicitly supplies
`--allow-mr-review`. Failed MR runs cannot enter PostMR.

For the W/5W6W frame, PostMR uses the fixed standard sites `A:12` and `B:4`.
It applies ordinary DNA/RNA base changes through headless Coot. For a supported
modified nucleotide, Coot first mutates the site to its clean canonical parent
(`DT` for `DE`/`DF`/`5IU`, `DA` for `1AP`, `DG` for `S6G`, or `DC` for
`C38`), builds the curated component from its dictionary, overlaps it, and
replaces the parent. NASolve then restores the
coordinates, occupancies, and B factors of every atom shared with the parent.
This preserves the canonical sugar and phosphate exactly while retaining only
the genuinely modified atoms from the dictionary. Hydrogens are removed.
Unsupported construction stops and asks the user for a model. Full-sequence
mutation uses the same Coot base-mutation path. NASolve restores the original
sugar and phosphate coordinates after every ordinary base change, so a whole
sequence application cannot curl or rotate the inherited backbone.

For reviewed single-atom sulfur substitutions, dictionary overlap does not
determine the final sulfur direction. PostMR projects `S4`, `S1`, or `S6`
along the canonical parent's `C4-O4`, `C2-O2`, or `C6-O6` vector while keeping
the dictionary-derived C-S bond length. The substituted atom inherits the
parent oxygen's occupancy and B factor.

For `C38` and `5IU`, PostMR places iodine outward from mapped ring atom `C5`
along the external `C4-C5-C6` bisector, using the reviewed dictionary's C-I
bond length from its ideal-coordinate set. Coot's generated monomer coordinates
are not used for this distance. The iodine inherits the parent `C5` occupancy
and B factor.

The 5W6W restraint stack contains:

- NARestraints output generated from `Std_padd.txt` (`A 11:13` paired with
  `B 5:3`), including its stacking restraints; and
- 17 additional scaffold base-pair definitions from the packaged 5W6W
  secondary-structure template.

The scaffold template contains no stacking pairs and omits the two base pairs
already supplied by `Std_padd.txt`, preventing duplicate restraints.

For a standard or nonstandard run that should restrain only modified chemistry,
use:

```bash
nasolve postmr RUN --modified-pairs-only
```

PostMR runs the NARestraints guesser after Coot and backbone restoration with
noncanonical-pair guessing enabled. It keeps a guessed pair when either
partner has a noncanonical nucleotide residue code, writes no stacking
restraints, and records all guessed/retained pairs and warnings. A canonical
sequence change alone is not treated as a modification. If no modified pair is
found, the restraint step is a successful no-op and ReadySet still runs.

Known problematic Phenix residues use reviewed dictionaries from NASolve's
local ligand library. The `E` token resolves to `DE`; legacy `E` reports frozen
as `8RO` are migrated to `DE` because official CCD `8RO` is a different
compound with an unwanted sulfur-ring topology. `DF` is tied explicitly to
CCD `A1AAZ`. The reviewed dictionaries enforce `DE C4-S4` without `N3-S4`,
`DF C2-S1` without `N3-S1`, and `S6G C6-S6` without `N1-S6`. ReadySet is launched in its own directory with
`hydrogens=False` and its output is rejected if hydrogens appear or atom counts
change unexpectedly.

The curated CIF and the coordinate edit solve different problems. Coot creates
and places the modified residue; the CIF defines its chemical topology and
ideal geometry. Although `phenix.refine` can accept a model plus `1AP.cif`
directly, NASolve still uses ReadySet as the uniform final preparation and
validation gate. ReadySet is not trusted to invent the modification, and it
does not replace the NARestraints inter-residue geometry.

NARestraints v1.1.1 records the `DF` canonical `O2` mapping as the nonexistent
atom `S2`. PostMR corrects this to `S1` only in memory for the current builder
call, records the correction in `report.json`, and never edits the installed
NARestraints workbook.

The `Q` token resolves to official CCD `S6G` and uses `DG` as its canonical
construction parent. NARestraints v1.1.1 also stores its `C5` mapping as `C5 `;
PostMR trims that exact trailing space in the same process-local adapter.

After ReadySet, PostMR scans nucleotide-like residues for configurable
anomalous elements. The initial trigger set is iodine, bromine, and selenium;
it is element-driven rather than restricted to known residue codes. Element
columns are preferred, with atom-name inference recorded when required. The
candidate sites and whether AutoSol is required are written to `report.json`.

## Run directories and outputs

Every invocation creates a new numbered directory. Existing runs are never
overwritten:

```text
my_dataset/
├── nasolve.txt
└── AutoMR/
    └── run_001/
        ├── nasolve.input.txt
        ├── automr.log
        ├── report.json
        ├── Model/
        │   ├── source_model.pdb       # present only for --mirror
        │   ├── input_model.pdb
        │   └── assessment.json
        ├── Phaser/
            ├── phaser.eff
            ├── phaser.log
            ├── PHASER.1.pdb
            ├── PHASER.1.mtz
            ├── mr_solution.pdb
            └── mr_solution.mtz
        └── PostMR/
            ├── postmr.log
            ├── report.json
            ├── Model/
            │   ├── mr_solution.pdb
            │   ├── after_coot_raw.pdb
            │   ├── after_coot.pdb
            │   ├── prepared_model.pdb
            │   └── readyset_model.pdb
            ├── Coot/
            │   ├── mutate.py
            │   ├── coot.log
            │   └── parent_A_12_DT.pdb
            ├── Restraints/
            │   ├── Std_padd.txt
            │   ├── narestraints_Std_padd.eff
            │   ├── 5W6W_secondary_structure.eff
            │   ├── DE.cif
            │   ├── DF.cif
            │   └── 1AP.cif
            └── ReadySet/
                ├── ready_set.log
                ├── prepared_model.updated.pdb
                └── prepared_model.ligands.cif
```

`Model/input_model.pdb` is the checksum-verified search model actually supplied
to Phaser. Without `--mirror`, heteroatoms and all bytes are preserved from the
selected source. With `--mirror`, the untouched source is retained separately
and the transformed model must preserve its atom, residue, chain, and HETATM
inventory. Phaser is run
with:

- one explicit ensemble named `nasolve_model`;
- `use_hetatm = True`;
- the model checker's polymer-residue count as the NA composition;
- an explicit model RMSD of 1.0 A; and
- one search copy for H3/R3, or three only for the explicit P1 shunt.

The original Phaser outputs are retained. `mr_solution.pdb` and
`mr_solution.mtz` are stable copies selected for the next pipeline layer.

`report.json` is the machine-readable provenance record. It includes the
effective inputs, checksums, residue and heteroatom counts, symmetry evidence,
Phenix version and executable, generated parameters, command, TFZ/LLG, output
paths, and any post-MR mutation plan. `automr.log` is the corresponding concise
human-readable record.

## Result gates

AutoMR classifies the best final-solution TFZ reported by Phaser:

| Result | TFZ | Meaning | Exit code |
| --- | ---: | --- | ---: |
| `MR_SUCCESS` | `>= 8.0` | Accepted MR solution | `0` |
| `MR_REVIEW` | `7.0–7.99` | Red flag; inspect the solution before continuing | `3` |
| `MR_FAILED` | `< 7.0` or missing | Return to the model or inputs | `4` |

A candidate also fails if Phaser exits unsuccessfully or does not produce both
a PDB and MTZ output. Input, discovery, and preflight errors exit with code 2.

## Current scope

AutoMR currently supports PDB search models and Phenix Phaser MR_AUTO. PostMR
currently implements W/5W6W sites, canonical Coot mutations, curated label
normalization, complete sequence application, modification-scoped
NARestraints, and hydrogen-free ReadySet. It does not yet:

- construct arbitrary modified residues without an approved template;
- perform mirror-side sequence changes through an unmirror/Coot/remirror cycle;
- prepare the 3GBI frame, whose standard-site manifest is not yet defined;
- run `phenix.refine`;
- apply the final H3/R3 notation patch; or
- search multiple catalogue models automatically.

These operations are deliberately kept behind later validation gates rather
than being implied by an MR success. Always inspect the molecular-replacement
solution and electron density before treating it as a solved structure.

## Project presets and future model providers

The current frame directories are the first project presets. Future projects
can add sibling preset directories rather than new project-name branches in
the workflow code. A preset manifest can declare its MR catalogue and fallback,
site roles, sequence resource, restraint policy, AutoSol sequence, metalation
recipe, and model providers. A provider may later be a curated PDB, an
AlphaFold result, or another approved source; downstream stages consume the
same frozen model-and-capability contract.

This keeps project-specific scientific choices in versioned data while the
pipeline retains common validation, provenance, non-overwrite behavior, and
external-tool isolation.

## Problems and reproducibility

Start troubleshooting with:

```bash
nasolve check
```

For an individual run, inspect `automr.log`, `report.json`, and
`Phaser/phaser.log`. When reporting a problem, include the command, NASolve and
Phenix versions, terminal error, and the relevant log excerpt. Please do not
upload unpublished diffraction data or coordinates to a public issue unless
you intend to make them public.

Issues may be reported at
[github.com/vecchioni-lab/NASolve/issues](https://github.com/vecchioni-lab/NASolve/issues).
