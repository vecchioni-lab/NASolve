# NASolve campaigns and project presets

Status: architecture and roadmap. Versioned 5W6W presets, immutable campaign
planning/status, and one sequential resumable candidate path are implemented;
see [campaign planning](campaign-planning.md) and
[campaign execution](campaign-execution.md) for available commands and limits.
The broader candidate-selection, Doctor, approval, reporting and deposition
commands described below remain planned.

## Purpose

NASolve campaigns apply a versioned project preset to a pre-curated collection
of crystallographic datasets. A campaign should run each dataset as far as its
scientific evidence permits, preserve every decision and branch, and collect
exceptions for later inspection without stopping unrelated datasets.

The campaign layer orchestrates the existing guarded stage engines. It must not
reimplement Phaser, Coot, ReadySet, AutoSol, Phenix refinement, NARestraints,
or their safety checks.

The first supported production preset is 5W6W. The architecture must also
support later project presets with different MR catalogues, sequences,
metalation strategies, restraint policies, AutoSol protocols, refinement
recipes, or model providers such as AlphaFold.

## Core principles

1. **Continue globally, pause locally.** A blocked or ambiguous dataset enters
   an inspection queue while the rest of the campaign continues.
2. **Preserve scientific gates.** Campaign mode may choose among approved
   recovery branches, but it may not bypass failed preflights, corrupt Free-R
   flags, unknown chemistry, incompatible models, or other hard stage gates.
3. **Keep provenance immutable.** Every input, preset resource, command,
   result, branch, selection, warning, and user decision remains attributable.
4. **Resume rather than repeat.** Restarting a campaign continues from the
   last valid save point and does not overwrite completed stage outputs.
5. **Use bounded automation.** Doctors and candidate searches have declared
   trial sets, budgets, ordering, and acceptance criteria.
6. **Separate solution from approval.** Numerical or recipe success can solve
   a dataset. Only an explicit user action can create a deposit-ready snapshot.
7. **Treat machine-readable records as authoritative.** PDFs, dashboards, and
   tables are rendered from the structured record and are not the sole record.

## Terminology and hierarchy

- **Preset:** versioned project policy and its reviewed resources.
- **Campaign:** one frozen collection of datasets evaluated with one resolved
  preset and campaign configuration.
- **Dataset:** one pre-curated crystallographic input directory.
- **Candidate:** one scientific hypothesis for a dataset, such as a particular
  MR model, linear metal site, square-planar site, or two-metal geometry.
- **Stage run:** one isolated invocation of an existing NASolve stage.
- **Checkpoint:** an immutable model/refinement node with a stable parent.
- **Solution pointer:** the candidate and checkpoint currently selected as the
  dataset's solved result. It is not necessarily the newest checkpoint.
- **Approved snapshot:** an immutable copy/reference created when the user
  marks the solution deposit-ready.

The intended hierarchy is:

```text
campaign
└── dataset
    ├── shared stage history
    ├── candidate A
    │   └── checkpoint tree
    ├── candidate B
    │   └── checkpoint tree
    └── selected solution pointer
```

Candidates should share completed upstream work when scientifically valid. For
example, four metal-geometry candidates using the same MR solution should fork
after MR rather than execute Phaser four times.

## Pre-curated campaign input

Campaigns do not build, rename, or clean dataset directories. Dataset import
and preparation belong to a separate future user-facing tool.

A campaign root contains a manifest and dataset subdirectories:

```text
Campaign/
├── nasolve-campaign.toml
├── QiC/
│   ├── staraniso_alldata-unique.mtz
│   ├── Data_1_autoPROC_STARANISO_all.cif
│   ├── summary.html
│   └── nasolve.txt
├── DF/
└── EG/
```

Each dataset must contain the three authoritative processing inputs:

1. one accepted STARANISO/all-data MTZ;
2. one matching `Data_1*` metadata CIF; and
3. `summary.html`.

