# NASolve

NASolve is a guarded command-line workflow for nucleic-acid molecular
replacement and post-MR model preparation. It discovers autoPROC/STARANISO
inputs, selects and validates an approved search model, runs Phenix Phaser with
reproducible settings, preserves modified residues and other heteroatoms, and
classifies the solution by TFZ.

The current workflow provides **AutoMR**, **PostMR**, a conditional
**AutoSol** branch, checkpointed **AutoRefine**, bounded **Refine Doctor**
triage, and sequential campaign execution from frozen plans with per-dataset
review isolation. PostMR constructs
supported modified nucleotides through Coot, restores trusted parent
coordinates, can apply complete chain sequences, generates either the 5W6W
restraint stack or modification-scoped pair restraints, supplies curated,
supported local or configured-Phenix CCD dictionaries, and runs ReadySet without
hydrogens. When PostMR finds iodine, bromine, or selenium in a nucleotide,
AutoSol performs guarded MR-SAD phasing
and verifies a corresponding anomalous site. AutoRefine runs Phenix quietly,
surfaces the crystallographic statistics normally shown by the GUI, and
preserves successful, review, failed, and manually imported models as
branchable checkpoints. Refine Doctor audits the frozen Free-R set, preserves
an anomalous-strength benchmark, and compares a small number of controlled
refinement branches without silently selecting one. Final structural
validation remains a user gate.

CIF Doctor adds offline, read-only dictionary assessment and report-only PostMR
receipts before mutations and on both sides of ReadySet. To inspect an existing
run without changing it, use `./nasolve cif-doctor assess --run RUN --json`.
[The CIF Doctor guide](docs/cif-doctor.md) describes the implemented checks and
explicit source-preserving preparation recipes.
The [human/manuscript overview](docs/cif-doctor-human-overview.md) explains the
algorithm, tools and pipeline placement and supplies an editable figure.

