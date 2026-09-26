# NASolve documentation map

NASolve documentation is organized by role, not chronology.

## Start here

- [`../README.md`](../README.md) — human-facing overview, installation,
  normal commands, and why the major safeguards exist.
- [`architecture.md`](architecture.md) — durable implementation contracts,
  artifact/checkpoint invariants, and stage responsibilities.
- [`development-handoff.md`](development-handoff.md) — current validated state,
  immediate next work, active scientific caveats, and known blockers.
- [`collaboration.md`](collaboration.md) — workspace, portability, Git, and
  artifact-handling rules.

## Active subsystem contracts

- [`sequence-family-targets.md`](sequence-family-targets.md) — explicit
  sequence-reference target assembly, standalone AutoMR/PostMR integration, and
  campaign sequence-thread inheritance.
- [`backbone-chemistry.md`](backbone-chemistry.md) — phosphodiester,
  terminal-phosphate, and unsupported-backbone policy.
- [`campaigns.md`](campaigns.md) — campaign orchestration contract.
- [`campaign-planning.md`](campaign-planning.md) and
  [`campaign-execution.md`](campaign-execution.md) — current campaign stages.
- [`model-compatibility-facts.md`](model-compatibility-facts.md) — descriptive
  search-model, checkpoint-candidate, and donor-to-recipient compatibility
  provenance; no donor eligibility or automatic reuse.
- [`construct-registration.md`](construct-registration.md) — logical
  construct-to-coordinate registration design plus the current Birch core/Scout
  implementation boundary; [`construct-registration-intent.json`](construct-registration-intent.json)
  records the machine-readable inference policy and validation checkpoint.
- [`campaign-model-roadmap.md`](campaign-model-roadmap.md) — forward-looking
  model/sequence/processing architecture and the current Campaign Doctor
  implementation boundary.

Machine-readable schemas and small recipe examples beside these files are part
of the active contract.

## History

[`history/`](history/) contains superseded validation diaries, integration
notes, and old handoff snapshots.

These files are retained because they can explain regressions, failed approaches,
and why later contracts exist. They are evidence, not instructions.

When history and active documentation disagree, use the active documentation,
current tests, and current code as authoritative. Git history remains the
fine-grained chronology.
