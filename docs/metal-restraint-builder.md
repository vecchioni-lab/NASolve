# Metal-coordination restraint builder

Status: **planned; not implemented**. User request recorded 2026-10-06.
This is a future metal-recipe authoring tool, not a Pine merge prerequisite.
Published examples and private cluster context have been supplied. The scope
now includes one-, two- and three-metal base pairs and an extensible cluster
graph. Numerical targets and uncertainties still require scientific review;
published structures do not automatically define reusable restraint defaults.

## Purpose and interaction

Provide a toggleable metal-restraint workspace in the NASolve GUI, with an
optional small standalone/detached companion window using the same backend.
It does not need the entire future GUI to exist before a bounded prototype.

Show clickable atom spheres, selectable metal sites/elements, existing molecular
bonds, and visible proposed coordination-restraint edges. Let the scientist pick
atoms, select one or more metals, add/remove distance and angle restraints,
name the hypothesis, and save/load/select a reusable recipe. Toggle the overlay
or the whole tool without changing the underlying model or selected checkpoint.

The lines represent proposed restraints, not an assertion that a covalent bond
has been created. Do not snap atoms to target distances, minimize coordinates,
change bond order, or launch refinement merely because an edge was drawn.
Measured geometry and requested target geometry should be displayed separately.
Ordinary Coot remains the coordinate editor; this tool authors constraints.

The molecular workspace uses a dark grey background, blue dotted proposed
restraint edges and blue selection highlights. Existing molecular bonds remain
visually distinct. Pair color with line style, labels and selection rings;
proposed interactions never inherit an accepted-checkpoint marker. Design,
Experiment and Compare are connected views of the same hypothesis and atom
identities, not independent copies of the model.

## Camera and interactive restraint sets

