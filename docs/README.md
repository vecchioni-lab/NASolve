# NASolve documentation map

Updated **2026-11-26** for **`willow`**. Start with the
[current development handoff](development-handoff.md) for the proven edge,
remaining gates and next bounded task. Historical handoffs are evidence, not
current instructions; other branches retain their own status and validation pins.

## What's current?

- **W289:** [compact Willow/Pine handoff](development-handoff.md) distinguishes
  branch-available tools, local experiments and the remaining integrated workflow.
  The [roadmap](topostitch-roadmap.md) is the only milestone/action queue.
- **Latest science, W288:** [matched coordinate weights](topostitch-periodic.md#w288--the-original-pose-catches-up-under-matched-coordinate-weights)
  let the original 2.824 Å gap recover to 1.616 Å near the seeded result. Residual
  torsions and poor diffraction prevent acceptance. Next inspect exact model/map
  pairs before widening the movable region; do not rerun the panel.
- **Latest maintained code, W287:** [saved annotation replay](topostitch-preview.md#reopen-a-saved-annotation-proposal-w287)
  reproduces an explicit review from bound original inputs. 81 source / 81 installed
  checks at that checkpoint; no metadata application or scientific approval.
- **Pine output:** whole-original-asym diagnostic CIF save/replay/inspection is
  available through the explicit cut-preview/view commands. Mixed-fragment entity
  policy, ordinary parent/TLS restart and persistent human operation/refine loop
  remain separate gates. [Scope](topostitch.md).
- **Shared owners:** Willow/Pine supplies topology/motion/review; Cedar owns chemistry
  and ordinary runtime; Alder owns protected metals and parameter authority. Check
  those branches before integration. Local Pine still lacks Willow's five extra
  entry points; a branch install is not a merged release.
- **Exact history:** [periodic/native evidence](topostitch-periodic.md) and
  [preview/API contracts](topostitch-preview.md) retain methods, failures and pins.
  Earlier synthetic recovery, native controls and software PASS results retain
  their recorded scopes. No new tests or experiments were run in this docs audit.

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
| Future GUI and shared dynamic inspection | [GUI contract](gui.md), [shared 3D inspector](architecture.md#shared-in-app-modeldensity-inspector), [GUI live checks](gui-live-checks.md) |
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
