# Campaign model, sequence, and recovery roadmap

Status: design addendum for the campaign architecture. This document narrows the next development direction without replacing `campaigns.md`. It is deliberately broader than the current single-scaffold 5W6W execution slice.

## Goal

Campaigns must support both closely related construct series and genuinely heterogeneous structure families. NASolve must not assume that every dataset in a campaign differs only by sequence or chemistry. A campaign may contain:

- one search scaffold with many sequence or modified-site variants;
- several related search models with small geometric changes;
- different space groups or copy-number expectations;
- per-dataset models generated from sequence by a model provider such as AlphaFold;
- experimentally solved models that later become useful search models for unsolved siblings; or
- mixtures of these cases within one campaign.

The human-facing configuration should stay simple even when the frozen internal record is rich.

## Experimental families and scientific extension boundaries

A campaign groups related experiments; shared sequence is one possible family
relationship, not a required campaign property. Explicit design metadata may
instead identify shared geometry, topology or discrete construction parameters.
Different family types may coexist in a campaign under an applicable project
policy. The current sequential executor remains its narrower implemented slice.

Keep three responsibilities separate:

- experiment definition: declared invariants, variable parameters and explicit
  dataset/thread membership;
- model provision: how candidate coordinates are selected, generated or
  transformed for a member;
- reuse eligibility: what permits an artifact from one member to seed another.

Family membership is not evidence of MR-model compatibility. Sequence-defined
families use explicit chain/residue correspondence; geometry/topology-defined
families may use other reviewed providers and compatibility rules without a
shared sequence or coordinate template. Compact design metadata identifies
intent, not proof that generated coordinates satisfy it.

The immediate sequence-defined case is the W-scaffold chemistry series:
compile a reviewed scaffold sequence and dataset/thread site declarations into
one effective residue target. Using the metal-adapted W reference does not
request metal atoms or validate metal coordination. Watson-Crick-like
proof-of-principle restraint policies and explicit metal-pair hypotheses belong
to distinct reviewed project policies; component identity alone establishes
neither pairing geometry nor metal occupancy.

A separate metal-pair project can later add declared metal-site construction,
coordination candidates, restraints and evidence checks. Existing multi-candidate
budgets and inspection rules apply; the ordinary WC-like path must not silently
become a metal-site inference engine. Broader geometry/topology providers remain
later extensions, not prerequisites for the present sequence-family work.

[Sequence-family target assembly](sequence-family-targets.md) records the
compiler and explicit opt-in standalone AutoMR/PostMR integration, including
its pending live-validation boundary. General campaign-family orchestration,
thread binding and campaign reference snapshotting remain separate work;
campaign planning does not silently discard a selected sequence reference.

## Three scientific state layers

For sequence and chemistry, NASolve should reason in three layers.

### 1. Search-model state

This is what the actual MR model contains. It is the lowest-authority starting state and must be recorded exactly. It may have a different sequence from the intended construct and may lack chemistry that PostMR is expected to install.

The search model is not silently edited before Phaser merely to resemble the target construct. Differences are recorded and reconciled after MR unless a reviewed MR-model-generation policy says otherwise.

### 2. Frame/reference state

A frame or model-family recipe may provide a reference sequence and other expected scaffold properties. This describes the baseline construct family, not necessarily the literal sequence of every search-model PDB.

For a shared family, the campaign may optionally provide a campaign-level reference sequence. A dataset may override it. Neither is mandatory for campaigns whose datasets use unrelated models.

Reference-sequence information is strongly recommended where available because it enables model validation, explicit mutation planning, and later deposition checks.

### 3. Dataset target state

This is the authoritative intended construct for one dataset. It may be assembled from:

- a dataset sequence;
- an inherited campaign/reference sequence;
- explicit site mutations;
- modified-residue identities;
- terminal chemistry such as 5-prime phosphate;
- backbone chemistry declarations; and
- other reviewed site-specific chemistry.

Ordinary sequence and explicit site chemistry are one authority layer. When both address the same site, the explicit site declaration wins because it contains more chemical information.

NASolve should compile these inputs into one effective target before PostMR and then execute only the delta between the actual MR model and that effective target. It should not blindly mutate through several intermediate sequence layers.

