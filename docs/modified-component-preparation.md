# Modified-component preparation

**Current (2026-10-10):** P2 specific component preparation is **implemented
in Pine**, and user-local regression passed **276 focused + 20 subtests**
and **927 full + 224 subtests** on the published P2 code point `dec56c2`.
The independent **real source-component `1W5→DZ` / `1WA→DP`
native preparation, DP dictionary and refinement provenance check is still
PENDING**. This is not discharged by successful synthetic-target W Z:P
refinement or the earlier ordinary DZ GZ11 visual PASS. Exact current
priority is in the [short handoff](development-handoff.md); completed
four-member DiU/5CM full-auto results live in the
[full-auto checkpoint](full-auto-patch-handoff.md). The combined modified-W
prepared-bundle run has passed PostMR, and separate native diagnostics passed
generic linkage mechanics and custom-restraint coverage. The effective audit
then exposed an active 5CM wrong-atom torsion and defective ReadySet DF geometry.
The narrow 5CM correction and source-audited DF candidate subsequently passed
repaired native interpretation, including DF linkage, effective bonds/chirality
and preserved other/custom proxies. Bounded geometry minimization subsequently
completed awaiting review and exposed a DP angle/planarity inconsistency.
DP numerical repair/audit and overall geometry qualification remain pending.
This is not yet a fresh generic full-auto result. Exact evidence and the
bounded recovery sequence belong in the [native ledger](native-modified-pair-live-validation.md#effective-geometry-findings-and-bounded-recovery).

## Generic preparation target and current boundary

The intended user workflow is a fresh ordinary full-auto attempt from declared
sequence/chemistry and a component code: resolve the source, obtain numerical
restraints, prepare the actual polymer context, and carry the frozen effective
definitions through PostMR and refinement without editing NASolve or selecting
a test-only component preset. Ordinary acquired/cached source files must remain
separate from the small registry of justified overrides. Existing reviewed
1W5→DZ and 1WA→DP policy stays explicit. Unknown chemistry does not become an
automatic guess merely because a source file exists.

Cedar currently resolves local-first, then a unique source in the configured
Phenix CCD installation for supported non-curated mutation targets. It does not
fetch over the network, automatically try alternative numerical generators,
collect every unchanged non-curated residue, or generically adapt every monomer
dictionary to linked polymer chemistry. Raw graphs require numerical ReadySet
output; the existing parameterized check is a limited energy-type/bond-target
check, not a complete angle/torsion/chirality audit.

The October 10 combined test used a prepared resource bundle. A later diagnostic
substituted a freshly generated IMC dictionary and removed linkage leaving atoms
and their attached hydrogens by graph, without changing frozen parent inputs.
It established linkage mechanics for those four tested sites, not production
integration or generalization to arbitrary sequence environments. Preserve this
successful evidence, qualify the remaining geometry, then reproduce the
preparation through ordinary runtime code in a fresh attempt. The acceptance
check must cover relevant unchanged modified residues as well as mutations,
with source hashes, derivative differences and effective native restraints
recorded independently.

## Bundled ligand audit (2026-10-09)

Audit code point: `ccb7608b21d5bb994a973130298edaced24acf0c`. The nine
`CURATED_LIGANDS` entries combine source selection, construction recipes,
identity bridges and numerical restraint profiles. Membership is not evidence
that an upstream CIF was defective, nor that the bundled numerical geometry
has completed scientific review. The October 10 follow-up below supersedes
the earlier 5CM geometry conclusion while preserving source-byte provenance.
This audit changes documentation only.

| Component | Evidence from history and source comparison | Recommendation |
| --- | --- | --- |
| **1AP** | `af08c5a` replaced a raw CCD graph with parameterized MonomerLibrary data after the failed eLBOW attempt. Direct comparison with pinned source blob `1be06d4bb0848891fd3e7dca22d217dd2ad1b69b` finds only audit comments and `NON-POLYMER -> DNA`; numerical geometry is unchanged. | Retain the parameterized override and selected phosphate profile. The failed generated dictionary and polymer typing, not a demonstrated defect in all upstream 1AP sources, justify this route. |
| **DE** | The current eLBOW file has never changed since its addition at `b8317b0`. September's 1AP integration and handoff explicitly leave DE geometry defective and replacement unapproved. It is byte-identical to the historical repository-root eLBOW `8RO.cif` after changing the component label to DE; that historical file is not proof of official CCD equivalence. | Retain the lab identity/construction exception, but reopen geometry repair. Do not describe the existing file as a validated repaired dictionary or infer an approved `8RO -> DE` conversion. |
| **DF** | Added at `b8317b0` ("mutation works; patched DF"); retains the laboratory working label, `C2-S1` construction and deposition identity `A1AAZ`. User comparison found only component-label and trailing-whitespace differences. Restoring A1AAZ labels in the Git-verified DF file and trimming line ends reproduces the installed Phenix SHA-256 exactly. This is a graph/coordinate source without numerical bond targets. | Retain the short working label, exact identity bridge and sulfur-placement recipe. No chemical repair relative to the inspected A1AAZ graph source is present. The October 10 effective ReadySet DF was defective; a fresh candidate preserving this source graph passed separate native linkage/bond/chirality interpretation. Geometry remains pending. The user reports creating A1AAZ from lab DF; historical origin and runtime label conversion have opposite directions. |
| **DZ** | Direct comparison with pinned MonomerLibrary blob `9e6151658d2887ef3902d170c77752ccc90159d4` finds comments and `NON-POLYMER -> DNA` only. Numerical geometry is unchanged. | Retain the parameterized DNA resource and C-glycoside/linked-phosphate treatment; this is a sourced adaptation, not invented geometry. |
| **DP** | Pinned MonomerLibrary blob `50218f6ebd8ccaa5582c32286c675f466d8a6d0d` differs only by `NON-POLYMER -> DNA`. The geometry trial revealed incompatible N5-centred angle targets and their shared plane in the exact frozen numerical source. | Preserve the source; numerical repair requires a separate candidate/audit before a clean rerun. Do not infer targets or attribute this dictionary conflict to native fallback. True source-native P2 validation remains separate. |
| **5CM** | Added at `984f75d` after a missing-source failure; byte-identical to MonomerLibrary blob `a8a590f15f0b50c42ed9ad46d59eec3aab11d583`. The October 10 effective audit nevertheless found `C2e-nyu0` incorrectly referencing base C2 instead of sugar C2'. | Source equality remains true, but the earlier removal of the broken-dictionary classification is superseded for this exact version. The one-reference correction plus existing alternate normalization passed separate native interpretation. Geometry and any version/hash-scoped production repair remain pending. |
| **S6G** | Added at `eda1df7` for thioguanine construction, before the later incorrect Benner S selection. No subsequent CIF edits; the registry supplies `O6 -> S6` placement. The user-supplied complete diff shows trailing whitespace only. Removing line-end spaces/tabs from the Git-verified bundled source reproduces the installed Phenix SHA-256 exactly; atom names, charges, bond orders, stereochemistry, coordinates and metadata are unchanged. | Candidate for generic source lookup, preserving the sulfur-placement rule. S6G is thioguanine; the lab's S is IMC. That selection error does not establish a dictionary defect. |
| **C38** | Added at `739e6df` with iodine construction/AutoSol support; no subsequent CIF edits or identified supplier repair. The current coordinate reader gives ring `C5-I` = 2.094074 A. Its bytes match the user's installed Phenix 2.2.1-6174 CCD exactly. | Candidate for generic source lookup, preserving iodine placement/topology and numerical-generation checks. |
| **5IU** | Added at `739e6df`; CIF bytes have not changed. `984f75d` fixed the parser stripping the prime from `C5'`: direct calculation gives ring `C5-I5` = 2.095111 A and sugar `C5'-I5` = 8.843030 A. | Candidate for generic source lookup. The long apparent iodine bond was a NASolve parser defect; preserve the fix and iodine-placement rule. Its bytes match the user's installed Phenix 2.2.1-6174 CCD exactly. |

Evidence: [1AP integration](history/1ap-phosphate-integration.md),
[September handoff](history/development-handoff-2026-09-29.md.txt),
[component/parser recovery](full-auto-patch-handoff.md),
the three packaged provenance JSON files, and per-file Git history through the
audit code point. Upstream comparison used the exact Git blobs in
[MonomerLibrary/monomers](https://github.com/MonomerLibrary/monomers), not a
moving branch or a claim about the user's installed Phenix version. The four
downloaded source blobs and all nine NASolve CIFs were hashed against their
Git identities; the coordinate checks used the audited NASolve reader.

**DE remains an unresolved scientific item.** The current file declares group
`rna`, lacks OP3 and lists `C4-S4` as a single bond with a 1.816 A target. These
are source observations, not permission to edit bond order, targets or terminal
chemistry automatically. The archived note explicitly requires reviewed monomer
geometry and a fresh ED comparison before changing the sulfur pair target.
Passing limited topology checks or the full Python suite does not close that
review; no later committed DE replacement was found.

**Audit decision:** retain the specific bundled roles of 1AP, DE, DF, DZ and
DP, with DE geometry still unresolved. S6G/C38/5IU contain no supplier-chemistry
repairs; their placement recipes remain needed independently of source lookup.
5CM remains an unchanged pinned MonomerLibrary resource in production, but its
exact-version atom-reference defect now has a separately native-verified
derivative. The nine-entry source-equality audit does not certify numerical
geometry; DE remains unresolved and generic runtime integration is unfinished.

**Migration boundary:** source identity, atom names, elements/charges,
bonds/stereochemistry and coordinates match for the inspected S6G/C38/5IU
Phenix sources and the DF/A1AAZ bridge. This establishes source equivalence,
not the native readiness of a replacement lookup route. Keep construction
recipes independently of file-source policy. `DF`, `S6G`, `C38` and `5IU` need generated numerical restraints; `1AP`,
`DE`, `5CM`, `DZ` and `DP` contain numerical fields, which alone do not certify
their quality. Do not remove S6G/C38/5IU/5CM resources or relax the current
missing-curated-file guard until their replacement routes have appropriate
native evidence. Existing frozen dictionaries and runs retain their provenance.

### Lab labels and placement scope

User clarification on 2026-10-09 fixes the intended lab vocabulary below.
These names do not establish equivalence to a similarly named official CCD
component. The existing `1W5 -> DZ` and `1WA -> DP` chemistry overrides stay.

| Lab name | Intended component | Current implementation at `afc4496` |
| --- | --- | --- |
| F / DF | 2-thio-dT, deposition identity A1AAZ | F -> DF and A1AAZ -> DF are implemented for the working PDB route. |
| E / DE | 4-thio-dT, preserving the exception for the problematic 8RO source | E -> DE is implemented. This does not certify the old DE geometry or make the official 8RO graph an approved source. |
| Q / DQ | S6G thioguanine | Q -> S6G exists; DQ is not an implemented alias. |
| S / DS | IMC, N-linked 5-methyl-isodeoxycytidine | Literal IMC is accepted; S and DS are not implemented input aliases. |

The released [NARestraints v1.1.3 table](https://github.com/vecchioni-lab/NARestraints/blob/a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691/restraints/data/Ligands.xlsx)
contains DE/DF placeholders and IMC/S6G records, but no DQ or DS rows.
A future lab-alias bridge should resolve DQ -> S6G and S/DS -> IMC while
retaining requested labels in provenance; it need not create DQ/DS CIF copies.
The user's separate unpublished workbook is outside this audit.

IMC's `C1'-N1` bond is explicit in MonomerLibrary source blob
`d6701f39a17afee7763894d4133a4844a83720e6`.
The C-linked S in [modern ALIEN/hachimoji work](https://doi.org/10.1038/s41467-025-61991-9)
is different chemistry. Describe the combined challenge as lab B:S = IGU:IMC;
earlier wording equating IMC with that C-linked S was too broad. No official
CCD assignment for the bare code DS is inferred from the lab name.

**Placement is a separate concern from source repair.** Current
`postmr._restore_shared_parent_coordinates` restores shared same-element atoms
after Coot overlap. Its declared sulfur substitutions place the new atom along
the canonical parent C-O vector, retaining the C-S distance measured in the
raw Coot-built monomer. Its declared iodine substituents point away from the
midpoint of the two mapped ring neighbors and use the CIF ideal-coordinate
C-I distance. These preserve placement relative to the restored scaffold;
neither operation demonstrates a supplier CIF defect. The broad sulfur
sanity interval is not an element-specific validated refinement target.

The intended direction is reusable placement from an unambiguous chemical
graph/anchor mapping and sourced geometry, with dictionary-source policy
independent of the recipe. Numerical bond/angle targets, when available, should
be preferred to treating generated coordinates as geometry authority. Apply
a terminal-substituent rule only to a matching chemical environment; an S/F/Cl/Br/I
element label alone is insufficient. Keep the current scoped recipes while
validating a replacement. Add a bundled override when a demonstrated source
defect or representation requirement warrants one, with exact source and
reviewed differences; do not build a blanket repaired sulfur/halogen library.
The earlier source-equality audit did not detect the subsequently confirmed
5CM torsion defect; its narrow correction has separate native evidence above.

**Installed-source receipt (2026-10-09):** the user read and hashed the four
Phenix **2.2.1-6174** files without executing Phenix or Coot. For each component,
`lib/python3.1/...` and `lib/python3.11/...` resolve to the same file under
`lib/python3.11/site-packages/chem_data/chemical_components/`. The returned
SHA-256 values are compared with Git-verified NASolve CIF bytes below.

| Installed component | Installed SHA-256 | Bundled comparison |
| --- | --- | --- |
| S6G | `c84f5f1bdbb6155431290d7d342435d1ad4ef17b0100776ec99d6b8ea3f3bf3b` | Exact match after removing line-end spaces/tabs from bundled S6G; no chemical difference or CIF repair. |
| C38 | `852944f129b28115112c4cc0d16acc6ca09fbb1b1d66d7838d8d612a9522caa5` | Exact match to bundled C38; no NASolve CIF repair. |
| 5IU | `c621cc62fec1c1e189a544c811e57e874c2284045d806a4c67c6fe27d0b05f73` | Exact match to bundled 5IU; no NASolve CIF repair. |
| A1AAZ | `49022f8c86017f27a8a2364c35f17ca07eb2364dbdb18d66df996226756b1ac6` | Exact match after restoring A1AAZ component labels in bundled DF and trimming line ends; no additional chemical difference. |

Cedar's resolver now counts unique **resolved paths**, so symlink aliases no
longer cause false ambiguity. Two distinct resolved files still fail closed,
even when their bytes match; no arbitrary glob selection or content-based
source merging is introduced. The regression recreates this relative Python
directory symlink and checks genuine ambiguity alongside it. Bundled precedence,
identity validation and numerical parameterization requirements remain intact.
This lookup fix and source equality do not certify native geometry or remove
any CIF. User-local focused and full-checkout regression passed at `1443979`;
see the current [handoff](development-handoff.md) for exact commands/counts
and the [native ledger](native-modified-pair-live-validation.md) for the later
prepared-bundle and diagnostic results and their remaining geometry limits.

## Intermediate construction hops

The intermediate is a Coot placement convenience, not the final identity,
protonation state, pairing class or target atom dictionary. A recognized
NARestraints `Source sheet` wins; older records use `Base Analog`; an
unclassified intermediate uses C. Existing curated routes keep precedence.

| Category | Intermediate |
| --- | --- |
| adenine / A | A |
| guanine / G | G |
| cytosine / C | C |
| thymine / T | T |
| uracil / U | U |
| Z, S, K, unique | C |
| P, B, X | G |
| D, I | A |
| Unclassified intermediate | C |

DNA uses D-prefixed codes; RNA uses its ribonucleotide (U for a T-category hop).
The existing script skips a redundant mutation when already at the parent.
There is no N9, purine/pyrimidine or complete atom-role-map gate at this step.
The final component/dictionary, actual mutation and backbone checks remain
separate. The category table replaces, rather than supplements, the earlier
N9 proposal. No NARestraints workbook data or pairing class is rewritten.

## Component identity and the DZ resource

The standing conversions are specified below under P2. Raw input and
historical identities remain unchanged.

DZ is supplied as a local parameterized resource from MonomerLibrary
`d/DZ.cif`, Git blob `9e6151658d2887ef3902d170c77752ccc90159d4`.
The packaged adaptation changes `NON-POLYMER` to `DNA`, with source numerical
geometry, atom names, planes and chirality retained. Its regression reconstructs
the upstream bytes and checks the Git hash. No runtime download or experimental
registry injection is needed. Validation checks DZ's C1'-C1 C-glycoside,
parameterization, component identity and base-plane coverage. This is not a
pH-dependent protonation correction or final structural approval.

DZ keeps final identity DZ, NARestraints class Z, and DC as its construction
scaffold. The explicit `force = G:C` override still affects only the selected
inter-residue pairing recipe.

## Reviewed long deposition-code bridge

User-reported provenance (2026-10-09): the A1AAZ PDB deposition was built
from the laboratory's DF definition. Recorded origin is DF -> A1AAZ;
NASolve's runtime conversion goes from deposition identity back to the short
working label. The comparison confirms agreement of the current dictionaries.

PDB cannot carry a five-character residue name. The one approved exact
exception is target `(A1AAZ)` -> **DF**: DF's curated deposition identity is
A1AAZ and the PDB-compatible working definition is the already-reviewed DF.
This is a requested-to-prepared *target* identity mapping, **not** a source
heavy-atom normalization analogous to 1W5 -> DZ or 1WA -> DP. The original
five-character string stays in the frozen sequence/family target and the
`postmr.component_normalization.requested_target_changes` record gains
`basis=reviewed-deposition-to-pdb-code`. The target dictionary/refinement
component is DF and its recorded deposition identity remains A1AAZ.
Other unreviewed long CCD names still fail before PDB output; neither generic
truncation nor coordinate/dictionary guessing is authorized. The combined-W
PostMR identity audit verified requested A:19 A1AAZ as prepared DF within its
42 matched targets. This does not close source-native P2 conversion or final
geometry validation.

## Standing preferred-component preparation (P2)

The candidate implements **1W5 -> DZ always** and **1WA -> DP** for new PostMR
preparations. It is not pH-conditioned and does not rewrite a completed run.
Raw PDB/configuration/Phaser/sequence-family targets stay frozen; executable
prepared targets and the conversion receipt are separate from those originals.
A source at a site explicitly targeted for a different residue still undergoes
that requested mutation; neither path is allowed to leave 1W5/1WA as a final
prepared target. No new 8RO/1W0/DE/DF equivalence is introduced.

For an already placed source component, the reviewed correspondence retains
all mapped heavy-atom coordinates, occupancy, B values, sites and alternates.
Each source/target pair has the same 23 heavy-atom names/elements and adjacency.
Phosphate aliases O1P/O2P/O3P map to OP1/OP2/OP3. This is an explicit atom map,
not N9-based scaffold inference or general tautomer-equivalence detection.

Source hydrogen atoms and formal-charge annotations are not carried into the
new chemical state. Source intra-residue CONECT records are removed in favor
of the target dictionary; external heavy-atom links survive. Coordinate-linked
ANISOU/SIGATM/SIGUIJ/TER/LINK labels follow the conversion. Removed metadata is
accounted for and the complete source stays preserved. Missing atoms are not
invented; ordinary native preparation retains authority over usable geometry.
Unknown heavy-atom correspondence, collisions and unsupported mirrored-source
conversion are affected-dataset errors, not guesses or campaign-wide stops.

The target dictionary supplies bond orders and numerical geometry. In the
reviewed source definitions, 1W5 has C2-O2 SINGLE and DZ has C2-O2 DOUBLE;
1WA has C6-O6 SINGLE and DP has C6-O6 DOUBLE. The CCD also distinguishes 1WA's
+2 formal charge from DP's neutral component. Therefore this policy is more
than renaming a residue and is not a blanket claim that these identifiers are
chemically synonymous. No source protonation is inferred from pH.

If the site needs construction from a different residue, existing Coot parent
hops remain: DZ uses DC, DP uses DG. All other category hops stay unchanged.
NARestraints still uses its target Z/P categories and mapped atom-role columns;
`force = G:C` remains only an explicitly requested inter-residue recipe.

DP is supplied from MonomerLibrary d/DP.cif, exact source Git blob
`50218f6ebd8ccaa5582c32286c675f466d8a6d0d`. Only the component group is adapted
from NON-POLYMER to DNA. Atom names, numerical geometry, planes and chirality
are unchanged; DP.provenance.json records source/packaged hashes. No runtime
fetch is needed. The source group can be reconstructed to verify the Git hash.
DP uses the existing content-based torsion adapter, effective-dictionary
precedence and connectivity-selected phosphate profile; legacy frozen 1AP
profiles keep their old scope.

`postmr.component_normalization` records policy preferred-DZ-DP-v1, requested
versus prepared targets, the actual coordinate conversion and exact target
dictionaries. Existing mutation_actions record final prepared identities for
subsequent validation. Source/derivative references are run-anchored and hashed.
Old reports without this field are not reinterpreted, and source dictionaries,
raw MR models, observations/Free-R and old checkpoints are not overwritten.

Validation: source-level conversion/preservation, DP/DZ parameterization/
adaptation, ordinary PostMR fixture ReadySet, explicit/ambient aliases,
frozen intent, effective target CIFs, linked phosphate and downstream model
checks have passed. **The local full-checkout ferry returned green**
(276 focused + 20 subtests; 927 full + 224 subtests; the detailed receipt is
[archived](history/modified-component-preparation-2026-10-10-pre-reconciliation.md.txt)). **Actual native source `1W5/1WA` conversion and source-native DP
refinement remain untested.** Do not claim native coverage or structural
approval merely by implementing conversion.

Source review: MonomerLibrary 1W5 blob b309086c6d215b6ae48d7beb4654b9e278633005;
1WA blob c4d547e90bbe99595e44d674248a3613350dc54d. Pinned target DP and existing
DZ definitions are compared by atom identity/adjacency, not numerical equality.

## Effective dictionary preparation

PostMR snapshots each explicit source in
`PostMR/Restraints/source_dictionaries/` before creating a runtime derivative.
The effective bundle is prepared after ReadySet independently of whether a
linked-phosphate profile exists. Existing nonempty `refinement_restraints` and
`view_dictionaries` references bind the actual inputs used by descendants;
empty manifests are not added to dictionary-free native models.

Explicit parameterized component inputs take precedence over generated copies.
Construction-only CCD graphs still defer to ReadySet's numerical definitions.
Selection uses component IDs in the content, not filenames. Other generated
components and modification-only CIFs are retained. Raw ReadySet output remains
provenance, not an implicit override of the frozen effective definition.

Supported C2e/C3e alternative-torsion rows are converted for every component,
including components found only in the effective generated dictionary. Grouping
uses component identity plus ordered atom quartets (or full reversal), never
an arbitrary permutation of four names. Existing alternate values survive.
Equivalent duplicate rows may be folded; unrelated competing targets, different
periods and unsupported layouts remain intact with warnings for native
interpretation rather than receiving guessed chemical repairs.

**Unequal uncertainties:** retain the first row's sigma, as CCTBX's own
alternative conversion does, and record all source rows and their uncertainties.
This preserves the angle alternatives, not independent weights for each angle;
the receipt states that distinction explicitly. It does not flatten every DNA
sugar to one pucker or delete all torsion restraints to suppress an error.

Reference implementation inspected: CCTBX `mmtbx/monomer_library/server.py`,
`convert_ccp4_tor_list`. NASolve's stricter ordered-quartet and recognized-family
checks avoid generalizing its sorted-atom grouping to unrelated torsions.

`postmr.dictionary_compatibility` is additive schema-1 adaptation provenance;
its source/output references use the existing run anchors, hashes and sizes.
`dictionary_precedence` records the selected policy, authoritative components
and exact effective dictionaries. No checkpoint schema migration is needed.

## Linked phosphate and continuation

New 1AP/DZ/DP/5CM profiles use the connectivity-selected NASnoOP3 mechanism only
at verified internally linked sites; explicit terminal phosphate intent remains
unchanged. An explicit `profile_codes` scope is frozen for new DZ profiles.
Legacy profiles lacking that field remain 1AP-only and are not reinterpreted
when another supported component is added.

Missing optional NASolve recognition should not veto library-backed chemistry.
This patch leaves unfamiliar torsion representations intact with warnings and
defers unsupported cases to Phenix. It does not implement the entire broader
library-backed construction fallback. Required missing definitions, failed
execution, contradictory usable restraints, changed target identity or lost
observation/Free-R integrity remain real blockers for the affected dataset.

The generic IGU/IMC/CGY/DX linked-dictionary changes remain separate diagnostic
work. Their graph-driven removal of OP3 and linkage hydrogens cleared missing
heavy-atom and dangling-reference checks while preserving D:1 terminal intent.
The diagnostic retained source-specific OP2 protonation: IGU was anionic,
whereas the other three retained an OP2 hydrogen and neutral formal charge.
Mechanical success does not select a common protonation policy; that scientific
question and effective geometry remain open.

Keep a small known-problem list and supported, audited transformations. Do not
infer arbitrary missing bonds, bond orders, protonation or new ideal distances
merely to obtain a zero exit code. Base planarity alone does not validate every
internal bond. A numerical pass is not structural approval.

## Proposed SMILES and CIF audit

The [audit methods](cif-restraint-audit-methods.md) specify the reusable checks,
known 5CM/DF/DP cases and proposed report/review boundaries. This section owns
the preparation policy and staged integration scope.

**Queued after the current combined geometry test and before Topo/Scout;
not implemented and not a prerequisite for that geometry trial.** Start with a
read-only assessor. Parse a declared SMILES descriptor and the CIF into molecular
graphs; do not compare raw SMILES text. Match atom identity/connectivity under a
recorded aromaticity convention and report bond-order, element, formal-charge,
hydrogen and stereochemical differences separately. Keep an explicit atom map
back to CIF names and report ambiguous or unsupported comparisons as such.

Record the descriptor's source, program/version and source checksum. A SMILES
string copied from the same CIF is an internal consistency check, not independent
proof of correct chemistry. A separate reviewed reference is required for an
independent chemical comparison. Do not silently normalize tautomers or
protonation states away. Reviewed 1W5→DZ/1WA→DP transformations must be audited
against their intended target, retaining their explicit differences from the
source; they are not graph-equivalence assertions. Linked derivatives should
likewise be compared using the declared linkage changes and retained terminal
intent rather than required to equal the isolated monomer.

Pair graph comparison with a separate restraint check: valid atom references,
finite numerical targets/uncertainties, duplicate or conflicting terms, chirality,
angle/planarity consistency (including the demonstrated DP conflict), and
effective sugar/glycosidic torsions in the native interpreter.
SMILES alone cannot expose wrong numerical targets or a valid-but-wrong atom
quartet such as IMC/5CM C2 in place of C2'. A passing graph comparison therefore
cannot certify numerical geometry. The assessor should explain findings and
their evidence without inventing repairs or turning optional unknowns into
blanket campaign stops. Integration of any new runtime blocker needs its own
justification and tests.

### Staged automation after assessment

The first assessor is a development stage, not the final user workflow. Follow
it with separately validated, **deterministic** acquisition, bounded generation
and continuation for ordinary passing cases. No AI interaction or NASolve source
patch should be required during an ordinary run.

1. Resolve/cache source bytes independently of the small reviewed-override
   registry. Check graph, hydrogen attachments, formal charge, stereochemistry,
   numerical terms/references, restraint coverage and effective Phenix proxies.
   Keep chemical-state differences and unsupported comparisons explicit.
2. If declared policy permits regeneration, run a bounded, versioned generator
   recipe against the preserved source; freeze command, tool versions, hashes,
   warnings and source-to-candidate differences. Apply only verified polymer
   context changes, then repeat the source, numerical and native-effective
   audits. A generator exit code alone is not acceptance.
3. Continue automatically when required checks pass under that policy. Exact
   reviewed repairs need source-version/hash scope and recorded derivative
   provenance; the demonstrated 5CM correction is not permission for broad
   atom-name substitutions. Ambiguous protonation, tautomers or target chemistry
   require declared intent or a reviewed policy, not invented repairs. Preserve
   useful diagnostics and stop only the affected operation when required
   chemistry cannot be established.

This is planned integration after the geometry test and before Topo/Scout, not
implemented runtime recovery or a new gate on the current trial. The DF source
audit, repaired native interpretation and completed minimization are evidence
for one diagnostic sequence, with geometry qualification still pending; they
do not prove every ligand can already follow this path automatically.

## Historical validation evidence

The exact pre-reconciliation document, including the October 7 fixture recovery
and returned P2 commands/results, is
[archived](history/modified-component-preparation-2026-10-10-pre-reconciliation.md.txt).
The companion [intent record](modified-component-preparation-intent.json) is a
compact development summary, not runtime chemistry or registration authority.
