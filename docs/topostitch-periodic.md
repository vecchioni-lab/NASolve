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
