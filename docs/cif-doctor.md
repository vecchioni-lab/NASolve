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

### Explicit curated outgoing-oxygen candidates

`cif_outgoing_preparation.prepare_outgoing_component` accepts a preserved
curated dictionary, model, explicit same-code site contexts and a successful
captured detailed native receipt. It verifies every anchored native input and
output, the exact model and declared backbone links. Before changing a selected
site, every projected atom, bond, angle, torsion, chirality and plane row must
match the captured native definition under the existing torsion policy.

At an explicitly declared outgoing link, the bounded supported motif is O3′
with C3′ and exactly one graph-identified H/D neighbor, single bonds and OH1
typing. The recorded canonical DNA outgoing control supplies OC2 typing; no
partial charge or numerical target is borrowed. A new per-site modifier removes
that H/D and changes only O3′ typing. Existing modifiers stay in place. The
projection removes H-dependent rows and preserves all remaining values and
formal/partial charges. True free 3′ ends remain untouched. Coordinate-H
deletion, unknown authorities, changed inputs, inconsistent contexts and
unsupported motifs are refused. Sources and the coordinate model are preserved.

This is an explicit diagnostic adaptation of already captured curated inputs,
separate from whole-component generation/quarantine and production PostMR.
Before/after Doctor findings are retained; source REVIEW does not become whole
dictionary approval. No pH, replacement targets or achieved geometry is inferred.

`scripts/build_cif_outgoing_bundle_probe.py` builds
`13_Cedar_probe_cif_outgoing_bundle.py` for the exact Cedar 12 ZIP. All 116
payloads verify before declared native members are materialized. Offline
preparation proves all 24 source/native projection checks and selects 1AP A:5,
5CM A:7, DZ A:12 and DP B:4, using captured canonical DC A:4 as the type authority.
The probe replays the unchanged Cedar 12 baseline, then adds only the four
selected modifiers to the same dictionaries, parameters and 877-atom model.

`cif_outgoing_qualification` retains the terminal qualification checks and adds
full captured-baseline replay and exact prior/new modifier IDs at every site.
It keeps the reviewed 5CM torsion/alternate gate, all 38 outgoing-H audits,
unselected definitions and every recorded unaffected proxy. Installation/module
hashes and frozen inputs are checked before and after. Formal-charge limitations,
existing source reviews and broader geometry/stereochemical review remain separate;
REVIEW/exit 2 can remain after
successful native execution. Explicit input/installation/timeout/inspect-only
options and all previous runs remain available.

Returned Cedar 13 completes all four preparations and preserves every frozen
input, but stops before native interpretation because the omitted
`--phenix-root` became `None`. The corrected Cedar 14 delivery uses the working
versioned default `$HOME/Applications/phenix-2.2.1-6174`. An explicit
`--phenix-root` still selects a relocated installation, which must pass the
same version, dispatcher and source-hash checks. The new CLI regression uses
the real loader and executable discovery with explicit external-program
fixtures. Candidates and scientific qualification gates are unchanged.

Returned Cedar 14 completes both installed Phenix 2.2.1-6174 interpretations,
exit 0. All 141 payloads and anchored native files verify; offline qualification
replay reproduces **138 PASS and nine UNSUPPORTED formal-charge checks** after
sorting only unavailable-charge items by atom ID. All four outgoing-H findings
clear, and all 38 endpoint audits pass. Exact modifier IDs, projected definitions,
captured-baseline replay, unselected definitions, unaffected proxies and the
reviewed 5CM torsion/alternate all pass. Coordinates remain the same 877 atoms
at 43 sites. Aggregate REVIEW preserves unavailable charge evidence and does
not approve existing source reviews, achieved geometry or experimental chemistry.

The correction rule has no component-code or hydrogen-name allowlist. Existing
regressions exercise a synthetic `ZZZ` component with misleading H names and D,
an outgoing site alongside a true free end, OP2 H and retained terminal phosphate.
Unknown motifs, missing contexts, changed authorities and coordinate-H deletion
are refused. This generality covers the explicitly supported OH1 O3′–C3′/H
motif with captured canonical authority. The Cedar probe is deliberately pinned
to reviewed inputs; the hash-scoped historical 5CM correction and future
production integration retain their separate evidence requirements. Exact
returned hashes and software checks are in the
[native evidence record](cif-linked-native-registration-evidence.json).

### Captured Cartesian geometry review

`cif_captured_geometry.review_captured_geometry` is a separate read-only
diagnostic for detailed native inventories. It verifies atom identities,
indices, coordinate correspondence and proxy counts, then reports Cartesian
simple-bond distances, central angles and ordered chirality triple products.
The signed nominal deviation is `(observed - target) * sqrt(weight)`; a recorded
`both_signs` flag compares absolute ordered volume. All original targets and
weights are retained. Missing/negative/zero weights, degenerate measurements,
nonidentity bond symmetry and deferred proxy kinds remain visible.

This is descriptive geometry evidence, **not a native residual calculation or
scientific acceptance gate**. Existing captures omit some symmetry, slack and
top-out conventions; angle/chirality values use recorded Cartesian endpoints
without inferred transforms. Counts at nominal absolute deviations of three
and five are ranking aids. Dihedrals, constant dihedrals, ASU bonds, planes,
parallelities, sugar pucker and independent absolute stereochemistry remain
unassessed. The diagnostic cannot approve source chemistry or replace full
geometry/refinement qualification.

`scripts/build_cif_geometry_review_probe.py` builds the source-bundled
`15_Cedar_probe_cif_geometry_review.py` for the exact verified Cedar 14 ZIP.
It validates all 141 payloads and the captured receipt/report agreement, freezes
all 47 referenced native members and preserves the original archive. It carries
forward the earlier 138 PASS/nine UNSUPPORTED outcomes and existing source
assessments without reevaluating them as new native results. It writes a full
JSON report, short summary, provenance and 51-payload review ZIP in a fresh
directory. Successful review remains REVIEW/exit 2. Explicit archive/output
options remain; no new Phenix/Coot call or package installation is needed.
Actual-input replay and source-isolated relocation pass. Production PostMR,
automatic adoption, model coordinates and prior qualification gates are unchanged.

Returned Cedar 15 verifies all 51 payloads and all 47 byte-identical frozen
native members. Offline replay matches the report except computed-scalar
platform roundoff of at most 7.11e-14; identities, targets, weights, statuses,
ranks and threshold counts agree. It records 50 simple-bond and 107 angle
nominal absolute deviations at least five, with no recorded chirality sign
conflicts. For example, DX D:3 C2–O2 measures 5.129713 Å while its declared
dictionary coordinates measure 1.215504 Å and the native target is 1.215 Å.
The distorted model coordinates are identical at all 858 atomic identities
shared with Cedar 05. This localizes the problem before the later
dictionary diagnostics; the responsible construction step remains unproven.
Review frozen construction/parent-restoration and graph correspondence before
selecting any repair. Full geometry and chemical approval remain separate.

### Original construction-stage provenance

`cif_construction_provenance` snapshots explicit stage artifacts from a declared
run whose prepared-model hash and size match reviewed evidence. The saved Coot
script is parsed with Python AST; it is never executed. Literal references
rebase only through the declared historical run anchor; outside-run paths stay
uncollected. All recorded source/frozen hashes are rechecked after analysis.
Missing stages and receipts remain explicit. Unsafe paths, source symlinks,
changed inputs, duplicate atoms and multiple PDB models are refused.

The audit selects intrasite bond/angle cases at nominal absolute deviation
at least five from the captured geometry report, independent of component code.
Single-model PDB stages must match the exact site, altloc, atom name, component
and element. It records first-observed outliers and adjacent comparable-stage
threshold crossings; a gap cannot prove a transition. Same-name parent
coordinates are compared descriptively (within 0.001 Å after a difference over
0.01 Å), without claiming chemical/graph correspondence. Chronology and observed
coordinate copies do not by themselves establish the responsible algorithm.

`scripts/build_cif_construction_probe.py` builds the explicit Cedar 16 runner
for the exact returned Cedar 15 ZIP and original-run binding. The original run
is read-only; `--run` supports relocation. The runner writes a new frozen
evidence inventory, construction report and review ZIP. It requires Python's
standard library and performs no new Coot/Phenix execution, remapping,
optimization, refinement or adoption. Successful analysis retains REVIEW/exit 2
and root cause NOT_ESTABLISHED. The returned Cedar 16 capsule now verifies all
74 payloads, including 19 recorded original-run artifacts. Offline report
replay confirms 55 raw→restored threshold crossings at eight sites. Replaying
the legacy restoration on frozen inputs reproduces the restored model byte
for byte. Thus the same-name/element copying operation reproducibly damages
these captured geometries; not every MR/raw outlier is attributed to it.
The read-only receipt is preserved without rewriting its causal verdict.

### Separate attached-fragment restoration candidate

`cif_fragment_restoration` constructs an explicit candidate from a reviewed
baseline model, raw Coot coordinates, saved parent controls and captured
effective component graphs. The rule requires the complete explicit DNA
sugar/phosphate graph and a connected heavy-atom base attached only at C1′.
The base is selected by connectivity, with no component-code, glycosidic atom
name or N-versus-C linkage allowlist. It forms right-handed orthonormal frames
at raw and preserved C1′, with O4′ defining the first axis and C2′ the plane,
then transports the complete raw base by a proper rigid rotation/translation.
Parent base coordinates are never copied. All sugar/phosphate and unselected
coordinates, atom identities and noncoordinate PDB fields stay unchanged.
The baseline scaffold must match the exact frozen parent. A distance guard
allows at most 0.002 Å change within the fragment plus C1′ after PDB rounding;
attachment orientation must survive. These are implementation invariants,
not chemistry or achieved-geometry approval.

Unsupported sugar bond types/graphs, multiple attachments, disconnected
fragments, hydrogen-bearing grafts, alternate/insertion contexts, degenerate
frames and ambiguous/mismatched source identities are refused. Every declared
site is assessed; unsupported sites remain explicitly recorded and unchanged
in a partial candidate. The actual input excludes DF A:19 because three sugar
bonds are aromatic. Eight supported contexts transport 84 base atoms. The
largest fragment-distance change is 0.001040 Å. Captured-proxy prediction changes
nominal deviations at least five from 50→34 bonds and 107→72 angles, with zero
recorded chirality sign conflicts. Raw/sugar/source defects remain; no target
is retuned or model optimized.

