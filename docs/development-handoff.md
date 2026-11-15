# NASolve development handoff — current state

Updated **2026-11-15, C307 numerical-parameter investigation active**. Worktree NASolve-c96, branch
**cedar**, source fix **a2e73603**, C304/C305 compact native evidence **91591126**. Simon's new window is **11:54–14:54 London**;
interruptions expected. Focused checks only; no full suite, new branch or merge.
Linden owns Pine/Willow; no Cedar edits from that work.

## Active bounded checkpoint

C307 adds `cif_linear_bond_reference.py`: source-graph queries, explicit numerical
comparisons and separate candidates changing only selected distances. No model
coordinates, invented targets, ESD changes, implicit adoption or legacy-policy
changes. Exact energy-library rows additionally require source valence, matching
dictionary types and unique library type definitions; unsupported neighbors remain
visible. MMFF and library references are diagnostic evidence, not automatic truth.

Validation: **161 focused passes**, including 43 new cases. Broader chemistry:
1735 passes +10 subtests, with 11 sandbox-denied process-signal/inspection failures.
All four affected files subsequently pass outside that restriction: **192 passed**.
Do not call the original sandboxed profile green. No full suite or process-code edit.

Local live tests: `307_Cedar_linear-parameter-82pj2ra2`. Both owned MMFF queries
and `native-check-0002` have stopped successfully. Its native interpretation
changes exactly the chosen terminal-bond target to 1.459 Å, retaining every other
proxy and coordinate. Initial output-layout refusal is preserved, not retried
in place. The exact installed CSP–CH3 library row independently supplies
**1.470 Å / .020 Å**. Separate library candidates retain the original ESDs; their
native/refinement tests are next. No source lock or native work currently active.
Compact methods, commands and fingerprints: ledger
`linear_neighborhood_reference_candidates_2026_11_15`. Continue under existing
round ownership, preserve selected endpoints, and do not reopen Q04/Q05.

## Current stopping state and next work

**All C304/C305 native jobs, readbacks and C304 retention have stopped.** No source
lock or pending retry remains. Native sources: C304 **9489077a**, C305 **a2e73603**;
C305 consumer/readback source differs only by compact documentation. No full suite.
Completed controls use Phenix 2.2.1-6174 / dispatcher 2.2.1; C305 also uses Coot
1.3.3 revision 0. See exact records, source pins and limits in the evidence ledger.

**Next bounded task:** establish trustworthy numerical parameters for the whole
linear substituent, including the single bonds beside its triple bond, through
existing repair/selection owners. C306 confirms C206's unresolved PDU target and
finds the related 5PC terminal bond needs review too. Do not use seed coordinates
as replacement targets, copy weights or change historical triple-screen meaning.
Separate parameter calibration from packing and diffraction/restraint compromise.
No Coot repeat, new recovery owner or blanket flattening. **Q06 remains open**;
Q08 supplies the numerical diagnosis. All C306 read-only commands have exited.

## C306: a straight triple bond can still have a wrong neighbor

The source-graph diagnostic selects explicit triple bonds and their adjoining
heavy-atom single bonds, without residue-name rules. Exact selected dictionaries
and prepared/refined native captures agree on these terminal single-bond targets:

| Control | Terminal bond | Target / ESD (Å) | Prepared → refined distance (Å) |
| --- | --- | --- | --- |
| PDU | C5B–C5M | 1.607 / 0.020 | 1.4580 → 1.6242 |
| 5PC | C8–C9 | 1.364 / 0.027 | 1.4552 → 1.3564 |

