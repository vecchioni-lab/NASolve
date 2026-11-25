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
bond was refused.

If Coot and ReadySet both ran in this run and its `postmr` checkpoint contains
the reviewed ReadySet model, register on the original Coot coordinates and fit
the ReadySet coordinates in one step.

```sh
nasolve autorefine RUN --from postmr --registered-continuations 1 2 \
  --registration registration.json --discovery-input discovery.json \
  --backbone-continuations continuations.json --native-receipt native_receipt.json \
  --prepared-backbone-source RUN
```

For an imported preparation, name the checkpoint containing the candidate and
the ancestor containing the registered Coot model. Both runs must agree on the
frozen backbone intent and measured reflection data.

```sh
nasolve autorefine RECEIVING_RUN --from manual-002 --registration-checkpoint manual-001 \
  --registered-continuations 1 2 --registration registration.json \
  --discovery-input discovery.json --backbone-continuations continuations.json \
  --native-receipt native_receipt.json --prepared-backbone-source SOURCE_RUN
```

The model, dictionaries and inherited restraints must already agree with the
native interpretation. The numbered round copies any missing, self-contained
PHIL restraints in order. For a declared terminal phosphate it identifies the
matching protection by regenerating the angles with the candidate model and
dictionaries. The run keeps one copy of those restraints. The checked
source is recorded in `outputs.prepared_backbone`. On restart the usual
`--from refine-002 --native-receipt NEW_RECEIPT` uses the fitted model.

In C567 the two PDU crystal bonds went from 3.340/3.017 Å to 1.610/1.633 Å
after five ordinary cycles and to 1.643/1.627 Å in the relocated restart.
All 38 ordinary bonds, eleven D:1 terminal terms and 124 original free
observations survived both fits. The two PDU tips ended 0.182/0.245 Å from
their rings. The D:7 donor torsion stayed at +36.0° against a native target
of −140° with a 35° width. D:7 O3′ and C:8 P were at −1.80 and −1.18
whole-map rms in the unfilled 2mFo−DFc map. Both fits stayed unselected.

Check the actual partner image even when the atom names agree. In a native
input containing the B:7 O3′–B:1 P restraint, the O3′ image relative to P
was `-x+y,-x,z`. Those atoms were 3.340 Å apart before fitting. Substituting
`-y,x-y,z` gave 25.189 Å. The ordinary command now reports both images
before starting the wrong fit. Integral cell translations matter as well.
An existing crystal bond with an unreadable image requires review.

C569 repeated ordinary construction from the same MR solution with the
corrected PDU dictionary present at the first Coot mutation. Its Cartesian
template put C5B–C5M at 1.6074 Å while its target was 1.470(20) Å. In a
private comparison, moving the terminal methyl and its three dictionary
hydrogens along that bond gave a template distance of 1.4700 Å. All
restraint rows, other template bond lengths and the other 860 model atom
coordinates were preserved. ReadySet retained both as built. The same
seven restraint inputs by chemical content, original amplitudes, 124 free
reflections and both crossover declarations went into each five-cycle fit.

| A:12 / B:4 | Original dictionary positions | Adjusted terminal positions |
| --- | --- | --- |
| Coot / ReadySet terminal C–C distance (Å) | 1.607 / 1.608 | 1.470 / 1.470 |
| Phenix terminal C–C distance (Å) | 1.443 / 1.456 | 1.455 / 1.501 |
| Phenix tip height above six-atom ring (Å) | 0.242 / 0.187 | 0.445 / 0.081 |
| B:7–B:1 / D:7–C:8 phosphate distance (Å) | 1.632 / 1.641 | 1.644 / 1.616 |
| R-work / R-free | 0.2213 / 0.2856 | 0.2207 / 0.2833 |

The correction improved the starting bond at both sites. After refinement
the tip lay closer to its ring at B:4 and farther away at A:12. The D:7
donor torsion was +37.6° and +30.9° respectively. Both endpoints remain
unselected. Use the new template comparison to find candidate construction
problems across components. A general repair needs an independent component
and a separate check of its geometry after native refinement.

