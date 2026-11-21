# NASolve development handoff — current state

Updated **2026-11-21, C517 measuring the diffraction response to a flatter arm — Rowan**.
Active branch **cedar**, worktree **NASolve-c96**. Current scaffold B transfer is **`3dff6357`**.
Last standalone full-qualified runtime **`58965920`** passes
**12,043 tests and 293 subtests**, with two existing native opt-in skips, in
**3104.30 s**. All 1,417 tracked test-checkout files and exact NARestraints
`a9264f9e` remain unchanged; the test process group is absent. The verified
254 KB qualification archive retains exact results, commands and source bindings.
Linden completed the recorded 4.48 GB owned test-copy retirement on 19 November,
rechecking the archive and preserving scientific inputs, installations and shared NAR.
Focused, relocated installed, matched native and independent checks also pass.
Software qualification does not change the scientific REVIEW or close Q06.

## Where to resume

**All thirteen substitutions have now gone through one ordinary refinement.**
Phenix 2.2.1-6174 ran five cycles on the registered PostMR model using the
host reflections. At A:11, ATL's two backbone bonds went from 1.595/1.839
to 1.610/1.619 Å (target 1.607). Its two adenine contacts went from
3.318/3.301 to 2.971/2.873 Å (target 2.800). The four sugar stereocentres
and the receiving phosphate's oxygen order survived. The two remaining close
contacts overlap by 0.557 and 0.572 Å. ATL's B values span 185–441 Å².
The parent remains selected. Rwork/Rfree changed from 0.3346/0.2966 to
0.2670/0.2517. These host observations test the refinement machinery.

Phenix printed all 211 frame restraints and six protected D:1 angles.
Both models retained all 38 backbone links. All 2,273 measured intensities
and uncertainties and 3,236 Free-R assignments matched by Miller index.
The final PDU and 5PC terminal bonds measured 1.475 and 1.465 Å against
1.470 Å. Their tip heights above their six-atom rings were 0.189 and
0.434 Å. DF's C=S moved from 1.812 to 1.633 Å against 1.638 Å.
The nine-pair control has its registered diffraction result. The unfamiliar
eight-residue challenge and the independent symmetry-linked PDU:PDU gate
remain open. The compact ledger entry is
`registered_thirteen_change_diffraction_2026_11_21`.

**What survives another ordinary round.** Starting from that registered child,
five more Phenix 2.2.1-6174 cycles put the PDU and 5PC tips 0.105 and 0.254 Å
from their respective ring planes. Their terminal bonds measured 1.472 and
1.471 Å. ATL's two pair distances reached 2.859 and 2.819 Å. Its sugar
stereochemistry and phosphate oxygen order survived, with two overlaps of
0.528 and 0.586 Å still present. All 211 frame restraints, six protective
angles, 2,273 measured intensities with uncertainties and 3,236 original
Free-R flags were checked. These observations belong to the substituted host.
The matched sibling added one soft plane per arm at 0.10 Å. The final heights
were 0.076 Å for PDU and 0.189 Å for 5PC. Both terminal bonds remained close
to 1.470 Å. The two siblings started with the same full native coordinates
and could be distinguished by one additional input. In the independent B:4
5PC comparison, both refinements placed the tip within 0.09 Å of the ring while
the terminal bond stretched to about 1.55 Å. Keep this treatment experimental.
The operator can now read both measurements before and after refinement from
the existing `--refined-planes` assessment.

**Why the independent 5PC still needs review.** At B:4 the roughly 1.55 Å
terminal bond persisted with or without the extra plane. Phenix listed two
nonbonded contacts for the terminal methyl carbon in each endpoint. Even the
closer approach relative to its van der Waals distance had over 1.23 Å of
clearance. The source-verified glycosidic torsion changed by +1.8° and +2.4°
respectively. Local terminal crowding and a half-turn of the base do not
explain this control. The cause of the bond stretch remains open.

**How far the locked-sugar result transfers.** TLN passed all 21 isolated
Phenix dictionary checks. In the same ordinary thirteen-substitution card,
its base oxygen O4 moved 4.739 Å when fitted between the phosphates. For
9V9, O4 moved 3.852 Å. Cedar now reports the residue, site, atom, measured
motion and limit. In 27 starts per residue the existing routine found
13 fits below 2 Å for ATL and zero for TLN or 9V9. Changing the glycosidic
angle brought 9V9 down to 1.801 Å but left its pair contacts at 4.38/4.42 Å.
The three independently generated NARestraints files request 2.8 Å with
sigmas of 0.2 Å (ATL/TLN) or 0.4 Å (9V9). The measured starting host also
has long contacts. A fixed-neighbour fit that mimics that host cannot
establish a good pair. The prescribed-target control recovered the two
bond lengths but shifted the bases too far. No new pose qualified for
ordinary use. See `locked_sugar_transfer_geometry_2026_11_21`.

Three separate four-residue Phenix readings then checked whether the other
sugars' dictionaries actually produce the expected links. Each showed both
1.607(12) Å phosphate bonds, the corresponding eight flanking angles, and
the two requested NARestraints pair bonds. Both the ten covalent targets
and their sigmas agreed across ATL, TLN and 9V9. Phenix found every expected
heavy atom. This was a geometry reading using a 5 Å diagnostic allowance for
placement. TLN still needs a working pose. For 9V9, C500/C501 rebuilt the full
duplex and compared two starts in five Phenix cycles on the same host data.
Allowing the opposing adenine and its flanks to move during construction gave
final pairing distances of 3.201/3.176 Å. Moving only the substituted strand
gave 3.419/3.877 Å and a lower global Rfree (0.2418 versus 0.2505). Both
refinements preserved the sugar hands, all eight local phosphate oxygen orders,
the 211 frame terms and both central backbone bonds (1.608/1.615 Å). Each
retained four close contacts, with central B values above 190 Å². This shows
how placement affects local pairing under unchanged restraints. Both tests
used separate diagnostic parents. The ordinary placement guard remains at 2 Å.
See `locked_sugar_paired_pose_diffraction_2026_11_21` in the native evidence ledger.

The changed diagnostic passed 72 focused tests across furanose construction,
PostMR lineage and explicit mutation targets. Both atom-naming regressions
failed on the previous wording and passed on the relocated install, where
all 320 package source files matched. Use
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_cif_furanose_bridge.py tests/test_postmr_furanose_lineage.py tests/test_postmr_explicit_targets.py`.
There is no record migration. The full suite was deferred.

**The mutation card can now supply the locked-sugar chemistry.** On a fresh
Phaser run, the ordinary site option found ATL, its DT host at A:11 and the
NARestraints workbook. Phenix 2.2.1-6174 qualified the new dictionary on
all 21 isolated checks. The second request reused the same entry without
eLBOW or another native qualification. The resulting thirteen-change PDB
matched the explicit-source construction byte for byte.

**Publishing the result exposed a separate bug.** The original publisher
tried to plan ATL a second time as ordinary DNA after the chemistry had
completed. The corrected publisher checks the current mutation card against
the verified source-bound construction. It also recovers explicitly chosen
deoxy temporary parents from the retained chemical source. Changed card
targets, sites and mirrored intent still fail. The original thirteen-component
request completed and preserved its independent parent selection. ReadySet
changed atom-name spacing in eight of 211 ordered requests. Rechecking its
two native captures with the existing named-atom comparison passed all 28
endpoint checks. The separate comparison leaves the recorded selection intact.
The frozen request, cold and warm receipts and compact measurements are in
`site_only_locked_sugar_and_publication_2026_11_21` in the evidence ledger.

The saved thirteen-change attempt registered as the `postmr` review checkpoint
without repeating Coot, eLBOW, ReadySet or Phenix. Removing OXT's leaving-group
flag from a disposable copy after planning stopped acquisition before it could
create a cache entry. The relocated install matched 320 package source files.
The initial site/caller group passed 143 focused checks. The final publication,
source and named-request group passed 194. A relocated install passed another
104 on publication, construction, source selection and CLI forwarding. The
full regression was deferred. The existing record schemas and older selections
can be read without migration. Only compact measurements are tracked.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_postmr_furanose_lineage.py tests/test_cif_ordinary_construction.py tests/test_cif_postmr_publication.py tests/test_postmr_explicit_targets.py tests/test_cif_named_custom_requests.py tests/test_cif_named_custom_execution.py
```

**Ordinary construction, C494.** Fresh molecular replacement, Coot 1.3.3 and
NARestraints 1.1.3 produced all thirteen substitutions in one PostMR run.
Coot handled twelve. The source-qualified route read ATL's base anchors from
the workbook, kept nine matched base B values and removed OXT at A:11. All
869 atoms matched the separate C493 seed in coordinates, occupancy, element
and B. A relocated install reopened the 40 construction files (1,267,441
bytes) after the first checkout disappeared. Native dictionary checking
confirmed four plane changes and both PDU/5PC bond corrections. C496 records
the endpoint selection and C497 records the registered diffraction child.
The first attempt stopped at a macOS temporary-directory alias after Coot.
The second ran on its own numbered MR lineage.

