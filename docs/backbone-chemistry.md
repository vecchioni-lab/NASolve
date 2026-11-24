# Backbone chemistry in NASolve

Status: active contract. Terminal-phosphate construction, final-geometry
audit, targeted Doctor rescue, and automatic proactive protection from the
first AutoRefine round are implemented and live-validated.

## Goal

NASolve should automate ordinary phosphodiester chemistry aggressively while
remaining honest about backbone chemistries it does not understand. Residue
identity, base-pair/stacking geometry, backbone connectivity, and terminal
chemistry are treated as related but distinct concerns.

The automatic default is **standard phosphodiester**. A non-standard backbone
is never inferred from atom names, distances, residue codes, or a monomer
library entry. A user must explicitly mark the affected site.

For a registered crystal-boundary bond the native runtime puts the relevant
atoms in one local Cartesian frame, evaluates the ordinary Phenix angle and
torsion terms there, and rotates their derivatives back to the stored atom
positions. The existing bond and nonbonded exclusions still apply. Each
selection inherits the complete terms it contains. A five-cycle restart from
a registered 5W6W-derived child measured 107.30° and 113.88° at the two
phosphate oxygens with these forces. The matched distance-only run gave
75.17° and 127.56°. Chemical intent, image selection and final readback
remain separate decisions. A periodic central strand can average a real
nick over several equivalent copies. Its crystal representative can be cut
at a different base without identifying the nick.

## Checking the direction of a repaired phosphate

A short O3′–P bond and plausible tetrahedral angles can survive even when
the whole phosphate points into a duplex. Inspect both nonbridging oxygen
positions after molecular replacement, gap filling and crystal recutting.
Register the paired bases on both sides of the step, put them in their
declared crystal images, and compare the OP1/OP2 midpoint and the two
individual directions with the neighbouring backbone. A label exchange
leaves the midpoint in the same place. One oxygen can legitimately point
toward a groove. At a crossover, true nick or unresolved base pair, record
which local comparison is possible.