The current diagnostic trial has reproduced coordinate damage from legacy
parent restoration for some modified bases. A separate graph-selected fragment
candidate and source-recovered DF definitions pass native mechanics, with
formal-charge readback unavailable. A separate fixed-definition geometry trial
reached its iteration limit. Native PDB readback preserves atom/component
identities and exposes distance-dependent hydrogen-bond additions. Achieved
geometry and scientific approval remain under review.
A separate explicit NARestraints membership diagnostic now compiles declared
pairs/stacks and passes both installed native membership checks at two saved
coordinate sets. Cedar 22 now provides a separate bounded geometry trial under
that verified policy, with strict manager matching, stopping/gradient evidence
and native PDB readback. The returned trial passes all 17 native mechanics
checks, decreases the objective and stops with a line-search error. Geometry
qualification remains open and ordinary PostMR is unchanged.
A separate Cedar 23 diagnostic now checks native gradients against finite
energy differences at the saved endpoints and repeats dictionary assessment.
The returned audit localizes a stable sampled gradient mismatch to native
parallelity terms in both coordinate cases. An independent plane calculation
points to gradient accumulation. Returned Cedar 24 confirms that defect in
the installed native path: individual plane gradients pass the sampled checks,
while accumulation omits second-plane contributions in both saved cases and
tilted controls. Restoring those contributions in the saved numerical data
explains all earlier sampled mismatches. Cedar 25 adds an explicit NASolve-local
correction that replaces only the accumulated plane gradient with complete
individual-restraint sums. Its separate audit freshly checks the fixed native
objective at the initial coordinates and both saved endpoints. The returned
audit passes both endpoints but retains six failed directions at the initial
coordinates. An independent normal-orientation sign model reproduces the
remaining gradient. Cedar 26 therefore uses each plane's first-plane derivative
in both native orders, with fresh per-plane, rotated-control and full-objective
checks. Returned Cedar 26 passes all 504 global/category and 1,080 corrected
per-plane directions, including rotated controls, with unchanged native energy.
Cedar 27 now supplies a separate bounded geometry trial from the original
initial coordinates, using that qualified correction. Exact source/snapshot
gates, fresh endpoint derivatives and native PDB readback accompany the trial.
Returned Cedar 27 passes all 17 native mechanics checks and all 336 sampled
endpoint derivative directions. The fixed objective falls 28.72%, but the
trial reaches its 1,000-iteration limit with the native criterion false. A
bounded continuation is supplied by Cedar 28, using the saved full-precision
endpoint and a fresh optimizer with the same policy and endpoint checks.
Returned Cedar 28 passes the same 17 mechanics and 336 sampled derivative
checks. Its target falls another 3.64%, with stopping still at the iteration
limit after 2,000 cumulative iterations. Three distance and ten angle outliers
persist. Cedar 29 supplies a separate graph-selected base-orientation audit:
temporary rotations measure category responses and numerical slopes under
the same fixed objective. Source/endpoint preflight, periodic controls and
explicit internal-angle context accompany the scan. Returned Cedar 29 passes
all 96 sampled rotation directions; every coarse-grid minimum is the starting
angle. This does not establish a local/global minimum. Cedar 30 prepares a
separate source-graph numerical dictionary candidate for the retained DP
angle/plane conflict, with exact chemical comparisons. Its return stops in
the installed eLBOW input parser before producing a candidate: external
coordinate-tag case was lost during export. Cedar 31 restores canonical tag
spelling and adds an explicit PDU public control. PDU source graph and existing
NARestraints pairing/stacking compiler checks pass offline. Returned Cedar 31
separates DP missing-alias metadata from a PDU optimizer/restart crash; neither
produces a dictionary. Cedar 32 adds a general missing-alias export and an
explicit installed-source/read-only input diagnostic. Its return passes the
PDU reader and exposes DP's broader dictionary-dialect mismatch. Cedar 33
adds a checked consumer projection and an opt-in bounded single-block trial,
with installed option/source proof and explicit nonconvergence evidence.
Returned Cedar 33 passes both input readers. DP stops in preparatory chirality
handling before optimization; PDU writes a nonconverged dictionary. PDU's three
signed sugar volumes preserve source-coordinate handedness, but its R/S labels
are omitted. Cedar 34 separately audits these stereo boundaries through saved
candidate comparisons and bounded installed-reader controls, without generation.
Returned Cedar 34 reproduces DP's unknown-marker constructor failure and passes
PDU's known-marker control. Its captured code also shows local chiral-template
minimization inside the constructor; no full dictionary trial ran. Cedar 35
preserves the source dictionary's reader dialect and checks native parsed
inventory before another generation. Its return stops in the temporary graph
preflight before native parsing. Cedar 36 resolves the tool-owned temporary
directory and retries the same audit while preserving that failure. Native
parsing now completes for both sources. PDU passes raw route/inventory checks;
DP preserves names, elements, coordinates and signed markers but loses double
orders and declared charges. Cedar 37 translates monomer order tokens and
separately tests explicit source-charge population on a temporary parsed
component, retaining the raw reader evidence. Returned Cedar 37 preserves all
declared orders; its isolated charge control passes for DP and leaves PDU
unchanged. Cedar 38 audits graph-selected triple bonds in public PDU and 5PC
controls: installed monomer lookup, explicit installed-CIF replay and the saved
PDU candidate are compared at fixed isolated source-seed coordinates. Active
length/linearity targets, ESDs, membership and linear-axis torsions are recorded.
5PC's two NARestraints records remain ambiguous; no role record is selected.
Returned Cedar 38 finds no component through either default monomer lookup;
those models stop on unknown energy types. The supplied PDU candidate loads
with active 1.174 Å / 180° terms and six linear-axis torsion reviews at fixed
source-seed coordinates. Cedar 39 separately inventories installed CCD chemistry
and direct/canonical monomer lookups, comparing declarations and SMILES text
with the public controls. It records route-helper source without running
ReadySet. No experimental model, target, generation or optimization is changed.
NARestraints policy and production defaults stay fixed; geometry, convergence
and adoption remain open.
See the [current handoff](docs/development-handoff.md) for the exact scope.

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