Focused checks used `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m
pytest -q -p no:cacheprovider` on the furanose lineage, explicit targets, base
anchors, stored furanose, canonical/site/projection lineage, PostMR construction,
ordinary construction, ordinary PostMR and complete request tests (326 passed).
The changed-source refusal and both ordinary preparation files then passed all
29 checks. The full regression was deferred. Existing explicit records retain
their version 1 envelope. Native models and diffraction files stay in the
numbered run. The compact measurements are in the scientific evidence ledger.

**ATL on the selected twelve-change scaffold, C493.** The simpler seed used the
currently qualified dictionary without first shifting either neighbour. Its 869
atoms had the same starting occupancies, B values and elements as C488. After
five Phenix 2.2.1-6174 cycles its junctions measured 1.612 and 1.603 Å, and its
two adenine contacts measured 2.974 and 2.874 Å. All four sugar centres and the
original Free-R assignments survived. The two remaining overlaps measured
0.561 and 0.574 Å. Rfree rose from 0.2439 in C488 to 0.2514 here. This supports
testing the simpler construction in ordinary PostMR. The thirteenth substitution
in C493 was built separately from the selected twelve-change checkpoint.

**9V9 dictionary recovery.** Phenix printed all 40 source bonds plus one
5.061 Å O4′–C4 bond. The new acquisition follows that exact stopped attempt
into a fresh request. Only the order of the reader's atom rows changes.
All 21 isolated checks passed against the original native source. The ordinary
retained-dictionary route then reused exactly those results. The historical
failure occupies 611,151 bytes; the new request links it with 895 bytes.
The relocated installed program reopened both results and the failure.

**9V9 in the helix.** At five weights, fitting the phosphate arm moved the
base 2.07–3.85 Å. Giving it the measured host glycosidic angle first moved it
2.46–4.63 Å. All ten trials exceed the established 2 Å limit. 9V9 matches
the host at all three corresponding sugar-hand checks, whereas ATL matches
only at C1′. A sugar-aligned 9V9 still leaves its two junctions 3.33 and
4.23 Å apart. Sugar hand alone cannot pick a working pose. Q11 still needs a
qualified placement and both native links. Q07 still needs ordinary ATL
mutation followed through registered refinement. Compact evidence is under
`heldout_native_bond_recovery_and_reference_frames_2026_11_21`.

**Building ATL on the selected parent, C486–C488.** Cedar now reads both
backbone neighbours at A:11 and the departing oxygen directly from the
ordinary model, its phosphate intent and the source dictionary. DG A:10
supplies O3′, DZ A:12 supplies P and ATL loses OXT. On the earlier Coot
model the installed program reproduced the hand-declared placement and seed
byte for byte. On the selected twelve-change PostMR parent, the same atom
positions carried 110 different B values at ten surrounding residues. The
older mixed control had inherited historical resets at those sites.

Keeping the measured host B values gave ATL junctions of 1.611 and 1.604 Å
after five Phenix cycles. Its two contacts to adenine were 2.708 and 2.969 Å.
The four sugar stereocentres survived. Three overlaps exceeded 0.4 Å and the
outgoing O3′–P–OP2 angle was 112.4° against 108°. Rwork/Rfree finished at
0.2632/0.2439 on the original host reflections. An independent run using the
local median B for the thirteen new sugar/phosphate atoms also left three
overlaps. Keep the measured host B values and leave the median experimental.
C488 used a separate construction for the thirteenth substitution. C494–C497
subsequently exercised the ordinary mutation and its registered refinement.

**Held-out locked sugar, C489.** For 9V9, raw eLBOW and Cedar's ordinary
dictionary acquisition both failed on a 5.06 Å O4′–C4 bond absent from the
source. Reusing C116's connected atom ordering preserved all 38 atom identities
and 40 source bonds. The resulting isolated dictionary passed all 21 Phenix
checks. Base placement kept all four sugar hands and removed OP3. Its two
backbone distances started at 3.728 and 3.535 Å. The first bridge fit exceeded
the existing 2 Å base-movement limit. Q11 still needs a connected native
reading and Q07 retains its ordinary ATL gate.

The C486–C489 change is confined to the whole-furanose Python placement
reader/writer, its focused test and these documents. The new placement policy
uses the existing version 1 envelope. Historical explicit-context records
replay without migration. The five placement, bridge, model-context and
reaction test files passed all 178 checks; a relocated installed wheel
reproduced the control with the old code paths inaccessible. Raw models,
diffraction files and Phenix logs stay in the local checkout. The compact
ledger records the exact test command, source and result fingerprints under
`ordinary_locked_placement_host_displacement_and_heldout_generation_2026_11_21`.

**PDU with equal weights, C484.** On the independent A:PDU scaffold, two
five-cycle Phenix children used the same parent, random seed, original
observations and fixed coordinate weight of 1 in every cycle. The extra
0.10 Å plane reduced the tip height above the six ring atoms from 0.466 to
0.304 Å. The terminal bond was 1.475 and 1.476 Å. The two alkyne angles
changed from 173.5°/177.1° to 175.4°/178.1°. Rfree was 0.2501 and 0.2500.
The earlier adaptive pair gave 0.175 and 0.231 Å. Keep the plane experimental.
Both fixed-weight children preserved all original Free-R flags, the three
sugar hands, the 196 frame terms and six protected phosphate angles.

C485 also corrected the reported starting Rwork/Rfree. The mixed ATL log
first printed 0.5307/0.7513 before scaling. Phenix published 0.3439/0.3059
as its start and 0.2492/0.2345 as its final pair. New round reports use that
explicit recap and retain the preceding scaling observations in the history.
Nine saved native logs independently reproduced their printed endpoints.

**Mixed scaffold with ATL, C481–C483.** A separately built 42-residue model
carried all thirteen substitutions through ReadySet and five Phenix 2.2.1-6174
cycles on the host reflections. Both ATL backbone links finished at 1.610 and
1.606 Å (target 1.607 Å). The two contacts to adenine finished at 2.735 and
2.991 Å (target 2.8 Å). The outgoing O3′–P–OP2 angle went from 106.2° to
112.5° (target 108°). All four sugar stereocentres and the order of the two
labelled nonbridging phosphate oxygens survived. Contacts around ATL with more
than 0.4 Å overlap fell from four to two. Phenix printed all 211 requested
frame terms and six separately protected D:1 angles. The output retained
all 2,273 measured intensities and sigmas and all 3,236 original Free-R flags.
Rwork/Rfree finished at 0.2492/0.2345. These are host-data software controls.
Next connect the ordinary mutation request to the source-bound locked-sugar
builder and keep the separately constructed model as its comparison.

**Ordinary mixed refinement, C461/C466.** Twelve substitutions went from Coot
1.3.3 and ReadySet through a registered parent and five Phenix 2.2.1-6174
cycles. A:11 retained DT. The two terminal carbon bonds ended at 1.476 Å (PDU)
and 1.465 Å (5PC) against 1.470 Å. DF C=S shortened from 1.812 to 1.632 Å
against 1.638 Å. The final manager carried all 211 W-frame terms and six
terminal-phosphate angles. PDU’s terminal carbon moved from 0.095 to 0.171 Å
from its ring plane. The 5PC carbon moved from 0.710 to 0.382 Å. The child received
REVIEW with Rwork/Rfree 0.2667/0.2612. The parent stays selected. The host
observations serve as a restraint-delivery challenge. Q06 remains open on
whole-arm geometry.

**Matched arm-shape test, C470/C474.** A ring with a source-declared triple-bond
arm and two native 180° targets supplies the trial geometry. At D:5 PDU and
A:4 5PC, adding a seven-atom plane with a 0.10 Å width reduced tip distances
to 0.123 and 0.285 Å after five cycles. The terminal bonds were 1.478 and
1.461 Å. All 36 measured stereocentres retained their hand and both runs printed
Rwork/Rfree 0.2667/0.2612. The parent remains selected.
At the G:5PC pair at B:4, the ordinary control put the tip close to its ring.
Its distance changed from 0.087 to 0.079 Å. The long terminal bond changed
from 1.549 to 1.548 Å against 1.470(27) Å. Both experiments used
the same substituted-host reflections. In the mixed scaffold, the drop in 5PC
tip height was 0.097 Å. Movement of the tip accounted for 0.052 Å along the
plane normal, movement of the ring centre for 0.011 Å and ring tilt for 0.034 Å.
The soft plane remains an experimental option.

C475 tested the same plane independently at B:4 in the ordinary A:PDU control.
After five cycles its tip-to-ring distance was 0.175 Å with the original restraints
and 0.231 Å with the added plane. Its terminal bond measured 1.500 and
1.475 Å respectively against 1.470(20) Å. Chi was -112.6° and -111.6°.
Rfree rose from 0.2265 to 0.2414. Here the terminal bond approached its
target as the arm departed farther from the ring. Keep the plane experimental.
The original 196 frame restraints, six phosphate angles and Free-R assignments
survived. This control explicitly has a free hydroxyl at B:1. The historical
PDU:PDU construct has an incoming phosphate at B:1 through symmetry and
requires its own declared partner and a qualified native link. C476/C477
reopened all six final models. At independent A:PDU the tip was 0.036 Å
from the seven-atom fit and 0.231 Å from the ring alone. Phenix chose final
coordinate weights of 10.000 and 1.517. Treat the runs as comparisons of
complete refinements. The mixed-scaffold weights were 0.957 and 0.951.

