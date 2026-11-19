# Metal development handoff — current state

Updated **19 November 2026**. Active feature branch: **Alder**. The
[root integration handoff](development-handoff.md) owns the current combined
source, full validation and delivery. The [A01–A09 roadmap](metal-development-roadmap.md)
owns feature completion. The earlier chronological diary is preserved as
[evidence through 18 November](history/metal-development-handoff-2026-11-18.md),
not a second queue.

## Current scientific and engineering boundary

**Evening session, 19 November:** the approved matched neutral/deprotonated
DF–Hg–DT research comparison is complete and independently read back. Two
five-cycle open XYZ/group-B fits used matched generated sources, identical
starting atom states, data/Free-R/phases, common original planes and Hg terms.
DF C1′–N1 changes **1.652534 → 1.601336 Å**, against targets **1.499 → 1.501 Å**;
Rwork/Rfree change **0.3082/0.3384 → 0.3087/0.3380**. The DF ring becomes flatter,
but its attachment remains long and C2–S1 moves farther from its target.
This is a partial response, not a repair or experimental protonation assignment.
Both jobs stopped and sealed; no f″ fit or checkpoint selection followed.

The whole-model context checker still refuses unrelated terminal B:1. The local
comparison preserves that state and uses the existing selected-site phosphate
and linked-preparation owners. Formal-charge readback is unavailable, and the
unchanged V9 executor does not record individual optimizer stop reasons; five
completed macrocycles do not prove convergence. Routine donor-state integration
remains deferred until after the build. Do not repeat this pair without a new
question. Local evidence: `ft-hg-donor-comparison-20261119-01/` under the Alder
artifact anchor; independent endpoint review is
`cedar/c410-matched-neutral/matched-endpoint-review.json` under `branch-artifacts`.
The small local science checkout is
`ScienceCheckouts/Hazel/2026-11-19_donor-comparison/review.html` alongside the repos.

**A01 remains partial: ligand geometry and open XYZ/B refinement. A02 stays
gated.** Whole-base construction and exact restraint delivery have evidence, but
the FT_Hg open fit still stretches the sugar–base attachment. A readable CIF,
completed process, or Rwork below 0.30 alone does not establish useful geometry.
No new accepted geometry or f″ parent follows from current integration work.

Cedar C409 subsequently qualifies the declared DF/DT imide-anion sources and
their isolated two-seed native usability (separate Cedar source `452b7c45`).
Independent cold readback preserves all 145 files and confirms the exact H3-only
removal/N3 formal-charge delta with all other graph/charge state retained. Native
formal charge is not exposed by the API, and absolute CIP remains unassigned;
source-relative sugar handedness is preserved. This source change is not yet
adopted here. The investigator's later 19 November scope decision defers routine
donor-state integration until after NASolve is built. It is not an immediate
A01 gate or a prerequisite for another otherwise qualified FT_Hg open fit.
The approved matched neutral/deprotonated research comparison is now complete
as described above. Its aliases, selected polymer links and common planes were
checked through the shared owners; the whole-model terminal limitation remains.
Existing A01 geometry and evidence standards remain unchanged.
The retained C409 `site-compatibility.json` maps the exact A109 input: selected
A:12/B:4 atoms already match the derived sources by name, with OP3 as the sole
extra source heavy atom. Preserve eight unrelated DT sites and all Hg targets.
Use an actual site-relabelled child and the existing linked preparation owner;
the canonical-only construction projection cannot represent the existing DF
input. Recover declared links from preparation before pruning terminal atoms;
neighbor distances are inventory evidence, not link authority. This read-only
map is under the shared local `cedar/c409-declared-donor-state/` artifact anchor.

**A04 remains partial: lean frozen-trial storage.** Read-only inventory, scenario
forecast, lossless compact projection and exact input archive transport are
implemented. The adapter reuses the shared archive/temporary-view owner, preserves
all attempts and reconstructs inputs without original-data lookup. Production
shared-parent retention, native regeneration, campaign budgets and safe retirement
remain separate gates; the bounded feasibility result below does not close them. Do not prune old immutable trials through an input-transport receipt.