Checkpoint listing is read-only. Before the registry has been initialized, it
shows the validated PostMR root without creating files. AutoRefine prints an
exact `show RUN --checkpoint ID` command when the same view resolver used by
`show` can resolve that checkpoint's model and maps, so you can inspect an
unselected result without changing the current checkpoint. If resolution fails,
it reports the reason and directs you to the log and report instead.

If a structurally sound result remains under review—for example, because a
small test set gives `Rwork >= Rfree`—run the bounded triage layer:

```bash
./nasolve refine-doctor "$RUN"
```

Refine Doctor never regenerates Free-R flags. Its engine preserves the current
checkpoint; the interactive CLI changes it only when you explicitly select one.
It requires an available, valid Free-R audit, tries eligible sibling branches
in declared order, and stops at the first numerical pass or a technical error.
The ordinary mean-data path includes grouped-B, eligible individual-ADP,
coordinate-only and B-only recipes. Anomalous data use explicit calculated
scattering values and an optional f''-only trial; the recorded AutoSol
wavelength is required. Existing anomalous benchmarks remain in the report.
The default limit is five trials of three macrocycles each; `--max-trials` and
`--cycles` each accept 1-10.

An unresolved inversion remains `REFINE_DOCTOR_REVIEW` (exit 2). Doctor prints
the lowest-Rfree usable candidate for inspection without declaring statistical
superiority or offering to select an unpassed candidate. A numerical pass may
be selected through the interactive `[y/N/i]` prompt. Type `i` and press Enter
to open the recommended model and maps in Coot. The terminal asks again while
Coot remains open: return to enter `y` to select or `n` (or just Enter) to finish
with the current checkpoint unchanged. An inspection-launch error also returns
to the prompt. Every report records attempted/skipped recipes and stopping
reasons. The durable Doctor contract is described in
[the architecture](docs/architecture.md), with campaign-level follow-up in
[the campaign design](docs/campaigns.md). A candidate can be opened without
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

Open the selected current checkpoint in the active workspace, an explicit run,
or the highest numbered run in a dataset:

```bash
./nasolve show
./nasolve show "$RUN"
./nasolve show last "$DATASET"
./nasolve show "$RUN" --stage autosol
./nasolve show "$RUN" --checkpoint refine-005
```

The current checkpoint wins over newer unselected refinement attempts. Without
a checkpoint registry, NASolve chooses an accepted AutoSol view with a usable
density map, completed PostMR, or Phaser. Explicit `--stage` and `--checkpoint`
options leave the selection unchanged. The console identifies the run, model,
checkpoint, and map source.

After `./nasolve campaign run ROOT --dataset DATASET` reaches a viewable stage,
that **single-dataset** run becomes the machine-local active workspace view.
A following `./nasolve show` therefore opens its current checkpoint without
recalling any path. `workspace use DATASET` alone also permits bare
`./nasolve show` (newest numbered readable run in that dataset). For batch
campaigns, failed/unviewable stages, or `--no-activate`, the prior active
workspace is preserved. This convenience does not select/approve a new
scientific checkpoint or change Coot windows already open.

AutoMR shows the Phaser model and map. PostMR shows the ReadySet model and its
ligand dictionaries, using accepted AutoSol density when available and the
Phaser map otherwise. AutoSol shows the prepared ReadySet model with its
dictionaries, the density-modified map, and a separate heavy-atom overlay.
AutoRefine shows the selected model, its map coefficients, and frozen
dictionaries. An imported manual checkpoint can inherit an ancestor's map only
when its observation data match; the output labels this map as not recalculated
for the manual model. Missing or corrupt declared maps produce an error.

If the selected MTZ contains `ANOM` and `PHANOM`, `show` also opens a named
**Anomalous difference** map at **3 sigma**. If Phenix wrote separate map and
refinement MTZ files, it also checks the refinement MTZ recorded for that same
checkpoint. Availability depends on the columns, so fixed-scattering and
refined-anomalous results both work; a mean-only result without this pair opens
its usual maps. This also works from Refine Doctor's `i` inspection option.
The usual maps and their refinement/scroll controls are preserved. Coot's log
records whether the extra map was loaded, already open, absent, or failed.

