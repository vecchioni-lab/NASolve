# Explicit sequence-family target assembly

Status: **explicitly opt-in AutoMR/PostMR integration for standalone runs and
dataset-level campaign inputs; regression fixtures and a fresh live
Phenix/Coot/AutoRefine path validated.** The live validation accounted for all
42 intended residue identities, preserved the independent terminal-phosphate
chemistry, and carried the prepared model through refinement. Ordinary W recipe
defaults and existing frozen runs remain unchanged. Explicit campaign
sequence-thread inheritance is supported; thread membership remains target
metadata and does not imply model compatibility or reuse.

## Scope and scientific boundary

A sequence-defined construct family is one supported design model, not the
meaning of a campaign. Other experiments may be related by geometry, topology,
or declared design parameters without sharing a sequence or an MR scaffold.
Family membership never establishes search-model interchangeability.

The reference `w-metal-scaffold` describes the reviewed W-family **sequence**.
The name does not request a metal atom, metal occupancy, coordination geometry,
or a metal-pair restraint model. Watson-Crick-like proof-of-principle chemistry
and an explicit metal-pair project remain separate scientific policies. This
module does not assert that every modified pair is Watson-Crick-like; an
applicable restraint policy and its evidence remain necessary.

## Reference resource

`src/nasolve/data/sequence_references/w-metal-scaffold.json` explicitly maps:

| Chain | Residue IDs | Baseline sequence |
| --- | --- | --- |
| A | 1 through 21 | GAGCAGCCTGTATGGACATCA |
| B | 1 through 7 | CCATACA |
| C | 8 through 14 | GGCTGCT |
| D | 1 through 7 | CTGATGT |

The resource contains every residue-ID string, not an instruction to infer
numbering from sequence length or the order of an unlabelled text file.
Reference fields have a strict schema, explicit polymer type, ID and version.
Duplicate keys, chains or residue IDs and incompatible symbols are rejected.

`content_sha256` fingerprints canonical validated reference content. It is not
claimed to be a raw-file checksum. The run-freezing integration also retains
the exact consumed reference artifact and its byte checksum using NASolve's
ordinary portable provenance machinery.

## Target precedence

`compile_sequence_family_targets()` resolves residue identities in this order:

1. family reference sequence;
2. optional shared-thread sequence overrides;
3. optional dataset sequence overrides;
4. optional inherited/thread site-specific component identities;
5. optional dataset site-specific component identities.

Sequence overrides replace only the explicitly named complete chain sequences.
They cannot change the reference residue IDs or silently omit/reassign sites.
More specific site chemistry survives ordinary sequence overlays; a dataset
site declaration may explicitly replace inherited modified chemistry with a
canonical component. An empty overlay makes no changes; it does not remove
inherited declarations.

Every site records its effective component code, winning source layer and all
preceding assignments, including assignments that retain the same identity.
Component-code overlays must already be resolved by the existing identity/alias
layer. Checking their syntax here does not certify dictionary availability,
connectivity, handedness, or a supported mutation route.

The primitive has no dependency on a mutable workspace, a current checkpoint,
Phenix/Coot, or inferred dataset grouping. It does not build coordinates.
The caller supplies the explicitly resolved thread/dataset membership and
then applies the existing mirror, dictionary and mutation-execution policies.

## Read-only model comparison

`compare_sequence_family_inventory()` accepts literal residue identities keyed
by explicit `CHAIN:RESID`. A missing or additional site is a correspondence
error, not permission to align, renumber, insert or delete residues.

The original 5W6W scaffold tested with the W-family baseline differs at A:13
(DC to DT) and B:3 (DG to DA). Those differences are computed from the reference
and inventory, not implemented as mandatory site-specific substitutions. A
model already matching the effective target needs no identity changes.

A:12 and B:4 remain experimental-variant sites. Their final component identities
come from the applicable resolved site declarations. D:1 terminal-phosphate
construction/protection is a separate chemistry contract and is not part of
this residue-identity compiler.

## Explicit standalone opt-in

Add the following field to the dataset's existing `[automr]` section before
creating a **fresh** run:

```ini
[automr]
mode = standard
frame = W
pair = A:T
sequence_reference = w-metal-scaffold
```

