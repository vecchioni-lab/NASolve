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
