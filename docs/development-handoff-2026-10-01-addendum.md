# Development handoff addendum — 2026-10-01

Status: **category-based intermediate hops implemented and focused-tested;
full regression/live integration pending; component conversion and dictionary
repair remain separate work**.

Read this addendum before the GZ11 sections of [development-handoff.md](development-handoff.md).
It supersedes the 2026-09-29 immediate GZ11 validation/blocker statements, not the
broader campaign, registration or GUI contracts. The companion
[modified-component-preparation-intent.json](modified-component-preparation-intent.json)
is development intent, not a runtime registry. The current subsystem contract is
[modified-component-preparation.md](modified-component-preparation.md).
Older snapshots retain the validation state they described.

## Current implementation: temporary construction hops

Simon replaced the N9/purine/pyrimidine inference proposal with explicit
intermediate-category policy: **Z -> C, P -> G, D -> A, B -> G, S -> C,
I -> A, X -> G, K -> C, unique -> C**. An unclassified intermediate also
uses C. This is a placement hop, not the final chemical target.

`curated_ligands.construction_parent_code` now uses a recognized `Source sheet`
first, then a recognized `Base Analog` category for older records, then C.
Ordinary categories retain their canonical routes; DNA/RNA selects the sugar
form (RNA T-category uses U). Existing curated component recipes keep precedence.
No N9, family inference or complete ring-role map is required for this step.
The actual final component record/dictionary, sugar compatibility, coordinate
identity and backbone checks remain in force. Existing parent mutation is
skipped when already at that parent. Pairing classes and workbook bytes do not
change.

Focused validation used an exact Git-blob-verified source module from Pine
`97ab3e2` in an isolated Linux environment with a fixture library loader:
**32 failing + 9 passing tests before; 41 passing after**. This is not a full
NASolve suite, live workbook/Coot/Phenix validation or GitHub CI. The last
user-returned full-suite baseline remains 694 tests + 224 subtests. No source
checkout, original GZ11 run, or historical experiment was edited on Simon's
machine by this change.

## Recorded component-normalization intent

Simon clarified: **we WANT 1W5 to go to DZ ALWAYS**, and identified the P
source as **1WA -> DP**. Directions are settled; implementation remains pending.
These specific component conversions are independent of the construction-hop
table and of torsion compatibility. Preserve raw input identities and frozen
historical models. An audited prepared derivative must realize the target
chemistry; a residue-name swap alone is not assumed sufficient.

The existing curated registry contains DE, DF, 1AP, S6G, C38 and 5IU. These are
different exception types, not one universal tautomer-equivalence rule. The
historical 8RO/DE problem and the 1AP dictionary/OP3 fixes remain distinct; the
uncertain recollection of 1W0 does not create a new mapping.

## Evidence returned during this session

All live results below were reported by Simon from his local environment.

1. At local code head `0803989b1c51c6aae7d50a3fcb11835e5280e533`, force-focused
   tests passed 6; the input/PostMR/campaign slice passed 115 tests + 50 subtests;
   the full suite passed **694 tests + 224 subtests** in 53.60 s. Syntax, patch
   hygiene and machine-intent JSON parsing passed.
2. Real installed NARestraints generated and audited actual G/Z -> forced G/C
   restraints. That probe used the historical manual GZ11 `Refine_74` model
   (DG/1W5) and historical DOHU `Std_padd.txt`, not a verified current packaged
   pair-file source. It validates that generation seam, not production GZ11.
3. Fresh `examples/TestSets/GZ11/AutoMR/run_002` reached **MR_SUCCESS, TFZ 12.20**.
   Its frozen target remained DG/DZ and its separate override G/C. PostMR stopped
   before mutation because DNA + Base Analog Z lacked a construction parent.
   No new-run inventory showed 1W5. Refine_74 was manual pre-NASolve work, not
   evidence of a NASolve-created 1W5 model.
4. A single-use experimental probe registered DC as DZ's construction scaffold
   and supplied a checksum-pinned parameterized MonomerLibrary DZ dictionary
   with DNA group adaptation, using a copied MR snapshot. Ordinary Coot/PostMR/
   ReadySet reached **POSTMR_READY**: B:4 DG -> DC -> DZ, A:12 DG, and separate
   G/Z -> G/C force audit. Original code/registry/run were unchanged by the
   probe. This is experimental preparation evidence, not production approval.
5. `Probe/DZ-via-DC` refinement failed at `refine-001` / `AutoRefine/round_001`
   before R statistics with **Conflicting dihedral restraints**. The audit
   identifies DZ B:4 C3e-nyu0 over C4'-O4'-C1'-C2', with C2e/C3e alternatives
   present. The actual command consumed
   **PostMR/ReadySet/prepared_model.ligands.cif**, which retained those rows.
   Current stayed unchanged. This is not numerical refinement success.

The retained pen was `nasolve-dz-dc-probe-kad1eax8` in Simon's macOS temporary
directory, with `MR_snapshot/` and `probe_receipt.json`. It may expire; preserve
all original/experimental attempts. The nine-dataset TestSets campaign has not
been launched or validated by these changes.

## Next bounded slice

Run focused plus full local regression for the category hops. Then generalize
the known alternative-torsion compatibility and effective dictionary authority
without building an automatic chemical-repair engine. September 24 commit
`d203d2e32effd8c5f7b4b319ee2774b05972aa82` added normalization but called it only
for 1AP. The actual effective CIF must be checked after ReadySet/checkpoint
selection; normalizing an unused input copy cannot fix this failure.

Audit supported torsion alternatives, ordered/reversed quartets, period,
existing alternatives and unequal uncertainties explicitly. Correct known
representation issues with a source/derivative record; do not invent bonds or
silently discard conflicting restraints. No general bond-fix policy is yet
implemented. Supplying the reviewed DZ/DP dictionaries and implementing the
requested 1W5/1WA conversions remain separate from intermediate selection.

Historical references: [1AP integration](history/1ap-phosphate-integration.md),
[September 11 handoff](history/development-handoff-2026-09-11.md), and the
September 24 normalization commit. Keep verified internal OP3 rules and existing
component-specific topology checks. No workbook edits, silent downloads, changes
to observations/Free-R, or overwriting of failed attempts are introduced here.