C570 repeated the adjusted PDU construction, then fitted its ordinary
`postmr` checkpoint directly. The first five cycles produced exactly the same
coordinate file as the two named checkpoints in C569. After moving the run,
five more cycles gave crystal bonds of 1.641 and 1.632 Å. The 124 original free
reflections and eleven D:1 terms survived. The two PDU tips ended 0.180 and
0.284 Å from their rings, and the D:7 torsion remained at +40.7°. A different
run with equivalent starting coordinates was refused before creating a round.

At that second D:7 endpoint the onefold native donor torsion was only 0.72°
from the angle directly opposite its −140° target. Using the actual crystal
image and the native Phenix torsion, the residual was 15.673 against a maximum
of 15.673. Its turning force was **1.26%** of this term's maximum. The B:7
control retained **85.8%**. A small virtual rotation gave the same derivative
as the native atom gradients. These are single-term measurements on the
written coordinates. The total refinement force includes neighboring geometry
and diffraction.

Four intact T→G steps supplied alternative local shapes for D:7–C:8. Across
both written checkpoints, fitting four donor sugar atoms and the acceptor P
could reproduce a plausible torsion or a plausible O3′–P distance separately.
For example, in the second checkpoint the A:9–A:10 shape gave −149.5° and
a 1.188 Å bond. D:2–D:3 gave 1.614 Å and +60.1°. Moving a six-atom linkage
as a rigid group between two fixed sugars stretched the recipient O5′–C5′
bond to 1.76–2.45 Å there, from 1.436 Å.

With the two fitted O3′ bond lengths fixed, moving only O3′ around their
intersection circle could reach −140°. At that position the O3′–P–OP2 angle
collapsed to 63.9° and O3′–P–O5′ opened to 145.2°. The native targets were
108° and 104°. This numerical trial moved O3′ by 1.50 Å. The existing
4.19 Å unfilled map was weak at the written O3′ and P (−1.86 and −1.18
whole-map rms units). A jointly adjustable sugar–phosphate fragment with
anchored flanking bases is the next starting model to test against the data.
Both existing refinements and their selections are preserved.

**C574, fitting the two sugars together.** In the 5W6W-derived PDU:PDU
scaffold, 19 atoms could move during construction, spanning the two sugars and
C:8 P, OP1 and OP2. The other 843 atoms, including the bases, anchored the
fragment. Four intact T→G steps supplied independent starting shapes. The
D:2–D:3 start reached −136.3° against the native −140° donor torsion, with
all six local stereocentre signs preserved. It was chosen before inspecting
diffraction. Five cycles of Phenix 2.2.1-6174 then fitted the complete models
with both registered crystal bonds and the same 1,778 working and 124 free
reflections.

| Starting shape and refinement weights | D:7 donor turn | D:7 O3′–C:8 P | Largest sugar-angle deviation at D:7 or C:8, in native restraint widths | R-work / R-free |
| --- | ---: | ---: | ---: | ---: |
| Written shape, ordinary weights | +43.0° | 1.635 Å | 2.73 | 0.2022 / 0.2741 |
| D:2–D:3 start, ordinary weights | −122.5° | 1.627 Å | 5.17 | 0.2017 / 0.2801 |
| C:11–C:12 start, ordinary weights | −58.4° | 1.626 Å | 3.30 | 0.2079 / 0.2662 |
| Written shape, fixed weights | +21.9° | 1.616 Å | 1.68 | 0.2492 / 0.3134 |
| D:2–D:3 start, same fixed weights | −135.6° | 1.606 Å | 2.65 | 0.2451 / 0.3086 |

The ordinary D:2–D:3 fit compressed D:7 C2′–C3′–O3′ to 96.5° against
109.4°. Fixing the weights improved local geometry and worsened the overall
diffraction agreement. Both PDU methyl tips in the fixed alternative lay
within 0.14 Å of their base planes. Two common maps omitted all 19 atoms,
used only working amplitudes and differed in bulk-solvent treatment. Across
those 19 atoms, the ordinary alternative minus the ordinary written-shape
control averaged −0.047 and −0.003 whole-map rms units in the difference
maps. Nearby samples share density. At 4.19 Å there is insufficient evidence
to choose a local conformation. Keep the alternatives available and carry
the two-sugar check forward to an independently declared junction.

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

<a id="crossovers-in-the-ft-hg-scaffold"></a>

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
open for that source model. Reslicing must preserve the declared images and
report the current gaps.

