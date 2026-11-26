# NASolve development handoff — Willow

**W296 coupled-sugar admission and refinement, 2026-11-26.** Latest native
preflight, refinement and maintained code: **W296**,
`d81ce8ecbe0ae4b1f1cc6a7d1123a39fb0147e60`.
The [audited roadmap](topostitch-roadmap.md) owns status and the next decision;
[periodic evidence](topostitch-periodic.md) and [API contracts](topostitch-preview.md)
own exact methods, commands, hashes and limitations. This handoff is not a run diary.

<a id="read-this-first-current-development-edge"></a>
## Current development edge

The original aims remain: TopoStitch should realize an intended periodic DNA
connection with supported chemistry and diffraction; Pine should offer a faithful
ASU cut with persistent human review and a reproducible refinement child. Both
must work without an AI service. A representation change does not repair a gap.

| Available on the Willow branch | Proven scope | Remaining gate |
| --- | --- | --- |
| Explicit end/image inspection and placement | Registered canonical ends, bounded paired-window proposals and saved previews | Arbitrary-model inference, physical partner capacity, general density-supported deformation |
| Local native phosphate receiving | Default six-atom route plus explicit unphased 19-atom coupled-sugar admission; installed preflight and fit complete with original context/data | Wider paired/base motion, packing acceptance and ordinary campaign adoption |
| W296 coupled-sugar experiment | Original 2.824 Å gap recovers to 1.61293 Å; common-subset local angle maximum improves 1.830→0.571σ; six sugar hands and 843 held atoms preserved | Residual image torsion 2.814σ, held-base tilt near 17.9°, weak sugar density; Rwork/Rfree 0.313/0.366, unselected |
| Whole-original-asym diagnostic CIF export | W272–278 preserve qualified source categories, images, tensors and backbone coverage; save/replay/inspect available | Mixed-fragment entity policy, native TLS restart, genuine source/parent join and persistent operation/refine loop |
| W286/W287 connection review | Source/row/evidence-bound unapplied proposals and independent saved-report replay | Explicit metadata authority, application and separate chemistry/export/native admission |
| W290 endpoint-map comparison | Same 1,909 indices/124 Free-R; P near 2.52σ in both maps, weak fixed sugar support | Explicit coupled-window chemistry/packing before broader native motion; no map-based acceptance |
| W292–W296 coupled-sugar scope | Source geometry, native derivatives, actual live definitions, sugar hands/pucker and C1 plane tradeoff checked; no plane removed | Full returned packing-review intake, physical partner authority and whole-duplex motion remain open |
| W291 pre-motion scope review | Existing terminal/interior windows expose moving residues, fixed anchors/context and adjacent links without rendering | Genuine PDU has no declared duplex partners; wider chemistry/native motion remains gated |
| Offline model/density and cut inspection | Installed renderers, map/model roles, saved preference and trusted export views | General stage/campaign integration and supported human edit/re-enter/refine lifecycle |

**Availability is branch-specific.** The inspected local Pine checkout is still
`d7913ddd95336fddb7cb266b0bc707ffd768d9ab`, Willow's ancestor; it exposes only the
`nasolve` script. Willow adds five `nasolve-topostitch-*` entry points in
`pyproject.toml`. Qualified installed Willow slices do not establish a combined
Pine/Cedar/Alder release. No online PR status, merge or fresh combined regression
was inferred from this local audit.

