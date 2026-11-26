# Explicit TopoStitch bend previews

The `nasolve-topostitch-preview` command writes one new candidate from an explicit
window and terminal motion. It preserves the source model and fixed anchors.
This is a controlled trial generator: it does not find the best placement, close
an atomistic backbone, refine a model or recommend campaign adoption.

## Review a window before generating coordinates (W291)

The ordinary preview command can now inspect the selected scope without writing
coordinates. Use the same explicit model, registration, discovery and schema-1/2/3
trial that would be used for the preview:

```sh
nasolve-topostitch-preview source.pdb discovery.json \
  --registration registration.json --trial trial.json --inspect-window
```

`--inspect-window` and `--out` are mutually exclusive. The former prints a
schema-1 `topostitch-window-inspection` JSON report. The latter retains the
existing candidate-building behavior. The equivalent read-only Python API is
`inspect_bend_window(model, discovery, registration_path=..., trial_path=...)`
in `nasolve.topostitch_preview`.

This reuses the existing terminal/interior window selection and canonical residue
mapping. The report identifies each moving residue, fixed anchor and neighbouring
backbone residue; its zero-based atom indices use the complete source PDB
ATOM/HETATM record order. `fixed_context_atom_indices` contains **all** nonmoving
atoms, including the separately listed anchors. It also carries ordinary backbone
links touching the movement scope and exact model/discovery/registration/trial
file digests. No host path is needed to interpret the report.

`WINDOW_FOR_REVIEW` means the declared scope maps to the supplied source. It does
not mean that displacement, strain, base planes, packing, ADP transport or native
restart have passed. A scope can pass inspection while its later preview exceeds
a motion limit. Representation continuations and changed images are not traversed;
modified residues and undeclared pairing are not admitted by this canonical owner.
A caller must recheck the current parent and input digests before acting. This is
a fresh inspection, not a saved-report approval or replay interface.

The existing `nasolve-topostitch-inspect ... --windows` report also adds
`planning_status`: `WINDOWS_FOR_REVIEW`, `DUPLEX_PARTNERS_UNSPECIFIED` when an
incomplete inventory declares no pairs, or `NO_EDITABLE_WINDOWS`. An explicitly
complete inventory with no pairs is distinct from missing partner information.
Existing trial schemas, window identities, preview receipts and defaults do not
change; consumers of window-proposal reports should accept this additive field.

**Genuine-parent check:** the W280/W282 PDU `refine-003` parent, resolved through its
declared dataset/run anchors and Cedar's trusted registry reader, has four strand
routes and no declared duplex pairs. Source and relocated installed inspection
both report `DUPLEX_PARTNERS_UNSPECIFIED` with incomplete assessment and no selected
window. Original inputs remain byte-identical and current selection remains
`postmr`. Soft contact restraints do not establish the missing designed partners
or physical oligos. This is an upstream scope boundary, not a geometry result.

**Validation:** eight distinct regression cases were observed failing before their
respective fixes; **161 focused source and 161 relocated installed tests pass**
across interior preview, preview, discovery, fit and checkpoint modules. The
installed console script passes help and positive inspection; the genuine PDU
observation reproduces exactly. All 94 installed Python modules match source.
The original package/build paths are removed before installed checks; explicit
input relocation is tested with original paths gone. This does not qualify whole
scientific-run portability or a combined Pine/Cedar/Alder release.

Exact commands, dependency file hashes, results and the trusted-reader pin are
local under the NASolve anchor `branch-artifacts/willow/w291-window-review/` in
`installation.json`, `source-genuine-pdu.json` and `qualify.py`. Focused commands
set `PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH`; Phenix's launcher resets
that variable, so the recorded bootstrap restores those same roots in-process.
Validation uses Phenix **2.2.1-6174** Python 3.11.15, SciPy 1.17.1, Gemmi 0.7.5 and
installed NARestraints 1.1.3 with openpyxl 3.1.5. Initial launcher/import failures
are preserved. The subsequent complete Willow regression passes **3,010 tests
and 234 subtests, with no skips**, in 210.47 seconds at `f19e9515`, using that same
Phenix Python and isolated pure dependencies. The first ordinary-Python attempt
stopped at collection (24 skips, five errors) because Gemmi/SciPy were absent;
it is retained separately. The supplied collaboration contract requested this
complete check. No source or test bytes changed, and 68,350,157 temporary bytes
were removed. This is branch regression, not native refinement or a combined release.

The complete command, run from the Willow anchor, is:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <NASolve>/.venv/bin/python -B \
  <NASolve>/branch-artifacts/willow/w291-window-review/full_suite.py
```

`full-suite-summary.json` binds the controller, both attempt logs and
`full-suite-qualified.json`, which records the exact child command, dependency
hashes and process environment. The child runs `pytest -q -rs -p no:cacheprovider
tests` with an owned temporary test directory and the explicit source/dependency
bootstrap described above. Scientific inputs, reports and dependency copies are
excluded from Git; all task-owned installation/test staging was removed.

## Reuse a saved motion in backend code

`load_bend_motion` replays a preview pinned by its exact receipt digest and returns
an immutable motion plus its six saved rotation/translation parameters:

```python
from nasolve.topostitch_preview import load_bend_motion

motion, parameters = load_bend_motion(
    preview_directory, expected_receipt_sha256=expected_preview_digest,
    parent_model_bytes=current_parent_bytes,  # optional exact immutable snapshot
)
displacements = motion.displacements(parameters)
```

The source atom order, fixed atoms, paired weights, pivot and displacement bound
come from the verified packet and registration. The motion binds the **source**
model; the saved candidate or a refined child requires a new workflow binding.
`NativeMaskedObjective.evaluate_motion` checks that source digest as well as the
exact mask/reference/bound. Existing previews need no migration. Compilation may
conservatively refuse a preview whose unrounded motion exceeds a bound that its
rounded candidate passed, or whose coordinate fields do not reproduce exactly.

This returns coordinate arithmetic, not a model or permission to optimize. ADPs
are not transported by this API, and a different parameter vector must undergo
fresh backbone/packing and scientific review. It neither restores a failed trial
nor changes optimizer stopping policy.

When an admitting caller has a current parent, supply its immutable PDB bytes
with `parent_model_bytes`. W171 rejects any difference from the preview's pinned
source, including coordinates, B/Q, identities and metadata, before returning the
motion. Omitting the option retains the existing numerical API. This verifies a
snapshot; it does not resolve a checkpoint, authorize motion or keep a later
mutable file current. The execution owner must bind the checkpoint and recheck
its consumed inputs at dispatch.

For the narrow coordinate-only route, pass the reconstructed full-precision
points and the saved candidate bytes to `audit_masked_endpoint` with the motion's
mask/bound. That existing owner retains candidate-byte and tensor restrictions.
The optional parent comparison does not allow an ANISOU-rotating preview into a
route requiring fixed non-XYZ bytes, or admit modified residues/metals.

## Bind a motion to a saved checkpoint (W173)

For the supported canonical coordinate-only route, use the read-only adapter:

```python
from nasolve.topostitch_checkpoint import load_checkpoint_bend_motion

motion, parameters, binding = load_checkpoint_bend_motion(
    run_directory, preview_directory,
    expected_checkpoint_id=parent_id,
    expected_receipt_sha256=preview_digest,
    checkpoint=None,  # current selection, or an explicit ID/bookmark
)
```

The run must already have a saved schema-2 registry and complete checksummed
`run`, `dataset` or `repository` references. The exact selected ID, parent record,
model, observations, ordered restraints and optional declared phases are checked.
No registry is initialized or migrated, and current selection is unchanged.
The existing preview loader supplies full-precision points; the strict endpoint
owner checks fixed atoms, non-XYZ bytes and full/rounded displacement limits.

Before dispatch, call again with the same arguments and
`expected_checkpoint_context_sha256=binding["context_sha256"]`. This detects
changed selection, metadata, declarations or inherited inputs. Each call reads
and verifies inputs both before and after preview replay. The returned binding
contains anchored references and hashes, not operational host-absolute paths.

This is **not a run lock or a refinement request**. The executor must freeze and
consume the verified inputs under its own ownership protocol. Chemical/topology
intent, Free-R meaning, retained native manager, ordinary execution lineage and
scientific acceptance remain separate. Existing APIs/previews need no migration;
older or incomplete registries remain usable through their existing workflows,
but this narrow adapter refuses them. Modified/metal motion and ANISOU-changing
previews are not admitted. [Validation and limits](topostitch-periodic.md#w173--bind-motion-to-the-selected-checkpoint-inputs).

## Join an existing execution request (W174)

`topostitch_checkpoint.load_execution_bend_motion` adds a read-only join to the
W173 call. Supply the same parent/preview arguments plus:

```python
motion, parameters, binding = load_execution_bend_motion(
    run_directory, preview_directory,
    expected_checkpoint_id=parent_id,
    expected_receipt_sha256=preview_digest,
    expected_checkpoint_context_sha256=parent_context_digest,
    execution_reference=frozen_request_reference,
    child_checkpoint_id=child_id,
    request_model_role="candidate",  # or explicitly "parent"
    generated_parameters=round_parameters_reference,
    refinement_input_reference=namespace_adaptation_reference,  # optional
)
```

An unchanged-parent request proves ancestry/input membership only. A candidate
request must contain the exact serialized preview bytes. Neither authorizes
coordinate transfer. Model/data, ordered restraints and phases are checked
against the selected parent; `additional_restraints` must be separately declared
in order. Generated `AutoRefine/round_NNN/autorefine.params` is a distinct final
input. Namespace derivatives are validated by Cedar's existing adaptation owner.
A returned context digest can be required on the next call with
`expected_execution_context_sha256`; requests and source/preview inputs are reread.

The API uses the maintained `refinement_parallelity.read_execution_request` and,
when needed, `refinement_inputs.validate_refinement_inputs`. These owners are
not yet present on standalone Willow: that installation refuses clearly unless
an integration caller explicitly supplies trusted `execution_reader` and
`refinement_input_reader` callables. Pinned Cedar compatibility was tested;
there is no dynamic source loader, copied reader or alternate executor here.
The executor still owns file freezing, command/force semantics, chemistry,
admission and launch. Output keeps `chemical_admission` and `runtime_authority`
false. No existing request is rewritten or silently upgraded.

## Inputs and use

Start with the existing [registered discovery manifest](topostitch-periodic.md)
and inspect it with `--windows`. Choose an available window from that report;
free ends and protected junctions cannot be bypassed with an old window ID.
Use the same maximum window size and fixed-anchor count when defining the trial.
The input is single-model ASCII PDB with canonical DA/DC/DG/DT sites and explicit
logical-to-coordinate mappings. Missing or pending target chemistry is not built.

```sh
nasolve-topostitch-inspect model.pdb discovery.json \
  --registration registration.json --radius 20 --windows
nasolve-topostitch-preview model.pdb discovery.json \
  --registration registration.json --trial trial.json --out new-preview
```

`new-preview` must not exist; its parent must exist. The preview command needs no
additional dependency beyond NASolve. The optional `topology` extra is needed for
periodic inspection, not this explicit Cartesian move.

New `trial.json` inputs should use schema 2, kind `topostitch-window-transform`, and accepts only
these fields. Hashes are exact lowercase SHA-256 digests of file bytes, not
filenames or paths. Replace the descriptive placeholders below with real hashes
and the selected ID; the numerical values are an arithmetic example, **not
scientifically qualified limits**.

```json
{
  "schema_version": 2,
  "kind": "topostitch-window-transform",
  "model_sha256": "<model.pdb SHA-256>",
  "discovery_file_sha256": "<discovery.json SHA-256>",
  "registration_file_sha256": "<registration.json SHA-256>",
  "window_id": "<window_id from the inspector>",
  "max_window_pairs": 12,
  "fixed_anchor_pairs": 2,
  "rotation_vector_degrees": [0, 0, 1],
  "translation_angstrom": [0.2, 0, 0],
  "max_atom_displacement_angstrom": 2,
  "max_backbone_bond_change_angstrom": 0.2,
  "max_backbone_angle_change_degrees": 15,
  "max_backbone_torsion_change_degrees": 15
}
```

The rotation vector is Cartesian axis-angle: its direction is the rotation axis,
its magnitude the angle in degrees (at most 180). It is not three Euler angles.
The pivot is the mean of the two terminal six-membered base-ring centroids.
Translation is applied after rotation, in the source PDB Cartesian frame.

## Motion and audit

The terminal pair and all overhang residues receive weight 1. Each remaining
movable paired step receives the smoothstep weight `3t² − 2t³`, where
`t = 1 − i/m`, `i` is the zero-based terminal-first pair index and `m` is the
number of movable pairs. This taper is an initialization, not a claim about the
physical distribution of curvature; strand-specific or density-driven relaxation
is not implemented. Fixed anchors have weight 0 and their records are
untouched. Each paired step moves rigidly as a group; rotation angle and
translation are scaled by its weight. This preserves each residue's internal
shape up to PDB coordinate rounding, but can strain bonds between residues.

Every declared strand link touching a movable site is therefore checked after
serialization. Schema 2 checks O3′–P distance; C3′–O3′–P and
O3′–P–{O5′, OP1, OP2} angles; and epsilon, zeta and alpha torsions spanning
the link. Torsion changes use the shortest signed difference in [−180°, 180°);
the positive torsion limit cannot exceed 180°. The receipt
records before, after and change values. Missing audit atoms, unusable occupancy,
alternate conformers, unresolved mappings, degenerate angles and field overflow
stop the trial before creating its output directory. Caller limits bound changes
from the source; they do not establish ideal geometry or repair a bad starting
bond. Torsion ideals, sugar pucker, clashes, stacking quality, density and symmetry contacts remain
separate qualification work.

All atoms belonging to a movable residue move together. Associated ANISOU tensors
are transformed as `R U Rᵀ`; occupancy, isotropic B, identities and other fields
are retained. Fixed/unselected records and CRYST1 remain byte-identical. A zero
motion preserves the complete PDB bytes. Selected SIGATM/SIGUIJ uncertainty
records are unsupported; duplicate/orphan/mismatched selected ANISOU records
fail. The ANISOU units and Cartesian frame follow the
[wwPDB fixed-column specification](https://www.wwpdb.org/documentation/file-format-content/format33/sect9.html).
A bend changes the physical structure; this is not a symmetry-equivalent recut.

## Output, replay and UI meaning

The new folder contains `source.pdb`, `candidate.pdb`, `discovery.json`,
`registration.json`, `trial.json` and `preview.json`. Input snapshots preserve
exact bytes. The `topostitch-bend-preview` receipt (same schema version as its trial) binds each artifact to
its declared run-relative path, byte count and checksum. It includes the selected
window, weights, origin, actual displacement and backbone audit. Original input
paths are not operational dependencies.

```python
from nasolve.topostitch_preview import load_bend_preview
receipt = load_bend_preview("moved-preview-folder")
```

The loader verifies all snapshots and replays the exact trial, checking both the
candidate bytes and receipt. It rejects stale, missing or altered evidence.
Relocation is tested after removing original inputs; this is stricter than
merely copying a folder. Exact floating-point replay across different numerical
platforms is not yet qualified. An I/O interruption can leave an incomplete new
folder; it is never accepted as a complete preview or overwritten automatically.

UI consumers may compare the frozen source and actual candidate, highlight
movable/fixed sites and show measured changes. The receipt means
`CANDIDATE_BUILT`, refinement `NOT_ATTEMPTED`, review `UNREVIEWED`, with
`geometry_validated: false` and no campaign/checkpoint authority. Viewing a
candidate cannot mark it approved. There is no Apply/Refine/Approve API yet.

## Offline original/candidate view

```sh
nasolve-topostitch-view new-preview --out connection.html
# Optional: reproduce an explicitly chosen original-model search and show its mate.
nasolve-topostitch-view new-preview --candidate 0 --radius 20 --periodic \
  --out connection-with-mate.html
```

Open the resulting HTML in a browser. It contains all display coordinates and
code; no server, online service, CDN, browser plugin or AI runtime is required.
The basic window view needs no Gemmi/SciPy. A periodic mate requires the
`topology` extra; it does not require the fitter. Write outside the frozen preview
folder to a new file; existing files are never replaced. The standalone artifact
contains structure coordinates, so treat it like the source model when sharing.

The writer verifies and replays the exact frozen preview before reading its
source/candidate atoms and checks that inputs remained unchanged. A mate is
optional and must be chosen explicitly with the **original-model** candidate
index and search radius/budgets. It is not recovered by trusting a fit report or
searching the moved model. Both coordinate sets use the same exact target image.
Source and transformed selected-image ambiguity stay visible as review warnings;
these checks do not qualify whole-window packing.

Use Original, Candidate or Overlay; drag to rotate, Shift-drag to pan, scroll to
zoom, or use keyboard arrows, +/− and Home. Click O3′ points for residue, image,
scope and coordinate detail; All atoms permits atomic inspection. Solid traces
join consecutive **declared** strand sites at O3′, six-membered base outlines
show orientation, and dashed lines show measured proposed base contacts. None
of those lines asserts a newly built covalent link. Unmapped unrelated routes do
not acquire invented coordinates or trace edges.

`nasolve.topostitch_view.preview_scene` provides the detached schema-1
`topostitch-preview-view` display payload for later UI reuse. It contains actual
coordinates, search/image identity, source/candidate/receipt hashes and the
verified preview's workflow state. It is a display derivative, not a new
checkpoint, model loader, authoritative graph or resumable scientific record.
The HTML exposes no Apply/Refine/Approve controls. Pine still needs its periodic
molecular graph, selectable cut alternatives and backend materialization before
this component can support a real recut workflow.

Python data/replay tests, installed and relocated asset checks, and JavaScript
syntax plus mock-DOM interaction checks cover this component. The 8D93 view
contains 404 atom instances, 204 moved, from the actual schema-2 candidate.
**Browser visual/interaction validation remains pending:** automation policy
blocked opening the local HTML. The mock-DOM check is not a rendered-browser
check, and the full GUI is not claimed complete.

## Bounded placement for one chosen pairing

`nasolve-topostitch-fit` adds a read-only local placement search. It fixes the
chosen pairing/image and editable window, starts once at zero motion, and fits
six terminal rotation/translation parameters. It never chooses another partner,
expands a window automatically, writes a model or adopts a result.

```sh
python -m pip install ".[topology-fit]"
nasolve-topostitch-fit model.pdb discovery.json \
  --registration registration.json --request fit.json > placement.json
```

The strict schema-2 `topostitch-placement-request` has these fields:

| Field | Meaning |
| --- | --- |
| `model_sha256`, `discovery_file_sha256`, `registration_file_sha256` | Exact input-byte hashes, as for preview trials |
| `reference_catalog_sha256` | `effective_catalog_sha256` from the inspector's NARestraints contact assessment |
| `search` | `periodic` boolean, explicit `radius_angstrom`, positive integer `max_pairs` and `max_image_tests` |
| `candidate` | Exact ordered `ends` from the inspector and `target_image_operator` (`null` for same-frame mode) |
| `window` | Explicit `window_id`, `max_base_pairs` and `fixed_anchor_pairs` |
| `motion_bounds` | Three positive `rotation_degrees` and three positive `translation_angstrom` component bounds; both signs are allowed |
| `objective` | Positive `backbone_distance_scale_angstrom`, `backbone_angle_scale_degrees`, `backbone_torsion_scale_degrees`, `plane_offset_scale_angstrom`, `plane_normal_scale_degrees` and `motion_weight` |
| `limits` | The four displacement/backbone-change limits from the preview trial |
| `max_residual_evaluations` | Positive integer cap including finite-difference Jacobian calls |

The request also includes `schema_version: 2` and
`kind: "topostitch-placement-request"`. The norm of the rotation-bound vector
cannot exceed 180°, the torsion scale and change limit must be at most 180°,
and the plane-normal scale must be at most 90°. These are
component boxes, not spherical motion bounds. The final per-atom displacement
limit still applies. Numerical scales and limits are caller policy, not
scientifically calibrated defaults.

The objective combines canonical NARestraints bond/angle deviations divided by
recipe sigmas; paired-plane offsets and normal alignment; backbone bond/angle/circular-torsion
changes from the source; and a small-motion penalty scaled by the declared box.
Plane normals may be parallel or antiparallel. Angles use degrees. The current
whole-residue motion preserves local shape but does not optimize sugar torsions
or solve atomistic closure. No density, diffraction, Rwork or Rfree enters this
objective. Improved target score is not independent confirmation of the pairing.

The solver uses SciPy's bounded `trf` least squares, three-point differences,
explicit parameter scales and tolerances, and one zero initialization. The report
records exact settings and NumPy/SciPy/library versions. Its own residual counter
includes Jacobian calls, which SciPy's `max_nfev` does not count. Fixed before/after
observations are outside the solver-call count. See the
[official least-squares API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).

A `topostitch-placement-proposal` (same schema version as its request) returns one of:

- `TRANSFORM_FOR_REVIEW`: converged, serialized trial passes its declared limits,
  and the named pair target improves numerically; `trial` is ready for preview.
- `NO_PAIR_TARGET_IMPROVEMENT`: no useful numerical improvement; no trial.
- `BUDGET_EXHAUSTED` or `SOLVER_DID_NOT_CONVERGE`: no partial best-so-far trial.
- `TRIAL_LIMIT_REJECTED`: fitting converged but the serialized move exceeds a
  declared displacement/backbone limit; no trial.

Malformed/stale inputs, incomplete contact measurements, self-pair fitting and
movement of the other end's defining residues fail explicitly. The other end may
be in a nonidentity symmetry image; atoms are moved in their original ASU frame
before applying that exact image. Physical orbit distinctness is not certified.

To materialize an explicitly chosen successful proposal, save its `trial` object
as a new JSON file and pass it to `nasolve-topostitch-preview`. The candidate hash
must match `candidate_model_sha256` from the fit report. API users can call
`fit_end_placement` and `build_bend_preview` directly; UI consumers can show the
continuous versus serialized target changes and actual preview audit. No
scientific acceptance, native audit or review state is upgraded by convergence.

### Periodic source and candidate image checks

The fitter now runs the selected present-atom image audit before invoking the
optimizer for periodic requests. It records the full `selected_image_identity`
evidence using a 0.01 Å coincidence tolerance, 2,000,000-test work limit and the
inspector's finite record cap. Coincident source identities, stabilizer
observations, partial occupancy or an unassessed selected inventory return
`IMAGE_IDENTITY_REVIEW_REQUIRED`, zero solver residual calls and no trial.
Each audit has its own recorded work budget; budget exhaustion is an input
error with no partial proposal. Nonperiodic fits
retain their existing behavior and record no periodic audit.

Both request schemas now use proposal algorithm
`single-window-canonical-contact-least-squares-v4`. For an improving serialized
trial, the fitter repeats the bounded selected-atom audit on the generated bytes,
using the exact original end identities and image operator. It does not search
again or reinterpret a candidate index after motion. The separate schema-1
`topostitch-transformed-image-identity` evidence binds the candidate hash, source
audit fingerprint, cell/setting and operator. A new coincidence returns
`TRANSFORMED_IMAGE_REVIEW_REQUIRED` with no trial; exhausted audit budgets fail
without a partial proposal. Nonperiodic, early-refusal and non-improving outcomes
record `transformed_image_identity: null`.

Eligible public 8D93 input preserves the prior candidate bytes; schema-1/2
previews still replay. This closes the demonstrated gap where the pair score
improved but an unscored atom collided with the selected mate. Both audits are
limited to the selected present atoms and the declared coincidence tolerance.
They do not approve van der Waals packing, omitted atoms, global orbit capacity
or a connection.

## Validation and compatibility

This additive module/entry point leaves the read-only inspector, Pine
registration schema, campaign mechanics, Cedar code and shared environments
unchanged. Schema 1 retains its original two-angle audit, objective and exact
preview replay. Schema 2 adds mandatory torsion policy fields and extended
backbone evidence; it never silently downgrades when atoms or fields are missing.
Existing frozen reports are not migrated. To request the extended checks, create
a new schema-2 request/trial from the same verified inputs; do not edit old receipts.
Older NASolve versions reject schema 2 rather than interpreting it as schema 1.
Focused regression tests cover preservation, ANISOU rotation, finite bounds,
malformed records, free/protected ends, no-overwrite behavior, tampering and
original-path-absent relocation. See the [current validation receipt](topostitch-periodic.md#current-validation-receipt--2026-11-13)
for commands, installation checks and aggregate counts.

A local public 8D93 smoke check used an explicitly selected six-pair window,
two fixed pairs, a 1° z rotation and 0.2 Å x translation. It moved 204 atoms and
rotated 204 ANISOU records; maximum displacement was 0.310058 Å, maximum backbone
bond change 0.091192 Å and angle change 3.314059°. Source bytes stayed unchanged
and the frozen trial replayed. This is a serialization/audit check, **not a
scientific repair success**. Coordinates and derived models are excluded from
Git. The explicit preview is not a native geometry pass; see the interpretation
comparison below. No Coot execution or diffraction refinement was performed.

### Public 8D93 native interpretation comparison — 2026-11-13

A bounded fit used the same six-pair scope/two fixed pairs, component bounds of
±5° and ±2 Å, and the exact selected periodic mate. Objective scales were 0.05 Å
backbone distance, 5° backbone angle, 0.2 Å plane offset, 10° plane normal and
motion weight 0.1; limits were 3 Å atom displacement, 0.2 Å bond change and 15°
angle change, with 3,000 solver residual calls allowed. These are a development
trial policy, not established scientific tolerances. SciPy 1.18.1 / NumPy 2.5.4
converged in 91 actual residual calls. The serialized pair target sum of squares
fell from 190.692330 to 123.887533; maximum displacement was 0.788651 Å,
backbone bond change 0.053171 Å and angle change 8.381172°.

Using Cedar `ecafc98`'s existing `cif_native_validation.inspect_native_bundle`,
all three models completed native interpretation (not a dry-run) with Phenix
installation **2.2.1-6174**, dispatcher **2.2.1**, exit 0 and aggregate **REVIEW**.
This was a separate diagnostic invocation, not a Willow/Cedar merge or a new
production interface. Each retained 855 atoms and 956 simple-bond, 1,467 angle
and 166 chirality proxies. Source and frozen input bytes remained unchanged.

| Model | Simple bonds with nominal absolute deviation ≥5 | Angles ≥5 | Chirality sign conflicts |
| --- | ---: | ---: | ---: |
| Source | 4 | 17 | 0 |
| Explicit 1° / 0.2 Å preview | 7 | 17 | 0 |
| Bounded fitted candidate | 4 | 18 | 0 |

These counts come from Cedar's captured Cartesian review, not a calibrated
acceptance threshold. The fitted candidate avoided the arbitrary move's three
new severe bond deviations but added a severe angle deviation. That is evidence
for further qualification/relaxation, not a repair success. Symmetry contacts,
planes/parallelities, full packing and diffraction agreement remain unqualified.
Native energy inventory was captured, but no optimization/refinement was run.

The exact native call settings were:

```python
receipt = inspect_native_bundle(
    model, [], output_parent, installation.executables["phenix.python"],
    environment=installation.environment, phenix_version=installation.version,
    timeout_seconds=120, phil_files=[geometry_phil], inventory_detail="linked",
    installed_library_only=True, energy_inventory=True, policy_inventory=True,
    full_monomer_inventory=True,
)
review = review_captured_geometry(receipt["native_validation"])
```

`geometry_phil` contained only
`pdb_interpretation.use_ncs_to_build_restraints = False`. Installation discovery
used the existing saved Phenix root, revalidated through `discover_phenix` without
saving configuration. Diagnostics were written outside every input directory.
All downloaded coordinates, candidate models and native receipts remain local,
excluded from Git. This coordinate-only comparison is separate from the proposed
8D93-to-hexagonal-recipient diffraction benchmark.

### Stricter backbone controls — 2026-11-13

Three policies were declared before comparison, changing only the backbone
penalty scales in the original public 8D93 request. The source, image, window,
other objective terms, motion bounds and 3,000-call budget were unchanged.

| Control | Distance / angle scale | Serialized pair target | Max backbone bond / angle change | New nominal ≥5 bonds / angles / chirality |
| --- | --- | ---: | --- | --- |
| Original fit | 0.05 Å / 5° | 123.887533 | 0.053171 Å / 8.381172° | 0 / 1 / 0 |
| Gentle | 0.02 Å / 1° | 157.293092 | 0.012602 Å / 1.597793° | 0 / 0 / 0 |
| Conservative | 0.01 Å / 0.5° | 171.649933 | 0.008765 Å / 0.665227° | 0 / 0 / 0 |
| Stiff | 0.005 Å / 0.25° | 183.775561 | 0.003787 Å / 0.226707° | 0 / 0 / 0 |

The unmoved pair target is 190.692330. These scales are development controls,
not calibrated tolerances or new product defaults. Each new candidate completed
read-only Phenix 2.2.1-6174 interpretation (exit 0, REVIEW), with the same options
above, using an immutable Cedar `cd744e2` source snapshot. Existing source outliers
remained; no new nominal ≥5 scalar outliers or chirality sign conflicts appeared.

This comparison uses Cedar's existing `_capture` receipt binding,
`qualify_fragment_restoration` mechanics check, `_proxy_subset` ordered named
proxy multisets and `review_captured_geometry`. It checks every captured proxy
category, atom identity, effective definition, interpreter/API and restraint-policy
context before matching individual scalar endpoints. All matched, so equal counts
are not concealing exchanged outliers. Cedar code/environments were unchanged.

This demonstrates a contact/strain tradeoff and removes the particular earlier
angle regression under these tighter controls. It does **not** establish atomic
closure, native residual improvement, complete torsion/packing qualification or
better diffraction agreement. These schema-1 controls cover the declared
O3′–P length and two junction angles. Schema 2 extends source-change coverage as
described below; native geometry remains an explicit next gate. Frozen inputs, models, native
receipts and the matched diagnostic stay local and out of Git.

### Extended backbone checks — 2026-11-13

Schema 2 adds the two nonbridging phosphate angles and three cross-residue
backbone torsions to both the fitting objective and serialized preview audit.
The original fitted 8D93 trial changes an extended angle by 9.454433° and a
torsion by 10.298284°, compared with the legacy maximum angle change of
8.381172°. This explains why the smaller audit was insufficient.

A new development fit kept the gentle control's 0.02 Å / 1° scales, added a 5°
torsion scale and 15° torsion-change limit, and held the remaining inputs,
window, bounds and budget fixed. Its serialized pair target was 161.832389
(from 190.692330), maximum extended angle change 1.246422° and torsion change
1.524362°. Complete Phenix 2.2.1-6174 interpretation returned exit 0, REVIEW.
Cedar cd744e2 receipt binding, native contexts, named proxy multisets and mechanics
checks matched the source; no new nominal ≥5 captured bond/angle/chirality
outliers appeared. Frozen source snapshots remained unchanged. This uses the
same native options and comparison scope above, with no Coot/refinement run.

These are bounded changes from the starting geometry, not ideal torsion targets,
phosphate valence validation, packing qualification or atomic closure. Existing
source outliers remain. Standard OP1/OP2 atom names are required; missing atoms
fail before creating output. Native symmetry-restraint transport and local
relaxation remain the next S05 work, followed by matched diffraction validation.
All native inputs and generated scientific artifacts stay local and out of Git.

### Native transport and backbone-only relaxation diagnostics — 2026-11-13

A local Phenix 2.2.1-6174 CCTBX check reproduced all five canonical bond and eight
angle measurements for the exact 8D93 R3:H mate. Explicit unit-cell-aware native
proxies matched the independent Gemmi observations within 10⁻⁹ in their respective
units. Central differences over contact-atom ASU coordinates at steps 10⁻⁴, 10⁻⁵
and 10⁻⁶ Å agreed with native gradients; at 10⁻⁵ Å the largest bond/angle errors
were 9.77×10⁻⁹ and 3.41×10⁻⁸. Bond operators use the relative transform
`op0.inverse().multiply(op1)`; angles use the ordered per-atom `sym_ops`. This
was an executed value/gradient probe, not manager attachment or a refinement
interface. Sixty public backbone torsions plus signed synthetic controls also
matched the schema-2 dihedral convention within 1.2×10⁻¹³ degrees.

A separate local experiment held every base and all sites outside the chosen
window fixed, allowing only 107 selected sugar/phosphate atoms to relax. It used
the installed native geometry manager, including crystal nonbonded terms, plus
a 0.1 Å coordinate tether; no added contact restraints, dictionary edits or
chemical links. Source and placed models received identical predeclared policy:
200 iterations, 1,000-call ceiling, 2 Å trial displacement ceiling and 0.5 Å final
ceiling. Both reached the iteration limit, **not a convergence verdict**.

| Input | Native geometry target before → rounded endpoint | Maximum move | New / resolved nominal ≥5 angles |
| --- | --- | --- | --- |
| Unmoved source control | 7222.455462 → 6780.040386 | 0.215779 Å | 0 / 3 |
| Schema-2 placed candidate | 7192.557988 → 6762.463778 | 0.157561 Å | 0 / 3 |

The target table excludes the separately recorded coordinate tether. Fresh native
captures retained matched definitions/proxies/contexts, added no severe captured
bond/angle/chirality outliers, and returned REVIEW. Endpoint derivatives checked
all 321 movable Cartesian coordinates at two step sizes; maximum error was
1.04×10⁻⁶ at 10⁻⁵ Å. Fresh serialized native targets reproduced the saved values.
All nonselected coordinates, non-coordinate columns and ANISOU records remained
byte-identical to each respective input. The contact bases were fixed, so their
placement score cannot improve during this cleanup.

This supports a scoped backbone-relaxation approach, not a production closure
API or repair acceptance. Some native target components increased while the
total fell; sugar-pucker/stacking, complete endpoint chemistry and matched
diffraction validation remain open. Both models improve under ordinary cleanup,
so the target reduction alone is not a stitching benefit. Cedar owns the existing
captured-geometry trial lifecycle; its all-atom policy does not yet expose this
fixed-base selection or an arbitrary symmetry-contact objective. Keep the local
prototype distinct from Cedar's qualified policy and reuse its lifecycle at
integration. No Coot or diffraction refinement was run; artifacts remain local.

### Explicit movement-mask and contact controls — 2026-11-13

Local complete Phenix 2.2.1-6174 executions now exercise a separately identified
masked objective. They reuse Cedar `cd744e2`'s `evaluate_fixed_native` and static
constraint signature, without changing Cedar's all-atoms trial policy. Model,
mask, tether, effective PHIL, native/helper sources and objective identities are
recorded locally. Nonbonded neighbors follow the native manager's policy; their
membership is not claimed frozen.

The fixed-base check keeps 748 atoms fixed and permits only 107 explicitly named
sugar/phosphate atoms. Every one of the 321 movable Cartesian components passes
central differences at 1e-4 and 1e-5 Å before optimization, at the continuous
endpoint and after PDB rounding (worst error at 1e-5: 1.06e-6). Both source/placed
controls reproduce the previously captured backbone-only candidates byte-for-byte,
with matching static native definitions. This qualifies that local projection
calculation, not a production trial adapter or ideal DNA geometry.

A second diagnostic permits all 204 atoms of the already selected movable window;
651 other atoms stay fixed. It compares a native-geometry/tether control with the
same objective plus the chosen image's five reference distances, eight angles,
two plane groups and two parallelity terms. A further matched pair adds the
12 declared existing duplex pairs to both objectives. Every trial starts from the
same schema-2 candidate; the six-pair scope, two fixed anchor pairs, 0.1 Å tether,
200-iteration/1,000-optimization-call caps, 2 Å trial and 1 Å final displacement
limits are declared before execution. The shared image helper expands Cartesian
coordinates and accumulates gradients into the actual ASU variables.

| Local objective | Serialized native geometry target | Selected contact target | Largest move / Å |
| --- | ---: | ---: | ---: |
| Starting candidate | 7192.557988 | 125.597906 | 0 |
| Native cleanup control | 6532.450184 | 117.369689 | 0.182543 |
| Cleanup + selected contacts | 6529.205252 | 100.673520 | 0.198784 |
| Cleanup + core pair terms | 6536.152202 | 117.450800 | 0.182543 |
| Cleanup + core + selected contacts | 6532.916244 | 100.674680 | 0.198784 |

These targets are unnormalized diagnostic sums with distinct meanings; the
selected-contact target is **not** the SciPy fitter's earlier pair score. All
four trials stop at the 200-iteration limit, so none is called converged. Their
612-variable initial/continuous/rounded derivative checks pass at both steps
(7,347 audit evaluations per trial; worst 1e-5 error <2.8e-6). Source and
unselected coordinates, identities, occupancy/B and non-coordinate PDB records
remain unchanged. Native readback contexts and named proxy inventories match;
no new nominal absolute >=5 captured bond/angle/chirality outliers or chirality
sign conflicts appear, and three prior angle outliers resolve. Selected image
coordinates remain distinct. Existing outliers and some worsening individual
geometry components remain.

Core pair bond/angle deviation sums worsen from 27.169238 to 38.811180 without
core terms, versus 29.405228 with them. The latter limits the largest core-pair
angle change to 1.251271° (versus 2.670175°); it does not freeze duplex geometry.
This is evidence to retain core-pair preservation in a native adapter, not to
accept the endpoint automatically.

**Recipe/integration limits:** bond and angle references come from frozen
NARestraints 1.1.3 tables. These exploratory plane terms use six-membered ring
outlines, planarity sigma 0.2 Å and parallelity weight 1. They are not the complete
NARestraints emitted plane selections/sigmas (0.176 Å and 0.027). The additive
objective does not alter native bonded tables, exclusions or LINK records.
Supported integration must qualify those semantics and the complete emitted
recipe, full torsion/packing behavior and captured input lifecycle. No covalent
seam is built, no density/Rwork/Rfree is used, and no checkpoint is published or
selected. All input models, workers, native receipts and generated candidates
remain local and outside Git.

### Complete recipes, native exclusions and broader-bend controls — 2026-11-13

Further **complete local Phenix 2.2.1-6174 executions** use the actual
NARestraints 1.1.3 emitted pair recipes, including full plane atom selections,
planarity sigma 0.176 Å and parallelity sigma 0.027. Effective PHIL is parsed
with unused definitions rejected; selections bind to captured atom identities
and explicit Cartesian images. These local recipe snapshots describe ASU roles;
they are **not exportable cross-symmetry refinement PHIL**.

The matched trials retain the preceding 204-atom movement scope and budgets.
Both include all 12 declared core pairs; only the contact trial adds the two
selected inter-image pairs. All 612-coordinate initial/continuous/PDB-rounded
derivative checks pass (worst 1e-5 Å error 2.68e-6), as do fresh native context,
proxy, immobile-byte and selected-image checks. Both stop at 200 iterations.

| Full-recipe objective | Native geometry | Selected contacts | Existing core pairs |
| --- | ---: | ---: | ---: |
| Starting candidate | 7192.557988 | 228.789516 | 336.128612 |
| Cleanup + core pairs | 6545.915697 | 226.906229 | 259.077233 |
| Cleanup + core + selected pairs | 6547.217972 | 176.738735 | 259.042567 |

The contact trial improves its selected target while slightly worsening native
geometry versus its matched control. It adds no nominal absolute >=5 captured
bond/angle/chirality outliers; three inherited angles resolve. However, individual
torsion/monomer-plane residuals and some native nonbonded overlaps worsen. Summed
energies alone therefore cannot accept the result. These targets differ from the
earlier exploratory recipe and must not be compared across objective definitions.

A separate **read-only native interpretation** establishes an important integration
boundary. Adding the five chosen symmetry distances as ordinary Phenix bond edits
changes native nonbonded exclusions and creates five internal LINK requests.
At identical coordinates, the bond target rises by 36.435957, while the nonbonded
target falls from 1077.721614 to 963.181796; ASU neighbor proxy entries change from
618 to 587. Five requested distances produce eight ASU bond-proxy entries, not
eight independent chemical bonds. This is different physics from appending those
five energies to an unchanged native manager. The supported adapter must declare
which semantics it implements and audit the intended proxy/exclusion changes.
LINK bookkeeping for a pair restraint must not become inferred phosphodiester
chemistry. This installed Phenix bond-edit scope exposes `symmetry_operation`;
its angle/dihedral/planarity/parallelity edit scopes do not provide corresponding
per-atom symmetry fields. Full periodic recipes need a qualified image-aware
path, not an ordinary ASU PHIL export with plausible selections.

The earlier, more strongly bent schema-1 candidate was also revisited with the
same **107 sugar/phosphate atoms movable and 748 atoms fixed**. No contact terms
are added and every base coordinate remains byte-identical to that bent model.
Its native geometry target falls from 7299.779902 to 6714.289955 with maximum
cleanup motion 0.127679 Å. All 321-variable endpoint derivatives pass; fresh
capture resolves the bend-induced severe angle and three inherited severe angles,
with no new severe captured scalar deviations or chirality sign conflicts versus
the original source. The chosen image remains coordinate-distinct. This supports
bend-then-backbone-cleanup as a candidate strategy, but does **not** close S05.

The full-neighborhood comparison explains why. One other periodic contact,
DT C101 C7 to DC C114 C2′ through `-y+1/3,x-y-1/3,z-1/3`, has native VDW overlap
0.083625 Å in the original model and 0.445409 Å after bend plus cleanup. Some
previously nonoverlapping pairs also overlap. Maximum overlap over the whole
model actually decreases (1.009571 to 0.977553 Å), hiding these local regressions.
Monomer-plane residual sum rises from 118.608875 to 130.371311; the largest local
plane RMS change is 0.013109 to 0.019338 Å and includes the movable glycosidic C1′.
Keeping base coordinates fixed does not freeze every monomer plane.

These observations reconstruct all 442 captured torsion and 42 monomer-plane
proxies and verify their summed energies against fresh captures. Native neighbor
pairs are compared by atom identity and exact reciprocal-normalized image;
`max(0, native VDW distance - observed distance)` is a **native-policy overlap,
not a MolProbity clashscore**. No newly listed overlapping neighbor is not the same
as no new overlap among existing neighbors. The source and cleanup-only control
retain their own unfavorable components. No model is promoted, no Free-R data or
refinement is used, and all scientific inputs/results stay local.

**Next S05 slice:** define one captured masked-trial policy with exact source,
mask, recipe and exclusion intent; require intended-contact and surrounding-image
comparisons, individual geometry changes and fixed-boundary checks at the rounded
endpoint. Reuse Cedar capture/correction/validation owners rather than building a
parallel native lifecycle. Keep numerical convergence, geometric qualification
and later matched diffraction improvement as separate gates. More optimization
iterations are not a substitute for those missing acceptance checks.

### Captured native packing comparison

`nasolve.topostitch_packing.compare_native_packing` is a thin read-only comparison
over authenticated Cedar captures and its maintained `review_native_nonbonded`
reviewer. It does not generate neighbors or execute a native worker. The developer
wrapper authenticates exact model/receipt snapshots through Cedar, replays the
captured directed pair sums/gradients, checks unchanged inputs and writes a
separate report:

```sh
python scripts/compare_topostitch_native_packing.py \
  --cedar-source /trusted/cedar/src \
  --before-receipt /evidence/before/native_receipt.json \
  --before-model /evidence/before.pdb \
  --after-receipt /evidence/after/native_receipt.json \
  --after-model /evidence/after.pdb \
  --out /review/new-packing-comparison.json
