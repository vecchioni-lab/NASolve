> **Historical record — not an active implementation contract.**  
> Preserved for provenance, debugging, and understanding why earlier decisions were made. Commands, paths, test counts, branch names, and next-action sections below may be obsolete. Verify current behavior against active documentation and code before acting on this file.

# Refine Doctor triage direction

Status: implementation and remaining design direction, updated 2026-09-10.
Standalone Doctor now implements bounded ordinary and anomalous trial lists,
explicit scattering settings, and separate numerical ranking and recommendation.
Campaign triggers and the broader diagnosis-driven alternatives remain planned.

## Available in this patch

The mean-data list tries conservative ML, eligible MLHL and individual ADPs,
then separate coordinate-only and group-B-only sibling branches. Anomalous data
try fixed calculated scattering with ML/eligible MLHL, f''-only refinement,
then coordinate-only and B-only fixed-scattering branches. All start from the
same source, preserve flags and occupancies, and stop on the first numerical
pass. `--max-trials` defaults to five and accepts 1-10; `--cycles` defaults to
three and accepts 1-10. A technical error stops further scientific trials.

An invalid or unavailable Free-R audit stops before any refinement. A review
result remains review: it prints a numerically ranked inspection candidate
without an automatic selection or an assertion of statistical superiority.
The report records skipped recipes, budget use, stopping reasons and next
actions. No campaign status, historical result or current checkpoint is
automatically rewritten to count a review result as solved.

## Ordinary datasets are the main path

Simon reports that most datasets in the intended campaigns use ordinary mean
observations. Recovery for noisy `IMEAN,SIGIMEAN` data is therefore a primary
requirement. Anomalous recipes extend that path when applicable.