A bounded A04 rehearsal now recovers two old legacy PostMR roots and their
metal parents through the existing installed readers from **782,402 bytes**
(**4,730,256 logical bytes**), with original science/source access denied and
seven missing/changed-dependency refusals. Exact archived-request reproductions
then return identical complete result records in **7.83 s (Hg)** and
**17.15 s (four Ag)** under the original trusted worker/native hashes.
These are diagnostic recovery checks, not scientific solutions. No new public
storage interface or deletion follows. Modern checked ancestry and full software
identity remain open; details and receipt anchors are in the
[storage contract](metal-campaign-storage.md#bounded-protected-parent-and-regeneration-rehearsal).

Construction is chemistry/connectivity driven. PDU and DF are qualification
examples, not names selecting special repairs. Related supported cases, unchanged
good cases and unsupported/ambiguous contexts need their own evidence. Label
invariance is useful mechanism coverage, not another chemical specimen.

## Reuse these results before proposing another experiment

| Evidence | Established result and remaining limit |
| --- | --- |
| Whole-base construction and native state export | Initial FT_Hg C1′–N1 is 1.49958 Å; source chemistry/link context and active-state B export are preserved. Construction does not qualify the subsequent open fit. |
| Matched weight/iteration/phase/normalization controls | Private controls expose pooled pairing/covalent weight-selection effects, actual stopping limits and a geometry/R tradeoff. None is an adopted repair; do not repeat the matrix without a new hypothesis. |
| Source/effective/native local audit | All 20 surviving local heavy atoms, 21 bonds, 30 angles and the 10-heavy-atom plane match the declared scope/targets/weights. Three removed source bonds touch explicitly deleted HO3′/HOP3/OP3. Missing local targets do not explain the retained strain. |
| Retained pooled versus covalent-eligibility controls | Attachment 1.66243991 versus 1.57775796 Å, against 1.499 ± 0.038 Å; Rwork/Rfree 0.28553/0.29088 versus 0.32905/0.34210. Geometry improves locally while diffraction fit worsens. These are independent old diagnostic fits, not successive accepted stages. |
| Shared C406 non-triple observation | Two one-cycle native arms with observation off/on have identical complete PDB bytes, output state and kernel counts. Local capture exposes 20/859 atoms and actual proxies. The 1.92975 Å attachment remains unaccepted; it is not comparable as a five-cycle endpoint. |
| Compact result projection | Three old FT_Hg trials produce 25,884 B of projection; the Ag4 trial produces 54,643 B. Every attempt and complete result remains. Original inputs/native evidence are still required; these are not safe-reclamation or accepted atom-count claims. |

The local audit passes 1,703 checks and rejects seven corruptions. Two complete
relabellings preserve all 51 bond/angle rows. Independent C406 readback passes
700 checks with the original root absent and 66 native files unchanged. H atoms,
cross-site/link/symmetry interactions and deferred native categories are not
qualified by the local scalar audit. Source phosphate chemistry is a separate
shared question; do not silently change protonation, targets or sigmas.

Exact native producer: **Phenix 2.2.1-6174**. Those native executions belong to
the retained controls; cold readback/projection/integration launches no new
Phenix or Coot job. All diagnostic values retain their actual source context.

## A01 evidence audit and next finite-move experiment

The late **19 November** audit reconnects already completed Cedar C397–C399
work that the older local `next-a01-gradient-bridge.json` still describes as
scoped. That historical plan is preserved, but its derivative/restart queue is
closed. C397 reproduced the exact A85 fixed-normalization XYZ callback at
return 2779, before ADP refinement: geometry derivatives agreed with finite
differences in 13 sampled directions, while FFT data/combined derivatives did
not. C398's direct-factor diagnostic agreed for all three components in the
same 13 directions. C399's fresh-history restarts still stopped with an FFT
rounding error or direct iteration cap; neither repaired the attachment.
These are completed diagnostics, not authority to adopt direct factors or the
private normalization policy. The independent Alder C399 review already passed
215 checks; do not repeat it. Exact source records remain in the shared Cedar
registration ledger and the local C397–C399 archives.

A new **cold projection**, using the retained full C397/C398 gradients, asks
whether shortening the attachment is initially uphill or downhill at that
historical state. Positive displacement means a shorter C1′–N1 bond. Values
below are derivatives of the weighted objective per Å of bond shortening:

| Direct-factor direction | Data | Geometry | Combined |
| --- | ---: | ---: | ---: |
| Move C1′ and N1 equally toward each other | +0.000727452 | −0.001117854 | −0.000390402 |
| Translate the connected nine-heavy-atom base toward C1′ | +0.014921958 | −0.017962439 | −0.003040480 |

Data opposes both movements, geometry favours them, and their combined first
derivative favours shortening. The attachment is **1.615911357 Å** in this
snapshot. These are slopes, not finite improvements or evidence about the new
neutral/deprotonated endpoints. The direction norms differ: compare signs, not
their magnitudes as competing search performance. The base is selected from
the declared source bond graph after cutting the attachment, not by a repair
rule keyed to the residue name. Rigid translation preserves its internal
geometry but changes Hg, pair, stacking and other context contacts; the existing
plane including C1′ is also not an internal-base invariant.

The local `a01-gap-audit-20261119-01/projection.json` records **45 passed checks**:
archive/member hashes, exact cross-archive state identity, full weighted gradient
closure, graph selection and coordinate invariance. The 0.02/0.05/0.10 Å
coordinate constructions check that invariance only; their objectives were not
evaluated. No new Phenix/Coot process or complete refinement ran. The retained
native producer was **Phenix 2.2.1-6174**; the cold reader used Python 3.12.14
and Gemmi 0.7.5. Reproduction command, with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 "$ALDER_REVIEW_PYTHON" branch-artifacts/Alder/runners/A166_a01_gap_audit.py --repo "$NASOLVE_CHECKOUT" --output "$NEW_LOCAL_REVIEW_DIR"
```

**Next experiment, scoped but not executed:** one finite attachment-contraction
profile in a captured current-protocol objective state. C413/C415 final-site
records provide atom identities and geometry, not the complete data target,
likelihood core, scales, masks and gradients. A written PDB is insufficient.
Reuse the C397/C398 actual-owner capture precedent; first reproduce the chosen
baseline with identical observations, Free-R, phases, scattering, B/Q/f′/f″,
weights and declared source/metal terms. Capture the selected XYZ stage before
ADP changes and retain its relation to the full open fit. If that state cannot
be reproduced, stop at the capture gap without interpreting a substitute.

For the diagnostic only, record the direct-factor objective as distinct from
FFT. First qualify the new rigid-base direction by central differences at
±0.0001 and ±0.001 Å against its own direct gradient. Then evaluate 0.02, 0.05
and 0.10 Å shortening and restore the baseline. Retain raw geometry, weighted
data/geometry/total, actual term inventory and cache observations for every
point. Freeze non-coordinate context; do not refresh the likelihood or masks
mid-profile. Record expected Fcalc changes. A changed nonbonded inventory is a
boundary to report, not a reason to hide terms or force an unchanged cache.
Stop the first profile there and reassess its smooth range. Bound one process,
at most 12 profile evaluations and 180 seconds after takeover, with a separately
declared replay timeout and powerdown margin. No optimizer resumes in this
diagnostic. The historical C398 state is an available qualification fixture,
not a substitute for current-state scientific evidence.

- **Finite improvement survives:** scope one structural child using the same
  declared chemistry/recipe and ordinary open XYZ/B policy. Record whether the
  gain survives refinement and assess the whole local geometry, Rwork/Rfree,
  stopping evidence and maps. A profile point alone is not an accepted model.
- **Only infinitesimal improvement, reversal, or a contact boundary:** inspect
  the contributing terms and affected contacts before choosing a new recipe or
  structural degree of freedom. Do not infer protonation or tighten targets
  from this result alone.
- **Derivative/state inconsistency:** return the bounded reproduction to the
  shared native owner. Do not launch another weight/iteration matrix.

This is a plan, not a new optimizer, constructor or acceptance policy. A01
remains partial and A02 gated. Generated vectors, archives and the compact
science checkout stay local; runtime, schemas and migration requirements are
unchanged. The local checkout adds `a01-next.html` beside the existing reports,
without replacing the earlier model/map comparisons.

## New readbacks and declared donor state

C407's shared final-site scalar report reproduces 112 existing PDU/DF rows;
installed readback is exact. No second coordinate calculator or changed numerical
worker is introduced. The saved one-cycle DF fit retains C1′–N1 = 1.92975 Å
against 1.499 ± 0.038 Å, C2–N1 = 1.67415 Å against 1.396 ± 0.030 Å,
and C2–S1 = 1.74920 Å against 1.638 ± 0.026 Å. These are descriptive local
observations, not native energies, new fits or a later stage of the five-cycle
controls. Missing hydrogen/link/symmetry context remains explicit.

The source DF dictionary includes neutral NH1 at N3 and an N3–H3 bond; the
A:12 DF/B:4 DT model has no H3 coordinates. Its recorded modification changes
terminal atoms, not this donor state. The investigator confirmed that Hg replaces
both N3 hydrogens. Shared chemistry Q13 owns explicit site-scoped state derivation
and native qualification, preserving neutral sources and unrelated residues.
Routine integration is deferred until after NASolve is built; the completed
matched research comparison is separate from product implementation and A01 completion.
Absent H3 coordinates do not establish equivalent heavy-atom restraint chemistry.
The delivered neutral and regenerated definitions differ in local bonds, angles
and plane membership, so those differences cannot all be attributed to H loss.
Preserve the approved plane policy and Hg terms in the matched comparison, record
remaining generation differences, and judge the local heavy-atom response without
assuming a repair. Intent does not establish new numerical targets, formal-charge
readback or the cause of the observed strain. No routine donor-state workflow is
implemented here.
Evidence and confirmed intent are in the integration anchor's
`coordination-state-question.json` and `coordination-state-authority.json`.

Cedar C408 separately supplies a matching-data PDU positive control. With
noise-free atomic amplitudes and the original restraints, the perturbed terminal
ring-plane offset falls 0.500205→0.088035 Å; the reference relaxes
0.094297→0.088595 Å. Independent cold review passes 70 checks and preserves
all 96 files. Eight separate scalar/count checks reproduce the two endpoints'
0.023303 Å selected-atom RMSD after background alignment. Both endpoints move
from the generator and R values rise, so this is bounded recovery, not exact
truth or experimental PDU/FT_Hg qualification. Reuse this completed control.
Receipts: `coordination-c408-native-review-20261119.json` and
`coordination-c408-endpoint-review-20261119.json` under the Alder artifact anchor.

A04's private four-request input archive is 251,197 bytes and reconstructs
all 36 declared files exactly after staging removal. Complete parent/audit and
environment identity, native regeneration and retirement remain open; see the
[storage contract](metal-campaign-storage.md). Original runs remain untouched.

That rehearsal is followed by the explicit Python input-transport adapter at
`26b0f41c`: 86 focused tests, including corruption, changed/missing source evidence,
pre-expansion byte caps and relocated source/data controls, pass in 51.35 s.
The source-free relocated installation preserves all 345 package files. Public
packing/expansion recovers three saved FT_Hg requests plus their full compact
records from 134,901 bytes (913,800 logical bytes), and one Ag4 request from
130,351 bytes (431,484 logical bytes). These archives differ from the earlier
private layout: they include complete result projections and remain per-run.
Original trials stay exact. This is input recovery, not native regeneration or
standalone scientific replay. See `input-archive-20261119-01/` under the local
Alder artifact anchor for exact commands, source pins and installed records.
The only source follow-up after those checks clarifies a comment about filesystem
expansion versus decoder RAM; its AST is unchanged. Peer static review found no
blocking issue. The focused validation is not a new whole-repository full pass.

## Evening validation and coordination

The private runners under `branch-artifacts/Alder/runners/` used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Alder checkout>/src
/private/tmp/willow-w94-pivot/env/bin/python -B <runner>` for the owned execution
and analysis. Cold recovery reviewers used the same Python with the existing
source-free installation explicitly selected; no source fallback or native job
was allowed during readback. Exact commands, hashes and timings are in each
experiment's progress/readback records.

- A138–A140: linked preparation, three fixed-coordinate Phenix captures and
  matched source/proxy checks; independent review passes. Preserve the initial
  atom-order harness correction; native atom identity, not row index, owns comparison.
- A141–A143: two complete five-cycle open XYZ/group-B jobs, final sealed scalar
  readback and saved-map rendering. Both processes stopped. The Hg capitalization
  and renderer-environment/PHIL-token setup corrections required no extra fit.
- A145–A148: shared archive and installed parent/root recovery; seven adversarial
  dependency checks refuse. The initial unresolved temporary-path attempt is retained.
- A149–A150: exact historical-worker/native-source preflight and two complete
  frozen-f″ reproductions, 180-second bounds, both stopped and exactly reproduced.
  No experiment in this session selects a checkpoint or changes ordinary defaults.

C412's independent cold review preserves the actual checked-preparation PostMR
root, its existing C403 descendant and both new registered chemistry/pair
continuations, all 855 fixed Q/ADP states, original observation/Free-R values,
D:1 protection and original recipe identity. All six requested pair terms already
have native owners; zero terms are added. Poor Rfree remains explicit. This is
shared mechanical evidence, not a qualified FT_Hg or experimental PDU endpoint.
This is modern ordinary continuation evidence, unlike C408/C411's private
synthetic-data parent. Root-free archive closure and Refine Doctor forwarding
remain separate. Receipt: `coordination-c412-review-20261119.json` under the
Alder artifact anchor.
C413 `1a4094fd` adds the shared literal plane reader on Cedar. Its final review
reuses 55 source and 55 relocated installed checks plus seven models/nine planes;
an independent missing-centre counterexample now passes without changing the
fitted plane. Exact FT_Hg model bindings reproduce the common-plane RMS values
**0.026598→0.010827 Å (DF)** and **0.008082→0.008355 Å (DT)**. These include the
recorded ten members, including C1′, and differ from ring-only fits. Symmetry
context and native residuals remain unassessed. No Alder runtime adoption follows.
Receipt: `coordination-c413-review-20261119.json` under the Alder artifact anchor.
C415 `a1620839` then qualifies explicit Python Refine Doctor forwarding of that
ordinary declared-site observation, preserving defaults and counted-ancestry refusals.
Its 80 focused tests plus 10 subtests pass. One bounded native standard group-B
trial preserves the selected PostMR root, named parent and measured inputs;
independent sealed-trial/plane readback preserves all 302 dataset files. Lower
Rfree accompanies a slightly worse terminal plane departure, so recommendation
is not geometry acceptance. These are substituted-scaffold PDU mechanics, not
experimental PDU/FT_Hg validation. The first setup attempt stopped before native
work because its version-string assertion expected a build suffix; it is retained.
Receipts: `coordination-c415-static-review-20261119.json` and
`coordination-c415-native-review-20261119.json`. No Alder runtime adoption or
separate installed/full-suite claim follows from this peer review.

The native Doctor check also identifies a separate counting issue: its ADP
eligibility ratio uses assigned flag groups rather than measured observations.
Rowan owns that correction. Existing metal XYZ/f″ adapters use the audit for flag
validity and do not consume that ratio; tonight's explicit group-B/f″ requests
are unaffected. Preserve the valid historical flag statistics and introduce an
explicitly measured-data count through its own qualification.
C414 supplies the modern-root dependency census for the existing C412 lineage;
its ten returned endpoint inputs omit most preparation/ancestry evidence.
The [storage contract](metal-campaign-storage.md#modern-checked-parent-dependency-boundary)
records the measured scope and next bounded parent-validation design.
W154's independent static/published-payload review finds no blocker in separate
model/map labels and confirms unchanged scientific display fields. Its completed
source/installed tests are reused; no renderer adoption or browser/GPU claim.
Receipt: `coordination-w154-review-20261119.json` at the same anchor.
W155's separate prescribed complex-F contrasts show that displacement, excess
model occupancy and an ADP mismatch can each produce negative density at P.
Independent cold checks preserve its six original files and exact source/variant
identity; the original version API field is empty and remains an explicit limit.
These are synthetic, commonly normalized complex differences, not experimental
Fo–Fc attribution or detector calibration. Receipt: `coordination-w155-review-20261119.json`.

The later isolated shared-reader rehearsal combines baseline `fb4f93d7` with
only the eight source/test files from C413 `1a4094fd` and C415 `a1620839`.
Alder's active scientific source remains unchanged. Two Doctor regression probes
fail on the baseline before the new option exists. On the private candidate,
**2,761 tests plus 70 subtests pass in two bounded parts**: 2,101 tests/50 subtests
before a graceful time-bound interruption, then only the 660 unfinished tests/20
subtests. All 1,505 candidate files remain exact. This is complete coverage of the
selected 80-file workflow/direct-consumer scope, not an uninterrupted profile run
or a full-suite pass. The earlier restricted-environment attempt retains its
eight process-inspection/termination failures and partial results; corrected
process permissions precede the successful checks. No scientific refinement runs.

The relocated installed candidate has **346 exact package files**. With original
build/install/development-source paths unavailable, it reproduces two existing
FT_Hg plane reports, recovers four old frozen-f″ requests and verifies all 35
referenced input files. Invalid Doctor observation intent refuses before work
allocation. The original geometry evidence is deliberately available; old f″ run
paths are denied. This qualifies those installed interfaces, not a self-contained
scientific archive, accepted geometry or general deployment. The explicit pinned
NARestraints dependency remains available. No new combined full gate or active
runtime integration is claimed; later Cedar fixes are outside these source pins.

Exact source patches, manifests, commands/environments, failed/partial results,
XML, split coverage, wheel and installed probe are retained under the Alder
artifact anchor `shared-readers-integration-20261119-01/`. Runners A157–A164
record the preparation, bounded execution, cold review and owned-scratch seal.
All recorded rehearsal processes stopped; only its owned private workspace was
retired (1,115,855,482 logical bytes), preserving 29 evidence/package files and
all original scientific runs. The small `mechanics.html`/`mechanics.json`
addendum beside the evening checkout records this result without changing the
original science report.
Reuse this evidence before scheduling another unchanged check. W153's separate
saved-stage review verifies 84 native rows and keeps initial scaling, XYZ steps
and final scaling distinct; the endpoint missing-work observation does not prove
stagewise reflection identity. Its two `coordination-w153-stage*` receipts remain
local, with no new fit, convergence claim or change to metal acceptance criteria.

Only documentation changes in Alder this session. Relevant document/link and
whitespace checks suffice; existing source tests and the root handoff's last
integration evidence remain unchanged. All generated science, reports, private
runners and experimental archives stay local and excluded from Git. No schema
migration, production scientific-policy change or existing-run cleanup occurs.

## Next work, in order

1. Reuse the integrated development base qualified by the complete runtime
   execution and reviewed test-only correction under the agreed focused cadence.
   The root handoff preserves exact limits; no fresh full-green result is claimed.
   Do not repeat unchanged controls merely to relabel the original full failure.
2. Reuse the isolated C413/C415 source and installed consumer rehearsal when
   qualifying the next shared integration. Preserve scalar-versus-native-energy
   distinctions, global atom identities, missing evidence and unassessed science.
   Later peer fixes need their own source-bound review; do not build a second
   geometry calculator or repeat unchanged completed cases.
3. Reuse C412's checked-parent ordinary continuation evidence for the next A01
   consumer qualification; continue unresolved open XYZ/B geometry work under
   the existing evidence standards. C415 now qualifies shared Refine Doctor
   declared-site forwarding; consume that patch when integrating the shared
   runtime rather than implementing it again. Routine
   donor-state integration is deferred until after NASolve is built; C409 site
   application is not the immediate gate. Preserve its read-only compatibility
   map and the completed matched neutral/deprotonated research comparison.
   Reuse the completed C397–C399 derivative/restart evidence. The next distinct
   A01 question is the [finite contraction profile](#a01-evidence-audit-and-next-finite-move-experiment),
   with current objective-state capture as a prerequisite; no broad weight,
   derivative, iteration or donor-state matrix is queued.
4. Advance A04 from input transport to complete protected parent/audit retention,
   qualify modern checked ancestry/software identity beyond the successful legacy
   two-case recovery, then the production regeneration/retirement boundary. Keep important nodes protected;
   geometry-moving work retains the stronger shared retention discipline.
5. Return to A02 only with a qualified open XYZ/B endpoint. Keep A05 GUI co-design
   and A07 reconstruction from experimental inputs explicit on the roadmap.

## Deferred post-development request

[A09 — hydration shells and counterion coordination](metal-development-roadmap.md#a09--post-development-hydration-shells-and-counterion-coordination)
records the 19 November request: investigate metal water shells and counterions
such as Mg when resolution is better than 3 Å or the user explicitly enables it.
Explicit, editable coordination spheres distinguish water ligands, other donors
and CoHex ammines. This remains after the main build; it changes no current
priority, scientific gate or runtime behavior. Structural shell changes retain
full geometry-parent protection before later frozen-f″ trials.
The same deferred milestone includes a sub-2 Å water-placement inspector (also
explicitly accessible for approximately 2 Å/noisy cases): bounded recipe batches,
numerical local map/geometry comparison, compact ranked alternatives and
uncertainty-aware review. Map movement, unsettled fits and model-assisted evidence
must remain visible; score calibration and automatic selection are future work.

## Scientific contracts that must survive

- Open XYZ/group-B refinement precedes environmental metal-B preparation. Use
  the actual refined base-only or donor environment, excluding sugar/backbone
  for base means; record inter-base mismatch and the chosen assumption.
- Frozen f″ trials fix XYZ, all ADPs and f′, with Q fixed at each declared point.
  Occupancy fitting is a separately declared stage. Preserve original Free-R,
  observations, wavelength, phase/scattering policies and all background scatterers.
- Cluster comparisons retain signed group/per-element sums and cancellation.
  A fitted f″ sum alone is not a unique count/identity or an acceptance rule.
- Human-solved models are endpoint comparisons, not hidden construction/search
  priors. Their f″ may be missing or from a later deposition refinement.
- Existing FT_Hg N3–Hg–N3 terms and source authority remain unchanged. Source
  distance targets, environmental B and acceptance gates are not tuned to force
  agreement with a reference endpoint.
- Scientific data remain local and immutable; no automatic checkpoint selection,
  new GUI execution route or campaign fan-out is introduced by this integration.

## Validation and evidence navigation

Last separately qualified metal runtime: `e002e2037048a4f5778898c7682174e96da5a01b`,
**6,432 tests and 276 subtests**, plus source-free installed real-data replay
and source/data relocation. Separate Cedar C406 runtime `58965920` passed
**12,043 tests and 293 subtests**, with two expected native opt-in skips.
These passes do not automatically qualify a new integrated revision.

Under the existing local Alder artifact anchor, retain:

- `df-source-native-audit-20261118-01/`: exact input contract, local term audit,
  label controls and checkout validation.
- `coordination-c406-native-review-20261118.json`: independent cold native check.
- `compact-projection-20261118-01/` and `compact-full-suite-20261118-01/`:
  real-data projections, installed checks and exact full qualification.
- `integration-rehearsal-20261118-01/` and `integration-delta-20261118-01/`:
  earlier scoped compatibility, package/relocation and owned-cleanup receipts.
- `integration-20261119-01/`: current combined candidate, exact patches,
  validation ownership/results and delivery status.

Exact historical commands, failed harness attempts and scope limits are linked in
the archived handoff. Publishers refuse old output locations; a replay requires
a fresh owned destination. No raw models/maps/native output are committed.

The earlier geometry checkout is
`ScienceCheckouts/Hazel/2026-11-18_FT-Hg_terms/review.html` beside the repositories;
the compact-record checkout is `ScienceCheckouts/Hazel/2026-11-18_compact/review.html`.
Both remain intact. Today's two-file afternoon checkout is at
`ScienceCheckouts/Hazel/2026-11-19_integration/review.html`. It retains the failed
integration gate explicitly beside measured geometry and storage results; it
provides the evidence trail for the evening report without new native work.
The subsequent mechanics checkout is
`ScienceCheckouts/Hazel/2026-11-19_input-transport/review.html`, with measured
archive sizes, preserved old diagnostic Q/B/f″ values and the scoped C409 result.

The evening checkout is
`ScienceCheckouts/Hazel/2026-11-19_evening-checkout/review.html`, beside its compact
`summary.json`. It links the new donor-comparison figure without copying it and
keeps historical bad-fit regeneration values separate from the new XYZ/B fits.
Source hashes and all four local report links validate; browser visual review is
not claimed. Total new report payload is 90,325 bytes.
