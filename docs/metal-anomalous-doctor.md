# Metal hypotheses and anomalous-scattering diagnostics

Status: **planned, not implemented**. Design expanded 2026-10-26. This contract
defines a bounded diagnostic workflow for metal identity, site count, occupancy
and cluster hypotheses. It complements the [restraint builder](metal-restraint-builder.md)
and the existing refinement Doctor; it is not a new Cedar/Pine integration gate.

## Purpose and experimental stages

The scientist defines plausible metal arrangements and NASolve executes and
records the comparison. The output is a set of traceable alternatives, including
an unresolved result when the data cannot discriminate them. A fitted f'' value
is a conditional scattering estimate, not an atom counter or a chemical verdict.

Keep these operations separate:

1. **Design:** create reusable donor/metal graphs and restraints without data.
2. **Bind and prepare:** bind the recipe to an explicit model/checkpoint; create
   a derived model only when requested. Audit dictionaries, chemistry, symmetry
   and effective restraints, then prepare each candidate geometry under the same
   declared protocol. Preserve each geometry endpoint and its limitations.
3. **Freeze and probe:** snapshot the chosen endpoint for each hypothesis;
   run independent fixed-occupancy f'' fits with fixed coordinates and ADPs.
4. **Compare:** inspect per-site response, maps, geometry, fitted parameters and
   alternative hypotheses through linked tables and model views.
5. **Continue:** explicitly select an eligible checkpoint or request a separate
   follow-up experiment. Browsing or sorting results never selects a checkpoint.

Different geometric hypotheses need their own preparation. Comparing their
frozen endpoints is distinct from a matched-coordinate identity substitution
control; record which experiment was performed. Final joint refinement, if
requested, creates another child and does not retroactively validate the scan.

## What occupancy and f'' can establish

For an isotropic atom its anomalous contribution contains the factor
`q * f''(lambda) * exp(-B*s^2)`, where `q` is occupancy and
`s = sin(theta)/lambda`. Spatial phases, the rest of the model and experimental
scaling also matter. This expression explains parameter coupling; it is not a
replacement refinement target or a universal inverse-response law.

At fixed coordinates and ADPs, changing q may be compensated by fitted f''.
Seeing f'' respond therefore helps diagnose whether the fit is active and
sensitive, but does not by itself establish occupancy, element or metal count.
Conversely, a weak or flat response can arise from poor signal, coupled sites,
incorrect selections, parameter bounds, scaling or nonconvergence; it does not
automatically establish a mixed metal. Keep those alternatives explicit.

Two complementary experiments answer different questions:

| Experiment | Fitted | Fixed | Interpretation |
| --- | --- | --- | --- |
| Occupancy profile | f'' for declared anomalous groups | XYZ, all ADPs, q, f' | Scattering required at each assumed occupancy |
| Element-conditioned occupancy | q under explicit constraints | XYZ, ADPs and reference f'/f'' | Occupancy conditional on that element/reference |
| B or geometry sensitivity | Only the declared extra parameters | All other controls | Dependence on the prepared geometry/ADPs |

Do not simultaneously free q, B and f'' and present their output as a uniquely
identified solution. Initial B choices and any neighborhood-derived B policy
remain recorded assumptions. A B sensitivity check is a separate experiment.
Use `occupancy`/`q` and `formal_charge` explicitly; a cluster charge Q is not q.

## Inputs and comparison groups

Freeze the source checkpoint/model, observations, original Free-R flags and test
value, symmetry, dictionaries, active restraints, source recipe and atom mapping.
Use declared anchors and checksums for operational references. Keep explicit
CLI paths available. No basename discovery or writable reference to a cache
may substitute for independent frozen inputs.

Require actual separate Friedel observations, their labels and uncertainties,
and a known wavelength for a wavelength-referenced diagnostic. Report anomalous
completeness, multiplicity and resolution support where available; overall
diffraction resolution does not prove equal anomalous resolution. Mean-only
data can support design/geometric work but cannot silently enter this scan.
Audit Free-R consistency under the existing rules without regenerating flags.

A comparison group shares observations, flags, resolution treatment, likelihood,
phase policy and nuisance-parameter policy. Keep excluded reflections and all
selection rules visible. An MR/SAD phase source generated under a competing
heavy-atom hypothesis can bias comparisons: use a common declared phase policy
and separately test phase dependence when appropriate. Never pool different
crystals or processing alternatives into one same-data rank.

Reference f'/f'' values carry element, exact wavelength/energy, table or scan
source/version, interpolation and calibration provenance. Atomic tabulations
near an absorption edge need not capture white-line or chemical-state effects.
A calibrated scan and a tabulation remain distinct reference options. No
universal Ag/Hg cutoff, tolerance of one electron, or target from a particular
paper becomes a default for Au, other energies or other experiments.