Provide a zoom slider, genuine three-dimensional rotation, pan/recenter and fit
controls. Camera transformations change only the view; stored coordinates,
restraint targets, atom identities and checkpoint selection remain unchanged.
Preserve depth for nonplanar six-site clusters and show surrounding nucleotides
or explicit symmetry mates when requested. A flat graph layout is not a geometry
model. The public [8VH6 deposition](https://www.rcsb.org/structure/8VH6) is a
useful spread-out three-Au viewing case; it is not a universal geometry target.

Make donor atoms as well as metal sites selectable. In an explicit add-restraint
mode, choosing two atoms creates an orange draft edge; a third selection can
define an angle. Display endpoint identities and let the scientist add, cancel
or remove the draft. Confirmed recipe proposals retain blue dotted styling.
Orange denotes a draft interaction, not bad chemistry; green retains its
accepted-checkpoint meaning. Use labels and distinct line styles with color.
Keep named restraint sets independently visible and editable, with targets,
uncertainties and sources attached to the set's individual constraints.

## Portable atom roles, not fixed PDB atom names

A reusable donor selector uses a logical residue slot plus a canonical atom-role
key from the NARestraints ligand workbook, such as `O4` or `N3`. The key is a
spreadsheet column/semantic site. It is not a requirement for the actual target
atom to have that literal name or element. Resolve it using the selected
residue's workbook record; retain the resolved atom name and element explicitly.

For illustration only (not a frozen file schema):

```
residue_slot_1.role(N3) -- metal_site_1 -- residue_slot_2.role(N3)
residue_slot_1.role(O4) -- metal_site_2 -- residue_slot_2.role(O4)
```

The concrete instance binds those slots to exact model/chain/residue/alternate
and, where relevant, symmetry identities. Never erase primes from C5' or conflate
an atom-role key, a chemical element, a PDB name, or a mutation intermediate.

Selecting an atom should suggest its corresponding role. If several roles map
to it, let the user choose. A concrete-only draft is still useful when no role
mapping exists; mark its narrower scope instead of inventing portability.
Missing or ambiguous donors prevent only application of the affected requested
restraint, not browsing, saving a draft, or unrelated campaign members.

A matching role makes a recipe addressable on another similarly shaped base;
it does not by itself prove identical metal affinity, protonation, oxidation
state, or suitable bond targets. Show actual donor elements and let the user
review the mapped instance. Do not add a new universal residue-classification
gate or revive the rejected N9 intermediate-mutation rule.

## Manually buildable hypotheses

Support named variants including square-planar coordination, N3-N3 or O4-O4
bridges, one, two or three metals, and homo-/heterometal arrangements. Distinct
metal slots carry separately selected species; do not assume sites are identical.
Keep a zero-metal/omitted-site control available for downstream comparison.
These labels may compose one hypothesis rather than being mutually exclusive.

Recipes describe explicit metal-donor distances and donor-metal-donor angles,
with units, targets and uncertainties. Metal-metal distances, planarity or other
constraints are included only when deliberately requested. A named geometry can
help enumerate a pattern; metal-specific numerical values must come from user
examples or an explicitly reviewed source, not be inferred from a drawn picture.
Keep which constraints are enabled visible, and permit editing their values.

Existing metal atoms can be selected. Draft metal placeholders can describe a
hypothesis, but adding actual atoms/species/coordinates must be a separate
explicit materialization action in a derived model, never a hidden side effect
of saving or previewing a restraint recipe.

## Cluster extension and chemical declarations

Represent a recipe as a graph of stable donor/metal slots and explicit
interactions, without a three-slot limit in the underlying representation.
Simple base-pair presets can cover one to three metals first. Larger clusters
use the same graph with optional metal-metal restraints and neighboring-residue
donors; each native geometry and disorder policy needs its own qualification.
Polyhedral templates are editable hypotheses, not inferred chemical bonds.

Keep modeled site count, symmetry multiplicity, occupancy and formal charge
separate. A shared cluster occupancy describes an intact-cluster hypothesis;
independent site occupancies describe another disorder model. Same-site element
alternatives have a shared physical occupancy budget, while spatially distinct
sites do not. The [anomalous diagnostic contract](metal-anomalous-doctor.md)
defines these comparisons and their identifiability limits.

Record source chemistry, protonation and oxidation-state assumptions without
silently rewriting component dictionaries. A restraint graph and an element
label alone do not establish those chemical properties.

## Local chemistry-aware target suggestions

Maintain a versioned local library of suggested metal-donor distances and
uncertainties. Use reviewed recipes/reference data and, where the exact chemical
context is supported, targets from the existing PostMR/CIF generation and
qualified dictionary store. Reuse its source/graph/producer/consumer provenance
through an adapter; do not fork the CIF chemistry engine. Ordinary component
bond numerics do not automatically qualify a metal-coordination target.

Match more than element pairs: metal identity and declared oxidation state,
donor element, donor bond-order environment, formal charge, explicit hydrogen
state/tautomer and applicable coordination geometry belong in the lookup.
C=S, C-SH, thiolate, -OH and -O-minus represent distinct stated contexts; do
not silently infer a protonation or redox change from pH or a drawn edge.
Offer a suggested target and uncertainty with its source, applicability and
qualification status. The scientist may edit either value, with the override
retained alongside the original suggestion. No matching supported source means
an unset target or an explicitly unreviewed draft, not an invented default.

Changing a declared donor state invalidates the prior match and offers a fresh
lookup. It does not mutate component bond orders, hydrogens, charge or fitted
coordinates. An actual chemical variant needs an explicit derived dictionary
and native qualification under the existing source-preserving workflow.
Keep measured model distances separate from restraint targets; a distance from
the same refinement is not an independent reference validating its own target.

Store user recipes and optional suggestions outside Git. Each applied recipe
freezes the exact library entry/version/hash, chemistry selector, target, sigma,
source and override into its run artifacts. Later library updates do not alter
past recipes or satisfy an old full-experiment reuse key. See the existing
[qualified dictionary store](cif-doctor.md#persistent-local-reuse-of-qualified-repairs)
for the reusable provenance and native-consumer boundary.

## Template, application, and refinement remain separate

A saved recipe retains its name/version, logical donor slots/roles, metal slots,
coordination pattern, target values/uncertainties, applicability notes and source
examples. Use a human-readable recipe representation; the serialization format,
final field names, and backend ownership are implementation decisions still open.
This document and the adjacent intent JSON are not a runtime recipe schema.

Each application freezes the recipe/version/hash, source checkpoint/model hash,
role-map source/version or fingerprint, resolved atom selections, explicit
instance overrides, and emitted restraint artifacts. Preview lists the resolved
atoms, donor elements, edges, angle triples and any unresolved selections.

Use one UI-independent restraint-building backend, reusing NARestraints atom-role
semantics and the existing NASolve/Phenix restraint pipeline. The docked and small
window modes must not have separate recipes, histories or scientific rules.

Refining several manually selected hypotheses creates distinct children from
explicit checkpoint sources. Preserve the original coordinates, observations,
Free-R and failed alternatives. Show each recipe and its results so the user can
select/reject a branch. Do not equate a lower Rfree or visual fit with proof of
metal identity/coordination. Automatic variant enumeration and campaign rescue
are later opt-ins, not requirements for the first authoring tool.

## First validation examples

Use the supplied scientific contexts to select explicit, reviewable fixtures.
Test the same recipe in both window modes; a literal N3/N3 case and an O4 role
whose actual target atom is renamed; reapplication to another compatible
modified base; save/load round-trip; one/two/three-metal and heterometal variants;
larger cluster graph round-trip without claiming native support; explicit
missing/ambiguous donor diagnostics; visible edges
and angle controls without any coordinate edit; and an emitted bundle interpreted
by Phenix in a fresh child run. Confirm that recipe toggling does not change
checkpoint selection or the original model, and that all resolved selections and
target uncertainties survive into the actual refinement command.

After authoring and geometry preparation, the separate
[anomalous workflow](metal-anomalous-doctor.md) runs bounded fixed-occupancy
f'' trials with audited XYZ/ADP/f' invariants. Tables bind exact trial/model/map
artifacts back to the same molecular sites. Inspecting a row or pinning a
comparison does not select a current checkpoint.

Metal anomalous evidence is separate from restraint authoring. Selecting a metal
or drawing an edge does not establish anomalous observations, phase quality,
occupancy or experimental support. Future application reports should expose
those facts without silently converting a geometric hypothesis into evidence.

See [GUI contract](gui.md), [GUI live checks](gui-live-checks.md), and the
[development handoff](development-handoff.md) for the current development order.
This design remains a separate later scope; it does not add a gate to the
combined geometry trial or Cedar/Pine close-out.
