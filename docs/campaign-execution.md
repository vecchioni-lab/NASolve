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
The default `autorefine` endpoint still stops for inspection. MR/AutoSol
reviews and technical failures do not acquire Doctor eligibility. A
recommendation remains unselected, and a completed Doctor receipt is not
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

## Current four-member W live validation

A disposable real-environment campaign is currently being used to validate the
coordinator independently of the newer nonstandard-provider path. The sandbox
is `/tmp/NASolve-W-live-20260928` and contains clean top-level copies of:

- `DOHU`;
- `QiC_120325_0513`;
- `QE_120325_0607`; and
- `EG_091325-0302`.

The planning-only phase has now been completed successfully:

```text
4 total
4 DISCOVERED
0 blocked
frozen input integrity OK
runtime: Python 3.12.14 / NARestraints 1.1.2 /
         Phenix 2.2.1 / Coot 1.3.3
```

All four members froze the expected W recipe chemistry with D:1 as the explicit
5-prime-phosphate/OP3 site. No scientific stage had been launched at the time
of that check.

The bounded **PostMR** phase has now completed successfully for all four
datasets. Every member completed preflight, Phaser and PostMR in campaign-owned
`AutoMR/run_001`; campaign and status both exited 0, frozen integrity remained
`OK`, and all four paused at the next conditional AutoSol gate.

The coordinator's generic `next_stage = autosol` display is a stage-boundary
label, not evidence that AutoSol is scientifically required. At execution time,
the stage engine verifies PostMR's anomalous report. If
`autosol_required = false`, it records accepted status `SKIPPED` and does not
launch `phenix.autosol`.

The next live command can therefore simply resume to the ordinary default
endpoint:

```bash
./nasolve campaign run /tmp/NASolve-W-live-20260928
./nasolve campaign status /tmp/NASolve-W-live-20260928
```

A plain campaign run defaults through AutoRefine. This is already unattended
within the fixed built-in stage order: each dataset independently evaluates
conditional AutoSol, skips or runs it as appropriate, then advances to
AutoRefine unless a scientific gate stops that dataset.

The unattended resume has now completed:

- DOHU: AutoSol `SKIPPED`, `SOLVED`, `refine-001`;
- EG_091325-0302: AutoSol `SKIPPED`, `SOLVED`, `refine-001`;
- QE_120325_0607: AutoSol `SKIPPED`, `SOLVED`, `refine-001`;
- QiC_120325_0513: `AUTOSOL_READY`, then `AWAITING_INSPECTION` at
  `refine-001` because numerical refinement acceptance failed. The final
  refinement had Rwork/Rfree = 0.1646/0.1561
  (`Rfree - Rwork = -0.0085`), clashscore 32.23, and a terminal-phosphate
  geometry audit `PASS` with maximum normalized deviation 1.74 sigma. Its
  iodine `B:4` anomalous site refined to f'' = 7.51547 at wavelength
  1.377618 A. `refine-001` remained REVIEW/non-current; current stayed
  `postmr`.

The campaign ended `COMPLETE_WITH_FLAGS` with frozen integrity `OK`.
Run/status exit code 3 correctly represented the QiC review case while the other
three datasets completed independently.

This closes the **real W orchestration smoke validation**. It demonstrates
one-command multi-dataset progression, conditional AutoSol skip/run behavior,
independent dataset stops, exact run/checkpoint ownership and a useful final
solution/review list. It does **not** count as the prepared-nonstandard
geometry-diverse Pine live gate.

Future campaign-recipe work should make the **workflow endpoint and conditional
graph explicit frozen recipe data** rather than leaving the endpoint implicit in
the executor default. Refine Doctor escalation also needs to become a
campaign-owned transition before it is used on a campaign-owned run: standalone
Doctor appends history to `RUN/report.json`, while the completed AutoRefine
campaign receipt intentionally freezes/checksums that report. Running standalone
Doctor after the receipt would therefore appear as out-of-band report drift.
Pine now contains a campaign-owned Refine Doctor bridge with that shape: an
explicit optional `refine-doctor` stage after `AUTOREFINE_REVIEW`, exact
AutoRefine receipt dependency, report-integrity checking, and preserved
non-auto-selection semantics. The default campaign endpoint remains AutoRefine;
Doctor runs only when explicitly continued through the Doctor boundary until
workflow-recipe policy is implemented.

The real QiC campaign continuation has now succeeded: Doctor consumed
`refine-001`, ran `RefineDoctor/ML-fixed-scattering`, and produced
`refine-002` with Rwork/Rfree = 0.1500/0.1502. It returned
`REFINE_DOCTOR_RECOMMEND`, preserved `postmr` as current, and did not
auto-select the candidate. Focused regression passed 4 tests + 4 subtests. After correcting the obsolete
CLI expectation, the campaign executor CLI passed 9 tests + 4 subtests, the
entire campaign family passed 132 tests + 85 subtests, and the full NASolve
regression passed 688 tests + 224 subtests. Patch/doc hygiene also passed.
The campaign-owned Refine Doctor continuation is therefore **regression + live
validated** for its current explicit scope.

The intended workflow-recipe policy is simple at the human level: a recipe may
include **"apply Doctor as needed"** or omit it. Omission leaves an eligible
review as an inspection stop. Opt-in permits the campaign to enter only
validated, bounded stage-specific Doctor transitions when their eligibility
conditions are met. It does not mean "try arbitrary fixes", and it does not by
itself select a Doctor recommendation as current.

The same review/inspection transitions must be operable from both control
surfaces. CLI prompts/commands and future GUI actions are alternate interfaces
to the same backend operations: inspect/open in Coot, yes/no confirmation,
continue from review, inspect Doctor candidates, and explicitly select a
checkpoint.

**Next live campaign stress test:** use the user-local `examples/TestSets/`
folder (roughly nine datasets) as one frozen campaign and execute from MR through
`--through refine-doctor` in a single invocation. Each member should advance
independently through conditional AutoSol, AutoRefine and, only when refinement
lands in review, the campaign-owned Doctor stage. The success criterion is not
"nine green statuses at any cost"; it is one command producing the maximum
scientifically valid set of solved/recommended/inspection outcomes while
preserving any honest blockers.

## Validation limits

Regression tests use controlled stage workers and external-tool fixtures to
exercise dispatch, scientific stops, artifact verification, interruption,
resume and relocation. Pine also exercises prepared nonstandard execution
through the real NASolve stage engines with fixture crystallographic programs,
including relocation, plus a mixed W/nonstandard campaign under one
coordinator.

Real geometry-diverse campaign execution with the user's Phenix/Coot
installations remains the next live gate. The existing standalone DOHU
validation does not by itself validate every campaign recovery path, the QiC
phased path on a new Phenix installation, or a 3-5 member prepared-nonstandard
campaign.