The pair above is an example, not a new default. Retain the intended experimental
pair and any explicit `[mutations]` declarations. `sequence_reference` may also
name an explicit dataset-relative JSON file with the same reference schema;
absolute paths and paths escaping the dataset are rejected. No unlabelled
sequence file, model name, or frame selection implicitly enables this feature.
This slice introduces no `W*` frame alias and does not modify the W preset.

Standalone sequence overlays and site declarations feed the tested compiler.
Campaign planning accepts the same explicit per-dataset `sequence_reference`
selector. The planner copies the exact selected reference bytes into the
content-addressed `NASolveCampaign/resources/` store, records the original
selector separately, and fingerprints both into the immutable plan. Campaign
preflight consumes only that frozen resource, receipts its attempt-local copy,
and then lets ordinary AutoMR freeze the same bytes again into the numbered run.
The installed reference or original dataset-relative JSON is therefore not
reopened during execution.

Campaign sequence-thread inheritance is supported only through explicit root
`nasolve-campaign.toml` membership. A named thread freezes the reviewed
`w-metal-scaffold` selector plus optional shared chain-sequence and site-code
overlays. Dataset sequence and site declarations remain more specific.

Thread membership is target metadata only. It does not establish search-model
compatibility, select a sibling model, authorize cross-dataset reuse, or imply
shared geometry/metal chemistry. Those remain separate reviewed campaign/model
policies.

An explicit standard-frame model provider may be combined with the same frozen
sequence-family target. The tracked `MR_frames/5W6W/5W6W_noPO4.pdb` fixture
exercises this path: its original 42-site scaffold enters the W workflow as
coordinates, while the sequence-family compiler independently records the A:13
DC→DT and B:3 DG→DA target differences. The W recipe independently retains D:1
terminal-phosphate intent. Provider selection therefore never becomes target
authority.

## Frozen run contract

AutoMR validates complete chain/residue correspondence and compiles the target
before allocating the new run. It copies the original search coordinates
unchanged, apart from the existing explicitly requested mirror transform.
Sequence mutations are never performed before Phaser.

The new run retains:

- `Model/sequence_reference.json`: the exact reference bytes consumed;
- `Model/sequence_family_target.json`: all effective residue codes and layer
  assignments;
- additive `post_mr_plan.sequence_family` schema-1 metadata containing the two
  run-anchored, checksummed artifacts, frozen overlays and an input-intent
  fingerprint;
- a matching `inputs.sequence_reference` artifact reference; and
- a read-only preflight comparison of the literal source inventory before any
  mirroring, separate from the actual post-MR mutation plan.

The JSON files are not reconstructed from a later installed reference. PostMR
checks their byte hashes and internal consistency, rejects changed input
intent, and checks actual MR correspondence before constructing its output.
Removing a requested artifact or contract is an error, not permission to fall
back to the legacy planner.

PostMR feeds the verified target codes to the existing mutation planner and
Coot/parent-overlap routes. Existing DNA/RNA sugar checks, mirrored-mutation
restrictions, component dictionaries and chemistry safeguards remain active.
It checks all final prepared residue identities after ReadySet and records a
`sequence_family_audit`. This is an identity audit, not a claim of correct
geometry, metal coordination, map quality or deposition readiness.

Low-level callers inspecting an opted-in run must pass its explicit location:

```python
build_mutation_plan(report, model, run_directory=run)
```

Legacy calls and reports without a selected reference retain their prior target
semantics. No existing run is migrated, and older coordinate/checkpoint files
are never rewritten to acquire new reference authority.

## Validation boundary

Controlled tests cover 42-site coverage, the two computed scaffold corrections,
sequence/site precedence, C:8–14 numbering, raw-search-model preservation,
artifact/intent drift, relocation after the original directory disappears,
legacy behavior, existing mirror/sugar/chemistry gates, final prepared-model
identity checks, campaign reference snapshotting, campaign execution after
the original reference source disappears, explicit standard-model providers,
and controlled normalization of the original no-phosphate W scaffold through
PostMR. External executables in these tests are fixtures.

A fresh W-family live run separately verified all 42 intended identities,
the actual A:12/B:4 variant, independent D:1 phosphate protection, and successful
AutoRefine continuation. That validation does not make the reference a default:
a future versioned recipe may consider doing so explicitly. The metal-pair
project, automatic cross-dataset model reuse, and geometry/topology-defined
campaign families remain separate work.