Source ideal-coordinate distances are 1.4724 and 1.4619 Å respectively, but those
coordinates are not independent numerical authority. As a separate benchmark,
[NIST's experimental propyne table](https://cccbdb.nist.gov/listgeomexpx.asp?casno=74997&charge=0)
reports 1.460 Å for the methyl–sp-carbon bond. That supports scrutiny, not copying
a PDU/5PC target or ESD from a different molecule. The existing triple screen
checks triple length/linearity, not these neighboring single-bond targets; retain
its historical meaning. The 5PC scoped PASS therefore is **not whole-ligand approval**.

Both selected targets match selected seed-coordinate distances at CIF precision.
Installed eLBOW writing starts from coordinate bond lengths, with optional ideal,
Mogul/transfer/override branches; this is consistent provenance, not proof of
which generation branch executed. Retained generation provenance uses the same
180-step source-preserving recipe: PDU reports nonconvergence; 5PC convergence
is not reported. C206 already tried longer PDU optimization, without qualifying
these targets, so increasing steps is not the next answer. Fresh bounded installed
lookups find neither component in this exact Phenix consumer. No easy installed
numerical fallback was found; no new generation, target edit or acceptance gate ran.
Exact anchored inputs, SDK hashes, local runner hashes and scope are in ledger
`triple_neighbor_numerical_target_review_2026_11_15`. Existing C304/C305 entries
remain unchanged. Native captures and every scientific output remain local.

## Retained native controls for the next comparison

C305 G:5PC run: `305_Cedar_5PC-campaign-nu1t7jyw/relocated/DiU/AutoMR/run_001`
under local live tests. C304 A:PDU run:
`303_Cedar_PDU-campaign-btuh5sop/relocated-after-c304/DiU/AutoMR/run_001`;
its comparison records are `304_Cedar_PDU-recovery-1f37ak8q`. Both have postmr
parents and selected refine-001 children after five actual checked-plane cycles.
They preserve original scaffold observations/Free-R and D:1 terminal phosphate;
these are substitution mechanics controls, not data from PDU/5PC crystals or
structure approval. No chi flips; all three recorded sugar signs and native
45-plane/58-parallelity inventories survive. PDU triple geometry is REVIEW,
5PC scoped triple geometry PASS; neither has whole-neighborhood target approval.
Old campaign anchors are absent and cold archive-backed reads passed. Full native,
relocation and geometry evidence is in the existing C304/C305 ledger entries.

## Where the pipeline stands

**Q04/Q05 accepted for the explicit supported route** at C285/d5996bc4:
preparation, independent fallback, stopped-work recovery, retained alternatives,
chosen-input delivery, serial bookkeeping and archived evidence. Reuse those
owners. Defaults, migration, deployment capacity and integration remain Q16.
The [completion queue](cif-doctor-completion-queue.md) is the sole work order.
Last full suite is C220/583d30df: **9178 tests +276 subtests**; not current.

**Q06 active: does real refinement preserve the intended chemistry?** C291–C300
already establish complete parallelity parameters, corrected native forces,
frozen helpers, zero-cycle setup and explicit AutoRefine/campaign/Doctor routes.
Only the recorded Phenix 2.2.1-6174 / dispatcher 2.2.1 Darwin arm64 source is
qualified. No SDK edits or default activation. Do not repeat those controls
without a new question. Keep Free-R, NAR membership, chemical targets and thresholds.

C301 bea76681 fixes mixed canonical/modified Coot serial authority. C302 d32825e9
separates the actual repair owner in storage v3 while retaining old layouts.
C303 c9736e39 removes duplicate final validation through the existing bounded
pure-math scope. Their full evidence remains in the existing ledger, not this diary.

## Recovery and storage state to preserve

C304's fresh attempt 2 completed under the frozen request's existing 900 s
allowance; attempt 1 and historical BLOCKED campaign bookkeeping remain intact.
No retry in place, Coot repeat or automatic campaign-resume claim. Successful
retirement reduced the PDU request 388.38→231.02 MB while preserving all failed
work; C305's archived successful request is 39.74 MB. Neither is a native
100-dataset capacity guarantee. Raw science and optional captures stay local.
C304's cleanup-policy export fix a2e73603 passed 147 focused checks. C307 changes
none of those owners. Exact commands and limits remain in the evidence ledger.

## Scientific and collaboration boundaries

B:1 in the original PDU:PDU scaffold means intended incoming symmetry continuation:
preserve **P/OP1/OP2, no OP3**, superseding Simon's earlier free-OH reply. C295's
nearest B:7 O3′ image `-x+y,-x,z` at 3.34019 Å is a candidate, not confirmed linkage.
D:1's separately declared complete terminal phosphate remains distinct. No blanket
OP3 rule, lone symmetry bond, inferred free OH or invented angle enforcement.
Pine carries editable intent; TopoStitch previews; Cedar separates declarations,
coordinates and actual native enforcement. Linden W66/W67 preserve those boundaries;
installed composition is separate from Cedar chemical acceptance. Linden's W68
reports native angle kernels can handle explicit images, but ordinary manager
evaluation omits unit-cell context and pickle/deepcopy can lose operators. Treat
that as separate source-bound Willow evidence: no Cedar symmetry-angle support or
bond activation. The current plane-force bridge wraps the evaluation kernel; it
has no custom-proxy metadata reconstruction hook and explicitly refuses symmetry
planes. Future reuse of the existing round owner needs separate angle lifecycle
and evaluation qualification, not another refinement driver.

Simon authorized code/tests/compact evidence pushes. Models, diffraction data,
logs and runners stay local. Retain failed work; use existing qualified archive
owners for successful duplicates, never ad hoc deletion. Keep execution serial
and one expensive scientific reader at a time. No native 100-dataset capacity claim.

Next after Q06: Q07 combined and unfamiliar-modification controls; Q08–Q14 retain
sugar/backbone/chemical-state learning; Q15 scientist report/PDF; Q16 AutoPhase
compatibility rename and full integration/release review. No automatic merge.
Cross-agent notes are signed **— Rowan**.
