# Modified-component preparation

**Current (2026-10-08):** P2 specific component preparation is **implemented
in Pine**, and user-local regression passed **276 focused + 20 subtests**
and **927 full + 224 subtests** on the published P2 code point `dec56c2`.
The independent **real source-component `1W5→DZ` / `1WA→DP`
native preparation, DP dictionary and refinement provenance check is still
PENDING**. This is not discharged by successful synthetic-target W Z:P
refinement or the earlier ordinary DZ GZ11 visual PASS. Exact current
priority is in the [short handoff](development-handoff.md); completed
four-member DiU/5CM full-auto results live in the
[full-auto checkpoint](full-auto-patch-handoff.md). Historical validation
subsections below document their then-current stages rather than overriding
this update.

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
truncation nor coordinate/dictionary guessing is authorized. Native validation
of this explicit bridge remains separate from the previous P2 regression.

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
(276 focused + 20 subtests; 927 full + 224 subtests; see detailed historical
receipt below). **Actual native source `1W5/1WA` conversion and DP
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

New DZ profiles use the existing connectivity-selected NASnoOP3 mechanism only
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

Keep a small known-problem list and supported, audited transformations. Do not
infer arbitrary missing bonds, bond orders, protonation or new ideal distances
merely to obtain a zero exit code. Base planarity alone does not validate every
internal bond. A numerical pass is not structural approval.

## Historical P2 fixture recovery and returned local regression

The following describes the **2026-10-07 debugging and publication sequence**,
not a still-pending full-checkout run. P2 implementation and full regression
passed, as recorded at the top of this document. Completed native
GZ11/full-auto runs remain preserved; a **new** source-native
`1W5/1WA` alias and DP refinement check must not overwrite or relabel
those successes, nor be confused with ordinary DZ model validation.

### P2 fixture geometry recovery (2026-10-07)

The first P2 focused run returned 4 failed, 268 passed and 20 subtests in
22.20 s, before any full-suite run or publication. The four new PostMR tests
placed the preceding O3' at P + (-1.6, 0, 0), irrespective of monomer orientation.
That synthetic source already failed the unchanged phosphate guard at 28.5
(DZ fixture) or 29.8 degrees (DP fixture), before component normalization.
The same angles persisted after conversion: conversion did not create them.

The fixture now places incoming O3' at 1.6 A along the dictionary P-to-OP3
ray. This is test-data construction, not an automatic repair of real structures
or a change to the supplier dictionary. New tests check valid source geometry,
unchanged geometry after normalization and continued rejection of the original
bad placement. Existing PostMR integration assertions remain intact.
An isolated check used the exact phosphate.py Git blob
ca5def196ae0a53de1b19e8e625b914b3e8b841b: 34 conversion cases and four new
geometry cases passed (38 total). This is not full-checkout/native validation.
The recovery retains the failed parent receipt/log and uses a separate child
receipt for focused/full-suite validation and gated publication. No production
source or dictionary is changed by this fixture correction. The later returned
regression section records the complete-checkout result only after it passes.

### Returned local P2 regression

Tested source based on e13df41e027942d855475fa882d882237cbe5e1e.
focused: **276 passed, 20 subtests passed in 20.59s**.

full: **927 passed, 224 subtests passed in 78.72s (0:01:18)**.

Full-checkout regression is complete for these bytes. Native DP/alias
preparation remains pending; no scientific run or main merge was launched.
