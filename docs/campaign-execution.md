# Execute a frozen campaign

The first executor runs one standard W/5W6W candidate per selected dataset,
sequentially, using the existing AutoMR preflight, Phaser, PostMR, conditional
AutoSol and AutoRefine engines. It consumes the immutable schema-1 plan created
by [campaign planning](campaign-planning.md). Existing saved plans need no
migration or replacement.

## First live check

From the NASolve checkout on a Mac with Phenix and Coot configured:

```bash
./nasolve check
./nasolve campaign status examples
./nasolve campaign run examples --dataset DOHU --through postmr
./nasolve campaign status examples
```

The command prints the exact new numbered run owned by this campaign attempt.
Earlier standalone runs remain available. Inspect the new PostMR model using
that printed path:

```bash
./nasolve show /exact/path/printed/by/campaign/status --stage postmr
```

Then continue the same attempt through refinement:

```bash
./nasolve campaign run examples --dataset DOHU
./nasolve campaign status examples
```

Completed, verified MR and PostMR stages are reused. Inspect the reported
checkpoint in its exact run. After the ordinary DOHU path has been checked,
exercise the phased path separately:

```bash
./nasolve campaign run examples --dataset QiC_120325_0513
./nasolve campaign status examples
```

Omitting `--dataset` runs all eligible datasets in the frozen plan. Repeating
the option selects several exact planned names. `--through` accepts
`preflight`, `phaser`, `postmr`, `autosol` or `autorefine` (the default). A stage
boundary leaves the attempt paused with its next stage recorded. A later
`run` resumes from that boundary. Requests cannot admit an unplanned dataset
or silently replace a frozen input.

An explicit Phenix installation applies to this invocation:

```bash
./nasolve --phenix-root /path/to/phenix campaign run examples --dataset DOHU
```

The executor uses machine-local external-tool discovery but does not change
the active workspace. Use explicit run paths when inspecting campaign results.

## Local inspection stops

| Outcome | Campaign behavior |
| --- | --- |
| Full AutoMR preflight rejected | Record a technical/scientific blocker for this dataset |
| `MR_REVIEW` | Stop this dataset for inspection before PostMR |
| `MR_FAILED` | Record `NO_SOLUTION` for this bounded attempt |
| PostMR fails, or required output validation fails | Preserve the attempt and record its diagnostic |
| No supported anomalous candidate | Record the AutoSol skip and continue ordinary refinement |
| AutoSol does not return accepted phases | Stop for inspection under the frozen preset's `on_unaccepted = "inspect"` policy |
| `AUTOREFINE_REVIEW` | Preserve the unselected checkpoint and stop for inspection |
| Numerical refinement passes | Record `SOLVED`, the checkpoint, `numerical_success = true`, and `inspection_required = true` |

`SOLVED` is the current numerical workflow outcome. It is not structural
approval or deposition readiness. The normal model compatibility, R-factor,
observation and Free-R checks remain in place. Raw validation scores and
scientific warnings remain in the stage reports. No automatic Refine Doctor
branch selection is introduced in this executor.

One dataset reaching `BLOCKED`, `NO_SOLUTION` or `AWAITING_INSPECTION` does not
stop other selected datasets. A subsequent `run` does not bypass these states
or automatically select a review checkpoint.

## Pause, interruption and retry

Execution runs in the foreground on macOS/Linux. Keep its terminal session
open while stages run. From a second terminal, request a stage-boundary pause:

```bash
./nasolve campaign pause examples
```

The active stage finishes and its result is recorded before the executor
stops. Another `campaign run` resumes eligible work. A pause request is
separate from a stage failure.

Ctrl-C requests termination of the owned stage process group. Interrupted or
incomplete work is preserved for inspection. If the controller disappears
while a worker is still running, another executor must not start a duplicate
stage. Process/lock records distinguish active work from abandoned attempts;
an uncertain live process prevents retry.

Resume verifies saved results and their checksummed artifacts before reusing
them. It never infers success from an output filename, adopts the newest
unrelated run, or reruns an incomplete stage in place. Inspect the exact run
and diagnostic first. When the prior attempt is no longer active and a fresh
attempt is appropriate:

```bash
./nasolve campaign retry examples --dataset DOHU
./nasolve campaign run examples --dataset DOHU
```

`retry` records a new attempt; it does not launch a stage. The following `run`
starts from preflight and allocates a fresh numbered run. Every old attempt,
log, output and checkpoint remains available. Retrying does not update a
plan's frozen inputs or repair input drift. Plan revision remains a separate
future feature.

## State, integrity and portability

The frozen `NASolveCampaign/plan.json` is unchanged. Execution stores a separate
schema-1 summary at `NASolveCampaign/execution/state.json`, tied to the plan
fingerprint. Per-dataset attempts and stage job/result records live beneath
`NASolveCampaign/execution/datasets/`. Atomic updates and locks prevent
competing campaign invocations from running the same work. Records include
process identity, start time, heartbeat, exact run ownership and diagnostic
evidence for recovery.

Model and sequence resources come from the plan snapshots. The executor
verifies the original authoritative dataset inputs against their frozen
checksums before continuing. Stage reports retain the ordinary immutable run
and checkpoint lineage; campaign progress records refer to exact relative
paths rather than searching by basename.

Stop all campaign processes before moving a campaign. Move the whole campaign
root, including dataset inputs, numbered runs and `NASolveCampaign/`, then
check status at the new location. Local Phenix/Coot configuration belongs to
the current computer; historical process records do not make a live remote
process safe to resume or replace.

## Structured output and exit codes

All campaign commands accept `--json`. `run --json` suppresses progress messages
and prints one final structured record; tool output remains in stage logs.
Status checks read the frozen plan and execution record without launching tools.

| Exit code | Meaning |
| --- | --- |
| `0` | Requested boundary/pause/retry/status succeeded without blocked or inspection outcomes, or numerical refinement passed |
| `2` | Invalid request/state, unavailable campaign, unusable frozen preset resources or conflicting execution |
| `3` | Returned report includes blocked/no-solution/inspection outcomes or input drift |

Exit code `0` does not approve the structure. Read the per-dataset state,
checkpoint, integrity and diagnostic fields when automating the command.

## Validation limits

Regression tests use controlled stage workers and external-tool fixtures to
exercise dispatch, scientific stops, artifact verification, interruption,
resume and relocation. Real campaign execution with the user's Phenix/Coot
installations remains the live check above. The existing standalone DOHU
validation does not by itself validate every campaign recovery path or the
QiC phased path on a new Phenix installation.
