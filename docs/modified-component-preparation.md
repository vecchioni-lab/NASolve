# Modified-component preparation

Status: **category-based construction hops implemented; 41 focused source tests
passed and Simon subsequently reported 735 passing local full-suite tests;
new live integration pending**. Library-backed warning/continuation policy below
is agreed development direction, not an implemented relaxation of runtime gates.

## Intermediate construction hops

A construction parent is a temporary Coot placement scaffold. It is not the
final component, an inferred tautomer, the target's base-pair class, or a
replacement source of target atom definitions.

For generic dictionary construction, use the recognized NARestraints `Source
sheet` category below. Older records without a recognized sheet use `Base
Analog` as the category. If neither supplies a recognized category, choose C.
The current generic constructor still requires a target record: fallback C
fills a missing **intermediate choice**, not a missing final residue identity
or dictionary. Broader library-backed continuation is discussed separately below.

| Source category | Intermediate base |
| --- | --- |
| adenine / A | A |
| guanine / G | G |
| cytosine / C | C |
| thymine / T | T |
| uracil / U | U |
| Z | C |
| P | G |
| D | A |
| B | G |
| S | C |
| I | A |
| X | G |
| K | C |
| unique | C |
| Unclassified intermediate | C |

DNA uses the corresponding D-prefixed code; RNA uses the ribonucleotide code
(and U for a T-category intermediate). Existing curated routes and their
sulfur/halogen placement rules keep precedence. Canonical mutation behavior is
unchanged. The ordinary PostMR script already skips a redundant intermediate
mutation when the residue is the selected parent.

This explicit user-approved table **replaces the N9 and purine/pyrimidine
inference proposal**. Do not add N9-presence, ring-family or atom-role-completeness
requirements to choose this temporary hop. Sugar compatibility and the actual
final construction, dictionary, identity, backbone and refinement checks remain
separate responsibilities. The existing mutation action records `parent_code`;
no checkpoint/report schema migration is introduced.

For example, DZ uses DC as the intermediate while its final identity and
NARestraints category remain DZ and Z. `force = G:C` still changes only the
requested inter-residue recipe. No installed workbook data are changed.

## Component identity is a separate policy

The recorded requested conversions are 1W5 -> DZ and 1WA -> DP. They remain
pending implementation review. Choosing an intermediate hop neither implements
these conversions nor declares the two component definitions interchangeable.
Raw inputs and frozen historical attempts retain their original identities.

## Recognition failures versus scientific blockers

Simon clarified after returning the category-hop regression: do not halt merely
because NASolve does not recognize a component or lacks its own special-case
classification when an applicable library supplies the intended component and
Phenix can interpret/refine it. NASolve should delegate supported chemistry to
the selected library rather than demand a duplicate internal registry.

The agreed direction is to continue with a recorded warning and library-source
provenance for a resolved library-backed component. Missing optional NASolve
annotations or specialized diagnostics should disable/report only those extras,
not veto otherwise usable refinement. Carry any remaining inspection caveat
forward without declaring it final structural approval. Missing NASolve
recognition and missing usable chemical definitions are different conditions.

A stop remains appropriate when execution cannot produce a usable result or
continuation would invalidate the intended science: for example, required
component definitions cannot be resolved, target identity would be silently
changed, required restraints remain unusable or contradictory, authoritative
observations/Free-R integrity is lost, or an explicitly requested operation
cannot be performed. Attempt supported, audited compatibility corrections first
where available. Do not silently omit an explicit requested constraint merely
to obtain a successful exit code. A scientific review flag is not itself a
technical failure and need not prevent every downstream diagnostic action.

Scope any necessary stop to the affected stage/dataset; unrelated campaign
members should continue. The known DZ conflicting-dihedral result is a real
execution blocker to repair, not evidence that every unfamiliar component must
be rejected. This section records policy for the next implementation slice;
no existing gate was changed by this documentation update.

## Effective dictionaries and bounded repair

The next dictionary slice should audit the **actual effective refinement
bundle**, including ReadySet-generated CIFs, not just an earlier input file.
Keep that small: identity/atom references, duplicate or conflicting restraints,
finite positive numerical parameters where required, and source/derivative
provenance. This is not a new monomer geometry library or a chemical inference
engine. Classify findings by their consequence rather than turning every
unrecognized feature into an exception.

Allow automatic corrections only for recognized transformations with defined
semantics and an audit trail. Examples are a supported CCP4 alternative-torsion
conversion or choosing an explicitly authoritative component over a conflicting
ReadySet copy. Existing connectivity-selected OP3 handling remains separate.
Do not infer an arbitrary missing bond, alter bond order/protonation, remove a
restraint, or widen its uncertainty merely because refinement otherwise errors.
Final plane restraints alone do not validate every internal bond or sugar.

The GZ11 audit exposed DZ B:4 C2e/C3e alternative rows for C4'-O4'-C1'-C2'.
The command consumed `PostMR/ReadySet/prepared_model.ligands.cif`, which retained
the alternatives. The current normalizer is still called only for 1AP. Its
future generalization must preserve legitimate angle alternatives, distinguish
ordered/reversed quartets from arbitrary permutations, and document how period,
existing alternative fields and unequal uncertainties are handled. Do not
collapse all sugar conformations to one fixed torsion target.

No generalized bond repair, torsion conversion, dictionary-precedence rewrite,
or new DZ/DP dictionary is implemented by the category-hop patch.

## Validation boundary

`tests/test_construction_scaffolds.py` exercises all nine requested categories
for DNA and RNA, source-sheet priority, legacy category fallback, default C,
independence from N9/role inference, unchanged target identities/library records,
ordinary category routes, retained curated recipes, sugar checks and separate
missing-dictionary failures.

The verified source module from Pine `97ab3e2` was tested in an isolated Linux
Python environment with a fixture residue-library loader. The new tests returned
32 failures and 9 passes before the patch, then **41 passes** after it. That
isolated check was not a full NASolve suite, workbook audit, Coot run, or Phenix
execution.

After the local validation ferry for category-hop commit `88e2f53`, Simon
reported **735 green tests** on 2026-10-01. Record this as a user-reported local
full-suite pass, not an independently executed run or GitHub CI. The follow-up
did not include a raw test transcript, exact checked-out SHA, subtest count or
runtime; none is inferred. The earlier 694-test/224-subtest result remains
historical evidence for its separately recorded code head.

New live integration remains pending. Preserve failed GZ11 and experimental
attempts; the category-hop regression pass does not resolve the known DZ
dictionary/torsion refinement blocker or validate the nine-dataset campaign.
