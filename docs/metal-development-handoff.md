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

**A04 remains partial: lean frozen-trial storage.** Read-only inventory, scenario
forecast and lossless compact projection are implemented. Protected shared input
publication, native regeneration, resource budgets and safe retirement remain
separate gates. The integrated shared storage owners must be reused; do not
create a parallel metal archive system or prune old immutable trials.

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

## Next work, in order

1. Complete the coordinated integrated-base review, full regression and installed
   gate recorded in the root handoff. Reuse the existing 755-test and 166-test
   rehearsals as prior evidence, not a substitute for the changed combined gate.
2. Consume the shared source-bound final-site geometry report when qualified,
   preserving scalar-versus-native-energy distinctions, global atom identities,
   missing evidence and unassessed science. Do not build a second calculator.
3. Qualify the needed ordinary preparation/descendant path before another
   structural candidate. Refine Doctor declared-site forwarding remains a
   separately qualified boundary. No repeated weight/derivative sweep is queued.
4. Advance A04 through shared protected inputs and durable compact publication,
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
Both remain intact. Prepare a small new report from today's qualified evidence
for the evening lab checkout; do not rerun science merely to decorate it.