## Frozen diagnostic protocol

For each eligible geometry endpoint:

- Resolve explicit anomalous groups to exact atom identities, including altloc
  and symmetry. Check empty, overlapping and ambiguous selections. Keep other
  known anomalous atoms, such as iodine in modified bases, in the model with an
  explicit fixed or fitted policy. Do not merge distinct sites by element alone.
- Build each q-vector trial independently from that endpoint. Change q only in
  the new input. q=0 is an omitted-site control with f'' marked not identifiable,
  not a division-by-zero point on a fitted response curve.
- Disable XYZ, real-space, ADP/TLS and occupancy refinement, automatic atom
  addition/removal, coordinate corrections and other unintended model changes.
  Fix f' to the declared reference and fit only the requested f'' parameters.
- Freeze or explicitly profile bulk-solvent/overall scale and other nuisance
  terms with the same policy across a comparison. Audit automatic ADP rescaling
  too: absence of an ADP strategy alone does not demonstrate fixed output B.
- Record starting f'', bounds, cycles, stopping reason and sensitivity to
  declared alternate starts. Starting at zero is one reproducible protocol;
  preserve any failed zero-start attempt before trying another start.
- Read back effective parameters and actual output atom identities, coordinates,
  occupancies, ADPs and fixed scattering values. A violated freeze invalidates
  the diagnostic even if the process exits successfully. Report failures and
  partial evidence without promoting them to usable model checkpoints.

Validate the installed Phenix version with a dry run and then a complete native
control before claiming this protocol works. Native finite-precision and model
serialization tolerances must be justified and versioned, not silently widened.

## Hypotheses, mixtures and clusters

Support explicit one-, two- and three-metal base-pair hypotheses, mixed Ag/Au
assignments, two-versus-three Au arrangements, and a zero-metal control. A graph
of stable metal slots and edges extends the representation to larger clusters.
Cluster hypotheses can include metal-metal edges and donors from neighboring
residues, with explicit symmetry ownership. A polyhedral template proposes
geometry; it does not establish a cluster's existence or bonding.

Distinguish separate coexisting sites from mutually exclusive elements at one
physical site. For same-site alternatives the physical occupancy sum is at
most one (including a vacant state); distinct sites have separate budgets.
Special-position multiplicity and the native occupancy convention must be
resolved explicitly before applying that constraint to serialized atoms.
For a cluster, offer a shared occupancy only as an explicit intact-cluster
model; independent site occupancies describe a different disorder hypothesis.

Shared f'' groups reduce parameter count but impose equality. Per-site groups
allow different values but may be unidentifiable at limited resolution. Show
the grouping, fitted parameter count and sensitivity instead of quietly choosing
the grouping that gives the most favorable identity assignment.

Report these quantities separately:

- modeled site count and symmetry scope;
- expected occupied atom count, `sum(q_i)` over the declared physical sites;
- each fitted f'' and its element/wavelength reference;
- optional arithmetic sum of per-atom f'', clearly labeled and with group
  values expanded per atom exactly once;
- optional occupancy-weighted sum `sum(q_i*f''_i)` with identical site scope;
- resolution-dependent attenuation and actual modeled diffraction evidence.

These sums are bookkeeping summaries, not the measured total anomalous signal:
interference, B factors, symmetry and resolution remain in the structure-factor
calculation. Do not divide a cluster summary by one atomic f'' to infer a
unique count. If a source table does not define weighting or grouping, retain
that ambiguity rather than interpreting its number as a runtime target.

Close sites must also be assessed together. Use omitted-site controls and
residual/anomalous maps to examine whether adding a site changes the fitted
signal at neighboring sites. Keep atomic-species hypotheses, oxidation states,
cluster charge and protonation separate. Optical, chemical and computational
evidence may inform declared priors, but is not another diffraction observation
or automatic proof of atom count/charge.

## Bounded, scriptable experiments

Freeze a finite plan containing hypothesis IDs, occupancy vectors/grouping,
starts, controls, resources, parameter policies and maximum jobs/cycles/time.
Preview the exact job count before execution. Start with small declared grids
and allow an explicit bounded refinement of that grid; do not enumerate an
unbounded Cartesian product of every geometry, identity, occupancy and B value.

Each job has a stable ID, independent input/output directory and checksummed
parent. Resume validates completed jobs and preserves failed/interrupted attempts.
Share the planner, executor and report reader between CLI and GUI. Scheduling
must respect a total processor budget, including other active NASolve work.
The future Doctor may recommend a discriminating next experiment from diagnosed
limitations; it does not silently expand the search or choose a chemical model.

