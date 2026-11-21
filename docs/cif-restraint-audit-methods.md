# CIF and effective-restraint audit methods

**Scientific methods blueprint, originally 2026-10-11; current-scope clarification
2026-10-31.** The rule catalogue below retains its design scope. Implemented
capabilities now include source-preserving generation/preparation, exact native
proxy and monomer inventories, explicit selected bundles, derivative/geometry
diagnostics and bounded graph-selected repair attribution. The
[runtime contract](cif-doctor.md) identifies the exact supported APIs and limits;
they are not all connected into ordinary automatic PostMR recovery/adoption.
Ordinary PostMR assessment hooks remain report-only. Mapped external chemical
inputs and general checkpoint adoption are separate unfinished stages.

The [completion queue](cif-doctor-completion-queue.md) owns remaining priorities;
the [handoff](development-handoff.md) owns the active checkpoint. The
[component contract](modified-component-preparation.md) owns chemical intent and
source precedence, and the [CIF Doctor evidence ledger](cif-linked-native-registration-evidence.json)
records exact native outcomes. The [implementation map](cif-restraint-doctor-implementation.json)
retains the original scientific design alongside dated progress records; an old
planned/pending statement is not current scheduling authority. Existing-checkpoint
assessment remains read-only; accepted preparation/coordinate adoption must
create an immutable child. No scientific gate is relaxed by this clarification.

## Purpose and boundaries

Turn repeatable scientific debugging into recorded checks: given component
codes, declared chemical/linkage intent, source dictionaries and native outputs,
explain what is consistent, what changed, what remains untested and why a
particular operation needs review. Ordinary passing cases should eventually run
without AI intervention, hand-prepared bundles or per-component NASolve patches.

Keep acquisition/cache separate from the small reviewed-override registry.
Finding or using a CIF does not make it an exception. Distinguish source identity,
chemical graph, numerical restraints, effective native proxies, achieved geometry
and experimental support. A pass at one layer cannot certify the next. Already
present modified residues need the same assessment as newly mutated residues.
Keep required chemistry failures local to the affected operation; an optional or
unsupported comparison is not a blanket campaign stop.

The assessor proposes no new tautomer, protonation, bond order, ideal distance,
sugar pucker, pairing class or metal coordination. Reviewed `1W5→DZ` and
`1WA→DP` transformations remain explicit identity changes; `A1AAZ→DF` is the
reviewed label bridge. The chemical transformations preserve their declared
source/target differences; the label bridge expects graph equivalence under
component-ID renaming.

## Doctor coordination and assembly geometry

**Requested 2026-10-11; roadmap only.** The generalized restraint assessor is
the first new module in a shared Doctor workflow. The same entry/orchestration
layer should coordinate existing data/Free-R and refinement diagnostics with
component/effective-restraint assessment and a subsequent geometry/connectivity
checker plus guided arm stitcher. These modules retain separate findings and
evidence; a dictionary finding does not itself establish an assembly defect.
No unified entry point or geometry stitcher is implemented by this document.

The user attributes GeoTest's elevated Rwork to fractured arms at sticky ends,
and asks for that repair to be bundled with Doctor rather than treated only as
an anomalous/data refinement problem. Record this as the user's diagnosis and
development motivation. High Rwork alone cannot distinguish anomalous noise,
wrong assembly, coordinate misfit or deficient restraints, or establish which
connection is intended. The planned geometry module must inspect the exact
placed/refined model, maps, effective proxies and symmetry, then identify local
evidence and declared connectivity before proposing an operation. Run these
assessments before spending strategy trials on a known invalid model.

