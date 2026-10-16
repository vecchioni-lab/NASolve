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
reported, never inferred from the fitted model. The generation-v4 adapter first
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

Generation-v4 also recognizes a bounded bond representation change: an entire
isolated six-member C/N ring can change from alternating single/double orders
to aromatic bond types only when every source ring bond is explicitly aromatic.
Ring atoms must have unchanged elements and explicit zero formal charges;
ring bonds must have no explicit stereochemical declaration beyond `N`.
Every substituent edge must remain a single graph bridge, excluding fused/spiro
rings, chords and exocyclic multiple bonds. Missing/conflicting aromatic flags,
partial conversions, other ring sizes and all unresolved order changes remain
rejected. This checks supplied declarations without inferring aromaticity,
resonance, valence, protonation or tautomer equivalence. Source and candidate
files and numerical targets remain untouched.

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
Inspection receipts add `bond_representation` under
`cif-source-declared-six-member-aromatic-v1`, retaining every raw `bond_orders`
and aromatic-metadata difference in the existing comparison. Representation
evidence does not override independent atom, hydrogen, charge, stereo or
numerical failures. New builds of the native shuttle recognize source-retaining v3/v4
receipts, verify all source/output hashes and re-inspect current dictionaries;
unknown generator policies remain unsupported.

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
embedded source runtime and native pickles are excluded. The returned Cedar 05
inventory completed on Phenix 2.2.1-6174: 42 mappings, 38 internal O3′–P links,
zero coordinate OP3/O3P, and four isolated-monomer OP3 expectations. REVIEW
is the worker's successful inventory status; see the [native ledger](native-modified-pair-live-validation.md#cedar-05-return-and-source-state-audit).

## Source-preserving linked-state diagnostic

`06_Cedar_probe_cif_linked.py` takes the exact checksum-bound returned 05 ZIP,
verifies its 57 payloads and writes a fresh external session. It reuses CIF
Doctor's source/candidate comparison and existing eLBOW candidate API before
link adaptation. The selected CGY/IMC/DX ReadySet definitions lost their
source OP2-bound hydrogens; source-preserving whole-component regeneration is
therefore required. The accepted 04 IGU candidate can be reused. Failed or
chemically changed candidates remain separate review evidence, with no
hydrogen insertion or invented numerical targets.

The explicit `cif-source-preserving-linked-sites-v1` preparation API requires
source `DNA LINKING` metadata, a complete source-preserving numerical candidate,
and declared incoming/outgoing and terminal contexts for every same-code model
site. It writes a DNA metadata derivative, graph-selected atom-deletion/O3′-OC2
modifiers, exact site selections, projected dictionaries and assessments.
Incoming and outgoing treatment are independent. Source-specific OP2 H and
formal charge declarations survive; free 5′-OH and explicitly requested
terminal phosphate states remain distinct. Unsupported symmetry, alternate
conformers, insertion codes and experimental backbones stop for review.
Raw source dictionaries and coordinate models remain unchanged.

Native `inventory_detail="linked"` is opt-in and additive to the existing
inventory API. It records effective atom/energy/charge/graph definitions and
individual proxy targets/weights, and resolves explicit geometry edits through
the installed native selector. Qualification checks all 38 declared links,
exact custom proxy coverage, retained pair/stacking parallelities, unchanged
model coordinates/identities and other-component definitions, plus absent
leaving atoms and dangling references. A separate 43-residue control adds a
free-OH IGU while retaining internal IGU under the same component code.

`LINKED_MECHANICS_PASS` describes these checks only. Existing 5CM torsion,
angle/plane and generated stereochemical metadata reviews remain visible;
achieved geometry and experimental protonation remain unqualified. The shuttle
runs no ReadySet retry, diffraction refinement, checkpoint selection or
dictionary adoption. The returned Cedar 06 capsule completed IMC/CGY/DX eLBOW
generation and stopped at `SOURCE_RECOVERY_REVIEW`: only CGY's ring-bond
representation blocked the generation gate. Native bundle interpretation and
the shared-code control did not run. The [source-recovery evidence](cif-linked-source-recovery-evidence.json)
records its 87 verified payloads, exact source/candidate hashes and offline
reanalysis. With generation-v4, all four returned candidates prepare linked
derivatives offline, retaining their OP2 hydrogens. The subsequent delivery used
`--delivery-prefix 07_Cedar` with `scripts/build_cif_linked_probe.py`.
The Cedar 07 return is recorded below; offline tests and fake
native APIs do not establish an installed Phenix pass. Failed source recovery
now prints the component, generation status and recorded rejection reasons.
The older native API defaults and receipts stay compatible.

