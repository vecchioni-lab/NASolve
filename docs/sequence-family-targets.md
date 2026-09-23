# Explicit sequence-family target assembly

Status: **tested standalone primitive; not yet invoked by AutoMR, PostMR, or
campaign execution.** No existing run or default recipe changes in this slice.

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
claimed to be a raw-file checksum. The future run-freezing integration must
also retain the exact consumed reference artifact and its byte checksum using
NASolve's ordinary portable provenance machinery.

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

## Next integration slice

Freeze the explicitly selected family reference and resolved target for fresh
runs, feed that target to the existing PostMR mutation executor, and audit the
prepared identities against it. Do not retrofit reference authority into legacy
reports or recompile old runs from a newly installed recipe. Preserve the
current mutation and chirality safety gates; this primitive does not supply a
new mutation engine.

Only after that integration and its tests should a fresh live W-family run
check full 42-site target coverage, scaffold conversion, variant-site identity,
and unchanged terminal-phosphate protection together.