```

Use the actual receipt paths returned by Cedar, not a guessed filename. Captures
must request `nonbonded_inventory=True`,
`nonbonded_policy=cif_native_asu.POLICY_ID`, linked energy/policy inventories and
full monomer inventory through the existing `inspect_native_bundle` owner.
`--cedar-source` is explicitly trusted executable source; captured worker text is
never executed by this reader. The wrapper refuses overwrite or output inside a
frozen native capture. Exit zero means a report was written, not accepted geometry.

The additive schema-1 `topostitch-native-packing-comparison` retains source native
hashes, common/added/removed directed pairs, every native row and weight, changed
multiplicity, and separate counts for newly overlapping existing neighbors and
newly listed overlapping neighbors. Its API requires caller authentication; the
wrapper adds model/receipt hashes and reviewer-source fingerprints. No old schema
or checkpoint changes. The installed comparison core has no native/Gemmi dependency;
the developer wrapper needs the trusted Cedar checkout and its Python dependencies.

Identity is the ordered atom-label pair plus `first_image^-1 * second_image`,
including lattice translation. Native image indices may change between managers;
reciprocal directions and repeated native contributions remain separate. Standard
fractional rotations must be proper integer unimodular matrices; translations
must reconstruct with denominator at most 24 within 1e-12. Unsupported mappings
fail explicitly. This bounded rational interpretation is not a general orbit or
space-group validator. Matching requires identical atom identities/order, cell,
static restraints, interpretation context and nonbonded function. Native-edit
comparisons that change those definitions are deliberately outside this first scope.

Fresh complete Phenix 2.2.1-6174 captures of original 8D93 and the broader
bend-plus-cleanup candidate contain 8,305 and 8,309 directed rows. Replay confirms
native nonbonded target 1115.631384 → 1017.394684, while **103 matched directed rows
worsen and 20 previously nonoverlapping rows overlap**. There are 35 added and
31 removed identities, with no newly listed overlapping row or multiplicity
change. Counts are directed native rows, not unique physical contacts. This
independent Cedar-owned capture confirms the earlier local packing observation.

The detached report is byte-identical after moving copied source/models/captures,
with the original copied paths absent and Python reads of the original live
source/evidence directories blocked during the comparison. This validates this
reader's explicit relocated inputs; it does not qualify every historical local
experiment as resumable. Torsion/plane comparison, optimization, acceptance,
refinement and campaign adoption remain outside this report.

### W34 — Matched public-reference diffraction control

Three **complete Phenix 2.2.1-6174 refinements** test coordinate preprocessing on
already refined public [8D93](https://www.rcsb.org/structure/8D93). This is a
reference/healthy-control pilot, not an artificially damaged MR case or proof
that the deposited structure needs stitching. It is early S06 evidence while
S05 remains partial; no candidate or checkpoint is approved.

The deposited structure-factor CIF contains several processing blocks. The pilot
uses the STARANISO mean amplitudes/sigmas from `r8d93Asf`, joined by exact Miller
index to primary `r8d93sf` status `o`/`f`. This reproduces the deposited refinement
cohort: **3,333 observations, 3,157 work and 176 free**, 41.2867–2.9608 Å. The
original integer flag values and free value 0 are retained in the input MTZ;
round-trip readback verifies the exact held-out indices and observed amplitudes.
No flag is generated and no isotropic completion or alternative data block is
silently substituted.

Before execution, one common recipe and all three model hashes were frozen:
three coordinate-only macrocycles, ML target, fixed `wxc_scale=0.5`, no weight
optimization, one processor and one seed. No real-space/ADP/occupancy refinement,
added waters/atoms, experimental phases, extra pair restraints or data-outlier
rejection is used. Native bulk-solvent/scaling remains common to all cases;
overall isotropic scaling of ADPs is disabled. Each run finished within its
240-second limit. There is no Rfree-guided retry, weight search or extra trial.

| Starting model | Final Rwork | Final Rfree | Bond RMSD / Å | Angle RMSD / ° | Reported all-atom clashscore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original deposited coordinates | 0.1776 | 0.2284 | 0.012 | 2.622 | 30.78 |
| Source backbone cleanup | 0.1779 | 0.2274 | 0.011 | 2.668 | 30.03 |
| Broader bend + backbone cleanup | 0.1772 | 0.2276 | 0.013 | 2.842 | 27.03 |

W35 now reads these bond/angle RMSDs through the ordinary statistics parser when
the log lacks a combined geometry line. It recognizes the named final-PDB RMSD
summary and preserves existing log precedence; it does not infer missing values
from maxima or RMSZ. The installed wheel reproduces all three printed pairs.

These are printed native values at the reported precision, not an estimate of
statistical superiority. Relative to cleanup alone, bending lowers Rwork but
Rfree is 0.0002 higher and bond/angle RMSDs worsen. A small Rfree difference from
176 test reflections is not sufficient evidence to choose a bend. The pilot
does not reproduce the original deposited refinement protocol or claim a new
improved deposited structure.

At the same explicitly frozen sticky-end image, the descriptive sum of squared
NARestraints bond/angle reference deviations is 187.337, 177.269 and 112.202 after
refinement, respectively. Bending retains a contact advantage, but all three
scores rise during ordinary coordinate refinement (their inputs are 146.252,
146.252 and 83.748). No partner is reselected. This favors testing a qualified
pair-aware refinement path rather than assuming ordinary refinement will retain
all intended contacts. The measure excludes planes and is not an acceptance score.

Fresh Cedar directed-neighbor captures also replay after refinement. Compared
with the refined original, cleanup and bend+cleanup have 11 and 21 newly
overlapping **directed rows**, respectively; native nonbonded residuals are
1090.331 and 1088.475 versus 1076.017. These differ from the all-atom clashscore's
radii/hydrogen/exclusion conventions. Neither aggregate score nor a count of any
worsening contact can decide acceptance; inspect severity, location, intended
chemistry and the matched control together.

All 855 atom identities/order and occupancies survive. Input models, parameters
and MTZ remain byte-identical; final MTZ readback confirms exactly the same
observations/sigmas and free membership in every case. ANISOU values remain
unchanged within each refinement; printed B values differ by at most 0.01.
Native output-label warnings are retained; reflection readback passes. Final
model/map/density inspection in Coot and a damaged-model repair benchmark remain
open. Inputs, models, maps, native captures, scripts and receipts are local only.

### W36 — Native restraint callback: useful arithmetic, incomplete lifecycle

A complete **Phenix 2.2.1-6174 energy/derivative/lifecycle probe** evaluates a
small artificial harmonic distance on original 8D93, using the selected exact
image and the shared Cartesian transport. This is a diagnostic term, **not a
DNA recipe**, optimizer run, refinement or production adapter. All 855 source
atoms and native definitions remain unchanged. Its local script, source hashes,
effective parameters, interpretation log and result are preserved with the local
reference evidence; no generated models/data are committed.

The installed native source exposes
`cctbx.geometry_restraints.manager.set_external_energy_function`. Its callback
receives `sites_cart` and `gradient_array`, adds gradients into that existing
array, and returns an additional residual. The probe confirms both gradient and
energy-only calls and the `mmtbx.restraints.manager` wrapper. Six ASU derivatives
at two step sizes agree to **<5.4e-10** after subtracting the unchanged native
baseline. This verifies only the added term; it does not rehabilitate the raw
native plane derivatives that failed earlier controls.

Three lifecycle details matter before using this in a refinement:

- Even selecting **all atoms** with `geometry.select(...)` returns a manager
  without the callback. `discard_symmetry(...)` also drops it. Source inspection
  shows the same omission in `new_including_isolated_sites(...)`; that last path
  was inspected, not executed in this probe. A trial must prove binding after
  every relevant rebuild/selection and on continuation, or stop visibly.
- The extra residual changes the numerator but not `number_of_restraints`:
  the probe stays at **11,378** native restraints. Normalized geometry therefore
  divides the added term by the existing count. Its sigma/weight and the final
  diffraction-versus-geometry scale must be an explicit frozen policy, not an
  assumed one-to-one translation of the standalone objective.
- Turning all ordinary geometry flags off still evaluates the callback. The
  standard native energy summary also has no dedicated external-term row in
  this version's source. Enablement, component reporting and effective recipe
  fingerprints therefore need their own checked integration; ordinary printed
  bond/angle RMSDs do not prove that the extra terms were active.

No generic callable loader was found in the inspected normal refinement PHIL
and driver paths. An in-process API exists; a portable `phenix.refine` parameter
file carrying this policy has **not** been demonstrated. The earlier bond-edit
exclusion/LINK changes also remain relevant: an additive callback does not
implicitly reproduce those chemical semantics.

**Next decision, before more bending trials:** keep two bounded routes explicit.
The first is a version-qualified native integration that reuses Cedar's validated
energy/correction owners and Willow's image transport, and captures a complete
recipe, mask, exclusion policy, normalization and callback lifecycle. Test an
unselected no-op control and one declared distorted duplex with full derivative,
geometry/packing and matched diffraction checks before exposing it to campaigns.
A successful call into the native API alone is not that integration.

The alternative is a Pine cut that places the chosen interface inside one
represented model, allowing ordinary complete NARestraints selections there.
This is a hypothesis for a selected seam, not a shortcut already implemented:
prove atom-orbit/scattering equivalence, preserve the moved boundary's chemistry,
and track every displaced periodic connection. Simply adding symmetry copies
would change model content. A periodic network can retain unavoidable seams;
recutting cannot be assumed to make every contact local at once. Keep this route
in the existing Pine track rather than making a new cut engine inside TopoStitch.

### W37 — Complete canonical pair recipe backend

The previous complete-recipe checks used local diagnostic scripts. The reusable
backend now freezes and evaluates **caller-declared canonical DNA AT/GC pairs**
at exact symmetry images, with no structure IDs, dataset names or fitted
benchmark constants in its algorithm. This closes one arithmetic/binding gap
in S05; it does not close native repair or refinement integration.

In a Python environment with NASolve's topology dependencies and NARestraints:

```python
from nasolve.topostitch_coordinates import ResidueSite
from nasolve.topostitch_recipe import PairImage, prepare_pair_recipe, recipe_digest

packet = prepare_pair_recipe(
    model_path,
    [PairImage("interface", ResidueSite("A", 12), ResidueSite("B", 4),
               target_operator_xyz="x,y,z", purpose="selected")],
    expected_sha256=verified_model_sha256,
)
digest = recipe_digest(packet)
```

These site numbers/operator are placeholders: the caller supplies verified
topology and exact source bytes. Existing duplex pairs can be listed with
`purpose="core"`; no partner, capacity or topology inference is performed.
Save the returned JSON with the canonical `recipe_digest`, which differs from
the hash of pretty-printed file bytes. Consumption requires an explicit model
path plus the packet digest; there is no basename search or hidden path fallback.

Schema 1, kind `topostitch-canonical-image-recipe`, binds the source hash, exact
PDB atom order/identities, cell/group, full lattice shifts, selected/core roles,
effective NARestraints role maps, emitted PHIL, term counts and hashes. It rejects
missing plane-only atoms, ambiguous/partial-occupancy selected residues,
noncanonical selected chemistry, unsupported cell/operator conventions and
duplicate/reciprocal requested edges. Different lattice images remain distinct;
their simultaneous physical partner capacity is **not** thereby approved.

The emitted PHIL uses virtual **L/R, residue 1** labels solely for selection
binding. **Do not pass that PHIL directly to `phenix.refine` on the original
model.** No virtual atom is added to the scattering model. Atom-order checks
explicitly disable IOTBX's default sorting; a changed order is an error rather
than a silently misbound restraint. The packet and existing preview schemas are
separate; schema-1/2 preview replay and ordinary workflow interfaces are unchanged.

Inside the qualified native interpreter, `NativePairRecipe(packet, model_bytes,
expected_recipe_sha256=digest, correction=trusted_cedar_module)` compiles native
Cartesian proxies. `evaluate(points, atom_identities=exact_ordered_ledger)` returns
four component energies and ASU gradients; `compute_gradients=False` requests
energy only. `native_atom_identities(hierarchy)` supplies the native ledger, and
`binding_report()` returns detached terms/transforms and correction provenance.
The trusted Cedar correction module is explicitly supplied executable code,
never loaded from a captured recipe. Imports remain optional until construction.

The policy is **unnormalized additive pair energy**. Shared ASU atoms accumulate
all image contributions. Bond-like contact terms do not edit native bond tables,
exclusions or covalent links. There is no stacking term, movement mask, native
manager callback, optimizer, density target or scientific approval. An eventual
full objective must declare those semantics and use Cedar's qualified owners;
this API must not be mistaken for a standalone geometry optimizer.

The committed developer probe is read-only and refuses an existing output:

```bash
phenix.python scripts/probe_topostitch_pair_recipe.py   --model /explicit/source.pdb --recipe /explicit/recipe.json   --recipe-sha256 CANONICAL_JSON_SHA256   --cedar-source /explicit/trusted/cedar/src --out /explicit/new-probe.json
```

It checks every referenced ASU coordinate at 1e-4 and 1e-5 Å, within an explicit
coordinate budget (default 1,200, maximum 10,000). Both maximum absolute errors
must be ≤1e-4 for `DERIVATIVES_PASS`; exit 2 means `DERIVATIVE_REVIEW`. It also
rejects stale source/recipe hashes, changed atom order/count, nonfinite points,
negative sigma, partial planes and unsupported PHIL fields. Energy-only parity,
zero unreferenced gradients, detached caller data and unchanged inputs/numerical
sources are checked. This is a developer qualification gate, not an acceptance
threshold for chemical geometry.

Complete energy/derivative executions used **Phenix 2.2.1-6174**, actual
NARestraints 1.1.3 recipes, and frozen Cedar `cd744e2`'s existing both-first-planes
correction. No refinement or optimization was run:

| Frozen control | ASU coordinates | Maximum error at 1e-4 / 1e-5 Å | Outcome |
| --- | ---: | --- | --- |
| 8D93 candidate, 2 interface + 12 core pairs | 798 | 3.35e-6 / 4.20e-8 | PASS |
| Independent 7R96, one AT and one GC | 114 | 3.02e-6 / 6.38e-8 | PASS |
| Independent 5W6W, one AT and one GC | 114 | 3.09e-4 / 3.18e-6 | REVIEW |
| Synthetic P43, shared ASU atoms in two images | 57 | 8.31e-6 / 1.55e-6 | PASS |
| Synthetic skew P21, shared ASU atoms in two images | 57 | 4.56e-6 / 2.74e-6 | PASS |
| Synthetic skew P1, deliberately strained coordinates | 57 | 3.38e-3 / 3.30e-5 | REVIEW |

All eight rejection controls pass in these executions. Independent structure
fixtures use the first canonical AT/GC pairs in NARestraints' sorted guessed
list, with identity images and no score-driven selection; the guesser is used
only to prepare these local fixtures, not integrated into the product.

The 5W6W and strained-P1 failures remain REVIEW under the declared rule. At each
flagged coordinate, additional step-size diagnostics show approximately quadratic
finite-difference truncation followed by floating-point limits; the changing
component is principally the angle term. The 5W6W selected angle reaches 175.96°;
the artificial P1 fixture reaches 0.78°/179.22°. This supports a numerical
step-size explanation at those coordinates, not blanket derivative qualification
or a reason to loosen the gate. A future general derivative audit should declare
its convergence/error policy before using it to qualify optimization.

The complete 8D93 energy (564.9181277186) matches the preceding independent local
selected/core composition to roundoff. Isolated installed-wheel native execution
reproduces it with identical components. All scientific inputs, packets, native
logs and receipts remain local and excluded from Git. Cedar C274's active AutoSol
publication work has no source overlap with this component; no combined branch
build is claimed. Complete native movement/normalization/lifecycle policy,
packing and matched damaged-model refinement remain the next S05/S06 gates.

### W38 — Explicit movable coordinates and direct native composition

`CoordinateMask` in `topostitch_transport` maps a caller-ordered, bounded
displacement vector to the full ASU. Unlisted coordinates remain exactly equal
to the frozen source. Gradient projection retains the full objective's
interactions with those fixed atoms; it does not remove their restraints.
Inverse mapping rejects changed fixed coordinates. The mask owns arithmetic,
not permission to move a residue, junction or chemical group.

`NativeMaskedObjective` in `topostitch_native_recipe` now composes Cedar's
`evaluate_fixed_native(..., plane_order_safe=True)`, a W37 `NativePairRecipe`,
and an explicit isotropic Cartesian tether. Its variables are displacements
from exact PDB source coordinates, in the requested index order. The target is
the **unnormalized sum**, with native and pair weights one and tether
`sum(delta² / sigma²)`; all ordinary native geometry flags are enabled.
No geometry manager callback or bond/exclusion edit is installed.

The constructor takes the caller's geometry manager, interpreted hierarchy,
exact model bytes, compiled pair binding, explicit movable indices, expected
Cedar static-definition signature, trusted correction/audit modules, tether
sigma, atom-displacement bound and evaluation-call budget. `evaluate(delta)`
returns the target, reduced gradient, full points and separate native/pair/tether
components. `binding_report()` records the source/recipe/definition hashes,
mask identities/order, correction and audit source hashes, and declared limits.
Schema 1 kind `topostitch-masked-native-objective` is additive; old preview and
recipe packets remain unchanged. This is an in-memory evaluator, not a run or
checkpoint reader/writer.

Identity, crystal, special-position and fixed-definition checks run before
evaluation; the definition and native-reference checks repeat afterward.
Unexpected callbacks, auxiliary managers, reference-coordinate proxies,
changed identities/source coordinates, invalid masks, nonfinite/excess motion,
nonrepresentable tether weights and exhausted budgets are refused. Native
interpretation's measured roundoff (7.11e-15 Å in the reference control) is
allowed up to 1e-10 Å at initial binding; the original PDB coordinates remain
the exact fixed reference, and later native hierarchy changes are rejected.

The caller still owns native construction, trusted input/CIF/PHIL context and
capture authentication. Cedar's static-definition signature is reused as-is:
it does **not** authenticate the complete nonbonded/exclusion policy or freeze
neighbour membership. Consequently this component does not qualify a production
masked optimizer, manager rebuild/continuation, packing, refinement or campaign
adoption. It does not select the mask or infer topology. That boundary is a
required next integration step, not an implicit approval in this report.

The developer command `scripts/probe_topostitch_masked_objective.py`, run with
`phenix.python`, accepts `--model`, `--recipe`, `--recipe-sha256`, `--mask`,
`--mask-sha256`, `--cedar-source` and a new `--out` JSON file. The mask checksum
is the **file-byte SHA256**; the recipe checksum remains canonical JSON.
The mask request has schema 1, kind `topostitch-native-mask-request`, source
model SHA256, `movable_indices`, `tether_sigma_angstrom`,
`max_displacement_angstrom` and `max_evaluations`. Unknown fields are refused.
The probe interprets through installed monomers with NCS restraint building
disabled and retains effective PHIL/logs; it is not authenticated Cedar capture
replay and has no custom dictionary input in this first diagnostic scope.

Complete **Phenix 2.2.1-6174** energy/derivative executions use every masked
coordinate at the source and at a frozen, input-independent sinusoidal
perturbation of amplitude 0.002 Å. The 1e-3 absolute derivative bound at steps
1e-4/1e-5 Å was declared from the earlier full-native diagnostic policy before
execution; W37's separate stricter pair-only review outcomes are unchanged.
There is no optimization, refinement or new scientific candidate:

| Explicit control / coordinates | Variables | Maximum absolute errors, 1e-4 / 1e-5 Å | Outcome |
| --- | ---: | --- | --- |
| fixed-base, zero | 321 | 9.95e-05 / 1.05e-06 | DERIVATIVES_PASS |
| fixed-base, nonuniform | 321 | 9.92e-05 / 1.06e-06 | DERIVATIVES_PASS |
| whole-window, zero | 612 | 0.000266 / 2.68e-06 | DERIVATIVES_PASS |
| whole-window, nonuniform | 612 | 0.000266 / 2.68e-06 | DERIVATIVES_PASS |
| 7r96, zero | 246 | 0.000194 / 1.93e-06 | DERIVATIVES_PASS |
| 7r96, nonuniform | 246 | 0.000194 / 1.99e-06 | DERIVATIVES_PASS |

The 8D93 controls reuse the prior exact-source-bound 107-atom sugar/phosphate
mask, then all 204 atoms of those same explicitly movable residue sites. They
leave 748 and 651 atoms fixed respectively. The independent 7R96 control moves
all 82 atoms in the two canonical pairs selected by the earlier frozen fixture
rule, leaving 773 atoms fixed. These native controls cover canonical movable
residues; broader chemical movement policies remain unqualified. Mask selection
is fixture input, not structure-specific logic in the evaluator. Both source and perturbed
targets also match separate direct native/pair/tether calculations.
Ten negative controls reject changed signature, duplicate indices, nonfinite
variables, excessive displacement, underflowing sigma, budget exhaustion,
unexpected callback, altered native coordinates/identity and changed native
angle weight. Deliberate in-memory negative-control mutations are restored;
input files and numerical sources remain unchanged.

The isolated installed wheel reproduces the fixed-base source and perturbed
targets from exact installed module bytes. Native packets/logs/models and the
mask receipts are local only. Source regression, installed and relocation
counts are in the current inspector receipt. S05 stays partial pending complete
native policy/capture qualification, endpoint geometry/packing and a bounded
trial; no end-to-end stitching or diffraction benefit is claimed.

### W39 — Reconstruct the observed native starting context

W38 accepted a caller-constructed manager. The developer probe now authenticates
an explicit Cedar capture through its existing owner, freezes its inputs, builds
**fresh trusted worker code**, and keeps the reconstructed manager for masked
evaluation. Captured worker text is authenticated evidence and is never executed.
Cedar also owns native discovery, process timeout/cleanup, monomer review and ASU
pair replay. No Cedar code or shared environment is changed.

```bash
python scripts/probe_topostitch_captured_objective.py \
  --model SOURCE.pdb --native-receipt CAPTURE/native_receipt.json \
  --recipe COMPLETE.json --recipe-sha256 CANONICAL_JSON_SHA256 \
  --mask MASK.json --mask-sha256 MASK_FILE_SHA256 \
  --cedar-source /trusted/cedar/src --phenix-root /installed/phenix \
  --output-parent /local/new-probes
```

Run this in ordinary Python with Cedar's host dependencies; the owned child uses
that installation's `phenix.python`. Require a linked, policy/energy/full-monomer
capture with explicit `cif-native-nonbonded-asu-attribution-v1` inventory and fixed
native NA policy. Mapping/gradient capture extensions are outside this probe.
The bare NCS-building PHIL setting belongs to native interpretation here; it is
**not** emitted as ordinary `phenix.refine` input. Rowan's separate consumer-specific
PHIL adaptation work remains Cedar-owned.

The new optional `topostitch_capture.compare_reconstructed_context` compares every
observed report field, including full monomer definitions, native geometry,
initial energy/gradient and directed symmetry-pair inventories. Only exact
`module`/SHA256 source records may differ in their historical path. Changed
fields, missing inventory, normalization, competing secondary structure and
unexpected claims fail. This function consumes authenticated/reviewed records;
it does not replace Cedar's capture reader.

Each immutable local probe has relative staged inputs/runtime sources, the old
capture for review, a newly built bootstrap, repeated source/nonuniform masked
evaluations, checksums and a schema-1 receipt. Its matching status is diagnostic,
not scientific approval or a resumable NASolve checkpoint. No model is written.
The complete exclusion/neighbor-generation policy is **not** authenticated merely
by matching its initial observed contacts; future movement still needs qualification.

Complete **Phenix 2.2.1-6174** controls reproduce all initial observations and match
W38's source/nonuniform native, pair and tether energies exactly for the 107-atom
fixed-base mask, 204-atom whole window and independent 82-atom 7R96 mask. Wrong
recipe/mask hashes and a tampered captured worker with recomputed file hashes are
rejected before execution. The relocated checkout/capture and installed-wheel
backend independently reproduce the fixed-base check. These are complete energy
and reconstruction executions, not dry-runs or new derivative qualification.
Scientific models, captures, generated workers and reports stay local.

S05 remains partial. Next qualify a bounded trial's full native lifecycle and
individual geometry/packing at full precision and serialized coordinates; preserve
existing W37 derivative-review outcomes and avoid native/additive pair double counting.

### W40 — Bind endpoint review to movement and serialized bytes

`topostitch_endpoint.audit_masked_endpoint` checks a supplied full-precision
endpoint and candidate PDB against an explicit mask. It requires identical atom
identity/order, unchanged fixed records and **every noncoordinate byte**, exact
8.3 coordinate serialization, and the displacement limit both before and after
rounding. Full-precision fixed motion cannot hide below PDB precision. This audit
writes nothing; first scope is full-occupancy canonical DNA without movable
alternate conformers. It is not a geometry or chemistry acceptance decision.

The existing packing reader optionally binds that audit to authenticated source
and candidate native captures:

```bash
python scripts/compare_topostitch_native_packing.py \
  --cedar-source /trusted/cedar/src \
  --before-model SOURCE.pdb --before-receipt BEFORE/native_receipt.json \
  --after-model CANDIDATE.pdb --after-receipt AFTER/native_receipt.json \
  --mask MASK.json --mask-sha256 MASK_FILE_SHA256 \
  --full-precision POINTS.json --full-precision-sha256 POINTS_FILE_SHA256 \
  --anisou-policy preserve-cartesian --out ENDPOINT_REVIEW.json
