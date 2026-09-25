# NASolve development handoff

Status: **current working state — updated 2026-09-25**.

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

Latest local regression baseline before this documentation-only cleanup:

- **620 tests passed** in the full suite;
- the focused donor/recipient comparison slice passed **51 tests plus 22
  subtests**.

These results were reported from the active Python 3.12 development
environment. This handoff does not claim fresh `compileall`, `diff --check`,
or GitHub Actions results beyond the checks actually run in that development
window.

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
- reviewed Campaign Doctor eligibility and bounded rescue execution remain the
  next major orchestration layer; the donor provenance and donor-to-recipient
  descriptive comparison prerequisites are already implemented.

## Documentation rule

Use:

- `README.md` for human workflow;
- `docs/README.md` as the documentation map;
- `docs/architecture.md` for durable invariants;
- subsystem docs for active scientific/technical contracts;
- this file for immediate implementation state;
- `docs/history/` for archaeology only.

Future work should not require chat history to recover the active design.