**Locked sugar and starting displacement, C463–C467.** The complete dictionary
request now carries its workbook and both explicitly reacting sugar ends. The
separately placed 13-component model preserved all 869 positions, 38 backbone
links, 152 neighboring angles and 211 frame terms through ReadySet. Nine ATL
atom-name fields changed PDB spacing. The historical strict reader finds
eight unequal display-label rows and retains the checked parent. The first
attempt stopped at publication. C467 reopened its sealed evidence after
relocation, within the unchanged 128 MiB allowance, with all 26 dictionaries
and 17 parameter files. A fresh complete C468 request returned that same
fallback under its recorded comparison. C471/W181 separately selected the
actual ReadySet output by checking the ordered atoms and tolerating ordinary
PDB atom-name spaces. After relocation all 14 endpoint CIF files and 17
parameter files matched the final native inputs, in order. The earlier
selection remained readable alongside it. C473 also restored three missing
ligand source records in the installed package.

A separate optional construction seed transfers B factors only for a fully
matched base. Nine thymine atoms could inherit their host values. The other
13 ATL atoms kept B=20. At fixed coordinates, direct Phenix calculation on
2,146 working reflections gave 52.7% of the original RMS amplitude from those
nine atoms. The outgoing O3′–P still starts at 1.839 Å. Ordinary ATL placement,
calibration of new sugar-atom B values and ordinary 13-component delivery remain open.
C472 moved the intact locked sugar while holding its neighbours fixed. The
links shortened but the pair opened. C478–C479 then allowed rigid movement
of both neighbours. The outgoing O3′–P–OP2 angle reached 82.8° against
108°. One extra rotation about the receiving O5′–P single bond brought it
to 106.2°. Both central links ended within 0.004 Å of 1.607 Å. Fresh
crystal-image searches found four contacts around ATL with more than 0.4 Å
of overlap, down from six at the start. C480 serialized this candidate with
the nine measured base B factors and repeated the full Phenix reading. All
869 atoms, 42 monomers, 211 frame terms and eight restraint categories were
preserved. C483 above measures what survived diffraction in that construction.