**C575, after fitting the two FT–Hg junctions.** Four later five-cycle native
controls used those exact declared partners, experimental phases and 59 free
reflections. Two starting models differed at six atoms of B:7 and B:1. Each
was fitted with Hg either fixed or free to move in XYZ. The original and
altered starts had B:7 C4′–C3′–O3′ angles of 111.2° and 114.5°, against
109.7°. After refinement all four angles were 126.3–129.3°. The two intact
A→C references, A:16–A:17 and B:5–B:6, ended at 110.4–114.4°. B:1 OP2–P–O5′
also closed to 91.2–93.5° against 108°, even as the crystal O3′–P bond
shortened to 1.649–1.658 Å. Each of these angles had one ordinary covalent
target in each initial and final Phenix geometry table.

**C576, allowing both sugars to move during construction.** Each trial changed
19 coordinates at B:7 and B:1. All six checked sugar stereocentres kept
their handedness. The B:5–B:6 template squeezed B:7 OP2–P–O5′ to 41.2°
in construction, against 108°. The relaxed written start and the A:16–A:17
template went through five cycles of the same fixed-Hg Phenix 2.2.1-6174
protocol. Each had its own native chemistry inspection and two registered
crystal links. The supplied phase coefficients and original 59 Free-R flags
matched at initialization and on return.

| After refinement | Archived original | Relaxed written start | A:16–A:17 start | Native target |
| --- | ---: | ---: | ---: | ---: |
| B:7 O3′–B:1 P (Å) | 1.650 | 1.653 | 1.638 | 1.607 |
| B:7 C4′–C3′–O3′ (°) | 129.3 | 116.4 | 101.1 | 109.7 |
| B:1 OP2–P–O5′ (°) | 91.2 | 97.3 | 108.7 | 108.0 |
| R-free | 0.3341 | 0.3363 | 0.3367 | |

Both new fits opened B:7 C2′–C1′–N9 to 122.3–122.8°, against 114.3° with a
1.4° restraint width. All four fixed-Hg endpoints passed the same local
2.2 Å crystal-contact screen. The two new Hg–N3 distances were 1.99–2.03 Å,
and the N3–Hg–N3 angle was 172.0–172.7°. The two sugar paths finish 1.08 Å
apart RMS over 19 atoms. At 5.06 Å, their average sampled densities differ by
0.13 map standard deviations in a working-only supplied-phase map and 0.10
in the opposite direction in a common 19-atom omit difference map. Neither
model has been selected. Read each endpoint with its own final GEO using
`phosphate-image --flanking-geometry`. The option includes the internal
bonds and angles of the named reference residues as well as the junction.

**C577, why the B:7 sugar opens.** An instrumented replay of the A:16–A:17
trial produced the same final coordinate file, final GEO and unrounded
returned model byte for byte. The B:7 C2′–C1′–N9 angle moved from 119.12° to
122.85°. The biggest opening, 3.44°, occurred during the second cycle's
coordinate fit against diffraction. Its own ordinary angle restraint opposed
that opening. At the written endpoint, projecting the native forces along
the angle showed counterpressure from the C3′–C2′ bond and the adenine plane
that includes C1′. Two finite-difference step sizes reproduced the chemical
gradient. This measures one direction in a coupled sugar and base.

A separate construction let the complete B:7 adenine and B:1 cytosine move
with the sugars. The original five pairing distances, two pair planes and
both crystal links stayed active. All six sugar stereocentres retained their
hand. Of 859 atoms, 822 stayed fixed in construction. The B:7 sugar-to-base
angle reached 115.1° against 114.3°. After five native cycles it returned to
122.5°, compared with 122.8° when the bases had stayed fixed in construction.
B:1 OP2–P–O5′ finished at 107.8° against 108°. A different B:1 sugar angle
finished 6.24 restraint widths from its target. The two crystal bonds were
1.625 and 1.624 Å. The fixed mercury retained both N3 contacts at 1.995 and
2.021 Å. Neither fit introduced a non-neighbour contact within 2.2 Å around
these 37 atoms. The original 1,092 working and 59 free observations and
experimental phase coefficients matched exactly.

