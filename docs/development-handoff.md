# NASolve development handoff — current state

Updated **2026-11-19, C410–C417 refinement and geometry checks — Rowan**.
Active branch **cedar**, worktree **NASolve-c96**; C409 source checkpoint **`452b7c45`**; C407/C408 runtime **`f83562b0`**.
Last standalone full-qualified runtime **`58965920`** passes
**12,043 tests and 293 subtests**, with two existing native opt-in skips, in
**3104.30 s**. All 1,417 tracked test-checkout files and exact NARestraints
`a9264f9e` remain unchanged; the test process group is absent. The verified
254 KB qualification archive retains exact results, commands and source bindings.
Linden completed the recorded 4.48 GB owned test-copy retirement on 19 November,
rechecking the archive and preserving scientific inputs, installations and shared NAR.
Focused, relocated installed, matched native and independent checks also pass.
Software qualification does not change the scientific REVIEW or close Q06.

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
including all 201 intended restraints. That geometry-only run supplies the Q07
starting recipe. Ordinary diffraction refinement of the mixture is still open.
C417 checked the final geometry files written by Phenix in four ordinary runs.
The local PDU plane, the shared base-pair plane and the two neighbouring stacking
restraints all include the first alkyne carbon. The outer two carbons are absent
from those plane selections. Their shape can therefore move even when Phenix
retains the requested stacking restraints. All three shared planes and 58 two-plane requests matched at each
endpoint. These historical readbacks required no new native calls.

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
   Reuse the matched bond-target controls and the measured whole substituent. The
   synthetic recovery and omitted-scattering controls are complete. Repeating them
   or locating the original collaborator files is unnecessary for this checkpoint.
2. The [DF–Hg–DT comparison](cif-doctor-completion-queue.md#df-hg-dt-comparison)
   is complete as a research test. Its mixed outcome and Q13’s distinct phosphate
   question remain visible. Routine donor-state integration is a post-build decision.
3. Ordinary continuation from a checked root is demonstrated with the counted pair
   fully supplied. Wider protocols, additional force terms in that combined route
   and validated density fitting each need their own evidence before being advertised.
4. Q07: original mixed scaffold with ATL alongside, then the held-out modified-pair
   challenge. Retain L-DNA/FANA/L-FANA/L-FDNA/PNA/locked-sugar learning under Q08–Q14.
   Q15 explains the result. Q16 ends with the AutoPhase compatibility audit,
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
  are connected through C366. The C4–N1T single bond joins two independently rotatable
  rings; do not impose a common plane. PDU→DT→DY and the reverse preserve the shared
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
