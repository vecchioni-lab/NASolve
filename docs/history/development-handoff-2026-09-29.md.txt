# NASolve development handoff

Status: **current working state — updated 2026-09-29**.

This file records the implementation edge: what is validated now, what is
scientifically blocked, and what should happen next.

Durable behavior belongs in `architecture.md` or the relevant subsystem
document. Superseded handoffs and validation diaries live under `docs/history/`.

## Read this first: current development edge

For a fresh development session, recover state in this order:

1. **Registration state:** Oak/PR #22 is merged to `main` at
   `fec66ebeddbd525684824576b705460324ec0a14`. The design-aware Scout
   implementation remains **proposal-only/non-runtime**. Internally the dev
   history distinguishes Scout v1/v2; scientist-facing language should simply
   say **Scout**.
2. **Active branch:** `pine`. The last fully returned local regression baseline
   is **688 tests + 224 subtests**, with the campaign family at
   **132 tests + 85 subtests** and campaign executor CLI at
   **9 tests + 4 subtests**. That baseline includes the campaign-owned Refine
   Doctor bridge and its live QiC validation.
3. **Campaign-owned Refine Doctor is regression + live validated.** In the real
   four-member W campaign, DOHU/EG/QE reached `SOLVED`; QiC required AutoSol,
   initially stopped at `refine-001` review, then campaign-owned Doctor ran
   `RefineDoctor/ML-fixed-scattering` and produced recommended `refine-002`
   at Rwork/Rfree = **0.1500/0.1502**. Doctor preserved actual current
   checkpoint `postmr` and did not auto-select the recommendation. Do not run
   standalone Doctor out-of-band on a campaign-owned run; use campaign provenance.
4. **Immediate code edge: GZ11 forced restraint geometry.** Pine now contains an
   **implemented-unvalidated** `[automr] force = FIRST:SECOND` pathway.
   `pair = G:Z` remains the actual chemistry/target; `force = G:C` overrides
   only the NARestraints base-pair recipe for the designated W pair
   A:12/B:4. Residue identity, model selection and flanking-pair inference remain
   separate. Parser/AutoMR/campaign/PostMR code and focused tests are present,
   but **Simon has not yet run the local regression ferry**. Do not promote this
   feature to validated until that evidence returns.
5. **Nine-dataset live stress test is staged conceptually, not yet planned.**
   User-local `examples/TestSets/` contains exactly:
   `DOHU`, `DT`, `DiU`, `EA`, `ED`, `FA`, `GZ11`, `Q5cm`, `QiC`.
   All nine have the current AutoPROC/STARANISO MTZ + `Data_1*.cif` +
   `summary.html` profile and `nasolve.txt`. EA/ED already contain historical
   `AutoMR/` directories, which campaign execution should leave alone while
   allocating a new numbered run. The TestSets root has **no**
   `NASolveCampaign/` and no `nasolve-campaign.toml`; the source folder
   remains untracked and untouched.
6. **Do not rewrite GZ11 input.** Its literal
   `pair = G:Z` / `force = G:C` is the intended edge case. Scientific
   motivation: at pH 11, Z is deprotonated/C-like for the intended hydrogen-bond
   geometry. The packaged repo currently exposes no `DZ.cif`; before live
   PostMR, verify the reviewed DZ construction/dictionary provenance from the
   previously successful standalone GZ11 path rather than guessing or fetching
   chemistry silently.
7. **Reflection-input compatibility roadmap:** current runtime still discovers
   MTZ only and requires `Data_1*.cif` + `summary.html`. This is an adapter
   limitation, not a scientific invariant. Future campaign setup should classify
   `MR-ready`, `refinement-ready`, `anomalous-ready`, and
   `deposition-ready` separately. Generic MTZ should work by content.
   SCA/Scalepack is a legitimate **direct Phaser/MR source**; any later SCA->MTZ
   derivation should exist only when a downstream stage needs MTZ arrays and must
   carry separate checksum/provenance. Missing deposition metadata should lock
   deposition, not structure solution.
8. **Next product semantic after the live flock:** first-class frozen workflow
   recipes declaring endpoint/conditional graph, including an optional human
   semantic **"apply Doctor as needed"**. Current explicit
   `--through refine-doctor` remains the validated path.
9. **Separate Pine live gate still pending:** a dedicated real
   prepared-nonstandard/geometry-diverse 3-5 dataset campaign. After that, add
   explicit stable `design_id`, then allow the GUI fork. The GUI should visually
   build the same backend recipe and expose CLI-equivalent inspect/confirm/select
   operations.