The [W288 result](topostitch-periodic.md#w288--the-original-pose-catches-up-under-matched-coordinate-weights)
weakens the earlier unique-initialization/basin interpretation of W241: much of
the contrast disappears when coordinate coefficients match. Final endpoints
differ by max 0.06113 Å, RMS **0.03359 Å over the six movable atoms**. The smaller
all-atom RMS includes 856 unchanged atoms. Native bulk/scale and likelihood
nuisance state were not frozen. This local experimental receiver is not a new
maintained fixed-weight product mode or recommended production weight.

## Next decisions

1. **Stitching:** use W296 as the new unselected local baseline. The 19-atom
   receiver now works; do not repeat its derivative checks, weight panel or fit
   without a new question. Source is the registered 5W6W-derived central-strand/PDU
   model, canonical DC B1 / DA B7 endpoints, held PDU B4—not FT or 8D93. The sugars
   improve local angles and C1-to-base plane distances, but cannot realign held
   bases. Next define a source-authorized base/partner-inclusive window and qualify
   returned packing observation with Cedar. Its fixed exclusion/shell-table reader
   is passive; its ASU pair helper performs extra evaluations in an isolated worker.
   Do not insert it into the active guard or relabel partial live capture as complete.
   Both endpoint maps use 1,909 reflections/124 Free-R; weak/negative sugar density
   remains. No Free-R-driven trial search or automatic selection.

   **Next-window readiness audit:** W296's frozen discovery contains only B1–B7,
   no declared duplex pairs, incomplete pairing coverage and two representation
   boundaries. Its registration maps those seven sites only; the A-chain partners
   are unmapped. This is distinct from W291's four-route parent. Native A15/B1
   and A9/B7 plane restraints are useful observations, not physical pairing or
   oligo authority. First extend source-bound registration and review partner,
   junction and continuation declarations; an empty protected-site list does not
   prove there are no junctions. Reuse `plan_editable_windows` and
   `inspect_bend_window` for the source-frame scope and fixed neighbours. The latter
   does not traverse representation continuations or changed images, so periodic
   realization remains a separate qualification before wider native motion.
   No new fit or repeated missing-partner test was needed for this audit.

2. **Pine integration:** Rowan/Linden agree to use the genuine PDU ordinary parent
   with its proven data/thermal route. Use source-frame native refinement and
   derived views; keep physical strand/entity assignments unresolved without a
   designed-oligo source. Native soft pair restraints do not supply that authority.
   W291 confirms the concrete boundary: four routes, no declared duplex partners;
   the normal window inspector reports that absence without selecting a window.
   Whole paired-residue motion needs reviewed partner/image context. The W292
   narrower fixed-base proposal is a different source/model and does not fill
   that metadata gap or inherit this checkpoint’s admission. The 3LNA export remains
   the strong
   metadata/scattering control without a qualified ordinary parent/TLS restart.
   Whole-asym diagnostic export is not deposition readiness.

## Pine recuts and shared ownership

- **Willow/Pine:** logical construct/site/image correspondence, explicit cuts and
  bounded motion, inverse mapping, coordinate/ADP transport, review/inspection.
  Preserve true nicks and unknown partners; a displayed chain start is not a terminus.
- **Cedar:** prepared chemistry, component identities, native bond/angle/torsion
  forces and exclusions, ordinary checkpoint/process ownership and deposition
  readback. Keep P/OP1/OP2 for declared continuations; do not activate a bond alone.
- **Alder:** protected metal/cluster hypotheses and scoped B/Q/f′/f″ authority.
  Reuse the qualified `NativePhasedGuard` and `audit_masked_endpoint` interfaces;
  a six-atom mask or returned mapping does not authorize wider or metal motion.
- **Shared GUI:** reuse the W149/W154 density inspector and W277/W278 saved-export
  view. Scope approval, source-bound preference, model selection and native
  execution are distinct. No second map parser, symmetry engine or protection owner.

The [connectivity contract](construct-registration.md#shared-periodic-connectivity-intent-pine-topostitch-and-cedar)
and [pre-deformation contract](topostitch.md#preserve-chemistry-before-a-bend-w175-integration-contract)
remain authoritative. Re-entered edits require checked inverse mappings; identity,
intent or topology changes need fresh qualification. Deposition output additionally
needs sequence/entity provenance, truthful connection types, transformed annotation
references and thermal/TLS semantics. File readback alone cannot prove those.

<a id="validation-and-scientific-interpretation"></a>
## Validation and compatibility

**W296:** 219 ordinary-Python focused tests pass with one native-only skip;
**3,073 tests + 238 subtests, no skips** pass in the native full suite. After
removing original build/install paths, **220 installed focused checks**, CLI help,
zero-cycle preflight and one complete five-cycle/100-iteration-cap Phenix
**2.2.1-6174** fit pass. Clean Cedar
`2d6de758e40059c4346d9cb80354741bf5456313` was pinned and independently reproduced
from Git. All source/input bytes remain unchanged; hooks restore and workers stop.
ChimeraX **1.12** loads three models and executes five controls headlessly; 35 cold
artifact/reference/payload/link checks pass. Interactive use is not newly certified.

`movement_scope` is an additive schema-1 request field; omission keeps the six-atom
route. Coupled scope is currently unphased and requires complete canonical endpoint
chemistry. The exact native definitions, existing masked-coordinate guard and
Cedar pucker/plane readers remain the owners. No optimizer, tolerance, force kernel,
checkpoint adoption or combined release change. Read
[W296 evidence](topostitch-periodic.md#w296--admit-coupled-sugars-through-the-installed-native-route)
for exact commands, schemas, source identity, failed/interrupted evidence and all
remaining scientific limits. Generated models, maps and reflections remain local.
Installation relocation is not a whole-scientific-run portability claim.

**Reused evidence:** W293's 19-atom derivative qualification and W294's explicit
frame policy were not rerun as new numerical research. W295's unchanged shared
source reader still owns phased source-array handling; its FT equivalence check
created no parent or fit. W288 remains the matched six-atom comparator. Historical
validation counts and exact receipts stay in the roadmap and periodic evidence,
not duplicated here as a second chronology. The earlier C374 joined-package receipt
is not a current merge or qualification of later branches.

## Local science checkout

Latest checkout, at the ScienceCheckouts anchor:
`Linden/2026-11-26_coupled-sugars/index.html`. It links the offline 43-atom density
comparison, a Python-openable three-model ChimeraX comparison, native PDB, figure
and exact evidence under NASolve anchor
`branch-artifacts/willow/w296-coupled-admission/`. The small checkout links large
artifacts instead of copying models/maps. All references are checksummed; previous
checkouts and failed attempts remain intact. `verification.json` owns the cold
checks. The browser view is filled output, not an unfilled developer template.

## Scientific limits and demonstration gates

A recovered phosphate junction is not a completed sticky-end duplex: oriented
base-pair/register assignment, planes, stacking and paired-window geometry remain
separate requirements. General straight→bent, bent→straight and redistributed-curvature recovery, internal
stacking, density calibration and campaign inference remain open. Useful local
recovery does not close those gates. The geotest altered-arm panel remains a final
end-to-end demonstration, including X11_18 in P4_3 with its original data/setting
lineage preserved. Blunt contacts, three post-first-refinement triangle orientations
and specified local helicity remain separately scoped plans.

Maximally fragmented ASU refinement stays behind mixed-image output, chemistry and
restart gates. LNA is a later chemistry extension. Metal B/Q/f″ recovery is tabled
until Alder has a qualified nonzero-f″ case and identifiable recovery tools; query
Hazel then. Neither a fixed-zero-f″ control nor another stress suite substitutes
for closing current scientific gates. See the [publication shortlist](campaign-model-roadmap.md#nasolve-publication-demonstrations).

## Earlier implementation and bounded controls

Use W-number entries in the [machine roadmap](topostitch-roadmap.json) and the
periodic/preview ledgers; do not repeat a closed probe because it was removed from
this summary. The complete pre-audit handoff and index are recoverable in Git at
`d30cd0e489898a1c434e7a87fe57fa27622e035e`. No scientific evidence was deleted.

## Historical Pine references

The inherited October queue is historical context for this branch, not a current
Willow action list. Main Pine's local handoff still carries that date; consolidation
requires its owners, not an implicit rewrite from Willow.

### Pine close-out

See the [archived Pine gates](history/development-handoff-2026-10-08-pre-consolidation.md#pine-close-out).
They do not establish current Cedar or Pine completion.

### Nine-member baseline results

See the [archived baseline](history/development-handoff-2026-10-08-pre-consolidation.md#nine-member-baseline-results).

### After Pine: blind AlphaFold geometry campaign, then Scout

See the [historical sequencing](history/development-handoff-2026-10-08-pre-consolidation.md#after-pine-blind-alphafold-geometry-campaign-then-scout)
and current [registration contract](construct-registration.md). Predictions remain
candidate models; preserve frozen sequence/data/Free-R and blind-selection policy.

## Work discipline and doc ownership

Follow [AGENTS.md](../AGENTS.md) and [collaboration.md](collaboration.md). Keep this
handoff short: update current decisions, link exact evidence, and avoid accumulating
another chronological ledger. Do not add guard/report layers without a concrete
missing boundary. Preserve original inputs, native failures and other authors'
dirty work; publish scientific payloads only with explicit project authorization.
