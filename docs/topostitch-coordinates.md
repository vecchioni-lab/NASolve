# TopoStitch backend slice 2: verified coordinates and end frames

Implemented on Willow, 2026-11-13. This read-only adapter connects explicitly
assigned PDB sites to the [canonical candidate screen](topostitch-backend.md).
It is not automatic duplex detection, a general registration compiler, a
symmetry finder or a repair engine. It adds no CLI or campaign execution option.

## API and authority

`nasolve.topostitch_coordinates.ResidueSite(chain, residue_number,
insertion_code="")` identifies an exact coordinate site. Blank chain is `""`;
insertion codes are explicit. Decimal PDB numbering is supported, not hybrid-36.

`EndAssignment(end_id, overhang_sites, terminal_pair, inner_pair, polarity,
state="available")` records caller-declared topology:

- Overhang sites are explicitly in chemical 5-prime to 3-prime order. Coordinate
  line order and residue numbering never establish this order.
- Each pair lists strand 1 followed by strand 2. The terminal pair borders the
  overhang; the inner pair is the next paired step toward the duplex interior.
- `polarity` and `state` have the same meaning as the first backend slice.
- Each assignment uses distinct sites. Overhang sites cannot be shared between
  two end assignments. Caller-owned mutable lists are copied to immutable tuples.

`inspect_end_assignments(model_path, assignments, expected_sha256=...,
max_distance_angstrom=..., max_pairs=100000)` reads the exact supplied path once,
checks its bytes against the expected SHA-256, and assesses those same bytes.
It performs no input discovery or writes. It returns schema-1
`topostitch-coordinate-end-report`, including the verified model hash and size,
a detached assignment snapshot/hash, end assessments and the underlying screen.
No source path is emitted; identical bytes and assignments give the same result
when moved/renamed. Caller checkpoint/run context must supply the anchored model
reference for any later viewer or consumer. A hash alone is not a locator.

The assignment manifest is explicit topology intent, not proof of pairing,
terminal status, strand adjacency, direction, sugar chirality or chemical
connectivity. The future logical registration adapter must supply and validate
those facts. This interface does not yet accept NASolve's construct-registration
artifact directly. It never infers a sticky end from a PDB chain boundary.

## Conservative coordinate handling

Accept one implicit or explicit MODEL only. Reject multimodel or malformed
coordinate data rather than mixing structures. ATOM and HETATM canonical DA,
DC, DG and DT are treated alike at the selected sites. Normalize the legacy
sugar-star spelling to prime, with collisions reported as ambiguous atoms.

Selected residues require unambiguous canonical identities, the six-membered
base ring N1/C2/N3/C4/C5/C6 and C1-prime, and positive finite occupancy no greater
than one on these atoms. Missing/unsupported residues, alternate conformers,
duplicate atom names, repeated identities across TER segments, missing required
atoms and unusable occupancies leave the affected end `UNASSESSED` with a reason
code and site. Other usable ends can still be reported. The adapter does not
choose a highest-occupancy conformer or complete missing atoms. Full phosphate,
sugar, base-substituent and covalent continuity checks remain unimplemented.

Declared terminal and inner pairs must be canonical A:T or G:C combinations in
either orientation for this first scope. This is a scope restriction, not a claim
that other pairs are impossible. Noncanonical recipes need a separate adapter.

## Descriptive reference frame

For each selected base, calculate the centroid and polygon-area normal of its
ordered six-membered ring. Align the two terminal normals and normalize their
sum. Choose its sign toward the exterior using the terminal-to-inner pair
center relationship. Project the terminal C1-prime-to-C1-prime vector into the
plane to define x; y is z cross x. The origin is the mean of the two terminal
ring centroids. Axes are unit vectors; positional quantities are Angstrom.

The resulting right-handed reference frame is a coordinate convention, not an
inference of DNA handedness. Its convention is explicitly named
`terminal-six-ring-area-normal-v1`; it is **not a standardized 3DNA frame**.
Report the two ring planarity RMS deviations and terminal inter-plane angle as
observations, without calling them chemically acceptable. Numerical degeneracy
or an indeterminate outward normal leaves an end unassessed. The tolerances
only guard normalization/sign determination; they are not allowed DNA bends.

Frame calculation does not validate stacking, helicity, groove placement,
backbone reachability or the caller's assignment. The downstream initial screen
uses the origin and actual coordinate-derived overhang sequence; it does not
apply orientation cutoffs yet. Coordinate-frame availability is therefore
separate from `geometry_validated`, which remains false.

