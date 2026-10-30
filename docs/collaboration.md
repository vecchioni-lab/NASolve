# Collaboration, workspaces, and portable results

NASolve separates machine-local convenience state from reviewable
crystallographic artifacts.

## Documentation roles

The root `README.md` is the human-facing operating guide. `architecture.md` and
the active subsystem documents define durable behavior.
`development-handoff.md` records the current implementation/validation edge and
immediate next work. Superseded integration notes, validation diaries and old
handoffs live under `history/`; they are retained for debugging and provenance
but are not implementation instructions.

See [`docs/README.md`](README.md) for the complete documentation map.

Before diagnosing an established problem or proposing a change, read the current
handoff and the relevant subsystem contract. Follow their links to validation
receipts, history and Git when prior decisions or failed attempts matter.
Use recorded evidence before reconstructing intent from chat memory or inference;
verify it against the actual checkout and name any remaining uncertainty.
Update the smallest authoritative document rather than creating another status
file or appending a session transcript.

Maintain a concise **human-facing feature descriptor** for substantive features
so a user or manuscript author can understand what the software does without
reconstructing development conversations. State the purpose, actual behavior,
pipeline placement, algorithm/tools, evidence and remaining limits. Include a
methods paragraph and editable vector figure when useful; link exact validation
receipts rather than duplicating a changing status ledger. The descriptor is an
explanation of the subsystem contract, not a second operational authority.

When editing a feature, update its human descriptor and associated figure/caption
in the same change whenever behavior, dependencies or scientific claims change.
Distinguish deployed capability, diagnostic demonstrations and future designs.
Use professional, attributable manuscript language and exact software versions;
private collaboration/personality notes stay outside repository documentation.
The [CIF Doctor overview](cif-doctor-human-overview.md) is the first example.

## Continual handoff during active work

At the start of a substantive push, record the current scope, ordered acceptance
milestones, last tested/pushed commit and immediate next action in the maintained
development handoff. Update that same boundary when implementation becomes
reviewable, validation starts or finishes, and publication completes. Record any
active job and its owned output location while it runs; preserve partial evidence
and distinguish implementation complete, tests passing and published.

An interruption must leave enough information to resume from files and Git
without reconstructing intent from chat. Keep scientific evidence and exact
validation commands in the existing evidence ledger, and keep local absolute
paths out of portable operational references. Do not accumulate chat transcripts
or a second competing status document. Open scientific gates remain visible
when priorities change; diagnostic progress never silently closes them.

## Testing cadence and development profiles

Use focused tests while developing a bounded change. Run its new regression,
tests for directly affected callers and shared helpers, then the relevant
profile below. These profiles are reviewable starting points, not automatic
change-impact analysis: a passing chemistry profile cannot cover an unrelated
numerical worker, campaign executor or CLI change. Add those tests explicitly.
A documentation-only change needs appropriate document/link checks, not another
unchanged scientific regression.

From the checkout, with its test-enabled Python:

```bash
.venv/bin/python scripts/run_tests.py smoke
.venv/bin/python scripts/run_tests.py chemistry
.venv/bin/python scripts/run_tests.py workflow
.venv/bin/python scripts/run_tests.py chemistry workflow
.venv/bin/python scripts/run_tests.py delivery
.venv/bin/python scripts/run_tests.py full
```

| Profile | Purpose |
| --- | --- |
| `smoke` | Short checks of source qualification, usable selection, ordinary reuse, checkpoint/path integrity and the test runner itself. |
| `chemistry` | Source graphs/stereochemistry, FANA/enantiomers, attachment operations, linked/end-state preparation, topology and phosphate protections. |
| `workflow` | Qualified storage through ordinary PostMR, source reuse, checkpoints, full-model recipes and campaign coordination. |
| `delivery` | Historical numbered deliveries and probe/shuttle contracts, retained for compatibility and replay. |
| `full` | The entire tests directory, including new files absent from every development profile. |

**C134 audit baseline (2026-10-30, Python 3.12.14 / pytest 9.1.1):**
6,804 cases in 302 files were all collected under tests, not datasets/environments.
Exactly five imported campaign methods were accidentally recollected; fixing the
module import retains their original tests. Ten new regressions give 6,809 cases
in 304 files. All 853 numbered-delivery cases remain. Three text-identical test
pairs use different template readers/fixtures and are intentionally retained;
there are no remaining duplicate collected identities or shadowed test definitions.

