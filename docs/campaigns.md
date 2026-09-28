# NASolve campaigns and project presets

Status: architecture and roadmap. Versioned presets, immutable schema-2
campaign planning/status, and one sequential resumable candidate path are
implemented for standard W plus prepared nonstandard per-dataset PDB/sequence
inputs; existing schema-1 W plans remain executable. See
[campaign planning](campaign-planning.md) and
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

The first supported production preset is 5W6W. Schema-2 planning can also host
prepared nonstandard datasets whose explicit model/sequence intent suppresses
W-specific AutoMR defaults and chemistry while retaining the selected campaign's
bounded shared stage policy. A neutral project-local preset ID is recommended
for a geometry-diverse real campaign so the human-facing project identity is not
misleading. The architecture must also support later project presets with
different MR catalogues, sequences, metalation strategies, restraint policies,
AutoSol protocols, refinement recipes, and imported model providers. Model
generation itself is upstream; NASolve does not invoke AlphaFold.

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

Campaigns do not act as the laboratory design/raw-data database. Dataset import,
design reconciliation and folder preparation may be handled by the separate
upstream NAPrep package, or manually.

NAPrep is optional. NASolve consumes a curated dataset/model/design handoff and
then owns the downstream crystallographic decision tree, campaign execution,
Campaign Doctor, curation/reporting and deposition provenance.

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
- workflow-level Doctor policy, including the future semantic option
  **"apply Doctor as needed"**: absent means stop at the review gate; enabled
  means run only the applicable bounded Doctor(s) already exposed by the backend,
  while preserving explicit inspection/selection semantics;
- reporting and PDF policy;
- later curate, Table 1, and deposition policy; and
- imported/external provider provenance and reviewed model transformations.

All preset paths are resolved relative to the preset root. The frozen campaign
records the preset file, version, Git revision when available, and checksums of
every consumed resource.

Configuration precedence is:

```text
NASolve defaults < project preset < dataset nasolve.txt < explicit CLI options
```

The fully resolved configuration is frozen in each dataset run.

## Scientific stage graph

Keep the **current executable campaign graph** separate from the broader
registration/Doctor target architecture.

Current Pine campaign execution is:

```text
frozen input/model/target validation
  -> AutoMR preflight
  -> Phaser
  -> PostMR
  -> conditional AutoSol
  -> AutoRefine
  -> SOLVED / REVIEW / BLOCKED / NO_SOLUTION
```

A plain `campaign run ROOT` currently advances eligible datasets through the
default AutoRefine endpoint. AutoSol is conditional on PostMR evidence: when no
supported anomalous candidate is present, the AutoSol stage records accepted
status `SKIPPED` and does not launch `phenix.autosol`. Review/failure of one
dataset does not stop unrelated campaign members.

Pine now also contains a **regression + live validated** explicit
`AUTOREFINE_REVIEW -> refine-doctor` continuation for campaign-owned Refine
Doctor provenance. It is deliberately not automatic and not part of default
campaign completion; a future workflow recipe may opt into Doctor-as-needed
behavior.

The longer-term registration-aware target graph is:

