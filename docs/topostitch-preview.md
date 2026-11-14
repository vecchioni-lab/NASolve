# Explicit TopoStitch bend previews

The `nasolve-topostitch-preview` command writes one new candidate from an explicit
window and terminal motion. It preserves the source model and fixed anchors.
This is a controlled trial generator: it does not find the best placement, close
an atomistic backbone, refine a model or recommend campaign adoption.

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

### Shared image-coordinate transport

`nasolve.topostitch_transport` owns the rigid Cartesian operation used by the
viewer and native image probe. `crystallographic_image(cell, group, operator)`
validates group membership (including a retained lattice shift) and compiles
`x_image = R_cart x_ASU + t_cart`. Its `CartesianImage` core also accepts explicit
finite proper Cartesian matrices without importing Gemmi or Phenix; those
matrices alone are numerical inputs, not proof of crystallographic membership.

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