It may also contain `nasolve.txt`, sequence files, custom models, or other
preset-specific inputs. Existing NASolve output directories are never treated
as new datasets.

Discovery is frozen before execution. The campaign records dataset identities,
relative paths, input hashes, and the resolved input inventory. Files added
after the freeze cannot silently join the active campaign. A later explicit
refresh may create a new campaign revision.

## Project presets

Presets declare typed NASolve behavior, not arbitrary shell commands. A preset
may declare:

- schema and preset version;
- MR model providers, reviewed catalogues, exact-pair models, fallbacks,
  ensembles, copy-number policy, symmetry policy, and search budgets;
- standard mutation sites, chain sequences, aliases, deposition identities,
  curated component dictionaries, and D/L mirroring policy;
- project scaffold restraints, NARestraints mode, modified-pair mode, stacking
  policy, and overlap precedence;
- ReadySet policy and required output validation;
- anomalous trigger elements and expected-site policy;
- AutoSol sequence resources, phasing protocol, recovery trials, and acceptance
  distances;
- AutoRefine recipe, numerical continuation criteria, and validation policy;
- bounded Doctor trial definitions and candidate-selection policy;
- reporting and PDF policy;
- later curate, Table 1, and deposition policy; and
- later discovery providers, including AlphaFold.

All preset paths are resolved relative to the preset root. The frozen campaign
records the preset file, version, Git revision when available, and checksums of
every consumed resource.

Configuration precedence is:

```text
NASolve defaults < project preset < dataset nasolve.txt < explicit CLI options
```

The fully resolved configuration is frozen in each dataset run.

## Scientific stage graph

The ordinary 5W6W policy is:

```text
data validation
  -> AutoMR
  -> PostMR
  -> conditional AutoSol
  -> AutoRefine
  -> conditional Refine Doctor
  -> final model validation
  -> solved or inspection queue
  -> summarize/curate
  -> explicit approval
  -> deposit preparation and submission
```

AutoSol remains conditional on supported anomalous candidates and usable
anomalous data. AutoSol warning/failure may permit the ordinary MR refinement
path to continue without experimental phases when the preset allows it.

ReadySet's validated model and combined ligand CIF remain the refinement
inputs. The campaign must not fall back silently to the original MR model or
uncombined dictionaries.

Generated NARestraints PHIL and project scaffold EFF files retain distinct
roles. When both are present, the generated PHIL is authoritative and matching
scaffold pair restraints are removed rather than duplicated.

## Campaign states

### Campaign-level states

- `PLANNED`: discovery and preset resolution are complete.
- `RUNNING`: at least one runnable dataset remains.
- `PAUSED`: execution was deliberately suspended.
- `COMPLETE`: every dataset has reached a terminal campaign state.
- `COMPLETE_WITH_FLAGS`: complete, with inspection, blocked, or no-solution
  datasets recorded.

### Dataset-level states

- `DISCOVERED`: frozen input is valid but execution has not begun.
- `RUNNING`: a stage or candidate branch is active.
- `SOLVED`: one candidate/checkpoint satisfies the preset and is selected.
- `SOLVED_WITH_FLAGS`: selected solution is defensible but retains reported
  non-blocking warnings.
- `MULTIPLE_SOLUTIONS_READY`: multiple candidates are defensible and require a
  user choice.
- `AWAITING_INSPECTION`: scientific ambiguity prevents automatic selection.
- `BLOCKED`: a technical or hard scientific gate needs intervention.
- `NO_SOLUTION`: the bounded recipe space was exhausted without a solution.
- `DEPOSIT_READY`: the user approved an immutable solution snapshot.
- `DEPOSITED`: the approved snapshot was successfully deposited.

A local terminal or waiting state does not pause other datasets.

Candidate branches have their own status and reason. A dataset with several
solution-ready candidates remains `MULTIPLE_SOLUTIONS_READY` until a selection
policy or user decision creates its solution pointer.

## Automatic selection and statistical discipline