A repair trial must preserve both ester bonds, the sugar stereocentres
and the intended phosphate chemistry. Compare the starting pose with a
locally rotated or reference-based alternative under the same refinement
restraints and diffraction observations. Measure the written model and
retain the original free flags. A change of crystal representative alone
must preserve the local orientation. The general automatic repair remains
in the [crystal-boundary queue](cif-doctor-completion-queue.md#crystal-phosphates-after-an-asymmetric-unit-recut).

The central A11 O3′–A12 P linkage is a known pair of controls. In deposited
5W6W the OP1/OP2 midpoint projects 0.65 Å toward the local duplex axis.
Both individual oxygens point inward. The six standard templates introduced
at `eda1df7b` carry the outward pose, with the midpoint 0.57–0.58 Å away
from the axis. The packaged `5W6W_noPO4.pdb` retains the inward pose for
explicit historical tests. AutoMR uses a named pair template or its standard
`C_G.pdb` fallback. The original and current files therefore serve different
purposes. [Deposited 5W6W](https://www.rcsb.org/structure/5W6W).

For a metal refinement, check its actual parent model. One older DF–Hg–DT
lineage inherited the inward A12 phosphate in molecular replacement and
kept it through Coot, scaffold restoration and ReadySet. A PDU:PDU lineage
started outward and remained outward through two checked five-cycle fits.
PostMR deliberately restores the incoming sugar and phosphate when changing
a base. A pre-existing backbone error needs a separate, source-traced trial.

In matched five-cycle Phenix refinements of the DF–Hg–DT model, the A12
oxygen midpoint stayed 0.58 Å inward from the original start and 0.41 Å
outward from a locally corrected start. Only six backbone coordinates
changed in the trial seed. The adjacent sugar angle improved from 124.1°
to 110.8°. The neighbouring T–A contacts shortened further and final free R
rose from 0.2974 to 0.3329. Keep this as a local comparison. A new metal
run can inspect its own parent or numbered child using the
[paired-step measurement](cif-doctor.md#inspecting-a-phosphate-at-a-crystal-boundary).

## Standard phosphodiester contract

For ordinary DNA/RNA-like backbones, including sugar variants that retain the
same phosphodiester connection (for example LNA-style residues), NASolve applies
the standard contract:

- an internal nucleotide phosphate uses P, OP1 and OP2 and is connected to the
  previous residue through O3'-P;
- an internal phosphate must not retain terminal OP3/O3P;
- a requested 5'-terminal phosphate is a **complete terminal group**, not an
  OP3 exception: P, OP1, OP2 and OP3 are required;
- a requested 5'-terminal phosphate must not also have an incoming O3'-P link;
- ordinary 5'-OH termini are not given a phosphate unless the user or selected
  recipe explicitly requests one.

The existing historical `allow_op3_sites` field remains readable for old frozen
runs, but new user-facing configuration should use `five_prime_phosphate_sites`.
The chemistry request is a terminal-phosphate state; OP3 is only one atom in
that state.

Coordinate cleanup and effective dictionary chemistry require separate checks.
Removing OP3 from a PDB does not itself remove a monomer dictionary's OP3,
attached hydrogen or terminal O3' typing. Production linked profiles currently
cover the declared 1AP/DZ/DP/5CM scope; they are not a generic monomer-to-polymer
adapter.

The explicit `06_Cedar` diagnostic now prepares source-preserving, per-site
DNA derivatives using declared incoming/outgoing links and terminal states.
It requires a context for every model site sharing a component code, finds H
through graph adjacency, retains source OP2 protonation, and audits projected
and actual native monomers. This remains external diagnostic preparation;
production profiles and PostMR continuation are unchanged. The fresh 05 trial
has four declared free 5′-OH ends and zero coordinate OP3 atoms. Its earlier
D:1-phosphate exception must not be inherited. See [CIF Doctor](cif-doctor.md#source-preserving-linked-state-diagnostic).

The October 10 combined-W diagnostic passed graph-based leaving-atom/hydrogen
removal and O3' typing for IGU/IMC/CGY/DX, with no missing heavy atoms or dangling
references and D:1 terminal phosphate preserved. This was a separate diagnostic,
not integrated production behavior. Source-specific OP2 protonation was retained
and remains a geometry/chemical-state review item. Generalization must follow
verified site connectivity, preserve terminal/nick intent and audit the effective
native restraints; it must not assume that a hydrogen-free coordinate model has
an unprotonated dictionary. Exact evidence and remaining checks are in the
[native ledger](native-modified-pair-live-validation.md).

## Declared symmetry continuation — planned shared contract

A chain boundary in the asymmetric unit need not be a chemical terminus. Pine
will carry editable declared connections, including exact atom identities,
symmetry operations and lattice shifts, separately from current coordinate
support and refinement capability. TopoStitch previews those connections; Cedar
checks the chemistry and whether native restraints actually enforce it. Reslicing
or an edit must preserve previous choices and explicitly remap endpoints/images
or mark them unresolved. Missing local neighbors must not silently change intent.

### The central strand in the 5W6W scaffold

**In the standard 5W6W scaffold, B:7 O3′ bonds to B:1 P across crystal
symmetry.** This is the lab's standing interpretation for 5W6W and derivatives
that retain its central strand. Simon confirmed the covalent endpoints and
the use of the closest crystal copy on 22 November 2026. In the deposited
setting, hold B:1 P fixed and apply `-x+y,-x,z` to B:7 O3′. This operation
needs zero additional unit-cell translation. **B:1 is an internal phosphate
with P, OP1 and OP2. It has no OP3.** D:1 is the separately declared terminal
5′ phosphate in the standard W recipe.

The nearest and next-nearest copies of B:7 O3′ are 2.795 and 21.895 Å from
B:1 P in the 5W6W starting frame. In the archived PDU:PDU refinement they
are 2.824 and 22.867 Å. A stretched starting gap is a geometry issue. It
does not change the declared chemistry. When a model is renumbered, reindexed
or resliced, follow the corresponding atoms and transform the operation into
the new frame. A construct-specific nick or changed central strand takes
precedence. Apply the investigator's junction convention at this position;
other nicks, crossovers and their occupancies have separate evidence.
[Deposited 5W6W](https://www.rcsb.org/structure/5W6W).

To check the image in a saved model, run
`nasolve cif-doctor phosphate-image MODEL.pdb --phosphate B:1 --o3 B:7 --nearest-image`.
Use the remapped site labels when the construct's numbering has changed.

Pine records a directed backbone edge from the 3′ oxygen to the receiving
phosphorus. Its [5W6W continuation declaration](recipes/5w6w-central-continuation.json)
therefore uses the inverse operation, `-y,x-y,z`, on **B:1 P** while B:7 O3′
stays fixed. Both descriptions give 2.795 Å in the project's
[`C_G.pdb` starting frame](../MR_frames/5W6W/C_G.pdb). This declaration
requires the two registered B-strand ends to be representation boundaries.
It describes the seven-site central strand. Other strands and their nicks
can be declared separately.

Doctor can [read that registration on an exact checkpoint](cif-doctor.md#inspecting-a-phosphate-at-a-crystal-boundary).
The archived PDU:PDU `refine-005` retained B:1 P and reported B:7 O3′ only
as a nonbonded neighbour. If a different test model lacks B:1 P, the reader
keeps the supplied declaration and reports that the distance is unavailable.

In the controlled PDU:PDU fit, a distance alone closed the gap but left the
two O3′–P–OP angles at 84.5° and 129.3°. With angle and torsion forces evaluated
in the named mate they reached 107.5° and 110.5° after five Phenix cycles.
The ordinary adaptive refinement settings also improved the angles in a
separate five-cycle comparison, from 72.0°/139.1° to 103.2°/115.7°.
When Phenix reopened that written model with only its seven inherited inputs,
it treated the 1.620 Å junction as a nonbonded contact. Supplying the distance
alone still left the crossing angles and torsions absent. Pine owns editable
connection intent. Routine continuation must carry both the written child
and the complete local restraints. [Cedar completion queue](cif-doctor-completion-queue.md#pipeline-position).

### Two crossovers in the PDU:PDU test scaffold

Simon confirmed on 23 November 2026 that D:7 O3′ continues into C:8 P in
the 5W6W-derived PDU:PDU scaffold with A:1–A:21. Its central B:7–B:1
connection also applies. The [two-connection declaration](recipes/5w6w-pdu-backbone-continuations.json)
keeps the original central edge and adds the crossover. Holding each O3′
fixed, apply `-y,x-y,z` to B:1 P and `-x+y,-x,z` to C:8 P. Both use zero
additional lattice shift. D:1 retains its separate terminal phosphate.
Register the declaration against the actual coordinates before using it.

In the saved MR and Coot models, the two distances are 3.340 and 3.017 Å.
In all three subsequent five-cycle PDU comparison models, Phenix restrained
B:7–B:1 and treated D:7–C:8 as a nonbonded contact with a 3.4 Å target.
The latter gap measured 2.934, 3.043 and 2.993 Å. Four intact T→G
links in the same model agree on the bond, four angles and three torsions
for the D:7 crossover. The native bond target is 1.607 Å. Two intact
A→C links supply the reference for the central B strand. This declaration
does not establish ligation or occupancy in individual crystal copies.

C558 applied both declared bonds, all eight crossing angles and all six
torsions together in five standalone Phenix 2.2.1-6174 cycles. B:7–B:1
finished at 1.645 Å and D:7–C:8 at 1.627 Å. The crossover's O3′–P–OP1
and O3′–P–OP2 angles finished at 112.5° and 107.2°. Its C4′–C3′–O3′–P
torsion remained 4.9 reference standard deviations from its target, so
the repaired bond alone cannot establish the backbone conformation.
D:1 retained all eleven terminal restraints. The same 1,778 working and
124 free reflections were retained in the one-link and two-link fits.

The ordinary numbered test used the archived starting model and its seven
original restraint files. Starting from manual-001, two five-cycle rounds
gave B:7–B:1 and D:7–C:8 distances of 1.649/1.630 Å and then 1.643/1.647 Å.
Both had eight crossing angles, six torsions, all eleven D:1 terminal terms,
and the same 1,778 working and 124 free indices. R-work/free were
0.2354/0.2964 and 0.2171/0.2826. Refine-005 stayed selected.

The second fit still placed D:7 O3′ and C:8 P at −1.87 and −1.05 whole-map
rms units in its unfilled 2mFo−DFc map at 4.19 Å. The donor C4′–C3′–O3′–P
torsion was 54.5°, against a native target of −140° and a width of 35°.
In the first fit, two of four chemically matched ordinary T→G links also
had positive values (92.5° and 81.5°). All donor sugar stereocentres tested
kept their handedness. These measurements leave the crossover conformation
open. In the restarted fit the four ordinary values were −122.3°, +87.0°,
+78.4° and −176.0°. To read these eight geometric terms for any fitted
continuation, use `cif-doctor phosphate-image RUN --checkpoint ID
--saved-continuation-id NUMBER --restraint-deviations --json`. The target
and its weight come from the starting native chemistry. The junction and
ordinary-link coordinates come from the named written checkpoint.

With the historical PDU restraints, the final two propynyl tips lay
2.338/1.243 Å from their ring planes.

C562 started again from the original 862-atom C290 Coot model. ReadySet
2.2.1-6174 rebuilt PDU from chemical components when given the historical
dictionary. Its generated C5–C5A and C5B–C5M targets were both 1.527 Å,
and its base plane stopped at the ring. With the qualified dictionary,
ReadySet used the supplied restraints. The two targets were 1.431 and 1.470 Å,
with the first arm carbon C5A in the base plane. Both ReadySet runs preserved
every coordinate, occupancy and displacement parameter. Both crystal gaps
were still open. The ordinary phosphate audit identified 38 local incoming
bonds, the declared D:1 terminal phosphate and two unresolved incoming sites.

To inspect that stage on another run, use `nasolve cif-doctor prepared-backbone RUN`.
It reads the model, source dictionaries and terminal consent recorded when Coot
returned. To account for the crystal connections, provide the three matching
files from the same source frame.

```sh
nasolve cif-doctor prepared-backbone RUN --registration registration.json \
  --discovery-input discovery.json --backbone-continuations continuations.json --json
```

The O3′ image in each result acts on the donor oxygen. The inverse operator
in the declaration acts on P. On the starting PDU scaffold the donor images
are `-x+y,-x,z` for B:7 and `-y,x-y,z` for D:7. Omitting either declaration
leaves a named phosphate unaccounted for. A protected terminus or an O3′
that already has a local partner cannot be used for a new connection.
This inspection is available even when Coot returned before a dictionary
request could be published. A distance across a declared gap is a measurement
on the starting model. The five-cycle comparison below measures the fitted bonds.

Add `--candidate-model RETURNED.pdb --native-receipt native_receipt.json`
to the same command to review an unselected set of refinement inputs. Supply
the exact candidate PDB used for the preserved Phenix interpretation. The
reader checks the modeled heavy-atom identities, local bonds, terminal intent
and the crystal copy of each registered residue. Each native target needs
matching intact bonds in the same model's audited backbone. The bond, angles
and torsions must be measurable at the proposed junction and at every intact
reference. The JSON includes the input dictionary and restraint-file digests
in their recorded order.

On the corrected ReadySet return the two crystal gaps were still 3.340 and
3.017 Å. Two intact A→C links and four intact T→G links supplied the same
1.607 Å distance target. The native files contained the corrected PDU
dictionary and six restraint files. A control with the extra D:7 O3′–B:1 P
bond was refused. This comparison establishes the inputs to a possible
refinement. The ordinary numbered child and its Free-R data still require a
separate handoff.

One standalone five-cycle Phenix refinement used the corrected returned model,
the two registered crystal partners, the original reflection flags and the seven
effective restraint files. The R values were read at the start and end of the
4.19 Å refinement.

| Measurement | After ReadySet | After refinement |
| --- | ---: | ---: |
| B:7 O3′–B:1 P across its registered image | 3.340 Å | 1.624 Å |
| D:7 O3′–C:8 P across its registered image | 3.017 Å | 1.617 Å |
| A:12 / B:4 propynyl tip height above the six-atom ring plane | 0.094 / 0.093 Å | 0.290 / 0.246 Å |
| R-work / R-free | 0.3389 / 0.4317 | 0.2348 / 0.3023 |

The refined terminal PDU arm bonds were 1.454/1.493 Å. The native base
planes contained C5A at both sites and left the methyl tips free. Each
crossing had one printed bond and four crossing angles. The terminal D:1
retained all eleven restraints. All 124 free flags survived. Phenix excluded
seven working reflections, leaving 1,778 working and 124 free indices, exactly
the final set in the archived comparison. The D:7 C4′–C3′–O3′–P torsion
was +37.3° against −140° with a width of 35°. Its O3′ and C:8 P sampled
−1.83 and −1.26 whole-map rms units in the unfilled 2mFo−DFc map. The bond
and arm measurements demonstrate restraint survival. The local crossover
conformation remains open. This experiment created no numbered checkpoint.

### Crossovers in the FT–Hg scaffold

In the separate FT_Hg construct, the investigator declared the central B
continuation and confirmed the C/D crossover. A runs from 1 to 21 in each of
three saved models. On the selected source model, the directed correspondences
are B:7 O3′ to B:1 P under `-x+y,-x,z` and D:7 O3′ to C:8 P under `-y,x-y,z`,
both with zero lattice shift. B:1 and C:8 contain P/OP1/OP2. D:1 is a declared
5′ terminal phosphate and also contains OP3.

If both connections occur in all three equivalent positions, tracing the 38
ordinary O3′–P links in each copy plus six image connections gives one closed
21-nucleotide B path, three 14-nucleotide D:1–C:14 paths and three separate
21-nucleotide A strands. The two image gaps in the measured model are 3.100 and
3.027 Å, compared with 1.593–1.639 Å in its ordinary backbone. At the second
gap the O3′–P–OP2 angle measures 55.79°. Keep this conditional strand map with
the construct. Ligation, nick state, occupancy and native enforcement remain
open. Reslicing must preserve the declared images and report the current gaps.

## Building a requested 5'-terminal phosphate

When a site is explicitly declared as a 5'-terminal phosphate, PostMR runs an
`ensure` step before the ordinary phosphate sanitizer:

1. a complete P/OP1/OP2/OP3 group is preserved;
2. P/OP1/OP2 with missing OP3 is completed using tetrahedral starting geometry;
3. if no phosphate atoms are present, P/OP1/OP2/OP3 are seeded from the local
   O5'-C5'-C4' sugar frame with idealized, clash-checked starting coordinates;
4. any other partial phosphate state stops for review rather than guessing;
5. the generated geometry is recorded and remains subject to ReadySet/Phenix
   regularization and final model inspection.

The local-frame construction is a starting-coordinate operation, not an
assertion that the initial group is the experimentally measured phosphate
geometry. Live validation on a phosphate-free 5W6W fixture established that the
constructed group can enter ReadySet and native Phenix interpretation cleanly.
Phenix's native terminal-phosphate geometry is not a perfectly symmetric
109.47-degree tetrahedron; where exact native ideals matter, NASolve should read
or preserve the authoritative Phenix chemistry rather than substitute its own
idealized target.

## Refinement protection for constructed terminal chemistry

Low-information terminal groups can be driven into chemically implausible
internal geometry by global diffraction weighting even when their starting
coordinates and native Phenix restraints are valid. For a declared standard
terminal phosphate, NASolve therefore treats local geometry protection as part
of the normal chemistry contract rather than waiting for an unprotected
refinement to fail first.

The production contract is:

1. construct the explicitly requested terminal group in a local molecular frame;
2. validate it for completeness, connectivity, severe clashes, and Phenix
   interpretability;
3. obtain the authoritative native terminal-phosphate geometry from Phenix
   interpretation rather than hard-coding a second NASolve geometry table;
4. before the first coordinate refinement, generate local
   `geometry_restraints.edits` using `action = change` to retain Phenix's native
   ideals while tightening only the reviewed low-information internal geometry;
5. keep normal global diffraction/stereochemistry weighting unless an
   independent diagnostic justifies changing it;
6. record the protection file as a normal checkpoint restraint artifact so it
   is inherited transitively by every refinement, Doctor branch, or manual
   child descended from that protected checkpoint;
7. after every refinement, audit the declared terminal group against the final
   Phenix geometry restraints; and
8. if the protected group still exceeds the guarded geometry threshold, stop
   for review and allow Refine Doctor to create a bounded clean-parent rescue
   rather than silently accepting the distorted coordinates.

The first validated 5'-phosphate experiment established this policy
experimentally. An unprotected default refinement drove one native P-centered
angle to approximately 7 sigma from its Phenix target. A sibling using local
`action = change` protection retained normal global X-ray weighting, removed
the severe violation, passed all 11 terminal-phosphate geometry checks, and did
not worsen the global R factors. The protected branch therefore becomes the
production default; the deliberately unprotected route remains diagnostic.

Automatic first-round protection was subsequently live-validated on ED
`run_010/refine-005`, branched directly from `postmr`. AutoRefine harvested the
native terminal geometry with `phenix.pdb_interpretation`, generated the six
sigma=1-degree P-centered `action = change` restraints before coordinate
refinement, and carried their semantic provenance into the checkpoint. The
final D:1 audit passed all 11 restraints with zero severe violations and reached
Rwork/Rfree 0.1735/0.1707 without an unprotected precursor.

Protection is lineage-scoped. A child of a protected checkpoint inherits the
protection automatically. A deliberate branch from an older unprotected
checkpoint does not silently acquire it unless terminal-phosphate protection is
being generated anew from the declared chemistry contract. Future merge/rebase
operations must preserve all applicable chemistry-protection restraints and
rerun the terminal-geometry audit afterward.

An advanced opt-out may disable proactive terminal-phosphate protection for
diagnostic or method-development work. Such an override must be explicit,
prominently reported in provenance, and must **not** disable the final geometry
audit. Automatic chemistry rescue should also remain suppressed while that
override is active, so "off" means deliberately off rather than partially off.

A globally conservative `wxc_scale` branch remains useful as a diagnostic, but
blanket global reweighting is not the preferred production response to a local
terminal-group geometry problem.

NARestraints remains responsible for reviewed pairing/stacking geometry and
should not duplicate Phenix's native terminal-phosphate restraints.

## 3'-terminal phosphates

3'-phosphate chemistry exists and should eventually be represented by a
reviewed recipe. NASolve does **not** currently guess a representation for it.
Unlike a 5'-terminal phosphate, a 3'-terminal phosphate can collide with the
usual P atom naming/ownership convention of a nucleotide that already carries
its incoming phosphate, so a real example and reviewed atom/link convention
should precede automation.

When a validated 3'-phosphate example is available, its constructor should
explicitly inherit the lessons from the 5'-phosphate work rather than being
implemented as a simple atom-name swap:

- require an explicit, site-scoped 3'-phosphate declaration;
- establish authoritative atom ownership, naming, connectivity, and native
  Phenix geometry from a real reviewed example before coding the recipe;
- construct missing atoms in a local molecular frame defined from the terminal
  sugar, with deterministic orientation and clash checks;
- preserve complete existing groups and fail closed on ambiguous partial states;
- treat constructed coordinates as starting coordinates rather than measured
  geometry;
- validate the prepared group through ReadySet/Phenix before refinement;
- run the same post-refinement local-geometry audit used for constructed
  5'-phosphate chemistry; and
- if refinement distorts the low-information group, prefer a Refine Doctor
  sibling using local `action = change` tightening of **native** restraints over
  duplicate custom restraints or a blanket reduction of global X-ray weight.

No 3'-phosphate constructor should be generalized from the current 5' routine
until this atom/link convention and a live refinement example are reviewed.

If you need 3'-phosphate support now, please contact the developers with an
example model and intended linkage.

## Non-standard backbones

A site may be declared in `nasolve.txt`:

```ini
[automr]
allow_unreviewed_backbone = true

[backbones]
A:12 = experimental_passthrough
```

`experimental_passthrough` is deliberately not a chemistry recipe. It means:

- apply otherwise supported mutation/model-preparation steps;
- do not apply the standard phosphate-linkage validator at the flagged site;
- do not invent missing atoms, bonds, or atom deletions for that site;
- preserve the site in run/campaign provenance as chemically unvalidated;
- continue only because the user explicitly opted into unreviewed chemistry;
- require human inspection before the structure is accepted or deposited.

This makes one-off GNA/PNA/TNA/other backbone experiments possible without
pretending NASolve understands their connectivity.

## Human review

Runs containing experimental passthrough sites retain a persistent
`UNREVIEWED_NONSTANDARD_BACKBONE` warning. The review interaction is:

1. After a successful interactive AutoRefine, NASolve asks whether to show the
   flagged result in Coot (`y/n`). The same flow is available later through
   `nasolve backbone-review RUN`.
2. If opened, the user inspects the current model and maps.
3. NASolve then asks whether the chemistry has been reviewed (`y/n`).
4. Confirmation writes a separate review record with a run-anchored model
   reference and the inspected model hash and marks it `USER_REVIEWED`; it does
   not erase the fact that passthrough chemistry was used.

Declining review does not convert an otherwise successful refinement into a
failed run; the warning remains pending. For non-interactive campaigns, the
same condition remains an inspection flag and can be reviewed later with the
dedicated backbone review command.

## Future reviewed custom recipes

A future custom-backbone recipe should be intentionally small and readable by a
chemist/crystallographer. The desired language is closer to:

```text
Backbone recipe: example phosphodiester-like linkage
incoming connection: previous O3' -> this P
outgoing connection: this O3' -> next P
delete from internal residue: OP3
keep: P, OP1, OP2
```

than to a low-level machine graph. Internally NASolve can compile that text into
strict selections and checks, but the source recipe should remain auditable by
a human.

No generic custom-linkage executor is included yet because we do not have a
reviewed non-standard example in this repository. If your structure uses GNA,
PNA, TNA, or another unsupported backbone, please contact the developers (Simon
Vecchioni / Jens Mueller) with the intended inter-residue atom connections and
atoms that should be deleted or retained. A validated real case can then be
promoted into a reusable recipe rather than guessed.

## Relationship to NARestraints

Backbone chemistry does not by itself disable NARestraints pairing or stacking.
A single non-standard residue may still use the same base mapping and stacking
geometry as neighboring nucleotides. NARestraints owns reviewed pairing and
stacking geometry; NASolve owns model preparation, inter-residue backbone
chemistry, terminal chemistry, dictionary precedence, and provenance.

## Safety and provenance rules

- Raw input models and numbered runs are never rewritten in place.
- Automatic standard-phosphodiester corrections are site- and connectivity-
  checked.
- Unsupported backbone chemistry is opt-in and remains visibly unvalidated.
- Human review changes review status but never removes passthrough provenance.
- DE dictionary repair and sulfur-contact validation are separate work and are
  not part of this feature.
