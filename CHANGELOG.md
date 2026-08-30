# Changelog

All notable user-visible, compatibility, schema, and reproducibility changes
to NASolve are recorded here.

The format follows Keep a Changelog. Until the first tagged release, historical
entries are reconstructed from repository history.

## [Unreleased]

### Added

- Added a tracked POSIX `./nasolve` source-checkout launcher. It resolves
  symbolic links, uses the checkout's `.venv` by default, accepts an explicit
  `NASOLVE_PYTHON`, and scopes `src` path injection to the launched process.
- Added portable run, dataset, and repository artifact anchors. Newly created
  checkpoint registries no longer depend on a collaborator's checkout path.
- Added compatibility rebasing for legacy run reports containing absolute
  paths from another computer.
- Added `nasolve workspace use`, `status`, and `clear`. An active dataset/run is
  stored in the existing user configuration, allowing stage commands to omit
  repeated paths.
- Added collaboration and AI-review guidance in `AGENTS.md`,
  `docs/collaboration.md`, and the pull-request template.
- Added a frozen SHA-256 for authoritative reflections to new AutoMR reports.
- Added a checksummed, run-local `Model/seq_base.txt` snapshot for new standard
  frame runs when the selected catalogue supplies it, so conditional AutoSol
  can continue without the source catalogue.
- Added SHA-256 values for AutoSol heavy-atom and refinement-phase outputs.

### Fixed

- Fresh-terminal source launches no longer depend on macOS Python loading the
  editable-install `.pth` file; this avoids `ModuleNotFoundError: nasolve` when
  that metadata carries the hidden file flag. The launcher also places the
  checkout package ahead of the current directory, so an unrelated
  `nasolve.py` cannot shadow it.
- Bound AutoRefine observation, Free-R, and experimental-phase Miller arrays
  explicitly to their source MTZ files through the Phenix Data Manager. This
  fixes Phenix 2.1 preflight failures when an MTZ contains multiple equally
  suitable observation arrays, such as `IMEAN,SIGIMEAN` and anomalous
  intensities.
- Committed PostMR runs can now resolve their prepared model, authoritative
  observations, restraints, Phaser outputs, and optional AutoSol inputs after
  the repository is cloned or moved.
- Legacy paths now prefer the selected checkout even when the collaborator's
  old checkout still exists, understand Windows/POSIX path forms, and reject
  traversal or ambiguous rebases.
- AutoRefine recovers approved AutoSol phases after relocation when the root
  checkpoint was created before AutoSol completed.
- AutoRefine now fails closed when an approved phase source is unavailable,
  instead of silently continuing without the requested phases.
- Malformed saved workspace, run-report, and checkpoint JSON now produces a
  guarded NASolve error instead of an uncaught type exception.
- Coot views now fail closed when a reported map, primary refinement MTZ, or
  required ligand dictionary is missing or fails checksum validation.
- AutoSol and Coot now verify available frozen model/data checksums before
  consuming relocated artifacts.
- Legacy AutoSol runs recover the exact declared frame's `seq_base.txt` after
  relocation even when the historical pair-model filename no longer exists;
  the selected checkout wins while an older checkout is still present.
- Coot scratch creation rejects unsafe checkpoint path components and existing
  symlinks that could redirect logs, launch records, or backups outside a run.

### Changed

- AutoRefine reuses the checksum produced by mandatory phase validation when
  writing the child checkpoint, avoiding a second full read of the AutoSol MTZ
  in each round. A stable file-identity check before and after Phenix rejects
  phase replacement, modification, or deletion during the external process.
- AutoRefine checkpoint serialization hashes each unique output file once, so
  legacy Phenix layouts that use one MTZ for maps and refinement reflections
  no longer read that potentially large file twice.
- AutoRefine now writes file-scoped Miller-array selections into
  `autorefine.params` while retaining the existing `xray_data` refinement
  parameters for compatibility.
- Separate AutoSol phase files receive their own file-scoped
  Hendrickson-Lattman label selection.
- `automr` uses the active workspace dataset when its dataset argument is
  omitted. `postmr`, `autosol`, `autorefine`, `refine-doctor`,
  `checkpoints list`, `checkpoints add`, `checkpoints use CHECKPOINT`, and
  `show` can use the active run.