Coot histories and backups stay under `RUN/CootGUI/STAGE/`, with a separate
checkpoint subdirectory when one is selected.

A manual PostMR launch using the MR map is:

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

## Backbone and terminal-phosphate chemistry

NASolve treats ordinary DNA/RNA-like backbones as standard phosphodiesters. A requested 5'-terminal phosphate is a complete P/OP1/OP2/OP3 group; PostMR preserves a complete group, completes a missing OP3 when P/OP1/OP2 are present, or seeds the whole group from O5'-C5' when the phosphate is absent. New input files may use `five_prime_phosphate_sites`; the historical `allow_op3_sites` name remains readable for old frozen runs.

Unsupported backbone chemistry is never guessed. Mark a site explicitly in `nasolve.txt` and opt into the experimental passthrough only when you intend to inspect the result yourself:

```ini
[automr]
allow_unreviewed_backbone = true

[backbones]
A:12 = experimental_passthrough
```

Passthrough suppresses only NASolve's standard phosphate-linkage rules at the listed site. It does not disable pairing/stacking elsewhere and does not invent custom bonds. The run stays visibly unreviewed. After a successful interactive AutoRefine, NASolve immediately offers to show the flagged result in Coot and then separately asks whether the chemistry was reviewed. You can defer that inspection and later run `./nasolve backbone-review RUN`. Confirmation records a portable reference plus the inspected model hash but never erases passthrough provenance.

Reviewed arbitrary GNA/PNA/TNA linkage recipes and 3'-terminal phosphate construction are intentionally deferred until we have real validated examples. If you need one, contact the developers with the intended atom connections and deletions so it can become a reviewed recipe rather than a guess. See [Backbone chemistry](docs/backbone-chemistry.md), the [machine-readable schema](docs/backbone-chemistry.schema.json), and the [human recipe example](docs/backbone-recipe-example.txt).

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
| Search model | Catalogue by default; explicit dataset/frame-catalogue override allowed | Supplied in the dataset |
| Required request | Frame plus ordered pair | One PDB, found or named |
| Space-group rule | H3/R3; P1 only through the explicit shunt | No standard-frame symmetry gate |
| Standard-site change | Exact catalogue pair, fallback mutation, or conservative target application for a forced model | Use explicit mutation sites |
| Complete sequence | Optional explicit reference/thread/dataset target | Chain-labelled sequence file or inline chains |
| Optional mirror | `--mirror` on the selected/forced standard model | `--mirror` on the selected dataset model |
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

For a deliberate validation or unusual dataset, force one exact PDB while
retaining the standard frame's symmetry, chemistry, sequence-family and PostMR
rules:

```bash
./nasolve automr my_dataset -W --pair A:T \
  --model 5W6W_noPO4.pdb --execute
```

In standard mode the selector is resolved only from the dataset directory and
the selected frame catalogue. If both contain the same selector NASolve stops
as ambiguous; escaping/absolute paths are rejected. A forced model is never
declared an exact pair match from its filename. NASolve records the provider and
model checksum, verifies required standard PostMR sites such as W A:12/B:4, and
lets the ordinary PostMR target decide what identity changes are actually needed.
The W catalogue remains the source of frame context such as `seq_base.txt`.

The same selector can be written in `nasolve.txt`:

```ini
[automr]
mode = standard
frame = W
pair = A:T
model = 5W6W_noPO4.pdb
```

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

## Optional sequence-family reference

A fresh standalone run can explicitly select the reviewed W sequence baseline
with `[automr] sequence_reference = w-metal-scaffold`. This does not change W's
default recipe, imply metal-pair chemistry, or edit the MR search coordinates.
It freezes the complete intended residue target for PostMR, with dataset
sequence and explicit site-chemistry overrides retained. The same field accepts
an explicit dataset-relative reference JSON. See
[sequence-family target assembly](docs/sequence-family-targets.md) for the
schema, precedence and validation boundary. Campaign planning accepts the same
explicit per-dataset selector and freezes the exact reference bytes into the
campaign resource store before execution. A root `nasolve-campaign.toml` can
also bind datasets explicitly into named W-family sequence threads whose shared
sequence/site overlays are inherited before dataset-specific overrides. Thread
membership changes target intent only: it does not select or reuse MR models.

