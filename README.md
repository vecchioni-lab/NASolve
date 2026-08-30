# NASolve

NASolve is a guarded command-line workflow for nucleic-acid molecular
replacement and post-MR model preparation. It discovers autoPROC/STARANISO
inputs, selects and validates an approved search model, runs Phenix Phaser with
reproducible settings, preserves modified residues and other heteroatoms, and
classifies the solution by TFZ.

The current release provides **AutoMR**, **PostMR**, a conditional
**AutoSol** branch, checkpointed **AutoRefine**, and bounded **Refine Doctor**
triage. PostMR constructs
supported modified nucleotides through Coot, restores trusted parent
coordinates, can apply complete chain sequences, generates either the 5W6W
restraint stack or modification-scoped pair restraints, supplies reviewed ligand
dictionaries, and runs ReadySet without hydrogens. When PostMR finds iodine,
bromine, or selenium in a nucleotide, AutoSol performs guarded MR-SAD phasing
and verifies a corresponding anomalous site. AutoRefine runs Phenix quietly,
surfaces the crystallographic statistics normally shown by the GUI, and
preserves successful, review, failed, and manually imported models as
branchable checkpoints. Refine Doctor audits the frozen Free-R set, preserves
an anomalous-strength benchmark, and compares a small number of controlled
refinement branches without silently selecting one. Final structural
validation remains a user gate.

## Quick start

### Install

```bash
git clone https://github.com/vecchioni-lab/NASolve.git
cd NASolve
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[test]"
```

### Check the runtime

```bash
./nasolve check
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest
```

The tracked `./nasolve` launcher resolves the checkout even when invoked
through a symbolic link, uses `.venv/bin/python`, and prepends this checkout's
`src` directory only for its child process. It therefore works in a fresh
terminal without activation and does not depend on editable-install metadata.
Set `NASOLVE_PYTHON` to an explicit interpreter path only when intentionally
using a different environment. To use the shorter `nasolve` spelling from any
directory, symlink `./nasolve` into a directory that is already on `PATH`; the
link must be recreated if the checkout moves.

For example, if `$HOME/.local/bin` is already on `PATH`:

```bash
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/nasolve" "$HOME/.local/bin/nasolve"
```

`ln -s` refuses to replace an existing command. The examples in this README
use `./nasolve` and therefore assume the checkout root is the current directory.

The tracked launcher is for POSIX shells (macOS and Linux). On Windows, use the
generated virtual-environment entry point after installation:

```powershell
.\.venv\Scripts\nasolve.exe check
```

If an editable-install import needs to be bypassed on Windows, run from the
checkout with its `src` directory scoped to that PowerShell session:

```powershell
$env:PYTHONPATH = (Join-Path $PWD "src")
.\.venv\Scripts\python.exe -m nasolve check
```

