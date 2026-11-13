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

## Records and compatibility

New descriptive kinds are `topostitch-periodic-candidate-report` and
`topostitch-periodic-coordinate-report`, each schema 1. The strict input manifest
is also schema 1 but has a different kind. No old report, checkpoint, campaign
recipe or frozen attempt is migrated or reinterpreted. The installed inspector
is additive; the default NASolve dependency set is unchanged. Source changes are
isolated in new TopoStitch modules plus package metadata. Cedar's code, selected
bundles and publication interfaces are not consumed or modified.

No generated scientific data are included. Tests use synthetic endpoints and
synthetic PDB rings; no physical repair, Phenix/Coot execution or real diffraction
validation is claimed. Next: automatic/registration-backed end detection, full
image distinctness and global pairing constraints, then qualified geometry work.

## Validation basis

Focused tests compare the bounded search with an independent brute-force image
enumeration for P1, P21, P212121, P43, R3:H and P63, including centering,
non-orthogonal cells, screw operations, large cell shifts and cutoff boundaries.
They verify reciprocal operators, endpoint reimaging, self-edge capacity warnings,
frame transformations, budgets, missing-extra behavior, strict manifests, source
drift, SCALE/CRYST1 handling and relocation after the original model is removed.

The two new test modules first failed at collection with `ModuleNotFoundError`
because their backends did not exist. Final validation on 2026-11-13 used Python
3.12.14, pytest 9.1.1 and optional Gemmi 0.7.5:

| Check | Result |
| --- | --- |
| Complete source suite, topology extra available | **1,099 tests + 226 subtests passed**, 53.33 s |
| Four TopoStitch modules against installed wheel | **132 passed**, 0.61 s |
| Four TopoStitch modules from relocated temporary checkout, original temporary checkout absent | **132 passed**, 0.61 s |
| Installed command on synthetic PDB and assignment manifest | Verified periodic JSON, no changed input files |
| Same installed command after moving inputs and renaming PDB, old input directory absent | Identical report |
| Lean wheel without Gemmi | Nonperiodic command passed; periodic request exited 2 with actionable extra-install error and no partial stdout |
| Isolated installed import and package metadata | Imported wheel modules; both entry points and optional extra present |
| Python 3.10 parser syntax check | Passed; this is not a Python 3.10 runtime test |
| `git diff --check` and intent/Markdown references | Passed |

Exact full-suite invocation from the Willow checkout (paths below are historical
validation provenance, not operational model references):

```sh
NASOLVE_TEST_PYTHON=/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$NASOLVE_TEST_PYTHON" - <<'PYTEST'
import sys
sys.path.append('/private/tmp/willow-periodic-deps')
import pytest
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider']))
PYTEST
```

The optional dependency was installed only under `/private/tmp`; the shared
NASolve/Cedar environment was not changed. A disposable build environment built
`nasolve-0.1.0-py3-none-any.whl` with `pip wheel --no-deps --no-build-isolation`.
Two fresh virtual environments installed that wheel with `--no-deps`; one also
installed Gemmi 0.7.5. This checks the new inspector's packaging and isolated
optional-dependency behavior, not a fresh provisioning of Phenix, Coot or the
existing NARestraints dependency.

The exact installed test invocation used:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/private/tmp/willow-periodic-install/lib/python3.12/site-packages \
"$NASOLVE_TEST_PYTHON" -m pytest \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/tests/test_topostitch.py \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/tests/test_topostitch_coordinates.py \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/tests/test_topostitch_periodic.py \
  /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve-linden/tests/test_topostitch_inspect.py \
  -q -p no:cacheprovider --import-mode=importlib
```

That command ran from `/private/tmp`, with isolated `python -I` checks verifying
installed module origins. Relocation testing copied the tracked checkout plus
this patch into a temporary clone, renamed its directory, asserted the old path
was absent, verified imports originated in the relocated `src`, then ran the
same four test files with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` and the
optional Gemmi directory appended. No live-run inputs were copied or published.
No external crystallographic tools ran, so there is no Phenix/Coot version or
native refinement result for this patch.

Gemmi API references used for this implementation:
[symmetry operations](https://gemmi.readthedocs.io/en/latest/symmetry.html) and
[unit-cell transforms](https://gemmi.readthedocs.io/en/latest/cell.html).

Contact-layer validation (2026-11-13): the new test module first failed at import
before implementation. The five TopoStitch test files then passed **143 tests**
with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, using the same test interpreter
and optional Gemmi path shown above. Checks include role remapping/provenance,
partial contacts, degenerate angles, exact screw-image atom transforms, rigid
transforms, no-write CLI behavior and relocation with the original path absent.
This isolated additive inspector change did not alter global mechanics, so the
complete suite was not repeated. The same **143 tests passed against the installed wheel** (1.60 s), using the
installed-test command above with `test_topostitch_contacts.py` appended. The
wheel was installed with its declared dependencies, including NARestraints
v1.1.3 (`a9264f9`) and Gemmi 0.7.5. An actual isolated installed
`nasolve-topostitch-inspect ... --radius 15 --periodic --contacts` call on a
synthetic fixture passed, and installed module bytes matched current source. No native Phenix/Coot tools or scientific inputs
were used.
