# CIF Doctor

## Generated numerical defects and explicit candidates

The assessor's `cif-doctor-graph-numerics-v2` policy checks exact coincident
bonded heavy atoms in numerical dictionary coordinates. Invalid bond-target
findings include the atom pair. Raw graph sources, absent coordinates and
unsupported representations stay separately unassessed; achieved model
geometry is still NOT_RUN. The new coordinate inventory/verdict is additive
within assessment receipt schema 1.

PostMR's existing generic numerical gate now writes an exclusive
`PostMR/ReadySet/cif_doctor_generation_failure.json` when generated targets are
missing, invalid or have coincident bonded heavy atoms. It reports the actual
component, atom references and reason rather than treating every failure as a
missing dictionary. Curated or explicitly numerical inputs retain their
existing authority over rewritten ReadySet rows. The complete failed component
is quarantined; no individual distance is filled in.

To generate an explicit, independent whole-component candidate:

```bash
./nasolve --phenix-root /path/to/phenix cif-doctor generate-candidate source.cif \
  --code ABC --output-parent /path/to/candidates --timeout-seconds 600 --json
```

This operation alone requires optional `phenix.elbow`, resolved beside the
selected installation's Phaser dispatcher. It preserves the user's saved
configuration/workspace and passes a cleaned native environment copy.
Generation uses the frozen chemical CIF and a naming/initial-geometry PDB
derived only from complete source ideal coordinates and integer formal charges.
The explicit template supports component IDs of up to three characters and
atom names of up to four ASCII characters; missing or unrepresentable data are
reported, never inferred from the fitted model. The generation-v3 adapter first
records a bounded `phenix.elbow --help` check from that exact executable. It
selects supported option spellings and verifies that each required option takes
a value or is a switch as appropriate. Initial geometry and hydrogen controls
may use dashed or underscored aliases; no required control is silently omitted.
Unsupported or failed help checks stop before chemistry with
`UNSUPPORTED_GENERATOR`. Help logs, hashes, selected aliases and executable
identity remain in the receipt. eLBOW then receives explicit optimization,
hydrogen addition disabled, retained chirality and the independent template.
The required valued `--pH` control is set to `low`, the installed generator's
input-chemistry retention mode. This requests preservation of the source state; it
does not assert experimental pH or establish the correct crystal protonation.
Hydrogen addition disabled alone does not prevent eLBOW from removing existing
acid hydrogens. Atom, bond, hydrogen, charge and declared-stereo comparisons
still reject changed chemistry even when the generator exits successfully.
The requested `--opt` option and any backend named in the native log are
separate evidence; the returned Phenix 2.2.1-6174 run used RM1/GDIIS.
The original CIF, failed ReadySet output and prior numerical resources are
never overwritten or used as a source of invented numerical targets.

Schema-1 `cif_component_generation_inspection` and
`cif_numerical_generation_candidate` receipts record source/candidate
assessments, chemical differences, exact numerical issues, generator command,
version, timeout, output hashes and preservation checks. Exit 0 means
`CANDIDATE_REVIEW`, not chemical approval; rejected/failed candidates exit 2.
Complete numerical candidates may retain soft plane/torsion REVIEW findings;
missing targets, invalid numerics and unresolved plane compatibility remain
rejected. These findings are preserved rather than relabeled as numerical PASS.
The generator does not retry ReadySet, edit a model, adapt polymer links or
adopt a dictionary. Native reader/geometry/proxy verification and any actual
linked-site chemistry remain separate qualification steps.

The source-bundled `04_Cedar_probe_cif_generation.py` inspects an existing failed run,
selects invalid non-curated generic components by findings, and invokes this
same candidate API. Its summary distinguishes failed/rejected generation from
an actual candidate awaiting review. It writes a review ZIP into a fresh external session while
preserving the original run. `--inspect-only` skips native generation.
Its delivery prefix appears first in the script/session/review-ZIP name and is
printed with the policy ID. The ZIP additionally includes the session's unique
token near the beginning. Schema-1 metadata and probe receipts retain the same
prefix. Developers can set `--delivery-prefix` when building another delivery;
explicit output paths remain honored. Older runs and shuttles remain readable.

The [optimized native evidence](elbow-optimized-state-evidence.json) records
the restored IGU C2–N3 target (1.387 Å) and the separate rejection for deleted
phosphate hydrogens and altered formal charges. A native retry with explicit
source-state retention was pending at that point; that evidence does not authorize
candidate adoption or a full-auto campaign restart. The subsequent
[source-retention evidence](elbow-source-retention-evidence.json) records a
successful v3 retention attempt with all 37 atoms and unchanged formal charges.
That candidate remains REVIEW pending metadata/native-reader/link qualification.

## Explicit native bundle diagnostic

