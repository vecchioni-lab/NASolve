# NASolve documentation map

Updated **2026-11-18** for **`willow`**. Start with the
[current development handoff](development-handoff.md) for the proven edge,
remaining gates and next bounded task. Historical handoffs are evidence, not
current instructions; other branches retain their own status and validation pins.

## What's current?

- **Willow queue:** [Development handoff](development-handoff.md). W128 audits
  Cedar C386's explicit counted-pair path through ordinary AutoRefine: fixed-unit
  one-cycle XYZ protocol, preserved original intent/frame, actual-writer checkpoint
  binding and unselected REVIEW. Willow's numerical library remains W118; the
  shared controller changes belong to Cedar. Broader weighting, phases, chemistry,
  exclusions and physical repair remain open. W122's user-facing sticky-end option
  is still planned. W129 measures a small provider-dependent native angle RMS at
  unchanged coordinates and equivalent complete forces. No actual weight decision was tested;
  semantic geometry classification and broader weighting remain separate gates.
  Earlier arithmetic, lifecycle and continuation evidence lives in the ledgers;
  do not repeat it merely because this current guide is shorter.
- **Audited milestones:** [Generated roadmap](topostitch-roadmap.md) and its
  [machine-readable source](topostitch-roadmap.json). Next human update is W130;
  do not restart completed probes merely because a handoff is shorter.
- **Exact evidence:** [Periodic/native ledger](topostitch-periodic.md) and
  [preview ledger](topostitch-preview.md). These preserve commands, failed
  attempts, compatibility pins and limits; they are not duplicate action queues.
- **Other branches:** inspect current Pine/Cedar/Alder handoffs before integration.
  The [October Pine handoff](history/development-handoff-2026-10-08-pre-consolidation.md)
  and [modified-pair ledger](native-modified-pair-live-validation.md) retain earlier
  chemistry evidence, not a claim about today's other-branch implementation.

## Publication demonstration plan

The [shared publication shortlist](campaign-model-roadmap.md#nasolve-publication-demonstrations)
records A2T7 rotation, ASU recuts combined with bending, standard test data
including DOHU, and metal cases coordinated with Hazel. These are downstream
demonstration goals with explicit evidence gates, not completed-result claims.

## User and contributor reading

- [User guide](../README.md): installed commands, run/view workflows,
  outputs and safeguards.
- [Architecture](architecture.md): stable MR, PostMR, refinement, checkpoint
  and provenance contracts.
- [Collaboration](collaboration.md) and [agent contract](../AGENTS.md):
  workspace, Git safety, artifact handling and one-change review.
- [Changelog](../CHANGELOG.md): changes by implementation date; it does not
  independently authorize experimental chemistry or validate a live run.

## Active subsystem contracts

| Work area | Read here |
| --- | --- |
| Modified residues, CCD aliases and terminal phosphate | [Modified-component preparation](modified-component-preparation.md), [backbone chemistry](backbone-chemistry.md), [sequence-family targets](sequence-family-targets.md) |
| Pair recipes and historical modified-pair native evidence | [Native modified-pair validation](native-modified-pair-live-validation.md) |
| Campaigns and stages | [Campaign architecture](campaigns.md), [planning](campaign-planning.md), [execution](campaign-execution.md), [full-auto recipe](campaign-full-auto.md) |
| Other-family model selection and proposed providers | [Campaign model roadmap](campaign-model-roadmap.md), [model compatibility facts](model-compatibility-facts.md) |
| Operational Scout and eventual ASU/Topo surgery | [Construct registration](construct-registration.md), [registration intent](construct-registration-intent.json), [Scout/Topo live checks](construct-registration-live-checks.md) |
| TopoStitch recut and connection repair | [Audited completion roadmap](topostitch-roadmap.md), [design contract](topostitch.md), [development intent](topostitch-intent.json) — [candidate screen](topostitch-backend.md) and [coordinate adapter](topostitch-coordinates.md), [periodic inspector, saved proposals and read-only representative views](topostitch-periodic.md) and [explicit bend previews and offline comparison](topostitch-preview.md); campaign inference, scheme transfer and repair remain planned |
| Future GUI | [GUI contract](gui.md), [GUI live checks](gui-live-checks.md) |
| Metal-coordination design and intent (check Alder for implementation) | [Metal restraint builder](metal-restraint-builder.md), [development intent](metal-restraint-builder-intent.json) — branch-local design reference |

Implementation-intent JSON is **not** runtime registration authority. Check each subsystem’s audited status and owning branch before treating a design
as implemented or a diagnostic as production qualification.

## Older evidence, not an action queue

- [Full-auto native validation checkpoint](full-auto-patch-handoff.md)
  preserves the earlier four-member real Phenix/Coot results. Its old
  implementation/recovery wording is **not** the current next step.
- [History index](history/README.md) preserves earlier failures, handoffs
  and provenance, including the **exact October 8 pre-prune handoff and
  native pair ledger**. Read these only for forensic questions.
- [October 1 compatibility redirect](development-handoff-2026-10-01-addendum.md),
  [old DOHU validation](validation-dohu.md),
  [old 1AP integration](1ap-phosphate-integration.md) and
  [old Refine Doctor triage](refine-doctor-triage.md) are archived pointers,
  not duplicate sources of live status.

**Status ownership:** handoff = current priorities; native ledger = exact
pair-matrix progress; subsystem contract = actual behavior and safety;
history/Git = how we arrived here. Updating documentation does **not**
change scientific data, frozen inputs, user approvals or runtime capability.
