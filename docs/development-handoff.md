# NASolve development handoff

Status: **current working state — updated 2026-09-26**.

This file records the implementation edge: what is validated now, what is
scientifically blocked, and what should happen next.

Durable behavior belongs in `architecture.md` or the relevant subsystem
document. Superseded handoffs and validation diaries live under `docs/history/`.

## Current pipeline

The guarded standalone spine is operational:

```text
AutoMR -> PostMR -> conditional AutoSol -> AutoRefine
       -> conditional Refine Doctor -> inspection / explicit selection
```

Numbered runs and checkpoint branches are immutable. Free-R flags are not
regenerated for convenience. Refine Doctor preserves the current checkpoint
unless a user explicitly selects another one.

Latest local code regression baseline before the current documentation/design
update:

- **620 tests passed** in the full suite;
- the focused donor/recipient comparison slice passed **51 tests plus 22
  subtests**.

These results were reported from the active Python 3.12 development
environment. The Sep 26 Construct Registration/NAPrep update is documentation
and architecture planning only; it does not claim a new code-test,
`compileall`, `diff --check`, or GitHub Actions result.

## Terminal-phosphate chemistry

The W/5W6W recipe explicitly declares the designed D:1 5-prime phosphate.

PostMR treats a requested standard 5-prime terminal phosphate as the complete
P/OP1/OP2/OP3 group:

- preserve a complete valid group;
- complete P/OP1/OP2 by adding OP3;
- construct a wholly missing group from the local O5'-C5'-C4' sugar frame;
- fail closed on ambiguous partial groups, incoming/internal O3'-P conflicts,
  cyclic-like geometry, or other contradictory chemistry.

`MR_frames/5W6W/5W6W_noPO4.pdb` is a forced validation fixture, not a normal
catalogue fallback.

Live ED `run_010` validation confirmed that a wholly missing D:1 phosphate can
be constructed, survive ReadySet, pass Phenix interpretation, and enter
refinement.

### Geometry ownership

Keep these responsibilities separate:

- **Phenix** supplies authoritative native terminal-phosphate geometry.
- **NASolve** owns terminal intent, construction, provenance, geometry audit,
  and local protection policy.
- **NARestraints** owns reviewed pairing/stacking geometry and must not
  duplicate Phenix's native terminal-phosphate geometry.

Constructor coordinates are starting geometry only, not a second native
refinement target.

### Refinement audit and Doctor rescue

An unprotected refinement exposed a real low-information failure: one native
P-centered phosphate angle moved to approximately 7 sigma from its Phenix
target while the global R factors remained superficially reasonable.

AutoRefine now audits declared terminal phosphates from Phenix's final geometry
output. Eleven restraints are expected per site:

- four P-O bonds;
- six P-centered angles;
- one P-O5'-C5' angle.

A >=5-sigma local violation forces `AUTOREFINE_REVIEW` independently of the
global numerical gate.

Refine Doctor was live-validated from `refine-003`. It branched from the clean
`postmr` parent, generated six local Phenix `action = change` angle protections
using Phenix-derived ideals, and created `refine-004`.

`refine-004` reported:

- Rwork/Rfree = 0.1735 / 0.1707;
- terminal audit `PASS`;
- 11/11 expected restraints found;
- zero severe restraints.

It remained a numerical user-review case because Rwork was still slightly above
Rfree. Chemical validity and numerical acceptance are intentionally separate.

## Proactive terminal protection: live-validated

Production AutoRefine now protects a declared standard terminal phosphate from
**refinement #1** rather than deliberately allowing an unprotected refinement
before Doctor rescue.

For a declared site on an unprotected lineage, AutoRefine now:

1. runs `phenix.pdb_interpretation ... write_geo=True` on the inherited
   model/restraint bundle before creating the numbered refinement round;
2. requires a complete native Phenix geometry snapshot with all 11 expected
   terminal-phosphate restraints per site;
3. derives the six P-centered angle ideals from that Phenix geometry rather
   than from a NASolve hard-coded target table;
4. writes local `action = change` protection at sigma = 1 degree;
5. stores the source `.geo`, interpretation log, and protection PHIL inside the
   new AutoRefine round;
6. attaches schema-1 semantic protection provenance to the checkpoint;
7. passes the protection restraint to the first coordinate refinement;
8. inherits the same protection through AutoRefine/manual descendants without
   stacking duplicate protection files; and
9. retains the final 11-restraint geometry audit after every refinement.

Preparation fails closed before `round_00N` is created if Phenix interpretation
is unavailable or the declared terminal geometry is incomplete.

Live ED `run_010` validation from the clean `postmr` parent created
`refine-005` with proactive protection already present in the actual
`phenix.refine` command. It reported:

- Rwork/Rfree = 0.1735 / 0.1707;
- semantic protection for D:1 with six angles at sigma = 1 degree;
- ideal source = pre-refinement `phenix.pdb_interpretation` geometry;
- final terminal audit `PASS`;
- 11/11 expected restraints found;
- maximum final normalized deviation = 4.27 sigma under the tightened
  1-degree protection;