10. **Later Campaign Doctor:** campaign-wide donor rescue remains on its separate
    runway: read-only candidate matrix -> reviewed eligibility -> attempt-local
    donor provenance -> explicit donor rescue -> bounded enumeration. Do not
    infer donor eligibility from similarity/ranking.


Scientific invariants remain stronger than convenience: immutable attempts,
frozen observations/Free-R/targets, fail-closed ambiguity, one dataset's
review/failure not stopping unrelated members, and no hidden score/ranking used
to authorize donor reuse or registration.

### GZ11 forced restraint-geometry edge case

The user-local TestSets campaign contains GZ11 with:

```ini
[automr]
mode = standard
frame = W
pair = G:Z
force = G:C
```

This historical `force` semantics has now been recovered and restored on Pine
as **implemented-unvalidated** pending the next local regression ferry.

- `pair = G:Z` is the actual intended residue identity/chemistry.
- `force = G:C` is **not** a mutation and **not** a search-model override.
- It requests G:C-like NARestraints pair geometry for the W standard pair only
  (A:12/B:4), while preserving the actual G/Z residue atom mappings.
- Scientific motivation: GZ11 is measured at pH 11, where Z is deprotonated and
  C-like for the intended H-bond geometry.
- The override is frozen separately through AutoMR/campaign provenance and must
  apply exactly once to the designed pair; flanking frame-template pairs remain
  inferred from their actual residues.
- PostMR records both actual base classes and forced recipe classes. If the
  designed sites are no longer paired together, or the requested recipe cannot
  be generated, PostMR fails closed.

The current packaged NASolve ligand directory does not contain `DZ.cif`.
Before the live nine-dataset run, inspect the successful standalone GZ11
provenance/local files to determine which reviewed DZ dictionary/construction
path it used; do not guess or silently download one.

### Session handoff — 2026-09-29

- **Validated baseline:** 688 tests + 224 subtests; campaign family
  132 + 85 subtests; campaign-owned Refine Doctor regression + live validation
  complete.
- **Newest code beyond that baseline:** forced restraint-geometry support for
  `force = FIRST:SECOND`, specifically needed by GZ11
  (`pair = G:Z`, `force = G:C`). It is **implemented-unvalidated** until
  Simon runs the pending local regression ferry.
- **No nine-dataset campaign plan has been created yet.** Original
  `examples/TestSets/` remains untracked and untouched.
- **Next execution order:** pull latest Pine -> run force-focused regression ->
  run relevant campaign/full regression -> inspect/confirm GZ11 DZ dictionary
  provenance if needed -> plan a disposable TestSets campaign -> if all nine are
  discovered, run the campaign from MR through explicit `refine-doctor`.
- **Success criterion:** not "force nine greens"; one invocation should produce
  the maximum scientifically valid solved/Doctor-recommended/inspection set,
  preserving honest blockers and exact provenance.
- **Source-data portability work is roadmap only:** generic MTZ and direct-SCA
  capability modeling is documented but not implemented.
- Known user-local untracked data, patches, bundles, environments and example
  runs remain out of scope for cleanup unless Simon explicitly asks.


A fresh session should start by reading this section plus the machine intent,
then inspect the current Pine head before changing code.

### Development handoff workflow

Use a small number of compact multi-command terminal ferries rather than many
tiny exchanges.

- Work in one coherent code/docs slice at a time.
- Prefer one dense sequential command block for a coherent validation boundary:
  normally pull -> syntax/focused tests -> relevant family/full regression ->
  live mutation only behind successful `&&` gates -> concise status/worktree.
- After returned output, diagnose the first meaningful failure before adding
  more work.
- Promote validation status only after supporting evidence is returned.
- Keep code and documentation synchronized using the smallest authoritative doc
  set.
- Do not stage, delete, rename, or otherwise clean unrelated untracked
  scientific data, patches, bundles, old environments, or example runs without
  explicit instruction.
- Preserve enough repository state that development can resume without relying
  on chat history.

## Current pipeline

The guarded standalone spine is operational:

```text
AutoMR -> PostMR -> conditional AutoSol -> AutoRefine
       -> conditional Refine Doctor -> inspection / explicit selection
```

Numbered runs and checkpoint branches are immutable. Free-R flags are not
regenerated for convenience. Refine Doctor preserves the current checkpoint
unless a user explicitly selects another one.

Latest local code regression baseline on Pine:

- **688 tests passed** in the full NASolve suite;
- **224 subtests passed**;
- full-suite runtime: **58.19 s**;
- campaign family: **132 tests + 85 subtests passed** in **24.08 s**;
- campaign executor CLI: **9 tests + 4 subtests passed** in **0.24 s**;
- campaign Doctor focused slice: **4 tests + 4 subtests passed** in **4.77 s**;
- patch/doc hygiene passed; and
- the real QiC campaign Doctor live continuation passed through immutable
  campaign provenance.

These results were reported from the active Python 3.12 development environment
on Pine after the campaign-owned Refine Doctor bridge and stale CLI regression
fix. This is a user-local validation result, not GitHub CI. The untracked local
scientific/test artifacts were left untouched.

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

### Pine: geometry-diverse campaign backend before GUI implementation

Pine is now the active campaign branch, created from Oak after the backend-only
Scout-v2 scope was closed. It implements the first conservative heterogeneous
campaign slice while leaving Oak/PR #22's runtime scope unchanged.

Current Pine behavior:

- new campaign plans use schema 2;
- existing schema-1 W plans remain readable **and executable**;
- one explicit or uniquely discovered nonstandard PDB provider is allowed per
  dataset;
- the exact model bytes/checksum/provider provenance are content-addressed and
  frozen;
- a nonstandard dataset must supply an explicit complete chain-labelled target
  via inline `[sequences]` or `sequence_file`;
- the raw sequence-source bytes/checksum and the parsed effective sequence target
  are frozen separately;
- frozen nonstandard preflight reconstructs ordinary `ResolvedAutoMRInput`
  without source-folder/catalogue rediscovery;
- discovered-model provenance remains discovery provenance after resource
  relocation rather than being rewritten as user selection;
- W preset frame/pair, W sequence-thread overlays and W D:1 phosphate chemistry
  do not leak into nonstandard members;
- fixture-backed full execution reaches AutoMR -> PostMR -> conditional AutoSol
  -> AutoRefine after deleting the original model/FASTA and after campaign
  relocation; and
- a mixed standard-W + nonstandard fixture campaign uses one coordinator while
  retaining separate frame/target/provider contexts.

The guardrail remains deliberately narrow: model-to-sequence correspondence
must be simple and unambiguous. Nontrivial registration, recuts, split chains,
unexpected multiplicity or topology stop only that dataset for inspection.
Scout v2 is not promoted merely to unblock campaign execution.

**Next live gate:** run a real 3-5 dataset geometry-diverse campaign with the
user's actual Phenix/Coot installations and inspect exact run/checkpoint
ownership plus at least one review/block case. Only after that live gate should
we add minimal explicit `design_id` grouping for datasets sharing a stable
construct/design record. Do not infer design membership from filenames or
sequence similarity.

**GUI branch point:** only after the real heterogeneous campaign and Design
identity are CLI-functional should implementation attention split into the GUI.
The GUI then visualizes stable backend concepts rather than inventing them.

The Campaign Doctor runway after that branch point is already mapped in the
campaign roadmap: read-only campaign-wide donor/recipient facts -> reviewed
eligibility policy -> attempt-local derived-provider provenance -> one explicit
donor rescue -> bounded automatic donor enumeration. None of those should be
smuggled into the first heterogeneous campaign milestone.

Pine campaign work remains a separate development scope above the now-merged
Oak mainline. PR #22 is complete; Pine does not turn Scout v2 into runtime
authority.

### Current live orchestration validation: four-member W campaign

Before the prepared nonstandard geometry-diverse datasets are supplied, Pine is
also being exercised on an intentionally easy **real W campaign** to validate
campaign orchestration with the user's actual Phenix/Coot environment.

The live sandbox is:

`/tmp/NASolve-W-live-20260928`

and is built from clean top-level copies of:

- `DOHU`;
- `QiC_120325_0513`;
- `QE_120325_0607`; and
- `EG_091325-0302`.

This validation is **not** a substitute for the later geometry-diverse
nonstandard live gate. Its purpose is narrower and useful:

- verify a real multi-dataset campaign can plan and run sequentially under one
  coordinator;
- verify campaign-owned numbered runs/checkpoints are attributable per dataset;
- confirm one review/failure remains local while other datasets continue;
- exercise real Phenix/Coot rather than fixture executables; and
- produce a compact campaign-level solution list
  (dataset -> status -> run -> checkpoint -> diagnostic) suitable for later GUI
  and Campaign Doctor presentation.

The planning/status phase has now passed in the real user environment:

- `nasolve check`: Python 3.12.14, NARestraints 1.1.2, Phenix 2.2.1 and
  Coot 1.3.3 all reported OK;
- all four datasets were `DISCOVERED`;
- zero datasets were blocked;
- frozen input integrity was `OK`; and
- every member froze the expected W recipe chemistry with D:1 as the explicit
  5-prime-phosphate/OP3 site.

The bounded real MR/PostMR phase has now also passed for all four datasets.
Each dataset allocated campaign-owned `AutoMR/run_001`, completed preflight,
Phaser and PostMR, and paused cleanly at the next conditional AutoSol stage.
Campaign exit code and status exit code were both 0; frozen integrity remained
`OK`.

This wording matters: `next_stage = autosol` means the executor will evaluate
the conditional AutoSol gate. It does **not** mean every dataset requires
AutoSol. The stage engine reads PostMR anomalous evidence and returns `SKIPPED`
without launching `phenix.autosol` when no supported nucleotide heavy atom is
present. `SKIPPED` is an accepted campaign AutoSol outcome.

A plain `campaign run ROOT` already defaults through AutoRefine, so the
`--through postmr` boundary used here was a validation handbrake rather than a
required interactive workflow. The selected preset already freezes
`autosol.policy = when-anomalous` and the AutoRefine recipe/cycle count.

**New workflow requirement:** evolve the preset/campaign recipe contract so the
desired campaign endpoint and conditional stage graph are explicit recipe data,
rather than relying on the executor's built-in stage order/default endpoint.
The eventual common UX should be: select/freeze one campaign recipe, issue one
run command, and let each dataset advance independently until solved, review,
blocked, or another recipe-declared terminal state. Later reviewed Doctor
escalation may join that graph, but must remain bounded and provenance-rich.

The unattended resume has now completed and closes the W orchestration smoke
test:

| Dataset | AutoSol | Final campaign state | Checkpoint |
| --- | --- | --- | --- |
| DOHU | `SKIPPED` | `SOLVED` | `refine-001` |
| EG_091325-0302 | `SKIPPED` | `SOLVED` | `refine-001` |
| QE_120325_0607 | `SKIPPED` | `SOLVED` | `refine-001` |
| QiC_120325_0513 | `AUTOSOL_READY` | `AWAITING_INSPECTION` | `refine-001` |

Campaign state was `COMPLETE_WITH_FLAGS`, frozen integrity remained `OK`,
and both run/status returned exit code 3 because QiC correctly remained a review
case. This is desirable scientific isolation: the three unrelated members were
not held back, and the questionable result was not promoted to solved.

QiC is also the motivating kind of dataset for Refine Doctor. Its exact live
review fingerprint is useful:

- AutoSol: `AUTOSOL_READY`, `use_for_refinement = true`;
- anomalous model site: iodine at `B:4`, wavelength 1.377618 A;
- refined iodine f'' = 7.51547 and f' = -5.98383;
- final `Rwork = 0.1646`, `Rfree = 0.1561`;
- `Rfree - Rwork = -0.0085`, therefore the current strict numerical gate fails;
- clashscore = 32.23;
- terminal-phosphate geometry audit = `PASS`, 11/11 expected restraints, no
  chemistry review required, maximum normalized deviation 1.74 sigma;
- `refine-001` remains a REVIEW checkpoint and was **not selected current**;
  current checkpoint remains `postmr`; and
- no Refine Doctor directory exists yet.

This is therefore a numerical/statistical review case, not a terminal-phosphate
chemistry failure.

**Do not run standalone Doctor directly on this campaign-owned run yet.**
Refine Doctor preserves the selected current checkpoint and never auto-selects a
recommendation, but it updates the run-level `report.json` with Doctor history.
The campaign AutoRefine receipt has already frozen/checksummed that report, so
an out-of-band Doctor invocation would be detected as report drift during later
reconciliation. The correct next implementation is a campaign-owned Doctor
transition with its own receipt and recipe policy.

The later Pine-specific live gate remains a real 3-5 member prepared
nonstandard/geometry-diverse campaign once those datasets are available.

## Construct registration: next structural robustness layer

The next planned scientific infrastructure is **Construct Registration**:
logical construct sites must be separated from incidental PDB chain names,
residue numbering and ASU cuts.

The design contract is
[`construct-registration.md`](construct-registration.md). It now records the
full expected failure-mode inventory, automatic-versus-guided triage matrix,
user-escalation rules, reporting escalation, Registration Net interaction model,
reviewed recipe promotion rules, and the rationale for preferring Scout -> MR
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