The nested primitive screen still says `source_bytes_verified=false` because
that function itself performs no I/O. The enclosing coordinate report records
the actual byte verification; both reports bind the same source digest.

## GUI-facing distinction between proposed and done

The report includes orthogonal fields:

- `workflow.proposal_state`: `NO_CANDIDATES`, `CANDIDATES_FOR_REVIEW` or
  `INCOMPLETE_ASSESSMENT`;
- `workflow.execution_state`: always `NOT_ATTEMPTED` for this API;
- `workflow.review_state`: always `UNREVIEWED` for this API;
- `changes`: always an empty list;
- `runtime_authority=false`, `inspection_required=true`.

These are observations, not a permission token or writable state machine.
An incomplete end assessment stays visible even if other candidates exist.
A zero-candidate result means none within this explicit scope, not that a
structure has no dangling ends or periodic connections. Later construction and
review stages must produce their own immutable receipts; a frontend cannot
turn this report into a completed repair by changing a status string.

## Validation, compatibility and next work

Synthetic planar-ring fixtures test coordinate extraction, checksum refusal,
explicit/implicit models, HETATM, missing/ambiguous atoms, alternate conformers,
occupancy, insertion codes, naming aliases, numerical degeneracy, rigid
transforms, renaming/reordering, exact sequences, two-end candidate screening,
partial results and immutable assignments. These fixtures validate the algorithm,
not DNA chemistry. A relocation test removes the original input directory and
confirms an identical report from the moved, renamed model.

The new test file failed before implementation with the missing module. After
implementation the two TopoStitch test files pass 72 cases. No native tool runs,
real coordinates, maps or diffraction inputs were used. Standard-library-only
code leaves Cedar, existing CLI/recipes and checkpoint schemas unchanged.

Next: validate logical strand/pairing assignments against registration and
backbone evidence, add coordinate-driven duplex-end detection, and introduce
qualified periodic image enumeration. The [GUI contract](gui.md) specifies how
proposals and eventual execution/review receipts fit into Campaign desk.


## Validation receipt — 2026-11-13

The exact validation commands were run from Willow using the existing NASolve
Python 3.12.14 / pytest 9.1.1 environment read-only (denoted here by
`NASOLVE_TEST_PYTHON`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" -m pytest tests/test_topostitch_coordinates.py tests/test_topostitch.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" -m pytest -q -p no:cacheprovider
git diff --check
```

Results: **72 focused passed**; **1039 full passed + 226 subtests** in 62.97 s;
diff check passed. JSON authority assertions and 66 local documentation links
passed an ephemeral read-only check. The coordinate-adapter test file failed
before implementation with `ModuleNotFoundError`, as expected.

Wheel build/install used the existing disposable build interpreter
(`NASOLVE_BUILD_PYTHON`) without modifying shared dependencies:

```sh
"$NASOLVE_BUILD_PYTHON" -m pip wheel --no-deps --no-build-isolation --wheel-dir /private/tmp/willow-coordinates-wheels .
"$NASOLVE_BUILD_PYTHON" -m venv /private/tmp/willow-coordinates-install
/private/tmp/willow-coordinates-install/bin/python -m pip install --no-deps /private/tmp/willow-coordinates-wheels/nasolve-0.1.0-py3-none-any.whl
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/willow-coordinates-install/lib/python3.12/site-packages "$NASOLVE_TEST_PYTHON" -m pytest tests/test_topostitch.py tests/test_topostitch_coordinates.py -q -p no:cacheprovider --import-mode=importlib
```

The installed test invocation ran outside the checkout, using absolute paths to
the two test files: **72 passed** in 0.12 s. A separate isolated `python -I`
check verified imports from the installed `site-packages` and constructed an
explicit assignment. This tests the standard-library-only backend package,
not clean provisioning of NARestraints or external Phenix/Coot dependencies.
Temporary absolute paths above record validation provenance only.

Before: callers had to supply sequences and positions without a verified input
adapter. After: an exact-checksum PDB plus explicit site assignments produces
coordinate-derived sequences, descriptive frames, per-end diagnostics and
honest proposal/execution/review states. New source and tests are
`src/nasolve/topostitch_coordinates.py` and `tests/test_topostitch_coordinates.py`.
The additive coordinate-report schema does not change the original screen
schema, checkpoint formats or existing recipes. No migration is needed. GUI,
intent, index, changelog and handoff documents record implemented versus future
capabilities. No generated scientific artifacts are included.