```

`POINTS.json` is the complete ordered ASU Cartesian point list; the mask is the
existing schema-1 source-bound request. The four mask/point arguments are supplied
together. Without them the original packing report retains its behavior/content.
Cedar's fixed-policy geometry checker must confirm unchanged native identities,
definitions, proxies and context. Its selected-environment reviewer supplies
separate selected-only, boundary and fixed-only scalar/repulsion observations.
The full-precision scalar projection, serialized native observations and directed
packing changes remain distinct. Full-precision native energies/packing and
endpoint derivatives are explicitly **not evaluated by this read-only command**.

The default tensor policy rejects movable ANISOU. For coordinate-only trials,
`preserve-cartesian` explicitly keeps each associated tensor byte unchanged; it
neither invents a rotation for nonrigid movement nor qualifies thermal motion.
Rigid previews retain their separate existing tensor-rotation owner. Rowan
confirmed this limited interpretation; no Cedar change was needed.

Three complete **Phenix 2.2.1-6174** endpoint captures from W39's nonuniform
controls pass exact serialization and native mechanics: 107-, 204- and independent
82-atom masks. All contain movable ANISOU; the initial default rejections remain
recorded before explicit preservation was declared. Full-precision maximum motion
is about 0.002517 Å; rounding reaches 0.003 Å, with maximum roundtrip error about
0.000676 Å. This is a serialization control, not an optimized repair.
The fixed-base example lowers native repulsion 1077.7216 → 1077.1472 while 38
existing directed contacts worsen; the whole-window and 7R96 controls worsen
89 and 40 respectively. Neighbor-list additions/removals remain separate from
resolved/new overlaps. No candidate is selected or called chemically acceptable.

Relocated copied code/captures reproduce the complete review **byte-for-byte**
with the original temporary checkout absent and old capture/source reads blocked.
Installed endpoint audits reproduce all three source results. Scientific inputs,
perturbed models and reports stay local. S05 still needs a bounded optimization
and full-precision/serialized derivative, geometry and packing qualification;
this review does not close those gates.

### W41 — Bounded native trials and matched cleanup controls

`nasolve.topostitch_trial` supplies one shared all-variable derivative checker
and a bounded installed-scitbx trial. W38's diagnostic and the W39 captured
probe reuse it. Initial, full-precision and PDB-rounded endpoints each require
both predeclared finite-difference steps (10⁻⁴ and 10⁻⁵ Å), maximum absolute error
≤10⁻³ and exact repeated target/gradient. Raw plus/minus samples remain available.
The mask, native definitions, fixed atoms and existing source checks still apply.

To explicitly extend the W39 command into a diagnostic trial, add:

```sh
--trial-iterations 200 --trial-calls 2000
# Matched cleanup: identical inputs/mask/tether/limits, zero additive pair weight:
--trial-iterations 200 --trial-calls 2000 --without-pairs
```

The default remains read-only. The existing explicit mask must budget all three
full derivative audits plus optimizer calls. Trial iterations are limited to
1–500 and optimizer evaluations to 10–5000. Existing motion limits are hard
rejection bounds, **not a box-constrained optimizer**; crossing one is a failed
trial, not proof that the connection is impossible. Native geometry edits are
outside this first trial scope; existing native secondary-structure terms also
remain excluded. This conservative gate avoids unqualified native/additive pair
duplication. Cleanup still reports unweighted pair scores but uses zero pair
energy/gradient. Native geometry and tether remain identical policies.

Five complete **Phenix 2.2.1-6174** controls used 200 iterations, 2000 optimizer
calls, a 0.1 Å tether sigma and 0.5 Å maximum selected-atom motion: 8D93 fixed-base
paired/cleanup, whole-window paired/cleanup, and independent 7R96 paired. All
source/full-precision/rounded derivative checks pass; the largest error is below
0.000266. All five stop at the iteration limit with the native convergence
criterion false. `ENDPOINT_DERIVATIVES_PASS` and `BOUNDED_TRIAL_REVIEW` describe
numerical evidence, **not convergence, physical acceptance or adoption**.

Fresh ordinary native captures of all five rounded endpoints reproduce their
trial native target (absolute tolerance 10⁻⁸, relative 10⁻¹⁰). The existing W40
reader verifies exact fixed/noncoordinate bytes, explicit Cartesian ANISOU
preservation and Cedar-owned mechanics/selected-environment evidence. The
whole-window paired control clears three affected scalar angle deviations ≥5
nominal sigma while fixed-only source outliers remain. This scalar review still
defers other chemistry; it is not complete DNA validation.

| Rounded 8D93 endpoint | Unweighted pair target | Native repulsion | Worsened existing directed contacts |
| --- | ---: | ---: | ---: |
| Source | 564.9181 | 1077.7216 | — |
| Fixed-base paired or cleanup | 564.9181 | 1066.0108 | 55 |
| Whole-window paired | 435.8030 | 1002.2450 | 110 |
| Whole-window cleanup | 575.3480 | 1000.3669 | 108 |

Pair atoms are fixed in the first mask, so pair terms are constant and cannot
pull the bases; paired/cleanup serialized models are identical. Whole-window
pair terms improve their intended score while cleanup favors a different
geometry/packing tradeoff. The independent 7R96 pair score falls 466.2860 →
225.8504, with 51 worsened directed contacts. Counts are captured directed rows,
not unique physical clashes or MolProbity statistics. New overlaps and changed
neighbor membership remain separately reported. No threshold was tuned and no
candidate was selected. Full-precision endpoint native targets/derivatives are
checked; fresh native packing review is currently for serialized endpoints only.

An insufficient evaluation budget rejects before optimization. The native
manual-edit negative and installation/relocation checks are recorded in the
[current validation receipt](topostitch-periodic.md#current-validation-receipt--2026-11-13).
No Phenix refinement, diffraction comparison, Coot run, campaign adoption or
Cedar edit is included. Source inputs, all trial traces, endpoint captures and
failed checks stay local. The next integration step is one installed captured-job
boundary reusing Cedar process/anchor owners; geometry qualification and matched
refinement remain explicit S05/S06 gates. No checkpoint schema is migrated.

### W42 — One installed captured-job boundary

The developer capture/trial command now calls
`nasolve.topostitch_captured_job.run_captured_objective`. The installed API accepts
explicit `model`, `recipe`, `mask`, `native_receipt`, `output_parent`, canonical
`recipe_sha256`, file `mask_sha256`, and `phenix` (a discovered installation or
explicit installation root). It returns `(new_directory, report)`. Optional
`trial_iterations=0`, `trial_calls=2000`, `include_pairs=True` and
`timeout_seconds=600` retain the W41 defaults and bounds. No new end-user CLI,
checkpoint schema, implicit source discovery or input-by-basename search is added.

Default `cedar_source=None` consumes the Cedar owners in the same installed
NASolve package. Willow alone still needs an explicit trusted Cedar source for
execution until integration is qualified; importing the API remains dependency
light. The existing `--cedar-source` CLI option continues to work. Its temporary
module namespace is isolated and released after each call, including errors, so
one process can run successive jobs without reusing a prior developer namespace.
The CLI still prints the new directory/status and preserves its exit meanings.

The adapter reuses Cedar capture authentication, exact ordered snapshots and
`_native_context_worker` observation layering. Cedar's general captured-gradient
`_inputs` scope excludes ASU nonbonded inventory, so it is not broadened or bypassed
as a purported full optimizer qualification. The explicit ASU capture checks stay
in the existing TopoStitch boundary. Exact native dispatcher bytes are checked
before and after execution. Discovery may report `2.2.1` while a capture records
`2.2.1-6174`; both labels remain provenance, with dispatcher/native-source bytes
providing the identity binding.

`_process_runner` accepts the existing Cedar owned-runner protocol and is forwarded
to its `_run_native_command`; no executor or process group implementation is
added. Verified timeouts retain a failed receipt. `CampaignProcessError`, including
uncertain cleanup or expired-before-launch allowance, escapes to the owner after
the diagnostic receipt is saved. Deleted input/dispatcher bytes are recorded as
preservation failures without losing the receipt. These are execution outcomes,
not chemical verdicts. A future campaign caller must still own resource admission,
checkpoint lineage, review and adoption; this API does not register itself there.

Complete **Phenix 2.2.1-6174** source read-only and one-iteration trial executions
reproduce W41 evaluation content exactly, including fresh bootstrap worker bytes.
Installed Willow and a temporary combined Cedar/Willow package also complete
read-only native evaluation from relocated inputs with original paths blocked;
the combined path uses same-package owners and the injected runner exactly once.
The temporary package uses Cedar commit `948a7860` plus nine explicit Willow
modules. This is tested adapter compatibility, **not a branch merge or complete
combined-suite qualification**. Three actual Cedar-runner failure controls launch
no native process: verified timeout, unverified cleanup and prelaunch expiry all
retain the appropriate receipt/exception behavior.

See the [validation receipt](topostitch-periodic.md#current-validation-receipt--2026-11-13)
for counts, wheel hashes and retained initial setup failures. Scientific files
remain local. S05 remains partial: next review full-precision as well as serialized
packing and affected chemistry, then use matched diffraction rather than lower
geometry energy alone to establish repair benefit.

### W43 — Full-precision endpoint observations

The existing captured-job command accepts one explicit read-only endpoint:

```sh
# Add these to the W39 explicit model/recipe/mask/capture arguments:
--endpoint-points full-precision.json --endpoint-sha256 FILE_SHA256
```

The installed API uses `endpoint_points` and `endpoint_sha256`. Both are required
together and cannot be combined with `trial_iterations`. The file is an ordered
JSON array of Cartesian `[x, y, z]` points for every original atom. Before native
launch, its file hash, atom count, finite values, exact fixed coordinates and
full-precision/rounded motion bounds must match the source-bound mask. This
mode does not write a PDB, optimize, refine or infer a connection.

One freshly reconstructed, authenticated source manager evaluates the source,
full-precision endpoint and three-decimal endpoint. The rounded observation
includes the same binary displacement expansion as the actual masked evaluator;
it is not claimed to be a literal PDB reparse. Each case retains repeated composed
native/pair/tether evidence and two **actual native directed-ASU snapshots**, using
Cedar `capture_asu_pairs`. Cedar's native energy/gradient and pair-kernel replay,
selected/boundary/fixed environment reviewer, and the existing packing comparator
then assess the observations. Raw native gradients used for capture replay remain
distinct from the corrected composed mask gradient. No derivative qualification
is inferred merely from an endpoint observation; W41 owns those earlier checks.

The schema-1 `topostitch-native-coordinate-observations` payload and
`topostitch-native-endpoint-review` artifact explicitly carry
`FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION`. A transient coordinate projection
is only an input to the existing pure reviewers; it is never saved as an ordinary
native model capture. The outer receipt binds the review through its existing
relative artifact inventory. Fixed-manager observations do not establish universal
neighbor/exclusion behavior or chemical acceptance.

Five complete **Phenix 2.2.1-6174** controls use the W41 endpoints unchanged:

| Endpoint | Full-precision repulsion | Rounded repulsion | Worsened directed contacts, full / rounded |
| --- | ---: | ---: | ---: |
| Fixed-base paired | 1066.1577 | 1066.0108 | 54 / 55 |
| Fixed-base cleanup | 1066.1577 | 1066.0108 | 54 / 55 |
| Whole-window paired | 1002.1383 | 1002.2450 | 110 / 110 |
| Whole-window cleanup | 1000.3205 | 1000.3669 | 109 / 108 |
| Independent 7R96 paired | 572.1503 | 572.2094 | 51 / 51 |

These are descriptive directed rows, not unique clashes or an acceptance cutoff.
All five rounded fixed-manager observations agree with the independently
interpreted W41 PDB captures in full native target/gradient and matched pair
residuals. Fresh interpretation changes some neighbor-list entries, but all added
or removed entries have exactly zero residual and nonpositive overlap in these
controls. That finite observation is not an independent proof of neighbor
completeness. The underlying W41 trials remain capped and unselected.

The initial whole-window observation refused a 3.5×10⁻¹⁸ Å decimal/displacement
roundtrip difference near zero. The failed result remains; the explicit binary
expansion now matches the actual evaluator, with a regression. No acceptance
threshold or scientific target was relaxed. Installed/relocated review reproduces
the complete endpoint artifact byte-for-byte with original paths blocked; wrong
endpoint hashes and fixed-atom movement refuse before creating a native job.
The [validation receipt](topostitch-periodic.md#current-validation-receipt--2026-11-13)
records exact scope. All scientific inputs and outputs stay local.

S05 remains partial. Next expose individual intended/core-pair contributions so
an improving aggregate cannot hide a damaged pair, alongside the existing
geometry/packing evidence; then use a declared bend/cleanup comparison. Broader
sugar/torsion/plane qualification and matched diffraction remain open. Density
calibration stays in S06 and no campaign acceptance path is enabled.

### W44 — Individual pair attribution

The endpoint observation now includes `NativePairRecipe.describe_terms`: existing
native bond, angle, planarity and parallelity kernels provide individual residuals
and measurements. Their family/total sums must reproduce the complete containers.
`compare_pair_attribution` checks the complete binding, definitions and arithmetic,
then retains each selected/core pair's change. The raw score remains available
when cleanup uses pair weight zero. Native parallelity delta is a descriptive
angle, **not** a Gaussian sigma score or calibrated acceptance threshold.

All five W41 endpoints completed this read-only check in **Phenix 2.2.1-6174**;
no optimization or refinement was repeated. Both fixed-base controls retain
constant pair terms. In the whole-window paired control, all 12 core and both
selected pair totals improve (full-precision role changes −77.022504 and
−52.141429 respectively). Cleanup alone worsens two core pairs and one selected
pair despite the selected aggregate improving. Both core pairs in the independent
7R96 control improve. These are per-pair totals, not a claim that every individual
term improves. Selected contact distances remain imperfect: for example one
2.120 Å contact reaches only 2.274 Å and another remains about 3.551 Å. Capped
optimization and the W43 collateral packing changes remain unqualified.

The schema-1 diagnostic endpoint review adds `pair_attribution_from_source`, and
raw observations add `pair_attribution` per coordinate case. The existing report
is now written with compact JSON separators. Removing only the new attribution
field reproduces all five old review dictionaries exactly; the whole-window
file shrinks from 109,527,599 to 48,962,830 bytes. No scientific tables are dropped.
These diagnostics are not resumable checkpoints or authority to accept a model.

Validation (complete execution, not a dry-run):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_recipe.py tests/test_topostitch_trial.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider
python3 /private/tmp/willow-w44-pair-attribution/run-controls.py
python3 /private/tmp/willow-w44-pair-attribution/check-legacy-content.py
python3 /private/tmp/willow-w44-pair-attribution/installed-check.py
```

The focused tests passed **50**; complete Willow passed **1,397 + 229 subtests**.
The rebuilt wheel passed **140** installed/relocated focused tests and reproduced
one entire native endpoint report byte for byte after moving the temporary
checkout and blocking original source/input paths. Wrong endpoint hashes and
fixed-atom motion refuse before native job creation. Local execution receipts
retain the expanded native commands and exact inputs; these historical paths
are provenance, not committed operational artifact references. Scientific
coordinates/captures/reports and wheels remain local and excluded from Git.

S05 remains partial. Next predeclare a bend/cleanup comparison using these same
owners, then qualify affected chemistry before matched diffraction refinement.
No Cedar edits, branch merge, campaign adoption or physical partner-capacity
qualification is implied.

### W45 — Matched retained-core control

The W41 cleanup control removed all additive pair terms. W45 isolates the effect
of the two intended contact pairs by retaining the identical 12 core pairs in
both arms. Existing `prepare_pair_recipe` reproduces the old complete packet
exactly and generates the core-only packet; no new runtime API is necessary.
The original paired trial is reused, with immutable receipts verified.

One new complete **Phenix 2.2.1-6174** trial uses the same captured source, 204-atom
mask, 0.1 Å tether, 0.5 Å motion bound and 200-iteration/2,000-optimizer-call caps.
All 612 initial/full-precision/rounded derivatives pass at both declared steps
(maximum error 0.000266). It stops at 200 iterations/209 calls and is explicitly
**NOT_CONVERGED_LIMIT**. No budget, weight or Free-R tuning was performed.

Both endpoints are observed using the same complete packet:

| Full-precision observation | Core only | Core + selected |
| --- | ---: | ---: |
| Native geometry target | 6544.928214 | 6546.376345 |
| Core pair target | 259.112026 | 259.106108 |
| Selected pair target | 226.973167 | 176.648087 |
| Tether target | 90.975770 | 112.271268 |

All core pair totals improve in both arms. One selected pair worsens in the
core-only control; both improve when included. Individual packing still worsens:
113/112 directed contacts in full-precision/rounded core-only observations,
versus 110/110 with selected terms. These counts are descriptive, not independent
chemical clashes or an acceptance threshold. Fresh rounded interpretation agrees
in full native target/gradient and matched pair residuals; changed neighbor rows
have zero contribution in this control. Numerical improvement is not repair.

Exact expanded native commands, frozen plan and comparisons remain in local
execution receipts. Validation commands were:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w45-core-control/prepare-and-run.py
PYTHONDONTWRITEBYTECODE=1 /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w45-core-control/prepare-endpoints.py
PYTHONDONTWRITEBYTECODE=1 /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w45-core-control/capture-endpoints.py
python3 /private/tmp/willow-w45-core-control/observe-complete.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w45-core-control/compare-fresh.py
python3 /private/tmp/willow-w45-core-control/summarize.py
```

All completed successfully; this is actual native execution, not a dry-run.
Runtime code and artifact schemas are unchanged, so W44 full-suite/installation
results still apply. Scientific inputs, generated coordinates and captures are
local only; the archive is evidence, not a resumable NASolve run. Historical paths
above are provenance. Next reuse Cedar's maintained native torsion/plane kernels
for complete endpoint observations, checking live proxy policy and container sums
rather than reconstructing missing symmetry. Ordinary refinement enforcement,
sugar-pucker/chemical acceptance and matched diffraction remain open.

### W46 — Native torsion and monomer-plane observations

`NativeTermObserver` composes Cedar `native_plane_evaluator`, `native_evaluator`
and `dihedral_geometry` into the existing endpoint job. It checks complete live
proxy definitions, explicit identity symmetry, and torsion limit/top-out/slack
before calling local kernels. Missing properties and unsupported semantics refuse.
Each original live proxy must agree in target/gradient with two repeated Cedar
single/container evaluations. Scattered gradients and residuals must reproduce
the full native family container; residuals also match the composed native target.
This is fixed-point observation, not a derivative or chemical qualification.

The schema-1 raw coordinate observation adds `native_terms`; the endpoint review
adds `native_terms_from_source`. Complete per-proxy measurements and changes retain
selected-only, boundary and fixed-only dependence. All old review dictionaries
remain identical after removing this one new field. Other native families,
including `const_dihedral`, remain explicitly deferred by this observer; no
sugar-pucker assignment, Gaussian torsion score or acceptance threshold is added.

Six complete **Phenix 2.2.1-6174** endpoint controls pass: five W41 endpoints plus
the W45 core-only control. Each 8D93 coordinate case checks 442 active torsions
and 42 planes through 2,422 kernel interfaces; 7R96 checks 440 and 42 through
2,412. No near-collinear torsions occur under Cedar's recorded descriptive screen.
All fixed-only terms stay unchanged. The whole-window paired trial reduces the
overall plane residual from 118.787933 to 117.809119, yet five individual planes
increase. Fixed-base cleanup raises the A103 plane RMS from 0.013112 to 0.019482 Å
because its C1′ moves while base atoms stay fixed. Counts/changes are descriptive;
they do not establish new chemical outliers or a successfully repaired model.

Validation commands (complete native execution, not dry-run):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_native_terms.py tests/test_topostitch_captured_job.py tests/test_topostitch_trial.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider
python3 /private/tmp/willow-w46-native-terms/run-controls.py
python3 /private/tmp/willow-w46-native-terms/installed-check.py
python3 /private/tmp/willow-w46-native-terms/summarize.py
```

Focused: **40 passed**. Full Willow: **1,416 + 229 subtests**. An initial sandbox
run refused five existing process-group tests with `PermissionError`; its log is
retained, and the permitted complete rerun passed. Actual native proxy controls
accept defaults and reject slack, top-out, nondefault limit and nonidentity images.
Installed/relocated: **159 passed**, plus a byte-identical native endpoint report
with original source/input paths blocked and hash/fixed-coordinate negatives.
Five installed entry points, dependency-light module imports and Python 3.10
syntax pass. Wheel SHA256:
`0719d7f4d594cd9e5c92ab99e40e118d218259b3a61f93dccafd1528c0e97571`.

A temporary installed Cedar **7e843af7 (C289)** plus explicit Willow adapter
modules also reproduces the entire endpoint report byte for byte through the
same-package owners and injected owned runner, with original paths blocked.
Its focused adapter tests pass **159**; one initial missing-wrapper fixture error
is retained and corrected. This is compatibility evidence, not a branch merge or
complete combined-suite qualification.

The reused numerical function sources match frozen Cedar f2345a8 and the inspected
Cedar cbece417 checkout exactly. No Cedar files changed. Scientific data/captures,
local harnesses and generated reports stay outside Git; recorded temporary paths
are provenance, not operational references in a committed run. No checkpoint
schema migration is needed. S05 remains partial: chemical acceptance, physical
connection capacity and ordinary refinement enforcement are still open. Rowan's
reported C289 ordinary full-objective force discrepancy remains separate consumer
evidence; Willow does not install a corrected ordinary refinement route.

### W47 — One periodic edge and its reciprocal partners

A declared `A → g(B)` connection also requires `B → g⁻¹(A)` at the identity
representatives. The existing pairing owner now supplies that exact incidence
calculation to the image audit. A self-edge through an involution can have one
partner; a screw, translation or centering translation can give distinct forward
and inverse partners. Operators are never reduced modulo the unit cell when
counting them. This calculation supplies a shared primitive for Pine's graph.

Source and transformed image audits add `single_edge_capacity`, bound by a digest
of the complete enclosing coordinate audit before that field is added. Its
`ONE_PARTNER_IN_SELECTED_SCOPE` outcome is conditional on distinct present
selected atoms at the recorded coincidence tolerance. Shared atoms under distinct
end labels, identity self-edges, coincidences, special-position ambiguity and
partial occupancy stay under review. `MULTIPLE_PARTNERS_IN_SELECTED_SCOPE` is a
conflict for the declared one-partner hypothesis, not a blanket rejection of
periodic networks. Global assignment and full molecular identity remain false.
No sequence/orientation, covalent connectivity, geometry or adoption is approved.

Periodic fitting now requires that scoped outcome in addition to its prior
coordinate-identity guard; otherwise it returns `CONNECTION_CAPACITY_REVIEW_REQUIRED`
without solver calls. Proposal algorithm becomes v5; request/preview schemas and
explicit-path CLI arguments stay compatible. Existing pairing alternatives retain
their prior conservative self-edge deferral. No new inference or cut is selected.

Validation:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_images.py tests/test_topostitch_pairings.py tests/test_topostitch_fit.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/willow-periodic-install/lib/python3.12/site-packages /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python /private/tmp/willow-w47-capacity/public-control.py
python3 /private/tmp/willow-w47-capacity/installed-check.py
```

Focused **68**, full Willow **1,424 + 229 subtests**, installed/relocated **68**
pass. P1 translation, P2 involution, C2 centering and P43 screw controls preserve
exact reciprocal distinctions; centroid coincidence does not imply atom identity.
The public 8D93 source and moved-end audits both support one partner in scope.
After excluding only new capacity metadata and the algorithm version, its complete
prior placement report reproduces exactly. The installed wheel repeats that after
moving the temporary checkout and blocking original source/input paths. Original
scientific files are unchanged; generated evidence remains local, not Git.
Five entry-point checks, lean imports and Python 3.10 syntax pass. Wheel SHA256:
`25404b11b03f7973ec2e13eeb207fcf6d9f4f35b5c76f2540972577fb3f41232`.
No Phenix/Coot execution was needed for this host-side image calculation.

F02/S03 remain partial for complete molecular equivalence and global schemes.
Next build the minimum read-only declared graph for one proposed Pine cut,
retaining typed edges, unknown coverage and nonzero periodic winding. This may
prototype algebra before the remaining physical/materialization gates close;
it does not authorize a recut or replace S05 chemistry/refinement work.

### Shared image-coordinate transport

`nasolve.topostitch_transport` owns the rigid Cartesian operation used by the
viewer and native image probe. `crystallographic_image(cell, group, operator)`
validates group membership (including a retained lattice shift) and compiles
`x_image = R_cart x_ASU + t_cart`. Its `CartesianImage` core also accepts explicit
finite proper Cartesian matrices without importing Gemmi or Phenix; those
matrices alone are numerical inputs, not proof of crystallographic membership.

W94 adds `CartesianImage.around_pivot(rotation, pivot, translation=(0,0,0))`
(translation is keyword-only). It compiles `R(x-p)+p+t` into the existing rigid
image, with translation applied after rotation and the same inverse, tensor and
gradient rules. `(I-R)p+t` preserves a small translation at a large pivot under
identity rotation. Invalid/improper rotations, nonfinite vectors and overflowing
offsets are rejected. This explicit numerical constructor neither infers a
molecular axis nor authorizes a placement or symmetry operation. The preview
uses it for ANISOU transport; centered coordinate arithmetic and serialized PDB
replay retain their existing rounding. Three-orientation campaign execution is
still planned, strictly after PostMR and first refinement, with no MR rerun.

`expand_sites` retains each explicit atom/image instance.
`accumulate_image_gradients` applies `R_cart` transpose and **adds** all image
contributions to their shared ASU atom. Repeated ASU indices are intentional;
using the forward rotation or overwriting a prior image contribution gives the
wrong derivative. No restraint, atom mask, topology or native-policy authority
is inferred. This is the common numerical boundary for a future native adapter,
not that adapter itself.

Tests compare independent fractional/Gemmi paths in skew P1, P43, R3:H and
centered cells, inverse/distance preservation, finite-difference self-image
contacts with repeated ASU indices, invalid bindings and detached immutable
matrices. The native plane probe now uses this same helper and records its source
hash. Under Phenix 2.2.1-6174, Cartesian planarity and Cedar-corrected parallelity
pullback still pass; the intentionally retained raw negative controls still fail.
The viewer keeps JSON arrays and schema 1. Source/candidate PDBs and frozen
preview replay are unchanged; only floating-point display arithmetic is shared.

### W94 validation — 2026-11-16

Nine new cases fail before `around_pivot` exists and pass afterward. They check
an off-origin 120-degree cycle, inverse and post-rotation translation, tensor and
gradient semantics, detached inputs, identity translation at a large pivot,
invalid/improper inputs and overflow. Focused **139**, full **1,844 +229 subtests**
and fresh-wheel **139** tests pass. Six installed CLI helps and `pip check` pass.
The full suite covers the shared numerical boundary; no native external program
was executed, so this is software validation, not Phenix/geometry qualification.

Exact validation commands (temporary paths record historical local provenance):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider tests/test_topostitch_transport.py tests/test_topostitch_preview.py tests/test_topostitch_trial.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/willow-w94-pivot/env/bin/python -m pytest -q -p no:cacheprovider
/private/tmp/willow-w94-pivot/env/bin/python /private/tmp/willow-w94-pivot/install-check.py
env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/install/env/bin/python -m pytest -q -p no:cacheprovider /private/tmp/willow-w94-pivot/install/test-suite/tests/test_topostitch_transport.py /private/tmp/willow-w94-pivot/install/test-suite/tests/test_topostitch_preview.py /private/tmp/willow-w94-pivot/install/test-suite/tests/test_topostitch_trial.py
```

The install check builds an sdist, removes its staging source, extracts elsewhere,
builds a wheel and installs it plus declared test/topology-fit dependencies into a
fresh environment. Tests import the installed package without source PYTHONPATH.
The first harness invocation reached installation/CLI checks but test collection
failed because setuptools' default sdist test selection omitted relative-import
helpers. Supplying the complete relocated test package fixed the harness; the
wheel was unchanged and all 139 tests passed. This does not claim the distributed
sdist contains a self-contained test suite. Wheel SHA256:
`809be293c07093398600ad2fa39b259812ef48cc9e482181e210a89abfdb01a4`.
Generated models/builds/logs stay local and are excluded from Git. No published
scientific dataset or artifact-format migration is part of W94.

### Reproducible native plane gate

The repository includes a small synthetic developer probe (no crystallographic
input files):

```sh
phenix.python scripts/probe_topostitch_native_images.py --out new-probe.json
# Optionally reuse the existing correction from a trusted Cedar source checkout:
phenix.python scripts/probe_topostitch_native_images.py \
  --cedar-source /path/to/trusted/NASolve-cedar/src --out new-corrected-probe.json
```

It records script/native source fingerprints, the explicit R3:H fixture, three
finite-difference step sizes, per-coordinate discrepancies and raw negative
controls. Output must be new. Exit 2 means `NATIVE_DERIVATIVE_REVIEW`; it is the
expected result on the tested installation because failing raw controls remain
in the report even when an alternate evaluation path passes. The optional source
is trusted executable project code, not a captured diagnostic worker.

Complete Phenix **2.2.1-6174** executions of both forms reproduce the following:

| Evaluation path | Maximum component error at 10⁻⁵ Å | Result in this fixture |
| --- | ---: | --- |
| Native symmetry bond | 8.08×10⁻⁹ | Matches |
| Native symmetry angle | 4.81×10⁻⁹ | Matches |
| Native symmetry planarity | 1.986513 | Review |
| Cartesian planarity + explicit image pullback | 3.93×10⁻⁹ | Matches |
| Raw Cartesian parallelity + image pullback | 0.108042 | Review |
| Cedar corrected Cartesian parallelity + image pullback | 1.46×10⁻¹¹ | Matches |

The Cartesian parallelity failure and correction are already owned by Cedar's
`cif_parallelity_correction` (`native-parallelity-both-first-planes-v1`), described
in its C23–C27/C44–C51 evidence. This probe imports that implementation; it does
not duplicate it or extend its symmetry-bearing-proxy policy. Instead, it
explicitly expands the image coordinates, calls the existing Cartesian kernel,
and accumulates gradients with the transpose Cartesian rotation. Native energies
and declared targets/weights are unchanged. The same composition passes both
public 8D93 plane pairs (corrected parallelity maximum error 3.80×10⁻¹¹ at 10⁻⁵ Å).
The direct native symmetry-planarity path gives correct values but inconsistent
gradients in these controls; the native symmetry-parallelity constructor remains
unexercised/unsupported. Do not attach these raw proxies to a production manager
and infer support from a plausible energy value.

This is a bounded integration diagnostic, not a new runtime closure evaluator,
a blanket API qualification or an optimizer run. Cedar's captured trial lifecycle,
fixed-base scope, packing and endpoint chemistry still need a supported combined
adapter before native repair can be exposed. The normal six-parameter TopoStitch
fitter uses numerical differences of its own descriptive objective and is not
using these failing native gradients. Synthetic probe output and public-derived
native diagnostics remain local; only the reusable probe source is committed.

### W51 — Native convergence ceiling control

Two predeclared complete native executions in **Phenix 2.2.1-6174** restarted
W41's paired and W45's retained-core-only objectives from their identical source.
Only the supported iteration ceiling changed from 200 to 500 and the watchdog
from 600 to 1200 seconds. The 2000-call cap, native context, frozen Cedar
`f2345a8`, source/mask, tether, hard displacement, pair weights and derivative
policy were unchanged. Consumed Willow source was frozen at W50 before running;
no source/runtime changes occurred during either serial job.

Both initial complete derivative gates pass, and every recorded evaluation
through the old 200-iteration stopping point reproduces exactly. The paired
control then fails the existing L-BFGS rounding-error line-search policy at 358
accepted steps/390 calls; core-only fails at 351/385. Last accepted projected
gradient norms are about 0.000380 and 0.000548. Additional movement relative to
the 200-iteration endpoints is at most 0.0000913 and 0.0001043 Å per atom,
respectively. These small changes do not turn the failed jobs into successful
convergence or accepted structures.

No full-precision/serialized endpoint derivative gate ran after the exception;
no candidate was emitted and no stopping exception was ignored. Inputs and
consumed sources remain unchanged. Keep the earlier capped, fully audited
endpoints distinct from these later failed trajectories. The next numerical
question is whether objective precision/conditioning limits the unchanged
stopping criterion; quantify that before changing tolerances or optimizer policy.
This is independent of Cedar's ordinary-refinement consumer investigation.

Exact commands and frozen inputs are retained in the local execution receipts.
The two CLI invocations used the same explicit W41/W45 model, recipe, mask and
native-receipt arguments with `--trial-iterations 500 --trial-calls 2000
--timeout-seconds 1200`, through a frozen copy of
`scripts/probe_topostitch_captured_objective.py`. This is an evidence-only update:
W50's 1,468-test + 229-subtest full suite and 155 installed/relocated checks still
apply to unchanged runtime code. Generated native jobs, inputs and traces stay
local; they are neither committed nor resumable NASolve checkpoints.


### W53 — Measure precision at the last accepted failed-trial points

Two complete read-only probes in **Phenix 2.2.1-6174** rebuild the authenticated
W51 contexts and reproduce each last accepted point's target components and
projected gradient norm exactly. A fresh, locally frozen diagnostic worker then
runs the unchanged complete 612-variable derivative check at 10⁻⁴ and 10⁻⁵ Å.
Both pass the existing absolute 10⁻³ bound: maximum errors are about 2.562×10⁻⁴
at the larger step and 2.554×10⁻⁶ / 2.608×10⁻⁶ at the smaller step (paired / core-only).
No optimizer runs in these probes, and the original failed trials stay failed.

The predeclared directional observations use the negative gradient, the three
largest gradient coordinates, and four fixed Rademacher directions (seed 5301),
each at 10⁻² through 10⁻¹⁰ Å. Raw plus/minus scores and actual coordinate changes
are retained. The scalar score ULP is 9.095×10⁻¹³ in both contexts. Measured local
steepest-direction curvatures at 10⁻⁴ Å are about 109,401 and 205,435; a local
quadratic estimate gives potential decreases of 6.60×10⁻¹³ and 7.31×10⁻¹³,
respectively, below one score ULP. The smallest perturbations visibly quantize.
This supports a numerical-resolution explanation for the line-search problem;
it is not proof of native convergence or acceptable geometry. Other directions,
other algorithms and ordinary refinement have not been qualified by this estimate.

Baseline evaluations repeat exactly after all observations. No weights, stopping
criteria, native SDK or Cedar source were changed. The local diagnostic injection
was authored afresh into frozen trusted project source; captured worker text was
never executed. Exact commands, injected-source fingerprints, raw observations and
failed-trial bindings remain in local receipts. W52's full and installation checks
still apply to unchanged product code; roadmap and documentation checks cover
this evidence update. The next small software task is to retain and audit the
identified last accepted point after an optimizer exception, while preserving
FAILED status, the original error and no candidate/adoption authority.


### W54 — Audit last accepted points without recovering failed trials

`run_native_masked_trial` now retains a separate `failure_endpoint` diagnostic
when the optimizer raises a caught error. Its coordinate origin is the last
callback-confirmed accepted trace step. A lower-scoring rejected trial, the
optimizer's restored working vector, and the initial source are not substitutes.
Callbacks must match the last evaluated coordinates before an accepted step can
be recorded. If no accepted step exists, report `NO_ACCEPTED_STEP` without an
invented endpoint or new evaluations.

The diagnostic checks pinned optimizer sources and remaining evaluation budget,
reproduces the accepted target components/projected gradient norm exactly, and
uses the existing full-coordinate derivative gates at full precision and after
three-decimal coordinate rounding. Fixed atoms remain fixed. The nested status
can be `DERIVATIVES_PASS`, `DERIVATIVE_REVIEW`, `FAILED`, `NO_ACCEPTED_STEP` or
`INSUFFICIENT_BUDGET`; partial observations and their own errors are retained.
The original optimizer error and outer **FAILED** status remain unchanged.
Passing derivatives cannot supply convergence, chemistry approval or a candidate.
Ordinary successful/capped trial fields and all optimizer parameters stay unchanged.

The captured-job receipt exposes additive `failure_endpoint_status` metadata;
its execution status, nonzero return and failed-trial state remain authoritative.
No schema migration, CLI option, retry, tolerance relaxation, checkpoint writer or
Cedar change is introduced. This is diagnostic use of a failed trajectory, not
optimizer recovery. Scientific inputs, native reports and frozen sources remain
local and are not committed as NASolve runs.

Twelve new tests include accepted-versus-best-rejected points, absent callbacks,
source loss/change, insufficient budget, changed objective/gradient, partial
rounded failure, derivative review and unchanged successful/capped behavior.
Eleven new failure-capability checks fail against the preceding runtime; all
33 focused trial/job checks now pass. Complete Willow: 1,489 tests plus 229
subtests. Installed/relocated shared-owner checks: 276, with exact legacy public
preview replay and original paths unavailable. Five command helps, lean imports
and Python 3.10 syntax pass. Commands follow the current periodic validation
receipt, with focused arguments `tests/test_topostitch_trial.py
 tests/test_topostitch_captured_job.py`; the full run used the same environment
and `-m pytest -q -p no:cacheprovider`. The wheel SHA-256 is
`2d474f2c6698de1452562900b43e076cbddf00c51d1eaa717bac0d420eb65841`.

Two complete native reproductions in **Phenix 2.2.1-6174**, using frozen Cedar
`f2345a8` and unchanged W51 requests, preserve every optimizer evaluation, accepted
step and original error exactly. Both jobs still return 2 and remain FAILED.
The new diagnostics audit accepted trace indices 369 and 364 (paired/core-only),
not the subsequent rejected line-search trials. All 612 full and rounded
coordinate derivatives pass unchanged bounds; full-precision samples exactly
match the independent W53 observations. Each diagnostic uses 4,900 objective
calls within the original mask budget. Inputs and consumed sources are unchanged.
No native model file, candidate selection or stopping-policy change follows.
Exact predeclared commands and failed-job receipts remain local; they use the
same W51 CLI arguments (`--trial-iterations 500 --trial-calls 2000
--timeout-seconds 1200`) through frozen W54 source.


## W61 — Read-only chemistry at failed last accepted points

Two predeclared serial calls to the existing captured endpoint observer inspect
W54's authenticated callback-confirmed last accepted points (paired iteration 358;
core-only 351). Receipt/file hashes, complete source/mask bindings and failed
parent status are checked before extracting the points. Both review calls use
**the same original complete 14-pair recipe**. The core-only optimization used 12
core pairs, so its common review score is not its original optimization score.
No optimizer, restraint change, refinement or candidate-model export is run.

Phenix **2.2.1-6174**, frozen Cedar `f2345a8`, complete native execution (8.48/7.92s)
returns `ENDPOINT_OBSERVATIONS_REVIEW` for both. The source observations agree
exactly. Source/full-precision/three-decimal cases repeat exactly under the fixed
original native manager; this is not fresh candidate reinterpretation. All inputs
and both W54 FAILED receipts remain unchanged.

