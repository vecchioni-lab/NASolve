# Backbone chemistry in NASolve

Status: active contract. Terminal-phosphate construction, final-geometry
audit, targeted Doctor rescue, and the reusable proactive-protection primitive
are implemented and validated. Automatic invocation of proactive protection on
the first AutoRefine round remains the immediate runtime step.

## Goal

NASolve should automate ordinary phosphodiester chemistry aggressively while
remaining honest about backbone chemistries it does not understand. Residue
identity, base-pair/stacking geometry, backbone connectivity, and terminal
chemistry are treated as related but distinct concerns.

The automatic default is **standard phosphodiester**. A non-standard backbone
is never inferred from atom names, distances, residue codes, or a monomer
library entry. A user must explicitly mark the affected site.

## Standard phosphodiester contract

For ordinary DNA/RNA-like backbones, including sugar variants that retain the
same phosphodiester connection (for example LNA-style residues), NASolve applies
the standard contract:

- an internal nucleotide phosphate uses P, OP1 and OP2 and is connected to the
  previous residue through O3'-P;
- an internal phosphate must not retain terminal OP3/O3P;
- a requested 5'-terminal phosphate is a **complete terminal group**, not an
  OP3 exception: P, OP1, OP2 and OP3 are required;
- a requested 5'-terminal phosphate must not also have an incoming O3'-P link;
- ordinary 5'-OH termini are not given a phosphate unless the user or selected
  recipe explicitly requests one.

The existing historical `allow_op3_sites` field remains readable for old frozen
runs, but new user-facing configuration should use `five_prime_phosphate_sites`.
The chemistry request is a terminal-phosphate state; OP3 is only one atom in
that state.

## Building a requested 5'-terminal phosphate

When a site is explicitly declared as a 5'-terminal phosphate, PostMR runs an
`ensure` step before the ordinary phosphate sanitizer:

1. a complete P/OP1/OP2/OP3 group is preserved;
2. P/OP1/OP2 with missing OP3 is completed using tetrahedral starting geometry;
3. if no phosphate atoms are present, P/OP1/OP2/OP3 are seeded from the local
   O5'-C5'-C4' sugar frame with idealized, clash-checked starting coordinates;
4. any other partial phosphate state stops for review rather than guessing;
5. the generated geometry is recorded and remains subject to ReadySet/Phenix
   regularization and final model inspection.

The local-frame construction is a starting-coordinate operation, not an
assertion that the initial group is the experimentally measured phosphate
geometry. Live validation on a phosphate-free 5W6W fixture established that the
constructed group can enter ReadySet and native Phenix interpretation cleanly.
Phenix's native terminal-phosphate geometry is not a perfectly symmetric
109.47-degree tetrahedron; where exact native ideals matter, NASolve should read
or preserve the authoritative Phenix chemistry rather than substitute its own
idealized target.

## Refinement protection for constructed terminal chemistry

Low-information terminal groups can be driven into chemically implausible
internal geometry by global diffraction weighting even when their starting
coordinates and native Phenix restraints are valid. For a declared standard
terminal phosphate, NASolve therefore treats local geometry protection as part
of the normal chemistry contract rather than waiting for an unprotected
refinement to fail first.

The production contract is:

1. construct the explicitly requested terminal group in a local molecular frame;
2. validate it for completeness, connectivity, severe clashes, and Phenix
   interpretability;
3. obtain the authoritative native terminal-phosphate geometry from Phenix
   interpretation rather than hard-coding a second NASolve geometry table;
4. before the first coordinate refinement, generate local
   `geometry_restraints.edits` using `action = change` to retain Phenix's native
   ideals while tightening only the reviewed low-information internal geometry;
5. keep normal global diffraction/stereochemistry weighting unless an
   independent diagnostic justifies changing it;
6. record the protection file as a normal checkpoint restraint artifact so it
   is inherited transitively by every refinement, Doctor branch, or manual
   child descended from that protected checkpoint;
7. after every refinement, audit the declared terminal group against the final
   Phenix geometry restraints; and
8. if the protected group still exceeds the guarded geometry threshold, stop
   for review and allow Refine Doctor to create a bounded clean-parent rescue
   rather than silently accepting the distorted coordinates.

The first validated 5'-phosphate experiment established this policy
experimentally. An unprotected default refinement drove one native P-centered
angle to approximately 7 sigma from its Phenix target. A sibling using local
`action = change` protection retained normal global X-ray weighting, removed
the severe violation, passed all 11 terminal-phosphate geometry checks, and did
not worsen the global R factors. The protected branch therefore becomes the
production default; the deliberately unprotected route remains diagnostic.

Protection is lineage-scoped. A child of a protected checkpoint inherits the
protection automatically. A deliberate branch from an older unprotected
checkpoint does not silently acquire it unless terminal-phosphate protection is
being generated anew from the declared chemistry contract. Future merge/rebase
operations must preserve all applicable chemistry-protection restraints and
rerun the terminal-geometry audit afterward.

An advanced opt-out may disable proactive terminal-phosphate protection for
diagnostic or method-development work. Such an override must be explicit,
prominently reported in provenance, and must **not** disable the final geometry
audit. Automatic chemistry rescue should also remain suppressed while that
override is active, so "off" means deliberately off rather than partially off.