Every overridden value remains visible in provenance, for example:

```text
MR model: DA
frame/reference: DA
dataset sequence: DG
explicit site chemistry: 1AP
effective PostMR target: 1AP
```

## Simple human-facing sequence input

The common case should require almost no path configuration.

A dataset directory may contain a conventionally named sequence file, discovered automatically. A campaign may also declare a shared/reference sequence for a family of datasets. Dataset sequence input overrides the inherited campaign/reference sequence.

The exact filename and syntax remain to be finalized, but users should not normally need to point each campaign entry at a text file. Large campaigns can be organized by ordinary external scripting rather than turning NASolve into a file-management system.

Chain-labelled sequence is preferred in the durable schema. Existing unlabeled frame resources such as `MR_frames/5W6W/seq_base.txt` may remain provenance inputs, but a reviewed preset should resolve them to explicit chain identities before execution.

## Sequence comparison policy

Before Phaser, NASolve should compare the selected search model against any applicable frame/reference sequence and record:

- chain inventory and lengths;
- residue identities;
- exact mismatch sites;
- whether mismatches are expected to be corrected after MR; and
- the final effective dataset target.

A residue-identity mismatch is not automatically a bad MR model. A model may be a valid scaffold with the wrong construct sequence. Chain topology or length incompatibility is a stronger error and may block the run unless the preset explicitly supports that transformation.

PostMR applies the final effective target only after MR succeeds.

## Mirroring

`mirror = true` remains the simple human-facing D/L chirality switch.

Mirroring is orthogonal to sequence and chemistry. It changes the chirality of the selected search scaffold before Phaser; it does not itself change the intended sequence, modified-residue identity, terminal chemistry, or dataset target.

Configuration precedence remains dataset-specific: a dataset may override a campaign or preset mirror default in either direction.

## Model-provider hierarchy

Campaigns must not assume one catalogue model for all datasets. A dataset may obtain its MR candidate from a reviewed model provider. Planned provider classes include:

- fixed reviewed catalogue model;
- bounded catalogue/model library;
- explicit dataset-supplied model;
- campaign-shared model;
- sequence-derived model, including a later AlphaFold provider;
- model generated or transformed from a reviewed template; and
- model promoted from a solved sibling dataset by Campaign Doctor.

Every provider must record the source sequence/model, provider version or identity, transformation, checksums, and the exact model submitted to Phaser.

Different datasets in one campaign may use different providers.

## Geometry-rich campaigns

A future campaign may contain related assemblies whose differences are geometric rather than merely sequence-based. One planned example is a family of triangular DNA constructs with different shapes, space groups, and small geometric adjustments.

For such campaigns NASolve should support:

```text
sequence / construct specification
        -> model provider
        -> dataset-specific search model
        -> AutoMR
        -> PostMR target chemistry
```

The campaign may share design logic while each dataset has its own model, expected symmetry, and MR state. The campaign schema must therefore avoid encoding "one frame model plus mutations" as a universal assumption.

## Campaign Doctor: cross-dataset model rescue

Campaign Doctor is a future recovery layer above the existing stage-specific Doctors. Its purpose is to use information learned from solved datasets to generate bounded rescue candidates for related unsolved datasets.

Potential reviewed operations include:

- use a solved sibling structure directly as an MR model when construct compatibility permits;
- mutate a solved sibling toward the failed dataset's effective target before using it as a search model;
- use several solved siblings as a bounded MR library;
- build an ensemble from structurally related solved siblings;
- prefer a solved model with matching geometry, space group family, or construct class;
- feed a solved model back into a model-provider pipeline for a nearby design; and
- retry MR under a preset-declared budget.

This must be provenance-rich and bounded. Campaign Doctor must record which solved dataset supplied the parent model, what sequence/geometry transformations were applied, how many rescue candidates were tried, and why each candidate was eligible.

It must never silently treat one dataset's solution as ground truth for another.

A donor solution supplies a search candidate, not recipient evidence. A rescue
must record the exact donor dataset/checkpoint and model checksum, the recipient
identity, compatibility checks, transformations and search budget. The recipient
retains its own authoritative observations, Free-R flags, effective construct
target and scientific gates; donor occupancy, metal assignment or approval must
not be inherited as experimentally established facts about the recipient.