`scripts/build_cif_fragment_restoration_probe.py` builds the Cedar 17 shuttle.
It verifies the exact Cedar 16 ZIP and every payload, freezes its contents,
and writes eligibility, preparation, predicted geometry and candidate files.
`--inspect-only` skips new native execution. Otherwise, the selected Phenix
version/dispatcher and four API source hashes must match the capture before
and after interpreting the candidate with the unchanged 18 dictionaries and
11 PHIL inputs. Qualification compares every native atom identity, effective
site definition, custom request and detailed proxy/target/weight with the
capture, and checks the exact candidate coordinates. It also records all new
native Cartesian measurements. Prior qualification and source reviews remain
visible, including unavailable formal-charge readbacks. The captured baseline
is not re-executed. No Coot, ReadySet retry, minimization, refinement or adoption
is performed. Successful mechanics retain REVIEW/exit 2.

Generic regressions, the full 1,543-test suite and actual-input deleted-build
transport pass. Returned Cedar 17 verifies all 129 payloads and 14 native
mechanics checks. Preparation replays byte for byte and native geometry
confirms the predicted counts. Intrasite improvements do not prove a sound
pairing pose: CGY–DX contacts include 9.357476 and 6.818964 Å versus 2.8 Å
targets; the latter worsens from 2.947120 Å. This is a
separate diagnostic candidate; ordinary PostMR retains the demonstrated legacy
restoration issue until a separately qualified integration is adopted.

### Effective/source graph recovery

`cif_effective_source_recovery` selects unsupported effective scaffolds only
when the recorded source component/input index and exact SHA-256/size match an
explicit resource inventory, and that source supports the DNA graph. Matching
uses content/hashes, never residue or filename exceptions. Missing, ambiguous,
changed or unsupported sources, incomplete shared-code contexts and prior
modifiers without a composition policy are blocked. Supported effective graphs
do not trigger regeneration. DF's frozen source has single sugar bonds; the
aromatic declarations are in its effective definition.

The Cedar 18 runner reuses whole-component source-preserving eLBOW generation
and explicit linked preparation. A native trial with coordinates held fixed
checks full projections, unaffected definitions/proxies, backbone links, custom
restraints and exact modifiers. Only passing mechanics and the already explicit
unavailable formal-charge readback permit a separate fragment restoration and
second native trial. Charge contradictions and every other review/unsupported
mechanics outcome stop it. Dictionary and coordinate effects have separate
reports; different objectives are not comparable geometry rankings.

`scripts/build_cif_effective_source_recovery_probe.py` builds the exact
Cedar 17 capsule workflow. `--inspect-only` performs source planning;
`--source CODE=/explicit/path` retains a hash-bound override. Existing
Python/Biopython/Phenix with eLBOW suffice. Captured version/dispatcher/four API
hashes are checked and generation capabilities recorded. Originals and prior
reviews survive; successful analysis remains REVIEW/exit 2. Dictionary generation
may optimize its independent component, but model minimization, pairing-pose
adjustment, Coot, ReadySet retry, refinement, integration and adoption do not
run. Generic regressions, 1,568 full tests and actual-input deleted-build
planning pass. Returned Cedar 18 verifies all 252 payloads, source-preserving
generation, 68 PASS/one unavailable charge check and 14 fragment mechanics
checks. Linked files and the nine-atom candidate replay byte for byte; raw
geometry and pairing contacts remain under review.


### Separate fixed-definition geometry trial

`cif_fixed_geometry` reconstructs an explicitly captured manager with the same
model, dictionaries and parameter files, and refuses changed atom coordinates,
identities, site definitions, detailed proxies/custom requests or native APIs
before optimization. One all-coordinate geometry-only scitbx L-BFGS trial uses
that fixed manager with installed flags enabled and normalization false. It
records symmetry, Python/compiled optimizer hashes, static constraint signatures,
per-term native residuals, gradient norms, accepted steps and the actual stopping
log. Default bounds are 500 iterations, 10,000 calls and 1,200 seconds. A cap or
error cannot become a convergence claim; special-position contexts are refused
until an explicit constraint policy exists.

Full-precision endpoints and energy stay separate from the new PDB's 8.3 rounding.
Only coordinate columns change; headers/metadata and source inputs survive.
The runner records per-site displacement and requires the serialized candidate's
new native interpretation to preserve exact identities, effective definitions,
all detailed proxies/counts and custom requests. Cartesian bond/angle/chirality
reviews remain descriptive; native nonbonded energy uses installed symmetry and
exclusions, while a separate contact/clash inventory remains unassessed.

`scripts/build_cif_fixed_geometry_probe.py` builds `19_Cedar_probe_cif_geometry_trial.py`
for the exact verified Cedar 18 capsule. Existing Python and Phenix suffice;
`--inspect-only` tests frozen-input transport without optimization. Source/charge,
independent stereochemistry, sugar pucker, pose, diffraction evidence and full
scientific qualification remain review gates. Native numerical completion alone
cannot authorize selection/adoption. All outcomes stay REVIEW/exit 2; installed
PDB postcheck remains pending. Returned optimization is recorded below. Ordinary
PostMR and earlier runs remain unchanged.


The returned Cedar 19 capsule verifies completed optimization at the explicit
500-iteration limit, **not converged**. Serialization then stopped because native
atom ordering differed from PDB record ordering. The serializer now validates a
one-to-one supported identity map using chain/residue/insertion/alternate/atom
name, plus component/element and original-coordinate guards. It maps final
native endpoints back to the original PDB records without changing record order
or metadata. Missing, duplicate or changed identities remain blocked.

Cedar 20 uses the existing builder with `--delivery-prefix 20_Cedar` and the
runner's explicit `--completed-trial-zip`. This accepts the exact verified
Cedar 19 return and its preserved Cedar 18 baseline, checks saved inputs/manager/
constraint signatures, and resumes serialization/native postcheck from saved
full-precision endpoints. It runs no new optimization and preserves the original
limit/gradient evidence. Offline actual-input replay matches all 877 coordinates;
new installed native postcheck and scientific qualification remain pending.


### Native reload attribution

The returned Cedar 20 serialization is byte-exact. Its fresh native interpretation
preserves identities/definitions and every original proxy, and adds five hydrogen
bonds and ten angles. All five contacts cross the same 3.4 Å native cutoff;
native PHIL input is byte-identical. The exact comparison correctly remains
11 PASS/three REVIEW. This differs from loss of an original restraint or a
changed chemical component.

`cif_native_reload.audit_native_reload` records full proxy multisets and can
attribute only a narrow pattern: explicit caller-supplied origin/cutoff,
unchanged identities/definitions/custom requests, no removed terms, cutoff
crossings and two associated endpoint angles through existing covalent stems.
Other changes stay unexplained. Classification is always REVIEW, not installed-
source causal proof or a waiver of the original exact comparison.
`audit_saved_endpoint_readback` separately checks PDB-precision equivalence to
the saved fixed-manager rounded vector, with explicit native float roundoff and
a historical energy basis. It does not calculate a new fresh-manager energy.

Cedar 20's 877 readback coordinates agree at PDB precision (at most 7.11e-15 Å
float difference); the recorded fixed-manager evaluation and iteration-limit
verdict remain preserved. No additional Mac run is required for that review.
Cedar 21 now verifies explicit fixed hydrogen-bond membership. Input-file
equality alone cannot ensure freshly
generated manager equality; scientific qualification and adoption remain open.

**Accepted pairing and stacking authority:** NARestraints pair selections,
stacking relationships, mapped base planes and recipe targets
supersede Phenix's automatic secondary-structure guesses whenever NARestraints
supplies the pairing or stacking policy. Native interpretation must compile the intended
contacts without competing automatic additions or a distance-based omission of
an intended contact. Phenix remains the native restraint consumer and geometry
measurement engine; this authority does not waive identity, component, covalent
geometry or achieved-geometry checks. A separate diagnostic compiler now prepares explicit membership and
suppression of competing inference; both Cedar 21 native checks pass and
ordinary PostMR is unchanged.

The existing NARestraints stacking builder applies its shared base-class plane
mapping to chain neighbours. Canonical stacks use explicitly selected native
`stacking_pair` records; mapped modified stacks use explicit parallelities with
target 0 degrees and sigma 0.027. These are two compilation forms of the same
NARestraints-owned policy. Preserve their requested relationships when suppressing
competing inference. Cedar 21 compiles those declarations to explicit mapped
parallelities before disabling native secondary-structure construction. Unknown
mappings currently retain a generic declaration with a warning; verify actual
native coverage rather than assuming that fallback produced a plane. Track
physical stacks separately from base-pair parallelity/planarity and compare
expected relationships, mapped planes and targets/weights on readback.

The membership design will reuse NARestraints' existing pair guesser and
recipe builder. Its permissive geometry scoring and antiparallel-run rescue
provide pairing hypotheses, while the builder maps selected pairs to explicit
recipe contacts. NASolve already exposes this route through opt-in
`--modified-pairs-only`; that does not establish the origin of Cedar 20's frozen
pair selections. Keep guessed, reviewed/frame-selected and native-generated
membership distinguishable, retain scores/warnings, and compare actual proxies
for missing, extra or overlapping terms before freezing any new trial. A
topological guess or fixed contact set does not certify pairing chemistry;
diagnostic Phenix guesses do not acquire authority by passing a distance cutoff.

### Explicit NARestraints membership diagnostic

`cif_na_policy.compile_na_policy` prepares a separate input bundle from frozen
pair/stack declarations and the existing explicit edits. It reuses NARestraints'
workbook atom mappings, pair recipes and stacking-plane generator; it does not
rescore or discover pairs from the changed coordinates. The bounded first slice
supports unambiguous single-model chain/residue selections, declared Saenger
19/20 pairs matching configured recipes, and mapped stack declarations. Unknown
settings, alternate/insertion contexts, missing atoms or overlapping generated
edits stop before output. All non-SS input lines and original files survive.

**Methods.** The compiler records declaration provenance, resolves recipe atom
selections against captured native identities, emits explicit pair contacts and
mapped parallelities, and rejects duplicate physical requests. Once all declared
generic relationships have explicit representations, a separate final control
disables native secondary-structure construction. Existing modified-base edits,
component modifiers and all dictionary bytes remain. `qualify_na_policy` checks
exact requests/targets/weights, full retained proxy rows and component/identity
invariants using the installed origin registry. New native metadata is opt-in;
the ordinary inventory and pipeline defaults are preserved.

Cedar 21 verifies the exact returned Cedar 20 capsule and applies one policy to
two preserved coordinate sets: the initial model and saved PDB endpoints. This
is an interpretation-only test of membership stability, not another optimization.
Actual-input offline compilation produces 31 new bonds, 52 angles and 35
parallelities for 12 pair and 23 stack declarations, retaining the prior explicit
edits. The returned Phenix 2.2.1-6174 interpretations each pass **14/14 exact
mechanics checks** (6.298652 s and 1.450339 s, exit zero). All 491 payloads and
367 frozen prior payloads verify; the 19 dictionaries, component definitions,
modifiers, 38 backbone links and all captured static proxy rows survive. Both
managers contain 52 explicit bonds, 86 angles, eight planes and 58 parallelities,
with no competing SS-origin terms. The native effective PHIL and eight API
fingerprints match across cases. Compiler replay is byte-exact.

