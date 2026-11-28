# NASolve documentation map

Updated **2026-11-28**. Use the subsystem contract for actual behavior, the
[development handoff](development-handoff.md) for the current implementation and
validation edge, and linked evidence for exact scientific claims. Historical
milestone statements preserve their original scope; they are not a second queue.

## Current subsystem navigation

- [Integration handoff](development-handoff.md): active base, qualification and delivery.
- [Metal handoff](metal-development-handoff.md) and [A01–A09 roadmap](metal-development-roadmap.md): metal science and feature milestones.
- [Chemistry handoff](chemistry-development-handoff.md) and [completion queue](cif-doctor-completion-queue.md): shared construction/native chemistry.

Start with the [user guide](../README.md) for a first solve or the
[current behavior JSON](current-behavior.json) for the installed commands,
their inputs and which operations change a model. Use the chemistry table
to check support for a particular modification. [Chemistry capability table](cif-doctor.md#current-capability-boundary).

## What's current?

- **CIF Doctor.** The checked PostMR route constructs the model through Coot and
  NARestraints, checks ReadySet's effective dictionaries and gives ordinary
  refinement the chosen model and restraints. Supported-route preparation,
  failure recovery and handoff have passed their Q04/Q05 controls. Q06 now asks
  which chemical features survive in the returned model. Two PDU replays locate
  the bend in cycle three. The known mixed scaffold has also completed native
  refinement. Held-out chemistry, automatic use across the catalogue and native
  100-dataset capacity remain open. [Current handoff](development-handoff.md) ·
  [Work order](cif-doctor-completion-queue.md#pipeline-position) ·
  [Support by chemistry](cif-doctor.md#current-capability-boundary).
- **Captured reader settings.** Cedar can carry four reviewed Phenix settings
  separately from geometric restraints. Consult the scope for the particular
  parent and consumer before transferring a canonical result to a modified or
  metal-containing site. [Explicit captured settings](cif-doctor.md#explicit-captured-control-handoff-w186).
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
- **Release integration:** Alder receives the shared NASolve 0.2.0 candidate
  while retaining its metal milestones. [Compatibility checks and delivery](metal-release-compatibility.md)
  distinguish branch qualification from scientific acceptance. The
  [worked examples](../README.md#inspect-a-sticky-end-or-a-phosphate-across-symmetry)
  cover complementary ends and explicitly declared crystal phosphates.
- **Future inputs:** ChemDraw-derived chemical references/restraint bundles remain
  planned. Exact packaged chemical references and explicit DNA source composition
  are implemented; explicit ordinary DY target/per-site construction is connected. Automatic
  selection and pairing rules remain separate. Drawing-to-model construction is outside CIF Doctor. Sticky-end repair,
  blind AlphaFold prerequisites, Scout/Topo and the metal GUI retain their separate
  scopes and do not enlarge this chemistry checkpoint.

For a scientific or numerical claim, follow the [CIF Doctor evidence ledger](cif-linked-native-registration-evidence.json)
or the named subsystem receipt. The [human overview](cif-doctor-human-overview.md)
is an explanation, not an independent status ledger.

## User and contributor reading

- [User guide](../README.md): installed commands, run/view workflows,
  outputs and safeguards.
- [Preparing an X-ray deposition for OneDep](pdb-deposition.md) covers the
  paired Phenix CIFs, Free-R checks, modified components and returned coordinates.
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
| GUI design and initial metal viewer | [GUI contract](gui.md), [local saved-results viewer](metal-anomalous-doctor.md#implemented-local-saved-results-viewer), [Coot/map inspection and chemistry drafts](metal-anomalous-doctor.md#implemented-native-trial-map-and-coot-inspection), [GUI live checks](gui-live-checks.md) |
| Bounded coordinate diagnostics | [Feasible search and derivative checks](topostitch-feasible-diagnostics.md) — explicit pure Python helpers; native/source/output authority remains with callers; no default activation or model adoption |
| Metal-coordination authoring core | [Metal restraint builder](metal-restraint-builder.md), [development intent](metal-restraint-builder-intent.json) — one to three metals and extensible cluster graphs; **recipe/binding/preview, generated-W integration and explicit metal-model construction/replay and bounded recipe-only preparation implemented; GUI/whole-model optimization planned** |
| Experimental metal screen and XYZ review | [Metal-screen workflow](metal-screen.md) — phase-restrained XYZ API with [explicit weight controls](metal-anomalous-doctor.md#implemented-explicit-xyz-weight-controls), [iteration allowances](metal-anomalous-doctor.md#implemented-explicit-refinement-iteration-allowance) and refined B/fdp diagnostic bridge; planned AutoSol/campaign integration and scientific qualification |
| Metal development queue and storage | [Post-merge roadmap A01–A09](metal-development-roadmap.md), [campaign storage plan](metal-campaign-storage.md) — FT_Hg foundation, GUI co-design, experimental-input reconstruction and [explicit parent transport](metal-campaign-storage.md#implemented-fourth-step-explicit-parent-layout-transport) before large campaigns; scientific retirement remains unqualified |
| Metal anomalous diagnostics and planned search | [Metal anomalous workflow](metal-anomalous-doctor.md) — frozen occupancy profiles, [budgeted solution search](metal-anomalous-doctor.md#solution-space-search-and-provisional-decisions), optional chi branches, overlapping site groups and [recoverable trial retention](metal-anomalous-doctor.md#disk-budgets-and-recoverable-trial-retention) planned; **single frozen trials, [matched cluster response comparisons](metal-anomalous-doctor.md#implemented-matched-cluster-response-comparisons), [grouped cross-geometry reviews](metal-anomalous-doctor.md#implemented-grouped-reviews-across-geometry-branches), [completed-state XYZ maps and numerical context](metal-anomalous-doctor.md#implemented-completed-state-xyz-map-capture), [frozen-fdp anomalous maps](metal-anomalous-doctor.md#implemented-frozen-fdp-anomalous-map-capture), [native fit and endpoint recipe diagnostics](metal-anomalous-doctor.md#implemented-native-fit-and-endpoint-recipe-diagnostics), [shared cluster B environments](metal-anomalous-doctor.md#implemented-shared-cluster-b-environments), [refined endpoints and cluster count evidence](metal-anomalous-doctor.md#implemented-refined-endpoint-diagnostics-and-cluster-accounting), matched endpoint comparisons, [bounded occupancy sweeps](metal-anomalous-doctor.md#implemented-bounded-occupancy-sweeps), [human reference snapshots](metal-anomalous-doctor.md#implemented-human-reference-snapshots), [offline workbench navigation](metal-anomalous-doctor.md#implemented-offline-workbench-controller) and offline replay implemented; adaptive scan orchestration, convergence qualification and decision logic planned** |

The release guide lists commands available on main. The implementation blueprints
and experiment ledgers record design decisions and observations. Willow's additional
recut tools and Alder's metal-site tools have their own branch guides. The
[completion queue](cif-doctor-completion-queue.md#pipeline-position) tracks the
remaining Cedar chemistry.

## Older evidence, not an action queue

- [Full-auto native validation checkpoint](full-auto-patch-handoff.md)
  preserves the earlier four-member real Phenix/Coot results. Its old
  implementation/recovery wording is **not** the current next step.
- [History index](history/README.md) preserves earlier failures, handoffs
  and provenance, including verified Git originals and local snapshots from October, and the full November 25 handoff and queue. Read these only for forensic questions.
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

Environmental metal B preparation, trial grouping and camera behavior are
described in the [metal anomalous methods](metal-anomalous-doctor.md#implemented-environmental-metal-b-preparation).
