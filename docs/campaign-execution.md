# Execute a frozen campaign

## Opt-in full-auto exception to guarded stops

[Preset schema 2 full auto](campaign-full-auto.md) adds explicitly frozen review
trial and provisional-selection permissions. The guarded stop/non-selection
rules below continue to describe existing schema-1 recipes and campaigns.
Full auto may trial borderline MR without changing its status, continue without
rejected phases when requested, run bounded Doctor and select its verified
passing recommendation without user approval. CLI `--through` overrides the
recipe endpoint; no endpoint argument uses the frozen recipe default.
The original TestSets plan does not gain these permissions retroactively.


## Explicit Doctor continuation

`--through refine-doctor` applies in the initial run as well as on resume.
A newly reached AutoRefine REVIEW with an eligible preserved checkpoint
continues in the same invocation under the normal receipt/integrity checks.
The guarded default `autorefine` endpoint still stops for inspection. MR/AutoSol
reviews and technical failures do not acquire Doctor eligibility. Under guarded
policy a recommendation remains unselected, and a completed Doctor receipt is not
executed again. Stage-boundary pause requests still take precedence.

The prior post-stage loop used a narrower status-only test than resume;
it now reuses `_runnable(item, through)`. Current validation evidence and
the live QiC result belong in [the handoff](development-handoff.md).

The executor runs one frozen candidate per selected dataset, sequentially,
using the existing AutoMR preflight, Phaser, PostMR, conditional AutoSol and
AutoRefine engines. New schema-2 plans may contain standard W/5W6W members,
prepared nonstandard PDB+sequence members, or both in one campaign. Existing
schema-1 W plans remain readable/executable and need no migration or
replacement.

## First live check

From the NASolve checkout on a Mac with Phenix and Coot configured:

```bash
./nasolve check
./nasolve campaign status examples
./nasolve campaign run examples --dataset DOHU --through postmr
./nasolve campaign status examples
```

The command prints the exact new numbered run owned by this campaign attempt.
Earlier standalone runs remain available. After an **explicit single-dataset**
campaign run completes a viewable stage, NASolve makes that verified run the
**active machine-local Coot workspace**, so the next command can be simply:

```bash
./nasolve show
```

This opens the selected run's **current checkpoint**, or PostMR/Phaser if
refinement is not yet available. To inspect the earlier stage explicitly,
the printed numbered path still works:

```bash
./nasolve show /exact/path/printed/by/campaign/status --stage postmr
```

The active workspace is convenience state, not a scientific checkpoint
selection or approval.

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
`preflight`, `phaser`, `postmr`, `autosol`, `autorefine` or `refine-doctor`.
Without it, the frozen recipe's Doctor policy selects the endpoint; guarded
defaults end at AutoRefine. A stage boundary leaves the attempt paused with its
next stage recorded. A later `run` resumes from that boundary. Requests cannot
admit an unplanned dataset or silently replace a frozen input.

An explicit Phenix installation applies to this invocation:

```bash
./nasolve --phenix-root /path/to/phenix campaign run examples --dataset DOHU
```

The executor uses machine-local external-tool discovery. Its **CLI** makes a
viewable, unambiguous single-dataset run the active machine-local workspace
after the stage boundary, allowing `./nasolve show` with no path. Multi-dataset
runs, blocked/drifted/unviewable results, or
`campaign run --no-activate` do not change workspace selection. Scientific
stage artifacts, frozen inputs, Free-R and the checkpoint registry are never
rewritten. Explicit `show RUN --checkpoint ID` keeps its exact semantics;
Coot windows launched previously may remain open and are not brought forward
or replaced by this shortcut.

For a prepared nonstandard member, execution reconstructs the AutoMR request
only from the checksum-bound campaign resources. It does not rediscover the
source PDB/FASTA, apply W frame/pair chemistry, or reinterpret campaign
membership as model compatibility. Its supplied chain-labelled target is
validated against the frozen search model by the ordinary AutoMR preflight.
Representation ambiguity still stops that dataset for inspection.

## Local inspection stops

| Outcome | Campaign behavior |
| --- | --- |
| Full AutoMR preflight rejected | Record a technical/scientific blocker for this dataset |
| `MR_REVIEW` | Stop this dataset for inspection before PostMR |
| `MR_FAILED` | Record `NO_SOLUTION` for this bounded attempt |
| PostMR fails, or required output validation fails | Preserve the attempt and record its diagnostic |
| No supported anomalous candidate | Record the AutoSol skip and continue ordinary refinement |
| Schema-2 AutoSol policy explicitly disabled with a reason | Record the policy skip without calling AutoSol; refine the PostMR model without experimental phases |
| AutoSol does not return accepted phases | Stop for inspection under the frozen preset's `on_unaccepted = "inspect"` policy |
| `AUTOREFINE_REVIEW` | Preserve the unselected checkpoint and stop for inspection |
| Numerical refinement passes | Record `SOLVED`, the checkpoint, `numerical_success = true`, and `inspection_required = true` |

`SOLVED` is the current numerical workflow outcome. It is not structural
approval or deposition readiness. The normal model compatibility, R-factor,
observation and Free-R checks remain in place. Raw validation scores and
scientific warnings remain in the stage reports. Under guarded policy, Refine
Doctor recommendations are not automatically selected. Full-auto provisional
selection follows only the explicit frozen policy described above.

An explicit AutoSol-disabled skip retains the PostMR anomalous report and
observation/Free-R inputs. The stage receipt and live run report record its
frozen reason and whether nucleotide anomalous candidates were present.
Refinement requires that matching skip and refuses an existing AutoSol
execution/report; the campaign's first-refinement guard also refuses an existing
AutoRefine directory. This fresh path creates phase-free checkpoints for
subsequent Doctor trials. Numerical results against synthetic donor data remain
mechanics evidence, not scientific validation of the proposed chemistry.

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

## Preserved native validation

The historical four-member W campaign completed planning, preflight, Phaser
and PostMR for all four members. Its unattended refinement resume produced
three SOLVED outcomes and a preserved QiC review; the later explicit
campaign-owned QiC Doctor continuation produced a recommendation without
changing current. These checks established the scoped W orchestration path,
not geometry-diverse prepared-nonstandard execution.

The complete dated results, exact historical runtime and test counts are
[archived](history/campaign-execution-2026-10-10-pre-reconciliation.md.txt).
The separately executed four-member full-auto campaign and provisional Doctor
selection are recorded in the [full-auto checkpoint](full-auto-patch-handoff.md).
Neither receipt is a request to repeat a completed campaign. Current remaining
checks are owned by the [development handoff](development-handoff.md).

## Validation limits

Regression tests use controlled stage workers and external-tool fixtures to
exercise dispatch, scientific stops, artifact verification, interruption,
resume and relocation. Pine also exercises prepared nonstandard execution
through the real NASolve stage engines with fixture crystallographic programs,
including relocation, plus a mixed W/nonstandard campaign under one
coordinator.

Real geometry-diverse campaign execution with the user's Phenix/Coot
installations remains a separate live gate. The existing standalone DOHU
validation does not by itself validate every campaign recovery path, the QiC
phased path on a new Phenix installation, or a 3-5 member prepared-nonstandard
campaign.
