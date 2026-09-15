# Plan a campaign before running structures

Campaign planning is the first implemented part of the
[campaign roadmap](campaigns.md). It validates project policy, inventories a
fixed set of datasets, resolves their requested ligands and search models, and
records checksums. It does not run scientific stages or create solution or
approval decisions.

## Quick check using the published inputs

From a NASolve source checkout with its dependencies installed:

```bash
./nasolve preset check 5w6w
./nasolve campaign plan examples --dataset DOHU --dataset QiC_120325_0513
./nasolve campaign status examples
```

The plan is created at `examples/NASolveCampaign/plan.json`. These commands do
not rerun Phaser, Coot, ReadySet, AutoSol, or AutoRefine, and they do not change
the active workspace, existing `nasolve.txt` files, numbered runs, or current
checkpoints. A second `plan` command refuses to replace the saved plan; use
`status` to inspect it.

An installed copy without a discoverable model catalogue needs the explicit
catalogue root:

```bash
nasolve campaign plan /path/to/campaign --frames-dir /path/to/MR_frames
```

The planner uses the existing NASolve catalogue-selection rules. It deliberately
ignores the machine-local `NASOLVE_MR_FRAMES` environment setting so the
catalogue choice is either explicit or the installed/checkout default. An
invalid explicit directory produces an error rather than selecting a fallback
directory on the machine.

## Dataset selection

A campaign root is an existing directory whose immediate subdirectories hold
the datasets. Running `campaign plan ROOT` discovers children containing any
of the normal input markers: MTZ, `Data_1*.cif`, `summary.html`, or
`nasolve.txt`. An incomplete candidate is retained as `BLOCKED` with its reason;
it does not prevent valid datasets from being recorded.

Selection is sorted and shallow. Existing stage directories, environment
directories and symbolic-link directories do not become datasets. Repeat
`--dataset NAME` to select exact direct children rather than discovering the
whole root. The names must stay within that root.

Dataset discovery reuses the ordinary AutoMR rules: one authoritative MTZ,
one processing metadata CIF, and one summary. The first planner supports the
standard W/5W6W catalogue. Unsupported modes or frames are reported as blocked.
Custom model-provider execution is a later roadmap step.

`DISCOVERED` means input and model selection succeeded. It does **not** assert
that the MTZ contains usable arrays, symmetry agrees, the model passes its full
assessment, a mutation can be constructed, or a structure is solved. Those
remain the existing scientific stage gates.

## Presets and precedence

The built-in `5w6w` TOML preset is versioned separately from the preset schema.
It records the current W-frame policy and five-cycle default refinement
recipe. A local preset can be validated before planning:

```bash
nasolve preset check /path/to/project/preset.toml --json
nasolve campaign plan /path/to/campaign --preset /path/to/project/preset.toml
```

The loader rejects unsupported schema versions, unknown settings, wrong types,
unsupported policies and unsafe resource paths. Optional named resources are
relative to the preset directory and must resolve within it. Presets contain
typed settings; they cannot supply shell commands.

For the settings supported here, precedence is NASolve defaults, then preset,
then explicitly supplied `nasolve.txt` values. An explicitly written `false`
overrides a preset's `true`; an omitted value inherits the preset. Sequences
and explicit mutations use the existing dataset intent parser. The resolved
configuration is stored per dataset, while the original input file is preserved.

Recipe cards may explicitly declare terminal phosphates:

```toml
[chemistry]
terminal_phosphate_sites = ["D:1"]
```

The built-in `5w6w` card version 1.1.0 declares D:1 as part of the designed W
motif, following Simon's explicit confirmation. A custom card must declare its
own list; omission does not authorize any sites. Booleans, broad selectors,
malformed sites and duplicate sites are rejected. The dataset
`[automr] allow_op3_sites` overrides the complete card list, even when explicitly
empty. No option bypasses connectivity checks or constructs a missing phosphate.

Each dataset freezes the effective sites and their origin (`recipe` or explicit
`dataset` override), with recipe id, version and hashes. Plan/status prints
these beside the dataset. Workers use the frozen list after relocation without
reloading today's recipe or catalogue. Old plans do not acquire new permission
merely because the installed built-in card changed.

The campaign executor consumes these frozen declarations. Standalone `-W` /
`frame = W` uses the same **built-in** recipe chemistry, but never an active
campaign's custom preset. Planning does not alter another command's arguments,
source input, stage settings, or existing run.

## Frozen inputs and portable resources

The manifest records input paths, file sizes and SHA-256 checksums, the resolved
preset and its identity, selected models and sequence resources, duplicate
observation groups, and dataset diagnostics. References are anchored to the
campaign root. Selected models, the preset source and declared preset resources
are copied into `NASolveCampaign/resources/`; they remain available after the
source catalogue or custom preset is removed.

The large dataset inputs remain in their existing directories. Freezing records
their identities and checksums; it does not make another copy of every MTZ or
prevent a user editing a file. `campaign status` verifies the frozen references
and reports changed, missing, or unsafe inputs as `DRIFT`.

Move or copy the **whole campaign root**, including dataset inputs and
`NASolveCampaign/`, to preserve these relative references. A status check does
not need the old absolute location, source preset, or source catalogue.

Identical authoritative MTZ bytes are reported as duplicates. The datasets stay
separate because different intended chemistry can remain a meaningful reason
to evaluate the same measurements differently.

New directories added after planning are not silently admitted. Changes that
make a planned dataset's input selection ambiguous, or change the presence of
its configuration, are also integrity concerns. There is no automatic refresh,
repair, or overwrite. A future explicit revision command will manage changes
to an existing plan.

The plan is published only after its resource snapshots are complete. If a
process is interrupted before publication, an incomplete `NASolveCampaign/`
directory may remain. Keep it for inspection; another plan invocation refuses
to overwrite it.

## Status and automation

```bash
nasolve campaign status /path/to/campaign
nasolve campaign status /path/to/campaign --json
```

Status is read-only. The frozen dataset state and the current integrity result
are separate: fixing a blocked input does not silently rewrite the earlier
planning decision. After execution begins, status also reports each dataset's
current attempt, exact run, next stage, checkpoint and diagnostic from the
separate execution record.

| Exit code | Meaning |
| --- | --- |
| `0` | Preset check passed, or all planned datasets were discovered and integrity checks passed where performed |
| `2` | Invalid command/preset/manifest, unavailable campaign, or failed plan publication |
| `3` | Plan/status includes blocked datasets, detected input/resource drift, or execution outcomes needing inspection |

The JSON output includes full diagnostics and checksums. Planning checks only
the stages described above; successful planning does not replace `nasolve check`
or the numerical and structural acceptance gates.

## Execute the saved plan

The [campaign executor](campaign-execution.md) composes one standard W/5W6W
candidate per dataset using the existing scientific stages. It verifies this
same schema-1 plan before running and stores durable progress separately.
Existing plans remain compatible; do not delete or regenerate a plan to use
the executor. Automatic Doctor selection, approval, reporting PDFs and
deposition remain later work.
