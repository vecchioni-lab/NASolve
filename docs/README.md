# NASolve documentation map

Updated **2026-11-13**. Use the subsystem contract for actual behavior, the
[development handoff](development-handoff.md) for the current implementation and
validation edge, and linked evidence for exact scientific claims. Historical
milestone statements preserve their original scope; they are not a second queue.

## What's current?

- **CIF Doctor:** start with the [scientific work map](cif-doctor-completion-queue.md#pipeline-position).
  The checked preparation can use ordinary Coot/NARestraints inputs and complete
  dictionary repair plus ReadySet. [Truthful preparation reporting/recovery](cif-doctor.md#checked-preparation-and-honest-recovery-c220)
  is now available through `postmr --checked-preparation`; it saves the checked
  result as the initial review checkpoint. Schema-2 campaigns can explicitly choose
  the same route. New checked requests save compact, exact evidence; explicit
  retirement of successful working duplicates now preserves stable public paths
  and recovers interrupted cleanup. C260 connects new ordinary/campaign callers; broader campaign-scale
  resource acceptance and historical-campaign migration remain separate. Complete requests can
  reuse exact completed plane support or explicitly opt into graph-selected support
  generation. `cif-doctor prepare-run --automatic-plane-support` now exposes that
  choice with exact-result notes. Checked PostMR and schema-2 campaigns also forward
  this explicit choice. Publication and campaign status show verified generation
  notes without changing old receipts. C249 separately reports explicit planes in
  the exact selected dictionaries; native modifications, alternative restraints
  and achieved geometry remain unassessed by that screen. C251 adds explicit later
  preparation alternatives with unchanged root/current choice and exact Coot/
  refinement inputs. C253 binds chosen-model AutoSol site validation while preserving
  original-MR phasing; native AutoSol acceptance remains open. C263 binds an explicit
  prepared-input recipe to original chemical authority; isolated 1AP/5IU acquisition
  and relocated cold reads pass without changing ordinary defaults. C252 validates real two-attempt publication, relocated Coot/
  refinement inputs and preservation of a later manual choice. Alternative-aware phasing,
  real refinement and broader chemical controls remain open. Read the
  [short handoff](development-handoff.md) for validation and the next action,
  the [human overview](cif-doctor-human-overview.md) for the explanation, and the
  [capability table](cif-doctor.md#current-capability-boundary) for support limits.
- **Whole-model restraints:** the [full-model recipe](full-model-restraints.md)
  implements `restraint_scope = all`. The L-3GBI control passes mirror/round-trip,
  MR and ordinary PostMR native membership. Chemical-state/refinement and symmetry
  end-pair qualification remain separate.
- **Modified pairs:** [native validation](native-modified-pair-live-validation.md)
  owns the 42-target preflight/Phaser/PostMR evidence and remaining pair-matrix
  cases, including the separate source-native P2 and geometry-diverse P5 work.
- **Campaign orchestration:** the [full-auto checkpoint](full-auto-patch-handoff.md)
  preserves completed GeoTest execution evidence; orchestration success does not
  settle its scientific reviews. [Campaign contracts](campaigns.md) define runtime.
- **Integration:** work continues on cedar, with pine as the proposed integration
  target. A provisional merge can ship bounded, explicit functionality before the
  whole catalogue programme is complete, but needs its own integration review.
  No document update authorizes a merge or promotes diagnostic chemistry.
- **Future inputs:** ChemDraw-derived chemical references/restraint bundles remain
  planned; drawing-to-model construction is outside CIF Doctor. Sticky-end repair,
  blind AlphaFold prerequisites, Scout/Topo and the metal GUI retain their separate
  scopes and do not enlarge this chemistry checkpoint.

For a scientific or numerical claim, follow the [CIF Doctor evidence ledger](cif-linked-native-registration-evidence.json)
or the named subsystem receipt. The [human overview](cif-doctor-human-overview.md)
is an explanation, not an independent status ledger.

## User and contributor reading

- [User guide](../README.md): installed commands, run/view workflows,
  outputs and safeguards.
- [Architecture](architecture.md): stable MR, PostMR, refinement, checkpoint
  and provenance contracts.
- [Collaboration](collaboration.md) and [agent contract](../AGENTS.md):
  workspace, Git safety, artifact handling and one-change review; default
  [one-block conditional Git delivery](collaboration.md#git-delivery-and-terminal-handoffs)
  and separate install one-liners.
- [CIF Doctor completion queue](cif-doctor-completion-queue.md): dependency-ordered
  integration, chemistry-transfer, reporting and release jobs, with the C00–C150
  orphan-work audit and explicitly deferred extensions.
- [Development test profiles](collaboration.md#testing-cadence-and-development-profiles):
  focused smoke/chemistry/workflow checks, retained delivery compatibility and
  the unfiltered full integration gate.
- [Changelog](../CHANGELOG.md): changes by implementation date; it does not
  independently authorize experimental chemistry or validate a live run.
- [CIF Doctor human/manuscript overview](cif-doctor-human-overview.md): purpose,
  algorithm/tools, pipeline placement, methods wording and an editable figure.
  Human feature descriptors and their figures are maintained alongside feature
  changes under the [documentation convention](collaboration.md#documentation-roles).

## Active subsystem contracts

| Work area | Read here |
| --- | --- |
| Modified residues, CCD aliases and terminal phosphate | [Modified-component preparation](modified-component-preparation.md), [backbone chemistry](backbone-chemistry.md), [sequence-family targets](sequence-family-targets.md) |
| CIF Doctor runtime and planned extensions | [Human/manuscript overview and figure](cif-doctor-human-overview.md), [commands and implemented scope](cif-doctor.md), [public CCD controls](cif-doctor-ccd-controls.json), [audit methods and review boundaries](cif-restraint-audit-methods.md), [machine-readable implementation map](cif-restraint-doctor-implementation.json) |
| Pair recipes, successful Z:P run, combined four-family native evidence | [Native modified-pair validation](native-modified-pair-live-validation.md) |
| Campaigns and stages | [Campaign architecture](campaigns.md), [planning](campaign-planning.md), [execution](campaign-execution.md), [full-auto recipe](campaign-full-auto.md) |
| Fresh synthetic DNA challenge | [Human overview, recipe, shuttle and evidence limits](synthetic-dna-mechanics-test.md) |
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

**Status ownership:** completion queue = remaining priorities and acceptance;
handoff = current implementation/validation/publication edge; subsystem contract
and support matrix = actual behavior; evidence ledgers = exact results;
history/Git = how we arrived here. Dated milestone methods and old `Next` paragraphs
are evidence-time snapshots, not additional task queues. Documentation updates
change no scientific data, frozen inputs, user approvals or runtime capability.