In the two endpoints R-free was 0.3367 and 0.3314. Native weight
optimization used free-set scores. The common supplied-phase and 37-atom
omit maps gave small opposite differences (−0.09 and +0.05 map standard
deviations respectively, released minus anchored). The data extend to
5.06 Å. Keep both shapes for review. Preserve the native sugar and base
targets. The matched weight comparison follows below. The independent PDU
fixed-weight comparison is documented above.

**C580, can the sugar angle survive refinement?** Both starting models were
fitted for five cycles with a common coordinate weight of 1, taken from the
earlier PDU control, and again at 12, within the 11–14 range used by the
ordinary FT fit. Between these two controls only the relative reciprocal
coordinate weight changed. Both used the original observations, flags,
phase coefficients, metal scattering, base-pair and crystal-bond restraints.
The native coordinate minimizer confirmed the requested weight at every
evaluation. The 42 DNA groups continued to refine their displacement factors.

| B:7 C2′–C1′–N9, target 114.3° ± 1.4° | Built | Standard Phenix | Fixed 12 | Fixed 1 |
| --- | ---: | ---: | ---: | ---: |
| Bases held during construction | 119.1° | 122.8° | 122.9° | 118.3° |
| Bases free during construction | 115.1° | 122.5° | 121.4° | 116.8° |

At weight 1 the bases-free model kept both crystal bonds at 1.61–1.62 Å,
and its two base pairs had plane differences of 2.8° and 3.8°. Both Hg–N3
distances were 2.08–2.09 Å. All six sugar stereocentres kept their hand.
None of the 1,319 checked within-residue angles exceeded four restraint
widths, compared with twelve at weight 12. R-work/R-free increased from
0.3081/0.3328 to 0.3282/0.3400. This establishes sensitivity to the
diffraction weight at 5.06 Å. It leaves the choice of conformation open.
The two-scaffold experiment below keeps the working diffraction weight.

**C581, keeping diffraction weight and changing one local angle.** The FT–Hg
test used the same built coordinates, experimental phases, fixed Hg and
working coordinate weight of 12 as C580. The only chemical change halved the
B:7 sugar-to-base angle width. A second test used the previously chosen
D:2–D:3 start on the PDU:PDU scaffold. Two fresh five-cycle fits used the
same global weights and differed only in the width of the D:7 sugar angle.
Both scaffolds descend from 5W6W and use different diffraction observations.

| After five Phenix cycles | Control | Local change | Original ideal and width | R-work / R-free, control → changed |
| --- | ---: | ---: | --- | --- |
| FT–Hg B:7 C2′–C1′–N9 | 121.41° | 116.60° | 114.3° ± 1.4° | 0.3081 / 0.3328 → 0.3077 / 0.3306 |
| PDU:PDU D:7 O3′–C3′–C2′ | 99.08° | 106.45° | 109.4° ± 2.5° | 0.2041 / 0.2762 → 0.2041 / 0.2740 |

The FT sugar moved from 5.08 to 1.64 original widths from its target. The
PDU sugar moved from 4.13 to 1.18. Both fits kept the original free sets and
two registered crystal links. The FT Hg–N3 contacts stayed at 2.00 and
2.03 Å, and both sugar hands were retained at the PDU junction. The FT B:1
sugar still has an angle 5.81 widths from its target. On PDU the other
crystal bond, B:7→B:1, grew from 1.671 to 1.684 Å. The largest reported
local overlap at D:7 grew by 0.03 Å and the second PDU tip remained 0.67 Å
from its ring plane. Both small working-only map differences in FT were
under 0.02 map standard deviations and had opposite signs. These controls
justify checking the entire junction before retaining a local correction.
Transferable library widths and the crossover conformation remain open.