The **Registration Net** remains the general 2-D SVG/HTML mapping view for
logical strands, coordinate fragments, symmetry/ASU seams, complete/partial
copies, sticky ends, important logical sites and mapping bands. It is not a
second molecular viewer; Coot remains the coordinate editor.

A separate opt-in **Topo Net** extension is now planned for explicitly declared
periodic self-assembling frameworks. Topo Net should show the current ASU plus
only connected symmetry mates and operate on a periodic molecular graph rather
than treating the current PDB chain serialization as chemistry. It should let a
user preview moving an ASU seam past residues, moving symmetry-equivalent
fragments across the chosen ASU, split/join/relabel/renumber operations and
newly exposed sticky ends before coordinates are materialized.

Critical semantic distinction: an ASU seam may create a coordinate-file
"false nick" while the logical strand remains chemically continuous through a
symmetry operation. Such a representation seam keeps continuation-phosphate
intent and must not be reinterpreted as a true free 5-prime terminus merely
because the PDB starts a new chain there. A true chemical nick remains a
different, stronger edit that changes the covalent graph and terminus chemistry.

Materialization should write an immutable surgery manifest, use exact symmetry
transforms/chain operations in Coot, then re-run Phenix interpretation. Two
later empirical gates are required before automation: (1) determine whether a
Phenix symmetry-operation bond can safely enforce the seam connection without
uncontrolled phosphate-angle/clash behavior; and (2) practice bounded
single-residue Coot RSR on several disposable recuts where a phosphate/O3-prime
connection is initially too long, auditing which atoms move and whether Phenix
then interprets the linkage cleanly.

The umbrella term for this planned family is **topology-informed automation**:
topology may inform hypotheses, recuts, local repairs and branch diagnostics,
but it never overrides chemistry, diffraction evidence, fail-closed rules or
expert review.

Topo Net should also preserve a stronger design hierarchy than ASU chain
serialization. For framework work, keep four layers separate:

- complete synthesized/input strand inventory;
- tile hypothesis (usually declared, but possibly inferred/emergent);
- observed periodic crystal graph under symmetry; and
- one incidental ASU/PDB serialization of that periodic object.

Input strands are high-authority experimental intent, not guaranteed observed
content. A strand may be absent from the solved structure; copy number may
differ from the synthesis recipe; one strand may be split among symmetry/ASU
fragments; and the scientifically useful tile can become more abstract than
the original design. Tile status should therefore permit `DECLARED`, `INFERRED`,
`EMERGENT` and `UNRESOLVED` outcomes while retaining the original declared tile
for provenance.

This distinction matters for known lab-style multiplicity cases: a P4_132
structure may place two complete triangular tile copies in one ASU without
making the ASU itself the tile. Tile multiplicity, ASU multiplicity and
coordinate-chain decomposition must remain separate reported dimensions.

Repeat-bearing/root strands need their own design facts. Many tile families
contain one central/root strand with an internal n-fold repeated role while
other strands occur at higher per-tile copy number. Preserve intended
copies-per-tile and internal repeat order separately in the tile sequence
sheet; neither should be inferred from incidental ASU chain counts.

The observed periodic graph may violate both expectations. Record repeat-domain
coverage and repeat phase when possible, including cases where only part of a
root strand is ordered/used. Also allow a long topological closure: a known
fivefold repeat-bearing object embedded in a fourfold/screw lattice returned
to its original repeat phase only after twenty unit-cell steps. That is not a
missing-copy failure. It is an observed periodic organization in which the
nominal root-strand copy/repeat count is no longer a local tile invariant.

The net finder should explicitly consume declared root/repeat annotations and
may propose repeats from full sequences only as non-authoritative hypotheses.
It should map repeat domains into the periodic graph, follow phase changes
through symmetry, and report local closure, long-period closure, partial use,
reorganization or unresolved phase as separate descriptive facts. It must not
force the designed n-fold order onto the structure.

Junctions are now part of the intended Topo model as first-class topological
objects, but **junction arity is not the definition**. The minimal primitive is
a local directed-backbone passage/connection at a node; a single backbone can
be sufficient (the semi-junction is the motivating example). Four-, six- or
eight-arm junctions are contextual neighborhoods around one or more such
passages. ASU recutting may split that realization across symmetry fragments
without changing the underlying junction.

Junction declarations/hypotheses should therefore preserve stable logical
strand/residue participation, routing, true nicks/termini, sticky ends and
optional reviewed stacking/pairing expectations while treating observed arm
count as derived metadata. Net-finder discoveries remain `CANDIDATE` until
uniquely supported or user-confirmed; emergent high-valence nodes such as the
cuboctahedral case must be allowed, while apparent packing contacts may be
`REJECTED`.

