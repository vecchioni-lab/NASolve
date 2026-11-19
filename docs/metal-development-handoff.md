# Metal development handoff — current state

Updated **19 November 2026**. Active feature branch: **Alder**. The
[root integration handoff](development-handoff.md) owns the current combined
source, full validation and delivery. The [A01–A08 roadmap](metal-development-roadmap.md)
owns feature completion. The earlier chronological diary is preserved as
[evidence through 18 November](history/metal-development-handoff-2026-11-18.md),
not a second queue.

## Current scientific and engineering boundary

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
One matched neutral/deprotonated DF–Hg–DT research comparison is approved for a
later session; no job is queued by this documentation update. If that comparison
uses the derived sources, their site-specific aliases, polymer links and
terminal/phosphate context must first pass the shared linked preparation path.
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
all attempts and reconstructs inputs without original-data lookup. Complete shared
parents, native regeneration, campaign budgets and safe retirement remain separate
gates. Do not prune old immutable trials through an input-transport receipt.

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
Routine integration is deferred until after NASolve is built; the later matched
research comparison is separate from product implementation and A01 completion.
Absent H3 coordinates do not establish equivalent heavy-atom restraint chemistry.
The delivered neutral and regenerated definitions differ in local bonds, angles
and plane membership, so those differences cannot all be attributed to H loss.
Preserve the approved plane policy and Hg terms in the matched comparison, record
remaining generation differences, and judge the local heavy-atom response without
assuming a repair. Intent does not establish new numerical targets, formal-charge
readback or the cause of the observed strain. No donor-state candidate is
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

## Next work, in order

1. Reuse the integrated development base qualified by the complete runtime
   execution and reviewed test-only correction under the agreed focused cadence.
   The root handoff preserves exact limits; no fresh full-green result is claimed.
   Do not repeat unchanged controls merely to relabel the original full failure.
2. Consume the shared source-bound final-site geometry report when qualified,
   preserving scalar-versus-native-energy distinctions, global atom identities,
   missing evidence and unassessed science. Do not build a second calculator.
3. Continue A01's ordinary preparation/descendant qualification and unresolved
   open XYZ/B geometry work under the existing evidence standards. Refine Doctor
   declared-site forwarding remains a separately qualified boundary. Routine
   donor-state integration is deferred until after NASolve is built; C409 site
   application is not the immediate gate. Preserve its read-only compatibility
   map for the approved later matched neutral/deprotonated research comparison.
   No repeated weight/derivative sweep or donor-state job is queued now.
4. Advance A04 from input transport to complete protected parent/audit retention,
   then native regeneration before retirement. Keep important nodes protected;
   geometry-moving work retains the stronger shared retention discipline.
5. Return to A02 only with a qualified open XYZ/B endpoint. Keep A05 GUI co-design
   and A07 reconstruction from experimental inputs explicit on the roadmap.

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

The latest geometry checkout is
`ScienceCheckouts/Hazel/2026-11-18_FT-Hg_terms/review.html` beside the repositories;
the compact-record checkout is `ScienceCheckouts/Hazel/2026-11-18_compact/review.html`.
Both remain intact. Today's two-file afternoon checkout is at
`ScienceCheckouts/Hazel/2026-11-19_integration/review.html`. It retains the failed
integration gate explicitly beside measured geometry and storage results; it
provides the evidence trail for the evening report without new native work.
The subsequent mechanics checkout is
`ScienceCheckouts/Hazel/2026-11-19_input-transport/review.html`, with measured
archive sizes, preserved old diagnostic Q/B/f″ values and the scoped C409 result.