This verifies declared membership at two saved coordinate sets. No new
optimization occurs. The saved endpoint has four bond/ten angle nominal
deviations at least five and no sign conflicts among 158 recorded chirality
proxies; those descriptive counts do not establish geometry or convergence.
The objective differs from Cedar 19/20; historical energies and its iteration
limit are not reclassified. Geometry, source/charge and scientific approval
remain REVIEW, with no production integration or automatic adoption. The next
step is the separate fixed-policy geometry trial described below.

### Geometry trial under the verified NARestraints policy

`scripts/build_cif_na_geometry_probe.py` builds the source-bundled Cedar 22
runner, `22_Cedar_probe_cif_na_geometry.py`. It accepts only the exact verified
491-payload Cedar 21 capsule. Both native membership prerequisites replay
offline, and all previous evidence remains preserved. `--inspect-only` checks
that path without native execution. The installed trial starts from the captured
saved endpoint with its 19 dictionaries and 13 compiled PHIL inputs; it does
not rerun pair guessing, regenerate definitions or recompile policy.

**Methods.** The existing fixed-definition native engine rebuilds the captured
manager and requires exact initial coordinates, identities, component mappings,
geometry, eight installed API sources and native SS/origin metadata before
calling L-BFGS. The opt-in `policy_inventory=True` leaves the existing default
contract intact. One trial permits at most 1,000 iterations and 20,000 objective
calls, with a default 1,200-second native-phase timeout. Native geometry flags,
symmetry, nonbonded handling and static definitions remain fixed. The receipt
records actual stopping/limit/error evidence, gradients, objective terms and
optimizer source hashes. Full-precision endpoints and PDB-rounded fixed-manager
energies remain separate, alongside coordinate displacements and descriptive
bond/angle/chirality measurements.

Identity-based serialization writes only coordinate columns in a separate PDB.
Native reread uses the same input bytes and opt-in policy inventory.
`qualify_fixed_policy_geometry` retains the 14 existing exact identity,
definition, coordinate, request and static-proxy checks, then requires successful
interpretation, the same explicit policy with no competing SS-origin terms,
and exact installed APIs: 17 checks in this slice. No exact comparison is
relaxed. Dynamic nonbonded neighbours may change with coordinates; they are
reported separately from the static proxy contract.

Actual-input offline prerequisite replay and synthetic worker/transport tests
are distinct from installed native execution. Returned Cedar 22 verifies all
609 payloads and 491 unchanged prior payloads plus their manifest. Phenix
2.2.1-6174 completes the trial in 4.4478 s and reread in 1.737436 s, exit zero;
all 17 exact mechanics checks pass and serialization replays byte for byte.
The fixed-policy objective decreases 24.26% and gradient norm 91.17%, but the
line search reports rounding errors preventing progress at 905 iterations /
970 calls, with a false native criterion: retain NOT_CONVERGED_ERROR.
This precedes PDB serialization. PDB rounding separately changes the recorded
gradient norm from 91.28 to 907.04, so preserve full-precision endpoint evidence.
Nominal distance deviations >=5 decrease four to three, while ten angle
deviations remain and no chirality sign conflicts appear. All three remaining
distance outliers are CGY A:20–DX D:3 hydrogen bonds at 4.34–5.58 Å against
2.8 Å targets; one worsens slightly. Nine angle outliers involve that pair and
one involves DP B:4 N5. Pair pose/intent, local definitions and numerical
line-search/gradient behavior need review before another trial; no target
change or automatic rerun follows from this descriptive evidence alone.
A limit/error remains nonconverged, and meeting a native criterion does not
certify complete geometry, source/charge, pucker, absolute stereochemistry or
experimental fit. Overall REVIEW/exit 2 and no adoption remain deliberate.
Only within-trial energies share this new policy; Cedar 19/20 retain their
historical objective and stopping record. Ordinary PostMR is unchanged.

### Saved native gradient audit

`scripts/build_cif_gradient_audit_probe.py` builds the separate Cedar 23 runner,
`23_Cedar_probe_cif_gradient_audit.py`. It accepts only the verified 609-payload
Cedar 22 capsule, replays its 17-check mechanics and stopping evidence, preserves
all earlier payloads and assesses the same 19 dictionary files with CIF Doctor.
The existing planar-angle rule detects the retained DP N5 conflict; this probe
adds no replacement target. All explicit intersite distance groups are reported
at the saved full-precision coordinates. Six coordinate-probe atoms are selected
from the largest bond/angle nominal deviations, using native indices and labels
with no residue-code or site allowlist.

**Methods.** `cif_gradient_audit.run_native_gradient_audit` rebuilds and exactly
matches the captured initial identities, coordinates, definitions, geometry,
policy/origin metadata and eight installed API sources. The six installed
numerical-source hashes and full static constraint signature must also match
Cedar 22. Saved full-precision and PDB-rounded vectors are evaluated without
optimization. Each case records the full objective plus isolated bond, angle,
dihedral, chirality, planarity, parallelity and nonbonded controls. The controls
change evaluation flags only, with no definition/input edits or adopted model.

Analytical directional derivatives are compared to central energy differences
at steps 1e-3, 1e-4, 1e-5 and 1e-6 Å. Directions include the full gradient,
an alternating global direction, the selected atom axes and each category's
gradient. Every sampled value remains visible; consistency requires agreement
at two consecutive steps within absolute 1e-4 plus relative 1e-4. Separate
repeat/snapshot and additivity checks use absolute 1e-8 / relative 1e-10.
These numerical tolerances do not change native proxy comparisons. The audit
also retains full per-family gradients, local descent profiles, neighbour
counts and captured-versus-rebuilt energy/gradient-norm comparisons. Static
constraints and installed source hashes must remain unchanged afterward.
The cap is 4,000 native energy calls and a default 1,200-second timeout.

This is a bounded diagnostic of sampled numerical consistency. A discrepancy
requires interpretation of step dependence, controls and neighbour behaviour;
it does not by itself identify a Phenix defect. Agreement cannot prove every
gradient component, global convergence, intended pairing chemistry or
experimental fit. No minimization, target retuning, candidate model, diffraction
refinement or adoption occurs.

**Returned Cedar 23 evidence (2026-10-19).** All 670 payloads verify; the
609-payload prior capsule and its manifest remain byte-identical. Phenix
2.2.1-6174 completes 2,734 energy evaluations in 7.8046 s, native exit zero.
Exact manager, API/numerical sources and static constraint signatures match.
In both coordinate cases, parallelity and the full objective fail 18/21
sampled directions; each other category passes 21/21. Baseline repeats,
captured snapshots and additivity agree. The parallelity count remains 58
through its isolated samples. Dynamic nonbonded neighbour counts can vary;
this evidence does not claim exact dynamic neighbour membership.

