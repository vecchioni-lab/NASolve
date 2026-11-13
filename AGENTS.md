# NASolve agent collaboration contract

These instructions apply to AI agents and human contributors working anywhere
in this repository.

## Before changing anything

1. Run `git status --short`. Generated runs and unrelated dirty files belong to
   their author; never delete, overwrite, or silently absorb them.
2. Read `README.md`, `docs/README.md`, `docs/architecture.md`,
   `docs/development-handoff.md`, `docs/collaboration.md`, and the `Unreleased`
   section of `CHANGELOG.md`. Files under `docs/history/` are evidence, not
   current instructions.
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

## Ongoing collaboration

- Keep completed, appropriately validated patches committed and pushed to the
  active feature branch. Do not force-push or merge other branches implicitly.
- Check current related branch changes for interface and shared-file conflicts,
  especially Cedar, before touching shared mechanics. Record unresolved overlap;
  a clean textual merge alone does not establish runtime compatibility.
- Update existing human guides and agent-readable contracts with behavior and
  remaining limits. Prefer one current source of truth over new handoff diaries.
- Avoid unused scaffolding, redundant tests and abandoned scratch directories.
  Remove only task-owned disposable material; preserve others' work and scientific
  evidence. Keep tests that protect distinct behavior or demonstrated failures.
- Challenge assumptions when evidence disagrees; explain the consequence and
  recommend a concrete alternative rather than silently following a mistake.

### TopoStitch milestone audits

For TopoStitch and Pine ASU-slicing work, read `docs/topostitch-roadmap.json`
(the status source) and its generated human view before choosing new work.
At each substantial validated slice, native result, changed assumption, blocker
or handoff, update the affected delivered scope, evidence, status and next action.
Run `python scripts/audit_topostitch_roadmap.py --write` after an audited ledger
edit and `--check` before pushing. The script checks consistency, not scientific
truth; never mark a job complete merely because code exists or tests pass.
Use the ledger's W-number for human progress updates and handoffs. Start at the
recorded `human_updates.next` for a new substantial audited update; never renumber
older entries or increment for a small correction. Keep full Git commits in the
machine ledger, and do not treat a numbered update as scientific acceptance.
Reuse existing Pine, NARestraints, Cedar and campaign owners before adding another
helper. Keep old caveats and failed evidence; Git retains superseded queue states.

## Required validation

- For behavior changes, add a meaningful regression test that fails before the
  change and passes afterward. Documentation-only edits need relevant checks,
  not artificial tests.
- Run focused tests with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`.
  Run the complete suite when global/shared mechanics change; do not repeat it
  for isolated patches without a concrete integration concern. Record scope and
  rationale so focused validation is not mistaken for a full-suite result.
- Verify installation after each substantial code patch, including affected
  entry points and optional dependencies.
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
