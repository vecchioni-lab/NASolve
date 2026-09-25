# Model compatibility facts

Status: **descriptive run-local provenance only.** This layer records explicit
facts that a future Campaign Doctor may use under a separate reviewed policy.
It does not score candidate models, rank alternatives, declare donor
eligibility, or authorize cross-dataset reuse.

Every fresh AutoMR run freezes:

```text
Model/model_compatibility_facts.json
```

and records a checksum/size reference in `report.json` under
`model_compatibility_facts`.

## Why this exists

Model provision, experimental-family membership and reuse eligibility are
separate responsibilities. A coordinate model may be a useful MR candidate
without matching the recipient sequence exactly, and a sequence/thread
relationship does not prove that two structures are interchangeable.

The fact sheet therefore exposes named dimensions without combining them into
an overall judgment.

## Candidate and recipient roles

The record distinguishes:

- **candidate**: the effective search model submitted to, or prepared for,
  Phaser in this run;
- **recipient**: the frozen AutoMR intent for the dataset being solved.

The candidate section records the source/effective model hashes, provider
summary, run mode, polymer residue count and exact chain/residue-ID inventory.

The recipient section records the run mode, selected standard frame when
applicable, authoritative diffraction symmetry class and requested MR copy
count.

## Named dimensions

### Frame identity

If both the provider and recipient declare a frame, Moss records whether those
declarations are the same or different. It does not infer frame identity from
coordinate geometry or filenames.

### Construct family

Current model providers do not declare construct-family membership. Even when a
complete target names `w-metal-scaffold`, the model-side family remains
unknown. The fact sheet therefore records the recipient reference and leaves
the relation `UNKNOWN`.

### Site set

When Hemlock's complete search-model comparison is available, Moss records
whether the model and target use the same explicit site set plus any missing or
unexpected sites. Without a complete explicit target this relation remains
`UNKNOWN`; NASolve does not invent a target from an unlabeled `seq_base.txt`,
filename, frame membership or sibling dataset.

### Residue identity

With a complete target, Moss summarizes the literal pre-mirror identity
comparison as `SAME`, `DIFFERENT` or `PARTIAL` and records compared/mismatch
counts. The detailed site-level evidence remains in
`Model/search_model_comparison.json`.

A residue difference is a fact, not a negative model-quality judgment.
Mutation-route availability remains a separate PostMR responsibility.

### Chirality

The current schema records whether NASolve applied its explicit mirror
transform. It does **not** establish the model's absolute D/L chirality.
Therefore both absolute-chirality fields and their relation remain unknown.

In particular, `mirror = false` must never be reinterpreted as proof of
D-DNA.

### Terminal-phosphate chemistry

Moss records the recipient's explicit 5-prime-phosphate/OP3 sites and the
provenance of that intent. It does not yet claim that the candidate coordinates
already contain or satisfy that chemistry, so the model-side relation remains
unknown.

### Backbone chemistry

Moss records the recipient's standard-phosphodiester default, explicit
site-level overrides, experimental passthrough sites and unreviewed-consent
flag. Candidate-coordinate backbone compatibility is not inferred.

### Symmetry and copy number

Diffraction symmetry and the requested MR copy count belong to the recipient
dataset. A PDB search model does not itself establish compatibility with that
symmetry, so the candidate-side relation remains unknown.

## Meaning of relation values

`SAME`, `DIFFERENT`, `PARTIAL` and `UNKNOWN` are per-dimension
descriptions only.

- `SAME`: the two explicit values/site sets being compared are literally the
  same.
- `DIFFERENT`: those explicit facts differ.
- `PARTIAL`: identities can be compared only across a subset of sites.
- `UNKNOWN`: NASolve lacks evidence required to compare that dimension.

`UNKNOWN` is not a permissive value and `DIFFERENT` is not a rejection.

## Explicit non-decision contract

Every schema-1 record fixes:

```json
{
  "descriptive_only": true,
  "score": null,
  "overall_compatibility": null,
  "donor_eligibility": null,
  "automatic_reuse_authorized": false
}
```

The loader rejects a re-signed artifact that inserts a score or verdict.

## Integrity

Loading Moss provenance verifies:

- the fact-sheet artifact checksum and schema;
- source/effective model hashes against the run report;
- provider provenance;
- exact candidate chain/residue inventory;
- mode, frame and mirror intent;
- recipient symmetry/copy-number evidence;
- terminal-phosphate and backbone intent; and
- Hemlock's comparison reference and checksum when present.

Mirror transforms are also required to preserve exact polymer residue IDs, not
only residue counts. Residue names may use mirrored aliases, but site numbering
and chain topology may not silently change.

## Campaign boundary

Campaign preflight automatically receives the same fact sheet because it
reconstructs AutoMR from frozen campaign resources. Moss therefore describes
the exact provider, target and chemistry frozen by the plan rather than
rediscovering live files.

A future Campaign Doctor may consume these facts only under a separate reviewed
eligibility policy. Moss itself does not decide whether a solved sibling may be
used, how candidates should be ranked, or what transformations would be
permitted.
