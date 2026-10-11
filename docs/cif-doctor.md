# CIF Doctor

CIF Doctor assesses component dictionaries without changing their chemistry or
the model. It runs offline, using NASolve's existing CIF reader and lightweight
graph and numerical checks. It does not require an LLM, RDKit, a generator or
Phenix. The larger scientific design remains in
[the audit methods](cif-restraint-audit-methods.md) and
[the implementation map](cif-restraint-doctor-implementation.json).

## Commands

Assess explicit dictionaries, optionally against a PDB atom inventory:

```bash
./nasolve cif-doctor assess /path/to/component.cif --stage source --json
./nasolve cif-doctor assess /path/to/effective.cif --stage effective \
  --model /path/to/model.pdb --output /path/to/new-audit.json
```

Assess the exact frozen bundle at a completed run's selected checkpoint:

```bash
./nasolve cif-doctor assess --run /path/to/AutoMR/run_001 --json
./nasolve cif-doctor assess --run /path/to/AutoMR/run_001 \
  --checkpoint refine-002 --output /path/to/new-audit.json
```

The run adapter reads existing state without creating a checkpoint registry,
changing the selection or rewriting any artifact. It verifies frozen model,
observation and restraint references through the existing run-context resolver.
An explicit checkpoint ID or bookmark takes precedence over the current one.
It never falls back to a similarly named file after an integrity failure.

Compare an explicitly selected source with a same-code candidate:

```bash
./nasolve cif-doctor compare /path/to/source.cif /path/to/candidate.cif --json
```

The comparison records exact atom, bond, aromatic, hydrogen, charge and declared
stereo differences. It reports which fields differ without choosing the correct
chemistry or guessing an alias, tautomer or linked-state transformation. Formal
and partial charge fields remain separate; an unspecified charge is not zero.

Exit codes are `0` for the implemented checks passing, `2` for review/unassessed
evidence, `3` for an invalid assessment and
`1` for an operational error. A passing dictionary check is not scientific
approval, native interpretation or geometry qualification. Missing numerical
restraints in an ordinary CCD construction graph remain explicitly unassessed;
in an effective refinement dictionary they need review.

## Pipeline placement and receipts

New PostMR executions produce three JSON receipts under `PostMR/Restraints`:

- `cif_doctor_mutation.json` when mutation dictionaries are required: exact target construction dictionaries before
  coordinate normalization or Coot mutation, with audit-only source snapshots.
- `cif_doctor_source.json`: frozen source definitions and a separate assessment
  of runtime inputs immediately before ReadySet.
- `cif_doctor_effective.json`: the actual selected effective bundle and final
  ReadySet model, after dictionary precedence/normalization and before readiness.

PostMR reports reference these receipts by anchored path, size and SHA-256 and
retain their summaries. Source and effective dictionaries remain separate;
the source and its derivative are not misreported as simultaneously loaded
competing definitions. Already-present curated modifications enter the source
and effective audits even when no mutation is requested.

This first deployment is report-only. The existing identity, phosphate,
parameterization and precedence checks still own continuation. Audit findings
do not silently change ReadySet inputs, start a repair or add a campaign gate.
Old runs remain unchanged and can be assessed with the command above.

Receipts use schema version 1, `audit_kind` and a versioned policy. They contain
ordered, hash-bound input descriptors, component inventories, stable rule IDs,
raw measurements and explicit unimplemented layers. Run receipts have portable
references; standalone receipts declare their input root for explicit replay.
Native proxies, site-specific link chemistry, sugar-pucker interpretation,
achieved geometry and map support are not certified by a source-file assessment.
Zero-sigma torsion annotations are inventoried under the native inactive-term
convention, with actual proxy activity still unassessed. A `CONST` name alone
does not determine activity. Signed periodicity remains visible rather than
being converted into a guessed sugar-pucker or Gaussian-sigma conclusion.

## Reviewed preparation

Preparation is an explicit derivative write, separate from PostMR adoption:

```bash
./nasolve cif-doctor prepare /path/to/source.cif \
  --recipe torsion-alternates-v1 --output /path/to/new-candidate.cif \
  --report /path/to/new-preparation.json
```

`torsion-alternates-v1` wraps the existing supported CCP4 alternate-torsion
normalizer. It retains the primary row's uncertainty, preserves recognized
alternate targets and leaves unsupported competing terms intact for review.

`5cm-reviewed-torsion-v1` applies only to the exact reviewed historical source
hash `38378c7df4eef73a0bd2be40059b2c3dd2b98618a4eeb7e91f6ec3427f7e7858`.
It changes the single reviewed C2 reference to C2′ in the
C4′–O4′–C1′–C2 torsion, then applies that existing normalizer. Other files,
including another file named `5CM.cif`, are refused. This is not a general
prime-name correction rule.

Both recipes preserve the original bytes, refuse existing destinations and
return hashes, field-level changes and before/after assessment. `PREPARED`
means a candidate file was created; it does not mean native qualification or
automatic adoption. Preparation's exit code follows the candidate assessment;
invalid candidates visibly remain blocked from adoption. The recipes do not edit coordinates, invent protonation or bond
orders, install the diagnostic DF/DP candidates or rewrite a frozen run.

## Broader evidence and remaining work

NARestraints' ligand workbook selects test cases and records pairing semantics;
it is not a universal bond-order, protonation or stereochemistry authority.
Official [wwPDB CCD](https://www.wwpdb.org/data/ccd) definitions provide separate
source evidence. Downloads used for development are hash-frozen local inputs;
runtime assessment itself performs no network acquisition.

The first held-out corpus contains 18 public CCD source graphs, with provenance
and workbook row references in [the control manifest](cif-doctor-ccd-controls.json).
It includes halogenated DNA/RNA, C-glycosidic
pseudouridine, L-DNA, a nucleotide lacking O3′, methylated/sulfur components
and diphosphates. These exercise general checks without component-specific
exceptions. Official CCD 8RO remains distinct from the lab's DE identity.

The frozen comparison exposed inconsistent 5BU/BRU sugar-type workbook labels
and a PSU glycosidic-atom loader assumption. Those observations are recorded
as target-selection cautions; this change does not edit the workbook or loader.
The controls also prevent a fixed DNA R/S pattern: substituent changes can
change CIP labels without inverting the sugar. Preserve declared stereo and
perform any future assignment against the actual mapped graph.

Validation for the initial slice: 88 new Doctor tests and seven subtests, plus
the complete 1,077-test suite (two skips, 276 subtests). Frozen public controls
and exact historical replays preserve all input bytes. These are offline tests
and source-file audits, not a returned native Phenix/Coot campaign receipt.

Installed consumer-parser agreement, mapped descriptor chemistry, generator
adapters, effective native proxy receipts and new-checkpoint adoption remain
follow-up work. Geometry/connectivity assessment and guided sticky-end stitching
remain part of the Doctor roadmap, using declared routing and Scout/Topo
primitives while preserving true nicks, terminal intent and frozen Free-R flags.