`05_Cedar_probe_cif_native.py` is a separate diagnostic shuttle. Its default
case uses the returned Cedar 04 generation receipt and the original failed
synthetic run. It rechecks the current candidate, binds its frozen chemistry
to the source audit, and verifies the prepared PDB plus every recorded runtime
CIF/PHIL/EFF. The generation probe also binds the source audit and failed
ReadySet baseline; caller-selected exact paths are checked against those
hashes rather than resolved through historical absolute paths.

The shuttle copies inputs into a fresh external directory, replaces only the
candidate component in that diagnostic input list, and applies the ordinary
parameterized-input precedence and supported torsion normalizer. All recorded
ancillary parameters and reviewed site-modification files are retained.
It does not add generic site modifications or change DNA metadata/protonation.
`--inspect-only` performs this preparation offline without discovering Phenix.
Explicit `--run`, `--candidate-directory`, `--generation-probe`, `--phenix-root`
and `--output-parent` overrides retain their declared checksum boundaries.

Native execution requires optional `phenix.python` beside the selected
installation's Phaser dispatcher. The standalone worker uses installed
iotbx/libtbx/mmtbx readers and monomer/energy libraries. It records effective
monomer metadata, missing-atom mappings where supported, interpreted atom
identities/coordinates, simple/ASU bond endpoints and geometry proxy counts.
Original and copied input bytes are rechecked after execution. Native hierarchy
normalization is recorded separately from preservation of the original model.

The opt-in `refinement-root-to-interpreter-v1` PHIL namespace policy uses the
native parser to remove only a top-level `refinement` wrapper, retaining all
child definitions, value tokens and selections. Canonical derivatives and field
maps are preserved, and unused parameters stop as explicit unsupported evidence.
Geometry edits/removals and scoped CIF modifications use the corresponding
native consumers; no parameter is silently discarded to obtain a clean run.

Schema-1 `cif_native_bundle_inspection` receipts use policy
`cif-native-bundle-inventory-v1`. Successful interpretation returns **REVIEW**,
with native failures, unavailable APIs/fields and missing coverage visible.
Inventory does not certify intended links, custom-restraint coverage, achieved
geometry or scientific validity. The helper runs no optimization, ReadySet,
refinement, candidate adoption or checkpoint selection. A prefixed review ZIP
contains exact diagnostic inputs, canonical parameters, raw logs and receipts;
embedded source runtime and native pickles are excluded. Native execution of
this new helper remains pending the laptop return.

CIF Doctor assesses component dictionaries without changing their chemistry or
the model. It runs offline, using NASolve's existing CIF reader and lightweight
graph and numerical checks. It does not require an LLM, RDKit, a generator or
Phenix. The larger scientific design remains in
[the audit methods](cif-restraint-audit-methods.md) and
[the implementation map](cif-restraint-doctor-implementation.json).
For a plain-language explanation, methods paragraph and editable publication
figure, read [the human/manuscript overview](cif-doctor-human-overview.md).

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

## Offline runner for the public control ZIP

The downloadable `run_cif_doctor_ccd_controls.py` contains the exact reviewed
assessor and its required reader/normalizer code. Run it with Python >=3.10
and Biopython; an existing NASolve virtual environment is sufficient. It
requires neither a NASolve checkout nor network access. Given both downloads
in `~/Downloads`, the established laptop environment can run:

```bash
"$HOME/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python" -B \
  "$HOME/Downloads/run_cif_doctor_ccd_controls.py" \
  "$HOME/Downloads/NASolve_CIF_Doctor_public_CCD_controls_2026-10-11.zip"
```

The runner verifies the frozen ZIP, manifest, all 18 CIFs and embedded runtime,
then creates a unique output folder beside the ZIP. It refuses reused output
folders, leaves the ZIP unchanged and writes `audit_summary.txt`,
`audit_summary.json` and 36 hash-bound receipts. These particular controls
produce **18 source PASS / numerical UNASSESSED and 18 effective REVIEW**:
the same source graphs are screened in two contexts. No numerical dictionary
is generated, and ReadySet/refinement are not run. A completed audit exits zero;
findings are recorded in its report, unlike the single-assessment CLI exit codes.

Developers can regenerate the single-file artifact without an installed NASolve:

```bash
python3 scripts/build_cif_doctor_ccd_shuttle.py \
  --corpus-zip /path/to/public-control.zip --output /path/to/new-runner.py
```

Build/receipt schema 1 pins the exact source hashes and original module paths;
the shared reader definitions are copied unchanged with minimal imports.
The builder refuses existing destinations. The runner's hash belongs to each
delivery receipt, rather than serving as a rolling software version.

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
and a PSU glycosidic-atom loader assumption. The separately reviewed
[NARestraints workbook patch](https://github.com/vecchioni-lab/NARestraints/blob/main/docs/workbook-audit-2026-10-11.md)
corrects the sugar labels/abbreviations, DF/S6G atom mappings and explicitly
authorized C5 whitespace. It does not change the frozen public-control snapshot
or fix PSU's coupled glycosidic/base-plane handling. Released v1.1.3 installations
retain their original workbook until explicitly updated.
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
