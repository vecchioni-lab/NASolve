# NASolve development handoff

Status: living design notes for decisions that are newer or more specific than the main
architecture documents. Updated 2026-09-11.

Read this together with `docs/architecture.md`, `docs/campaigns.md`, and the
stage-specific design notes. When a decision here becomes implemented and stable, move
its durable contract into the relevant architecture/user documentation rather than
letting this file become a second specification.

## Current architectural position

The linear scientific spine is now implemented:

```text
AutoMR -> PostMR -> conditional AutoSol -> AutoRefine -> Refine Doctor
```

The first live updated Refine Doctor check on QiC completed its bounded sibling trials
and identified `refine-007`, the coordinate-only fixed-scattering branch, as the first
numerical pass. The source/current checkpoint remains unchanged unless the user
explicitly selects a Doctor result. This is evidence that standalone Doctor is
operational, not final validation of every recipe class.

The next scientific validation target is an ordinary/noisy mean-data case
(`IMEAN,SIGIMEAN`), because most intended campaign datasets are ordinary rather than
anomalous. New local test datasets are being staged under `examples/TestSets/`; that
directory was not yet present in the published repository when this note was written.

After standalone Doctor behaves on an ordinary test case, the next major development
block is campaign-level Doctor integration: preset-declared triggers, bounded recipe
budgets, automatic selection only across reviewed passing branches, and an inspection
queue for unresolved datasets. This is roadmap step 4 in `docs/campaigns.md`.

## User-forced base-pair restraint geometry

A new edge case motivates an explicit geometry override that is independent of residue
identity.

The current example is a `G:Z` wobble pair measured at approximately pH 11. In this
context Z is expected to be deprotonated and to present a C-like hydrogen-bonding
geometry. The dataset currently contains the provisional intent line:

```ini
force = G:C
```

The intended semantics are **restraint geometry only**. The chemical/model identity
must remain `G:Z`; `force = G:C` must not mutate Z to C, rewrite deposition identity,
or otherwise pretend the residue chemistry changed. It means: restrain the selected
pair using the reviewed G:C hydrogen-bond geometry because the user is supplying
chemical context that the generic pair guesser does not know.

Initial reviewed force geometries should be hard-coded and small in number. The first
requested templates are:

- `G:C`
- `G:A`
- `G:T`

Unknown or unsupported `force` values should fail closed rather than being guessed.
NASolve should not infer a forced geometry automatically from pH at this stage; the
explicit user request is the scientific decision. Reports should preserve the observed
pair identity, requested force template, source configuration, and the exact restraint
resource/template that was applied.

Implementation location is intentionally open pending inspection. If NASolve can select
or construct the required reviewed geometry cleanly around NARestraints, keep the
special-case policy in NASolve. If NARestraints cannot express the necessary template
without changing residue identity, patch NARestraints at the appropriate geometry
selection layer and retain a version/provenance record in NASolve. Do not modify the
installed NARestraints workbook in place.

For the first pass, hard-coded cases are preferred to a generic inference engine. If
this becomes a recurring requirement, generalize it into an explicit pair-geometry
registry or pair-scoped override schema rather than accumulating ad hoc parser
conditionals.

## Finalization and evidence provenance

A central design rule emerging from Doctor is:

> the best final coordinates do not have to be the source of every final map or piece
> of experimental evidence.

For example, a Doctor branch may improve the coordinate model without performing an
anomalous refinement itself. A compatible earlier refinement may still contain the
useful anomalous difference map or anomalous-scattering benchmark. Finalization must
not discard that evidence merely because a later coordinate-only branch becomes the
selected model.

The future `curate`/finalize layer should therefore assemble an explicit evidence
bundle rather than assuming every artifact belongs to the selected coordinate
checkpoint. At minimum it should be able to record separate provenance for:

- selected coordinate checkpoint;
- primary map-coefficient source;
- authoritative STARANISO observations;
- frozen Free-R source;
- experimental phase source, when accepted;
- anomalous difference-map source (`ANOM`/`PHANOM` or equivalent);
- anomalous-scattering benchmark source, including fitted/calculated f'/f'' metadata;
- restraint/dictionary bundle; and
- checkpoint ancestry and compatibility evidence.

In particular, if the selected final Doctor branch lacks anomalous map columns, curate
should be able to carry forward a compatible anomalous map from an earlier refinement.
Compatibility must be demonstrated from the frozen observation identity/checksums and
checkpoint lineage; do not attach an unrelated MTZ because it is nearby or has matching
labels.

Keep `phase_source` and `anomalous_map_source` conceptually separate. They may point to
the same MTZ, but experimental phases used during refinement and an anomalous
difference map retained for inspection are different evidence roles.

`nasolve show` already opens an additional anomalous difference map at 3 sigma when a
selected checkpoint declares usable `ANOM`/`PHANOM` columns. That viewing behavior is
useful, but curate should eventually consume explicit evidence provenance rather than
reconstructing final evidence from GUI-opening heuristics.

## Refine Doctor follow-up

Standalone Doctor should continue to keep numerical ranking, confidence, and checkpoint
selection separate. A numerical pass is still subject to map/model inspection.

Near-term follow-up remains:

1. validate the ordinary/noisy mean-data path using the new test datasets;
2. debug the provisional `force = G:C` path and determine whether NASolve alone can
   express the requested geometry or whether NARestraints needs a reviewed patch;
3. after ordinary validation, expose Doctor triggers/recipes/budgets through the
   campaign preset and executor;
4. retain explicit reuse of prior fitted anomalous scattering values as a later
   reviewed Doctor capability; and
5. keep broader xtriage/data diagnostics, restraint-alternative diagnosis, chained
   staging, Final Model Doctor, curate/Table 1, and deposition as downstream roadmap
   layers already described in the main design documents.

## Handoff rule

When future work changes any item above, update this file or promote the stabilized
behavior into the relevant architecture document in the same change. The purpose is to
keep recent scientific intent in the repository so a new session or collaborator does
not need chat history to reconstruct why the next implementation step exists.
