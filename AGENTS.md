# NASolve agent collaboration contract

These instructions apply to AI agents and human contributors working anywhere
in this repository.

## Before changing anything

1. Run `git status --short`. Generated runs and unrelated dirty files belong to
   their author; never delete, overwrite, or silently absorb them.
2. Read `README.md`, `docs/README.md`, `docs/architecture.md`,
   `docs/development-handoff.md`, `docs/collaboration.md`, and the `Unreleased`
   section of `CHANGELOG.md`. Files under `docs/history/` are evidence, not
   current instructions. Consult the relevant recorded decisions and validation
   evidence before inferring intent; follow the [branch and worktree lifecycle](docs/collaboration.md#branch-and-worktree-lifecycle)
   to keep one active development line and retire completed work promptly.
3. Identify whether the change affects crystallographic behavior,
   compatibility, artifact schemas, portability, or reproducibility.

## Implementation rules

- Preserve immutable numbered runs and checkpoint lineage.
- Never use a host-absolute path as the sole operational reference to a
  committed artifact. Use the run-context anchor/path representation and keep
  absolute paths only as historical provenance.
- Do not search for crystallographic inputs by basename. Rebase only through
  declared run/dataset/repository anchors and verify available checksums.
- Treat generated crystallographic data as potentially unpublished or
  sensitive. Do not upload or commit it without explicit project authorization.
- Keep user-local workspace state out of Git.
- Add an `Unreleased` changelog entry for every user-visible, schema,
  compatibility, portability, or reproducibility change.
- Preserve support for explicit CLI paths when adding workspace shortcuts.
- Default reviewed live-test deliveries to one pasteable subshell joining
  fetch, a full-SHA detached worktree, build and run with `&&`; follow
  [terminal handoffs](docs/collaboration.md#git-delivery-and-terminal-handoffs).
  Keep required install commands as separate one-liners and preserve the
  everyday checkout and all prior deliveries.
- Write generated live-test runners under the everyday checkout's ignored
  `branch-artifacts/<branch>/runners/` directory. Follow the
  [branch artifact archive and merge cleanup](docs/collaboration.md#branch-artifact-archive-and-merge-cleanup)
  policy; inventory and preserve earlier root-level runners before retirement.
- Maintain a short human-facing descriptor for each substantive feature: its
  purpose, behavior, algorithm/tools, evidence, limitations and pipeline role,
  with a methods paragraph and editable figure when these help explain it.
  Update that descriptor and any associated figure/caption in the same change
  whenever the feature's behavior, dependencies or scientific claims change.
  Keep implemented capability distinct from planned work; see
  [documentation roles](docs/collaboration.md#documentation-roles).

## Continuity when new ideas arrive

- Finish the active bounded checkpoint before diverting to a new idea unless
  Simon explicitly asks to stop or switch. When an idea would change active
  scope, state the tradeoff and ask whether to finish the current checkpoint
  and queue it or intentionally switch; do not silently leave work dangling.
- Record new ideas in the relevant maintained job queue with acceptance scope
  and dependencies. An explicit switch still needs an interruption handoff,
  preserved partial outputs and the state/ownership of any active processes.
  Follow [new ideas and active work](docs/collaboration.md#new-ideas-and-active-work).
  This policy applies across NASolve, not only Cedar or CIF Doctor.

## Required validation

- Add a regression test that fails before the change and passes afterward.
- During development, run the affected tests and the relevant focused profile
  with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`. A focused pass is not a full pass.
  Run the unfiltered full suite before branch integration/release, and for
  cross-cutting runtime, schema/provenance, dependency or test-selection changes.
  Record scope, command, result and the last full-tested revision. Follow the
  [testing cadence](docs/collaboration.md#testing-cadence-and-development-profiles).
- For external-tool changes, record the exact Phenix/Coot version and whether
  the check was a dry-run or a complete execution.
- For portability changes, test from a relocated temporary checkout after the
  original path is gone.

## Reviewer handoff

Every handoff or pull request must state:

- behavior before and after;
- changed files and schemas;
- exact validation commands and results;
- compatibility and migration impact;
- generated artifacts included or deliberately excluded;
- remaining limitations and recommended follow-up.

Do not describe a generated run as portable merely because its files are
committed. Its operational references and checksums must also validate after
relocation.