`./nasolve check` discovers and validates Phenix, Coot, and NARestraints. If an
external tool is not found automatically, see [Configure external
tools](#configure-external-tools).

### Remember an active dataset or run

NASolve can remember a machine-local working target, so collaborators do not
need to change into a dataset directory or repeatedly paste a long run path:

```bash
./nasolve workspace use /absolute/path/to/dataset/AutoMR/run_004
./nasolve workspace status

./nasolve autorefine
./nasolve checkpoints list
./nasolve checkpoints use refine-001
./nasolve show
```

Explicit dataset/run arguments continue to work and always take precedence.
Creating a new AutoMR run makes that run active; one-off explicit paths passed
to later stage commands do not silently replace the active selection.
The workspace pointer is a small value in NASolve's user configuration; it
does not copy the dataset, start a background process, or consume persistent
RAM. Use `nasolve workspace clear` to remove it.

Workspace selection does not replace installation. The tracked launcher makes
activation optional for source-checkout use. See [Collaboration, workspaces, and portable
results](docs/collaboration.md) for artifact and Git guidance.

### Run AutoMR through AutoRefine

For a standard W/5W6W-frame dataset:

```bash
DATASET=/absolute/path/to/dataset
./nasolve automr "$DATASET" -W --pair F:D --execute
```

NASolve prints the new numbered run directory. Use that exact path for PostMR:

```bash
RUN=/absolute/path/to/dataset/AutoMR/run_001
./nasolve postmr "$RUN"
```

If PostMR reports an anomalous heavy-atom candidate, run the conditional
MR-SAD layer:

```bash
./nasolve autosol "$RUN"
```

AutoSol is not run for ordinary structures without a nucleotide-bound iodine,
bromine, or selenium atom.

Run the first five-cycle refinement and inspect its checkpoint history:

```bash
./nasolve autorefine "$RUN"
./nasolve checkpoints list "$RUN"
```

If a structurally sound result remains under review—for example, because a
small test set gives `Rwork >= Rfree`—run the bounded triage layer:

```bash
./nasolve refine-doctor "$RUN"
```

Refine Doctor never regenerates Free-R flags or changes the current checkpoint.
It audits the existing flags, runs only eligible sibling branches, stores any
measured anomalous `f''` benchmark, and prints an explicit recommendation for
inspection and optional selection. In an interactive terminal it asks whether
to make the recommendation current; answering `n` or `i` prints the exact
inspection and later-selection commands. A candidate can be opened without
changing the current pointer:

```bash
./nasolve show "$RUN" --checkpoint refine-005
```

A numerically successful result becomes current. Repeating `autorefine` then
starts from that improved model, while `--from` creates a deliberate branch:

```bash
./nasolve autorefine "$RUN"
./nasolve autorefine "$RUN" --from refine-001
```

Bookmark, select, or import a manually corrected model with:

```bash
./nasolve checkpoints add "$RUN" --name "clean first refine"
./nasolve checkpoints use "$RUN" refine-001
./nasolve checkpoints add "$RUN" \
  --model /absolute/path/to/manually_fixed.pdb \
  --name "fixed ligand"
```

For a nonstandard dataset containing one search-model PDB, omit the frame and
pair options:

```bash
./nasolve automr "$DATASET" --execute
```

Useful opt-in variants are:

```bash
# Mirror the selected D/L nucleic-acid search model before Phaser.
./nasolve automr "$DATASET" --mirror --execute

# Restrain only guessed base pairs containing a modified nucleotide.
./nasolve postmr "$RUN" --modified-pairs-only
```

### Inspect the prepared model in Coot

Open the most advanced completed stage of a run, or the highest numbered run in
a dataset, with:

```bash
./nasolve show "$RUN"
./nasolve show last "$DATASET"
./nasolve show "$RUN" --stage autosol
./nasolve show "$RUN" --checkpoint refine-005
```

NASolve chooses a stage-specific view: Phaser model/map for AutoMR, ReadySet
model plus its generated dictionary for PostMR, Phaser model plus AutoSol HA
sites and density-modified map for AutoSol, or the current refined model and
map coefficients for AutoRefine. Coot is launched from a stage-local working
directory so its histories, state files, backups, and downloads do not clutter
the repository.

The equivalent manual PostMR launch is:

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
5. freezes the effective inputs in a new, numbered run directory, including a
   checksummed standard-frame sequence snapshot when available;
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
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

If you prefer Conda, create an environment in the repository instead:

```bash
conda create -p .venv python=3.12
.venv/bin/python -m pip install -e .
```

For development and testing, install the test dependencies:

```bash
.venv/bin/python -m pip install -e ".[test]"
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest
```

Use `./nasolve` for source-checkout commands. Unlike the generated editable
entry point, the tracked launcher does not require virtual-environment
activation or a working `.pth` file. An optional symbolic link to `./nasolve`
may provide the shorter `nasolve` spelling from other directories on macOS and
Linux. Windows users should use `.\.venv\Scripts\nasolve.exe` or the documented
PowerShell `PYTHONPATH` fallback.

## Configure external tools

Begin with:

```bash
./nasolve check
```

NASolve checks the current `PATH`, any saved configuration, and standard
installation locations. On macOS it searches locations such as
`/Applications/phenix-*`; equivalent standard locations are checked on Linux
and Windows. A discovered installation is validated and remembered for later
runs.

If automatic discovery fails, configure Phenix once using its installation
directory, `phenix_env.sh`, or one of its executables:

```bash
./nasolve configure phenix /path/to/phenix/phenix_env.sh
```

The saved path is revalidated at startup, so moving or replacing Phenix does
not silently leave NASolve using a stale installation.

For a one-run override, place the global option before the subcommand:

```bash
./nasolve --phenix-root /path/to/phenix automr DATASET --execute
```

The environment variable `NASOLVE_PHENIX_ROOT` provides another override.

Coot is discovered independently from the current `PATH`, saved
configuration, and standard platform locations. Configure it explicitly when
needed with:

```bash
./nasolve configure coot /path/to/coot
```

## Repository layout

When NASolve is used from a source checkout, the repository is organized as:

```text
NASolve/
├── nasolve            source-checkout launcher
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

An approved standard-frame directory may supply `seq_base.txt`; AutoMR freezes
that sequence source into the run when present. A nonstandard run can instead
use complete sequences recorded in its frozen plan. AutoSol uses the selected
sequence only as phasing input, never for model building, because NASolve
disables every AutoBuild path.

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
./nasolve automr my_dataset -W --pair E:G
```

Run Phaser after the same guarded preflight:

```bash
./nasolve automr my_dataset -W --pair E:G --execute
```

Use the 3GBI frame with:

```bash
./nasolve automr my_dataset -3GBI --pair C:C --execute
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
./nasolve automr my_dataset -W --pair E:G --frames-dir /path/to/MR_frames
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
./nasolve automr my_dataset -W --pair E:G --allow-p1-standard --execute
```

This creates a prominent red flag in the run report. Other space groups, or a
real disagreement between the authoritative inputs, stop a standard run.
Nonstandard mode does not apply the H3/R3 gate.

## Quick start: nonstandard models

When a dataset contains exactly one top-level PDB and no standard frame is
requested, AutoMR uses nonstandard mode automatically:

```bash
./nasolve automr my_dataset
./nasolve automr my_dataset --execute
```

The first command performs preflight only. The second creates a new run and
executes Phaser.

Nonstandard models should already be suitable search models. AutoMR never
changes their sequence before MR; it freezes the requested chain sequences so
PostMR can mutate the accepted Phaser solution through Coot.

To solve the opposite D/L hand, mirror the selected search model before MR:

```bash
./nasolve automr my_dataset --mirror --execute
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
./nasolve automr my_dataset --execute
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
./nasolve postmr my_dataset/AutoMR/run_004
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
./nasolve postmr RUN --modified-pairs-only
```

PostMR runs the NARestraints guesser after Coot and backbone restoration with
noncanonical-pair guessing enabled. It keeps a guessed pair when either
partner has a noncanonical nucleotide residue code, writes no stacking
restraints, and records all guessed/retained pairs and warnings. A canonical
sequence change alone is not treated as a modification. If no modified pair is
found, the restraint step is a successful no-op and ReadySet still runs.
For a project that also supplies a scaffold EFF, the generated NARestraints
PHIL is authoritative: PostMR removes matching base-pair blocks from the EFF
and retains the non-overlapping project scaffold rather than failing or
double-restraining the pair.

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

## AutoRefine and checkpoints

`nasolve autorefine RUN` performs one five-macrocycle default refinement. It
uses the current checkpoint model, the original STARANISO observations and
unchanged Free-R flags, the ReadySet-generated ligand dictionary when present,
and the PostMR PHIL/EFF restraint stack. A validated AutoSol MTZ contributes
only its Hendrickson-Lattman coefficients; its HA coordinates never replace
known model atoms.

For ordinary data, AutoRefine selects mean observations. When PostMR records a
heavy atom, it requires `F(+),SIGF(+),F(-),SIGF(-)` and refines `f'` and `f''`
for exact model selections such as `chain B and resid 4 and name I`. The target
is explicitly left `auto`, including when experimental phases are supplied. If
validated AutoSol phases exist but the original data lack a complete anomalous
amplitude quartet, NASolve runs a mean-data, non-anomalous fallback, preserves
its outputs for inspection, and exits with a final error rather than silently
calling the intended anomalous refinement successful.

The default strategy refines reciprocal- and real-space coordinates, group
B-factors, and eligible occupancies; it disables rigid-body, individual-B,
TLS, NCS, reference-model, water-update, hydrogen-addition, and simulated
annealing paths. X-ray/stereochemistry and X-ray/ADP weights are optimized,
the scattering table is `n_gaussian`, and all available processors are used.

Phenix stdout and stderr are written only to the round-local log. The terminal
receives a start line and a compact final card containing initial/final Rwork
and Rfree, their gap, clashscore, bond/angle RMSDs, selected labels, phases,
and anomalous atom selections. Per-cycle R factors are retained in JSON and
`metrics.tsv`.

A result reaches `AUTOREFINE_READY` only when Phenix completed, the modified
residue/heavy-atom inventory survived, `Rwork < Rfree`, and `Rwork < 0.30`.
This is a numerical gate, not final structural approval. Review and failed
attempts remain visible without replacing the current model.

Every round is an immutable checkpoint node with a parent, recipe, input and
output checksums, statistics, compatibility state, and frozen observation,
phase, dictionary, and restraint references. Successful compatible results
become current automatically. `nasolve checkpoints add` can assign a bookmark
to the current node or import a manual Coot model as a review child;
`checkpoints use` selects a reusable branch deliberately. The model advances
between rounds, but map-coefficient/refinement MTZ outputs can never replace
the authoritative STARANISO observations or regenerate the Free-R set.

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
        │   ├── assessment.json
        │   └── seq_base.txt           # optional standard-frame snapshot
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
            │   ├── narestraints_Std_padd.phil
            │   ├── 5W6W_secondary_structure.eff
            │   ├── DE.cif
            │   ├── DF.cif
            │   └── 1AP.cif
            └── ReadySet/
                ├── ready_set.log
                ├── prepared_model.updated.pdb
                └── prepared_model.ligands.cif
        └── AutoRefine/
            ├── checkpoints.json
            └── round_001/
                ├── autorefine.params
                ├── phenix.refine.log
                ├── metrics.tsv
                ├── report.json
                ├── refined_001.pdb
                ├── refined_001.cif
                └── refined_001_map_coeffs.mtz
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
NARestraints, hydrogen-free ReadySet, guarded AutoSol, and checkpointed
five-cycle Phenix refinement. It does not yet:

- construct arbitrary modified residues without an approved template;
- perform mirror-side sequence changes through an unmirror/Coot/remirror cycle;
- prepare the 3GBI frame, whose standard-site manifest is not yet defined;
- choose or compare advanced refinement recipes automatically;
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
./nasolve check
```

For an individual run, inspect `automr.log`, `report.json`, and
`Phaser/phaser.log`. When reporting a problem, include the command, NASolve and
Phenix versions, terminal error, and the relevant log excerpt. Please do not
upload unpublished diffraction data or coordinates to a public issue unless
you intend to make them public.

Issues may be reported at
[github.com/vecchioni-lab/NASolve/issues](https://github.com/vecchioni-lab/NASolve/issues).
