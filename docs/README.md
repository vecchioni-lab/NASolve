# NASolve documentation map

Updated **2026-10-08**. **Start with the
[current development handoff](development-handoff.md)** — the single short
ledger of proven capabilities, remaining Pine gates and *next test*. Read
subsystem contracts only for the subsystem being changed; do not ingest
historical handoffs as current instructions.

## What's current?

- **Current project queue:** [Development handoff](development-handoff.md).
  NARestraints **v1.1.3 is released**; NASolve PR #25 pathless Coot `show`
  is merged and user-live verified; **modified-W Saenger PR #24 remains
  unmerged** despite a successful isolated native Phenix refinement and
  overall human Coot visual PASS.
- **Next chemistry test, after PR #24 integration:**
  [five-member native modified-pair matrix](native-modified-pair-live-validation.md)
  — independent **A:T control, D:T, B:S, Z:P, K:X** datasets in one frozen
  campaign. **Not** D:A, and **not** all four noncanonical pairs in one PDB.
  Missing native component dictionaries remain meaningful blockers.
- **Still required for Pine:** [specific component P2](modified-component-preparation.md)
  true 1W5→DZ/1WA→DP native provenance and the small real
  prepared-nonstandard P5 test. Then final review/merge. After Pine:
  blind AlphaFold geometry campaign, then operational Scout.

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
| Pair recipes, successful Z:P run, five-case next matrix | [Native modified-pair validation](native-modified-pair-live-validation.md) |
| Campaigns and stages | [Campaign architecture](campaigns.md), [planning](campaign-planning.md), [execution](campaign-execution.md), [full-auto recipe](campaign-full-auto.md) |
| Other-family model selection and proposed providers | [Campaign model roadmap](campaign-model-roadmap.md), [model compatibility facts](model-compatibility-facts.md) |
| Operational Scout and eventual ASU/Topo surgery | [Construct registration](construct-registration.md), [registration intent](construct-registration-intent.json), [Scout/Topo live checks](construct-registration-live-checks.md) |
| Future GUI | [GUI contract](gui.md), [GUI live checks](gui-live-checks.md) |
| Proposed metal-coordination builder | [Metal restraint builder](metal-restraint-builder.md), [development intent](metal-restraint-builder-intent.json) — **design, not implemented** |

Implementation-intent JSON is **not** runtime registration authority. The
GUI/Topo/metal-builder designs are future scopes and do not enlarge the
current Pine merge gate.

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
