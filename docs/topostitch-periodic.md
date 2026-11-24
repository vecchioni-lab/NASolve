# TopoStitch periodic search and read-only inspector

Implemented on Willow, 2026-11-13. This extends the [coordinate adapter](topostitch-coordinates.md)
with metric-bounded symmetry-image search and an installed inspection command.
It does not discover duplexes automatically, choose partners, construct models,
recut an ASU, refine or change checkpoints. All candidates require review.

## Install and inspect

Install the optional crystallography extra in the NASolve environment:

```sh
python -m pip install ".[topology]"
nasolve-topostitch-inspect model.pdb ends.json --radius 20 --periodic
```

`python -m nasolve.topostitch_inspect` is the equivalent module invocation.
Omit `--periodic` for the existing same-frame coordinate screen, which needs no
Gemmi. The radius is explicitly supplied in Angstrom, not a chemical ideal.
The command prints JSON to stdout and errors to stderr (exit 2); it writes no
files. Shell redirection, if desired, is the caller's output decision. There are
no apply, refine or select actions. The main `nasolve` CLI remains untouched.

Gemmi is an optional `topology` dependency (`>=0.7.5,<0.8`); this patch was tested
with 0.7.5. Default NASolve installations and Cedar's environments are unchanged.
For the full development test profile use `.[test,topology]`; lean installations
skip the Gemmi-dependent tests while still testing the missing-extra diagnostic.

## Selected atom-image audit

```sh
nasolve-topostitch-inspect model.pdb ends.json --radius 20 --periodic \
  --audit-image 0 --coincidence-tolerance 0.01 --max-atom-tests 2000000
```

`--audit-image` selects an index from the freshly recomputed candidate list.
The exact source, assignment and search hashes bind that index; it is not a
persistent connection identifier. Coordinate, registered and discovery inputs
are supported, and the option composes with contacts, pairings and windows.
The Python API is `nasolve.topostitch_images.inspect_periodic_image_identity`.
No externally supplied candidate report is accepted by that public API.

The added `selected_image_identity` object has schema 1 and kind
`topostitch-selected-image-identity`. It records the present atoms in both ends'
overhang, terminal pair and inner pair. Two separate observations are retained:

- **Orbit contacts:** for every selected source atom pair, test all space-group
  operations and metric-bounded lattice translations for coordinate coincidence.
  Nonidentity images fixing the same source atom are stabilizer observations;
  coincident orbits of different source labels remain ambiguous distinct labels.
- **Selected-image overlap:** compare the source end with the exact chosen target
  image. Retain its lattice translation; do not wrap it back into the unit cell.
  Coincident end centers alone neither prove nor disprove atom overlap.

The default observation tolerance is 0.01 Å, configurable in `(0, 0.05]`, with
recorded 1e-7 Å numerical padding. This is not a clash threshold or a chemical
acceptance cutoff. Near coincidences are not transitively merged. The work budget
counts every atom-pair/operator screen and explicit distance evaluation; each
output section is capped at 10,000 coincidence records. Exceeding a budget fails
without partial JSON. Unknown/invalid selected occupancy leaves the audit
`UNASSESSED`; partial occupancy remains a review condition. Missing atoms are not
invented, and unselected crystal atoms are outside the audit's scope.

`SELECTED_COORDINATES_DISTINCT` describes only the inspected coordinates.
`COINCIDENCE_OR_OCCUPANCY_REVIEW` retains ambiguity. In either case,
`physical_identity_validated`, `geometry_validated` and `runtime_authority` stay
false, and original candidate approval fields are unchanged. This first slice
supplies F02 evidence; global partner capacity, full molecular orbit identity,
Pine cut/scattering invariance remain open. Periodic fitting now consumes the
source audit as a conservative precondition; see the preview guide.

## Assignment manifest

The input is a strict schema-1 `topostitch-end-assignments` object:

```json
{
  "schema_version": 1,
  "kind": "topostitch-end-assignments",
  "model_sha256": "REPLACE_WITH_EXACT_64_CHARACTER_LOWERCASE_MODEL_SHA256",
  "ends": [
    {
      "end_id": "arm-a",
      "overhang_sites": [
        {"chain": "A", "residue_number": 1},
        {"chain": "A", "residue_number": 2}
      ],
      "terminal_pair": [
        {"chain": "A", "residue_number": 3},
        {"chain": "B", "residue_number": 3}
      ],
      "inner_pair": [
        {"chain": "A", "residue_number": 4},
        {"chain": "B", "residue_number": 2}
      ],
      "polarity": "5prime",
      "state": "available"
    }
  ]
}
```

This illustrates shape only; these sites are not a recipe for a real structure.
Use the actual model digest and actual assignments. Overhang order is explicitly
5-prime to 3-prime; pair order follows the same two strands from the terminal
pair to the next interior pair. Site objects optionally include `insertion_code`.
End state defaults to `available`; declare `free`, `connected` or `unknown` when
appropriate. Missing required fields, duplicate JSON keys, unknown fields and
unsupported schema versions are errors, not ignored future permissions.

The model path is an explicit CLI argument, not discovered from the manifest or
stored as an absolute operational reference. The report retains the model hash,
parsed assignment hash and exact assignment-file hash. A report is evidence, not
a standalone resumable checkpoint: a future GUI must resolve its model through
verified run/dataset anchors and hashes, or an explicitly supplied matching file.

## Logical end definitions through construct registration

Coordinate manifests remain supported unchanged. For end roles written against
logical construct sites, pass the existing schema-1 Pine registration explicitly:

```sh
nasolve-topostitch-inspect model.pdb logical-ends.json \
  --registration registration.json --radius 20 --periodic --contacts --pairings
```

The logical manifest has `schema_version: 1`,
`kind: "topostitch-logical-end-assignments"`, `model_sha256`,
`registration_sha256` (the exact registration **file bytes**) and `ends`.
Each end has the usual ID, polarity/state and three site lists, plus an explicit
`copy_id`. Its sites are logical strings such as `"strand-a:12"`, rather than
coordinate-site objects. For example, an end row is:

```json
{
  "end_id": "arm-a", "copy_id": "copy_1", "polarity": "5prime",
  "overhang_sites": ["A:1", "A:2"],
  "terminal_pair": ["A:3", "B:3"],
  "inner_pair": ["A:4", "B:2"]
}
```

`nasolve.topostitch_registration.resolve_registered_ends` validates the existing
registration contract, binds it to the actual PDB checksum, and checks selected
registered residue identities against the coordinate bytes and target codes.
It returns coordinate assignments plus schema-1
`topostitch-registration-end-map` evidence. Multiple copies are explicit; logical
order survives renamed/split coordinate chains and supported insertion codes.
This does not infer covalent continuity or make a split chain into a chemical nick.

Missing mappings and identity conflicts retain unresolved ends and their reasons.
Unknown logical/copy identifiers are input errors. Partial selected copies keep
coverage incomplete, even when some ends can be inspected. The outer report's
`registration_assessment` retains every requested end; its proposal state remains
`INCOMPLETE_ASSESSMENT` when mapping coverage is incomplete. Existing coordinate
and candidate assessments remain visible for the resolvable subset.

The assessment records a canonical-content registration fingerprint separately
from `registration_file_sha256`, plus logical assignment content and its hash.
Paths remain explicit CLI inputs; reports do not require an original filesystem
location. No existing registration/checkpoint schema is changed, and no mapping,
chemistry or source model is edited. This first adapter resolves identity-image
sites only: a periodic recut realization and automatic end detection are later
capabilities, not consequences of successful label mapping.

## Discovering ends from declared topology

A third input kind, `topostitch-end-discovery-input` (schema 1), derives logical
end assignments instead of requiring each overhang/anchor to be written out.
It uses the same explicit `--registration` path and file/model SHA-256 fields.
The remaining fields are:

```json
{
  "copy_id": "copy_1",
  "pairing_inventory_complete": true,
  "strands": [
    {"strand_id": "long", "sites": ["A:1", "A:2", "A:3", "A:4"],
     "five_prime_boundary": "chemical", "three_prime_boundary": "unknown"},
    {"strand_id": "short", "sites": ["B:2", "B:3"],
     "five_prime_boundary": "unknown", "three_prime_boundary": "chemical"}
  ],
  "duplex_pairs": [["A:3", "B:3"], ["A:4", "B:2"]],
  "protected_sites": [],
  "max_overhang_length": 12
}
```

This is a shape example, not a real-structure recipe. Strand sites are explicit
chemical 5-prime to 3-prime order, independent of coordinate chain names or
residue numbers. Boundary meanings are `chemical`, `representation` or
`unknown`; only declared chemical termini support a discovered overhang. Route
fragments can have unknown/representation boundaries but cannot silently turn
those cuts into chemical termini. Protected sites mark junction boundaries.

`pairing_inventory_complete` defaults to **false**. Set it true only when the
declared duplex-core pairing inventory is complete within the supplied route
scope. A partial contact-detection list does not establish that all other bases
are unpaired. Without that declaration, missing pairing evidence remains
`PAIRING_COVERAGE_UNKNOWN` and cannot create an overhang assignment.

`nasolve.topostitch_discovery.discover_logical_end_assignments` follows adjacent
antiparallel core pairs to their boundaries. It needs two distinct paired steps,
exactly one unpaired terminal tail, and chemical boundaries on both outward
routes. It derives ordered overhang/terminal/inner sites and 5-prime/3-prime
polarity. Stable IDs depend on logical roles, not coordinate labels. Internal
unpaired intervals, changed pairing routes, two tails, isolated pairs, protected
junctions and length limits remain explicit boundary outcomes. No atoms are
built, phosphate bonds added, or coordinate-based chemical topology inferred.

The schema-1 `topostitch-logical-end-discovery` assessment is nested in
`registration_assessment.discovery_assessment`. It retains normalized input,
its fingerprint, all boundary outcomes, unanchored strands and the derived
logical assignments. Incomplete discovery or mapping keeps the outer proposal
state incomplete while still showing assessable candidates. This is discovery
**within declared topology**, not yet an unattended end finder from an arbitrary
PDB or an automatic pairing/strand-registration engine.

## Editable-window proposals

With a discovery manifest, add `--windows` to describe increasing paired windows
for each discovered end. `--max-window-pairs` defaults to 12;
`--fixed-anchor-pairs` defaults to 2. Each proposal moves the overhang and outer
whole pairs while holding its innermost pairs fixed. Expansion stops before a
protected junction, changed pairing route or route-scope boundary. Too little
paired context yields an explicit outcome rather than a guessed anchor.

The API `plan_editable_windows` in `nasolve.topostitch_discovery` replays and
checks the discovery evidence before producing schema-1
`topostitch-editable-window-proposals`. It records logical movable/fixed sites,
stable window IDs and why expansion stopped; no window is selected. This is a
movement-scope proposal, not coordinate mapping, motion, closure feasibility or
combined-window overlap validation. A later geometry trial must qualify those
properties against the actual source model and periodic target.

Optional `do_not_connect_sites` in discovery input marks matching overhang or
terminal-pair sites as declared free ends. They remain visible with `state=free`,
but candidate search and window planning exclude them. Unmatched declarations
remain visible and keep coverage incomplete. This is separate from protected
junctions. Earlier schema-1 discovery reports without this additive extension
remain readable by the window planner: their original fingerprint is checked,
and only the missing free-site fields receive empty in-memory defaults.

## Periodic backend

`nasolve.topostitch_periodic.propose_periodic_connections` accepts explicit
`DuplexEnd` records, six cell parameters, a space-group name, source model hash,
search radius and budgets. It validates these inputs and obtains the full
space-group operations and cell transforms from Gemmi. Cell metrics must be
positive/nondegenerate and compatible with the named setting. This first DNA
scope permits only Sohncke groups; improper operations need a separate chirality
policy. Coordinates outside the reference unit cell are supported within a
finite numerical range (fractional components no larger than 1e6 in magnitude).

For each compatible endpoint pair and operator, the search bounds every lattice
translation that could lie in the Cartesian sphere. If F is the fractionalization
matrix, a displacement of length at most r has fractional component i bounded
by `r * norm(F.row(i))`. The finite translation box follows from this bound,
then each image receives an actual Cartesian-distance check. This handles skewed
cells and nonlocal cell shifts without a fixed 27-cell assumption.

Canonical full-overhang reverse complementarity and matching overhang polarity
remain screening conditions. Unknown chemistry and declared free/connected ends
are excluded. Partial register and noncanonical pairing searches remain future
work. The endpoint origin, not each constituent atom, is the searched position.

`max_pairs` bounds pairs including self-images. `max_image_tests` bounds the
translation-box evaluations, including images later rejected by the sphere test.
Exceeding a budget fails the request without returning a partial successful
report. Empty boxes are skipped before materializing ranges. Oversized numeric
bounds fail cleanly. Cartesian tolerance is 1e-7 Angstrom and fractional box
padding is 1e-9; these are recorded numerical tolerances, not geometry targets.

## Image identity, reciprocal edges and uncertainty

A candidate records both endpoints, transformed target position, distance,
sequence-index pairing and the exact target image:

- wrapped symmetry operation string and integer lattice translation;
- full unwrapped operation string;
- integer rotation/translation numerators with their common denominator;
- the exact inverse operation for reciprocal inspection.

No donor operator index or rounded Cartesian distance is used as image identity.
Different logical endpoints have one fixed source ordering. For self-image edges,
the identity copy is excluded and a transformation/inverse pair is represented
once. Nonzero lattice winding remains valid. Inputs and candidates have stable
ordering; no nearest-neighbor selection is made.

This is **not complete atom-orbit deduplication**. Special-position stabilizers
may identify apparently different operator descriptions; coincident reference
points may be the same physical site or overlapping structures. The report marks
image distinctness as unvalidated, retains the alternatives and warns against
counting them as independent evidence. Full atomic/registration identity is
needed before topology adoption.

There is also a capacity issue for a self-end edge: if forward and reciprocal
operators differ, the periodic orbit may require two neighbors at the same
one-partner overhang. Such edges carry an explicit warning. An involutive
twofold image is not blanket-rejected, but still needs image-distinctness and
geometry validation. This search enumerates hypotheses, not globally compatible
connection schemes. Every candidate requires global assignment review.

## Source-verified PDB integration and preview frames

`inspect_periodic_end_assignments` uses the existing exact-checksum coordinate
adapter, then re-verifies the PDB bytes for the crystal header. It requires
exactly one CRYST1; missing symmetry never defaults to P1. When SCALE records
are present, all three must match conventional cell fractionalization with zero
translation (within serialization tolerance). Nonstandard/incomplete SCALE is
rejected until a dedicated coordinate-transform implementation exists.

The result includes both coordinate and periodic reports. Missing/unassessed
ends remain visible, so the top-level result stays `INCOMPLETE_ASSESSMENT` even
when other candidates exist. The declared search completeness refers only to
the supplied assessable ends, compatible sequences and radius; it does not claim
all crystallographic connections have been found.

For each candidate the wrapper transforms the observed target end-frame axes
with the operator's Cartesian rotation and translates only the origin. It reports
outward-axis and source/target facing angles for display, not acceptance tests.
Coincident reference points have undefined facing angles (`null`). These are not
helical phase or backbone-closure measurements. The GUI can show the actual mate
and a dashed proposal using backend-computed frames, without inventing edits.

All report variants retain `runtime_authority=false`, empty `changes`,
`execution_state=NOT_ATTEMPTED`, `review_state=UNREVIEWED`, no selected candidate
and required inspection. The coordinate report is byte-verified; the nested pure
screen identifies its source digest but performs no I/O itself.

## Optional contact observations

Add `--contacts` to measure the candidate overhang pairs in the current model:

```sh
nasolve-topostitch-inspect model.pdb ends.json --radius 20 --periodic --contacts
```

`nasolve.topostitch_contacts.inspect_end_contacts` uses the same verified source
and candidate search, then transforms each target atom by the exact candidate
operator. It reads the installed NARestraints canonical AT/GC recipes and the
bundled residue-role library. It records the effective role/recipe snapshot,
its SHA-256 and NARestraints version, so a changed mapping cannot silently look
like the same reference configuration. It does not read a user-local workbook.

The additive `contact_assessment` contains schema-1
`topostitch-contact-observations`: per-candidate/per-residue-pair atom identities,
measured heavy-atom bond distances and angles, reference ideals/sigmas and signed
deviations. Six-member ring normals, plane offsets and ring-plane residuals are
observations only. Atom references distinguish the source and transformed target
image, including when a recipe's role order reverses their order.

Missing exocyclic atoms, unusable occupancies and degenerate angles remain
explicit incomplete measurements with `null` values, never zero-distance
contacts or silently omitted evidence. Other available measurements survive.
The existing adapter still rejects ambiguous conformers or duplicate sites.
Reference sigmas are not calibrated acceptance cutoffs. No hydrogen placement,
stacking, backbone torsion, packing or diffraction check is implied, and no
candidate is accepted, rejected or ranked by this layer. Default reports are
unchanged unless the flag is supplied. Neither old checkpoints nor assignment
manifests need migration.

## Optional pairing alternatives

Add `--pairings` to enumerate mutually compatible choices under the initial
one-partner-per-overhang rule. It composes with `--periodic` and `--contacts`.
`--max-alternatives` bounds alternatives per connected group (default 256), and
`--max-pairing-states` bounds total enumeration states (default 100,000).
Exceeding a budget fails with no partial JSON result.

The additive schema-1 `pairing_alternatives` report records the exact candidate
report fingerprint, independent connected groups and every admitted matching
within each group, including empty and partial matchings. A whole-structure
scheme chooses one alternative from each group. `scheme_count` gives the product
without materializing it: forty independent pairs need eighty stored choices,
not a trillion complete scheme records. No nearest/most-connected choice is
preferred; `selected_scheme` remains null.

The API is `nasolve.topostitch_pairings.describe_pairing_alternatives`. It checks
candidate input fingerprints, endpoint/register consistency and reciprocal image
operators. It analyzes the declared graph, not source coordinate bytes. The
outer inspector provides the verified model context. Distinct image choices
for the same two ends compete for their capacity. An involutive self-image can
consume one logical end; non-involutive self-images are listed as deferred for
atom-orbit/capacity review, not declared chemically impossible. Special-position
physical equivalence is still unvalidated for every scheme. Completeness means
all matchings of the admitted graph, not all physical connections in a crystal.
This is a combinatorial aid for review, not an adopted connection scheme,
scientific assignment, campaign permission or reconstruction input.

## Records and compatibility

New descriptive kinds are `topostitch-periodic-candidate-report` and
`topostitch-periodic-coordinate-report`, each schema 1. The strict input manifest
is also schema 1 but has a different kind. No old report, checkpoint, campaign
recipe or frozen attempt is migrated or reinterpreted. The installed inspector
is additive; the default NASolve dependency set is unchanged. Source changes are
isolated in new TopoStitch modules plus package metadata. Cedar's code, selected
bundles and publication interfaces are not consumed or modified.

No generated scientific data are included. Unit tests use synthetic endpoints
and synthetic PDB rings. Native diagnostic/placement evidence is recorded
separately below; no successful physical repair or Coot acceptance is claimed.
The audited roadmap owns the remaining image, capacity and geometry gates.

## Current validation receipt — 2026-11-14

**W52 checkpoint:** nine new tests; complete Willow 1,477 plus 229 subtests;
installed/relocated shared-owner tests178. The prior package lacks the new module.
The complete public preview and its earlier graph/relabel/orbit observations
reproduce after relocation with original paths blocked and the old checkout absent.
Five command helps, lean import and Python 3.10 syntax pass. Commands/environments
follow W48 below, using `tests/test_topostitch_recut.py` for the focused suite.
Wheel SHA-256: `2113d2951694ea27b3a18815318551574cb0afd19097e57689fcaf148b90d9c6`.
No Phenix/Coot execution, native enforcement or coordinate writing is introduced.

A subsequent temporary installed compatibility check combines pinned Cedar C295
`c74149196e1d40722f2bb20f6b00303ba7da9c74` with the 23 Willow TopoStitch modules:
264 focused shared-owner/API tests pass and the complete public registered preview
reproduces exactly after relocation. Commands use the same Python/pytest settings
above against the installed temporary package and copied focused test files;
exact arguments and module fingerprints are retained locally. This is not a
branch merge, full combined-suite qualification or combined CLI/dependency-metadata
claim. Cedar's package metadata was preserved unchanged.

**W50 checkpoint:** 76 focused graph/image tests; complete Willow 1,468 plus
229 subtests; installed/relocated shared-owner tests 155. The ten new tests fail
against W49. Both public-derived orbit reports reproduce exactly with original
paths blocked and the old temporary checkout absent. Five command helps, lean
import and Python 3.10 syntax pass. Commands/environments follow W48 below,
with focused arguments `tests/test_topostitch_images.py tests/test_topostitch_graph.py`.
Wheel SHA-256: `419ca51af0ac7eccb128f9d12a2639316737987f0c01d7a3721f150aa0b4380d`.
This read-only change needs no Phenix/Coot execution; it changes no native policy.

**W49 checkpoint:** 34 graph tests pass; installed W48 fails the 14 new tests and
passes the 20 existing tests. Complete Willow passes 1,458 plus 229 subtests;
installed/relocated graph and shared-owner checks pass 127, with byte-identical
public registered graph and relabel preview after the old checkout is absent
and original source paths are blocked. The commands/environments are the same
as W48 below, using the W49 source and wheel. Five entrypoint helps, lean import
and Python 3.10 syntax pass. Wheel SHA-256:
`db67f84b3f452b301cd30483628e1d4d8d1a0e11e24753d8510c004722ca4768`.
No coordinate or native-runtime behavior changes; no Phenix/Coot execution.

**W48 checkpoint:** declared graph tests pass (20); complete Willow passes
1,444 tests plus 229 subtests. Installed/relocated graph and shared-owner tests
pass (113), and the existing public graph reproduces exactly with original paths
blocked and the original temporary checkout absent. Five installed command helps,
lean import and Python 3.10 syntax checks pass. The wheel SHA-256 is
`60c6520dbf266ab81782cf2084b6659bd6a192d2b70a3d7c884a514fc5ede66e`.
Source validation used `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages`,
and `/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python`
with `-m pytest -q -p no:cacheprovider` (complete suite) and the same command
with `tests/test_topostitch_graph.py` (focused). Installed checks use that site's
package without source `PYTHONPATH`, on a renamed temporary checkout. These
paths record local validation provenance; no operational graph input depends on
them. The source failure before W48 is the absent graph module. No Phenix/Coot
run or native-runtime behavior change applies to this patch.

**W47 checkpoint:** selected source/transformed image audits now bind exact
reciprocal partner incidence without reducing lattice shifts. Capacity is scoped
to the present selected-coordinate evidence; global/molecular identity is open.
Focused/installed-relocated **68**, full Willow **1,424 + 229 subtests**, and exact
public-placement compatibility pass. See [W47](topostitch-preview.md#w47--one-periodic-edge-and-its-reciprocal-partners).


**W46 checkpoint:** individual live torsion/plane observations compose Cedar
kernels with original-proxy and full-family target/gradient checks. Six native
endpoint controls pass while retaining local regressions and deferred chemistry.
Full Willow **1,416 + 229 subtests**; focused **40**; installed/relocated **159**
plus byte-identical complete native endpoint review. Live policy negatives refuse.
See [W46](topostitch-preview.md#w46--native-torsion-and-monomer-plane-observations)
for exact commands, schema additions and limitations.


**W44 checkpoint:** individual native pair terms reproduce complete container
scores for all five prior endpoints. Selected/core attribution exposes worsening
pairs hidden by aggregate scores; no acceptance policy changes. Full Willow:
**1,397 + 229 subtests**; focused: **50**; installed/relocated: **140** plus a
byte-identical complete native endpoint review with original paths blocked.
Compact JSON preserves the old review content exactly while reducing the largest
report from about 110 MB to 49 MB. See [W44](topostitch-preview.md#w44--individual-pair-attribution)
for commands, schema additions, native version and scientific limitations.


**W43 checkpoint (2026-11-14):** twelve new regression cases cover exact source/
full-precision/rounded masking, forbidden fixed motion, rounding limits, finite
points, detached coordinate projections, actual pair snapshots, mismatched capture
and retained partial failures, budget admission and the observed binary roundtrip.
Focused source: **67 passed** (0.41 s). Final full Willow: **1,384 passed + 229
subtests** (73.83 s), using the W39 full-suite command below. Installed/relocated
focused: **127 passed** (1.69 s), using the W41 installed command pattern with
captured-job, trial, capture, mask, recipe, transport, endpoint and packing tests.
All five installed entrypoints, lean imports and Python 3.10 syntax pass.
Wheel SHA256: `2443d91e6ebca9e956f575e5a0854416a50cc7908c3c9aa77f56442507b70657`.

Five complete native endpoint observations use **Phenix 2.2.1-6174**; independent
W41 rounded captures confirm native target/full-gradient and pair-residual parity.
Installed/relocated whole-window review is byte-identical with the original copied
checkout absent and source/scientific paths blocked. Wrong endpoint hash and
fixed-coordinate negatives reject before job creation. The initial exact-decimal
roundtrip refusal is retained and explicitly handled through the evaluator's
binary displacement expansion. Default read-only native results still match W41.
[W43](topostitch-preview.md#w43--full-precision-endpoint-observations) documents
additional flags, report kinds, measured tradeoffs and limitations. No complete
combined/Cedar suite, checkpoint migration, model edit or adoption is claimed;
scientific artifacts remain local. Cedar's consumed capture/numerical/process
interfaces are unchanged from the W42 compatibility control through af9aee87.

**Prior W42 checkpoint (2026-11-14):** eight orchestration regressions cover early
control rejection, repeat/developer namespace isolation, Cedar observation-layer
ordering, owned runner forwarding, uncertain cleanup propagation, verified timeout,
removed inputs/dispatcher and changed-dispatcher refusal. Focused source: **29
passed**; final full Willow: **1,372 passed + 229 subtests** (70.04 s), using the
W39 full-suite command below. Installed/relocated focused: **74 passed** (1.97 s):
captured job, trial, capture, mask, recipe and transport, using the W41 installed
command pattern. Entry-point help, lean imports and Python 3.10 syntax pass.
Willow wheel SHA256:
`44f95e05e2e4317cee0b0a19ebc8b7cf6889b557ee697e14af54cd6db099a7b9`.

A temporary installed package from Cedar `948a7860` plus the nine native TopoStitch
modules passes **244 focused tests + 19 subtests** (28.42 s): those six Willow files
plus Cedar campaign process, Phenix runtime, native validation, attachment native
and captured mixed gradients. The initial copied test tree omitted two imported
fixture modules; the corrected declared set passes and the collection failure is
retained. This is neither a merge nor the full combined/Cedar suite. Combined
wheel SHA256: `755b246462542e225b51889f6225ab111c41bec3ce80de929ed6e31f33206a09`.

Complete native source/installed/relocated controls and owned-runner negatives
are described in [W42](topostitch-preview.md#w42--one-installed-captured-job-boundary).
The first extra version-label equality check refused the same dispatcher because
native discovery returns a shorter release label; that unintended compatibility
change was removed before validation. Exact byte fingerprints remain binding.
Original copied checkout paths are absent and old source/scientific reads are
blocked during installed native checks. Evidence relocation is not resumable
campaign-run portability. Generated captures, trial results, combined checkout
and wheels stay local; only source, regressions and documentation are committed.

**Prior W41 checkpoint (2026-11-14):** six new regressions cover complete derivative
sampling/repeatability, wrong/nonfinite derivatives, matched pair contributions
and strict control types. Focused source: **107 passed** (1.06 s). Full Willow:
**1,364 passed + 229 subtests** (73.89 s), using the W39 full-suite command below.
This is the Pine-derived Willow suite, not Cedar or a merged integration build.
Installed/relocated focused: **107 passed** (96 + 11), covering trial, transport,
mask, recipe, capture, endpoint and packing. One initial harness collection named
a nonexistent test file; the corrected run and original failure are retained.

The wheel's native code completes a one-iteration 7R96 trial and the default
read-only probe from relocated copied inputs, with the original temporary
checkout absent and original scientific/source paths blocked. The capped trial
passes all three derivative audits; no resumable campaign portability is claimed.
All five installed entrypoints, lean optional imports and Python 3.10 syntax pass.
Wheel SHA256: `fcf874a3517a859478bac98535bd27890607b859abeede047500742d3f04d681`.
Build/install commands remain the W39 commands below. The installed focused
command is `python -m pytest -q -p no:cacheprovider` with the seven named
`tests/test_topostitch_*.py` files from a separate copied test tree, with
`PYTHONDONTWRITEBYTECODE=1` and only the wheel site-packages on `PYTHONPATH`.

Five complete native trials and fresh endpoint captures use **Phenix 2.2.1-6174**;
see [W41](topostitch-preview.md#w41--bounded-native-trials-and-matched-cleanup-controls)
for exact additional CLI options, bounds, numerical outcomes and remaining gates.
An insufficient budget rejects before optimization. An independently captured
manual angle replacement rejects before trial creation; the initial add-mode
fixture was refused by native interpretation as a duplicate restraint and remains
recorded. No native engine/Cedar source, old checkpoint or artifact schema is
changed. New developer trial reports are schema 1 and grant no runtime authority.
Generated scientific artifacts and failed checks are deliberately excluded from Git.

**Prior W40 checkpoint (2026-11-14):** 20 endpoint regressions cover exact protected
bytes, fixed motion below serialization precision, outward rounding, unsupported
movable chemistry and explicit ANISOU preservation. Full Willow source: **1,358
passed + 229 subtests** (85.60 s), using the W39 command with topology dependencies.
Installed focused: **101 passed** (1.03 s): capture, endpoint, mask, packing, recipe
and transport. The initial copied harness lacked the developer packing script;
after including that existing test dependency the complete declared set passes.
Relocated focused: **69 passed**, plus byte-identical complete native endpoint
review with old capture/source reads blocked and the original copied checkout
absent. Lean optional import and Python 3.10 syntax pass. Installed endpoint
results match all three native-control audits. The original packing command's
content/keys remain unchanged without endpoint options; wrong mask/point hashes
reject. Wheel SHA256:
`c1cb9c71cf7891592cecf37ddd7c43033d4475cd94b067286602dad92f949b75`.
See [W40](topostitch-preview.md#w40--bind-endpoint-review-to-movement-and-serialized-bytes)
for the native command and retained ANISOU/default-rejection evidence. No existing
artifact migration, optimization or model adoption is introduced.

**Prior W39 checkpoint (2026-11-14):** 15 new reconstruction regressions pass.
Full Willow source: **1,338 passed + 229 subtests** (65.90 s), with the declared
topology dependencies. The initial run omitted Gemmi and had 15 dependency
failures/77 skips; its log is retained, and the corrected complete run is green.
Installed and relocated focused sets each pass **60 tests** (1.08 s): capture,
mask, recipe and transport. The first installed collection omitted the test
package/fixture helpers; the corrected copied test package passes.
The original temporary checkout path is absent during relocation; a fresh native
reconstruction also succeeds from the relocated capture and source. This is a
reconstruction check, not resumable native-run portability. The installed wheel
supplies the exact staged backend bytes for a second successful native check.
Wheel SHA256: `983a923e5b3b3f16d153abc6184d9022bb1679c99e25dd6160bbfac96adb7ed4`.

Exact full-suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/path/to/topology/site-packages \
  /path/to/test/python -m pytest -q -p no:cacheprovider
```

Focused installed tests use only the installed wheel's site-packages on
`PYTHONPATH` from a separate copied test tree. The wheel is built with
`python -m pip wheel --no-deps --no-build-isolation --wheel-dir /local/wheels .`
and installed with `python -m pip install --no-deps --force-reinstall WHEEL`.
[W39](topostitch-preview.md#w39--reconstruct-the-observed-native-starting-context)
owns the native command, scopes and limits. No workflow/schema migration or
Cedar merge is included; all scientific artifacts remain local.

**Prior W38 checkpoint (2026-11-14):** the new 11 mask regressions verify exact fixed
coordinates, explicit variable ordering, motion limits and independent numerical
derivatives that include interactions with fixed atoms. Focused mask/transport/
recipe tests: **45 passed** (1.26 s). Full Willow source: **1,323 passed + 229 subtests**
(68.70 s). The first sandboxed full run had five `/bin/ps` permission failures in
existing campaign process tests; the complete rerun with process-inspection
access passed. No process-management code changed.

Installed-wheel validation from a separate copied test tree: **410 tests + 18
subtests** (24.82 s), covering all `test_topostitch_*.py` plus construct registration,
run context, AutoRefine and Refine Doctor. This is a declared focused set, not
the full installed suite. The test runner was supplied by the normal test
environment with only the installed wheel's site-packages prepended to
`PYTHONPATH`; import origins were checked. The lean installation imports the
optional native module and executes numerical masks without native dependencies.
Isolated Phenix execution from the extracted wheel reproduces source/perturbed
masked targets. Wheel SHA256:
`9ea8fc9912d16f756cebc1acaf18337f79d6b159d658f73383c2123821870cee`.

Original-copied-path-absent relocation passes **107 tests** (2.01 s): mask,
recipe, periodic, contacts, transport and roadmap. This qualifies those source
operations, not resumable native-run portability. Python 3.10 syntax passes.
Commands use the same source environment/full-suite/wheel invocation below,
with `tests/test_topostitch_mask.py` added to the focused selection. Native
commands, exact Phenix version, masks and complete diagnostic outcomes are in
[W38](topostitch-preview.md#w38--explicit-movable-coordinates-and-direct-native-composition).

**Prior W37 checkpoint (2026-11-14):** complete canonical recipes add 17 regression
cases, including the observed partial-plane omission and exact image/identity
binding. Focused recipe/periodic/contact/transport: **88 passed** (1.99 s).
Full source: **1,312 passed + 229 subtests** (72.24 s), run because the existing
CRYST1/SCALE reader was shared without changing its validation behavior.
Rebuilt installed wheel: **438 focused tests + 18 subtests** (25.19 s).
Both optional modules import from the lean isolated installation; construction
still needs the declared dependencies. An isolated wheel under Phenix reproduces
the complete 14-pair native energy and components from exact installed bytes.

Exact source commands (with installed topology/test dependencies):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest \
  tests/test_topostitch_recipe.py tests/test_topostitch_periodic.py \
  tests/test_topostitch_contacts.py tests/test_topostitch_transport.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation . --wheel-dir /explicit/wheels
```

This machine additionally appended its explicit temporary optional-dependency
site-packages directory to `PYTHONPATH`; no shared environment was modified.
After renaming a copied checkout so its original path was absent, the four
focused files plus `test_topostitch_roadmap.py` passed **96 tests** (1.80 s).
The explicit-model-path recipe regression also reproduces the identical packet
after moving the source directory. This qualifies those operations, not a
resumable native run. The W37 wheel SHA256 is
`d7aa5235518f64a0a31b94aed46a2d00eaf50224fcbbf8eeed5acd16809dec73`.
Native Phenix 2.2.1-6174 complete derivative executions and retained review
outcomes are recorded in [W37](topostitch-preview.md#w37--complete-canonical-pair-recipe-backend).

**Prior W35 checkpoint (closed 2026-11-14):** the new final-PDB RMSD regression fails
before the fallback and passes afterward. Three new tests (plus three subtests)
cover native output, log precedence and incomplete/unrecognized summaries.
Focused source AutoRefine/Doctor/roadmap checks: **53 tests + 16 subtests**
(10.21 s). The full source suite passes **1,295 tests + 229 subtests** (70.83 s).
The rebuilt installed wheel passes **421 focused tests + 18 subtests** (26.36 s),
including the existing TopoStitch/registration/context suite and AutoRefine/Doctor.
An isolated installed parser matches current source bytes and all three actual
Phenix 2.2.1-6174 final PDB/log readbacks. These are rereads of completed W34
refinements, not new refinement executions. Existing statistic keys, R-factor
parsing and checkpoint selection remain unchanged.

The prior W33 original-copied-path-absent relocation passed **376 tests + 2
subtests** (12.12 s); it was not repeated for this parser-only patch, which changes
no operational paths. The comparator's preceding new-module regression failed
against its prior wheel; its reader rejects changed model bytes, overwrite and
repeated path reads with changed snapshots. Python 3.10 syntax checks pass.

Actual Phenix 2.2.1-6174 captures replay through Cedar's maintained directed
nonbonded reviewer. The comparison is byte-identical after copied
source/models/captures relocate, with original copied paths absent and Python
reads of original live evidence/source blocked. Both frozen Cedar `cd744e2` and
`f2345a8` readers produce identical measurements from the same captures. This is
narrow read-only compatibility, not a combined branch/runtime qualification.
Installed comparison/image arithmetic needs no Cedar/Gemmi/Phenix; the developer
capture-reader wrapper explicitly requires a trusted Cedar source and dependencies.
Wheel SHA256: `f3eabac1645159b971170e848a1afa009806fe3674caa86e955e36db67258720`.

The preceding installed 8D93 viewer retains source/candidate hashes, selected
operator and display coordinates to <1e-10 Å. Corrected native plane controls
pass while raw negative controls remain. JavaScript syntax/mock-DOM checks pass;
rendered browser validation remains pending after the local-file automation policy
block. No full GUI or scientific repair qualification is claimed.
Environment: Python 3.12.14, pytest 9.1.1, NARestraints 1.1.3 (`a9264f9`), Gemmi
0.7.5, SciPy 1.18.1 and NumPy 2.5.4. The earlier 17 fitting tests passed with
minimum SciPy 1.14.1 / NumPy 2.2.6; that is not a current minimum-version run.
The transformed-image regression fails before its guard: a distinct source improves its
contact score but places an unscored atom on the selected mate. The updated
fitter withholds that transform without writing files. Actual installed 8D93
fitting preserves the schema-2 candidate bytes and reports a distinct transformed
selection (240 atoms, 274,916 tests). Schema-1/2 preview replay is unchanged.

Coverage includes independent brute-force symmetry enumeration in P1, P21,
P212121, P43, R3:H and P63; nonlocal/skew-cell bounds; reciprocal/self-image
capacity; transformed frames/contact atoms; library role fingerprints; incomplete
contacts; exact source and registration checksums; renamed/split chains and
copies; chemical versus representation boundaries; protected/free ends; fixed
anchors and whole-pair window expansion; bounded matching alternatives; no-write
CLI behavior; explicit bend-preview anchor/ANISOU preservation, serialized
backbone-change limits, frozen-input replay, tampering and no-overwrite behavior;
bounded placement, no-op/refusal outcomes, finite Jacobian-call budgets,
ASU motion under P43 screw images and opposite-direction proposals; offline view
replay, exact mate coordinates in both movement directions, unrelated unmapped
routes, script-safe scene embedding and frozen-directory/no-overwrite checks; selected-atom
stabilizers, centered/screw/skew cells, large translations, nontransitive near
coincidences, occupancy uncertainty and original-path-absent relocation.

Source command (historical environment paths, not operational model references):

```sh
NASOLVE_TEST_PYTHON=/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" - <<'PYTEST'
import sys
from pathlib import Path
sys.path.append('/private/tmp/willow-periodic-install/lib/python3.12/site-packages')
import pytest
paths = sorted(str(p) for p in Path('tests').glob('test_topostitch*.py'))
raise SystemExit(pytest.main(paths + ['tests/test_construct_registration.py', 'tests/test_run_context.py', 'tests/test_autorefine.py', 'tests/test_refine_doctor.py', '-q', '-p', 'no:cacheprovider']))
PYTEST
```

The equivalent explicit paths were used for the installed receipt above.
The narrower source regression command was `python -m pytest
tests/test_autorefine.py tests/test_refine_doctor.py tests/test_topostitch_roadmap.py
-q -p no:cacheprovider`, with the same source environment. Installed tests
ran from `/private/tmp`, using the same test interpreter, absolute test paths,
`--import-mode=importlib` and
`PYTHONPATH=/private/tmp/willow-periodic-install/lib/python3.12/site-packages`.
A wheel was built with `pip wheel --no-deps --no-build-isolation` and installed
into that disposable environment with its declared dependencies. Subsequent
patches rebuilt/reinstalled the wheel without changing the shared NASolve/Cedar
environments. Isolated `python -BI` imports matched current source bytes. The dependency-free
lean environment imports comparison/transport only; AutoRefine correctly requires
its existing declared dependencies (including Biopython). No dependency was added.

Actual installed CLI checks cover periodic/contact/pairing composition, logical
registration, discovery/windows and the separate [bend-preview writer and fitter](topostitch-preview.md). A scoped public
[8D93](https://www.rcsb.org/structure/8D93) check used explicitly declared local
strand/core windows: two ends, one mate, two unselected pairing choices and four
window sizes per end. It retained unknown interior cuts and preserved PDB bytes.
This is a read-only smoke check, not unsupervised discovery or scientific repair
validation. Downloaded coordinates and derived benchmark files are excluded from
Git. The synthetic CLI checks also verified no input-file changes.

Full-suite command: the source environment above with
`python -m pytest -q -p no:cacheprovider`, executed with process-control permission
for campaign tests. The focused installed/relocated checks do not claim a full
installed-platform matrix. `git diff --check`, Python 3.10 syntax, JSON,
documentation references and roadmap synchronization are checked before publication.

The actual installed command reproduced the source public 8D93 image audit:
240 selected atoms, 274,916 budgeted atom tests, no selected overlaps or orbit
coincidences. Source bytes were unchanged. The selected coordinate sets are
distinct within this scope; closure, global packing and physical partner capacity
are not thereby approved. The [preview guide](topostitch-preview.md#public-8d93-native-interpretation-comparison--2026-11-13)
retains the separate Phenix source/preview/fitted interpretation results and
remaining geometry degradation.

The periodic fitter's source-image eligibility guard is included in these tests.
It refuses optimization for coincident or uncertain selected images. Schema-1
public 8D93 requests preserve their candidate bytes; new schema-2 requests opt
into extended phosphate-angle and circular-torsion checks without migrating old
previews. The preview guide records the separate complete native captures and
their remaining scientific limitations.

## Local diffraction benchmark preflight — 2026-11-13

Five serial single-job **Phenix 2.2.1-6174** (`phenix.phaser`, dispatcher version
2.2.1) MR executions completed: public 8D93/5W6W into the supplied hexagonal data,
and public 5W6W/8CS1/7R96 into one requested basic dataset (straight reference plus
two bent-model controls). The supplied MTZ, metadata CIF and STARANISO report PDF
were crosschecked. All source inputs stayed unchanged; frozen copies, checksums,
commands, logs, exact results and generated models stay in local benchmark
receipts and are deliberately excluded from Git.

These use the existing `prepare_automr` frozen-input API in nonstandard mode,
then `build_phaser_eff` for an isolated native benchmark. The PDF is explicitly
supplied as `DatasetFiles.summary`; no fake `summary.html` is generated. Normal
folder discovery still requires `summary.html`, so this is not PDF-loader
support. Native parameters retain one explicit ensemble, original source atoms,
42-residue NA composition, one search copy and 1 Å model RMSD, adding explicit
`F,SIGF` labels and `phaser.keywords.general.jobs=1`. No target chemistry edits,
TopoStitch motion, refinement, automatic checkpoint adoption or successful repair
are claimed. Copy/composition assumptions, different ASU cuts and terminal
sequences must be resolved before a matched deformation/refinement comparison.
The roadmap tracks these as placement preflight, not closure of S06.

Gemmi API references:
[symmetry operations](https://gemmi.readthedocs.io/en/latest/symmetry.html) and
[unit-cell transforms](https://gemmi.readthedocs.io/en/latest/cell.html).

## W48 — Declared periodic graph for Pine

The installed backend `nasolve.topostitch_graph` adds two read-only APIs:

```python
from nasolve.topostitch_graph import build_registered_periodic_graph
report = build_registered_periodic_graph(
    model_path, discovery_manifest_path, registration_path,
    extra_edges=[{
        "kind": "base_pairing",
        "source_site": "A:1",       # logical identities in the selected copy
        "target_site": "B:2",
        "target_operator_xyz": "x+1,y,z",
    }],
)
```

The example operator must belong to the input crystal. The three paths are
explicit caller inputs, validated by the existing discovery/registration owners;
source, discovery and registration hashes bind the report. It contains no
host-absolute operational path. `extra_edges` defaults to empty. Their values
are explicit caller hypotheses, not inferred or accepted connections.

The registered report has kind `topostitch-registered-periodic-graph`, schema 1.
It retains every target site for the one declared discovery copy, including
missing mappings, coordinate identity issues and sites outside declared routes.
Other registered copies and unrepresented atom indices remain excluded scope.
Existing route order supplies backbone edges and declared core pairs supply
pairing edges. Extra edges may be pairing, stacking or symmetry correspondence;
extra covalent links are refused until seam chemistry has its own qualified
adapter. Chemical, representation and unknown route boundaries, protected sites
and do-not-connect intent are retained. A boundary is never guessed from PDB
labels, a missing atom or the graph's connected-component count.

The nested `topostitch-declared-periodic-graph` schema-1 report is also available
through `describe_periodic_graph(node_ids, edges, cell_parameters=..., space_group=...)`.
Each explicit edge has `edge_id`, `kind`, `source`, `target`, and
`target_operator_xyz`; node and edge IDs are distinct positive integers, not PDB
serials. Edge `u -> v` means `x_u` connects to `g(x_v)`. Reverse traversal uses
`g^-1`. The deterministic spanning forest records each parent edge and exact root
image `T_v`; each non-tree edge records the loop `T_u g T_v^-1`. Nonidentity
translation or screw loops are legitimate winding observations. Mixed edge-kind
loops do not prove chemical strand closure. Parallel edges stay explicit.

Limits are 10,000 nodes, 20,000 edges and absolute exact operator numerators at
most 1,000,000. Gemmi composition is checked against Python integer arithmetic;
whole lattice translations are never wrapped away. Scope remains the shared
conventional single-model PDB/Sohncke adapter. These APIs change no coordinates,
chemistry, registry or checkpoint. Physical orbit equivalence, whole-ASU/tile
multiplicity, cut choices, materialization and scattering invariance remain open.

Validation: 20 focused graph regressions include noncommuting screw/translation
order, reverse edges, centering, self loops, missing sites and checksum drift.
The pre-patch checkout fails to import the absent backend. Public 8D93 consumes
its existing declared artifact references and preserves all source bytes. Full
Willow and installed/relocated results are recorded in the audited roadmap.
No Phenix/Coot execution is needed for this read-only graph addition. Scientific
fixtures and generated reports remain local and are not included in Git.

## W49 — Preview a change of graph representatives

`relabel_periodic_graph(graph, node_images, expected_graph_sha256=...)` in the same
installed module accepts the nested W48 graph and explicit assignments such as
`[{"node_id": 2, "operator_xyz": "x+1,y,z"}]`. Unlisted nodes keep their identity
representative. The complete source graph is replayed and compared; a modified
summary with a newly computed hash is still rejected if it disagrees with its
inputs. This API binds graph identity only. A physical cut must separately retain
the registered outer report and coordinate source identity.

For `y_v = h_v(x_v)`, each edge changes by `g' = h_u g h_v^-1`. This preserves
noncommuting operation order. Every fundamental loop is checked against
conjugation by its root image; applying inverse node images must reproduce the
entire original graph exactly. Isolated nodes may change representatives while
their edge-free graph remains unchanged, so proposed node images are retained
separately. These are algebra checks, not physical orbit or scattering tests.

The schema-1 `topostitch-periodic-image-relabel-preview` report retains the source
graph hash, proposed/changed node images, transformed graph, loop checks, inverse
round-trip result and explicit false coordinate/scattering/runtime authority.
It writes no model and does not modify the source report. True boundary meanings,
missing-site coverage and protected intent remain in the registered owner; this
low-level API cannot override them or authorize a chemical seam. P01 stays
partial, P02 still requires a genuine graphical cut preview, and P03 remains open.

Fourteen new regressions cover screw/translation conjugacy, inverse recovery,
no-op/isolated nodes and invalid/stale inputs. The prior installed W48 package
passes its 20 existing graph tests and fails all 14 new capability tests. On the
public declared graph, moving the two explicit target-side representatives makes
the selected pairing edges identity-image edges; all loop checks and the inverse
round trip pass without changing any source bytes or claiming geometry repair.

## W50 — Observe all present model atom orbits

`nasolve.topostitch_images.inspect_model_orbit_identity(model_path,
expected_sha256=..., coincidence_tolerance_angstrom=.01,
max_atom_tests=2_000_000)` reuses the same bounded metric-aware orbit engine for
all present ATOM/HETATM records. Explicit larger work budgets are accepted;
the two public-source controls used 10,000,000. No basename input search,
chemistry filter, registration selection or PDB serial-number indexing occurs.
Coordinates and source-order atom identities come from the existing PDB owners.
The source is hashed before observation and its bytes are checked again before
returning the report.

The schema-1 `topostitch-present-model-orbit-observation` report retains all atom
identities, coordinates, record types and occupancies, exact coincidence operators,
work counts, issues and numerical policy. Unknown/invalid/partial occupancy,
alternate conformers and ambiguous residue groups remain explicit review findings.
Their finite coordinates are still observed; missing chemical meaning is never
filled in. Duplicate exact atom identities are rejected by the existing parser.
`PRESENT_MODEL_COORDINATES_DISTINCT` means no coincidences or listed input issues
in that present-coordinate scope. Otherwise the result is `MODEL_ORBIT_REVIEW`.
Neither result merges identities or validates molecular topology, packing, ADPs,
scattering or an ASU cut. Missing atoms and omitted structure content remain unknown.

Ten new tests cover waters outside the chosen polymer, source-order indices,
lattice aliases, special positions, occupancy/alternate uncertainty, TER ambiguity,
source drift, bounded refusal and relocation. The retained 8D93 and independent
7R96-derived source snapshots each have 855 present atoms and no observed orbit
coincidences at the explicit tolerance. These statements concern the exact input
snapshots, not completeness of their deposited entries. All scientific inputs and
reports remain local. No Phenix/Coot execution or Cedar changes are involved.

## W52 — Bind an image preview to registered source atoms

The installed API `nasolve.topostitch_recut.preview_registered_relabel` composes
W48's registered graph, W49's image algebra, W50's all-present atom observation
and the existing Cartesian image transport. Call it with explicit model,
discovery and registration paths, `node_images`, optional `extra_edges`, and the
fresh outer graph's `expected_registered_graph_sha256`. The outer binding is
required: identical graph algebra in a renamed or different model does not
identify the same coordinate source. Numerical orbit options are the same as W50.

```python
from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_recut import preview_registered_relabel
bound = build_registered_periodic_graph(model, discovery, registration)
preview = preview_registered_relabel(
    model, discovery, registration,
    node_images=[{"node_id": 2, "operator_xyz": "x+1,y,z"}],
    expected_registered_graph_sha256=bound["report_sha256"],
)
```

Node numbers refer to this exact bound report. A requested nonidentity image
must have resolved, unambiguous registered coordinates; the complete residue's
present atom indices move together in memory. Unrequested and unregistered
context atoms stay exactly unchanged. Missing unrequested nodes, unknown route
boundaries, protected/free-site intent and source orbit/occupancy findings remain
visible. Changing a protected node's representative is not permission to bend a
junction or change its routing. No source file is changed.

The schema-1 `topostitch-registered-image-relabel-preview` report retains the
fresh registered graph and orbit observation, relabeling proof, requested atom
groups, fixed indices and proposed in-memory coordinates. Every moved atom is
checked by inverse Cartesian image transport. O3-prime anchors, when uniquely
present, check each edge's before/after image arithmetic and distance invariance;
missing anchors stay `ANCHOR_UNAVAILABLE`, without centroid substitution. These
anchor distances are display observations, not chemical bond or pairing targets.
The numerical coordinate bound is `1e-7 Å + 64 ULPs` at the coordinate scale;
edge distance comparison allows four times that arithmetic bound. It is not a
chemical acceptance threshold.

This is **not** a materialized ASU or an immutable NASolve child. There is no
coordinate writer, ANISOU/tensor transport, terminal-chemistry change, native
restraint generation or approval action. The shared Pine intent owner must still
carry editable choices, and P02 must supply the graphical review. Complete
physical/scattering/chemistry qualification remains open. A semantic continuation
does not activate a lone symmetry bond while its phosphate-angle policy is
unsupported.

Nine regressions cover exact atom ownership through renamed chains, missing
requested sites, unchanged context, stale outer identity, absent anchors,
noncommuting edge-image checks, deliberately reversed image transport and
relocation. The retained public-source example relabels two whole residues
(36 atoms), keeps 819 fixed, and verifies all 38 declared edge observations.
Old graph/relabel/orbit reports reproduce exactly; all source bytes are preserved.
Scientific fixtures and observations remain local. No Phenix/Coot run is needed.


## W55 — Observe sampled scattering before and after representative relabeling

`nasolve.topostitch_scattering.observe_registered_relabel_scattering` takes the
same explicit model/discovery/registration paths, `node_images`, outer registered
graph hash and optional `extra_edges` as W52, plus an explicit list of `hkls`.
It rebuilds the registered preview and uses all present source atoms in Gemmi's
crystal-image direct sum. Cartesian anisotropic U tensors are rotated in memory
with Gemmi's cell-operator transform; source occupancy, element, charge and
isotropic B are preserved. No PDB or other coordinate file is written.

```python
from nasolve.topostitch_scattering import observe_registered_relabel_scattering
observation = observe_registered_relabel_scattering(
    model, discovery, registration,
    node_images=chosen_images,
    expected_registered_graph_sha256=bound["report_sha256"],
    hkls=[[0, 0, 0], [1, 2, 3], [-1, 3, 2]],
)
```

The schema-1 `topostitch-registered-relabel-scattering-observation` retains
complex before/after values, individual and aggregate differences, exact source
and preview hashes, observed atom/ADP/image counts, transported tensors, numerical
scope, Gemmi version/kernel fingerprint and the actual element coefficients.
Its status is always `OBSERVED_REVIEW_REQUIRED`; there is no acceptance threshold
or claim that a finite reflection sample proves complete scattering invariance.
A sampled match cannot resolve missing atoms, special-position multiplicity,
occupancy ambiguity, molecular identity, chemical seams or native restraints.

Requests contain 1–4096 unique integer Miller triples, components at most 10,000,
and at least one allowed nonzero reflection. F000/systematic absences alone are
insufficient. The default work budget is 5,000,000 atom/image/reflection terms
(counting before and after); an explicit positive budget up to 100,000,000 is
accepted. Existing orbit budgets still apply. Unknown/unparameterized elements,
missing/invalid occupancy or B, zero/negative-eigenvalue ANISOU, mismatched/orphan/
duplicate ANISOU, nonstandard SCALE and NCS expansion refuse. The observer reads
and checks the process-global neutral IT92 policy without modifying it.

[Gemmi's documented direct-sum calculator](https://gemmi.readthedocs.io/en/stable/scattering.html#direct-summation)
uses nonzero anisotropic U in preference to isotropic B. Its
[cell image list](https://gemmi.readthedocs.io/en/stable/cell.html#unit-cell)
contains the crystallographic images. This observer excludes NCS and verifies
the image count against the declared space group. Atom ANISOU values are stored
as float32 by Gemmi; tensor readback allows the documented diagnostic's bounded
float32 scaling error, and raw scattering differences remain visible.

Twenty-two synthetic regressions cover P43, centered hexagonal R3 and oblique
P21 images; isotropic/no-op/translation cases; wrong tensor transport and distorted
coordinates; unsupported input/budget/global-policy cases; and exact relocation.
The previous installed package lacks this module. Focused graph/recut/image/
scattering checks pass 107; complete Willow passes 1,511 plus 229 subtests.
Installed/relocated owner checks pass 298, including exact public scattering and
legacy preview replay with original paths blocked and the old checkout absent.
Five command helps, lean import and Python 3.10 syntax pass. Validation commands
follow the W52 receipt above, adding `tests/test_topostitch_scattering.py`.
Wheel SHA-256: `3b1c1ab0a46a7a00dfa0638a93de460f392283e61b5094f6ec0f54cfc627bad2`.

The retained public source has 855 ANISOU-bearing atoms; the preview changes 36
representatives. Across the predeclared 343-index grid, Gemmi's maximum complex
difference is 8.24×10⁻⁷ and relative L2 difference 2.91×10⁻¹¹. The control that
omits tensor rotation differs by up to 106.36. An independent complete direct
calculation in **Phenix 2.2.1-6174** transforms fractional coordinates and Ustar
using cctbx and gives a maximum difference of 3.05×10⁻¹² across 115 allowed
indices, with the same large negative control. Libraries are not bitwise equal:
source Fcalc differs by up to 5.44×10⁻⁴, with different parameter precision.
This qualifies the stated mathematical observations, not a written ASU.

The initial manually supplied cctbx grid included centering-forbidden indices.
Its direct kernel multiplies by centering multiplicity rather than independently
summing those translations, so that raw output is not an absence oracle. It is
retained; a separately recorded follow-up uses the native
`miller.set.remove_systematic_absences` owner before calculation. Exact commands,
source fingerprints and all local failures/observations are retained. Neither
execution is refinement or a dry-run. No native installation or Cedar source was
changed; scientific inputs/results are deliberately excluded from Git.

A temporary installed package combining Cedar C297 `fe7e9fd73988fc2ffb5501c3740fd9e06da0b45d`
with the 24 Willow TopoStitch modules passes the same 298 focused owner/API
checks and exactly reproduces the public preview/scattering observations.
The original temporary source directory is absent. This checks those interfaces,
not a branch merge, full combined suite or merged CLI/dependency metadata.


## W56 — Freeze and replay an explicit representative proposal

The installed `nasolve-topostitch-cut-preview` command freezes one explicit
proposal alongside byte-identical model, discovery and registration inputs.
It reuses the registered graph, atom-orbit and coordinate-image preview owners.
It does not create an edited model, chemistry decision or NASolve checkpoint.

```bash
nasolve-topostitch-cut-preview model.pdb --discovery discovery.json \
  --registration registration.json --proposal proposal.json --out new-cut-preview
```

The schema-1 `topostitch-representative-proposal` request has exactly these fields:

```json
{
  "schema_version": 1,
  "kind": "topostitch-representative-proposal",
  "registered_graph_sha256": "<exact outer registered report_sha256>",
  "node_images": [{"node_id": 2, "operator_xyz": "y,-x,z+1/4"}],
  "extra_edges": [],
  "coincidence_tolerance_angstrom": 0.01,
  "max_atom_tests": 2000000
}
```

The example operator is for P43; choose an actual group member and exact node
identity from the declared graph. The hash is the 64-character outer registered
report hash, not the nested graph hash. Include the same noncovalent `extra_edges`
used to build that report. New covalent edges remain unsupported. Explicit image
choices change representation only; they do not declare a nick or chemical seam.

`build_relabel_preview` validates before creating a new exclusive directory.
The packet contains unchanged `source.pdb`, `discovery.json`, `registration.json`,
`proposal.json`, then `preview.json` written last. Interrupted writes preserve
partial evidence; a directory without its receipt is incomplete. Existing output
is never overwritten. Source and proposal checksums, fixed run-relative paths
and byte sizes use NASolve's existing artifact-reference owners.

`load_relabel_preview(directory)` verifies those local references and recomputes
the full observation from the frozen inputs. It rejects altered derived results,
rehashed approval flags, changed inputs, duplicate keys, external symlinks,
wrong references and artifact drift during replay. No historical absolute path
or basename lookup is consulted. Exact replay needs a compatible algorithm and
Gemmi runtime; incompatible saved observations refuse rather than silently migrate.
The receipt kind is `topostitch-representative-preview-bundle`, schema 1. Its
workflow stays PREVIEW_BUILT / UNREVIEWED / NOT_ATTEMPTED. Human review, model
materialization, chemical connectivity changes and checkpoint selection are false.
W55 scattering remains a separate source/preview-bound diagnostic.

Before this patch, registered image previews were in-memory observations only.
The new module/CLI and receipt are additive; existing commands and bundles retain
their behavior. The existing bend viewer does not yet display this packet. The
next step is a genuine before/after periodic view with atom and edge inspection,
then persistent reviewed choices; neither GUI review nor chemistry is claimed.

Validation: 22 new regressions, 67 focused tests, the complete suite **1,533 plus
229 subtests**, and 320 installed/relocated owner tests pass. Two demonstrated
replay gaps (boolean/numeric equality and late artifact drift) failed before their
fixes. Six installed command helps, Python 3.10 syntax and lean import pass. The
installed command builds the exact expected public packet. The 855-atom public
snapshot with 36 proposed image atoms reproduces the prior W52 observation exactly
and reopens after its original input directory is removed; installed replay also
blocks original source paths. W55 scattering and older preview replay remain exact.

Commands use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<installed-dependency-site>`
with `python -m pytest -q -p no:cacheprovider`, targeting
`tests/test_topostitch_recut_bundle.py`, `tests/test_topostitch_recut.py` and
`tests/test_topostitch_preview.py` for the focused check; omit targets for the full
suite. Wheel construction uses `python -m pip wheel --no-deps --no-build-isolation .`;
installed/relocated checks use only the installed site on PYTHONPATH. The installed
command is exercised with all four explicit paths and a new `--out` directory.
Wheel SHA-256: `dffd1e0ce2c00d6ef86456f501867f43ddd88956d8ae4c7089c5d8015ee186d0`.
No native Phenix/Coot execution or Cedar change was needed. All scientific inputs,
outputs and installation evidence remain local and are deliberately excluded from
Git; committed tests contain synthetic fixtures only.


## W57 — Inspect periodic representative proposals in the shared viewer

`nasolve-topostitch-view new-cut-preview --out cut.html` now recognizes a W56
representative packet as well as the existing bend packet. It replays frozen
inputs first, writes a new standalone HTML outside that packet, and makes no
model, chemistry, review or checkpoint change. Bend-search options refuse for
a representative packet because its images are already explicit. Existing bend
commands, saved scenes and optional selected-mate behavior remain supported.

The new schema-1 `topostitch-representative-view` scene contains every present
source atom in source order, exact before/proposed positions, logical and
coordinate identities, protection flags, unchanged context, declared route
boundaries, scope findings and the original source-orbit assessment. Each typed
edge retains its exact before/after target operator and transformed O3′ endpoints.
These endpoints are not necessarily the displayed target ASU representative.
Missing anchors retain their node identities without invented positions. Graph
lines are display observations, not newly activated atom-level chemical bonds.

The existing renderer adds Original / Proposed / Overlay modes for this packet,
atom inspection, typed graph edges, an edge selector with image/spacing details,
edge focusing, optional unit-cell outline and declared-boundary/coverage details.
All-atom and base-ring toggles, rotation, pan, zoom and keyboard controls are reused.
There is no Apply button, automatic cut enumeration, persistent human-review
record or changed-coordinate export. P02 remains partial, with actual rendered
browser/user validation still required. A prior local-file automation policy block
has not been bypassed; no visual or scientific approval is claimed.

Before W57, the offline viewer accepted bend packets only. Changes are limited
to `topostitch_view.py`, its existing packaged HTML asset, synthetic regressions
and current documentation/intent. W56 proposal/receipt schemas do not change.
Eleven new tests protect exact image endpoints, renamed logical ownership, all
source atoms, missing/context scope, relocation, input drift and dispatch errors.
The first endpoint test used a base-only fixture; it was corrected to the existing
O3′-anchored fixture. A malformed receipt dispatch regression failed before its
fix. The initial public harness lacked the test-root import path and was retried
with that path explicitly supplied; original failure evidence is retained.

Validation uses the W56 commands, with focused targets
`tests/test_topostitch_recut_view.py`, `tests/test_topostitch_view.py`, and
`tests/test_topostitch_recut_bundle.py`: **40 pass**. Final complete Willow:
**1,544 plus 229 subtests**. Installed/relocated owner checks: **338 pass**, six
command helps, lean import and Python 3.10 syntax. The installed command emits
the exact public scene after relocation with original paths blocked. Existing
bundle, graph and scattering replay remains exact. Wheel SHA-256:
`b6ca58eac298d44c2b2a7c651627d0682d950e29077d8777660f3942ea5508d2`.

The public scene retains 855 atoms, 42 nodes and 38 edges in R3:H. A Node VM
executes the actual packaged JavaScript with DOM/canvas doubles for public,
legacy bend and missing-anchor scenes, exercising mode switches, atom picking,
all edge choices, focus, rotation/zoom and cell display without nonfinite draw
coordinates. O3* spelling also passes. This is interaction-logic evidence only,
not browser rendering, layout or accessibility qualification. No Phenix/Coot
execution or Cedar changes were required. Scientific snapshots, generated HTML,
local harnesses and receipts remain excluded from Git.


## W58 — Qualify the installed viewer boundary with Cedar

The viewer now loads/renders its packaged asset before creating the requested
output. Previously an absent template left an empty HTML file; the regression
reproduces that failure and now confirms no output or frozen-input mutation.
No scene, packet, chemistry, command or checkpoint schema changes.

The initial temporary C299 `b4739c76` composition deliberately kept Cedar package
metadata unchanged. It passed 335 owner tests and exact public replay, but three
HTML tests failed because the template was not packaged. Preserve that failure:
copying Python modules alone is not an installable branch integration.
A separate temporary wheel adds exactly Willow's two topology extras, five
TopoStitch entry points and `data/topostitch-view.html` package-data path to the
Cedar metadata, with a parsed exact-union check. Original source is then moved
away. That installed composition passes **339 Willow tests**, **162 Cedar tests
plus 19 subtests**, six command helps and exact public graph/bundle/scattering/
scene replay. Cedar owns AutoRefine, checkpoint and qualified plane-force code;
Willow contributes its existing modules and asset. No live worktree was edited,
branch merged, complete combined suite run or native refinement executed.
The combined README/docs still need explicit reconciliation at integration.

Willow alone passes focused **41**, full **1,545 plus 229 subtests**, installed/
relocated **339**, six helps, lean import and Python 3.10 syntax. Commands and
relocation guards follow W57; the added target is the missing-template regression
in `tests/test_topostitch_view.py`. Final wheel SHA-256:
`38fa81b7226ee13dd11af2537a9920a268617c8fc0b42b327666c6f62f9b4194`.

Authenticated retained W34 inventories have zero parallelity proxies and 42
planarity proxies in each reference/cleanup/bend result. Rerunning those unchanged
recipes would not exercise C299's parallelity correction, so no new native trial
was launched. This is a scope decision, not a new scientific result. Existing
failed/capped trials and chemistry limitations stand. All temporary composition,
failure and scientific evidence remains local and is excluded from Git.


## W59 — Calculate representatives along explicitly chosen links

`propose_forest_representatives` in the existing graph owner accepts an exact
source graph/hash, explicit selected edge IDs and one fixed anchor node per
selected connected component. The chosen edges must form a forest: no cycles,
self loops or parallel-edge cycles. The caller chooses the omitted edges and
anchors; the function does not search for partners or rank cuts.

```python
from nasolve.topostitch_graph import propose_forest_representatives
choice = propose_forest_representatives(
    bound["periodic_graph"],
    selected_edge_ids=chosen_edges,
    anchor_node_ids=fixed_representatives,
    expected_graph_sha256=bound["periodic_graph"]["graph_sha256"],
)
# Copy choice["node_images"] into a W56 explicit representative proposal;
# its outer registered_graph_sha256 must still bind the same source/registration.
```

The existing exact graph/tree owner supplies path-ordered images. For a selected
anchor a, each node receives `h_v = G_a^-1 G_v`; selected edge images become
identity under `g' = h_u g h_v^-1`. The anchor stays in its current representative.
Unselected vertices stay unchanged. The complete graph, edge kinds, cycle
conjugacy and inverse recovery are checked by the existing relabel owner.
Unselected edges retain whatever image is necessary, including nonzero lattice
winding. An identity image does not imply a short distance or a chemical bond.
An omitted edge is not a declared nick. Existing exact arithmetic limits apply.

The additive schema-1 `topostitch-explicit-forest-representatives` report retains
selected edges, anchors/components, generated node images, unchanged vertices,
remaining nonidentity edges, full relabel proof and a proposal hash. It is
PROPOSED_REVIEW_REQUIRED with no runtime/model/chemistry/review authority.
Empty selections are a deliberate no-op; duplicate/unknown/boolean IDs, missing
or extra anchors, selected cycles, stale graphs and arithmetic overflow refuse.
Source graph replay now compares canonical fingerprints, closing a demonstrated
Python-equality hole where an integer could impersonate a boolean report field.
Valid historical reports remain unchanged; malformed type-edited reports now refuse.

Twenty-one new forest cases plus that replay regression cover reversed and
noncommuting paths, disconnected anchors, centered R3, P43, oblique P21, unwrapped
translations, winding, failures and composition with the saved registered packet
and viewer. An initial helper-call mismatch was corrected before qualification.
Focused graph/forest/bundle checks pass **78**; full Willow **1,567 plus 229 subtests**;
installed/relocated **361**, six helps, lean import and Python 3.10 syntax pass.
Validation uses the W58 commands, adding `tests/test_topostitch_forest.py` and
`tests/test_topostitch_graph.py`. Wheel SHA-256:
`812a5afee6596cc5d7e1c06f371e3d30eaac078d36bb3f4b5ae45ba4f519ec1e`.

A predeclared public control chooses 27 existing edges and separately anchors
node 1 or node 21. The two alternatives assign new images to 282 or 286 atoms; both
keep their anchors fixed, replay after original inputs are removed, and produce
valid existing viewer packets. Their 343-index Gemmi scattering observations have
maximum complex differences 1.51e-6 and 1.71e-6, relative L2 4.57e-11 and 5.94e-11.
Neither alternative is selected. This partial declared graph happens to leave
no nonidentity edge after either relabeling; that does not establish a complete
ASU, full molecular connectivity or a finite whole crystal. Missing route scope
and P01/P03/P04 gates remain. No native refinement, chemistry or rendered-browser
approval occurs. Scientific inputs, reports and views remain local, outside Git.

W60 below retains the chosen-edge/anchor meaning in the same source-bound saved
request. Actual graphical choice and persistent human review remain open.


## W60 — Preserve selected-link and anchor intent in saved proposals

The existing `nasolve-topostitch-cut-preview ... --proposal ...` command also
accepts schema-1 `topostitch-forest-proposal`. It uses the same common fields as
W56, replacing `node_images` with `selected_edge_ids` and `anchor_node_ids`:

```json
{
  "schema_version": 1,
  "kind": "topostitch-forest-proposal",
  "registered_graph_sha256": "<exact outer registered report_sha256>",
  "selected_edge_ids": [6, 37],
  "anchor_node_ids": [1],
  "extra_edges": [],
  "coincidence_tolerance_angstrom": 0.01,
  "max_atom_tests": 2000000
}
```

Numbers above are illustrative caller-owned graph IDs, not universal residue
numbers. Supply the same extra edges used to create the bound graph. Mixed image-
list/forest fields, stale bindings and invalid forest choices refuse before output.
The loader rebuilds the registered graph, derives exact images through W59 and
then calls the existing registered atom preview. Frozen `proposal.json` retains
what was chosen; the compact `forest_selection` receipt field retains canonical
edge/anchor IDs, nested source-graph hash and the derivation report hash.
Full replay recomputes all of them instead of trusting cached images or choices.

Packet kind/version and its five files are unchanged. Direct-image requests and
old receipts/scenes reproduce exactly, without migration or added default fields.
The additive request kind needs this reader; older readers reject it. New forest
scenes include the selection metadata, and the existing boundary/coverage panel
shows chosen graph-edge numbers and fixed logical sites. This records caller
proposal intent, not a scientist's acceptance. Human review remains UNREVIEWED.
There is still no automatic cut choice, GUI editing, model/chemistry write or
checkpoint action.

Nine regressions cover equivalent explicit-image results, retained choice bytes,
installed-style CLI input, relocation after original removal, incompatible/stale
fields and altered/rehashed selection evidence. The positive cases fail before
the feature. Focused checks pass **71**; full Willow **1,576 plus 229 subtests**;
installed/relocated **370**, six helps, lean imports and Python 3.10 syntax pass.
Commands follow W59 with `tests/test_topostitch_forest_bundle.py` added. The installed
CLI builds the exact forest packet as well as the legacy direct-image packet.
Wheel SHA-256: `275669fdd15071df76e22e052b022b9d436f25af755965eb76554d3a1eb6cb7a`.

Both W59 public alternatives reproduce their exact prior coordinate/graph
observations with the retained link/anchor request. Fresh packet hashes correctly
reflect the different intent representation. Originals are removed before replay.
The actual viewer JavaScript displays both selections and retains all tested
interactions through DOM/canvas doubles; browser rendering/user review is still
unqualified. No new scattering calculation, Phenix/Coot execution or Cedar change
was needed. All scientific packets/views and local validation remain outside Git.


## W62 — Exact labelled orbit permutations for a proposed cut

`nasolve.topostitch_recut.observe_registered_relabel_orbits` takes the same
explicit model/discovery/registration, graph checksum, node-image list and
optional extra edges as `preview_registered_relabel`. It reuses that verified
preview and the existing bounded exact operator algebra. The additive result is
schema 1 `topostitch-registered-orbit-permutation-observation`; no old packet,
preview, scene or sampled-scattering report is changed.

For each chosen representative operator **h**, every space-group representative
**g** has an exact correspondence

```text
g * h = T_n * g_mapped
(atom, g, lattice_m) -> (same_atom, g_mapped, lattice_m + n)
```

Here `T_n` is translation by an **integer** cell vector. Group indices are
zero-based and translations act **after** the group operation. The complete
forward table is a bijection, and right multiplication by `h.inverse()` returns
the original group index with the negated shift. This covers all lattice cells,
not just a sampled neighbor box. Noncommuting operator order and unwrapped shifts
are retained. Each unique image shares one table; atom indices must cover every
source atom exactly once, including unchanged/unregistered context. A separate
Gemmi cell transform checks that proposed coordinates actually match the chosen
images within the existing numerical arithmetic bound. Rehashed altered points
or duplicated/missing ownership refuse.

The default `max_permutation_rows=200000` bounds the combined forward/inverse
rows; callers may choose an explicit positive integer up to 2000000. Validation
occurs before building those tables. The result binds source bytes, graph,
preview and proposed points, and reports the maximum coordinate arithmetic error.
Input drift refuses; no global runtime/scattering settings are modified.

**Exact labelled multiplicity is not physical unique-atom multiplicity.** A
special-position atom may still appear several times in this labelled expansion.
The observer neither merges those images nor approves their weights/occupancies.
It does not prove molecular identity, missing content, ANISOU transport, coordinate
serialization, scattering acceptance, chemical continuity or a native restraint.
Use W55's independent tensor/scattering observation alongside it. No ASU writer,
GUI choice/approval or checkpoint action is added; P03 remains partial.

Sixteen regressions cover exact rational arithmetic independently of the production
composition helper across all 65 Sohncke reference groups, screw/centered/oblique/
noncommuting examples, lattice shifts, no-op and special-position multiplicity,
invalid budgets, changed coordinates/ownership, source drift and relocation.
Focused 47 and full Willow **1,592 plus 229 subtests** pass. Exact commands:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_topostitch_orbit_permutations.py tests/test_topostitch_recut.py tests/test_topostitch_scattering.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/local/wheels .
```

The host validation Python was 3.12.14 with Gemmi 0.7.5; the declared full topology
environment supplies the dependencies. Installed/relocated 386 tests, six command
helps, lean imports and Python 3.10 syntax pass. Original temporary inputs are gone
before replay and source paths are blocked. Old graph/preview/packet/scattering/
scene results remain exact; both new public orbit reports replay exactly from the
installed wheel. Wheel SHA-256:
`526aca524cbd58648536e9ce76fea134690f22e4489a19d480e9154b0ff16dc7`.

Both predeclared W60 public forest alternatives retain 855 labelled source atoms
and 9 group operations (7695 labelled image incidences, **not 7695 distinct atoms**).
Each uses 36 table rows. Largest Cartesian binding errors are 1.42e-14/7.11e-15 Å.
The first assigns 282 atoms to its nonidentity image; the second 286; neither is
selected. Scientific packets, requests, reports, wheels and local validation stay
outside Git. No Phenix/Coot execution was needed for this patch. Compatibility is
additive; callers must explicitly request the new observation, with no migration.


A temporary installed composition with published Cedar C301 `bea76681` passes
**386 Willow + 182 Cedar tests and 19 subtests**, six entry-point helps and exact
public old/new packet, orbit, view and scattering replay after its temporary
source path is removed. Only explicit topology extras, TopoStitch entry points,
viewer asset and TopoStitch modules are added to the archived Cedar base; metadata
union and every overlaid source hash are recorded. Cedar's dirty working files
are excluded. This is a scoped package/owner compatibility check, not a merge,
complete combined suite, combined human-documentation review or native execution.


## W63 — Show existing source bonds at proposed ASU seams

The source-bound packet now supports an optional read-only native-link observation:
`nasolve.topostitch_recut_bundle.observe_relabel_native_links(packet, native_receipt)`.
The existing viewer exposes it with `--native-receipt`:

```bash
nasolve-topostitch-view /path/to/representative-packet --native-receipt /path/to/capture/native_receipt.json --out /path/to/new-review.html
```

Use an authenticated **unchanged source-model** Cedar capture, not a capture of a
bent candidate or another representation. Installed Cedar owners are the default;
the isolated Willow prototype can explicitly use `--cedar-source /path/to/trusted/cedar/src`.
That developer option loads trusted code; it is not a scientific input resolver.
No native process is launched by this observer. The packet and all capture artifacts
are checked by their existing owners and must remain byte-identical during replay.
Native atoms are joined by exact source identity, so native reordering cannot change
which atoms are tracked. Ambiguous altloc/insertion identities refuse in this scope.

Cedar owns capture authentication, atom binding and the interpreted bond inventory.
Only existing **interresidue identity simple bonds** are transported. If source
endpoints use proposed images `h_left` and `h_right`, the second proposed endpoint
is viewed through `h_left * inverse(h_right)`. Independent Cartesian transforms
verify the unchanged original bond geometry. Duplicate source proxies remain
separate. Existing ASU bonds and simple bonds with nonidentity operators stay
explicitly unqualified; they are not mistaken for identity links. All angle,
plane and exclusion policies remain outside this observation.

The additive schema-1 `topostitch-representative-native-link-observation` binds
source, preview packet, registered preview and native receipt hashes. It reports
source/direct/exact-image endpoint coordinates and distances, native policy/version,
proxy counts and links absent from the declared backbone graph. For O3′–P links it
inventories source **P/OP1/OP2**. This is observed native connectivity, not complete
intended topology or chemical approval. Missing atoms remain missing; no atom,
OP3, terminal treatment, active bond, angle restraint or replacement model is made.

The optional viewer section **Existing links across the cut** lists affected links
and retained phosphate atoms. No extra bond line or Apply action is introduced.
Old scenes and packets are unchanged when no capture is supplied. A source-native
link absent from the logical graph is an explicit coverage gap, not permission to
silently extend that graph. The new observation and optional scene field are
additive; older readers need not consume them and no old packet migration is needed.
P04 is now partial for observation only; native seam enforcement remains open.

Eleven adapter regressions cover exact-image distances, no-op, source reordering,
duplicate links, unqualified source symmetry rows, incomplete/failed/drifting
captures, relocation and optional CLI behavior. The pre-feature module fails these
new imports. Focused **52** and complete Willow **1,603 plus 229 subtests** pass:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_topostitch_native_seams.py tests/test_topostitch_recut_bundle.py tests/test_topostitch_recut_view.py tests/test_topostitch_view.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/local/wheels .
```

Host Python 3.12.14 used the declared full topology environment (Gemmi 0.7.5).
Installed/relocated **397** tests, six command helps, lean imports and Python 3.10
syntax pass. Both native reports/scenes replay exactly after removing original
paths; the installed optional-view command reproduces its exact scene. Final
module/HTML bytes match wheel SHA-256
`bd3e31e175c241e19bdf3369373f6a59e3d86d09703666a3b998edcdbf8ae97a`.
Actual viewer JavaScript with DOM/canvas doubles passes native, plain representative,
bend and missing-anchor controls. This is not rendered-browser or human review;
that earlier graphical validation gap remains open.

One complete read-only **Phenix 2.2.1-6174** source capture used frozen Cedar
`f2345a8`, with no optimization/refinement/Coot execution. Initial setup refused
before native launch because the proposed output parent contained the PHIL input;
that refusal is retained. Separating input/output parents produced `REVIEW` in
1.8515 seconds. The exact source has 855 atoms, 956 simple native bonds, zero ASU
bonds and 38 interresidue identity links. Native receipt SHA-256:
`ff2384075aa0613b0531cf473e96d9331ac76a755695e68e5e583e612d1d027d`.
Both W60 alternatives create two representation seams: anchor 1 at C:108–109 and
D:115–116; anchor 21 at A:108–109 and C:108–109. All four O3′–P observations retain
P/OP1/OP2 and original exact-image distances. None of those links is present in
the partial declared backbone graph. Neither proposal is selected or chemically
approved. Scientific sources, native capture, packets, views and validation logs
remain local and are excluded from Git.


A temporary installed composition with published Cedar C302 `d32825e9` passes
**397 Willow + 238 Cedar tests and 19 subtests**, six helps and exact public replay,
including authentication through the default installed Cedar owners. Temporary
source inputs were relocated before replay. This adds source-capture compatibility
to W62's packet/orbit/view/scattering checks. Only explicit topology metadata,
TopoStitch modules and viewer asset were overlaid on the archived Cedar commit;
no dirty Cedar file, branch merge, full combined suite or native execution was used.


## W64 — Compare explicit cuts in one shared view

The existing offline viewer accepts additional representative packets:

```bash
nasolve-topostitch-view /path/to/cut-a --compare /path/to/cut-b --out /path/to/new-comparison.html
```

Repeat `--compare` for up to seven additional packets. All 2–8 cuts must replay
from the **same exact source and registered graph**; different source coordinates,
registration/graph intent, duplicate packets, bend previews, stale artifacts and
unrelated bend-search options refuse before writing HTML. Every input remains
unchanged. The output must sit outside every supplied packet. A 50,000-point
combined display budget bounds the shared camera's atom/edge coordinate inventory.
This is a visualization bound, not a scientific eligibility criterion.

`nasolve.topostitch_view.representative_comparison` returns an additive schema-1
`topostitch-representative-comparison-view` containing the unchanged per-cut scenes,
ordered local **Cut 1, Cut 2, …** display identifiers and exact comparison/source/
graph hashes. The numbers are local presentation labels; hashes identify the
proposals. Reordering inputs changes the comparison identity. No paths are embedded.
Optional `--native-receipt`/`--cedar-source` have W63's meaning and apply to all cuts;
the common receipt and all packets must stay unchanged throughout preparation.

The **Inspect cut** selector updates the proposal, edge operators, boundaries,
provenance and optional source-native seam report. It retains the common camera,
rotation, pan, zoom, coordinate mode and display toggles. Switching clears stale
atom/edge inspection rather than leaving the prior cut's details visible. Reset
fits all compared proposals, so changing cut does not silently change scale.
The displayed cut is **not selected or approved**; there is no model write,
checkpoint, saved human decision, automatic alternative generator or ranking.
Single-cut and bend scenes retain their exact existing payloads and commands.
P02 remains partial pending rendered/user validation, real cut editing and
persistent human review; P03/P04 chemical/materialization gates are unchanged.

Twelve regressions fail against the old feature boundary and pass with the new
comparison. They exercise exact scenes/order, wrong sources/graphs, input counts,
duplicates, late drift, relocation, output containment, budget and bend refusals.
Focused **42** and full Willow **1,615 plus 229 subtests** pass:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_topostitch_cut_comparison.py tests/test_topostitch_native_seams.py tests/test_topostitch_recut_view.py tests/test_topostitch_view.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/local/wheels .
```

Python 3.12.14 with the full topology dependencies/Gemmi 0.7.5 was used. The stale
installed W63 wheel initially refused the new API import, as expected; that failed
installation control is retained before rebuilding/reinstalling. Final wheel
SHA-256: `904d8fbf17256847081178d2e6a6ac9eb4c3e75a1533f8af25fa9549234ec044`.
Its module and viewer asset match the final source bytes.

Both predeclared public alternatives compare 855 source atoms with two observed
native seams apiece. The exact prior W63 scenes are retained, and the combined
result replays after relocation with original paths blocked. Actual packaged
JavaScript exercises repeated switching, shared original-coordinate pixel positions,
current seam/provenance/edge details, cleared stale selections and legacy bend/
missing-anchor/single-cut controls through DOM/canvas doubles. This does **not**
close the blocked rendered-browser/user review gate. No new native execution,
refinement, chemistry or Cedar change was needed. Scientific inputs, comparison
HTML/JSON and local validation are excluded from Git. Existing schemas need no
migration; the new comparison kind requires this compatible viewer.


Installed/relocated **409** tests, six helps, lean imports and Python 3.10 syntax
pass. The installed `--compare` command produces the exact native-context comparison
scene; legacy bundle, forest, orbit, single-view and source-native replay also pass.
W63's scoped C302 owner-composition qualification remains the compatibility baseline;
W64 adds no Cedar owner interface or package metadata change.


## W65 — Save and reopen a source-bound cut preference

The comparison view offers **Prefer the displayed cut**, **Keep the original
representation**, and **Needs revision**, with an optional note. Downloading a
preference requests a local JSON file; it does not modify a packet/model or select
a checkpoint. Changing the displayed cut clears the pending choice, retains the
note text and requires a fresh explicit choice before another download.

Reopen that note against the same explicit ordered comparison:

```bash
nasolve-topostitch-view /path/to/cut-a --compare /path/to/cut-b --preference /path/to/topostitch-cut-preference.json --out /path/to/new-noted-view.html
```

If the original comparison included a native capture, supply the same validated
`--native-receipt` context (and optional trusted developer `--cedar-source`) again.
The Python API is `nasolve.topostitch_view.validate_cut_preference(directories,
preference_path, native_receipt=..., cedar_source=...)`. It recomputes the comparison
from explicit packet paths before accepting the preference. Hashes identify inputs;
they are never used to locate files. Reordering cuts, changing the source/graph/
optional native evidence or selecting an undisplayed packet requires fresh review.

The request is schema 1 `topostitch-cut-preference`, with exactly these fields:
`schema_version`, `kind`, `comparison_sha256`, `source_model_sha256`,
`registered_graph_sha256`, `decision`, `preferred_preview_receipt_sha256`, `comment`.
Decisions are `prefer_cut`, `keep_original`, `needs_revision`. Only `prefer_cut`
may name a preferred packet hash; the other two require null. Comments are strings
up to 2000 characters and the input file is bounded to 16384 bytes. Unknown fields,
duplicate keys, bool schema versions, stale hashes and unsupported actions refuse.

The validator returns schema-1 `topostitch-bound-cut-preference`, retaining that
choice/comment plus the exact request-file hash. It explicitly sets
`reviewer_authenticated`, `scientific_acceptance`, `checkpoint_selection_applied`
and `runtime_authority` false. This is **caller-supplied preference evidence**,
not proof of who clicked, visual correctness or scientific approval. The verified
note appears separately from the unchanged scene in the HTML. It is not a NASolve
run, checkpoint or parallel campaign history. Existing checkpoint selection and
campaign record owners remain responsible for their later real operations.

Single-pass JSON template insertion preserves literal template markers and script
text in notes without substitution or execution. Fifteen regressions cover all
choices, stale/foreign/authority-bearing requests, duplicate keys, size/comment
bounds, relocation, reordered comparisons, non-comparison refusal and safe text.
The initial missing-feature and placeholder-substitution failures are retained.
Focused **57**, full Willow **1,630 plus 229 subtests** pass:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_topostitch_cut_preference.py tests/test_topostitch_cut_comparison.py tests/test_topostitch_native_seams.py tests/test_topostitch_view.py tests/test_topostitch_recut_view.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/local/wheels .
```

The host used Python 3.12.14 and the full topology dependencies/Gemmi 0.7.5.
Final wheel SHA-256:
`a7ade94f7676f9168646b4b91ff0945cccd9e560555ac6e8a863a284e3b71b78`;
its module/HTML bytes match the final source. Actual packaged JavaScript exercises
all three exports, choice reset, retained note and reopened preference display
through DOM/canvas/Blob doubles. Those exact exported requests validate against
relocated public packets/native capture with original paths blocked. The original
comparison and all legacy scenes remain exact. **Actual browser rendering, download
behavior and human review are still unqualified**, not supplied by these doubles.
No Phenix/Coot execution, chemistry, model/selection action or Cedar change occurs.
Scientific data, local preferences/views and validation stay outside Git. Both new
request/readback kinds are additive; old packets and scenes need no migration.


Installed/relocated **424** tests, six entry-point helps, lean imports and Python
3.10 syntax pass. The installed `--preference` command reproduces the exact verified
note while preserving the original comparison JSON; legacy packet/forest/orbit/
native-link/single-view and comparison commands also pass. The complete source
suite used `PYTHONDONTWRITEBYTECODE=1` and
`PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages`
with the host NASolve `.venv/bin/python -m pytest -q -p no:cacheprovider` from the
Willow checkout. These local environment paths are validation provenance, not
operational artifact locators; a normal installed topology environment uses the
portable commands above.


A final temporary installed composition with published Cedar C303 `c9736e39`
passes **424 Willow + 221 Cedar tests and 6 subtests**, six helps and exact public
packet/orbit/scattering/source-native/preference replay through default installed
Cedar owners. The Cedar set covers complete-request, complete-child-bounds,
attachment-native and checkpoint behavior; it took 292.13 seconds. Archived
published source and an explicit metadata/module/HTML union were used, with the
original temporary source path removed before replay. This is scoped compatibility,
not a branch merge, full combined suite, browser qualification or native execution.
The W65 code remains unchanged by that check.


## W66 — Observe declared backbone intent across a cut

Use the existing verified representative packet to inspect continuation and
phosphate inventory, independently of native bond evidence:

```bash
nasolve-topostitch-view /path/to/cut-a --compare /path/to/cut-b --backbone-intent --out /path/to/new-intent-view.html
```

The Python API is
`nasolve.topostitch_recut_bundle.observe_relabel_backbone_intent(directory)`.
It replays the existing packet, binds the exact source/graph/preview/receipt hashes,
and refuses input drift. Its additive schema-1
`topostitch-representative-backbone-intent` report is an observation, not a new
editable topology registry or chemistry instruction passed to native tools.

Each logical site's incoming state is `DECLARED_CONTINUATION`,
`DECLARED_CHEMICAL_BOUNDARY`, `UNKNOWN_BOUNDARY`, or `OUTSIDE_DECLARED_ROUTES`.
Declared 5′→3′ route order determines the incoming O3′→P partner; numerical residue
order, nearest images and source-native bonds never fill gaps in that declaration.
A representation boundary retains continuation with an unresolved partner. A known
logical partner can separately lack unambiguous atom endpoints. Missing mapping,
missing atoms, alternate records and protected/do-not-connect annotations remain
visible. Outgoing boundary declarations are retained as well.

Resolved route partners carry exact original and proposed target operators,
logical/copy/node identities and source atom indices. Where both atomic endpoints
are unambiguous, the observer checks the transported O3′–P image distance against
the original; a large direct ASU separation does not invalidate the logical link
or establish chemical geometry. This is exact representative transport with a
floating arithmetic check, not physical deformation or a new covalent proxy.

The inventory retains exact atom names and indices, including legacy O1P/O2P/O3P
aliases and duplicate-role ambiguity. A declared continuation records preservation
of **existing P/OP1/OP2**, even with an unresolved partner; missing atoms are reported,
not generated. Existing OP3 conflicts only with explicitly declared continuation.
A chemical boundary leaves terminal-phosphate authorization **unknown**: an
independently declared complete terminal phosphate, such as W D:1, is neither
forbidden nor granted by this observer. No OP3 is added/deleted, no phosphate is
removed, and no bond/angle/native restraint is enabled.

`--backbone-intent` works with the optional authenticated `--native-receipt` view.
It deliberately keeps intended topology and observed source-native links separate.
The two retained public proposals each have 24 declared incoming continuations,
two chemical and two unknown boundaries, and 14 logical sites outside the declared
routes. They have no declared route seams; the independent native observer still
reports two cut-crossing source bonds outside those routes. The incomplete graph
is not silently repaired or promoted into complete chemical intent.

The optional report changes comparison identity. Reopening a preference exported
from this view requires the same `--backbone-intent` and optional native context.
Without the flag, old scenes/comparisons/preferences remain exact. Existing packet
schemas need no migration. The viewer refreshes the current intent details on cut
switches; JavaScript interaction checks use DOM/canvas doubles only. The real
browser/download/user review gate remains open: a new local-file attempt was
refused by the browser URL policy, and no workaround was used.

Validation uses Python 3.12.14, Gemmi 0.7.5 and unchanged native interfaces.
Eighteen new regressions cover screw-image direction, unresolved and absent partners,
missing atoms, alias collisions, OP3 scope, drift/tampering, relocation and optional
view/preference binding. Full Willow: **1,648 tests plus 229 subtests**. The complete
suite was run under the current session's collaboration requirement; no global
pipeline behavior changed. Exact commands and installed/compatibility results are
recorded in the audited roadmap. No Phenix/Coot execution was added by W66; the
existing authenticated source capture is read-only evidence. Scientific inputs,
views, preferences and local validation artifacts remain outside Git.

W66 installed/relocated validation passes **442** focused owner/API tests, six
entry-point helps, lean imports and Python 3.10 syntax. The installed command
reproduces the public intent-enriched view exactly after relocation with original
paths blocked; the old comparison and three preference requests exported by the
actual JavaScript also replay exactly. Wheel SHA-256:
`b7022e296f6d25e46a87e7b826ee8333b62abc3e0697cd1fc6e7bfd4052d84a9`.
The initial build environments lacked setuptools; the final build used the same
isolated packaging interpreter as W65. Those failures and the stale-wheel import
refusal are retained locally, not treated as passing checks.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_topostitch_backbone_intent.py tests/test_topostitch_cut_preference.py tests/test_topostitch_cut_comparison.py tests/test_topostitch_native_seams.py tests/test_topostitch_view.py tests/test_topostitch_recut_view.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/local/wheels .
```

The host full-suite command used `PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages`
and the host NASolve `.venv/bin/python`; the packaging interpreter was
`/private/tmp/topotrace-rename-env/bin/python`. These paths are validation
provenance only. Installed replay used the wheel's site-packages, copied tests
and explicit relocated packet paths; it did not import the original checkout.


W66's temporary installed composition with published Cedar C303 `c9736e39` passes
**442 Willow + 221 Cedar tests and 6 subtests**, six helps and exact public/legacy/
native-link/backbone-intent replay through default installed owners. The Cedar
subset covers complete-request, child-bounds, attachment-native and checkpoints
(311.38 s). Source/runtime asset hashes and explicit package metadata union are
retained. This is scoped compatibility, not a merge, full combined suite or new
native execution. Rowan's subsequent work remains separate.


## W67 — Resolve explicitly declared boundary partners

An existing route may end because the chosen representation ends. W67 lets a caller
resolve that particular boundary through the existing registered graph, without
inventing a second topology registry or native restraint writer:

```python
continuations = [{
    "continuation_id": 1,
    "source_site": "logical-3-prime-end",
    "target_site": "logical-5-prime-end",
    "target_operator_xyz": "x+1,y,z",
}]
bound = build_registered_periodic_graph(
    model, discovery, registration, backbone_continuations=continuations)
```

The source must be the last site of a declared route and the target its partner's
first site. **Both boundaries must already be `representation`.** Chemical and
unknown boundaries, interior/unknown sites, do-not-connect sites and competing
incoming/outgoing partners refuse. Operators use the existing exact group and
arithmetic validation. A translated closed route can retain nonzero periodic
winding; choosing a tree does not erase the original cycle.

Use `schema_version: 2` and the required `backbone_continuations` array in either
`topostitch-representative-proposal` or `topostitch-forest-proposal`, with the exact
new `registered_graph_sha256`. All other request fields and the existing
`nasolve-topostitch-cut-preview` command remain the same. The outer packet stays
schema 1; its frozen proposal and graph bind the added intent. Old readers refuse
the new proposal version. Old schema-1 packets, empty declarations and default
observations remain exact; old requests cannot hide an extra continuation field.

The optional W66 observation now resolves the incoming partner and carries the
continuation number and exact before/after target image. A missing coordinate
partner remains a declared continuation with unresolved geometry, preserving
existing P/OP1/OP2 intent. This is **declared topology**, not proof of a good bond,
complete seam angles, appropriate exclusions or a valid whole-ASU cut. No terminal
phosphate permission, atom edit, native activation or model writer is introduced.

A predeclared public development control uses one authenticated existing source
link, C:108 O3′ → C:109 P, to test this plumbing on the two retained 8D93 cuts.
It changes those two previously unknown boundary declarations explicitly in a new
manifest; no nearest-neighbor inference occurs. All **855 proposed atom coordinates
remain exactly equal** to their earlier proposals. One of two native seams is now
covered by declared intent; the other remains outside the partial routes. The
1.618695153511 Å source distance survives image transport. Sampled 125-HKL complex
Fcalc maximum differences are 5.046e-7 and 1.113e-6, numerical observations only.
No complete physical-scattering qualification or scientific adoption is implied.

Twenty-six new regressions cover strict declarations, unresolved coordinates,
noncommuting screw transforms, oblique translations, centering, winding, stale
requests, old behavior and relocation. Full Willow: **1,674 tests + 229 subtests**
(94.28 s). Installed/relocated owner suite: **468** (23.84 s). Full-suite and wheel
commands are the W66 commands above, with the W67 wheel/output directory. Actual
viewer JavaScript passes DOM/canvas controls for both cuts and all three preference
exports; this remains distinct from the blocked rendered-browser/download/human
review gate. No Phenix/Coot execution was added; the existing Phenix 2.2.1-6174
capture is read-only evidence. Generated scientific inputs and results stay local.

The installed wheel also passes six entry-point helps, lean import and Python 3.10
syntax; exact old/new views and three JavaScript-exported preferences replay after
relocation with the original paths blocked. Wheel SHA-256:
`4b46546f869b9806d1116849e9cc3d75b083e4d38fdb0ab66b143c8690843ac8`.
Temporary installed composition with published Cedar `a2e73603` passes **468 Willow
+ 221 Cedar tests and 6 subtests**, six helps and exact old/new default-owner replay.
It uses explicit metadata union and recorded module/asset hashes; no merge, full
combined-suite qualification or native execution is claimed.


## W68 — Inspect source seam angles and proxy persistence

This is a **read-only native diagnostic**, extending the existing
[synthetic image-kernel evidence](topostitch-preview.md#reproducible-native-plane-gate).
It does not rediscover or replace that probe, enable a bond, alter Cedar/cctbx,
materialize an ASU or run refinement. The unchanged W67 package remains the latest
runtime implementation.

A fresh maintained Cedar bootstrap under **Phenix 2.2.1-6174** reconstructs the
retained 855-atom source with exact observed-context equality. The historical
capture does not describe angle `sym_ops` or `slack`, so the diagnostic inspects
all **1,467 live source angle objects**: every image assignment is absent/identity
and every slack is zero. Captured indices, labels, ideals, weights and origins
are also bound; the frozen packet/plan/source/worker bytes remain unchanged.

For each explicit W67 cut, eight source-native angle terms cross the proposed
representation boundary, involving twelve atoms. Each seam contributes the
existing O3′–P–O5′, O3′–P–OP1, O3′–P–OP2 and C3′–O3′–P terms. These are observed
source terms, **not a declaration that four angles exhaust the chemistry policy**.
Targets/weights are carried from the native interpretation, never hard-coded from
these examples. With source images `G_i` and middle-atom image `G_c`, the diagnostic
uses per-atom operators `G_c * inverse(G_i)` on the proposed coordinates. Native
unit-cell-aware angular energies then describe the same source geometry.

| Observation | Cut anchored at node 1 | Cut anchored at node 21 |
| --- | ---: | ---: |
| Source angle residual sum | 20.368838370829 | 11.636477921299 |
| Transported angle residual sum | 20.368838370831 | 11.636477921298 |
| Largest rotated-gradient discrepancy | 2.65e-11 | 8.34e-12 |
| Finite-difference error, step 1e-5 Å | 1.67e-7 | 1.22e-7 |
| Finite-difference error, step 1e-6 Å | 3.08e-7 | 3.35e-7 |
| Residual after native proxy-array pickle/reopen | 5631.849771642584 | 5458.774223097205 |

The direct angular residual/gradient API and native `energies` path agree.
Identity and subset/reindexing selections preserve the image operators and
expected angular energies/gradients. In contrast, individual
angle and shared-array **pickle round trips lose `sym_ops`** on this installation;
the reopened terms therefore evaluate the wrong Cartesian geometry. Generic
deepcopy of an isolated angular manager also loses the operators. Deliberately
omitting the unit cell is another retained negative control. This is a concrete
serialization failure, **not evidence that every ordinary Phenix refinement path
uses pickle or loses these fields**. That exact lifecycle still needs inspection.

A follow-up isolates the **actual geometry-manager call path** without changing
the original source manager: an angular-only manager with the correct crystal
symmetry and all eight image-bearing proxies is evaluated with explicit angle-only
flags. Its residuals are already **5631.849771642584 / 5458.774223097205**, before
serialization, exactly matching the cell-omitting negative control. The installed
`manager.energies_sites` does not forward `unit_cell` to the angular `energies`
constructor. `manager.select` preserves the image assignments, but this evaluator
still omits their cell context. Thus simply attaching correct proxies is not a
supported solution. This is a complete native microprobe of the isolated angular
manager, not a complete ordinary refinement or exclusion-policy test.

The installed `angle.h`/`angle_bpl.cpp` provide per-atom operators and image-aware
gradients. The installed `pdb_interpretation.py` angle-edit scope/constructor does
not expose/populate those operators. Upstream [PHIL edit definitions](https://github.com/cctbx/cctbx_project/blob/master/mmtbx/monomer_library/pdb_interpretation.py)
show the same interface distinction; the pinned installed source and native
execution, rather than a moving upstream page, support the numerical result.
Do not work around the missing ordinary input contract by writing a symmetry
bond alone or by treating a pickled proxy as durable scientific intent.

**Next P04 gate:** coordinate with Cedar on the existing native reconstruction/
refinement owner. A prospective adapter must bind exact logical/coordinate/image
identity and complete effective terms, reconstruct operators explicitly, supply
the required cell/image evaluation context, and verify both at every supported
selection/rebuild/reload boundary. Qualify
ordinary entry, checkpoints/workers, normalization, missing/extra terms, torsions/
chirality/planes and exclusions before enabling a seam. Recutting still cannot
repair a physical gap or bypass P02/P03. Intent stays in Pine; native enforcement
and its diagnostic report stay in Cedar. No new driver or persistent registry was
introduced for this experiment.

Rowan confirms that `cif_refinement_runtime.run_compatible_refinement` wraps the
parallelity kernel and audits its parameter sets; it **does not** restore lost
proxy metadata. `refinement_parallelity` owns reusable frozen helpers, zero-cycle
preflight, exact round/checkpoint receipts and ancestry. Its existing kernel rejects
unit-cell/symmetry-bearing proxies. Reuse that lifecycle shell only after a distinct
angle construction/rebinding/evaluation contract is qualified; do not label it
existing symmetry-angle support. Potential approaches remain an explicit
unit-cell-aware angular evaluator or existing Cartesian image expansion/pullback,
with complete term replacement/double-counting and normalization checks. Neither
approach is activated by these notes.

Validation consisted of complete fresh native reconstruction and angle microprobes,
not dry runs and not optimization/refinement. The final owned execution was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/to/verified/Willow/src \
  python /path/to/local/attempt-5/run-owned.py
# The maintained owner launched, in that new attempt directory:
phenix.python -B probe.py
```

The local driver uses Cedar `cif_native_validation._run_native_command`, a 120 s
watchdog and the pinned installed composition at Cedar `a2e73603`; the bootstrap
comes from maintained source, never untrusted captured worker text. First attempts
retain an unsupported operator-multiplication call and a module/class lookup
error; a later isolated-manager attempt omitted its angle-only flags and refused
before a result. All three setup failures remain separate from successful
observations. The final follow-up uses explicit angle-only flags. The final receipt, scripts,
source hashes, raw controls and earlier failures are archived locally. This
experiment-specific scaffolding is not a new public CLI or a committed runtime.
No software test rerun is needed for this evidence/docs-only slice: W67's full,
installed and composition results remain the applicable code validation.


The W66–W68 local evidence is retained under the Git-ignored
`TopoTrace/local/topostitch-native-2026-11-15` archive root. Each archive has a JSON
index with every payload's size/hash, and all payloads were read back and verified.
These names/hashes locate forensic evidence, not an operational resume contract:

| Update | Archive | SHA-256 |
| --- | --- | --- |
| W66 | `W66-evidence.tar.gz` | `fe0df70627b07c0d758502af241d4f61acc5ed765fad507641a8aed0c8bb751b` |
| W67 | `W67-evidence.tar.gz` | `9c2af2a8a3fb07885c97637e4fce13d2597de543ad3b4a8664e299a3372493c8` |
| W68 | `W68-evidence.tar.gz` | `3db1d6050124703313fb037a0ca26ce74d2ba6b06376f27825662bec9d4272f6` |

W68 attempt 3 is the first complete kernel/pickle observation; attempt 5 adds the
manager, subset/reindex and deepcopy controls. Attempts 1, 2 and 4 retain setup
failures. No generated scientific artifact is committed or uploaded.


## W69 — Audit the virtual Willow/Cedar integration

A read-only integration preview compares Willow `6cfe42e9` with published Cedar
`a2e73603` at common base `d7913ddd`. `git merge-tree --write-tree --name-only`
creates a temporary Git tree, without changing a branch, index or working tree.
The result has **no source conflicts** and seven documentation/contract conflicts:
`AGENTS.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/campaign-full-auto.md`,
`docs/collaboration.md`, `docs/construct-registration.md` and
`docs/development-handoff.md`. Those remain unresolved; this is not a merge-ready
or scientifically qualified combined branch.

The virtual tree's package metadata matches W67's explicit composition exactly.
Its only runtime difference from that tested composition is Willow's older
11-line `autorefine.py` final-PDB RMSD fallback. This addition combines automatically
with Cedar's current refinement code. The actual virtual tree's source and combined
tests were archived into a disposable checkout, built into a wheel, installed in an
isolated target, and the original checkout path removed by relocation.

Installed **76 tests + 16 subtests** pass (19.37 s), covering the combined
`test_autorefine.py`, `test_cif_refinement_runtime.py` and
`test_refinement_parallelity.py`. Six entry-point helps pass. Native runtime and
entry-point interfaces are unchanged; no Phenix/Coot run was added. This closes the
previous composition's shared-parser coverage gap, not a full combined-suite or
human-document review gate. W67's 468 Willow / 221 Cedar owner controls remain
separate evidence. No code, schema or scientific data was changed by W69.

```bash
# In the isolated, relocated test checkout, with only installed package paths:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/to/virtual/site:/path/to/topology/dependencies \
  python -m pytest -q -p no:cacheprovider \
  tests/test_autorefine.py tests/test_cif_refinement_runtime.py \
  tests/test_refinement_parallelity.py
```

Virtual tree: `ea3eac058f034cbe26b980a457420056e64b34cc`.
Wheel SHA-256: `7ae3d170c8360d2ba531c3ecc2b8af2168a3bda7b11dc9da83992d47cd0466a6`.
The exact command vectors, source pins, test/build logs, conflict inventory and
wheel stay in the local evidence archive; no generated artifacts are uploaded.
Before any real merge, reconcile the seven human/agent contracts with their owners
and perform release-level combined validation in the chosen final tree.

Local `W69-evidence.tar.gz` in the declared archive root has SHA-256
`6dad0e97905bf8144ff5c2f022de65acfb4a7dd54cc7fac4727fd73ee31f9634`;
its indexed payloads were read back and verified.


## W70 — Describe the registered graph before choosing a cut

Use the existing cut-preview command to see the graph's logical sites, numbered
nodes/links, exact symmetry operators, declared boundaries and graph checksum
before authoring a cut. Node/link numbers belong to that exact graph hash; review
them again when source or declarations change. This mode prints JSON and creates
no directory or model:

```bash
nasolve-topostitch-cut-preview model.pdb \
  --discovery discovery.json --registration registration.json --describe-graph
```

The optional existing proposal supplies its noncovalent extra edges and W67
explicit backbone continuations:

```bash
nasolve-topostitch-cut-preview model.pdb \
  --discovery discovery.json --registration registration.json \
  --proposal proposal.json --describe-graph
```

The schema-1 `topostitch-registered-graph-description` contains the unchanged
registered-graph report under `registered_graph`. Its `report_sha256` is the graph
identity to which a cut request binds. `proposal_binding` is null without a
proposal; otherwise it retains the request byte hash, kind/version, requested and
actual graph hashes, and **MATCH or MISMATCH**. The outer description has its own
report hash; do not substitute that for the nested graph hash.

A successful description means the graph was inspected, **not that the cut is
valid**. `status` is `GRAPH_DESCRIPTION_ONLY`, `cut_selection_validated` is false,
and no runtime authority is granted. Chosen node images, forest selection, cut
budgets/geometry and scientific suitability are not validated by this mode. A
bad forest choice can therefore have a matching graph binding and still fail the
ordinary preview builder. Review a mismatching graph/source/declaration before
intentionally creating a revised proposal; the tool never silently rebinds it.

The optional request uses the same strict version/field/duplicate-key parser as
normal preview creation, and graph declarations use the same endpoint, operator,
capacity and boundary checks. Input drift refuses before any report is emitted.
`--describe-graph` rejects `--out`. Normal mode still requires both `--proposal`
and `--out`, validates the entire cut and refuses a stale graph checksum. Existing
request and packet schemas need no migration; old packets replay exactly.
The API is `describe_relabel_graph(model, discovery, registration_path=...,
proposal_path=None)` in the existing packet module; no new registry or CLI is added.

Fourteen added cases cover no-proposal inspection, schema-2 continuations, exact
CLI/API agreement, request shape, explicit mismatch, invalid cut versus matching
graph, input drift, mode refusal, unchanged bytes and relocation with the old path
unavailable. Focused packet/continuation/view suite: **115 passed**. Complete Willow:
**1,688 + 229 subtests** (83.49 s). Installed/relocated owners: **482 passed**
(23.73 s); six helps, lean import and Python 3.10 syntax pass. Installed old/new
public packet replay and graph output are exact, with original source paths blocked.

The first full-suite attempt ran within the process sandbox: **1,683 passed,
5 failed + 229 subtests**, with process-group signalling and `/bin/ps` denied.
No test-owned workers remained at inspection. The unfiltered suite then passed
with permissions for its owned process tests. Both logs are preserved; the initial
failure is not reported as a pass or patched around in production code.
No Phenix/Coot execution or scientific activation was added by W70.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/test_topostitch_recut_bundle.py tests/test_topostitch_continuations.py \
  tests/test_topostitch_forest_bundle.py tests/test_topostitch_backbone_intent.py \
  tests/test_topostitch_recut_view.py tests/test_topostitch_cut_preference.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /path/to/wheels .
```

The host used its NASolve Python 3.12.14 `.venv`, adding the isolated installed
Gemmi site to `PYTHONPATH`; the exact vectors are retained locally. Wheel SHA-256:
`9298b86b4b2c57c31aa1c0ab2b041ce6c6eac606053cefca2e2cc6a731992f12`.


W70's installed virtual composition with Rowan's final Cedar tip `dca8ee82` passes
**558 tests + 16 subtests** (43.24 s): 482 TopoStitch owner controls plus the 76
combined statistics-parser/refinement-runtime/parallelity controls. Six helps pass;
old and schema-2 public packets, graph descriptions and authenticated source-native
links replay exactly through the default installed Cedar owners after relocation
with original paths blocked. Cedar's runtime bytes/package metadata are unchanged
from tested `a2e73603`. No new native execution or full combined-suite claim.
Virtual tree `ff0935d44624430498eeb86674d8c97d80371267` retains seven documentation
conflicts and no source conflicts; no branch, index or worktree is merged.


Local `W70-evidence.tar.gz` in the same archive root has SHA-256
`14e20204056e7601da11afab21be873e3a9c99c93671b662b617d100c1028236`.
All indexed payloads were read back and verified, including the initial denied
full-suite attempt. The local session index records verified disposable source/
installation/test-copy cleanup; scientific outputs and negative evidence remain.
The convenient `W70-graph-description.json` is a read-only report, not a proposal.


## W71 — Reconstruct image-bearing angle diagnostics explicitly

`topostitch_native_terms.freeze_native_angles` now compares every live angle's
indices, labels, ideal, weight and origin with its supplied native capture, then
records the otherwise uncaptured `sym_ops` and `slack`. The caller must first
authenticate that capture through Cedar's existing owner. The schema-1
`topostitch-native-angle-snapshot` contains the complete ordered family, atom
labels, native-context digest, cell and space group; it has no operational paths
or runtime authority. Absent versus explicit identity operators remain distinct.
Zero weights and nonzero slack are preserved rather than silently reset.

`validate_angle_snapshot` is available without Phenix. `NativeAngleSnapshot`
requires an independently retained snapshot digest, validates native group/metric
compatibility and canonical operators, and reconstructs its own private array.
`evaluate(points, atom_labels=...)` requires the exact ordered inventory and calls
the native angular kernel with the explicit unit cell. It returns an unnormalized
family target and Cartesian gradients, with source/point bindings. Changed live
metadata refuses before evaluation or serialization. JSON records, copying and
trusted local Python pickle reconstruct operators rather than pickling the native
array. No source manager or native installation is changed.

This is an **angle-family observer**, not an additive correction: adding it to a
manager already containing those angles would double count. A hash is not creator
authentication. The snapshot does not authorize a seam, infer image placement,
remap a selected atom subset, reconstruct other term families or restore an
ordinary Phenix model manager. Duplicate atom labels/repeated indices within one
angle, improper operations, unsupported fields and excess budgets refuse.

The developer diagnostic is reproducible without structure inputs:

```bash
PYTHONDONTWRITEBYTECODE=1 phenix.python -B \
  scripts/probe_topostitch_native_images.py --angle-snapshot-only --out new-angle-check.json
```

Under **Phenix 2.2.1-6174**, the synthetic nonorthogonal R3 control passes JSON,
deepcopy and pickle reconstruction, finite differences (largest absolute error
1.42e-6), native subset/reindex observation and deliberate metadata/ordering/group
refusals. Raw native proxy pickle and cell omission still give the wrong energy;
these are retained negative controls. A wheel-only installation reopens the
pickled adapter in a fresh native interpreter after its test directory moves.
The first installed attempt mixed Python 3.12 NumPy with Phenix Python 3.11 and
failed; the separate dependency-free wheel directory fixes the test environment,
not Phenix. Both failed logs are retained locally.

A fresh maintained Cedar bootstrap at `dca8ee82` reproduces the authenticated
855-atom source exactly. Each of the two saved cuts retains all **1,467 angles**,
including its eight crossing terms. The full source residual is
**3753.3791532751893**; transported residual errors are below **9.6e-12**, rotated
gradient errors below **6.7e-10**, and three predeclared full-coordinate directional
checks at two step sizes have errors below **1.83e-5**. JSON/deepcopy/pickle
reproduce each complete evaluation exactly. Raw proxy pickle instead gives
9364.86008654694 / 9200.516898451082. These are complete native diagnostics,
**not refinement executions, chemical approval or R-factor improvement**.

Validation: 27 added software cases (26 demonstrated failures before the API was
added); focused **101**, full Willow **1,715 + 229 subtests**, installed/relocated
**509**, six entry-point helps, lean import and Python 3.10 syntax. Old/new packet
and graph replay remain exact with original paths blocked. The first focused
invocation omitted the optional topology environment and retained 15 Gemmi
import failures; the properly provisioned invocation passed. Commands use
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src` plus the declared topology environment,
and `pytest -q -p no:cacheprovider`; the full run used owned-process permissions.
Scientific snapshots, inputs and outputs remain local and excluded from Git.

The next gate is complete seam terms/exclusions and supported Cedar lifecycle
integration. The W68 ordinary-manager cell omission remains unresolved. P04 stays
partial; P02/P03, physical closure and human review remain separate prerequisites.


W71's installed virtual composition with Cedar `dca8ee82` additionally passes
**585 + 16 subtests**, six helps and exact old/new default-owner native-link,
packet and graph replay. Only the angle-observation module differs in runtime
from the W70 virtual tree. Seven documentation conflicts remain, zero source
conflicts; no actual merge or full combined-suite claim. Runtime commit:
`0e8e62986158f8b4373506c5ea34baece223621f`.


## W72 — Evaluate complete geometry in a retained reference frame

The source seam inventory contains **two bonds, eight angles and six torsions**
for each saved cut. No captured chirality, constant-dihedral, planarity or
parallelity term crosses these particular whole-residue image assignments.
That observation is not a universal seam recipe or evidence that an omitted
source term is unnecessary.

A read-only alternative keeps the complete authenticated source geometry manager.
For a fixed representative assignment `y_i = R_i x_i + t_i`, evaluate its existing
objective at `x_i = R_i^T (y_i - t_i)`, then return `R_i g_i` as the gradient with
respect to `y_i`. Existing `CartesianImage`, `expand_sites` and accumulated
image-gradient transport supply this arithmetic; Cedar supplies native evaluation
and directed-neighbor capture. No proxy family is replaced or added. The same
source bond tables and exclusion rules remain in force. This preserves existing
chemistry; it cannot create an intended connection missing from the source or
make a physical gap disappear.

Three retained complete **Phenix 2.2.1-6174** diagnostics, using fresh maintained
Cedar `dca8ee82` reconstruction, establish the following bounded observations:

- Both cuts preserve the complete source objective, component sums and rotated
  gradients at the source and deterministic 0.002/0.03 Å perturbations.
- A second attempt explicitly resets/rebuilds native pair caches. Its 1.5 Å
  numerical stress case changes neighbor membership; source and mapped evaluation
  still have identical directed pair/mapping/function inventories. Maximum target
  difference is 2.24e-8 and gradient difference 1.29e-9. This deliberately distorted
  stress case is not a candidate model or evidence of good geometry.
- Three full-coordinate directions at steps 1e-4, 1e-5 and 1e-6 Å satisfy the
  predeclared screen: at least two step sizes below 1e-4 error, all below 1e-3.
  The largest observed directional error is 1.15e-4. Static native definitions
  remain unchanged. Directly sending recut coordinates to the original manager
  instead triggers its long-bond refusal; that negative control is retained.
- A third local microprobe exercises the actual `mmtbx.restraints.manager`
  energy entry with an experimental geometry facade. Both cuts pass gradients
  on/off, normalization on/off and preseeded shared gradient buffers: **12 cases**.
  Rotate only the newly computed contribution, then accumulate into the caller's
  buffer. Outer normalization retains **11,378 restraints**. It must not rotate
  or double-count a preexisting caller contribution.

**Selection remains a demonstrated blocker:** delegating the facade's identity
selection to its source manager silently drops the image mapping. The selected
ordinary manager then refuses the recut coordinates. A real implementation must
rebind mappings and source identities explicitly at selection/reconstruction;
ordinary model pickle/rebuild cannot be assumed to retain a restraint manager.
The facade is local experimental code, not installed or attached to refinement.

No production code, schema, model, restraint, checkpoint or installation changes
in W72; W71 remains the runtime and software-test baseline. Native commands were
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/verified/Willow/src python run-owned.py`,
launching `phenix.python -B probe.py` through Cedar's owned runner with a 600 s
watchdog. Attempts 1/2/3 retain 89/93/89 counted evaluator calls respectively;
Cedar's additional two-pass neighbor captures are separately retained. These are
actual executions, not dry runs, optimization or full refinement. Scripts,
source hashes and scientific results stay local.

This makes whole-objective reference-frame evaluation a promising candidate for
the existing Cedar lifecycle, without closing P04. Further gates include explicit
selection/reindexing, reconstructed source identity, callback/NCS policy, ADP
coordinates/tensors, gradient-buffer semantics at all consumers, normalization,
and diffraction/geometry frame agreement. A standalone recut PDB does not carry
this runtime context and is not thereby safe for stock Phenix. P02/P03 and human
review still precede any supported ASU materialization.


## W73 — Retain complete frame bindings through explicit reindexing

`topostitch_transport.ReferenceFrame` is a small immutable numerical binding over
existing `CartesianImage` arithmetic. It stores complete distinct source labels,
one image per source atom, a caller-owned context SHA256, and a complete permutation
from current representative order to source order. `to_source`,
`to_representatives` and `gradients_to_representatives` require explicit matching
labels/context. `reindex` composes a full permutation without discarding any atom
or its image. Partial/duplicate/out-of-range selections refuse. Translations act
on positions, never gradients; no two source atoms are merged.

This adds no artifact schema, command, native manager, selection hook or approval
policy. Explicit matrices are trusted numerical inputs, as for `CartesianImage`;
the caller must authenticate the source, verify crystal membership when compiling
images and recompute a context that binds cell/group and effective model/restraints.
Passing an unchanged digest without checking the actual context proves nothing
about a changed manager. The class never assumes that native selection preserved
its mapping. Copy and trusted local pickle contain plain Python data only.

Twelve added software cases all fail before implementation and pass afterward,
covering independent finite differences, full round trips, composed permutations,
identity/context drift, partial selections and detachment/serialization. Focused
checks pass **113**, full Willow **1,727 + 229 subtests**, installed/relocated
**521**, six helps, lean import and Python 3.10 syntax. Original packet/graph replay
remains exact after relocation with source paths blocked. Validation uses the
same declared W71 Python/topology environments and owned-process permissions.

A fresh **Phenix 2.2.1-6174** diagnostic consumes the actual new class through the
local W72 geometry-energy facade. Identity, reversed and cyclic complete orders
pass across both cuts, normalization on/off, gradients on/off and preseeded
buffers: **36 cases**, with maximum gradient error **1.16e-9**. The original
source manager stays intact. Partial/duplicate selection and a changed actual
unit cell refuse before native evaluation. Installed plain frame records reopen
and retain reversed correspondence in a fresh native interpreter after their
original directory is gone. The local facade is still **not installed**; these
are complete energy-entry diagnostics, not ordinary refinement.

The current safe boundary is explicit **complete-model reindexing**. Native subset
selection, model reconstruction, callbacks, NCS, ADPs and materialization remain
unqualified. Future Cedar integration must deliberately consume/rebind this
mapping, preserve complete source identity and refuse unsupported lifecycle paths.
Existing runtime behavior and schemas remain unchanged; generated science stays
local and outside Git.


W73 runtime `c4add34c3cdee0582e50efbf9f104e6b63de7698` also passes an installed
virtual composition with Cedar `393aea60`: **640 + 16 subtests**, including the
43 new Cedar numerical-reference tests, six helps and exact old/new default-owner
native/packet/graph replay. Seven documentation conflicts remain, zero source
conflicts; no branch merge or full combined-suite claim.


## W74 — Check diffraction agreement and deeper model boundaries

A complete native diagnostic extends W73 to the actual
`mmtbx.model.manager.restraints_manager_energies_sites` entry and to a synthetic
`mmtbx.f_model` least-squares target. It uses **1,008 calculated reflections to
6 Å**, neutral `wk1995` scattering, direct structure factors, zero solvent scale,
fixed deterministic synthetic amplitude perturbations and fixed synthetic test
flags. **No experimental reflection data or existing Free-R flags are used or
changed.** These synthetic R factors measure representation agreement, not repair
or experimental improvement. Geometry weight `1e-6` is a declared arithmetic-test
weight, not a proposed refinement calibration.

The first attempt correctly stops at an isotropic-only guard: **all 855 source
atoms carry anisotropic displacement tensors**. Its failure remains. The second
attempt rotates the existing tensors in memory by the same `R U R^T` rule as W55
(expressed natively as fractional `U_star` congruence), preserving flags and other
scattering parameters. ADPs are not refined and no coordinate/tensor file is written.

| Native observation | Cut 1 | Cut 21 |
| --- | ---: | ---: |
| Largest complex Fcalc difference | 1.61e-11 | 9.84e-12 |
| Largest diffraction-gradient discrepancy | 9.42e-18 | 4.31e-18 |
| Largest joint-target directional error | 3.84e-12 | 1.94e-12 |
| Fcalc discrepancy if tensor rotation is omitted | 363.27 | 340.97 |

Three directions at steps 1e-4/1e-5 Å pass the predeclared joint-target derivative
bound of 1e-6. Synthetic work/test R factors agree within 1e-10. Native model-level
coordinate-energy calls also reproduce the already checked restraint-manager
values. This is **Phenix 2.2.1-6174** execution, not optimization or ordinary
refinement; anisotropic-parameter derivatives and serialized tensors remain open.

Both actual model identity selection and `deep_copy` hit a new explicit boundary:
`model.select` immediately calls `geometry.pair_proxies` after selecting its
restraints. The narrow experimental facade deliberately has no such forwarding
method, so both operations refuse. Merely returning source-frame pair tables to
consumers using representative coordinates would not establish correct distances,
indices, exclusions or `.geo` reporting. Also, `model.select(flex.size_t(...))`
converts indices to a boolean selection: W73's lower-level full permutation test
must not be described as a model-level reorder.

Pinned installed source additionally shows:

- Coordinate minimization consumes the model energy entry and adds its Cartesian
  gradient to the diffraction gradient; this joint-frame arithmetic is now tested.
- ADP weighting/restraints directly consume geometry pair tables and the x-ray
  structure. They remain outside the tested coordinate-only scope.
- Model `deep_copy` uses selection. Model pickle deliberately removes its
  restraints manager; reloading ordinary model state therefore needs explicit
  source-context reconstruction, even if plain frame data themselves survive.
- Weight shaking, geometry minimization, native geometry reporting and auxiliary
  managers have further direct geometry consumers. They need an explicit supported
  protocol, not unrestricted attribute forwarding.

**Next bounded integration gate:** inventory the precise coordinate-only consumer
protocol with Cedar; bind current model/source/frame identities and native effective
parameters, handle supported model copy/selection and pair-table/reporting semantics,
and refuse unsupported partial selection, callbacks, NCS, ADP/TLS, cell changes and
rebuilds before evaluation. Then qualify a fresh-process ordinary entry and matched
refinement control. Keep physical gaps, missing intended links and P02/P03/human
review separate. A passing synthetic joint target is not an installation-ready
refinement adapter or permission to materialize an ASU.

W74 changes evidence/docs only; runtime remains W73 and its full/install/combined
validation remains applicable. Both local attempts, exact scripts and native source
hashes are retained. Some preparation/execution metadata inherited older angle-probe
wording; local scope/provenance addenda identify that wording and the actual executed
scripts/results without rewriting the original evidence. No scientific payloads are
committed or uploaded.


### W71–W74 local retention

The declared Git-ignored `TopoTrace/local/topostitch-native-2026-11-15`
evidence root retains the completed native probes, failed attempts, effective
contexts, scripts, wheels and exact test receipts. Every payload was read back
from its archive and checked against its relative-path size/SHA-256 manifest.
Only verified duplicate build/test trees were removed; scientific inputs,
results, probes and supporting native-only installs remain locally available.

| Update | Archive | SHA-256 |
| --- | --- | --- |
| W71 | `W71-evidence.tar.gz` | `8fb5671d0a5fe2f88df1c83a27a4092ebf1181f9868fb28e595a1620b5b83df0` |
| W72 | `W72-evidence.tar.gz` | `9acf21c1b4db788915cd47880d95009130da5b10c9ee4537fa56ed490c712b46` |
| W73 | `W73-evidence.tar.gz` | `89667cc2a2806d9e70f3921161190f6ba2ae50fefee8a49b0dc6e76fb637e8fa` |
| W74 | `W74-evidence.tar.gz` | `686579bbdfe4306bb7f933a13a11f8296888e78a227e9a9b611d45f47acb9353` |

Each archive includes a scope/provenance addendum distinguishing the actual
executed experiment from inherited angle-probe metadata. Additional installed
source hashes in that addendum were recorded after execution; the native
reconstruction's own effective-context checks remain in the original receipts.
These are forensic records, not resumable portable NASolve runs. Restoring an
experiment requires its declared source/environment and verified anchored inputs;
old absolute paths are provenance, not a basename-search instruction. No generated
scientific payload is committed or uploaded. W73 remains the runtime baseline.


## W75 — Observe stock native consumers before choosing an integration hook

A local Python call profiler observes five installed Phenix **2.2.1-6174**
modules during an ordinary source-model dry-run and one coordinate-refinement
cycle. It does not replace any geometry method or install a facade. The unchanged
855-atom source and W74's 1,008 synthetic amplitudes/test flags are used; no
experimental dataset, recut model or existing run is modified.

The dry-run completes with zero cycles. The coordinate control completes one
`individual_sites` cycle, `main.max_number_of_iterations=5`, `nproc=1`, LS/wk1995,
bulk-solvent/overall ADP scaling off and no ordered solvent. Native weight
estimation retains its default shaking/regularization: **five requested coordinate
iterations is not a five-evaluation cap on the whole job**. All attempts use a
600-second owned-process watchdog. The synthetic refined output is a diagnostic,
not an adopted model or evidence of useful experimental repair.

| Observed interface | Dry-run calls | Coordinate-cycle calls |
| --- | ---: | ---: |
| Native model `deep_copy` | 2 | 9 |
| Native model `select` | 4 | 18 |
| Geometry-manager `select` | 9 | 28 |
| Geometry-manager `pair_proxies` | 16 | 127 |
| Geometry-manager `energies_sites` | 2 | 94 |
| Model `restraints_manager_energies_sites` | 0 | 10 |
| Geometry `write_geo_file` / `show_sorted` | 1 / 1 | 1 / 1 |
| Geometry `get_struct_conn_mmcif` | 0 | 1 |

The 94 geometry evaluations are attributed to **54 geometry L-BFGS**, **20
Cartesian-dynamics**, **9 statistics** and **11 restraint-manager** calls. The
last 11 comprise ten model energy calls plus one weight-estimation call. Thus a
patch at only the model energy entry would miss real consumers, even in this
coordinate-only control. Standard mmCIF writing also consumes the native bond
description; an energy-equivalent frame does not automatically qualify that output.

State matters as well as method names. `adp_weights` is entered with
`compute_wxu=False`, and `update_dihedral_ncs_restraints` sees no NCS-dihedral
manager. Those observed calls do not establish ADP/NCS support or justify silently
forwarding active branches. Two `add_angles_in_place` calls originate in native
conformation-dependent model preparation; a later binding must distinguish that
construction phase from forbidden changes after freezing effective restraints.
All observed selections retain all 855 atoms. This says nothing about ordinary
partial selection or model-level reordering.

A matched unprofiled coordinate run gives **identical PDB atom/ANISOU/cell records
and identical `.geo` bytes**. Full-precision maximum coordinate/tensor changes
also agree; all full-precision in-memory coordinates were not serialized for this
comparison. A caller/state-aware repeat matches the same saved records and report.
Anisotropic flags remain intact, with maximum `U_star` difference 2.04e-11 between
independently interpreted initial/final structures. Two setup failures remain:
the first used the wrong flex namespace for Miller indices; the second requested
the old test-flag PHIL namespace. The successful input explicitly uses
`data_manager.fmodel.xray_data.r_free_flags.test_flag_value=1`.

### Next implementation contract

For **pure representative recuts**, first evaluate a whole-process boundary:
keep native refinement, its copies, weights, neighbor tables and reports in one
computational/source frame, and derive the chosen displayed representatives at
explicit workflow boundaries. This is the next integration candidate agreed with
Cedar after W78/W79, **not an installed runtime protocol**. It avoids requiring
an in-engine facade merely to display another equivalent cut.

Bind every derived view to exact source atom identities, image operators,
displacement tensors and immutable checkpoint lineage. Scientific statistics
belong to the computational model. A changed computational child needs a fresh
source binding; an old cut preference must never be silently rebased. Re-entered
exports or Coot edits require an explicit checked inverse mapping. Additions,
deletions, renames or changed topology/chemistry intent require fresh qualification,
not reuse of an old frame. Neither a view nor an exported recut is automatically
an independent Phenix input.

This route does not repair missing links, winding seams or physical gaps, qualify
special-position inventory, or close P02/P03/P04. Keep those gates and Cedar's
live source-policy/lineage requirements. Only pursue an in-engine facade if a
concrete supported workflow still needs one; in that case the following bounded
contract remains necessary:


1. **Freeze after native construction.** Bind the complete ordered source,
   crystal, effective live restraint parameters and image frame after ordinary
   preparation has finished. Recompute/verify that identity before use; repeating
   an old digest is insufficient. An initialization mutator is not permission to
   mutate the frozen objective later.
2. **Keep one complete geometry owner.** Energy, derivative, statistics and
   weight/regularization consumers must use the same source-frame semantics.
   Preserve private gradient accumulation and outer normalization from W72/W73.
   A model-energy-only patch or unrestricted attribute forwarding is inadequate.
3. **Make copies and reports explicit.** Qualify complete model copies with
   source reconstruction and bound frames. Pair tables, distances, `.geo` and
   mmCIF bond exports must have declared coordinate/image semantics. Do not return
   raw source tables to representative-coordinate consumers merely to make a
   call succeed. Reject unsupported partial selection/reordering and changed
   chemistry/cell before evaluation or export.
4. **Qualify weights separately.** Random shaking in one frame is not the same
   atomwise displacement as reusing its random seed in another frame. First
   compare explicitly fixed, source-bound weights or a correctly transported
   weighting experiment; then assess ordinary automatic weighting. Do not hide
   weight-estimation differences inside a supposed representation-invariance test.
5. **Distinguish disabled from supported branches.** Verify NCS/ADP/TLS/IAS,
   callbacks and auxiliary managers are absent or explicitly qualified. A no-op
   entry can be allowed only with its inactive state bound; its active version
   remains unsupported. Reuse Cedar's process/preflight/lineage owners without
   expanding its qualified parallelity-only hook by implication.
6. **Prove the complete supported path.** A future adapter must pass fresh-process
   source/representative controls, copy/report checks and matched actual refinement
   before ordinary activation. This profiling exercise is only a lower bound:
   it covers Python calls in five modules, not every C++ consumer or attribute
   access, and does not close P03/P04 or the missing-link/physical-gap gates.

W75 changes documentation/evidence only; runtime and full/install/composition
validation remain W73. Exact commands, scripts, effective parameters, initial
failures, stock outputs and matched comparisons remain local. No scientific
payload or standalone diagnostic subsystem is added to the repository.


Local `W75-evidence.tar.gz` in the same declared evidence root retains all 85
payloads, read-back verified against its manifest. Archive SHA-256:
`9b68353c8d8f72001b1b5445bdf825ad886ac9ba1b5192ce64df1babafd32d7c`.
The original W75 probe directories remain available for Cedar coordination.
This archive has the same forensic-only, non-publication limitations as W71–W74.


## W76 — Represent captured native contacts in chosen crystal images

`topostitch_packing.reframe_native_packing` adds a read-only report to the existing
packing owner. The caller supplies Cedar-authenticated native evidence, its exact
digest, complete ordered atom labels and images, an explicit space group, and
Cedar's maintained nonbonded reviewer. Gemmi is imported only for this optional
operation; existing packing comparisons remain unchanged.

For a source contact `x_i → h x_j` and representatives `y_i = g_i x_i`, the report
uses the exact relative operation **`g_i h g_j^-1`**. It retains lattice translations,
reciprocal/self-image rows, native multiplicity, weights and source proxy kind.
Source simple terms stay labelled as source simple terms even when the new drawing
crosses symmetry. It checks both the Cartesian composition and agreement with the
reviewed native distance; direct-ASU distance is separately labelled. No neighbor
search, native proxy/table reconstruction, exclusion edit, new bond or physical
identity/special-position approval follows.

The new schema-1 kind `topostitch-representative-native-packing` records the source
digest, complete frame and frame digest, contacts and numerical discrepancies.
It is a diagnostic return value, not a persisted run/checkpoint schema or runtime
permission. The existing comparison kind/schema and all installed CLI defaults
remain unchanged. A stale source, reordered/incomplete identity, non-group image,
incompatible cell metric, invalid native review or changed input refuses.

Synthetic screw-axis, noncommuting image, reciprocal/self, translation, duplicate
row, empty-inventory and context-drift controls protect this scope. Nineteen new
tests fail before implementation; three further empty/metric/overflow controls supplement
them. The focused packing/transport/graph/native-link group passes 118 tests.

Authenticated replay of the existing Phenix **2.2.1-6174** source capture preserves
**8,305 directed rows per cut** for both retained public controls. Maximum distance
error is **1.69e-14 Å**; the captured native total residual remains
1115.6313838790597 with its original weights/multiplicity. This is host-Python
read-only capture replay, **not a fresh native execution** or refinement.
Source model, receipt and plan bytes remain unchanged; all reports stay local.

This closes a bounded report-arithmetic component of P04, not P04 itself. Native
model copying, pair-table consumers, source construction/freeze policy, automatic
weighting and output serialization still require their own integration. Cedar owns
the separately demonstrated hierarchy/scattering-ADP export synchronization; do
not implement a second exporter or subtract a logged B shift from old models here.


Installed/relocated W76 validation passes **564 tests**, all six entry-point helps,
lean import, Python 3.10 syntax and exact old/new packet/graph replay with original
source paths blocked. Wheel SHA-256:
`45ce8b63acf4c4f314e5df8af28bd4d8947d16c343e3e7742ffd13a714cec61e`.
The complete suite passed **1,748 + 229 subtests** before the final finite-distance
guard; that newly demonstrated failure is fixed and passes focused/installed
checks. Final complete-suite validation waits for Cedar's serial native window.


## W77 — Bind contact reports to immutable saved previews

`topostitch_recut_bundle.observe_relabel_native_packing(preview_directory,
native_receipt, *, cedar_source=None)` supplies the authenticated bridge from an
existing saved representative preview to W76's contact arithmetic. It reuses the
native-link observer's packet/capture owner, now factored into one context shared
by both read-only reports. Cedar still authenticates captures and reviews native
nonbonded evidence. The development `cedar_source` option remains explicit; a
combined installation uses its installed Cedar owners.

The bridge resolves complete atom correspondence in native order, checks the
captured cell and exact source coordinates against the saved preview, derives
whole-residue images from the frozen proposal and verifies its transformed points.
It then returns a new schema-1
`topostitch-representative-native-packing-observation` with source/preview/capture
hashes, coordinate discrepancies and the W76 report. Input bytes are checked
again before the context closes. Reordered native storage can be mapped without
reassigning identities; incomplete, shifted or stale data refuse. The existing
unambiguous-residue/whole-residue preview scope is retained.

This API creates no output file, changes no packet/checkpoint schema and leaves
all CLI/view defaults and existing native-link report fields unchanged. It does
not export coordinates/tensors, replace native pair tables, add contacts, change
exclusions or approve topology/refinement. In particular, a packing-distance
report does not qualify the separate scattering/hierarchy ADP serialization gate.

Seven new regressions fail before implementation. The focused native-link,
packing, packet/view/preference and continuation group passes **167 tests**.
Both existing public saved previews produce packing subreports **exactly equal**
to W76's independently assembled inputs, preserving all **8,305 directed rows**
per cut. Source-coordinate discrepancy is at most 7.11e-15 Å; proposed-coordinate
discrepancy is at most 1.43e-14 Å. This replays authenticated Phenix 2.2.1-6174
captures on the host; it performs no fresh native execution. Scientific outputs
remain local, and P04 integration remains open.


W77 final validation: **1,756 tests + 229 subtests** in the complete Willow suite,
**571 installed/relocated tests**, all six helps, lean import, Python 3.10 syntax,
exact old/new packet/graph replay with original paths blocked. This includes W76's
final finite-distance guard. Wheel SHA-256:
`861b2e50289baa6174a6fe2c3c3dd70abb2857f9b98bf967c38a6896ea7aa7f2`.
No combined-Cedar full-suite result or native manager activation is implied.


## W78 — Distinguish source-manager copying from policy preservation

Complete **Phenix 2.2.1-6174** source-only diagnostics reconstruct the authenticated
855-atom source through the current maintained Cedar worker (`c4adb6b2`). The
observed native context matches the frozen capture before any copy experiment.
No facade, representative coordinates, optimization or refinement is installed.
These are complete diagnostic executions, not dry-run predictions.

The experiment records every public non-callable field on angle, dihedral,
constant-dihedral, chirality, planarity and parallelity proxies; it also checks
Cedar's static bond signature, W71's full angle snapshot, checked torsion/plane
rows, crystal and ordered model labels. That inventory is explicitly **not** a
complete nonbonded-policy fingerprint. At the source and deterministic 0.002/0.03 Å
perturbations, original and copied managers independently rebuild neighbor tables.

| Source-only copy route | Energy / gradient result |
| --- | --- |
| Geometry identity selection | Exact in all three coordinate controls |
| Actual model identity selection | Exact in all three coordinate controls |
| Actual model `deep_copy()` | Exact in all three coordinate controls |
| Python `copy.deepcopy(geometry)` | Fails: complete nonbonded residual disappears |

At the original coordinates the failing copy retains **8,305 contact rows**, but
its nonbonded residual changes from **1115.6313838790597 to zero**. The full target
changes from 7222.455461706065 to 6106.824077827005, and maximum component gradient
error is 397.51122015948863. At the two perturbations, 8,296 and 8,291 contacts
remain, again with zero copied nonbonded residual. Other reported family energies
match. All four copy routes preserve the inspected proxy metadata; changing a
single angle weight only on each disposable clone leaves the original snapshot
intact, while the W71 checker rejects the changed clone. This establishes only
that particular mutation's isolation, not independent ownership of all tables.
Parallelity is absent in this source.

A separate tiny native-object control, with no scientific input, reproduces the
serialization mechanism: `nonbonded_params` deepcopy and pickle drop populated
radius, ionic-radius and donor/acceptor tables while preserving the five scalar
options. The PROLSQ function's four parameters survive unchanged. The installed
`nonbonded_bpl.cpp` pickle wrapper serializes only scalar constructor arguments,
not those tables. Ordinary identity selection instead passes the source parameter
object into the new manager; its numerical success does **not** prove independent
mutable policy ownership. No installed cctbx/Phenix code is changed.

The initial fail-fast attempt is retained. Its detailed follow-up records all
four routes without changing thresholds; `SOURCE_COPY_MISMATCH` remains a failure,
not a promoted pass. Preserve this negative control alongside W68's image-angle
serialization loss. Future source ownership must authenticate live parameter
and exclusion tables, use qualified native selection or explicit reconstruction,
and reject unsupported copying; equal proxy counts or scalar settings are not
enough. A report of captured coordinates cannot replace rebuilt native tables.
No complete exclusion policy, arbitrary partial selection, recut copy, pair-table
consumer, ordinary refinement, physical gap repair or scientific acceptance is
qualified here. Source/receipt bytes and historical evidence remain unchanged.

### Current installed Willow/Cedar composition

An isolated virtual tree combines Willow `7e846aec` with published Cedar
`794e0d7b`, including its versioned output synchronization and dictionary-target
inventory checks. Tree `4266c2e1fe2868968dfe0c6267b7c23c3d91be75` has **zero source
conflicts and seven documentation conflicts**; neither branch is merged or moved.
The built wheel is installed into a separate prefix, its original source directory
is removed by relocation, and **782 tests + 16 subtests pass**. This includes all
571 TopoStitch cases plus combined AutoRefine, refinement runtime/parallelity,
output synchronization, bond-reference and native target-delivery checks. All six
entry-point helps pass. Old/new packet, graph and default-owner native-link replay
stay exact with original paths blocked; the new saved-preview packing report is
also exactly equal. Wheel SHA-256:
`417692da12b71bb98d01a24d4f2600fe9eefc867b9edc1d3133bfaed611cc30c`.

The local `virtual-integration/receipt.json` records exact build/install/test and
help commands. Validation uses `PYTHONDONTWRITEBYTECODE=1` and the installed
package prefix on `PYTHONPATH`; native calls use the pinned Cedar process owner
and its explicit `phenix.python -B probe.py` invocation. W78 changes documentation
and evidence only. W77's full Willow **1756 +229** and installed **571** remain the
runtime baseline. This composition check is not a full combined suite or a native
combined refinement. Scientific outputs stay local; migration impact is none.


## W79 — Keep outlier queries in the same frame as the energy

A complete local **Phenix 2.2.1-6174** diagnostic reconstructs the same authenticated
855-atom source through maintained Cedar `c4adb6b2`, then calls actual
`mmtbx.model.statistics.geometry` with source coordinates, an energy-only local
representative facade, and a facade whose four outlier callbacks explicitly map
query coordinates back to the source. Both saved cuts are tested at the original
coordinates and a deterministic 0.002 Å perturbation. This is a reporting execution,
not refinement, an installed hook or a model writer.

The native statistics constructor obtains scalar deviations from the returned
source-frame energy object, but its bond/angle/dihedral/chirality methods pass
hierarchy coordinates back into `get_*_outliers`. Without remapping those calls,
scalar targets still agree while **outlier identity is wrong**. The source has
four dihedral outlier quartets: cut 1 loses two; cut 21 replaces one with a different
quartet, at both coordinate controls. Other measured families do not show changed
outlier lists in this particular fixture; this is not proof they are generally safe.

A diagnostic-only remapping of all four callback inputs restores the exact source
outlier lists and scalar statistics (largest absolute difference **3.55e-11**).
The returned native atom indices remain in source order; this test does not qualify
arbitrary model reordering or frontend selection indices. The static source
signature remains unchanged. We do not install the facade, forward unknown methods,
change native definitions, patch Cedar/cctbx, or infer full live-policy ownership.

The source-frame `.geo` writer is also checked after inverse mapping. Raw output
is **not byte-identical**: the observed differences are equivalent +180/-180 ideal
angle display and ordering of nearly equal nonbonded distances. A separate host
audit normalizes only the explicit sinusoidal dihedral ideal display and compares
nonbonded records as multisets, retaining every directed label, printed distance,
VDW value, symmetry string and multiplicity. All four comparisons agree; each
contains 8,305 cached contact rows. This is source-frame report equivalence, not
representative-frame operator/export qualification or a forced-neighbor-rebuild
test. Raw reports and the exact differences remain preserved.

The first host preparation lacked the optional Gemmi path, and the ensuing native
attempt refused missing plans. Both failures remain; the successful second attempt
uses the topology-enabled host environment and keeps the native Python environment
separate. The native invocation is `phenix.python -B probe.py` through the maintained
Cedar process owner; the host comparison is `python compare-reports.py`, both with
`PYTHONDONTWRITEBYTECODE=1`. No runtime/schema changes or migration occur, so W77's
full **1756 +229**, installed **571** and W78's combined **782 +16** remain the
validation baseline. Complete policy binding, pair-table consumers, representative
reports/exports and ordinary recut refinement remain open.

### Local evidence preservation for W76–W78

The existing declared local evidence root now retains the following forensic
archives. Every payload was read back and checked by size and SHA-256 before
removing any disposable build copy. Generated science remains uncommitted and
unuploaded; these are not portable resumable campaign runs.

| Update | Payload files | Archive SHA-256 |
| --- | --- | --- |
| W76 | 321 | `518f6442af7c5204c9b2c6311ea88d2a9833487ca191e0065cec271bfd2cedee` |
| W77 | 320 | `4d5f35b5198e9968a885ed58b3902759a5b70ff6282bbb74e6b79a674a2a3c5a` |
| W78 | 2008 | `467776cd11d3267d28e2a54519a27acf28bd759b56a919c39746760a1726f9d2` |


## W80 — Bind Cartesian displacement tensors to the coordinate frame

`CartesianImage.rotate_tensor` provides the existing preview's `R U R^T` rotation
in the shared transport owner. Its six-component order is
**U11, U22, U33, U12, U13, U23**, in Cartesian coordinates and unchanged caller units.
Translation has no effect. `ReferenceFrame.tensors_to_representatives` and
`tensors_to_source` apply that rotation with the same complete ordered atom labels,
caller-authenticated context and full permutation as coordinates/gradients. Missing,
nonfinite, stale or ambiguously assigned tensors refuse; `None` does not silently
choose an isotropic/anisotropic policy. Fractional `U_star` must be converted by
the caller, and the arithmetic does not validate physical ADPs or their flags.

The existing bend-preview ANISOU writer now calls this rotation, preserving its
integer PDB scaling, summation order, field rounding, unchanged-source behavior and
field-width rejection. The independent Gemmi scattering observer remains an
independent oracle. No new writer, packet schema, automatic tensor inference,
ADP optimization, chemistry or representative-ASU export is introduced.

Thirteen new regressions fail before implementation. They check independent Gemmi
rotations in triclinic, tetragonal and hexagonal settings, trace/norm/roundtrip
invariants, off-diagonal signs, full reordered atom binding, translation independence
and invalid/overflow refusal. The focused transport/preview/scattering/endpoint/
packet/fitter group passes **184 tests**; the complete Willow suite passes **1769 tests +229
subtests**. The installed/relocated package passes **668 tests**, all six entry-point
helps, lean imports, Python 3.10 syntax and exact old/new packet/graph replay with
original paths blocked. Wheel SHA-256:
`056c36f1d346e88e944469eb82250c5d04398a4a26fc4789bbff35d7268833af`.

A fresh **Phenix 2.2.1-6174** execution imports the installed pure-Python wheel into
its native interpreter and reconstructs the authenticated source through maintained
Cedar `c4adb6b2`. All **855 source anisotropic tensors** pass both cuts in identity,
reverse and cyclic atom orders. Native conversion from Cartesian U to fractional
`U_star` agrees with an independent fractional-rotation calculation within
**1.63e-19**; Cartesian roundtrip error is at most **3.56e-15 Å²**. Native direct
`wk1995` Fcalc at **1,008 reflections, 6 Å limit**, agrees within **4.43e-11**.
Omitting tensor rotation produces a 341–363 maximum Fcalc discrepancy, retaining
a sensitive negative control. Source scatterers, anisotropic flags and occupancies
remain unchanged. This is complete diagnostic execution with synthetic calculated
scattering only, no experimental reflections/Free-R, model output or refinement.

Exact commands and logs reside in the local W80 evidence: source tests use
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<topology-dependency-prefix> python -m
pytest -q -p no:cacheprovider`; focused files are transport, preview, scattering,
endpoint, recut_bundle and fit. The installed receipt records its complete test
list and each help/replay command. The owned native call is
`phenix.python -B probe.py`. P03/P04 remain partial; physical inventory, ADP
serialization, native policy and ordinary recut-refinement qualification are
separate gates.

W79's 44-payload forensic archive is also read-back verified, SHA-256
`88b9f5e60e1f863f6a67fba8eac7f1fcbfe2b6eeb0a126981ee2d2757f87a315`.
The W76–W78 duplicate build/test/install trees were removed only after matching
all their files to the verified archives. Native probes and pinned source needed
for Cedar coordination remain available; no scientific source was deleted.


## W81 — Audit the combined installation and narrow the Pine boundary

The first unfiltered combined full suite completed: **4 failed,11,109 passed,
284 subtests passed**,2671.02s. Its frozen inputs are Willow
`2a76967c0182d3a4719f4aab29e6fe7ab5b43b8e` and Cedar C322
`dc82aee125dbe4e2341a3af7be8dd6477d8fb7e7`, virtual tree
`6414a2c8a3071c8f4ed91d8a6b15f147e365f04b`. Zero source/seven documentation
conflicts; no real branch merge. Main pytest imports a fresh isolated wheel after
original build relocation. C323 and W82 are outside this pin.

The failures are retained, not relabelled as a green full suite:

- The ATL shuttle-builder test needs NASolve and NARestraints Git metadata; an
  archived/wheel environment does not meet that source-builder assumption.
- A sequence-family test compares the installed resource path with a checkout
  `src` path. Its content lookup is distinct from that path-equality assertion.
- The C62 construction and C63 context replay readers default to a canonical
  frame under checkout `MR_frames`. That resource is absent from the installed
  wheel: this is an actual installed historical-reader limitation. Cedar owns
  the narrow packaging correction; no Willow runtime workaround was added.

Follow-ups preserve the exact virtual source tree in a separate temporary Git
fixture, plus the exact NARestraints v1.1.3 commit from installed `direct_url.json`.
The four affected modules pass **90 tests +20 subtests** there. Source-only
builder assumptions are therefore tested in their proper context. The installed
C62/C63 reader also passes with explicit `runtime_sources` from its exact pinned
historical commits, all bytes/hash checked, with original checkouts and process
execution blocked; changed canonical bytes refuse. This does not fix the default
installed resource gap. Broad negative `ValueError` tests can otherwise pass too
early on that missing resource, so the installed pass count alone is insufficient
coverage for those reader modules.

The installed old/new graph/packet/default-Cedar native-link and W77 packing
replays pass exactly with original paths blocked; all six CLI helps pass. Wheel
SHA-256 `5d72b573d8874442d2a6582fa0702e0b61fbb87eeb5ed8f054d404e065f1c12b`.
The full command is `PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=<isolated-site>:<topology-deps> <host-python> -m pytest -q -p
no:cacheprovider` from the relocated virtual checkout. Follow-ups use the explicit
virtual source and pinned NARestraints paths in `PYTHONPATH`, targeting only the
four failing tests and then their four modules. Exact commands, environment,
pins, original failures and subsequent receipts remain local under W81 evidence.
Test subprocesses may deliberately exercise source fixtures; do not claim every
child imports the installed wheel. No complete combined rerun was performed.

A separate complete Phenix 2.2.1-6174 synthetic diagnostic uses the installed wheel:
six atoms in triclinic P1, P43, R3:H and P212121, each in identity/reverse order.
All eight cases preserve direct wk1995 Fcalc (maximum error5.01e-13) and tensor
round trips (maximum5.00e-16 square Angstrom). Omitted tensor rotation fails for
rotating images and is neutral for translation-only P1. No experimental data,
coordinate writer or refinement is exercised.

W78/W79 motivate the agreed next integration candidate: retain one computational
native frame and derive explicitly bound views at workflow boundaries. The
[implementation contract](#next-implementation-contract) now records this as the
first route for pure recuts, including fresh child binding and checked inverse
mapping for external edits. No runtime workflow changes or physical repair are
claimed; P02/P03/P04 and Cedar's source-policy gates stay open.

W80's local forensic archive contains505 verified payloads, SHA-256
`0729af914ded3f113a8ea5ede042e3a699e390876eb4b7e8e2806e862ceebc71`.
Every payload size/hash was read back before removing owned duplicate build trees.
It is retained evidence, not a resumable portable campaign; no science was uploaded.

## W82 — Bind numerical frames to immutable saved previews

`load_relabel_reference_frame(directory, *, expected_receipt_sha256)` in the
existing `topostitch_recut_bundle` owner replays an exactly pinned preview and
returns the existing immutable `ReferenceFrame`. Previously callers had to
assemble atom/image correspondence themselves. Now every source atom has a
canonical JSON identity label and an explicit image, including unchanged context
atoms. The complete numerical result must reproduce the saved preview, and
source/receipt drift during compilation refuses.

The context is the exact `preview.json` byte digest, **not** a native policy or
checkpoint identity. This component permits coordinate, gradient and Cartesian
tensor arithmetic through the existing core. It does not infer chemistry, adopt
a cut, bind a refined child, accept Coot edits or write a model. Old packet schemas,
CLI defaults and saved observations remain unchanged; no migration is required.
Physical inventory, ADP presence/flags, scattering and external-edit qualification
remain separate. The planned whole-process boundary itself is not implemented.

Validation of runtime `e570d15f308ec46a0b2bc6f62c43c3346e17abb5`:

- Twelve new boundary regressions fail against the pre-change installed package;
  final focused bundle/transport/recut tests pass99. They cover exact receipt
  pinning, reverse/inverse/tensor mapping, source and mid-load drift, bad transform
  detection, relocation, and unregistered water with alternate/insertion identity.
- Complete Willow suite: **1,781 tests +229 subtests**,94.83s, using
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<topology-deps> <host-python>
  -m pytest -q -p no:cacheprovider`.
- Fresh isolated wheel, relocated tests: **680 passed**,32.24s; six CLI helps,
  Python3.10 syntax and lean imports pass. The original source/build paths are
  absent or explicitly blocked for replay. Both old/new855-atom packets reproduce
  exactly in identity/reverse/cyclic order; maximum preview-coordinate error0.
- Wheel SHA-256
  `351cf56a1033487ac3b5a431120eb8be3aa443bcac8f60accf6dc9a936775cf1`.
  Build used pinned base plus the recorded runtime patch; a separate receipt
  verifies installed source and regression bytes against the final code commit.

Exact build/install/test commands, before-failure logs, receipts and relocated
replay remain local under W82 evidence. No new native execution was required for
this packet-to-existing-arithmetic boundary; W81's older combined build remains a
separate audit with the recorded installed historical-reader limitation. Generated payloads are excluded from Git. Next qualify the
workflow boundary and human review; do not silently reuse this context for a
changed computational child or turn a preview into a Phenix input.


## W83 — Preserve the labelled scattering object at special positions

A pure representative change must preserve the supplied scattering object; it
need not declare that object's chemistry or packing valid. W62's exact labelled
image bijection and W80 tensor transport remain the algebraic basis. This bounded
native diagnostic tests the additional native special-position/occupancy behavior
without merging labels or treating coordinate coincidence as chemical identity.

The installed W82 wheel is exercised under **Phenix 2.2.1-6174**, using only five
synthetic scatterers per case in C2, R3:H and P4. Two separately labelled carbon
scatterers share a special-position orbit with occupancies0.25 and0.35; context
also includes isotropic/anisotropic general-position atoms, a partial occupancy
and a zero-occupancy atom. Each case uses identity/reverse/cyclic ordering.
The target is freshly constructed through native `xray.structure`, recomputing
its site-symmetry table rather than carrying the source table across images.

All **nine complete native diagnostic cases pass**. Native multiplicities,
occupancies, scattering types and isotropic/anisotropic flags remain exactly
bound to their source labels. Direct wk1995 Fcalc at4 Angstrom resolution agrees
within7.62e-13 (360/156/327 reflections for C2/R3:H/P4). Native construction adjusts
mapped coordinates by at most1.43e-14 Angstrom and Cartesian tensors by1.15e-16
square Angstrom. Source state remains unchanged. These are full-precision
in-memory checks, not serialized-coordinate or refinement results.

The controls deliberately break preservation: dropping one coincident label
changes Fcalc by2.09–6.21; omitting anisotropic rotation by1.28–4.24; replacing
occupancies with1 by69.34–140.71. The source special-position multiplicities are
2,3,1 respectively, with native weights retained after changing representatives.
No test silently normalizes occupancies, deduplicates atoms or changes ADP flags.

Exact scripts, predeclared tolerances, results and selected native Python/kernel
hashes remain local under W83 evidence. Execution is
`phenix.python -B probe.py` through Cedar's existing bounded process owner; it is
a complete synthetic calculation, **not a phenix.refine dry-run or refinement**.
No SDK, source runtime, artifact schema or user model changes. W82 full/install
checks remain the runtime baseline; documentation/roadmap checks are sufficient
for this evidence-only update. Installed-default historical replay remains the
separate W81/Cedar issue.

This narrows P03 to preservation of the supplied labelled/scattering inventory.
It does not establish unique molecular identity, correct occupancies, missing
content, behavior near native special-position classification tolerances,
serialization, anomalous/bulk-solvent policies or physical seam closure. P02/P03/
P04 remain partial. Keep source scientific validity and representation equivalence
as separate questions when implementing the computational-model/derived-view
boundary.

W82's485-payload forensic archive is read-back verified, SHA-256
`9576ef749f9eb919fb2c1a95626f61e7e2c5966058ffba1ed6c1161d2b2f41dc`.
Owned duplicate source/test build trees were removed after verification; the
installed validation runtime remains available. This is forensic evidence,
not an autonomous portable campaign; no scientific payload is committed.


## W84 — Verify the repaired installed composition

Cedar C325 supplies the canonical historical-reader frame as a dedicated package
resource. A fresh virtual combination pins Willow
`29723067dff6e3ad12bac5dd15e8a51e46105091` and Cedar
`cad829a60a6ecc97643e220d4f5d16496bca39e6`. There are zero source conflicts,
seven documentation conflicts and one `pyproject.toml` package-data conflict.
The temporary tree retains both `data/topostitch-view.html` and
`data/replay/*.pdb`, plus Willow's extras and six entry points. Its resolved tree
is `b61a58636501a86b6aef4d969d5baf9f74eb9ce5`; neither branch was merged.

The installed wheel SHA256 is
`7a53ab01571d4be77253c74b0a376e5b0d319b57050271afa2685f9170968e82`.
After moving the build source away, **873 tests and 16 subtests pass** in72.44s:
28 explicitly selected TopoStitch modules and seven shared/Cedar modules. The
exact pytest command, environment, module list and raw output are retained in
`check.py`, `receipt.json`, `audit-scope.json` and `tests.log` in the local W84
archive. The receipt's original phrase "All topology tests" is too broad; the
addendum corrects its scope without modifying executed evidence. Six CLI helps,
both packaged resources, old/new graph/native-link/packing replay and W82's two
855-atom complete saved frames also pass with original paths blocked.

This verifies the C325 default historical-reader repair in the later installed
combination. It does not turn W81's original four failures into a full green
result. No full-suite rerun, native execution, coordinate writer, new runtime or
schema is included. Future integration must retain the package-data union and
reconcile the seven documentation conflicts. Physical stitching, seam chemistry
and ordinary recut refinement remain unqualified.

### Retained W81–W83 evidence

Git-ignored local forensic archives retain original failures and positive controls;
all payload sizes and SHA256 values were read back and verified. These are
forensic records, not autonomous relocated campaign runs. Archive references are
relative to the local evidence root recorded with the session, not input-discovery
rules; no scientific payload is committed or uploaded.

| Archive | Files | SHA256 |
| --- | ---: | --- |
| W81-evidence.tar.gz | 3892 | `187ff8fe7197dce6f108521d1ef5e171989d825efb9040d03147992d98f510ae` |
| W82-evidence.tar.gz | 485 | `9576ef749f9eb919fb2c1a95626f61e7e2c5966058ffba1ed6c1161d2b2f41dc` |
| W83-evidence.tar.gz | 8 | `3975d1767daa20861e5184ac202ad7ddbe6aa3f53faef27de754c78975b5006b` |


## W85 — Check coarse-motion derivatives against native geometry

This local diagnostic joins two existing owners: the six-parameter tapered
whole-residue motion in `topostitch_preview` and the authenticated native/pair/
tether objective in `topostitch_native_recipe`. It adds no product runtime or
second chemistry engine. The analytical chain rule converts Cartesian forces
into derivatives with respect to rotation-vector and translation parameters.
The local probe uses scales of 1 degree and 0.1 Angstrom per dimensionless variable,
with stable small-angle rotation derivatives. Whole paired residues share weights;
fixed atoms remain exact. The pivot is freshly measured from the declared terminal
pair in the diagnostic model; an old preview is not rebound to new coordinates.

The exact W38/W41 model SHA256 is
`dbdaac83c67a60c0d3df48ac19f1dbd2ddd2e15307dcb41cce564d560ab23465`.
Its complete 14-pair recipe, 204-atom mask and prior window/registration are pinned.
The recipe's canonical digest is distinct from its raw-file SHA256; an initial
preparation assertion confused these, stopped before native execution, and is
retained with the correction and original byte comparison. Later Pine-view 8D93
bytes are a different model and were not substituted. Runtime comes from W84's
installed virtual tree `b61a58636501a86b6aef4d969d5baf9f74eb9ce5`.

Validation is a **complete native diagnostic, not a dry run or refinement**, using
**Phenix 2.2.1-6174** through Cedar's owned process runner with a 600-second ceiling.
The parent returned 0, all frozen inputs remained unchanged and the native window
was released. Local evidence contains exact commands and paths in the scripts,
plan/source hashes, capture, worker, execution receipt and logs. Commands use
`PYTHONDONTWRITEBYTECODE=1`; host preparation/review use the W84 installed package
and existing dependency environment, while native execution uses its Phenix
interpreter and the pinned pure-Python package.

- `math-check.py`: 60 independent finite-difference controls across zero, tiny,
  mixed and large rotations, five taper weights and three points. Maximum error
  `5.88e-11` versus the predeclared `1e-7`; fixed-point and equal-weight internal
  distance checks pass.
- `prepare.py`, then `run-owned.py`: fresh maintained Cedar reconstruction exactly
  matches the authenticated original observed context. Five controls (zero,
  positive/negative tilt, translation and mixed), six variables and step sizes
  `1e-3`/`1e-4` are evaluated both cached and with `reset_internals()` before each
  evaluation. All 270 native objective evaluations complete; maximum derivative
  discrepancy `9.98e-7` is below the predeclared absolute `1e-3` per variable.
  Maximum physical displacement is 0.064 Angstrom; zero-control arithmetic has
  approximately 1.3e-15 Angstrom roundoff.
- `review.py`: Cedar replays every saved directed capture and the existing packing
  comparator matches exact relative operations and multiplicity. Forced rebuilds
  yield 8314–8316 directed rows. Changed buffered rows have zero repulsion residual;
  common multiplicities are unchanged, and cached/rebuilt total energy and all
  Cartesian gradients agree exactly at these controls.

Correct derivatives are not a successful stitch. The positive-tilt control lowers
nonbonded residual from 1077.72 to 1071.19, while worsening 48 existing directed
overlaps and making one previously nonoverlapping row overlap. Its total composed
objective also includes other geometry, pairing and tether terms. No control is
selected or emitted as a candidate. Large physical displacements, flexible taper,
window expansion, a supported optimizer and density/refinement benefit remain
untested. The complete live nonbonded/exclusion policy guard remains Cedar-owned;
this observation does not independently enumerate neighbors or prove all exclusions.
W51/W54 failure classifications and S04/S05 partial status are unchanged.

The next reusable component should be a small explicit coarse-motion adapter over
these existing owners, followed by matched bounded placement/cleanup experiments
under the shared native policy. The current Cartesian optimizer assumes 3N variables
and cannot be reused unchanged for six variables. No full suite is repeated for
this local diagnostic/documentation slice; W82's full runtime and W84's focused
installed-composition results retain their stated scope. No scientific files are
committed or uploaded.

W84's verified local forensic archive contains 2295 files, SHA256
`5a65007c6b7afe76cd8e3489e9bc467140b43c30e280268d403fda9744c1cf97`.


## W86 — Expose bounded tapered motion through the existing native objective

Previously, the preview/fitter could propose a six-parameter tapered motion,
while the native objective accepted only independent Cartesian displacements.
`topostitch_transport.TaperedMotion(mask, origin, weights)` now maps explicit
rotation-vector degrees and translation Angstrom into the existing bounded mask,
and pulls a complete Cartesian gradient back through the analytical rotation
Jacobian. Preview/fitting use the identical rotation kernel moved into that
numerical module; their imports and output behavior are preserved.

Weights cover the complete source order; positive weights must match exactly the
movable mask. Inputs are detached, fixed coordinates are exact, zero motion is
exact, and gradient queries cannot bypass displacement bounds. The caller assigns
shared residue/pair weights and the pivot; the component does not infer topology
or an appropriate curvature profile. `NativeMaskedObjective.evaluate_motion`
requires the exact native mask/reference/order/bound, calls the unchanged energy
owner once, retains Cartesian gradients/components, and returns six derivatives
in the declared physical units. Existing 3N optimizer calls remain unchanged.
No model/ADP writer, native callback, force-field change, packet schema migration,
CLI change, optimizer or scientific acceptance is introduced.

Software validation uses the standard source command
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<existing dependencies> <project Python> -m pytest -q -p no:cacheprovider`.
The local W86 logs/installation receipt preserve exact expanded commands:
21 new controls fail before the patch; focused 156 pass; full 1,802 tests and 229
subtests pass; a fresh relocated installation passes 712 selected tests, six CLI
helps, lean imports, Python 3.10 parsing and exact saved-preview/frame replay.
The first full run retained five process-lifecycle failures caused by sandbox
refusal of `/bin/ps`; a complete rerun with process-list access passes, without
changing tests or cleanup behavior. Wheel SHA256:
`6774cb3046d7b62ff2638a6764b21f60941b14323132103d875d225d356aa44b`.
Complete **Phenix 2.2.1-6174** replay through the installed API passes all five
W85 controls: 270 objective calls, both finite-difference steps, and forced
neighbor resets/rebuilds. Maximum scaled derivative discrepancy remains 9.98e-7;
cached/rebuilt energies and Cartesian gradients agree exactly. Cedar replay
confirms changed buffered rows contribute zero residual. Prior W85 targets and
scaled gradients reproduce within 9.1e-13 and 5.8e-13; exact zero motion removes
its earlier tiny pivot-arithmetic roundoff.

Native construction and review use the explicit pinned C325 owners from W84's
virtual installation. The copied host reviewer initially assumed a combined
package and could not import a Cedar-only module from Willow; a separate
`review-pinned.py` uses those same explicit owners. The original failed import
and script remain, with no native rerun or runtime correction. The native parent
returned 0 and frozen inputs were unchanged at completion. This is a complete
native diagnostic, not refinement or a full combined-suite audit. S04/S05 remain
partial; Cedar owns the full live source-policy guard.

W85's verified local forensic archive contains 58 files, SHA256
`59b91b792ae52bb8586b1d33ea64e4a5f08b6d3011ceefda89f4daa7c8bfc80a`.


## W87 — Compare matched six-variable placements without promoting failures

The installed W86 motion API now has a complete matched native diagnostic,
using **Phenix 2.2.1-6174**, the same W38 model/mask and authenticated W39
reconstruction, and the exact W45 retained-core recipe. The paired control keeps
all 14 pairs; the control keeps the identical 12 core pairs. Both use the same
204 movable atoms, six motion variables, fixed residue-pair taper and pivot,
0.5 Angstrom displacement bound and 0.1 Angstrom tether sigma. Dimensionless
optimizer variables correspond to one degree or 0.1 Angstrom. The predeclared
limits are 100 iterations, 500 optimizer calls and 900 seconds per process;
rounding errors are not ignored. This is a complete native execution, **not a
refinement or an experimental-data comparison**.

Both trials **FAILED** with the native LBFGS line-search rounding error. The
paired trial accepted 11 steps (33 attempted evaluations); core-only accepted
10 (32). Their callback-confirmed last accepted points replay exactly and pass
the existing full-precision and PDB-rounded 612-component Cartesian derivative
audits. Total objective calls, including audits, were 7,409 and 7,408. Neither
trial emitted a successful endpoint or candidate PDB. Small six-variable gradient
norms (2.31e-5 / 6.22e-5) do not establish atomic relaxation: their Cartesian
projected norms remain about 6,660. The error cause is not established by its
message; no tolerance change or restart was used to manufacture convergence.

The existing endpoint observer independently compared both saved diagnostic
points under the **same full 14-pair recipe**, with full-precision and rounded
packing, pair attribution, backbone, torsion and plane observations:

| Full-precision observation | Paired | Core-only |
| --- | ---: | ---: |
| Maximum atom motion (Angstrom) | 0.053775 | 0.044405 |
| Selected-pair target change | -7.121786 | -5.317748 |
| Retained-core pair target change | roundoff only | roundoff only |
| Native nonbonded target, from 1077.721614 | 1055.746200 | 1059.585469 |
| Largest increase in an existing directed overlap (Angstrom) | 0.036717 | 0.028682 |
| Largest newly positive existing overlap (Angstrom) | 0.011284 | 0.009778 |
| Native dihedral target change | +0.222094 | +0.181314 |

The retained-pair invariance is expected: each complete pair moves rigidly with
one weight. Thus those terms cannot supply new internal pair relaxation in this
parameterization. Both intended pair totals improve, but some individual AT
bond/parallelity/planarity components worsen. Packing counts (74/77 worsening
directed overlaps and two newly positive existing rows) are descriptive;
reciprocal/directed rows are not independent physical clashes, and a positive
change is not a calibrated rejection threshold. The worst increased overlap is
0.110135→0.146852 / 0.138817 Angstrom. Native plane targets remain invariant to
roundoff. Rounded observations remain separately retained. A better aggregate
score is not chemical acceptance or evidence that the physical gap is closed.

The initial host-side motion reconstruction asserted exact coordinates and
stopped before native observation: host versus Phenix Python arithmetic differed
by at most 7.11e-15 Angstrom. A separate replay in the original Phenix interpreter
reproduced both motion/displacement records exactly; the host then consumed those
hash-bound saved displacements through the unchanged mask. The original script,
failure note and corrected observer are retained. An initial replay invocation
also lacked the installed NASolve import path; explicit installed-path binding
resolved that before execution. No numerical tolerance or native trial changed.

Local evidence is under the declared W87 stage, with per-control `execution.json`
freezing actual worker inputs; generators/preflight hashes preceded a final
worker preparation edit and are not a substitute for those execution receipts.
Expanded commands are retained in the local audit. The operations were:

```text
<host-python with W86 installed package> <control>/run-owned.py
<Phenix 2.2.1-6174 python> verify-motion-native.py <control>
<host-python with W86 installed package> observe-recorded.py <control>
python3 summarize.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_topostitch_roadmap.py --check
```

The two endpoint observers completed with `ENDPOINT_OBSERVATIONS_REVIEW`; they
neither rerun derivative qualification nor reinterpret a rounded model as a fresh
refinement. The original trial derivative receipts provide that separate audit.
W87 changes documentation/evidence only, with no runtime, schema or migration
change and no repeated full suite. W86's 1,802-test full source check and installed
712-test check remain the latest software validation. All scientific payloads,
including failures, remain local and unselected; no automatic adoption, Rfree
claim, full live-policy qualification or supported repair route is introduced.

**Next gate:** bind the reusable motion to verified source/registration/preview
inputs before exposing it to workflow callers. Keep the physical-search question
open: coarse initialization needs a justified stopping/cleanup route, individual
chemistry/packing review, nonuniform curvature and matched diffraction evidence.
The shared complete live-policy guard remains open; Cedar Q06 separately owns
actual refinement chemistry survival. Density enters S06 after exact map/model/data
binding. Do not loosen failed trial policy while wiring the general interface.

W86's verified local forensic archive contains 544 files, SHA256
`392eb4fc602860fbe6a10694ffca5d6144e788dc1eda94bd62ff4eb18ab13e6d`.
These archives are forensic records, not autonomous portable campaign runs.


## W88 — Compile source-bound motions from saved bend previews

Before this change, W86 callers supplied their own weights/pivot/mask provenance.
`load_bend_motion` now reuses the existing complete saved-preview replay and
registration mapping, returning `(motion, parameters)` with exact source atom
order and fixed context. It checks the full-precision bound, exact rounded
coordinate fields, receipt pin and unchanged snapshots. A motion's optional
`source_model_sha256` is checked by the native evaluator before spending a call;
identical coordinates alone cannot authorize reuse on changed model bytes.

Changed runtime owners are `topostitch_preview`, `topostitch_transport` and
`topostitch_native_recipe`; regressions extend their existing preview/mask/trial
tests. There is **no new packet schema or migration**, CLI, optimizer, model writer
or tensor transport. Existing unbound numerical callers remain supported. A
previous rounded preview may be refused if its unrounded motion exceeds the same
bound or exact coordinate serialization differs; the existing preview loader and
writer remain unchanged. Other parameters do not inherit its backbone audit.

Validation: **19 fail-before regressions**, **111 focused tests**, complete source
**1,821 tests +229 subtests**, and **731 installed/relocated tests** pass. Six CLI
helps, lean imports, Python 3.10 syntax and old/new representative-frame replays
pass. The public saved bend preview compiles 855 source atoms /204 movable atoms
after relocation with original paths blocked, retaining its original `91db…`
source rather than the later `dbda…` diagnostic candidate. Commands use
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<declared-dependencies>` and
`<host-python> -m pytest -q -p no:cacheprovider` for source checks; the installed
check instead puts the newly built wheel's isolated site first. Expanded commands,
file hashes and results remain in the local installation receipt.

Exact source validation commands below are historical local invocations, not
portable environment requirements (run from the Willow checkout):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_preview.py tests/test_topostitch_mask.py tests/test_topostitch_trial.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider
python3 /private/tmp/willow-w88-preview-motion/install-check.py
```

Wheel SHA256: `e60931ddbb694732518894d57524cb492665e9134a6b44647ce5e7e253abad4d`.
Cedar C328 `11fd6ee6` has no overlapping runtime files in this slice; this is not
an actual merge or a new combined/native qualification. No external crystallographic
execution was needed for this binding-only patch. S04/S05 remain partial; W87
failures remain unchanged. The shared live-policy guard and Cedar Q06 refinement
chemistry survival are separate open gates. Next investigate the
six-variable stopping resolution without changing the original trial policy,
before deciding how coarse placement should feed local atomic cleanup.

W87's 166-file local forensic archive was verified, SHA256
`8199617fc46c9e22bae915be7cced4802bfab926f2218f0647c48ee7e350fbe3`.
No scientific payload is committed or uploaded; archives are forensic evidence,
not autonomous portable campaign runs.


## W89 — Separate coarse-step resolution from atomic cleanup

Two complete, read-only **Phenix 2.2.1-6174** probes use exactly W87's installed
W86/C325 owners and inputs, rather than silently changing to current branches.
Each callback-confirmed failed point reproduces its target, all Cartesian
coordinates/gradients and coarse gradient norm exactly, including forced neighbor
rebuilds before and after the observations. Each probe uses 240 objective calls;
no optimizer, restart, tolerance edit, model writer or refinement runs.

The predeclared six-variable Hessians use gradient differences at dimensionless
steps 0.01/0.001/0.0001. Symmetrized eigenvalues are positive and stable (paired
about 188–602, core-only 184–597). At 0.001, the local Newton estimates predict
only 8.05e-9 /2.70e-8 Angstrom additional maximum atom motion and decreases
4.70e-13 /3.46e-12: **0.52 /3.80 score ULPs**. Actual sampled scores instead rise
4 /6 ULPs while the six-variable gradients fall to about 4.45e-11 /7.38e-11.
Eleven fixed directions at nine steps retain the raw quantization observations.
This supports a numerical-resolution explanation; a local positive Hessian is
not proof of convergence, global optimality or good atomic geometry. W87 remains
FAILED, and its Cartesian gradient norm remains around 6,660.

The next useful integration is an **explicit diagnostic start for the existing
atomic trial**, with the original source/tether/mask/policy unchanged. A failed
coarse point can be an explicitly identified experimental input, never a successful
coarse endpoint or an implicitly selected model. The atomic stage needs its own
initial/endpoint derivative checks, bounds, stopping status, chemistry/packing
observations and eventual matched diffraction review. Compare it against a cold
start before claiming benefit; do not repair the error label or loosen tolerance.

Exact local execution, separately for `paired` and `core-only`:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/willow-w86-motion/site:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w89-coarse-resolution/<control>/run-owned.py
```

The historical paths above identify this local diagnostic, not portable runtime
references. Per-control execution receipts pin actual inputs and report return0
and unchanged inputs. W89 is evidence-only; no source suite was repeated. W88's
full and installed results remain the current software audit. No scientific data
were committed/uploaded, and S04/S05/Q06 remain open.

W88's verified 495-file local archive has SHA256
`56ac64029a415fe4e177c366bd9bd189e78f27cb19ae0422020ebd8df7fa4e1c`.
Only W86/W88 duplicate build/test trees (588 files, 11,374,761 bytes total) were
removed after exact comparison against verified archives. Installed runtimes,
raw native/failed evidence and immutable runs remain; archives are forensic,
not independently resumable campaign runs.


## W90 — Add explicit diagnostic starts to the existing atomic trial

Previously `run_native_masked_trial` always started at zero displacement. It now
accepts optional `initial_displacements` in the **original objective mask order**.
The vector is detached, checked against the same source/bound, and used for both
the complete initial derivative audit and the optimizer start. No reference model,
tether, restraint, finite-difference step, native stopping epsilon or rounding-error
policy changes. The seed is not an accepted optimizer step; subsequent failures
retain their original errors and only callback-confirmed accepted-point diagnostics.

Explicit starts add an `initialization` observation with
`coordinate_origin=EXPLICIT_DIAGNOSTIC_START`, original-source reference and frozen
displacements. Default calls retain their prior result shape/behavior. This is an
additive backend API/report field, with no CLI, file-format migration, candidate
writer or campaign adoption. Callers authenticate the chosen parent point and
retain its failed/capped status. The existing capture-job CLI is not expanded.

A staged caller can already have spent evaluations, so preflight now checks the
**remaining** budget for the declared optimizer plus all three derivative audits.
An inadequate reused objective is refused before further evaluation; it previously
could enter work and fail only when the hard budget ran out.

Fourteen fail-before controls (13 initialization cases plus the independently
observed remaining-budget failure), **75 focused**, full **1,835 +229 subtests**,
and installed/relocated **745** tests pass. Six CLI helps, lean imports, Python3.10
syntax, saved preview/frame replay and source/install hash equality pass. Changed
runtime/test files are `topostitch_trial.py` and its existing test module. No Cedar
runtime file changes or actual branch merge; native validation is the next W91
matched cold/coarse-seeded diagnostic, not yet claimed here.

Exact historical local validation commands, from the Willow checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_trial.py tests/test_topostitch_captured_job.py tests/test_topostitch_endpoint.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider
python3 /private/tmp/willow-w90-atomic-start/install-check.py
```

Wheel SHA256: `fe84f7ba5bf9e924287423f74defd13d56cf953e7bed1fc726b0ecb6460e7604`.
All scientific payloads remain local. S04/S05, complete native live policy, physical
closure, nonuniform curvature and matched diffraction gates remain open. An atomic
trial's own derivative pass or numerical stop cannot supply scientific acceptance.


## W91 — Compare cold and explicitly coarse-seeded atomic cleanup

Two complete **Phenix 2.2.1-6174** trials exercise the installed W90 API with
explicit pinned C325 native owners. All frozen worker/model/recipe/mask/bootstrap
inputs match; plans differ only in label and starting displacements. Both retain
the original W38 source/tether, full 14-pair recipe, 204 movable atoms, 0.5 Angstrom
bound, 0.1 Angstrom tether sigma, 500 iterations/2,000 optimizer-call limits,
10,000 total evaluations and 1,200-second owned timeout. The seeded start is the
exact W87 paired callback-confirmed point, whose parent remains **FAILED**.
Both source and parent coordinates/gradients replay exactly before either trial.

| Observation | Cold source start | Explicit coarse diagnostic start |
| --- | ---: | ---: |
| Atomic outcome | FAILED: line-search rounding | FAILED: line-search rounding |
| Accepted steps / optimizer calls | 358 /390 | 363 /401 |
| Total calls including audits and two prechecks | 7,742 | 7,753 |
| Maximum motion from original source (Angstrom) | 0.196911 | 0.196911 |
| Total target | 7094.401789628126 | 7094.401789628118 |
| Projected atomic gradient norm | 0.00038015 | 0.00040430 |

Both callback-confirmed points pass full-precision and rounded Cartesian derivative
checks. Independent existing common-recipe endpoint observers complete with
`ENDPOINT_OBSERVATIONS_REVIEW`; no candidate/model, checkpoint or refinement is
created. The parent processes return0 for a completed diagnostic; each nested
atomic trial remains FAILED. This does not establish numerical convergence.

Maximum inter-control coordinate difference is **2.65e-7 Angstrom**, RMS1.38e-8;
all855 PDB-rounded coordinate triplets are identical. Native/pair/tether components
differ slightly while the total is within8 ULPs. This particular small coarse
polish provides no demonstrated endpoint or iteration-count benefit over cold
atomic cleanup. Keep the reusable explicit-start interface for genuinely displaced
placements, but do not add redundant coarse polishing to the default pipeline or
generalize this one-window result to large bending/unbending problems.

The common observations are practically equal: movable-region nominal>=3
bond deviations9→0, angles14→0, boundary angles1→0, and no observed chirality sign
conflicts. Fixed-only deviations remain unchanged; this is not whole-model repair.
Selected and retained-core pair targets decrease52.145 and77.019. Overall native
nonbonded target improves1077.722→1002.146, but110 directed existing overlaps
worsen and18 previously nonpositive rows become positive. The largest increase
is0.139359 Angstrom (0.082822→0.222182); largest new positive overlap0.075566.
These are descriptive severities, not calibrated rejection/acceptance thresholds
or counts of independent physical clashes. Dihedral target rises1.391813 and
planarity drops0.980100. Individual geometry/packing remains a review gate.

Exact historical local commands, separately for `cold` and `coarse-seeded`:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/willow-w90-atomic-start/site:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w91-atomic-handoff/<control>/run-owned.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/willow-w90-atomic-start/site:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w91-atomic-handoff/observe.py <control>
python3 /private/tmp/willow-w91-atomic-handoff/summarize.py
```

Per-control receipts preserve frozen hashes and unchanged inputs. W91 adds no
runtime/schema changes and repeats no source suite; W90 full1,835+229 and installed
745 remain current. All raw scientific and failed evidence remains local; no
ordinary chemistry, physical gap closure, data/Rfree or full combined-current
branch claim is made.

**Shared dependency correction:** Cedar Q06 concerns actual refinement's effective
restraints and achieved chemistry. It is not a synonym for the missing complete
live nonbonded/exclusion-policy mutation guard identified in W78. Existing Cedar
capture/ASU/cache readers observe generated contacts and fixed-state arithmetic;
they do not authenticate every parameter-table entry/assignment/exclusion capable
of generating later contacts. PDU's achieved-angle review does not block unrelated
TopoStitch numerical work. Rowan owns the proposed additive native-policy helper;
Willow will consume a concrete qualified interface rather than duplicate it.
Legitimate neighbor rebuilds must remain distinct from hidden policy changes.

Verified local forensic archives: W89 (48files), SHA256
`cf6dea676c5d03cd9861588c756dfb1c7220ffd14aa864874c414e315131370a`;
W90 (497files), SHA256
`32e4438f2247175364ed97082906fff1495f5cce040c06836bede7117556a4df`.
W90's297 duplicate build/test files (5,903,264bytes) were removed only after exact
archive comparison; active installed runtimes/scientific evidence remain. These
archives are forensic records, not autonomous resumable campaigns.


## W92 — Shared live nonbonded-policy contract (qualification pending)

Rowan confirmed that existing Cedar interpretation/context, directed-ASU capture,
nonbonded readers, cache-transition proofs and static bonded signatures do **not**
implement a complete live nonbonded-policy mutation guard. Extend those owners;
do not create a second executor or treat generated-neighbor equality as proof of
unchanged inputs. This is distinct from Q06 achieved refinement chemistry.

The proposed Cedar owner is `cif_live_nonbonded_policy`, with
`snapshot_live_nonbonded_policy(geo, *, flags, normalization, ...)` and
`require_live_nonbonded_policy(geo, expected, **same_evaluation_options)`.
The machine-readable proposed contract is in roadmap evidence
`E_LIVE_NONBONDED_CONTRACT`; it is **not an installed API or qualification claim**.
Snapshotting requires an already-resolved numeric cutoff and must not warm up,
mutate, pickle or deepcopy the manager. Coverage must include all four parameter
maps/five scalars, ordered assignments, complete exclusion/shell symmetry inputs,
crystal/site symmetry, supported function parameters and fixed search controls.
Unused entries matter even when current contacts/energy remain unchanged.

The intended Willow consumer takes an explicit trusted owner plus a frozen
expected primitive snapshot, records its digest/source provenance, and checks
before and after energy evaluation. It must pass the **same actual flags** used
by `evaluate_fixed_native`, `normalization=False`, and no function/external/
extension overrides. Existing static definitions, atom identity/order and fixed
source-coordinate checks remain; no energy owner or callback is replaced.
Defaults and unguarded report shapes remain unchanged until explicit adoption.

Actual current calls are `geo.pair_proxies(sites_cart=points)` inside the static
signature and `geo.energies_sites(..., flags=active_flags, compute_gradients=True,
normalization=False)` inside the pinned correction owner (`plane_order_safe=True`).
Ordinary movement uses native neighbor rebuilding; forced diagnostic controls use
`geo.reset_internals()`. Adjusted cutoff, effective buffer, update count and the
automatic-cutoff marker are observed cache/derived state, not independently frozen
chemistry: reset legitimately changes them. Generated pair/mapping/force checks
remain with the existing ASU owner and are not replaced by a policy hash.

Required negatives include an unused table entry or inactive exclusion changing
while energy stays equal, W78 serialization loss, changed call flags/function/
normalization, and mid-evaluation mutation. Positives include motion and forced
rebuilds with fixed policy, plus unchanged legacy callers. Parent/source
provenance and actual native-version coverage stay explicit. A fresh snapshot
cannot retroactively authenticate fields absent from an old capture.

No Willow runtime guard is implemented in this update. Owner implementation and
native qualification are pending; a partial inventory must not be labelled
complete. This is planning/documentation only, with JSON/roadmap synchronization
and whitespace checks; W90 source/install validation remains current. The current
handoff is condensed to latest behavior/results, while prior failures and exact
validation commands remain in the detailed ledger. No scientific payload is
committed or uploaded.

W91's142-file local forensic archive is verified, SHA256
`57138c778486e0bacf90519dbb0a333cb246c1e6fa9c3fb563aac53ca4329635`.
It preserves both atomic failures and common-recipe observations; it is not an
autonomous resumable campaign or evidence of scientific adoption.

W92 closes as a **recorded contract-only update**. W93 starts with qualification of
the Cedar owner; the proposed API/schema/policy identifier must not be consumed as
stable before then. Rowan's native inventory is complete, but that is not an
implemented guard. Prospective failing tests are evidence until implemented; they
must not leave the maintained suite failing on an absent module. No further Willow
runtime change was made at shutdown. S04/S05 remain PARTIAL, and W90's full and
installed validation remain the latest software checks. All Linden native trial
and observer processes have completed. Next-session work should use the explicit
roadmap gate rather than rerun W91 or resume nonexistent background work.

Pinned owner preparation: [Cedar C330 contract](https://github.com/vecchioni-lab/NASolve/blob/3bd46f6e96ef7a923936bb74b8a8f0366a17aaba/docs/architecture.md#live-nonbonded-policy-boundary-c330-planned),
commit `3bd46f6e96ef7a923936bb74b8a8f0366a17aaba`. The same commit's
`docs/cif-linked-native-registration-evidence.json` key
`live_nonbonded_policy_contract_2026_11_15` records exact inspected source hashes,
commands, synthetic API observations and pending qualification controls. Rowan
reports 122 adjacent existing tests passed in 7.71 s, no full-suite rerun and no
runtime/test/config change. All C330 native jobs stopped. These observations
support the planned interface; they do not qualify an implemented guard or change
Willow's runtime pins. No merge, scientific payload or local workspace state is
included. W92 validation: `PYTHONDONTWRITEBYTECODE=1 python3
scripts/audit_topostitch_roadmap.py --write`, the corresponding `--check`, and
`git diff --check` pass. No runtime/artifact-schema migration is required.

## W95 — Prepare the qualified guard consumer

This is an implementation plan, not a qualified consumer. W94 runtime remains
unchanged. Rowan is implementing/testing C331 on Cedar; its uncommitted source
and native profile are review inputs only. Wait for an exact qualified commit,
interface, packaged profile and native receipt before using them as an owner.
The machine contract remains `E_LIVE_NONBONDED_CONTRACT` in the roadmap.

The concrete existing boundary is `NativeMaskedObjective` in
`topostitch_native_recipe.py`. Its `_check_native` calls Cedar's
`cif_gradient_audit.fixed_signature`, which invokes `pair_proxies` and may rebuild
neighbors. Consequently a check only after `_check_native` is too late to detect
pre-existing policy drift before native work. The proposed optional integration:

1. Require the trusted qualified owner and expected snapshot together; neither
   means the legacy path. Supplying one without the other, an unsupported native
   profile, or malformed baseline must fail explicitly, never fall back.
2. Freeze the expected primitive snapshot without native copy/pickle. Check it
   before construction's static checks and again afterward. Caller changes to
   the original snapshot cannot update the bound expectation. Baseline creation
   belongs to the authenticated fresh context, after deliberate cutoff resolution;
   the consumer must not warm up an unresolved manager to obtain a snapshot.
3. For each evaluation, construct one ordinary `active_flags` object and pass that
   same object to both guard and corrected native evaluator. Supply the actual
   options explicitly: `compute_gradients=True`, `normalization=False`,
   `disable_asu_cache=False`, no supplied gradient buffer or custom/external/
   extension energy. `plane_order_safe=True` remains the correction owner's
   separate contract. Guard before the first native/static check and after all
   evaluation/static checks, before returning a target or gradient.
4. Preserve original failures and budget accounting. A guard failure produces no
   accepted result and never refreshes the expected baseline. A native exception
   stays a failure even when post-error inspection is unavailable; any additional
   policy diagnosis must not mask the original error. This is sequential mutation
   detection, not a concurrency lock or proof against transient mutate-and-restore.
5. Add guard provenance only to explicitly guarded binding reports: expected
   policy digest, owner/profile identity and trusted source/profile hashes. Keep
   default result shape, fixed-source/atom-order checks, source masks, plane
   correction and interpretation ownership intact. Policy equality alone does
   not authenticate historical captures, generated contacts or physical packing.

Acceptance uses existing native-seam/trial tests and one bounded native comparison:

| Check | Required result |
| --- | --- |
| Existing unguarded construction/evaluation | Same behavior and report shape; optional owner never imported implicitly |
| Missing owner/baseline, malformed or caller-mutated baseline | Refused or detached as appropriate; no silent downgrade |
| Hidden unused table, assignment or exclusion drift before a call | Rejected before any static/native helper is invoked |
| Identical returned energy with policy mutation during evaluation | Rejected before a result escapes |
| Flags/options changed on the actual evaluation object | Detected, including gradients and normalization |
| Coordinate motion and forced neighbor reset/rebuild | Fixed policy passes; ASU owner separately checks generated contacts |
| Guarded versus unguarded supported native controls | Same targets/gradients under identical policy and inputs |
| Frozen-source, identity, budget, native failure and trial reporting | Existing refusal/failure behavior remains |

After focused fail-before tests, run the full suite for this shared evaluation
boundary and verify a fresh wheel with the qualified Cedar owner/profile. Use
Phenix 2.2.1-6174 only within the owner's exact supported platform/API profile;
record complete execution versus dry-run, dependencies and source hashes. No
cross-platform support claim follows from ordinary Python tests.

Start with direct optional objective integration. The existing captured worker
stages Willow modules plus renamed correction/audit files; adding only a guard
`.py` would omit its `data/nonbonded-native-profile.json`. Later worker adoption
must stage and hash the full owner/resource dependency closure through existing
runtime provenance, verify installed and relocated execution, and retain old
readers. Do not expand the worker, CLI or campaign defaults in the first slice.

After that gate, predeclare a genuinely displaced intact-duplex case and matched
cleanup control, with contact, collateral geometry/packing, derivatives and
failure outcomes. W91's small-polish experiment is complete and offers no reason
to repeat it. Density-aware S06 and independently bent post-first-refinement
orientation siblings stay in sequence; do not tune a geometry-only winner to
one dataset or rank repeated trials on Rfree. Campaign desk remains the human
review direction: show the proposed motion, completed change, retained failure
and comparison evidence, with acceptance separate from computation.

W95 validation (documentation only): `PYTHONDONTWRITEBYTECODE=1 python3
scripts/audit_topostitch_roadmap.py --write` and `--check`, plus
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
/private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
tests/test_topostitch_roadmap.py` (**8 passed**) and `git diff --check`.
No new full suite, installation or external-tool execution was required; W94
remains the runtime validation receipt. No generated scientific artifacts included.

## W96 — Optional direct live-policy consumer

`NativeMaskedObjective` now accepts keyword-only `live_policy_owner` and
`expected_live_policy`. Supply both or neither. The trusted owner validates the
expected primitive snapshot and actual manager before the baseline is frozen as
JSON. A missing/incomplete owner/profile or policy mismatch raises; there is no
fallback or replacement snapshot. The original caller dictionary cannot change
the stored expectation. The owner still owns bounds, supported native types and
policy comparison; Willow does not duplicate those mechanics.

Construction checks bracket the existing static-signature check. Evaluation
checks precede all native/static work, follow the corrected native energy, and
follow the final static check before a result can return. All checks and the
corrected evaluator share the actual flags object; explicit options match
`compute_gradients=True`, `normalization=False`, `disable_asu_cache=False`, with
no supplied gradient buffer or function/external/extension overrides. The existing
plane correction is unchanged. Native errors propagate without a later guard
masking them; failed attempts retain existing budget accounting. Sequential
checks cannot detect a concurrent transient mutation that is restored in between.

Opt-in binding reports gain `live_nonbonded_policy` containing `policy_id`,
`native_profile_id`, `policy_sha256`, `owner_source_sha256` and
`native_profile_sha256`. These hashes are provenance, not authority to adopt a
model. Existing callers keep their old binding and evaluation shapes. There is
no new CLI, worker bootstrap, campaign default or dependency; the guard owner is
not imported implicitly. Existing objective restrictions, including rejection of
special-position constraints, remain even though the guard can read them. The caller remains responsible for trusted source
lifetime and interpretation. Historical captures do not gain missing policy
provenance, and the guard does not authenticate generated contacts or chemistry.

The qualified owner is Cedar **C331** commit
`c4e5ddb8530358c524feb473f3c4ffe77c64b6ac`,
`cif_live_nonbonded_policy.py` plus `data/nonbonded-native-profile.json`.
Supported profile: `phenix-2.2.1-6174-darwin-arm64-nonbonded-v1`.
Owner SHA256 `0a812020882d5452554a4f6629c5af1aa56e01f6060c26fce585e9174bcfaf3e`;
profile SHA256 `d35a0b61dd49a75132d16d3bb53b1c636eefbd30c21d19fe5d50a03d018e6ee6`.
No Cedar files were copied into Willow's tracked source and no branch was merged.

Nine new regressions exercise the previously absent API (three failures and six
missing-helper fixture errors before implementation). **84 focused**, **1,853 full
+229 subtests**, **84 fresh-wheel** tests, six installed CLI helps and `pip check`
pass. The full suite covers shared evaluation behavior. Source and installed
runtime bytes match; Python 3.10 syntax parsing passes. Exact local commands:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_trial.py tests/test_topostitch_captured_job.py tests/test_topostitch_endpoint.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w96-guard/install-check.py
PYTHONDONTWRITEBYTECODE=1 /Users/svecchio/Applications/phenix-2.2.1-6174/bin/phenix.python /private/tmp/willow-w96-guard/native-check.py /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/src
PYTHONDONTWRITEBYTECODE=1 /Users/svecchio/Applications/phenix-2.2.1-6174/bin/phenix.python /private/tmp/willow-w96-guard/native-check.py /private/tmp/willow-w96-guard/native-installed/site-packages /private/tmp/willow-w96-guard/native-installed/site-packages/nasolve
```

Both native runs were **complete executions**, not dry-runs, under Phenix
**2.2.1-6174 / Python 3.11.15**. Eight bounded checks pass: real constructor/opt-in
provenance; exact guarded/unguarded source, local-motion and forced-reset/moved
targets/gradients; all six movable-variable finite differences; caller snapshot
detachment; an unused-radius mutation refused before any static/energy helper;
and a mid-evaluation mutation refused before returning. The synthetic three-atom
manager uses a zero additive-pair control. This qualifies the guard/native seam,
not a canonical DNA recipe, physical gap closure, diffraction or refinement.

Installation builds an sdist, deletes its staging source, builds a wheel after
relocation and tests a fresh environment without source PYTHONPATH. A separate
temporary native installation combines that pure-Python wheel with exactly four
C331 wheel members: guard, profile, existing correction and static auditor. Their
bytes match the pinned sources. This is a bounded installed composition, not a
full merged-Cedar regression. The first native install attempt accidentally put
the ordinary Python 3.12 environment ahead of Phenix's Python 3.11 NumPy and failed
ABI import. The corrected `--no-deps` wheel target retains Phenix's own compiled
dependencies and passes; the failed harness log is retained. No product fallback
or SDK patch was used. Willow wheel SHA256:
`853d8bfbb8a476a65e5f6d673de8dce8a4f81a5112b9a01b70ff6f87c4118d79`.

Raw scripts/receipts/logs remain ignored local evidence; no scientific payload,
SDK or generated model is committed. Next: qualify explicit captured-worker
staging of the complete owner/profile dependency set and report provenance before
any supported job option is added. Keep the direct interface opt-in. Large-motion
DNA, independent packing/contact checks, density-aware matched refinement and
Pine/campaign acceptance remain separate open milestones.

W96's 19-file local forensic archive is verified under the everyday NASolve
checkout at ignored `branch-artifacts/willow/w96-live-policy-2026-11-16.tar.gz`,
SHA256 `751a1a34a74410d826c68fee0ef222c85d45dabb7edf89c8abdfde0e0b88451d`.
It retains scripts, pinned owner/profile files, checksummed receipts and the
failed harness log; it is not a portable/resumable campaign. Roadmap validation:
`PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_topostitch_roadmap.py --write`
and `--check`; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q
-p no:cacheprovider tests/test_topostitch_roadmap.py` gives **8 passed**; whitespace
checks pass. These documentation checks do not replace the native receipt above.

## W97 — Explicit guarded captured diagnostics

`run_captured_objective(..., guard_live_policy=True)` carries W96's explicit guard
into the existing captured worker. The new Python argument is strictly boolean
and defaults to `False`. No new CLI or campaign default is added. The default
worker text and its request/report shape are unchanged; a legacy installation
does not need to import the optional owner. Opt-in requires Cedar C331's qualified
`cif_live_nonbonded_policy.py` and `data/nonbonded-native-profile.json` in the
selected installed/developer package. Missing assets or a different qualified
layout fail before allocating a job; there is no fallback to unguarded work.

The same existing runtime staging/provenance mechanism retains the complete
two-file guard closure. `request.json.live_policy_guard` binds owner/profile
hashes and IDs plus source-model and original-capture digests. The guarded worker
verifies staged bytes, reconstructs the native context using maintained Cedar
code, compares it with the authenticated capture, and only then snapshots the
new live policy before the static signature can generate pairs. The configured
cutoff must already be resolved; this adapter does not warm up a manager to make
snapshotting succeed. All W96 invocation options and baseline rules apply.

`live-policy.json` is a new schema-1 observation with kind
`topostitch-live-policy-baseline`, origin `FRESH_RECONSTRUCTED_CONTEXT`, source
model/capture SHA256 values and the Cedar snapshot. It records a fresh baseline;
it does **not** reconstruct policy fields missing from a historical capture.
The controller cross-checks identity, policy digest and exact objective-binding
provenance even when the child returns zero. The receipt gains an opt-in
`live_policy_guard` object, `baseline_verified`, and a checksummed
`probe_directory` reference to the baseline. Source/staged-file drift invalidates
the job and clears baseline verification. A retained baseline file or verified
binding alone does not imply the whole job, geometry or chemistry passed.
Original failures and uncertain-process-ownership behavior remain unchanged.

Ten new cases fail before implementation; the new legacy-with-owner control
already passed. **84 focused**, **1,864 full +229 subtests**, **84 fresh-wheel**
tests, six installed CLI help checks and `pip check` pass. Tests cover lazy owner
loading/cleanup, missing assets before allocation, immutable staged resources,
missing/mismatched success evidence, changed source/profile and legacy behavior.
Full regression is appropriate for the worker orchestration change. Runtime
source/installed bytes match and Python 3.10 syntax parsing passes.

Complete **Phenix 2.2.1-6174** execution uses the explicit, hash-verified W91
archive inputs: **855 atoms, 204 movable atoms, 14 canonical pair recipes**.
One fresh native capture remains REVIEW. Unguarded and guarded read-only workers
both return `INITIAL_CONTEXT_AND_EVALUATIONS_MATCH`, with exactly equal source
and nonuniform evaluation values/gradients (including repeat evaluations).
Their guard baseline is new evidence, not a promotion of W91's failed trials.
No optimizer, coordinate editing or refinement was run.

A fresh installed Willow wheel and the explicitly selected installed C331 wheel
repeat guarded execution after both original input/capture directories are moved
away. Values, gradients and binding match the source run exactly; baseline
references/checksums and retained-source checks pass. Trusted-source entries use
installed packages, not the old source checkout. This qualifies the explicit
installed-Cedar route and the declared relocation on this host; it is not a full
merged-branch test, another native profile, or a universal portable campaign.

Exact local validation commands (historical scratch paths):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_captured_job.py tests/test_topostitch_trial.py tests/test_topostitch_capture.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w97-worker/native.py /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/src
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w97-worker/install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w97-worker/install/env/bin/python /private/tmp/willow-w97-worker/installed-native.py
```

Willow wheel SHA256:
`3025cf64334f134b566615a3373c80680d7941f2734a204c4fdee235a639b048`.
Cedar owner remains `c4e5ddb8530358c524feb473f3c4ffe77c64b6ac`; its source/profile
hashes are unchanged from W96. Native baseline policy digest in this declared
case is `4765d4a0173a162dda89d0673654e8080e4201e9e82848afc45b457918e0da31`.
Changed runtime/test files are the existing captured-job module and its tests;
no Cedar edits, branch merge, dependency change or migration of legacy receipts.
Scientific inputs, generated captures and job outputs remain local and uncommitted.

Next: predeclare a genuinely displaced intact-duplex diagnostic and matched
cleanup control, with explicit mask/bounds and protected junctions. Measure guard
overhead before reserving a longer native evaluation/time budget; do not weaken
the policy checks for speed. Use contact, collateral geometry/packing, derivative
and failure evidence, then the separate density-aware/matched-refinement gate.
W91's small-polish result is settled and need not be rerun. Guarded long optimizer
trajectories, endpoint-observer combinations and scientific bend acceptance are
not established by these read-only worker cases.

The verified 144-file forensic archive is ignored local evidence under the
ordinary NASolve checkout at
`branch-artifacts/willow/w97-guarded-worker-2026-11-16.tar.gz`, SHA256
`e95861400eba30f8bc1fd3defbda47c92a646dfe47739c7049a8507ce96a7216`.
It retains the declared relocated inputs/capture, immutable diagnostic outputs,
source/profile snapshots, validation scripts and receipts with a payload index;
it is not an autonomous resumable campaign. Roadmap validation passes via
`PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_topostitch_roadmap.py --write`
and `--check`; focused `tests/test_topostitch_roadmap.py` gives **8 passed** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider`.
Whitespace checks pass. No scientific payload is committed or pushed.


## W98 — Declared starts through captured native trials

The captured-objective Python API now accepts `initial_displacements=None`.
When supplied, this is an explicit list/tuple of finite numbers in the movement
mask's 3N order, frozen at API entry. Booleans, iterators, empty/partial vectors,
more than 1,200 variables, and nonfinite numbers fail before owner loading.
An explicit start requires a nonzero `trial_iterations` request. Its complete
atom count and each atom's radial displacement must match the authenticated
mask before a job is allocated. Endpoint-observation and optimization requests
remain mutually exclusive.

The controller records the vector as
`request.json.trial.initial_displacements` and forwards it to W90's existing
`run_native_masked_trial`. It does not rewrite the source model, rebase the
reference tether, relax bounds, skip derivatives or replace a failed outcome.
The optional shared policy guard can be used with this path. Legacy requests
omit the new member; worker text, schema version 1 and default behavior remain
unchanged. There is no new CLI flag, dependency, candidate publication or
campaign selection authority. Consumers requesting this optional member need
the updated captured-job API; historical requests need no migration.

Twelve new regressions fail before this change and pass afterward. **96 focused,
1,876 complete-suite tests +229 subtests, and 96 fresh-wheel tests** pass, as do
six installed CLI help checks and `pip check`. The first sandboxed full-suite
attempt passed 1,871 tests but failed five process-ownership tests because macOS
denied `/bin/ps`; the unchanged suite passed outside the sandbox. Both logs are
retained. Installation used a relocated sdist after removing its source staging
path; the installed test process imported NASolve from `site-packages` without
source `PYTHONPATH`.

Exact validation commands (historical scratch paths):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_captured_job.py tests/test_topostitch_trial.py tests/test_topostitch_capture.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/install-check.py
```

Fresh Willow wheel SHA256:
`97594379a1aa6c3a71f390f8017ebed010df59b18dd8a12b59dbda289e35140e`.
The existing captured-job module and tests own the change; no Cedar code or
native optimizer is modified. Runtime source and installed module bytes match,
and Python 3.10 syntax parsing passes. Rowan reviewed the exact `7faff1a1` diff
without a Cedar compatibility blocker; this was code review, not a native or
scientific endorsement. The explicit installed C331 owner remains
`c4e5ddb8530358c524feb473f3c4ffe77c64b6ac`; no branch merge is implied.

### Native controls and preserved budget correction

Complete **Phenix 2.2.1-6174** native geometry execution used the existing
855-atom source and 14-pair recipe. A predeclared +5-degree tapered window selected
204 atoms (612 variables), maximum movement 1.768 Å and RMS 0.917 Å, with a 3 Å
radial bound and the original 0.1 Å reference tether. The instrumented four-call
profile measured 0.640 s per objective evaluation; a separate unprofiled whole
read-only job took 4.456 s. Profiling includes overhead and is not a native
throughput guarantee. The chosen 1,800-second cap did not have a justified margin
for 7,350 finite-difference evaluations plus optimization. The first window run
was interrupted before a complete verdict; the second was not launched.

The sandboxed interruption returned `OWNERSHIP_ERROR` because process cleanup
was denied. Its original FAILED receipt and partial files remain intact. An
independent unsandboxed `killpg(group, 0)` check returned ESRCH, establishing that
the worker group was absent. Subsequent native controls ran outside the sandbox
through the unchanged owned process runner. This is retained budget/environment
evidence, **not** a numerical failure, a policy-drift finding or a qualified
full-window trajectory. Do not silently retry or promote the interrupted run.

The smaller, separately declared control retained the original displacement for
the **complete A103/C114 base pair**: 41 moving atoms/123 variables and 814 fixed
atoms, maximum displacement **1.3825 Å**, RMS **1.1506 Å**. All source coordinates,
weights, pair definitions, tether and hard bounds stayed fixed. Two 25-iteration/
50-call pilots had 1,600-evaluation budgets and passed all derivative audits but
stopped at their iteration limits with large remaining gradients. One equal,
predeclared 300-iteration/500-call extension restarted both cases from the exact
original displaced coordinates with fresh L-BFGS history, 2,200-evaluation budgets
and 900-second owned caps. Its initial audits exactly match the pilots. No sign,
weight, taper or coordinate choice was tuned from the outcomes.

| Iteration cap | Added pair forces | Objective calls | Wall s | RMS from source, Å | Native target | Raw pair target | Full gradient norm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 25 | Pairs on | 1510 | 425.42 | 0.591970 | 7819.1091 | 581.4880 | 3468.139735 |
| 25 | Pairs off | 1510 | 421.65 | 0.588683 | 7793.1830 | 596.1614 | 3642.844013 |
| 300 | Pairs on | 1805 | 514.59 | 0.065399 | 7032.7809 | 560.5891 | 0.091188 |
| 300 | Pairs off | 1795 | 512.31 | 0.064062 | 7029.9549 | 571.1117 | 0.043267 |

All four cases are **ENDPOINT_DERIVATIVES_PASS** and **NOT_CONVERGED_LIMIT**;
the declared native convergence criterion is false. Every initial/full/rounded
123-variable audit at 1e-4 and 1e-5 Å passes the unchanged 1e-3 absolute-error
bound. Guard baselines verify and inputs/trusted sources are preserved. These
unnormalized scores are not R factors, and the total weighted objective is not
used to rank different pair-force policies. The observed complete-job rate is
about 0.28 s/evaluation; plan a larger full-window budget from that observation,
with margin, rather than treating the instrumented estimate as a measured limit.

### Contact, packing and rounding observations

Three additional fresh guarded read-only jobs inspect the displaced initial
point and both extended endpoints, each in source/full/rounded coordinate form.
All return **ENDPOINT_OBSERVATIONS_REVIEW**, with verified guard baselines,
repeated native inventories and existing per-term/packing reviewers. Only core
pair `core-0` changes: its raw pair penalty is **14.9391 → 10.6100** with pair
forces, versus **21.1327** without. The two selected sticky-end pair terms are
unchanged. The improvement with pair forces comes from planarity/parallelity;
its bond and angle contributions still increase by 1.2143 and 0.9152 relative to
the initial rigid pair. A better aggregate pair penalty does not mean every
contact improved.

Native packing residual falls from 3,089.1081 at the displaced point to
1,052.6228 / 1,051.3692 (pairs on/off), compared with 1,077.7216 at the original
source. Relative to source, **5 / 6** existing directed rows become overlapping,
and **41 / 38** have worsened positive overlap; worst increases are **0.0618 /
0.0588 Å**. All 8,316 source/endpoint directed identities match, with no added,
removed or changed-multiplicity rows. These counts are native directed records,
not unique physical contacts or a MolProbity clashscore. Native dihedral residual
increases by about 0.8374 / 0.7096 relative to source; fixed-only terms do not
change. Source and endpoint environment reviews all remain **REVIEW**.

PDB three-decimal rounding changes the full gradient norms from **0.0912 /
0.0433** to **225.31 / 232.95**, while rounded derivative consistency still passes.
Retain numerical stationarity and serialization evidence separately; neither a
small coordinate change nor a passing derivative check establishes physical
acceptance. No PDB candidate, diffraction refinement, Coot check, R statistic,
campaign selection or automatic adoption was produced.

The original-source tether explicitly biases these controls toward the reference.
They qualify the installed API/guard/atomic-trial and endpoint-observer
composition in this local paired-step scope, **not** blind MR repair, full-window
bending, selected sticky-end closure or density-supported recovery. S04/S05 remain
PARTIAL. Next: reserve realistic complete matched full-window budgets, retaining
per-contact/boundary/packing and serialization outcomes, then address general
source-displaced and density/matched-refinement controls. A later owner-side
immutable prepared baseline may reduce repeated expected-tree validation, but
must preserve complete fresh live-policy/source checks; no optimization or
policy-cache shortcut is introduced here. Do not repeat W91's small-polish study.

Exact native/evidence commands (historical scratch paths; all native workers were
complete executions except the explicitly interrupted full-window attempt):

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/profile.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/timing.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/run-trials.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/paired-step/run-trials.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/paired-step/extended/run-trials.py
nice -n 10 env PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/paired-step/extended/observe.py
python3 /private/tmp/willow-w98-starts/summarize.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w98-starts/archive.py
```

The ignored local forensic archive at the ordinary NASolve repository anchor is
`branch-artifacts/willow/w98-declared-starts-2026-11-16.tar.gz`, SHA256
`8b5aaf98b3d394c8245ff426334c4f663d94337e92dc90f8c6e9c89f5307679d`:
**487 files / 40,234,280 bytes**, with every indexed payload
checksum verified. It retains declarations, interrupted and complete jobs,
profile command/output, installed wheels, source capture, comparisons and logs.
Historical paths are provenance only. This is not an autonomous portable campaign
or a bundled native SDK. No scientific inputs or generated outputs are committed
or uploaded; only code, tests and documentation are pushed. All native jobs from
this slice are finished.

### User-requested coordinate inspection exports

On 2026-11-16, the user requested viewable coordinates. The ordinary NASolve
repository anchor now has the ignored local folder
`branch-artifacts/willow/inspection-2026-11-16/`: `00_reference.pdb`,
`01_imposed_window_bend_UNREFINED.pdb`, `02_local_pair_displaced_UNREFINED.pdb`,
`03_local_pair_recovered_with_pairs_REVIEW.pdb`, and
`04_local_pair_recovered_without_pairs_REVIEW.pdb`. These are fresh visual exports
from checksummed W98 evidence; original runs/archives are unchanged. Existing
masked-serialization audits pass, preserving fixed atoms and all non-coordinate
records; Gemmi 0.7.5 reads all five with one model, 855 atoms and the original cell.
Original ADPs are held unchanged for coordinate inspection, not requalified.

`05_cut_preview.html` is generated by the installed read-only viewer from the
checksum-verified, replayed W82 `relocated/new` packet. It shows an earlier,
separately bound source/representative cut, not a refinement-ready recut PDB.
The browser layout was not visually re-reviewed. `README.txt` identifies the
windows/pair and inspection limits; `inspection-receipt.json` binds parent
archives, output checksums and audits. These local files create no candidate
checkpoint, chemical connection, refinement or scientific acceptance. No runtime
code or CLI changed, and no new scientific calculation or full-suite rerun was
needed to materialize/replay the existing observations.

## W99 — Complete full-window native bend controls

The separately declared comparison retains the W98 +5-degree taper, all 204
movable atoms (612 variables), the complete 855-atom source, 14-pair recipe,
3-Angstrom bound and original 0.1-Angstrom reference tether. The interrupted
W98 attempt remains unqualified evidence. Both siblings start afresh with
identical settings apart from the declared added-pair-force switch: 300
iterations, 500 optimizer calls, 8,000 total evaluations and a 3,600-second
owned cap. Initial, full-precision and PDB-rounded derivative checks retain
every variable at both finite-difference steps (7,350 evaluations before
optimization). Plan SHA256:
`fb04b4fcf7905995879a3f3871c8d5aa2b4d992b6d2b9a639e0a76500edab60c`.

**Completed execution, limited scientific result:** installed W98 with pinned
Cedar C331 under **Phenix 2.2.1-6174**, sequential at nice 10. Both initial
coordinates and native/raw-pair/tether components match exactly. All six
initial/full/rounded derivative audits pass the unchanged 0.001 absolute bound;
maximum error is 0.0002662 at 1e-4 Angstrom and 0.000002732 at 1e-5 Angstrom.
Guard baselines, input hashes and all retained payload checks pass. Both stop
**NOT_CONVERGED_LIMIT**, not native convergence.

| Observation | With pair forces | Without added pair forces |
| --- | ---: | ---: |
| Wall time, seconds | 2191.33 | 2184.94 |
| Total objective evaluations | 7661 | 7663 |
| RMS from original source, Angstrom | 0.074182 | 0.058718 |
| Full-precision native target | 6546.3873 | 6531.5154 |
| Common raw pair target | 435.7551 | 575.4410 |
| Full / PDB-rounded gradient norm | 0.0633 / 512.77 | 0.2102 / 522.41 |

The common imposed start was 0.917496 Angstrom RMS from source, with native
and raw-pair targets 10881.6017 and 835.3249. These are objective values, not
physical energies or crystallographic statistics. PDB rounding substantially
changes stationarity even though derivative consistency still passes.

Three fresh guarded observers use the same complete pair recipe for the initial
point and both endpoints. They retain full/rounded native geometry, individual
pair terms, torsions/planes and symmetry-aware packing. Both endpoints remove
the imposed affected simple-bond/angle nominal >=3 screens, with no chirality
sign conflicts; these screens are descriptive, not calibrated acceptance.
The A104 O3'-A105 P link is 1.9361 Angstrom initially and 1.6082 with pairs,
against a 1.607 target. Fixed-boundary links and angles remain included.

Compared with the original source, the pair-enabled endpoint improves both
selected contacts (penalty changes -33.2131 and -18.9310) and the core total
(-77.0189). The no-added-pair control worsens selected-0 and two core pairs.
Aggregate packing residual improves from 1077.72 to 1002.14 / 1000.31, while
110 / 109 existing overlaps worsen and 18 / 16 existing contacts newly overlap.
The largest positive-overlap increases are 0.1394 / 0.1627 Angstrom. Aggregate
native dihedral penalties increase by 1.3913 / 1.0995. These individual trade-offs
and environmental REVIEW survive the favorable aggregate scores. Fixed-only
native torsion/plane terms remain unchanged.

**Limit:** the original-source tether strongly favors return toward that known
reference. This qualifies a complete numerical control and observer path, not
blind MR repair, intended end closure, chemical acceptance, density agreement,
Rwork/Rfree improvement, or S04/S05 completion. No model is adopted.

The everyday NASolve repository anchor contains the local forensic archive
`branch-artifacts/willow/w99-full-window-2026-11-16.tar.gz`:
SHA256 `979172fbdd4c590bdecebf6c840b06da4f4216960a0685ce7ac7c0b713f46c4f`,
255 payloads, 35,543,397 bytes. Every indexed member was read back and checked.
Inputs, exact wheels, raw receipts, full comparisons, scripts and stopping
outcomes are retained. This is not an autonomously portable campaign; Phenix
is not bundled. Four audited inspection PDBs are in
`branch-artifacts/willow/inspection-w99-2026-11-16/` under the same anchor.
Overlay reference, imposed start and either endpoint without independent
alignment. ADPs are held fixed for inspection only; no new bonds/checkpoints.
No GUI visual review is claimed. Scientific artifacts remain local, excluded
from Git.

Historical driver root: `/private/tmp/willow-w99-window/`. Exact controller
commands used the pinned `/private/tmp/willow-w94-pivot/env/bin/python` with
`PYTHONDONTWRITEBYTECODE=1`: `run-trials.py`, then `observe.py` at nice 10,
`summarize.py`, `scalar-endpoints.py`, `scientific-summary.py`, `archive.py` and
`export-inspection.py`. Native processes use the existing owned-command runner.
No runtime/schema/dependency changes, so W98 software/install qualification
remains the applicable code evidence. Documentation validation:
`python3 scripts/audit_topostitch_roadmap.py --write`, then `--check`, JSON
readback and `git diff --check`; no new full-suite or installation claim.

## W100 — Source-displaced controls

The next predeclared panel removes the pristine-reference tether from the
perturbed worker: a reference-source control with pair forces, a displaced-source
control with pair forces, and a matched displaced-source control without them.
Each starts at its own actual input coordinates with the same **1-Angstrom
tether sigma**, 204-atom mask, 3-Angstrom radius and W99 iteration/evaluation/
time caps. The original reference is only a separate control and after-the-fact
comparison; it is not a displaced-worker restraint target. The source already
has geometry REVIEW and is not an ideal chemical truth. All ADPs remain fixed;
no diffraction, inference or physical repair claim.

Before execution, a preparation audit caught a stale original-source checksum
in the displaced movement mask. The first unexecuted declaration is preserved.
A fresh declaration corrects only that binding; model/recipe/PHIL bytes, force
policy, coordinates, cases and budgets are identical. Revised plan SHA256:
`5fc8b01082cbaf6bfa8d6000baf9a22d34f26b614c3b920efee973cdc4f615c6`.
The local preflight explicitly maps Willow's candidate checksum field to the
existing Cedar qualifier's spelling; no owner API or acceptance rule changes.

Fresh native interpretation of the displaced source passes all **22** exact
identity, monomer-definition, complete proxy, installed-API and policy checks.
No link or angle is lost. The existing owned runner executes the three trials
sequentially; launching requires all three worst-case caps plus 600 seconds
before the 23:00 London cutoff. All three complete executions and three common
full-recipe endpoint observers are now audited under **Phenix 2.2.1-6174**.
Initial points and native/raw-pair/tether components match exactly between the
displaced controls. Every initial/full/rounded 612-variable derivative check
passes the unchanged 1e-4/1e-5-Angstrom steps and absolute 1e-3 bound. All trials
remain **NOT_CONVERGED_LIMIT at 300 iterations**; no endpoint is adopted.

| Actual input / pair forces | Native target, final | Raw pair target, final | RMS from actual input / Å | RMS from reference / Å | Objective evaluations |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reference / on | 6307.5844 | 270.0376 | 0.421001 | 0.421001 | 7657 |
| Displaced / on | 6327.2791 | 333.7927 | 0.634082 | 0.698233 | 7655 |
| Displaced / off | 6244.5665 | 1292.3020 | 0.478782 | 0.942609 | 7660 |

The displaced start has native target 10883.1943, raw pair target 835.3084 and
reference RMS 0.917427 Å. Pair forces improve both selected pairs and the four
movable core-pair totals; the eight fixed core pairs stay exact. Without those
forces, one selected pair and all four movable core pairs worsen, despite lower
native geometry energy. These are bounded controls, not a converged optimum or
proof of blind recovery. Total objectives with different input tethers are not
one comparable objective. Even the reference control moves 0.421 Å; geometry
regularization alone does not show that this motion is supported by diffraction.
The paired displaced endpoint's maximum distance from the reference increases
1.7680 → 1.8635 Å while its RMS improves.

All three full and rounded endpoints have zero nominal absolute deviations ≥3
among the **230 affected simple bonds and 356 affected angles**, with no sign
conflict among 39 affected chiralities. The fixed-context source outliers remain.
These native sigma screens are descriptive, not calibrated validation grades.
Packing improves in aggregate but retains 125/145/106 worsened directed overlaps
(reference/paired displaced/unpaired displaced), including 55/81/49 newly
overlapping existing rows. Largest positive-overlap increases are
0.3777/0.4392/0.4354 Å. Native directed multiplicity changes are 0/2/3; no newly
listed overlapping contact is observed. Aggregate torsion and plane targets
improve, while individual torsions and one plane in the paired displaced case
worsen. Boundary torsion penalties also increase. The full gradients remain
107.03/174.05/210.65; PDB rounding raises them to 551.00/596.70/588.17.

The 324-file local archive is verified member by member under the everyday
NASolve anchor: `branch-artifacts/willow/w100-source-controls-2026-11-16.tar.gz`,
SHA256 `e7afd8c9e48cc55958335ce282031d794d7f6e561b0a0f077c6bac4401190444`.
It retains the unexecuted stale-mask preparation, corrected declaration,
checksummed inputs, complete trials/observations, accepted-step samples, drivers,
logs and exact wheels. Historical working root:
`/private/tmp/willow-w99-window/next-source-control-v2/`.
This is a forensic archive, not an autonomous portable campaign.

Five local inspection PDBs and their receipt are under
`branch-artifacts/willow/inspection-w100-2026-11-16/`: original input, displaced
input and all three endpoints. Existing masked endpoint auditing preserves the
651 fixed atoms and original ADPs; Gemmi 0.7.5 independently reads 855 atoms,
H3 and the original cell from every file. No GUI visual review is claimed.
Full versus rounded coordinates remain distinct. Nothing is committed/uploaded
from either generated directory; no checkpoint or selection is created.

Exact local commands use `PYTHONDONTWRITEBYTECODE=1` and the pinned Python 3.12
controller with `run-source-controls.py`, `summarize-source-controls.py`,
`observe-source-controls.py`, `review-source-observations.py`,
`archive-source-controls.py` and `export-source-inspection.py`. Their complete
bytes/logs are archived. The existing owned runner launches native
`phenix.python -B evaluate.py`, with 3600-second trial and 600-second observer
caps. This is complete execution, not a dry-run. W98/C331 runtime, scientific
thresholds and schema stay unchanged; no new full-suite or installation claim.

### Installed C338 compatibility during W100

A separate, read-only virtual combination pins Willow
`06323002aebafa1aaca0ad782a0f2c1956ccc3af` and Cedar
`80c10e2c07cc8588a67927330a36f37a28509965`. A disposable Git object store reads
the original objects without writing either branch/index. There are **zero
source conflicts, seven documentation conflicts and one package-data conflict**.
Only the temporary package-data conflict is resolved, retaining both the viewer
HTML and replay PDB resources. Resolved tree:
`685811d0fabc448d1e757896eff5d588d198348a`; no actual merge.

The installed wheel passes **1,062 tests + 22 subtests in 82.65 seconds** after
moving the build source away: exactly 28 TopoStitch modules and 11 shared/Cedar
modules, including AutoRefine, checkpoints and C338's actual-manager reporting.
Six CLI helps pass. Saved old/new graph, complete frame, default-owner native-link
and packing replays are exact with original source/capture paths blocked. Both
package resources survive. Installed legacy-v2 reader pins match the frozen
helper fixtures and unchanged shared sources. Wheel SHA256:
`6cf484ba5351e98bffbffe1ad65c78cfdbbbc59e9332723bff1be8bc35ced48f`.

The first launch was refused by sandbox scheduling permissions before build/tests;
the unchanged low-priority check then ran outside the sandbox. After the tests
and saved replays passed, an extra local assertion incorrectly expected historical
v2 helper fixtures to be packaged. The actual contract retains helpers in each
run. That assertion was replaced by explicit legacy source-hash validation;
replay and helps passed, without product changes or repeating passed tests.
Both original failures remain in the evidence.

Exact commands, explicit module list, raw logs, snapshots and wheel are in the
verified local 51-file archive, under the everyday NASolve anchor:
`branch-artifacts/willow/w100-c338-installed-composition-2026-11-16.tar.gz`,
SHA256 `e152b276aeb087ff4fd8902e8b3b6ab1eed4e88691aa63a4e76c98bda4aeb5d9`.
The controller uses `PYTHONDONTWRITEBYTECODE=1`, the installed prefix on
`PYTHONPATH`, `pip wheel --no-deps --no-build-isolation`, isolated target install,
and `pytest -q -p no:cacheprovider` with the 39 named modules in `receipt.json`.
`audit-scope.json` is the authoritative test selection. This is focused installed
compatibility, not a full combined suite, native combined refinement, resolved
human-document merge or scientific acceptance. C340 is not part of this pin.
W100 native controls completed with unchanged installed W98/C331; no dependency,
API, runtime or branch migration. No archive payload is committed or uploaded.


### Next ordinary refinement boundary

Read-only coordination with Rowan and inspection of Cedar's C338/C343 source
confirm that S06 should reuse `refinement_parallelity.prepare_execution` and
AutoRefine's frozen round/checkpoint owner. `cif_refinement_runtime._run_observed`
already shares the actual native manager and final writer;
`cif_refinement_output` binds the scattering state and written coordinates.
The C338 `cif_refinement_sites` observer covers source-projected local triples;
it is not a complete periodic-pair observer or an additive-force adapter.

The next integration qualification must bind the complete ordered pair recipe,
exact atom/image identities and actual exclusion policy to the initialized,
selected/rebuilt and final managers. Observe native normalization and prove
added energy/force accounting, with missing, duplicate and stale-term negative
controls. Bind the result to the actual final model and a versioned frozen helper;
reusing a lifecycle owner alone does not qualify these new terms. C291-C294's
whole-objective controls provide the existing method: call the actual
`model.restraints_manager_energies_sites` without switching restraint families,
and retain each manager's own normalization/contact inventory. Do not compare
normalized targets across rebuilt managers as if their denominators were fixed.

Only after that boundary is qualified should a predeclared candidate/no-repair
comparison reuse the same observations, Free-R flags, phase policy and refinement
budget. Inspect local geometry, periodic contacts and model-bound maps alongside
Rwork/Rfree. This is the path to density-aware bending; current W100 geometry
regularization and installed C338 compatibility do not close S06. No new runner,
callback, force policy, schema or native execution is introduced by this plan.


## W101 — Pair-kernel composition before ordinary refinement

A static concern was that Willow's explicit plane-force correction might be
applied twice when Cedar's ordinary runtime installs its corrected
`ParallelityKernel`. Reading the correction showed a possible safe composition:
it subtracts the currently evaluated container contribution before adding the
checked manual contribution. A complete native microprobe now tests that point;
no defect or product patch is presumed from the initial concern.

For both W100 source models, the same complete ordered recipe is evaluated with
the original native residual-sum binding and with the existing Cedar kernel
installed temporarily at that binding. Cedar's existing whole-objective probe
uses its unchanged four finite-difference steps, tolerances, six deterministic
plane atoms and full/global directions. **All four cases pass 20/20 directions**
(162 evaluations each), baseline repeats and recorded context checks. Baseline
targets and all gradient components are **exactly equal** between the two kernel
contexts for each source. The existing correction composes safely in these cases;
no corrective code, native binding change or tolerance adjustment is needed.
The original binding is restored, and inputs/software remain unchanged.

The complete owned **Phenix 2.2.1-6174 / dispatcher 2.2.1 / Python 3.11.15**
execution takes 18.04 seconds under a 600-second cap. The native module profile
is verified, and the pinned C331 kernel bytes equal C338's kernel. This tests
pair-energy/force arithmetic only: it does not attach the complete policy to an
ordinary refinement manager, prove selection/rebuild persistence, normalize the
combined geometry objective, or qualify a diffraction refinement or final writer.
Those remain the [S06 integration gate](#next-ordinary-refinement-boundary).

An earlier launcher exposed the Python 3.12 installed prefix to native Python
3.11; NumPy import failed and the native process exited -11 before numerical
comparison. That attempt is retained. A fresh V2 preparation exposes only the
pure package path, rejects foreign dependency paths and verifies the old process
is absent before launch. Models, recipes, cases and numerical policy are unchanged.
The plan's pre-execution state is historical; execution receipts record the
completed native observation. No failed numerical result was replaced.

The verified 41-file local archive is under the everyday NASolve anchor:
`branch-artifacts/willow/w101-pair-kernel-composition-2026-11-16.tar.gz`, SHA256
`3bd123dc9dad4dd9daf021889e6255812cb58bd29860abcdd949c8c3bd7ce832`.
It includes both attempts, exact plans/inputs, consumed helper sources, native
profile, process receipts and raw/replayed derivative records. It is not committed,
not an autonomous portable campaign and not scientific acceptance. Historical
V2 root: `/private/tmp/willow-pair-kernel-boundary-v2/`. Exact controller command:
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python run.py`;
the existing owner launches `phenix.python -B probe.py`. Runtime/API/schema and
installation remain W98; documentation validation is roadmap regeneration/check,
JSON readback and `git diff --check`, not a repeated full software suite.


## W102 — Complete pair arithmetic through actual model entry

The W101 pair kernels now compose through the real
`mmtbx.model.manager.restraints_manager_energies_sites` entry point. The probe
constructs each W100 source with its frozen NCS parameter, unchanged atom order,
normalization enabled and the existing Cedar corrected parallelity kernel. It
checks all 855 atom identities, crystal identity and the W100 static fingerprint,
then repeats on the actual `model.select(all_atoms)` result. That fingerprint
alone does not independently inventory every angle/plane symmetry field.

A local diagnostic binds the complete pair callback only for an explicit call,
restoring the prior empty slot afterward. **Eight controls pass 20/20 derivative
directions each** (162 evaluations per case): two sources, original/select-all
managers and native-only/pair-active objectives. Existing Cedar four-step probe
tolerances remain unchanged; independent review reproduces every saved review,
baseline repeat and unchanged recorded context. Zero-valued callbacks leave the
target and every gradient exactly unchanged; energy-only evaluation agrees.

The pair residual and forces use the same native denominator without increasing
its restraint count. Healthy and displaced managers have **11,389 and 11,263**
restraints respectively; each select-all result retains its own source count.
Maximum added-gradient accounting error is 2.78e-17. Different coordinate-dependent
neighbor inventories can produce different denominators, so normalized targets
across models must not be compared as if the count were fixed.

Twelve local negative controls reject partial atom selection, changed identity,
an existing callback, disabled normalization, disabled geometry families and a
supplied external gradient buffer, once per source. Native bindings are restored;
source inputs and consumed software hashes remain unchanged. **Phenix
2.2.1-6174 / dispatcher 2.2.1** completes the owned execution in 168.92 seconds
under its predeclared 900-second cap, exit 0. No optimizer or diffraction data
are used, and no output coordinates are produced.

This is explicit per-call rebinding, **not automatic ordinary-refinement
selection/rebuild integration**. C331 policy snapshots observe idle, callback-free
default energy-only settings before/after restoration; they do not qualify the
actual internal shared gradient buffer or custom callback. Existing exclusions
are unchanged; complete image-bearing term/exclusion accounting, missing/duplicate
term controls, callback-aware guarding, final-writer binding and matched refinement
remain separate gates. No production adapter or second refinement runner is added.

Exact historical controller: `/private/tmp/willow-model-entry-boundary/`, with
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python run.py`,
then the same interpreter running `audit.py`, and `python3 archive.py`. The owned
runner invokes `phenix.python -B probe.py`. Plan SHA256:
`bcd4abc700ce07a5c33f54851f029caaa7345022e3ef11313b618028ae0899fb`.
The verified 43-file local forensic archive is under the everyday NASolve anchor:
`branch-artifacts/willow/w102-model-entry-2026-11-16.tar.gz`, SHA256
`334b644f247427531bd4942cde6506d11eb995495212966a9391c534fcdd4e72`.
It retains plans, sources, native/process records, numerical probes and audit
code/results. It is uncommitted and not an autonomous portable campaign.
Runtime/API/schema and installation remain W98; this documentation update uses
roadmap regeneration/check, JSON/evidence readback and `git diff --check`, without
claiming a repeated full suite or new installation validation.


## W103 — Actual pair membership and ordinary PHIL exclusions

The next boundary is not just adding the numerically qualified W102 callback.
Ordinary refinement can already contain core-pair terms and a different exclusion
policy. A local read-only probe now compares each complete requested term with
actual bond, angle, plane and parallelity proxies, retaining targets, weights,
per-atom images and ordered native occurrences. Support comparison allows a common
crystallographic image and the appropriate endpoint/plane permutations; it never
wraps lattice translations or discards native multiplicity. Cedar's C331 observer
supplies exact exclusion shells, and `capture_asu_pairs` supplies directed repulsion.

Both source models are inspected before selection, after actual all-atom selection,
and after selected-model reinterpretation with a newly constructed geometry manager.
All six have the same **956 bonds, 1,467 angles and 42 planes**. None of the complete
recipe's **124 terms** (36 bonds, 60 angles, 14 planes, 14 parallelity terms) have
matching native supports. All 36 intended hydrogen-bond contacts remain in native
repulsion (39 directed rows), with none in the exclusion shells. This describes
the earlier additive diagnostic policy; it does not establish that removing or
retaining those terms is scientifically preferable.

A separate predeclared control applies ordinary PHIL for exactly the 12
identity-image core pairs. It replaces only the frozen virtual L/R selections
with declared source sites, leaving the two periodic selected pairs uninstalled.
Both inputs then contain **107 matching core terms**: 31 bonds, 52 angles,
12 planes and 12 parallelity terms. All targets/weights/modes match the recipe,
and all previous native definitions are preserved. The 31 core contacts acquire
native shell exclusions; only the five periodic requested contacts remain in
repulsion. Ordinary PHIL removes **117 directed nonbonded rows**, including
indirect exclusions, rather than only the 31 requested contacts. The normalization
count consequently decreases by ten: **11,389 → 11,379** for the healthy source
and **11,263 → 11,253** for the displaced source (107 added minus 117 removed).
A complete callback appended here would double-count core forces. Equal pair
formulas alone do not establish equal full objectives or exclusion semantics.

Each observation leaves that manager's target, complete gradient and coordinates
exactly unchanged. Independent **Gemmi 0.7.5** image matching checks every saved
native/requested support, exclusion and directed-contact association; maintained
Cedar pair arithmetic reproduces captured repulsion sums. Five algebra controls
cover reciprocal bonds, reversed angles, permuted planes, exchanged parallel
planes and preservation of integer cell translations. These are not runtime
missing/duplicate/stale rejection tests. All observed atoms occupy general
positions; special-position equivalence remains unqualified.

Selected-model reinterpretation changes only the recorded cell lengths in the
C331 policy: `105.54699999999998` becomes `105.54699999999997` for a and b. The
maximum coordinate change is 1.42e-14 Å; target changes are at most 6.0e-15. Static
term definitions and exclusion shells stay exact. The exact policy digest does
change, so future lifecycle integration must explicitly requalify the reconstructed
manager; this result does not justify loosening the shared guard or silently
adopting a new baseline.

Complete owned **Phenix 2.2.1-6174 / dispatcher 2.2.1** executions take 6.13 seconds
for six source-manager observations and 4.27 seconds for two ordinary-core controls,
each under a 600-second cap. Both exit 0, restore native kernel bindings and preserve
inputs/software. An initial attempt used Python `*` for `rt_mx` composition and
failed before model construction; the fresh attempt uses native `.multiply` and
retains the original failure. No optimizer, diffraction refinement, coordinate
output, production observer, callback activation or scientific acceptance is added.

The next implementation should bind the complete intended recipe to native terms
plus explicitly authorized missing periodic terms, with target/image mismatches
and duplicate/missing/stale coverage refusing. Retain ordinary core restraints and
qualify periodic exclusion behavior separately. Integrate through the existing
frozen AutoRefine actual-manager/final-writer owners; do not create a second runner
or infer exclusion policy from a missing neighbor row. W100 remains a valid matched
comparison under its recorded additive policy, not an ordinary-PHIL-equivalent run.

Historical roots are `/private/tmp/willow-pair-inventory-boundary/` (failed API
attempt), `/private/tmp/willow-pair-inventory-boundary-v2/` (source observations)
and `/private/tmp/willow-pair-inventory-native-core/` (ordinary PHIL control).
The latter two run `run.py` then `audit.py` using
`/private/tmp/willow-w94-pivot/env/bin/python`; the owned runner invokes
`phenix.python -B probe.py`. Source plan SHA256 is
`73363c4edd79a703001c6fd8cdf275e30cb757075845b7cf75be95376888bb5a`;
ordinary-core plan is
`7b4fa84c273ea218ab7f101509c597374f3a9cc53e79ed048a31ea3d6ba9f24a`.
The 73-file verified local forensic archive under the everyday NASolve anchor is
`branch-artifacts/willow/w103-pair-inventory-2026-11-16.tar.gz`, SHA256
`a9bad887a61288978a9cc6394692b1a6e8c4aa3a3d2f712edd1575274266336e`.
All inputs, failures, native inventories, plans, consumed sources and independent
audits remain local and uncommitted; this is not an autonomous portable campaign.
Runtime/API/schema and installation remain W98. Documentation validation is
roadmap regeneration/check, JSON/archive readback and `git diff --check`; no new
full-suite or installation result is claimed.


## W104 — Explicit native/additive term coverage

`nasolve.topostitch_pair_coverage.review_pair_coverage` is an opt-in, read-only
Python API for the W103 double-counting boundary. It requires every requested
term exactly once from its explicitly assigned native or additive provider.
It does not infer a provider, remove existing terms, manufacture missing terms,
modify exclusions or attach a callback. Existing commands, runtime behavior and
saved recipe packets remain unchanged.

The caller supplies three ordered lists: the complete requested recipe, complete
observed native terms in the four supported families, and explicit proposed
additions. Each term contains `term_id`, `kind`, `atoms`, `other_atoms` and
`parameters`. An atom reference is `{"atom": "source label", "rotation": [nine
integers], "translation": [three reduced rational strings]}`. The nine fractional
rotation entries are row-major; translations retain whole-cell offsets. Complete
source atom labels are distinct and frozen. `other_atoms` is nonempty only for
the second parallelity plane.

| Family | Complete score parameters |
| --- | --- |
| bond | `ideal`, `weight`, `slack`, `limit`, `top_out` |
| angle | `ideal`, `weight`, `slack` |
| planarity | `weights`, in the same order as `atoms` |
| parallelity | `ideal`, `weight`, `slack`, `limit`, `top_out` |

`frozen` contains `context`, `requested_sha256`, `native_sha256`,
`additive_sha256` and the ordered `native_requested_ids`. Compute inventory
fingerprints with the existing `recipe_digest`; the remaining requested IDs
must be supplied by the additive list. `current_context` must reproduce the
frozen context exactly: `source_model_sha256`, `recipe_sha256`, `atom_labels`,
`crystal_sha256` and `native_exclusion_policy_sha256`. A changed manager requires
explicit upstream requalification, never silent baseline replacement.

The checker reuses the existing packing owner's exact rational relative-image
arithmetic. Bond endpoints and angle ends may reverse; plane atom order and the
two parallel planes may exchange under a common crystallographic image. Plane
weights follow their atoms. Different lattice translations stay different.
Targets and modes compare exactly; reciprocal-square weights allow only relative
rounding tolerance 1e-12, with no absolute tolerance that could merge distinct tiny
weights. Inventories are bounded to 25,000 terms each and 64 references per term;
standard fractional translation denominators must divide 24. Rotational parts
must be proper unimodular integer matrices; inversion/reflection images are
outside this coverage policy. Unsupported fields,
malformed images and duplicate occurrence IDs refuse.

The result records ordered provider/occurrence coverage, frozen and input digests,
requested-term counts for each provider and the total observed native term count.
These counts are **not Phenix's normalization denominator**. The result has
`declared_coverage_complete=true`, `runtime_authority=false` and
`scientific_acceptance=false`; it cannot authorize activation.

This is a declaration checker, not a native observation or authentication engine.
The caller must establish complete actual inventories, valid group membership,
general-position scope, source/recipe identity and exclusion-policy authenticity.
It cannot detect native terms omitted by a dishonest or incomplete producer whose
hashes were frozen that way. Special-position equivalence, actual forces,
normalization, callback-aware policy guarding, selection/rebuild interception,
final-writer binding and diffraction remain with their existing owners and still
need integration qualification. No new serialized runtime helper is activated.


### W104 validation — 2026-11-16

Code `97f5bbec3b410338586481893855c635ef684831` changes one new optional module
and its regression file, with architecture/usage/changelog documentation. There
is no dependency, CLI, existing packet or runtime-helper migration. Thirty-four
initial tests fail before the API exists; a further noncommuting-image regression
brings the final new tests to **35 passing**. The complete Willow suite passes
**1,911 tests +229 subtests in 101.75 seconds**. A fresh sdist is relocated after
removing its staging source, then built/installed; both source staging paths are
absent for **204 installed tests**, six CLI helps, `pip check`, lean import and
exact source/installed module-byte checks. Python 3.10 syntax parsing passes.

The installed checker replays all eight retained W103 native inventories: source
cases have 124 additive terms; ordinary-core cases have 107 native and 17 additive
terms. Twelve actual-derived negative controls reject duplicate complete callbacks,
missing/duplicated native occurrences, changed targets, wrong periodic images and
stale reconstructed contexts. Source and installed results are exact after input
relocation; this is **saved native evidence replay**, not new Phenix execution.
The earlier Phenix 2.2.1-6174 observations retain their W103 limits. No Coot run.

The first installed test harness copied tests without the existing developer
script used by one packing-reader regression: **203 pass, one fails with
FileNotFoundError**. The original log/script are retained. Copying that unchanged
script as a test fixture allows all 204 to pass with the same installed wheel;
no product change or unsupported packaging claim is made. The new source/test
paths have no overlap with Cedar `32316a76`; this is a compatibility review, not
a combined branch or native-runtime qualification.

Exact principal commands (historical scratch root
`/private/tmp/willow-w104-coverage/`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_coverage.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python install-finish.py
```

The first installation command's fixture failure and the second command's
completion are distinguished above. Wheel SHA256:
`c920e837f96cd043d77c86a71ca73ddd940513e97a6dd7a1fb73c689cdc01950`.
The verified 29-file local forensic archive under the everyday NASolve anchor is
`branch-artifacts/willow/w104-pair-coverage-2026-11-16.tar.gz`, SHA256
`c8c427e12363c93ef0d0936c76e741a1bbe0bc5b2ad31b4ac0aec5d6b922e7f4`.
It retains software/distributions, exact inputs, both installed-test outcomes,
commands and replay results. Generated scientific observations remain uncommitted;
the archive is not an autonomous portable campaign or scientific approval.


## W105 — Declarations from the existing compiled recipe

`nasolve.topostitch_pair_coverage.describe_compiled_pair_terms(recipe, packet,
expected_binding_sha256=...)` exports an already-constructed `NativePairRecipe`
for the W104 checker. Freeze the expected digest from the original
`recipe.binding_report()` with `recipe_digest`; supply the original checksum-bound
packet. Do not refresh that digest to accept drift. The existing constructor
remains the sole PHIL parser/compiler and source-model validation owner.

The adapter reads the actual compiled bond, angle, planarity and parallelity
proxies, checking their membership, complete score parameters, family counts and
absence of additional images on already-expanded coordinates. Each reference
must belong to the packet's disjoint L/R roles. Exact fractional operators come
from cctbx and retain lattice translations; their Cartesian form must agree with
the compiled references (relative tolerance 1e-12, absolute 1e-10). This tolerance
checks a floating-point representation, not coverage equivalence: W104 still
compares rational images exactly. No force evaluation or native attachment occurs.

The returned policy is `topostitch-compiled-pair-declarations-v1`, with
`compiled_binding_sha256`, `source_model_sha256`, `recipe_sha256`, `atom_labels`,
`terms` and `terms_sha256`. Atom labels are sorted-key compact JSON of each full
source identity, in the existing source order. Term IDs combine pair ID and
zero-based global term ordinal. Both authority/acceptance flags are false. The
returned arrays are detached from the recipe and caller data.

This is an explicit adapter to the existing class's compiled containers, with
regressions guarding that interface. It does not create a second compiler,
change binding schema 1, or modify captured worker sources. Imports remain lean;
cctbx/scitbx are needed only when the optional native exporter is called. The
caller still owns native-profile qualification, complete actual-manager
observation, special-position scope, exclusion approval, active forces,
normalization, lifecycle and final-writer binding. There is no new CLI or
migration of existing packets/checkpoints.

### W105 validation — 2026-11-16

Twelve new regressions fail before implementation; all **47 coverage tests**
now pass. The complete suite passes **1,923 tests +229 subtests in 92.86 seconds**.
A fresh relocated sdist/wheel passes **216 installed tests**, six CLI helps,
`pip check`, lean import and Python 3.10 syntax. Both staging source directories
are absent during installed validation. The installed recipe engine and captured
worker files remain byte-identical to W104.

A complete read-only **Phenix 2.2.1-6174 (dispatcher 2.2.1)** execution checks
healthy and displaced sources under raw and Cedar-corrected kernels: all four
cases export **124 terms (36 bonds, 60 angles, 14 planes, 14 parallelities)**,
exactly matching the independently Gemmi-derived W103 records. Full energy and
gradient arrays and old recipe bindings are unchanged before/after. Eighteen
native negative controls reject changed proxy parameters/images, missing/extra
proxies and stale binding/packet inputs. All inputs/software and kernel binding
are preserved. This is an installed exporter qualification against pinned C331,
not a new refinement, density test or combined latest-Cedar qualification.

The original native attempt is retained: two healthy cases pass, then the harness
tries to assign read-only `parallelity_proxy.top_out`. Native return code 2 is
recorded. A separate V2 harness substitutes distinct native proxy objects and
restores original containers; unchanged product/wheel passes in 3.02 seconds.
No thresholds or scientific acceptance criteria changed. Cedar `6f2bd7e0` has no
source-path overlap with this change; no Cedar files were edited.

Exact commands from the Willow checkout and local validation root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_coverage.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w105-declarations/install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w105-declarations/native-v2/run.py
```

Scientific inputs, native records, distributions and failed-attempt evidence stay
in a local forensic archive, excluded from Git. This is not a portable autonomous
campaign. Next: authenticate the actual manager's complete native inventory and
bind it to the existing exclusion-policy and frozen lifecycle owners before any
force activation. S06 remains partial.


## W106 — Complete callback-free native inventory observation

`nasolve.topostitch_native_coverage.observe_native_pair_terms(model,
frozen_context=..., frozen_policy=..., policy_owner=...,
expected_policy_owner_sha256=...)` reads the actual manager's bond, angle,
planarity and parallelity proxies. `model` must be the qualified native mmtbx
model class. `policy_owner` is the caller's trusted Cedar live-nonbonded-policy
module, checked against a previously frozen source SHA256. Its existing
`require_live_nonbonded_policy` owns API/profile validation and exact policy
comparison; no second exclusion or symmetry-policy reader is introduced.

`frozen_context` is the W104 context, including complete ordered atom labels,
source/recipe digests, crystal digest and native exclusion-policy digest. The
crystal digest is `recipe_digest(frozen_policy['policy']['symmetry'])`. This
observer verifies current native atom identities against those labels, finite
coordinates, general-position scope and the frozen policy. It does not prove
that the caller's source/recipe digests came from an authoritative run; existing
checkpoint/frozen-runtime owners must establish that lineage and source lifetime.
C331's platform/native-profile and callback-free restrictions remain in force.
The current qualified profile is Phenix 2.2.1-6174 on macOS ARM64.

Both simple and ASU bonds retain exact endpoint images; other supported families
retain their native per-atom images. Group membership uses exact rational
rotations and translations modulo integers, avoiding cctbx's denominator-sensitive
membership assertion. **Only membership** uses that reduction: exported atom
images retain every whole-cell offset. Native atom/term bounds and parameter
validation reuse the coverage checker. Origin IDs are recorded in term order as
provenance, separate from the score parameters used for coverage.

The observer reads inventories twice and invokes the unchanged policy owner
before/after. It also checks the manager identity, coordinates, atom identities
and policy-owner source remain unchanged. Pair-cache refresh is possible; no
energy evaluation, coordinate edit, callback attachment or exclusion mutation
is requested. Single-owner access is required: repeated reads detect drift but
are not a lock against concurrent mutation. An already warm, supported manager
and its independently qualified baseline are required.

The returned policy is `topostitch-native-pair-observation-v1`: `context`,
`policy_owner_sha256`, `terms`, `origin_ids`, `terms_sha256` and `points_sha256`,
with both runtime/scientific authority flags false. The complete observation
should be frozen by its caller; the term digest deliberately represents score
coverage, not origin metadata. These are the four configured proxy families,
not all crystallographic forces or a normalization denominator. Callback-aware
active policy, force accounting, selection/rebuild interception and final-writer
integration remain separate gates. No new CLI, dependency, existing-packet
migration or change to NativePairRecipe/captured workers is made.

### W106 validation — 2026-11-16

Twelve initial regressions fail before implementation. A later native ASU-image
control exposes a real denominator-sensitive membership failure; its added
regression fails before the rational fix. Final **60 focused tests**, **1,936
full tests +229 subtests in 97.27 seconds**, and **229 installed tests** pass.
Fresh sdist/wheel staging sources are removed before installed validation; six
CLI helps, `pip check`, lean import, Python 3.10 syntax and unchanged existing
compiler/worker bytes are verified. Initial 1,935+229/228 installed results are
retained as pre-fix evidence, not substituted for final validation.

The final installed Phenix 2.2.1-6174 (dispatcher 2.2.1) execution completes eight
healthy/displaced original, select-all, reinterpreted and ordinary-core manager
cases in 34.16 seconds. Every term/image/parameter/origin exactly matches the
independent W103/Gemmi records. Ordinary sources contain 2,465 supported native
terms and require 124 additions; ordinary-core sources contain 2,572 native
terms and supply 107 requested terms, leaving 17 explicit additions. All eight
coverage checks pass with unchanged complete energy/gradient arrays and sites.
Twelve negatives reject existing callbacks, stale rebuilt policies and changed
native core targets. Small reinterpretation cell drift remains a strict mismatch.

A separate isolated C++ proxy-codec control covers a symmetry-bearing simple
bond, a real ASU-mapped bond, image-bearing angle/plane proxies and ordinary
parallelity. Independent Gemmi 0.7.5 replay verifies all five rows, retained
whole-cell offsets and nonuniform plane weights. The model is not given these
synthetic restraints; its complete energies/gradients remain unchanged. This
qualifies encoding, not the stock manager's ability to evaluate image-bearing
angles or a physical connection.

All attempts remain local: the first image probe finds that the native
parallelity constructor rejects `sym_ops`; V2 then exposes the denominator
assertion; V3 passes after the product fix. Ordinary native parallelity therefore
remains identity-image; periodic parallelity uses the existing virtual expanded
recipe. The eight-manager panel is rerun against the corrected wheel and passes.
Neither this observation API nor the codec probe enables refinement or proves
scientific acceptance. Cedar source paths are untouched; this is pinned-C331
composition, not a merged latest-Cedar build.

Exact principal validation commands (Willow checkout unless absolute):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_native_coverage.py tests/test_topostitch_pair_coverage.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w106-native-coverage/install-check-v2.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w106-native-coverage/native-v2/run.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w106-native-coverage/image-codec-v3/run.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w106-native-coverage/audit-images.py
```

Generated models, inputs, native reports, wheels and failed diagnostics are
excluded from Git and retained in the local forensic archive. They are not an
autonomous portable campaign. Next: qualify only the explicitly missing additive
terms with existing native core terms, retaining complete frozen coverage,
exclusion policy and actual normalization; then integrate the existing frozen
refinement lifecycle. Do not append the complete recipe or infer exclusions.


## W107 — Native core plus only the missing periodic terms

The next bounded arithmetic control composes the W104–W106 APIs with the
existing W102 actual-model energy probe. Ordinary core PHIL supplies **107**
requested terms. The existing `prepare_pair_recipe` generates a separate packet
for the two explicitly declared periodic pairs, supplying the remaining **17**.
Its pair rows must exactly equal the corresponding rows of the complete original
packet. Both source/recipe identities are frozen; full requested coverage is
checked against the actual manager before/after each manager case. The whole
124-term recipe is never appended on top of native core forces.

This uses the current W106 installed wheel and pinned C331 owners with complete
Phenix **2.2.1-6174 (dispatcher 2.2.1)** execution. Healthy and displaced sources,
each before/after explicit all-atom selection/rebinding, are tested in native-only
and native-plus-missing-pair modes. All **eight derivative cases pass 20/20
directions**, using the unchanged four-step Cedar probe: **162 evaluations each,
1,296 total**. The diagnostic completes in **192.80 seconds**, under its original
900-second owned-process cap. No optimizer, diffraction data, edited model or
Coot session is involved.

| Input | Actual native denominator | Raw 17-term additive energy |
| --- | ---: | ---: |
| Healthy | 11,379 | 228.7895161473 |
| Displaced | 11,253 | 499.2917956480 |

Zero-valued callbacks preserve native targets and complete gradients exactly.
The additive energy and complete force vectors use the actual native denominator
without incrementing its count. Maximum force-composition discrepancy is
**1.39e-17**; maximum target-composition discrepancy is **5.21e-17**. Energy-only
calls agree. These are arithmetic errors, not geometric displacement measures or
claims that either structure improved. The two denominators differ: never carry
a normalization count blindly across input models or rebuilt managers.

All **12 negative controls** refuse partial atom selection, changed identity,
existing callbacks, disabled normalization, changed family flags and supplied
external gradient buffers before invoking the diagnostic callback. Complete
native definitions, exclusion policies, input/software hashes and temporary
kernel/method bindings are preserved. Independent replay reproduces all saved
Cedar derivative reviews and coverage results. Six reused Cedar source/profile
files are byte-identical in current Cedar `162ffe1d`; that is a source compatibility
check, not a merged latest-Cedar runtime qualification.

C331 still observes only the restored callback-free, default energy-only policy
before/after calls. It does **not** qualify the active custom callback or actual
model-provided internal gradient buffer. The diagnostic binds its callback for
each call and restores it; no automatic ordinary-refinement interception,
selection/rebuild lifetime or final-writer integration is enabled. Existing
periodic nonbonded repulsion is deliberately retained. Arithmetic correctness
does not approve that exclusion policy or make it equivalent to ordinary PHIL
for every periodic contact.

The initial preparation failed before staging inputs because `ResidueSite` was
imported from the wrong module; its original driver is retained and the import
was corrected to the existing coordinate owner. Archive assembly initially
refused an unchanged base-module provenance path from the earlier pinned
installation. An explicit installed-file/wheel-member hash audit proves the
actual imported copy has identical bytes; archive classification was corrected.
Both failures remain recorded. No diagnostic settings, runtime code or acceptance
thresholds changed to obtain a pass.

Exact commands (historical local validation root):

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w107-missing-pair-arithmetic/prepare.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w107-missing-pair-arithmetic/run.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w107-missing-pair-arithmetic/audit.py
python3 /private/tmp/willow-w107-missing-pair-arithmetic/archive-finish.py
```

All scientific inputs, native logs, recipes and retained failures are local and
excluded from Git. The verified forensic archive is not an autonomous portable
campaign. This is a diagnostic/documentation update; no source patch requires
another install/full-suite run beyond W106's recorded validation.

### Next integration gates after W107

1. **Explicit provider selection.** General production selection must consume
   frozen term-level provider assignments and exact compiled parameters/images.
   Do not infer a provider from `selected`/`core` labels or assume whole pairs are
   always missing. W107's whole-pair split is a declared control, not the general
   selection algorithm. Reuse the existing compiler; qualify any compiled-term
   subset against the complete recipe and reject overlap or omissions.
2. **Frozen lifetime and active guarding.** Reuse Cedar's
   `refinement_parallelity.prepare_execution`, frozen round/checkpoint lifecycle,
   C338 actual-manager observation and final-writer owners. Bind all consumed
   helper/profile bytes and both complete/additive recipe identities. A separate
   callback-aware protocol must qualify buffer ownership, actual force activity,
   normalization and source/exclusion preservation through selection/rebuild;
   keep C331's callback-free contract unchanged. Boundary scans are not a proven
   per-evaluation guard or a concurrency lock.
3. **Exclusion policy.** Preserve W103's distinction between score coverage and
   native shell exclusions. The missing periodic hydrogen-bond contacts still
   participate in native repulsion here. Either retain that policy explicitly or
   qualify an intended ordinary-pair-equivalent periodic exclusion transformation
   against identity-image and periodic controls, complete repulsion and force
   counts. Never silently delete repulsion or infer covalent closure. Cross-image
   phosphate bonds/angles remain a separate gate; Cedar keeps OP1/OP2 intent.
4. **Matched scientific trials.** Only after those gates, use predeclared
   candidate/no-repair siblings with identical observations, Free-R, refinement
   budgets and model-bound maps. Retain healthy/wrong-connection and forward/reverse
   shape controls, geometry/packing/twist/rise tradeoffs, and calibrated backbone
   difference-density review. B09 geotest alignment remains the final demonstration,
   not an acceptance claim from these derivative controls. No repeated Rfree-led
   tuning or campaign adoption is enabled.


## W108 — Frozen term-level provider selection

`topostitch_pair_coverage.select_pair_providers(requested, native, *, frozen,
current_context)` plans coverage using the existing exact atom/image and score
parameter rules. `frozen` must contain exactly `context`, `requested_sha256` and
`native_sha256`, bound before selection. The caller supplies authenticated complete
observations; matching cannot discover omitted native terms or approve chemistry.

The result contains detached `additive` declarations, the complete W104 `frozen`
binding and its `review`. Native matches must be unique and parameter-compatible;
a conflict refuses instead of adding a second force. Only absent requested supports
become additions. Unrequested native terms, including custom chemistry/metal terms,
remain untouched. Providers do not follow a pair's purpose or identifier: one pair
can have native bonds and missing angles/planes. Retain the returned binding for
`review_pair_coverage`; reselecting after drift is not a valid replay.

This optional planner changes no existing default, compiler, worker, CLI, packet
schema or dependency. It does not evaluate the selected subset, attach a callback,
approve exclusions, infer metal/base roles or qualify ordinary refinement.
General-position, proper-rotation and standard-setting limitations remain W104's.
The next step is to evaluate the exact frozen additive subset through the existing
compiler/kernels, then qualify active policy and the ordinary frozen-round lifetime.

### W108 validation — 2026-11-17

Fifteen selection regressions failed before the API existed; sixteen new tests
cover mixed within-pair providers, all-native/all-additive plans, equivalent images,
whole-cell offsets, weighted planes, stale bindings and conflicting/duplicate terms.
**76 focused, 1,952 full tests +229 subtests, and 245 installed tests pass.**
The full suite took 107.60 seconds. Fresh sdist→relocated wheel installation removes
both source stages before testing; six CLI helps, `pip check`, lean imports and
Python 3.10 syntax pass. Existing compiler and captured-worker bytes are unchanged.

A complete **Phenix 2.2.1-6174** diagnostic uses the two retained sources and their
independently recorded native inventories. Six cases compare full native core,
a deliberately partial individual pair, and that partial manager after select-all.
Removing one angle, one planarity and one parallelity term from a single pair
changes the split from **107 native +17 additive** to **104 +20** while retaining
that pair's native bonds. Complete remaining membership matches the independent
inventory with precisely those three terms removed. Twelve negatives reject
duplicate native support and conflicting native targets. Planning preserves every
coordinate and complete native energy/gradient array. No optimizer, diffraction,
model export, activation or scientific repair is claimed.

Principal commands (Willow checkout unless absolute):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_coverage.py tests/test_topostitch_native_coverage.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w108-provider-selection/install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w108-provider-selection/native/run.py
/private/tmp/willow-w108-provider-selection/install/env/bin/python /private/tmp/willow-w108-provider-selection/audit-native.py
```

Absolute command paths are local historical provenance. Scientific inputs, native
outputs, test logs and build products remain local; the machine roadmap records
the anchored forensic archive and checksum. No scientific payload is committed.
The native diagnostic composes the pinned C331 owner, not a merged current Cedar
build. Full combined-branch, active callback/buffer policy, periodic exclusions and
matched density/refinement acceptance remain open.


## W109 — Evaluate the exact frozen additive subset

`NativePairRecipe.evaluate_terms(points, *, atom_identities, packet,
expected_binding_sha256, selected_terms, expected_terms_sha256,
compute_gradients=True)` accepts the exact ordered subset exported by W105 or
selected by W108. The original packet, compiled binding, live proxy parameters
and image references are checked on every call. Changed/reordered/duplicate/unknown
terms refuse, including a live-proxy mismatch when the selected subset is empty.

The method filters existing proxy containers locally, then reuses the same
kernel, Cedar parallelity correction and image-gradient pullback as full `evaluate`.
No partial PHIL is generated and no second compiler is introduced. The return
retains target/components/gradients/normalization, adds compiled-binding and
selected-term digests, and explicitly grants no runtime or scientific authority.
Default `evaluate`, binding reports, compilation and captured-worker requests
remain compatible. There is no schema, dependency or CLI migration.

The caller must replay the frozen coverage plan against the actual manager and
qualify policy, exclusions, callback/buffer ownership, source order and lifetime
separately. Reconstructing a subset digest after drift is not an authorized rebind.
This is an additive numerical evaluator, not a production refinement adapter.

### W109 validation — 2026-11-17

Twelve regressions fail before the new method exists. **117 focused, 1,964 full
+229 subtests (101.61 seconds), and 257 installed tests** pass. Fresh relocated
sdist/wheel installation removes source stages before testing; six CLI helps,
`pip check`, lean imports and Python 3.10 syntax pass. Captured-worker bytes remain
unchanged; native recipe evaluation is deliberately factored through one kernel path.

Complete **Phenix 2.2.1-6174** diagnostics cover both retained sources plus an
independent synthetic **P4_3** canonical pair with a screw image. All **six 20/20
directional checks (972 evaluations)** pass; installed independent review agrees.
Twelve composition controls at original and perturbed points prove full evaluation
exactly matches the installed W108 implementation, all-selected exactly matches
full evaluation, empty selection gives exactly zero energy/gradient, and selected
plus complementary terms reproduce the complete objective. Maximum complementary
gradient error is **7.11e-15**. Energy-only calls agree. Twelve native negatives
reject stale subsets, wrong atom order and changed live proxies, including empty
subsets. Inputs/software/kernel bindings are preserved.

The original panel remains **FAILED** after its four retained-source derivative
cases pass: the harness's default PDB hierarchy parser sorts the synthetic fixture,
so its atom-identity guard refuses. Only that fixture is rerun with
`construct_hierarchy(sort_atoms=False)` and passes; no product or geometry change.
The original attempt took 139.91 seconds; the corrected synthetic-only execution
6.61 seconds. Preserve both receipts; do not describe the first whole run as green.
No optimizer, actual-manager callback, ordinary refinement or scientific repair is
claimed by these subset controls.

Principal commands (Willow checkout unless absolute):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_coverage.py tests/test_topostitch_native_coverage.py tests/test_topostitch_recipe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w109-selected-forces/install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w109-selected-forces/native/run.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w109-selected-forces/native-synthetic/run.py
/private/tmp/willow-w109-selected-forces/install/env/bin/python /private/tmp/willow-w109-selected-forces/audit-native.py
```

Absolute command paths record local execution provenance only. The roadmap owns
the anchored forensic archive/checksum. Generated scientific inputs/results,
failed diagnostics and build/install products stay local and are not committed.
The next gate is the separate active-callback policy/lifetime contract with Cedar;
C331 remains callback-free. Native normalization and periodic exclusions still
need qualification through the ordinary frozen-round refinement owner.

## W110 — Provider normalization and active contribution contract

W108 plans exact term ownership and W109 evaluates the chosen subset. Neither
qualifies a live refinement callback. Rowan confirms no generic active-callback
owner is currently qualified. The following is a bounded shared-owner proposal,
not an instruction to relax C331 or activate ordinary refinement. Rowan reviewed
the admission/lifetime boundary on 2026-11-17; implementation and production
weighting remain unqualified.

### Smallest owner extension

Cedar should expose a separate active-contribution admission/check API using the
same native profile, exact-type reader and complete policy traversal as C331.
Keep C331's callback-free signature, policy identity, records and refusal behavior
unchanged. Do not copy `_Reader`, detach an adapter to fake idle inspection or
present fabricated callback-free invocation options. The active record has its
own versioned identity and truthful actual invocation fields.

W110 initially considered a configured callback for admission diagnostics. W111
then qualified counted-extension arithmetic, so the **counted route is the current
implementation candidate**, specified below. The configured callback is not a second
queued implementation. Ordinary model entry does not forward native extensions;
the proposed owner must qualify that missing boundary explicitly.

The trusted frozen runtime factory creates a new process-local callable and binds
its exact object plus contract/source digests. A name, object address or serialized
digest alone cannot authenticate executable code or survive restart. Single-owner
execution remains required; before/after reads are not a concurrency lock. The
actual model-owned inner gradient buffer needs provenance from its outer call,
not a blanket ban on all non-None geometry buffers.

### Frozen contract and call lifecycle

| Boundary | Required binding/check | Failure action |
| --- | --- | --- |
| Prepare | Existing run/checkpoint/parent anchors and hashes, source model, ordered full atom identities, crystal/frame, complete compiled packet/binding, native inventory and exclusion policy, W108 provider binding, W109 selected declarations, exact helper/profile bytes | Refuse preparation; preserve parent |
| Install | Actual manager and hierarchy match the frozen contract; no prior callback; original source labels/images remain valid; inspect whole requested/native coverage before installing once | Refuse, without replacing a native term or selecting a different provider |
| Enter energy call | Correct manager instance, atom order, frame, current policy and selected binding; supported flags, normalization and energy/gradient mode; no competing extension or caller buffer | Refuse before adding energy/forces |
| Inside callback | One invocation for this call; finite correctly ordered coordinates; buffer kind/length and requested gradient mode agree; source arrays are not overwritten; selected evaluator rechecks compiled definitions | Refuse and unwind; do not return an apparently valid partial score |
| Return | Exactly one callback; finite added energy/forces; actual native restraint count and normalization accounted for; unchanged source/term/exclusion contract; callback ownership retained | Mark the attempt failed; never save a selected child from partial evidence |
| Select/rebuild | Default native selection can drop the callback. Require explicit re-observation and checked rebinding to the same frozen intent; reordered/partial atoms need a qualified mapping | Unbound/new managers refuse. Do not silently inherit or reselect providers |
| Final writer | Existing Cedar actual-manager/final-output observer binds the refined model, final recipe/policy and synchronized coordinates/tensors to the immutable round/checkpoint | Incomplete evidence blocks usable publication; preserve diagnostic outputs |
| Exception/exit | Restore only bindings owned by this runtime, prove restoration, retain failure and child-process ownership evidence | A cleanup failure remains a failed attempt; never overwrite another owner's callback |

Coordinates may move during optimization; atom identity, intended frame and
restraint/exclusion ownership must remain authenticated. An updated cell, physical
identity or chemistry is not an ordinary coordinate step. Allowed neighbor-cache
rebuilding must remain distinct from a changed exclusion policy. On rebuild,
coverage can change; do not regenerate a provider plan to conceal that drift.
Any legitimate new plan belongs to a separately frozen phase with explicit lineage.

The proposed first profile admits energy-only calls and native-owned Cartesian gradient
buffers. Buffer aliasing, size, mutability, accumulation semantics, repeated calls
and reentrancy must be tested against actual C++ objects. Caller-supplied buffers
remain unsupported until separately qualified. A zero-scale diagnostic still
checks the same bindings; zero contribution is not a bypass for invalid inputs.

### Energy, normalization and exclusions

The inspected Phenix 2.2.1-6174 `geometry_restraints.energies` adds callback residual
and gradients before finalization but **does not increment `number_of_restraints`**.
The actual `mmtbx.restraints.manager` passes its own gradient buffer into geometry
with `normalization=False`, aggregates counts/energies, then applies model-level
normalization. W107's unchanged-native-denominator behavior is a valid diagnostic
policy, **not provider-independent geometry/data weighting**.

W110's six complete actual-model controls demonstrate the distinction. Move three
angle/plane/parallelity terms from native containers into the exact W109 additive
subset without changing their scoring or shell exclusions:

| Source | Native/additive terms | Actual native count | Normalized target | Raw target |
| --- | --- | --- | --- | --- |
| Healthy, full core | 107 / 17 | 11,379 | 0.6766157544 | 7699.210669570105 |
| Healthy, partial pair | 104 / 20 | 11,376 | 0.6767941868 | 7699.210669570104 |
| Displaced, full core | 107 / 17 | 11,253 | 1.0361900218 | 11660.246315243341 |
| Displaced, partial pair | 104 / 20 | 11,250 | 1.0364663391 | 11660.246315243337 |

Select-all reproduces both partial cases. Raw gradients agree within 1.14e-13;
normalized targets shift **0.02637% / 0.02667%**, exactly following the denominator
ratio. This is small in these controls, but implementation placement must not
silently choose relative geometry/data weight. Earlier unnormalized W100 trials
and W109 raw-force checks are unaffected. No production normalization change is made.

`N_native + N_additive` gives a provider-invariant candidate count for these exact
supported controls (11,396 / 11,270). That is arithmetic evidence, **not a qualified
counting implementation or general rule for all native terms**. Do not invent
counts from inventory rows or multiply an already normalized target blindly.
Trace actual native force-count semantics, special images, active families and
other model-level contributions before adopting a policy. Competing custom or
metal terms must remain with their existing explicit owners.

The native geometry API exposes `extension_obj.energies_add(energies_obj=self)`
before finalization, but the ordinary mmtbx manager does **not** forward
`extension_objects`. A counted contribution therefore requires an explicitly
qualified seam in the existing frozen runtime; setting a new manager attribute or
passing a callback alone is insufficient. Compare this route with an explicit
model-level normalization policy before choosing the smallest owner extension.
Do not widen the configured-callback admission proposal into an unreviewed extension
object bypass. Bind and test the actual denominator and force scaling at the model
entry; preserve default behavior and report the policy in any future frozen phase.

Retain current periodic repulsion explicitly in the first bounded qualification.
Coverage success does not authorize editing shell exclusions. Later ordinary-pair-
equivalent periodic exclusions need their own identity-image and periodic controls,
including directed multiplicity, complete energy/force/count observations and
neighbor rebuilds. Do not infer covalent stitching or add a symmetry phosphate
bond alone; continuation intent preserves P/OP1/OP2 until surrounding chemistry is
qualified. Custom metal/stack recipes retain their existing owners and hypotheses.

W72/W73 already record actual-model accumulation and preseeded-buffer arithmetic;
reuse those [12-case](#w72--evaluate-complete-geometry-in-a-retained-reference-frame)
and [36-case](#w73--retain-complete-frame-bindings-through-explicit-reindexing)
receipts as context. They do not establish active-owner admission; new controls
should exercise the missing owner boundary rather than repeat old arithmetic.

### Acceptance sequence before ordinary refinement

1. **Owner admission:** callback-free old records/readers remain exact. Active
   snapshots traverse the same complete policy without mutation. Wrong callable,
   source/helper/profile, context or invocation mode refuses; no fallback.
2. **Direct actual-manager calls:** energy-only and native-owned gradient modes,
   exact zero-callback preservation, provider-invariant model-level weighting under
   the explicitly chosen policy, selected+complement accounting, ordinary and
   partially covered pairs, native normalization and independently recomputed
   directional derivatives. Inject policy/exclusion/term changes both before
   entry and during the callback; restoration must work on success and exception.
3. **Lifetime:** fresh manager, select-all, explicit full permutation, neighbor
   rebuild, source-reinterpretation and copied-manager controls. Show which routes
   rebind and which refuse. Deliberate dropped/duplicated callbacks, skipped or
   repeated calls, stale selection, unknown/partial identities, recursive entry,
   foreign/aliased buffers and changed flags/normalization must not pass silently.
4. **Existing frozen execution:** stage through `refinement_parallelity.prepare_execution`,
   its isolated zero-cycle preflight, `cif_refinement_runtime` and final-writer
   observations. First an isolated geometry/one-cycle qualification, then matched
   real-data candidate/control rounds; never create another refinement runner.
   Reopen installed requests after relocation with original paths unavailable;
   helper tampering, resume without required runtime and missing final evidence
   must refuse. Preserve old checkpoint readers and opt-in/default behavior.
5. **Science:** same observations, Free-R, phase policy, budget and map provenance;
   geometry/packing and healthy/wrong-connection controls, then density calibration
   and B09. Numerical force agreement alone does not close S05/S06 or authorize
   campaign adoption, changed ASU output or publication.

The first deliverable is owner admission plus direct-call evidence, not all five
steps at once. Exact numerical tolerances should reuse Cedar's established
objective reviewer and be frozen before each control. This proposal grants no
new runtime behavior, input/output schema or approval.


### Counted-owner implementation slice — W112 follow-on proposal

After W111, the first implementation candidate is the **counted extension route**,
not a configured residual-only callback. The earlier configured-callback paragraph
records the admission problem but is not a competing implementation queue. Keep
`geo.external_energy_function` and the per-call callback empty in this slice.
Use one trusted owner to forward exactly one native `energies_add` contribution;
ordinary refinement still waits for the separate frozen-execution qualification.

**Smallest Cedar API:** one opt-in context-managed admission owner plus its active
policy check, implemented alongside the existing live-policy machinery. Final names
belong to Cedar. The owner binds one actual model/restraints/geometry object triple,
one frozen contribution contract, one freshly constructed process-local evaluator,
and exact native/helper/profile sources. The active checker must share C331's
complete `_Reader` traversal while retaining a distinct policy identifier and
truthful invocation record. Legacy C331 signatures, results and refusals stay exact.
A serialized contract cannot authorize an arbitrary supplied callable.

For the first direct-call qualification, scope the temporary adapters to the
**instance** `mmtbx.restraints.manager.energies_sites` and its geometry instance's
`energies_sites`. Preserve the original class implementations and call them exactly
once. The outer wrapper checks the real call and opens a one-shot invocation state;
the inner wrapper may forward the frozen counted extension only within that state.
Do not install a global factory hook, copy the native energy implementation, or
introduce a separate refinement runner. Unsupported class/instance overrides and
pre-existing adapters refuse before installation. A copied or selected manager has
no admission; explicit preparation/rebinding is required before it can contribute.

The inspected Phenix 2.2.1-6174 outer method allocates `scitbx.restraints.energies`
with `gradients=None`, passes `result.gradients` to its geometry call, aggregates
`result.geometry`, then normalizes once. Its optional AFITT and Cartesian-NCS paths
are outside the first profile. Admission binds their absence, exact method/factory
bindings and source hashes. Reuse the existing bounded native-objective scope:
reference/NCS-dihedral, DEN and Ramachandran auxiliary managers and nonempty
reference-coordinate proxies are not newly admitted merely because C331's
nonbonded traversal passes. That reader is not a complete all-force policy.
Reject supplied outer buffers, per-call custom forces,
unknown options and unsupported flags; record the actual normalization mode.
Resolve positional/keyword arguments and documented defaults through the qualified
native signature, rejecting duplicates/unknowns. If incoming flags are `None`,
record that native-default route and its effective flags; do not conceal actual
arguments behind a fabricated invocation. IAS-filtered or otherwise partial atom
arrays are outside the first full-model profile.

**Inner buffer provenance:** a correctly sized `flex.vec3_double` is not proof of
ownership. Require an active matching outer invocation, its same coordinate buffer,
mode and exact trusted native call chain. Record the inner allocation identity and
check on return that it is the *same storage* used by the actual outer result and
its geometry result (`flex.id()`, not just Python wrapper identity). It must not alias
coordinates; energy-only uses `None`. Reject direct inner calls, recursion, a second
inner call, a foreign buffer, mode changes or an unexpected extension. Before adding,
validate finite contribution target/gradients and the frozen supported count; add to
existing gradients without replacing their storage. On return require exactly one
inner call and one extension invocation, correct unnormalized inner result and
complete outer count/normalization. Native neighbor counts can legitimately change
with coordinates; compare the actual per-call pre-addition count plus frozen supported
addition count, not an old absolute total. Outer finalization scales the shared
buffer in place: after return, `result.geometry.gradients` is already normalized
although `result.geometry.target` remains raw. Observe raw arithmetic before that
boundary and do not normalize the shared gradients a second time. No accepted result
may escape a failed check.

The outer geometry family inventory, exclusion policy, source identity and contribution
binding are checked before/after, without temporarily detaching adapters or calling
C331 with pretend idle options. W112 remains a **callback-free preparation/recovery
observer**; do not invoke it during active installation as if it authenticated that
state. Active term observation must use the same inventory semantics through an
explicit active guard boundary. The frozen provider selection cannot be regenerated
to conceal a changed native inventory. Normal coordinate movement is permitted;
new identities, cell/group, source reinterpretation or selected terms need new binding.
The inspected minimizer replaces xray scatterers for coordinate steps and only
synchronizes hierarchy later. Therefore preparation/recovery coordinate agreement
is not an inner-loop requirement: bind the actual incoming force sites and current
scattering order while allowing expected hierarchy-coordinate staleness. Never
synchronize the hierarchy during energy evaluation. The first direct-call scope
and later optimizer/final-writer qualification must state this distinction.

**Lifetime and cleanup:** single-owner access is required. An invocation state lives
only for the outer call; entering again before it closes refuses. A failure poisons
that admission so it cannot be reused. Restore an adapter only while its exact
installed binding is still present; if another owner replaced it, leave that foreign
binding intact, report cleanup failure and preserve the failed attempt. Clean up
other still-owned bindings even when one was replaced. No function address or live
buffer identity is persisted as restart authority. Restart constructs and qualifies
a new owner from the frozen factory and contract.

The first regression/native matrix should protect distinct failures:

| Boundary | Required controls |
| --- | --- |
| Legacy | Existing C331 records and callback/override refusals unchanged |
| Install | Wrong factory/helper/profile/contract, stale manager, pre-existing callback/adapter, AFITT/NCS refuse without mutation |
| Invocation | Direct inner entry, recursion, extra/missing inner or extension calls, foreign/aliased outer or inner buffers, wrong shape/mode/flags refuse |
| Contribution | Full/empty/partial frozen subsets; provider-invariant count and normalized forces; changed selected definitions/exclusions refuse |
| Exit | Normal return, evaluator/native exception, foreign replacement of either adapter; preserve others' bindings and forbid reuse after failure |
| New manager | Select/copy/rebuild do not inherit admission; explicit checked fresh binding or documented refusal |

Reuse W109–W112 arithmetic/state controls where applicable. New native work should
exercise these ownership failures and the actual shared-owner entry, not repeat the
local facade's numerical proof. Only after this scoped slice passes should the
existing prepare/preflight/runtime/final-writer path receive an opt-in frozen
contract. No ordinary-refinement activation or numerical tolerance change is
approved by this proposal.


### W110 validation — 2026-11-17

One complete **Phenix 2.2.1-6174** execution finishes in **59.97 seconds**:
six actual-manager cases, energy-only/gradient and normalization-on/off calls,
twelve duplicate/conflicting-target negative controls, unchanged source atoms,
input/software bytes, exclusions and restored callback/kernel bindings. The
actual-model provider-dependent normalization finding is independently replayed
from saved results. This is a bounded diagnostic; it does not qualify active
C331 checks, automatic callback lifetime, counted production forces or refinement.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w110-provider-normalization/run.py
python3 /private/tmp/willow-w110-provider-normalization/audit.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/audit_topostitch_roadmap.py --check
git diff --check
```

No production code changed after W109, so its full/installed results remain the
software baseline; no redundant full-suite rerun. Native evidence, the exact
source-trace hashes, plan, logs and archive stay local. The roadmap records the
anchored archive checksum. Absolute command paths are historical provenance,
not portable execution references. Native subset correctness and partial-pair
coverage are proven separately from the proposed active guard and weighting policy.


## W111 — Counted contributions through actual model entry

A **local diagnostic adapter**, using the native `energies_add` extension hook,
adds exactly the W109 selected residual, gradients and supported proxy count before
the native result is finalized/aggregated. It forwards that extension through the
existing geometry call to the actual mmtbx model entry. No second compiler or
refinement runner is introduced. This adapter is **not installed product code**:
it temporarily overrides one local geometry method, and C331 correctly refuses
that override. It is evidence for selecting the shared runtime integration point,
not an active-guard bypass or approval of production refinement.

The count is justified here only for the four canonical proxy families whose
ordinary native implementations each count one per proxy. No arbitrary inventory,
new exclusion, custom metal role or covalent continuation is inferred. Both
physical source cases retain their existing periodic repulsion.

| Source | Full-core / partial native counts | Additive counts | Actual complete count | Normalized target |
| --- | --- | --- | --- | --- |
| Healthy | 11,379 / 11,376 | 17 / 20 | 11,396 for both | 0.675606411861 |
| Displaced | 11,253 / 11,250 | 17 / 20 | 11,270 for both | 1.034627002240 |

All **six actual-model cases**, including both partial managers after select-all,
now reproduce the same normalized target and complete gradients across providers.
Maximum target difference is **4.44e-16**, gradient difference **1.39e-17**. Four
**20/20 directional checks (648 evaluations)** pass. Empty subsets exactly preserve
native target/gradients/count; energy-only and normalization-on/off calls agree.
Eighteen negatives include six deliberate C331 refusals of the local adapter.
The final complete **Phenix 2.2.1-6174** execution takes **212.27 seconds**; independent
saved-result review reproduces the findings. This qualifies bounded arithmetic,
not automatic lifecycle, normalization for every force family or scientific repair.

### Exact restoration and retained attempts

Attempt 1 stops at the harness type check: `gr.energies` is a module; the native
result class is `gr.energies.energies`. Attempt 2 passes its first derivative case
but fails exact post-probe restoration. Both attempts remain FAILED and retained.

Two isolated controls show why: `model.set_sites_cart` restores hierarchy Cartesian
coordinates exactly but recalculates fractional scattering coordinates. Actual
model energy reads `_xray_structure.sites_cart()`, while W106's `points_sha256`
records the hierarchy sites. In the isolated unchanged-coordinate round trip,
force sites differ by **7.11e-15 Å**, target by **6.66e-16**, gradients by **2.31e-14**;
coverage declarations remain exact. This is numerical representation roundoff,
not a physical deformation. Restoring **both** original hierarchy sites and original
fractional scattering sites recovers target, gradients, force sites and observations
exactly. Attempt 3 uses that restoration and passes with unchanged tolerances.
Future active/source/writer contracts must distinguish these two representations;
a hierarchy-coordinate hash alone does not authenticate the native force sites.

Principal native commands (local historical paths):

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w111-counted-contribution/run.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w111-counted-contribution/run-v2.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w111-counted-contribution/run-roundtrip.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w111-counted-contribution/run-roundtrip-v2.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w111-counted-contribution/run-v3.py
/private/tmp/willow-w109-selected-forces/install/env/bin/python /private/tmp/willow-w111-counted-contribution/audit.py
```

No production code changed after W109; its full/installed validation remains the
baseline. Roadmap generation/check, documentation links and `git diff --check`
cover this update. All native data, failed attempts, scripts and execution records
stay in the local checksum-indexed archive referenced by the machine roadmap;
they are forensic evidence, not an independently portable refinement campaign.

**Next:** Cedar-owned admission for the counted contribution and authenticated
native-owned buffer, then source/dual-coordinate/policy lifetime through the existing
frozen execution and final writer. Preserve callback-free C331 and old readers.
Provider-invariant arithmetic is a gate passed in these controls; owner admission,
ordinary refinement, exclusions, density and B09 remain open. Do not replay W111
merely because the production adapter is still absent.


## W112 — Bind both hierarchy and scattering coordinates

`observe_native_pair_terms` accepts optional `state_owner` and
`expected_state_owner_sha256` together. The caller supplies the trusted, frozen
Cedar `cif_refinement_output` owner; Willow reuses its `_hierarchy`, `_scattering`
and representation-agreement check. It never calls its synchronization or writer.
The owner source digest and `native-refinement-output-state-v1` policy are required.
The existing callback-free C331 policy check remains unchanged.

Without those options, the complete **v1 result remains unchanged**. Opting in
returns `topostitch-native-pair-observation-v2` with a compact `native_state` record
(`topostitch-dual-native-state-v1`): owner policy/digest, atom count, and separate
`hierarchy_sha256`, `scattering_sha256`, `fractional_sites_sha256` and
`force_sites_sha256`. The original `points_sha256` continues to identify hierarchy
coordinates. V2 reads bond-cache terms at the actual scattering-derived force sites.
Existing provider declarations and their context are unchanged.

The observer checks exact native model/scattering types, atom counts and order,
geometry/scattering cell and group agreement, finite complete coordinates, and
non-ADP state agreement using Cedar's existing 1e-8 representation tolerance.
Hierarchy and scattering ADPs may differ; both are hashed separately and neither
is overwritten. Before/after state reads and scattering-object identity detect
changes during inventory observation. They are **not** concurrent-access protection,
source authenticity, active contribution admission or a final-writer qualification.
The caller still owns trusted helper loading, source provenance and single-owner
access. An observation may refresh native neighbor caches but evaluates no forces.

### W112 validation — 2026-11-17

Seventeen new regressions fail before the patch. The focused observer/coverage
set passes **105 tests**; the full suite passes **1,981 +229 subtests** in 106.97s.
A fresh sdist→relocated wheel with source stages removed passes **274 installed
checks**, six CLI helps, `pip check`, lean import and Python 3.10 syntax. Existing
captured-worker bytes are unchanged; no dependency, CLI or checkpoint migration.

A complete **Phenix 2.2.1-6174** execution takes **53.46 seconds**. Six cases cover
healthy/displaced sources, select-all and deliberately stale hierarchy ADPs.
Default observations equal the separately installed W106 implementation exactly;
model target, full gradients and restraint count remain exact. Four no-motion
`set_sites_cart` round trips leave the v1 hierarchy fingerprint unchanged but alter
all three scattering/fractional/force fingerprints. Restoring original fractional
sites recovers the complete observation and native result exactly. Twelve negative
controls refuse missing/wrong owner, label/occupancy/position mismatches and
fractional drift during inventory reading. Independent saved-result audit passes.
These are observation controls, not refinement, bending or density acceptance.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest tests/test_topostitch_native_coverage.py tests/test_topostitch_pair_coverage.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w112-dual-state/install-check.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w112-dual-state/run.py
/private/tmp/willow-w112-dual-state/install/env/bin/python /private/tmp/willow-w112-dual-state/audit.py
```

Exact local scripts, plans, logs, inputs and wheel are retained in the checksum-indexed
archive referenced by the roadmap, excluded from Git. Absolute command paths are
historical provenance; this archive is not a portable campaign. A preliminary
focused-test invocation named a nonexistent test module and ran no tests; corrected
commands above provide the results. A non-escalated focused run emitted only pytest
cache-write warnings; complete and installed runs use disabled cache writing.
Next is the existing W110/W111 Cedar-owned admission/lifetime gate, not another
coordinate observer or arithmetic probe.


## W113 — Freeze the selected-pair contribution factory

`NativePairContribution` lives in `topostitch_native_recipe`; it accepts exact
packet/model bytes, their expected recipe/compiled-binding digests, an existing
W108 `provider_selection` with its independently retained digest, admitted
`native_terms`/`current_context`, and the trusted Cedar correction module. It
constructs a **fresh** `NativePairRecipe`, exports its W105 declarations and
reproduces the existing W104 coverage review. It never replans native ownership.

- `revalidate(native_terms, current_context=...)` rechecks current compiled
  definitions and frozen coverage against newly supplied native observations.
- `evaluate(points, atom_identities=..., compute_gradients=...)` delegates to
  unchanged `evaluate_terms`. It enforces exact boolean mode, atom ordering,
  finite target and full ordered finite gradients (`None` for energy-only).
  Results retain existing fields and add `supported_count`, `count_policy` and
  `provider_selection_sha256`.
- `binding_report()` returns detached existing compiled/provider records and
  count metadata. Caller edits cannot retarget the retained packet/selection.

`canonical-pair-one-per-proxy-v1` counts only selected validated bond, angle,
planarity and parallelity proxies. It is not a generic count for arbitrary forces.
Empty subsets still authenticate the complete compiled/frozen bindings and return
zero energy/count/gradients. The class observes no manager on its own: Cedar must
call `revalidate` at admitted entry/exit boundaries. Neither evaluation nor a
saved report grants active-owner, normalization or scientific authority.

`CONTRIBUTION_SOURCE_MODULES` exposes the exact eight Python helper names for
Cedar's existing frozen loader. Cedar authenticates the actual dependency modules,
correction/native sources and runtime methods, and constructs the exact trusted
factory class itself. There is no arbitrary evaluator argument, second loader,
new persistent artifact schema, correction installer, callback or force activation.
The [counted-owner proposal](#counted-owner-implementation-slice--w112-follow-on-proposal)
was reviewed with Rowan; C367 factors the existing policy traversal while preserving
C331. Active direct-call admission/lifetime is the next Cedar-owned slice.

### W113 validation — 2026-11-17

Nineteen new regression cases fail before implementation. **153 focused tests,
2,000 full tests +229 subtests** pass (full:107.41s). The full run precedes only the
exported tuple's agreed naming change; the final fresh relocated installation and
native execution use the final source. **293 installed checks**, six CLI helps,
pip check, lean import and Python3.10 syntax pass. AST comparison proves all prior
public classes/functions in this module unchanged; captured-worker bytes also match.

Eight complete **Phenix 2.2.1-6174** cases pass in **87.59s** on two retained sources:
full-core, partially covered individual pair, select-all, and core-only packets
prepared through the existing recipe API with zero additions. Supported counts are
17/20/20/0 respectively. All sixteen energy-only/gradient outputs exactly match the
existing subset evaluator; native model energy/full gradients/count and both
coordinate representations remain unchanged. Sixteen negatives reject changed
native inventory/context, nonboolean mode and compiled drift, including empty
subsets. The existing outer `ParallelityKernel` binding is preserved/restored;
the factory installs nothing. Independent saved-result/source audit passes.
No extra derivative panel is claimed: scoring/pullback code is unchanged and this
slice checks fresh construction, frozen ownership and exact numerical reuse.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest tests/test_topostitch_pair_coverage.py tests/test_topostitch_native_coverage.py tests/test_topostitch_recipe.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w113-composition/install-check-final.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w113-composition/native/run.py
/private/tmp/willow-w113-composition/install-final/env/bin/python /private/tmp/willow-w113-composition/audit-factory.py
```

The verified local forensic archive contains factory/native inputs, scripts,
logs and draft/final wheels. It excludes the independently running full-source
composition baseline and is not a portable campaign. No scientific payload is
committed. That separate baseline pins W112/C366 and cannot qualify W113 or C367;
its outcome must be audited separately. No ordinary refinement or scientific
repair is enabled by this factory.


## W114 — Qualify the shared counted-owner lifetime

The W113 numerical factory now passes direct actual-model calls through Cedar's
separate C368 `CountedContributionOwner`. This is cross-branch qualification of a
frozen Cedar wheel and the installed Willow factory, not a branch merge or ordinary
refinement activation. No Willow runtime/API/schema changes are made in W114.

One complete **Phenix 2.2.1-6174** diagnostic finishes in **302.62 seconds**:
**eight cases, sixteen fresh owners/compilers and twenty-eight model calls**.
Healthy and displaced sources each cover full native core, an actual all-native
core packet with zero additions, three terms moved to the additive provider, and
explicit select-all rebinding. Energy-only and native-owned gradients pass.

| Source | Complete count, both providers | Normalized target | Largest target difference | Largest gradient-component difference |
| --- | ---: | ---: | ---: | ---: |
| Healthy | 11,396 | 0.6756064118611885 | 1.11e-16 | 1.39e-17 |
| Displaced | 11,270 | 1.0346270022398707 | 4.44e-16 | 1.39e-17 |

Changing the additive subset from 17 to 20 preserves the complete count and
weighting within the existing W111 tolerances. Both zero-addition cases reproduce
the native result exactly. Two scattering-only coordinate shifts leave hierarchy
positions unchanged while the owner binds the actual force sites. Restoring the
original fractional coordinates restores full state and native results exactly.
Every owner closes cleanly; fresh restart reconstructs the evaluator and repeats
the result exactly. Default flags, cache mode, count and single normalization are
recorded. No optimizer, diffraction refinement, new derivative panel, exclusion
change or scientifically accepted repair is claimed.

**Exact code/package pins:** Willow code `3f5806106bdb233e648ad3c8442d878998c846da`,
factory SHA256 `1739b2a7cf11d802bfa9293d7b79b9edcf7bb1ad868b53d4c1b1996b461d7748`;
Cedar owner SHA256 `772fe23b3075414c355903d35f976dc8667292a576e64f7a68d222cf1a76d34b`,
wheel SHA256 `409d3a963c90f4851bfc52860fa2aea03121e3330f4ccbf942ca3cdb9af47f1a`.
Rowan separately reports **155 focused and 155 relocated-installed tests and 32
native controls** for that owner. Those admission/failure controls are not counted
as Linden's eight lifecycle cases. W109/W111 retain derivative/arithmetic scope.

Historical diagnostic root: `/private/tmp/willow-w114-owner-lifecycle/`.
Exact controller command:
`/private/tmp/willow-w94-pivot/env/bin/python -B /private/tmp/willow-w114-owner-lifecycle/run.py`.
It owns the native command `phenix.python -B probe.py` with a 900-second limit.
`audit.py` independently checks saved outputs and source/input pins. Its first
version incorrectly expected the build suffix in the reported semantic version;
the correction binds reported `2.2.1` plus the exact qualified `6174` source profile.
The native attempt passed once and was not rerun. No process remains active.

The verified **local-only** archive is anchored at the everyday NASolve checkout:
`branch-artifacts/willow/w114-counted-lifecycle-2026-11-17.tar.gz`, SHA256
`e95c27b092fecf326f5d7ee69c2ad077eac66025b8cd9b385ac6e542ead7310c`
(2,400,859 bytes; 27 indexed files). It preserves private inputs, both exact wheels,
scripts, results, logs and source-review evidence. Generated data is excluded from
Git. This is forensic evidence, not a claim of portable campaign execution.

### Separate full-source compatibility baseline

The full unfiltered SOURCE suite of a temporary W112/C366 composition passes:
**12,138 tests, 284 subtests, one skipped module, 2,982.99 seconds**. The skipped
module explicitly requires opt-in execution in pinned Phenix; this ordinary
Python run is not native API qualification. The source remains clean afterward.

Pins: Willow `e005b0da4fbaf793bab9a7f1de88558c1c462220`, Cedar
`09303e803d64737bfa7ff89975fea96967372204`, NARestraints
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`; resolved temporary tree
`b1d09eaf21c431bb6cce348f181a1010e2b46111`. There are no source, test or script
conflicts. Only package resources were explicitly unioned. Eight documentation
conflicts remain for actual integration; no branch/index merge occurred.

From historical `/private/tmp/willow-w113-composition/source`, the exact command was
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:../narestraints /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider`.
The controller supplies equivalent absolute anchored paths and caps native thread
counts at one. `full-execution.json` retains ownership and timing; `full-audit.json`
checks the completed result. This is a full **source** baseline, not a complete
installed suite and not qualification of newer W113/C367/C368. Earlier W81
installed-context failures remain preserved rather than retroactively relabelled.

Verified local archive at the everyday NASolve checkout:
`branch-artifacts/willow/w114-source-compatibility-2026-11-17.tar.gz`, SHA256
`88b7d967d663aafba0ff8c33bffd14b1e0e899dbd07684873998da4172468ff8`
(20,636,466 bytes; 12 indexed files). It includes both source snapshots and receipts;
the temporary Git alternates are not a portable execution claim. No generated
scientific data or archive is committed.

### Next ordinary-runtime gate

Static review of exact Phenix/Cedar sources identifies concrete consumers to
qualify next; it does not implement a hook:

- The existing refinement runtime wraps `ParallelityKernel` to record usage.
  C368 intentionally accepts the exact kernel, so that observed wrapper still
  refuses. Qualify the existing observation owner; do not bypass it or add an installer.
- Preprocessing rebuilds restraints and can change nonbonded weight with resolution,
  then modifies other model state. Bind the actual prepared manager and frozen
  provider/policy contract at the correct boundary, not merely the input file.
- Coordinate-dependent target updates, local restraint scaling, solvent changes and
  model replacement require explicit scope or a separately frozen phase. Do not
  reselect providers to conceal drift. Direct inner calls remain unsupported.
- Native statistics often use selected copies, which drop instance admission, and
  assert a decomposition into named native-family residuals. Keep native-family
  statistics separate from added-pair evidence until reporting/weight consumers
  are qualified. A successful copied report does not prove added terms were scored.

Reuse the existing prepare/preflight/runtime/final-writer owners for a bounded
optimizer/one-cycle check, then matched data/Free-R controls. S05/S06 and the B09
physical alignment gate remain open; no density or geometry repair is selected.


## W115 — Observe the actual prepared model

**2026-11-17; diagnostic evidence, no Willow runtime or schema change.** Use the
[roadmap](topostitch-roadmap.md) for the current queue. W115 calls the existing
`prepare_execution` and frozen `run_compatible_refinement` APIs, then inspects
its actual returned preflight model. A diagnostic entry retains that return;
it is not the unchanged normal command-line entry or production admission.
The ordinary preflight reader validates the saved evidence. No added forces,
coordinate optimization, checkpoint registration or structural adoption occurs.

### Exact input lineage and working frame

The current geometry control, historically called `healthy`, is the earlier
small bend preview: model SHA `dbdaac83c67a60c0d3df48ac19f1dbd2ddd2e15307dcb41cce564d560ab23465`.
Its archived source is the deposited reference, SHA
`91db1085ca5ca585655912ca169dde1fb10e6071558c5c03a37fcecd5b0cf247`.
All 855 identities/order and occupancy/isotropic-B fields match; 204 atoms and
ANISOU tensors were transformed, maximum Cartesian displacement 0.178553 Å.
The preview remains unvalidated. Do not substitute the original bytes under its
already-bound recipe.

Static discovery used declared archive indexes and verified three archives plus
20 exact members in memory, without basename search. TopoTrace's declared local
W34 archive supplies `experiment/observations.mtz`, SHA
`f57083bb6d6b74789ba77c0c448c678356f7e3a52805a7142e1b33f9055d86a7`.
Its 3,333 amplitudes/sigmas and 176 original test reflections use labels
`Fobs,SIGFobs`, `FreeR_flag`, test value 0, generation disabled. Exact Miller IDs
and the original flag identity
`104271d1333e6fa01ce6712fd0f9b34a24eb86603541b76f7f91345b73fb918a`
are verified in actual prepared fmodel readback; amplitudes/sigmas agree within
relative tolerance 1e-6. The original MTZ bytes remain unchanged.

Native default preparation takes the MTZ's stored cell: a=b105.54699707031247,
c96.26799774169922 Å, whereas source/recipe has a=b105.547, c96.268 Å.
The maximum difference, 2.93e-6 Å, correctly fails the existing 1e-10 frame join.
The first inspection remains failed. The second completes read-only observation
but explicitly refuses provider selection in that frame. No tolerance is widened.

A separate control declares these native arguments before execution:

```text
refinement.crystal_symmetry.unit_cell=105.547,105.547,96.268,90,90,120
refinement.crystal_symmetry.space_group=R 3 :H
```

Its actual prepared cell matches within 2.84e-14, with unchanged original data
and flags. This is an explicit working-frame choice for the diagnostic, not an
automatic source-cell preference for campaigns. A production route must choose
and freeze its working model/data frame before accepting compiled periodic
images; changing cell parameters or recompiling images requires explicit lineage.

### Native result and installed shared reader

All runs use **Phenix 2.2.1-6174**, complete native **zero-cycle dry-run
preflight**, nproc1, seed2679941, individual-sites-only intent and declared
`fix_wxc=1`, `wc=1`. The weight is a fixed lifecycle control, not a tuned scientific
choice. No optimizer runs. Each preflight makes two energy-only corrected plane
calls, zero gradient calls, and one deduplicated usage record.

| Attempt | Result | Owned wall time |
| --- | --- | --- |
| 1 | Native preflight completes; diagnostic fails source-frame assertion | 6.29 s |
| 2 | Full read-only observation; default-frame provider selection refused | 7.74 s |
| 3 | Explicit working-frame observation and initial provider selection pass | 8.66 s |
| 4 | Installed C371 read-only assembly exactly reproduces attempt 3 records | 11.12 s |

The last three preserve all 855 ordered atoms and anisotropic scatterers, with
no hierarchy/scattering ADP disagreement. Explicit-frame Cartesian roundtrip
movement is at most 1.59e-14 Å. The actual supported-family native inventory is
2,572 proxies; 124 requested pair terms divide into **107 native and 17 missing**.
The missing terms are selected as declarations only. Native owners/methods,
source files, inputs, kernel and prepared state remain unchanged.

Attempt 4 uses `observe_prepared_pair_contribution` from the installed C371
candidate. It returns the existing policy, compiled binding, dual-state
observation and provider selection; no new durable schema or full-state duplicate.
Its observation/selection exactly match independent attempt 3, and compiled
binding SHA is `382f5618e4b332a192011dd59c2df9689de5d08c224669c2fa3b0ddc22ebaeef`.
The ordinary saved preflight reader and independent saved-evidence audit pass.
Preflight R statistics are not an improvement result or a repair-selection gate.

### Pins, commands and retained evidence

Willow numerical code remains W113 `3f5806106bdb233e648ad3c8442d878998c846da`.
Attempts 1–3 use the frozen C368 wheel already recorded in W114. Attempt 4 uses
C371 wheel SHA `6d87257cb9a02fabe8b0efecb1a37b17ef8e7a5489d18da344688b8f34ed6119`,
counted helper SHA `2504e4718b7538ac96d36a0f65c120aa695010dbdc0d51bc5605226a6ee44918`.
All retain exact v3 runtime SHA
`6698585c1da6225895dd1d639554321ccab695eda1b4366d243deb39106c3503`.
No actual branch merge, full-suite repeat or new Willow installation is claimed.
Rowan separately qualifies C371 source/installed/native behavior.

Historical local commands, with exact native argv, qualified source hashes,
process identities and input references retained in their plans:

```text
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w115-prepared-state/run.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w115-prepared-state/run-observe.py plan-2.json
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w115-prepared-state/run-observe.py plan-3.json
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w115-prepared-state/run-c371.py plan-4.json
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w115-prepared-state/audit.py
```

Repository anchor **everyday NASolve checkout**, local forensic archive
`branch-artifacts/willow/w115-prepared-state-2026-11-17.tar.gz`, SHA
`d877caa3ad7a82c930b3952dd6ed14aaeac7f22c511bed78ce8b1c32e450d13d`:
5,152,349 bytes, 114 indexed files verified after writing. It retains all attempts,
plans, scripts, original input bytes, runtime receipts and exact software wheels.
Scientific inputs/results stay out of Git. It is not a portable resumable campaign;
archived diagnostic workers are evidence, not execution authority.

Next: immutable prepared admission, then a bounded fixed-weight ordinary lifecycle
through the existing driver and final writer. Native-only/zero-addition equality
and the full recipe are distinct controls; the latter changes requested chemistry.
Reporting copies, broader target/weight phases, exclusions and scientific
stitch/density acceptance remain open. S05/S06 remain **PARTIAL**.


## W116 — Qualify one bounded ordinary refinement cycle

**2026-11-17; actual native execution, diagnostic integration only.** Three
separate ordinary zero-cycle preflights precede three complete coordinate
refinements under **Phenix 2.2.1-6174**. Each uses one macrocycle, 10 iterations,
12 function evaluations, nproc1, seed2679941, fixed effective X-ray weight1 and
geometry weight1. Automatic weight optimization/shaking, ADP/occupancy refinement,
solvent/ion changes, bulk-solvent reoptimization and restraint target updates are
disabled. No endpoint is adopted and no production runtime/default/schema changes.

### What is joined and checked

The existing execution/process owners freeze inputs and v3 runtime. The installed
C371 helper assembles the initial records on the actual returned preflight model.
The controller validates preflight before sealing its existing records, input and
request/source references. The actual phase receives the seal checksum; it never
calls the provider planner again. At module-level native `driver.run`, it verifies
the actual prepared observation against the sealed one before binding the owner.
The same prepared model remains owned through the optimizer and native final
writer. A diagnostic observer calls the original `run_lbfgs` exactly once and
records actual effective weights and iteration counts; it changes no arithmetic.

This entry is a local diagnostic, not the production CLI or durable admission
schema. Exact native methods/files are pinned. Binding checks happen **before**
historical cleanup as well as after return, so restored booleans alone are not
used as evidence of exclusivity. No competing-hook fault is injected here;
foreign-replacement cleanup remains a separately versioned Cedar qualification.
All source data, input bytes and software remain unchanged.

### Controls and result

| Sibling | Requested terms | Added by owner | Refine time | Rwork / Rfree |
| --- | --- | --- | --- | --- |
| Native core | 107 core terms | Owner absent | 12.10 s | .22451965 / .25989801 |
| Zero addition | Same 107 core terms | 0 | 78.14 s | .22451965 / .25989801 |
| Full recipe | 124 terms | 17 | 83.21 s | .22452413 / .25991557 |

Native core and zero addition give **exactly identical** complete hierarchy,
scattering, fractional/force coordinates, R statistics, optimizer counts and final
geometry target/count/normalization. Their final model count is 11,379. Both active
owner cases complete 16 checked model calls and close unpoisoned; full coverage
counts 11,379 native +17 added =11,396. The existing usage wrapper remains owned.

The full-recipe endpoint differs from native core by maximum0.033571 Å and
RMS0.002797 Å, demonstrating that the additional forces participate in ordinary
coordinate refinement. It is a different requested objective, not a numerical
identity comparison. **No diffraction improvement is shown**: common preflight
Rwork/Rfree are .22364321/.25919212, and both short fixed-weight runs worsen them
slightly. These are lifecycle controls, not a ranking, optimized scientific weight
choice or repaired structure. The original 3,333 observations, exact Miller set,
176 Free-R selections, occupancy and anisotropic scattering remain intact.

The actual writer's bound hierarchy/scattering/Fcalc observations match final
saved state. Final PDB atom identities/order and expected coordinate rounding
also pass independent readback. Native-family PDB/.geo statistics omit the added
terms; separate counted-score evidence is retained. Existing Willow W35 parsing
reads overall native-family bond/angle RMSDs .025 Å/2.104° in all three rounded
PDB summaries. The unmerged standalone Cedar parser lacks that fallback and
returns absent RMSDs; both readouts are retained, with no duplicate parser patch.

The zero-addition actual refinement is **6.46×** the native baseline in this
small control. Record this as overhead to investigate, not a reason to remove
checks. Rowan's separate single-call profile identifies repeated pure exact
relative-image arithmetic. Optimize only a measured, bounded operation while
preserving results and refusals; do not rerun these siblings just for profiling.

### Reproducibility and limits

Inputs retain W115's declared derived-model/W34 observation lineage and explicit
working crystal. Both core-only siblings use the same existing native-core recipe
subset; full coverage uses the original full recipe. All use the same native core
PHIL, coordinate model, data, Free-R and protocol. W116 deliberately fixes the
weights before seeing its R statistics and performs no outcome-driven retries.

Willow source stays W113 `3f5806106bdb233e648ad3c8442d878998c846da`;
Cedar is the exact copied C371 candidate wheel
`6d87257cb9a02fabe8b0efecb1a37b17ef8e7a5489d18da344688b8f34ed6119`.
The native runtime remains v3 SHA
`6698585c1da6225895dd1d639554321ccab695eda1b4366d243deb39106c3503`.
The Willow factory is supplied by a separate qualified installation; it is not
already in the Cedar wheel. Production needs a qualified coordinated package join
or an explicit maintained dependency, not another vendored recipe implementation.
Cedar C372 or later runtime changes are not silently included. Exact prepared
records, native command arguments, source pins, phase receipts, process identities,
full endpoint state and original writer output are retained. Current ordinary
`finish_execution`/`validate_execution` and independent saved-evidence audit pass.

Historical diagnostic commands:

```text
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w116-ordinary-cycle/run.py native_core
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w116-ordinary-cycle/run.py zero_added
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w116-ordinary-cycle/run.py full_added
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w116-ordinary-cycle/audit.py
```

The latter siblings require earlier controls to pass; the full case additionally
requires exact native/zero endpoint agreement. All six native phases are stopped.
No new Willow production-code tests/full suite/install are implied by this
docs-only checkpoint; preceding source/install and derivative gates retain their
own pins. No data or generated coordinate outputs are committed.

Repository anchor **everyday NASolve checkout**, forensic archive
`branch-artifacts/willow/w116-ordinary-cycle-2026-11-17.tar.gz`, SHA
`74867d382d806662f6469cf2318371425ade5c834f99fda68b4476748d4e15a3`:
5,259,129 bytes, 123 indexed files verified. This preserves diagnostic evidence,
not a portable resumable campaign or permission to execute archived workers.

Next is **immutable production admission through the existing execution owner**,
plus the measured pure-helper performance work. Broader weights/phases, exclusions,
physical sticky-end closure, calibrated density evidence and B09 remain open.
S05/S06 remain **PARTIAL**.


## W117 — Cancel identical validated images without repeated matrix products

**2026-11-17; code, installed-package and actual native checks.** The private
coverage canonicalizer now returns exact identity when two already validated
full image operations are equal. All proper-rotation, rational-translation,
denominator and arithmetic-budget validation remains upstream and unchanged.
Distinct images still use the existing exact operation, preserving unwrapped
lattice shifts. There is no cache, new state, relaxed tolerance, public API,
schema, dependency, physical target or activation change. Existing captured-worker
bytes remain unchanged; historical readers need no migration.

### Validation and measured effect

- Nine regression cases cover common identity/screw/centering images across all
  four term families, mixed noncommuting images with full lattice translation,
  invalid equal images and distinct-image arithmetic budgets. Four fail before
  the patch; the other five preserve existing refusal behavior.
- **223 focused, 2,009 complete-source tests +229 subtests**, and **302 installed
  tests** pass. The initial sandbox full run retains five campaign-process
  failures caused by denied `/bin/ps` access. One complete rerun with process
  inspection allowed passes; no source change was needed for those failures.
- A relocated sdist builds a wheel; original staging and extracted source are
  removed before fresh-environment installed checks. Six CLI helps, pip check,
  lean import and Python 3.10 syntax pass. NARestraints resolves to
  `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691` (`v1.1.3`).
- The saved W116 native inventory contains 2,572 terms and previously repeated
  26,415 equal-image matrix products. These become zero, with exact inventory
  equality; the isolated check takes 0.395 versus 0.101 seconds. This is a pure
  saved-record benchmark, not native refinement.
- Rowan's **C373 / Phenix 2.2.1-6174** complete native direct-call control takes
  **4.6208 versus 1.5670 seconds** for the same model and terms. Full targets,
  gradients, counts, normalization, call statistics and initial prepared provider
  selection/binding match exactly. Native count11,379 plus17 additions remains
  11,396. Changed torsion inventory and native policy still refuse, poison the
  owner and prevent reuse. Native state restores, source files remain unchanged
  and the process is verified stopped. This does not measure whole-refinement
  speed, change W116's historical timing or demonstrate a successful repair.

Exact source validation commands (from the Willow checkout):

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_coverage.py tests/test_topostitch_native_coverage.py tests/test_topostitch_packing.py tests/test_topostitch_native_seams.py tests/test_topostitch_recipe.py
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w117-identity/install-check.py
python3 /private/tmp/willow-w117-identity/audit.py
```

These paths record historical validation, not operational dependencies. The
indexed local archive preserves scripts, exact commands/logs including failed
runs, source patch, package artifacts, dependency versions and C373 summary plus
stopped/source receipt. Repository anchor **everyday NASolve checkout**:
`branch-artifacts/willow/w117-exact-image-2026-11-17.tar.gz`, SHA
`4a306751fbb75c61164b3f457bc5fa43cff2fdf3be00f027826970963f256de7`,
1,210,750 bytes, 24 indexed files verified. Full native evidence remains owned by
Cedar's C373 run; the copied summary is not a replacement for that run. Neither
archive is a portable resumable campaign or committed scientific payload.

Installed wheel SHA
`b92d45cde4720fb2f5c9f387e72af0381943bd48b8dea2de98d2b5b2141200f7`;
coverage helper SHA
`e342d7aa4d6277dac0cd4b90d63fe1501c74249927fe909e119680901c21f591`.
Only `topostitch_pair_coverage.py` changes production code, with regressions in
`test_topostitch_pair_coverage.py` and existing human/machine documentation updated.
Coordinated package ownership, immutable production admission, broader native
phases/exclusions and matched scientific repair remain open; S05/S06 stay partial.


## W118 — Rebind frozen pair intent to a compatible child

**2026-11-17; optional data API and complete native compiler check.**
`topostitch_recipe.rebind_pair_recipe(packet, source_model_bytes, model_bytes,
expected_recipe_sha256=..., expected_model_sha256=...)` returns a detached existing
schema-1 packet with **only `source_model_sha256` changed**. It verifies the
original packet/source and destination hashes, ordered identities and conventional
crystal frame. Frozen pair IDs, sites, purposes, full image translations, library
provenance, emitted PHIL, weights and all authority flags remain unchanged.

Coordinates and displacement parameters may change. Element, formal charge,
occupancy, ATOM/HETATM identity and internal same-chain TER breaks may not.
Elements/occupancies/charges must be explicit and valid; missing elements are not
guessed. Equivalent space-group spelling and TER separators between different
chain IDs are accepted, while cell, setting, ordering, chemistry, added/missing
atoms and internal chain-break changes refuse. Existing PDB/CRYST1/SCALE checks
apply; mmCIF, recuts and renamed/reordered descendants are outside this API.
The existing topology extra supplies Gemmi. No NARestraints loading/regeneration,
file I/O, inference, native call or provider selection occurs inside this helper.

This is not a full native packet validator or proof that the destination is the
intended parent. The controller must preserve original intent and checked lineage,
bind the actual parent/input/frame, obtain fresh preflight and freeze its initial
selection. The unchanged native compiler validates the whole resulting packet.
Same-phase consumption must compare its already sealed selection without choosing
again. A read-only validator must never write admission records. If native
preflight succeeds but admission fails, preserve native return code0 plus an
explicit refusal/unlaunched-refinement outcome; do not fabricate native failure.

### Checks and compatibility

- **24 new regressions**, including held-out chemistry/frame refusals and mutation
  of the caller's packet during parsing. The initial 23 cases fail before the API;
  the later detachment regression is included in all final checks.
- **237 focused, 2,033 complete-source tests +229 subtests, 326 installed tests**
  pass. Relocated sdist-to-wheel installation removes original staging/source
  before tests. Six CLI helps, pip check, lean import, Python 3.10 syntax and
  unchanged captured-worker bytes pass. No existing preparation API/schema changes.
- Verified W116 archive replay covers all three saved native endpoints: 855 ordered
  atoms and all 14 pair definitions remain exact apart from the new source digest.
  This replay launches no native tool and does not adopt those endpoints.
- **Phenix 2.2.1-6174**, complete native compiler/direct-evaluator execution in
  1.32 seconds of owned wall time: original recipe/source and rebound recipe/child
  compile identical 124 terms/images, with exact energy-only and complete-gradient
  results at the same child coordinates. Source pins and native kernel remain
  unchanged; process return0 and stopped verification pass. No model owner,
  optimization, diffraction refinement or continued-checkpoint qualification.

Historical commands, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` for source tests:

```text
/private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_recipe.py tests/test_topostitch_pair_coverage.py tests/test_topostitch_native_coverage.py tests/test_topostitch_transport.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w118-rebind/run-full.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w118-rebind/install-check.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w118-rebind/replay.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w118-rebind/run-native.py
python3 /private/tmp/willow-w118-rebind/audit-archive.py
```

Repository anchor **everyday NASolve checkout**, local forensic archive
`branch-artifacts/willow/w118-recipe-rebind-2026-11-17.tar.gz`, SHA
`d02350f6ee8c82a1d9ff34db929bec52287d1314b908761e01b74e5d52c8dae7`:
1,235,612 bytes, 29 indexed files verified. It retains source/patch, package,
tests/logs, exact input-member checksums, rebound packets and native receipts.
Scientific source data remain in the verified W116 archive and are excluded from
Git. This is diagnostic evidence, not a portable/resumable campaign.

Wheel SHA `d1a7319f9a3d7e63d68906974a25d22691d47b61296d9db7f94004dccbdb755d`;
recipe module SHA `73b735197560d8b0e0f0c343b4636fdf9e83b5acffa179aa7586367931293e76`.
Only `topostitch_recipe.py` changes production code; existing recipe tests and
human/machine docs are updated. S05/S06 remain partial. The separate C374 joined
package uses W117/C373 pins and does not cover this new API. Production admission,
descendant retention, broader phases/exclusions and scientific repair remain open.


## W119 — Consume strong preflight state at the real driver boundary

**2026-11-17; genuine native phase-boundary diagnostic, no optimization.**
Installed C375 introduces an explicit stronger prepared capture and a consumer
that reconstructs the existing owner without selecting providers again. The legacy
C371 four-field record alone omits the broad bonded signature and outer restraint
normalization. Its default output stays unchanged; stronger consumption requires
the explicit new baseline. Rowan's source/installed/native tests own that API's
refusal matrix. W119 independently checks its actual ordinary phase boundary.

### Exact scope and outcome

One isolated zero-cycle Phenix 2.2.1-6174 preflight returns the actual prepared
model. The controller validates existing preflight evidence, then explicitly seals
the stronger record, original request and input/source references. A separate
fresh non-dry process reaches module-level native `driver.run`; before invoking
that driver, the installed consumer compares the sealed state and reconstructs
the owner. Entry rechecks the same initial state. No planner runs in consumption.

The source is the existing W116 full-recipe endpoint, rebound by W118 while
preserving original intent/chemistry and all 14 pair definitions. Exact declared
archive members/checksums supply the parent, original recipe/source, core PHIL,
fixed protocol and original data. This is no new benchmark search or weight choice.
The original source/recipe and child bytes remain separately pinned.

**The boundary passes.** Preflight and actual-driver state agree, including broad
torsion/chirality settings, normalization, pair coverage and dual coordinate/ADP
state. One checked energy/full-gradient call uses 11,392 current native terms plus
17 additions =11,409. The native count is freshly observed for this reinput parent;
W116's historical 11,379 is not reused as a fixed denominator. Exactly one inner
call/extension uses the native-owned buffer. All model state and kernel, writer,
driver, optimizer-monitor and monomer-summary bindings restore.

The harness then raises the deliberate `BoundaryObserved` sentinel **before any
optimizer or original driver invocation**. The native runtime truthfully retains
`FAILED` with that exception. The diagnostic is `BOUNDARY_OBSERVED`, not completed
refinement: no final model, ordinary successful execution receipt or usable
checkpoint is written. Both owned processes stop; preflight takes 7.93 seconds and
the driver-boundary process 9.57 seconds. No threshold is relaxed and no refused
state is bypassed.

Both phases retain the same 3,333 observations and 176 original Free-R selections;
their Rwork/Rfree are exactly .2245247483/.2599282849. These initial values are not
an improvement claim. The model is unchanged by the diagnostic call; no repair,
diffraction optimization, repeated sibling panel or scientific adoption occurs.

### Validation, pins and retained evidence

Independent readback revalidates the existing preflight, sealed references,
strong baseline, source/input hashes, owned call counts, original data/Free-R,
intentional native failure, absence of optimizer/final output and stopped processes.
This Willow slice changes documentation only, so no repeat full suite or package
build is implied. W118 source/install and C375's 184 source/184 installed plus
native controls remain separately pinned evidence.

Historical commands:

```text
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w119-phase-prepare.py
python3 /private/tmp/willow-w119-prepared-boundary/build-probe.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w119-prepared-boundary/run.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w119-prepared-boundary/audit.py
```

Willow `c08f337024f8901c583c0988f652e9a1c3156a49`, wheel
`d1a7319f9a3d7e63d68906974a25d22691d47b61296d9db7f94004dccbdb755d`;
Cedar `b058581a2b75e9cab617c1c01eddb5866a0bb382`, wheel
`132abf48b06701154b35c68d755989decf0530c00c3d0e3d4a7eff7a58d9f3b9`.
The runtime is explicit existing v4; helper and native source pins are recorded
separately. This diagnostic uses separately qualified installations, not a new
joined-package or branch-merge claim.

Repository anchor **everyday NASolve checkout**, local forensic archive
`branch-artifacts/willow/w119-prepared-boundary-2026-11-17.tar.gz`, SHA
`1159fdca85917be8f4772f9fab5e2d2836216cdf6e7a7ffad0324f700a37eaad`:
2,377,760 bytes, 43 indexed files verified. Plan SHA
`5e59471ed16ad7747e136aa8b1aefc14aa658c1ea44f1a55a011aecbb62fd6e3`;
sealed preflight SHA `57a6059ba9c0d77dd3441008ab30120c148f3ab627368bfd2cd411a5ee662654`.
Scientific inputs, native records/logs and package artifacts are excluded from Git.
The archive is forensic evidence, not a portable resumable campaign.

Next: existing-controller versioned original-request/preflight/admission/phase
wiring, honest admission-refusal outcomes and descendant intent retention.
Broader phases, periodic exclusions, scientific repair and B09 stay open;
S05/S06 remain partial. C375/W119 do not replace these gates.


## W120 — Replay the complete cycle with stronger prepared ownership

**2026-11-17; complete native execution, one historical-control replay.**
Use the original W116 full-added source, full recipe, core PHIL, observations and
fixed protocol byte-for-byte. This is not W119's rebound endpoint. At installed
W118/C375 pins, a fresh actual zero-cycle preflight returns the stronger complete
baseline; existing preflight validation precedes an immutable local seal. A fresh
actual phase reconstructs the owner from that seal at module-level `driver.run`,
without replanning, then retains the same model through original driver and final
writer. The diagnostic observer records actual native optimizer settings/counts.

The predeclared scope remains one coordinate-only macrocycle, 10 iterations /
12 function evaluations, fixed effective X-ray and geometry weights of 1, seed 2679941,
nproc 1, no automatic weights/shaking, ADP/occupancy refinement, solvent/ion changes
or target updates. There is no new search, weight tuning, sibling ranking or
three-sibling repeat. W116 remains immutable historical evidence at its own pins.

### Exact replay and timing

Independent saved-evidence comparison passes **exactly** for:

- original scientific input bytes and effective controls;
- complete final hierarchy, scattering, fractional and actual-force coordinates;
- written ATOM/HETATM/ANISOU/TER/cell/SCALE records;
- initial/final R statistics, optimizer trace and counted geometry score;
- all owner statistics, including 16 successful calls, 11,379 native +17 additions
  =11,396, normalization, force-site and contribution-binding hashes.

The final Rwork/Rfree remain **.2245241262 / .2599155744**. This repeats W116's
outcome; it does not add diffraction benefit or scientific acceptance. Original
3,333 observations and 176 Free-R selections, non-coordinate scattering and all
source inputs remain unchanged. Writer state/readback and expected PDB coordinate
rounding pass; native-family RMSDs remain .025 Å /2.104° and omit the added terms.
Existing `finish_execution` and `validate_execution(..., usable=True)` pass for
the local ordinary runtime receipt; no campaign checkpoint is selected/published.

Preflight takes **8.01 seconds** and the complete current refinement phase
**37.03 seconds**, versus historical W116 full-recipe **83.21 seconds**. This is
one observed historical/current phase comparison across the qualified helper
updates, not an isolated causal performance benchmark or general speed guarantee.
Both processes are stopped; ownership, kernel/writer/driver and observer bindings
restore. This test does not inject a foreign-hook failure or qualify broader phases.

### Reproducibility and remaining work

Installed source/wheel pins remain exactly W119's W118/C375 pair. The runtime is
explicit existing v4 with separately pinned counted/factory helpers; no production
runtime bytes, default, schema or dependency change is made on Willow. This is
still a local diagnostic hook, not the maintained lifetime/controller integration.
No new Willow source suite or installation is implied by this docs-only result.

Historical commands:

```text
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w120-cycle-prepare.py
python3 /private/tmp/willow-w120-strong-cycle/build-probe.py
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w120-strong-cycle/run.py full_added
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w120-strong-cycle/audit.py
```

Repository anchor **everyday NASolve checkout**, local forensic archive
`branch-artifacts/willow/w120-strong-cycle-2026-11-17.tar.gz`, SHA
`ba41b4488ceebaff82e9a1d0edeca7e4874269bb0c42480c0f1f6338c752ab04`:
3,069,852 bytes, 50 indexed files verified. Plan SHA
`20e151d54936e68093420f32deb1bc3f32c0c193addbb91f93d05f6804e43f02`;
sealed preflight SHA `9d523a626b99b1db1689269be468f6272bfe798c5d87361f3602d0aa96d8dd9d`.
The exact W116 baseline is read only from its declared checked archive members.
Scientific data/results and software artifacts stay local and excluded from Git;
this archive is not a portable resumable campaign.

Next: a maintained driver-lifetime wrapper around unchanged v4, followed by
versioned original-request/preflight/admission/phase records and descendant
intent retention in the existing controller. Preserve honest refusal outcomes
and compact evidence. Broader phases, exclusions, calibrated density, useful
repair and B09 remain open; S05/S06 stay partial.


## W121 — Qualify the current joined installation and maintained lifetime

**2026-11-17; installed software composition, not a branch merge.** Build one
namespace from Willow `dbb5ae249ee087b5b62a218b94429629f8a10b2b` (runtime code W118)
and Cedar `0aaec4bd0b7dc49ffd038a5be578523d9ed1a4f1` (C377). Reuse C374's temporary
merge/package harness. Source and tests have no conflicts; resolve only the
package-data union. Retain the eight documentation conflicts as unresolved:
AGENTS, CHANGELOG, docs README/architecture/campaign-full-auto/collaboration/
construct-registration/development-handoff. No repository branch or default changes.

The offline wheel is installed into a temporary target and relocated; original
build source and initial installation path are removed before verification.
**556 focused tests, zero skips, pass in 25.06 seconds** in the existing Gemmi
0.7.5 environment. All six installed CLI entry points and `pip check` pass.
Independent readback verifies **306 Python/resource files** against qualified
source hashes. The panel covers existing native ownership/runtime/output/sites,
execution readers, counted ownership/new phase helper and current Willow recipe,
coverage, packing, transport and native-term APIs. This is not a new complete
suite or an actual native run of the joined package.

Wheel SHA `1f712477c66eadb06b5dc27d576c4c0c6be930cbcd9cb105126cbd3f495d89b7`.
Exact merge pins, resource hashes, commands, selected tests, CLI logs and harness
are in the local forensic archive under repository anchor **everyday NASolve
checkout**: `branch-artifacts/willow/w121-joined-package-2026-11-17.tar.gz`, SHA
`b63e9549aba3baf18e6e305c24c800bc3b307264df61fdbe08939264fda98802`,
1,771,781 bytes /70 indexed files, all verified. It contains software and committed
fixtures, not generated scientific runs. It stays out of Git and is not a portable
resumable campaign. The qualified relocated package remains available locally.

Historical command:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w121-package.py 0aaec4bd0b7dc49ffd038a5be578523d9ed1a4f1
```

**Separate C377 native evidence:** `PreparedCountedRefinement` now owns the actual
source-qualified module-level driver lifetime around unchanged v4, consuming the
C375 strong seal and preserving the same model through final writing. Its initial
scope is explicitly fixed unit weights, one process, one cycle /at most ten
iterations, all-site XYZ, with changing targets/identities and broader phases
refused. It performs no extra final energy call and preserves original errors and
foreign hooks. Phenix 2.2.1-6174 complete preflight (7.79s) and cycle (34.92s) match
W120's preparation, full endpoint, physical records, optimizer trace and diffraction
exactly; 15 calls replace W120's 16 including the diagnostic final score. All jobs
stop and hooks restore. The two early parameter-representation failures are retained
as stopped preflights; 46 final helper and 230 relocated installed tests pass.
Cedar's machine ledger key is `maintained_prepared_refinement_lifetime_2026_11_17`
at the exact C377 commit. Its native proof uses separate installed packages; do not
relabel it as W121 joined native qualification or scientific acceptance.

Next: durable original intent/preflight/admission/phase outcomes and descendant
retention through existing controller owners. Reuse the established ancestry checks
for manual children and Doctor. Ordinary AutoRefine/Doctor settings are broader
than the bounded helper: require an explicit supported protocol or refuse, rather
than silently changing their defaults. Broader phases, periodic exclusions,
calibrated density, physical repair and B09 remain open; S05/S06 stay partial.


### W121 follow-up — C378 failure recovery and frozen worker code

Cedar C378 adds two actual Phenix 2.2.1-6174 controls with unchanged C377 source.
The exact Cedar ledger at commit `fbc4ea01df5a5e623e20dd555186ce3066cb6c95`,
`docs/cif-linked-native-registration-evidence.json`, key
`frozen_phase_failure_and_joined_package_2026_11_17`, retains commands and full
control bindings. Source remains C377 `0aaec4bd0b7dc49ffd038a5be578523d9ed1a4f1`.
The deliberate MTZ path collision occurs during **final writing after ten
iterations /12 evaluations**, although the original plan expected earlier failure.
Preserve that distinction: native phase return codes are 0/1, the first native
`Sorry` survives, 15 calls complete, the owner closes/poisons and all owned hooks
restore. Partial scientific outputs remain; no usable execution is published.
This is native failure recovery evidence, not successful refinement or campaign
recovery qualification.

A separate fresh native process uses exactly **18 frozen Python modules and three
profiles, 342,556 bytes**, copied from the W121 installed candidate. All 18 native
imports resolve only under the owned code directory, with no live `nasolve`
namespace. Actual preflight 7.86s plus full cycle 35.17s reproduce W120 preparation,
full state, written physical records, optimizer trace and diffraction exactly,
with 15 calls and restored/stopped ownership. This qualifies the bounded worker
source set; the existing installed outer controller still orchestrates it. It does
not establish a durable production request, optional chemistry-site observations,
arbitrary protocols, portable campaign, independent SDK or branch merge.

Exact read-only local receipts under repository anchor **everyday NASolve checkout**:

- `branch-artifacts/cedar/c377-phase-lifetime/native-failure-audit.json`, SHA
  `5d9edf0217673fa2b311a431b3b25433465f6b6ab995832e3180933fa7fa2bae` (1,964 bytes).
- `branch-artifacts/cedar/c377-phase-lifetime/frozen-native-audit.json`, SHA
  `309c57785c712b2405623a95bcd8f3a98f4681f0acc420563818d0f4a19b67d5` (8,043 bytes).

These are separate C378 receipts, not additions to the immutable W121 software
archive or new Willow source/installed test counts. Reuse the qualified frozen set
and existing v4 files in the next versioned execution policy; avoid inferring a
whole-repository dependency from unused diagnostic functions. S05/S06 remain partial.


### W123 — Attribute saved ordinary-refinement pair geometry

**Scope:** read-only Phenix **2.2.1-6174** analysis of the exact archived W116
endpoints, using the W121 joined installation (Willow W118/Cedar C377). Reuse
`NativePairRecipe.describe_terms` and `compare_pair_attribution`; no new evaluator,
refinement, weight search, checkpoint or model adoption. This closes the missing
per-pair readback of the existing ordinary-cycle controls, not S05/S06.

All 123 members of the W116 archive and 306 installed source/resource hashes were
verified before analysis. The same original full recipe measures **124 terms /14
pairs** at each coordinate state. Native-only and zero-addition full endpoint and
R-statistic records are exactly equal, so their observation is reused rather than
recomputed. Saved full-precision force sites equal saved hierarchy coordinates;
identity, term definitions, input bytes and native kernel bindings stay unchanged.
Individual residuals reproduce complete native container sums. These are **raw
unnormalized pair penalties**, not native whole-model geometry scores.

| Pair / scope | Native-only endpoint | Full-addition endpoint | Interpretation |
| --- | ---: | ---: | --- |
| GC A:101–C:102 pair penalty | 152.497191 | 133.198389 | Decreases 19.298803 |
| AT A:102–C:101 pair penalty | 81.470379 | 77.283052 | Decreases 4.187327 |
| GC plane deviation | 20.185303° | 18.681316° | Modest improved alignment |
| AT plane deviation | 5.147528° | 4.830166° | Modest improved alignment |
| GC joint-plane RMS | 0.211030 Å | 0.196516 Å | Still nonplanar |
| AT joint-plane RMS | 0.067061 Å | 0.063642 Å | Small change |

Both selected pairs use the exact declared target image
`-x+y+2/3,-x+1/3,z+1/3`. All four restraint-family penalties decrease for each
selected pair. Their combined change is **−23.486130**; the 12 retained-core pairs
change **−0.102301** in total. Two core pairs increase slightly: A:103–C:114
(+0.001908) and A:108–C:109 (+0.004074). These signs are descriptive, not calibrated
acceptance thresholds. Joint-plane and plane-deviation terms describe pairing,
not adjacent-base stacking or phosphate closure.

The geometry is not repaired: GC donor/acceptor distances are
2.970351, 2.639261 and **2.207122 Å**, and AT distances remain
**3.401875 and 3.491959 Å** against the frozen 2.8 Å targets. Exact saved Rfree
remains 0.2598980109 (native-only) versus 0.2599155744 (full addition); no
improvement or scientific acceptance is claimed. W116 was a short, fixed-weight
lifecycle control using an existing tiny-bend preview, not a repaired deposited
8D93 model or a general sticky-end test.

**Precision and retained failure:** attempt 001 stops with return 1 in 1.88s
because reconstructing coordinates from the source PDB does not reproduce the
sealed prepared force-site hash. Exact prepared initial coordinates were not
archived; a hash alone cannot recover them. Preserve that refusal. Attempt 002
explicitly uses the serialized original PDB only for separately labelled source
comparisons and uses exact archived full-precision endpoints for the main paired
comparison. It completes in **1.42s**, return 0; both owned processes are verified
stopped. No new preflight was run and no prepared-state claim was weakened.

Written endpoint PDB coordinates differ by at most 0.000500 Å per Cartesian axis.
Evaluating those rounded copies changes aggregate raw penalties by −0.219032
(native-only) and +0.106915 (full addition). Consequently tiny individual core
changes must not be inferred from rounded PDB readback alone. Full precision and
serialization comparisons remain separate in the receipt.

Historical commands (attempt 001 retained; attempt 002 is the successful analysis):

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w123-pair-readback/run.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w123-pair-readback/run_002.py
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/willow-w123-pair-readback/audit.py
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/willow-w123-pair-readback/archive.py
```

Independent saved-evidence audit passes: all input/script hashes, stopped outcomes,
complete term definitions, sums, per-pair/family/purpose differences and honest
source/endpoint scope. Local forensic archive under repository anchor **everyday
NASolve checkout**:
`branch-artifacts/willow/w123-pair-attribution-2026-11-17.tar.gz`, SHA
`e6d5104e5c3394865217931318e595af82c23bce61c58d696836f474f3edaa72`,
**1,182,648 bytes /30 indexed files**, every member verified. Scientific inputs,
coordinates and generated measurements remain local and excluded from Git. This
archive references qualified external software and is not a portable resumable
campaign. Full attribution SHA:
`df798184f50c361eda7e9359333ac8929698e55220d75c868608f7840651dea7`.

Repository changes are documentation and roadmap evidence only: no runtime schema,
API, default, compatibility or migration change. No new source/full/install test
claim; native read-only evaluation and documentation audits are the relevant checks.
Next remains Rowan's durable controller/admission/continuation integration, followed
by qualified contact controls. This analysis does not evaluate all backbone chemistry,
clashes, adjacent stacking or density and does not justify retuning against Rfree.


### W124 — Audit package-owned integration and refused admission

Cedar now contains the unchanged maintained Willow library at its original module
paths. This is a bounded source integration, not a second recipe implementation,
a full branch merge or ordinary sticky-end activation. Source authority remains
Willow for periodic geometry/factory code and Cedar for execution ownership.

Exact Cedar pins:

- **C379 `d9e2308e86615c7ed24ef355339fa4b6fefe01ac`** preserves successful
  native preflight followed by rejected evidence as a separate schema-2
  `preflight-admission-refusal-v1` outcome: native codes `[0, null]`, explicit
  `NOT_LAUNCHED`, original typed refusal, exact anchored raw membership, unusable
  failed checkpoint and unchanged selection. Readers retain invalid evidence
  without making it valid or writing repairs. Historical schema-1 meaning and
  native protocols remain unchanged. Old readers reject the new outcome; no
  migration is required. Input/code failures outside preflight-evidence validation
  remain outside this recording slice.
- **C380 `7808e9edf0f863f1f0de21573757d8a5a403fb9e`** integrates exact upstream
  **W118 `c08f337024f8901c583c0988f652e9a1c3156a49`** source: 18 modules,
  17 existing test files and one existing comparison script, **514,308 bytes**.
  No existing shared source is replaced. The optional `topology` extra matches
  upstream Gemmi `>=0.7.5,<0.8`; native imports and recipe-generation dependencies
  stay lazy. Missing or changed qualified runtime helpers now refuse before
  allocating a round or its runtime directory.

Why 18 modules rather than the nine used by the native worker: complete maintained
modules have additional lazy graph/recut dependencies. The existing packing test
also loads the comparison script, whose optional endpoint mode needs the endpoint
audit. Keeping that bounded complete closure avoids shipping partially broken
modules or rewriting qualified code. The **native worker still freezes only its
separately qualified 18 modules /three profiles**; its closure includes Cedar
helpers and is a different set from the installed Willow library. Do not expand
a saved worker merely because additional APIs are installed.

Rowan's validation, not repeated by Linden:

- C379: one regression fails before the change; **135 focused tests +13 subtests**
  pass. Three invalid-evidence variants survive dataset relocation after the
  original path is gone; cold readers preserve bytes/mtime and cannot launch or
  write. Contradictory codes, usability, schema, phase membership and modified
  evidence refuse. Immutable receipt and original-error preservation checks pass.
- C380: **662 focused source tests** pass. **887 relocated installed tests +13
  subtests** pass in **42.28s**, after removing original build-source and install
  directories. All 18 modules import in the base environment without Gemmi or the
  native SDK; periodic use reports its optional dependency. Two allocation-guard
  regressions fail before and pass after; Python 3.10 syntax checks pass.

The exact commands, source hashes and scope are in the immutable
[Cedar C380 evidence ledger](https://github.com/vecchioni-lab/NASolve/blob/7808e9edf0f863f1f0de21573757d8a5a403fb9e/docs/cif-linked-native-registration-evidence.json),
keys `preflight_admission_refusal_2026_11_17` and
`maintained_pair_recipe_package_2026_11_17`.
Qualified wheel SHA:
`f7da3ba3b129d016e6bd06d6a3a42414d9fb31c76a8be2463ddb27697009a49d`.

**Independent read-only audit:** Linden verifies all 36 imported paths against
both upstream and committed Cedar bytes, preserved shared source/fixture bytes,
C379 source hashes, the wheel digest, test-log/receipt equality, absent original
source/install directories and **296 installed Python/resource files against the
committed C380 tree**. No duplicate tests or native run are performed. Exact
integration-manifest SHA is
`36a51365ac730863a8bccca22e917cdfb3aa201050e77139d4e5365c3bc93115`;
the first static-only draft is superseded because it missed the script dependency.
Local audit under repository anchor **everyday NASolve checkout**:
`branch-artifacts/willow/w124-integration-audit.json`, SHA
`13aaf1ceaeee0caf4d5adf6176b3243afd7f2d7004d455b4dbae9b95d01225e5`,
1,552 bytes. Historical independent command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/willow-w124-integration-audit.py
```

No new native execution, full-suite result, scientific artifact, repair acceptance
or automatic counted admission is claimed. The older W112/C366 full-source result
remains historical; current checks are the stated focused/installed panels. Willow
repository changes for W124 are evidence/docs only; Cedar owns the code above.
Next is explicit original-request/current-parent/frame binding, actual preflight,
immutable positive admission and same-phase consumption through existing owners,
then descendant intent retention. W122's user-facing sticky-end option remains
planned, with no new CLI/default behavior. S05/S06 remain partial.


#### W124 focused caller follow-up

The new early source guard also reaches campaign/Doctor callers. The existing
`tests/test_workflow_plane_forces.py` panel was therefore run once against the
same frozen C380 relocated installation: **15 pass, no skips, 4.24s** (4.53s owned
wall). Exact committed fixture dependencies were copied to an isolated directory;
all fixture and installed-package hashes remain unchanged and the process is
verified stopped. No source/tests were edited, and this is neither another full
suite nor a native refinement. It covers existing caller forwarding, cold campaign
reads, Doctor continuation and refusal before allocation; it is not a new counted
admission or complete campaign scientific qualification.

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w124-workflow.py
# Owned child: python -m pytest -q -p no:cacheprovider tests/test_workflow_plane_forces.py --tb=short -ra
# PYTHONPATH=/private/tmp/c380-package-2y61s5fv/relocated
```

Local review archive under repository anchor **everyday NASolve checkout**:
`branch-artifacts/willow/w124-integration-review-2026-11-17.tar.gz`, SHA
`795052794874791f5864d945abee9a0b96e80d2fe2836f2a32e06e9d812e1143`,
**43,550 bytes /11 indexed files**, all members verified. It retains both planning
revisions (revision 002 is authoritative), independent audit, installed receipts,
caller-check script/log and exact source/fixture manifests. External software and
committed fixtures are represented by their pins rather than duplicated; no
scientific data or portable-execution claim is included.


### W125 — Audit durable counted admission and native outcomes

Cedar C381 replaces the diagnostic-only handoff with an explicit saved request,
actual native preflight, immutable admission and same-phase consumption. It reuses
the existing execution owner, W118 recipe rebind, C375 contribution and C377
bounded refinement lifetime. No new optimizer or pair engine is introduced.

The new explicit `round-local-counted-execution-v5` request stores original recipe
and source, checked current-parent recipe, anchored inputs and qualified code.
After stopped successful native preflight, admission seals the actual prepared
state, selected providers and protocol. The prepared JSON is compacted with the
existing verified archive format; its directory is synchronized before retiring
the transient raw copy. Cold readers validate records without publishing them.
An exclusive launch marker prevents duplicate use of the same admitted attempt,
including an early worker failure. Native errors survive secondary reporting
errors; failed evidence is retained without being marked usable.

Ordinary AutoRefine/Doctor defaults remain v3. Their existing lineage guard now
refuses a counted ancestor, including a manual descendant, before allocating a
new round: ordinary continuation must not silently drop pair restraints. Positive
descendant continuation remains the next gate. The admitted protocol remains
one cycle, 1–10 iterations, one process, fixed unit weights and all-site coordinate
refinement; unsupported broader native scope refuses rather than being overridden.

**Actual Phenix 2.2.1-6174 controls, run by Rowan:**

- Success: preflight **16.21s**, complete refinement **35.78s**, native codes
  **0/0**. Original W116 inputs and working crystal frame are preserved. The
  saved preparation, final hierarchy/scattering/force sites and written physical
  PDB records match the checksum-bound W120 control exactly. The owner closes
  cleanly after **15 calls**, with **11,379 native +17 added =11,396** terms and
  normalization **1/11,396**. The prepared archive is **67,216 bytes**.
- Unsupported actual iteration scope: native preflight **4.57s /exit0**, then
  explicit refusal; no admission, launch marker or refinement. The saved outcome
  preserves the typed reason and codes **0/null**, rather than inventing a native
  failure.
- Blocked final MTZ: actual preflight **6.89s /exit0**, refinement **34.36s /exit1**.
  Optimization reached the final writer. The original native `Sorry` survives;
  partial PDB/output files remain, the owner closes poisoned after 15 calls and
  its binding is restored. This is failed execution, not a usable checkpoint.

**Independent Linden audit:** all 298 files in the native candidate's installed
source/resource manifest and 60 relocated successful-run files verify. The original
run root is absent. Completed execution/admission cold reads cannot launch a
process or publish records, preserve bytes/mtime, and remove their temporary
expanded view. Exact archived W120 preparation and final-state comparisons pass.
Both native failure controls independently cold-read, reject usability, preserve
input hashes and errors, and have stopped processes. Their roots were not relocated
in this audit; relocation evidence is the successful case. No duplicate native run
or duplicate peer test panel was launched by Linden.

Cedar source pin: **C381 `571f3850b73bc4bd13a070d1f3c8dc0481854bdb`**.
The [committed Cedar ledger](https://github.com/vecchioni-lab/NASolve/blob/571f3850b73bc4bd13a070d1f3c8dc0481854bdb/docs/cif-linked-native-registration-evidence.json),
key `maintained_counted_admission_2026_11_17`, owns the exact native commands,
source hashes, negative-before regressions and peer validation.

The final relocated installation passes **347 focused tests +13 subtests in
48.79s** after removing build source and the original install directory. Linden
independently verifies all **298 installed source/resource files against the
committed C381 tree**, the saved test log and wheel SHA
`e81ffddb20c72a4a25ba0547601fe2429e641921bda978a14998e5d7b0f6f8ee`.
The earlier native candidate wheel is
`ed023b9c062674ed4255cb3331f0c766939d2bf2eea2c4148795619b7886d602`;
all **24 frozen native payload files are byte-identical** in the final package.
Only outer controller/cold-reader/storage guards changed after the native run.
Final-package readers independently validate the success and both failures without
launches or persistent writes; this is not another native execution.

Historical independent commands:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w125-admission-review/audit.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w125-admission-review/controls.py
```

Local forensic review archive under repository anchor **everyday NASolve checkout**:
`branch-artifacts/willow/w125-counted-admission-review-2026-11-17.tar.gz`, SHA
`c2105880206b1939708ccd6df67f3ffa4a49f8d271a84f8b3befa75e9283362b`,
**44,941 bytes /18 indexed files**, all verified. It retains independent audit
scripts/results, both installed manifests/receipts and peer native summaries.
Original scientific run artifacts remain local and excluded from Git; this compact
review archive is not a portable or resumable campaign.
Two further read-only commands, using the same Python/environment above, are
`final-package.py` and `committed-source.py` in the same historical audit directory.

This Willow change records evidence and roadmap progress only; Cedar owns the
runtime/schema changes. The new records require a v5-capable reader; old policies
and ordinary defaults retain their meanings, with no old-run migration. Relocated
completed receipts are readable; historical pending commands are not resumable.
No ordinary CLI activation, usable campaign selection, positive continuation,
broader phase/weight scope, current full-suite or scientific-repair qualification
is claimed. This independent audit does not recompute or compare full-precision
R statistics. W123's residual defects and lack of diffraction benefit still apply.
S05/S06 remain partial; W122's explicit user-facing option remains planning-only.


### W126 — Audit registered continuation and inherited input adaptation

Cedar **C382 `18283b3159a1f2404fd957da60328d88801fbb2e`** adds the explicit
`refinement_counted.prepare_continuation` join. Before it, C381 could admit an
initial request but ordinary descendants correctly refused rather than lose intent.
The new helper uses existing registry/strict-lineage validation, exact selected
model/observation/restraint/phase inputs, original recipe/source and W118's
same-frame rebind. Each child still needs fresh native preflight and admission.
Registry reads also reject changed original intent across counted descendants.
The caller owns numbered rounds, processes and publication; the helper is not
another executor and grants no scientific selection.

Cedar **C383 `e9afa595a26116ce9ef5f88ff779c640efd936aa`** then accepts the
existing C278 namespace-only PHIL execution copies through an optional
`refinement_input_reference`. The existing validator authenticates the selected
parent's original references, copy indices/contents and current round; the normal
checkpoint output must retain that receipt. This changes PHIL scope spelling,
not atom identities, chemistry or the compiled pair recipe. No new adapter,
schema, native worker or default is introduced. C291 is whole-base transport,
not this input adapter; retain the distinction.

Changed Cedar runtime paths are `refinement_counted.py` and
`refinement_parallelity.py`; existing `test_refinement_counted.py` gains focused
controls. Exact commands and source pins are in the
[committed Cedar ledger](https://github.com/vecchioni-lab/NASolve/blob/e9afa595a26116ce9ef5f88ff779c640efd936aa/docs/cif-linked-native-registration-evidence.json),
keys `registered_counted_continuation_2026_11_17` and
`counted_continuation_input_adaptation_2026_11_17`.

**Peer validation, not duplicated by Linden:** C382 has 40 focused source tests
and **360 relocated installed tests +13 subtests (53.73s)**. Compatible direct
and manual children, changed/missing model atoms/frame, original intent replacement,
broken lineage, lost intent, wrong inputs and relocation are covered. C383's
targeted installed input/continuation panel has **62 passes (18.09s)**, including
absent/previous-round receipts, changed execution bytes, identical bytes from the
wrong declared source, missing checkpoint proof and relocation. Negative-before
results are retained. No current full-suite claim.

**Actual Phenix 2.2.1-6174:** the completed C381 model is explicitly imported
into a diagnostic PostMR registry context; no MR/ReadySet rerun or retrospective
registration of C381's arbitrary parent label is claimed. One registered cycle
then supplies the exact parent output to a second cycle via the maintained helper:

| Registered result | Actual preflight /refine | Final native +added count | Prepared archive |
| --- | --- | --- | --- |
| `refine-001` from diagnostic `postmr` | 11.83 /43.50s; both exit0 | 11,392 +17 =11,409 | 67,226 bytes |
| `refine-002` from `refine-001` | 7.55 /35.76s; both exit0 | 11,382 +17 =11,399 | 67,225 bytes |

Both owners close cleanly after 15 calls. Original intent is exact; rebound recipes
and preparations differ appropriately for the new coordinates. Both checkpoints
are usable for explicit continued inspection but remain **unselected REVIEW**;
the selected checkpoint stays `postmr`. The retained runner asserts first-round
bytes/mtime preservation through the second run. Its original root is gone after
relocation. Historical pending commands are not thereby resumable.

**Independent audit:** 117 relocated-run files, both C382 installed manifests,
exact parent-output linkage, original intent, fresh preparation/counts and stopped
owned processes verify. Cold registry/execution reads launch nothing, publish
nothing and preserve bytes/mtime. Final C382 and C383 each have **298 installed
source/resource files matching their committed tree**; C383 changes only the
outer `refinement_counted.py` module relative to final C382. All 24 frozen native
payload files per round remain exact. C383's final reader accepts the C382 registry.

Wheel pins: native C382 `112761efcdfbab6753443076e875c66d421332f18039575ba2956c4975f4bc72`;
final C382 `b208105fa2492af571f2e08901af8f4abd2870d77fc1171c77995344fabcaa12`;
final C383 `810ad0dd99a56211950f0ac3f2d9dba1662e06b59f4212b8a7ae10fd96f9e85a`.
Later outer-controller guards are independently separated from unchanged actual
native payloads. No additional native cycle is run for C383.

**PDB-only scientific readback:** using the same exact image and declared base
atom groups, G·C plane mismatch is **18.69 →17.77 →16.77°**, and its short O6–N4
contact is **2.207 →2.286 →2.340 Å** across imported parent and both descendants.
A·T plane mismatch is **4.83 →4.37 →4.27°**; distances are mixed and remain long.
The baseline calculation matches the existing W123 native written-PDB observations
(distances within 1e-8 Å; plane angles within 1e-7°). This is SVD/distance readback,
not new native force evaluation, complete geometry or matched efficacy evidence.
Logged rounded Rwork/Rfree worsen **.2245/.2599 →.2251/.2609 →.2253/.2611**.
There are no native-only continuation siblings; do not attribute all changes to
the extra terms or call this repair. The fixed-unit, one-cycle capped protocol is
a qualification diagnostic, not a recommended scientific default.

Historical independent commands use `PYTHONDONTWRITEBYTECODE=1` and
`/private/tmp/willow-w94-pivot/env/bin/python` on `audit.py`, `committed-source.py`,
`adaptation.py` and `geometry.py` under
`/private/tmp/willow-w126-continuation-review/`. Local review archive, repository
anchor **everyday NASolve checkout**:
`branch-artifacts/willow/w126-registered-continuation-review-2026-11-17.tar.gz`, SHA
`028e88fbd3108f94952510f2a2ee0c07979a3524ba36adaf2b09cd9c421e4b86`,
**67,493 bytes /25 indexed files**, all verified. It references separately verified
Cedar native archives and verifies all three measured PDB members against their
source hashes. Original models/maps remain local, excluded from Git; forensic
archives are not portable resumable campaigns.

Willow changes are docs/evidence only. Optional argument/API growth preserves old
callers and schemas; incompatible ancestry now refuses intentionally. Ordinary
AutoRefine/Doctor activation, broader protocol/chemical scope, periodic exclusions,
physical repair and density-aware acceptance remain open. Next is the
[ordinary-owner integration boundary](topostitch.md#ordinary-owner-integration-boundary-w126-planning),
not another duplicate short-cycle probe. W122's user-facing feature remains planned.

**Follow-up boundary:** Rowan subsequently tested a fresh copy of the C382 registry
and found that substituting `refine-001`'s checksum-valid model reference into
`refine-002` could pass the C383 reader. The original run was unchanged. This does
not change the independently verified actual output hashes above; it identifies
a missing final-writer-to-checkpoint binding that must close before ordinary-owner
integration. No fixed reader or negative regression is claimed by W126.


**C384 ancestry follow-up:** `4fa8969b86c5dc971953ed29b152b8a96dd6ad19`
closes a separate missed case: an ordinary refinement with no execution receipt
could previously be skipped when recovering inherited pair intent, including
through a later manual import. The existing root-to-parent traversal now permits
an unrecorded post-counted step only under the existing `manual` / `manual-*`
contract. Two regressions failed before; peer source and relocated installed
panels each pass **144 tests** (installed **45.82s**). No native/schema/default or
worker changes; the final-writer/model-reference gap above remains open.

Independent read-only `c384-audit.py` in the historical W126 review directory
verifies all **298 installed source/resource files** against that commit, the
144-test log and wheel `11ca6e6db54959531ab57fd4db19858e3bb680b4930f6f78cca0873f59e2c735`.
Only outer `refinement_counted.py` differs from final C383; all **24 frozen native
files per round** remain exact, and cold reads preserve all **117 C382 run files**
without writes or launches. No peer test/native run is duplicated.
Exact peer commands are in the committed Cedar ledger key
`counted_missing_refinement_ancestry_2026_11_17`. The follow-up archive under the
same everyday-NASolve repository anchor is
`branch-artifacts/willow/w126-c384-ancestry-review-2026-11-17.tar.gz`, SHA
`9d9ad0f1120a944d4a70222abd4f006a7e57eb6b35a6ac913b99eece82bd2619`,
**20,420 bytes /6 indexed files**, all verified. This is forensic review evidence,
not a portable or resumable run. W126's scientific interpretation is unchanged.


### W127 — Bind the published checkpoint to the native-written model

Cedar **C385 `2d4987ef6aa17d392e49f3f864d1a82eea8b2bfe`** closes the publication gap found after W126.
Previously a checksum-valid previous model could replace a counted checkpoint's
output reference and still pass the v5 reader. New explicit
`round-local-counted-execution-v6` requires a `native-written-model-v1` observation
from the actual native final writer. It resolves the fresh PDB path before Phenix
increments its output serial, observes unchanged native hierarchy around the
existing writer callback, and hashes the bytes only after the entire writer returns.
The existing checkpoint validator joins that hash/size to the published usable
model; the state hash must also match completed output-synchronization evidence.
No filename search, extra executor, geometry term or scientific setting is added.

Default v3 stays unchanged. Frozen v4/v5 helper bytes are preserved in the package
resource `data/refinement-runtime-v5-sources.json`; independent source review
checks all three archived files against committed C384. Historical v5 remains
readable with its original limitations; it does not retroactively gain this proof.
Continuation retains its inherited v5/v6 policy, and a v6 descendant cannot drop
back to v5. Existing callers retain their defaults; v6 requires a capable reader.

Changed Cedar source: `cif_refinement_output.py`, `cif_refinement_runtime.py`,
`cif_counted_phase.py`, `refinement_counted.py`, `refinement_parallelity.py`, the
historical-source resource and focused existing tests. Exact peer validation is in
the [committed Cedar ledger](https://github.com/vecchioni-lab/NASolve/blob/2d4987ef6aa17d392e49f3f864d1a82eea8b2bfe/docs/cif-linked-native-registration-evidence.json),
key `counted_native_written_model_2026_11_17`. Six new observation tests failed
before implementation; **197 focused source tests pass (40.44s)** and
**282 relocated installed tests pass (46.69s)**: actual callback
ordering/serial, absent/changed/symlink/preexisting output, changed hierarchy,
missing callback, retained partial output/original writer error, wrong published
model, relocation, inherited policy and downgrade refusal. No current full suite
or whole-branch integration qualification is claimed.

**Actual Phenix 2.2.1-6174:** one dry-run preflight **11.42s**, followed by a
complete refinement **35.35s**, both exit0. This is an explicit diagnostic import
of C381's completed output, under the unchanged one-cycle/ten-iteration fixed-unit
protocol. The owner closes unpoisoned after **15 calls**, with **11,392 native +17
added =11,409** terms. Complete PDB bytes, native output-synchronization state and
the entire counted-owner observation exactly match C382's first cycle. The native
written-model record is SHA `55d28cbd19bf01874a313ff9b10b2ed4209e9e0f9b23e738b189ed5eda1082eb`,
143,889 bytes, hierarchy-state SHA
`f4d01d2e62d67354ddc86ea28dc6f5592e6ac91071b4f9de10296ccc4644dbed`.
This qualifies provenance, not additional structural improvement.

The registered checkpoint remains **unselected REVIEW**, with `postmr` selected.
Logged Rwork/Rfree remain the existing **.2245/.2599 → .2251/.2609**. No new geometry
or diffraction benefit is claimed, and the published five-file science checkout
is intentionally unchanged. Ordinary AutoRefine/Doctor activation, broader native
scope, terminal-source additions, physical repair and density acceptance remain open.

**Independent audit:** verifies all **299 installed source/resource files**, exact
wheel `12b613410142aed6ae7fd7aeb758d6d01e8f40a91458765356cac413672514d6`,
the installed test log, all **24 v6 native payload files**, unchanged historical v5
payloads and stopped owned processes. Relocated cold reads preserve **64 current
and 117 historical C382 files** without launches or persistent writes. An
in-memory copy substituting the checksum-valid previous model is rejected by the
production publication validator; no on-disk registry is modified. The peer's
separate disposable-copy previous-model/modified-copy controls are retained in its
runner/receipt and reviewed, not duplicated. The original root and temporary
expanded preparation are absent. Historical pending commands are not resumable.

One earlier harness used a controller environment missing Gemmi; its preserved
failed root reports zero cycles and stopped before runtime allocation/native
launch. That setup failure is not a failed native chemistry experiment.

Independent historical command: `PYTHONDONTWRITEBYTECODE=1
/private/tmp/willow-w94-pivot/env/bin/python
/private/tmp/willow-w127-written-model-review/audit.py` (one command; line breaks
for reading). Final installed/committed source equality is checked separately by
`committed-source.py` in the same directory. Review archive, repository anchor
**everyday NASolve checkout**: `branch-artifacts/willow/w127-written-model-review-2026-11-17.tar.gz`, SHA `af30cd8135302f86cb8b8f164b8189b0efcfa353c764f5932dd676240a146f40`, **32,744 bytes
/14 indexed files**, all verified. Scientific originals remain local and
excluded from Git. This is forensic evidence, not a portable/resumable campaign.

Willow changes are documentation/evidence only. S05/S06 remain partial. W122's
explicit sticky-end feature remains planned; next join the qualified path to the
existing ordinary refinement owner, without silently narrowing its defaults.


### W128 — Carry explicit pair restraints through ordinary AutoRefine

Cedar **C386 `d5c2fb7be944aae5e048903e1de495c67baa4b05`** joins the qualified
counted-pair machinery to the existing AutoRefine owner. Previously counted
ancestry was refused by that route; the positive cycle required a manually
composed diagnostic. The Python API now accepts an explicit original recipe and
source model with `counted_protocol="counted-xyz-fixed-unit-v1"`. Caller options
must request one cycle/process, XYZ only, no ADPs/occupancy or anomalous refinement.
The named protocol fixes unit weights, seed 1 and ten iterations. Unsupported
experimental-phase consumption, chemistry projections and new extra/terminal
restraints refuse before round allocation; inherited protection stays checked.
This is a bounded control, not a recommended scientific default or a CLI feature.

Methods: reuse the ordinary parameter writer, C278 input adapter, stopped-preflight
seal, existing subprocess ownership and checkpoint publisher. Preserve original
pair intent and validate the actual written-model proof **before** appending a
usable checkpoint. A fresh v6 request may retain a v5 ancestor's exact original
intent, without upgrading its old evidence. Successful controls remain unselected
REVIEW even when the ordinary numerical thresholds pass. Context-entry refusals
preserve existing launch evidence and do not invent a no-launch outcome.

`counted_frame="recipe"` explicitly chooses the already validated recipe crystal;
the ordinary parameter file and report record it. Leaving the option unset retains
native frame choice. No fixture-specific cell, changed compiled tolerance or
campaign-wide PDB-over-MTZ rule is introduced. Ordinary parameter/command bytes
match C385 exactly across **32** existing combinations of selector version,
mean/anomalous data, phase use and strategy.

**Actual Phenix 2.2.1-6174:** one ordinary controller completes native dry-run
preflight and real refinement, both exit 0, in **45.41 seconds total**. Both native
children belong to that controller; all processes stopped. Its **15** counted
calls preserve **11,392 native +17 added =11,409** terms. The complete written PDB
is exactly C385's `55d28cbd19bf01874a313ff9b10b2ed4209e9e0f9b23e738b189ed5eda1082eb`
(143,889 bytes). The result remains usable, unselected REVIEW with `postmr`
selected. This first ordinary control starts from a fresh diagnostic PostMR import; ordinary
counted-parent continuation has synthetic coverage, not a new native descendant
run here. This closes the initial owner handoff, not a new bending or diffraction result:
logged Rwork/Rfree are again **.2245/.2599 → .2251/.2609**.

The diagnostic stages a **label-only** copy, `Fobs/SIGFobs → F/SIGF`, to use the
existing ordinary reflection menu. Original and staged MTZ bytes differ; all
ordered HKL/data/sigma/Free-R array bytes, column types, missing masks, cell and
group agree. There are **3,333 observations /176 Free-R selections**. Original
SHA `f57083bb6d6b74789ba77c0c448c678356f7e3a52805a7142e1b33f9055d86a7`;
staged SHA `7bb523e28f495712e8c8098a01c084b92ba9276a6cd29561b41e1961c0d9393f`.
This fixture needs no C278 namespace copy; that adaptation is separately covered
by focused tests and earlier evidence. Parsed bond/angle RMS fields in C386 are
unavailable for this log format, not zero; a reporting follow-up belongs to Cedar.

**Validation:** peer source panel **207 tests +13 subtests**, followed by **five**
new boundary cases; relocated installed panel **345 +13** in **75.83s**. Exact
commands are in Cedar's committed ledger key `ordinary_counted_control_2026_11_18`.
Independent review verifies all **299 committed/installed files**, wheel
`cde2754b357f8262c64d2303dbdd02eca5f28bea1a7dd1db1bbb5b7c06541ec5`, actual
request/admission/output identity, the label adaptation, and immutable cold reads
of **72 current /64 historical files**. A checksum-valid previous model is refused
without changing a registry. Old source/install/run locations are absent; historical
absolute command paths remain provenance, not permission to replay a relocated run.

An unfiltered full **Cedar** suite is running separately from a tracked snapshot
of C386. It includes Cedar's integrated Willow numerical library, not a whole-branch
Willow/Pine/Cedar merge. No full pass is claimed until its result is recorded.

Independent historical commands use `/private/tmp/willow-w94-pivot/env/bin/python`
with `PYTHONDONTWRITEBYTECODE=1`: `audit.py` and `ordinary-compatibility.py` in
`/private/tmp/willow-w128-autorefine-review`; the latter records baseline
`eeb4f3f9` and the relocated package explicitly. The local review archive, anchored
at the **everyday NASolve checkout**, is
`branch-artifacts/willow/w128-ordinary-owner-review-2026-11-18.tar.gz`, SHA
`71f639e64fe0c4b0136f827303181282fac581a14d4de6832bc5f296c40a5549`, **11,646
bytes /9 indexed files**, all verified. It excludes the still-running full suite.
Raw scientific runs, scripts and installed packages remain local, outside Git.

Willow changes are documentation/evidence only. S06 remains partial and W122's
user-facing sticky-end option stays planned. Before broadening automatic weights,
compare **selection statistics** across equivalent native/additive provider splits,
not only energies/gradients. Hazel's saved metal evidence shows soft NA-pair terms
can dominate pooled bond RMS. Whether changing provider ownership changes the
selector is a separate, initially untested hypothesis: first compare actual native
statistics at frozen coordinates with existing full/partial recipes, without an
optimizer or weight sweep. Broader phases, exclusions, density-aware repair and
matched independent-structure efficacy remain open.


### W129 — Measure provider-dependent geometry summaries

The installed native XYZ-weight summary reads `model.geometry_statistics()` bond
and angle RMS. Provider-independent energies and gradients therefore do not, by
themselves, prove provider-independent weight-selection inputs. W129 tests that
specific distinction on **one retained W110 reference model**. The fixture's old
`healthy` label does not imply accepted chemical geometry.

One passive **Phenix 2.2.1-6174** process, **20.68s**, compares complete native core
coverage with the existing partial-pair construction: move one angle, one plane
and one parallelity term to the declared additive subset. Coordinates, fractional
force sites, intended terms and shell exclusions stay fixed. The existing compiler
and native energy API reconstruct the complete score/forces; no active contribution
facade, optimizer, weight search or model output is introduced. Native requested
coverage changes **107→104**, additive coverage **17→20**, total count stays
**11,396**, and complete normalized target stays **0.6756064118611885**. Raw target
and full-gradient differences are only **9.09e-13 /4.55e-13**, within the existing
W110 arithmetic tolerances.

| Actual native summary | Complete core | Partial pair |
| --- | ---: | ---: |
| Default bond RMS /count | 0.02638705 Å /987 | identical |
| Default angle RMS /count | 2.30831009° /1519 | 2.30892601° /1518 |
| Standard-origin 0 bond RMS /count | 0.01328101 Å /956 | identical |
| Standard-origin 0 angle RMS /count | 2.32419589° /1467 | identical |
| Origin 4 edited bond RMS /count | 0.12934085 Å /31 | identical |
| Origin 4 edited angle RMS /count | 1.80337955° /52 | 1.81552098° /51 |

The default angle statistic changes by **0.000615924° without moving any atoms**.
This is a small bookkeeping effect, not a structural improvement or a demonstrated
different weight choice. The native `Auto` origin filter includes origin 4,
**edits**, which contains these NA-pair terms. It must not be treated as a universal
noncovalent label: legitimate covalent and terminal-phosphate edits may share it.
Future separation must use existing semantic request/coverage ownership, not
blanket exclusion of edited restraints. The standard-origin angle RMS remains
above 2°; separating soft pair terms does not establish good overall geometry.

Independent cold audit verifies **304 software files /5 archived inputs**, pooled
RMS arithmetic, exact restoration of native proxies/kernel and unchanged source
and force coordinates. Direct PDB arithmetic gives the removed angle
**117.205637532265°**, ideal **116.2°**; its **1.005637532265°** deviation accounts
for the entire pooled variance change. No second native run is used for this audit.
The first setup attempt failed on an optional OS niceness operation before native
launch. Its receipt/runner remain retained; a fresh attempt omitted that scheduling
request and used the same frozen scientific probe.

Source/package pin: Cedar C386 `d5c2fb7be944aae5e048903e1de495c67baa4b05`, including
the W118 library. Native plan SHA
`a14b2ad32e7eaa3a6270af1e9fbb69cbb3f965bdfbd6ac54b685dd50878bbd06`;
result SHA `9fb272796f99837f2a63bc4648521776eb3c6e415700b61ffc564a48a1e546ad`.
The exact source trace includes the installed `xyz_reciprocal_space.summary`,
`model.geometry_statistics`, statistics and origin-filter implementations; no
general claim about every Phenix version is made.

Historical launch: with `PYTHONDONTWRITEBYTECODE=1`, the existing controller Python
`/private/tmp/willow-w94-pivot/env/bin/python` runs the repository-anchored
`branch-artifacts/willow/runners/w129-run-provider-statistics.py` with explicit
plan `/private/tmp/willow-w129-provider-statistics/plan.json` and `attempt-002`.
The existing process owner bounds native execution to 300s and one numerical
thread; `audit.py` in that local task directory performs cold review. Local archive,
**everyday NASolve repository** anchor:
`branch-artifacts/willow/w129-provider-statistics-2026-11-18.tar.gz`, SHA
`253870ec10b63e3ccc767044bbe156c53b61f9e5e39f1892f00983c622e76072`, **35,842
bytes /11 indexed files**, all verified. It references the existing checked W110
input archive rather than duplicating scientific inputs. It is forensic evidence,
not a portable/resumable campaign.

Willow production code and refinement policies are unchanged. The C386 full suite
continues separately and has reported failures pending complete traces. Next
resolve those failures, coordinate semantic geometry readback with Cedar/Hazel,
and qualify any automatic-weighting policy separately. Do not repeat this frozen
comparison or manufacture an optimizer to avoid that decision. S06 stays partial;
matched efficacy, density, broader protocols and W122 activation remain open.


### W130 — Keep chemistry observation beside counted pair forces

Independent review qualifies Cedar C388 `a67df6b7a70dad94d0f14e3cdabea5f8f5a9c21e`:
existing site-scoped chemical observation can accompany the explicit v6 one-cycle
counted protocol. The ordinary owner preserves validated source projections before
round allocation, through forwarding and during descendant/cold-read validation.
Dropping or replacing inherited projections refuses. V5 still excludes this
combination; old C386 readers refuse it rather than silently ignoring chemistry.
Frozen numerical/native worker bytes and ordinary defaults are unchanged. This
requires the C388 reader; it is not a migration of old execution evidence.

Two actual **Phenix 2.2.1-6174** matched controls each use the same modified starting
model and explicit canonical **A:11 DT / B:5 DA** pair, with passive **PDU B:4**
observation off/on. The full-native pair uses **10,998 native /0 additive** terms;
the partial pair transfers exactly one parallelity declaration and uses
**10,997 /1**, retaining all other declarations, bonds and exclusions. Each case
finishes dry-run preflight and a complete bounded refinement cycle; all processes
stop. Within each off/on pair, the written model, full native output state and
15-call owner lifetime are exact. Across provider arrangements, rounded PDB bytes
match but **full-precision state hashes differ**; do not conflate those claims.

The scoped triple screen reads **1.158299 Å**, **176.621° /176.291°**. This is
coexistence evidence, not a new PDU repair result or noncanonical pair support.
Final **Rwork/Rfree 0.4230/0.8360**, bond RMS **0.116 Å**, angle RMS **4.368°** make
this short fixed-unit mechanics control unsuitable for scientific acceptance.
The native demonstrations use the low-level owner; ordinary forwarding and
continuation have separate synthetic regression coverage. No ordinary native
chemistry-descendant demonstration is claimed.

Installed qualification: **365 passes +24 subtests**, initially **12 missing-fixture
failures**, followed by those **12 passing** after supplying the exact existing
public PDU/ATL test inputs; no product patch between attempts. That is 377 distinct
passing tests across two invocations, not an uninterrupted clean panel. Independent
review matches all **299 Git/wheel/installed source files**, verifies exact PHIL
surgery, original inputs/projection and native readback, and leaves **125 /126**
relocated files plus **57** historical C338 files unchanged. It launches no native
process and makes no persistent evidence writes. Earlier C386 full regression is
still running with failure markers; later C387/C388 are not included in that pin.

Local audit command: `PYTHONDONTWRITEBYTECODE=1` with the existing controller Python
runs `/private/tmp/willow-w130-chemistry-integration-review/audit.py`. Native roots
are `/private/tmp/c388-counted-chemistry-lhckzfvp-relocated` and
`/private/tmp/c388-counted-chemistry-partial-x8eiln6f-relocated`; original roots are
absent. These absolute paths are historical/local evidence locations, not portable
replay instructions. Audit SHA
`d39ea5cc60e94aae170e264c5a3d31498b898594e95f38781348d410551811c5`;
installed wheel SHA
`84079e56aafdcd1e1aed9842bea58f527c102c53e71bb68aefe482713ac44023`.
The everyday NASolve repository-anchored archive
`branch-artifacts/willow/w130-chemistry-integration-review-2026-11-18.tar.gz`
has SHA `ba05b2c2c979fbe05be4ab000d57005664f5263e809f010e9a29b742acdff815`,
**5,096 bytes /2 indexed files**, independently expanded/verified. Raw science
stays local. Willow changes here are documentation/evidence only.

Next: finish full-suite diagnosis and add optional semantic pair-geometry
readback outside the frozen runtime helper closure. Reuse complete recipe
attribution and exact coverage; leave the native remainder unclassified until
Cedar supplies chemical ownership. No blanket origin-ID filtering or weight
policy change follows from this audit. S06 and W122 activation remain partial/planned.


### W131 — Report complete pair geometry across force providers

Optional pure Python `topostitch_pair_geometry.review_pair_geometry` joins four
existing caller-authenticated records: full recipe attribution, compiled term
declarations, v2 native force-state observation and frozen provider selection.
It checks the frozen input digest, source/recipe/atom identities, compiled binding,
actual force-coordinate digest, complete coverage and measured term targets.
It reuses existing validators; it does not evaluate native forces or launch tools.
The new module sits outside the frozen native helper closure, whose nine relevant
numerical/observation sources remain byte-identical to C388. No new runtime policy,
CLI, ordinary default, selection rule or operational schema migration is introduced.
The new schema-1 `topostitch-covered-pair-geometry` report is descriptive only;
see the [API contract](topostitch.md).

Physical summaries cover the full declared recipe independently of provider:
unweighted pair-distance and angle deviations, RMS of per-plane RMS distances
(not pooled per-atom RMS), and native parallelity delta RMS. Energy is retained
separately. Exact unmatched native IDs/families/origins remain **UNCLASSIFIED**;
`covalent_geometry=UNASSESSED`. No blanket origin-0/origin-4 chemistry assignment
or future weight policy is implied.

**One passive Phenix 2.2.1-6174 check, 15.13s**, uses the retained W110 input
already verified in W129. It evaluates full recipe attribution once at actual
force coordinates, then joins complete and partial native observations. Moving
one angle, plane and parallelity term changes native/additive coverage
**107+17→104+20**. The following complete intended-pair measurements stay exact:

| Quantity | Count | RMS |
| --- | ---: | ---: |
| Pair-distance target deviation | 36 | 0.234286 Å |
| Pair-angle target deviation | 60 | 4.856396° |
| Per-plane RMS-distance summary | 14 planes | 0.127707 Å |
| Native parallelity delta | 14 | 9.823554° |

Pair energy stays **564.9181277185738** under its existing unnormalized sum.
**2,465** other supported native terms remain unclassified in each observation
(bond/angle/planarity/parallelity only, not dihedral/chirality/nonbonded families);
their ordinal IDs are local to each inventory and must not be treated as stable
cross-provider atom identities. Coordinates/policy stay fixed; native proxy objects
and temporary kernel binding are restored. No optimizer, selector, new PDB or
scientific acceptance. These imperfect pair measurements are diagnostic outcomes,
not thresholds or a new improvement claim.

Source pin **`ead86be9f70280cb7c76e2df9416aadbea301463`**. Validation uses
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` and the existing controller interpreter:
`python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_pair_geometry.py
 tests/test_topostitch_recipe.py tests/test_topostitch_pair_coverage.py
 tests/test_topostitch_native_coverage.py` gives **203 passes**. The 17 new
regressions first failed before the module existed. Unfiltered `python -B -m pytest
-q -p no:cacheprovider` gives **2,050 passes +229 subtests, 105.61s** after an
initial sandbox run gave **2,045 passes +229 subtests /5 explicit `/bin/ps`
permission failures**. Both attempts are retained; no product code changed.

Clean wheel install relocated after removing its build/source copy and original
install path: **203 installed passes**, six entry-point helps and dependency check.
All **92** tracked source/data files match the exact source commit; **89** are
packaged. Three pre-existing ligand provenance notes are source-only. Verification
initially expected those notes in the wheel and omitted two existing test-helper
imports; the retained harness failures were corrected using the complete tracked
test closure, without a product change. Wheel SHA
`3a0d74cd237bcd6ea32185bc5a5ae413dfce5a1f532d9db343933806a85355bd`, **470,760 bytes**.

The native probe combines installed C388
`a67df6b7a70dad94d0f14e3cdabea5f8f5a9c21e` with only the installed new diagnostic
module via a declared package search path; no copied or replaced frozen helper.
It verifies **305 software /5 scientific input hashes**. Plan SHA
`94ede7748740540977763757643a71526655070b62f5e30d443e5275695ce03e`;
result SHA `07c787a9d1ab7fe06a93af6acf8acdb1a6cc98f893139bf6d8351056a43dea62`.
Cold audit reproduces both reports with native launches blocked, independently
recomputes bond/angle RMS from measurements, and preserves saved files. Audit SHA
`87d62b9ba2e5a94d04ec02473f8388719c35b6bf5f11b8e3c3f2ebc7facb0a46`.

Local runner/audit/package receipt: `/private/tmp/willow-w131-pair-geometry/`.
Historical native launch: controller Python `run-probe.py plan.json native`,
300s cap, one numerical thread, existing process ownership and verified shutdown.
The repository-anchored local archive is
`NASolve/branch-artifacts/willow/w131-pair-geometry-2026-11-18.tar.gz`, SHA
`0bd0f0ba3316e8edec5bd11ecd3874fedf6e1c6a45807a2e666e3ea0d4adcb4b`,
**271,845 bytes /28 indexed files**, verified after expansion. This is forensic
local evidence, not a portable replayable campaign. Raw science is not committed.

Next: Cedar integration of this pure reporting seam, explicit ownership of
covalent/terminal/metal terms and full C386 failure diagnosis. W129's native summary
comparison need not be repeated. Automatic weighting, density, matched efficacy
and W122 user-facing activation remain separate gates; S06 remains partial.


### W132 — Resolve full-suite environment and source prerequisites

The complete unfiltered Cedar C386 snapshot
`d5c2fb7be944aae5e048903e1de495c67baa4b05` finished in **3,266.71s** with
**11,873 passed /46 failed /2 skipped /281 subtests passed**. All **1,405** tracked
files remained unchanged; no generated files appeared in the source snapshot,
and the owned test process stopped. This is a failed full attempt, preserved intact.
It includes the integrated W118 library, not a whole Willow/Pine/Cedar branch merge.

A real detached local clone of the same commit, with process-inspection/cleanup
permission, reran exactly the 46 failed node IDs: **45 passed /1 failed, 84.71s**.
The remaining source-bundle test invokes Git for NARestraints provenance; an
installed `site-packages` directory has no Git metadata. A separate detached
NARestraints checkout at the installed distribution's exact VCS revision
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691` supplies that prerequisite. All **14**
installed library/resource files are byte-identical to this source checkout.
The one residual test then **passes in 0.96s**. Source manifests are exact across
all three attempts; both real checkouts remain clean and test owners stopped.

Thus **all 46 original failures are resolved without a production fix or added
skip**, across diagnostic reruns. This is **not an uninterrupted full-suite pass**,
and it does not extend C386's result to later Cedar code. The two original skipped
modules require explicit native qualification: counted-owner control and pinned
live-nonbonded API. Existing native experiments remain separate evidence.

Original command: with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<snapshot>/src`, the
existing controller Python runs `scripts/run_tests.py full --junitxml results.xml`.
The targeted reruns use `python -B -m pytest -q -p no:cacheprovider -o addopts=
--junitxml results.xml` followed by the exact saved failed-node list. For the
source-bundle test, `PYTHONPATH` explicitly orders the NASolve `src` directory
before the exact NARestraints source checkout. The developer profile runner
currently resets that variable, so the equivalent unfiltered direct pytest command
must preserve the declared dependency-source path when needed. Do not silently
substitute a different NARestraints revision or weaken source provenance.

Plan, complete logs/XML, exact node lists, manifests and process results are in
`/private/tmp/willow-w132-full-regression/` and the retained original
`/private/tmp/willow-w128-autorefine-review/full-suite/`. These absolute locations
are local evidence, not portable execution references. Verified repository-anchored
archive: `NASolve/branch-artifacts/willow/w132-full-suite-diagnosis-2026-11-18.tar.gz`,
SHA `af9b70d88ae9853fb9a4bad3e1b7998003fb0dfbe08433c638ef7ef8752e8293`,
**476,111 bytes /26 indexed files**. The shared local software clones depend on
read-only Git objects in the original repositories; no portability claim is made.

Cedar C390 separately integrates W131's exact reporter and tests, with peer-reported
**283 source /283 installed** checks and exact cold replay. Linden verified the two
committed files match W131 byte-for-byte; this is not a new native refinement.
The next full run is deferred to the final validated integration pin, avoiding a
second hour-long gate on an intermediate revision. Final-state capture remains a
separate qualification; old preflight/metal-only records cannot be relabeled to
satisfy W131's complete canonical-pair/v2 force-state contract.


### W133 — Bind complete pair measurements to the actual final writer

Cedar C391, `8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6`, adds explicit
`counted_pair_geometry=True` to the bounded Python AutoRefine request. New v7
captures the complete intended pair recipe **after the counted owner closes**,
using the same returned native model and frozen providers. It verifies unchanged
native inventory and joins exact force sites, hierarchy and scattering to the
completed writer. The controller seals one compact capture and reuses W131's
cold reader. Preflight values and rounded PDB reinterpretation are not final-state
measurements. Old v3/v4/v5/v6 workers remain byte-identical; no ordinary default,
CLI, force target, weight or provider-selection change.

One **complete ordinary Phenix 2.2.1-6174 execution, 52.84s**, reproduces C386/C389's
written PDB and full native state exactly. The counted owner retains **15 calls**.
The separate descriptive read adds **one energy-only kernel call**: total 52→53,
energy-only 16→17, gradient calls remain 36. Its maximum observed parallelity
container grows from 12 to 14 because the report measures the complete recipe;
that is not an extra optimizer evaluation or a force change.

| Actual final pair metric | Count | RMS |
| --- | ---: | ---: |
| Pair-distance target deviation | 36 | 0.220180 Å |
| Pair-angle target deviation | 60 | 4.780349° |
| Per-plane RMS-distance summary | 14 planes | 0.118995 Å |
| Native parallelity delta | 14 | 8.893697° |

Coverage is **107 native +17 additive** requested terms across 14 pairs; **2,465**
other terms in the four observed families stay unclassified. Covalent geometry,
dihedrals/chirality, packing and density acceptance remain separate. The final
pair report is not a whole-model quality score. W131's passive original reference
and this control's actual starting coordinates differ, so these tables are **not**
a before/after improvement comparison. The matched control outcome is exact old
endpoint identity, with Rwork/Rfree **0.2251/0.2609** and an unselected **REVIEW**
checkpoint; no new structural or diffraction improvement is claimed.

Linden independently verifies all **303 Git/wheel/installed package files**, cold
report replay with process launches and record writes blocked, wrong-written-PDB
refusal, the actual state joins and exact prior counted owner. Independent
aggregation reproduces the saved native physical summaries. All **77 current /72
C386 baseline files and mtimes** remain unchanged. Rowan separately qualifies
**305 installed tests +24 subtests**, historical cold reads, v7→v6 refusal before
round allocation/process launch and preserved v7 continuation intent. The complete
unfiltered suite is now running on a separate detached C391 clone with W132's
exact NARestraints source prerequisites; it is not yet a completed full pass.

Independent command: `PYTHONDONTWRITEBYTECODE=1 python audit.py --commit
8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6`, using the existing controller environment
and host process-inspection permission. No new native run is launched by the audit.
Wheel SHA `1ace5cda8b6f53fdf3242ecd1e5c91be9c3d6f11b6b1f2e68406de26fb8dcb78`;
PDB SHA `55d28cbd19bf01874a313ff9b10b2ed4209e9e0f9b23e738b189ed5eda1082eb`;
report SHA `4428aafc7303331a7ae2ed3151cdbfc5bc29c561408fe6e25a33bd4f2f8109e7`.
Capture archive is **15,492 bytes**, SHA
`02528919cf4c00c9e053d4e0a9d9e087705a94af69c77e6014c8047f7753fc6b`.

The relocated native root is `/private/tmp/c391-final-pair-geometry-nf7n7jjf-relocated`;
its original location is absent. These paths are local provenance, not operational
replay instructions. W133 auditor and receipts are retained in the verified local
archive `NASolve/branch-artifacts/willow/w133-final-pair-geometry-review-2026-11-18.tar.gz`,
SHA `3a690080004974c907f491c9dc64a1a43e6dbd68562400a20103ecc01757ce0d`,
**28,560 bytes /9 indexed files**. Audit SHA
`169a5952398bde0794ffcc008b302e0b6cbf1f5b05e383ee2e1b5a01b3b89193`.
Raw science stays local and is excluded from Git.

This closes the bounded actual-final pair-readback gap, not S06's scientific
acceptance. Broader refinement protocols, semantic covalent/terminal ownership,
matched B10 efficacy, calibrated B06 density and W122 user-facing activation remain
open. Reuse Cedar's source graphs and Alder's explicit metal declarations when
classifying chemistry; its private origin-0 selector experiment is not a general
classifier. Existing map provenance/periodic sampling is a reuse candidate, not a
phosphate-density threshold or a new density implementation.


### W134 — Continue the ordinary run with final pair readback

One **complete Phenix 2.2.1-6174 ordinary AutoRefine continuation, 69.94s**, on
unchanged installed C391 creates `refine-002` from registered `refine-001`.
The complete parent run was copied to a fresh root and renamed before execution;
its original staging path is absent. Existing native owners retain the explicit
v7 pair report and original pair intent, rebind to the actual parent model and
inherit the prepared NARestraints PHIL. No extra-restraint file was supplied or
present in this parent: optional extra-restraint/chemistry inheritance is **not**
qualified by this control. No new MR, ReadySet, source patch or protocol change.

The bounded protocol remains one all-site XYZ cycle, ten iterations, fixed unit
weights, seed 1, one process and a 300-second process cap; ADP/occupancy/anomalous
and real-space refinement are off. The original data and Free-R assignments are
unchanged. The child is usable **REVIEW**, and `postmr` remains selected.

| Exact final-state metric | Parent | Child |
| --- | ---: | ---: |
| Pair-distance RMS target deviation, 36 terms | 0.220180 Å | 0.216024 Å |
| Pair-angle RMS target deviation, 60 terms | 4.780349° | 4.727018° |
| RMS of per-plane RMS distances, 14 planes | 0.118995 Å | 0.115785 Å |
| Native parallelity delta RMS, 14 pairs | 8.893697° | 8.505102° |
| Rwork / Rfree | 0.2251 / 0.2609 | 0.2253 / 0.2611 |
| Logged bond RMS / angle RMS | 0.025 Å / 1.772° | 0.026 Å / 1.731° |
| Clashscore | 31.53 | 33.78 |

The comparison uses successive authenticated native states, unlike the differently
started passive W131 diagnostic. Pair geometry improves slightly while diffraction
statistics and clashscore worsen. There is no matched native-only continuation
sibling, so neither attribution of all movement to the added terms nor scientific
acceptance follows. The PDB and counted owner exactly reproduce the earlier C382
second endpoint: **15 calls, 11,382 native +17 added =11,399** complete terms.
This closes the actual ordinary canonical-continuation integration gap; it does
not add a new physical repair result. Full S06 acceptance remains open.

The independent cold audit disables process launch and record writers, validates
both final reports, verifies writer hierarchy/scattering/force-site joins and
recomputes summary arithmetic from the saved native measurements. A parent PDB
is refused for the child report. All **138 descendant /77 C391 source /117 C382
historical files and mtimes** remain unchanged, all **303 installed source files**
match the qualified manifest, and all ancestor checkpoint records remain exact.
Native and controller processes are stopped. Two private setup failures are
retained: a registry-directory/file mix-up, then an assumption that unsigned
schema-2 registries carried `record_sha256`. Both stopped before Phenix; the
successful harness uses the existing supported API and privately verifies the
registry file digest. No production guard or schema was changed.

Exact commands use the existing controller interpreter with
`PYTHONDONTWRITEBYTECODE=1`: `python -B run-attempt-003.py` and
`python -B cold-audit.py`; the latter launches no native process. Scripts, plans,
process identity, successful and failed setup receipts are in the verified local
archive `NASolve/branch-artifacts/willow/w134-ordinary-continuation-2026-11-18.tar.gz`,
SHA `41f68a5293e644b8f01250c259b3d015b9e73a73130aeebb3ff7141b5b187e58`,
**17,421 bytes /14 indexed files**. Cold audit SHA
`020f721abc1d5d03f550a74a27efa333c5fbd488c2e549a27a7c1ef49c620488`;
child PDB SHA `cddd7a8bd7f333e5bced3ed795eb710cdaa9192351c2fa01e1aaff21646e4e4c`;
child pair report SHA `6192d58189e8680a78bbb45645e11a59a000cf090fb5b1fca774f90bfd497e6c`.
The complete native root is `/private/tmp/willow-v7-descendant-m20lo6hl-relocated`;
absolute paths are historical local provenance, not portable operational references.
Coordinates/reflections stay local and are excluded from Git.


### W135 — Close the full integration regression and observer coexistence

The **single unfiltered C391 full suite passes: 11,983 tests, 292 subtests and
2 existing native opt-in skips**, in **3,196.08s** pytest /3,200.09s owned wall.
The frozen source is `8ccec55b862898667e1bfb9fbb3f2cb45fee3fd6`. All **1,413
tracked files** remain byte-identical, Git is clean and the owned process is
stopped. The exact NARestraints Git source is
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`; its 14 installed library/resource
files match before and after, and its checkout remains clean. No production fix,
new skip, filtered test selection or changed source was used to obtain this pass.
The two collection skips are the existing explicit counted-owner native control
and pinned live-nonbonded-policy native qualification. Separate installed and
actual-native controls retain their own scope. This supersedes the pending
full-suite state, not W132's preserved failed earlier run or later revisions.

The exact recorded invocation is the existing controller interpreter with
`PYTHONDONTWRITEBYTECODE=1`, empty `PYTEST_ADDOPTS`, and
`PYTHONPATH=<C391 checkout>/src:<exact NARestraints checkout>`:
`python -B -m pytest -q -p no:cacheprovider -o addopts= --durations=20
--junitxml <output>/results.xml tests`. The existing owned-command runner caps
execution at 5,400s. `audit_full_suite.py` independently rechecks source/dependency
identity, process stop and XML/log counts after completion. Audit SHA
`9951b655ce205f16003013a3a6917aaf1f43e8ae88176ac51f67256af57d9830`.
The shared local clones depend on their repositories' Git objects; this is not
portable campaign qualification or permission to merge entire branches.

**C393 coexistence, unchanged C391 source:** Rowan ran one actual Phenix
2.2.1-6174 preflight (12.61s) and complete refinement (42.78s), combining v7 final
pair capture, the existing PDU B:4 chemistry observer and one added A:11/B:5
parallelity. Linden independently cold-replays the installed readers with process
launch/record writes blocked and verifies exact prior C388 partial-control PDB,
full native state, chemistry report, common counted lifetime and every MTZ array.
All **75 current /126 historical files and mtimes** and 303 installed package
sources remain unchanged. The one extra lifetime field is the new authenticated
pair capture; the original comparator's failure on that expected addition remains
recorded, with no native rerun. Linden's first auditor also correctly refused an
incorrect ordinary-parent assumption; the successful read uses the declared
low-level `c338-starting-model` parent. No registry ancestry is invented.

The extra descriptive kernel call changes total **52→53**, energy-only **16→17**,
with **36 gradient calls unchanged**. Pair coverage is **5 native +1 added**;
2,656 other four-family terms remain unclassified. The local PDU triple screen
passes, while the distinct canonical A:11/B:5 pair has distance RMS **0.954701 Å**
and directional-angle RMS **37.019027°**; Rwork/Rfree remain **0.4230/0.8360**.
These are simultaneous descriptive scopes, not a repaired structure or ordinary
chemistry-descendant qualification. The independent C393 audit SHA is
`61f29022b289333fadc76c34417b9546e513efe5281fe8f485a938769a448631`.

**Follow-up is bounded, not another repeated short control.** A planned new
explicit 100-iteration single-cycle fixed-unit scope must preserve old worker
bytes and the old 1–10-iteration guard. Freeze native-core /zero-addition /full
recipe siblings and the same data/Free-R before looking at outcomes; reuse W123
full-recipe readback at exact saved coordinates. A larger budget is not a promise
of convergence or improved Rfree. Hazel's A79/A84 private metal replay observes
identical-coordinate denominator jumps in two selected line-search failures; that
is a reason to retain actual count/raw/normalized objective observations in the
future canonical experiment, not to assume the same failure or freeze counts.
The other three selected rounding failures remain unexplained. No normalization
repair, weight policy, longer protocol or new canonical run is implemented here.

Additional saved checks: actual installed C386/C391 v3/v4/v5/v6 worker payloads
remain exact (8/8/24/24 files). Metadata-only inspection of the ordinary C391 MTZ
finds 3,157 work +176 test-index finite coefficients in unfilled maps; the filled
2mFo-DFc column additionally includes 5,011 non-observed indices. Membership alone
does not establish coefficient derivation. No FFT, fmodel, map alteration,
threshold or density-guided motion was performed; explicit generation/Free-R
policy remains a later B06 gate.

Verified local archive under the **NASolve repository anchor**:
`branch-artifacts/willow/w135-full-regression-and-coexistence-2026-11-18.tar.gz`,
SHA `e23a140a794267be35d657387db1752e3a61b9ad2192dd9bc075cfda8176f357`,
**269,662 bytes /24 indexed files**. It retains the complete suite plan/log/XML,
source manifest, exact prerequisite receipt, cold auditors, failed audit setup,
legacy/map/selected-contact readbacks and a clearly planning-only next-control
record. Raw models/reflections/native trace arrays remain local and excluded from
Git. No API, schema, compatibility/default or migration change in this update.


#### W135 closeout follow-ups

Cedar C394 `5ccda59a585a0bb93da4554e61f50e7aacbce64b` subsequently fixes only
native log-stage suffix digits (`1_realsrl2`). Independent current-source versus
installed-C391 cold parsing of both retained C392 logs and the frozen table
changes only missing bond/angle summaries to **0.078 Å /2.744°**. All other parsed
fields, source bytes/mtimes and v3/v4/v5/v6/v7 worker payloads remain exact.
Rowan's strengthened regression fails before; 64 affected tests +31 subtests and
148 smoke tests +6 subtests pass. No new wheel or native execution was needed for
this parser-only change. C391's full-suite pin remains distinct. Local review:
`NASolve/branch-artifacts/willow/c394-reporting-review-2026-11-18.json`, SHA
`38fc45f5c607bc72fef9b18ffca1c7b4d839c587924bf0885bdb5071ef8fcda9`.

Read-only bundled-source inspection clarifies the normalization count: the
nonbonded contribution is `simple.size()+asu.size()`, including potentially
zero-energy neighbor candidates; it is not a count of nonzero forces. The
standard prolsq residual/gradient vanish beyond their repulsive support, but the
proxy still counts. Pair lists are buffered and cached relative to construction
coordinates, supporting a history-dependent candidate-count mechanism. This does
not identify the individual proxy changes in A79. A57/A58 already established the
geometry-only same-site nonbonded count change and a separate fixed-denominator
control; reuse that evidence. Counting only currently active contacts would also
create a coordinate-dependent denominator and is not an automatic fix. No library,
cache, evaluator or production normalization was changed. Versioned source hashes
and exact locations are in
`NASolve/branch-artifacts/willow/nonbonded-count-source-review-2026-11-18.json`, SHA
`0f3763a950d9e2a240c5013579ef087ec94dd3aa16b6e9956845bf63b194eec7`.

After verifying all 1,405 tracked files against its source manifest and sealed
W132 evidence, the obsolete **72 MB C386 software clone** was retired. Source
repositories, installed packages, native runs, data, failures and test receipts
were retained; the reusable exact NARestraints source clone remains. The C391
software clone was subsequently verified and retired at W136 closeout below.
The separate retirement receipt is
`NASolve/branch-artifacts/willow/w132-c386-clone-retirement-2026-11-18.json`, SHA
`29c9e9e0e152d04985419e6b54fea04dad68e5ea501ce1d0a63104e0eb38d045`.


Cedar C395 extends the passive observation to each actual XYZ weight-trial
reporting object. One fresh Phenix **2.2.1-6174** execution (5.94 s preflight,
276.54 s refinement) retains the exact C392 model, full native chemistry state,
1,962 correction calls, all 3,239 MTZ rows and the complete public weight receipt.
Independent cold replay resolves the frozen simple PHIL selections through literal
PDB columns, matches **141 unique source requests** with no missing/ambiguous
assignments, and reconstructs all **48 trials** on **855 heavy atoms**. The single
stable inventory contains 51 declared pair distances, 84 pair angles and six
protected terminal-phosphate angles; 956 bond and 1,462 angle terms remain
**unclassified**. This is actual reporting-model evidence, not W131 complete
force-site correspondence or a general chemical classifier.

The 51 pair distances contribute **97.80–99.79%** of the unweighted squared
bond deviations in the five selected trials. This is a property of the pooled
RMS screening statistic, **not** the fraction of energy or force. It motivates a
separate, predeclared private eligibility experiment that omits only source-matched
pair terms from the screening means while retaining terminal protection, unknown
terms and all optimizer forces. No such selector is activated by this review.
The independent physical-delta replay agrees within **2.28e-13**; 48 current,
65 baseline, 40 failed-setup and 308 installed-package files/mtimes stay unchanged.
The first observer attempt, which assumed a non-None reporting-energy cell,
remains preserved. No native execution occurred during Linden's review.

Exact cold command (the retained runner is an identical copy of the scratch
runner used):

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B /private/tmp/willow-c395-review.py
```

Local NASolve-anchor receipt
`branch-artifacts/willow/c395-trial-membership-review-2026-11-18.json`, SHA
`004accc05f46d6d3dfac408178f42b6f4995137c8cb82b9f8291dcaad025c0e1`;
retained runner `branch-artifacts/willow/runners/c395-trial-membership-review-2026-11-18.py`,
SHA `97c9b853feb867d33928a5b9d316640206af355d005e206137d1dfee02d58133`.
These references complement the sealed W135 archive; they do not rewrite it or
claim a portable campaign. Documentation/evidence only: no API, schema, default,
migration or scientific-acceptance change, and raw crystallographic files stay
local and excluded from Git.


### W136 — Separate trial screening from optimizer normalization

**2026-11-18, coordinated with Rowan and Hazel.** Two independently bounded
private diagnostics answer different questions. Linden reviewed the source and
sealed results without launching another native job. No production source,
selector, count policy, force definition or scientific-acceptance gate changes.
C395's actual reporting-object/source-membership qualification is retained above.

| Diagnostic | Changed quantity | Result and limitation |
| --- | --- | --- |
| Rowan C396 | Only the bond/angle means used by native weight eligibility: omit the 135 exact source-matched pair terms, retain six protected terminal angles and all 2,418 unclassified terms | Actual choices change; final logged Rwork/Rfree **.2125/.2265 → .2277/.2444**, worse. PDU remains REVIEW. This is not a successful repair or a universal covalent classifier. |
| Hazel A85 | Only the returned optimizer geometry objective **and gradient**, anchored to each minimizer's initial count 11,170; retain all raw terms, data contribution and the same private A71 selector | Dynamic **9 lower-bound +12 rounding errors** becomes fixed **16 rounding errors +5 iteration limits**. Final Rwork/Rfree **.297570/.314876 → .296857/.312645**; modest improvement without convergence or scientific acceptance. |

**C396.** One actual Phenix **2.2.1-6174** control, 5.90 s preparation /250.37 s
refinement, uses the same original model, restraints, observations and Free-R.
Preflight semantic state and the first trial's full sites/deviations match C395.
The changed trajectory has **40 trials**, not 48; its 2,559-term reporting
inventory is unchanged. Independent arithmetic reconstructs every pooled and
retained mean, then replays the exact native criterion, fallback and tie rules.
The retained eligibility inventory is **956 bonds /1,468 angles**. Searched
cycles 2/4/5 have 15/9/10 eligible trials; cycles 1/3 are native single-trial
choices, not proof of meeting every eligibility threshold. Selected weights are
78.65254, .5, .556593, .0852549 and 1.0. All 3,239 output HKL/Free-R assignments
remain exact; the final model changes. Final native **pooled** bond/angle RMS is
**.083 Å /1.972°**, distinct from the restricted eligibility means. The independent
physical-delta reconstruction agrees within **2.28e-13**; 49 current and 48 C395
files/mtimes remain unchanged. Native forces and normalization were not changed
by the eligibility hook. No threshold relaxation or best-of-results adoption.

**A85.** The dynamic baseline exactly reproduces A71's first-cycle trials,
choices and stopping records. Each sibling has **21 minimizers** and selects
trial 7, weight 2, with 13 eligible trials under the unchanged private origin-based
A71 selector. That selector is not general chemical classification. There are
4,598 /6,040 actual evaluator returns, distinct from the native-reported
4,306 /5,720 function evaluations. The first **27 evaluator inputs/data/raw
terms** match. At return 27, native count **11,237** versus anchored **11,170**
first changes the returned objective/gradient; later trajectories diverge.
Nine dynamic same-coordinate count changes explain their objective jumps within
**6.67e-16**. Fixed has no count-changing same-coordinate repeat: the corresponding
jump maximum is **null**, not a measured zero. Saved gradient norms/selected atom
components are checked; unsaved full-vector identity is not asserted.

Original input bytes, 1,151 reflection identities /59 Free-R flags and all HL
coefficients are exact. The final fmodel amplitude hashes differ by an allowed
common **F/sigma scale 1.0012296868232102**, verified using the existing
`metal.fdp.audit_reflections` reader (maximum relative residual **2.22e-16**).
An initial cold assertion of exact final amplitude hashes correctly refused;
using the established scale-aware reader resolves the scope distinction without
rerunning refinement. Native summaries/monitors retain dynamic normalization.
Both native executions use Phenix **2.2.1-6174**; owned launcher durations are
**544.17 /715.37 s**, distinct from inner refinement timing. Cold review preserves
67 dynamic /67 fixed /65 A71 baseline files and mtimes.

Exact cold commands:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B /private/tmp/willow-c396-review.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B /private/tmp/willow-a85-review.py
```

Both reviewers block subprocess creation. Retained runners under the NASolve
anchor are `branch-artifacts/willow/runners/c396-eligibility-review-2026-11-18.py`
and `branch-artifacts/willow/runners/a85-pair-cold-review-2026-11-18.py`.
Their review receipts have SHA
`1d04f09ba8935905a8aa128680113839aebf52638d72de616d2863f87a19645c`
and `f8d749da733cfbaaf6fe7aff9eec6d63e2884ecba5ce5b20b2e8f24338f4d7fa`.
The A85 receipt's selector wording was corrected before sealing; numerical audit
results are unchanged. All seven source-review/receipt/runner files are indexed
in the separate **14,041-byte** archive
`NASolve/branch-artifacts/willow/w136-separate-diagnostic-audits-2026-11-18.tar.gz`,
SHA `f31128093a52331f66392b29ee536b7f6639d58b646a41ad695fa2cab37c7238`.
The archive excludes raw native coordinates, reflections and maps and is not a
portable campaign. No supported API/schema migration or ordinary behavior change.

**Next:** use these diagnostics to specify observations, not to install their
private policies. Preserve the old ten-iteration protocol while qualifying the
separate longer canonical native-core/zero-addition/full-recipe control. Standalone
bending remains unnormalized; native refinement's count history must be observed
without extra energy/cache queries. Physical geometry, healthy/wrong-contact B10
controls, density calibration, general bending and Pine recuts remain open.


W136 closeout also confirms all **18 shared TopoStitch modules** are byte-identical
between Willow and current Cedar. Cedar's only source/test changes after the
frozen C391 full suite are the separately reviewed C394 log parser/regression;
this is not a whole-branch merge or a claim that later source had another full run.
All three working branches were clean at the recorded check. The completed C391
software-test clone was also retired after all **1,413** tracked hashes, clean Git,
stopped suite and archived evidence verified, releasing **72.4 MB**. The exact Git
commit, original repositories, native installed package, all scientific runs and
failed attempts remain. Retirement receipt SHA
`a9aae36d0e5d9ac8895aea0c9b25a3f46c51d63731df31f052f0b3860b3d581e`.

Static closeout verifies **12 Linden /25 Rowan /12 Hazel** local report links.
The selected scientific PNGs were visually inspected; the PDU displacement plot
now explicitly labels its expanded vertical scale. Rowan's six-file consolidated
report links the unchanged two-file Linden report and Hazel's separate four-file
normalization report. There is no browser-layout claim or duplicated raw model/map.
The combined source/report receipt is
`NASolve/branch-artifacts/willow/source-report-closeout-2026-11-18.json`, SHA
`1a930e499bcb4d778c8b3a4da9a764a8d6356c7a4168584423ea68b694de9bd9`;
the static link receipt SHA is
`450c2fe81ea55e93bfcbeac99ba410ac9d4398270c70adb038ec6f063b830610`.


### W137 — Audit actual-state derivatives and ordinary chemistry lineage

**2026-11-18.** Independent cold review of Rowan's C397/C398 diagnostics
reproduces the exact first **2,779 actual evaluator returns** from Hazel's A85
fixed-normalization control. This is one pre-ADP state, not iteration 2,779.
All original physical terms remain; the fixed denominator is 11,170. The scope
retains the private A71 eligibility selector and is not a canonical repair test.

| Same state and declared 13 directions | Raw geometry | Diffraction | Combined |
| --- | --- | --- | --- |
| C397 FFT | 13/13 consistent | 0/13 consistent | 0/13 consistent |
| C398 direct structure factors | 13/13 consistent | 13/13 consistent | 13/13 consistent |

Consistency requires agreement at two adjacent sampled steps (10⁻³, 10⁻⁴,
10⁻⁵, 10⁻⁶ Å). Absolute/relative tolerances are 10⁻⁴/10⁻⁴ for raw geometry
and 10⁻⁷/10⁻⁴ for diffraction/combined objectives. Both runs retain the same
11,143-proxy inventory, coordinates, non-coordinate state, likelihood core,
scales, masks and raw geometry. C398 changes only FFT to direct; its separate
FFT reproduction is exact. All 13 direction vectors are the frozen C397 vectors,
including its FFT combined-gradient direction, not direct steepest descent.
The direct baseline target is higher by 0.00017266277904681715; that numerical
offset is not deterioration or improvement of a refined structure.

C397 performs 106 diagnostic evaluations. C398 performs 106 direct evaluations
plus one FFT reproduction. First/restored targets repeat exactly in both;
C398 retains the full repeated vectors and cold review verifies zero gradient
error. C397's repeated vectors were asserted live but not saved, so only the
original full baseline and saved target repeats are independently recoverable.
Combined-gradient closure differs by at most 8.67×10⁻¹⁹. C397 preserves 34 current
and 35 original refinement files; C398 preserves 38 and 35, including mtimes.
Small negative-FFT-gradient steps lower the objective in both calculations;
these are not the actual L-BFGS search direction and do not establish why the
original optimizer stopped. No optimizer resumes, final model is produced or
production algorithm is adopted by either diagnostic.

Actual external consumer: **Phenix 2.2.1-6174**. C397's replay plus stopped
diagnostic takes 340.05 s; C398 takes 333.43 s. These are complete bounded
diagnostics, not complete refinements. Preserve the unlaunched C397 candidate
whose mapping fingerprint initially omitted values, and C398's first stopped
309.97 s attempt: its helper expected bare mmtbx settings, while Phenix supplied
`taam_verbose=0`. The corrected fresh attempt validates the actual typed scope;
no probe ran in the failed attempt and no scientific result was overwritten.

**Ordinary chemistry boundary.** The real C303 registered preparation supplies a
1.607 Å C5M–C5B target; C327 separately qualifies 1.470 Å at unchanged sigma
0.020 Å. Their models and ordered five PHIL inputs are byte-identical. The
independent installed-C391 reader checks both owners with subprocess/publication
blocked, preserving 1,234 C303 and 141 C327 files. C327 is a standalone request,
not an adopted ordinary checkpoint. C393/C338's diagnostic parent label supplies
no registry authority. A fresh checked ordinary construction can freeze the
explicit bond-pair choice, qualify it and publish a new REVIEW root. The existing
alternative-preparation API accepts only later attempts of the same frozen
request; it cannot change C303's chemical intent in place. Keeping C327's exact
already-prepared model/PHIL would need an explicit source-bound reprepare owner,
not a manual import or retroactive producer claim. No such owner was added.

**Next bounded code gate.** Rowan delegated the longer canonical control to
Linden. Detached review candidate `d8656b2212ec1777e3da5f1979ac2a766fc71563`
on clean Cedar `653587b9` adds only explicit configured cap 100, v8/cycle-v2 and
mandatory final pair capture; old v3–v7 payload bytes and v1 bounds stay exact.
334 focused tests pass; 35 final pin/lifecycle checks pass. A relocated installed
wheel matches 304 packaged resources and passes the same 334 tests (77.04 s),
dependency checks and root/AutoRefine/PostMR command helps. The first installation
audit wrongly expected three historically unpackaged provenance JSON files;
its failure remains recorded. No packaging or production fix was needed.
The full candidate suite is a separate running gate; the last completed full
baseline remains C391. No native v8 experiment, merge or new scientific approval
is claimed here. The matched native/zero/full control still needs passive actual
stopping/count history. C391's 12 core pairs provide a genuinely native-covered
nonempty zero-addition subset; only the two selected end pairs contribute the
17 additions. Preserve that subset/full-intent distinction rather than override
provider selection or invent an empty recipe.

**Reproduction and retained evidence.** Cold commands use
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B`:
`willow-c397-review.py ROOT RECEIPT`, `willow-c398-review.py ROOT RECEIPT`, and
`PYTHONPATH=/private/tmp/c391-package-9d301ocz/relocated
willow-chemistry-lineage-review.py`. Exact reader sources, receipt hashes,
historical roots and limitations are sealed locally at declared NASolve anchor
`branch-artifacts/willow/w137-actual-state-and-lineage-audits-2026-11-18.tar.gz`
(10,601 bytes, seven indexed files plus manifest), SHA-256
`d59ab2764fcef1b880bc8086433f1d5ca517dcc50976413b27b8b2f0710c41b3`.
No raw models/maps/data are committed. The archive is evidence, not a claim that
the original native runs are portable. S04/S05/S06 and P01/P02 remain partial;
density calibration, B10 efficacy and altered-arm B09 success remain open.


### W138 — Qualify the explicit longer coordinate control

**2026-11-18.** Candidate `d8656b2212ec1777e3da5f1979ac2a766fc71563`
on Cedar `653587b9` passes focused, installed, full-source and actual ordinary
native checks. Its opt-in `counted_protocol="counted-xyz-fixed-unit-100-v1"`
requires `counted_pair_geometry=True`, one all-site XYZ cycle, fixed unit
weights, process count 1 and seed 1. It uses explicit
`round-local-counted-execution-v8` / `prepared-counted-refinement-cycle-v2`.
The configured maximum is exactly 100; it is not a measured iteration count.
Neither default activation nor scientific acceptance follows.

**Before/after and compatibility.** The earlier ordinary counted scope allowed
only the bounded ten-cap control. The new explicit route admits cap 100 and
requires actual final writer/geometry capture; inherited v8 requests cannot
silently downgrade. Unsupported cap/seed/missing-capture requests refuse.
Old v3–v7 payload bytes, old scope/seed semantics, defaults, explicit paths and
native algorithms remain unchanged. A frozen v7 helper resource preserves old
worker hashes. No FFT/direct, normalization, force or weighting policy changes.
The unchanged 18 Willow shared modules are not recopied into Cedar by this work;
Rowan owns the single candidate integration after exact source matching.
Published Cedar integration `4f7aeb84b8762b3bd4ebcc1741c6b1116443632a` retains the exact
qualified source/tests/package configuration; an independent manifest check
records that relationship rather than claiming a second full-suite execution.

Changed candidate files: `autorefine.py`, `refinement_counted.py`,
`refinement_parallelity.py`, `cif_counted_phase.py`, `cif_counted_refinement.py`,
`data/refinement-runtime-v7-sources.json`, the focused counted-control tests and
architecture/changelog documentation. New execution/scope identifiers are opt-in;
existing runs need no migration and acquire no retrospective authority.

**Validation.** Two initial regressions fail before implementation. The affected
source suite passes 334 tests (72.36 s); 35 final pin/lifecycle checks pass (2.46 s).
The relocated wheel passes the same 334 tests (77.04 s), dependency check and
root/AutoRefine/PostMR helps, with 304 exact packaged resources. The build-source
copy and old install directory are absent during installed checks. The retained
first audit erroneously expected three historically unpackaged provenance JSONs;
this was an audit correction, not a packaging change.

The complete unfiltered pinned suite reports **12008 passed, 2 skipped, 293 subtests passed in 3581.07s (0:59:41)**.
The owned process has stopped, tracked source hashes remain exact and Git is
clean. Exact command uses `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=/private/tmp/nasolve-willow-long-control/src:/private/tmp/willow-w132-full-regression/narestraints`,
and `/private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider
-o addopts= --durations=20 --junitxml <declared-evidence-root>/results.xml tests`.
NARestraints is pinned at `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`.
The archive retains exact expanded commands, environment, XML/log and complete
source manifest. This qualifies the candidate pin, not an unaudited later branch.

**Actual native mechanics.** A complete **Phenix 2.2.1-6174** ordinary run takes
280.319 s. The existing registered `postmr` remains selected; the fresh
`refine-002` child is usable but unselected `REVIEW`. Both short and long controls
start from the same existing diagnostic PostMR parent; this is not fresh MR or
fresh ordinary chemical preparation. Original model/recipe intent, observations,
Free-R/core inputs and existing rounds remain unchanged. The actual prepared
PHIL/native command is checked before launch, allowing only the declared cap
change and exact observation-path rebasing. Native scope, model writer and
final measurements bind to the actual child.

The run records 85 counted geometry calls, **not optimizer iterations**. Last
native count is 11,308 plus 17 additions =11,325. Actual stopping/history is a
separate matched-control gate. Cold review launches nothing and preserves all
77 original and 138 long-root files plus 304 installed resources. Original full
14-pair intent includes 107 native-covered and 17 additive requested terms;
2,465 observed terms in four restraint families remain unclassified.

| Same-start endpoint observation | Short cap 10 | Longer cap 100 |
| --- | ---: | ---: |
| Pair distance RMS (Å; 36 terms) | 0.220180 | 0.199943 |
| Pair angle RMS (°; 60 terms) | 4.780349 | 3.083988 |
| Pair plane-angle RMS (°; 14 pairs) | 8.893697 | 4.799671 |
| Selected GC plane angle (°) | 17.775729 | 6.287164 |
| Native log Rwork | 0.2251 | 0.2271 |
| Native log Rfree | 0.2609 | 0.2609 |
| Native pooled bond RMS (Å) | 0.025 | 0.029 |
| Native pooled angle RMS (°) | 1.772 | 1.489 |
| Native clashscore | 31.53 | 24.77 |

Pair geometry is the full-precision actual final state. R values retain their
reported four-decimal precision. Rounded written PDBs differ by 0.144008 Å RMS
over 855 atoms, maximum 0.755434 Å at B:111 OP2, without superposition. Better
pairing does not establish better diffraction: Rfree is unchanged, Rwork and
pooled bond error worsen, and selected AT contacts remain strained. Both
endpoints are restrained; this is not matched native/zero/full efficacy,
proven convergence, accepted bending or backbone closure.

**Visible science and next gate.** Five local files at GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-18_long-control` provide a report, machine
provenance, two display PDBs and ChimeraX script. The exact declared image
`-x+y+2/3,-x+1/3,z+1/3` maps C to display-only X without lattice wrapping;
original coordinates are unchanged. The viewer shows actual movement, four
fitted base planes and five contact guides per model, without alignment or
magnification. ChimeraX 1.12 headless checks pass (two 1,140-atom models);
all five local links and checksums validate. No browser-layout check is claimed.
Display derivatives omit ANISOU/connectivity and are not refinement inputs.

Rowan owns the separately frozen C400 native/core-only-zero/full matrix and
passive actual evaluator/stopping history. Do not duplicate that experiment or
change the product candidate to add a private observer. Native/zero should
reproduce one another; full versus core deliberately changes the objective.
Density/packing, terminal and backbone chemistry, B10 efficacy, altered-arm B09
and W122 user-facing activation remain open. No new covalent symmetry link is
drawn and no Rfree-driven tuning is authorized.

**Retained attempts and evidence.** The first harness never launches because
an audit compared macOS `/var` versus `/private/var` spelling. A fresh second
attempt stops in 3.04 s before native refinement because the comparison guard
did not normalize its two declared observation CLI paths. A third fresh attempt
fixes only that guard, validates their exact request identities and completes.
All attempts remain; no run is overwritten or product workaround introduced.
Local archive `branch-artifacts/willow/w138-long-control-mechanics-2026-11-18.tar.gz` has 57 indexed
files plus manifest, 398,651 bytes, SHA-256
`2c31fde0aaf2f9153e1771f1a3053e00e7d8253bf2b05e664e0a3583a2bd5f23`. It includes candidate patch, runner sources, failures,
commands and receipts; raw PDB/map/MTZ data are deliberately excluded and remain
at their original declared local anchors. The archive is evidence, not a claim
of executable run portability. Human/agent docs are the only Willow changes.


### W139 — Measure matched sticky-end benefit without claiming repair

**2026-11-18.** Rowan's C400 joins the retained completed native/full controls to
one fresh zero-addition control. Native-only and genuinely zero-addition runs
reproduce each other's complete returned-evaluator records, accepted-step and
stopping history, model/scattering/Fcalc and reflection arrays/metadata exactly.
The observed full run reproduces W138's ordinary full endpoint, prepared state,
counted lifetime and reflections exactly. Hazel independently verifies the union
in **82 cold checks**, with no native evaluations. This qualifies the passive
observer composition and zero control, not optimizer convergence.

Linden applies the **same full fourteen-pair frozen PHIL** to all three written
PDBs: 36 distances, 60 angles, 14 joint fitted planes and 14 inter-base plane
angles, using the exact unwrapped crystal image. Measuring the unrestrained end
pairs in the native control does not apply those restraints to that control.
All physical values below are rounded-PDB measurements; the full arm agrees
with its full-precision final native report within declared serialization
tolerances (0.002 Å for distances/plane RMS, 0.08° for angle/parallelity RMS).

| Common endpoint measurement | Native / zero addition | Full pair intent |
| --- | ---: | ---: |
| Pair distance RMS (Å) | 0.247180 | 0.200020 |
| Pair angle RMS (°) | 4.785545 | 3.085463 |
| Joint plane RMS (Å) | 0.113594 | 0.086912 |
| Pair plane-angle RMS (°) | 8.870410 | 4.800041 |
| Selected GC plane mismatch (°) | 27.298448 | 6.298366 |
| Selected AT plane mismatch (°) | 8.854420 | 4.591776 |
| Final Rwork | 0.2267 | 0.2271 |
| Final Rfree | 0.2613 | 0.2609 |
| Final PDB clashscore | 23.27 | 24.77 |
| Actual optimizer iterations | 75 | 73 |
| Native function-evaluation counter | 80 | 76 |
| Actual evaluator returns | 86 | 82 |

GC contacts change from 3.314310/3.125281/2.823165 Å to
2.981375/2.969891/2.826787 Å. AT contacts remain long at 3.258241/3.375554 Å
against the requested 2.80 Å target. Pair alignment improves locally, but full
Rwork and clashscore are worse than the matched control. Rfree is lower by
0.0004 at log precision, with no statistical-significance claim; both final
values remain worse than the common initial 0.2599. All endpoints remain
diagnostic and unselected; no overall repair, backbone closure or large bend is
accepted. Native pooled bond RMS is 0.029 Å in both cases.

**Actual stopping and numerical boundary.** Both optimizations stop with the
line-search lower-bound `stpmin()` error before their 100-iteration cap. Full
returned evaluations 76 and 82 have identical coordinate/non-XYZ/data states
and raw geometry 2637.52902110223, but complete count changes 11,409→11,325.
The geometry target changes 0.2311796845562477→0.23289439479931393, entirely
reproduced by the changed normalization. These counts include candidate
nonbonded terms; they are not active-force counts. Hazel independently checks
this recorded scalar discontinuity. It does **not** prove that normalization is
the sole cause of every line-search failure or authorize an immediate policy
change. A stable numerical objective is now the next explicit qualification
boundary before larger motions; reuse C397–C399/A85 evidence rather than repeat
equivalent derivative/restart or iteration sweeps.

**Failures and summary correction stay visible.** The first zero fixture removed
the two selected pairs but retained their effective-library record. Preflight
correctly refused it; no zero refinement launched there. The existing recipe
compiler rebuilt the twelve unchanged core pair definitions and their matching
library fingerprint in a fresh directory. Full/native completed results were
reused, never rerun. Fresh zero completes in 213.183 s. All native executions use
**Phenix 2.2.1-6174** and are stopped.

The immutable C400 runner supplied only the native log to the statistics reader;
its clashscore 32.28 belongs to the **initial** model. Rowan's separate cold
amendment supplies log plus final PDB, matching ordinary AutoRefine, and binds
the parser/log/model hashes. Linden independently reproduces the amended final
scores 23.27/24.77; all other statistics are unchanged. Original receipts remain
intact. W138's short/long clashscores already came from the ordinary log-plus-PDB
path and are final-model values; their comparison is a different experiment.

**Validation and artifacts.** The common physical reader blocks subprocesses,
preserves all 172 original-matrix and 75 fresh-zero files plus 304 installed
resources, and requires exact native/zero PDBs/measurements. Command:
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B
branch-artifacts/willow/runners/w139-c400-geometry.py` from declared NASolve root.
No source/API/schema/default or migration changes occur in W139; no new test
suite or native calculation is needed for this cold evidence/documentation step.
The W138 pinned full/installed/source-integration gates retain their own scope.

The current local science view is GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-18_matched-sticky-ends/review.html`.
Four new files reuse W138's full display PDB through a relative checksum-bound
reference. ChimeraX 1.12 headless validation checks both 1,140-atom models,
four child planes and five contact guides per model; five links/checksums pass.
No browser-layout check or graphic motion exaggeration. Earlier checkouts remain
intact; raw models/maps/MTZ/trajectories are excluded from Git and from the compact
cold-review archive. The latter is evidence only, not executable-run portability:
`branch-artifacts/willow/w139-matched-pair-review-2026-11-18.tar.gz`, 27,720 bytes, 13
indexed files plus manifest, SHA-256 `8a42558a55f4e4990d255dbfcc258f0e927cb96ec21826b657e020248fdbd339`.

S04/S05/S06 and P01/P02 remain partial. The next bounded design must address the
recorded objective discontinuity with an explicit invariant and matched controls;
it must preserve physical forces/repulsion, original inputs and independent
diffraction/geometry review. Broad normalization changes, automatic sticky-end
enforcement, density calibration, geotest B09 and wider B10 efficacy remain open.
No more native sweeps are scheduled for this work window.

## W140 — Audit backbone response and saved density

**2026-11-18; read-only scientific review, not another refinement.** W139's
matched C400 native/full outputs and native definition archive are reused.
The actual scientific execution remains Phenix **2.2.1-6174**, published Cedar
`4f7aeb84b8762b3bd4ebcc1741c6b1116443632a`; this audit adds no forces, coordinates,
map coefficients, covalent connection, checkpoint selection or runtime schema.
The W34 public 8D93 STARANISO amplitude cohort is retained: 3,333 observations,
176 original free indices, 2.9608 Å. W115's explicit working-cell declaration and
W118-compatible derived-model lineage remain; this is not a fresh deposited-model
refinement or proof that the deposited structure requires stitching.

### Backbone support and independent checks

The common actual native definition digest is
`123ae22218806e4fd0dbea967b82f1a763d39f6e9238963e97717ef9b25e50ff`.
Explicit canonical residue/atom identities select 494 sugar/phosphate bonds,
42 glycosidic bonds and 732 sugar/phosphate angles. This is a descriptive support
set, not a general covalent classifier or semantic weight selector. Existing
native O3′–P records define 38 links; residue-number adjacency does not invent
links. All selected supports use identity images; none is silently omitted.

The one-recorded-link neighborhood around A101/A102/C101/C102 adds A103/C103:

| Measurement | Native-only | Full pair terms |
| --- | ---: | ---: |
| Nearby sugar/phosphate bond RMS deviation, 66 terms / Å | 0.005764 | 0.005993 |
| Nearby sugar/phosphate angle RMS deviation, 100 terms / ° | 2.748014 | 2.765356 |
| Nearby glycosidic bond RMS deviation, 6 terms / Å | 0.006021 | 0.005000 |
| Elsewhere sugar/phosphate bond RMS deviation, 428 terms / Å | 0.004146 | 0.004126 |
| Elsewhere sugar/phosphate angle RMS deviation, 632 terms / ° | 1.808002 | 1.821663 |

The four end residues have sugar/phosphate RMS movement 0.080–0.113 Å and base
RMS movement 0.190–0.341 Å. A103/C103 backbone RMS movement is about 0.023/0.025 Å.
Existing nearby O3′–P distances remain 1.608–1.617 Å. All 126 ordered sugar
signed-volume signs survive source/native/full. These are comparative signs,
not absolute stereochemical or complete sugar-pucker assignments.
C103 OP2–P–O5′ is already 96.054° in the source, then 94.575°/93.803° against
108° native target. The full endpoint changes the native-control value by about
−0.77°; it does not create the pre-existing feature.

Independent parsing of actual native geometry reports verifies **3,804**
source/native/full bond/angle measurements with fixed PDB/report serialization
allowances (0.002 Å, 0.12°). Actual maximum discrepancy is 0.001285 Å/0.077949°.
A separate cross-product/atan2 calculation verifies **342 torsions**, maximum
2.84e−14°. All 172 C400 files and 304 installed resources remain unchanged.
The old installed Cedar package lacks the Willow preview module; the reader
explicitly adds the pinned Willow namespace only for existing angle/torsion
helpers and records all loaded source hashes. This is not a newly qualified
combined installed package. Setup failures before completed measurements are
retained in the receipt; no native fit or scientific input was changed.

### Saved coefficients and interpretation

A complete **read-only Phenix FFT/sampling execution**, not a dry-run or
refinement, reuses Hazel's unchanged `Alder/runners/A72_maps.py` periodic sampler.
The ordinary ML maps are explicitly distinct from the maintained metal MLHL
capture protocol. Exact PDB/MTZ/effective-parameter hashes and previous reflection
array metadata bind both endpoints. The native typed master reads the saved
PHIL; no fmodel, new structure factors or new coefficients are calculated.

- Columns: `2FOFCWT_no_fill,PH2FOFCWT_no_fill` and `FOFCWT,PHFOFCWT`.
- Each has 3,333 finite complex coefficients, including all **176 test indices**.
  Saved policy is unfilled, isotropized, unsharpened, `exclude_free_r_reflections=False`.
- Four maps ×456 canonical sugar/phosphate atoms retain signed samples at each
  endpoint's own coordinates and the common original source coordinates.
- Whole-cell sigma scaling, FFT resolution factor 0.25, 144×144×135 grid;
  periodic whole-lattice translation agrees within 1.23e−13.
- The inherited 1.5 Å sphere/0.5 Å spacing (123 probes) is an uncalibrated sampling
  neighborhood, not a phosphate mask, patch classifier or motion prescription.

C102 P Fo–Fc is −6.641→−6.677 sigma at own positions and −6.597→−6.591 at the
common source position. OP2 is −6.158→−6.241 at own positions. Its ordinary
2mFo−DFc support remains weak (P 0.976→0.957; OP2 −0.072→−0.095 sigma).
Occupancies are 1; P/OP1/OP2 B factors remain 214.15/180.49/193.25 Å² in these
coordinate-only trials. The persistent feature does not distinguish coordinate,
occupancy/ADP, processing or other model error. Per-map sigma differences are
not absolute density/electron changes, and model-assisted maps including free
indices are not independent validation or a work-only search target.

Small Rwork/Rfree/clashscore changes are **context, not rejection thresholds**.
Local pair benefit, backbone response, density evidence and numerical stopping
are separate observations. The next S06 step is to specify the shared ordinary
ML/saved-map provenance/sampling boundary with Alder, then calibrate descriptive
backbone features against healthy/noisy/displaced controls. No automatic density
threshold, coordinate change or new numerical-policy matrix follows.

### Commands, retained evidence and inspection

Run from the NASolve artifact anchor with the qualified Python 3.12 interpreter
`/private/tmp/willow-w94-pivot/env/bin/python` (historical environment provenance):

```text
PYTHONDONTWRITEBYTECODE=1 <python> -B branch-artifacts/willow/runners/w140-backbone-review.py
PYTHONDONTWRITEBYTECODE=1 <python> -B branch-artifacts/willow/runners/w140-backbone-verify.py
PYTHONDONTWRITEBYTECODE=1 <python> -B branch-artifacts/willow/runners/w140-saved-density.py
```

The density controller owns the exact Phenix bundled-Python command and stopped
process receipt. Attempt 01 failed before sampling because untyped PHIL extraction
returns tokens and loses repeated scopes; its runner/log/process records remain
in `w140-saved-density-attempt01.zip`. Attempt 02 uses the native typed master and
completes. The installed native profile is 2.2.1-6174; its optional version API
returns `(None,None)`, so executable/module hashes provide additional provenance.
No complete native refinement is attributed to these read-only checks.

A separate ChimeraX **1.12** headless execution of
`branch-artifacts/willow/runners/w140-viewer-check.py` passes two 1,140-atom
models, four child planes/five contact guides and six highlighted atoms each.
The first process could not acquire the normal application cache lock in the
sandbox; the authorized retry succeeds. Ten local packet references/links and
unchanged input hashes pass. Browser-layout validation is not claimed.

The three-file local science view is at the GitHub workspace anchor,
`ScienceCheckouts/Linden/2026-11-18_backbone-density/`. It reuses the W139 script
and prior coordinate files through checked relative references; no PDB/map copies
are added. No map surfaces are displayed. Keep sibling folders together.

The byte-verified local archive at the NASolve anchor,
`branch-artifacts/willow/w140-backbone-density-2026-11-18.tar.gz`, contains 18
indexed receipts/runners plus manifest, 406,684 bytes, SHA256
`1b8e1bc307c4d1d0d5d64b798e26a55c695c45d07503c3a879236cfb45104a8b`.
Detailed measurements and failed setup attempts remain local. Raw scientific
payloads are deliberately excluded from Git. Runtime APIs, artifact schemas,
CLI/defaults and migration requirements are unchanged. Documentation checks
regenerate the human roadmap, validate its machine source and check diff/link
consistency; no new full suite is needed for this documentation-only update.
The separately running exact C402 full qualification is not a W140 science PASS.


## W141 — Qualify the shared periodic grid sampler

**2026-11-18.** Hazel's Alder `9c4c3b050fedd42f6be1fd6f26aa03873709bd76`
extracts `sphere_offsets(radius_A, spacing_A)` and
`sample_grid(grid, unit_cell, xyz, *, radius_A, spacing_A)` inside the existing
stdlib-only `nasolve.metal.map_diagnostics` owner. Its ordinary and anomalous
capture callers reuse that arithmetic. No new module/import path, coefficient
reader, phase/Free-R policy, map normalization, artifact schema, force or threshold
is introduced. `_offsets()` preserves the existing 1.5 Å/0.5 Å neighborhood and
order; finite inputs and the 100,000-candidate enumeration bound are explicit.
Own/common positions remain caller choices, not interchangeable observations.

Linden reviewed the two source adapters and analytic/nonorthogonal/bare-import
regressions with no blocking finding. Hazel records the pre-change missing-API
failure and **82 focused passes** (5.27 s). Its exact full regression was pending
at the initial audit; W142 closes it at the same code pin. The separate C402/C404
shared Cedar gates do not qualify Alder by implication. Willow does not yet import unmerged Alder or contain a
parallel sampler. The next S06 adapter must bind saved-map generation/provenance
and eligibility through existing owners before any calibrated backbone detector.

### Independent installed and native read-only replay

The exact Git archive builds a wheel without dependency downloads. All **191**
packaged files match source bytes. The three historical unpackaged ligand
provenance JSON files retain their prior packaging status. The temporary build
source is removed and installation moved before `nasolve metal --help` and native
checks; all imported helper bytes come from that relocated wheel.

Under **Phenix 2.2.1-6174**, two complete read-only saved-coefficient FFT/sampling
executions test normal package imports and the bare sibling-module import used
by native workers. Each reproduces **3,648** W140 samples exactly: four maps ×456
atoms ×own/common positions, maximum numerical difference **0**. Four whole-cell
translation checks pass in each mode. Bare mode loads no `nasolve` package.
Legacy ordinary/anomalous requests and offset order match their exact pre-change
fingerprints. All 191 installed files and seven original model/map/parameter
references remain unchanged. Owned wall times are 3.030/2.019 s; both processes
are stopped. These are not new refinements, fmodel evaluations or coefficient
generation, nor a repeat of the full native metal capture lifecycle.

Exact controller command from the NASolve anchor (existing Python environment is
historical provenance, not a committed operational requirement):

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w141-install-sampler.py --commit 9c4c3b050fedd42f6be1fd6f26aa03873709bd76
```

The controller records wheel/source hashes, exact package/bare native commands,
process ownership and immutable before/after checks. The byte-verified archive
`branch-artifacts/willow/w141-shared-sampler-2026-11-18.tar.gz` contains 18 indexed
files plus manifest, 30,767 bytes, SHA256
`710b729a0ac6d039bb131dae25c0e0a5c23c532075606bfde7d2e874f0856315`.
Installed root `/private/tmp/w141-sampler-install-gx057s8e/relocated` is local
qualification provenance. No raw science or software environment is committed.
Old map receipts remain readable; no migration or public CLI change is required.
Ordinary ML inspection and metal MLHL capture remain different protocols, and
W140's test-inclusive maps are not upgraded into a work-only search objective.

### Scientific figure supplement

W140's existing measurements now have a three-panel PNG and editable SVG at the
NASolve artifact anchor, `branch-artifacts/willow/w140-science.{png,svg}`.
`w140-science.json` retains exact source hashes/data, rendering settings and output
checksums; `runners/w140-science-figure.py` reproduces them using Matplotlib 3.11.1,
Agg, DejaVu Sans, 12.5×4.6 inches and 170-dpi PNG. The PNG was visually inspected.
This adds no scientific measurements and leaves the three-file ChimeraX packet
unchanged. Geometry improvement, backbone movement and persistent phosphate
Fo–Fc are shown separately; the figure does not infer motion from a map value.

## W142 — Close shared qualification and map the density boundary

**2026-11-18.** This update closes software evidence and specifies the next S06
inspection boundary. It adds no coordinates, map coefficients, native fit,
numerical policy, runtime API/schema, CLI option or accepted repair. Rowan retains
Cedar ownership; Hazel owns the shared sampler and Alder delivery. The existing
W139/W140 scientific results and limitations remain unchanged.

### Exact shared gates

- **C402 `23c1f411f29501da351effa77e20dda707819468`:** complete unfiltered suite,
  **12,016 passes +293 subtest passes**, two existing native opt-in skips, zero
  failures/errors; pytest **3,275.43 s**, owned controller **3,279.887 s**.
  All **1,415** tracked files remain unchanged, Git/dependency status is clean,
  and the owned process stopped. Skips are the separately qualified native
  counted-contribution and pinned nonbonded-policy controls; no new skip/filter.
- **C402 installed:** source-absent relocated installation, all **304** resources
  match. The first 162-test run gave 143 passes and 19 failures from absent
  repository-relative data fixtures. Supplying only the two exact 5W6W restraint
  data files gives **19/19 passes**; this is a **143+19 joined proof**, not a
  claimed uninterrupted 162-pass execution. Original failure and corrected
  import/fixture receipts remain. No source-code fallback was introduced.
- **Alder `9c4c3b050fedd42f6be1fd6f26aa03873709bd76`:** **6,406 passes +276
  subtest passes**, no skips/failures/errors; pytest **1,390.83 s**, controller
  **1,399.501 s**. All **1,128** tracked files unchanged, clean Git and process
  stopped. Linden checked the result, source manifest and XML (6,682 entries).
  Hazel's separate **421-check** review of W141 passes. Alder delivery
  `a88b902a2a87da06454b1e2b99c89b7f915f97ba` changes docs after that code pin.
- **C404 `4bfffbca068cfe74cc926ff68fefca5ba5c83c3a`:** final frozen unfiltered
  suite completes with **12,032 passes +293 subtest passes**, two existing native
  opt-in collection skips, no failures/errors. Pytest **3,226.56 s**, controller
  **3,233.083 s**; all **1,416** tracked files unchanged, clean source/dependency,
  stopped process. The independent XML/source audit passes. Its first archival
  checker stopped before mutation because it expected collection-skip modules in
  JUnit `classname`; they are in `name`, with an empty class. The corrected checker
  requires the exact two names and collection-skip messages; expectations did not
  change. This gate does not cover Hazel's subsequent A04 edits.

Exact full-suite command shape, run by the retained owned controllers:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<clean-checkout>/src:<exact-NARestraints-checkout> PYTEST_ADDOPTS= <python> -B -m pytest -q -p no:cacheprovider -o addopts= --durations=20 --junitxml <receipt-root>/results.xml tests
```

The NARestraints checkout is exact `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`.
C404 adds only an explicit fresh `--basetemp <owned-scratch>`; no test scope or
filter changes. Plans retain exact argv, environment, interpreter/dependencies,
source hashes, process identity and timeout. C402 installed controllers are
`runners/w140-c402-install.py` and `runners/w140-c402-install-review.py` under the
NASolve `branch-artifacts/willow` anchor. Their receipts retain exact invocation
and initial/corrected results. These software suites are not new Phenix refinements.

### Map-source and frame audit

The [existing design contract](topostitch.md#saved-map-inspection-boundary-w142-design-w145-selection-identity-delivered)
now maps responsibilities to checkpoint/run-context/view, native-written-model
and shared grid-sampling owners. It separates artifact integrity, generation
evidence, coordinate correspondence and permitted scientific use. Ordinary ML
and maintained metal MLHL remain distinct; legacy inspection is not disabled.

The cold audit binds **nine source files** at C404/Alder pins and installed
**Phenix 2.2.1-6174**, with **seven unchanged scientific inputs**. Installed map
construction calculates weights/combined coefficients before excluding Free-R
rows; the map helper's alpha/beta estimator selects true-flag observations when
present. Therefore output work-set membership alone cannot qualify a work-only
search procedure. This is static source-path evidence, not a dynamic trace of
historical generation. No new coefficients, FFT, fmodel or native execution occurs.

Both C400 endpoints have identical Gemmi PDB/MTZ cells, while saved CCTBX values
differ by at most **2.93×10⁻⁶ Å** and agree at float32 precision. The original audit
incorrectly expected Gemmi to expose this difference and failed before output;
its runner/failure note remain. The corrected receipt records reader-specific
representation. No recipe-frame tolerance or symmetry image changes follow.

Controller command (all roots supplied explicitly; these are local audit anchors):

```text
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B branch-artifacts/willow/runners/w142-map-owner-audit.py --cedar <C404-checkout> --alder <Alder-checkout> --phenix <Phenix-site-packages> --c400 <C400-run-root> --nasolve <NASolve-anchor> --output <new-receipt>
```

The adapter, backbone calibration and automatic-motion policy remain unimplemented.
S06 remains **PARTIAL**. Distinct future regressions cover substituted references,
inherited-map meaning, unproven frames and relocation; do not repeat W141 arithmetic
or the completed native/normalization matrices.

### Retention, compatibility and handoff

All paths below use the NASolve anchor, `branch-artifacts/willow/`:

| Retained evidence | Bytes / SHA256 |
| --- | --- |
| `w142-c402-qualification-2026-11-18.tar.gz` — 12 indexed files + manifest | 269,982 / `93d844de3a4fd590f0998ed8c493d279a143c6c9737d3b44ba38739ec5956fdd` |
| `w140-c402-installed-evidence-2026-11-18.zip` — 16 indexed files + manifest | 1,561,924 / `374f325e797f39909561789a52064b81b2efc8150c98f1c14d8a38fbd1cb094f` |
| `w142-map-owner-audit-2026-11-18.tar.gz` — four indexed files + manifest | 5,740 / `9b88f787427e53df0175aa41fc1bd274dfabb0b9562dc267947a38671d7b42a2` |
| `w142-c404-qualification-2026-11-18.tar.gz` — ten indexed files + manifest | 252,388 / `61fadd3da2efad8e46215b649ba680df7a6a0b135d630f4d7884a9f23b3165b9` |

After archive member/hash verification, clean source checks and stopped-process
proof, only C402's owned checkout and proven-owned test scratch were retired:
**246,159 regular files, 4,477,814,236 logical bytes**. Symlinks were not followed;
scientific runs, shared dependency/environment and qualified installed packages
remain. The retirement plan/result retain inode and process ownership evidence.
C404's separately recorded disposable checkout/test scratch was then retired:
**246,214 regular files, 4,476,703,649 logical bytes**, 242.158 s; its two roots
are gone and shared dependencies, installed packages and science remain.
Hazel separately retired only Alder-owned source/test copies. No cleanup operated
on another agent's live workspace or generated scientific evidence. Rowan's
published Cedar `0a398d15ee465b12ed44b7e749221e54a8e343a9` has the same qualified
runtime/tests/packaging/README; later documentation does not imply a new suite.

Willow changes are confined to the existing design, periodic ledger, current
handoff, documentation index, roadmap JSON/generated Markdown and changelog.
Roadmap generation/check and diff/link checks validate this docs-only update;
the exact software gates above retain their separate source scopes. No schema
migration or default behavior changes. Raw structures/maps, test scratch,
qualification environments and all local audit payloads are excluded from Git.

## W143 — Make backbone density inspectable in 3D

**2026-11-18.** S07 presentation work requested by the scientist; no fitting,
new coefficients, automatic correction or maintained runtime/schema changes.
Hazel's chemistry-oriented 2D contour view remains preferred for residues/metals.
Backbone review needs a continuous rotatable path in one fixed crystal frame.
The [presentation contract](topostitch.md#density-presentation-local-chemistry-and-continuous-backbones-w143)
records that distinction and future shared-owner integration.

### Before, after and human feedback

W140's ChimeraX packet highlighted phosphates without map surfaces. The local
W142 common-plane/orthogonal section figure now uses identical crops/frame for
native and full endpoints, actual-point values and signed out-of-plane offsets.
All 24 sampled values match W140 and seven input references remain unchanged.
The PNG was visually checked; the first crowded-label draft is retained in its
verified archive. Matplotlib 3.11.1/Agg produced PNG and editable SVG.

W143 adds a self-contained 3D HTML view of C101–C103: **30 sugar/phosphate atoms,
32 recorded native bonds**, depth-tested solid geometry and real density-surface
section bands/silhouettes. Rotation, zoom, atom inspection, fixed-frame independent
model/map switching, optional faint shell and density-only front clipping support
inspection without exaggerating movement or fabricating contours. The user
confirmed v1 rotates and looks nice. After v2 lighting/theme polish, the user
preferred Slate, liked the residual fade and requested stronger contrast/control.

Final **v3** defaults to Slate and difference **±3.5σ**. The quiet contour-target
dropdown selects signed difference or ordinary density, remembering each level.
Both extend to **6σ**, in 0.5σ steps; ordinary defaults +1σ, minimum1σ, difference
minimum1.5σ. Paper has stronger pen contrast and Slate stronger red/green hues.
View options contains an independent contrast control. Optional signed-density
fading follows displayed-atom distance (full opacity through1.5Å, smoothly reduced
to15% from3.5Å, interpolated at mesh vertices). It leaves map values, meshes and
ordinary density untouched; it is emphasis, not a noise classification. The
buffer cache is bounded to three map/level combinations. No animation loop is
needed while idle. The user subsequently approved v3's appearance, calling it a
"beautiful inspector tool", and explicitly requested reuse throughout NASolve
without opening Coot for routine inspection. The main user/architecture/GUI docs
now record that shared direction; general stage integration remains planned.

### Validation and retained limits

- Complete **Phenix 2.2.1-6174 display-only execution**, not a refinement/dry-run:
  existing coefficient FFTs plus CCTBX/scitbx surface triangulation. V3 completes
  in **14.552 s** and stops; no new coefficient generation or native fit.
- Four saved maps, 0.5Å local sampling on43×23×25 sites, periodic interpolation,
  separate whole-cell sigma scaling. **62 meshes** include legitimately empty
  high-level surfaces. **6,277** interpolation checks pass, maximum error
  **3.55×10⁻¹⁵** before display rounding; **120** actual atom samples match W140.
  All **seven** scientific input references and **30** prior v2 meshes match
  exactly. Ordinary ML/test-reflection inclusion limitations remain explicit.
- **16 offline DOM/render-command contracts pass**, exercising all21level choices,
  independent remembered contour values, model/map/camera separation, clipping,
  focus/contrast controls, bounded buffers and unchanged data. The updated
  checker fails against v2's old default and passes v3. This is a mock WebGL
  harness: no real shader compilation, GPU or browser-layout PASS is claimed.
- Browser URL policy refused local-file automation. No alternate browser route
  was attempted. Human v1/v2 feedback and the later explicit v3 visual approval
  are separate from automated checks; no GPU automation PASS is inferred.

Commands recorded in the local execution receipts:

```text
PYTHONDONTWRITEBYTECODE=1 <Phenix-2.2.1-6174>/bin/phenix.python -B <NASolve>/branch-artifacts/willow/runners/w143-density-scene.py
```

The offline Node module exports `check(html_path, receipt_path)` in
`runners/w143-view-contract-check.mjs`; it was imported/executed in the available
Node runtime with no browser/network. Atlas/render source, exact executed argv,
process/exit receipt, final contract/integrity results and prior-version failure
are archived together, with per-member size/SHA verification. Local renderer
revisions remain in their respective archives, not a new production map reader.

All following paths use the **NASolve** anchor `branch-artifacts/willow/`:

| Artifact | Size / SHA256 |
| --- | --- |
| `w143-backbone-density-v3.html` — current self-contained viewer | `4949cdb869118a86aa75e9143ee18541bbe64151162421e85097780e860958aa` |
| `w143-density-prototype-v3.zip` — 11 indexed files + manifest | 1,717,737 bytes / `09d4ac28e848c1c2378bb96803713aa7aac1014d9ff1c37cced6d13ee9dc4e2c` |
| `w143-density-prototype-v2.zip` — reviewed previous graphics study | 1,008,044 bytes / `114c5d554dc1cf9e84c143c7d906be8ab6af164b1233911efbe61a4a6cd18842` |
| `w143-density-prototype-v1.zip` — user-confirmed initial interaction | 278,166 bytes / `837d91ac3392aae5a1965c92c36c578875d164576dd89e32eace37bb3224beb5` |
| `w142-density-sections-v2.{png,svg,json}` — fixed-frame orthogonal supplement | PNG `daad8079a67077d803e56482af5e13104025669151b591c20077d3090cbd9789` |

Committed changes are the existing main README, architecture/GUI contracts,
design/handoff, periodic ledger, docs index, changelog and roadmap JSON/generated
Markdown. Documentation generation/check
and diff/link/reference checks apply; C404's full suite is separately scoped to
its software pin and does not test this local prototype. No package/install,
CLI/default, runtime schema or migration change. HTML contains derived science;
all display payloads, coordinates/maps and local receipts remain excluded from
Git. Existing scientific packets and their checksums are preserved. S07 remains
**PARTIAL**: integrate through shared native map/checkpoint/view owners after the
W142 inspection boundary is qualified; do not create another map reader/history
or turn display controls into automatic acceptance.

## W144 — Bind saved density to the inspected frame

**2026-11-18.** This is a cold/native-read-only S06/S07 composition check of
existing owners, not a new adapter, sampling policy or repaired structure. The
C400 diagnostic has no ordinary report/registry and correctly refuses ordinary
checkpoint resolution. The genuine W138 ordinary **refine-002** child resolves
through Cedar `0a398d15` (qualified runtime `4bfffbca`), and its native-written
model validates. The selected checkpoint remains **postmr**. Its PDB bytes match
C400 full exactly; MTZ bytes differ, but all **8,344 ×16 numeric entries**, NaN
positions, labels, cell and space-group operations are identical. No basename
search, fabricated checkpoint, new coefficients or native fit was used.

A disposable derivative made through the existing manual-checkpoint owner moves
only C102 P by 0.25 Å. The existing resolver retains the ancestor map with an
explicit **not recalculated** label. Its model/map references resolve inside the
relocated context after the old copy vanishes. Changed observations and altered
map bytes refuse. A deliberately changed cell remains inspectable by the legacy
viewer, while a separate header comparison identifies the conflict; this is
why viewing compatibility and eligibility for automatic motion remain distinct.
Matching headers alone is **not** origin/image proof. The original 138 ordinary
files, 172 diagnostic files and 307 runtime source files remain unchanged. Only the
owned 140-file/17,858,738-byte test copy was retired; no real run was edited.

### Symmetry and interpolation

Four existing maps ×456 backbone atoms ×9 R3 operations give **16,416** symmetry
image comparisons. Native eight-point interpolation is periodic under integer
translations but not exactly equivariant under hexagonal fractional-axis mixing:

| Saved endpoint / map | Largest image difference (σ) | Largest operator RMS (σ) |
| --- | ---: | ---: |
| Native / ordinary | 0.244455 | 0.049094 |
| Native / difference | 0.277354 | 0.067404 |
| Full / ordinary | 0.244676 | 0.049290 |
| Full / difference | 0.272330 | 0.067458 |

Direct Fourier evaluation at the **six largest discrepancies per map** agrees
across symmetry images to **2.13×10⁻¹⁴σ**; nearest-voxel direct/FFT controls also
pass. This is a numerical interpolation effect, not a physical density change,
a map-quality threshold or a reason to reject the inspector. The direct-sum
method returns complex values; the first driver failed on `float(complex)`.
The corrected driver requires negligible imaginary parts and retains real
values. Both attempts and their stopped-process receipts remain.

The follow-up composes existing `topostitch_transport.ReferenceFrame` and Alder's
unchanged `sample_grid`, with checked map-group images and each complete
**855-atom** model inventory. Reverse reindexing preserves the whole mapping.
Bringing representatives back into their declared source query frame gives a
maximum **6.75×10⁻¹⁴σ** difference across all 16,416 comparisons and a maximum
coordinate roundtrip of **3.56×10⁻¹⁴Å**. Changed contexts and partial inventories
refuse. The probe explicitly requests radius 0.1 Å / spacing 0.5 Å (one center offset);
legacy metal capture defaults remain unchanged. This establishes source-query
consistency for this declared mapping, not exact continuous-map interpolation,
automatic image selection, a generalized origin witness or density-force gradients.

Complete read-only **Phenix 2.2.1-6174** executions: corrected direct/FFT diagnostic
**16.989 s**; existing frame/sampler composition **17.595 s**. All input hashes and
qualified helper bytes remain unchanged; no fmodel, refinement, new coefficients,
new acceptance threshold or runtime API/schema/default. Ordinary ML/test-reflection
limitations from W140/W142 still apply. The initial cold audit also retained a
setup failure from an unsupported `artifact_reference(...,sha256=...)` argument;
the corrected audit uses the existing path-only helper and adds measured hashes
in its own receipt, without changing the owner.

Controllers use explicit roots and retain exact argv in the local execution
receipts. Commands follow these forms:

```text
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w144-map-inspection-boundary.py --cedar <Cedar> --ordinary <W138-root> --diagnostic <C400-root> --nasolve <NASolve> --output <new-receipt>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w144-inherited-map-probe.py --cedar <Cedar> --ordinary <W138-root> --output <new-receipt>
PYTHONDONTWRITEBYTECODE=1 <Phenix>/bin/phenix.python -B <NASolve>/branch-artifacts/willow/runners/w144-symmetry-map-probe.py --baseline <W140-saved-density> --science <C400-root> --output <new-receipt>
PYTHONDONTWRITEBYTECODE=1 <Phenix>/bin/phenix.python -B <NASolve>/branch-artifacts/willow/runners/w144-source-frame-sampling.py --plan <checked-image-plan> --nasolve <NASolve> --science <C400-root> --transport <qualified-installed-package> --sampler <qualified-installed-Alder-package> --output <new-receipt>
```

At NASolve anchor, `branch-artifacts/willow/w144-map-frame-evidence-2026-11-18.zip`
contains **22 indexed files + manifest**, 30,207 bytes, SHA256
`34c7769433bc721b602020b3039d91bab4492dbcca9936ee8b2669de16471fa9`.
Each member was byte/size verified. Hazel independently passed **278 checks**
of archive integrity, exact Gemmi operations, Cartesian conjugation and saved
scalar arithmetic. This review did not repeat native FFTs or broaden the 24
direct-Fourier comparisons into 16,416 direct evaluations. The receipt is at
NASolve anchor `branch-artifacts/Alder/coordination-w144-frame-review-20261118.json`
(2,000 bytes; SHA256
`65eb426404e6c490f18b99f14348468bfab4c60b5bcb79d13026d6923fee6b28`).
Raw models/maps are excluded. A one-file
science checkout at GitHub anchor,
`ScienceCheckouts/Linden/2026-11-18_map-frame/review.html`, links five local evidence
files/views; all links resolve. Existing checkouts and the approved v3 inspector
remain unchanged. The later browser error was opening its unfilled developer
template; the template now identifies the finished file instead of attempting
to decode its placeholder. Strict base64 validation of the finished v3 passed.

The maintained adapter is still the next bounded implementation: reuse exact
checkpoint/view resolution, report generation evidence separately, and carry
explicit source/image correspondence into sampling. Keep uncertainty visible
when correspondence is absent. General origin/setting changes, local density
calibration, derivatives and automatic bending remain open. No new production
code was added; documentation/roadmap/reference checks apply. Local derived
science and receipts remain excluded from Git.

### Shared C406 qualification

Rowan's explicit declared-site observation candidate
`589659201a15b4284e93e2c4dcfc47cdefbdcb64` passes the complete unfiltered source
suite: **12,043 tests +293 subtests**, two existing native opt-in collection
skips, in **3,104.30 s**. All **1,417 tracked files** remain unchanged;
source and exact NARestraints `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691` are clean.
The stopped process, XML totals and both exact skip identities were independently
checked. This qualifies the frozen Cedar source, not a combined Willow/Alder
installation, the browser inspector or scientific repair.

The existing controller ran Python 3.12.14 / pytest 9.2.0 / Gemmi 0.7.5 /
NumPy 2.5.5 with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH` set to the
isolated checkout's `src` plus the explicit NARestraints source. The exact argv,
environment, source manifest, output and XML are archived. Its pytest command is:

```text
<qualified-python> -B -m pytest -q -p no:cacheprovider -o addopts= --durations=20 --junitxml <new-results.xml> tests --basetemp <fresh-owned-test-scratch>
```

NASolve anchor `branch-artifacts/willow/w144-c406-qualification-2026-11-18.tar.gz` retains
**13 indexed files + manifest**, 254,249 bytes, SHA256
`738138a9569d76d58b4ae4df905c37fe52d11c9a47e2a25752a0dabb773031b7`. Every indexed member was independently checked.

On 2026-11-19, the deferred retirement reverified the stopped process group,
source identity, recorded inode/device and all 13 archived members, then removed
only the two planned software/test roots: **246,332 regular files /
4,477,519,863 logical bytes**, 50.941 s. The completion receipt is
`branch-artifacts/willow/w144-c406-retirement-2026-11-18.json` at NASolve anchor.
No scientific run, qualified installation or shared dependency was removed.

Scientific inputs/runs, qualified installed packages and shared dependencies
remain.
No native refinement was run by this source suite; Rowan's separate installed
and actual native observation checks retain their own scope and evidence.

The source-gate records remain at NASolve anchor
`branch-artifacts/willow/w144-c406-full-suite-2026-11-18/`.
The archived closure ran with `--archive-only` and is not an idempotent cleanup
command: do not rerun it against already-created receipts. The subsequent ownership-checked retirement is complete. Do not repeat the
full suite or remove scientific/installed artifacts.

The exact C406 candidate also cold-replays the genuine W138 v8 child through
existing execution/checkpoint/view owners: native-written model validation,
8,344 ×16 map-value join and current **postmr** selection are preserved.
All 138 ordinary, 172 diagnostic and 307 runtime source files remain unchanged;
the 6.737 s check performs no FFT, native fit or child-process launch. This
confirms old-map-owner continuity, separately from the new observation feature.
The exact executed runner is retained as `runners/w144-c406-map-owner-compatibility.py`;
the original W144 runner was restored byte-for-byte from its immutable archive.


## W145 — Expose map selection ancestry through the shared view owner

**2026-11-19; additive backend API.** Previously, a `ViewProfile` identified the
inspected model's checkpoint but described map ancestry only in its human label.
It now carries optional, keyword-only `map_origin`: immutable
`MapOrigin(stage, checkpoint_id, inherited_through)`. The existing stage choice
and observation-compatible ancestry traversal construct this value directly.
For manual-002 → manual-001 → refine-001, the inspected ID stays manual-002;
the map owner is refine-001 and the route is `(manual-002, manual-001)`.
PostMR consumes a Phaser/AutoSol stage map without inventing a producing checkpoint.

Existing positional construction, file selection, labels, errors and Coot launch
behavior are unchanged. An available legacy map can still be viewed when its
ancestor model is gone. This is **selection identity**, not authenticated producer
XYZ/ADPs, coefficient-generation policy, frame equivalence or permission to move
coordinates. No map parsing, FFT, native fit, GUI launch, saved-schema migration,
checkpoint selection or detector is added. The architecture records the API;
the wider inspection projection remains partial.

### Validation and compatibility

- Source is Willow `efbb0336e8cd9380fc12145e0ba4e26d7e54fbab`; runtime source equals
  preceding `51af3423`, with a follow-up placing new cases before `unittest.main`.
  Five new cases cover direct/stage selection, requested versus current,
  multi-hop inheritance, PostMR's consumer role and old positional construction.
  The baseline fails on the absent field. The first focused run finds a test-only
  macOS path-alias comparison; resolving the expected temporary root fixes it.
  Both attempts remain. The direct unittest entry point runs all **36 cases**.
- **114 focused tests +53 subtests** pass in 9.97 s. **2,055 complete Willow
  tests +234 subtests** pass in 105.06 s, zero skips, 720 tracked files unchanged,
  source/dependency clean and process stopped. XML totals and hashes are independently
  checked. This is the smaller standalone Willow source, not Cedar's 12,043-test
  source gate or the forthcoming combined integration gate.
- A wheel built from the exact pin passes **114 installed tests +53 subtests**,
  CLI/import checks and all **89 installed file** hashes after its build-source
  and old installation paths vanish. The three pre-existing ligand provenance
  JSON sidecars remain outside this branch's wheel; no packaging policy changes.
  The tests import the relocated package, with explicit pinned NARestraints.
- The first full-suite controller setup stops before any test process: old Willow
  lacks the newer `run_owned_command` helper. The corrected external controller
  uses Cedar's qualified process owner while the **test process** imports only the
  pinned Willow source and NARestraints. Both setup records are preserved; no
  second test execution is claimed for the failed setup.
- Exact Cedar adaptation: base `86bdbb41ceef0693ea75c2bda385dae9c1358c44`, local
  commit `ae0929364c6994cb9bab643fe4df32f436e82f8b`, **182 focused tests +31 subtests**
  in 15.95 s; seven new Cedar assertions fail before. It preserves the positional
  `preparation_attempt` slot, preparation alternatives and explicit attempts.
  AutoSol's saved validation-model checkpoint remains separate from the stage-map
  origin; it is not relabelled as the coefficient-producing model. Hazel reviewed
  and applied all five exact file hashes to the isolated integration candidate.
  **Its combined full/installed gate is still pending**, with no active branch merge.

Exact source/installed command forms (full argv/environment are retained locally):

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <qualified-python> -B -m pytest -q -p no:cacheprovider tests/test_coot_view.py tests/test_coot_anomalous.py tests/test_coot_runtime.py tests/test_doctor_inspection.py tests/test_checkpoints.py tests/test_autorefine.py --junitxml=<receipt.xml>
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <qualified-python> -B -m tests.test_coot_view
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w145-full-suite.py --checkout <pinned-Willow-copy> --commit efbb0336e8cd9380fc12145e0ba4e26d7e54fbab --process-owner <qualified-Cedar> --output <new-receipts> --dependency-source <pinned-NARestraints> --basetemp <fresh-owned-scratch>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w145-install-view.py
```

NARestraints remains `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`;
Python 3.12.14 / pytest 9.2.0. Tests use synthetic inputs/executables, not a live
Phenix/Coot execution. The installed command sets `PYTHONPATH` to the relocated
package and that exact dependency, with source export absent.

At NASolve anchor, `branch-artifacts/willow/w145-map-origin-qualification-2026-11-19.zip`
retains **42 indexed files + manifest**, 620,699 bytes, SHA256
`dea71ae25f3d49b940c077eb7ad89ff0838571dd8e09c81fda730e4e505e209b`.
Every member was checked. It includes exact patches, the Cedar adaptation bundle,
wheel, logs/XML, initial failures and source/installed manifests; no scientific
payloads. The original W144 archive and all scientific packets are unchanged.
After archival and stopped-owner checks, four owned software/test roots were
retired: **6,079 regular files / 156,785,031 logical bytes**. The wheel and patch
bundle remain archived; shared dependencies and all original scientific data remain.
Receipt: `branch-artifacts/willow/w145-owned-retirement.json` at NASolve anchor.

Next is the shared inspection projection using this source identity, after the
combined qualification: bind exact displayed artifacts, keep associated model,
actual coefficient-generation model and comparison frame distinct, and retain
unknown evidence. Do not repeat the closed sampler/Fourier/normalization probes.
S06/S07 remain **PARTIAL**; no automatic bending or accepted repair follows.


## W146 — Bind a read-only model and map inspection snapshot

**2026-11-19; source `c3f52e2945f23ca77eb0c728a1353763a39c1a45`.**
`model_inspection.inspect_model_map` now projects the existing view into JSON:
selected model/map/support references, their measured hashes/sizes, and W145 map
ancestry. Previously consumers had to assemble this themselves. It re-resolves
the selection and checks the measured references before return, refusing changes
rather than mixing states. Explicit external paths stay usable and visibly
host-bound; anchored snapshots survive relocation with the original path gone.

This is new `model-map-inspection` schema 1, with no existing run/checkpoint/CLI
migration. Hashes are explicitly measured at inspection; they do not authenticate
historical producer XYZ/ADPs. Generation and frame evidence stay `not_assessed`.
Anomalous-map candidates do not prove usable columns. It writes nothing, launches
nothing, selects no checkpoint and does not lock the filesystem. Later consumers
must revalidate at their action boundary. Changed files: the new module and its
six regression cases, architecture, changelog and the current status documents.

### Qualification

- The absent-module baseline fails before the patch. **61 focused tests +31
  subtests** pass in 5.63 s. Cases cover exact bytes/read-only behavior, inherited
  maps without ancestor models, full relocation, explicit external maps,
  mid-read selection/model changes and existing declared-checksum refusal.
- **2,061 complete Willow tests +234 subtests**, zero skips, pass in **98.42 s**;
  controller 100.074 s, all **722 source files unchanged**, source/dependency clean,
  owned process stopped. The first full run retains **five sandbox-permission
  failures** in process listing/signalling and 2,056 passes; the unchanged rerun
  has those OS permissions. No product patch hides those failures.
- A source-free relocated wheel passes **120 tests +53 subtests** in 17.15 s,
  CLI/import checks and all **90 installed file hashes**. Build source and old
  install paths are absent. Wheel SHA256:
  `0c005d8d6d736a9e802213d871135fdde46caabc52b19944f583aaa353a41d11`.
  Existing unshipped ligand provenance sidecars remain unchanged.
- Hazel reviewed this bounded consumer and found no blocking issue; this is
  review evidence, not another executed test suite. An external load of this exact
  consumer over Hazel's unchanged installed candidate
  `1acc7892d2bc19d5572d46f430b27515a7ea6301` also passes on genuine W138 refine-001/002.
  All **344 installed files and 130 run files** remain unchanged; refine-002
  model/map hashes match W144. The current PostMR still refuses its missing
  Phaser MTZ through the existing owner; current selection stays PostMR.
  W145's direct installed origin read passes separately on the same two outputs.
  **W146 is not included in that frozen combined package or full-suite gate.**

Exact command forms; retained receipts contain the complete argv/environment:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <qualified-python> -B -m pytest -q -p no:cacheprovider tests/test_model_inspection.py tests/test_coot_view.py tests/test_coot_anomalous.py tests/test_doctor_inspection.py --junitxml=<receipt.xml>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w145-full-suite.py --checkout <pinned-Willow-copy> --commit c3f52e2945f23ca77eb0c728a1353763a39c1a45 --process-owner <qualified-Cedar> --output <new-receipts> --dependency-source <pinned-NARestraints> --basetemp <fresh-owned-scratch>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w146-install-inspection.py
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w146-real-inspection.py
```

Python 3.12.14 / pytest 9.2.0; NARestraints remains
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`. Tests use synthetic executables;
the cold compatibility read blocks launches. No Phenix/Coot execution, FFT,
new coefficients, detector or scientific acceptance is claimed.

At NASolve anchor, `branch-artifacts/willow/w146-inspection-qualification-2026-11-19.zip`
retains **42 indexed files + manifest**, **663,234 bytes**, SHA256
`639ada1b3104e6b328925642b22685a28ffe72780fcdd68b121202a88e329190`.
It includes the wheel, source patch, runners, failures, commands/XML/manifests
and the two genuine-run read receipts; raw crystallographic payloads are excluded.
Every archive member and both XML totals were independently checked. After archive
and stopped-owner verification, four owned software/test roots were retired:
**8,438 regular files / 109,624,452 logical bytes**. Scientific runs, shared
libraries and Hazel's package remain under their owners. The retirement receipt
is `branch-artifacts/willow/w146-retirement.json`; no generated evidence is in Git.

Next: reuse the existing native coefficient selection/description boundary for
explicit labels and descriptive headers, separately from FFT, sampling and
coefficient generation. The shared worker's extraction needs exact-version
saved-coefficient parity and must preserve old caches. No second launcher or
reader, inferred origin proof or default density threshold. S06/S07 remain
**PARTIAL**, and combined integration remains a separate gate.


## W147 — Share exact native coefficient selection and descriptive headers

**2026-11-19; source `5319a870b92d82adbba2c817c3bdc1073aaae402`.**
The native preview previously selected its complex array inline. A dependency-free
`map_coefficients` helper now exposes that exact ordered-list label match and
exactly-one-match refusal, returning the original object. Its second function
reports selected-array labels, cell, space-group/Hall symbol/operators and
reflection count as `map-coefficient-header` schema 1. The count describes the
selected native array, not every raw MTZ row. It performs no I/O, data-value
inspection, FFT, sampling, coefficient generation or fitting. Reader observations
stay separate from generation and model/frame proof, both explicitly unassessed.

The Willow patch adds that module, nine regressions, architecture and changelog;
no existing run/CLI schema or numerical policy changes. A separate candidate patch
for Alder's existing preview worker reuses the selector, preserves its sampling
and contour code, and adds the executed helper-source hash. **The worker patch
is not applied to the frozen combined candidate or active Alder branch.**

### Exact validation and review

- Missing-module baseline fails; **15 focused cases** (nine new plus W146's six)
  pass in 0.92 s. Exact, reversed, partial, case-changed, noncomplex, duplicate
  and absent selections are covered without first-match fallback or value reads.
- **2,070 complete Willow tests +234 subtests**, zero skips, pass in **133.92 s**;
  controller 134.868 s. All **724 tracked files** remain unchanged; source/dependency
  clean, owned process stopped. A relocated source-free wheel passes **129 tests
  +53 subtests** in 16.64 s, CLI/import checks and **91 installed file hashes**.
  Wheel SHA256 `11c0173441630045ea755f7609faedbb8308764da8b14d0207c61f7b199eaac3`.
- Complete **Phenix 2.2.1-6174** source and installed/bare-native checks read four
  authenticated W140 arrays (two MTZs). Each has 3,333 selected coefficients,
  exact labels and nine R3:H operators. The same native objects, values and indices
  remain unchanged; 16 missing/reordered/ambiguous controls refuse. Source and
  relocated-install executions take 2.496 s and 1.251 s, stopped; no FFT in these
  descriptor checks. The installed build source and original path are gone.
- The first worker adaptation and original worker independently generate exactly
  the same four-map/six-layer/**19,054-segment** preview, including numerical
  coordinates and metadata apart from implementation hashes. Both complete in
  about 1.24 s. This is a saved-coefficient FFT/contour replay, not new map
  coefficients, refinement, actual browser/GPU qualification or scientific acceptance.
- Hazel's review catches a helper-identity weakness: `importlib` can execute stale
  bytecode while a later file read reports a source hash. Version 2 captures the
  source bytes once, compiles/executes those exact bytes and hashes the same buffer.
  Two regression cases verify a real timestamp-matching stale-bytecode fixture and
  a source change after read; both pass (0.09 s), while the prior adapter baseline
  fails. Version 2 again reproduces the archived original preview exactly in
  **2.330 s**, stopped, with both original MTZs unchanged. Cached old results are
  not rewritten. This fixes the new helper identity, not all historical worker
  provenance. Hazel accepted the corrected bounded patch/test review, separately
  from these execution results. Final candidate worker SHA256:
  `d270c9ac72b499d7e50f114870e06897c4e7848c1b077311f8ebd1605173b54b`;
  helper SHA256 `0f43f741e50e4c67de9faae4da2de1f4894e5829b11a9788918c13b9236a197e`.

Commands use Python 3.12.14 / pytest 9.2.0 and pinned NARestraints
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`; exact argv, native interpreter and
execution records remain local. This is complete execution, not a dry-run.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <qualified-python> -B -m pytest -q -p no:cacheprovider tests/test_map_coefficients.py tests/test_model_inspection.py --junitxml=<receipt.xml>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w145-full-suite.py --checkout <pinned-Willow-copy> --commit 5319a870b92d82adbba2c817c3bdc1073aaae402 --process-owner <qualified-Cedar> --output <new-receipts> --dependency-source <pinned-NARestraints> --basetemp <fresh-owned-scratch>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w147-install-coefficients.py
<phenix.python> <NASolve>/branch-artifacts/willow/runners/w147-native-coefficient-review.py --helper <exact-source-or-relocated-helper> --baseline <W140-receipt> --science <declared-C400-root> --output <new-receipt>
PYTHONDONTWRITEBYTECODE=1 <qualified-python> -B <NASolve>/branch-artifacts/willow/runners/w147-preview-v2.py
```

Local NASolve-anchor archives, each checked member by member:

- `branch-artifacts/willow/w147-inspection-qualification-2026-11-19.zip`:
  **54 indexed files + manifest**, 854,471 bytes, SHA256
  `e0d35cb2a4a8e610ef3e60a7435da2d19b96a49ee14aee8d9b8879a157d9c829`.
- `branch-artifacts/willow/w147-worker-v2-qualification.zip`:
  **14 indexed files + manifest**, 144,695 bytes, SHA256
  `faf36b13303d78ad073a770d1522c17c1dcbc62e28be93bbe29dcbb30da80206`.

They preserve commands/XML, wheel/source patches, native headers and exact preview
outputs; no raw source MTZ/PDB files are added. Generated scientific evidence stays
local and out of Git. Eight owned software/adaptation/test roots are retired after
verification: **4,726 regular files / 93,593,803 logical bytes**, including disposable
copies of the retained original maps. Shared dependencies, scientific sources and
other agents' packages remain. The worker-v2 patch and regression test candidate
are retained separately for integration. Both S06 and S07 remain **PARTIAL**.

Next: qualify the shared integration before applying the worker adapter or joining
W146 snapshots to the native descriptor. Keep producer/frame interpretation and
calibrated density separate. In parallel, audit a bounded matching-diffraction
backbone recovery control: reuse W100's already declared displaced start and
C408's source-bound generation approach, rather than another bend generator or
repeat of W74/W75 representation tests. C408 remains a private chemistry-specific
prototype with fixed labels and a three-chirality fixture assumption, not a general
simulator. No new recovery result or density threshold follows from this plan.


## W148 — Recover a known backbone displacement with matching diffraction

**2026-11-19; installed Cedar source `f83562b0c1f61eb5b696d1ba75ebb4578b22c7ad`.**
This private control asks whether the existing native coordinate route recovers
an already frozen backbone perturbation when diffraction matches the reference.
It reuses W100's exact reference and +5° tapered displacement (A101–106/C111–114),
not a new bend generator. W100 was geometry/packing-only; W74/W75 tested
representation/scattering invariance rather than recovery. C408 supplied the
source-bound generation approach, not a general simulator or copied chemistry.

### Frozen comparison and complete execution

The two original PDBs have the same 855 canonical atoms. Exactly 204 XYZ records
change; all other bytes, occupancies and Cartesian ANISOU remain identical.
W138's prepared coordinates differ from this generating reference by up to
0.294579 Å: the plan explicitly distinguishes them. W138 supplies the bound
observations/Free-R template, ordinary native restraint file and settings;
fresh preflight interprets each actual W100 start. No truth-coordinate tether,
reference-model target, additional counted pair term or new chemical link is added.

Direct `n_gaussian` structure factors from the reference generate noiseless
amplitudes on the original 3,333 HKLs, preserving every Free-R flag (176 test).
`SIGF=0.02*F` is a declared weighting convention, not measured uncertainty.
No original amplitudes, experimental phases, bulk solvent or anomalous scattering
enter this control. The R3:H PDB/MTZ cells agree under the explicitly checked
float32 storage roundtrip, with exact symmetry operators; this is not a relaxed
general frame/origin tolerance. Resolution limit: 2.960807 Å.

Both arms use the same ordinary native restraints and 12 native parallelity groups,
five macrocycles, configured 100-iteration cap, fixed unit weights/scaling policy,
seed 1 and one process. All 855 XYZ refine; ADPs and occupancies do not. The other
651 atoms are unchanged only in the input perturbation, not fixed during refinement.
The existing Cedar preparation/phase/finalization owner validates both arms.
**Phenix 2.2.1-6174 completes all five native processes in 119.624 s**, all stopped;
eight original files, current checkpoint selection and all 304 installed files
remain unchanged. No live campaign is created or selected. No detailed optimizer
convergence proof was captured; five macrocycles and the absence of a stop message
do not provide one. The shared log parser's recap rows are not optimizer history.

Frozen plan SHA256:
`0f81297ead940b3f03a666c80900a349ece774818f0434970bceb937043d1826`.
Synthetic MTZ SHA256:
`8f5ce430b917935e95aa4ac33af8aff64de69963315f7a933b08c8ac12d4ea88`.

### Measured result and independent review

| Measurement | Displaced start | Recovered endpoint | Separately refined reference |
| --- | ---: | ---: | ---: |
| Selected 204-atom RMS error to generator (Å) | 0.917427 | 0.029167 | 0.011665 |
| Selected maximum error to generator (Å) | 1.768020 | 0.120312 | 0.029816 |
| Local 230 covalent bond RMS deviation (Å) | 0.039434 | 0.010913 | 0.012321 |
| Local 356 covalent angle RMS deviation (°) | 1.726343 | 1.671916 | 1.554269 |
| Final Rwork / Rfree | — | 0.0025 / 0.0029 | 0.0022 / 0.0017 |

All comparisons use the same crystal frame without rigid alignment. The two
refined endpoints differ by **0.026449 Å RMS** over the selected atoms. Remaining
context moves 0.032390 Å RMS (maximum 0.235741 Å) from the generator. All 126
ordered sugar-volume signs, 855 identities, occupancies and ANISOU are preserved.
Rwork/Rfree begin at 0.0983/0.1160 for the displaced model and 0.0045/0.0028 for the
reference. Near-zero final values concern idealized matching data, not experimental
validation. The pooled native log bond RMS is 0.027 Å for both; it must not be
conflated with the explicitly covalent-only table above.

Cold native geometry readback reuses W140's fixed-column method: **2,506 bond/angle
rows per model**, including 956 covalent bonds, 1,467 covalent angles and 83
user-supplied terms. Targets, weights and identities match across four tables;
independent Cartesian calculations agree within the predeclared printed/PDB
rounding bounds (0.002 Å / 0.12°). All 38 native O3′–P links are retained.
The generating model already has distorted B107→B111 phosphate angles outside
the moved region, also recorded in its original REMARK 500. One deviation is
46.61° initially and 37.07° at the recovered endpoint. Returning to this reference
does not establish healthy whole-model geometry or validate that link's intent.

Rowan's independent cold review passes **65 grouped checks**, reproducing 160
coordinate summary scalars, 504 ordered sugar volumes and 168 attachment distances
with separate fixed-column/stdlib arithmetic. Gemmi verifies HKLs/flags/sigma
convention; the input/restraint/settings changes and four-phase native inventory
match exactly. All 78 experiment files remain unchanged. No native rerun or
structure-factor recomputation is claimed by this review.

### Inspection, retention and exact commands

At the GitHub workspace anchor, the nine-file local checkout
`ScienceCheckouts/Linden/2026-11-19_matching-backbone/` contains `review.html`,
four actual PDBs, `open_inspection.py`, PNG/SVG figure and a checksum manifest.
The figure was visually checked. A separate **ChimeraX 1.12** headless execution
verifies four 855-atom models, 204 displayed atoms each, original coordinates and
identity scene transforms. The first launch failed on its sandboxed cache lock;
the unchanged permitted rerun passes. This is not a rendered browser/GPU check.
Gray/reference and salmon/start initially show; turquoise/recovered and
gold/refined-reference are available in Model Panel. No alignment or magnification.

The exact local runners, commands, source/installed manifest, native requests,
results, geometry, independent review and checkout are archived at NASolve anchor
`branch-artifacts/willow/w148-matching-backbone-evidence-2026-11-19.zip`:
**102 indexed files + manifest**, **3,442,322 bytes**, SHA256
`99bf9d6e150e0510519adc9b929d15cc1d3954eba2449625ea4a7e2eb5b83e25`.
Every archive member was read back and checked; five native process groups are
absent. Historical requests retain their original provenance paths: this archive
is verifiable cold evidence, **not a portable executable campaign**. Raw science
and source run remain local, deliberately excluded from Git.

```text
PYTHONDONTWRITEBYTECODE=1 <Python3.12.14> <NASolve>/branch-artifacts/willow/runners/w148-control.py
PYTHONDONTWRITEBYTECODE=1 <Python3.12.14> <NASolve>/branch-artifacts/willow/runners/w148-readback.py
PYTHONDONTWRITEBYTECODE=1 <Python3.12.14> <NASolve>/branch-artifacts/willow/runners/w148-geometry.py
PYTHONDONTWRITEBYTECODE=1 <Matplotlib 3.11.2-python> <NASolve>/branch-artifacts/willow/runners/w148-checkout.py
<ChimeraX1.12> --nogui --exit --script <NASolve>/branch-artifacts/willow/runners/w148-viewer-check.py
PYTHONDONTWRITEBYTECODE=1 <python> <NASolve>/branch-artifacts/willow/runners/w148-archive.py
```

Native argv/process records are in `experiment/audit.json`; the controller and
generator are frozen in that same prefix. Cold receipt references resolve through
the declared `experiment` anchor; archive names preserve it. This was complete
execution, not a dry-run. No maintained runtime, schema, CLI or installation
behavior changed; documentation-only validation uses the roadmap audit and its
eight focused tests. A new full software suite would duplicate unchanged code;
Hazel owns the separate frozen combined gate.

**Scope:** this closes one idealized positive-control question, not S04/S05/S06,
B09/B10, experimental repair or automatic sticky-end enforcement. No detector,
density-noise calibration or chemical acceptance follows. Next qualify the
shared inspector integration, then predeclare independent healthy/no-op and
forward/reverse bend controls with verified sequence/link intent. Keep imperfect
source-link diagnosis separate; do not silently repair or remove it in this
matched experiment. Numerical-policy changes and W122 activation remain deferred.

## W149 — Package the reusable offline density inspector

**2026-11-19; S07 remains PARTIAL.** Source
`04b6402a274f27b84da298d23ce5c0db58776438` extracts the approved W143 presentation
into `nasolve.density_inspection` and an installed HTML resource. Previously the
view required a local developer template. A caller can now render a prepared,
bounded two-state scene with explicit labels and source/frame notes from an
installed package. Missing maps remain unavailable. Display controls retain
Slate/Paper, lighting, independent model/map selection, independent contour levels
through 6σ, contrast, cutaway and distance-based residual fading.

**Boundary:** the existing local scene kind/version remains
`local-backbone-density-display`/1; `native` and `full` are legacy presentation
slots, not quality or scientific-policy labels. Existing CLI, checkpoints and
native readers are unchanged. This API does not generate maps, find inputs,
authenticate a producer, establish frame equivalence, fit coordinates or adopt a
trial. Calls copy and validate the scene, escape human text, embed compressed
JSON and refuse output overwrite. A 40 Å camera radius covers both atom states
and all mesh vertices; bounded centers/crops, counts and exact contour-band loop
work prevent clipping or unbounded display work. The 0.25 Å crop allowance is a
legacy half-voxel display allowance, never a crystallographic frame tolerance.
See the [API contract](architecture.md#shared-in-app-modeldensity-inspector).

**Validation and failures retained:** initial source `b8b4678` passed 2087 tests
+234 subtests and 154 installed +53. Rowan then identified missing camera-envelope
and generated-band-work bounds. Four added regressions fail on that source;
corrected `04b6402a` passes all 29 focused renderer/graph tests. The initial absent
module baseline also fails as expected. Corrected qualification:

- Full Willow: **2091 tests +234 subtests**, no skips, 126.57 s pytest elapsed.
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<pinned-NARestraints> python -B -m pytest
  -q -p no:cacheprovider -o addopts= --durations=20 --junitxml <receipt> tests
  --basetemp <owned-external-scratch>` in an exact clean checkout. NARestraints
  `a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`; all tracked bytes remain unchanged.
- Build: `python -B -m pip wheel --no-deps --no-build-isolation --wheel-dir
  <wheels> <source>` then `pip install --no-deps --no-compile --target <installed>
  <wheel>`. Move installation, delete source and original installation, import
  public APIs, run `python -B -m nasolve show --help`, then pytest over
  `test_density_inspection`, `test_topostitch_view`, `test_map_coefficients`,
  `test_model_inspection`, `test_coot_view`, `test_coot_anomalous`,
  `test_coot_runtime`, `test_doctor_inspection`, `test_checkpoints` and
  `test_autorefine`: **158 +53 subtests** in 19.78 s. All 93 package files remain
  unchanged. Python 3.12.14, pytest 9.2.0. Exact argv/environment in receipts.
- Wheel SHA256:
  `74e64bac3bd269f2dc56bcc5d2445a53bcde28d26dbe11742f8acc5ce52f2ec4`.
  Three inherited ligand provenance sidecars remain outside existing packaging;
  this patch does not change that prior limitation.
- Source/installed HTML bytes agree exactly. All original W143 scene fields,
  30 atoms, 32 bonds, 62 meshes, 61,500 vertices, 117,814 triangles and shader
  sources remain exact. A generic non-phosphate/no-map fixture also renders.
- The same installed API displays W148's actual 204 moved atoms and 228 existing
  internal covalent bonds, without maps, alignment or invented links. Sixteen
  offline control contracts pass on each of the three scenes. These are mocked
  DOM/WebGL command checks, **not browser layout, shader/GPU or visual acceptance**.
- Rowan's bounded static recheck finds both issues and wording addressed. No new
  Phenix/Coot execution or map calculation occurs in W149. W148's separate native
  recovery evidence is unchanged.

**Local review:** GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-19_inspector/review.html`; four files including
both self-contained views and a checksum manifest. The recovery view links the
prior four-model science report. This is not a new campaign selection.

**Preservation:** NASolve anchor
`branch-artifacts/willow/w149-inspection-qualification-2026-11-19.zip`, 90 indexed
files +manifest, 5,594,024 bytes, SHA256
`d32c50554542e4c12c32af92ee573103589948f030a34620b46e2cd9cd3ebae9`.
Every member verified; includes initial/final failures and passes, both wheels,
source patch, runners, views and peer reviews. Historical paths are provenance;
the archive is not a portable executable campaign. After process/inode and archive
checks, only four owned test/install roots were retired (9,418 files,
168,624,027 bytes); science, shared dependencies and peer work remain. A sandbox
process-list permission failure preceded the unchanged successful cleanup.

**Next:** qualify shared receiving-owner integration before the stage adapter.
W146/W147/W149 and the worker-v2 adaptation remain outside the frozen combined
runtime `1acc7892`. Its separate full run recorded one fixture-related failure,
12,845 passes, two skips and 298 subtests; the test-only amendment has 35 focused
passes. Hazel owns the documented delivery decision; do not label that evidence
a fresh full-suite pass. Reuse existing selection, map and frame owners for a
small read-only scene adapter; ordinary repair publication and density-guided
movement remain separate gates. No new model/frame or noise threshold follows
from a working renderer.

## W150 — Qualify the inspection follow-on against shared Alder

**2026-11-19; temporary candidate, no active-branch merge.** Delivered Alder
`f989111e31a18687625995a5264c25cc38a67db6` incorporates the reviewed test-only
amendment to its completed full execution. W150 composes the already qualified
W146/W147/W149 helpers/resource and W147 worker-v2 against that exact base.
Candidate `e89adc319fbd10e466efe5ed1856d6c29868c261` is preserved in a local Git
bundle/patch, not a published development branch. Existing selection, native map,
checkpoint and sampling owners are reused. Of 1,501 prior tracked files, 1,497
are byte-exact; changes are the previously qualified worker adaptation, one
additive package-resource pattern and two scoped documents. Eight files are
added: three helpers, the renderer resource and four existing test modules.
No new scientific behavior, generation policy or inference is introduced.

**Focused qualification:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<pinned-NAR>
python -B -m pytest -q -p no:cacheprovider -o addopts= --junitxml <receipt>
<explicit modules> --basetemp <owned external scratch>` passes **192 tests
+37 subtests** in 28.07 s. Modules cover model inspection, coefficient selection,
renderer, worker helper identity, metal inspection/sampling, checkpoint integrity,
Coot views/runtime/anomalous maps, Doctor inspection, checkpoints and counted
AutoRefine. All 1,509 tracked files remain exact. The source-free relocated wheel
passes the same **192 +37** in 26.35 s, API imports and `nasolve show --help`;
all **348 packaged files** stay exact. Wheel SHA256
`fa80d1261fe04a63a300365c0b5dd76218ac2f9ad8a51b905fdc97c1085613f4`.
Build uses `pip wheel --no-deps --no-build-isolation` and install uses
`pip install --no-deps --no-compile --target`; source and original installation
are absent before installed tests. Exact argv/environment and source/package
manifests are archived. The three inherited provenance-sidecar exclusions remain.
This is focused development qualification, **not a new combined full-suite pass**.
The base's original full failure and test-only correction remain explicit.

Actual W138 two-checkpoint inspection equals the prior W146 snapshots and leaves
all 130 run files unchanged. An initial runner used the experiment parent rather
than the archived declared `/run` child; it refused before output, and the
corrected runner retains that failed attempt. The installed renderer produces
byte-identical W143 HTML and exact scientific fields. One complete installed
**Phenix 2.2.1-6174** saved-coefficient FFT/contour replay reproduces all **19,054
segments/six layers** from the archived original worker in 1.99 s. It does not
refine or generate coefficients. Both unique MTZ inputs and all package files
remain unchanged; the owned process is stopped. No new browser/GPU claim.

**Delivery and cleanup:** NASolve anchor
`branch-artifacts/willow/w150-inspection-integration/candidate.bundle` and
`candidate.patch` retain the exact candidate for the receiving owner. Archive
`branch-artifacts/willow/w150-inspection-integration-2026-11-19.zip` contains
49 indexed members +manifest, 3,628,492 bytes, SHA256
`1a6bad0f4356a49bf10053200c35a6b3edcbd9407839bcacf04c1f7f1c78f17b`.
Every member verifies. After stopped-process, inode and archive checks, one owned
scratch root was retired: 7,173 files/63,298,755 bytes. Source bundle, wheels,
evidence, scientific inputs and peer work remain. Historical paths do not make
this a portable executable campaign. Hazel owns any receiving-branch adoption;
no stage adapter, CLI activation, new coordinate fit or scientific acceptance.

## W151 — Separate deposited sequence continuity from reference geometry

**2026-11-19; cold evidence only.** Before broadening the W148 positive control,
check the B107→B111 reference-link interpretation against the
[public deposited 8D93 mmCIF](https://files.rcsb.org/download/8D93.cif), retrieved
2026-11-19 (237,027 bytes, SHA256
`9f67eb6a7193d1ff06b68105e4ba8a066f4b02bef55787fc096404a99fa1d7bb`).
The [entry](https://www.rcsb.org/structure/8D93) declares the seven-nucleotide
B strand **ACACCGT**. Polymer sequence positions 3 and 4 map to the actual atom
records labelled B107 and B111. This numbering jump is **not three absent
residues**. The scheme's `auth_seq_num` and `pdb_seq_num` differ here; bind
`label_asym_id`/`label_seq_id` to actual `atom_site` identity instead of swapping
number namespaces or sorting numbers into a chemical interpretation.

The deposited O3′(B107)–P(B111) distance is **1.605707 Å**. Its O3′–P angles to
O5′, OP1 and OP2 are **77.7349°, 79.6844° and 154.6068°**. The W148 generating
reference retains essentially the same distortion; original PDB REMARK 500 also
reports it. Sequence-supported adjacency and unhealthy local angles are separate
facts. Do not delete the link, fill three invented residues or call the whole
reference healthy solely from numbering/coordinates.

This audit also preserves W115's existing lineage finding: W148's generating
reference is the earlier unvalidated small bend preview, not pristine deposited
coordinates. All 855 identities match the current mmCIF; maximum raw positional
difference is 0.178558 Å, RMS 0.048102 Å. Higher mmCIF coordinate precision causes
small raw differences throughout; 204 atoms differ by more than 0.001 Å. That
reporting threshold is not a frame-tolerance change. W148 remains a valid recovery
of its declared generating reference, not a new healthy-source qualification.

**Validation:** `PYTHONDONTWRITEBYTECODE=1 <Python3.12> -B
runners/w151-reference-audit.py` uses Gemmi 0.7.5, exact source hashes, full atom
identity matching, deposited entity/polymer/atom-table joins and independent
Cartesian distance/angle arithmetic. The first runner correctly refused a
comparison of undecoded quoted CIF names with PDB names; Gemmi string decoding
fixes the runner without weakening identity checks. Both source files remain
exact. No native execution, runtime/schema change, inference activation, new
model or scientific acceptance. Existing TopoStitch discovery already refuses
to infer a break from a chain boundary, number gap or missing atom; this is a
real example supporting that boundary, not a new implementation.

Local archive: NASolve anchor
`branch-artifacts/willow/w151-reference-audit-2026-11-19.zip`, eight indexed files
+manifest, 78,027 bytes, SHA256
`2a036d2e6212406310f31eeba92467e218da2c4e533a8e49a2b28ad9ebb3dea2`.
It preserves public input, failed/corrected runner, audit and interpretation;
W148's existing archive owns the reference PDB. No raw scientific file is committed.

**Next scientific gate:** predeclare an independent canonical bend/unbend or
changed-direction control and its matched no-op, with sequence/image/link intent
and local geometry audited before fitting. A no-op reference need not be a
perfect whole molecule, but its monitored local region and inherited defects
must be explicit. Keep the B107→B111 distortion visible as context; never remove
real topology to improve a geometry score. Retain fixed data/Free-R, original
attempts, junction limits and matched endpoint comparisons. Experimental/noisy
density support, general closure and the B09 geotest demonstration remain open.

## W152 — Recover opposite backbone displacements in an independent deposited model

**2026-11-19; completed canonical matched-data control.** W148's generating
reference is now complemented by deposited 5W6W, not another descendant of the
8D93 preview. Public [5W6W coordinates](https://files.rcsb.org/download/5W6W.pdb)
were retrieved 2026-11-19 (99,225 bytes; SHA256
`f33754cc170ab8167e8085cb848f4ef0b6bd0f545c81db6163a650a41f503e71`).
All 859 atoms/42 canonical residues, cell, occupancy and B values are preserved.
The explicit register is A2–8/C14–8, A9–15/B7–1 and A16–21/D7–2. Twenty
canonical pair recipes are declared; no inferred sticky connection or symmetry
covalent bond is added. The input window has fixed end pairs A9/B7 and A15/B1;
205 atoms in the five interior pairs receive equal opposite tapered rotations
(up to ±5°) through the existing preview rotation/render functions.

One frozen synthetic amplitude set is calculated from the deposited source at
3.06 Å: 7,554 reflections, 389 deterministic synthetic test flags, no added
measurement noise. These are not experimental observations or original Free-R
flags. All three starts use the same data, restraints, five macrocycles,
100-iteration cap, seed 1, one process, fixed unit weights, fixed occupancy/B,
no generating-coordinate tether and all 859 XYZ coordinates active. Thus the
654 context atoms are not frozen during refinement. Phenix **2.2.1-6174** runs
through the unchanged installed Cedar C407 owner
`f83562b0c1f61eb5b696d1ba75ebb4578b22c7ad`; NARestraints source is
`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`.

| Start | Initial selected RMS to generator (Å) | Final RMS to generator (Å) | Final RMS to relaxed control (Å) | Local covalent bond RMS (Å) | Local angle RMS (°) |
| --- | ---: | ---: | ---: | --- | --- |
| Deposited reference | 0 | 0.01436 | 0 | 0.01742 → 0.01785 | 1.833 → 1.896 |
| Positive displacement | 0.76410 | 0.05152 | 0.04505 | 0.06226 → 0.01105 | 3.661 → 2.004 |
| Negative displacement | 0.76411 | 0.04653 | 0.03978 | 0.06665 → 0.01143 | 3.636 → 2.010 |

Local geometry covers 232 covalent bonds and 363 angles touching the selected
atoms. All 126 ordered sugar-volume signs and 38 native backbone links survive;
all 2,569 bond/angle target, sigma and weight definitions match across six states.
The pooled native bond RMS includes user terms and must not be presented as pure
covalent geometry. Final Rwork/Rfree are .0062/.0067, .0121/.0141 and .0114/.0132;
these small values reflect idealized matching data, not experimental success.
Fixed-budget completion does not establish optimizer convergence.

**Stacking scope:** the identical native recipe contains 20 pair-plane and 38
same-chain adjacent stacking groups, not merely twenty restraint terms. It
includes A8–9 and A15–16 outside the moved interior. Independent unsigned SVD
plane angles at those boundaries are initially 8.174°/7.003°, 8.051°/6.862° in
the relaxed control and approximately 7.2°/6.35° after displaced recovery. The
largest initial plane mismatch is 23.369°. Existing source defects remain;
this does not qualify whole-model stacking health, junction intent or flexibility.
No restraint was removed or retuned after seeing the outcome.

**Validation and ownership:** source/hash/preflight checks preceded fitting.
Exact commands were `PYTHONDONTWRITEBYTECODE=1 <shared Python3.12> -B
runners/w152-prepare.py`, `runners/w152-control.py`,
`runners/w152-readback.py`, `runners/w152-control.py --refine`,
`runners/w152-readback.py --final`, `runners/w152-execution-review.py` and
`runners/w152-parallelity-scope.py` (same Python/environment prefix throughout).
The generator is a captured Phenix job. Seven native process groups stopped;
preflight took 22.33 s and refinement phases 177.15 s combined. Independent
Rowan cold review reproduced both signed inputs to PDB rounding, coordinate and
geometry results, target identities, links, sugar signs and data/flag counts.
The cold execution audit preserves 113 source/result files and 304 installed
package files. No runtime code or schema changed; the existing W149 complete
source/installed qualification is not rerun for private diagnostics and docs.

The local human packet is at ScienceCheckouts anchor
`Linden/2026-11-19_opposite-bends/review.html`: two existing-renderer comparisons,
six actual PDBs and one ChimeraX loader. ChimeraX **1.12** headless verification
opens all six models with exact coordinates, identity placements and 205 selected
atoms each. This is not browser/GPU review. No alignment or exaggerated movement.

Evidence archive: NASolve anchor
`branch-artifacts/willow/w152-independent-backbone-evidence-2026-11-19.zip`,
145 indexed files +manifest, 5,489,262 bytes, SHA256
`c9887ace11aae6bffe77cd5aaba602741c2e652a05db0e346e6f31c06ac76753`.
Member hashes verify. Original science remains; generated data, native logs,
models, maps and local runners are excluded from Git. Historical native paths
are provenance, not a portable executable-campaign claim. No compatibility or
migration change.
Documentation validation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
<shared Python3.12> -B -m pytest -q -p no:cacheprovider
tests/test_topostitch_roadmap.py` passes all eight cases;
`scripts/audit_topostitch_roadmap.py --write` and `--check`, plus
`git diff --check`, pass. The initial unittest invocation collected zero pytest
functions and is not counted as validation. No unchanged full suite rerun.

**Milestone decision:** close this independent-model, opposite-displacement,
matched-no-op subgate. S04/S05/S06 remain PARTIAL. This is not reciprocal
straight/curved target recovery, larger bending, automatic window expansion,
physical seam closure or experimental/noisy-density qualification. Next inspect
whether the deposited diffraction supports a bounded matched experimental
control, preserving original observations/flags and the relaxed-reference arm.

## W153 — Separate experimental backbone recovery from geometry-driven relaxation

**2026-11-19; ordinary experimental control, mixed outcome.** Reuse W152's
unchanged reference and signed starts against [deposited 5W6W structure factors](https://files.rcsb.org/download/5w6w-sf.cif),
retrieved 2026-11-19, 651,299 bytes, SHA256
`d5a0d2190fb21a6e0b1ebbac917da8f189ceff1af2c1d14c36886d8e0bc1c4dd`.
Of 7,562 source rows, 5,137 have positive finite F/SIGF: 4,630 work and all
507 original Free observations (`test_flag_value=1`). The other 2,425 rows
have missing F/SIGF (2,410 status `x`, 15 status `o`); preserve their identities
and reasons. No flags are created, extended or reclassified; deposited map
coefficients are not used as observed amplitudes. The conversion is checked at
MTZ float32 precision. Deposited PDB/CIF cell fields match exactly; native
120°→120.00000000000001° arithmetic fits the existing 1e−10 frame bound. The
first converter's overly strict binary-equality refusal is retained, not hidden.

The same three arms use five cycles, 100-cap XYZ optimization, seed 1, one core,
fixed unit coordinate/geometry weights, fixed B/occupancy and unchanged explicit
pair/stack restraints. **Bulk-solvent/scaling is enabled in every arm**, an
explicit difference from W152. No coordinates, restraints or weights are tuned
after seeing Rfree. All 859 XYZ coordinates are active; the input-only anchors
are not native fixed sites. Installed Cedar C407 and Phenix **2.2.1-6174** remain
unchanged. Preflight completes before fitting; three refinements take 246.72 s
combined. All seven successful native process groups stop.

| Start | Final selected RMS to deposited model (Å) | Final RMS to relaxed reference (Å) | Local bond RMS (Å) | Local angle RMS (°) | Common-HKL Rwork / Rfree |
| --- | ---: | ---: | ---: | ---: | --- |
| Reference | 0.52152 | 0 | 0.00357 | 1.201 | .239242 / .259995 |
| Positive | 0.52131 | 0.21485 | 0.00361 | 1.205 | .239916 / .257888 |
| Negative | 0.49506 | 0.14566 | 0.00353 | 1.243 | .238709 / .261100 |

The initial reference after native scale fitting gives Rwork/Rfree .2238/.2413,
close to the deposited values. Geometry improves while the reference moves and
its Rfree rises by about .019. This is a tradeoff under the frozen protocol,
not an accepted repair or proof of a universally appropriate weight policy.
Twenty pair-plane angles have RMS 11.226° initially, about 3.38–3.54° afterward;
38 adjacent-stack angles change from RMS 9.193° to 4.13–4.27°. These measured
changes do not prove that flattening every base pair/step is physically right.
All 38 covalent backbone links and 126 ordered sugar signs survive; all 2,569
bond/angle target/sigma/weight definitions match across six states. Local
geometry covers the same 232 bonds and 363 angles as W152.

**Adaptive filtering is explicit.** Raw input/output F/SIGF and all original
Free membership remain exact in all arms. Native outlier rejection removes work
reflection **(5,18,−1), F=434.87, SIGF=5.33** only in the positive arm. Thus the
trajectories do **not** share identical effective work sets. The strict initial
saved-map audit correctly refused that equality; retain its log and original
worker. The amended read-only audit records the excluded row and exact remaining
values, rather than calling it a matched-data PASS. Rowan independently confirms
source/raw-output membership, the native log's 5,137→5,136 transition and the
coordinate comparisons.

Following that review, reuse saved final `F-model` amplitudes and their fixed
scales to reconstruct each native R value, then evaluate the **common 4,629 work
and all 507 Free indices**. The table gives this cold common-HKL arithmetic;
no additional refinement, coefficient generation or scale optimization occurs.
The common-set values hardly change the interpretation. Positive-arm F-model is
unavailable at its rejected work row; no value is invented. This does not qualify
a fixed-work-set trajectory or provide a reason to choose a winner from the
small final Rfree differences.

**Saved density:** all six selected unfilled ordinary ML coefficient arrays are
bound to exact model, MTZ and effective parameters. Each includes the 507 Free
indices; positive has 5,136 coefficients, the other arms 5,137. Reuse W147's exact
coefficient selector and Hazel's unchanged A72 periodic sampler. At 459
sugar/phosphate sites per map, compare own endpoint and fixed deposited positions;
lattice-translation checks agree within 2.63e−13σ. B2 P remains about −8.09,
−8.31 and −8.35σ at its three endpoints. B2 P's occupancy=1 and B=90.39 Å²
remain fixed. Strong negative density on an atom is still not a unique motion
instruction: occupancy/ADP, scattering, model or phase errors remain alternatives.
Separate whole-cell sigma scaling and model-assisted phases prohibit absolute
cross-map electron-count or independent-validation claims. The inherited
123-point/1.5 Å sampling sphere is not a calibrated backbone noise detector.

The small human checkout is at GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-19_experimental-backbone/review.html`. It contains
two B2–4 density/movement views, six actual PDBs, ChimeraX loader and manifest.
B2–4 was chosen after fitting because its phosphate has the most negative
selected-phosphorus sample in every arm; this is disclosed inspection selection,
not a fitting or acceptance rule. Each view has 33 atoms/35 native covalent bonds,
a shared 0.5 Å grid and 62 verified contour meshes. Model labels name the displaced
start/endpoint; map labels separately name relaxed-control/endpoint coefficients.
Default model switching keeps the control map stationary. No alignment or
magnification. ChimeraX **1.12** headless checks exact six-model coordinates,
205 selected atoms per model and identity placements. Seventeen offline mocked
render/control checks pass per view; no browser/GPU qualification is claimed.

**Exact validation commands:** with `PYTHONDONTWRITEBYTECODE=1`, the shared
Python 3.12 runs `runners/w153-prepare.py`, `w153-control.py`,
`w153-readback.py`, `w153-control.py --refine`, `w153-readback.py --final`,
`w153-execution-review.py`, `w153-density.py`, `w153-common-r.py` and
`w153-parallelity-scope.py`. The controller captures native conversion/refinement;
the density controller captures a read-only Phenix worker. Phenix's bundled Python
runs `-B runners/w153-scene.py`; shared Python runs `w153-checkout.py` through the
qualified W154 installation. ChimeraX runs `--nogui --exit --script
runners/w153-viewer-check.py`. Exact arguments, dependencies and retained failed
attempts are in the receipts. No Willow scientific runtime/schema or default
refinement policy changes; the separate W154 presentation patch is below.

Archive: NASolve anchor
`branch-artifacts/willow/w153-experimental-backbone-evidence-2026-11-19.zip`,
187 indexed files +manifest, 12,809,610 bytes, SHA256
`efdeadf5a96084752d0ab24bdd5f1e7f4108359234439201af5d55c47efb3d52`.
All member hashes verify. Native roots, failures and human checkouts remain local;
none of the generated scientific payload is committed. Archive paths and checksums
support integrity, not portable native continuation.

**Decision:** close the bounded ordinary experimental comparison and source-to-map
readback question; retain the mixed scientific outcome and adaptive-work-set
limitation. S04/S05/S06 stay PARTIAL. No new refinement matrix is queued merely
to erase one rejected row. A future fixed-work-set trajectory must predeclare
that policy. Next density work must distinguish displacement from occupancy/ADP
and phase/scattering errors before proposing motion. Hazel's existing matched
scale/ADP control and own/common-coordinate map sampling are useful precedents,
not a qualified local causal matrix. See Alder's current owner and its
`docs/history/metal-development-handoff-2026-11-18.md` evidence sections; history
is evidence, not an active instruction. Larger/reciprocal shapes, junction-aware
window expansion, physical closure and the B09 geotest demonstration remain open.

**Cold movement/geometry supplement (same W153 scope):**
`branch-artifacts/willow/w153-experimental-backbone/motion-association.json`
binds the existing coordinate/plane receipts and all six original model hashes.
Run with `/private/tmp/willow-w94-pivot/env/bin/python -B
branch-artifacts/willow/runners/w153-motion-association.py` from the NASolve anchor.
The script verifies two analytic rigid-motion controls and preserves all inputs;
there are no native calls or new refinements. Reference all-859-atom RMS is
0.50749 Å, 0.50467 Å after removing common translation and 0.50357 Å after a
proper rigid least-squares decomposition. The movement is predominantly internal.
This decomposition exports no aligned coordinates and changes neither the
crystallographic/map frame nor existing scores/views.

No-op RMS decreases occur across families: 20 pair-plane angles 11.226→3.383°,
38 adjacent-stack angles 9.193→4.130°, 960 covalent bonds 0.01810→0.00346 Å,
and 1,474 covalent angles 1.657→1.147°. These within-family reductions cannot
compare force/energy across families or identify pair flattening as the causal
driver. The supplementary receipt is outside the immutable archive above.
Rowan confirms prior Cedar protocols do not supply a matched causal contrast on
these exact inputs. If that question becomes necessary, prospectively compare an
ordinary production protocol with the fixed-unit arm, preserving the declared
pairs, starting model and source observations and reporting effective/common
sets. Coordinate protocol ownership first; do not treat changed protocols as a
pure weight intervention or start an Rfree-driven search. No new matrix is queued.

## W154 — Name map sources independently of coordinate states

**2026-11-19; isolated presentation patch.** The previous renderer reused model
labels for density sources. A fixed control map could therefore be named as if
it came from the displaced model. Optional `map_labels` now independently names
the two map slots in the dropdown and stationary-map status. Omission retains
the existing model-label default. Bounded escaped text, one-pass replacement and
validation-before-write remain enforced. No geometry, mesh, shader, sampling,
source authentication, checkpoint selection or native refinement policy changes.
The input scene stays schema 1; rendered presentation metadata adds
`display_map_labels`. Existing API calls and saved scenes need no migration.

Code **`71dda01aecc616a8bc8f94506567ef3a3218842a`** changes
`src/nasolve/density_inspection.py`, `src/nasolve/data/density-inspection.html`,
`tests/test_density_inspection.py`, `docs/architecture.md` and `CHANGELOG.md`.
The meaningful new regression fails on the old API with the unexpected
`map_labels` argument, then passes for independent/default/escaped labels,
unchanged scientific data and invalid-label refusal before file creation.

**Validation:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <Python3.12> -B -m
pytest -q -p no:cacheprovider tests/test_density_inspection.py
tests/test_topostitch_roadmap.py` passes **30**. One complete pinned-source run
passes **2,092 tests +234 subtests**, 101.77 s pytest time, unchanged tracked files
and a stopped process. The full command uses the existing `w149-full-suite.py`
controller, `-o addopts= --durations=20 --junitxml ... tests --basetemp ...`,
with explicit pinned NARestraints source. Initial setup selected Willow's older
process API and stopped before any tests; the recorded second setup reuses the
maintained Cedar process owner exactly as prior W149 qualification. No failed
suite is represented as a pass.

A `pip wheel --no-deps --no-build-isolation` build and `pip install --no-deps
--no-compile --target ...` installation pass. After relocating the package and
removing both build source and old installation, the existing ten affected owner
modules pass **159 tests +53 subtests**; import and `nasolve show --help` pass.
All 93 installed package files remain exact. Wheel SHA256
`89b75e66f749e7956a383ee0ee93a66440db5b9d402195345d8d4735ca8971f6`.
Source/installed rendering of the unchanged W143 science gives identical HTML;
all original scene fields and shader source remain exact. Seventeen mocked
WebGL/control checks verify independent map labels survive model switching;
W153's two real scenes pass the same contracts. Hazel independently reviews the
source/template and both published scientific payloads, without duplicating
these tests. Browser/GPU rendering and stage integration remain separate gates.

Archive: NASolve anchor
`branch-artifacts/willow/w154-density-labels-qualification-2026-11-19.zip`,
46 indexed files +manifest, 2,437,749 bytes, SHA256
`7e8416ce8abc0230589cf3e5365d86e2986001440e08d851c4700c204a7b8318`.
Hazel's detailed review is separately bound at
`branch-artifacts/Alder/coordination-w154-review-20261119.json`.
After archive/hash, inode and stopped-process checks, only two owned scratch
roots are retired: **3,956 files /29,020,618 bytes**. Scientific runs, checkouts,
shared Python/NARestraints and C407 installation remain. W150's receiving-owner
candidate remains frozen and deferred; this patch is not silently folded into
its earlier compatibility receipt or adopted into Alder/Cedar.

## W155 — Record density counterexamples before proposing backbone motion

**2026-11-19; prescribed scattering diagnostic only.** W153 leaves a strong
negative phosphate feature despite improved geometry. Before introducing a
red-density motion rule, check an explicit counterexample set. Hazel confirms
that her existing global-scale/ADP invariance and own/common-coordinate sampling
controls do not already supply this local contrast. No additional refinement,
experimental attribution or detector implementation is undertaken.

The unchanged deposited 5W6W source from W152 supplies 859 scatterers. Only
**B2 P, OP1 and OP2** vary; the other 856 scatterers retain exact fractional sites,
occupancy, isotropic/anisotropic displacement fields, types and anomalous terms.
Use the same 7,554 nonanomalous HKLs through 3.06 Å, the same 144×144×125 grid
and `n_gaussian` direct structure factors. The zero control subtracts identical
complex coefficients. Three separate prescribed comparisons use:

| Error | Prescribed true/model distinction | Exact value at modeled P |
| --- | --- | ---: |
| Displacement | Original truth; model group translated +0.75 Å along Cartesian x | −1.454744 |
| Occupancy | True group Q=0.5; model retains Q=1 at the same sites | −2.802522 |
| ADP | True group B increases by 40 Å²; model retains source B at the same sites | −1.685074 |

These are **complex `F_true − F_model`**, with their prescribed phases, divided
by one common reference Fcalc-map sigma. They are **not amplitude differences,
experimental mFo−DFc maps or ordinary Fo−Fc sigma units**. No noise, scales,
coordinates or occupancies are fitted. F000 is omitted; electron-count integrals
are unavailable and finite-resolution/zero-order effects can produce ripples.
The deliberately shifted phosphate group is a strained diagnostic scattering
model, not a chemically acceptable repair proposal.

All three errors produce a negative modeled-P feature. The ADP case also has a
broader positive feature without translation. Within the displaced group, OP1
is **positive (+0.2511)** while P is negative: not every atom in a misplaced group
must have the same residual sign. This demonstrates ambiguity, not a general
shape classifier, identification of W153's cause or proof of a motion vector.
No calibration threshold or automatic action follows.

**Checks:** the zero coefficients/map are exactly zero. Full-model contrasts
match the three-atom-only contribution within **4.82e−12** structure-factor units;
nearest-voxel direct Fourier and FFT values agree within **1.18e−14** common
reference units. Native arrays have identical ordered HKLs; serialized arrays
retain 7,554 unique reflections and no F000. Q and B change independently.
Reported numerical metrics use full-precision arrays; serialized MTZ amplitudes
and phases have float32 precision. Source PDB and immutable result remain exact.
Hazel independently checks source/plan/worker/result/MTZ hashes, Cartesian motion,
Q/B deltas, HKLs and zero control, and reviews the retained arithmetic evidence;
she does not rerun the coefficient calculation.

**Runtime-provenance limit:** the direct launcher is the selected
`phenix-2.2.1-6174/bin/phenix.python`, but the original version API returned an
empty string. Preserve that original field and result hash
`7a6b1e1e485b9dfffbbeed89b4fd248faf9457e83a1518a2e07e65cad0b39fce`.
A separate identity-only launch using `installation_from_candidate`'s environment
identifies the installation as **Phenix 2.2.1-6174** and records interpreter/module
hashes. It is not a retroactive capture of the original process version/environment
or complete loaded-module inventory. No science calculation is repeated to hide
this gap; future native diagnostics should capture SDK environment/version at
launch. This contrast is not an installed native-policy qualification.

Commands: `PYTHONDONTWRITEBYTECODE=1 <shared Python3.12> -B
runners/w155-scattering.py` captures the predeclared ≤180 s native worker (actual
**2.05 s**, stopped); `w155-runtime-identity.py` captures the separate identity
probe, also stopped, with zero new scattering calculations/refinements.
`w155-checkout.py` uses the existing Matplotlib environment for a PNG/SVG report.
The final figure is visually inspected after correcting title/footer overlap;
scientific data do not change. No new source tests, installation or unchanged full
suite are needed for this private diagnostic/docs update. Roadmap checks reuse
the existing eight focused cases and generated-view/reference audit.

Human checkout: GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-19_density-ambiguity/review.html` (four files).
The three common-scale slices and line profiles explicitly label prescribed/model
sites and the non-ML normalization. The archived package includes the source,
frozen plan, native coefficients/result, peer review, provenance supplement,
figure and final report. NASolve anchor
`branch-artifacts/willow/w155-density-counterexamples-2026-11-19.zip` contains
24 indexed files +manifest, 1,014,541 bytes, SHA256
`addacfb60c7befbc46b834761f2aacab9ffe7989b6f3da7bf47efadeb6655c86`.
All hashes verify. Science remains local, excluded from Git; archive integrity is
not portable native execution. No runtime/schema/CLI/compatibility migration.

**Next:** retain these prescribed errors as required counterexamples before any
motion detector. Model-assisted phases, observed-amplitude uncertainty, occupancy/
ADP interactions, noisy healthy controls and geometry/packing context still need
qualification with the scientist. Do not promote nearby green/red patterns,
a single atom's sign or this reference normalization into a bending instruction.
S06 remains PARTIAL; no further native matrix is queued from this result alone.

## W157 — Separate scaling and coordinate recovery in saved histories

**2026-11-19; saved-data audit only.** Following W156, extract the native
step-by-step tables from the three W153 logs already pinned in the immutable
archive. No original files or runtime code changed, and no refinement ran.
The small experimental checkout now contains an inline scientific SVG showing
Rwork/Rfree after the first scaling step, with scale and XYZ points distinct.

| State | Reference Rfree | Positive Rfree | Negative Rfree |
| --- | --- | --- | --- |
| Before initial bulk-solvent/scaling | .3207 | .3437 | .3376 |
| First scaled state, before XYZ | .2413 | .2637 | .2624 |
| Final after five cycles and final scaling | .2600 | .2579 | .2611 |

The first large drop does not establish coordinate recovery. Positive/negative
starts recover some penalty relative to their own scaled starts, while the
unperturbed control changes too. Reference minimizations use 100 / 100 / 100 / 100 / 100
iterations; positive 100 / 100 / 36 / 100 / 44; negative 100 / 100 / 42 / 100 / 100.
Neither hitting the cap nor stopping below it establishes convergence. The
fixed-budget endpoints retain the W156 map-review interpretation.

The positive effective total is 5,137 at first scaling and 5,136 from second
scaling onward. **Those counts do not identify stagewise HKL/Free membership.**
The separate original endpoint audit identifies missing work(5,18,-1) and
unchanged 507 Free. Initial figure wording conflated those facts; its original
receipt/recipe/figure/report are preserved in
`branch-artifacts/willow/w153-experimental-backbone/stage-history-display-attempt01.zip`.
The corrected version retains all 84 stage rows and plotted order exactly.
Hazel independently checked the archive/member/worker/figure hashes, 84 numeric
rows, 15 iteration records, 18 scale counts and endpoint agreement, then reviewed
the wording amendment. Final PNG inspected without clipping; no browser/GPU
qualification follows from this static figure.

The existing `parse_refinement_statistics.cycle_series` is log-match order, not
native stage identity: trailing repeated Start summaries can appear in that
list. The local report uses the labelled native table instead. Rowan is informed;
no shared parser patch or backward-compatibility change is made here. A future
recovery display must use qualified stage identities and distinguish final
scaling from coordinate motion. These curves supply no intermediate XYZ snapshots.

**Validation:** with `PYTHONDONTWRITEBYTECODE=1` and
`MPLCONFIGDIR=/private/tmp/willow-science-mpl`, the existing Matplotlib 3.11.2
environment runs `-B branch-artifacts/willow/runners/w153-stage-history.py`.
The worker verifies the original archive, source members, five macrocycles,
start/final summaries, retained execution values and six scaling blocks per arm.
The corrected run reproduces all numeric cases from the preserved first version.
Native version remains the original Phenix 2.2.1-6174; this audit launches none.
Roadmap `--write`/`--check`, focused eight roadmap tests and `git diff --check`
pass. No full suite or installation repeat: production code is unchanged from
qualified W154. The receiving-owner/shared native gates remain separate.

The 12-file indexed supplement (+manifest), 341,194 bytes, is at NASolve anchor
`branch-artifacts/willow/w153-cold-history-supplement-2026-11-19.zip`, SHA256
`5355f21a40ecaaa3e4a0c4ee4f7ad9a58777b5a439e64abe1427b9fc56787f31`.
It binds the motion audit, final history/figures, original display correction,
peer reviews and updated human report/manifest without duplicating native data.
Original W153 archive and all scientific runs remain unchanged. All science is
local; this is integrity evidence, not portable execution or accepted repair.

## W159 — Compare ordinary recovery with the fixed-unit baseline

**Outcome.** The same undeformed deposited 5W6W model now has a completed ordinary-
recipe diagnostic beside W153's retained fixed-unit XYZ control. The selected
205-atom RMS to deposited coordinates is **0.591 versus 0.522 Å**. Common effective
Rwork/Rfree is **0.226432/0.267735 versus 0.239233/0.259995** (4,630 work and 507
original Free). Both start from the same first-scaled .2238/.2413 state. The
ordinary recipe therefore does not establish an improved reference baseline.
No opposite-start matrix, lowest-Rfree selection or repair acceptance follows.

**Ownership and protocol.** Rowan confirmed that the deposited-source diagnostic
has no ordinary AutoMR/PostMR root, and `checkpoints add` requires an existing
valid run. We did not manufacture ancestry, remove counted gates or repeat MR.
Instead, the existing C407 `autorefine.write_recipe_parameters`,
`build_refine_command` and `refinement_parallelity` native owners execute the
comparison. This is not `execute_autorefine`/ordinary checkpoint qualification.
The installed 304-file C407 manifest remains exact at
`f83562b0c1f61eb5b696d1ba75ebb4578b22c7ad`.

Phenix **2.2.1-6174**, selected local native source/extension profile, performed
one complete five-cycle, one-process refinement (about 17.6 minutes). The SDK's
family-version field is `2.2.1`; the map worker captures the full native version.
The same seed 1, 100-iteration cap, bulk scaling, no-added-atoms, no-overall-B-shift
and CDL-off policies are retained. The ordinary recipe changes optimized XYZ/ADP
weights, XYZ scale 0.5, group ADPs and real-space-site steps together. Its auto target
uses LS in cycles 1–2 and ML in 3–5. Eligible occupancy selection has zero atoms;
rotamer fitting reports zero residues. Native XYZ weight selection consults Free
data. Equal cycle budgets are not equal optimizer work, and final Rfree cannot
independently select the protocol. Four selected-weight XYZ counts are 100; the
last is 90, without recorded stopping reasons or all internal trial counts.

**Geometry and scattering.** All 859 atom identities, 2,569 original bond/angle
definitions, 58 pair/stack groups, 38 existing O3′–P links and 126 checked sugar signs
survive. Local covalent bond/angle RMS is .00851 Å/2.142° versus .00357 Å/1.201°;
the native pooled bond statistic also contains custom terms and is not relabeled
covalent RMS. Pair/stack unsigned plane RMS is 4.749°/5.308° versus 3.383°/4.130°.
All 859 B factors change; all occupancies remain 1. B2 P increases 90.39→112.52 Å²,
yet its own-map negative sample is −8.38σ versus −8.09σ. At the common deposited
site it is −8.04σ versus −7.57σ. Separate whole-cell normalization, model phases and
coupled protocol changes prevent attributing this feature to position or ADP.

**Data and display.** Raw F/SIGF and original flag membership are exact. Neither
endpoint excludes an observation; common endpoint arithmetic agrees with native
rounded R values, with no refit. Saved unfilled ML maps include all 507 Free rows.
The predeclared B2–4 view uses 33 actual atoms / 35 native covalent bonds and 62 checked
meshes. W154's unchanged renderer keeps map and model selection independent.
Seventeen offline control/buffer contracts pass; these are not browser/GPU review.
ChimeraX 1.12 headless loading confirms three 859-atom models, 205 visible atoms each,
identity scene transforms and exact file coordinates within serialization precision.
Its automatic bond inference differs (960 fixed / 962 ordinary); native geometry
definitions, not those inferred display bonds, establish the scientific links.
The initial hidden-model focus error and sandbox cache refusal are preserved;
the corrected loader passed with an explicit result receipt, not exit code alone.

**Evidence and validation.** Main `NASolve` anchor:
`branch-artifacts/willow/w159-recovery-protocol-attempt03/` contains exact plan,
preflight/final geometry, 43 native stage rows, maps, scene and viewer receipts.
`w159-recovery-protocol-evidence-2026-11-20.zip` verifies 89 indexed files;
SHA256 `bc11417d2cacdfd5e45f56ceca0d858550b8f0e660397001ef8f056538bad9d0`.
This is a local integrity archive, not a portable continuation. Two prelaunch
controller refusals are archived; the successful run and source inputs remain.
The compact human packet is at GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-20_recovery-protocol/review.html`.

Exact local commands use `PYTHONDONTWRITEBYTECODE=1` and the retained Python at
`/private/tmp/willow-w94-pivot/env/bin/python -B`, with runners under the main
`branch-artifacts/willow/runners/`: `w159-protocol.py preflight`, `audit-preflight`,
`refine`, `audit-final`; `w159-final-audit.py`; `w159-map-review.py`;
`w159-scene-launch.py`; `w159-checkout.py`; and `w159-archive.py`. All final native
and readback checks pass. `w154-view-contract-check.mjs:check` supplies 17 offline
inspector checks; ChimeraX `--nogui --exit w159-viewer-check.py` supplies actual
coordinate inventory. No production source/schema changed: existing readers need
no migration, raw scientific artifacts stay out of Git, and no full suite or
installation repeat is claimed. Documentation uses the focused 8-test roadmap
check, roadmap `--write`/`--check` and `git diff --check`.

## W160 — Retain ambiguity and normalization context in model-assisted maps

**Bounded result.** W158's three-case noiseless model-assisted panel is complete.
One synthetic truth supplies all 7,554 amplitudes at 3.06 Å. Its B2 P/OP1/OP2
have deposited B +40 Å²; all other atom/scattering fields remain exact. Compare
that correct model, the same model with those three sites shifted +0.75 Å in X,
and the deposited lower-B group at the correct sites. Each has all 859 atoms.
Known position and B errors both give negative modeled-P difference density:
−0.804 and −1.524 in a common truth-map normalization. This supports retaining
alternative explanations, not classifying the experimental W153/W159 feature.

**The zero control matters.** Its common-scale sample is −3.11×10⁻¹⁵; difference-
map raw σ / truth-map raw σ is 1.916×10⁻¹⁵. Normalizing that numerical-scale
residual by its own σ nevertheless reports −1.624σ. The result is retained, not
forced to zero. Own-map samples −28.09/−65.56σ in the two error cases are also
idealized noiseless values, not experimental significance. A known truth-map
denominator is available here because this is synthetic; it does not establish
an operational normalization policy or threshold for measured campaigns.

**Native method and ownership.** Hazel confirmed that her maintained metal
capture wrapper is site/result-specific; no general generator should be invented
or that wrapper stretched. This panel uses native
`mmtbx.f_model.manager.map_coefficients` and the existing W147 exact coefficient
reader. Phenix **2.2.1-6174** is captured in the native process, with 11 Python/
extension source hashes. One complete native calculation took about 10.7 s;
there are no coordinate, B, occupancy or scale refinement calls. Unit isotropic/
anisotropic scales and zero solvent contributions are explicit; accidental
`update_all_scales` calls are guarded. No new product code or defaults result.

The same deterministic W152 hash rule supplies 389 synthetic Free flags. The
native alpha/beta/FOM estimate uses these flags, and both unfilled ML maps include
all reflections. Model phases and likelihood weights change together: this is
not a phase-only intervention or independent validation. Nominal σF=0.02F is a
field, not sampled noise or a calibrated experimental uncertainty model.

**Checks and view.** All model states, observation/flag tuples, unit scales and
Fmodel arrays stay unchanged during map generation. A separate expression for
the declared centric/acentric ML coefficient formula agrees within 5.31×10⁻¹²;
direct Fourier/FFT voxel values agree within 5.16×10⁻¹⁴. Six complex arrays pass
exact-label/HKL and float32 readback checks. Hazel's independent **80-check** cold
review binds input hashes, reconstructs all synthetic flag identities and checks
normalization arithmetic without another native call. It reviews, rather than
independently recalculates, the producer's in-memory/formula assertions.

The visually checked six-panel common-scale figure, vector export, report and
manifest are at GitHub workspace anchor
`ScienceCheckouts/Linden/2026-11-20_model-assisted-density/review.html`.
No graphical/browser capability is implied beyond reviewing that generated PNG.
The shifted group is a prescribed potentially strained scattering error, not a
proposed chemical repair. Noise, uncertain observations/model phases, local
geometric context and scientist calibration remain prerequisites for a detector.

**Evidence and reproducibility.** Main NASolve anchor:
`branch-artifacts/willow/w160-model-assisted-density/` holds plan, native result,
execution, figure and archive receipts. The 22-file local archive
`w160-model-assisted-density-evidence-2026-11-20.zip` has SHA256
`fea85c6aff4a5bf95a14b4909ce081b13fe721629ac2eee86ac869a354986886`.
Hazel's cold receipt is
`branch-artifacts/Alder/a01-current-profile-20261120-01/w160-cold-review.json`.
This is an integrity archive, not a portable executable checkpoint. Raw science
is excluded from Git.

Exact runner entry: `PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w160-model-assisted.py`;
it binds the SDK environment and owned 240 s native worker. `w160-figure.py` runs
through the same native Python environment; `w160-archive.py` verifies all members.
No production source/schema/compatibility change or installation migration;
documentation uses the eight focused roadmap tests, roadmap `--write`/`--check`
and `git diff --check`. No full-suite/install repeat or scientific acceptance is
claimed. Do not rerun W155/W160 just to reestablish the ambiguity they now record.

## W161 — Locate mixed local recovery and reuse the known screening diagnosis

**Saved results only.** The W159 refinement is not repeated. A cold read separates
four unchanged native bond/angle families, all 42 residues and 459 backbone atoms.
Each atom's deposited/fixed/ordinary coordinates are sampled in each of the two
saved ordinary and difference maps: **5,508 fixed-map samples**. Recomputed values
agree with W159's own/common samples within 10⁻¹⁰. All 41 P atoms remain; these
are distinct from the 38 existing O3′–P links. B1/C8/D1 have terminal phosphorus.
The first audit incorrectly equated those counts; its stopped attempt and source
are archived, then the read-only audit was corrected against the actual inventory.

| RMS deviation from unchanged targets | Deposited | Fixed endpoint | Ordinary endpoint |
| --- | ---: | ---: | ---: |
| 960 covalent bonds / Å | .01810 | .00346 | .00741 |
| 1,474 covalent angles / ° | 1.657 | 1.147 | 1.833 |
| 51 declared pair-contact distances / Å | .4824 | .2467 | .3392 |
| 84 declared pair-contact angles / ° | 19.474 | 3.313 | 6.277 |

Largest ordinary movement **A10 C5′: 2.543 Å**. Its 2mFo−DFc sample rises from
1.21→2.96σ in the held fixed-unit map and 1.40→2.75σ in the held ordinary map.
**D2 OP1: 2.520 Å** instead moves to lower ordinary density in both sources
(1.78→1.23σ and1.58→1.14σ). A10's other atoms do not uniformly improve. These are
posthoc endpoint descriptions, not independent map validation, causal restraint
attribution, correct-direction inference or a whole-model winner. Native printed
family residual sums are retained, not presented as a full force/energy split.

**Known screening limitation, now explicit in this baseline.** All **76** printed
XYZ candidates (16/17/14/14/15 by cycle) fail the initial .015 Å bond-RMS screen.
Even the most favorable printed rounding bounds exceed it; cycle minima are
.070/.058/.069/.064/.066 Å. The actual pinned XYZ scorer source consequently
requires its default fallback. `r_free_only=False` is explicit. Printed precision
does not recover every fallback tie or original source membership for each trial.
At the final endpoint, 51 pair distances contribute **99.11% of unweighted squared
bond deviations**, reconstructing pooled RMS .07652 Å versus logged .077 Å.
This is not their energy or force share. Pooled angle RMS likewise reconstructs
2.30268° versus2.303°. The additional current statistics/linking source inspection
is labeled separately from modules captured during W159.

This is the C395/C396 issue already documented under W135/W136, not a newly
discovered policy fix. C396's source-matched eligibility change altered choices
without automatically improving its result. Do not repeat or activate that
selector, change forces, or relax criteria because this baseline also falls back.

**Inspection and evidence.** The existing eight-file local recovery packet gains
one `a9-11.html` view plus context in `review.html`; its three coordinate files
are unchanged. The posthoc A9–11 window displays 33 atoms/35 native covalent bonds
against independently named endpoint maps, using W154 unchanged. All 62 meshes
and 17 offline control/buffer checks pass; actual browser/GPU review remains open.
The old human packet and failed audit are retained. Main NASolve anchor:
`branch-artifacts/willow/w161-recovery-context/`; the verified 26-file archive
`w161-saved-recovery-context-2026-11-20.zip` has SHA256
`b7f8ae71b4be1738507be6574727ce4148e20a028d18af689de7c0cb9f8c361c`.
Its parent points to the immutable W159 archive; no portable-run claim.

Exact cold entry points under main `branch-artifacts/willow/runners/`:
`w161-recovery-context.py`, `w161-weight-screen.py`, `w161-scene.py`,
`w161-checkout.py`, `w161-archive.py`. Controllers use
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B`;
map/mesh workers run through the bound Phenix2.2.1-6174 SDK with 180 s ownership.
The weight review launches no native tool. Eight focused roadmap tests,
roadmap `--write`/`--check` and `git diff --check` cover docs-only publication.
No runtime/schema/install change or migration, full-suite rerun or scientific
acceptance; raw artifacts stay local. Cedar construction/orientation work and
Hazel's private objective profiles remain separately owned and unmerged.


## W162 — Bind the selected backbone state and retain the derivative limit

One passive repetition of the exact W159 ordinary recipe qualifies a private
LS/ML reader without changing the target schedule. All 859 final atom records,
both saved reflection/map MTZ arrays and printed trials match W159 exactly.
The new capture records 76 returned XYZ states (16/17/14/14/15 by cycle), including
actual selected trial identity. W159 did not record those internals, so final
neutrality is not a retrospective whole-trajectory proof. The new passive trace
is the reference for its separate replay. The selected last-cycle frame is
sequence 73, weight 7, before later refresh/ADP, with 11,115 counted terms.
It returns after 90 iterations with a recorded rounding-error line-search message;
the shared stopping classifier reports `unreported`, not convergence.

The dedicated replay matches the complete 73-state captured prefix and selected
snapshot. One prospectively fixed paired A9–15/B7–1 tapered rotation protects both
endpoint pairs and all context; 205 atoms move. The exact maintained TaperedMotion
pullback is checked independently using fixed-axis Rodrigues tangents. Nine native
evaluations include repeat, ±10⁻⁵/±10⁻⁴ rad derivative checks and restoration.
Geometry and combined derivatives pass. Data-only slopes differ by 4.52–5.45×10⁻⁶
per radian against a predeclared bound about 1.41×10⁻⁶, so the finite ±degree
scan is **not run**. No tolerance is relaxed after seeing this result.

Both sampled numerical data slopes and weighted-geometry slopes favor the same
local direction in this one mode; this does not establish finite benefit or
identify the source of W159's drift. Direct and original FFT targets and complete
gradients restore with zero recorded error, and captured inventory membership
stays fixed. The diagnostic stops deliberately; it never resumes optimization
or becomes a completed refinement child. **194 passive and 120 profile cold
checks** pass as evidence-readback checks, not derivative/scientific acceptance.

**Capture scope correction.** The inherited C397 inventory omits dihedral
`limit`, `top_out` and `slack`. Actual parallelity fields, including limit, are
explicitly collected, but this is not a complete six-family state claim. The
maintained `topostitch_native_terms.checked_proxy_rows` already checks the missing
live policies; no supported-reader bug or new product fix is implied. The LS/ML
reader records directly consumed core values, not all Miller-array metadata.
Original frozen helpers and failed setup attempts remain preserved. W164's
separate reconstruction checks cannot fill historical callback fields.

This bounded mechanism study is closed as limited. Do not repeat it or the
C395–C400 work simply to make the control perfect. Future supported capture must
bind all required live policies through existing owners, while ordinary
topology-driven recovery can proceed under its own explicit contract.

Main NASolve anchor: `branch-artifacts/willow/w162-current-backbone-attempt02/`.
Archive `branch-artifacts/willow/w162-current-backbone-evidence-2026-11-20.zip`,
142 files, SHA256 `7c5bb2803747e78d3ddfbe4e38c27f059d81fbefd4fc7dadbd976eec7581a66d`.
Entry points under `branch-artifacts/willow/runners/`: `w162-capture.py`
(`plan`, `preflight`, `review-preflight`, `passive`), `w162-passive-review.py`,
`w162-replay.py` (`plan`, `run`), `w162-profile-review.py`, `w162-archive.py`.
Controllers use `PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B`;
native jobs bind Phenix **2.2.1-6174**, seed 1/nproc 1 and owned 2,100 s limits.
One complete passive refinement and one intentionally stopped replay; no ordinary
PostMR ancestry, generic capture API, numerical-policy change or acceptance.

## W163 — Retain known backbone links before larger displacement recovery

The W152 5W6W control is extended from prescribed ±5° to **±15°** tapered
rigid-residue rotations under the same canonical paired window and generating
synthetic diffraction. These are motion parameters, not a measured total helix
bend. Selected 205-atom starting RMS is **2.288 Å**, with maximum motion **4.79 Å**;
both endpoint pairs and all other atoms stay fixed in the input displacement.
All 859 coordinates may subsequently refine.

The first negative start exposes a preparation boundary: its B2 O3′–B3 P distance
is **3.835877 Å**. Native `pdb_interpretation.link_distance_cutoff=3` drops that
declared bond and four flank angles (C3′–O3′–P and O3′–P–O5′/OP1/OP2). Its
2,569-term bond/angle inventory falls to 2,564. The first two-start attempt is
held after preflight; **no refinement runs on that changed topology**.

A fresh private matched **4 Å interpretation envelope** retains the existing
canonical links through the native library, including their angles and exclusion
shells. This is not an explicit bond-only edit, global default, chemical inference
or symmetry-seam solution. A default-reference dry-run and widened-reference
dry-run have identical captured context. Both deformed inputs retain all 38
source links, 58 complete plane definitions, captured bonded parameters and all
fixed nonbonded assignments/potential/search/symmetry/exclusions. Coordinate-
dependent neighbor membership legitimately changes. The original torsion-policy
omission is explicitly qualified as described under W162.

Fresh unchanged/positive/negative siblings receive five cycles, 100-iteration
cap, seed 1/nproc 1, fixed unit weights, fixed B/Q and identical noiseless 3.06 Å
data/Free/restraints through frozen C407 code `f83562b0`. No scale refinement or
generating-coordinate tether. The widened unchanged control reproduces W152
atom records and map arrays exactly. Selected RMS becomes **0.01436/0.75845/
0.27904 Å**. Positive/negative local covalent bond RMS improves from
0.143/0.205 to **0.00787/0.00782 Å**; local angle RMS becomes **2.010/1.953°**.
All 126 checked ordered sugar signs and 38 links survive. Native scores continue
improving through the fixed budget; this is partial recovery, not convergence.

Main anchors: `branch-artifacts/willow/w163-larger-bends/` preserves the held
default-envelope attempt; `branch-artifacts/willow/w163-link-envelope/` holds
the admitted matched experiment. Exact entry points: `w163-larger-bends.py`,
`w163-link-envelope.py` (`plan`, `preflight`, `refine`),
`w163-context-review.py` and `w163-linked-readback.py` (preflight and `--final`),
`w163-execution-review.py`. Same controller Python as W162; actual native
**Phenix 2.2.1-6174** preflights and three complete refinements. Context capture
adds one explicitly recorded post-program energy-only observation, not an
optimizer-frame measurement. No scientific-data publication or runtime change.

## W164 — Measure a matched recovery window and retain local distortion

Before seeing another outcome, freeze one additional five-cycle recovery window
for **all three** W163 siblings, with unchanged data, weights, restraints and
iteration cap. Each starts from its own saved rounded PDB. This is five plus five
cycles with a restart, not one uninterrupted ten-cycle trajectory or ordinary
PostMR lineage. All outcomes remain, without choosing a lowest-Rfree intermediate.

| Condition | Initial RMS to generator / Å | After five cycles / Å | After continuation / Å | Final Rwork / Rfree |
| --- | ---: | ---: | ---: | --- |
| Unchanged reference | 0 | .01436 | .01436 | .0062 / .0067 |
| Positive displacement | 2.28803 | .75845 | .25257 | .0211 / .0259 |
| Negative displacement | 2.28799 | .27904 | .03972 | .0086 / .0100 |

These are unaligned crystal-frame distances over the same 205 atoms. The
additional unchanged-control movement is only .00020 Å RMS. All 859 atom
identities, B/Q, 38 declared links and 126 checked sugar signs remain. The six
endpoints preserve all **7,554 original raw and effective F/σF/Free tuples**;
unrecorded intermediate effective-HKL trajectories are not inferred from that.

**Low Rfree does not finish the geometry job.** Positive B2 O3′ remains **1.412 Å**
from the generator and C2′ **1.178 Å** away. The B2 O3′–B3 P–OP2 angle is about
76.71° versus a 108° target (**31.32° deviation**); A13 C5′–C4′–C3′ also remains
distorted. Positive local bond/angle RMS is .01418 Å/3.717°, versus negative
.01441 Å/2.024°. Sugar-volume sign preservation is not complete pucker validation.
The evidence supports strong recovery in both directions and a remaining local
positive-arm distortion, not automatic acceptance or a new round of weight tuning.

**Supplementary policy check.** Nine fresh saved-coordinate native dry-runs
(three starts, five-cycle endpoints and continued endpoints) call the exact
existing `checked_proxy_rows` owner. All 443 dihedrals have the same explicit
`limit=-1`, `top_out=False`, `slack=0` and identity images, alongside identical
62 planarity definitions and unchanged declared geometry/exclusion context.
These reconstructed-manager observations supplement interpretation evidence;
they do not retrospectively capture omitted historical optimizer fields.
No fitting occurs during these nine checks. The combined cold audit passes
**601 checks**, including the exact endpoint diffraction tuples.

**Human inspection.** GitHub workspace anchor:
`ScienceCheckouts/Linden/2026-11-20_larger-bend-recovery/review.html`.
`open_report.py` uses standard Python and can verify all files with `--check`.
`open_inspection.py` opens six models in ChimeraX; three offline HTML comparisons
use W154's unchanged renderer, real coordinates and original native covalent bonds.
All 51 offline control/buffer checks and the separate **ChimeraX 1.12** headless
859-atom/205-visible-atom inventory pass. No real GPU/browser visual pass is claimed.
ChimeraX infers display bonds (961 for its relaxed control versus 960 native
covalent bonds); scientific linkage assertions use the native graph.

Main NASolve anchor: `branch-artifacts/willow/w164-larger-bend-continuation/`.
The joint W163/W164 631-file integrity archive is
`branch-artifacts/willow/w163-w164-larger-bend-evidence-2026-11-20.zip`, SHA256
`1ae264840a69398147d8317241845c5d968a84292970abc8d6dc3761a8bbd54b`.
Entry points: `w164-continuation.py` (`plan`, `preflight`, `refine`),
`w164-context-review.py` / `w164-readback.py` (preflight and `--final`),
`w164-execution-review.py`, `w164-live-policy.py` (`plan`, `run`),
`w164-science-review.py`, `w164-checkout.py`, `w164-viewer-check.py`,
`w164-archive.py`. The immutable local derivation receipts bind reused readers
and the extracted unchanged live-policy function. Same controller/native versions
as W163; three complete additional refinements and nine dry-runs. Archives are
integrity records, **not portable/resumable checkpoints**; raw science stays local.

W162–W164 change documentation and local diagnostics only: no installed source,
runtime schema, default, compatibility or migration change. Validation for the
tracked update: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
tests/test_topostitch_roadmap.py`, roadmap `--write` / `--check`, local evidence
checksum checks and `git diff --check`. No full suite by the user's instruction;
no installation repeat is needed for unchanged product code. S04/S05/S06 remain
partial. Next inspect local distortion and qualify parent-derived topology
retention through shared owners; do not turn the private 4 Å example into a
production heuristic or rerun completed objective sweeps.


## W166 — Carry known parent geometry without a global cutoff change

**Question and scope.** Can the intact parent's native geometry manager retain
the declared canonical same-ASU topology when its coordinates are changed to the
existing W163 signed 15° starts? Rowan confirmed Cedar can audit missing/extra
links but does not currently force a stretched parent link through preparation.
This diagnostic reuses the C407 installed execution/Phenix owners, C397 observed
inventory, complete parallelity reader, fixed nonbonded-policy reader and W164's
unchanged supplemental live torsion/plane owner. It adds no product helper.

**Prospective comparison.** One intact parent is interpreted at the unchanged
native 3 Å cutoff. Its returned dry-run manager evaluates initial, positive,
restored, negative and restored coordinates. Two independent 4 Å preparations
evaluate the same positive/negative states, reusing W163's explicitly private
control policy. The qualified run has **three dry-runs and seven energy/gradient
calls**, with **zero refinement/optimizer calls**, on **Phenix 2.2.1-6174**.
Per-component raw energy/gradient agreement was set beforehand to
`1e-9 + 1e-10 * max(abs(a), abs(b))`. Nonbonded neighbor enumeration and normalized
objectives are separately observed, not assumed invariant across different sites.

**Result.** All 38 intended O3′–P links survive. The negative child's B2 O3′–B3 P
distance is **3.83587656 Å**, yet its bond and four flank angles remain, alongside
identical six-family definitions, 58 complete parallelity terms, 443 explicitly
checked torsion policies, 62 planarity definitions and fixed graph exclusions,
types, functions and search policy. Raw geometry energy differences versus
independent preparation are at most **1.02e-10** and raw Cartesian gradient
differences at most **1.92e-9**, within the declared componentwise bound.
Normalized target differences are at most **8.9e-15**; both restoration checks
reproduce the initial energy and gradient exactly. Same-coordinate nonbonded
lists/counts match here (positive 11,378 total terms, negative 11,084; parent
11,102). This does not resolve C400's general normalization-history question.
The cold readback passes **77 checks**.

**Identity lesson and retained failures.** Native preparation moves terminal
D1 OP3 in the array, changing 20 indices despite `sort_atoms=False`. Transfer uses
an explicit unique full-label bijection, not index coincidence or nearest atoms.
Input non-XYZ state is checked against the source input; the separately prepared
native hierarchy/scatterer state stays unchanged and matches the fresh controls.
Raw element/charge whitespace is normalized by preparation, so raw-versus-native
representation equality is not itself a chemical check. Five earlier wrapper
refusals are preserved: dropped forwarded arguments, exact float equality across
fractional roundtrip, assumed atom order, raw/prepared representation comparison,
and temporary iotbx hierarchy lifetime. None transferred child coordinates or
ran refinement. Four performed native preparation and two recorded an initial
energy evaluation; the first only printed native usage. These are diagnostic
setup failures, not failures of the physical retention hypothesis.

**Artifacts and validation.** Main NASolve anchor:
`branch-artifacts/willow/w166-parent-geometry-attempt06/review.json`.
`runners/w166-parent-geometry.py plan` / `run` freeze and execute the prospective
experiment; `runners/w166-review.py` performs independent cold comparison, using
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B`.
The archive `branch-artifacts/willow/w166-parent-geometry-evidence-2026-11-20.zip`
retains 239 indexed files, including all setup attempts; SHA256
`0fd86e7fd8b2d5bbb57f3f0250ba9100a53581b7c6263722b27f0b4976b121d0`.
Its per-file size/hash readback passes. It is an integrity archive, not a portable
or resumable run. No scientific inputs/results are committed or uploaded.

**Remaining gate.** This observes a returned geometry manager, not an optimizer
frame or a transported fmodel. Before supported refinement, bind both source and
candidate identities and fresh diffraction state before optimizer preparation,
preserve native chemistry/frame/site symmetry and refuse unsupported changes.
Symmetry seams, automatic link inference and general repaired-model acceptance
remain separate. No new installed code, runtime schema/default, migration or
installation behavior changes. Tracked validation is the focused roadmap test,
generated roadmap check, evidence checksum review and `git diff --check`; no
full suite or redundant install check for unchanged product code. S04/S05/S06
remain partial. Inspect W164's remaining B2/A13 distortion in its saved maps next;
do not repeat this transport comparison or tune another refinement loop by Rfree.


## W168 — Retain parent chemistry through child diffraction and recovery

**Question and native order.** W166 qualified returned-manager geometry only.
W168 asks whether the actual native entry can retain those source links while
using the displaced child for diffraction and a bounded fit. Source inspection
in **Phenix 2.2.1-6174** establishes that `Program.validate` constructs its
initial `DataManager.get_fmodel` before `preprocess.finalize_model -> model.process`.
`model.process(sort_atoms=False)` reloads `_model_input`; an earlier coordinate
setter alone is therefore insufficient. This supersedes the proposed pre-fmodel
ordering for this exact entry, without rewriting the W166 historical result.

A private process-local wrapper supplies the hash-bound intact parent only to
`process_pdb_files` during the single chemistry-interpretation call, then restores
the child by unique full atom identity before preprocessing continues. The
initial fmodel always represents the child and is unchanged during interpretation.
All wrappers restore on exit. No installed/native source or production API changes.
The frozen C407 execution owner is `f83562b0c1f61eb5b696d1ba75ebb4578b22c7ad`.

**Predeclared comparison.** Two dry-runs compare default-3 Å parent interpretation
against ordinary child interpretation under W163's private 4 Å control. They pass
**102 cold checks**: initial, pre-interpretation and returned `Fcalc`, `Fmodel`
and masks match exactly; all **7,554 original observation/sigma/Free tuples,
including 389 Free reflections**, survive. The 38 source O3′–P links include the
3.83587656 Å B2 O3′–B3 P and four flank angles. Six-family static definitions,
58 complete parallelity terms, 443 torsion/62 plane policies and fixed exclusions,
nonbonded types/functions/search remain equal. Raw geometry target/gradient
maximum errors are 7.28e-11 / 1.36e-9, within the predeclared componentwise bound.
Native OP3 array reordering is mapped explicitly; input order remains strict.

**One complete native execution.** Passing preflight admitted exactly one
five-cycle replay of W163's negative start: all 859 sites refine, fixed B/Q,
original noiseless synthetic data, fixed unit weights, seed1, one process,
100-iteration cap. The run completes and the process stops; **39 final cold checks
pass**. Exact initial/admitted preparation snapshots agree, and final source
geometry, complete live policies, 38 backbone links, all 126 ordered sugar signs,
atom identities/B/Q and raw/effective reflection tuples survive.

| Observation | W168 retained parent | Existing W163 private 4 Å control |
| --- | --- | --- |
| Selected 205-atom RMS to generator | 2.287991 → 0.271141 Å | 2.287991 → 0.279044 Å |
| Final Rwork / Rfree | .0467 / .0589 | .0475 / .0602 |
| Local covalent bond RMS, 232 terms | .007954 Å | .007816 Å |
| Local covalent angle RMS, 363 terms | 1.965877° | 1.952718° |
| Largest local angle deviation | 10.54° | 10.33° |

The two endpoints differ **.008788 Å RMS** over all 859 atoms (maximum .075 Å).
PDB records and output MTZ arrays are **not** identical. The tiny coordinate/R
improvement and tiny local geometry cost are observations, not evidence that
this path is superior or converged. Native aggregate summary .083 Å / 2.744°
is reported separately from the local covalent subset. Low synthetic R values
cannot accept an experimental repair; W164's other arm still has B2/A13 distortion.

Actual minimizer iterations are **100,100,100,100,49**, with 103,106,105,105,51
function evaluations. The initial final-reader regex missed native wording and
left `reported_iterations` empty; its original receipt is retained. A separate
`stopping-review.json` uses the existing W163 reader pattern and binds the exact
log. Generic statistics `cycle_series` also repeats initial/final summaries and
must not be treated as the macrocycle count. A preflight progress snapshot was
reconstructed from retained phase rows and verified against its already-frozen
SHA256 before sealing as `preflight-execution.json`; the historical review is
unchanged.

**Visible checkout and validation.** GitHub workspace anchor:
`ScienceCheckouts/Linden/2026-11-20_retained-backbone-recovery/review.html`.
Four small PDBs and two views show actual start/recovered/generator/control
coordinates and the local angle cost. The maintained renderer is unchanged;
34 offline JavaScript/control checks pass. A separate **ChimeraX 1.12 headless**
load validates four models, 859 atoms each, the 205-atom display mask and unchanged
crystal coordinates. Grey background, silhouettes, soft light and thin nucleic
rings are applied. The first sandbox startup stopped before script loading at a
toolshed-cache permission; the authorized retry passes, with both logs retained.
This is not rendered browser/GPU qualification. Viewer-inferred display bonds
are not the native chemical authority.

Main NASolve anchor: `branch-artifacts/willow/w168-parent-preparation/`.
Commands, run from that anchor's repository, use the existing local Python:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w168-prepare.py plan
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w168-prepare.py preflight
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w168-review.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w168-prepare.py refine
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w168-final-review.py
```

These commands describe the completed immutable experiment, not an instruction
to rerun it. The reader/source/receipt hashes and full native command arrays are
retained. Archive `branch-artifacts/willow/w168-parent-preparation-evidence-2026-11-20.zip`
has **112 indexed files / 9,100,709 bytes**, SHA256
`19c917b1f121b72f4c76bdf8c269071e122066615b800f21767d37a16764eb53`.
Every archived file's size/hash validates; prior-control evidence is linked to
its existing archive. This is an integrity bundle, not a portable/resumable
checkpoint. No crystallographic inputs or outputs are committed or uploaded.

**Next supported boundary, not implementation.** Reuse
`topostitch_recipe.rebind_pair_recipe` and its existing identity/frame/chemistry
negative controls. Require immutable current-parent/candidate bindings and retain
the strict initial ordered-identity scope: refuse renamed/reordered/missing/added
atoms, chemical changes, internal chain breaks, recuts and changed frame.
Keep supported canonical/alternate/site-symmetry scope explicit. Native array
reordering after preparation remains an exact identity-map problem. The generic
recipe owner deliberately permits ADP changes, whereas this W168 protocol is
fixed-B/Q; its new admission must enforce that stricter policy without silently
changing the generic owner. Existing registration is the owner for a later
broader logical mapping. Complete native source topology/policies, fresh child
diffraction, callback lifetime, output proof and ordinary checkpoint ancestry
still need shared API qualification. No production hook is enabled.

Changed tracked scope is existing guides, intent, handoff, roadmap/generated view
and changelog. The focused command
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_roadmap.py tests/test_topostitch_recipe.py -k 'roadmap or rebind'`
passes **32 tests** (eight roadmap, 24 existing rebind cases; 29 unrelated cases
deselected). These qualify the existing recipe predicates, not the private W168
wrapper as a production hook. `python scripts/audit_topostitch_roadmap.py --write`
and `--check`, JSON/evidence bindings and `git diff --check` pass.
No code/schema/default/migration or install behavior changes; no full
suite or redundant installation repeat. S04/S05/S06 remain **PARTIAL**. No further
native fit is queued. W167 cluster accommodation remains planned with Alder and
Cedar; Q15 owns shared regional helical measurements, and single-Hg evidence is
not widening qualification.


## W169 — Reuse the existing coordinate-only admission guard

**Question.** Before adding a fixed-B/Q admission helper for W168, inspect the
existing owners. W40's `topostitch_endpoint.audit_masked_endpoint` already protects
every non-XYZ byte, fixed coordinates, ordered identity, mask, movement bound and
exact PDB serialization. `topostitch_recipe.rebind_pair_recipe` separately binds
source/candidate bytes and frozen canonical pair intent; it deliberately permits
ADP and coordinate changes. Their responsibilities must stay distinct. This
corrects the proposed implementation queue: compose these owners, not another
fixed-B/Q checker.

**Cold real-input controls.** Exact W168 parent/negative-child bytes, the original
W163 205-atom mask and seven declared window pairs supply the control. The
original input files remain unchanged. Both the displaced child and no-op pass
the endpoint owner; the measured saved displacement is 4.78857150 Å. A fresh
seven-pair recipe is generated through the existing owner solely to exercise
binding; it is not substituted for W168's executed native restraint definitions.

| Deliberate child change | Coordinate-only endpoint audit | Generic recipe rebinder |
| --- | --- | --- |
| Selected or fixed atom B, +1 Å² | Refuses | Allows, as designed |
| Selected or fixed atom occupancy, 0.5 | Refuses | Refuses |
| Protected atom coordinate, +0.01 Å | Refuses | Allows, as designed |
| Chain label or atom order | Refuses | Refuses |
| Changed cell parameter | Refuses | Refuses |

All **eight altered children** are refused by the stricter owner. Hash-bound
recipe rebinding also refuses changed original parent bytes. The source audit
passes **27 checks**, and the already installed C407 package passes **29**, including
exact equality of scientific readback and frozen recipe. All five consumed
Willow owner modules are byte-identical between source and that installed pin.
No runtime hook, file/model mutation, native process or refinement is invoked.
No new production function or regression test is needed for already implemented
behavior; existing endpoint tests cover B/Q, tensors, masks and serialization,
and W168's 24 existing recipe-rebind cases remain valid.

**Scope of the evidence.** Points are read from the saved three-decimal PDB,
not the original unrounded proposal. The explicit 5 Å bound is a posthoc cold-
check input for this known 4.7886 Å displacement; it is not a new general motion
policy or proof of prospective W168 admission. Passing byte preservation does
not validate physical B/tensor quality, source chemical correctness or site
symmetry. The strict byte route can refuse harmless header/layout differences;
this is intentional, not general model equivalence. Native preparation's OP3
array reorder remains a later exact-identity mapping step.

**Validation and artifacts.** From the main NASolve workspace:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w169-admission.py source
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w169-admission.py installed
```

These completed commands write immutable local receipts, not a queued repeat.
Source/installed/recipe evidence is at the NASolve anchor
`branch-artifacts/willow/w169-parent-admission/`. Its archive
`branch-artifacts/willow/w169-parent-admission-evidence-2026-11-20.zip`
contains four indexed files, 19,389 bytes, SHA256
`58b24327b1775f10bdf16cd2303238529a40d46a7c8b94b6ad3028dbe6923f1b`.
Per-file hash/size validation passes; the already sealed W168/W163 archives bind
its inputs, avoiding another copy of the native runs. It is not a portable or
resumable checkpoint. Raw evidence remains local.

The eight focused roadmap tests, generated roadmap `--write`/`--check`, local
receipt hashes and `git diff --check` validate the documentation update. The
installed check reuses the frozen C407 package; it is not a new wheel installation.
No product code, API/schema/default, dependency, migration or installation change;
no full suite or redundant native run. S04/S05/S06 remain **PARTIAL**.

**Next gate.** The shared caller must authenticate the original full-precision
proposal, prospective mask/bound and source/current-parent/candidate lineage,
then use the existing byte auditor and recipe owner before native preparation.
Complete source topology/exclusions/policies, fresh child diffraction, scoped
callback lifetime, actual output proof and ordinary checkpoint ancestry remain
supported-integration work. Keep the W168 private hook gated. W164's B2/A13 saved-
map review remains a separate science step; no new fit or cluster-width claim
follows this input audit.


## W170 — Inspect saved maps at the remaining B2/A13 distortion

**Question and scope.** W164 left local positive-arm distortion despite synthetic
Rfree .0259. Does the saved density retain evidence of that discrepancy? This
posthoc review holds each completed map fixed and samples the generator, no-op,
positive and negative coordinates. It adds no deformation, coefficients, scale
fit, alignment, sharpening or refinement, and does not identify the forces or
optimizer history that caused the residual.

The exact W164 archive binds all three endpoint PDB/MTZ/parameter/geometry files,
original generator and synthetic observations. The maintained exact-label map
selector and Hazel's already-qualified A72 sphere sampler are reused with the
unchanged W152 native-geometry reader. Select unfilled `2FOFCWT_no_fill,
PH2FOFCWT_no_fill` and `FOFCWT,PHFOFCWT` only. Native declarations retain
isotropization, exclude no Free reflections and add no missing reflections or
sharpening. All **7,554 original F/SIGF/Free tuples and 389 Free rows** match.

**Readback.** Six maps and **44 backbone atoms** in A13/A14/B2/B3, each sampled at
four saved coordinate states, pass **108 checks**. A common 144×144×125 FFT grid
uses resolution factor .25. Each map's raw FFT σ/mean and own-σ samples are kept;
the displayed comparison uses one shared **saved reference ordinary-map σ**,
not the difference map's own σ. Periodic translation checks pass, and direct
Fourier sums at selected grid nodes agree with FFT values within **5.60e-14**.
The native saved-coefficient calculation completes in 15.62s in this one run;
this is not a performance claim.

| Positive-endpoint observation | B2 O3′ | A13 C5′ |
| --- | --- | --- |
| Position error versus generator | 1.411713 Å | 1.184607 Å |
| Native angle model / target | 76.68° / 108.00° | 91.04° / 114.10° |
| Absolute native angle deviation | 31.32° | 23.06° |
| Ordinary map at generator / recovered point, common σ | 4.385273 / 4.166316 | 3.329110 / 3.812315 |
| Difference map at generator / recovered point, common σ | +.082704 / −.224824 | +.190477 / −.059613 |
| Difference map at generator / recovered point, own σ | +3.18954 / −8.67044 | +7.34583 / −2.29900 |

The respective angles are B2 O3′–B3 P–B3 OP2 and A13 C5′–C4′–C3′. Native `.geo`
values describe the final geometry before PDB coordinate rounding; coordinate
errors and map markers use the saved rounded PDBs. The positive difference map
has the expected signed discrepancy at both known residual sites. Yet the
ordinary-map point sample is **higher at the misplaced C5′** than at its
known generating position. An ordinary-map uphill direction alone therefore
cannot settle placement in this example; no causal optimizer conclusion follows.

An atom-centred red-only 3.5σ display would omit the C5′ negative sample, while
its nearby generating position has positive signal. This does not calibrate an
automatic detector or change the viewer/default planned trigger. The negative
control is only .06225 Å from the generating B2 O3′ but still samples −2.93 of
its own difference-map σ. The no-op also retains a 5.29° B2 junction-angle
deviation; the source is not assumed ideally restrained. Keep signed spatial
context and geometry alongside ordinary maps/global R, with near-zero/own-map
normalization and phase/model bias explicit. These are noiseless synthetic,
model-assisted maps containing Free reflections, not independent experimental
validation or a universal significance policy.

**Visible packet.** GitHub workspace anchor:
`ScienceCheckouts/Linden/2026-11-20_remaining-backbone-density/review.html`.
It contains a four-panel PNG/SVG figure, exact matched-control table and the
standard-Python checksum/opening script. The planes contain each known positive
residual direction and a declared nearby anchor; this is a 2D diagnostic slice,
not a whole-volume classifier. PNG layout/markers/legends were viewed directly;
HTML/GPU rendering is not claimed. Existing coordinate checkouts are linked,
without duplicating PDB/MTZ files. `python3 open_report.py --check` passes.

**Execution and preserved setup limits.** Phenix **2.2.1-6174** performs a complete
read-only saved-coefficient FFT/interpolation; no `phenix.refine` or refinement
dry-run is invoked. Three initial readers stop before FFT at the saved Free-flag
declaration: first the obsolete input scope, then integer/scalar assumptions.
A separate raw-PHIL inspection shows that the untyped `data_manager.fmodel.
xray_data.r_free_flags.test_flag_value` extracts as the one-word list `['0']`.
The corrected reader uses that exact representation; the independent numerical
MTZ membership checks, map policy and numerical bounds are unchanged. All failed
workers/logs/receipts and the successful run remain preserved. Matplotlib writes
the static plot separately; its font-cache warnings do not prevent output.

Completed commands, from main NASolve, use
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w170-saved-maps.py`
(the controller records the exact native Python command/environment) and the
bound `w170-figure.py` under the same Phenix Python. These are historical commands,
not a request to rerun the immutable folders. Native/direct-FFT checks, cold
normalization/readback, process-stop checks, figure hashes and the Python opener
pass. The main artifact anchor is
`branch-artifacts/willow/w170-residual-maps-attempt04/`.
Archive `branch-artifacts/willow/w170-residual-map-evidence-2026-11-20.zip`
contains **29 indexed files / 1,069,446 bytes**, SHA256
`9f70b4d33e5f8640a48a1ff398da1f7f4d42b94ccb25a29cce46535ab4b30037`.
Every member hash/size validates; original scientific inputs remain in the
already-bound W163/W164 archive. This is integrity evidence, not a portable or
resumable checkpoint, and no generated science is committed or uploaded.

Documentation validation from the Willow checkout:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_roadmap.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_topostitch_roadmap.py --write
PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_topostitch_roadmap.py --check
git diff --check
```

Eight focused tests pass; roadmap structure/references/synchronization pass.
Both JSON documents parse, and all seven declared receipt hashes/sizes match
through their anchors. Product code, runtime schemas/defaults, installation,
dependencies and generic rebinding remain unchanged, with no migration required.
No full suite or new installation repeat. S04/S05/S06/S07 remain **PARTIAL**. The descriptive
B2/A13 map-review task is closed in this exact scope; the distorted model is not
accepted and its causal/remedial question remains open. Continue supported
request/chemistry/execution integration, with noisy density calibration and
cluster opening as separate later gates; do not repeat this sampling or launch
an identical fit as a substitute for a distinct hypothesis.


**Same-update request-owner review.** Before extending W168 admission, source
review identifies the existing W88 `load_bend_motion` and captured-job endpoint/
3N-start owners. The former pins the registered terminal preview and rebuilds
unrounded points under the original bound; its source digest is authenticated by
that loader, unlike a bare caller-constructed `TaperedMotion`. Existing controls
cover changed input/receipt, mutation during reading, renamed registration,
relocation after original removal, and a sub-PDB-precision bound violation.
Captured-job unit controls cover mask/count/bounds and frozen forwarding through
a mocked runner. Current parent/request binding into the retained-chemistry
ordinary lifecycle remains unimplemented; this is not a native integration test.
The W163 interior taper is outside the terminal-preview request scope, and
retrospective reconstruction cannot create prospective authority for an old run.
ANISOU-rotating preview output also requires an explicit compatible admission
policy; the strict coordinate-only audit cannot silently allow those byte changes.

At source commit `94dc8a7a6d5d24dad557bcac9e8fff3a5619cbeb`:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_preview.py tests/test_topostitch_captured_job.py -k 'saved_motion or explicit_trial_start or explicit_start'
```

**24 passed, 56 deselected**. No new tests, product code, runtime schema,
installation, native calculation, refinement or science files. This clarifies
the same W170 queue without claiming another scientific milestone or repeating
already-qualified arithmetic. Existing full/install evidence remains historical.


## W171 — Bind a saved motion to the current parent snapshot

**Before/after.** The saved-motion loader authenticated a pinned preview and
reconstructed its source-bound unrounded motion; the caller compared any current
parent separately. `load_bend_motion(..., parent_model_bytes=...)` now optionally
requires immutable bytes that exactly match the pinned preview source before
returning that same motion and six parameters. Any coordinate, B/Q, identity or
metadata drift is refused. The old call/return and existing artifacts remain
compatible; no schema migration or CLI/default behavior changes.

This is a small composition point in the existing owner, not a new request
format or lifecycle. The caller still authenticates its selected checkpoint,
passes the actual parent snapshot and checks inputs again when dispatching.
The strict endpoint auditor still owns full/rounded coordinate serialization,
fixed records and tensor policy. New schema-1/schema-2 composition tests exercise
that unchanged owner, while the sub-rounding bound case also runs with the new
parent option. No retained-chemistry native hook, ordinary checkpoint activation,
modified-metal movement, backbone closure or scientific acceptance follows.

**Changed source:** `src/nasolve/topostitch_preview.py` adds the optional argument
and exact-byte check; `tests/test_topostitch_preview.py` adds distinct composition,
parent-drift/type cases and extends the existing unrounded-bound case. Code pin:
`ab84322f6697fc29a25c170b1dbdbab11282c6c9`. The source parent digest alone is not a
substitute for the pinned request or a trustworthy checkpoint caller.

Validation from the Willow checkout:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_preview.py -k 'current_parent or parent_requires or unrounded'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_preview.py tests/test_topostitch_endpoint.py tests/test_topostitch_captured_job.py
```

Before implementation, **12 fail / one existing unbound case passes** (47
unselected). Afterward, **118 focused tests pass**. The exact commit is built
and installed with `pip wheel --no-deps --no-build-isolation` and `pip install
--no-deps --no-compile --target`; the copied build source is removed and target
relocated. The same **118 tests**, actual installed import, `pip check`, all six
entry-point help commands and **93 package-file hashes** pass there. Full exact
commands/environment and results are in `install-result.json`, via the NASolve
anchor `branch-artifacts/willow/w171-parent-bound-motion/`. Controller invocation:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w171-install-parent-binding.py
```

This historical command is not a request to rerun immutable output folders.
No global/shared numerical mechanic changed, so no full-suite repeat; focused
checks cover the loader and adjacent endpoint/captured-job contracts. No Phenix
or Coot calculation, refinement or new structural result was produced. Existing
W168/W170 coordinate/map checkouts remain the scientific illustrations.

Archive `branch-artifacts/willow/w171-parent-binding-evidence-2026-11-20.zip`
contains **31 indexed files / 506,537 bytes**, SHA256
`147b88e8ab464d59d3447f6bbc12e87ddcbc5cbba4c5cf43a50b92072c270d1d`.
All archive members verify. After preserving the wheel, exact code patch,
commands/logs and source hashes, the owned installation scratch is retired:
**209 files / 3,515,209 bytes**. The archive is integrity evidence, not a resumable
crystallographic checkpoint. Generated diagnostics stay local; no raw science
is committed. Human/machine docs and queue are updated; S04–S07 remain PARTIAL.

The documentation gate also passes eight existing roadmap tests with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_roadmap.py`,
roadmap `--write`/`--check`, JSON/declared receipt hashes, Python 3.10 AST syntax
for the changed source/test files, and `git diff --check`. The small human note
uses the existing GitHub workspace science folder:
`ScienceCheckouts/Linden/2026-11-20_remaining-backbone-density/W171-parent-binding.txt`.

Hazel confirmed no overlap: Alder keeps the read-only connected-region inventory
and a private per-residue axis proposal using existing `TaperedMotion` arithmetic.
Its modified-metal scope does not enter this canonical endpoint admission route.
The next bounded step is the supported caller/lifecycle composition, with real
checkpoint identity and dispatch-time freshness; repeat neither the arithmetic
qualification nor the already-completed matching-data fits.

## W172 — Require declared topology before parent-coordinate transfer

**Question.** Exact replay of a native manager can preserve an unwanted bond.
The source declaration must therefore be checked independently before motion.
Cedar's maintained C109 capture reader and C128 topology checker already own
this comparison; no new bond classifier or origin-wide exemption was added.

Cold authenticated controls reproduce C345's two intended O3′–P links (MATCH)
and C346's 38 intended links plus the unwanted A:12 DA N6–B:4 DY C5T bond
(REVIEW). The controls use their bundle-declared endpoints and model/receipt
checksums. They do not authorize DY movement or rerun either native capture.

The existing W168 private Phenix wrapper now checks the actual manager after
parent interpretation, before child-coordinate restoration or optimizer entry.
Its original SS-enabled frame remains REVIEW: all 38 backbone links exist, but
the 51 explicit distances have no complete C128 soft-policy authorization. The
original model, parameters and historical result are unchanged.

A distinct control uses C21 to compile the frozen W152 `pairs.txt` (20 pairs)
and original 38 stack declarations. All 155 original non-planarity explicit
requests match; the original 20 pair-planarity requests are carried unchanged
as a separate retained PHIL block. The 38 native stacking terms become explicit
NAR requests, so this is a **new objective**, not W168 energy continuation.
The compiler first refused a literal declaration with SS disabled; its required
source declaration is enabled and its compiled output disables competing SS.
Both inputs remain preserved.

A fresh registered terminal preview supplies a prospective 0.25° rotation with
a 0.2 Å hard bound. W171 loads it against the exact parent snapshot and the
existing endpoint auditor verifies full-precision/serialized coordinates and
every protected byte. Sixty atoms move; maximum serialized displacement is
0.048166 Å. This tests admission, not a new bending-efficacy claim.

The completed **Phenix 2.2.1-6174 dry-run** admits the fresh parent manager and
retains, after child transfer, 38 declared backbone links, 51 individually
verified soft distances, **213 exact custom requests**, all bonded parameter
inventories, all 859 atom identities and P/OP1/OP2/OP3 inventory. Child diffraction
is unchanged during parent-only interpretation; observations/Free are retained.
No optimizer, macrocycle, refinement, Coot job or scientific adoption ran.

Two setup stops precede the qualified policy stop/control. First, importing the
full host topology module in Phenix encountered its transitive workbook
dependency. The diagnostic stages unchanged pure C109/C128 functions and checks
their complete-owner parity on both saved controls. Second, `model.process`
clears its processed-PDB handle before returning. Retaining the actual
interpreter return object fixes its lifetime. Each failed attempt retains its
evidence and restores all five scoped hooks. No installed/native source is edited.

**Validation:** `w172-review.py` passes **35 cold checks**, including host/native
checker parity and Cedar's `custom_restraint_check` for all 213 terms. Four native
preflight launches comprise two setup stops, one intended policy stop and one
completed dry-run. The compiler and registered-preview checks run without native
optimization. Human/machine documentation uses existing roadmap tests and audit;
no full suite or install repetition for this documentation/private-diagnostic slice.

Exact local evidence is under the NASolve anchor
`branch-artifacts/willow/w172-parent-topology/`; `review.json`, the two cold
reviews, `attempt03/live-execution.json`, `explicit-control/live-execution.json`,
the explicit-policy comparison and prospective-motion admission are pinned in
the machine roadmap. Controllers are in `branch-artifacts/willow/runners/`:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w172-topology-cold.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w172-explicit-policy.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w172-motion.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w172-prepare.py --explicit
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w172-review.py
```

These record completed invocations, not instructions to overwrite their output.
Attempt controllers/helper snapshots are retained inside their exact job roots.
The positive cold control was a separate recorded host invocation. No generated
science is committed. Portable checkpoint/resumption is not claimed.

**Remaining:** private canonical same-ASU preparation only; no installed hook,
ordinary selected-checkpoint ancestry, symmetry covalent seam, modified/metal
admission or physical recovery qualification. The live negative is the legacy
soft-policy refusal; DY remains a separate saved negative. A matched independent
child-diffraction control remains distinct from the observed unchanged fmodel.
Next bind the actual selected checkpoint/request and dispatch freshness before
promoting this native entry. Do not repeat the same tiny move or old recovery fits.
S04/S05/S06 stay PARTIAL. Alder owns typed coordination declarations separately.


## W173 — Bind motion to the selected checkpoint inputs

Before this change, W171 bound a caller-supplied parent snapshot to a preview but
did not resolve the selected checkpoint. `nasolve.topostitch_checkpoint` now
composes the existing checkpoint, preview and endpoint owners. It requires a
saved schema-2 registry, one exact usable selected ID, and complete checksummed
anchored model/observations/ordered-restraint/optional-phase references. Both
current selection and explicit ID/bookmark resolution preserve the current pointer.

The read-only result binds registry/report bytes, selected record, inherited
inputs and preview receipt. Repeated reads surround preview replay; the returned
context digest can be required on a fresh dispatch-time call. Even a different
checkpoint with identical coordinates is refused. The strict endpoint owner
retains full-precision and rounded displacement, fixed-atom and non-XYZ checks.
This detects input drift; it does not lock mutable files or authorize execution.

Code commit: `16a5e13478a9fb4be9d559390bb65f3d084d3793`. Changed runtime file:
`src/nasolve/topostitch_checkpoint.py`; regression module:
`tests/test_topostitch_checkpoint.py`. New returned binding/context objects are
schema 1; no existing stored schema, CLI, default or dependency changes. Existing
APIs remain compatible. The new strict API refuses legacy/incomplete references
rather than migrating them or weakening their provenance.

Validation used Python 3.12.14:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_topostitch_checkpoint.py tests/test_topostitch_preview.py \
  tests/test_topostitch_endpoint.py tests/test_checkpoints.py tests/test_run_context.py
```

The first 22 added cases failed before implementation; the final 25-case addition
includes later input-race and declared-phase controls. **138 tests plus 6 subtests
pass**. The same selection passes against a relocated wheel installation after
removing the copied build source and original install path (3.52 s test time).
A dataset/preview relocation regression removes the original paths and reproduces
the context. Installed import location, six entry-point helps, `pip check`, all
94 package-file hashes and Python 3.10 syntax checks pass. Wheel SHA-256:
`a9d86b3d1b19be93233b664f2f84a7bd87a5db1b97b946993f4a7480c03a0922`.
The three existing ligand provenance JSON files remain outside package data;
this change does not alter that packaging policy. No full suite or native
Phenix/Coot execution was repeated for this isolated additive input adapter.

Exact commands, logs, source hashes and installation record are under the local
NASolve artifact anchor `branch-artifacts/willow/w173-checkpoint-motion/`.
Generated checks/fixtures remain outside Git; no scientific run is published.
Tests and installation validate this API, not portability of every historical run.

Next: pass this binding through the maintained executor's frozen input ownership
and separately authenticate complete intended chemistry before W172's live parent
transfer. No atomic lock, retained-manager hook, Free-R semantic validation,
modified/metal admission or scientific acceptance follows. Hazel confirms the FT
parent lacks whole-model link/C128 authority; the native inventory cannot fill
that gap. S04/S05/S06 remain partial. Do not repeat a tiny move or old fit without
a new integration question.


## W174 — Join checked motion to the frozen child request

W173 authenticated the selected parent and preview without joining the executor's
request. W174 adds `load_execution_bend_motion` in the same module. It reuses
Cedar's request and namespace-adaptation readers, checks parent and child IDs
separately, and requires an explicit `parent` or `candidate` model role. The latter
must match the preview's exact serialized bytes. Ordered inherited/adapted/extra
restraints, phases and round-generated parameters are separate recorded roles.
Repeated reads and an optional execution-context pin detect changed inputs.

The adapter grants no chemistry, locking, command/force semantics or launch
permission. It adds no executor, native hook, stored request/checkpoint schema,
CLI/default or dependency. Existing APIs remain unchanged. Standalone Willow
lacks the shared Cedar readers and refuses unless they are explicitly supplied by
a trusted integration caller; no module is copied or branch silently merged.
Returned `topostitch-execution-input-binding` records are schema 1 and retain
`chemical_admission=False` and `runtime_authority=False`.

**Validation, code `02411806ad7d444672803a27e6699f68b11d888d`:** the first
18 new cases fail before implementation; 21 final cases cover input roles/order,
selection/request/preview drift, explicit candidate identity, optional phases,
extra restraints, namespace adaptation and old-path-gone relocation. Python
3.12.14 source and source-free relocated wheel runs each pass **159 tests plus
6 subtests**. Use the W173 focused command with
`tests/test_topostitch_execution.py` additionally; all exact commands are in the
local source/install records. Python 3.10 syntax, 94 unchanged installed files,
six entry-point helps and `pip check` pass. Wheel SHA-256:
`5d887e91b0bbfb1126c3d6a1297753eee03d1900de7a932aefe7913d5f5aabf8`.

One complete Willow run with the same `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`
environment and `python -B -m pytest -q -p no:cacheprovider` finished in 114.38 s:
**2,145 tests plus 234 subtests passed; five process tests failed because the
sandbox denied `/bin/ps` or process-group signals.** The whole
`tests/test_campaign_process.py` module then passed outside that restriction:
**22 tests plus 19 subtests, 2.79 s**. No process code changed; no test worker
remained. This is a split validation result, not a clean uninterrupted full-suite
pass. No further full suite is queued for tonight.

**Cedar compatibility:** pinned source `a1ce98818fb3ece14a2cbdb6ecbf24d30a7d9393`
reads two genuine C412 requests (v3 and v7), each with 11 inputs. The extracted
membership join preserves the exact declared parent, validated namespace copy,
terminal-protection declaration and separate generated parameters. Changed
parent/data/order/request-hash controls refuse. The 223 cold/source checks include
16 unchanged original files and isolated-owner source hashes. These real modified
parents have no registered canonical preview; this is deliberately request-only
readback, not a fabricated successful W173 admission. Request digests are
`3f778e4e3e783fa06b288e19abba437a71d6876ad2627c62df75187110d71b0d`
and `9ea5e242837ac781ac4c4cef88fd883c419751e98890a14bc9c39fccc70e3e14`.

Separately, Cedar's actual freezer/adaptation/request readers produce labelled
synthetic canonical parent- and candidate-model controls. The complete W174 API
passes 17 checks, including selection/input refusal and relocation after removing
the original dataset/preview paths. The same 17 checks pass using the relocated
installed Willow package. No native Phenix/Coot process or fit runs in W174.

Local evidence: NASolve anchor `branch-artifacts/willow/w174-execution-binding/`;
private runners `w174-request-compat.py`, `w174-supported-request-fixture.py`,
`w174-installed-supported-request.py` and `w174-install-execution.py` record exact
invocations/source pins. Tests, wheels, reports and existing scientific inputs
remain outside Git. Runtime change: `src/nasolve/topostitch_checkpoint.py`; new
regressions: `tests/test_topostitch_execution.py`; human/machine docs updated.
W173's disposable install tree was retired after its wheel/log archive verified;
no scientific input or run was removed.

Next gate: join independently complete W172-style chemical authority for an actual
parent/candidate to these exact child inputs, checking the moving neighborhood
and untouched remainder together. Native retention and ordinary ancestry remain
open. An observed link inventory cannot manufacture expected chemistry; FT lacks
both whole-model authority and an ordinary selected checkpoint. No repeated
private tiny-motion or refinement control is justified without that new question.


## W175 — Bind the private candidate and check its untouched remainder

The new question is whether the candidate/request and the entire captured
chemical context agree, including the region outside the moving window. Reuse
W172's original genuine v3 request and completed **Phenix 2.2.1-6174 dry-run**;
no new native invocation, coordinate proposal, fit or accepted repair occurs.
Original request SHA-256:
`d787499d4815195a4ce6248d7fa840022950d75c316b1a6f7b216e64e1e8bd12`.

W171 replays the exact prospective preview; the strict endpoint auditor reproduces
W172's original audit. Source/candidate bytes, independently declared 38 covalent
links, compiled C21 policy/PHIL, 51 soft distances and all 213 supplied requests
remain bound. Cedar's topology/supplied-term owners reproduce the saved results.
These are explicitly private collected views, not complete maintained native
capture receipts. `link_status=MATCH` does not change C128's
`chemical_qualification=NOT_ESTABLISHED`.

The native-to-source mapping is a complete 859-atom bijection. **60 atoms** move
in A:1/A:2/C:14; **799 remain fixed**. Native fixed-coordinate differences are
at most **1.1235e−14 Å**; serialized fixed records and all non-XYZ bytes are exact.
All captured proxy definitions are unchanged in the following disjoint partitions:

| Captured family | Moving only | Crossing boundary | Fixed remainder |
| --- | ---: | ---: | ---: |
| Simple distance restraints | 68 | 2 | 941 |
| Angles | 100 | 8 | 1,450 |
| Dihedrals | 27 | 6 | 410 |
| Constant dihedrals | 29 | 0 | 316 |
| Chiralities | 11 | 0 | 156 |
| Planarities | 4 | 0 | 58 |
| Parallelities | 2 | 2 | 54 |

No symmetry covalent proxies are present. Distances include supplied soft terms;
the table is a native restraint inventory, not a new list of chemical bonds.
Cedar's `cif_terminal_qualification._proxy_subset` independently checks named
endpoints, every captured parameter and multiplicity for complete/fixed subsets.
Detached moving/fixed target changes are detected; removing a declared link
returns REVIEW. No historical native model or expectation is edited.

A separate explicitly diagnostic request tests only the standard final
`autorefine.params` role, replacing W172's historical `source.params` filename.
All four consumed input hashes remain identical. It has no AutoMR report or
checkpoint registry, creates no ordinary ancestry, and is never launched.
W174's read-only membership join is used; its full checkpoint-preview API is
not claimed to admit this private parent. C412 remains a separate genuine
ordinary request control with modified chemistry.

Validation: **64 cold binding checks plus 28 maintained named-proxy checks**
pass using Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<Willow>/src`,
with `python -B <NASolve>/branch-artifacts/willow/runners/w175-diagnostic-chemistry.py`
and `w175-owner-review.py`. Cedar owners are pinned to
`a1ce98818fb3ece14a2cbdb6ecbf24d30a7d9393`; Willow code remains W174
`02411806ad7d444672803a27e6699f68b11d888d`. Local evidence and source hashes are
under `branch-artifacts/willow/w175-diagnostic-chemistry/`. No new runtime/test
code, installed package, CLI/default or stored schema changes; W174 validation
remains applicable. Science and diagnostic request files stay outside Git.

The [first-capture contract](topostitch.md#preserve-chemistry-before-a-bend-w175-integration-contract)
identifies ten existing producer/consumer interfaces. Prepared-model context,
literal NAR provenance, complete dictionary requests and native capture already
preserve relevant pieces. Their authenticated ordinary parent/request/native
lifetime join is missing for this canonical control. Source-mode and native-index
compiler artifacts are different policies, not interchangeable labels. Do not
weaken the fixed-coordinate dictionary comparator for moved coordinates or derive
source intent from the bent child's observed bonds. S04/S05/S06 remain partial.


## W176 — Capture the complete fixed parent through the maintained native owner

One **Phenix 2.2.1-6174 fixed-coordinate interpretation** uses Cedar
`cif_native_validation.inspect_native_bundle`, pinned at
`a1ce98818fb3ece14a2cbdb6ecbf24d30a7d9393`. It is a complete invocation of that
read-only interpreter, not a refinement or a new coordinate proposal. The parent
is W172's exact canonical source (`f33754cc…`), with its unchanged combined C21
edits and twenty retained pair planes. The original sort-atoms/CDL settings are
copied explicitly. Full monomer mapping additionally requires
`use_ncs_to_build_restraints=False`; this declared capture policy is distinct
from replaying the historical optimizer's state.

A first setup stopped before launching: the native output directory lay beneath
an input's directory. The preserved attempt contains only its plan/settings. The
corrected sibling input/output layout completed **one native invocation in
1.554410 s**, with zero optimization cycles. All historical inputs remain exact.
The installation setup records `PHENIX_VERSION=2.2.1-6174`; API and executable
hashes are also frozen. No Coot invocation or suite rerun occurs.

The maintained capture reader and complete-monomer owner verify **859 atoms and
42 residue mappings**, including effective component definitions and terminal
modifications for every residue. All explicit PHIL definitions are consumed;
there are no unsupported inventory fields. C128 finds all **38 independently
declared backbone links** and exactly **51 declared soft distances**; all
**213 supplied requests** agree with the prior private parent. Its outcome is
still `REVIEW`, `link_status=MATCH`, `chemical_qualification=NOT_ESTABLISHED`.

Cedar's named-proxy comparator finds identical definitions/multiplicity in all
eight captured families: 1,011 simple distances, zero ASU bonds, 1,558 angles,
443 dihedrals, 345 constant dihedrals, 167 chiralities, 62 planarities and
58 parallelities. These are restraint counts, including soft terms. They are
not a claim that every distance restraint is a chemical bond.

**17 cold checks pass**, including refusal of a missing monomer mapping and an
altered explicit soft target, and a retained REVIEW for an omitted declared
link. These detached controls do not alter the original capture. Exact commands,
from the NASolve workspace:

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w176-parent-capture.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w176-review-capture.py
```

The local-only evidence is anchored at
`NASolve:branch-artifacts/willow/w176-parent-capture/`; `attempt02/result.json`
identifies the capture relative to the owned root in `attempt02/ownership.json`.
The original prelaunch controller and plan remain recorded. These are historical
local invocation paths, not portable package entry points. Generated coordinates,
receipts and scientific evidence are deliberately excluded from Git; no portable
run claim is made.

**What this adds:** a maintained, integrity-checked reading of complete effective
monomers, native policy, consumed PHIL and named geometry for the fixed parent.
It does **not** add independent full chemical-intent approval, nonbonded exclusion/
force evidence, actual optimizer-lifetime retention, ordinary checkpoint ancestry,
modified/metal motion or accepted repair. An observed effective monomer definition
is not an independently declared source dictionary.

**Next producer boundary:** Rowan identified existing
`cif_postmr_publication.validate_published_preparation` and
`cif_complete_request.read_dictionary_request_result`. Their authenticated
publication already points to exact prepared-model/restraint contexts and compiler
inputs when present. Read those through their owners for the exact parent before
adding a producer or schema. Legacy missing fields remain unavailable. Canonical
motion and modified-input evidence reporting remain distinct. Cedar head
`d3267292e7f124fcbfe379220c401e9178d29202` leaves the capture, monomer, topology,
publication and execution reader modules unchanged from the pinned owner; its
PostMR request adds the explicitly declared furanose-reaction option. No shared
Cedar file is edited or combined runtime qualified here.

The same doc audit reconfirms Hazel's W167 nanocluster contract: preserving
chemical identity and targets permits coupled sugar/backbone coordinate movement.
It does not freeze conformation or establish an implemented widening move.


## W177 — Read existing ordinary preparation authority without admitting motion

`inspect_checkpoint_preparation` reuses Cedar's
`checkpoints._read_registry_with_preparations`, including its authenticated
checked-publication and complete-result values. It consumes the expensive history
read once rather than replaying it for each field. No chemistry producer, model
edit, native invocation, CLI or saved checkpoint schema is added.

The caller pins selected checkpoint identity and model SHA-256. The adapter
brackets the owner read with saved metadata/input checks, binds the returned
preparation/result to that exact selection, and exposes field availability/hashes.
A previous context pin detects changed inputs on a later call; it does not lock
or authorize dispatch. Missing model/restraint/compiler fields stay unavailable.
Native-capture coverage is not assessed. The default owner is absent on standalone
Willow, requiring an explicitly trusted reader dependency until branch integration.

Scope is published `postmr` or explicit `prepare-NNN`; refined descendants refuse
pending their lineage join. Legacy roots without checked publication return
`NO_CHECKED_PREPARATION`. W173's canonical/schema-2 motion admission is unchanged.
An available source model context may describe pre-ReadySet coordinates rather
than the selected prepared model: both hashes and their inequality are retained.

Validation at code `a725c575f2f8f6979108526d79e474ce9d63deec`:

- **20 new cases**, with the first **18 failing before implementation**: wrong
  parent/model, explicit preparation, missing authority, owner-side metadata/input
  races, mismatched returned result/compiler, unavailable owner, context changes,
  and relocation with the old path gone. Legacy missing authority is explicit.
- **179 focused tests + 6 subtests** pass with
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, covering preparation, execution,
  checkpoint, preview, endpoint and run-context boundaries. Python 3.10 syntax passes.
- The same **179 + 6** pass from a clean wheel after removing the build checkout
  and old install path. **95 installed module/resource files** match source and
  remain unchanged; dependency checks and all six entry-point helps pass.
  Wheel SHA-256: `74d0be1c4ad78e90c62df98ff28b07fbd6b3bedc8a12cb902ef070efa4bb7c23`.
- One real C412 supported-owner read completes in **99.50 s**, with **14 original
  input/metadata files unchanged**. It supplies prepared-model/restraint contexts
  and source-literal inputs with `PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES`.
  Native-index explicit policy is unavailable. Source model `f2c07a22…` and
  selected prepared model `636223e4…` are explicitly different. This modified
  parent is evidence-only, not canonical/modified-motion admission. C461 was not
  read while Rowan's optional retention work remained active.

The real owner is pinned to Cedar `a1ce98818…`; default integrated-runtime testing
is separate from explicitly injected reader compatibility. No full-suite rerun
or native refinement was needed for this bounded read-only adapter.
Local-only logs, exact commands and hashes are anchored at
`NASolve:branch-artifacts/willow/w177-preparation-reader/`. Runners
`w177-c412-preparation.py` and `w177-install-preparation.py` preserve the exact
commands; scientific files are excluded from Git. No portable scientific-run
claim follows from the relocated software check.

Next audit the existing source-policy/native-membership and descendant-lineage
owners before broadening motion. An availability report cannot manufacture the
missing chemical authority or turn a source-index policy into C128 native indices.


## W178 — Bind the existing source producer without inventing ordinary authority

The bounded question is whether existing producers supply complete declared
canonical topology and compiled-restraint provenance that can be carried into an
ordinary request. W172's private 38-link declaration and separate native-index C21
recipe are real evidence, but no authenticated ordinary canonical PostMR context
is available for that private parent. No PostMR report, registry, missing terminal
intent or ordinary history is fabricated to make a new request pass.

The existing source path **does** work. Cedar `a1ce98818…` owners
`freeze_acquisition_sources`, `prepare_postmr_literal_inputs` and
`cif_complete_request._compiler_input` freeze four canonical component sources,
20 independently declared pairs, 38 stacks and twenty retained pair planes. No
pair guesser reruns. The returned role is `literal_na_inputs`, policy
`cif-source-literal-na-inputs-v1`, with explicit
`PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES` basis. Compiled membership policy
remains `narestraints-source-bound-literal-membership-v1`.

The source-bound evidence joins these exact roles:

| Role | SHA-256 |
| --- | --- |
| Canonical parent | `f33754cc170ab8167e8085cb848f4ef0b6bd0f545c81db6163a650a41f503e71` |
| Independently declared links | `501d1f29c45a9fe12aed0def66089790a4e8bfc653d4a7545f7eb0c936605f27` |
| Literal compiler manifest | `97a2b6f38a89fa5c904237765ee41512eb74d4de473bc13f7181685301f44d7b` |
| Local role binding | `a9719094e8124aec8defc6fed5d6ac51c0aba7075d8d7a7b6a1251805a5b1cb9` |

**17 checks pass**: source component coverage, declared pair/stack/link counts,
index/approval labels, exact compiled PHIL bytes, different-parent refusal,
relocation with the old evidence directory gone, changed topology/original PHIL/
source-CIF refusal, restored replay and untouched original scientific inputs.
The generated C21 PHIL is byte-identical to W172's compiled policy; retained planes
remain separate ordered inputs. This local role binding is diagnostic evidence,
not a new executable request or runtime schema.

**Five further checks** reuse W176's maintained fixed-parent capture and existing
C128/PHIL owners. All **213 supplied requests** agree exactly by full request
content/multiplicity, including all **20 retained planes**. C128 correctly refuses
the source policy as native-index authority. This verifies observed membership
without relabelling policy identity, supplying chemical approval or launching a
new native process.

The producer gap is precise: `prepare_literal_na_inputs` already owns native-index
literal provenance, but requires a maintained capture of **original literal
intent**. W176 contains already-compiled edits, so there are no literal
relationships left to compile; compiling original relationships against the
populated edits would overlap them. W172 explicitly constructed a separate private
recipe using native identities with an empty old-edit list. It is not a maintained
original-capture artifact and cannot be silently promoted into one.

A fresh fixed capture of original pair/stack declarations plus retained edits
could qualify that existing producer. The genuinely ordinary canonical parent and
execution-role join would still be required afterward. A source-index manifest
or matching native inventory cannot substitute for either. W173 and all modified-
motion admission criteria are unchanged; C461 was not reread because C412 already
answered availability. No product code, installation behavior, native invocation,
refinement or branch-wide test suite changes in W178.

Exact local commands, from the NASolve workspace:

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w178-source-intake.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w178-native-membership-review.py
```

Evidence is anchored at `NASolve:branch-artifacts/willow/w178-source-intake/`.
Its owned root contains the relocated producer artifact and checksummed local
role binding. Scientific inputs and resulting captures stay outside Git. The
producer artifact's relocated readback is proven; no complete ordinary portable
scientific run is claimed.

The same coordination update records the investigator-confirmed FT C/D crossover:
the A21 condition holds in the exact current, PostMR and selected MR models. Alder's
versioned v2 declaration supersedes the earlier tentative status; residue-level
image realization and native seam angles/exclusions remain separate. Older Cedar
free-end scaffold declarations do not override this newer FT-specific intent.


## W179 — Capture original literal intent and isolate the control-role gap

One new **Phenix 2.2.1-6174 maintained fixed-coordinate interpretation** captures
original literal intent on the exact W172/W176 canonical parent. This is the
missing pre-compilation input, not another fit or a repeat of already-compiled
W176 input. Cedar `a1ce98818…` owns capture, atom/monomer readback, compilation,
policy comparison and topology review. No shared Cedar source changes.

The three ordered PHIL roles remain explicit: independently pinned original
20-pair/38-stack declarations, twenty retained pair planes, and source sort/CDL
settings plus `use_ncs_to_build_restraints=False` for full monomer capture. The
native run completes in **1.709551 s**, with **859 atoms / 42 full monomer mappings**.
Its original secondary-structure policy is enabled; only the twenty retained
planes are explicit custom edits before compilation. Original science is unchanged.

The complete `prepare_literal_na_inputs` producer **refuses**:
`Unsupported line-oriented PHIL syntax`. It feeds all captured PHIL inputs into
the bounded literal compiler, including the flat interpreter-settings file.
No supported literal artifact is published. The first cold review also reaches
that same parser stop when passing the whole input list directly to the compiler;
its original runner is preserved. This is not a native failure or permission to
strip settings.

An explicit **diagnostic input partition** then passes only the two independently
bound literal/plane inputs to the unchanged compiler, while the full native
receipt continues to bind all interpreter controls. This produces 193 C21 terms
(51 bonds, 84 angles, 58 parallelities) and retains twenty planes. The C21 PHIL is
byte-identical to W172. All **213 complete requests** match W176 actual native
readback by content and multiplicity.

The existing `qualify_na_policy` reports **14/14 native mechanics checks PASS**:
atom identities, effective component definitions, policy readback, exact custom
requests, absence of competing native SS terms, and unchanged remaining proxies
across all eight captured families. C128 accepts the genuine native-index policy
for **38 declared backbone links and 51 soft distances**, while keeping
`chemical_qualification=NOT_ESTABLISHED`. **15 binding/compiler checks** also pass.
This is a two-capture fixed-parent policy comparison, not optimizer/force evidence,
nonbonded exclusion qualification or recovery.

Original-intent native receipt SHA-256:
`0b1e68c877b7ee21253411a0f2b5bfb57cd9e2b840c6e9d80c185533e26c006a`.
Diagnostic native-index policy SHA-256:
`dd9b46190f1aab02956c2df0deb9033a2fb504fe8069989ff0b2949225b8dbd4`.
These hashes identify evidence; they do not make a supported ordinary artifact.

**Exact missing producer seam:** classify captured interpreter controls and
literal/plane compiler inputs separately, with every role/input authenticated.
The supported owner must preserve interpretation requirements into later execution
and refuse unsupported/misclassified controls. An arbitrary caller-selected subset
or discarded setting is insufficient. Cedar owns that interface; no duplicate
compiler or forged producer policy is introduced here. A genuine ordinary canonical
parent and selected ancestry remain unresolved, so no request/checkpoint is
fabricated and W173/modified-motion admission remains unchanged.

Local evidence is anchored at
`NASolve:branch-artifacts/willow/w179-original-intent/`; the result resolves its
native receipt beneath the owned root recorded in `ownership.json`. Exact commands:

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w179-original-intent.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B branch-artifacts/willow/runners/w179-producer-review.py
```

Scientific inputs/captures remain outside Git. No branch-wide suite or reinstall
is repeated for this documentation/local-diagnostic change; W177's installed
software remains unchanged. Eight focused roadmap checks and generated-document
synchronization validate the documentation update, without asserting scientific
closure. No additional native run or optimization is queued by this result.


## W180 — Preserve typed reader controls with the literal capture

Cedar `ac339d3ee389083212335a11991e369d88e1093d` integrates the separate
`cif-typed-native-literal-inputs-v1` artifact. Explicit ordered roles and input
hashes bind each literal/plane or interpretation-control input to its genuine
capture. Four reviewed False-valued controls cover sorting, CDL, nucleotide CDL
and NCS restraint copying. Unknown values, missing/repeated roles and changed
native definition readback refuse. Existing compiler bytes and older artifact
semantics are unchanged. The saved W179 artifact contains 193 compiled terms and
20 planes, and manifest SHA-256
`4d4aaf7197d5ecbcfbc3d1364346b37da3914f5a8dd97dbd4ae6baab4c92a6bc`.

Linden's candidate passed 30 new tests, 310 surrounding focused checks and 89
relocated installed checks; Rowan reports 219 focused integration checks. The
public reader exposes separate restraint/control paths, never an executable
combined PHIL list. Ordinary execution still refuses. This closes the typed
producer gap, not ordinary-parent authority or motion. The evidence remains local;
no new native run was needed to replay the saved Phenix 2.2.1-6174 capture.

## W181 — Bind ReadySet restraint comparisons to exact native atoms

Cedar `f27a8dd2c61a6387d1ec8771c607cad43c2c9449` integrates an opt-in ordered
named-request comparison. Only the four PDB atom-name columns may differ, and
only after both display fields bind to their complete native atom identities.
Indices, elements, endpoints, symmetry, selections, targets, order and multiplicity
remain exact. Opaque labels and missing field evidence retain exact comparison.
Historical request policies and selections remain unchanged.

The final candidate passed 247 focused source and 247 relocated installed checks;
313 installed package files match the built wheel/source. A 43-case feature
red check, 20 narrower label-scope red checks and a once-per-capture identity-table
check protect distinct behavior. Saved C464's eight padding-only row differences
pass the new mode; its historical v2 review remains unchanged. Cold C467 still
selects its old verified parent with 26 dictionaries and 17 parameter files.
Linden did not rerun native preparation. Rowan separately reports fresh C471
publication and independent cold relocation selecting the actual ReadySet output.
That report is integration evidence, not a new Willow bending result.

## W182 — Locate the ordinary control owner without admitting execution

Three probes against clean Cedar `999a42ef24d1567a5c16c5e5e4bb6835ddb4f6be`
use the pinned W180 artifact and existing fixture/transport owners. Together with
all 30 typed-control tests, **33 pass in 5.34 s**. `subprocess.Popen` is forbidden.

1. `initialize_postmr_dictionary_request` reaches `_compiler_input` then
   `resolve_literal_na_inputs` and refuses with **Typed controls require owner
   binding before ordinary handoff**. No source acquisition, request, cache or
   process is created. Fixture component settings exercise only this early refusal;
   they do not pretend to be a scientific ordinary parent for the saved model.
2. The three compiled PHIL files reconstruct the exact 213-term restraint context.
   Appending the fourth, control PHIL to that grammar correctly refuses.
3. Direct diagnostic transport through `inspect_native_bundle` passes all four
   byte-identical frozen PHIL files to the supplied runner via `native_spec.json`.
   The exact command is the selected interpreter plus `native_worker.py` and
   `native_spec.json`. The synthetic runner returns 97 before launching anything;
   the result remains FAILED with no native validation or scientific approval.

**Next bounded experiment:** introduce a separately reviewed, opt-in control role
at ordinary request intake and carry it through bundle, continuation/publication
and cold readers. Reuse the current launcher and process owner. Reconcile its
existing generated full-monomer control with the captured declaration, preserving
provenance and refusing conflicting/repeated input declarations. First test missing,
changed, reordered and conflicting controls plus old-policy preservation and cold
relocation. Only then run one fixed-coordinate native comparison proving effective
settings and the same intended 213 restraints before considering deformation.
No new parser, launcher, retrospective ancestry or generic PHIL relaxation is needed.

Local reproducer and exact command are at
`NASolve:branch-artifacts/willow/w182-control-owner/report.json` and the neighboring
`test_control_owner_probe.py`. The report declares the typed-artifact anchor and
checksums; its test checkout is a disposable committed-code snapshot. W182 changes
no production code or schema and makes no installation, portability, full-suite,
refinement or scientific-acceptance claim. The initial probe's wrong hardcoded PHIL
count was corrected to the actual ordered list length; it is not a product red test.


## W183 — Retry the existing cut-preview browser gate

The existing in-app browser inventory exposes the saved ASU representative preview
at `NASolve:branch-artifacts/willow/inspection-2026-11-16/05_cut_preview.html`.
Claiming that known tab with the documented browser tool refused navigation under
its local-file URL policy. No rendered state, preference interaction or download
was observed. This is an access limitation, not a demonstrated viewer defect.
No alternative transport was used to evade the restriction, no synthetic copy was
created, and the earlier DOM/canvas-double results remain the only automated
interaction evidence. P02 remains PARTIAL. The next check is still an actual
permitted browser rendering and preference round trip with unchanged packet hashes;
opening a view is not a human preference or scientific approval.


## W184 — Measure surrounding DNA shifts between completed plane trials

At Rowan's request, compare the saved C466 and C470 five-cycle siblings from
Phenix 2.2.1-6174. Resolve the exact run through C466's declared `local_run`, then
its checkpoint references; verify both model hashes against C470 `science.json`.
Both records name `postmr` as parent and bind the same observations. All **867
ordered identities/elements** and CRYST1/SCALE records agree. Willow's existing
`model_atom_rows` and `CoordinateMask` supply parsing/displacement arithmetic.
No superposition, wrapping, native run, geometry target or model change is made.

Predeclared groups use control six-ring centroids: within 10 Å of either target
is nearby; at least 20 Å from both is distant. NAR maps the six ring roles.
Forty-one sites map completely (19 nearby, 5 distant); DX D:3 lacks all six
landmarks and is excluded from the grouped analysis, but remains in the total.

| Landmark group | Nearby RMS shift (Å) | Distant RMS shift (Å) |
| --- | ---: | ---: |
| Six mapped ring atoms | 0.00687 | 0.01016 |
| Named sugar/backbone atoms | 0.00515 | 0.00561 |
| P and phosphate oxygens | 0.00535 | 0.00511 |

5PC C9 and PDU C5M move **0.05187 and 0.02914 Å**. Their own six-ring RMS shifts
are **0.01491 and 0.01264 Å**. P shifts at A:4/D:5 are 0.00173/0.00447 Å.
The whole-model RMS is 0.00678 Å. Ring-relative tip-height improvements are not
literal atom travel because the ring plane also changes. Nearby backbone motion
is comparable to distant controls; this single comparison gives no descriptive
enrichment supporting preferential local propagation. All B-factor fields differ;
occupancies do not. No causal, helical twist/radius or density interpretation is
claimed. PDB coordinate precision is 0.001 Å and symmetry neighbors are not sampled.

Zero, reverse, expand-roundtrip and independent-distance arithmetic controls pass.
Independent **Gemmi 0.7.5** parsing reproduces every identity and the complete
coordinate RMS/maximum exactly. Source metadata, models and observations remain
byte-identical. This is a read-only coordinate audit, not a new native/refinement
experiment or qualified cluster-opening move. The ordinary-control handoff remains
S04/S05's next step; no milestone is closed by this local result.

The anchored local packet is
`NASolve:branch-artifacts/willow/w184-plane-neighborhood/`. `plan.json` binds inputs
and groups; `result.json` retains all site values; `independent-reader.json` records
the separate parse; `report.txt` is the compact science summary. Reproduce with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<willow>/src <python> -B inspect_shifts.py --nasolve <NASolve> --output <fresh-output>`
using Python 3.12 and the existing NAR/Gemmi environment. Scientific files remain
local. No installed code/schema change or full-suite rerun is required.


## W185 — Check independent PDU trial input equivalence

Read-only comparison of C403 `refine-001` and C475 `refine-002` uses the exact
run declared in C475 `plan.json` and both maintained `read_execution_request`
results. **Ten checks pass over 41 frozen files**, unchanged across the review.
The historical request matches its saved C403 hash. Both requests retain the
same original `postmr` record/model, measured data, five cycles, v3 runtime policy,
chemistry projection, runtime code and scientific command/options. The four
restored dataset inputs independently match their declared checksums.

The sole added input is the declared seven-atom B:4 PDU plane, sigma 0.10 Å.
Every other ordered input is byte-identical, except the exact dataset path in
`autorefine.params`; command differences are that plane and declared dataset/round
paths only. Terminal-phosphate protection is identical. The original B:1 O5′
without P/OP and D:1 P/OP1/OP2/OP3 fixture is preserved, and `postmr` remains
selected. This historical free-OH control does not replace later symmetry-linked
PDU:PDU intent. No input is found by basename, and history is not edited.

The bounded literal compiler rejects the extra `resname` selector. The reviewer
therefore uses the existing structural PHIL parser, exact equality to the declared
selection and explicit seven-atom membership, without changing that grammar or
claiming compiler admission. Actual Phenix plane membership and child geometry
remain Rowan's readback. This review runs no native command, verifies no child
outcome and grants no scientific acceptance; it compares frozen inputs rather
than claiming every process/environment condition identical.

Reproducer and checksummed input references are local at
`NASolve:branch-artifacts/willow/w185-independent-pdu-inputs/inspect_inputs.py`
and `result.json`. Exact invocation:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<cedar>/src <python> -B inspect_inputs.py --nasolve <NASolve> --output <fresh-result.json>`.
No product/schema/default change, installation or full-suite rerun is involved.


## W186 — Carry captured reader controls through ordinary preparation

Cedar commit `04d506c5866d9075cfa4076de59fd269ee04f267` delivers the W182 missing
role. Python callers explicitly choose `cif-captured-reader-control-handoff-v1`
with authenticated typed literal input. Original PHIL bytes/order and model binding
remain checked; geometry and reader settings remain separate. Complete requests,
acquired preparation and stored bundles freeze the ordered reader role. The
existing launcher carries it unchanged; only redundant generated NCS=False is
omitted when the captured declaration already supplies it. Conflicting, missing,
changed, reordered or unknown controls are refused. The generic literal resolver
and old artifacts retain their behavior; older readers refuse the new opt-in role.
No outer schema version, CLI or campaign default changes.

The six changed runtime modules, exact commands, hashes, additive field locations
and qualification are in Cedar's
[technical evidence at the integrated commit](https://github.com/vecchioni-lab/NASolve/blob/04d506c5866d9075cfa4076de59fd269ee04f267/docs/cif-linked-native-registration-evidence.json),
key `captured_reader_control_handoff_2026_11_21`; its
[API contract](https://github.com/vecchioni-lab/NASolve/blob/04d506c5866d9075cfa4076de59fd269ee04f267/docs/cif-doctor.md#explicit-captured-control-handoff-w186)
is owned by Cedar. Willow records the join without duplicating that implementation.

Two fail-before cases demonstrate the missing API, and all **25 new tests** pass.
The focused source command (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, Python
3.12.14, `-B -m pytest -q -p no:cacheprovider`, exact twelve-file list in the linked
receipt) passes **558 tests in 667.01 s**. A separately built/relocated wheel passes
**546**, with **12 fixture failures**: the test copy lacked six CIFs in its expected
source-tree fixture layout, although they were present in the wheel. Copying those
six installed CIFs into that fixture layout, with no runtime/test-source changes,
lets the 12 compiler-intake tests pass in 21.11 s. The original build source and
installation path are gone; six runtime source hashes match. This is a corrected
546+12 installed result, not an uninterrupted 558-test pass. No full suite ran,
per the scoped push. The historical Cedar full-suite baseline is not new validation.

One actual Phenix **2.2.1-6174** fixed-coordinate capture, without diffraction or
refinement, retains **859 atoms / 42 full monomers / 213 terms** (51 distances,
84 angles, 58 parallelity, 20 planarity). Four effective settings are False and
appear once, with identical ordered input bytes. A reviewer initially compared
untyped PHIL string tokens with booleans; re-reading the saved capture through the
native master schema corrected the reviewer without repeating the native run.
The receipt is `w186_native_check:capture/cif-native-srqes1xw/native_receipt.json`,
SHA256 `a0d7d83ff4959209817cc1cae046a5dcc6a5c89c88f264f9ab02398a59074890`.
Native inputs, captures, wheels and local runners remain excluded from Git.

Synthetic complete/ReadySet transport tests and this real direct native capture
are separate proofs. No real complete ordinary-parent execution, retained-manager
motion, geometry acceptance or nanocluster widening is established. Alder's older
read-only bridge must explicitly adopt the role; selected runtime manifests keep
it in their authenticated source bundle, not a duplicated top-level field.

## W187 — Reopen a real canonical PostMR root with the original inaccessible

The declared geotest inventory selects the X11_22 member ending `cd527b22bf7e`,
its `AutoMR/run_001` report, and the explicit PostMR root. All 2603 atoms are
canonical DA/DC/DG/DT. Model and observation checksums are verified. The real
selected checkpoint remains `refine-001`; only a fresh local root closure is written.
This is distinct from the private 859-atom bend example and cannot supply its ancestry.

The first replay stopped honestly: copying an unchanged legacy schema-1 report
under `fresh-dataset` prevented its exact dataset-component rebase, so the still
available historical absolute MTZ path won. The report contains an absolute
`inputs.reflections` string/checksum and string `dataset`, not an ignored declared
observation anchor. Its original schema-2 checkpoint already has an explicit
`dataset` reference. Current `automr.prepare_automr` retains that schema-1 input
writer; `checkpoints.initialize_registry` → `_root_payload` →
`_required_observations` → `_required_file` uses the legacy resolver for this report.
A checked preparation's declared observation anchor takes a separate strict route.

A second protected copy preserves the exact declared dataset component for
initialization, using explicit inventory/root references and checksums, with no
input search or report rewrite. The normal writer produces the expected schema-2
run/model and dataset/observation references. After renaming this copy to
`relocated-dataset`, with its earlier path absent, a fresh process reopens the
same registry and identical Willow preparation-availability digest. Original
science open/stat calls are denied to each Python reader, with positive guard
controls and **zero original access attempts** during successful owner operations.
This is reader-level isolation, not an OS/container isolation claim. A separate
protected negative confirms the first renamed legacy report refuses initialization
when its historical fallback is unavailable. The first guard harness needed ENOENT
on its synthetic FileNotFoundError; that pre-owner stop is retained too.

Five original hashes and `refine-001` selection remain unchanged. This proves
ordinary root metadata and anchored cold readback, not portability of the complete
historical run. The inspector correctly returns `NO_CHECKED_PREPARATION`, with
model/restraint/compiler authority unavailable. No inherited PHIL/CIF exists;
historical guessed-pair diagnostics do not become compiled restraint authority.
No acquisition, native process, Phenix run, refinement, chemical admission or
runtime patch is involved. There is no demonstrated ignored-anchor bug to fix.

Local anchored evidence: `NASolve:branch-artifacts/willow/w187-canonical-root/`
contains `plan.json`, `initial-stop.json`, the protected negative, normal-writer and
cold-reader snapshots, and `result.json`; the roadmap binds receipt hashes.
The preserved initial runner and follow-up are under
`NASolve:branch-artifacts/willow/runners/w187-canonical-root.py` and
`w187-root-review.py`. Exact follow-up invocation:
`PYTHONDONTWRITEBYTECODE=1 <python3.12> -B <NASolve>/branch-artifacts/willow/runners/w187-root-review.py`.
These are immutable one-shot diagnostics, not an installed regeneration command.
Original/copy roots in the ownership record are local anchor provenance.

Next define prospective parent topology/restraint intent through existing owners
for this exact canonical parent, then qualify its fixed native capture before
coordinate transfer. Preserve dictionary acquisition >=1 rather than constructing
an empty chemical bundle. S04/S05/S06 remain partial; do not repeat completed
transport/root probes or infer scientific closure from this metadata result.


## W188 — Inspect native support across a real preparation window

Code `adca2e07c50cb313541918f261c6a4c80ea6745b` adds the read-only native-window API
to the existing preparation module. It composes the preparation inspector with
Cedar's maintained capture/atom/full-monomer/named-endpoint readers; no native
parser or force calculator is copied. This turns W175's private partition into
an exact ordinary-parent inspection with source/native order mapping, captured
family status, named boundary rows and actual proxy multiplicity. No checkpoint
schema, default, CLI, selection or motion behavior changes.

One fixed-coordinate Phenix **2.2.1-6174** capture reads the W187 canonical parent.
A prospective E9–E13 window selects all **102 atoms** in those five residues;
**2501 atoms** are outside it. Its capture covers **2603 atoms / 128 monomers**.
The selected region is not a declaration of its duplex mate or a qualified bend
window. Atom-order preservation and full monomer mapping are new explicit capture
settings, not reconstructed historical refinement settings. The initial output
layout was refused before native launch; moving the exact PHIL bytes into an input
subdirectory permits the single actual capture, completed in **11.63 s**.

| Captured proxy family | Selected | Boundary | Fixed remainder | Total |
| --- | ---: | ---: | ---: | ---: |
| Simple bond | 113 | 2 | 2801 | 2916 |
| ASU bond | 0 | 0 | 0 | 0 |
| Angle | 172 | 8 | 4308 | 4488 |
| Dihedral | 47 | 6 | 1299 | 1352 |
| Constant dihedral | 31 | 0 | 1009 | 1040 |
| Chirality | 20 | 0 | 485 | 505 |
| Planarity | 5 | 0 | 123 | 128 |
| Parallelity | 0 | 0 | 0 | 0 |

The two boundary bonds are **E8 O3′–E9 P** and **E13 O3′–E14 P**, each with a
captured 1.607 Å target. There are **16 named crossing terms** in total. Coordinates
and source selection are unchanged; no optimizer or refinement ran. The source
has no inherited PHIL/CIF and the capture has zero custom requests. Neither fact
establishes missing physical pairing/stacking/interactions. Complete monomer
mapping is not complete-atom chemical quality or scientific acceptance.

The inherited-file check is byte/multiplicity inclusion, allowing explicit
additional capture inputs; it does not prove identical effective settings or
original role/order. Rowan independently reviewed this distinction, full endpoint
binding and two-list parallelity. A future execution gate must bind ordered roles,
settings and prospective topology/interaction intent separately.

The new regression fails before implementation (missing API). **25 new cases**
cover native/input reorder, repeated boundary terms, both parallelity planes,
missing versus zero evidence, parent/receipt/context pins, capture-time drift,
inherited-input multiplicity and old-path-gone relocation. Exact focused command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider \
  tests/test_topostitch_native_window.py tests/test_topostitch_preparation.py \
  tests/test_topostitch_checkpoint.py tests/test_topostitch_execution.py \
  tests/test_topostitch_endpoint.py
```

Python **3.12.14**: **117 passed in 4.28 s**. A newly built wheel, with build source
removed and the original installation path gone, passes the same **117 tests in
3.64 s** using `PYTHONPATH=<relocated-install>` from an isolated test copy. Wheel
SHA256 `46d1a3433110781329986a730961f03477b01d41ae8543d0b9553f216db0d8df`;
runtime module SHA256 `3fc83d7a9d4aeb92de4ce09769fc16c1822d78a56d783b44ab817892fa5ba158`.
No full suite ran, per the scoped push.

The installed reader also reproduces the exact real report after copying/renaming
its root and capture, with old copy paths gone. Fresh-process original open/stat
denial and positive guard controls pass, with **zero original access attempts**.
This is reader-level isolation, not OS isolation. Scientific inputs and original
selection are untouched. Source and installed readers use the same trusted Cedar
`04d506c5` modules; this is a composed read-only API check, not a merged release.

Local evidence remains excluded from Git at
`NASolve:branch-artifacts/willow/w188-canonical-window/`: `plan.json`,
`layout-stop.json`, `capture.json`, `window-report.json`, `review.json`,
`installed-check.json` and `cold-installed.json`. The roadmap binds receipt hashes;
local ownership records supply anchor provenance. Native receipt:
`w188_capture:native/cif-native-589qdd0b/native_receipt.json`, SHA256
`8c8780da19411414677703f28be8288213c4f4fa014bab92d660fc4fe7dbf318`.
The source review preceded a computation-preserving set-lookup optimization; final
installed source hashes and identical real report establish final-code parity.

Next use the existing Cedar captured-geometry reader to examine these actual
boundary targets and current covalent strain before planning a deformation. Keep
torsion/plane conventions, absent pair intent, nonbonded scope and density separate.
No new native capture or duplicate metric engine is needed for that question.


## W189 — Measure the existing local and remote covalent baseline

The existing Cedar `cif_captured_geometry.review_captured_geometry` reads W188's
saved exact capture. No runtime modification, new native interpretation, optimizer
or refinement occurs. All **7909** bond/angle/chirality scalars retain their actual
native index and window partition; the **10** boundary bond/angle values reproduce
with independent distance/atan2 arithmetic to 1e-10. Inputs and selection are unchanged.

The two edge bonds are **1.59668782 / 1.62668251 Å**, against **1.607 Å** targets.
Eight boundary angles have maximum absolute target difference **2.53505544°**;
all ten edge scalars are below three nominal deviation units. Selected-window
bond/angle RMS differences are **0.01028839 Å / 1.14480175°**, with one internal
angle above three nominal units and none above five. Its 20 captured ordered-volume
signs agree with their targets; this does not establish independent absolute
stereochemistry or sugar pucker.

The unselected remainder already contains **7 bonds and 26 angles above five
nominal units**. Worst examples are B1 O3′–B2 P **1.28539255 Å** and C1 O3′–C2 P
**1.39036326 Å**; their C3′–O3′–P angles are **148.996676° / 142.734004°**, against
119.7° targets. These are defects in this unmodified original **PostMR parent**,
not a result of a bend and not an assessment of the selected `refine-001` child.
Future local/global comparisons must preserve this baseline rather than attributing
all remote strain to a new candidate. Nominal deviation is the existing reader's
(descriptive) difference × sqrt(weight), not a native residual or calibrated gate.
Six crossing dihedrals remain unscored; pair/stack intent, symmetry/image closure,
nonbonded geometry, density and chemical/scientific acceptance remain separate.

The compact local checkout is
`ScienceCheckouts:Linden/2026-11-21_canonical-boundary-baseline/geometry-baseline.html`,
with PNG/SVG figure, exact JSON and W188 window report. **Matplotlib 3.11.1** in the
existing Phenix Python environment generated the standard plot; the PNG was visually
inspected for labels, units and clipping. Raw models/MTZ/native captures stay in their
original local locations. No figure or unpublished numerical result file is uploaded.

Anchored receipts are in `NASolve:branch-artifacts/willow/w188-canonical-window/`:
`geometry-baseline.json` binds model/capture/window and reader/controller hashes;
`geometry-baseline.html` and PNG/SVG explain the findings. Reproducer:
`PYTHONDONTWRITEBYTECODE=1 <python3.12> -B <NASolve>/branch-artifacts/willow/runners/w189-boundary-geometry.py`.
It is an immutable one-shot local diagnostic; do not overwrite its output. The
unchanged geometry owner is Cedar `04d506c5`; no new installation or suite rerun
is needed for this evidence-only step.

There is no independently declared paired-window target authorizing a bend in this
root. The next maintained source/intent step is to compose the existing
`cif_model_context.derive_prepared_model_context` with the exact parent reader,
keeping DERIVED ordinary backbone context distinct from checked preparation.
An initial direct call returns 121 standard links and all 128 canonical sites.
This is the ordinary auditor's coordinate/frozen-plan derivation, not independent
experimental topology or permission to invent missing sticky-end partners.

## W190 — Bind derived ordinary source connectivity

Code `776f0c316e06d8198d438a6c39b84e2fef18c82f` adds only an explicit optional
ordinary-model-context owner in `topostitch_preparation.py`; eleven additional
cases in `test_topostitch_native_window.py` cover source binding and refusal.
Before: ordinary checked authority was unavailable with no maintained source-intent
join. After: original canonical roots can report separately derived source context,
while checked authority stays unavailable. Defaults and schema versions are unchanged.

The genuine 2603-atom/128-residue source yields 121 standard backbone links through
Cedar's existing `cif_model_context`. Its existing topology reader matches all 121
against W188's saved capture. Removing one expected edge yields REVIEW with one
unexpected link. This agreement is between two source-derived interpretations,
not independent topology truth. No pairing/stack intent or motion approval follows.

Validation command (both source and relocated installation, Python 3.12.14):
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider
 tests/test_topostitch_native_window.py tests/test_topostitch_preparation.py
 tests/test_topostitch_checkpoint.py tests/test_topostitch_execution.py
 tests/test_topostitch_endpoint.py`.
Source **128 passed (3.80 s)**; fresh relocated installed **128 passed (3.75 s)**,
with PYTHONPATH replaced by the installed package path and build source removed.
A new-API test fails before the patch. A protected fresh installed reader reproduces
the actual result with original-path open/stat denied and zero access attempts;
this is reader-level protection, not OS isolation. Default W188 JSON is identical.
Wheel SHA256 `5d2118b595d258e5646b8f912ba777a886a99a76b93c87be47f7d819d0ff70bb`.

Local-only evidence uses anchor `NASolve`, relative directory
`branch-artifacts/willow/w190-source-context/`: `review.json`,
`ordinary-context-window.json` (SHA256
`ee15cca6432f8dcd333f3293dd0e78dda39b5ba4cedcd4b24ba337112f245dcd`),
`native-topology.json` (SHA256
`63c22a65c365eefd6c565418c638c28e8ee2516ac16cd1b53a20f07a3a0a7d92`),
and installed/cold-read receipts. Cedar source is `04d506c5`; this reuses the saved
Phenix 2.2.1-6174 capture and makes **no new native execution or refinement**.
No generated science is committed. No migration is required. Modified roots,
refined descendants, independent pair/stack intent, effective input-order/settings
identity and motion acceptance remain separate. No full suite was run, as scoped.

## W191 — Measure explicit paired phosphate spans

Code `d50076e92af79e765841f8d4dc1679a059167c8c` adds `helical_geometry.py` and 34 targeted
cases in `test_helical_geometry.py`. Before: C444 was an offline public-coordinate
pilot only. After: one installed read-only API/module CLI preserves explicit logical
pair order, exact components/sites/conformers, core/flank roles and breaks; it binds
model/region hashes and reports each missing/ambiguous phosphate independently.
The new schema-1 report does not change any existing artifact or require migration.
No dependency, automatic pairing, ring projection or workflow default is added.

Exact focused command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest
-q -p no:cacheprovider tests/test_helical_geometry.py tests/test_topostitch_coordinates.py`.
Python 3.12.14: **67 source passed (0.29 s); 67 fresh relocated installed passed
(0.26 s)**, using the installed path instead of `src`. The new API fails import
before implementation. Tests include rigid motion, isolated pair perturbation,
component/conformer ambiguity, insertion codes, absent phosphates, explicit breaks,
source drift, duplicate physical identities and relocation with the old path gone.
Wheel SHA256 `aecf61096691d733127af859a77962b7b156b0941f7699abd26cf326b2d01d38`.

One public control downloads exact [7SDF PDB bytes](https://files.rcsb.org/download/7SDF.pdb),
SHA256 `19b942e87abbbc1021225da11d704ad83bb221fbfcb33ac264bd447eb76df21c`,
and declares A9–15/B7–1 in the identity image. Seven measurements independently
reproduce; A12 DC/B4 IMC = **18.1937341137 Å**, identical to C444's independent
Gemmi-based pilot. Its half-span is 9.0968670568 Å, not an axis radius. Removing only
B4 P leaves six exact results and one missing measurement. A relocated installed
CLI gives identical full JSON after its original model/installation copies and
build source are gone. Public/local evidence stays under anchor `NASolve`, relative
`branch-artifacts/willow/w191-phosphate-spans/`; report SHA256
`cdb3fd3ecb6abf9da45897a247ff84f6de02cf26497f65006b1ea0e20ea40d94`.
No PDB or generated report is committed. No Phenix/Coot call, fit or coordinate change.

H1/H2 remain partial and H3 open: nonidentity images, mmCIF, registered cross-state
correspondence, modified ring frames, axis radii, weighted regional twist and the
7SDG discrepancy still need their own qualification. Existing C444 pilot evidence
is preserved; this slice does not claim agreement for unimplemented quantities.

## W192 — Resolve the simple-twist normal convention against the reference

The [author's printed 1XVK example](https://x3dna.org/articles/simple-parameters-for-non-watson-crick-base-pairs)
provides seven signed simple-step values. Exact RCSB biological-assembly bytes
(`1XVK.pdb1`, SHA256 `0be88f42985e557973ea4e3aef4eb377528bd7aae34ef6cd71fec2b90dbf183c`)
contain two coordinate MODEL blocks: explicit MODEL1 A1–8 pairs with MODEL2 A8–1.
No new symmetry expansion or inferred production assignment is made. The initial
C444 pilot refuses alternate C1′ positions; the [documented default](https://x3dna.org/articles/about-alternate-location-altloc-field)
selects blank/A/1, not the highest-occupancy conformer. Using only that atom-selection
adapter retains the original pilot's failures: steps 1/4/5 give 113.23548/−0.00555/
−132.93433° against the historical printed 23.36/25.67/25.70°. Four other steps match.
Exact selected ring/C1′ identities, altlocs, occupancies and coordinates are retained.

The official archived [source](https://github.com/x3dna-dssr/x3dna-v2.4/blob/43eafa8407be1a8292e38ca995ab16adfbeffcac/src/analyze.c#L237-L247)
requires both pair normals to point along the pair-origin displacement **before**
C1′ frame construction and midpoint untilting. A preliminary nearest-hemisphere
diagnostic is retained separately; it is not the adopted source definition.
Applying the source rule gives 23.36225/25.66901/25.70505° for those three steps.
A temporary source build at commit `43eafa8407be1a8292e38ca995ab16adfbeffcac`
(Apple clang 21.0.0; `make -j2 analyze find_pair`) supplies **3DNA v2.4.10-2026nov01**.
Complete `find_pair -symm 1XVK.pdb1 1XVK.bps` and `analyze -symm 1XVK.bps`
runs reproduce the declared eight-pair mapping. All seven corrected steps agree
with the fresh reference at two decimals. Its step 5 prints **25.71**, whereas
the historical web table prints **25.70**; neither result is relabelled or rounded
to force agreement. This confirms one current-input/current-reference control,
not universal simple-twist equivalence or qualification of an axis method.

The same reference's `find_pair -s 7SDG.pdb all.bps` establishes residue ordinals;
`analyze declared-region.bps` then uses explicit A9–15/B7–1, identity coordinates.
All six printed simple twists agree with C444. The two flanking steps give 30.36°
from the printed table (pilot 30.35568286°), not the recorded S15 value 32.08°;
the edge mean is ~37.92° versus 37.63°. The ordinary local-step mean is 34.49°,
so merely substituting that quantity does not resolve the discrepancy. Historical
SI model/image/assignment provenance is still required. No publication correction
or inferred replacement target is asserted.

Local-only evidence: anchor `NASolve`, relative directory
`branch-artifacts/willow/w192-simple-twist/`, `review.json` SHA256
`942a92f77583f3d3a7b5589c79a077ade121a1a820a33786c695ad98ceec26c1`.
It pins raw/corrected comparisons, assembly/atom mapping, both exact models,
reference requests/outputs, source commit and executable hashes. Four complete
reference analysis calls; **zero Phenix/Coot/refinement calls**, no coordinate or
product changes. No third-party code, executable or raw science is committed.
Use the same independent controls when implementing the maintained metric; retain
missing/degenerate orientation and modified-frame gates. W191 phosphate distances
remain independently qualified, with no axis or twist inferred from those spans.

The compact local checkout is
`ScienceCheckouts/Linden/2026-11-21_helix-measurement-controls/index.html` with a
visually checked PNG/SVG, paired-span JSON and twist evidence inventory.
Matplotlib 3.11.1 rendered the two independent controls; no models are copied into
the checkout. Local links/JSON validate. The temporary reference build, redundant
copied test trees and clean already-integrated W186 worktree/branch were retired;
build/source manifests, wheels, validation logs and all science remain retained.


## W193 — Maintain canonical simple step twist

Code `80bfb8582f7c60848f5d47ca90bc4bbd8e287100` adds `helical_twist.py`, generalizes the existing
site-atom selector without changing default P-span reports, and adds focused
regressions. Opt-in schema-1 `regional-helical-geometry` records canonical fits,
atom mappings, signs, missing reasons and the W192 convention. No migration or
new dependency; use the existing optional Gemmi 0.7.5 extra. H1/H2 stay partial.

Validation (Python 3.12.14, `PYTHONDONTWRITEBYTECODE=1`):

```bash
PYTHONPATH=src:/private/tmp/w193-qualification-c1tf1610/optional-relocated \
  python -B -m pytest -q -p no:cacheprovider tests/test_helical_twist.py \
  tests/test_helical_geometry.py tests/test_topostitch_coordinates.py
```

**96 source + 96 fresh relocated installed checks pass**. The new regressions
first fail without the implementation; the installed module test also exposed
and fixed duplicate `__main__` declaration-class identity. Sign/rigid controls,
missing/ambiguous atoms, degeneracy, declared breaks and coordinate drift are
covered. Installed tests use the same command with `PYTHONPATH` set to the
relocated wheel and optional-dependency targets, copied tests and original build/
install paths removed. No full suite: this is an isolated opt-in measurement.
Wheel SHA256 `8456646205d21bc38aa6522d98f93603a4ce5f8916e35513f236da33d63aacb2`.

Existing W192 reference outputs supply independent values from **3DNA
v2.4.10-2026nov01**; no new reference or Phenix execution. 1XVK's two biological
MODEL copies are explicitly flattened to A/Z for this diagnostic, preserving all
selected coordinates and source-atom mapping; this is not a crystal ASU. All
7 steps match at two decimals, including three former non-WC failures. Exact
7SDG A9..15/B7..1 matches all 6 steps. With a declared 0.15 Å fit limit, maximum
ring RMSD is 0.02940 / 0.01874 Å. Missing terminal phosphates leave 6/8 1XVK spans
but all 7 twists. The old 1XVK web step-5 0.01° difference and 7SDG SI provenance
problem remain unresolved historical distinctions, not fitted corrections.

Both fresh installed public CLI reports match after copied inputs are relocated;
default W191 7SDF report is unchanged with Gemmi absent. Local evidence uses
anchor `NASolve`, directory `branch-artifacts/willow/w193-simple-twist/`:
`public-review.json` SHA256 `94c928d8edf5391b30018895ca48f4fff639def6049d101837985551a0b6ad54`;
`installed-check.json` SHA256 `25145ac4b1e78e9b9deb21d0177e92dcdd3edb4e301d42bd1bd0f256a7a8cd6c`.
Raw coordinates, frame reports, runners and build products are excluded from Git.
Next: named-state correspondence; modified frames, axis radii, regional summaries
and real bend/acceptance remain separate gates. P–P span/half-span is not radius
and this signed twist is not a measurement of helix curvature.


## W194 — Compare explicit named helix states

Code `ab02a1bd25a6f000d0896e1cf6e46e5510da6c35` adds `helical_comparison.py` and its focused tests.
Before this slice, the caller had separate measurements without maintained
correspondence/delta handling. The new schema-1 API requires named, byte-pinned
states, complete explicit pair accounting and declared I→I/II→II strand mapping.
It composes existing readers; no separate geometry calculation, CLI/default change,
new dependency, source migration or physical-equivalence claim. Missing mates,
changed components/roles and reversed/nonmatching adjacency remain visible.

Validation (Python 3.12.14, Gemmi 0.7.5):

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src:/private/tmp/w193-qualification-c1tf1610/optional-relocated \
python -B -m pytest -q -p no:cacheprovider tests/test_helical_comparison.py \
  tests/test_helical_twist.py tests/test_helical_geometry.py tests/test_topostitch_coordinates.py
```

**113 source + 113 fresh relocated installed checks pass**. The new tests fail
before implementation. Renumbering, partial/duplicate mapping, changed chemistry,
per-state missing atoms, signed wrap/half-turn ambiguity, declared breaks,
reordering, local perturbation and source drift are covered. Installed tests use
the same copied test set with `PYTHONPATH` pointing to relocated package/Gemmi
roots after build/install/input-copy originals are gone. Five real reports match
exactly through a fresh installed process; five phosphate-only comparisons also
work without Gemmi. Wheel SHA256
`89db06cd49e2a6ea344f091bff99465b38f99d305f7810addc6d5b1b9aa6e0da`.
No full suite: isolated optional analysis, unchanged workflow mechanics.

The immutable W163/W164 six-model local packet supplies actual 5W6W generator,
relaxed control, signed starts and recovered endpoints, using declared A9..15 /
B7..1 pairs. All six model checksums match their original manifest; 35 span deltas
independently match Gemmi atom lookup/distance calculations. All 30 twist deltas
are available under the declared 0.15 Å ring-fit policy. Starts move ~2.288 Å RMS
while their spans differ by <0.001 Å: paired sites rotate together. Recovered
positive/negative maximum |twist change| is 2.193°/0.262°; relaxed control 0.128°.
The positive maximum is A13/B3→A14/B2. Maximum |span change| is 0.0555/0.0314 Å;
control 0.0132 Å. This preserves the previous positive covalent-distortion finding,
not a new repair or causal diagnosis. These are neither axis radii nor curvature.

No new native execution: saved source recovery used Phenix 2.2.1-6174 and matching
noiseless synthetic diffraction, as recorded in W163/W164. New figures use
Matplotlib 3.11.1 only. Local evidence anchor `NASolve`, directory
`branch-artifacts/willow/w194-helical-state-comparison/`:
`request.json` SHA256 `61226a5782219b8fd30d95015d79a7b1e151ff53d11bfdc796b1826977c648e1`;
`review.json` SHA256 `219010ed4a3db5b06a3f20f284707c5ba707376936b064b06709ed81246d7d5c`;
`installed-check.json` SHA256 `fe11e4ad08a2df6b393a3ac8d35dbb3bf41356c319008694eda0e8027640435e`.
Inputs are resolved only through that request's declared GitHub/checkout anchors
and verified checksums. Raw science, figures, reports and runners remain outside
Git. Small visual checkout: GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_helix-state-comparison/index.html`, with checked
local links, inspected PNG/SVG and a standard-Python checksum/open helper.

H3 advances to partial for explicit named-state changes. Weighted region summaries,
publication export and modified-site qualification remain open; H1/H2 also retain
registered-image, modified-frame and local screw-axis gates. Next audit actual
step weights/gaps and near-zero helicity rules before adding summary arithmetic.


## W195 — Declare regional step weights and retain coverage

Code `796af35a5a9f4dc8a40fc970dffa917c2b807dc9` extends only `helical_twist.py` and adds focused
summary regressions. The new opt-in function retains the existing schema-1 raw
measurement and adds a method-versioned weighted summary. One finite nonnegative
weight per step is required. Positive weights cover one contiguous segment;
missing included values, disjoint selections and angle ranges >=180° leave the
mean unavailable. No zero filling, observed-only renormalization or guessed
unwrapping. Signed bp/turn is 360/mean only beyond the caller's explicit positive
mean-magnitude limit; that policy is not experimental uncertainty.

Exact focused command (Python 3.12.14, Gemmi 0.7.5):

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src:/private/tmp/w193-qualification-c1tf1610/optional-relocated \
python -B -m pytest -q -p no:cacheprovider tests/test_helical_summary.py \
  tests/test_helical_comparison.py tests/test_helical_twist.py \
  tests/test_helical_geometry.py tests/test_topostitch_coordinates.py
```

**136 source + 136 fresh relocated installed checks pass**; new imports fail
before implementation. Local/two-flank, full-edge and half-step weights, missing
coverage, gaps, signed/near-zero means, ambiguous wrap and numerical overflow
are covered. No full suite for isolated optional analysis. Installed tests use
the same copied test set and relocated package/Gemmi targets, with original
build/install/input-copy paths removed. Twelve summaries match fresh installed
API output; five prior W194 reports remain identical, and base phosphate-only
comparison still works without Gemmi. Wheel SHA256
`31b37baac555a4cf5ad2fe6056070a6653ce026d2207a1912863d42dcd1a55c2`.

Existing W163/W164 six-model evidence only: six full-step edge summaries and
six central A12/B4 two-flank summaries under a declared 0.1° minimum mean and
0.15 Å ring-fit limit. Generator edge/local 36.421601°/32.834048° reproduces C444.
Positive recovered edge mean changes −0.122274°, local mean +0.219737°; the
known −2.192997° A13/B3→A14/B2 step departure and covalent defect remain. Regional
cancellation is why the next science task returns to S04/S05 local repair and
source-bound comparison rather than a descriptive axis metric. The existing
W194 figure/coordinate packet is sufficient; no new checkout or export layer.

No new native/refinement execution or coordinate changes. Local evidence anchor
`NASolve`, directory `branch-artifacts/willow/w195-regional-summary/`:
`review.json` SHA256 `98304f55520704e34b57d316bb3df4635723c47fb462d0309e83d5b817a826e6`;
`installed-check.json` SHA256 `d2ff6d54f5625d6f014f7aaaabfc3bb297867b045cacdcddab362b43a692f2d5`.
Input references reuse W194's exact anchored request/checksums. Raw science and
local runners stay out of Git. No migration/default/dependency changes. H3 remains
partial pending modified-site qualification/publication export; H1/H2 retain
registered-image, modified-frame and axis gates. Do not relabel a historical
private taper as a prospectively authenticated registered preview.


## W196 — Replay a prospective interior paired window

Code `020aa1ba030cd30a375642f2408a69b6a099449f` changes only the existing `topostitch_preview.py`
owner and adds focused interior regressions. Schema-3 trials retain registered
source/discovery identity, explicit ordered antiparallel pairs, declared [0,1]
weights, source-derived pivot and zero-weight paired flanks on both sides.
Canonical mapping, whole-residue rendering, extended backbone audits, portable
snapshots and unrounded `TaperedMotion` replay are reused. No new force engine,
export layer, checkpoint ancestry or native retention hook is manufactured.
Schema-1/2 terminal reports and APIs remain unchanged; old readers reject schema 3.

**155 focused source + 155 fresh installed checks pass** for:
`test_topostitch_interior_preview.py`, `test_topostitch_preview.py`,
`test_topostitch_checkpoint.py`, `test_topostitch_execution.py`,
`test_topostitch_view.py`, `test_topostitch_fit.py`. New success cases fail before
implementation. Protected junctions, changed parent, route gaps, invalid weights,
byte-fixed flanks/context, stale receipts, displacement bounds and relocation are
covered. The complete optional fitting/view checks use existing Phenix Python
3.11, SciPy 1.17.1, Gemmi 0.7.5 and isolated copies of NARestraints 1.1.3 with
openpyxl 3.1.5/et_xmlfile 2.0.0. Initial harness attempts lacked PYTHONPATH/NAR/
openpyxl; completing that environment yields the same unchanged-code pass.
No crystallographic Phenix program or full repository suite was run.

Exact source runner, from the Willow checkout (the temporary dependency root is
qualification provenance, not an operational artifact reference):

```bash
PYTHONDONTWRITEBYTECODE=1 phenix.python -B -c '
import os,sys
from pathlib import Path
paths=[str(Path("src").resolve()),"/private/tmp/w196-qualified-3a52c_8h/pure-dependencies"]
sys.path[:0]=paths
os.environ["PYTHONPATH"]=os.pathsep.join(paths)
import pytest
raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",
 "tests/test_topostitch_interior_preview.py","tests/test_topostitch_preview.py",
 "tests/test_topostitch_checkpoint.py","tests/test_topostitch_execution.py",
 "tests/test_topostitch_view.py","tests/test_topostitch_fit.py"]))'
```

The launcher resets PYTHONPATH, hence the explicit bootstrap. Installed tests use
the same copied fixture closure and relocated wheel path instead of `src`, after
build/install originals are removed. Wheel SHA256
`fc671694bed12c4842dde07bc844bb614520ce3ba23588479420ae9a71690ab0`.

Fresh direct-input 5W6W proposals use existing checksum-verified coordinates and
literal identity registration, explicit A9..15/B7..1 routes and no claim of
complete global topology. Zero/±2° Cartesian-Y rotations, pair weights
`[0,.2,.4,.7,1,.5,0]`, central-pair pivot and two paired flanks are declared before
execution. All 859 atoms remain; 205 move and 654 stay fixed. Maximum signed-start
motion is ~0.400 Å; zero preserves every source byte. Max link/angle/torsion
changes are positive 0.17178 Å/5.94510°/4.52854°, negative
0.18189 Å/5.58918°/4.01827°. These are source-relative trial costs, not healthy
geometry or a repaired endpoint. Changed-parent checks refuse all three packets.

All three reports and endpoint audits reproduce from a fresh installed Python
3.12.14 process after original packet-copy paths are gone; the installed CLI
rebuilds the positive candidate exactly. Cross-version Python 3.11 replay refuses:
PDB bytes match but 30 audit scalars differ at last bits (~1e-14 degrees). Preserve
this exact-replay limitation rather than claim universal numerical portability
or relax admission. No source/runtime tolerance changed.

Local evidence anchor `NASolve`, directory `branch-artifacts/willow/w196-interior-preview/`:
`review.json` SHA256 `8ce18dbc110a0abdb03e76a839657adaf7d42bc731eebe2fbf1586d0e7c97d4d`;
`installed-check.json` SHA256 `9ce61d7668187ac050dc859a3f03266304bd771db9df5675492880470fdf440e`.
New source/registration/discovery/trial snapshots and zero/positive/negative PDBs
remain local and uncommitted. Existing viewer HTML is beside each packet; no new
checkout framework. Next bind a prospective motion to legitimate current-parent
preparation and qualified native retention, then assess local recovery. This
slice does not retroactively qualify the private W163 taper or close S04/S05/S06.

## W197 — Recover a signed interior window with fixed end frames

**Question and distinction.** W196 supplies fresh source-bound interior proposals,
but W168's all-site relaxation cannot prove fixed-frame recovery. Its old SS-enabled
policy is also C128 REVIEW. This new panel therefore uses W172's independently
declared 38 backbone links and explicit C21 20-pair/38-stack policy, retaining
the twenty original pair planes: 213 custom requests including 51 authorized
soft distances. It is a new fixed-scope experiment, not another proof of W168's
private lifecycle and not continuation under its older objective.

The existing W172 private worker and C407 installed execution/process owners are
reused. Scoped observation adds the actual native atom selection and checks six
full-model coordinate updates per refinement; native source, forces and optimizer
are unchanged. Preflight/refinement topology outputs are phase-separated. Each
case is a new immutable execution; no interrupted child was resumed or replaced.
The controller freezes exact current inputs before all native calls. Generating
Python 3.12.14 authenticates W196 full-precision motion and strict endpoint bytes;
native Python 3.11 consumes this frozen binding. Cross-version preview equality
is not relaxed or claimed.

One predeclared panel: zero, +2°, −2° Cartesian-Y initial rotations, unchanged
W196 nonuniform pair weights; five macrocycles, 100-iteration cap, nproc=1 and
seed=1. Individual XYZ selection is exactly A10–A14/B2–B6 (205 atoms). The two
paired flanks and all remaining atoms (654) are fixed; B/Q and the chemical
inventory remain fixed. All cases use the original 7554 F/SIGF/Free tuples,
including 389 Free observations, fixed unit objective weights and no weight sweep.
These are matching noiseless 5W6W synthetic data, not a new experimental dataset.

**Completed external execution:** three actual Phenix **2.2.1-6174 dry-runs** and
three complete five-cycle refinements. 74 cold preflight and 80 cold final checks
pass. Native selected labels, exact source atom bijection, parent-only chemical
interpretation, unchanged child diffraction during that interpretation, complete
bonded/plane/exclusion policies, all 213 requests and original data/Free survive.
126 ordered sugar handedness signs are retained. All 859 atoms and 124 P/OP atoms
remain. Written fixed coordinates are exact; observed native update differences
are floating-point roundoff, at most 2.9e−14 Å. B1 P/OP1/OP2 remains fixed, and no
new incoming symmetry bond or OP3 addition is inferred.

| Quantity | Zero | Positive | Negative |
| --- | ---: | ---: | ---: |
| Interior starting RMS to generator, Å | 0 | 0.14195 | 0.14196 |
| Recovered RMS to generator, Å | 0.01633 | 0.03163 | 0.02929 |
| Recovered RMS to refined zero, Å | 0 | 0.02235 | 0.01960 |
| Boundary-bond starting RMS error, Å | 0.00507 | 0.09329 | 0.10372 |
| Boundary-bond recovered RMS error, Å | 0.00822 | 0.01167 | 0.01071 |
| Largest boundary-bond recovered error, Å | 0.012 | 0.018 | 0.017 |
| Largest local recovered angle error, degrees | 9.55 | 10.15 | 9.69 |
| Final Rfree | 0.00717 | 0.00744 | 0.00726 |

The largest local angle cost is A12 OP2–P–O5′ (8.86° already in the generator).
Largest touching-interior bond errors are 0.099/0.088/0.089 Å; signed cases
retain a B2 O5′–C5′ cost. Local geometry is not wholly repaired just because
boundary bonds and coordinate RMS recover. The zero control exposes inherited
strain and refinement drift. Actual iterations per macrocycle and elapsed times
are recorded in the checkout manifest; completing five cycles is not a claim
of optimizer convergence or chemical acceptance.

Existing W191/W193 readers provide seven paired-P and six simple-step measurements,
with raw coverage retained. Maximum recovered local twist changes from the
generator are zero 0.13029°, positive 0.29424°, negative 0.24332°; maximum P
departures are 0.01334/0.02548/0.02258 Å. These are distinct from the prescribed
Cartesian rotation, helix curvature and local-axis radii. No alignment is fitted.

**Exact local evidence:** NASolve anchor `branch-artifacts/willow/w197-fixed-frame-native/`:
`experiment/plan.json`, `preflight-review.json`, `refine-review.json` and
`local-science.json` are pinned in the machine roadmap. Native code/request/input
snapshots and each stopped process receipt stay in their new experiment folders.
Local runner commands, from NASolve, with the host's generating Python and the
already qualified optional Gemmi directory (the latter is environment provenance):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w197-fixed-frame-native.py plan
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w197-fixed-frame-native.py preflight
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/w193-qualification-c1tf1610/optional-relocated .venv/bin/python -B branch-artifacts/willow/runners/w197-review.py preflight
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w197-fixed-frame-native.py refine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/w193-qualification-c1tf1610/optional-relocated .venv/bin/python -B branch-artifacts/willow/runners/w197-review.py refine
```

These describe completed invocations, not permission to overwrite the experiment.
An initial cold reader expected a dry-run PDB that Phenix does not write; it was
corrected to read the frozen candidate plus exact captured native coordinates.
No native phase was repeated. No full suite or installation repeat: product code,
dependencies and schemas are unchanged. Roadmap `--write`/`--check` pass, and
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_roadmap.py`
passes **8 tests**. W196's source/installed qualification is not relabelled as new W197 validation.

Small local checkout: GitHub anchor
`ScienceCheckouts/Linden/2026-11-21_fixed-frame-recovery/index.html` with one PNG/SVG
figure, provenance and Python opening scripts. Models are linked and hash checked,
not copied. Figure visually inspected; ChimeraX script prepared with shared defaults,
not GUI-executed in this update. Generated science remains uncommitted.

**Next decision:** retain the signed and neutral outcome; qualify the existing
source/motion/policy/execution handoff before another perturbation or weight sweep.
The private native hook is not an installed ordinary workflow. Experimental
diffraction, independent targets, larger deformation, full local geometry and
symmetry covalent seams remain open; S04/S05/S06 stay PARTIAL.


## W198 — Keep native atom order and movement scope together

**Before/after.** W188 could inspect a complete native/source bijection, but a
caller had to reconstruct coordinate and mask assignments separately. The
existing endpoint owner now returns `NativeEndpointMapping` through
`map_native_endpoint`; W188 uses the same factored bijection. An explicit
parent/candidate role and trusted endpoint audit bind the detached immutable
assignment. Source order stays strict; only native interpretation may reorder.
Changed masks, bounds, parent bytes, identities and coordinate roles refuse.
No model is modified, no process launched, no disk/execution schema introduced.

**Real order distinction.** Nine saved stages from W197 (three signed/zero cases,
each with prepared parent, prepared candidate and initial diffraction state)
pass 63 cold checks. Initial diffraction has 20 reordered atoms, all fixed in
this experiment: D1 OP3 moves from raw source index 714 to native index 733.
Prepared `sort_atoms=False` states return to raw order. W197's private
`native_to_input_index` refers to default iotbx parsed input, not raw PDB records;
its actual transfer already matched labels correctly. The initial W198 cold
reader assumed these index bases were equal and refused. Its preserved attempt
was corrected without rerunning native science. A separate constructed test
moves the selection boundary through the reordered atoms to catch assignment of
C5′ instead of O5′; this is not claimed as an observed W197 moving atom.

The cold reader derives initial-stage atom observations from saved diffraction
labels, coordinates, elements and occupancies, joining exact immutable identity
metadata by label. It does not generate a new native capture. OP3→OPX and a
0.001 Å fixed-coordinate change refuse through the existing Cedar reader.
Parent/candidate observations and frozen source inputs remain unchanged.

**Validation.** The new regression fails before the API exists. Source and fresh
relocated wheel each pass **141 focused tests** with the same five-file scope:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_topostitch_endpoint.py tests/test_topostitch_preparation.py \
  tests/test_topostitch_native_window.py tests/test_topostitch_checkpoint.py \
  tests/test_topostitch_execution.py
```

The interpreter path is historical environment provenance, not an artifact
lookup. Installation uses a fresh source copy, offline wheel build and relocated
installation with the original build source/install paths removed. Wheel SHA256:
`9e4104eaba2dcad8b2e39b5402594ab68e5b8fb3c4fe890e22b76b1237ab6f0a`.
The source, relocated Python 3.12.14 and Phenix 2.2.1-6174 Python 3.11 cold reports
are exactly equal for all nine handoffs/63 checks. This invokes the Phenix
interpreter only: **zero native dry-runs or refinements**. W196's whole-preview
cross-Python last-bit replay limitation is not resolved or relaxed.

Local evidence under NASolve anchor `branch-artifacts/willow/w198-native-handoff/`:
`source-final-review.json`, `python311-review.json`, `installed-review.json`,
`installed-check.json`. Checksums are in the roadmap. `attempt01-reader.py` and
`source-review.json` preserve precursor evidence; final claims use the final
reports. The existing runner is `branch-artifacts/willow/runners/w198-native-handoff.py`;
its source invocation from NASolve used the Willow source path in `PYTHONPATH`
and `.venv/bin/python -B`, with the final report as its output argument. The
Phenix interpreter explicitly prepended Willow source and the already pinned
pure-Python dependencies before `runpy.run_path`; the report records owner hashes.
No full suite: this bounded mapping refactor does not alter force/optimizer or
workflow defaults. Roadmap audit and its eight focused tests cover the doc update.

**Compatibility and next gate.** No new dependency, CLI, file format or migration;
existing W188 reports/APIs remain unchanged. Files changed: endpoint/preparation
owners, existing endpoint tests, changelog and current guides/roadmap. Native
ADPs, crystal/scattering, topology, process completion and retained-parent input
lifetime remain independently owned. Alder's retained-reader completion is not
release of the enclosing retained scope; a cold receipt is not a live handle.
Coordinate assignment must be checked against the actual live model at use.
Agree that transition with Cedar before adopting it through the existing
versioned execution policy. No duplicate preview reader or private refinement
repeat is warranted. S04/S05/S06 remain PARTIAL; scientific payload stays local.


## W199 — Use the installed handoff during live preparation

Cedar review confirms that the counted driver entry is later than the relevant
geometry construction. The tested boundary is `finalize_model → manager.process
→ process_pdb_files`, with exactly one parent interpretation. This experiment
uses the installed W198 endpoint owner in that earlier path; it does not repeat
W197 refinements or change the counted/native execution policy.

The explicit positive W197 initializer, original reflections, complete C21
policy and fixed-coordinate selection are copied from their checksummed declared
paths into two fresh cases. The existing frozen execution owner constructs their
requests; only dry-run commands are retained. W198 maps actual live atoms with
the maintained Cedar collector at initial candidate diffraction, interpreted
parent and restored candidate. The returned `candidate_points` supply the one
coordinate transfer. Native geometry/topology, non-coordinate scattering and
candidate diffraction retain their existing independent checks.

**Result:** one completed Phenix **2.2.1-6174 dry-run**, 9.15 seconds; one injected
preparation failure, 4.07 seconds; **zero refinements**. Three live mapping digests
exactly equal the saved W198 positive-stage results. Initial native order moves
20 atoms relative to raw PDB order; interpreted parent/candidate have raw order.
All W197 diffraction snapshots, prepared geometry/model, fixed native inputs and
205-atom movement selection reproduce exactly. This is preparation equivalence,
not additional evidence of bending recovery or scientific acceptance.

Failure is deliberately raised after parent mapping, before candidate restoration.
The initial candidate F-model remains unchanged. All six private Python bindings
and the native runtime bindings restore; the original RuntimeError is preserved
and the child process stops. The partially prepared manager is **discarded with
the failed process**. This does not qualify coordinate rollback, manager reuse,
re-entry, foreign binding replacement or a fresh retry in the same execution.

The first attempt failed on the indirect `openpyxl` import before entering the
native program. It remains at `experiment/`; no scientific result is inferred.
Fresh `attempt02/` explicitly binds the previously qualified pure dependencies.
It does not overwrite/restart the failed attempt. No dependency was added to
NASolve. Installed W198 source files and all input/code hashes are checked.

**71 independent cold checks pass**, including exact prior-state comparison,
input immutability, expected failure, stopped process identity and the existing
execution owner's successful dry-run validation. Commands from the NASolve anchor:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w199-live-preparation.py plan
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w199-live-preparation.py run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w199-review.py
```

These describe completed calls; their destinations are immutable. Local evidence:
`branch-artifacts/willow/w199-live-preparation/review.json`,
`attempt02/experiment/plan.json`, each child's `execution.json` and
`preparation-preflight.json.gz`; exact review/plan pins are in the roadmap.
The first controller is preserved with its failed experiment. No new picture is
needed: the existing W197 fixed-frame recovery checkout shows the actual science.

**Next contract, agreed with Rowan:** maintain an opt-in one-shot preparation
context using bound parent/candidate bytes, admitted W198 mapping and an explicit
qualified native builder. The builder/native owners retain actual interpretation,
chemistry/diffraction checks and the live manager; the outer worker owns input
lifetime, process completion and failed-manager disposal. Keep exactly one
interpretation and transfer, and refuse stale/reused state. Do not attach at the
later counted driver or change historical runtime policies. Separately qualify
that maintained entry on one success/failure before any ordinary integration.
Alder's committed retained-file reader remains the lifetime owner; its pending
storage-budget work is not adopted by this experiment.

Only current guides/changelog/roadmap change in Git. Local workers/receipts and
science remain uncommitted. Eight focused roadmap tests and `--write`/`--check`
pass; no full suite or install repeat for a diagnostic/docs-only update. W198's
installed checks are not relabelled as new W199 tests. S04/S05/S06 remain PARTIAL.


## W200 — Maintain one-shot native parent preparation

**Before/after.** W199's private builder controlled coordinate roles itself.
The new installed `NativeEndpointPreparation` owns the single candidate→parent
interpretation→candidate transition, reusing W198 mappings and an explicitly
qualified builder. It checks the initial candidate again, requires parent
verification before transfer and candidate verification at context close, and
refuses replaced managers, stale native observations and false verifier returns.
Repeated/reentrant operations, swallowed errors and outer exceptions poison the
context. Only successful closure exposes a result; failed managers are discarded.

The builder retains the actual single native interpretation and complete Cedar
chemistry/topology/diffraction proof. The context is not a new native collector,
force owner, file reader, process controller or execution format. Outer worker
owns binding cleanup, input lifetime and process disposal. Source qualification
of executable adapters remains mandatory; no artifact imports arbitrary code.
[API and responsibilities](topostitch-preview.md#prepare-parent-geometry-once-w200).

**Focused regression and installation.** The first real-order test fails before
the module exists. **160 source + 160 fresh relocated installed tests** pass:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_topostitch_endpoint.py tests/test_topostitch_preparation.py \
  tests/test_topostitch_native_window.py tests/test_topostitch_checkpoint.py \
  tests/test_topostitch_execution.py
```

Tests cover changed native order, all failure stages, no transfer after failed
parent verification, wrong model, stale coordinates, false verdicts, missing/
repeated/reentrant calls, swallowed errors, post-verifier drift and closure.
Current source equals installed modules and parses under Python 3.10 syntax.
The fresh build source and original installation path were removed before the
relocated package tests. No dependency, CLI or disk schema changes. Wheel SHA256:
`cec58413983f38bdaaa90ce0c9bce614b30526368d67df2277d83785e060c5c2`.

**Actual installed native experiment:** one completed Phenix **2.2.1-6174 dry-run**
(9.13 s) and one deliberately failed preparation (4.57 s); **zero refinements**.
The existing frozen native execution policy, source snapshots and Cedar reviewers
are unchanged. The maintained context receives exact bound parent bytes via its
builder. Initial candidate/parser order and interpreted parent/prepared order
remain separate. All three mapping digests exactly match W198/W199, and complete
W197 diffraction snapshots, prepared geometry/model, fixed inputs and native
selection reproduce. **81 independent cold checks** pass. No code changes or
additional iterations were needed after this real run.

The deliberate error occurs in parent verification before transfer. Context
reports one interpretation request, zero transfers and FAILED; successful closure
reports one of each and COMPLETE. Original RuntimeError survives. Six outer
Python bindings and native runtime bindings restore, both child processes stop,
and input bytes remain unchanged. This qualifies disposal/cleanup, not model
rollback, same-process retry, arbitrary native versions or broader chemistry.

Exact local evidence under NASolve anchor `branch-artifacts/willow/w200-native-context/`:
`installed-check.json`, `review.json`, `native/experiment/plan.json`, plus each
child's `execution.json` and `preparation-preflight.json.gz`. Roadmap pins those
receipts. Frozen context module hash binds the actual installed implementation
before its Git commit; the matching committed code is the W200 ledger pin.
Local completed commands from NASolve:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B /private/tmp/w200-install.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w200-live-preparation.py plan
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w200-live-preparation.py run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w200-review.py
```

The temporary installer path is historical execution provenance. Scientific
inputs/results are not located by basename; the native controller uses declared
checksummed W197 source paths. Completed destinations refuse overwrite/restart.

**Full-suite attempt, explicitly not a pass.** A repository-wide invocation used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` and the same Python/pytest flags with no
file selection. It was interrupted after the task-specific branch-only scope
was clarified: 446 passed, 15 skipped, 133 subtests and five process-lifecycle
tests failed because the sandbox denied `/bin/ps`; elapsed 73.39 s, exit 2.
`full-suite.log` is retained. A scoped process listing afterward found no remaining
matching pytest/test workers. No unrelated process patch/retry or full-suite
success is claimed. Eight roadmap tests and `--write`/`--check` cover the docs.

**Handoff:** new module plus existing endpoint tests/changelog and current guides;
no native/counted policy edits or schema migration. Ordinary runtime integration
is next and requires separately agreed versioned execution/input ownership with
Cedar. Hazel's qualified Alder `17d52b730a74682ab0f9d5548405681b24d3313e` now offers
ordinary retained-parent closure/settlement, but no combined Willow adoption is
claimed. Input retention, inner reader completion, outer cleanup and physical
reclaim remain distinct. S04/S05/S06 stay PARTIAL. No new physical result or
picture is implied; reuse W197's small recovery checkout. Scientific payload stays
local. The current handoff was consolidated; older exact evidence remains in the
ledgers and Git rather than another diary file.


## W201 — Identify the missing geometry-only parent input role

**Question:** can the current ordinary execution owner carry W200's exact parent
and candidate without confusing source geometry with the diffraction model?
The cold audit uses actual Cedar `refinement_parallelity` readers/writer at clean
commit `ed4fa6d736aada7e2202671854b407622d2e059f`, a frozen W200 v3 request and
its declared checksummed inputs/helper files. Temporary copies are made only
through those references and removed after the audit; original evidence is intact.

| Control | Actual outcome |
| --- | --- |
| Existing ordinary v3 capture | Readable through the current owner |
| Fresh ordinary default request | Same v3 policy and exact frozen helper hashes; command not executed |
| Rehashed extra geometry-parent field | Refused by the historical request reader |
| Proposed new execution policy | Refused by the historical request reader |
| Extra parent input without a native command argument | Refused before runtime-directory allocation |

Thus ordinary v3 cannot currently express a **typed geometry-only parent**.
The extra-input refusal is useful: silently passing the parent as another native
model argument would lose the intended role separation. Code review also notes
that counted original-model provenance is not automatically the current geometry
parent. These five controls do not claim to exercise every historical policy.

The [human contract](topostitch.md#versioned-parent-preparation-execution-contract-w201)
and `native_preparation_execution_contract` in the existing intent JSON propose
named opt-in `topostitch-bound-parent-preparation-v1` under a new versioned policy
of the same owner. Its unfinalized `parent_preparation` field must bind original
parent, exact candidate, motion, current source chemistry/reader intent, original
diffraction/Free, a maintained native builder and actual input lifetime. No new
request reader, execution format, CLI flag, callback loader or policy registration
is implemented. Old readers/defaults remain untouched. Shared changes were sent
to Rowan for owner agreement before editing.

**Validation:** five cold owner controls, unchanged source/owner hashes and removed
temporary fixtures. **Zero native calls/refinements**. Command from NASolve:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w201-execution-contract.py
```

Local report `NASolve:branch-artifacts/willow/w201-execution-contract/review.json`
pins the source request, owner/functions and audit script; its hash is in the
roadmap. Eight roadmap tests and `--write`/`--check` plus intent JSON parsing cover
this docs/design update. No full-suite or installation repeat; W200 remains the
latest qualified implementation. Scientific inputs, generated request controls
and native evidence remain outside Git. Only current intent/guides/changelog and
roadmap change. No schema migration; the new identifiers are explicitly proposed,
not supported. S04/S05/S06 stay PARTIAL. The absence of an expressible role is the
result, not a reason to fabricate current-parent authority or repeat W197.


## W202 — Qualify typed controls and the maintained live collector

**Before/after:** W200's context used a private extraction of Cedar geometry
readers, a separately extracted topology reader and three explicit reader
settings. W202 consumes installed Cedar C507's `collect_live_atoms(model)` and
`collect_live_geometry(model, processed=...)`, plus the existing maintained
`review_native_topology`. The collector checks that the interpreted selection
indices belong to the current hierarchy while allowing coordinates to move.
The old `_NATIVE_WORKER` literal and historical frozen helpers remain unchanged.
This removes the private copies from the new experiment; the live native builder
itself remains source-qualified diagnostic code, not a product dispatcher.

The existing typed source reader reopens the exact W180 artifact. Its model,
C21 PHIL and retained-plane bytes match W200, but provenance/settings differ:
the planes are now a second explicit compiler source, and source
`use_ncs_to_build_restraints=False` differs from W200's effective **True**.
Sorting, CDL and nucleotide CDL remain False. Twelve cold checks record these
differences, reject the old duplicate control declarations and reproduce both
saved topology classifications using the current owner. Earlier W200 evidence
remains valid under its actual settings; it is not retroactively called typed
four-control transport.

A fresh diagnostic freezes the complete typed source, installed Cedar code,
unchanged installed W200 context and original candidate/data/Free scope. The
new parameter file removes the three shadow declarations; a separately bound
control file adds only the explicit `refinement` namespace wrapper. The existing
bounded control reader verifies all four definitions. The actual native builder
checks requested controls, interpreted parameters and retained parameters after
transfer. No global native defaults are edited.

**Actual Phenix 2.2.1-6174 outcomes:** one completed dry-run (9.685 s), one
deliberate failure before coordinate restoration (4.602 s), **zero refinements**.
The independent cold review passes **84 checks**. All three mapping digests
match W200; 205 movable and 654 fixed atoms remain correctly partitioned.
Complete prepared geometry, model, fixed inputs, selected native labels and
candidate diffraction reproduce exactly despite the explicitly changed NCS
setting. Geometry retains 1,011 simple bonds, 1,558 angles and 213 explicit
requests. Both topology classifications preserve 38 declared backbone links and
51 supplied soft distances. Six temporary native bindings are restored on both
paths, both owned children stop, and the original failure is retained. The failed
manager is discarded, with no rollback/retry claim.

The **original literal source capture** has 1,001 simple bonds/1,556 angles;
compilation of its secondary-structure intent into the explicit C21 stack is
a real transformation. Therefore neither matching the compiled stack nor these
live observations constitutes whole original-capture equality or complete
chemical qualification. The collector explicitly returns `complete_capture=False`
and `scientific_acceptance=False`. Ordinary checkpoint/chemical admission,
maintained builder and retained-file lifetime composition remain open.

**Provenance/validation:** Cedar C507 commit
`d09962f378c0aeae7125fa515f08fa66e2269809`; installed native-validation module
SHA-256 `2e8df0a5a3e06e08e45dff701fe41c8a6d463bd2fccbd78d54255223e66644c1`.
Its installed closure is copied and hashed into the local experiment; no host
path is the sole operational reference. W200's installed preparation code is
unchanged. Commands from the NASolve anchor:

```bash
/Users/svecchio/Applications/phenix-2.2.1-6174/bin/phenix.python -B branch-artifacts/willow/runners/w202-source-controls.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w202-live-collector.py plan
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w202-live-collector.py run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w202-review.py
```

The versioned local interpreter path above records the actual invocation, not
a portable launch contract. Plan/source/final reports are under NASolve anchor
`branch-artifacts/willow/w202-typed-native-builder/`; their hashes are in the
roadmap. Scientific payload, native observations and code snapshots stay local.
No Willow runtime code/schema/dependency changes, merge or migration occur.
Eight roadmap tests and generated-document checks cover the docs; no full suite
or redundant installation build. C507's installation is independently qualified
by its owner and exercised here through the exact installed closure. W203 is the
maintained source-qualified builder, before a new public execution policy.
S04/S05/S06 remain PARTIAL. W197 remains the latest physical recovery checkout.


## W204 — Compose the installed Cedar parent service

**Question:** can installed Cedar C509 perform the actual parent interpretation
inside the existing W203 input binding and W200 coordinate-role handoff without
changing candidate diffraction or the retained geometry?

**Result:** one complete Phenix **2.2.1-6174 dry-run** (10.09 s) and one deliberate
post-parent/pre-transfer failure (5.56 s) pass **99 cold checks**. Zero refinement
cycles. The three W200/W202 mapping digests, complete final model/geometry/fixed
inputs, native moving selection and all initial/final diffraction snapshots
reproduce exactly. All 859 atoms remain; 205 movable/654 fixed roles survive.
All four authenticated reader controls stay False. The compiled stack retains
1,011 simple bonds, 1,558 angles and 213 explicit requests. The original literal
capture is a different stage (1,001 bonds/1,556 angles), not silently equated.

The maintained service factory is created before the outer manager hook. Its
single `interpret` call receives the exact pending `finalize_model` kwargs and
W203 immutable inputs. The returned actual `processed` object feeds the existing
live geometry reader; W200 then maps the newly observed order and transfers the
candidate PDB decimals. The private parent-input interpreter is removed from this
new diagnostic. Cedar restores its own server binding before transfer and at exit;
five outer observation bindings also restore. The failure preserves its original
error, transfers no coordinates and discards the manager with its stopped child.

The first attempt omitted a lazy compiler dependency from the frozen closure and
stopped with `ModuleNotFoundError` before any interpretation. It remains under
`experiment/`; the corrected `attempt02/` preserves the already qualified W202
lazy-import closure plus C509. No existing scientific run was overwritten.

**Validation commands**, from the NASolve anchor:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w204-parent-service.py plan attempt02
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w204-parent-service.py run attempt02
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w204-review.py
```

The frozen controller resolves the recorded Phenix installation and runs each
owned child sequentially with one thread and a 180 s timeout. Both stopped.
The installed W203 module is unchanged (`cd5ff34c91410b7d9ba5e72e0cdf859887c2c2f03574d58ddec8f2e35565fbc5`).
Cedar C509 commit is `a78931eb1962e731a7873c5acf49e67b4e241aca`.
Installed C509 parent-service module SHA-256 is
`f967ccc8e4d539dbf2f51b2ac17c6d5bbc68e017f297fb6090cb95ee75eec13f`;
its wheel is `59c01f878a1d420b34f67fcaa4b577259e859adcdc4c2f9152149ee62c17aece`.
Module closures are copied/pinned in the local experiment. Evidence is under
NASolve anchor `branch-artifacts/willow/w204-parent-service/`; review/plan pins
are in the roadmap. These remain local diagnostics, not portable committed runs.

**Limits/next:** C509's receipt and W203 binding explicitly carry no chemical or
ordinary runtime authority. Exact compiled-state reproduction does not reconcile
all original residue definitions or authorize a new refinement. Cedar owns that
remaining source-chemistry gate. W205 joins that evidence before a maintained
receiving builder and ordinary lifetime/execution route. S04/S05/S06 remain
PARTIAL; W197 is still the latest physical recovery. This patch changes human
and machine documentation only, with no runtime/schema/default/migration change.
Eight focused roadmap checks and content/link checks cover the docs; no new
full suite or redundant installation build. Generated coordinates, snapshots,
logs and native receipts are deliberately excluded from Git.


## W205 — Join source chemistry to candidate transfer

**Result:** installed Cedar C510 compares the exact original native observation
during W204's single parent interpretation. All **42 per-site definitions** match,
with **3,451 retained terms across eight restraint families**; compiler-replaced
secondary-structure relationships are accounted for separately. The C510 receipt
is checked before W200 moves candidate coordinates. Complete final geometry,
model/scattering, fixed inputs, selected atoms and every candidate diffraction
snapshot reproduce W204 exactly afterward. The component definitions are observed
during interpretation; they are not reconstructed by a second interpretation after
transfer. No new physical deformation or refined endpoint is claimed.

One Phenix **2.2.1-6174 complete dry-run** took 10.65 s. A second process received
a deliberately changed source byte string and refused in 4.59 s **before native
interpretation or coordinate transfer**. W200 exposes no completed result; candidate
atoms and diffraction remain unchanged, the manager is discarded, and the original
ValueError is preserved. The thread profiler point, Cedar server binding and five
outer hooks restore; both owned children stop. **72 cold checks pass; one actual
interpretation, zero refinements.** Rowan's altered-Td chemistry tests are not
repeated: this receiving check tests the source-byte/transfer integration boundary.

`source_native_json` is the exact original `native/native_validation.json` byte
string from the typed compiler report, SHA-256
`278da35a6cda125558d091c30f02d60e8c78aabb0be0d35f81935937b0d97fca`.
C510's live site-definition digest is
`6e55b86eacc18438e11ce22be965f91225a509b9772fd5af27f11a3e9d6bdf1a`.
The comparison preserves its limitation: **all 42 sites lack full formal-charge
readback**. Matching available definitions/proxies to the source is not independent
chemical correctness or an accepted structural solution. Both the service's
chemical/ordinary authority flags and scientific acceptance remain False.

**Commands**, from NASolve:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w205-source-chemistry.py plan experiment
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w205-source-chemistry.py run experiment
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w205-review.py
```

Each owned process is single-threaded with the existing 180 s cap. Installed
C510 commit is `6842107c122ce15e5042e92687730c7b23c04020`;
wheel SHA-256 is `4441fac28b9a0006f1484d683bbb6da11eeb9300de8cb77376c87a25cac29084`;
service module `9a39ac073e58549573d0e49a1643efceed1139051a3ea3596f1f14c3ce4e8195`;
chemistry module `9ff7d08d0482d067237c7813bf9b5ea06bc4d50cba7de3b47bc591649f97e545`.
The C507 collector and W203/W200 Willow code remain unchanged. Local evidence
under NASolve anchor `branch-artifacts/willow/w205-source-chemistry-transfer/`
contains frozen module/input closures and all observations; the roadmap pins
review and plan. No scientific data or local state is committed.

This Willow patch updates current human/machine docs only. Eight roadmap tests,
JSON/link checks and exact receipt pins validate the documentation; no full suite
or redundant installation build. No runtime schema/default/dependency/migration
change. **W206** audits the existing versioned execution and outer lifetime route
with Rowan before maintaining the receiving bridge. S04/S05/S06 remain PARTIAL.


## W209–W210 — Local torsional alternatives after backbone recovery

W207's low synthetic R factors concealed A11/A14 phosphate-angle defects.
W209 reconstructed its exact full-precision endpoint against the original
source-bound native geometry. The two O5′/C5′ straight return paths initially
increase chemical energy; their sampled midpoints cost about 1,497 and 697 raw
units above the endpoint. This is a path-specific penalty, not proof of an
unavoidable energy barrier. Two congruent P–O5′–C5′–C4′ configurations give a
useful discrete alternative while keeping P/C4 fixed, all three chain lengths
and both internal angles. A truth-assisted axial fit puts A11 at 108.33° and A14
at 94.79° versus 108° target; only the former is close. This diagnosis uses the
known synthetic generator and is **not** a production selector.

One clean Phenix 2.2.1-6174 dry-run / 31 read-only energy evaluations reproduces
W207's raw energy exactly and its gradient within 4.6e-13, with zero coordinate
writes or diffraction changes. 38 cold checks pass. Both shoulder derivatives
agree with central differences; the all 205-atom direction differs by 2.697 raw
units (about0.25%) at steps 1e-4, 1e-5, 1e-6. That discrepancy remains explicit;
no force/normalization tolerance or optimizer was changed. Earlier source-path
and final-restoration failures remain frozen, stopped and excluded from the
clean-closure claim. The successful evaluator passes points directly to native
geometry rather than moving the live model.

W210 freezes 48 intrinsic states before scoring: original and reflected local
chain configurations at twelve 30° axial rotations per site. **No generating
coordinates, Free amplitudes or saved maps enter generation/ranking.** All 48
preserve the three local/boundary lengths and 126 sugar handedness signs. The
same direct nonanomalous `n_gaussian`, no-solvent convention as the synthetic
generator is used on 7,165 original work reflections; 389 Free amplitudes are
excluded. One work-only least-squares amplitude scale 1.0000227985 is frozen
across candidates. This is an atomic work-residual diagnostic, not Phenix
Rwork, likelihood or a calibrated experimental score. C517's direct-scattering
method is reused with four independent whole-model additivity controls.

| Site / retained alternative | Chemical-energy change | Fixed-scale work squared residual | OP2–P–O5′ |
| --- | ---: | ---: | ---: |
| Original, either site |0|8.84111e-6|A11 77.43°; A14 78.81°|
| A11 alternate +60° |−133.49|8.81805e-6|105.70°|
| A14 alternate +90° |−167.99|9.07464e-6|95.79°|

A11 has one non-dominated state in the frozen grid. A14 retains both original
and alternate: chemistry improves while the declared squared work residual
worsens. Its absolute amplitude residual improves slightly, demonstrating why
we keep the predeclared primary score rather than choosing a favorable statistic.
Differences are small; no significance or automatic adoption follows. The A14
O5′–C5′ bond remains short because congruent alternatives preserve input lengths.
One completed dry-run / 50 geometry and 55 direct scattering calls, 26 cold checks;
an earlier Miller-index adapter import failure is preserved. Zero refinements.

**Prespecified controlled experiment W211 (completed below):** matched unchanged endpoint versus A11-only
+60° seed, each one five-cycle/100-cap XYZ fit. Retain original 205 movable/654
fixed atoms, all 7,554 / 389 observations/Free, B/Q, source targets and identical
native weighting/scaling recipes. A14 is unchanged at entry, still movable.
Measure both sites, local/boundary links and final original-data statistics;
no additional restart or weight sweep. This is separately authorized by Rowan,
not an ordinary workflow activation.

Local frozen evidence: `branch-artifacts/willow/w209-backbone-energy-profile/`
and `w210-intrinsic-shoulder-candidates/`. Their anchored hashes are in the
roadmap; inputs/results stay untracked. Exact cold commands from the NASolve
checkout (with its interpreter) are:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w209-review.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w210-review.py
```

These writers refuse existing outputs. Native controllers and commands are
frozen alongside each attempt. No runtime/schema/default/dependency change,
new install claim, full-suite run or migration; previous W208 installation
qualification remains its own evidence. General local reconstruction,
experimental support, modified chemistry, symmetry seams and ordinary request
integration remain open; S04/S05/S06 stay PARTIAL.


## W211–W212 — Local corrections survive matched refinement

**Question:** can discrete local configurations escape the defects that remain
after W207's large perturbation recovers, without changing chemical targets or
using the generating answer to choose candidates? W211 compares unchanged and
A11-only seeds; W212 adds A14-only and both-site seeds, reusing the two immutable
W211 controls. The two candidates are exactly the retained W210 alternatives.
No additional grid, re-ranking by Free, weight changes or restarts follow.

All four arms use the same source-qualified worker, original data/Free flags,
205 movable and 654 fixed atoms, fixed B/occupancy, five macrocycles, 100-iteration
cap, seed 1 and one CPU. Native unit coordinate/geometry weights and scaling
recipe are identical. Only the declared two or four O5′/C5′ input coordinates
differ. Cross-arm checks compare complete commands, input hashes, frozen helper
hashes and all native covalent target identities. Endpoint writes are independently
checked against full-precision native observations within PDB precision.

| Five-cycle arm | A11 OP2–P–O5′ | A14 OP2–P–O5′ | A11 / A14 O5′–C5′ (Å) | Rwork / Rfree |
| --- | ---: | ---: | --- | --- |
| Unchanged |76.83°|81.39°|1.369 / 1.275|0.007975 / 0.008418|
| A11 seed only |108.11°|80.72°|1.405 / 1.270|0.007790 / 0.008135|
| A14 seed only |76.94°|102.76°|1.361 / 1.447|0.007299 / 0.007561|
| Both seeds |107.96°|103.06°|1.398 / 1.455|0.007216 / 0.007301|

Native targets are 108° and 1.418 Å (bond sigma 0.025 Å). **Each local seed
repairs its own shoulder, and both survive together.** A14's starting work-only
squared residual was worse; the final native recovery is better. This supports
allowing a bounded recovery before rejecting a promising deformation. It does
not turn the direct-amplitude score into a likelihood, or establish an Rfree
selection rule. All four predeclared results are retained, including imperfect
A14 geometry. Generating coordinates are used only for post-run diagnostics:
selected RMS falls from 0.1177 Å in the unchanged arm to 0.0290 Å with both seeds;
maximum residual falls from 0.8900 Å to 0.1211 Å.

All 859 atoms, 38 links, 213 explicit geometry terms, 126 sugar-handedness signs,
7,554 observations and 389 Free reflections remain. Source definitions, native
geometry policy and fixed surroundings are unchanged. The four movable/fixed
boundary bonds improve from RMS 0.0133 Å to 0.00925 Å; their 16 angles improve
from RMS 2.808° to 2.267°. Across all 960 covalent bonds and 1,474 angles, RMS
changes from 0.01965 Å / 2.378° to 0.01819 Å / 1.693°. There remain 27 bonds and
33 angles beyond four native sigmas in the combined model, including inherited
fixed-region geometry (25 bond and 30 angle outliers are wholly fixed); **this is not complete stereochemical acceptance**.
Torsions, full chirality/clash validation, experimental data and symmetry seams
are not certified by these local measurements.

A final cold readback includes **all four P-centered bonds and all six angles**
at each shoulder, not only the tracked OP2–P–O5′ angle. Unchanged-control maximum
bond/angle deviations are 3.05/10.39 sigma at A11 and 7.55/8.87 at A14. With both
seeds they are 1.60/1.70 and 1.25/1.887: every local phosphate bond/angle is within
two native sigmas. Targets and term identities match exactly. This readback
uses the saved native `.geo` precision, no new native call, and does not extend
the global acceptance claim. The pinned supplemental receipt is
`w212-factorial-shoulder-recovery/phosphate-readback.json`; command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w212-phosphate-readback.py
```

**Validation:** Phenix 2.2.1-6174, four completed zero-cycle preflights and four
completed five-cycle refinements, all processes stopped. W211 and W212 each
pass 38 preflight and 40 recovery checks; the cross-arm closure passes 28.
No full-suite run, new package installation or product code change. The local
cold-review commands are:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w211-review.py preflight
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w211-review.py refine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w212-review.py preflight
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w212-review.py refine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B branch-artifacts/willow/runners/w212-factorial-review.py
```

They refuse existing outputs; frozen plans/controllers retain exact native
commands. Local evidence stays under `w211-matched-shoulder-recovery/` and
`w212-factorial-shoulder-recovery/`; roadmap receipts bind the results. No new
maintained local-proposal API is added: the current registered motion is a
whole-pair taper, and these two-atom discrete states have no maintained consumer.
The queued seam must preserve exact atom identities, two fixed endpoints,
existing masks/admission and complete native source chemistry. It must not
quietly reinterpret an existing preview schema. S04/S05/S06 remain PARTIAL.

## W213 — Trace the ordinary receiving boundary without invented ancestry

The retained W208 canonical parent does genuinely match W207's registered bend
preview and W206's detached typed source. Current maintained readers replay the
exact 205-atom motion/candidate and rebind the same parent, compiler report,
original native observation, ordered restraint/control PHIL bytes and four
False controls. This is an 18-check cold trace, with zero native calls or source
changes. No new generic helper is needed to connect those existing pieces.

However, the registration is a **construct-identity registration**, not a saved
campaign checkpoint. Its W196 ancestor explicitly declares a fresh diagnostic
and denies ordinary checkpoint admission. The actual W208 execution names
`private-W208-maintained-builder`; its run anchor contains neither `report.json`
nor `AutoRefine/checkpoints.json`. The actual W173 loader refuses at the missing
run report, before W174 can bind a current parent. No registry, checkpoint or
historical authority is minted to bridge this gap. W174's synthetic fixture has
a different parent hash; C412's real request membership evidence did not admit
a registered motion. Neither supplies the missing identity.

The current Cedar `read_execution_request`, `prepare_execution` and
`_expected_code` function sources are byte-identical to the W201 audit. Therefore
its five refusal/default controls remain applicable without repeating them:
ordinary v3 has no typed geometry-only parent role. C516's qualified entry still
requires trusted `observe_candidate` and `prepare_parent` providers; it is not
an ordinary request consumer by itself. The exact owner hashes and retained
C516 receipt are bound in the local trace.

**Next gate, agreed with Rowan:** obtain a genuinely registered current-parent
checkpoint with exact original data and source roles, then join W174/W206/W208
through Cedar's opt-in versioned parent-preparation request and qualified native
callback/lifetime consumer. Do not manufacture ancestry from an unrelated test
fixture, repeat the already-qualified native entry panel, or patch the ordinary
writer from Willow. Existing v3/v9 bytes/defaults remain unchanged.

```bash
# From the Willow source checkout, using the NASolve environment:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /path/to/NASolve/.venv/bin/python -B /path/to/NASolve/branch-artifacts/willow/runners/w213-ordinary-binding-trace.py
```

The final trace is `NASolve:branch-artifacts/willow/w213-ordinary-binding-trace/review.json`.
An initial diagnostic assertion expected a registry-related error; the actual
owner first requires the run report. The corrected assertion records that exact
missing-report refusal. No scientific state was written. Local artifacts remain
untracked; documentation, intent and roadmap only are committed. No schema,
compatibility, dependency or migration change. Next evidence must close a real
receiving gap, not repeat a missing-identity demonstration.

Current documentation validation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
/path/to/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider
tests/test_topostitch_roadmap.py` passes **8 tests**.
`python3 scripts/audit_topostitch_roadmap.py --write` and `--check` pass for
16 jobs; `git diff --check` is clean. The local W212 science checkout contains
three checksum-verified PDBs, a visually inspected four-arm plot and an openable
comparison script. ChimeraX **1.12** headless validation opens all three
859-atom models and all five view actions; no GUI-render claim is made. The
first harness read hit ChimeraX's ASCII locale after opening the models; its
UTF-8 read was made explicit and the complete check passed. The viewer uses
gray background, soft lighting, silhouettes and thin nucleic rings.


## W214/W215 — Real checkpoint and dictionary-only parent binding

W214 reopens the retained W187 root-only replay of the real X11_22 PostMR model.
The original run report and registry match the frozen inventory. Original
selection remains refine-001; the isolated root replay selects postmr. This is
not portability of the complete historical refinement tree. The parent has
2603 atoms/128 canonical residues, exact original atom/occupancy/B bytes, and
original observations. Eighteen cold checks bind that ancestry and unchanged
source. There is no prospective child or registered motion; the private W208
859-atom parent is unrelated.

The frozen configuration contains only nonstandard mode, an explicit model and
empty OP3 sites. Saved sequences/mutations are empty, standard_pair is null and
there is no sequence file. PostMR records 55 NARestraints-guessed pairs but no
restraint file. Those coordinate-derived guesses are not independent design
intent. The earlier E9–E13 inspection window likewise grants no pairing/motion
permission. This absence is recorded once, scoped to these exact saved records;
no claim is made about all external design documents or other parents.

The existing literal compiler correctly refused controls-only inputs. Cedar
C526 and Willow W215 now support an explicit separate dictionary-parent policy,
with no fake pair or dummy restraint. One new completed Phenix 2.2.1-6174 native
interpretation captured the same 2603 atoms with all four reader controls False.
It made no coordinate changes, refinement or checkpoint writes. Cedar's one
shared typed artifact binds that original observation; Willow source/installed
readback passes 19 checks, including old-path-gone relocation and altered-control
refusal. Phenix Python 3.11 agrees after verified dependency bootstrap.
[API, exact test command and compatibility](topostitch-preview.md#bind-a-dictionary-only-native-parent-w215).

W215 has 225 focused source and 225 relocated installed passes. The user's
supplied contract also requested a complete suite: one run completed with
1947 passed, 131 skipped, 51 failures and 234 passing subtests. The failures show
missing optional Gemmi or sandbox-denied process inspection/cleanup. This is not
a clean full-suite claim. A first failed-node replay parsed parameter IDs with
spaces incorrectly and collected no tests; the corrected focused environment
replay passes all **51 tests** in 4.70 seconds with Gemmi 0.7.5 and permission
for the tests’ own process inspection/cleanup. No product change was needed.
This does not rerun the 131 skipped cases or replace an integration full-suite gate.

Local receipts remain under `NASolve:branch-artifacts/willow/w214-canonical-parent-binding/`
and `NASolve:branch-artifacts/willow/w215-dictionary-parent-binding/`, with exact
pins in the roadmap. Raw science and temporary build trees are excluded from
Git. Source policy is opt-in; old callers, CLI, result shape and dependency
requirements retain their meanings. No migration, ordinary dispatch, invented
motion or scientific acceptance follows. Next: finish Cedar's receiving scope
and independently maintain the queued intrinsic local proposal consumer.


## W217 — Recover installed local proposals after PDB rounding

One new matched receiving check uses installed W216 to generate the declared
A11 reflection/+60° and A14 reflection/+90° proposals from the saved W211
starting PDB. It changes four permitted local atoms before serialization;
three serialized atoms differ from the older W212 combined initializer by at
most 0.002237 Å. No candidate grid, Free-R scoring or map selection is repeated.
The existing W212 worker, native recipe and earlier unchanged/combined controls
are reused with their exact input and code pins.

Phenix **2.2.1-6174** completed one zero-cycle preflight and one five-cycle
XYZ recovery (68.04 seconds, one CPU, 100-iteration cap per minimizer). Both
owned processes stopped. The fixed original 205/654 mask, 859 atoms/B/Q,
38 backbone links, 213 explicit geometry terms, 126 sugar-volume signs and all
7554 observations/389 original Free flags survive. Source interpretation and
candidate transfer happen once per phase; native geometry definitions,
exclusions and initial candidate diffraction are retained. The preflight has
24 cold checks and recovery has 25; no second fit or parameter search.

| Final result | Unchanged recovery W211 | Private combined seeds W212 | Maintained seeds W217 |
| --- | ---: | ---: | ---: |
| A11 OP2–P–O5′ angle | 76.83° | 107.96° | 108.10° |
| A14 OP2–P–O5′ angle | 81.39° | 103.06° | 102.87° |
| A11 O5′–C5′ bond | 1.369 Å | 1.398 Å | 1.400 Å |
| A14 O5′–C5′ bond | 1.275 Å | 1.455 Å | 1.454 Å |
| Maximum residual to synthetic generator | 0.890 Å | 0.121 Å | 0.118 Å |

The maintained result is within 0.01361 Å maximum coordinate difference of the
private combined result. Its Rwork/Rfree are 0.007198/0.007267 on the same
synthetic data. Small statistical differences do not establish superiority.
The complete local readback checks all four P-centered bonds and six angles at
each repaired site: largest absolute native Z is 1.77, with the original
restraint targets retained. Residual A14 and inherited whole-model defects
remain; this is not general/experimental acceptance or an ordinary workflow.
The bounded question closes: the maintained seed survives saved-PDB rounding
and reaches the prior local recovery behavior.

Exact local commands (NASolve environment, `-B`):

```bash
python -B branch-artifacts/willow/runners/w217-maintained-recovery.py plan
python -B branch-artifacts/willow/runners/w217-maintained-recovery.py preflight
python -B branch-artifacts/willow/runners/w217-review.py preflight
python -B branch-artifacts/willow/runners/w217-maintained-recovery.py refine
python -B branch-artifacts/willow/runners/w217-review.py refine
python -B branch-artifacts/willow/runners/w217-phosphate-readback.py
```

The controller refuses an existing output and binds all native commands before
execution. Receipts stay under `NASolve:branch-artifacts/willow/w217-maintained-shoulder-recovery/`.
This is evidence/documentation after the installed W216 patch, not another code,
CLI, schema or dependency change. Raw science is excluded from Git. Next work
qualifies explicit displacement measurements before the separately requested
centroid/centerline stress tests; neither target is claimed by these results.


## W219 — A true 10 Å centroid stress case fails bounded recovery

The investigator's larger-displacement target is now tested once with a precise
metric. The existing registered five-pair window, two fixed flanks and taper
are retained. Zero rotation and a declared +x translation scaled by the mean
taper weight give **10.000 Å centroid displacement** of the same 205 atoms.
This is neither a helix-centerline radius nor valid starting DNA geometry.
Starting atomic RMS is 11.123 Å and maximum atom displacement 17.857 Å. Twelve
original chain connections are audited before native execution; the longest
O3′–P distance is 10.285 Å, with four fixed-flank crossings at
5.022/10.285/7.585/3.340 Å. Loose initialization limits were frozen beforehand
(20 Å atom motion, 12 Å bond-length change, 180° angle/torsion change); they
confer no geometry acceptance.

Phenix **2.2.1-6174** completed one zero-cycle preflight (23 cold checks) and
one five-cycle, one-CPU recovery under the existing W212/W217 native policy.
There was no amplitude sweep, retry or expanded window. Original atoms/B/Q,
source chemistry, 205/654 mask, 38 links, 213 explicit terms and 7554/389
observations/Free flags remain. Native preparation is finite and the actual
owned processes stop; that does not imply recovery succeeded.

**The result is rejected.** The original cold reviewer refuses the final
sugar-handedness condition. A separate negative readback retains 24 input and
chemistry/data-retention checks and records the physical failures:

- A11 DT C1′ changes ordered sugar volume from **+2.33475 to −2.14440 Å³**.
- The four boundary distances shrink to **1.746/1.834/1.700/1.589 Å**, but the
  worst original chain-link bond and associated angle remain **18.92σ/32.19σ**.
- Rwork/Rfree change **0.3993/0.4994 → 0.3670/0.4148**. Poor initial statistics
  were allowed a recovery window; the final structure still fails.
- Final selected-region centroid displacement is **7.776 Å**, RMS **9.756 Å**,
  and maximum atom displacement **18.486 Å** from the original model.

Shortened distances and some statistical improvement therefore do not establish
junction closure or correct placement. The original failed review and its source
hash are preserved separately from the negative readback. No further fit runs
under this declaration. The next question is whether the existing collective
whole-residue motion can preserve sugar shape and improve junction geometry
before independent Cartesian refinement; first inspect native geometry only.
W85's small-motion derivatives and W209's unresolved full-direction discrepancy
remain distinct evidence, not permission for a new optimizer.

Local commands use the NASolve environment with `-B`:
`runners/w219-centroid-stress.py plan`, then `preflight`,
`runners/w219-review.py preflight`, then the controller's `refine`.
`runners/w219-review.py refine` refuses as described;
`runners/w219-negative-readback.py` and `runners/w219-metric-readback.py`
record the retained failure. All paths are beneath
`NASolve:branch-artifacts/willow/`; pinned outputs are in `w219-centroid-stress/`.
This is science/documentation only; no runtime/schema/default/dependency change,
migration, ordinary activation or raw-data publication. The 5 Å centerline test
remains unrun, and S04/S05/S06 remain PARTIAL.


## W220–W221 — Whole-residue path and the existing corrected force owner

W219's inverted sugar motivates a constrained-motion check before another
Cartesian recovery. W220 reuses the unchanged six-parameter `TaperedMotion`,
original source chemistry, 205 movable/654 fixed atoms, and exact crystal frame.
One Phenix **2.2.1-6174 zero-cycle preparation** makes 55 read-only geometry
calls: five fixed path fractions, two endpoint derivative panels at steps
1e-4/1e-5 in degrees or Å, and restored rounded-start observations. No refinement,
optimizer, candidate coordinate write or diffraction ranking is performed.
The observed model, complete source chemistry, original data/Free, native hooks
and rounded-start energy/gradient restore unchanged; 28 cold integrity checks pass.

All 126 sugar handedness signs survive the five poses. Raw geometric energy
falls from 2,377,991 to 12,518 along the known-source return path; maximum
chain-link distance falls from 10.285 to 1.620 Å. This is a descriptive path,
not a discovered repair or proof of a continuous low-energy route. The large
translation stretches connections between whole residues despite preserving
individual sugar shape. The source itself retains nonzero geometric strain.

**The raw derivative panel fails all 24 comparisons.** Signed discrepancies
are nearly identical at source and displaced endpoints. Before adding another
force owner, W221 checks the existing Cedar correction. The observation is made
*after* `run_compatible_refinement` restores the original native parallelity
function; actual refinement uses `ParallelityKernel` while its context is active.
The maintained `NativeMaskedObjective.evaluate_motion` likewise consumes the
existing corrected evaluator. A raw post-program gradient is not that force.

W221 reconstructs the exact saved native plane proxies and atom order at both
endpoints, applies the existing `native-parallelity-both-first-planes-v1`
correction, and projects corrected-minus-native forces through the unchanged
motion. **All 24 comparisons then pass the original tolerances**, with maximum
absolute error 0.000851 (mixed physical units; individual tolerances are retained).
Native residuals are unchanged. There are zero new native preparations, full
geometry calls, refinements or model writes. This explains W220's discrepancy;
it does not retrospectively change W209's raw receipt or qualify every direction.
No Cedar defect, new force implementation or tolerance adjustment is claimed.

Commands from the NASolve root (all scripts under `branch-artifacts/willow/runners/`):

```text
.venv/bin/python -B branch-artifacts/willow/runners/w220-collective-geometry.py plan
.venv/bin/python -B branch-artifacts/willow/runners/w220-collective-geometry.py run
.venv/bin/python -B branch-artifacts/willow/runners/w220-review.py
.venv/bin/python -B branch-artifacts/willow/runners/w221-plane-force-readback.py plan
<Phenix 2.2.1-6174>/bin/phenix.python -B branch-artifacts/willow/runners/w221-plane-force-readback.py readback
```

The first W220 planning import exposed that the frozen endpoint-only package
has no preview loader; planning stopped before any native execution. The repair
uses the hash-verified W218 installed preview owner, as W219 did, and preserves
that planning note. Frozen native transport bytes remain unchanged.
Local receipts are in `NASolve:branch-artifacts/willow/w220-collective-geometry/`
and `w221-plane-force-readback/`, with anchors/checksums in the roadmap.
Next qualify the live corrected collective callback before any optimizer or
new recovery. The existing Cartesian trial API remains 3N; do not relabel it
as a six-parameter optimizer. Source-informed return paths are diagnostics,
not data-selected solutions. S04/S05/S06 remain PARTIAL. Evidence/docs only;
no runtime/schema/default/dependency change, migration or scientific upload.


## W222–W225 — Corrected collective warm-start and matched receiving refinement

**W222 live force boundary:** one zero-cycle Phenix 2.2.1-6174 preparation,
55 read-only geometry evaluations, 31 cold integrity checks. All 24 projected
endpoint derivative comparisons pass a strict absolute 0.001 bound; energies
match W220 exactly and corrected projections agree with W221. The existing
Cedar correction is applied to actual live proxies before `TaperedMotion.pullback`.
No new force implementation, `NativeMaskedObjective` constructor bypass, ordinary
execution or relabeling of the maintained 3N Cartesian trial API is involved.

**W223 geometry-only warm-start:** one predeclared six-parameter scitbx L-BFGS
run begins at the exact W219 10 Å centroid perturbation. Source chemistry,
205/654 mask, 20 Å atom bound and fixed pair weights remain. Rotation variables
are degrees and translations Å, without hidden rescaling. The run stops at its
**20-iteration cap, not convergence**, using 24 optimizer calls and 78 total
geometry evaluations (including both 26-call derivative audits and restored
baseline). All 24 derivative comparisons pass; 20 cold checks replay unchanged.
Raw geometry cost falls 2,377,991 → 12,511. All 126 sugar signs and every internal
distance in the seven full pairs survive. The four flank links become
1.606–1.617 Å; worst original chain bond/angle is 1.75σ/3.15σ. The centroid/RMS/max
return to 0.00626/0.01873/0.04683 Å from source. This undoes a large distortion;
it is not a retained alternative 1 nm shape. Whole-model strain remains:
31 bonds/38 angles exceed 4σ, with 6/8 touching movable atoms.

**W224 receiving test:** separately frozen, exactly one preflight and one
five-cycle/100-cap XYZ refinement receives the W223 PDB. Eleven independent
retention checks confirm the same native worker, source chemistry, original
7554 observations/389 Free flags, 205/654 mask, original B/Q and command after
declared run rebasing; among the seven native inputs only the candidate changes.
There is an additional geometry warm-start stage, so total computation differs
from W219 even though the downstream diffraction refinement is matched. The
initializer and recovery use the same frozen six-parameter motion family; this
is a controlled same-family test, not independent deformation generalization.

| Final written result | Direct W219 recovery | W223 → W224 staged recovery |
| --- | ---: | ---: |
| Sugar signs retained |125/126|126/126|
| Four flank O3′–P lengths, Å |1.746/1.834/1.700/1.589|1.612/1.621/1.608/1.618|
| Worst original chain bond/angle, σ |18.92/32.19|2.75/2.59|
| Rwork/Rfree |0.3670/0.4148|0.007123/0.007274|
| Region centroid / atom RMS / maximum, Å |7.776/9.756/18.486|0.00266/0.02072/0.05907|

W224 passes 24 preflight and 25 final checks. Both repaired P centers have all
four bonds/six angles within 2σ (maxima 1.71 and 1.91σ). **This is bounded
synthetic staged recovery, not experimental or symmetry-stitch acceptance.**
There are still 26 bonds and 32 angles above 4σ overall. Three touch the moving
region: A11 base C4–O4 bond changes from −4.14σ in the source to −4.89σ;
A11 O4′–C1′–N1 improves −9.16σ → −5.69σ; A12 C5′–C4′–O4′ worsens
−2.37σ → −4.40σ. Thus not every residual is inherited unchanged, and tiny R
factors do not override chemical review. The failed direct endpoint remains.

**W225 fixed-flank planning bound:** the seven explicitly defined present-atom
pair centers have source path length 21.057 Å and anchor separation 20.530 Å.
The requested +10 Å selected-region centroid requires **at least 29.011 Å** of
path (+37.77%); the actual initializer uses 40.421 Å. For a path of length L
between A/B, every path point p obeys |p−A|+|p−B|≤L; convexity extends this to
its positive weighted centroid. Five mathematical/control checks verify the
calculation and the atom-count weighting reproduces the 205-atom centroid.
This is a necessary bound on those measured centers, **not a helix-axis/rise,
stacking, elasticity or universal DNA length limit**. It explains why retaining
all center-step lengths cannot realize this target in this fixed window. Check
window feasibility and explicit expansion toward protected junctions before
forcing another large move; no amplitude/window search or native calculation ran.

Local evidence roots under `NASolve:branch-artifacts/willow/` are
`w222-live-collective-forces/`, `w223-collective-warmstart/`,
`w224-collective-seed-recovery/`, and `w225-centroid-feasibility/`.
Controllers/readers under `runners/` are `w222-live-collective-forces.py`
(`plan`, `run`), `w222-review.py`, `w223-collective-warmstart.py` (`plan`, `run`),
`w223-review.py`, `w224-collective-recovery.py` (`plan`, `preflight`, `refine`),
`w224-review.py` (`preflight`, `refine`), `w224-retention.py`, and
`w225-centroid-feasibility.py`; use the NASolve Python with `-B`. Native workers
use the exact declared Phenix installation. Cold reviewer corrections (sample
count, terminal metric print, and proposal-role naming) are retained separately;
none required a native rerun or changed scientific outputs. W223's original
saved review and reader remain hash-bound and its corrected cold replay matches.

No product runtime/schema/default/dependency change or migration in these steps;
scientific artifacts stay local. S04/S05/S06 remain PARTIAL. Do not repeat the
closed trajectory to tune a result. Next: specify the maintained six-parameter
trial's source/units/budget/stopping/rounding contract using existing owners;
then qualify feasible windows and general data-supported deformation/stacking,
including independent forward/reverse cases and eventual periodic closure.


## W228 — Review the shared registered phosphate reader

Cedar **C539**, commit `7bc491ac13e255c724073136c1ca1e85c19f8266`, now lets its
existing phosphate-image reader consume the shared registered periodic graph
for one named continuation. Willow independently reviewed the source and
replayed the exact retained inputs: **20 canonical-frame checks and 16 original
numbered-checkpoint checks pass**, with no new native calculation, coordinate
write, registration change or refinement. This is Cedar's source-frame reader,
not a Willow implementation or a merge of the branches.

The declaration fixes B7 O3′ and applies `-y,x-y,z` to B1 P. Doctor instead fixes
P and applies the inverse `-x+y,-x,z` to O3′ and C3′. Direct fractional-coordinate
readback independently gives **2.794915 Å** in the shipped C_G model, versus
**21.894628 Å** in the untransformed ASU. The seven-site registered strand keeps
its periodic cycle and 716 unrepresented context atoms. Logical-to-coordinate
mapping, the exact three input-file hashes and unresolved endpoints remain
explicit; proximity does not replace a declared operator.

The separate original no-metal PDU `run_002/refine-005` source gives
**2.824291 Å** from its coordinates. Its own Phenix 2.2.1-6174 GEO records a
**2.825 Å nonbonded contact**, no matching bond and no matching angle entries.
P/OP1/OP2 are present and OP3 absent. The registered claim and existing native
reference groups reproduce exactly; the registry/model/GEO/declaration/native
receipt hashes and timestamps stay unchanged. Thus a confirmed chemical intent
and retained phosphate atoms do **not** imply that this historical refinement
restrained the intended symmetry bond. The later matched image-force fit is a
separate Cedar result, not this original checkpoint.

C539 retains `runtime_authority=false` and `scientific_approval=NOT_ASSESSED`.
Willow's relabel/physical-boundary packet, numerical forces and native lifecycle
are unchanged. This does not qualify a proposed recut frame, seam chemistry,
all junctions or automatic adoption. The original source registration is not
silently rebound to a different checkpoint. The existing W196/W219 interior
window fixes both B7 and B1 in its flanks; it therefore cannot place this seam.
A separate permitted terminal/coupled window is required, with explicit partner
and protected-junction context. The graph declaration does not release anchors.

The read-only controllers are
`NASolve:branch-artifacts/willow/runners/w228-c539-review.py` and
`w228-checkpoint-review.py`, run with the NASolve Python using
`PYTHONDONTWRITEBYTECODE=1`, optional Gemmi 0.7.5 and `-B`. Their immutable
`canonical-review.json` and `checkpoint-review.json` receipts live under
`NASolve:branch-artifacts/willow/w228-registered-phosphate-review/` and pin the
exact Cedar owners and input artifacts. Generated scientific inputs stay local.
No source tests, installation or native run were repeated for this independent
cold review; C539's own focused/relocated qualification remains Cedar-owned.


## W229 — The current interior window cannot simply grow

Before a wider-window control, the installed W227 package replayed W196/W207's
frozen registration/discovery and original selector. **13 cold checks pass**,
including three refused changes that would silently release a flank or remove
both anchors. There were no candidate coordinates, model writes, native calls
or fits. All input hashes/timestamps stayed unchanged.

The same 205-atom core occupies five movable pairs within A9/B7 through A15/B1.
Both declared routes contain seven sites, and the actual source B chain contains
B1–B7. Enumerating every contiguous declared interval shows that the existing
seven-pair interval is the only one containing this core with one fixed pair at
each end. Raising `max_window_pairs` from 7 to 9 returns the identical window.
The boundary types are `unknown`, pairing coverage is incomplete, and an empty
protected-site list does not authorize surrounding junction movement.

This is a **declaration/scope limit, not a physical impossibility result**.
W227's wider reporting mask did not admit an expanded recovery. The next attempt
needs a source-qualified terminal/coupled or periodic-image window, explicit
paired neighbours and junction/anchor permissions. Keep the original measured
core only after proving its source and image correspondence. The existing
motion source (`f33754cc…`) and Cedar C539's canonical source (`d26ebf24…`)
are different coordinate bytes; matching residue labels do not let one inherit
the other's operators or motion authority.

Receipt: `NASolve:branch-artifacts/willow/w229-window-scope/review.json`;
controller: `branch-artifacts/willow/runners/w229-window-scope.py` under that
same anchor, run with `PYTHONDONTWRITEBYTECODE=1`, the NASolve Python `-B`, and
optional Gemmi 0.7.5. No production change, new tests, full suite or native run
accompanies this read-only planning result. Rowan reviewed it as tonight's
bounded stopping point.


## W231 — Distinguish the central crossover from a stacked duplex step

A cold context audit binds the same canonical `MR_frames/5W6W/C_G.pdb`
(SHA256 `d26ebf248a0a597a3884a6d6b2c6ec8f9bba27c9cad9f0604da136e13bfb1817`)
and C536/C539 source-frame registration used in W228. The existing graph owner
retains the single B7 O3′ → B1 P continuation, imaging B1 by `-y,x-y,z`.
No new pairing, junction mobility or connection is inferred.

| Source context | O3′–P distance (Å) | Adjacent ring-plane angle (°) |
| --- | ---: | ---: |
| A8 → A9 | 1.614036 | 8.2335 |
| A15 → A16 | 1.620926 | 6.6841 |
| B7 → image(B1) | 2.794915 | 81.9763 |

The seam's ring centroids are 11.8165 Å apart. This source geometry is a
crossover context, not an ordinary within-duplex stacking target. The intended
covalent connection does **not** imply that its two bases should become parallel.
Do not copy a generic neighbouring-base stacking restraint across this seam.

**22 cold checks** include source hashes/immutability, forward and reciprocal
bond distance, order-three cycle, exact graph intent, independent fractional
versus Cartesian image transport, P/OP1/OP2 retention without OP3, and observed-
ring least-squares plane fits. The independent seam angle is 81.9773°; the small
difference from canonical-template fits is retained. No coordinates, native
calls or refinements were written/run. The numerical image composition is an
explicit diagnostic; W230's public reader remains identity-image only.

Rowan confirms that the reviewed connection does not independently declare
movement of A8–A9 or A15–A16. W229's fixed whole-pair endpoint mask therefore
remains closed to seam motion. Next, describe a narrowly scoped connecting-
backbone candidate with bases/sugars and outer context explicitly held, or obtain
an explicit coupled-junction movement declaration before a whole-pair trial.
Keep proposal/testing authority distinct from final scientific acceptance; no
unnecessary repeat of Cedar's whole-model phosphate recovery is warranted.
Cedar C543's 1.620183 Å child connection and OP angles 103.22°/115.70° are
owner-reported evidence from ordinary coordinate/ADP refinement, not proof of a
sugar-frozen repair or a new Willow-native qualification.

Local NASolve evidence: `branch-artifacts/willow/w231-junction-context/review.json`;
controller `branch-artifacts/willow/runners/w231-junction-context.py`, run with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages`
and the main checkout's Python 3.12. It consumes the relocated W230 installation
and explicitly anchored canonical inputs. An initial interactive inspection used
an absent `point` method and stopped before measuring the seam; the recorded
controller uses existing `apply`/`pullback` and independently verifies transport.
Raw science remains local. No runtime/schema/default change or migration.


## W232 — Bind a six-atom connecting-backbone scope

The first conservative candidate window now names B1 P/OP1/OP2/O5′/C5′ and
B7 O3′, with a proposed 2 Å per-atom displacement cap. All other **856 atoms**
—including every base and sugar-ring atom—stay fixed, as do occupancy/ADPs.
This is an exploratory feasibility constraint, not a recommended production
fit. O3′ is exocyclic; moving it still needs the B7 C3′ handedness check, and
moving C5′ needs the B1 C4′ check. Keeping ring coordinates alone is insufficient.

**23 cold checks** bind the exact C543 `manual-001` child
(`5c0b63b683c58e977d12ebce9b6aca61d44444367a816417a2e8c39e667fb075`)
to its real `refine-005` ancestor, unchanged 862 identities, observations and
source-image declaration. The inherited native receipt
`886583be3b0a852e38c9770f7ee081f30388540f481db8ef8b5f4b148c702fde`
authenticates the copied fixed-coordinate capture through existing Cedar owners.
The existing coordinate mask and endpoint byte audit accept zero displacement
and refuse moving a held sugar atom or exceeding the 2 Å cap. No displaced
model, minimization, native call or refinement is produced.

Captured dictionary support touches six bonds, nine angles, six dihedrals and
three chirality terms (including phosphate chirality). All 44 planarity and
57 parallelity terms lie wholly in the fixed context. The capture contains no
`bond_asu` terms; observing its monomer support is not proof of complete
image-aware continuation forces in the restarted optimizer. Cedar owns that
restoration, exclusion and exactly-once execution gate.

The maintained preparation-window inspector deliberately refuses refined/manual
descendants. This audit does not bypass it by inventing a preparation or preview
ancestor: existing checkpoint resolution and inherited-input verification,
authenticated native capture, named proxy support and native/source mapping are
composed directly in a local diagnostic. A maintained descendant-window consumer
will require the explicit Cedar lineage join.

The current child already measures 1.620183 Å at the seam. The next useful
physical test starts from the **original 2.824 Å ancestor**, asking whether
this narrow backbone window can close with rings held under the full original
chemistry and complete image-aware restraints. Do not perturb and recover the
already closed child merely to obtain another success. Expand the window only
as a new explicit hypothesis if the narrow constraint proves infeasible.

NASolve anchor: `branch-artifacts/willow/w232-backbone-window/review.json`,
with unchanged model/registry snapshots in `inputs/` and the authenticated
capture in `native-capture/`. Controller `branch-artifacts/willow/runners/w232-backbone-window.py`
uses Python 3.12 with the same `PYTHONDONTWRITEBYTECODE` and Gemmi environment
as W231. Original inputs and selected checkpoint remain untouched. These local
working inputs are not a complete portable numbered run and stay out of Git.
No runtime/schema/default change, new installation or full-suite repeat.


## W234 — A closed seam can still strain the fixed-sugar boundaries

The explicit six-atom donor-coordinate graft tests a narrower question than a
new fit: can C543's refined connecting atoms simply be copied into the original
ancestor while all 856 other atoms stay fixed? **No: this graft closes the seam
but leaves substantial fixed-sugar boundary strain.** It does not establish that
a separately optimized six-atom solution is impossible.

| Measurement | Original ancestor | Whole-model donor | Six-atom graft |
| --- | ---: | ---: | ---: |
| Image O3′–P, Å | 2.824291 | 1.620183 | 1.620183 |
| B1 C4′–C5′, Å | 1.513077 | 1.515540 | 1.444806 |
| B7 C3′–O3′, Å | 1.428669 | 1.463469 | 1.648819 |
| Image C3′–O3′–P, degrees | 107.948 | 121.345 | 131.893 |

The graft's two fixed-sugar boundary bonds are −9.60 and +16.45 native dictionary
sigmas respectively; the largest local dictionary angle deviation is −4.81
sigmas. These are measured against the authenticated W232 native definitions,
not new empirical thresholds. All three explicit source-relative chirality
signs survive. The maximum selected-atom displacement is 1.370846 Å, below the
predeclared 2 Å bound. All available W233 base-stacking changes are exactly zero
because every base and sugar-ring coordinate remains fixed; unsupported PDU
frames remain explicit. Unchanged stacking does not make this a good backbone.

**22 cold checks** verify exact input hashes, full record identity/order, the
existing masked endpoint byte audit, retained occupancy/ADPs, source-relative
handedness, dictionary target/weight validity and input preservation. Exactly one
diagnostic PDB is written; no native geometry evaluation, optimization,
refinement, map scoring or acceptance occurs. In particular, donor ADPs are not
copied. The candidate is evidence of boundary strain, not a model to adopt.

Next use Cedar's complete image-force manager for one bounded optimization from
the original ancestor, retaining the two sugar boundary bonds, their angles and
handedness. Do not silently expand the mask, adopt the donor graft or replace
this question with another whole-model fit. Complete symmetry force/exclusion
lifecycle, packing and diffraction-supported recovery remain separate gates.

Local NASolve receipt: `branch-artifacts/willow/w234-local-pose-preflight/review.json`;
PDB: `six-atom-donor-candidate.pdb` in that folder. Controller:
`branch-artifacts/willow/runners/w234-local-pose-preflight.py`, executed with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages`
and the main checkout's `.venv/bin/python -B`. It reuses the relocated W233
installation and exact W232 source/capture anchors; no external program runs.
Generated science stays local and excluded from Git. Documentation/evidence only;
no API/schema/default or migration change. Roadmap consistency and diff checks
suffice here; the preceding W233 installed tests and W230 complete-suite result
remain tied to their own recorded code checkpoints.


## W235 — Close the local symmetry connection with all rings held

One bounded native geometry trial answers W234's next question. Starting from
the original `refine-005` ancestor, **six connecting atoms can approach the
complete native bond and angle targets while all 856 other atoms stay fixed**.
This is a local feasibility result for this declared connection, not a large
helix bend or general repair. No datum or Free-R flag is used to choose the pose.

| Measurement | Original | Six-atom donor graft | Constrained endpoint |
| --- | ---: | ---: | ---: |
| Image O3′–P, Å | 2.824291 | 1.620183 | 1.613032 |
| B1 C4′–C5′, Å | 1.513077 | 1.444806 | 1.511786 |
| B7 C3′–O3′, Å | 1.428669 | 1.648819 | 1.440062 |
| Image C3′–O3′–P, degrees | 107.948 | 131.893 | 119.737 |
| Maximum local bond deviation, native σ | 0.514 | 16.448 | 0.389 |
| Maximum local angle deviation, native σ | 2.997 | 4.812 | 1.553 |
| Maximum image bond / angle deviation, native σ | 101.441 / 16.512 | 1.099 / 10.161 | 0.503 / 0.733 |

A separate 36-case Phenix dihedral-kernel readback confirms the reported signed
angles and absolute periodic deviations (maximum errors 2.85×10⁻¹³ degrees and
1.43×10⁻¹⁴ σ); no new whole-model evaluation or fit.
These descriptive deviations use the exact source definitions; they are not a
universal geometry acceptance gate. The written candidate's largest local and
image torsion deviations are **2.250 and 2.943 σ**. All three selected-boundary
relative chirality signs survive at full and PDB-rounded precision. Base/sugar
coordinates and their frames are identical to the ancestor. Maximum selected
motion is **1.884603 Å**, below the declared 2 Å bound. Occupancy/ADPs and all
noncoordinate source bytes are unchanged.

### Native composition and actual stopping state

The installed Cedar C545 `RegisteredPhosphateRuntime` attaches to the intact
862-atom native model before any coordinate restriction. Ordinary Phenix owns
the explicit image bond and its four second-shell exclusions; the runtime adds
the four angles and three torsions from two agreeing, chemically matched source
links. The actual full manager evaluates every proposal; only the six selected
atoms receive coordinate variables. No shortened molecular model or new force
implementation is substituted. Existing internal pair/plane restraints remain.
All plane terms lie in the fixed context, so no movable plane force is omitted.

The original C540 ancestor reference and its own capture are used, not the
C543 written child. Native work/free selection is **1785/124**, digest
`5c5153ab49d91becc9c1986450c5684a0e51e8d88a18538b4aad5b72e5d029de`.
This is a complete **Phenix 2.2.1-6174 geometry-only optimization**, following a
native dry-run initialization. There is **no diffraction refinement** or fitted
B/Q. The original model hierarchy, scattering metadata, observation arrays and
baseline energy/gradient are verified unchanged; runtime hooks are restored.

The existing Willow `run_native_masked_trial` uses 18 Cartesian variables and
hard budgets of 50 iterations, 180 optimizer calls and 450 total evaluations,
with a 300-second owned-process timeout and one CPU. No extra pair penalty or
tether is added to the complete native target. It takes **53 optimizer calls,
277 total evaluations and 8.60 seconds**, stopping at **50 iterations—not
convergence**. Raw target decreases 14545.5943 → 3623.3298 (rounded 3623.3474).
Initial, full-precision and rounded derivative audits each test all 18 axes at
10⁻⁴ and 10⁻⁵ Å; worst absolute error is 5.81×10⁻⁵ against the existing 10⁻³
bound. This qualifies the numerical callback here, not physical completeness in
other cases or scientific acceptance.

### Evidence, compatibility and next gate

**34 cold checks** authenticate the ancestor's own capture, inspect all six local
bonds/nine angles/six torsions plus eight image terms, verify all fixed records
and confirm the owned process stopped. The candidate SHA-256 is
`43ed35838333eebbcf8cac2126dae496218dfc8715aefeae99749c0eb846756b`.
The earlier donor-graft failure remains intact; no selected endpoint or source
checkpoint is changed. First exploratory readback imported an absent private
angle helper and stopped before measurement; the recorded cold review uses the
existing preview angle helper and Gemmi's dihedral measurement.

NASolve anchor: `branch-artifacts/willow/w235-six-atom-native/`, containing the
frozen `plan.json`/`binding.json`, `native-result.json`, `review.json`, process
receipts and diagnostic `geometry-candidate.pdb`. Controller commands:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w235-six-atom-native.py prepare`
and the same command with `launch`; preparation and launch are single-use for
this immutable directory. Cold review uses `w235-review.py` with the W231 Gemmi
environment. The plan records declared input/code anchors and hashes, with
absolute runtime locations retained as local provenance. It is not a portable
numbered-run publication.

The compact local checkout is under the GitHub sibling anchor
`ScienceCheckouts/Linden/2026-11-23_symmetry-connection/`: `index.html`, one figure,
`manifest.json` and `open_comparison.py`; models are hash-checked links, not
copies. ChimeraX **1.12** headless checks load three 862-atom sources, verify the
explicit displayed image distances and execute all five actions. First launch
was blocked by its application cache lock; the permitted launch passes. GUI
rendering is not claimed. The matplotlib figure was rendered and visually checked.
Grey background, silhouettes, soft lighting and thin rings remain defaults;
GUI uses orthographic projection. Displaying B7's symmetry image changes no file.

Next qualify the exact candidate through a matched diffraction receiving step
with its complete image forces, original observations/Free and held context,
coordinating with Cedar's separate child-restart survival comparison. Review
residual torsions, native packing and maps; do not simply extend the geometry
budget or optimize against Free-R. No wider junction movement follows.
Evidence/docs only in Git, no new product API/schema/default or migration; raw
science stays local. Existing installed owners were composed without a source
patch; no redundant full suite or new packaging claim.


## W236 — Bind the saved candidate to matched receiving preflights

The saved W235 endpoint now has its **own fresh native capture** under the seven
original restraint inputs. Cedar's `inspect_inherited_continuation` verifies
identical atom chemistry and crystal representatives against the original
registered source. Its agreeing native reference links reproduce the original
source groups. This is a diagnostic coordinate descendant; no numbered
checkpoint ancestry or preparation status is invented.

Two complete **Phenix 2.2.1-6174 dry runs**, original seed and W235 seed, pass the
complete image-force restart and exact six-atom selection. All 862 source atoms,
coordinates and B/Q remain unchanged at preflight. Both use identical **1785
work / 124 Free** observations and all live connection terms. Original and
candidate raw geometry targets reproduce W235 within 10⁻⁸ despite fresh native
interpretation. The eight-term seam is not inferred merely from a plausible
printed distance. Seventeen cold checks verify the recorded comparison.

The intended receiving policy is five cycles, at most 100 iterations per cycle,
one CPU, seed 15403, individual selected XYZ only, native scaling enabled but
no overall isotropic scale transfer into atom ADPs. XYZ/ADP weight optimization
is disabled; the initial native weight uses `wxc_scale=0.5`. This is a frozen
matched two-arm question, not a Free-R-driven parameter sweep. Final observation
selection must still be audited because the original outlier policy remains.
Dry-run R values precede the completed scaling/refinement cycle and must not be
compared with published final refinement statistics.

Two preparation failures are retained. Version 1 omitted the original explicit
`data_manager` labels, and the native parser refused the ambiguous intensity
arrays before preparing a model. Version 2 restored those labels but used `C5*`,
which also selects the nucleobase C5; the exact six-atom check refused it before
any fit. Version 3 uses literal apostrophe atom names, independently checked by
the native selection parser, and both preflights pass. No production code or
science result was overwritten. These are input preparation corrections, not
changes selected from refinement outcomes.

**No diffraction fit has run.** Rowan requested the fitting window remain free
for the separate deposition repair. Reuse the passed version-3 preflights when
that window opens; do not rerun source interpretation without changed inputs or
policy. In the meantime, a fixed-map comparison against the original checkpoint
can inspect the proposed local movement without regenerating density from the
unrefined candidate.

NASolve anchor: `branch-artifacts/willow/w236-six-atom-receiving/` contains the
fresh capture, `candidate-inspection.json`, original and corrected receiving
plans, per-arm `preflight-v3/` proofs and `review.json`. Controllers under
`branch-artifacts/willow/runners/`: `w236-receiving-prepare.py`, `w236-bind.py`,
`w236-live-preflight.py` and `w236-review.py`. Preparation/frame/cold readers use
the same main Python 3.12 and W231 Gemmi environment; the owned preflight launcher
runs native Phenix Python with a 120-second limit and single-thread variables.
The execution script exposes dry runs only, not a refinement dispatcher.
Generated science remains local. Evidence/docs only in Git; no API/schema/default
change, migration, installation claim or full-suite repeat.


## W237 — Inspect the local proposal in the fixed original map

While diffraction fits remain held, the installed model/map inspection,
coefficient-selection and density-rendering owners now show W235 against the
**original `refine-005` map**, held fixed for both coordinate states. No density
is regenerated from the proposed coordinates. The 18 displayed atoms include
all six moving atoms; B7 uses the explicitly declared crystal image beside B1.
No coordinate alignment, movement exaggeration or automatic noise classification.

| Moving atom | Original → proposed, 2mFo–DFc σ | Original → proposed, mFo–DFc σ |
| --- | ---: | ---: |
| B1 P | 0.730 → 0.777 | 1.382 → 1.857 |
| B1 OP1 | 1.736 → 1.722 | 2.574 → 2.677 |
| B1 OP2 | 0.205 → 0.819 | 0.658 → 1.894 |
| B1 O5′ | 0.079 → 0.054 | 0.835 → 0.877 |
| B1 C5′ | −0.891 → −0.887 | 0.321 → 0.325 |
| Image B7 O3′ | −0.676 → −0.522 | 1.116 → 1.234 |

These are two positions sampled in each **same** source map, not a before/after
change in density. P/OP2 sample more positive difference density, while weak or
negative ordinary-map support remains elsewhere. This is mixed, limited evidence;
it neither validates the repair nor identifies the cause of residual density.
The ordinary model-assisted maps include Free-R reflections and must not be used
as an independent validation or motion-search score.

The existing resolver pins the model and `refined_001.mtz` to the saved
checkpoint; map SHA is `646940e316126a379b844b0a320959293a2cb509e802791d18da892613a87936`.
Exact arrays are `2FOFCWT_no_fill,PH2FOFCWT_no_fill` and `FOFCWT,PHFOFCWT`.
Saved parameters declare unfilled, isotropized, unsharpened maps with Free-R
included. Source hashes, group and cell at PDB precision agree. An initial
10⁻⁶ Å cell comparison refused before the FFT: MTZ float storage differs by
2.32×10⁻⁶ Å. The corrected check verifies the exact space group and PDB cell
precision, retaining the measured difference rather than changing any frame.

Two Phenix **2.2.1-6174** FFTs of saved coefficients use whole-cell sigma scaling,
then trilinear sampling on a 24×28×20 local grid. Existing W143 mesh arithmetic
produces 31 contour levels, 8931 vertices and 16243 triangles. Every checked
mesh vertex reproduces its contour within 10⁻⁸. Lattice translation samples
agree within 10⁻¹⁰; rotation-related trilinear samples differ by at most
0.01945 σ, explicitly recorded instead of assuming interpolation preserves
rotational symmetry exactly. Twelve fixed-atom sample pairs are unchanged.

**14 cold checks** verify source pins, numerical scene preservation, the filled
base64/gzip HTML payload, separate model/map labels, all contour levels, absence
of a candidate map, lattice sampling and report links. The static sample figure
was rendered and visually checked. Interactive browser rendering of this scene
has not been tested. The historical run has checkpoint/parameter/hash evidence,
not a retroactively invented modern producer receipt.

NASolve anchor: `branch-artifacts/willow/w237-fixed-source-density/`; controllers
`w237-fixed-density.py`, `w237-review.py`, `w237-checkout.py`, `w237-figure.py`
under the existing runners directory. Native scene command:
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 phenix.python -B branch-artifacts/willow/runners/w237-fixed-density.py`.
Cold verification uses main `.venv/bin/python -B` with `PYTHONDONTWRITEBYTECODE=1`.
Existing output files are single-use; failed cell-check log is preserved.
The local GitHub sibling checkout is
`ScienceCheckouts/Linden/2026-11-23_fixed-source-density/index.html`, alongside
its self-contained `inspect_density.html`, figure and compact manifest.
No new coefficients, diffraction fit, product API/schema/default or migration;
raw map data and derived visualizations remain excluded from Git.


## W239 — Regress explicit staggered duplex recuts

A local live repair motivated one compact regression through the existing Pine
owners, rather than another recut implementation. The parameterized synthetic
case in `tests/test_topostitch_backbone_intent.py` reuses the renamed two-duplex
fixture in P43 and R3:H. It declares directed strand order, cuts A2|A3 opposite
B2|B3, and changes the representatives of A3/A4/B2. Exactly one paired rung
crosses the boundary. The two resulting route images are reciprocal; continuation
P/OP1/OP2 persist without OP3 or terminal-phosphate authorization. The replayed
packet binds all source identities and numerical coordinate/tensor round trips;
context atoms and source bytes remain unchanged. These synthetic ring/phosphate
coordinates are not a chemical validation fixture.

Validation (Gemmi available in the test environment):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q \
  tests/test_topostitch_backbone_intent.py tests/test_topostitch_recut_bundle.py \
  tests/test_topostitch_continuations.py tests/test_topostitch_transport.py
```

171 passed in 8.71 s. The actual local invocation added the existing external
Gemmi/test dependency directory to PYTHONPATH. No full-suite or installation
repeat: this adds coverage only, with no product code, schema, dependency or
native-runtime change. No generated structures, manuscript data or host paths
are committed. The first test draft exposed the reused fixture's record-order
strand list; the case now explicitly declares 5′→3′ order instead of inferring it.

**Open pipeline gates:** an explicit image request does not establish that the
chosen cut belongs to the intended duplex. Automatic wrong-duplex rejection
needs registered pair/route correspondence and a reviewed cut request; existing
identity guards are not that scientific discriminator. The live source-frame
repair and locked-sugar qualification remain separate Cedar-owned evidence,
not a maintained end-to-end Pine replay. P03/P04 stay PARTIAL: preserve complete
angles, planes, exclusions and fixed boundaries; recutting cannot close a gap.

The live read-only audit also exposed a native serialization hazard in Phenix
2.2.1-6174: `mmtbx.model.manager` deep-copies its input, and the hierarchy pickle
path uses PDB precision when labels fit PDB. An otherwise identical long-component
CIF can therefore follow a different precision path from a short native alias.
A controlled local comparison measured XYZ rounding up to 0.0005 Å and Uij up to
0.00005 Å²; passing an explicit `hierarchy.deep_copy()` preserved both exactly.
This is diagnostic evidence, not a runtime patch or proof of the full refinement
lifecycle. Qualify construction, copying, source-frame export and independent
scattering readback before widening native representative support. Preserve
original coordinate/tensor fields in final source-frame exports.

The earlier prepared two-arm 5W6W receiving experiment remains unlaunched;
its local folder name was reserved before this live diversion and does not
establish a completed W239 native result. Resume only after coordinator release.


## W240 — Reach registered phosphate refinement through the installed product

**Behavior:** the existing fitting command now has an opt-in `native-phosphate`
route, instead of requiring an experiment-specific native launcher. Cedar C545
still owns registered image chemistry, four angles/three torsions, the native
bond/exclusion shell and refinement/process lifetime. Willow owns the checked
request, preflight-before-fit sequence, six-atom motion mask and verified source-
frame return. The legacy geometric route remains unchanged. See the
[request/API guide](topostitch-preview.md#refine-one-registered-phosphate-connection-w240).

The real qualification uses the previously declared B7 O3′→B1 P continuation
and original 862-atom source, with only six connecting atoms movable. Source
SHA-256: `00ee2b2f9ebc57e1bab1a51abc64a903c204cdddabccf6a8399ef1546c547313`.
The target-P image is `-y,x-y,z`, reciprocal to the P-fixed O3′ view
`-x+y,-x,z`. These belong to that registered construct and exact coordinate
frame; they are not defaults for other designs. P/OP1/OP2 persist without OP3.

One complete Phenix **2.2.1-6174** preflight followed by one **1-cycle,
50-iteration-cap** refinement returns `REFINED_FOR_REVIEW`. All 862 atoms,
856 held coordinates, source B/Q and noncoordinate PDB records survive. The
native owner records 33 complete seven-term gradient calls, one bond, four
second-shell pairs and no remaining nonbonded pair for that connection. Both
workers stop and native hooks restore. Full-precision maximum motion is
0.820711 Å. The final installed command reproduces both full-precision points
and the source-preserving PDB exactly (SHA-256
`89cae84cd5b90da136bdf05e0d9ae699d4b3db31bde51bd7634673510e42b494`).

**This is a software qualification, not a finished chemical repair:** O3′–P
shortens 2.824291→1.945379 Å, while O3′–P–OP1/OP2 remain 65.042°/154.648°.
Final Rwork/Rfree are 0.315017/0.363246. The scaled native starting values are
approximately 0.3138/0.3540; the preflight's unscaled raw statistics are not a
comparable recovery baseline. No checkpoint is selected, no statistical gate
is changed and no longer refinement is implied by this one-cycle result.

The first complete fit was deliberately rejected by a too-literal observation
check. Investigation showed **no dropped reflections**: native
`apply_scale_k1_to_f_obs` rescales F and SIGF by one common positive factor.
The corrected guard requires all 1909 ordered indices and 124 original Free-R
assignments exactly, allowing only this common normalization (131.91489939471037
in the returned native doubles). Per-value native-double tolerance is 1e-12
relative/1e-10 absolute; exported float32 MTZ arrays were independently checked
and are not held to double precision. Nonuniform F/SIG changes, duplicate or
removed indices and changed flags still fail. No data-selection policy was
relaxed. The rejected attempt and its read-only diagnostic preflight remain.

**Validation:** 261 focused source tests (7.12 s) and the same 261 tests from an
isolated wheel installation (6.48 s), with original temporary build path gone.
The 26 entry-specific cases cover invalid bounds, request relocation/checksums,
source records/Cartesian tensors, fixed atoms, thermal/data preservation, both
CLI dispatch paths, common-scale handling, failed-preflight isolation and changed-
plan refusal. The changed-plan regression fails against the earlier installed
implementation, then passes with the guard. Both installed help routes and
Python 3.10 syntax checks pass. Installed and source module hashes agree.
No shared chemistry/global mechanics changed; no full-suite repeat. The legacy
geometric CLI dispatch is tested; its optional SciPy optimization is not rerun.

Exact focused command (Python 3.12, Gemmi/test dependencies available):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q \
  tests/test_topostitch_phosphate.py tests/test_topostitch_endpoint.py \
  tests/test_topostitch_captured_job.py tests/test_topostitch_recut_bundle.py \
  tests/test_topostitch_backbone_intent.py tests/test_topostitch_transport.py
```

The actual local invocation appends the existing qualified Gemmi/test dependency
root to PYTHONPATH. Build uses `python -m pip install --no-deps --no-build-isolation
--target INSTALL BUILD_SOURCE` with existing setuptools. Installed checks use
`PYTHONPATH=INSTALL:DEPENDENCIES` from the isolated copied test fixture tree.
Initial missing-build-backend and incomplete test-fixture-copy failures were
harness preparation failures, retained alongside the successful logs.

Native command, from outside the checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=INSTALL:DEPENDENCIES \
  INSTALL/bin/nasolve-topostitch-fit native-phosphate \
  --request REQUEST --out NEW_JOB --phenix PHENIX_ROOT \
  --cedar-source QUALIFIED_CEDAR_PACKAGE --timeout 300
```

The complete installed execution qualifies the final input/plan/source guards,
not just the earlier source draft. All native runs use one CPU. Local evidence
was moved, not duplicated, into the NASolve anchor
`branch-artifacts/willow/w240-native-phosphate/`; `archive-manifest.json` verifies
867 original files after that move. `attempt-001` preserves the rejected fit,
`attempt-002` the source success, and `installed-native` the final installed
success. Request/source pins, native argv/logs, worker stop receipts, initial/
returned states, geometry readback and installation/test logs remain there.
Historical absolute paths record execution provenance; replay after moving a
native job is **not qualified**. No coordinates, diffraction data, native capture,
private request or generated output are committed.

**Compatibility/migration:** additive schema-1 request/plan/result, no migration
of existing requests or checkpoints. Standalone Willow requires explicitly
supplied compatible Cedar modules; no implicit branch merge or ordinary campaign
activation. The PDB review export preserves original metadata and requires later
deposition preparation. Whole-ASU mmCIF construction, arbitrary endpoints, multiple
connections, automatic partner choice and scientific acceptance remain open.

**Next distinct experiment:** compare the original poor pose and W235's already
qualified geometry seed under the same five-cycle receiving protocol. This asks
whether initialization changes recovery, not whether the seven-term runtime
works (Cedar already qualified that). Reuse the frozen W236 controls, keep arms
independent, and audit retained observations, fixed context, boundary geometry,
residual angles/torsions and maps. Do not tune weights against Free-R.

**Investigator interpretation (via Rowan):** in the live periodic-repeat example,
retain the phosphate treatment where its symmetry-related oxygen angles work;
otherwise an explicitly reviewed unrestrained edge is a legitimate fallback.
This does not authorize deleting phosphate atoms or inventing another construct's
connection. An averaged ASU repeat boundary is not itself a chemical nick; actual
strand termini/cuts need construct-specific correspondence. W240 does not implement
automatic fallback selection or claim the live manuscript repair as a Pine replay.


## W241 — Compare geometry-seeded and direct native receiving

The queued initialization question now has two complete five-cycle refinements
through the installed W240 entry. Both use the same explicit continuation,
six-atom mask, held B/Q/context, seven ordinary restraint/dictionary files,
100-iteration cap per cycle, random seed 15403, one CPU and requested
`wxc_scale=0.5`. No new chemistry implementation or partner inference.
Compared with W236's frozen preparation, **outlier rejection is now explicitly
False in both arms**, so original observation membership is mandatory. New
preflights were therefore appropriate. The historical W236/W239 preparations
remain unchanged and were not relabelled as completed native runs.

| After five cycles | Original pose start | W235 geometry-seed start |
| --- | ---: | ---: |
| O3′–P connection, Å | 1.819145 | 1.613075 |
| O3′–P–OP1 / OP2, degrees | 74.607 / 149.406 | 107.179 / 109.761 |
| P–OP2 bond, Å | 2.002509 | 1.482122 |
| Maximum local bond / angle deviation, native σ | 26.125 / 8.341 | 0.398 / 1.614 |
| Maximum image angle / torsion deviation, native σ | 13.802 / 1.845 | 0.742 / 2.955 |
| Rwork / Rfree | 0.314296 / 0.363045 | 0.311730 / 0.368844 |
| Maximum movement from that arm's start, Å | 0.690984 | 0.006580 |
| Complete seven-term gradient calls | 148 | 139 |

All 862 atoms, 856 held coordinates and source B/Q survive. Exact initial native
arrays, all 1909 ordered indices and 124 Free-R assignments match between arms;
final arrays retain those indices/flags with only the audited common F/SIG scale.
Both runs use identical runtime source hashes and seven image terms, retain the
native bond/second-shell exclusions, restore hooks and stop their workers. All
three measured source-relative sugar/phosphate handedness checks remain positive
in all four states. Those checks are not a new phosphorus stereochemical assignment.
The table uses source-preserving written coordinates, with full-precision endpoints
retained separately. No automatic checkpoint adoption or scientific acceptance.

**Interpretation:** the geometry seed survives the native recipe with good local
bond/oxygen-angle geometry. Direct refinement of the poor pose remains badly
strained. The seeded torsions still reach 2.955 native σ, both Rwork values remain
above 0.3, and seeded Rfree is slightly worse. This closes the narrow question of
whether the local seed survives five receiving cycles, not the general repair,
density support, convergence or end-to-end campaign gate.

**Important native-weight confound:** same requested protocol did not mean a
fixed objective. First-cycle native `wxc` is 618.328357 for the original versus
1.171254 for the seed; with scale 0.5 the effective printed diffraction factors
are 309.164 versus 0.585627. Fifth-cycle factors are approximately 143.624 versus
0.332522. The seed moves only 0.00658 Å. We therefore cannot attribute the outcome
solely to an initialization/basin effect or claim that strong diffraction forces
were resisted by the seed.

Read-only inspection of the installed Phenix **2.2.1-6174**
`mmtbx/refinement/weights.py` explains this: with `fix_wxc=None`, native weighting
uses the chemical/data gradient norm ratio. At 3.5–4.5 Å resolution after cycle 1
(this data set is 4.19 Å), it also adjusts `wxc_scale` using the angle between
those gradients. `optimize_xyz_weight=False` disables the optimization search,
not either of these native operations. Exact printed cycle values, source hash
and line references are in `weight-audit.json`; no SDK or default was patched.
There was no Free-R-driven search or extra refinement after this finding.

**Validation/evidence:** two complete Phenix 2.2.1-6174 preflights plus two complete
five-cycle fits through `nasolve-topostitch-fit native-phosphate`, with the W240
CLI flags and respective predeclared requests. No software change, installation
repeat or full suite. Reuse the already qualified W239 local-term measurement
arithmetic: 29 source-native terms per state (116 values over original, seed and
two returns), plus 12 handedness checks. The matched input/return checks and exact
source references are recorded in `geometry-review.json`. A new independent
NASolve-anchor directory `branch-artifacts/willow/w241-seeded-receiving/` contains
`plan.json`, `original-request.json`, `geometry_seed-request.json`, independent
`original/` and `geometry_seed/` jobs, logs, native state/stop receipts, geometry
and weight audits. The prior preparations and all raw input bytes are preserved.
Generated data stay local and excluded from Git.

**Inspection:** the compact GitHub-sibling checkout
`ScienceCheckouts/Linden/2026-11-23_seeded-receiving/index.html` links a simple
Python-openable ChimeraX comparison and the existing offline density inspector.
The latter reuses W237's exact 31 saved contour meshes and crystal image: no FFT,
new map, alignment or exaggerated motion. Obsolete atom samples were removed
rather than carried across changed coordinates. It holds the original
model-assisted map fixed; Free-R reflections are included, so it is diagnostic,
not independent evidence. Both full source-preserving final PDBs are linked by
verified relative paths/hashes, not copied into the checkout. The bond/angle
figure was rendered and visually checked. ChimeraX **1.12** headless opening and
initial comparison pass; interactive browser/GUI behavior was not retested here.

**Next bounded question:** qualify and expose the effective native weight policy
before treating a paired run as a fixed-objective comparison. If a mechanistic
control is then justified, predeclare one common native `fix_wxc`, keep the same
models/observations/mask and inspect geometry plus maps; do not choose that value
by looking for a lower Free-R. Native already provides this option: do not write
a second weighting engine. No extra fit or weight sweep is authorized by the
ledger itself. Density-supported repair, stacking recovery and broader bending
remain their existing separate milestones.


## W244 — Audit coordinated live anisotropic phosphate returns

Cedar's C547 working package and the frozen installed Willow W243 entry completed
four **Phenix 2.2.1-6174** refinements owned by Rowan: two explicitly registered
cuts in each of two R3 working inputs derived from the deposited coordinate/data
pairs. Each had three macrocycles, at most 60 iterations per cycle, six movable
backbone atoms, maximum motion 1.5 Å and requested `wxc_scale=0.5`. These are
initially healthy connection controls, not repair of a widely separated seam.

| Control | O3′–P (Å) | O3′–P–OP1 / OP2 (°) | Maximum local residual (σ) | Maximum atom motion (Å) |
| --- | --- | --- | --- | --- |
| 3LNA cut 1 | 1.613413 | 109.141 / 112.008 | 1.808 | 0.330717 |
| 3LNA cut 2 | 1.610070 | 107.094 / 110.074 | 1.764 | 0.554335 |
| 5LNA cut 1 | 1.606412 | 108.880 / 107.785 | 1.305 | 0.107192 |
| 5LNA cut 2 | 1.604866 | 107.004 / 104.290 | 1.371 | 0.074192 |

All eight native-reference local terms remain within 1.82 σ. Each result moves
six atoms and preserves every other coordinate and source ANISOU/B/Q record.
Rowan independently reopened each exported candidate with native cctbx: all
1271/1275 Cartesian displacement tensors agree with the native return within
8.89e-15 Å², with only expected PDB coordinate rounding. Original reflection
and Free membership survive (1484/66 and 2375/120 respectively). These checks
qualify this local native-return/export path; they are not a whole-ASU scattering
invariance or deposition-acceptance claim.

Linden audited the saved evidence without rerunning refinement: **84 frozen-file
hashes**, four candidate/source digest bindings, exact W243 runtime module pin,
three-cycle/six-atom controls, exact initial/final frame, complete observations
and atom inventory all pass. Every result remains `REFINED_FOR_REVIEW`, with no
checkpoint created or scientific acceptance. The source hashes and per-case
references are in NASolve anchor
`branch-artifacts/willow/w244-live-return-audit.json`; each external receipt uses
the explicit `cedar_r3_native_links` anchor and relative path. Its local binding
is historical evidence, not a claim that the native run is portable. The underlying
Cedar archive is owned by Rowan; do not copy/re-run it or edit manuscript files.
W243's source/installed tests remain the code qualification; this update changes
documentation only. No native run, full suite, model/MTZ copy or private data commit
was added by Linden.

**Next:** keep the damaged-seam recovery and residual torsion/density questions
open. Use W242's existing observer before any matched receiving comparison; qualify
an explicitly common weight policy with Cedar instead of treating identical
requested scales as identical objectives. Preserve the independent whole-ASU,
input/scattering and reviewed unrestrained-edge gates. A mobile healthy cut is a
positive integration control, not proof that arbitrary ends can be repaired.


**W244 coordinated control addendum:** Cedar C547 is now pinned at
`43bec537e68ec7f0ee6db185564c4fa1577f40da`, paired with Willow W243
`5f5c129b439452256e71d3e03dc6bcbeb10404b8`. Rowan's durable report,
`Verified phosphate fits.json`, SHA-256
`8a4a187d51e23f026834fd7f016656754dc1822dfe118eef24775a982a99bf45`,
and adjacent `Reproduce the fits.zip` are bound through the local
`lna_crystal_phosphate_tests` anchor in NASolve
`branch-artifacts/willow/w244-control-evidence.json`. The archive retains the
four original independent readbacks byte-for-byte; Linden checked their hashes,
all four added control records and the matched fixed-control starting/data bindings.
No manuscript artifact was edited or copied into Git.

For 3LNA A116→D107, the released-link control opens to **3.261472 Å**.
That adaptive-weight run is descriptive, not an isolated force comparison.
The separate bond-only and complete-restraint controls use an explicit fixed-unit
diagnostic policy and print `wxc/wxc_scale/wc = 1/1/1` in all three cycles.
Their starting state and data hashes match; O3′–P–O5′ is **95.192744°** with
bond-only restraints versus **102.461673°** with complete restraints, against the
**104°** native target. Bond lengths remain 1.609736/1.608052 Å. This shows why a
correct distance alone does not establish phosphate geometry. All displacement
tensors remain preserved on independent native reread. These are Cedar-owned
explicit diagnostic controls, not a new supported fixed-weight product mode or
a qualification of the different W241 damaged-start/geometry-seed experiment.

The **two-crystal, one-junction-at-a-time** native test is now qualified in its
stated scope. **Both junctions active in one fit remains a separate open gate**:
bind both explicit connections and the combined movable-atom selection, retain
all protected rings/thermal state/data, and check both complete seam geometries
and exclusions together. Do not infer simultaneous support from independent fits
or duplicate the completed one-junction controls.


## W246 — Observe both declared R3 routes in one saved recut

Reuse the frozen 3LNA/5LNA working PDBs, registrations, pair inventory,
continuations and reflection indices from W244's authenticated Cedar inputs.
These are PDB working derivatives, **not a direct evaluation of processed V51**.
V51's missing external annotations remain separate from the operator's declared
intent. No manuscript files are changed.

For each source, compare an unchanged packet with one explicit compound recut:
select the registered paired rungs containing D107 and B101, carry their partners
B116 and A115 with the same respective image, and preserve each source's original
directed operators/translations. This is a diagnostic representative choice, not
an adopted asymmetric unit. Only **82 atoms in four canonical residues** change
representatives; all present atoms contribute to the independent scattering sum.

| Source | All atoms / unchanged representatives | Supplied reflection indices | Relative complex-Fcalc L2 difference | Maximum absolute complex difference | Both preserved O3′–P lengths (Å) |
| --- | --- | --- | --- | --- | --- |
| 3LNA | 1271 / 1189 | 1484 | 1.466618e-9 | 6.282520e-6 | 1.609309 / 1.608058 |
| 5LNA | 1275 / 1193 | 2375 | 1.531780e-9 | 4.940444e-6 | 1.608806 / 1.604539 |

Both unchanged controls have exactly zero complex-Fcalc difference, and their
source structure factors exactly match the corresponding recut's source values.
The installed W245 API evaluates every supplied index using the unchanged Gemmi
0.7.5 neutral-atom direct sum; it does not use observed amplitudes or Free flags
to optimize or choose a cut. The declared numerical review bound is 1e-6 relative
L2, distinct from scientific acceptance; float32 tensor transport remains explicit.
The four observations take about 28–29 seconds each. No Phenix process is run.

Both selected continuation images become identity in the new representatives,
with their image-aware distances unchanged to the checked 1e-10 Å bound. All
P/OP1/OP2 groups remain; no OP3 is added. Existing labelled orbit permutations
cover every atom, and the exact graph inverse restores both original operators,
including lattice translations. Source inventory and all original input hashes
remain unchanged. Real chemical boundaries A101/C101 stay chemical boundaries;
missing annotation creates neither a chemical nick nor a guessed link. Existing
ambiguous-partner/screw/rotated/gap controls remain their scoped prior evidence,
not new experimental results from this comparison.

The frozen declaration, installed module pin, explicit HKLs, four observations,
source references and summary are at NASolve anchor
`branch-artifacts/willow/w246-two-route-recut/`. Commands use the retained
`controller.py plan` followed by `controller.py run`, host Python 3.12 with
`PYTHONDONTWRITEBYTECODE=1` and the existing topology dependency path. The controller
is a local diagnostic; external inputs use the declared Cedar anchor and checksums,
not basename discovery. This is not a portable native-run claim. No datasets,
coordinates, reflection tables or generated checkouts are committed.

A compact local checkout reuses the existing Pine comparison viewer at GitHub
sibling anchor `ScienceCheckouts/Linden/2026-11-23_two-route-recut/index.html`.
Three HTML hashes and four local links pass; scene generation validates both
saved choices. Browser security blocked the local file URL, so **interactive
rendering was not revalidated**. No replacement coordinate file was emitted.
P03 remains partial: full reciprocal-space/native-policy/serialization and
physical interpretation are separate. **Both links being represented together
is not both links being refined together**; the P04/S05 coupled-fit gate remains
open, as do W241/W242's distinct receiving question and Cedar's restart work.


## W247 — Qualify serialization precision before a recut writer

W246 established the saved in-memory representation. W247 asks a smaller next
question: what survives existing coordinate writers and independent readers?
Each unchanged/compound packet is bound by its exact receipt and source hashes;
its existing `ReferenceFrame` transports every coordinate and all six Cartesian
U components. No source, prior packet, manuscript artifact or native model is
modified. Diagnostic derivatives stay local.

The first attempt deliberately stops when default Gemmi 0.7.5 mmCIF output
exceeds the declared **1e-6 Å² tensor-component bound**. Keep that failed plan,
first printed file and log. A separate observation records all default outcomes
under the same bounds, plus a control using Gemmi's existing CIF tables with
explicit **17-significant-digit XYZ/U fields**. This is a diagnostic precision
control, not a new production model writer.

| Compound recut | Format | Maximum coordinate-component error (Å) | Maximum U-component error (Å²) | Relative complex-Fcalc L2 error against represented memory |
| --- | --- | --- | --- | --- |
| 3LNA | PDB | 4.99950e-4 | 5.00679e-5 | 1.08080e-5 |
| 3LNA | default mmCIF | 4.93433e-8 | 4.19617e-5 | 5.25921e-8 |
| 3LNA | full-precision mmCIF control | 0 | 0 | 0 |
| 5LNA | PDB | 4.99828e-4 | 4.96358e-5 | 1.37393e-5 |
| 5LNA | default mmCIF | 4.91153e-8 | 5.00679e-6 | 4.89605e-8 |
| 5LNA | full-precision mmCIF control | 0 | 0 | 0 |

All twelve outputs preserve **1271/1275 ordered atoms**, residue/element/record
identities, occupancies/B, anisotropic inventory, cell and group in Gemmi.
Unchanged PDB controls are exactly unchanged numerically; default mmCIF can
still round float32 tensors in an unchanged model. The full-precision control
preserves the represented Gemmi state exactly, including both external links'
image-aware lengths. PDB link-distance changes stay below 0.0004 Å. None of
these thresholds grants structural acceptance.

A separate **Phenix 2.2.1-6174 / Python 3.11.15** read-only iotbx/cctbx pass
reopens all twelve files, checks identity/order before comparing, independently
reconstructs all Cartesian tensors, and calculates direct IT1992 structure
factors on the same 1484/2375 supplied indices. Written CIF numbers agree with
native scattering U within **3.56e-15 Å²** and XYZ within numerical round-off.
Native source-to-full-CIF Fcalc differs by about **2e-8 relative L2**: this is
consistent with passing the source through Gemmi's float32 atom tensors, and
must not be called exact preservation of native full precision. No Phenix
refinement, Coot execution or native dry-run is performed.

The initial native harness compared a default-sorted hierarchy against raw-order
scatterers in modified ATL residues. Its failure is retained. Explicit
`sort_atoms=False` and atom-label equality before every value comparison resolve
the harness error; it was not evidence that the coordinate file moved atoms.

**Connections are a separate contract.** These working sources have zero parsed
connection records, and the diagnostic outputs also have zero. Both intended
links remain bound to the saved graph, with the recut's correct operators and
measured distances. They have not been embedded in the coordinate files.
Absence of annotations neither removes intended chemistry nor creates a nick.
Likewise, preserving author atom identities does not qualify polymer/entity/sequence
metadata or an adopted whole-ASU layout.

Evidence resides at NASolve anchor `branch-artifacts/willow/w247-serialization/`
(first failed precision attempt) and `w247-serialization-observation/` (twelve
observations and independent native results). Frozen plans pin exact inputs,
runner files and dispatcher; the roadmap binds plan/summary/failure hashes.
Commands run the retained `runners/w247-serialization.py plan` then `run`,
`runners/w247-serialization-observation.py plan` then `run`, and the independent
`runners/w247-native-ordered-readback.py` with Phenix Python. Host observations
use `PYTHONDONTWRITEBYTECODE=1` and the existing topology dependency environment;
native readback additionally uses `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.
The first native harness is retained as `runners/w247-native-readback.py`.
No scientific artifacts enter Git; no test-suite or install repeat is warranted
for this evidence/docs-only update, with W245's 208/208 maintained-code validation
unchanged. These local diagnostics are not a portable native-run claim.

**Next small contract:** a read-only, exact-source/receipt-bound export observer,
with complete labelled mapping and declared precision, external intent separated
from actual annotations, and native source state separated from Gemmi state.
Qualify connection and polymer metadata before a production recut writer. P03
remains partial; simultaneous-cut force qualification and checkpoint restart stay
with their existing owners and prerequisites.


## W249 — Carry the whole boundary graph in full-precision mmCIF

W248 exposed a concrete export requirement: localizing two chosen joins creates
six image-spanning boundaries elsewhere. W249 tests complete metadata transport
using **the original full-precision paper mmCIFs**, separately bound to their
original source hashes. The working PDB receipt is not reused as authority for
changed source bytes or a differently named component.

Rowan supplied the declared `paper_r3` anchor (`LNA repair/R3 redeposition 2`),
relative coordinates `3LNA/9Z65_coordinates.cif` and `5LNA/9ZS1_coordinates.cif`,
and the original preparation receipts. The existing Cedar conversion explicitly
maps A1C3T to ACL only in the working PDB. Replaying that exact conversion reproduces
the frozen working PDB hash. The diagnostic preserves **A1C3T, every original atom
ID and author identity**, original B/occupancy and all six original U components;
ACL is used only to bind the working graph. Original entity types and sequence
scheme supply the metadata; no polymer type is guessed from an atom/component name.

Identity-image backbone edges define explicit directed paths. Every other edge
remains an explicit image-spanning declaration. The local projection refuses
incomplete atom coverage, branching or an uncut identity cycle rather than
inventing a path. The existing `ReferenceFrame` transports full double-precision
XYZ/U from the original CIF and checks its inverse. New diagnostic label/entity
and sequence assignments retain a per-node original-to-new mapping. All source
`struct_conn` rows—including hydrogen bonds—receive corresponding endpoint labels
and inverse image mappings. Previously undeclared exposed boundaries get their
own rows; already explicit boundaries are not duplicated.

| Original source | Atoms / logical nucleotides / unique backbone edges | Unchanged paths; ordinary/image edges | Recut paths; ordinary/image edges | Original connection rows retained; added rows | Native recut relative complex-Fcalc L2 |
| --- | --- | --- | --- | --- | --- |
| 3LNA | 1271 / 62 / 60 | 4; 58 / 2 | 8; 54 / 6 | 80 retained; 6 added | 1.051516e-15 |
| 5LNA | 1275 / 62 / 60 | 4; 58 / 2 | 8; 54 / 6 | 87 retained; 5 added | 7.995454e-16 |

One 5LNA boundary was already explicitly declared. Original hydrogen-bond rows
number 71/74; all remain and their physical endpoint positions agree within
4e-15 Å after image transport. Every original author field and atom ID rereads
unchanged, and all polymer labels match the bound lineage. Ordinary adjacency
plus the explicit declarations reconstruct **exactly the 60 original directed
backbone edges**, including their relative operators. This is a representative
change, not new chemical bond formation or a geometry repair.

Cedar's existing `cif_deposition_links.inspect_deposition_links` at
`92a280402957b1fdf869cccee0abeac224674961` reads the four diagnostic models,
checks the sequence tables and resolves all boundaries. No second annotation
parser is added. Independent **Phenix 2.2.1-6174 / Python 3.11.15** readback checks
all atom identities, modes/multiplicities, original IDs, B/Q, cell/group and full
Cartesian tensors. XYZ agreement is within 7.11e-15 Å and U within 3.56e-15 Å².
Direct IT1992 Fcalc uses all 1484/2375 supplied indices; unchanged controls are
exactly zero, and recuts agree at the near-round-off levels above. These are
complete read-only native calculations, **not refinements or dry runs**; no
observed amplitudes, Free flags or density were used to select the cut.

**Retained formatting failure:** the first four diagnostic files copied scalar
cell categories through Gemmi's generic category setter, producing one-row loops.
Gemmi accepted them, but iotbx refused `_cell_length_a` in a loop before scattering.
Those files/plan/log remain. A separate attempt preserves scalar category layout
without changing the numerical state, and all four independent native checks pass.
The check therefore qualifies this explicit output layout, not every valid-looking
CIF produced by a generic conversion.

**Connectivity controls:** on the 3LNA recut, removing one boundary row leaves
the standalone geometry reader at `CHECKED`, while comparing against the complete
bound reference reports the missing declaration and returns `REVIEW`. Replacing
its image with identity also returns `REVIEW`. Both altered files preserve exactly
the same native coordinates, tensors and Fcalc as the correct file. This reuses
Cedar's existing annotation-comparison behavior on the real recut: scattering
invariance and locally good geometry alone cannot prove the intended connectivity.

Evidence is local at NASolve anchors
`branch-artifacts/willow/w249-boundary-metadata/` (path projection and first attempt)
and `w249-boundary-metadata-format/` (scalar-layout retry, native readback, coverage
and negative controls). Plans bind original/working inputs, declared external
anchors, alias-conversion code, exact reader dependencies and outputs. Retained
runners are `w249-boundary-partition.py`, `w249-metadata-diagnostic.py`,
`w249-metadata-format.py`, `w249-native-readback.py`,
`w249-native-format-readback.py`, `w249-coverage-controls.py` and
`w249-negative-native.py` under `branch-artifacts/willow/runners/`.
Host runs use the existing Gemmi environment with `PYTHONDONTWRITEBYTECODE=1`;
native runs use `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
phenix.python -B RUNNER`. This is a local diagnostic, not a portable native-run
claim. Scientific coordinates and reports remain outside Git.

**Scope remains partial.** These files intentionally contain the diagnostic
coordinate/chemical/sequence/connection categories, with omitted source categories
listed in lineage receipts and immutable originals retained. They are not
submission-ready depositions. W248's maintained saved-PDB/single-block export
API is unchanged; W249 has a separate original-mmCIF binding and attached component
blocks. General source/alias import, full metadata preservation, special positions,
inverse editing, native refinement adoption and human review remain before a
supported ASU writer. No new force, fit, production code or test-suite repeat.
Cedar's separate 5W6W/PDU restart and its A112 phosphate-orientation diagnosis
remain distinct from these two R3 metadata controls.


## W251/W252 — Separate native output completion from local repair

**Question.** Can the declared image-spanning B7 O3′–B1 P connection close with
only its six connecting atoms movable, both sugar rings held and the original
phased diffraction/scattering inputs retained? This is one explicit registered
connection, not automatic seam discovery or a general repair result.

W251 used the W250 installed owner, original `7aade3c4…` parent, 3 cycles × 60
iterations, 1.5 Å displacement cap and native `wxc_scale=0.5`. The cycles ran;
Phenix 2.2.1-6174 then failed an assertion in optional `.def` output. Native
parameter formatting changed five of six selection strings by whitespace while
preserving every selected atom. It also rounded every fixed f-prime (maximum
change below 1e-9). The original parsed policy contains the exact source values.
The failed run retains raw native output but has no valid completed writer/return
receipt and no recorded target-call count; those facts cannot be repaired by
reinterpreting its files afterward.

W252 changes only the phased optional output setting to `write_def_file=False`.
It preserves normal native PDB/mmCIF/maps/geometry writing and all Cedar return
checks. The relocated installed replay completes in about 49 seconds. Frozen
scientific controls/inputs, admitted and prepared states and **all raw atom
records match W251 exactly**. The first host launch lacked optional Gemmi and
stopped before native execution; its separate failure is retained. There was one
actual output-only native replay, no scientific parameter search.

The successful return retains 859 atoms, 853 fixed positions, B/Q/U and all fixed
fp/fdp, 1,151 original HKL/HL/F/SIGF rows (only the permitted common native
amplitude/sigma scale) and 59 Free-R assignments. Actual MLHL target admissions:
97 evaluations/94 requesting gradients. Complete image-angle/torsion gradient
calls: 97, alongside the native bond and exclusions. Rwork/Rfree are
0.306743/0.342453; these are not a selection criterion or fixed-weight comparison.

The chemistry remains poor. Raw printed geometry reviewed independently by Hazel
shows O3′–P 3.0285→1.9966 Å, B7 C3′–O3′ 1.442→1.772 Å, P–OP1/OP2
1.795/1.715 Å and OP2–P–O5′ 101.4→58.15°. Maximum movement is 0.631342 Å
(full precision). The output-only fix reproduces the same distortion, so technical
completion does not rescue this candidate. Hazel’s independent full returned-state audit passes 4,720 cold checks and
confirms the strain (full-precision O3′–P 1.997399 Å). Maps, stacking and broader
closure remain unaccepted. Its first reader invocation refused an additional
current Cedar source hash; the separately reviewed receiver explicitly binds
the already-present opt-in reader, without relaxing numerical bounds.

**Next discriminator.** After that audit, one same-parent geometry-plus-tether
trial may test the six-role scope using the existing masked native objective,
registered phosphate owner and fixed rings. Preserve finite-derivative/live-state
checks and source binding. A failed start is not proof of geometric impossibility;
a healthy endpoint is only a seed candidate. No weight grid or automatic mask
expansion. Keep the separate outward-phosphate whole-model child out of this ancestry.

**Validation/compatibility.** 213 source and 213 relocated installed tests (two
skips outside Phenix), plus the real native PHIL regression in source and installed
contexts; it fails at the expected output setting on the previous code. 214
relocated files hash-match after original build/install paths are removed.
No full suite rerun, force/default-ML change, request migration or job portability
claim. Additive failed-phase target counts mean admitted calls, not successful
native completion. Exact commands and versions are in the current handoff and
`branch-artifacts/willow/w252-validation-qualified/validation.json` under the
NASolve artifact anchor. Native jobs/diagnosis are in `w251-phased-junction-fit/`
and `w252-phased-output-qualified/` under `branch-artifacts/willow/`. All scientific
inputs, coordinates and reports remain local; only code, tests and documentation
are committed. S05/S06 remain PARTIAL.


## W253 — Audit a motion-limited geometry trial without claiming an optimum

**Purpose.** Distinguish the W252 data/geometry compromise from the ability of
this same six-role local window to improve chemistry. Earlier W235/W241 controls
use different parents; they do not answer this exact FT parent question.

Hazel ran one predeclared geometry-plus-source-tether diagnostic on the original
`7aade3c4…` parent, both rings fixed, same six roles and registered image terms.
The existing `NativeMaskedObjective(include_pairs=False)` and bounded native
trial are composed under Cedar's active phosphate owner. The optional full-native-
crystal binding is explicitly frozen from Alder; no implicit Willow merge or
standalone support claim. Native phases/scattering are held and observed but
contribute no diffraction objective. Tether sigma is 0.5 Å, motion cap 1.5 Å,
100 iteration/300 optimizer-call/600 total-evaluation budget, 600-second owned
wall cap; Phenix 2.2.1-6174. No new optimizer or production worker is introduced.

The owned diagnostic stops after about 178 seconds. Its embedded optimization
is **FAILED**, because a proposed unconstrained L-BFGS step exceeds the motion
cap after 12 accepted steps and 14 evaluated optimizer points. The outer complete
receipt means the diagnostic recorded/restored its state, not optimizer success.
All source/code pins, native manager, live model/scattering/data and shared
preflight source remain unchanged. No geometry candidate PDB is emitted.

The existing failed-endpoint observer replays the last accepted point exactly.
Initial/full/rounded derivatives pass, maximum error 6.70e-5 against 1e-3;
236 total evaluations include those audits. Independent failure review passes
1,789 checks. At this diagnostic point:

| Quantity | Last accepted value | Native target |
| --- | ---: | ---: |
| Image O3′–P | 1.616792 Å | 1.607 Å |
| B7 C3′–O3′ | 1.487373 Å | 1.435 Å |
| OP2–P–O5′ | 85.662° | 108° |
| C5′–C4′–C3′ | 124.638° | 114.1° |

Native whole-model geometry sum falls from 20739.428 to 6779.382; the final tether
term is 29.023. These sums are not acceptance scores; many fixed terms contribute.
Largest accepted movement is 1.479672 Å. The remaining coordinate-gradient norm
is about 1306. **This is not a constrained optimum at 1.5 Å.** The rejected
proposal is not recorded, so the violating atom and amount cannot be reconstructed
from the accepted trace. No inference that a larger mask/bound is required, no
claim of convergence and no proof of geometric impossibility follows.

**Cold necessary reach check.** Original fixed image C3′ to P is 4.142861813 Å.
The three exact native ideals C3′–O3′ 1.435 Å, O3′–P 1.607 Å and included angle
119.7° imply C3′–P 2.631876511 Å by the law of cosines. The reverse triangle
inequality therefore requires P movement of at least 1.510985302 Å to meet all
three exact ideals. This exceeds the arbitrary trial cap by only 0.010985 Å;
it is not a physical rejection criterion. Illustrative one-/three-native-width
boxes give necessary minimum movements 1.473467/1.398531 Å, within the cap.
Those boxes are sensitivity illustrations, not acceptance thresholds or joint
confidence intervals. Other sugar/oxygen constraints, chirality, sterics and
diffraction are omitted, so passing this necessary test proves no feasible bridge.
No new native evaluation, coordinate change or altered policy accompanies it.

**Next.** First retain exact rejected-proposal provenance through the existing
trial recorder, preserving refusal semantics. Review chemical placement against
fixed sugar frames before choosing a new initialization or motion parameterization.
Any next experiment must declare its parent, role mask, bound/tether, native terms
and comparison in advance. No automatic limit relaxation, repeated cap/weight
search, mask expansion or additional native run tonight. Complete integration
suite remains a pre-merge requirement; no full pass is claimed for this slice.

**Inspection/evidence.** Under the GitHub anchor, open
`ScienceCheckouts/Linden/2026-11-23_phased-junction-boundary/index.html` or
`open_comparison.py`. The latter verifies original/fit hashes and the exact failed
receipt, then displays last-accepted points on a temporary in-memory copy. Three
859-atom models, all six toggles and image gaps 3.028533/1.996554/1.616792 Å pass
ChimeraX 1.12 headless checks. GUI/browser appearance is not newly qualified.
Thirteen link/hash/syntax checks pass. Hazel's two-state map image is reused with
its exact provenance and diagnostic-map limitations; no duplicate FFT or candidate
file is written. Raw files stay local under the NASolve anchor at
`branch-artifacts/Alder/a01-phosphate-geometry-feasibility-20261123-01/` and
`branch-artifacts/willow/w253-{chimerax-check,checkout-validation,geometry-reach}.json`.
This is evidence/docs only; no new production code, schema or scientific acceptance.
S05/S06 remain PARTIAL.

## W255 — Record the coordinated cap and feasible-step diagnostics

Hazel completed the predeclared original-parent 1.5→2.0 Å cap comparison using
the same six atoms, held rings, 0.5 Å tether, chemistry, budgets and Phenix
2.2.1-6174. It stopped after 27 accepted steps/29 optimizer evaluations:
OP2 proposed 2.0491108 Å versus the last accepted 1.9719141 Å. The last step has
O3′–P 1.615456 Å, C3′–O3′ 1.4598 Å and OP2–P–O5′ 107.340°. There is no candidate
or constrained optimum. The 1,797 cold checks and 21 local-term checks show the
angle penalty falling 55.44→0.048 and outward radial derivative −157.65→−1.51;
the rejected proposal does not prove that a larger displacement domain is needed.
Two prior resource-copy preparation failures remain distinct from this one fit.

A separate private projected-gradient diagnostic kept the 2 Å balls, original
parent and objective. It reached 100 iterations/209 search evaluations in 189 s,
stopping at the iteration limit with projected residual 5.1565. All 3,154 cold
checks pass, with no out-of-domain objective calls. Centered endpoint probes are
unavailable at the active cap; the rounded PDB point is outside the cap. A separate
read-only 75-evaluation feasible-basis audit completed in 55 s and reproduced the
saved scalar/gradient exactly; largest derivative error is 4.963e-5 against 1e-3.
This checks forces, not stationarity or serialized-model acceptance.

Alder now owns the optional pure search/audit helpers at
`7c2e1c41d969db7b047b242d847bf18ace49b531`: 53 focused, 99 adjacent, 53 installed
tests and 531 cold replay assertions. Linden's independent review caught/refused
collapsed finite-difference probes and retained successful partial probes on
failure. Replay reproduces saved calls, not new native evaluations. These modules
are not imported or merged into Willow by this update; ordinary trial defaults
are unchanged. Native adapters, exact source identity, deadlines and output
qualification remain caller-owned.

The next gate separates convergence, force correctness, chemistry and actual
serialization. Scope an explicit opt-in boundary-endpoint contract before any
receiving candidate: preserve old centered `UNAVAILABLE`, independently qualify
feasible-basis derivatives and the serialized point's own geometry/gradient/
projected residual. First inspect high-precision mmCIF receiving support; any
PDB lattice choice is a separate encoding proposal requiring fresh evaluation,
not silent clipping or reuse of the old gradient. No cap grid, automatic mask
expansion, diffraction receiving or acceptance follows from this audit.

Evidence stays local under the NASolve anchor:
`branch-artifacts/Alder/a01-phosphate-cap-comparison-20261124-03/`,
`a01-feasible-step-native-20261124-01/`,
`a01-feasible-basis-native-20261124-01/` and
`a01-feasible-maintained-20261124-01/` (the latter three share the same
`branch-artifacts/Alder/` parent). The existing human checkout under the GitHub
anchor is `ScienceCheckouts/Hazel/2026-11-24_feasible-helper-extraction/index.html`.
This is coordinated evidence, not a duplicated Linden experiment.

## W256 — Preserve original CIF precision in a maintained recut source context

The [original-CIF source reader](topostitch-preview.md#bind-an-original-mmcif-to-a-saved-working-recut-w256)
formalizes the source-binding slice of W249. Original bytes, atom IDs, component
names and raw double XYZ/U survive; the explicit A1C3T→ACL alias only matches the
working-PDB graph. A separate original-source digest owns the frame. Attached
component blocks and category layouts remain available for subsequent metadata
work. The working-file error limits are explicit, not an implicit source rewrite.

Four cold real-data replays cover 3LNA/5LNA unchanged and both-route cuts. All
1,271/1,275 atoms map exactly once. Compiled raw XYZ and Cartesian U reproduce
W249 expected values with **zero component difference** in all four cases.
Maximum original-to-working errors are 0.0005 Å coordinates, 0.00005 Å² U,
0.005 Å² B and zero occupancy difference. This is exact replay of earlier
unrefined numerical states; no new Fcalc, Phenix, refinement or coordinates are
generated. Original files remain unchanged. The first local replay predates the
symmetry-table admission check; the separately pinned final replay uses the
qualified source. Do not relabel the first result as the final-code check.

Focused command, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<qualified-test-dependencies>`:
`python -m pytest -p no:cacheprovider -q tests/test_topostitch_cif_source.py
tests/test_topostitch_scattering.py tests/test_topostitch_recut_bundle.py
tests/test_topostitch_recut.py tests/test_topostitch_transport.py`.
217 source tests pass; the same 217 pass from the relocated installation after
removing the temporary source build and old installation location. The complete Willow suite ran: 2,688 passed, four skipped and 234 subtests passed; five campaign-process tests failed because sandbox process inspection/signaling was denied. Those same five passed with permission (2.48 s), unchanged source. This clears all 2,693 tests across the run and retry, not a single clean full invocation or a combined-branch integration result. Hazel's exact-hash independent cold review has no blocking finding. Original-source relocation is also exercised with its old path gone.
Exact commands, hashes, logs and source replay are under the NASolve anchor
`branch-artifacts/willow/w256-source-cif-context/`. Task-owned disposable build/
installation files were removed; private scientific data is excluded from Git.

P03 stays **PARTIAL**. The next maintained slice must bind complete polymer paths
and every original connection type to this source context and the proposed cut,
reusing Cedar's deposition-link reader/comparison. An annotation-only omission
can preserve Fcalc and pass an incomplete standalone check. Required P02 GUI,
inverse edits, refined-child rebinding, supported writing, special-position
source validity and the native refinement lifecycle remain separate gates.

## W257 — Account for original sites and every declared backbone edge

The [maintained path projection](topostitch-preview.md#project-declared-paths-onto-original-cif-sites-w257)
uses W256's original-source binding and the replayed graph. It encodes each
declared covalent edge exactly once, either as local adjacency or as an explicit
image-spanning connection. All registered nodes map to complete original CIF
sites; component aliases never overwrite original labels. Unregistered atoms,
protected sites and original chemical/unknown boundary intentions stay visible.

| Source | Original atoms / registered nucleotides / backbone edges | Before: paths, local edges, image edges | Two-route recut: paths, local edges, image edges |
| --- | --- | --- | --- |
| 3LNA | 1,271 / 62 / 60 | 4, 58, 2 | 8, 54, 6 |
| 5LNA | 1,275 / 62 / 60 | 4, 58, 2 | 8, 54, 6 |

All four source-bound path/node sequences and boundary operators reproduce the
earlier W249 diagnostic exactly. A1C3T remains A1C3T. This is a change in how the
same crystal is represented, not a new chemical nick or physical bend. The new
API writes no model and performs no Fcalc/native call. Original annotations
remain preserved in the W256 document, but are not yet re-expressed by this API.

**Validation:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<qualified-dependencies>
python -m pytest -p no:cacheprovider -q tests/test_topostitch_cif_paths.py
tests/test_topostitch_cif_source.py tests/test_topostitch_recut_bundle.py
tests/test_topostitch_graph.py` passes 121 tests, and the same 121 pass from a
relocated offline installation. The complete `python -m pytest -p no:cacheprovider
-q` run, with process permissions available, passes **2,705 tests, four skips and
234 subtests**. No branch merge is implied by this Willow-only suite.

The first test fixtures incorrectly aliased multiple author sites and assumed
equal strand lengths; those fixture failures remain. A separate negative test
demonstrated a real prototype gap: different components could occupy the same
original label-chain/sequence position. The maintained binding now refuses that
collision; branch/cycle, partial-source, unregistered-context and relocated/race
controls also pass. Hazel then identified an unregistered atom with missing entity metadata that
could hide a collision at a known position. Its regression fails before the fix;
position occupancy now includes incomplete metadata rows. Revised source, all
four real replays, installation and full suite pass, and Hazel confirms the
exact-hash fix. Prior formatting and replay-harness failures remain retained;
none is relabelled as a scientific result.

Exact source/review hashes, logs, replay, installation/cleanup and restart records
are local under NASolve anchor
`branch-artifacts/willow/w257-original-path-projection/`. Scientific files remain
outside Git; task-owned disposable installations are removed. P03 stays partial.
Next, transport **all** original connection rows through original atom/image
lineage, retaining explicit reasons for unresolved/out-of-scope endpoints. Reuse
Cedar for covalent chemistry/sequence semantics and compare against the complete
bound reference. Its O3′–P-specific checker is not an all-annotation parser.
No automatic row deletion, chemical inference, supported writer, edited-child
rebinding, P02 GUI acceptance or native receiving is introduced here.
