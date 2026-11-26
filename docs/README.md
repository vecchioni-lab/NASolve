# NASolve documentation map

Updated **2026-11-26** for **`willow`**. Start with the
[current development handoff](development-handoff.md) for the proven edge,
remaining gates and next bounded task. Historical handoffs are evidence, not
current instructions; other branches retain their own status and validation pins.

## What's current?

- **Latest code and refinement, W296:** [coupled sugars](topostitch-periodic.md#w296--admit-coupled-sugars-through-the-installed-native-route)
  complete an installed 19-atom trial: join 1.613 Å, improved local angles, six sugar
  hands and 843 held atoms retained. C1′ plane distances improve; weak sugar density,
  residual torsion and held-base tilt remain. Rwork/Rfree 0.313/0.366, unselected.
  3,073 tests + 238 subtests/no skips, 220 installed checks and actual installed
  preflight/fit pass. Source is the 5W6W-derived PDU model, not FT or 8D93.
- **Shared/previous controls:** [W295 source reading](topostitch-periodic.md#w295--share-source-diffraction-reading-with-alder)
  removes Willow/Alder parser duplication; [W294 frame policy](topostitch-periodic.md#w294--complete-ordinary-preflight-with-explicit-frame-roundoff)
  retains old defaults; [W293 derivatives](topostitch-periodic.md#w293--qualify-coupled-forces-and-isolate-native-worker-imports)
  and [W292 scope](topostitch-periodic.md#w292--map-a-coupled-sugar-scope-before-wider-native-motion)
  support the broader receiver. These receipts retain their original limits.
- **W291:** [review a window before motion](topostitch-preview.md#review-a-window-before-generating-coordinates-w291)
  exposes moving residues, fixed anchors/context and links through the normal
  preview command. 161 focused source / 161 relocated-installed checks and the
  complete Willow suite (3,010 tests + 234 subtests, no skips) pass. Genuine PDU
  inspection reports missing declared pairs without inventing a window.
- **W290:** [endpoint-map inspection](topostitch-periodic.md#w290--inspect-the-closed-phosphate-and-its-fixed-sugar-boundary)
  confirms similar density around both recovered phosphates and weak support at
  several fixed sugar atoms. W296 tests the coupled scope;
  complete returned packing acceptance remains open.
- **W288 is the six-atom comparator:** the original 2.824 Å gap recovers to
  1.616 Å near the seeded result at matched coordinate weights. Residual torsions
  and poor diffraction still prevent acceptance. Do not rerun the weight panel.
- **W287:** [saved annotation replay](topostitch-preview.md#reopen-a-saved-annotation-proposal-w287)
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
  their recorded scopes. W290 adds read-only map calculations and 20 cold checks;
  W296 adds the explicit coupled-sugar fit. None of these
  receipts qualifies a combined branch release.

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
