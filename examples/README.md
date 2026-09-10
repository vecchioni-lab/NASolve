# Rerunnable example inputs

Use these inputs with the checked-out NASolve source, its installed Python
dependencies, the repository's `MR_frames` catalogue, and working Phenix/Coot
installations. Start with the installation instructions in the [main
README](../README.md) and run `./nasolve check` from the checkout root.

| Dataset | Repository directory | Configured pair | Workflow |
| --- | --- | --- | --- |
| DOHU | `examples/DOHU` | `D:OHU` → `1AP:OHU` | AutoMR → PostMR → AutoRefine |
| QiC | `examples/QiC_120325_0513` | `Q:iC` → `S6G:C38` | AutoMR → PostMR → conditional AutoSol → AutoRefine |

Each directory contains `nasolve.txt`, `staraniso_alldata-unique.mtz`,
`Data_1_autoPROC_STARANISO_all.cif`, and `summary.html`. The user's uploaded
`examples/QiC` inputs are byte-for-byte identical to the four corresponding
files already stored in `examples/QiC_120325_0513`; use the dated repository
directory. Other existing examples include `QE_120325_0607`, `EG_091325-0302`,
and `FD_dummy` (the synthetic integration fixture).

## Run DOHU

Run one command at a time and check each stage's result before continuing:

```bash
./nasolve automr examples/DOHU --execute
./nasolve postmr
./nasolve autorefine
./nasolve show
```

AutoMR allocates a new numbered run and makes it the active workspace. Bare
subsequent commands use that run; finish one dataset sequence before starting
another. Explicit run paths remain supported. DOHU uses the included OHU ligand
dictionary and does not need AutoSol. The [earlier DOHU validation
record](../docs/validation-dohu.md) describes the user's complete execution on
Phenix 2.2.1-6174 and Coot 1.3.3; its results are not a newly generated run.

## Run QiC

```bash
./nasolve automr examples/QiC_120325_0513 --execute
./nasolve postmr
./nasolve autosol
./nasolve autorefine
./nasolve checkpoints list
```

QiC's iodine makes guarded MR-SAD phasing applicable. `AUTOSOL_READY` confirms
accepted phases; an AutoSol warning can withhold phase approval even when the
command exits successfully. Inspect that result before proceeding. This input
publication adds no new live AutoSol or anomalous-refinement validation.

An `AUTOREFINE_REVIEW` result does not become current automatically. Use the
checkpoint ID printed by AutoRefine with `./nasolve show --checkpoint ID` to
inspect it. Bare `show` follows the selected current checkpoint, which may
still be PostMR. `./nasolve refine-doctor --from ID` can audit a reported
refinement and compare bounded branches.

## Integrity and scope

[inputs.sha256](inputs.sha256) covers the eight input files listed above.
Verify their bytes from the repository root:

```bash
shasum -a 256 -c examples/inputs.sha256
```

These are inputs for fresh executions, not a package for resuming the user's
latest checkpoints. The new DOHU addition includes no generated models, maps,
logs, GUI state, environment directories, or run histories. Existing historical
run directories in other examples are unchanged.

Publication validation checks configuration parsing, dataset discovery,
standard-frame model and ligand resolution, and exact file hashes. It does not
run Phaser, Coot, or Phenix. No workflow algorithm or checkpoint schema changes
are required to use these inputs. For sharing a selected completed run, follow
the separate [collaboration artifact guidance](../docs/collaboration.md#what-to-commit).
