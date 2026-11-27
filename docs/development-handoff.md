# NASolve development handoff

Updated 27 November 2026. Three Q07 substitutions have completed ordinary refinement. The fourth has survived a direct five-cycle diffraction test.
Q06 keeps the PDU B:4 site under review. The aim is for a scientist to use a supported modified nucleotide without hand-editing a CIF. Coot builds the
residue, NARestraints supplies the intended pairs and stacks, and Cedar checks what
ReadySet and Phenix actually use. The [completion queue](cif-doctor-completion-queue.md#pipeline-position) owns the work order. The [capability table](cif-doctor.md#current-capability-boundary) owns the support
claims.

## Where to resume

The four-site diagnostic now starts from the mutation card alone. With UY1 absent from the cache, Cedar recognized the sugar and recovered from eLBOW adding a 3.728 Å C1′–N1 bond. The four-site construction reproduced the 860-atom seed from the earlier local fit, which cleared five short contacts without moving the 839 bystanders. The raw sugar stays out of the refinement checkpoint. Next, bind the local fit to the exact checked preparation and verify the six protected D:1 phosphate angle widths in ordinary AutoRefine. [Q07 measurements and remaining work](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C629 carried the cold-acquired UY1 dictionary into the actual 42-residue model. At A:19 Phenix used the 2′-endo table with the internal O3′–P connection. All 37 active geometry checks passed. In that protected input the general bundle check stopped on the six inherited D:1 phosphate angle replacements. The two native reads verified their actual targets and weights. Formal-charge readback remains unavailable. Ordinary selection of the fourth site and a final four-site run from a fresh molecular-replacement solution remain open. [Whole-model evidence](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C628 closed the isolated-dictionary step for two differently attached methyl ethers. The ordinary dictionary builder recovered UY1’s false C1′–N1 bond in a new attempt. Phenix chose 3′-endo from source coordinates and 2′-endo from generated coordinates. For the independent N-linked control OMU, both starts selected 2′-endo. All four reads per component qualified. Both six-file snapshots reopened offline. The regenerated UY1 numerical file differed from the fitted dictionary only in its writing-time comment. SJO’s source says DNA linking and marks O1P as leaving, so it remains under review. [Q07 evidence and next step](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C627 tested what happens when the fourth residue receives its full internal-strand dictionary. Phenix stopped expecting a terminal OP3, read O3′ as a bridging oxygen and kept the methyl ether. The other 41 residues and all applied geometry targets were identical. After five matched diffraction cycles, all 860 returned coordinates, occupancies and B factors matched the earlier fit at output precision. This establishes that Cedar can describe the actual backbone chemistry without moving the model in this test. The OP2 protonation question remains with Q13. [Linked chemistry comparison](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

Fresh whole-sugar construction now writes the phosphate where Phenix looks for it in the PDB atom-name field. In a two-residue calibration, moving only two spaces in that label changed the sugar restraint choice from 2′-endo to 3′-endo at identical coordinates. None of the 450 eligible site/conformer observations we screened changed choice. Those include related models and repeated conformers. On the four-site seed, all 860 coordinates were identical after the correction. The older construction still reopens byte for byte. [Phosphate and sugar evidence](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C624 placed the fourth substitution, 2′-O-methylpseudouridine (UY1), at A:19 opposite adenine D:4. Cedar matched the two pairing atoms and the measured sugar–base twist. Phenix moved only the 21 atoms of UY1, clearing five contacts shorter than 2.2 Å while leaving 839 neighbors fixed. The two base-pair contacts ended at 3.00 and 2.88 Å. Both phosphate links remained 1.60–1.61 Å. Transferring the source sugar pose without matching the host twist left a 2.08 Å clash after the same minimization. This was the geometry-only control. Five diffraction cycles then retained all 22 UY1 bonds and its four sugar hands. The N3–N1 and O2–N6 pair contacts finished at 2.93 and 2.83 Å, and both phosphate links stayed near 1.61 Å. All 125 test reflections kept their assignments. Phenix chose the 2′-endo numerical table with the next phosphate present. In this direct four-site experiment we supplied the repaired dictionary and the host residue’s median starting B. Ordinary four-site PostMR still needs to make those choices and clear the initial sugar clash. [Fourth-site evidence and limits](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C623 checked the pairing edge for the C-linked UY1 site. The older NARestraints
recipe asked adenine to bind the oxygen on the sugar-facing side. On the same
84 deposited atoms from 6I1V, Phenix installed the old distance at 5.33 Å and
the corrected one at 2.94 Å. Ordinary U:A stayed at 2.90 Å. An offline source
graph check now detects that mistake even when every atom is renamed.
The assignment for UY1 transfers from measured PSU and B8H duplexes. [Upstream correction](https://github.com/vecchioni-lab/NARestraints/pull/8).

C620 examined the next two sites, SJO and UY1. The same source-order repair
caught two different false native bonds. Phenix then chose the same sugar pucker
from both SJO starting geometries, but different puckers from the two UY1 starts.
C621 verified both native choices and both literal coordinate starts. UY1’s
ring pseudorotation was 58.7° in the source and 63.2° in the generated seed.
These are isolated dictionaries. The linked model still needs the correct
attachment at the base and both real phosphate connections.

C618–C619 took 2MG, 5MC and 6MZ through ordinary checked PostMR. Starting
with no 6MZ dictionary, Phenix added an O4′–C2 bond absent from the source.
Cedar recorded the failed attempt and recovered in one fresh attempt using the
same source atoms in a different order. The prepared coordinates, observations,
five parameter files and four dictionaries matched the warm-cache run byte for
byte. In that run, five ordinary Phenix cycles kept the 26 ring bonds within
1.98 restraint widths, all twelve sugar hands and all 38 backbone links.
Rwork/Rfree were 0.2292/0.2338. Three of 50 pairing distances exceeded three
widths. The unmodified host supplied the diffraction data. Next examine the
2′-O-methyl sugars on this same eight-site design. Leave the OP2-state question
with Q13.

C617 moved the starting-B correction into ordinary Coot construction. It checks the
two base graphs for one methyl in place of a hydrogen, on carbon or nitrogen.
For 5MC, 2MG and 6MZ the returned atoms reproduced all 32 independently predicted
starting B values. A fresh two-site Phaser → Coot → ReadySet → AutoRefine run
gave 1.427 Å for 2MG N9–C4 and 1.366 Å for 5MC N3–C4 after five cycles.
All 16 ring bonds were within 1.26 restraint widths. The 38 backbone links and
eight sugar hands survived. Three of 50 pair contacts still require review.
Rwork/Rfree were 0.2287/0.2356 (earlier two-site run 0.2213/0.2360).
Fresh checked construction now saves its base-B decisions and rechecks them
from the raw Coot model, parent and dictionaries when the run is reopened.
The three-site run above extends that result to the third methylated base.

C614–C616 traced the stretched RNA rings to a construction choice. Coot set all
32 transported base atoms to B = 20 Å². The three original host bases had median
B values of 223–270 Å². With the original dictionaries and five ordinary Phenix
cycles, starting shared heavy atoms from the host B fields and each added methyl
carbon from its attachment atom kept all 26 ring bonds within two printed widths.
Rfree changed from 0.2652 to 0.2423. All twelve sugar hands and 38 backbone links
survived. Three of 50 pair contacts still exceed three widths. These are hypothetical
substitutions on the host crystal. The exact-component ring dictionary comparisons
are controls. C617 applied the proven starting-value rule in ordinary construction.
The independent OP2-state and remaining Q07 substitutions stay on the queue.

C590 isolated why the PDU at B:4 can leave its base plane during refinement.
On the same coordinates, diffraction observations, displacement and solvent state,
least squares pulled its methyl tip toward the ring plane and maximum likelihood
pulled it away. Both five-cycle controls and a direct scattering calculation agreed.
The chemical plane was active. These 4.19 Å data leave the individual carbon
unresolved. Keep the qualified parent and mark B:4 for review.
[Measurements and scope](backbone-chemistry.md#two-diffraction-scores-on-the-same-pdu-model).

C591 identified both neighboring partners at A:11 in the first ordinary mixed
round. One contact reaches the preceding sugar, the other the following O5′.
The second round retains the two ATL-atom overlap values. Its compact record
omits their opposite endpoints. The new optional printed-contact screen preserves
every qualifying pair. Use the prior observations when planning the independent
eight-residue challenge and retain explicit review where sugar or phosphorus
stereochemistry is unresolved. [Mixed-scaffold evidence and transfer criteria](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

The independent eight-substitution W-frame challenge is fixed. Its first three
sites are C:12 2MG, A:7 5MC and B:5 6MZ. Coot placed all three on correctly handed
ribose sugars. The six flanking bonds and original displacement values survived
construction. Removing internal OP3 required proof of both backbone links.
NARestraints 1.1.4 also corrects the C1′–C5 attachment for four pseudouridines.
[Pair design and earlier controls](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

ReadySet placed four handed sugar carbons under a tight plane in conventional 6MZ.
A matched one-cycle experiment reduced base rotation from 38.6° to 8.9° when only
its dictionary changed. Cedar now screens both recipes for this contradiction with
the source graph. The source-preserving eLBOW route needed a separate atom-order
recovery after it introduced a 5.779 Å bond. All 42 declared bonds survived recovery.

Using all three source-derived dictionaries, five cycles preserved all twelve sugar
hands and six neighboring links. Eight of 50 pair contacts lay beyond three restraint
widths after one cycle and one after five. The 2MG–C and 6MZ–T contacts reached
2.46 and 3.37 Å. The diffraction was measured on the original W-frame crystal.
[Native measurements](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).

C611 carried the four independent isolated RNA reads (two with the ordinary Phenix
sugar pucker and two against the literal dictionary) into the linked model.
The native site-specific modification and pucker matched at all three sites. All
148 available checks passed. Phenix exposed no formal charges for the three sites.
The saved result reopened after relocation with the original run, installed workbook,
Phenix and local cache inaccessible.

C612–C613 took the actual ReadySet delivery through five native cycles. All three
sugars retained their hand. Two substitutions also completed the ordinary Phaser,
Coot, ReadySet and AutoRefine commands from a fresh run with qualified dictionaries.
Read the ring bonds before advancing the panel. The two-site fit stretched 2MG
N9–C4 and 5MC N3–C4 to 1.496 and 1.439 Å. The three-site coordinate-only fit
stretched them further to 1.611 and 1.573 Å. The targets were 1.388 and 1.352 Å.
6MZ N9–C4 reached 1.530 Å against 1.393 Å. One-cycle controls localized the large
stretch to the balance with diffraction. Dropping all external pair and stack terms
left it, while zero coordinate diffraction weight restored all three bonds to within
two restraint widths with the complete geometry. With the same full restraint set,
a lower positive weight reduced the three ring discrepancies to 0.9–2.9 widths in
five stock cycles. Rfree rose from 0.2652 to 0.2767. Test local chemical restraint
widths and neighboring geometry before recommending a global weight. The printed
widths were 0.024–0.031 Å for the three modified bonds and 0.006–0.008 Å for their
ordinary-base comparisons. The source
OP2 proton also reaches each linked phosphate dictionary. Reuse the Q13 state
check before changing it. A fresh three-site run still needs to select the
proven 6MZ recovery through ordinary preparation.
The C-linked base, distinct sugar bridges and specified sulfur side remain in Q07.
The catalogue-wide construction sweep follows in Q12. [Queue and scientific boundaries](cif-doctor-completion-queue.md#pipeline-position).

## What already works

- **Preparing and handing off a model.** Q04/Q05 closed on the explicit checked route. A
  normal campaign on the recorded control completed preparation, phasing and five
  refinement cycles, then reopened the chosen result after relocation. A separately
  qualified fallback can survive failed optional chemistry. Unknown or failed attempts
  retain their files and identity. [Acceptance and limits](cif-doctor-completion-queue.md#q04q05-acceptance-and-supported-boundary-at-c285).
- **Delivering modified chemistry.** Source-backed PDU and 5PC bond targets and neutral
  DF–adenine chemistry reached native refinement. Two five-cycle rounds used the known
  13-change scaffold, including ATL alongside the eight original pairs. Two close ATL
  contacts and site-dependent PDU/5PC geometry remain. The independent G:5PC C474
  measurements survive, but its final geometry/report no longer resolve at the original
  temporary location for a fresh C587 reading. Reuse its recorded evidence with that limit.
  [Mixed-scaffold requirements](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).
- **Crystal links and deposition.** On the tested 5W6W-derived PDU scaffold, both
  crossovers survived native restart with the original Free-R set. B:1 has P, OP1 and OP2
  and connects to B:7 through a crystal copy. D:1 terminal protection is a separate intent.
  A recut must carry the declared atoms and image into its new numbering. Independent sugar
  class, torsions and local density still matter even when the O3′–P length recovers. The
  deposition guide records what the wwPDB actually returned for the locked-DNA models and
  how to remeasure a reported outlier. [Backbone chemistry](backbone-chemistry.md#the-central-strand-in-the-5w6w-scaffold) · [OneDep checks](pdb-deposition.md).
- **Transfer beyond the original ligands.** Carry the FANA and mirror-sugar stereochemistry
  checks, locked-sugar junctions and connected PNA attachment rules into the ordinary
  route. Census coverage (599 distinct codes in 618 NARestraints rows) identifies the
  remaining work. Geometric survival on one member qualifies only the tested context. [Coverage and chemical-family gates](cif-doctor-completion-queue.md#chemistry-transfer-and-coverage-packages).

## Boundaries with Willow/Pine and Alder

Willow/Pine identifies the logical strand, the crystallographic copy and what changes when
the model is recut. Cedar verifies the component graph, the intended covalent versus
pairing interactions, and the forces and geometry at those endpoints. Alder declares the
metal site, its donors and protected atoms and the occupancy, displacement and
anomalous-scattering policy. When a site crosses those boundaries, carry the same chosen
parent, atom identities, image, dictionaries and Free-R assignments through ordinary
refinement and its returned model. Reuse the shared map sampling, checkpoint and Phenix
readers. Linden found that a newer base-restraint reader had stopped the older
phosphate workers from starting. C622 restored their exact bytes. A relocated
Cedar wheel emitted all ten worker bundles identically to the original source,
and 142 focused checks passed. Willow owns the resulting two-link trial. The
transferable handoff still needs an installed combined-source check. [Integration checks](cif-doctor-completion-queue.md#q16--final-integration-portability-and-retained-artifact-closure).

## Validation and release

C623 passed 223 focused checks with each of NARestraints 1.1.4 and the 1.1.5
candidate. Both new package distributions passed 57 tests after relocation.
Native Phenix read both restraint sets on identical deposited coordinates.

C620 passed 209 focused tests covering the native sugar checks and acquisition.
C621 passed 264 focused checks, ran four literal Phenix controls and replayed
both pairs after moving the evidence and blocking access to the original SDK.

C619 passed 172 focused outer-request, cache and ordinary-PostMR checks, followed
by 124 acquisition, retention and source-order checks. The two pytest selections
overlap. Native Phenix 2.2.1-6174 and Coot 1.3.3 completed cold preparation. Its
compact record reopened after relocation with the original inputs inaccessible.

C587's plane inspection passed 123 focused tests plus seven subtests. C589's AutoRefine
reporting passed 61 plus 52 subtests. Each set passed from source and from a relocated
installation. Four PDU logs and a separate FT–Hg log support the target reader. C588's
relocated full five-cycle replay reproduced the written coordinates, final geometry and all
140 recorded gradient evaluations for the combined case. These are distinct software and
native checks. C605 passed 323 focused tests covering qualification execution,
RNA pucker replay, acquisition, dictionary storage, binding and native usability.
The 6MZ pair of jobs also reopened identically after both directories moved and
their previous paths became inaccessible. Phenix 2.2.1-6174 executed the native
checks. C606 passed 149 focused tests plus seven subtests and ran a fresh
five-cycle linked Phenix comparison with the same input and Free-R assignments.

The last recorded standalone full Cedar pass is C406 at `58965920`, with 12,043 tests passed, 293
subtests passed and two native opt-in skips. The later combined C407 experiment had one
location-dependent fixture failure. The fixture correction has focused coverage.
C611 passed 419 focused acquisition and linked-chemistry tests and another 108
focused preparation and sugar tests. C612–C613 used native Phenix 2.2.1-6174,
Coot 1.3.3 and NARestraints 1.1.4. The trial used the original scaffold observations
and Free-R flags. Cedar and any combined integration revision still require their own full qualification.
Provisional integration into Pine and eventual main review are separate decisions. [Archived commands and receipts](history/README.md#november-26-cedar-roadmap-audit) ·
[CIF Doctor evidence ledger](cif-linked-native-registration-evidence.json).
