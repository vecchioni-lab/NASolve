# NASolve agent collaboration contract

These instructions apply to AI agents and human contributors working anywhere
in this repository.

## Before changing anything

1. Run `git status --short`. Generated runs and unrelated dirty files belong to
   their author; never delete, overwrite, or silently absorb them.
2. Read `README.md`, `docs/architecture.md`, `docs/collaboration.md`, and the
   `Unreleased` section of `CHANGELOG.md`.
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

## Required validation

- Add a regression test that fails before the change and passes afterward.
- Run the focused tests and the complete suite with
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`.
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