Keep three decisions separate: the observation array, the optional phase
information, and the scattering parameters. Classify the actual selected
Miller array and its provenance; neither a filename nor a heavy atom in the
model proves that usable anomalous differences are available. Mean intensities
alone do not retain those differences. Fixed physical scattering corrections
and fitting anomalous parameters are different decisions; do not assume
corrections must be zero for every mean-data model. Phenix documents separate
controls for Friedel-mate handling and fixed or refined f'/f'' values.
[Phenix refinement reference](https://phenix-online.org/documentation/reference/refinement.html)

The original Doctor already offered reciprocal-space ML with residue-group B
factors and fixed occupancies, an accepted-phase MLHL counterpart, and an
individual-ADP branch with resolution and observation-count eligibility gates.
AutoRefine already enables XYZ/ADP weight optimization. These remain the
starting point, rather than being presented as new fallback features.

## Proposed ordered triage

Each entry needs an eligibility reason, a finite cost, and a stop condition.
Choose a few applicable trials rather than running every combination.

| Step | Evidence to examine | Proposed response |
| --- | --- | --- |
| 1. Establish trustworthy inputs | Observation identity, uncertainty estimates, model/data symmetry, Free-R integrity and shell coverage, restraint identity, available phases | Stop on corrupt or incompatible inputs. Classify a small test set separately from invalid flags. Software or missing-file errors require technical recovery. |
| 2. Try the ordinary conservative recipe | Noisy mean observations or an overly flexible starting refinement | Use the existing ML/group-B/fixed-occupancy branch. Compare MLHL only when accepted phase information exists. |
| 3. Separate model adjustments | Poor geometry, unstable B factors, or coupled changes during refinement | Add bounded coordinate-only and B-only stages. Each complete trial starts from the same source; record every intermediate parent. Permit a short continuation only when the recorded trend supports it. |
| 4. Review restraint and model assumptions | Local map disagreement or persistent modified-site distortion | Check phosphate links, dictionary atom mapping, base-pair/stacking targets, and scaffold restraints. Use only reviewed restraint alternatives. Incorrect chemistry requires correction before more refinement. |
| 5. Investigate remaining data/model mismatch | Completeness, anisotropy, intensity outliers, scaling or solvent-mask concerns, possible twinning | Use data diagnostics to select a specific next hypothesis or request reprocessing/model inspection. Do not automatically try twin laws, discard reflections, or change symmetry to lower Rfree. |
| 6. Finish or hand back | No eligible trials, exhausted budget, conflicting diagnostics, or differences too uncertain to rank | Preserve the current checkpoint and report an inspection outcome with candidates, attempted/skipped recipes, reasons, and the next useful action. |

Phenix provides coordinate/ADP strategy controls and nucleic-acid secondary
structure restraints. `xtriage` can examine completeness, anisotropy, anomalous
signal, and twinning evidence. Their availability does not validate a proposed
NASolve recipe; each integration still needs version-specific checks and real
dataset validation.
[Phenix refinement reference](https://phenix-online.org/documentation/reference/refinement.html),
[Xtriage reference](https://phenix-online.org/documentation/reference/xtriage.html)

## Conditional anomalous recipes

Where separate Friedel observations, a known site, and wavelength provenance
support the experiment, add fixed calculated f'/f'', f''-only refinement with
f' and occupancy fixed, and explicit reuse of prior fitted scattering values.
These options complement ordinary geometry/B-factor triage. Missing or weak
anomalous evidence should produce an eligibility explanation.

The legacy `anomalous_mode="off"` retains the selected anomalous observations
but omits explicit scattering-group parameters. It must not be described as
preserving fitted or calculated f'/f'' until the implementation actually writes
those values. New Doctor defaults use explicit `fixed` and `fdp-only` modes instead.
Calculated values and their source are recorded; diagnostics now also store
final f' and distinguish fixed from fitted values. Explicit reuse of an older
fitted pair remains planned. Phenix supports explicitly fixed values
and refinement of f'' alone.
[Phenix refinement reference](https://phenix-online.org/documentation/reference/refinement.html)

## Comparisons, stopping, and campaign recipes

Keep the authoritative observations, Free-R flags, and source checkpoint fixed
for comparable trials. A diagnostic using a different resolution range,
reflection subset, or Friedel merging needs separate provenance and a common
evaluation basis before its Rfree can be ranked against ordinary branches.

Separate numerical ranking, confidence in differences, and checkpoint
selection. A positive Rfree-minus-Rwork gap is not an optimization objective.
Retaining the source is a conservative decision, not evidence that it fits
better than every child. A small test set neither proves a model is correct
nor guarantees that an inversion is just noise. Report missing validation
metrics as unknown, and interpret geometry in the project's nucleic-acid and
crystal-connectivity context. Numerical success still requires map/model review.

A future campaign preset should freeze trigger reasons, ordered eligible
recipes, per-trial and total budgets, stop rules, and the selection policy.
Trigger Doctor only for supported refinement review conditions with reusable
inputs; a failed integrity gate or technical exception is not a scientific
recipe trigger. Run it once per diagnosed source/configuration unless an
explicit retry or changed evidence creates a new attempt. Resume must preserve
completed trials. If nothing resolves the issue, keep the dataset in
`AWAITING_INSPECTION` and continue other datasets. Automatic Doctor execution
and these richer preset fields are not available in the current executor.

## Implementation order and validation cases

Recommendation reasoning, independent coordinate/B fallbacks, and explicit
calculated anomalous modes are now implemented. Chained staging, broader data
diagnostics and reviewed restraint alternatives remain future work. Next expose
the reviewed list and budgets through a versioned campaign preset and executor
integration.

Regression coverage should include mean-only datasets without heavy atoms,
small valid versus corrupt Free-R sets, unavailable phases, ineligible ADPs,
explicit scattering values and provenance, exhausted budgets, interrupted
staged trials, and unchanged checkpoint selection. Live validation must include
noisy ordinary datasets as well as the anomalous QiC case; success on one data
class is not validation of the other.

## Live validation and handoff, 2026-09-11

The user completed the first updated Doctor run on QiC on 2026-09-11, after
syncing the published source and passing 395 tests and 129 subtests on macOS.
The command, run from the NASolve checkout, was:

```bash
./nasolve refine-doctor examples/QiC_120325_0513/AutoMR/run_004 --from refine-001
```

Doctor completed four sibling trials, recommended the coordinate-only
fixed-scattering branch `refine-007`, and stopped on its numerical pass before
the fifth recipe. The source remained current. This is a live workflow check;
the numerical recommendation still needs map/model inspection. The source had
Rwork 0.1644, Rfree 0.1562 and 66 independent Free-R groups. Those are historical
results from the earlier implementation, not validation of the new recipes.
The user's installed runtime is Phenix 2.2.1-6174 and Coot 1.3.3 on Apple Silicon.
No scientific execution was performed in the coding environment during
publication.

That live run identified a prompt issue: `i` printed inspection commands and
exited. The follow-up now opens Coot and repeats the `y/N/i` prompt after
`i` plus Enter. Selection still requires `y`; inspection never selects the
candidate. The prompt change is covered with simulated input and a controlled
GUI launcher; live Coot interaction remains to be checked on the user's Mac.

The prompt update passed **399 tests and 132 subtests**, with **2 skips** for
process-inspection cases in the Linux container. The exact validation command,
run with Python 3.12.14 from the prepared checkout, was:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /workspace/scratch/fe02cd83cd4e/nasolve_test_env/bin/python -m pytest -q
```

For a local checkout, the corresponding interpreter is `.venv/bin/python`.
Focused validation used the same command with `tests/test_doctor_inspection.py
tests/test_cli.py tests/test_doctor_triage.py`, passing 33 tests and 17 subtests.
The new regression tests reproduced the original prompt exit before the fix.
They verify the requested model/map sources, inspection followed by acceptance
or decline, repeated and invalid input, launch failure, EOF/Ctrl-C, and
noninteractive commands with spaces in the run path. The prompt change affects
the CLI, its tests and documentation; scientific recipes, selection validation
and report/checkpoint schemas are unchanged.

The preceding 2026-09-10 publication included the preset/planning and
campaign-execution modules, their CLI/tests/docs, the macOS worker-shutdown and
AutoSol parameter fixes, and the standalone Doctor update. Presets, campaign
plans and execution records use their documented schema 1; the Doctor changes
add report fields without migrating stage or checkpoint schemas. Existing
frozen plans and immutable run history remain usable. Generated local campaign
state, refinement outputs, logs, patch archives and virtual environments are
not part of the publication.

Next inspect the QiC candidate and validate a noisy ordinary `IMEAN,SIGIMEAN`
case. Campaign recipe configuration and automatic Doctor triggers remain the
next development block, after reviewing these live results.