Standalone Doctor commands may remain interactive. In campaign mode, the
default is to execute the preset's bounded Doctor recipes and automatically
select a candidate when it crosses the declared acceptance boundary.

Automatic selection follows a fixed recipe priority and chooses the first
compatible branch that satisfies all declared criteria. It must not try an
unbounded set of branches and choose whichever has the lowest Rfree. Repeated
selection against the same Free-R set can overfit cross-validation,
particularly when few independent Free-R groups exist.

Every automated selection records:

- source candidate and checkpoint;
- selected candidate and checkpoint;
- recipes attempted before selection;
- acceptance tests and results;
- number of alternatives evaluated;
- non-blocking warnings; and
- the original branch, which remains available.

Free-R arrays remain authoritative. Campaigns and Doctors do not regenerate or
search test flags merely to improve R-factor ordering.

For ordinary refinement the current continuation boundary includes a
compatible model, `Rwork < Rfree`, and `Rwork < 0.30`, plus project validation.
Clashscore and other validation metrics are reported but their thresholds are
preset-specific; low-resolution DNA must not inherit inappropriate generic
protein gates.

## Multi-candidate campaigns

A preset may deliberately produce several scientific candidates. Examples
include linear, square-planar, and two-metal geometries or a brute-force MR
library containing dozens of models.

The preset declares:

- how candidates are generated and identified;
- where the graph forks;
- cheap rejection screens and full-evaluation criteria;
- maximum candidate and trial budgets;
- fixed automatic ranking/selection policy, or `manual` selection;
- which upstream artifacts may be shared; and
- what evidence must be shown for comparison.

Each retained candidate can proceed independently to a solution-ready model.
For manual policies, the campaign reports every defensible candidate and
places the dataset in `MULTIPLE_SOLUTIONS_READY`. It never collapses distinct
metal geometries into one result merely because one has the lowest R factor.

## Doctors and recovery policies

Doctors are bounded, stage-specific recovery planners. They may create new
branches but may not weaken hard scientific gates invisibly.

### Data Doctor

Potential responsibilities include label discovery, symmetry consistency,
Free-R integrity, wavelength consistency, anomalous signal, completeness,
likely duplicate inputs, and other pre-MR blockers.

### MR Doctor

Potential preset-approved branches include exact and fallback frames, trimmed
or more general models, ensembles, bounded copy-number alternatives,
D/L-mirrored paths, a reviewed generic duplex generator, and a finite model
library. Every Phaser candidate retains its search scores and provenance.
Changing experimental symmetry or other high-risk assumptions requires an
explicit preset policy or user intervention.

### PostMR Doctor

Potential branches include isolating the failed mutation, applying changes one
at a time, changing a reviewed operation order, or briefly refining a
canonical-parent diagnostic model before reinstalling the modification.

A canonical-parent diagnostic can never become the final structure. The
modified residue must ultimately be restored, validated through Coot/ReadySet,
restrained, and refined. Removing an anomalous modification may also disable
the AutoSol evidence path and must be reported.

### AutoSol Doctor

Potential branches include guarded label alternatives, reviewed resolution
cutoffs, anomalous-signal diagnostics, element/site expectations, and output
validation. Model-seeded or otherwise confirmatory site searches must be
distinguished from independent validation against the original Phaser model.

### Refine Doctor

The existing Refine Doctor remains the bounded refinement finisher. Campaign
mode may select its first successful preset-approved branch automatically;
standalone use may prompt. Anomalous `f''` benchmarks remain attached even if
later validation branches stop refining anomalous parameters.

The [Refine Doctor triage proposal](refine-doctor-triage.md) makes recovery for
noisy mean-intensity datasets the main path, with conditional anomalous
recipes. Standalone Doctor now implements a bounded fallback list, finite trial
budgets, and an inspection outcome when no eligible recipe passes. Broader data
diagnostics and automatic campaign Doctor triggers remain planned.

### Final Model Doctor

