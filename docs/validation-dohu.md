# DOHU validation — 2026-09-09

This record captures the user's live execution and Coot inspection after the
local dictionary, Phenix 2.2, checkpoint-view, and phosphate fixes. It is an
integration record, not a deposition-validation report.

## Environment and inputs

| Item | Value |
| --- | --- |
| Host | macOS, Apple Silicon; newly rebuilt native Python environment |
| Python | 3.12.14 |
| NARestraints | 1.1.1 |
| Phenix | 2.2.1-6174 |
| Coot | 1.3.3 |
| Dataset | `examples/DOHU` |
| Configuration | standard mode; frame `W`; pair `D:OHU` |
| Run | `examples/DOHU/AutoMR/run_004` |
| Selected checkpoint | `refine-001`, parent `postmr` |

The dataset contains the usual autoPROC/STARANISO CIF, MTZ, summary, and
`nasolve.txt`. `D` resolves to `1AP`. OHU construction uses the local
`src/nasolve/data/ligands/OHU.cif` with its NARestraints residue mapping.

## Execution

From the repository root:

```bash
./nasolve automr examples/DOHU --execute && ./nasolve postmr
./nasolve autorefine examples/DOHU/AutoMR/run_004
```

These commands produced the run recorded here. A repeat AutoMR invocation
allocates a new numbered run; use its reported path for subsequent commands.

AutoMR returned `MR_SUCCESS` with TFZ **14.30**. PostMR returned `POSTMR_READY`
and supplied the prepared ReadySet model, `narestraints_Std_padd.phil`,
`5W6W_secondary_structure.eff`, `1AP.cif`, and `OHU.cif`. This completed the
path that had previously stopped on unsupported OHU construction and then on
ambiguous reused phosphate atom serials.

AutoRefine completed five cycles with the automatic target, mean observations
`IMEAN,SIGIMEAN`, no experimental phases, and anomalous refinement off. It
returned `AUTOREFINE_READY` and selected `refine-001` as current.

| Metric | Initial | Final |
| --- | ---: | ---: |
| Rwork | 0.277 | 0.147 |
| Rfree | 0.296 | 0.209 |
| Rfree − Rwork | — | 0.062 |
| Clashscore | — | 36.70 |
| Bond RMSD | — | Not reported |
| Angle RMSD | — | Not reported |

Phenix reported unrecognized output MTZ labels for filtered observations,
model factors, and unfilled map coefficients. Model PDB/mmCIF, reflection
mmCIF, the MTZ, logs, and the round report were produced. This warning did not
prevent completion; this record does not independently validate every exported
reflection column.

## Inspection and interpretation

The user confirmed that the Coot view worked and the result looked correct.
Simon describes the structure as an intentionally interconnected
symmetry-related crystal and considers the observed clashes expected in that
lattice context. The raw clashscore is retained above with that interpretation.
No clash threshold or score was changed for this validation.

The latest run's full model and maps were not independently remeasured in the
documentation workflow. `POSTMR_READY` confirms that the implemented phosphate
checks completed; exact atom removals and measured geometry remain in
`PostMR/report.json` under `phosphate_cleanup`. Inspect the current model with:

```bash
./nasolve show examples/DOHU/AutoMR/run_004
```

Bare `./nasolve show` also opens the current checkpoint when this run is the
active workspace. A newer unselected attempt does not replace the current view.

## Automated checks and scope

The assembled fixes passed the complete suite in an isolated source-test
environment. To repeat in an installed checkout:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m pytest -q
```

The isolated result was **225 passed, 51 subtests passed**. The user separately
confirmed **225 passing tests** on the Mac before this live run.

The Phenix 2.2 execution above validates the ordinary mean-data path. It does
not exercise AutoSol, anomalous refinement, a multi-dataset campaign, or every
possible modified residue. Generic construction still needs a supported
NARestraints mapping and an available local dictionary. Modified-pair wobble
angles and sulfur–nitrogen contact targets remain separate NARestraints work.
See [development priorities](architecture.md#next-development-priorities).

This document uses repository-relative paths. The documentation patch contains
no diffraction data, generated coordinates, maps, or run histories.
