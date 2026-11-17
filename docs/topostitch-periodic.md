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

A separate complete Phenix2.2.1-6174 synthetic diagnostic uses the installed wheel:
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

The installed W82 wheel is exercised under **Phenix2.2.1-6174**, using only five
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
**Phenix2.2.1-6174** through Cedar's owned process runner with a 600-second ceiling.
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

Cedar should expose a **separate active-callback admission/check API** using the
same native profile, exact-type reader and complete policy traversal as C331.
Factor internal traversal only if needed; keep C331's callback-free signature,
policy identity, records, refusal behavior and old installed replay unchanged.
Do not copy `_Reader` or shell/symmetry/parameter inventory logic into Willow.
The active record needs its own versioned policy identity and truthful invocation
fields; it must not call C331 with fabricated callback-free arguments or detach
an installed callback merely to inspect the manager. Cedar chooses final API names.

For admission diagnostics, start with one narrow configured-callback route: the geometry manager contains
the exact callback object created by the checked runtime owner, and the per-call
`external_energy_function` argument remains `None`. Reject competing configured
or per-call callbacks, extension objects, custom nonbonded functions, externally
supplied gradient buffers and unsupported geometry flags. The model-level native
owner forwards its own buffer into geometry; authenticate that ownership boundary
rather than rejecting every non-None buffer at the inner layer. Invocation-only and
arbitrary third-party callback routes are separate future qualifications. This
diagnostic route does not decide the counted production-contribution mechanism.

A serialized digest does not authenticate a callable. The runtime factory must
be trusted code frozen through the existing execution request, with helper/profile
checksums and explicit construction. The active check compares the actual callback
object with that runtime-owned object and binds its frozen contract digest; it
never imports code or resolves a callable named by an untrusted record. A function
name, object address or class name alone is not persistent proof. After restart,
the frozen runtime factory must rebuild and authenticate its new process-local
callable; a serialized object identity cannot be reused. Single-owner
execution is required; before/after snapshots are not a concurrency lock.

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

The first profile admits energy-only calls and native-owned Cartesian gradient
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