The returned Cedar 07 capsule passed source recovery and baseline interpretation
(858 atoms, 42 mappings and 38 backbone links), then failed linked interpretation
because the modifier writer used a shared `data_mod_linked_sites` block. The
native reader registered `linked_sites` four times while PHIL requested four
distinct `NASL...` IDs. Preparation now emits one `data_mod_<ID>` block per
requested modifier, including mixed contexts for one component code. Atom-loop
IDs, PHIL requests, base dictionaries, deletions and projected site chemistry
stay identical. Schema-1 preparation adds
`modification_block_policy = cif-native-modification-blocks-v1`.
The [native-registration evidence](cif-linked-native-registration-evidence.json)
records the 164 verified payloads, reader contract and exact offline replay.

The baseline's detailed native atom records also expose no formal-charge values.
The detailed worker records missing attributes separately from null values.
Qualification labels unavailable formal-charge readback `UNSUPPORTED`, preserves
actual charge contradictions as `REVIEW`, and never substitutes partial charges
or a presumed zero. Other site/proxy checks continue; a complete mechanics pass
still requires all checks. Native failures print the relevant baseline/linked
error alongside the preserved receipt.

Cedar 08 completed baseline, linked and shared-code native interpretation on
Phenix 2.2.1-6174. All four effective atom sets, H adjacency and energy types
agree, with 38 preserved backbone links, exact custom proxy coverage and
unchanged original coordinates/other definitions. Complete qualification stays
REVIEW: the installed atom API lacks formal-charge attributes, and scalar
`comp_list` metadata is skipped by the reader, leaving the native group null.
Native logs classify all 42 residues as DNA; classification and group are
separate fields. The original atom check also required DNA group and therefore
reported REVIEW despite matching atom sets.

Preparation now retains the singleton `_chem_comp` row as a loop in base and
projected dictionaries, with schema-1 `component_list_policy =
cif-native-component-list-loop-v1`. Parsed metadata and every atom/restraint
value remain the same, as do modifier/PHIL bytes and site plans. Detailed
metadata adds native `classification`; qualification separates exact atoms
from required DNA group without relaxing either check.

The returned Cedar 09 installed execution recovers DNA group and classification
at all four internal sites. All **29** evaluable qualification checks pass;
the four formal-charge checks are **UNSUPPORTED** because the installed native
atom API lacks that attribute. The aggregate remains REVIEW. Read-only file
comparison confirms 148 unchanged source/candidate formal charges; ordered
signed-volume comparison agrees at all 12 sugar centres against source ideal
coordinates and native proxy order. These are separate evidence, not native
charge readback or independent absolute stereochemistry.

The shared-code control preserves all original atoms, definitions and links;
E:1 has group DNA and classification undetermined. Its O5′ retains source O2
typing with no attached explicit H, so the demonstrated scope is atom/context
isolation, not complete terminal-OH chemistry. The 12 soft plane-angle findings,
omitted generator metadata and retained 5CM C2/C2′ torsion remain visible.
The next phase is explicit dictionary/end-state and geometry review. No runtime
gate was changed to make the returned result pass, and repeating an unchanged
inventory will not resolve unavailable native formal-charge readback.

## Explicit terminal numerical-source review

`scripts/build_cif_terminal_probe.py` builds a source-bundled terminal review
with the existing pinned NARestraints source. The completed Cedar 11 delivery uses
`--delivery-prefix 11_Cedar --output PATH/11_Cedar_probe_cif_terminal_review.py`;
the builder retains its original `10_Cedar` default for compatibility.
The runner reads the exact
returned Cedar 09 review ZIP, verifies its 207 payloads and snapshots the
explicitly declared 5CM source. The existing source/output-hash-scoped
`5cm-reviewed-torsion-v1` recipe produces a new candidate and receipt, without
replacing any run input. `--inspect-only` stops after that offline preparation;
explicit `--review-zip`, `--output-parent`, `--phenix-root` and timeout overrides
remain available. New sessions and review ZIPs retain the leading delivery/run
identifier.

The separate `cif-installed-terminal-resources-v2` API reads requested native
modification IDs and applies them only to a canonical library object in memory.
Default `5*END`/DG records supply installed atom/bond/angle/torsion/chirality/plane
row fields and numerical values, source/module hashes, charge availability and
unchanged canonical base evidence. The native row API supplies its own field
names; missing interfaces/modifications are unsupported, without guessed targets
or charge substitutions. Canonical lookup uses the installed
`get_comp_comp_id_and_atom_name_interpretation` API with an empty atom-name
list: the explicit residue name selects a library identity without supplying
model atoms. Requested code, interpreted residue name, resolved component ID
and the `iotbx.pdb` module hash are recorded additively in schema 1. Native
translation handles PDB names such as DG and library names such as GD; no
NASolve alias table or guessed alternative component is introduced.
No coordinate model is supplied or edited.