A solved related model may therefore prime a fresh MR attempt for a failed
dataset, but must not rewrite that failed branch or replace the recipient's
intended construct. Numerical success alone is not universal donor eligibility;
the applicable project rule determines which source checkpoints may be used.

## Cross-dataset compatibility

Before reusing a solved model for another dataset, Campaign Doctor should eventually evaluate explicit compatibility dimensions rather than simple filename similarity. These may include:

- chain count and polymer topology;
- intended sequence and modified-site compatibility;
- chirality;
- construct/model-family identity;
- expected oligomeric or geometric class;
- symmetry/copy-number expectations;
- known terminal or backbone chemistry; and
- user/preset-declared family relationships.

The exact scoring/eligibility rules are deferred until a real heterogeneous campaign is available. Early implementations should prefer explicit family declarations and conservative hard gates over inferred similarity.

## DAG implications

The campaign execution graph must permit both shared and dataset-specific parents.

Examples:

```text
shared reference sequence
├── dataset A -> model A -> MR -> solved A
├── dataset B -> model B -> MR failed
└── dataset C -> model C -> MR -> solved C

Campaign Doctor:
solved A ----\
              -> bounded rescue candidates for B
solved C ----/
```

A successful upstream artifact may be shared only when scientifically compatible. Immutable run/checkpoint lineage remains mandatory.

## Campaign Prep and collection hierarchy

A future `Campaign Prep` layer should sit upstream of campaign planning/execution and reconcile the laboratory's experiment-facing records into a clean, machine-readable campaign without rewriting the raw archive.

The input side may include:

- XRD spreadsheets containing sample, puck, pin, beam-date, sequence/design, anomalous, expected-space-group, and note fields;
- design slide decks or other design records that map construct names to sequences and modified sites;
- beamline/raw-data directories organized by date, puck, pin, and collection; and
- autoPROC outputs or other processing results.

Prep should create explicit provenance-rich relationships rather than assuming one folder equals one dataset. The core hierarchy is:

```text
design -> sequence/chemistry -> physical sample -> pin -> collection -> processing result
```

A single physical pin may have many collections: point collects, vector collects, weak or radiation-damaged collects, repeats, alternate wedges, and other attempts of very different quality. Therefore **sample, collection, processed dataset, and refinement result are distinct objects** in the durable campaign model.

Prep should preserve the original pin/puck/date organization as immutable source data and create only a curated campaign view containing metadata, checksums, references/symlinks, generated inputs, and unresolved-match queues. Ambiguous sample/design/collection joins should go to a Prep Doctor queue rather than being guessed silently.

## Collection triage within a sample

One sample may legitimately enter NASolve through several processed collections. The default policy should be bounded rather than exhaustive:

1. begin with the most promising processed collection, usually the highest-resolution candidate that passes basic processing/statistical gates;
2. run the normal AutoMR/PostMR/AutoRefine path;
3. if refinement, validation, or map quality is unsatisfactory, consider alternate collections from the same physical sample;
4. compare resulting checkpoints using descriptive statistics and model-quality evidence; and
5. either select a preferred branch automatically under reviewed hard rules or place the shortlist into a human inspection queue.

Campaign execution must therefore allow multiple collection branches to share one sample/design parent while preserving immutable provenance. It should not assume that the first or nominally highest-resolution collection is scientifically best.

## autoPROC automation and Doctor

A future upstream autoPROC runner should read frozen experiment metadata and construct the appropriate processing intent, including reviewed settings such as anomalous handling, expected/candidate space group, global phasing-related options, and other beamline-specific flags.

The runner should be paired with an AutoProc Doctor that can recognize common technical/statistical failure modes and retry a bounded set of reviewed recipes. Every processing attempt should remain inspectable and attributable to its input collection and parameter set.

Processing automation should not silently reinterpret user-declared chemistry/symmetry intent; disagreements between metadata and processing evidence should be surfaced explicitly.

## Dataset merging / combination search

A later autoPROC-side feature should explore merging multiple equivalent or near-equivalent collections from the same sample/design family when a single collection is incomplete or statistically poor despite high nominal resolution.

