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

## Current validation receipt — 2026-11-13

**W38 checkpoint (2026-11-14):** the new 11 mask regressions verify exact fixed
coordinates, explicit variable ordering, motion limits and independent numerical
derivatives that include interactions with fixed atoms. Focused mask/transport/
recipe tests: **45 passed** (1.26 s). Full source: **1,323 passed + 229 subtests**
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