A sequence-family target can be combined with an explicit standard-model
provider. This is the intended validation path for the tracked original
`5W6W_noPO4.pdb`: the original scaffold coordinates enter Phaser unchanged,
while the frozen W-family target records the post-MR sequence delta and the W
recipe independently retains D:1 terminal-phosphate intent.

An explicitly named model may also declare a stable provider-side family with
`model_family = FAMILY_ID` in `[automr]`. The declaration is bound to that
exact `model = ...` selector and is copied into provider provenance; it cannot
silently follow a different command-line model override. NASolve does not infer
this value from the frame, filename, sequence thread, residue similarity, or
target reference.

When a complete explicit residue target is available, AutoMR also freezes
`Model/search_model_comparison.json`. This descriptive record captures the
literal model chain/residue inventory, missing or unexpected target sites, exact
identity mismatches, and the target layer responsible for each mismatch.
`expected_postmr_correction = true` means only that the frozen target differs
at that site; the comparison does not claim that a mutation route, dictionary,
MR-model compatibility rule, or cross-dataset reuse policy has been validated.
Runs without a complete explicit target do not invent this comparison from
filenames or unlabeled frame sequence files.

Every fresh AutoMR run also freezes
`Model/model_compatibility_facts.json`. This fact sheet joins existing provider,
model, target, symmetry and chemistry provenance into named dimensions such as
frame identity, candidate chain/site inventory, residue identity, mirror-transform
state, terminal/backbone intent and symmetry/copy number. Relations are
descriptive (`SAME`, `DIFFERENT`, `PARTIAL`, `UNKNOWN`) and are never
collapsed into a score or overall verdict. When both an explicit provider
`model_family` and a complete target reference are present, the construct-family
dimension reports their literal identifier relation as `SAME` or `DIFFERENT`;
missing declarations remain `UNKNOWN`. This is still not a reuse decision.
Absolute D/L chirality is currently unknown even when `mirror` is false;
NASolve records only whether it applied the explicit mirror transform. See
[model compatibility facts](docs/model-compatibility-facts.md).

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
`C38`), builds the component from its dictionary, overlaps it, and
replaces the parent. NASolve then restores the
coordinates, occupancies, and B factors of every atom shared with the parent.
This preserves the canonical sugar and phosphate exactly while retaining only
the genuinely modified atoms from the dictionary. Hydrogens are removed.
Unsupported construction stops and asks the user for a model. Full-sequence
mutation uses the same Coot base-mutation path. NASolve restores the original
sugar and phosphate coordinates after every ordinary base change, so a whole
sequence application cannot curl or rotate the inherited backbone.

Modified-residue mutations can also use a local component dictionary without
adding a new curated registry entry. NASolve requires one unambiguous
NARestraints residue record, a supported construction parent derived from its
`Sugar Type` and recognized `Source sheet` (falling back to `Base Analog`),
and a matching component dictionary. A local `ligands/CODE.cif` takes
precedence; otherwise Cedar resolves a unique CCD source in the configured
Phenix installation. Symlink aliases of one file are deduplicated; distinct
competing files remain an error. The included `OHU.cif` enables DNA `D:OHU`
preparation; OHU uses `DT` as its Coot construction parent according to the
NARestraints mapping. Curated overrides remain authoritative, and their
dictionaries are retained even when the residue needs no mutation.

This fallback does not download dictionaries or automatically parameterize every
arbitrary component. Raw CCD graphs require usable numerical restraints from
ReadySet; there is no automatic alternate-generator fallback. Generic dictionary
validation checks the component identity; it does not infer arbitrary atom mappings or
establish that every component topology is correct. New chemistry still needs
model inspection, and an absent or ambiguous definition gives a specific
preparation error. Resolution follows mutation actions; unchanged non-curated
residues are not all acquired automatically. The
[component preparation contract](docs/modified-component-preparation.md)
separates current behavior from the fresh full-auto acceptance target.