| Full-precision observation | Paired endpoint | Core-only endpoint |
| --- | ---: | ---: |
| Common 14-pair objective | 7094.401790 | 7121.996121 |
| Native geometry target | 6546.387958 | 6544.925962 |
| Selected 2-pair target change from source | -52.144860 | -1.809397 |
| Core 12-pair target change from source | -77.019477 | -77.014866 |
| Largest atom displacement / Å | 0.196911 | 0.182182 |
| Existing contacts newly positive in overlap | 18 | 18 |
| Existing positive overlaps worsened | 110 | 113 |
| Largest newly positive overlap / Å | 0.075566 | 0.075565 |
| Largest positive-overlap increase / Å | 0.139359 | 0.162903 |
| Native ordinary-torsion target change | +1.391813 | +1.659604 |
| Native monomer-plane target change | -0.980100 | -2.792361 |

All 12 core-pair targets improve in both; selected-0 worsens under core-only
cleanup despite the small summed selected improvement. Affected scalar review
covers 230 simple bonds, 356 angles and 39 chiral volumes. Source nominal absolute
>=3 counts are 9 bonds/15 angles (3 angles >=5); both endpoint and rounded cases
have zero in these screens and no chiral sign conflict. These are descriptive
captured-geometry screens, **not new acceptance thresholds**. Fixed torsion/plane
terms are unchanged. Individual native terms can worsen despite improved sums:
the largest monomer-plane increase is at A:104 (~+3.53); the largest ordinary
torsion increase involves C:111 O3′–C:112 P/O5′/C5′ (~+0.70846).

Native pair identity/multiplicity remains 8316; no added/removed entries. Aggregate
nonbonded target improves from 1077.721614 to 1002.145960/1003.381017 while individual
contacts regress as listed. Rounding retains 18 newly positive overlaps for paired,
and 17 for core-only. No numerical difference is used to relabel a failed optimizer
or select an endpoint. The 345 captured constant-torsion rows all have weight 0 and
periodicity 0: retain them as inventory, without claiming an unimplemented live
individual qualification or treating them as 345 missing active restraint forces.

Validation uses the existing `scripts/probe_topostitch_captured_objective.py`
with explicit model/complete recipe/mask/native receipt/Cedar/Phenix paths and
checksums, `--endpoint-points`, `--endpoint-sha256`, `--timeout-seconds 600`, and
no trial flags. Exact two commands, predeclared plan, failed-parent hashes,
authenticated staged captures, observations and executable summarizers are in
local W61 evidence. Receipt hashes: paired
`3ecd57b46a183933e242133f7d9c3f525e208c87e8b60eb742153045e753a40e`;
core-only `1b38b14f40e87465332b79a1b8c1db21aab48075b0ca30022e420c3c3496d5f6`.
No runtime/schema/dependency change: W60 full 1576 plus 229 subtests and installed 370
remain the current software validation; roadmap synchronization and 8 focused
roadmap tests pass for this documentation update. Scientific artifacts remain
local and excluded from Git. S05 is still partial; ordinary enforcement, full
chemical judgment and later matched diffraction qualification remain open.


### Inspect existing preparation authority (W177)

`nasolve.topostitch_preparation.inspect_checkpoint_preparation` consumes the
existing Cedar registry/publication/result reader. Supply `expected_checkpoint_id`
and the exact `expected_model_sha256`; `checkpoint=None` uses the saved current
selection, while an explicit checkpoint/bookmark must resolve to that same ID.
An optional `expected_context_sha256` refuses metadata/input changes after an
initial inspection. The function writes no files and launches no native job.

The result describes availability of frozen prepared-model context, restraint
context and literal/explicit NAR compiler records. It reports their hashes and
original index basis, retaining missing authority as `UNAVAILABLE`. A source-model
context may legitimately describe the pre-ReadySet input rather than the selected
prepared model: both hashes remain explicit and the equality flag is descriptive.
They must not be substituted for each other. Native-capture coverage is not
assessed by this adapter.

Only published `postmr` or explicit preparation checkpoints are in scope. Refined
descendants require a later lineage join and refuse; legacy roots without checked
publication return `NO_CHECKED_PREPARATION`. This availability report does not
admit modified/canonical motion, grant chemical approval or freeze dispatch.
W173's schema-2 motion policy is unchanged. The single call-local existing owner
result is reused rather than reading its entire history twice.

Standalone Willow does not include Cedar's maintained preparation owner. Its
absence raises a clear runtime error; cross-branch integration may pass an
explicitly trusted `preparation_reader` implementing
`checkpoints._read_registry_with_preparations`. This dependency injection is a
caller trust boundary, not an importer or a way to load executable code from a
saved report. No chemistry producer, compiler, artifact copy or new launcher is
added.


### Inspect native support for a preparation window (W188)

`topostitch_preparation.inspect_checkpoint_native_window` reads an existing
PostMR/explicit preparation and a maintained native capture at the exact selected
model bytes. Supply `expected_checkpoint_id`, `expected_model_sha256`,
`native_receipt`, its `expected_native_receipt_sha256`, and a nonempty sorted list
of unique `selected_indices` in **source PDB atom-record order**, not atom serials
or native indices. `expected_context_sha256` optionally pins the earlier preparation
snapshot; an explicit `checkpoint` preserves the existing selection API.

Standalone Willow callers supply the trusted `preparation_reader` and
`native_owners=(cedar_attachment_native, cedar_terminal_qualification,
cedar_native_monomers)` modules. An integrated installation uses those existing
owners automatically. No artifact-supplied code is loaded. The strict supported
PDB identity/alternate-conformer limits remain Cedar's; mmCIF and ambiguous atom
mapping are not silently broadened. Refined descendants still require a separately
qualified preparation-lineage join.

The returned schema-1 `topostitch-preparation-native-window` observation includes
exact parent context, an anchored native receipt, full monomer proof, selected
source/native indices, atom identities, and selected/boundary/fixed counts for
eight captured proxy families. Each crossing term retains its native ordinal,
both endpoint lists when present, input indices, structured atom names and recorded
parameters/symmetry metadata. Repeated proxies are counted repeatedly. Unsupported
families are unavailable, never zero. A zero observed family count is specific to
this captured manager and is not evidence that the physical interaction is absent.

Every inherited PHIL/CIF must be included by bytes and multiplicity. Additional
capture inputs are explicit. This **multiset inclusion is not input-order/role or
effective-setting equivalence**: extra PHIL can override settings, and even the
same files in another order may differ. An execution gate must separately bind
those roles, order and effective settings. Pair/stack assignments and absence of
interactions are never inferred from the file or custom-request count.