**C583, what happened to the five-membered rings.** The same four endpoints
gave 42 occupied, covalently closed sugar rings per fit. At FT–Hg B:7 (DA)
the local correction changed the phase from 126.7° to 128.6° and the amplitude
from 43.1° to 44.1°. At D:7 on the PDU scaffold the residue is **ordinary
thymidine**. Its phase changed from 3.7° to 6.4° while the amplitude fell from
20.8° to 15.0°. Tightening that angle flattened the sugar. The actual PDU
at B:4 retained a large amplitude, 65.1° and 64.0° in the two fits. These
are readings of written models. The diffraction evidence for choosing a
sugar conformation remains open. At low resolution a measured pucker alone
cannot establish the right reference for a new restraint.
[Measurement](cif-doctor.md#seeing-how-a-sugar-ring-changed) ·
[NA Valence Geometry Working Group](https://pmc.ncbi.nlm.nih.gov/articles/PMC12791123/).

**C584, comparing two crystal junctions with independent DNA ranges.**
The four C581 five-cycle models supplied two declared phosphodiesters each.
Each comparison measured 53 sugar, glycosidic and phosphate dimensions.
The two scaffolds use opposite crystal operations for the equivalent named
links. The measurements used each scaffold's own recorded operation.

| Change at fixed diffraction weight | Control | Local change | Published DNA outer interval |
| --- | ---: | ---: | --- |
| FT–Hg B:7 DA, N9–C1′–C2′ | 121.41° | 116.60° | 107.12–123.10° |
| PDU scaffold D:7 DT, C2′–C3′–O3′ | 99.08° | 106.45° | 101.17–120.02° |
| PDU scaffold B:7 O3′ to B:1 P | 1.671 Å | 1.684 Å | 1.539–1.640 Å |

The FT angle stayed inside the published interval even when it lay five
widths from the restraint Phenix used. The PDU scaffold's D:7 sugar angle
crossed into the interval as the ring flattened. Its other crystal bond was
already long and lengthened further. Four out of 53 terms around D:7 and
seven around B:7 fell outside the published ranges in the changed PDU model.
This comparison supplies an independent screen for canonical sugars beside
modified sites. Choosing a transferable correction still requires evidence
for the whole junction and its fit to diffraction.
[Reference and reading instructions](cif-doctor.md#inspecting-a-phosphate-at-a-crystal-boundary).

### How Phenix labels base-pair restraints in the PDU scaffold

**C585.** The two Watson–Crick pairs flanking PDU are A:11 DT with B:5 DA,
and A:13 DC with B:3 DG. Willow traced five inter-base rows labeled
`covale` in the native coordinate mmCIF. In the saved refinement, the
five rows came from the NARestraints hydrogen-bond distances. Both the
printed Phenix restraints and the actual source recipe were checked.

Five new five-cycle Phenix 2.2.1-6174 fits used the same start, displacement
model, PDU dictionaries, two registered crystal phosphates, 1,778
working and 124 held-out reflections. The original C581 local fit supplied
the matched control. Halving the five distance widths from 0.20 to 0.10 Å
while retaining the 2.80 Å targets brought the shortest contact from 1.816
to 2.032 Å. It remained compressed.

For a separate comparison we obtained the five atom-specific target lengths
and widths from Phenix. One fit supplied those values as distance edits.
The other supplied just the five native secondary-structure hydrogen bonds,
preserving the original pair angles and planes in both. All 7,924 initial
nonbonded contacts and their distance limits agreed. After refinement, all
862 written atom positions agreed to PDB precision. Both fits gave
R-work/R-free of 0.2078/0.2693. All five rows were `covale` for distance
edits and `hydrog` for native hydrogen bonds. This separates the chemical
meaning of the exported rows from the quality of the coordinates.

Changing just the working diffraction weight gave the following results.
Weight 4 was chosen as the integer nearest the geometric midpoint of 1 and
12. The test set was kept out of the weight choice.

| Weight | A:11 O4···B:5 N6 | B:7 O3′···B:1 P | B:4 PDU tip to ring plane | R-work / R-free |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 2.352 Å | 1.683 Å | 0.590 Å | 0.2078 / 0.2693 |
| 4 | 2.564 Å | 1.627 Å | 0.009 Å | 0.2287 / 0.2873 |
| 1 | 2.711 Å | 1.609 Å | 0.028 Å | 0.2554 / 0.3125 |

At weights 4 and 1, all 53 independently referenced dimensions at each
crystal junction lay within the published outer ranges. At weight 4 the
A:13 O2···B:3 N2 contact remained short at 2.447 Å. The second crystal
phosphodiester measured 1.609 Å. Both PDU tips approached their ring planes.
The better geometry costs 0.0209 in R-work relative to weight 12. This leaves
the uniform weight and the whole-arm correction open.

For the earlier C581 sugar-width comparison, rebuilding its two fixed
19-atom omit maps reproduced the archived parent and starting-position
samples. Both maps excluded all 124 test reflections. At 4.19 Å, changing
the D:7 sugar width shifted the mean sampled density over the 19 omitted
atoms by less than 0.003 map standard deviations in every map and solvent
comparison. The density gives little leverage between these two sugar fits.
These omit comparisons concern the original C581 siblings.

### How far local restraints carry the PDU arms at the original diffraction weight

C586 kept the working diffraction weight at 12. It reused C585's atom-specific
hydrogen-bond targets and strengthened only the five contacts flanking PDU by
a factor of three. A second comparison transferred the C470 soft plane to
each PDU, using the six ring atoms and the terminal carbon from its dictionary
graph at a width of 0.10 Å. The three new five-cycle fits and the saved
reference have identical starting coordinates and the same 1,778 working
and 124 held-out reflections. The starting native geometry tables differ only
in the declared contacts or planes. All 7,924 nonbonded contacts are shared.

| Local treatment | A:11 O4···B:5 N6 (Å) | B:4 tip above ring (Å) | B:7 O3′···B:1 P (Å) | R-work |
| --- | ---: | ---: | ---: | ---: |
| Reference | 2.352 | 0.590 | 1.683 | 0.2078 |
| Five stronger contacts | 2.705 | 0.543 | 1.672 | 0.2026 |
| Two extra arm planes | 2.360 | 0.419 | 1.660 | 0.2077 |
| Both changes | 2.703 | 0.510 | 1.683 | 0.2036 |

Four of the five contacts moved closer to their targets when strengthened.
The second crystal bond stayed between 1.612 and 1.627 Å in all four fits.
Combining the changes gave less improvement in the B:4 tip than the planes
alone. Phenix placed this tip only 0.061 Å from the seven-atom plane in the
plane-only fit, while the height above the six ring atoms was 0.419 Å.
Adding the tip lets the fitted plane tilt toward it. With the C587
inspection, leaving the tip out rotated the B:4 plane by 3.72° in the
plane-only fit and 4.53° with both changes. The corresponding A:12 rotations
were 0.41° and 0.80°. Across all four measured planes, the distances
recalculated from written coordinates agreed with the printed table to
within 0.001 Å. No tip plane was found in either control that omitted it.

The PDU dictionary matches C569's adjusted Cartesian template byte for byte.
It supplies a 1.431 Å C5–C5A target, a 1.470 Å C5B–C5M target and a base
plane containing C5A. This identifies the exact PDU input behind C581,
C585 and C586. The earlier C581 replay note described it as a legacy arm.
The two phosphates retained their image restraints and the terminal D:1
retained its eleven native terms in all new fits. Each fit remains unselected.

### When the B:4 tip left the ring plane

C588 observed the forces during the same two five-cycle fits that had the
extra planes. The Phenix 2.2.1-6174 working diffraction score used least
squares for cycles 1–2 and maximum likelihood for cycles 3–5. Its numerical
weight stayed at 12. The same 1,778 working reflections and 124 held-out
reflections appeared in the live target in every cycle.

| B:4 tip height above the six ring atoms (Å) | End of cycle 2 | End of cycle 3 | Final written model |
| --- | ---: | ---: | ---: |
| Two extra arm planes | 0.032 | 0.631 | 0.419 |
| The same planes and five stronger flanking contacts | 0.027 | 0.634 | 0.510 |

The first two columns use unrounded coordinates at the last gradient call
of the indicated cycle. Moving the six ring atoms changes their fitted
plane. The projection accounts for that movement as well as movement of
the terminal carbon. At B:4 the working diffraction term favored a smaller
height in all 109 evaluations during cycles 1–2 and a larger height in all
166 during cycles 3–5. The added plane favored flattening at all 275
evaluations. By the end of cycle five the rest of the chemical restraints
also favored flattening in both models. A:12 ended at 0.047 and 0.094 Å in
the written models.

Both replays reproduced the 862-atom coordinate file and final GEO from
their respective uninstrumented fits byte for byte. These are local changes
in the refinement score. The maps at 4.19 Å do not resolve an individual
terminal carbon reliably in this comparison. Atomic displacement, solvent
and scale estimates were also updated during refinement. To distinguish
their influence from the target switch, compare the two diffraction scores
on the same coordinates, displacement parameters and scale before changing
a restraint or selecting a model.

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