- zero severe restraints.

`refine-005` therefore reached the same protected endpoint as the earlier
Doctor rescue `refine-004` without requiring an unprotected sacrificial
refinement first. Its `AUTOREFINE_REVIEW` status is numerical only because
Rwork remains slightly above Rfree; the terminal chemistry itself passes.

A future advanced opt-out may disable proactive protection deliberately, but it
must remain explicit, visible in provenance, and must not disable the final
geometry audit.

## Unsupported backbone chemistry

Ordinary DNA/RNA-like phosphodiester chemistry is the automatic default.

Unsupported GNA/PNA/TNA/other linkage chemistry is never guessed.
`experimental_passthrough` bypasses only the standard linkage validator at the
declared site and remains visibly unreviewed until a human Coot review is
recorded.

The interactive passthrough review path has now been live-validated on a
disposable copy of ED `run_010` using a synthetic A:12
`experimental_passthrough` declaration. NASolve opened the intended
`refine-005` model/maps in real Coot, waited for human confirmation, and wrote a
portable `USER_REVIEWED` record containing the run-anchored model reference,
model SHA-256, flagged site, timestamp, and preserved passthrough provenance.
This validated the review UX/provenance path only; it does not assert
non-standard chemistry at A:12.

## Campaign provenance and Doctor groundwork

Sequential campaign execution from immutable plans is operational for the
current standard W path. Planning freezes explicit dataset/model/reference
choices, supports root `nasolve-campaign.toml` sequence threads, and keeps
run/checkpoint lineage immutable.

The donor/recipient provenance stack is now implemented in read-only layers:

- complete explicit sequence-family targets and search-model mismatch
  provenance when a target is available;
- checksum-bound model compatibility fact sheets for every fresh AutoMR run;
- explicit provider-side `model_family` declarations bound to a named model,
  never inferred from frame, filename, sequence thread, or similarity;
- checkpoint-candidate descriptors that re-verify the selected checkpoint
  model, observations, lineage, literal residue inventory, chemistry context,
  and frozen target comparison; and
- donor-checkpoint versus recipient-run comparisons that re-verify both sides
  and compare literal donor site/residue inventory against the recipient's own
  frozen target while keeping source frame/reference/mirror facts as context.

These layers are deliberately **descriptive only**. They do not rank donors,
declare donor eligibility, declare recipient compatibility, authorize rescue,
or reuse a solved sibling automatically. Source observations remain donor
provenance rather than recipient evidence.

The next campaign orchestration edge is therefore a separate reviewed
eligibility/rescue policy that consumes these facts under a bounded budget.
That future layer must record the exact donor checkpoint, recipient, applicable
hard gates, transformations, attempts and stopping reason without rewriting the
recipient's authoritative observations, Free-R set, target chemistry or failed
branch.

## Construct registration: next structural robustness layer

The next planned scientific infrastructure is **Construct Registration**:
logical construct sites must be separated from incidental PDB chain names,
residue numbering and ASU cuts.

The design contract is
[`construct-registration.md`](construct-registration.md). It now records the
full expected failure-mode inventory, automatic-versus-guided triage matrix,
user-escalation rules, reporting escalation, Registration Net interaction model,
reviewed recipe promotion rules, and the rationale for preferring scout -> MR
-> authoritative ASU registration over heavy pre-MR coordinate surgery.

The intended timing is:

```text
logical construct manifest
    -> AutoMR Registration Scout (cheap, non-mutating)
    -> ordinary MR first when plausible
    -> authoritative ASU Registration on the MR solution
    -> PostMR logical-site sequence/chemistry
```

MR itself is often the most useful coordinate registry. NASolve should not
require heavy recutting, renumbering or mutation of a plausible search model
before learning whether it solves.

If MR fails, or a reviewed representation problem is known, a separate bounded
**Registration/Recut Rescue** may build a transformed candidate with frozen
provenance. Planned reviewed transforms include equivalent ASU cuts,
split/join/relabel/renumber operations, sticky-end/boundary changes and
explicitly reviewed boundary chemistry.

The common W path must stay cheap: an identity-like single-copy registration
should pass automatically without user interaction.

Guided mode is reserved for crystallographically interesting cases such as:

- equivalent but nontrivial ASU cuts;
- renamed/renumbered/split logical strands;
- unexpected complete copy multiplicity;
- one complete plus a partial copy;
- sticky-end/arm coverage differences; or
- several non-equivalent registrations.

The **Registration Net** will be a simple 2-D SVG/HTML schematic, not a second
molecular viewer. It should show logical strands, coordinate fragments,
symmetry/ASU seams, complete/partial copies, sticky ends, important logical
sites and mapping bands. Minimal click actions will accept/reassign fragments,
select equivalent cuts/recipes, mark partial/extraneous fragments and preview
recuts; Coot remains the coordinate editor.

