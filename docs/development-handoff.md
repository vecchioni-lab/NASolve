# NASolve development handoff — Willow

**W289 documentation audit, 2026-11-26.** Latest science: **W288**. Latest
maintained code: **W287**, `f68a6a930d1730553ea63f67cacbdd31cc890600`.
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
| Local native phosphate receiving | Opt-in six-atom source-frame route, exact protected context/data and Cedar image forces | Broad duplex/modified-endpoint motion and ordinary campaign adoption |
| W288 matched-coordinate-weight experiment | Original 2.824 Å gap recovers to 1.61590 Å, near seeded 1.61420 Å; no model selected | Residual torsions near 3σ and Rwork/Rfree about 0.312/0.369; no density acceptance |
| Whole-original-asym diagnostic CIF export | W272–278 preserve qualified source categories, images, tensors and backbone coverage; save/replay/inspect available | Mixed-fragment entity policy, native TLS restart, genuine source/parent join and persistent operation/refine loop |
| W286/W287 connection review | Source/row/evidence-bound unapplied proposals and independent saved-report replay | Explicit metadata authority, application and separate chemistry/export/native admission |
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

1. **Stitching:** use the existing inspector to compare each W288 endpoint with
   its own exact maps, keeping the original assisted map separately labelled.
   Inspect moving phosphates and held sugar boundaries before deciding whether
   to widen the movable region. Preserve observation/Free-R/map provenance and
   noise uncertainty. Do not repeat the matched-weight panel or tune by Free-R.
2. **Pine integration:** agree with Rowan on one authoritative parent/data/metadata
   route into a reviewed immutable child, using source-frame native refinement
   and derived views first. The 3LNA export has strong metadata/scattering evidence
   but no qualified ordinary parent/TLS restart; the genuine PDU parent has missing
   entity fields and unresolved experimental-sequence/physical-oligo authority.
   Choose and bind a supported route before another metadata writer or GUI action.
   Whole-asym diagnostic export must not be advertised as deposition readiness.

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

**No tests, product changes, native fits or merges in W289.** Documentation links,
roadmap synchronization, source entry points and local worktree state were audited.

- W287: ten fail-before regressions, **81 focused source / 81 relocated installed**
  checks; 94 Python module hashes match, genuine 49-row proposal cold replay exact.
  Sources, evidence, selection and existing schemas/defaults stay unchanged.
- W288: two complete five-cycle Phenix **2.2.1-6174** fits after two fresh preflights;
  the earlier exact-frame refusal is preserved. Existing roundoff policy was
  explicitly adopted in a separate successor, not a new tolerance. Both arms share
  117 runtime-source pins, all 862 atoms/856 held XYZ/BQ, 1,909 indices/124 Free-R
  assignments, ten native weight observations, restored hooks and stopped workers.
  Reproduced 116 old term values before measuring 58 new values/six relative signs.
- Earlier C374 joined-package qualification remains the exact historical receipt
  in roadmap evidence `E_C374_JOINED_PACKAGE`, at its recorded W117/C373 pins.
  It is not a current branch merge or qualification of later software.
- Full-suite, skipped-case, native and relocation claims remain bound to their
  exact historical commits. No fresh release-wide PASS follows from focused tests.
  Source-frame installation checks do not make entire scientific runs portable.

## Local science checkout

Latest measured result: ScienceCheckouts anchor
`Linden/2026-11-25_matched-weight-recovery/index.html`, with the Python-openable
ChimeraX comparison beside it. Three model hashes and five view actions pass
headless ChimeraX 1.12; figure rendered and inspected. Fresh interactive browser/
GUI behavior was not tested. Evidence uses NASolve anchor
`branch-artifacts/willow/w288-matched-weight/validation.json`.
Models are linked and checksummed, not copied into the checkout. All previous
checkouts, collaboration notes, failed attempts and unique runs are preserved.

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
