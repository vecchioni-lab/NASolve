# Modified-component preparation

Status: category hops and the effective-dictionary/DZ patch are implemented.
Simon's ferry passed **151 focused tests and 771 full tests plus 224 subtests**,
then published the tested code as `66cb7a2`. A fresh ordinary campaign-owned
GZ11 retry on that checkout now reached **SOLVED**, `run_002/refine-001`.
Detailed receipt/local-geometry and model/map inspection remain pending;
`1W5 -> DZ` / `1WA -> DP` conversions are separate unimplemented work.
Current evidence and next action are in the [development handoff](development-handoff.md).

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

The requested standing conversions **1W5 -> DZ** and **1WA -> DP** remain
pending: shipping DZ and choosing a DC intermediate do not implement source
component conversion. Raw input and historical identities remain unchanged.

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

## Validation and next action

The original isolated source harness passed 34 tests using real Bio.PDB and
stubs for unrelated imports. Simon then returned full-checkout regression:
151 focused tests in 3.66 s; 771 tests + 224 subtests in 66.78 s. The tested
working tree was committed as `66cb7a2295bd9ea79fb946b2312ea7e3acd7eb08` and
pushed to Pine. Coverage includes construction hops, representation,
unequal-sigma receipts, source preservation, unknown-case continuation, DZ
provenance/topology, effective precedence, legacy profile scope and
fixture-backed PostMR/checkpoint/view/relocation. These are local tests, not CI.

**Native workflow result:** on printed checkout `66cb7a2`, ordinary campaign
retry/run for GZ11 proceeded through preflight, Phaser, PostMR, the AutoSol gate
and AutoRefine to SOLVED at campaign-owned `attempt_002`,
`GZ11/AutoMR/run_002`, checkpoint `refine-001`. Frozen input and member integrity
were OK. The previous missing-resource/torsion execution blocker no longer
prevents this workflow from completing numerical refinement. The run used no
temporary registry injection. The exact campaign root and evidence limits are
recorded in the handoff and machine intent, rather than repeated here.

The returned status is not a detailed component audit: exact R values, final
atom inventory, force application, effective-CIF receipt, local geometry and
model/map inspection still need reading from the successful outputs. It also
does not identify whether the AutoSol stage ran its engine or skipped it.
Inspect the existing successful checkpoint rather than rerunning GZ11. Do not
confuse it with the earlier blocked standalone run_002 or the temporary probe.
The separate component conversions and other campaign blockers remain pending.