This is intentionally a search problem. A collection reaching, for example, 0.7 A may still be unusable because completeness, redundancy, radiation damage, scaling consistency, or other statistics are poor. Combining several compatible collections may improve the usable dataset, but the best subset may not be obvious in advance.

The merger should therefore:

- define explicit compatibility gates before attempting a merge;
- generate bounded candidate subsets rather than blindly trying every power-set combination;
- run autoPROC/scaling on those candidates with frozen provenance;
- compare merged-data statistics to the best individual parent datasets;
- retain only scientifically meaningful improvements for downstream NASolve testing;
- permit Campaign/AutoProc Doctor to expand the search budget when early candidates fail; and
- preserve the exact parent collections and merge parameters for every derived dataset.

A successful merged dataset becomes another processed-dataset candidate under the same physical-sample parent, not a replacement for the original raw collections.

## Roadmap insertion

The existing campaign roadmap remains valid but should be interpreted with the following additions.

### Near-term: before broad campaign Doctor work

1. Generalize sequence handling into search-model, reference, and dataset-target layers.
2. Add simple campaign/reference sequence inheritance plus dataset override.
3. Add search-model sequence comparison and mismatch provenance.
4. Keep `mirror` as an orthogonal inherited/overridable token.
5. Allow explicit forced search-model selection for validation and unusual datasets.
6. Preserve one effective PostMR target compiled from sequence plus site-specific chemistry.

### Multi-candidate / model-provider stage

7. Generalize candidate generation so different datasets in one campaign may use different search models/providers.
8. Add provider provenance and sequence-to-model hooks; AlphaFold is a later provider, not a special campaign architecture.
9. Extend the campaign DAG to represent shared references, per-dataset models, reusable solved sibling models, and multiple processed collections for one physical sample.

### Campaign Doctor stage

10. Add bounded cross-dataset model rescue using solved siblings and explicit compatibility rules.
11. Add campaign-level model libraries/ensembles derived from solved structures under declared budgets.
12. Keep failed MR branches and every rescue attempt immutable and inspectable.

### Upstream preparation / processing stage

13. Add Campaign Prep to reconcile design, sequence/chemistry, sample, pin, collection, and processing metadata into a curated campaign view without moving raw data.
14. Add autoPROC runner + AutoProc Doctor with frozen processing intent and bounded recovery recipes.
15. Add within-sample collection triage so a sample can try alternate processed collections when the leading candidate fails or refines poorly.
16. Add bounded multi-collection autoPROC merging/subset search, retaining only provenance-rich derived datasets that improve useful statistics.

### Later validation and curation

17. Reuse the effective target sequence/chemistry record for Final Model Doctor, model completeness checks, curate/Table 1, and deposition sequence validation.

## Immediate validation fixture

`MR_frames/5W6W/5W6W_noPO4.pdb` is intended as a forced test model, not a default catalogue choice. It is the original 5W6W PDB sequence rather than the Lu-Vecchioni metal-pair scaffold sequence used by the current project models. It also lacks the designed D:1 5-prime phosphate.

This makes it a useful integration fixture for:

1. forced alternate MR-model selection;
2. search-model versus frame/reference sequence comparison;
3. PostMR normalization to the effective dataset target;
4. explicit dataset/site mutations overriding the frame/reference sequence; and
5. whole D:1 5-prime-phosphate construction and downstream ReadySet/Phenix interpretation.

The model must not become the normal W catalogue fallback merely because it exists in the frame directory.

## Design rule

The campaign layer should know enough to answer five questions for every dataset:

1. **What construct did the user intend?**
2. **What search model did we actually use?**
3. **How did that model differ from the intended/reference construct?**
4. **What did PostMR change to reach the effective target?**
5. **If ordinary MR failed, what bounded related-model evidence was tried next, and why?**

For campaign preparation and processing, it must also be possible to answer:

- which physical sample/pin produced this collection;
- which raw collection(s) produced this processed dataset;
- whether this result came from one collection or a merge;
- which processing/Doctor parameters generated it; and
- which alternate collections or merged candidates were tested before selecting the downstream branch.

If those answers remain explicit, NASolve can grow from simple 5W6W sequence variants to heterogeneous geometric campaigns without changing its fundamental provenance model.