- Checkpoint schema 2 uses `anchor` plus `relative_path` (or an explicit
  `absolute_path` fallback), SHA-256, and size. Refinement review outputs such
  as maps, reflection/mmCIF files, metrics, and logs use the same references.
- A newly allocated AutoMR run becomes active automatically. Explicit one-off
  paths passed to later stages do not silently change the active workspace.
- Machine-local Coot GUI scratch and PostMR Coot backup directories are ignored;
  portable stage artifacts remain visible for deliberate commits.

### Tests

- Added source-launcher coverage for fresh terminals, symlink resolution,
  argument and working-directory preservation, `PYTHONPATH` scoping, explicit
  and default interpreters, current-directory import shadowing, and
  missing, directory-valued, and non-executable interpreter diagnostics.
- Added hash-call regression coverage for inherited/recovered AutoSol phases
  and shared AutoRefine MTZ outputs, plus phase drift during Phenix, immutable
  failed-attempt retention, and successful next-round recovery.
- Added relocation coverage for reports created beneath a collaborator's
  absolute directory.
- Added coverage for anchored run/dataset references and path-escape rejection.
- Added repository-anchor and exact frame-sequence relocation coverage,
  including old and current checkouts existing at the same time.
- Added same-machine-copy, cross-platform legacy-path, schema migration, and
  checksummed-reflection coverage.
- Added legacy AutoSol coverage for reports that predate frozen input hashes.
- Added workspace configuration and optional-target parser coverage.
- Added regression coverage for mean-intensity refinement without AutoSol.
- Expanded coverage for anomalous observations, Free-R flags, and a separate
  experimental-phase MTZ.
- Validated the AutoRefine selector patch with Phenix 2.1-6048 in both a
  `--dry_run` preflight and a complete five-cycle E:G refinement that reached
  `AUTOREFINE_READY`.
- Re-ran all four example workflows end to end with Phenix 2.1-6048 and Coot
  1.3.1. Fresh five-cycle refinements reached `AUTOREFINE_READY` for E:G
  (TFZ 11.80, Rwork/Rfree 0.127/0.168), the F:D synthetic integration fixture
  (TFZ 11.80, 0.131/0.171), Q:E (TFZ 10.80, 0.161/0.208), and Q:iC (TFZ
  10.80, 0.146/0.148). Q:iC retained the expected non-blocking AutoSol warning
  and refined its anomalous iodine without experimental phases.

### Migration

- No configuration or artifact migration is required for the source launcher;
  the generated package entry point remains supported when its editable
  installation metadata loads normally.
- Existing absolute-path reports remain readable; they do not need to be
  rewritten before use.
- Existing checkpoint schema-1 registries are read in place and migrate to
  schema 2 on their next write. Older NASolve versions reject schema 2 instead
  of interpreting an anchor-relative path against the current directory.
- Portably resolvable legacy references are normalized during migration;
  unavailable or external-only legacy evidence is retained explicitly as
  non-operational provenance rather than remaining a raw schema-1 path in a
  schema-2 registry.
- Legacy AutoMR reports without `reflections_sha256` remain usable and are
  marked `legacy-unverified` when a root checkpoint is first initialized,
  rather than silently claiming observation checksum verification.
- Existing failed refinement rounds remain immutable. Running
  `nasolve autorefine RUN` again creates the next numbered checkpoint.
- Workspace state is machine-local and is not intended for Git.

### Known compatibility notes

- File-scoped Data Manager parameters have been validated with Phenix
  2.1-6048 in preflight and a complete five-cycle E:G refinement. A Phenix
  1.20.1 integration run remains desirable.
- Large MTZ/map histories may eventually warrant Git LFS; current fixtures are
  intentionally kept in ordinary Git until a repository-wide LFS policy is
  adopted.

## [0.1.0 development baseline] - 2026-08-28

### Added

- External Phenix and Coot discovery and saved runtime configuration.
- Guarded AutoMR with frozen inputs and TFZ classification.
- PostMR model preparation, curated modified nucleotides, NARestraints, and
  hydrogen-free ReadySet.
- Conditional AutoSol for supported nucleotide-bound I, Br, and Se atoms.
- Sequence mutation, modified-pair restraints, and model mirroring.
- Checkpointed AutoRefine and bounded Refine Doctor triage.