PostMR checks nucleotide phosphates before generating restraints and again
after ReadySet. It removes `OP3` (or legacy `O3P`) only where an incoming
`O3'–P` backbone link confirms an internal phosphate. **OP3/O3P is strictly
user-opt-in, even at a terminus.** An unexpected unlinked OP3 stops preparation
for review rather than being retained automatically or blindly deleted. Numbering gaps and insertion codes do not define
connectivity; chain and `TER` boundaries are respected. Remaining phosphate
atoms, broad bond/angle plausibility, and reference-known backbone links are
checked. Ambiguous alternatives or broken geometry stop preparation with a
specific error. This is a connectivity repair, not a coordinate minimization.

Selecting the standard **W/5W6W recipe** (`-W`, `frame = W`, or
`frame = 5W6W`) explicitly selects its designed **5-prime phosphate at D:1**.
The versioned `5w6w` recipe card contains:

```toml
[chemistry]
terminal_phosphate_sites = ["D:1"]
```

The source and effective sites are printed by AutoMR, `preset check`, and
campaign plan/status. This is recipe-declared chemistry, not an automatic
exception for every terminal residue or permission inferred from coordinates.
Other frames/nonstandard models do not inherit W's sites. A custom campaign
recipe supplies its own explicit chemistry list; omitting the table means no
recipe-authorized phosphates.

An explicit site list may be supplied in `nasolve.txt` with the preferred
`five_prime_phosphate_sites` name; the historical `allow_op3_sites` name remains
readable for old inputs and frozen runs. This is a site-scoped chemistry
declaration, not a boolean. An explicitly supplied list **replaces** the recipe
list; include D:1 when also requesting another site. An explicitly empty list
suppresses recipe phosphate permissions for that variant without editing the raw
coordinates.

At a requested 5-prime terminal site, PostMR preserves a complete valid
P/OP1/OP2/OP3 group, completes a P/OP1/OP2 group that lacks OP3, or constructs a
wholly missing terminal group from the local sugar frame. Ambiguous partial
groups, incoming/internal O3'-P conflicts, cyclic-phosphate-like geometry, and
other contradictory states still fail closed. See the active
[backbone chemistry contract](docs/backbone-chemistry.md). The earlier 1AP
integration diary is retained only as a
[historical record](docs/history/1ap-phosphate-integration.md).

Both checks are recorded under `phosphate_cleanup` in the PostMR report. Raw
Coot and ReadySet outputs remain available; the cleaned ReadySet copy is named
`prepared_model.phosphate_checked.pdb`. Existing runs are unchanged. A model
already refined with an extra OP3 should be rebuilt in a new run and refined
again because removing the atom alone does not reverse earlier distortion.

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
For modified W pairs, PostMR replaces incompatible template Saenger blocks
with explicit NARestraints pair restraints using the reviewed atom-role
mapping. Unaffected scaffold pairs and the normal stacking source are retained.

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

