# NASolve documentation map

Updated **2026-10-10**. Start with the
[current development handoff](development-handoff.md) for completed checks,
remaining bounded gates and the next native action. Read subsystem contracts
for actual behavior; history is evidence, not a second task queue.

## What's current?

- **Completed:** NARestraints v1.1.3; merged W Saenger overlay and pathless
  viewing; installed generic CCD lookup; combined 42-target preflight,
  Phaser and PostMR; generic linkage diagnostic and exact custom-restraint
  coverage. [The native ledger](native-modified-pair-live-validation.md)
  owns returned counts, dictionary hashes and evidence paths.
- **Current trial:** repaired 5CM/DF native interpretation passed and bounded
  geometry minimization completed awaiting review. The target fell 97.45% and
  all chirality signs survived; original inputs and the manager were preserved.
  The user reports Coot visual PASS for all modified pairs. A separate DP
  angle/plane repair now has an audited v2 candidate after successful installed
  parser preflight/generation. Next is native interpretation with complete
  B:4 linkage in a fresh diagnostic. Adoption, full numerical qualification,
  convergence and fresh ordinary full auto remain open.
- **Still separate:** source-native 1W5→DZ/1WA→DP P2 and geometry-diverse
  real P5, followed by bounded integrated review/merges.
- **Queued:** deterministic SMILES/CIF assessment, then separately tested
  policy-bounded generation/validation and continuation, after the current
  geometry trial and before Topo/Scout. PDB + coordinate mmCIF and explicit
  trusted-model / no-sequence input are requested prerequisites for the blind AlphaFold
  baseline, not implemented options. The baseline remains after Pine
  close-out and before operational Scout.

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
| Proposed automated CIF/restraint checks | [Audit methods and review boundaries](cif-restraint-audit-methods.md) |
| Pair recipes, successful Z:P run, combined four-family native evidence | [Native modified-pair validation](native-modified-pair-live-validation.md) |
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
  and provenance, including **exact October 8 and October 10 pre-reconciliation
  snapshots**. Read these only for forensic questions.
- [October 1 compatibility redirect](development-handoff-2026-10-01-addendum.md),
  [old DOHU validation](validation-dohu.md),
  [old 1AP integration](1ap-phosphate-integration.md) and
  [old Refine Doctor triage](refine-doctor-triage.md) are archived pointers,
  not duplicate sources of live status.

**Status ownership:** handoff = current priorities; native ledger = exact
pair-matrix progress; subsystem contract = actual behavior and safety;
history/Git = how we arrived here. Updating documentation does **not**
change scientific data, frozen inputs, user approvals or runtime capability.