Topo Net should be a persistent workbench above the checkpoint graph rather
than a one-shot cutter. A user should be able to operate on a seam/junction,
materialize a child, optionally perform bounded Coot repair, press Refine, and
receive the resulting refinement child plus diagnostics back into the same GUI
without closing/restarting the topology session. The first Refine action should
use a short ordinary audited AutoRefine path; selection-restricted refinement
is intentionally later work.

This work exposes a useful **generic NASolve GUI** seam. The existing immutable
checkpoint graph should become a reusable model-tree view for normal workflows:
MR, PostMR, AutoSol, long refinement chains, Doctor siblings, manual imports,
topology surgery and later re-MR-from-refined-model attempts should all appear
in one traversable lineage. Important checkpoints can be pinned as panels,
repetitive refine chains can collapse, and historical nodes can be selected or
used as explicit new branch sources without deleting descendants. Topo Net
should embed this same component rather than maintain a private history.

The dedicated [GUI design contract](gui.md) now records the broader shell:
Campaign -> optional Design -> Dataset -> Run scientific navigation; one-window
Navigator / Workspace / Inspector / Activity layout; root/recent-workspace
selection; explicit viewed/current/pinned separation; semantic colors with
redundant shape/fill cues; and GUI coverage for existing CLI operations
(environment/config, workspace, presets, campaign actions, AutoMR/PostMR,
backbone review, AutoSol, AutoRefine/Doctor, checkpoints and Coot inspection).
The shell is capability-driven: future backend actions/metadata/views should
register into existing surfaces rather than require a new window or bespoke
history model.