**Shared reader settings, W186.** The explicit typed-input handoff now carries
reviewed controls through ordinary PostMR/complete-request intake, acquisition,
stored preparation and the existing native transport. Geometry PHILs keep their
own context. Captured NCS=False suppresses the duplicate generated setting;
conflicts refuse. Historical/default requests remain unchanged. All **558 focused
source checks** pass. Relocated installed checks pass as **546 + 12**: the latter
needed six already-packaged CIFs restored to the existing test fixture layout.
The wheel's build source and original installation directory were removed.
One fixed-coordinate Phenix 2.2.1-6174 read retains **859 atoms, 42 monomers and
213 terms**, with each reader control supplied once and all four effectively
False. No motion, refinement or real ordinary-parent ancestry is claimed.
This implementation reached Cedar in `04d506c5`.
Next trace the existing canonical PostMR/checkpoint writer without changing the
nonempty dictionary-acquisition contract. See the [API and remaining gates](cif-doctor.md#explicit-captured-control-handoff-w186)
and evidence `captured_reader_control_handoff_2026_11_21`. No full suite in this
explicitly scoped push; the earlier full baseline above is not a new release pass.

**DY ring geometry, C456.** The triazole favors the plane of the pyrimidine.
A soft shared plane recovered both twisted starts in five Phenix cycles.
The original scaffold also had an unintended covalent bond between the bases.
The original native topology check identified it. C502 now reads the bonds in
the selected refinement checkpoint. In the archived DY final geometry it reports
the extra A:12 DA N6–B:4 DY C5T bond at 1.436 Å with a 1.430(10) Å target.
In the registered ATL mixed child all 38 backbone links and 53 supplied
distances match the checked preparation. C503 reads both tables from the same
round and binds the initial table to its entrance model. The archived DY control
required two exact atom-pair exclusions. Five cycles retained the 38 backbone
links and put adenine N6 at 2.913 Å from C5T and 3.104 Å from N4T.
Ordinary checked refinement now records both bond tables. The open questions
are explicit authority to exclude additional links and the triazole edge facing adenine. The [DY queue
entry](cif-doctor-completion-queue.md#dy--packaged-retained-triazole-reference-and-mutation-support)
records the separate chemistry milestone.

C502 adds the optional `refined_links` assessment field. Existing checkpoint
schemas and native inputs need no migration. The public CLI reopened the exact
registered child. Its dictionary verdict stayed at REVIEW, and its bond verdict
was MATCH. Source validation passed 187 tests and 7 subtests with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_refinement_link_geometry.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py tests/test_cif_printed_parallelity.py tests/test_cif_topology_gate.py tests/test_cif_restraint_context.py`.
The first three modules passed 41 tests and 7 subtests on the relocated install.
All 321 packaged source and data files matched. The DY and ATL checks read
existing Phenix 2.2.1-6174 results. The commit carries code, synthetic tests
and documentation. Full regression remains deferred for the branch.

C503 adds `preflight_links` to the requested Doctor assessment. Historical
rounds without a recorded isolated preflight return null for this field.
The registered ATL child had 38 backbone and 53 intentional distances at
both stages. Its dictionary stayed at REVIEW. One separate DY experiment
completed native preflight and five cycles with Phenix 2.2.1-6174. All 2,273
intensities with uncertainties and 3,236 Free-R assignments matched by HKL.
The compact evidence is under
`dy_two_atom_pair_exclusions_2026_11_21` in the native register.
With the existing Gemmi 0.7.5 topology extra on the Python path,
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_refinement_link_geometry.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py tests/test_refinement_parallelity.py tests/test_refinement_declared_sites.py`
passed 138 tests and 7 subtests. The first three modules passed 42 tests and
7 subtests from the relocated wheel. All 321 packaged files matched source.

**D:1 terminal phosphate, C504.** Phenix printed the O5′–P–OP3 angle as the
last angle before the first dihedral. AutoRefine had counted the dihedral's
atoms in that row and reported ten of eleven expected restraints. The reader
now checks four P–O bonds, six O–P–O angles and the P–O5′–C5′ angle by atom
identity. A repeated angle with reversed endpoints cannot replace a missing
one. A bond to a different crystal image cannot satisfy a local bond.
The starting DY phosphate genuinely warrants review at 7.69σ. All eleven
terms are present after refinement. The largest deviations were 1.84σ in
the original control, 2.12σ with the two excluded interbase bonds, and 1.75σ
in the registered mixed scaffold. These are fresh reads of the saved Phenix
2.2.1-6174 tables. The separate B:1 symmetry-linked phosphate has a different
declared end state. Historical checkpoints retain their original reports.
With `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_autorefine.py tests/test_refine_doctor.py tests/test_phosphate.py tests/test_refinement_inputs.py`,
87 tests and 48 subtests passed. The first two modules passed 48 tests and
38 subtests on the relocated wheel. All 321 packaged source and data files
matched. Only synthetic fixtures, code and the compact findings are tracked.

**C505 background readback.** Previously an operator had to ask for the
cross-residue bond comparison. AutoRefine now records it when declared-site
observation is enabled on a checked preparation. Refine Doctor keeps a flagged
child out of numerical recommendation. The read-only bond assessment
reproduces its recorded decision. Both tables in the mixed continuation
matched 38 backbone bonds and 53 supplied distances. The child remained usable
for review and the selected checkpoint stayed at PostMR. Older rounds need
no migration. The additive metric and acceptance flag are described in
[CIF Doctor](cif-doctor.md). The code is in `autorefine`, `refine_doctor`,
`refinement_link_geometry`, `cif_doctor_run` and the CLI. The source check used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_refinement_link_geometry.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py tests/test_refinement_parallelity.py tests/test_refinement_declared_sites.py tests/test_refine_doctor.py tests/test_autorefine.py`.
191 tests and 45 subtests passed. The first three modules passed 47 tests
and 7 subtests from the relocated wheel. All 321 packaged files matched.
Full regression remains deferred. The ledger entry
`mixed_scaffold_second_ordinary_round_2026_11_21` retains the scientific
fingerprints. Synthetic tests and compact observations accompany the change.

**C506 validation.** One additional sibling completed Phenix 2.2.1-6174
preflight and five real cycles. Its native table contained the original 211
frame restraints, six protective angles and the two extra planes. All 3,236
original flags and 2,273 intensities with uncertainties matched by Miller
index. The read-only assessment also reopened four finished checkpoints,
including the independent B:4 controls. The new optional comparison in
`refinement_plane_departures`, `refinement_parallelity`, the run assessor
and CLI needs no checkpoint migration. The existing Python reader retains
its prior output when the comparison is omitted. The focused command was
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_refinement_plane_departures.py tests/test_refinement_parallelity.py tests/test_refinement_declared_sites.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py tests/test_refinement_link_geometry.py`.
178 tests and 7 subtests passed. The plane, run-assessment and CLI modules
passed 60 tests and 7 subtests from the relocated wheel. All 321 package
files matched. Only the compact measurements, code, synthetic checks and
documentation are tracked. Full regression remains deferred.

**C507, between Cedar and Willow.** Both branches can now read atoms before
Phenix builds restraints and read those restraints after a bend moves the
atoms. The live geometry reader in `cif_native_validation` binds selections
to the original interpretation and checks the current native indices. It uses
the same atom and restraint readers as the existing sealed standalone worker.
On Willow's W200 compiled scaffold, 205 of 859 atoms moved by more than
0.002 Å, up to 0.400 Å. Each complete live view agreed with the earlier
diagnostic on the same manager. All 1,011 bond rows, 1,558 angle rows, 213
explicit requests, 38 backbone links and 51 supplied soft distances also
agreed with the saved compiled-stack observations at each end. This was a
Phenix 2.2.1-6174 geometry preparation with zero refinement cycles. W180's
original restraints and Willow's four-control candidate need separate evidence.

The additive Python API requires no checkpoint migration. The isolated worker
keeps SHA-256 `9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78`.
The focused command was `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_cif_native_validation.py tests/test_cif_topology_gate.py tests/test_cif_attachment_native.py tests/test_cif_native_atom_mapping.py`.
All 170 passed. The relocated install passed 114 across the native validation,
topology and atom mapping modules. All 321 packaged files matched. The Phenix
comparison uses `phenix.python -B c507_live_geometry_compare.py W200_HANDOFF RELOCATED_INSTALL NEW_JSON`.
The local checkout retains the runner, compact result and input fingerprints.
Only code, synthetic tests and documentation accompany this change.

**C508 validation.** The existing run assessor now accepts repeatable
`--contacts-at` selections. The public reader shares fixed-column model
identity with the bond reader, verifies every section count and preserves
both atom ordering and the printed operator. Four completed checkpoints
were read at both phases without starting Phenix. On the mixed model the
signed PDU tip overlaps finished at 0.091/0.125 Å (ordinary/extra plane).
At D:1, 18 initial and 19 final crystal-image witnesses per sibling reproduced
the printed distances within 0.0014 Å using the declared cell and space
group. These readings add no restraint or chemical-selection rule.
The focused test modules were `test_refinement_link_geometry`,
`test_cif_doctor_run`, `test_cif_doctor_cli`, `test_refinement_parallelity`
and `test_refinement_declared_sites`, using
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider`.
152 tests and 7 subtests passed. The first three modules passed 56 tests and
7 subtests from the relocated wheel and all 322 packaged files matched.
Reproduce the compact measurements with `c508_local_contacts.py WORK CEDAR_HISTORY NEW_JSON`.
Historical checkpoints need no migration. Only the reader, tests and
documentation are tracked.

**C509, preparing the pre-bend restraints.** An outer worker can create
`cif_native_parent.load_native_parent_service()` before its model hook and
call `interpret(model, bound_inputs, expected_report_sha256=..., process_options=...)`.
The expected digest comes from the original W203 compiler report. The service
returns the native result, the actual interpretation and a compact receipt.
It verifies the geometric PHIL parameters at full precision, all four False
reader controls and ownership of the pending Phenix call. It restores its
own service binding on exit. An outer worker discards any failed manager.
Scope is a PDB parent, the reviewed geometric inputs and Phenix 2.2.1-6174.
Checkpoint formats and ordinary refinement keep their existing behavior.

One installed geometry preparation on the 859-atom W202 scaffold gave all
1,011 bond rows, 1,558 angle rows and 213 compiled requests from the saved
parent. The largest parent coordinate difference was 1.7 × 10⁻¹⁴ Å.
The incoming atom order differed, with 205 moved sites when matched by
identity. A changed report, a changed NCS setting and a 10⁻⁹ Å change to
one target each refused before interpretation. This comparison ran zero
refinement cycles. Source residue chemistry, coordinate transfer and
candidate diffraction have separate owners and checks.

From the local Cedar runners, use
`phenix.python -B c509_native_parent.py CEDAR_INSTALL WILLOW_PACKAGE W202_EXPERIMENT NEW_JSON`.
The saved 2.7 kB receipt records the exact inputs. The branch carries the
service, synthetic tests and documentation. Focused validation used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_cif_native_parent.py tests/test_cif_native_validation.py tests/test_cif_reader_control_handoff.py tests/test_cif_complete_request.py`.
The source run passed 208 before seven additional edge cases; all 27 final
service cases passed. The relocated wheel passed all 215, and all 323
packaged files matched source. Full regression remains deferred.

**C510, checking the actual residue dictionaries.** Passing the original
typed `native/native_validation.json` bytes as `source_native_json` to
C509 observes each effective monomer before Phenix reduces it to a summary.
The service checks the summary identities on that same manager and reuses
the existing dictionary and restraint comparison. Only compact fingerprints,
counts and any changed-site examples persist. This optional check requires
the reviewed native interpreter and an available thread profiling hook.
Existing callers and checkpoint formats require no migration.

On the 42-residue canonical control, all original per-site definitions and
3,451 retained restraints matched. NARestraints supplied 51 pair distances,
84 angles and 58 plane relationships. This explains the change from 41 to 51
pair distances and from 82 to 84 angles. The native dictionary interface
could not read all formal charges. In a negative control, changing only
the thymidine C1′–N1 target from 1.468 to 1.508 Å changed nine bond targets
and nine C1′ chiral-volume targets. At A:9 the latter changed from 2.4315
to 2.4977 Å³, with its sign preserved. The unmodified supplied dictionary
matched the ordinary parent. Each case used one Phenix 2.2.1-6174 geometry
interpretation and zero refinement cycles. Modified/metal motion, scattering
and diffraction qualification have separate evidence requirements.

Reopen `branch-artifacts/cedar/c510-native-source-chemistry/science.json`
or run `phenix.python -B c510_native_source_comparison.py CEDAR_INSTALL WILLOW_PACKAGE W202_EXPERIMENT NEW_JSON`
from the local runner shelf. The focused commands use
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$GEMMI_PATH python -B -m pytest -q -p no:cacheprovider tests/test_cif_native_parent_chemistry.py tests/test_cif_native_parent.py tests/test_cif_na_policy.py tests/test_cif_native_validation.py tests/test_cif_topology_gate.py`.
All 122 passed in source and again after wheel relocation. All 324 packaged
files matched; full regression remains deferred. The shared historical
standalone reader keeps its original bytes.

C512 fixes a false refusal when the refinement worker is also recording a
selected residue. Create the parent service before either observer is
installed. The usual A:9 reader then returned its 20 DT heavy atoms, 21 local
covalent bonds and four chiral restraints during the same Phenix interpretation
that checked all 42 residues and 3,451 retained terms. The ordinary and
explicit unmodified dictionaries agreed. Changing the thymidine attachment
still identified the same nine sites. Both observers released their own hooks.
The underlying selected-site reader and stored checkpoint formats are unchanged.
Two regressions failed on C510. The source and relocated package each passed
72 focused tests and three actual Phenix 2.2.1-6174 geometry interpretations
with zero refinement cycles. All 324 package files matched. Repeat with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_cif_native_parent.py tests/test_cif_native_parent_chemistry.py tests/test_cif_na_policy.py tests/test_cif_refinement_sites.py`
and `phenix.python -B c512_joint_observers.py CEDAR_INSTALL WILLOW_PACKAGE W202_EXPERIMENT C510_RUNNER NEW_JSON`.
The compact record is `branch-artifacts/cedar/c512-joint-observation/science.json`.

**C516, connecting Willow's preparation to Phenix.** The shared
`cif_native_parent_entry.native_parent_entry` now calls the admitted candidate
reader after Phenix builds its diffraction model. During finalization it hands
that same manager to the qualified Willow builder exactly once. The closed
coordinate mapping must identify the original motion and the closed chemistry
builder must identify the same manager. Only then does Phenix receive its
native result. The trusted worker owns both callbacks and the input lifetime.
The source-bound builder and coordinate mapping must come from the same
installed Willow package. The outer worker discards the process after a failure.

An installed Phenix 2.2.1-6174 dry-run reproduced Willow W208's final native
model, restraints, candidate diffraction snapshots and all 42 source-defined
residues exactly. It kept 38 backbone links and 51 supplied distances while
transferring 205 moving atoms among 654 fixed atoms. A second dry-run stopped
at the deliberate error after parent interpretation, before any coordinate
transfer. Both restored the three entry bindings, the two observers, the
parent service and thread profiler. Both processes stopped. Neither ran a
refinement cycle. The ordinary request still needs distinct geometry-parent
and candidate roles, motion evidence and preflight admission before this
route can run automatically. Existing policies, workers and saved schemas
need no migration. Reuse the compact
`branch-artifacts/cedar/c516-source-parent-entry/science.json` and the two
runner scripts. The models and diffraction files stayed local.

The new module and its regression tests are `cif_native_parent_entry.py`
and `test_cif_native_parent_entry.py`. Source and relocated installation
each passed 138 focused tests. All 326 packaged files matched the source.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_cif_native_parent_entry.py tests/test_cif_native_parent.py tests/test_cif_native_parent_chemistry.py tests/test_refinement_parallelity.py
python -B c516_parent_entry.py W208_ATTEMPT INSTALLED_NASOLVE NEW_ATTEMPT PHENIX_ROOT
python -B c516_entry_review.py W208_ATTEMPT NEW_ATTEMPT NEW_OUTPUT.json
```

**Q07, 20 November.** Ordinary Coot and ReadySet now prepare 1AP:T and S6G:C
on the same substituted host. The plane screen follows the verified source chemistry.
All four screened 1AP carbons were already covered. Five Phenix cycles retained
both amino nitrogens in its 12-atom plane (0.00866 Å RMS). S6G was different.
Its 11-atom local plane excluded sulfur, while the 19-atom shared pair plane
included it. After five cycles sulfur lay 0.101 Å from the nine-atom ring.
The C=S bond finished at 1.558 Å against 1.598(24) Å. Both controls preserved
2,273 measured intensities and uncertainties and 3,236 Free-R assignments.
These are delivery and shape checks on substituted host reflections.

**Mixed scaffold.** The separately assembled model with all thirteen current
components gave the repaired PDU and 5PC terminal targets of 1.470 Å and DF
C=S of 1.638 Å. The first ordinary twelve-component preparation independently
reproduced the same covalent terms at those three sites, including 38 backbone
bonds and 152 flanking angles across the scaffold. Phenix received 211 frame
requests in each model. ATL used the separate locked-sugar adapter in the
thirteen-component model. The ordinary control retained the host DT there.
C454 found identical plane membership in both mixed models. At A:5 the 1AP
local plane included N2 and N6. Of the two, the shared plane with C:11
included N2 only. At C:9 the S6G local plane again omitted S6, and the shared
plane with A:7 included it. These are interpreted restraints before diffraction.

**C462.** The stored bundle now prepares the locked sugar on the independently
placed mixed model. Two fixed-coordinate Phenix 2.2.1-6174 interpretations
covered 869 atoms on 42 sites. The all-thirteen preparation retained 38
backbone links, 152 neighboring angles and 211 supplied frame terms. At A:11
Phenix read ATL as RNA with numerical group `non-polymer`. Its two declared
links consumed OXT/HXT and the outgoing alcohol H; all four recorded sugar
centres survived. The 13 unavailable formal-charge readings retain REVIEW.
The prepared manager matches the separately assembled control for those
backbone and frame terms. Ordinary locked-sugar coordinate
placement, displacement assignment and diffraction with ATL remain open.

**C458–C460.** An ordinary fresh Coot construction and Phenix 2.2.1-6174
ReadySet run completed the twelve substitutions with DT still at the separate
ATL site. The repaired parent and ReadySet output have the same positions,
occupancies and isotropic B values for all 867 atoms. Phenix retained 38
backbone links, 53 supplied inter-residue distances and all 211 frame terms.
PDU and 5PC have terminal bond targets of 1.470 Å. DF C=S starts at 1.812 Å
against its 1.638 Å target. C466 above records the subsequent twelve-change refinement.

The original attempt sealed its publication error after the native jobs
stopped. C460 reopened those inputs in separate bounded stages and independently
selected the checked ReadySet model. After relocation, all 13 dictionary and
16 parameter paths resolved with the old run inaccessible. This separate
diagnostic has no registered checkpoint. C461 subsequently registered its own fresh parent.

**C455.** Cedar selected all seven consecutive repairs together for the first
ordinary twelve-component mixture. Phenix 2.2.1-6174 passed the sampled restraint
gradient checks on its final repaired dictionaries at the unchanged coordinates.
The source, model, ordered dictionaries and Phenix settings were checked at
each transition. The compact diagnostic bundle reopened in a new location with
access to the original evidence disabled. The terminal PDU and 5PC targets
were both 1.470 Å and the DF thione target was 1.638 Å.

The original C450 attempt stopped with 1,600 paths and 235,160,056 logical
bytes of repair evidence. C455 used those saved stages and a separate fresh
derivative job. It published a standalone diagnostic bundle. The original
attempt remains exhausted. Its unfinished outer record still contains
144.6 MiB of distinct payloads. C457 read all 3,599 original files without
depending on a later published bundle. A controlled interruption with the new
owner sealed the partial work, then a fresh attempt finished without changing
the first. A live child still blocked retry. Separate lossless packs of the
sixteen real working stages and the remaining distinct working files together
required 52,347,778 bytes before outer archive metadata. This was a storage
rehearsal on saved files. C459 subsequently recovered all 3,599 original files from one 10,546,262-byte
archive while access to both the original and the later publication was blocked.
The temporary working view occupied 39,930,826 bytes. It preserved the stopped
repair and missing outer completion. The normal retirement and later readback
also passed on a separately completed test request.

A complete bond count on both saved native models found 38 backbone and 53
supplied inter-residue soft bonds, with no extra links. All 211 frame terms
were realized. These are fixed-coordinate observations. The C458–C460 paragraph above records
the subsequent ReadySet experiment and its scope. The existing register entry
`qualified_rings_and_mixed_repairs_2026_11_20` retains exact evidence, including
the independently qualified original with its 1.364 Å 5PC and 1.607 Å PDU targets.

Simon confirmed that OP3 is disposable at an incoming phosphodiester. The
C438–C439 charge-aware reaction preserves the original OP1 and OP2 orders at
same-ASU incoming links. Free ends and symmetry-linked sites retain their
separate declarations. Q06 still owns the PDU arm after diffraction refinement,
and Q07 retains the long outgoing ATL junction and the held-out eight-residue
challenge.

**20 November, Q06.** C437 followed the ordinary G:5PC control through five Phenix cycles after C433 restored the eleven measured host scaffold B factors. The 5PC terminal carbon finished 0.087 Å from the ring plane, while its terminal bond reached 1.549 Å against 1.470(27) Å. The original uniform starting values gave 0.130 Å and 1.460 Å. Inputs and Free-R flags matched. Retain the measured scaffold displacement and separately qualify a starting displacement for new base atoms. C433 publication reused the completed native attempt after an edit to worker source interrupted verification. Subsequent experiments use pinned per-job code. See `internal_phosphate_and_mixed_panel_2026_11_20` in the native evidence register.

**20 November, C423.** Nonmetal DF at A:19 opposite D:4 adenine completed
five ordinary Phenix cycles. The prepared sulfur bond was 1.812 Å, its native
target was 1.638 Å and the final distance was 1.637 Å. The sugar–base bond
finished at 1.514 Å against 1.499 Å. Both base-pair contacts, all three source
sugar hands, all 202 frame terms, D:1 protection and the original Free-R flags
survived. PostMR remains selected. This substituted-host test scopes nonmetal
DF:A. The separate Hg experiment has different inputs. The compact evidence
key is `nonmetal_df_ordinary_refinement_2026_11_20`.

**Q07, C424–C427.** Ordinary Coot construction now makes twelve substitutions
on the fresh scaffold. Its matcher turned the DP base by 179° and IMC by 41°.
A source-defined rotation on the isolated monomer restored the parent base
orientation to within 0.05° in both finished residues. Thirty other sites
kept their coordinates. DZ and CGY have a different sugar–base attachment
and remain outside this named-angle check. A relocated wheel reproduced both
native Coot models byte for byte.

A separate source-bound placement installed the locked ATL at A:11 while
keeping four sugar stereocentres and the other 41 sites. Phenix read all 869
atoms and applied 211 requested restraints on the fresh nine-pair model,
including ten shared planes. It supplied the two backbone bonds and all
eight flanking angles. The incoming and outgoing links start at 1.595 and
1.839 Å against 1.607 Å. The outgoing C3′–O3′–P angle starts at 141.55°
against 119.7°. ATL starts at B=20 Å² while its host atoms span 166–320 Å².
C430 transferred the current ordinary PDU, 5PC and DF definitions onto the
same 869 atoms, generating the linked-site modifications for their actual
positions. Phenix reproduced all 67 local bond targets, 94 angles, nine
chirality restraints, 96 torsions and three local planes from the individual
runs. The 38 backbone links and 211 frame restraints also survived. Ten
other component definitions in this native test are still historical.
C431 froze and independently reopened one pending dictionary request with
all thirteen current sources, all 38 links and all 211 frame terms. The
request uses the separately constructed nine-pair seed. Generation,
qualification of the full set and mixed diffraction refinement remain open.

**C428–C429/C511, starting B factors.** Of 132 sugar and phosphate atoms that
kept their host coordinates through twelve mutations, 110 acquired B=20 Å².
On a separate 5PC site the starting guanine base had one recorded B value.
Changing only 22 starting B values to their host-supported values changed
the RMS calculated amplitude by 10.26% of the original RMS amplitude across
2,146 work reflections. Five ordinary Phenix cycles gave the 5PC terminal
bond at 1.460 Å from the Coot start and 1.472 Å from the host-derived start
(target 1.470 Å). The terminal carbon lay 0.130 and 0.140 Å from the ring
plane. PostMR remains selected. Carry forward B values where the original
atom identity is established. A defensible rule for newly added atoms on a
nonuniform host remains open.

The fourth matched five-cycle Phenix 2.2.1-6174 refinement completes the crossed
comparison. With the base alone set to the original host-base value of 138.44 Å²
and the scaffold at 20 Å², the 5PC terminal bond was 1.443 Å and the tip lay
0.343 Å above its six ring atoms. The previously tested scaffold-only change
gave 1.549/0.087 Å, both changes gave 1.472/0.140 Å, and the original Coot
start gave 1.460/0.130 Å. All four began with the same coordinates.
The per-residue B refinement shifted every atom at this site by the same
amount within each experiment. For the new case the shift was +157.11 Å²,
so its initial base–scaffold difference survived. The complex starting model
structure factors from the two B changes add on all 2,146 work indices.
The final shapes therefore cannot be predicted from either starting change
alone. All 38 backbone links, 201 supplied frame terms, six protective
phosphate angles, 2,273 intensity/sigma pairs and 3,236 flags survived.
Reuse the three previous controls. The evidence ledger entry is
`crossed_5pc_starting_displacements_2026_11_21`.

C513 changed the same eleven base B fields in the independent A:PDU control.
It used the original C403 runtime and restraints. Five Phenix 2.2.1-6174
cycles shortened the terminal bond from the control's 1.500 to 1.476 Å
(target 1.470 Å), while tip height increased from 0.175 to 0.582 Å.
The inner alkyne angle reached 172.49°. Cedar retained the geometry
review. All 38 backbone links, 196 supplied terms, six D:1 protective
angles and all original intensity/sigma and flag values survived.
Both PDU and 5PC moved their tips farther from the ring under the base-only
change. The two terminal bonds moved in the same direction, but only PDU
moved closer to its target. This common host has a free B:1 hydroxyl.
The independent PDU:PDU incoming symmetry phosphate still needs its own
link evidence. Reopen `branch-artifacts/cedar/c513-pdu-displacement/science.json`.
The native and cold commands are in `matched_pdu_base_displacement_2026_11_21`.

C514 adds a read-only `--b-factors-at` option to the ordinary run assessment.
For a registered refinement it verifies the chosen model and its exact
parent and matches individual atom names and elements across the two PDBs.
The original checkpoint selection survives the reading. A single-model
checkpoint can also report its own values. The new reader, run integration
and CLI are in `refinement_displacement.py`, `cif_doctor_run.py` and `cli.py`.
There is no migration or change to normal refinement. Only numerical
readback is retained in the compact local record. Existing coordinates,
maps and run outputs stay in their original locations.

The installed reader recovered the four independent 5PC controls, the
matched A:PDU and the registered thirteen-change host. The latter retained
equal shifts within each of ATL (+164.94), DF (+8.80), 5PC (+222.74) and PDU
(+161.10 Å²). Their written occupancies stayed fixed. Each of the 22 atoms
in the independent PDU shifted by +168.12 Å². All six registries retained
their original fingerprints. Reopen
`branch-artifacts/cedar/c514-model-displacement/science.json`. Reproduce
with the relocated installation using
`python -B c514_bound_b_cli.py WORK CEDAR_SHELF NEW_OUTPUT.json`.

The following focused set passed 61 tests and seven subtests from source and
again from a relocated installation. All 325 packaged files matched.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_refinement_displacement.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py tests/test_refinement_link_geometry.py
```

**Where the arm bends.** C515 brings C405's signed bond directions into the
existing `--refined-planes` reading for any eligible source ring. In the
matched PDU the three successive bond elevations changed from −0.82°, −3.04°
and −3.76° to −1.99°, −9.42° and −13.88° at the final model when only the
starting base B changed. The last bond alone contributed 0.354 Å of the
0.582 Å displacement. In G:5PC the same change gave −1.85°, −5.46° and
−7.67°. The signed sum reproduces all six tip distances, and the old C403
model independently reproduces the original C405 calculation. The other
two 5PC B starts finish on the opposite side. These directions describe
coordinates. They do not resolve the driving forces.

Only the optional plane report and its tests changed. Existing checkpoints
and stored schemas need no migration. Source and relocated installation
each passed 105 focused tests and seven subtests. All 325 packaged files
matched. Three new regression cases failed before the change. The offline
replay used six existing five-cycle Phenix 2.2.1-6174 results and launched
zero native workers. It saved only the compact measurements in
`branch-artifacts/cedar/c515-arm-directions/science.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_refinement_plane_departures.py tests/test_cif_plane_coverage.py tests/test_cif_doctor_run.py tests/test_cif_doctor_cli.py
python -B c515_arm_directions.py WORK CEDAR_SHELF NEW_OUTPUT.json
```

C517 used the four existing original and base-only PDU/5PC models to ask
how much calculated scattering changes when the arm moves. In memory, the
three pendant carbons were rotated together about their attachment until the
tip reached the ring plane. All distances within the arm were preserved.
At the same coordinates the written arm B factors gave 59.7% (PDU) and
58.6% (5PC) of the complex structure-factor response obtained by assigning
those three atoms their own sugar C1′ B. In the uniform-B controls the
two calculations agreed. For PDU the 0.584 Å tip motion changed calculated
whole-model amplitudes by 0.204% RMS relative to model RMS amplitude. For
5PC the 0.341 Å motion gave 0.124%. Both use the exact 2,146 work indices;
all 127 measured free indices were excluded. This is a model sensitivity
measurement. The data's preferred orientation remains unresolved.

The native calculation reproduced the atom-only change from independent
whole-model sums and the expected B attenuation on every index. The three
PDB decimals shift the six-ring 5PC tip height from 0.34326 to 0.34112 Å
in the base-only model. The higher-precision coordinates reproduce the
existing C515 result. Full command and compact record are under
`arm_motion_work_scattering_sensitivity_2026_11_21`. No new refinement,
checkpoint, schema or product code was needed.

**Q06.** Fresh G:5PC completed both construction and ordinary five-cycle Phenix
refinement. Its automatically corrected C8–C9 target survived in the native
covalent restraints at 1.470 Å. The refined distance was 1.460 Å. The terminal
carbon moved from 0.712 to 0.130 Å from the six-atom ring plane. PostMR remains
selected and the new child is `refine-001`. C418's separately prepared one-cycle
continuation moved the terminal atom farther out despite straighter alkyne angles.
Keep both observations. This is a substituted-scaffold test. C423 now supplies the corresponding nonmetal DF:A refinement.

The [Q07 experiment order](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run)
keeps the known mixture ahead of the unfamiliar catalogue challenge.

## Which parts of the molecule stayed in shape?

The corrected PDU terminal bond is reproducibly closer to its 1.470 Å library target
after refinement. The historical matched pair also works on 5PC. Distortion can
still occur elsewhere. With matching simulated diffraction, a bent PDU straightens.
When only its two outer carbons cease contributing to those simulated observations,
the same model and restraints leave the arm bent (C411). The collaborator’s original
refinement is unavailable. Simon chose the controlled test to evaluate the patch.

C412 starts at the actual C401 checked preparation, continues C403’s ordinary
refinement for two further single-cycle children and retains the original selection,
eight inputs, phosphate protection and Free-R assignments. All six requested
pair terms were already supplied. Both new children pass the narrow alkyne screen,
yet the terminal carbon moves farther from the ten-atom plane Phenix restrained.
The new C413 cold reader exposes that distinction for any captured linear target.
Nine recorded planes in seven saved models agree with installed cctbx Cartesian
arithmetic. The same 55 focused tests pass from source and from a relocated wheel.
This checkpoint has focused qualification only. The two new fixed-unit rounds remain
unselected. Q06 still owns the scientific decision about refinement survival.

C410 completes the matched DF–Hg–DT research comparison with Hazel. Both actual
five-cycle refinements retained the contacts and heavy-atom plane memberships.
The DF attachment shortened, but a different bond moved farther from its target.
Changing the generated donor state also changed target values and uncertainties.
Keep routine metal-workflow adoption deferred until after NASolve is built.

C415 now carries the explicit observation request into ordinary Python Refine
Doctor trials. One real one-cycle Phenix ML-group child from the same C403
parent retained the prepared PDU, all eight inputs and the measured Free set.
The alkyne angles improved while its terminal carbon moved slightly farther
from the actual ten-atom plane. Doctor recommended inspection and preserved
the original selection. Eighty focused tests and ten subtests passed. The
Q06 whole-shape decision remains open.

C414 traced the actual modern parent reader for Hazel. It opened 290 distinct
dataset files during registry validation, though the child inherits just ten
operational inputs. Temporary verification files were released. A04 needs
its own metal-parent verifier before making a retention or pruning claim.

C416 confirmed all eight original pairs plus ATL:A on the saved mixed scaffold,
including all 201 intended restraints. That geometry-only run supplied the Q07
starting recipe for the registered C497 diffraction refinement and C505 continuation.
C417 checked the final geometry files written by Phenix in four ordinary runs.
The local PDU plane, the shared base-pair plane and the two neighbouring stacking
restraints all include the first alkyne carbon. The outer two carbons are absent
from those plane selections. Their shape can therefore move even when Phenix
retains the requested stacking restraints. All three shared planes and 58 two-plane requests matched at each
endpoint. These historical readbacks required no new native calls.

C418 checks 5PC on the same ordinary Doctor route. Its corrected terminal
bond ends at 1.478 Å, while the outer carbon moves from 0.043 to 0.157 Å
from the six-atom ring plane. The existing angle screen passes. This one-cycle
child inherited the historical explicit override. The ten-processor parent
is `refine-003`; an older four-processor sibling wrote the same coordinates.
C420 now names the checkpoint Doctor evaluated when another remains selected.

C419 then started again from the five G:5PC fixture inputs. Ordinary Coot and
NARestraints construction, automatic source-based correction and ReadySet
publication completed without a manual target. The published 5PC dictionary
sets C8–C9 to 1.470 Å with its original 0.027 Å width. PostMR is selected for
review. C420 passed 22 focused tests and 10 subtests across the Doctor and
triage modules. No full suite ran on the evening changes.

## C409 handoff, 19 November

Prior-work review found C114 neutral amide deletion, existing source composition,
explicit generator charge transfer and the bound neutral DF/DT parents. None
represents the newly confirmed N3 proton loss. Reuse those graph/source/generation
owners; do not change neutral definitions, phosphate state or the experimental model.

C409’s explicit graph-selected imide operation returns a separately named anion
source and provenance, without writing or adopting it. Local N(H/D) between two
C(=O/S) groups is required; no DF/DT atom-name dispatch. Ninety-four focused tests
pass, including both existing reader-input handoffs. The 27 new cases also pass
from a relocated package copy with its original path absent; all 310 copied files
remain exact. This is not a wheel-install or full-suite claim. Hazel's bounded static review
found no blocker. Both isolated generation attempts finish under the existing durable owner,
preserving all 35 formal charges, missing H3 and three sugar configurations.
The existing two-seed isolated qualification passes for each candidate, with the
same covalent proxies between seeds. All processes are stopped. Native monomer
formal charge remains unexposed; partial charge is not a substitute. No optimizer
convergence, Hg-linked acceptance or experimental refinement is claimed. Cold
replay leaves 145 files unchanged; a verified 750 KB local archive retains their
8.47 MB logical payload. Originals remain available.

Hazel independently rederived both isolated results without new native calls;
parent-to-declared stereo labels are exact, while candidate source-relative hands
are preserved without claiming new absolute CIP labels. Rowan’s read-only A109
compatibility map verifies both selected heavy-atom inventories and existing
backbone-port chemistry. No sulfur rename is needed. Eight other DT sites must
remain unchanged; four donor selectors need exact rebinding. Pair/stack selections
remain atom-based. Recorded neighboring distances do not supply link intent.
The donor-state ledger binds this map, isolated qualification and the subsequent
C410 comparison. Ordinary metal preparation continues to use its original definition.

Hazel delivered the preceding frozen integration to Alder at `f989111e` using
the complete run plus reviewed fixture-only focused correction, under Simon's
updated testing cadence. The original full result remains one failed fixture;
this is not a fresh all-green full run. C409 is not part of that frozen delivery.

## Previous bounded work — C407/C408, 19 November

Through 14:30 UK. C407 connects the existing C15 scalar geometry calculation to
C406's validated final-site observations. Prior-work review found no missing DF heavy
term and no justified new numerical target; C15 already owns bond/angle/ordered-
volume measurement. Reuse it rather than writing another chemical calculator.
Keep global indices, selected versus whole-model counts, source identities,
unavailable conventions and descriptive-only status explicit. Preserve historical
reports/workers and all acceptance/default choices. No new native sweep is planned.

Current checks: the exact-owner regression fails before the change; 168 focused
tests pass; 11 historical report/error cases are exactly unchanged. Cold replay
checks 112 scalar measurements across existing C403/C406 endpoints, leaving all
349 native files unchanged. All historical workers remain exact. Hazel
identified and the regression reproduced a source-change gap between owner
validation and reporting in scalar, trigonal and triple reads. They now reuse the
raw-site reader's existing final sealed-request check; all four readers refuse
the perturbation. No new validator or changed native worker.

The relocated installation passes 261 tests with 304 packaged files exact; its
actual saved reports match source readback. Eight source-only shuttle checks remain
in the 168-test source gate. The omitted-fixture first installed attempt is
preserved separately. Hazel accepts the final source review and source-free
installed readback. The combined full gate at `1acc7892` finished with **12,845
passed, one failed, two skipped and 298 subtests passed** in 4582.29 s. Its one
failure assumed a sibling temporary PHIL was unanchored, although the test scratch
was inside a repository. Runtime behavior was correct. The test now declares its
own repository boundary and asserts the outside input is absolute. The complete
counted-refinement module passes both inside and outside a checkout (35 tests each);
Cedar's counted/path checks pass 43 tests. The first local verification driver
omitted its scratch parent and is preserved separately from the successful fresh
attempt. This is a focused correction, **not a fresh green full suite**. The correction is preserved at `834b6b94`; subsequent aggregate qualification
and Alder delivery are recorded above. Runtime remains
exact `f83562b0`; the last standalone Cedar full gate remains `58965920`.
Linden completed C406 scratch retirement and owns W145 map provenance; Hazel owns
Cedar/Alder integration review. No overlapping branch or owner changes.

**C408 complete — matching-data recovery control, no new repair.** Both five-cycle
arms finish through the existing native owner. With amplitudes generated from the
C401 molecule, the independently perturbed PDU terminal offset falls 0.500→0.088 Å;
the reference finishes at 0.089 Å. Both narrow triple screens pass, the captured
sugar signs remain consistent and all supplied restraints/protection are retained.
Reference and perturbed endpoints still move 0.093/0.086 Å from the generator after
background alignment, and their R factors rise. The two refined PDU endpoints
differ by 0.0233 Å after background alignment (the displaced start differed by
0.1527 Å from the relaxed reference). This idealized, low-resolution
control establishes bounded recovery rather than experimental accuracy or Q06
closure. Hazel's 70-check independent review and separate eight-check endpoint
comparison pass. Native processes are stopped;
a verified 2.42 MB local archive retains all 96 files. No repeated native work is
needed. See `matching_atomic_data_recovery_2026_11_19` in the existing ledger and
`ScienceCheckouts/Rowan/2026-11-19/review.html` in the sibling workspace.

## Current checkpoint

**Already qualified C402–C404; reuse, do not repeat.**

| Milestone | Established behavior and retained limit |
| --- | --- |
| C402 | Automatic bond preparation now uses the existing archive/retirement owner. Actual C401 shrinks from 250.79 MB to 53.06 MB with all eight public model/PHIL/CIF files unchanged; interrupted retirement and relocated reads are covered. This is one preparation, not a 100-dataset capacity claim. |
| C403 | Fresh C401 preparation has a genuine unselected five-cycle ordinary child. Original observations/Free-R, all restraints and D:1 protection survive; actual native state, model inventory and all 3,239 reflection rows reproduce C338. Rwork/Rfree 0.2125/0.2265 and triple angles 175.4494°/174.4251° retain REVIEW. A verified 1.28 MB child archive explicitly depends on its retained parent. |
| C404 | The cold reader composes existing source-selected trigonal measurement with authenticated final coordinates. C2/C4/C5 maximum bond elevations are 0.802°/1.405°/2.039° with positively weighted native planes present. The installed package passes 185 focused checks; historical workers/triple reports stay exact. This measures shape, not repair or wider capture. |

Exact source, native, relocation and independent review receipts remain in the
existing evidence ledger. C403's 283 current and 57 comparison files remain
unchanged during cold readback; C404 reuses that same saved native result.

**C405 complete — separate local attachment shape from accumulated bending.**
A cold comparison applies the qualified C404 reader to the retained C396 private
control and C403 ordinary endpoint. Source connectivity selects the unique ring
and attached triple chain. C5 local maximum elevation rises from 2.039° to 3.149°;
the terminal carbon's ring-plane distance rises from 0.174812 to 0.365565 Å.
Signed bond components account for the latter exactly. The native covering plane
and member weights remain identical. This separates geometry, not causal forces;
C396 is not a repair or an ordinary checkpoint. All 332 native files retain bytes
and timestamps; no new Phenix job, production change or scientific acceptance.
Hazel independently verifies 73 checks with a different plane fit and angle
calculation. A smaller total bend at C5B coexists with a larger normal increment;
do not summarize this as both individual bends worsening.

**C406 qualified — record declared modified sites without a triple bond.**
An explicit ordinary Python option uses graph-valid checked-preparation projections
and a distinct v9 request, with byte-identical frozen v3 native code. Defaults and
historical readers remain unchanged; descendants cannot silently drop this scope.
The cold reader exposes captured heavy-atom intra-site terms. It neither infers
missing hydrogen/cross-site evidence nor invents a non-triple acceptance screen.
Focused regressions cover ordinary capture, source/identity drift, relocated reads,
manual ancestry and unsupported combinations. The relocated installation passes 231 focused tests. Matched actual DF controls
complete dry preflight and one cycle each, preserving byte-identical PDBs, output
state and correction counts with observation off/on. The new arm captures 20 heavy
atoms, 21 bonds, 30 angles, three chirality terms and one plane. All 66 files read
unchanged after relocation with the old path absent; the old reader refuses v9.
Hazel independently verifies 700 bindings without native calls.
The 1.930 Å attachment remains unaccepted: this is capture qualification, not a
repair, five-cycle survival or a new ordinary DF preparation. C406 full regression
passes on exact `58965920`; C407 has its later qualification above. Hazel owns the
complementary retained DF source-to-effective audit. Yesterday’s temporary
Cedar/Alder integration passed 166 focused tests and installed cold readback.
Its five documentation conflicts were subsequently resolved in today’s frozen
combined candidate; this is not an active Pine/main merge.

## Reuse the existing science

| Evidence | What it establishes; what it does not |
| --- | --- |
| C401 | Fresh AutoMR/Phaser → Coot/NARestraints → new source/plane generation → automatic bond discovery/repair → ReadySet → ordinary initial REVIEW publication. No borrowed C327 checkpoint authority. Published model, five PHILs and two dictionaries reproduce earlier corrected inputs. Preparation is not refinement survival. |
| C329 / C338 / C392 | Corrected PDU targets reach actual Phenix; the terminal C5B–C5M single target is 1.470 Å and C5A≡C5B remains 1.174 Å. Five-cycle PDU still bends. C392's passive weight observer exactly reproduces model/native state/maps and 1,962 correction calls. Do not repeat delivery or weight sweeps. |
| C395 / C396 | Declared pairing dominates pooled unweighted bond delta², not necessarily energy. Excluding only declared pairing from eligibility changes choices but does not repair chemistry: some lengths improve while terminal plane offset and diffraction agreement worsen. No production selector or threshold change. |
| C397–C399 / Hazel A85 | Actual-state FFT score/force mismatch is isolated; direct calculation agrees locally. Matched fresh histories still stop at rounding/iteration bounds without repairing sugar–base/metal strain. These diagnostics are complete; do not restart them without a new hypothesis. |
| C400 / Willow W137–W139 | Explicit 100-cap control and matched native/zero/full pair mechanics are qualified. Zero reproduces native history/model/reflections; passive full reproduces ordinary full. All arms share the existing plane-force correction. Seventeen added terms improve pair geometry, but all stop with lower-bound line-search errors before the cap. Not convergence or modified-residue acceptance. |

C400's same-fourteen-pair written-model comparison gives selected G:C plane mismatch
27.30→6.30°, A:T 8.85→4.59° and pair-distance RMS 0.247→0.200 Å. The A:T contacts
remain long. Final Rwork/Rfree are 0.2267/0.2613 for native/zero and 0.2271/0.2609
for full. Final clashscores are 23.27 and 24.77; the old runner's 32.28 was initial,
with a separate immutable amendment. Small Rfree/clashscore changes are context,
not standalone rejection gates. Same-coordinate denominator changes explain scalar
jumps, not the complete cause of stopping. Full-precision twelve-core-pair results
remain distinct from the fourteen-pair rounded-PDB comparison.

The A:PDU substituted scaffold is a mechanics control; its observations are not
claimed to come from a PDU crystal. Original PDU:PDU/B:1 intent remains separate.
C401's rounded published geometry has terminal single length 1.457987 Å, triple
1.189433 Å, adjacent angles 176.401°/176.885°, and terminal carbon distance from the
six-atom ring plane 0.094297 Å. These descriptive starting values are not acceptance.

## Next work, in order

1. Q06 still needs a defensible scope for post-refinement PDU and DF geometry.
   C476/C477 already compared the six C470/C474/C475 endpoints against the
   source rings. C497 adds the four named sites from the registered mixed
   scaffold. The earlier PDU:PDU construct retains separate incoming-phosphate
   and symmetry requirements. The
   synthetic recovery and omitted-scattering controls are complete. Repeating them
   or locating the original collaborator files is unnecessary for this checkpoint.
2. The [DF–Hg–DT comparison](cif-doctor-completion-queue.md#df-hg-dt-comparison)
   is complete as a research test. Its mixed outcome and Q13’s distinct phosphate
   question remain visible. Routine donor-state integration is a post-build decision.
3. Ordinary continuation from a checked root is demonstrated with the counted pair
   fully supplied. Wider protocols, additional force terms in that combined route
   and validated density fitting each need their own evidence before being advertised.
4. Q07 has its registered thirteen-component diffraction child with ATL
   alongside. The held-out eight-residue modified-pair challenge remains.
   Retain L-DNA/FANA/L-FANA/L-FDNA/PNA/locked-sugar learning under Q08–Q14.
   Q15 explains the result and owns the [regional twist and radius milestones](cif-doctor-completion-queue.md#regional-helix-analysis-for-publication)
   shared with Willow and Alder. Q16 ends with the AutoPhase compatibility audit,
   combined-source/full/native gates and merge review. No automatic merge or defaults.

The [single maintained queue](cif-doctor-completion-queue.md) owns closure criteria.
Q04/Q05 are complete for their recorded supported route; narrow integration gaps do
not reopen all ownership foundations. Linden owns Willow/TopoStitch and Hazel owns
Alder; coordinate before shared-source or native work. Do not duplicate their runs.

## Scientific boundaries to preserve

- **Native ownership:** C381–C391 provide preflight admission, counted-intent
  continuity, exact written-model proof and compact actual-final pair capture.
  Existing v3–v7 emitted workers keep their bytes; explicit v8 is separately bound.
  Missing optional improvement can retain a qualified parent. Unknown process state
  never authorizes retry, deletion or in-place repair.
- **PDU:** native planes and targets are present. C338 angles 175.4494°/174.4251°
  retain REVIEW. Do not flatten the molecule, copy coordinates into targets or
  strengthen restraints merely to force a pass. Site projections avoid incorrectly
  treating an isolated reference's OP3 as missing from linked B:4.
- **DF:** lab DF is 2-thio-dT/A1AAZ. Existing whole-base transport improves C1′–N1
  construction to 1.49958 Å, but Hazel's matched refinement stretches it to 1.662440 Å
  at native precision. Good construction is not successful refinement; preserve
  curated sulfur/iodine protections and the separate metal experiment's authority.
- **DY:** explicit packaged-source/backbone composition and ordinary construction
  are connected through C366. The C4–N1T single bond permits rotation. Conjugation
  favors near-coplanarity. C456 tested a soft shared plane and found that the
  triazole edge facing adenine also needs checking. Plane weight and ordinary
  use remain open. PDU→DT→DY and the reverse preserve the shared
  scaffold under the explicit deoxy rule. Broader sugar-family placement and DY
  pairing semantics remain separate; do not invent NARestraints relationships.
- **Phosphates:** original PDU:PDU B:1 is incoming symmetry continuation with
  P/OP1/OP2 and no OP3, superseding the earlier free-OH answer. B:7 O3′ is a candidate
  partner, not confirmed linkage. D:1 terminal protection is separate. Remove OP3
  only with proven incoming bonding; no blanket removal or invented symmetry angles.
- **ReadySet:** C323 traced the old 1.607 Å target to upstream RM1/GDIIS output after
  nonconvergence; ReadySet retained the supplied dictionary. Prefer source-faithful,
  independently checked repair over repeating the same generation for longer.

## Evidence, storage and reporting

Exact commands, revisions, limits and hashes are in the existing
[evidence ledger](cif-linked-native-registration-evidence.json). Current entries:
`fresh_automatic_pdu_publication_2026_11_18` (C401),
`automatic_bond_publication_retention_2026_11_18` (C402),
`fresh_ordinary_pdu_refinement_child_2026_11_18` (C403), and
`native_trigonal_geometry_readback_2026_11_18` (C404),
`pdu_substituent_geometry_decomposition_2026_11_18` (C405), and
`declared_site_native_observation_2026_11_18` (C406). Historical worker,
chemistry and construction entries remain evidence, not a second active queue.
Models, reflections, logs and archives stay local; compact evidence alone is committed.

The twelve-file science checkout (about 1.68 MB) is
`ScienceCheckouts/Rowan/2026-11-18/review.html` under the sibling GitHub root. Update it
with completed effects, reusing original model links and the Linden/Hazel checkouts.
C404 retires 487 verified duplicate software/test files (5.27 MB), retaining the
installed package, wheel, logs, XML and reproduction instructions. No scientific
files are removed. C406 separately retires 488 verified software/test files
(5.27 MB), keeping its installed package and native evidence. Hazel closes her
70.92 MB temporary integration export without removing scientific payloads.
A byte-verified 930 KB local archive preserves both C406 native attempts (91 files);
originals remain unchanged. It preserves evidence, not portable native re-execution.
Linden also retires 246,214 verified disposable C404 full-test files
(4.48 GB logical), retaining a byte-verified 252 KB qualification archive, installed
packages and all scientific inputs. Do not copy raw datasets to decorate reports. Private continuity and coordination
notes stay outside the product repository.

The earlier audit of 3,965 test definitions found seven exact-body groups with
mostly distinct owners/parameters, and no accidental imported-test collection.
A bounded C406 static check of 470 top-level test files also finds no shadowed
test names or directly imported test functions; it does not prove every case is
necessary. Do not delete tests merely because their bodies look similar. Retire only verified
owned duplicates through the appropriate owner; unrelated local files and peer
work remain untouched. Archive size does not measure peak temporary disk or memory.
