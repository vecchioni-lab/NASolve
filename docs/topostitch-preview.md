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