Live campaigns should update the Navigator/tree from authoritative execution
records with restrained running-node/edge activity. The bottom Activity drawer
has a human-readable Events/Notifications stream (for example "refinement 21
passed", "PostMR needs your review", "current checkpoint changed") plus
expandable exact backend tokens, metrics, diagnostics and logs. Repeated
heartbeats are coalesced; reduced-motion mode uses static activity markers.

The corresponding [GUI human live-check queue](gui-live-checks.md) covers shell
navigation, live campaign/event reconciliation, long model trees,
color/accessibility semantics, campaign/design scope changes, CLI/GUI
interoperability, Coot round-trip and a "register one new action without shell
redesign" extensibility test.

Keep the workbench display sparse. Global chips may show current checkpoint,
Rwork/Rfree and refinement/local-warning state. Selecting a residue, seam or
junction expands only the relevant local diagnostics: Phenix bond/angle
outliers, phosphate connectivity and clashes, base-plane/sugar/backbone
geometry, reviewed pairing/stacking deviations, mutation/registration state,
and later validated residue-density metrics. Selections should round-trip to
Coot so abstract Topo operations and atomic inspection stay coupled.

Topo surgery also needs a bounded local repair layer rather than assuming one
Coot action always works. A future **Topo Surgeon/Doctor** may branch a small
declared set of materialization/mutation/RSR strategies, then compare Phenix
local geometry, phosphate/clash behavior, base planes, pairing/stacking
restraints and unintended coordinate movement. Every attempt remains immutable.
If automated repair cannot produce a trustworthy local model, expert manual
Coot work is an expected Topo-mode fallback; NASolve should open the exact
model/maps/seam, then import the user's repaired PDB as a new user-reviewed
checkpoint without erasing failed automated attempts.

The first planned blind topology-surgery fixture is **8D93 -> 3GBI-style
representation without coordinate cheating**: the transform receives 8D93,
symmetry and requested cut intent, while 3GBI coordinates are withheld until
the post-transform comparison. Ordinary W identity registration, chain
renaming/numbering offsets, multicopy/partial-copy ASUs and bounded multi-PDB MR
checks remain separate validation rungs.

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
Keep the top-level queue trigger-based, with project-scoped banks beneath it;
it exists so clean-W wiring, blind 8D93 -> 3GBI surgery, 8D31-like multiplicity,
repeat/root-strand closure, emergent-tile cases, guided ambiguity and bounded
multi-PDB checks are not forgotten as implementation context moves across chats.

Validation history is preserved rather than overwritten:

- the earlier Birch checkpoint at code head
  `4452295c3330de6d55bddd75b01be21f39afb222` had **23 focused registration
  tests passing locally**;
- the current Birch bundle at code head
  `686830beb64907f2a1ba73fa1bdbff97f6dcc38d` has **44 focused tests passing locally** across
  `tests/test_construct_registration.py` and
  `tests/test_model_candidates.py`.

Both are user-local checkpoints, not GitHub CI. The full NASolve regression
suite subsequently passed with **664 tests and 222 subtests**, satisfying the
remaining merge gate for PR #17.

### Renamed-chain real-W ambiguity check

A second read-only ED `run_011` test renamed coordinate chains
`A/B/C/D -> M/N/P/Q` without changing coordinates/residue identities.

Scout v1 returned `AMBIGUOUS`, as designed, because multiple equal-length
one-to-one chain assignments satisfied its current length/offset rules. Its non-decisional
design evidence strongly identified the intended mapping (A->M 19/2, B->N 5/2,
C->P 7/0, D->Q 7/0; alternatives carried many more mismatches). Explicit guided
selection of A->M, B->N, C->P, D->Q yielded `REGISTERED_COMPLETE`, one copy,
4 target-identity mismatches and no coordinate edit.

This validates both the conservative refusal-to-guess behavior and the guided
resolution primitive on real W coordinates. It also suggests the next reviewed
inference experiment: classify mismatches as **declared construct-change sites**
versus **unexpected mismatches**, and allow automatic disambiguation only when
one complete one-to-one chain mapping has zero unexpected mismatches and every alternative has
at least one. This is recorded as proposed policy, not runtime authority.

### Oak: experimental design-aware Scout v2

Following the renamed-chain real-W result, Oak prototypes a **proposal-only**
design-aware helper. It enumerates bounded complete one-to-one chain mappings
and classifies differences using explicit target assignment history plus an
optional reviewed-provider baseline map.

The hard proposal rule is intentionally non-scoring: exactly one mapping must
have **zero unexplained mismatches**, and every alternative must have at least
one. A mapping with merely fewer unexplained mismatches is still ambiguous.

The helper is not runtime authority, cannot apply a mapping, and is not called
by AutoMR/PostMR. Provider-baseline evidence is now derived from an assessed
standard frame-catalogue model plus NASolve's existing provider provenance;
free-floating caller residue dictionaries are no longer accepted. The original
Oak v2 checkpoint had **41 focused tests passing locally** at code head
`189fd4589a8c8f2a0191e21e99cec22b428e6a1c`.

The first renamed real-W v2 shadow case supplied only A:13=DC and B:3=DG as
provider evidence and correctly stayed `AMBIGUOUS`: 6 complete mappings,
0 zero-unexplained mappings; the intended mapping had 38 exact,
2 provider-explained and 2 unexplained sites. Direct inspection of
`MR_frames/5W6W/C_G.pdb` verified that the missing provider-pair identities
were A:12=DC and B:4=DG.

The same case was then repeated with all four verified provider identities
(A:12/A:13=DC; B:3/B:4=DG). v2 returned `PROPOSED` with exactly one
zero-unexplained mapping: A->M, B->N, C->P, D->Q. That mapping had 38 exact,
0 target-history, 4 provider-explained and 0 unexplained sites; the five
alternatives retained 12, 11, 16, 17 and 10 unexplained mismatches.
`runtime_authority` remained false.

This validates the experimental zero-unexplained uniqueness rule on the real-W
rename nuisance case without promoting it into runtime authority.

Oak has now implemented the next provenance slice at code head
`c515a37dc41fa8bb1935d2c80c825ebef8153177`: Scout v2 no longer accepts an
ad hoc provider residue dictionary. Optional provider evidence is derived from
an actual `ModelAssessment` of a standard frame-catalogue model plus NASolve's
existing `model_provider` record. The helper requires frame-catalogue
provenance, exact target-site coverage and provider-selector/source-model
agreement, and returns the derived residue baseline bound to the source model's
SHA-256. Runtime authority remains false and AutoMR/PostMR still do not call it.

The provenance-bound helper plus its new fail-closed coverage now passes
**43 focused tests locally** at checkout/test head
`507745a0b7166f05229f6c3501d5e1f694db93e2`; the source-behavior head remains
`c515a37dc41fa8bb1935d2c80c825ebef8153177`. The two added tests explicitly
reject incomplete provider target coverage and provider-selector/source-model
mismatch. The result is user-local, not GitHub CI.

The real renamed-W case has now also passed through the new
`provider_assessment + model_provider` interface. Because ED `run_011`
predates structured `model_provider` provenance, the shadow script reconstructed
only the standard-frame fallback provider facts already proven by the old run's
model path, `model_source`, and source-model SHA-256, then asserted that checksum
against the current `C_G.pdb` before Scout ran. No residue-code dictionary was
supplied. The result remained exactly one zero-unexplained proposal
A->M/B->N/C->P/D->Q (38 exact + 4 provider-explained; alternatives
12/11/16/17/10 unexplained), with provider provenance bound and
`runtime_authority = false`.

Scout v2 therefore remains experimental/non-runtime, but its focused tests and
intended real-W provenance-bound shadow gate are now green. The current Oak
checkout `316ac43eaf85a63cf675828bb8960a28f0db2773` also passed the **full
NASolve regression suite: 672 tests locally**. No runtime or subtest count was
reported for this checkpoint; it is user-local validation, not GitHub CI.

The merge-grade regression gate is therefore green. The remaining confidence
check has also now passed: a fresh current-schema ED `run_013` preflight was
created from the same run_011 scientific intent, and the renamed-W shadow case
was repeated using its native structured `model_provider` record plus a fresh
assessment of the referenced `C_G.pdb`. The result was identical: provider
bound true, caller codes false, exactly one zero-unexplained
A->M/B->N/C->P/D->Q proposal (38 exact + 4 provider-explained; alternatives
12/11/16/17/10 unexplained), with `runtime_authority = false`.

The current backend-only Scout v2 scope is therefore fully validated for its
stated purpose. AutoMR/PostMR integration, automatic application, authoritative
registration and any promotion of Scout v2 into runtime decision-making remain
separate future work and are not implied by this validation.

### Oak branch-readiness sweep

A final user-local readiness sweep on the current Oak checkout reported:

- authority audit: no live callers of
  `propose_design_aware_chain_mapping` outside its defining module;
- patch hygiene: `git diff --check main...oak` produced no output;
- runtime health: `./nasolve check` passed with Python 3.12.14,
  NARestraints 1.1.2, Phenix 2.2.1 and Coot 1.3.3.

This sweep changes no scientific behavior. It confirms that the experimental
Scout v2 helper remains isolated from the live pipeline, the branch diff is
whitespace-clean, and the configured local crystallographic runtime is healthy.

### First real-data registration shadow check

The new registration core was then exercised read-only against existing ED
`run_011` using its frozen 42-site target:

- search model: `REGISTERED` by `identity-site-map`, 4 identity mismatches;
- PostMR ReadySet model: `REGISTERED` by `identity-site-map`, 0 mismatches;
- transition: copy structure `SAME`, multiplicity `SAME`, complete-copy
  identity classes `DIFFERENT`, single-copy coordinate realization `SAME`.

This is the expected scientific behavior: PostMR changed logical residue
identity while the coordinate registration itself remained stable. It is a
useful real-W validation of the abstraction, but **not** yet a live pipeline
integration test because registration was invoked manually against an already
completed run.

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

- `README.md` for current human workflow;
- `docs/README.md` as the documentation map;
- `docs/architecture.md` for durable invariants;
- subsystem docs for active scientific/technical contracts;
- this file for immediate implementation state;
- `docs/construct-registration-intent.json` for machine-readable current intent;
- `docs/history/` for archaeology only.

### Documentation synchronization discipline

Treat small changes in scientific/product intent as real design changes and
propagate them **in the same development turn**, before chat context becomes the
only place they exist.

Use the *smallest authoritative swarm* that preserves the idea:

1. update the relevant subsystem contract for the changed behavior/intent;
2. update `architecture.md` only when a durable invariant or system boundary
   changed;
3. update this handoff when the immediate implementation edge/next action changed;
4. update machine intent whenever future automation/Aster continuity depends on
   the distinction;
5. update `gui.md` when the change affects interaction semantics;
6. update README only when current user-facing workflow changes—not merely for a
   future design thought.

Do not invent final field names, claim implementation, or mark validation merely
to make documents agree. Use explicit states such as **planned**,
**implemented-unvalidated**, **fixture-validated**, and **live-validated**.
After tests/live evidence arrive, make the smallest follow-up edit that promotes
only the claims the evidence supports.

Chat history is working memory, never the sole design authority. A future Aster
should be able to reconstruct the current design and epistemic status from the
repo alone.

README cleanup must never be used as a reason to delete developer provenance.
Public simplification and developer continuity are separate operations. The
2026-09-28 README cleanup was verified to have changed **README only**; Scout
generation history, registration/topology design, GUI contract, campaign Doctor
runway and workflow-recipe intent remain in the dev swarm.
