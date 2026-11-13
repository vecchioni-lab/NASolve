# TopoStitch backend slice 1: explicit end candidate screening

Implemented on Willow, 2026-11-13. This is a small pure-Python backend API,
not an installed CLI command or an automatic structural interpretation tool.
The broader [TopoStitch design](topostitch.md) remains the implementation plan.

## What it does

`nasolve.topostitch.DuplexEnd` records one explicitly identified duplex end:

- `end_id`: stable caller-defined identifier (not inferred from a chain name);
- `sequence`: exposed overhang sequence written 5-prime to 3-prime, uppercase
  A/C/G/T only, or `None` for unknown/unsupported chemistry;
- `polarity`: `5prime` or `3prime`, the kind of overhang;
- `position`: three finite Cartesian coordinates in Angstrom, representing a
  consistently defined duplex-end reference point in a shared frame;
- `state`: `available`, `connected`, `free` (explicit do-not-connect), or `unknown`.

`propose_connections(ends, source_model_sha256=..., max_distance_angstrom=...,
max_pairs=100000)` screens available ends for same-polarity, exact full-length
reverse complements within the supplied distance bound. Two complementary
5-prime overhangs can associate, as can two complementary 3-prime overhangs.
Sequence indices in `residue_pairs` are zero-based within the supplied 5-to-3
strings. They are not coordinate residue numbers or atom restraints.

The search bound is a caller-selected screening radius, not a default chemical
ideal or proof of geometric reachability. Partial overlaps, shifted registers,
noncanonical pairs, handedness and orientation are not analyzed. `None` does not
become a wildcard; unsupported sequences are excluded. Malformed records fail
before inference. Duplicate identifiers are rejected. Inputs are immutable and
the report contains a detached JSON-compatible input snapshot.

Connected/free/unknown ends remain visible with their exclusion reason. Multiple
partners are retained, including competition for a shared partner. Even a lone
candidate is `SINGLE_CANDIDATE_NOT_CONFIRMED`; no end is declared definitively
dangling and no connection is adopted. Exceeding the pair budget raises an error
without a misleading partial report. Zero eligible ends is a normal result.

## Descriptive report schema 1

Kind: `topostitch-end-candidate-report`; algorithm:
`canonical-full-overhang-screen-v1`. It contains:

- supplied source model SHA-256 and `source_bytes_verified=false`;
- the exact normalized inputs and a deterministic SHA-256 over their canonical
  sorted-key compact JSON encoding;
- all candidate pairs with distances and positional sequence pairings;
- per-end outcomes and competing partners;
- explicit limited search scope and limitations;
- `selected_candidate=null`, `no_connection_alternative=true`,
  `runtime_authority=false`, `inspection_required=true`.

The function does not read a model file or validate its hash. The future input
adapter must verify bytes and bind the supplied end records to the exact model,
logical registration, coordinate sites and evidence before operational use.
This report is not a reusable connection scheme or approval manifest. There is
no loader or persisted run artifact yet, and no operational filesystem paths.
Input order does not affect the report. The fingerprint is input identity, not
scientific validity, digital signature or a substitute for provenance checking.

## Integration boundaries and next patches

No CLI, campaign recipe, checkpoint, PostMR, Cedar, dependency or native tool
interface changes. Existing imports/commands retain their behavior. The API can
be imported from a standard NASolve wheel and uses only Python's standard library.

Next add a source-verified adapter that derives end records and full oriented
frames from explicit logical registration plus coordinate evidence. It must not
turn every PDB chain terminus into a sticky end. Periodic partner search then
needs actual cell/symmetry, image identities, reciprocal/orbit handling, search
completeness and tests for equivalent representations. Those features should
not be simulated by passing duplicated image records to this first API: it has
no periodic-equivalence semantics. Geometry feasibility, recuts, deformation,
Cedar construction and campaign proposal adoption require separate patches.

## Validation and compatibility

Before this change the new regression file failed at collection because
`nasolve.topostitch` did not exist. After implementation the focused suite passes
39 cases, including competing partners, nearest incompatible ends, protected
ends, sequence/polarity/register/distance limits, provenance input validation,
determinism, input immutability, empty input and budget exhaustion.

From the Willow checkout, using the existing interpreter read-only:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" -m pytest tests/test_topostitch.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" -m pytest -q -p no:cacheprovider
git diff --check
```

`NASOLVE_TEST_PYTHON` denotes the existing NASolve Python 3.12.14 environment
with pytest 9.1.1; it is a validation environment, not an operational artifact
reference. Complete suite: **1006 passed + 226 subtests**, 63.87 seconds.
Focused source suite: **39 passed**, 0.03 seconds. No native Phenix/Coot execution or scientific validation is
claimed. Fixtures are synthetic records; no generated scientific data or local
workspace state is included. No old runtime schema migration is required.


Wheel validation used a disposable environment without installing dependencies
(the new primitive itself is standard-library-only). This checks wheel packaging
and the backend, not full external-tool/dependency provisioning:

```sh
"$NASOLVE_BUILD_PYTHON" -m pip wheel --no-deps --no-build-isolation --wheel-dir /private/tmp/willow-topostitch-wheels .
"$NASOLVE_BUILD_PYTHON" -m venv /private/tmp/willow-topostitch-install
/private/tmp/willow-topostitch-install/bin/python -m pip install --no-deps /private/tmp/willow-topostitch-wheels/nasolve-0.1.0-py3-none-any.whl
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/willow-topostitch-install/lib/python3.12/site-packages "$NASOLVE_TEST_PYTHON" -m pytest tests/test_topostitch.py -q -p no:cacheprovider --import-mode=importlib
```

`NASOLVE_BUILD_PYTHON` was the existing disposable TopoTrace build interpreter
(Python 3.12.14, setuptools/wheel); its environment was not modified. The final
installed-wheel test was invoked from outside the source checkout with an
absolute test-file path: **39 passed**, 0.03 seconds. A separate `python -I`
smoke check confirmed import from the disposable environment's `site-packages`,
JSON serialization and a complementary candidate with no automatic selection.
The temporary paths above are validation provenance only. No source relocation
or runtime-artifact portability change is part of this slice.