The [guided-arm contract](construct-registration.md#geotest-guided-arm-connection)
owns mapping, strand routing, symmetry-aware preview and repair acceptance.
Preserve true nicks and GeoTest's declared free 5′-OH ends; sticky-end pairing is
not authorization to form a new covalent bond. An accepted, bounded local repair
creates a new immutable checkpoint, is reinterpreted with reviewed effective
restraints and is refined against the same observations and frozen Free-R set.
Data/flag diagnosis never permits changing or regenerating that set to improve
statistics. This coordinated roadmap does not add a gate to the successful
GeoTest campaign or delay the read-only assessor's first development slice.

## Rules: stable IDs and bounded evidence

IDs below define the complete planned methods; the runtime contract distinguishes
the implemented subset from unassessed layers. Every result identifies
its input hashes, scope and calculation. Return raw measurements alongside the
finding; distinguish parser/numerical tolerances from calibrated scientific
decision thresholds. Do not invent a universal sigma cutoff.

| Rule | Input and calculation | Output and limits |
| --- | --- | --- |
| `PROV-01` | Resolve declared anchored references; verify size/hash before and after; record ordered sources, precedence, code/tool versions and transformations. | Immutable provenance or an explicit missing/mismatch/ambiguity finding. No basename searching or silent substitution. |
| `GRAPH-01` | Parse component identity, unique atom IDs, elements, bonds and references; construct adjacency/mapping. Compare serialized seeds through an independent CIF reader and the installed consumer reader, including atom/bond/chirality fields. | Missing/duplicate IDs, parser disagreement, dangling references, graph changes and mapping ambiguity. Writer-library round-trip alone is insufficient; connectivity does not prove correct chemistry. |
| `CHEM-01` | Compare mapped elements, bond orders/aromaticity, explicit H attachments, formal charges and declared stereochemistry under a recorded representation policy. | Separate changes and unsupported comparisons. Check valence using supported element/charge/bond conventions; do not guess unfamiliar coordination chemistry. |
| `NUM-01` | Inventory required numerical categories; check finite values, units, usable uncertainties/weights, distinct atom references and restraint-specific connectivity. | Missing, unusable or suspicious terms. Presence of any numerical field does not establish complete parameterization. |
| `TOR-01` | Compare ordered torsion quartets/full reversals, central bonds, periods, alternates, weights and native energetic/constant roles. | Exact redundancy, supported alternate family, competing term or unsupported representation. Do not equate arbitrary permutations or count zero-weight annotations as energetic restraints. |
| `STEREO-01` | Map each centre and ordered neighbours; compare dictionary/native signed volumes with coordinate volumes and separately assigned stereochemistry. | Preserved, inverted, degenerate, unrestricted or unassessed centre. Permutation parity and reference ordering matter; a CIF sign is not itself an R/S label. |
| `PLANE-01` | For a centre and three neighbours jointly restrained planar, compare all three pair-angle targets using their Gram matrix and planar branches below. | Target-compatibility measurements and candidate angle/plane conflict; uncertainty-aware classification requires calibration, not an automatic repair. |
| `LINK-01` | Compare isolated source with each site's declared incoming/outgoing links, modifications and terminal intent; inspect effective atoms, H adjacency and references. | Exact allowed deletions/type changes plus unexpected changes or incomplete links. Component-wide edits cannot stand in for site context. |
| `NATIVE-01` | Extract actually loaded components/mods and interpreted proxies, including atom identities, symmetry, target, period/alternates, weight and origin. | Requested-versus-effective differences and missing/extra/conflicting restraints. File existence or interpreter exit zero is insufficient. |
| `COVER-01` | Resolve configured edit selections, then match actual proxies by type and full atom/symmetry identity plus target and weight. | Exact coverage and multiset duplicates; plane/parallelity overlaps reported separately. Correct counts alone cannot prove the intended atoms were restrained. |
| `GEOM-01` | Evaluate before/after coordinates with the same effective manager; record per-term residuals, displacement, chirality, links and symmetry-aware contacts. | Achieved geometry and numerical completion/convergence evidence. Misfit alone does not identify a dictionary defect or establish experimental identity. |

## Input graphs, numerical terms and comparison semantics

Classify CIF content before use: a coordinate mmCIF (`_atom_site`) and a
component/restraint dictionary (`_chem_comp*`) have different roles; extension
`.cif` alone identifies neither. Mixed-content files require an explicit role.
Model-input checks and the planned PDB/coordinate-mmCIF adapter remain under
[the architecture](architecture.md), not ligand-dictionary inference.

`PROV-01` freezes source, generated candidate, linked derivative and native inputs
as separate artifacts. A receipt must identify actual content selected by the
interpreter, not merely a convenient file named `CODE.cif`. Preserve generator
warnings, commands, environment/version receipts and failed candidates. Record
whether target values were derived from the very model being assessed: low
residuals against such targets are not independent validation of geometry.

For `GRAPH-01`, validate the consumer's parsed content **before** expensive
generation. Primed IDs are an observed interoperability case: the first DP seed
round-tripped through Biopython with 35 atoms/37 bonds, but AceDRG interpreted
only 20/21 and failed on a single-quoted primed ID. Use consumer-compatible
serialization (double-quoted primed IDs in this retry), then compare selected
source atom, bond and chirality fields exactly; counts alone are insufficient.
Record permitted quote normalization and distinguish added consumer-derived
fields from source changes. Offline reader replay is not installed generator
validation. Preserve the failed seed/log. This is a parser failure, not
permission to delete atoms, alter
chemistry or weaken the inventory check.

For `CHEM-01`, record explicit versus implicit hydrogen policy, aromaticity and
resonance handling; report ambiguous graph maps instead of choosing one silently.
Report explicit bond-order changes separately from aromatic annotation changes.
The DP v2 candidate retained all 37 explicit orders, H/charge and stereo while
four aromatic flags changed; its combined literal-comparison `false` required
review, not an automatic chemical-change verdict or blanket flag suppression.
Keep dropped alias metadata as a separate provenance finding. A retained graph
does not mean a one-angle correction: inventory every regenerated numerical
category and compare native target/weight/plane coverage. Generator-coordinate
self-consistency is not independent validation.
**Formal charge and partial charge are different fields.** Preserve both when
present; absence is unknown, not zero. Do not compare a CCD formal-charge total
with a force-field partial-charge total as if they were identical. Linked-state
changes must be explained independently of isolated-monomer equality.

Parse SMILES to a mapped molecular graph, not raw-string equality. Record its
source/program/version and whether it was copied from the same CIF. Copied
descriptors test internal consistency, not independent chemical correctness.
SMILES cannot validate numerical targets, sigmas, atom selections or the native
proxies actually used. Preserve tautomer/protonation differences explicitly.
The frozen DP example also has neutral-phosphate descriptors beside an explicit
atom/bond graph with OP2/OP3 each charged −1. A regeneration seed therefore
preserves the selected graph, charges, explicit H and chirality while excluding
those descriptors and old numerical targets/types. Preserve both the untouched
source and a field-level seed derivation; do not silently use a descriptor to
choose another protonation state.

For `NUM-01`, distinguish missing values (`.`/`?`) from numeric zero. Check that
bond and angle references follow their declared graph; classify torsions as
proper/improper/other before testing connectivity. A proper torsion should follow
a bonded path; legitimate improper torsions need not. A suspicious sugar-labelled
term ending at base `C2` instead of sugar `C2'` merits evidence-backed review,
not a global atom-name substitution. Compare requirements with the supported
component/polymer class and native handling, rather than requiring every possible
angle or signed centre indiscriminately.

For `TOR-01`, use the engine's actual potential and alternative-angle semantics.
Separate source-quartet comparisons from native proxy canonicalization. In
cctbx `dihedral.h` blob `ee41da7a84b3ae1155f39e70021abe943f6bb97e`,
`sort_i_seqs` independently swaps terminal 0↔3 and central 1↔2 indices,
negating ideal/alternate angles for each swap; two swaps preserve sign. The DP
checker missed valid proxies by allowing only full reversal. Match this verified
engine representation, including kind/period/weight/alternates; do not authorize
arbitrary source permutations. Test single/two swaps with a nonzero angle and
reject missing/duplicate/wrong-central-pair or altered target/weight/period terms.
Report nearest periodic angular displacement separately from energy. Do not
apply one harmonic `delta/sigma` formula to every periodic or alternative term.
Reconcile native atom ordering and sign conventions before comparing targets;
`.geo` can display a nearest periodic equivalent without changing the proxy.
The existing `ccp4-alternates-primary-sigma-v2` adapter in
`src/nasolve/dictionary_compatibility.py` recognizes supported C2e/C3e families,
preserves the first row's sigma and records all source uncertainties. It preserves
alternate targets, **not independent weights for each alternative**. Different
periods, unsupported competing targets and arbitrary quartet permutations must
not be collapsed. Native zero-weight `const_dihedral` rows remain inventory
evidence; they are not extra energetic torsion failures. Determine activity from
actual proxy kind and weight, not a `const` name alone.

For `STEREO-01`, reconcile neighbour order before comparing signs; odd
permutations reverse signed volume. CIP labels depend on substituent priorities,
so compare R/S only after a valid graph-based assignment. A `both` declaration
or near-zero volume is not proof of preserved definite chirality. Record the
distance from degeneracy and the numerical tolerance used.

## General angle/planarity compatibility

`PLANE-01` requires one plane containing the centre and all three neighbours in
the same symmetry-image frame. Consider angles in `[0,180]` between three nonzero
vectors from centre O to neighbours A/B/C. Build `Gii = 1`, `Gij = cos(theta_ij)`.
Positive semidefiniteness is necessary and sufficient for those three pair
angles to be realizable as unit vectors in three dimensions. Planar realization
additionally requires rank at most two. Record eigenvalues/determinant and the
numerical tolerance; a determinant close to zero alone is insufficient if G is
not positive semidefinite. Preserve degenerate/collinear cases separately.

For a nondegenerate planar arrangement, the three smaller pair angles either
sum to 360° (centre inside the triangle of its three neighbours), or the largest
equals the sum of the other two (directions in a half-plane; exterior branch).
Never apply a universal 360° sum rule. Unknown orientation requires considering
both branches; actual coordinates can identify the observed branch but must not
force the source targets into it.

Report angular distance to each feasible branch and, where supported, a bounded
minimum-adjustment score using the recorded angle uncertainties and native
restraint forms. A score based on angle sigmas alone excludes finite plane weights
and correlations; label that limitation. Exact central targets may be mutually
incompatible while their finite-width restraints intentionally permit a compromise.
Separate algebraic incompatibility, material strain and a probable source defect.
Classification thresholds need reviewed examples and false-positive checks;
neither this calculation nor a large residual supplies replacement ideal angles.

## Linked state, actual proxies and achieved geometry

`LINK-01` derives eligible edits from verified site connectivity and a supported
policy. Identify attached hydrogens from the graph, not only their names. After
each deletion, verify surviving references, no orphan H, expected incoming and
outgoing bonds, and preserved terminal/nick intent. Do not erase OP2 hydrogens to
make charge totals uniform. Isolated, internal, terminal, nick, cyclic and
symmetry-linked contexts require distinct evidence; a four-site internal-link
diagnostic does not validate all of them.

For `NATIVE-01`/`COVER-01`, record complete atom identifiers including model,
chain, residue/insertion code, alternate and atom name, with link symmetry
operators. Compare proxy multisets; an aggregate count can hide a missing term
balanced by an unintended extra term. Match plane atom sets and parallelity plane
pairs under justified symmetries; separately report subset/overlap candidates.
Preserve origins so a covalent term, NARestraints edit and native secondary-
structure term cannot silently masquerade as the same source. Optional unknown
proxy types stay visible, with scope of coverage explicitly limited.

`GEOM-01` uses full-precision coordinates, preserves original inputs and records
whether the restraint-definition hash and flags stayed fixed, separately from
manager API/version provenance. Preserve atom metadata, cell/symmetry and mapped
input/output identities; audit serialization/round-trip precision separately.
Objectives from different restraint definitions are not like-for-like model
rankings: changing DP targets changes the objective itself. Compare each trial
against its own fixed definitions and report cross-trial raw geometry separately.
Residual strain alone does not justify dictionary repair. Include absolute
errors and configured uncertainties as well as native residuals/weights, per-site maxima
and distributions; overall target reduction can hide a local conflict. Evaluate
bonded exclusions and symmetry operators when reporting contacts, so symmetry
clashes are not missed or ordinary covalent contacts counted as clashes. Do not
invent cross-symmetry angle restraints from a bond-only observation.

Record iteration/cycle limits, actual stopping reason, gradients, warnings and
native tolerances. An exit-zero minimization, decreasing target or retained
chirality is not a convergence verdict. Geometry-only minimization uses no
diffraction evidence; refinement, maps, Free-R integrity and human inspection
remain separate. A human verdict names the exact model/effective-input hashes.

## Learning cases and future regression fixtures

The following evidence is indexed, not recopied. Paths below are relative to
the ledger's declared source/repaired/geometry anchors; hashes and tool versions
remain authoritative in that ledger. Commit no unpublished models/CIF bundles.
Future tests should use small synthetic reproductions of these failure modes.

| Case and evidence | Proposed fixture expectation |
| --- | --- |
| [5CM active torsion](native-modified-pair-live-validation.md#5cm--confirmed-active-torsion-defect): `inputs/06_07_5CM.cif`, C4'–O4'–C1'–C2 at 340.7°/6.3°/period 1; correct C2' alternative 2.8°/6.1°. | Detect the suspicious/nonbonded proper quartet without renaming it. An explicitly reviewed single-reference correction plus existing normalizer yields primary 340.7°, alternate 2.8°, first sigma 6.3°; preserve source rows and native coverage. |
| [DF generated replacement](native-modified-pair-live-validation.md#df--generated-replacement-and-source-audit): effective ReadySet supplement versus `DF-CANDIDATE/DF_source_CCD.cif` and `DF.cif`; incorrect aromatic sugar/bond targets and missing active sugar chirality. | Graph, numerical and native tests detect distinct failures. Source-preserving regenerated graph retains explicit H; linked `NASpDF` removes OP3/HOP3/HO3', retains HOP2, verifies the 21 heavy bonds/three signed sugar centres. Preserve old/new charge evidence; no inferred pH repair. |
| [DP angle/plane conflict](native-modified-pair-live-validation.md#review-findings--dp-angleplane-inconsistency-remains-open): `inputs/08_09_DP.cif`; N5 with C4/C7/C6 in one plane. Targets 109.471°, 120.772°, 109.471° sum to 339.714°; achieved third angle 127.914° versus 109.471°/3°. | Report incompatible exact planar central targets and uncertainty-aware strain; do not manufacture 120° targets. Gram determinant ≈0.40233 permits a three-dimensional pyramid: the conflict is with planarity. Include valid exterior-branch and finite-width near-compatible counterexamples to prevent a universal sum-rule blocker. |
| [DP seed-parser failure](native-modified-pair-live-validation.md#dp-candidate-attempt--blocked-by-seed-parser-disagreement): 35/37 source inventory became 20/21 in AceDRG before `KeyError: "'C5'"`. | Exercise primed and double-primed IDs across writer and consumer readers; require exact atoms/bonds/chirality agreement before generation. Preserve both failed and corrected seeds and unchanged sources; no candidate/adoption on failure. |
| [DP v2 aromatic annotations and linkage](native-modified-pair-live-validation.md#dp-v2-candidate--generated-and-audited-for-native-testing): 37 explicit orders unchanged, four aromatic Y→N flags, source aliases absent from generated output; B:4 retains O3'-bound H3 under `NASnoOP3` alone. | Separate representation, metadata and chemical graph findings. Preserve source aliases; require outgoing-link H/type handling alongside incoming phosphate modification. Neither generation nor graph equivalence proves effective polymer chemistry. |
| [Historical 8RO/DE](modified-component-preparation.md#bundled-ligand-audit-2026-10-09), queued challenge case: official CCD 8RO is not the intended lab DE; the historical eLBOW file labelled 8RO became DE by label substitution. Current DE numerical geometry remains unresolved. | Recover exact failed source/candidate hashes and declared intended chemistry before assessment. Distinguish wrong identity/topology from numerical defects and label-only changes. No general `8RO→DE` equivalence or automatic bond-order/target repair. Retain unresolved findings and a correct-identity control. |
| [1AP history](history/1ap-phosphate-integration.md#reviewed-dictionary), queued challenge case: the failed eLBOW attempt introduced an O4'–N1 connection; raw CCD lacked required numerical targets. The selected MonomerLibrary adaptation preserves numerical rows while changing polymer group. | Recover the failed artifact or a clearly labelled synthetic reproduction. Test wrong connectivity separately from incomplete parameterization, supported alternate torsions/native compatibility and site-specific OP3 handling. The current curated source is a preservation/control case, not presumed defective. Keep both internal and explicitly phosphorylated terminal sites. |
| [Linked diagnostic](native-modified-pair-live-validation.md#linked-diagnostic--mechanics-pass-chemistry-still-pending), including fresh IMC and `LINKED/linked_audit.json`; [coverage evidence](native-modified-pair-live-validation.md#custom-restraint-coverage--preserved-baseline). | Renamed linkage H is found by adjacency; terminal OP3 survives; retained OP2 H is reported. Matching counts with wrong atoms fail coverage. Unsupported terminal/symmetry cases remain unassessed. |

The October 11 decision uses 5CM/DF/DP as development cases and 8RO/DE plus 1AP
as additional generalization challenges. Freeze the expected findings and exact
source provenance before tuning rules on those cases. Run the same assessor;
add a rule only for a demonstrated failure mode with a valid counterexample,
not merely a component-code branch. A missing historical artifact remains an
evidence gap; a synthetic fixture must not masquerade as a replay of that run.
No new 8RO/DE or 1AP assessment or repair is claimed by this documentation.

Also test quartet reversal versus arbitrary permutation, different periods,
unequal alternate sigmas, zero-weight constant torsions, chirality neighbour
parity, ambiguous atom maps, missing formal charge versus supplied partial charge,
copied versus independent SMILES, missing source hash and unchanged inputs after
failure. Include a stopped-at-limit minimization that must never report convergence.

## Proposed audit receipt and continuation policy

This is a proposed schema, not a change to existing run/checkpoint schemas:

```json
{
  "schema_version": 1,
  "audit_kind": "cif_restraint_assessment",
  "scope": {"components": [], "sites": [], "required_rules": []},
  "inputs": [{"role": "source", "anchor": "run", "relative_path": "...", "sha256": "...", "size": 0}],
  "provenance": {"tools": [], "code_commit": "...", "policy_id": "...", "descriptor_sources": []},
  "transformations": [],
  "findings": [{"rule_id": "PLANE-01", "status": "REVIEW", "severity": "candidate_conflict", "evidence_refs": [], "measurements": {}, "limitations": []}],
  "verdicts": {"graph": "NOT_RUN", "numerical": "REVIEW", "linked": "NOT_RUN", "native": "NOT_RUN", "geometry": "NOT_RUN", "convergence": "NOT_ASSESSED", "experimental": "NOT_ASSESSED"},
  "input_integrity": "UNCHANGED",
  "next_action": {"kind": "REVIEW_REQUIRED", "reason_codes": []}
}
```

Per-rule states: `PASS`, `REVIEW`, `FAIL`, `ERROR`, `UNSUPPORTED`, `NOT_RUN`. `PASS` names
only the checked invariant; `FAIL` requires a demonstrated invariant violation.
Separate `ERROR` (execution/parse failure) from chemical findings. Keep successful
checks and limitations when another layer fails. A machine-readable measurement
never becomes an overall scientific approval by Boolean reduction.

Implementation order: (1) read-only provenance/graph/numerical checks and receipts;
(2) linked/native extraction and exact coverage adapters; (3) geometry/completion
assessment with calibrated finding classes; (4) separately validated acquisition,
bounded generation and approved transformations; (5) ordinary fresh full-auto
acceptance without manually staged dictionaries. Earlier geometry work supplies
fixtures, not an obligation to rerun every passed experiment.

Future orchestration may select `CONTINUE`, `GENERATE_CANDIDATE`, `REVIEW_REQUIRED`
or `BLOCK_AFFECTED_STAGE` only under a versioned policy. Preserve each attempt,
limit generator recipes/retries and re-audit candidates through all applicable
layers. Exact repair policies need input version/hash scope and derivative
provenance; generator exit zero is not acceptance. Required missing definitions,
unusable/contradictory effective restraints or lost identity/integrity can block
the affected operation. Unknown optional comparisons may remain warnings. Any
new runtime blocking rule or automatic chemistry action needs its own review,
tests and migration/compatibility analysis; this document installs none.