```text
data validation
  -> AutoMR
       -> Registration Scout
       -> Phaser
       -> authoritative ASU Registration
       -> optional Registration/Recut Rescue branch when needed
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

That second graph is **not all current runtime behavior**. In particular, the
merged design-aware Scout-v2 helper remains experimental/non-runtime, automatic
ASU Registration/Recut Rescue is not yet the campaign authority, and automatic
campaign Doctor escalation remains future work.

AutoSol warning/failure may later permit the ordinary MR refinement path to
continue without experimental phases when an explicit reviewed workflow recipe
allows it. Current policy remains fail-closed for unaccepted anomalous branches.

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

Standalone Doctor now implements bounded recovery for ordinary and anomalous
data, finite trial budgets, and an inspection outcome when no eligible recipe
passes. The original design proposal is archived under
`history/refine-doctor-triage.md`. Broader data diagnostics and automatic
campaign Doctor triggers remain planned; current implementation state lives in
`development-handoff.md`.

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
checkpoints in Coot. Every interactive CLI decision must correspond to a backend
action that the future GUI can invoke directly: open/inspect in Coot, yes/no
confirmation, explicit continuation from a review gate, Doctor candidate
inspection, and checkpoint selection/Make Current. The GUI may replace terminal
prompts with buttons, cards or action popovers, but the eligibility rule,
default, provenance and resulting state must be identical.

Static PDFs can contain file links and copyable commands. The planned native GUI
is the preferred interactive surface for clickable inspection and branch
selection; a local web dashboard remains an optional implementation detail, not
the scientific authority.

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

1. **Implemented:** versioned preset schema and loader.
2. **Implemented:** strict dataset discovery, input freezing, campaign state
   storage, explicit sequence-reference freezing, and root
   `nasolve-campaign.toml` sequence threads.
3. **Implemented and now real-environment checked through PostMR:** one resumable
   sequential 5W6W execution path using AutoMR/PostMR/conditional
   AutoSol/AutoRefine, including pause and explicit retry. In the four-member
   W live campaign (`DOHU`, `QiC_120325_0513`, `QE_120325_0607`,
   `EG_091325-0302`), planning/integrity and real preflight/Phaser/PostMR
   passed 4/4 under Phenix 2.2.1 and Coot 1.3.3. The plain unattended resume
   through the default AutoRefine endpoint is the current live check.
4. **Implemented on Pine; real prepared-nonstandard validation pending:**
   schema-2 planning/execution for one frozen nonstandard per-dataset PDB
   provider plus an exact frozen raw+parsed sequence target, while preserving
   schema-1 W plan execution and pause/retry/relocation safeguards.
5. **Implemented in fixture-backed regression; real geometry-diverse gate
   pending:** standard W and prepared nonstandard members can coexist under one
   sequential coordinator without frame/pair/chemistry leakage. Run a small
   real 3-5 member prepared-nonstandard/geometry-diverse campaign when those
   inputs are available, with ambiguous representation problems stopping only
   the affected dataset.
6. **Add first-class workflow-recipe semantics.** The selected/frozen campaign
   recipe should explicitly declare its intended endpoint and conditional stage
   graph instead of relying on the executor's hard-coded stage order/default
   endpoint. Preserve current conditional AutoSol skip/run behavior and
   fail-closed per-dataset stops. A recipe may optionally request
   **"apply Doctor as needed"**; omission leaves review states for inspection,
   while opt-in may traverse only validated bounded Doctor transitions. Doctor
   recommendation and checkpoint selection remain separate unless a later,
   separately validated policy explicitly changes that.
7. Add explicit stable Design grouping/identity for datasets sharing one
   construct/design record. Do not infer Design membership from filenames or
   similarity.
8. **Prerequisites implemented; policy/execution still future:** read-only
   checkpoint-candidate descriptors and donor-checkpoint versus recipient-run
   comparisons now provide provenance-rich inputs for Campaign Doctor. Add a
   campaign-wide read-only candidate view, then a reviewed donor eligibility
   policy and attempt-local rescue-provider provenance before any automatic
   donor selection.
9. Validate one explicit-donor recipient rescue before adding bounded automatic
   Campaign Doctor donor enumeration. Preserve the failed recipient attempt,
   observations, Free-R set and every rescue candidate.
10. **GUI fork is allowed after the basic heterogeneous campaign + Design layer
    are CLI-functional.** The GUI should consume the workflow recipe/state as
    backend authority rather than inventing its own progression semantics.
11. Add machine-readable summaries and per-dataset/campaign PDF rendering.
12. Add broader multi-candidate DAGs, shared-parent execution, model
    libraries/ensembles and rescue budgets under explicit policy.
13. Add Model Doctor and project-specific recovery extensions.
14. Add curate and the lab Table 1 specification.
15. Add deposition preparation, validation, and explicit submission.

The implemented campaign slice provides `preset check`, `campaign plan`,
`campaign status`, `campaign run`, `campaign pause`, and explicit
`campaign retry` with immutable planning state, portable resource snapshots,
integrity verification, and per-dataset execution records. Planning can also
freeze explicit sequence threads and provider/target provenance used by later
run-level compatibility records. A plain `campaign run` currently runs
unattended through AutoRefine, but that endpoint remains executor-defined rather
than recipe-declared. A database execution index and general multi-candidate DAG
remain future work.

The current real W smoke test plus QiC Doctor continuation validate campaign
orchestration through explicit `refine-doctor`. The next stress test is the
user-local `examples/TestSets/` campaign (roughly nine datasets): one invocation
from MR through conditional AutoSol, AutoRefine and explicit Doctor continuation,
with honest review/block outcomes preserved. This does not replace the later
prepared-nonstandard geometry-diverse Pine live gate.

The donor/recipient comparison layer is descriptive only: automatic cross-dataset
Doctor eligibility/selection and the later approval/deposition workflow are not
implied by numerical success or by matching compatibility facts.

## Deferred decisions

The following details are intentionally deferred until their implementation
stage:

- exact TOML field names and preset inheritance syntax;
- the lab Table 1 field set and visual format;
- dashboard framework and local Coot-launch mechanism;
- direct OneDep integration constraints and authentication;
- storage archival policy for very large campaigns;
- cluster executor details;
- stable optional NAPrep handoff details; and
- specific metal-base-pair candidate providers.

These are extension points, not blockers for the first campaign slice.