A later final validation layer should examine residue-level fit, geometry,
B-factor and occupancy outliers, difference density, modified-site integrity,
anomalous-site evidence, restraint violations, and model completeness. A low
global R factor is not sufficient evidence for a modified or metal site.

## Anomalous reporting

The anomalous registry begins with iodine, bromine, and selenium and remains
open to reviewed project additions and later metal-site policies. Reports retain
the expected site, symmetry-aware heavy-atom match, match distance, wavelength,
phase-use decision, occupancy, B factor, refined `f''`, theoretical `f''`, and
the checkpoint that produced the benchmark.

Known-site anomalous refinement uses exact model selections. A later recipe may
stop refining anomalous parameters after benchmarking while preserving the
benchmark and continuing to use the authoritative observations as appropriate.

## Persistence and restart

Campaigns are expected to run for a long time. The execution layer therefore
requires:

- atomic structured-report updates;
- per-dataset locks;
- subprocess identity, start time, and heartbeat records;
- detection of interrupted or abandoned work;
- clean cancellation and campaign pause;
- immutable completed stage outputs and checkpoints;
- explicit retry records rather than directory overwrites;
- deterministic random seeds where supported; and
- restart from the last compatible save point.

An interrupted stage is inspected before retry. A campaign must not infer
success from an output filename alone.

## Scheduling and scale

The first executor is local and sequential because current Phenix stages may
consume every logical CPU. Later executors may use an explicit campaign CPU,
memory, and concurrent-job budget. Scientific orchestration remains separate
from the execution backend so an eventual SLURM/HPC executor does not alter
stage logic or provenance.

For large campaigns, individual dataset JSON reports remain the scientific
source of truth while a campaign-level SQLite index provides efficient status,
query, scheduling, and reporting. The index may contain dataset hashes, state,
current stage, jobs, attempts, runtimes, selected candidate/checkpoint, headline
metrics, warnings, next actions, and paths to canonical reports.

Campaigns should detect duplicate authoritative inputs by content hash. Storage
and retention policy must be explicit; NASolve does not automatically delete
scientific outputs or failed branches.

Runtime estimates begin as ranges and are updated from observed per-stage and
per-preset durations. Candidate count, processor allocation, and completed
work contribute to the estimate. False precision is avoided.

## Inspection queue and user interface

The common campaign workflow should be short. When the current directory is a
campaign root, proposed commands include:

```bash
nasolve dataset inspect QiC
nasolve dataset approve QiC
```

These commands use the dataset's solution pointer and selected solution
checkpoint. Optional `--candidate` and `--checkpoint` arguments expose tree
navigation. If several candidates are solution-ready and none is selected,
approval must present or require a choice rather than guessing.

An inspection queue reports exact commands for opening candidates and
checkpoints in Coot. Static PDFs can contain file links and copyable commands,
but reliable one-click Coot launching requires a later local dashboard or a
registered local URL handler. A local `nasolve campaign serve` dashboard is the
preferred future direction for clickable inspection and branch selection.

## Approval and reopening

`nasolve dataset approve DATASET` creates an immutable approved snapshot from
the dataset's solution pointer and moves it to `DEPOSIT_READY`. Approval never
follows the chronologically newest checkpoint blindly.

Further experiments create new branches and cannot silently change the
approved snapshot. A deliberate command such as:

```bash
nasolve dataset unapprove QiC --reason "Revisit modified-site geometry"
```

records a new event, reopens the dataset, and preserves the former approved
snapshot and report.

## Structured reports and PDFs

Each dataset produces a canonical machine-readable report. A report renderer
may produce a versioned PDF at configured terminal states without rerunning any
scientific stage. Example preset policy:

```toml
[reporting]
pdf = "terminal-states"
states = ["DEPOSIT_READY", "DEPOSITED"]
campaign_index = true
```

Proposed commands are:

```bash
nasolve summarize RUN --pdf
nasolve campaign report CAMPAIGN --pdf --state deposit-ready,deposited
```