An independent spectral plane calculation reproduces native energies and
selected central differences. Applying the public CCTBX accumulation-loop
bounds to those analytical plane gradients reproduces every saved parallelity
gradient component to about 1e-12. The public loop accumulates only
`max(0, j_size - i_size)` second-plane contributions. The immutable primary
[source blob](https://api.github.com/repos/cctbx/cctbx_project/git/blobs/25d3a75f20d3611dcb32d919a893bc0beb18e6a0)
and exact derived metrics are recorded in the
[native evidence ledger](cif-linked-native-registration-evidence.json).
This strongly indicates an accumulation defect, while the installed C++ header
identity and isolated native per-proxy reproduction remain unverified. Small
negative-gradient steps still reduce energy; a causal explanation of the
prior line-search failure remains open. The next check isolates that installed
calculation without changing NARestraints selections, planes, targets or weights.
`--inspect-only` performs capsule, distance-group and dictionary checks offline.
The finite-difference method follows the same checking principle used in the
[CCTBX gradient tutorial](https://cci.lbl.gov/docs/cctbx/tuto_rigid_body/);
actual installed source identities remain pinned by the captured hashes.

### Installed per-plane accumulation diagnostic

`scripts/build_cif_parallelity_audit_probe.py` builds Cedar 24,
`24_Cedar_probe_cif_parallelity_audit.py`, from the verified 670-payload
Cedar 23 ZIP. It verifies the nested prior/native evidence, replays Cedar 22's
17 mechanics checks and preserves its stopping classification. It executes no
captured code. `--inspect-only` checks the source-bundled capsule and mechanics
offline. Returned installed execution is recorded below.

**Methods.** The installed worker rebuilds and exactly matches the initial
manager and source/constraint fingerprints. The two newly consumed Python
adapter modules are also fingerprinted before/after evaluation, without claiming
a retrospective Cedar 23 source match. For all 58 captured plane restraints
at both saved precisions, it obtains `parallelity(...).gradients()` and scatters
every first/second-plane contribution by atom identity. Independently, it
calls `parallelity_residual_sum` on a singleton container. Both kernels retain
full gradients, residuals and repeated baselines. Three directions and four
central-difference steps test each original and swapped plane order. Swapping
retains the same identity order and target/weight metadata; it is an isolated
diagnostic control, not a changed NARestraints policy.

Three asymmetric tilted controls use 4/4, 4/6 and 6/4 atoms, also both orders.
At each saved crystal coordinate set, the worker additionally compares manually
scattered gradients, the actual full proxy container, manager evaluation and
every captured Cedar 23 parallelity gradient component. The supported slice is
zero-target, zero-slack, non-top-out, symmetry-free planes; unsupported inputs
fail visibly. Limits are 7,000 single/container evaluation pairs (two residual
kernels per pair), plus two whole-batch comparisons, and 1,200 seconds. The
58-proxy input requires 6,188 pairs. Numerical tolerances match Cedar 23 and
do not change exact native inventory gates.

Available `parallelity.h` and `parallelity_bpl.cpp` bytes are frozen from the
imported geometry-manager package directory, with checksums and explicit missing
status. Header identity alone does not establish the source used to compile
the pinned binary. These controls can isolate an accumulation failure; they
cannot prove why the earlier optimizer stalled or approve chemistry or
convergence. No optimization, native patch, target/weight edits, new crystal
model, diffraction/refinement or adoption occurs. Existing pairing/stacking
authority remains with NARestraints. Exact software checks and source blob IDs
are in the [native ledger](cif-linked-native-registration-evidence.json).

**Returned evidence (2026-10-19).** All 732 payloads and the frozen 670-payload
prior plus manifest verify. Phenix 2.2.1-6174 completes 6,188 evaluation pairs
in 3.483823 s, native exit zero, with unchanged initial manager, native/numerical
source hashes and static constraints. All 17 prerequisite mechanics checks replay.
All 714 sampled single-restraint directions pass; every one of 238 accumulated
orders fails the second-plane and alternating directions. Energies, repeated
arrays and individual-gradient plane-order invariance agree. Accumulated
gradients depend on plane order. For the 4/4 tilted control, the second-plane
gradient norm is 2.21375 individually and zero after accumulation.

Installed header/binding files match the recorded public source blobs. The
second loop adds only `max(0, j_size - i_size)` second-plane contributions.
That model reproduces every per-order accumulation array exactly; the full
manager and full native container reproduce the same incomplete gradient.
The confirmed scope is the installed non-unit-cell path for these supported
proxies and controls. Compiled-source provenance and other versions/overloads
remain separate questions.

Saved-data recombination replaces only the incomplete parallelity gradient
with complete individual-restraint sums. All 84 Cedar 23 full/parallelity
directional checks then agree, explaining the 72 earlier failures at unchanged
energies, coordinates, directions and tolerances. This is algebraic replay,
not a corrected native manager or optimizer run. Cedar 25 implements the
separate correction audit below. The NARestraints policy remains fixed;
convergence and chemistry remain under review. No repeat Cedar 24 is needed.

### Complete native plane accumulation correction

`scripts/build_cif_corrected_gradient_probe.py` builds Cedar 25,
`25_Cedar_probe_cif_corrected_gradient.py`, from the verified 732-payload Cedar 24
return. The explicit NASolve evaluator retains the native unnormalized energy
and full gradient, subtracts the native accumulated parallelity contribution,
and adds every original single-restraint i/j gradient by atom index. Shared
atoms receive all contributions. No proxy reconstruction, target edit, native
file patch or global monkeypatch is involved. Native accumulation that is
already correct is unchanged; symmetry-bearing planes and special positions
are refused. The implementation consumes the original target/slack/top-out
parameters through the native single-restraint kernel; the actual installed
validation remains limited to this capsule's supported planes.

The probe replays the 17 prior mechanics checks and exactly matches the initial
manager, static constraints and pinned native/API/adapter/C++ source identities.
At initial, saved full-precision and PDB-rounded coordinates, it first matches
the old raw full-objective energy and gradient norm. It also matches both saved
complete and incomplete plane arrays. These raw baselines are not requirements
on the corrected gradient norm.

Fresh full-objective and seven category controls use four central-difference
steps, repeated baselines, target/gradient additivity, outlier-selected atom
directions and the existing numerical tolerances. The audit budget is 5,500
evaluations, plus five recorded preflight evaluations. Complete individual and
container plane residuals must agree on every correction-bearing evaluation;
the returned native energy is unchanged. The probe records
`SAMPLED_NATIVE_DERIVATIVES_PASS` or `DERIVATIVE_REVIEW`, while overall status
remains REVIEW/exit 2. Returned Phenix 2.2.1-6174 execution verifies 4,101 audit
evaluations plus five preflight calls with zero energy change. Both endpoints
pass all 168 sampled directions each. The initial case passes 162/168, retaining
three failures each in the full and parallelity categories. Repeats and
additivity pass in every case; the overall correction stays DERIVATIVE_REVIEW.

This is an opt-in diagnostic, with no automatic production integration or
optimization. A native derivative pass is required before a separate bounded
geometry trial; it cannot establish convergence, chemistry or adoption.

### Plane-order correction and rotated controls

The remaining Cedar 25 initial discrepancy is reproduced by an independent
centered-scatter eigensystem calculation and a model of the installed header's
normal-sign handling. The header negates the second raw normal when aligning
the two normals, but continues differentiating through the original second
plane's row vectors. Four captured initial stacks exercise that branch; the
same model reproduces the complete stored gradient within 3e-12 in norm. Both
endpoints have no such normal-sign flips. This is source/model evidence for
the sign error, separately from the installed accumulation defect already
reproduced by Cedar 24. It does not establish the optimizer failure's cause.

`scripts/build_cif_plane_order_probe.py` builds Cedar 26,
`26_Cedar_probe_cif_plane_order.py`, from the verified 794-payload Cedar 25
return. Its explicit evaluator uses the original restraint's first-plane
gradient for i and the swapped native copy's first-plane gradient for j.
The native copy constructor preserves targets, slack, limits, top-out, weight
and origin ID; every field and swapped residual is checked. Copies are used
only for evaluation. All manager membership and native energies stay fixed,
including shared-atom contributions. This avoids second-plane sign handling
without fitting a replacement objective or choosing exceptional sites.

Before fresh numerical checks, the worker matches the same sources/static
constraints, three raw full-objective snapshots and all three captured complete
and incomplete plane arrays. The full-objective/category audit retains its
5,500-call cap, with six recorded preflight evaluations. A separate all-plane
audit checks every one of the 58 proxies at all three coordinate sets, both
orders, three local directions and four numerical step sizes. It retains both
the original complete kernel gradient and the new two-first-plane gradient,
including their repeated arrays and order invariance evidence.

Equal/unequal tilted 4/4, 4/6 and 6/4 controls are repeated after a 30-degree
rigid rotation about x. This changes the raw-normal orientation branch while
preserving physical plane angles. The audit checks energy invariance and
gradient rotation as well as derivatives. Expected work is 9,360 two-kernel
evaluation pairs under a separate 10,000-pair cap, plus the 4,101 global audit
evaluations and six preflight calls. All numerical tolerances are unchanged.
The per-plane audit currently supports zero-target, zero-slack, non-top-out,
symmetry-free proxies, which cover this capsule. Unsupported cases fail
visibly. Returned Cedar 26 verifies all 857 payloads and preserves all 794 prior
payloads plus their manifest. Installed execution completes in 53.402075 s:
all 504 global/category directions and all 1,080 corrected per-plane directions
pass. Native complete gradients fail eight initial orders and six rotated toy
orders, reproducing the predicted sign cases. All corrected order/rotation,
repeat/additivity and energy checks pass; native energy change is zero.
Qualification is SAMPLED_NATIVE_DERIVATIVES_PASS. This remains sampled evidence;
geometry, convergence, chemistry and adoption stay open.

### Bounded geometry trial with qualified corrected gradients

`scripts/build_cif_corrected_geometry_probe.py` builds Cedar 27,
`27_Cedar_probe_cif_corrected_geometry.py`, from the exact verified Cedar 26
return. It replays the 17 native mechanics prerequisites and recomputes all
stored corrected derivative comparisons before native work. The correction
module must match Cedar 26 byte for byte. The native worker pins the same
numerical modules, adapters, C++ sources, definitions, explicit NARestraints
policy and static constraints. Its full corrected initial gradient and energy
must match the qualified snapshot before L-BFGS can start.

The trial restarts from the same original initial coordinates as Cedar 22.
Default limits remain 1,000 iterations, 20,000 objective calls, gradient epsilon
1e-5 and a 1,200 s native timeout. The original unnormalized native energy is
evaluated with the qualified both-first-plane gradient correction; targets,
weights, definitions, proxy membership, symmetry/exclusions and compiled
pairing/stacking intent stay fixed. Native step history, stopping reason,
errors, criterion result and full-precision endpoints are preserved. Raw native
gradient norms are recorded separately from the corrected norms used by the
optimizer. An improvement or native exit zero does not establish convergence.

After the bounded trial, fresh full-objective and seven category controls
check both full-precision and PDB-rounded endpoints using the same four-step
criteria and frozen coordinate probes, with a separate 4,000-evaluation cap.
The existing exact-identity serializer writes a separate candidate while
preserving all other PDB columns. Fresh native interpretation must pass all
17 fixed-policy mechanics checks. Endpoint derivative qualification, stopping
classification and mechanics remain independent, including when any requires
review. No new guessing, policy recompilation, dictionary generation, ReadySet,
diffraction/refinement or adoption occurs. Ordinary PostMR/refinement defaults
and previous runs remain unchanged.

Returned Cedar 27 verifies all **980 payloads**, including 857 unchanged prior
payloads and their manifest. Phenix 2.2.1-6174 (dispatcher 2.2.1) completes the
trial/audit in **75.822869 s** and PDB readback in **1.565038 s**, both exit zero.
All **17 native mechanics checks** and **336 sampled endpoint directions** pass;
independent replay recomputes all 1,344 four-step samples and analytical dot
products. Candidate serialization reproduces byte for byte, including the
157 native/PDB ordering differences resolved by exact identity.

The fixed objective changes **3784.7499458394077 -> 2697.762263611603**, a
**28.72%** decrease, and corrected norm **1110.520668509296 ->
372.53738052839816**. At **1,000 iterations / 1,028 calls** the stop is
**NOT_CONVERGED_LIMIT**, with no recorded optimizer error and the native
criterion false. All accepted targets decrease; iteration 900 to 1000 still
reduces the target by **31.2321**. Corrected norms fluctuate, so a lower target
does not certify proximity to convergence. The PDB-rounded fixed-manager
target **2700.856094619088** and norm **905.6214940891548** remain separate.

Both precisions retain three nominal distance and ten angle deviations at least
five, and zero sign conflicts among 158 captured chirality proxies. All three
distance outliers remain CGY A:20-DX D:3 contacts at **4.42–5.62 Å** against
2.8 A targets; nine angle outliers involve that pair. The retained DP B:4 N5
angle is **127.638 degrees** against 109.471 degrees. No target changes follow
from those residuals alone. A separately bounded continuation from saved full
precision is justified for the next numerical test, after fresh exact
source/start-vector matching and with new endpoint derivative/mechanics gates.
Cedar 28 supplies that continuation below. Rerunning Cedar 27 restarts the
original model. Geometry, convergence, chemistry and adoption remain open.

### Bounded continuation from saved full precision

`scripts/build_cif_geometry_continuation_probe.py` builds Cedar 28,
`28_Cedar_probe_cif_geometry_continuation.py`, from the exact 980-payload Cedar 27
return. Its reusable engine opt-in `continuation` requires the same qualified
correction, complete endpoint derivative proof, prior limit stopping and exact
native source/static identities. The source-bundled inspector preserves all
prior payloads, pins the captured trial worker/verifier bytes, replays the
17 mechanics checks and recomputes the raw prior derivative evidence. Captured
code is retained as evidence and never executed.

The native worker first rebuilds and matches the original manager and qualified
initial snapshot. It then loads the saved full-precision native atom-order
coordinates and requires the same static signature plus a fresh match of the
**entire corrected gradient and target** to Cedar 27. The expected start is
**2697.762263611603 / 372.53738052839816** (target / corrected norm). Rounded,
reordered or altered points cannot pass that gate. The continuation starts
fresh L-BFGS history; it restores coordinates rather than optimizer memory.

One stage permits at most **1,000 further iterations / 20,000 calls**, gradient
epsilon **1e-5** and **1,200 s** native timeout. It retains prior stopping and
reports new stopping and cumulative optimizer counts separately. Native energy
definitions, all 19 CIF/13 PHIL inputs, explicit NARestraints pair/stack policy
and native sources/static proxies stay fixed. Fresh full/rounded endpoint
derivative audits retain the **4,000-evaluation** cap, and candidate
`candidate/continued_geometry_model.pdb` must pass all 17 native PDB mechanics
checks. New-stage displacement is measured from the saved endpoint separately
from serialization displacement relative to the original initial model.

The actual-input offline inspector and synthetic deleted-build transport pass.
Returned Cedar 28 verifies all **1,104 payloads**, including all 980 unchanged
Cedar 27 payloads and their byte-identical manifest. The published runner and
110-member runtime, trusted worker/correction bytes and installed API/numerical/
adapter/C++ identities match. Phenix 2.2.1-6174 (dispatcher 2.2.1) completes the
continuation/audit in **76.066902 s** and PDB readback in **1.692405 s**, both
exit zero. All **17 native mechanics checks** and **336 sampled endpoint
directions** pass. Independent replay recomputes all 1,344 four-step samples
and exact candidate serialization; it executes no captured code.

The fixed target changes **2697.762263611603 -> 2599.5275576416398 (3.64%)**
and corrected gradient norm **372.53738052839816 -> 144.16496914598542
(61.30%)**. The new stage reaches **1,000 iterations / 1,036 calls**, cumulative
**2,000 / 2,064**, with no recorded optimizer error and the native criterion
false. Preserve **NOT_CONVERGED_LIMIT**. All accepted targets decrease; the last
100 iterations reduce it by **8.7054**, while corrected norms fluctuate. Across
both corrected stages, target/norm decreases are **31.32% / 87.02%**. The
PDB-rounded target/norm **2602.971189992592 / 950.90556704461** are separate.

Both precisions retain **three distance / ten angle nominal deviations >=5**
and zero sign conflicts among 158 chirality proxies. The three CGY A:20-DX D:3
contacts remain **4.360-5.583 A** versus 2.8 A; nine angle outliers involve that
pair. DP B:4 C6-N5-C7 remains **127.749 degrees** versus 109.471 degrees.
Angles contribute 1193.6456 and bonds 553.0823 to the unchanged native target;
individual category gradients can cancel and their norms do not add. These
findings require term/source review before selecting another bounded trial or
a separately declared chemical candidate. No next native delivery is prepared.
Existing corrected/uncorrected trial defaults are unchanged; no new package,
target tuning, policy guessing, refinement, scientific approval or adoption is
introduced.

### Fixed-policy base-orientation audit

`scripts/build_cif_base_rotation_probe.py` builds Cedar 29,
`29_Cedar_probe_cif_base_rotation.py`, from the verified 1,104-payload Cedar 28
return. It replays the entire qualified lineage and all 17 prior mechanics
checks before any native work. Exact correction and installed source identities,
the original inventory/static constraints and complete corrected initial vector
must match. Both saved endpoint family targets and entire gradients must then
match before angular evaluations begin.

The reusable planner selects sites from ranked nominal bond/angle outliers
(default absolute threshold five), reusing the supported connected-base graph
and explicit DNA scaffold rule. The base attachment is graph-selected, including
N- and C-linked cases. Unsupported context and any group-limit omissions remain
explicit. For each selected group, proper Rodrigues rotations about the
C1-prime-to-attachment axis preserve the entire scaffold, attachment atom and
all internal base distances. No original or candidate coordinate file changes.

The fixed grid is **-180, -90, -30, -10, 0, 10, 30, 90, 180 degrees**, sampled
independently for each base at full and rounded precision. The full objective
and seven isolated family controls retain native energies and the qualified
plane-gradient evaluator. The analytic rotational slope is
`sum(g_i dot (axis cross (r_i - origin)))`, in target units per radian. Four
central-difference steps **1e-3, 1e-4, 1e-5, 1e-6 radians** check the full slope
at every angle and each family slope at zero angle. The existing absolute-plus-
relative **1e-4** criterion requires two consecutive passing steps.

Receipts retain baseline repeats, target/gradient additivity, +/-180 energy
agreement, fragment-distance invariance and actual neighbour counts. Selected
outlier distances/angles are measured descriptively at every sample. Intrasite
angle contexts retain exact effective target rows, center-atom types and shared
declared planes. Internal base geometry is fixed during rotation; a parameter
conflict therefore cannot be cleared by this scan. Each lowest grid value is
explicitly a diagnostic sample, not a candidate or a minimum.

The default bounds are **six supported groups / 3,000 total energy evaluations /
1,200 s**. All 17 preflight evaluations count toward the energy cap. Offline
replay selects A:20, D:3 and B:4 by the same generic rule, each with 11 base
atoms; it does not hard-code those identities. The actual-input inspector and
synthetic deleted-build source transport pass. **88 focused and 1,902 full tests
pass**, with two full-suite skips and 276 passing subtests. Returned installed
Phenix **2.2.1-6174 / dispatcher 2.2.1** execution verifies all 1,173 payloads
and passes all 96 sampled rotational directions (384 four-step samples), in
31.56962 s and 1,201 total calls. All three independent coarse grids favor
zero degrees at both precisions; nonzero analytic slopes remain. This result
excludes no unsampled/coupled configuration and establishes no minimum. NARestraints intent,
all targets/weights, original runs and production defaults remain fixed. No
optimization, policy recompilation, dictionary generation, installed native
patch, refinement or adoption occurs.

### Source-graph numerical recovery candidates

`scripts/build_cif_numerical_recovery_probe.py` builds Cedar 30 from the verified
Cedar 29 capsule. The reusable planner inspects declared source angle/plane
contradictions on one independent graph-valid component definition, records all
model sites/modifiers, and supports explicit component selection without a
residue allowlist. The reviewed probe selects DP's retained N5 conflict; other
source reviews remain deferred. This is a candidate-only numerical operation.

A separate graph source preserves exact atom identifiers/elements, H/charge,
bond order/aromatic/stereo declarations and signed chirality. It excludes old
numerical targets, energy types, planes and torsions; the complete original and
removed-field inventory remain frozen. Complete source ideal coordinates may
seed naming/initial geometry. If absent, complete declared source atom x/y/z
are accepted only with explicit `SOURCE_DECLARED_COORDINATES_NOT_INDEPENDENT_IDEAL`
provenance. Partial/nonfinite families, missing/ambiguous formal charges, lossy
naming and graph changes refuse. No experimental model supplies target values.

The existing eLBOW-v4 adapter discovers installed help capabilities and retains
its source-state, explicit-H and chirality controls, isolated output, timeout
and raw evidence. It requests generator-internal geometry optimization; it
runs no crystal-model optimization. The output is compared to both graph source
and original numerical dictionary. Existing graph/state/stereo and numerical
rejection gates remain; complete source formal charges must survive exactly,
without partial-charge substitution. `CANDIDATE_REVIEW` still requires native
site/proxy, source/chemical and scientific qualification. Generation failures
and unresolved findings are retained; no angle is retuned to match the model.

The probe verifies the 1,173-payload capsule, exact trusted worker/core/source
identities and full qualified lineage, recomputes all 96 saved rotation
directions and replays all 17 native mechanics prerequisites. Default bounds
are at most three explicitly selected components and 600 seconds each. Actual
input planning and graph preparation pass. Returned Cedar 30 verifies all
1,185 payloads and preserved predecessors, but installed eLBOW stops before
generation on the lower-case coordinate-tag attribute. No dictionary exists
to assess; its zero-review console count is not a numerical pass.
The original 19 CIF/13 PHIL inputs and NARestraints pairing/stacking policy stay
frozen. No new dictionary is applied, no modifier composition is attempted,
and no ReadySet retry, refinement or adoption occurs. Existing production
defaults and dependencies need no migration.

### Canonical coordinate tags and explicit PDU control

Cedar 31 uses the same numerical-recovery builder with
`--delivery-prefix 31_Cedar --component-control PDU`. It accepts the exact
Cedar 30 failure capsule, validates all 1,185 payloads, both generation receipts,
original/graph inputs and the input-parser/no-candidate outcome, then replays
the preserved C29/C28 derivative/mechanics lineage. The corrected graph export
retains normalized internal lookup but emits canonical
`pdbx_model_Cartn_x/y/z_ideal` tags for the installed reader. Coordinate values
and chemical declarations remain unchanged. Receipts state both source and
output coordinate fields. No output dictionary means numerical assessment
NOT_RUN, not a zero-count result.

`--component-control CODE` is an explicit builder option (up to two controls,
three total candidates). It admits only test fixtures listed with exact hashes
and sizes in [the public control catalog](cif-doctor-ccd-controls.json). PDU's
unmodified 9,033-byte public CCD is the requested exception to the original
local-only control collection. It is bundled under `controls/PDU.cif`, never
installed into `nasolve/data/ligands`. The original 18-control ZIP is unchanged.
The runner freezes the source and records graph/stereo/H/charge, mapped roles
and compiler output, then applies the same independent generation/comparison
gates as DP. No experimental model supplies generation targets.

The generic control API uses the actual NARestraints mapping, pair compiler
and stacking matrix on exact source atom identities. PDU has the T role; AT
compiler controls resolve N3-N1 and O4-N6 contacts and two angles, with a pair
parallelity. Both stacking orders resolve its C7 role to C5A. The propynyl
C5A-C5B triple bond and complete 38-atom/39-bond source survive graph export.
The H named H2 is attached to O3-prime, demonstrating why context rules follow
bonds. A synthetic canonical partner exercises the compiler only. These are
not native proxies or achieved pair geometry, and no PDU is inserted into the
frozen scaffold. Returned Cedar 31 preserves all 1,209 payloads and both
failed attempts: DP stops on missing alt_atom_id; PDU reads 38 atoms, 39 bonds
and three R/S/R centres, then fails in the installed optimizer restart path
after nonconvergence, with an empty XYZ intermediate. Neither produces a
dictionary; chemical and numerical generation assessment remain NOT_RUN.

### Installed eLBOW input contract and source evidence

Cedar 32 uses the same builder with --delivery-prefix 32_Cedar and
--component-control PDU, then runs with --native-contract-only against the
exact Cedar 31 ZIP. The new reader verifies its 1,209 payloads, trusted build,
both receipt/artifact sets, exact original/graph copies and distinct failure
evidence. Prior excluded pickle descriptors remain visible without loading
serialized objects. The 17 native mechanics and 96 rotational direction
prerequisites replay; captured Python is never an executable authority.

The graph exporter supplies alt_atom_id from exact primary IDs only when the
whole column is absent. Existing aliases, including unknown tokens, survive.
The additive atom_alias_metadata receipt records the compatibility metadata
separately from unchanged chemical declarations. DP
graph SHA-256 becomes 3cfff153966194861451113747ba8f1ebbd7b47d58c8aa9acfd50ddfcc4783dd;
PDU graph bytes are unchanged. This fallback is independent of component code.

The explicit input-contract mode derives the installed Python-library directory
from the already verified iotbx/phil.py anchor and copies four exact eLBOW
modules: Utilities.py, optimisation_manager.py, command_line/builder.py and
chemistry/any_chemical_format_reader.py. Each must resolve under the selected
installation and be at most 1 MiB. Copies retain original bytes/hashes and
relative installed/snapshot anchors. AST item-attribute accesses are an
inventory, not an inferred universal required schema. Installed and copied
bytes must match before and after the two input checks. No installed code is
modified, and no captured code or pickle is executed. Native source snapshots
stay in the private review capsule and outside Git.

Each input check requires exact installed help support for a read-only flag
and existing state-retention options, then uses source.cif with read-only,
exact ID, a separate output prefix, add_hydrogens=False, pH=low and
chiral=retain. The owned process group is bounded to at most 60 seconds.
Source and frozen source/dispatcher bytes are checked; unexpected optimizer
markers or nonzero execution retain REVIEW. PARSER_READ_ONLY_PASS means only
exit zero under that recognized input path. No numerical generation or
optimizer setting change occurs. Receipts add requested_action,
installed_elbow_contract and native_input_checks; each input-check directory
has a probe_directory relative anchor. native_execution can now record
READ_ONLY_INPUT_CHECKS without claiming native proxy or geometry qualification.

Existing explicit generation remains the default without this new flag.
Production PostMR, curated dictionaries, NARestraints pairing/stacking policy,
scientific gates and dependencies are unchanged. At that delivery, native read-only checks and source capture were pending.
The returned
Cedar 32 capsule verifies all 1,229 payloads and the four exact source snapshots.
PDU completes read-only parsing (exit zero, 1.371951 s); DP stops in 3.551229 s
on absent atom pdbx_aromatic_flag. The captured reader also requires CCD atom
stereo and bond value_order fields, while the preserved DP dictionary declares
legacy bond type/aromatic flags and signed chiral volumes.

### Reader projection and explicit bounded generation

Cedar 33 uses the same builder with --delivery-prefix 33_Cedar and
--component-control PDU. Run against the exact Cedar 32 capsule with
--single-block-steps 180. It verifies the complete installed contract and prior
qualified lineage, retaining the original DP/PDU outcomes and every source.

prepare_elbow_ccd_input writes a separate consumer file. Formal-charge and
aromatic/stereo aliases must agree after normalization. Only declared single,
double and triple orders translate to SING/DOUB/TRIP; unsupported localization
is refused. Atom aromatic/CIP metadata without declarations is ?, never an
inferred N/R/S assignment. All original non-consumer fields, coordinates, H,
bond stereo and signed chiral volumes survive unchanged, and a semantic
round-trip plus raw Doctor comparison is retained. PDU consumer bytes are
unchanged. DP consumer SHA-256 is
6b914d7fed9a98e30ed68b2381507e6d5bb0dc9b351fee48d42ced085c9501fa.

Fresh installed read-only checks gate each component independently. An explicit
step request requires valued option support from exact installed help and the
four unchanged captured reader/optimizer source identities. The installed
manager uses a positive opt_steps value to skip its default later-block XYZ
reload. Before generation, an installation-bound Phenix Python worker calls
only the installed options parser with the intended source/seed/state/step
arguments. It verifies the imported module path/hash, records the module
snapshot, and requires the requested steps and exactly one effective block.
It records the default tolerance without changing it. Installed/captured option
source bytes are checked after the trial too; captured source is never executed.

The reusable single_block_steps argument defaults to None, preserving installed
defaults; explicit integers are bounded to 1--600. This delivery requests one
180-step block and the existing 600-second per-component timeout. Options
interrogation is bounded to 30 seconds and read-only checks to 60 seconds.
Failure of input checks defers that component from generation; failure to prove
the shared block contract stops the unsupported trial. No installed code is
patched, no prior pickle/partial XYZ is reused, and no tolerance is relaxed.

Candidate interpretation remains separate. Record NOT_CONVERGED_REPORTED
when the native log states geometry not converged; otherwise stopping is
NOT_REPORTED. Exit zero, a CIF file or exhaustion of attempt control does not
prove convergence. Candidates pass through the existing complete source, H,
formal-charge, stereo and numerical gates against both consumer and original
definitions. New raw unknown/alias fields remain explicit comparison evidence.
No result is composed with modifiers or adopted; native proxy, achieved geometry
and scientific qualification remain open. There are no new dependencies or
production-default changes.

### Read-only candidate and native-reader stereochemistry

Returned Cedar 33 verifies all 1,288 payloads and the complete 1,229-payload
predecessor. Both read-only inputs pass under Phenix 2.2.1-6174. DP exits one
in preparatory Chiralise/ChiralClass, before any numerical optimization or output
dictionary. The CCD reader assigns every atom token other than N, including ?,
to its native chiral marker. DP has 35 unknown atom tokens and four preserved
signed-volume declarations. No false nonchiral or invented R/S export is used
to bypass this boundary.

PDU generation exits zero after one explicit block, but reports geometry not
converged. Its candidate retains exact graph/order/H and all 38 explicit zero
formal charges, with zero retained plane/angle findings. All three original
R/S labels are omitted. Generated signed volumes agree with source ideal and
generated Cartesian hands; this is a source-relative comparison, not independent
absolute CIP assignment. Its printed 181-row energy table reaches -517.4105 at
row 146, rises to -477.2222 at row 147 and ends at -480.5612. No intermediate
coordinate trajectory is available to explain that rise.

Use the same builder with --delivery-prefix 34_Cedar --component-control PDU,
then run the generated script against the exact Cedar 33 ZIP with
--component DP --stereochemistry-audit-only. This action is mutually exclusive
with generation/read-only-contract actions. It verifies trusted build metadata,
both reader and installed-option proofs, source/consumer/candidate hashes,
generation receipts, explicit stopping and all preserved lineage. Serialized
molecule outputs stay excluded. The saved PDU chemical/numerical assessment is
recomputed from the original source before its stereo audit.

The generic stereo audit compares exact elements/orders/formal charges first.
For each declared R/S centre, it records missing/conflicting labels and every
generated ordered three-neighbor signed term. The centre must have four
declared covalent neighbors. Compute det(a-centre,b-centre,c-centre) in each
complete coordinate family; never mix families or fill missing coordinates.
The 1e-6 cubic-angstrom threshold marks degenerate volumes, not chemical accuracy.
Inversions, flattened or contradictory signed terms reject; absent/unsigned
terms, missing coordinates or omitted labels retain review. Extra generated
centres also retain review. No CIP label is inferred and no term is rewritten.

The installed phase captures Utilities.py, MoleculeClass.py, TopologyMixins.py
and ChiralClass.py under the verified library anchor (1 MiB maximum each).
Snapshots use .py.txt suffixes and the worker removes its evidence directory
from module search paths. Only selected installed module paths execute. A
maximum 30-second worker per
component reads exact source IDs/markers with chirals=False, then separately
exercises the reader's chirals=True entry point. It records constructor exceptions
without promoting them to chemical rejection. This control does not reproduce
the full builder preparation sequence. Installation, snapshot, dispatcher and
input hashes must survive; escaped/changed modules or inventory mismatches refuse.
No whole-molecule trial or dictionary writer is requested. --inspect-only performs just
the offline comparisons. New additive JSON records are source_stereo_inventories,
saved_candidate_stereochemistry, saved_optimizer_trajectories and
installed_chirality_controls. Existing production APIs, dependencies and
NARestraints policy remain unchanged; native stereo execution is pending.

The Cedar 34 return verifies all 1,320 payloads and both captured source sets.
DP retains 35 literal ? native markers and reproduces the same assertion;
PDU's three known markers and constructor pass. Captured TopologyMixins.Chiralise
calls ChiralClass.Optimise, which performs local template minimization and native
RS notation. The old optimization_execution=NOT_RUN and absolute_cip_assignment
flags did not instrument those internals. Preserve those immutable receipts and
apply this narrower interpretation; no whole-molecule dictionary trial ran.
Future constructor receipts label internals uninstrumented and distinguish
independent CIP validation from native constructor operations.

### Preserved source reader dialect

Cedar 37 uses --delivery-prefix 37_Cedar --component-control PDU, then the exact
Cedar 36 ZIP with --component DP --source-dialect-audit-only
--declared-charge-control. It preserves the completed raw reader audit and
failed Cedar 35 preflight, and verifies nested Cedar 34 source/worker/input
hashes, native marker/constructor outcomes and all previous evidence. It also
replays saved PDU comparisons and printed trajectories.

The installed dispatcher classifies any _chem_comp.id file without the literal
data_comp_list marker as chemical components. DP's original monomer dictionary
has that block; its graph export did not. The explicit adapter first recomputes the exact source-derived, target-free
graph and requires byte equality, refusing old targets/types reintroduced by
a caller. It uses parsed source blocks to preserve that reader dialect. It writes one real comp_list loop and
one component definition, restores only source metadata and equal x/y/z aliases
from the complete graph seed, and retains exact chemistry/signed chirality.
No old numerical target or energy type is reintroduced. Reject changed chemical
fields, conflicting aliases, ambiguous components and unsafe outputs. No atom
stereo/aromatic label is inferred. Original source and graph bytes stay frozen.
PDU continues through the existing CCD projection with unchanged consumer bytes.
DP's new consumer SHA-256 is
4648c37ce867cce5a285d5f31a394a334b2cb9e347936511525a947927798bfa.
This opt-in diagnostic does not change the default generator's input policy.
The returned Cedar 35 audit stopped before native parsing because its internal
graph-check temporary path traversed an OS alias. Cedar 36 resolves only the
fresh tool-owned temporary directory before the strict graph writer, so system
temp aliases work without permitting symlinked caller outputs. Regression checks
cover both source dialects and byte-identical consumers. The actual returned
temporary path was not recorded; synthetic alias tests reproduce the error.

The native worker captures selected any_chemical_format_reader.py and
monomer_library_cif_parser.py as .py.txt, removes its evidence directory from
module search paths and checks selected imports/hashes before and after parsing.
It calls the installed dispatcher with simple=True, return_all_restraints=True
and do_not_check_for_smiles=True. Unwrap exactly one molecule when the dispatcher
returns a list; empty/multiple-component returns stay review. The input contains graph and signed declarations,
without numerical targets. A maximum 30-second read per component records actual
dispatch, format, identities, elements, raw atom charge, coordinates and bond
orders. Exceptions remain review evidence. Literal readback disagreement remains
visible, including aromatic representations; no equivalence is guessed here.
The native charge attribute's semantics and signed-stereo interpretation require
the returned parser source, independently of equality checks. No chiral
constructor or whole-molecule optimizer is requested; parser internals remain
uninstrumented. Snapshot/input/dispatcher/source checks surround both controls.
The source_reader_audits receipt and SOURCE_READER_DIALECT_CONTROLS status
are additive. Returned Cedar 36 completes both native reads: PDU passes every
raw check, while DP preserves route, identities, elements and coordinates but
loses five double orders and two declared -1 charges. Its four signed markers
survive; that alone is not a complete native stereo qualification.

The captured monomer parser matches only lowercase order tokens and defaults
other spellings to single. Its atom loop reads no charge field, including
partial_charge. Cedar 37 maps explicit single/double/triple/aromatic/delocalized
orders to that exact vocabulary in the separate consumer input. Original source
and graph bytes stay fixed; chemical comparisons use declared order semantics.
No partial-charge alias is fabricated and no atom stereo label is inferred.

The additional --declared-charge-control action separately exercises explicit
formal charges on the temporary parsed component. The worker snapshots the raw
reader result first. Source-bound Utilities/MoleculeClass captures support the
native integer charge API; input, dispatcher, parser and API hashes are checked
before/after. Exact route, atom identities/elements, bond membership/orders,
coordinates and complete integer charges (absolute per-atom value <=4, matching
the captured Chargise boundary) are preconditions. A conflicting or partially
loaded native charge state blocks assignment. An otherwise zero monomer object
receives the exact source charge map by atom identity plus its sum; an already
correct CCD object is checked without assignment. Recorded coordinates, bonds,
chiral markers and signed markers must stay unchanged. The host independently
rechecks the resulting inventory/total and retains the original raw reader flags.
No chiral constructor, Chargise, perception, optimizer or dictionary writer is
called by the population control; parser internals remain uninstrumented.
SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS describes this explicit request.
Returned Cedar 37 passes the isolated source-charge control for both components.
DP preserves all declared orders, and explicit population changes only OP2/OP3
from zero to source -1 on the temporary object (total -2); PDU already preserves
charges and requires no assignment. Raw DP charge failure stays visible. This
is not native stereo, full generator, achieved-geometry, convergence or
scientific qualification.
No new dependency, policy
guess, model change, refinement or adoption is introduced.


### Installed triple-bond controls

Build Cedar 38 with --delivery-prefix 38_Cedar --component-control PDU
--component-control 5PC; run against the exact Cedar 37 ZIP with --component DP
--triple-bond-audit-only. The mutually exclusive action verifies every C37
payload, source/worker/consumer hash and predecessor gate. It independently
replays both raw and controlled charge inventories. --inspect-only performs
this replay and offline dictionary screening without importing native Phenix.

The public source graph selects every explicit triple edge and all its linear
neighbors. Screening reports unique active distance/angle membership, target,
positive ESD/weight, observed geometry, preserved order and any dihedral whose
consecutive triplet contains an expected-linear angle. Carbon-carbon target
screening uses 1.10–1.30 Å; carbon-nitrogen uses 1.05–1.25 Å. Bond ESD must be
positive and <=0.05 Å. Adjacent angle targets must be 175–180°, with positive
ESD <=5°; measured bending over 5° requires review. These broad, versioned
review thresholds are not generated targets or universal chemical limits.
NIST's [acetylene experimental geometry](https://cccbdb.nist.gov/exp2x.asp?casno=74862&charge=0)
and [HCN geometry](https://cccbdb.nist.gov/expgeom2x.asp?casno=74908) provide
reference examples rather than bounds for every chemical environment. Other
triple-element pairs and unusual connectivity remain unsupported/review.

The installed resource worker binds server/cif_types imports to the selected
Phenix library, captures both APIs as .py.txt and asks only the monomer lookup
for the explicit component. A different resolved ID is unsupported. The exact
source_info file must reside inside the selected installation; freeze its bytes
and record anchored path/hash/size, with checks before/after native controls.
No basename discovery, source download, installed edit or captured-code import
is used. Absent/unsupported resources remain explicit review evidence.

Every native case uses the same separate source-ideal-seed PDB and explicit
secondary_structure.enabled=False. Compare installed lookup without overrides,
explicit captured-CIF replay (when available), and the saved C33 PDU candidate.
The native wrapper allows an empty dictionary list only with the explicit
installed_library_only=True option, rejecting simultaneous explicit overrides.
Full linked inventories retain effective definitions and active proxy details.
Component selection trims native PDB residue-name padding while preserving
literal labels in the captured inventory; two-character codes use the same
graph/proxy checks as three-character controls. No atom or component is renamed.
The report records lookup/snapshot term equality; it does not assume provenance
from equality. Per-resource timeout is <=30 s and per native case <=60 s; owned
process groups terminate on timeout. No generator, optimizer, ReadySet or
refinement runs. This is an isolated component control, not a complete replay
of ReadySet's dictionary precedence or an experimental scaffold qualification.

5PC is a second hash-pinned public graph control with C7/C8 triple names. Its
pinned workbook has two matching records; graph_only_if_ambiguous=True records
that ambiguity without choosing a role record or compiling its NA policy.
Existing controls still require unambiguous records by default. PDU's existing
pair/stack compiler checks remain fixed. No dependency or production default
changes. All results end at REVIEW; no dictionary or model is adopted.


### Installed CCD/source catalogue

Returned Cedar 38 verifies all 1,446 payloads. PDU and 5PC default monomer
lookups return no component; native interpretation stops with 38/39 unknown
energy types. The supplied PDU candidate loads with active 1.174 Å (ESD 0.020 Å)
and two 180° (ESD 3°) terms, plus six linear-axis torsion reviews. These native
controls use source-ideal seeds; the saved generated coordinates remain bent
and nonconverged. This does not identify the full ReadySet resource path.

Build Cedar 39 with --delivery-prefix 39_Cedar --component-control PDU
--component-control 5PC. Run the exact C38 ZIP with --component DP
--installed-source-audit-only. The mutually exclusive action preserves every
predecessor, verifies API/owned-worker/native input/output bytes and retains
failed lookups separately from the supplied dictionary. Independently replay
all prior mechanics, rotations, raw/controlled charge checks, source-seed models,
offline triple screens and captured active native screens. Numeric float replay
uses abs_tol=1e-8 and rel_tol=1e-10 for cross-platform libm rounding; other types,
identities, counts, state, targets beyond tolerance, hashes and bytes are exact.
--inspect-only performs those replays without native execution.

Use the verified library anchor, not a filesystem search or ambient Phenix, to
freeze the exact installed CCD paths
chem_data/chemical_components/<lowercase-initial>/data_<CODE>.cif. This is the
existing NASolve configured-CCD contract. Missing sources remain MISSING;
wrong/ambiguous chemistry remains REVIEW. Compare chemical declarations,
explicit triple edges, source coordinates/stereo and every SMILES descriptor
(type/program/version/text). Text equality/difference is descriptive. No SMILES
parser, graph assignment, target generation or chemical normalization is added.
Numerical parameterization remains a separate assessment.

Bind monomer server/cif_types imports to the selected installation and their
C38 source proofs. On fresh server objects, compare direct component-ID and
residue-name lookups; record root_path/geostd_path, full available component rows
and exact anchored source bytes. DG/DC are separate canonical resolution
controls recording resolved metadata/provenance, without parameter comparison.
Utilities must match its prior verified source. Capture its exact
GeoStd/monomer helper modules, one unambiguous Python layout of
mmtbx.chemical_components, and the selected ReadySet dispatcher as text. No
captured source, route helper or ReadySet dispatcher is executed. Missing
optional helper source layouts are recorded. All paths must remain beneath the
selected installation; source/API/snapshot/dispatcher/reference hashes are
checked before/after. No pickle or network source is consulted.

Installed CCDs with a valid declared graph also pass through the existing simple
native source reader, retaining raw format, atom/bond/charge/coordinate readback
and exact parser snapshots. These are independent of the absent numerical
monomer resources. The catalogue worker and each reader have <=30 s deadlines;
owned process groups terminate on timeout. INSTALLED_MONOMER_CCD_SOURCE_CONTROLS
records the request. No constructor, optimizer, generation, native geometry
trial, experimental model edit, refinement or adoption occurs. Curated
precedence and NARestraints pairing/stacking authority are unchanged, including
5PC's unresolved duplicate records. Complete ReadySet selection, mapped-SMILES,
stereo, numerical and scientific qualification remain open.

Returned Cedar 39 verifies all 1,486 payloads and the trusted clean published
runner. Both installed CCDs preserve public declarations and all SMILES text;
all six raw reader checks pass per component. Both direct/wrapped monomer
lookups are missing, while DG/DC canonical resolution succeeds. CCD numerical
parameters remain UNASSESSED; descriptor graph mapping and ReadySet remain
NOT_RUN. No historical SMILES or floppy-chain cause is established.

Build Cedar 40 with --delivery-prefix 40_Cedar --component-control PDU
--component-control 5PC. Run the exact C39 ZIP with --component DP
--readyset-source-audit-only. The new mutually exclusive action replays all prior
mechanics, rotational, raw/controlled source-reader and triple-proxy evidence,
plus both installed/public CCD comparisons and raw CCD inventories. --inspect-only
performs those checks without native execution.

Resolve exactly one literal $LIBTBX_PREFIX/...py target from the captured,
hash-matched ReadySet dispatcher. The target must stay beneath the selected
Python library. Copy it and bounded literal elbow/mmtbx imports of ReadySet-named
modules as text: at most three levels, 32 files, 1 MiB/file and 8 MiB total.
Direct helper sources are captured without recursive execution. Record missing
literal targets and budget limits; dynamic and complete transitive source
coverage is not claimed. No ReadySet module or captured code is imported.

A separate worker uses selected Phenix Python and the C39-proven
mmtbx.chemical_components module. Verify get_cif_filename against each exact
captured CCD resource before calling get_smiles. Retain the exact selected text
and matching descriptor type/program/version records. SELECTED_DESCRIPTOR_MATCH
means only text membership; graph mapping and numerical targets remain separate.
The worker has a <=30 s deadline and an owned timeout group. All selected API,
dispatcher, resource, reference and snapshot bytes remain checked before/after.
INSTALLED_CCD_DESCRIPTOR_SELECTION_ONLY records this native scope. ReadySet
execution, constructors, generation, optimization and model edits remain
unrequested; no numerical target, NAR policy, production default or adoption
changes. Saved PDU torsion reviews and the two ambiguous 5PC records survive.

Returned Cedar 40 verifies 1,529 payloads and the trusted clean build. Both
native CCD accessors select CACTVS SMILES_CANONICAL text, and 24 static sources
fit the literal-import budget. This is not executed ReadySet provenance. One
captured branch deletes its temporary SMILES and requests chemical_component;
Cedar 41 records the preparatory file-input call, then fails before reaching
that later branch: leaked wrapper PHIL options cause eLBOW's options parser to
raise SystemExit 2. All 1,624 returned payloads verify. Each receipt worker exits
zero after recording the native exception; ReadySet itself does not complete.
Both surviving CIFs exactly match the public CCD sources, without numerical
targets, and native interpretation remains NOT_RUN. Missing terms in these
preparatory copies do not establish a generation defect or historical cause.

The returned Cedar 42 capsule verifies all 1,747 payloads and the clean
published runner. Both file-input eLBOW calls and isolated ReadySet invocations
complete with no SMILES argument. PDU/5PC generated and active native targets
pass: lengths 1.203/1.186 Å with 0.020 Å ESD, and both linear angles 180° with
3° ESD. Native evaluation uses fixed public source seeds, not an optimized
linked model. Six generated/three active heavy-atom linear-axis torsions each,
source-relative chemistry and 5PC's angle/plane review remain open.

Cedar 42 used --readyset-generation-audit-only on the exact C41 ZIP. DP remains a preserved prerequisite; the new
generation cases are PDU/5PC only. --inspect-only replays saved evidence and
writes complete/heavy source-seed controls without native execution.

The selected Phenix interpreter calls the original ReadySet run API under
prior source/hash proofs. The v2 invocation keeps explicit ReadySet API arguments
out of process argv, matching the captured native entrypoint's separation.
Nested builder calls retain their original kwargs and reparse empty process
options. Each observer records argv; the installed options parser is also hash
checked and captured. The exact C41 failure is preserved and its source-copy
triple screens and complete/heavy seed models replay without executing old code. Heavy-atom inputs use hydrogens=False, ligands=True,
optimise_ligand_geometry=False, optimise_final_geometry_of_hydrogens=False,
trust_residue_code_is_chemical_components_code=False, metals=False,
link_to_edits=False and remove_waters=False. The shell dispatcher is not run.
No user CIF/cache is supplied; the ReadySet cache environment variable is
removed and bytecode writes disabled. Internal native template operations can
still optimize geometry and are recorded as NOT_INSTRUMENTED.

Process-local observers record builder/template arguments, caller source/line,
returned graph snapshots or exceptions while forwarding original arguments,
return objects and exceptions. Atomic logs survive a 180 s owned-process-group
timeout. Trace truncation at 64 events remains explicit; nonfinite native values
become trace markers without changing native objects. Preserve process failure,
ReadySet failure, caught builder errors and fallback dictionaries separately.
Select only the exact owned <CODE>.cif. Compare its bytes to the explicit
source and record UNCHANGED_SOURCE_COPY, PARTIAL_OR_UNQUALIFIED_OUTPUT or
COMPLETED_READYSET_OUTPUT. RECORDED means only file presence. Process success
alone or an unchanged source never establishes numerical generation. Native
success plus a changed output still requires independent qualification.
The console prints worker outcome, native outcome/error and file classification
separately. Serialized outputs are never loaded and remain excluded from review
capsules. Malformed, missing and partial candidates
stay review evidence; only completed policy-matched output proceeds to native
interpretation, capped at 60 s per control with SS inference disabled.

Retain raw source/dictionary graph, charge, hydrogen and stereo differences,
plus dictionary and native triple-target/linearity/ESD/membership/torsion screens.
The native model uses fixed source-ideal heavy-atom seeds. Full-reference
hydrogen-inventory differences remain visible even when the selected triple
terms pass. No convergence, all-chemistry, linked-scaffold or adoption approval
is inferred. Production defaults and NARestraints authority stay fixed.

5PC already has two cytosine-sheet records with equal C-like atom roles. The
component-control auditor now compares every operational atom mapping and
base/sugar/phosphate/Saenger/function/sheet/glycosidic context before allowing
equivalent aliases to compile once. All raw records remain in the report;
conflicting records and missing atoms remain blocked/reviewed. Explicit C5-mod
and C7-mod annotation columns are excluded, consistent with upstream mirror
metadata handling. Prefer an available canonical partner from registered
recipes before modified-family synthetic controls: 5PC exercises existing G:C
and both stack orders. No NARestraints table edit, package release or recipe
change is required; the conditional missing-entry case was not present.

Cedar 43 used --torsion-conditioning-audit-only on the exact C42 ZIP. This mutually exclusive action replays the
completed generated/native triple screens and all earlier prerequisites, then
evaluates only existing graph-selected heavy-atom dihedrals. The prior native
inputs are reached through exact reviewed relative anchors and hashes; old
absolute paths are provenance only. Captured code never executes.

The new cif-native-linear-axis-dihedral-conditioning-v1 module rebuilds the
exact captured manager before evaluating selected single-restraint and
singleton-container kernels. All atom/definition/proxy/API/policy inventory
fields match C42, six numerical module/binary hashes are pinned, and special
positions, symmetry-bearing torsions or nondefault limit/top-out/slack functions
are refused. Every original target, weight, periodicity and alternate remains
unchanged. Complete manager signatures and installed hashes are rechecked.

Cases use the saved native source-seed coordinates and generated dictionary
Cartesian coordinates at full precision and separately rounded to 0.001 Å.
Perturbations are temporary numerical evaluations; no model is written. At each
selected four-atom proxy, test all 12 Cartesian directions and the nonzero
single-gradient direction with six central-difference steps (10^-3…10^-8 Å).
Retain every step and require two adjacent agreeing steps per direction for
sampled agreement, with absolute/relative tolerance 10^-4. Record single versus
container energies/gradients, repeats, reversed order and the original function
parameters. Nonfinite values and native exceptions remain explicit JSON evidence.

Normalized cross-product sines describe each defining plane. A minimum sine
below 10^-3 raises descriptive near-collinearity review; this is not a universal
chemical cutoff or a removal policy. Exactly zero plane geometry is undefined,
even if native code returns a finite residual or zero gradient. Independent
nonchemical bent/exact-collinear controls and radius/phase profiles approaching
collinearity inspect this distinction. Bound each component to 3,000 paired
single/container evaluations (at most 6,000 kernels), plus a 180 s owned-process
deadline. Returned C43 completes both controls at 1,603 pairs each. All 234
real-coordinate directional checks independently recompute; every selected
torsion remains near-collinear. The 5PC full-precision maximum single gradient
norm is 578,927.34. Fixed-phase gradients grow approximately as inverse radius
in approach controls, and exact-collinear zero gradients remain undefined.
Correct sampled derivatives do not establish useful conditioning. The
--inspect-only action performs saved-evidence preflight without native kernels.

Retain the raw 0→−2 charge and HOP2/HOP3 loss, omitted R/S declarations,
source-relative stereo rejection and all other numerical findings. Passing
triple targets does not approve those generated changes. No ReadySet, dictionary
generation, optimizer, refinement, restraint removal, adoption or production
default change occurs in this action. Historical floppy-chain causation stays
unestablished.

Cedar 44 used --linear-torsion-candidate-only on the exact C43 ZIP. The exclusive action verifies all 1,794
payloads, replays saved directional arithmetic and preserves the entire prior
lineage without executing captured Python. Reach scientific inputs only via
reviewed relative anchors/checksums.

The cif-declared-linear-torsion-candidate-v1 preparation requires explicit C-C
or C-N triple orders, unique exact 180° flank targets with positive ESDs, and
supported unique consecutive torsion paths/finite parameters. Select rows only
from those declarations, never coordinate thresholds or code/atom-name lists.
Write a separate CIF omitting the six complete selected rows per control.
All other parsed values, including unknown fields, must compare exactly;
unmodified blocks retain original text. Affected blocks may reformat. Invalid
or ambiguous declarations refuse preparation before the candidate is written.
No production repair recipe is added and no source is overwritten.

Fresh original interpretation must match C43 atom/definition/proxy/API/policy
inventories. Candidate interpretation must match an expected inventory formed
only by removing the six effective-definition torsions and three matching active
heavy proxies/counts. Every other field, including charges, stereo, coordinates,
triple bonds, angles, planes and unrelated torsions/proxies, stays exact; any
extra inferred term or changed field remains REVIEW. Native triple-target
screens must still pass and no linear-axis torsion may remain. Each inventory
has a 60 s deadline. Returned C44 completes all four interpretations and passes
both exact comparisons. Active dihedrals change 28→25; the eight constant
dihedrals and every unrelated inventory field remain unchanged. Both native
triple-target screens pass with no remaining linear-axis torsion.

Keep phosphate 0→−2/HOP2/HOP3 differences, omitted R/S metadata and 5PC plane
findings open. This candidate does not select chemistry or prove a lower total
gradient, convergence, historical causation, scaffold suitability or adoption.
No ReadySet, generator, optimizer, model writer, refinement or installed edits
run. Explicit NARestraints pairing/stacking authority is unchanged.

Build Cedar 45 with --delivery-prefix 45_Cedar --component-control PDU
--component-control 5PC and run the exact C44 ZIP with --component DP
--linear-torsion-impact-only. Verify all 1,847 payloads and replay the candidate
plan/bytes, exact native delta and dictionary/native triple screens using
current maintained code. Preserve all earlier evidence, including C43 arithmetic,
without executing captured Python. Inputs use reviewed relative anchors/hashes.

The cif-fixed-linear-torsion-numerical-impact-v1 worker rebuilds separate
original and candidate managers under the exact captured C44 inventories. Pin
six numerical module/binary hashes and selected-installation geometry/flex
adapters. Refuse special positions or nonzero parallelity proxies in this
isolated slice; the qualified plane correction remains untouched. Preserve both
complete static signatures and all input/installed hashes before and after.

At the same three saved coordinate cases, record original/candidate full and
seven family-control targets, Cartesian gradients and proxy counts. Repeat all
baselines before and after temporary perturbations. Full/dihedral original-minus-
candidate differences must equal the saved three single-torsion sums, scattered
into full vectors by exact native indices. Bond, angle, chirality, planarity,
parallelity and nonbonded values must remain equal; family sums reproduce each
full target/gradient. Absolute/relative repeat/delta tolerances are 1e-8/1e-10.

For the candidate full and dihedral objectives, sample the 18 Cartesian axes of
the six atoms selected from omitted-proxy endpoints, alternating-global,
nonzero full-gradient and dihedral-gradient directions. Six central steps
(1e-3…1e-8 A) retain raw values and require two adjacent consistent steps with
absolute/relative 1e-4 tolerance; sample proxy counts must equal their baseline.
Cap each control at 2,000 energy evaluations and 180 s. Norm changes are
reported descriptively, not required to decrease. Numerical agreement is not
scientific approval, convergence, historical causation or scaffold validation.
Native numerical results await Mac; explicit fake-API/quadratic-oracle tests
and saved-capsule replay are separate evidence. No generator, optimizer,
coordinate model, state selection, installed edit, refinement or adoption runs.

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
