# NASolve documentation map

Updated **2026-11-23** for **`willow`**. Start with the
[current development handoff](development-handoff.md) for the proven edge,
remaining gates and next bounded task. Historical handoffs are evidence, not
current instructions; other branches retain their own status and validation pins.

## What's current?

- **Current code: W233.** [Before/after stacking comparison](topostitch-preview.md#compare-internal-stacking-between-named-states-w233)
  retains explicit pair/strand correspondence and per-metric missing coverage:
  125 source/125 installed tests, six saved comparisons, no native run.
- **W230:** [Internal stacking placement](topostitch-preview.md#measure-internal-stacking-placement-w230)
  separates per-strand plane orientation, spacing and lateral displacement;
  116 source/116 installed tests, six saved states; full Willow checkpoint
  2481 passed/3 skipped/234 subtests. No force or motion authority.
- **W227:** [Stable core measurements](topostitch-preview.md#keep-the-measured-core-fixed-when-a-window-expands-w227)
  remain comparable when the editable window expands, with complete-mask checks:
  392 source/392 installed tests and three saved-endpoint readback contexts.
- **Reusable optimizer: W226.** [Bounded collective-motion trials](topostitch-preview.md#run-a-bounded-collective-trial-w226)
  qualify six-parameter optimization with exact points, physical units, hard
  budgets and accepted-step/derivative/restoration records: 378 source/378
  installed tests and 26 installed-native checks. No ordinary activation.
  [W218 displacement metrics](topostitch-preview.md#measure-explicit-region-displacement-w218)
  keep centroid, RMS and maximum atom motion distinct from a helix centerline.
- **Successful local receiving control: W217.** [Maintained local proposals survive native recovery](topostitch-periodic.md#w217--recover-installed-local-proposals-after-pdb-rounding),
  with original source chemistry, atom content, fixed context and data retained.
  Both local phosphate sites finish within two native sigmas; general repair,
  residual whole-model geometry and experimental qualification remain open.
- **Shared connection readback: W228.** [Cedar's registered phosphate adapter](topostitch-periodic.md#w228--review-the-shared-registered-phosphate-reader)
  passes 36 independent cold checks; declared bonds, measured symmetry distances
  and actually printed native restraints stay separate. No force or recut grant.
- **Ordinary integration:** W214/W215 bind a real PostMR root and an explicit
  dictionary-only native source; no pairing/motion intent is invented. Cedar
  owns the receiving request and native lifecycle. Read the [current handoff](development-handoff.md).
- **Larger-motion science: W222–W225.** [Collective warm-start and matched receiving refinement](topostitch-periodic.md#w222w225--corrected-collective-warm-start-and-matched-receiving-refinement)
  recover a large synthetic perturbation while preserving sugar handedness.
  The failed direct result and three remaining moving-region outliers stay
  explicit. This is same-family synthetic recovery, not general experimental repair.
- **One audited queue:** [Machine roadmap](topostitch-roadmap.json) and its
  [generated human view](topostitch-roadmap.md). Current W235, next W236:
  [six-atom native closure](topostitch-periodic.md#w235--close-the-local-symmetry-connection-with-all-rings-held)
  retains fixed rings and healthy sugar boundaries. Qualify diffraction receiving
  and residual geometry next; the capped geometry trial is not acceptance.
  The existing two-fixed-flank interval cannot simply grow around the same core.
  Keep the successful synthetic receiving comparison closed. The 5 Å centerline target is separate.
- **Exact evidence:** [Periodic/native ledger](topostitch-periodic.md) and
  [preview/API guide](topostitch-preview.md) retain commands, failed attempts,
  compatibility pins and limits. Do not repeat closed probes because this index
  is shorter; Git and those evidence records retain the earlier W-number history.
- **Other branches:** inspect current Pine/Cedar/Alder handoffs before integration.
  Willow owns periodic helpers and cold reporting, Cedar execution, and Alder
  the maintained metal/map boundary. No implicit merge follows from compatibility.

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