Use Rwork/Rfree as context and comparable diagnostics, not a repeated Rfree
optimization objective. Adding sites/parameters can improve fit without being
supported. Preserve the number and history of tried hypotheses and any held-out
validation strategy. Confidence intervals require an implemented statistical
procedure; starting-point spread is sensitivity, not a confidence interval.

Multiple wavelengths can help distinguish elements when suitably collected.
Bind each to its own observations, calibration, dose/order and sample identity.
Common geometry/occupancy must be a tested assumption, especially across
different crystals, reactions or radiation damage. Multi-dataset joint fitting
is a later explicit protocol, not implicit merging of independently refined rows.

## Tables, plots and GUI selection

Use an overview row per hypothesis/trial plus an expandable per-site table.
Include count, species assignments, geometry endpoint, q-vector, B policy,
f' policy, reference and refined f'', q*f'', resolution/wavelength, grouping,
fit metrics, local geometry, residual-map findings, convergence, freeze audit
and diagnostic status. Unavailable values remain unavailable, not zero.

Plot f'' versus q and q*f'' versus q for matched trials, with reference lines
and explicit fixed parameters. Multi-site vectors must be labeled; points from
different hypotheses or nuisance policies must not become one response curve.
Cluster summary rows expand to their per-site evidence. Keep rejected and failed
alternatives discoverable, with scientific uncertainty separate from execution
failure and from an unrun plan.

Every row resolves the exact model, maps, recipe and checkpoint/diagnostic
artifact. Selecting a row focuses the same sites in the molecular view and can
open the exact model/maps in Coot. Preview, pin, compare and select-as-current
are distinct actions. A diagnostic without an eligible checkpoint cannot be
selected as current. CSV/TSV and JSON exports retain IDs, units and provenance.

## Existing backend and implementation order

`autorefine.py` already exposes coordinate/ADP/occupancy strategy switches,
explicit anomalous groups, fdp-only mode, wavelength-derived references and
per-site diagnostics. These are foundations, not a qualified new workflow.
The current `RefineDoctor/ML-fdp-only` trial still has coordinate refinement and
group ADPs enabled by default. Its name means f'' rather than f' is fitted;
it does **not** mean all other atomic parameters are frozen.

Implement in bounded stages:

1. Recipe graph, atom-role binding and serialization with synthetic controls.
2. Interactive preview and restraint export, without launching refinement.
3. Explicit derived models and native restraint-consumption checks.
4. One complete, audited fixed-q/f'' control; then a small independent q grid.
5. Linked comparison tables and user selection, including unresolved controls.
6. Multiple identities/counts, mixtures and larger cluster qualification.

Core graph types should allow clusters now; native support is earned per tested
policy rather than implied by drawing additional nodes. Keep upstream CIF
acquisition and numerical-kernel work separate. No current CLI behavior,
checkpoint schema, scientific threshold or old report changes with this design.

## Validation cases and published precedents

Required future controls include: known single metal; no anomalous observations;
wrong/empty/overlapping selection; q=0; invariants deliberately violated; a weak
site; two nearby correlated sites; a third-site overfit; ambiguous mixed identity;
shared versus independent groups; charge-versus-occupancy labels; special-position
counting; missing wavelength; failed/restarted jobs; and relocation with original
paths removed. A complete native test must verify emitted restraints, all frozen
parameters and row-to-artifact linkage, not only subprocess completion.

Published precedents inform those tests, not universal acceptance thresholds:

- [Vecchioni et al., Advanced Materials 35, 2210938 (2023)](https://doi.org/10.1002/adma.202210938),
  supporting information, "Disambiguation of Metal Sites and f'' Refinement":
  staged B/reference/occupancy treatment and independent heavy-atom controls.
- [Lu et al., JACS (2023)](https://doi.org/10.1021/jacs.3c05478), supporting
  information, anomalous-group refinement and gold structure determination:
  occupancy sensitivity, close-site interference and single-wavelength ambiguity.
- [De et al., Small (2025)](https://doi.org/10.1002/smll.202411518), supporting
  information, heavy-atom identification, ambiguous sites and Tables S2-S3:
  time-series context, map evidence and retained ambiguity.
- [Liu et al., Matter 9, 102470 (2026)](https://doi.org/10.1016/j.matt.2025.102470):
  related metal-exchange experiments; independent samples remain distinct.
- [Phenix refinement reference](https://www.phenix-online.org/documentation/reference/refinement.html),
  f'/f'' refinement: explicit groups, starts, fixed f' and anomalous LLG maps.

The supplied private cluster manuscript remains outside Git. Its experimental
results, unpublished figures and numerical tables are not redistributed here.
Concrete native fixtures and recipe target/uncertainty values still require
selection; reading a paper is not a native qualification receipt.