The latter generates one PDF per matching dataset and a campaign index. This
keeps PDF generation bounded even when a campaign contains thousands of
datasets but at most approximately one hundred deposition candidates.

A per-dataset solution report should include:

- campaign, dataset, preset, code, tool, and input identity;
- data statistics, cell, symmetry, resolution, wavelength, and checksums;
- a rendered decision/checkpoint tree with the selected path highlighted;
- MR candidates, TFZ/LLG, copy/model decisions, and warnings;
- sequence, mutations, internal codes, and deposition-code mapping;
- restraint, Coot, ReadySet, and compatibility decisions;
- AutoSol outcome, expected/matched HA sites, distances, and phase-use decision;
- anomalous `f''` benchmark, theoretical value, occupancy, and B factor;
- refinement/checkpoint metrics and Rwork/Rfree history;
- model-validation results and unresolved flags;
- the approved or selected final model; and
- exact inspection, selection, and resumption commands.

PDFs are versioned rather than overwritten, for example:

```text
Reports/
├── solution-report.deposit-ready.pdf
├── solution-report.deposited.pdf
└── report.json
```

## Curate and Table 1

`summarize` produces provenance reports. A later `curate` command produces
publication artifacts from the selected or approved solution, including the
Vecchioni Lab Table 1 format, structure slices, and later figure-generation
helpers.

Table 1 values must be traceable to their source log, MTZ, validation output,
or approved model. The exact field set and layout will be specified from lab
examples before implementation. Curate cannot silently choose a different
checkpoint from the solution or approved snapshot.

## Deposition

Deposition is deliberately downstream of a mature campaign manager and cannot
be tested safely until the solution, approval, validation, and reporting paths
are stable.

Deposition should have two explicit layers:

1. `deposit prepare`: translate reviewed internal component identities, assemble
   coordinates, structure factors, dictionaries, sequences, metadata, and
   validation artifacts, then validate the package.
2. `deposit submit`: perform the external PDB/OneDep submission for explicitly
   approved campaign datasets.

Only `DEPOSIT_READY` datasets are eligible. External submission is never an
implicit consequence of campaign completion. `DEPOSITED` records deposition
identifiers and the exact approved snapshot submitted.

## Proposed implementation sequence

1. Add a versioned preset schema and loader.
2. Add strict dataset discovery, input freezing, and campaign state storage.
3. Orchestrate one resumable single-candidate 5W6W path using existing stages.
4. Add campaign-level Doctor policy, automatic bounded selection, and the
   inspection queue.
5. Add machine-readable summaries and per-dataset/campaign PDF rendering.
6. Add multi-candidate DAGs, shared-parent execution, budgets, and comparison.
7. Add a local dashboard for status, Coot launch, tree navigation, and approval.
8. Add Model Doctor and project-specific recovery extensions.
9. Add curate and the lab Table 1 specification.
10. Add deposition preparation, validation, and explicit submission.

Steps 1 and 2 provide `preset check`, `campaign plan` and `campaign status`,
with an immutable JSON inventory, portable resource snapshots and integrity
verification. Step 3 adds `campaign run`, `campaign pause` and explicit
`campaign retry` for one sequential standard-frame path. It reuses verified
completed stages, preserves incomplete attempts for inspection and records
per-dataset outcomes separately from the plan. It does not yet parse the
proposed `nasolve-campaign.toml` or maintain a database execution index.

The first execution slice ends after step 3. Real Phenix/Coot campaign smoke
checks remain necessary alongside the regression suite. Automatic Doctor
selection and the later approval/deposition workflow are not implied by
numerical success.

## Deferred decisions

The following details are intentionally deferred until their implementation
stage:

- exact TOML field names and preset inheritance syntax;
- the lab Table 1 field set and visual format;
- dashboard framework and local Coot-launch mechanism;
- direct OneDep integration constraints and authentication;
- storage archival policy for very large campaigns;
- cluster executor details; and
- specific AlphaFold and metal-base-pair candidate providers.

These are extension points, not blockers for the first campaign slice.
