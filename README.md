# NASolve

NASolve is a command-line workflow for nucleic-acid molecular replacement. It
organizes autoPROC/STARANISO datasets, selects or checks an MR model, runs
Phenix Phaser with reproducible settings, preserves modified residues and
other heteroatoms, and classifies the result by TFZ.

The present release provides the **AutoMR** layer. Later NASolve layers will
handle model mutation, nucleic-acid restraint generation, ReadySet, refinement,
and final validation. Those later operations are not performed by the current
command.

## What AutoMR does

For each dataset, AutoMR:

1. locates the reflection MTZ, `Data_1*.cif`, and `summary.html` files;
2. chooses a standard 5W6W/3GBI search model or validates a user-supplied PDB;
3. checks the model, including modified nucleotides written as `HETATM`;
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
  `phenix.mtz.dump`, `phenix.ready_set`, and `phenix.refine`
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

## Configure Phenix

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

## Choosing a run type

| | Standard frame | Nonstandard model |
| --- | --- | --- |
| Search model | Selected from `MR_frames/5W6W` or `MR_frames/3GBI` | Supplied in the dataset |
| Required request | Frame plus ordered pair | One PDB, found or named |
| Space-group rule | H3/R3; P1 only through the explicit shunt | No standard-frame symmetry gate |
| Standard-site change | Exact catalogue pair or recorded fallback mutation | Use explicit mutation sites |
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

Nonstandard models should already be suitable search models. NASolve currently
checks and copies the model but does not yet remodel it before MR.

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

A nonstandard input file may name a dataset-relative model and record later
sequence or site-specific changes:

```ini
[automr]
mode = nonstandard
model = search_model.pdb

[sequences]
A = GCGTACGT
B = ACGTACGC

[mutations]
A:8 = 5IU
B:8 = DT
```

Sequence chain names must occur in the model, and each sequence length must
match the model's polymer-residue count for that chain. Mutation sites use
`CHAIN:RESID` and must exist in the model. Modified nucleotides written as
`HETATM` count toward the chain length when their residue code occurs in the
NARestraints library.

Sequence and mutation sections are validated and preserved in the current
release, but they are **not yet applied to the Phaser solution**. They are the
input contract for the forthcoming post-MR mutation layer.

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
| `B` | `IGU` |  |  |
| `P` | `DP` |  |  |
| `Z` | `DZ` |  |  |
| `I` | `DI` |  |  |
| `X` | `DX` |  |  |
| `K` | `CGY` |  |  |

For example, `F` selects `DF`. A different known ligand such as `A1AAZ` must
be written explicitly.

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
        │   ├── input_model.pdb
        │   └── assessment.json
        └── Phaser/
            ├── phaser.eff
            ├── phaser.log
            ├── PHASER.1.pdb
            ├── PHASER.1.mtz
            ├── mr_solution.pdb
            └── mr_solution.mtz
```

`Model/input_model.pdb` is a checksum-verified copy of the selected search
model. Heteroatoms are preserved byte-for-byte during preflight. Phaser is run
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

AutoMR currently supports PDB search models and Phenix Phaser MR_AUTO. It does
not yet:

- apply full sequences or mutations to the MR solution;
- invoke Coot;
- generate NARestraints restraints;
- run `phenix.ready_set` or `phenix.refine`;
- apply the final H3/R3 notation patch; or
- search multiple catalogue models automatically.

These operations are deliberately kept behind later validation gates rather
than being implied by an MR success. Always inspect the molecular-replacement
solution and electron density before treating it as a solved structure.

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