All nine payloads in the returned Cedar 10 capsule verify. It prepared the
exact reviewed 5CM candidate and captured installed Phenix 2.2.1-6174 `5*END`
rows and source hashes, then returned `NATIVE_RESOURCES_REVIEW` because its v1
direct DG lookup found no library component. The canonical control and terminal
recipe did not run. The v2 retry addresses this lookup boundary without
changing numerical targets or existing qualification checks.

All nine returned Cedar 11 payloads also verify. Phenix 2.2.1-6174 completed
resource collection at exit zero in 0.837208 s. Requested DG resolves to native
metadata ID `Gd`; the canonical base remains unchanged. Applying `5*END` removes
P/OP1/OP2, changes O5′ to OH1 and adds HO5′ with HOH1 typing. The source supplies
the O5′–HO5′ bond (0.84 ± 0.02 Å; neutron target 1.02 Å) and C5′–O5′–HO5′
angle (120 ± 3°). No unaffected bond/angle/torsion/chirality/plane row changes
and no dangling atom reference remains. Source files are unchanged.

The canonical control retains DNA group but its classification changes from
DNA to `undetermined`. Thus that classification alone does not distinguish the
earlier synthetic modified end from an installed canonical hydroxyl end; it
does not erase the earlier observed missing O5′ hydrogen/type treatment.
Formal-charge readback remains unsupported in both canonical states; partial
charges are not substituted and the earlier native qualification gates remain.

`PREPARATION_AND_RESOURCES_REVIEW` means that the separate preparation and
resource collection completed, not that generic terminal chemistry is qualified.
The exact 09 source reproduces the reviewed 5CM output in offline replay and
both returned Cedar 10/11 preparations. Terminal numerical-source collection
is complete. Complete modified-terminal adaptation,
new native bundle validation, geometry trials, refinement and adoption remain
subsequent operations. No existing native qualification check is relaxed.

## Explicit modified-terminal and revised-bundle validation

`cif_terminal_preparation.prepare_terminal_component` wraps the existing linked
preparation with a captured native numerical authority. It verifies the exact
resource receipt and all anchored outputs, completed canonical control and
source preservation, then adds the native O5′/H atom operations, bond and angle
only at explicitly declared free 5′-OH sites. The shared base and unselected
internal/phosphate contexts stay unchanged. Unknown shapes, naming collisions,
unsupported types and changed authorities are refused. Existing formal charges
are retained; the new H receives `?` because the native source supplies partial
charge only. No H coordinate or replacement numerical target is invented.

`scripts/build_cif_terminal_bundle_probe.py` builds
`12_Cedar_probe_cif_terminal_bundle.py`. It verifies every payload in the exact
returned Cedar 09/11 ZIPs, materializes only declared inputs, reuses the existing
43-site shared-code control and prepares the reviewed 5CM derivative explicitly.
Baseline and candidate use the same model. The selected candidate changes are
IGU E:1 hydroxyl treatment and 5CM A:7 torsion preparation; IGU A:6 stays internal.
The selected installation, captured module/source hashes and dispatcher are
checked before and after native execution through a declared installation
anchor. `--linked-review-zip`, `--terminal-review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds` and `--inspect-only` remain explicit options.

`cif_terminal_qualification` preserves the old linkage/custom-proxy/charge gates
and adds full projected row comparisons, including neutron bond targets and
torsion alternate readback. It requires the corrected 5CM torsion quartet,
primary target, weight, period and alternate in the actual native proxy.
All unselected effective definitions and recorded unaffected proxy rows must
remain equal. No missing native readback becomes a pass.

The whole-bundle outgoing-endpoint audit uses declared links, exact atom types
and graph adjacency, not hydrogen spelling or distances. Read-only replay of
the prior Cedar 09 return identifies retained O3′ H at 1AP A:5, 5CM A:7,
DZ A:12 and DP B:4. These are pre-existing linked-state REVIEW findings;
the Cedar 12 candidate preserves them visibly for subsequent explicit review.
`REVIEW`/exit 2 can therefore remain after successful interpretation, alongside
unavailable formal charges. Returned Cedar 12 verifies all 116 payloads and
completed baseline/candidate interpretation under Phenix 2.2.1-6174 (both
exit 0). The 95 passing checks include projected definitions, the corrected
5CM torsion/alternate proxy, all unselected definitions and unaffected proxies.
Six formal-charge checks remain UNSUPPORTED and the same four outgoing-H checks
remain REVIEW. Offline qualification replay reproduces all 105 outcomes and
evidence after sorting only unavailable-charge items by atom ID; the aggregate
verdict stays REVIEW. Exact receipts are indexed in the
[native evidence record](cif-linked-native-registration-evidence.json).
No model coordinates, ReadySet inputs, refinement checkpoint or production
dictionary are adopted or optimized by this probe.

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