The first planned validation ladder begins with ordinary W identity
registration and an 8D93-style -> W recut fixture, then chain renaming,
numbering offsets, chain splits, multicopy/partial-copy ASUs and bounded
multi-PDB MR candidates.

### Birch implementation checkpoint

The first backend-only slice is now implemented on the `birch` development
branch without changing any existing AutoMR/PostMR call path.

Implemented:

- strict logical-site -> coordinate-site registration records;
- complete, multicopy and partial-copy representation;
- complete-copy-only logical mutation/chemistry expansion;
- checksum-bound freeze/load provenance and semantic revalidation;
- exact accounting for mapped and unmapped polymer residues;
- read-only logical inventories for later Hemlock/Moss/Campaign Doctor use;
- conservative Registration Scout v1 for identity, same-name constant residue
  offsets, unique whole-chain rename, and rename-plus-offset cases;
- descriptive per-candidate design-identity evidence that is explicitly barred
  from Scout assignment/ranking;
- checksum-bound `Model/registration_scout.json` freeze/load with semantic
  revalidation; and
- a non-decisional registration-transition comparison for later
  Scout-versus-authoritative-MR reporting;
- UI-independent guided resolution for ambiguous simple chain assignments,
  restricted to explicit user selections among already enumerated Scout
  candidates;
- read-only top-level dataset PDB candidate inventory with valid/invalid
  diagnostics, per-file SHA-256/size and a stable candidate-set fingerprint;
  and
- read-only conservative Registration Scout across every valid discovered PDB,
  with no ranking, selection or MR authorization.

Scout v1 deliberately does not use sequence-similarity ranking, modified-site
similarity, symmetry expansion, split-chain inference, copy-number inference or
topology. Ambiguous renamed chains remain ambiguous rather than being selected
by a hidden score.

The primary inference regime is designed self-assembling nucleic-acid crystals:
input construct sequence/modification/boundary intent is normally known and
short designed strands are usually less repetitive than generic polymers.
Repeated short motifs and single-base overhangs remain explicit ambiguity
hazards rather than ignored corner cases.

The machine-readable development policy is
[`construct-registration-intent.json`](construct-registration-intent.json).
Policy changes should update that file alongside the human design contract so
real-data testing can intentionally backtrack or revise inference behavior
without losing why an earlier rule existed.

The minimum human/real-workflow validation queue is maintained separately in
[`construct-registration-live-checks.md`](construct-registration-live-checks.md).
Keep that list intentionally small and trigger-based; it exists so clean-W,
8D93-style recut, 8D31-like multiplicity, guided ambiguity and bounded multi-PDB
live checks are not forgotten as implementation context moves across chats.

Local focused validation reported **23 passing tests** in
`tests/test_construct_registration.py` at Birch code head
`4452295c3330de6d55bddd75b01be21f39afb222`. This is a user-local test
checkpoint, not GitHub CI. Newer design-evidence/frozen-Scout/transition code is
intentionally tracked as **pending validation** in the machine-readable intent
ledger rather than being folded into that earlier green checkpoint.

## NAPrep boundary

NAPrep is a separate optional upstream design/data-management package, analogous
in separation to NARestraints. It may organize design records, sequences,
sample/collection metadata, folders and externally generated model candidates.

NASolve does **not** invoke AlphaFold.

NASolve remains responsible for the crystallographic/campaign decision tree
once a curated handoff exists: AutoMR, Construct Registration, PostMR, AutoSol,
refinement, Campaign Doctor, reporting/curation and deposition. NAPrep must not
become a second campaign manager that re-infers NASolve's downstream decisions.

Direct manually prepared NASolve inputs remain supported; NAPrep is not a
runtime requirement.

## Separate scientific follow-up

These are not blockers for proactive terminal-phosphate protection:

- **DE dictionary** remains defective/unapproved for production refinement.
- sulfur-containing pair target geometry still needs a reviewed source/target
  audit;
- provisional `force = G:C` should change pair restraint geometry only, never
  residue or deposition identity;
- a future MR Doctor may add preset-specific checks such as 5W6W sticky-end
  packing, but must not globally redefine TFZ 7 as success;
- Final Model Doctor / curate / deposition should preserve explicit evidence
  provenance rather than assuming every artifact comes from the selected
  coordinate checkpoint;
- Construct Registration/Registration Net and bounded recut rescue are the next
  structural robustness layer before broad automatic Campaign Doctor rescue;
- reviewed Campaign Doctor eligibility and bounded rescue execution remain a
  major orchestration layer; donor provenance and donor-to-recipient descriptive
  comparison prerequisites are already implemented.

## Documentation rule

Use:

- `README.md` for human workflow;
- `docs/README.md` as the documentation map;
- `docs/architecture.md` for durable invariants;
- subsystem docs for active scientific/technical contracts;
- this file for immediate implementation state;
- `docs/history/` for archaeology only.

Future work should not require chat history to recover the active design.