A globally conservative `wxc_scale` branch remains useful as a diagnostic, but
blanket global reweighting is not the preferred production response to a local
terminal-group geometry problem.

NARestraints remains responsible for reviewed pairing/stacking geometry and
should not duplicate Phenix's native terminal-phosphate restraints.

## 3'-terminal phosphates

3'-phosphate chemistry exists and should eventually be represented by a
reviewed recipe. NASolve does **not** currently guess a representation for it.
Unlike a 5'-terminal phosphate, a 3'-terminal phosphate can collide with the
usual P atom naming/ownership convention of a nucleotide that already carries
its incoming phosphate, so a real example and reviewed atom/link convention
should precede automation.

When a validated 3'-phosphate example is available, its constructor should
explicitly inherit the lessons from the 5'-phosphate work rather than being
implemented as a simple atom-name swap:

- require an explicit, site-scoped 3'-phosphate declaration;
- establish authoritative atom ownership, naming, connectivity, and native
  Phenix geometry from a real reviewed example before coding the recipe;
- construct missing atoms in a local molecular frame defined from the terminal
  sugar, with deterministic orientation and clash checks;
- preserve complete existing groups and fail closed on ambiguous partial states;
- treat constructed coordinates as starting coordinates rather than measured
  geometry;
- validate the prepared group through ReadySet/Phenix before refinement;
- run the same post-refinement local-geometry audit used for constructed
  5'-phosphate chemistry; and
- if refinement distorts the low-information group, prefer a Refine Doctor
  sibling using local `action = change` tightening of **native** restraints over
  duplicate custom restraints or a blanket reduction of global X-ray weight.

No 3'-phosphate constructor should be generalized from the current 5' routine
until this atom/link convention and a live refinement example are reviewed.

If you need 3'-phosphate support now, please contact the developers with an
example model and intended linkage.

## Non-standard backbones

A site may be declared in `nasolve.txt`:

```ini
[automr]
allow_unreviewed_backbone = true

[backbones]
A:12 = experimental_passthrough
```

`experimental_passthrough` is deliberately not a chemistry recipe. It means:

- apply otherwise supported mutation/model-preparation steps;
- do not apply the standard phosphate-linkage validator at the flagged site;
- do not invent missing atoms, bonds, or atom deletions for that site;
- preserve the site in run/campaign provenance as chemically unvalidated;
- continue only because the user explicitly opted into unreviewed chemistry;
- require human inspection before the structure is accepted or deposited.

This makes one-off GNA/PNA/TNA/other backbone experiments possible without
pretending NASolve understands their connectivity.

## Human review

Runs containing experimental passthrough sites retain a persistent
`UNREVIEWED_NONSTANDARD_BACKBONE` warning. The review interaction is:

1. After a successful interactive AutoRefine, NASolve asks whether to show the
   flagged result in Coot (`y/n`). The same flow is available later through
   `nasolve backbone-review RUN`.
2. If opened, the user inspects the current model and maps.
3. NASolve then asks whether the chemistry has been reviewed (`y/n`).
4. Confirmation writes a separate review record with a run-anchored model
   reference and the inspected model hash and marks it `USER_REVIEWED`; it does
   not erase the fact that passthrough chemistry was used.

Declining review does not convert an otherwise successful refinement into a
failed run; the warning remains pending. For non-interactive campaigns, the
same condition remains an inspection flag and can be reviewed later with the
dedicated backbone review command.

## Future reviewed custom recipes

A future custom-backbone recipe should be intentionally small and readable by a
chemist/crystallographer. The desired language is closer to:

```text
Backbone recipe: example phosphodiester-like linkage
incoming connection: previous O3' -> this P
outgoing connection: this O3' -> next P
delete from internal residue: OP3
keep: P, OP1, OP2
```

than to a low-level machine graph. Internally NASolve can compile that text into
strict selections and checks, but the source recipe should remain auditable by
a human.

No generic custom-linkage executor is included yet because we do not have a
reviewed non-standard example in this repository. If your structure uses GNA,
PNA, TNA, or another unsupported backbone, please contact the developers (Simon
Vecchioni / Jens Mueller) with the intended inter-residue atom connections and
atoms that should be deleted or retained. A validated real case can then be
promoted into a reusable recipe rather than guessed.

## Relationship to NARestraints

Backbone chemistry does not by itself disable NARestraints pairing or stacking.
A single non-standard residue may still use the same base mapping and stacking
geometry as neighboring nucleotides. NARestraints owns reviewed pairing and
stacking geometry; NASolve owns model preparation, inter-residue backbone
chemistry, terminal chemistry, dictionary precedence, and provenance.

## Safety and provenance rules

- Raw input models and numbered runs are never rewritten in place.
- Automatic standard-phosphodiester corrections are site- and connectivity-
  checked.
- Unsupported backbone chemistry is opt-in and remains visibly unvalidated.
- Human review changes review status but never removes passthrough provenance.
- DE dictionary repair and sulfur-contact validation are separate work and are
  not part of this feature.