Measured focused runs: smoke 139 tests + 6 subtests in 25.95s; chemistry 608 + 10
in 22.93s; workflow 292 + 26 in 30.41s. Full: 6809 passed, 276 subtests passed in 1018.99s (0:16:58).
These are one-machine observations, not performance thresholds. The delivery
profile selects 1,560 cases across 86 files; it is covered by the full run rather
than separately timed. The largest full-run case-time contributors were
`test_cif_recovered_resolution.py`, `test_cif_recovered_torsion.py`, `test_cif_mixed_endpoint.py`.
Exact scope, source hashes and per-file timings are recorded under evidence key
`development_validation_and_postmr_workflow_2026_10_30` in the
[CIF Doctor ledger](cif-linked-native-registration-evidence.json). Future cases
need not preserve these counts; full selection always discovers the complete directory.

Use `--list` to inspect exact file selection without importing tests, or
`--collect-only` to inspect pytest cases. Profiles can be combined without
repeating files; `full` must be used alone. The runner locates its own checkout,
uses the invoking Python, sets `PYTHONDONTWRITEBYTECODE=1` and checkout `src` on
`PYTHONPATH`, and clears inherited pytest addopts so an old `-k`/last-failed option
cannot silently narrow a named suite. It returns pytest's exit status. Missing
profile files are errors. Existing plain `python -m pytest` remains unfiltered.
For individual tests or custom filtering, use pytest directly with the documented
environment rather than calling that result a named full pass.

Run **full regression before merging a branch or releasing**, and when changes
cross shared runtime boundaries, change schemas/provenance, alter dependencies,
or change test discovery/selection. A new external-tool or scientific workflow
also needs its appropriate native evidence; pytest cannot replace that evidence.
A green full baseline may be carried through several focused development commits,
but is invalidated as a merge gate by subsequent source/test/configuration changes.
Rerun the full gate on the final combined state before integration.

Record each handoff's exact scope, command, result, revision and remaining full
or native gates. Do not describe a focused branch push as fully validated. For
one-time timing analysis, append `--junitxml /new/local/path/results.xml`; existing
output is refused. Keep machine timings and generated reports outside Git and
scientific runs. Do not shorten timeout/process-ownership tests or discard
historical replay tests merely to make a faster development loop.

## Diagnostic evidence and student workflow