Selection means ASU atom-index membership; it is not a geometrically bounded
crystal-image neighborhood. Native symmetry metadata remains visible, but image
closure, nonbonded support, geometric quality, identity of partners and motion
admission are not qualified. Repeated reads detect drift, not races; no locking,
model/registry writing, launch, model selection or runtime authority is added.
The unselected/fixed remainder label is a partition, not an installed movement
constraint. [Real parent and checks](topostitch-periodic.md#w188--inspect-native-support-across-a-real-preparation-window).

### Derived ordinary source context (W190)

Both preparation inspectors accept `ordinary_model_context_owner=cedar_model_context`,
a trusted installed `cif_model_context` module supplied explicitly by the caller.
Only an original canonical DA/DC/DG/DT `postmr` model with no checked publication
is supported. Its frozen `post_mr_plan` and recorded prepared-model hash must bind
the exact selected bytes. The existing owner derives the standard-backbone context;
no new chemistry implementation or artifact-supplied code is used.

The additive `derived_source_context` field has status
`DERIVED_ORDINARY_BACKBONE_CONTEXT`, authority
`CURRENT_MODEL_AND_FROZEN_ORDINARY_PLAN`, and `checked_preparation=False`.
The parent digest includes `derived_source_context_sha256`; use the resulting
`expected_context_sha256` for a later read. Omitting the opt-in does not reproduce
that pin. Existing checked availability remains unavailable and the preparation
status stays `NO_CHECKED_PREPARATION`. Coordinates and frozen policy supply the
derivation, not independent experimental truth or original pair/stack assignment.
No modified-source, descendant or motion scope is added; existing calls and
schema versions are unchanged. [Validation](topostitch-periodic.md#w190--bind-derived-ordinary-source-connectivity).

### Measure declared paired phosphates (W191)

The shared `nasolve.helical_geometry` module measures an explicitly assigned
region independently of refinement, Cedar chemistry or Alder cluster placement.
`HelicalSite` holds exact chain, residue number, component, insertion code,
`altloc` and `operator_xyz`. `DeclaredPair` preserves a logical `pair_id`, strand
I and II, `role` (`core` or `flank`) and a boolean `break_before`. `PairedRegion`
keeps caller order; numbering is never used to invent adjacency or pairing.
Logical IDs can be carried to later states, but correspondence is not inferred.

```python
from nasolve.helical_geometry import (
    HelicalSite, DeclaredPair, PairedRegion, inspect_phosphate_spans,
)
region = PairedRegion("inner-edge", (
    DeclaredPair("local", HelicalSite("A", 12, "DC"),
                 HelicalSite("B", 4, "IMC")),
))
report = inspect_phosphate_spans(
    model_path, region, expected_model_sha256=model_sha256,
    include_half_span=True,
)
```

An installed environment also provides:

```bash
python -m nasolve.helical_geometry --model model.pdb \
  --region region.json --sha256 EXPECTED_MODEL_SHA256 --half-span > spans.json
```

`region.json` is the JSON form of the dataclasses (for example
`json.dumps(dataclasses.asdict(region))`). The CLI writes JSON only to stdout;
redirection selects the output path. It does not find datasets or alter a model.
Every result includes model bytes/hash/size, method version, region/hash, exact
P atom mapping/coordinates/occupancy and measured/missing pair coverage. Its source
reference uses anchor `model_directory` and the explicit model filename. Relocate
by supplying the new exact model path; the reader never searches by basename.

Only **one PDB model**, `model_index=0` (ordinal, not MODEL serial), and explicitly
identity images `x,y,z` are supported. Nonidentity images and multi-model inputs
are refused; mmCIF and registered recut correspondence are future adapters. Exact
modified component labels remain intact without requiring a base-ring projection.
A chosen alternate uses its named P or a shared blank P; an ambiguous/absent
conformer, duplicate site/atom, component mismatch, absent phosphate or unusable
occupancy remains unavailable with a reason. Missing measurements are never zero
or an invitation to join across a break. Labels supply nominal atom identity;
this report does not chemically validate the selected component or pairing.

The measured **P–P span** is the straight Cartesian distance between the paired
phosphates. Optional `half_span_angstrom` divides this number by two. It is **not**
either strand's distance to a local screw axis. Axis radii and simple step twist
are explicitly `NOT_MEASURED` in this default mode. Geometry quality, density and topology acceptance
are outside this read-only method. The [shared plan](helical-geometry-plan.json)
keeps those gates and the unresolved 7SDG twist discrepancy visible.


### Measure canonical simple step twist (W193)

Opt in through the same explicitly assigned region and exact model hash:

```python
from nasolve.helical_twist import inspect_helical_region
report = inspect_helical_region(
    model_path, region, expected_model_sha256=model_sha256,
    max_ring_fit_rmsd_angstrom=0.15, include_half_span=True,
)
```

```bash
python -m nasolve.helical_geometry --model model.pdb --region region.json \
  --sha256 EXPECTED_MODEL_SHA256 --simple-twist --max-ring-fit-rmsd 0.15 \
  --half-span > geometry.json
```

Install the existing `.[topology]` extra. The positive finite fit limit is required;
0.15 Å is the explicit policy used for the public controls, not a validated
chemical acceptance cutoff. Default phosphate-only use needs no Gemmi and retains
its original report. Opt-in output has kind `regional-helical-geometry`, schema 1,
and a `simple_step_twist` section with method
`declared-canonical-simple-step-twist-v1`. It records canonical reference hash,
Gemmi version, exact ring/C1′ atoms and conformers, per-base RMSD, pair frames,
normal reversals, signed step values in degrees and coverage.

Only DA/DC/DG/DT rings are mapped. Canonical reference fits follow Olson et al.
(DOI 10.1006/jmbi.2001.4987). Each pair normal is oriented along the displacement
to the next pair origin before the C1′ directions are untilted into a common
frame. This is the qualified simple-step convention, not a reconstruction model.
Missing ring/C1′ atoms, modified residues, ambiguous conformers, poor/degenerate
fits, undefined step directions and exact 180° ambiguity retain explicit reasons.
A declared break suppresses its step. Missing P does not suppress valid twist;
missing twist does not suppress an independently measured P–P span.

Identity-image, single-model PDB limits still apply. The reader does not discover
or validate pairs, map modified rings, infer a screw axis, compute region means,
move coordinates or authorize bending. P–P span, half-span and axis radii remain
different quantities. [W193 qualification](topostitch-periodic.md#w193--maintain-canonical-simple-step-twist)
retains the current-versus-historical 1XVK rounding difference and unresolved 7SDG
publication-input discrepancy.


### Compare declared helix states (W194)

The Python API compares two named, independently byte-pinned models through the
same readers. Pair identifiers may differ after renumbering; the caller supplies
complete one-to-one accounting and explicitly declares strand I → I, II → II.
Existing construct registration may supply those assignments upstream, but this
adapter does not establish or infer physical correspondence.

```python
from nasolve.helical_comparison import (
    HelicalState, PairCorrespondence, compare_helical_states,
)
reference = HelicalState("before", before_path, before_region, before_sha256)
candidate = HelicalState("after", after_path, after_region, after_sha256)
comparison = compare_helical_states(
    reference, candidate,
    correspondence=(PairCorrespondence("logical-pair", "old-id", "new-id"),),
    strand_correspondence="I_TO_I_II_TO_II",
    simple_twist=True, max_ring_fit_rmsd_angstrom=0.15,
    include_half_span=True,
)
```

Supply one row per logical correspondence covering every pair in both declared
regions exactly once. Use `None` for an unmatched state pair; do not drop it to
join its neighbors. The example contains one pair, so it has no step: multiple
adjacent pairs are needed for twist. The optional twist and fit-limit rules are
those of W193. Default phosphate-only comparisons need no Gemmi. This slice is
an API; the single-state CLI remains unchanged.

The schema-1 `helical-state-comparison` contains both raw measurement reports,
state names, complete correspondence/hash, per-pair values/changes and coverage.
Each embedded state owns its own `model_directory` anchor; pass the relocated
exact paths and original hashes. No old-path or basename search occurs. Both
source hashes are rechecked after measurement; this is not a filesystem lock.

Changes are **candidate minus reference**. Angular differences wrap into
(-180°, 180°); exact half-turn ambiguity is unavailable. Reordered/reversed
steps are not assigned a guessed sign: each state's actual directed adjacency
is retained and unmatched steps have no delta. Declared breaks and unavailable
frames survive. Component and core/flank changes remain visible; these do not
rewrite chemistry or imply comparison of equivalent biological states.

This measures local P–P span, optional half-span and simple-step twist. It does
not measure axis radii or helix curvature, average regions, validate pairing,
infer symmetry correspondence or approve a bend. [W194 saved-state check](topostitch-periodic.md#w194--compare-explicit-named-helix-states)
shows why unchanged pair width is compatible with large coordinate displacement.


### Summarize declared regional twist (W195)

Use `nasolve.helical_twist.inspect_weighted_twist` with the same pinned model,
region and canonical ring-fit policy as W193. Add `step_weights` (one finite,
nonnegative number for every adjacent pair step) and an explicit positive
`min_abs_mean_twist_deg` below 180°. At least one step weight must be positive.
The result retains the raw report and adds `regional_twist_summary` with method
`declared-weighted-simple-twist-v1`; existing API/CLI output is unchanged.

For a seven-pair edge, `(1,1,1,1,1,1)` averages six full steps. For its central
pair, `(0,0,1,1,0,0)` averages the two flanking steps. For a separately declared
nine-pair junction-inclusive region, `(.5,1,1,1,1,1,1,.5)` has total weight seven.
Weights come from the scientific declaration, not inferred component/core labels.
A modified ring still needs separate W193 mapping qualification.

```python
from nasolve.helical_twist import inspect_weighted_twist
report = inspect_weighted_twist(
    model_path, region, expected_model_sha256=model_sha256,
    max_ring_fit_rmsd_angstrom=0.15, step_weights=(1,1,1,1,1,1),
    min_abs_mean_twist_deg=0.1,
)
```

The example's 0.1° limit is explicit caller policy, not experimental uncertainty
or a biological threshold. A mean at/below that magnitude is retained but has no
bp/turn estimate. Negative means retain a negative signed repeat. Missing included
steps never become zero or a renormalized observed-only mean. Positive weights
must cover one contiguous segment; interior zero-weight gaps remain unavailable.
An included angle range of at least 180° is ambiguous: no circular unwrapping is
guessed. Half-turn comparisons and regional averaging are different operations.
Every raw step, weight, availability reason and declared/measured weight survives.

A small regional mean does not prove local repair. In the saved positive recovery,
−0.122° edge-mean change hides a −2.193° individual step change. Axis radii,
curvature, coordinate repair and scientific selection remain outside this API.


### Regional helicity model building (planned)

The 2026-11-21 request is a later-stage **geometric MR-model construction**
operation: for example, declare one duplex region at 9 bp/turn and another at
11 bp/turn. It belongs beside bending and helix opening, after supported intact
placement and backbone repair. Current source-chemistry/execution integration
stays ahead of this feature; no builder, CLI flag or new
runtime schema is introduced here. The [shared helix plan](helical-geometry-plan.json)
records inputs, constraints and qualification gates; H1–H3 remain read-only.

For an ideal straight right-handed helix those targets are 40° and approximately
32.727° per step. Name the convention: conventional base-pair-step Twist, local
helical/screw-axis Twist and the current simple-step measurement are different
in general. We must qualify a matching construction/measurement pair rather than
silently invert the existing reporter. Declare ordered **steps** and their weights:
N pairs normally contain N−1 internal steps. A regional mean allows local variation;
a uniform per-step target is a stronger, separately requested constraint.

Use registered base-pair frames and step transforms shared with bending. Specify
rise and the other step geometry separately: 11 bp/turn alone does not make A-DNA.
Changing twist rotates downstream frames and changes how a local roll/tilt maps
onto a global bend direction. This geometric construction has precedent in
[3DNA](https://doi.org/10.1093/nar/gkg680) and
[3D-DART](https://doi.org/10.1093/nar/gkp287); their reconstruction principles do
not by themselves guarantee a chemically sound sugar–phosphate backbone.

Blend transitions through allowed flanks, retain base-pair integrity, and let
sugars/phosphates adjust through Cedar/NARestraints reconstruction and regularization.
Report the achieved profile after repair along with bonds, angles, chirality,
pucker, stacking, clashes and endpoint residuals. Density is unnecessary for
initial geometric generation; later MR/refinement determines experimental support.

First qualify canonical DNA with one anchored end and a free opposite end.
Two fixed endpoint **positions and orientations** can conflict with accumulated
twist. Allow explicit transition flexibility or expansion within the editable
region, stop at protected junctions, and refuse infeasible requests. Periodic
closure, modified bases and metal-coupled geometry need their own qualification.
Use bounded, declared candidate ensembles through existing campaign machinery;
this is neither an unrestricted Free-R search nor a separate geometry engine.


### Registered interior paired windows (W196)

The existing builder, CLI, viewer and `load_bend_motion` now also read schema-3
`topostitch-window-transform` trials. Use the same exact model/discovery/registration
hashes and motion/audit limits as schema 2. Replace `window_id` with:

```json
{
  "schema_version": 3,
  "ordered_pairs": [["A:9","B:7"],["A:10","B:6"],["A:11","B:5"],
                    ["A:12","B:4"],["A:13","B:3"],["A:14","B:2"],
                    ["A:15","B:1"]],
  "pair_weights": [0,0.2,0.4,0.7,1,0.5,0],
  "origin_pair_index": 3,
  "max_window_pairs": 7,
  "fixed_anchor_pairs": 1
}
```

This is the schema-specific fragment, not a complete executable request. Retain
`kind`, the three file hashes, explicit rotation/translation, displacement limit,
and all bond/angle/torsion change limits. The existing `nasolve-topostitch-preview`
command still writes only to a new directory and takes explicit input paths.

`ordered_pairs` lists logical sites from the selected registered copy. Each pair
must be a declared mate; consecutive pairs must advance one site along one
chemical route and retreat one along the other. Reordering, route gaps, duplicate
sites and protected junctions refuse. The fixed-anchor count applies **per flank**;
those paired weights must be zero, and all intervening weights must be in (0,1].
Declared free-site boundaries also refuse. Neither pairing nor missing junction
intent is inferred. Incomplete global discovery coverage stays visible.

The pivot is the mean of the existing base-plane centroids of the zero-based
`origin_pair_index`, computed from the original model. Both residues of a pair
receive the same weighted rotation and translation. Context and both flanks stay
fixed. Weights are caller-supplied; no smoothness, corrective direction, local-axis
measurement or density fit is inferred. Nonuniform weights are a motion proposal,
not an atomic relaxation rule.

The schema-3 receipt uses algorithm `whole-pair-declared-interior-transform-v3`,
`window.kind=interior-paired-window`, `end_id=null`, and
`motion_origin_angstrom`. It preserves the original window declaration and exact
source snapshots. Schema-1/2 receipt fields remain unchanged; old readers reject
schema 3 and require an updated installation. No migration of old runs is needed.
The existing viewer can show the before/after region without an end-mate selection.

`load_bend_motion` replays the new packet and enforces unrounded displacement
limits, exact coordinate serialization and, when supplied, the current parent
bytes. Existing checkpoint/request bindings compose that loader; this does not
create an ordinary checkpoint or qualify retained-parent native transfer.
Selected ANISOU handling and stricter downstream endpoint rules are unchanged.

Three fresh 5W6W diagnostic proposals (zero and ±2° about the declared Cartesian
Y direction) demonstrate delivery and replay, not repair. 205 atoms move while
654 remain fixed; maximum motion is ~0.400 Å. Audited link changes reach 0.182 Å
and angle changes 5.95°, so the models still need geometry recovery. The new
proposals do not authenticate the older private W163 taper retroactively.

Exact replay currently also requires compatible numerical behavior: the same
packet relocates under Python 3.12, while Python 3.11 produces identical PDB bytes
but last-bit audit-angle differences and is refused. No tolerance is widened.
[Qualification and limits](topostitch-periodic.md#w196--replay-a-prospective-interior-paired-window).


## Map an admitted endpoint to native atom order (W198)

`nasolve.topostitch_endpoint.map_native_endpoint` adapts an already admitted
motion to an explicitly observed native **parent** or **candidate**. Obtain
`expected_audit_sha256` through the existing trusted preview/checkpoint/execution
join; recomputing a digest from arbitrary new coordinates is not motion authority.

```python
mapping = map_native_endpoint(
    source_bytes, candidate_bytes, full_precision_points,
    movable_indices=source_indices,
    max_displacement_angstrom=bound,
    expected_audit_sha256=admitted_audit_digest,
    native=observed_native_atoms,
    native_model_role="parent",  # or "candidate", matching observed coordinates
    native_owner=trusted_cedar_native_owner,
)
```

The trusted owner defaults to the installed Cedar module when present. Standalone
Willow must receive that dependency explicitly; do not load executable code from
an artifact. Cedar's strict identity/element/occupancy/coordinate checks retain
their existing model/conformer scope and roundoff limit.

The frozen `NativeEndpointMapping` contains `native_to_source`,
`native_identities`, `movable_native_indices`, `fixed_native_indices`, and
native-order `native_points`, `parent_points`, `candidate_points` and
`full_precision_points`. Its `source_index_basis` is
`SOURCE_PDB_ATOM_RECORD_ORDER`, never an implicitly sorted parser order.
Candidate points are exact PDB decimals; full-precision points retain the admitted
initializer. Nested tuples are detached from mutable input observations. Fixed
atoms, full atom coverage, source record order and the bound audit stay strict.
Movable ANISOU is rejected by this first handoff scope.

This is a coordinate assignment, not a mutable model handle, lifetime permit or
native execution request. The executing owner must bind it to the actual live
model and independently preserve topology, crystal/scattering/ADPs, fixed context
and input lifetime. No coordinates are applied and no files are emitted.
[Qualification](topostitch-periodic.md#w198--keep-native-atom-order-and-movement-scope-together).


## Prepare parent geometry once (W200)

`nasolve.topostitch_native_preparation.NativeEndpointPreparation` is an opt-in
in-memory stage owner. It consumes the existing admitted W198 mapping of the
actual initial **candidate**, then reobserves it before any interpretation:

```python
context = NativeEndpointPreparation(
    source_bytes, candidate_bytes, full_precision_points,
    initial_mapping=admitted_candidate_mapping,
    max_displacement_angstrom=bound,
    native_owner=trusted_cedar_atom_owner,
    builder=qualified_native_builder,
)
with context:
    context.prepare()
prepared_candidate_mapping = context.result()
```

The builder is explicit executable infrastructure qualified by the caller, never
code selected from a saved receipt. It exposes a stable `model` and five methods:

| Method | Required owner responsibility |
| --- | --- |
| `observe_atoms(model)` | Exact current atom observation from Cedar's maintained collector |
| `interpret_parent(model, parent_bytes)` | Exactly one qualified interpretation using those bound bytes; retain candidate diffraction |
| `verify_parent(model, mapping)` | Prove independently declared source topology/chemistry and protected crystal/scattering/ADP state before transfer |
| `set_candidate_sites(model, points)` | Apply candidate PDB-decimal coordinates to the same manager, once |
| `verify_candidate(model, parent_mapping, candidate_mapping)` | Prove complete retained native chemistry/protected state and unchanged candidate diffraction through transfer |

Except `observe_atoms`, methods return `None` or raise; a false verdict cannot
silently count as success. This protocol does not itself establish chemistry:
retain and independently check the builder's actual native evidence. The context
reuses the unchanged W198 strict byte/role/mask/order checks before/after verifiers.
Reordered interpretation receives a fresh mapping. Full-precision initializer
coordinates remain admitted evidence; the transfer uses exact candidate PDB
coordinates, matching the frozen refinement input.

One context permits one interpretation request and one transfer. Missing,
repeated/reentrant calls, swallowed failures, changed managers, stale observations
and verifier-induced coordinate drift invalidate it. `result()` is unavailable
until successful context exit and remains unavailable on failure. `statistics()`
returns detached control-flow data, not a native execution or chemistry receipt.
An outer exception also invalidates a prepared result. No rollback or reuse is
supported: discard the failed manager/context with its owned worker.

This module installs no native patches, opens no files and launches no process.
The outer worker owns binding cleanup, source qualification, serial native use,
retained-input lifetime and failed-manager disposal. Native/counted execution
policies and ordinary checkpoint admission remain separate integration work.
The real qualification used one unchanged native dry-run path and one injected
failure; broader chemistry and actual ordinary integration are not implied.
[Evidence](topostitch-periodic.md#w200--maintain-one-shot-native-parent-preparation).


## Bind typed native preparation inputs (W203)

`topostitch_native_preparation.bind_native_preparation_inputs(directory,
parent_bytes, expected_report_sha256=..., compiler_owner=..., controls_owner=...)`
reopens existing typed inputs through trusted Cedar owners. Before W203, the
private worker carried these roles itself; now an independently testable binding
preserves the exact current parent, complete source report and separate PHIL roles.
It performs no native interpretation and changes no W200 builder method.

The expected digest is the **canonical complete compiler-report digest**, as used
by preparation availability; it is not the raw JSON-file checksum. The existing
`_compiler_input` reader authenticates the actual artifact. The adapter compares
the exact parent bytes, requires separate ordered compiled/control paths, calls
the existing control parser/shadow check, requires all four False settings, then
repeats the owner read and source-byte checks. These are snapshot checks, not locks.
There is no filename search, artifact code loading or inferred authority.

The returned frozen `NativePreparationInputs` contains:

| Field | Meaning |
| --- | --- |
| `parent_bytes` | Exact authenticated current-parent model bytes |
| `source_report_json` | Complete canonical report, retaining original source/compiled provenance |
| `compiled_restraint_phils` | Ordered tuple of unchanged compiled PHIL byte strings |
| `interpretation_control_phils` | Separate ordered tuple of unchanged original control bytes |
| `reader_controls` | Sorted `(name, False)` tuples for the four authenticated settings |
| `reader_policy` | Existing `cif-captured-reader-control-handoff-v1` |

Properties expose `model_sha256`, `report_sha256`, `runtime_authority=False` and
`chemical_admission=False`. Byte snapshots remain detached when source files or
owner dictionaries later change. Constructing this object or matching its digest
does not authorize native work. The concrete Cedar service must independently
qualify its live source/profile, scope and required chemical evidence.

**One native owner:** Cedar owns actual Phenix interpretation/service binding;
Willow owns typed parent/candidate roles, controls, atom movement and W200 ordering.
A Willow builder may receive the explicit Cedar interface. It must not become a
wrapper that imports the private W200 worker or another global dispatcher. Existing
C507 live readers can observe atoms/geometry but do not interpret a parent.
Inspection of the maintained owners finds no current early parent-service hook;
the counted `driver.run` hook is after geometry construction and cannot substitute.

The proposed concrete binding returns W200's existing stable-model builder with
`observe_atoms`, `interpret_parent`, `verify_parent`, `set_candidate_sites` and
`verify_candidate`. Its exact factory signature remains Cedar-owned. Required
success/failure cases, before a public execution policy:

- Observe exactly one qualified `process_pdb_files` call on the intended model
  and capture its actual processed object. Verify expected model-input identity
  and native call shape; do not attach a different manager or merely count a callback.
- Consume the bound parent only for geometry, under the four exact controls and
  the authenticated compiled stack. Preserve original literal source evidence
  separately; its proxy counts need not equal those of the compiled C21 stack.
- Require source chemical/scattering/crystal/ADP proof before transfer. C507's
  linked-geometry MATCH alone is not complete chemical admission. W200 then maps
  the freshly observed native order and transfers candidate PDB decimals.
- Preserve candidate diffraction and complete prepared state through closure.
  Refuse wrong/stale identities, changed controls, zero/repeated/nested native
  calls, altered fixed atoms or missing evidence before exposing a result.
- Preserve the original failure, restore only owned bindings, stop the owned
  child and discard the failed manager. There is no model rollback or same-process
  retry. Retained-file/session ownership remains outside this input snapshot.

**Validation:** the new regression fails before implementation with ImportError.
Fifteen new cases cover detached immutable bytes, parent/report/owner mismatches,
role aliasing/merging, missing/nonboolean/True controls, shadows and read races.
The existing five-file focused set passes **175 source +175 relocated installed**:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_endpoint.py tests/test_topostitch_preparation.py tests/test_topostitch_native_window.py tests/test_topostitch_checkpoint.py tests/test_topostitch_execution.py
```

The installed run uses the same tests from a copied fixture closure with
`PYTHONPATH` pointing to the relocated installation after its original install
and temporary build-source paths are removed. Python 3.10 syntax parses. The
real W202-frozen typed source passes **14 cold checks in each of source3.12,
installed3.12 and Phenix 3.11**, with identical bound output. Its temporary source
is renamed before reading; the old path is gone. Wrong parent/report and a changed
captured control refuse through actual Cedar readers. Temporary input trees are
removed; original scientific artifacts remain unchanged.

Commands from NASolve use `branch-artifacts/willow/runners/w203-bind-source-final.py`
with `source`, `installed` or `python311`; the last uses the exact
Phenix **2.2.1-6174** `phenix.python -B` interpreter. These are cold reads,
**not native interpretations or refinement executions**. Local reports and
installation receipt are under `NASolve:branch-artifacts/willow/w203-source-input-binding/`
and pinned in the roadmap. Wheel SHA-256
`4e4994f4176ff92d17f1b01648453a650fa558c2345dac218356dd1f76c696be`;
module SHA-256 `cd5ff34c91410b7d9ba5e72e0cdf859887c2c2f03574d58ddec8f2e35565fbc5`.
Final receipts use `*-final-review.json` and `install-final/installed-check.json`.
The preliminary passing build remains recorded separately; the final rebuild
includes a module-description correction, with unchanged function behavior.

Changed code: the existing native-preparation module and preparation tests;
current guides/intent/roadmap/changelog stay synchronized. No new disk schema,
dependency, default or native dispatcher; no migration. No full-suite repeat.
Scientific data and source snapshots remain outside Git. Ordinary current-parent
lineage, complete chemical admission, concrete service and outer lifetime remain
separate gates. W204 is that Cedar-owned service boundary; no new refinement panel
or physical recovery claim is attached to W203.


## Installed parent-service composition (W204)

The [W204 diagnostic](topostitch-periodic.md#w204--compose-the-installed-cedar-parent-service)
now exercises the concrete Cedar interface anticipated by W203:

```python
# Capture qualified native functions before installing any outer manager hook.
service = cedar_parent_owner.load_native_parent_service()
interpreted = service.interpret(
    model, bound_inputs,
    expected_report_sha256=expected_report_sha256,
    process_options=pending_process_kwargs,
)
```

Pass the exact pending native kwargs, not a reconstructed subset. Its result
contains `processed` (the actual interpretation used), `native_result` (the
original native return) and `receipt`. Willow's W200 builder retains the same
model, observes the fresh order through the maintained atom reader, transfers
candidate coordinates and verifies retained geometry/scattering/diffraction.
C509 owns the one native interpretation and restores its server hook. An outer
worker owns all other hooks, retained inputs, child lifetime and failed-manager
disposal. This is qualified diagnostic composition, not a callable ordinary
Willow execution route. Full original-source chemistry remains a separate Cedar
gate; neither receipt nor matching compiled topology authorizes transfer in the
future ordinary path. No W200 protocol or W203 field changed.


### Original source chemistry in that same call (W205)

Pass `source_native_json` to the same C510 `service.interpret` call when requiring
the original per-site definition/restraint comparison. These must be the exact
original native-observation bytes bound by `bound_inputs.source_report_json`.
The service authenticates them, observes the real effective residue mappings
during its one interpretation, compares through the existing NARestraints owner,
and returns `interpreted.receipt["source_chemistry"]`. Require its `status == "MATCH"`
and exact source hash before transfer. Preserve its unsupported formal-charge
readback list; do not turn source agreement into complete chemical authority.

The [W205 receiving diagnostic](topostitch-periodic.md#w205--join-source-chemistry-to-candidate-transfer)
joins that parent proof to unchanged W204 post-transfer geometry/scattering and
candidate diffraction. Its source-byte mismatch refuses before interpretation
and movement. The optional observer requires an unoccupied thread profiler point
and restores only its own binding. Ordinary dispatch and retained-input lifetime
are still separate integration gates; the service has no persistent observer or
second comparison interpretation.


## Bind the original native observation (W206)

W205 still reopened the original native JSON separately in its local receiving
runner. The existing W203 binder can now carry those bytes with the same immutable
parent/report/PHIL snapshot:

```python
bound = bind_native_preparation_inputs(
    typed_directory, parent_bytes,
    expected_report_sha256=expected_report_sha256,
    compiler_owner=compiler_owner, controls_owner=controls_owner,
    include_source_native=True,
)
# After separate native/execution admission, use the existing Cedar keyword:
# interpreted = service.interpret(model, bound, ...,
#     source_native_json=bound.source_native_json)
```

`source_native_json` defaults to None, preserving old callers and the unmodified
PHIL ordering/source report. The opt-in requires exactly one
`literal_na_input_directory:native/native_validation.json` declaration, verifies
its exact size/hash and confined, non-aliased resolved path, and includes its
bytes/path in the repeated snapshot checks. It does not search by basename or
parse new chemistry. Cedar's actual source-observation reader verifies the bytes
again at use. **Passing None to C510 leaves its chemistry comparison disabled**;
the future ordinary receiver must require the opt-in bytes rather than mistake
an omitted observation for a successful comparison.

The regression fails before this change because the result lacks the new field.
Sixteen new cases cover opt-out/detachment, absent/duplicate/wrong source roles,
size/hash/byte mismatch, external or aliased paths, read races and strict boolean
opt-in. Focused validation:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_endpoint.py tests/test_topostitch_preparation.py tests/test_topostitch_native_window.py tests/test_topostitch_checkpoint.py tests/test_topostitch_execution.py
```

**191 source +191 freshly relocated installed tests pass.** The temporary build
source and original install path are removed before installed testing. Real W205
inputs pass **16 cold checks each** through source/installed Python 3.12 and Phenix
**2.2.1-6174 Python 3.11**, with identical bound outputs. The temporary input tree
is renamed, then removed before the installed C510 source-observation and bound
input readers consume the detached result. Both compiler-time and point-of-use
byte substitution refuse. Python 3.10 syntax parses. No native interpretation or
refinement was repeated; W205 already qualifies the identical payload at that
boundary.

The local recipe `NASolve:branch-artifacts/willow/runners/w206-install.py` builds
and tests the relocated wheel. `w206-bind-source.py` in that runners directory
accepts `source`, `installed` or `python311`; run with the matching interpreter
and `-B`. Receipts are under
`NASolve:branch-artifacts/willow/w206-source-observation-binding/`; pins are in
the roadmap. No new file format, CLI, dependency or execution policy. The in-memory
result gains one optional field; constructing it still grants no chemical,
motion, locking, process, storage or ordinary runtime authority. No full-suite run.

The receiving audit also keeps three lifetimes distinct: immutable ordinary
round inputs, Cedar's counted prepared-view/native-force scope, and Alder's
budgeted frozen-metal session. Neither a counted scope nor an Alder review is a
generic coordinate-moving session grant. The first opt-in ordinary route needs
an explicit early parent hook and source-bound parent/candidate input role in the
existing execution owner; future compact-parent expansion/budgeting is separate.


## Larger displacement with fixed flanks (W207)

W207 changes the physical question from W197's small fixed-flank perturbations
and W163/W164's larger all-atom fits. It prospectively declares one+25° Cartesian-Y
profile across A9..A15/B7..B1, weights `[0,.2,.4,.7,1,.5,0]`, origin pair3 and
one fixed pair at each flank. The largest atom moves4.96184 Å; this is **not**
25° of helical twist or a4.96 Å centroid movement. The initial backbone is
intentionally strained: maximum link-length change1.11831 Å. Broad declared
initialization limits permit the test; they are not geometry acceptance limits.

One Phenix**2.2.1-6174** dry-run is followed, after39 cold checks, by one actual
**five-cycle,100-iteration-cap XYZ-only refinement**, nproc1/seed1. Original
synthetic F/SIGF/Free, fixed B/Q, source geometry, explicit restraints and four
False reader controls remain unchanged. W206 detached source bytes feed the
same C510 interpretation before transfer;42 source sites/eight families/3451
retained terms match. The formal-charge readback caveat remains. No second
amplitude, weight search, retry or continuation is run.

| Measurement | Displaced start | Recovered |
| --- | ---: | ---: |
| Interior RMS from generator, Å |1.76560 |0.12238 |
| Largest atom departure, Å |4.96184 |0.90391 |
| Boundary bond RMS target error, Å |0.55659 |0.01657 |
| Boundary angle RMS target error, degrees |29.9634 |2.5935 |
| Synthetic Rwork / Rfree |0.23615 /0.22946 |0.008515 /0.009151 |

Final cold review passes41 checks:205 selected/654 fixed, fixed movement below
3e-14 Å, all 859 atoms,124 phosphate atoms,126 sugar handedness signs,38 declared
links,213 explicit terms, original 7554 observations/389 Free flags, source
chemistry/target definitions and all owned bindings retained. **This is partial
recovery, not accepted local geometry.** A11 OP2–P–O5′ is 77.42° against 108°;
A14 O5′–C5′ is 1.303 Å against 1.418 Å. O5′/C5′ carry the largest residual
positions, while maximum phosphate-P departure is 0.154 Å. The A11 angle began
at 109.57° and worsened during recovery; low synthetic Rfree conceals it. Existing
W197 zero is explicitly a historical reference, not a new matched panel.

Local recipes under `NASolve:branch-artifacts/willow/runners/`:

```bash
# From NASolve; plan is immutable and refuses an existing output directory.
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w207-fixed-flank-recovery.py plan
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w207-fixed-flank-recovery.py preflight
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages .venv/bin/python -B branch-artifacts/willow/runners/w207-review.py preflight
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w207-fixed-flank-recovery.py refine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages .venv/bin/python -B branch-artifacts/willow/runners/w207-review.py refine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/w206-qualified-dswq6ef2/installed-relocated:/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages .venv/bin/python -B branch-artifacts/willow/runners/w207-local-science.py
```

These exact historical commands borrow Gemmi from the existing local validation
environment; they are not a portable installation prescription. Current receipts,
frozen inputs and preserved local runners live under
`NASolve:branch-artifacts/willow/w207-fixed-flank-recovery/`; roadmap references
bind their bytes. Native worker calls are actual executions, not mocked tests.
No full suite was run for this documentation/science-only update.

The compact local packet at
`ScienceCheckouts/Linden/2026-11-21_fixed-flank-recovery/` contains three PDBs,
`open_comparison.py`, `review.html`, one figure and a checksummed manifest.
ChimeraX 1.12 headless verifies all 3×859 coordinates and five view controls;
the static plot is visually inspected. No interactive GUI rendering is claimed.
Gray background, silhouettes, soft lighting and thin nucleic rings are retained.
Raw models, data, local runners and generated results remain excluded from Git.
No schema/default/CLI or migration change; this does not close S04/S05/S06.

**Larger stress targets, planned:** the investigator requests 10 Å displacement
of a specified segment centroid and/or5 Å from a defined helix centerline.
Specify atom/pair weights, centroid definition, centerline and reference frame
before generation. Record maximum atom motion and RMS separately. Centerline
measurement/qualification and fixed-boundary/window expansion controls come
before a claim of radial displacement; P–P span is not an axis radius. These
future tests do not authorize an undeclared continuation of W207.

A separately bound descriptive readback makes this distinction concrete:
using the **unweighted arithmetic mean of the 205 movable present atoms**, the
start centroid shifts **0.25302 Å** (recovered departure 0.00539 Å). The largest
unweighted complete-pair atom-centroid shift is **0.88466 Å**. Coordinates are
compared in their original crystal frame without alignment; these centroids are
not fitted helix axes. The 4.96184 Å maximum atom motion therefore cannot stand in
for either requested future stress target. Opposing rotational motions largely
cancel in a whole-window centroid. Declare the exact segment or local centers
before targeting 10 Å, and distinguish displacement along an axis from offset
away from a centerline. `w207-displacement-metrics.py` reuses the unchanged W152
coordinate reader and writes `displacement-metrics.json` beside the preserved
W207 results; no additional native call or parameter choice is involved.


## Maintained source-bound parent builder (W208)

`SourceBoundParentBuilder` lives beside W200 in `topostitch_native_preparation`.
The five methods remain useful: W200 checks actual native identity/order and
fixed-coordinate roles around interpretation, parent verification, transfer and
candidate verification. The concrete builder now owns the previously local
composition of Cedar's native service and explicit trusted observation readers.
It does not install hooks, launch a child, retain files or change forces.

```python
# Outer worker: bind exact source/candidate/motion and qualify every callable.
# Cedar service must be created BEFORE installing model/selected-site hooks.
service = cedar_parent.load_native_parent_service()
builder = SourceBoundParentBuilder(
    model=pending_model, bound_inputs=bound,
    expected_report_sha256=source_report_pin, candidate_bytes=candidate_bytes,
    service=service, process_options=actual_pending_process_options,
    atom_reader=cedar_collector.collect_live_atoms,
    geometry_reader=read_and_review_live_geometry,
    protected_reader=read_protected_native_state,
    diffraction_reader=read_original_candidate_fmodel,
    coordinate_writer=set_native_sites,
)
context = NativeEndpointPreparation(
    parent_bytes, candidate_bytes, full_precision_points,
    initial_mapping=admitted_candidate_mapping,
    max_displacement_angstrom=declared_limit,
    native_owner=cedar_atom_owner, builder=builder,
)
with context:
    context.prepare()
mapping = context.result()       # W200 correspondence/closure proof
interpreted = builder.result()   # completed same native interpretation
proof = builder.evidence()       # detached observations, not runtime authority
native_return = interpreted.native_result
```

The outer worker discards the model/process on **any** exception, including W200
checks outside builder methods. A successful builder alone is not completed W200
admission. Do not catch an error, edit an observer and reuse that native manager.
The first builder-method error is re-raised unchanged; subsequent calls/result
access refuse. Returned proof snapshots are detached from mutable native state.
No existing caller, schema, default, CLI or execution policy changes; the API is
an explicit opt-in and requires no migration.

| Trusted input | Required meaning |
| --- | --- |
| `bound_inputs` | W206 source bytes, original native observation, compiled PHILs and controls; original observation cannot be None |
| `geometry_reader(model, processed, payload)` | Existing Cedar live collector and topology review; `native_view.geometry.proxy_details`, `custom_proxy_requests` and complete `topology` are retained; require MATCH |
| `protected_reader(model)` | Exactly `model_noncoordinate` and `fixed_geometry_inputs`; first contains stable-identity `atoms`, `scattering`, `crystal`, including ADPs/occupancy/charges/special positions; second is None before geometry and complete fixed native geometry inputs afterward |
| `diffraction_reader()` | Original candidate observations/Free, Fcalc/Fmodel, masks, scales and crystal/scattering snapshot; never silently a parent F-model |
| `coordinate_writer(model, points)` | Set only W200-mapped sites; return None or raise |

These are trusted installed/worker-code dependencies, never executable callbacks
loaded from a scientific artifact. The builder introduces no replacement native
chemistry or diffraction parser. Cedar C512 owns actual source definitions and
compiled restraint interpretation; W200 owns coordinate correspondence; existing
outer owners retain source qualification, binding cleanup and input/process life.
A generic boolean validator is not a substitute for the required evidence roles.

**Validation:** 26 new regression cases fail before the API exists and pass after
implementation. They cover missing/wrong source bindings, source mismatch, native
error propagation, altered diffraction/ADPs/fixed inputs/geometry/topology, reader
side effects, wrong manager/stage order and attempted reuse.217 source and 217
freshly relocated installed checks pass, using the same five focused files and
command listed under W206. Temporary build source and original install path are
removed before installed tests; Python 3.10 syntax also parses. The installed
qualification recipe is `NASolve:branch-artifacts/willow/runners/w208-install.py`.
No full-suite repeat or new general supported native scope is claimed.

Actual **Phenix 2.2.1-6174** qualification uses installed W208 and C512 on the
already-qualified W207 candidate, not another deformation. One completed dry-run
and one deliberately refused post-parent/pre-transfer child pass **54 cold
checks**. The successful final model, complete recorded geometry, prepared state,
selector and every diffraction snapshot exactly reproduce W207. The C512 source
chemistry receipt matches C510's prior result exactly. The failure preserves the
original RuntimeError after one interpretation, makes zero coordinate transfers,
exposes no builder result/child proof and leaves candidate diffraction unchanged.
Five outer hooks, native service and thread profiler restore; both processes stop.
No refinement runs. The formal-charge readback limitation remains.

The first attempt stopped earlier on an over-exact cell snapshot comparison.
It is preserved, including its zero-transfer failure and unchanged candidate
F-model. Comparison to original W207 captures isolates metric reconstruction:
stable-identity non-XYZ scattering, group and special positions match; raw cell
values differ by at most 2.8422e-14. The fresh attempt canonicalizes **only cell
values** at 10 decimal places in the trusted worker reader, retains all raw cell
observations and requires a difference below 1e-10. Library comparisons stay
strict; the candidate diffraction snapshot remains bitwise exact. This is a
representation correction, not a change to geometry/diffraction policy.

Exact local native commands, from NASolve:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w208-native-builder.py plan attempt02
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w208-native-builder.py run attempt02
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w208-review.py
```

Frozen `attempt02/entry.py` gives the concrete successful reader composition;
`post_parent_failure/request.json` binds the sole deliberate failure. Reports,
first-refusal evidence and installed receipts are under
`NASolve:branch-artifacts/willow/w208-maintained-parent-builder/`; roadmap pins
bind them. These local runs are not advertised as portable committed artifacts.
Generated scientific models/data/runners remain excluded from Git. Only library,
focused tests and human/machine documentation are committed. Shared versioned
parent-input/early-entry/dispatch integration is next and remains Cedar-owned.


### W207 saved-map check

A final **read-only** inspection reuses W170's pinned coefficient selector and
Hazel's existing A72 sampler on the already written W207 maps. Two exact unfilled
arrays (2mFo–DFc and mFo–DFc), 44 backbone atoms across A10/A11/A13/A14 and two
known O5′ residual planes pass 46 checks. All 7554 observation/sigma/Free tuples
and 389 Free reflections remain; native map declarations show no filling or
sharpening. Original crystal frame, periodic sampling and direct-Fourier/FFT
grid-node checks pass (maximum discrepancies 2.71e-14/1.07e-14).

| O5′ site | Difference at generating position / own map σ | At recovered position / own map σ | Ordinary at generating / recovered, common ordinary σ |
| --- | ---: | ---: | ---: |
| A11 |+0.948 |−0.215 |2.877 /3.221 |
| A14 |+8.268 |+0.982 |3.915 /4.323 |

The A11 atom lacks a strong negative sample despite 30.57° phosphate-angle error.
A14 has positive evidence toward the generating position but no negative sample
at the misplaced atom. Ordinary-map samples favor both displaced O5′ positions.
This supports keeping geometry and signed local context together; it does not
validate a red-only trigger, identify the causal force or calibrate a detector.
The map is held fixed while comparing positions. These are noiseless,
model-assisted synthetic maps including Free reflections, not independent
experimental validation. The 2D slices use the known residual vector plus a P
anchor; they are not a whole-volume classification or fitted helix centerline.

The comparison packet now includes `residual-maps.png`, the vector SVG and a
small `figure-evidence.json`. The rendered figure was inspected. Exact commands:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B branch-artifacts/willow/runners/w207-saved-maps.py
MPLCONFIGDIR=/private/tmp/w207-matplotlib PYTHONDONTWRITEBYTECODE=1 /Users/svecchio/Applications/phenix-2.2.1-6174/bin/phenix.python -B branch-artifacts/willow/runners/w207-map-figure.py
```

The owned **Phenix 2.2.1-6174** child only reads saved coefficients and computes
FFT/interpolation; it stopped cleanly. No new coefficients, alignment, coordinate
changes or refinement. Receipts under
`NASolve:branch-artifacts/willow/w207-fixed-flank-recovery/saved-maps/` are bound
in the roadmap. W170's earlier map panel and W207's current panel are different
endpoints; no new matched-control experiment is implied.


### Cedar native-entry handoff (C516)

After W208, Rowan qualified the shared early native ordering on Cedar at
`7ed50ffab8ecfcd232a50abfda41c45e9cf545ce`. C516 owns three hooks at validation,
finalization and the one pending `model.process` call; the existing two diagnostic
observers remain separate. Its actual Phenix 2.2.1-6174 success matches W208's
final model, geometry, prepared state, source chemistry, mappings and all three
diffraction snapshots. The post-parent refusal preserves the original error,
performs zero transfer and denies a usable result. All bindings restore and
both processes stop; zero refinement cycles.

This is **Cedar owner-qualified evidence**, not another Willow experiment.
Willow checked that the two prior-record hashes in
`NASolve:branch-artifacts/cedar/c516-source-parent-entry/science.json` exactly
identify its W208 success/failure captures; the roadmap binds that receipt.
The qualified relocated package remains at its historical local path
`/private/tmp/rowan-cedar-nov21-BrSPrj/package-516-final/relocated`, alongside the
separate retained W208 installation. No portable-public-run claim follows.

Cedar's remaining W209 step is the versioned ordinary request with authenticated
source/parent and motion roles. Preserve old request meanings/helper bytes. Both
W200 completion and builder evidence are mandatory; use one consistent Willow
module namespace for their typed classes. On a post-parent failure the disposable
native manager can hold parent coordinates: unchanged input files and candidate
F-model do **not** mean rollback of that manager. Discard it. Ordinary dispatch
and scientific acceptance remain false. Do not repeat C516 just to obtain another
copy of the same successful native evidence.


## Bind a dictionary-only native parent (W215)

The default W203/W206 literal route still requires real compiled restraints.
A canonical parent may instead have been interpreted using only the installed
monomer library and explicit reader controls. Cedar C526 defines that separate
source policy; opt in explicitly when binding its artifact:

```python
bound = bind_native_preparation_inputs(
    typed_directory, parent_bytes,
    expected_report_sha256=expected_report_sha256,
    compiler_owner=compiler_owner, controls_owner=controls_owner,
    include_source_native=True,
    source_policy="cif-typed-native-dictionary-parent-v1",
)
```

This calls Cedar's `native_dictionary_parent` reader and requires an empty
compiled-restraint role, the exact pinned report, and separate authenticated
reader controls. The four controls remain explicitly False. Original observation
bytes, parent identity, ordering, repeated reads and detached snapshots retain
W206 semantics. The default `cif-typed-native-literal-inputs-v1` rejects this
artifact; unknown policies and invented compiled restraints refuse. No dummy
pair restraints, pairing intent or execution authority are created. The result
class, CLI, old source policy, dependencies and ordinary execution defaults are
unchanged; no migration is required.

Eight focused regression cases include success, old-default rejection, empty
literal rejection, unknown policy and four role/control faults. Before the
change, six fail because the opt-in argument is absent. Afterward, this command
passes **225 tests**, repeated against a newly built, relocated installation
with the temporary build source and original installation removed:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /path/to/NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_topostitch_preparation.py tests/test_topostitch_endpoint.py tests/test_topostitch_native_window.py tests/test_topostitch_checkpoint.py tests/test_topostitch_execution.py
```

The existing local install recipe is `NASolve:branch-artifacts/willow/runners/w215-install.py`.
Nineteen real-source checks cover source/installed parity, relocation after the
old path disappears, exact original bytes, altered-control refusal and detached
results. Phenix **2.2.1-6174**, Python 3.11, reads the same bound result after
loading checksum-verified pure dependencies. The initial unbootstrapped Python
3.11 attempt lacked openpyxl; it made no native call. Ordinary CLI help also
passes from the relocated installed package.

One completed fixed-coordinate native interpretation captured the real X11_22
PostMR parent with all four controls. There was **no refinement, displacement or
checkpoint write**. Cedar C526 supplied the shared typed artifact; its separate
native source-reproduction qualification remains Cedar-owned. Receipts and
runners stay local under `NASolve:branch-artifacts/willow/w215-dictionary-parent-binding/`;
the roadmap pins exact bytes. This validates a source-binding interface, not
whole-model chemistry, a motion declaration or an ordinary repair workflow.


## Propose an intrinsic local backbone orientation (W216)

`topostitch_local.propose_backbone_shoulder` makes one explicit canonical
P–O5′–C5′–C4′ orientation from exact source PDB bytes:

```python
from nasolve.topostitch_coordinates import ResidueSite
from nasolve.topostitch_local import propose_backbone_shoulder

proposal = propose_backbone_shoulder(
    source_bytes, expected_source_sha256=source_sha256,
    site=ResidueSite("A", 11), reflection=True,
    rotation_degrees=60, max_displacement_angstrom=6,
)
```

The names/numbers/angle above are caller choices, not default repair targets.
P and C4′ define the fixed axis. Reflection selects the congruent branch across
the plane containing that axis and O5′; signed rotation then acts about P→C4′.
Only O5′/C5′ move. All six distances within the four-atom chain, including its
three bond lengths, are preserved at full precision. Existing bad lengths are
also preserved; native refinement must still repair them. Angles to atoms
outside this short chain can change. No score, search, map, Free-R set or known
answer enters the proposal.

The frozen result carries candidate PDB bytes, full-precision points, two source
indices and a JSON report. It uses the existing exact endpoint audit, preserving
all fixed records and noncoordinate bytes. Both precise and rounded positions
must fit the caller's displacement bound. The selected site must be a single
full-occupancy canonical residue without alternatives or explicit hydrogens;
P/O5′/C5′/C4′/C3′/O4′ must be present with exact names. Movable ANISOU tensors
refuse. Degenerate axis/plane/sugar frames refuse at 1e-8 in their corresponding
norm or normalized triple product. C4′ relative handedness must survive at full
precision and after PDB rounding. Other sugar centers and all base atoms stay
fixed. Preserving the source sign does not establish correct source chemistry.

This is a **proposal**, not registered motion or chemical admission. The new
in-memory report is `topostitch-intrinsic-shoulder-proposal`, schema 1; it does not
change the whole-pair preview schema or ordinary execution. Existing
`map_native_endpoint` accepts the same endpoint shape after a trusted caller
has separately admitted it. Native geometry/clash/diffraction checks and the
process/chemistry owner remain required before transfer or selection. No CLI,
dependency, default behavior or migration changes.

Validation: **247 focused source +247 relocated installed tests**, including
22 local cases. Twenty initial cases fail before implementation because the
module is absent. Tests cover independently calculated geometry, all six
internal distances, rigid-frame equivariance, canonical scope, degenerate
frames, chirality reversal, exact insertion codes, movable tensors and reordered
native indices. The existing six-file focused command is the W215 command with
`tests/test_topostitch_local.py` added. Temporary build source and original
installation are removed before the installed test run.

The real saved 859-atom W211 input replays all 48 independently frozen W210
orientations, retaining 857 fixed atoms per proposal and relative C4′ signs.
Maximum difference from historical full-native coordinates is **0.001830 Å**:
this API starts from saved three-decimal PDB coordinates. This is measured
precision agreement, not identical historical inputs or renewed scientific
acceptance. Source and installed Python 3.12 outputs agree exactly. Regenerating in Phenix
Python 3.11 changes last-bit full-precision arithmetic (maximum 2.56e-15 Å),
so an initial strict report-hash comparison refuses. All 48 serialized PDBs
are identical, and handing over the frozen 3.12 points reproduces every endpoint
audit exactly in 3.11. Preserve those bound points across interpreters instead
of assuming independently regenerated report hashes will match. No new native interpretation or refinement is
part of this replay. Local install/replay runners and receipts live under
`NASolve:branch-artifacts/willow/` in `runners/w216-*.py` and
`w216-local-shoulder-proposals/`; the roadmap pins evidence. W211/W212 remain
the separate prior recovery evidence, including residual geometry limitations.


## Measure explicit region displacement (W218)

Use the existing `CoordinateMask` for a read-only summary after binding atom
correspondence and a common physical Cartesian frame:

```python
summary = mask.displacement_summary(candidate_points)
# Optional positive weights follow mask.indices exactly:
weighted = mask.displacement_summary(candidate_points, weights=atom_weights)
```

The default is an equal-weight centroid of the selected present atoms. Explicit
weights may implement a separately declared scientific convention; no mass or
base-pair weighting is inferred. The result records exact indices, normalized
weights, both centroids, the weighted mean displacement vector and its length,
weighted per-atom RMS, and maximum atom displacement. Opposite displacements can
cancel in the centroid while RMS/max remain large. The vector is evaluated from
individual differences to avoid subtracting large nearly equal centroid values.

All weights must be finite and positive; wrong counts, booleans, zero/negative
weights and numerical underflow that erases a selected contribution refuse.
Normalization avoids overflow for large finite weights. Existing finite bounds,
coordinate count and fixed-atom checks remain active. Results are detached.
There is no alignment, symmetry unwrapping, radius or centerline fit, and no
model/sequence/registration authority. Callers must prove exact source and
endpoint identities and the common frame; the returned flags make that limit
explicit. Existing motion, endpoint, preview and native schemas/hashes are
unchanged. No CLI/default/dependency/migration change.

Twelve new cases include independent cancellation/weighted/translation examples,
frame rotation, weight rejection/overflow, exact fixed atoms and bounds. Eleven
initial cases fail before the method exists. **310 focused source +310 relocated
installed tests pass**, using optional Gemmi 0.7.5 for existing image tests; the
metric itself has no new dependency. Run the W216 six-file command plus
`tests/test_topostitch_transport.py`. The install test removes its build source
and original installation first; local recipe: `runners/w218-install.py` under
`NASolve:branch-artifacts/willow/`.

The exact already-bound W207/W217 endpoint pairs pass 18 source and 19 installed
checks; Phenix 2.2.1-6174 Python 3.11 produces the same serialized metrics
(19 checks). An initial comparison mixed in-memory tuples with saved JSON lists;
canonical JSON comparison corrected that harness check without a source change.
No native calculation or refinement is repeated. The older independent W207
centroid measurement agrees within 1e-12 Å:

| Selected-region motion from the original model | Centroid shift | Atom RMS | Maximum atom motion |
| --- | ---: | ---: | ---: |
| W207 initial bend | 0.2530 Å | 1.7656 Å | 4.9618 Å |
| W217 maintained seed | 0.00505 Å | 0.05695 Å | 0.33260 Å |
| W217 recovered | 0.00287 Å | 0.02783 Å | 0.11760 Å |

All rows use the same explicit 205 present-atom region in its original crystal
frame. These numbers do not measure displacement from a helix centerline and do
not meet either requested stress target. Receipts and source bindings stay in
`NASolve:branch-artifacts/willow/w218-displacement-summary/`; the roadmap pins
them. The next stress declaration must name its centroid weights/vector and
initializer/recovery bounds before coordinates are generated.

## Run a bounded collective trial (W226)

`nasolve.topostitch_trial.run_native_motion_trial` adds an explicit six-parameter
optimizer driver alongside the unchanged Cartesian `run_native_masked_trial`.
It consumes a source-bound `TaperedMotion` and a caller-qualified callback,
for example `lambda p: objective.evaluate_motion(motion, p)` on an already
qualified `NativeMaskedObjective`. Native construction, original chemistry,
corrected forces, neighbor policy and model/process lifetime stay with their
existing owners. Supplying a digest is not independent source authentication.

```python
from nasolve.topostitch_trial import run_native_motion_trial

report = run_native_motion_trial(
    lambda p: objective.evaluate_motion(motion, p),
    motion,
    initial_parameters=[0, 0, 0, 0, 0, 0],
    max_iterations=20,
    max_optimizer_calls=100,
    max_evaluations=153,
)
```

Parameters and gradients use three rotation-vector components in **degrees**
and three translations in **Å**; there is no hidden rescaling. The driver checks
that every callback returns the exact prescribed complete points, a finite
scalar and six finite gradients. It counts attempted callbacks, including failed
ones. The total budget reserves two 26-call derivative audits plus one baseline
restoration: `max_evaluations >= 53 + max_optimizer_calls`. The underlying
objective must separately have enough remaining budget; this driver cannot
grant extra native evaluations. Callback counts are not a count of any hidden
native work inside a supplied callback.

The installed scitbx optimizer is byte-pinned. Initial/final derivatives reuse
the existing two-step absolute 0.001 policy with correct per-variable unit
labels. Accepted-step history remains distinct from evaluated/rejected trials.
Errors, count mismatches, source drift and failed restoration cannot leave a
successful result. The reported stop reason and convergence criterion remain
separate from `ENDPOINT_DERIVATIVES_PASS`; an iteration cap is not convergence.
An interrupted run does not start an extra restoration callback.

The additive schema-1 `topostitch-bounded-native-motion-trial` report contains
bindings, limits, compact trace, accepted steps, derivative audits, stopping and
restoration evidence. It writes no coordinates and grants no geometry/adoption
permission. **No PDB-rounding qualification is claimed.** Rounding generally
moves an endpoint off the exact six-parameter surface; use the existing masked
byte audit and qualified native receiving/geometry checks separately. Existing
Cartesian reports, CLI/defaults, dependencies and ordinary execution are unchanged.

W226 qualification: **378 focused source tests and 378 relocated-installed
passes**, including 19 new protocol regressions. The first 15 new cases failed
before the implementation. The clean wheel was built offline; its build source
and original install path were removed before testing the relocated install.
Wheel SHA256:
`ed39b27fb3219982e12295c01d901d1b181ea34c9a080d867869a0877cd3dc65`.
The eight test files are `test_topostitch_{trial,transport,local,endpoint,
preparation,native_window,checkpoint,execution}.py`, run with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` and `python -B -m pytest -q -p
no:cacheprovider` (the installed run substitutes the relocated package path).

One actual **Phenix 2.2.1-6174** installed-driver qualification completed a
zero-cycle preparation and read-only geometry optimization, **not refinement**.
All 24 optimizer evaluations, 20 accepted steps and final coordinates/energies
match W223 exactly; the stop remains the declared 20-iteration cap. Both endpoint
derivative audits pass the unchanged absolute 0.001 bound (maximum error
0.000850484). The driver counts **77 callbacks**; the observer counts **80 native
geometry evaluations**, including its three separate baseline/endpoint checks.
There are no coordinate writes, diffraction scores, fits or automatic adoption.
All source chemistry, data and hooks survive/restored; **26 cold checks pass**.
A redundant post-driver gradient readback differs by at most 3.93e-13, within
its 1e-10 comparison; the optimizer trajectory itself matches exactly. The
first cold reader's overly strict equality assumption is preserved locally.

Local receipts use the `NASolve` anchor under
`branch-artifacts/willow/w226-collective-trial/`: `install/installed-check.json`,
`native-review.json`, and the frozen native request/execution/record. Reproduction
controllers live under the same anchor's `branch-artifacts/willow/runners/`:
`w226-install.py`, `w226-native-parity.py`, `w226-native-observer.py`, and
`w226-review.py`. These generated science/installation artifacts are excluded
from Git. They qualify this frozen synthetic trajectory, not general scientific
repair or ordinary integration. **The complete suite is deferred to the merge
gate under Rowan's direction for tonight's focused run; it is not claimed passed.**


## Keep the measured core fixed when a window expands (W227)

`CoordinateMask.displacement_summary` accepts optional `measurement_indices`,
a nonempty list/tuple of distinct indices **within the complete movable mask**.
The mask still validates every candidate coordinate, every movable displacement
bound and every fixed atom before reporting the subset. Explicit weights follow
measurement order and remain strictly positive; omission means uniform atoms.

```python
# expanded_mask already declares and validates the complete editable region.
core = expanded_mask.displacement_summary(
    candidate_points,
    measurement_indices=original_core_indices,
)
whole = expanded_mask.displacement_summary(candidate_points)
```

`atom_indices` identifies what was measured. Only the explicit-subset form adds
`motion_atom_indices`, retaining the complete editable selection. Centroid/RMS/
maximum describe the measured core, not all surrounding motion; call the default
form separately to inspect the whole window. Existing default return values are
unchanged. This does not select/expand a window, move a protected junction, grant
motion permission, align coordinates or define a helix centerline. Actual source,
correspondence and frame qualification remain with the caller.

The distinction is observable in the saved W219 coordinates: the original
205-atom core moved **10.000 Å**, while including its unchanged flanking pairs
(287 atoms total) reports **7.142857 Å**. Keeping the original measurement subset
reproduces its 10.000 Å target under that broader declared mask. This is a
read-only measurement comparison, not a newly executed expanded-window repair.

Validation: **14 regressions fail against the qualified W226 installed API**;
**392 source/392 relocated-installed focused tests pass**. The same eight-file
command as W226 is used, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` and
`python -B -m pytest -q -p no:cacheprovider`; the relocated run substitutes the
installed package path after the build source and original installation are gone.
The wheel SHA256 is
`012dd56390d0360eabd88b454808af716bd3a0bbe3b046c9c4751dc1efc566cd`.
Four saved endpoints each reproduce their complete old default report and core
metrics exactly. **21 readback checks each** pass in source, installed Python
3.12 and Phenix Python 3.11. `TaperedMotion` code is unchanged. No native geometry
call or refinement ran; W226's separately frozen native qualification stays
bound to its original installation. The complete suite remains deferred to the
merge gate under tonight's focused-validation direction.

Local receipts are anchored at
`NASolve:branch-artifacts/willow/w227-core-measurement/`; the controllers are
`branch-artifacts/willow/runners/w227-install.py` and `w227-readback.py`.
The first new-test attempt had a missing test import and is preserved as a setup
error, not counted as fail-before evidence. Corrected tests were replayed against
W226 before qualification. Source/install/readback logs and generated coordinates
are not committed; no existing artifact migration is needed.


## Measure internal stacking placement (W230)

`helical_twist.inspect_helical_region(..., include_stacking=True)` adds
`stacking_geometry` to the existing source-bound canonical report. The default
remains `False`; default reports, CLI and existing comparison/weighted-summary
APIs are unchanged. This is an opt-in reporting field, not a new model schema
or a stacking restraint.

For each adjacent declared pair, the reader keeps both strand identities and
core/flank roles, and measures each strand separately using the existing fitted
base planes and observed ring atoms. It reports acute unoriented plane angle,
ring-centroid separation, unsigned spacing along the aligned mean normal and
lateral centroid displacement. The two displacement components reconstruct the
centroid distance. No C1′ or phosphate enters the ring centroid. The existing
frame availability policy still requires C1′; missing or unsupported frames
remain unavailable. Missing one strand does not erase the other strand. Explicit
pair breaks suppress both corresponding strand steps.

Planes at 90° have an ambiguous mean normal: angle/distance remain available,
but normal spacing/lateral offset do not. Coincident or coplanar centroids can
still give measured zeros even when signed twist is unavailable. Zeros are
observations, not acceptance. Acute unoriented planes cannot detect a flipped
base; retain sugar/chirality and atom-identity audits separately.

Within-pair geometry and signed step twist remain in `simple_step_twist`.
Lateral displacement is not a ring-overlap area, contact or stacking energy.
There is no universal parallelity/spacing cutoff, local-axis inference or
permission to move a junction. Canonical identity-image PDB scope and caller
fit limits are unchanged. Periodic context needs an independently verified
image binding before use; this API still refuses nonidentity `HelicalSite`s.

**Validation.** Thirteen regressions fail on the previous API and pass after the
change. The four helical-reader test files pass **116 source / 116 relocated
installed** tests, including existing source/CLI/relocation controls. The build
source and original installation paths were removed before installed validation.
Wheel SHA256 `8cd366f1c2a7f88a673d559324ad36b27cb4674f8df9812dd64d0fc8e7c7ec73`.
Exact commands from the Willow checkout (explicit external environment anchors
are local validation provenance, not artifact resolution):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/private/tmp/alder-validation-20261121-01/lib/python3.12/site-packages \
  ../NASolve/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_helical_geometry.py tests/test_helical_twist.py \
  tests/test_helical_comparison.py tests/test_helical_summary.py
```

Six immutable W217/W219/W223/W224 endpoints give 96 cold checks in each
source/installed readback; reports are byte-identical across those contexts.
No coordinates, Phenix/Coot runs or refinement outputs were generated. The
original 10 Å initializer keeps the source maximum neighbouring plane angle
(12.8204°), while maximum lateral ring-centroid offset grows from 3.5014 to
10.5321 Å. Rejected direct recovery reaches 35.6597° and 10.3348 Å; staged
recovery returns to 12.6964° and 3.4816 Å. These are maxima over twelve
same-strand steps, not necessarily the same step. Recovery near the synthetic
source is not evidence for a distinct experimental shape or ideal geometry.

Local evidence uses the NASolve anchor, `branch-artifacts/willow/w230-stacking-readback/`:
`installed-check.json`, `source-readback.json`, `installed-readback.json`, and
source/installed test logs. Controllers are `branch-artifacts/willow/runners/w230-install.py`
and `w230-readback.py`. They resolve saved models through the prior checkout's
explicit model references and hashes. Raw science is deliberately excluded from Git.
One coordinated complete Willow suite at checkpoint
`c4b95b20b1d045c5f06a9572c3774b3da952c6a2` also passes: **2481 passed,
3 skipped, 234 passing subtests**, 107.35 s. Command uses the same environment
above with `-m pytest -q -p no:cacheprovider` and no file restriction; thread
limits `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`.
`full-suite-owner.json`, `full-suite-review.json` and `full-suite.log` retain
exact invocation, source commit and result. The three skipped cases remain
unqualified. This is software validation, separate from native science; no
scientific fitting experiment was launched for W230.


## Compare internal stacking between named states (W233)

Use the existing `helical_comparison.compare_helical_states` with
`simple_twist=True`, an explicit `max_ring_fit_rmsd_angstrom`, and
`include_stacking=True`. Both source models, ordered pairs and strand
correspondence are still explicit. No alignment or matching is inferred.

Each directed step gains two `stacking_geometry` entries, labelled `strand_i`
and `strand_ii`. Each carries reference, candidate and ordinary difference for
plane angle, centroid distance, normal spacing and lateral offset. Acute plane
angle differences are not wrapped and are not signed bend angles; the existing
signed-twist differences retain their original wrap policy. `coverage.stacking_changes`
counts each metric separately. Embedded measurements retain their exact original
source and frame provenance.

Missing/reversed/unmatched adjacency never becomes a step by compressing the
mapping. A missing base frame leaves the other strand measurable. At an ambiguous
mean plane, the observed angle and centroid distance can still be compared while
normal spacing/lateral offset remain unavailable. Default reports are unchanged;
only the explicit option adds fields, with no CLI, dependency or schema migration.
This does not measure overlap, validate physical correspondence or adopt a model.

**Validation:** nine fail-before regressions; **125 source / 125 relocated
installed** tests using the same four helical test files/command as W230.
The original build source and installation are absent before relocated tests.
Final wheel SHA256 `03a7a54417b1245ae11c2ee2559fc4cd3ddc93c7b35bbbebef302b81b2033fd9`.
Six saved comparisons give **254 cold checks** per source/installed context
and exact report parity, including 240 independently subtracted saved scalar
changes. The real C543 ancestor/child comparison preserves all seven phosphate
span changes while reporting only eight of twelve strand steps for each stacking
metric: both PDU ring frames remain explicitly unsupported, not canonicalized.
This is a readback of Cedar's whole-model result, not a Willow narrow-window fit.

An unsupported descriptive frame does **not** mean its native restraint is
absent. Cold inspection of this exact original-source capture finds 57 actual
parallelity terms: 38 same-strand adjacent and 19 cross-strand. Four adjacent
terms include PDU (A11–A12, A12–A13, B3–B4, B4–B5). Their source-specific atom
selections are native evidence; they do not extend this reader's canonical-frame
qualification. Plane orientation alone does not establish normal spacing or
lateral overlap. All 57 terms are fixed in the six-atom seam experiment.
The authenticated receipt is already pinned in W235; cold rows and exact
source/native movable-index mapping are retained under the NASolve anchor
`branch-artifacts/willow/w239-local-closure-receiving/` in
`source-stacking-context.json` and `stacking-context-mapping-check.json`.
No new native evaluation, restraint or pairing authority follows.

Local NASolve evidence: `branch-artifacts/willow/w233-stacking-comparison/`
(`installed-check.json`, `source-readback.json`, `installed-readback.json`,
`readback-parity.json`, test logs); controllers `runners/w233-install.py` and
`runners/w233-readback.py` under `branch-artifacts/willow/`. A pre-format wheel
was superseded and its task-owned temporary package removed; final qualified
files and fail-before evidence remain. No native calculation or coordinate
write, and no repeat of W230's complete suite under the coordinated cadence.


## Admit only accepted atomic trial endpoints (W238)

The existing `run_native_masked_trial` now uses the same successful-endpoint
rules as the collective-motion driver. A normally returning native optimizer
must report no error, bounded iteration counts and an evaluation count matching
the recorded trace. Its final coordinates must be its last accepted step; when
no step was accepted, only the unchanged initial coordinates may be reported.
Previously, a returned error or restored/unaccepted trial could pass endpoint
derivative checks and appear successful.

Failures retain the existing `FAILED` outcome and original error, with any
last-accepted-point audit confined to `failure_endpoint`. That diagnostic never
becomes an accepted candidate. A legitimate unchanged start remains reportable,
and an iteration cap remains distinct from convergence. Successful report shapes,
function arguments, source masks and scientific force calculations are unchanged;
no schema migration or new optimizer is introduced.

Five rejection regressions fail against the previous source; an unchanged-start
control already passes. Focused source and source-free relocated-wheel checks
pass **398 tests each** across trial, transport, local proposal, endpoint,
preparation, native-window, checkpoint and execution files. The installation's
build source and original installation path are removed before installed tests.
Seven cold checks show W235's existing saved endpoint satisfies these stricter
rules, including exact accepted coordinates/scalars/gradient norm and 53 recorded
optimizer evaluations. No new Phenix execution or scientific rerun is implied.

Evidence at the NASolve anchor `branch-artifacts/willow/w238-accepted-endpoint/`
records exact argv/environment/Python, module/wheel/test hashes, raw logs and
source/installed counts in `*-command.json`, `fail-before.json` and
`installed-check.json`. The initial harness incorrectly expected the older
384-test count; its log is preserved, the successful 398-test source run was
reused, and installed checks ran once. Generated scientific data remain outside
Git. Final software-suite qualification is recorded in the current handoff.


## Refine one registered phosphate connection (W240)

The existing fitting command now offers an explicit native route:

```sh
nasolve-topostitch-fit native-phosphate --request request.json --out new-job \
  --phenix /path/to/phenix --cedar-source /path/to/qualified/package-root
```

`--cedar-source` points to a package root containing `nasolve/`, not the repository
root. Standalone Willow does not contain all required Cedar modules: supply a
compatible, qualified Cedar installation explicitly. A combined installation may
omit that option only after the owners have been integrated and validated.
W240 qualifies Cedar C545 with Phenix **2.2.1-6174**; it does not claim arbitrary
Cedar/native version compatibility. Install the `topology` extra for Gemmi. This
route does not require SciPy; the unchanged geometric fitting route still does.

**W293 worker compatibility:** an explicit Cedar package now supplies its native
runtime and all relative companion imports in an isolated namespace throughout
worker execution. This avoids mixing older Willow helpers with newer Cedar
helpers. The worker imports only the refinement and phosphate runtime owners;
Phenix Python does not need catalogue-only spreadsheet dependencies for that
step. Controller dependencies remain unchanged. Source pins, request fields,
six-atom selection, force calculations and exact-frame defaults are unchanged.
This fixes branch composition; it does not establish arbitrary Cedar-version
compatibility or qualify a combined release. Exact validation and the separate
19-atom diagnostic are recorded in the [W293 evidence](topostitch-periodic.md#w293--qualify-coupled-forces-and-isolate-native-worker-imports).

**W294 explicit frame policy:** schema-1 requests may add
`"native_frame_policy": "native-roundoff"` to use the existing qualified native
arithmetic policy for either ML or MLHL. The alternative is `"exact"`. Omission
preserves the historical defaults: exact ML frames, qualified MLHL roundoff.
There is no numeric tolerance knob. The existing 1e-10 bound applies to cell
lengths/matrix components in Å and angles in degrees; space group stays exact.
Each anisotropic tensor is compared in its own Cartesian frame at the existing
1e-12 Å² bound, with unchanged ADP modes, occupancies and fixed coordinates.
The same explicit choice applies at initialization and returned-model checking.
The chosen field is frozen in the job plan. Earlier builds reject this new field;
no migration is needed for old requests. A preflight PASS is still not a fit or
scientific acceptance. See [W294 validation](topostitch-periodic.md#w294--complete-ordinary-preflight-with-explicit-frame-roundoff).

The API is `topostitch_phosphate.run_registered_phosphate_refinement(request_path,
output_directory, *, phenix, cedar_source=None, timeout_seconds=1200, preflight_only=False)`.
The historical request uses these mandatory schema-1 fields; W250 adds the
[optional phased contract](#admit-experimental-phases-and-fixed-scattering-w250):

```json
{
  "schema_version": 1,
  "kind": "topostitch-phosphate-refinement",
  "inputs": {
    "model": {"path": "inputs/model.pdb", "sha256": "SHA256"},
    "registration_model": {"path": "inputs/registered.pdb", "sha256": "SHA256"},
    "data": {"path": "inputs/data.mtz", "sha256": "SHA256"},
    "registration": {"path": "inputs/registration.json", "sha256": "SHA256"},
    "discovery": {"path": "inputs/discovery.json", "sha256": "SHA256"},
    "continuations": {"path": "inputs/continuations.json", "sha256": "SHA256"},
    "native_receipt": {"path": "capture/receipt.json", "sha256": "SHA256"}
  },
  "restraints": [{"path": "inputs/restraints.phil", "sha256": "SHA256"}],
  "continuation_id": 1,
  "cycles": 1,
  "iterations": 50,
  "max_displacement_angstrom": 5,
  "wxc_scale": 0.5,
  "data_labels": "IMEAN,SIGIMEAN",
  "free_label": "FreeR_flag",
  "test_flag_value": 0
}
```

Replace each `SHA256` with the actual 64-character lowercase digest. Paths resolve
relative to the request; explicit absolute CLI/input paths remain supported.
`model` is the source-frame model to refine. `registration_model` is the model
bound by the existing Pine registration, discovery and continuation records.
Cedar qualifies inheritance between them and authenticates the **complete** native
reference capture, including its referenced files. Supply every intended ordinary
restraint/dictionary in order; the capture is evidence, not a substitute for those
files. No partner, nick, image or sequence is inferred. Reference identities and
exact image must already describe the requested construct.

The bounded route permits 1–5 cycles, 1–200 iterations, 0–10 Å maximum endpoint
motion (strictly positive), positive `wxc_scale` up to 10, and 1–30 restraint files.
`wxc_scale` is the requested initial scale, not a fixed diffraction weight.
Phenix can estimate `wxc` and adapt its scale even with the weight-optimization
search disabled; compare the native logs before calling two objectives matched.
[W241 records the observed distinction](topostitch-periodic.md#w241--compare-geometry-seeded-and-direct-native-receiving).
Timeout is 1–3600 seconds **per phase**, default 1200. It freezes inputs and native
capture into a new job directory, records source hashes/native version, then runs
one preflight and one coordinate-only fit in separate owned processes. Changed
inputs, plan or loaded source files prevent the next phase; a failed preflight
cannot launch the fit. Fit must start from the same native atom/data state.

Only six unambiguous canonical, fully occupied connecting atoms are movable:
acceptor **P/OP1/OP2/O5′/C5′** and donor **O3′**. All rings and other atoms are held.
Cedar evaluates its four angles/three torsions in one local contiguous image and
returns forces to the original ASU; native bond and exclusion-shell owners remain
active. This introduces no whole-ASU rewrite and does not grant general duplex,
modified-endpoint or multi-connection movement. Unrelated modified residues may
remain in the fixed context with their supplied dictionaries.

On return, actual compiled selection, atom inventory, fixed coordinates,
occupancies and native ADP modes/Uiso must survive exactly. W243 compares active
anisotropic tensors in the unchanged Cartesian frame at the round-off bound
[below](#preserve-cartesian-adps-through-native-return-w243). Exact ordered reflection
indices and Free-R flags must survive too. Phenix's normal common positive F/SIGF
rescaling is recorded and allowed; filtering, changed flags, duplicate indices or
nonuniform amplitude/sigma changes refuse. Small R factors are not an acceptance
criterion. A refinement must actually invoke all seven image terms with gradients.

`result.json` reports `REFINED_FOR_REVIEW`, with a checksummed run-relative candidate
reference, `scientific_acceptance: false` and `checkpoint_created: false`.
`fit/candidate.pdb` changes only movable XYZ fields in the original PDB bytes;
Cartesian ANISOU and all other records remain exact. Full-precision coordinates,
native model/map/geometry outputs, state audits and logs remain beside it.
Original PDB metadata are therefore preserved rather than refreshed: the candidate
is **not deposition-ready**. Inspect the actual geometry, density and R statistics.
No fallback silently removes a restraint or declares a successful repair.

A request-relative relocation regression and source-independent wheel tests cover
software/input resolution; they do not qualify replay of a moved native job.
Native/source installation paths and historical capture references remain provenance.
See [W240 native evidence](topostitch-periodic.md#w240--reach-registered-phosphate-refinement-through-the-installed-product).


## Observe printed native XYZ weights (W242)

`refinement_weight_observation.observe_native_xyz_weights` reads the already
written log; it never imports Phenix, changes weights or launches a program:

```python
from nasolve.refinement_weight_observation import observe_native_xyz_weights

observed = observe_native_xyz_weights(
    log_bytes,
    expected_log_sha256=trusted_log_digest,
    expected_cycles=5,
)
```

The caller supplies immutable bytes, a previously trusted SHA-256 and the exact
cycle count. Qualification covers the ordinary X-ray XYZ summary printed by
Phenix **2.2.1-6174**. It requires ordered cycles 1…N, one known objective equation
and weight summary per cycle, and one final completion marker. Truncated or
concatenated logs, missing/duplicate/out-of-order summaries, unsupported equations,
malformed/nonfinite/negative weights, wrong digests and ambiguous counts refuse.
Joint X-ray/neutron equations are outside this parser's scope. No version is
inferred from a directory name or claimed from the log's chemical-library path.

The additive schema-1 `native-xyz-weight-observation` result records source SHA,
one-based source line numbers, exact printed strings, numerical `wxc`,
`wxc_scale`, `wc`, their `printed_data_factor` product, and a
`printed_data_to_chemistry_ratio` (unavailable when `wc=0`). Values are explicitly
**rounded display evidence**, not recovered full-precision weights. The
`identical_printed_weights` flag compares those displayed triples only. It cannot
establish fixed policy or equal objectives. `native_policy_inferred`,
`runtime_authority` and `scientific_acceptance` remain false. A completion marker
is not a process/native receipt, and this API does not qualify a successful run.

W241's two existing logs reproduce all ten manually audited cycle values exactly.
The observer retains the large native weighting difference without running
another fit. **278 focused source/278 isolated installed tests** pass; 17 new
cases cover distinct reader behavior. Source and installed results are identical
(12/13 saved-log checks), including a standard-library-only installed replay with
`python -S` (13 checks). Original build source was removed before installed tests;
Python 3.10 syntax and installed/source module hashes agree. No optional dependency,
CLI change, native hook, default change or existing-report migration.

Focused command, with existing Gemmi/test dependencies available for adjacent
TopoStitch tests:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q \
  tests/test_refinement_weight_observation.py tests/test_topostitch_phosphate.py \
  tests/test_topostitch_endpoint.py tests/test_topostitch_captured_job.py \
  tests/test_topostitch_recut_bundle.py tests/test_topostitch_backbone_intent.py \
  tests/test_topostitch_transport.py
```

Actual local commands append the existing dependency root to PYTHONPATH. The
same test fixture closure runs outside the checkout against a fresh wheel built
with `pip install --no-deps --no-build-isolation --target INSTALL BUILD_SOURCE`.
Source tests: 278 in 9.57 s; installed: 278 in 9.71 s. No full-suite repeat because
this isolated, opt-in reader does not alter any workflow or shared native behavior.
Evidence/logs and module pins are local at the NASolve anchor
`branch-artifacts/willow/w242-native-weight-observer/`; the archive move verifies
231 original file hashes. `validation.json` records scope and exact environment.
No private native logs, coordinates or diffraction data are committed.

**Reuse boundary:** Cedar already owns a fixed-unit native protocol in
`cif_counted_refinement.refinement_scope`, emitted by AutoRefine and checked by
`refinement_counted`. It validates actual/returned parameters for
`fix_wxc=wc=1`, one counted cycle, explicit process/selection/target constraints
and its own disabled-changing-target conditions. That qualification cannot be
transferred to Willow's five-cycle six-atom protocol with bulk scaling enabled.
W288 now qualifies a separately pinned local experiment with common native
coordinate coefficients, using the existing receiver and observed native weights.
[Its measured result and limits](topostitch-periodic.md#w288--the-original-pose-catches-up-under-matched-coordinate-weights)
do not extend counted scope or add a maintained fixed-weight product mode.
Matched coefficients do not freeze the entire likelihood/scaling objective.
No second weighting engine or fixed-mode switch is introduced by W242.


## Preserve Cartesian ADPs through native return (W243)

Two real anisotropic dry runs reached the W240 return checker with only
reciprocal U* round-off changed (up to 4.34e-19 / 6.51e-19). Exact U* list equality
incorrectly rejected them. W243 snapshots the actual native cell parameters,
space-group string and orthogonalization matrix in both native state receipts.
It requires that frame to remain exact, converts U* with **O U* Oᵀ**, and compares
all six Cartesian components (U11/U22/U33/U12/U13/U23) at an **absolute 1e-12 Å²**
limit, with no relative tolerance. This accommodates arithmetic round-off, not
an ADP-refinement allowance. Full tensor/mode and coordinate checks apply to fixed
as well as movable atoms.

ADP usage flags and Uiso remain exact; isotropic atoms retain their previous
exact inactive-U* check. Changed cell/group/matrix, changed modes, nonfinite
components and real tensor changes refuse. Historical private checker calls
without both frame snapshots keep exact reciprocal comparison, rather than
silently gaining a tolerance. New initial/returned-state receipts add `frame`;
`observation_audit.adp_audit` records mode, count, measured maximum, units and
bound. Requests/CLI/checkpoints stay unchanged. A fresh native job/preflight is
needed for the new evidence fields; old immutable receipts are not rewritten.

The source-preserving exporter is unchanged: original ANISOU, ATOM B/Q and all
other noncoordinate records remain byte-exact. This is separate from the native
scattering-state comparison. Cedar owns the source-ANISOU-to-native starting check
and native model/F-model synchronization. W243 does not re-interpret the exported
candidate or claim whole-ASU tensor/materialization qualification.

**Validation:** 293 focused source tests (9.31 s), 293 isolated installed tests
(9.01 s), including 15 new cases. Both saved failures reject under the old installed
code and pass under source, installed and relocated-installed code. Read-only
Phenix **2.2.1-6174** replay covers all 1271/1275 anisotropic atoms: maximum Cartesian
differences 7.11e-15 / 5.33e-15 Å²; independent native cctbx conversion agrees within
3.56e-15 Å². For each model, a deliberate 1e-4 Å² change to each diagonal and
off-diagonal component is rejected (12 refusals). Candidate export keeps all source
ANISOU/B/Q bytes, and provided input files stay unchanged. Both saved 862-atom
isotropic W241 controls still pass strict thermal checks.

Use W242's focused test command (same seven files). Tests run with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` plus the existing dependency root;
installed tests run outside the checkout with the old build source removed.
Python 3.10 syntax and installed/source module hashes agree. These were cold
replays of existing arrays, **zero new native preflights or refinements** by
Willow; Rowan owns the separate live execution. No full-suite repeat for this
isolated return comparator. Evidence and the frozen installed package live at
NASolve anchor `branch-artifacts/willow/w243-cartesian-return/`; private arrays,
models and scientific data are excluded from Git. No manuscript files were edited.


## Observe scattering for a pinned saved recut (W245)

`topostitch_recut_bundle.observe_relabel_scattering` binds the existing independent
Gemmi scattering observer to an exact immutable preview receipt. Previously a
caller reconstructed the proposal's image list and connection declarations when
calling `observe_registered_relabel_scattering`; the new API derives them from
the replayed saved packet, for explicit-image and forest proposals alike.

```python
from nasolve.topostitch_recut_bundle import observe_relabel_scattering
report = observe_relabel_scattering(
    preview_directory,
    expected_receipt_sha256=recorded_preview_sha256,
    hkls=[[1, 2, 3], [-1, 3, 2]],
    max_structure_factor_terms=5_000_000,
)
```

The supplied digest must identify the exact saved `preview.json`, not a graph
fingerprint or a newly calculated digest substituted for the intended choice.
The packet owner revalidates local anchored source/proposal inputs and the full
preview. The observer uses the verified graph's complete requested node images,
retains schema-2 explicit backbone continuations and applies the original work
budgets. Its source, graph and preview bindings must reproduce the saved choice;
changed packet bytes or a mismatched returned calculation refuse. No original
external source location is consulted.

The additive schema-1 `topostitch-representative-scattering-observation` report
contains `preview_receipt_sha256`, the unchanged nested scattering `observation`
and its own `report_sha256`. Source-byte verification is recorded separately
from scientific authority. Existing proposal/preview schemas, direct scattering
API, CLI defaults and previous reports remain unchanged; no migration is needed.
Nothing is written, selected, refined or serialized. Gemmi 0.7.5's neutral-atom
sampled complex Fcalc, float32 anisotropic storage and the existing scope limits
still apply. This is not complete reciprocal-space, special-position chemistry,
serialized-ADP or whole-ASU acceptance. The original tensor/scattering engines are
reused unchanged; Cedar remains the owner of native forces.

**Validation:** six distinct new boundary cases fail before implementation;
**208 focused source tests (12.45 s) and 208 isolated installed tests (11.66 s)**
pass. Coverage includes explicit anisotropic and forest/declared-continuation
packets, wrong receipt pins before calculation, packet drift, mismatched computed
preview, byte-exact read-only behavior, work budget delegation and relocated
packet replay after original sources are removed. Existing screw/centered/oblique,
wrong-tensor, coordinate-damage, chemical-boundary and ambiguous-partner controls
are reused unchanged. Python 3.10 syntax and installed/source bytes agree.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q \
  tests/test_topostitch_scattering.py tests/test_topostitch_recut_bundle.py \
  tests/test_topostitch_continuations.py tests/test_topostitch_forest_bundle.py \
  tests/test_topostitch_backbone_intent.py tests/test_topostitch_transport.py
```

Actual local commands append the existing test/Gemmi dependency directory to
PYTHONPATH. Installation uses `pip install --no-deps --no-build-isolation --target
INSTALL BUILD_SOURCE`; the build source is removed before installed tests, which
run outside the checkout against the copied test-fixture closure. The initial
installed attempt omitted relative fixture imports and failed collection; its
log is retained, the fixture closure was corrected, and the package was unchanged.
The complete evidence/install directory was then relocated: all 222 file hashes
match, the old location is absent and the relocated package imports correctly.
Local receipts/logs live under NASolve anchor
`branch-artifacts/willow/w245-saved-scattering/`. No native Phenix execution,
full-suite repeat, scientific dataset copy or generated payload commit was needed
for this isolated read-only composition boundary. P03 remains partial.


## Inspect a serialized recut against its saved source (W248)

`topostitch_recut_bundle.observe_relabel_serialization` checks whether a separately
saved PDB/mmCIF still represents the chosen recut. Previously this comparison was
only the W247 local experiment. The maintained API is read-only: it writes no
coordinates, adopts no ASU and activates no bond or restraint.

```python
from nasolve.topostitch_recut_bundle import observe_relabel_serialization
report = observe_relabel_serialization(
    preview_directory, exported_model,
    expected_receipt_sha256=recorded_preview_sha256,
    expected_model_sha256=recorded_export_sha256,
    coordinate_format="mmcif",
    max_coordinate_component_error_angstrom=1e-6,
    max_u_component_error_angstrom_squared=1e-6,
)
```

Both SHA-256 values must identify the intended saved bytes. The packet owner
replays its existing anchored inputs and `ReferenceFrame`; drift before or during
inspection refuses. PDB/mmCIF selection and finite nonnegative precision bounds
are explicit. These are caller-declared **numerical review bounds**, not chemical
or crystallographic acceptance thresholds.

The inspector checks the complete atom inventory by chain, residue number,
insertion code, component, atom name and alternate location. A one-to-one
`source_to_export_indices` permutation records reordered files; it never joins
independently sorted arrays just by index. Missing, extra or duplicate atoms,
changed record type/element/charge, B/occupancy, anisotropic presence, parsed cell
or space group refuse. CIF atom IDs, required scattering fields and six Cartesian
U fields must be explicit and unambiguous; missing values are not replaced with
parser defaults. NCS expansion and multiple coordinate models/blocks are outside
this scope. Author atom identities must remain resolvable; this is not a renaming
or polymer/entity metadata importer.

Coordinates and all six Cartesian U components are compared against the existing
bound frame. U values explicitly describe **Gemmi's float32 Atom state**, including
rotation/readback rounding; this does not preserve a higher-precision native
scattering object by implication. The report records maximum component errors,
counts exceeding each bound and `within_requested_precision`. A coordinate/U
precision failure remains an observed result with `scientific_acceptance=False`;
it is not silently accepted or confused with an identity/binding failure.

The existing backbone-intent owner supplies each resolved O3′–P partner and exact
directed image. The inspector measures that geometry in the reread model and
retains unresolved endpoints. `declared_link_observations` comes from the external
verified graph; `annotations.parsed_connection_count` describes the coordinate
reader separately. `declared_graph_verified_in_file` remains false even when
counts happen to match. No proximity-based partner or chemical nick is inferred.
Native chemical interpretation and actual annotation correspondence need their
own qualification.

The additive schema-1 `topostitch-representative-serialization-observation` carries
receipt, exported-model/source/graph digests, numerical precision and permutation,
external-intent digest, link observations and its own report digest. Existing
packets, reports, CLI defaults, force owners and direct scattering API are unchanged;
no migration is required. This observer calculates no structure factors. Use the
existing W245 scattering observation for the same saved recut and preserve W247's
independent native readback evidence; neither alone closes whole-ASU acceptance.

**Validation:** 29 focused cases, including 24 demonstrated fail-before cases,
cover explicit anisotropic and forest/isotropic packets, reordered atoms,
coordinate/tensor precision loss, changed inventory/thermal state/cell/group,
ambiguous CIF fields, exact pins, mid-read drift, explicit format/bounds and
relocation with the original packet directory gone. **237 source checks (17.42 s)
and 237 isolated installed checks (20.76 s)** pass using the six-file W245 command.
The source run's only warning was sandbox-denied pytest-cache writing; the installed
run disables the cache. Python 3.10 syntax, installed/source module bytes and the
existing cut-preview `--help` entry point pass. The disposable build source is
removed; all **219** archived file hashes match after relocation, the original
install path is gone, and the installed tests run from the relocated package.
Installation uses `pip install --no-index --no-deps --no-build-isolation --target
INSTALL BUILD_SOURCE` with the existing topology/test dependencies.

A full-suite attempt was stopped at Rowan's request to preserve Simon's focused
branch-testing scope. It had 285 passes, one skip and five campaign-process
failures caused by sandbox-denied `killpg`/`ps`, then exited on the requested
interrupt. Its partial log is retained; **there is no full-suite pass**. The
confirmed pytest process and recorded fixture-worker PIDs had exited. Complete
integration testing remains a pre-merge gate, not a claim made by this patch.

**Frozen real-model replay:** the maintained source and installed APIs return
identical reports for all twelve W247 files, including both expected default-mmCIF
tensor-bound failures. File hashes bind W247's unchanged independent Phenix
readback; no native fit or repeated Fcalc run is needed. All 60 declared backbone
links per model are measured. The two original image-spanning joins become local
in the compound recut, while six formerly ordinary links become image-spanning.
This is preserved topology in different representatives, not six new chemical
breaks; a future exporter must carry every boundary connection.

Generated observations, install receipts and logs remain under NASolve anchor
`branch-artifacts/willow/w248-serialization-observer/`. No datasets, coordinate
exports or scientific reports are committed. P03 stays partial: production writer,
connection/polymer metadata, native full-precision/cell policy, inverse edit import,
coupled refinement and scientific acceptance remain separate gates.

## Admit experimental phases and fixed scattering (W250)

**W295 shared source owner:** the maintained `NativePhasedGuard` delegates its
independent amplitude/Free-R/HL read to `refinement_diffraction_source`, received
unchanged from Alder. Explicit Bijvoet averaging, positive amplitudes/sigmas,
exact HL coverage, flag-superset coverage and Miller-index joins retain their
existing semantics. Target/optimizer/scattering checks and native-module pins
remain with the guard. The shared reader supplies no runtime or scientific
permission; ordinary ancestry, exact inputs and selectors remain caller-owned.
The old `_indexed` name aliases the shared join for compatibility. Historical
frozen workers and request/report schemas stay unchanged. See the
[W295 evidence](topostitch-periodic.md#w295--share-source-diffraction-reading-with-alder).


`native-phosphate` now has `--preflight-only` (API keyword
`preflight_only=True`). It creates a new immutable job, runs the same native
preflight, and returns `PREFLIGHT_COMPLETE_REQUIRES_REVIEW` without a fit or
candidate reference. A dry-run is input qualification, not a successful repair.
Omitting the option retains the preflight-then-fit sequence.

Historical schema-1 requests retain their unphased ML policy. A request may
add a `diffraction` object and **both** `inputs.phases` and `inputs.scattering`,
using the same explicit request-relative path/SHA-256 references as other inputs:

```json
{
  "target": "mlhl",
  "phase_labels": ["HLAM", "HLBM", "HLCM", "HLDM"],
  "fixed_scattering_groups": [
    {"selection": "element C", "f_prime": 0.0051, "f_double_prime": 0}
  ]
}
```

This is a **shape example**, not a complete scientific request or a prescribed
carbon value. Groups must cover every actual atom exactly once, with independently
declared finite values. The `scattering` JSON has schema version 1, kind
`topostitch-fixed-scattering`, the exact `model_sha256`, and a source-ordered
`atoms` array. Each entry contains the full six-field `model_atom_rows` identity
(`chain`, `residue_number`, `insertion_code`, `residue_code`, `atom_name`, `altloc`)
plus `f_prime` and `f_double_prime`. Missing, reordered or renamed atoms refuse.
This expectation is a caller-supplied scientific input; it does not infer or fit
anomalous scattering. For this MLHL geometry scope, every f″ must be **fixed zero**,
not a reported measurement. Phase MTZ files are dedicated diffraction inputs,
never extra restraints. Original anomalous data remain untouched.

The optional `topostitch_phased` observer independently reads the requested
native reflection arrays. Its initial scope requires unique measured amplitude/
sigma arrays, positive merged amplitudes and sigmas, integer original Free-R
flags, and a complete non-anomalous HL quartet. Bijvoet averaging is explicit;
no other observation filtering, phase substitution or guessed label selection
is allowed. Flags may include additional unobserved reflections, but all observed
HKLs and phase coefficients must survive exactly. Other input shapes refuse
rather than silently narrowing the experiment. Existing unphased input support
is unaffected.

Phenix finalizes its target and scattering groups **after** `Program.validate`.
The guard therefore reads the initialized driver before coordinate fitting:
actual MLHL target, enabled phases, coordinate-only strategy, complete indexed
HL coefficients/original flags, and exact disjoint fixed-scattering groups in
both model and diffraction managers. Model/data cells must agree within source
PDB printing precision; space groups must agree exactly. The source model and all
thermal/charge/scattering-type state remain bound. Element spelling is normalized
only in the optional phased state (`Hg` and `HG` denote the same element).
This does not normalize charge or allow another scattering species.

During fitting the observer also checks the **actual coordinate target object**:
its MLHL specialization, held experimental phases, aligned original flags and
observations, and current fixed f′/f″ state. A correct manager label cannot hide
a stale target. This wraps the existing native calculation without changing its
energy, derivatives or optimizer. The fit's initialized state must match its own
qualified preflight; return checks repeat the binding. Only the already qualified
common positive F/SIGF normalization is allowed. Missing observed gradient calls
cannot count as a completed phased fit.

The optional phased route also records both exact native crystal frames. Native
copying changed the measured FT frame by at most 4.27e-14 Å in its orthogonalization
matrix and 2.85e-14° in a cell angle. Its explicit arithmetic allowance is 1e-10 Å
per cell-length/matrix component and 1e-10° per angle, with exact space group.
Each displacement tensor is transformed in **its own** frame and still must agree
within the unchanged 1e-12 Å² Cartesian bound. This is separate from input
PDB/MTZ printing compatibility. Just-outside cell/basis changes and charge/species
changes refuse; the historical ML path retains its exact-frame default.

Reports add `prepared-state.json`, `diffraction-initial.json`,
`diffraction-returned.json`, and a phased
audit with source checks and coordinate-target call counts. Saved captures,
native errors and stopped-process records remain alongside the existing job
artifacts. The six-role movement scope, Cedar reference chemistry, tensor return
checks, review-only result and lack of checkpoint adoption are unchanged.
Older requests need no migration; older readers intentionally reject the new
optional fields. No campaign default or global AutoRefine policy changes.

W250 validation and native qualification are recorded in the current handoff and
roadmap. Full integration testing remains required before a supported merge.
Private models, phase arrays, reflection data and generated jobs stay local.


### Complete phased output without lossy next-run defaults (W252)

Explicit phased phosphate jobs set native `refinement.output.write_def_file=False`.
Phenix 2.2.1-6174 formats its optional next-run defaults before comparing group
selection strings literally; whitespace changes can abort output after all
refinement cycles. The same formatting rounds fixed f-prime. Replay therefore
uses the immutable request and checksummed original inputs, not printed `.eff`
or `.def` values. PDB, mmCIF, maps and final geometry output still use the native
writer and Cedar's unchanged final-state/written-model guards. Historical ML
requests keep their existing output policy; no request migration is needed.

Phased `science.json` additionally records `coordinate_target_checks` even when a
later writer or return check fails. These are counts of admitted target calls
before native evaluation, not proof that the calls returned successfully or that
a result is accepted. A successful result also retains the existing final
`diffraction_audit.coordinate_target_checks` alongside its full returned-state
checks. Old failed runs cannot acquire counts retroactively.


### Observe a failed atomic proposal without promoting it (W254)

`run_native_masked_trial` adds `failed_proposal` only when a call to
`objective.evaluate` raises a caught `ValueError`, `RuntimeError` or
`OverflowError`. The pre-call displacement values are copied before evaluation
can alter the optimizer's working vector. The original error, failed status and
separate `failure_endpoint` observation of the last accepted step remain intact.
Successful reports and optimizer-only errors after returned evaluations keep
their previous fields. Collective-motion trials are unchanged.

This additive observation stores compact SHA-256 digests of the proposed
ordered displacement vector and ordered mask indices, the source model SHA when
provided by the existing binding, the variable count/motion bound and at most the
**first exceeding displacement in mask order**: zero-based source atom index,
zero-based movable offset, move length and bound, all distances in Å. Digests use
ASCII compact JSON arrays (`separators=(',', ':')`, finite numbers only). The
source model and existing objective binding provide identity/reference context;
the digest does not reconstruct the missing full proposal. No new coordinate
array, energy, gradient or candidate is emitted.

`objective_returned=False` and `accepted_by_this_call=False` describe this call;
they do not claim the objective performed no partial work. The observer itself
adds zero evaluations. A null `first_exceeding_displacement` means no move beyond
the bound was found; it does not make a failed evaluation valid. Conversely an
observed excess does not classify the original exception as a motion error.
Malformed/nonfinite vectors or unrepresentable norms report `UNAVAILABLE` with
an observation error, while retaining the original trial error. Observation does
not retry, project, clip, relax the bound or change the optimizer's coordinates.

Nine focused cases cover failure before/after an accepted step, exact evaluation
counts, snapshotting before argument mutation, malformed/nonfinite values,
unrelated objective errors and mask-order identity. Both public rejection cases
fail on the preceding code because `failed_proposal` is absent. Combined scope:
274 source/274 relocated installed passes, one skip each; 83 trial tests pass.
All 216 installation files hash-match after original build/install paths are
removed; Python 3.10 syntax and installed entry-point help pass. Exact commands
are in `branch-artifacts/willow/w254-validation/validation.json` under the NASolve
anchor. This is synthetic/software and installation validation, **not a fresh
Phenix trial**. No global mechanics, numerical policy or request schema changes;
full integration suite remains a separate pre-merge gate.

W253's unrecorded rejected proposal stays unknown. Its known accepted step and
failed status cannot be upgraded by this patch, nor can the violating atom be
inferred retrospectively from the new reporting code.

### Bind an original mmCIF to a saved working recut (W256)

`topostitch_cif_source.load_relabel_cif_source(directory, model, ...)` binds one
SHA-pinned original coordinate mmCIF to the existing SHA-pinned working-PDB
preview. It replays the saved preview and frame owners; it does not replace the
working receipt with an original source or broaden W248's export-reader scope.
Supply `expected_receipt_sha256`, `expected_model_sha256`, an explicit
`component_aliases` mapping (possibly empty), and four nonnegative finite bounds:
`max_coordinate_component_error_angstrom`,
`max_u_component_error_angstrom_squared`, `max_b_error_angstrom_squared` and
`max_occupancy_error`. Bounds describe known working-file serialization error;
they are not permission to match an arbitrary refined child.

Every original atom must map once to a working atom through complete author-chain,
residue-number/insertion, component, atom-name and alternate identity. Only named
component spelling aliases may differ; unused aliases are refused. Record type,
element, charge, crystal and ADP mode must agree. A supplied symmetry-operation
table must equal the declared group. There must be one coordinate block; extra
blocks must be unique attached component definitions. Unsupported parser changes
to ordered identity, NCS expansion, missing/duplicate atoms, unexplained source
differences and input races stop the read. Explicit file paths remain required;
no basename discovery or hidden workspace lookup is added.

The immutable `CifRelabelSource` keeps exact `document_bytes`, original `atom_ids`,
the complete `working_atom_indices` permutation, raw double-precision
`positions_angstrom` and `u_cart_angstrom_squared` (absent tensors remain `None`).
Its `frame` maps the original-order positions and tensors using the existing
`ReferenceFrame` methods. Pass `frame.source_labels` and `frame.context_sha256`
to those methods. The new context digest binds the original file, aliases,
precision policy and saved preview; it is not the working receipt's digest.
`observation` returns a detached schema-1 descriptive dictionary with scalar/loop
category and component-block inventory, precision errors and source bindings.
Original B/Q and all annotations remain in exact document bytes.

**Scope:** source/working compatibility, not independent historical producer proof
or alias chemistry validation. Polymer paths and connection annotations are
inventoried, not validated or transported. No writer, edited-child rebase,
native interpretation, CLI/default change or model adoption. Complete original
annotation/path coverage must be bound before materialization; use Cedar's
deposition-link owner against a complete reference rather than infer completeness
from a standalone check or unchanged scattering.

**Validation:** 217 focused source and 217 relocated installed checks; synthetic
permutation, isotropic forest, exact original precision, symmetry contradiction,
missing/extra source data and relocation/race cases. Initial collection fails on
the absent new API, not on an existing behavior regression. Python 3.10 syntax,
installed cut-preview help and 206 relocated installation-file hashes pass after
build/original installation path removal. An initial offline install lacked the
already-available build dependency path; adding that path qualified the same
source, with the failure retained. No native execution was repeated. The complete Willow suite ran: 2,688 passed, four skipped and 234 subtests passed; five campaign-process tests failed because sandbox process inspection/signaling was denied. Those same five passed with permission (2.48 s), unchanged source. This clears all 2,693 tests across the run and retry, not a single clean full invocation or a combined-branch integration result.
See W256 in the periodic ledger for the four real-source replays and remaining
scientific gates. Existing calls and artifact schemas need no migration.

### Project declared paths onto original CIF sites (W257)

`topostitch_cif_source.observe_relabel_cif_paths(directory, model, **source_binding)`
accepts the same explicit controls as W256 and returns a read-only schema-1
`topostitch-original-cif-declared-path-projection`. It invokes the existing source
loader, then partitions only the exact saved graph's `covalent_backbone` edges.
Identity-image edges form deterministic directed paths; nonidentity edges remain
explicit boundaries. Base-pairing and other graph edges retain their IDs separately.
No edge is created from coordinates, distance, sequence or base identity.

Every registered node must have resolved complete atom coverage and exactly one
original `label_asym_id` / positive `label_seq_id` / `label_entity_id` /
`label_comp_id` site. Each numeric chain/sequence position belongs to one whole
node, even when competing components have different names. Missing labels,
partial sites, aliasing, competing incoming/outgoing covalent edges and uncut
identity cycles refuse with a reason. Periodic cycles remain representable when
their nonidentity edge stays explicit; an isolated node does not acquire a bond.

`paths` lists node order and ordinary edge IDs; `boundary_edges` keeps exact
target operators and both proposed path positions. `registered_original_sites`
binds those nodes to original labels/atom IDs and protected/do-not-connect flags.
`declared_routes` preserves original chemical/representation/unknown boundary
intent; outside-route node IDs and the `unregistered_original_atom_ids` list
remain visible. The report pins the original context, receipt, registered graph and
representative graph. Source bytes are checked again after projection; relocation
with the old input path gone reproduces the report.

**These are graph path numbers, not new CIF chain/entity assignments.** Complete
registered-node coverage does not establish complete original polymer coverage,
entity/sequence correctness or the coverage of original `struct_conn` rows. The
reader does not classify unregistered atoms as solvent, name chemical termini,
validate chemistry, write coordinates/annotations or authorize native refinement.
Cedar remains the semantic sequence/backbone declaration owner; its covalent
reader intentionally does not cover every other connection type. Original
noncovalent annotation transport is the next separate source-bound layer.

121 focused source and 121 relocated installed checks pass; the complete Willow
suite passes 2,705 tests, four skips and 234 subtests. Hazel's independent review exposed and verified the missing-entity collision
fix: occupancy of a known label position is now indexed independently of full
entity labels. The regression fails before the fix and passes afterward. Final
source and installed bytes match exactly; installed imports/help also pass. 206 installation
files hash-match after temporary build/old installation path removal. Initial
absent-API and prototype position-collision failures remain recorded; no native
run occurred. Existing source-reader calls and saved-preview schemas are unchanged.

## Preserve original connection endpoints through a recut (W258)

`topostitch_cif_annotations.observe_relabel_cif_connections(directory, model,
expected_image_owner_sha256=..., cedar_source=..., **source_binding)` observes
all original `_struct_conn` rows against W256's original byte/atom context and
W257's complete registered-site projection. `source_binding` is exactly the
explicit receipt/model hashes, aliases and working-precision controls required
by `load_relabel_cif_source`. `cedar_source` is an explicitly selected trusted
source directory containing `nasolve`; omit it only with a compatible installed
Cedar owner. No checkout is searched automatically. Pin
`nasolve/cif_deposition_links.py` with `expected_image_owner_sha256`.

Cedar's `resolve_deposition_image` resolves the file's declared operation IDs and
cell shifts. The isolated existing owner loader is reused and its source hash is
checked before/after. This does not call Phenix. The qualified current owner is
Cedar `51be01f48327c187ac2015e328c1c61adb46891a`, decoder SHA-256
`931af21688c15a29c99b605b4d442afc908df91d48a1825c19dc68eae81e4204`.
Earlier Willow-only installations without that compatible owner require the
explicit developer source argument; this is not a combined-branch release.

Every supplied label/author identity field constrains matching. Ambiguous or
missing atoms, inconsistent IDs, absent/unknown symmetry codes, conflicting
operation tables and third partners stay unresolved with reasons and the complete
raw row. Explicit CIF blank (`.`) differs from unknown (`?`) or an absent field.
A polymer endpoint with a known source sequence position needs an explicit label
or author residue number. Unregistered context stays at its existing image.
Unknown connection kinds may retain resolved endpoints without acquiring chemical
meaning. Duplicate connection IDs retain both numbered rows and block a fully
resolved result. An absent table does not certify absent or complete connectivity.

For source endpoint `g(x)` and new representative `y = h(x)`, observe the new image
`g h^-1(y)` using the existing exact operator owners. Both absolute physical
endpoints, their numerical errors and connection distance are recorded; unchanged
distance alone cannot hide an incorrect common translation. Original atom IDs,
raw fields and proposed path positions remain visible. The JSON observation is
schema 1, `topostitch-original-cif-connection-transport`; it contains source,
preview, path and decoder hashes and no operational absolute paths. Full original
lexical bytes remain in the pinned W256 source context.

This is **not a writer**: it does not choose output chain/entity names, add missing
graph edges as annotations, validate connection chemistry, alter sequence/termini,
interpret native restraints or authorize a changed model. These are separate P03
and Cedar gates. [The wwPDB category definition](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/struct_conn.html)
covers different connection types, which is why the reader does not filter to
O3′–P covalent bonds.

## Account for declared polymer positions and original coordinates (W259)

`topostitch_cif_polymer.observe_relabel_cif_polymer(directory, model,
expected_deposition_owner_sha256=..., cedar_source=..., **source_binding)` adds
read-only polymer coverage to the W256 original-source/W257 path binding. The
source arguments retain their explicit hashes, aliases and precision controls.
The trusted Cedar source is selected explicitly, using the same isolated,
SHA-pinned owner loader as W258. Its public `inspect_deposition_links` supplies
sequence-table checks, conflicts and unlabelled polymer-atom counts. The whole
Cedar geometry status is not sequence approval; an unchanged-label processed-file
comparison is not used for recut labels. No Phenix/Coot process is launched.

The observer retains raw `_entity`, `_entity_poly`, `_struct_asym`,
`_entity_poly_seq` and `_pdbx_poly_seq_scheme` tables, including original component
spellings, author identifiers and nonstandard-linkage flags. It joins declarations
without filling absent fields or replacing conflicting rows. Every original atom
belongs exactly once to a known polymer, known nonpolymer or unresolved group;
unregistered polymer atoms remain visible. Declared sequence positions are
expanded separately for each original asym element, even when several elements
share one entity. Legitimate alternative monomers at one position are retained.

Each declared position is `OBSERVED`, `UNMODELED` or `UNRESOLVED`. Conflicting
atom labels cannot make existing coordinates appear absent. An unresolved atom
only casts uncertainty over positions compatible with its known identifiers;
a uniquely identified water with a missing chain does not erase evidence of an
unmodeled DNA residue. Missing declarations, duplicate identifiers/monomers,
numbering gaps, contradictory entity assignments and incomplete coverage remain
review reasons. No missing residue is generated or assigned to a recut segment.

The schema-1 `topostitch-original-cif-polymer-coverage` observation retains source,
receipt, path-projection, owner and report hashes. Its overall status stays
`OBSERVED_REVIEW_REQUIRED`. `metadata_coverage_status=CONSISTENT_DECLARATIONS`
means these supplied tables agree with observed coverage and Cedar's separate
sequence-table evidence. It does not certify the biological sequence, chemical
connectivity or a deposition-ready model. Missing any of the five scoped tables
returns `UNAVAILABLE`; this is this observer's coverage requirement, not a claim
that every general CIF must contain those tables.

**Unvalidated semantics stay explicit:** original author numbering and canonical
one-letter sequence text are preserved, not checked or rewritten. In particular,
[scheme author numbering](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_pdbx_poly_seq_scheme.auth_seq_num.html)
need not equal coordinate residue numbering. The
[sequence definition](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/entity_poly_seq.html)
permits alternative monomers at a position, and
[asym elements](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/struct_asym.html)
may share an entity. A geometric cut must not automatically invent a chemical nick,
new chemical entity or `nstd_linkage=no`. No writer, output labels, new annotations,
restraints, coordinate changes, ordinary-workflow activation or migration is added.

## Compare original literal and canonical sequence text (W260)

`topostitch_cif_polymer.observe_relabel_cif_sequence_text(directory, model,
**polymer_binding)` composes W259 with the exact original document and the shared
`sequence_syntax.parse_sequence_tokens` owner. `polymer_binding` is the unchanged
explicit original/receipt/precision/Cedar-owner contract. The previous W259 API
and report remain unchanged. This optional observation writes no model or metadata.

Each original nucleic-acid entity retains its raw text and every declared position,
including positions without coordinates. Literal parenthetical CCD tokens compare
to the allowed monomers at each position; matching one alternative does not select
the chemical population. DNA target coercion is deliberately not used: deposited
bare `A` and `(DA)` are different literal components. Unsupported grammar (including
codes outside the shared tokenizer's 1–5-character syntax) remains unavailable.

Canonical comparison uses standard DA/DC/DG/DT and A/C/G/U identities, or an explicit
standard nucleotide parent in a source `_chem_comp` row, including attached blocks.
Missing columns, unknown, conflicting, nonstandard or multiple parents remain
unavailable. Explicit unquoted CIF `.` for an inapplicable parent permits `X`;
quoted `'.'` and `'?'` stay literal strings. No external CCD lookup, alias, residue
name or target mutation supplies a guessed parent. Standard-ID mapping does not
validate custom chemistry defined under a standard name.

A canonical string is compared only when every declared position has exactly one
supported letter, shared by all allowed alternatives. Multiple-parent components
can expand canonical text, so this scoped observer never indexes later residues
into such a string. The
[wwPDB canonical-text definition](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_entity_poly.pdbx_seq_one_letter_code_can.html)
and [literal-text definition](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_entity_poly.pdbx_seq_one_letter_code.html)
are the format references; these comparisons do not establish chemical truth.

The schema-1 `topostitch-original-cif-sequence-text` report preserves component
rows with block/row identity, per-position parent evidence, reasons, source/receipt/
coverage/owner hashes and a report digest. Per-entity literal/canonical outcomes
are `MATCH`, `CONFLICT` or `UNAVAILABLE`; aggregate `MATCHES_DECLARATIONS`, `PARTIAL`
or `REVIEW_REQUIRED` is separate from its permanent `OBSERVED_REVIEW_REQUIRED`
status. Original coverage conflicts cannot become approval. Author-number semantics,
output labels, chemical entities, unmodeled-position reassignment and a writer
remain unimplemented. No existing packet migration or ordinary default changes.

## Carry original identity through visible fragments (W261)

`topostitch_cif_fragments.observe_relabel_cif_fragments(directory, model,
**polymer_binding)` composes W259 with the saved graph/path and existing construct
registration. Every registered node retains original CIF atom/site/author identity,
registered copy/logical/coordinate site, declared route and proposed representative
operator. Path numbers remain preview identifiers; output chain/entity IDs are unset.
Every declared backbone edge retains both original and proposed image operations,
its declared origin, fragment boundary and original asym/entity/sequence transition.
A cross-entity or wrapped transition remains visible even when local in the new cut.

Optional `oligo_registration_path` and `expected_oligo_registration_sha256` accept
only an explicitly selected, exact-hash existing construct-registration document.
The existing validator owns its schema, uniqueness and partial-copy semantics;
actual identities are checked against the same saved working-model bytes. Target
order is retained as supplied, never sorted by author residue number. The target
reference is preserved, but its external content is not loaded in W261.

The saved ASU registration does not establish full synthesized-oligo identity.
Reusing its target reference returns `SOURCE_TARGET_REUSED`, including equivalent
JSON reserialization. A distinct supplied registration is `DECLARED_REGISTRATION_ONLY`
or `DECLARED_MAPPING_REVIEW_REQUIRED`. Rows carry neutral `declared_mapping` evidence;
`oligo_assignment` remains unset until a separately bound target-document check.
No supplied registration returns `SOURCE_LINEAGE_ONLY`. Target identity conflicts,
nonadjacent/wrapped sequence relations and missing mappings remain explicit.

Unmapped logical target positions are separate from original declared positions
without coordinates. Unregistered original polymers/nonpolymers and supplied
mappings outside the current fragment projection remain visible. Existing one-site
registration uniqueness is unchanged; repeated symmetry occurrences cannot be
manufactured by assigning one coordinate site to several logical residues.
The schema-1 `topostitch-original-cif-fragment-lineage` report binds original,
receipt, coverage, graph and optional registration hashes and checks frozen inputs
after observation. It performs no coordinate/sequence edit, entity assignment,
physical-copy/nick inference, assembly/TLS transformation or writer authorization.

## Bind a declared strand target document (W262)

The W261 fragment observer additionally accepts paired `oligo_target_path` and
`expected_oligo_target_sha256`. These require the explicit registration arguments.
The file must use the existing `sequence-family-target` schema. Its exact bytes
are frozen and hashed; duplicate JSON keys, drift and a mismatched digest fail.

The observer rebuilds the registration through `build_construct_registration`
using that target, the same working model, supplied copy maps and original source
text. Modified polymer roles come from W259 original CIF polymer coverage plus
its explicit component aliases, not the supplied registration. The rebuilt
registration must equal the supplied validated registration in full. Matching site
names with different mapped residue codes or a different target reference fail.

The report retains `target_document_sites` with every site/component, including
unmapped positions, and the target-document digest. A consistent, distinct target
returns `TARGET_DOCUMENT_BOUND`; its mapped rows populate `oligo_assignment` as
**caller-declared identity**, not verified physical placement. Missing coordinate
mappings, identity differences and nonadjacent/repeat relations still require
review. A partial copy stays partial even when all observed sites are mapped.
Known ASU-target reuse remains `SOURCE_TARGET_REUSED` with no oligo assignment,
even if the actual ASU target document rebuilds correctly.

`target_document_status=LOADED_REGISTRATION_MATCH` and
`explicit_target_document_verified` mean the document and mapping agree, including
a declared coordinate/target identity conflict. `target_reference_status=NOT_LOADED`
separately identifies the unverified external source cited by the target. It does
not certify the synthesized strand, sequence authenticity, physical copy/nick
phase, or a target reference file that was not loaded. The separate
`target_reference_content_loaded` and physical-acceptance flags remain false.
Codes for unmapped target positions come from the newly bound document; the old
registration alone could not validate them. Existing calls without a target file
produce exactly the W261 report, with no migration or new required input.
No source coordinates, chemical entities, assemblies, TLS or native controls change.

## Carry source sequence-reference ranges across a split (W263)

`topostitch_cif_fragments.observe_relabel_cif_reference_ranges(directory, model,
**fragment_binding)` composes the qualified fragment observer with the original
`_struct_ref`, `_struct_ref_seq`, `_struct_ref_seq_dif` and sequence-scheme tables.
Each projected segment retains its original alignment/reference/entity/asym IDs.
The source range uses [entity sequence positions](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_struct_ref_seq.seq_align_beg.html);
its [PDB strand locator](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_struct_ref_seq.pdbx_strand_id.html)
is resolved through the explicit scheme, without substituting author numbers.

Supported rows require a unique reference/strand, complete declared range and
registered fragment membership. Author-number qualification is separately limited
to consistent, numeric, forward, uninserted ranges. An explicit no-insertion
scheme can resolve an unreported atom insertion field; neither raw field is
rewritten. Unknown in both sources, inserted/reversed numbering, unmodeled or
unregistered positions and conflicting endpoints remain review cases. Missing
alignment tables mean unavailable. An invalid source may be refused by the
existing source/Gemmi reader before this observer; that boundary is unchanged.

Raw reference/discrepancy/depositor rows remain in the report, including orphan or
ambiguous alignment links. The original [discrepancy parent link](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_struct_ref_seq_dif.align_id.html)
is retained, not reassigned. Unmodeled coordinates and unknown author metadata
are distinct states. Source-range membership does not validate discrepancy details.

New chain/entity/alignment IDs and fragment database endpoints remain unset.
[Database endpoints](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_struct_ref_seq.db_align_beg.html)
refer to an external sequence; equal span lengths do not establish a gapless
per-residue correspondence. The schema-1 `topostitch-original-cif-reference-ranges`
report therefore qualifies source membership only. It binds the original bytes
and fragment report, preserves every original link slot and writes no CIF.

## Carry one declared TLS motion through a uniform image (W264)

`topostitch_cif_tls.observe_relabel_cif_tls(directory, model, **fragment_binding)`
reuses W261/W262 source/image binding. It retains the original TLS parameter and
group rows, resolves complete explicit label/author ranges, and aggregates range
fragments belonging to the same original TLS identifier. A matching **explicit**
refinement ID is required; two unknown identifiers cannot establish that link.
Unknown selection text needs an exact complete-range description. An explicitly
inapplicable selection is distinct from unknown. Other selection grammars,
missing/unregistered members, contradictory author bounds and overlaps require review.

For one proper crystal image shared by every member, the observer transports the
origin and T/L/S axes. `transport_tls_parameters` and `tls_u_cart` expose the pure
numerical operation and declared TLS field evaluation. T uses Å², L degree² and
S Å·degree; symmetric tensors have order 11,22,33,12,13,23 and S is row-major nine
components. All nine supplied S values and its trace survive. No trace correction,
parameter uncertainty propagation, total atom ADP update or refinement is performed.
The [TLS category](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/pdbx_refine_tls.html)
and [group fragments](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/pdbx_refine_tls_group.html)
remain distinct declarations.

A mixed-image group returns `MIXED_IMAGES_REVIEW`, with original parameters and
all per-image member IDs retained, but no transported group. It is not silently
split into independent refinable groups. Missing parameters or membership return
review; an absent TLS table is unavailable. The schema-1 transport report binds
the exact source/fragment report and keeps writer/native-refinement permission false.

**Convention limit:** cctbx's `zeroize_trace=True` overwrites S33, rather than
subtracting a scalar identity matrix from S. Independent Phenix 2.2.1-6174 checks
therefore use `zeroize_trace=False` for the supplied nine-component field and
measure the default's effect separately. The original 3LNA group 6 differs by up
to 2.46919 Å² in TLS U under that reinterpretation. This is not a coordinate or
total deposited ADP change, nor a claim that the source's refinement is invalid.
The tested R3 default-convention transport also stays near roundoff; source-field
reinterpretation and frame-transport covariance are different questions.

## Inspect original TLS groups in the ordinary recut viewer (W265)

The existing `nasolve-topostitch-view` command can optionally recompute the
original-CIF TLS observation for **one saved representative preview**. It does
not accept a previously generated TLS report as evidence. Give the original
coordinate CIF, a path-free JSON binding, and the explicitly trusted compatible
Cedar source until shared-owner integration:

```bash
nasolve-topostitch-view prepared-preview --out recut-inspection.html \
  --original-cif original-coordinates.cif --cif-binding source-binding.json \
  --cedar-source ../NASolve-c96/src
```

The JSON requires exactly these existing observer arguments: replace the three
hash placeholders with the expected SHA-256 values. The numerical bounds below
are an example for the known three-decimal working PDB, **not universal defaults**.
Aliases must be explicitly known; use `{}` when none are needed.

```json
{
  "expected_receipt_sha256": "<prepared preview.json SHA-256>",
  "expected_model_sha256": "<original coordinate CIF SHA-256>",
  "expected_deposition_owner_sha256": "<trusted cif_deposition_links.py SHA-256>",
  "component_aliases": {"A1C3T": "ACL"},
  "max_coordinate_component_error_angstrom": 0.000501,
  "max_u_component_error_angstrom_squared": 0.000051,
  "max_b_error_angstrom_squared": 0.0051,
  "max_occupancy_error": 0.0051
}
```

Paths remain explicit CLI arguments; no basename discovery, stored host-path
fallback or automatic component aliasing is introduced. Duplicate/unknown JSON
keys, missing bindings, mismatched inputs and a changed preview fail before output.
This option rejects bend previews and multi-cut comparisons. Ordinary calls are
unchanged. Python callers use `representative_scene` or `write_preview_view` with
`original_cif=...`, `cif_binding=...` and optional `cedar_source=...`.

The additive `original_cif_tls` field carries the exact schema-1 observer result.
The **Original TLS groups** panel shows original group IDs, member counts, each
crystal image and its exact original CIF atom IDs. Expand **Complete TLS evidence**
for parameters, range rows, issues and source/report hashes. Mixed groups visibly
remain under review; this UI does not turn image subsets into independent groups.
The scene's coordinates, atom inventory, graph and approval state are unchanged.
The generated HTML is standalone with no network requests. Input and installation
relocation were exercised using the installed command; browser visual rendering
was not verified because the browser tool refused the local file protocol.

## Observe original assembly images without rewriting them (W266)

`topostitch_cif_assembly.observe_relabel_cif_assemblies(directory, model,
max_rotation_component_error=..., max_translation_component_error_angstrom=...,
max_assembly_position_error_angstrom=..., **fragment_binding)` composes the
existing original-CIF/fragment binding with assembly-reference inspection. Supply
the same exact model/preview/owner hashes, explicit aliases, working precision
bounds and compatible Cedar owner as W265. The three additional assembly bounds
are explicit rounding allowances, not motion allowances. Supported upper limits
are 1e-5 per rotation component, 1e-3 Å per translation component and 0.01 Å per
source position. A translation allowance must also distinguish lattice images.
The actual LNA checks used 1e-8, 1e-6 Å and 1e-5 Å respectively.

Curated and depositor tables remain separate namespaces. Every raw assembly,
generator, operator and support category is retained. The observer resolves only
single unparenthesized operator IDs and explicit label-asym lists. Unknown,
duplicate, missing/unregistered membership, unsupported product expressions or
contradictory inline matrices remain visible review items. Unknown/inapplicable
CIF matrix fields cannot become numeric zero. Supporting assembly references are
observed separately; original oligomeric counts are never recalculated from cuts.

For a proper Cartesian matrix, numerical rotation/translation/position checks
against the declared space group determine its exact fractional-image match and
whole-cell shift. Original symmetry-table IDs are reported from those operations;
operator names and row numbers never choose the image. The **supplied matrix**
and its **exact matched operation**, with measured rounding differences, remain
separately inspectable. No matrix is silently snapped or normalized.

For each resolved generator, all observed atom IDs are partitioned by original
label-asym, proposed path and representative image G. The original Cartesian
operation H yields a proposed correction H G⁻¹. The observer verifies each raw
physical endpoint through this correction and retains its maximum error. Mixed
paths keep multiple partitions; no output asym/entity IDs are assigned. This is
an optional schema-1 observation, not an assembly writer, biological assembly
approval, total-ADP transport or proof of full finite-set equivalence. No existing
call, default, saved packet or shared Cedar owner changes.

## Inspect assembly references beside the saved cut (W267)

The existing `nasolve-topostitch-view` command can additionally recompute the
W266 assembly observation for one representative preview. Keep the same explicit
`--original-cif`, eight-key `--cif-binding` and compatible `--cedar-source` used
for original TLS inspection, and add `--assembly-bounds rounding.json`:

```json
{
  "max_rotation_component_error": 1e-8,
  "max_translation_component_error_angstrom": 1e-6,
  "max_assembly_position_error_angstrom": 1e-5
}
```

These are the declared matrix-rounding allowances used for the LNA controls,
not universal experimental tolerances. All three keys are required; null,
unknown keys, invalid values and missing original-source binding are refused
before output. The API equivalent is `assembly_bounds=...` on
`representative_scene` or `write_preview_view`. Numerical qualification remains
owned by the W266 observer. Saved reports are not accepted as trusted input.

The optional **Assembly images** section separates curated/depositor operators,
supplied Cartesian matrices, exact matched fractional images, whole-cell shifts
and rounding differences. Generator rows show source atom counts, image/asym
partitions and endpoint-transport error; complete evidence remains expandable.
The additive scene member is `original_cif_assemblies`. No original-CIF option
means the ordinary scene; omitting assembly bounds retains TLS-only behavior.

The 3D canvas still shows the saved ASU representative proposal, not an expanded
biological assembly. This is inspection, not an assembly editor, molecule-count
assignment, total-ADP/instance-equivalence proof or model writer. Multiple-cut and
bend views retain the existing original-CIF restriction. Paths stay explicit CLI
arguments; the scene contains source/report hashes, not operational host paths.

## Observe labelled assembly instances and deposited ADPs (W269)

`topostitch_cif_assembly.observe_relabel_cif_assembly_instances(directory, model,
max_instances=200_000, **assembly_binding)` recomputes W266's source-bound assembly
observation and the existing original-CIF `ReferenceFrame`. Supply the same exact
hashes, aliases, precision/assembly-rounding bounds and compatible Cedar source.
It accepts no saved assembly report as authority. The explicit integer instance
budget is 1–2,000,000; the default counts generator/atom occurrences across both
namespaces and refuses excessive expansion.

The optional schema-1 result retains the original assembly/source report hashes,
original scalar-field digest, curated/depositor namespaces and separate assembly
IDs. Each fully resolved assembly reports labelled occurrence counts, anisotropic/
isotropic instance counts, raw H G⁻¹ tensor-transport error and a separate raw-to-
exact tensor rounding difference. Original B/occupancy are scalar metadata;
absent anisotropic tensors remain absent. No TLS U is added or substituted.
Unsupported generators, unknown assembly references and missing declarations stay
explicit; a partially resolved assembly cannot report complete counts.

`unchanged_generator_exact_set_preserved` compares the finite multisets of exact
`(original atom ID, affine image)` keys before/after applying the original generator
set to the recut. Duplicate occurrences are retained, integer lattice shifts are
not wrapped, and missing/extra counts remain visible. A false result does not
invalidate the separately observed per-instance H G⁻¹ transport. A true result
does not establish physical atom uniqueness, biological validity, raw rounded
matrix equality, output reference semantics or writer authority.

This additive function does not alter W266 reports or the W267 viewer. Inputs are
rechecked after observation; no coordinates, atomic ADPs, labels, native settings
or checkpoints are written. Source tensor convention remains the existing bound
Cartesian-source contract, not a new generic CIF convention converter.


## Prepare a reviewed whole-asym CIF draft (W272)

`nasolve.topostitch_cif_output.prepare_whole_asym_cif(directory, model, *,
reviewed_categories, tls_policy, center_policy, **binding)` returns
`(document_bytes, receipt)` without writing or selecting a model. Use the exact
saved representative packet and original coordinate mmCIF, with the existing
source precision controls, explicit Cedar owner/hash and assembly-rounding bounds.
No extra oligo-target options or implicit source lookup are accepted by this route.

`reviewed_categories` maps **every original coordinate-block category** to the
existing `_fingerprint(_rows(block, category))` digest after reviewing its output
policy. The W271 source-specific category plan is one reviewed example. Missing,
extra or changed digests refuse; simply auto-generating those hashes does not
constitute semantic review. The caller owns the decision that all remaining
metadata can be retained unchanged. There is no universal dictionary classifier
or ordinary user-facing writer yet. Unknown frame-sensitive metadata requires a
new explicit policy, not a blanket safe-copy declaration.

The supported explicit policies are `tls_policy="preserve_raw_no_restart"` and
`center_policy="unit_occupancy_present_polymer_mass"`. One image must cover every
atom of each original label-asym and each complete declared TLS group. The draft
retains atom/chain/entity/sequence/copy labels, original scalar B/Q/charge and
ADP modes, all attached component definitions, and historical refinement values.
It re-expresses full-precision Cartesian XYZ/U and raw TLS parameters; no TLS U is
added to deposited total ADPs. Populated coordinate/TLS uncertainties, additional
fractional coordinate columns and anisotropic B columns are outside this scope.

Existing `_struct_conn` endpoints are encoded through the original symmetry
table and checked by the pinned Cedar decoder. Their metadata and type survive;
missing graph annotations are **not** inferred or silently created. The exact
preview remains the external declared-graph authority. Native seam chemistry and
complete in-file graph coverage remain later gates.

Original assembly operator IDs remain in their curated/depositor namespaces.
Derived raw **H G^-1** matrices receive collision-free IDs; generator rows are
partitioned by original-asym image, retaining each source occurrence. Keep an
original generator ID for its first partition and record all derived rows in
`assembly_generator_lineage`. Inline matrices, author-chain lists and identity/
all-chain flags are updated together. Conflicting supplied generator flags,
author-chain lists or symmetry text are refused before rewriting. Raw matrix rounding is not replaced by
exact symmetry. Unresolved operators/support/membership and helical metadata
refuse. The flag and chain-list semantics follow the
[wwPDB generator definitions](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Categories/pdbx_struct_assembly_gen_depositor_info.html).

If a polymer center is supplied, require complete present-polymer membership,
unit occupancy and a source center matching elemental-mass weighting to the
explicit implementation bound **5.01e-7 Å** per coordinate before recalculating.
Preserve absent/null centers and unchanged center text for an identity proposal.
Other center conventions remain unsupported. Scalar categories remain scalar;
growing generator categories become one loop without duplicate categories.
Every category is parsed back and compared with the proposed rows before return.

The additive schema-1 receipt binds source/preview/output, reviewed categories,
the existing owner reports, actual changed categories and assembly row lineage.
It reports the count of re-expressed deposited tensors. `file_written`,
`native_restart_qualified`, `all_declared_graph_links_written`,
`retention_semantics_independently_approved`, `scientific_acceptance` and
`runtime_authority` remain false. No existing schema/default/CLI is changed.

Qualification: **185 focused source / 185 relocated installed checks**, two
existing skips each; 218 installed files, exact actual 3LNA draft bytes/report
after package and staged-input relocation, Python 3.10 syntax and viewer entry
help. Five missing-API regressions failed before implementation. Four additional
metadata-refusal regressions fail on the exact pinned pre-guard implementation
and pass in the final source/installed suite. An inherited
fixture's contact labels had to follow its earlier polymer renumbering; that
initial refusal is retained separately from the passing qualification.

One exact 3LNA whole-A diagnostic re-expresses **327 of 1,271** deposited tensors.
Both serialized assembly namespaces retain **3,813** labelled occurrences;
maximum raw endpoint error **4.27e-14 Å**. Independent **Phenix 2.2.1-6174 /
Python 3.11.15** parsing retains labels/B/Q/elements/charge/ADP modes/multiplicity;
XYZ/U readback errors are **1.07e-14 Å / 3.55e-15 Å²**. Direct IT1992 calculated
scattering on **1,484** fixed prior indices differs relatively by **4.28e-15**.
This was complete read-only execution, not a dry-run or refinement. It does not
qualify TLS restart, native restraints, deposition acceptance or an adopted cut.
The original source is unchanged; diagnostics stay local under NASolve anchor
`branch-artifacts/willow/w272-whole-asym-draft/`. No full-suite repeat.


### Account for serialized backbone links through Cedar (W274)

`observe_whole_asym_cif_backbone` in `nasolve.topostitch_cif_output` compares a
saved declared graph with the **actual serialized CIF**, retaining original atom
IDs/site labels. It reuses the qualified source/path binding and Cedar's public
`inspect_deposition_links(..., include_ordinary_steps=True)` interface. No second
bond/image parser, chemical inference, output writer or restraint activation.

```python
from nasolve.topostitch_cif_output import observe_whole_asym_cif_backbone

coverage = observe_whole_asym_cif_backbone(
    preview_directory,
    original_cif,
    serialized_cif,
    expected_output_sha256=draft_receipt["output_sha256"],
    cedar_source=cedar_source_directory,
    expected_deposition_owner_sha256=reviewed_reader_sha256,
    **source_binding,
)
```

`source_binding` is the same seven original-source controls used by W256:
preview/model hashes, component aliases and explicit XYZ/U/B/occupancy precision
bounds. Do not pass the assembly bounds used by the separate draft API. Until
owner integration, pass an explicit compatible Cedar source and exact module
hash; an old aggregate-only reader is refused. Cedar C578 supplies this public
interface; the tested source revision and hash are in the current handoff.

The additive schema1 `topostitch-serialized-backbone-coverage` report lists each
declared edge, matched ordinary/explicit rows, image conflicts, unexpected links
between registered sites, sequence gaps and observations outside registered scope.
An ordinary adjacency across a declared nick cannot override that intent. Missing
or ambiguous endpoint labels stay unresolved; the consumer never picks a candidate.
Only one model with retained source labels and no registered alternate labels is
supported in this first scope. Changes to atom inventory/labels or any input during
inspection refuse. Reports contain hashes, not operational absolute input paths.

`status="COMPLETE"` means the declared backbone links are accounted for, not that
the structure is good. `LONG` and `PARTIAL_ANGLES` ordinary rows can establish
known connectivity while retaining Cedar's geometry review. `SEQUENCE_GAP`,
`UNMEASURED` and `ALTERNATE_LABEL_REVIEW` do not establish a covered bond. The
report explicitly leaves geometry acceptance, coordinate/scattering equivalence,
physical nick assignment and runtime authority false. No missing annotation is
invented, no coordinate is written, and W272's draft behavior remains unchanged.

The actual 3LNA whole-A draft accounts for 60 unique links through 58 ordinary
steps and nine explicit records (seven overlaps). Supplying the original CIF
against that proposed graph correctly flags the A–D image conflict. An immutable
save/replay wrapper remains the next boundary; a coverage report alone cannot
authorize native restart or a selected checkpoint.


### Save and replay an immutable whole-asym export (W275)

`write_whole_asym_cif` composes the reviewed draft and public backbone-coverage
owners into a **diagnostic export packet**. It requires the same explicit category,
TLS, center and source/assembly policies as W272, plus a compatible Cedar per-step
reader. Complete declared backbone coverage is required before publication.
No checkpoint, native job, force, physical nick or accepted structure is created.

```python
from hashlib import sha256
from pathlib import Path
from nasolve.topostitch_cif_output import (
    write_whole_asym_cif, load_whole_asym_cif,
)

receipt = write_whole_asym_cif(
    preview_directory, original_cif,
    output_directory=export_directory,
    cedar_source=cedar_source_directory,
    **reviewed_draft_options,
)
receipt_file = Path(export_directory) / "export.json"
replayed = load_whole_asym_cif(
    export_directory,
    expected_receipt_sha256=sha256(receipt_file.read_bytes()).hexdigest(),
    cedar_source=cedar_source_directory,
)
```

The destination's parent must exist. The destination itself must be new; an
existing directory or symlink is refused. Nine hash/size-bound artifacts retain
the original CIF, the five-file source preview, `representative.cif`, `draft.json`
and `coverage.json`. `export.json` is the last file written and marks a complete
packet. As with existing preview packets, interrupted partial directories remain
inspectable and are not overwritten or silently cleaned up. This is receipt-last
completion, not a claim of an atomic filesystem transaction.
W276 publishes the completed canonical receipt through a same-directory temporary
file, flush/fsync and a no-clobber hard link, following the existing campaign
publication pattern. A competing completion marker is never replaced. A failed
pre-publication write leaves the packet partial; temporary receipt files are
cleaned up after handled failures. No multi-file power-loss durability is claimed:
all artifacts and the caller-supplied trusted receipt digest still need validation.
The same receipt schema/bytes and old packet loading remain supported. Filesystems
without hard-link support refuse publication; there is no non-atomic fallback.

The example above hashes a newly created local packet for immediate replay. An
automated consumer must instead receive its expected file digest from the trusted
producer/handoff; hashing an arbitrary incoming file is not admission. W277
now supplies the explicit producer-to-consumer command handoff; W278 consumes it
in the existing inspector.

Every operational artifact reference uses the existing `run` anchor and exact
relative path. There is no basename search or dependency on the original input
directory. Cedar is an explicit, hash-bound software dependency supplied at replay;
its host path is not stored as an operational reference. Source inputs are frozen
before preparation and checked for drift before and during publication.

Loading validates the caller's **file SHA-256** for `export.json` (distinct from
the receipt's internal `report_sha256`), all file hashes/sizes and exact local
references. It then regenerates the CIF and both reports from the captured inputs.
Rehashing a damaged derived CIF cannot make it pass. Unknown changes or incompatible
algorithm/owner behavior refuse rather than silently migrate a saved packet.

The additive schema1 `topostitch-whole-asym-cif-export` remains
`EXPORTED_REVIEW_REQUIRED`. Known long links can remain covered while their
geometry is flagged for review. Native TLS restart, full mixed-path cuts, chemical
nick assignment and ordinary checkpoint/GUI integration remain separate gates.
The actual supported 3LNA export reproduces W272's native-tested coordinate bytes;
this does not constitute a new refinement or a general native-restart approval.


## Export and replay through the cut-preview command (W277)

Legacy preview construction and `--describe-graph` retain their behavior. The
same installed command now offers explicit whole-asym export and read-only replay:

```bash
nasolve-topostitch-cut-preview original.cif --export-preview saved-preview \
  --export-options reviewed-options.json --cedar-source /path/to/cedar/src \
  --out new-export
nasolve-topostitch-cut-preview --replay-export new-export \
  --expected-export-sha256 DIGEST_FROM_PRODUCER --cedar-source /path/to/cedar/src
```

`reviewed-options.json` contains the exact W272 draft keywords (source/preview/
owner hashes, component aliases, precision and assembly bounds, category review,
TLS and center policies). It contains no input/output paths. The existing draft
owner rejects missing/extra fields; the CLI neither chooses policies nor guesses
chemistry. Export/replay cannot be mixed with discovery, registration, proposal or
graph-description arguments. Existing destinations remain protected.

Successful export prints a schema-1 `topostitch-whole-asym-export-handoff` JSON
object with run-relative receipt/model references, byte sizes and SHA-256 values.
The receipt file digest is computed from the trusted producer's canonical return
and checked against the written file before printing. Save that trusted handoff
and supply `receipt.sha256` to replay; do not generate a new expected hash from an
untrusted incoming file. References are relative to the explicitly chosen export
directory, not a global filesystem search. Replay validates and regenerates the
packet through the existing loader and prints the same bound references.

This additive stdout contract is not a new coordinate/receipt schema or a
checkpoint registry entry. A handoff remains review-required, unselected and not
native-restart-qualified. W278 adds explicit inspector consumption; no automated inspection, refinement,
selection or native execution starts.


## Inspect a verified saved export (W278)

```bash
nasolve-topostitch-view new-export --export-sha256 DIGEST_FROM_PRODUCER \
  --cedar-source /path/to/cedar/src --out export-view.html
```

The same viewer verifies and regenerates the packet through the export owner
before rendering its captured representative preview. Supply the trusted
`receipt.sha256` from the W277 handoff. Export mode refuses comparison/native/
external-CIF/bend options; its source is the packet itself. Output must be new and
outside the frozen packet. Every artifact is checked again after scene assembly.

The page says **Saved CIF verified · Needs review** and explicitly identifies
its drawing as saved **working-preview coordinates and labels**. The full-precision
CIF is verified separately, not substituted into the drawing. Original component
aliases and working-coordinate precision therefore keep their original scope.
The ordinary inspector's atom/image controls and backbone-intent display are
reused; provenance includes the exact exported-CIF and receipt hashes. No model
selection, chemistry edit, new refinement, native restart or acceptance occurs.

The optional `verified_export` scene field is additive; legacy preview/viewer
paths and frozen export receipt formats are unchanged. The Python equivalent is
`write_export_view(directory, output_path, expected_receipt_sha256=..., cedar_source=...)`.


## Native restart readiness after export (W279 audit)

**Read-only audit, 2026-11-25; no new native initialization, fit or checkpoint.**
W278 completes diagnostic export inspection, not admission to refinement. The
same pinned 3LNA original and whole-A export each contain **1,271 atom rows,
1,271 anisotropic rows, six `_pdbx_refine_tls` rows marked `refined` and six TLS
groups**. `_refine.pdbx_TLS_residual_ADP_flag` is null. The legacy
`_refine_ls_tls` categories are absent; looking only there would miss the TLS
metadata. Local inventory records both spellings and preserves the initial
incomplete-category inventory separately.

The existing native control confirms the as-deposited per-atom scattering state
and correct coordinate/U transport. Metadata presence and a null residual flag
cannot establish how a new native job should decompose or refine ADPs. Preserve
the deposited U values; do not add TLS U, silently drop TLS metadata, zeroize raw
S or split a shared group as a restart shortcut. W264's actual R3 controls and
W271's separate nonzero-trace counterexample remain the relevant evidence.

| Contract | What the export carries | Remaining native/ordinary requirement |
| --- | --- | --- |
| Identity and periodic graph | Original atoms/labels, source mappings, all 60 declared backbone edges and image relations | Actual native chemistry, force/exclusion and complete term inventory; C578 coverage alone is not force admission. |
| Frame and ADPs | Explicit proper image transforms, preserved deposited tensors and raw TLS policy | Demonstrate the chosen native strategy consumes the intended scattering state. `preserve_raw_no_restart` remains literal. |
| C566/C567 preparation and child | Source CIF/preview, diagnostic reports and exact packet hashes | Genuine construction/parent, original observation/Free-R identity, ordered recipe/dictionary/native input bindings and receiving-child proof. None are created by this export packet. |
| C568 continuation inheritance | Declared physical links survive the recut | Current inherited-continuation owner parses PDB endpoint columns and checks the same closest representatives. It does not admit an arbitrary full-precision CIF recut by treating it as a small coordinate descendant. |
| Manual import | Existing checkpoint owner can retain a REVIEW child | Its `compatibility.validated=False` is not native recut/thermal approval; do not use import to bypass source or frame admission. |

The declared `paper_r3:3LNA/` dataset contains the original coordinate CIF,
`9Z65_structure_factors.cif` and a display script. The reflection CIF is present
(SHA-256 `f425e28e3996fb071ca561b228eeca44c6b63f621b8a3e4f59fd1b9a4c6f1ac0`).
Its `r9z65sf` block has 2,637 reflection rows, including 1,418 `o` and 66 `f`
status rows, and 1,153 null-status rows; separate STARANISO and AIMLESS blocks
also exist. Presence of these columns is not a qualified data selection or proof
of the original Free-R interpretation. No conversion or native job ran.
There is no numbered run report/registry in this declared three-file folder or
the saved export. This is a bounded inventory, not a search for or claim about
possible parent runs elsewhere. The local `context-inventory.json` records exact
anchor-relative inputs, hashes, columns and counts.

Rowan confirmed that the 3LNA repair was a separate Phenix experiment; no
verified ordinary NASolve checkpoint for this exact recut is known to the owner.
Keep 3LNA diagnostic. The genuine numbered PDU lineage already exercised by
C560/C579 is the next candidate for an existing-owner readiness check, without
converting its observations, changing its chemistry or inventing a 3LNA parent.

**Smallest next integration:** join one genuine original-parent observation/Free-R
and ordered restraint context to the exact exported-source identity through
existing Pine/Cedar owners. Record absent bindings as unavailable; do not invent
Coot/ReadySet or AutoMR ancestry. Qualify an explicitly fixed deposited-ADP,
no-active-TLS native input policy before motion; the presence of an `adp_mode=none`
option is not that proof. Prefer the existing qualified **source computational
frame** for execution and exact mapped return before a general dispersed-frame
restart. A fresh interpretation must prove identity, occupancy, U, source terms
and any native input normalization in that declared scope. It need not fit the
model merely to demonstrate admission. Direct recut execution remains a separate
qualification if the existing owners cannot represent its file format or images.

Cedar sources consulted: completion queue C560/C563–C568 and C578;
`refinement_prepared_backbone`, `cif_prepared_backbone`,
`cif_phosphate_continuation`, `refinement_phosphate`, `cif_phosphate_restraints`,
`autorefine` and `checkpoints`. Exact inspected file hashes, model bindings and
limits are local under NASolve anchor
`branch-artifacts/willow/w279-restart-readiness/readiness.json`.
The sources were read, not merged or modified; neither this audit nor their PDU
qualification is a tested combined-branch 3LNA restart.


## Observe refined checkpoint inputs without a preview (W280)

A refined checkpoint has valid input history but is not an original PostMR
preparation. `inspect_checkpoint_inputs` in `nasolve.topostitch_checkpoint`
now observes a saved schema-2 parent independently of a bend preview:

```python
observed = inspect_checkpoint_inputs(
    run_directory,
    checkpoint="refine-003",
    expected_checkpoint_id="refine-003",
    expected_model_sha256=trusted_model_sha256,
    registry_reader=trusted_cedar_checkpoints.read_registry,
)
```

The application supplies the trusted Cedar reader; it is never imported from a
saved artifact. Cedar owns authentication of supported run history. Willow
checks that the returned registry equals the saved bytes and binds the exact
model, original observations, optional phases and ordered restraints through
existing anchored/checksummed resolvers. It reads twice and rejects changed
selection, metadata or input files. Supply `expected_context_sha256` on a later
call to refuse a rebound context. Explicit checkpoint selection does not change
the run's current model; omitted `checkpoint` must resolve to the expected ID.

The additive `topostitch-checkpoint-input-observation` report has no preview
receipt and grants no chemistry, motion, thermal, native restart, selection or
scientific authority. It does not infer Free-R semantics, convert observations
or replace a source-frame/recut mapping. Existing bend/preparation readers and
schemas remain unchanged, including refusal to treat a refined descendant as
an original checked preparation. Schema 3 and legacy migration are outside this
adapter's declared scope. Snapshot checks are not locks; dispatch must revalidate.

**Exact read-only control:** the owner-declared, already relocated PDU lineage
from Cedar C579 reopens at `refine-003`: 862 atoms, original observations and
seven ordered restraints. The saved current checkpoint stays `postmr`. Original
input bytes and modification times remain unchanged; no new fit or native
initialization ran. The written PDB has no ANISOU records or TLS remarks; this
inventory alone is not a thermal-policy qualification. C579's prior endpoint and
Python-version checks are reused, not claimed as newly run. The separate 3LNA
export remains diagnostic because it has no verified ordinary parent binding.

Validation: the new API was absent in five initial failing checks. Six final
cases cover preview-free relocation, owner failure/mismatch, rebound data/model,
input/selection drift and explicit scope refusal. The checkpoint, execution,
preparation and native-window files pass **173 source and 173 installed tests**.
The installed package is moved after deleting its build/original install paths;
fixture relocation removes original dataset paths. Exact installed source bytes
and Python 3.10 syntax are checked. No CLI entry or full suite was needed for this
isolated observer; no shared runtime or executor changed. Local commands,
readbacks and checksums are under NASolve anchor
`branch-artifacts/willow/w280-numbered-parent/`.


## Follow a registered graph into a refined model (W281)

Phenix may reorder atoms even when every chemical identity survives refinement.
`observe_registered_graph_descent` in `nasolve.topostitch_graph` follows the
original declared graph into a coordinate descendant using an explicit atom
identity bijection. It retains the original registration and discovery records,
reuses the source-bound graph reader, and takes the trusted Cedar
`closest_atom_images` function as an explicit application dependency.

The caller supplies the expected source-graph and descendant-model SHA-256
values, original source/discovery/registration files, unchanged continuation
intent, and an image-separation threshold covering both PDB rounding errors
(at least `2*sqrt(3)*0.001` Å). The same exact cell and space-group setting,
complete unique atom identities, record/element/charge and occupied status must
survive. Every atom must retain the unique nearest identity image. Missing or
ambiguous identities, changed images, unresolved nodes and input drift are
refused. Numeric occupancies, ADPs and coordinates may change in a refinement;
this observation does not assert unchanged scattering or good geometry.

The distinct `topostitch-registered-graph-descent` result includes the explicit
source-to-descendant atom-index mapping. Node indices and unregistered atom
indices refer to the descendant PDB order. Logical nodes, routes and periodic
edge operators stay unchanged. It is **not** a rehashed replacement registration
or a normal recut-preview input. Checkpoint/construction ancestry remains the
responsibility of the existing owners; `checkpoint_ancestry_verified` and all
runtime/chemistry/restart authority fields remain false in this geometric report.

**Genuine control, coordinated with Rowan:** Cedar's construction and registry
readers bind original PDU construction `c813a651…` to the already refined,
unselected `refine-003` model `69d3f118…`. All **862 atoms** correspond; **32**
change record position. The **42-node, 40-edge** graph retains 38 ordinary
backbone edges and two explicit symmetry continuations. Maximum same-atom
movement since construction is **2.8160 Å**; the smallest gap between the nearest
and second-nearest image is **0.72438 Å**, above Cedar's **0.003464 Å** rounding
margin. A temporary copy with one atom translated by a unit-cell vector is
refused. The original registration, models, observations and current `postmr`
selection remain untouched. No native initialization, new fit or parameter
change ran. This is a correspondence result on an existing refinement, not a new
bending result or physical validation of every declared edge.

The registry-declared model CIF also maps uniquely to all 862 PDB atoms. Its
largest literal differences are 0.0005000000000024 Å in a coordinate component,
0.00488 Å² in B and zero in occupancy, consistent with the written PDB precision.
That inventory identifies a possible future original-CIF source; it does not
replace the source-bound CIF loader or qualify an export.

Validation: eight tests fail before the observer exists; the final graph, recut,
scattering and checkpoint set passes **140 source and 140 relocated installed
checks**. The tests cover unique reordering, unregistered atom indices, missing/
duplicate identities, occupancy-status/frame changes, image ambiguity, exact
bindings and input drift. Controlled image-reader cases test the adapter; the
real PDU positive/refusal use Cedar's maintained enumerator. Installed source
bytes and Python 3.10 syntax match, and disposable installation/refusal copies
were removed. No shared mechanics changed and the full suite was not repeated.
Evidence and exact commands remain local under NASolve anchor
`branch-artifacts/willow/w281-source-graph-join/`.

**Next:** teach the existing recut-preview consumer to accept an explicitly
bound descent observation and its original provenance, or keep the endpoint
held. Do not silently edit registration hashes, infer replacement chemistry or
reuse an earlier native capture as if it described the final endpoint.


## Ordinary recut preview of an attested descendant (W282)

W282 uses the W280 input binding and W281 atom/image correspondence to create
one ordinary preview through existing Pine owners. `build_construct_registration`
rebuilds a **separate** registration from the current `ModelAssessment` and the
exact original logical target and mappings. Its source label includes the W281
descent digest. Target, copy mappings, identity relations and semantics remain
identical; the old registration is never overwritten. Discovery is bound to this
new record, then the ordinary preview builder, replay and viewer run unchanged.
This is an explicit local producer experiment, not an automatic descendant
registration API or a new artifact schema.

The selected image for all seven C-chain residues is `-x+y,-x,z`, making the
existing D:7→C:8 continuation an identity-image edge. The 144 affected atoms move
only between equivalent crystal representatives; the largest displayed change
is 74.40 Å and is **not a physical bend**.

| Connection | Direct display gap before → after | Physical image bond before → after | Image after |
| --- | --- | --- | --- |
| D:7→C:8 | 32.0511 → 1.6347 Å | 1.6347 → 1.6347 Å | `x,y,z` |
| B:7→B:1 | 23.6836 → 23.6836 Å | 1.6700 → 1.6700 Å | `-y,x-y,z` |

All **40** declared O3′–P distances and **160** angles are preserved: maximum
changes are 3.56×10⁻¹⁵ Å and 3.42×10⁻¹³°. At D:7→C:8, C3′–O3′–P,
O3′–P–O5′, O3′–P–OP1 and O3′–P–OP2 remain respectively 121.92277°,
104.60724°, 108.86487° and 109.97798°. The corresponding B-boundary angles
also remain unchanged. These are observed existing geometries, not newly
optimized targets. Pairing inventory is still incomplete; none is inferred.

The endpoint has genuine Cedar construction/ordinary history, preserved through
separate provenance. The standard preview itself grants no such ancestry or
native authority. The W281 shifted-image refusal remains relevant. An initial
literal comparison of node-index lists refused because the source-order mapping
and freshly built descendant lists enumerate the same atom membership differently;
the corrected comparison checks all node metadata and exact index membership.
It does not relax the unique atom bijection or assume equal array positions.

Local opening report and standard inspector are under NASolve anchor
`branch-artifacts/willow/w282-descendant-preview/README.md` and
`PDU-descendant-recut.html`. `result.json` and `geometry.json` carry pre/post
comparisons and exact upstream hashes. All original files and selected `postmr`
remain unchanged. No coordinate export, native initialization or refinement ran;
no new code/schema or installation changed. Existing focused/installed controls
were reused; no full suite or new browser-render qualification is claimed.


## Genuine descendant CIF export gaps (W283)

The W282 genuine-parent preview reaches a real input-format boundary. Its paired
Phenix CIF has complete atom/residue chain locators but all 862 atom rows lack
`label_entity_id`; `_struct_asym` contains only `id`, with no entity/polymer
sequence tables. The existing source-path observer and whole-asym exporter refuse
`Registered node 1 lacks one complete original CIF site label` before publication.
No export directory or coordinate file is created. This is an observed refusal,
not a completed native restart or a missing-CIF repair.

An independent raw-table/explicit Cedar decoder audit finds 49 `_struct_conn`
rows (38 `hydrog`, 11 `covale`) without either partner-symmetry column: 98 unknown
endpoint images. Connection rows also supply author component IDs missing from
`_atom_site`. Original labels, all rows and source bytes are retained. For example,
author C:8 is label C:1; that difference is not evidence of a sequence mutation.
The current strict reader remains unchanged.

A separate, **unapplied two-row proposal** binds C00048 and C00049 to the W281
registered graph, the authentic completed native phosphate witness and the final
geometry file. The native witness holds P fixed and transforms O3′; the graph
holds O3′ fixed and transforms P. The operators are inverses, so the bond is the
same periodic bond under a common change of representative. This is not an
assertion of identical absolute endpoint positions. Four missing author-component
fields are corroborated by the exact paired PDB with unique identities and the
previously measured serialization bound; the source CIF is not silently enriched.

| Row | Bond | Proposed recut codes, P / O3′ | Full-precision CIF distance |
| --- | --- | --- | --- |
| C00048 | B:7 O3′ → B:1 P | `2_555` / `1_555` | 1.670058 Å |
| C00049 | D:7 O3′ → C:8 P | `1_555` / `1_555` | 1.634283 Å |

Codes refer to this source's explicit operation table. Both proposed endpoint
transports agree within 1e-12 Å. The other 47 rows remain unresolved, as do entity
metadata and complete pairing. Small differences from W282's distances reflect
CIF versus rounded PDB precision, not another fit. No model, restraint, source
registration or selected `postmr` was changed.

Evidence lives under NASolve anchor
`branch-artifacts/willow/w283-descendant-cif-export/`: `result.json`,
`two-phosphate-proposal.json`, exact commands in `validation.json`, and an opening
`README.md`. The ledger hashes the scripts, positive observations and preserved
refusal logs. These local experimental files are excluded from Git. This is a
read-only actual-source experiment; no new product behavior/schema, installation,
full-suite or native execution was introduced. Historical Phenix 2.2.1-6174
complete-run evidence was reread. Cedar's changed reader at
`49bdd664471a278296a8da0b8419cf55f39bd581` was reviewed and explicitly repinned;
its symmetry decoder is unchanged. Source-owner pin refusal is retained.

Next, specify an explicit metadata-repair boundary with Rowan: author-component
fields need exact companion-model evidence; entity/sequence assignment needs a
real construct definition; every remaining connection needs its own native or
other declared image evidence. Keep a proposal separate from an applied derivative.
Do not default absent images to identity, fabricate full oligos, drop unhandled
rows, or weaken strict export admission. Once those inputs exist, reuse the current
export/coverage owners and recheck all 40 graph edges before native restart work.
The deferred fragmented-ASU/LNA/nonzero-f″ metal tests remain queued behind their
existing P03–P05/Alder prerequisites.


## Archived sequence and entity authority (W284)

Following W283, the actual archived reference/recipe were traced through the
existing loaders. The `w-metal-scaffold` content digest exactly matches the
original registration, and all four archived frame-sequence blocks match that
reference. The `5w6w` source/configuration hashes also match the saved recipe
intent, including explicit D:1 terminal phosphate permission.

The reference with the run's explicit A:12/B:4 PDU substitutions reproduces
**40/42** registered targets. At A:13 it predicts DT while the model has DC;
at B:3 it predicts DA while the model has DG. Both model identities already
occur in the original `C_G.pdb`, read at the exact report-declared location and
verified against its recorded digest. They persist through the checksum-bound
MR input, construction and refined endpoint. Construction changes exactly A:12
DC→PDU and B:4 DG→PDU. This establishes inherited model choices, not experimental
sequence confirmation or evidence that these sites need correction.

| Metadata | Supported evidence | Still unqualified |
| --- | --- | --- |
| Author labels / modeled components | Unique PDB/CIF correspondence and bound model lineage | Experimental sequence correctness |
| ASU target inventory | Exact sequence document, registration and explicit substitutions | Two inherited source choices require design review |
| Terminal phosphate | Exact recipe permission for D:1 | Unspecified ends and physical nick phase |
| Full oligos / entity membership | No sequence file/override in this run; no SEQRES in four inspected models | Physical oligo assignment across ASU fragments |
| Deposition template | No pointer in inspected report/construction/registration/recipe | No global absence claim or implicit external-template authority |
| Connection images | Two W283 graph/native proposals | Other 47 original rows |

The existing family reference describes labeled ASU sites. Its hash alone must
not promote four coordinate fragments into four complete synthesized oligos.
Before a complete metadata writer, review the inherited sequence choices and
supply actual physical-oligo/entity provenance. Missing image annotations need
separate evidence. Keep source files immutable and proposed repair distinct from
an applied derivative; retain strict exporter refusal in the meantime.

Local matrix, scripts, commands and opening report are under NASolve anchor
`branch-artifacts/willow/w284-metadata-authority/`. All inspected inputs and the
selected `postmr` remain unchanged. This documentation/evidence checkpoint adds
no executable behavior or artifact schema and runs no native calculation, new
installation or full suite. The current product remains W281. Local scientific
records stay outside Git; roadmap references retain hashes. The existing delayed
fragmented-ASU/LNA/nonzero-f″ metal gates are unchanged.


## Native connection images versus chemical types (W285)

The remaining source-image question now has bounded native evidence. Cedar's
existing `refinement_link_geometry` reader parses all 1,007 printed bond rows
from the exact saved final geometry: 958 covalent-geometry, 38 Bond-like and
11 User-supplied. Each of the **49 original CIF connection rows** has exactly
one native atom-pair match. This establishes 47 explicit same-image pairs and
two symmetry-image phosphate pairs from the native report, rather than assuming
identity for absent CIF fields. Original atom-site author components absent in
the CIF are corroborated by the exact paired PDB, as in W283.

After the W282 whole-C recut, 34 matched relative images are identity and 15
are nonidentity. Physical endpoint transport agrees within 7.59e-15 Å, and
full-precision CIF distances agree with printed native distances within
0.000500 Å. This is native image evidence only; the original CIF is unchanged,
its image columns remain missing, and W283's two-row proposal remains unapplied.

**Chemical type is a separate gate.** Five rows tagged `covale` in the CIF
are inter-residue base-atom distance terms in the native User-supplied section:

| Row | Pair | Printed distance | Native target / width |
| --- | --- | --- | --- |
| C00019 | A:11 DT N3 — B:5 DA N1 | 1.911 Å | 2.800 / 0.200 Å |
| C00020 | A:11 DT O4 — B:5 DA N6 | 1.869 Å | 2.800 / 0.200 Å |
| C00023 | A:13 DC O2 — B:3 DG N2 | 1.943 Å | 2.800 / 0.200 Å |
| C00024 | A:13 DC N3 — B:3 DG N1 | 2.560 Å | 2.800 / 0.200 Å |
| C00025 | A:13 DC N4 — B:3 DG O6 | 3.088 Å | 2.800 / 0.200 Å |

These are retained strained contacts, not accepted geometry. A native distance
term does not establish a covalent chemical bond. The other six `covale` rows
are four PDU intramonomer terms and the two phosphate links. The 38 `hydrog`
rows have native Bond-like matches; complete pairing is still unqualified.
A future mmCIF writer must keep image evidence, chemical intent and observed
geometry distinct. Do not turn every native User-supplied distance restraint
into a chemical linkage or silently rewrite existing classifications.

**Cedar follow-up C585, evidence verified 2026-11-25.** Rowan compared native
hydrogen-bond settings with five explicit distance edits using identical
atom-specific targets and widths on the same PDU starting model. After five
cycles both gave the same 862 final atom positions **at written PDB precision**.
The native route wrote
`hydrog` for these five rows; the explicit-edit route wrote `covale`. All 7,924
initial nonbonded interactions, including their closest-approach distances,
matched. Thus this controlled comparison separates output classification from
coordinate behavior. It does not establish geometry acceptance, equality under
arbitrary restraint settings, or unchanged thermal/reflection outputs. These
are Cedar's results, not a Willow rerun. Willow verified the supplied archive
and result-member SHA-256 values and read the compact measurements: coordinate
RMS/max differences are zero at written precision; both fits report
R-work/R-free 0.2078/0.2693. The historical distances above remain their own result.
See [Cedar C585](https://github.com/vecchioni-lab/NASolve/blob/34724cca4d2b933a4f96779622eec45ed9d5fce5/docs/backbone-chemistry.md#how-phenix-labels-base-pair-restraints-in-the-pdu-scaffold).

The immutable local evidence is NASolve anchor
`branch-artifacts/cedar/c558-two-crystal-phosphates/C585 PDU pair restraints and deposition labels.zip`
(34,175 bytes; SHA-256
`9a310bb91c1c48c3188b088ea1e2a302ac0b0a26a1a4a5c00f1803f1852d9f7f`).
Its `measurements/five-cycle-returns.json` member has SHA-256
`b3a35a4ed4500beaa432a61c71d87b8fd19bee5a781f665bfa99d8692a37abe3`.
The starting-contact comparison is in `measurements/native-starting-tables.json`,
SHA-256 `186fc5467ffca11fd637869884a4f32a131c51ba868c4782634d5e2c10e0e914`.
The evidence reference is closed; full metadata repair remains gated.

The writer requirement is now more specific: recover the intended contact class
from qualified chemistry/intent evidence, rather than interpreting the supplied
restraint form or a `covale` output tag as proof of covalency. Keep the source
row/digest and its proposed reclassification auditable. No rewrite was applied.

The W284 experimental-sequence and physical-oligo/entity gates remain. Before
full export, qualify a source-bound metadata proposal with actual design evidence,
review the five base-contact classifications, and retain original row IDs/digests.
Only then apply a separate derivative and reuse existing export/coverage owners.
No new fit or deferred stress test is needed to resolve these metadata questions.

Local `accounting.json`, `audit.py`, commands and opening report are under
NASolve anchor `branch-artifacts/willow/w285-native-connection-images/`.
All inputs, selected `postmr` and original proposal bytes remain unchanged.
No product/schema, native execution, installation or full-suite repetition was
introduced. The existing Cedar parser SHA is
`37e5479771da9fcbe8b66b045f56dda573fc4fb212c096de50d5c6243b95f5cb`.
Historical Phenix 2.2.1-6174 complete-run evidence was reread; this is not a new
refinement. Scientific files stay local; the ledger retains their checksums.


## Review explicit connection-annotation proposals (W286)

`topostitch_cif_annotations.prepare_connection_annotation_proposal` turns explicit
caller declarations into a source-bound **unapplied review**, including when the
original CIF lacks entity metadata. It does not weaken the existing source-path
or export gates. There is no new CLI mode or automatic repair; current commands,
receipts, previews and output schemas remain compatible.

Supply the original coordinate CIF, its expected SHA-256, the explicitly pinned
Cedar image owner, and a list of changes. Each change names an existing connection
ID and its original canonical raw-row fingerprint. Only `conn_type_id` (`covale`
or `hydrog`) and `ptnr1_symmetry` / `ptnr2_symmetry` may be proposed. Identity,
sequence, entity, coordinate and other metadata fields are outside this boundary.
The source must have one coordinate block, unique connection IDs and an explicit
unambiguous operation table. All proposed image codes are decoded through the
existing trusted Cedar owner; no missing image defaults to identity.

Each field independently names its evidence IDs. The `evidence` argument maps
those IDs to explicit `path`/`sha256` dictionaries. The API reads and rechecks
those exact documents; it does not search for them, interpret their contents or
approve their scientific meaning. Missing/duplicate/unknown evidence IDs,
unused evidence, unchanged field edits, stale source/row/file hashes and late
source/evidence changes refuse. Caller change records are snapshotted before use.

A change has this shape (values shown are illustrative):

```python
{
    "connection_id": "C00019",
    "expected_row_sha256": original_row_digest,
    "fields": {"conn_type_id": "hydrog", "ptnr1_symmetry": "1_555"},
    "evidence": {"conn_type_id": ["chemistry"], "ptnr1_symmetry": ["images"]},
}
```

The additive version-1 report kind is `topostitch-connection-annotation-proposal`.
It retains every original row in source order, proposed fields, per-field evidence,
explicit missing-versus-null distinctions, source/evidence digests and decoded
proposed operators. Unreviewed rows and unknown original types stay unchanged.
The report's `report_sha256` is its canonical fingerprint, not a signature or
scientific approval. Evidence file locators are omitted from the report; original
raw annotation text remains intact. Replay requires the caller's exact inputs;
this is not a portable run/export packet or an application/approval record.
`applied`, `coordinates_written`, `evidence_semantics_validated`,
`endpoint_identity_validated`, `chemical_semantics_validated`,
`native_restart_qualified` and `runtime_authority` remain false.

The actual W285 case now produces 49 proposed rows: 98 explicitly evidenced
**source-frame** image fields, plus exactly the five C585-attested `covale`→`hydrog`
corrections. The proposal contains 43 `hydrog` and six `covale` rows. C585's actual
original NARestraints digest and the five exact atom-pair identities were checked
before declaring those corrections. These are not silently inferred by the API.
The four PDU intramonomer and two phosphate row types are retained. Source files,
selected `postmr` and W283's separate two-row recut proposal stay unchanged.
The strict source-path observer still refuses the original missing entity label.
No CIF, coordinates, native process or selected child is produced.

Validation: 15 fail-before cases; **71 focused source / 71 relocated installed**
checks over `test_topostitch_cif_annotations.py`, `test_topostitch_cif_paths.py`,
`test_topostitch_cif_output.py`, and `test_topostitch_cif_export.py`, using
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:<optional-dependencies> python -m pytest
-p no:cacheprovider -q` with those modules. The wheel was installed offline, moved,
and replayed after its original build/install paths were removed. Its Python
source hashes match the checkout; the real proposal replays exactly. Installation
staging was removed. Exact commands, source hashes, proposal and results are local
under NASolve anchor `branch-artifacts/willow/w286-annotation-proposal/`.
No full-suite or native repetition was requested for this additive read-only slice.
Local science remains outside Git.

Next review the proposal separately from application. W284's physical-oligo/entity
and experimental-sequence questions remain required for full metadata output;
C585's matched result does not establish geometry acceptance. A future application
boundary must reproduce this proposal against exact source/evidence, preserve
all unrelated categories, publish a separate derivative and maintain strict
export/native admission. It must not treat the proposal fingerprint as approval.


### Reopen a saved annotation proposal (W287)

`load_connection_annotation_proposal(proposal, model, *,
expected_proposal_sha256, expected_model_sha256, changes, evidence,
expected_image_owner_sha256, cedar_source=None)` reopens this existing report
without introducing an application or approval schema. Supply the trusted **raw
file SHA-256**, separately from the report's internal `report_sha256`, and the
same independently supplied original inputs used by the proposal builder.
No paths, requested edits or evidence authority are adopted from the saved report.

The loader uses the existing duplicate-key-rejecting JSON reader and proposal
builder. It compares canonical typed fingerprints, not Python dictionary equality:
`false` and `0` must remain different. Rehashed edits, changed input bindings,
nonfinite JSON and proposal-file changes during replay refuse. It returns the
same unapplied report; verification does not make its evidence scientifically valid.

Ten missing-loader regressions preceded the change. The same four focused CIF
modules pass **81 source / 81 relocated installed** checks; all 94 Python source
hashes match. The actual saved 49-row W286 proposal reopens exactly in each
installation, and a rehashed false-to-zero authority edit refuses. Original
sources/evidence and selected `postmr` remain unchanged. No new CIF, native run,
CLI option, schema migration or full-suite repeat. Exact validation commands and
local evidence use NASolve anchor `branch-artifacts/willow/w287-annotation-replay/`.
Installed-package relocation reused explicit scientific input anchors; this is
not a claim that the scientific run is independently portable.

This closes the saved-review reproduction substep. Before writing a separate
metadata derivative, distinguish explicit image/type edits from the unresolved
physical-oligo/entity and experimental-sequence decisions. Preserve all unrelated
categories, and keep chemistry, geometry, export and native admission independent.