NASolve's bundled registry contains source adaptations, construction recipes
and identity bridges; membership does not mean the supplier CIF was defective.
The [source audit](docs/modified-component-preparation.md#bundled-ligand-audit-2026-10-09)
records their separate roles and the still-unresolved DE numerical geometry.
The `E` token resolves to `DE`; legacy `E` reports frozen
as `8RO` are migrated to `DE` because official CCD `8RO` is a different
compound with an unwanted sulfur-ring topology. `DF` is tied explicitly to
CCD `A1AAZ`. The topology checks require `DE C4-S4` without `N3-S4`,
`DF C2-S1` without `N3-S1`, and `S6G C6-S6` without `N1-S6`. ReadySet is launched in its own directory with
`hydrogens=False` and its output is rejected if hydrogens appear or atom counts
change unexpectedly.

The curated CIF and the coordinate edit solve different problems. Coot creates
and places the modified residue; the CIF defines its chemical topology and
ideal geometry. Although `phenix.refine` can accept a model plus `1AP.cif`
directly, NASolve still uses ReadySet as the uniform final preparation and
validation gate. ReadySet is not trusted to invent the modification, and it
does not replace the NARestraints inter-residue geometry.

The legacy NARestraints `DF` canonical `O2` mapping names the nonexistent
atom `S2`. PostMR corrects this to `S1` only in memory for the current builder
call, records the correction in `report.json`, and never edits the installed
NARestraints workbook.

The `Q` token resolves to official CCD `S6G` and uses `DG` as its canonical
construction parent. The legacy NARestraints `C5` mapping is `C5 `;
PostMR trims that exact trailing space in the same process-local adapter.

After ReadySet, PostMR scans nucleotide-like residues for configurable
anomalous elements. The initial trigger set is iodine, bromine, and selenium;
it is element-driven rather than restricted to known residue codes. Element
columns are preferred, with atom-name inference recorded when required. The
candidate sites and whether AutoSol is required are written to `report.json`.

## AutoRefine and checkpoints

`nasolve autorefine RUN` performs one five-macrocycle default refinement. It
uses the current checkpoint model, the original STARANISO observations and
unchanged Free-R flags, the frozen effective PostMR dictionaries, and the
PostMR PHIL/EFF restraint stack. Explicit parameterized component inputs take
precedence over generated copies; graph-only inputs defer to usable generated
numerical definitions. A validated AutoSol MTZ contributes
only its Hendrickson-Lattman coefficients; its HA coordinates never replace
known model atoms.

Reflection-array binding is version-gated. Phenix 1.20.x receives explicit
observation, Free-R, and optional experimental-phase file/label command
selectors without the unsupported Data Manager block. Phenix 2.1.x and 2.2.x
receive the same explicit selectors plus file-scoped Data Manager definitions, which
disambiguate MTZ files containing multiple plausible arrays. NASolve records
the discovered version and selected mode in every refinement checkpoint and
report. Unknown, malformed, or unvalidated version families stop before a
refinement directory is allocated rather than guessing a weaker policy.

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
implements W/5W6W sites, canonical Coot mutations, curated overrides, supported
local/configured-Phenix dictionary mutations, complete sequence application,
modification-scoped NARestraints, phosphate connectivity checks, and hydrogen-free ReadySet.
Guarded AutoSol, checkpointed five-cycle Phenix refinement, bounded Refine
Doctor comparisons, and views of the current checkpoint are available. The
[historical DOHU validation record](docs/history/validation-dohu.md)
documents an earlier complete Phenix 2.2.1 execution and user inspection.
Current validation state is summarized in
[`docs/development-handoff.md`](docs/development-handoff.md). NASolve does not yet:

- fetch missing ligand dictionaries over the network, construct arbitrary
  modified residues without a supported mapping and source, or complete the
  generic generation/linkage workflow from every valid code automatically;
- accept coordinate mmCIF search models or explicitly trust a model without a
  sequence file in prepared-nonstandard campaigns; these are
  [proposed input modes](docs/architecture.md#proposed-model-input-contract);
- perform mirror-side sequence changes through an unmirror/Coot/remirror cycle;
- prepare the 3GBI frame, whose standard-site manifest is not yet defined;
- search unbounded refinement recipes or run several campaign jobs concurrently;
- apply the final H3/R3 notation patch;
- perform construct/ASU registration or registration-aware recut rescue; or
- search multiple catalogue/dataset models automatically or reuse solved sibling
  structures automatically.

These capabilities are outside the current runtime. Always inspect the
molecular-replacement solution and electron density before treating it as a
solved structure.

## Plan and run a dataset campaign

Validate the built-in project preset and freeze the published example inputs
without launching scientific stages:

```bash
./nasolve preset check 5w6w
./nasolve campaign plan examples --dataset DOHU --dataset QiC_120325_0513
./nasolve campaign status examples
```

The planner records valid and blocked datasets independently, input checksums,
resolved configuration, and portable copies of selected models and preset
resources under `NASolveCampaign/`. New plans use schema 2 and may contain
standard W members, prepared nonstandard PDB+sequence members, or both.
Existing schema-1 W plans remain executable. Status checks detect changed or
missing frozen inputs. Existing dataset files, runs and checkpoint selections
are preserved. A saved plan is immutable; use `status` rather than planning
over it.

A prepared nonstandard member explicitly declares `mode = nonstandard`, one
dataset-relative/discovered PDB and a complete chain-labelled target (inline
`[sequences]` or `sequence_file`). NASolve freezes the model bytes, raw
sequence source and parsed target separately. Nonstandard members do not inherit
the W frame/pair or D:1 chemistry merely because the selected campaign preset
also supports W datasets.

`DISCOVERED` means input and model selection passed; the scientific preflight
and execution gates still remain. The sequential executor runs those existing
engines and saves progress separately from the immutable plan. For a cautious
first check, you can stop one dataset after PostMR and then resume it:

```bash
./nasolve campaign run examples --dataset DOHU --through postmr
./nasolve campaign status examples
./nasolve campaign run examples --dataset DOHU
```

The second `run` continues the same campaign-owned numbered run after verifying
its completed stages. It does not repeat MR or PostMR. A plain
`campaign run ROOT` otherwise defaults through AutoRefine and can advance all
eligible datasets unattended through the current fixed stage order.

A scientific review or technical failure stops only that dataset while other
selected datasets continue. AutoSol is conditional: when PostMR finds no
supported anomalous candidate, the campaign records an accepted `SKIPPED`
AutoSol stage and does not launch `phenix.autosol`; when anomalous evidence
requires it, AutoSol runs under the frozen policy. Under guarded policy,
unaccepted phasing stops for inspection. Numerical refinement success retains the selected checkpoint and
still requires model/map inspection.

The guarded sequential path has been exercised end-to-end with real Phenix/Coot.
A separate fresh [full-auto campaign](docs/full-auto-patch-handoff.md) reached
four numerical SOLVED results, including a provisionally selected Doctor
recommendation; all retain model/map inspection requirements.

A campaign refinement-review case can be continued explicitly through the
campaign-owned bounded Refine Doctor stage:

```bash
./nasolve campaign run CAMPAIGN_ROOT --dataset DATASET --through refine-doctor
```

Under guarded policy, Doctor preserves campaign provenance and leaves its
recommendation unselected. An explicitly frozen
[full-auto recipe](docs/campaign-full-auto.md) may run bounded Doctor and
provisionally select its verified passing recommendation. This does not record
user approval; inspect the model/maps and retained decision history.

Use `campaign pause examples` from another terminal to stop after the active
stage finishes. Keep the execution terminal open; this first executor runs in
the foreground on macOS/Linux. See [campaign execution](docs/campaign-execution.md)
for interruption handling, explicit retries and live-test commands, and
[campaign planning](docs/campaign-planning.md) for preset and input integrity.

## Project presets and model providers

The versioned `5w6w` planning preset describes the standard W workflow.
Prepared nonstandard members explicitly override the W AutoMR layer while using
the selected preset's bounded shared stage policies. For a geometry-diverse real
campaign, use a small project-local preset with a neutral project ID so the
human-facing campaign identity reflects the project even though the current
stage-policy schema remains conservative.

The current preset freezes the standard W AutoMR defaults, PostMR policy,
conditional AutoSol policy, AutoRefine recipe/cycle count, resources, and
declared chemistry. Prepared nonstandard members supply their own model/sequence
request while retaining the selected preset's bounded shared stage policy.

NASolve does **not** invoke AlphaFold or another model-generation service.
Supply the intended search-model PDB explicitly when using a nonstandard model.
Project-specific scientific choices remain frozen in versioned inputs while the
pipeline retains common validation, provenance, non-overwrite behavior, and
external-tool isolation. Numerical acceptance and model/map inspection remain
separate outcomes.

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