CIF Doctor diagnostic review receipts are developer-facing evidence. They do
not imply that students must inspect CIF tables or approve chemical repairs.
The [automatic continuation contract](cif-doctor.md#automatic-continuation-and-student-facing-decisions)
requires bounded recovery, automatic usable fallback and plain-language
solution reporting. Preserve hard evidence of unusable chemistry separately
from nonconvergence, pucker changes and descriptive outliers. Keep implemented
selection/report capabilities distinct from pending orchestration/adoption/PDF
integration, and preserve all historical failed diagnostics.

## Git delivery and terminal handoffs

The default user interaction for reviewed live-test deliveries is **one
pasteable terminal block**: a subshell `( ... )` with every dependent command
joined by `&&`. Supply the exact commands and paths, ready to paste from any
working directory. Keep the accompanying explanation short: what the block
does, the expected result and which output or review capsule to return.
Deliver repository-backed code through Git and place generated runners in the
intended project directory.

When an authorized local agent can execute the test and inspect its output,
perform those steps directly and push reviewed source changes through Git.
Do not require the operator to upload/download runners or review ZIPs between
portals. Keep raw evidence local and publish only the bounded technical receipt
and hashes authorized by the project. A generated runner may live outside the
product checkout under an explicit live-test root: pass that path to the builder
with `--output`, omitting `--local-artifact-checkout`. The ignored checkout
layout below remains supported for existing handoffs.

Use this sequence for source-bundled probes:

1. Fetch the named remote branch from an existing build checkout.
2. Create a new, uniquely named detached worktree at the full reviewed commit
   SHA. Resolve and verify that commit before giving the user the block.
3. Build the runner with the explicit existing virtual-environment interpreter,
   declared dependency source checkout and exact new output filename.
4. Run that exact runner with the same interpreter.

This is Git delivery through `fetch` and a pinned worktree, not an instruction
to pull into the everyday checkout. Quote paths, including those using `$HOME`;
do not depend on an activated environment or the terminal's current directory.
Preserve existing everyday-checkout changes, previous scripts, worktrees and
native runs.
If a destination already exists, stop and reconcile it rather than deleting,
resetting or overwriting it to make a repeated block succeed.

`&&` runs the next command only after exit status zero. A nonzero status must
stop dependent steps; do not use unconditional separators or suppress failures.
A diagnostic may deliberately return `REVIEW`/exit 2 after successful native
execution: inspect its receipt and capsule before deciding the next action.
Use separate steps when a later command depends on interpreting an earlier
result or on a user decision. Honor requests for a different interaction style.

When installation is actually needed, supply each required install command
as a separate, pasteable one-liner with a short purpose. Do not add installation
to routine delivery blocks when the existing environment is sufficient.

For user-facing shuttles and returned review capsules, put a short delivery
identifier at the **start** of the filename, for example
`04_Cedar_probe_cif_generation.py`. Leading numbers/letters/plant names remain
visible when file cards truncate the ending. Returned capsules also include
their run token near the front, so repeated executions of one delivery remain
distinguishable. Print and record the same delivery identifier in receipts;
use the exact new filename in the terminal block. Keep previous deliveries
and runs intact; do not rely on Downloads suffixes such as `(1)` to select code.

This command-passage convention is an operational repository contract. Keep it
here and point agent instructions and the current handoff to this section;
private personality handoffs remain outside repository documentation.

## Branch artifact archive and merge cleanup

Generated source-bundled live-test runners belong in the everyday checkout's
`branch-artifacts/<branch>/runners/` directory, for example
`branch-artifacts/cedar/runners/30_Cedar_probe_cif_numerical_recovery.py`.
The root `.gitignore` excludes the whole `branch-artifacts/` tree. Keep the
maintained builders, templates, runtime code, tests and technical evidence
records tracked in their existing locations. Do not commit generated runners,
review ZIPs, native logs, models or a copy of an entire branch into Git.

Delivery commands must create the destination parent as needed, retain unique
numbered filenames and refuse an existing output. Continue using a pinned
detached build worktree; the everyday checkout supplies the interpreter and
ignored runner destination, and is not pulled, reset or switched for delivery.
For an older everyday checkout that has not acquired this ignore rule, the
handoff must first install the same `/branch-artifacts/` rule in that clone's
local Git exclude file, without changing tracked files. Verify the rule with
`git check-ignore` before writing a runner. Never use `git add -f` for this tree.

**Cedar merge cleanup is an explicit outstanding task.** Before retiring Cedar,
inventory the earlier root-level numbered runners and the ignored branch
directory, including each file's original relative path, byte count, SHA-256,
delivery prefix and available build commit/runner receipt. Preserve the
manifest locally with the archive. Archive verified historical runners outside
the product checkout, under an
explicit local live-test/archive root. Retain original relative paths in the
manifest, refuse collisions, and verify all copied bytes and hashes before
removing only those redundant runner copies from the checkout. Keep the original
review ZIPs, run directories and checkpoint lineage accessible at their
recorded locations. Do not relocate an artifact still referenced by an active
job or an operational receipt without updating and checking that reference.

Archive completion does not itself authorize pruning scientific evidence or
local work. Apply the lifecycle audit below before removing disposable build
worktrees or retiring branch refs. Ignored local files survive branch switches
but still need a normal backup; Git does not archive their contents. Never
perform broad directory deletion or a blanket `git clean` as merge cleanup.

## Branch and worktree lifecycle

Prefer **one active development branch and one everyday checkout**. Arboreal
branch names are welcome. Integrate completed, reviewed work into its parent
branch, and the development branch into `main`, as soon as its bounded scientific
and software acceptance gates support it. A longer-lived branch is acceptable;
parallel branches and worktrees need a concrete isolation reason, a named
integration target and a retirement point recorded in the current handoff.
Future features must not become new gates for an otherwise complete change.

Retire completed or explicitly abandoned branches, PRs and disposable worktrees
promptly. Verify exact local and remote heads, integration (including file-tree
or patch equivalence after squash merges), unique commits, active processes,
and tracked, untracked and ignored files first. Preserve scientific runs, source
data, maps, Free-R, environments, unpublished workbooks and local-only work.
Remove only audited disposable worktrees, then their retired branches and stale
references; never force deletion to make housekeeping appear complete.

Keep current branch, integration target, tested commit and remaining gates in
the existing development handoff. Public code, documentation and PR descriptions
use professional language; private collaboration jokes remain in private notes.

## Command available from any directory

The tracked launcher can be linked into an existing `PATH` directory. From the
checkout root, if `$HOME/.local/bin` is already on `PATH`, run:

```bash
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/nasolve" "$HOME/.local/bin/nasolve"
```

The command refuses to overwrite an existing path. Recreate the machine-local
link if the checkout moves. Without a link, use the launcher's absolute path or
run `./nasolve` from the checkout root. This tracked launcher is POSIX-only.
On Windows, use `.\.venv\Scripts\nasolve.exe`; if editable metadata is not
loading, set `$env:PYTHONPATH = (Join-Path $PWD "src")` in PowerShell and run
`.\.venv\Scripts\python.exe -m nasolve`.

## Active workspace

Remember a dataset or a specific run once:

```bash
nasolve workspace use /path/to/dataset
nasolve workspace use /path/to/dataset/AutoMR/run_004
nasolve workspace status
```

After selecting a run, these forms are equivalent to passing the run path:

```bash
nasolve postmr
nasolve autosol
nasolve autorefine
nasolve refine-doctor
nasolve checkpoints list
nasolve checkpoints use refine-001
nasolve show
```

Explicit paths always take precedence. Clear the pointer with:

```bash
nasolve workspace clear
```

A newly allocated standalone AutoMR run becomes active automatically. An
unambiguous **single-dataset `campaign run`** now also makes its verified,
viewable result the active run, so `nasolve show` can open the **current
checkpoint with no path**. A dataset-only workspace selection lets bare
`nasolve show` choose that dataset's latest numbered readable run. Explicit
run/`--checkpoint`/`--stage` requests remain authoritative. Multi-dataset
campaigns and `campaign run --no-activate` preserve the previous active run.
A blocked/unviewable campaign result cannot silently become the active view.
Passing an explicit one-off run to other stages does not by itself change the
saved selection; use `workspace use` when the switch should persist.

The pointer lives in the platform-specific NASolve user configuration. It is a
small JSON value, starts no process, duplicates no crystallographic files, and
uses no persistent RAM. A working directory consumes disk only when tools write
artifacts into it.

Workspace selection does not install an executable. The repository's tracked
`./nasolve` launcher uses that checkout's `.venv` and `src` tree directly, so it
works in a fresh terminal without activation. It also resolves symbolic links,
allowing collaborators to place a link in an existing `PATH` directory when
they want the shorter `nasolve` spelling from elsewhere. The link is
machine-local and should be recreated after moving the checkout.

## Why historical runs failed after cloning

Early reports recorded absolute paths such as
`/Users/collaborator/.../AutoMR/run_004/PostMR/Model/readyset_model.pdb`.
The file could be committed under the new checkout and still be rejected
because the old path no longer existed.

New checkpoint references identify both an anchor and a relative path:

```json
{
  "anchor": "run",
  "relative_path": "PostMR/Model/readyset_model.pdb",
  "sha256": "...",
  "size": 68187
}
```

Top-level observations use the `dataset` anchor. NASolve also rebases legacy
absolute references through the exact `AutoMR/run_NNN` or dataset suffix.
Both POSIX and Windows legacy path forms are understood. Current-checkout
matches take precedence over an old checkout that still exists; arbitrary
basename searches, ambiguous matches, and path escapes are rejected.

Checkpoint schema 2 distinguishes `relative_path` from legacy schema-1
absolute `path` values. NASolve reads schema 1 and migrates it on the next
checkpoint write. New AutoMR reports freeze the authoritative reflection
checksum and, when the selected standard-frame catalogue supplies
`seq_base.txt`, copy it into `Model/` with a portable, checksummed report
reference. Legacy frame runs resolve the exact declared frame directory without
requiring the historical pair-model filename to remain in the catalogue.
Legacy reports without a reflection checksum remain usable, but their root
checkpoint records `legacy-unverified` observation integrity when the registry
is first initialized.

## What to commit

A useful results-bearing commit should include everything needed to inspect or
continue the selected checkpoint:

- run and stage reports;
- frozen effective configuration and parameter files;
- the run-local standard-frame `Model/seq_base.txt` snapshot when present;
- dataset metadata and `summary.html` needed for review and conditional AutoSol;
- the authoritative observation MTZ;
- selected Phaser/PostMR/AutoSol HA/refined models;
- active restraint PHIL/EFF and ligand CIF files;
- checkpoint registry, metrics, and selected map/reflection outputs;
- concise diagnostic logs needed to explain a failure or decision.

Do not routinely commit Coot GUI state, backups, duplicate scratch products, or
every exploratory branch. Logs are ignored globally, so add a diagnostic log
with `git add -f PATH` only after reviewing it for unpublished or
machine-sensitive content.

Before committing a live run, inspect:

```bash
git status --short
git diff --stat
du -sh DATASET/AutoMR/run_NNN
```

Ordinary Git is adequate for the current small fixtures. Adopt Git LFS or
external/private artifact storage when repeated MTZ/map history materially
increases repository size. Do not introduce LFS attributes piecemeal: all
collaborators and CI must be able to hydrate the selected artifacts.

## AI-agent review record

Agents must follow the repository-root `AGENTS.md` and update
`CHANGELOG.md`. The pull-request template mirrors the required handoff so a
reviewer can distinguish source changes, portable artifacts, local-only state,
and remaining external-tool validation.
